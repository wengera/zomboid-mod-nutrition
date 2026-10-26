"""a_pipe_4 -- Plan 21b Stage A pass 4: the pipe's go/no-go after pass 3 (run a_pipe_3-20261026-130558, NO-GO on
tick_p99_at5, scan15 and cmd_motion_p90), with the three changes the agent harness report's § 6 names, ordered by
Angus outside spec § 4.1's three-pass budget. One boot of agent-nozombies (fixture `agent0`; admin -debug, PZTestKit +
PZAgent); the agent sits still and the driver measures the file channel, then walks the motion legs.

WHY A PASS 4 (testing/artifacts/a_pipe_3-20261026-130558/GUIDE.md; the report's § 6):
  1. the tick gate on the 60 Hz mean: tick_p99_ms_at5 read 2 against < 2 on a 1 ms clock (every cost is a difference
     of two integer getTimestampMs readings, so one frame's tickMs is quantised to whole ms), while the rate-60
     window's mean read 0.482 ms over 1803 consecutive ticks (GUIDE § 2). grades.gate_a4 grades tick_mean_ms_at60
     < 1 ms instead and reports the p99 ungraded. A grade change only: the phases are pass 3's.
  2. 20-square scan parts: scan15 read 7 ms against < 5; 60-square parts read 3-7 ms a tick, the walk about 1 ms
     beside an emit of about 0.5 ms per KB plus about 0.5 ms a line, so a 20-square part projects to about 4.1-4.5
     ms peak (GUIDE § 1). A Lua change only (PZAgent_Sense.lua S.SCAN_SQUARES_PER_TICK = 20): an r=15 scan is now 49
     parts, one a tick; the scans phase and the scan15 gate are pass 3's.
  3. motion as ack to first position change: cmd_motion_p90_ms read 8130 against < 500, yet every walk started
     moving 77-180 ms after its ack; every +x leg's path leaves the agent0 house westward by its south door, so the
     first frame 0.2 tiles east of the start came 7.5-8.5 s in (GUIDE § 3). Each motion row now carries first_move
     (below), which grades.gate_a4 grades; first_motion, the directional reading, is kept beside it, ungraded.

PHASES (each through xs.run_phase; a phase's fault is recorded and the next still runs): pass 3's (a_pipe_3.py's
docstring: rates, rate60, scans, motion, server), unchanged but for the motion row's new key:
  first_move  the first frame with seq > ack.seq whose hypot(x - x0, y - y0) > MOVE_EPS_TILES (grades.MOVE_EPS_TILES,
              0.01 tiles; x0, y0 the settled position the row already records), as {seq, wallMs, x, y, readPyMs};
              None on a refused or unacked row, a row with no x0, y0, or a leg with no such frame. Any direction
              counts: a detour's first step is the walk responding. grades.cmd_move_ms is its wallMs minus the ack's,
              both the client's clock.

Clocks: as pass 1 (a line's wallMs is the client's PZA.now(); a key ending in PyMs is this process's time.time() in ms).

RULES: never edited after its run (the next pass is a new file); takes no argument; one live session at a time; free
memory gated at MIN_FREE_GB before the boot; never -safemode. a_pipe.py, a_pipe_2.py and a_pipe_3.py are frozen and
imported, never changed; the phases inherited from a_pipe_2 and a_pipe_3 read those files' own constants, named in
CONSTANTS here for the artifact. BUDGET_S is 800 s (ruling P21b-1).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _dlib as DL                                    # noqa: E402
import xlib as X                                      # noqa: E402
from agent import grades as G                         # noqa: E402
from agent.drivers import a_pipe as AP                # noqa: E402  (the frozen pass-1 file: the boot seams)
from agent.drivers import a_pipe_2 as AP2             # noqa: E402  (the frozen pass-2 file: Pipe2)
from agent.drivers import a_pipe_3 as AP3             # noqa: E402  (the frozen pass-3 file: Pipe3)

KEY = "a_pipe_4"
DRIVER = "a_pipe_4.py"
PROFILE = "testing/profiles/agent-nozombies.toml"
ARTIFACT = "a_pipe_4.json"
PASS3_RUN = "a_pipe_3-20261026-130558"
BUDGET_S = 800.0           # ruling P21b-1: pass 3's 560 s ran out after 19 of 20 legs; 800 s plus the boot is under 15 min
USER = "admin"
MIN_FREE_GB = AP3.MIN_FREE_GB
REPO = DL.REPO
_ME = os.path.basename(os.path.abspath(__file__))

MOVE_EPS_TILES = G.MOVE_EPS_TILES
AGENT_LUA = AP3.AGENT_LUA
CLIENT_ERR_RX = AP3.CLIENT_ERR_RX

CONSTANTS = {k: globals()[k] for k in ("MOVE_EPS_TILES", "BUDGET_S", "MIN_FREE_GB", "CLIENT_ERR_RX", "PASS3_RUN")}
CONSTANTS["inherited_from_a_pipe_3"] = {k: getattr(AP3, k) for k in (
    "RATE60", "RATE60_WINDOW_S", "RATE_BACK", "SCAN_RADII", "SCANS_PER_RADIUS", "SCAN_TIMEOUT_S", "NEXT_FRAME_TIMEOUT_S",
    "ACK_TIMEOUT_S", "COST_KEYS", "PASS2_RUN")}
CONSTANTS["inherited_from_a_pipe_2"] = {k: getattr(AP2, k) for k in (
    "HELLO_TIMEOUT_S", "RATES", "WINDOW_S", "MOTION_TRIPS", "MOTION_DX", "MOTION_EPS", "SETTLE_S", "GOAL_TIMEOUT_S",
    "SERVER_CALLS", "POLL_S")}


def parse_argv(argv, driver_file):
    """The driver takes no argument: the refusal text, or None for a bare call."""
    if argv:
        return f"{os.path.basename(driver_file)} takes no arguments; a bare call boots the session"
    return None


def new_out():
    out = AP3.new_out()
    out["pass3_run"] = PASS3_RUN
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


def _xy(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def first_move(frames, ack, x0, y0, eps=MOVE_EPS_TILES):
    """The first of `frames` ((frame, readPyMs) pairs) with seq > ack.seq whose position is more than eps tiles from
    (x0, y0) in any direction, as {seq, wallMs, x, y, readPyMs}; None with no ack, no x0/y0 or no such frame."""
    if not isinstance(ack, dict) or not ack.get("ok") or _xy(ack.get("seq")) is None:
        return None
    if _xy(x0) is None or _xy(y0) is None:
        return None
    after = ack["seq"]
    for f, read in frames:
        x, y = _xy(f.get("x")), _xy(f.get("y"))
        if f.get("seq", 0) > after and x is not None and y is not None and math.hypot(x - x0, y - y0) > eps:
            return {"seq": f["seq"], "wallMs": f.get("wallMs"), "x": x, "y": y, "readPyMs": read}
    return None


class Pipe4(AP3.Pipe3):
    """Pass 3's Pipe with each motion row's first_move beside its first_motion."""

    def one_goto(self, trip, dx):
        row = super().one_goto(trip, dx)
        row["first_move"] = first_move(self.frames, row.get("ack"), row.get("x0"), row.get("y0"))
        return row


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
            pipe = Pipe4(xs, DL.link_for(clients, USER))
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
                      "tick_mean_ms_at60": (out.get("readings", {}).get("rate60") or {}).get("tick_mean_ms_at60"),
                      "cmd_move_p90_ms": G.gate_a4(out).get("cmd_move_p90_ms"),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str))
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main()
