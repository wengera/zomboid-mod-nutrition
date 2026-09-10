"""Pure-Python tests for the profile loader and the sandbox merge: no game, no fixture blob.

The two that DO need something on this machine (a subscribed workshop item, the golden
fixture's gitignored cache) are gated and skip themselves elsewhere.
"""
import contextlib, json, os, shutil, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pytest
from pzt import fixture as fx
from pzt import profile, server
from pzt.paths import FIXTURES, HARNESS_MODS, WORKSHOP_DIR

KEEN_ITEM = "3685392864"          # KeenPerception, spike S3's subject
MULTI_ITEM = "3621968227"         # one workshop item shipping several mods
KIT = HARNESS_MODS["PZTestKit"]

# A SandboxVars.lua in the shape the server writes one: top-level options at four spaces,
# a nested table opening at that same indent with its own options at eight, CRLF throughout.
SANDBOX = ("SandboxVars = {\r\n"
           "    VERSION = 6,\r\n"
           "    -- 6 = None\r\n"
           "    Zombies = 6,\r\n"
           "    Map = {\r\n"
           "        ZombiesDragDown = true,\r\n"
           "    },\r\n"
           "}\r\n")


def _write(path, text, newline=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline=newline) as fh:
        fh.write(text)
    return path


@contextlib.contextmanager
def workspace(toml, sandbox=SANDBOX, name="p"):
    """A throwaway testing/profiles + testing/fixtures pair, so load() reads both without
    touching the repo's own (the fixture cache is gitignored and machine-local)."""
    with tempfile.TemporaryDirectory() as d:
        profiles, fixtures = os.path.join(d, "profiles"), os.path.join(d, "fixtures")
        _write(os.path.join(profiles, f"{name}.toml"), toml, newline=None)
        _write(os.path.join(fixtures, "default", "cache", "server", "Server", "pzt_SandboxVars.lua"),
               sandbox)
        _write(os.path.join(fixtures, "default", "fixture.json"),
               json.dumps({"name": "default", "build": "42.20.4",
                           "server": {"name": "pzt", "mods": ["PZTestKit"]},
                           "clients": {"admin": {}}}), newline=None)
        old = (profile.PROFILES, fx.FIXTURES)
        profile.PROFILES, fx.FIXTURES = profiles, fixtures
        try:
            yield d
        finally:
            profile.PROFILES, fx.FIXTURES = old


# ---- resolve_mod: one [[mods]] table -> (id, source dir, workshop item) ------------------

def test_resolve_by_workshop_id():
    """The acceptance profile's own entry: item -> its single mods/ folder."""
    keen = os.path.join(WORKSHOP_DIR, KEEN_ITEM, "mods", "KeenPerception")
    if not os.path.isdir(keen):
        pytest.skip(f"workshop item {KEEN_ITEM} not installed")
    assert profile.resolve_mod({"id": "KeenPerception", "workshop_id": KEEN_ITEM}, {}) == \
        ("KeenPerception", keen, KEEN_ITEM)
    # the id is optional when the item ships exactly one mod: mod.info supplies it
    assert profile.resolve_mod({"workshop_id": KEEN_ITEM}, {}) == ("KeenPerception", keen, KEEN_ITEM)


def test_resolve_by_harness_id():
    assert profile.resolve_mod({"id": "PZTestKit"}, {}) == ("PZTestKit", KIT, None)


def test_resolve_by_path():
    """Relative paths are from the repo root, and the id comes from the folder's mod.info."""
    got = profile.resolve_mod({"path": os.path.join("testing", "PZTestKit", "PZTestKit")}, {})
    assert got == ("PZTestKit", os.path.normpath(KIT), None)


def test_resolve_by_index():
    """A bare id that is neither harness nor local: the workshop index answers it."""
    index = {"Some": (r"D:\ws\1\mods\Some", "1")}
    assert profile.resolve_mod({"id": "Some"}, index) == ("Some", r"D:\ws\1\mods\Some", "1")


def test_copy_false_places_nothing_but_needs_an_id():
    assert profile.resolve_mod({"id": "NoSuchModHere", "copy": False}, {}) == \
        ("NoSuchModHere", None, None)
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve_mod({"copy": False}, {})
    assert "id" in str(e.value)


def test_bogus_workshop_id_names_the_dir_it_looked_in():
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve_mod({"workshop_id": "1"}, {})
    assert WORKSHOP_DIR in str(e.value) and "not installed" in str(e.value)


def test_multi_mod_item_needs_an_id_to_pick_with():
    item_dir = os.path.join(WORKSHOP_DIR, MULTI_ITEM, "mods")
    subdirs = [e for e in (os.listdir(item_dir) if os.path.isdir(item_dir) else [])
               if os.path.isdir(os.path.join(item_dir, e))]
    if len(subdirs) < 2:
        pytest.skip(f"workshop item {MULTI_ITEM} (multi-mod) not installed")
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve_mod({"workshop_id": MULTI_ITEM}, {})
    assert "ships" in str(e.value)
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve_mod({"workshop_id": MULTI_ITEM, "id": "NotInThere"}, {})
    assert "no mod with id" in str(e.value)


def test_uninstalled_id_reports_the_index_size():
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve_mod({"id": "NotAMod"}, {"A": ("x", "1")})
    assert "1 mods indexed" in str(e.value) and WORKSHOP_DIR in str(e.value)


def test_declared_id_must_agree_with_mod_info():
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve_mod({"id": "Wrong", "path": os.path.join("testing", "PZTestKit", "PZTestKit")}, {})
    assert "'Wrong'" in str(e.value) and "'PZTestKit'" in str(e.value)


def test_folder_without_mod_info_points_at_mod_lint():
    with tempfile.TemporaryDirectory() as d:
        with pytest.raises(profile.ProfileError) as e:
            profile.resolve_mod({"path": d}, {})
        assert "tools/mod_lint.py" in str(e.value)


def test_missing_path_and_unknown_keys_are_errors():
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve_mod({"path": os.path.join("testing", "nope")}, {})
    assert "not a directory" in str(e.value)
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve_mod({}, {})
    assert "needs one of: id, workshop_id, path" in str(e.value)
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve_mod({"id": "PZTestKit", "mod_id": "PZTestKit"}, {})
    assert "unknown key(s) mod_id" in str(e.value)


# ---- load(): the whole file ------------------------------------------------------------

def test_harness_is_prepended_when_a_profile_forgets_it():
    with workspace('[[mods]]\nid = "Ghost"\ncopy = false\n'):
        p = profile.load("p")
    assert p.mods == ["PZTestKit", "Ghost"]        # index 0: no harness, no bus, no ready marker
    assert p.skip == ("Ghost",) and p.sources == {"PZTestKit": KIT}
    assert p.items == {}


def test_defaults_match_the_cli():
    with workspace('fixture = "default"\ndescription = "d"\n[[mods]]\nid = "PZTestKit"\n'):
        p = profile.load("p")
    assert (p.name, p.fixture, p.description) == ("p", "default", "d")
    assert (p.hold, p.safemode, p.launcher) == (5, False, "java")
    assert (p.server_timeout, p.client_timeout) == (420, 300)
    assert p.users == ["admin"] and p.verify == [] and p.sandbox == {}
    assert p.mods == ["PZTestKit"] and p.skip == ()
    assert p.report()["sources"] == {"PZTestKit": KIT}


def test_run_server_client_tables_override_the_defaults():
    toml = ('run = { hold = 9 }\nserver = { timeout = 60 }\n'
            'client = { timeout = 30, users = ["admin", "tester"], safemode = true, launcher = "exe" }\n'
            'verify = [ { side = "client", cmd = "trait.check", expect = "true" } ]\n'
            '[[mods]]\nid = "PZTestKit"\n')
    with workspace(toml):
        p = profile.load("p")
    assert (p.hold, p.server_timeout, p.client_timeout) == (9, 60, 30)
    assert (p.safemode, p.launcher, p.users) == (True, "exe", ["admin", "tester"])
    assert p.verify[0]["cmd"] == "trait.check"


def test_duplicate_ids_are_named_once():
    toml = '[[mods]]\nid = "PZTestKit"\n\n[[mods]]\nid = "PZTestKit"\n'
    with workspace(toml):
        assert profile.load("p").mods == ["PZTestKit"]


def test_unknown_sandbox_key_suggests_the_real_one():
    with workspace('[sandbox]\nZombiess = 6\n'):
        with pytest.raises(profile.ProfileError) as e:
            profile.load("p")
    assert "Zombiess" in str(e.value) and "Zombies" in str(e.value)


def test_nested_options_and_table_names_are_not_settable():
    """The lookahead in SANDBOX_KEY_RX keeps `Map` (a table opener) and its eight-space
    options out of the known set, so naming either fails instead of no-op'ing."""
    for key in ("Map", "ZombiesDragDown"):
        with workspace(f"[sandbox]\n{key} = 1\n"):
            with pytest.raises(profile.ProfileError) as e:
                profile.load("p")
        assert key in str(e.value)


def test_known_sandbox_keys_pass_through_with_their_types():
    with workspace('[sandbox]\nZombies = 4\nVERSION = 6\n'):
        assert profile.load("p").sandbox == {"Zombies": 4, "VERSION": 6}


def test_unknown_tables_and_keys_are_rejected():
    for toml, needle in [('mod = "x"\n', "unknown key(s) mod"),
                         ('[extras]\na = 1\n', "unknown key(s) extras"),
                         ('run = { hold = 1, users = ["a"] }\n', "[run]"),
                         ('server = { timeout = 1, port = 2 }\n', "[server]"),
                         ('client = { debug = true }\n', "[client]"),
                         ('client = { launcher = "steam" }\n', "launcher must be"),
                         ('verify = [ { side = "both", cmd = "ping" } ]\n', "side must be"),
                         ('verify = [ { expect = "x" } ]\n', "needs a cmd")]:
        with workspace(toml):
            with pytest.raises(profile.ProfileError) as e:
                profile.load("p")
        assert needle in str(e.value), toml


def test_missing_profile_lists_the_ones_that_exist():
    with workspace("", name="mod-under-test"):
        with pytest.raises(profile.ProfileError) as e:
            profile.load("nope")
    msg = str(e.value)
    assert "nope.toml" in msg and "have: mod-under-test" in msg


def test_broken_toml_is_a_profile_error_not_a_traceback():
    with workspace("fixture = \n"):
        with pytest.raises(profile.ProfileError) as e:
            profile.load("p")
    assert "not valid TOML" in str(e.value)
    assert isinstance(profile.ProfileError("x"), SystemExit)   # the CLI exits without a traceback


def test_a_path_ending_in_toml_is_taken_as_given():
    with workspace('[[mods]]\nid = "PZTestKit"\n') as d:
        p = profile.load(os.path.join(d, "profiles", "p.toml"))
    assert p.name == "p" and p.mods == ["PZTestKit"]


def test_missing_fixture_raises_the_fixtures_own_error():
    with workspace('fixture = "nosuch"\n'):
        with pytest.raises(SystemExit) as e:
            profile.load("p")
    assert "fixture 'nosuch' not found" in str(e.value)


# ---- the sandbox merge ------------------------------------------------------------------

def test_merge_rewrites_only_the_named_keys():
    with tempfile.TemporaryDirectory() as d:
        p = _write(os.path.join(d, "pzt_SandboxVars.lua"), SANDBOX)
        applied, appended = server.merge_sandbox_vars(p, {"Zombies": 4, "DayLength": 1})
        assert (applied, appended) == (["Zombies"], ["DayLength"])
        with open(p, encoding="utf-8", newline="") as fh:
            out = fh.read()
    assert "    Zombies = 4,\r\n" in out and "Zombies = 6" not in out
    assert "    Map = {\r\n" in out                          # table opener untouched
    assert "        ZombiesDragDown = true,\r\n" in out      # nested option untouched
    assert "    -- 6 = None\r\n" in out                      # the server's comments survive
    assert out.endswith("    DayLength = 1,\r\n}\r\n")       # appended before the final brace
    assert out.replace("\r\n", "") .count("\n") == 0         # CRLF everywhere, still


def test_merge_writes_lua_booleans_and_keeps_lf_files_lf():
    with tempfile.TemporaryDirectory() as d:
        p = _write(os.path.join(d, "s.lua"), SANDBOX.replace("\r\n", "\n"))
        server.merge_sandbox_vars(p, {"Zombies": False, "NewFlag": True})
        with open(p, encoding="utf-8", newline="") as fh:
            out = fh.read()
    assert "\r" not in out
    assert "    Zombies = false,\n" in out and out.endswith("    NewFlag = true,\n}\n")


def test_sandbox_keys_are_the_settable_options_only():
    with tempfile.TemporaryDirectory() as d:
        p = _write(os.path.join(d, "s.lua"), SANDBOX)
        assert server.sandbox_keys(p) == ["VERSION", "Zombies"]


def test_write_sandbox_vars_still_writes_a_partial_table():
    """The fresh-cache path is unchanged -- same text as before, booleans aside."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.lua")
        server.write_sandbox_vars(p, {"Zombies": "6", "Flag": True})
        with open(p, encoding="utf-8") as fh:
            assert fh.read() == "SandboxVars = {\n    VERSION = 6,\n    Zombies = 6,\n    Flag = true,\n}\n"


def _read(path):
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        return fh.read()


def test_merge_on_a_copy_of_the_real_fixture_file():
    """The read-only check the plan asks for, on the golden fixture's own 1020-line file:
    one line changes, nothing else -- key set, line count and CRLF all identical.

    184 settable options, not the plan's 189: that count includes the five nested-table
    openers (Basement, Map, ZombieLore, ZombieConfig, MultiplierConfig), which sit at the
    same four-space indent but are not settable (189 = 184 + 5; 86 more options are nested
    inside them at eight spaces)."""
    real = os.path.join(FIXTURES, "default", "cache", "server", "Server", "pzt_SandboxVars.lua")
    if not os.path.exists(real):
        pytest.skip("fixture 'default' cache not on this machine (gitignored)")
    with tempfile.TemporaryDirectory() as d:
        copy = os.path.join(d, "pzt_SandboxVars.lua")
        shutil.copyfile(real, copy)
        before_keys, before = server.sandbox_keys(copy), _read(copy)
        applied, appended = server.merge_sandbox_vars(copy, {"DayLength": 1})
        after_keys, after = server.sandbox_keys(copy), _read(copy)
    assert (applied, appended) == (["DayLength"], [])
    assert after_keys == before_keys and len(before_keys) == 184
    assert before.count("\r\n") == after.count("\r\n") == 1020
    changed = [(a, b) for a, b in zip(before.split("\r\n"), after.split("\r\n")) if a != b]
    assert changed == [("    DayLength = 4,", "    DayLength = 1,")]
