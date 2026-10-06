-- NR_Data_Effects.lua -- not a kernel file: the declarative effects table the composer
-- (NR_Kernel_Effects.lua, K.effects.compose) folds into record.effects, as NR.data.effects = { SURF, ROWS, ... }
-- (Plan 5, formulas briefing A3-A4, B5, D3-D4, E3, F2, G, H1; rulings 2-3, 5-10, 12, 17-18, 23; T1-1).
-- SURF names each surface's fold operator (mul | add | max | min | or), its identity and its clamp. A surface
-- marked machine = true is written by its own kernel function on the slow clock (nightVision by K.effects.nvMinute,
-- drain by K.effects.drain) and the composer never resets, scales or clamps it; sevMin on a boolean surface is the
-- Severity below which it reads false (Short Sighted, ruling 7).
-- ROWS is an array of { src, on, at, list }: on is grade (record.nutrients[src].g), rung (record.nutrients[src].x),
-- band (the band named src in the twelve-band vector), flag (flags[src]; at nil matches true, a number or
-- {lo, hi} matches a numeric flag), pe (the protein-energy grade) or ea (K.effects.eaBand of the closed-day energy
-- availability); at is an integer or an inclusive {lo, hi}. A row may carry gated (VITD_EFFECTS: folded only when
-- the composer's vitdOn is true; BalanceBonus: only when bonusOn is true) and unless (a flag name: the row is
-- skipped while that flag is true -- the "replaces" of the briefing). Each entry is { ch, s, v, row } with ch the
-- spec section 4.5 channel, s a surface, v its magnitude and row the science row it rests on; gc = true marks a
-- magnitude that is a game choice (its comment names the open row); bonus = true marks the two adequacy exceptions
-- the Severity dial does not scale (the vitamin C cold credit, BalanceBonus).
-- Band rows are evaluated at the band's lower edge (A2), so each band's magnitude is a literal computed in doubles
-- with its arithmetic in the comment; testing/tests/kernel/test_data_effects.py recomputes them and enforces that
-- every line with a number carries its row (an S id, a #nnnn claims row for a vanilla threshold, or a game choice
-- naming its open row).
-- Ruled differently from the briefing (the plan's rulings only): hungerMul and thirstMul dropped (ruling 3); POISON
-- ships 0 at every rung, so no row drives poisonTarget (ruling 12); the toxicity, hyponatraemia and refeeding rows
-- target FOOD_SICKNESS 30 / 55 / 85, never the SICKNESS stat (ruling T1-1); omega-3 ships nothing (ruling 8: S0919
-- is EPA-specific and the vector has no EPA key); iron excess has no infection row (ruling 17; S0989 is a
-- malaria-setting trial); the two vitamin D rows are gated off (ruling 8).
-- Additions beyond the briefing's SURF list, each named by its own A-section: bruise (F4's per-minute purpura
-- probability, A3's own example entry), tempHeat (G's dehydration heat side, applied by the adapter only while
-- exerting, met >= 3, so the set stays a pure function of its trigger), foodSickTarget (T1-1).
local NR = NutritionRevamp
NR.data = NR.data or {}

NR.data.effects = {
    -- Ruling 8: the vitamin D rows ship gated off until an outdoor-daylight seat exists (kSun 0, open S1064).
    VITD_EFFECTS = false,
    -- The bleeding time a spontaneous bruise starts at (F4; the adapter's event write).
    BRUISE_T0 = 0.05, -- game choice: about 1.79 x damageScaler health per bruise (open S1153)
    SURF = {
        mNut = { op = "mul", id = 1, lo = 1.0, hi = 2.0 }, -- fatigue accrual, nutritional part; game choice clamp above the 1.3 trait span #2270 (open S1133)
        rNut = { op = "mul", id = 1, lo = 0.5, hi = 1.3 }, -- sleep recovery, nutritional part; game choice clamp (open S1133)
        stressTarget = { op = "add", id = 0, lo = 0, hi = 0.50 }, -- STRESS floor; game choice cap at the level-2 step 0.50 #2369 (open S1147)
        unhappyTarget = { op = "add", id = 0, lo = 0, hi = 59 }, -- UNHAPPINESS floor; game choice cap one under the level-3 step 60 #2369 (open S1147)
        panicTarget = { op = "add", id = 0, lo = 0, hi = 64 }, -- PANIC floor; game choice cap one under the level-3 step 65 #2369 (open S1147)
        foodSickTarget = { op = "max", id = 0, lo = 0, hi = 85 }, -- FOOD_SICKNESS floor (T1-1): SICK levels from max(...)/100 #3019, never 90 or more (the red drain #2356); game choice (open S1165)
        poisonTarget = { op = "max", id = 0, lo = 0, hi = 30 }, -- no row drives it: POISON 0 at every rung (ruling 12); the drain caps at 30 #2358
        healMul = { op = "mul", id = 1, lo = 0.5, hi = 1.0 }, -- wound healing; game choice floor (open S1149)
        bleedMul = { op = "mul", id = 1, lo = 1.0, hi = 1.25 }, -- total bleeding damage; game choice range (open S1152)
        infectMul = { op = "mul", id = 1, lo = 1.0, hi = 2.3 }, -- wound-infection progression; S0954 OR 2.31, as 2.30
        coldMul = { op = "mul", id = 1, lo = 0.5, hi = 3.0 }, -- catchACold rises; game choice clamp under S0993/S0991 (open S1159)
        tempOffset = { op = "add", id = 0, lo = -0.5, hi = 0.3 }, -- core target offset, degrees C; game choice clamp around the -0.2 falls (S1016, open S1161) and the +0.3 rise (open S1160)
        tempHeat = { op = "add", id = 0, lo = 0, hi = 0.3 }, -- the exertion-gated heat side, degrees C; game choice magnitude (open S1160)
        speedMul = { op = "min", id = 1, lo = 0.75, hi = 1.0 }, -- the direct speed write; game choice floor (open S1176)
        fOffNut = { op = "add", id = 0, lo = 0, hi = 0.15 }, -- the nutritional fatigue offset; game choice cap so no state alone crosses Tired 1 (open S1132)
        bruise = { op = "max", id = 0, lo = 0, hi = 1 }, -- spontaneous-bruise probability per game minute; a probability, no row needed
        drain = { op = "max", id = 0, lo = 0, hi = 1, machine = true }, -- health per game minute, K.effects.drain; game choice ceiling (open S1174)
        nightVision = { op = "or", id = false, machine = true }, -- K.effects.nvMinute (ruling 6)
        shortSighted = { op = "or", id = false, sevMin = 1 }, -- ruling 7: only at Severity 1 or more; game choice gate (open S1143)
    },
    ROWS = {
        -- A4 fatigue accrual (mNut). Energy availability enters as K.effects.eaAccrual (continuous, closed day).
        -- Vitamin D, B12, folate and protein: no row (S0778, S0910 null; protein open S0792).
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
        -- Caffeine withdrawal: the wd band is round(4 x wd x cafTol) (K.effects.bands), so each row is (1 + 0.20 q) and
        -- 10 q on unhappiness with q = band / 4 = wdQ x cafTol. S0805 time course, S0803 the symptom set.
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
        { src = "hang", on = "band", at = 1, list = { -- the hangover flag, S0814/S0817/S0930
            { ch = "stat", s = "mNut", v = 1.15, row = "S0814", gc = true }, -- S0814 g 0.66 / S0817 g 0.47 via lambda; game choice (open S1127)
            { ch = "stat", s = "stressTarget", v = 0.10, row = "S0930", gc = true }, -- direction only, no pooled size (open S0943); game choice magnitude (open S1145)
        } },
        -- A4 sleep recovery (rNut) and E3 panic from caffeine on board, by the 50 mg band (C = 50 x band).
        -- rNut: 1 - 0.15 x satC, satC = clamp((C - 32.1) / (107 - 32.1), 0, 1), the 32.1 mg zero = 0.3 x 107 (S0797 x S0793,
        -- 2^(-8.8/5) = 0.2952); S0795 direction; 0.15 game choice (open S1126). Panic: 15 C / 400 to 400 mg (S0929 low SMD
        -- 0.61 x 24), then 15 + 49 (C - 400) / 400 to 64 at 800 mg; the slope a game choice (open S1145).
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
        -- Alcohol: the episode peak band (0.0735 / 0.125 % = S0813's 0.50 / 0.85 g/kg over 10 r, r 0.68 open S1104).
        { src = "alc", on = "band", at = 1, list = { -- peak at least 0.0735 %, S0813
            { ch = "stat", s = "rNut", v = 0.90, row = "S0813", gc = true }, -- the spec's bounded judgement; game choice (open S0853)
        } },
        { src = "alc", on = "band", at = 2, list = { -- peak at least 0.125 %, S0813
            { ch = "stat", s = "rNut", v = 0.80, row = "S0813", gc = true }, -- range [0.80, 1.00] game choice (open S0853)
        } },
        -- Exercise earlier today: the ex band (exEma / 7.5 min, full at EX_FULL 30 min, open S1148) gives 1 + 0.10 q,
        -- q = band / 4, S0826 (+1.3 pp SWS), S0824; skipped while boutVig (the vigorous row replaces it, S0827/S0828).
        { src = "ex", on = "band", at = 1, unless = "boutVig", list = { -- q 0.25, S0826
            -- a behaviour credit the spec names (s4.5 "exercise improves recovery"; S0826/S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "rNut", v = 1.025, row = "S0826", gc = true, bonus = true }, -- 1 + 0.10 x 0.25; game choice 0.10 (open S1129)
        } },
        { src = "ex", on = "band", at = 2, unless = "boutVig", list = { -- q 0.50, S0826
            -- a behaviour credit the spec names (s4.5 "exercise improves recovery"; S0826/S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "rNut", v = 1.05, row = "S0826", gc = true, bonus = true }, -- 1 + 0.10 x 0.50; game choice 0.10 (open S1129)
        } },
        { src = "ex", on = "band", at = 3, unless = "boutVig", list = { -- q 0.75, S0826
            -- a behaviour credit the spec names (s4.5 "exercise improves recovery"; S0826/S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "rNut", v = 1.075, row = "S0826", gc = true, bonus = true }, -- 1 + 0.10 x 0.75; game choice 0.10 (open S1129)
        } },
        { src = "ex", on = "band", at = 4, unless = "boutVig", list = { -- q 1, S0826
            -- a behaviour credit the spec names (s4.5 "exercise improves recovery"; S0826/S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "rNut", v = 1.10, row = "S0826", gc = true, bonus = true }, -- 1 + 0.10 x 1; game choice 0.10 (open S1129)
        } },
        { src = "boutVig", on = "flag", list = {
            { ch = "stat", s = "rNut", v = 0.95, row = "S0827", gc = true }, -- vigorous ending 1 h or less before the bout, direction S0827 (none at 4 h, S0828); game choice (open S1130)
        } },
        { src = "allReplete", on = "flag", gated = "BalanceBonus", list = {
            { ch = "stat", s = "rNut", v = 1.05, row = "S1175", gc = true, bonus = true }, -- BalanceBonus, the dial's fatigue-recovery half; game choice (open S1175)
        } },
        -- A4 stress (STRESS 0..1, one SMD = one 0.25 band, open S1144).
        { src = "bgroupMax", on = "flag", at = 3, list = { -- the worst B-vitamin grade depleted, S0922
            { ch = "stat", s = "stressTarget", v = 0.03, row = "S1145", gc = true }, -- half the clinical rung; game choice (open S1145)
        } },
        { src = "bgroupMax", on = "flag", at = 4, list = { -- clinical, S0922
            { ch = "stat", s = "stressTarget", v = 0.06, row = "S0922", gc = true }, -- SMD 0.23 x band 0.25 = 0.0575, as 0.06; game choice convention (open S1144)
        } },
        { src = "dehyd", on = "band", at = { 2, 8 }, list = { -- 1.5 % and above, S0098/S0099
            { ch = "stat", s = "stressTarget", v = 0.06, row = "S0098", gc = true }, -- direction only, no effect size; game choice (open S1145)
            { ch = "stat", s = "panicTarget", v = 7, row = "S0098", gc = true }, -- tension/anxiety p = 0.029; 7, not 6: level 1 is > 6 #2369; game choice (open S1145)
        } },
        { src = "bac", on = "band", at = 1, list = { -- intoxicated: nothing during (the never-during gate), S0931
            { ch = "stat", s = "stressTarget", v = 0, row = "S0931" }, -- S0931 inconsistent and unusable; the spec adds nothing while bac > 0
        } },
        -- E3 panic and unhappiness from sleep loss (iuS band, iuSleepQ = band x 0.125): panic 14 x iuSleepQ capped 20
        -- (S0916 SMD 0.57-0.63 x 24 = 13.7-15.1; the cap a game choice, open S1147); unhappiness 25 x iuSleepQ / 1.5
        -- (S0915 SMD 0.27-1.14 x 22 = 6-25).
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
        -- E3 the exercise credit (target offsets only, ruling 9): q = ex band / 4; panic -11 q (S0932 anxiety SMD -0.47 x 24
        -- = 11.3), unhappiness -13 q (S0932 depression SMD -0.61 x 22 = 13.4).
        { src = "ex", on = "band", at = 1, list = { -- q 0.25, S0932
            -- a behaviour credit the spec names (s4.5 "exercise improves recovery"; S0826/S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "panicTarget", v = -2.75, row = "S0932", gc = true, bonus = true }, -- -11 x 0.25; game choice convention (open S1144)
            -- a behaviour credit the spec names (s4.5 "exercise improves recovery"; S0826/S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "unhappyTarget", v = -3.25, row = "S0932", gc = true, bonus = true }, -- -13 x 0.25; game choice convention (open S1144)
        } },
        { src = "ex", on = "band", at = 2, list = { -- q 0.50, S0932
            -- a behaviour credit the spec names (s4.5 "exercise improves recovery"; S0826/S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "panicTarget", v = -5.5, row = "S0932", gc = true, bonus = true }, -- -11 x 0.50; game choice (open S1144)
            -- a behaviour credit the spec names (s4.5 "exercise improves recovery"; S0826/S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "unhappyTarget", v = -6.5, row = "S0932", gc = true, bonus = true }, -- -13 x 0.50; game choice (open S1144)
        } },
        { src = "ex", on = "band", at = 3, list = { -- q 0.75, S0932
            -- a behaviour credit the spec names (s4.5 "exercise improves recovery"; S0826/S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "panicTarget", v = -8.25, row = "S0932", gc = true, bonus = true }, -- -11 x 0.75; game choice (open S1144)
            -- a behaviour credit the spec names (s4.5 "exercise improves recovery"; S0826/S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "unhappyTarget", v = -9.75, row = "S0932", gc = true, bonus = true }, -- -13 x 0.75; game choice (open S1144)
        } },
        { src = "ex", on = "band", at = 4, list = { -- q 1, S0932
            -- a behaviour credit the spec names (s4.5 "exercise improves recovery"; S0826/S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "panicTarget", v = -11.0, row = "S0932", gc = true, bonus = true }, -- -11 x 1; game choice (open S1144)
            -- a behaviour credit the spec names (s4.5 "exercise improves recovery"; S0826/S0932), not an adequacy bonus: bonus-flagged so the Severity dial never amplifies it
            { ch = "stat", s = "unhappyTarget", v = -13.0, row = "S0932", gc = true, bonus = true }, -- -13 x 1; game choice (open S1144)
        } },
        -- E3/F2 vitamin D (gated off, ruling 8): unhappiness (S0920 SMD -0.32 per 1000 IU x 22 = 7, halved) and colds
        -- (S0974 OR 0.94: at most 6 %). Semi-starvation mood: no row (S0113 symptom list, open S0937); omega-3: no row.
        { src = "vitD", on = "grade", at = 3, gated = "VITD_EFFECTS", list = { -- depleted, S0920/S0974
            { ch = "stat", s = "unhappyTarget", v = 2, row = "S1145", gc = true }, -- half the clinical rung; game choice (open S1145)
            { ch = "body", s = "coldMul", v = 1.03, row = "S1158", gc = true }, -- half of S0974's 6 %; game choice (open S1158)
        } },
        { src = "vitD", on = "grade", at = 4, gated = "VITD_EFFECTS", list = { -- clinical, S0920/S0974
            { ch = "stat", s = "unhappyTarget", v = 4, row = "S0920", gc = true }, -- 7 halved for small-study bias, as 4; game choice (open S1145)
            { ch = "body", s = "coldMul", v = 1.06, row = "S0974", gc = true }, -- OR 0.94, the spec's 6 % cut; game choice (open S1158)
        } },
        -- B5 the nutritional fatigue offset (fOffNut, capped 0.15): dehydration +0.06 at 2 % linear to +0.10 at 4 %, held
        -- (S0098/S0099 fatigue at 1.36-1.59 %; magnitudes open S0934); hypoglycaemia +0.10 (ruling L7, open S1132).
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
        -- Blood glucose band 3 (below 2.6 mmol/L, S0897): fatigue (B5), speed (D4), temperature (G).
        { src = "bg", on = "band", at = 3, list = { -- below 2.6 mmol/L, S0897
            { ch = "stat", s = "fOffNut", v = 0.10, row = "S1132", gc = true }, -- hypoglycaemia through fatigue (spec); game choice (open S1132)
            { ch = "stat", s = "speedMul", v = 0.85, row = "S1176", gc = true }, -- game choice (open S1176)
            { ch = "stat", s = "tempOffset", v = -0.2, row = "S1014", gc = true }, -- S1014 direction (a listed cause of secondary hypothermia); game choice (open S1161)
        } },
        { src = "bg", on = "band", at = 2, list = { -- [2.6, 3.0) mmol/L, S0897
            { ch = "stat", s = "speedMul", v = 0.92, row = "S1176", gc = true }, -- game choice (open S1176)
        } },
        -- D3 Short Sighted at clinical vitamin A (S0143 the clinical rung, S0144 xerophthalmia follows night blindness).
        { src = "vitA", on = "grade", at = 4, list = { -- clinical, S0143
            { ch = "trait", s = "shortSighted", v = 1, row = "S0143", gc = true }, -- the toggle at clinical; game choice (open S1143)
        } },
        -- D4 the direct speed write (min; computed and mirrored, unapplied until X47).
        { src = "dehyd", on = "band", at = { 7, 8 }, list = { -- 6 % and above, the thirst level-4 region #0509
            { ch = "stat", s = "speedMul", v = 0.85, row = "S1176", gc = true }, -- game choice (open S1176)
        } },
        { src = "iu", on = "band", at = { 20, 25 }, list = { -- 2.0 IU and above, S0750 the unit's anchor
            { ch = "stat", s = "speedMul", v = 0.90, row = "S1176", gc = true }, -- game choice (open S1176)
        } },
        { src = "hypo", on = "band", at = { 2, 3 }, list = { -- below 120 mmol/L, S1047 (CNS symptoms)
            { ch = "stat", s = "speedMul", v = 0.85, row = "S1176", gc = true }, -- game choice (open S1176)
        } },
        -- F2 healing (H_pe, H_c, H_zn), bleeding (vitamin C), infection (protein-energy), colds (C_c, C_e, C_s; C_d above).
        { src = "pe", on = "pe", at = 2, list = { -- protein-energy marginal, S0951/S0954
            { ch = "body", s = "healMul", v = 0.92, row = "S1150", gc = true }, -- game choice (open S1150; PEM healing size open S0129)
            { ch = "body", s = "infectMul", v = 1.15, row = "S1154", gc = true }, -- game choice (open S1154)
        } },
        { src = "pe", on = "pe", at = 3, list = { -- protein-energy depleted, S0951/S0954
            { ch = "body", s = "healMul", v = 0.80, row = "S1150", gc = true }, -- game choice (open S1150)
            { ch = "body", s = "infectMul", v = 1.55, row = "S1154", gc = true }, -- game choice (open S1154)
        } },
        { src = "pe", on = "pe", at = 4, list = { -- protein-energy clinical, S0951/S0954/S0955
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
        { src = "ea", on = "ea", at = 1, list = { -- energy availability [20, 30) kcal/kg LBM, S0691/S0990
            { ch = "body", s = "coldMul", v = 1.3, row = "S1156", gc = true }, -- game choice rung (open S1156)
        } },
        { src = "ea", on = "ea", at = 2, list = { -- [10, 20), S0990 (22 kcal/kg immune markers)
            { ch = "body", s = "coldMul", v = 2.2, row = "S0990", gc = true }, -- game choice rung (open S1156)
        } },
        { src = "ea", on = "ea", at = 3, list = { -- below 10, S0991
            { ch = "body", s = "coldMul", v = 3.0, row = "S0991", gc = true }, -- OR 3.8 the top, taken at the clamp; game choice (open S1156)
        } },
        { src = "debt", on = "band", at = 1, list = { -- debt [4, 8) h, S0993
            { ch = "body", s = "coldMul", v = 1.6, row = "S0993", gc = true }, -- 6-7 h OR 1.66 (NS); the hours-to-debt map a game choice (open S1157)
        } },
        { src = "debt", on = "band", at = 2, list = { -- debt 8 h and more, S0993
            { ch = "body", s = "coldMul", v = 2.5, row = "S0993", gc = true }, -- under 6 h OR 4.24-4.50, damped; game choice (open S1157)
        } },
        -- G thermal: iron-deficiency anaemia (iron's clinical grade) and the exertion-gated dehydration heat side
        -- +0.3 x clamp((d - 2)/2, 0, 1) at the band's lower edge (S1021 linear rise, no slope; 2 %/4 % the spec's knots).
        { src = "iron", on = "grade", at = 4, list = { -- iron clinical (anaemia), S1016
            { ch = "stat", s = "tempOffset", v = -0.2, row = "S1016" }, -- S1016: 36.0 vs 36.2 degrees C; iron-depleted non-anaemic equal controls
        } },
        { src = "dehyd", on = "band", at = 4, list = { -- [2.5, 3) %, S1021
            { ch = "stat", s = "tempHeat", v = 0.075, row = "S1021", gc = true }, -- 0.3 x 0.5/2; game choice magnitude (open S1160)
        } },
        { src = "dehyd", on = "band", at = 5, list = { -- [3, 4) %, S1021
            { ch = "stat", s = "tempHeat", v = 0.15, row = "S1021", gc = true }, -- 0.3 x 1/2; game choice magnitude (open S1160)
        } },
        { src = "dehyd", on = "band", at = { 6, 8 }, list = { -- 4 % and above, S1021
            { ch = "stat", s = "tempHeat", v = 0.3, row = "S1021", gc = true }, -- 0.3 x 1, held; game choice magnitude (open S1160)
        } },
        -- H1 toxicity: FOOD_SICKNESS 30 at rung 1, 55 at rung 2, 85 at rung 3 (ruling T1-1; SICK 1/2/3, #3019), POISON 0.
        -- Rung 1 is the UL rung (every record with an ul); a rung row matches its rung and above, and max keeps the worst.
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
        -- Rung 2: chronic excess held or stored, or an acute rung-2 dose (the records that carry chronic or acute).
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
        { src = "iron", on = "rung", at = 3, list = { -- acute 60 mg/kg, the lethal rung (its drain is K.effects.drain), S1033
            { ch = "stat", s = "foodSickTarget", v = 85, row = "S1033", gc = true }, -- SICK 3, under 90 (#2356); game choice (open S1165)
        } },
        -- H1 hyponatraemia (K.fluids.hyponatGrade, S0102/S1047) and refeeding (S0114/S0117: no drain).
        { src = "hypo", on = "band", at = 2, list = { -- below 120 mmol/L, S1047
            { ch = "stat", s = "foodSickTarget", v = 55, row = "S1047", gc = true }, -- CNS symptoms as sickness; game choice (open S1165)
        } },
        { src = "hypo", on = "band", at = 3, list = { -- below 112 mmol/L, S1047
            { ch = "stat", s = "foodSickTarget", v = 85, row = "S1047", gc = true }, -- with its drain; game choice (open S1165)
        } },
        { src = "refeedEvent", on = "flag", list = {
            { ch = "stat", s = "foodSickTarget", v = 55, row = "S0114", gc = true }, -- fluid shift as sickness, S0117 no mortality; game choice (open S1165)
        } },
    },
}
