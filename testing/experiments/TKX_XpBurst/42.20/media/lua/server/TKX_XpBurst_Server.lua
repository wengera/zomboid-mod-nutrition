-- TKX_XpBurst server (X40): a bus-triggered burst of experience writes with NO anti-cheat
-- checker refresh. The driver sets keys in the global-modData table "TKX_XpBurst" through
-- `globalmoddata.set TKX_XpBurst <key> <value>`: `perk` (default Strength), `amount` (default 1),
-- then `fire <n>`. An EveryOneMinute poll (cheap early-out, #1071) reads fire, resets it to 0,
-- and calls the first online player's XP object n times:
--   getXp():AddXP(perk, amount, false, true, true, false)
-- the six-argument overload IsoGameCharacter$XP.AddXP(Perk;FZZZZ)V (#2106: the body, no
-- local-player gate), arguments in the order GameServer.addXp passes them (#2132: false, the
-- multiplier flag inverted to true, true, the halo flag false) but WITHOUT that route's
-- updateXpChecker refresh, so the anti-cheat snapshot is left behind by the burst.
-- What it did is logged to `fired` (a string) and `firedCount` (a number) in the same table.
-- Install-once (#2845): sentinel global TKX_XpBurst_Installed, handler registered once at file
-- scope behind the nil-checked isServer() test.
local function tkxServer()
    if isServer == nil then return false end
    local ok, s = pcall(isServer)
    return ok and s == true
end

local function poll()
    if ModData == nil then return end
    local t = ModData.getOrCreate("TKX_XpBurst")
    local n = t["fire"]
    if n == nil or n == 0 then return end
    t["fire"] = 0
    local perkName = t["perk"] or "Strength"
    local amount = tonumber(t["amount"]) or 1
    local perk = nil
    if Perks ~= nil then perk = Perks[perkName] end
    local players = nil
    if getOnlinePlayers ~= nil then players = getOnlinePlayers() end
    local count = 0
    if players ~= nil then count = players:size() end
    if perk == nil or count == 0 then
        t["fired"] = "skipped: perk=" .. tostring(perkName) .. " players=" .. tostring(count)
        return
    end
    local player = players:get(0)
    local xp = nil
    if player["getXp"] ~= nil then xp = player:getXp() end
    if xp == nil or xp["AddXP"] == nil then
        t["fired"] = "skipped: no getXp():AddXP"
        return
    end
    local times = tonumber(n) or 0
    local done = 0
    for i = 1, times do
        xp:AddXP(perk, amount, false, true, true, false)
        done = done + 1
    end
    t["firedCount"] = (t["firedCount"] or 0) + done
    t["fired"] = "n=" .. tostring(done) .. " perk=" .. tostring(perkName) .. " amount=" .. tostring(amount)
end

if tkxServer() and TKX_XpBurst_Installed == nil then
    TKX_XpBurst_Installed = true
    if Events ~= nil and Events.EveryOneMinute ~= nil then
        Events.EveryOneMinute.Add(poll)
    end
end
