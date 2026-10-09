-- NR_Server_Writer.lua -- the once-a-minute stat writer (Plan 11 Task 14; Decision 1 (c), the hybrid). At the
-- server's OnGameBoot (one instruction before ZomboidGlobals.Load copies the Lua table, #3364) it reads NR.Mode,
-- saves the seven hunger, thirst and fatigue rise rates (#3362) and, in Mode 1, sets each to 0, never nil (#3366);
-- a client never reads the mode at its OnGameBoot (#3381) and never zeroes. Once a player-minute, as the pipeline's
-- step after weight and before store (after the minute's eats and the effects build, #3383), it writes HUNGER,
-- THIRST and FATIGUE and the floors, PANIC, TEMPERATURE and INTOXICATION through K.hybrid.write, stepping by elapsed
-- world age (#3371) and folding each auto-drink sip into the THIRST target (#3382). The HUNGER target is
-- hungerTarget(sated(F, post(P)), energyState) x circadian(hour) x acuteFactor(S) x sleepFactor(debtH), capped at 0.69 (Plan 11c, Plan 11d; NR_Kernel_Satiety.lua):
-- the stomach's fullness F (W.satietyF), the meal pool P (fed at the eat by the intake, decayed here), the acute suppression S
-- of vigorous work (stepped here) and the acute record's sleep debt debtH (W.satietyFactor). It registers no stat hook.
-- Every Java read goes through NR.num / NR.obj / NR.flag; every Java global is named inside a function behind a
-- nil check, so the file loads with no engine. Slow-clock code: no @fastpath region.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.writer = {
    h = {}, inp = {}, saved = nil, zeroed = false, mode = 1, wired = false, so = nil,
    stats = { writes = 0, failures = 0, sips = 0, skipped = 0, seeded = 0, guarded = 0, nms = false, dry = 0 },
    limitations = {
        "the mode (NR.Mode) is read once at the server's OnGameBoot; a change takes effect at the next restart (no mod route re-runs ZomboidGlobals.Load, #3365)",
        "with the rates zeroed, a writer outage stops hunger, thirst and fatigue rather than falling back to vanilla (Decision 1)",
        "other mods reading ZomboidGlobals' hunger, thirst and fatigue rise rates read 0; NutritionRevamp.vanillaRate(key) answers the values saved before zeroing",
        "HUNGER, THIRST and FATIGUE are written once a game minute; an eat or a drink shows at once and the next write overwrites it with the satiety target, hungerTarget(sated(F, post(P)), energyState) x the circadian factor x the acute exercise factor x the sleep-debt factor, capped at 0.69: F is the stomach's fullness mass (its satiety mass plus the protein term) over its 730 g maximum, drunk liquid counting at a fifth, and P the meal pool, fed at the eat with the eaten vector's weighted kcal and decaying on game time asleep or awake, so displayed hunger never reaches 0 after a meal (about 0.1 after a typical meal, about 0.09 at a full stomach), and a vanilla HUNGER below the seed floor reads it on its first minute: hungerTarget(0.797, energy state), that is 0.203 x es + 0.15 x max(0, es - 1), times the minute's circadian, acute and sleep factors (an empty stomach's read at the seed's cap P_SEED_MAX); protein fills the satiety fullness while it is in the stomach (a fitted game choice); an eat another mod makes through a direct Eat call reaches the stomach and P through the reconcile path a minute late and as its macros only (no water or fibre mass), and a drink another mod makes through a direct DrinkFluid call outside the intake's wraps is not seen; an eat landing in a fresh record's first minute, before the writer has seeded P, shows only through the HUNGER the seed reads; the exercise share of the energy deficit enters hunger through a lag of weeks, so a regular exerciser who eats to balance reads lower hunger for weeks; heavy work the model does not class as vigorous (neither the swing state nor the heavy-work band) overshoots the hunger rise of a heavy labour deficit (S1325); past 730 g in the stomach the mod's own Overfull moodle rises in four levels to 1100 g (the soft cap: shown, never a block), and vanilla's own refusal to start an eat at the FOOD_EATEN moodle's level 3 stands; fibre sates only through its mass, and carbohydrate, sugar, starch and fat take one weight per kcal (the evidence is mixed or absent: rulings 11c-6 and 11c-7); a vanilla HUNGER above the fullness ceiling, hungerTarget(0.55 F, energy state), that is (1 - 0.55 F) x es + 0.15 x max(0, es - 1), times the minute's circadian, acute and sleep factors, seeds an empty pool, so a migrated full-stomached character's first written HUNGER drops to that ceiling; short sleep raises hunger by a factor capped at the pooled size, whether a step or graded is unsettled; the sleep factor steps at the acute record's 24 h window close, not at waking, so a short night that straddles the close reaches hunger in two steps a day apart; after a short night, nights of exactly the need repay nothing, so the rise holds until a longer night repays half its excess; right at a bout's end the acute term reads deeper than the pooled immediate-post effect (ruling T1-3); glycogen depletion no longer raises hunger, so past about 24-36 h of fasting the energy state's balance term sits at its cap (es 1.5; ruling T4-1); heat's lowering of intake is not modelled (cold reaches hunger through its expenditure); sugary drinks, ketosis, alcohol's aperitif effect, aerated foods' volume and eating rate are neutral; injury adds no expenditure",
        "PANIC is written once a game minute and vanilla decays it between writes, up to 1.2556 under its floor at DayLength 1 (#3400); vanilla's panic rise between writes is unread",
        "TEMPERATURE is written once a game minute on the adjustment's far side (held within 0.04 C, #3393)",
        "an auto-drink sip in a minute when the intake also landed an eat or a drink is missed once and caught at the next minute",
        "asleep, FATIGUE saw-tooths by one minute of vanilla's recovery and the endurance rmod applies one minute late",
        "the sleep-onset latency terms (solAddH, solMul) are not applied: vanilla sets the sleep delay",
        "the Effects step reads the writer's engine reads of the previous minute",
        "in Overlay (Mode 2) vanilla owns HUNGER, THIRST and FATIGUE; the floors, PANIC, TEMPERATURE and INTOXICATION are still written; auto-drink is not captured",
        "another mod whose OnGameBoot handler runs after ours and sets ZomboidGlobals' hunger, thirst or fatigue rise keys (before ZomboidGlobals.Load, #3364) restores vanilla's drift between the writer's minute writes: HUNGER, THIRST and FATIGUE climb at its rates each tick and the next minute's write takes them back (the satiety pool decays at its own half-life, never at those rates)",
    },
}
local W = NR.server.writer
W.RATE_KEYS = { "HungerIncrease", "HungerIncreaseWhenWellFed", "HungerIncreaseWhileAsleep",
                "HungerIncreaseWhenExercise", "ThirstIncrease", "ThirstSleepingIncrease", "FatigueIncrease" } -- #3362
W.NMS_ID = "NutritionMakesSense" -- its 42/mod.info id= (Plan 11 Task 1)
-- the sleep bed factor (IsoPlayer.updateStats_Sleeping @109-@244, #2276; moved from NR_Server_Fast)
W.BED = { badBed = 0.9, badBedPillow = 0.95, averageBedPillow = 1.05, goodBed = 1.1, goodBedPillow = 1.15,
          floor = 0.6, floorPillow = 0.75 }
W.c = K.hybrid.defaults()
W.input = K.hybrid.input()
W.output = K.hybrid.output()

-- The rates the server ran before the zeroing (nil when unread), else the live table's value.
function NR.vanillaRate(key)
    if W.saved ~= nil and W.saved[key] ~= nil then return W.saved[key] end
    if type(ZomboidGlobals) == "table" and type(ZomboidGlobals[key]) == "number" then return ZomboidGlobals[key] end
    return nil
end

function NR.vanillaRates()
    local out = {}
    for i = 1, #W.RATE_KEYS do
        out[W.RATE_KEYS[i]] = NR.vanillaRate(W.RATE_KEYS[i])
    end
    return out
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

local function trait(h, id)
    if id == nil then return false end
    return NR.flag(h.traits, "get", id)
end

-- The handles, once per player object (a respawn or a reconnect is a new object, #3360): nil when the player has
-- no stats object or the stat enum is absent, and the writer then writes nothing for that player.
function W.hoist(username, p)
    local stats = NR.obj(p, "getStats")
    if stats == nil or CharacterStat == nil then return nil end
    local h = { p = p, stats = stats, moodles = NR.obj(p, "getMoodles"), bd = NR.obj(p, "getBodyDamage"),
                traits = NR.obj(p, "getCharacterTraits"), ageH = nil, lastThirst = nil, lastEnd = nil,
                unhappyLast = 0, swipe = nil, fresh = true }  -- fresh: no step yet, W.satietyDtH reads the stamp
    h.thermo = NR.obj(h.bd, "getThermoregulator")
    if SwipeStatePlayer ~= nil and SwipeStatePlayer.instance ~= nil then
        local ok, sw = pcall(SwipeStatePlayer.instance)    -- the melee swing state: vigorous work for the acute term
        if ok then h.swipe = sw end
    end
    pcall(NR.call, h.bd, "setDrunkReductionValue", 0)       -- ruling 19 kept: the writer owns INTOXICATION
    if W.so == nil and getSandboxOptions ~= nil then
        local ok, so = pcall(getSandboxOptions)
        if ok then W.so = so end
    end
    return h
end

-- The engine reads Effects' accrual and recovery need (the takeover's input table fields it read, B3 and B4).
function W.readEngine(username, h, p)
    local i = W.inp[username]
    if i == nil then
        i = {}
        W.inp[username] = i
    end
    local T = CharacterTrait
    i.endurance = get(h, CharacterStat.ENDURANCE) or 1
    i.endFold = false
    i.sitting = NR.flag(p, "isSitOnGround") or NR.flag(p, "isSittingOnFurniture")
    i.resting = NR.flag(p, "isResting")
    i.thermoFatigue = NR.num(h.thermo, "getFatigueMultiplier", 1)
    i.sd = NR.num(W.so, "getStatsDecreaseMultiplier", 1)
    i.needsLess = T ~= nil and trait(h, T.NEEDS_LESS_SLEEP)
    i.needsMore = T ~= nil and trait(h, T.NEEDS_MORE_SLEEP)
    i.insomniac = T ~= nil and trait(h, T.INSOMNIAC)
    i.nightOwl = T ~= nil and trait(h, T.NIGHT_OWL)
    i.bedFactor = W.BED[NR.obj(p, "getBedType")] or 1
    return i
end

local function finiteOr(v, dflt)
    if NR.finite(v) then return v end
    return dflt
end

-- The hour of day the circadian factor reads: the game clock's getTimeOfDay, else the world age's hour (the seam the
-- Metabolism, Nutrients and Strength adapters read).
function W.hourOfDay(ageH)
    local hour = ageH - math.floor(ageH / 24) * 24
    if getGameTime ~= nil then
        local ok, gt = pcall(getGameTime)
        hour = NR.num(ok and gt or nil, "getTimeOfDay", hour)
    end
    return hour
end

-- Vigorous work for the acute suppression term (spec § 5c, ruling 11c-29; ruling T6-2): the melee or tool swing state is
-- resistance-type work; else Metabolism's stamp of the minute's billed MET at the Compendium's HeavyWork band or above
-- (6.0) is vigorous, and the kind follows the metabolism class Metabolism stamps on the minute's ctx: Fitness,
-- FitnessHeavy, ClimbRope (rope climbing, and tree chopping: classOf reads ForestryAxe's 8.0 as ClimbRope, ruling T6-3)
-- and ForestryAxe are resistance work, as is any minute with a Fitness exercise in progress (ctx.exercising: the engine
-- classes a 6.0 exercise as HeavyWork); DiggingSpade and UsingTools bill under 6.0 and are listed inert (S1301, S1305).
-- The run flag never reaches the server (x141a), so a runner is not vigorous unless the metabolic rate classes it so.
-- Returns vigorous, kind (K.satiety.ACUTE_KIND's keys). ctx is nil or lacks the stamp: the class is unknown, aerobic.
W.RESISTANCE_CLASSES = { Fitness = true, FitnessHeavy = true, ClimbRope = true, ForestryAxe = true, DiggingSpade = true, UsingTools = true }
function W.vigorous(h, player, record, ctx)
    if h.swipe ~= nil and NR.flag(player, "isCurrentState", h.swipe) then return true, "resistance" end
    local met = record.body and record.body.met
    if NR.finite(met) and met >= K.energy.COMPENDIUM.HeavyWork then
        if ctx ~= nil and (ctx.exercising == true or W.RESISTANCE_CLASSES[ctx.activityClass] == true) then return true, "resistance" end
        return true, "aerobic"
    end
    return false, nil
end

-- Plan 11c (spec § 3.1, § 5b, § 5c; Task 6 amendments 3 and 4): satiety from physiology. record.satiety is
-- { P, S, L, v = 4 }: the meal pool P (weighted kcal, fed at the eat by the intake), the acute suppression state S and
-- the exercise lag L (Metabolism steps it). Each minute: S and L are healed (a non-finite S or L, or a negative L, is
-- stamped 0 and counted in guarded; S is clamped to [0, 1]) and S is stepped over the elapsed world age toward the
-- vigorous kind's weight; a P that is absent, unmarked (v ~= 4) or non-finite is seeded so the HUNGER written equals
-- the HUNGER read, inverting the composition below (K.satiety.seedP on hunger / (circadian x acuteFactor x sleepFactor), W.satietyFactor's divisor
-- that is non-finite or not positive reading 1; counted in seeded, and a non-finite P in guarded too); otherwise P
-- decays over the elapsed world age at the half-life, scaled by the appetite trait (#0485) and the sandbox's
-- stats-decrease multiplier (ruling 11c-11), a P the decay makes non-finite re-stamped from its pre-step value
-- (counted in guarded). The target is hungerTarget(sated(F, post(P)), es) x circadian(hour) x acuteFactor(S) x sleepFactor(record.acute.debtH), which
-- K.hybrid.write caps at hungerCap 0.69 once: min(0.69, target x circadian x acute x sleep), so a swing minute's hunger is
-- never above the same minute idle (ruling 11c-29 (3)); F is W.satietyF's fullness mass (ruling T5-2), the factor W.satietyFactor's (Plan 11d Task 6).
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
    local factor = K.satiety.circadian(W.hourOfDay(ageH)) * K.satiety.acuteFactor(s.S)
    factor = W.satietyFactor(factor, record)
    if s.v ~= 4 or not NR.finite(s.P) then
        if s.P ~= nil and not NR.finite(s.P) then W.stats.guarded = W.stats.guarded + 1 end
        s.P = K.satiety.seedP(inp.hunger / factor, F, es)
        s.v = 4
        W.stats.seeded = W.stats.seeded + 1
    else
        local P0 = s.P
        local T = CharacterTrait
        local tr = K.satiety.trait(T ~= nil and trait(h, T.HEARTY_APPETITE), T ~= nil and trait(h, T.LIGHT_EATER))
        s.P = K.satiety.decay(s.P, dtH, K.satiety.HALF_LIFE_H, tr * eng.sd)
        if not NR.finite(s.P) then
            s.P = P0
            W.stats.guarded = W.stats.guarded + 1
        end
    end
    inp.hungerTarget = K.hybrid.hungerTarget(K.satiety.sated(F, K.satiety.post(s.P)), es) * factor
end

function W.step(username, player, record, ctx)
    -- The dry seam (Plan 11 Task 19, ruling 15): nil in production, set true only by the test harness around its
    -- ghost runs. A dry minute computes and sets nothing -- no stat write, no hoist, no engine read, and no record
    -- mutation (the satiety pool's seed and decay, the acute state, the sip fold, the landing mark) -- and is counted in stats.dry. It
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
    local ageH = NR.worldAge()
    if ageH == nil then
        W.stats.skipped = W.stats.skipped + 1
        return
    end
    local CS = CharacterStat
    local eng = W.readEngine(username, h, player)
    local inp, out = W.input, W.output
    inp.dtS = 0
    if h.ageH ~= nil then inp.dtS = (ageH - h.ageH) * 3600 end
    h.ageH = ageH
    inp.mode = W.mode
    inp.asleep = NR.flag(player, "isAsleep")
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
    inp.unhappyTarget = E.unhappyTarget or 0
    inp.lastUnhappyTarget = h.unhappyLast
    inp.foodSick = get(h, CS.FOOD_SICKNESS) or 0
    inp.foodSickTarget = E.foodSickTarget or 0
    inp.panic = get(h, CS.PANIC) or 0
    inp.panicTarget = E.panicTarget or 0
    inp.temp = get(h, CS.TEMPERATURE) or 0
    inp.tempTarget = E.tempTarget or 0
    inp.tempAdj = E.tempAdj or 0
    inp.intoxTarget = E.intoxTarget
    inp.endurance = eng.endurance
    inp.lastEndurance = h.lastEnd
    inp.rmod = finiteOr(body.rmod, 1)
    K.hybrid.write(inp, out, W.c)
    set(h, CS.HUNGER, out.hunger)
    set(h, CS.THIRST, out.thirst)
    h.lastThirst = out.thirst
    if out.sip > 0 and fl ~= nil then
        fl.autoDrop = (fl.autoDrop or 0) + out.sip      -- landed as water at the next minute (ruling 7)
        W.stats.sips = W.stats.sips + 1
    end
    set(h, CS.FATIGUE, out.fatigue)
    set(h, CS.STRESS, out.stress)
    set(h, CS.UNHAPPINESS, out.unhappy)
    h.unhappyLast = out.unhappyTarget
    set(h, CS.FOOD_SICKNESS, out.foodSick)
    set(h, CS.PANIC, out.panic)
    set(h, CS.TEMPERATURE, out.temp)
    set(h, CS.INTOXICATION, out.intox)
    set(h, CS.ENDURANCE, out.endurance)
    h.lastEnd = out.endurance or inp.endurance
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

-- Plan 11c close (ruling C-1): the satiety step's length in game hours, P's decay and S's step. A minute on the same
-- player object reads the writer's own inp.dtS. The first minute of a new object (a reconnect or a respawn, #3360) or
-- of a restart, whose hoist holds no age (h.fresh), reads the gap from the stamp record.satiety.t the writer leaves at
-- every step (game hours; stored, K.store.INPUTS), so P and S decay across the gap as Kinetics and Metabolism catch it
-- up. Both clamp at maxStepS (60 min). A non-finite stamp reads none and is counted in guarded; a record with no stamp
-- (a v3 record, a fresh one) steps 0 on its first minute. Stamps t = ageH.
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

-- Plan 11d Task 5 fix (ruling T5-2): the satiety fullness F the writer reads. Protein fills only here: F is the
-- stomach's fullness mass (K.stomach.fullnessMass, the satiety mass plus K.satiety.PROTEIN_FILL x the solid lane's
-- protein, ruling 11d-5) over K.stomach.CAPACITY_MAX_G, clamped to [0, 1]; record.stomachFill, the kinetics' stamp,
-- stays physical (K.stomach.fill), because NUT.FED_FILL and the acute dose test's ACUTE_EMPTY_FILL gate on grams of
-- contents. A record with no stomach or no buffer, or a non-finite F, reads the stamp (0 when it is not finite).
-- Appended so no line above moves.
function W.satietyF(record)
    local st = record.stomach
    if type(st) == "table" and type(st.buffer) == "table" and W.bufferFinite(st) then
        local F = K.satiety.fill(K.stomach.fullnessMass(st), K.stomach.CAPACITY_MAX_G)
        if NR.finite(F) then
            return F
        end
    end
    return finiteOr(record.stomachFill, 0)
end

-- Plan 11d Task 6 (ruling 11d-2, spec § 5d): the factor W.satiety multiplies the hunger target by and divides the seed
-- by: the circadian and acute product times K.satiety.sleepFactor(record.acute.debtH), the sleep debt the acute
-- kernel books at each 24 h window's close (K.acute.sleepMinute; held at 0 while the server disables sleep). A record
-- with no acute table, or a debt that is not a finite number, reads the sleep factor 1; a product that is non-finite
-- or not positive reads 1 (the seed's guarded divisor). Appended so no line above moves.
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

-- Plan 11d close (ruling C-1): whether every key of a stomach's solid buffer (K.vector.KEYS) is a finite number and its
-- liquid lane is absent or finite. W.satietyF reads the stamp otherwise, so a malformed buffer (a key nil, a string or
-- NaN) never raises in K.stomach.fullnessMass and the writer still writes; Kinetics heals the buffer on its own minute
-- (KIN.malformed). Appended so no line above moves.
function W.bufferFinite(st)
    local b = st.buffer
    local keys = K.vector.KEYS
    for i = 1, #keys do
        if not NR.finite(b[keys[i]]) then
            return false
        end
    end
    if st.liquid ~= nil and not NR.finite(st.liquid) then
        return false
    end
    return true
end
