-- NR_Server_Strength.lua -- the body model's Strength adapter (spec § 4.3): once per player per
-- game minute, after the metabolism step (the pipeline's ORDER, NR_Server_Minute, runs the strength
-- step after metabolism, nutrients and effects), it re-asserts the carry delta. The lean-mass body's level is moved
-- at the day close (NR_Server_Metabolism) and written here from Plan 13 Task 14 on; until then the minute writes no
-- level and the carry's trait factor reads the native level's band (ruling 13-28).
--
-- The carry delta is the trait factor of the muscle band (K.strength.traitCarry, #2144; ruling 13-7) times
-- (1 + eAcute), written with setMaxWeightDelta when it differs from the live delta, so any other writer is
-- re-asserted against (#2143, #2565). This file never writes the carry base (#2704).
--
-- STR.ladder (the XP ladder) and STR.remap (vanilla's band remap, the measured route of #2867-#2874) are kept for
-- the level write.
--
-- Every Java read goes through NR.call (index-first) with a default; every Java global is named only
-- inside a function behind a nil check, so the file loads with no engine
-- (testing/tests/kernel/test_strength_shape.py). The whole minute runs under one pcall per player and
-- never raises into the players walk. Slow-clock code: no @fastpath region in this file.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.strength = {
    stats = { minutes = 0, pushes = 0, pushMissing = 0, carryWrites = 0, failures = 0,
              badReads = 0, ladderFallbacks = 0 },
    lastError = nil,
    wired = false,
    totals = nil,
    limitations = {
        "the carry delta's acute inputs (dehydration, sweat, hours awake, caffeine, clinical vitamin D) read the current minute's fluids, acute and nutrients sub-tables",
        "no level is written yet and the carry's trait factor reads the native level's band; an unreadable level writes no carry that minute",
    },
}
local STR = NR.server.strength

-- The #2102 ladder (cumulative XP for levels 1-10), the fallback when the perk's own getter is absent.
STR.FALLBACK_TOTALS = { 1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500 } -- #2102
-- The four Strength band traits vanilla's remap removes before it adds one back (#2157).
STR.BAND_TRAITS = { "WEAK", "FEEBLE", "STOUT", "STRONG" }
-- The carry delta re-assertion tolerance.
STR.CARRY_EPS = 0.001

local finite = NR.finite

-- The world age and the minute's other engine reads are NR.read's (an unread age skips the step, never stamped 0).

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

-- Vanilla's band remap for a written level: every band trait but the level's own is removed if present,
-- the level's own added if absent; one sendSyncPlayerFields(player, 2) (#2099) when the set changed.
-- Returns whether it changed. ctx (optional) is the pipeline's, whose trait collection read (NR.read) it shares.
function STR.remap(player, level, ctx)
    if CharacterTrait == nil then return false end
    local coll = NR.read.traits(ctx, player)
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
    if changed then NR.pushTraits(player, STR.stats) end
    return changed
end

-- The carry delta's acute inputs off the record's Plan 4 sub-tables. The pipeline's ORDER runs the
-- nutrients step before this one, so these are the CURRENT minute's stamps. An
-- absent sub-table (one the nutrients step has not laid) or an absent or non-finite field reads the neutral the
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

-- The carry delta: the trait factor of level's band (K.strength.traitCarry) x (1 + eAcute), the dehydration, sweat,
-- hours-awake, caffeine and vitamin D inputs read off the record (acuteInputs) at the body mass fm + lm + lx; written
-- when it differs from the live delta by more than CARRY_EPS, so any other writer is re-asserted against (#2143,
-- #2565).
local function carry(player, record, body, ageH, ctx, level)
    local hourOfDay = NR.read.hour(ctx, ageH)
    local w = body.fm + body.lm + body.lx
    local bf = 0
    if w > 0 then bf = body.fm / w end
    local dehydPct, sweatActive, awakeH, caffeineActive, vitDClinical = acuteInputs(record, w)
    local eAcute = K.strength.eAcute(dehydPct, sweatActive, awakeH, hourOfDay, caffeineActive, vitDClinical, bf)
    local delta = K.strength.carryDelta(K.strength.traitCarry(level), eAcute)
    if not finite(delta) then return end
    local live = num(player, "getMaxWeightDelta", nil)
    if live == nil or math.abs(delta - live) > STR.CARRY_EPS then
        local ok = NR.call(player, "setMaxWeightDelta", delta)
        if ok then STR.stats.carryWrites = STR.stats.carryWrites + 1 end
    end
    body.delta = delta
end

local function step(username, player, record, ctx)
    local body = record.body
    if body == nil then return end
    local ageH = NR.read.ageH(ctx)
    if ageH == nil then
        STR.stats.badReads = STR.stats.badReads + 1
        return
    end
    local perk = Perks ~= nil and Perks.Strength or nil
    local level = nil
    if perk ~= nil then level = num(player, "getPerkLevel", nil, perk) end
    if level == nil then
        STR.stats.badReads = STR.stats.badReads + 1
        return
    end
    carry(player, record, body, ageH, ctx, level)               -- the native level's band until Task 14 (ruling 13-28)
end

-- One player's minute: the pipeline's strength step (NR_Server_Minute.run, called from P.work).
-- One pcall around the body: a failure is kept and logged on the slow clock, never raised into the
-- players walk.
function STR.minute(username, player, record, ctx)
    if record == nil then return end
    STR.stats.minutes = STR.stats.minutes + 1
    local ok, err = pcall(step, username, player, record, ctx)
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
