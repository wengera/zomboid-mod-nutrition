"""make_server(reuse=True) boots the run directory's existing server cache instead of restoring
the fixture into it (X28, X49b: a second boot on the same run dir). Pure Python: no game."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from pzt import session


class Calls:
    restored = []


def test_reuse_skips_the_restore_and_keeps_the_record_ports(monkeypatch, tmp_path):
    rec = {"name": "default", "server": {"name": "pzt", "mods": ["PZTestKit"], "port": 27261, "rcon_port": 27015}}
    monkeypatch.setattr(session.fx, "restore_server", lambda name, run_dir: Calls.restored.append(name) or os.path.join(run_dir, "server"))
    monkeypatch.setattr(session.Server, "seed", lambda self, sandbox=None: None)
    run_dir = str(tmp_path)
    os.makedirs(os.path.join(run_dir, "server", "Server"))
    s = session.make_server(run_dir, rec, reuse=True)
    assert Calls.restored == []
    assert s.cache == os.path.abspath(os.path.join(run_dir, "server"))
    assert (s.name, s.port, s.rcon_port, s.mods) == ("pzt", 27261, 27015, ["PZTestKit"])


def test_reuse_refuses_a_run_dir_with_no_server_cache(tmp_path):
    rec = {"name": "default", "server": {"name": "pzt", "mods": ["PZTestKit"], "port": 1, "rcon_port": 2}}
    try:
        session.make_server(str(tmp_path), rec, reuse=True)
    except SystemExit as e:
        assert "reuse" in str(e)
    else:
        raise AssertionError("expected SystemExit")
