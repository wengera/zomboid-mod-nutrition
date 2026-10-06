"""The collapsible panel (Plan 7 Task 5, ruling 6): NR_Client_Panel.lua on the view cache and the options page.

The pattern of test_client_effects_shape.py: a FRESH Lua 5.1 runtime per test, Lua stand-ins that count -- an
ISCollapsableWindow with derive/new and the ISUIElement members the panel calls (initialise, prerender, render,
titleBarHeight, setVisible, getIsVisible, addToUIManager, removeFromUIManager, bringToTop, setRenderThisPlayerOnly,
setResizable, getWidth, getHeight, getY, setHeight, drawText, drawTextRight; visible by default, as an element is), an
ISLayoutManager.RegisterWindow that counts and can play the restore's re-add (DefaultRestoreWindow's
addToUIManager + setVisible(true)), Events, Keyboard, PZAPI.ModOptions, getText, sendClientCommand counting. The
kernel loads in this runtime of its own, so the session host's coverage gate is untouched. A stub proves the
wiring, the guards and the cadence, never the engine: what the layout restore and the UI manager do live is x183's
(the research's risks 1-3).
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
PANEL = os.path.join(CLIENT, "NR_Client_Panel.lua")
VIEW = os.path.join(CLIENT, "NR_Client_View.lua")

ENV = r"""
NR_T = { adds = {}, sends = 0, regs = 0, regNames = {}, printed = 0 }
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
NR_T.player = { hasTrait = function(self, enum) return false end }
getPlayer = function() return NR_T.player end
sendClientCommand = function(p, module, command, args)
    NR_T.sends = NR_T.sends + 1
    NR_T.lastCommand = command
end
getText = function(k) return k end
getTextManager = function() return { getFontHeight = function(self, f) return 15 end } end
UIFont = { Small = "small" }
Keyboard = { KEY_K = 37, KEY_SEMICOLON = 39 }
CharacterTrait = { NUTRITIONIST = { id = "n1" }, NUTRITIONIST2 = { id = "n2" } }
SandboxVars = { NR = { VisibilityMode = 1 } }
PZAPI = { ModOptions = { loads = 0 } }
function PZAPI.ModOptions:create(id, name)
    local page = { id = id, dict = {} }
    function page:addKeyBind(oid, label, key, tip)
        local h = { key = key, getValue = function(s) return s.key end }
        self.dict[oid] = h
        return h
    end
    function page:addTickBox(oid, label, value, tip)
        local h = { value = value, getValue = function(s) return s.value end }
        self.dict[oid] = h
        return h
    end
    return page
end
function PZAPI.ModOptions:load() self.loads = self.loads + 1 end

NR_T.ui = { prerenders = 0, renders = 0, draws = 0, rights = 0 }
ISCollapsableWindow = {}
function ISCollapsableWindow:derive(name)
    local c = {}
    setmetatable(c, self)
    self.__index = self
    c.Type = name
    return c
end
function ISCollapsableWindow:new(x, y, w, h)
    local o = { x = x, y = y, width = w, height = h, visible = true, onUI = false, isCollapsed = false, resizable = true }
    setmetatable(o, self)
    self.__index = self
    return o
end
function ISCollapsableWindow:initialise() self.initialised = true end
function ISCollapsableWindow:prerender() NR_T.ui.prerenders = NR_T.ui.prerenders + 1 end
function ISCollapsableWindow:render() NR_T.ui.renders = NR_T.ui.renders + 1 end
function ISCollapsableWindow:titleBarHeight() return 16 end
function ISCollapsableWindow:setVisible(v) self.visible = v end
function ISCollapsableWindow:getIsVisible() return self.visible end
function ISCollapsableWindow:addToUIManager() self.onUI = true end
function ISCollapsableWindow:removeFromUIManager() self.onUI = false end
function ISCollapsableWindow:bringToTop() self.onTop = true end
function ISCollapsableWindow:setRenderThisPlayerOnly(n) self.renderPlayer = n end
function ISCollapsableWindow:setResizable(r) self.resizable = r end
function ISCollapsableWindow:getWidth() return self.width end
function ISCollapsableWindow:getHeight() return self.height end
function ISCollapsableWindow:getY() return self.y end
function ISCollapsableWindow:setHeight(h) self.height = h end
function ISCollapsableWindow:drawText(s, x, y, r, g, b, a, f) NR_T.ui.draws = NR_T.ui.draws + 1 end
function ISCollapsableWindow:drawTextRight(s, x, y, r, g, b, a, f) NR_T.ui.rights = NR_T.ui.rights + 1 end
ISLayoutManager = {
    RegisterWindow = function(name, funcs, target)
        NR_T.regs = NR_T.regs + 1
        NR_T.regNames[#NR_T.regNames + 1] = name
        NR_T.regFuncs = funcs
        if NR_T.restoreVisible then
            target:addToUIManager()
            target:setVisible(true)
        end
    end,
}
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
    for path in (MIRROR, MODOPTIONS, OPTIONS, PANEL, VIEW):  # the engine's path order (#1055)
        _load(rt, path)


def rt_env(restore_visible=False):
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(ENV)
    G(rt).NR_T.restoreVisible = restore_visible
    _kernel(rt)
    _clients(rt)
    fire(rt, "OnGameStart")
    return rt


def G(rt):
    return rt.globals()


def P(rt):
    return G(rt).NutritionRevamp.client.panel


def fire(rt, event, args=""):
    rt.execute("for _, f in ipairs(NR_T.adds.%s) do f(%s) end" % (event, args))


def create(rt, n=0):
    fire(rt, "OnCreatePlayer", "%d, NR_T.player" % n)


def key(rt, code):
    fire(rt, "OnKeyPressed", str(code))


def inst(rt, n=0):
    return P(rt).instances[n]


def same(rt, a, b):
    """Lua identity (two lupa wrappers of one table never compare equal in Python)."""
    return rt.eval("rawequal")(a, b)


# ------------------------------------------------------------------------------------------- loading

def test_the_file_loads_with_no_engine():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    _kernel(rt)
    _clients(rt)
    assert P(rt).cls is None
    assert G(rt).NR_Client_Panel is None
    assert P(rt).toggle(0) is False
    P(rt).onCreatePlayer(0, None)            # no class, no side: nothing built
    P(rt).onKey(39)
    assert P(rt).stats.opens == 0


def test_the_file_loads_with_the_stand_ins_and_derives_the_class():
    rt = rt_env()
    assert P(rt).cls is not None and G(rt).NR_Client_Panel.Type == "NR_Client_Panel"
    assert len(G(rt).NR_T.adds.OnKeyPressed) == 1


def test_a_reload_adds_no_second_listener_and_keeps_the_window():
    rt = rt_env()
    create(rt)
    w = inst(rt)
    _load(rt, CORE)
    _kernel(rt)
    _clients(rt)
    g = G(rt)
    assert len(g.NR_T.adds.OnKeyPressed) == 1
    count = rt.eval("""function(fn)
        local n = 0
        for _, f in ipairs(NR_T.adds.OnCreatePlayer) do if f == fn then n = n + 1 end end
        return n
    end""")
    assert count(g.NR_ClientPanel_Installed.create) == 1
    assert same(rt, inst(rt), w)
    key(rt, 39)
    assert P(rt).stats.opens == 1 and inst(rt).onUI is True


# ------------------------------------------------------------------------------------------- create

def test_create_player_builds_a_hidden_instance_off_the_ui_manager_and_registers_player_0():
    rt = rt_env()
    create(rt)
    p = inst(rt)
    assert p is not None and p.visible is False and p.onUI is False
    assert p.renderPlayer == 0 and p.resizable is False and p.initialised is True
    assert p.width == 280 and p.height == 320
    assert p.title == "Nutrition"                        # a translation miss reads the fallback
    g = G(rt)
    assert g.NR_T.regs == 1 and g.NR_T.regNames[1] == "NutritionRevamp.panel"
    assert same(rt, g.NR_T.regFuncs, g.ISCollapsableWindow)
    assert P(rt).stats.restoredVisible is False


def test_only_player_0_registers_with_the_layout_manager():
    rt = rt_env()
    create(rt, 1)
    assert inst(rt, 1) is not None and inst(rt, 1).renderPlayer == 1
    assert G(rt).NR_T.regs == 0


def test_a_respawn_removes_the_old_instance_first():
    rt = rt_env()
    create(rt)
    old = inst(rt)
    P(rt).toggle(0)
    assert old.onUI is True
    create(rt)
    assert old.onUI is False and old.visible is False
    assert not same(rt, inst(rt), old) and P(rt).stats.creates == 2


def test_the_restore_re_adding_the_panel_is_recorded():
    rt = rt_env(restore_visible=True)
    create(rt)
    assert P(rt).stats.restoredVisible is True
    assert inst(rt).onUI is True
    assert P(rt).toggle(0) is False                    # the first press closes what the restore opened
    assert inst(rt).onUI is False and P(rt).stats.closes == 1


# ------------------------------------------------------------------------------------------- toggle and the key

def test_toggle_sends_one_request_per_open():
    rt = rt_env()
    create(rt)
    sends = G(rt).NR_T.sends
    assert P(rt).toggle(0) is True
    p = inst(rt)
    assert p.onUI is True and p.visible is True and p.onTop is True
    assert G(rt).NR_T.sends == sends + 1 and G(rt).NR_T.lastCommand == "mirror.request"
    assert P(rt).toggle(0) is False
    assert p.onUI is False and p.visible is False
    assert G(rt).NR_T.sends == sends + 1
    assert P(rt).toggle(0) is True
    s = P(rt).stats
    assert G(rt).NR_T.sends == sends + 2
    assert s.opens == 2 and s.closes == 1 and s.requests == 2 and s.requestFailures == 0


def test_a_failed_request_is_counted_apart():
    rt = rt_env()
    create(rt)
    G(rt).sendClientCommand = None
    assert P(rt).toggle(0) is True
    assert P(rt).stats.requests == 0 and P(rt).stats.requestFailures == 1


def test_toggle_without_an_instance_answers_false():
    rt = rt_env()
    assert P(rt).toggle(0) is False
    assert P(rt).toggle("0") is False


def test_the_key_handler_toggles_on_the_bound_key_and_ignores_other_keys():
    rt = rt_env()
    create(rt)
    key(rt, 49)
    key(rt, 37)
    assert P(rt).stats.opens == 0 and P(rt).stats.keyPresses == 0
    key(rt, 39)
    assert P(rt).stats.opens == 1 and inst(rt).onUI is True
    key(rt, 39)
    assert P(rt).stats.closes == 1


def test_the_key_follows_a_rebind():
    rt = rt_env()
    create(rt)
    G(rt).NR_ClientModOptions_Page.dict.togglePanel.key = 49
    key(rt, 39)
    assert P(rt).stats.opens == 0
    key(rt, 49)
    assert P(rt).stats.opens == 1


def test_the_key_handler_never_runs_on_the_server_side():
    rt = rt_env()
    create(rt)
    G(rt).NR_T.client = False
    key(rt, 39)
    assert P(rt).stats.keyPresses == 0


def test_a_raising_toolkit_member_is_caught():
    rt = rt_env()
    create(rt)
    rt.execute("function ISCollapsableWindow:addToUIManager() error('ui boom') end")
    key(rt, 39)                                        # must not raise into the event
    assert P(rt).stats.opens == 1                       # the guard swallowed the one member that raised


# ------------------------------------------------------------------------------------------- the frame

def frame(rt, p):
    p.prerender(p)
    p.render(p)


def test_frames_rebuild_once_and_draw_the_cached_rows():
    rt = rt_env()
    create(rt)
    P(rt).toggle(0)
    p = inst(rt)
    v = G(rt).NutritionRevamp.client.view
    n = v.stats.rebuilds
    frame(rt, p)
    frame(rt, p)
    assert v.stats.rebuilds == n + 1                  # two frames, one rebuild
    ui = G(rt).NR_T.ui
    assert ui.prerenders == 2 and ui.renders == 2
    assert P(rt).stats.renders == 2
    assert ui.draws == 12 and ui.rights == 12         # the six class rows, twice
    fire(rt, "OnServerCommand", "'NutritionRevamp', 'mirror', { fluids_dehydPct = 2 }")
    frame(rt, p)
    assert v.stats.rebuilds == n + 2


def test_a_collapsed_panel_draws_no_rows():
    rt = rt_env()
    create(rt)
    p = inst(rt)
    p.isCollapsed = True
    frame(rt, p)
    assert G(rt).NR_T.ui.renders == 1 and G(rt).NR_T.ui.draws == 0


def big_mirror(rt):
    rt.execute("NR_T.player.hasTrait = function(self, e) return e == CharacterTrait.NUTRITIONIST end")
    rt.execute("""
        local m = {}
        for _, k in ipairs(NutritionRevamp.data.records.ORDER) do m['nut_' .. k .. '_g'] = 2 end
        NR_T.bigMirror = m
    """)
    fire(rt, "OnServerCommand", "'NutritionRevamp', 'mirror', NR_T.bigMirror")


def test_the_height_follows_the_rows_and_is_capped_at_the_screen():
    rt = rt_env()
    create(rt)
    p = inst(rt)
    frame(rt, p)
    v = G(rt).NutritionRevamp.client.view
    assert len(v.rows) == 6
    assert p.height == 16 + 4 + 6 * 15 + 4 and p.width == 280      # the six class rows: no cap reached
    assert v.stats.overflowRows == 0
    big_mirror(rt)
    rt.execute("getPlayerScreenHeight = function(n) return 300 end")
    frame(rt, p)
    assert v.level == 3 and len(v.rows) > 20
    assert p.height == 300 - 200                                  # the cap: the screen minus the panel's top
    fit = (100 - 16 - 8) // 15
    assert v.stats.overflowRows == len(v.rows) - fit
    frame(rt, p)
    assert v.stats.overflowRows == len(v.rows) - fit              # once per rebuild, not per frame


def test_the_wheel_scrolls_within_bounds_and_the_render_draws_from_the_offset():
    rt = rt_env()
    create(rt)
    p = inst(rt)
    assert p.onMouseWheel(p, 1) is False                          # no overflow: the event is not taken
    big_mirror(rt)
    rt.execute("getPlayerScreenHeight = function(n) return 300 end")
    frame(rt, p)
    n = len(G(rt).NutritionRevamp.client.view.rows)
    room = 100 - 16 - 8
    assert p.scrollY == 0
    assert p.onMouseWheel(p, 1) is True and p.scrollY == 45       # 3 lines of 15 px
    assert p.onMouseWheel(p, -1) is True and p.scrollY == 0
    assert p.onMouseWheel(p, -1) is True and p.scrollY == 0       # clamped at the top
    for _ in range(100):
        p.onMouseWheel(p, 1)
    assert p.scrollY == n * 15 - room                             # clamped at the overflow
    rt.execute("NR_T.firstY = nil; function ISCollapsableWindow:drawText(s, x, y) NR_T.firstY = NR_T.firstY or y end")
    frame(rt, p)
    start = 16 + 4 - (n * 15 - room)                                # the scrolled origin, above the title bar
    first = G(rt).NR_T.firstY
    assert first >= 16 + 4 and first < 16 + 4 + 15 and (first - start) % 15 == 0  # the first row at or below the top clip


def test_close_leaves_the_ui_manager_and_counts():
    rt = rt_env()
    create(rt)
    P(rt).toggle(0)
    p = inst(rt)
    assert p.onUI is True
    p.close(p)                                                    # the title-bar X
    assert p.onUI is False and p.visible is False and P(rt).stats.closes == 1
    p.close(p)                                                    # already hidden: no second count
    assert P(rt).stats.closes == 1


def test_the_title_falls_back_when_the_text_lookup_is_absent():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(ENV)
    _kernel(rt)
    for path in (MIRROR, PANEL, VIEW):                            # no _ModOptions: no NR.client.text
        _load(rt, path)
    assert G(rt).NutritionRevamp.client.text is None
    p = G(rt).NR_Client_Panel.new(G(rt).NR_Client_Panel, 0, 0, 280, 320, 0)
    assert p.title == "Nutrition"


def test_a_raising_render_is_caught():
    rt = rt_env()
    create(rt)
    p = inst(rt)
    rt.execute("function ISCollapsableWindow:render() error('render boom') end")
    frame(rt, p)
    assert P(rt).stats.errors == 1
