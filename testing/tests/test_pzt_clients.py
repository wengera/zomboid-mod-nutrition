"""Plan 8 Task 1: the two-client fixture's driver side, pure Python (no game, no fixture blob).

The profile's top-level `clients` key (default ["admin"], validated against the fixture's own
provisioned clients), `bus.resolve_side` (the drivers' `server` / `client` / `client:<user>`
side, the bare `client` staying `admin` so every existing driver and profile reads as before),
`session.attach_clients` (each listed user launched in turn, each ready before the next), and the
`[[verify]]` rows on a named client.
"""
import argparse, contextlib, json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pytest
from pzt import bus, cli, profile, session
from pzt import fixture as fx

SANDBOX = ("SandboxVars = {\r\n"
           "    VERSION = 6,\r\n"
           "    Zombies = 6,\r\n"
           "}\r\n")

TWO = {"admin": {"password": "pzt-admin-pw", "debug": True},
       "bob": {"password": "bob-pw", "debug": False}}


def _write(path, text, newline=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline=newline) as fh:
        fh.write(text)
    return path


@contextlib.contextmanager
def workspace(toml, name="p", fixture="two", clients=None):
    """A throwaway profiles + fixtures pair whose fixture record lists `clients`."""
    with tempfile.TemporaryDirectory() as d:
        profiles, fixdir = os.path.join(d, "profiles"), os.path.join(d, "fixtures")
        _write(os.path.join(profiles, f"{name}.toml"), toml, newline=None)
        _write(os.path.join(fixdir, fixture, "cache", "server", "Server", "pzt_SandboxVars.lua"), SANDBOX)
        _write(os.path.join(fixdir, fixture, "fixture.json"),
               json.dumps({"name": fixture, "build": "42.20.4",
                           "server": {"name": "pzt", "mods": ["PZTestKit"]},
                           "clients": clients if clients is not None else TWO}), newline=None)
        old = (profile.PROFILES, fx.FIXTURES)
        profile.PROFILES, fx.FIXTURES = profiles, fixdir
        try:
            yield d
        finally:
            profile.PROFILES, fx.FIXTURES = old


def toml(head="", fixture="two", verify=""):
    """Bare keys first (TOML: they must precede the first table header)."""
    return f'fixture = "{fixture}"\n{head}{verify}\n[[mods]]\nid = "PZTestKit"\n'


class Node:
    def __init__(self, name, acks=None):
        self.username, self.acks, self.sent = name, acks or {}, []

    def send(self, cmd, args="", **kw):
        self.sent.append((cmd, args))
        return self.acks.get(cmd, "ok:" + self.username)


# ---- the profile's `clients` key ---------------------------------------------------------

def test_clients_defaults_to_admin_alone():
    """Every existing profile has no `clients` key and attaches exactly what it did before."""
    with workspace(toml(fixture="default"), fixture="default", clients={"admin": {}}):
        p = profile.load("p")
    assert p.clients == ["admin"] and p.users == ["admin"]


def test_clients_lists_the_fixture_users_a_run_attaches_in_order():
    with workspace(toml('clients = ["admin", "bob"]\n')):
        p = profile.load("p")
    assert p.clients == ["admin", "bob"] and p.users == ["admin", "bob"]
    with workspace(toml('clients = ["bob"]\n')):
        assert profile.load("p").clients == ["bob"]


def test_clients_naming_a_user_the_fixture_never_provisioned_is_a_pre_boot_error():
    with workspace(toml('clients = ["admin", "carol"]\n')):
        with pytest.raises(profile.ProfileError) as e:
            profile.load("p")
    msg = str(e.value)
    assert "carol" in msg and "admin" in msg and "bob" in msg and "two" in msg


@pytest.mark.parametrize("value", ['[]', '"admin"', '["admin", 3]', '["admin", "admin"]'])
def test_clients_must_be_a_non_empty_list_of_distinct_names(value):
    with workspace(toml(f'clients = {value}\n')):
        with pytest.raises(profile.ProfileError) as e:
            profile.load("p")
    assert "clients" in str(e.value)


def test_clients_and_a_conflicting_client_users_list_are_refused():
    """Two spellings of one list: the profile must not name two different sets."""
    head = 'clients = ["admin", "bob"]\nclient = { users = ["admin"] }\n'
    with workspace(toml(head)):
        with pytest.raises(profile.ProfileError) as e:
            profile.load("p")
    assert "clients" in str(e.value) and "users" in str(e.value)
    same = 'clients = ["admin", "bob"]\nclient = { users = ["admin", "bob"] }\n'
    with workspace(toml(same)):
        assert profile.load("p").clients == ["admin", "bob"]


def test_a_verify_row_may_name_a_listed_client():
    verify = ('verify = [ { side = "client:bob", cmd = "lua.global", args = "TK.version" },\n'
              '           { side = "client", cmd = "lua.global", args = "TK.version" } ]\n')
    with workspace(toml('clients = ["admin", "bob"]\n', verify=verify)):
        p = profile.load("p")
    assert [v["side"] for v in p.verify] == ["client:bob", "client"]


@pytest.mark.parametrize("side,why", [("client:bob", "bob"), ("player", "player")])
def test_a_verify_row_on_an_unlisted_client_or_an_unknown_side_is_refused(side, why):
    verify = f'verify = [ {{ side = "{side}", cmd = "ping" }} ]\n'
    with workspace(toml('clients = ["admin"]\n', verify=verify)):
        with pytest.raises(profile.ProfileError) as e:
            profile.load("p")
    assert why in str(e.value)


# ---- bus.resolve_side --------------------------------------------------------------------

def nodes():
    server, admin, bob = Node("server"), Node("admin"), Node("bob")
    return server, {"admin": admin, "bob": bob}


def test_resolve_side_server_client_and_named_clients():
    server, clients = nodes()
    assert bus.resolve_side("server", server, clients) is server
    assert bus.resolve_side("client", server, clients) is clients["admin"]   # bare client = admin
    assert bus.resolve_side("client:admin", server, clients) is clients["admin"]
    assert bus.resolve_side("client:bob", server, clients) is clients["bob"]


def test_resolve_side_bare_client_is_the_first_client_when_admin_is_absent():
    server, clients = nodes()
    only_bob = {"bob": clients["bob"]}
    assert bus.resolve_side("client", server, only_bob) is clients["bob"]


def test_resolve_side_takes_the_list_the_run_path_holds():
    """`cmd_run` and `scenario.run` keep their clients as a list (teardown order); a list is
    keyed by each node's own username."""
    server, clients = nodes()
    as_list = [clients["bob"], clients["admin"]]
    assert bus.resolve_side("client", server, as_list) is clients["admin"]
    assert bus.resolve_side("client:bob", server, as_list) is clients["bob"]


def test_resolve_side_passes_a_node_through_so_object_style_drivers_keep_working():
    server, clients = nodes()
    assert bus.resolve_side(server, server, clients) is server
    assert bus.resolve_side(clients["bob"], server, clients) is clients["bob"]


def test_resolve_side_unknown_user_is_a_clear_keyerror_naming_the_attached():
    server, clients = nodes()
    with pytest.raises(KeyError) as e:
        bus.resolve_side("client:carol", server, clients)
    msg = str(e.value)
    assert "carol" in msg and "admin" in msg and "bob" in msg
    assert not msg.startswith("'")          # a sentence, not KeyError's quoted repr
    with pytest.raises(KeyError) as e:
        bus.resolve_side("client", server, {})
    assert "no client" in str(e.value)


def test_resolve_side_refuses_a_side_that_is_neither():
    server, clients = nodes()
    with pytest.raises(ValueError) as e:
        bus.resolve_side("clients:bob", server, clients)
    assert "clients:bob" in str(e.value)


# ---- verify() on a named client ----------------------------------------------------------

def test_verify_routes_a_named_client_row_to_that_client():
    server, clients = nodes()
    prof = argparse.Namespace(verify=[
        {"side": "client:bob", "cmd": "lua.global", "args": "TK.version", "expect": "bob"},
        {"side": "client", "cmd": "lua.global", "args": "TK.version", "expect": "admin"},
        {"side": "client:carol", "cmd": "ping"}])
    tl = session.Timeline()
    out = session.verify(prof, server, [clients["admin"], clients["bob"]], tl)
    assert [v["ok"] for v in out] == [True, True, False]
    assert clients["bob"].sent == [("lua.global", "TK.version")]
    assert clients["admin"].sent == [("lua.global", "TK.version")]
    assert "carol" in out[2]["got"] and out[2]["got"] == tl.items[2]["got"]
    assert [m["side"] for m in tl.items] == ["client:bob", "client", "client:carol"]


# ---- session.attach_clients ---------------------------------------------------------------

class FakeClient:
    def __init__(self, user, log, debug):
        self.username, self.log, self.debug, self.alive = user, log, debug, False

    def start(self):
        self.alive = True
        self.log.append(("start", self.username))

    def wait_ready(self, timeout=None):
        self.log.append(("ready", self.username, timeout))
        return 30.0 if self.username == "admin" else 40.0


def fake_make(log, made):
    def make(run_dir, user, server, rec=None, **kw):
        made.append((user, kw))
        info = (rec or {}).get("clients", {}).get(user, {})
        return FakeClient(user, log, info.get("debug", user == "admin")), True
    return make


def test_attach_clients_launches_each_in_turn_and_returns_them_by_name():
    log, made, started = [], [], []
    rec = {"name": "two", "clients": TWO}
    prof = argparse.Namespace(users=["admin", "bob"], clients=["admin", "bob"], safemode=False,
                              launcher="java", client_timeout=120)
    tl = session.Timeline()
    out = session.attach_clients("run", prof, Node("server"), rec, tl, started=started,
                                 make_client=fake_make(log, made))
    assert list(out) == ["admin", "bob"]
    # one at a time: admin is ready before bob is launched
    assert log == [("start", "admin"), ("ready", "admin", 120), ("start", "bob"), ("ready", "bob", 120)]
    assert started == [out["admin"], out["bob"]]
    assert (out["admin"].debug, out["bob"].debug) == (True, False)   # the fixture's own flags
    assert [u for u, _ in made] == ["admin", "bob"]
    assert made[0][1] == {"safemode": False, "launcher": "java"}
    marks = [(m["phase"], m.get("user")) for m in tl.items]
    assert marks == [("client_launch", "admin"), ("client_ready", "admin"),
                     ("client_launch", "bob"), ("client_ready", "bob")]
    assert tl.items[3]["took"] == 40.0


def test_attach_clients_without_a_profile_takes_the_fixtures_clients_and_the_defaults():
    log, made = [], []
    rec = {"name": "two", "clients": TWO}
    out = session.attach_clients("run", None, Node("server"), rec, session.Timeline(),
                                 make_client=fake_make(log, made))
    assert list(out) == ["admin", "bob"]
    assert made[0][1] == {"safemode": profile.DEFAULTS["safemode"],
                          "launcher": profile.DEFAULTS["launcher"]}
    assert log[1] == ("ready", "admin", profile.DEFAULTS["client_timeout"])


def test_attach_clients_keeps_a_client_whose_wait_raised_for_the_teardown():
    log, started = [], []

    class Stall(FakeClient):
        def wait_ready(self, timeout=None):
            raise TimeoutError("bob: not ready")

    def make(run_dir, user, server, rec=None, **kw):
        cls = Stall if user == "bob" else FakeClient
        return cls(user, log, False), False
    with pytest.raises(TimeoutError):
        session.attach_clients("run", None, Node("server"), {"name": "two", "clients": TWO},
                               session.Timeline(), started=started, make_client=make)
    assert [c.username for c in started] == ["admin", "bob"]   # bob is there to be killed


def test_make_client_takes_the_fixtures_debug_flag(monkeypatch, tmp_path):
    """bob is a release client because the record says so, not because of his name."""
    seen = {}

    class C:
        def __init__(self, cache, server, user, password, debug=False, **kw):
            seen[user] = (password, debug)
            self.missing_mods = []

        def prepare(self):
            pass

        def seed(self):
            pass
    monkeypatch.setattr(session, "Client", C)
    monkeypatch.setattr(session.fx, "restore_client", lambda name, user, run_dir: (str(tmp_path), True))
    srv = argparse.Namespace(port=27261, mods=["PZTestKit"], mod_sources={}, mod_skip=())
    rec = {"name": "two", "clients": TWO}
    session.make_client(str(tmp_path), "admin", srv, rec)
    session.make_client(str(tmp_path), "bob", srv, rec)
    assert seen == {"admin": ("pzt-admin-pw", True), "bob": ("bob-pw", False)}


# ---- cmd_run attaches every listed client ---------------------------------------------------

def test_cmd_run_attaches_every_listed_client_and_verifies_on_each(monkeypatch, tmp_path):
    verify = ('verify = [ { side = "client", cmd = "lua.global", args = "TK.version", expect = "admin" },\n'
              '           { side = "client:bob", cmd = "lua.global", args = "TK.version", expect = "bob" } ]\n')
    made, sent = [], {}

    class FC:
        def __init__(self, user):
            self.username, self.events, self.seen, self.mods_not_found, self.alive = user, [], set(), [], True

        def start(self):
            pass

        def wait_ready(self, timeout=None):
            return 1.0

        def send(self, cmd, args="", **kw):
            sent.setdefault(self.username, []).append(cmd)
            return "ok:" + self.username

        def quit(self):
            self.alive = False
            return 0

        def kill(self):
            self.alive = False

        def results(self):
            return {}

    class FS(FC):
        def __init__(self):
            super().__init__("server")
            self.log_path, self.errors, self.build, self.port = str(tmp_path / "s.log"), [], "42.20.4", 1
            self.t_started, self.mods_not_found = 1.0, []

        def start(self, timeout=None):
            return self.t_started

        def stop(self):
            self.alive = False
            return 0

    def fake_make_client(run_dir, user, srv, rec=None, **kw):
        made.append(user)
        return FC(user), True
    monkeypatch.setattr(cli, "new_run_dir", lambda p: ("unit", str(tmp_path)))
    monkeypatch.setattr(cli, "make_server", lambda run_dir, rec=None, **kw: FS())
    monkeypatch.setattr(cli, "make_client", fake_make_client)
    monkeypatch.setattr(cli, "hold", lambda s, tl, srv, c: True)
    a = argparse.Namespace(profile="p", fixture=None, clients=None, port=None, rcon_port=None,
                           **{k: None for k in profile.DEFAULTS})
    with workspace(toml('clients = ["admin", "bob"]\n', verify=verify)):
        assert cli.cmd_run(a) == 0
    assert made == ["admin", "bob"]
    with open(tmp_path / "report.json") as fh:
        rep = json.load(fh)
    assert [v["ok"] for v in rep["verify"]] == [True, True]
    assert sorted(rep["clients"]) == ["admin", "bob"]
    assert sent["bob"] == ["ping", "lua.global"]
