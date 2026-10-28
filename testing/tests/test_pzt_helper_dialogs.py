"""Harness: no helper dialogs over the test clients. Client.prepare() sets three options.ini keys
false in place (every other byte kept, CRLF kept); Server.seed() blanks ServerWelcomeMessage.
P23-AN: prepare() also closes the saved character-info window in the per-run Lua/layout.ini, moves
the chat window to the screen's bottom-left at its smallest height, and
starts a -debug client's debug console hidden (UI.DebugConsole.StartVisible=false)."""
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


def test_debug_console_closed_debugger_not_touched(tmp_path, monkeypatch):
    # P23-AN: the debug console starts hidden (UIManager.init reads UI.DebugConsole.StartVisible)
    _prepare(_client(tmp_path, debug=True), monkeypatch)
    dbg = open(os.path.join(str(tmp_path), "debug-options.ini")).read().splitlines()
    assert "UI.DebugConsole.StartVisible=false" in dbg
    assert "UI.DisableLogoState=true" in dbg and "UI.DisableWelcomeMessage=true" in dbg
    assert not any("Debugger" in line for line in dbg)


def test_release_client_writes_no_debug_options(tmp_path, monkeypatch):
    _prepare(_client(tmp_path, debug=False), monkeypatch)
    assert not os.path.exists(os.path.join(str(tmp_path), "debug-options.ini"))


# ---- P23-AN: the saved character-info window closed in the per-run layout.ini -------------

def _layout(tmp):
    return os.path.join(str(tmp), "Lua", "layout.ini")


LAYOUT = (b"chat x=7 y=8 width=9 height=10\r\n"   # before any [WxH] section: ReadIni has no screen for it
          b"[1280x720]\r\n"
          b"ISSearchWindow x=120 y=300 width=420 height=192 visible=false pin=true\r\n"
          b"charinfowindow x=300 y=100 visible=true pin=true tabs=info,skills,health,clothingIns,protection current=info\r\n"
          b"inventory0 x=213 y=0 width=427 height=240 visible=true pin=false column2=253 sortBy=nameInc\r\n"
          b"charinfowindow.health x=5 y=6 width=300 height=400 visible=true pin=true\r\n"
          b"chat x=15 y=320 width=500 height=200 visible=true locked=false\r\n"
          b"[1920x1080]\r\n"
          b"charinfowindow x=1 y=2 pin=false\r\n"
          b"chat x=40 y=50 width=600 locked=true\r\n")

EXPECTED = (b"chat x=7 y=8 width=9 height=10\r\n"
            b"[1280x720]\r\n"
            b"ISSearchWindow x=120 y=300 width=420 height=192 visible=false pin=true\r\n"
            b"charinfowindow x=300 y=100 visible=false pin=true tabs=info,skills,health,clothingIns,protection current=info\r\n"
            b"inventory0 x=213 y=0 width=427 height=240 visible=true pin=false column2=253 sortBy=nameInc\r\n"
            b"charinfowindow.health x=5 y=6 width=300 height=400 visible=false pin=true\r\n"
            b"chat x=0 y=630 width=500 height=90 visible=true locked=false\r\n"
            b"[1920x1080]\r\n"
            b"charinfowindow x=1 y=2 pin=false visible=false\r\n"
            b"chat x=0 y=990 width=600 locked=true height=90\r\n")


@pytest.mark.parametrize("debug", [False, True])
def test_layout_charinfo_closed_chat_moved_other_bytes_kept(tmp_path, monkeypatch, debug):
    os.makedirs(os.path.dirname(_layout(tmp_path)))
    open(_layout(tmp_path), "wb").write(LAYOUT)
    _prepare(_client(tmp_path, debug), monkeypatch)
    assert open(_layout(tmp_path), "rb").read() == EXPECTED


def test_chat_bottom_left_at_its_smallest_height():
    # the chat's bottom edge is the screen's, so ISResizeWidget:resize's screen cap holds it at CHAT_HEIGHT
    assert cl.CHAT_HEIGHT == 90
    tokens = "chat x=15 y=320 width=500 height=200 visible=true locked=false".split(" ")
    out = dict(t.split("=", 1) for t in cl._uncover_layout_line(tokens, 720)[1:])
    assert (out["x"], int(out["y"]) + int(out["height"])) == ("0", 720)
    assert out["width"] == "500" and out["visible"] == "true" and out["locked"] == "false"


def test_layout_missing_file_left_missing(tmp_path, monkeypatch):
    _prepare(_client(tmp_path, debug=True), monkeypatch)
    assert not os.path.exists(_layout(tmp_path))


def test_layout_already_uncovered_untouched(tmp_path, monkeypatch):
    os.makedirs(os.path.dirname(_layout(tmp_path)))
    body = (b"[1280x720]\nchat x=0 y=630 height=90 visible=true locked=false\n"
            b"charinfowindowX x=1 y=1 visible=true\nchatter x=5 y=5 height=300\n")
    open(_layout(tmp_path), "wb").write(body)
    mtime = os.stat(_layout(tmp_path)).st_mtime_ns
    _prepare(_client(tmp_path), monkeypatch)
    assert open(_layout(tmp_path), "rb").read() == body
    assert os.stat(_layout(tmp_path)).st_mtime_ns == mtime


def test_layout_twice_changes_nothing(tmp_path, monkeypatch):
    os.makedirs(os.path.dirname(_layout(tmp_path)))
    open(_layout(tmp_path), "wb").write(LAYOUT)
    c = _client(tmp_path, debug=True)
    _prepare(c, monkeypatch)
    first = open(_layout(tmp_path), "rb").read()
    mtime = os.stat(_layout(tmp_path)).st_mtime_ns
    _prepare(c, monkeypatch)
    assert open(_layout(tmp_path), "rb").read() == first == EXPECTED
    assert os.stat(_layout(tmp_path)).st_mtime_ns == mtime


def test_layout_falsifier_a_prepare_that_skips_the_layout_fails(tmp_path, monkeypatch):
    os.makedirs(os.path.dirname(_layout(tmp_path)))
    open(_layout(tmp_path), "wb").write(LAYOUT)
    monkeypatch.setattr(cl, "edit_layout", lambda *a, **k: None)
    _prepare(_client(tmp_path), monkeypatch)
    after = open(_layout(tmp_path), "rb").read()
    assert after == LAYOUT and after != EXPECTED


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
