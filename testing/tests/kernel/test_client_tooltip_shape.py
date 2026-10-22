"""The food-tooltip band (Plan 7 Task 6, ruling 8): NR_Client_Tooltip.lua.

Each test loads a FRESH Lua 5.1 runtime: NR_Core.lua, the real kernel files the band calls (NR_Kernel.lua for
K.clamp, NR_Kernel_Vector.lua for K.vector.resolve, NR_Kernel_View.lua for K.view.tooltip), a stub NR.data, then
the client file, with Lua stand-ins for the engine: an ISToolTipInv class whose render counts, an
ISContextMenu.instance whose visibleCheck toggles, drawing methods on the panel that record, Food stand-ins with
IsFood, getFullType, getModData, the four macro getters, getBaseHunger, getHungChange and getFoodType, and a
local player whose inventory answers getFirstTypeRecurse. The kernel files load into this private runtime only;
the coverage gate counts the session host's runtime alone (conftest.py, test_zz_coverage.py), so it is untouched.
A stub proves the wrap's shape, its guards and the source chain's wiring, never the engine: whether the band
lands on screen is x183's (Task 11), which cannot hover.
"""
import os
import re

import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
CORE = os.path.join(LUA, "shared", "NR_Core.lua")
DIALS = os.path.join(LUA, "shared", "NR_Data_Dials.lua")  # the dial registry the kernels and the tooltip resolve from (Plan 19)
KERNELS = [os.path.join(LUA, "shared", n) for n in ("NR_Kernel.lua", "NR_Kernel_Vector.lua", "NR_Kernel_View.lua")]
TOOLTIP = os.path.join(LUA, "client", "NR_Client_Tooltip.lua")

ENV = r"""
NR_T = { renders = 0, draws = {}, heights = {} }
local Base = {}
Base.__index = Base
function Base.render(self)
    NR_T.renders = NR_T.renders + 1
    self.height = 120
end
ISToolTipInv = setmetatable({}, { __index = Base })
ISToolTipInv.render = Base.render
ISContextMenu = { instance = { visibleCheck = false } }
UIFont = { Small = "small" }
function NR_T.panel(item)
    local p = { item = item, height = 0, width = 200,
                backgroundColor = { r = 0, g = 0, b = 0, a = 0.5 }, borderColor = { r = 0.4, g = 0.4, b = 0.4, a = 1 },
                tooltip = { getLineSpacing = function(s) return 15 end } }
    function p.getHeight(s) return s.height end
    function p.getWidth(s) return s.width end
    function p.setHeight(s, h) s.height = h; NR_T.heights[#NR_T.heights + 1] = h end
    function p.drawRect(s, x, y, w, h, a, r, g, b) NR_T.draws[#NR_T.draws + 1] = { "rect", x, y, w, h, a } end
    function p.drawRectBorder(s, x, y, w, h, a, r, g, b) NR_T.draws[#NR_T.draws + 1] = { "border", x, y, w, h } end
    function p.drawText(s, str, x, y, r, g, b, a, font) NR_T.draws[#NR_T.draws + 1] = { "text", str, x, y, font } end
    return p
end
function NR_T.food(fullType, o)
    o = o or {}
    local it = { md = o.md or {} }
    it.IsFood = function(s) return o.notFood ~= true end
    it.getFullType = function(s) return fullType end
    it.getModData = function(s) return s.md end
    it.getCalories = function(s) return o.cal or 95 end
    it.getCarbohydrates = function(s) return o.carb or 25 end
    it.getLipids = function(s) return o.lip or 0.3 end
    it.getProteins = function(s) return o.pro or 0.5 end
    it.getBaseHunger = function(s) return o.base or -0.16 end
    it.getHungChange = function(s) return o.hung or -0.16 end
    it.getFoodType = function(s) return o.foodType end
    return it
end
NR_T.inv = { items = {} }
function NR_T.inv.getFirstTypeRecurse(s, t) return s.items[t] end
NR_T.player = { getInventory = function(s) return NR_T.inv end, isFemale = function(s) return NR_T.female == true end }
getPlayer = function() return NR_T.player end
"""

DATA = r"""
local NR = NutritionRevamp
NR.data = {
    dials = NR.data.dials,
    UNITS = { calories = "kcal", carbs = "g", lipids = "g", proteins = "g", vitC = "mg", fibre = "g" },
    records = { ORDER = { "vitC" }, REC = { vitC = { R = { 90, 75 }, unit = "mg" } } },
    infer = { _default = { n = 3, density = { vitC = 0.01 } } },
    nutrients = {},
}
function NR.data.nutrients.get(fullType)
    if fullType == "Base.Apple" then
        local v = {}
        for i = 1, #NR.kernel.vector.KEYS do v[NR.kernel.vector.KEYS[i]] = 0 end
        v.calories = 50
        v.carbs = 10
        v.vitC = 30
        return v
    end
    return nil
end
"""


def _src(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _load(rt, path):
    rt.eval("function(src, name) return assert(loadstring(src, name)) end")(_src(path), "@" + os.path.basename(path))()


def rt_with(view=False, engine=True):
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    if engine:
        rt.execute(ENV)
    _load(rt, CORE)
    _load(rt, DIALS)
    for k in KERNELS:
        _load(rt, k)
    rt.execute(DATA)
    if view:
        rt.execute("NutritionRevamp.client.view = { level = 3, listeners = {} }")
    _load(rt, TOOLTIP)
    return rt


def T(rt):
    return rt.globals().NutritionRevamp.client.tooltip


def render(rt, item_lua):
    """One render of a fresh panel over the item expression; returns the panel."""
    return rt.eval("function() local p = NR_T.panel(%s); ISToolTipInv.render(p); return p end" % item_lua)()


def draws(rt, kind=None):
    out = [list(d.values()) for d in rt.globals().NR_T.draws.values()]
    return [d for d in out if kind is None or d[0] == kind]


def L(rt, expr):
    """A Lua boolean expression evaluated in the runtime (identity of Lua tables and functions)."""
    return rt.eval(expr) is True


def seq(t):
    """The array part of a Lua table (the band's lines carry a width field beside it)."""
    return [t[i] for i in range(1, len(t) + 1)]


def code_only(src):
    src = re.sub(r"--\[(=*)\[.*?\]\1\]", "", src, flags=re.S)
    return "\n".join(line.split("--", 1)[0] for line in src.splitlines())


# ----------------------------------------------------------------------------------------------- the install

def test_loads_with_no_engine():
    rt = rt_with(engine=False)
    assert rt.globals().NR_ClientTooltip_Installed is None
    assert T(rt).stats.installs == 0
    assert T(rt).probe("Base.Apple") == (0, "none")


def test_the_wrap_installs_once_across_two_loads():
    rt = rt_with()
    assert L(rt, "NR_ClientTooltip_Installed.class == ISToolTipInv")
    assert L(rt, "ISToolTipInv.render == NR_ClientTooltip_Installed.wrapper")
    rt.execute("NR_T.s1 = NR_ClientTooltip_Installed")
    _load(rt, TOOLTIP)
    assert L(rt, "NR_ClientTooltip_Installed == NR_T.s1")
    assert L(rt, "ISToolTipInv.render == NR_T.s1.wrapper")
    assert T(rt).stats.installs == 0
    render(rt, "NR_T.food('Base.Apple')")
    assert rt.globals().NR_T.renders == 1


def test_a_recreated_class_is_wrapped_afresh():
    rt = rt_with()
    rt.execute("NR_T.old = NR_ClientTooltip_Installed.wrapper")
    rt.execute("ISToolTipInv = { render = function(self) NR_T.renders = NR_T.renders + 1; self.height = 80 end }")
    _load(rt, TOOLTIP)
    assert L(rt, "NR_ClientTooltip_Installed.class == ISToolTipInv")
    assert L(rt, "NR_ClientTooltip_Installed.wrapper ~= NR_T.old")
    assert L(rt, "ISToolTipInv.render == NR_ClientTooltip_Installed.wrapper")
    assert T(rt).stats.installs == 1
    render(rt, "NR_T.food('Base.Apple')")
    assert rt.globals().NR_T.renders == 1


def test_a_foreign_wrap_on_top_is_not_rewrapped():
    rt = rt_with()
    rt.execute("local w = ISToolTipInv.render; ISToolTipInv.render = function(self) NR_T.foreign = (NR_T.foreign or 0) + 1; w(self) end")
    _load(rt, TOOLTIP)
    render(rt, "NR_T.food('Base.Apple')")
    assert rt.globals().NR_T.renders == 1
    assert rt.globals().NR_T.foreign == 1


# ---------------------------------------------------------------------------------------------- the wrapper

def test_the_original_is_called_once_and_the_band_drawn_below_the_box():
    rt = rt_with(view=True)
    p = render(rt, "NR_T.food('Base.Apple')")
    assert rt.globals().NR_T.renders == 1
    rects = draws(rt, "rect")
    assert len(rects) == 1 and rects[0][2] == 120
    assert len(draws(rt, "border")) == 1
    texts = draws(rt, "text")
    n = len(texts)
    assert n >= 2
    assert texts[0][3] == 120 + 3 and texts[1][3] == 120 + 3 + 15
    assert texts[0][4] == "small"
    assert rects[0][4] == 15 * n + 6
    assert p.height == 120 + 15 * n + 6
    assert rects[0][5] == 0.5
    assert T(rt).stats.draws == 1 and T(rt).stats.lines == n


def test_no_band_for_a_non_food():
    rt = rt_with(view=True)
    render(rt, "NR_T.food('Base.Hammer', { notFood = true })")
    assert rt.globals().NR_T.renders == 1
    assert draws(rt) == []
    render(rt, "nil")
    assert rt.globals().NR_T.renders == 2
    assert draws(rt) == []


def test_no_band_when_the_option_is_off():
    rt = rt_with(view=True)
    rt.execute("NutritionRevamp.client.options = { tooltipLines = function() return false end }")
    render(rt, "NR_T.food('Base.Apple')")
    assert rt.globals().NR_T.renders == 1
    assert draws(rt) == []
    rt.execute("NutritionRevamp.client.options = { tooltipLines = function() error('boom') end }")
    render(rt, "NR_T.food('Base.Apple')")
    assert len(draws(rt, "rect")) == 1


def test_no_band_while_a_context_menu_is_flagged():
    rt = rt_with(view=True)
    rt.execute("ISContextMenu.instance.visibleCheck = true")
    render(rt, "NR_T.food('Base.Apple')")
    assert rt.globals().NR_T.renders == 1
    assert draws(rt) == []


def test_a_raising_linesFor_leaves_the_original_intact():
    rt = rt_with(view=True)
    rt.execute("NutritionRevamp.client.tooltip.linesFor = function() error('boom') end")
    render(rt, "NR_T.food('Base.Apple')")
    assert rt.globals().NR_T.renders == 1
    assert draws(rt) == []
    assert T(rt).stats.errors == 1
    assert "boom" in T(rt).lastError


def test_a_raising_draw_is_caught_after_the_original():
    rt = rt_with(view=True)
    p = rt.eval("function() local p = NR_T.panel(NR_T.food('Base.Apple')); p.drawRect = function() error('nodraw') end; ISToolTipInv.render(p); return p end")()
    assert rt.globals().NR_T.renders == 1
    assert T(rt).stats.errors == 1


def test_a_missing_tooltip_table_still_calls_the_original():
    rt = rt_with(view=True)
    rt.execute("NutritionRevamp.client.tooltip = nil")
    render(rt, "NR_T.food('Base.Apple')")
    assert rt.globals().NR_T.renders == 1
    assert draws(rt) == []


# ------------------------------------------------------------------------------------- the lines and sources

def test_sources_through_the_intake_chain():
    rt = rt_with(view=True)
    t = T(rt)
    assert rt.eval("function() NR_T.inv.items['TKX.DeclaredBar'] = NR_T.food('TKX.DeclaredBar', { md = { NR_Nutrients = 'vitC:40;fibre:3' } }) end")() is None
    assert t.probe("TKX.DeclaredBar") == (len(t.linesFor(rt.eval("NR_T.inv.items['TKX.DeclaredBar']"))), "declared")
    rt.execute("NR_T.inv.items['Base.Apple'] = NR_T.food('Base.Apple')")
    assert t.probe("Base.Apple")[1] == "table"
    rt.execute("NR_T.inv.items['Mod.Pie'] = NR_T.food('Mod.Pie', { foodType = 'Pie' })")
    assert t.probe("Mod.Pie")[1] == "inferred"
    rt.execute("NR_T.inv.items['Mod.Nil'] = NR_T.food('Mod.Nil', { cal = 0 })")
    assert t.probe("Mod.Nil") == (1, "missing")
    assert t.probe("Base.Nothing") == (0, "none")


def test_a_malformed_declaration_falls_through_to_the_table():
    rt = rt_with(view=True)
    rt.execute("NR_T.inv.items['Base.Apple'] = NR_T.food('Base.Apple', { md = { NR_Nutrients = 'vitC' } })")
    assert T(rt).probe("Base.Apple")[1] == "table"


def test_level_one_shows_the_source_line_alone():
    rt = rt_with()
    lines = T(rt).linesFor(rt.eval("NR_T.food('Base.Apple')"))
    assert seq(lines) == ["Per whole item (table)"]


def test_the_items_own_macros_are_written_over_the_tables_seed():
    rt = rt_with(view=True)
    lines = seq(T(rt).linesFor(rt.eval("NR_T.food('Base.Apple')")))
    assert "calories: 95.0 kcal" in lines
    assert "carbs: 25.0 g" in lines
    assert "vitC: 30.0 mg" in lines
    assert not any(l.startswith("calories: 50") for l in lines)


def test_a_half_eaten_item_shows_the_whole_item():
    rt = rt_with(view=True)
    lines = seq(T(rt).linesFor(rt.eval("NR_T.food('Base.Apple', { cal = 47.5, carb = 12.5, hung = -0.08 })")))
    assert "calories: 95.0 kcal" in lines
    assert "carbs: 25.0 g" in lines


def test_bands_level_shows_macros_and_a_rich_line():
    rt = rt_with()
    rt.execute("NutritionRevamp.client.view = { level = 2, listeners = {} }")
    lines = seq(T(rt).linesFor(rt.eval("NR_T.food('Base.Apple')")))
    assert lines[0] == "Per whole item (table)"
    assert "calories: 95.0 kcal" in lines
    assert "vitC: rich" in lines


def test_text_goes_through_the_client_text_function():
    rt = rt_with(view=True)
    rt.execute("NutritionRevamp.client.text = function(k, f) if k == 'UI_NR_Row_calories' then return 'Energy' end return f end")
    lines = seq(T(rt).linesFor(rt.eval("NR_T.food('Base.Apple')")))
    assert "Energy: 95.0 kcal" in lines


def test_the_requirement_map_follows_the_players_sex():
    rt = rt_with()
    rt.execute("NutritionRevamp.client.view = { level = 2, listeners = {}, female = true }")
    T(rt).linesFor(rt.eval("NR_T.food('Base.Apple')"))
    assert T(rt).R[2].vitC == 75
    assert T(rt).R[1] is None


def test_the_same_item_again_reads_only_its_hunger_left_and_its_calories():
    rt = rt_with(view=True)
    rt.execute("NR_T.reads = 0; NR_T.apple = NR_T.food('Base.Apple')")
    rt.execute("for _, n in ipairs({'IsFood', 'getFullType', 'getModData', 'getBaseHunger', 'getCarbohydrates'}) do"
               " local f = NR_T.apple[n]; NR_T.apple[n] = function(...) NR_T.reads = NR_T.reads + 1; return f(...) end end")
    rt.execute("NR_T.cals = 0; local f = NR_T.apple.getCalories"
               " NR_T.apple.getCalories = function(...) NR_T.cals = NR_T.cals + 1; return f(...) end")
    T(rt).linesFor(rt.eval("NR_T.apple"))
    first, cals = rt.eval("NR_T.reads"), rt.eval("NR_T.cals")
    assert first > 0
    for _ in range(3):
        T(rt).linesFor(rt.eval("NR_T.apple"))
    assert rt.eval("NR_T.reads") == first      # no other Java read on a hit
    assert rt.eval("NR_T.cals") == cals + 3    # the calorie check, once a hit (P12-14)


def test_a_calorie_change_with_the_hunger_unchanged_is_not_answered_from_the_last_item():
    rt = rt_with(view=True)
    rt.execute("NR_T.o = {}; NR_T.apple = NR_T.food('Base.Apple', NR_T.o)")
    same = rt.eval("function(a, b) return a == b end")
    a = T(rt).entryFor(rt.eval("NR_T.apple"))
    hits = T(rt).stats.cacheHits
    assert same(T(rt).entryFor(rt.eval("NR_T.apple")), a) and T(rt).stats.cacheHits == hits + 1
    rt.execute("NR_T.o.cal = 190")                 # the macros moved, the hunger left did not
    b = T(rt).entryFor(rt.eval("NR_T.apple"))
    assert T(rt).stats.cacheHits == hits + 1        # a miss: neither T.last nor the keyed cache answered
    assert not same(b, a)
    assert same(T(rt).entryFor(rt.eval("NR_T.apple")), b)   # and the new entry is the next hit's


# --------------------------------------------------------------------------------------------------- the cache

def test_the_cache_hits_and_the_listener_clears_it():
    rt = rt_with(view=True)
    t = T(rt)
    a = rt.eval("NR_T.food('Base.Apple')")
    b = rt.eval("NR_T.food('Base.Apple')")
    t.linesFor(a)
    t.linesFor(a)
    t.linesFor(b)
    assert t.stats.builds == 1
    assert t.stats.cacheHits == 2
    listeners = rt.globals().NutritionRevamp.client.view.listeners
    assert len(listeners) == 1
    listeners[1]()
    assert t.stats.invalidations == 1
    t.linesFor(a)
    assert t.stats.builds == 2


def test_a_level_change_takes_a_new_entry():
    rt = rt_with(view=True)
    t = T(rt)
    a = rt.eval("NR_T.food('Base.Apple')")
    n3 = len(t.linesFor(a))
    rt.execute("NutritionRevamp.client.view.level = 1")
    assert len(t.linesFor(a)) == 1
    assert n3 > 1
    assert t.stats.builds == 2


def test_the_listener_registers_lazily_and_once():
    rt = rt_with(view=False)
    rt.execute("NutritionRevamp.client.view = { level = 3, listeners = {} }")
    listeners = rt.globals().NutritionRevamp.client.view.listeners
    assert len(listeners) == 0
    a = rt.eval("NR_T.food('Base.Apple')")
    T(rt).linesFor(a)
    T(rt).linesFor(a)
    assert len(listeners) == 1
    _load(rt, TOOLTIP)
    T(rt).linesFor(a)
    assert len(listeners) == 1
    listeners[1]()
    assert T(rt).stats.invalidations == 1


def test_the_listener_registers_at_file_scope_when_the_view_exists():
    rt = rt_with(view=True)
    assert len(rt.globals().NutritionRevamp.client.view.listeners) == 1


def test_two_instances_of_one_type_with_other_macros_take_two_entries():
    rt = rt_with(view=True)
    t = T(rt)
    a = rt.eval("NR_T.food('Base.PotOfStew', { cal = 300, foodType = 'Stew' })")
    b = rt.eval("NR_T.food('Base.PotOfStew', { cal = 450, foodType = 'Stew' })")
    la = seq(t.linesFor(a))
    lb = seq(t.linesFor(b))
    assert "calories: 300 kcal" in la and "calories: 450 kcal" in lb
    assert t.stats.builds == 2
    n = 0
    for _ in t.cache.keys():
        n += 1
    assert n == 2


def test_the_same_item_hovered_twice_builds_once_and_hits_once():
    rt = rt_with(view=True)
    t = T(rt)
    a = rt.eval("NR_T.food('Base.PotOfStew', { cal = 300, foodType = 'Stew' })")
    t.linesFor(a)
    t.linesFor(a)
    assert t.stats.builds == 1
    assert t.stats.cacheHits == 1


def test_the_cache_key_form():
    rt = rt_with(view=True)
    k = rt.eval("function() return NutritionRevamp.client.tooltip.keyOf('Base.Apple', nil, 3, 1, { calories = 95, carbs = 25, lipids = 0.3, proteins = 0.5 }) end")()
    assert k == "Base.Apple|nil|3|1|95.000|25.000|0.300|0.500"


def test_a_zero_hung_change_reads_ratio_one():
    rt = rt_with(view=True)
    lines = seq(T(rt).linesFor(rt.eval("NR_T.food('Base.Apple', { hung = 0 })")))
    assert "calories: 95.0 kcal" in lines


def test_a_ratio_below_one_is_clamped_to_one():
    rt = rt_with(view=True)
    lines = seq(T(rt).linesFor(rt.eval("NR_T.food('Base.Apple', { base = -0.08, hung = -0.16 })")))
    assert "calories: 95.0 kcal" in lines
    assert T(rt).wholeScale(rt.eval("NR_T.food('Base.Apple', { base = -0.08, hung = -0.16 })")) == 1


# ------------------------------------------------------------------------------------------------ the source

def test_no_padBottom_write_and_no_server_reach():
    code = code_only(_src(TOOLTIP))
    assert "padBottom" not in code
    assert "sendClientCommand" not in code
    assert "getText(" not in code


def test_the_sentinel_is_a_global_of_its_own():
    code = code_only(_src(TOOLTIP))
    assert re.search(r"^\s*NR_ClientTooltip_Installed = \{ class = ISToolTipInv, original = original, wrapper = wrapper \}", code, re.M)
    assert "NutritionRevamp.client.tooltip.installed" not in code


# --- the close's D2: the band above the box at the screen's bottom edge and under anchorBottomLeft -------------

def render_at(rt, setup_lua):
    """One render of a fresh Apple panel after setup_lua runs on it (p in scope); returns the panel."""
    return rt.eval("function() local p = NR_T.panel(NR_T.food('Base.Apple')); %s; ISToolTipInv.render(p); return p end"
                   % setup_lua)()


def _assert_above(rt, p):
    rects = draws(rt, "rect")
    texts = draws(rt, "text")
    n = len(texts)
    band = 15 * n + 6
    assert len(rects) == 1 and rects[0][2] == -band and rects[0][4] == band
    assert draws(rt, "border")[0][2] == -band
    assert texts[0][3] == -band + 3 and texts[1][3] == -band + 3 + 15
    assert all(t[3] < 0 for t in texts)
    assert p.height == 120                       # no setHeight: the original's height stands
    assert list(rt.globals().NR_T.heights.values()) == []
    assert T(rt).stats.above == 1 and T(rt).stats.draws == 1


def test_a_box_near_the_screens_bottom_draws_the_band_above_it():
    rt = rt_with(view=True)
    rt.execute("getPlayerScreenHeight = function(n) NR_T.screenAsked = n; return 800 end")
    p = render_at(rt, "function p.getAbsoluteY(s) return 800 - 120 - 10 end")
    assert rt.globals().NR_T.screenAsked == 0
    _assert_above(rt, p)


def test_the_screen_height_defaults_to_720_when_unread():
    rt = rt_with(view=True)
    p = render_at(rt, "function p.getAbsoluteY(s) return 600 end")     # 600 + 120 + band > 720
    _assert_above(rt, p)
    rt2 = rt_with(view=True)
    rt2.execute("getPlayerScreenHeight = function() error('boom') end")
    p2 = render_at(rt2, "function p.getAbsoluteY(s) return 590 end")
    _assert_above(rt2, p2)


def test_anchor_bottom_left_draws_the_band_above_the_box():
    rt = rt_with(view=True)
    p = render_at(rt, "p.anchorBottomLeft = { x = 10, y = 500 }; function p.getAbsoluteY(s) return 100 end")
    _assert_above(rt, p)


def test_a_box_with_room_below_keeps_the_band_below():
    rt = rt_with(view=True)
    rt.execute("getPlayerScreenHeight = function() return 1080 end")
    p = render_at(rt, "function p.getAbsoluteY(s) return 600 end")
    rects = draws(rt, "rect")
    assert rects[0][2] == 120
    assert p.height > 120 and T(rt).stats.above == 0


# --- Plan 11 Task 18: the breaker and the re-entry guard ----------------------------------------------------------

def test_ten_consecutive_failures_open_the_breaker():
    rt = rt_with(view=True)
    rt.execute("NutritionRevamp.client.tooltip.linesFor = function() error('boom') end")
    for _ in range(12):
        render(rt, "NR_T.food('Base.Apple')")
    t = T(rt)
    assert t.broken is True and t.stats.errors == 10 and t.stats.breaks == 1
    assert rt.globals().NR_T.renders == 12                  # the original ran every frame


def test_a_success_resets_the_count():
    rt = rt_with(view=True)
    rt.execute("NR_T.fail = function() error('boom') end; NR_T.ok = function() return nil end")
    for i in range(30):
        rt.execute("NutritionRevamp.client.tooltip.linesFor = NR_T.%s" % ("ok" if i % 5 == 4 else "fail"))
        render(rt, "NR_T.food('Base.Apple')")
    t = T(rt)
    assert t.broken is not True and t.fails == 0 and t.stats.errors == 24


def test_a_reentrant_render_calls_the_saved_original():
    rt = rt_with(view=True)
    rt.execute("""NutritionRevamp.client.tooltip.linesFor = function(item)
        NR_ClientTooltip_Installed.wrapper(NR_T.panel(item))      -- a third mod's render calling back into the chain
        return nil
    end""")
    render(rt, "NR_T.food('Base.Apple')")
    assert T(rt).stats.reentries == 1
    assert rt.globals().NR_T.renders == 2                   # the inner call drew the original only, then the outer
    assert len(draws(rt, "rect")) == 0                      # and neither drew the band


def test_a_depth_left_by_a_raising_original_never_sticks_without_a_clock():
    rt = rt_with(view=True)
    rt.execute("getTimestampMs = nil")                       # T.now() reads 0: only a test host has no clock
    rt.execute("NutritionRevamp.client.tooltip.depth = 2; NutritionRevamp.client.tooltip.depthAt = 0")
    render(rt, "NR_T.food('Base.Apple')")                    # the depth an original that raised left behind
    t = T(rt)
    assert t.stats.reentries == 0 and t.stats.stale == 1 and t.depth == 0
    render(rt, "NR_T.food('Base.Apple')")
    assert T(rt).stats.reentries == 0 and rt.globals().NR_T.renders == 2


def test_with_a_clock_a_fresh_depth_is_a_reentry_and_an_old_one_is_stale():
    rt = rt_with(view=True)
    rt.execute("NR_T.ms = 5000; getTimestampMs = function() return NR_T.ms end")
    rt.execute("NutritionRevamp.client.tooltip.depth = 2; NutritionRevamp.client.tooltip.depthAt = 4500")
    render(rt, "NR_T.food('Base.Apple')")                    # 500 ms after the original began: inside it
    assert T(rt).stats.reentries == 1 and T(rt).depth == 2
    rt.execute("NutritionRevamp.client.tooltip.depthAt = 3000")
    render(rt, "NR_T.food('Base.Apple')")                    # 2000 ms: an original that raised; stale
    assert T(rt).stats.stale == 1 and T(rt).depth == 0


def test_a_clean_band_resets_the_count_after_a_raising_linesFor():
    rt = rt_with(view=True)
    rt.execute("""NR_T.n = 0
    NutritionRevamp.client.tooltip.linesFor = function()
        NR_T.n = NR_T.n + 1
        if NR_T.n % 2 == 1 then error('boom') end
        return { 'a line', width = 0 }
    end""")
    for _ in range(30):
        render(rt, "NR_T.food('Base.Apple')")
    t = T(rt)
    assert t.fails == 0 and t.broken is not True       # only T.after's success path resets: linesFor returned lines
    assert t.stats.errors == 15 and t.stats.draws == 15 and t.stats.breaks == 0


def test_a_real_reentry_from_inside_the_original_calls_the_saved_original_only():
    rt = rt_with(view=True)
    rt.execute("""NR_T.ms = 5000; getTimestampMs = function() return NR_T.ms end
    ISToolTipInv = { render = function(self)
        NR_T.renders = NR_T.renders + 1
        self.height = 120
        if not NR_T.inner then
            NR_T.inner = true
            ISToolTipInv.render(self)                          -- the original calls back into the wrapped chain
        end
    end }""")
    _load(rt, TOOLTIP)                                           # the recreated class is wrapped afresh
    render(rt, "NR_T.food('Base.Apple')")
    assert T(rt).stats.reentries == 1 and T(rt).stats.stale == 0
    assert rt.globals().NR_T.renders == 2                       # the inner call ran the saved original only
    assert len(draws(rt, "rect")) == 1                          # the outer draws the one band; the inner none
    assert T(rt).stats.draws == 1 and T(rt).depth == 0


# --- the fill line and vanilla's hunger line (Plan 15 Task 9 and its fix 1; decisions item 4) -----------------------

FILLS = r"""
NutritionRevamp.data.fills = {}
function NutritionRevamp.data.fills.get(ft)
    if ft == "Base.Apple" then return 1.23, 95 end
    if ft == "Base.Cabbage" then return 0.2, 95 end
    return nil
end
ItemTag = { HIDE_HUNGER_CHANGE = "hhc" }
NR_T.tags = {}
NR_T.log = {}
function NR_T.tagset(ft)
    local s = NR_T.tags[ft]
    if s ~= nil then return s end
    s = { set = {}, ft = ft }
    function s.contains(self, t) return self.set[t] == true end
    function s.add(self, t) self.set[t] = true; NR_T.log[#NR_T.log + 1] = "add " .. self.ft .. " " .. NR_T.renders; return true end
    function s.remove(self, t) self.set[t] = nil; NR_T.log[#NR_T.log + 1] = "remove " .. self.ft .. " " .. NR_T.renders; return true end
    NR_T.tags[ft] = s
    return s
end
NR_T.tagset("Base.Cabbage").set.hhc = true     -- vanilla's own tag (the canned vegetables carry it)
local food = NR_T.food
function NR_T.food(ft, o)
    local it = food(ft, o)
    it.getTags = function(s) return NR_T.tagset(ft) end
    return it
end
"""


def log(rt):
    return seq(rt.globals().NR_T.log)


def test_the_fill_line_leads_the_band_while_the_items_kcal_is_the_tables():
    rt = rt_with()
    rt.execute(FILLS)
    lines = T(rt).linesFor(rt.eval("NR_T.food('Base.Apple')"))
    assert seq(lines) == ["A whole one fills you for about 1 h, 95 kcal", "Per whole item (table)"] and lines.fill is True
    T(rt).invalidate()
    lines = T(rt).linesFor(rt.eval("NR_T.food('Base.Apple', { cal = 200 })"))   # another dish's macros: no fill line
    assert seq(lines) == ["Per whole item (table)"] and lines.fill is False
    T(rt).invalidate()
    lines = T(rt).linesFor(rt.eval("NR_T.food('Base.Apple', { cal = 104 })"))   # inside 10 % and 1 kcal
    assert seq(lines)[0] == "A whole one fills you for about 1 h, 104 kcal"
    assert T(rt).sameKcal(95, None) is False and T(rt).sameKcal(None, 95) is False


def test_the_hunger_line_is_hidden_around_the_one_draw_that_shows_the_fill_line():
    # fix 1 (review M1): the tag is added just before the original draws and taken off right after, only for an item
    # whose entry leads with the fill line; the set never keeps it past the draw
    rt = rt_with(view=True)
    rt.execute(FILLS)
    g = rt.globals().NR_T
    render(rt, "NR_T.food('Base.Apple')")
    assert log(rt) == ["add Base.Apple 0", "remove Base.Apple 1"] and g.tags["Base.Apple"].set.hhc is None
    render(rt, "NR_T.food('Base.Apple')")
    assert log(rt)[2:] == ["add Base.Apple 1", "remove Base.Apple 2"]
    assert T(rt).stats.hidden == 2 and T(rt).stats.shown == 2 and T(rt).pending is None
    render(rt, "NR_T.food('Base.Apple', { cal = 200 })")                  # kcal not the table's: vanilla's line shows
    render(rt, "NR_T.food('Base.Orange')")                                # no fill entry
    assert len(log(rt)) == 4
    rt.execute("NutritionRevamp.client.options = { tooltipLines = function() return false end }")
    render(rt, "NR_T.food('Base.Apple')")                                 # the band off: vanilla's line shows
    assert len(log(rt)) == 4


def test_vanillas_own_tag_is_never_touched_and_a_raising_draw_is_cleaned_at_the_next_render():
    rt = rt_with(view=True)
    rt.execute(FILLS)
    g = rt.globals().NR_T
    render(rt, "NR_T.food('Base.Cabbage')")                               # pre-tagged: no add, no remove
    assert log(rt) == [] and g.tags["Base.Cabbage"].set.hhc is True
    # an original that raises after the tag went on (the panel refuses its height): the next render's stale-depth reset
    # takes the tag off before it draws
    rt.execute("""NR_T.badPanel = function(item)
        local p = NR_T.panel(item)
        return setmetatable({}, { __index = p, __newindex = function(t, k, v)
            if k == "height" then error("draw boom") end
            rawset(p, k, v)
        end })
    end""")
    ok = rt.eval("function() local p = NR_T.badPanel(NR_T.food('Base.Apple')); return pcall(ISToolTipInv.render, p) end")()
    assert ok[0] is False if isinstance(ok, tuple) else ok is False
    assert g.tags["Base.Apple"].set.hhc is True and T(rt).pending is not None
    render(rt, "NR_T.food('Base.Orange')")                                # no clock: the depth is stale at once
    assert g.tags["Base.Apple"].set.hhc is None and T(rt).pending is None and T(rt).stats.stale == 1
    bare = rt_with(engine=False)
    assert T(bare).hide(None) is False and T(bare).pending is None
