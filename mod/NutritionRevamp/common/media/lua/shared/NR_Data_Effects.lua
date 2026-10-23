-- NR_Data_Effects.lua -- not a kernel file: the declarative effects table K.effects.compose folds into record.effects.
-- SURF names each surface's fold (mul | add | max | min | or), identity and clamp; a machine surface is written by its
-- own kernel function and never reset, scaled or clamped by the composer. ROWS are { src, on, at, list }; stim, gated
-- and unless gate a row. gc marks a game-choice magnitude (its comment names the open row); bonus marks the adequacy
-- exceptions the Severity dial never scales. Band rows read at the band's lower edge, so each magnitude is a literal
-- with its arithmetic in the comment; test_data_effects.py recomputes them and enforces a row on every number line.
-- The toxicity, hyponatraemia and refeeding rows target FOOD_SICKNESS, never SICKNESS; POISON ships 0 at every rung.
-- SYMPTOMS is the lethal causes' symptom table, folded every minute by K.effects.symptoms on each cause's progress,
-- not by the composer (docs/superpowers/specs/2026-10-21-symptoms-design.md@program-record-v19).
local NR = NutritionRevamp
NR.data = NR.data or {}

-- The symptom rows every cause shares, read by K.effects.symptoms and never written. 15 is the middle of Pain level 1's
-- band (above 10, at most 20, #2369).
local SYM_PAIN = 15 -- game choice, flat while the cause is active, a placeholder for the researched pang and ache shapes (open S2247)
-- The endurance cap deepens from Endurance level 1 at onset to level 4 at the death point (K.hybrid.capAt re-sizes the
-- caps for the day length). At the 90-minute day the moodle shows level 2 from p 0.307, 3 from p 0.640 and 4 from p 0.956.
local SYM_END = { lever = "endurance", shape = "knots", k = {
    0, 0.73, -- level 1 at onset, under 0.75 (#3926); game choice (open S1176)
    1 / 3, 0.48, -- level 2, under 0.5 (#3926); game choice (open S1176)
    2 / 3, 0.23, -- level 3, under 0.25 (#3926); game choice (open S1176)
    1, 0.08, -- level 4 at the death point, under 0.10 (#3926); game choice (open S1176)
} }
-- The stress floor; in the partial first minute after a write it falls less.
local SYM_STRESS = { lever = "stress", shape = "knots", k = {
    0, 0, -- none at onset; game choice (open S1145)
    0.5, 0.30, -- Stress level 1 (above 0.25, #2369) from p 0.417 on the ramp from (0, 0); game choice (open S1145)
    0.9, 0.55, -- Stress level 2 (above 0.5, #2369) from p 0.82; game choice (open S1145)
    1, 0.55, -- held to the death point; game choice (open S1145)
} }
-- The unhappiness floor, released by the writer's subtraction (#3119).
local SYM_UNHAPPY = { lever = "unhappy", shape = "knots", k = {
    0, 0, -- none at onset; game choice (open S1145)
    0.5, 25, -- Unhappy level 1 (above 20, #2369) from p 0.40 on the ramp from (0, 0); game choice (open S1145)
    0.9, 50, -- Unhappy level 2 (above 45, #2369) from p 0.82; game choice (open S1145)
    1, 50, -- held to the death point; game choice (open S1145)
} }

NR.data.effects = {
    -- The vitamin D rows ship gated off until an outdoor-daylight seat exists (no cutaneous term, open S1064).
    VITD_EFFECTS = false,
    -- The bleeding time a spontaneous bruise starts at (the adapter's event write).
    BRUISE_T0 = 0.05, -- game choice: about 1.79 x damageScaler health per bruise (open S1153)
    SURF = {
        mNut = { op = "mul", id = 1, lo = 1.0, hi = 2.0 }, -- fatigue accrual, nutritional part; game choice clamp above the 1.3 trait span #2271 (open S1133)
        rNut = { op = "mul", id = 1, lo = 0.5, hi = 1.3 }, -- sleep recovery, nutritional part; game choice clamp (open S1133)
        stressTarget = { op = "add", id = 0, lo = 0, hi = 0.50 }, -- STRESS floor; game choice cap at the level-2 step 0.50 #2369 (open S1147)
        unhappyTarget = { op = "add", id = 0, lo = 0, hi = 59 }, -- UNHAPPINESS floor; game choice cap one under the level-3 step 60 #2369 (open S1147)
        panicTarget = { op = "add", id = 0, lo = 0, hi = 64 }, -- PANIC floor; game choice cap one under the level-3 step 65 #2369 (open S1147)
        foodSickTarget = { op = "max", id = 0, lo = 0, hi = 85 }, -- FOOD_SICKNESS floor (T1-1): SICK levels from max(...)/100 #3130, #2369, never 90 or more (the red drain #2356); game choice (open S1165)
        poisonTarget = { op = "max", id = 0, lo = 0, hi = 30 }, -- no row drives it: POISON 0 at every rung; the drain caps at 30 #2358
        healMul = { op = "mul", id = 1, lo = 0.5, hi = 1.0 }, -- wound healing; game choice floor (open S1149)
        bleedMul = { op = "mul", id = 1, lo = 1.0, hi = 1.25 }, -- total bleeding damage; game choice range (open S1152)
        infectMul = { op = "mul", id = 1, lo = 1.0, hi = 2.3 }, -- wound-infection progression; S0954 OR 2.31, as 2.30
        coldMul = { op = "mul", id = 1, lo = 0.5, hi = 3.0 }, -- catchACold rises; game choice clamp under S0993/S0991 (open S1159)
        tempOffset = { op = "add", id = 0, lo = -0.5, hi = 0.3 }, -- core target offset, degrees C; game choice clamp around the -0.2 falls (S1016, open S1161) and the +0.3 rise (open S1160)
        tempHeat = { op = "add", id = 0, lo = 0, hi = 0.3 }, -- the exertion-gated heat side, degrees C; game choice magnitude (open S1160)
        speedMul = { op = "min", id = 1, lo = 0.75, hi = 1.0 }, -- the direct speed write; game choice floor (open S1176)
        rowEndCap = { op = "min", id = 1, lo = 0.73, hi = 1.0, sevMin = 0.5 }, -- the rows' ENDURANCE ceiling, under the writer's enduranceCap; game choice floor at the Overfull row's value, and on at Severity 0.5 or more, off below, never partial (open S1176)
        foodSickStep = { op = "max", id = 0, lo = 0, hi = 85 }, -- a FOOD_SICKNESS level raised at once, not at the floor's pace; game choice (open S1165)
        fOffNut = { op = "add", id = 0, lo = 0, hi = 0.15 }, -- the nutritional fatigue offset; game choice cap so no state alone crosses Tired 1 (open S1132)
        bruise = { op = "max", id = 0, lo = 0, hi = 1 }, -- spontaneous-bruise probability per game minute; a probability, no row needed
        nightVision = { op = "or", id = false, machine = true }, -- K.effects.nvMinute
        shortSighted = { op = "or", id = false, sevMin = 1 }, -- only at Severity 1 or more; game choice gate (open S1143)
    },
    ROWS = {
        -- Fatigue accrual (mNut); energy availability enters as K.effects.eaAccrual. Vitamin D, B12, folate: no row (S0778).
        { src = "iron", on = "grade", at = 3, unless = "anaemia", list = { -- iron depleted without anaemia, S0699
            { ch = "stat", s = "mNut", v = 1.11, row = "S0699", gc = true }, -- 1 + lambda 0.30 x SMD 0.38 = 1.114, as 1.11; S0699, S0775 cross-check; lambda game choice (open S1119)
        } },
        { src = "anaemia", on = "flag", list = {
            { ch = "stat", s = "mNut", v = 1.25, row = "S1120", gc = true }, -- game choice: beyond S0699's non-anaemic trials (open S1120)
        } },
        { src = "dehyd", on = "band", at = 2, list = { -- [1.5, 2) % body mass, S0098/S0099
            { ch = "stat", s = "mNut", v = 1.0875, row = "S0098", gc = true }, -- 1 + 0.30 x d(1.5), d = 0.35 x 0.5/0.6; lambda game choice (open S1119), curve (open S1121)
        } },
        { src = "dehyd", on = "band", at = 3, list = { -- [2, 2.5) %, S0895
            { ch = "stat", s = "mNut", v = 1.1516666666666666, row = "S1121", gc = true }, -- 1 + 0.30 x (0.35 + 0.35 x 0.4/0.9); game choice curve (open S1121)
        } },
        { src = "dehyd", on = "band", at = 4, list = { -- [2.5, 3) %, S0895 (> 2 % subgroup)
            { ch = "stat", s = "mNut", v = 1.21, row = "S0895", gc = true }, -- 1 + 0.30 x 0.70; game choice shape (open S1121)
        } },
        { src = "dehyd", on = "band", at = 5, list = { -- [3, 4) %, S0895
            { ch = "stat", s = "mNut", v = 1.26, row = "S1121", gc = true }, -- 1 + 0.30 x (0.70 + 0.50 x 0.5/1.5); game choice curve (open S1121)
        } },
        { src = "dehyd", on = "band", at = { 6, 8 }, list = { -- 4 % and above, held, S0895
            { ch = "stat", s = "mNut", v = 1.36, row = "S1121", gc = true }, -- 1 + 0.30 x 1.20, held above 4 %; game choice (open S1121)
        } },
        -- Caffeine withdrawal: q = band / 4 = wdQ x cafTol (S0805).
        { src = "wd", on = "band", at = 1, list = { -- q 0.25, S0805
            { ch = "stat", s = "mNut", v = 1.05, row = "S0805", gc = true }, -- 1 + 0.20 x 0.25; game choice 0.20 (open S1122)
            { ch = "stat", s = "unhappyTarget", v = 2.5, row = "S0803", gc = true }, -- 10 x 0.25; game choice 10 (open S1145)
        } },
        { src = "wd", on = "band", at = 2, list = { -- q 0.50, S0805
            { ch = "stat", s = "mNut", v = 1.10, row = "S0805", gc = true }, -- 1 + 0.20 x 0.50; game choice 0.20 (open S1122)
            { ch = "stat", s = "unhappyTarget", v = 5.0, row = "S0803", gc = true }, -- 10 x 0.50; game choice 10 (open S1145)
        } },
        { src = "wd", on = "band", at = 3, list = { -- q 0.75, S0805
            { ch = "stat", s = "mNut", v = 1.15, row = "S0805", gc = true }, -- 1 + 0.20 x 0.75; game choice 0.20 (open S1122)
            { ch = "stat", s = "unhappyTarget", v = 7.5, row = "S0803", gc = true }, -- 10 x 0.75; game choice 10 (open S1145)
        } },
        { src = "wd", on = "band", at = 4, list = { -- q 1, S0805
            { ch = "stat", s = "mNut", v = 1.20, row = "S0805", gc = true }, -- 1 + 0.20 x 1; game choice 0.20 (open S1122)
            { ch = "stat", s = "unhappyTarget", v = 10.0, row = "S0803", gc = true }, -- 10 x 1; game choice 10 (open S1145)
        } },
        -- The hangover, one row per stimulant set: Game (1, the default) halves Realistic's sizes. Both carry an unhappiness
        -- floor (S0930's negative affect).
        { src = "hang", on = "band", at = 1, stim = 2, list = { -- the hangover flag, S0814/S0817/S0930
            { ch = "stat", s = "mNut", v = 1.15, row = "S0814", gc = true }, -- S0814 g 0.66 / S0817 g 0.47 via lambda; game choice (open S1127)
            { ch = "stat", s = "stressTarget", v = 0.10, row = "S0930", gc = true }, -- direction only, no pooled size (open S0943); game choice magnitude (open S1145)
            { ch = "stat", s = "unhappyTarget", v = 42, row = "S0930", gc = true }, -- twice Game's, under the UNHAPPY level-2 step 45 #2369; game choice (open S1145, S0943)
        } },
        { src = "hang", on = "band", at = 1, stim = 1, list = { -- the hangover flag, Game: half each realistic size, S0814/S0817/S0930
            { ch = "stat", s = "mNut", v = 1.075, row = "S0814", gc = true }, -- 1 + 0.15 / 2; game choice (open S1127)
            { ch = "stat", s = "stressTarget", v = 0.05, row = "S0930", gc = true }, -- 0.10 / 2; game choice (open S1145)
            { ch = "stat", s = "unhappyTarget", v = 21, row = "S0930", gc = true }, -- UNHAPPY level 1 is > 20 #2369 (the S2248 precedent); game choice (open S1145, S0943)
        } },
        -- Sleep recovery (rNut) and panic from caffeine on board, C = 50 x band: rNut 1 - 0.15 x satC, satC = clamp((C - 32.1)
        -- / (107 - 32.1), 0, 1) (S0797); panic 15 C / 400 to 400 mg (S0929), then 15 + 49 (C - 400) / 400 to 64 at 800 mg.
        { src = "caf", on = "band", at = 1, list = { -- 50 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.9641522029372497, row = "S0795", gc = true }, -- 1 - 0.15 x 17.9/74.9; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 1.875, row = "S0929", gc = true }, -- 15 x 50/400; one SMD = one band, game choice (open S1144)
        } },
        { src = "caf", on = "band", at = 2, list = { -- 100 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.8640186915887851, row = "S0795", gc = true }, -- 1 - 0.15 x 67.9/74.9; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 3.75, row = "S0929", gc = true }, -- 15 x 100/400; game choice (open S1144)
        } },
        { src = "caf", on = "band", at = 3, list = { -- 150 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- 1 - 0.15 x 1 (saturated); game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 5.625, row = "S0929", gc = true }, -- 15 x 150/400; game choice (open S1144)
        } },
        { src = "caf", on = "band", at = 4, list = { -- 200 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 7.5, row = "S0929", gc = true }, -- 15 x 200/400; game choice (open S1144)
        } },
        { src = "caf", on = "band", at = 5, list = { -- 250 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 9.375, row = "S0929", gc = true }, -- 15 x 250/400; game choice (open S1144)
        } },
        { src = "caf", on = "band", at = 6, list = { -- 300 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 11.25, row = "S0929", gc = true }, -- 15 x 300/400; game choice (open S1144)
        } },
        { src = "caf", on = "band", at = 7, list = { -- 350 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 13.125, row = "S0929", gc = true }, -- 15 x 350/400; game choice (open S1144)
        } },
        { src = "caf", on = "band", at = 8, list = { -- 400 mg, the knee, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 15.0, row = "S0929", gc = true }, -- 15 x 400/400, S0929's 400 mg knee; game choice (open S1144)
        } },
        { src = "caf", on = "band", at = 9, list = { -- 450 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 21.125, row = "S0929", gc = true }, -- 15 + 49 x 50/400; game choice slope (open S1145)
        } },
        { src = "caf", on = "band", at = 10, list = { -- 500 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 27.25, row = "S0929", gc = true }, -- 15 + 49 x 100/400; game choice slope (open S1145)
        } },
        { src = "caf", on = "band", at = 11, list = { -- 550 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 33.375, row = "S0929", gc = true }, -- 15 + 49 x 150/400; game choice slope (open S1145)
        } },
        { src = "caf", on = "band", at = 12, list = { -- 600 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 39.5, row = "S0929", gc = true }, -- 15 + 49 x 200/400; game choice slope (open S1145)
        } },
        { src = "caf", on = "band", at = 13, list = { -- 650 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 45.625, row = "S0929", gc = true }, -- 15 + 49 x 250/400; game choice slope (open S1145)
        } },
        { src = "caf", on = "band", at = 14, list = { -- 700 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 51.75, row = "S0929", gc = true }, -- 15 + 49 x 300/400; game choice slope (open S1145)
        } },
        { src = "caf", on = "band", at = 15, list = { -- 750 mg, S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 57.875, row = "S0929", gc = true }, -- 15 + 49 x 350/400; game choice slope (open S1145)
        } },
        { src = "caf", on = "band", at = 16, list = { -- 800 mg and above (the band's cap), S0795/S0929
            { ch = "stat", s = "rNut", v = 0.85, row = "S0795", gc = true }, -- saturated; game choice (open S1126)
            { ch = "stat", s = "panicTarget", v = 64.0, row = "S0929", gc = true }, -- 15 + 49 x 400/400, S0929's 2.86 x 24 = 68.6 capped under 65; game choice slope (open S1145)
        } },
        -- Alcohol: the episode peak band (S0813; r open S1104).
        { src = "alc", on = "band", at = 1, list = { -- peak at least 0.0735 %, S0813
            { ch = "stat", s = "rNut", v = 0.90, row = "S0813", gc = true }, -- a bounded judgement; game choice (open S0853)
        } },
        { src = "alc", on = "band", at = 2, list = { -- peak at least 0.125 %, S0813
            { ch = "stat", s = "rNut", v = 0.80, row = "S0813", gc = true }, -- range [0.80, 1.00] game choice (open S0853)
        } },
        -- Exercise earlier today: 1 + 0.10 q, q = band / 4 (S0826); skipped while boutVig, whose row replaces it (S0827).
        { src = "ex", on = "band", at = 1, unless = "boutVig", list = { -- q 0.25, S0826
            -- a behaviour credit (S0826), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "rNut", v = 1.025, row = "S0826", gc = true, bonus = true }, -- 1 + 0.10 x 0.25; game choice 0.10 (open S1129)
        } },
        { src = "ex", on = "band", at = 2, unless = "boutVig", list = { -- q 0.50, S0826
            { ch = "stat", s = "rNut", v = 1.05, row = "S0826", gc = true, bonus = true }, -- 1 + 0.10 x 0.50; game choice 0.10 (open S1129)
        } },
        { src = "ex", on = "band", at = 3, unless = "boutVig", list = { -- q 0.75, S0826
            { ch = "stat", s = "rNut", v = 1.075, row = "S0826", gc = true, bonus = true }, -- 1 + 0.10 x 0.75; game choice 0.10 (open S1129)
        } },
        { src = "ex", on = "band", at = 4, unless = "boutVig", list = { -- q 1, S0826
            { ch = "stat", s = "rNut", v = 1.10, row = "S0826", gc = true, bonus = true }, -- 1 + 0.10 x 1; game choice 0.10 (open S1129)
        } },
        { src = "boutVig", on = "flag", list = {
            { ch = "stat", s = "rNut", v = 0.95, row = "S0827", gc = true }, -- vigorous ending 1 h or less before the bout, direction S0827 (none at 4 h, S0828); game choice (open S1130)
        } },
        { src = "allReplete", on = "flag", gated = "BalanceBonus", list = {
            { ch = "stat", s = "rNut", v = 1.05, row = "S1175", gc = true, bonus = true }, -- BalanceBonus, the dial's fatigue-recovery half; game choice (open S1175)
        } },
        -- Stress (STRESS 0..1, one SMD = one 0.25 band, open S1144).
        { src = "bgroupMax", on = "flag", at = 3, list = { -- the worst B-vitamin grade depleted, S0922
            { ch = "stat", s = "stressTarget", v = 0.03, row = "S1145", gc = true }, -- half the clinical rung; game choice (open S1145)
        } },
        { src = "bgroupMax", on = "flag", at = 4, list = { -- clinical, S0922
            { ch = "stat", s = "stressTarget", v = 0.06, row = "S0922", gc = true }, -- SMD 0.23 x band 0.25 = 0.0575, as 0.06; game choice convention (open S1144)
        } },
        -- The dehydration mood rows sit in the 4-6 % band: apathy and weariness at about 4.2 % (S2248).
        { src = "dehyd", on = "band", at = { 6, 8 }, list = { -- 4 % and above, S2248 (weariness, apathy, impatience at about 4 %)
            { ch = "stat", s = "stressTarget", v = 0.06, row = "S0098", gc = true }, -- direction only, no effect size; game choice (open S1145)
            { ch = "stat", s = "panicTarget", v = 7, row = "S0098", gc = true }, -- tension/anxiety p = 0.029; 7, not 6: level 1 is > 6 #2369; game choice (open S1145)
            { ch = "stat", s = "unhappyTarget", v = 21, row = "S2248", gc = true }, -- apathy at about 4.2 %; 21: UNHAPPY level 1 is > 20 #2369; vanilla-sized; game choice (open S1145)
        } },
        -- Panic and unhappiness from sleep loss (iuSleepQ = band x 0.125): panic 14 x iuSleepQ capped 20 (S0916),
        -- unhappiness 25 x iuSleepQ / 1.5 (S0915).
        { src = "iuS", on = "band", at = 1, list = { -- 0.125 IU, S0916/S0915
            { ch = "stat", s = "panicTarget", v = 1.75, row = "S0916", gc = true }, -- 14 x 0.125; game choice convention (open S1144)
            { ch = "stat", s = "unhappyTarget", v = 2.0833333333333335, row = "S0915", gc = true }, -- 25 x 0.125/1.5; game choice convention (open S1144)
        } },
        { src = "iuS", on = "band", at = 2, list = { -- 0.25 IU, S0916/S0915
            { ch = "stat", s = "panicTarget", v = 3.5, row = "S0916", gc = true }, -- 14 x 0.25; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = 4.166666666666667, row = "S0915", gc = true }, -- 25 x 0.25/1.5; game choice (open S1144)
        } },
        { src = "iuS", on = "band", at = 3, list = { -- 0.375 IU, S0916/S0915
            { ch = "stat", s = "panicTarget", v = 5.25, row = "S0916", gc = true }, -- 14 x 0.375; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = 6.25, row = "S0915", gc = true }, -- 25 x 0.375/1.5; game choice (open S1144)
        } },
        { src = "iuS", on = "band", at = 4, list = { -- 0.5 IU, S0916/S0915
            { ch = "stat", s = "panicTarget", v = 7.0, row = "S0916", gc = true }, -- 14 x 0.5; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = 8.333333333333334, row = "S0915", gc = true }, -- 25 x 0.5/1.5; game choice (open S1144)
        } },
        { src = "iuS", on = "band", at = 5, list = { -- 0.625 IU, S0916/S0915
            { ch = "stat", s = "panicTarget", v = 8.75, row = "S0916", gc = true }, -- 14 x 0.625; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = 10.416666666666666, row = "S0915", gc = true }, -- 25 x 0.625/1.5; game choice (open S1144)
        } },
        { src = "iuS", on = "band", at = 6, list = { -- 0.75 IU, S0916/S0915
            { ch = "stat", s = "panicTarget", v = 10.5, row = "S0916", gc = true }, -- 14 x 0.75; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = 12.5, row = "S0915", gc = true }, -- 25 x 0.75/1.5; game choice (open S1144)
        } },
        { src = "iuS", on = "band", at = 7, list = { -- 0.875 IU, S0916/S0915
            { ch = "stat", s = "panicTarget", v = 12.25, row = "S0916", gc = true }, -- 14 x 0.875; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = 14.583333333333334, row = "S0915", gc = true }, -- 25 x 0.875/1.5; game choice (open S1144)
        } },
        { src = "iuS", on = "band", at = 8, list = { -- 1 IU (24 h awake), S0916/S0915
            { ch = "stat", s = "panicTarget", v = 14.0, row = "S0916", gc = true }, -- 14 x 1; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = 16.666666666666668, row = "S0915", gc = true }, -- 25 x 1/1.5; game choice (open S1144)
        } },
        { src = "iuS", on = "band", at = 9, list = { -- 1.125 IU, S0916/S0915
            { ch = "stat", s = "panicTarget", v = 15.75, row = "S0916", gc = true }, -- 14 x 1.125; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = 18.75, row = "S0915", gc = true }, -- 25 x 1.125/1.5; game choice (open S1144)
        } },
        { src = "iuS", on = "band", at = 10, list = { -- 1.25 IU, S0916/S0915
            { ch = "stat", s = "panicTarget", v = 17.5, row = "S0916", gc = true }, -- 14 x 1.25; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = 20.833333333333332, row = "S0915", gc = true }, -- 25 x 1.25/1.5; game choice (open S1144)
        } },
        { src = "iuS", on = "band", at = 11, list = { -- 1.375 IU, S0916/S0915
            { ch = "stat", s = "panicTarget", v = 19.25, row = "S0916", gc = true }, -- 14 x 1.375; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = 22.916666666666668, row = "S0915", gc = true }, -- 25 x 1.375/1.5; game choice (open S1144)
        } },
        { src = "iuS", on = "band", at = 12, list = { -- 1.5 IU (the sleep term's cap), S0916/S0915
            { ch = "stat", s = "panicTarget", v = 20, row = "S0916", gc = true }, -- 14 x 1.5 = 21, capped 20; game choice cap (open S1147)
            { ch = "stat", s = "unhappyTarget", v = 25.0, row = "S0915", gc = true }, -- 25 x 1.5/1.5; game choice (open S1144)
        } },
        -- The exercise credit (target offsets only), q = band / 4: panic -11 q, unhappiness -13 q (S0932).
        { src = "ex", on = "band", at = 1, list = { -- q 0.25, S0932
            -- a behaviour credit (S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "panicTarget", v = -2.75, row = "S0932", gc = true, bonus = true }, -- -11 x 0.25; game choice convention (open S1144)
            { ch = "stat", s = "unhappyTarget", v = -3.25, row = "S0932", gc = true, bonus = true }, -- -13 x 0.25; game choice convention (open S1144)
        } },
        { src = "ex", on = "band", at = 2, list = { -- q 0.50, S0932
            { ch = "stat", s = "panicTarget", v = -5.5, row = "S0932", gc = true, bonus = true }, -- -11 x 0.50; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = -6.5, row = "S0932", gc = true, bonus = true }, -- -13 x 0.50; game choice (open S1144)
        } },
        { src = "ex", on = "band", at = 3, list = { -- q 0.75, S0932
            { ch = "stat", s = "panicTarget", v = -8.25, row = "S0932", gc = true, bonus = true }, -- -11 x 0.75; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = -9.75, row = "S0932", gc = true, bonus = true }, -- -13 x 0.75; game choice (open S1144)
        } },
        { src = "ex", on = "band", at = 4, list = { -- q 1, S0932
            { ch = "stat", s = "panicTarget", v = -11.0, row = "S0932", gc = true, bonus = true }, -- -11 x 1; game choice (open S1144)
            { ch = "stat", s = "unhappyTarget", v = -13.0, row = "S0932", gc = true, bonus = true }, -- -13 x 1; game choice (open S1144)
        } },
        -- Vitamin D (gated off): unhappiness (S0920) and colds (S0974). Semi-starvation mood and omega-3: no row (open S0937).
        { src = "vitD", on = "grade", at = 3, gated = "VITD_EFFECTS", list = { -- depleted, S0920/S0974
            { ch = "stat", s = "unhappyTarget", v = 2, row = "S1145", gc = true }, -- half the clinical rung; game choice (open S1145)
            { ch = "body", s = "coldMul", v = 1.03, row = "S1158", gc = true }, -- half of S0974's 6 %; game choice (open S1158)
        } },
        { src = "vitD", on = "grade", at = 4, gated = "VITD_EFFECTS", list = { -- clinical, S0920/S0974
            { ch = "stat", s = "unhappyTarget", v = 4, row = "S0920", gc = true }, -- 7 halved for small-study bias, as 4; game choice (open S1145)
            { ch = "body", s = "coldMul", v = 1.06, row = "S0974", gc = true }, -- OR 0.94, a 6 % cut; game choice (open S1158)
        } },
        -- The nutritional fatigue offset (fOffNut, capped 0.15): dehydration from 2 %, held at 4 % (S0098); hypoglycaemia
        -- +0.10 (open S1132).
        { src = "dehyd", on = "band", at = 3, list = { -- [2, 2.5) %, S0098
            { ch = "stat", s = "fOffNut", v = 0.06, row = "S0098", gc = true }, -- 0.06 at 2 %; game choice (open S0934)
        } },
        { src = "dehyd", on = "band", at = 4, list = { -- [2.5, 3) %, S0098
            { ch = "stat", s = "fOffNut", v = 0.07, row = "S0098", gc = true }, -- 0.06 + 0.04 x 0.5/2; game choice (open S0934)
        } },
        { src = "dehyd", on = "band", at = 5, list = { -- [3, 4) %, S0098
            { ch = "stat", s = "fOffNut", v = 0.08, row = "S0098", gc = true }, -- 0.06 + 0.04 x 1/2; game choice (open S0934)
        } },
        { src = "dehyd", on = "band", at = { 6, 8 }, list = { -- 4 % and above, held, S0098
            { ch = "stat", s = "fOffNut", v = 0.10, row = "S0098", gc = true }, -- 0.06 + 0.04, held; game choice (open S0934)
        } },
        -- Blood glucose band 3 (below 2.6 mmol/L, S0897): fatigue, speed and temperature.
        { src = "bg", on = "band", at = 3, list = { -- below 2.6 mmol/L, S0897
            { ch = "stat", s = "fOffNut", v = 0.10, row = "S1132", gc = true }, -- hypoglycaemia through fatigue; game choice (open S1132)
            { ch = "stat", s = "speedMul", v = 0.85, row = "S1176", gc = true }, -- game choice (open S1176)
            { ch = "stat", s = "tempOffset", v = -0.2, row = "S1014", gc = true }, -- S1014 direction (a listed cause of secondary hypothermia); game choice (open S1161)
        } },
        { src = "bg", on = "band", at = 2, list = { -- [2.6, 3.0) mmol/L, S0897
            { ch = "stat", s = "speedMul", v = 0.92, row = "S1176", gc = true }, -- game choice (open S1176)
        } },
        -- Short Sighted at clinical vitamin A (S0144: xerophthalmia follows night blindness).
        { src = "vitA", on = "grade", at = 4, list = { -- clinical, S0143
            { ch = "trait", s = "shortSighted", v = 1, row = "S0143", gc = true }, -- the toggle at clinical; game choice (open S1143)
        } },
        -- The direct speed write (min).
        { src = "dehyd", on = "band", at = 7, list = { -- [6, 10) %, dizziness at about 5.8 % (S2248); game choice (open S1098)
            { ch = "stat", s = "speedMul", v = 0.85, row = "S1176", gc = true }, -- game choice (open S1176)
        } },
        { src = "dehyd", on = "band", at = 8, list = { -- 10 % and above, delirium at about 11 % (S2248): confusion and collapse
            { ch = "stat", s = "speedMul", v = 0.75, row = "S1176", gc = true }, -- the clamp's floor, vanilla-sized; game choice (open S1176)
        } },
        { src = "iu", on = "band", at = { 20, 25 }, list = { -- 2.0 IU and above, S0750 the unit's anchor
            { ch = "stat", s = "speedMul", v = 0.90, row = "S1176", gc = true }, -- game choice (open S1176)
        } },
        { src = "hypo", on = "band", at = { 2, 3 }, list = { -- below 120 mmol/L, S1047 (CNS symptoms)
            { ch = "stat", s = "speedMul", v = 0.85, row = "S1176", gc = true }, -- game choice (open S1176)
        } },
        -- Starvation in science's order: phase 1 weakness from the onset, 2 cold intolerance and slower healing from day 3,
        -- 3 infection and mood from day 14 (pacing open S2247). Before phase 3 (starveEarly) the protein-energy and
        -- energy-availability rows are held off, so infection and colds wait for day 14.
        { src = "starve", on = "flag", at = { 1, 3 }, list = { -- weakness: endurance (S2239 difficulty getting up and moving)
            { ch = "stat", s = "mNut", v = 1.25, row = "S2247", gc = true }, -- the anaemia row's size; game choice (open S2247)
        } },
        { src = "starve", on = "flag", at = 2, list = { -- slower healing from day 3 (S2246 exhaustion)
            { ch = "body", s = "healMul", v = 0.80, row = "S2247", gc = true }, -- the pe 3 row's size; game choice (open S2247)
        } },
        { src = "starve", on = "flag", at = { 2, 3 }, list = { -- cold intolerance (S2238 hypothermia under 35.5 C, S2246 body temperature)
            { ch = "stat", s = "tempOffset", v = -0.2, row = "S2247", gc = true }, -- the iron-anaemia row's size; game choice (open S2247)
        } },
        { src = "starve", on = "flag", at = 3, list = { -- mood from day 14 (S2239 apathy, S2245 depression)
            { ch = "stat", s = "unhappyTarget", v = 21, row = "S2247", gc = true }, -- UNHAPPY level 1 is > 20 #2369; game choice (open S2247)
        } },
        -- Healing, bleeding (vitamin C), infection (protein-energy) and colds.
        { src = "pe", on = "pe", at = 2, unless = "starveEarly", list = { -- protein-energy marginal, S0951/S0954
            { ch = "body", s = "healMul", v = 0.92, row = "S1150", gc = true }, -- game choice (open S1150; PEM healing size open S0129)
            { ch = "body", s = "infectMul", v = 1.15, row = "S1154", gc = true }, -- game choice (open S1154)
        } },
        { src = "pe", on = "pe", at = 3, unless = "starveEarly", list = { -- protein-energy depleted, S0951/S0954
            { ch = "body", s = "healMul", v = 0.80, row = "S1150", gc = true }, -- game choice (open S1150)
            { ch = "body", s = "infectMul", v = 1.55, row = "S1154", gc = true }, -- game choice (open S1154)
        } },
        { src = "pe", on = "pe", at = 4, unless = "starveEarly", list = { -- protein-energy clinical, S0951/S0954/S0955
            { ch = "body", s = "healMul", v = 0.74, row = "S0951" }, -- 1/1.35, the closure ratio 60.9/45.2 of S0951
            { ch = "body", s = "infectMul", v = 2.30, row = "S0954" }, -- S0954 OR 2.31, as 2.30
        } },
        { src = "vitC", on = "grade", at = 3, list = { -- vitamin C depleted, S0952/S0965
            { ch = "body", s = "healMul", v = 0.85, row = "S0216", gc = true }, -- game choice (open S0216); S0952 null at replete
            { ch = "body", s = "bleedMul", v = 1.10, row = "S1152", gc = true }, -- S0965/S0966 direction; game choice (open S1152)
        } },
        { src = "vitC", on = "grade", at = 4, list = { -- clinical (scurvy), S0958/S0965/S0966
            { ch = "body", s = "healMul", v = 0.50, row = "S0958", gc = true }, -- a defining sign of scurvy; game choice magnitude (open S0216)
            { ch = "body", s = "bleedMul", v = 1.25, row = "S0965", gc = true }, -- direction; game choice magnitude (open S1152)
            { ch = "event", s = "bruise", v = 3.4722222222222224e-4, row = "S0966", gc = true }, -- 1/2880 per game minute, purpura predominates; game choice (open S1153)
            { ch = "body", s = "coldMul", v = 1.15, row = "S1155", gc = true }, -- C_c at clinical; game choice (open S1155)
        } },
        { src = "zinc", on = "grade", at = 3, list = { -- zinc depleted, S0953/S0948
            { ch = "body", s = "healMul", v = 0.92, row = "S1151", gc = true }, -- game choice (open S1151); S0953 null for supplementation
        } },
        { src = "zinc", on = "grade", at = 4, list = { -- zinc clinical, S0948
            { ch = "body", s = "healMul", v = 0.85, row = "S1151", gc = true }, -- game choice (open S1151)
        } },
        { src = "coldCredit", on = "flag", list = { -- replete vitamin C, at least 200 mg/d, exerting and cold-exposed, S0980
            { ch = "body", s = "coldMul", v = 0.50, row = "S0980", gc = true, bonus = true }, -- S0980 RR 0.48 taken as 0.50 (roughly halves); game choice (open S1155)
        } },
        { src = "ea", on = "ea", at = 1, unless = "starveEarly", list = { -- energy availability [20, 30) kcal/kg LBM, S0691/S0990
            { ch = "body", s = "coldMul", v = 1.3, row = "S1156", gc = true }, -- game choice rung (open S1156)
        } },
        { src = "ea", on = "ea", at = 2, unless = "starveEarly", list = { -- [10, 20), S0990 (22 kcal/kg immune markers)
            { ch = "body", s = "coldMul", v = 2.2, row = "S0990", gc = true }, -- game choice rung (open S1156)
        } },
        { src = "ea", on = "ea", at = 3, unless = "starveEarly", list = { -- below 10, S0991
            { ch = "body", s = "coldMul", v = 3.0, row = "S0991", gc = true }, -- OR 3.8 the top, taken at the clamp; game choice (open S1156)
        } },
        { src = "debt", on = "band", at = 1, list = { -- debt [4, 8) h, S0993
            { ch = "body", s = "coldMul", v = 1.6, row = "S0993", gc = true }, -- 6-7 h OR 1.66 (NS); the hours-to-debt map a game choice (open S1157)
        } },
        { src = "debt", on = "band", at = 2, list = { -- debt 8 h and more, S0993
            { ch = "body", s = "coldMul", v = 2.5, row = "S0993", gc = true }, -- under 6 h OR 4.24-4.50, damped; game choice (open S1157)
        } },
        -- Thermal: iron-deficiency anaemia, and the exertion-gated dehydration heat side +0.3 x clamp((d - 2)/2, 0, 1) from
        -- 3 % (S1021, S2249).
        { src = "iron", on = "grade", at = 4, list = { -- iron clinical (anaemia), S1016
            { ch = "stat", s = "tempOffset", v = -0.2, row = "S1016" }, -- S1016: 36.0 vs 36.2 degrees C; iron-depleted non-anaemic equal controls
        } },
        { src = "dehyd", on = "band", at = 5, list = { -- [3, 4) %, S1021
            { ch = "stat", s = "tempHeat", v = 0.15, row = "S1021", gc = true }, -- 0.3 x 1/2; game choice magnitude (open S1160)
        } },
        { src = "dehyd", on = "band", at = { 6, 8 }, list = { -- 4 % and above, S1021
            { ch = "stat", s = "tempHeat", v = 0.3, row = "S1021", gc = true }, -- 0.3 x 1, held; game choice magnitude (open S1160)
        } },
        -- Toxicity: FOOD_SICKNESS 30 / 55 / 85 at rungs 1 / 2 / 3 (SICK 1/2/3, #3130), POISON 0. A rung row matches its rung and
        -- above, and max keeps the worst.
        { src = "vitC", on = "rung", at = { 1, 3 }, list = { -- UL 2000 mg/d, S1043
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S1043", gc = true }, -- game choice (open S1165)
        } },
        { src = "niacin", on = "rung", at = { 1, 3 }, list = { -- UL 35 mg/d nicotinic acid, S0269
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S0269", gc = true }, -- game choice (open S1165)
        } },
        { src = "vitB6", on = "rung", at = { 1, 3 }, list = { -- UL 100 mg/d, S0295
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S0295", gc = true }, -- game choice (open S1165)
        } },
        { src = "folate", on = "rung", at = { 1, 3 }, list = { -- UL 1000 ug/d folic acid, S0330
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S0330", gc = true }, -- game choice (open S1165)
        } },
        { src = "choline", on = "rung", at = { 1, 3 }, list = { -- UL 3500 mg/d, S0373
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S0373", gc = true }, -- game choice (open S1165)
        } },
        { src = "vitA", on = "rung", at = { 1, 3 }, list = { -- UL 3000 ug/d preformed, S1024
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S1024", gc = true }, -- game choice (open S1165)
        } },
        { src = "vitD", on = "rung", at = { 1, 3 }, list = { -- UL 100 ug/d, S1029
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S1029", gc = true }, -- game choice (open S1165)
        } },
        { src = "vitE", on = "rung", at = { 1, 3 }, list = { -- UL 300 mg/d supplemental, S0173
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S0173", gc = true }, -- game choice (open S1165)
        } },
        { src = "iron", on = "rung", at = { 1, 3 }, list = { -- UL 45 mg/d, S1031
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S1031", gc = true }, -- game choice (open S1165)
        } },
        { src = "zinc", on = "rung", at = { 1, 3 }, list = { -- UL 40 mg/d, S1034
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S1034", gc = true }, -- game choice (open S1165)
        } },
        { src = "copper", on = "rung", at = { 1, 3 }, list = { -- UL 10000 ug/d, S0472
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S0472", gc = true }, -- game choice (open S1165)
        } },
        { src = "magnesium", on = "rung", at = { 1, 3 }, list = { -- UL 350 mg/d supplements, S0421
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S0421", gc = true }, -- game choice (open S1165)
        } },
        { src = "calcium", on = "rung", at = { 1, 3 }, list = { -- UL 2500 mg/d, S0410
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S0410", gc = true }, -- game choice (open S1165)
        } },
        { src = "iodine", on = "rung", at = { 1, 3 }, list = { -- UL 1100 ug/d, S0458
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S0458", gc = true }, -- game choice (open S1165)
        } },
        { src = "selenium", on = "rung", at = { 1, 3 }, list = { -- UL 400 ug/d, S1038
            { ch = "stat", s = "foodSickTarget", v = 30, row = "S1038", gc = true }, -- game choice (open S1165)
        } },
        { src = "vitB6", on = "rung", at = { 2, 3 }, list = { -- chronic 50 mg/d held 180 d, S0305
            { ch = "stat", s = "foodSickTarget", v = 55, row = "S0305", gc = true }, -- game choice (open S1165)
        } },
        { src = "vitA", on = "rung", at = { 2, 3 }, list = { -- chronic 7500 ug/d or the liver store, S0149/S0150; acute S1025
            { ch = "stat", s = "foodSickTarget", v = 55, row = "S0149", gc = true }, -- game choice (open S1165)
        } },
        { src = "vitD", on = "rung", at = { 2, 3 }, list = { -- chronic 250 ug/d, S1029/S1030
            { ch = "stat", s = "foodSickTarget", v = 55, row = "S1030", gc = true }, -- game choice (open S1165)
        } },
        { src = "selenium", on = "rung", at = { 2, 3 }, list = { -- chronic 5000 ug/d, S0469
            { ch = "stat", s = "foodSickTarget", v = 55, row = "S0469", gc = true }, -- game choice (open S1165)
        } },
        { src = "iron", on = "rung", at = { 2, 3 }, list = { -- acute 20 mg/kg, S0442/S1032
            { ch = "stat", s = "foodSickTarget", v = 55, row = "S1032", gc = true }, -- game choice (open S1165)
        } },
        { src = "iron", on = "rung", at = 3, list = { -- acute 60 mg/kg, the lethal rung (its drain is K.drain's), S1033
            { ch = "stat", s = "foodSickTarget", v = 85, row = "S1033", gc = true }, -- SICK 3, under 90 (#2356); game choice (open S1165)
        } },
        -- Hyponatraemia (S0102) and refeeding (S0114: no drain).
        { src = "hypo", on = "band", at = 2, list = { -- below 120 mmol/L, S1047
            { ch = "stat", s = "foodSickTarget", v = 55, row = "S1047", gc = true }, -- CNS symptoms as sickness; game choice (open S1165)
        } },
        { src = "hypo", on = "band", at = 3, list = { -- below 112 mmol/L, S1047
            { ch = "stat", s = "foodSickTarget", v = 85, row = "S1047", gc = true }, -- with its drain; game choice (open S1165)
        } },
        { src = "refeedEvent", on = "flag", list = {
            { ch = "stat", s = "foodSickTarget", v = 55, row = "S0114", gc = true }, -- fluid shift as sickness, S0117 no mortality; game choice (open S1165)
        } },
        -- Overfull is the Overfull level of the stomach's whole mass (K.view.overfullOf), 4 at the 1100 g capacity (S1253).
        -- Level 3 holds ENDURANCE at or under 0.73, the Endurance moodle's level 1, whose speed cut is the one route to a
        -- player's speed (#2711). Level 4 adds nausea at once (SICK 1); its refusal is vanilla's timer (K.view.foodTimer).
        { src = "overfull", on = "flag", at = { 3, 4 }, list = { -- Bloated and Painfully stuffed, S1253 the scale's top
            { ch = "stat", s = "rowEndCap", v = 0.73, row = "S1253", gc = true }, -- 0.75 less the standing regeneration of about 0.0056 a game minute at the 90-minute day (#2258), so the level holds between writes; game choice (open S1176)
        } },
        { src = "overfull", on = "flag", at = 4, list = { -- maximal discomfort at the hard capacity, S1253
            { ch = "stat", s = "foodSickStep", v = 30, row = "S1253", gc = true }, -- nausea as SICK 1 at once, the UL rung's size; vanilla's own decay (about 2.7 an hour, #3084) then lets it linger about 1.8 game hours; game choice (open S1165)
        } },
    },
    SYMPTOMS = {
        PAIN_TOP = 20, -- a part's added pain capped at 20 over its pain modifier, Pain level 1's band top (PAIN above 10, at most 20, #2369), so causes sharing a part add no more than level 1 there (causes on different parts still sum); game choice (open S1147)
        -- A two-part cause sums to twice the top, so a head, a lower-torso and both leg causes reach Pain level 3 at Severity 1
        -- (#2369); InjurySeverity scales it in getPain.
        CAP_LO = 0.05, -- the symptom cap's floor under Severity above 1, inside Endurance level 4 (at most 0.10, #3926); game choice (open S1176)
        STRESS_HI = 0.70, -- the stress floor's cap under Severity, one step under Stress level 3 at 0.75 (#2369), as the surfaces' caps (S1147); game choice (open S1147)
        UNHAPPY_HI = 59, -- the unhappiness floor's cap under Severity, one under Unhappy level 3 at 60 (#2369), as unhappyTarget's; game choice (open S1147)
        CAUSES = {
            { name = "starvation", overlayOff = true, list = {
                SYM_END,
                SYM_STRESS,
                SYM_UNHAPPY,
                { lever = "pain", shape = "flat", v = SYM_PAIN, parts = {
                    7, -- Torso_Lower, the stomach: abdominal pain (S2239) from the onset at 30 unfed hours; game choice part pending research (open S2247)
                } },
            } },
            { name = "scurvy", list = {
                SYM_END,
                SYM_STRESS,
                SYM_UNHAPPY,
                { lever = "pain", shape = "flat", v = SYM_PAIN, parts = {
                    13, -- LowerLeg_L: joint pain and swelling (S0227); vanilla has no knee part; game choice part pending research (open S1168)
                    14, -- LowerLeg_R, as LowerLeg_L (S0227); game choice part pending research (open S1168)
                } },
            } },
            { name = "beriberi", list = {
                SYM_END,
                SYM_STRESS,
                SYM_UNHAPPY,
                { lever = "pain", shape = "flat", v = SYM_PAIN, parts = {
                    13, -- LowerLeg_L: the legs of wet beriberi's oedema (S0244); game choice part pending research (open S1169)
                    14, -- LowerLeg_R, as LowerLeg_L (S0244); game choice part pending research (open S1169)
                } },
            } },
            { name = "pellagra", list = {
                SYM_END,
                SYM_STRESS,
                SYM_UNHAPPY,
                { lever = "pain", shape = "flat", v = SYM_PAIN, parts = {
                    7, -- Torso_Lower: the diarrhoea of pellagra (S0272); game choice part pending research (open S1170)
                } },
            } },
            { name = "hyponatraemia", list = {
                SYM_END,
                SYM_STRESS,
                SYM_UNHAPPY,
                { lever = "pain", shape = "flat", v = SYM_PAIN, parts = {
                    8, -- Head: headache as a central-nervous symptom under 120 mmol/L (S1047); game choice part pending research (open S1171)
                } },
            } },
            { name = "dehydration", overlayOff = true, list = {
                SYM_END,
                SYM_STRESS,
                SYM_UNHAPPY,
                { lever = "pain", shape = "flat", v = SYM_PAIN, parts = {
                    8, -- Head: headache from about 5 % of body mass (S2248); game choice part pending research (open S1101)
                } },
            } },
            { name = "iron", list = {
                SYM_END,
                SYM_STRESS,
                SYM_UNHAPPY,
                { lever = "pain", shape = "flat", v = SYM_PAIN, parts = {
                    7, -- Torso_Lower, the gut of an acute overdose; game choice part pending research (open S1173)
                } },
            } },
        },
    },
}
