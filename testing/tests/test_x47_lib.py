"""Offline tests of testing/experiments/x47_lib.py (Plan 16 Task 12, runs x471 and x472): every grade with a failing case
and its unmeasured case; the pre-boot checks on the real repository, the real staged upload copy, a real copy of bob's
folder and the real fixture's options file merged as the seed merges it; the log readers on x223a's and x223b's committed
logs (the game's real line formats); and the bob watch against a fake client on a fake clock.

The fake bus answers the harness's real reply shapes (docs/reference/harness-commands.md): lua.global
{side, name, resolved, type, value} or {side, name, resolved, failedAt}; players a list of usernames ({} with nobody on).
The staged-copy and fixture tests skip where release/ or the fixture cache (both gitignored) are absent.
"""
import os
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x47_lib as L                   # noqa: E402
import xlib as X                      # noqa: E402

REPO = L.REPO
STAGED = os.path.join(REPO, L.STAGE_ROOT)
FIXTURE_SANDBOX = os.path.join(REPO, "testing", "fixtures", "two", "cache", "server", "Server", "pzt_SandboxVars.lua")
X223A = os.path.join(REPO, "testing", "artifacts", "x223a-20261007-085224")
X223B = os.path.join(REPO, "testing", "artifacts", "x223b-20261007-085832")
need_staged = pytest.mark.skipif(not os.path.isdir(STAGED), reason="release/ (gitignored) not staged on this machine")


def lg(value, resolved=True, side="server", name="x"):
    """A lua.global reply in the harness's shape."""
    if not resolved:
        return {"side": side, "name": name, "resolved": False, "failedAt": "NR"}
    return {"side": side, "name": name, "resolved": True, "type": "number", "value": value}


# ---------------------------------------------------------------- pre-boot on the repository
def test_preboot_x471_on_the_repository():
    c, ok = L.preboot("x471", "x471_options.py")
    assert all(v is True for k, v in c["profile_checks"].items()), c["profile_checks"]
    assert c["key"] and c["driver_file"] and c["driver_prefix"]
    if c["staged_from_is_mod_head"] and c["no_prior_artifact"]:
        assert ok


def test_preboot_refuses_a_wrong_driver_file():
    c, ok = L.preboot("x471", "x472_checksum.py")
    assert c["driver_file"] is False and ok is False


@pytest.mark.parametrize("name", ["x47-options", "x47-checksum"])
def test_real_profiles_pass_their_doc_checks(name):
    import tomllib
    with open(os.path.join(REPO, "testing", "profiles", name + ".toml"), encoding="utf-8") as fh:
        text = fh.read()
    c = L.profile_doc_checks(name, tomllib.loads(text), text)
    assert all(v is True for v in c.values()), c


def test_profile_doc_checks_fail_a_wrong_option_and_a_mod_path():
    import tomllib
    with open(os.path.join(REPO, "testing", "profiles", "x47-options.toml"), encoding="utf-8") as fh:
        text = fh.read()
    doc = tomllib.loads(text)
    doc["sandbox"]["NR"] = {"VisibilityMode": 2}
    assert L.profile_doc_checks("x47-options", doc, text)["nr_block"] is False
    doc = tomllib.loads(text)
    doc["mods"][1]["path"] = "mod/NutritionRevamp"
    assert L.profile_doc_checks("x47-options", doc, text)["mods_staged"] is False
    assert L.profile_doc_checks("x46-mod", doc, text) == {"known_profile": False}


@need_staged
def test_staged_gate_on_the_real_upload_copy():
    if not L.preboot("x471", "x471_options.py")[0]["staged_from_is_mod_head"]:
        pytest.skip("mod/ moved past STAGED_FROM: the drivers have run and the copy may be re-staged")
    m = L.staged_gate()
    assert m["ok"], m
    assert m["staged_version"] == "1.0.0"


# ---------------------------------------------------------------- bob's copy
@pytest.fixture
def bob_copy(tmp_path):
    if not os.path.isdir(STAGED):
        pytest.skip("release/ (gitignored) not staged on this machine")
    bob_root = tmp_path / "x472-bob" / "NutritionRevamp"
    facts = L.make_bob_copy(STAGED, str(bob_root))
    return str(bob_root / "Contents" / "mods" / "NutritionRevamp"), facts


def bob_file(bob_mod):
    return os.path.join(bob_mod, *L.CHANGED_REL.split("/"))


def test_bob_copy_of_the_real_staged_copy_is_one_byte_in_a_comment(bob_copy):
    bob_mod, facts = bob_copy
    c = L.bob_copy_check(os.path.join(REPO, L.STAGE_MOD), bob_mod)
    assert c["ok"], c
    assert c["line_no"] == 1 and c["bytes_differ"] == 1 and c["in_comment"]
    assert facts["sha256"] == c["bob_file"]["sha256"]
    assert L.grade_copy(c)[0] == "as_predicted"


def test_bob_copy_check_fails_two_bytes(bob_copy):
    bob_mod, _ = bob_copy
    p = bob_file(bob_mod)
    b = open(p, "rb").read().replace(b"its versiom", b"its versixm", 1)
    open(p, "wb").write(b)
    c = L.bob_copy_check(os.path.join(REPO, L.STAGE_MOD), bob_mod)
    assert c["bytes_differ"] == 2 and not c["ok"]
    assert L.grade_copy(c)[0] == "falsified"


def test_bob_copy_check_fails_a_byte_outside_a_comment(bob_copy):
    bob_mod, _ = bob_copy
    p = bob_file(bob_mod)
    b = open(p, "rb").read().replace(b"its versiom", b"its version", 1).replace(b'"1.0.0"', b'"1.0.1"', 1)
    open(p, "wb").write(b)
    c = L.bob_copy_check(os.path.join(REPO, L.STAGE_MOD), bob_mod)
    assert c["bytes_differ"] == 1 and c["in_comment"] is False and not c["ok"]


def test_bob_copy_check_fails_a_cr_only_change(bob_copy):
    bob_mod, _ = bob_copy
    p = bob_file(bob_mod)
    b = open(p, "rb").read().replace(b"its versiom", b"its version", 1)
    b = b.replace(b"\n", b"\r\n", 1)
    open(p, "wb").write(b)
    c = L.bob_copy_check(os.path.join(REPO, L.STAGE_MOD), bob_mod)
    assert c["ok"] is False


def test_bob_copy_check_fails_an_extra_file(bob_copy):
    bob_mod, _ = bob_copy
    open(os.path.join(bob_mod, "common", "media", "lua", "shared", "NR_Extra.lua"), "wb").write(b"-- x\n")
    c = L.bob_copy_check(os.path.join(REPO, L.STAGE_MOD), bob_mod)
    assert c["one_file"] is False and not c["ok"]


def test_make_bob_copy_refuses_a_multi_byte_edit_and_a_missing_text(tmp_path):
    with pytest.raises(ValueError):
        L.make_bob_copy(str(tmp_path), str(tmp_path / "b"), old=b"ab", new=b"cd")
    src = tmp_path / "s" / "Contents" / "mods" / "NutritionRevamp" / "common" / "media" / "lua" / "shared"
    src.mkdir(parents=True)
    (src / "NR_Core.lua").write_bytes(b"-- nothing here\n")
    with pytest.raises(ValueError):
        L.make_bob_copy(str(tmp_path / "s"), str(tmp_path / "b"))


def test_grade_copy_unmeasured_without_a_check():
    assert L.grade_copy(None)[0] == "unmeasured"


# ---------------------------------------------------------------- deployed copies
def test_grade_deployed():
    rows = {"server/mods/NutritionRevamp/common/media/lua/shared/NR_Core.lua": {"sha256": "S"},
            "clients/admin/mods/NutritionRevamp/common/media/lua/shared/NR_Core.lua": {"sha256": "S"},
            "clients/bob/mods/NutritionRevamp/common/media/lua/shared/NR_Core.lua": {"sha256": "B"}}
    assert L.grade_deployed(rows, "S", "B")[0] == "as_predicted"
    bad = dict(rows)
    bad["clients/bob/mods/NutritionRevamp/common/media/lua/shared/NR_Core.lua"] = {"sha256": "S"}
    assert L.grade_deployed(bad, "S", "B")[0] == "falsified"
    del bad["clients/admin/mods/NutritionRevamp/common/media/lua/shared/NR_Core.lua"]
    assert L.grade_deployed(bad, "S", "B")[0] == "unmeasured"


def test_deployed_copies_finds_each_side(tmp_path):
    for side in ("server", os.path.join("clients", "admin"), os.path.join("clients", "bob")):
        p = tmp_path / side / "mods" / "NutritionRevamp" / "common" / "media" / "lua" / "shared"
        p.mkdir(parents=True)
        (p / "NR_Core.lua").write_bytes(b"-- " + side.encode() + b"\n")
    rows = L.deployed_copies(str(tmp_path))
    assert sorted(k.split("/")[0] + "/" + k.split("/")[1] for k in rows) == ["clients/admin", "clients/bob",
                                                                              "server/mods"]


# ---------------------------------------------------------------- the options file
@pytest.mark.skipif(not os.path.isfile(FIXTURE_SANDBOX), reason="fixture two's cache (gitignored) absent")
def test_the_seed_merge_of_the_real_fixture_file_holds_the_option(tmp_path):
    from pzt.server import merge_sandbox_vars
    p = tmp_path / "pzt_SandboxVars.lua"
    shutil.copyfile(FIXTURE_SANDBOX, p)
    assert L.sandbox_nr_block(p.read_text(encoding="utf-8")) is None          # the fixture carries no NR block
    assert L.grade_ini(None)[0] == "unmeasured"
    merge_sandbox_vars(str(p), {"Nutrition": False, "DayLength": 1, "NR": {"VisibilityMode": 3}})
    block = L.sandbox_nr_block(p.read_text(encoding="utf-8"))
    assert block == {"VisibilityMode": "3"}
    assert L.grade_ini(block)[0] == "as_predicted"


def test_grade_ini_falsified_on_the_default():
    assert L.grade_ini({"VisibilityMode": "2"})[0] == "falsified"
    assert L.grade_ini({"Mode": "1"})[0] == "falsified"


def test_sandbox_nr_block_parses_the_server_shape():
    text = "SandboxVars = {\n    VERSION = 6,\n    NR = {\n        Mode = 1,\n        VisibilityMode = 3,\n    },\n}\n"
    assert L.sandbox_nr_block(text) == {"Mode": "1", "VisibilityMode": "3"}
    assert L.sandbox_nr_block(None) is None


# ---------------------------------------------------------------- the option reads
def test_grade_option():
    assert L.grade_option([lg(3), lg(3.0)])[0] == "as_predicted"
    assert L.grade_option([lg(3), lg(2)])[0] == "falsified"
    assert L.grade_option([lg(3), lg(None, resolved=False)])[0] == "unmeasured"
    assert L.grade_option([lg(3), {"error": "TimeoutError: no reply"}])[0] == "unmeasured"
    assert L.grade_option([])[0] == "unmeasured"
    assert L.grade_option([lg(2), lg(None, resolved=False)])[0] == "falsified"


def fake_ask(values):
    """A bus whose lua.global answers values[(side, name)] in the harness's shape; absent names fail at NR."""
    calls = []

    def ask(node, cmd, args, timeout=20):
        calls.append((node, cmd, args))
        assert cmd == "lua.global"
        v = values.get((node, args), "absent")
        if v == "absent":
            return lg(None, resolved=False, side=node, name=args)
        return lg(v, side=node, name=args)
    ask.calls = calls
    return ask


def all_values(opt=3, mod=3, version="1.0.0"):
    v = {}
    for side in (L.SRV, L.ADMIN, L.BOB):
        v[(side, L.SERVER_OPT_G)] = opt
        v[(side, L.VERSION_G)] = version
    v[(L.SRV, L.SERVER_MOD_G)] = mod
    v[(L.ADMIN, L.CLIENT_MOD_G)] = mod
    v[(L.BOB, L.CLIENT_MOD_G)] = mod
    return v


def take(values, nodes=None):
    rs = {}
    nodes = nodes or {L.SRV: L.SRV, L.ADMIN: L.ADMIN, L.BOB: L.BOB}
    for tag in ("after_ready", "end"):
        L.take_reads(fake_ask(values), nodes, tag, rs)
    return rs


def test_take_reads_and_the_option_grades_as_predicted():
    rs = take(all_values())
    for side in (L.SRV, L.ADMIN, L.BOB):
        assert L.grade_option(L.collect(rs, side, L.SERVER_OPT_G))[0] == "as_predicted"
        assert len(L.collect(rs, side, L.SERVER_OPT_G)) == 2
    assert L.grade_mod_read(rs)[0] == "as_predicted"


def test_the_option_grades_falsified_on_the_default():
    rs = take(all_values(opt=2, mod=2))
    assert L.grade_option(L.collect(rs, L.BOB, L.SERVER_OPT_G))[0] == "falsified"
    assert L.grade_mod_read(rs)[0] == "falsified"


def test_mod_read_unmeasured_when_a_side_never_answered():
    v = all_values()
    del v[(L.BOB, L.CLIENT_MOD_G)]
    rs = take(v)
    assert L.grade_mod_read(rs)[0] == "unmeasured"
    rs = take(all_values(), nodes={L.SRV: L.SRV, L.ADMIN: L.ADMIN, L.BOB: None})
    assert L.grade_option(L.collect(rs, L.BOB, L.SERVER_OPT_G))[0] == "unmeasured"
    assert L.grade_mod_read(rs)[0] == "unmeasured"


# ---------------------------------------------------------------- the logs (x223a's and x223b's real files)
def read(p):
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def one(folder, suffix, prefix):
    hits = [f for f in os.listdir(folder) if f.startswith(prefix) and f.endswith(suffix)]
    assert len(hits) == 1
    return os.path.join(folder, hits[0])


def test_log_readers_on_x223a_the_kick():
    u = L.user_log_facts(read(one(X223A, "_user.txt", "server-")))
    assert len(u["anticheat_bob"]) == 1 and "Lua incorrect checksum" in u["anticheat_bob"][0]
    assert u["fully_connected"] == ["admin"]
    c = L.conn_facts(read(one(X223A, "_connections.txt", "bob-")))
    assert len(c["force_checksum"]) == 1 and "nr_core.lua" in c["force_checksum"][0]


def test_log_readers_on_x223b_the_join():
    u = L.user_log_facts(read(one(X223B, "_user.txt", "server-")))
    assert u["anticheat_any"] == [] and "bob" in u["fully_connected"]
    c = L.conn_facts(read(one(X223B, "_connections.txt", "bob-")))
    assert c["force_checksum"] == []
    assert L.user_log_facts(None)["read"] is False


def test_kicked_bob_pattern_matches_the_x223a_stdout_line():
    line = ("WARN : Multiplayer    f:0 > ChecksumPacket.parseServer > user bob will be kicked in 60000ms because "
            "Lua/script checksums do not match")
    assert L.KICKED_BOB_RX.search(line) and L.MISMATCH_RX.search(line)


def test_mismatch_pattern_on_x223a_real_lines():
    import json
    with open(os.path.join(X223A, "luasum.json"), encoding="utf-8") as fh:
        hits = [h["text"] for h in json.load(fh)["logs"]["server_mismatch"]["hits"]]
    boot = [h for h in hits if "luaChecksum:" in h]
    kick = [h for h in hits if "luaChecksum:" not in h]
    assert len(boot) == 1 and len(kick) == 2
    assert not L.MISMATCH_RX.search(boot[0])
    assert all(L.MISMATCH_RX.search(h) for h in kick)
    assert L.KICKED_BOB_RX.search(kick[0])
    for line in ("client: DoLuaChecksum start", "client: DoLuaChecksum end"):
        assert not L.MISMATCH_RX.search(line)


def test_find_logs_on_a_run_layout(tmp_path):
    (tmp_path / "server" / "Logs").mkdir(parents=True)
    (tmp_path / "clients" / "bob" / "Logs").mkdir(parents=True)
    for n in ("2026-10-19_10-00_user.txt", "2026-10-19_10-00_connections.txt"):
        (tmp_path / "server" / "Logs" / n).write_text("x")
    (tmp_path / "clients" / "bob" / "Logs" / "2026-10-19_10-01_connections.txt").write_text("x")
    f = L.find_logs(str(tmp_path))
    assert f["server_user"].endswith("_user.txt") and f["bob_connections"].endswith("10-01_connections.txt")
    assert L.find_logs(str(tmp_path / "none")) == {"server_user": None, "server_connections": None,
                                                   "bob_connections": None}


# ---------------------------------------------------------------- the session grades
def join_ok():
    return {"bob_started": True, "admin_ready": True, "bob_ready": True, "staged_version": "1.0.0",
            "versions": {L.SRV: "1.0.0", L.ADMIN: "1.0.0", L.BOB: "1.0.0"}, "players_end": ["bob", "admin"],
            "fully_connected": ["admin", "bob"], "anticheat_any": [], "server_mismatch": [], "user_log_read": True}


def test_grade_join_as_predicted_and_each_defect():
    assert L.grade_join(join_ok())[0] == "as_predicted"
    defects = [("bob_ready", False), ("admin_ready", False), ("players_end", ["admin"]),
               ("fully_connected", ["admin"]), ("anticheat_any", ["Anti-cheat=..."]),
               ("server_mismatch", ["user bob will be kicked"]), ("user_log_read", False),
               ("versions", {L.SRV: "1.0.0", L.ADMIN: "1.0.0", L.BOB: None}), ("staged_version", None)]
    for k, v in defects:
        o = join_ok()
        o[k] = v
        assert L.grade_join(o)[0] == "falsified", k
    o = join_ok()
    o["bob_started"] = False
    assert L.grade_join(o)[0] == "unmeasured"


def kick(**kw):
    o = {"bob_started": True, "bob_ready": False, "bob_answered_end": False, "anticheat_bob": ["Anti-cheat=..."],
         "kicked_bob": [], "force_checksum": [], "server_mismatch": []}
    o.update(kw)
    return o


def test_grade_kick():
    assert L.grade_kick(kick())[0] == "as_predicted"
    assert L.grade_kick(kick(anticheat_bob=[], force_checksum=["force"]))[0] == "as_predicted"
    assert L.grade_kick(kick(bob_ready=True, bob_answered_end=True, anticheat_bob=[]))[0] == "falsified"
    assert L.grade_kick(kick(anticheat_bob=[]))[0] == "unmeasured"
    assert L.grade_kick(kick(bob_ready=True))[0] == "unmeasured"
    assert L.grade_kick(kick(bob_started=False))[0] == "unmeasured"


def test_grade_admin_stays():
    assert L.grade_admin_stays(["admin"], 1)[0] == "as_predicted"
    assert L.grade_admin_stays(["admin", "bob"], 1)[0] == "falsified"
    assert L.grade_admin_stays({}, 1)[0] == "unmeasured"
    assert L.grade_admin_stays(["admin"], None)[0] == "unmeasured"


def test_grade_z_reused_from_x45g():
    import x45g_lib as G
    assert G.grade_z({"logs": {"mod_error": []}, "admin_lua_error": False})[0] == "as_predicted"
    assert G.grade_z({"logs": {"mod_error": ["NR_Server_X.lua:1 failed:"]}, "admin_lua_error": False})[0] == "falsified"


def test_kick_obs_and_join_obs_read_the_artifact_keys():
    out = {"bob": {"ready_wall": None}, "logs": {"user": {"anticheat_bob": ["a"], "fully_connected": ["admin"],
                                                          "anticheat_any": ["a"], "read": True},
                                                 "bob_connections": {"force_checksum": ["f"]},
                                                 "server_kicked_bob": ["k"], "server_mismatch": ["k"]},
           "bob_version_at_end": None, "players_end": ["admin"], "admin_ready_wall": 50.0,
           "manifest_gate": {"staged_version": "1.0.0"}}
    o = L.kick_obs(out, True)
    assert o["anticheat_bob"] == ["a"] and o["force_checksum"] == ["f"] and o["kicked_bob"] == ["k"]
    assert o["bob_ready"] is False and L.grade_kick(o)[0] == "as_predicted"
    j = L.join_obs(out, {}, True)
    assert j["bob_ready"] is False and L.grade_join(j)[0] == "falsified"


# ---------------------------------------------------------------- the bob watch (fake client, fake clock)
class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


class FakeBob:
    def __init__(self, clock, ready_at=None, in_game_at=None):
        self.clock, self.ready_at, self.in_game_at = clock, ready_at, in_game_at
        self.alive, self.events, self.clicks, self.t0 = True, [], 0, None
        self._seen = {}

    def start(self):
        self.t0 = self.clock()

    @property
    def seen(self):
        el = self.clock() - self.t0
        if self.in_game_at is not None and el >= self.in_game_at:
            self._seen.setdefault("in_game", self.in_game_at)
        if self.ready_at is not None and el >= self.ready_at:
            self._seen.setdefault("ready", self.ready_at)
        return self._seen

    def click_to_start(self):
        self.clicks += 1
        return 1


def xs_for(clock):
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}}
    return X.Xs(out, node=lambda s: s, clock=clock, sleep=clock.sleep)


def test_watch_bob_ready_holds_past_ready_once():
    clock = Clock()
    xs = xs_for(clock)
    bob = FakeBob(clock, ready_at=40.0, in_game_at=30.0)
    calls = []
    ready = L.watch_bob(xs, bob, lambda: calls.append(clock()) or 10.0, 180.0, clock=clock, sleep=clock.sleep)
    assert ready is True and len(calls) == 1
    assert xs.out["bob"]["ready_wall"] is not None and bob.clicks >= 1
    assert 49.0 <= xs.out["bob"]["window_end_wall"] <= 51.0


def test_watch_bob_never_ready_stops_at_the_cap():
    clock = Clock()
    xs = xs_for(clock)
    bob = FakeBob(clock)
    ready = L.watch_bob(xs, bob, lambda: pytest.fail("on_ready on a never-ready bob"), 60.0, clock=clock,
                        sleep=clock.sleep)
    assert ready is False and "ready_wall" not in xs.out["bob"]
    assert 59.0 <= xs.out["bob"]["window_end_wall"] <= 61.0
