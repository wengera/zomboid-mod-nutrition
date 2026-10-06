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
VIEW = os.path.join(LUA, "client", "NR_Client_View.lua")

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
function ISPanelJoypad:render()
    NR_T.baseRenders = (NR_T.baseRenders or 0) + 1
    if NR_T.baseRaises then error("base boom") end
end
function ISPanelJoypad:drawText(s, x, y) NR_T.ys[#NR_T.ys + 1] = y end
function ISPanelJoypad:drawTextRight(s, x, y) end
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

STATE = "NR_T = { created = 0, torn = 0, saved = 0, regs = {}, views = {}, panelRaises = false, draws = 0, refreshes = 0, ys = {} }"


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
        " lineHeight = function() return 14 end,"
        " draw = function(el, rows, x, y, w, font, maxY, minY) NR_T.draws = NR_T.draws + 1;"
        " NR_T.args = { rows[1], x, y, w, font, maxY, minY }; return y end }"
    )
    w = rt.eval("NR_T.newWindow()")
    w.createChildren(w)
    w.nrView.render(w.nrView)
    assert rt.eval("NR_T.baseRenders") == 1
    assert rt.eval("NR_T.refreshes") == 1 and rt.eval("NR_T.force") is False
    assert rt.eval("NR_T.draws") == 1
    assert rt.eval("NR_T.args[2]") == 8 and rt.eval("NR_T.args[3]") == 8
    assert rt.eval("NR_T.args[4]") == 284 and rt.eval("NR_T.args[5]") == "small"
    assert rt.eval("NR_T.args[6]") == 192 and rt.eval("NR_T.args[7]") == 8   # maxY the tab's height, minY the inset
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
    rt.execute("NutritionRevamp.client.view = { rows = {}, refresh = function() end, lineHeight = function() return 14 end,"
               " draw = function() error('x') end }")
    w = rt.eval("NR_T.newWindow()")
    w.createChildren(w)
    w.nrView.render(w.nrView)
    assert tab(rt).stats.errors == 1


def test_no_code_line_assigns_layout_current_but_nil():
    for line in _src(TAB).splitlines():
        code = line.split("--", 1)[0]
        if "layout.current" in code and "=" in code:
            assert code.strip().endswith("= nil"), code


# --- the close's D1: the rows clipped to the tab and scrolled by the wheel ---------------------------------

def rt_real_view(n_rows, height):
    """The real NR_Client_View.lua's draw over n_rows rows on a tab of the given height."""
    rt = rt_with()
    _load(rt, VIEW)
    rt.execute("NutritionRevamp.client.view.rows = {}")
    rt.execute("for i = 1, %d do NutritionRevamp.client.view.rows[i] = { label = 'L', labelText = 'L', valueText = 'v' } end"
               % n_rows)
    w = rt.eval("NR_T.newWindow()")
    w.createChildren(w)
    w.nrView.height = height
    return rt, w.nrView


def test_forty_rows_on_a_200px_tab_draw_within_its_bounds():
    rt, v = rt_real_view(40, 200)
    v.render(v)
    assert tab(rt).stats.errors == 0
    ys = [rt.eval("NR_T.ys[%d]" % i) for i in range(1, rt.eval("#NR_T.ys") + 1)]
    assert ys and len(ys) < 40
    assert min(ys) >= 8 and max(ys) + 14 <= 200


def test_the_wheel_scrolls_and_clamps_to_the_overflow():
    rt, v = rt_real_view(40, 200)
    over = 40 * 14 - (200 - 16)
    assert v.onMouseWheel(v, 1) is True
    assert v.scrollY == 3 * 14
    for _ in range(40):
        v.onMouseWheel(v, 1)
    assert v.scrollY == over
    rt.execute("NR_T.ys = {}")
    v.render(v)
    ys = [rt.eval("NR_T.ys[%d]" % i) for i in range(1, rt.eval("#NR_T.ys") + 1)]
    assert min(ys) >= 8 and max(ys) + 14 <= 200
    assert max(ys) == 8 - over + 39 * 14                  # the last row is on screen at the bottom of the scroll
    for _ in range(40):
        v.onMouseWheel(v, -1)
    assert v.scrollY == 0
    assert tab(rt).stats.errors == 0


def test_the_wheel_without_overflow_does_not_take_the_event():
    rt, v = rt_real_view(5, 200)
    assert v.onMouseWheel(v, 1) is False
    assert v.scrollY == 0


def test_a_raising_base_render_is_caught_by_the_renders_pcall():
    rt = rt_with()
    rt.execute("NR_T.baseRaises = true")
    w = rt.eval("NR_T.newWindow()")
    w.createChildren(w)
    w.nrView.render(w.nrView)
    assert tab(rt).stats.errors == 1
    assert "base boom" in tab(rt).lastError
