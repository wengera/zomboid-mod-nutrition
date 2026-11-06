"""Pure-Python tests for pzt.paths' environment roots: PZT_FIXTURES and PZT_RUNS.

The roots are module constants fixed at import, so each case imports pzt.paths in a child
interpreter with the environment it names (no reload of the module the other tests hold).
"""
import json, os, subprocess, sys
import pytest

TESTING = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

PROBE = ("import json, sys; sys.path.insert(0, sys.argv[1]);"
         "from pzt import paths; print(json.dumps([paths.RUNS, paths.FIXTURES, paths.TESTING]))")


def roots(monkeypatch, cwd=None, **env):
    monkeypatch.delenv("PZT_RUNS", raising=False)
    monkeypatch.delenv("PZT_FIXTURES", raising=False)
    full = dict(os.environ, **env)
    out = subprocess.run([sys.executable, "-c", PROBE, TESTING], env=full, cwd=cwd, check=True,
                         capture_output=True, text=True).stdout
    return json.loads(out)


def test_defaults_with_both_variables_unset(monkeypatch):
    runs, fixtures, testing = roots(monkeypatch)
    assert runs == os.path.join(testing, "runs")
    assert fixtures == os.path.join(testing, "fixtures")


def test_runs_variable_is_honoured(monkeypatch, tmp_path):
    runs, fixtures, testing = roots(monkeypatch, PZT_RUNS=str(tmp_path / "r"))
    assert runs == str(tmp_path / "r")
    assert fixtures == os.path.join(testing, "fixtures")


def test_fixtures_variable_is_honoured(monkeypatch, tmp_path):
    runs, fixtures, testing = roots(monkeypatch, PZT_FIXTURES=str(tmp_path / "f"))
    assert fixtures == str(tmp_path / "f")
    assert runs == os.path.join(testing, "runs")


def test_both_variables_together(monkeypatch, tmp_path):
    runs, fixtures, _ = roots(monkeypatch, PZT_RUNS=str(tmp_path / "r"), PZT_FIXTURES=str(tmp_path / "f"))
    assert (runs, fixtures) == (str(tmp_path / "r"), str(tmp_path / "f"))


def test_a_relative_value_is_made_absolute_against_the_working_directory(monkeypatch, tmp_path):
    runs, fixtures, _ = roots(monkeypatch, cwd=str(tmp_path), PZT_RUNS="rel_runs", PZT_FIXTURES=os.path.join(".", "rel_fx"))
    assert os.path.isabs(runs) and os.path.isabs(fixtures)
    assert os.path.basename(runs) == "rel_runs" and os.path.basename(fixtures) == "rel_fx"
    assert os.path.samefile(os.path.dirname(runs), str(tmp_path))
    assert os.path.samefile(os.path.dirname(fixtures), str(tmp_path))


def test_an_empty_value_falls_back_to_the_default(monkeypatch):
    runs, fixtures, testing = roots(monkeypatch, PZT_RUNS="", PZT_FIXTURES="")
    assert (runs, fixtures) == (os.path.join(testing, "runs"), os.path.join(testing, "fixtures"))


def test_new_run_dir_lands_under_the_runs_root(monkeypatch, tmp_path):
    code = ("import sys; sys.path.insert(0, sys.argv[1]);"
            "from pzt import paths; rid, d = paths.new_run_dir('t3'); print(d)")
    monkeypatch.delenv("PZT_FIXTURES", raising=False)
    env = dict(os.environ, PZT_RUNS=str(tmp_path / "rr"))
    out = subprocess.run([sys.executable, "-c", code, TESTING], env=env, check=True,
                         capture_output=True, text=True).stdout.strip()
    assert os.path.dirname(out) == str(tmp_path / "rr") and os.path.isdir(out)
