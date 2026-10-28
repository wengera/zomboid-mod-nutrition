"""e_day -- Plan 23 Task 16c, the chain's session driver: one session of a chained survival day on the driver library
(`testing/agent/driverlib/`), the first driver built on it. One boot of the profile `agent` (PZTestKit + PZAgent, one
admin -debug client) on the fixture `--fixture` names (default `agent`; a chain's later session boots the fixture the
controller snapshotted off the last one's run), the scripted survivor `Survive(source=ScriptedSource())` over the PZA/1
file channel, the server's reads off a `PollThread` (P23-13: no server read stalls the planner). A chain of these
sessions is graded by `gates_e.gate_e1` over its artifacts in order; each session's `grade_e1` is written at its end.

The driver is thin: its constants, its pre-boot checks and its planner. The day's arguments, chain inputs, `Chain`
(the library's `Session` with the two hooks) and the boot (`day.boot_and_run`) are `driverlib/day.py`'s (moved there
by Task 16d, shared with f_goals.py); the rest is the library's, documented in `driverlib/session.py`'s docstring.

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
              (loop.last_frames[-1]) against the first frame, each quantity {prev, now, delta, tol, ok}, ok within
              LINEAGE_TOL (ruling P23-Y: gameMin 3.0, each stat 0.005, position 0.5, health 0.01, the inventory
              count equal); None for a chain's first session;
  t_loop0_ms  the loop's start in epoch ms on this host's clock, the frames' wallMs base (gates_e.frame_times).
out["chain"] {session, fixture_arg (the fixture booted), profile_fixture (the profile's own `fixture`, reported
beside it), prev (the path), commit (the tree's)}; out["preboot"]["chain_checks"] (day.chain_checks: {fixture,
fixture_ok, fixture_error, fixture_session, prev, prev_ok, prev_error, prev_frames, prev_session, session,
session_consistent}); out["grade_e1"] is gates_e.grade_e1(out) (its lineage the record's
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
Lua, agent base, driver library or driver, a committed artifact of this key, a fixture with no record or cache (or
an unreadable one) and a --prev that does not read as an artifact carrying loop.last_frames; a --session that does
not follow the fixture's or the prev's session is reported (session_consistent), never refused. Nothing is imported
from a frozen driver but `xlib` (and `_dlib` through the library).
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import xlib as X                                      # noqa: E402
from agent.base import gates_e as GE                  # noqa: E402
from agent.base.planner.goals import ScriptedSource   # noqa: E402
from agent.base.planner.survive import Survive        # noqa: E402
from agent.driverlib import day as DY                 # noqa: E402
from agent.driverlib import session as DS             # noqa: E402
from agent.driverlib.day import ALLOWED, DEFAULT_FIXTURE, Chain, flags, parse_argv   # noqa: E402,F401
from agent.driverlib.polls import PollThread          # noqa: E402

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
REPO = DS.REPO
_ME = os.path.basename(os.path.abspath(__file__))


# ================================================================ pre-boot
def preboot(driver_file, args, repo=REPO):
    """The library's pre-boot checks (DS.preboot: _dlib's, the library's commit and the driver's own, a dirty library
    refused) and the chain's (DY.chain_checks)."""
    pre, ok = DS.preboot(driver_file, KEY, DRIVER, PROFILE, repo)
    pre["chain_checks"], ok2 = DY.chain_checks(args)
    return pre, bool(ok and ok2)


# ================================================================ the session
def planner(world, actions, log_path, clock):
    return Survive(world, actions, log_path, clock, source=ScriptedSource())


def make_session(xs, transport, prev=None, clock=time.time, sleep=time.sleep, free=X.free_gb, polls=None,
                 limits=None):
    """The library's Chain with the driver's planner, LIMITS (with `limits` laid over them) and a PollThread on
    `clock`."""
    return Chain(xs, transport, prev=prev, planner_factory=planner, clock=clock, sleep=sleep, free=free,
                 limits=dict(LIMITS, **(limits or {})), polls=polls if polls is not None else PollThread(clock))


def run_session(xs, transport, prev, pre):
    make_session(xs, transport, prev).run()


def grade(out):
    """out["grade_e1"] (gates_e.grade_e1 over the record, its lineage loop.lineage), else out["grade_e1_error"]."""
    DY.grade(out, "grade_e1", GE.grade_e1)


# ================================================================ the boot
def main(args, budget_s=BUDGET_S):
    return DY.boot_and_run(args, lambda: preboot(_ME, args), run_session, grade, key=KEY, driver=DRIVER,
                           artifact=ARTIFACT, profile=PROFILE, constants=CONSTANTS, grade_key="grade_e1", user=USER,
                           budget_s=budget_s, min_free_gb=MIN_FREE_GB)


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main(flags(sys.argv[1:]))
