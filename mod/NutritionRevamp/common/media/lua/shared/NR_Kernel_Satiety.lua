-- NR_Kernel_Satiety.lua -- satiety from physiology (Plan 11c; spec docs/superpowers/specs/2026-10-08-satiety-physiology-
-- design.md; the meal pool M, spec docs/superpowers/specs/2026-10-12-gut-satiety-design.md § 7). Two signals
-- sate: the stomach's fullness F, counted past the comfortable maximum up to the hard capacity (fill, fullness), and
-- the meal pool M, the weighted kcal eaten, fed in full at the eat and cleared first-order (weigh, mealFeed, mealClear,
-- drain, mealRead, seedMeal); sated(F, mealRead(M)), which K.deficit.hungerTarget turns into hunger (target); the soft
-- cap's discomfort; the appetite traits (HEARTY, LIGHT, trait: vanilla's game numbers, #0485, applied to M's
-- clearance); and the factors on hunger: circadian, the acute suppression of vigorous work, sleep debt and nicotine
-- withdrawal. Plan 11g Task 4 replaced the meal pool P with the gut stage G, fed at emptying, and grouped the file by
-- section, every constant first; Plan 11g Task 6c (spec § 7) went back to the eat feed as M, because G fed at emptying counted
-- the meal's size a second time (the stomach's energy-limited emptying already carries it in F), and let F count past
-- the comfortable maximum. Pure; one statement a line for the coverage gate.
local K = NutritionRevamp.kernel
K.satiety = {}

-- Constants: one line each, resolved from its NR_Data_Dials.lua row (Plan 19), whose comment is its provenance. The joint fit (fit-11g-20261012d: a coordinate refinement over all eight from fix 1's point, until its last rounds moved nothing; fix 1's fit-11g-20261012c searched a full grid of 11,664 points first) set
-- FULL_WEIGHT, LIQUID_WEIGHT, PROTEIN_FILL, W_PROTEIN, W_FAT, MEAL_HALF_LIFE_H, MEAL_REQ and MEAL_STEEP together, loss
-- 0.5782 over the 39 scored oracles of testing/tests/kernel/gut_oracles.py (Tieken read-only; S1233's volume slope scored; S1231's null for water drunk alongside scored and LIQUID_WEIGHT's bound lifted to (0, 1];
-- fix 1's fit-11g-20261012c, loss 0.6719 with LIQUID_WEIGHT held at a bound of 0.19, Task 6c's fit-11g-20261012b, loss 1.3609 with Tieken scored, and the Task 6 fit of the gut stage G, fit-11g-20261012, degenerate, are superseded).
K.satiety.HEARTY = K.dials.get("satiety.HEARTY")
K.satiety.LIGHT = K.dials.get("satiety.LIGHT")
K.satiety.W_PROTEIN = K.dials.get("satiety.W_PROTEIN")
K.satiety.W_CARB = K.dials.get("satiety.W_CARB")
K.satiety.W_FAT = K.dials.get("satiety.W_FAT")
K.satiety.W_NEUTRAL = K.dials.get("satiety.W_NEUTRAL")
K.satiety.MEAL_HALF_LIFE_H = K.dials.get("satiety.MEAL_HALF_LIFE_H")
K.satiety.MEAL_REQ = K.dials.get("satiety.MEAL_REQ")
K.satiety.MEAL_STEEP = K.dials.get("satiety.MEAL_STEEP")
K.satiety.MEAL_SEED_MAX = K.dials.get("satiety.MEAL_SEED_MAX")
K.satiety.FULL_WEIGHT = K.dials.get("satiety.FULL_WEIGHT")
K.satiety.LIQUID_WEIGHT = K.dials.get("satiety.LIQUID_WEIGHT")
K.satiety.BETA = K.dials.get("satiety.BETA")
K.satiety.PROTEIN_FILL = K.dials.get("satiety.PROTEIN_FILL")
K.satiety.DISCOMFORT_MAX = K.dials.get("satiety.DISCOMFORT_MAX")
K.satiety.ATWATER_P = K.dials.get("satiety.ATWATER_P")
K.satiety.ATWATER_C = K.dials.get("satiety.ATWATER_C")
K.satiety.ATWATER_F = K.dials.get("satiety.ATWATER_F")
K.satiety.CIRCADIAN_A = K.dials.get("satiety.CIRCADIAN_A")
K.satiety.CIRCADIAN_PEAK_H = K.dials.get("satiety.CIRCADIAN_PEAK_H")
K.satiety.ACUTE_MAX = K.dials.get("satiety.ACUTE_MAX")
K.satiety.ACUTE_HALF_LIFE_H = K.dials.get("satiety.ACUTE_HALF_LIFE_H")
K.satiety.ACUTE_DECAY_HALF_LIFE_H = K.dials.get("satiety.ACUTE_DECAY_HALF_LIFE_H")
K.satiety.ACUTE_KIND = {}
K.satiety.ACUTE_KIND.aerobic = K.dials.get("satiety.ACUTE_KIND.aerobic")
K.satiety.ACUTE_KIND.resistance = K.dials.get("satiety.ACUTE_KIND.resistance")
K.satiety.ACUTE_KIND.walk = K.dials.get("satiety.ACUTE_KIND.walk")
K.satiety.SLEEP_MAX = K.dials.get("satiety.SLEEP_MAX")
K.satiety.SLEEP_SHORT_H = K.dials.get("satiety.SLEEP_SHORT_H")
K.satiety.NIC_MAX = K.dials.get("satiety.NIC_MAX")
K.satiety.NIC_FADE_DAYS = K.dials.get("satiety.NIC_FADE_DAYS")
K.satiety.NIC_WITHDRAWAL_MAX = K.dials.get("satiety.NIC_WITHDRAWAL_MAX")
K.satiety.SLEEP_DEBT_FULL_H = K.acute.SLEEP_NEED_H - K.satiety.SLEEP_SHORT_H -- derived: the debt the acute kernel books for one night of SLEEP_SHORT_H, 7.5 - 5.5 the double 2.0

-- Fullness: the stomach's F (spec § 3.1; Plan 11g spec § 7).
-- The physical fill: a mass over a capacity, clamped to [0, 1]; K.stomach.fill passes the whole mass, both lanes at
-- density 1, over K.stomach.CAPACITY_MAX_G, fullness being linear in gastric volume up to the
-- tolerated maximum. record.stomachFill stays this physical fill; the satiety F below is not clamped at 1.
function K.satiety.fill(mass, capacity)
    return K.clamp(mass / capacity, 0, 1)
end

-- The F a stomach sates with: its fullness mass (K.stomach.fullnessMass, the satiety mass plus PROTEIN_FILL x the solid
-- lane's protein) over K.stomach.CAPACITY_MAX_G, clamped to [0, CAPACITY_HARD_G /
-- CAPACITY_MAX_G] (1100 / 730 = 1.507; Plan 11g spec § 7): fullness keeps rising past the tolerated maximum up to
-- maximal discomfort (S1250, S1253), so a well-fed stomach past 730 g sates more than one at it, where a clamp at 1
-- read Karl 2021's resting and well-fed post-meal stomachs alike (harvest 13: BAL's emptying 612 min against 182,
-- S1874). Protein fills while it is in the stomach and leaves with the lane's energy, so the term fades as the meal
-- empties; no row names gastric fullness from protein, so PROTEIN_FILL is a game choice fitted with FULL_WEIGHT and the
-- read's exponent (ruling 11c-31's request-anchored mapping, an assumption). The writer's W.satietyF and the replays
-- read it; the soft cap's discomfort and the Overfull moodle read the mass (K.view.fullnessLevel), never F.
function K.satiety.fullness(stomach)
    local cap = K.stomach.CAPACITY_MAX_G
    return K.clamp(K.stomach.fullnessMass(stomach) / cap, 0, K.stomach.CAPACITY_HARD_G / cap)
end

-- The meal pool M, the weighted kcal eaten, fed at the eat (spec § 7).
-- The intake feeds M in full at the eat with the landed vector's weighted kcal (mealFeed; NR_Server_Intake's IN.feed, on
-- every route that lands); the kinetics step clears it first-order on every one-minute substep of the stomach's drain
-- (drain), and the writer seeds M and reads it. The meal pool P was fed the same
-- way; Plan 11g Task 4's gut stage G, fed with what the stomach emptied, fitted flat and was withdrawn.
-- A vector's weighted kcal: its delivered calories split by the Atwater share of its protein, carbohydrate and fat
-- grams, each share times its weight; a vector with no macronutrient grams takes the neutral weight.
function K.satiety.weigh(vector)
    local p = K.satiety.ATWATER_P * vector.proteins
    local c = K.satiety.ATWATER_C * vector.carbs
    local f = K.satiety.ATWATER_F * vector.lipids
    local atwater = p + c + f
    if atwater <= 0 then
        return vector.calories * K.satiety.W_NEUTRAL
    end
    return vector.calories * (K.satiety.W_PROTEIN * p + K.satiety.W_CARB * c + K.satiety.W_FAT * f) / atwater
end

-- Feed M with an eaten vector: its weighted kcal, in full at the eat.
function K.satiety.mealFeed(M, vector)
    return M + K.satiety.weigh(vector)
end

-- First-order clearance over dtH game hours at MEAL_HALF_LIFE_H, scaled by trait (the appetite trait times the sandbox's
-- stats-decrease multiplier); nothing for no time. No asleep factor: the same clearance asleep and awake.
function K.satiety.mealClear(M, dtH, trait)
    if dtH <= 0 then
        return M
    end
    return M * math.exp(-0.6931471805599453 * dtH * trait / K.satiety.MEAL_HALF_LIFE_H)
end

-- The stomach's drain over dtM game minutes in ceil(dtM) equal substeps of at most one minute (Plan 11c Task 6
-- amendment 5; moved here from KIN.drain in Plan 11g Task 6), the emptied vectors summed into the first, which is
-- returned. pool is nil or a {M, trait} state whose M is cleared over each substep (mealClear; nothing feeds it here:
-- the eat does). A float one-minute gap (60 x 1/60 h, or a stamp a 14-digit slot rounded) is one substep (ruling
-- T4-4). Kinetics calls it with the step the pipeline bounds (K.resume.STEP_M), and the replays' stand-ins call it, so every path splits a step alike.
function K.satiety.drain(stomach, dtM, pool)
    local n = math.ceil(dtM - 1e-6)
    if n < 1 then
        n = 1
    end
    local dtH = dtM / n / 60
    local emptied = K.stomach.drain(stomach, dtH)
    if pool ~= nil then
        pool.M = K.satiety.mealClear(pool.M, dtH, pool.trait)
    end
    for i = 2, n do
        local e = K.stomach.drain(stomach, dtH)
        if pool ~= nil then
            pool.M = K.satiety.mealClear(pool.M, dtH, pool.trait)
        end
        K.vector.add(emptied, e, 1)
    end
    return emptied
end

-- The appetite trait's factor on M's clearance (#0485): HEARTY for a hearty appetite, LIGHT for a light eater, else 1.
function K.satiety.trait(hearty, light)
    if hearty then
        return K.satiety.HEARTY
    end
    if light then
        return K.satiety.LIGHT
    end
    return 1
end

-- The read and composition (Plan 11c structure D; Plan 11g spec § 7).
-- M's read 1 - 1 / (1 + 3 (M / MEAL_REQ)^MEAL_STEEP), in [0, 1): 3 = (1 - 0.25) / 0.25, so an empty stomach reads the
-- request level 0.25 at M = MEAL_REQ; MEAL_STEEP makes the read near-logarithmic.
function K.satiety.mealRead(M)
    if M <= 0 then
        return 0
    end
    local x = math.exp(K.satiety.MEAL_STEEP * math.log(M / K.satiety.MEAL_REQ))
    return 1 - 1 / (1 + 3 * x)
end

-- Sated: either signal sates and together they compound, 1 - (1 - FULL_WEIGHT x F) x (1 - Mn), clamped to [0, 1]:
-- with F counted to the hard capacity, FULL_WEIGHT x F passes 1 only for a FULL_WEIGHT above 730 / 1100 (the fitted 0.518 reaches 0.780), and the clamp keeps the product in [0, 1] under any fit (spec § 7).
function K.satiety.sated(F, Mn)
    return K.clamp(1 - (1 - K.satiety.FULL_WEIGHT * F) * (1 - Mn), 0, 1)
end

-- The hunger target before the factors: K.deficit.hungerTarget(sated(F, mealRead(M)), energyState). The writer multiplies
-- it by circadian(hour) x acuteFactor(S) x nicotineFactor x sleepFactor(debtH), writes it through the calibrated curve (K.hungerCurve.write) and caps it (K.hybrid.caps); the replays read it.
function K.satiety.target(F, M, energyState)
    return K.deficit.hungerTarget(K.satiety.sated(F, K.satiety.mealRead(M)), energyState)
end

-- The seed (spec § 4; Plan 11g spec § 3.3): the M for which target(F, M, energyState) equals hunger, the inverse of
-- mealRead, MEAL_REQ (mn / (3 (1 - mn)))^(1 / MEAL_STEEP), capped at MEAL_SEED_MAX; 0 where no M reaches it (a
-- fullness at or past 1 / FULL_WEIGHT sates fully alone; F reaches it only for a FULL_WEIGHT above 730 / 1100), and 0 for a
-- non-finite input (K.finite), so a bad read never loops NaN through M.
function K.satiety.seedMeal(hunger, F, energyState)
    if not K.finite(hunger) or not K.finite(F) or not K.finite(energyState) then
        return 0
    end
    if energyState <= 0 then
        return 0
    end
    local free = K.deficit.unsated(hunger, energyState)
    local rest = 1 - K.satiety.FULL_WEIGHT * F
    if rest <= 0 then
        return 0
    end
    local mn = 1 - free / rest
    if mn <= 0 then
        return 0
    end
    if mn >= 1 then
        return K.satiety.MEAL_SEED_MAX
    end
    local M = K.satiety.MEAL_REQ * math.exp(math.log(mn / (3 * (1 - mn))) / K.satiety.MEAL_STEEP)
    return K.min(M, K.satiety.MEAL_SEED_MAX)
end

-- Discomfort: the soft cap's scale (the Overfull moodle's level reads it through K.view.fullnessLevel;
-- nothing writes DISCOMFORT): 0 up to capMax grams, DISCOMFORT_MAX at capHard, linear between.
function K.satiety.discomfort(mass, capMax, capHard)
    return K.satiety.DISCOMFORT_MAX * K.clamp((mass - capMax) / (capHard - capMax), 0, 1)
end

-- The circadian, acute, sleep and nicotine factors on hunger.
-- The circadian factor on hunger at hourOfDay (0-24, the game clock): 1 + CIRCADIAN_A x
-- cos(2 pi (hourOfDay - CIRCADIAN_PEAK_H) / 24), peaking at 19:50 and troughing at 07:50 (the multiplicative form and the game-clock phase are game choices; Scheer's model is additive). The writer applies
-- keeps hungerTarget(Z, es) x circadian(h) x acuteFactor(S) x sleepFactor(debtH) x nicotineFactor(w, d) as h_model and writes it through K.hungerCurve under K.hybrid.caps, awake and asleep.
-- The hour is the body clock's (K.circadian.hour, Plan 16); nil, with sleep off, is no rhythm: the factor is 1 (a game
-- choice, Plan 16 spec section 6: the server has no sleep cycle and vanilla no hunger rhythm, so S1273 is set aside there).
function K.satiety.circadian(hourOfDay)
    if hourOfDay == nil then
        return 1
    end
    return 1 + K.satiety.CIRCADIAN_A * math.cos(6.283185307179586 * (hourOfDay - K.satiety.CIRCADIAN_PEAK_H) / 24)
end

-- Spec § 5c: the acute suppression of hunger by vigorous work (exercise-induced
-- anorexia: during and just after the bout, gone within about 1.5 h; S1299, S1300, S1303, S1304, S1305, S1306). A
-- state S in [0, 1] relaxes toward the kind's weight while vigorous and toward 0 otherwise, first-order with
-- ACUTE_HALF_LIFE_H while vigorous and ACUTE_DECAY_HALF_LIFE_H otherwise; the writer multiplies hunger by acuteFactor(S) = 1 - ACUTE_MAX x S (Task 6
-- wires it: vigorous is the swing state or the metabolism class's heavy-work band, IsRunning never reaching the
-- server, x141a).
-- One step of dtH game hours: toward the kind's weight while vigorous (an unknown kind weighs 0), toward 0 otherwise;
-- nothing for no time (the state returned clamped to [0, 1]); a non-finite state reads 0.
function K.satiety.exerciseSuppression(S, dtH, vigorous, kind)
    if not K.finite(S) then
        S = 0
    end
    if not (dtH > 0) then
        return K.clamp(S, 0, 1)
    end
    local w = 0
    if vigorous then
        w = K.satiety.ACUTE_KIND[kind or "none"] or 0
    end
    local k = math.exp(-0.6931471805599453 * dtH / K.satiety.acuteHalfLife(vigorous))
    return K.clamp(w + (S - w) * k, 0, 1)
end

-- The factor on hunger: 1 - ACUTE_MAX x S, S read as 0 when non-finite and clamped to [0, 1].
function K.satiety.acuteFactor(S)
    if not K.finite(S) then
        S = 0
    end
    return 1 - K.satiety.ACUTE_MAX * K.clamp(S, 0, 1)
end

-- The half-life of exerciseSuppression's step, the rise's while vigorous and the shorter
-- decay's otherwise.
function K.satiety.acuteHalfLife(vigorous)
    if vigorous then
        return K.satiety.ACUTE_HALF_LIFE_H
    end
    return K.satiety.ACUTE_DECAY_HALF_LIFE_H
end

-- Spec § 5d: sleep debt raises hunger. The factor 1 + SLEEP_MAX x clamp(debtH /
-- SLEEP_DEBT_FULL_H, 0, 1) multiplies the written hunger, read off record.acute.debtH in game hours (wired in the writer's W.satietyFactor); it is inert while the server disables sleep, K.acute.sleepMinute holding the debt at 0.
-- It follows the acute kernel's accounting (K.acute.sleepMinute): the debt books once per 24 h window at the window's
-- close, as the shortfall against SLEEP_NEED_H x needFactor, so the factor steps at the window's close rather than at
-- waking; a longer night repays only REPAY (0.5) of its excess, so recovery takes more than one full night. It
-- reverses as the debt is repaid (S1567: intake fell on recovery sleep). Whether hunger steps with any short night or
-- rises graded with the loss is not settled (S1568: total and partial loss gave comparable late-night intake; S1282:
-- hunger 3.9 after total deprivation against 2.2 after 4.5 h and 1.7 after 7 h: only total deprivation differed significantly; 4.5 h against 7 h is not tested in the row), so the
-- ramp to a full debt and its cap are game choices.
-- The factor on hunger for a sleep debt of debtH game hours: 1 for no debt, a negative one or a non-finite one
-- (K.finite), rising linearly to 1 + SLEEP_MAX at SLEEP_DEBT_FULL_H and held there.
function K.satiety.sleepFactor(debtH)
    if not K.finite(debtH) then
        return 1
    end
    return 1 + K.satiety.SLEEP_MAX * K.clamp(debtH / K.satiety.SLEEP_DEBT_FULL_H, 0, 1)
end

-- Spec memo C12: nicotine withdrawal raises hunger. The factor 1 + NIC_MAX x
-- clamp(w / NIC_WITHDRAWAL_MAX, 0, 1) x fade(d) multiplies the written hunger, where w is the server's own
-- NICOTINE_WITHDRAWAL (a Smoker's, rising on the server alone (#3630, #3631), or a former Smoker's, held where it stood; vanilla reads it only
-- as stress, #3635) and d the game days since the mod's own anchor, the last minute the stat read 0 or fell (a smoke
-- lowers it, #3632; the writer's W.nicotine keeps it as record.satiety.nicH, because the vanilla timer's
-- units move with the time speed, #3636). The fade is linear, 1 at d = 0 and 0 at NIC_FADE_DAYS. A first or healed anchor laid in withdrawal starts fully faded.
-- A character who keeps smoking keeps resetting the anchor, so between smokes the factor stays at its withdrawal-scaled
-- level and never fades while the habit continues; only a quit runs the fade.
-- The factor on hunger for a withdrawal w (the stat's value) d game days after the anchor: 1 for a non-finite input
-- (K.finite), for no withdrawal (w <= 0) and for a negative d; otherwise
-- 1 + NIC_MAX x clamp(w / NIC_WITHDRAWAL_MAX, 0, 1) x clamp(1 - d / NIC_FADE_DAYS, 0, 1).
function K.satiety.nicotineFactor(w, d)
    if not K.finite(w) or not K.finite(d) then
        return 1
    end
    if w <= 0 or d < 0 then
        return 1
    end
    local fade = K.clamp(1 - d / K.satiety.NIC_FADE_DAYS, 0, 1)
    return 1 + K.satiety.NIC_MAX * K.clamp(w / K.satiety.NIC_WITHDRAWAL_MAX, 0, 1) * fade
end
