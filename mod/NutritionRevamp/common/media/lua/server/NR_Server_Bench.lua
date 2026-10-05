-- NR_Server_Bench.lua -- the cost-budget entry point (spec § 6, Plan 2 entry gate).
-- bench.global calls a resolved global N times with no arguments; the fast kernel step needs a
-- fully filled input and output, so this file owns one filled input, one output and the constants,
-- builds them once at file scope, and runs NutritionRevamp.kernel.fast.step once per call. The
-- tables are reused, never re-allocated, so bench.global measures the step and not a constructor.
-- This file exists only for the § 6 cost reading and ships with the mod. It is not a kernel file:
-- it names no NutritionRevamp.kernel function. It names no Java global -- at file scope or in its
-- functions -- so it loads with no engine (it only reads NutritionRevamp.kernel, loaded before it).
local NR = NutritionRevamp
local K = NR.kernel

-- Built once: the constants, one output and one input filled to a steady-state awake tick.
local BENCH_C = K.fast.defaults()
local BENCH_OUT = K.fast.output()
local BENCH_INP = K.fast.input()

-- A steady-state awake update: one game-minute (M = 1, D = 24 -> sixty game-seconds), not asleep,
-- not a ghost, mid-range stats, every optional multiplier neutral, a real day length and a mid
-- fitness level. Every trait and flag K.fast.input() seeds false stays false.
BENCH_INP.M = 1
BENCH_INP.D = 24
BENCH_INP.sd = 1
BENCH_INP.asleep = false
BENCH_INP.ghost = false
BENCH_INP.hunger = 0.3
BENCH_INP.thirst = 0.3
BENCH_INP.fatigue = 0.2
BENCH_INP.endurance = 1
BENCH_INP.stress = 0
BENCH_INP.anger = 0
BENCH_INP.idleness = 0
BENCH_INP.morale = 1
BENCH_INP.nicotine = 0
BENCH_INP.thermoFatigue = 1
BENCH_INP.thermoFluids = 1
BENCH_INP.endRegen = 1
BENCH_INP.recoveryMod = 1
BENCH_INP.bedFactor = 1
BENCH_INP.minutesPerDay = 60
BENCH_INP.fitnessLevel = 5

-- One fast step over the reused tables; returns the output table. The target of bench.global.
function NR.bench_fast()
    K.fast.step(BENCH_INP, BENCH_OUT, BENCH_C)
    return BENCH_OUT
end

-- The filled input, for a test to read the steady-state tick it benchmarks.
function NR.bench_fast_input()
    return BENCH_INP
end
