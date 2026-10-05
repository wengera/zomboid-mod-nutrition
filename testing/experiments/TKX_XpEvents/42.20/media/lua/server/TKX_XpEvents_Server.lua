-- TKX_XpEvents server (X39): which XP events fire on a dedicated server, and with what.
-- Counters are flat scalar keys in the global-modData table "TKX_XpEvents" (scalars only, so
-- witness.moddata reads them as strings, #2848):
--   addxp_<Perk>_count / _lastAmount / _lastLevel   Events.AddXP(player, perk, amount)
--   levelperk_count / _lastPerk / _lastLevel / _lastGained   Events.LevelPerk(player, perk, level, gained)
--   hitxp_count / hitxp_lastHitCount                Events.OnWeaponHitXp(owner, weapon, hitObject, damage, hitCount)
--   hittree_count                                   Events.OnWeaponHitTree(owner, weapon)
-- Install-once (#2845): the sentinel TKX_XpEvents_Installed is a global of its own, never a field of
-- a table the shared file re-creates; handlers register at file scope behind the nil-checked
-- isServer() test, once, and never at a boot event.
local function tkxServer()
    if isServer == nil then return false end
    local ok, s = pcall(isServer)
    return ok and s == true
end

local function store()
    if ModData == nil then return nil end
    return ModData.getOrCreate("TKX_XpEvents")
end

local function bump(t, key)
    t[key] = (t[key] or 0) + 1
end

local function perkName(perk)
    if perk == nil then return "nil" end
    local f = perk["getId"]
    if f ~= nil then
        local ok, v = pcall(f, perk)
        if ok and v ~= nil then return tostring(v) end
    end
    return tostring(perk)
end

local function onAddXp(owner, perk, amount)
    local t = store()
    if t == nil then return end
    local n = perkName(perk)
    bump(t, "addxp_" .. n .. "_count")
    t["addxp_" .. n .. "_lastAmount"] = amount
    local lvl = nil
    if owner ~= nil and perk ~= nil then
        local f = owner["getPerkLevel"]
        if f ~= nil then lvl = f(owner, perk) end
    end
    t["addxp_" .. n .. "_lastLevel"] = lvl
end

local function onLevelPerk(owner, perk, level, gained)
    local t = store()
    if t == nil then return end
    bump(t, "levelperk_count")
    t["levelperk_lastPerk"] = perkName(perk)
    t["levelperk_lastLevel"] = level
    t["levelperk_lastGained"] = gained
end

local function onHitXp(owner, weapon, hitObject, damage, hitCount)
    local t = store()
    if t == nil then return end
    bump(t, "hitxp_count")
    t["hitxp_lastHitCount"] = hitCount
end

local function onHitTree(owner, weapon)
    local t = store()
    if t == nil then return end
    bump(t, "hittree_count")
end

if tkxServer() and TKX_XpEvents_Installed == nil then
    TKX_XpEvents_Installed = true
    if Events ~= nil then
        if Events.AddXP ~= nil then Events.AddXP.Add(onAddXp) end
        if Events.LevelPerk ~= nil then Events.LevelPerk.Add(onLevelPerk) end
        if Events.OnWeaponHitXp ~= nil then Events.OnWeaponHitXp.Add(onHitXp) end
        if Events.OnWeaponHitTree ~= nil then Events.OnWeaponHitTree.Add(onHitTree) end
    end
end
