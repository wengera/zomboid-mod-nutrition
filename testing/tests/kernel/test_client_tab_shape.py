"""The character-info tab (Plan 7 Task 7): NR_Client_Tab.lua against Lua stand-ins for the vanilla window.

Each test loads NR_Core.lua then the file into a FRESH Lua 5.1 runtime, with stand-ins for ISCharacterInfoWindow
(three counting methods), ISPanelJoypad (derive/new/initialise/render/noBackground), a panel (addView counting,
getActiveView), ISLayoutManager.RegisterWindow counting and ISCollapsableWindow. A stand-in proves the wiring,
the guards and the sentinel, never the engine: that vanilla's RestoreLayout survives the saved layout is x183's.
"""
import os

import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
CORE = os.path.join(LUA, "shared", "NR_Core.lua")
TAB = os.path.join(LUA, "client", "NR_Client_Tab.lua")

CLASSES = r"""
ISCollapsableWindow = { tag = "collapsable" }
ISLayoutManager = { RegisterWindow = function(name, funcs, target)
    NR_T.order = (NR_T.order or "") .. "reg;"
    NR_T.regs[#NR_T.regs + 1] = { name = name, funcs = funcs, target = target }
end }
ISPanelJoypad = {}
ISPanelJoypad.__index = ISPanelJoypad
function ISPanelJoypad:derive(name)
    local c = { Type = name }
    c.__index = c
    setmetatable(c, self)
    return c
end
function ISPanelJoypad:new(x, y, w, h)
    return setmetatable({ x = x, y = y, width = w, height = h }, self)
end
function ISPanelJoypad:initialise() self.inited = true end
function ISPanelJoypad:noBackground() self.background = false; return self end
function ISPanelJoypad:render() NR_T.baseRenders = (NR_T.baseRenders or 0) + 1 end
UIFont = { Small = "small" }
"""

WINDOW = r"""
ISCharacterInfoWindow = {}
ISCharacterInfoWindow.__index = ISCharacterInfoWindow
function ISCharacterInfoWindow:createChildren()
    NR_T.created = NR_T.created + 1
    self.panel = { views = {}, active = nil }
    function self.panel:addView(name, view)
        if NR_T.panelRaises then error("addView boom") end
        self.views[#self.views + 1] = { name = name, view = view }
        view.parent = self
        NR_T.views[#NR_T.views + 1] = name
    end
    function self.panel:getActiveView() return self.active end
    return "made"
end
function ISCharacterInfoWindow:onTabTornOff(view, window)
    NR_T.torn = NR_T.torn + 1
    NR_T.order = (NR_T.order or "") .. "orig;"
end
function ISCharacterInfoWindow:SaveLayout(name, layout)
    NR_T.saved = NR_T.saved + 1
    layout.tabs = "info,skills"
    layout.current = "skills"
end
function NR_T.newWindow(n)
    return setmetatable({ playerNum = n or 0, width = 300, height = 200 }, ISCharacterInfoWindow)
end
"""

STATE = "NR_T = { created = 0, torn = 0, saved = 0, regs = {}, views = {}, panelRaises = false, draws = 0, refreshes = 0 }"


def _src(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _load(rt, path):
    rt.eval("function(src, name) return assert(loadstring(src, name)) end")(_src(path), "@" + os.path.basename(path))()


def rt_with(classes=True, window=True):
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(STATE)
    if classes:
        rt.execute(CLASSES)
    if window:
        rt.execute(WINDOW)
    _load(rt, CORE)
    _load(rt, TAB)
    return rt


def tab(rt):
    return rt.globals().NutritionRevamp.client.tab


def test_the_file_loads_with_every_stand_in_nil():
    rt = rt_with(classes=False, window=False)
    assert tab(rt).cls is None
    assert rt.globals().NR_ClientTab_Installed is None
    assert rt.globals().NR_Client_TabPanel is None


def test_the_file_loads_with_the_panel_class_but_no_window_class():
    rt = rt_with(window=False)
    assert tab(rt).cls is not None
    assert rt.globals().NR_ClientTab_Installed is None


def test_the_window_without_the_panel_class_counts_an_error_and_the_original_still_runs():
    rt = rt_with(classes=False)
    assert rt.eval("NR_T.newWindow():createChildren()") == "made"
    assert tab(rt).stats.errors == 1
    assert tab(rt).stats.added == 0
    assert rt.eval("NR_T.created") == 1


def test_one_wrap_across_two_loads_and_the_originals_run_once():
    rt = rt_with()
    rt.execute("NR_T.inst = NR_ClientTab_Installed")
    wrapper = rt.eval("ISCharacterInfoWindow.createChildren")
    _load(rt, CORE)
    _load(rt, TAB)
    assert rt.eval("NR_ClientTab_Installed == NR_T.inst") is True
    assert rt.eval("function(f) return ISCharacterInfoWindow.createChildren == f end")(wrapper) is True
    rt.execute("NR_T.newWindow():createChildren()")
    assert rt.eval("NR_T.created") == 1
    assert rt.eval("#NR_T.views") == 1
    assert tab(rt).stats.added == 1


def test_a_recreated_class_is_wrapped_again_once():
    rt = rt_with()
    rt.execute(WINDOW)       # the class table is re-created, unwrapped
    _load(rt, TAB)
    rt.execute("NR_T.newWindow():createChildren()")
    assert rt.eval("NR_T.created") == 1
    assert tab(rt).stats.added == 1


def test_create_children_adds_one_view_named_by_the_fallback_or_the_translation():
    rt = rt_with()
    w = rt.eval("NR_T.newWindow()")
    assert w.createChildren(w) == "made"
    assert rt.eval("NR_T.views[1]") == "Nutrition"
    assert rt.eval("function(w) return w.nrView.parent == w.panel end")(w) is True
    assert w.nrView.inited is True
    assert w.nrView.playerNum == 0
    assert w.nrView.y == 8 and w.nrView.height == 192
    rt2 = rt_with()
    rt2.execute("NutritionRevamp.client.text = function(k, f) return 'T:' .. k end")
    w2 = rt2.eval("NR_T.newWindow()")
    w2.createChildren(w2)
    assert rt2.eval("NR_T.views[1]") == "T:UI_NR_Tab"


def test_a_raising_addview_is_swallowed_and_counted():
    rt = rt_with()
    rt.execute("NR_T.panelRaises = true")
    w = rt.eval("NR_T.newWindow()")
    assert w.createChildren(w) == "made"
    assert tab(rt).stats.errors == 1
    assert tab(rt).stats.added == 0
    assert rt.eval("NR_T.created") == 1


def test_save_layout_with_the_tab_not_active_keeps_the_originals_current_and_appends_the_name():
    rt = rt_with()
    w = rt.eval("NR_T.newWindow()")
    w.createChildren(w)
    layout = rt.eval("{}")
    w.SaveLayout(w, "charinfowindow", layout)
    assert rt.eval("NR_T.saved") == 1
    assert layout.tabs == "info,skills,NutritionRevamp"
    assert layout.current == "skills"
    assert tab(rt).stats.saves == 1


def test_save_layout_with_the_tab_active_nils_current_and_never_writes_the_mods_name():
    rt = rt_with()
    w = rt.eval("NR_T.newWindow()")
    w.createChildren(w)
    w.panel.active = w.nrView
    layout = rt.eval("{}")
    w.SaveLayout(w, "charinfowindow", layout)
    assert rt.eval("NR_T.saved") == 1
    assert layout.current is None
    assert layout.tabs == "info,skills,NutritionRevamp"


def test_save_layout_with_the_tab_not_in_the_panel_appends_nothing():
    rt = rt_with()
    w = rt.eval("NR_T.newWindow()")
    layout = rt.eval("{}")
    w.SaveLayout(w, "charinfowindow", layout)
    assert layout.tabs == "info,skills"
    assert tab(rt).stats.saves == 0
    w.createChildren(w)
    w.nrView.parent = None
    layout2 = rt.eval("{}")
    w.SaveLayout(w, "charinfowindow", layout2)
    assert layout2.tabs == "info,skills"


def test_ontabtornoff_registers_only_player_zero_and_only_the_mod_view():
    rt = rt_with()
    w0 = rt.eval("NR_T.newWindow(0)")
    w0.createChildren(w0)
    w0.onTabTornOff(w0, rt.eval("{}"), rt.eval("{ id = 'w' }"))
    assert rt.eval("#NR_T.regs") == 0
    assert rt.eval("NR_T.torn") == 1
    win = rt.eval("{ id = 'floating' }")
    w0.onTabTornOff(w0, w0.nrView, win)
    assert rt.eval("#NR_T.regs") == 1
    assert rt.eval("NR_T.regs[1].name") == "charinfowindow.NutritionRevamp"
    assert rt.eval("NR_T.regs[1].funcs == ISCollapsableWindow") is True
    assert rt.eval("NR_T.torn") == 2
    assert tab(rt).stats.tornOff == 1
    w1 = rt.eval("NR_T.newWindow(1)")
    w1.createChildren(w1)
    w1.onTabTornOff(w1, w1.nrView, win)
    assert rt.eval("#NR_T.regs") == 1
    assert rt.eval("NR_T.torn") == 3


def test_ontabtornoff_registers_before_the_original_runs():
    rt = rt_with()
    w = rt.eval("NR_T.newWindow(0)")
    w.createChildren(w)
    w.onTabTornOff(w, w.nrView, rt.eval("{}"))
    assert rt.eval("NR_T.order") == "reg;orig;"


def test_the_tab_render_calls_the_base_then_the_views_refresh_and_draw():
    rt = rt_with()
    rt.execute(
        "NutritionRevamp.client.view = {"
        " rows = { 'r' },"
        " refresh = function(force) NR_T.refreshes = NR_T.refreshes + 1; NR_T.force = force end,"
        " draw = function(el, rows, x, y, w, font) NR_T.draws = NR_T.draws + 1;"
        " NR_T.args = { rows[1], x, y, w, font }; return y end }"
    )
    w = rt.eval("NR_T.newWindow()")
    w.createChildren(w)
    w.nrView.render(w.nrView)
    assert rt.eval("NR_T.baseRenders") == 1
    assert rt.eval("NR_T.refreshes") == 1 and rt.eval("NR_T.force") is False
    assert rt.eval("NR_T.draws") == 1
    assert rt.eval("NR_T.args[2]") == 8 and rt.eval("NR_T.args[3]") == 8
    assert rt.eval("NR_T.args[4]") == 284 and rt.eval("NR_T.args[5]") == "small"
    assert tab(rt).stats.renders == 1


def test_the_tab_render_with_no_view_draws_nothing_and_counts():
    rt = rt_with()
    w = rt.eval("NR_T.newWindow()")
    w.createChildren(w)
    w.nrView.render(w.nrView)
    assert rt.eval("NR_T.baseRenders") == 1
    assert tab(rt).stats.noView == 1
    assert tab(rt).stats.errors == 0


def test_a_raising_draw_is_swallowed():
    rt = rt_with()
    rt.execute("NutritionRevamp.client.view = { rows = {}, refresh = function() end, draw = function() error('x') end }")
    w = rt.eval("NR_T.newWindow()")
    w.createChildren(w)
    w.nrView.render(w.nrView)
    assert tab(rt).stats.errors == 1


def test_no_code_line_assigns_layout_current_but_nil():
    for line in _src(TAB).splitlines():
        code = line.split("--", 1)[0]
        if "layout.current" in code and "=" in code:
            assert code.strip().endswith("= nil"), code
