"""The file transport (spec § 8): tails the state files the PZAgent Lua writes and writes `cmd.txt`.

Tailing is Plan 21's (`testing/agent/link.py`, ported): the files are `state.log`, its rotations `state.<n>.log` and
the chunk files `state-NNNNNN.log`; a rotation below the highest and a chunk once read are never reopened; a partial
last line waits for its newline. Every complete line is parsed as JSON and decoded through `pza1.decode` (a list is
a positional kind, a dict a keyed one); a line that fails either is counted in `bad` and dropped.

The delta rule (ruling S-6): the Lua elides a frame group equal to the last one it sent, so the transport keeps one
running merged frame. A full frame (no group elided) replaces it; a delta frame is merged into it with
`pza1.merge_delta` and becomes it. A delta before any full frame has no base: it counts in `bad` and is dropped.
`lines()` returns full frames only, each a deep copy (a caller may mutate it); `SAME` never leaves the transport.

`cmd_seq` starts at the `seq` of `ack.txt` when the dir holds one (the last command the Lua accepted; a missing,
malformed or negative one seeds 0): the drivers clear the state dir before a session (`_dlib.clear_state_dir`), and
this is the fallback for a dir they did not, where a first command at seq 1 would read as old and nothing would answer.

Counters: `bad`, `gaps`, and `replace_retries` (a `send` whose replace met a Windows sharing violation retries it up
to `REPLACE_TRIES` attempts, `REPLACE_SLEEP_S` apart, and re-raises the last `PermissionError` when they run out).
"""
import copy
import json
import os
import re
import time

from agent.base import pza1

CHUNK_RX = re.compile(r"state-(\d{6})\.log$")
ROT_RX = re.compile(r"state\.(\d+)\.log$")
CMD_KEYS = frozenset(("seq", "aid", "type", "args"))
REPLACE_TRIES = 50       # attempts at the cmd.txt replace: Windows refuses a rename onto a file the Lua holds open
REPLACE_SLEEP_S = 0.01   # between attempts; a collision clears within one client tick (16 ms at 60 Hz)


def _is_seq(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _acked_seq(state_dir):
    """The seq in state_dir's ack.txt, or 0 when it is absent, malformed or not a non-negative int."""
    try:
        with open(os.path.join(state_dir, "ack.txt"), encoding="utf-8") as f:
            ack = json.loads(f.read())
    except (OSError, ValueError):
        return 0
    seq = ack.get("seq") if isinstance(ack, dict) else None
    return seq if _is_seq(seq) and seq >= 0 else 0


class FileTransport:
    def __init__(self, state_dir, clock=time.time):
        self.dir = state_dir
        self.clock = clock
        self.cmd_seq = _acked_seq(state_dir)
        self.expect = 1
        self.gaps = []
        self.replace_retries = 0    # cmd.txt replaces retried after a sharing violation
        self.bad = 0             # lines dropped: malformed, outside the schema, or a delta without a base
        self.running = None         # the last full frame, every delta merged in
        self.last_line_wall = None  # the clock at the last read that returned a line
        self._pos = {}              # file -> bytes consumed
        self._done_chunks = set()

    # -- tailing (Plan 21) ------------------------------------------------------------------------------------------
    def _files(self):
        """Unfinished files in read order, plus the paths the Lua can no longer append to (a segment below the
        highest one)."""
        names = os.listdir(self.dir)
        rots = sorted((int(m.group(1)), n) for n in names for m in [ROT_RX.fullmatch(n)] if m)
        chunks = sorted(n for n in names if CHUNK_RX.fullmatch(n))
        live = ["state.log"] if "state.log" in names else []
        segs = live + [n for _, n in rots]
        closed = {os.path.join(self.dir, n) for n in segs[:-1]}
        order = [os.path.join(self.dir, n) for n in [r for _, r in rots] + chunks + live]
        return [p for p in order if p not in self._done_chunks], closed

    def _read_new(self, path):
        """The decoded lines from the consumed position to the last newline; a partial line waits."""
        pos = self._pos.get(path, 0)
        with open(path, "rb") as f:
            f.seek(pos)
            data = f.read()
        cut = data.rfind(b"\n")
        if cut < 0:
            return []
        self._pos[path] = pos + cut + 1
        out = []
        for raw in data[:cut].split(b"\n"):
            raw = raw.strip()
            if not raw:
                continue
            try:
                line = pza1.decode(json.loads(raw.decode("utf-8")))
            except (ValueError, TypeError):  # bad JSON or UTF-8 (ValueErrors), a value of the wrong type in decode
                line = None
            if line is not None and _is_seq(line.get("seq")):
                out.append(line)
            else:
                self.bad += 1
        if CHUNK_RX.search(path):
            self._done_chunks.add(path)
        return out

    # -- frames ------------------------------------------------------------------------------------------------------
    def _full(self, frame):
        """The frame made full against the running frame, or None for a delta without a base."""
        if pza1.SAME not in frame.values():
            self.running = frame
        elif self.running is None:
            return None
        else:
            self.running = pza1.merge_delta(frame, self.running)
        return self.running

    # -- the seam ----------------------------------------------------------------------------------------------------
    def lines(self):
        got = []
        files, closed = self._files()
        for p in files:
            got.extend(self._read_new(p))
            if p in closed:
                self._done_chunks.add(p)
        got.sort(key=lambda l: l["seq"])
        out = []
        for l in got:
            if l["seq"] != self.expect:
                self.gaps.append((self.expect, l["seq"]))
            self.expect = l["seq"] + 1
            if l["kind"] == "frame":
                l = self._full(l)
                if l is None:
                    self.bad += 1
                    continue
            out.append(copy.deepcopy(l) if l["kind"] == "frame" else l)
        if out:
            self.last_line_wall = self.clock()
        return out

    def send(self, cmd):
        """Write `cmd` to cmd.txt as one sorted JSON line, through cmd.txt.tmp and an atomic replace."""
        if not isinstance(cmd, dict) or set(cmd) != CMD_KEYS:
            raise ValueError("PZA/1 cmd: want the keys %s, got %r" % (sorted(CMD_KEYS), cmd))
        if not _is_seq(cmd["seq"]) or cmd["seq"] <= self.cmd_seq:
            raise ValueError("PZA/1 cmd: seq %r is not above %d" % (cmd["seq"], self.cmd_seq))
        text = json.dumps(cmd, sort_keys=True, allow_nan=False) + "\n"
        tmp = os.path.join(self.dir, "cmd.txt.tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        dst = os.path.join(self.dir, "cmd.txt")
        for attempt in range(REPLACE_TRIES):
            try:
                os.replace(tmp, dst)
                break
            except PermissionError:
                if attempt == REPLACE_TRIES - 1:
                    raise
                self.replace_retries += 1
                time.sleep(REPLACE_SLEEP_S)
        self.cmd_seq = cmd["seq"]
