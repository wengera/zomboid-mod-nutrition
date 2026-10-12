-- NR_Client_View.lua -- the client's one row cache and the draw helper every surface shares (Plan 7 Task 5,
-- rulings 3, 5 and 16): the visibility level (max of the server option NR.VisibilityMode and a Nutritionist
-- trait), the row model K.view.rows builds from the stored mirror, the seven moodle class levels
-- K.view.moodleClasses reads (the six classes and overfull, Plan 11c Task 7), and view.draw, which paints a row list
-- onto any ISUIElement.
--
-- The mirror is read at the push cadence, never the frame cadence (#2692): refresh() makes the one per-frame test
-- K.view.changed(received, lastReceived, level, lastLevel) and rebuilds only when the arrival counter
-- NR.client.received or the level moved; the rebuild resolves every label and text through NR.client.text then, so
-- draw() walks the cached rows and calls no getText per frame. Nothing here walks the mirror in a render.
-- The level is recomputed on each mirror arrival (view.onMirror, called by one guarded line in NR_Client_Mirror.lua's
-- OnServerCommand handler after the install) and on OnCreatePlayer, never per frame (ruling 3). Trait tests compare
-- the registry object through hasTrait (#0550, #0551, #1162), behind a nil check on each enum.
-- The panel never shows a band label read from the client's trait list (ruling 16): the band row is the mirror's
-- body_band, a server value, and the trait read here is the Nutritionist test alone.
-- The grade rows list K.view.gradedOrder(NR.data.records), never the raw ORDER (the ungraded kinds would list a
-- replete grade and pool figures); cached on view.order at the first rebuild that has the records.
--
-- view.listeners is an array of functions, each called as fn(classes, rows, level) under its own pcall after every
-- rebuild (Task 8 appends the moodles' hook). A file that loads before this one (NR_Client_Moodles sorts first) may
-- create NR.client.view = { listeners = {} } itself: this file carries an existing listeners array over.
--
-- Shape (the client-file discipline): the sentinel NR_ClientView_Installed is a global of its own holding
-- the one OnCreatePlayer closure, which looks NutritionRevamp.client.view up per call; the side test is per call;
-- every Java global (getPlayer, CharacterTrait, SandboxVars, getTextManager, UIFont) is named only inside a function
-- behind a nil check, so the file loads with no engine (testing/tests/kernel/test_client_view_shape.py); every
-- handler body runs under one pcall. No @fastpath region: refresh's per-frame cost is one compare.
local NR = NutritionRevamp
local prior = NR.client.view
NR.client.view = {
    level = 2,
    optionLevel = 2,
    hasTrait = false,
    rows = nil,
    classes = nil,
    order = nil,
    lastReceived = -1,
    lastLevel = -1,
    listeners = {},
    stats = { rebuilds = 0, traitReads = 0, listenerErrors = 0, errors = 0, overflowRows = 0 },
    lastError = nil,
}
local V = NR.client.view
if prior ~= nil and type(prior.listeners) == "table" then V.listeners = prior.listeners end

NR_ClientView_Installed = NR_ClientView_Installed or {}

local DEFAULT_LINE = 14 -- px: the line height when the text manager is absent or raises (plan Task 5)

-- A translation through NR.client.text when it exists (NR_Client_ModOptions.lua), else the fallback or the key.
local function text(key, fallback)
    local nr = NutritionRevamp
    if nr.client.text ~= nil then return nr.client.text(key, fallback) end
    if fallback ~= nil then return fallback end
    return key
end

-- Whether player holds either Nutritionist trait: CharacterTrait.NUTRITIONIST / NUTRITIONIST2 (each nil-checked)
-- through player:hasTrait(enum), index-first inside a pcall. false on a nil player, an absent enum or any failure.
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

-- The server option SandboxVars.NR.VisibilityMode (1 Symptoms, 2 Bands, 3 Numbers); a missing or non-number value
-- reads 2, Bands, the option's default (ruling T13-1). K.view.level clamps it.
function V.readOption()
    if SandboxVars == nil then return 2 end
    local ok, v = pcall(function() return SandboxVars.NR.VisibilityMode end)
    if ok and type(v) == "number" then return v end
    return 2
end

-- The level from the option and the trait (K.view.level), or 2 (the default, Bands) when the kernel is absent.
local function levelOf(optionLevel, hasTrait)
    local K = NutritionRevamp.kernel
    if K == nil or K.view == nil then return 2 end
    return K.view.level(optionLevel, hasTrait)
end

-- Resolves every row's label and text once, at rebuild: labelText through text(label, nil), the key's tail, valueText through
-- text(text, text) when the row's text is a key (isKey), else the formatted string as it is.
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

-- The rebuild: the graded order (cached), the rows at the current level, the classes, the stamps, the listeners.
local function rebuild(received)
    local nr = NutritionRevamp
    local K = nr.kernel
    if V.order == nil and nr.data ~= nil and nr.data.records ~= nil then
        V.order = K.view.gradedOrder(nr.data.records)
    end
    local m = nr.client.mirror
    local rows = K.view.rows(m, V.level, V.order)
    resolveRows(rows)
    V.rows = rows
    V.classes = K.view.moodleClasses(m)
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

-- The one per-frame test: rebuild only when the mirror's arrival counter or the level moved (or force). true when
-- it rebuilt.
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

-- The level from the stored option and trait; true when it moved.
function V.recompute(player)
    V.hasTrait = V.readTrait(player)
    V.optionLevel = V.readOption()
    local before = V.level
    V.level = levelOf(V.optionLevel, V.hasTrait)
    return V.level ~= before
end

-- A mirror arrived (NR_Client_Mirror.lua's handler, after the install): re-read the trait and the option, then
-- refresh (the counter moved, so it rebuilds).
function V.onMirror()
    local p = nil
    if getPlayer ~= nil then
        local okP, pl = pcall(getPlayer)
        if okP then p = pl end
    end
    V.recompute(p)
    V.refresh(false)
end

-- OnCreatePlayer: the local player's trait and the option level (player 0 only; the mirror is the local
-- player's).
function V.onCreatePlayer(playerNum, player)
    if not NR.isClient() then return end
    if playerNum ~= nil and playerNum ~= 0 then return end
    local ok, err = pcall(V.recompute, player)
    if not ok then
        V.stats.errors = V.stats.errors + 1
        V.lastError = err
    end
end

-- The line height of font through getTextManager():getFontHeight(font), guarded; DEFAULT_LINE on any failure.
function V.lineHeight(font)
    if getTextManager == nil or font == nil then return DEFAULT_LINE end
    local ok, h = pcall(function() return getTextManager():getFontHeight(font) end)
    if ok and type(h) == "number" and h > 0 then return h end
    return DEFAULT_LINE
end

-- UIFont.Small behind a nil check, or nil.
function V.smallFont()
    if UIFont == nil then return nil end
    local ok, f = pcall(function() return UIFont.Small end)
    if ok then return f end
    return nil
end

-- Draws rows onto el: each row's label left at x and its text right-aligned at x + w, one line apart from y, in
-- font (nil: UIFont.Small); stops before a line would pass maxY (nil: no limit; the panel counts the rows left out
-- once per rebuild, in stats.overflowRows); skips a row whose top sits above minY (nil: no clip), the scrolled
-- panel's top clip, because the vanilla window clears its stencil before the subclass render (ISCollapsableWindow.lua:193-195).
-- Returns the y after the last row drawn. The caller holds the pcall (a render body); the row strings were
-- resolved at rebuild, and a row built elsewhere is resolved here.
function V.draw(el, rows, x, y, w, font, maxY, minY)
    if el == nil or rows == nil then return y end
    local f = font
    if f == nil then f = V.smallFont() end
    local lh = V.lineHeight(f)
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
