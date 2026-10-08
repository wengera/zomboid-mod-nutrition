-- NR_Server_Writer.lua -- the once-a-minute stat writer (Plan 11 Task 14; Decision 1 (c), the hybrid). At the
-- server's OnGameBoot (one instruction before ZomboidGlobals.Load copies the Lua table, #3364) it reads NR.Mode,
-- saves the seven hunger, thirst and fatigue rise rates (#3362) and, in Mode 1, sets each to 0, never nil (#3366);
-- a client never reads the mode at its OnGameBoot (#3381) and never zeroes. Once a player-minute, as the pipeline's
-- step after weight and before store (after the minute's eats and the effects build, #3383), it writes HUNGER,
-- THIRST and FATIGUE and the floors, PANIC, TEMPERATURE and INTOXICATION through K.hybrid.write, stepping by elapsed
-- world age (#3371) and folding each auto-drink sip into the THIRST target (#3382). The HUNGER target is 1 - S, the
-- satiety scalar (Task 15; NR_Kernel_Satiety.lua), stepped here at the rates saved at boot. It registers no stat hook.
-- Every Java read goes through NR.num / NR.obj / NR.flag; every Java global is named inside a function behind a
-- nil check, so the file loads with no engine. Slow-clock code: no @fastpath region.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.writer = {
    h = {}, inp = {}, saved = nil, rates = nil, zeroed = false, mode = 1, wired = false, so = nil,
    stats = { writes = 0, failures = 0, sips = 0, skipped = 0, seeded = 0, nms = false },
    limitations = {
        "the mode (NR.Mode) is read once at the server's OnGameBoot; a change takes effect at the next restart (no mod route re-runs ZomboidGlobals.Load, #3365)",
        "with the rates zeroed, a writer outage stops hunger, thirst and fatigue rather than falling back to vanilla (Decision 1)",
        "other mods reading ZomboidGlobals' hunger, thirst and fatigue rise rates read 0; NutritionRevamp.vanillaRate(key) answers the values saved before zeroing",
        "HUNGER, THIRST and FATIGUE are written once a game minute; an eat shows at once and the next write overwrites it with 1 - S, so the eat stays only through the satiety scalar it raised; hunger is that scalar stepped once a game minute, so it lags vanilla by up to a minute (5.8e-4 idle, 1.2e-3 exercising; Appendix D); under a calorie deficit vanilla's food-eaten freeze fires less often, and at the 0.69 cap a starving character can earn a freeze its scalar did not (Appendix D Question 4)",
        "PANIC is written once a game minute and vanilla decays it between writes, up to 1.2556 under its floor at DayLength 1 (#3400); vanilla's panic rise between writes is unread",
        "TEMPERATURE is written once a game minute on the adjustment's far side (held within 0.04 C, #3393)",
        "an auto-drink sip in a minute when the intake also landed an eat or a drink is missed once and caught at the next minute",
        "asleep, FATIGUE saw-tooths by one minute of vanilla's recovery and the endurance rmod applies one minute late",
        "the sleep-onset latency terms (solAddH, solMul) are not applied: vanilla sets the sleep delay",
        "the Effects step reads the writer's engine reads of the previous minute",
        "in Overlay (Mode 2) vanilla owns HUNGER, THIRST and FATIGUE; the floors, PANIC, TEMPERATURE and INTOXICATION are still written; auto-drink is not captured",
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
    -- the satiety scalar's rates (Task 15): the saved values, each unread one vanilla's defines.lua default
    local d = K.satiety.defaults()
    W.rates = { idle = W.saved.HungerIncrease or d.idle, wellFed = W.saved.HungerIncreaseWhenWellFed or d.wellFed,
                asleep = W.saved.HungerIncreaseWhileAsleep or d.asleep,
                exercise = W.saved.HungerIncreaseWhenExercise or d.exercise }
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
                unhappyLast = 0, swipe = nil }
    h.thermo = NR.obj(h.bd, "getThermoregulator")
    if SwipeStatePlayer ~= nil and SwipeStatePlayer.instance ~= nil then
        local ok, sw = pcall(SwipeStatePlayer.instance)    -- the melee swing state: exercise for the satiety rate
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

-- Task 15: the satiety scalar (Decision 2 (c)): seeded 1 - HUNGER on a record without it (a migrated v2) or with a
-- non-finite one, stepped by elapsed world age at the rates saved at boot with the FOOD_EATEN freeze, and read
-- through the energy term. The eats of the minute raised it before this step (NR_Server_Intake).
function W.satiety(h, player, record, eng, inp, es)
    if not NR.finite(record.satiety) then
        record.satiety = K.satiety.seed(inp.hunger)
        W.stats.seeded = W.stats.seeded + 1
    end
    local fed = false
    if MoodleType ~= nil and MoodleType.FOOD_EATEN ~= nil then
        fed = NR.num(h.moodles, "getMoodleLevel", 0, MoodleType.FOOD_EATEN) > 0
    end
    local exercising = (NR.flag(player, "IsRunning") and NR.flag(player, "isPlayerMoving"))
        or (h.swipe ~= nil and NR.flag(player, "isCurrentState", h.swipe))
    local T = CharacterTrait
    local tr = K.satiety.trait(T ~= nil and trait(h, T.HEARTY_APPETITE), T ~= nil and trait(h, T.LIGHT_EATER))
    local rates = W.rates or K.satiety.defaults()
    local rate = K.satiety.rate(rates, inp.asleep, exercising, fed)
    record.satiety = K.satiety.step(record.satiety, K.clamp(inp.dtS, 0, W.c.maxStepS), rate, eng.sd, tr)
    inp.hungerTarget = K.hybrid.hungerTarget(record.satiety, es)
end

function W.step(username, player, record, ctx)
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
    W.satiety(h, player, record, eng, inp, es)
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
