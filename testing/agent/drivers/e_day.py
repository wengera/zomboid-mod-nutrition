"""e_day -- Plan 23 Task 16c, the chain's session driver: one session of a chained survival day on the driver library
(`testing/agent/driverlib/`), the first driver built on it. One boot of the profile `agent` (PZTestKit + PZAgent, one
admin -debug client) on the fixture `--fixture` names (default `agent`; a chain's later session boots the fixture the
controller snapshotted off the last one's run), the scripted survivor `Survive(source=ScriptedSource())` over the PZA/1
file channel, the server's reads off a `PollThread` (P23-13: no server read stalls the planner). A chain of these
sessions is graded by `gates_e.gate_e1` over its artifacts in order; each session's `grade_e1` is written at its end.

The driver is thin: its constants, its arguments, its pre-boot checks, `Chain` (the library's `Session` with the two
hooks) and its boot. Everything else is the library's, documented in `driverlib/session.py`'s docstring.

PHASES (driverlib.session, each through xs.run_phase; a phase's fault lands under out["phase_errors"][name]; each
reading at out["readings"][phase]):
  hello        the hello line (proto PZA/1, mode append) and a first frame; a failed hello skips the rest.
  damage_hook  `damage.watch USER` once, before the kit.
  kit          KIT through xs.spawn, Equip awaited, a frame wielding it.
  loop         every POLL_S: the transport pumped into World and Actions; at PLANNER_HZ the planner's tick; the server's
               stats.all and players every SERVER_POLL_S and damage.watch since every DAMAGE_POLL_S, each run on the
               PollThread and merged by the loop when newer; every PERSIST_S out["loop"] rebuilt and persisted.
  `on_frame` keeps the session's first frame (a frame row, read in the hello phase) for the lineage.
STOPS (out["stop"] {reason, detail, wallS, gameMin, worldAge}, the first that holds): death, bus_dead,
lua_error_storm, memory, day_cap (the loop's wall time reaches DAY_CAP_S), budget (BUDGET_S from the end of the memory
gate), error; a death writes out["loop"]["death"] (record.death_record).

THE RECORD: out["loop"] is record.loop_summary's (actions [{aid, type, args, state, reason, sentS, endedS, branch,
use on a consume}] with `branch` the decision line that sent each action (Survive.last_branch) and `use` the consumed
item's use off World.by_use() at the send, fights, needs, needs_pairs, last_frames (the last LAST_FRAMES frames),
cost, damage, first_game_min, game_min, polls_joined, poll_errors, ...) plus `Chain.extra_record()`, the keys of
task-15-amendments.md:
  goals       the goal runner's rows {type, args, state, reason, startS, endS, source}, every goal that ended and the
              running one (state "running", endS None); startS/endS seconds from the runner's creation;
  night       {wants (the ticks the night branch wanted), steps [{step, building, aid, state, reason, startS, endS}],
              sleeps [{aid, state, reason, result, startS, endS, fatigueBefore, fatigueAfter, sleptH, bedType}]};
  lineage     with --prev, chain.lineage_diff(the previous artifact, this session's first frame): its last kept frame
              (loop.last_frames[-1]) against the first frame, each quantity {prev, now}, ok within LINEAGE_TOL; None
              for a chain's first session;
  t_loop0_ms  the loop's start in epoch ms on this host's clock, the frames' wallMs base (gates_e.frame_times).
out["chain"] {session, fixture_arg (the fixture booted), profile_fixture (the profile's own `fixture`, reported
beside it), prev (the path), commit (the tree's)}; out["preboot"]["chain_checks"] {fixture, fixture_ok,
fixture_error, prev, prev_ok, prev_error}; out["grade_e1"] is gates_e.grade_e1(out) (its lineage the record's
loop.lineage, read off the session's first frame), else out["grade_e1_error"]; out["finished"] is set last.

Clocks: a line's wallMs is the client's clock (ms); `*S` keys are this process's clock in seconds since the loop
began (goals and night: since the planner's creation); the same host's epoch throughout.

RULES: never edited after its run (the next pass is a new file); takes only `--session N` (an int >= 1, default 1),
`--fixture NAME` (default agent; the profile's mods, ini and verify rows used as they are) and `--prev PATH` (the
previous session's artifact JSON, optional), each once; one live session at a time; free memory gated at MIN_FREE_GB
before the boot; never -safemode; launched by the controller and polled through the persisted artifact. The chain:
after each session the controller snapshots its run into the next session's fixture with `pzt snapshot --from-run
<run dir> --name <next> --parent <this fixture> --session <n>` (chain.snapshot_cmd; the summary prints it), then
boots `e_day.py --session <n+1> --fixture <next> --prev <this artifact>`. The pre-boot checks refuse a dirty agent
Lua, agent base, driver library or driver, a committed artifact of this key, a fixture with no record or cache and a
--prev that does not read as an artifact. Nothing is imported from a frozen driver but `_dlib` and `xlib`.
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
from agent.base import gates_e as GE                  # noqa: E402
from agent.base.planner.goals import ScriptedSource   # noqa: E402
from agent.base.planner.survive import Survive        # noqa: E402
from agent.base.transport.files import FileTransport  # noqa: E402
from agent.driverlib import chain as CH               # noqa: E402
from agent.driverlib import session as DS             # noqa: E402
from agent.driverlib.polls import PollThread          # noqa: E402
from pzt import fixture as fx                         # noqa: E402

KEY = "e_day"
DRIVER = "e_day.py"
ARTIFACT = "e_day.json"
PROFILE = "testing/profiles/agent.toml"
USER = "admin"
BUDGET_S = 1200.0                    # the wall budget from the end of the memory gate, the boot included
DAY_CAP_S = 840                      # the loop's own wall time
PLANNER_HZ = 2
DAMAGE_POLL_S = 5
MIN_FREE_GB = DS.DEFAULTS["MIN_FREE_GB"]
LIMITS = {"DAY_CAP_S": DAY_CAP_S, "PLANNER_HZ": PLANNER_HZ, "DAMAGE_POLL_S": DAMAGE_POLL_S}
CONSTANTS = dict(DS.DEFAULTS, **LIMITS, BUDGET_S=BUDGET_S)
ALLOWED = ("--session", "--fixture", "--prev")
DEFAULT_FIXTURE = "agent"
REPO = DS.REPO
_ME = os.path.basename(os.path.abspath(__file__))


# ================================================================ arguments
def parse_argv(argv, driver_file):
    """The one-line refusal of anything but ALLOWED (each once, with one value) and of a --session that is not an int
    >= 1, else None."""
    refusal = DS.parse_argv(argv, driver_file, ALLOWED)
    if refusal:
        return refusal
    s = DS.parse_flags(argv, ALLOWED).get("--session")
    if s is not None and not (s.isdigit() and int(s) >= 1):
        return "%s: --session takes an int >= 1; refused: %s" % (os.path.basename(driver_file), " ".join(argv))
    return None


def flags(argv):
    """{session, fixture, prev} off an argv parse_argv accepted (the defaults 1, DEFAULT_FIXTURE, None)."""
    f = DS.parse_flags(argv, ALLOWED) or {}
    return {"session": int(f.get("--session", 1)), "fixture": f.get("--fixture", DEFAULT_FIXTURE),
            "prev": f.get("--prev")}


def load_prev(path):
    """(the previous session's artifact, None), or (None, why) when it does not read as one; (None, None) without a
    path."""
    if path is None:
        return None, None
    try:
        with open(path, encoding="utf-8") as fh:
            art = json.load(fh)
    except (OSError, ValueError) as e:
        return None, "%s: %s" % (type(e).__name__, e)
    if not isinstance(art, dict):
        return None, "not an artifact (a JSON %s): %s" % (type(art).__name__, path)
    return art, None


def chain_record(args, profile_fixture, commit):
    """out["chain"]: the session, the fixture booted beside the profile's own, the previous artifact's path and the
    tree's commit."""
    return {"session": args["session"], "fixture_arg": args["fixture"], "profile_fixture": profile_fixture,
            "prev": args["prev"], "commit": commit}


# ================================================================ pre-boot
def preboot(driver_file, args, repo=REPO):
    """The library's pre-boot checks (DS.preboot: _dlib's, the library's commit and the driver's own, a dirty library
    refused) and the chain's: the fixture's record and cache (fx.load), and --prev read as an artifact."""
    pre, ok = DS.preboot(driver_file, KEY, DRIVER, PROFILE, repo)
    cc = {"fixture": args["fixture"], "fixture_ok": False, "fixture_error": None, "prev": args["prev"],
          "prev_ok": None, "prev_error": None}
    try:
        fx.load(args["fixture"])
        cc["fixture_ok"] = True
    except SystemExit as e:                      # fx.load names a missing record or cache by SystemExit
        cc["fixture_error"] = str(e)
    if args["prev"] is not None:
        art, cc["prev_error"] = load_prev(args["prev"])
        cc["prev_ok"] = art is not None
    pre["chain_checks"] = cc
    return pre, bool(ok and cc["fixture_ok"] and cc["prev_ok"] is not False)


# ================================================================ the session
def planner(world, actions, log_path, clock):
    return Survive(world, actions, log_path, clock, source=ScriptedSource())


def goal_row(runner):
    """The running goal as a record row: its own row, startS from the runner's creation, endS None."""
    g = runner.current
    start = g.started_wall - runner.t0 if isinstance(g.started_wall, (int, float)) else None
    return dict(g.row(), startS=start, endS=None, source=getattr(runner.source, "NAME", None))


class Chain(DS.Session):
    """The library's Session with the chain's hooks: the first frame kept, the goals, the night, the lineage and the
    loop's start in the record."""

    def __init__(self, xs, transport, prev=None, **kw):
        self.prev = prev
        self.first_frame = None
        super().__init__(xs, transport, **kw)

    def on_frame(self, line):
        if self.first_frame is None:
            self.first_frame = DS.frame_row(line)

    def extra_record(self):
        p = self.planner
        goals = [dict(r) for r in p.goals.history]
        if p.goals.current is not None:
            goals.append(goal_row(p.goals))
        n = p.night
        return {"goals": goals,
                "night": {"wants": n.wants_n, "steps": [dict(r) for r in n.steps],
                          "sleeps": [dict(r) for r in n.sleeps]},
                "lineage": CH.lineage_diff(self.prev, self.first_frame) if self.prev is not None else None,
                "t_loop0_ms": self.t_loop0 * 1000.0 if self.t_loop0 is not None else None}


def make_session(xs, transport, prev=None, clock=time.time, sleep=time.sleep, free=X.free_gb, polls=None,
                 limits=None):
    """The driver's Chain: its planner, LIMITS (with `limits` laid over them) and a PollThread on `clock`."""
    return Chain(xs, transport, prev=prev, planner_factory=planner, clock=clock, sleep=sleep, free=free,
                 limits=dict(LIMITS, **(limits or {})), polls=polls if polls is not None else PollThread(clock))


def grade(out):
    """out["grade_e1"] (gates_e.grade_e1 over the record, its lineage loop.lineage), else out["grade_e1_error"]."""
    try:
        out["grade_e1"] = GE.grade_e1(out)
    except Exception as e:                               # noqa: BLE001 - the controller re-grades the artifact
        out["grade_e1_error"] = "%s: %s" % (type(e).__name__, e)


# ================================================================ the boot
def main(args, budget_s=BUDGET_S):
    from _common import ask, hard_kill                       # noqa: E402
    import x49b_lib as B                                     # noqa: E402
    from pzt import profile, session                         # noqa: E402
    from pzt.bus import resolve_side                         # noqa: E402
    from pzt.paths import new_run_dir                        # noqa: E402

    pre, ok = preboot(_ME, args)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    prof = profile.load(os.path.join(REPO, PROFILE))
    rec_fx = fx.load(args["fixture"])
    prev = load_prev(args["prev"])[0]
    run_id, run_dir = new_run_dir(KEY)
    tl = session.Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = DS.new_out()
    out["world_changes"]["restored"] = "fixture %s restored into the run dir" % args["fixture"]
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, user=USER)
    xs.path = os.path.join(run_dir, ARTIFACT)
    out.update({"run_id": run_id, "session_key": KEY, "driver": _ME, "user": USER, "profile": prof.report(),
                "preboot": pre, "argv": sys.argv[1:], "constants": CONSTANTS,
                "chain": chain_record(args, prof.fixture, DL.C.git_say("rev-parse", "--short", "HEAD")),
                "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                            "build": rec_fx.get("build"), "parent": rec_fx.get("parent"),
                            "session": rec_fx.get("session")},
                "driver_commit": DL.C.git_say("log", "-1", "--format=%h", "--", "testing/agent/drivers/" + DRIVER)})
    DS.memory_gate(xs, MIN_FREE_GB)
    xs.mem("preboot")
    xs.persist()
    try:
        out.update(DL.boot(xs, prof, rec_fx, run_dir, [USER], started, clients, holder,
                           make_client=DS.clearing_make_client(session.make_client)))
        xs.mem("ready")
        xs.persist()
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            out["state_dir"] = DL.state_dir(clients[USER])
            make_session(xs, FileTransport(DL.state_dir(clients[USER])), prev).run()
    except Exception as e:                                   # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = "%s: %s" % (type(e).__name__, e), traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            found, n = DS.count_parks([(getattr(c, "username", "?"), c.console) for c in every], xs.parked())
            out["logs"] = {"patterns": {"park": DS.DEFAULTS["PARK_RX"]}, "clients": found}
            out["frames"]["parks"] = n

        xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs)
        xs.mem("after")
        grade(out)
        out["finished"] = True
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)
    n = args["session"]
    print(json.dumps({"run_id": run_id, "run_dir": run_dir, "error": out.get("error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "budget_stop": out.get("budget_stop"), "stop": out.get("stop"), "chain": out.get("chain"),
                      "report": (out.get("grade_e1") or {}).get("report_lines"),
                      "snapshot_cmd": CH.snapshot_cmd(run_dir, "e_day-after-%d" % n, args["fixture"], n),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str))
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main(flags(sys.argv[1:]))
