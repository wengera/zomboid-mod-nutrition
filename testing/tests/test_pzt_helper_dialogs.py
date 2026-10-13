"""Harness: no helper dialogs over the test clients. Client.prepare() sets three options.ini keys
false in place (every other byte kept, CRLF kept); Server.seed() blanks ServerWelcomeMessage."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pytest
from pzt import client as cl
from pzt import server as sv

KEYS = ("showSurvivalGuide", "showFirstTimeSearchTutorial", "showFirstAnimalZoneInfo")


def _client(tmp, debug=False):
    c = cl.Client(str(tmp), "127.0.0.1:16261", "bob", "pw", debug=debug, mods=())
    return c


def _prepare(c, monkeypatch):
    monkeypatch.setattr(cl.harness, "install", lambda *a, **k: [])
    monkeypatch.setattr(cl.harness, "enable_client_mods", lambda *a, **k: None)
    c.prepare()


def _opts(tmp):
    return os.path.join(str(tmp), "options.ini")


def _read(tmp):
    with open(_opts(tmp), "rb") as fh:
        return fh.read()


GAME = (b"showFirstAnimalZoneInfo=true\r\nshowFirstTimeSearchTutorial=true\r\n"
        b"showFirstTimeSneakTutorial=true\r\nshowSurvivalGuide=true\r\nzzz=1 \r\n")


@pytest.mark.parametrize("debug", [False, True])
def test_three_keys_false_other_lines_and_crlf_kept(tmp_path, monkeypatch, debug):
    open(_opts(tmp_path), "wb").write(GAME)
    _prepare(_client(tmp_path, debug), monkeypatch)
    assert _read(tmp_path) == (b"showFirstAnimalZoneInfo=false\r\nshowFirstTimeSearchTutorial=false\r\n"
                               b"showFirstTimeSneakTutorial=true\r\nshowSurvivalGuide=false\r\nzzz=1 \r\n")


def test_missing_key_appended_with_file_ending(tmp_path, monkeypatch):
    open(_opts(tmp_path), "wb").write(b"a=1\r\nshowSurvivalGuide=true")
    _prepare(_client(tmp_path), monkeypatch)
    data = _read(tmp_path)
    assert data.startswith(b"a=1\r\nshowSurvivalGuide=false\r\n")
    for k in KEYS:
        assert f"{k}=false\r\n".encode() in data
    assert b"\n" not in data.replace(b"\r\n", b"")


def test_seed_path_gets_the_keys(tmp_path, monkeypatch):
    c = _client(tmp_path)
    monkeypatch.setattr(cl.harness, "install", lambda *a, **k: [])
    monkeypatch.setattr(cl.harness, "enable_client_mods", lambda *a, **k: None)
    c.seed()
    data = _read(tmp_path).decode()
    assert "termsOfServiceVersion=1" in data
    for k in KEYS:
        assert f"{k}=false" in data


def test_twice_changes_nothing(tmp_path, monkeypatch):
    open(_opts(tmp_path), "wb").write(GAME)
    c = _client(tmp_path)
    _prepare(c, monkeypatch)
    first = _read(tmp_path)
    mtime = os.stat(_opts(tmp_path)).st_mtime_ns
    _prepare(c, monkeypatch)
    assert _read(tmp_path) == first
    assert os.stat(_opts(tmp_path)).st_mtime_ns == mtime


def test_debug_console_and_debugger_not_touched(tmp_path, monkeypatch):
    _prepare(_client(tmp_path, debug=True), monkeypatch)
    dbg = open(os.path.join(str(tmp_path), "debug-options.ini")).read()
    assert "DebugConsole" not in dbg and "Debugger" not in dbg


def test_server_seed_blanks_welcome_message(tmp_path, monkeypatch):
    s = sv.Server.__new__(sv.Server)
    s.cache = str(tmp_path); s.name = "pzt"; s.port = 16261; s.rcon_port = 27015; s.rcon_pw = "x"
    s.mods = []; s.workshop_items = []; s.workshop = False; s.mod_sources = {}; s.mod_skip = ()
    s.echo = None
    s.bus = type("B", (), {"reset": lambda self: None})()
    monkeypatch.setattr(sv.harness, "install", lambda *a, **k: [])
    os.makedirs(os.path.join(str(tmp_path), "Server"))
    open(s.ini, "w").write("ServerWelcomeMessage=Welcome <LINE> x\nPublic=false\n")
    s.seed()
    lines = open(s.ini).read().splitlines()
    assert "ServerWelcomeMessage=" in lines and "Public=false" in lines
