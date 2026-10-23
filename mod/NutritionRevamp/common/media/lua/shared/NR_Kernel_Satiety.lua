-- NR_Kernel_Satiety.lua: satiety from physiology (docs/superpowers/specs/2026-10-12-gut-satiety-design.md@program-record-v19
-- section 7). Two signals sate: the stomach's fullness F, counted past the comfortable maximum to the hard capacity, and
-- the meal pool M, the weighted kcal eaten. M is fed in full at the eat, never at emptying, which would count
-- the meal's size a second time (the stomach's energy-limited emptying already carries it in F).
-- Also the appetite traits and the factors on hunger. Pure; one statement a line for the coverage gate.
local K = NutritionRevamp.kernel
K.satiety = {}

-- Constants: each one's provenance is its NR_Data_Dials.lua row. Eight were fitted jointly (fit-11g-20261012d), loss
-- 0.5782 over the 39 scored oracles of testing/tests/kernel/gut_oracles.py: retune them together.
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
K.satiety.SLEEP_DEBT_FULL_H = K.acute.SLEEP_NEED_H - K.satiety.SLEEP_SHORT_H -- derived: the debt the acute kernel books for one night of SLEEP_SHORT_H

-- Fullness: record.stomachFill stays this physical fill, clamped at 1; the satiety F below is not.
function K.satiety.fill(mass, capacity)
    return K.clamp(mass / capacity, 0, 1)
end

-- F runs past 1 to CAPACITY_HARD_G / CAPACITY_MAX_G, since fullness keeps rising to maximal discomfort (S1250); a clamp
-- at 1 read resting and well-fed stomachs alike. PROTEIN_FILL is a game choice: no row names fullness from protein.
-- The soft cap and the Overfull moodle read the mass (K.view.fullnessLevel), never F.
function K.satiety.fullness(stomach)
    local cap = K.stomach.CAPACITY_MAX_G
    return K.clamp(K.stomach.fullnessMass(stomach) / cap, 0, K.stomach.CAPACITY_HARD_G / cap)
end

-- The meal pool M, fed at the eat (NR_Server_Intake's IN.feed) and cleared first-order in the drain below.
-- A vector's weighted kcal: its calories split by Atwater share, each share times its weight; no grams take W_NEUTRAL.
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

function K.satiety.mealFeed(M, vector)
    return M + K.satiety.weigh(vector)
end

-- trait is the appetite trait times the sandbox's stats-decrease multiplier; no asleep factor.
function K.satiety.mealClear(M, dtH, trait)
    if dtH <= 0 then
        return M
    end
    return M * math.exp(-0.6931471805599453 * dtH * trait / K.satiety.MEAL_HALF_LIFE_H)
end

-- ceil(dtM) equal substeps of at most one minute, the emptied vectors summed into the first; a float one-minute gap is
-- one substep (ruling T4-4). Kinetics and the replays' stand-ins both call it, so every path splits a step alike.
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

-- #0485: HEARTY for a hearty appetite, LIGHT for a light eater, else 1.
function K.satiety.trait(hearty, light)
    if hearty then
        return K.satiety.HEARTY
    end
    if light then
        return K.satiety.LIGHT
    end
    return 1
end

-- The read and composition. 3 = (1 - 0.25) / 0.25, so an empty stomach reads the request level 0.25 at M = MEAL_REQ.
function K.satiety.mealRead(M)
    if M <= 0 then
        return 0
    end
    local x = math.exp(K.satiety.MEAL_STEEP * math.log(M / K.satiety.MEAL_REQ))
    return 1 - 1 / (1 + 3 * x)
end

-- Either signal sates and together they compound; F passes 1, so the clamp keeps the product in [0, 1].
function K.satiety.sated(F, Mn)
    return K.clamp(1 - (1 - K.satiety.FULL_WEIGHT * F) * (1 - Mn), 0, 1)
end

-- The writer multiplies this by the factors below, writes it through K.hungerCurve and caps it (K.hybrid.caps).
function K.satiety.target(F, M, energyState)
    return K.deficit.hungerTarget(K.satiety.sated(F, K.satiety.mealRead(M)), energyState)
end

-- The seed: mealRead's inverse, capped at MEAL_SEED_MAX; 0 where no M reaches hunger or for a non-finite input, so a
-- bad read never loops NaN through M.
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

-- Discomfort: the soft cap's scale; nothing writes DISCOMFORT (the Overfull level reads it through K.view.fullnessLevel).
function K.satiety.discomfort(mass, capMax, capHard)
    return K.satiety.DISCOMFORT_MAX * K.clamp((mass - capMax) / (capHard - capMax), 0, 1)
end

-- The circadian, acute, sleep and nicotine factors.
-- 1 + CIRCADIAN_A x cos(2 pi (hourOfDay - CIRCADIAN_PEAK_H) / 24), peaking at 19:50 (the form is a game choice). The
-- hour is the body clock's (K.circadian.hour); nil, with sleep off, is no rhythm, since the server has no sleep cycle.
function K.satiety.circadian(hourOfDay)
    if hourOfDay == nil then
        return 1
    end
    return 1 + K.satiety.CIRCADIAN_A * math.cos(6.283185307179586 * (hourOfDay - K.satiety.CIRCADIAN_PEAK_H) / 24)
end

-- Exercise-induced anorexia (S1299): S relaxes toward the kind's weight while vigorous, toward 0 otherwise. Vigorous is
-- the swing state or the heavy-work band, since IsRunning never reaches the server.
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

function K.satiety.acuteFactor(S)
    if not K.finite(S) then
        S = 0
    end
    return 1 - K.satiety.ACUTE_MAX * K.clamp(S, 0, 1)
end

function K.satiety.acuteHalfLife(vigorous)
    if vigorous then
        return K.satiety.ACUTE_HALF_LIFE_H
    end
    return K.satiety.ACUTE_DECAY_HALF_LIFE_H
end

-- Sleep debt raises hunger (S1567), read off record.acute.debtH; inert while the server disables sleep. The debt books
-- at the 24 h window's close (K.acute.sleepMinute), so the factor steps there, not at waking. The ramp and its cap are
-- game choices: whether hunger is graded with the loss is not settled (S1568, S1282).
function K.satiety.sleepFactor(debtH)
    if not K.finite(debtH) then
        return 1
    end
    return 1 + K.satiety.SLEEP_MAX * K.clamp(debtH / K.satiety.SLEEP_DEBT_FULL_H, 0, 1)
end

-- Nicotine withdrawal raises hunger. w is the server's own NICOTINE_WITHDRAWAL, which rises on the server alone (#3630);
-- d counts game days from the mod's anchor (record.satiety.nicH), since the vanilla timer's units move with the time
-- speed. A character who keeps smoking keeps resetting the anchor, so only a quit runs the fade; an anchor laid in withdrawal starts fully faded.
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
