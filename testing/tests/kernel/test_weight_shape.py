"""NR_Server_Weight, driven through table-of-functions Java stand-ins.

The file is a server/ file the kernel host does not load, so it is loaded on top of the session host
the way test_strength_shape.py loads NR_Server_Strength.lua. NR.call indexes obj[name] and calls it with
obj first, so a Lua table of function fields stands in for a Java object. The body is built with the
real K.body.new and its masses set by hand; the Nutrition object records every setter call; the kernel
math is the real kernel. A stub proves the wiring, the order and the guards, not the engine's real
setters, which the live acceptance runs read.
"""
import os

import lupa.lua51 as lua51
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SERVER = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server")
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
WEIGHT = os.path.join(SERVER, "NR_Server_Weight.lua")
CORE = os.path.join(SHARED, "NR_Core.lua")
TOL = 1e-9
BAND_TRAITS = ("OBESE", "OVERWEIGHT", "UNDERWEIGHT", "VERY_UNDERWEIGHT", "EMACIATED")
MACRO_SETTERS = ("setCalories", "setProteins", "setCarbohydrates", "setLipids")

# The Java globals the adapter names, stubbed; the previous values are returned so the teardown puts
# them back and nothing leaks into a later module.
SETUP = r"""
function(age)
    local names = { "getGameTime", "CharacterTrait", "sendSyncPlayerFields" }
    local saved = { age = NR_TEST_AGE, tod = NR_TEST_TOD, names = names, vals = {} }
    for i = 1, #names do saved.vals[i] = _G[names[i]] end
    NR_TEST_AGE = age
    NR_TEST_TOD = nil
    NR_TEST_PUSHES = 0
    getGameTime = function()
        return {
            getWorldAgeHours = function(self) return NR_TEST_AGE end,
            getTimeOfDay = function(self)
                if NR_TEST_TOD ~= nil then return NR_TEST_TOD end
                return math.fmod(NR_TEST_AGE, 24)
            end,
        }
    end
    CharacterTrait = { OBESE = "OBESE", OVERWEIGHT = "OVERWEIGHT", UNDERWEIGHT = "UNDERWEIGHT",
                       VERY_UNDERWEIGHT = "VERY_UNDERWEIGHT", EMACIATED = "EMACIATED",
                       STRONG = "STRONG" }
    sendSyncPlayerFields = function(p, n)
        if n == 2 then NR_TEST_PUSHES = NR_TEST_PUSHES + 1 end
    end
    return saved
end
"""

TEARDOWN = r"""
function(saved)
    NR_TEST_AGE, NR_TEST_TOD = saved.age, saved.tod
    for i = 1, #saved.names do _G[saved.names[i]] = saved.vals[i] end
end
"""

# A player stand-in: getNutrition answers one Nutrition stand-in whose every setter records
# { name, value } into cfg.calls; the trait collection reads cfg.traits.
PLAYER = r"""
function(cfg)
    local p = { cfg = cfg }
    cfg.calls = {}
    local function rec(name, v)
        cfg.calls[#cfg.calls + 1] = { name, v }
    end
    local nut = {}
    local setters = { "setWeight", "setIncWeight", "setIncWeightLot", "setDecWeight", "setCalories",
                      "setProteins", "setCarbohydrates", "setLipids" }
    for i = 1, #setters do
        local name = setters[i]
        nut[name] = function(self, v)
            if cfg.raising == name then error("stub: " .. name .. " raised") end
            rec(name, v)
        end
    end
    nut.applyTraitFromWeight = function(self) rec("applyTraitFromWeight", true) end
    p.getNutrition = function(self) return nut end
    p.getCharacterTraits = function(self)
        return { get = function(s, t) return self.cfg.traits[t] == true end }
    end
    return p
end
"""

MINUTE = r"""
function(player, record, age)
    NR_TEST_AGE = age
    NutritionRevamp.server.weight.minute("admin", player, record)
    return record
end
"""


def _load(host, path, name):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, name)()


@pytest.fixture(scope="module")
def wgt_host(host):
    _load(host, WEIGHT, "@NR_Server_Weight.lua")
    server = host.G.NutritionRevamp.server
    saved_opts = server.options
    server.options = host.table({"legacyMirror": True})   # NR_Server_Options is not in the kernel host
    saved = host.rt.eval(SETUP)(100.0)
    try:
        yield host
    finally:
        host.rt.eval(TEARDOWN)(saved)
        server.options = saved_opts


@pytest.fixture(autouse=True)
def _reset(wgt_host):
    h = wgt_host
    h.G.NR_TEST_TOD = None
    h.G.NutritionRevamp.server.options.legacyMirror = True
    yield


def WGT(h):
    return h.G.NutritionRevamp.server.weight


def stats(h):
    return dict(WGT(h).stats.items())


def player(h, traits=None):
    cfg = h.rt.table()
    cfg.traits = h.table({t: True for t in (traits or [])})
    return h.rt.eval(PLAYER)(cfg)


def record_for(h, fm=15.0, lm=65.0, band=None):
    """A body built at 80 kg, then its masses set to fm + lm exactly."""
    record = h.rt.table()
    body = h.K.body["new"](80, 1, h.table({}), 5, 1.0, 1.0, 99.0)
    body.fm = fm
    body.lm = lm
    for i in range(1, 8):
        body.mass7[i] = fm + lm
    if band is not None:
        body.band = band
    record.body = body
    return record


def minute(h, p, record, age=100.0):
    return h.rt.eval(MINUTE)(p, record, age)


def calls(p, name=None):
    out = [(c[1], c[2]) for c in p.cfg.calls.values()]
    if name is None:
        return out
    return [v for n, v in out if n == name]


def pushes(h):
    return h.G.NR_TEST_PUSHES


# --- the weight write and the flags (#2643, #2644) -------------------------------------------------

def test_a_body_at_80_writes_the_weight_and_three_false_flags(wgt_host):
    h = wgt_host
    p = player(h)
    s0, n0 = stats(h), pushes(h)
    minute(h, p, record_for(h))
    assert calls(p, "setWeight") == [80.0]
    assert calls(p, "setIncWeight") == [False]
    assert calls(p, "setIncWeightLot") == [False]
    assert calls(p, "setDecWeight") == [False]
    assert calls(p, "applyTraitFromWeight") == []
    assert pushes(h) == n0
    s = stats(h)
    assert s["weightWrites"] == s0["weightWrites"] + 1
    assert s["flagWrites"] == s0["flagWrites"] + 1
    assert s["minutes"] == s0["minutes"] + 1


def test_weight_and_flags_are_written_every_minute(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h)
    minute(h, p, record, 100.0)
    minute(h, p, record, 100.0 + 1 / 60)
    assert calls(p, "setWeight") == [80.0, 80.0]
    assert calls(p, "setIncWeight") == [False, False]


def test_oldest_mass_79_3_raises_inc(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h)
    record.body.mass7[1] = 79.3                         # (80 - 79.3) / 7 = 0.1 kg/d
    minute(h, p, record)
    assert calls(p, "setIncWeight") == [True]
    assert calls(p, "setDecWeight") == [False]


@pytest.mark.parametrize("oldest, inc, lot, dec", [
    (79.5, True, False, False),                         # +0.071 kg/d
    (79.0, True, True, False),                          # +0.143 kg/d
    (81.0, False, False, True),                         # -0.143 kg/d
    (80.1, False, False, False),                        # -0.014 kg/d
])
def test_direction_flags_off_the_trend(wgt_host, oldest, inc, lot, dec):
    h = wgt_host
    p = player(h)
    record = record_for(h)
    record.body.mass7[1] = oldest
    minute(h, p, record)
    assert calls(p, "setIncWeight") == [inc]
    assert calls(p, "setIncWeightLot") == [lot]
    assert calls(p, "setDecWeight") == [dec]


def test_weight_is_written_before_the_band_refresh(wgt_host):
    h = wgt_host
    p = player(h)
    minute(h, p, record_for(h, fm=20.0, lm=65.0, band="normal"))
    names = [n for n, _ in calls(p)]
    assert names.index("setWeight") < names.index("applyTraitFromWeight")


# --- the band change, the push and the repair (#2722, #0534, #2099, #2740) -------------------------

def test_crossing_85_refreshes_the_band_once_and_pushes_once(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h, fm=20.0, lm=65.0, band="normal")
    s0, n0 = stats(h), pushes(h)
    minute(h, p, record)
    assert calls(p, "setWeight") == [85.0]
    assert calls(p, "applyTraitFromWeight") == [True]
    assert pushes(h) == n0 + 1
    assert record.body.band == "overweight"
    s = stats(h)
    assert s["bandChanges"] == s0["bandChanges"] + 1
    assert s["pushes"] == s0["pushes"] + 1
    assert s["bandRepairs"] == s0["bandRepairs"]


def test_same_band_with_its_trait_present_makes_no_call(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h, fm=20.0, lm=65.0, band="normal")
    minute(h, p, record)
    p.cfg.traits.OVERWEIGHT = True                      # what applyTraitFromWeight put on
    n0, s0 = pushes(h), stats(h)
    minute(h, p, record, 100.0 + 1 / 60)
    assert calls(p, "applyTraitFromWeight") == [True]   # the first minute's only
    assert pushes(h) == n0
    assert stats(h)["bandRepairs"] == s0["bandRepairs"]


def test_same_band_with_its_trait_absent_is_repaired_and_pushed(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h, fm=20.0, lm=65.0, band="overweight")
    s0, n0 = stats(h), pushes(h)
    minute(h, p, record)
    assert calls(p, "applyTraitFromWeight") == [True]
    assert pushes(h) == n0 + 1
    s = stats(h)
    assert s["bandRepairs"] == s0["bandRepairs"] + 1
    assert s["bandChanges"] == s0["bandChanges"]
    assert record.body.band == "overweight"


@pytest.mark.parametrize("fm, lm, band, trait", [
    (40.0, 65.0, "obese", "OBESE"),
    (5.0, 65.0, "underweight", "UNDERWEIGHT"),
    (5.0, 55.0, "veryUnderweight", "VERY_UNDERWEIGHT"),
    (5.0, 40.0, "emaciated", "EMACIATED"),
])
def test_each_band_reads_its_own_trait(wgt_host, fm, lm, band, trait):
    h = wgt_host
    p = player(h, traits=[trait])
    minute(h, p, record_for(h, fm=fm, lm=lm, band=band))
    assert calls(p, "applyTraitFromWeight") == []
    p2 = player(h, traits=["OVERWEIGHT"])               # a wrong band trait only
    minute(h, p2, record_for(h, fm=fm, lm=lm, band=band))
    assert calls(p2, "applyTraitFromWeight") == [True]


def test_normal_band_with_a_band_trait_present_is_repaired(wgt_host):
    h = wgt_host
    p = player(h, traits=["OBESE"])
    n0 = pushes(h)
    minute(h, p, record_for(h))
    assert calls(p, "applyTraitFromWeight") == [True]
    assert pushes(h) == n0 + 1


def test_normal_band_ignores_a_non_band_trait(wgt_host):
    h = wgt_host
    p = player(h, traits=["STRONG"])
    minute(h, p, record_for(h))
    assert calls(p, "applyTraitFromWeight") == []


def test_missing_push_global_is_counted(wgt_host):
    h = wgt_host
    saved = h.G.sendSyncPlayerFields
    h.G.sendSyncPlayerFields = None
    try:
        p = player(h)
        s0 = stats(h)
        minute(h, p, record_for(h, fm=20.0, lm=65.0, band="normal"))
    finally:
        h.G.sendSyncPlayerFields = saved
    assert calls(p, "applyTraitFromWeight") == [True]
    s = stats(h)
    assert s["pushMissing"] == s0["pushMissing"] + 1
    assert s["pushes"] == s0["pushes"]


def test_no_trait_registry_skips_the_repair(wgt_host):
    h = wgt_host
    saved = h.G.CharacterTrait
    h.G.CharacterTrait = None
    try:
        p = player(h, traits=["OBESE"])
        s0 = stats(h)
        minute(h, p, record_for(h))
    finally:
        h.G.CharacterTrait = saved
    assert calls(p, "applyTraitFromWeight") == []
    assert calls(p, "setWeight") == [80.0]
    assert stats(h)["failures"] == s0["failures"]


# --- the legacy macro mirror (ruling 13) -----------------------------------------------------------

def test_mirror_on_writes_the_four_mapped_stores(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h)
    body = record.body
    body.lastCloseAgeH = 100.0 - 12.0                   # half of yesterday still in the window
    h.G.NR_TEST_TOD = 0.0                               # the clock hour never enters the blend
    body.ebDay = -250.0
    body.eb7[7] = -500.0                                # eb24h = -250 + -500 * 0.5 = -500
    body.pDay = 48.0
    body.p7[7] = 96.0                                   # (48 + 48) / 80 = 1.2 g/kg/d
    body.carbDay = 100.0
    body.carb7[7] = 400.0                               # 300 g -> 0
    body.lipDay = 50.0
    body.lip7[7] = 100.0                                # 100 g -> 30
    s0 = stats(h)
    minute(h, p, record)
    assert calls(p, "setCalories") == [-500.0]
    assert len(calls(p, "setProteins")) == 1
    assert abs(calls(p, "setProteins")[0] - 75.0) < TOL
    assert calls(p, "setCarbohydrates") == [0.0]
    assert calls(p, "setLipids") == [30.0]
    last = list(body.mirrorLast.values())
    assert len(last) == 4
    assert last[0] == -500.0 and abs(last[1] - 75.0) < TOL and last[2] == 0.0 and last[3] == 30.0
    assert stats(h)["mirrorWrites"] == s0["mirrorWrites"] + 1


def test_mirror_reads_today_only_at_midnight_and_clamps(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h)
    body = record.body
    body.lastCloseAgeH = 100.0 - 24.0                   # yesterday weighs 0
    body.ebDay = 5000.0
    body.eb7[7] = -9000.0
    body.pDay = 0.0
    body.p7[7] = 500.0
    minute(h, p, record)
    assert calls(p, "setCalories") == [3700.0]          # the store's ceiling (#0022)
    assert calls(p, "setProteins") == [-400.0]          # P = 0 g/kg/d


def test_mirror_is_written_every_minute(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h)
    minute(h, p, record, 100.0)
    minute(h, p, record, 100.0 + 1 / 60)
    for name in MACRO_SETTERS:
        assert len(calls(p, name)) == 2, name


def test_mirror_off_writes_no_macro_store(wgt_host):
    h = wgt_host
    h.G.NutritionRevamp.server.options.legacyMirror = False
    p = player(h)
    s0 = stats(h)
    minute(h, p, record_for(h))
    for name in MACRO_SETTERS:
        assert calls(p, name) == [], name
    assert calls(p, "setWeight") == [80.0]              # the weight arm is not the mirror's
    assert stats(h)["mirrorWrites"] == s0["mirrorWrites"]


# --- guards ----------------------------------------------------------------------------------------

def test_no_body_is_a_no_op(wgt_host):
    h = wgt_host
    p = player(h)
    record = h.rt.table()
    s0 = stats(h)
    minute(h, p, record)
    assert calls(p) == []
    assert stats(h)["failures"] == s0["failures"]


def test_nil_record_is_a_no_op(wgt_host):
    h = wgt_host
    p = player(h)
    s0 = stats(h)
    WGT(h).minute("admin", p, None)
    assert calls(p) == []
    assert stats(h)["minutes"] == s0["minutes"]


def test_a_non_finite_mass_writes_nothing_and_counts_a_failure(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h)
    record.body.fm = float("nan")
    s0 = stats(h)
    minute(h, p, record)
    assert calls(p) == []
    assert stats(h)["failures"] == s0["failures"] + 1
    assert "non-finite" in WGT(h).lastError


def test_no_nutrition_object_writes_nothing(wgt_host):
    h = wgt_host
    p = player(h)
    p.getNutrition = None
    s0 = stats(h)
    minute(h, p, record_for(h))
    assert stats(h)["badReads"] == s0["badReads"] + 1
    assert stats(h)["weightWrites"] == s0["weightWrites"]


def test_a_raising_setter_never_raises_into_the_walk(wgt_host):
    h = wgt_host
    p = player(h)
    p.cfg.raising = "setWeight"
    s0 = stats(h)
    minute(h, p, record_for(h))
    assert stats(h)["failures"] == s0["failures"] + 1
    assert "setWeight raised" in WGT(h).lastError


def test_the_rings_are_not_rebuilt_here(wgt_host):
    # NR_Server_Metabolism owns the ring rebuild (it runs first in the minute); a ring missing here is
    # a failure counted under the pcall, after the weight write
    h = wgt_host
    p = player(h)
    record = record_for(h)
    record.body.p7 = None
    s0 = stats(h)
    minute(h, p, record)
    assert record.body.p7 is None
    assert calls(p, "setWeight") == [80.0]
    assert stats(h)["failures"] == s0["failures"] + 1
    with open(WEIGHT, encoding="utf-8") as fh:
        assert "RINGS" not in fh.read()


def test_mirror_blend_on_hours_since_close(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h)
    body = record.body
    body.lastCloseAgeH = 100.0 - 6.0                    # three quarters of yesterday in the window
    body.carbDay = 100.0
    body.carb7[7] = 400.0
    minute(h, p, record)
    assert calls(p, "setCarbohydrates") == [100.0]      # 100 + 400 x 0.75 - 300
    body.lastCloseAgeH = 100.0 + 3.0                    # a close ahead of the age reads the full day
    minute(h, p, record)
    assert calls(p, "setCarbohydrates")[1] == 200.0


def test_absent_apply_trait_stamps_no_band_and_pushes_nothing(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h, fm=25.0, lm=65.0)            # 90 kg: overweight, the body says normal
    band0 = record.body.band
    p.getNutrition(p).applyTraitFromWeight = None
    s0 = stats(h)
    n0 = pushes(h)
    minute(h, p, record)
    assert record.body.band == band0                    # not stamped: the next minute retries
    assert stats(h)["bandChanges"] == s0["bandChanges"]
    assert pushes(h) == n0


def test_absent_apply_trait_counts_no_repair(wgt_host):
    h = wgt_host
    p = player(h, traits=["OBESE"])                     # 80 kg normal with a band trait present
    p.getNutrition(p).applyTraitFromWeight = None
    s0 = stats(h)
    n0 = pushes(h)
    minute(h, p, record_for(h))
    assert stats(h)["bandRepairs"] == s0["bandRepairs"]
    assert pushes(h) == n0


def test_flag_writes_count_only_on_success(wgt_host):
    h = wgt_host
    p = player(h)
    p.getNutrition(p).setDecWeight = None
    s0 = stats(h)
    minute(h, p, record_for(h))
    assert stats(h)["flagWrites"] == s0["flagWrites"]
    assert calls(p, "setIncWeight") == [False]


def test_limitations(wgt_host):
    lim = list(WGT(wgt_host).limitations.values())
    assert "the mirror is a plain overwrite; its four written values are the reconciliation's baseline (NR_Server_Reconcile)" in lim
    assert "the weight-direction thresholds are a game choice" in lim


def test_never_writes_the_strength_or_trait_set_directly():
    with open(WEIGHT, encoding="utf-8") as fh:
        src = fh.read()
    for name in ("setPerkLevelDebug", "LevelPerk", "LoseLevel", "addXp", "AddXP", "setMaxWeightDelta",
                 '"add"', '"remove"'):
        assert name not in src, name


# --- the options read ------------------------------------------------------------------------------

READ = r"""
function(v)
    local saved = SandboxVars
    if v == "absent" then
        SandboxVars = { NR = {} }
    elseif v == "string" then
        SandboxVars = { NR = { LegacyMirror = "false" } }
    else
        SandboxVars = { NR = { LegacyMirror = v } }
    end
    local O = NutritionRevamp.server.readOptions("test")
    local out = O.legacyMirror
    SandboxVars = saved
    NutritionRevamp.server.readOptions("test")
    return out
end
"""


@pytest.fixture(scope="module")
def opt_host(host):
    server = host.G.NutritionRevamp.server
    saved = server.options
    _load(host, os.path.join(SERVER, "NR_Server_Options.lua"), "@NR_Server_Options.lua")
    try:
        yield host
    finally:
        server.options = saved


@pytest.mark.parametrize("v, want", [(True, True), (False, False), ("absent", True), ("string", True),
                                     (1, True)])
def test_legacy_mirror_option_read(opt_host, v, want):
    h = opt_host
    assert h.rt.eval(READ)(v) is want
    assert h.G.NutritionRevamp.server.options.mode == 1


# --- the wiring order -------------------------------------------------------------------------------

def test_weight_runs_last_in_the_players_list():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    with open(CORE, encoding="utf-8") as fh:
        load(fh.read(), "@NR_Core.lua")()
    rt.execute(r"""
        NR_STARTED = {}
        Events = { OnServerStarted = { Add = function(fn) NR_STARTED[#NR_STARTED + 1] = fn end } }
        isServer = function() return true end
        NutritionRevamp.server.players = { onMinute = {} }
    """)
    names = sorted(["NR_Server_Weight.lua", "NR_Server_Training.lua", "NR_Server_Strength.lua",
                    "NR_Server_Metabolism.lua", "NR_Server_Kinetics.lua", "NR_Server_Minute.lua"])
    assert names == ["NR_Server_Kinetics.lua", "NR_Server_Metabolism.lua", "NR_Server_Minute.lua",
                     "NR_Server_Strength.lua", "NR_Server_Training.lua", "NR_Server_Weight.lua"]
    for n in names:
        with open(os.path.join(SERVER, n), encoding="utf-8") as fh:
            load(fh.read(), "@" + n)()
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")   # a second start wires nothing twice
    G = rt.globals()
    S = G.NutritionRevamp.server
    assert len(S.players.onMinute) == 0                     # the pipeline's named steps (Plan 10 R2)
    same = rt.eval("rawequal")
    assert same(S.minute.steps["strength"], S.strength.minute)
    assert same(S.minute.steps["weight"], S.weight.minute)
    order = [S.minute.ORDER[i] for i in range(1, len(S.minute.ORDER) + 1)]
    assert order[-3:] == ["weight", "writer", "store"] and order.index("strength") < order.index("weight")
    assert S.weight.wired is True


# --- the legacy-mirror option text (whole-pass issue 14) ---------------------------------------------

def test_legacy_mirror_tooltip_names_the_strength_bonus_only():
    # #2112: the protein store's experience bonus is on Strength experience only, never Fitness
    import json
    path = os.path.join(SHARED, "Translate", "EN", "Sandbox.json")
    with open(path, encoding="utf-8") as fh:
        tip = json.load(fh)["Sandbox_NR_LegacyMirror_tooltip"]
    assert "applies to Strength experience only" in tip
    assert "Fitness" not in tip
