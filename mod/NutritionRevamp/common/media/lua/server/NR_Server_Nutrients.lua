-- NR_Server_Nutrients.lua -- the record engine, the fast pools and the acute states on the slow clock
-- (Plan 4, spec § 4.4): once per player per game minute, on the players' OnTick stagger and after the
-- stomach step (NR_Server_Kinetics) and the body step (NR_Server_Metabolism), it consumes the minute's
-- absorbed vector, steps the per-nutrient records (K.nutrients over NR.data.records with K.interact.two),
-- the water and electrolyte pools and the thirst view (K.fluids), and the acute states (K.acute), and
-- stamps every result on three record sub-tables: record.nutrients, record.fluids and record.acute.
--
-- Order (plan ruling 17): the pipeline's declared ORDER (NR_Server_Minute, Plan 10 R2) runs Kinetics,
-- Metabolism, Nutrients (this file), Effects, Strength, Weight; each registers its step at OnServerStarted
-- (Training has no minute step). NR_Server_Options loads before NR_Server_Players and so polls on
-- EveryOneMinute directly, ahead of the drain. Metabolism reads the absorbed handoff's four macros first;
-- this file then consumes it (the context lives one player's minute). Metabolism's dmod/rmod
-- read the PREVIOUS minute's scalars stamped here (a one-minute lag, stated in the limitations).
--
-- Plan 4 writes no stat, moodle or health: every value here is mod state for Plan 5 and the mirror.
-- Every Java read goes through NR.call (index-first) with a default; every Java global is named only
-- inside a function behind a nil check, so the file loads with no engine
-- (testing/tests/kernel/test_nutrients_shape.py). The whole minute runs under one pcall per player and
-- never raises into the players walk. Every field written on the record is a number, a boolean, a
-- string or a table of numbers (#1495). Slow-clock code: no @fastpath region in this file.
--
-- The x151r fix wave: the calcium x iron factor reads the meal calcium in the stomach before the minute's
-- emptying (NR_Server_Kinetics' mealCa handoff on the context; ruling T17-1, #2981), and caffeine and ethanol reach
-- the acute states through the gut lane (ruling T17-2, #2982/#2983): the intake landing's pending sums are
-- drained into record.acute.gutAlc / gutCaf, K.acute.absorbGut releases them, and the released doses feed
-- the alcohol and caffeine steps, the urinary losses and the alcohol diuresis. The stomach's absorbed
-- ethanol and caffeine, 0 for every vector landed since the fix, are added to the released doses, so a
-- buffer that held them before the fix still delivers them.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.nutrients = {
    stats = { players = 0, minutes = 0, healed = 0, errors = 0, badAge = 0, noBody = 0, days = 0,
              skippedDays = 0, effectsErrors = 0 },
    lastError = nil,
    lastHealed = nil,
    wired = false,
    sleepDisabled = false,
    limitations = {
        "the one-minute lag: Metabolism's dmod and rmod read the previous minute's nutrient, fluid and acute stamps",
        "metabolic water is omitted (S1093 reads the water AI as turnover)",
        "respiratory water loss is 0 beyond basal (S1052 open)",
        "caffeine diuresis is 0 for a habitual drinker (S0528/S0529)",
        "liver glycogen is not modelled (S0110 open)",
        "the sleep state freezes at rested while the server's SleepAllowed and SleepNeeded are not both true (x151s, #2947): the engine resets FATIGUE ahead of the hook",
        "the thirst view reads the water pool plus the stomach's pending water (ruling T1-1); the performance dehydration is the pool alone",
        "auto-drink litres land in the stomach once per slow minute (the fast handler skips its call while a drop is pending: Task 12)",
        "raw-egg biotin detection is absent until the food data carries an isRawEgg flag (rawEggDay is always false)",
        "the first Nutrients minute on a new record integrates no time (its absorbed vector is dropped; Metabolism already credited it) and also drops that minute's absorbed water",
        "before the first day close the protein-scaled requirements read P_LOW x w (Plan 3's pPrevKg backfill)",
        "a step longer than 60 minutes (offline time) is integrated as 60 minutes; a multi-day jump closes one refeeding day",
        "the potassium-depletion refeeding criterion reads false (no row grades potassium)",
        "Plan 4 writes no stat, moodle or health; INTOXICATION and FATIGUE are vanilla's until Plan 5",
        "caffeine and ethanol absorb on a 0.5 h gut lane that a full stomach does not slow (ruling T17-2; S1102 open): a drink with a meal peaks as early as one on an empty stomach",
        "the interaction factors read the stomach buffer's phytate, vitC and calcium before each minute's emptying (ruling T17-1): two meals in the buffer act as one meal, and the inhibition eases as the buffer empties",
        "a sleep bout tolerates awake gaps under 10 game minutes (ruling T17-4, S1112 open): a real wake of under 10 minutes inside a night counts as sleep for hours awake",
        "vitamin D has no cutaneous term (kSun 0, S1064 open): every character trends to its dietary steady state (clinical in ~153 d at zero intake; ~5 d at OnsetSpeed 30)",
        "SleepAllowed/SleepNeeded are read once at OnServerStarted; a runtime change of the server options is not followed",
        "the fat factor reads the stomach buffer's lipids before each minute's emptying (ruling T19-1): it eases as the meal empties, so a 30 g-fat meal absorbs 90 % of its retinol and vitK and three 10 g-fat meals a day 81 %",
        "the minute's training band is read off the growth of Metabolism's day accumulators band1Day/band2Day (no per-minute band is stamped); a minute whose day close skipped days reads the new day's growth alone",
    },
}
local NUT = NR.server.nutrients

-- The per-minute context tables, overwritten on every call: no allocation per minute.
NUT.ctx = {}
NUT.fctx = {}
NUT.kMul = {}
-- The water vector an auto-drink lands in the stomach, made once on first use and rewritten per use.
NUT.waterVec = nil
-- The heal references, made once on first use: a fresh key state, fluids and acute table.
NUT.refKey = nil
NUT.refFluids = nil
NUT.refAcute = nil
NUT.refNut = nil

-- The handoff a minute with no absorbed or ingested vector reads: one file-scope table, never written.
local EMPTY = {}

-- The stomach fill above which the stomach counts as fed (the glucose term's empty-stomach clock).
NUT.FED_FILL = 0.05 -- game choice: a stomach below 5 % of full is empty for the alcohol-fasting glucose term
-- The alcohol-history refeeding criterion: the 7-day mean daily alcohol above this, g per kg.
NUT.ALC_HISTORY_GKG = 0.5 -- game choice: S0115 names alcohol misuse with no dose; no row
-- The 7-day mean's daily weight.
NUT.ALC_EMA_DAYS = 7 -- game choice: the 7-day window
-- The NEEDS_MORE_SLEEP and NEEDS_LESS_SLEEP factors on the sleep need: the engine's own awake-fatigue
-- trait multipliers (#2271, updateStats_Awake 1.3 / 0.7); their use as a need factor a game choice on S0740.
NUT.NEED_MORE = 1.3 -- #2271 (updateStats_Awake); the reuse a game choice
NUT.NEED_LESS = 0.7 -- #2271 (updateStats_Awake); the reuse a game choice
-- The magnesium grade at which the refeeding risk reads magnesium-depleted (S0115's low-magnesium criterion).
NUT.MG_DEPLETED_GRADE = 3 -- game choice: the depleted rung of the magnesium record
-- The litres one unit of THIRST drop stands for: Water's ThirstChange -50 per litre = 0.5 THIRST per litre (ruling 9).
NUT.LITRES_PER_THIRST = 2 -- ruling 9 (Water ThirstChange -50 per litre, x151w #2932/#2939)

local finite = NR.finite



-- The world age, or nil when it cannot be read or is not finite (the minute is then skipped and counted:
-- the acute kernel's sleep-window loop needs a finite age).
local worldAge = NR.worldAge







-- A number read off obj:name(...), or dflt when the member is absent or the answer is not finite.
local num = NR.num





-- An object read off obj:name(...), or nil.
local obj = NR.obj





-- A uniform roll in [0, 1) from ZombRandFloat, or dflt when the global is absent or the answer is not finite.
local function roll(dflt)
    if ZombRandFloat == nil then return dflt end
    local ok, v = pcall(ZombRandFloat, 0, 1)
    if ok and finite(v) then return v end
    return dflt
end

-- The server's sleep options, read once at OnServerStarted (the Task 5 verdict, x151s #2947/#2948): the
-- engine resets an out-of-handler FATIGUE write unless SleepAllowed and SleepNeeded are both true, so the
-- sleep state freezes when they are not. An unreadable option reads true (sleep NOT disabled).
function NUT.readSleepOptions()
    local allowed, needed = true, true
    if getServerOptions ~= nil then
        local ok, so = pcall(getServerOptions)
        local okA, a = NR.call(ok and so or nil, "getBoolean", "SleepAllowed")
        if okA and type(a) == "boolean" then allowed = a end
        local okN, n = NR.call(ok and so or nil, "getBoolean", "SleepNeeded")
        if okN and type(n) == "boolean" then needed = n end
    end
    NUT.sleepDisabled = not (allowed and needed)
    if NUT.sleepDisabled then
        NR.log.say(2, "nutrients: SleepAllowed=" .. tostring(allowed) .. " SleepNeeded=" .. tostring(needed)
            .. ": the sleep state freezes at rested")
    end
    return NUT.sleepDisabled
end

-- The sleep-need factor off the character's trait set (the CharacterTrait registry objects).
local function needFactor(player)
    if CharacterTrait == nil then return 1 end
    local traits = obj(player, "getCharacterTraits")
    local tMore, tLess = CharacterTrait.NEEDS_MORE_SLEEP, CharacterTrait.NEEDS_LESS_SLEEP
    if tMore ~= nil then
        local okM, more = NR.call(traits, "get", tMore)
        if okM and more == true then return NUT.NEED_MORE end
    end
    if tLess ~= nil then
        local okL, less = NR.call(traits, "get", tLess)
        if okL and less == true then return NUT.NEED_LESS end
    end
    return 1
end

-- The heal: every numeric field of the three sub-tables finite, else its fresh value. A field with no fresh
-- value takes its named default; one with neither (iron S and H, calcium bone, laid lazily by K.interact.two)
-- is cleared so the kernel re-initialises it. healBad collects the healed names of one pass.
local healBad = nil
local function healTable(t, ref, prefix, ageH, ageFields)
    for k, v in pairs(t) do
        if type(v) == "number" and not finite(v) then
            local nv = ref[k]
            if ageFields ~= nil and ageFields[k] then nv = ageH end
            t[k] = nv
            if healBad == nil then healBad = prefix .. tostring(k) else healBad = healBad .. "," .. prefix .. tostring(k) end
        end
    end
end

NUT.AGE_NUT = { lastAgeH = true }
NUT.AGE_ACUTE = { winStartH = true, mass90ageH = true, lastFedAgeH = true }

local function heal(username, record, body, ageH)
    healBad = nil
    if NUT.refKey == nil then
        NUT.refKey = K.nutrients.newKey()
        NUT.refFluids = K.fluids.new(nil, nil, nil)
        NUT.refFluids.viewPct = 0
        NUT.refAcute = K.acute.new(0)
        NUT.refAcute.alc7 = 0
        NUT.refAcute.alcDayG = 0
        NUT.refAcute.lastB1 = 0
        NUT.refAcute.lastB2 = 0
        NUT.refNut = { nv = K.nutrients.NV, epoch = 0, ironGrade = 1, lastDayIndex = 0 }
    end
    local n = record.nutrients
    NUT.refNut.lastDayIndex = body.dayIndex
    healTable(n, NUT.refNut, "nutrients.", ageH, NUT.AGE_NUT)
    local order = NR.data.records.ORDER
    -- ORDER is a Lua table the record file built, so # is a Lua length, never a Java list (#0940).
    for i = 1, #order do
        local s = n[order[i]]
        if type(s) == "table" then healTable(s, NUT.refKey, "nutrients." .. order[i] .. ".", ageH, nil) end
    end
    healTable(record.fluids, NUT.refFluids, "fluids.", ageH, nil)
    healTable(record.acute, NUT.refAcute, "acute.", ageH, NUT.AGE_ACUTE)
    if healBad ~= nil then
        NUT.stats.healed = NUT.stats.healed + 1
        NUT.lastHealed = healBad
        NR.log.say(2, "nutrients: non-finite " .. healBad .. " for " .. tostring(username) .. "; stamped fresh")
    end
end

-- Ensure the three sub-tables. The sweat multiplier and sweat sodium are drawn once per character: the multiplier uniform over
-- its range, the sodium as 10 + 80 r^2 (mean 36.7; fallback with no ZombRandFloat: the multiplier 1.0 and 37 mmol/L); the
-- slow-metaboliser trait once (fallback roll 0.75: not slow; ruling T9-1).
local function ensure(record, body, ageH)
    if record.nutrients == nil then
        record.nutrients = K.nutrients.newState(NR.data.records)
    end
    if record.fluids == nil then
        local sk = K.fluids.SWEATK_RANGE
        local sweatK = sk[1] + (sk[2] - sk[1]) * roll(0.5)
        -- the fallback roll is the one that lands on 37 exactly: sqrt(27/80); the draw is the kernel's
        local naSweat = K.fluids.naSweatOf(roll(math.sqrt(27 / 80)))
        record.fluids = K.fluids.new(body.lm, sweatK, naSweat)
    end
    if record.acute == nil then
        record.acute = K.acute.new(ageH)
        record.acute.slowMet = K.acute.drawSlowMet(roll(0.75))
    end
    -- the fields this file adds beside the kernels' own, backfilled on any table that lacks them
    local n, f, a = record.nutrients, record.fluids, record.acute
    if n.lastAgeH == nil then n.lastAgeH = ageH end
    if n.lastDayIndex == nil then n.lastDayIndex = body.dayIndex end
    if f.viewPct == nil then f.viewPct = 0 end
    if a.lastFedAgeH == nil then a.lastFedAgeH = ageH end
    if a.alc7 == nil then a.alc7 = 0 end
    if a.alcDayG == nil then a.alcDayG = 0 end
    -- the fix wave's fields (rulings T17-2, T17-4) on a record made before them
    if a.gutAlc == nil then a.gutAlc = 0 end
    if a.gutCaf == nil then a.gutCaf = 0 end
    if a.boutH == nil then a.boutH = 0 end
    if a.gapH == nil then a.gapH = 0 end
    -- the Plan 5 fields (schema av 1 -> 2, Task 5) on a record made before them; the band baselines start at
    -- the accumulators' current values, so a backfilled record credits no exercise it did not see
    if a.exEma == nil then a.exEma = 0 end
    if a.lastVigAgeH == nil then a.lastVigAgeH = -1e9 end
    if a.boutVig == nil then a.boutVig = false end
    if a.coldH == nil then a.coldH = 0 end
    if a.retEma == nil then a.retEma = 0 end
    if a.iuSleep == nil then a.iuSleep = 0 end
    if a.lastB1 == nil then a.lastB1 = body.band1Day or 0 end
    if a.lastB2 == nil then a.lastB2 = body.band2Day or 0 end
    a.av = K.acute.AV
end

-- The minute's training band, 0/1/2 (Plan 5 Task 5): Metabolism's K.training.sample adds the minute to
-- body.band1Day (band >= 1) and body.band2Day (band 2) and stamps no per-minute band, so the band is read
-- off their growth since the last minute (record.acute.lastB1/lastB2). On a minute whose day close ran
-- (closed: Metabolism samples, then closes, zeroing the accumulators) the growth is the closed day's ring
-- slot 7 less the baseline, plus the new day's value; a multi-day close (days > 1) reads the new day alone.
local function minuteBand(a, body, days)
    local b1 = body.band1Day or 0
    local b2 = body.band2Day or 0
    local g1 = b1 - a.lastB1
    local g2 = b2 - a.lastB2
    if days > 0 then
        g1 = b1
        g2 = b2
        local slot = type(body.bandWeek) == "table" and body.bandWeek[7] or nil
        if days == 1 and type(slot) == "table" then
            g1 = g1 + K.max(0, (slot[1] or 0) - a.lastB1)
            g2 = g2 + K.max(0, (slot[2] or 0) - a.lastB2)
        end
    end
    a.lastB1 = b1
    a.lastB2 = b2
    if g2 > 0 then return 2 end
    if g1 > 0 then return 1 end
    return 0
end

-- The day close, when Metabolism's dayIndex has advanced since the last one seen here: the 7-day alcohol
-- mean takes the closed day's ingested ethanol, then the refeeding day and event (ruling 15, T9-3) read the
-- closed day's absorbed kcal per kg (Metabolism's body.inDayClosed stamp). body.alcDay is Metabolism's: its
-- partition close zeroes it, so it is not zeroed again here.
local function closeDay(record, body, w, ageH)
    local n = record.nutrients
    local a = record.acute
    local days = body.dayIndex - n.lastDayIndex
    if days > 1 then NUT.stats.skippedDays = NUT.stats.skippedDays + (days - 1) end
    local kcal = body.inDayClosed
    if not finite(kcal) then kcal = 0 end
    local kcalPerKg = kcal / w
    a.alc7 = a.alc7 + (a.alcDayG / w - a.alc7) / NUT.ALC_EMA_DAYS
    a.alcDayG = 0
    local mg = n.magnesium
    local mgDepleted = mg ~= nil and mg.g >= NUT.MG_DEPLETED_GRADE
    K.acute.refeedDay(a, kcalPerKg, w, ageH, false, mgDepleted, a.alc7 > NUT.ALC_HISTORY_GKG)
    K.acute.refeedEvent(a, kcalPerKg, roll(0.5))
    n.lastDayIndex = body.dayIndex
    NUT.stats.days = NUT.stats.days + 1
end

-- The interaction factors on the absorbed vector before the engine (Task 10's contract): calcium x iron on
-- the meal calcium caMeal (the stomach buffer's calcium before the minute's emptying, ruling T17-1; nil --
-- a handoff set without Kinetics -- falls back to the minute's absorbed calcium, the Plan 4 proxy), the
-- caffeine and alcohol urinary losses of this minute's released doses cafDose and alcDose (the gut lane,
-- ruling T17-2) off magnesium and calcium (floored at 0), and the vitamin A fold: the engine reads
-- absorbed[ORDER key] = absorbed.vitA, so the folded amount (preformed retinol plus the carotene the liver
-- gate passes) is written there; the ingested vitA the excess tests read is the preformed retinol alone.
-- Niacin's tryptophan credit (ruling T19-2, S0270): absorbed niacin gains the absorbed protein's tryptophan
-- (protein g x 1000 x trpShare mg) over trpPerNE mg per mg NE, read off the niacin record.
local function factors(absorbed, ingested, n, lm, caMeal, cafDose, alcDose)
    if absorbed ~= EMPTY then
        if caMeal == nil then caMeal = absorbed.calcium or 0 end
        absorbed.iron = (absorbed.iron or 0) * K.interact.calciumIron(caMeal)
        local cafMg, cafCa = K.interact.caffeineLossMg(cafDose, lm)
        local alcMg = K.interact.alcoholLossMg(alcDose)
        absorbed.magnesium = K.max(0, absorbed.magnesium - cafMg - alcMg)
        absorbed.calcium = K.max(0, (absorbed.calcium or 0) - cafCa)
        local vitA = n.vitA
        local rec = NR.data.records.REC.vitA
        local p = 1
        if vitA ~= nil then p = vitA.p end
        local off = nil
        if rec ~= nil and rec.two ~= nil then off = rec.two.caroteneOff end
        absorbed.vitA = (absorbed.retinol or 0) + K.interact.CAROTENE_RAE * K.interact.caroteneOn(p, off) * (absorbed.carotene or 0)
        local nia = NR.data.records.REC.niacin
        if nia ~= nil and nia.trpShare ~= nil and nia.trpPerNE ~= nil then
            absorbed.niacin = (absorbed.niacin or 0) + (absorbed.proteins or 0) * 1000 * nia.trpShare / nia.trpPerNE
        end
    end
    if ingested ~= EMPTY then
        ingested.vitA = ingested.retinol or 0
    end
end

local function step(username, player, record, pipe)
    -- the handoffs are read first off the pipeline's context (Kinetics wrote them this minute); the context
    -- is cleared at the start of each player's run, so no early return leaves them for a later minute
    local absorbed = EMPTY
    local caMeal = nil
    if pipe ~= nil then
        absorbed = pipe.absorbed or EMPTY
        caMeal = pipe.mealCa
    end
    local intake = NR.server.intake
    local ingested = EMPTY
    if intake ~= nil and intake.lastIngested ~= nil then
        ingested = intake.lastIngested[username] or EMPTY
        intake.lastIngested[username] = nil
    end
    local ageH = worldAge()
    if ageH == nil then
        NUT.stats.badAge = NUT.stats.badAge + 1
        return
    end
    local body = record.body
    if body == nil then
        NUT.stats.noBody = NUT.stats.noBody + 1      -- Metabolism makes it first; counted, never healed here
        return
    end
    ensure(record, body, ageH)
    heal(username, record, body, ageH)
    local n, f, a = record.nutrients, record.fluids, record.acute
    -- the gut lane's pending doses move onto the record (ruling T17-2); drained here, after the record
    -- exists, so a minute skipped above leaves them pending for the next one
    if intake ~= nil and intake.pendingAlc ~= nil then
        a.gutAlc = a.gutAlc + (intake.pendingAlc[username] or 0)
        intake.pendingAlc[username] = nil
        a.gutCaf = a.gutCaf + (intake.pendingCaf[username] or 0)
        intake.pendingCaf[username] = nil
    end
    local dtM = K.clamp((ageH - n.lastAgeH) * 60, 0, 60)    -- offline time is not integrated
    n.lastAgeH = ageH
    if dtM <= 0 then return end                             -- K.fluids.losses divides by dtM
    local dtH = dtM / 60
    local w = body.fm + body.lm
    local O = NR.server.options or EMPTY
    local closedDays = body.dayIndex - n.lastDayIndex       -- read before closeDay moves lastDayIndex
    if body.dayIndex > n.lastDayIndex then closeDay(record, body, w, ageH) end

    -- the gut lane's release this minute, plus any ethanol or caffeine a pre-fix buffer still empties
    local alcDose, cafDose = K.acute.absorbGut(a, dtH)
    alcDose = alcDose + (absorbed.ethanol or 0)
    cafDose = cafDose + (absorbed.caffeine or 0)

    -- the records
    factors(absorbed, ingested, n, body.lm, caMeal, cafDose, alcDose)
    local hSince = ageH - body.lastCloseAgeH
    local eeYest = K.energy.ree(body.lm)                    -- before the first close: the resting expenditure
    if finite(body.inDayClosed) then eeYest = body.inDayClosed - body.eb7[7] end
    local ee24 = K.max(K.body.blend24(body.eeDay, eeYest, hSince), K.energy.ree(body.lm))
    local alcGkg = body.alcDay / w
    NUT.kMul.thiamine = K.interact.thiamineAlcoholK(1, alcGkg)
    -- choline's female rate (ruling T19-3; S0378 the ratio, labelled on the record): x kFemale on a female body
    local cho = NR.data.records.REC.choline
    NUT.kMul.choline = (body.sex == 2 and cho ~= nil and cho.kFemale) or 1
    local ctx = NUT.ctx
    ctx.sex = body.sex
    ctx.w = w
    ctx.lm = body.lm
    ctx.eeMJ = ee24 * 4.184 / 1000                          -- kcal to MJ
    ctx.pDay = body.pPrevKg * w                             -- yesterday's protein g, as Plan 3's rmod reads it
    ctx.alcGkg = alcGkg
    ctx.dial = O.onsetSpeed or 1
    ctx.excessOn = O.excessEffectsOn ~= false
    ctx.two = K.interact.two
    ctx.kMul = NUT.kMul
    ctx.riboGrade = 1
    if n.riboflavin ~= nil then ctx.riboGrade = n.riboflavin.g end
    ctx.rawEggDay = false                                   -- no raw-egg flag in the data until Plan 6
    ctx.e24Zn = 0
    if n.zinc ~= nil then ctx.e24Zn = n.zinc.e24 end
    K.nutrients.minute(n, NR.data.records, absorbed, ingested, ctx, dtM)

    -- the fluids
    local met = body.met
    if not finite(met) then met = 1 end
    local coldMult = body.coldMult
    if not finite(coldMult) then coldMult = 1 end
    K.fluids.intake(f, absorbed)
    local fctx = NUT.fctx
    fctx.sex = body.sex
    fctx.met = met
    fctx.thermoFluids = num(obj(obj(player, "getBodyDamage"), "getThermoregulator"), "getFluidsMultiplier", 1)
    fctx.coldMult = coldMult
    fctx.ethanolAbsG = alcDose
    fctx.dehydPct = f.dehydPct
    K.fluids.losses(f, fctx, dtM)
    K.fluids.clearance(f, dtM)
    local stomach = record.stomach
    if f.autoDrop > 0 then
        -- ruling 9: the fast handler's bracketed THIRST drop, converted to litres, lands as a water drink
        if stomach == nil then
            stomach = K.stomach.seedFull(K.stomach.new())
            record.stomach = stomach
        end
        if NUT.waterVec == nil then NUT.waterVec = K.vector.new() end
        NUT.waterVec.water = NUT.LITRES_PER_THIRST * f.autoDrop * 1000
        K.stomach.ingest(stomach, NUT.waterVec)
        f.autoDrop = 0
    end
    f.dehydPct = K.fluids.dehydPct(f, w, 0)
    local pendingG = 0                                      -- K.stomach has no water accessor: the buffer's field is read
    if stomach ~= nil and stomach.buffer ~= nil and finite(stomach.buffer.water) then pendingG = stomach.buffer.water end
    f.viewPct = K.fluids.dehydPct(f, w, pendingG)           -- ruling T1-1
    f.c = K.fluids.conc(f, body.lm)
    f.naPlasma = K.fluids.naPlasma(f.c)
    f.thirstTarget = K.fluids.thirstTarget(f.viewPct, f.c, f.naPlasma, O.deficienciesCanKill ~= false)
    f.sweatActive = K.fluids.sweatActive(f)

    -- the acute states
    local okS, asleep = NR.call(player, "isAsleep")
    asleep = okS and asleep == true
    local hourOfDay = ageH - math.floor(ageH / 24) * 24
    if getGameTime ~= nil then
        local ok, gt = pcall(getGameTime)
        hourOfDay = num(ok and gt or nil, "getTimeOfDay", hourOfDay)
    end
    K.acute.caffeine(a, cafDose, w, dtH)                   -- the gut lane's dose (CAF_ABSORB applied there)
    K.acute.alcohol(a, alcDose, w, body.sex, dtH)
    local ethIng = ingested.ethanol or 0
    body.alcDay = body.alcDay + ethIng                      -- Plan 3's alcohol gate, finally written
    a.alcDayG = a.alcDayG + ethIng
    local cho24 = K.body.blend24(body.carbDay, body.carb7[7], hSince) / w
    K.acute.glycogen(a, met, coldMult, cho24, dtH)
    if (record.stomachFill or 0) > NUT.FED_FILL then a.lastFedAgeH = ageH end
    K.acute.glucose(a, met, absorbed.carbs or 0, a.bac, ageH - a.lastFedAgeH, dtH)
    -- the Plan 5 memories (Task 5): the band before the sleep step, which latches boutVig off lastVigAgeH
    K.acute.exerciseMinute(a, minuteBand(a, body, K.max(0, closedDays)), ageH, dtH)
    K.acute.coldMinute(a, coldMult, dtH)
    K.acute.retinolMinute(a, ingested.retinol or 0, dtM / 1440)
    -- Plan 5: the fatigue multipliers record.effects stamped LAST minute (NR_Server_Effects runs after this
    -- step: a one-minute lag); absent, non-finite or non-positive reads nil (1 in the kernel, no division by 0)
    local mAcc, rRec = nil, nil
    local eff = record.effects
    if type(eff) == "table" then
        if finite(eff.mAcc) and eff.mAcc > 0 then mAcc = eff.mAcc end
        if finite(eff.rRec) and eff.rRec > 0 then rRec = eff.rRec end
    end
    K.acute.sleepMinute(a, asleep, hourOfDay, needFactor(player), ageH, dtH, NUT.sleepDisabled, mAcc, rRec)
    K.acute.iu(a, f.dehydPct, n.ironGrade)

    heal(username, record, body, ageH)
    NUT.stats.players = NUT.stats.players + 1

    -- Plan 5 ruling 22, made explicit (Plan 10 R2): the effects step runs next in the pipeline and reads this
    -- minute's epoch, fluids and acute stamps; its inputs are stamped on the context last, so the step runs
    -- only on a minute that reached here (as the hand call did), and a raise there never skips a stamp here
    if pipe ~= nil then
        pipe.body = body
        pipe.dtM = dtM
        pipe.ageH = ageH
    end
end

-- One player's minute: the pipeline's nutrients step (NR_Server_Minute.run, from P.work); pipe its context.
-- One pcall around the body: a failure is kept and logged on the slow clock, never raised into the
-- players walk.
function NUT.minute(username, player, record, pipe)
    if record == nil then return end
    NUT.stats.minutes = NUT.stats.minutes + 1
    local ok, err = pcall(step, username, player, record, pipe)
    if not ok then
        NUT.stats.errors = NUT.stats.errors + 1
        NUT.lastError = err
        NR.log.say(2, "nutrients: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

-- Wiring: registered as the pipeline's nutrients step at OnServerStarted; ORDER runs it after Kinetics and
-- Metabolism and before Effects, Strength and Weight.
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if NUT.wired then return end
        NUT.wired = true
        NUT.readSleepOptions()
        local MIN = NR.server.minute
        MIN.register("nutrients", NUT.minute)
    end)
end
