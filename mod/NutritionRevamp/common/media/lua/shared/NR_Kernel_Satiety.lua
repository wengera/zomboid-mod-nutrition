-- NR_Kernel_Satiety.lua -- satiety from physiology (Plan 11c; spec docs/superpowers/specs/2026-10-08-satiety-physiology-
-- design.md). Structure D: the stomach's fullness F (fill), the meal pool P of weighted kcal (weigh, feed, decay, post,
-- seedP) and sated(F, post(P)), which K.hybrid.hungerTarget turns into hunger; the soft cap's discomfort; the circadian
-- factor on hunger (CIRCADIAN_*); the acute suppression of hunger by vigorous work (ACUTE_*, exerciseSuppression,
-- acuteFactor); and the appetite traits (HEARTY, LIGHT, trait: vanilla's game numbers, #0485, applied to P's decay).
-- Task 15's vanilla-keyed scalar retired in Plan 11c Task 9. Pure; one statement a line for the coverage gate.
local K = NutritionRevamp.kernel
K.satiety = {}

K.satiety.HEARTY = 1.5 -- #0485: vanilla's game number, not science (spec sec. 3.4)
K.satiety.LIGHT = 0.75 -- #0485: vanilla's game number, not science (spec sec. 3.4)

function K.satiety.trait(hearty, light)
    if hearty then
        return K.satiety.HEARTY
    end
    if light then
        return K.satiety.LIGHT
    end
    return 1
end

-- Plan 11c (spec § 3.1, § 5a and § 5b, structure D, ruling 11c-30): satiety from physiology. Two signals sate: the
-- stomach's fullness F (its satiety mass, K.stomach.satietyMass, over its maximal capacity, K.stomach.CAPACITY_MAX_G,
-- ruling 11c-19) and a meal satiety pool P of weighted kcal, fed at the eat and decaying first-order. Hunger is
-- K.hybrid.hungerTarget(sated(F, post(P)), energyState) x circadian(hour) x acuteFactor(S), capped at 0.69 by the writer.
K.satiety.W_PROTEIN = 2.5 -- game choice, fitted in Task 4 (Plan 11c), kept at 2.5 and bounded by S1224's delay differences (Plan 11c Task 4 review) (S1268 open; rulings 11c-7 and 11c-31): protein satiates more per kcal (S1222, S1223, S1224, direction)
K.satiety.W_CARB = 1 -- neutral (ruling 11c-7): carbohydrate against fat is disputed (S1226, S1227, S1228, S1229), so both take the common weight; not an evidenced tie
K.satiety.W_FAT = 1 -- neutral (ruling 11c-7), as W_CARB
K.satiety.W_NEUTRAL = 1 -- neutral (spec § 3.1): the common weight of a vector with no macronutrient grams
K.satiety.HALF_LIFE_H = 0.7 -- game choice, fitted in Task 4 (Plan 11c) (S1270 open): P's half-life in game hours, fitted with P_REQ and STEEP against S1247 (Callahan's preloads from the request and fasted), the 650 kcal anchor (S1247, S1248), a fasted 400 kcal breakfast and S1231 (Rolls's soup at its measured size)
K.satiety.P_REQ = 6 -- game choice, fitted in Task 4 (Plan 11c) (S1270 open): the pool in weighted kcal at which an empty stomach reads the request level 0.25, fitted with HALF_LIFE_H and STEEP (S1247, S1248, S1231)
K.satiety.STEEP = 0.08 -- game choice, fitted in Task 4 (Plan 11c) (S1270 open; no row gives a satiety signal's read): the read's exponent, near-logarithmic so a snack leaves hunger intermediate while the interval grows with the log of the meal (S1247)
K.satiety.FULL_WEIGHT = 0.6 -- game choice, fitted in Task 4 (Plan 11c): fullness's weight in the sated product, fitted to S1231's three arms and checked against S1233; S1235 has fullness track gastric volume
K.satiety.LIQUID_WEIGHT = 0.2 -- game choice, fitted in Task 4 (Plan 11c): drunk liquid's weight in the satiety mass (K.stomach.satietyMass), between S1231 (water drunk alongside did not affect satiety) and S1233 (a drink's volume moved intake)
K.satiety.P_SEED_MAX = 1300 -- game choice (ruling 11c-30): seedP's cap, about the weighted pool of a 1,000 kcal mixed meal, so a HUNGER of 0 does not seed a pool that sates for days
K.satiety.DISCOMFORT_MAX = 100 -- not science: the soft cap's discomfort scale, borrowed from the DISCOMFORT stat's range 0-100 (CharacterStat.<clinit> registers 'Discomfort' with 0.0 and 100.0; Task 5 cites it on 42.21); ruling 11c-25: the Overfull moodle's level reads it through K.view.fullnessLevel and nothing writes DISCOMFORT
K.satiety.ATWATER_P = 4 -- S1209 (Atwater general factors: protein 4.0 kcal/g)
K.satiety.ATWATER_C = 4 -- S1209 (carbohydrate 4.0 kcal/g)
K.satiety.ATWATER_F = 9 -- S1209 (fat 9.0 kcal/g)
K.satiety.CIRCADIAN_A = 0.085 -- labelled inference (ruling 11c-24; S1273): the cosine's amplitude, half of Scheer 2013's 17 % peak-to-trough of hunger; the halving is the plan's own arithmetic; the multiplicative form and the game-clock phase are game choices (ruling 11c-24a; Scheer's model is additive)
K.satiety.CIRCADIAN_PEAK_H = 19.8333 -- S1273 (ruling 11c-24): Scheer 2013's circadian hunger peak at 19:50 (trough 07:50), in game hours of the day

-- The fullness F: mass over capacity, clamped to [0, 1] (liquid and food taken at density 1, ruling 11c-8); K.stomach.fill
-- passes K.stomach.CAPACITY_MAX_G, fullness being linear in gastric volume up to the tolerated maximum (ruling 11c-19).
function K.satiety.fill(mass, capacity)
    return K.clamp(mass / capacity, 0, 1)
end

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

-- Feed the pool with the vector eaten: called once per eat or drink with the delivered vector, never per minute.
function K.satiety.feed(P, vector)
    return P + K.satiety.weigh(vector)
end

-- First-order decay over dtH game hours at the half-life, scaled by trait (the appetite trait times the sandbox's
-- stats-decrease multiplier, ruling 11c-11); nothing for no time. No asleep factor: the same decay asleep and awake (ruling 11c-24).
function K.satiety.decay(P, dtH, halfLifeH, trait)
    if dtH <= 0 then
        return P
    end
    return P * math.exp(-0.6931471805599453 * dtH * trait / halfLifeH)
end

-- The pool's read 1 - 1 / (1 + 3 (P / P_REQ)^STEEP), in [0, 1): 3 = (1 - 0.25) / 0.25, so an empty stomach reads the
-- request level 0.25 at P = P_REQ; STEEP makes the read near-logarithmic.
function K.satiety.post(P)
    if P <= 0 then
        return 0
    end
    local x = math.exp(K.satiety.STEEP * math.log(P / K.satiety.P_REQ))
    return 1 - 1 / (1 + 3 * x)
end

-- Sated: either signal sates and together they compound, 1 - (1 - FULL_WEIGHT x F) x (1 - Pn).
function K.satiety.sated(F, Pn)
    return 1 - (1 - K.satiety.FULL_WEIGHT * F) * (1 - Pn)
end

-- The migration seed (spec § 4): the P for which hungerTarget(sated(F, post(P)), energyState) equals hunger, the
-- inverse of post, P_REQ (pn / (3 (1 - pn)))^(1 / STEEP), capped at P_SEED_MAX; 0 where no P reaches it, and 0 for a
-- non-finite input (x - x is NaN for NaN and for an infinity), so a bad read never loops NaN through the pool.
function K.satiety.seedP(hunger, F, energyState)
    if hunger - hunger ~= 0 or F - F ~= 0 or energyState - energyState ~= 0 then
        return 0
    end
    if energyState <= 0 then
        return 0
    end
    local free = (hunger - K.hybrid.DEFICIT_FLOOR * K.max(0, energyState - 1)) / energyState
    local rest = 1 - K.satiety.FULL_WEIGHT * F
    if rest <= 0 then
        return 0
    end
    local pn = 1 - free / rest
    if pn <= 0 then
        return 0
    end
    if pn >= 1 then
        return K.satiety.P_SEED_MAX
    end
    local P = K.satiety.P_REQ * math.exp(math.log(pn / (3 * (1 - pn))) / K.satiety.STEEP)
    return K.min(P, K.satiety.P_SEED_MAX)
end

-- The soft cap's discomfort scale (ruling 11c-25: the Overfull moodle's level reads it through K.view.fullnessLevel; nothing writes DISCOMFORT): 0 up to capMax grams, DISCOMFORT_MAX at capHard, linear between.
function K.satiety.discomfort(mass, capMax, capHard)
    return K.satiety.DISCOMFORT_MAX * K.clamp((mass - capMax) / (capHard - capMax), 0, 1)
end

-- The circadian factor on hunger at hourOfDay (0-24, the game clock; ruling 11c-24): 1 + CIRCADIAN_A x
-- cos(2 pi (hourOfDay - CIRCADIAN_PEAK_H) / 24), peaking at 19:50 and troughing at 07:50 (the multiplicative form and the game-clock phase are game choices, ruling 11c-24a; Scheer's model is additive). The writer applies
-- min(0.69, hungerTarget(Z, es) x circadian(h) x acuteFactor(S)), awake and asleep.
function K.satiety.circadian(hourOfDay)
    return 1 + K.satiety.CIRCADIAN_A * math.cos(6.283185307179586 * (hourOfDay - K.satiety.CIRCADIAN_PEAK_H) / 24)
end

-- Plan 11c Task 4b (spec § 5c, ruling 11c-29): the acute suppression of hunger by vigorous work (exercise-induced
-- anorexia: during and just after the bout, gone within about 1.5 h; S1299, S1300, S1303, S1304, S1305, S1306). A
-- state S in [0, 1] relaxes toward the kind's weight while vigorous and toward 0 otherwise, first-order with one
-- half-life for the rise and the decay; the writer multiplies hunger by acuteFactor(S) = 1 - ACUTE_MAX x S (Task 6
-- wires it: vigorous is the swing state or the metabolism class's heavy-work band, IsRunning never reaching the
-- server, x141a). Appended so no line above moves. Pure; one statement a line.
K.satiety.ACUTE_MAX = 0.7 -- game choice, fitted in Task 4b (Plan 11c) (S1334 open): with ACUTE_HALF_LIFE_H, to S1303 (Douglas 2017: ES >= 0.60 at 0.5, 1.0 and 1.5 h of a trial whose bout ran 0-1 h) and S1306 (Goltz 2018: ES 0.62-1.47 just after a 60 min run), under the request-anchored mapping (ruling 11c-31: 65 mm read as 0.25, an assumption) and an SD of 25.7 mm read off S1303's main effect (an inference)
K.satiety.ACUTE_HALF_LIFE_H = 0.5 -- game choice, fitted in Task 4b (Plan 11c) (S1334 open): the state's half-life in game hours, rise and decay, a compromise between S1303's reading (no effect 30 min after the bout) and S1305 / S1304's return to control within 30-60 min; a limitation: the model still shows ES 0.33 at trial hour 2.0, 30 min after the bout, where S1303 shows no effect
K.satiety.ACUTE_KIND = {}
K.satiety.ACUTE_KIND.aerobic = 1 -- S1300, S1303, S1306: running suppresses hunger (the weight is the scale's unit)
K.satiety.ACUTE_KIND.resistance = 0.5 -- game choice (S1301: suppressed during resistance work too; S1305: less marked and not observed consistently), the swing state
K.satiety.ACUTE_KIND.walk = 0 -- S1302: brisk walking did not move appetite

-- One step of dtH game hours: toward the kind's weight while vigorous (an unknown kind weighs 0), toward 0 otherwise;
-- nothing for no time (the state returned clamped to [0, 1]); a non-finite state reads 0.
function K.satiety.exerciseSuppression(S, dtH, vigorous, kind)
    if S - S ~= 0 then
        S = 0
    end
    if not (dtH > 0) then
        return K.clamp(S, 0, 1)
    end
    local w = 0
    if vigorous then
        w = K.satiety.ACUTE_KIND[kind or "none"] or 0
    end
    local k = math.exp(-0.6931471805599453 * dtH / K.satiety.ACUTE_HALF_LIFE_H)
    return K.clamp(w + (S - w) * k, 0, 1)
end

-- The factor on hunger: 1 - ACUTE_MAX x S, S read as 0 when non-finite and clamped to [0, 1].
function K.satiety.acuteFactor(S)
    if S - S ~= 0 then
        S = 0
    end
    return 1 - K.satiety.ACUTE_MAX * K.clamp(S, 0, 1)
end
