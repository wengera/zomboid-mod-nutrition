-- NR_Client_ModOptions.lua -- the mod's one PZAPI.ModOptions page (the panel keybind and the tooltip, moodles and
-- level-1 moodles ticks, each a per-player client setting), its four accessors, and NR.client.text, the one
-- translation lookup every client file goes through.
-- The page exists at FILE SCOPE (#2520: a row added after the main screen is built is not a known key until the next
-- one) and is loaded by the mod ONCE, after the page exists, inside a pcall (#2519: a load applies a saved value only
-- to a page that exists).
-- The default key is the semicolon (LWJGL code 39, read from the jar): `;` is unbound in vanilla's keyBinding.lua.
-- The shapes and their risks: docs/platform/client-ui.md.
-- The sentinels are globals of their own (#0943: NR_Core re-creates NutritionRevamp on every load), and the accessors
-- read the page through them per call, never through a handle captured on NR.client.
local NR = NutritionRevamp

-- On a miss (getText absent, raising, nil, a non-string or the key itself) the fallback, else the key's TAIL with its
-- prefix stripped and every _ read as a space, so a surface is readable before the translations ship. Defined only
-- when absent, so whichever client file loads first may call it.
NR.client.tail = NR.client.tail or function(key)
    if type(key) ~= "string" then return tostring(key) end
    local t = string.gsub(key, "^UI_NR_", "")
    t = string.gsub(t, "^IGUI_NR_", "")
    t = string.gsub(t, "^Moodles_NR_", "")
    t = string.gsub(t, "^Row_", "")
    t = string.gsub(t, "_", " ")
    return t
end

NR.client.text = NR.client.text or function(key, fallback)
    local nr = NutritionRevamp
    local fb = fallback
    if fb == nil or fb == key then fb = nr.client.tail(key) end
    if type(key) ~= "string" or getText == nil then return fb end
    local ok, s = pcall(getText, key)
    if not ok or type(s) ~= "string" or s == key or s == "" then return fb end
    return s
end

local KEY_DEFAULT_CODE = 39 -- the LWJGL code of the semicolon (Keyboard.KEY_SEMICOLON, read from the jar)

NR_ClientModOptions_Installed = NR_ClientModOptions_Installed or {}

local function defaultKey()
    if Keyboard == nil then return KEY_DEFAULT_CODE end
    local ok, k = pcall(function() return Keyboard.KEY_SEMICOLON end)
    if ok and type(k) == "number" then return k end
    return KEY_DEFAULT_CODE
end

local function addRow(page, method, id, label, value, tip)
    local ok, present, handle = pcall(NR.call, page, method, id, label, value, tip)
    if ok and present then return handle end
    return nil
end

local function createPage()
    if NR_ClientModOptions_Page ~= nil then return NR_ClientModOptions_Page end
    if PZAPI == nil or PZAPI.ModOptions == nil or type(PZAPI.ModOptions.create) ~= "function" then return nil end
    local text = NR.client.text
    local ok, page = pcall(PZAPI.ModOptions.create, PZAPI.ModOptions, "NutritionRevamp", text("UI_NR_ModName", "Nutrition Revamp"))
    if not ok or page == nil then return nil end
    NR_ClientModOptions_Page = page
    addRow(page, "addKeyBind", "togglePanel", text("UI_NR_Toggle", "Toggle the nutrition panel"), defaultKey(), nil)
    addRow(page, "addTickBox", "tooltipLines", text("UI_NR_TooltipLines", "Nutrition lines on food tooltips"), true, nil)
    addRow(page, "addTickBox", "moodles", text("UI_NR_Moodles", "Nutrition moodles"), true, nil)
    addRow(page, "addTickBox", "moodleLevelOne", text("UI_NR_MoodleLevelOne", "Show level 1 of the Stimulant, Sleep and Excess moodles"), true, nil)
    -- The page's apply re-applies the moodles from the view's last classes, so the ticks take effect at once rather
    -- than at the next push.
    local base = page.apply
    page.apply = function(self, ...)
        if base ~= nil then base(self, ...) end
        local nr = NutritionRevamp
        if nr ~= nil and nr.client ~= nil and nr.client.modOptions ~= nil then
            pcall(nr.client.modOptions.onApply)
        end
    end
    return page
end

local function option(id)
    local page = NR_ClientModOptions_Page
    if page == nil then return nil end
    local ok, h = pcall(function() return page.dict[id] end)
    if ok then return h end
    return nil
end

local function value(id)
    local h = option(id)
    if h == nil then return nil end
    local ok, present, v = pcall(NR.call, h, "getValue")
    if ok and present then return v end
    return nil
end

-- Kept in a table no other file assigns, then copied onto NR.client.options.
NR.client.modOptions = {
    stats = { loads = 0, loadFailures = 0 },
}
local MO = NR.client.modOptions

function MO.key()
    local v = value("togglePanel")
    if type(v) == "number" then return v end
    return defaultKey()
end

function MO.tooltipLines()
    local v = value("tooltipLines")
    if type(v) == "boolean" then return v end
    return true
end

function MO.moodles()
    local v = value("moodles")
    if type(v) == "boolean" then return v end
    return true
end

function MO.moodleLevelOne()
    local v = value("moodleLevelOne")
    if type(v) == "boolean" then return v end
    return true
end

-- true when it applied.
function MO.onApply()
    local nr = NutritionRevamp
    local m, v = nr.client.moodles, nr.client.view
    if m == nil or type(m.apply) ~= "function" or v == nil or type(v.classes) ~= "table" then return false end
    m.apply(v.classes)
    return true
end

-- Once per Lua state, after the page exists (#2519). true when this call loaded.
function MO.loadOnce()
    if NR_ClientModOptions_Loaded ~= nil then return false end
    if NR_ClientModOptions_Page == nil then return false end
    if PZAPI == nil or PZAPI.ModOptions == nil or type(PZAPI.ModOptions.load) ~= "function" then return false end
    NR_ClientModOptions_Loaded = true
    local ok, err = pcall(PZAPI.ModOptions.load, PZAPI.ModOptions)
    if ok then
        MO.stats.loads = MO.stats.loads + 1
    else
        MO.stats.loadFailures = MO.stats.loadFailures + 1
        NR.log.say(2, "modoptions: load failed: " .. tostring(err))
    end
    return ok
end

function MO.attach()
    local nr = NutritionRevamp
    if nr == nil or nr.client == nil or nr.client.modOptions == nil then return end
    nr.client.options = nr.client.options or {}
    local o = nr.client.options
    local m = nr.client.modOptions
    o.key = m.key
    o.tooltipLines = m.tooltipLines
    o.moodles = m.moodles
    o.moodleLevelOne = m.moodleLevelOne
    o.loadOnce = m.loadOnce
    o.page = NR_ClientModOptions_Page
end

function MO.onGameStart()
    MO.attach()
    MO.loadOnce()
end

createPage()
MO.attach()

if NR_ClientModOptions_Installed.fn == nil and Events ~= nil and Events.OnGameStart ~= nil then
    NR_ClientModOptions_Installed.fn = function()
        local nr = NutritionRevamp
        if nr == nil or nr.client == nil or nr.client.modOptions == nil then return end
        local ok, err = pcall(nr.client.modOptions.onGameStart)
        if not ok then nr.log.say(2, "modoptions: game start failed: " .. tostring(err)) end
    end
    Events.OnGameStart.Add(NR_ClientModOptions_Installed.fn)
end
