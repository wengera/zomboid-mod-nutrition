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
-- stomach's fullness F (the writer's W.satietyF since Plan 11d Task 5, ruling T5-2: its fullness mass, K.stomach.fullnessMass, the satiety mass plus the protein term, over its maximal capacity, K.stomach.CAPACITY_MAX_G,
-- ruling 11c-19) and a meal satiety pool P of weighted kcal, fed at the eat and decaying first-order. Hunger is
-- K.hybrid.hungerTarget(sated(F, post(P)), energyState) x circadian(hour) x acuteFactor(S) x sleepFactor(debtH) (Plan 11d), capped at 0.69 by the writer.
K.satiety.W_PROTEIN = 2.5 -- game choice, fitted in Task 4 (Plan 11c), kept at 2.5 and bounded by S1224's delay differences (Plan 11c Task 4 review) (S1268 open; rulings 11c-7 and 11c-31): protein satiates more per kcal (S1222, S1223, S1224, direction)
K.satiety.W_CARB = 1 -- neutral (ruling 11c-7): carbohydrate against fat is disputed (S1226, S1227, S1228, S1229), so both take the common weight; not an evidenced tie
K.satiety.W_FAT = 1 -- neutral (ruling 11c-7), as W_CARB
K.satiety.W_NEUTRAL = 1 -- neutral (spec § 3.1): the common weight of a vector with no macronutrient grams
K.satiety.HALF_LIFE_H = 0.7 -- game choice, fitted in Task 4 (Plan 11c) (S1270 open): P's half-life in game hours, fitted with P_REQ and STEEP (STEEP then 0.08; STEEP was refit to 0.05 in Plan 11d Task 5, ruling T5-1, and HALF_LIFE_H was not) against S1247 (Callahan's preloads from the request and fasted), the 650 kcal anchor (S1247, S1248), a fasted 400 kcal breakfast and S1231 (Rolls's soup at its measured size)
K.satiety.P_REQ = 6 -- game choice, fitted in Task 4 (Plan 11c) (S1270 open): the pool in weighted kcal at which an empty stomach reads the request level 0.25, fitted with HALF_LIFE_H and STEEP (S1247, S1248, S1231; STEEP then 0.08, refit to 0.05 in Plan 11d Task 5, ruling T5-1, and P_REQ was not)
K.satiety.STEEP = 0.05 -- game choice, fitted in Task 4 (Plan 11c) at 0.08 (S1270 open; no row gives a satiety signal's read), refit in Plan 11d Task 5 (rulings 11d-5 and T5-1) jointly with FULL_WEIGHT and PROTEIN_FILL (at 0.08 no PROTEIN_FILL and FULL_WEIGHT held S1231, S1233 and S1247 with the protein contrast of S1222): the read's exponent, near-logarithmic so a snack leaves hunger intermediate while the interval grows with the log of the meal (S1247)
K.satiety.FULL_WEIGHT = 0.55 -- game choice, fitted in Task 4 (Plan 11c) at 0.6, refit in Plan 11d Task 5 (rulings 11d-5 and T5-1) jointly with STEEP and PROTEIN_FILL: fullness's weight in the sated product, fitted to S1231's three arms and checked against S1233; S1235 has fullness track gastric volume
K.satiety.LIQUID_WEIGHT = 0.2 -- game choice, fitted in Task 4 (Plan 11c): drunk liquid's weight in the satiety mass (K.stomach.satietyMass), between S1231 (water drunk alongside did not affect satiety) and S1233 (a drink's volume moved intake)
K.satiety.P_SEED_MAX = 1300 -- game choice (ruling 11c-30): seedP's cap, about the weighted pool of a 1,000 kcal mixed meal, so a HUNGER of 0 does not seed a pool that sates for days; it sets the seed's floor, an empty stomach's read at the cap, 0.203 under STEEP 0.05 (ruling T5-1; 0.178 at 0.08): a vanilla HUNGER below it seeds the cap and writes hungerTarget(0.797, energy state), that is 0.203 x es + 1.0 x max(0, es - 1), times the circadian, acute and sleep factors
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

-- The seed (spec § 4): the P for which hungerTarget(sated(F, post(P)), energyState) equals hunger, the
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
-- min(0.69, hungerTarget(Z, es) x circadian(h) x acuteFactor(S) x sleepFactor(debtH)), awake and asleep.
function K.satiety.circadian(hourOfDay)
    return 1 + K.satiety.CIRCADIAN_A * math.cos(6.283185307179586 * (hourOfDay - K.satiety.CIRCADIAN_PEAK_H) / 24)
end

-- Plan 11c Task 4b (spec § 5c, ruling 11c-29): the acute suppression of hunger by vigorous work (exercise-induced
-- anorexia: during and just after the bout, gone within about 1.5 h; S1299, S1300, S1303, S1304, S1305, S1306). A
-- state S in [0, 1] relaxes toward the kind's weight while vigorous and toward 0 otherwise, first-order with
-- ACUTE_HALF_LIFE_H while vigorous and ACUTE_DECAY_HALF_LIFE_H otherwise (ruling 11d-1); the writer multiplies hunger by acuteFactor(S) = 1 - ACUTE_MAX x S (Task 6
-- wires it: vigorous is the swing state or the metabolism class's heavy-work band, IsRunning never reaching the
-- server, x141a). Appended so no line above moves. Pure; one statement a line.
K.satiety.ACUTE_MAX = 0.7 -- game choice, fitted in Task 4b (Plan 11c) while its against-control row was open (now S1500 and S1502; kept at 0.7, ruling 11d-1): with ACUTE_HALF_LIFE_H, to S1303 (Douglas 2017: ES >= 0.60 at 0.5, 1.0 and 1.5 h of a trial whose bout ran 0-1 h) and S1306 (Goltz 2018: ES 0.62-1.47 just after a 60 min run), under the request-anchored mapping (ruling 11c-31: 65 mm read as 0.25, an assumption) and an SD of 25.7 mm read off S1303's main effect (an inference); since Plan 11d S1500 (no effect 30-90 min after the bout) overrides S1303's 1.5 h reading, the decay being ACUTE_DECAY_HALF_LIFE_H (ruling 11d-1)
K.satiety.ACUTE_HALF_LIFE_H = 0.5 -- game choice, fitted in Task 4b (Plan 11c) (fitted while its against-control row was open; now S1500 and S1502, ruling 11d-1): the state's rise half-life in game hours, while vigorous, fitted with ACUTE_MAX to S1303 and S1306; it reads S1502's -33 % during a 60 min bout (the replay's mean 0.674 of control); the decay is ACUTE_DECAY_HALF_LIFE_H (Plan 11d)
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
    local k = math.exp(-0.6931471805599453 * dtH / K.satiety.acuteHalfLife(vigorous))
    return K.clamp(w + (S - w) * k, 0, 1)
end

-- The factor on hunger: 1 - ACUTE_MAX x S, S read as 0 when non-finite and clamped to [0, 1].
function K.satiety.acuteFactor(S)
    if S - S ~= 0 then
        S = 0
    end
    return 1 - K.satiety.ACUTE_MAX * K.clamp(S, 0, 1)
end
K.satiety.ACUTE_DECAY_HALF_LIFE_H = 0.15 -- game choice, Plan 11d (ruling 11d-1): the post-bout decay, fitted to S1500 (no effect 30-90 min after) and S1502 (-33 % during); the rise keeps ACUTE_HALF_LIFE_H; fitted at 0.15 h, the activity replay of a 60 min aerobic bout reads 0.674 of control's hunger over the bout (S1502: 41 against 61 mm, 0.67) and -3.8 mm 30 min after it (-3.9 before the deficit drive's refit, ruling 9c-1) (S1500: no larger than the pooled -8.465 mm immediately after)

-- Plan 11d (ruling 11d-1): the half-life of exerciseSuppression's step, the rise's while vigorous and the shorter
-- decay's otherwise. Appended so no line above moves; one statement a line for the coverage gate.
function K.satiety.acuteHalfLife(vigorous)
    if vigorous then
        return K.satiety.ACUTE_HALF_LIFE_H
    end
    return K.satiety.ACUTE_DECAY_HALF_LIFE_H
end

-- Plan 11d (ruling 11d-2, spec § 5d): sleep debt raises hunger. The factor 1 + SLEEP_MAX x clamp(debtH /
-- SLEEP_DEBT_FULL_H, 0, 1) multiplies the written hunger, read off record.acute.debtH in game hours (wired in the writer's W.satietyFactor, Plan 11d Task 6); it is inert while the server disables sleep, K.acute.sleepMinute holding the debt at 0.
-- It follows the acute kernel's accounting (K.acute.sleepMinute): the debt books once per 24 h window at the window's
-- close, as the shortfall against SLEEP_NEED_H x needFactor, so the factor steps at the window's close rather than at
-- waking; a longer night repays only REPAY (0.5) of its excess, so recovery takes more than one full night. It
-- reverses as the debt is repaid (S1567: intake fell on recovery sleep). Whether hunger steps with any short night or
-- rises graded with the loss is not settled (S1568: total and partial loss gave comparable late-night intake; S1282:
-- hunger 3.9 after total deprivation against 2.2 after 4.5 h and 1.7 after 7 h: only total deprivation differed significantly; 4.5 h against 7 h is not tested in the row), so the
-- ramp to a full debt and its cap are game choices. Appended so no line above moves; one statement a line for the coverage gate.
K.satiety.SLEEP_MAX = 0.18 -- game choice, Plan 11d (ruling 11d-2): the factor's rise at a full debt, fitted to S1284 (hunger +13.4 mm, +252.8 kcal/d) and S1565 (<= 5.5 h: +204 kcal/d), with S1564 (+385 kcal/d) the band's top and S1567 the reversal; under the request-anchored mapping (ruling 11c-31: 260 mm per unit, an assumption) it reads +11.7 mm at the request (S1284's 13.4 within 1.5x) and a next-day intake ratio of 1.18 on an assumed 2,000 kcal day (band 1.10-1.19); the two bands admit SLEEP_MAX in [0.137, 0.19], 0.18 favouring the measured hunger
K.satiety.SLEEP_DEBT_FULL_H = 2 -- game choice, Plan 11d (ruling 11d-2): the debt that reads the full factor, the debt the acute kernel books for one night of 5.5 h (S1565's restriction to 5.5 h or less; S1284, S1564 and S1567 its pooled and reversal rows): K.acute.SLEEP_NEED_H 7.5 - 5.5 = 2.0 h at the window's close; reaching the full factor after one night is a game choice (the pooled protocols are multi-night)

-- The factor on hunger for a sleep debt of debtH game hours: 1 for no debt, a negative one or a non-finite one (x - x
-- is NaN for NaN and for an infinity), rising linearly to 1 + SLEEP_MAX at SLEEP_DEBT_FULL_H and held there.
function K.satiety.sleepFactor(debtH)
    if debtH - debtH ~= 0 then
        return 1
    end
    return 1 + K.satiety.SLEEP_MAX * K.clamp(debtH / K.satiety.SLEEP_DEBT_FULL_H, 0, 1)
end

-- Plan 11d Task 5 (ruling 11d-5, spec § 5d): protein fills while it is in the stomach. The fullness F reads the
-- satiety mass plus PROTEIN_FILL x the solid lane's protein (K.stomach.fullnessMass, read by the writer's W.satietyF)
-- against CAPACITY_MAX_G (record.stomachFill stays physical, ruling T5-2); the protein leaves with the lane's energy, so it fades as
-- the meal empties. No row names gastric fullness from protein: the term is a game choice, fitted with FULL_WEIGHT and
-- STEEP so the oracle's protein contrast reads at least half S1222's -7 mm under the request-anchored mapping (ruling
-- 11c-31, an assumption) while every hard replay holds at 1.1x. Appended so no line above moves.
K.satiety.PROTEIN_FILL = 8 -- game choice, Plan 11d (ruling 11d-5; no row names gastric fullness from protein): the extra grams of fullness mass a gram of protein in the solid lane counts for, fitted jointly with FULL_WEIGHT 0.55 and STEEP 0.05 so the protein contrast (30 % against 10 % protein at 400 kcal, mean over 240 min) reads 0.0134, at least half the 0.025 of S1222 (hunger -7 mm; S1380 and S1383: less eaten after protein), with S1231 and S1247 held at 1.1x, S1233 at 1.15x and S1224's differences at 1.5x; S1384's short-term null for whey against carbohydrate is not reproduced (the model reads about 8 mm)

-- Plan 11e (rulings 11e-2 and T2-A, spec memo C12): nicotine withdrawal raises hunger. The factor 1 + NIC_MAX x
-- clamp(w / NIC_WITHDRAWAL_MAX, 0, 1) x fade(d) multiplies the written hunger, where w is the server's own
-- NICOTINE_WITHDRAWAL (a Smoker's, or a former Smoker's, rising on the server alone: #3630, #3631; vanilla reads it only
-- as stress, #3635) and d the game days since the mod's own anchor, the last minute the stat read 0 or fell (a smoke
-- lowers it, #3632; the writer's W.nicotine keeps it as record.satiety.nicH, ruling T2-A, because the vanilla timer's
-- units move with the time speed, #3636). The fade is linear, 1 at d = 0 and 0 at NIC_FADE_DAYS.
-- A character who keeps smoking keeps resetting the anchor, so between smokes the factor stays at its withdrawal-scaled
-- level and never fades while the habit continues; only a quit runs the fade. Appended so no line above moves; one statement a line.
K.satiety.NIC_MAX = 0.11 -- game choice, Plan 11e (ruling 11e-2): the factor's rise at the stat's cap, fitted to S1576 (Stamford 1986: intake +227 kcal/d over the 48 days after quitting, 1.1135 of an assumed 2,000 kcal day): under the request-anchored mapping (ruling 11c-31, an assumption) the next-day intake ratio reads 1.1093 and the 48-day mean 1.0951, both in the band 1.08-1.14, which admits NIC_MAX in about [0.093, 0.14] (0.13 would put the 48-day mean on 1.1135; the ruling's 0.11 puts the next day near it); the size is low certainty, one experiment with n = 13 sedentary women and no certainty rating; S1577 sets the fade's end
K.satiety.NIC_FADE_DAYS = 182 -- game choice, Plan 11e (ruling 11e-2): 26 weeks, the fade's end, from S1577 (Hall 1989: abstinent women's intake about baseline by week 26, men's below it), linear between; the size it fades is S1576's (n = 13, low certainty) and the shape of the fade is not measured
K.satiety.NIC_WITHDRAWAL_MAX = 0.51 -- CharacterStat.NICOTINE_WITHDRAWAL's maximum, the stat's cap a full smoke removes (#3632)

-- The factor on hunger for a withdrawal w (the stat's value) d game days after the anchor: 1 for a non-finite input
-- (x - x is NaN for NaN and for an infinity), for no withdrawal (w <= 0) and for a negative d; otherwise
-- 1 + NIC_MAX x clamp(w / NIC_WITHDRAWAL_MAX, 0, 1) x clamp(1 - d / NIC_FADE_DAYS, 0, 1).
function K.satiety.nicotineFactor(w, d)
    if w - w ~= 0 or d - d ~= 0 then
        return 1
    end
    if w <= 0 or d < 0 then
        return 1
    end
    local fade = K.clamp(1 - d / K.satiety.NIC_FADE_DAYS, 0, 1)
    return 1 + K.satiety.NIC_MAX * K.clamp(w / K.satiety.NIC_WITHDRAWAL_MAX, 0, 1) * fade
end
