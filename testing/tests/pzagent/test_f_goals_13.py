"""drivers/f_goals_13.py (Plan 28 Task 5, the twelfth LLM session's driver, f_goals_12.py copied under its own key on
the fixture `agent` and the profile `agent` by day, the live CLI probe kept and grade_f9 of agent.base.grades.f9),
offline: the driver is never invoked and the real
`claude` CLI is never called.

The static tests read its arguments (the day's `--session`, `--fixture`, `--prev`, through `driverlib/day.py`), its
constants and its imports; the pre-boot checks run against the real profile and throwaway fixture records (conftest's
`agent_fixture`), the CLI's presence and `claude --version` read through stubbed `which` and `run`. The loop runs
`f_goals.make_session` (the library's `Chain` with the driver's LLM planner, its `llm` record and `goals.log`) on
test_driverlib.py's DayMod and FakeBus (the library's own fakes, imported), the LLMSource's `runner` a fake (a goal
answered on the first call, a timeout on the second) and its worker thread run synchronously at its start
(`SyncThread`, the module's `threading` swapped for the test), so the run is deterministic on the fake clock."""
import json
import os
import re
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
from agent.drivers import f_goals_12 as F1
from agent.drivers import f_goals_9 as F9
from agent.drivers import f_goals_13 as F
from .test_driverlib import Clock, DayMod, FakeBus, FakeServer, InlinePolls

REPO = S.REPO
X = S.X


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
        assert r and "f_goals_13.py" in r and "\n" not in r, bad
    for good in ([], ["--session", "2"], ["--fixture", "chain-1"], ["--prev", "a.json"],
                 ["--session", "3", "--fixture", "chain-2", "--prev", "testing/runs/f_goals_13-1/f_goals_13.json"]):
        assert F.parse_argv(good, me) is None, good
    assert F.flags([]) == {"session": 1, "fixture": "agent", "prev": None}
    assert F.parse_argv is DY.parse_argv and F.flags is DY.flags


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(F.__file__) == F.DRIVER == F.KEY + ".py" == "f_goals_13.py"
    assert (F.KEY, F.PROFILE, F.ARTIFACT) == ("f_goals_13", "testing/profiles/agent.toml", "f_goals_13.json")
    assert os.path.isfile(os.path.join(REPO, F.PROFILE))
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
                 "from agent.driverlib import day as DY", "from agent.base.grades import f9 as GF",
                 "from agent.base.planner import llm as L",
                 "from agent.base.planner.survive import Survive",
                 "from agent.base.planner.goals import ScriptedSource"):
        assert need in imports, need
    assert "source=L.LLMSource(ScriptedSource()," in src and "timeout_s=LLM_TIMEOUT_S" in src
    assert "DY.make_day_session(xs, transport, planner_factory(runner)" in src and "copied=(GOALS_LOG,)" in src
    # the boot is the library's: driverlib/day.boot_and_run (its order tested in test_driverlib.py)
    assert "DY.boot_and_run(args, lambda: preboot(_ME, args), run_session, grade, key=KEY, driver=DRIVER," in src
    assert "grade_key=GRADE_KEY" in src and 'GRADE_KEY = "grade_f9"' in src
    assert "GF.grade_f9(out, state_dir=out.get(" in src
    assert "DY.grade(out, GRADE_KEY, grade_state)" in src and F.GRADE_KEY == "grade_f9"
    assert "grade_f1" not in src and "grade_f2" not in src and "grade_f6" not in src and "gates_f" not in src
    assert "GF.grade_f5" not in src
    assert 'cli_version=pre.get("claude_version")' in src
    doc = F.__doc__
    for word in ("RULES", "--session", "--fixture", "--prev", "never edited after its run", "goals.log", "llm",
                 "claude --version", "grade_f9", "LLMSource", "ScriptedSource", "day_cap"):
        assert word in doc, word
    # M-10: an F session on the chain's last fixture follows the chain's numbering (P23-Z)
    rules = doc[doc.index("RULES"):]
    assert "--session <n+1>" in rules and "--prev <the last chain artifact>" in rules and "P23-Z" in rules


def test_the_e_day_driver_shares_the_day_session_through_the_library():
    from agent.drivers import e_day as E
    assert E.Chain is DY.Chain and E.parse_argv is DY.parse_argv is F.parse_argv and E.flags is DY.flags is F.flags
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
    assert pre["profile"] == "agent" and pre["driver_checks"]["driver_file"] is True
    assert pre["driver_checks"]["driverlib_dirty"] is False and pre["driverlib_commit"]
    assert pre["chain_checks"] == DY.chain_checks(F.flags([]))[0]
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
    tracked["v"] = "testing/artifacts/f_goals_13-20261028-120000/f_goals_13.json"
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
    assert "def claude_answers(cli=L.DEFAULT_CLI, run=subprocess.run, which=shutil.which):" in src
    assert "probe_argv(cli)" in src


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
    xs.path = str(tmp_path / "f_goals_13.json")
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
    persisted = json.loads((tmp_path / "f_goals_13.json").read_text(encoding="utf-8"))
    assert persisted["loop"]["llm"] == json.loads(json.dumps(llm))
    g = out["grade_f9"]
    assert "grade_f2" not in out and "grade_f2_error" not in out
    assert g["grade"] == "grade_f9" and g["survived"] is True
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
    monkeypatch.setattr(F.GF, "grade_f9", lambda o, **kw: (_ for _ in ()).throw(ValueError("boom")))
    F.grade(out)
    assert out["grade_f9_error"] == "ValueError: boom" and "grade_f9" not in out and "grade_f8" not in out


# ================================================================ the copy of f_goals.py and the totals
def test_the_totals_reach_the_llm_record(tmp_path, monkeypatch):
    r = run_goals(tmp_path, monkeypatch, day_cap_s=40)
    llm = r.out["loop"]["llm"]
    calls = llm["calls"]
    assert llm["prompt_bytes_total"] == sum(c["prompt_bytes"] for c in calls) > 0
    assert llm["answer_bytes_total"] == sum(c["answer_bytes"] for c in calls)
    assert "answer_bytes_total" in llm and llm["model"] == "sonnet"


BASE_SENTENCE = (
    "the base at `c6fdcd37` (the planner: Plan 28 Task 3, its head at the copy) carries PZA/1.7.2 (the part record's "
    "`wound`, and the attack releasing the stance and pressing one tick after facing, P28-F; the hello reads `mod` "
    "`1.7`) and survival iteration 21 (over iteration 20: P28-A the wound dressed, P28-B the back leg after a missed "
    "shove and the drifted pin's stance, P28-C the floor swing under the arms' pain, P28-D a busy rejection no "
    "refusal, P28-E the circle), the goal source with the fourth round's readings (P26-F the objects, P26-G the open "
    "views, P26-H the re-asks, read by `grade_f7` and so by `grade_f9`) and the view's `stuck` line (P27-F); the "
    "controller re-bases this sentence to the commit the session boots on")
NEW17 = ("stuck_leave", "floor_finish", "fallen_seek", "listing", "shove_close", "stock_early", "low_exit",
         "spent_held", "wounded_swing_off")
NEW18 = ("hits", "wound_dress", "shove_back", "drift_stand", "floor_pain", "busy_retry", "circle", "facing",
         "client_end")
NEW19 = ("flee_finish", "many_tail", "hold_fight", "hold_rest", "spent_kept", "low_swing", "wounded_swings",
         "window_still", "unwear_live")
BOOT = "# ================================================================ the boot"


def _between(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i) + len(end)]


def test_the_driver_is_f_goals_12_py_copied_under_its_own_key_with_grade_f9_wired():
    """Plan 28 Task 5: f_goals_13.py is f_goals_12.py (the model) under its own key: only the first docstring line,
    the docstring's grade, stops and protocol passages, the grade import, the key triple and the grade block differ
    (swapping each back reproduces the parent byte for byte); the profile and fixture by day, the probe, the
    pre-boot, the planner and the LLM constants are the model's."""
    a, b = open(F1.__file__, encoding="utf-8").read(), open(F.__file__, encoding="utf-8").read()
    imp = "from agent.base.grades import f9 as GF                # noqa: E402\n"
    old_imp = "from agent.base.grades import f8 as GF                # noqa: E402\n"
    assert b.count(imp) == 1 and imp not in a and a.count(old_imp) == 1 and old_imp not in b
    swaps = [(b.splitlines()[0], a.splitlines()[0]), (imp, old_imp),
             (_between(b, "The rest of this docstring", "f_goals -- Plan 23"),
              _between(a, "The rest of this docstring", "f_goals -- Plan 23")),
             (_between(b, "Each session's `grade_f9`", "is written at its end."),
              _between(a, "Each session's `grade_f8`", "is written at its end.")),
             (_between(b, 'STOPS (out["stop"])', "lua_error_storm,"),
              _between(a, 'STOPS (out["stop"])', "lua_error_storm,")),
             (_between(b, 'out["grade_f9"] is grades.f9', 'else out["grade_f9_error"];'),
              _between(a, 'out["grade_f8"] is grades.f8', 'else out["grade_f8_error"];')),
             ('KEY = "f_goals_13"', 'KEY = "f_goals_12"'), ('DRIVER = "f_goals_13.py"', 'DRIVER = "f_goals_12.py"'),
             ('ARTIFACT = "f_goals_13.json"', 'ARTIFACT = "f_goals_12.json"'),
             (b[b.index("GRADE_KEY = "):b.index(BOOT)], a[a.index("GRADE_KEY = "):a.index(BOOT)])]
    norm = b
    for mine, theirs in swaps:
        assert norm.count(mine) == 1, mine
        norm = norm.replace(mine, theirs)
    assert norm == a
    assert F.GRADE_KEY == "grade_f9" and F1.GRADE_KEY == "grade_f8" and F.GF is not F1.GF
    doc = F.__doc__
    first = doc.splitlines()[0]
    assert doc.splitlines()[1] == "" and doc.splitlines()[2].startswith("The rest of this docstring is f_goals.py")
    assert BASE_SENTENCE in first and "PZA/1.7.2" in first and "Task 5" in first and "f_goals_12.py" in first
    assert "c6fdcd37" in first and "0c5da18c" not in doc and "PZA/1.7.1" not in doc and "P27-K1" not in doc
    assert "iteration 20 (over" not in doc and "f_goals_11" not in doc
    order = [first.index(x) for x in ("P28-A ", "P28-B ", "P28-C ", "P28-D ", "P28-E ")]
    assert order == sorted(order)           # one clause each, in order
    for word in NEW17 + NEW18 + ("f_grade_9.py", "grade_f8", "grades.e17", "grades.e18", "agent.base.grades.f9"):
        assert word in first, word
    assert "boots only after one live `-p` call answers" in first
    assert F.LLM_TIMEOUT_S == F1.LLM_TIMEOUT_S and F.MODEL == F1.MODEL
    assert F.L.DEFAULT_CLI == F1.L.DEFAULT_CLI
    assert F.planner_factory.__code__.co_code == F1.planner_factory.__code__.co_code
    assert F.DAY_CAP_S == F1.DAY_CAP_S == 840


def test_the_stops_block_names_client_end_after_death():
    """Amendment 3: the docstring's STOPS block names `client_end` after `death` as the library's STOPS tuple orders
    it (Plan 28 Task 1, 37a70a97)."""
    flat = " ".join(_between(F.__doc__, 'STOPS (out["stop"])', "memory,").split())
    assert ("death, client_end (a `players` reply without the user with no death event and no zero-health frame read "
            "before it: the client's end, `loop.end` {seq, health, players}, never a death; Plan 28 Task 1, "
            "37a70a97), bus_dead, lua_error_storm, memory,") in flat
    stops = S.STOPS
    assert stops.index("death") + 1 == stops.index("client_end")
    assert stops.index("client_end") + 1 == stops.index("bus_dead")


def test_the_base_sentence_names_the_planner_s_head_at_the_copy():
    """The base sentence's commit is the planner's head the copy was made at (`git log -1 -- testing/agent/base/planner`
    at Task 5: c6fdcd37, Plan 28 Task 3); the controller re-bases it before the boot."""
    first = F.__doc__.splitlines()[0]
    assert BASE_SENTENCE in first
    assert "the base at `c6fdcd37` (the planner: Plan 28 Task 3, its head at the copy)" in first


def test_the_driver_boots_the_agent_fixture_by_day_as_f_goals_12_py_does():
    assert F.PROFILE == F1.PROFILE == F9.PROFILE == "testing/profiles/agent.toml" and not hasattr(F, "FIXTURE")
    assert F.flags is DY.flags is F1.flags and F.flags([])["fixture"] == "agent"        # no night wrapper
    a, b = open(F1.__file__, encoding="utf-8").read(), open(F.__file__, encoding="utf-8").read()
    mark = "# ================================================================ pre-boot"
    assert a[a.index(mark):a.index("def make_session")] == b[b.index(mark):b.index("def make_session")]
    assert a[a.index(BOOT):] == b[b.index(BOOT):]


def test_the_grade_wired_is_grade_f9_of_the_grades_module():
    """The session calls grades.f9.grade_f9 (GF is that module), never grade_f8; f_grade_9.py regrades it."""
    from agent.base.grades import f9
    from agent.drivers import f_grade_9
    assert F.GF is f9 and F.GRADE_KEY == "grade_f9" and f9.grade_f9.__module__ == "agent.base.grades.f9"
    assert not hasattr(F.GF, "grade_f6") and F.GF.grade_f9 is f9.grade_f9
    assert f_grade_9.grade_f9 is f9.grade_f9        # the regrade takes the run's artifact path, whatever its key


def test_the_grade_carries_the_iteration_20_and_pass_18_readings_unread_without_a_decision_log(tmp_path, monkeypatch):
    r = run_goals(tmp_path, monkeypatch, day_cap_s=5)
    g = r.out["grade_f9"]
    assert g["grade"] == "grade_f9" and "grade_f9_error" not in r.out and "grade_f8" not in r.out
    # no decision log and no state lines at the boot: all eighteen readings (the hits off the state lines) unread
    for k in NEW17 + NEW18 + NEW19:
        assert g[k] == {"read": False}, k
    assert all(g[k] == {"read": False} for k in ("open_views", "objects", "reasks"))
    json.dumps(r.out, allow_nan=False)
