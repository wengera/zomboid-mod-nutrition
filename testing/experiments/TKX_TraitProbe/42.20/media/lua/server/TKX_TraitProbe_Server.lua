-- TKX_TraitProbe server side (X4 registered-trait arm, X42 grant). An OnTick watcher reads two
-- player-modData keys:
--   TKX_grant  a string: a registry id (TKX:Probe, SWTraits:SWAdaptiveMetabolism) to add, or
--              -<id> to remove, or a bare vanilla static name (NIGHT_VISION). Read, acted on,
--              then cleared.
--   TKX_push   1 -> sendSyncPlayerFields(player, 2) (the trait block), then cleared.
-- Resolution: an id with a colon goes through CharacterTrait.get(ResourceLocation.of(id)); if
-- ResourceLocation is not a Lua global the fallback is CharacterTrait.get(id). A bare name uses
-- the static field CharacterTrait[name]. Every Java member is indexed before it is called.
-- This file also runs in the client Lua state, so the side test is made at event time.
local function tkxCall(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return pcall(m, obj, ...)
end

local function tkxIsServer()
    if isServer == nil then return false end
    local ok, s = pcall(isServer)
    return ok and s == true
end

local function resolve(id)
    if CharacterTrait == nil then return nil end
    if string.find(id, ":", 1, true) == nil then
        return CharacterTrait[id]
    end
    local getter = CharacterTrait.get
    if getter == nil then return nil end
    if ResourceLocation ~= nil and ResourceLocation.of ~= nil then
        local okL, loc = pcall(ResourceLocation.of, id)
        if not okL or loc == nil then return nil end
        local okT, trait = pcall(getter, loc)
        if okT then return trait end
        return nil
    end
    local okT, trait = pcall(getter, id)
    if okT then return trait end
    return nil
end

local function applyGrant(player, spec)
    local remove = false
    local id = spec
    if string.sub(spec, 1, 1) == "-" then
        remove = true
        id = string.sub(spec, 2)
    end
    local trait = resolve(id)
    TKX_TraitProbe.lastId = spec
    if trait == nil then return end
    local okT, traits = tkxCall(player, "getCharacterTraits")
    if not okT or traits == nil then return end
    if remove then
        tkxCall(traits, "remove", trait)
        TKX_TraitProbe.removes = TKX_TraitProbe.removes + 1
    else
        tkxCall(traits, "add", trait)
        TKX_TraitProbe.grants = TKX_TraitProbe.grants + 1
    end
end

local function eachPlayer(player)
    local okMd, md = tkxCall(player, "getModData")
    if not okMd or md == nil then return end
    local spec = md.TKX_grant
    if spec ~= nil then
        md.TKX_grant = nil
        if type(spec) == "string" and spec ~= "" then applyGrant(player, spec) end
    end
    local push = md.TKX_push
    if push ~= nil then
        md.TKX_push = nil
        if (push == 1 or push == "1") and sendSyncPlayerFields ~= nil then
            pcall(sendSyncPlayerFields, player, 2)
        end
    end
end

local function tick()
    if TKX_TraitProbe == nil then return end
    if not tkxIsServer() then return end
    if getOnlinePlayers == nil then return end
    local okList, players = pcall(getOnlinePlayers)
    if not okList or players == nil then return end
    local okSize, size = tkxCall(players, "size")
    if not okSize or size == nil then return end
    local i = 0
    while i < size do
        local okGet, player = tkxCall(players, "get", i)
        if okGet and player ~= nil then eachPlayer(player) end
        i = i + 1
    end
end

if Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(tick)
end
