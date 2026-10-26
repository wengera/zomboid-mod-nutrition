"""drivers/c_survive_2.py (Plan 21b Stage C pass 2), offline: the driver is never invoked. Its refusal, its constants
and its pre-boot checks under its own spec, modelled on test_c_survive.py's dense-driver tests."""
import os

from agent.drivers import c_survive as D
from agent.drivers import c_survive_2 as D2

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_the_driver_refuses_arguments_before_main():
    with open(D2.__file__, encoding="utf-8") as fh:
        src = fh.read()
    i_ref, i_main = src.index("refusal = parse_argv(sys.argv[1:], __file__)"), src.rindex("    CS.main(SPEC, _ME)")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    assert "c_survive_2.py takes no arguments" in D2.parse_argv(["x"], D2.__file__)
    assert D2.parse_argv(["--help"], D2.__file__) and D2.parse_argv([], D2.__file__) is None


def test_the_constants_name_the_drivers_own_file_and_profile():
    assert os.path.basename(D2.__file__) == D2.DRIVER == D2.KEY + ".py" and D2.ARTIFACT == D2.KEY + ".json"
    assert (D2.KEY, D2.PROFILE, D2.ARTIFACT) == ("c_survive_2", "testing/profiles/agent.toml", "c_survive_2.json")
    assert D2.RUN1 == "c_survive-20261026-183905" and D2.RUN1 in D2.__doc__
    assert D2.SPEC == (D2.KEY, D2.DRIVER, D2.PROFILE, D2.ARTIFACT) and os.path.isfile(os.path.join(REPO, D2.PROFILE))
    assert D2.Survive is D.Survive and D2.parse_argv is D.parse_argv and D2.BUDGET_S == D.BUDGET_S
    assert (D2.USER, D2.MIN_FREE_GB, D2.REPO) == (D.USER, D.MIN_FREE_GB, D.REPO)
    src = open(D2.__file__, encoding="utf-8").read()
    assert "class " not in src and "def main" not in src


def test_the_docstring_names_run_1s_four_defects():
    doc = D2.__doc__
    for word in ("disengage", "flapping", "never closed", "FLEE_HEALTH_PAIR", "game minute 670"):
        assert word in doc, word


def stub_checks(monkeypatch, dirty=None, lint=(), tracked=""):
    dirty = dirty or {}
    monkeypatch.setattr(D.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(D.DL.harness, "lint_paths", lambda srcs: list(lint))
    monkeypatch.setattr(D.DL.C, "git_dirty", lambda rel: (dirty.get(rel, False), ""))
    real = D.DL.C.git_say
    monkeypatch.setattr(D.DL.C, "git_say", lambda *a: tracked if a[0] == "ls-files" else real(*a))


CLEAN = {"driver_file": True, "driver_prefix": True, "profile_exists": True, "no_committed_artifact": True,
         "agent_lua_dirty": False, "agent_py_dirty": False, "driver_dirty": False}


def test_preboot_on_the_real_profile(agent_fixture, monkeypatch):
    stub_checks(monkeypatch)
    pre, ok = D2.preboot(D2.__file__)
    assert ok, pre
    assert pre["profile"] == "agent" and pre["lint_errors"] == [] and pre["driver_checks"] == CLEAN


def test_preboot_refuses(agent_fixture, monkeypatch):
    stub_checks(monkeypatch, tracked="testing/artifacts/c_survive_2-20261027-120000/c_survive_2.json")
    pre, ok = D2.preboot(D2.__file__)
    assert not ok and pre["driver_checks"]["no_committed_artifact"] is False
    for rel in ("testing/PZAgent", "testing/agent", "testing/agent/drivers/c_survive_2.py"):
        stub_checks(monkeypatch, dirty={rel: True})
        assert D2.preboot(D2.__file__)[1] is False, rel
    stub_checks(monkeypatch, dirty={"testing/agent/drivers/c_survive_2.py": True})
    assert D.preboot(D.__file__)[1] is True                  # the dirty file is this driver's, not c_survive's
    stub_checks(monkeypatch, lint=["ERROR x"])
    assert D2.preboot(D2.__file__)[1] is False
    stub_checks(monkeypatch)
    assert D.preboot(D2.__file__)[1] is False and D2.preboot(D.__file__)[1] is False   # each file under its own spec


def test_driver_checks_names_this_file():
    c, ok = D2.driver_checks(D2.__file__, git_say=lambda *a: "", git_dirty=lambda rel: (False, ""))
    assert ok and c == CLEAN
    seen = []
    D2.driver_checks(D2.__file__, git_say=lambda *a: seen.append(a) or "", git_dirty=lambda rel: seen.append(rel) or
                     (False, ""))
    assert ("ls-files", "--", "testing/artifacts/c_survive_2-*") in seen
    assert "testing/agent/drivers/c_survive_2.py" in seen
