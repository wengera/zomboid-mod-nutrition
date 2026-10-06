"""The options page and the view cache (Plan 7 Task 5): NR_Client_ModOptions.lua and NR_Client_View.lua.

The pattern of test_client_effects_shape.py: a FRESH Lua 5.1 runtime per test, Lua stand-ins for the engine that
count (Events whose Add records each listener, PZAPI.ModOptions whose create returns a page with addKeyBind and
addTickBox handles carrying getValue, Keyboard, CharacterTrait, SandboxVars, getText answering the key itself on a
miss, getTextManager, getPlayer with a hasTrait that compares the enum object by identity, sendClientCommand
counting). NR_Core.lua loads first, then the kernel files and the records (K.view is real, so the rows are the
kernel's), then the client files in the engine's path order (#1055). The kernel files load in a runtime of their
own here, so the session host's coverage gate is untouched. A stub proves the wiring, the guards and the cadence,
never the engine: whether the page loads ModOptions.ini this early and what the layout restore does are x183's.
"""
import glob
import os

import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
SHARED = os.path.join(LUA, "shared")
CLIENT = os.path.join(LUA, "client")
CORE = os.path.join(SHARED, "NR_Core.lua")
RECORDS = os.path.join(SHARED, "NR_Data_Records.lua")
MIRROR = os.path.join(CLIENT, "NR_Client_Mirror.lua")
MODOPTIONS = os.path.join(CLIENT, "NR_Client_ModOptions.lua")
OPTIONS = os.path.join(CLIENT, "NR_Client_Options.lua")
VIEW = os.path.join(CLIENT, "NR_Client_View.lua")

ENV = r"""
NR_T = { adds = {}, sends = 0, creates = 0, texts = {}, held = nil, hasTraitRaises = false, printed = 0 }
print = function() NR_T.printed = NR_T.printed + 1 end
local function event(name)
    NR_T.adds[name] = {}
    return { Add = function(fn) local l = NR_T.adds[name]; l[#l + 1] = fn end }
end
Events = {
    OnServerCommand = event("OnServerCommand"),
    OnGameStart = event("OnGameStart"),
    OnCreatePlayer = event("OnCreatePlayer"),
    OnKeyPressed = event("OnKeyPressed"),
}
isClient = function() return NR_T.client ~= false end
isServer = function() return false end
NR_T.player = {
    hasTrait = function(self, enum)
        if NR_T.hasTraitRaises then error("boom") end
        return enum == NR_T.held
    end,
}
getPlayer = function() return NR_T.player end
sendClientCommand = function(p, module, command, args) NR_T.sends = NR_T.sends + 1 end
getText = function(k)
    if NR_T.textRaises then error("boom") end
    return NR_T.texts[k] or k
end
getTextManager = function() return { getFontHeight = function(self, f) return 15 end } end
UIFont = { Small = "small" }
Keyboard = { KEY_K = 37 }
CharacterTrait = { NUTRITIONIST = { id = "n1" }, NUTRITIONIST2 = { id = "n2" } }
SandboxVars = { NR = { VisibilityMode = 1 } }
PZAPI = { ModOptions = { loads = 0, pages = {} } }
function PZAPI.ModOptions:create(id, name)
    NR_T.creates = NR_T.creates + 1
    local page = { id = id, name = name, dict = {} }
    function page:addKeyBind(oid, label, key, tip)
        local h = { key = key, label = label, getValue = function(s) return s.key end }
        self.dict[oid] = h
        return h
    end
    function page:addTickBox(oid, label, value, tip)
        local h = { value = value, label = label, getValue = function(s) return s.value end }
        self.dict[oid] = h
        return h
    end
    self.pages[#self.pages + 1] = page
    return page
end
function PZAPI.ModOptions:load()
    self.loads = self.loads + 1
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


def _clients(rt):
    for path in (MIRROR, MODOPTIONS, OPTIONS, VIEW):  # the engine's path order (#1055)
        _load(rt, path)


def rt_env():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(ENV)
    _kernel(rt)
    _clients(rt)
    return rt


def G(rt):
    return rt.globals()


def NRC(rt):
    return G(rt).NutritionRevamp.client


def V(rt):
    return NRC(rt).view


def fire(rt, event, args=""):
    rt.execute("for _, f in ipairs(NR_T.adds.%s) do f(%s) end" % (event, args))


def receive(rt, mirror_lua):
    fire(rt, "OnServerCommand", "'NutritionRevamp', 'mirror', %s" % mirror_lua)


# ------------------------------------------------------------------------------------------- loading

def test_the_files_load_with_no_engine():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    _kernel(rt)
    _clients(rt)
    g = G(rt)
    assert g.NR_ClientModOptions_Page is None
    assert NRC(rt).modOptions.loadOnce() is False
    assert NRC(rt).modOptions.key() == 37
    assert NRC(rt).modOptions.tooltipLines() is True and NRC(rt).modOptions.moodles() is True
    assert NRC(rt).text("UI_NR_PanelTitle", "Nutrition") == "Nutrition"
    assert V(rt).readTrait(None) is False
    assert V(rt).readOption() == 1
    assert V(rt).lineHeight("small") == 14
    assert V(rt).refresh(False) is True       # an empty mirror still builds the six class rows
    assert len(V(rt).rows) == 6


def test_the_files_load_with_the_stand_ins_and_the_page_has_three_rows():
    rt = rt_env()
    g = G(rt)
    page = g.NR_ClientModOptions_Page
    assert page is not None and page.id == "NutritionRevamp"
    assert g.NR_T.creates == 1
    assert page.dict.togglePanel.key == 37
    assert page.dict.tooltipLines.value is True and page.dict.moodles.value is True


def test_a_reload_creates_no_second_page_and_adds_no_second_listener():
    rt = rt_env()
    _load(rt, CORE)
    _kernel(rt)
    _clients(rt)
    g = G(rt)
    assert g.NR_T.creates == 1
    count = rt.eval("""function(event, fn)
        local n = 0
        for _, f in ipairs(NR_T.adds[event]) do if f == fn then n = n + 1 end end
        return n, #NR_T.adds[event]
    end""")
    # the mirror and options files add their own OnGameStart listeners per load; this file's is one across loads
    assert count("OnGameStart", g.NR_ClientModOptions_Installed.fn)[0] == 1
    assert count("OnCreatePlayer", g.NR_ClientView_Installed.create) == (1, 1)

# ------------------------------------------------------------------------------------------- the options page

def test_the_accessors_survive_the_options_file_and_are_reattached_at_game_start():
    rt = rt_env()
    o = NRC(rt).options
    assert o.mode == 1                       # NR_Client_Options.lua assigned its own table after this file
    fire(rt, "OnGameStart")
    o = NRC(rt).options
    assert o.key() == 37 and o.tooltipLines() is True and o.moodles() is True
    assert o.mode == 1 and o.toggleKey is not None


def test_the_accessors_read_the_values():
    rt = rt_env()
    fire(rt, "OnGameStart")
    page = G(rt).NR_ClientModOptions_Page
    page.dict.togglePanel.key = 49
    page.dict.tooltipLines.value = False
    page.dict.moodles.value = False
    o = NRC(rt).options
    assert o.key() == 49 and o.tooltipLines() is False and o.moodles() is False


def test_the_accessors_fall_back_when_getValue_raises_or_answers_junk():
    rt = rt_env()
    fire(rt, "OnGameStart")
    rt.execute("""
        local d = NR_ClientModOptions_Page.dict
        d.togglePanel.getValue = function() error('boom') end
        d.tooltipLines.value = 'yes'
        d.moodles = nil
    """)
    o = NRC(rt).options
    assert o.key() == 37 and o.tooltipLines() is True and o.moodles() is True


def test_loadOnce_loads_once_across_two_calls_and_game_start():
    rt = rt_env()
    fire(rt, "OnGameStart")
    assert G(rt).PZAPI.ModOptions.loads == 1
    assert NRC(rt).options.loadOnce() is False
    fire(rt, "OnGameStart")
    assert G(rt).PZAPI.ModOptions.loads == 1
    assert NRC(rt).modOptions.stats.loads == 1


def test_a_raising_load_is_caught_and_counted():
    rt = rt_env()
    rt.execute("function PZAPI.ModOptions:load() error('no file') end")
    fire(rt, "OnGameStart")                  # must not raise into the event
    assert NRC(rt).modOptions.stats.loadFailures == 1


def test_text_returns_the_fallback_on_a_miss_and_the_string_on_a_hit():
    rt = rt_env()
    t = NRC(rt).text
    assert t("UI_NR_PanelTitle", "Nutrition") == "Nutrition"          # getText answers the key: a miss
    G(rt).NR_T.texts["UI_NR_PanelTitle"] = "Nutrition panel"
    assert t("UI_NR_PanelTitle", "Nutrition") == "Nutrition panel"
    assert t("UI_NR_Class_energy_2", None) == "Class energy 2"         # no fallback: the key's tail
    assert t("UI_NR_Row_vitC_p", "UI_NR_Row_vitC_p") == "vitC p"       # the key as its own fallback: the tail
    G(rt).NR_T.textRaises = True
    assert t("UI_NR_PanelTitle", "Nutrition") == "Nutrition"
    G(rt).getText = None
    assert t("UI_NR_PanelTitle", "Nutrition") == "Nutrition"


# ------------------------------------------------------------------------------------------- the trait and the level

def test_readTrait_false_when_the_enum_is_nil():
    rt = rt_env()
    G(rt).CharacterTrait = None
    assert V(rt).readTrait(G(rt).NR_T.player) is False
    rt.execute("CharacterTrait = {}")
    assert V(rt).readTrait(G(rt).NR_T.player) is False


def test_readTrait_compares_the_enum_object_by_identity():
    rt = rt_env()
    p = G(rt).NR_T.player
    assert V(rt).readTrait(p) is False
    rt.execute("NR_T.held = { id = 'n1' }")                 # an equal-looking table, not the registry object
    assert V(rt).readTrait(p) is False
    rt.execute("NR_T.held = CharacterTrait.NUTRITIONIST2")
    assert V(rt).readTrait(p) is True
    G(rt).NR_T.hasTraitRaises = True
    assert V(rt).readTrait(p) is False
    assert V(rt).stats.traitReads == 4


def test_the_option_level_is_read_at_create_player_and_a_non_number_reads_1():
    rt = rt_env()
    G(rt).SandboxVars.NR.VisibilityMode = 2
    fire(rt, "OnCreatePlayer", "0, NR_T.player")
    assert V(rt).optionLevel == 2 and V(rt).level == 2
    rt.execute("SandboxVars.NR.VisibilityMode = 'x'")
    fire(rt, "OnCreatePlayer", "0, NR_T.player")
    assert V(rt).optionLevel == 1 and V(rt).level == 1
    rt.execute("SandboxVars = nil")
    fire(rt, "OnCreatePlayer", "0, NR_T.player")
    assert V(rt).level == 1


def test_the_trait_grants_level_3_on_the_next_mirror():
    rt = rt_env()
    receive(rt, "{ nut_vitC_g = 2 }")
    assert V(rt).level == 1
    n = V(rt).stats.rebuilds
    rt.execute("NR_T.held = CharacterTrait.NUTRITIONIST")
    receive(rt, "{ nut_vitC_g = 2 }")
    assert V(rt).hasTrait is True and V(rt).level == 3
    assert V(rt).stats.rebuilds == n + 1
    keys = [V(rt).rows[i].key for i in range(1, len(V(rt).rows) + 1)]
    assert "nut_vitC_p" in keys and "acute_caf" in keys


# ------------------------------------------------------------------------------------------- the cache

def test_refresh_rebuilds_only_when_received_or_level_moved():
    rt = rt_env()
    v = V(rt)
    assert v.refresh(False) is True
    assert v.refresh(False) is False          # two refreshes, one rebuild
    assert v.stats.rebuilds == 1
    receive(rt, "{ fluids_dehydPct = 3 }")    # the mirror handler calls onMirror, which refreshes
    assert v.stats.rebuilds == 2
    assert v.refresh(False) is False
    v.level = 2                                 # a level move alone
    assert v.refresh(False) is True and v.stats.rebuilds == 3
    assert v.refresh(True) is True and v.stats.rebuilds == 4


def test_the_mirror_handler_calls_onMirror_once_per_arrival():
    rt = rt_env()
    receive(rt, "{ fluids_dehydPct = 5 }")
    v = V(rt)
    assert v.stats.rebuilds == 1 and v.lastReceived == 1
    assert v.classes.hydration == 3
    receive(rt, "{ fluids_dehydPct = 0 }")
    assert v.stats.rebuilds == 2 and v.classes.hydration == 0


def test_the_grade_rows_use_the_graded_order_never_the_raw_order():
    rt = rt_env()
    K = G(rt).NutritionRevamp.kernel
    v = V(rt)
    v.refresh(True)
    graded = K.view.gradedOrder(G(rt).NutritionRevamp.data.records)
    assert list(v.order.values()) == list(graded.values())
    raw = G(rt).NutritionRevamp.data.records.ORDER
    assert len(v.order) < len(raw)


def test_the_listeners_are_called_after_each_rebuild_and_a_raising_one_is_caught():
    rt = rt_env()
    rt.execute("""
        NR_T.heard = 0
        local L = NutritionRevamp.client.view.listeners
        L[#L + 1] = function(classes, rows, level) NR_T.heard = NR_T.heard + 1; NR_T.lastHyd = classes.hydration end
        L[#L + 1] = function() error('listener boom') end
    """)
    receive(rt, "{ fluids_dehydPct = 7 }")
    assert G(rt).NR_T.heard == 1 and G(rt).NR_T.lastHyd == 4
    assert V(rt).stats.listenerErrors == 1
    V(rt).refresh(False)
    assert G(rt).NR_T.heard == 1


def test_a_listeners_array_made_before_this_file_loads_is_carried_over():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(ENV)
    _kernel(rt)
    rt.execute("""
        NR_T.heard = 0
        NutritionRevamp.client.view = { listeners = { function() NR_T.heard = NR_T.heard + 1 end } }
    """)
    _clients(rt)
    V(rt).refresh(False)
    assert G(rt).NR_T.heard == 1


def test_a_failing_rebuild_is_caught_and_stamped():
    rt = rt_env()
    rt.execute("NutritionRevamp.kernel.view.rows = function() error('rows boom') end")
    assert V(rt).refresh(False) is False
    assert V(rt).stats.errors == 1
    assert V(rt).refresh(False) is False and V(rt).stats.errors == 1   # stamped: no retry per frame


# ------------------------------------------------------------------------------------------- the draw helper

DRAW_EL = r"""
NR_T.left, NR_T.right = {}, {}
NR_T.el = {
    drawText = function(self, s, x, y, r, g, b, a, f) NR_T.left[#NR_T.left + 1] = { s = s, x = x, y = y, f = f } end,
    drawTextRight = function(self, s, x, y, r, g, b, a, f) NR_T.right[#NR_T.right + 1] = { s = s, x = x, y = y } end,
}
"""


def test_draw_paints_each_rows_resolved_label_and_text_and_returns_the_next_y():
    rt = rt_env()
    rt.execute(DRAW_EL)
    G(rt).NR_T.texts["UI_NR_Class_energy"] = "Energy"
    G(rt).NR_T.texts["UI_NR_Class_energy_0"] = "fine"
    v = V(rt)
    v.refresh(True)
    y = v.draw(G(rt).NR_T.el, v.rows, 8, 20, 264, None)
    g = G(rt).NR_T
    assert len(g.left) == 6 and len(g.right) == 6
    assert g.left[1].s == "Energy" and g.right[1].s == "fine"
    assert g.right[1].x == 272 and g.left[2].y == 35
    assert g.left[1].f == "small"
    assert g.left[2].s == "hydration"                  # a label miss falls back to the row key
    assert g.right[2].s == "Class hydration 0"         # a text-key miss falls back to the key's tail
    assert y == 20 + 6 * 15


def test_draw_resolves_no_text_per_frame():
    rt = rt_env()
    rt.execute(DRAW_EL)
    v = V(rt)
    v.refresh(True)
    rt.execute("NR_T.gets = 0; local g = getText; getText = function(k) NR_T.gets = NR_T.gets + 1; return g(k) end")
    v.draw(G(rt).NR_T.el, v.rows, 8, 20, 264, None)
    assert G(rt).NR_T.gets == 0


def test_draw_stops_before_maxY_and_counts_the_clip():
    rt = rt_env()
    rt.execute(DRAW_EL)
    v = V(rt)
    v.refresh(True)
    y = v.draw(G(rt).NR_T.el, v.rows, 8, 0, 264, "small", 50)
    assert len(G(rt).NR_T.left) == 3 and y == 45
    assert v.stats.clipped == 1


def test_draw_is_nil_safe():
    rt = rt_env()
    v = V(rt)
    assert v.draw(None, None, 0, 7, 10, None) == 7
    assert v.draw(rt.eval("{}"), rt.eval("{}"), 0, 7, 10, None) == 7
