r"""The golden trace of 1.0.0 (Plan 10 Task R0, ruling 3; fix round 1): the refactor's oracle.

run(host) drives six stand-in players g1..g6 through 240 slow minutes on server_host.Host, fully deterministic:
ZombRandFloat (the only random global the mod's Lua calls; `grep -rn 'ZombRand\|math.random' mod/` finds it in
NR_Server_Effects, NR_Server_Metabolism and NR_Server_Nutrients) and ZombRand are a seeded Park-Miller generator
in the env, and getTimestampMs stays absent (the bus's push gap is then the slow minute itself).

The stand-in player is server_host's PLAYER (untouched) under this file's decorator (DECORATE): a body-damage
object whose thermoregulator answers a per-player metabolic rate (the class's engine MET times the engine's load
factor, which the adapter divides out), body parts with wound, bleeding, infection and fracture fields, a
catch-a-cold value and the regeneration and health setters, all counting; isAsleep (g6, minutes 40-90),
isPlayerMoving (g2, minutes 20-60), the inventory and max weight, the max-weight delta, getFitness, isCurrentState,
getMoodles, isFemale (g5), a trait collection, the Strength perk level, its XP and setPerkLevelDebug, and getStats
(Plan 11e Task 1, ruling 11e-3: a stats object starting at STAT_START, so the writer's W.step runs every minute).
The globals beside it: CharacterStat, CharacterTrait (17 sentinels), Perks.Strength with the 75 L (L + 1) ladder,
MoodleType, BodyPartType, sendSyncPlayerFields and syncBodyPart counting, and getSandboxOptions (StatsDecrease 1). A
small engine step (NR_T.engine) runs before each minute: wound timers fall, an infection and a catch-a-cold rise.

Each minute m = 1..240: world age START_AGE + m/60 (118.5 -> 122.5: minute 90 closes a day); the engine step; the
minute's events; every EveryOneMinute listener (h.minute()), then 25 OnTick frames (h.tick(25)); a snapshot per 30.
Events: meals at minutes 10, 70 and 130 (NR_T.meals) through IN.readAfterAndLand (so IN.assemble), one per round
(g4's Steak at 10, g1's dish at 70, g3's at 130) first through IN.readBefore over a stand-in Food (NR_T.food); the
rest over a fixed before-snapshot. Minute 70 is a round of second bites (frac, the share of what was left, differs
from share, the share of the whole): g1's dish (K.vector.dish, extraTypes), g2's Bread, g4's butchered Steak
(instBase -0.36 over the script's -0.30), g5's craft Sandwich, g6's thirst-only tea (a declared vector, thirst over
scriptThirst). The dish and craft inputs instance through an instanceItem global (NR_T.types, so IN.typeInfo and
IN.foodInfo run, a first-sight type each round: table, inferred and declared inputs). g3's minute-130 item answers
NaN for its carbohydrates: Intake's num keeps it and the landing guard rejects the vector (intake.failures). g1's
sleep debt set to DEBT_G1 at minute 20; g6's macro stores raised by an external writer at minute 45 (reconciled);
Wine for g1 and Tea for g5 at minute 50, 0.25 L of water for g2 at 60 (K.vector.fluid, IN.land); g3 dies at minute
100 and at 101 OnNewGame fires for a new g3 object; a NaN written into g2's body (at, inDay) at minute 115 (the
heal); g4 departs at 150 and returns as a new object at 180; at 200 the bus answers one "mirror.request" by g5.
Writer guards (11e T1 fix 1): NaN into satiety S (g2, 80), t (g4, 120) and P (g5, 140); g1's P overflows (170).
A snapshot: every player's full store record, the stand-in player's own state (traits, perk, carry delta, the
body-damage counters and parts, the Nutrition stores, `written`: the writer's last set value per stat, `statSets`),
the counters of a FIXED list of NR.server adapters (STATS_NAMES; a new module's stats never move the trace), the
sendServerCommand counts by command name, the sync and instanceItem counts; printed lines are counted, never kept.

serialize(trace) is deterministic JSON: keys sorted, one value per line, every number written "%.17g" (a
non-finite one as a quoted string), a table key that is a number written the same way.

    python testing/tests/kernel/golden_trace.py --write    records golden/trace-1.0.0.json (from the 1.0.0 mod/
                                                           tree only: ruling 3)
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lupa.lua51 as lua51  # noqa: E402

import server_host  # noqa: E402

GOLDEN = os.path.join(HERE, "golden", "trace-1.0.0.json")
SEED = 20261007
START_AGE = 118.5
MINUTES = 240
TICKS = 25
SNAPSHOT_EVERY = 30
MEAL_MINUTES = (10, 70, 130)
NAMES = ("g1", "g2", "g3", "g4", "g5", "g6")

# The adapters whose stats tables are traced, by name (bus.effects is NR.server.bus.effects.stats). Fixed: a
# module added by the refactor (NR.server.minute) never enters the trace. "writer" joins in Plan 11e Task 1 fix 1: its
# guarded and seeded counters are the only trace of a guard that heals a field the kernel heals again.
STATS_NAMES = ("bus.effects", "effects", "fast", "intake", "kinetics", "metabolism", "nutrients", "reconcile",
               "store", "strength", "training", "weight", "writer")

# Starting macros (calories, carbs, lipids, proteins), distinct per player.
MACROS = {
    "g1": (1000.0, 100.0, 40.0, 60.0),
    "g2": (1500.0, 180.0, 55.0, 75.0),
    "g3": (600.0, 60.0, 25.0, 40.0),
    "g4": (2200.0, 250.0, 90.0, 110.0),
    "g5": (800.0, 120.0, 30.0, 50.0),
    "g6": (1250.0, 140.0, 70.0, 95.0),
}
RESPAWN_G3 = (900.0, 110.0, 35.0, 55.0)
RETURN_G4 = (1700.0, 200.0, 70.0, 90.0)

DRINK_LITRES = 0.25
STORE_RAISE_G6 = (300.0, 40.0, 10.0, 12.0)      # minute 45: another writer's eat, the four stores raised
# minute 20: synthetic state (ruling T1-1), written straight to g1's record.acute.debtH, not booked through
# K.acute.sleepMinute: no 24 h close falls in the trace's 4 h, so the writer's sleep factor (above 1 at half of
# K.satiety.SLEEP_DEBT_FULL_H) is reached only this way
DEBT_G1 = 1.0
# minutes 80, 120, 140, 170: the writer's satiety guards (W.satiety, W.satietyDtH). A NaN S (g2), t (g4) and P (g5)
# is healed in the step before any snapshot reads it (L is healed by Metabolism first, so no guard there). At 170
# g1 gets a P of GUARD_P_G1 and one StatsDecrease read of GUARD_SD, so the decay overflows to inf (exp of +0.58 or
# more) and the P restore (s.P = P0) catches it
GUARD_S_MINUTE, GUARD_T_MINUTE, GUARD_P_MINUTE, GUARD_RESTORE_MINUTE = 80, 120, 140, 170
GUARD_P_G1 = 1e308
GUARD_SD = -50.0

# The env addendum: the generator, the command and sync counters, the globals, the decorator, the engine step
# and the fixed meal snapshots.
ENV = r"""
NR_T.rng = %d
NR_T.sent = {}
NR_T.syncs = { players = {}, parts = {} }
NR_T.m = 0
NR_T.bodies = {}
local function nextU()
    NR_T.rng = math.fmod(16807 * NR_T.rng, 2147483647)
    return NR_T.rng / 2147483647
end
ZombRandFloat = function(lo, hi) return lo + (hi - lo) * nextU() end
ZombRand = function(a, b)
    if b == nil then return math.floor(a * nextU()) end
    return a + math.floor((b - a) * nextU())
end
sendServerCommand = function(player, module, command, args)
    local k = tostring(command)
    NR_T.sent[k] = (NR_T.sent[k] or 0) + 1
end
sendSyncPlayerFields = function(player, mask)
    local k = tostring(player:getUsername()) .. ":" .. tostring(mask)
    NR_T.syncs.players[k] = (NR_T.syncs.players[k] or 0) + 1
end
getSandboxOptions = function()
    return { getStatsDecreaseMultiplier = function(s)
        local v = NR_T.sdOnce
        NR_T.sdOnce = nil
        if v ~= nil then return v end
        return 1
    end }
end
syncBodyPart = function(part, mask)
    local k = tostring(part.st.name) .. ":" .. tostring(mask)
    NR_T.syncs.parts[k] = (NR_T.syncs.parts[k] or 0) + 1
end

CharacterStat = {}
for _, n in ipairs({ "HUNGER", "THIRST", "FATIGUE", "ENDURANCE", "STRESS", "UNHAPPINESS", "FOOD_SICKNESS", "PANIC",
                     "TEMPERATURE", "INTOXICATION" }) do
    CharacterStat[n] = n
end
CharacterTrait = {}
for _, n in ipairs({ "ATHLETIC", "FIT", "OUT_OF_SHAPE", "UNFIT", "STRONG", "STOUT", "WEAK", "FEEBLE",
                     "NEEDS_MORE_SLEEP", "NEEDS_LESS_SLEEP", "NIGHT_VISION", "SHORT_SIGHTED",
                     "OBESE", "OVERWEIGHT", "UNDERWEIGHT", "VERY_UNDERWEIGHT", "EMACIATED" }) do
    CharacterTrait[n] = "trait:" .. n
end
Perks = { Strength = { name = "Strength" } }
Perks.Strength.getTotalXpForLevel = function(s, L) return 75 * L * (L + 1) end
MoodleType = { HEAVY_LOAD = "moodle:HEAVY_LOAD", HYPERTHERMIA = "moodle:HYPERTHERMIA" }
BodyPartType = {}
NR_T.PARTS = { "Hand_L", "Hand_R", "UpperLeg_L", "UpperLeg_R", "LowerLeg_L", "LowerLeg_R" }
for _, n in ipairs(NR_T.PARTS) do BodyPartType[n] = "part:" .. n end

local WOUND_FIELDS = { "scratch", "cut", "deep", "bite", "burn", "fracture" }
local GETSET = { scratch = "ScratchTime", cut = "CutTime", deep = "DeepWoundTime", bite = "BiteTime",
                 burn = "BurnTime", fracture = "FractureTime", bleed = "BleedingTime",
                 infect = "WoundInfectionLevel" }

local function newPart(name, init)
    local st = { name = name, scratch = 0, cut = 0, deep = 0, bite = 0, burn = 0, fracture = 0, bleed = 0,
                 infect = 0, splint = false, writes = 0 }
    for k, v in pairs(init or {}) do st[k] = v end
    local part = { st = st }
    for field, suffix in pairs(GETSET) do
        part["get" .. suffix] = function(s) return s.st[field] end
        part["set" .. suffix] = function(s, v) s.st[field] = v; s.st.writes = s.st.writes + 1 end
    end
    part.isSplint = function(s) return s.st.splint end
    return part
end

-- The decorator: cfg = { cls, rate, inv, maxW, female, traits = {names}, heavy, asleep = {from, to},
-- moving = {from, to}, parts = { name = {field = value} }, cold, coldRise, hunger, thirst, fatigue }.
NR_T.decorate = function(p, cfg)
    local st = { traits = {}, perk = 5, xp = 260, delta = 1.0, perkWrites = 0, deltaWrites = 0 }
    for _, n in ipairs(cfg.traits or {}) do st.traits[CharacterTrait[n]] = true end
    p.st = st
    local thermo = {}
    local f = math.min(math.max(cfg.inv / cfg.maxW, 0), 1)
    local rate = cfg.rate * (1 + 0.35 * f * f)
    thermo.getMetabolicRate = function(s) return rate end
    thermo.getEnergyMultiplier = function(s) return 1.0 end
    thermo.getFluidsMultiplier = function(s) return 1.0 end
    thermo.getSetPoint = function(s) return 37.0 end
    local bst = { std = 0.002, red = 0.0013, sev = 0.0008, slp = 0.02, regenSets = 0, reduced = 0,
                  reduceCalls = 0, added = 0, cold = cfg.cold or 0, coldRise = cfg.coldRise or 0, coldSets = 0 }
    st.body = bst
    local parts, byType = {}, {}
    for i, n in ipairs(NR_T.PARTS) do
        local part = newPart(n, cfg.parts and cfg.parts[n])
        parts[i] = part
        byType[BodyPartType[n]] = part
    end
    st.parts = {}
    for i, part in ipairs(parts) do st.parts[part.st.name] = part.st end
    local list = { size = function(s) return #parts end, get = function(s, i) return parts[i + 1] end }
    local bd = { st = bst }
    bd.getThermoregulator = function(s) return thermo end
    bd.getBodyPart = function(s, t) return byType[t] end
    bd.getBodyParts = function(s) return list end
    bd.getCatchACold = function(s) return s.st.cold end
    bd.setCatchACold = function(s, v) s.st.cold = v; s.st.coldSets = s.st.coldSets + 1 end
    bd.setStandardHealthAddition = function(s, v) s.st.std = v; s.st.regenSets = s.st.regenSets + 1 end
    bd.setReducedHealthAddition = function(s, v) s.st.red = v; s.st.regenSets = s.st.regenSets + 1 end
    bd.setSeverlyReducedHealthAddition = function(s, v) s.st.sev = v; s.st.regenSets = s.st.regenSets + 1 end
    bd.setSleepingHealthAddition = function(s, v) s.st.slp = v; s.st.regenSets = s.st.regenSets + 1 end
    bd.ReduceGeneralHealth = function(s, v) s.st.reduced = s.st.reduced + v; s.st.reduceCalls = s.st.reduceCalls + 1 end
    bd.AddGeneralHealth = function(s, v) s.st.added = s.st.added + v end
    NR_T.bodies[#NR_T.bodies + 1] = bd
    bd.parts = parts
    p.getBodyDamage = function(s) return bd end
    p.isAsleep = function(s)
        return cfg.asleep ~= nil and NR_T.m >= cfg.asleep[1] and NR_T.m <= cfg.asleep[2]
    end
    p.isPlayerMoving = function(s)
        return cfg.moving ~= nil and NR_T.m >= cfg.moving[1] and NR_T.m <= cfg.moving[2]
    end
    p.getInventoryWeight = function(s) return cfg.inv end
    p.getMaxWeight = function(s) return cfg.maxW end
    p.getMaxWeightDelta = function(s) return s.st.delta end
    p.setMaxWeightDelta = function(s, v) s.st.delta = v; s.st.deltaWrites = s.st.deltaWrites + 1 end
    local fitness = { getCurrentExe = function(s) return nil end }
    p.getFitness = function(s) return fitness end
    p.isCurrentState = function(s, state) return false end
    local moodles = { getMoodleLevel = function(s, t)
        if t == MoodleType.HEAVY_LOAD then return cfg.heavy or 0 end
        return 0
    end }
    p.getMoodles = function(s) return moodles end
    p.isFemale = function(s) return cfg.female == true end
    local coll = {}
    coll.get = function(c, t) return st.traits[t] == true end
    coll.add = function(c, t) st.traits[t] = true end
    coll.remove = function(c, t) st.traits[t] = nil end
    p.getCharacterTraits = function(s) return coll end
    p.getPerkLevel = function(s, perk) if perk == Perks.Strength then return s.st.perk end return 0 end
    local xp = { getXP = function(x, perk) if perk == Perks.Strength then return st.xp end return 0 end }
    p.getXp = function(s) return xp end
    p.setPerkLevelDebug = function(s, perk, level)
        if perk == Perks.Strength then s.st.perk = level; s.st.perkWrites = s.st.perkWrites + 1 end
    end
    -- the stats object (Plan 11e Task 1, ruling 11e-3): get answers the current value, set records it as written
    local sv = { HUNGER = cfg.hunger, THIRST = cfg.thirst, FATIGUE = cfg.fatigue, ENDURANCE = 1.0, STRESS = 0,
                 UNHAPPINESS = 0, FOOD_SICKNESS = 0, PANIC = 0, TEMPERATURE = 37.0, INTOXICATION = 0 }
    local wst = { written = {}, sets = 0 }
    p.wst = wst
    local stats = {}
    stats.get = function(s, k) return sv[k] end
    stats.set = function(s, k, v) sv[k] = v; wst.written[k] = v; wst.sets = wst.sets + 1 end
    p.getStats = function(s) return stats end
    return p
end

-- The engine's own minute on every decorated body: wound timers fall a game minute's worth, an infection rises,
-- the catch-a-cold value rises by the body's rate.
NR_T.engine = function()
    for _, bd in ipairs(NR_T.bodies) do
        for _, part in ipairs(bd.parts) do
            local s = part.st
            for _, k in ipairs(WOUND_FIELDS) do
                if s[k] > 0 then s[k] = math.max(0, s[k] - 1 / 60) end
            end
            if s.bleed > 0 then s.bleed = math.max(0, s.bleed - 1 / 60) end
            if s.infect > 0 then s.infect = math.min(10, s.infect + 0.01) end
        end
        if bd.st.coldRise > 0 then bd.st.cold = bd.st.cold + bd.st.coldRise end
    end
end

-- The meals, by minute and player. A `via = "item"` meal goes through IN.readBefore over a stand-in Food (NR_T.food)
-- and then IN.readAfterAndLand; every other meal is a fixed before-snapshot (IN.readBefore's shape) handed to
-- IN.readAfterAndLand with an item stub that answers only the after readings. A second bite (minute 70: g1's dish,
-- g2's Bread, g4's Steak, g5's Sandwich, g6's tea) reads rawBefore (or thirstBefore) below the whole instance's
-- instBase (or scriptThirst), so frac (the share of what was left) and share (the share of the whole) differ. g4's
-- Steak is butchered: instBase -0.36 against the script's -0.30 (the hunger ratio 1.2), its live macros at that
-- scale. The minute-130 item meal answers NaN for its carbohydrates: Intake's local num keeps it, the macros carry
-- it and the landing guard rejects the vector (intake.failures).
NR_T.meals = {
    [10] = {
        g1 = { fullType = "Base.Salad", rawBefore = -0.20, rawAfter = -0.10, instBase = -0.20, thirstBefore = 0,
               thirstAfter = 0, cal = 80, carb = 12, lip = 4, pro = 3, scriptHunger = -0.20, scriptThirst = 0,
               extraTypes = { "Base.Lettuce", "Base.Tomato", "NRTrace.Crouton" } },
        g2 = { fullType = "Base.Bread", rawBefore = -0.30, rawAfter = -0.15, instBase = -0.30, thirstBefore = 0,
               thirstAfter = 0, cal = 532, carb = 99, lip = 6.66, pro = 17.7, scriptHunger = -0.30, scriptThirst = 0,
               foodType = "Bread" },
        g3 = { fullType = "NRTrace.TrailMix", rawBefore = -0.20, rawAfter = 0, instBase = -0.20, thirstBefore = 0,
               thirstAfter = 0, cal = 300, carb = 30, lip = 18, pro = 9, scriptHunger = -0.20, scriptThirst = 0,
               foodType = "Seed" },
        g4 = { via = "item", fullType = "Base.Steak", hungBefore = -0.36, hungAfter = -0.18, baseHunger = -0.36,
               thirstBefore = 0, thirstAfter = 0, cal = 264, carb = 0, lip = 11.22, pro = 37.944,
               scriptHungerPts = -30, scriptThirstPts = 0, foodType = "Beef", cooked = true, burnt = true,
               modData = {} },
        g5 = { fullType = "Base.Sandwich", rawBefore = -0.10, rawAfter = -0.05, instBase = -0.10, thirstBefore = 0,
               thirstAfter = 0, cal = 360, carb = 42, lip = 8.5, pro = 5.8, scriptHunger = -0.10, scriptThirst = 0,
               craftMap = { ["Base.Bread"] = 1, ["Base.Cheese"] = 2 } },
        g6 = { fullType = "Base.HotDrinkTea", rawBefore = 0, rawAfter = 0, instBase = 0, thirstBefore = -0.20,
               thirstAfter = -0.10, cal = 4, carb = 1, lip = 0, pro = 0, scriptHunger = 0, scriptThirst = -0.20,
               declared = "water:237;caffeine:47;potassium:88;folate:12" },
    },
    [70] = {
        g1 = { via = "item", fullType = "Base.Salad", hungBefore = -0.10, hungAfter = 0, baseHunger = -0.20,
               thirstBefore = 0, thirstAfter = 0, cal = 40, carb = 6, lip = 2, pro = 1.5, scriptHungerPts = -20,
               scriptThirstPts = 0, extra = { "Base.Lettuce", "Base.Tomato", "NRTrace.Crouton" }, modData = {} },
        g2 = { fullType = "Base.Bread", rawBefore = -0.15, rawAfter = 0, instBase = -0.30, thirstBefore = 0,
               thirstAfter = 0, cal = 266, carb = 49.5, lip = 3.33, pro = 8.85, scriptHunger = -0.30,
               scriptThirst = 0, foodType = "Bread" },
        g3 = { fullType = "NRTrace.Stew", rawBefore = -0.25, rawAfter = 0, instBase = -0.25, thirstBefore = 0,
               thirstAfter = 0, cal = 210, carb = 24, lip = 7, pro = 12, scriptHunger = -0.25, scriptThirst = 0,
               extraTypes = { "Base.Carrots", "Base.Cabbage", "NRTrace.Dressing" } },
        g4 = { fullType = "Base.Steak", rawBefore = -0.18, rawAfter = 0, instBase = -0.36, thirstBefore = 0,
               thirstAfter = 0, cal = 132, carb = 0, lip = 5.61, pro = 18.972, scriptHunger = -0.30, scriptThirst = 0,
               foodType = "Beef", cooked = true, burnt = true },
        g5 = { fullType = "Base.Sandwich", rawBefore = -0.05, rawAfter = -0.02, instBase = -0.10, thirstBefore = 0,
               thirstAfter = 0, cal = 180, carb = 21, lip = 4.25, pro = 2.9, scriptHunger = -0.10, scriptThirst = 0,
               craftMap = { ["Base.Bread"] = 1, ["Base.Cheese"] = 2 } },
        g6 = { fullType = "Base.HotDrinkTea", rawBefore = 0, rawAfter = 0, instBase = 0, thirstBefore = -0.10,
               thirstAfter = 0, cal = 2, carb = 0.5, lip = 0, pro = 0, scriptHunger = 0, scriptThirst = -0.20,
               declared = "water:237;caffeine:47;potassium:88;folate:12" },
    },
    [130] = {
        g1 = { fullType = "Base.Apple", rawBefore = -0.16, rawAfter = 0, instBase = -0.16, thirstBefore = -0.07,
               thirstAfter = 0, cal = 95, carb = 25.13, lip = 0.31, pro = 0.47, scriptHunger = -0.16,
               scriptThirst = -0.07, foodType = "Fruits" },
        g2 = { fullType = "Base.Bread", rawBefore = -0.30, rawAfter = -0.20, instBase = -0.30, thirstBefore = 0,
               thirstAfter = 0, cal = 532, carb = 99, lip = 6.66, pro = 17.7, scriptHunger = -0.30, scriptThirst = 0,
               foodType = "Bread" },
        g3 = { via = "item", fullType = "NRTrace.TrailMix", hungBefore = -0.20, hungAfter = 0, baseHunger = -0.20,
               thirstBefore = 0, thirstAfter = 0, cal = 300, carb = 0, lip = 18, pro = 9, scriptHungerPts = -20,
               scriptThirstPts = 0, foodType = "Seed", modData = {}, nan = "getCarbohydrates" },
        g4 = { fullType = "Base.Steak", rawBefore = -0.36, rawAfter = 0, instBase = -0.36, thirstBefore = 0,
               thirstAfter = 0, cal = 264, carb = 0, lip = 11.22, pro = 37.944, scriptHunger = -0.30,
               scriptThirst = 0, foodType = "Beef", cooked = true },
        g5 = { fullType = "Base.Sandwich", rawBefore = -0.10, rawAfter = 0, instBase = -0.10, thirstBefore = 0,
               thirstAfter = 0, cal = 330, carb = 40, lip = 7.5, pro = 6.2, scriptHunger = -0.10, scriptThirst = 0,
               craftMap = { ["Base.Bread"] = 1, ["Base.Cheese"] = 1, ["NRTrace.Pickle"] = 1 } },
        g6 = { fullType = "Base.HotDrinkTea", rawBefore = 0, rawAfter = 0, instBase = 0, thirstBefore = -0.20,
               thirstAfter = -0.05, cal = 4, carb = 1, lip = 0, pro = 0, scriptHunger = 0, scriptThirst = -0.20,
               declared = "water:237;caffeine:47;potassium:88;folate:12" },
    },
}

-- The input types a dish or a craft names, as instanceItem builds them (IN.typeInfo -> IN.foodInfo): three in
-- the table, two inferred (no table entry, the chain reads foodInfo's macros and FoodType) and one declared
-- (an NR_Nutrients string in its modData). A type absent here instances to nil (IN.typeInfo caches false).
NR_T.types = {
    ["Base.Bread"] = { cal = 532, carb = 99, lip = 6.66, pro = 17.7, foodType = "Bread" },
    ["Base.Cheese"] = { cal = 113, carb = 0.4, lip = 9.3, pro = 7, foodType = "Cheese" },
    ["Base.Lettuce"] = { cal = 20, carb = 3.9, lip = 0.2, pro = 1.8, foodType = "Vegetables" },
    ["Base.Tomato"] = { cal = 16.38, carb = 3.54, lip = 0.18, pro = 0.8, foodType = "Vegetables" },
    ["Base.Carrots"] = { cal = 41, carb = 9.6, lip = 0.24, pro = 0.93, foodType = "Vegetables" },
    ["NRTrace.Crouton"] = { cal = 60, carb = 11, lip = 1, pro = 2, foodType = "Bread" },
    ["NRTrace.Pickle"] = { cal = 12, carb = 2.6, lip = 0.1, pro = 0.3, foodType = "Vegetables" },
    ["NRTrace.Dressing"] = { cal = 90, carb = 1, lip = 9.5, pro = 0.2,
                             modData = { NR_Nutrients = "vitE:2.1;vitK:24;sodium:310;efa:4.6" } },
}
NR_T.instanced = {}

-- A stand-in Food: the getters IN.readBefore and IN.foodInfo read. The hunger and thirst getters answer the
-- before value until NR_T.eat marks the item eaten, then the after value. `nan` names one getter that answers NaN.
NR_T.food = function(fullType, spec)
    local item = { eaten = false }
    local function pick(b, a) if item.eaten then return a end return b end
    item.getFullType = function(s) return fullType end
    item.getHungChange = function(s) return pick(spec.hungBefore or 0, spec.hungAfter or 0) end
    item.getThirstChangeUnmodified = function(s) return pick(spec.thirstBefore or 0, spec.thirstAfter or 0) end
    item.getBaseHunger = function(s) return spec.baseHunger or 0 end
    item.getCalories = function(s) return spec.cal end
    item.getCarbohydrates = function(s) return spec.carb end
    item.getLipids = function(s) return spec.lip end
    item.getProteins = function(s) return spec.pro end
    if spec.nan ~= nil then item[spec.nan] = function(s) return 0 / 0 end end
    item.isCooked = function(s) return spec.cooked == true end
    item.isBurnt = function(s) return spec.burnt == true end
    item.isRotten = function(s) return false end
    item.isFrozen = function(s) return false end
    local script = { getHungerChange = function(s) return spec.scriptHungerPts or 0 end,
                     getThirstChange = function(s) return spec.scriptThirstPts or 0 end }
    item.getScriptItem = function(s) return script end
    local extra = spec.extra or {}
    local list = { size = function(s) return #extra end, get = function(s, i) return extra[i + 1] end }
    item.haveExtraItems = function(s) return #extra > 0 end
    item.getExtraItems = function(s) return list end
    local md = spec.modData or {}
    item.getModData = function(s) return md end
    item.getFoodType = function(s) return spec.foodType end
    return item
end

instanceItem = function(fullType)
    local spec = NR_T.types[fullType]
    if spec == nil then return nil end
    NR_T.instanced[fullType] = (NR_T.instanced[fullType] or 0) + 1
    return NR_T.food(fullType, spec)
end

NR_T.eat = function(minute, username)
    local m = NR_T.meals[minute][username]
    local IN = NutritionRevamp.server.intake
    if m.via == "item" then
        local item = NR_T.food(m.fullType, m)
        local character = { getUsername = function(s) return username end }
        local b = IN.readBefore({ item = item, character = character })
        item.eaten = true
        return IN.readAfterAndLand(b)
    end
    local item = {}
    item.getHungChange = function(s) return m.rawAfter end
    item.getThirstChangeUnmodified = function(s) return m.thirstAfter end
    local b = { item = item, username = username, rawBefore = m.rawBefore, fullType = m.fullType,
                instBase = m.instBase, thirstBefore = m.thirstBefore, cal = m.cal, carb = m.carb, lip = m.lip,
                pro = m.pro, cooked = m.cooked == true, burnt = m.burnt == true, rotten = false, frozen = false,
                scriptHunger = m.scriptHunger, scriptThirst = m.scriptThirst, extraTypes = {},
                craftMap = nil, declared = m.declared, foodType = m.foodType }
    for i, t in ipairs(m.extraTypes or {}) do b.extraTypes[i] = t end
    if m.craftMap ~= nil then
        b.craftMap = {}
        for k, v in pairs(m.craftMap) do b.craftMap[k] = v end
    end
    b.macros = { calories = b.cal, carbs = b.carb, lipids = b.lip, proteins = b.pro }
    return IN.readAfterAndLand(b)
end
""" % SEED

# The decorator's per-player configuration: the activity class (its engine MET is the rate before the load
# factor), the carried and max weight, the traits held at creation, the asleep and moving windows (minutes),
# body parts with wounds, a catch-a-cold rise.
PLAYER_CFG = {
    "g1": {"rate": 1.5, "inv": 6, "maxW": 8, "traits": [], "cold": 0.0, "coldRise": 0.02,
           "parts": {"Hand_L": {"cut": 5.0, "bleed": 2.0}}},
    "g2": {"rate": 3.1, "inv": 6, "maxW": 8, "traits": ["FIT"], "moving": [20, 60],
           "parts": {"Hand_R": {"scratch": 3.0, "infect": 0.5}}},
    "g3": {"rate": 1.0, "inv": 6, "maxW": 8, "traits": ["OUT_OF_SHAPE"],
           "parts": {"UpperLeg_L": {"deep": 8.0}}},
    "g4": {"rate": 6.0, "inv": 12, "maxW": 8, "traits": ["STRONG"], "heavy": 2,
           "parts": {"Hand_L": {"burn": 4.0}}},
    "g5": {"rate": 1.1, "inv": 6, "maxW": 8, "traits": ["NEEDS_MORE_SLEEP"], "female": True,
           "parts": {"LowerLeg_L": {"fracture": 30.0}}},
    "g6": {"rate": 0.8, "inv": 6, "maxW": 8, "traits": ["NEEDS_LESS_SLEEP"], "asleep": [40, 90],
           "parts": {"Hand_R": {"bite": 2.0}}},
}

# The HUNGER, THIRST and FATIGUE each player's stats object starts at (Plan 11e Task 1, ruling 11e-3), distinct per
# player; a respawned or returning player's new object starts at its name's values again.
STAT_START = {
    "g1": (0.15, 0.10, 0.05),
    "g2": (0.30, 0.20, 0.20),
    "g3": (0.05, 0.05, 0.40),
    "g4": (0.45, 0.30, 0.10),
    "g5": (0.20, 0.15, 0.30),
    "g6": (0.10, 0.25, 0.60),
}


def new_host():
    return server_host.Host(extra_env=ENV)


# --- the Lua value walk -------------------------------------------------------------------------------

class _Num:
    __slots__ = ("text",)

    def __init__(self, x):
        x = float(x)
        self.text = ("%.17g" % x) if math.isfinite(x) else json.dumps("%.17g" % x)


def _key(k):
    if isinstance(k, bool):
        return "<bool:%s>" % k
    if isinstance(k, (int, float)):
        return "%.17g" % float(k)
    if isinstance(k, str):
        return k
    if isinstance(k, bytes):
        return k.decode("utf-8")
    return "<%s>" % lua51.lua_type(k)


def walk(v, stack=()):
    """A Lua value as plain Python: a table a dict keyed by strings, a number a _Num."""
    if v is None or isinstance(v, (bool, str)):
        return v
    if isinstance(v, bytes):
        return v.decode("utf-8")
    if isinstance(v, (int, float)):
        return _Num(v)
    t = lua51.lua_type(v)
    if t == "table":
        if any(v is s for s in stack):
            raise ValueError("cycle in a walked table")
        out = {}
        for k, x in v.items():
            ks = _key(k)
            if ks in out:
                raise ValueError("key collision: %r" % ks)
            out[ks] = walk(x, stack + (v,))
        return out
    return "<%s>" % t


def _emit(v, ind, parts):
    if isinstance(v, _Num):
        parts.append(v.text)
    elif v is None or isinstance(v, (bool, str)):
        parts.append(json.dumps(v))
    elif isinstance(v, (int, float)):
        parts.append(_Num(v).text)
    elif isinstance(v, list):
        if not v:
            parts.append("[]")
            return
        parts.append("[\n")
        for i, x in enumerate(v):
            parts.append(" " * (ind + 1))
            _emit(x, ind + 1, parts)
            parts.append(",\n" if i < len(v) - 1 else "\n")
        parts.append(" " * ind + "]")
    elif isinstance(v, dict):
        if not v:
            parts.append("{}")
            return
        parts.append("{\n")
        keys = sorted(v)
        for i, k in enumerate(keys):
            parts.append(" " * (ind + 1) + json.dumps(k) + ": ")
            _emit(v[k], ind + 1, parts)
            parts.append(",\n" if i < len(keys) - 1 else "\n")
        parts.append(" " * ind + "}")
    else:
        raise TypeError("unserialisable: %r" % (v,))


def serialize(trace):
    parts = []
    _emit(trace, 0, parts)
    parts.append("\n")
    return "".join(parts)


# --- the scenario --------------------------------------------------------------------------------------

def _stats(h):
    srv = h.NR.server
    out = {}
    for name in STATS_NAMES:
        if name == "bus.effects":
            bus = srv["bus"]
            st = bus["effects"]["stats"] if bus is not None and bus["effects"] is not None else None
        else:
            mod = srv[name]
            st = mod["stats"] if lua51.lua_type(mod) == "table" else None
        out[name] = walk(st) if lua51.lua_type(st) == "table" else None
    return out


def _player_state(p):
    nut = p.nut
    return {
        "st": walk(p.st),
        "nutrition": {k: walk(nut[k]) for k in ("cal", "carb", "lip", "pro", "weight", "sets", "traitApplies")},
        "written": walk(p.wst.written),
        "statSets": _Num(p.wst.sets),
    }


def _snapshot(h, minute, players):
    recs = h.NR.server.store.records
    return {
        "minute": minute,
        "age": _Num(h.T.age),
        "records": {n: walk(recs[n]) for n in NAMES},
        "players": {n: _player_state(players[n]) for n in NAMES},
        "stats": _stats(h),
        "sent": walk(h.T.sent),
        "syncs": walk(h.T.syncs),
        "instanced": walk(h.T.instanced),
    }


def _new_player(h, name, macros):
    p = h.player(name, *macros)
    cfg = dict(PLAYER_CFG[name])
    cfg["hunger"], cfg["thirst"], cfg["fatigue"] = STAT_START[name]
    lcfg = h.rt.table()
    for k, v in cfg.items():
        if isinstance(v, list):
            lcfg[k] = h.rt.table(*v)
        elif isinstance(v, dict):
            parts = h.rt.table()
            for pn, fields in v.items():
                parts[pn] = h.rt.table_from(fields)
            lcfg[k] = parts
        else:
            lcfg[k] = v
    return h.T.decorate(p, lcfg)


def _meal(h, minute, name):
    rec = h.record(name)
    if rec is None or rec["stomach"] is None:
        raise AssertionError("no record or stomach for %s at a meal" % name)
    h.T.eat(minute, name)


def _fluid(h, name, fluid, litres):
    rec = h.record(name)
    if rec is None or rec["stomach"] is None:
        raise AssertionError("no record or stomach for %s at a drink" % name)
    src = h.NR.data.fluids.get(fluid)
    if src is None:
        raise AssertionError("no fluid entry for %s" % fluid)
    h.NR.server.intake.land(rec, name, h.K.vector.fluid(src, litres))


def run(host):
    h = host
    players = {n: _new_player(h, n, MACROS[n]) for n in NAMES}
    order = list(NAMES)

    def publish():
        h.online(*[players[n] for n in order])

    publish()
    h.T.age = START_AGE
    snapshots = []
    for m in range(1, MINUTES + 1):
        h.T.age = START_AGE + m / 60.0
        h.T.m = m
        h.T.engine()
        if m in MEAL_MINUTES:
            for n in order:
                _meal(h, m, n)
        if m == 20:
            h.record("g1")["acute"]["debtH"] = DEBT_G1
        if m == GUARD_S_MINUTE:
            h.record("g2")["satiety"]["S"] = float("nan")
        if m == GUARD_T_MINUTE:
            h.record("g4")["satiety"]["t"] = float("nan")
        if m == GUARD_P_MINUTE:
            h.record("g5")["satiety"]["P"] = float("nan")
        if m == GUARD_RESTORE_MINUTE:
            h.record("g1")["satiety"]["P"] = GUARD_P_G1
            h.T.sdOnce = GUARD_SD
        if m == 45:
            nut = players["g6"].nut
            nut.cal = nut.cal + STORE_RAISE_G6[0]
            nut.carb = nut.carb + STORE_RAISE_G6[1]
            nut.lip = nut.lip + STORE_RAISE_G6[2]
            nut.pro = nut.pro + STORE_RAISE_G6[3]
        if m == 50:
            _fluid(h, "g1", "Wine", DRINK_LITRES)
            _fluid(h, "g5", "Tea", DRINK_LITRES)
        if m == 60:
            _fluid(h, "g2", "Water", DRINK_LITRES)
        if m == 100:
            players["g3"].deadFlag = True
        if m == 101:
            players["g3"] = _new_player(h, "g3", RESPAWN_G3)
            publish()
            h.fire("OnNewGame", players["g3"], None)
        if m == 115:
            body = h.record("g2")["body"]
            body["at"] = float("nan")
            body["inDay"] = float("nan")
        if m == 150:
            order.remove("g4")
            publish()
        if m == 180:
            players["g4"] = _new_player(h, "g4", RETURN_G4)
            order.insert(3, "g4")
            publish()
        if m == 200:
            h.fire("OnClientCommand", "NutritionRevamp", "mirror.request", players["g5"], None)
        h.minute()
        h.tick(TICKS)
        if m % SNAPSHOT_EVERY == 0:
            snapshots.append(_snapshot(h, m, players))
    return {"snapshots": snapshots, "printed_count": len(h.printed())}


def main(argv):
    text = serialize(run(new_host()))
    if "--write" in argv:
        os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
        with open(GOLDEN, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("wrote %s (%d bytes)" % (GOLDEN, len(text.encode("utf-8"))))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
