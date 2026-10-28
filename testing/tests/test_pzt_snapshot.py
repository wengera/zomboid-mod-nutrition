import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pytest
from pzt import fixture as fx
from pzt import cli


def _run_dir(tmp_path):
    rd = tmp_path / "runs" / "e_day-20261028-120000"
    for p in ("server/Saves/Multiplayer/pzt/map_p.bin", "server/Logs/x.txt", "server/mods/PZTestKit/mod.info",
              "clients/admin/options.ini", "clients/admin/Logs/y.txt", "clients/admin/mods/PZAgent/mod.info"):
        (rd / p).parent.mkdir(parents=True, exist_ok=True)
        (rd / p).write_text("x")
    return rd


@pytest.fixture
def fixtures(tmp_path, monkeypatch):
    root = tmp_path / "fixtures"
    monkeypatch.setattr(fx, "FIXTURES", str(root))
    (root / "agent" / "cache" / "server").mkdir(parents=True)
    rec = {"name": "agent", "build": "42.21.0", "provision_run": "prov-20261026-092028",
           "server": {"sandbox": {"Zombies": "5"}, "mods": ["PZTestKit"]}, "clients": {"admin": {"debug": True}}}
    (root / "agent" / "fixture.json").write_text(json.dumps(rec))
    return root


def test_snapshot_from_run_copies_the_caches_and_writes_the_lineage(tmp_path, fixtures):
    rd = _run_dir(tmp_path)
    rec = fx.snapshot_from_run("agent-s1", str(rd), "agent", 1)
    cache = fixtures / "agent-s1" / "cache"
    assert (cache / "server" / "Saves" / "Multiplayer" / "pzt" / "map_p.bin").is_file()
    assert not (cache / "server" / "Logs").exists() and not (cache / "server" / "mods").exists()
    assert (cache / "clients" / "admin" / "options.ini").is_file() and not (cache / "clients" / "admin" / "mods").exists()
    assert rec["parent"] == "agent" and rec["run"] == "e_day-20261028-120000" and rec["session"] == 1
    assert rec["lineage"] == ["agent"] and rec["server"]["sandbox"] == {"Zombies": "5"} and rec["build"] == "42.21.0"
    assert json.load(open(fixtures / "agent-s1" / "fixture.json"))["name"] == "agent-s1"


def test_a_second_link_extends_the_lineage(tmp_path, fixtures):
    rd = _run_dir(tmp_path)
    fx.snapshot_from_run("agent-s1", str(rd), "agent", 1)
    rec = fx.snapshot_from_run("agent-s2", str(rd), "agent-s1", 2, run_id="e_day-20261028-130000")
    assert rec["lineage"] == ["agent", "agent-s1"] and rec["run"] == "e_day-20261028-130000"


def test_a_run_without_a_server_cache_or_a_client_is_refused(tmp_path, fixtures):
    rd = _run_dir(tmp_path)
    import shutil
    shutil.rmtree(rd / "clients" / "admin")
    with pytest.raises(SystemExit, match="clients"):
        fx.snapshot_from_run("agent-s1", str(rd), "agent", 1)
    shutil.rmtree(rd / "server")
    with pytest.raises(SystemExit, match="server"):
        fx.snapshot_from_run("agent-s1", str(rd), "agent", 1)


def test_the_cli_resolves_a_run_id_under_runs_and_dispatches(tmp_path, fixtures, monkeypatch, capsys):
    rd = _run_dir(tmp_path)
    monkeypatch.setattr("pzt.cli.RUNS", str(tmp_path / "runs"), raising=False)
    calls = []
    monkeypatch.setattr(fx, "snapshot_from_run", lambda *a, **k: calls.append((a, k)) or {"size_mb": 9.5})
    rc = cli.main(["snapshot", "--from-run", "e_day-20261028-120000", "--name", "agent-s1", "--parent", "agent"])
    assert rc == 0 and calls[0][0] == ("agent-s1", str(rd), "agent", 1)
    assert "FIXTURE 'agent-s1' snapshotted" in capsys.readouterr().out
