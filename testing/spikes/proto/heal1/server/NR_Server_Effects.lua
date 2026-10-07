-- NR_Server_Effects.lua -- the effects layer's slow adapter (Plan 5, spec § 4.5; rulings 2, 6-8, 12-13, 16-17,
-- 19, 22-23; T1-1, T1-3, T4-1, T6-1, T6-2): once per player per game minute it builds record.effects, the
-- coefficient set the fast handler and the mirror read, and applies the slow channels itself -- the trait
-- toggles (Night Vision, Short Sighted), the four regeneration setters, the per-part wound, bleeding and
-- infection folds, the catchACold fold, the health drains and the spontaneous bruise.
--
-- Order (ruling 22, made explicit by the pipeline, Plan 10 R2): the effects step runs right after the
-- nutrients step in NR_Server_Minute's ORDER, on the body, dtM and ageH Nutrients stamps on the context at
-- the end of its own minute, so the step reads this minute's epoch, fluids and acute stamps with zero lag. Strength follows and reads the raw
-- sub-tables as before. The fatigue multipliers mAcc and rRec stamped here feed the NEXT minute's
-- K.acute.sleepMinute (a one-minute lag, stated).
--
-- Per minute, under one pcall per player: ensure and heal record.effects; the day close (the protein-energy
-- grade and the closed day's energy availability); the twelve-band vector and the flags; the rebuild only
-- when the key moved (K.effects.changed: the nutrient epoch, the closed day, the dial snapshot or a band);
-- the per-minute scalars (fOff, mAcc, rRec, solAddH, solMul, intoxTarget, tempTarget); the night-vision
-- machine and the four trait rules; the drain (kernel order: compose, nvMinute, drain); the regeneration
-- setters on a rebuild, a drain start or stop and at first sight (the constants are not saved, #3020); the
-- per-part folds and the cold fold; the bruise roll; the drain's ReduceGeneralHealth.
--
-- Every Java read goes through NR.call (index-first) with a default; every Java global is named only inside
-- a function behind a nil check, so the file loads with no engine (testing/tests/kernel/test_effects_shape.py).
-- Every field written on the record is a number, a boolean or a table of numbers and booleans (#1495).
-- Slow-clock code: no @fastpath region in this file.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.effects = {
    stats = { minutes = 0, errors = 0, healed = 0, rebuilds = 0, closes = 0, traitAdds = 0, traitRemoves = 0,
              reasserts = 0, pushes = 0, pushMissing = 0, regenWrites = 0, partWrites = 0, infectSyncs = 0,
              coldWrites = 0, drainMinutes = 0, bruises = 0, skippedDead = 0 },
    lastError = nil,
    lastHealed = nil,
    wired = false,
    last = {},
    limitations = {
        "the one-minute lag: mAcc and rRec feed the NEXT minute's sleep-pressure step (Nutrients runs the sleep step before this file builds them)",
        "the engine part of mAcc and rRec reads the fast handler's last input table (its endurance read, resting, the thermoregulator's fatigue multiplier, the sleep traits, StatsDecrease, the bed); before the first tick, or in Overlay mode, it reads the hoist defaults",
        "the vitamin D effect rows ship gated off (VITD_EFFECTS false, ruling 8): no sun term exists (kSun 0, S1064 open)",
        "omega-3 drives no mood row: S0919 is EPA-specific and the vector carries no EPA key (ruling 8)",
        "speedMul is computed and stamped but no speed write is applied (X47 open: the WalkSpeed write is gone at the first 266 ms sample)",
        "aimMul is computed and stamped but applied by no seat (X86 open: the engine clears a written aim flag on most updates)",
        "POISON ships 0 at every toxicity rung (ruling 12); the rungs act through FOOD_SICKNESS floors 30/55/85, never the SICKNESS stat (ruling T1-1)",
        "the HUNGER and THIRST views are capped under moodle level 4 always (ruling 14): the level-4 Hungry and Thirsty moodles never show",
        "while the endurance fold is on (it ships off, X35) melee swings would drain scaled by dmod like any other drain; shipped, they are unscaled",
        "a trait change is pushed to its owner only: other clients' copies of a player's traits stay stale until relog (#2603)",
        "tempTarget is applied uncalibrated: the equilibrium of the held target against the regulator is unmeasured (X81); at rest the core already sits about 0.45 °C under the set point (x161b), so a −0.2 target does not act at rest",
        "the regeneration constants are not saved (#3020): re-asserted at every rebuild, at every drain start or stop and at first sight",
        "a natively held Night Vision or Short Sighted (held when the mod would add it) is never removed; Evolving Traits World's Cat Eyes composes (it grants, never removes)",
        "whether the regeneration tier scales awake regeneration is unmeasured (X80 open); healMul reaches the four setters with that stated",
        "the per-part folds rescale the engine's own change since the last minute: a wound timer or bleeding time the engine has run to 0 is passed through, so a wound's last fraction heals unscaled",
        "the closed day's energy availability reads the exercise kcal banked up to the minute before the close (Metabolism zeroes exKcalDay at its close)",
        "the protein side of the protein-energy grade reads unknown (grade 1) until the 7-day protein ring holds seven closed days",
        "the refeeding sickness floor holds for the refeeding event's day (record.acute.refeedEvent is set at a day close and held to the next)",
        "a spontaneous bruise rolls with ZombRandFloat; with no ZombRandFloat the roll reads 1.0 and no bruise fires",
        "a dead character's record is stepped but no trait, body or health write is made",
        "the sleep-onset latency terms (solAddH, solMul) reach only the fast kernel's delay mirror, which gates nothing while the record owns FATIGUE (the acute kernel decays S from the first asleep minute): caffeine's, exercise's and alcohol's onset latency is unapplied — a Plan 6 reading",
        "the cold fold (catchACold's rise × coldMul) is unmeasured (X105): on the x161b fixture the thermoregulator's catch-a-cold delta stayed under the engine's 0.1 gate, so no rise was folded",
    },
}
local EFF = NR.server.effects

-- The four regeneration constants' engine defaults (the BodyDamage constructor, #2354), scaled by healMul or
-- written 0 while a drain is active (ruling 13; S1174 open).
EFF.REGEN_STANDARD = 0.002 -- VANILLA #2354
EFF.REGEN_REDUCED = 0.0013 -- VANILLA #2354
EFF.REGEN_SEVERE = 0.0008 -- VANILLA #2354
EFF.REGEN_SLEEPING = 0.02 -- VANILLA #2354
-- The engine's cap on a part's wound-infection level (BodyPart.DamageUpdate @1296-@1309 L351-L352).
EFF.INFECT_MAX = 10 -- VANILLA #3131 (BodyPart.DamageUpdate caps the level at 10)
-- The body-part packet masks: bit = key - 1 (#2626).
EFF.MASK_BLEEDING = 8 -- key 4, bleeding (#2626)
EFF.MASK_BLEEDING_TIME = 131072 -- key 18, bleedingTime (#2626)
EFF.MASK_INFECTION = 32768 -- key 16, woundInfectionLevel (#2626)
-- The sleep-onset terms (B6), game hours and a multiplier on vanilla's delay.
EFF.SOL_CAF_H = 0.15 -- h at full caffeine saturation: S0795 (+9 min), S0798 (+8.35 min)
EFF.SOL_VIG_H = 0.15 -- h after vigorous exercise within 1 h: S0827 direction; game choice (open S1130)
EFF.SOL_ALC_MUL = 0.6 -- at the alcohol band 2 (>= 0.85 g/kg): S0813 direction; game choice (open S1128)
-- The engine factors (B3, B4): vanilla's own trait multipliers on accrual and recovery.
EFF.TRAIT_NEEDS_LESS_ACC = 0.7 -- VANILLA #2271 (updateStats_Awake)
EFF.TRAIT_NEEDS_MORE_ACC = 1.3 -- VANILLA #2271 (updateStats_Awake)
EFF.FF_INSOMNIAC = 0.5 -- VANILLA #2276
EFF.FF_NIGHT_OWL = 1.4 -- VANILLA #2276
EFF.T_NEEDS_LESS = 0.75 -- VANILLA #2276
EFF.T_NEEDS_MORE = 1.18 -- VANILLA #2276
-- The exertion at which the dehydration heat side applies (G).
EFF.MET_EXERT = 3 -- MET: game choice, the formulas briefing G (open S1160)
-- The days of protein data the 7-day ring must hold before the protein side is read.
EFF.P7_DAYS = 7 -- the ring's length, no row needed

-- The per-part fields the folds read and write: { last key, getter, setter }.
EFF.WOUNDS = {
    { "scratch", "getScratchTime", "setScratchTime" },
    { "cut", "getCutTime", "setCutTime" },
    { "deep", "getDeepWoundTime", "setDeepWoundTime" },
    { "bite", "getBiteTime", "setBiteTime" },
    { "burn", "getBurnTime", "setBurnTime" },
    { "fracture", "getFractureTime", "setFractureTime" },
}

-- File-scope scratch tables, overwritten per call: no allocation per minute.
EFF.b = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }
EFF.flags = { anaemia = false, allReplete = false, vitDClinical = false, hang = false, refeedEvent = false,
              frozen = false, bgroupMax = 1, coldCredit = false, boutVig = false }
-- The heal reference, made once on first use.
EFF.ref = nil
-- The options a load with no options file reads: one file-scope table, never written.
local EMPTY = {}

local finite = NR.finite



-- A number read off obj:name(...), or dflt when the member is absent or the answer is not finite.
local num = NR.num





-- An object read off obj:name(...), or nil.
local obj = NR.obj





-- A boolean read off obj:name(...): true only when the member is present and answers true.
local flag = NR.flag




-- A uniform roll in [0, 1) from ZombRandFloat, or dflt when the global is absent or the answer is not finite.
local function roll(dflt)
    if ZombRandFloat == nil then return dflt end
    local ok, v = pcall(ZombRandFloat, 0, 1)
    if ok and finite(v) then return v end
    return dflt
end

-- The fields this adapter adds beside K.effects.new's own, with their fresh values.
local function addFields(E, body)
    if E.lastDay == nil then E.lastDay = body.dayIndex end
    if E.exSeen == nil then E.exSeen = 0 end
    if E.tempAdj == nil then E.tempAdj = 0 end
    if E.dirty == nil then E.dirty = false end
    if type(E.own) ~= "table" then E.own = { nv = false, ss = false } end
    if type(E.key) ~= "table" then E.key = K.effects.new().key end
    if type(E.key.b) ~= "table" then E.key.b = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 } end
end

-- The heal: every numeric field of record.effects (and of its key) finite, else its fresh value; a key field
-- healed to its fresh value forces a rebuild. Backfill of a missing field is uncounted.
local healBad = nil
local function healTable(t, ref, prefix)
    for k, v in pairs(t) do
        if type(v) == "number" and not finite(v) then
            local nv = ref[k]
            if type(nv) ~= "number" then nv = 0 end
            t[k] = nv
            if healBad == nil then healBad = prefix .. tostring(k) else healBad = healBad .. "," .. prefix .. tostring(k) end
        end
    end
end

local function heal(username, E, body)
    healBad = nil
    if EFF.ref == nil then
        EFF.ref = K.effects.new()
        EFF.ref.exSeen = 0
        EFF.ref.tempAdj = 0
    end
    EFF.ref.lastDay = body.dayIndex
    healTable(E, EFF.ref, "effects.")
    healTable(E.key, EFF.ref.key, "effects.key.")
    healTable(E.key.b, EFF.ref.key.b, "effects.key.b.")
    if healBad ~= nil then
        EFF.stats.healed = EFF.stats.healed + 1
        EFF.lastHealed = healBad
        NR.log.say(2, "effects: non-finite " .. healBad .. " for " .. tostring(username) .. "; stamped fresh")
    end
end

-- The transient per-username memory (never persisted): the record it belongs to, the last regeneration
-- multiplier written, the per-part last values and the last catchACold. A new record (a respawn) or a first
-- sight starts it afresh, so the regeneration constants are re-asserted then.
local function memory(username, record)
    local L = EFF.last[username]
    if L == nil or L.rec ~= record then
        L = { rec = record, regen = nil, parts = {}, cold = nil }
        EFF.last[username] = L
    end
    return L
end

-- Forget a player's transient memory (Players' onFirstSight and onDeparture lists).
function EFF.forget(username)
    if username ~= nil then EFF.last[username] = nil end
end

-- The protein-energy grade and the closed day's energy availability, at a day close (F1, A4). The protein
-- mean is nil (unknown) until the 7-day ring holds seven closed days (the character's birth day from bornAge).
local function closeDay(E, record, body, closing)
    local a = record.acute
    local w = body.fm + body.lm
    local pMean = nil
    if finite(body.bornAge) and type(body.p7) == "table" and w > 0
        and body.dayIndex - math.floor(body.bornAge / 24) >= EFF.P7_DAYS then
        local sum = 0
        for i = 1, EFF.P7_DAYS do
            sum = sum + (body.p7[i] or 0)
        end
        pMean = sum / EFF.P7_DAYS / w
    end
    local bmi, starved = 0, 0
    if finite(a.bmi) then bmi = a.bmi end
    if finite(a.starvedDays) then starved = a.starvedDays end
    E.pe = K.effects.peGrade(bmi, starved, pMean)
    if not closing then return end
    if finite(body.inDayClosed) and finite(body.lm) and body.lm > 0 then
        E.ea = (body.inDayClosed - E.exSeen) / body.lm
    end
    EFF.stats.closes = EFF.stats.closes + 1
end

-- The fast handler's last input table for this player, or nil (no handle yet).
local function fastInput(username)
    local F = NR.server.fast
    if F == nil then return nil end
    if type(F.lastInp) == "table" and type(F.lastInp[username]) == "table" then return F.lastInp[username] end
    if type(F.h) == "table" and type(F.h[username]) == "table" and type(F.h[username].inp) == "table" then
        return F.h[username].inp
    end
    return nil
end

-- The engine parts of accrual and recovery (B3, B4) off the fast handler's last input: mEngine(endurance,
-- resting, thermoFatigue, sleepTrait, StatsDecrease) and rEngine(bed, ff / t). A missing or non-finite
-- input reads its neutral.
local function engineFactors(username)
    local inp = fastInput(username)
    if inp == nil then
        return K.effects.mEngine(1, false, 1, 1, 1), K.effects.rEngine(1, 1)
    end
    local endLast = finite(inp.endLast) and inp.endLast or nil
    if endLast == nil or inp.endFold ~= true then
        endLast = finite(inp.endurance) and inp.endurance or 1
    end
    local resting = inp.sitting == true or inp.resting == true
    local thermo = finite(inp.thermoFatigue) and inp.thermoFatigue or 1
    local sd = finite(inp.sd) and inp.sd or 1
    local sleepTrait = 1
    if inp.needsLess == true then sleepTrait = EFF.TRAIT_NEEDS_LESS_ACC end
    if inp.needsMore == true then sleepTrait = EFF.TRAIT_NEEDS_MORE_ACC end
    local ff = 1
    if inp.insomniac == true then ff = ff * EFF.FF_INSOMNIAC end
    if inp.nightOwl == true then ff = ff * EFF.FF_NIGHT_OWL end
    local t = 1
    if inp.needsLess == true then
        t = EFF.T_NEEDS_LESS
    elseif inp.needsMore == true then
        t = EFF.T_NEEDS_MORE
    end
    local bed = finite(inp.bedFactor) and inp.bedFactor or 1
    return K.effects.mEngine(endLast, resting, thermo, sleepTrait, sd), K.effects.rEngine(bed, ff / t)
end

-- One trait under the four rules (spec § 4.5): the ownership flag is set before an add and checked before a
-- remove; an owned trait not held is re-added every minute; a trait held while the mod did not add it is never
-- removed. Returns whether the collection changed.
local function toggle(coll, t, want, own, key)
    if t == nil or coll == nil then return false end
    local held = flag(coll, "get", t)
    if want then
        if not held then
            local reassert = own[key] == true
            own[key] = true
            if NR.call(coll, "add", t) then
                if reassert then
                    EFF.stats.reasserts = EFF.stats.reasserts + 1
                else
                    EFF.stats.traitAdds = EFF.stats.traitAdds + 1
                end
                return true
            end
        end
        return false
    end
    if own[key] == true then
        own[key] = false
        if held and NR.call(coll, "remove", t) then
            EFF.stats.traitRemoves = EFF.stats.traitRemoves + 1
            return true
        end
    end
    return false
end

-- The two trait toggles and the one push (rule 3: only on a change, only to the owner).
local function traits(player, record, body, E, nut, sev, dtD)
    local vitA = nut.vitA
    local zinc, iron, ribo = nut.zinc, nut.iron, nut.riboflavin
    local sex = body.sex
    local rec = NR.data.records.REC.vitA
    local R = rec ~= nil and rec.R ~= nil and rec.R[sex] or nil
    local retOk = finite(R) and finite(record.acute.retEma) and record.acute.retEma >= R
    local wantNv = K.effects.nvMinute(E, vitA.g, zinc.g, iron.g, ribo.g, retOk, dtD)
    local wantSs = K.effects.ssWant(vitA.g, sev)
    if record.dead == true then return false end
    if CharacterTrait == nil then return false end
    local coll = obj(player, "getCharacterTraits")
    if coll == nil then return false end
    local changed = toggle(coll, CharacterTrait.NIGHT_VISION, wantNv, E.own, "nv")
    changed = toggle(coll, CharacterTrait.SHORT_SIGHTED, wantSs, E.own, "ss") or changed
    if changed then
        if sendSyncPlayerFields == nil then
            EFF.stats.pushMissing = EFF.stats.pushMissing + 1
        else
            local ok = pcall(sendSyncPlayerFields, player, 2)
            if ok then EFF.stats.pushes = EFF.stats.pushes + 1 else EFF.stats.pushMissing = EFF.stats.pushMissing + 1 end
        end
    end
    return changed
end

-- The four regeneration setters at m x their defaults (#2354), index-first.
local function regen(bd, m)
    NR.call(bd, "setStandardHealthAddition", EFF.REGEN_STANDARD * m)
    NR.call(bd, "setReducedHealthAddition", EFF.REGEN_REDUCED * m)
    NR.call(bd, "setSeverlyReducedHealthAddition", EFF.REGEN_SEVERE * m)
    NR.call(bd, "setSleepingHealthAddition", EFF.REGEN_SLEEPING * m)
    EFF.stats.regenWrites = EFF.stats.regenWrites + 1
end

-- A wound timer's fold (F3, ruling 17): a fall since the last minute is scaled by healMul; a timer the engine
-- ran to 0 is passed through. Returns the value now on the part.
local function foldWound(part, last, getter, setter, healMul)
    local v = num(part, getter, nil)
    if v == nil then return nil end
    if last ~= nil and v < last and v > 0 then
        local nv = last - (last - v) * healMul
        if NR.call(part, setter, nv) then
            EFF.stats.partWrites = EFF.stats.partWrites + 1
            return nv
        end
    end
    return v
end

-- The per-part folds: wound timers x healMul, bleeding time's fall / bleedMul, the infection level's rise x
-- infectMul then syncBodyPart (gate 1: the immediate carrier). A group at identity makes no Java call and
-- forgets its last values, so its first active minute folds nothing it did not see.
local function partFolds(bd, L, E)
    local healOn = E.healMul < 1
    local bleedOn = E.bleedMul > 1
    local infectOn = E.infectMul > 1
    if not (healOn or bleedOn or infectOn) then
        L.parts = {}
        return
    end
    local list = obj(bd, "getBodyParts")
    local okN, n = NR.call(list, "size")
    if not okN or not finite(n) then return end
    local wounds = EFF.WOUNDS
    -- the parts list is a Java list, walked by size()/get(i) (#0940); WOUNDS is this file's Lua array, so # is its length
    for i = 0, n - 1 do
        local okP, part = NR.call(list, "get", i)
        if okP and part ~= nil then
            local last = L.parts[i]
            if last == nil then
                last = {}
                L.parts[i] = last
            end
            if healOn then
                for j = 1, #wounds do
                    local w = wounds[j]
                    last[w[1]] = foldWound(part, last[w[1]], w[2], w[3], E.healMul)
                end
            else
                for j = 1, #wounds do
                    last[wounds[j][1]] = nil
                end
            end
            if bleedOn then
                local v = num(part, "getBleedingTime", nil)
                if v ~= nil and last.bleed ~= nil and v < last.bleed and v > 0 then
                    local nv = last.bleed - (last.bleed - v) / E.bleedMul
                    if NR.call(part, "setBleedingTime", nv) then
                        EFF.stats.partWrites = EFF.stats.partWrites + 1
                        v = nv
                    end
                end
                last.bleed = v
            else
                last.bleed = nil
            end
            if infectOn then
                local v = num(part, "getWoundInfectionLevel", nil)
                if v ~= nil and last.infect ~= nil and v > last.infect then
                    local nv = K.min(last.infect + (v - last.infect) * E.infectMul, EFF.INFECT_MAX)
                    if NR.call(part, "setWoundInfectionLevel", nv) then
                        EFF.stats.partWrites = EFF.stats.partWrites + 1
                        v = nv
                        if syncBodyPart ~= nil and pcall(syncBodyPart, part, EFF.MASK_INFECTION) then
                            EFF.stats.infectSyncs = EFF.stats.infectSyncs + 1
                        end
                    end
                end
                last.infect = v
            else
                last.infect = nil
            end
        end
    end
end

-- The cold fold (F3, ruling T1-3): a rise of catchACold since the last minute is scaled by coldMul; a fall and
-- the zero reset pass through. At identity no Java call is made and the last value is forgotten.
local function coldFold(bd, L, E)
    if E.coldMul == 1 then
        L.cold = nil
        return
    end
    local c = num(bd, "getCatchACold", nil)
    if c == nil then return end
    if L.cold ~= nil and c > L.cold then
        local nc = L.cold + (c - L.cold) * E.coldMul
        if NR.call(bd, "setCatchACold", nc) then
            EFF.stats.coldWrites = EFF.stats.coldWrites + 1
            c = nc
        end
    end
    L.cold = c
end

-- The spontaneous bruise (F4): with probability E.bruise per game minute (0 unless vitamin C is clinical; the
-- Severity dial already applied), a random part starts bleeding at BRUISE_T0, synced at once.
local function bruise(bd, L, E, dtM)
    if not (E.bruise > 0) then return end
    if roll(1.0) >= E.bruise * dtM then return end
    local list = obj(bd, "getBodyParts")
    local okN, n = NR.call(list, "size")
    if not okN or not finite(n) or n < 1 then return end
    local i = K.clamp(math.floor(roll(0) * n), 0, n - 1)
    local okP, part = NR.call(list, "get", i)
    if not okP or part == nil then return end
    local t0 = NR.data.effects.BRUISE_T0
    NR.call(part, "setBleedingTime", t0) -- the jar sets bleeding from a positive time unless the part is bandaged (BodyPart.setBleedingTime): a bruise respects a bandage, so no setBleeding(true)
    if syncBodyPart ~= nil then pcall(syncBodyPart, part, EFF.MASK_BLEEDING + EFF.MASK_BLEEDING_TIME) end
    local last = L.parts[i]
    if last ~= nil and last.bleed ~= nil then last.bleed = t0 end
    EFF.stats.bruises = EFF.stats.bruises + 1
end

local function step(username, player, record, body, dtM, ageH)
    body = body or record.body
    local nut, fluids, a = record.nutrients, record.fluids, record.acute
    if body == nil or nut == nil or fluids == nil or a == nil then return end
    if not finite(dtM) then dtM = 1 end
    if not finite(ageH) then ageH = nut.lastAgeH end
    local w = body.fm + body.lm
    local O = NR.server.options or EMPTY
    local sev = finite(O.severity) and O.severity or 1
    local canKill = O.deficienciesCanKill ~= false
    local bonusOn = O.balanceBonus ~= false
    local excessOn = O.excessEffectsOn ~= false
    local T = NR.data.effects

    -- 1. ensure and heal
    local E = record.effects
    if type(E) ~= "table" then
        E = K.effects.new()
        record.effects = E
        addFields(E, body)
        closeDay(E, record, body, false)              -- pe from the current state; ea waits for a seen close
    end
    addFields(E, body)
    -- PROTO heal1 (Plan 10c H1, E2): the pre-step heal removed; the one heal is the post-step pass (12.)
    local L = memory(username, record)

    -- the day close: the protein-energy grade and the closed day's energy availability
    if body.dayIndex ~= E.lastDay then
        closeDay(E, record, body, true)
        E.lastDay = body.dayIndex
    end
    if finite(body.exKcalDay) then E.exSeen = body.exKcalDay end

    -- 2. the bands and the flags (file-scope scratch tables)
    local okS, asleep = NR.call(player, "isAsleep")
    asleep = okS and asleep == true
    K.effects.bands(EFF.b, a, fluids)
    local F = EFF.flags
    F.anaemia = nut.anaemia == true
    F.allReplete = nut.allReplete == true
    F.vitDClinical = nut.vitDClinical == true
    F.hang = a.hang == 1
    F.refeedEvent = a.refeedEvent == true
    F.frozen = a.frozen == true
    F.bgroupMax = K.effects.bgroupMax(nut)
    F.coldCredit = K.effects.coldCredit(nut.vitC.g, nut.vitC.e24, body.band1Day or 0, body.band2Day or 0, a.coldH)
    F.boutVig = asleep and a.boutVig == true
    -- the Severity term sits above the flag terms at a 0.001 resolution, so no fractional dial can collide with a flag
    local dials = math.floor(sev * 1000 + 0.5) * 1000000 + (canKill and 100 or 0) + (bonusOn and 10 or 0) + (excessOn and 1 or 0)
        + (F.coldCredit and 10000 or 0) + (F.boutVig and 100000 or 0)

    -- 3. the rebuild, only on a moved key
    local rebuilt = false
    if K.effects.changed(E.key, nut.epoch, E.lastDay, dials, EFF.b) then
        K.effects.compose(E, T, nut, EFF.b, E.pe, E.ea, F, sev, bonusOn, T.VITD_EFFECTS)
        K.effects.stampKey(E.key, nut.epoch, E.lastDay, dials, EFF.b)
        rebuilt = true
        EFF.stats.rebuilds = EFF.stats.rebuilds + 1
    end

    -- 4. the per-minute scalars
    E.fOff = K.effects.fOff(a.debtH, a.caf, a.cafTol, E.fOffNut)
    local mEng, rEng = engineFactors(username)
    E.mAcc = K.clamp(E.mNut * mEng, K.effects.M_LO, K.effects.M_HI)
    E.rRec = K.clamp(E.rNut * rEng, K.effects.R_LO, K.effects.R_HI)
    local solAdd = EFF.SOL_CAF_H * K.effects.satC(a.caf)
    if not asleep and finite(a.lastVigAgeH) and ageH - a.lastVigAgeH <= K.acute.VIG_WINDOW_H then
        solAdd = solAdd + EFF.SOL_VIG_H
    end
    E.solAddH = solAdd
    E.solMul = 1
    if EFF.b[K.effects.B.alc] >= 2 then E.solMul = EFF.SOL_ALC_MUL end
    E.intoxTarget = K.effects.intoxTarget(a.bac)
    local met = finite(body.met) and body.met or 1
    local adj = E.tempOffset
    if met >= EFF.MET_EXERT then adj = adj + E.tempHeat end
    E.tempAdj = adj
    local bd = obj(player, "getBodyDamage")
    local setPoint = num(obj(bd, "getThermoregulator"), "getSetPoint", nil)
    if setPoint == nil or adj == 0 then
        E.tempTarget = 0
    else
        E.tempTarget = setPoint + adj
    end

    -- 5. the traits (the night-vision machine runs even for a dead record; the writes do not)
    local changedTraits = traits(player, record, body, E, nut, sev, dtM / 1440)

    -- 6. the drain (kernel order: compose, nvMinute, drain)
    local wasLethal = E.lethal
    local d = K.effects.drain(E, nut, fluids, a, E.pe, w > 0 and body.fm / w or 0, body.sex, canKill)

    if record.dead == true then
        EFF.stats.skippedDead = EFF.stats.skippedDead + 1
    elseif bd ~= nil then
        -- 7. the regeneration setters: on a rebuild, a drain start or stop, a new healMul and at first sight
        local m = E.healMul
        if d > 0 then m = 0 end
        if rebuilt or L.regen == nil or L.regen ~= m or wasLethal ~= E.lethal then
            regen(bd, m)
            L.regen = m
        end
        -- 8. the per-part folds and the cold fold
        partFolds(bd, L, E)
        coldFold(bd, L, E)
        -- 9. the bruise
        bruise(bd, L, E, dtM)
        -- 10. the drain's health write
        if d > 0 then
            NR.call(bd, "ReduceGeneralHealth", d * dtM)
            EFF.stats.drainMinutes = EFF.stats.drainMinutes + 1
        end
    end

    -- 11. the mirror marked dirty when the set or a trait changed
    if rebuilt or changedTraits then
        E.dirty = true
        local bus = NR.server.bus
        if bus ~= nil and bus.markEffects ~= nil then bus.markEffects(username) end
    end

    -- 12. the stamps, every one finite
    heal(username, E, body)
end

-- One player's minute, called by EFF.step on the inputs Nutrients stamped (ruling 22). One pcall around
-- the body: a failure is kept and logged on the slow clock, never raised into the pipeline.
function EFF.minute(username, player, record, body, dtM, ageH)
    if record == nil then return end
    EFF.stats.minutes = EFF.stats.minutes + 1
    local ok, err = pcall(step, username, player, record, body, dtM, ageH)
    if not ok then
        EFF.stats.errors = EFF.stats.errors + 1
        EFF.lastError = err
        NR.log.say(2, "effects: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

-- The pipeline's effects step: it runs only when the nutrients step reached the end of its minute and
-- stamped ctx.body, ctx.dtM and ctx.ageH (where 1.0.0's hand call sat), and keeps that call's guard, its
-- counter (NR.server.nutrients.stats.effectsErrors) and its log line.
function EFF.step(username, player, record, ctx)
    if ctx == nil or ctx.body == nil then return end
    local okE, errE = pcall(EFF.minute, username, player, record, ctx.body, ctx.dtM, ctx.ageH)
    if not okE then
        local NUT = NR.server.nutrients
        if NUT ~= nil then NUT.stats.effectsErrors = NUT.stats.effectsErrors + 1 end
        NR.log.say(2, "nutrients: the effects step failed for " .. tostring(username) .. ": " .. tostring(errE))
    end
end

-- Wiring: the effects step registered by name; the transient memory is forgotten at first sight
-- (a join, a respawn) and departure, so the regeneration constants are re-asserted after a load.
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if EFF.wired then return end
        EFF.wired = true
        NR.server.minute.register("effects", EFF.step)
        local P = NR.server.players
        if P == nil then return end
        P.onFirstSight[#P.onFirstSight + 1] = EFF.forget
        P.onDeparture[#P.onDeparture + 1] = EFF.forget
    end)
end
