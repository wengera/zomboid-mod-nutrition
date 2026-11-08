"""drivers/f_goals_17.py (Plan 31 Task 15b, the sixteenth LLM session's driver: f_goals_16.py copied under its own key
for the Harden evidence, the live probe the library's `driverlib/probe.py`, grade_x1 wired), offline: the driver is
never invoked and the real `claude` CLI is never called.

The static tests read its arguments, its constants, its imports and the copy against its parent; the pre-boot checks
run against the real profile and throwaway fixture records (conftest's `agent_fixture`), once with the layout lint
itself over the real tree the profile boots, the CLI's presence, `claude --version` and the live `-p` probe read
through stubbed `which` and `run`. The loop runs `f_goals_17.make_session` (the library's `Chain` with the driver's LLM
planner, its `llm` record and `goals.log`) on test_driverlib.py's DayMod and FakeBus in a real run layout, the
LLMSource's `runner` a fake and its worker run synchronously (`SyncThread`), then the driver's grade over the run's
state dir and the regrade script `f_grade_13.py` over the artifact folder the auto-copy would leave."""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import threading
import types

import pytest

from agent.base.grades import x1 as GX
from agent.base.planner import llm as L
from agent.base.planner.goals import ScriptedSource
from agent.base.planner.survive import Survive
from agent.base.transport.files import FileTransport
from agent.driverlib import day as DY
from agent.driverlib import probe as PR
from agent.driverlib import session as S
from agent.drivers import f_goals_16 as F1
from agent.drivers import f_goals_17 as F
from agent.drivers import f_grade_13 as FG13
from .test_driverlib import Clock, DayMod, FakeBus, FakeServer, InlinePolls

REPO = S.REPO
X = S.X
RUN_ID = "f_goals_17-20261106-120000"
BASE_COMMIT = "066c4336"   # the planner's head at the copy, re-based before the boot (one replacement)
PRE = "# ================================================================ pre-boot"
SESSION = "# ================================================================ the session"
BOOT = "# ================================================================ the boot"


# ================================================================ static: refusal, constants, imports
def test_the_driver_refuses_arguments_before_main():
    src = open(F.__file__, encoding="utf-8").read()
    i_ref = src.index("refusal = parse_argv(sys.argv[1:], __file__)")
    i_main = src.rindex("    main(flags(sys.argv[1:]))")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    me = F.__file__
    for bad in (["x"], ["--help"], ["--session"], ["--session", "0"], ["--session", "two"], ["--fixture"],
                ["--prev"], ["--session", "2", "--session", "3"], ["--model", "opus"], ["--session", "2", "x"],
                ["--no-llm"]):
        r = F.parse_argv(bad, me)
        assert r and "f_goals_17.py" in r and "\n" not in r, bad
    for good in ([], ["--session", "2"], ["--fixture", "chain-1"], ["--prev", "a.json"]):
        assert F.parse_argv(good, me) is None, good
    assert F.flags([]) == {"session": 1, "fixture": "agent", "prev": None}
    assert F.parse_argv is DY.parse_argv and F.flags is DY.flags


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(F.__file__) == F.DRIVER == F.KEY + ".py" == "f_goals_17.py"
    assert (F.KEY, F.PROFILE, F.ARTIFACT) == ("f_goals_17", "testing/profiles/agent.toml", "f_goals_17.json")
    assert os.path.isfile(os.path.join(REPO, F.PROFILE)) and not hasattr(F, "FIXTURE")
    assert (F.BUDGET_S, F.DAY_CAP_S, F.PLANNER_HZ, F.DAMAGE_POLL_S) == (1200.0, 840, 2, 5)
    assert F.LLM_TIMEOUT_S == L.LLM_TIMEOUT_S == F1.LLM_TIMEOUT_S == 20.0     # the goal source's own, the probe's too
    assert F.CONSTANTS == dict(DY.CONSTANTS, LLM_TIMEOUT_S=20.0) == F1.CONSTANTS
    assert F.MODEL == "sonnet" == L.model_of(L.DEFAULT_CLI) and F.GOALS_LOG == "goals.log" and F.USER == "admin"
    assert F.MIN_FREE_GB == S.DEFAULTS["MIN_FREE_GB"] and F.LLM_JOIN_S == 25.0
    assert F.GRADE_KEY == "grade_x1" and F1.GRADE_KEY == "grade_f12"
    assert F.NOT_PROBED == {"ok": False, "exit": None, "answer": None, "latency_s": None,
                            "error": "not probed: no CLI"}


def test_nothing_is_imported_from_a_frozen_driver_and_the_probe_is_the_library_s():
    src = open(F.__file__, encoding="utf-8").read()
    imports = [l.split("#")[0].strip() for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
    frozen = [l for l in imports if re.match(r"^(a_|b_|c_|d_|e_|p22|x4_|x5_)", l.split()[1].split(".")[-1])
              or "drivers" in l or l.split()[1] in ("agent.link", "agent.grades", "agent.grade_c", "agent.world",
                                                     "agent.policy")]
    assert frozen == [], frozen
    for need in ("import xlib as X", "from agent.driverlib import session as DS",
                 "from agent.driverlib import day as DY", "from agent.driverlib import probe as PR",
                 "from agent.base.grades import x1 as GX", "from agent.base.planner import llm as L",
                 "from agent.base.planner.survive import Survive",
                 "from agent.base.planner.goals import ScriptedSource"):
        assert need in imports, need
    assert F.PR is PR and F.GX is GX
    for own in ("def claude_available", "def claude_answers", "def probe_argv", "PROBE_SYSTEM =", "ERR_SNIPPET ="):
        assert own not in src, own                               # the probe lives in the library alone
    assert "ca = PR.claude_available(which, run)" in src and "PR.claude_answers(run=run, which=which)" in src
    assert "source=L.LLMSource(ScriptedSource()," in src and "timeout_s=LLM_TIMEOUT_S" in src
    assert "DY.make_day_session(xs, transport, planner_factory(runner)" in src and "copied=(GOALS_LOG,)" in src
    assert "DY.boot_and_run(args, lambda: preboot(_ME, args), run_session, grade, key=KEY, driver=DRIVER," in src
    assert 'GX.grade_x1(out, state_dir=out.get("state_dir"), kind="f")' in src
    assert "DY.grade(out, GRADE_KEY, grade_state)" in src and "after_teardown=after_teardown)" in src
    assert "DRESS_MANEUVER" not in src


def _between(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i) + len(end)]


def test_the_copy_differs_from_f_goals_16_only_in_the_expected_lines():
    """f_goals_17.py is f_goals_16.py under its own key: only the first docstring line, the docstring's two grade
    passages, the two imports `json` and `time` the probe took with it, the grade import and the probe's import, the
    key triple, the LLM timeout (the goal source's own), the probe's constants (NOT_PROBED in their place), the
    pre-boot section (the library's probe) and the grade block differ; swapping each back reproduces the parent byte
    for byte."""
    a, b = open(F1.__file__, encoding="utf-8").read(), open(F.__file__, encoding="utf-8").read()
    swaps = [
        (b.splitlines()[0], a.splitlines()[0]),
        (_between(b, "Each session's `grade_x1`", "is written at its end."),
         _between(a, "Each session's `grade_f12`", "is written at its end.")),
        (_between(b, 'out["grade_x1"] is grades.x1', 'else out["grade_x1_error"];'),
         _between(a, 'out["grade_f12"] is grades.f12', 'else out["grade_f12_error"];')),
        ("import os\nimport shutil\nimport subprocess\nimport sys\n",
         "import json\nimport os\nimport shutil\nimport subprocess\nimport sys\nimport time\n"),
        ("from agent.base.grades import x1 as GX                # noqa: E402\n",
         "from agent.base.grades import f12 as GF               # noqa: E402\n"),
        ("from agent.driverlib import probe as PR               # noqa: E402\n", ""),
        ('KEY = "f_goals_17"', 'KEY = "f_goals_16"'), ('DRIVER = "f_goals_17.py"', 'DRIVER = "f_goals_16.py"'),
        ('ARTIFACT = "f_goals_17.json"', 'ARTIFACT = "f_goals_16.json"'),
        (_between(b, "LLM_TIMEOUT_S = L.LLM_TIMEOUT_S", "driverlib/probe.py)\n"),
         _between(a, "LLM_TIMEOUT_S = 20.0", "is a fallback\n")),
        (_between(b, "NOT_PROBED = ", "}\n"), _between(a, "CLAUDE_VERSION_TIMEOUT_S = ", "empty prompt\n")),
        (b[b.index(PRE):b.index(SESSION)], a[a.index(PRE):a.index(SESSION)]),
        (b[b.index("GRADE_KEY = "):b.index(BOOT)], a[a.index("GRADE_KEY = "):a.index(BOOT)]),
    ]
    norm = b
    for mine, theirs in swaps:
        assert norm.count(mine) == 1, mine
        norm = norm.replace(mine, theirs)
    assert norm == a
    assert a[a.index(BOOT):] == b[b.index(BOOT):] and F.DAY_CAP_S == F1.DAY_CAP_S == 840
    assert F.planner_factory.__code__.co_code == F1.planner_factory.__code__.co_code
    assert F.L.DEFAULT_CLI == F1.L.DEFAULT_CLI and F.MODEL == F1.MODEL


def test_the_base_sentence_names_the_planner_s_head_at_the_copy_once():
    first = F.__doc__.splitlines()[0]
    assert ("the base at `%s` (the planner: Plan 31 Task 13 mix_2 fix 1, its head at the copy, re-based before the "
            "boot)" % BASE_COMMIT) in first
    assert first.count(BASE_COMMIT) == 1 and F.__doc__.count(BASE_COMMIT) == 1 and first.count("re-based") == 1
    for c in ("f_goals_16.py", "Plan 31 Task 15b", "P31-H", "PZA/1.10", "`mod` `1.10`", "driverlib/probe.py",
              "this driver sets nothing of it", "grade_x1", "grade_f12", "f_grade_13.py", "stall",
              "boots only after one live `-p` call answers"):
        assert c in first, c
    rules = F.__doc__[F.__doc__.index("RULES"):]
    assert "--session <n+1>" in rules and "--prev <the last chain artifact>" in rules and "P23-Z" in rules


# ================================================================ the pre-boot and the probe
class Proc:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


def answering_run(version="2.1.310 (Claude Code)\n", probe=None, calls=None):
    """A fake `run` for both pre-boot calls: `--version` answers the version, the probe call (`-p` in argv) `probe`."""
    probe = probe if probe is not None else Proc(json.dumps({"type": "result", "is_error": False, "result": "ok"}))

    def run(argv, **kw):
        if calls is not None:
            calls.append((argv, kw))
        if "-p" in argv:
            if isinstance(probe, BaseException):
                raise probe
            return probe
        return Proc(version)
    return run


def _stub(monkeypatch, lint=True):
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (True, "ok"))
    if lint:
        monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (False, ""))
    real = S.DL.C.git_say
    tracked = {"v": ""}
    monkeypatch.setattr(S.DL.C, "git_say", lambda *a: tracked["v"] if a[0] == "ls-files" else real(*a))
    return tracked


WHICH = lambda name: "C:/bin/claude.exe"                                     # noqa: E731


def test_preboot_on_the_real_profile_with_the_library_s_probe(agent_fixture, monkeypatch, tmp_path):
    tracked = _stub(monkeypatch)
    monkeypatch.setenv("CLAUDECODE", "1")
    calls = []
    pre, ok = F.preboot(F.__file__, F.flags([]), which=WHICH, run=answering_run(calls=calls))
    assert ok, pre
    assert pre["profile"] == "agent" and pre["driver_checks"]["driver_file"] is True
    assert pre["chain_checks"] == DY.chain_checks(F.flags([]))[0]
    assert pre["claude_available"]["ok"] is True and pre["claude_version"] == "2.1.310 (Claude Code)"
    assert pre["claude_answers"]["ok"] is True and pre["claude_answers"]["answer"] == "ok"
    assert [c[0][0] for c in calls] == ["C:/bin/claude.exe"] * 2                 # the version call and the probe
    argv, kw = calls[1]
    assert argv[1:] == PR.probe_argv()[1:] and kw["input"] == PR.PROBE_INPUT and kw["timeout"] == L.LLM_TIMEOUT_S
    assert "CLAUDECODE" not in kw["env"]
    pre, ok = F.preboot(F.__file__, F.flags([]), which=lambda name: None, run=answering_run())
    assert ok is False and pre["claude_available"]["found"] is False and pre["claude_answers"] == F.NOT_PROBED
    assert pre["claude_answers"] is not F.NOT_PROBED                              # a copy, never the constant
    pre, ok = F.preboot(F.__file__, F.flags(["--fixture", "nope"]), which=WHICH, run=answering_run())
    assert ok is False and pre["chain_checks"]["fixture_ok"] is False
    tracked["v"] = "testing/artifacts/f_goals_17-20261106-120000/f_goals_17.json"
    assert F.preboot(F.__file__, F.flags([]), which=WHICH, run=answering_run())[1] is False
    tracked["v"] = ""
    assert F.preboot(os.path.join(os.path.dirname(F.__file__), "f_goals_16.py"), F.flags([]), which=WHICH,
                     run=answering_run())[1] is False


def test_preboot_refuses_the_boot_when_the_live_probe_does_not_answer(agent_fixture, monkeypatch):
    _stub(monkeypatch)
    pre, ok = F.preboot(F.__file__, F.flags([]), which=WHICH, run=answering_run(probe=Proc("", 1, "usage limit")))
    assert ok is False and pre["claude_available"]["ok"] is True
    assert pre["claude_answers"]["ok"] is False and pre["claude_answers"]["error"] == "exit 1; stderr: usage limit"
    pre, ok = F.preboot(F.__file__, F.flags([]), which=WHICH,
                        run=answering_run(probe=subprocess.TimeoutExpired("claude", 20.0)))
    assert ok is False and pre["claude_answers"]["error"].startswith("TimeoutExpired")
    empty = Proc(json.dumps({"type": "result", "is_error": False, "result": ""}))
    assert F.preboot(F.__file__, F.flags([]), which=WHICH, run=answering_run(probe=empty))[1] is False
    pre, ok = F.preboot(F.__file__, F.flags([]), which=WHICH, run=lambda argv, **kw: Proc("", 1))
    assert ok is False and pre["claude_version"] is None and pre["claude_answers"]["error"] == "not probed: no CLI"


def test_preboot_lints_the_real_tree_the_profile_boots(agent_fixture, monkeypatch):
    _stub(monkeypatch, lint=False)
    pre, ok = F.preboot(F.__file__, F.flags([]), which=WHICH, run=answering_run())
    assert pre["lint_errors"] == [] and ok, pre


# ================================================================ the session on the fake, in a real run layout
class SyncThread:
    """threading.Thread for the LLMSource's worker, run to its end at start()."""

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


def run_goals(tmp_path, monkeypatch, day_cap_s=20):
    monkeypatch.setattr(L, "threading", types.SimpleNamespace(Thread=SyncThread, Event=threading.Event))
    clock = Clock()
    run_dir = tmp_path / "runs" / RUN_ID
    sd = run_dir / "clients" / "admin" / "Lua" / "pzagent" / "admin"
    mod = DayMod(str(sd), clock, held=True)
    fb = FakeBus(mod)
    monkeypatch.setattr(S.DL, "time", types.SimpleNamespace(time=clock.now))
    out = S.new_out()
    xs = X.Xs(out, node=lambda side: side, server=FakeServer(mod), ask=fb.ask, clock=clock.now, sleep=mod.sleep,
              budget_s=1e9, user="admin", clients={"admin": types.SimpleNamespace(seen={})})
    xs.path = str(run_dir / F.ARTIFACT)
    runner = Runner()
    sess = F.make_session(xs, FileTransport(str(sd), clock=clock.now), cli_version="2.1.310 (Claude Code)",
                          runner=runner, clock=clock.now, sleep=mod.sleep, free=lambda: 30.0,
                          polls=InlinePolls(clock=clock.now), limits={"DAY_CAP_S": day_cap_s})
    sess.run()
    out["frames"]["parks"] = 0
    out["state_dir"] = str(sd)
    F.grade(out)
    out["finished"] = True
    return types.SimpleNamespace(out=out, day=sess, run_dir=run_dir, sd=sd, runner=runner, xs=xs)


def test_the_llm_session_builds_the_planner_with_the_defaults_and_grades_grade_x1(tmp_path, monkeypatch):
    r = run_goals(tmp_path, monkeypatch)
    out, s = r.out, r.day
    assert out["phase_errors"] == {} and out["stop"]["reason"] == "day_cap"
    assert isinstance(s, DY.Chain) and isinstance(s.planner, Survive) and s.planner.control == "ladder"
    src = s.planner.goals.source
    assert isinstance(src, L.LLMSource) and isinstance(src.fallback, ScriptedSource) and src.runner is r.runner
    assert src.timeout_s == 20.0 and src.log_path == os.path.join(str(r.run_dir), "goals.log")
    # the Dress's switch is the planner's own default (on after Task 15a): the driver sets nothing of it
    assert "DRESS_MANEUVER" not in vars(s.planner) and s.planner.DRESS_MANEUVER is Survive.DRESS_MANEUVER
    assert out["loop"]["llm"]["model"] == "sonnet" and out["loop"]["llm"]["calls"]
    assert "goals.log" in r.xs.copied and "decision.log" in r.xs.copied
    g = out["grade_x1"]
    assert "grade_x1_error" not in out and "grade_f12" not in out
    assert g["grade"] == "grade_x1" and g["base"] == "grade_f12" and set(GX.NEW) <= set(g)
    assert g["llm"]["calls"] == len(out["loop"]["llm"]["calls"]) and g["frames_source"] == "state_logs"
    assert g["fleeing"] == {"read": False} and g["landed_hits"]["read"] is True
    json.dumps(out, allow_nan=False)


def test_the_regrade_f_grade_13_reads_the_artifact_folder_the_auto_copy_leaves(tmp_path, monkeypatch):
    r = run_goals(tmp_path, monkeypatch)
    art = tmp_path / "artifacts" / RUN_ID
    art.mkdir(parents=True)
    with open(art / F.ARTIFACT, "w", encoding="utf-8") as fh:
        json.dump(r.out, fh, allow_nan=False)
    for name in ("decision.log", "goals.log"):
        shutil.copy(r.run_dir / name, art / name)
    shutil.copy(r.sd / "state.log", art / "state.log")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert FG13.main([str(art / F.ARTIFACT)]) == 0
    text = buf.getvalue()
    got = json.loads(text[text.index("\n{\n"):])
    assert got["grade"] == "grade_x1" and got["base"] == "grade_f12"
    assert got["fleeing"]["read"] is True and got["answers"]["read"] is True      # the logs beside it


def test_run_session_returns_the_session_and_the_worker_is_joined_after_the_teardown(monkeypatch):
    joins = []
    source = types.SimpleNamespace(join=lambda t: joins.append(t) or True)
    sess = types.SimpleNamespace(planner=types.SimpleNamespace(goals=types.SimpleNamespace(source=source)))
    sess.run = lambda: None
    monkeypatch.setattr(F, "make_session", lambda xs, tr, prev, cli_version=None: sess)
    assert F.run_session(types.SimpleNamespace(out={}), "tr", None, {"claude_version": "v"}) is sess and joins == []
    out = {}
    F.after_teardown(out, sess)
    assert out == {"llm_joined": True} and joins == [25.0]


def test_the_dress_maneuver_is_on_by_default_in_the_planner_the_driver_builds():
    assert Survive.DRESS_MANEUVER is True


def test_grade_records_a_grade_failure_rather_than_raising(monkeypatch):
    out = {"loop": {}}
    monkeypatch.setattr(F.GX, "grade_x1", lambda o, **kw: (_ for _ in ()).throw(ValueError("boom")))
    F.grade(out)
    assert out["grade_x1_error"] == "ValueError: boom" and "grade_x1" not in out
