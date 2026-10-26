"""a_pipe_2 -- Plan 21 Stage A pass 2 (spec § 4.1): the pipe's go/no-go again, after pass 1 (run a_pipe-20261026-101003,
NO-GO). One boot of agent-nozombies (now on fixture `agent0`, provisioned with Zombies = 6; admin -debug, PZTestKit +
PZAgent); the agent sits still and the driver measures the file channel.

WHY A PASS 2 (testing/artifacts/a_pipe-20261026-101003/GUIDE.md, "Defect analysis" and "Pass-2 recommendation"):
  - the character was killed by zombies the `agent` fixture held mid-motion phase, and every later leg commanded a dead
    body: the profile moves to `agent0`, the Lua fails a dead player's goals with `dead`, and each leg here records the
    frame's health and nZombies so a leg on a hurt, attacked or dead character is voided rather than graded;
  - a dead body drifting reset the old position-change stuck count: goto's stuck now reads progress toward the target;
  - an r=15 scan cost 14-21 ms in one tick: the scan is now a chunked job (60 squares a tick, 17 ticks at r=15), its
    line carrying scanMs (the summed chunk ms) and scanTicks, and each frame's cost the tick's scanStepMs.

PHASES (each through xs.run_phase; a phase's fault is recorded and the next still runs). Pass 1's phases (a_pipe.py's
docstring) with these changes:
  rates   the hello wait also requires mode == "append" (anything else fails the phase) and records out["hello_build"];
          the per-frame cost lists add scanStepMs, and tickMs sums COST_KEYS (scanStepMs included).
  scans   each `scan r` is acked at once ("queued") and its line lands when its last chunk is done: the row records
          scanMs (the summed latency, ungraded), scanTicks, scanMsPerTick (the line's per-step ms list),
          scanStepMaxMs (its largest), scanMsMeanPerTick (scanMs / scanTicks) and the ack's reason; a line with no
          scanTicks is an error row (not the chunked scan). From the next frame: senseMs, scanStepMs and scanEmitMs
          (the completing tick's line emit and flush). grades.gate_a's scan gate reads the per-tick maximum.
  motion  each leg records at_send and at_end ({health, nZombies} of the latest frame before the write and at the
          goal's end), min_health and max_nZombies over the leg's frames. A leg is `voided` (with its reason) when
          health at the send reads 0 or less ("dead at send"), when any frame of the leg reads health below the send's
          ("health fell a -> b") or nZombies above 0 ("zombies n"); grades.gate_a leaves a voided leg out of the pairs
          and the count. Any voided leg on this zombie-free fixture is itself a finding (out["voided_legs"], a note).
  server  as pass 1.

Clocks: as pass 1 (a line's wallMs is the client's PZA.now(); a key ending in PyMs is this process's time.time() in ms).

RULES: never edited after its run (the next pass is a new file); takes no argument; one live session at a time; free
memory gated at MIN_FREE_GB before the boot; never -safemode. a_pipe.py is frozen and imported, never changed.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _dlib as DL                                    # noqa: E402
import xlib as X                                      # noqa: E402
from agent.drivers import a_pipe as AP                # noqa: E402  (Pipe and the boot seams; the frozen pass-1 file)

KEY = "a_pipe_2"
DRIVER = "a_pipe_2.py"
PROFILE = "testing/profiles/agent-nozombies.toml"
ARTIFACT = "a_pipe_2.json"
PASS1_RUN = "a_pipe-20261026-101003"
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
COST_KEYS = ("pollMs", "actMs", "scanStepMs", "senseMs", "linkMs")
AGENT_LUA = "testing/PZAgent"
CLIENT_ERR_RX = AP.CLIENT_ERR_RX

CONSTANTS = {k: globals()[k] for k in (
    "HELLO_TIMEOUT_S", "ACK_TIMEOUT_S", "RATES", "WINDOW_S", "SCAN_RADII", "SCANS_PER_RADIUS", "SCAN_TIMEOUT_S",
    "NEXT_FRAME_TIMEOUT_S", "MOTION_TRIPS", "MOTION_DX", "MOTION_EPS", "SETTLE_S", "GOAL_TIMEOUT_S", "SERVER_CALLS", "POLL_S",
    "BUDGET_S", "MIN_FREE_GB", "CLIENT_ERR_RX", "COST_KEYS", "PASS1_RUN")}


def parse_argv(argv, driver_file):
    """The driver takes no argument: the refusal text, or None for a bare call."""
    if argv:
        return f"{os.path.basename(driver_file)} takes no arguments; a bare call boots the session"
    return None


def new_out():
    out = AP.new_out()
    out["pass1_run"] = PASS1_RUN
    return out


def driver_checks(driver_file, repo=REPO, git_say=None, git_dirty=None):
    """The driver's own pre-boot checks: its file name, the profile on disk, no committed artifact of its key (a
    driver that ran is frozen), the agent Lua and the driver committed clean. Returns (checks, ok)."""
    git_say = git_say or DL.C.git_say
    git_dirty = git_dirty or DL.C.git_dirty
    base = os.path.basename(driver_file)
    c = {"driver_file": base == DRIVER, "driver_prefix": base.startswith(KEY),
         "profile_exists": os.path.isfile(os.path.join(repo, PROFILE))}
    c["no_committed_artifact"] = git_say("ls-files", "--", f"testing/artifacts/{KEY}-*") == ""
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


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def body_of(frame):
    """{health, nZombies} of a frame (None where the frame does not carry one)."""
    frame = frame or {}
    return {"health": _num(frame.get("health")), "nZombies": _num(frame.get("nZombies"))}


def void_reason(at_send, leg_frames):
    """Why a leg is voided, or None: dead at the send; health below the send's in any leg frame; any nZombies > 0
    (the send frame included). A missing reading never voids."""
    h0 = at_send.get("health")
    if h0 is not None and h0 <= 0:
        return "dead at send"
    bodies = [at_send] + [body_of(f) for f in leg_frames]
    hs = [b["health"] for b in bodies if b["health"] is not None]
    if h0 is not None and hs and min(hs) < h0:
        return "health fell %s -> %s" % (h0, min(hs))
    nz = [b["nZombies"] for b in bodies if b["nZombies"] is not None]
    if nz and max(nz) > 0:
        return "zombies %s" % max(nz)
    return None


class Pipe2(AP.Pipe):
    """Pass 1's Pipe with pass 2's readings. Every phase that reads a constant is overridden here, so the frozen
    module's constants never steer this driver."""

    def __init__(self, xs, link, world=None, clock=None, sleep=None, bus_stats=DL.bus_stats, poll_s=POLL_S):
        kw = {k: v for k, v in (("clock", clock), ("sleep", sleep)) if v is not None}
        super().__init__(xs, link, world=world, bus_stats=bus_stats, poll_s=poll_s, **kw)
        self.voided = 0

    # ---- phase 1: rates
    def phase_rates(self):
        t0 = self.py_ms()
        self.wait_until(lambda: self.hello is not None, HELLO_TIMEOUT_S)
        self.out["hello_wait_ms"] = self.py_ms() - t0
        self.need_hello()
        self.out["hello"] = self.hello
        self.out["mode"] = self.hello.get("mode")
        self.out["hello_build"] = self.hello.get("build")
        if self.out["mode"] != "append":
            raise RuntimeError("hello mode %r, not append" % (self.out["mode"],))
        for r in RATES:
            self.rd["rates"][str(r)] = self.rate_window(r)
            self.sync_out()
            self.xs.persist()

    def rate_window(self, r):
        sent = self.py_ms()
        seq = self.link.send("rate", str(r))
        row = {"rate": r, "cmdSeq": seq, "sentPyMs": sent, "expected": r * WINDOW_S, "window_s": WINDOW_S}
        ack = self.await_ack(seq, ACK_TIMEOUT_S)
        row["ack"] = ack
        if ack is None:
            row["error"] = "no ack"
            return row
        row["ackPyMs"] = self.py_ms()
        row["state_bytes_start"] = AP.state_bytes(self.link.dir)
        t_end = self.clock() + WINDOW_S
        self.wait_until(lambda: self.clock() >= t_end, WINDOW_S + 1.0)
        row["state_bytes_end"] = AP.state_bytes(self.link.dir)
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

    # ---- phase 2: scans (chunked)
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
        ms, ticks = _num(line.get("scanMs")), _num(line.get("scanTicks"))
        row.update({"scanMs": ms, "scanTicks": ticks, "squares": len(AP._seq(line.get("squares"))),
                    "bytes": AP._bytes(line), "missing": AP._seq(line.get("missing")), "seq": line.get("seq"),
                    "wallMs": line.get("wallMs"), "readPyMs": read, "acked": got,
                    "scanMsMeanPerTick": ms / ticks if ms is not None and ticks else None,
                    "scanMsPerTick": AP._seq(line.get("scanMsPerTick")) if line.get("scanMsPerTick") is not None
                    else None,
                    "scanStepMaxMs": _num(line.get("scanStepMaxMs"))})
        if ticks is None:
            row["error"] = "no scanTicks: not the chunked scan"
        nf = self.next_frame(line["seq"], NEXT_FRAME_TIMEOUT_S)
        cost = (nf.get("cost") or {}) if nf else {}
        row["next_frame_senseMs"] = cost.get("senseMs") if nf else None
        row["next_frame_scanStepMs"] = cost.get("scanStepMs") if nf else None
        # the completing tick's scan-line emit and flush, carried once on the first frame after the line
        row["scanEmitMs"] = _num(cost.get("scanEmitMs")) if nf else None
        return row

    # ---- phase 3: motion (voided legs)
    def phase_motion(self):
        self.need_hello()
        for trip in range(MOTION_TRIPS):
            for dx in MOTION_DX:
                self.rd["motion"].append(self.one_goto(trip, dx))
            self.sync_out()
            self.xs.persist()

    def latest_frame(self):
        return self.frames[-1][0] if self.frames else None

    def one_goto(self, trip, dx):
        """`goto <x0+dx> <y0>` in world coordinates, x0 and y0 the latest frame's own values (str, unrounded), with
        the character's health and nZombies at the send, over the leg and at its end, and the leg voided on a hurt,
        attacked or dead character."""
        settle_t0 = self.py_ms()
        settled = self.wait_until(self.still, SETTLE_S)
        x0, y0 = self.world.me.get("x"), self.world.me.get("y")
        row = {"trip": trip, "dx": dx, "x0": x0, "y0": y0, "settled": settled, "settleMs": self.py_ms() - settle_t0}
        if not isinstance(x0, (int, float)) or not isinstance(y0, (int, float)):
            row["error"] = "no frame before the command: no x0, y0"
            return row
        at_send = body_of(self.latest_frame())
        args = "%s %s" % (str(x0 + dx), str(y0))
        i0 = len(self.frames)
        sent = self.py_ms()
        seq = self.link.send("goto", args)
        row.update({"args": args, "cmdSeq": seq, "sentPyMs": sent, "at_send": at_send})
        ack = self.await_ack(seq, ACK_TIMEOUT_S)
        row["ack"] = ack
        refused = ack is not None and not ack.get("ok")
        if refused:
            row["error"] = "refused: %s" % ack.get("reason")
        else:
            if self.wait_until(lambda: seq in self.goal_end, GOAL_TIMEOUT_S):
                row["goal"] = dict(self.goal_end[seq])
            else:
                row["goal"] = {"state": "timeout", "detail": "goal %d not finished in %ss" % (seq, GOAL_TIMEOUT_S)}
        row["donePyMs"] = self.py_ms()
        leg = [f for f, _ in self.frames[i0:]]
        row["at_end"] = body_of(self.latest_frame())
        hs = [h for h in [at_send["health"]] + [body_of(f)["health"] for f in leg] if h is not None]
        nz = [n for n in [at_send["nZombies"]] + [body_of(f)["nZombies"] for f in leg] if n is not None]
        row["min_health"] = min(hs) if hs else None
        row["max_nZombies"] = max(nz) if nz else None
        why = void_reason(at_send, leg)
        if why is not None:
            row["voided"] = why
            self.voided += 1
        if refused:
            return row
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

    # ---- phase 4: server
    def phase_server(self):
        for i in range(SERVER_CALLS):
            t0 = self.py_ms()
            r = self.bus_stats(self.xs, USER)
            self.rd["server"].append({"i": i, "startPyMs": t0, "rttMs": self.py_ms() - t0, "ack": r.get("ack"),
                                      "wallMs": r.get("wallMs")})

    def sync_out(self):
        super().sync_out()
        self.out["voided_legs"] = self.voided
        note = "voided legs on the zombie-free fixture: %d (a finding)" % self.voided
        notes = [n for n in self.out["notes"] if not str(n).startswith("voided legs on the zombie-free fixture")]
        self.out["notes"] = notes + ([note] if self.voided else [])


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
    AP.memory_gate(xs)
    xs.mem("preboot")
    xs.persist()
    pipe = None
    try:
        out.update(DL.boot(xs, prof, rec_fx, run_dir, [USER], started, clients, holder,
                           make_client=AP.clearing_make_client(session.make_client)))
        xs.mem("ready")
        xs.persist()
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            out["state_dir"] = DL.state_dir(clients[USER])
            pipe = Pipe2(xs, DL.link_for(clients, USER))
            pipe.run()
    except Exception as e:                                   # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            found, n = AP.client_errors([(getattr(c, "username", "?"), c.console) for c in every])
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
                      "budget_stop": out.get("budget_stop"), "voided_legs": out.get("voided_legs"),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str))
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main()
