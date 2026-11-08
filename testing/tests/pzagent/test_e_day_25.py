"""drivers/e_day_25.py (Plan 31 Task 15b, the twenty-fifth chain's session driver: e_day_24.py copied under its own key
for the Harden evidence, grade_x1 wired), offline: the driver is never invoked.

The static tests read its arguments (`--session`, `--fixture`, `--prev`, through `driverlib/day.py`), its constants,
its imports and the copy against its parent; the pre-boot checks run against the real profile and throwaway fixture
records (conftest's `agent_fixture`), once with the layout lint itself over the real tree the profile boots (the
PZAgent folder by path: the agent profile stages no release copy). The loop runs `e_day_25.make_session` (the
library's `Chain` with the driver's planner) on test_driverlib.py's DayMod and FakeBus (the library's own fakes,
imported) in a real run layout (`runs/<key>-<stamp>/clients/admin/Lua/pzagent/admin`), then the driver's grade over
that state dir and the regrade script `e_grade_22.py` over the artifact folder the auto-copy would leave."""
import contextlib
import io
import json
import os
import re
import shutil
import types

import pytest

from agent.base.grades import x1 as GX
from agent.base.planner.goals import ScriptedSource
from agent.base.planner.survive import Survive
from agent.base.transport.files import FileTransport
from agent.driverlib import day as DY
from agent.driverlib import session as S
from agent.drivers import e_day_24 as E1
from agent.drivers import e_day_25 as E
from agent.drivers import e_grade_22 as EG22
from .test_driverlib import Clock, DayMod, FakeBus, FakeServer, InlinePolls

REPO = S.REPO
X = S.X
RUN_ID = "e_day_25-20261106-120000"
BASE_COMMIT = "066c4336"   # the planner's head at the copy (`git log -1 -- testing/agent/base/planner`), re-based
#                            before the boot: the controller's re-base is this one replacement
BOOT = "# ================================================================ the boot"


# ================================================================ static: refusal, constants, imports
def test_the_driver_refuses_arguments_before_main():
    src = open(E.__file__, encoding="utf-8").read()
    i_ref = src.index("refusal = parse_argv(sys.argv[1:], __file__)")
    i_main = src.rindex("    main(flags(sys.argv[1:]))")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    me = E.__file__
    for bad in (["x"], ["--help"], ["--session"], ["--session", "0"], ["--session", "-1"], ["--session", "two"],
                ["--session", "1.5"], ["--fixture"], ["--prev"], ["--session", "2", "--session", "3"],
                ["--day", "2"], ["--session", "2", "x"], ["--dress"]):
        r = E.parse_argv(bad, me)
        assert r and "e_day_25.py" in r and "\n" not in r, bad
    for good in ([], ["--session", "2"], ["--fixture", "chain-1"], ["--prev", "a.json"],
                 ["--session", "3", "--fixture", "chain-2", "--prev", "testing/runs/e_day_25-1/e_day_25.json"]):
        assert E.parse_argv(good, me) is None, good
    assert E.flags([]) == {"session": 1, "fixture": "agent", "prev": None}
    assert E.parse_argv is DY.parse_argv and E.flags is DY.flags


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(E.__file__) == E.DRIVER == E.KEY + ".py" == "e_day_25.py"
    assert (E.KEY, E.PROFILE, E.ARTIFACT) == ("e_day_25", "testing/profiles/agent.toml", "e_day_25.json")
    assert os.path.isfile(os.path.join(REPO, E.PROFILE))
    assert (E.BUDGET_S, E.DAY_CAP_S, E.PLANNER_HZ, E.DAMAGE_POLL_S) == (1200.0, 840, 2, 5)
    assert E.LIMITS is DY.LIMITS and E.CONSTANTS is DY.CONSTANTS and E.USER is DY.USER == "admin"
    assert E.ALLOWED == ("--session", "--fixture", "--prev") and E.DEFAULT_FIXTURE == "agent"
    assert E.MIN_FREE_GB == S.DEFAULTS["MIN_FREE_GB"] == 0.0
    assert E.GRADE_KEY == "grade_x1" and E1.GRADE_KEY == "grade_e21"


def test_nothing_is_imported_from_a_frozen_driver_and_the_grade_is_grade_x1():
    src = open(E.__file__, encoding="utf-8").read()
    imports = [l.split("#")[0].strip() for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
    frozen = [l for l in imports if re.match(r"^(a_|b_|c_|d_|p22|x4_|x5_)", l.split()[1].split(".")[-1])
              or "drivers" in l or l.split()[1] in ("agent.link", "agent.grades", "agent.grade_c", "agent.world",
                                                     "agent.policy")]
    assert frozen == [], frozen
    for need in ("import xlib as X", "from agent.driverlib import session as DS",
                 "from agent.driverlib import day as DY", "from agent.base.planner.survive import Survive",
                 "from agent.base.planner.goals import ScriptedSource", "from agent.base.grades.x1 import grade_x1"):
        assert need in imports, need
    assert "Survive(world, actions, log_path, clock, source=ScriptedSource())" in src
    assert "return DY.make_day_session(xs, transport, planner, prev=prev, **kw)" in src
    assert "DY.boot_and_run(args, lambda: preboot(_ME, args), run_session, grade, key=KEY, driver=DRIVER," in src
    assert '    return grade_x1(out, state_dir=out.get("state_dir"), kind="e")' in src
    assert "grade_key=GRADE_KEY" in src and "    DY.grade(out, GRADE_KEY, grade_state)" in src
    assert E.grade_x1 is GX.grade_x1 and "gates_e" not in "\n".join(imports)
    assert "DRESS_MANEUVER" not in src and "control=" not in src.replace("`Survive(control=...)`", "")


def _between(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i) + len(end)]


def test_the_copy_differs_from_e_day_24_only_in_the_expected_lines():
    """e_day_25.py is e_day_24.py under its own key: only the first docstring line (its lineage, base and grade
    sentences), the second line (whose driver's lines the rest is), the grade passage of THE RECORD, the grade import,
    the key triple and the grade block differ; swapping each back reproduces the parent byte for byte."""
    a = open(E1.__file__, encoding="utf-8").read()
    b = open(E.__file__, encoding="utf-8").read()
    imp = "from agent.base.grades.x1 import grade_x1             # noqa: E402\n"
    old_imp = "from agent.base.grades.e21 import grade_e21           # noqa: E402\n"
    assert b.count(imp) == 1 and imp not in a and a.count(old_imp) == 1 and old_imp not in b
    swaps = [(b.splitlines()[0], a.splitlines()[0]), (b.splitlines()[1], a.splitlines()[1]), (imp, old_imp),
             (_between(b, 'out["grade_x1"] is grades.x1', 'else out["grade_x1_error"];'),
              _between(a, 'out["grade_e21"] is grades.e21', 'else out["grade_e21_error"];')),
             ('KEY = "e_day_25"', 'KEY = "e_day_24"'), ('DRIVER = "e_day_25.py"', 'DRIVER = "e_day_24.py"'),
             ('ARTIFACT = "e_day_25.json"', 'ARTIFACT = "e_day_24.json"'),
             (b[b.index("GRADE_KEY = "):b.index(BOOT)], a[a.index("GRADE_KEY = "):a.index(BOOT)])]
    norm = b
    for mine, theirs in swaps:
        assert norm.count(mine) == 1, mine
        norm = norm.replace(mine, theirs)
    assert norm == a
    assert b.splitlines()[1] == a.splitlines()[1].replace("e_day_23.py's", "e_day_24.py's")
    stops = ('STOPS (out["stop"]', "day_cap (the loop")
    assert _between(b, *stops) == _between(a, *stops)
    assert E.CONSTANTS == E1.CONSTANTS and E.PROFILE == E1.PROFILE


def test_the_base_sentence_names_the_planner_s_head_at_the_copy_once():
    """The base sentence's commit is the planner's head the copy was made at; the controller re-bases it before the
    boot, and the commit stands once, in this sentence and this module's BASE_COMMIT, so a re-base is one
    replacement."""
    first = E.__doc__.splitlines()[0]
    assert ("the base at `%s` (the planner: Plan 31 Task 13 mix_2 fix 1, its head at the copy, re-based before the "
            "boot)" % BASE_COMMIT) in first
    assert first.count(BASE_COMMIT) == 1 and E.__doc__.count(BASE_COMMIT) == 1 and first.count("re-based") == 1
    for c in ("e_day_24.py", "Plan 31 Task 15b", "twenty-fifth", "P31-H", "PZA/1.10", "`mod` `1.10`", "Dress",
              "this driver sets nothing of it", "grade_x1", "grade_e21", "state.1.log"):
        assert c in first, c


# ================================================================ the pre-boot, the real profile and the real tree
def _stub(monkeypatch, lint=True):
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (True, "ok"))
    if lint:
        monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (False, ""))
    real = S.DL.C.git_say
    tracked = {"v": ""}
    monkeypatch.setattr(S.DL.C, "git_say", lambda *a: tracked["v"] if a[0] == "ls-files" else real(*a))
    return tracked


def _chain_fixture(root, name):
    sv = root / name / "cache" / "server" / "Server"
    sv.mkdir(parents=True)
    (root / name / "fixture.json").write_text(json.dumps(
        {"name": name, "build": "42.21.0", "server": {"name": "pzt", "mods": ["PZTestKit"]}, "clients": {"admin": {}},
         "parent": "agent", "session": 1}))


def test_preboot_on_the_real_profile(agent_fixture, monkeypatch, tmp_path):
    tracked = _stub(monkeypatch)
    pre, ok = E.preboot(E.__file__, E.flags([]))
    assert ok, pre
    assert pre["profile"] == "agent" and pre["driver_checks"]["driver_file"] is True
    assert pre["driver_checks"]["driverlib_dirty"] is False and pre["driverlib_commit"]
    assert pre["chain_checks"] == DY.chain_checks(E.flags([]))[0] and pre["chain_checks"]["fixture_ok"] is True
    _chain_fixture(agent_fixture, "chain-1")
    prev = tmp_path / "e_day_25.json"
    prev.write_text(json.dumps({"loop": {"last_frames": [{"seq": 1}]}}), encoding="utf-8")
    pre, ok = E.preboot(E.__file__, E.flags(["--session", "2", "--fixture", "chain-1", "--prev", str(prev)]))
    assert ok, pre
    assert pre["chain_checks"]["session_consistent"] is True and pre["chain_checks"]["prev_frames"] is True
    pre, ok = E.preboot(E.__file__, E.flags(["--fixture", "nope"]))
    assert ok is False and pre["chain_checks"]["fixture_ok"] is False
    pre, ok = E.preboot(E.__file__, E.flags(["--prev", str(tmp_path / "gone.json")]))
    assert ok is False and pre["chain_checks"]["prev_ok"] is False
    tracked["v"] = "testing/artifacts/e_day_25-20261106-120000/e_day_25.json"
    assert E.preboot(E.__file__, E.flags([]))[1] is False
    tracked["v"] = ""
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (rel == "testing/agent/driverlib", ""))
    assert E.preboot(E.__file__, E.flags([]))[1] is False
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (False, ""))
    assert E.preboot(os.path.join(os.path.dirname(E.__file__), "e_day_24.py"), E.flags([]))[1] is False


def test_preboot_lints_the_real_tree_the_profile_boots(agent_fixture, monkeypatch):
    """The layout lint itself (not stubbed) over the real profile's mod sources: the PZAgent folder by path."""
    _stub(monkeypatch, lint=False)
    pre, ok = E.preboot(E.__file__, E.flags([]))
    assert pre["lint_errors"] == [] and ok, pre


# ================================================================ the session on the fake, in a real run layout
def run_chain(tmp_path, monkeypatch, day_cap_s=20):
    """One `e_day_25.make_session` on test_driverlib's DayMod and FakeBus in a real run layout, then the driver's
    grade over the run's state dir (as the boot records it)."""
    clock = Clock()
    run_dir = tmp_path / "runs" / RUN_ID
    sd = run_dir / "clients" / "admin" / "Lua" / "pzagent" / "admin"
    mod = DayMod(str(sd), clock, held=True)
    fb = FakeBus(mod)
    monkeypatch.setattr(S.DL, "time", types.SimpleNamespace(time=clock.now))
    out = S.new_out()
    xs = X.Xs(out, node=lambda side: side, server=FakeServer(mod), ask=fb.ask, clock=clock.now, sleep=mod.sleep,
              budget_s=1e9, user="admin", clients={"admin": types.SimpleNamespace(seen={})})
    xs.path = str(run_dir / E.ARTIFACT)
    sess = E.make_session(xs, FileTransport(str(sd), clock=clock.now), None, clock=clock.now, sleep=mod.sleep,
                          free=lambda: 30.0, polls=InlinePolls(clock=clock.now), limits={"DAY_CAP_S": day_cap_s})
    sess.run()
    out["frames"]["parks"] = 0
    out["state_dir"] = str(sd)
    E.grade(out)
    out["finished"] = True
    return types.SimpleNamespace(out=out, day=sess, run_dir=run_dir, sd=sd)


def test_the_session_builds_the_planner_with_the_defaults_and_grades_grade_x1_over_the_run_s_state_dir(
        tmp_path, monkeypatch):
    r = run_chain(tmp_path, monkeypatch)
    out, s = r.out, r.day
    assert out["phase_errors"] == {} and out["stop"]["reason"] == "day_cap"
    assert isinstance(s, DY.Chain) and isinstance(s.planner, Survive)
    assert isinstance(s.planner.goals.source, ScriptedSource) and s.planner.control == "ladder"
    # the Dress's switch is the planner's own default (on after Task 15a): the driver sets nothing of it
    assert "DRESS_MANEUVER" not in vars(s.planner) and s.planner.DRESS_MANEUVER is Survive.DRESS_MANEUVER
    g = out["grade_x1"]
    assert "grade_x1_error" not in out and "grade_e21" not in out
    assert g["grade"] == "grade_x1" and g["base"] == "grade_e21" and set(GX.NEW) <= set(g)
    assert g["frames_source"] == "state_logs" and g["frames_files"] == ["state.log"] and g["frames_n"] > 0
    assert g["survived"] is True and g["landed_hits"]["read"] is True and g["wounds_dressed"]["read"] is True
    assert g["fleeing"] == {"read": False} and g["dresses"] == {"read": False}    # no decision log at the boot
    json.dumps(out, allow_nan=False)


def test_the_regrade_e_grade_22_reads_the_artifact_folder_the_auto_copy_leaves(tmp_path, monkeypatch):
    r = run_chain(tmp_path, monkeypatch)
    art = tmp_path / "artifacts" / RUN_ID
    art.mkdir(parents=True)
    with open(art / E.ARTIFACT, "w", encoding="utf-8") as fh:
        json.dump(r.out, fh, allow_nan=False)
    shutil.copy(r.run_dir / "decision.log", art / "decision.log")
    shutil.copy(r.sd / "state.log", art / "state.log")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert EG22.main([str(art / E.ARTIFACT)]) == 0
    text = buf.getvalue()
    got = json.loads(text[text.index("\n{\n"):])
    assert got["grade"] == "grade_x1" and got["base"] == "grade_e21"
    assert got["fleeing"]["read"] is True and got["toward_target"]["read"] is True     # the decision log beside it
    assert text.splitlines()[-1] == "}" and "dresses" in text


def test_the_dress_maneuver_is_on_by_default_in_the_planner_the_driver_builds():
    assert Survive.DRESS_MANEUVER is True


def test_grade_records_a_grade_failure_rather_than_raising(monkeypatch):
    out = {"loop": {}}
    monkeypatch.setattr(E, "grade_x1", lambda o, **kw: (_ for _ in ()).throw(ValueError("boom")))
    E.grade(out)
    assert out["grade_x1_error"] == "ValueError: boom" and "grade_x1" not in out
