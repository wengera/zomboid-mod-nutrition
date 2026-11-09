"""f_goals_20 -- the nineteenth LLM session's driver (Plan 34 Task 7a): `f_goals_19.py` copied under its own key for Plan 34's one evidence session, the LLM session of the composition the trials proved (Plan 33's composition: the ladder with the Dress maneuver on by default over the meet reflex, the facing snap, the coward switches `POINT_BLANK_FIGHT`, `PAIR_NEAREST`, `CARE_COMMIT` and `STRAIN_BOUND`, the window glass gate `GLASS_CLEAR`, the finish's head-step floor `K.HEAD_LOOK_FLOOR` and cap `K.HEAD_MAX_TICKS` with the `head_stall` handback and the `head_ticks` leaf, the idle snap `K.IDLE_SNAP`, and `CRAWLER_FIRST`, `GROUP_LEAVE`, `DRAG_GUARD_FIGHT` and `SIDE_CLEAR`; plus Plan 34's, all on by default and this driver sets nothing of them: the planner switches `LEAVE_CARE`, `DOOR_INSIDE`, `LEAVE_DOOR_RACE`, `RETREAT_GAP`, `RETREAT_MELEE`, `STRUNG_HOLD`, `CRAWLER_CLEAR`, `LEAVE_ENTRY`, `RETREAT_REGAIN`, `SPENT_LEAVE`, `DRAG_DEFER` and `RUN_HOLD`, `SHOVE_CLEAR` (the Lua's shove wait, PZA/1.12 `waited`), the melee reflex's hand-back under a hit reaction and the decision line's `frame_age`), the session armed as `f_goals_19.py` is (the library's kit phase spawns and equips the bat) on the fixture `agent` and the profile `agent` by day (as `f_goals_19.py` booted) and boots only after one live `-p` call answers (the pre-boot's probe the library's, `driverlib/probe.py`: `claude_available` and `claude_answers`, the call's time limit the goal source's `llm.LLM_TIMEOUT_S`): the base at `80a2fff5` (the planner: Plan 34's head at the copy, re-based before the boot) carries the protocol PZA/1.12 in the schema (the shove's and the stomp's `waited`; the Lua's `PZA.VERSION` is still "1.11", so the hello reads `mod` `1.11`), the facing ring on each frame, the control fork (`Survive(control=...)`, the ladder its default) and the Dress maneuver (one commitment from the stop to the dressing of one bleeding part, on by default since Plan 31; this driver sets nothing of it), the goal source with the view's `stall` line (P29-B: the target of a goal budget that never moved, which the goal prompt tells the model never to answer); the controller re-bases this sentence to the commit the session boots on. The planner is built exactly as `f_goals_4.py` builds it: `Survive(source=LLMSource(ScriptedSource(), ...))`, the `claude` CLI call, its timeout and the model unchanged. Its grade is `grade_x4` (agent.base.grades.x4: `grade_x3`'s readings under its `base`, plus the column readings, clipped at the loop's stop). In the session the grade reads the record and the state files; `f_grade_16.py` regrades with `decision.log` and `goals.log` beside the artifact.

The rest of this docstring is f_goals.py's, unchanged but for the stops and the grade's name: f_goals -- Plan 23 Task 16d, the LLM session driver: e_day.py's session (one session of a chained survival day on
the driver library) with the survivor's goals chosen by a model. One boot of the profile `agent` (PZTestKit + PZAgent,
one admin -debug client) on the fixture `--fixture` names (default `agent`), the survivor
`Survive(source=LLMSource(ScriptedSource()))` over the PZA/1 file channel, the server's reads off a `PollThread`
(P23-13). The LLMSource (`planner/llm.py`, P23-11, P23-V) runs the `claude` CLI (`DEFAULT_CLI`, model sonnet) on a
worker thread with LLM_TIMEOUT_S, the scripted source standing in for every late, malformed or unsafe answer; the
instincts above the goal branch pre-empt whatever goal runs. Each session's `grade_x4` (grades.x4: grade_x3's readings plus the column readings)
is written at its end.

The driver is thin: its key, artifact and profile, its LLM constants, its pre-boot checks (`claude_available` beside
the day's), its planner and its `llm` record. The day's constants, arguments, chain inputs, `Chain` (the library's
`Session` with the two hooks), its builder (`day.make_day_session`) and the boot (`day.boot_and_run`) are
`driverlib/day.py`'s, shared with e_day.py; the rest is the library's (`driverlib/session.py`'s
docstring). The LLMSource's worker is joined after the teardown (out["llm_joined"]; `after_teardown`), so no join
widens the gap between the last kept frame and the server's save, the gap the next session's lineage reads.

PHASES (driverlib.session): hello, damage_hook, kit, loop, as e_day.py's; `on_frame` keeps the session's first frame
for the lineage.
STOPS (out["stop"]): death, client_end (a `players` reply without the user with no death event and no zero-health
frame read before it: the client's end, `loop.end` {seq, health, players}, never a death; Plan 28 Task 1, 37a70a97),
bus_dead, lua_error_storm, memory, day_cap (the loop's wall time reaches DAY_CAP_S),
budget (BUDGET_S from the end of the memory gate), error.

THE RECORD: out["loop"] is record.loop_summary's (the action rows with `branch` and a consume's `use`) plus
`Chain.extra_record()`: `goals` (the runner's rows {type, args, state, reason, startS, endS, source}, `source` "llm"
for the model's goal and "scripted" for a stand-in), `night`, `lineage`, `t_loop0_ms` (e_day.py's docstring), and
  llm         {calls (LLMSource.calls, one row per collected call {wall, latency_s, ok, goal, error, prompt_bytes,
              model}, copies), model (DEFAULT_CLI's --model, "sonnet"), cli_version (`claude --version` read once
              in the pre-boot, out["preboot"]["claude_version"]; None when the CLI is absent)}.
`goals.log` (every call's row with its prompt and answer, one JSON line each, beside decision.log) is copied with the
artifact. out["chain"], out["preboot"]["chain_checks"] as e_day.py's; out["preboot"]["claude_available"] {found, path,
version, error, ok}; out["preboot"]["claude_answers"] {ok, exit, answer, latency_s, error}; out["grade_x4"] is grades.x4.grade_x4(out, state_dir=out["state_dir"], kind="f"), else out["grade_x4_error"]; out["finished"] last.

RULES: never edited after its run (the next pass is a new file); takes only `--session N` (an int >= 1, default 1),
`--fixture NAME` (default agent) and `--prev PATH` (the previous session's artifact JSON, optional), each once; one
live session at a time; free memory gated at MIN_FREE_GB before the boot; never -safemode; launched by the controller
and polled through the persisted artifact; the chain's snapshot between sessions is e_day.py's (`pzt snapshot
--from-run`, day.next_steps). An F session on the chain's last fixture (agent-s<n>, snapshotted off session n) is
given `--session <n+1>` and `--prev <the last chain artifact>` (session n's), or the pre-boot refuses it (P23-Z:
the fixture's record says session n); the day summary prints that line as `next.f_session`. The pre-boot checks
refuse a dirty agent Lua, agent base, driver library or driver, a committed artifact of this key, a fixture with no
record or cache (or an unreadable one), a --prev that does not read as an artifact carrying loop.last_frames, a
--session that does not follow the fixture's or the prev's session
(session_consistent False, ruling P23-Z), a `claude` CLI that is not on PATH or does not answer
`claude --version` (an F session without a model is not the reading) and a CLI whose live `-p` probe call does not
answer (`claude_answers`: the LLMSource's own `DEFAULT_CLI` argv with a one-line system prompt, one tiny call, read
once; out["preboot"]["claude_answers"] {ok, exit, answer, latency_s, error}). The model runs under Angus's own login.
Nothing is imported from a frozen driver but `xlib` (and `_dlib` through the library).
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import xlib as X                                      # noqa: E402,F401 - the provenance the RULES name
from agent.base.grades import x4 as GX4               # noqa: E402
from agent.base.planner import llm as L               # noqa: E402
from agent.base.planner.goals import ScriptedSource   # noqa: E402
from agent.base.planner.survive import Survive        # noqa: E402
from agent.driverlib import day as DY                 # noqa: E402
from agent.driverlib import probe as PR               # noqa: E402
from agent.driverlib import session as DS             # noqa: E402
from agent.driverlib.day import (BUDGET_S, DAMAGE_POLL_S, DAY_CAP_S, LIMITS, MIN_FREE_GB,  # noqa: E402,F401
                                 PLANNER_HZ, USER, flags, parse_argv)

KEY = "f_goals_20"
DRIVER = "f_goals_20.py"
ARTIFACT = "f_goals_20.json"
PROFILE = "testing/profiles/agent.toml"
LLM_TIMEOUT_S = L.LLM_TIMEOUT_S      # P23-11: a call answering later than this is a fallback (the goal source's own,
                                     # the probe's limit too: driverlib/probe.py)
GOALS_LOG = "goals.log"              # the LLMSource's log, beside decision.log
MODEL = L.model_of(L.DEFAULT_CLI)    # "sonnet"
NOT_PROBED = {"ok": False, "exit": None, "answer": None, "latency_s": None, "error": "not probed: no CLI"}
CONSTANTS = dict(DY.CONSTANTS, LLM_TIMEOUT_S=LLM_TIMEOUT_S)
REPO = DS.REPO
_ME = os.path.basename(os.path.abspath(__file__))


# ================================================================ pre-boot
def preboot(driver_file, args, repo=REPO, which=shutil.which, run=subprocess.run):
    """The library's pre-boot checks (DS.preboot), the chain's (DY.chain_checks) and the library's probe
    (`driverlib/probe.py`): `PR.claude_available` (its version stored as pre["claude_version"], None when the CLI is
    absent or does not answer) and `PR.claude_answers` (the live probe, made only when the CLI is found and answers
    `--version`, else NOT_PROBED; the boot is refused on its ok False)."""
    pre, ok = DS.preboot(driver_file, KEY, DRIVER, PROFILE, repo)
    pre["chain_checks"], ok2 = DY.chain_checks(args)
    ca = PR.claude_available(which, run)
    pre["claude_available"], pre["claude_version"] = ca, ca["version"]
    pre["claude_answers"] = PR.claude_answers(run=run, which=which) if ca["ok"] else dict(NOT_PROBED)
    return pre, bool(ok and ok2 and ca["ok"] and pre["claude_answers"]["ok"])


# ================================================================ the session
def planner_factory(runner=None):
    """The planner: Survive over the LLMSource, the scripted source its fallback, goals.log beside the decision log;
    `runner` the CLI's (None: llm._run, the real CLI; tests inject a fake)."""
    def planner(world, actions, log_path, clock):
        goals_log = os.path.join(os.path.dirname(log_path), GOALS_LOG)
        return Survive(world, actions, log_path, clock,
                       source=L.LLMSource(ScriptedSource(), log_path=goals_log, timeout_s=LLM_TIMEOUT_S, clock=clock,
                                          runner=runner))
    return planner


def llm_extra(cli_version):
    """The `llm` record key off the session's LLMSource: its calls (copies), the model and the CLI's version."""
    def extra(sess):
        src = sess.planner.goals.source
        return {"llm": dict(src.totals(), calls=[dict(c) for c in src.calls], model=MODEL, cli_version=cli_version)}
    return extra


def make_session(xs, transport, prev=None, cli_version=None, runner=None, **kw):
    """The day's Chain (day.make_day_session): the LLM planner, the `llm` record and goals.log copied; `kw` its clock,
    sleep, free, polls and limits."""
    return DY.make_day_session(xs, transport, planner_factory(runner), extra=llm_extra(cli_version),
                               copied=(GOALS_LOG,), prev=prev, **kw)


GRADE_KEY = "grade_x4"             # the key this driver's record carries its grade under


def grade_state(out):
    """grades.x4.grade_x4 over the record and the state files in out["state_dir"], an LLM session's (`kind` "f": the
    decision-log parts and the goals.log readings arrive with the regrade, f_grade_16.py)."""
    return GX4.grade_x4(out, state_dir=out.get("state_dir"), kind="f")


def grade(out):
    """out["grade_x4"] (grades.x4.grade_x4 over the record and the state files), else out["grade_x4_error"]."""
    DY.grade(out, GRADE_KEY, grade_state)


# ================================================================ the boot
LLM_JOIN_S = LLM_TIMEOUT_S + 5.0     # the worker's join after the teardown: the CLI's own timeout ends a call in flight


def run_session(xs, transport, prev, pre):
    """The session with the pre-boot's CLI version; returns it for after_teardown."""
    sess = make_session(xs, transport, prev, cli_version=pre.get("claude_version"))
    sess.run()
    return sess


def after_teardown(out, sess):
    """The LLMSource's worker joined after the teardown (out["llm_joined"]): a call still in flight ends by its
    subprocess timeout and its answer is never collected; None when no session ran."""
    if sess is None:
        return
    out["llm_joined"] = sess.planner.goals.source.join(LLM_JOIN_S)


def main(args, budget_s=BUDGET_S):
    return DY.boot_and_run(args, lambda: preboot(_ME, args), run_session, grade, key=KEY, driver=DRIVER,
                           artifact=ARTIFACT, profile=PROFILE, constants=CONSTANTS, grade_key=GRADE_KEY, user=USER,
                           budget_s=budget_s, min_free_gb=MIN_FREE_GB, after_teardown=after_teardown)


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main(flags(sys.argv[1:]))
