-- NR_Server_Writer.lua -- the once-a-minute stat writer (the hybrid). At the
-- server's OnGameBoot (one instruction before ZomboidGlobals.Load copies the Lua table, #3364) it reads NR.Mode,
-- saves the seven hunger, thirst and fatigue rise rates (#3362) and, in Mode 1, sets each to 0, never nil (#3366);
-- a client never reads the mode at its OnGameBoot (#3381) and never zeroes. Once a player-minute, as the pipeline's
-- step after weight and before store (after the minute's eats and the effects build, #3383), it writes HUNGER,
-- THIRST and FATIGUE and the floors, PANIC, TEMPERATURE and INTOXICATION through K.hybrid.write, stepping by elapsed
-- world age (#3371) and folding each auto-drink sip into the THIRST target (#3382). The HUNGER target is
-- hungerTarget(sated(F, mealRead(M)), energyState) x circadian(hour) x acuteFactor(S) x sleepFactor(debtH) x nicotineFactor (W.nicotine),
-- the model's h_model (kept on record.satiety.hModel for the study oracles), written through the calibrated curve
-- (K.hungerCurve.write, Plan 15 Task 6) and capped at 0.69 below starvation (K.hybrid.caps; NR_Kernel_Satiety.lua):
-- the stomach's fullness F (W.satietyF), the meal pool M (fed at the eat, cleared by Kinetics, seeded and read here), the acute suppression S
-- of vigorous work (stepped here) and the acute record's sleep debt debtH (W.satietyFactor). It registers no stat hook.
-- Option B (Plan 15 Task 5, W.severe): the caps lift at starvation and dehydration (K.hybrid.caps), and while the written
-- HUNGER or THIRST stands at level 4 the writer holds vanilla's severe-moodle constant at 0 and re-applies its other terms.
-- Every Java read goes through NR.num / NR.obj / NR.flag; every Java global is named inside a function behind a
-- nil check, so the file loads with no engine. Slow-clock code: no @fastpath region.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.writer = {
    h = {}, inp = {}, saved = nil, zeroed = false, mode = 1, wired = false,
    stats = { writes = 0, failures = 0, sips = 0, skipped = 0, seeded = 0, guarded = 0, nms = false, dry = 0, seedPlates = 0, seedShort = 0 },
    limitations = {
        "the mode (NR.Mode) is read once at the server's OnGameBoot; a change takes effect at the next restart (no mod route re-runs ZomboidGlobals.Load, #3365)",
        "with the rates zeroed, a writer outage stops hunger, thirst and fatigue rather than falling back to vanilla",
        "other mods reading ZomboidGlobals' hunger, thirst and fatigue rise rates read 0; NutritionRevamp.vanillaRate(key) answers the values saved before zeroing",
        "HUNGER, THIRST and FATIGUE are written once a game minute; an eat or a drink shows at once and the next write overwrites it with the satiety target, hungerTarget(sated(F, mealRead(M)), energyState) x the circadian factor x the acute exercise factor x the sleep-debt factor x the nicotine factor (the model's h_model), written through the calibrated curve (K.hungerCurve: a satisfying meal reads about 0 and Peckish and Hungry return on vanilla's cadence; unfed, the morning dip is taken out and HUNGER never falls; at the minute the meal pool empties in the morning, HUNGER steps up by the circadian dip (under 0.01); a level steps down only 0.02 under its threshold) and capped at 0.69 below starvation (K.hybrid.caps): F is the stomach's fullness mass (its satiety mass plus the protein term) over its 730 g comfortable maximum, counted on to the 1100 g hard capacity, drunk liquid counting at 0.279 of its mass, and M the meal pool, the weighted kcal eaten, fed in full at the eat and cleared on game time asleep or awake by the kinetics step while the writer seeds and reads it, so h_model never reaches 0 after a meal, and a fresh record's first minute writes the vanilla HUNGER it finds (read back through the curve's inverse); a vanilla HUNGER under what the meal pool alone can write on an empty stomach (the curve of hungerTarget(0.786, energy state) times the minute's factors, the seed's cap MEAL_SEED_MAX) lands a real meal before that minute, the curve fit's plate of the guide's foods sized to the least kcal whose first write is within the dead zone of it, at most one 667 kcal plate, its kcal and nutrients counted like any meal (W.seedPlate); protein fills the satiety fullness while it is in the stomach (a fitted game choice); an eat another mod makes through a direct Eat call reaches the stomach and M through the reconcile path a minute late and as its macros only (no water or fibre mass), and a drink another mod makes through a direct DrinkFluid call outside the intake's wraps is not seen; an eat in a fresh record's first minute, before the writer has seeded M, is not fed into M (it shows only through the HUNGER the seed reads); the exercise share of the energy deficit enters hunger through a lag of weeks, so a regular exerciser who eats to balance reads lower hunger for weeks; heavy work the model does not class as vigorous (neither the swing state nor the heavy-work band) overshoots the hunger rise of a heavy labour deficit (S1325); past 730 g in the stomach the mod's own Overfull moodle rises in four levels to 1100 g, and at its level 4 the food-timer bridge holds vanilla's FOOD_EATEN timer at its level 3, so vanilla's own refusal greys the eat menu and the double-click eat (a drink with no food value is not refused) (W.foodTimer), and the server refuses an eat queued past the menu at Overfull 4 (NR_Server_IntakeGuard; a drink from a fluid container and a direct Eat call another mod makes are not refused); a drink lands whole in the minute it is drunk, and drunk water leaves at a half-time of 13 min plus 0.12 min per kcal the drink itself carried, whatever food sits beside it (Plan 15 Task 14b), so a large drink right after a meal can hold level 4 for a few minutes; fibre sates only through its mass, and carbohydrate, sugar and starch take one weight per kcal (the evidence is mixed or absent), and fat and protein take fitted weights per kcal (0.879 and 2.50 times carbohydrate's, game choices of the fit); a vanilla HUNGER above the fullness ceiling, hungerTarget(0.5 F, energy state), that is (1 - 0.5 F) x es, times the minute's circadian, acute, sleep and nicotine factors, seeds an empty meal pool, so a fresh character's first written HUNGER drops to that ceiling's curve value; short sleep raises hunger by a factor capped at the pooled size, whether a step or graded is unsettled; the sleep factor steps at the acute record's 24 h window close, not at waking, so a short night that straddles the close reaches hunger in two steps a day apart; after a short night, nights of exactly the need repay nothing, so the rise holds until a longer night repays half its excess; right at a bout's end the acute term reads deeper than the pooled immediate-post effect; glycogen depletion no longer raises hunger, and a trailing-24 h deficit is bounded by the day's expenditure, so a sedentary fast plateaus at es about 1.19 to 1.29 by body size (1.2456 for the 70 kg man) from about 36 h, the balance term's cap is reached only by very heavy work, and higher energy states come from fat depletion; heat's lowering of intake is not modelled (cold reaches hunger through its expenditure); sugary drinks, ketosis, alcohol's aperitif effect and eating rate are neutral; an airy food sates by its weight plus 0.05 of its plate volume beyond its weight (a game choice; the physical fill and the Overfull moodle stay on mass); injury adds no expenditure; nicotine withdrawal raises hunger by a factor anchored on one small trial, fading over 26 weeks; a smoker who keeps smoking reads the rise between smokes, unfaded, and a character first seen in withdrawal reads none until a smoke; the deficit drive is fitted on the deficit studies alone, Karl 2021's well-fed arm held inside its band by the meal pool and the stomach's fill past 730 g rather than by the gut hormones the paper credits, so its post-meal troughs stay shallower than the study's; every Fitness set minute is vigorous resistance work for the acute term from the server's exercise flag, whatever the exercise and its billed MET (a light stretch and burpees alike)",
        "PANIC is written once a game minute and vanilla decays it between writes, up to 1.2556 under its floor at DayLength 1 (#3400); vanilla's panic rise between writes is unread",
        "TEMPERATURE is written once a game minute on the adjustment's far side (held within 0.04 C, #3393)",
        "an auto-drink sip in a minute when the intake also landed an eat or a drink is missed once and caught at the next minute",
        "asleep, FATIGUE saw-tooths by one minute of vanilla's recovery and the endurance rmod applies one minute late",
        "the sleep-onset latency terms (solAddH, solMul) are not applied: vanilla sets the sleep delay",
        "the Effects step reads the writer's engine reads of the previous minute",
        "in Overlay (Mode 2) vanilla owns HUNGER, THIRST and FATIGUE; the floors, PANIC, TEMPERATURE and INTOXICATION are still written; auto-drink is not captured; vanilla's own level-4 hunger and thirst drains (and their deaths) run, and the mod's starvation and dehydration drain states do not (its scurvy, beriberi, pellagra, sodium and iron drains still do, and the starvation clock and its effect phases still run; Plan 15 close, ruling M2); a fresh record still lands its seed plate (W.seedPlate), its kcal, nutrients and stomach mass counted, though no first HUNGER write is made",
        "another mod whose OnGameBoot handler runs after ours and sets ZomboidGlobals' hunger, thirst or fatigue rise keys (before ZomboidGlobals.Load, #3364) restores vanilla's drift between the writer's minute writes: HUNGER, THIRST and FATIGUE climb at its rates each tick and the next minute's write takes them back (the meal pool clears at its own half-life, never at those rates)",
        "a fresh record's 24 h window holds no meals: it reads like an even eater, its energy state rising from first sight at its expenditure rate (a new character or a respawn reaches energy level 1 after several unfed hours, inside the model's range for a skipped meal)",
        "while the written HUNGER or THIRST stands at level 4 vanilla's severe-moodle constant is 0 (option B, x451): its SICK, BLEEDING, HEAVY_LOAD and under-35 kg terms are re-applied once a minute, at vanilla's rates in expectation, on the moodle levels and conditions read at the minute (a level that came and went between two minutes is missed or carried a minute), as one ReduceGeneralHealth with no OnPlayerGetDamage event; the heavy-load term is its expected value, not vanilla's one-in-ten roll a tick, and never takes health under 75; the vanilla value is read once per player object, so after a Lua reload a player whose constant reads 0 at first sight keeps it until the next player object",
        "at days longer than 800 real minutes a Well Fed level shows for 1600 / (2 x dayMin) of each game minute; the refusal holds at every day length, showing FOOD_EATEN level 4 above 4800",
    },
}
local W = NR.server.writer
W.RATE_KEYS = { "HungerIncrease", "HungerIncreaseWhenWellFed", "HungerIncreaseWhileAsleep",
                "HungerIncreaseWhenExercise", "ThirstIncrease", "ThirstSleepingIncrease", "FatigueIncrease" } -- #3362
W.NMS_ID = "NutritionMakesSense" -- its 42/mod.info id= (Plan 11 Task 1)
-- the sleep bed factor (IsoPlayer.updateStats_Sleeping @109-@244, #2276)
W.BED = { badBed = 0.9, badBedPillow = 0.95, averageBedPillow = 1.05, goodBed = 1.1, goodBedPillow = 1.15,
          floor = 0.6, floorPillow = 0.75 }
W.c = K.hybrid.defaults()
W.input = K.hybrid.input()
W.output = K.hybrid.output()
W.SIP_EPS = 1e-6 -- game choice: far below a real drink (~0.1 of THIRST) and far above float noise (~1e-10 seen live, x281-x284); out.sip is in THIRST units (0..1)
-- The rates the server ran before the zeroing (nil when unread), else the live table's value.
function NR.vanillaRate(key)
    if W.saved ~= nil and W.saved[key] ~= nil then return W.saved[key] end
    if type(ZomboidGlobals) == "table" and type(ZomboidGlobals[key]) == "number" then return ZomboidGlobals[key] end
    return nil
end

function W.boot()
    if not NR.isServer() then return end
    local sv = SandboxVars and SandboxVars.NR or nil
    W.mode = 1
    if sv ~= nil and sv.Mode == 2 then W.mode = 2 end
    local zg = ZomboidGlobals
    if type(zg) ~= "table" then
        NR.log.say(1, "writer: ZomboidGlobals is absent at OnGameBoot; the rates stay vanilla's")
        return
    end
    W.saved = {}
    for i = 1, #W.RATE_KEYS do
        local k = W.RATE_KEYS[i]
        if type(zg[k]) == "number" then W.saved[k] = zg[k] end
    end
    if W.mode ~= 1 then
        NR.log.say(1, "writer: Mode 2 (Overlay): vanilla's hunger, thirst and fatigue rates stand")
        return
    end
    for i = 1, #W.RATE_KEYS do
        local k = W.RATE_KEYS[i]
        if W.saved[k] ~= nil then zg[k] = 0 end            -- 0, never nil (#3366)
    end
    W.zeroed = true
    NR.log.say(1, "writer: vanilla's hunger, thirst and fatigue rates saved and zeroed at boot (Mode 1); a mode change needs a restart")
end

local function get(h, stat)
    if stat == nil then return nil end
    return NR.num(h.stats, "get", nil, stat)
end

local function set(h, stat, v)
    if stat == nil or v == nil then return end
    local ok = pcall(NR.call, h.stats, "set", stat, v)
    if not ok then W.stats.failures = W.stats.failures + 1 end
end

-- The handles, once per player object (a respawn or a reconnect is a new object, #3360): nil when the player has
-- no stats object or the stat enum is absent, and the writer then writes nothing for that player.
function W.hoist(username, p)
    local stats = NR.obj(p, "getStats")
    if stats == nil or CharacterStat == nil then return nil end
    local h = { p = p, stats = stats, moodles = NR.obj(p, "getMoodles"), bd = NR.obj(p, "getBodyDamage"),
                traits = NR.obj(p, "getCharacterTraits"), ageH = nil, lastThirst = nil, lastEnd = nil,
                monoSeen = false, swipe = nil, fresh = true, username = username }  -- fresh: no step yet, W.satietyDtH reads the stamp
    h.thermo = NR.obj(h.bd, "getThermoregulator")
    if SwipeStatePlayer ~= nil and SwipeStatePlayer.instance ~= nil then
        local ok, sw = pcall(SwipeStatePlayer.instance)    -- the melee swing state: vigorous work for the acute term
        if ok then h.swipe = sw end
    end
    pcall(NR.call, h.bd, "setDrunkReductionValue", 0)       -- ruling 19 kept: the writer owns INTOXICATION
    return h
end

-- The engine reads Effects' accrual and recovery need (the input table's fields it reads, B3 and B4).
function W.readEngine(username, h, p, ctx)
    local i = W.inp[username]
    if i == nil then
        i = {}
        W.inp[username] = i
    end
    local T = CharacterTrait
    i.endurance = get(h, CharacterStat.ENDURANCE) or 1
    i.sitting = NR.flag(p, "isSitOnGround") or NR.flag(p, "isSittingOnFurniture")
    i.resting = NR.flag(p, "isResting")
    i.thermoFatigue = NR.num(h.thermo, "getFatigueMultiplier", 1)
    local sd = ctx ~= nil and ctx.sd or nil                -- Kinetics' read this player-minute (ruling T10-1)
    if sd == nil then
        sd = NR.num(NR.sandbox(), "getStatsDecreaseMultiplier", 1)
        if ctx ~= nil then ctx.sd = sd end
    end
    i.sd = sd
    -- Rule 6: the minute's shared trait flags (NR.read.trait), so the sleep traits Nutrients read cost no second get
    i.needsLess = T ~= nil and NR.read.trait(ctx, p, T.NEEDS_LESS_SLEEP, h.traits)
    i.needsMore = T ~= nil and NR.read.trait(ctx, p, T.NEEDS_MORE_SLEEP, h.traits)
    i.insomniac = T ~= nil and NR.read.trait(ctx, p, T.INSOMNIAC, h.traits)
    i.nightOwl = T ~= nil and NR.read.trait(ctx, p, T.NIGHT_OWL, h.traits)
    i.bedFactor = W.BED[NR.obj(p, "getBedType")] or 1
    return i
end

local function finiteOr(v, dflt)
    if NR.finite(v) then return v end
    return dflt
end

-- Vigorous work for the acute suppression term (spec § 5c): the melee or tool swing state is
-- resistance-type work; else Metabolism's stamp of the minute's billed MET at the Compendium's HeavyWork band or above
-- (6.0) is vigorous, and the kind follows the metabolism class Metabolism stamps on the minute's ctx: Fitness,
-- FitnessHeavy, ClimbRope (rope climbing, and tree chopping: classOf reads ForestryAxe's 8.0 as ClimbRope)
-- and ForestryAxe are resistance work; DiggingSpade and UsingTools bill under 6.0 and are listed inert (S1301, S1305).
-- A minute with a Fitness exercise in progress (ctx.exercising, the server's exercise flag) is resistance-vigorous
-- before any MET test (C-2): resistance work suppresses hunger regardless of load (S1508, S1509, S1301), and
-- a set now bills its exercise's own MET, under 6.0 for every vanilla type but burpees. The 6.0 bar stays for the rest.
-- The run flag never reaches the server (x141a), so a runner is not vigorous unless the metabolic rate classes it so.
-- Returns vigorous, kind (K.satiety.ACUTE_KIND's keys). ctx is nil or lacks the stamp: the class is unknown, aerobic.
W.RESISTANCE_CLASSES = { Fitness = true, FitnessHeavy = true, ClimbRope = true, ForestryAxe = true, DiggingSpade = true, UsingTools = true }
function W.vigorous(h, player, record, ctx)
    if h.swipe ~= nil and NR.flag(player, "isCurrentState", h.swipe) then return true, "resistance" end
    if ctx ~= nil and ctx.exercising == true and ctx.activityClass ~= "Sleeping" then return true, "resistance" end
    local met = record.body and record.body.met
    if NR.finite(met) and met >= K.energy.COMPENDIUM.HeavyWork then
        if ctx ~= nil and W.RESISTANCE_CLASSES[ctx.activityClass] == true then return true, "resistance" end
        return true, "aerobic"
    end
    return false, nil
end

-- The satiety step's length in game hours, S's step (M's clearance is Kinetics'). A minute on the same
-- player object reads the writer's own inp.dtS. The first minute of a new object (a reconnect or a respawn, #3360) or
-- of a restart, whose hoist holds no age (h.fresh), reads the step from the stamp record.satiety.t the writer leaves at
-- every step (game hours; stored, K.store.INPUTS), which the resume moved past any absence (Plan 16 Task 2), so S
-- steps only the online time since the return. Both clamp at maxStepS (60 min, the pipeline's sub-step bound). A
-- non-finite stamp reads none and is counted in guarded; a record with no stamp (a fresh record) steps 0 on its first
-- minute. Stamps t = ageH.
function W.satietyDtH(h, s, inp, ageH)
    local dtS = inp.dtS
    if s.t ~= nil and not NR.finite(s.t) then
        s.t = nil
        W.stats.guarded = W.stats.guarded + 1
    end
    if h.fresh == true then
        h.fresh = nil
        if s.t ~= nil then
            dtS = (ageH - s.t) * 3600
        end
    end
    s.t = ageH
    return K.clamp(dtS, 0, W.c.maxStepS) / 3600
end

-- Plan 11d Task 5 fix: the satiety fullness F the writer reads. Protein fills only here: F is the
-- stomach's fullness mass (K.stomach.fullnessMass, the satiety mass plus K.satiety.PROTEIN_FILL x the solid lane's
-- protein) over K.stomach.CAPACITY_MAX_G, clamped to [0, 1100 / 730] (K.satiety.fullness, Plan 11g spec
-- § 7); record.stomachFill, the kinetics' stamp, stays physical (K.stomach.fill, both lanes whole). A
-- record with no stomach or no buffer, or a non-finite F, reads the stamp (0 when it is not finite).
--
function W.satietyF(record)
    local st = record.stomach
    if type(st) == "table" and type(st.buffer) == "table" and W.bufferFinite(st) then
        local F = K.satiety.fullness(st)
        if NR.finite(F) then
            return F
        end
    end
    return finiteOr(record.stomachFill, 0)
end

-- Spec § 5d: the factor W.satiety multiplies the hunger target by and divides the seed
-- by: the circadian and acute product times K.satiety.sleepFactor(record.acute.debtH), the sleep debt the acute
-- kernel books at each 24 h window's close (K.acute.sleepMinute; held at 0 while the server disables sleep). A record
-- with no acute table, or a debt that is not a finite number, reads the sleep factor 1; a product that is non-finite
-- or not positive reads 1 (the seed's guarded divisor).
function W.satietyFactor(factor, record)
    local A = record.acute
    local debtH = nil
    if type(A) == "table" then
        debtH = A.debtH
    end
    local f = factor
    if NR.finite(debtH) then
        f = factor * K.satiety.sleepFactor(debtH)
    end
    if not NR.finite(f) or f <= 0 then
        return 1
    end
    return f
end

-- Whether every key of a stomach's solid buffer (K.vector.KEYS) is a finite number and its
-- liquid lane is finite (an absent lane is malformed). W.satietyF reads the stamp otherwise, so a malformed buffer (a key nil, a string or
-- NaN) never raises in K.stomach.fullnessMass and the writer still writes; Kinetics heals the buffer on its own minute
-- (KIN.malformed).
function W.bufferFinite(st)
    local b = st.buffer
    local keys = K.vector.KEYS
    for i = 1, #keys do
        if not NR.finite(b[keys[i]]) then
            return false
        end
    end
    if not NR.finite(st.liquid) or not NR.finite(st.volX) then
        return false
    end
    return true
end

-- The nicotine-withdrawal factor W.satiety multiplies into the circadian and
-- acute product, so it reaches the hunger target and the seed's divisor through W.satietyFactor. It reads the server's
-- own NICOTINE_WITHDRAWAL once a writer minute (#3637; a server-side read, the stat rising there alone, #3631) and
-- keeps the anchor s.nicH (record.satiety.nicH; stored, K.store.INPUTS): the world age in game hours at the last minute
-- the stat read 0 or fell below the previous minute's read (h.nicLast, per hoist: a fall across a reconnect or a
-- restart is not seen, and the anchor holds), so the days since the last smoke are (ageH - nicH) / 24, exact in game
-- time whatever the time speed (where the vanilla timer is not, #3636), an offline gap skipped (the resume moves the
-- anchor past it, K.resume.STAMPS).
-- A record with no anchor lays it at the minute; a stored anchor that is not a finite number, or that lies ahead of
-- the minute, is dropped (counted in guarded) and laid again.
-- A first or healed anchor laid while the stat reads above 0 starts fully faded, at ageH - NIC_FADE_DAYS x 24, so
-- the factor reads 1 (no fall seen is no evidence of a recent quit, measured-or-neutral);
-- one laid at a 0 stat or a fall sits at the minute, and from a smoke on the rise between smokes counts.
-- A stat that is not a finite number, or an absent enum key, reads 1 and leaves the anchor.
-- Returns K.satiety.nicotineFactor(w, days), at least 1.
function W.nicotine(h, s, ageH)
    local w = get(h, CharacterStat.NICOTINE_WITHDRAWAL)
    if w == nil then
        h.nicLast = nil
        return 1
    end
    if s.nicH ~= nil and (not NR.finite(s.nicH) or s.nicH > ageH) then
        s.nicH = nil
        W.stats.guarded = W.stats.guarded + 1
    end
    if w <= 0 or (h.nicLast ~= nil and w < h.nicLast) then
        s.nicH = ageH
    elseif s.nicH == nil then
        s.nicH = ageH - K.satiety.NIC_FADE_DAYS * 24
    end
    h.nicLast = w
    return K.satiety.nicotineFactor(w, (ageH - s.nicH) / 24)
end

-- Spec § 3.1, § 5b, § 5c: satiety from physiology. record.satiety is
-- { M, S, L, t }: the meal pool M (weighted kcal, fed at the eat and cleared by Kinetics), the acute
-- suppression state S and the exercise lag L (Metabolism steps it). Each minute: S and L are healed (a non-finite S or
-- L, or a negative L, is stamped 0 and counted in guarded; S is clamped to [0, 1]) and S is stepped over the elapsed
-- world age toward the vigorous kind's weight; then W.satietyMeal seeds M at first sight. The target is
-- K.satiety.target(F, M, es) = hungerTarget(sated(F, mealRead(M)), es), times circadian(the body clock's hour,
-- K.circadian.hour: 1 with sleep off, Plan 16 Task 4) x acuteFactor(S) x
-- W.nicotine's factor x sleepFactor(record.acute.debtH): h_model, kept on record.satiety.hModel (a derived field, not
-- saved: the study oracles read it, never the written HUNGER). K.hybrid.write maps it through the calibrated curve
-- (K.hungerCurve.write, which reads inp.fed, the meal pool at K.hungerCurve.FED_M or more, and inp.circ, the minute's
-- circadian factor) and caps it at hungerCap 0.69 once (below starvation, K.hybrid.caps); the curve is monotone, so a
-- swing minute's hunger is never above the same minute idle (ruling 11c-29 (3)); F is W.satietyF's fullness mass, the
-- factor W.satietyFactor's.
function W.satiety(h, player, record, eng, inp, es, ageH, ctx)
    local F = W.satietyF(record)
    local s = record.satiety
    if type(s) ~= "table" then
        s = {}
        record.satiety = s
    end
    if s.S == nil then s.S = 0 end
    if s.L == nil then s.L = 0 end
    if not NR.finite(s.S) then
        s.S = 0
        W.stats.guarded = W.stats.guarded + 1
    end
    if not NR.finite(s.L) or s.L < 0 then
        s.L = 0
        W.stats.guarded = W.stats.guarded + 1
    end
    local dtH = W.satietyDtH(h, s, inp, ageH)
    local vigorous, kind = W.vigorous(h, player, record, ctx)
    s.S = K.satiety.exerciseSuppression(s.S, dtH, vigorous, kind)
    local circ = K.satiety.circadian(K.circadian.hour(record, NR.sleepOn()))   -- the body clock's hour; 1 with sleep off
    local factor = circ * K.satiety.acuteFactor(s.S) * W.nicotine(h, s, ageH)
    factor = W.satietyFactor(factor, record)
    if s.M == nil then F = W.seedPlate(h, record, inp, F, es, factor, circ) end -- a fresh record (Plan 15 Task 13 fix 1)
    W.satietyMeal(s, inp, F, es, factor, circ)
    inp.hungerTarget = K.satiety.target(F, s.M, es) * factor
    inp.circ = circ
    inp.fed = s.M >= K.hungerCurve.FED_M
    s.hModel = inp.hungerTarget
end

-- The meal pool's seed (Plan 11g Task 4 and its fix 1): an M that is absent or non-finite is seeded so the
-- HUNGER written equals the HUNGER read, inverting the curve (K.hungerCurve.inverse, Plan 15 Task 6) and the
-- composition (K.satiety.seedMeal on that h_model / factor, W.satietyFactor's
-- divisor that is non-finite or not positive reading 1; counted in seeded, and a non-finite M in guarded too). A seed
-- under K.hungerCurve.FED_M is unfed, where the curve takes the circadian dip out (K.hungerCurve.dip), so it is seeded
-- again with the dip out of the divisor; one that then reaches FED_M keeps the first seed (the fasting hold writes no less
-- than the HUNGER read either way). A finite M is left as it is: the intake fed it at each eat, and Kinetics cleared it
-- over this minute's substeps before this step (the pipeline's ORDER runs kinetics before writer, K.satiety.drain).
function W.satietyMeal(s, inp, F, es, factor, circ)
    if not NR.finite(s.M) then
        if s.M ~= nil then W.stats.guarded = W.stats.guarded + 1 end
        local h = K.hungerCurve.inverse(inp.hunger)
        local M = K.satiety.seedMeal(h / factor, F, es)
        local dip = K.hungerCurve.dip(circ)
        if M < K.hungerCurve.FED_M and dip < 1 then
            local M2 = K.satiety.seedMeal(h * dip / factor, F, es)
            if M2 < K.hungerCurve.FED_M then
                M = M2
            end
        end
        s.M = M
        W.stats.seeded = W.stats.seeded + 1
    end
end

-- Angus's choice of 2026-10-11: monotony as a self-releasing floor. Once a
-- writer minute, W.step reads record.monotony's target (K.monotony.target at the minute's world age: the most repeated
-- food type's level, from the counts the intake books at each eat) and composes it:
--  * UNHAPPINESS: the effects' target, clamped to the effects surface's own range [0, 59] (59 one under the UNHAPPY
--    level-3 step 60, #2369), plus monotony's, which is added after that clamp: an effects bonus (the exercise credit,
-- as low as -13) never offsets monotony; an effects target that is not a finite number reads 0;
--  * BOREDOM: monotony's target alone (no other BOREDOM target exists), held under K.monotony.BORED_MAX 49.
-- K.hybrid.write raises each stat toward its target (UNHAPPINESS 22, BOREDOM 25 a game hour) and, when the target
-- falls, lowers the stat by the fall once (#3119; a fall under K.hybrid.FLOOR_EPS 0.05 is held and folded into the next write, Rule 6), so the floor is bounded by the target and releases as a varied diet
-- lets the counts decay. The release lowers the stat by the target's fall even when another source (vanilla, a food, an
-- effect) also raised it: the downside Angus accepted. Vanilla resets BOREDOM while PANIC > 5 (BodyDamage.UpdateBoredom
-- @482-@509, #3015), the mod's own dehydration PANIC floor of 7 included, so the BOREDOM floor is wiped
-- while the character panics and rises again after (K.hybrid.boredRise holds the BOREDOM rise, the target still
-- remembered). The remembered targets live on record.moodLast, so a reconnect's new hoist still releases the fall. A
-- record.monotony the heal finds corrupt is reset and counted in guarded; the heal runs at the hoist's first sight (the
-- eat heals its own), never every minute, and K.monotony.level reads a non-table entry 0. No eat adds a mood any more (NR_Server_Intake IN.monotony books only).
-- Each composed target passes the dead zone (K.monotony.hold, Plan 15 Task 9, item 10c) against its remembered target,
-- so a floor falling through a moodle threshold holds just over it until it is DEAD_ZONE of the threshold under.
W.UNHAPPY_HI = 59 -- the fallback for the effects surface's cap (NR_Data_Effects.lua SURF.unhappyTarget.hi, #2369)

function W.unhappyHi()
    local D = NR.data and NR.data.effects
    local surf = D and D.SURF and D.SURF.unhappyTarget
    if surf ~= nil and NR.finite(surf.hi) then return surf.hi end
    return W.UNHAPPY_HI
end

function W.monotony(h, record, inp, E, ageH)
    local u, b = 0, 0
    local m = record.monotony
    if m ~= nil then
        if not h.monoSeen then
            local healed
            m, healed = K.monotony.heal(m, ageH)
            if healed then
                record.monotony = m
                W.stats.guarded = W.stats.guarded + 1
            end
        end
        u, b = K.monotony.target(m, ageH)
    end
    h.monoSeen = true
    local eu = E.unhappyTarget
    if not NR.finite(eu) then eu = 0 end
    inp.lastBoredTarget = W.moodTarget(record, "b")
    inp.unhappyTarget = K.monotony.hold(K.min(eu + u, W.unhappyHi()), W.moodTarget(record, "u"), K.monotony.UNHAPPY_AT)   -- the dead zone (Plan 15 Task 9)
    inp.boredTarget = K.monotony.hold(b, inp.lastBoredTarget, K.monotony.BORED_AT)
    inp.bored = get(h, CharacterStat.BOREDOM) or 0
end

-- A remembered floor target off the record (record.moodLast, laid by W.moodWrote): absent, not a table or not a finite
-- number reads 0. It sits on the record, not the hoisted handles, so a reconnect (a new player object, a new hoist)
-- still lowers the stats by the fall the target made while the player was away.
function W.moodTarget(record, k)
    local ml = record.moodLast
    if type(ml) ~= "table" then
        return 0
    end
    if not NR.finite(ml[k]) then
        return 0
    end
    return ml[k]
end

function W.moodWrote(h, record, out)
    if type(record.moodLast) ~= "table" then
        record.moodLast = {}
    end
    record.moodLast.u = out.unhappyTarget
    set(h, CharacterStat.BOREDOM, out.bored)
    record.moodLast.b = out.boredTarget
end

function W.step(username, player, record, ctx)
    -- The dry seam: nil in production, set true only by the test harness around its
    -- ghost runs. A dry minute computes and sets nothing -- no stat write, no hoist, no engine read, and no record
    -- mutation (the meal pool's seed, the acute state, the sip fold, the landing mark) -- and is counted in stats.dry. It
    -- sits first, so every step added here later inherits it.
    if W.dry == true then
        W.stats.dry = W.stats.dry + 1
        return
    end
    if record == nil or player == nil then return end
    local h = W.h[username]
    if h == nil or h.p ~= player then
        h = W.hoist(username, player)
        W.h[username] = h
    end
    if h == nil then return end
    local ageH = NR.read.ageH(ctx)
    if ageH == nil then
        W.stats.skipped = W.stats.skipped + 1
        return
    end
    local CS = CharacterStat
    local eng = W.readEngine(username, h, player, ctx)
    local inp, out = W.input, W.output
    inp.dtS = 0
    local st = record.satiety                                       -- the stored step stamp, which the resume moves (fix 1, F3)
    if type(st) == "table" and NR.finite(st.t) then
        inp.dtS = (ageH - st.t) * 3600
    elseif h.ageH ~= nil then
        inp.dtS = (ageH - h.ageH) * 3600                            -- a stamp the satiety guard heals this minute
    end
    h.ageH = ageH
    inp.mode = W.mode
    local D = record.drain
    inp.starving = type(D) == "table" and D.starving == true      -- the caps lift (K.hybrid.caps, Plan 15 Task 5)
    inp.starveAcute = type(D) == "table" and D.starveAcute == true  -- the starving minimum's onset (Plan 15 Task 6, ruling I2)
    inp.dehydrated = type(D) == "table" and D.dehydrated == true
    inp.asleep = NR.read.asleep(ctx, player)
    inp.hunger = get(h, CS.HUNGER) or 0
    local body = record.body or {}
    local es = finiteOr(body.energyState, 1)
    W.satiety(h, player, record, eng, inp, es, ageH, ctx)
    inp.thirst = get(h, CS.THIRST) or 0
    local fl = record.fluids
    inp.thirstTarget = fl and fl.thirstTarget or nil
    inp.lastThirst = h.lastThirst
    local IN = NR.server.intake
    inp.sipOK = not (IN ~= nil and IN.landed ~= nil and IN.landed[username] == true)
    if IN ~= nil and IN.landed ~= nil then IN.landed[username] = nil end
    local A = record.acute or {}
    local E = record.effects or {}
    inp.fOwned = NR.finite(A.S)
    inp.fFrozen = A.frozen == true
    inp.fS = finiteOr(A.S, 0)
    inp.fCirc = finiteOr(A.circ, 0)
    inp.fOff = finiteOr(E.fOff, 0)
    inp.stress = get(h, CS.STRESS) or 0
    inp.stressTarget = E.stressTarget or 0
    inp.unhappy = get(h, CS.UNHAPPINESS) or 0
    W.monotony(h, record, inp, E, ageH)                   -- UNHAPPINESS: the effects' target plus monotony's; BOREDOM: monotony's (Plan 11f Task 9b)
    inp.lastUnhappyTarget = W.moodTarget(record, "u")
    inp.foodSick = get(h, CS.FOOD_SICKNESS) or 0
    inp.foodSickTarget = E.foodSickTarget or 0
    inp.foodSickStep = finiteOr(E.foodSickStep, 0)              -- a FOOD_SICKNESS level raised at once (Plan 15 Task 8 fix 1)
    inp.panic = get(h, CS.PANIC) or 0
    inp.panicTarget = E.panicTarget or 0
    inp.temp = get(h, CS.TEMPERATURE) or 0
    inp.tempTarget = E.tempTarget or 0
    inp.tempAdj = E.tempAdj or 0
    inp.intoxTarget = E.intoxTarget
    inp.endurance = eng.endurance
    inp.lastEndurance = h.lastEnd
    inp.rmod = finiteOr(body.rmod, 1)
    inp.endCap = finiteOr(E.enduranceCap, 1)                     -- the Overfull slowing's ceiling (Plan 15 Task 8)
    if inp.endCap < 1 then                                        -- sized from the day length, read only at Overfull 3-4 (fix 1)
        inp.endCap = K.hybrid.capAt(inp.endCap, NR.read.dayMin(ctx, K.drain.DAY_MINUTES))
    end
    K.hybrid.write(inp, out, W.c)
    set(h, CS.HUNGER, out.hunger)
    set(h, CS.THIRST, out.thirst)
    h.lastThirst = out.thirst
    if out.sip > W.SIP_EPS and fl ~= nil then
        fl.autoDrop = (fl.autoDrop or 0) + out.sip      -- landed as water at the next minute (ruling 7)
        W.stats.sips = W.stats.sips + 1
    end
    set(h, CS.FATIGUE, out.fatigue)
    set(h, CS.STRESS, out.stress)
    set(h, CS.UNHAPPINESS, out.unhappy)
    W.moodWrote(h, record, out)                                   -- the targets remembered, and BOREDOM written (Plan 11f Task 9b)
    set(h, CS.FOOD_SICKNESS, out.foodSick)
    set(h, CS.PANIC, out.panic)
    set(h, CS.TEMPERATURE, out.temp)
    set(h, CS.INTOXICATION, out.intox)
    set(h, CS.ENDURANCE, out.endurance)
    h.lastEnd = out.endurance or inp.endurance
    W.severe(h, player, record, inp, out, eng, ctx)               -- option B: the constant and the re-applied terms (Plan 15 Task 5)
    W.foodTimer(h, player, record, inp, ctx)                      -- Well Fed and the eating refusal (Plan 15 Task 8)
    W.stats.writes = W.stats.writes + 1
end

function W.checkNeighbours()
    if getActivatedMods == nil then return false end
    local ok, mods = pcall(getActivatedMods)
    if not ok or mods == nil then return false end
    -- on a dedicated server every entry is the bare id: GameServer.main strips backslashes from Mods= (#3569); the
    -- "\\" form is also checked because a client's list was not read
    if not NR.flag(mods, "contains", W.NMS_ID) and not NR.flag(mods, "contains", "\\" .. W.NMS_ID) then return false end
    W.stats.nms = true
    NR.log.say(1, "NutritionRevamp WARNING: Nutrition Makes Sense is loaded. Both mods write hunger, the calorie store and body weight every minute and book each other's calorie writes as meals; run one of them (see COMPATIBILITY.md). Nutrition Revamp keeps running.")
    return true
end

local function departed(username)
    W.h[username] = nil
    W.inp[username] = nil
    local IN = NR.server.intake
    if IN ~= nil and IN.landed ~= nil then IN.landed[username] = nil end
end

if Events ~= nil and Events.OnGameBoot ~= nil then
    Events.OnGameBoot.Add(W.boot)
end

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if W.wired then return end
        W.wired = true
        NR.server.minute.register("writer", W.step)
        local P = NR.server.players
        if P ~= nil then P.onDeparture[#P.onDeparture + 1] = departed end
        local O = NR.server.options
        if O ~= nil then
            O.changed[#O.changed + 1] = function(old, new)
                if old.mode ~= new.mode then
                    NR.log.say(1, "writer: NR.Mode changed to " .. tostring(new.mode) .. "; it is read at boot and takes effect at the next restart")
                end
            end
        end
        W.checkNeighbours()
    end)
end

-- Option B (Plan 15 Task 5; spec section 3.1; jar-checks Check 3; run x451). Vanilla's HUNGRY-4 and THIRST-4 health
-- terms scale with the day length (#0518); the mod's drain-and-floor engine owns those crises instead (K.drain). So
-- while the HUNGER or THIRST this minute leaves stands at level 4 (K.hybrid.severe), the writer sets the player's
-- severe-moodle constant to 0 (BodyDamage.setHealthReductionFromSevereBadMoodles, per player, from server Lua: x451;
-- at 0 the HUNGRY-4, THIRST-4, SICK-4 and under-35 kg terms stop, measured; HEAVY_LOAD and the wound-infection arm read
-- the same constant, #2356), and otherwise writes back vanilla's value, read once per player object from the getter at
-- first sight (the constructor's 0.0165, #0516), never a literal. The constant is not saved (x451's reload read
-- 0.0165), so the first minute of each player object (a load, a reconnect or a respawn) writes it whatever it wants;
-- after that it is written only when the wanted value changes (h.red, the last written; Rule 6: a steady minute costs
-- no Java call). Mode 1 only: in Overlay vanilla owns HUNGER and THIRST and the constant is never touched.
-- While the constant was 0 over the minute just past (h.red before this minute's write), W.reapply re-applies the
-- other terms it carries at vanilla's rates: vanilla's own damage, so it may take health under a drain floor, as a
-- wound does.
W.severeStats = { writes = 0, failures = 0, reapplied = 0, unread = 0 }
function W.severe(h, player, record, inp, out, eng, ctx)
    if inp.mode ~= 1 then return end
    if h.red0 == nil then
        if h.redRead then return end
        h.redRead = true
        local v = NR.num(h.bd, "getHealthReductionFromSevereBadMoodles", nil)
        if v ~= nil and v > 0 then W.red0 = v end
        h.red0 = W.red0                                         -- the first positive read, kept (one constructor value)
        if h.red0 == nil then
            W.severeStats.unread = W.severeStats.unread + 1
            return
        end
    end
    if h.red == 0 then W.reapply(h, player, record, inp, out, eng, ctx) end
    local want = h.red0
    if K.hybrid.severe(out.hunger or inp.hunger, out.thirst or inp.thirst) then want = 0 end
    if h.red ~= want then
        local ok, present = pcall(NR.call, h.bd, "setHealthReductionFromSevereBadMoodles", want)
        if ok and present then
            h.red = want
            W.severeStats.writes = W.severeStats.writes + 1
        else
            W.severeStats.failures = W.severeStats.failures + 1
        end
    end
end

W.LOWWEIGHT_KG = 35 -- VANILLA #3881: setWeight's floor, under which it takes the constant times the multiplier
W.HEAVY_HEALTH = 75 -- VANILLA #2356: the heavy-load term runs only above 75 overall health (BodyDamage.Update L2390)

-- Whether vanilla's heavy-load term would run this minute (#2356): not in a vehicle, not asleep, not sitting (on the
-- ground or furniture: IsoGameCharacter.isSitting, the writer's eng.sitting), a metabolic target other than
-- SeatedResting's 1.0 MET (#2632), and above 75 health. The server's fast-forward runs only while every player sleeps
-- (an inference), which the asleep test already covers. Returns the health read (nil when the term is off).
function W.heavyHealth(h, player, inp, eng)
    if inp.asleep or (eng ~= nil and eng.sitting) then return nil end
    if NR.obj(player, "getVehicle") ~= nil then return nil end
    if NR.num(h.thermo, "getMetabolicTarget", nil) == K.energy.CLASS_MET.SeatedResting then return nil end
    local health = NR.num(h.bd, "getOverallBodyHealth", nil)
    if health == nil or not (health > W.HEAVY_HEALTH) then return nil end
    return health
end

-- Vanilla's SICK, BLEEDING, HEAVY_LOAD and under-35 kg terms over the minute just past, while the constant was 0:
-- their multiple of the constant per multiplier unit (K.hybrid.severeRate) times the constant times the multiplier
-- units of the elapsed game time (120 x the day length's real minutes a game hour, #2922; the step clamped at 60 game
-- minutes as the write's), through one ReduceGeneralHealth; the heavy-load share is held to health - 75 (vanilla stops
-- there), and half of it goes to back-muscle strain (addBackMuscleStrain, as vanilla's L2393). SICK 4's arms:
-- FOOD_SICKNESS over ZOMBIE_INFECTION, or the WoundInfectionFactor option above 0 and the general wound-infection level
-- over ZOMBIE_INFECTION (#2356). The under-35 kg term is the mod's own setWeight call (the weight step, which ran this
-- minute under the same constant; with Nutrition off vanilla's updateWeight never runs, Nutrition.update L65-L66, read
-- on 42.21): one call's constant times the multiplier (#3881). Moodles are read only here, on a minute the constant was 0
-- (NR.read.moodleLevel); the day length is the player-minute's shared read (NR.read.dayMin, one with Effects' heal).
function W.reapply(h, player, record, inp, out, eng, ctx)
    local MT = MoodleType
    local CS = CharacterStat
    local dayMin = NR.read.dayMin(ctx, K.drain.DAY_MINUTES)
    local units = K.clamp(inp.dtS, 0, W.c.maxStepS) / 60 * K.drain.UNITS_PER_MIN * dayMin
    local sick, bleed, heavy = 0, 0, 0
    if MT ~= nil then
        sick = NR.read.moodleLevel(h.moodles, MT.SICK)
        bleed = NR.read.moodleLevel(h.moodles, MT.BLEEDING)
        heavy = NR.read.moodleLevel(h.moodles, MT.HEAVY_LOAD)
    end
    local sickArm = false
    if sick == 4 then
        local zi = get(h, CS.ZOMBIE_INFECTION) or 0
        local fs = out.foodSick or inp.foodSick
        if fs > zi then
            sickArm = true
        else
            local wif = SandboxVars and SandboxVars.WoundInfectionFactor or 0
            sickArm = type(wif) == "number" and wif > 0 and NR.num(h.bd, "getGeneralWoundInfectionLevel", 0) > zi
        end
    end
    local health = nil
    if heavy > 2 then health = W.heavyHealth(h, player, inp, eng) end
    local f, fHeavy = K.hybrid.severeRate(sick, sickArm, bleed, heavy, health ~= nil)
    local yHeavy = fHeavy * h.red0 * units
    if health ~= nil then yHeavy = K.min(yHeavy, health - W.HEAVY_HEALTH) end
    local y = (f - fHeavy) * h.red0 * units + yHeavy
    local body = record.body
    if body ~= nil and NR.finite(body.fm) and NR.finite(body.lm) and NR.finite(body.lx)
            and body.fm + body.lm + body.lx < W.LOWWEIGHT_KG and getGameTime ~= nil then
        local okT, gt = pcall(getGameTime)
        y = y + h.red0 * NR.num(okT and gt or nil, "getMultiplier", 0)
    end
    if y > 0 then
        pcall(NR.call, h.bd, "ReduceGeneralHealth", y)
        W.severeStats.reapplied = W.severeStats.reapplied + 1
    end
    if yHeavy > 0 then
        pcall(NR.call, player, "addBackMuscleStrain", yHeavy * K.hybrid.HEAVY_STRAIN)
    end
end

-- The food-timer bridge (Plan 15 Task 8; spec sections 2.3 and 2.4; jar-checks Check 1). The mod owns vanilla's
-- health-from-food timer, which alone drives the FOOD_EATEN moodle (Well Fed) and vanilla's eat and drink refusals at its
-- level 3 (#0511; jar-checks Check 1c): each minute the target is K.view.foodTimer of the Overfull level (K.view.overfullOf,
-- the client moodle's number), the meal pool M (record.satiety.M, this minute's, after the satiety step) and whether a
-- drain state is active (record.drain.active), and BodyDamage.setHealthFromFoodTimer writes it (#3896: a server write
-- reaches the client's moodle and its eat gates through the 1 Hz stats packet). Vanilla drains the timer between writes
-- (#2385), so a target above 0 is written every minute (one Java call a sated minute); a target of 0 is written only on
-- the change to 0 and vanilla's own drain keeps it there (no call on a steady unfed minute, Rule 6), except on a minute an
-- intake landed (IN.landed, an eat or a drink): vanilla's eat at HUNGER 0 (#3598) and every drink (jar-checks Check 1
-- J1.1, ungated) add to the timer, so that minute writes the target again. The timer is saved (saveMainFields) but the
-- mod's last write is not, so the first minute of each player object (a load, a reconnect or a respawn) writes whatever
-- it wants. sendSyncPlayerFields(player, 8) (the body-damage main fields, the timer among them; #2602, a server-only
-- global) pushes only when the FOOD_EATEN band of the value written changes (K.view.timerBand), so a level the player
-- sees moves at once and the stats packet carries the rest. Mode 1 only: in Overlay vanilla owns HUNGER and its own timer.
W.timerStats = { writes = 0, failures = 0, pushes = 0, pushMissing = 0 }
function W.foodTimer(h, player, record, inp, ctx)
    if inp.mode ~= 1 then return end
    local s = record.satiety
    local D = record.drain
    local level = K.view.overfullOf(record)
    local M = s and s.M
    local draining = type(D) == "table" and D.active == true
    local want = K.view.foodTimer(level, M, draining)
    if want == 0 and h.ft == 0 and inp.sipOK then return end   -- held at 0 by vanilla's own drain, no landing: no call
    if want > 0 then                                           -- sized from the day length: one shared read, sated minutes only
        want = K.view.foodTimer(level, M, draining, NR.read.dayMin(ctx, K.drain.DAY_MINUTES))
    end
    local ok, present = pcall(NR.call, h.bd, "setHealthFromFoodTimer", want)
    if not (ok and present) then
        W.timerStats.failures = W.timerStats.failures + 1
        return
    end
    h.ft = want
    W.timerStats.writes = W.timerStats.writes + 1
    local band = K.view.timerBand(want)
    if h.ftBand == band then return end
    h.ftBand = band
    local f = sendSyncPlayerFields
    if f ~= nil and pcall(f, player, 8) then
        W.timerStats.pushes = W.timerStats.pushes + 1
    else
        W.timerStats.pushMissing = W.timerStats.pushMissing + 1
    end
end
-- The seed plate (Plan 15 Task 13 fix 1, the controller's ruling, option (a)): on an empty stomach the meal pool alone
-- cannot write a HUNGER under the curve of hungerTarget(0.786, energy state) times the minute's factors (mealRead is
-- nearly flat in M, so the seed caps at K.satiety.MEAL_SEED_MAX and a fresh spawn at HUNGER 0 would write about 0.13),
-- so a fresh record (satiety.M absent) whose vanilla HUNGER sits more than the dead zone under that floor lands a real
-- meal first, as if the survivor ate before the first morning: the curve fit's plate (tools/fit_hunger_curve.py
-- PLATE, the guide's foods, their whole vectors from the mod's table summed and scaled) through the intake's own landing
-- (IN.land: the stomach, the meal pool, the day's intake), sized by bisection to the least kcal whose first write is
-- within K.hungerCurve.DEAD_ZONE of the vanilla HUNGER, at most W.SEED_PLATE_MAX; a record seen before never takes one.
-- Once per fresh record, so no per-minute cost.
W.SEED_PLATE = {
    "Base.CannedBologneseOpen", -- the curve fit's plate (tools/fit_hunger_curve.py PLATE): game choice (spec section 10: the curve's knots)
    "Base.Bread", -- the fit's plate: game choice (spec section 10: the curve's knots)
    "Base.Apple", -- the fit's plate: game choice (spec section 10: the curve's knots)
    "Base.Orange", -- the fit's plate: game choice (spec section 10: the curve's knots)
    "Base.Burger", -- the fit's plate: game choice (spec section 10: the curve's knots)
    "Base.TunaTinOpen", -- the fit's plate: game choice (spec section 10: the curve's knots)
}
W.SEED_PLATE_MAX = 667 -- kcal, one fit meal (tools/fit_hunger_curve.py MEAL_KCAL, a third of 2,000 kcal): game choice (spec section 10: the curve's knots)
W.SEED_PLATE_STEPS = 24 -- bisection steps on the kcal (under 1e-4 kcal), no row needed

-- The seed plate at kcal: (its vector, scaled from the foods' whole vectors summed, and its mass-weighted plate volume
-- per gram, IN.volumeOf of each food).
function W.seedPlateVector(kcal)
    local tot = K.vector.new()
    local mass = 0
    local volX = 0
    for i = 1, #W.SEED_PLATE do
        local ft = W.SEED_PLATE[i]
        local t = NR.data.nutrients.get(ft)
        if t ~= nil then
            local v = K.vector.add(K.vector.new(), t, 1)
            local m = K.stomach.massOf(v)
            K.vector.add(tot, v, 1)
            mass = mass + m
            volX = volX + (NR.server.intake.volumeOf(ft) - 1) * m
        end
    end
    local f = 0
    if tot.calories > 0 then f = kcal / tot.calories end
    local ml = 1
    if mass > 0 then ml = 1 + volX / mass end
    return K.vector.add(K.vector.new(), tot, f), ml
end

-- The HUNGER a fresh record's first minute writes with the seed plate of kcal in its empty stomach.
function W.seedPlateWrite(kcal, inp, es, factor, circ)
    local v, ml = W.seedPlateVector(kcal)
    local st = K.stomach.new()
    K.stomach.ingest(st, v, ml)
    local M = K.satiety.mealFeed(0, v)
    local hm = K.satiety.target(K.satiety.fullness(st), M, es) * factor
    return K.hungerCurve.write(hm, { hunger = inp.hunger, fed = M >= K.hungerCurve.FED_M, circ = circ })
end

-- The seed plate's landing (see W.SEED_PLATE): returns the fullness to read this minute, F unchanged when no plate
-- lands. A plate W.SEED_PLATE_MAX cannot bring within the dead zone lands at that size and is counted in seedShort.
function W.seedPlate(h, record, inp, F, es, factor, circ)
    local DZ = K.hungerCurve.DEAD_ZONE
    local floor = K.hungerCurve.write(K.satiety.target(F, K.satiety.MEAL_SEED_MAX, es) * factor,
        { hunger = inp.hunger, fed = true, circ = circ })
    if inp.hunger + DZ >= floor or type(record.stomach) ~= "table" or NR.server.intake == nil then return F end
    local want = inp.hunger + DZ
    local hi = W.SEED_PLATE_MAX
    if W.seedPlateWrite(hi, inp, es, factor, circ) > want then
        W.stats.seedShort = W.stats.seedShort + 1
    else
        local lo = 0
        for _ = 1, W.SEED_PLATE_STEPS do
            local mid = (lo + hi) / 2
            if W.seedPlateWrite(mid, inp, es, factor, circ) <= want then hi = mid else lo = mid end
        end
    end
    local v, ml = W.seedPlateVector(hi)
    record.satiety.M = 0
    NR.server.intake.land(record, h.username, v, nil, ml)
    W.stats.seedPlates = W.stats.seedPlates + 1
    W.lastSeedKcal = hi
    return W.satietyF(record)
end
