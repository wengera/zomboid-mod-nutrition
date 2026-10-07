"""Plan 9 Task 3: the layout lint before every boot. `harness.lint_paths` returns the ERROR
lines of `tools/mod_lint.py` for every mod folder a profile points at, and `pzt run` and
`pzt provision` stop with exit 2 before any seed or fixture copy when it returns any."""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pytest
from pzt import cli, harness, profile
from pzt import fixture as fx

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _bad_mod(tmp_path):
    f = tmp_path / "common" / "media" / "lua" / "shared" / "x.lua"
    f.parent.mkdir(parents=True)
    f.write_text("-- x\n")
    return str(tmp_path)


def test_a_mod_folder_with_no_version_dir_returns_an_error_line(tmp_path):
    lines = harness.lint_paths({"X": _bad_mod(tmp_path)})
    assert lines and all("ERROR" in ln for ln in lines)


def test_only_errors_are_returned(tmp_path):
    lines = harness.lint_paths({"X": _bad_mod(tmp_path)})
    assert not any(": WARN:" in ln or ": INFO:" in ln for ln in lines)


def test_the_real_mod_folder_is_clean():
    assert harness.lint_paths({"NutritionRevamp": os.path.join(REPO, "mod", "NutritionRevamp")}) == []


def test_no_sources_is_clean():
    assert harness.lint_paths(None) == [] and harness.lint_paths({}) == []


def test_run_exits_2_before_any_seed(monkeypatch, capsys):
    def boom(*a, **k):
        raise AssertionError("seeded after a failed lint")
    monkeypatch.setattr(cli, "profile_args",
                        lambda a: (None, None, {"mod_sources": {"X": "/x"}}))
    monkeypatch.setattr(harness, "lint_paths", lambda s: ["X: ERROR: version-dir: none"])
    monkeypatch.setattr(fx, "load", boom)
    monkeypatch.setattr(cli, "make_server", boom)
    monkeypatch.setattr(cli, "new_run_dir", boom)
    assert cli.cmd_run(argparse.Namespace()) == 2
    out = capsys.readouterr().out
    assert "X: ERROR: version-dir: none" in out and "layout lint failed" in out


def test_provision_exits_2_before_any_seed(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("seeded after a failed lint")
    monkeypatch.setattr(harness, "lint_paths", lambda s: ["X: ERROR: id: none"])
    monkeypatch.setattr(cli, "make_server", boom)
    monkeypatch.setattr(cli, "new_run_dir", boom)
    assert cli.cmd_provision(argparse.Namespace()) == 2


def test_scenario_exits_2_before_any_seed(monkeypatch):
    from pzt import scenario

    def boom(*a, **k):
        raise AssertionError("seeded after a failed lint")
    monkeypatch.setattr(scenario, "profile_args",
                        lambda a: (None, None, {"mod_sources": {"X": "/x"}}))
    monkeypatch.setattr(harness, "lint_paths", lambda s: ["X: ERROR: version-dir: none"])
    monkeypatch.setattr(fx, "load", boom)
    monkeypatch.setattr(scenario, "make_server", boom)
    monkeypatch.setattr(scenario, "new_run_dir", boom)
    assert scenario.run(argparse.Namespace(user=None)) == 2
