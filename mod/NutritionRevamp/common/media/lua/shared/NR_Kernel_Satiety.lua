-- NR_Kernel_Satiety.lua -- the satiety scalar S (Plan 11 Task 15; Decision 2 (c), Appendix D): vanilla's hunger as
-- 1 - S, decayed by vanilla's own rates and its FOOD_EATEN freeze, raised by a meal's relief |getHungerChange| x f
-- (the laddered getter; J1) with the meal's bulk scaling the applied relief by clamp(r / r0, 0.25, 4) ^ beta. The
-- writer reads 1 - S through the energy term (K.hybrid.hungerTarget) once a player-minute. Pure; one statement a
-- line for the coverage gate.
local K = NutritionRevamp.kernel
K.satiety = {}

K.satiety.R0 = 2.5079 -- Appendix D: the menu day's total fill over its total relief (the blend's normaliser)
K.satiety.LO = 0.25 -- Appendix D: the blend's clamp on r / r0
K.satiety.HI = 4 -- Appendix D
K.satiety.BETA = 0.25 -- Plan 11 ruling 9: Decision 2's modest beta, the option's default
K.satiety.HEARTY = 1.5 -- #0485
K.satiety.LIGHT = 0.75 -- #0485

-- Vanilla's defines.lua rates per game-second (#0470-#0473); the writer passes the values it saved before zeroing.
function K.satiety.defaults()
    return { idle = 9.6e-6, wellFed = 0.0, asleep = 1.0e-6, exercise = 1.92e-5 }
end

-- The rate this minute: asleep or idle freeze while the FOOD_EATEN moodle is up; exercise never freezes and runs at a
-- third of its rate with the moodle down (#0471, #2773).
function K.satiety.rate(rates, asleep, exercising, fed)
    if asleep then
        if fed then
            return rates.wellFed
        end
        return rates.asleep
    end
    if exercising then
        if fed then
            return rates.exercise
        end
        return rates.exercise / 3
    end
    if fed then
        return rates.wellFed
    end
    return rates.idle
end

function K.satiety.trait(hearty, light)
    if hearty then
        return K.satiety.HEARTY
    end
    if light then
        return K.satiety.LIGHT
    end
    return 1
end

function K.satiety.step(S, dtS, rate, sd, trait)
    return S * math.exp(-rate * sd * trait * dtS)
end

-- The relief the eat booked: the laddered getHungerChange (cooked x1.3 over stale, rotten and burnt, #0029) times
-- Eat's fraction of what was left (#3556). Deliberately the unclamped product: vanilla's own HUNGER drop is clamped
-- at 0 by Stats.add, but the scalar books the meal's whole relief, as Appendix D's model does (an eat on a sated
-- character still sates; add caps S at 1).
function K.satiety.relief(hungerChange, frac)
    return math.abs(hungerChange) * frac
end

-- The bulk factor on the applied relief: (landed bulk / FULL_BULK) / relief over r0, clamped, to the power beta.
-- 1 when there is no relief, no bulk scale or beta 0 (option (a)); a zero landed bulk floors at 0.25^beta (a drink never
-- reaches here: IN.sate skips the factor for a nil bulk).
function K.satiety.bulkFactor(landedBulk, fullBulk, relief, beta)
    if relief <= 0 or beta <= 0 or fullBulk <= 0 then
        return 1
    end
    local r = K.clamp((landedBulk / fullBulk) / relief / K.satiety.R0, K.satiety.LO, K.satiety.HI)
    return math.exp(beta * math.log(r))
end

function K.satiety.add(S, relief, factor)
    return K.min(1, S + relief * factor)
end

-- A record without S (a migrated v2) seeds it from the HUNGER read off the player (Appendix D Question 4).
function K.satiety.seed(hunger)
    return K.clamp(1 - hunger, 0, 1)
end

-- Plan 11c (spec § 3.1, § 5a and § 5b, structure D, ruling 11c-30): satiety from physiology. Two signals sate: the
-- stomach's fullness F (its satiety mass, K.stomach.satietyMass, over its maximal capacity, K.stomach.CAPACITY_MAX_G,
-- ruling 11c-19) and a meal satiety pool P of weighted kcal, fed at the eat and decaying first-order. Hunger is
-- K.hybrid.hungerTarget(sated(F, post(P)), energyState) x circadian(hour), capped at 0.69 by the writer.
-- Appended below Task 15's code so no line above moves; Task 9 retires that code. Pure; one statement a line.
K.satiety.W_PROTEIN = 2.5 -- game choice, fitted in Task 4 (Plan 11c) (S1268 open; rulings 11c-7 and 11c-30): protein satiates more per kcal (S1222, S1223, S1224, direction); no replay bounds the size (S1222 and S1223 give no per-trial protein-energy contrast; S1224 is not reproduced), so the oracle exempts it from its mutation bar
K.satiety.W_CARB = 1 -- neutral (ruling 11c-7): carbohydrate against fat is disputed (S1226, S1227, S1228, S1229), so both take the common weight; not an evidenced tie
K.satiety.W_FAT = 1 -- neutral (ruling 11c-7), as W_CARB
K.satiety.W_NEUTRAL = 1 -- neutral (spec § 3.1): the common weight of a vector with no macronutrient grams
K.satiety.HALF_LIFE_H = 0.7 -- game choice, fitted in Task 4 (Plan 11c) (S1270 open): P's half-life in game hours, fitted with P_REQ and STEEP against S1247 (Callahan's preloads from the request and fasted), the 650 kcal anchor (S1247, S1248), a fasted 400 kcal breakfast and S1231 (Rolls's soup at its measured size)
K.satiety.P_REQ = 6 -- game choice, fitted in Task 4 (Plan 11c) (S1270 open): the pool in weighted kcal at which an empty stomach reads the request level 0.25, fitted with HALF_LIFE_H and STEEP (S1247, S1248, S1231)
K.satiety.STEEP = 0.08 -- game choice, fitted in Task 4 (Plan 11c) (S1270 open; no row gives a satiety signal's read): the read's exponent, near-logarithmic so a snack leaves hunger intermediate while the interval grows with the log of the meal (S1247)
K.satiety.FULL_WEIGHT = 0.6 -- game choice, fitted in Task 4 (Plan 11c): fullness's weight in the sated product, fitted to S1231's three arms and checked against S1233; S1235 has fullness track gastric volume
K.satiety.LIQUID_WEIGHT = 0.2 -- game choice, fitted in Task 4 (Plan 11c): drunk liquid's weight in the satiety mass (K.stomach.satietyMass), between S1231 (water drunk alongside did not affect satiety) and S1233 (a drink's volume moved intake)
K.satiety.P_SEED_MAX = 1300 -- game choice (ruling 11c-30): seedP's cap, about the weighted pool of a 1,000 kcal mixed meal, so a HUNGER of 0 does not seed a pool that sates for days
K.satiety.DISCOMFORT_MAX = 100 -- not science: the DISCOMFORT stat's range, 0-100 (CharacterStat.<clinit> registers 'Discomfort' with 0.0 and 100.0; Task 5 cites it on 42.21)
K.satiety.ATWATER_P = 4 -- S1209 (Atwater general factors: protein 4.0 kcal/g)
K.satiety.ATWATER_C = 4 -- S1209 (carbohydrate 4.0 kcal/g)
K.satiety.ATWATER_F = 9 -- S1209 (fat 9.0 kcal/g)
K.satiety.CIRCADIAN_A = 0.085 -- labelled inference (ruling 11c-24; S1273): the cosine's amplitude, half of Scheer 2013's 17 % peak-to-trough of hunger; the halving is the plan's own arithmetic; the multiplicative form and the game-clock phase are game choices (ruling 11c-24a; Scheer's model is additive)
K.satiety.CIRCADIAN_PEAK_H = 19.8333 -- S1273 (ruling 11c-24): Scheer 2013's circadian hunger peak at 19:50 (trough 07:50), in game hours of the day

-- The fullness F: mass over capacity, clamped to [0, 1] (liquid and food taken at density 1, ruling 11c-8); the writer
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
-- stats-decrease multiplier, ruling 11c-11); nothing for no time. Asleep it runs unscaled (ruling 11c-24).
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

-- The soft cap's discomfort (ruling 11c-13): 0 up to capMax grams, DISCOMFORT_MAX at capHard, linear between.
function K.satiety.discomfort(mass, capMax, capHard)
    return K.satiety.DISCOMFORT_MAX * K.clamp((mass - capMax) / (capHard - capMax), 0, 1)
end

-- The circadian factor on hunger at hourOfDay (0-24, the game clock; ruling 11c-24): 1 + CIRCADIAN_A x
-- cos(2 pi (hourOfDay - CIRCADIAN_PEAK_H) / 24), peaking at 19:50 and troughing at 07:50 (the multiplicative form and the game-clock phase are game choices, ruling 11c-24a; Scheer's model is additive). The writer applies
-- min(0.69, hungerTarget(Z, es) x circadian(h)), awake and asleep.
function K.satiety.circadian(hourOfDay)
    return 1 + K.satiety.CIRCADIAN_A * math.cos(6.283185307179586 * (hourOfDay - K.satiety.CIRCADIAN_PEAK_H) / 24)
end
