"""drivers/f_goals_10.py (Plan 26 Task 7b, the ninth LLM session's driver, f_goals_9.py copied under its own key on the night fixture `agent-night` and the profile `agent-night`, grade_f7 of agent.base.grades.f7 kept), offline: the driver is never invoked and the real
`claude` CLI is never called.

The static tests read its arguments (the day's `--session`, `--fixture`, `--prev`, through `driverlib/day.py`), its
constants and its imports; the pre-boot checks run against the real profile and throwaway fixture records (conftest's
`agent_fixture`, with the night fixture's record added), the CLI's presence and `claude --version` read through stubbed `which` and `run`. The loop runs
`f_goals.make_session` (the library's `Chain` with the driver's LLM planner, its `llm` record and `goals.log`) on
test_driverlib.py's DayMod and FakeBus (the library's own fakes, imported), the LLMSource's `runner` a fake (a goal
answered on the first call, a timeout on the second) and its worker thread run synchronously at its start
(`SyncThread`, the module's `threading` swapped for the test), so the run is deterministic on the fake clock."""
import json
import os
import re
import shutil
import subprocess
import threading
import types

import pytest

from agent.base.planner import llm as L
from agent.base.planner.goals import ScriptedSource
from agent.base.planner.survive import Survive
from agent.base.transport.files import FileTransport
from agent.driverlib import day as DY
from agent.driverlib import session as S
from agent.drivers import f_goals_9 as F1
from agent.drivers import f_goals_10 as F
from .test_driverlib import Clock, DayMod, FakeBus, FakeServer, InlinePolls

REPO = S.REPO
X = S.X


@pytest.fixture
def agent_fixture(agent_fixture):
    """conftest's throwaway fixture records with the night fixture's added: `--fixture` defaults to `agent-night` here."""
    shutil.copytree(agent_fixture / "agent", agent_fixture / "agent-night")
    return agent_fixture


# ================================================================ static: refusal, constants, imports
def test_the_driver_refuses_arguments_before_main():
    src = open(F.__file__, encoding="utf-8").read()
    i_ref = src.index("refusal = parse_argv(sys.argv[1:], __file__)")
    i_main = src.rindex("    main(flags(sys.argv[1:]))")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    me = F.__file__
    for bad in (["x"], ["--help"], ["--session"], ["--session", "0"], ["--session", "two"], ["--fixture"],
                ["--prev"], ["--session", "2", "--session", "3"], ["--model", "opus"], ["--session", "2", "x"]):
        r = F.parse_argv(bad, me)
        assert r and "f_goals_10.py" in r and "\n" not in r, bad
    for good in ([], ["--session", "2"], ["--fixture", "chain-1"], ["--prev", "a.json"],
                 ["--session", "3", "--fixture", "chain-2", "--prev", "testing/runs/f_goals_10-1/f_goals_10.json"]):
        assert F.parse_argv(good, me) is None, good
    assert F.flags([]) == {"session": 1, "fixture": "agent-night", "prev": None}      # --fixture defaults to FIXTURE
    assert F.flags(["--fixture", "chain-1"]) == {"session": 1, "fixture": "chain-1", "prev": None}
    assert F.flags(["--session", "2", "--prev", "a.json"]) == {"session": 2, "fixture": "agent-night", "prev": "a.json"}
    assert F.parse_argv is DY.parse_argv and F.flags is not DY.flags and F.FIXTURE == "agent-night"
    assert DY.flags([])["fixture"] == "agent"                                       # the library's default is untouched


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(F.__file__) == F.DRIVER == F.KEY + ".py" == "f_goals_10.py"
    assert (F.KEY, F.PROFILE, F.ARTIFACT) == ("f_goals_10", "testing/profiles/agent-night.toml", "f_goals_10.json")
    assert os.path.isfile(os.path.join(REPO, F.PROFILE)) and F.FIXTURE == "agent-night"
    assert (F.BUDGET_S, F.DAY_CAP_S, F.PLANNER_HZ, F.DAMAGE_POLL_S) == (1200.0, 840, 2, 5)
    assert F.LIMITS == {"DAY_CAP_S": 840, "PLANNER_HZ": 2, "DAMAGE_POLL_S": 5}
    assert F.CONSTANTS == dict(S.DEFAULTS, **F.LIMITS, BUDGET_S=1200.0, LLM_TIMEOUT_S=20.0)
    assert F.LLM_TIMEOUT_S == 20.0 == L.LLM_TIMEOUT_S
    assert F.MODEL == "sonnet" == L.model_of(L.DEFAULT_CLI)
    assert F.GOALS_LOG == "goals.log" and F.USER == "admin" and F.MIN_FREE_GB == S.DEFAULTS["MIN_FREE_GB"]
    assert F.LIMITS is DY.LIMITS and F.CONSTANTS == dict(DY.CONSTANTS, LLM_TIMEOUT_S=20.0)       # M-8


def test_nothing_is_imported_from_a_frozen_driver():
    src = open(F.__file__, encoding="utf-8").read()
    imports = [l.split("#")[0].strip() for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
    frozen = [l for l in imports if re.match(r"^(a_|b_|c_|d_|e_|p22|x4_|x5_)", l.split()[1].split(".")[-1])
              or "drivers" in l or l.split()[1] in ("agent.link", "agent.grades", "agent.grade_c", "agent.world",
                                                     "agent.policy")]
    assert frozen == [], frozen
    for need in ("import xlib as X", "from agent.driverlib import session as DS",
                 "from agent.driverlib import day as DY", "from agent.base.grades import f7 as GF",
                 "from agent.base.planner import llm as L",
                 "from agent.base.planner.survive import Survive",
                 "from agent.base.planner.goals import ScriptedSource"):
        assert need in imports, need
    assert "source=L.LLMSource(ScriptedSource()," in src and "timeout_s=LLM_TIMEOUT_S" in src
    assert "DY.make_day_session(xs, transport, planner_factory(runner)" in src and "copied=(GOALS_LOG,)" in src
    # the boot is the library's: driverlib/day.boot_and_run (its order tested in test_driverlib.py)
    assert "DY.boot_and_run(args, lambda: preboot(_ME, args), run_session, grade, key=KEY, driver=DRIVER," in src
    assert "grade_key=GRADE_KEY" in src and 'GRADE_KEY = "grade_f7"' in src and "GF.grade_f7(out, state_dir=out.get(" in src
    assert "DY.grade(out, GRADE_KEY, grade_state)" in src and F.GRADE_KEY == "grade_f7"
    assert "grade_f1" not in src and "grade_f2" not in src and "grade_f6" not in src and "gates_f" not in src and "GF.grade_f5" not in src
    assert 'cli_version=pre.get("claude_version")' in src
    doc = F.__doc__
    for word in ("RULES", "--session", "--fixture", "--prev", "never edited after its run", "goals.log", "llm",
                 "claude --version", "grade_f7", "LLMSource", "ScriptedSource", "day_cap"):
        assert word in doc, word
    # M-10: an F session on the chain's last fixture follows the chain's numbering (P23-Z)
    rules = doc[doc.index("RULES"):]
    assert "--session <n+1>" in rules and "--prev <the last chain artifact>" in rules and "P23-Z" in rules


def test_the_e_day_driver_shares_the_day_session_through_the_library():
    from agent.drivers import e_day as E
    assert E.Chain is DY.Chain and E.parse_argv is DY.parse_argv is F.parse_argv and E.flags is DY.flags is not F.flags
    assert E.ALLOWED == DY.ALLOWED and E.DY is F.DY is DY
    assert "boot_and_run" in E.main.__code__.co_names and "boot_and_run" in F.main.__code__.co_names


# ================================================================ claude_available, the pre-boot
class Proc:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


def test_claude_available_reads_the_cli_and_its_version_once():
    seen = []

    def run(argv, **kw):
        seen.append((argv, kw))
        return Proc("2.1.310 (Claude Code)\n")

    r = F.claude_available(which=lambda name: "C:/bin/claude.exe" if name == "claude" else None, run=run)
    assert r == {"found": True, "path": "C:/bin/claude.exe", "version": "2.1.310 (Claude Code)", "error": None,
                 "ok": True}
    assert seen == [(["C:/bin/claude.exe", "--version"], {"capture_output": True, "text": True, "timeout": 30})]
    r = F.claude_available(which=lambda name: None, run=run)
    assert r == {"found": False, "path": None, "version": None, "error": "claude not on PATH", "ok": False}
    assert len(seen) == 1                                                   # no CLI: nothing run
    r = F.claude_available(which=lambda name: "c", run=lambda argv, **kw: Proc("", 3))
    assert r["ok"] is False and r["found"] is True and r["version"] is None and r["error"] == "exit 3"
    r = F.claude_available(which=lambda name: "c", run=lambda argv, **kw: Proc("  \n", 0))
    assert r["ok"] is False and r["error"] == "no version on stdout"

    def boom(argv, **kw):
        raise subprocess.TimeoutExpired(argv, 30)

    r = F.claude_available(which=lambda name: "c", run=boom)
    assert r["ok"] is False and r["version"] is None and r["error"].startswith("TimeoutExpired")


def answering_run(version="2.1.310 (Claude Code)\n", probe=None):
    """A fake `run` for both pre-boot calls: `--version` answers the version, the probe call (`-p` in argv) `probe`."""
    probe = probe if probe is not None else Proc(json.dumps({"type": "result", "is_error": False, "result": "ok"}))

    def run(argv, **kw):
        if "-p" in argv:
            if isinstance(probe, BaseException):
                raise probe
            return probe
        return Proc(version)
    return run


def test_preboot_on_the_real_profile(agent_fixture, monkeypatch, tmp_path):
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (False, ""))
    real = S.DL.C.git_say
    tracked = {"v": ""}
    monkeypatch.setattr(S.DL.C, "git_say", lambda *a: tracked["v"] if a[0] == "ls-files" else real(*a))
    here = {"which": lambda name: "C:/bin/claude.exe", "run": answering_run()}
    pre, ok = F.preboot(F.__file__, F.flags([]), **here)
    assert ok, pre
    assert pre["profile"] == "agent-night" and pre["driver_checks"]["driver_file"] is True
    assert pre["driver_checks"]["driverlib_dirty"] is False and pre["driverlib_commit"]
    assert pre["chain_checks"] == DY.chain_checks(F.flags([]))[0] and pre["chain_checks"]["fixture"] == "agent-night"
    assert pre["chain_checks"]["fixture_ok"] is True and pre["chain_checks"]["prev_ok"] is None
    assert pre["claude_available"]["ok"] is True and pre["claude_version"] == "2.1.310 (Claude Code)"
    assert pre["claude_answers"]["ok"] is True and pre["claude_answers"]["answer"] == "ok"
    gone = {"which": lambda name: None, "run": here["run"]}
    pre, ok = F.preboot(F.__file__, F.flags([]), **gone)
    assert ok is False and pre["claude_available"]["found"] is False and pre["claude_version"] is None
    assert pre["claude_answers"]["ok"] is False and pre["claude_answers"]["exit"] is None      # not probed
    pre, ok = F.preboot(F.__file__, F.flags([]), which=here["which"], run=lambda argv, **kw: Proc("", 1))
    assert ok is False and pre["claude_version"] is None and pre["claude_answers"]["ok"] is False
    pre, ok = F.preboot(F.__file__, F.flags(["--fixture", "nope"]), **here)
    assert ok is False and pre["chain_checks"]["fixture_ok"] is False
    pre, ok = F.preboot(F.__file__, F.flags(["--prev", str(tmp_path / "gone.json")]), **here)
    assert ok is False and pre["chain_checks"]["prev_ok"] is False
    tracked["v"] = "testing/artifacts/f_goals_10-20261028-120000/f_goals_10.json"
    assert F.preboot(F.__file__, F.flags([]), **here)[1] is False
    tracked["v"] = ""
    assert F.preboot(os.path.join(os.path.dirname(F.__file__), "e_day.py"), F.flags([]), **here)[1] is False


def test_preboot_refuses_the_boot_when_the_live_probe_does_not_answer(agent_fixture, monkeypatch):
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (False, ""))
    real = S.DL.C.git_say
    monkeypatch.setattr(S.DL.C, "git_say", lambda *a: "" if a[0] == "ls-files" else real(*a))
    which = lambda name: "C:/bin/claude.exe"                                   # noqa: E731
    assert F.preboot(F.__file__, F.flags([]), which=which, run=answering_run())[1] is True
    # `--version` answers (claude_available ok) while the probe exits 1: the sixth session's rate limit
    pre, ok = F.preboot(F.__file__, F.flags([]), which=which, run=answering_run(probe=Proc("", 1)))
    assert ok is False and pre["claude_available"]["ok"] is True
    assert pre["claude_answers"]["ok"] is False and pre["claude_answers"]["error"] == "exit 1"
    pre, ok = F.preboot(F.__file__, F.flags([]), which=which,
                        run=answering_run(probe=subprocess.TimeoutExpired("claude", 20.0)))
    assert ok is False and pre["claude_answers"]["error"].startswith("TimeoutExpired")
    empty = Proc(json.dumps({"type": "result", "is_error": False, "result": ""}))
    assert F.preboot(F.__file__, F.flags([]), which=which, run=answering_run(probe=empty))[1] is False


# ================================================================ claude_answers, the live probe
def envelope(result="ok", is_error=False):
    return Proc(json.dumps({"type": "result", "is_error": is_error, "result": result}))


def test_claude_answers_is_ok_only_on_exit_0_with_a_result_text():
    seen = []

    def run(argv, **kw):
        seen.append((argv, kw))
        return envelope("ok")

    r = F.claude_answers(run=run)
    assert r["ok"] is True and r["exit"] == 0 and r["answer"] == "ok" and r["error"] is None
    assert isinstance(r["latency_s"], float) and r["latency_s"] >= 0
    assert set(r) == {"ok", "exit", "answer", "latency_s", "error"}
    assert len(seen) == 1                                                    # one call, read once
    argv, kw = seen[0]
    assert kw["input"] == F.PROBE_INPUT and kw["input"].strip() and kw["timeout"] == F.LLM_TIMEOUT_S == 20.0
    assert kw["capture_output"] is True and kw["text"] is True
    r = F.claude_answers(run=lambda argv, **kw: Proc("", 1))
    assert r["ok"] is False and r["exit"] == 1 and r["error"] == "exit 1" and r["answer"] is None
    r = F.claude_answers(run=lambda argv, **kw: Proc("rate limited", 1))
    assert r["ok"] is False and r["error"] == "exit 1; stdout: rate limited"

    def boom(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw["timeout"])

    r = F.claude_answers(run=boom)
    assert r["ok"] is False and r["exit"] is None and r["error"].startswith("TimeoutExpired")
    assert isinstance(r["latency_s"], float)
    for bad in (envelope(""), envelope("   \n"), Proc(json.dumps({"type": "result"}), 0),
                Proc(json.dumps({"result": 5}), 0), Proc("[1]", 0)):
        r = F.claude_answers(run=lambda argv, **kw: bad)
        assert r["ok"] is False and r["exit"] == 0 and r["error"] == "no result text", bad.stdout
    r = F.claude_answers(run=lambda argv, **kw: envelope("Credit balance is too low", is_error=True))
    assert r["ok"] is False and r["error"] == "cli error" and r["answer"] == "Credit balance is too low"
    for bad in (Proc("not json", 0), Proc("", 0)):
        r = F.claude_answers(run=lambda argv, **kw: bad)
        assert r["ok"] is False and r["error"] == "stdout is not JSON"


def test_a_refusal_names_its_cause_from_stderr_and_stdout_cut_to_200_characters():
    r = F.claude_answers(run=lambda argv, **kw: Proc("", 1, stderr="  Claude AI usage limit reached|1761\n"))
    assert r["ok"] is False and r["exit"] == 1 and r["answer"] is None
    assert r["error"] == "exit 1; stderr: Claude AI usage limit reached|1761"
    r = F.claude_answers(run=lambda argv, **kw: Proc("out text", 1, stderr="err text"))
    assert r["error"] == "exit 1; stderr: err text; stdout: out text"
    r = F.claude_answers(run=lambda argv, **kw: Proc("o" * 500, 1, stderr="e" * 500))
    assert r["error"] == "exit 1; stderr: %s; stdout: %s" % ("e" * 200, "o" * 200) and F.ERR_SNIPPET == 200
    r = F.claude_answers(run=lambda argv, **kw: Proc("", 7, stderr=None))
    assert r["error"] == "exit 7"
    r = F.claude_answers(run=lambda argv, **kw: Proc("", 1, stderr="rate limit"), which=lambda name: "c")
    assert r["error"].endswith("stderr: rate limit")


def test_the_probe_runs_the_cli_without_claudecode_and_through_the_injected_which(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("PZ_PROBE_KEEP", "kept")
    seen, asked = [], []
    which = lambda name: asked.append(name) or "C:/injected/claude.exe"          # noqa: E731
    r = F.claude_answers(run=lambda a, **kw: seen.append((a, kw)) or envelope("ok"), which=which)
    assert r["ok"] is True and asked == ["claude"]
    argv, kw = seen[0]
    assert argv[0] == "C:/injected/claude.exe" and argv[1:] == F.probe_argv()[1:]
    assert "CLAUDECODE" not in kw["env"] and kw["env"]["PZ_PROBE_KEEP"] == "kept"      # the rest is carried
    assert kw["env"] is not os.environ and os.environ.get("CLAUDECODE") == "1"        # the host's own is untouched
    # a which that finds nothing leaves the argv's own name, as the runner does
    F.claude_answers(run=lambda a, **kw: seen.append((a, kw)) or envelope("ok"), which=lambda name: None)
    assert seen[1][0][0] == "claude"


def test_preboot_passes_its_injected_which_to_the_probe(agent_fixture, monkeypatch):
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (False, ""))
    real = S.DL.C.git_say
    monkeypatch.setattr(S.DL.C, "git_say", lambda *a: "" if a[0] == "ls-files" else real(*a))
    monkeypatch.setenv("CLAUDECODE", "1")
    calls = []
    inner = answering_run()

    def run(argv, **kw):
        calls.append((argv, kw))
        return inner(argv, **kw)

    pre, ok = F.preboot(F.__file__, F.flags([]), which=lambda name: "D:/injected/claude.exe", run=run)
    assert ok is True and len(calls) == 2
    assert [c[0][0] for c in calls] == ["D:/injected/claude.exe"] * 2             # the version call and the probe
    assert "CLAUDECODE" not in calls[1][1]["env"]
    # a refusal's stderr reaches the record
    refusing = answering_run(probe=Proc("", 1, stderr="usage limit reached"))
    pre, ok = F.preboot(F.__file__, F.flags([]), which=lambda name: "c", run=refusing)
    assert ok is False and pre["claude_answers"]["error"] == "exit 1; stderr: usage limit reached"


def test_the_probe_argv_is_the_goal_sources_own_with_only_the_system_prompt_swapped():
    argv = F.probe_argv()
    cli = list(L.DEFAULT_CLI)
    assert len(argv) == len(cli)
    diff = [i for i, (a, b) in enumerate(zip(cli, argv)) if a != b]
    assert diff == [cli.index("--system-prompt") + 1]
    assert argv[diff[0]] == F.PROBE_SYSTEM == "Reply with the single word ok."
    for flag in ("-p", "--output-format", "json", "--model", "sonnet", "--tools", "", "--setting-sources",
                 "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
        assert flag in argv
    assert L.SYSTEM in cli and L.SYSTEM not in argv and L.DEFAULT_CLI == tuple(cli)    # the source's argv is untouched
    assert F.probe_argv(("claude", "-p", "--system-prompt", "x", "--model", "m")) == [
        "claude", "-p", "--system-prompt", F.PROBE_SYSTEM, "--model", "m"]
    # the argv the call runs is the probe's (the executable resolved as the LLMSource's runner resolves it)
    seen = []
    F.claude_answers(run=lambda a, **kw: seen.append(a) or envelope("ok"))
    assert seen[0][1:] == argv[1:]
    src = open(F.__file__, encoding="utf-8").read()
    assert "def claude_answers(cli=L.DEFAULT_CLI, run=subprocess.run, which=shutil.which):" in src and "probe_argv(cli)" in src


# ================================================================ the loop on the fake session
class SyncThread:
    """threading.Thread for the LLMSource's worker, run to its end at start(): the call is done before propose
    returns, so the run is deterministic on the fake clock."""

    def __init__(self, target, args=(), name=None, daemon=None):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)

    def is_alive(self):
        return False

    def join(self, timeout=None):
        return None


class Runner:
    """The fake CLI: the first call answers `answer` in an envelope, every later call times out."""

    def __init__(self, answer='{"type": "Rest", "seconds": 5}'):
        self.answer, self.calls = answer, []

    def __call__(self, argv, input, timeout, env):
        self.calls.append({"argv": argv, "input": input, "timeout": timeout})
        if len(self.calls) == 1:
            return Proc(json.dumps({"type": "result", "is_error": False, "result": self.answer}))
        raise subprocess.TimeoutExpired(argv, timeout)


def run_goals(tmp_path, monkeypatch, day_cap_s, runner=None, cli_version="2.1.310 (Claude Code)"):
    """One `f_goals.make_session` on DayMod and FakeBus with the fake runner and SyncThread; then the driver's
    grade."""
    monkeypatch.setattr(L, "threading", types.SimpleNamespace(Thread=SyncThread, Event=threading.Event))
    clock = Clock()
    sd = str(tmp_path / "sd")
    mod = DayMod(sd, clock)
    fb = FakeBus(mod)
    monkeypatch.setattr(S.DL, "time", types.SimpleNamespace(time=clock.now))
    out = S.new_out()
    xs = X.Xs(out, node=lambda side: side, server=FakeServer(mod), ask=fb.ask, clock=clock.now, sleep=mod.sleep,
              budget_s=1e9, user="admin", clients={"admin": types.SimpleNamespace(seen={})})
    xs.path = str(tmp_path / "f_goals_10.json")
    runner = runner if runner is not None else Runner()
    sess = F.make_session(xs, FileTransport(sd, clock=clock.now), cli_version=cli_version, runner=runner,
                          clock=clock.now, sleep=mod.sleep, free=lambda: 30.0, polls=InlinePolls(clock=clock.now),
                          limits={"DAY_CAP_S": day_cap_s})
    sess.run()
    out["frames"]["parks"] = 0
    F.grade(out)
    out["finished"] = True
    return types.SimpleNamespace(out=out, mod=mod, day=sess, xs=xs, runner=runner)


def test_the_llm_session_records_its_calls_its_goals_and_goals_log(tmp_path, monkeypatch):
    # deterministic on the fake clock, under P23-AC (fix wave P: a pending call holds the runner, the scripted source
    # stands in only on a recorded failure): call 1 started at 2.9 s (pending), the model's Rest 5 taken at 3.3 s;
    # it ends at 8.35 s, call 2 starts and times out at once, so a scripted ExploreToward stands in at 8.85 s; it
    # arrives at 9.35 s, call 3 times out, a scripted Rest 30 stands in at 9.85 s; it ends at 40.35 s, call 4 times
    # out and is collected at 40.85 s: four rows, one ok, three fallbacks
    r = run_goals(tmp_path, monkeypatch, day_cap_s=40)
    out, loop, s = r.out, r.out["loop"], r.day
    assert out["phase_errors"] == {} and out["stop"]["reason"] == "day_cap"
    assert isinstance(s, DY.Chain) and isinstance(s.planner, Survive)
    src = s.planner.goals.source
    assert isinstance(src, L.LLMSource) and isinstance(src.fallback, ScriptedSource)
    assert src.timeout_s == 20.0 and src.runner is r.runner and src.cli == L.DEFAULT_CLI
    assert src.log_path == os.path.join(str(tmp_path), "goals.log")
    llm = loop["llm"]
    assert llm["model"] == "sonnet" and llm["cli_version"] == "2.1.310 (Claude Code)"
    calls = llm["calls"]
    assert len(calls) == 4, calls
    assert calls[0]["ok"] is True and calls[0]["error"] is None and calls[0]["goal"] == {"type": "Rest", "seconds": 5}
    for c in calls[1:]:
        assert c["ok"] is False and c["error"] == "timeout" and c["goal"] is None
    assert calls == src.calls and calls[0] is not src.calls[0]                 # copies, never the source's own rows
    sources = [g["source"] for g in loop["goals"]]
    assert "llm" in sources and "scripted" in sources
    llm_goals = [g for g in loop["goals"] if g["source"] == "llm"]
    assert llm_goals[0]["type"] == "Rest" and llm_goals[0]["args"] == {"seconds": 5}
    log = (tmp_path / "goals.log").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(l) for l in log]
    assert [x["ok"] for x in rows] == [True, False, False, False] and rows[1]["error"] == "timeout"
    assert rows[0]["answer"] == '{"type": "Rest", "seconds": 5}' and rows[0]["prompt"] == r.runner.calls[0]["input"]
    assert "goals.log" in r.xs.copied and "decision.log" in r.xs.copied
    assert set(loop) >= {"goals", "night", "lineage", "t_loop0_ms", "llm", "actions"}
    persisted = json.loads((tmp_path / "f_goals_10.json").read_text(encoding="utf-8"))
    assert persisted["loop"]["llm"] == json.loads(json.dumps(llm))
    g = out["grade_f7"]
    assert "grade_f2" not in out and "grade_f2_error" not in out
    assert g["grade"] == "grade_f7" and g["survived"] is True
    assert all(g[k] == {"read": False} for k in ("open_views", "objects", "reasks"))     # no goals.log at the boot
    assert g["llm"]["calls"] == 4 and g["llm"]["ok"] == 1 and g["llm"]["fallbacks"] == 3
    assert g["llm"]["goals_by_type"].get("Rest", 0) >= 1
    assert "grade_f5" not in out and g["answers"]["read"] is False and g["latency"]["calls"] == 4   # state files only
    assert g["latency"]["timeouts"] == 3 and g["fallback"]["calls_fallbacks"] == 3
    json.dumps(out, allow_nan=False)


def test_the_llm_record_reads_a_missing_cli_version_as_none(tmp_path, monkeypatch):
    r = run_goals(tmp_path, monkeypatch, day_cap_s=5, cli_version=None)
    assert r.out["loop"]["llm"]["cli_version"] is None and r.out["loop"]["llm"]["model"] == "sonnet"


def test_run_session_returns_the_session_and_the_llm_worker_is_joined_after_the_teardown(monkeypatch):
    joins = []
    source = types.SimpleNamespace(join=lambda t: joins.append(t) or True)
    sess = types.SimpleNamespace(ran=False, planner=types.SimpleNamespace(goals=types.SimpleNamespace(source=source)))
    sess.run = lambda: setattr(sess, "ran", True)
    made = []

    def make(xs, transport, prev, cli_version=None):
        made.append((xs, transport, prev, cli_version))
        return sess

    monkeypatch.setattr(F, "make_session", make)
    xs = types.SimpleNamespace(out={})
    assert F.run_session(xs, "tr", "prev", {"claude_version": "2.1.310"}) is sess
    assert sess.ran is True and made == [(xs, "tr", "prev", "2.1.310")] and joins == []    # no join in the session
    out = {}
    F.after_teardown(out, sess)
    assert out == {"llm_joined": True} and joins == [25.0] and F.LLM_JOIN_S == 25.0
    F.after_teardown(out, None)                                               # no session ran: nothing joined
    assert joins == [25.0]
    src = open(F.__file__, encoding="utf-8").read()
    assert "after_teardown=after_teardown)" in src


def test_grade_records_a_grade_failure_rather_than_raising(monkeypatch):
    out = {"loop": {}}
    monkeypatch.setattr(F.GF, "grade_f7", lambda o, **kw: (_ for _ in ()).throw(ValueError("boom")))
    F.grade(out)
    assert out["grade_f7_error"] == "ValueError: boom" and "grade_f7" not in out and "grade_f6" not in out


# ================================================================ the copy of f_goals.py and the totals
def test_the_totals_reach_the_llm_record(tmp_path, monkeypatch):
    r = run_goals(tmp_path, monkeypatch, day_cap_s=40)
    llm = r.out["loop"]["llm"]
    calls = llm["calls"]
    assert llm["prompt_bytes_total"] == sum(c["prompt_bytes"] for c in calls) > 0
    assert llm["answer_bytes_total"] == sum(c["answer_bytes"] for c in calls)
    assert "answer_bytes_total" in llm and llm["model"] == "sonnet"


BASE_SENTENCE = (
    "the base at `b7c60bbd` (the planner: iteration 18 with its fix rounds P26-K2, P26-N2, P26-J2 and P26-L2a and Task 7d's P26-L1 and P26-L2) and `54489fe5` (the Lua's window action) carries PZA/1.7.1 (the hello reads "
    "`mod` `1.7`) and survival iteration 18 (over iteration 17: a window way out needs an inside square that can be "
    "stood on, P26-I; the window step stall-read at WINDOW_STALL_S and an interrupted end sent once more, P26-J; the "
    "doorway stand ending crowd at STAND_CROWD_N standing zombies within DANGER_R, P26-K; a crowd end with nobody "
    "inside taking the close, else the way out, P26-K2; and the Lua's window action ending `interrupted` when a hit "
    "clears its queue, P26-M), the goal source with the fourth round's readings (P26-F the objects, P26-G the open "
    "views, P26-H the re-asks, read by `grade_f7`); the controller re-bases this sentence to the commit the session "
    "boots on")

FLAGS_LINES = [
    "def flags(argv):",
    '    """The library\'s {session, fixture, prev} with `--fixture` defaulting to FIXTURE (agent-night), not the library\'s'
    ' agent."""',
    "    f = DY.flags(argv)",
    '    if "--fixture" not in (DS.parse_flags(argv, DY.ALLOWED) or {}):',
    '        f["fixture"] = FIXTURE',
    "    return f",
]


def test_the_driver_is_f_goals_9_py_copied_under_its_own_key_on_the_night_fixture():
    import difflib
    a, b = open(F1.__file__, encoding="utf-8").read(), open(F.__file__, encoding="utf-8").read()
    changed = [l for l in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
               if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    plus = [l[1:] for l in changed if l[0] == "+"]
    minus = [l[1:] for l in changed if l[0] == "-"]
    assert 'KEY = "f_goals_10"' in plus and 'DRIVER = "f_goals_10.py"' in plus and 'ARTIFACT = "f_goals_10.json"' in plus
    assert 'KEY = "f_goals_9"' in minus and 'DRIVER = "f_goals_9.py"' in minus and 'ARTIFACT = "f_goals_9.json"' in minus
    assert 'PROFILE = "testing/profiles/agent-night.toml"' in plus and 'PROFILE = "testing/profiles/agent.toml"' in minus
    assert any(l.startswith('FIXTURE = "agent-night"') for l in plus)
    assert minus.count("                                 PLANNER_HZ, USER, flags, parse_argv)") == 1
    assert plus.count("                                 PLANNER_HZ, USER, parse_argv)") == 1
    assert plus[0].startswith('"""f_goals_10 -- the ninth LLM session') and minus[0].startswith('"""f_goals_9 -- the eighth')
    # nothing else moves but the night: the key triple, the profile and fixture, the import, the first docstring
    # paragraph and the flags wrapper
    rest = [l for l in plus[1:] if l.strip() and not l.startswith(("KEY = ", "DRIVER = ", "ARTIFACT = ", "PROFILE = ",
                                                                  "FIXTURE = ", "                                 PLANNER_HZ"))]
    assert rest == FLAGS_LINES, rest
    assert len([l for l in minus if l.strip()]) == 6 and F.GRADE_KEY == F1.GRADE_KEY == "grade_f7" and F.GF is F1.GF
    # the probe, the pre-boot, the planner and the LLM constants are f_goals_9.py's, byte for byte
    for name in ("def claude_available", "def claude_answers"):
        end = a.index("\ndef ", a.index(name) + 1)
        assert a[a.index(name):end] in b, name
    head = "# ================================================================ pre-boot"
    assert a[a.index(head):a.index("def make_session")] == b[b.index(head):b.index("def make_session")]
    mark = "# ================================================================ the boot"
    boot = b[b.index(mark):]
    cut, end = boot.index("\n\ndef flags(argv):"), boot.index('\n\nif __name__ == "__main__":')
    assert boot[:cut] + boot[end:] == a[a.index(mark):]
    doc = F.__doc__
    assert doc.splitlines()[1] == "" and doc.splitlines()[2].startswith("The rest of this docstring is f_goals.py")
    assert BASE_SENTENCE in doc and "PZA/1.7.1" in doc and "Task 7b" in doc and "f_goals_9.py" in doc
    assert "agent-night" in doc and "StartTime" in doc and "9 PM" in doc and "f_goals_5.py" in doc
    assert "boots only after one live `-p` call answers" in doc.splitlines()[0]
    assert "grade_f7 (agent.base.grades.f7:" in doc.splitlines()[0].replace("`", "")
    assert "claude_answers" in doc[doc.index("RULES"):] and "claude_answers" in doc[doc.index("THE RECORD"):doc.index("RULES")]
    assert F.LLM_TIMEOUT_S == F1.LLM_TIMEOUT_S and F.MODEL == F1.MODEL
    assert F.L.DEFAULT_CLI == F1.L.DEFAULT_CLI
    assert F.planner_factory.__code__.co_code == F1.planner_factory.__code__.co_code
    assert F.DAY_CAP_S == F1.DAY_CAP_S == 840        # the day cap is the library's, as f_goals_5.py kept it


def test_the_grade_wired_is_grade_f7_of_the_grades_module():
    """The session calls grades.f7.grade_f7 (GF is that module), never gates_f's grade_f6; f_grade_7.py regrades it."""
    from agent.base.grades import f7
    from agent.drivers import f_grade_7
    assert F.GF is f7 and F.GRADE_KEY == "grade_f7" and f7.grade_f7.__module__ == "agent.base.grades.f7"
    assert not hasattr(F.GF, "grade_f6") or F.GF.grade_f6 is not f7.grade_f7
    assert f_grade_7.grade_f7 is f7.grade_f7        # the regrade takes the run's artifact path, whatever its key


# ================================================================ the night: the profile and the fixture record
def test_the_night_profile_is_agent_tomls_on_the_night_fixture():
    import tomllib
    load = lambda name: tomllib.load(open(os.path.join(REPO, "testing", "profiles", name), "rb"))        # noqa: E731
    a, n = load("agent.toml"), load("agent-night.toml")
    assert (a["fixture"], n["fixture"]) == ("agent", "agent-night") == ("agent", F.FIXTURE)
    skip = ("fixture", "description")
    assert {k: v for k, v in a.items() if k not in skip} == {k: v for k, v in n.items() if k not in skip}
    assert [m["id"] for m in n["mods"]] == ["PZTestKit", "PZAgent"] and n["server"] == {"SleepAllowed": True,
                                                                                         "SleepNeeded": True}
    assert len(n["verify"]) == 2 and n["clients"] == ["admin"]


def test_the_night_fixture_record_is_the_agent_fixtures_with_the_9_pm_start():
    path = lambda name: os.path.join(REPO, "testing", "fixtures", name, "fixture.json")        # noqa: E731
    if not (os.path.isfile(path("agent")) and os.path.isfile(path("agent-night"))):
        pytest.skip("the agent and agent-night fixture records are machine-local")
    rec = lambda name: json.load(open(path(name), encoding="utf-8"))        # noqa: E731
    a, n = rec("agent"), rec("agent-night")
    assert n["name"] == "agent-night" and n["build"] == a["build"] == "42.21.0"
    assert a["server"]["sandbox"] == {"Zombies": "5"}
    assert n["server"]["sandbox"] == {"Zombies": "5", "StartTime": "6"}            # option 6 of StartTime is "9 PM"
    skip = ("name", "created", "provision_run", "timings", "size_mb", "server")
    assert {k: v for k, v in a.items() if k not in skip} == {k: v for k, v in n.items() if k not in skip}
    assert {k: v for k, v in a["server"].items() if k != "sandbox"} == {k: v for k, v in n["server"].items()
                                                                        if k != "sandbox"}
