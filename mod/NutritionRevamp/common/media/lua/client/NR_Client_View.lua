-- NR_Client_View.lua -- the client's one row cache and the draw helper every surface shares: the visibility level, the
-- rows K.view.rows builds from the stored mirror, and the five moodle class levels. The mirror is read at the push
-- cadence, never the frame cadence (#2692): refresh() makes one compare per frame and rebuilds only when the arrival
-- counter or the level moved, resolving every text then, so draw() calls no getText per frame.
-- Trait tests compare the registry object through hasTrait (#0550). The band row is the mirror's body_band, a server
-- value, never the client's trait list. The grade rows list K.view.gradedOrder, never the raw ORDER.
-- view.listeners are called after every rebuild under their own pcall; NR_Client_Moodles sorts first and may create
-- NR.client.view itself, so this file carries an existing listeners array over.
-- The sentinel NR_ClientView_Installed holds the two closures; every Java global is named only behind a nil check.
local NR = NutritionRevamp
local prior = NR.client.view
NR.client.view = {
    level = 2,
    optionLevel = 2,
    hasTrait = false,
    isFemale = false,
    female = false,
    fatBand = nil,
    rows = nil,
    classes = nil,
    order = nil,
    ungraded = nil,
    def = nil,
    lastReceived = -1,
    lastLevel = -1,
    listeners = {},
    stats = { rebuilds = 0, traitReads = 0, listenerErrors = 0, errors = 0, overflowRows = 0 },
    lastError = nil,
}
local V = NR.client.view
if prior ~= nil and type(prior.listeners) == "table" then V.listeners = prior.listeners end

NR_ClientView_Installed = NR_ClientView_Installed or {}

local DEFAULT_LINE = 14 -- px: the line height when the text manager is absent or raises

local text = NR.text

-- false on a nil player, an absent enum or any failure.
function V.readTrait(player)
    V.stats.traitReads = V.stats.traitReads + 1
    if player == nil or CharacterTrait == nil then return false end
    local okE, a, b = pcall(function() return CharacterTrait.NUTRITIONIST, CharacterTrait.NUTRITIONIST2 end)
    if not okE then return false end
    local enums = { a, b }
    for i = 1, 2 do
        local enum = enums[i]
        if enum ~= nil then
            local ok, present, has = pcall(NR.call, player, "hasTrait", enum)
            if ok and present and has == true then return true end
        end
    end
    return false
end

-- Unreadable keeps the last answer.
function V.readFemale(player)
    if player == nil then return V.isFemale end
    local ok, present, v = pcall(NR.call, player, "isFemale")
    if ok and present and type(v) == "boolean" then return v end
    return V.isFemale
end

-- Missing or unreadable reads false, the option's default, so every character reads the male values.
function V.readSexSpecific()
    if SandboxVars == nil then return false end
    local ok, v = pcall(function() return SandboxVars.NR.SexSpecific end)
    return ok and v == true
end

-- 1 Symptoms, 2 Bands, 3 Numbers; a missing or non-number value reads 2, the default.
function V.readOption()
    if SandboxVars == nil then return 2 end
    local ok, v = pcall(function() return SandboxVars.NR.VisibilityMode end)
    if ok and type(v) == "number" then return v end
    return 2
end

local function levelOf(optionLevel, hasTrait)
    local K = NutritionRevamp.kernel
    if K == nil or K.view == nil then return 2 end
    return K.view.level(optionLevel, hasTrait)
end

-- Once, at rebuild, so draw() resolves nothing per frame.
local function resolveRows(rows)
    for i = 1, #rows do
        local r = rows[i]
        r.labelText = text(r.label, nil)
        if r.isKey then
            r.valueText = text(r.text, r.text)
        else
            r.valueText = r.text or ""
        end
    end
end

local function rebuild(received)
    local nr = NutritionRevamp
    local K = nr.kernel
    if V.order == nil and nr.data ~= nil and nr.data.records ~= nil then
        V.order = K.view.gradedOrder(nr.data.records)
        V.ungraded = K.view.ungradedOrder(nr.data.records)
    end
    if V.def == nil then
        V.def = K.view.deficiencyKeys(nr.data and nr.data.effects)
    end
    local m = nr.client.mirror
    local rows = K.view.rows(m, V.level, V.order, { female = V.female, last = V.fatBand }, V.ungraded, V.def)
    V.fatBand = nil
    for i = 1, #rows do
        if rows[i].key == "body_fat" then V.fatBand = rows[i].fatBand end
    end
    resolveRows(rows)
    V.rows = rows
    V.lh = nil -- the font metrics are read again at the next draw, once per rebuild (V.metrics)
    V.classes = K.view.moodleClasses(m, V.def)
    V.lastReceived = received
    V.lastLevel = V.level
    V.stats.rebuilds = V.stats.rebuilds + 1
    for i = 1, #V.listeners do
        local ok, err = pcall(V.listeners[i], V.classes, V.rows, V.level)
        if not ok then
            V.stats.listenerErrors = V.stats.listenerErrors + 1
            V.lastError = err
        end
    end
end

-- true when it rebuilt.
function V.refresh(force)
    local nr = NutritionRevamp
    local K = nr.kernel
    if K == nil or K.view == nil then return false end
    local received = nr.client.received or 0
    if force ~= true and not K.view.changed(received, V.lastReceived, V.level, V.lastLevel) then return false end
    local ok, err = pcall(rebuild, received)
    if not ok then
        V.stats.errors = V.stats.errors + 1
        V.lastError = err
        NR.log.say(2, "view: rebuild failed: " .. tostring(err))
        V.lastReceived = received
        V.lastLevel = V.level
        return false
    end
    return true
end

function V.recompute(player)
    V.hasTrait = V.readTrait(player)
    V.isFemale = V.readFemale(player) -- the engine's sex, kept raw
    V.female = V.isFemale and V.readSexSpecific()
    V.optionLevel = V.readOption()
    local before = V.level
    V.level = levelOf(V.optionLevel, V.hasTrait)
    return V.level ~= before
end

function V.onMirror()
    local p = nil
    if getPlayer ~= nil then
        local okP, pl = pcall(getPlayer)
        if okP then p = pl end
    end
    V.recompute(p)
    V.refresh(false)
end

function V.onCreatePlayer(playerNum, player)
    if not NR.isClient() then return end
    if playerNum ~= nil and playerNum ~= 0 then return end
    local ok, err = pcall(V.recompute, player)
    if not ok then
        V.stats.errors = V.stats.errors + 1
        V.lastError = err
    end
end

-- Split-screen player 1's death keeps player 0's view. The view rebuilds empty, so the moodles clear and a respawn
-- shows none of the dead character's rows until the server's first push.
function V.onPlayerDeath(player)
    local nr = NutritionRevamp
    if not nr.isClient() then return end
    local ok, present, pn = pcall(NR.call, player, "getPlayerNum")
    if ok and present and type(pn) == "number" and pn ~= 0 then return end
    nr.client.clearMirror()
    V.refresh(true)
end

function V.lineHeight(font)
    if getTextManager == nil or font == nil then return DEFAULT_LINE end
    local ok, h = pcall(function() return getTextManager():getFontHeight(font) end)
    if ok and type(h) == "number" and h > 0 then return h end
    return DEFAULT_LINE
end

function V.smallFont()
    if UIFont == nil then return nil end
    local ok, f = pcall(function() return UIFont.Small end)
    if ok then return f end
    return nil
end

-- Kept until the next rebuild or resolution change: a frame's draws read two fields and call no engine.
function V.metrics()
    if V.lh == nil then
        V.font = V.smallFont()
        V.lh = V.lineHeight(V.font)
    end
    return V.font, V.lh
end

function V.onResolutionChange()
    V.lh = nil
end

-- WHEEL_LINES rows a notch; scrollBy answers true (the event taken) only when there is overflow to scroll.
V.WHEEL_LINES = 3

function V.overflow(n, lh, room)
    local over = n * lh - room
    if over < 0 then over = 0 end
    return over
end

function V.clampScroll(y, over)
    if y > over then y = over end
    if y < 0 then y = 0 end
    return y
end

function V.scrollBy(el, del, over)
    if type(del) ~= "number" or over <= 0 then return false end
    local _, lh = V.metrics()
    el.scrollY = V.clampScroll((el.scrollY or 0) + V.WHEEL_LINES * lh * del, over)
    return true
end

-- Stops before a line would pass maxY and skips a row above minY, because the vanilla window clears its stencil
-- before the subclass render. The caller holds the pcall. Returns the y after the last row drawn.
function V.draw(el, rows, x, y, w, font, maxY, minY)
    if el == nil or rows == nil then return y end
    local f, lh = font, nil
    if f == nil or f == V.font then
        f, lh = V.metrics()
    else
        lh = V.lineHeight(f)
    end
    local drawLeft = el.drawText
    local drawRight = el.drawTextRight
    if drawLeft == nil or drawRight == nil then return y end
    local yy = y
    for i = 1, #rows do
        if maxY ~= nil and yy + lh > maxY then
            return yy
        end
        local r = rows[i]
        if minY ~= nil and yy < minY then
            yy = yy + lh
            r = nil
        end
        if r ~= nil then
            local label = r.labelText
            if label == nil then label = text(r.label, nil) end
            local value = r.valueText
            if value == nil then
                value = r.text or ""
                if r.isKey then value = text(r.text, r.text) end
            end
            local cr, cg, cb = 1, 1, 1
            if r.cls ~= nil and type(r.n) == "number" and r.n > 0 then
                cr, cg, cb = 1, 0.75, 0.35 -- an amber class word above level 0
            end
            drawLeft(el, label, x, yy, 1, 1, 1, 1, f)
            drawRight(el, value, x + w, yy, cr, cg, cb, 1, f)
            yy = yy + lh
        end
    end
    return yy
end

if NR_ClientView_Installed.create == nil and Events ~= nil and Events.OnCreatePlayer ~= nil then
    NR_ClientView_Installed.create = function(playerNum, player)
        local nr = NutritionRevamp
        if nr == nil or nr.client == nil or nr.client.view == nil then return end
        pcall(nr.client.view.onCreatePlayer, playerNum, player)
    end
    Events.OnCreatePlayer.Add(NR_ClientView_Installed.create)
end
if NR_ClientView_Installed.death == nil and Events ~= nil and Events.OnPlayerDeath ~= nil then
    NR_ClientView_Installed.death = function(player)
        local nr = NutritionRevamp
        if nr == nil or nr.client == nil or nr.client.view == nil then return end
        local ok, err = pcall(nr.client.view.onPlayerDeath, player)
        if not ok then
            nr.client.view.stats.errors = nr.client.view.stats.errors + 1
            nr.client.view.lastError = err
        end
    end
    Events.OnPlayerDeath.Add(NR_ClientView_Installed.death)
end
