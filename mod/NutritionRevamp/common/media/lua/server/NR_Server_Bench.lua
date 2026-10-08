-- NR_Server_Bench.lua -- the cost-budget entry point (spec § 6, Plan 2 entry gate; Plan 11 Task 14: the writer).
-- bench.global calls a resolved global N times with no arguments; the writer's arithmetic needs a fully filled
-- input and output, so this file owns one filled input, one output and the constants, builds them once at file
-- scope, and runs NutritionRevamp.kernel.hybrid.write once per call. The tables are reused, never re-allocated,
-- so bench.global measures the write and not a constructor. This file exists only for the § 6 cost reading and
-- ships with the mod. It is not a kernel file: it defines no NutritionRevamp.kernel function. It names no Java
-- global, so it loads with no engine.
local NR = NutritionRevamp
local K = NR.kernel

-- Built once: the constants, one output and one input filled to a steady awake game minute.
local BENCH_C = K.hybrid.defaults()
local BENCH_OUT = K.hybrid.output()
local BENCH_INP = K.hybrid.input()

BENCH_INP.dtS = 60
BENCH_INP.mode = 1
BENCH_INP.hunger = 0.3
BENCH_INP.hungerTarget = 0.3
BENCH_INP.thirst = 0.3
BENCH_INP.thirstTarget = 0.3
BENCH_INP.lastThirst = 0.3
BENCH_INP.fOwned = true
BENCH_INP.fS = 0.3
BENCH_INP.fCirc = 0.05
BENCH_INP.fOff = 0.02
BENCH_INP.stress = 0.05
BENCH_INP.stressTarget = 0.1
BENCH_INP.panic = 9
BENCH_INP.panicTarget = 10
BENCH_INP.temp = 37.0
BENCH_INP.tempTarget = 37.5
BENCH_INP.tempAdj = 0.5
BENCH_INP.intoxTarget = 0
BENCH_INP.endurance = 1
BENCH_INP.lastEndurance = 1

function NR.bench_writer()
    K.hybrid.write(BENCH_INP, BENCH_OUT, BENCH_C)
    return BENCH_OUT
end

function NR.bench_writer_input()
    return BENCH_INP
end
