"""The Python side of PZAgent's file channel (spec § 2). Tails the state files the Lua writes and sends
commands as key=value lines (ruling P21-0). Knows nothing about the game."""
import glob, json, os, re, time

CHUNK_RX = re.compile(r"state-(\d{6})\.log$")
ROT_RX = re.compile(r"state\.(\d+)\.log$")


class Link:
    def __init__(self, state_dir, clock=time.time):
        self.dir = state_dir
        self.clock = clock
        self.cmd_seq = 0
        self.expect = 1
        self.gaps = []
        self.acks = {}
        self.last_goal = None
        self._pos = {}          # file -> bytes consumed
        self._done_chunks = set()

    def _files(self):
        rots = sorted(glob.glob(os.path.join(self.dir, "state.*.log")), key=lambda p: int(ROT_RX.search(p).group(1)))
        chunks = sorted(glob.glob(os.path.join(self.dir, "state-*.log")), key=lambda p: int(CHUNK_RX.search(p).group(1)))
        main = os.path.join(self.dir, "state.log")
        return [p for p in rots + chunks + [main] if os.path.exists(p) and p not in self._done_chunks]

    def _read_new(self, path):
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
            if raw:
                out.append(json.loads(raw.decode("utf-8")))
        if CHUNK_RX.search(path):
            self._done_chunks.add(path)
        return out

    def lines(self):
        out = []
        for p in self._files():
            out.extend(self._read_new(p))
        out.sort(key=lambda l: l["seq"])
        for l in out:
            if l["seq"] != self.expect:
                self.gaps.append((self.expect, l["seq"]))
            self.expect = l["seq"] + 1
            if l["kind"] == "ack":
                self.acks[l["cmdSeq"]] = l
            if l["kind"] == "frame" and "goal" in l:
                self.last_goal = l["goal"]
        return out

    def send(self, goal, args=""):
        self.cmd_seq += 1
        tmp = os.path.join(self.dir, "cmd.txt.tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write("seq=%d\ngoal=%s\nargs=%s\n" % (self.cmd_seq, goal, args))
        os.replace(tmp, os.path.join(self.dir, "cmd.txt"))
        return self.cmd_seq

    def ack_of(self, seq):
        return self.acks.get(seq)

    def goal_status(self):
        return self.last_goal

    def await_goal(self, seq, timeout_s, poll_s=0.1, on_line=None, _sleep=time.sleep):
        t0 = self.clock()
        while True:
            for l in self.lines():
                if on_line:
                    on_line(l)
                g = l.get("goal") if l["kind"] == "frame" else None
                if g and g.get("seq") == seq and g.get("state") in ("done", "failed"):
                    return g
            if self.clock() - t0 > timeout_s:
                raise TimeoutError("goal %d not finished in %ss" % (seq, timeout_s))
            _sleep(poll_s)
