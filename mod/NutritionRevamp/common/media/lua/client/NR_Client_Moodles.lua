-- NR_Client_Moodles.lua -- the six symptom-class moodles (Plan 7 Task 8, rulings 5, 10 and 11): through
-- MoodleFramework when it is installed, else the mod's own icon column at a FIXED inset of the player's viewport.
-- Optional, detected and never required (spec § 4.9); no moodle type goes through the vanilla registry (#1140).
--
-- Detection (#2547): type(MF) == "table" and type(MF.createMoodle) == "function", at OnGameBoot (MF is defined at
-- the framework's file load, which may follow this file's). The framework route creates "NR_<class>" per class at
-- boot, then configures and first sets each from an OnCreatePlayer handler added INSIDE the boot handler, after the
-- framework's own builders (#2548; MF.getMoodle answers nil until they ran). Measured on 42.20.4 in x181 (X29): the
-- framework loads whole, a moodle at 0.95 read level 4 and joined the UI manager, at 0.5 it was never drawn
-- (#2534, #3191-#3193); the mod's own ISUIElement widget rendered in the same session.
--
-- The framework's members this file calls (READ-ONLY live tree, workshop 3396446795, mods/MoodleFramework/42.20/
-- media/lua/client/MF_ISMoodle.lua, read 2026-10-06; the framework holds no pcall of its own, #2546, so every
-- call here is index-first inside one):
--   MF.createMoodle(name)                         :25  (adds one OnCreatePlayer builder per name, :29)
--   MF.getMoodle(name, playerNum)                 :35  (nil until the builder ran)
--   moodle:setValue(value)                        :83  (no clamp, #2535; joins/leaves the UI manager :102-109,
--                                                       the flag moodle.addedToUIManager :104/:108)
--   moodle:getLevel()                             :127 (0..4 against the eight thresholds; the probe's read)
--   moodle:getGoodBadNeutral()                    :120 (not called here: polarity follows the thresholds)
--   moodle:setThresholds(bad4..bad1, good1..good4) :155 (a nil good4 reads unreachable, a nil bad side never hit)
--   moodle:setPicture(goodBadNeutral, level, tex) :197 (the per-level override getPicture :361 reads first)
--   moodle:setTitle(goodBadNeutral, level, text)  :176
--   moodle:setDescription(goodBadNeutral, level, text) :185
-- The framework's defaults (MF_ISMoodle.lua:517): bad 0.1/0.2/0.3/0.4, good 0.6/0.7/0.8/0.9; the stored value starts
-- at 0.5 (:75). A symptom is a BAD moodle (ruling T8-1; vanilla's hunger is one, and the framework tints the plate by
-- polarity: bad index 2, :123 and :222), so this file replaces the thresholds per class with K.view.moodleThreshold
-- on the bad side only, each midway between two class values, so the framework's level IS the class level --
-- four-level classes bad1..bad4 0.4375 / 0.3125 / 0.1875 / 0.0625 (values 0.375 / 0.25 / 0.125 / 0.0), deficiency
-- and excess 0.41667 / 0.25 / 0.08333 and no fourth (values 0.33333 / 0.16667 / 0.0); the good side is left
-- unreachable (nil, MF.TooLargeValue, :156-164). setThresholds takes (bad4, bad3, bad2, bad1, good1..good4) at
-- :155, so the bad side is passed bad4 first. A class at level 0 sets 0.5: neutral, off the UI manager. The bad-side
-- draw is unmeasured: x181 read the good side only (#3192); x183m's arm F is the first bad-side reading.
-- Every set is repeated for the six after each player creation, because the framework's value
-- store is keyed by the character object and starts fresh (#2538).
-- The icon route: the framework's own default is a name lookup, media/ui/<size>/NR_<class>.png then
-- media/ui/NR_<class>.png (:432-437, :595); this file instead hands it the mod's one icon,
-- media/ui/NutritionRevamp/<class>.png, through setPicture for bad-side levels 1-4 behind a nil check (ruling 11;
-- Task 9 ships the PNGs), so no sized copy is needed; a nil texture leaves the framework's own lookup in place.
-- The tooltip text: setTitle from Moodles_NR_<class>_lvl<n> and setDescription from UI_NR_Class_<class>_<n>,
-- through NR.client.text (ruling 12), because the framework's own keys carry a polarity infix (:223, :242).
-- Ruling T8-3: both routes serve player 0 only, because the mirror and the view are the local player's and a
-- player-1 widget would show player 0's levels; split-screen gets no NR moodles. Death: the framework suspends its
-- moodles when the character dies (:549); the own column does the same through an OnPlayerDeath handler (added in
-- the boot handler) that zeros the kept levels, so the column draws nothing until the next apply.
--
-- The own route (no framework): one NR_Client_MoodleColumn (an ISUIElement) for player 0 -- the mirror is the local
-- player's -- at getPlayerScreenLeft + getPlayerScreenWidth - 96, getPlayerScreenTop + 240, 40 x 6 * 44: a FIXED
-- inset, NEVER anchored to the vanilla stack (ruling 10; MoodlesUI's exposure is a fact for the page only). Its
-- render draws each class whose level > 0 top-down as its icon (a coloured rect when the texture is nil) with the
-- level as a row of pips beneath; a respawn replaces the instance. It reads the cached levels only: nothing walks
-- the mirror per frame (#2692).
--
-- The driver: NR.client.view.listeners (NR_Client_View.lua :18-20, :120) calls fn(classes, rows, level) after every
-- view rebuild -- on each mirror arrival and when a surface refreshes -- and the hook here calls apply(classes). This
-- file sorts before _View, so it creates NR.client.view = { listeners = {} } when absent and View carries the array
-- over (:43). The moodles option (NR.client.modOptions.moodles(), default true) is read on each apply: off sets every
-- framework value neutral and takes the column off the UI manager; on restores both.
--
-- Shape (NR_Client_Effects.lua's discipline): the sentinel NR_ClientMoodles_Installed is a global of its own holding
-- the boot, create and listener closures, each looking NutritionRevamp.client.moodles up per call; the side test is
-- per call; every engine, toolkit and framework member is named only inside a function behind a nil check and
-- reached index-first inside a pcall, so the file loads with no engine (testing/tests/kernel/
-- test_client_moodles_shape.py); every handler body runs under one pcall. probe(cls) is TEST-ONLY for the driver.
-- The inset (ruling T8-2): the column spans x 1184-1224 on a 1280 viewport, clear of the measured vanilla band
-- 1238-1270 at the 32 px moodle size (x181); at 48 px the vanilla stack reaches 1222 and overlaps by 2 px, at 64 px
-- more, and a repositioner mod that moves the stack left may overlap it (the page states this beside the caveat).
-- Cadence: apply once per view rebuild (at most one push a minute plus requests); the column's render per frame
-- draws at most 6 icons and 24 pips from cached fields.
local NR = NutritionRevamp

NR_ClientMoodles_Installed = NR_ClientMoodles_Installed or {}

NR.client.moodles = {
    route = "none",
    classes = { "energy", "hydration", "deficiency", "excess", "stimulant", "sleep" },
    stats = { sets = 0, skips = 0, renders = 0, errors = 0, created = 0, got = 0, columns = 0 },
    levels = { energy = 0, hydration = 0, deficiency = 0, excess = 0, stimulant = 0, sleep = 0 },
    handles = {},
    column = nil,
    cls = nil,
    enabled = true,
    lastDrawn = 0,
    lastError = nil,
}
local MOODLES = NR.client.moodles

local PREFIX = "NR_" -- the framework moodle names, NR_<class> (ruling 10; #2556: no collision with the corpus)
local ICON_DIR = "media/ui/NutritionRevamp/" -- the mod's icons, <class>.png (ruling 11)
local NEUTRAL = 0.5 -- the framework's neutral value when the kernel is absent (K.view.MOODLE_NEUTRAL)
local BAD = 2 -- MF_ISMoodle.lua:123 (the framework's bad polarity index; a symptom is a bad moodle)
local INSET_RIGHT = 96 -- px from the viewport's right edge (ruling T8-2): the column spans 1184-1224 on 1280
local INSET_TOP = 240 -- px below the viewport's top
local COL_WIDTH = 40 -- px
local SLOT = 44 -- px per class slot: a 32 px icon and the pip row
local ICON = 32 -- px
local ICON_X = 4 -- px
local PIP_W = 6 -- px
local PIP_H = 4 -- px
local PIP_STEP = 8 -- px
local PIP_Y = 36 -- px below the slot's top
local SCREEN_W = 1280 -- px, the viewport width when getPlayerScreenWidth is absent or raises
local COLOURS = { -- r, g, b of a class's rect when its icon is nil
    energy = { 0.90, 0.60, 0.20 },
    hydration = { 0.25, 0.55, 0.95 },
    deficiency = { 0.85, 0.25, 0.25 },
    excess = { 0.75, 0.35, 0.85 },
    stimulant = { 0.95, 0.85, 0.25 },
    sleep = { 0.45, 0.45, 0.80 },
}

-- One method of el, index-first inside a pcall: (ok, result).
local function call(el, name, ...)
    local ok, present, v = pcall(NR.call, el, name, ...)
    return ok and present, v
end

local function fail(err)
    local nr = NutritionRevamp
    local M = nr.client.moodles
    M.stats.errors = M.stats.errors + 1
    M.lastError = err
    nr.log.say(2, "moodles: " .. tostring(err))
end

-- A screen function of playerNum (getPlayerScreenLeft / Top / Width), or default when absent, raising or not a number.
local function screen(fn, playerNum, default)
    if fn == nil then return default end
    local ok, v = pcall(fn, playerNum)
    if ok and type(v) == "number" then return v end
    return default
end

-- A texture through getTexture, or nil when the function is absent, raises or finds nothing (#2489).
local function texture(path)
    if getTexture == nil then return nil end
    local ok, t = pcall(getTexture, path)
    if ok then return t end
    return nil
end

-- A translation through NR.client.text when it exists (NR_Client_ModOptions.lua), else the fallback or the key.
local function text(key, fallback)
    local nr = NutritionRevamp
    if nr.client.text ~= nil then return nr.client.text(key, fallback) end
    if fallback ~= nil then return fallback end
    return key
end

local function kview()
    local K = NutritionRevamp.kernel
    if K == nil then return nil end
    return K.view
end

if ISUIElement ~= nil and type(ISUIElement.derive) == "function" then
    local okD, cls = pcall(ISUIElement.derive, ISUIElement, "NR_Client_MoodleColumn")
    if okD and cls ~= nil then
        NR_Client_MoodleColumn = cls
        MOODLES.cls = cls

        function cls:new(x, y, w, h, playerNum)
            local o = ISUIElement.new(self, x, y, w, h)
            o.playerNum = playerNum
            o.onUI = false
            o.textures = {}
            return o
        end

        -- The cached levels as icons and pips; never the mirror.
        function cls:render()
            local ok, err = pcall(NutritionRevamp.client.moodles.renderColumn, self)
            if not ok then fail(err) end
        end
    end
end

-- Whether the moodles show: NR.client.modOptions.moodles() read per call, true when absent or raising.
function MOODLES.isEnabled()
    local m = NutritionRevamp.client.modOptions
    if m == nil or m.moodles == nil then return true end
    local ok, v = pcall(m.moodles)
    if ok and v == false then return false end
    return true
end

-- The column's render body: one count, then each class whose level > 0, top-down in class order, as its icon (or
-- its coloured rect) with level pips beneath. The caller holds the pcall.
function MOODLES.renderColumn(el)
    if el == nil then return nil end
    local M = NutritionRevamp.client.moodles
    M.stats.renders = M.stats.renders + 1
    local drawRect = el.drawRect
    local drawTex = el.drawTextureScaled
    local y = 0
    local drawn = 0
    for i = 1, #M.classes do
        local c = M.classes[i]
        local lv = M.levels[c]
        if type(lv) == "number" and lv > 0 then
            local rgb = COLOURS[c]
            local tex = nil
            if el.textures ~= nil then tex = el.textures[c] end
            if tex ~= nil and drawTex ~= nil then
                drawTex(el, tex, ICON_X, y, ICON, ICON, 1)
            elseif drawRect ~= nil then
                drawRect(el, ICON_X, y, ICON, ICON, 0.85, rgb[1], rgb[2], rgb[3])
            end
            local pips = math.min(math.floor(lv), 4)
            if drawRect ~= nil then
                for p = 1, pips do
                    drawRect(el, ICON_X + (p - 1) * PIP_STEP, y + PIP_Y, PIP_W, PIP_H, 1, rgb[1], rgb[2], rgb[3])
                end
            end
            y = y + SLOT
            drawn = drawn + 1
        end
    end
    M.lastDrawn = drawn
    return nil
end

-- The column on or off the UI manager (on records onUI, the probe's read).
local function showColumn(col, on)
    if col == nil then return end
    if on and col.onUI ~= true then
        local ok = call(col, "addToUIManager")
        if ok then col.onUI = true end
    elseif not on and col.onUI == true then
        call(col, "removeFromUIManager")
        col.onUI = false
    end
end

-- The own route's column for playerNum: the old one (a respawn) leaves the UI manager first; the new one sits at
-- the fixed inset, loads the six icons once, and joins the UI manager when the option is on.
function MOODLES.buildColumn(playerNum)
    local M = NutritionRevamp.client.moodles
    local cls = M.cls
    if cls == nil then return nil end
    local old = M.column
    if old ~= nil then
        showColumn(old, false)
        M.column = nil
    end
    local left = screen(getPlayerScreenLeft, playerNum, 0)
    local top = screen(getPlayerScreenTop, playerNum, 0)
    local width = screen(getPlayerScreenWidth, playerNum, SCREEN_W)
    local col = cls:new(left + width - INSET_RIGHT, top + INSET_TOP, COL_WIDTH, #M.classes * SLOT, playerNum)
    for i = 1, #M.classes do
        local c = M.classes[i]
        col.textures[c] = texture(ICON_DIR .. c .. ".png")
    end
    call(col, "initialise")
    call(col, "instantiate")
    M.column = col
    M.stats.columns = M.stats.columns + 1
    showColumn(col, M.isEnabled())
    return col
end

-- One framework moodle's thresholds (K.view.moodleThreshold, passed bad4..bad1 in setThresholds' own order,
-- MF_ISMoodle.lua:155), its icon for bad-side levels 1-4 when the texture loads, and its title and description per
-- level.
function MOODLES.configure(h, c)
    local V = kview()
    if V == nil then return end
    local top = V.moodleTop(c)
    local t1 = V.moodleThreshold(1, c)
    local t2 = V.moodleThreshold(2, c)
    local t3 = V.moodleThreshold(3, c)
    local t4 = V.moodleThreshold(4, c)
    local okT = call(h, "setThresholds", t4, t3, t2, t1, nil, nil, nil, nil)
    if not okT then fail("setThresholds " .. c) end
    local tex = texture(ICON_DIR .. c .. ".png")
    for lvl = 1, 4 do
        if tex ~= nil then call(h, "setPicture", BAD, lvl, tex) end
        if lvl <= top then
            call(h, "setTitle", BAD, lvl, text("Moodles_NR_" .. c .. "_lvl" .. lvl, nil))
            call(h, "setDescription", BAD, lvl, text("UI_NR_Class_" .. c .. "_" .. lvl, nil))
        end
    end
end

-- OnGameBoot: the route, and on the framework route the six moodles created; then the OnCreatePlayer handler is
-- added (after the framework's builders, which createMoodle has just added).
function MOODLES.onGameBoot()
    local M = NutritionRevamp.client.moodles
    local detected = false
    if MF ~= nil then
        local ok, d = pcall(function() return type(MF) == "table" and type(MF.createMoodle) == "function" end)
        detected = ok and d == true
    end
    if detected then M.route = "framework" else M.route = "own" end
    if M.route == "framework" then
        for i = 1, #M.classes do
            local ok, err = pcall(MF.createMoodle, PREFIX .. M.classes[i])
            if ok then M.stats.created = M.stats.created + 1 else fail(err) end
        end
    end
    local S = NR_ClientMoodles_Installed
    if S.create == nil and Events ~= nil and Events.OnCreatePlayer ~= nil then
        S.create = function(playerNum, player)
            local nr = NutritionRevamp
            if nr == nil or nr.client == nil or nr.client.moodles == nil then return end
            local ok, err = pcall(nr.client.moodles.onCreatePlayer, playerNum, player)
            if not ok then fail(err) end
        end
        Events.OnCreatePlayer.Add(S.create)
    end
    if S.death == nil and Events ~= nil and Events.OnPlayerDeath ~= nil then
        S.death = function(player)
            local nr = NutritionRevamp
            if nr == nil or nr.client == nil or nr.client.moodles == nil then return end
            local ok, err = pcall(nr.client.moodles.onPlayerDeath, player)
            if not ok then fail(err) end
        end
        Events.OnPlayerDeath.Add(S.death)
    end
end

-- OnPlayerDeath: the framework suspends its moodles on death (:549); the own column's kept levels go to zero, so
-- it draws nothing until the next apply (a respawn's create re-applies the view's classes).
function MOODLES.onPlayerDeath(player)
    local M = NutritionRevamp.client.moodles
    for i = 1, #M.classes do
        M.levels[M.classes[i]] = 0
    end
end

-- OnCreatePlayer (player 0 only; the mirror is the local player's): the framework's six handles kept and configured,
-- or the own column built; then the last known levels are set again (the view's classes when it has them).
function MOODLES.onCreatePlayer(playerNum, player)
    local nr = NutritionRevamp
    local M = nr.client.moodles
    if not nr.isClient() then return end
    local pn = playerNum
    if type(pn) ~= "number" then pn = 0 end
    if pn ~= 0 then return end
    if M.route == "framework" then
        M.handles = {}
        local getMoodle = nil
        if MF ~= nil then
            local okG, g = pcall(function() return MF.getMoodle end)
            if okG then getMoodle = g end
        end
        for i = 1, #M.classes do
            local c = M.classes[i]
            local h = nil
            if getMoodle ~= nil then
                local ok, v = pcall(getMoodle, PREFIX .. c, pn)
                if ok then h = v end
            end
            if h == nil then
                fail("no framework moodle " .. PREFIX .. c)
            else
                M.handles[c] = h
                M.stats.got = M.stats.got + 1
                M.configure(h, c)
            end
        end
    elseif M.route == "own" then
        M.buildColumn(pn)
    end
    local last = M.levels
    if nr.client.view ~= nil and type(nr.client.view.classes) == "table" then last = nr.client.view.classes end
    M.apply(last)
end

-- The view listener's body: per class the level kept, then the framework value set (neutral when the option is off)
-- or the column shown or hidden. stats.sets counts each class written, stats.skips a missing handle or a non-table.
function MOODLES.apply(classes)
    local M = NutritionRevamp.client.moodles
    if type(classes) ~= "table" then
        M.stats.skips = M.stats.skips + 1
        return false
    end
    local on = M.isEnabled()
    M.enabled = on
    local V = kview()
    for i = 1, #M.classes do
        local c = M.classes[i]
        local lv = classes[c]
        if type(lv) ~= "number" then lv = 0 end
        M.levels[c] = lv
        if M.route == "framework" then
            local h = M.handles[c]
            if h == nil then
                M.stats.skips = M.stats.skips + 1
            else
                local v = NEUTRAL
                if on and V ~= nil then v = V.moodleValue(lv, c) end
                local ok, present = pcall(NR.call, h, "setValue", v)
                if ok and present then
                    M.stats.sets = M.stats.sets + 1
                elseif ok then
                    fail("no setValue on " .. PREFIX .. c)
                else
                    fail(present)
                end
            end
        else
            M.stats.sets = M.stats.sets + 1
        end
    end
    if M.route == "own" then showColumn(M.column, on) end
    return true
end

-- TEST-ONLY (the driver's lua.call NutritionRevamp.client.moodles.probe deficiency): three scalars -- the class
-- level (the framework moodle's getLevel() on that route, else the kept level), whether it is on the UI manager
-- (the framework's addedToUIManager flag, else the column's onUI), and the route.
function MOODLES.probe(c)
    local M = NutritionRevamp.client.moodles
    if M.route == "framework" then
        local h = M.handles[c]
        if h == nil then return 0, false, M.route end
        local ok, present, lv = pcall(NR.call, h, "getLevel")
        if not (ok and present and type(lv) == "number") then lv = 0 end
        return lv, h.addedToUIManager == true, M.route
    end
    local lv = M.levels[c]
    if type(lv) ~= "number" then lv = 0 end
    return lv, M.column ~= nil and M.column.onUI == true, M.route
end

local S = NR_ClientMoodles_Installed
if S.listener == nil then
    S.listener = function(classes, rows, level)
        local nr = NutritionRevamp
        if nr == nil or nr.client == nil or nr.client.moodles == nil then return end
        local ok, err = pcall(nr.client.moodles.apply, classes)
        if not ok then fail(err) end
    end
end
NR.client.view = NR.client.view or {}
NR.client.view.listeners = NR.client.view.listeners or {}
local listeners = NR.client.view.listeners
local present = false
for i = 1, #listeners do
    if listeners[i] == S.listener then present = true end
end
if not present then listeners[#listeners + 1] = S.listener end

if S.boot == nil and Events ~= nil and Events.OnGameBoot ~= nil then
    S.boot = function()
        local nr = NutritionRevamp
        if nr == nil or nr.client == nil or nr.client.moodles == nil then return end
        local ok, err = pcall(nr.client.moodles.onGameBoot)
        if not ok then fail(err) end
    end
    Events.OnGameBoot.Add(S.boot)
end
