-- TKX_MF (X29) -- registers one MoodleFramework moodle "TKX" and records what it does. Client only.
-- Names read off the live tree on 2026-10-06, D:\SteamLibrary\steamapps\workshop\content\108600\3396446795\mods\MoodleFramework\
-- (folders 42.0, 42.13, 42.20, common; 42.20/ holds only media/lua/client/MF_ISMoodle.lua, the file the engine runs):
--   (a) the UI-manager flag is the instance field `addedToUIManager`, set true at MF_ISMoodle.lua:104 and false at :108 inside :setValue (:102-109);
--       the plan's guess `addedToUIManager` is right.
--   (b) `moodle:getLevel()` at MF_ISMoodle.lua:127 (0..4) and `moodle:getGoodBadNeutral()` at :120 (1 good, 2 bad, 0 neutral); both read :getValue() (:114).
--   (c) `moodle:setValue(value)` at MF_ISMoodle.lua:83 (a method, colon call; no range check).
--   (d) `MF.getMoodle(moodleName, playerNum)` at MF_ISMoodle.lua:35 takes the player number as an optional second argument;
--       when nil it falls back to getPlayer():getPlayerNum() (or 0); it returns nil until the framework's own OnCreatePlayer handler has built the widget (:29, :500).
--   (e) `MF.key = "MoodleFramework"` is set at common/media/lua/client/MF_Config.lua:4 (42.20/ ships no config file; MF_Config.lua exists in 42.0/ and common/ only).
-- Rules: every Java and framework member is index-first inside pcall (the framework has no pcall of its own and the -debug client parks on a raise);
-- no file-scope call but Events.*.Add behind nil checks; the poll early-outs on one modData string compare.
-- Reading: set the client player-modData key TKX_mf with `moddata.set TKX_mf <v>` and read the global TKX_MF with `lua.global`.

TKX_MF = {
    detected = false,
    created = false,
    cfgKey = nil,
    renders = 0,
    ownRenders = 0,
    level = nil,
    gbn = nil,
    onUI = nil,
    lastSet = nil,
    moodle = nil,
    own = nil,
    ownOnUI = false,
    moodleFound = false,
    moodlesUI = false,
    stackBox = nil,
    errors = 0,
    lastError = nil,
}

local function fail(where, err)
    TKX_MF.errors = TKX_MF.errors + 1
    TKX_MF.lastError = tostring(where) .. ": " .. tostring(err)
end

local function detect()
    local ok, err = pcall(function()
        TKX_MF.detected = (type(MF) == "table" and type(MF.createMoodle) == "function")
        if type(MF) == "table" then TKX_MF.cfgKey = MF.key end
    end)
    if not ok then fail("detect", err) end
end

local function wrapRender(moodle)
    if TKX_MF_Wrapped ~= nil then return end
    if moodle == nil then return end
    local original = moodle.render
    if type(original) ~= "function" then return end
    TKX_MF_Wrapped = true
    moodle.render = function(self, ...)
        TKX_MF.renders = TKX_MF.renders + 1
        return original(self, ...)
    end
end

local function buildOwn()
    if TKX_MF.own ~= nil then return end
    if ISUIElement == nil then return end
    if type(ISUIElement.derive) ~= "function" then return end
    local cls = ISUIElement:derive("TKX_MFOwn")
    cls.render = function(self)
        TKX_MF.ownRenders = TKX_MF.ownRenders + 1
        if self.drawRect ~= nil then pcall(self.drawRect, self, 0, 0, 40, 40, 0.8, 1, 0, 1) end
    end
    local inst = cls:new(10, 300, 40, 40)
    if inst == nil then return end
    inst:initialise()
    inst:instantiate()
    inst:addToUIManager()
    TKX_MF.own = inst
    TKX_MF.ownOnUI = true
end

local function readStackBox()
    if MoodlesUI == nil then return end
    TKX_MF.moodlesUI = true
    if type(MoodlesUI.getInstance) ~= "function" then return end
    local ui = MoodlesUI.getInstance()
    if ui == nil then return end
    local box = {}
    if ui.getX ~= nil then box.x = ui:getX() end
    if ui.getY ~= nil then box.y = ui:getY() end
    if ui.getWidth ~= nil then box.w = ui:getWidth() end
    if ui.getHeight ~= nil then box.h = ui:getHeight() end
    TKX_MF.stackBox = box
end

local function onCreatePlayer(playerNum)
    local ok, err = pcall(function()
        if TKX_MF.detected and type(MF.getMoodle) == "function" then
            local m = MF.getMoodle("TKX", 0)
            if m ~= nil then
                TKX_MF.moodle = m
                TKX_MF.moodleFound = true
                wrapRender(m)
            end
        end
    end)
    if not ok then fail("moodle", err) end
    local ok2, err2 = pcall(buildOwn)
    if not ok2 then fail("own", err2) end
    local ok3, err3 = pcall(readStackBox)
    if not ok3 then fail("stackBox", err3) end
end

local function apply(v)
    local m = TKX_MF.moodle
    if m ~= nil and type(m.setValue) == "function" then
        m:setValue(tonumber(v))
        TKX_MF.level = m:getLevel()
        TKX_MF.gbn = m:getGoodBadNeutral()
        TKX_MF.onUI = m.addedToUIManager
    end
end

local function onPlayerUpdate(player)
    local ok, err = pcall(function()
        if player == nil or player.getModData == nil then return end
        local md = player:getModData()
        if md == nil then return end
        local v = md.TKX_mf
        if v == TKX_MF.lastSet then return end
        TKX_MF.lastSet = v
        if v == nil then return end
        apply(v)
    end)
    if not ok then fail("poll", err) end
end

local function onGameBoot()
    detect()
    if TKX_MF.detected then
        local ok, err = pcall(MF.createMoodle, "TKX")
        if ok then TKX_MF.created = true else fail("createMoodle", err) end
    end
    if TKX_MF_Events == nil and Events ~= nil then
        TKX_MF_Events = true
        if Events.OnCreatePlayer ~= nil then Events.OnCreatePlayer.Add(onCreatePlayer) end
        if Events.OnPlayerUpdate ~= nil then Events.OnPlayerUpdate.Add(onPlayerUpdate) end
    end
end

if Events ~= nil and Events.OnGameBoot ~= nil then Events.OnGameBoot.Add(onGameBoot) end
