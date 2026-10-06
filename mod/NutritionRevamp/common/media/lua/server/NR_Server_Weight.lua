-- NR_Server_Weight.lua -- the body model's weight adapter (Plan 3, spec § 4.3): once per player per game
-- minute, last in the per-player minute (this file sorts after NR_Server_Metabolism.lua,
-- NR_Server_Strength.lua and NR_Server_Training.lua, so its handler registers after theirs and reads
-- the fm and lm Metabolism stamped this minute), it writes the model's total mass into the vanilla
-- weight slot, the three direction flags off the 7-day trend, refreshes the weight band trait when the
-- band changes or its trait has gone missing and pushes the trait block, and, under the NR.LegacyMirror
-- sandbox option, overwrites the four vanilla macro stores other mods read.
--
-- The weight slot is re-asserted, not trusted (#2643): setWeight every minute even when unchanged, the
-- three flags every minute (#2644). The band is refreshed with applyTraitFromWeight, which removes the
-- five band traits and adds back the one the weight implies and pushes nothing (#2722, #0534), so the
-- push sendSyncPlayerFields(player, 2) follows it (#2099; it reaches that player's own connection only,
-- #2603). A band trait an admin or another mod removes is re-applied as a repair (#2740). The band
-- traits are compared as registry objects off CharacterTrait, never by name (#0550).
--
-- The legacy mirror (ruling 13): calories = the trailing-24 h energy balance; proteins = the piecewise
-- map of the trailing-24 h protein per kg; carbohydrates and lipids = the trailing-24 h grams less a
-- reference; each blends today with yesterday's closed day on the hours since the last day close
-- (K.body.blend24, as K.energy.eb24h does), clamped to the stores (#0022, #0023). A plain overwrite every
-- minute. The p7, carb7 and lip7 rings are NR_Server_Metabolism's: it rebuilds them on an old record
-- before this file reads them. When all four setters answer, the four values written become the record's
-- reconciliation baseline (record.reconcile.baseline, Plan 8 ruling 6): NR_Server_Reconcile, earlier in the
-- same minute, compares the stores against the mod's own last write. A band change also marks the bus
-- (B.markBand, ruling 7), so the mirror's body_band goes out with the next effects flush.
--
-- Every Java read goes through NR.call (index-first); every Java global is named only inside a function
-- behind a nil check, so the file loads with no engine (testing/tests/kernel/test_weight_shape.py). The
-- whole minute runs under one pcall per player and never raises into the players walk. Slow-clock code:
-- no @fastpath region in this file.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.weight = {
    stats = { minutes = 0, weightWrites = 0, flagWrites = 0, bandChanges = 0, bandRepairs = 0, pushes = 0,
              pushMissing = 0, mirrorWrites = 0, failures = 0, badReads = 0, rebases = 0 },
    lastError = nil,
    wired = false,
    limitations = {
        "the mirror is a plain overwrite; its four written values are the reconciliation's baseline (NR_Server_Reconcile)",
        "the weight-direction thresholds are a game choice",
    },
}
local WGT = NR.server.weight

-- The band each weight band implies, as the CharacterTrait registry field; "normal" implies none.
WGT.BAND_TRAIT = {
    obese = "OBESE",
    overweight = "OVERWEIGHT",
    underweight = "UNDERWEIGHT",
    veryUnderweight = "VERY_UNDERWEIGHT",
    emaciated = "EMACIATED",
}
-- The five band traits applyTraitFromWeight removes before it adds one back (#2722).
WGT.BAND_TRAITS = { "OBESE", "OVERWEIGHT", "UNDERWEIGHT", "VERY_UNDERWEIGHT", "EMACIATED" }
local function finite(x)
    return type(x) == "number" and x == x and x ~= math.huge and x ~= -math.huge
end

-- The hours since the body's last day close (world age less lastCloseAgeH), or 0 -- the full blend --
-- when either is unreadable.
local function hoursSinceClose(body)
    if getGameTime == nil then return 0 end
    local ok, gt = pcall(getGameTime)
    if not ok or gt == nil then return 0 end
    local okA, age = NR.call(gt, "getWorldAgeHours")
    if not okA or not finite(age) or not finite(body.lastCloseAgeH) then return 0 end
    return age - body.lastCloseAgeH
end

-- The trait-block push (#2099): a Java global called with a dot (#2815); absent -> counted.
local function push(player)
    local f = sendSyncPlayerFields
    if f ~= nil then
        f(player, 2)
        WGT.stats.pushes = WGT.stats.pushes + 1
    else
        WGT.stats.pushMissing = WGT.stats.pushMissing + 1
    end
end

-- Whether the band's trait set needs a repair: the band's own trait absent, or for "normal" any of the
-- five present. False when the registry or the trait collection is unreadable (nothing to compare).
local function needsRepair(player, band)
    if CharacterTrait == nil then return false end
    local okC, coll = NR.call(player, "getCharacterTraits")
    if not okC or coll == nil then return false end
    local want = WGT.BAND_TRAIT[band]
    if want ~= nil then
        local t = CharacterTrait[want]
        if t == nil then return false end
        local okG, present = NR.call(coll, "get", t)
        return okG and present ~= true
    end
    for i = 1, #WGT.BAND_TRAITS do
        local t = CharacterTrait[WGT.BAND_TRAITS[i]]
        if t ~= nil then
            local okG, present = NR.call(coll, "get", t)
            if okG and present == true then return true end
        end
    end
    return false
end

-- The legacy macro mirror: the four stores off the trailing-24 h blend of today and yesterday.
local function mirror(nut, body, w)
    local hsc = hoursSinceClose(body)
    local p24h = K.body.blend24(body.pDay, body.p7[7], hsc) / w
    local carb24h = K.body.blend24(body.carbDay, body.carb7[7], hsc)
    local lip24h = K.body.blend24(body.lipDay, body.lip7[7], hsc)
    local cal = K.body.mapCalories(K.energy.eb24h(body, hsc))
    local prot = K.body.mapProteins(p24h)
    local carb = K.body.mapCarbs(carb24h)
    local lip = K.body.mapLipids(lip24h)
    local okC = NR.call(nut, "setCalories", cal)
    local okP = NR.call(nut, "setProteins", prot)
    local okH = NR.call(nut, "setCarbohydrates", carb)
    local okL = NR.call(nut, "setLipids", lip)
    local last = body.mirrorLast
    if type(last) ~= "table" then
        last = {}
        body.mirrorLast = last
    end
    last[1] = cal
    last[2] = prot
    last[3] = carb
    last[4] = lip
    WGT.stats.mirrorWrites = WGT.stats.mirrorWrites + 1
    if okC and okP and okH and okL then
        return { calories = cal, carbs = carb, lipids = lip, proteins = prot }
    end
    return nil
end

-- The reconciliation baseline after the legacy write: the four values written (Plan 8 ruling 6). A record
-- with no reconcile table yet is left for the reconciliation's own seed.
local function rebase(record, wrote)
    local rc = record.reconcile
    if wrote == nil or type(rc) ~= "table" then return end
    rc.baseline = K.reconcile.baselineAfter(wrote)
    WGT.stats.rebases = WGT.stats.rebases + 1
end

-- The band mark on the bus (ruling 7): the effects mark, one gap and one flush.
local function markBand(username)
    local B = NR.server.bus
    if B ~= nil and B.markBand ~= nil then B.markBand(username) end
end

local function step(username, player, record)
    local body = record.body
    if body == nil then return end
    local w = body.fm + body.lm
    if not finite(w) or w <= 0 then
        WGT.stats.failures = WGT.stats.failures + 1
        WGT.lastError = "weight: non-finite or non-positive mass for " .. tostring(username) .. "; nothing written"
        NR.log.say(2, WGT.lastError)
        return
    end
    local okN, nut = NR.call(player, "getNutrition")
    if not okN or nut == nil then
        WGT.stats.badReads = WGT.stats.badReads + 1
        return
    end
    if NR.call(nut, "setWeight", w) then WGT.stats.weightWrites = WGT.stats.weightWrites + 1 end
    local inc, lot, dec = K.body.flags(K.body.trend(body.mass7, w))
    local okI = NR.call(nut, "setIncWeight", inc)
    local okL = NR.call(nut, "setIncWeightLot", lot)
    local okD = NR.call(nut, "setDecWeight", dec)
    if okI and okL and okD then WGT.stats.flagWrites = WGT.stats.flagWrites + 1 end
    local band = K.body.band(w)
    if band ~= body.band then
        if NR.call(nut, "applyTraitFromWeight") then       -- absent: nothing stamped; next minute retries
            body.band = band
            WGT.stats.bandChanges = WGT.stats.bandChanges + 1
            push(player)
            markBand(username)
        end
    elseif needsRepair(player, band) then
        if NR.call(nut, "applyTraitFromWeight") then
            WGT.stats.bandRepairs = WGT.stats.bandRepairs + 1
            push(player)
        end
    end
    local opts = NR.server.options
    if opts == nil or opts.legacyMirror ~= false then
        rebase(record, mirror(nut, body, w))
    end
end

-- One player's minute: the (username, player, record) callback NR_Server_Players fires from P.work.
-- One pcall around the body: a failure is kept and logged on the slow clock, never raised into the
-- players walk.
function WGT.minute(username, player, record)
    if record == nil then return end
    WGT.stats.minutes = WGT.stats.minutes + 1
    local ok, err = pcall(step, username, player, record)
    if not ok then
        WGT.stats.failures = WGT.stats.failures + 1
        WGT.lastError = err
        NR.log.say(2, "weight: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

-- Wiring: appended to the players' onMinute list at OnServerStarted. This file sorts last of the body
-- adapters, so its handler registers after Metabolism's and Strength's and reads this minute's masses.
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if WGT.wired then return end
        WGT.wired = true
        local P = NR.server.players
        P.onMinute[#P.onMinute + 1] = WGT.minute
    end)
end
