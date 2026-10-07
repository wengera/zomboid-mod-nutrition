"""Plan 10 Task S6: a per-client mod source override, `[client_overrides.<user>] <ModId> = "path"`.

The key gives ONE attached client a different folder for one mod the profile already lists, so
the server and every other client keep the profile's own source (the Lua checksum arm needs one
client whose copy differs). Pure Python: no game, no fixture blob; `harness.install` is stubbed
the way `test_pzt_lint_gate.py` stubs seeding.
"""
import argparse, contextlib, json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pytest
from pzt import cli, client, harness, profile, session
from pzt import fixture as fx

SANDBOX = "SandboxVars = {\r\n    VERSION = 6,\r\n    Zombies = 6,\r\n}\r\n"
TWO = {"admin": {"password": "pzt-admin-pw", "debug": True},
       "bob": {"password": "bob-pw", "debug": False}}


def _write(path, text, newline=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline=newline) as fh:
        fh.write(text)
    return path


def _mod(root, folder, mod_id):
    """A minimal mod folder: `42/mod.info` declaring `mod_id`."""
    d = os.path.join(root, folder)
    _write(os.path.join(d, "42", "mod.info"), f"name={mod_id}\nid={mod_id}\n")
    return d


@contextlib.contextmanager
def workspace(body):
    """A throwaway profiles + fixtures pair (fixture `two`, admin and bob) and two copies of one
    mod, `A` (the profile's) and `B` (the override). `body` is formatted with {a} and {b}."""
    with tempfile.TemporaryDirectory() as d:
        a, b = _mod(d, "A", "TKX_A"), _mod(d, "B", "TKX_A")
        profiles, fixdir = os.path.join(d, "profiles"), os.path.join(d, "fixtures")
        text = body.format(a=a.replace("\\", "/"), b=b.replace("\\", "/"), d=d.replace("\\", "/"))
        _write(os.path.join(profiles, "p.toml"), text, newline=None)
        _write(os.path.join(fixdir, "two", "cache", "server", "Server", "pzt_SandboxVars.lua"), SANDBOX)
        _write(os.path.join(fixdir, "two", "fixture.json"),
               json.dumps({"name": "two", "build": "42.20.4",
                           "server": {"name": "pzt", "mods": ["PZTestKit"]}, "clients": TWO}), newline=None)
        old = (profile.PROFILES, fx.FIXTURES)
        profile.PROFILES, fx.FIXTURES = profiles, fixdir
        try:
            yield {"a": os.path.normpath(a), "b": os.path.normpath(b), "d": d}
        finally:
            profile.PROFILES, fx.FIXTURES = old


HEAD = 'fixture = "two"\nclients = ["admin", "bob"]\n'
MODS = '\n[[mods]]\nid = "PZTestKit"\n[[mods]]\nid = "TKX_A"\npath = "{a}"\n'


def _toml(override=""):
    return HEAD + MODS + override


# ---- the profile ----------------------------------------------------------------------------

def test_the_parsed_profile_carries_the_override():
    with workspace(_toml('\n[client_overrides.bob]\nTKX_A = "{b}"\n')) as w:
        p = profile.load("p")
    assert p.client_overrides == {"bob": {"TKX_A": w["b"]}}
    assert os.path.normpath(p.sources["TKX_A"]) == w["a"]   # the server's source is unchanged
    assert p.report()["client_overrides"] == {"bob": {"TKX_A": w["b"]}}


def test_a_profile_without_the_key_has_no_override():
    with workspace(_toml()):
        p = profile.load("p")
    assert p.client_overrides == {}
    assert p.report()["client_overrides"] == {}


def test_an_override_naming_an_unknown_user_is_a_profile_error():
    with workspace(_toml('\n[client_overrides.carol]\nTKX_A = "{b}"\n')):
        with pytest.raises(profile.ProfileError, match="carol"):
            profile.load("p")


def test_an_override_naming_an_unlisted_mod_is_a_profile_error():
    with workspace(_toml('\n[client_overrides.bob]\nTKX_Other = "{b}"\n')):
        with pytest.raises(profile.ProfileError, match="TKX_Other"):
            profile.load("p")


def test_an_override_on_a_mod_that_is_not_placed_is_a_profile_error():
    body = HEAD + '\n[[mods]]\nid = "TKX_A"\ncopy = false\n\n[client_overrides.bob]\nTKX_A = "{b}"\n'
    with workspace(body):
        with pytest.raises(profile.ProfileError, match="TKX_A"):
            profile.load("p")


def test_an_override_path_that_is_not_a_folder_is_a_profile_error():
    with workspace(_toml('\n[client_overrides.bob]\nTKX_A = "{d}/nowhere"\n')):
        with pytest.raises(profile.ProfileError, match="not a directory"):
            profile.load("p")


def test_an_override_folder_declaring_another_id_is_a_profile_error():
    with workspace(_toml('\n[client_overrides.bob]\nTKX_A = "{d}/C"\n')) as w:
        _mod(w["d"], "C", "TKX_C")
        with pytest.raises(profile.ProfileError, match="TKX_C"):
            profile.load("p")


@pytest.mark.parametrize("value", ['"x"', '{{ TKX_A = 3 }}'])
def test_an_override_that_is_not_a_table_of_paths_is_a_profile_error(value):
    with workspace(HEAD + "client_overrides = {{ bob = " + value + " }}\n" + MODS):
        with pytest.raises(profile.ProfileError, match="client_overrides"):
            profile.load("p")


# ---- seeding: the override reaches the named user's cache only --------------------------------

def test_seed_installs_the_override_for_bob_and_the_normal_path_for_admin(monkeypatch, tmp_path):
    installed = {}

    def fake_install(mods_dir, mod_ids, workshop=True, sources=None, skip=()):
        installed[os.path.basename(os.path.dirname(mods_dir))] = dict(sources or {})
        return []
    monkeypatch.setattr(harness, "install", fake_install)
    monkeypatch.setattr(client.Client, "start", lambda self: None)
    monkeypatch.setattr(client.Client, "wait_ready", lambda self, timeout=300: 1.0)
    srv = argparse.Namespace(port=27261, mods=["PZTestKit", "TKX_A"],
                             mod_sources={"PZTestKit": "/kit", "TKX_A": "/a"}, mod_skip=())
    prof = argparse.Namespace(users=["admin", "bob"], safemode=False, launcher="java", client_timeout=5,
                              client_overrides={"bob": {"TKX_A": "/b"}})
    out = session.attach_clients(str(tmp_path), prof, srv, None, session.Timeline())
    # rec=None: each client is seeded fresh under <run>/clients/<user>/mods
    assert installed == {"admin": {"PZTestKit": "/kit", "TKX_A": "/a"},
                         "bob": {"PZTestKit": "/kit", "TKX_A": "/b"}}
    assert out["admin"].mod_sources["TKX_A"] == "/a" and out["bob"].mod_sources["TKX_A"] == "/b"
    assert srv.mod_sources == {"PZTestKit": "/kit", "TKX_A": "/a"}     # the server's map is not mutated


def test_attach_clients_passes_no_extra_argument_without_an_override():
    made = []

    class FC:
        def __init__(self, user):
            self.username = user

        def start(self):
            pass

        def wait_ready(self, timeout=None):
            return 1.0

    def make(run_dir, user, server, rec=None, **kw):
        made.append((user, kw))
        return FC(user), True
    prof = argparse.Namespace(users=["admin", "bob"], safemode=False, launcher="java", client_timeout=5,
                              client_overrides={})
    srv = argparse.Namespace(mod_sources={"TKX_A": "/a"})
    session.attach_clients("run", prof, srv, None, session.Timeline(), make_client=make)
    assert made == [("admin", {"safemode": False, "launcher": "java"}),
                    ("bob", {"safemode": False, "launcher": "java"})]


# ---- the lint gate lints the override folder too ---------------------------------------------

def test_lint_sources_adds_each_override_folder():
    prof = argparse.Namespace(client_overrides={"bob": {"TKX_A": "/b"}})
    got = profile.lint_sources(prof, {"TKX_A": "/a"})
    assert sorted(got.values()) == ["/a", "/b"]
    assert profile.lint_sources(None, {"TKX_A": "/a"}) == {"TKX_A": "/a"}
    assert profile.lint_sources(argparse.Namespace(), {"TKX_A": "/a"}) == {"TKX_A": "/a"}


def test_run_lints_the_override_folder_before_any_seed(monkeypatch):
    seen = {}

    def boom(*a, **k):
        raise AssertionError("seeded after a failed lint")

    def lint(sources):
        seen["sources"] = dict(sources)
        return ["B: ERROR: version-dir: none"]
    prof = argparse.Namespace(client_overrides={"bob": {"TKX_A": "/b"}})
    monkeypatch.setattr(cli, "profile_args", lambda a: (prof, None, {"mod_sources": {"TKX_A": "/a"}}))
    monkeypatch.setattr(harness, "lint_paths", lint)
    monkeypatch.setattr(fx, "load", boom)
    monkeypatch.setattr(cli, "make_server", boom)
    monkeypatch.setattr(cli, "new_run_dir", boom)
    assert cli.cmd_run(argparse.Namespace()) == 2
    assert "/b" in seen["sources"].values() and "/a" in seen["sources"].values()
