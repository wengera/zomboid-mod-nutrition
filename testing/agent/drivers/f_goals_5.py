"""f_goals_5 -- the fifth LLM session's driver: `f_goals_4.py` copied under its own key (Plan 25 Task 5) for the night: the same session on the fixture `agent-night` (`FIXTURE`; the profile `testing/profiles/agent-night.toml`, a copy of `agent.toml` naming it), a world provisioned with the sandbox `StartTime` 6 (9 PM) so the 90-minute day reaches `night` and `tired` within the session and the `Shelter` and `Rest` goals are exercised (F3 never saw `night` or `tired` true; the fixture itself is the controller's provisioning, `python testing/pzt provision`). `--fixture` defaults to `FIXTURE` here (`flags` is the library's with that default). the base at `d14e168f` carries PZA/1.7.1 (the hello reads `mod` `1.7`) and survival iteration 13 (over iteration 12: the corner under any hold, a missed shove followed by the swing at one in reach or the break through the gap from two, never a second shove within `SHOVE_REPEAT_S`, P25-A; a fallen zombie within `FINISH_R` stomped before a running attack's walk, P25-B; the endurance hold's strain flee walking with nobody within `DANGER_R` and released after `HOLD_SPAN_MIN` quiet game minutes, P25-C; a riding bandage holding a no-swing Fight's sends until it lands, P25-D; a doorway stand's stalled walk re-routed once through `reachable_adjacent`, then the plan dropped, P25-E; a chaser across a known fence waited for in the stance `FENCE_BACK_R` back, P25-F), the goal source at `f4b3aa11` (one `looted` rule for the view and the loot, the cooled refusal carried to the next prompt, an ExploreToward square measured from the calling view's position, the hold read in the view and one Rest clause for it) and the library at `73f5ae42` (the shot taker's window grab through `PrintWindow` when the screen grab is refused, P24-AM). The planner is built exactly as `f_goals_4.py` builds it: `Survive(source=LLMSource(ScriptedSource(), ...))`, the `claude` CLI call, its timeout and the model unchanged. Its grade is `grade_f6` (gates_f: `grade_f5`'s readings with the kills read off the act lines and the `zombie_dead` events; `grade_f5` stays beside it, unrun). In the session the grade reads the record and the state files; the decision-log and `goals.log` parts arrive with the regrade.

The rest of this docstring is f_goals.py's, unchanged: f_goals -- Plan 23 Task 16d, the LLM session driver: e_day.py's session (one session of a chained survival day on
the driver library) with the survivor's goals chosen by a model. One boot of the profile `agent` (PZTestKit + PZAgent,
one admin -debug client) on the fixture `--fixture` names (default `agent`), the survivor
`Survive(source=LLMSource(ScriptedSource()))` over the PZA/1 file channel, the server's reads off a `PollThread`
(P23-13). The LLMSource (`planner/llm.py`, P23-11, P23-V) runs the `claude` CLI (`DEFAULT_CLI`, model sonnet) on a
worker thread with LLM_TIMEOUT_S, the scripted source standing in for every late, malformed or unsafe answer; the
instincts above the goal branch pre-empt whatever goal runs. Each session's `grade_f6` (gates_f: grade_f5's readings with the kills off the act lines)
is written at its end.

The driver is thin: its key, artifact and profile, its LLM constants, its pre-boot checks (`claude_available` beside
the day's), its planner and its `llm` record. The day's constants, arguments, chain inputs, `Chain` (the library's
`Session` with the two hooks), its builder (`day.make_day_session`) and the boot (`day.boot_and_run`) are
`driverlib/day.py`'s, shared with e_day.py; the rest is the library's (`driverlib/session.py`'s
docstring). The LLMSource's worker is joined after the teardown (out["llm_joined"]; `after_teardown`), so no join
widens the gap between the last kept frame and the server's save, the gap the next session's lineage reads.

PHASES (driverlib.session): hello, damage_hook, kit, loop, as e_day.py's; `on_frame` keeps the session's first frame
for the lineage.
STOPS (out["stop"]): death, bus_dead, lua_error_storm, memory, day_cap (the loop's wall time reaches DAY_CAP_S),
budget (BUDGET_S from the end of the memory gate), error.

THE RECORD: out["loop"] is record.loop_summary's (the action rows with `branch` and a consume's `use`) plus
`Chain.extra_record()`: `goals` (the runner's rows {type, args, state, reason, startS, endS, source}, `source` "llm"
for the model's goal and "scripted" for a stand-in), `night`, `lineage`, `t_loop0_ms` (e_day.py's docstring), and
  llm         {calls (LLMSource.calls, one row per collected call {wall, latency_s, ok, goal, error, prompt_bytes,
              model}, copies), model (DEFAULT_CLI's --model, "sonnet"), cli_version (`claude --version` read once
              in the pre-boot, out["preboot"]["claude_version"]; None when the CLI is absent)}.
`goals.log` (every call's row with its prompt and answer, one JSON line each, beside decision.log) is copied with the
artifact. out["chain"], out["preboot"]["chain_checks"] as e_day.py's; out["preboot"]["claude_available"] {found, path,
version, error, ok}; out["grade_f6"] is gates_f.grade_f6(out, state_dir=out["state_dir"]), else out["grade_f6_error"]; out["finished"] last.

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
(session_consistent False, ruling P23-Z) and a `claude` CLI that is not on PATH or does not answer
`claude --version` (an F session without a model is not the reading). The model runs under Angus's own login.
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
from agent.base import gates_f as GF                  # noqa: E402
from agent.base.planner import llm as L               # noqa: E402
from agent.base.planner.goals import ScriptedSource   # noqa: E402
from agent.base.planner.survive import Survive        # noqa: E402
from agent.driverlib import day as DY                 # noqa: E402
from agent.driverlib import session as DS             # noqa: E402
from agent.driverlib.day import (BUDGET_S, DAMAGE_POLL_S, DAY_CAP_S, LIMITS, MIN_FREE_GB,  # noqa: E402,F401
                                 PLANNER_HZ, USER, parse_argv)

KEY = "f_goals_5"
DRIVER = "f_goals_5.py"
ARTIFACT = "f_goals_5.json"
FIXTURE = "agent-night"             # the fixture provisioned with StartTime 6 (9 PM); the default of --fixture here
PROFILE = "testing/profiles/agent-night.toml"
LLM_TIMEOUT_S = 20.0                 # P23-11: a call answering later than this is a fallback
GOALS_LOG = "goals.log"              # the LLMSource's log, beside decision.log
MODEL = L.model_of(L.DEFAULT_CLI)    # "sonnet"
CLAUDE_VERSION_TIMEOUT_S = 30
CONSTANTS = dict(DY.CONSTANTS, LLM_TIMEOUT_S=LLM_TIMEOUT_S)
REPO = DS.REPO
_ME = os.path.basename(os.path.abspath(__file__))


# ================================================================ pre-boot
def claude_available(which=shutil.which, run=subprocess.run):
    """{found, path, version, error, ok}: the `claude` CLI on PATH and `claude --version` answering (exit 0, a
    non-empty stdout), read once; the executable resolved as the LLMSource's own runner resolves it."""
    path = which("claude")
    r = {"found": path is not None, "path": path, "version": None, "error": None, "ok": False}
    if path is None:
        r["error"] = "claude not on PATH"
        return r
    try:
        proc = run([path, "--version"], capture_output=True, text=True, timeout=CLAUDE_VERSION_TIMEOUT_S)
    except Exception as e:                               # noqa: BLE001 - a CLI that cannot answer refuses the boot
        r["error"] = "%s: %s" % (type(e).__name__, e)
        return r
    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        r["error"] = "exit %s" % proc.returncode
    elif not out:
        r["error"] = "no version on stdout"
    else:
        r["version"], r["ok"] = out, True
    return r


def preboot(driver_file, args, repo=REPO, which=shutil.which, run=subprocess.run):
    """The library's pre-boot checks (DS.preboot), the chain's (DY.chain_checks) and claude_available, its version
    stored as pre["claude_version"] (None when the CLI is absent or does not answer)."""
    pre, ok = DS.preboot(driver_file, KEY, DRIVER, PROFILE, repo)
    pre["chain_checks"], ok2 = DY.chain_checks(args)
    ca = claude_available(which, run)
    pre["claude_available"], pre["claude_version"] = ca, ca["version"]
    return pre, bool(ok and ok2 and ca["ok"])


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


GRADE_KEY = "grade_f6"            # the key this driver's record carries its grade under


def grade_state(out):
    """gates_f.grade_f6 over the record and the state files in out["state_dir"] (the decision-log parts and the goals.log
    readings arrive with the regrade, f_grade_6.py)."""
    return GF.grade_f6(out, state_dir=out.get("state_dir"))


def grade(out):
    """out["grade_f6"] (gates_f.grade_f6 over the record and the state files), else out["grade_f6_error"]."""
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


def flags(argv):
    """The library's {session, fixture, prev} with `--fixture` defaulting to FIXTURE (agent-night), not the library's agent."""
    f = DY.flags(argv)
    if "--fixture" not in (DS.parse_flags(argv, DY.ALLOWED) or {}):
        f["fixture"] = FIXTURE
    return f


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main(flags(sys.argv[1:]))
