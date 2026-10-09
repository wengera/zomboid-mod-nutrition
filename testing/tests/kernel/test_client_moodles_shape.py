"""The moodles and the fallback column (Plan 7 Task 8, ruling 10): NR_Client_Moodles.lua.

The pattern of test_client_panel_shape.py: a FRESH Lua 5.1 runtime per test, Lua
stand-ins that count -- Events (OnGameBoot, OnCreatePlayer, OnGameStart, OnServerCommand, OnKeyPressed), a stub
MoodleFramework whose createMoodle adds its own OnCreatePlayer builder (as MF_ISMoodle.lua:25-31 does) and whose
widget mirrors the live file's setThresholds (:155-174), getGoodBadNeutral (:120-125), getLevel (:127-143) and the
addedToUIManager flag (:102-109), an ISUIElement with derive/new and the members the column calls, getTexture,
getPlayerScreenLeft/Top/Width. The kernel loads in this runtime of its own, so the session host's coverage gate is
untouched. A stub proves the wiring, the guards, the value map and the option gate, never the engine: whether the
framework draws the six moodles and the column renders live is x183's (Task 11 arm F).
"""
import glob
import os
import re

import pytest
import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
SHARED = os.path.join(LUA, "shared")
CLIENT = os.path.join(LUA, "client")
CORE = os.path.join(SHARED, "NR_Core.lua")
RECORDS = os.path.join(SHARED, "NR_Data_Records.lua")
MODOPTIONS = os.path.join(CLIENT, "NR_Client_ModOptions.lua")
MOODLES = os.path.join(CLIENT, "NR_Client_Moodles.lua")
VIEW = os.path.join(CLIENT, "NR_Client_View.lua")
CLASSES = ["energy", "hydration", "deficiency", "excess", "stimulant", "sleep", "overfull"]  # Plan 11c Task 7: overfull

ENV = r"""
NR_T = { adds = {}, printed = 0, textures = false, texCalls = 0,
         ui = { adds = 0, removes = 0, inits = 0, insts = 0, rects = 0, texs = 0 } }
print = function() NR_T.printed = NR_T.printed + 1 end
local function event(name)
    NR_T.adds[name] = {}
    return { Add = function(fn) local l = NR_T.adds[name]; l[#l + 1] = fn end }
end
Events = {
    OnGameBoot = event("OnGameBoot"),
    OnCreatePlayer = event("OnCreatePlayer"),
    OnGameStart = event("OnGameStart"),
    OnServerCommand = event("OnServerCommand"),
    OnKeyPressed = event("OnKeyPressed"),
    OnPlayerDeath = event("OnPlayerDeath"),
}
isClient = function() return NR_T.client ~= false end
isServer = function() return false end
NR_T.player = { hasTrait = function(self, enum) return false end }
getPlayer = function() return NR_T.player end
getSpecificPlayer = function(n) return NR_T.player end
getText = function(k) return k end
getTexture = function(path)
    NR_T.texCalls = NR_T.texCalls + 1
    NR_T.lastTexPath = path
    if NR_T.textures then return { path = path } end
    return nil
end
getPlayerScreenLeft = function(n) return 0 end
getPlayerScreenTop = function(n) return 0 end
getPlayerScreenWidth = function(n) return 1280 end

ISUIElement = {}
function ISUIElement:derive(name)
    local c = {}
    setmetatable(c, self)
    self.__index = self
    c.Type = name
    return c
end
function ISUIElement:new(x, y, w, h)
    local o = { x = x, y = y, width = w, height = h }
    setmetatable(o, self)
    self.__index = self
    return o
end
function ISUIElement:initialise() NR_T.ui.inits = NR_T.ui.inits + 1 end
function ISUIElement:instantiate() NR_T.ui.insts = NR_T.ui.insts + 1 end
function ISUIElement:addToUIManager() NR_T.ui.adds = NR_T.ui.adds + 1; self.managed = true end
function ISUIElement:removeFromUIManager() NR_T.ui.removes = NR_T.ui.removes + 1; self.managed = false end
function ISUIElement:drawRect(x, y, w, h, a, r, g, b) NR_T.ui.rects = NR_T.ui.rects + 1 end
function ISUIElement:drawTextureScaled(t, x, y, w, h, a) NR_T.ui.texs = NR_T.ui.texs + 1 end
"""

MF_STUB = r"""
NR_T.mf = { creates = 0, builds = 0, raiseSet = false, nilGet = false }
MF = { MoodlesStorage = {}, TooLargeValue = 100000 }
local Moodle = {}
Moodle.__index = Moodle
function Moodle:setThresholds(bad4, bad3, bad2, bad1, good1, good2, good3, good4)
    if nil == good4 then good4 = MF.TooLargeValue end
    if nil == good3 then good3 = good4 end
    if nil == good2 then good2 = good3 end
    if nil == good1 then good1 = good2 end
    if nil == bad4 then bad4 = -MF.TooLargeValue end
    if nil == bad3 then bad3 = bad4 end
    if nil == bad2 then bad2 = bad3 end
    if nil == bad1 then bad1 = bad2 end
    self.th = { bad4 = bad4, bad3 = bad3, bad2 = bad2, bad1 = bad1, good1 = good1, good2 = good2, good3 = good3, good4 = good4 }
    self.thresholdCalls = self.thresholdCalls + 1
end
function Moodle:getGoodBadNeutral()
    local v = self.value
    if v >= self.th.good1 then return 1 elseif v <= self.th.bad1 then return 2 end
    return 0
end
function Moodle:getLevel()
    local v, t = self.value, self.th
    if v >= t.good4 or v <= t.bad4 then return 4
    elseif v >= t.good3 or v <= t.bad3 then return 3
    elseif v >= t.good2 or v <= t.bad2 then return 2
    elseif v >= t.good1 or v <= t.bad1 then return 1 end
    return 0
end
function Moodle:setValue(v)
    if NR_T.mf.raiseSet then error("setValue boom") end
    self.value = v
    self.sets = self.sets + 1
    if not self.addedToUIManager and self:getGoodBadNeutral() ~= 0 then
        self.addedToUIManager = true
    elseif self.addedToUIManager and self:getGoodBadNeutral() == 0 then
        self.addedToUIManager = false
    end
end
function Moodle:setPicture(gbn, lvl, tex) self.pics[gbn .. ":" .. lvl] = tex end
function Moodle:setTitle(gbn, lvl, text) self.titles[gbn .. ":" .. lvl] = text end
function Moodle:setDescription(gbn, lvl, text) self.descs[gbn .. ":" .. lvl] = text end
function MF.createMoodle(name)
    NR_T.mf.creates = NR_T.mf.creates + 1
    Events.OnCreatePlayer.Add(function(playerNum)
        NR_T.mf.builds = NR_T.mf.builds + 1
        local m = setmetatable({ name = name, value = 0.5, sets = 0, thresholdCalls = 0, pics = {}, titles = {}, descs = {} }, Moodle)
        m:setThresholds(0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9)
        MF.MoodlesStorage[playerNum] = MF.MoodlesStorage[playerNum] or {}
        MF.MoodlesStorage[playerNum][name] = m
    end)
end
function MF.getMoodle(name, playerNum)
    if NR_T.mf.nilGet then return nil end
    local s = MF.MoodlesStorage[playerNum or 0]
    if s == nil then return nil end
    return s[name]
end
"""


def _src(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _load(rt, path):
    rt.eval("function(src, name) return assert(loadstring(src, name)) end")(_src(path), "@" + os.path.basename(path))()


def _kernel(rt):
    _load(rt, CORE)
    for path in sorted(glob.glob(os.path.join(SHARED, "NR_Kernel*.lua"))):
        _load(rt, path)
    _load(rt, RECORDS)


def rt_env(mf=False, textures=False, view=True):
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(ENV)
    G(rt).NR_T.textures = textures
    if mf:
        rt.execute(MF_STUB)
    _kernel(rt)
    for path in (MODOPTIONS, MOODLES) + ((VIEW,) if view else ()):  # the engine's path order (#1055)
        _load(rt, path)
    return rt


def G(rt):
    return rt.globals()


def M(rt):
    return G(rt).NutritionRevamp.client.moodles


def fire(rt, event, args=""):
    rt.execute("for _, f in ipairs(NR_T.adds.%s) do f(%s) end" % (event, args))


def boot(rt):
    fire(rt, "OnGameBoot")


def create(rt, n=0):
    fire(rt, "OnCreatePlayer", "%d, NR_T.player" % n)


def classes(rt, **levels):
    t = rt.table()
    for c in CLASSES:
        t[c] = levels.get(c, 0)
    return t


def handle(rt, cls, n=0):
    return G(rt).MF.MoodlesStorage[n]["NR_" + cls]


def option(rt, on):
    rt.execute("NutritionRevamp.client.modOptions.moodles = function() return %s end" % ("true" if on else "false"))


def code_only(src):
    src = re.sub(r"--\[(=*)\[.*?\]\1\]", "", src, flags=re.S)
    return "\n".join(line.split("--", 1)[0] for line in src.splitlines())


# ------------------------------------------------------------------------------------------- loading

def test_the_file_loads_with_no_engine():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    _kernel(rt)
    _load(rt, MOODLES)
    m = M(rt)
    assert m.route == "none" and m.cls is None and m.column is None
    assert list(m.classes.values()) == CLASSES
    assert G(rt).NR_ClientMoodles_Installed is not None
    m.apply(classes(rt, deficiency=3))       # no route, no handles, no column: nothing raises
    assert m.levels.deficiency == 3
    assert m.probe("deficiency") == (3, False, "none")
    m.onCreatePlayer(0, None)                 # no side test: nothing built
    m.onGameBoot()                            # MF absent: the own route, but no ISUIElement to derive from
    assert m.route == "own" and m.column is None
    assert m.renderColumn(None) is None


def test_the_listener_array_is_created_when_the_view_loads_after():
    rt = rt_env(view=False)
    v = G(rt).NutritionRevamp.client.view
    assert len(v.listeners) == 1
    _load(rt, VIEW)                           # NR_Client_View.lua carries the array over (:43)
    v = G(rt).NutritionRevamp.client.view
    assert len(v.listeners) == 1 and v.refresh is not None


def test_the_listener_array_survives_when_the_view_already_exists():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(ENV)
    _kernel(rt)
    rt.execute("NR_T.other = function() end; NutritionRevamp.client.view = { listeners = { NR_T.other }, keep = 7 }")
    _load(rt, MOODLES)
    v = G(rt).NutritionRevamp.client.view
    assert v.keep == 7 and len(v.listeners) == 2
    assert rt.eval("rawequal")(v.listeners[1], G(rt).NR_T.other)


def test_a_reload_adds_no_second_listener_or_handler():
    rt = rt_env()
    _load(rt, MOODLES)
    assert len(G(rt).NutritionRevamp.client.view.listeners) == 1
    assert len(G(rt).NR_T.adds.OnGameBoot) == 1
    boot(rt)
    boot(rt)
    assert len(G(rt).NR_T.adds.OnCreatePlayer) == 2   # the view's and the moodles' (added inside the boot handler)


def test_moodlesui_is_never_named_in_code():
    # ruling 10: the column sits at a fixed inset of the viewport, never anchored to the vanilla stack
    assert "MoodlesUI" not in code_only(_src(MOODLES))


# ------------------------------------------------------------------------------------------- the own route

def test_the_route_is_own_when_mf_is_absent_and_the_create_handler_follows_the_boot():
    rt = rt_env()
    assert M(rt).route == "none"
    before = len(G(rt).NR_T.adds.OnCreatePlayer)
    boot(rt)
    assert M(rt).route == "own"
    assert len(G(rt).NR_T.adds.OnCreatePlayer) == before + 1
    assert M(rt).stats.created == 0


def test_the_column_sits_at_the_fixed_inset_and_joins_the_ui_manager():
    rt = rt_env()
    boot(rt)
    create(rt)
    col = M(rt).column
    assert col is not None and G(rt).NR_Client_MoodleColumn.Type == "NR_Client_MoodleColumn"
    assert (col.x, col.y, col.width, col.height) == (1280 - 96, 240, 40, 7 * 44)
    assert col.onUI is True and col.managed is True
    assert M(rt).probe("deficiency") == (0, True, "own")


def test_the_column_suspends_on_death_until_the_next_apply():
    rt = rt_env()
    boot(rt)
    create(rt)
    m = M(rt)
    m.apply(classes(rt, energy=2, deficiency=3))
    m.column.render(m.column)
    assert m.lastDrawn == 2
    fire(rt, "OnPlayerDeath", "NR_T.player")
    assert m.levels.energy == 0 and m.levels.deficiency == 0
    m.column.render(m.column)
    assert m.lastDrawn == 0
    assert m.stats.errors == 0
    m.apply(classes(rt, energy=1))
    m.column.render(m.column)
    assert m.lastDrawn == 1


def test_player_one_builds_no_column():
    rt = rt_env()
    boot(rt)
    create(rt, 1)
    assert M(rt).column is None


def test_a_respawn_replaces_the_column():
    rt = rt_env()
    boot(rt)
    create(rt)
    old = M(rt).column
    create(rt)
    new = M(rt).column
    assert not rt.eval("rawequal")(old, new)
    assert old.onUI is False and old.managed is False and new.onUI is True


def test_apply_sets_the_levels_and_the_render_counts_and_draws_rects_with_no_texture():
    rt = rt_env()
    boot(rt)
    create(rt)
    m = M(rt)
    sets0 = m.stats.sets                     # the create's own re-apply counted seven
    m.apply(classes(rt, energy=2, deficiency=3))
    assert m.levels.energy == 2 and m.levels.deficiency == 3 and m.levels.sleep == 0
    assert sets0 == 7 and m.stats.sets == 14
    m.column.render(m.column)
    ui = G(rt).NR_T.ui
    assert m.stats.renders == 1
    assert ui.texs == 0
    assert ui.rects == 2 + 2 + 3            # two icons as rects, then 2 and 3 pips
    assert m.lastDrawn == 2
    assert m.probe("deficiency") == (3, True, "own")


def test_the_render_draws_textures_when_they_load():
    rt = rt_env(textures=True)
    boot(rt)
    create(rt)
    assert G(rt).NR_T.lastTexPath.startswith("media/ui/NutritionRevamp/")
    m = M(rt)
    m.apply(classes(rt, hydration=4))
    m.column.render(m.column)
    ui = G(rt).NR_T.ui
    assert ui.texs == 1 and ui.rects == 4


def test_a_render_that_raises_is_counted_not_propagated():
    rt = rt_env()
    boot(rt)
    create(rt)
    m = M(rt)
    m.apply(classes(rt, sleep=1))
    rt.execute("ISUIElement.drawRect = function() error('draw boom') end")
    m.column.render(m.column)
    assert m.stats.errors == 1


def test_the_option_off_removes_the_column_and_on_re_adds_it():
    rt = rt_env()
    boot(rt)
    create(rt)
    m = M(rt)
    option(rt, False)
    m.apply(classes(rt, sleep=2))
    assert m.column.onUI is False and m.column.managed is False
    assert m.probe("sleep") == (2, False, "own")
    option(rt, True)
    m.apply(classes(rt, sleep=2))
    assert m.column.onUI is True and m.column.managed is True


def test_a_column_built_while_the_option_is_off_stays_off_the_manager():
    rt = rt_env()
    boot(rt)
    option(rt, False)
    create(rt)
    assert M(rt).column.onUI is False and G(rt).NR_T.ui.adds == 0


def test_apply_skips_a_non_table():
    rt = rt_env()
    boot(rt)
    M(rt).apply(None)
    assert M(rt).stats.skips == 1 and M(rt).stats.sets == 0


# ------------------------------------------------------------------------------------------- the framework route

def test_the_route_is_framework_with_mf_and_seven_moodles_are_created():
    rt = rt_env(mf=True)
    boot(rt)
    m = M(rt)
    assert m.route == "framework"
    assert m.stats.created == 7 and G(rt).NR_T.mf.creates == 7
    create(rt)                                 # the framework's builders run first, then the mod's handler
    assert G(rt).NR_T.mf.builds == 7
    assert m.stats.got == 7 and m.stats.errors == 0
    for c in CLASSES:
        assert rt.eval("rawequal")(m.handles[c], handle(rt, c))
    assert m.column is None


@pytest.mark.parametrize("cls,bads", [
    ("energy", (0.4375, 0.3125, 0.1875, 0.0625)),
    ("sleep", (0.4375, 0.3125, 0.1875, 0.0625)),
    ("overfull", (0.4375, 0.3125, 0.1875, 0.0625)),
    ("deficiency", (0.5 - 0.5 * 0.5 / 3, 0.5 - 0.5 * 1.5 / 3, 0.5 - 0.5 * 2.5 / 3, -100000)),
    ("excess", (0.5 - 0.5 * 0.5 / 3, 0.25, 0.5 - 0.5 * 2.5 / 3, -100000)),
])
def test_the_thresholds_are_set_on_the_bad_side_with_no_good_side(rt_mf, cls, bads):
    h = handle(rt_mf, cls)
    th = h.th
    assert [th.bad1, th.bad2, th.bad3, th.bad4] == pytest.approx(list(bads))
    assert th.good1 == 100000 and th.good4 == 100000


@pytest.fixture
def rt_mf():
    rt = rt_env(mf=True)
    boot(rt)
    create(rt)
    return rt


@pytest.mark.parametrize("cls", CLASSES)
def test_apply_sets_each_value_and_the_framework_level_equals_the_class_level(rt_mf, cls):
    top = 3 if cls in ("deficiency", "excess") else 4
    m = M(rt_mf)
    h = handle(rt_mf, cls)
    for lv in range(0, top + 1):
        m.apply(classes(rt_mf, **{cls: lv}))
        want = 0.5 - 0.5 * lv / top
        assert h.value == pytest.approx(want)
        assert h.getLevel(h) == lv
        assert (h.addedToUIManager is True) == (lv > 0)
        assert m.probe(cls) == (lv, lv > 0, "framework")


def test_apply_sets_seven_values_per_call(rt_mf):
    m = M(rt_mf)
    sets0 = m.stats.sets
    m.apply(classes(rt_mf, energy=1, hydration=2, deficiency=3, excess=1, stimulant=4, sleep=2, overfull=1))
    assert m.stats.sets == sets0 + 7
    vals = {c: handle(rt_mf, c).value for c in CLASSES}
    assert vals == pytest.approx({"energy": 0.375, "hydration": 0.25, "deficiency": 0.0, "excess": 0.5 - 0.5 / 3,
                                  "stimulant": 0.0, "sleep": 0.25, "overfull": 0.375})


def test_the_option_off_neutralises_every_framework_value(rt_mf):
    m = M(rt_mf)
    m.apply(classes(rt_mf, energy=4, deficiency=3))
    assert handle(rt_mf, "energy").addedToUIManager is True
    option(rt_mf, False)
    m.apply(classes(rt_mf, energy=4, deficiency=3))
    for c in CLASSES:
        h = handle(rt_mf, c)
        assert h.value == 0.5 and h.getLevel(h) == 0 and h.addedToUIManager is not True
    assert m.levels.energy == 4                # the levels are kept, so the option back on restores them
    option(rt_mf, True)
    m.apply(m.levels)
    assert handle(rt_mf, "energy").value == 0.0


def test_the_last_levels_are_set_again_on_create(rt_mf):
    m = M(rt_mf)
    m.apply(classes(rt_mf, sleep=3))
    create(rt_mf)                               # a respawn: the framework builds fresh widgets at 0.5
    h = handle(rt_mf, "sleep")
    assert h.value == pytest.approx(0.125) and h.getLevel(h) == 3


def test_the_pictures_are_the_mods_icons_when_they_load_and_untouched_otherwise():
    rt = rt_env(mf=True, textures=True)
    boot(rt)
    create(rt)
    h = handle(rt, "excess")
    for lvl in range(1, 5):
        assert h.pics["2:%d" % lvl].path == "media/ui/NutritionRevamp/excess.png"
    rt2 = rt_env(mf=True)
    boot(rt2)
    create(rt2)
    assert len(list(handle(rt2, "excess").pics.keys())) == 0


def test_the_titles_and_descriptions_are_the_mods_keys(rt_mf):
    h = handle(rt_mf, "energy")
    # the stub getText answers the key itself, so NR.client.text falls back to the key's tail
    assert h.titles["2:1"] == "energy lvl1" and h.titles["2:4"] == "energy lvl4"
    assert h.descs["2:2"] == "Class energy 2"


def test_a_nil_handle_is_counted_and_skipped():
    rt = rt_env(mf=True)
    boot(rt)
    G(rt).NR_T.mf.nilGet = True
    create(rt)
    m = M(rt)
    assert m.stats.got == 0 and m.stats.errors == 7
    assert m.stats.skips == 7                  # the create's own re-apply found no handle
    m.apply(classes(rt, energy=1))
    assert m.stats.skips == 14 and m.stats.sets == 0
    assert m.probe("energy") == (0, False, "framework")


def test_a_raising_set_value_is_counted_not_propagated(rt_mf):
    m = M(rt_mf)
    errors0 = m.stats.errors
    G(rt_mf).NR_T.mf.raiseSet = True
    m.apply(classes(rt_mf, energy=1))
    assert m.stats.errors == errors0 + 7


# ------------------------------------------------------------------------------------------- the view drives it

def test_a_view_rebuild_calls_apply(rt_mf):
    nr = G(rt_mf).NutritionRevamp
    rt_mf.execute("NutritionRevamp.client.mirror = { acute_debtH = 13, nut_vitC_g = 4 }; NutritionRevamp.client.received = 1")
    assert nr.client.view.refresh(True) is True
    assert nr.client.view.stats.listenerErrors == 0
    assert M(rt_mf).levels.sleep == 3 and M(rt_mf).levels.deficiency == 3
    h = handle(rt_mf, "deficiency")
    assert h.value == 0.0 and h.getLevel(h) == 3


# ------------------------------------------------------------------------------------------- Plan 11c Task 7: Overfull

def test_overfull_is_created_thresholded_iconed_and_translated():
    rt = rt_env(mf=True, textures=True)
    boot(rt)
    create(rt)
    m = M(rt)
    assert m.classes[7] == "overfull" and len(m.classes) == 7
    h = handle(rt, "overfull")
    assert h is not None and rt.eval("rawequal")(m.handles.overfull, h)
    assert [h.th.bad1, h.th.bad2, h.th.bad3, h.th.bad4] == pytest.approx([0.4375, 0.3125, 0.1875, 0.0625])
    assert h.th.good1 == 100000
    for lvl in range(1, 5):
        assert h.pics["2:%d" % lvl].path == "media/ui/NutritionRevamp/overfull.png"
        assert h.titles["2:%d" % lvl] == "overfull lvl%d" % lvl
        assert h.descs["2:%d" % lvl] == "Class overfull %d" % lvl


def test_the_view_drives_overfull_from_the_mirrors_stomach_mass(rt_mf):
    nr = G(rt_mf).NutritionRevamp
    h = handle(rt_mf, "overfull")
    for n, (mass, lv) in enumerate(((700, 0), (800, 1), (900, 2), (1000, 3), (1100, 4), (600, 0))):
        rt_mf.execute("NutritionRevamp.client.mirror = { stomachFill = 1, stomachMass = %d }; "
                      "NutritionRevamp.client.received = %d" % (mass, n + 10))
        assert nr.client.view.refresh(False) is True
        assert nr.client.view.stats.listenerErrors == 0
        assert M(rt_mf).levels.overfull == lv
        assert h.getLevel(h) == lv and (h.addedToUIManager is True) == (lv > 0)
        assert M(rt_mf).probe("overfull") == (lv, lv > 0, "framework")


def test_overfull_goes_neutral_when_the_option_is_off(rt_mf):
    m = M(rt_mf)
    h = handle(rt_mf, "overfull")
    m.apply(classes(rt_mf, overfull=4))
    assert h.value == 0.0 and h.getLevel(h) == 4
    option(rt_mf, False)
    m.apply(classes(rt_mf, overfull=4))
    assert h.value == 0.5 and h.getLevel(h) == 0 and h.addedToUIManager is not True
    assert m.levels.overfull == 4


def test_overfull_on_the_own_column_draws_and_suspends_on_death():
    rt = rt_env()
    boot(rt)
    create(rt)
    m = M(rt)
    rt.execute("NutritionRevamp.client.mirror = { stomachMass = 1100 }; NutritionRevamp.client.received = 5")
    assert G(rt).NutritionRevamp.client.view.refresh(False) is True
    assert m.levels.overfull == 4
    m.column.render(m.column)
    assert m.lastDrawn == 1 and G(rt).NR_T.ui.rects == 1 + 4
    option(rt, False)
    m.apply(m.levels)
    assert m.column.onUI is False
    option(rt, True)
    m.apply(m.levels)
    fire(rt, "OnPlayerDeath", "NR_T.player")
    assert m.levels.overfull == 0
    m.column.render(m.column)
    assert m.lastDrawn == 0


def test_player_one_gets_no_overfull_moodle():
    rt = rt_env(mf=True)
    boot(rt)
    create(rt, 1)
    assert M(rt).handles.overfull is None and M(rt).stats.got == 0
