"""The harness's tooltip.measure (Plan 16 Task 8; carries section 6), offline: PZTestKit_Client.lua's Plan 16 Task 8
block, from its marker line to the end of the file, loaded beside the REAL mod tooltip file (NR_Client_Tooltip.lua,
through test_client_tooltip_shape's runtime: NR_Core, the three kernels the band calls, a stub NR.data and the fill
table) with a stub TK. The engine is Lua stand-ins: an ObjectTooltip whose measure counts its lines (a header and,
as Food.DoTooltip does on 42.21, the hunger line only while getHungerChange is not 0 and the item lacks
HIDE_HUNGER_CHANGE) and counts every draw made while not measure-only, and an ISToolTipInv.render that follows
vanilla's client/ISUI/ISToolTipInv.lua:43-106 step for step (the measure pass, setHeight, the frame, the second
DoTooltip), which the mod's wrapper wraps at load. It pins the reply shape, the height-difference reading of the
hunger line in each arm, that nothing is drawn, that the option's accessor is put back and the wrapper left clean,
and the refusals; whether the engine's own measure drops one line is the first live session's (Task 9), its smoke
test. The harness is never a kernel file, so the coverage gate is untouched."""
import os

from . import test_client_tooltip_shape as tts

LUA = os.path.join(tts.REPO, "testing", "PZTestKit", "PZTestKit", "42", "media", "lua")
CLIENT = os.path.join(LUA, "client", "PZTestKit_Client.lua")
MARK = "-- ==== Plan 16 Task 8 additions (client: tooltip.measure)"

# vanilla's render (ISToolTipInv.lua:43-106) and an ObjectTooltip whose measure counts lines; set before the mod's
# tooltip file loads, so its wrapper saves this render as the original
VANILLA = r"""
NR_V = { javaDraws = 0, LINE = 15, PAD = 10, raiseOn = nil }
getMouseX = function() return 100 end
getMouseY = function() return 100 end
getCore = function() return { getScreenWidth = function(s) return 1920 end,
                              getScreenHeight = function(s) return 1080 end } end
ObjectTooltip = {}
function ObjectTooltip.new()
    local t = { x = 0, y = 0, width = 0, height = 0, measureOnly = false }
    function t.setX(s, v) s.x = v end
    function t.setY(s, v) s.y = v end
    function t.getX(s) return s.x end
    function t.getY(s) return s.y end
    function t.setWidth(s, v) s.width = v end
    function t.getWidth(s) return s.width end
    function t.setHeight(s, v) s.height = v end
    function t.getHeight(s)
        if NR_V.raiseOn ~= nil and NR_V.raiseOn() then error("getHeight boom") end
        return s.height
    end
    function t.setMeasureOnly(s, v) s.measureOnly = v end
    function t.isMeasureOnly(s) return s.measureOnly end
    function t.getLineSpacing(s) return NR_V.LINE end
    function t.setCharacter(s, c) s.character = c end
    return t
end
-- Food.DoTooltip's hunger-line predicate (jar Food.DoTooltip @67-@83 L1391-L1393)
function NR_V.doTooltip(item, tt)
    local n = 1
    if item:getHungerChange() ~= 0 and not item:hasTag(ItemTag.HIDE_HUNGER_CHANGE) then n = n + 1 end
    if not tt.measureOnly then NR_V.javaDraws = NR_V.javaDraws + n end
    tt:setWidth(150)
    tt:setHeight(NR_V.PAD + n * NR_V.LINE)
end
ISToolTipInv.render = function(self)
    if not ISContextMenu.instance or not ISContextMenu.instance.visibleCheck then
        NR_T.renders = NR_T.renders + 1
        local mx = getMouseX() + 24
        local my = getMouseY() + 24
        if not self.followMouse then
            mx = self:getX()
            my = self:getY()
        end
        self.tooltip:setX(mx)
        self.tooltip:setY(my)
        self.tooltip:setWidth(50)
        self.tooltip:setMeasureOnly(true)
        if self.item then self.item:DoTooltip(self.tooltip) end
        self.tooltip:setMeasureOnly(false)
        local tw = self.tooltip:getWidth()
        local th = self.tooltip:getHeight()
        self.tooltip:setX(math.max(0, mx))
        self.tooltip:setY(math.max(0, my))
        self:setX(self.tooltip:getX())
        self:setY(self.tooltip:getY())
        self:setWidth(tw)
        self:setHeight(th)
        self:drawRect(0, 0, self.width, self.height, 0.5, 0, 0, 0)
        self:drawRectBorder(0, 0, self.width, self.height, 1, 0.4, 0.4, 0.4)
        if self.item then self.item:DoTooltip(self.tooltip) end
    end
end
"""

# Food items with the getters the command and Food.DoTooltip read, over FILLS' tag sets
ITEMS = r"""
local food = NR_T.food
function NR_T.food(ft, o)
    o = o or {}
    local it = food(ft, o)
    it.getHungerChange = function(s) return o.hc or -0.16 end
    it.hasTag = function(s, t) return NR_T.tagset(ft).set[t] == true end
    it.DoTooltip = function(s, tt) NR_V.doTooltip(s, tt) end
    return it
end
NR_T.inv.items["Base.Apple"] = NR_T.food("Base.Apple")
NR_T.inv.items["Base.Cabbage"] = NR_T.food("Base.Cabbage")
NR_T.inv.items["Base.Orange"] = NR_T.food("Base.Orange")
"""

STUB_TK = r"""
TK = { side = "client", commands = {} }
TK.register = function(name, fn) TK.commands[name] = fn end
TK.call = function(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end
"""


def section():
    with open(CLIENT, encoding="utf-8", newline="") as fh:
        src = fh.read().replace("\r\n", "\n")
    return src[src.index(MARK):]


# the mod's wrapper mutated as the Task 8 review's M1 (the hide ignores the option) and M4 (the unhide dropped)
M1 = ("if lines ~= nil and lines.fill == true and t.optionOn() then", "if lines ~= nil and lines.fill == true then")
M4 = ("        original(self)\n        t.unhide()\n", "        original(self)\n")


def rt_with(mod=True, mutate=None):
    rt = tts.lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(tts.ENV)
    rt.execute(VANILLA)
    tts._load(rt, tts.CORE)
    tts._load(rt, tts.DIALS)
    for k in tts.KERNELS:
        tts._load(rt, k)
    rt.execute(tts.DATA)
    rt.execute("NutritionRevamp.client.view = { level = 3, listeners = {} }")
    if mod:
        src = tts._src(tts.TOOLTIP)
        if mutate is not None:
            assert src.count(mutate[0]) == 1
            src = src.replace(mutate[0], mutate[1])
        rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@NR_Client_Tooltip.lua")()
    rt.execute(tts.FILLS)
    rt.execute(ITEMS)
    rt.execute(STUB_TK)
    rt.eval("function(src, name) return assert(loadstring(src, name)) end")(section(), "@PZTestKit_Client.lua")()
    return rt


def cmd(rt, *args):
    return rt.globals().TK.commands["tooltip.measure"](rt.table(*args))


def T(rt):
    return rt.globals().NutritionRevamp.client.tooltip


def test_the_mods_hide_drops_one_line_in_the_on_arm_and_the_off_arm_keeps_vanillas_line():
    rt = rt_with()
    on = cmd(rt, "Base.Apple", "1")
    assert on.ok is True and on.fullType == "Base.Apple" and on.hideOn is True and on.wrapped is True
    assert on.vanilla is True and on.nativeTag is False and on.fill is True and on.optionBefore is True
    assert on.heightBase == 40 and on.heightOff == 40 and on.heightOn == 25 and on.lineDrop == 15
    assert on.lineSpacing == 15 and on.tagLeft is False
    assert on.height == 25 and on.hungerLineDrawn is False and on.bandShown is True
    assert on.bandOn is True and on.bandOff is False                # the band follows the forced option
    assert on.hiddenOn == 1 and on.shownOn == 1                     # the wrapper's one add and its one remove
    assert on.tagAfter is False and on.restored is True and T(rt).pending is None and T(rt).depth == 0
    assert rt.globals().NR_V.javaDraws == 0                         # every DoTooltip ran measure-only
    off = cmd(rt, "Base.Apple", "0")
    assert off.ok is True and off.hideOn is False and off.height == 40
    assert off.hungerLineDrawn is True and off.bandShown is False and off.lineDrop == 15
    assert rt.globals().NR_V.javaDraws == 0


def test_a_hide_that_does_not_land_reads_the_line_drawn_in_the_on_arm():
    rt = rt_with()
    rt.execute("NR_T.tagset('Base.Apple').add = function(self, t) error('not exposed') end")   # the add raises
    r = cmd(rt, "Base.Apple", "1")
    assert r.ok is True and r.lineDrop == 0 and r.heightOn == r.heightOff == 40
    assert r.hungerLineDrawn is True and r.bandShown is True and r.hiddenOn == 0


def test_a_natively_tagged_food_never_draws_the_line_and_keeps_its_tag():
    rt = rt_with()
    for flag in ("0", "1"):
        r = cmd(rt, "Base.Cabbage", flag)
        assert r.ok is True and r.nativeTag is True and r.vanilla is False
        assert r.lineDrop == 0 and r.height == 25 and r.hungerLineDrawn is False and r.tagAfter is True
        assert r.hiddenOn == 0                                      # vanilla's own tag is never touched


def test_a_food_with_no_fill_entry_is_not_hidden_and_shows_vanillas_line_in_both_arms():
    rt = rt_with()
    r = cmd(rt, "Base.Orange", "1")
    assert r.ok is True and r.fill is False and r.lineDrop == 0 and r.hungerLineDrawn is True and r.hiddenOn == 0


def test_the_accessor_read_before_is_put_back_and_an_absent_options_table_removed():
    rt = rt_with()
    rt.execute("NR_T.userOpt = function() return false end; "
               "NutritionRevamp.client.options = { tooltipLines = NR_T.userOpt }")
    r = cmd(rt, "Base.Apple", "1")
    assert r.ok is True and r.optionBefore is False and r.restored is True
    assert rt.eval("NutritionRevamp.client.options.tooltipLines == NR_T.userOpt") is True
    assert r.hungerLineDrawn is False                               # the arms ran under the forced states, not the user's
    rt.execute("NutritionRevamp.client.options = nil")
    r2 = cmd(rt, "Base.Apple", "1")
    assert r2.ok is True and r2.restored is True and rt.eval("NutritionRevamp.client.options == nil") is True


def test_a_raising_render_names_the_error_and_leaves_the_wrapper_and_the_accessor_clean():
    rt = rt_with()
    # getHeight raises in the ON arm only, after the wrapper put the tag on
    rt.execute("NR_V.raiseOn = function() local f = NutritionRevamp.client.options.tooltipLines; "
               "return f ~= nil and f() == true end")
    r = cmd(rt, "Base.Apple", "1")
    assert r.ok is False and "getHeight boom" in r.error and r.heightOff == 40 and r.heightOn is None
    assert r.restored is True and rt.eval("NutritionRevamp.client.options == nil") is True
    assert T(rt).depth == 0 and T(rt).pending is None and r.tagAfter is False
    assert rt.eval("NR_T.tagset('Base.Apple').set.hhc == nil") is True


def test_without_the_mods_wrapper_both_arms_are_vanillas():
    rt = rt_with(mod=False)
    r = cmd(rt, "Base.Apple", "1")
    assert r.ok is True and r.wrapped is False and r.fill is None and r.lineDrop == 0
    assert r.hungerLineDrawn is True and r.bandShown is False


def test_refusals_and_a_context_menu():
    rt = rt_with()
    assert cmd(rt) == "usage: tooltip.measure <fullType> <hideOn 0|1>"
    assert cmd(rt, "Base.Apple") == "usage: tooltip.measure <fullType> <hideOn 0|1>"
    assert cmd(rt, "Base.Apple", "2") == "usage: tooltip.measure <fullType> <hideOn 0|1>"
    r = cmd(rt, "Base.Pear", "1")
    assert r.ok is False and r.reason == "no Base.Pear in the local inventory"
    rt.execute("ISContextMenu.instance.visibleCheck = true")
    c = cmd(rt, "Base.Apple", "1")
    assert c.ok is False and c.error == "render measured nothing (a context menu is up?)"
    assert c.restored is True
    rt.execute("getPlayer = function() return nil end")
    n = cmd(rt, "Base.Apple", "1")
    assert n.ok is False and n.reason == "no local player"


def test_a_hide_that_ignores_the_option_reads_the_line_not_drawn_in_the_off_arm():
    # review M1: the OFF arm is graded against the unwrapped baseline, not the vanilla predicate
    rt = rt_with(mutate=M1)
    off = cmd(rt, "Base.Apple", "0")
    assert off.ok is True and off.heightBase == 40 and off.heightOff == 25 and off.heightOn == 25
    assert off.hungerLineDrawn is False and off.lineDrop == 0
    good = cmd(rt_with(), "Base.Apple", "0")
    assert good.hungerLineDrawn is True and good.heightOff == good.heightBase == 40


def test_a_leaked_hide_tag_reads_ok_false():
    # review M4: the wrapper's unhide dropped, so the tag stays on the script item's set past the draw
    rt = rt_with(mutate=M4)
    r = cmd(rt, "Base.Apple", "1")
    assert r.ok is False and r.tagAfter is True and r.nativeTag is False and r.tagLeft is True
    assert r.error == "the hide tag was left on the item's script tag set" and r.hungerLineDrawn is None
    assert r.restored is True


def test_a_raise_outside_the_render_pcall_still_restores_the_accessor():
    # review finding 3: an arm that raises outside its render pcall (here the panel build) skips no restore
    rt = rt_with()
    rt.execute("NR_T.userOpt = function() return true end; "
               "NutritionRevamp.client.options = { tooltipLines = NR_T.userOpt }; "
               "TK.TM.panel = function() error('panel boom') end")
    r = cmd(rt, "Base.Apple", "1")
    assert r.ok is False and "panel boom" in r.error and r.restored is True
    assert rt.eval("NutritionRevamp.client.options.tooltipLines == NR_T.userOpt") is True
