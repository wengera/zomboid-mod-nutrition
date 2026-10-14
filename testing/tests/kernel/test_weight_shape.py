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
# Plan 13 Task 15: the registry stand-ins are opaque sentinels, never the trait's name nor a registry id, so a write
# that built an id from a name would miss every trait.
SENTINEL = "T#"
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
    CharacterTrait = { OBESE = "T#OBESE", OVERWEIGHT = "T#OVERWEIGHT", UNDERWEIGHT = "T#UNDERWEIGHT",
                       VERY_UNDERWEIGHT = "T#VERY_UNDERWEIGHT", EMACIATED = "T#EMACIATED",
                       STRONG = "T#STRONG" }
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
# { name, value } into cfg.calls; the trait collection reads cfg.traits, and its add and remove record
# { "add" or "remove", sentinel } and edit cfg.traits. applyTraitFromWeight raises: Plan 13 Task 15 retired it.
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
    nut.applyTraitFromWeight = function(self)
        rec("applyTraitFromWeight", true)
        error("stub: applyTraitFromWeight is retired")
    end
    p.getNutrition = function(self) return nut end
    p.getCharacterTraits = function(self)
        local coll = {
            get = function(s, t) return self.cfg.traits[t] == true end,
            add = function(s, t)
                if cfg.raising == "add" then error("stub: add raised") end
                rec("add", t)
                self.cfg.traits[t] = true
            end,
            remove = function(s, t)
                if cfg.raising == "remove" then error("stub: remove raised") end
                rec("remove", t)
                self.cfg.traits[t] = nil
            end,
        }
        if cfg.noAdd then coll.add = nil end
        if cfg.noGet then coll.get = nil end
        return coll
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
    cfg.traits = h.table({SENTINEL + t: True for t in (traits or [])})
    return h.rt.eval(PLAYER)(cfg)


def held(p):
    """The trait names the stand-in collection holds, sorted."""
    return sorted(k[len(SENTINEL):] for k, v in p.cfg.traits.items() if v is True)


def record_for(h, fm=15.0, lm=65.0, band=None, fatT=0, thinT=0, dirty=False):
    """A body built from the no-trait creation body, then its masses set to fm + lm exactly (lx 0), its trait rungs
    (fatT, thinT) and band word set by hand and traitsDirty set when dirty (the day close's stamp)."""
    record = h.rt.table()
    body = h.K.body["new"](h.K.body.create(None, None, h.K.strength.DEFAULTS, 1), 1, 99.0)
    body.fm = fm
    body.lm = lm
    for i in range(1, 8):
        body.mass7[i] = fm + lm
    if band is not None:
        body.band = band
    body.fatT = fatT
    body.thinT = thinT
    body.traitsDay = body.dayIndex
    if dirty:
        body.traitsDirty = True
    record.body = body
    return record


def minute(h, p, record, age=100.0):
    return h.rt.eval(MINUTE)(p, record, age)


def calls(p, name=None):
    out = [(c[1], c[2]) for c in p.cfg.calls.values()]
    if name is None:
        return out
    return [v for n, v in out if n == name]


def edits(p, name):
    """The trait names an add or remove was called with, sorted."""
    return sorted(v[len(SENTINEL):] for v in calls(p, name))


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


def test_the_weight_slot_counts_the_labile_lean(wgt_host):
    # ruling 13-20: the weight slot is the body mass fm + lm + lx, and the trend reads it against the same ring
    h = wgt_host
    p = player(h)
    record = record_for(h, fm=15.0, lm=65.0)        # the ring at 80 kg
    record["body"].lm = 63.5
    record["body"].lx = 1.5
    minute(h, p, record)
    assert calls(p, "setWeight") == [80.0]
    assert calls(p, "setIncWeight") == [False] and calls(p, "setDecWeight") == [False]


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


def test_weight_is_written_before_the_trait_write(wgt_host):
    h = wgt_host
    p = player(h)
    minute(h, p, record_for(h, fm=20.0, lm=65.0, band="overweight", fatT=1, dirty=True))
    names = [n for n, _ in calls(p)]
    assert names.index("setWeight") < names.index("add")


# --- the trait writes from the section 8 axes (Plan 13 Task 15; #2099, #2603, #0550) -----------------

@pytest.fixture
def marks(wgt_host):
    """A bus stand-in whose markBand records the username; the real bus is put back after."""
    h = wgt_host
    keep = h.G.NutritionRevamp.server.bus
    got = h.rt.eval("function() local t = {}; NR_TEST_MARKS = t; return t end")()
    h.G.NutritionRevamp.server.bus = h.rt.eval(
        "function() return { markBand = function(u) NR_TEST_MARKS[#NR_TEST_MARKS + 1] = u end } end")()
    try:
        yield got
    finally:
        h.G.NutritionRevamp.server.bus = keep


def test_an_overweight_axis_adds_overweight_and_removes_the_other_four_with_one_push(wgt_host, marks):
    h = wgt_host
    p = player(h, traits=["OBESE", "UNDERWEIGHT", "VERY_UNDERWEIGHT", "EMACIATED", "STRONG"])
    record = record_for(h, fm=20.0, lm=65.0, band="overweight", fatT=1, dirty=True)
    s0, n0 = stats(h), pushes(h)
    minute(h, p, record)
    assert edits(p, "add") == ["OVERWEIGHT"]
    assert edits(p, "remove") == ["EMACIATED", "OBESE", "UNDERWEIGHT", "VERY_UNDERWEIGHT"]
    assert held(p) == ["OVERWEIGHT", "STRONG"]
    assert pushes(h) == n0 + 1
    s = stats(h)
    assert s["pushes"] == s0["pushes"] + 1
    assert s["bandChanges"] == s0["bandChanges"] + 1
    assert s["bandRepairs"] == s0["bandRepairs"]
    assert not record.body.traitsDirty
    assert list(marks.values()) == ["admin"]
    assert record.body.band == "overweight"           # the day close's word, never rewritten here


def test_an_admin_removal_under_an_obese_axis_is_re_added_the_next_minute(wgt_host, marks):
    h = wgt_host
    p = player(h, traits=["OBESE"])
    record = record_for(h, fm=40.0, lm=65.0, band="obese", fatT=2)
    minute(h, p, record)
    assert calls(p, "add") == [] and calls(p, "remove") == []
    p.cfg.traits[SENTINEL + "OBESE"] = None           # an admin's removal
    s0, n0 = stats(h), pushes(h)
    minute(h, p, record, 100.0 + 1 / 60)
    assert edits(p, "add") == ["OBESE"]
    assert held(p) == ["OBESE"]
    assert pushes(h) == n0 + 1
    s = stats(h)
    assert s["bandRepairs"] == s0["bandRepairs"] + 1
    assert s["bandChanges"] == s0["bandChanges"]
    assert len(marks) == 0                             # the band did not change


@pytest.mark.parametrize("fatT, thinT, band, trait", [
    (1, 0, "overweight", "OVERWEIGHT"),
    (2, 0, "obese", "OBESE"),
    (0, 1, "underweight", "UNDERWEIGHT"),
    (0, 2, "veryUnderweight", "VERY_UNDERWEIGHT"),
    (0, 3, "emaciated", "EMACIATED"),
])
def test_each_rung_writes_its_own_trait_through_the_registry_object(wgt_host, fatT, thinT, band, trait):
    h = wgt_host
    p = player(h)
    minute(h, p, record_for(h, band=band, fatT=fatT, thinT=thinT, dirty=True))
    assert calls(p, "add") == [h.G.CharacterTrait[trait]]
    assert held(p) == [trait]


def test_a_thin_rung_replaces_a_held_fat_trait(wgt_host):
    h = wgt_host
    p = player(h, traits=["OVERWEIGHT"])
    minute(h, p, record_for(h, fm=5.0, lm=48.0, band="underweight", thinT=1, dirty=True))
    assert edits(p, "add") == ["UNDERWEIGHT"]
    assert edits(p, "remove") == ["OVERWEIGHT"]


def test_a_dirty_axis_already_held_clears_the_flag_and_marks_without_a_push(wgt_host, marks):
    h = wgt_host
    p = player(h, traits=["OBESE"])
    record = record_for(h, fm=40.0, lm=65.0, band="obese", fatT=2, dirty=True)
    s0, n0 = stats(h), pushes(h)
    minute(h, p, record)
    assert calls(p, "add") == [] and calls(p, "remove") == []
    assert pushes(h) == n0
    assert not record.body.traitsDirty
    assert stats(h)["bandChanges"] == s0["bandChanges"] + 1
    assert list(marks.values()) == ["admin"]


def test_a_normal_axis_with_stray_band_traits_is_repaired_with_one_push(wgt_host):
    h = wgt_host
    p = player(h, traits=["OBESE", "UNDERWEIGHT"])
    s0, n0 = stats(h), pushes(h)
    minute(h, p, record_for(h))
    assert edits(p, "remove") == ["OBESE", "UNDERWEIGHT"]
    assert calls(p, "add") == []
    assert held(p) == []
    assert pushes(h) == n0 + 1
    assert stats(h)["bandRepairs"] == s0["bandRepairs"] + 1


def test_a_normal_axis_ignores_a_non_band_trait(wgt_host):
    h = wgt_host
    p = player(h, traits=["STRONG"])
    n0 = pushes(h)
    minute(h, p, record_for(h))
    assert calls(p, "add") == [] and calls(p, "remove") == []
    assert pushes(h) == n0


def test_a_stray_beside_the_wanted_trait_goes_at_the_next_day(wgt_host):
    h = wgt_host
    p = player(h, traits=["OBESE", "OVERWEIGHT"])
    record = record_for(h, fm=40.0, lm=65.0, band="obese", fatT=2)
    minute(h, p, record)
    assert calls(p, "remove") == []
    record.body.dayIndex = record.body.dayIndex + 1
    minute(h, p, record, 100.0 + 1 / 60)
    assert edits(p, "remove") == ["OVERWEIGHT"]
    assert held(p) == ["OBESE"]


def test_a_raise_after_a_landed_removal_still_pushes(wgt_host):
    h = wgt_host
    p = player(h, traits=["OBESE"])
    p.cfg.raising = "add"
    record = record_for(h, band="overweight", fatT=1, dirty=True)
    n0 = pushes(h)
    minute(h, p, record)
    assert held(p) == []
    assert pushes(h) == n0 + 1


def test_an_absent_get_differs_from_nothing_and_writes_nothing(wgt_host):
    # review T15 m2: an unreadable get compares nothing
    h = wgt_host
    p = player(h, traits=["OBESE"])
    p.cfg.noGet = True
    n0 = pushes(h)
    minute(h, p, record_for(h))
    assert calls(p, "add") == [] and calls(p, "remove") == []
    assert pushes(h) == n0


def test_a_nil_fat_rung_never_raises(wgt_host):
    # review T15 m2: wantOf over a nil rung builds a fresh table, never a cache key
    h = wgt_host
    p = player(h)
    record = record_for(h)
    record.body.fatT = None
    s0 = stats(h)
    minute(h, p, record)
    assert stats(h)["failures"] == s0["failures"]
    assert calls(p, "setWeight") == [80.0]


def test_a_dirty_write_with_an_absent_get_keeps_the_flag(wgt_host):
    # review T15 m2
    h = wgt_host
    p = player(h)
    p.cfg.noGet = True
    record = record_for(h, band="overweight", fatT=1, dirty=True)
    minute(h, p, record)
    assert record.body.traitsDirty is True


def test_a_thin_rung_excludes_a_held_fat_rung_at_the_write(wgt_host):
    # review T15 m3: precedence holds at the write even when both rungs are set
    h = wgt_host
    p = player(h, traits=["OBESE"])
    minute(h, p, record_for(h, fm=5.0, lm=48.0, band="underweight", fatT=2, thinT=1, dirty=True))
    assert held(p) == ["UNDERWEIGHT"]
    assert edits(p, "remove") == ["OBESE"]


def test_apply_trait_from_weight_is_never_called(wgt_host):
    # Plan 13 Task 15 (spec section 8): vanilla's 65/75/85/100 kg band refresh is retired; the stub raises
    h = wgt_host
    s0 = stats(h)
    cases = [
        dict(fm=5.0, lm=60.0),                                     # 65 kg: vanilla Very Underweight, the axes normal
        dict(fm=20.0, lm=65.0, band="overweight", fatT=1, dirty=True),
        dict(fm=40.0, lm=65.0, band="obese", fatT=2),
        dict(fm=5.0, lm=40.0, band="emaciated", thinT=3, dirty=True),
        dict(fm=15.0, lm=65.0, band="normal", dirty=True),
    ]
    for kw in cases:
        p = player(h, traits=["UNDERWEIGHT"])
        minute(h, p, record_for(h, **kw))
        assert calls(p, "applyTraitFromWeight") == [], kw
    assert stats(h)["failures"] == s0["failures"]
    with open(WEIGHT, encoding="utf-8") as fh:
        src = fh.read()
    assert '"applyTraitFromWeight"' not in src
    assert "K.body.band(" not in src
    assert "BAND_TRAIT " not in src and "BAND_TRAIT=" not in src


def test_no_name_built_registry_id():
    # Task 10's review: the id of VERY_UNDERWEIGHT is "base:very underweight", with a space; the traits are the
    # CharacterTrait fields (#0550)
    with open(WEIGHT, encoding="utf-8") as fh:
        src = fh.read()
    for bad in ("base:", "ResourceLocation", "CharacterTrait.get(", "string.lower", ":lower("):
        assert bad not in src, bad


# Rule 6: with nothing differing the minute makes no more Java calls than at HEAD 922c4f52 (the old repair read: the
# collection and five gets for a normal band, one get for a held band). Every method of the player stand-in and of
# every table one of them returns is counted.
JAVA_COUNT = r"""
function(p, C)
    local seen = {}
    local function wrap(t)
        if type(t) ~= "table" or seen[t] then return t end
        seen[t] = true
        local names = {}
        for k, v in pairs(t) do
            if type(v) == "function" then names[#names + 1] = k end
        end
        for i = 1, #names do
            local k = names[i]
            local f = t[k]
            t[k] = function(...)
                C.n = C.n + 1
                return wrap(f(...))
            end
        end
        return t
    end
    wrap(p)
end
"""


@pytest.mark.parametrize("fm, lm, band, fatT, thinT, traits, head", [
    (15.0, 65.0, "normal", 0, 0, [], 15),                  # read at 922c4f52
    (15.0, 65.0, "normal", 0, 0, ["STRONG"], 15),
    (40.0, 65.0, "obese", 2, 0, ["OBESE"], 11),
    (5.0, 40.0, "emaciated", 0, 3, ["EMACIATED"], 11),
])
def test_a_minute_with_nothing_differing_makes_no_more_java_calls_than_head(wgt_host, fm, lm, band, fatT, thinT,
                                                                            traits, head):
    h = wgt_host
    p = player(h, traits=traits)
    record = record_for(h, fm=fm, lm=lm, band=band, fatT=fatT, thinT=thinT)
    C = h.rt.eval("{ n = 0 }")
    h.rt.eval(JAVA_COUNT)(p, C)
    n0 = pushes(h)
    minute(h, p, record)
    assert C.n <= head, C.n
    assert calls(p, "add") == [] and calls(p, "remove") == []
    assert pushes(h) == n0


def test_missing_push_global_is_counted(wgt_host):
    h = wgt_host
    saved = h.G.sendSyncPlayerFields
    h.G.sendSyncPlayerFields = None
    try:
        p = player(h)
        s0 = stats(h)
        record = record_for(h, fm=20.0, lm=65.0, band="overweight", fatT=1, dirty=True)
        minute(h, p, record)
    finally:
        h.G.sendSyncPlayerFields = saved
    assert edits(p, "add") == ["OVERWEIGHT"]
    assert not record.body.traitsDirty
    s = stats(h)
    assert s["pushMissing"] == s0["pushMissing"] + 1
    assert s["pushes"] == s0["pushes"]


def test_no_trait_registry_keeps_the_dirty_flag(wgt_host, marks):
    h = wgt_host
    saved = h.G.CharacterTrait
    h.G.CharacterTrait = None
    try:
        p = player(h, traits=["OBESE"])
        s0 = stats(h)
        record = record_for(h, band="overweight", fatT=1, dirty=True)
        minute(h, p, record)
    finally:
        h.G.CharacterTrait = saved
    assert calls(p, "add") == [] and calls(p, "remove") == []
    assert calls(p, "setWeight") == [80.0]
    assert record.body.traitsDirty is True             # the next minute retries
    assert len(marks) == 0
    assert stats(h)["failures"] == s0["failures"]


def test_an_unreadable_trait_collection_keeps_the_dirty_flag(wgt_host):
    h = wgt_host
    p = player(h)
    p.getCharacterTraits = None
    record = record_for(h, band="overweight", fatT=1, dirty=True)
    s0 = stats(h)
    minute(h, p, record)
    assert record.body.traitsDirty is True
    assert calls(p, "setWeight") == [80.0]
    assert stats(h)["failures"] == s0["failures"]


def test_an_absent_add_keeps_the_dirty_flag_and_the_next_minute_lands_it(wgt_host, marks):
    h = wgt_host
    p = player(h, traits=["OBESE"])
    p.cfg.noAdd = True
    record = record_for(h, band="overweight", fatT=1, dirty=True)
    n0 = pushes(h)
    minute(h, p, record)
    assert edits(p, "remove") == ["OBESE"]
    assert pushes(h) == n0 + 1                         # the removal landed: one push for it
    assert record.body.traitsDirty is True
    assert len(marks) == 0
    p.cfg.noAdd = None
    minute(h, p, record, 100.0 + 1 / 60)
    assert held(p) == ["OVERWEIGHT"]
    assert pushes(h) == n0 + 2
    assert not record.body.traitsDirty
    assert list(marks.values()) == ["admin"]


def test_a_raising_add_is_a_counted_failure_and_the_flag_is_kept(wgt_host, marks):
    h = wgt_host
    p = player(h)
    p.cfg.raising = "add"
    record = record_for(h, band="overweight", fatT=1, dirty=True)
    s0, n0 = stats(h), pushes(h)
    minute(h, p, record)
    assert stats(h)["failures"] == s0["failures"] + 1
    assert "add raised" in WGT(h).lastError
    assert calls(p, "setWeight") == [80.0]
    assert pushes(h) == n0
    assert record.body.traitsDirty is True
    assert len(marks) == 0
    p.cfg.raising = None
    minute(h, p, record, 100.0 + 1 / 60)
    assert held(p) == ["OVERWEIGHT"]
    assert not record.body.traitsDirty


# --- the legacy macro mirror (ruling 13) -----------------------------------------------------------

def window(h, body, hour, **amounts):
    """Plan 11d Task 9c: lays amounts in game hour `hour` of the body's trailing-24 h window (built at 99.0, which
    NR_Server_Metabolism moves and this step only reads) and marks its closed sums for a rebuild."""
    t = body.trail
    for k, v in amounts.items():
        t[k][h.K.body.trailSlot(hour)] = v
    t.ch = -1


def test_mirror_on_writes_the_four_mapped_stores(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h)
    body = record.body
    h.G.NR_TEST_TOD = 0.0                               # the clock hour never enters the window
    body.ebDay = 900.0                                  # the day's figures are not read: the window is
    body.pDay = 500.0
    window(h, body, 98, kcal=1500.0, ee=2000.0, p=48.0, carb=300.0, lip=100.0)   # eb24h -500; 300 g -> 0; 100 g -> 30
    window(h, body, 90, p=48.0)                         # (48 + 48) / 80 = 1.2 g/kg/d
    s0 = stats(h)
    minute(h, p, record)
    assert calls(p, "setCalories") == [-500.0]
    assert len(calls(p, "setProteins")) == 1
    assert abs(calls(p, "setProteins")[0] - 75.0) < TOL
    assert calls(p, "setCarbohydrates") == [0.0]
    assert calls(p, "setLipids") == [30.0]
    assert body.mirrorLast is None                      # the four written values are kept nowhere: nothing read them
    assert stats(h)["mirrorWrites"] == s0["mirrorWrites"] + 1


def test_mirror_clamps_to_the_stores(wgt_host):
    h = wgt_host
    p = player(h)
    record = record_for(h)
    body = record.body
    window(h, body, 99, kcal=9000.0)                    # the current hour: a 9000 kcal surplus, no protein
    body.p7[7] = 500.0                                  # a closed day's protein is not the window's
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
    # NR_Server_Metabolism owns the window (it runs first in the minute); a window missing here is a failure counted
    # under the pcall, after the weight write
    h = wgt_host
    p = player(h)
    record = record_for(h)
    record.body.trail = None
    s0 = stats(h)
    minute(h, p, record)
    assert record.body.trail is None
    assert calls(p, "setWeight") == [80.0]
    assert stats(h)["failures"] == s0["failures"] + 1
    with open(WEIGHT, encoding="utf-8") as fh:
        assert "RINGS" not in fh.read()


def test_mirror_reads_the_oldest_hour_by_its_share_inside_the_window(wgt_host):
    # Plan 11d Task 9c: at 99.25 the oldest hour (75) is three quarters inside the window, at 99.75 a quarter
    h = wgt_host
    p = player(h)
    record = record_for(h)
    body = record.body
    body.trail.at = 99.25
    window(h, body, 75, carb=400.0)
    window(h, body, 99, carb=100.0)
    minute(h, p, record)
    assert calls(p, "setCarbohydrates") == [100.0]      # 400 x 0.75 + 100 - 300
    body.trail.at = 99.75
    minute(h, p, record)
    assert calls(p, "setCarbohydrates")[1] == -100.0    # 400 x 0.25 + 100 - 300


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
    assert "a stray band trait beside the wanted one is removed at the first minute of the next record day (a once-a-day audit; the minute's held check reads the wanted trait alone, Rule 6)" in lim


def test_never_writes_the_strength_level_or_carry():
    # Plan 13 Task 15: the five weight-band traits are this file's to add and remove; the level and the carry are not
    with open(WEIGHT, encoding="utf-8") as fh:
        src = fh.read()
    for name in ("setPerkLevelDebug", "LevelPerk", "LoseLevel", "addXp", "AddXP", "setMaxWeightDelta"):
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
        NutritionRevamp.server.players = {}
    """)
    names = sorted(["NR_Server_Weight.lua", "NR_Server_Strength.lua",
                    "NR_Server_Metabolism.lua", "NR_Server_Kinetics.lua", "NR_Server_Minute.lua"])
    assert names == ["NR_Server_Kinetics.lua", "NR_Server_Metabolism.lua", "NR_Server_Minute.lua",
                     "NR_Server_Strength.lua", "NR_Server_Weight.lua"]
    for n in names:
        with open(os.path.join(SERVER, n), encoding="utf-8") as fh:
            load(fh.read(), "@" + n)()
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")   # a second start wires nothing twice
    G = rt.globals()
    S = G.NutritionRevamp.server
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


def test_a_raising_push_global_is_counted_and_the_band_still_marked(wgt_host, marks):
    # Plan 12 (S B6): a raise in the push lost the bus mark for good and skipped the mirror.
    h = wgt_host
    saved = h.G.sendSyncPlayerFields
    h.G.sendSyncPlayerFields = h.rt.eval("function(p, n) error('the push raised') end")
    try:
        p = player(h)
        record = record_for(h, fm=20.0, lm=65.0, band="overweight", fatT=1, dirty=True)
        s0 = stats(h)
        minute(h, p, record)
    finally:
        h.G.sendSyncPlayerFields = saved
    s = stats(h)
    assert held(p) == ["OVERWEIGHT"]
    assert not record.body.traitsDirty
    assert s["pushMissing"] == s0["pushMissing"] + 1
    assert s["failures"] == s0["failures"]
    assert len(marks) == 1
    assert s["mirrorWrites"] == s0["mirrorWrites"] + 1
