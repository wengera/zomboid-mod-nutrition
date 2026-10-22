-- NR_Server_Nutrients.lua -- the record engine, the fast pools and the acute states on the slow clock
-- (spec § 4.4): once per player per game minute, on the players' OnTick stagger and after the
-- stomach step (NR_Server_Kinetics) and the body step (NR_Server_Metabolism), it consumes the minute's
-- absorbed vector, steps the per-nutrient records (K.nutrients over NR.data.records with K.interact.two),
-- the water and electrolyte pools and the thirst view (K.fluids), and the acute states (K.acute), and
-- stamps every result on three record sub-tables: record.nutrients, record.fluids and record.acute.
--
-- Order (plan ruling 17): the pipeline's declared ORDER (NR_Server_Minute, Plan 10 R2) runs Kinetics,
-- Metabolism, Nutrients (this file), Effects, Strength, Weight; each registers its step at OnServerStarted
-- (Training has no minute step). NR_Server_Options loads before NR_Server_Players and so polls on
-- EveryOneMinute directly, ahead of the drain. Metabolism reads the absorbed handoff's four macros first;
-- this file then consumes it (the context lives one player's minute). Metabolism's rmod
-- reads the PREVIOUS minute's scalars stamped here (a one-minute lag, stated in the limitations).
--
-- Plan 4 writes no stat, moodle or health: every value here is mod state for Plan 5 and the mirror.
-- Every Java read goes through NR.call (index-first) with a default; every Java global is named only
-- inside a function behind a nil check, so the file loads with no engine
-- (testing/tests/kernel/test_nutrients_shape.py). The whole minute runs under one pcall per player and
-- never raises into the players walk. Every field written on the record is a number, a boolean, a
-- string or a table of numbers (#1495). Slow-clock code: no @fastpath region in this file.
--
-- The x151r fix wave: the calcium x iron factor reads the meal calcium in the stomach before the minute's
-- emptying (NR_Server_Kinetics' mealCa handoff on the context, #2981), and caffeine and ethanol reach
-- the acute states through the gut lane (#2982/#2983): the intake landing's pending sums are
-- drained into record.acute.gutAlc / gutCaf, K.acute.absorbGut releases them, and the released doses feed
-- the alcohol and caffeine steps, the urinary losses and the alcohol diuresis. The stomach never holds a
-- dose of either (IN.land diverts both), so the gut lane's release is the whole dose these steps read;
-- the day's ingested ethanol (the alcohol gate) is the ingested vector's.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.nutrients = {
    stats = { players = 0, minutes = 0, healed = 0, errors = 0, badAge = 0, noBody = 0, days = 0,
              skippedDays = 0, effectsErrors = 0 },
    lastError = nil,
    lastHealed = nil,
    wired = false,
    limitations = {
        "the one-minute lag: Metabolism's rmod reads the previous minute's nutrient, fluid and acute stamps",
        "metabolic water is omitted: the basal loss is the net figure, 2000 g/day at the no-trait body's lean mass and 32 g/day a kg of lean mass either side (S2218, S2220; the anchor and the total are game choices inside S1688's net range), sex-neutral; High Thirst (x1.5), Low Thirst (x0.5) and StatsDecrease scale it and never the sweat",
        "retained sodium carries its water isotonically (S1683): sodium stored without water at high sustained intakes (S1673, S1677) is not modelled, and a sodium deficit contracts the set point isotonically only to 8 % of ECF (0.20 L/kg, S1714; S1717, S1722's volume threshold applied to ECF, a game choice), then ever less to a bound of 20 % (S1729, McCance's plateau by eye); past the onset the same ramp relaxes the hypotonic thirst cap (S1729, S1731, S1724; riding the ramp is a game choice, the human cut-off open, S1695, S1736), so the lost water is drunk back and the pool dilutes, and only water not yet replaced reads as dehydration",
        "sweat sodium adapts to a sodium deficit, not to heat exposure alone: the drawn concentration falls linearly with the deficit to 0.325 of itself at 331 mmol (S1747, S1751, S1752, S1750; the line and its zero anchor are game choices, the dose-response open, S1770) and never under 10 mmol/L (S0518, S1758); a replete, acclimatising worker keeps the drawn concentration here although S1755, S1739 and S1743 fall without a known deficit, no gland lag is stored (S1748, S1773), and repletion restores it along the same line (S1771 open)",
        "respiratory water loss is 0 beyond basal (S1052 open)",
        "caffeine diuresis is 0 for a habitual drinker (S0528/S0529)",
        "liver glycogen is not modelled (S0110 open)",
        "the sleep state freezes at rested while the server's SleepAllowed and SleepNeeded are not both true (x151s, #2947): the engine resets a FATIGUE write made outside its own stat update; the two options are polled every server minute, so an admin's change takes effect at the next minute",
        "with sleep off there is no daily rhythm (a game choice): the hunger circadian factor is 1, the fatigue circadian term 0 and there is no carry morning halving; with sleep on the rhythm reads the character's body clock, which advances only by online time and wakes at 07:00 at the close of a sleep bout of at least 4 booked hours (a game choice: in real bodies light, not sleep, sets the phase), so naps (bouts separated by 10 game minutes or more) and an accelerated-sleep mod's few-minute nights never reset it; it starts at the world hour on a new record and when sleep turns on, and the off-to-on seed reads the server minute's hour, so a switch during a stall's carried sub-steps lands up to the carry ahead; a stall's sub-steps (a step over 60 game minutes, the carried ones in later minutes included) all read the sleep state seen when the stall was detected, so a waking inside the stall, or in the minutes its carry merges in, is booked at that state",
        "the thirst view reads the water pool plus the stomach's pending water, in its volume and its osmotic term (satiation precedes absorption, S1698, S1699; the weight 1.0 is a game choice); the solid buffer's water counts as the liquid lane's does (gastrointestinal receptors, S1704; a game choice), and pending water satiates for as long as it is pending, with no rebound (how long pre-absorptive satiation lasts is open, S1735; a game choice); the performance dehydration, plasma sodium and its grade are the pool alone",
        "auto-drink litres land in the stomach one minute after the writer folds the sip into the THIRST target",
        "the first Nutrients minute on a new record integrates no time (its absorbed vector is dropped; Metabolism already credited it) and also drops that minute's absorbed water",
        "before the first day close the protein-scaled requirements read P_LOW x w (K.body.new's neutral pPrevKg)",
        "offline time is never integrated: the resume at a return moves every world-age clock past the absence (the sleep window, the fed, vigorous and 90-day mass clocks, the monotony stamps, the nicotine anchor and the record day), and a return closes no refeeding day; the game's own clocks on the character are not the mod's: food it carries keeps ageing over the absence (vanilla's spoilage), and vanilla's Fitness regularity counts calendar days",
        "the potassium-depletion refeeding criterion reads false (no row grades potassium)",
        "this step writes no stat, moodle or health; the writer owns the stat writes (INTOXICATION and FATIGUE included) and the effects layer the health writes",
        "caffeine and ethanol absorb on a 0.5 h gut lane that a full stomach does not slow (S1102 open): a drink with a meal peaks as early as one on an empty stomach",
        "the interaction factors read the stomach buffer's phytate, vitC and calcium before each minute's emptying: two meals in the buffer act as one meal, and the inhibition eases as the buffer empties",
        "a sleep bout tolerates awake gaps under 10 game minutes (S1112 open): a real wake of under 10 minutes inside a night counts as sleep for hours awake",
        "vitamin D has no cutaneous term (no outdoor-daylight read, S1064 open): every character trends to its dietary steady state (clinical in ~153 d at zero intake; ~5 d at OnsetSpeed 30)",
        "the fat factor reads the stomach buffer's lipids before each minute's emptying: it eases as the meal empties, so a 30 g-fat meal absorbs 90 % of its retinol and vitK and three 10 g-fat meals a day 81 %",
        "the minute's training band is read off the growth of Metabolism's day accumulators band1Day/band2Day (no per-minute band is stamped); a minute whose day close skipped days reads the new day's growth alone",
        "a field the step's own arithmetic leaves non-finite and no later step reads in the same minute stays so until the next minute's pre-step heal",
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
-- The post-step guard: the fluids, acute and state fields something reads before the
-- next minute's pre-step heal -- Effects, Strength, the writer (after weight), the bus step (first in ORDER) and
-- the store step -- copied after the pre-step heal and re-stamped from the copy when the step leaves them non-finite
-- (testing/tests/kernel/test_heal_once.py CROSS names each read). viewPct and c are read inside this step only.
NUT.GUARD_FLUIDS = { "dehydPct", "thirstTarget", "naPlasma" }
NUT.GUARD_ACUTE = { "bac", "caf", "cafTol", "debtH", "S", "circ", "bodyHour", "iu", "hang", "coldH", "lastVigAgeH", "wd", "alcPeak",
                    "bg", "iuSleep", "exEma", "bmi", "starvedDays", "retEma", "awakeH", "g", "refeedRisk" }
NUT.GUARD_STATE = { "epoch" }
NUT.snapF = {}
NUT.snapA = {}
NUT.snapN = {}
NUT.guarded = 0

-- The handoff a minute with no absorbed or ingested vector reads: one file-scope table, never written.
local EMPTY = {}

-- The stomach fill above which the stomach counts as fed (the glucose term's empty-stomach clock).
NUT.FED_FILL = 0.05 -- game choice: a stomach below 5 % of full is empty for the alcohol-fasting glucose term; the food fill, the solid lane's mass over 730 g (K.stomach.recordFoodFill, ruling T6c-1: drunk water is not food), so about 37 g of food (ruling 11c-14)
-- The alcohol-history refeeding criterion: the 7-day mean daily alcohol above this, g per kg.
NUT.ALC_HISTORY_GKG = 0.5 -- game choice: S0115 names alcohol misuse with no dose; no row
-- The 7-day mean's daily weight.
NUT.ALC_EMA_DAYS = 7 -- game choice: the 7-day window
-- The NEEDS_MORE_SLEEP and NEEDS_LESS_SLEEP factors on the sleep need: the engine's own awake-fatigue
-- trait multipliers (#2271, updateStats_Awake 1.3 / 0.7); their use as a need factor a game choice on S0740.
NUT.NEED_MORE = K.dials.get("nut.NEED_MORE")
NUT.NEED_LESS = K.dials.get("nut.NEED_LESS")
-- The magnesium grade at which the refeeding risk reads magnesium-depleted (S0115's low-magnesium criterion).
NUT.MG_DEPLETED_GRADE = 3 -- game choice: the depleted rung of the magnesium record
-- The litres one unit of THIRST drop stands for: Water's ThirstChange -50 per litre = 0.5 THIRST per litre.
NUT.LITRES_PER_THIRST = 2 -- ruling 9 (Water ThirstChange -50 per litre, x151w #2932/#2939)

local finite = NR.finite

-- A number read off obj:name(...), or dflt when the member is absent or the answer is not finite. The world age and
-- the minute's other engine reads are NR.read's (an unread age skips the minute, counted: the acute kernel's
-- sleep-window loop needs a finite age).
local num = NR.num

-- A uniform roll in [0, 1) (NR.roll).
local roll = NR.roll

-- The sleep-need factor off the character's trait set (the CharacterTrait registry objects); ctx is the pipeline's.
-- Rule 6: each flag is the minute's shared read (NR.read.trait), which the writer's sleep traits reuse.
local function needFactor(player, ctx)
    local T = CharacterTrait
    if T == nil then return 1 end
    if NR.read.trait(ctx, player, T.NEEDS_MORE_SLEEP) then return NUT.NEED_MORE end
    if NR.read.trait(ctx, player, T.NEEDS_LESS_SLEEP) then return NUT.NEED_LESS end
    return 1
end

-- The basal water loss's scale (K.fluids.basalG's traitScale): High Thirst x1.5 or Low Thirst x0.5
-- (K.fluids.thirstTrait; game choices, spec section 3.4) times the sandbox's StatsDecrease multiplier, which scales
-- vanilla's thirst rate the same way (#2765); sweat is never scaled. Rule 6: each flag is the minute's shared read
-- (NR.read.trait), and the multiplier is Kinetics' read on ctx.sd, else read here and handed on for the writer.
local function basalScale(player, ctx)
    local high, low = false, false
    local T = CharacterTrait
    if T ~= nil then
        high = NR.read.trait(ctx, player, T.HIGH_THIRST)
        low = not high and NR.read.trait(ctx, player, T.LOW_THIRST)
    end
    local sd = ctx ~= nil and ctx.sd or nil
    if sd == nil then
        sd = num(NR.sandbox(), "getStatsDecreaseMultiplier", 1)
        if ctx ~= nil then ctx.sd = sd end
    end
    return K.fluids.thirstTrait(high, low) * sd
end

-- The heal (NR.healTable): every numeric field of the three sub-tables finite, else its fresh value. A field with no
-- fresh value takes its named default; one with neither (iron S and H, calcium bone, laid lazily by K.interact.two)
-- is cleared so the kernel re-initialises it. healBad collects the healed names of one pass; a nutrient sub-table's
-- names carry its key (nutrients.<key>.<field>).
NUT.AGE_NUT = { lastAgeH = true }
NUT.AGE_ACUTE = { winStartH = true, mass90ageH = true, lastFedAgeH = true }

local function heal(username, record, body, ageH)
    local healBad = nil
    if NUT.refKey == nil then
        NUT.refKey = K.nutrients.newKey()
        NUT.refFluids = K.fluids.new(nil, nil, nil)
        NUT.refFluids.viewPct = 0
        NUT.refAcute = K.acute.new(0)
        NUT.refAcute.alc7 = 0
        NUT.refAcute.alcDayG = 0
        NUT.refAcute.lastB1 = 0
        NUT.refAcute.lastB2 = 0
        NUT.refNut = { epoch = 0, ironGrade = 1, lastDayIndex = 0 }
    end
    local n = record.nutrients
    NUT.refNut.lastDayIndex = body.dayIndex
    healBad = NR.healTable(n, NUT.refNut, healBad, "nutrients.", nil, ageH, NUT.AGE_NUT)
    local order = NR.data.records.ORDER
    -- ORDER is a Lua table the record file built, so # is a Lua length, never a Java list (#0940).
    for i = 1, #order do
        local s = n[order[i]]
        if type(s) == "table" then healBad = NR.healTable(s, NUT.refKey, healBad, "nutrients.", order[i]) end
    end
    healBad = NR.healTable(record.fluids, NUT.refFluids, healBad, "fluids.")
    healBad = NR.healTable(record.acute, NUT.refAcute, healBad, "acute.", nil, ageH, NUT.AGE_ACUTE)
    if healBad ~= nil then
        NUT.stats.healed = NUT.stats.healed + 1
        NUT.lastHealed = healBad
        NR.log.say(2, "nutrients: non-finite " .. healBad .. " for " .. tostring(username) .. "; stamped fresh")
    end
end

-- Ensure the three sub-tables. The sweat multiplier and sweat sodium are drawn once per character: the multiplier uniform over
-- its range, the sodium as 10 + 80 r^2 (mean 36.7; fallback with no ZombRandFloat: the multiplier 1.0 and 37 mmol/L); the
-- slow-metaboliser trait once (fallback roll 0.75: not slow).
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
    -- the fields this file adds beside the kernels' own (no constructor lays them), laid on any table that lacks them
    local n, f, a = record.nutrients, record.fluids, record.acute
    if n.lastAgeH == nil then n.lastAgeH = ageH end
    if n.lastDayIndex == nil then n.lastDayIndex = body.dayIndex end   -- the record's day count (online days, ruling 13-5)
    if f.viewPct == nil then f.viewPct = 0 end
    if a.lastFedAgeH == nil then a.lastFedAgeH = ageH end
    if a.alc7 == nil then a.alc7 = 0 end
    if a.alcDayG == nil then a.alcDayG = 0 end
    -- the band baselines start at the accumulators' current values, so a new record credits no exercise it did
    -- not see
    if a.lastB1 == nil then a.lastB1 = body.band1Day or 0 end
    if a.lastB2 == nil then a.lastB2 = body.band2Day or 0 end
end

-- The minute's training band, 0/1/2: Metabolism's K.training.sample adds the minute to
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
        local slot = type(body.bandWeek) == "table" and body.bandWeek[K.body.WEEK_N] or nil
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
-- mean takes the closed day's ingested ethanol, then the refeeding day and event read the
-- closed day's absorbed kcal per kg (Metabolism's body.inDayClosed stamp). body.alcDay is Metabolism's: its
-- partition close zeroes it, so it is not zeroed again here.
local function closeDay(record, body, w, ageH)
    local n = record.nutrients
    local a = record.acute
    local days = body.dayIndex - n.lastDayIndex
    if days > 1 then NUT.stats.skippedDays = NUT.stats.skippedDays + (days - 1) end   -- 0 or 1 since ruling 13-5 (one close a minute, none on a return); over 1 only after a heal re-stamps dayIndex
    local kcal = body.inDayClosed
    if not finite(kcal) then kcal = 0 end
    local kcalPerKg = kcal / w
    a.alc7 = a.alc7 + (a.alcDayG / w - a.alc7) / NUT.ALC_EMA_DAYS
    a.alcDayG = 0
    local mg = n.magnesium
    local mgDepleted = mg ~= nil and mg.g >= NUT.MG_DEPLETED_GRADE
    local partial = finite(body.bornAge) and body.dayIndex - 1 <= math.floor(body.bornAge / 24)   -- the character's first, partial day: the close of its birth record day
    K.acute.refeedDay(a, kcalPerKg, w, ageH, false, mgDepleted, a.alc7 > NUT.ALC_HISTORY_GKG, partial)
    K.acute.refeedEvent(a, kcalPerKg, roll(0.5))
    n.lastDayIndex = body.dayIndex
    NUT.stats.days = NUT.stats.days + 1
end

-- The interaction factors on the absorbed vector before the engine (Task 10's contract): calcium x iron on
-- the meal calcium caMeal (the stomach buffer's calcium before the minute's emptying; nil --
-- a handoff set without Kinetics -- falls back to the minute's absorbed calcium, the Plan 4 proxy), the
-- caffeine and alcohol urinary losses of this minute's released doses cafDose and alcDose (the gut lane,
-- ruling T17-2) off magnesium and calcium (floored at 0), and the vitamin A fold: the engine reads
-- absorbed[ORDER key] = absorbed.vitA, so the folded amount (preformed retinol plus the carotene the liver
-- gate passes) is written there; the ingested vitA the excess tests read is the preformed retinol alone.
-- Niacin's tryptophan credit: absorbed niacin gains the absorbed protein's tryptophan
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

local function step(username, player, record, ctx)
    -- the handoffs are read first off the pipeline's context (Kinetics wrote them this minute); the context
    -- is cleared at the start of each player's run, so no early return leaves them for a later minute
    local absorbed = EMPTY
    local caMeal = nil
    if ctx ~= nil then
        absorbed = ctx.absorbed or EMPTY
        caMeal = ctx.mealCa
    end
    local intake = NR.server.intake
    local ageH = NR.read.ageH(ctx)
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
    K.heal.snap(f, NUT.GUARD_FLUIDS, NUT.snapF)
    K.heal.snap(a, NUT.GUARD_ACUTE, NUT.snapA)
    K.heal.snap(n, NUT.GUARD_STATE, NUT.snapN)
    -- the gut lane's pending doses move onto the record; drained here, after the record
    -- exists, so a minute skipped above leaves them pending for the next one
    if intake ~= nil and intake.pendingAlc ~= nil then
        a.gutAlc = a.gutAlc + (intake.pendingAlc[username] or 0)
        intake.pendingAlc[username] = nil
        a.gutCaf = a.gutCaf + (intake.pendingCaf[username] or 0)
        intake.pendingCaf[username] = nil
    end
    local dtM = K.max((ageH - n.lastAgeH) * 60, 0)          -- the pipeline's step (offline time never reaches it: the resume)
    n.lastAgeH = ageH
    -- the body clock (Plan 16 Task 4), ahead of the no-time return so a new record's first minute seeds it: with the
    -- options poll's sleep on it advances by this step's online hours, or seeds at the server minute's world hour
    local sleepOn = NR.sleepOn()
    K.circadian.step(a, sleepOn, NR.read.hour(ctx, ageH), dtM / 60)
    if dtM <= 0 then return end                             -- K.fluids.losses divides by dtM
    -- the minute's ingested sum, taken only by a minute that integrates: a minute skipped above leaves it for the
    -- next one, as it leaves the pending doses
    local ingested = EMPTY
    if intake ~= nil and intake.lastIngested ~= nil then
        ingested = intake.lastIngested[username] or EMPTY
        intake.lastIngested[username] = nil
    end
    local dtH = dtM / 60
    local w = body.fm + body.lm + body.lx
    local O = NR.server.options or EMPTY
    local closedDays = body.dayIndex - n.lastDayIndex       -- read before closeDay moves lastDayIndex; 0 or 1 (ruling 13-5)
    if body.dayIndex > n.lastDayIndex then closeDay(record, body, w, ageH) end

    -- the gut lane's release this minute: IN.land diverts every eaten ethanol and caffeine there
    local alcDose, cafDose = K.acute.absorbGut(a, dtH)

    -- the records
    factors(absorbed, ingested, n, body.lm, caMeal, cafDose, alcDose)
    -- the trailing-24 h expenditure (the window Metabolism moved this minute), floored at a resting day
    local ee24 = K.max(K.body.trail24(body.trail, "ee"), K.energy.ree(body.lm))
    local alcGkg = body.alcDay / w
    NUT.kMul.thiamine = K.interact.thiamineAlcoholK(1, alcGkg)
    -- choline's female rate (S0378 the ratio, labelled on the record): x kFemale on a female body
    local cho = NR.data.records.REC.choline
    local sex = K.body.effSex(body.sex, O.sexSpecific)          -- the effective sex, read once per minute (NR.SexSpecific)
    NUT.kMul.choline = (sex == 2 and cho ~= nil and cho.kFemale) or 1
    local kctx = NUT.ctx
    kctx.sex = sex
    kctx.w = w
    kctx.lm = body.lm
    kctx.eeMJ = ee24 * 4.184 / 1000                         -- kcal to MJ
    kctx.pDay = body.pPrevKg * w                            -- yesterday's protein g, as Plan 3's rmod reads it
    kctx.alcGkg = alcGkg
    kctx.dial = O.onsetSpeed or 1
    kctx.excessOn = O.excessEffectsOn ~= false
    kctx.two = K.interact.two
    kctx.kMul = NUT.kMul
    kctx.riboGrade = 1
    if n.riboflavin ~= nil then kctx.riboGrade = n.riboflavin.g end
    kctx.e24Zn = 0
    if n.zinc ~= nil then kctx.e24Zn = n.zinc.e24 end
    K.nutrients.minute(n, NR.data.records, absorbed, ingested, kctx, dtM)

    -- the fluids
    local met = body.met
    if not finite(met) then met = 1 end
    local coldMult = body.coldMult
    if not finite(coldMult) then coldMult = 1 end
    K.fluids.intake(f, absorbed)
    local fctx = NUT.fctx
    fctx.lm = body.lm
    fctx.basalScale = basalScale(player, ctx)
    fctx.met = met
    fctx.thermoFluids = num(NR.read.thermo(ctx, player), "getFluidsMultiplier", 1)
    fctx.coldMult = coldMult
    fctx.ethanolAbsG = alcDose
    fctx.dehydPct = f.dehydPct
    K.fluids.losses(f, fctx, dtM)
    K.fluids.clearance(f, dtM, w)
    local stomach = record.stomach
    if f.autoDrop > 0 then
        -- the writer's sip (THIRST's fall below its last write), converted to litres, lands as a drink: the liquid lane
        if stomach == nil then
            stomach = K.stomach.new()
            record.stomach = stomach
        end
        if NUT.waterVec == nil then NUT.waterVec = K.vector.new() end
        NUT.waterVec.water = NUT.LITRES_PER_THIRST * f.autoDrop * 1000
        K.stomach.ingestLiquid(stomach, NUT.waterVec)
        f.autoDrop = 0
    end
    f.dehydPct = K.fluids.dehydPct(f, w, 0)
    local pendingG = 0                                      -- both lanes' still-unabsorbed water (ruling T1-1)
    if stomach ~= nil and stomach.buffer ~= nil then
        local g = K.stomach.water(stomach)
        if finite(g) then pendingG = g end
    end
    f.viewPct = K.fluids.dehydPct(f, w, pendingG)           -- ruling T1-1
    f.c = K.fluids.conc(f, body.lm)
    f.naPlasma = K.fluids.naPlasma(f.c)
    -- the view's osmotic term counts the swallowed water too: AVP is back to its
    -- replete level 9 min after a drink (S1698) and thirst falls within 20 min at an unchanged Posm (S1699); the weight
    -- 1.0 on the pending water is a game choice resting on those rows. pendingG holds the solid buffer's water as well
    -- as the liquid lane's (S1704's gastrointestinal receptors; a game choice), and it satiates for as long as it is
    -- pending (the rebound time is open, S1735; a game choice). The hypotonic cap reads the pool's plasma sodium and is
    -- relaxed by the volume-defence weight past the onset (K.fluids.defence).
    local cView = K.fluids.conc(f, body.lm, pendingG)
    local defence = K.fluids.defence(f, w)
    f.thirstTarget = K.fluids.thirstTarget(f.viewPct, cView, f.naPlasma, defence)
    f.sweatActive = K.fluids.sweatActive(f)

    -- the acute states
    local asleep = NR.read.asleep(ctx, player)
    K.acute.caffeine(a, cafDose, w, dtH)                   -- the gut lane's dose (CAF_ABSORB applied there)
    K.acute.alcohol(a, alcDose, w, sex, dtH)
    local ethIng = ingested.ethanol or 0
    body.alcDay = body.alcDay + ethIng                      -- Plan 3's alcohol gate, finally written
    a.alcDayG = a.alcDayG + ethIng
    local cho24 = K.body.trail24(body.trail, "carb") / w    -- the trailing-24 h carbohydrate g/kg
    K.acute.glycogen(a, met, coldMult, cho24, dtH)
    if K.stomach.recordFoodFill(record) > NUT.FED_FILL then a.lastFedAgeH = ageH end
    K.acute.glucose(a, met, absorbed.carbs or 0, a.bac, ageH - a.lastFedAgeH, dtH)
    -- the Plan 5 memories: the band before the sleep step, which latches boutVig off lastVigAgeH
    K.acute.exerciseMinute(a, minuteBand(a, body, K.max(0, closedDays)), ageH, dtH)
    K.acute.coldMinute(a, coldMult, dtH)
    K.acute.retinolMinute(a, ingested.retinol or 0, dtM / 1440)
    -- The fatigue multipliers record.effects stamped LAST minute (NR_Server_Effects runs after this
    -- step: a one-minute lag); absent, non-finite or non-positive reads nil (1 in the kernel, no division by 0)
    local mAcc, rRec = nil, nil
    local eff = record.effects
    if type(eff) == "table" then
        if finite(eff.mAcc) and eff.mAcc > 0 then mAcc = eff.mAcc end
        if finite(eff.rRec) and eff.rRec > 0 then rRec = eff.rRec end
    end
    K.acute.sleepMinute(a, asleep, K.circadian.hour(record, sleepOn), needFactor(player, ctx), ageH, dtH, not sleepOn,
        mAcc, rRec)                                         -- the body clock's hour, nil with sleep off (circ 0)
    K.acute.iu(a, f.dehydPct, n.ironGrade)

    local ng = K.heal.guard(f, NUT.GUARD_FLUIDS, NUT.snapF) + K.heal.guard(a, NUT.GUARD_ACUTE, NUT.snapA)
        + K.heal.guard(n, NUT.GUARD_STATE, NUT.snapN)
    if ng > 0 then
        NUT.guarded = NUT.guarded + ng
        NR.log.say(2, "nutrients: " .. tostring(ng) .. " field(s) the step made non-finite re-stamped for " .. tostring(username))
    end
    NUT.stats.players = NUT.stats.players + 1

    -- Plan 5, made explicit (Plan 10 R2): the effects step runs next in the pipeline and reads this
    -- minute's epoch, fluids and acute stamps; its inputs are stamped on the context last, so the step runs
    -- only on a minute that reached here (as the hand call did), and a raise there never skips a stamp here
    if ctx ~= nil then
        ctx.body = body
        ctx.dtM = dtM
        ctx.ageH = ageH
    end
end

-- One player's minute: the pipeline's nutrients step (NR_Server_Minute.run, from P.work); ctx is its context.
-- One pcall around the body: a failure is kept and logged on the slow clock, never raised into the
-- players walk.
function NUT.minute(username, player, record, ctx)
    if record == nil then return end
    NUT.stats.minutes = NUT.stats.minutes + 1
    local ok, err = pcall(step, username, player, record, ctx)
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
        local MIN = NR.server.minute
        MIN.register("nutrients", NUT.minute)
    end)
end
