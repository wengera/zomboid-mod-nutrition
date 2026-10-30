"""e_day_11 -- Plan 24, the eleventh chain's session driver: `e_day_10.py` copied under its own key after the tenth chain's first session (`e_day_10-20261030-084253`, a survival of 227.5 game minutes with zero kills: 39 fights all fled, the stance flipping between seek and pull on seven aims running as a group came and went at the 12-tile listing edge, 63 fills of which 55 were rejected `no source` from water squares 60 to 159 tiles off, a stomp rejected `not valid` and one ended `stood`, and every shot taken through the window path); the base at `411dfc0e` carries PZA/1.7.1 (the hello reads `mod` `1.7`) and survival iteration 12 (over iteration 11: the arms' hold on the stiffness, `STIFF_HARD` and `STIFF_SOFT`, the arm pain its own reason `wounded` and a lone target still sought, P24-AT; the listing-edge hold, a zombie that left the listing held in the pull's reads for `EDGE_HOLD_TICKS` planner ticks, P24-AU; the stomp on the first fallen frame, a knock-down waited on, a `stood` stomp re-read and the finish refused for a chaser by the target, P24-AV; the fill sent only to a loaded source and a far one walked to first, P24-AW; the doorway's trigger logged as `doorway_pick` on every `many` line, P24-AX; the look behind skipping a fallen zombie, P24-AY) and the shot taker's window path (P24-AM: `shots.py` at `73f5ae42`, the client window's own content through `PrintWindow` when the screen grab is refused). Its grade is `grade_e8` (gates_e: `grade_e7`'s readings with three defects of E10's grade fixed, the wounded fight's strain flees read off the line's `inputs.nearest`, the fallen target's finish counted at its landing and the pull's fights named by their unit, plus the hold's kinds, the edge hold, the stomp on the first fallen frame, the fills and `doorway_pick`; the library has no `grade_day_8`, so the driver carries the grade call under `GRADE_KEY` `grade_e8`), and the run copy carries every state-log rotation (`state.1.log` ...). Every
other line is e_day_10.py's: the thin driver imports the library's `day` module, so the behaviour is the library's at
the boot.

The driver is thin: its key, artifact and profile, its pre-boot checks and its planner. The day's constants,
arguments, chain inputs, `Chain` (the library's `Session` with the two hooks), its builder (`day.make_day_session`) and
the boot (`day.boot_and_run`) are `driverlib/day.py`'s, shared with f_goals.py; the rest is the library's, documented
in `driverlib/session.py`'s docstring.

PHASES (driverlib.session, each through xs.run_phase; a phase's fault lands under out["phase_errors"][name]; each
reading at out["readings"][phase]):
  hello        the hello line (proto PZA/1, mode append) and a first frame; a failed hello skips the rest.
  damage_hook  `damage.watch USER` once, before the kit.
  kit          a weapon already held is kept and equipped (a chain's later session: no spawn); else KIT through
               xs.spawn; Equip awaited, a frame wielding it.
  loop         every POLL_S: the transport pumped into World and Actions; at PLANNER_HZ the planner's tick; the server's
               stats.all and players every SERVER_POLL_S and damage.watch since every DAMAGE_POLL_S, each run on the
               PollThread and merged by the loop when newer; every PERSIST_S out["loop"] rebuilt and persisted;
               at every stop the character stopped (a Stop pumped to its act line) before the teardown.
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
              LINEAGE_TOL (ruling P23-Y, amended: worldAge 0 to 3 game minutes on, one-sided; each stat 0.005,
              position 0.5, health 0.01, the inventory count equal; gameMin reported, never banded); None for a
              chain's first session;
  t_loop0_ms  the loop's start in epoch ms on this host's clock, the frames' wallMs base (gates_e.frame_times).
out["chain"] {session, fixture_arg (the fixture booted), profile_fixture (the profile's own `fixture`, reported
beside it), prev (the path), commit (the tree's)}; out["preboot"]["chain_checks"] (day.chain_checks: {fixture,
fixture_ok, fixture_error, fixture_session, prev, prev_ok, prev_error, prev_frames, prev_session, session,
session_consistent}); out["grade_e8"] is gates_e.grade_e8(out, state_dir=out["state_dir"]) (grade_e7's readings over every frame of the session's state files, plus the iteration 12 readings that need only the state files and the shots index; the decision-log parts arrive with the regrade; its lineage the record's
loop.lineage, read off the session's first frame), else out["grade_e8_error"]; out["finished"] is set last.

Clocks: a line's wallMs is the client's clock (ms); `*S` keys are this process's clock in seconds since the loop
began (goals and night: since the planner's creation); the same host's epoch throughout.

RULES: never edited after its run (the next pass is a new file); takes only `--session N` (an int >= 1, default 1),
`--fixture NAME` (default agent; the profile's mods, ini and verify rows used as they are) and `--prev PATH` (the
previous session's artifact JSON, optional), each once; one live session at a time; free memory gated at MIN_FREE_GB
before the boot; never -safemode; launched by the controller and polled through the persisted artifact. The chain:
after each session the controller snapshots its run into the next session's fixture with `pzt snapshot --from-run
<run dir> --name agent-s<n> --parent <this fixture> --session <n>` (day.next_steps; the summary prints it, and
`pzt snapshot` refuses an existing fixture or the parent), then boots `e_day.py --session <n+1> --fixture agent-s<n>
--prev <this artifact>`. The pre-boot checks refuse a dirty agent
Lua, agent base, driver library or driver, a committed artifact of this key, a fixture with no record or cache (or
an unreadable one), a --prev that does not read as an artifact carrying loop.last_frames and a --session that does
not follow the fixture's or the prev's session (session_consistent False, ruling P23-Z). out["teardown_started_wall"]
is this host's epoch seconds as the teardown begins (day.boot_and_run). Nothing is imported
from a frozen driver but `xlib` (and `_dlib` through the library).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import xlib as X                                      # noqa: E402,F401 - the provenance the RULES name
from agent.base.planner.goals import ScriptedSource   # noqa: E402
from agent.base.planner.survive import Survive        # noqa: E402
from agent.driverlib import day as DY                 # noqa: E402
from agent.driverlib import session as DS             # noqa: E402
from agent.driverlib.day import (ALLOWED, BUDGET_S, CONSTANTS, DAMAGE_POLL_S, DAY_CAP_S,  # noqa: E402,F401
                                 DEFAULT_FIXTURE, LIMITS, MIN_FREE_GB, PLANNER_HZ, USER, Chain, flags, parse_argv)

KEY = "e_day_11"
DRIVER = "e_day_11.py"
ARTIFACT = "e_day_11.json"
PROFILE = "testing/profiles/agent.toml"
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


def make_session(xs, transport, prev=None, **kw):
    """The day's Chain (day.make_day_session) with the driver's planner; `kw` its clock, sleep, free, polls and
    limits."""
    return DY.make_day_session(xs, transport, planner, prev=prev, **kw)


def run_session(xs, transport, prev, pre):
    sess = make_session(xs, transport, prev)
    sess.run()
    return sess


GRADE_KEY = "grade_e8"            # the key this driver's record carries its grade under (the library has GRADE_KEY and GRADE_KEY_6)


def grade_state(out):
    """gates_e.grade_e8 over the record and the state files in out["state_dir"]."""
    return DY.GE.grade_e8(out, state_dir=out.get("state_dir"))


def grade(out):
    """out["grade_e8"] (gates_e.grade_e8 over the record and the state files), else out["grade_e8_error"]."""
    DY.grade(out, GRADE_KEY, grade_state)


# ================================================================ the boot
def main(args, budget_s=BUDGET_S):
    return DY.boot_and_run(args, lambda: preboot(_ME, args), run_session, grade, key=KEY, driver=DRIVER,
                           artifact=ARTIFACT, profile=PROFILE, constants=CONSTANTS, grade_key=GRADE_KEY, user=USER,
                           budget_s=budget_s, min_free_gb=MIN_FREE_GB)


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main(flags(sys.argv[1:]))
