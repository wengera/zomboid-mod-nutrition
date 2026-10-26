"""a_pipe -- Plan 21 Task 8, Stage A (spec § 4.1): the pipe's go/no-go. One boot of agent-nozombies (fixture `agent`,
admin -debug, PZTestKit + PZAgent, zombies none); the agent sits still and the driver measures the file channel.

PHASES (each through xs.run_phase; a phase's fault is recorded and the next still runs):
  rates   wait for the hello line (HELLO_TIMEOUT_S; out["hello"], out["mode"]); then for r in RATES: `rate r`, its ack
          (ACK_TIMEOUT_S), WINDOW_S of wall clock collecting every frame after the ack: the frame count against the
          nominal r * WINDOW_S (60*r at 60 ticks/s), the per-frame cost lists pollMs/actMs/senseMs/linkMs and their sum tickMs, dropped's max, the
          first and last frame wallMs and the state files' bytes at the window's ends.
  scans   for r in SCAN_RADII: SCANS_PER_RADIUS `scan r`, each awaited by its scan line (SCAN_TIMEOUT_S): scanMs, the
          square count, the line's re-serialised byte length, its missing list and the next frame's senseMs.
  motion  MOTION_TRIPS round trips of `goto <x+10> <y>` then `goto <x-10> <y>` (world coordinates, x and y the latest
          frame's once two consecutive frames stand still (SETTLE_S cap; settled and settleMs recorded), sent
          unrounded); per command the Python wall ms at the write, the ack's wallMs, the first frame displaced from
          the pre-command x by more than MOTION_EPS in the command's own direction (its wallMs, seq, x and the Python
          wall ms at which it was read), the goal's final state/detail (GOAL_TIMEOUT_S), and the informational
          cmd_motion_host_ms (first-motion wallMs - sentPyMs, two clocks on one host; never graded).
  server  SERVER_CALLS harness stats.all round trips (_dlib.bus_stats), the bus's cost beside the link's.

Every reading sits under out["readings"] with its raw values (no rounding). out["missing"] is the union of every missing
list a line carried; out["gaps"] the link's seq gaps; out["bad"] its malformed lines; out["lua_errors"] the lua_error
events; out["client_lua_errors"] the error lines in the client console. The grade is a_grade.py over the artifact
(grades.gate_a). out["finished"] is set last; the controller polls the persisted artifact for it.

Clocks: a line's wallMs is the client's PZA.now() (getTimestampMs); a key ending in PyMs is this process's time.time()
in ms. The two are never subtracted from each other by the grade.

RULES: never edited after its run (the next pass is a_pipe_2.py); takes no argument; one live session at a time; free
memory gated at MIN_FREE_GB before the boot; never -safemode.
"""
import json
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
from agent.world import World                         # noqa: E402

KEY = "a_pipe"
DRIVER = "a_pipe.py"
PROFILE = "testing/profiles/agent-nozombies.toml"
ARTIFACT = "a_pipe.json"
BUDGET_S = 540.0
USER = "admin"
MIN_FREE_GB = 12.0
REPO = DL.REPO
_ME = os.path.basename(os.path.abspath(__file__))

HELLO_TIMEOUT_S = 60.0
ACK_TIMEOUT_S = 10.0
RATES = (2, 5, 10)
WINDOW_S = 60.0
SCAN_RADII = (5, 10, 15)
SCANS_PER_RADIUS = 5
SCAN_TIMEOUT_S = 15.0
NEXT_FRAME_TIMEOUT_S = 5.0
MOTION_TRIPS = 10
MOTION_DX = (10, -10)                # goto takes world coordinates: the target is the pre-command x + dx, y kept
MOTION_EPS = 0.2                     # tiles of displacement in the command's own direction
SETTLE_S = 3.0                       # before x0: two consecutive frames with equal x, y, waited for up to this
GOAL_TIMEOUT_S = 30.0
SERVER_CALLS = 3
POLL_S = 0.1
COST_KEYS = ("pollMs", "actMs", "senseMs", "linkMs")
AGENT_LUA = "testing/PZAgent"
# a Lua error line in the client console (the onTick pcall reports its raises as lua_error events; this catches the
# rest). Lua-specific only, after pzt/client.py's lua_error: every client boot prints the benign Java
# "AdvancedAnimator$1.visitFileFailed> Exception thrown" eight times, so a generic exception pattern is NO-GO on every run.
CLIENT_ERR_RX = r"LuaError|STACK TRACE|attempted index|tried to call nil"
ECHO_RX = r"PZTK: "

CONSTANTS = {k: globals()[k] for k in (
    "HELLO_TIMEOUT_S", "ACK_TIMEOUT_S", "RATES", "WINDOW_S", "SCAN_RADII", "SCANS_PER_RADIUS", "SCAN_TIMEOUT_S",
    "NEXT_FRAME_TIMEOUT_S", "MOTION_TRIPS", "MOTION_DX", "MOTION_EPS", "SETTLE_S", "GOAL_TIMEOUT_S", "SERVER_CALLS", "POLL_S",
    "BUDGET_S", "MIN_FREE_GB", "CLIENT_ERR_RX")}


def parse_argv(argv, driver_file):
    """The driver takes no argument: the refusal text, or None for a bare call."""
    if argv:
        return f"{os.path.basename(driver_file)} takes no arguments; a bare call boots the session"
    return None


def new_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {},
            "readings": {"rates": {}, "scans": {}, "motion": [], "server": []},
            "world_changes": {"left_in_place": []}, "finished": False}


def driver_checks(driver_file, repo=REPO, git_say=None, git_dirty=None):
    """The driver's own pre-boot checks: its file name, the profile on disk, no committed artifact of its key (a
    driver that ran is frozen), the agent Lua and the driver committed clean. Returns (checks, ok)."""
    git_say = git_say or DL.C.git_say
    git_dirty = git_dirty or DL.C.git_dirty
    base = os.path.basename(driver_file)
    c = {"driver_file": base == DRIVER, "driver_prefix": base.startswith(KEY),
         "profile_exists": os.path.isfile(os.path.join(repo, PROFILE))}
    tracked = git_say("ls-files", "--", f"testing/artifacts/{KEY}-*")
    c["no_committed_artifact"] = tracked == ""
    c["agent_lua_dirty"] = git_dirty(AGENT_LUA)[0]
    c["driver_dirty"] = git_dirty(f"testing/agent/drivers/{DRIVER}")[0]
    ok = (c["driver_file"] and c["driver_prefix"] and c["profile_exists"] and c["no_committed_artifact"]
          and c["agent_lua_dirty"] is False and c["driver_dirty"] is False)
    return c, ok


def preboot(driver_file, repo=REPO):
    """_dlib.preboot (git provenance, doctor, harness Lua clean, the layout lint) and the driver's own checks."""
    pre, ok = DL.preboot(driver_file, os.path.join(repo, PROFILE))
    pre["driver_checks"], ok2 = driver_checks(driver_file, repo)
    return pre, bool(ok and ok2)


def _seq(v):
    if isinstance(v, dict):
        return list(v.values())
    return list(v or ())


def _bytes(line):
    return len(json.dumps(line, separators=(",", ":")).encode("utf-8"))


def state_bytes(d):
    """The total size of the state files in the state dir (bytes per minute = the window's difference)."""
    try:
        return sum(os.path.getsize(os.path.join(d, n)) for n in os.listdir(d)
                   if n.startswith("state") and n.endswith(".log"))
    except OSError:
        return None


class Pipe:
    """The four phases over one Link. `clock` and `sleep` are injectable (the offline FakeMod drives both)."""

    def __init__(self, xs, link, world=None, clock=time.time, sleep=time.sleep, bus_stats=DL.bus_stats,
                 poll_s=POLL_S):
        self.xs = xs
        self.out = xs.out
        self.rd = self.out.setdefault("readings", {"rates": {}, "scans": {}, "motion": [], "server": []})
        self.link = link
        self.world = world or World()
        self.clock = clock
        self.sleep = sleep
        self.bus_stats = bus_stats
        self.poll_s = poll_s
        self.frames = []          # (line, read PyMs)
        self.scans = []           # (line, read PyMs)
        self.hello = None
        self.missing = []
        self.events = {}
        self.lua_errors = []
        self.goal_end = {}        # goal seq -> its first done/failed frame (never lost to a batch read elsewhere)
        self.last_seq = 0

    # ---- reading the link
    def py_ms(self):
        return self.clock() * 1000.0

    def on_line(self, l):
        self.world.apply(l)
        self.last_seq = max(self.last_seq, l.get("seq", 0))
        now = self.py_ms()
        k = l.get("kind")
        if k == "frame":
            self.frames.append((l, now))
            g = l.get("goal") or {}
            if g.get("state") in ("done", "failed") and g.get("seq") not in self.goal_end:
                self.goal_end[g.get("seq")] = {"state": g.get("state"), "detail": g.get("detail"),
                                               "seq": l.get("seq"), "wallMs": l.get("wallMs")}
        elif k == "scan":
            self.scans.append((l, now))
        elif k == "hello" and self.hello is None:
            self.hello = l
        elif k == "event":
            ev = l.get("event")
            self.events[ev] = self.events.get(ev, 0) + 1
            if ev == "lua_error":
                self.lua_errors.append(l)
        for m in _seq(l.get("missing")):
            if m not in self.missing:
                self.missing.append(m)

    def pump(self):
        if not os.path.isdir(self.link.dir):      # cleared before the start; the Lua makes it on its first ticks
            return []
        lines = self.link.lines()
        for l in lines:
            self.on_line(l)
        return lines

    def wait_until(self, cond, timeout_s):
        """Pump until cond() holds (True) or timeout_s of the clock passes (False); every poll checks the budget."""
        t0 = self.clock()
        while True:
            self.pump()
            if cond():
                return True
            if self.clock() - t0 >= timeout_s:
                return False
            self.xs.check()
            self.sleep(self.poll_s)

    def await_ack(self, seq, timeout_s=ACK_TIMEOUT_S):
        self.wait_until(lambda: self.link.ack_of(seq) is not None, timeout_s)
        return self.link.ack_of(seq)

    def need_hello(self):
        if self.hello is None:
            raise RuntimeError("no hello line: the link never opened")

    def sync_out(self):
        self.out["missing"] = list(self.missing)
        self.out["gaps"] = [list(g) for g in self.link.gaps]
        self.out["bad"] = getattr(self.link, "bad", 0)
        self.out["lua_errors"] = len(self.lua_errors)
        self.out["lua_error_lines"] = self.lua_errors[:20]
        self.out["events"] = dict(self.events)
        self.out["lines_read"] = self.last_seq

    # ---- phase 1: rates
    def phase_rates(self):
        t0 = self.py_ms()
        self.wait_until(lambda: self.hello is not None, HELLO_TIMEOUT_S)
        self.out["hello_wait_ms"] = self.py_ms() - t0
        self.need_hello()
        self.out["hello"] = self.hello
        self.out["mode"] = self.hello.get("mode")
        for r in RATES:
            self.rd["rates"][str(r)] = self.rate_window(r)
            self.sync_out()
            self.xs.persist()

    def rate_window(self, r):
        sent = self.py_ms()
        seq = self.link.send("rate", str(r))
        row = {"rate": r, "cmdSeq": seq, "sentPyMs": sent, "expected": r * WINDOW_S, "window_s": WINDOW_S}
        ack = self.await_ack(seq)
        row["ack"] = ack
        if ack is None:
            row["error"] = "no ack"
            return row
        row["ackPyMs"] = self.py_ms()
        row["state_bytes_start"] = state_bytes(self.link.dir)
        t_end = self.clock() + WINDOW_S
        self.wait_until(lambda: self.clock() >= t_end, WINDOW_S + 1.0)
        row["state_bytes_end"] = state_bytes(self.link.dir)
        fr = [f for f, read in self.frames if f["seq"] > ack["seq"] and read <= t_end * 1000.0]
        costs = [f.get("cost") or {} for f in fr]
        row["frames"] = len(fr)
        for k in COST_KEYS:
            row[k] = [c.get(k) for c in costs]
        row["tickMs"] = [sum(c.get(k) or 0 for k in COST_KEYS) if all(c.get(k) is not None for k in COST_KEYS)
                         else None for c in costs]
        drops = [c.get("dropped") for c in costs if c.get("dropped") is not None]
        row["dropped_max"] = max(drops) if drops else None
        row["frame_wallMs_first"] = fr[0].get("wallMs") if fr else None
        row["frame_wallMs_last"] = fr[-1].get("wallMs") if fr else None
        return row

    # ---- phase 2: scans
    def phase_scans(self):
        self.need_hello()
        for r in SCAN_RADII:
            rows = self.rd["scans"].setdefault(str(r), [])
            for _ in range(SCANS_PER_RADIUS):
                rows.append(self.one_scan(r))
            self.sync_out()
            self.xs.persist()

    def one_scan(self, r):
        n0 = len(self.scans)
        seq = self.link.send("scan", str(r))
        row = {"r": r, "cmdSeq": seq, "sentPyMs": self.py_ms()}
        got = self.wait_until(lambda: len(self.scans) > n0 and self.link.ack_of(seq) is not None, SCAN_TIMEOUT_S)
        row["ack"] = self.link.ack_of(seq)
        if len(self.scans) <= n0:
            row["error"] = "no scan line"
            return row
        line, read = self.scans[n0]
        row.update({"scanMs": line.get("scanMs"), "squares": len(_seq(line.get("squares"))), "bytes": _bytes(line),
                    "missing": _seq(line.get("missing")), "seq": line.get("seq"), "wallMs": line.get("wallMs"),
                    "readPyMs": read, "acked": got})
        nf = self.next_frame(line["seq"], NEXT_FRAME_TIMEOUT_S)
        row["next_frame_senseMs"] = (nf.get("cost") or {}).get("senseMs") if nf else None
        return row

    def next_frame(self, after_seq, timeout_s):
        """The first frame with a seq above `after_seq`, waited for up to timeout_s; None when none came."""
        self.wait_until(lambda: bool(self.frames) and self.frames[-1][0]["seq"] > after_seq, timeout_s)
        return next((f for f, _ in self.frames if f["seq"] > after_seq), None)

    # ---- phase 3: motion
    def phase_motion(self):
        self.need_hello()
        for trip in range(MOTION_TRIPS):
            for dx in MOTION_DX:
                self.rd["motion"].append(self.one_goto(trip, dx))
            self.sync_out()
            self.xs.persist()

    def one_goto(self, trip, dx):
        """`goto <x0+dx> <y0>` in world coordinates, x0 and y0 the latest frame's own values (str, unrounded)."""
        settle_t0 = self.py_ms()
        settled = self.wait_until(self.still, SETTLE_S)
        x0, y0 = self.world.me.get("x"), self.world.me.get("y")
        row = {"trip": trip, "dx": dx, "x0": x0, "y0": y0, "settled": settled, "settleMs": self.py_ms() - settle_t0}
        if not isinstance(x0, (int, float)) or not isinstance(y0, (int, float)):
            row["error"] = "no frame before the command: no x0, y0"
            return row
        args = "%s %s" % (str(x0 + dx), str(y0))
        i0 = len(self.frames)
        sent = self.py_ms()
        seq = self.link.send("goto", args)
        row.update({"args": args, "cmdSeq": seq, "sentPyMs": sent})
        ack = self.await_ack(seq)
        row["ack"] = ack
        if ack is not None and not ack.get("ok"):
            row["error"] = "refused: %s" % ack.get("reason")
            return row
        # the goal's end is taken from every frame on_line saw (Link.await_goal reads only the batch it pumps, so a
        # done frame read during the ack wait, followed by an idle frame, would be missed there)
        if self.wait_until(lambda: seq in self.goal_end, GOAL_TIMEOUT_S):
            row["goal"] = dict(self.goal_end[seq])
        else:
            row["goal"] = {"state": "timeout", "detail": "goal %d not finished in %ss" % (seq, GOAL_TIMEOUT_S)}
        row["donePyMs"] = self.py_ms()
        row["first_motion"] = None
        after = ack["seq"] if ack else 0
        sign = 1.0 if dx > 0 else -1.0
        for f, read in self.frames[i0:]:
            if f["seq"] > after and isinstance(f.get("x"), (int, float)) and (f["x"] - x0) * sign > MOTION_EPS:
                row["first_motion"] = {"seq": f["seq"], "wallMs": f.get("wallMs"), "x": f["x"], "readPyMs": read}
                break
        fm = row["first_motion"]
        # informational, not graded: the client's frame wallMs against this process's write time (same host, two
        # clocks); the graded figure is grades.cmd_motion_ms (ack wallMs to frame wallMs, the client's clock alone)
        row["cmd_motion_host_ms"] = (fm["wallMs"] - sent) if fm and isinstance(fm.get("wallMs"), (int, float)) else None
        return row

    def still(self):
        """The last two frames stand on the same x, y (a walk that runs on past its goal's done has ended)."""
        if len(self.frames) < 2:
            return False
        a, b = self.frames[-2][0], self.frames[-1][0]
        return a.get("x") is not None and (a.get("x"), a.get("y")) == (b.get("x"), b.get("y"))

    # ---- phase 4: server
    def phase_server(self):
        for i in range(SERVER_CALLS):
            t0 = self.py_ms()
            r = self.bus_stats(self.xs, USER)
            self.rd["server"].append({"i": i, "startPyMs": t0, "rttMs": self.py_ms() - t0, "ack": r.get("ack"),
                                      "wallMs": r.get("wallMs")})

    def phases(self):
        return [("rates", self.phase_rates), ("scans", self.phase_scans), ("motion", self.phase_motion),
                ("server", self.phase_server)]

    def run(self):
        for name, fn in self.phases():
            self.xs.run_phase(name, fn)
            self.sync_out()
        self.xs.persist()


def client_errors(consoles):
    """{user: [Lua error lines]} over each client's console.txt, the harness echo excluded, and their total."""
    import re
    rx, echo, never = re.compile(CLIENT_ERR_RX), re.compile(ECHO_RX), re.compile(r"(?!x)x")
    found, n = {}, 0
    for user, path in consoles:
        lines, _ = X.grep_noecho(path, rx, 80, echo, never)
        found[user] = lines
        n += len(lines)
    return found, n


def memory_gate(xs, wait=None):
    """The memory wait before the boot; a false result refuses. The wall budget's clock restarts after it, so a long
    wait never eats the session's budget; the readings stay under out["memory_wait"]."""
    ok, readings = (wait or DL.wait_memory)(MIN_FREE_GB)
    xs.out["memory_wait"] = readings
    if not ok:
        xs.refuse("blocked: memory")
    xs.t0 = xs.clock()
    return readings


def clearing_make_client(make):
    """pzt.session.make_client, then the stale pzagent/ folder removed before the client is started (the fixture
    snapshot copies the client's Lua/ folder; a kept ack.txt would make the Lua skip every seq up to it)."""
    def wrapped(*a, **kw):
        c, restored = make(*a, **kw)
        DL.clear_state_dir(c)
        return c, restored
    return wrapped


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
    pipe = None
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
            pipe = Pipe(xs, DL.link_for(clients, USER))
            pipe.run()
    except Exception as e:                                   # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            found, n = client_errors([(getattr(c, "username", "?"), c.console) for c in every])
            out["logs"] = {"patterns": {"client_error": CLIENT_ERR_RX}, "clients": found}
            out["client_lua_errors"] = n

        if pipe is not None:
            pipe.sync_out()
        xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs)
        xs.mem("after")
        out["finished"] = True
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)
    print(json.dumps({"run_id": run_id, "run_dir": run_dir, "error": out.get("error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "budget_stop": out.get("budget_stop"), "wall_seconds": out.get("wall_seconds")},
                     indent=1, default=str))
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main()
