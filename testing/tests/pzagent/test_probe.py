"""driverlib/probe.py (Plan 31 Task 4, the `claude -p` probe lifted out of the frozen driver f_goals_16.py), offline:
the real `claude` CLI is never called; every test injects `run` and `which`.

The tests are test_f_goals_16.py's own tests of `claude_available`, `probe_argv` and `claude_answers`, copied against
the library (the driver's, through its `preboot`, stay in that file and stay green on the frozen copy), plus one
fidelity test: the library's three functions are the frozen driver's, source for source."""
import ast
import json
import os
import subprocess

from agent.base.planner import llm as L
from agent.driverlib import probe as P

REPO_TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FROZEN = os.path.join(REPO_TESTING, "agent", "drivers", "f_goals_16.py")


class Proc:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


def envelope(result="ok", is_error=False):
    return Proc(json.dumps({"type": "result", "is_error": is_error, "result": result}))


# ================================================================ claude_available
def test_claude_available_reads_the_cli_and_its_version_once():
    seen = []

    def run(argv, **kw):
        seen.append((argv, kw))
        return Proc("2.1.310 (Claude Code)\n")

    r = P.claude_available(which=lambda name: "C:/bin/claude.exe" if name == "claude" else None, run=run)
    assert r == {"found": True, "path": "C:/bin/claude.exe", "version": "2.1.310 (Claude Code)", "error": None,
                 "ok": True}
    assert seen == [(["C:/bin/claude.exe", "--version"], {"capture_output": True, "text": True, "timeout": 30})]
    r = P.claude_available(which=lambda name: None, run=run)
    assert r == {"found": False, "path": None, "version": None, "error": "claude not on PATH", "ok": False}
    assert len(seen) == 1                                                   # no CLI: nothing run
    r = P.claude_available(which=lambda name: "c", run=lambda argv, **kw: Proc("", 3))
    assert r["ok"] is False and r["found"] is True and r["version"] is None and r["error"] == "exit 3"
    r = P.claude_available(which=lambda name: "c", run=lambda argv, **kw: Proc("  \n", 0))
    assert r["ok"] is False and r["error"] == "no version on stdout"

    def boom(argv, **kw):
        raise subprocess.TimeoutExpired(argv, 30)

    r = P.claude_available(which=lambda name: "c", run=boom)
    assert r["ok"] is False and r["version"] is None and r["error"].startswith("TimeoutExpired")


# ================================================================ claude_answers
def test_claude_answers_is_ok_only_on_exit_0_with_a_result_text():
    seen = []

    def run(argv, **kw):
        seen.append((argv, kw))
        return envelope("ok")

    r = P.claude_answers(run=run)
    assert r["ok"] is True and r["exit"] == 0 and r["answer"] == "ok" and r["error"] is None
    assert isinstance(r["latency_s"], float) and r["latency_s"] >= 0
    assert set(r) == {"ok", "exit", "answer", "latency_s", "error"}
    assert len(seen) == 1                                                    # one call, read once
    argv, kw = seen[0]
    assert kw["input"] == P.PROBE_INPUT and kw["input"].strip() and kw["timeout"] == P.LLM_TIMEOUT_S == 20.0
    assert kw["capture_output"] is True and kw["text"] is True
    r = P.claude_answers(run=lambda argv, **kw: Proc("", 1))
    assert r["ok"] is False and r["exit"] == 1 and r["error"] == "exit 1" and r["answer"] is None
    r = P.claude_answers(run=lambda argv, **kw: Proc("rate limited", 1))
    assert r["ok"] is False and r["error"] == "exit 1; stdout: rate limited"

    def boom(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw["timeout"])

    r = P.claude_answers(run=boom)
    assert r["ok"] is False and r["exit"] is None and r["error"].startswith("TimeoutExpired")
    assert isinstance(r["latency_s"], float)
    for bad in (envelope(""), envelope("   \n"), Proc(json.dumps({"type": "result"}), 0),
                Proc(json.dumps({"result": 5}), 0), Proc("[1]", 0)):
        r = P.claude_answers(run=lambda argv, **kw: bad)
        assert r["ok"] is False and r["exit"] == 0 and r["error"] == "no result text", bad.stdout
    r = P.claude_answers(run=lambda argv, **kw: envelope("Credit balance is too low", is_error=True))
    assert r["ok"] is False and r["error"] == "cli error" and r["answer"] == "Credit balance is too low"
    for bad in (Proc("not json", 0), Proc("", 0)):
        r = P.claude_answers(run=lambda argv, **kw: bad)
        assert r["ok"] is False and r["error"] == "stdout is not JSON"


def test_a_refusal_names_its_cause_from_stderr_and_stdout_cut_to_200_characters():
    r = P.claude_answers(run=lambda argv, **kw: Proc("", 1, stderr="  Claude AI usage limit reached|1761\n"))
    assert r["ok"] is False and r["exit"] == 1 and r["answer"] is None
    assert r["error"] == "exit 1; stderr: Claude AI usage limit reached|1761"
    r = P.claude_answers(run=lambda argv, **kw: Proc("out text", 1, stderr="err text"))
    assert r["error"] == "exit 1; stderr: err text; stdout: out text"
    r = P.claude_answers(run=lambda argv, **kw: Proc("o" * 500, 1, stderr="e" * 500))
    assert r["error"] == "exit 1; stderr: %s; stdout: %s" % ("e" * 200, "o" * 200) and P.ERR_SNIPPET == 200
    r = P.claude_answers(run=lambda argv, **kw: Proc("", 7, stderr=None))
    assert r["error"] == "exit 7"
    r = P.claude_answers(run=lambda argv, **kw: Proc("", 1, stderr="rate limit"), which=lambda name: "c")
    assert r["error"].endswith("stderr: rate limit")


def test_the_probe_runs_the_cli_without_claudecode_and_through_the_injected_which(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("PZ_PROBE_KEEP", "kept")
    seen, asked = [], []
    which = lambda name: asked.append(name) or "C:/injected/claude.exe"          # noqa: E731
    r = P.claude_answers(run=lambda a, **kw: seen.append((a, kw)) or envelope("ok"), which=which)
    assert r["ok"] is True and asked == ["claude"]
    argv, kw = seen[0]
    assert argv[0] == "C:/injected/claude.exe" and argv[1:] == P.probe_argv()[1:]
    assert "CLAUDECODE" not in kw["env"] and kw["env"]["PZ_PROBE_KEEP"] == "kept"      # the rest is carried
    assert kw["env"] is not os.environ and os.environ.get("CLAUDECODE") == "1"        # the host's own is untouched
    assert kw["cwd"] == L._cwd() or os.path.isdir(kw["cwd"])                          # the worker's own directory
    # a which that finds nothing leaves the argv's own name, as the runner does
    P.claude_answers(run=lambda a, **kw: seen.append((a, kw)) or envelope("ok"), which=lambda name: None)
    assert seen[1][0][0] == "claude"


# ================================================================ probe_argv
def test_the_probe_argv_is_the_goal_sources_own_with_only_the_system_prompt_swapped():
    argv = P.probe_argv()
    cli = list(L.DEFAULT_CLI)
    assert len(argv) == len(cli)
    diff = [i for i, (a, b) in enumerate(zip(cli, argv)) if a != b]
    assert diff == [cli.index("--system-prompt") + 1]
    assert argv[diff[0]] == P.PROBE_SYSTEM == "Reply with the single word ok."
    for flag in ("-p", "--output-format", "json", "--model", "sonnet", "--tools", "", "--setting-sources",
                 "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
        assert flag in argv
    assert L.SYSTEM in cli and L.SYSTEM not in argv and L.DEFAULT_CLI == tuple(cli)    # the source's argv is untouched
    assert P.probe_argv(("claude", "-p", "--system-prompt", "x", "--model", "m")) == [
        "claude", "-p", "--system-prompt", P.PROBE_SYSTEM, "--model", "m"]
    # the argv the call runs is the probe's (the executable resolved as the LLMSource's runner resolves it)
    seen = []
    P.claude_answers(run=lambda a, **kw: seen.append(a) or envelope("ok"))
    assert seen[0][1:] == argv[1:]


# ================================================================ the copy is the frozen driver's
def _segments(path, names):
    text = open(path, encoding="utf-8").read()
    tree = ast.parse(text)
    return {n.name: ast.get_source_segment(text, n) for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name in names}


def _constants(path, names):
    text = open(path, encoding="utf-8").read()
    out = {}
    for n in ast.parse(text).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and getattr(n.targets[0], "id", None) in names:
            out[n.targets[0].id] = ast.literal_eval(n.value)
    return out


def test_the_three_functions_and_their_constants_are_the_frozen_drivers():
    names = {"claude_available", "probe_argv", "claude_answers"}
    lib = _segments(P.__file__, names)
    frozen = _segments(FROZEN, names)
    assert set(lib) == set(frozen) == names
    for name in names:
        assert lib[name].replace("\r\n", "\n") == frozen[name].replace("\r\n", "\n"), name
    consts = {"LLM_TIMEOUT_S", "CLAUDE_VERSION_TIMEOUT_S", "PROBE_SYSTEM", "ERR_SNIPPET", "PROBE_INPUT"}
    assert _constants(P.__file__, consts) == _constants(FROZEN, consts) and len(_constants(P.__file__, consts)) == 5
