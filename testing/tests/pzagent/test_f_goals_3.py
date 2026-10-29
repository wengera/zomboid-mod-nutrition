"""drivers/f_goals_3.py (Plan 24 Task 11, the third LLM session's driver, f_goals_2.py copied under its own key), offline: the driver is never invoked and the real
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
from agent.drivers import f_goals_2 as F1
from agent.drivers import f_goals_3 as F
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
        assert r and "f_goals_3.py" in r and "\n" not in r, bad
    for good in ([], ["--session", "2"], ["--fixture", "chain-1"], ["--prev", "a.json"],
                 ["--session", "3", "--fixture", "chain-2", "--prev", "testing/runs/f_goals_3-1/f_goals_3.json"]):
        assert F.parse_argv(good, me) is None, good
    assert F.flags([]) == {"session": 1, "fixture": "agent", "prev": None}
    assert F.parse_argv is DY.parse_argv and F.flags is DY.flags


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(F.__file__) == F.DRIVER == F.KEY + ".py" == "f_goals_3.py"
    assert (F.KEY, F.PROFILE, F.ARTIFACT) == ("f_goals_3", "testing/profiles/agent.toml", "f_goals_3.json")
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
                 "from agent.driverlib import day as DY", "from agent.base import gates_f as GF",
                 "from agent.base.planner import llm as L",
                 "from agent.base.planner.survive import Survive",
                 "from agent.base.planner.goals import ScriptedSource"):
        assert need in imports, need
    assert "source=L.LLMSource(ScriptedSource()," in src and "timeout_s=LLM_TIMEOUT_S" in src
    assert "DY.make_day_session(xs, transport, planner_factory(runner)" in src and "copied=(GOALS_LOG,)" in src
    # the boot is the library's: driverlib/day.boot_and_run (its order tested in test_driverlib.py)
    assert "DY.boot_and_run(args, lambda: preboot(_ME, args), run_session, grade, key=KEY, driver=DRIVER," in src
    assert 'grade_key="grade_f3"' in src and 'DY.grade(out, "grade_f3", GF.grade_f3)' in src
    assert "grade_f1" not in src and "grade_f2" not in src
    assert 'cli_version=pre.get("claude_version")' in src
    doc = F.__doc__
    for word in ("RULES", "--session", "--fixture", "--prev", "never edited after its run", "goals.log", "llm",
                 "claude --version", "grade_f3", "LLMSource", "ScriptedSource", "day_cap"):
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
    def __init__(self, stdout="", returncode=0):
        self.stdout, self.returncode = stdout, returncode


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


def test_preboot_on_the_real_profile(agent_fixture, monkeypatch, tmp_path):
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (False, ""))
    real = S.DL.C.git_say
    tracked = {"v": ""}
    monkeypatch.setattr(S.DL.C, "git_say", lambda *a: tracked["v"] if a[0] == "ls-files" else real(*a))
    here = {"which": lambda name: "C:/bin/claude.exe", "run": lambda argv, **kw: Proc("2.1.310 (Claude Code)\n")}
    pre, ok = F.preboot(F.__file__, F.flags([]), **here)
    assert ok, pre
    assert pre["profile"] == "agent" and pre["driver_checks"]["driver_file"] is True
    assert pre["driver_checks"]["driverlib_dirty"] is False and pre["driverlib_commit"]
    assert pre["chain_checks"] == DY.chain_checks(F.flags([]))[0]
    assert pre["chain_checks"]["fixture_ok"] is True and pre["chain_checks"]["prev_ok"] is None
    assert pre["claude_available"]["ok"] is True and pre["claude_version"] == "2.1.310 (Claude Code)"
    gone = {"which": lambda name: None, "run": here["run"]}
    pre, ok = F.preboot(F.__file__, F.flags([]), **gone)
    assert ok is False and pre["claude_available"]["found"] is False and pre["claude_version"] is None
    pre, ok = F.preboot(F.__file__, F.flags([]), which=here["which"], run=lambda argv, **kw: Proc("", 1))
    assert ok is False and pre["claude_version"] is None
    pre, ok = F.preboot(F.__file__, F.flags(["--fixture", "nope"]), **here)
    assert ok is False and pre["chain_checks"]["fixture_ok"] is False
    pre, ok = F.preboot(F.__file__, F.flags(["--prev", str(tmp_path / "gone.json")]), **here)
    assert ok is False and pre["chain_checks"]["prev_ok"] is False
    tracked["v"] = "testing/artifacts/f_goals_3-20261028-120000/f_goals_3.json"
    assert F.preboot(F.__file__, F.flags([]), **here)[1] is False
    tracked["v"] = ""
    assert F.preboot(os.path.join(os.path.dirname(F.__file__), "e_day.py"), F.flags([]), **here)[1] is False


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
    xs.path = str(tmp_path / "f_goals_3.json")
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
    persisted = json.loads((tmp_path / "f_goals_3.json").read_text(encoding="utf-8"))
    assert persisted["loop"]["llm"] == json.loads(json.dumps(llm))
    g = out["grade_f3"]
    assert "grade_f2" not in out and "grade_f2_error" not in out
    assert g["grade"] == "grade_f3" and g["survived"] is True
    assert g["llm"]["calls"] == 4 and g["llm"]["ok"] == 1 and g["llm"]["fallbacks"] == 3
    assert g["llm"]["goals_by_type"].get("Rest", 0) >= 1
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
    monkeypatch.setattr(F.GF, "grade_f3", lambda o: (_ for _ in ()).throw(ValueError("boom")))
    F.grade(out)
    assert out["grade_f3_error"] == "ValueError: boom" and "grade_f3" not in out and "grade_f2" not in out


# ================================================================ the copy of f_goals.py and the totals
def test_the_totals_reach_the_llm_record(tmp_path, monkeypatch):
    r = run_goals(tmp_path, monkeypatch, day_cap_s=40)
    llm = r.out["loop"]["llm"]
    calls = llm["calls"]
    assert llm["prompt_bytes_total"] == sum(c["prompt_bytes"] for c in calls) > 0
    assert llm["answer_bytes_total"] == sum(c["answer_bytes"] for c in calls)
    assert "answer_bytes_total" in llm and llm["model"] == "sonnet"


BASE_SENTENCE = (
    "the base at `6159dbc4` carries PZA/1.5.2 (the combat stance held while backpedalling, the fence climb at a walk, "
    "the bandage, the rag rip and wash, the water fill, the parts' care fields, the squares' water sources, the item "
    "re-read after a fill or a drink) and survival iteration 6 (the stance fight against one or two with the backpedal "
    "band and the 20 s fallback, the care branch between threat and need, the water chain drinking clean water then "
    "filling a held vessel at a clean source, the climb after a stuck walk, the no-effect mark; rulings P24-A to "
    "P24-M)")


def test_the_driver_is_f_goals_2_py_copied_under_its_own_key():
    def lines(mod):
        return open(mod.__file__, encoding="utf-8").read().splitlines()
    old, new = lines(F1), lines(F)
    import difflib
    changed = [l for l in difflib.unified_diff(old, new, lineterm="", n=0)
               if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    plus = [l[1:] for l in changed if l[0] == "+"]
    minus = [l[1:] for l in changed if l[0] == "-"]
    assert 'KEY = "f_goals_3"' in plus and 'DRIVER = "f_goals_3.py"' in plus and 'ARTIFACT = "f_goals_3.json"' in plus
    assert 'KEY = "f_goals_2"' in minus and 'DRIVER = "f_goals_2.py"' in minus and 'ARTIFACT = "f_goals_2.json"' in minus
    rest = [l for l in plus if not l.startswith(("KEY = ", "DRIVER = ", "ARTIFACT = "))]
    # the first docstring paragraph, the two docstring lines that name the grade, the grade function's two lines and
    # the boot's grade_key; nothing else
    assert rest[0].startswith('"""f_goals_3 -- the third LLM session')
    assert sum(1 for l in rest if "grade_f3" in l) >= 5 and not any("grade_f2" in l for l in rest)
    assert '    DY.grade(out, "grade_f3", GF.grade_f3)' in rest
    assert any('grade_key="grade_f3"' in l for l in rest)
    doc = F.__doc__
    assert doc.splitlines()[1] == "" and doc.splitlines()[2].startswith("The rest of this docstring is f_goals.py")
    assert BASE_SENTENCE in doc and "PZA/1.5.2" in doc and "Task 11" in doc
    assert "grade_f3 (gates_f: grade_e3" in doc.replace("`", "") or "`grade_f3` (gates_f: grade_e3" in doc
