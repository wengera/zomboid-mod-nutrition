-- NR_Server_Strength.lua -- the body model's Strength adapter (Plan 3, spec § 4.3): once per player per
-- game minute, after the metabolism step (the pipeline's ORDER, NR_Server_Minute, runs the strength
-- step after metabolism, nutrients and effects), it reads the XP-implied Strength level, sets the ceiling the lean
-- ratio and the functional factor allow, moves the shown level one step by the write policy, writes it
-- when the Java level differs, re-applies vanilla's band remap and pushes the trait block when the
-- trait set changed, and re-asserts the carry delta.
--
-- The level is a clamp, never a grant (#2701): the shown level is min(XP-implied, ceiling), written with
-- setPerkLevelDebug alone (ruling T3-1, run x141s-20261005-105131: the write held through the
-- experience push, the rust pass and an admin SyncXp, and ran no band remap, #2867-#2874), so the band
-- (XpUpdate.lua:207-243, #2157) is re-applied here. Any divergence -- the client's XP sync, an admin
-- edit -- is corrected every minute (#2740), the band trait set included: when the Java level already
-- equals the shown level but the band traits differ from what that level implies (an admin trait edit;
-- an XP drop vanilla's own level-down met with no write, run x141c-20261005-132133), the remap runs as
-- a repair. This file never calls LevelPerk, LoseLevel, setXPToLevel,
-- addXp or AddXP, and never writes the carry base (#2704): a level-only write moves no XP and cannot
-- trip the XP anti-cheat.
--
-- BeyondTen (#2850, 1.3.4): for a perk at Java level 10 it holds getXP at the level-9 total every server
-- tick and banks the excess as mastery, so the XP-implied level reads 9 for a legitimate level 10; while
-- BeyondTen is loaded a level-10 perk whose XP is at least the level-9 total reads 10.
--
-- Every Java read goes through NR.call (index-first) with a default; every Java global is named only
-- inside a function behind a nil check, so the file loads with no engine
-- (testing/tests/kernel/test_strength_shape.py). The whole minute runs under one pcall per player and
-- never raises into the players walk. Slow-clock code: no @fastpath region in this file.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.strength = {
    stats = { minutes = 0, writes = 0, pushes = 0, pushMissing = 0, carryWrites = 0, failures = 0,
              badReads = 0, ladderFallbacks = 0, bandRepairs = 0 },
    lastError = nil,
    wired = false,
    totals = nil,
    limitations = {
        "the ceiling clamps the Java level 0-10; BeyondTen mastery levels are outside the model (#2118)",
        "a rise is one level per six-hour window",
        "the carry delta's acute inputs (dehydration, sweat, hours awake, caffeine, clinical vitamin D) read the current minute's fluids, acute and nutrients sub-tables (Plan 4)",
        "while BeyondTen is loaded a level-10 perk at or above the level-9 total reads 10 (#2850; BeyondTen 1.3.4 parks a level-10 perk's XP at the level-9 total)",
        "an XP loss follows down at once; the ceiling falls one level per game hour",
        "offline time is not integrated: the rise hold counts at most one hour per minute",
    },
}
local STR = NR.server.strength

-- The #2102 ladder (cumulative XP for levels 1-10), the fallback when the perk's own getter is absent.
STR.FALLBACK_TOTALS = { 1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500 } -- #2102
-- The four Strength band traits vanilla's remap removes before it adds one back (#2157).
STR.BAND_TRAITS = { "WEAK", "FEEBLE", "STOUT", "STRONG" }
-- The carry delta re-assertion tolerance.
STR.CARRY_EPS = 0.001
-- The rise hold's per-minute step cap, hours.
STR.MAX_DT_H = 1

local finite = NR.finite



-- The world age, or nil when it cannot be read (the step is then skipped, never stamped 0).
local worldAge = NR.worldAge







-- A number read off obj:name(...), or dflt when the member is absent or the answer is not finite.
local num = NR.num





-- A boolean read off obj:name(...): true only when the member is present and answers true.
local flag = NR.flag




-- An object read off obj:name(...), or nil.
local obj = NR.obj





-- The cumulative XP ladder, totals[0] = 0 and totals[L] = Perks.Strength:getTotalXpForLevel(L) for
-- L = 1..10, read once per server; a nil or non-finite answer anywhere reads the #2102 ladder instead,
-- logged once.
function STR.ladder()
    if STR.totals ~= nil then return STR.totals end
    local perk = Perks ~= nil and Perks.Strength or nil
    local totals = { [0] = 0 }
    local whole = true
    for L = 1, K.strength.L_MAX do
        local v = num(perk, "getTotalXpForLevel", nil, L)
        if v == nil then whole = false end
        totals[L] = v
    end
    if not whole then
        totals = { [0] = 0 }
        for L = 1, K.strength.L_MAX do
            totals[L] = STR.FALLBACK_TOTALS[L]
        end
        STR.stats.ladderFallbacks = STR.stats.ladderFallbacks + 1
        NR.log.say(2, "strength: getTotalXpForLevel unreadable; the #2102 ladder is used")
    end
    STR.totals = totals
    return totals
end

-- The XP-implied level and the Java level now, or nil when either read fails. BeyondTen's parked XP
-- reads 10 for a level-10 perk (#2850).
function STR.vanillaLevel(player, perk)
    local xp = num(obj(player, "getXp"), "getXP", nil, perk)
    local current = num(player, "getPerkLevel", nil, perk)
    if xp == nil or current == nil then return nil, nil end
    local totals = STR.ladder()
    local lvanilla = K.strength.xpLevel(xp, totals)
    if current == K.strength.L_MAX and xp >= totals[K.strength.L_MAX - 1] and BeyondTen ~= nil
        and BeyondTen.NATIVE_MAX_LEVEL ~= nil then
        lvanilla = K.strength.L_MAX
    end
    return lvanilla, current
end

-- Vanilla's band remap for a written level: every band trait but the level's own is removed if present,
-- the level's own added if absent; one sendSyncPlayerFields(player, 2) (#2099) when the set changed.
-- Returns whether it changed.
function STR.remap(player, level)
    if CharacterTrait == nil then return false end
    local coll = obj(player, "getCharacterTraits")
    if coll == nil then return false end
    local want = K.strength.bandOf(level)
    local changed = false
    for i = 1, #STR.BAND_TRAITS do
        local name = STR.BAND_TRAITS[i]
        local t = CharacterTrait[name]
        if t ~= nil then
            local present = flag(coll, "get", t)
            if name == want then
                if not present and NR.call(coll, "add", t) then
                    changed = true                       -- a failing add repairs nothing
                end
            elseif present and NR.call(coll, "remove", t) then
                changed = true
            end
        end
    end
    if changed then
        if sendSyncPlayerFields == nil then
            STR.stats.pushMissing = STR.stats.pushMissing + 1
        else
            sendSyncPlayerFields(player, 2)
            STR.stats.pushes = STR.stats.pushes + 1
        end
    end
    return changed
end

-- The self-heal (the #2833 pattern): a non-finite policy stamp reads its neutral and counts a failure.
local function heal(username, body, ageH)
    local bad = nil
    local function mark(name)
        if bad == nil then bad = name else bad = bad .. "," .. name end
    end
    if not finite(body.strAgeH) then body.strAgeH = ageH; mark("strAgeH") end
    if not finite(body.riseHeldH) then body.riseHeldH = 0; mark("riseHeldH") end
    if not finite(body.lastFallAge) then body.lastFallAge = ageH; mark("lastFallAge") end
    if not finite(body.shownL) then body.shownL = body.l0; mark("shownL") end
    if bad ~= nil then
        STR.stats.failures = STR.stats.failures + 1
        STR.lastError = "strength: non-finite " .. bad .. " for " .. tostring(username) .. "; stamped neutral"
        NR.log.say(2, STR.lastError)
    end
end

-- The carry delta's acute inputs off the record's Plan 4 sub-tables. The pipeline's ORDER runs the
-- nutrients step before this one, so these are the CURRENT minute's stamps. An
-- absent sub-table (a record made before Plan 4) or an absent or non-finite field reads the neutral the
-- Plan 3 stub passed. Read: fluids.dehydPct, fluids.sweatActive (true), acute.awakeH, acute.caf (through
-- K.acute.caffeineActive) and nutrients.vitDClinical (true). w is the body mass, kg.
local function acuteInputs(record, w)
    local nut, fl, ac = record.nutrients, record.fluids, record.acute
    local dehydPct, sweatActive = 0, false
    if type(fl) == "table" then
        if finite(fl.dehydPct) then dehydPct = K.max(0, fl.dehydPct) end
        sweatActive = fl.sweatActive == true
    end
    local awakeH, caffeineActive = 0, false
    if type(ac) == "table" then
        if finite(ac.awakeH) then awakeH = K.max(0, ac.awakeH) end
        if finite(ac.caf) and w > 0 then caffeineActive = K.acute.caffeineActive(ac, w) end
    end
    local vitDClinical = type(nut) == "table" and nut.vitDClinical == true
    return dehydPct, sweatActive, awakeH, caffeineActive, vitDClinical
end

-- The carry delta: traitCarry x (1 + eAcute) (ruling 11), the dehydration, sweat, hours-awake, caffeine
-- and vitamin D inputs read off the record (acuteInputs); written when it differs from the live delta by
-- more than CARRY_EPS, so any other writer is re-asserted against (#2143, #2565).
local function carry(player, record, body, ageH)
    local hourOfDay = ageH - math.floor(ageH / 24) * 24
    if getGameTime ~= nil then
        local ok, gt = pcall(getGameTime)
        hourOfDay = num(ok and gt or nil, "getTimeOfDay", hourOfDay)
    end
    local w = body.fm + body.lm
    local bf = 0
    if w > 0 then bf = body.fm / w end
    local dehydPct, sweatActive, awakeH, caffeineActive, vitDClinical = acuteInputs(record, w)
    local eAcute = K.strength.eAcute(dehydPct, sweatActive, awakeH, hourOfDay, caffeineActive, vitDClinical, bf)
    local delta = K.strength.carryDelta(body.traitCarry, eAcute)
    if not finite(delta) then return end
    local live = num(player, "getMaxWeightDelta", nil)
    if live == nil or math.abs(delta - live) > STR.CARRY_EPS then
        local ok = NR.call(player, "setMaxWeightDelta", delta)
        if ok then STR.stats.carryWrites = STR.stats.carryWrites + 1 end
    end
    body.delta = delta
end

local function step(username, player, record)
    local body = record.body
    if body == nil then return end
    local ageH = worldAge()
    if ageH == nil then
        STR.stats.badReads = STR.stats.badReads + 1
        return
    end
    heal(username, body, ageH)
    local dtH = K.clamp(ageH - body.strAgeH, 0, STR.MAX_DT_H)
    body.strAgeH = ageH
    local perk = Perks ~= nil and Perks.Strength or nil
    if perk ~= nil then
        local lvanilla, current = STR.vanillaLevel(player, perk)
        if lvanilla == nil then
            STR.stats.badReads = STR.stats.badReads + 1
        else
            local lceil = K.strength.ceiling(body.l0, body.lm, body.lm0, K.strength.fSlow(body, body.dayIndex))
            local desired = K.strength.policy(body, lvanilla, lceil, ageH, dtH)
            if current ~= desired then
                if NR.call(player, "setPerkLevelDebug", perk, desired) then
                    STR.stats.writes = STR.stats.writes + 1
                    STR.remap(player, desired)
                end
            elseif STR.remap(player, desired) then
                STR.stats.bandRepairs = STR.stats.bandRepairs + 1   -- #2740: the band set re-asserted
            end
        end
    end
    carry(player, record, body, ageH)
end

-- One player's minute: the pipeline's strength step (NR_Server_Minute.run, called from P.work).
-- One pcall around the body: a failure is kept and logged on the slow clock, never raised into the
-- players walk.
function STR.minute(username, player, record)
    if record == nil then return end
    STR.stats.minutes = STR.stats.minutes + 1
    local ok, err = pcall(step, username, player, record)
    if not ok then
        STR.stats.failures = STR.stats.failures + 1
        STR.lastError = err
        NR.log.say(2, "strength: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

-- Wiring: registered as the pipeline's strength step at OnServerStarted. ORDER runs it after the
-- metabolism step, so the body exists and its day has closed
-- before this step reads it.
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if STR.wired then return end
        STR.wired = true
        local MIN = NR.server.minute
        MIN.register("strength", STR.minute)
    end)
end
