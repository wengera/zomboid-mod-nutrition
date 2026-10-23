-- NR_Client_Moodles.lua -- the four symptom-class moodles (deficiency, excess, stimulant, sleep) and
-- the fifth, overfull, the soft cap shown (the stomach's whole mass past 730 g in four levels to 1100 g; never
-- vanilla's DISCOMFORT): through MoodleFramework when installed, else the mod's own icon column at a FIXED inset of the
-- player's viewport. No moodle type goes through the vanilla registry (#1140).
-- Detection at OnGameBoot (#2547), since MF may load after this file; the framework moodles are configured from an
-- OnCreatePlayer handler added INSIDE the boot handler, after the framework's own builders (#2548: getMoodle answers
-- nil until they ran). The framework holds no pcall of its own (#2546), so every call is index-first inside one.
-- A symptom is a BAD moodle (the framework tints by polarity), so the thresholds are replaced on the bad side only,
-- each midway between two class values, making the framework's level the class level; level 0 sets 0.5, neutral.
-- setThresholds takes the bad side bad4 first. Every set is repeated after each player creation, because the
-- framework's value store is keyed by the character object (#2538). The icon is handed in through setPicture and the
-- text through NR.client.text, because the framework's own keys carry a polarity infix.
-- Player 0 only: the mirror is the local player's, so split-screen gets no NR moodles. The own column is NEVER anchored
-- to the vanilla stack, reads cached levels only (#2692), sits on the UI manager only while a level is above 0, and
-- takes no mouse event, so it never eats a click meant for the world. At 48 px vanilla moodles it overlaps the stack
-- by 2 px, and a repositioner mod may overlap it.
-- Driven by NR.client.view.listeners after every rebuild; this file sorts before _View, so it creates
-- NR.client.view = { listeners = {} } when absent. The moodles and level-1 options are read on each apply.
-- The sentinel NR_ClientMoodles_Installed holds the five closures; probe(cls) is TEST-ONLY for the driver.
local NR = NutritionRevamp

NR_ClientMoodles_Installed = NR_ClientMoodles_Installed or {}

NR.client.moodles = {
    route = "none",
    classes = { "deficiency", "excess", "stimulant", "sleep", "overfull" },
    stats = { sets = 0, skips = 0, renders = 0, errors = 0, created = 0, got = 0, columns = 0 },
    levels = { deficiency = 0, excess = 0, stimulant = 0, sleep = 0, overfull = 0 },
    handles = {},
    column = nil,
    cls = nil,
    enabled = true,
    lastDrawn = 0,
    lastError = nil,
}
local MOODLES = NR.client.moodles

local PREFIX = "NR_" -- the framework moodle names, NR_<class> (#2556: no collision with the corpus)
local ICON_DIR = "media/ui/NutritionRevamp/" -- the mod's icons, <class>.png
local NEUTRAL = 0.5 -- the framework's neutral value when the kernel is absent (K.view.MOODLE_NEUTRAL)
local BAD = 2 -- MF_ISMoodle.lua:123 (the framework's bad polarity index; a symptom is a bad moodle)
local INSET_RIGHT = 96 -- px from the viewport's right edge: the column spans 1184-1224 on 1280
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
    deficiency = { 0.85, 0.25, 0.25 },
    excess = { 0.75, 0.35, 0.85 },
    stimulant = { 0.95, 0.85, 0.25 },
    sleep = { 0.45, 0.45, 0.80 },
    overfull = { 0.80, 0.45, 0.20 },
}

local call = NR.try

local function fail(err)
    NR.fail(NutritionRevamp.client.moodles, "moodles", err)
end

-- default when absent, raising or not a number.
local function screen(fn, playerNum, default)
    if fn == nil then return default end
    local ok, v = pcall(fn, playerNum)
    if ok and type(v) == "number" then return v end
    return default
end

-- nil when the function is absent, raises or finds nothing (#2489).
local function texture(path)
    if getTexture == nil then return nil end
    local ok, t = pcall(getTexture, path)
    if ok then return t end
    return nil
end

local text = NR.text

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
            o.wantMouseEvents = false -- onMouseUp and onMouseDown answer consumeMouseEvents when no handler answers
            return o
        end

        -- A right-button handler that answers nil consumes the click, so these answer false and a click or the wheel
        -- over the column reaches the world.
        function cls:onRightMouseDown(x, y) return false end
        function cls:onRightMouseUp(x, y) return false end
        function cls:onMouseWheel(del) return false end

        function cls:render()
            local ok, err = pcall(NutritionRevamp.client.moodles.renderColumn, self)
            if not ok then fail(err) end
        end
    end
end

-- true when absent or raising.
function MOODLES.isEnabled()
    local m = NutritionRevamp.client.modOptions
    if m == nil or m.moodles == nil then return true end
    local ok, v = pcall(m.moodles)
    if ok and v == false then return false end
    return true
end

-- true (shown, the default) when absent or raising.
function MOODLES.levelOneShown()
    local m = NutritionRevamp.client.modOptions
    if m == nil or m.moodleLevelOne == nil then return true end
    local ok, v = pcall(m.moodleLevelOne)
    if ok and v == false then return false end
    return true
end

-- The caller holds the pcall.
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

-- So an empty column holds no strip of the screen.
local function anyLevel(M)
    for i = 1, #M.classes do
        local lv = M.levels[M.classes[i]]
        if type(lv) == "number" and lv > 0 then return true end
    end
    return false
end

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

local function inset(playerNum)
    local left = screen(getPlayerScreenLeft, playerNum, 0)
    local top = screen(getPlayerScreenTop, playerNum, 0)
    local width = screen(getPlayerScreenWidth, playerNum, SCREEN_W)
    return left + width - INSET_RIGHT, top + INSET_TOP
end

function MOODLES.onResolutionChange()
    local col = NutritionRevamp.client.moodles.column
    if col == nil then return end
    local x, y = inset(col.playerNum)
    call(col, "setX", x)
    call(col, "setY", y)
end

-- A respawn's old column leaves the UI manager first.
function MOODLES.buildColumn(playerNum)
    local M = NutritionRevamp.client.moodles
    local cls = M.cls
    if cls == nil then return nil end
    local old = M.column
    if old ~= nil then
        showColumn(old, false)
        M.column = nil
    end
    local x, y = inset(playerNum)
    local col = cls:new(x, y, COL_WIDTH, #M.classes * SLOT, playerNum)
    for i = 1, #M.classes do
        local c = M.classes[i]
        col.textures[c] = texture(ICON_DIR .. c .. ".png")
    end
    call(col, "initialise")
    call(col, "instantiate")
    M.column = col
    M.stats.columns = M.stats.columns + 1
    showColumn(col, M.isEnabled() and anyLevel(M))
    return col
end

-- Thresholds passed bad4..bad1 in setThresholds' own order.
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

-- The OnCreatePlayer handler is added after the framework's builders, which createMoodle has just added.
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

-- The own column's kept levels go to zero until the next apply, as the framework suspends its moodles on death.
function MOODLES.onPlayerDeath(player)
    local ok, present, pn = pcall(NutritionRevamp.call, player, "getPlayerNum")
    if ok and present and type(pn) == "number" and pn ~= 0 then return end
    local M = NutritionRevamp.client.moodles
    for i = 1, #M.classes do
        M.levels[M.classes[i]] = 0
    end
    if M.route == "own" then showColumn(M.column, false) end
end

-- Player 0 only; the last known levels are set again (the view's classes when it has them).
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

-- stats.sets counts each class written, stats.skips a missing handle or a non-table.
function MOODLES.apply(classes)
    local M = NutritionRevamp.client.moodles
    if type(classes) ~= "table" then
        M.stats.skips = M.stats.skips + 1
        return false
    end
    local on = M.isEnabled()
    M.enabled = on
    local hideOne = not M.levelOneShown()
    local V = kview()
    for i = 1, #M.classes do
        local c = M.classes[i]
        local lv = classes[c]
        if type(lv) ~= "number" then lv = 0 end
        if V ~= nil then lv = V.shownLevel(c, lv, hideOne) end
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
    if M.route == "own" then showColumn(M.column, on and anyLevel(M)) end
    return true
end

-- TEST-ONLY (the driver's lua.call): the class level, whether it is on the UI manager, and the route.
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

if S.resolution == nil and Events ~= nil and Events.OnResolutionChange ~= nil then
    S.resolution = function()
        local nr = NutritionRevamp
        if nr == nil or nr.client == nil or nr.client.moodles == nil then return end
        local ok, err = pcall(nr.client.moodles.onResolutionChange)
        if not ok then fail(err) end
    end
    Events.OnResolutionChange.Add(S.resolution)
end

if S.boot == nil and Events ~= nil and Events.OnGameBoot ~= nil then
    S.boot = function()
        local nr = NutritionRevamp
        if nr == nil or nr.client == nil or nr.client.moodles == nil then return end
        local ok, err = pcall(nr.client.moodles.onGameBoot)
        if not ok then fail(err) end
    end
    Events.OnGameBoot.Add(S.boot)
end
