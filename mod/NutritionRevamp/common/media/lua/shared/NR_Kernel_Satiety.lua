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

-- Constants: one line each, its label its provenance. The joint fit (fit-11g-20261012d: a coordinate refinement over all eight from fix 1's point, until its last rounds moved nothing; fix 1's fit-11g-20261012c searched a full grid of 11,664 points first) set
-- FULL_WEIGHT, LIQUID_WEIGHT, PROTEIN_FILL, W_PROTEIN, W_FAT, MEAL_HALF_LIFE_H, MEAL_REQ and MEAL_STEEP together, loss
-- 0.5782 over the 39 scored oracles of testing/tests/kernel/gut_oracles.py (Tieken read-only; S1233's volume slope scored; S1231's null for water drunk alongside scored and LIQUID_WEIGHT's bound lifted to (0, 1];
-- fix 1's fit-11g-20261012c, loss 0.6719 with LIQUID_WEIGHT held at a bound of 0.19, Task 6c's fit-11g-20261012b, loss 1.3609 with Tieken scored, and the Task 6 fit of the gut stage G, fit-11g-20261012, degenerate, are superseded).
K.satiety.HEARTY = 1.5 -- #0485: vanilla's game number, not science (spec sec. 3.4)
K.satiety.LIGHT = 0.75 -- #0485: vanilla's game number, not science (spec sec. 3.4)
K.satiety.W_PROTEIN = 2.49782 -- game choice, fitted in Plan 11g Task 6c fix 2 against S1224 (tools/fit_gut_satiety.py, fit-11g-20261012d): protein's weight per kcal on M, 2.50 times carbohydrate's, above harvest 11's advice of slightly above 1 (S1820, S1822, the pooled S1222); it rests on S1224's two minute differences, Marmonier 2000's protein over carbohydrate and over fat, each scored on its own 26 and 35 min scale, in a study whose absolute delays the model stretches 3-6x (183 / 156 / 160 min against 60 / 34 / 25); the nulls S1818, S1821, S1814 and S1225 are not in the loss and do not move with the weight; the loss by weight (the Task 6c review, Tieken scored): 1.0 2.413, 1.25 2.032, 1.5 1.781, 2.0 1.531, 2.5 1.361, 3.0 1.406; on this fit's registry 1.0 1.535, 1.25 1.291, 1.5 0.990, 2.0 0.718, 2.50 0.578, 3.0 0.602, where at 2.0 and under S1222's contrast and S1231's null for water drunk alongside fail too, at 1.5 and under also S1224's protein-over-carbohydrate difference, at 1.25 and under Rolls' casserole (S1231), and at 1.0 also Callahan's 400 kcal preload (S1247); at x2 S1224's protein-over-carbohydrate difference, Belza's 50 % arm (S1820) and Rolls 1999's drop fail, at x0.5 S1224's two differences, S1222, S1231's null and Rolls' casserole (ruling 11c-31); S1268 open
K.satiety.W_CARB = 1 -- neutral (ruling 11c-7): carbohydrate against fat is disputed (S1226, S1227, S1228, S1229), so both take the common weight; not an evidenced tie
K.satiety.W_FAT = 0.878683 -- game choice, fitted in Plan 11g Task 6c fix 2 against S1224, S1228 and S1231 (tools/fit_gut_satiety.py, fit-11g-20261012d) (ruling T2-3: the fit decides): fat's weight per kcal on M, a little below carbohydrate's, the two minute differences scored on one scale (Melanson's 61 min, spec § 7): S1224 (Marmonier 2000: fat's delay 9 min shorter than carbohydrate's; the model reads it 4 min longer) against S1228 (Melanson 1999: fat's request 61 min later; the model reads it 2 min earlier), both named non-reproductions; at x0.5 S1231's null for water drunk alongside fails (and Melanson's named difference widens), at x2 S1222's contrast and Rolls 1999's drop (S1231); the hunger nulls (S1810, S1816, S1818, S1830) would put it at 1; S1268 open
K.satiety.W_NEUTRAL = 1 -- neutral (spec § 3.1): the common weight of a vector with no macronutrient grams
K.satiety.MEAL_HALF_LIFE_H = 0.583749 -- game choice, fitted in Plan 11g Task 6c fix 2 against S1247, S1248, S1224 and S1828 (tools/fit_gut_satiety.py, fit-11g-20261012d): M's clearance half-life in game hours (at x2 and x0.5 Callahan's preloads fail, at x2 the 650 kcal anchor, Marmonier's protein difference and the stability checks, at x0.5 Diekmann's 6 h), inside harvest 12's 0.5-2 h (S1841, S1847, S1850, S1854, S1861; inference) and harvest 11's 0.25-1.5 h (S1799); S1270 open: no row measures a satiety signal's decay
K.satiety.MEAL_REQ = 3.80654 -- game choice, fitted in Plan 11g Task 6c fix 2 against S1247, S1231, S1233 and S1222 (tools/fit_gut_satiety.py, fit-11g-20261012d): M in weighted kcal at which an empty stomach reads the request level 0.25 (at x2 Callahan's 190 and 400 kcal preloads, Rolls' casserole and S1231's null for water drunk alongside fail; at x0.5 S1222's contrast and Rolls' drop); S1270 open: no row gives a satiety signal's scale
K.satiety.MEAL_STEEP = 0.0356875 -- game choice, fitted in Plan 11g Task 6c fix 2 against S1247, S1231, S1233 and S1828 (tools/fit_gut_satiety.py, fit-11g-20261012d): the read's exponent, near-logarithmic so a snack leaves hunger intermediate while the interval grows with the log of the meal (S1247); not at a search bound (fix 1's grid spanned 0.03-0.08 and the last refinement rounds' neighbours read worse), so the stability checks hold (the 650 kcal meal at 19:00 back at 298 / 282 / 266 min under hunger x0.98 / x1.00 / x1.02, spread 32 min; hunger 0.396 at +24 h; at x0.5 the fasting rise fails); at x2 Callahan's fasted 400 kcal, Rolls' drop and 300 mL arm and Diekmann's 6 h fail; S1270 open
K.satiety.MEAL_SEED_MAX = 1180 -- game choice (ruling 11c-30; re-derived in Plan 11g Task 6c fix 1, unchanged by fix 2): the seed's cap, about the weighted kcal of a 1,000 kcal mixed meal (15/50/35 % of energy, 1182 under the fitted weights), so a HUNGER of 0 does not seed an M that sates for days; it sets the seed's floor, an empty stomach's read at the cap, 0.214 under the fitted MEAL_REQ and MEAL_STEEP (0.2136): a vanilla HUNGER below it seeds the cap and writes hungerTarget(0.786, energy state), that is 0.214 x es (no deficit floor since Plan 11g Task 7 fix 1, ruling T7-1; 0.02 x max(0, es - 1) was added from Plan 11f Task 2c fix 1), times the circadian, acute, sleep and nicotine factors
K.satiety.FULL_WEIGHT = 0.517741 -- game choice, fitted in Plan 11g Task 6c fix 2 against S1231, S1233, S1828 and S1325 (tools/fit_gut_satiety.py, fit-11g-20261012d): fullness's weight in the sated product, F counted to the hard capacity (spec § 7); at x2 and x0.5 Rolls 1999, Rolls 1998 and Karl 2021's BAL arm fail; S1235 has fullness track gastric volume, and harvest 13 credits F with part of Karl 2021's surplus troughs (S1874: BAL's emptying 612 min)
K.satiety.LIQUID_WEIGHT = 0.278815 -- game choice, fitted in Plan 11g Task 6c fix 2 against S1231 and S1233 (tools/fit_gut_satiety.py, fit-11g-20261012d) (rulings T6c-3, T6c-5): drunk liquid's weight in the satiety mass alone (K.stomach.satietyMass; the physical fill reads both lanes whole, ruling T6c-1), fitted in (0, 1], the weight's own range; two rows set it: S1231's null (Rolls 1999: water drunk alongside the casserole did not lower lunch, +18 kJ, scored within the arms' +/- 148 kJ, a design choice) holds it from above, the model's casserole-with-water less casserole-alone reading -130 kJ at the band's edge (and Rolls' drop, S1231, fails just past it, at x1.05), and S1233 (Rolls 1998: a drink's volume moved intake; its volume slope, scored) pulls it up, the slope a named non-reproduction (0.038 against 0.130); at x2 S1231's null and Rolls' drop fail, at x0.5 Rolls 1998's 600 mL arm; fix 1's 0.19 was a bound of its own, not a row
K.satiety.BETA = 0.05 -- game choice (spec § 10, Plan 15 Task 7, fullness by weight and volume): the share of a solid food's plate volume beyond its weight (stomach.volX, the SR Legacy household measures, S2212) the satiety mass counts (K.stomach.satietyMass), range 0 to 0.1; set at the evidence's point, Osterholt 2007's aerated snack eaten to equal fullness (S1484: 21 % less weight at 2.7 times the volume per gram, beta 0.046 on a linear fill), with Nguyen 2012's popcorn against chips bounding it small (S2209) and Rolls 2014's crushed cereal a portion cue that gives no number (S2215); chewed bulk acts on satiation, not gastric fill: no measurement of the volume surviving chewing (S2213, open) and no matched-weight satiety preload of a chewed solid (S2214, open), so the physical fill and the 730 and 1100 g caps stay on mass (ruling T6c-1); at 0.05 a slice of bread fills 29 % more than its weight, popcorn about 2.4 times, 1 kg of raw broccoli 8 %, water not at all
K.satiety.PROTEIN_FILL = 7.91676 -- game choice, fitted in Plan 11g Task 6c fix 2 against S1231, S1820 and S1222 (tools/fit_gut_satiety.py, fit-11g-20261012d) (ruling 11d-5: no row names gastric fullness from protein): the extra grams of fullness mass a gram of protein in the solid lane counts for (at x2 Rolls 1999's soup and water arms, Lewis' 20 % cut and Belza's 50 % arm fail, at x0.5 Rolls' soup and casserole, Rolls 1998's 600 mL arm and S1222's contrast); the protein contrast (30 % against 10 % protein at 400 kcal, mean over 240 min) reads 0.0126, inside S1222's band 0.0125-0.04 (hunger -7 mm; S1380 and S1383: less eaten after protein); S1384's short-term null for whey against carbohydrate is not reproduced
K.satiety.DISCOMFORT_MAX = 100 -- not science: the soft cap's discomfort scale, borrowed from the DISCOMFORT stat's range 0-100 (CharacterStat.<clinit> registers 'Discomfort' with 0.0 and 100.0; Task 5 cites it on 42.21); ruling 11c-25: the Overfull moodle's level reads it through K.view.fullnessLevel and nothing writes DISCOMFORT
K.satiety.ATWATER_P = 4 -- S1209 (Atwater general factors: protein 4.0 kcal/g)
K.satiety.ATWATER_C = 4 -- S1209 (carbohydrate 4.0 kcal/g)
K.satiety.ATWATER_F = 9 -- S1209 (fat 9.0 kcal/g)
K.satiety.CIRCADIAN_A = 0.085 -- labelled inference (ruling 11c-24; S1273): the cosine's amplitude, half of Scheer 2013's 17 % peak-to-trough of hunger; the halving is the plan's own arithmetic; the multiplicative form and the game-clock phase are game choices (ruling 11c-24a; Scheer's model is additive)
K.satiety.CIRCADIAN_PEAK_H = 19.8333 -- S1273 (ruling 11c-24): Scheer 2013's circadian hunger peak at 19:50 (trough 07:50), in game hours of the day
K.satiety.ACUTE_MAX = 0.7 -- game choice, fitted in Task 4b (Plan 11c) while its against-control row was open (now S1500 and S1502; kept at 0.7, ruling 11d-1): with ACUTE_HALF_LIFE_H, to S1303 (Douglas 2017: ES >= 0.60 at 0.5, 1.0 and 1.5 h of a trial whose bout ran 0-1 h) and S1306 (Goltz 2018: ES 0.62-1.47 just after a 60 min run), under the request-anchored mapping (ruling 11c-31: 65 mm read as 0.25, an assumption) and an SD of 25.7 mm read off S1303's main effect (an inference); since Plan 11d S1500 (no effect 30-90 min after the bout) overrides S1303's 1.5 h reading, the decay being ACUTE_DECAY_HALF_LIFE_H (ruling 11d-1)
K.satiety.ACUTE_HALF_LIFE_H = 0.5 -- game choice, fitted in Task 4b (Plan 11c) (fitted while its against-control row was open; now S1500 and S1502, ruling 11d-1): the state's rise half-life in game hours, while vigorous, fitted with ACUTE_MAX to S1303 and S1306; it reads S1502's -33 % during a 60 min bout (the replay's mean 0.674 of control); the decay is ACUTE_DECAY_HALF_LIFE_H (Plan 11d)
K.satiety.ACUTE_DECAY_HALF_LIFE_H = 0.15 -- game choice, Plan 11d (ruling 11d-1): the post-bout decay, fitted to S1500 (no effect 30-90 min after) and S1502 (-33 % during); the rise keeps ACUTE_HALF_LIFE_H; fitted at 0.15 h, the activity replay of a 60 min aerobic bout reads 0.674 of control's hunger over the bout (S1502: 41 against 61 mm, 0.67) and -3.6 mm 30 min after it (Plan 11g Task 7's deficit refit; -3.7 under Task 6c fix 2's and fix 1's refits, -3.8 under Task 6c's fit, -3.5 under the gut stage's fit, Task 6, -3.7 before it; -3.8 before the deficit drive's refit on the shipped pipeline, Plan 11f Task 2c, and -3.9 before ruling 9c-1) (S1500: no larger than the pooled -8.465 mm immediately after)
K.satiety.ACUTE_KIND = {}
K.satiety.ACUTE_KIND.aerobic = 1 -- S1300, S1303, S1306: running suppresses hunger (the weight is the scale's unit)
K.satiety.ACUTE_KIND.resistance = 0.5 -- game choice (S1301: suppressed during resistance work too; S1305: less marked and not observed consistently), the swing state
K.satiety.ACUTE_KIND.walk = 0 -- S1302: brisk walking did not move appetite
K.satiety.SLEEP_MAX = 0.18 -- game choice, Plan 11d (ruling 11d-2): the factor's rise at a full debt, fitted to S1284 (hunger +13.4 mm, +252.8 kcal/d) and S1565 (<= 5.5 h: +204 kcal/d), with S1564 (+385 kcal/d) the band's top and S1567 the reversal; under the request-anchored mapping (ruling 11c-31: 260 mm per unit, an assumption) it reads +11.7 mm at the request (S1284's 13.4 within 1.5x) and a next-day intake ratio of 1.18 on an assumed 2,000 kcal day (band 1.10-1.19); the two bands admit SLEEP_MAX in [0.137, 0.19], 0.18 favouring the measured hunger
K.satiety.SLEEP_DEBT_FULL_H = 2 -- game choice, Plan 11d (ruling 11d-2): the debt that reads the full factor, the debt the acute kernel books for one night of 5.5 h (S1565's restriction to 5.5 h or less; S1284, S1564 and S1567 its pooled and reversal rows): K.acute.SLEEP_NEED_H 7.5 - 5.5 = 2.0 h at the window's close; reaching the full factor after one night is a game choice (the pooled protocols are multi-night)
K.satiety.NIC_MAX = 0.1313 -- game choice, Plan 11e (rulings 11e-2 and T2-D): the factor's rise at the stat's cap, fitted to the 48-day mean of S1576 (Stamford 1986: intake +227 kcal/d, the period mean over the 48 days after quitting): the replay's 48-day mean intake ratio reads S1576's 1.1135, which is 227 kcal over a 2,000 kcal baseline that is an ASSUMPTION (the row gives no baseline intake), under the request-anchored mapping (ruling 11c-31, an assumption); the next-day ratio then reads 1.1304, both in the band 1.08-1.14; the size is low certainty, one experiment with n = 13 sedentary women and no certainty rating; S1577 sets the fade's end
K.satiety.NIC_FADE_DAYS = 182 -- game choice, Plan 11e (ruling 11e-2): 26 weeks, the fade's end, from S1577 (Hall 1989: abstinent women's intake about baseline by week 26, men's below it), linear between; the size it fades is S1576's (n = 13, low certainty) and the shape of the fade is not measured
K.satiety.NIC_WITHDRAWAL_MAX = 0.51 -- CharacterStat.NICOTINE_WITHDRAWAL's maximum, the stat's cap a full smoke removes (#3632)
K.satiety.MAX_GAP_M = 60 -- not science, no row needed (Plan 11g close; Kinetics' local until then): the gap cap, a step's drain integrating at most this many game minutes, the pipeline's offline cap (Metabolism's and Nutrients' dtM clamp), read by KIN.drain and replay_live's stand-in

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
-- T4-4). Kinetics calls it with its gap capped, and the replays' stand-ins call it, so every path splits a step alike.
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
-- it by circadian(hour) x acuteFactor(S) x nicotineFactor x sleepFactor(debtH) and caps it at 0.69 below starvation (K.hybrid.caps); the replays read it.
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
-- min(0.69, hungerTarget(Z, es) x circadian(h) x acuteFactor(S) x sleepFactor(debtH) x nicotineFactor(w, d)), awake and asleep.
function K.satiety.circadian(hourOfDay)
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
