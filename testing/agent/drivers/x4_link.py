"""x4_link -- Plan 22 X4, "the link": the agent base's first live session. One boot of agent-nozombies (one admin
client, -debug, PZTestKit + PZAgent, no zombies); the agent stands still, scans, walks twenty legs and scans again
while the driver measures the base over the PZA/1 file channel. Graded by `agent.base.gates.gate_x4` (spec § 10),
which also states the sidecar trigger (spec § 8 (6)) before this driver runs; `x4_grade.py` prints that grade.

PHASES (each through xs.run_phase; a phase's fault lands under out["phase_errors"][name] and the next still runs;
each reading at out["readings"][phase]):
  hello         pump until the hello line and a first frame, within HELLO_TIMEOUT_S; the hello's proto must be "PZA/1".
                {ok, proto, hello, first_frame {seq, wallMs}}; a failed hello skips every phase but `server`.
  rate60        Rate(60) awaited to done, RATE60_S standing still pumping every POLL_S, then Rate(10) awaited.
                {frames, tickMs [each 60 Hz frame's cost.tickMs, the frames after Rate(60)'s done act], tick_mean_ms,
                first_seq, last_seq, span_s, seconds, rate_on, rate_off}.
  scan          Scan(SCAN_R) awaited, every part of its `map full` scan awaited (the first part's `parts`; 49 at r = 15
                with 20 squares a part), SCAN_TIMEOUT_S at most. {scanId, parts, got, complete, squares, mapMs [each
                frame's cost.mapMs while the scan ran], seconds, act}.
  walk          WALK_LEGS WalkTo legs from the settled start (the position after `scan`): leg i goes from its own
                start x0 to x0 + LEG_DX (i even) or x0 - LEG_DX (i odd) at the start's y, gait "walk", each awaited to
                a terminal state or LEG_TIMEOUT_S (Actions' deadline: `timeout`), the agent settled (two frames within
                MOVE_EPS_TILES, SETTLE_S at most) before each. {start, legs [{leg, x0, y0, target, aid,
                accepted_seq, accepted_wallMs, accepted_wall, settled, at_accept, first_move {seq, wallMs, x, y} |
                None, end {state, reason, result, ended_wall}}], map_deltas}. first_move is the first frame after the
                accepted act whose position is more than MOVE_EPS_TILES from the position at accept (any direction).
  final_scan    settle, then the whole kept map snapshotted (world.map and world.containers; the final scan's squares
                define the window), then Scan(SCAN_R) as `scan`; the final scan's squares against the kept ones:
                {x, y, settled, kept_squares, final_squares, scan {...as scan}, kept {walls, doors, windows,
                containers: {kept, total, absent, seen, ratio[, note]}}}. walls: final squares with solid true that the
                kept map also reads solid; doors, windows: a non-null door or window; containers: by square and type.
                absent: on a square the kept map holds no entry for (coverage); ratio = kept / (total - absent), the
                fidelity over the squares both saw; seen 0 reads ratio 1.0.
  worst_window  pump standing still until the frames' cost rows span WORST_WINDOW_S (the 10-minute window of the worst
                tick, ruling P22-4), or until the budget's last RESERVE_S. {span_s, frames, stopped "span" | "reserve"}.
  server        stats.all for USER and players, each step's row kept raw: {stats, players}; each step's timeout is
                min(10 s, the budget's remaining), so a reserve stop keeps the reading.

FRAMES (out["frames"]): `cost` every frame's {seq, tick, wallMs, cost}; `n` frames; `gaps` the transport's seq gaps
(count) and `gap_list`; `bad` lines dropped; `lua_errors` the lua_error events and `lua_error_msgs`; `parks` the
client console's lines matching PARK_RX (a copy of a_pipe_3's CLIENT_ERR_RX: an unguarded Lua error parks the -debug
client) plus 1 when pzt saw the client park and the console showed nothing. out["finished"] is set last.

Clocks: a line's wallMs is the client's clock (ms); `*_wall` keys are this process's clock in seconds.

RULES: never edited after its run (the next pass is a new file); takes no argument; one live session at a time; free
memory gated at MIN_FREE_GB before the boot; never -safemode. Nothing is imported from the frozen drivers but `_dlib`
and `xlib`; the Plan 21 Link is not used (ruling P22-0): the transport is `FileTransport` on the client's state dir.
"""
import collections
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _dlib as DL                                    # noqa: E402
import xlib as X                                      # noqa: E402
from agent.base import gates as GT                    # noqa: E402
from agent.base import pza1                           # noqa: E402
from agent.base.actions import Actions                # noqa: E402
from agent.base.transport.files import FileTransport  # noqa: E402
from agent.base.world import World                    # noqa: E402

KEY = "x4_link"
DRIVER = "x4_link.py"
PROFILE = "testing/profiles/agent-nozombies.toml"
ARTIFACT = "x4_link.json"
BUDGET_S = 840.0
USER = "admin"
MIN_FREE_GB = 12.0
RATE60_S = 30.0
WORST_WINDOW_S = 600.0
WALK_LEGS = 20
LEG_DX = 6
LEG_TIMEOUT_S = 30.0
SCAN_R = 15
SCAN_TIMEOUT_S = 60.0
MOVE_EPS_TILES = 0.01
SIDECAR_MEAN_MS = 1.0
SIDECAR_WORST_MS = 3.0
HELLO_TIMEOUT_S = 60.0
ACT_TIMEOUT_S = 10.0       # Rate: accepted and done (a Scan's deadline is SCAN_TIMEOUT_S)
POLL_S = 0.05              # the pump's 20 Hz
SETTLE_S = 2.0
RESERVE_S = 30.0           # the budget's last seconds, left to `server` and the teardown
PERSIST_S = 60.0
REPO = DL.REPO
AGENT_LUA = "testing/PZAgent"
AGENT_BASE = "testing/agent/base"
# a copy of a_pipe_3's CLIENT_ERR_RX (a_pipe.py's): a Lua error line in the client console, the -debug client's park
PARK_RX = r"LuaError|STACK TRACE|attempted index|tried to call nil"
_ME = os.path.basename(os.path.abspath(__file__))

CONSTANTS = {k: globals()[k] for k in (
    "BUDGET_S", "MIN_FREE_GB", "RATE60_S", "WORST_WINDOW_S", "WALK_LEGS", "LEG_DX", "LEG_TIMEOUT_S", "SCAN_R",
    "SCAN_TIMEOUT_S", "MOVE_EPS_TILES", "SIDECAR_MEAN_MS", "SIDECAR_WORST_MS", "HELLO_TIMEOUT_S", "ACT_TIMEOUT_S",
    "POLL_S", "SETTLE_S", "RESERVE_S", "PERSIST_S", "PARK_RX")}
PHASES = ("hello", "rate60", "scan", "walk", "final_scan", "worst_window", "server")


def parse_argv(argv, driver_file):
    """The driver takes no argument: the refusal text, or None for a bare call."""
    if argv:
        return f"{os.path.basename(driver_file)} takes no arguments; a bare call boots the session"
    return None


def new_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {},
            "readings": {}, "frames": new_frames(), "world_changes": {"left_in_place": []}, "finished": False}


def new_frames():
    return {"cost": [], "n": 0, "gaps": 0, "gap_list": [], "bad": 0, "lua_errors": 0, "lua_error_msgs": [],
            "parks": None}


def driver_checks(driver_file, repo=REPO, git_say=None, git_dirty=None):
    """The driver's own pre-boot checks: its file name, the profile on disk, no committed artifact of its key (a
    driver that ran is frozen), the agent Lua, the agent base and the driver committed clean. Returns (checks, ok)."""
    git_say = git_say or DL.C.git_say
    git_dirty = git_dirty or DL.C.git_dirty
    base = os.path.basename(driver_file)
    c = {"driver_file": base == DRIVER, "driver_prefix": base.startswith(KEY),
         "profile_exists": os.path.isfile(os.path.join(repo, PROFILE))}
    c["no_committed_artifact"] = git_say("ls-files", "--", f"testing/artifacts/{KEY}-*") == ""
    c["agent_lua_dirty"] = git_dirty(AGENT_LUA)[0]
    c["agent_base_dirty"] = git_dirty(AGENT_BASE)[0]
    c["driver_dirty"] = git_dirty(f"testing/agent/drivers/{DRIVER}")[0]
    ok = (c["driver_file"] and c["driver_prefix"] and c["profile_exists"] and c["no_committed_artifact"]
          and c["agent_lua_dirty"] is False and c["agent_base_dirty"] is False and c["driver_dirty"] is False)
    return c, ok


def preboot(driver_file, repo=REPO):
    """_dlib.preboot (git provenance, doctor, harness Lua clean, the layout lint) and the driver's own checks."""
    pre, ok = DL.preboot(driver_file, os.path.join(repo, PROFILE))
    pre["driver_checks"], ok2 = driver_checks(driver_file, repo)
    return pre, bool(ok and ok2)


def memory_gate(xs, wait=None):
    """a_pipe.py's memory_gate, copied: the memory wait before the boot; a false result refuses. The wall budget's
    clock restarts after it, so a long wait never eats the session's budget; the readings stay under
    out["memory_wait"]."""
    ok, readings = (wait or DL.wait_memory)(MIN_FREE_GB)
    xs.out["memory_wait"] = readings
    if not ok:
        xs.refuse("blocked: memory")
    xs.t0 = xs.clock()
    return readings


def clearing_make_client(make):
    """a_pipe.py's clearing_make_client, reimplemented over DL.clear_state_dir: pzt.session.make_client, then the
    stale pzagent/ folder removed before the client is started (the fixture snapshot copies the client's Lua/ folder;
    a kept state would be read as this session's)."""
    def wrapped(*a, **kw):
        c, restored = make(*a, **kw)
        DL.clear_state_dir(c)
        return c, restored
    return wrapped


def count_parks(consoles, admin_parked=False):
    """({user: [PARK_RX lines]}, parks): the console lines matching PARK_RX (the harness echo excluded), plus 1 when
    pzt saw the client park and no console line shows it."""
    import re
    rx, echo, never = re.compile(PARK_RX), re.compile(r"PZTK: "), re.compile(r"(?!x)x")
    found, n = {}, 0
    for user, path in consoles:
        lines, _ = X.grep_noecho(path, rx, 80, echo, never)
        found[user] = lines
        n += len(lines)
    if n == 0 and admin_parked:
        n = 1
    return found, n


# ================================================================ the readings: pure functions over PZA/1 lines
def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _frames(lines):
    return [l for l in lines if l.get("kind") == "frame"]


def _xy(frame):
    me = frame.get("me") if isinstance(frame, dict) else None
    if not isinstance(me, dict):
        return None
    x, y = _num(me.get("x")), _num(me.get("y"))
    return (x, y) if x is not None and y is not None else None


def cost_row(frame):
    """A frame's row in out["frames"]["cost"]."""
    c = frame.get("cost")
    return {"seq": frame.get("seq"), "tick": frame.get("tick"), "wallMs": frame.get("wallMs"),
            "cost": dict(c) if isinstance(c, dict) else None}


def _cost(frame, key):
    c = frame.get("cost")
    return _num(c.get(key)) if isinstance(c, dict) else None


def act_line(lines, aid, states):
    """The first act line for `aid` in one of `states`, or None."""
    for l in lines:
        if l.get("kind") == "act" and l.get("aid") == aid and l.get("state") in states:
            return l
    return None


def hello_reading(lines):
    hello = next((l for l in lines if l.get("kind") == "hello"), None)
    frame = next((l for l in lines if l.get("kind") == "frame"), None)
    proto = hello.get("proto") if hello else None
    return {"ok": hello is not None and proto == pza1.PROTO and frame is not None, "proto": proto, "hello": hello,
            "first_frame": {"seq": frame.get("seq"), "wallMs": frame.get("wallMs")} if frame else None}


def rate60_reading(lines, after_seq, seconds):
    """The 60 Hz window: the frames after Rate(60)'s done act (seq > after_seq)."""
    frames = [f for f in _frames(lines) if after_seq is not None and (_num(f.get("seq")) or 0) > after_seq]
    ticks = [v for v in (_cost(f, "tickMs") for f in frames) if v is not None]
    walls = [w for w in (_num(f.get("wallMs")) for f in frames) if w is not None]
    return {"frames": len(frames), "tickMs": ticks, "tick_mean_ms": sum(ticks) / len(ticks) if ticks else None,
            "first_seq": frames[0].get("seq") if frames else None,
            "last_seq": frames[-1].get("seq") if frames else None,
            "span_s": (max(walls) - min(walls)) / 1000.0 if len(walls) > 1 else None, "seconds": seconds}


def _scan_lines(lines):
    full = [l for l in lines if l.get("kind") == "map" and l.get("mode") == "full"]
    sids = [s for s in (_num(l.get("scanId")) for l in full) if s is not None]
    if not sids:
        return None, []
    sid = max(sids)
    return sid, [l for l in full if l.get("scanId") == sid]


def scan_reading(lines):
    """The newest scan among `lines`' `map full` parts: {scanId, parts, got, complete, squares, mapMs}. mapMs is each
    frame's cost.mapMs up to the first frame after the last part seen."""
    sid, mine = _scan_lines(lines)
    if sid is None:
        return {"scanId": None, "parts": None, "got": 0, "complete": False, "squares": 0, "mapMs": []}
    parts = _num(mine[0].get("parts"))
    got = sorted({l.get("part") for l in mine})
    last = max(l["seq"] for l in mine)
    map_ms = []
    for f in _frames(lines):
        v = _cost(f, "mapMs")
        if v is not None:
            map_ms.append(v)
        if f["seq"] > last:
            break
    return {"scanId": sid, "parts": parts, "got": len(got), "complete": parts is not None and len(got) >= parts,
            "squares": sum(len(l.get("squares") or ()) for l in mine), "mapMs": map_ms}


def scan_squares(lines):
    """The newest scan's squares, one per (x, y, z), the last part's copy kept."""
    _, mine = _scan_lines(lines)
    sq = {}
    for l in mine:
        for s in l.get("squares") or ():
            if isinstance(s, dict) and s.get("x") is not None and s.get("y") is not None:
                sq[(s["x"], s["y"], s.get("z") or 0)] = s
    return list(sq.values())


def leg_reading(lines, aid, x0, y0, eps=MOVE_EPS_TILES):
    """One walk leg off the lines read while it ran: the accepted act, the position at accept (the last frame before
    it, else x0, y0), first_move (the first frame after the accept more than eps from that position), the map deltas."""
    acc = act_line(lines, aid, ("accepted",))
    row = {"accepted_seq": None, "accepted_wallMs": None, "at_accept": None, "first_move": None,
           "map_deltas": sum(1 for l in lines if l.get("kind") == "map" and l.get("mode") == "delta")}
    if acc is None:
        return row
    row["accepted_seq"], row["accepted_wallMs"] = acc.get("seq"), acc.get("wallMs")
    pos = (x0, y0) if _num(x0) is not None and _num(y0) is not None else None
    for f in _frames(lines):
        if f["seq"] < acc["seq"] and _xy(f) is not None:
            pos = _xy(f)
    row["at_accept"] = {"x": pos[0], "y": pos[1]} if pos else None
    if pos is None:
        return row
    for f in _frames(lines):
        p = _xy(f)
        if f["seq"] > acc["seq"] and p is not None and math.hypot(p[0] - pos[0], p[1] - pos[1]) > eps:
            row["first_move"] = {"seq": f["seq"], "wallMs": f.get("wallMs"), "x": p[0], "y": p[1]}
            break
    return row


def _sq_key(s):
    return (s["x"], s["y"], s.get("z") or 0)


def snapshot_kept(world):
    """The whole kept map (the final scan's squares define the window): its squares (copies) and its containers as
    (x, y, z, type), from world.map and world.containers."""
    squares = [json.loads(json.dumps(s)) for s in world.map.values()]
    conts = [(k[0], k[1], k[2], c.get("type")) for k, c in world.containers.items()]
    return squares, conts


def _ratio(kept, total, absent):
    """Fidelity over the squares both maps saw: ratio = kept / seen, seen = total - absent; seen 0 reads 1.0."""
    seen = total - absent
    r = {"kept": kept, "total": total, "absent": absent, "seen": seen, "ratio": kept / seen if seen else 1.0}
    if not seen:
        r["note"] = "no square of this kind both maps saw: ratio 1.0"
    return r


def map_kept(kept_squares, kept_containers, final_squares):
    """The kept map against the final scan, per kind over the final scan's squares (containers: (square, type)
    pairs): `total` the final scan's, `absent` those on a square the kept map holds no entry for (never sent by a full
    scan: coverage, reported for the guide), `kept` those the kept map also holds, `ratio` kept / (total - absent):
    the kept map's fidelity over the squares both saw."""
    kept = {_sq_key(s): s for s in kept_squares}
    final = {_sq_key(s): s for s in final_squares}
    tests = (("walls", lambda s: s.get("solid") is True), ("doors", lambda s: s.get("door") is not None),
             ("windows", lambda s: s.get("window") is not None))
    out = {}
    for kind, test in tests:
        total = [k for k, s in final.items() if test(s)]
        out[kind] = _ratio(sum(1 for k in total if k in kept and test(kept[k])), len(total),
                           sum(1 for k in total if k not in kept))
    want = collections.Counter((k[0], k[1], k[2], c.get("type")) for k, s in final.items()
                               for c in (s.get("containers") or ()) if isinstance(c, dict))
    have = collections.Counter(kept_containers)
    out["containers"] = _ratio(sum(min(n, have[c]) for c, n in want.items()), sum(want.values()),
                               sum(n for c, n in want.items() if c[:3] not in kept))
    return out


def frames_span_s(rows):
    walls = [w for w in (_num(r.get("wallMs")) for r in rows if r.get("cost") is not None) if w is not None]
    return (max(walls) - min(walls)) / 1000.0 if len(walls) > 1 else 0.0


def _end(a):
    return {"state": a.state, "reason": a.reason, "result": a.result, "ended_wall": a.ended_wall}


# ================================================================ the session
class X4:
    """The phases over one FileTransport: `pump()` reads the transport, feeds World and Actions and keeps the frames'
    rows and counters; each phase slices `self.lines` (every line read, in seq order) for its reading."""

    def __init__(self, xs, transport, clock=time.time, sleep=time.sleep):
        self.xs, self.tr, self.clock, self.sleep = xs, transport, clock, sleep
        self.out = xs.out
        self.out.setdefault("frames", new_frames())
        self.world = World()
        self.actions = Actions(transport, clock=clock)
        self.lines = []
        self.cost_walls = None      # (first, last) wallMs of the frames whose cost group is not null

    # -- the pump ------------------------------------------------------------------------------------------------
    def pump(self):
        got = self.tr.lines()
        fr = self.out["frames"]
        for l in got:
            self.world.apply(l)
            if l.get("kind") == "frame":
                row = cost_row(l)
                fr["cost"].append(row)
                fr["n"] += 1
                w = _num(row["wallMs"])
                if row["cost"] is not None and w is not None:
                    self.cost_walls = (w, w) if self.cost_walls is None else (min(self.cost_walls[0], w),
                                                                              max(self.cost_walls[1], w))
            elif l.get("kind") == "event" and l.get("event") == "lua_error":
                fr["lua_errors"] += 1
                fr["lua_error_msgs"] = (fr["lua_error_msgs"] + [l.get("msg")])[-20:]
        self.actions.pump(got)
        self.lines.extend(got)
        fr["gaps"], fr["gap_list"], fr["bad"] = len(self.tr.gaps), [list(g) for g in self.tr.gaps[:50]], self.tr.bad
        return got

    def wait(self, pred, timeout_s):
        """Pump every POLL_S until pred() or timeout_s; True when pred() held. xs.check() guards every poll."""
        t0 = self.clock()
        while True:
            self.pump()
            if pred():
                return True
            if self.clock() - t0 > timeout_s:
                return False
            self.xs.check()
            self.sleep(POLL_S)

    def send(self, cmd, deadline_s=ACT_TIMEOUT_S):
        a = self.actions.send(cmd, deadline_s=deadline_s)
        self.wait(lambda: self.actions.done(a), deadline_s + 1.0)
        return a

    def me(self):
        return _xy({"me": self.world.me})

    def reading(self, phase, value):
        self.out["readings"][phase] = value
        return value

    # -- the phases ----------------------------------------------------------------------------------------------
    def hello(self):
        self.wait(lambda: self.world.hello is not None and self.world.me is not None, HELLO_TIMEOUT_S)
        r = self.reading("hello", hello_reading(self.lines))
        if not r["ok"]:
            raise RuntimeError("no PZA/1 hello and frame within %s s (proto %r)" % (HELLO_TIMEOUT_S, r["proto"]))

    def rate60(self):
        r = self.reading("rate60", {"rate_on": None})
        a = self.send(pza1.Rate(60))
        r["rate_on"] = {"aid": a.aid, **_end(a)}
        done = act_line(self.lines, a.aid, ("done",))
        if a.state != "done" or done is None:
            raise RuntimeError("Rate(60) ended %s %r" % (a.state, a.reason))
        i0, t0 = next(i for i, l in enumerate(self.lines) if l is done), self.clock()   # the window opens at done
        while self.clock() - t0 < RATE60_S:
            self.pump()
            self.xs.check()
            self.sleep(POLL_S)
        self.pump()
        r.update(rate60_reading(self.lines[i0:], done["seq"], round(self.clock() - t0, 3)))
        off = self.send(pza1.Rate(10))
        r["rate_off"] = {"aid": off.aid, **_end(off)}

    def _scan(self):
        i0, t0 = len(self.lines), self.clock()
        a = self.actions.send(pza1.Scan(SCAN_R), deadline_s=SCAN_TIMEOUT_S)

        def finished():
            if not self.actions.done(a):
                return False
            return a.state != "done" or scan_reading(self.lines[i0:])["complete"]
        self.wait(finished, SCAN_TIMEOUT_S)
        r = scan_reading(self.lines[i0:])
        r["seconds"] = round(self.clock() - t0, 3)
        r["act"] = {"aid": a.aid, **_end(a)}
        return r, scan_squares(self.lines[i0:])

    def scan(self):
        self.reading("scan", self._scan()[0])

    def settle(self):
        """Pump until the last two frames' positions are within MOVE_EPS_TILES, SETTLE_S at most."""
        def still():
            ps = [p for p in (_xy(f) for f in _frames(self.lines[-40:])) if p is not None]
            return len(ps) >= 2 and math.hypot(ps[-1][0] - ps[-2][0], ps[-1][1] - ps[-2][1]) <= MOVE_EPS_TILES
        return self.wait(still, SETTLE_S)

    def walk(self):
        start = self.me()
        r = self.reading("walk", {"start": {"x": start[0], "y": start[1]} if start else None, "legs": [],
                                  "map_deltas": 0})
        if start is None:
            raise RuntimeError("no position to walk from")
        for i in range(WALK_LEGS):
            settled = self.settle()
            x0, y0 = self.me()
            tx = x0 + (LEG_DX if i % 2 == 0 else -LEG_DX)
            i0 = len(self.lines)
            a = self.actions.send(pza1.WalkTo(float(tx), float(start[1]), "walk"), deadline_s=LEG_TIMEOUT_S)
            self.wait(lambda: self.actions.done(a), LEG_TIMEOUT_S + 1.0)
            leg = {"leg": i + 1, "x0": x0, "y0": y0, "target": {"x": tx, "y": start[1]}, "aid": a.aid,
                   "accepted_wall": a.acked_wall, "settled": settled}
            leg.update(leg_reading(self.lines[i0:], a.aid, x0, y0))
            leg["end"] = _end(a)
            r["legs"].append(leg)
            r["map_deltas"] += leg["map_deltas"]

    def final_scan(self):
        settled = self.settle()
        pos = self.me()
        if pos is None:
            raise RuntimeError("no position to scan from")
        kept_sq, kept_c = snapshot_kept(self.world)
        r = self.reading("final_scan", {"x": pos[0], "y": pos[1], "settled": settled, "kept_squares": len(kept_sq)})
        scan, final = self._scan()
        r.update({"scan": scan, "final_squares": len(final), "kept": map_kept(kept_sq, kept_c, final)})

    def worst_window(self):
        r = self.reading("worst_window", {"span_s": None, "frames": None, "stopped": None})
        last_persist = self.clock()
        while True:
            self.pump()
            cw = self.cost_walls
            r["span_s"] = (cw[1] - cw[0]) / 1000.0 if cw else 0.0      # frames_span_s(frames.cost), kept as it grows
            r["frames"] = len(self.out["frames"]["cost"])
            if r["span_s"] >= WORST_WINDOW_S:
                r["stopped"] = "span"
                return
            if self.xs.wall() > self.xs.budget_s - RESERVE_S:
                r["stopped"] = "reserve"
                return
            if self.clock() - last_persist > PERSIST_S:
                self.xs.persist()
                last_persist = self.clock()
            self.xs.check()
            self.sleep(POLL_S)

    def server(self):
        """Each step's timeout is min(10, the budget's remaining seconds), so a reserve stop keeps the reading."""
        def timeout():
            return max(1.0, min(10.0, self.xs.budget_s - self.xs.wall()))
        r = self.reading("server", {})
        r["stats"] = self.xs.step("stats", "server", "stats.all", USER, timeout=timeout())
        r["players"] = self.xs.step("players", "server", "players", timeout=timeout())

    def run(self):
        self.xs.run_phase("hello", self.hello)
        if (self.out["readings"].get("hello") or {}).get("ok"):
            for name in PHASES[1:-1]:
                self.xs.run_phase(name, getattr(self, name))
        else:
            self.xs.note("no hello: every phase but server skipped")
        self.xs.run_phase("server", self.server)


# ================================================================ the boot
def main(budget_s=BUDGET_S):
    from _common import ask, hard_kill                       # noqa: E402
    import x49b_lib as B                                     # noqa: E402
    from pzt import fixture as fx, profile, session          # noqa: E402
    from pzt.bus import resolve_side                         # noqa: E402
    from pzt.paths import new_run_dir                        # noqa: E402

    pre, ok = preboot(_ME)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    prof = profile.load(os.path.join(REPO, PROFILE))
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(KEY)
    tl = session.Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = new_out()
    out["world_changes"]["restored"] = f"fixture {prof.fixture} restored into the run dir"
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, user=USER)
    xs.path = os.path.join(run_dir, ARTIFACT)
    out.update({"run_id": run_id, "session_key": KEY, "driver": _ME, "user": USER, "profile": prof.report(),
                "preboot": pre, "argv": sys.argv[1:], "constants": CONSTANTS,
                "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                            "build": rec_fx.get("build")},
                "driver_commit": DL.C.git_say("log", "-1", "--format=%h", "--", f"testing/agent/drivers/{DRIVER}")})
    memory_gate(xs)
    xs.mem("preboot")
    xs.persist()
    try:
        out.update(DL.boot(xs, prof, rec_fx, run_dir, [USER], started, clients, holder,
                           make_client=clearing_make_client(session.make_client)))
        xs.mem("ready")
        xs.persist()
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            out["state_dir"] = DL.state_dir(clients[USER])
            X4(xs, FileTransport(DL.state_dir(clients[USER]))).run()
    except Exception as e:                                   # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            found, n = count_parks([(getattr(c, "username", "?"), c.console) for c in every], xs.parked())
            out["logs"] = {"patterns": {"park": PARK_RX}, "clients": found}
            out["frames"]["parks"] = n

        xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs)
        xs.mem("after")
        try:
            out["gate_x4"] = GT.gate_x4(out)
        except Exception as e:                               # noqa: BLE001 - x4_grade.py re-grades the artifact
            out["gate_x4_error"] = f"{type(e).__name__}: {e}"
        out["finished"] = True
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)
    g = out.get("gate_x4") or {}
    print(json.dumps({"run_id": run_id, "run_dir": run_dir, "error": out.get("error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "budget_stop": out.get("budget_stop"), "verdict": g.get("verdict"), "pass": g.get("pass"),
                      "sidecar_trigger": g.get("sidecar_trigger"), "wall_seconds": out.get("wall_seconds")},
                     indent=1, default=str))
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main()
