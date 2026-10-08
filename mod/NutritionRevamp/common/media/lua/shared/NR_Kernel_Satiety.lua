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
-- 1 when there is no relief, no food bulk (a drink passes 0), no bulk scale or beta 0 (option (a)).
function K.satiety.bulkFactor(landedBulk, fullBulk, relief, beta)
    if relief <= 0 or landedBulk <= 0 or beta <= 0 or fullBulk <= 0 then
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
