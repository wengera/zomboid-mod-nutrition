"""f_goals_6 -- the sixth LLM session's driver: `f_goals_4.py` copied under its own key (Plan 25 Task 5) for the weapon want: the same session on the fixture `agent` and the profile `agent`, but started unarmed. `KIT_WEAPON` is None: the kit phase sends no RCON `additem` of the bat and no `Equip` (F3's bat was held on every frame, so the want `weapon` of `LootBuilding` was never exercised); the phase records `readings.kit` as skipped and the survivor starts with what the fixture's character carries. the base at `d14e168f` carries PZA/1.7.1 (the hello reads `mod` `1.7`) and survival iteration 13 (P25-A to P25-F, as `f_goals_5.py` names them), the goal source at `f4b3aa11` and the library at `73f5ae42` (P24-AM). The planner is built exactly as `f_goals_4.py` builds it: `Survive(source=LLMSource(ScriptedSource(), ...))`, the `claude` CLI call, its timeout and the model unchanged; the session is the library's `Chain` but for `phase_kit` (`UnarmedChain`). Its grade is `grade_f6` (gates_f: `grade_f5`'s readings with the kills read off the act lines and the `zombie_dead` events); the weapon want's reading is the grade's own (`answers` by want). In the session the grade reads the record and the state files; the decision-log and `goals.log` parts arrive with the regrade.

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
import time

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
                                 PLANNER_HZ, USER, flags, parse_argv)

KEY = "f_goals_6"
DRIVER = "f_goals_6.py"
ARTIFACT = "f_goals_6.json"
KIT_WEAPON = None                    # the bat withheld: no RCON additem, no Equip (the library kit phase's KIT is the bat)
PROFILE = "testing/profiles/agent.toml"
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


class UnarmedChain(DY.Chain):
    """The day's Chain with a kit phase that withholds the weapon: with KIT_WEAPON None it sends no spawn and no Equip and
    records `readings.kit` {skipped, held (the id of a weapon the inventory already holds, else None), armed False, ok True,
    first_sight}; with a weapon named it is the library's phase."""

    def phase_kit(self):
        if KIT_WEAPON is not None:
            return super().phase_kit()
        r = {"skipped": "KIT_WEAPON is None: the bat is withheld", "spawn": None, "item": None, "equip": None,
             "weapon_frame": None, "armed": False, "ok": True}
        self.rd["kit"] = r
        r["first_sight"] = self.first_sight()
        r["held"] = self.held_weapon(None)


def make_session(xs, transport, prev=None, cli_version=None, runner=None, clock=None, sleep=None, free=None, polls=None,
                 limits=None, shots=None):
    """The day's UnarmedChain (day.make_day_session's Chain with the unarmed kit phase): the LLM planner, the `llm` record
    and goals.log copied; the clock, sleep, free memory read, polls, limits and shots as make_day_session takes them."""
    clock = clock if clock is not None else time.time
    return UnarmedChain(xs, transport, prev=prev, extra=llm_extra(cli_version), copied=(GOALS_LOG,),
                        planner_factory=planner_factory(runner), clock=clock,
                        sleep=sleep if sleep is not None else time.sleep, free=free if free is not None else X.free_gb,
                        limits=dict(DY.LIMITS, **(limits or {})),
                        polls=polls if polls is not None else DY.PollThread(clock),
                        shots=shots if shots is not None else DY.day_shots(xs, clock))


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


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main(flags(sys.argv[1:]))
