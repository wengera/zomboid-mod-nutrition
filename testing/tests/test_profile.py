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
    """The source is a real folder on disk with a real mod.info in it -- asserting against
    HARNESS_MODS alone would pass on a lookup table that points nowhere."""
    mod_id, src, item = profile.resolve_mod({"id": "PZTestKit"}, {})
    assert (mod_id, item) == ("PZTestKit", None)
    assert os.path.normpath(src) == os.path.normpath(KIT)
    assert os.path.isdir(src) and os.path.isfile(os.path.join(src, "42", "mod.info"))


def test_resolve_by_path():
    """Relative paths are from the repo root, and the id comes from the folder's mod.info."""
    mod_id, src, item = profile.resolve_mod({"path": os.path.join("testing", "PZTestKit",
                                                                  "PZTestKit")}, {})
    assert (mod_id, item) == ("PZTestKit", None)
    assert os.path.normpath(src) == os.path.normpath(KIT)
    assert os.path.isdir(src) and os.path.isfile(os.path.join(src, "42", "mod.info"))


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
    assert out.replace("\r\n", "").count("\n") == 0          # CRLF everywhere, still


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
    """The read-only check the plan asks for, on the golden fixture's own 1 020-line file:
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


# ---- the placement plumbing (harness.install / make_client), on temp dirs -----------------

class StubServer:
    """Just enough Server for `session.make_client`: the mod list and the two placement maps
    the client is supposed to inherit."""

    def __init__(self, mods=("PZTestKit",), mod_sources=None, mod_skip=()):
        self.mods, self.port = list(mods), 27261
        self.mod_sources, self.mod_skip = dict(mod_sources or {}), tuple(mod_skip)


def _fake_mod(root, name, mod_id=None):
    """A folder shaped enough like a mod to be copied and read back."""
    p = os.path.join(root, name, "42.20")
    os.makedirs(p, exist_ok=True)
    _write(os.path.join(p, "mod.info"), "name=%s\nid=%s\n" % (name, mod_id or name), newline=None)
    return os.path.join(root, name)


def test_install_places_harness_mods_and_reports_the_rest_missing():
    """The pre-profile behaviour, unchanged: a harness id is copied from the repo, anything
    else is the workshop's problem, and what was not placed comes back."""
    with tempfile.TemporaryDirectory() as d:
        mods_dir = os.path.join(d, "mods")
        from pzt import harness
        missing = harness.install(mods_dir, ["PZTestKit", "NotAMod"], workshop=False)
        assert missing == ["NotAMod"]
        assert os.path.isdir(os.path.join(mods_dir, "PZTestKit"))
        assert sorted(os.listdir(mods_dir)) == ["PZTestKit"]


def test_install_skips_without_reporting_missing():
    """`copy = false`: named in Mods= on purpose, placed nowhere, and NOT in `missing` -- the
    run log says so once, in the `profile` mark's `skip=`."""
    with tempfile.TemporaryDirectory() as d:
        mods_dir = os.path.join(d, "mods")
        from pzt import harness
        missing = harness.install(mods_dir, ["PZTestKit", "Ghost"], workshop=False,
                                  skip=("Ghost",))
        assert missing == []
        assert os.listdir(mods_dir) == ["PZTestKit"]


def test_sources_win_over_the_harness_map():
    """A profile's `path =` on a harness id copies THAT folder -- otherwise a mod under test
    could never shadow a repo mod of the same name."""
    with tempfile.TemporaryDirectory() as d:
        src = _fake_mod(d, "elsewhere", mod_id="PZTestKit")
        mods_dir = os.path.join(d, "mods")
        from pzt import harness
        assert harness.install(mods_dir, ["PZTestKit"], workshop=False,
                               sources={"PZTestKit": src}) == []
        # placed under the ID, from the source folder: the marker file proves which one
        assert os.path.exists(os.path.join(mods_dir, "PZTestKit", "42.20", "mod.info"))
        assert not os.path.exists(os.path.join(mods_dir, "PZTestKit", "42", "media"))


def test_make_client_inherits_the_servers_placement_unless_told_otherwise():
    """`None` means 'the server's', not 'none', so the two sides cannot drift; an explicit `()`
    is still honoured."""
    from pzt import session
    with tempfile.TemporaryDirectory() as d:
        src = _fake_mod(d, "KeenSrc", mod_id="Keen")
        srv = StubServer(mods=["PZTestKit", "Keen", "Ghost"],
                         mod_sources={"Keen": src}, mod_skip=("Ghost",))
        c, restored = session.make_client(os.path.join(d, "run"), "admin", srv, workshop=False)
        assert restored is False
        assert c.mod_sources == {"Keen": src} and c.mod_skip == ("Ghost",)
        placed = sorted(os.listdir(os.path.join(c.cache, "mods")))
        assert "PZTestKit" in placed and "Keen" in placed and "Ghost" not in placed
        assert c.missing_mods == []                      # Ghost was skipped, not missed
        # default.txt still names the skipped id: both sides walk the same road (S3-A)
        with open(os.path.join(c.cache, "mods", "default.txt")) as fh:
            assert "mod = Ghost," in fh.read()
        c2, _ = session.make_client(os.path.join(d, "run2"), "admin", srv, workshop=False,
                                    mod_sources={}, mod_skip=())
        assert c2.mod_sources == {} and c2.mod_skip == ()
        assert c2.missing_mods == ["Keen", "Ghost"]      # nothing to copy them from now


# ---- pre-boot validation: everything that is wrong costs a second, not a boot -------------

def test_a_non_bool_copy_is_an_error_rather_than_a_placed_mod():
    """`copy = 0` would sail past `is False` and be COPIED -- the one misread that produces
    the wrong session instead of an error."""
    for bad in (0, "false", "no"):
        with pytest.raises(profile.ProfileError) as e:
            profile.resolve_mod({"id": "X", "copy": bad}, {})
        assert "copy must be a bool" in str(e.value)


def test_the_harness_cannot_be_copy_false():
    """No harness = no command bus = no ready marker: the run would hang waiting for a marker
    nothing will ever write."""
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve_mod({"id": "PZTestKit", "copy": False}, {})
    assert "cannot be copy = false" in str(e.value)


def test_path_and_workshop_id_together_are_an_error():
    """The branch order would take `path` and silently drop the workshop id, so the profile
    would record a provenance the run did not use."""
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve_mod({"path": "testing/PZTestKit/PZTestKit", "workshop_id": "1"}, {})
    assert "both path and workshop_id" in str(e.value)


def test_bad_scalar_types_are_profile_errors_not_tracebacks():
    for toml, needle in [('run = { hold = "soon" }\n', "[run] hold must be a whole number"),
                         ('server = { timeout = "later" }\n', "[server] timeout must be"),
                         ('client = { timeout = [1] }\n', "[client] timeout must be"),
                         ('client = { safemode = 1 }\n', "[client] safemode must be true or false"),
                         ('run = { hold = true }\n', "[run] hold must be a whole number")]:
        with workspace(toml + '[[mods]]\nid = "PZTestKit"\n'):
            with pytest.raises(profile.ProfileError) as e:
                profile.load("p")
        assert needle in str(e.value), toml


def test_a_float_hold_is_accepted_and_truncated():
    """`int()` still does its job where the value IS a number -- only the crash is removed."""
    with workspace('run = { hold = 2.9 }\n[[mods]]\nid = "PZTestKit"\n'):
        assert profile.load("p").hold == 2


def test_an_empty_users_list_is_rejected_rather_than_silently_meaning_the_fixtures():
    """It reads as 'server only' and is not: `pzt run` would fall back to the FIXTURE's client
    list and `pzt scenario` would raise IndexError on `users[0]`."""
    with workspace('client = { users = [] }\n[[mods]]\nid = "PZTestKit"\n'):
        with pytest.raises(profile.ProfileError) as e:
            profile.load("p")
    assert "users = [] is not a server-only run" in str(e.value)


def test_a_boolean_expect_is_rejected_and_a_number_is_coerced():
    """`expect` is matched inside the dumped JSON: a TOML `true` would stringify to "True" and
    could never match, and a bare non-string would raise a TypeError mid-run."""
    with workspace('verify = [ { cmd = "c", expect = true } ]\n[[mods]]\nid = "PZTestKit"\n'):
        with pytest.raises(profile.ProfileError) as e:
            profile.load("p")
    assert "expect must be a string" in str(e.value) and "true" in str(e.value)
    with workspace('verify = [ { cmd = "c", expect = 12 } ]\n[[mods]]\nid = "PZTestKit"\n'):
        assert profile.load("p").verify[0]["expect"] == "12"


def test_check_sandbox_is_a_no_op_when_the_fixture_blob_is_not_on_this_machine():
    """The caveat the doc carries: fixture caches are gitignored, so on a fresh clone a
    misspelt key is not caught here (the run cannot start either way)."""
    assert profile.check_sandbox("p", {"Nonsense": 1}, os.path.join("nowhere", "x.lua")) is None


# ---- the merge's edge cases --------------------------------------------------------------

def test_merge_keeps_a_trailing_comment_on_a_rewritten_line():
    with tempfile.TemporaryDirectory() as d:
        p = _write(os.path.join(d, "s.lua"),
                   SANDBOX.replace("    Zombies = 6,\r\n", "    Zombies = 6,   -- none\r\n"))
        server.merge_sandbox_vars(p, {"Zombies": 4})
        with open(p, encoding="utf-8", newline="") as fh:
            assert "    Zombies = 4,   -- none\r\n" in fh.read()


def test_merge_appends_before_the_column_zero_brace_not_a_nested_one():
    """`l.strip() == "}"` would put an appended option inside the last nested table."""
    text = ("SandboxVars = {\r\n    Map = {\r\n        A = 1,\r\n"
            "        }\r\n    Zombies = 6,\r\n}\r\n")
    with tempfile.TemporaryDirectory() as d:
        p = _write(os.path.join(d, "s.lua"), text)
        assert server.merge_sandbox_vars(p, {"DayLength": 1}) == ([], ["DayLength"])
        with open(p, encoding="utf-8", newline="") as fh:
            assert fh.read().endswith("    Zombies = 6,\r\n    DayLength = 1,\r\n}\r\n")


def test_merge_on_a_file_with_no_closing_brace_says_so_instead_of_crashing():
    with tempfile.TemporaryDirectory() as d:
        p = _write(os.path.join(d, "s.lua"), "SandboxVars = {\r\n    Zombies = 6,\r\n")
        with pytest.raises(SystemExit) as e:
            server.merge_sandbox_vars(p, {"DayLength": 1})
    assert "no closing '}' at column 0" in str(e.value) and "DayLength" in str(e.value)
