-- NR_Data_Records.lua -- not a kernel file: the declarative nutrient records K.nutrients.minute loops over, as
-- NR.data.records = { ORDER, REC }. Every number sits on its own line with its row: a settled S id, or
-- `design-phase-v1` / `game choice` naming the open row (test_data_records.py enforces it). This file sorts before the
-- kernels, so each derived rate is a literal with its expression in the comment, and the test recomputes it to 1e-9.
-- R is {male, female} per day on the INGESTED basis; the engine's absorbed requirement is R x absorb (nil absorb =
-- 1.0, open S1060). A field no Lua reads is not laid.
local NR = NutritionRevamp
NR.data = NR.data or {}

NR.data.records = {
    ORDER = {
        "vitC",
        "thiamine",
        "riboflavin",
        "niacin",
        "vitB6",
        "folate",
        "vitB12",
        "choline",
        "vitA",
        "vitD",
        "vitE",
        "vitK",
        "pantothenate",
        "biotin",
        "iron",
        "zinc",
        "copper",
        "magnesium",
        "calcium",
        "iodine",
        "selenium",
        "fibre",
        "efa",
        "sodium",
        "potassium",
        "caffeine",
        "ethanol",
    },
    REC = {
        -- Vitamin C: one pool calibrated to scurvy at 40 d.
        vitC = {
            key = "vitC",
            unit = "mg",
            kind = "pool",
            R = {
                90, -- male RDA mg/d, S0218
                75, -- female RDA mg/d, S0218
            },
            absorb = 0.85, -- design-phase-v1 game choice: K.stomach.BIOAVAIL.vitC (70-90 % food absorption, no settled row; open S1060)
            k = 0.047427999622147034, -- = ln(1/0.15)/40: K.nutrients.calib(0.15, 40); S0225 (scurvy at ~40 d), S0958/S0965 (the 0.15 clinical store)
            ladder = {
                0.70, -- marginal: the generic rung, design-phase-v1 game choice (open S1057)
                0.45, -- depleted: the generic rung, design-phase-v1 game choice (open S1057)
                0.15, -- clinical: ~300 mg near scurvy of a ~2 g replete pool, S0958/S0965
            },
            ul = 2000, -- mg/d, rung 1 (GI only), S0219
            pCap = 1.0, -- plasma and cells saturate at 100-200 mg/d, S0220/S0221
        },
        -- Thiamine: energy-scaled; the RDA rides as Rmin for the band only (K.view.dailyR). No UL (S0238).
        thiamine = {
            key = "thiamine",
            unit = "mg",
            kind = "pool",
            scale = "perMJ",
            R = {
                0.1, -- male mg per MJ expended (EFSA PRI), S0236
                0.1, -- female mg per MJ expended (EFSA PRI), S0236
            },
            Rmin = {
                1.2, -- male RDA mg/d, S0235 (read by the band only (K.view.dailyR), never by the engine)
                1.1, -- female RDA mg/d, S0235 (read by the band only (K.view.dailyR), never by the engine)
            },
            k = 0.020844493746521427, -- = ln(1.2/0.5)/42: K.nutrients.calib(0.4166666666666667, 42); clinical at 42 d with none eaten, game choice (open S0243) inside S2255's one to three months; the implied half-life exceeds S0240's isotope one: the onset wins
            ladder = {
                0.70, -- marginal: the generic rung, design-phase-v1 game choice (open S1057)
                0.45, -- depleted: the generic rung, design-phase-v1 game choice (open S1057)
                0.4166666666666667, -- clinical = 0.5/1.2: K.nutrients.fFromThreshold(0.5, 1.2); signs below 0.5 mg/d, S0242 (reached at 42 d)
            },
            pCap = 1.0, -- surplus excreted from the 1-12 h fast pool, S0241 (judgement)
        },
        -- Riboflavin: no store or onset row (S0260 open), so it takes thiamine's isotope half-life. No UL (S0255).
        riboflavin = {
            key = "riboflavin",
            unit = "mg",
            kind = "pool",
            R = {
                1.3, -- male RDA mg/d, S0253
                1.1, -- female RDA mg/d, S0253
            },
            k = 0.05134423559703299, -- = ln2/13.5: K.nutrients.kFromHalfLife(13.5); S0240's thiamine whole-body half-life midpoint, design-phase-v1 game choice (open S1067; onset open S0260)
            pCap = 1.0, -- urinary excretion rises sharply above ~1 mg/d (tissue saturation), S0257
        },
        -- Niacin (mg NE): NE = niacin + tryptophan/60 (NR_Server_Nutrients credits it). The UL is nicotinic acid only.
        niacin = {
            key = "niacin",
            unit = "mg",
            kind = "pool",
            scale = "perMJ",
            R = {
                1.6, -- male mg NE per MJ expended (EFSA PRI), S0268
                1.6, -- female mg NE per MJ expended (EFSA PRI), S0268
            },
            Rmin = {
                16, -- male RDA mg NE/d, S0267 (read by the band only (K.view.dailyR), never by the engine)
                14, -- female RDA mg NE/d, S0267 (read by the band only (K.view.dailyR), never by the engine)
            },
            k = 0.025205352020361647, -- = ln(1/0.25)/55: K.nutrients.calib(0.25, 55); pellagra at 50-60 d, S0271; f 0.25 design-phase-v1 (open S1068)
            ladder = {
                0.70, -- marginal: the generic rung, design-phase-v1 game choice (open S1057)
                0.45, -- depleted: the generic rung, design-phase-v1 game choice (open S1057)
                0.25, -- clinical: the generic rung, design-phase-v1 game choice (open S1068)
            },
            ul = 35, -- mg/d, nicotinic acid only (flushing), S0269
            ulBasis = "supplement", -- the IOM UL is on niacin added to foods or taken as supplements, never niacin naturally in food (S1913)
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
            trpShare = 0.011, -- tryptophan as 1.1 % of dietary protein, design-phase-v1 game choice (open S1069)
            trpPerNE = 60, -- mg tryptophan per mg NE, S0270
        },
        -- Vitamin B6: R = max(RDA, 0.016 mg/g protein); the store cross-check is x3 off and the ONSET wins.
        vitB6 = {
            key = "vitB6",
            unit = "mg",
            kind = "pool",
            scale = "perProteinGMax",
            R = {
                1.3, -- male RDA mg/d (the max floor), S0291; the max combination design-phase-v1 (open S1071)
                1.3, -- female RDA mg/d (the max floor), S0291; the max combination design-phase-v1 (open S1071)
            },
            Rscale = 0.016, -- mg B6 per g dietary protein, S0294
            k = 0.02390162691586018, -- = ln2/29: K.nutrients.kFromHalfLife(29); plasma PLP half-life 25-33 d, S0298
            ladder = {
                0.70, -- marginal: reached at 15 d, inside the 11-28 d biochemical depletion, S0301
                0.45, -- depleted: the generic rung, design-phase-v1 game choice (open S1057)
                0.25, -- clinical: the generic rung, design-phase-v1 game choice (open S1070)
            },
            ul = 100, -- mg/d (IOM), S0295; EFSA's 12 mg/d S0296 noted
            chronic = {
                perDay = 50, -- S0305: neuropathy below 50 mg/d only after > 6 months; holdD 180 d
                holdD = 180, -- days, S0305; the engine default hold is open S1058
            },
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Folate (ug DFE): the store cross-check is x1.5-3 off and the ONSET wins.
        folate = {
            key = "folate",
            unit = "ug",
            kind = "pool",
            R = {
                400, -- male RDA ug DFE/d, S0326
                400, -- female RDA ug DFE/d, S0326
            },
            k = 0.025584278811044955, -- = ln(1/0.10)/90: K.nutrients.calib(0.10, 90); stores depleted after 3 months, S0334
            ladder = {
                0.70, -- marginal: the generic rung, design-phase-v1 game choice (open S1057)
                0.10, -- depleted: design-phase-v1 game choice (open S1072), at the 90 d of S0334
                0.046415888336127774, -- clinical = p(120 d) = exp(-k x 120): anaemia after months of red-cell turnover, S0335
            },
            ul = 1000, -- ug/d folic acid only, S0330
            ulBasis = "supplement", -- the UL is on folic acid from fortified food or supplements, not food folate (S1914, S0330)
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Vitamin B12: two compartments; clinical when p2 < 1, accruing dmg hours that repletion does not clear
        -- (S0363). The per-eat absorption ceiling is K.interact.b12Ceiling. No UL (S0353).
        vitB12 = {
            key = "vitB12",
            unit = "ug",
            kind = "pool2",
            R = {
                2.4, -- male RDA ug/d, S0349
                2.4, -- female RDA ug/d, S0349
            },
            absorb = 0.5, -- S0358 (50 % of a 1 ug dose); the per-eat ceiling K.interact.b12Ceiling is applied by the intake wrapper on the INGESTED amount and already yields 0.5 at <= 4 ug, so R_abs = 1.2 ug/d and a diet at the 2.4 ug RDA holds p = 1
            k = 0.001, -- = obligatory loss / store = 2.5/2500 (t1/2 693 d), S0354/S0355
            ladder = {
                0.70, -- marginal (store): the generic rung, design-phase-v1 game choice (open S1057)
                0.45, -- depleted (store): the generic rung, design-phase-v1 game choice (open S1057)
                0.10, -- the store threshold dialExp reads: the functional threshold, design-phase-v1 game choice (open S1073)
            },
            clinicalOnP2 = true,
            p2Clinical = 1.0, -- clinical while the functional p2 < 1: any tissue deficit, S0363
            two = {
                fThreshold = 0.10, -- p2 = min(1, p/0.10), design-phase-v1 game choice (open S1073)
            },
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Choline: the female rate rides on NR_Server_Nutrients' kMul.choline. The UL is supplement-only.
        choline = {
            key = "choline",
            unit = "mg",
            kind = "pool",
            R = {
                550, -- male AI mg/d, S0370
                425, -- female AI mg/d, S0370
            },
            k = 0.05733203830123505, -- = ln(1/0.30)/21: K.nutrients.calib(0.30, 21); dysfunction within 3 weeks at 13 mg/d, S0376/S0377; f 0.30 open S1074
            kFemale = 0.57, -- female k multiplier (44 % vs 77 % affected, S0378), design-phase-v1 game choice (open S1075)
            ladder = {
                0.70, -- marginal: the generic rung, design-phase-v1 game choice (open S1057)
                0.45, -- depleted: the generic rung, design-phase-v1 game choice (open S1057)
                0.30, -- clinical: the 30 % fall of S0377 as the store fraction (onset 21 d), design-phase-v1 game choice (open S1074; pool open S0382)
            },
            ul = 3500, -- mg/d, S0373
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Vitamin A (ug RAE): the ingested vitA must be PREFORMED retinol only (the UL and both doses are). Conversion
        -- stops once p >= caroteneOff (S0202). No cap: hoardable to toxicity.
        vitA = {
            key = "retinol",
            unit = "ug",
            kind = "pool2",
            R = {
                900, -- male RDA ug RAE/d, S0133
                700, -- female RDA ug RAE/d, S0133
            },
            k = 0.008748517704155646, -- = ln(1/0.35)/120: K.nutrients.calib(0.35, 120); 20 ug/g = reserves for four months, S0139
            ladder = {
                0.25, -- marginal: liver < 0.1 umol/g of 0.4 (the newer proposal), S0139; S0138 (0.4 umol/g = the top of the adequate 0.1-0.7 range; the fractions divide by it)
                0.175, -- depleted: liver < 0.07 umol/g of 0.4, S0139; S0138 (0.4 umol/g = the top of the adequate 0.1-0.7 range; the fractions divide by it)
                0.06125, -- the store at which p2 crosses 0.35 = plasmaKnee x p2Clinical (S0143), design-phase-v1 game choice (open S1062)
            },
            clinicalOnP2 = true,
            p2Clinical = 0.35, -- plasma retinol 0.35 umol/L, ocular signs (WHO), S0143
            two = {
                plasmaKnee = 0.175, -- plasma held normal down to the deficient liver store, design-phase-v1 game choice (open S1062)
                caroteneOff = 1.0, -- carotene conversion x0 at liver p >= 1 (> 0.4 umol/g), S0202
            },
            ul = 3000, -- ug/d preformed, rung 1, S0136/S1024
            chronic = {
                perDay = 7500, -- ug/d hepatotoxicity, rung 2, S0149
                store = 7.2, -- liver p >= 2.87/0.4 umol/g, rung 2, S0150
            },
            acute = {
                abs = 90000, -- ug in one sitting, rung 2, S1025: 100 x the MALE RDA for both sexes (S1025); the engine reads one scalar - a female threshold of 70000 is a known simplification
            },
        },
        -- Vitamin D: p in units of 25(OH)D / 75 nmol/L (open S1065). No cutaneous term: no outdoor-daylight read exists
        -- (open S1064), so with no sun no diet keeps D replete.
        vitD = {
            key = "vitD",
            unit = "ug",
            kind = "pool",
            R = {
                15, -- male RDA ug/d (19-70 y), S0157
                15, -- female RDA ug/d (19-70 y), S0157
            },
            k = 0.011552453009332421, -- = ln2/60: K.nutrients.kFromHalfLife(60); parent D3 half-life ~2 months, S0161
            ladder = {
                0.67, -- marginal below 50/75 nmol/L (sufficiency above 50), S0159/S1005; the 75 unit open S1065
                0.40, -- depleted below 30/75 nmol/L, S0159/S1005; the 75 unit open S1065
                0.17, -- clinical below ~12.5/75 nmol/L, design-phase-v1 game choice (open S1066)
            },
            ul = 100, -- ug/d, rung 1, S0158/S1029
            chronic = {
                perDay = 250, -- ug/d sustained, rung 2 (toxicity unlikely below 250), S1029
                store = 5, -- p >= 375/75 nmol/L, rung 2, S1030
            },
        },
        -- Vitamin E: a ledger (tracked, no grade); no dietary deficiency.
        vitE = {
            key = "vitE",
            unit = "mg",
            kind = "ledger",
            R = {
                15, -- male RDA mg/d alpha-tocopherol, S0171
                15, -- female RDA mg/d alpha-tocopherol, S0171
            },
            ul = 300, -- mg/d supplemental (EFSA), S0173
            ulBasis = "supplement", -- the UL is on vitamin E as a supplement (S0173): no food intake meets it
        },
        -- Vitamin K: no clinical effect is defensible (S0963), so nothing maps on its grade. No UL (S0186).
        vitK = {
            key = "vitK",
            unit = "ug",
            kind = "pool",
            scale = "perKg",
            R = {
                1, -- male AI ug per kg body mass per day (EFSA), S0185
                1, -- female AI ug per kg body mass per day (EFSA), S0185
            },
            k = 0.25946357728426606, -- = calibAt(0.155, 13, 10/80): S0961 (plasma K1 to 15.5 % of baseline after 13 d at ~10 ug/d from an 80 ug/d baseline; R is the intake that holds p = 1, so the baseline, not the IOM AI S0184); S0962 cross-check p(21) ~ 0.516 vs 0.529 measured
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Pantothenate: a ledger; no dietary deficiency. No UL (S0280).
        pantothenate = {
            unit = "mg",
            kind = "ledger",
            R = {
                5, -- male AI mg/d, S0277
                5, -- female AI mg/d, S0277
            },
        },
        -- Biotin: untracked. The only deficiency route is a raw-egg-white staple (S0316) and the food data carries no
        -- raw-egg flag, so its p stays 1. No UL (S0322).
        biotin = {
            unit = "ug",
            kind = "counter",
            R = {
                30, -- male AI ug/d, S0310
                30, -- female AI ug/d, S0310
            },
        },
        -- Iron: two compartments, stepped by K.interact.two; ironGrade = g. No pCap: eta(p) is the repletion limit.
        iron = {
            key = "iron",
            unit = "mg",
            kind = "pool2",
            R = {
                8, -- male RDA mg/d, S0431
                18, -- female RDA mg/d (19-50 y), S0431
            },
            absorb = 0.18, -- K.stomach.BIOAVAIL.iron, the RDA's assumed bioavailability, S0434
            L = {
                1.0, -- male basal loss mg/d (0.9-1.0), S0437
                1.5, -- female basal loss mg/d (menstruating average), S0437
            },
            ladder = {
                0.50, -- marginal below half the store: design-phase-v1 game choice (open S1057)
                0.15, -- depleted: stores exhausted with Hb normal (stage 1-2), S0438; the 0.15 store fraction design-phase-v1 game choice (open S1057)
                0.01, -- game choice: never read (no k, so dialExp is 0; gradeTwo caps the store grade at 3)
            },
            clinicalOnP2 = true,
            p2Clinical = 0.88, -- Hb iron fraction at the anaemia cut-off, design-phase-v1 game choice (open S1079)
            two = {
                totalPerKg = {
                    50, -- male total body iron mg/kg, S0435
                    40, -- female total body iron mg/kg (menstruating), S0435
                },
                storeShare = 0.25, -- the mobilisable store ~25 % of total (S0436); the female share design-phase-v1 (open S1077)
                hbShare = 0.6666666666666666, -- = 2/3, almost two-thirds in circulating haemoglobin, S0436
                xMax = 30, -- mg/d store-to-Hb transfer ceiling, game choice (the Hb rise rate is open S0703)
                etaK = 0.5, -- eta(p) = 1 - 0.5 x clamp(p): direction S0535, magnitude design-phase-v1 (open S1078)
            },
            ul = 45, -- mg/d ingested (GI), rung 1, S0433/S1031
            acute = {
                perKg = {
                    20, -- mg/kg in one sitting, rung 2, S0442/S1032
                    60, -- mg/kg in one sitting, rung 3 (lethal), S1033
                },
            },
        },
        -- Zinc: no reserve; its e24 drives copper (the 40 mg/d UL).
        zinc = {
            key = "zinc",
            unit = "mg",
            kind = "pool",
            R = {
                11, -- male RDA mg/d, S0444
                8, -- female RDA mg/d, S0444
            },
            k = 0.031437653896880594, -- = -ln((0.5 - 4/11)/(1 - 4/11))/49: K.nutrients.calibAt(0.5, 49, 4/11); 7 wk at 3-5 mg/d, S0450; f 0.5 open S1083
            ul = 40, -- mg/d, rung 1 and the copper drive, S0446/S1034
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Copper: derived; it falls only under zinc excess (S0537) and recovers toward 1. Dietary deficiency is unreported.
        copper = {
            unit = "ug",
            kind = "derived",
            R = {
                900, -- male RDA ug/d, S0470
                900, -- female RDA ug/d, S0470
            },
            derived = {
                kcu = 0.02, -- per day, game choice (the zinc-to-copper dose-response is open S0572)
                ulZn = 40, -- mg/d zinc UL the loss runs above, S0446
            },
            ul = 10000, -- ug/d, unreachable from food, S0472
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Magnesium: the phytate factor and the alcohol/caffeine losses are K.interact's.
        magnesium = {
            key = "magnesium",
            unit = "mg",
            kind = "pool",
            R = {
                400, -- male RDA mg/d (19-30 y), S0419
                310, -- female RDA mg/d (19-30 y), S0419
            },
            absorb = 0.325, -- K.stomach.BIOAVAIL.magnesium, fractional absorption with no added phytate, S0536
            k = 0.013, -- = R_abs/store = 400 x 0.325/10 000, the store 10 000 mg exchangeable soft tissue = 40 % of ~25 g (t1/2 53 d), S0422/S0423
            ladder = {
                0.70, -- marginal: the generic rung, design-phase-v1 game choice (open S1057)
                0.45, -- depleted: the generic rung, design-phase-v1 game choice (open S1057)
                0.25, -- clinical (tetany): the generic rung, design-phase-v1 game choice (open S1085; timing open S0563)
            },
            ul = 350, -- mg/d from supplements only, S0421
            ulBasis = "supplement", -- no UL on food magnesium (S0421): no food intake meets it
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Calcium: a bone counter; it takes the absorbed amount, so absorb is never applied again.
        calcium = {
            key = "calcium",
            unit = "mg",
            kind = "counter",
            R = {
                1000, -- male RDA mg/d, S0408
                1000, -- female RDA mg/d, S0408
            },
            absorb = 0.25, -- K.stomach.BIOAVAIL.calcium, ~25 % of intake, S0413
            counter = {
                lossPerDay = 200, -- mg/d obligatory renal loss, S0414
                skeleton = {
                    1400, -- male skeletal calcium g at maturity, S0411
                    1200, -- female skeletal calcium g at maturity, S0411
                },
            },
            ul = 2500, -- mg/d, S0410
        },
        -- Iodine: thyroid up-regulation would slow it (direction only).
        iodine = {
            key = "iodine",
            unit = "ug",
            kind = "pool",
            R = {
                150, -- male RDA ug/d, S0456
                150, -- female RDA ug/d, S0456
            },
            k = 0.01, -- = R/store = 150/15 000, the store 15 000 ug thyroid iodine (t1/2 69 d), S0456/S0459
            ladder = {
                0.70, -- marginal: the generic rung, design-phase-v1 game choice (open S1057)
                0.45, -- depleted: the generic rung, design-phase-v1 game choice (open S1057)
                0.25, -- clinical (goitre/hypothyroid): the generic rung, design-phase-v1 game choice (open S1088; onset open S0464)
            },
            ul = 1100, -- ug/d, S0458
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Selenium: excess only. No acute or lethal number ships: that row is open (S1054).
        selenium = {
            key = "selenium",
            unit = "ug",
            kind = "excessOnly",
            R = {
                55, -- male RDA ug/d, S0465
                55, -- female RDA ug/d, S0465
            },
            ul = 400, -- ug/d, rung 1, S0467/S1038
            chronic = {
                perDay = 5000, -- ug/d endemic selenosis, rung 2, S0469
            },
        },
        -- Fibre: a counter, the 7-day EMA of intake/R (S0483); no clinical rung.
        fibre = {
            key = "fibre",
            unit = "g",
            kind = "counter",
            R = {
                38, -- male AI g/d (19-50 y), S0479
                25, -- female AI g/d (19-50 y), S0479
            },
            counter = {
                kEma = 0.19804205158855578, -- = ln2/3.5: K.nutrients.kFromHalfLife(3.5), design-phase-v1 game choice (open S1090)
            },
            ladder = {
                0.5, -- marginal: the EMA of intake/R, design-phase-v1 game choice (open S1090)
                0.25, -- depleted: the EMA of intake/R, design-phase-v1 game choice (open S1090)
                0.0, -- game choice: no clinical rung for fibre (open S1090)
            },
        },
        -- Essential fats (g LA + ALA): the real-food threshold is open (S0571). No UL.
        efa = {
            key = "efa",
            unit = "g",
            kind = "pool",
            R = {
                18.6, -- male AI g/d = LA 17 (S0497) + ALA 1.6 (S0488)
                13.1, -- female AI g/d = LA 12 (S0497) + ALA 1.1 (S0488)
            },
            k = 0.049510512897138946, -- = ln(1/0.25)/28: K.nutrients.calib(0.25, 28); triene:tetraene > 0.4 at 4 weeks fat-free, S0500/S0501; f open S1089
            ladder = {
                0.70, -- marginal: the generic rung, design-phase-v1 game choice (open S1057)
                0.45, -- depleted: the generic rung, design-phase-v1 game choice (open S1057)
                0.25, -- clinical: the generic rung, design-phase-v1 game choice (open S1089)
            },
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Sodium and potassium: K.fluids' fast pools, not stepped by the engine.
        sodium = {
            key = "sodium",
            unit = "mg",
            kind = "fast",
            R = {
                1500, -- male AI mg/d, S0389
                1500, -- female AI mg/d, S0389
            },
        },
        potassium = {
            key = "potassium",
            unit = "mg",
            kind = "fast",
            R = {
                3400, -- male AI mg/d, S0398
                2600, -- female AI mg/d, S0398
            },
        },
        -- Caffeine and ethanol: K.acute's states; no requirement, never graded here.
        caffeine = {
            key = "caffeine",
            unit = "mg",
            kind = "acute",
        },
        ethanol = {
            key = "ethanol",
            unit = "g",
            kind = "acute",
        },
    },
}
