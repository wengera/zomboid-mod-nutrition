-- NR_Client_ModOptions.lua -- the mod's one PZAPI.ModOptions page (Plan 7 Task 5, ruling 7): the panel keybind
-- (togglePanel), the tooltip-lines tick and the moodles tick; the loader the mod calls once itself; the three
-- accessors every surface reads; and NR.client.text, the one translation lookup every client file goes through
-- (ruling 12).
--
-- The page exists at FILE SCOPE (#2520: a row added after the main screen is built is not a known key until the
-- next one) and is loaded by the mod ONCE, after the page exists, inside a protected call (#2519: vanilla loads
-- ModOptions.ini only as the main screen is built, and a load applies a saved value only to a page that exists).
-- The vanilla API read (READ-ONLY, media/lua/client/PZAPI/ModOptions.lua on 42.20.4): PZAPI.ModOptions:create(id,
-- name) :247; Options:addTickBox(id, name, value, tooltip) :64; Options:addKeyBind(id, name, key, tooltip) :182;
-- option:getValue() (a tick's value, a bind's key); PZAPI.ModOptions:load() :292.
--
-- The default key is the semicolon: Keyboard.KEY_SEMICOLON, the LWJGL code 39 -- read from the jar on 42.20.4
-- (org/lwjglx/input/Keyboard.class, the ConstantValue of the static field KEY_SEMICOLON = 39 by a constant-pool
-- parse; KEY_K = 37). `;` is unbound in shared/keyBinding.lua and read by no media/lua/client handler outside debug
-- files; K is vanilla's Display FPS at keyBinding.lua:198. The code is named in one place (KEY_DEFAULT_CODE).
--
-- The research's minimal shape 1 (docs/superpowers/research/platform-client-ui.md), read in x183:
--  risk 1: ISLayoutManager.RegisterWindow restoring visible=true re-adds the panel before the key was ever pressed
--          (DefaultRestoreWindow's addToUIManager; NR_Client_Panel.lua records it on stats.restoredVisible) -- the
--          first registration measured (#3215); a saved visible=true line's restore unmeasured;
--  risk 2: whether layout.ini is written at all on the harness client's exit path -- measured in x183 (#3216 the layout write at the quit; #3218 the load 1 / 0 failures);
--  risk 3: whether PZAPI.ModOptions:load() called this early (OnGameStart) finds ModOptions.ini -- measured in x183 (#3216 the layout write at the quit; #3218 the load 1 / 0 failures).
--
-- Shape (the client-file discipline):
--  * Load order inside client/ is by path (#1055): _Mirror, _ModOptions, _Moodles, _Options, _Panel, _Tab,
--    _Tooltip, _View. NR_Client_Options.lua loads AFTER this file and merges mode and logLevel into the existing NR.client.options
--    table (never replacing it), so the accessors attach() sets at file scope stay; attach() runs again from this
--    file's OnGameStart handler, and the accessors read the page through the global sentinel per call, never
--    through a handle captured on NR.client.
--  * The sentinels are globals of their own (#0943: NR_Core re-creates NutritionRevamp on every load):
--    NR_ClientModOptions_Page (the page), NR_ClientModOptions_Loaded (the one load), NR_ClientModOptions_Installed
--    (the one OnGameStart listener closure, which looks NutritionRevamp up per call).
--  * Every engine and toolkit member is reached index-first inside a pcall (#0935, #1072); the file loads with no
--    engine (testing/tests/kernel/test_client_view_shape.py).
-- Cadence: the page once per Lua state; the accessors once per key press or per draw that reads them.
local NR = NutritionRevamp

-- The translation lookup (ruling 12). key's string from getText, or on a miss -- getText absent, raising, answering
-- nil, a non-string or the key itself -- the fallback; when the fallback is nil or the key itself, the key's TAIL:
-- the key with UI_NR_ (or IGUI_NR_ / Moodles_NR_) and a leading Row_ stripped and every _ read as a space, so a
-- surface is readable before the translation files ship (UI_NR_Class_energy_2 reads "Class energy 2").
-- Defined defensively (only when absent) so whichever client file loads first may call it.
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

-- The defaults, read when the page or its option is absent or getValue raises.
local KEY_DEFAULT_CODE = 39 -- the LWJGL code of the semicolon (Keyboard.KEY_SEMICOLON on 42.20.4, read from the jar; see the header)

NR_ClientModOptions_Installed = NR_ClientModOptions_Installed or {}

-- Keyboard.KEY_SEMICOLON behind a nil check; KEY_DEFAULT_CODE when the class is absent.
local function defaultKey()
    if Keyboard == nil then return KEY_DEFAULT_CODE end
    local ok, k = pcall(function() return Keyboard.KEY_SEMICOLON end)
    if ok and type(k) == "number" then return k end
    return KEY_DEFAULT_CODE
end

-- One option row added through the page's method name, index-first inside a pcall; the handle or nil.
local function addRow(page, method, id, label, value, tip)
    local ok, present, handle = pcall(NR.call, page, method, id, label, value, tip)
    if ok and present then return handle end
    return nil
end

-- The page, once per Lua state (the sentinel global NR_ClientModOptions_Page). A file-scope call.
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
    return page
end

-- The option handle id on the page, or nil: page.dict[id] (Options:getOption reads the same table).
local function option(id)
    local page = NR_ClientModOptions_Page
    if page == nil then return nil end
    local ok, h = pcall(function() return page.dict[id] end)
    if ok then return h end
    return nil
end

-- getValue of option id, index-first inside a pcall; nil on any failure.
local function value(id)
    local h = option(id)
    if h == nil then return nil end
    local ok, present, v = pcall(NR.call, h, "getValue")
    if ok and present then return v end
    return nil
end

-- The accessors and the loader, kept in a table no other file assigns, then copied onto NR.client.options.
NR.client.modOptions = {
    stats = { loads = 0, loadFailures = 0 },
}
local MO = NR.client.modOptions

-- The panel key code: the bind's value when it is a number, else the default semicolon.
function MO.key()
    local v = value("togglePanel")
    if type(v) == "number" then return v end
    return defaultKey()
end

-- Whether the tooltip band draws: the tick's value when it is a boolean, else true.
function MO.tooltipLines()
    local v = value("tooltipLines")
    if type(v) == "boolean" then return v end
    return true
end

-- Whether the moodles show: the tick's value when it is a boolean, else true.
function MO.moodles()
    local v = value("moodles")
    if type(v) == "boolean" then return v end
    return true
end

-- PZAPI.ModOptions:load() once per Lua state, after the page exists (#2519), inside a pcall. true when this call
-- loaded; false when it had already run, there is no page, or the API is absent.
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

-- Copies the accessors onto NR.client.options (the table NR_Client_Options.lua merges into after this file loads).
function MO.attach()
    local nr = NutritionRevamp
    if nr == nil or nr.client == nil or nr.client.modOptions == nil then return end
    nr.client.options = nr.client.options or {}
    local o = nr.client.options
    local m = nr.client.modOptions
    o.key = m.key
    o.tooltipLines = m.tooltipLines
    o.moodles = m.moodles
    o.loadOnce = m.loadOnce
    o.page = NR_ClientModOptions_Page
    o.toggleKey = option("togglePanel")
    o.tooltipLinesOption = option("tooltipLines")
    o.moodlesOption = option("moodles")
end

-- The OnGameStart listener's logic: re-attach, then the one load.
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
