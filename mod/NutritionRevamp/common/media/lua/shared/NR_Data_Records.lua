-- NR_Data_Records.lua -- not a kernel file: the 27 declarative nutrient records the generic engine
-- (NR_Kernel_Nutrients.lua, K.nutrients.minute) loops over, as NR.data.records = { ORDER, REC } (Plan 4,
-- formulas briefing A2/A6, rulings 2-6).
-- Fix-1 rulings T7-1 (vitK k solved against its trial baseline), T7-2 (vitD uncapped) and T7-3 (per-record
-- chronic.holdD, B6 180 d).
-- Every number sits on its own line with its row: a settled S id, or `design-phase-v1` / `game choice`
-- naming the open row it rests on (testing/tests/kernel/test_data_records.py enforces it on this file).
-- This file sorts BEFORE the kernels (NR_Data_ < NR_Kernel_), so it never calls K at load time: each
-- derived rate is a literal computed in doubles, its expression and the kernel function that gives it
-- written in the comment, and the test recomputes it through that function to 1e-9.
-- Fields the engine reads (task-6 report): kind, R, scale, Rscale, absorb, k, pCap, ladder,
-- clinicalOnP2, p2Clinical, ul, chronic.perDay, chronic.holdD, chronic.store, acute.perKg, acute.abs, dialExp.
-- Fields for the adapters, never read by the engine: key (the vector key; nil when the vector has none),
-- key2, unit (NR.data.UNITS for the key), Rmin, store (display mass at p = 1), L, two, counter, derived,
-- sun, kFemale, trpShare, trpPerNE.
-- R is {male, female} per day on the INGESTED basis; the engine's absorbed requirement is R x absorb, and
-- absorb mirrors K.stomach.BIOAVAIL for the key (nil = the engine's default 1.0, open row S1060).
-- Ladders are {marginal, depleted, clinical} on p; a record with no ladder takes the engine's generic one.
-- Omitted with no record (ruling 3): phosphorus, manganese, omega-3 EPA/DHA.
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
        -- Vitamin C: one pool calibrated to scurvy at 40 d; Store_eff = 76.5/0.0474 = 1613 mg closes on the 1500 mg pool.
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
            store = 1500, -- mg total body pool (display; the Store_eff cross-check closes), S0222
        },
        -- Thiamine: energy-scaled requirement; the RDA rides as Rmin for Task 11 (the engine reads no Rmin). At the
        -- fixture's ~10 MJ/d the per-MJ requirement is 1.0 mg/d against the 1.2 mg/d RDA. No UL (S0238). Alcohol
        -- raises the drain (S0250 direction; the lambda magnitude is open S0553 and lives in K.interact, Task 10).
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
                1.2, -- male RDA mg/d, S0235 (not read by the engine; Task 11)
                1.1, -- female RDA mg/d, S0235 (not read by the engine; Task 11)
            },
            k = 0.05134423559703299, -- = ln2/13.5: K.nutrients.kFromHalfLife(13.5); the 9-18 d whole-body half-life midpoint, S0240
            ladder = {
                0.70, -- marginal: the generic rung, design-phase-v1 game choice (open S1057)
                0.45, -- depleted: the generic rung, design-phase-v1 game choice (open S1057)
                0.4166666666666667, -- clinical = 0.5/1.2: K.nutrients.fFromThreshold(0.5, 1.2); signs below 0.5 mg/d, S0242 (reached at 17.05 d)
            },
            pCap = 1.0, -- surplus excreted from the 1-12 h fast pool, S0241 (judgement)
        },
        -- Riboflavin: no store row and no onset row (S0260 open), so it takes thiamine's rate. No UL (S0255).
        riboflavin = {
            key = "riboflavin",
            unit = "mg",
            kind = "pool",
            R = {
                1.3, -- male RDA mg/d, S0253
                1.1, -- female RDA mg/d, S0253
            },
            k = 0.05134423559703299, -- = thiamine's ln2/13.5, design-phase-v1 game choice (open S1067; onset open S0260)
            pCap = 1.0, -- urinary excretion rises sharply above ~1 mg/d (tissue saturation), S0257
        },
        -- Niacin (mg NE): energy-scaled; NE = niacin + tryptophan/60, the tryptophan read from protein at trpShare.
        -- The UL is nicotinic acid only (S0269, S0274): it can only fire on a supplement item.
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
                16, -- male RDA mg NE/d, S0267 (not read by the engine; Task 11)
                14, -- female RDA mg NE/d, S0267 (not read by the engine; Task 11)
            },
            k = 0.025205352020361647, -- = ln(1/0.25)/55: K.nutrients.calib(0.25, 55); pellagra at 50-60 d, S0271; f 0.25 design-phase-v1 (open S1068)
            ladder = {
                0.70, -- marginal: the generic rung, design-phase-v1 game choice (open S1057)
                0.45, -- depleted: the generic rung, design-phase-v1 game choice (open S1057)
                0.25, -- clinical: the generic rung, design-phase-v1 game choice (open S1068)
            },
            ul = 35, -- mg/d, nicotinic acid only (flushing), S0269
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
            trpShare = 0.011, -- tryptophan as 1.1 % of dietary protein, design-phase-v1 game choice (open S1069)
            trpPerNE = 60, -- mg tryptophan per mg NE, S0270
        },
        -- Vitamin B6: R = max(RDA, 0.016 mg/g protein). Cross-check: Store_eff = 1.3/0.0239 = 54 mg against the
        -- 170 mg body store (S0297), x3 off; the ONSET wins (ruling 2), stated.
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
        -- Folate (ug DFE): depleted 0.10 at 90 d; clinical (anaemia) at p(120 d). Cross-check: Store_eff =
        -- 400/0.0256 = 15.6 mg against 5-10 mg (S0333), x1.5-3 off; the ONSET wins (ruling 2), stated.
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
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Vitamin B12: two compartments at real scale (ruling 5's dial exponent 1, computed: 2303 d > 90): store p
        -- first-order, functional p2 = min(1, p/fThreshold) (Task 10); clinical when p2 < 1, accruing dmg hours that
        -- repletion does not clear (S0363). The per-eat absorption ceiling is Task 10/12's. No UL (S0353).
        -- Requirement IOM 2.4 (ruling 6); EFSA's 4 (S0351) and NNR's 2 (S0388) noted.
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
            store = 2500, -- ug total body store at p = 1 (display), S0354
        },
        -- Choline: the female rate x0.57 is for Task 11 (the engine reads one k). The UL is supplement-only.
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
                0.30, -- clinical: the 30 % fall of S0377 as the store fraction, briefing A2's calibration rung (onset 21 d, S0376/S0377); the plan table's 'generic' superseded by this derivation, design-phase-v1 game choice (open S1074; pool open S0382)
            },
            ul = 3500, -- mg/d, S0373
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Vitamin A (ug RAE): liver p (1.0 = 0.4 umol/g, the top of the balance zone) and plasma p2 = min(1,
        -- p/plasmaKnee) (Task 10). The engine's ingested vitA must be PREFORMED retinol only: the UL, the chronic
        -- dose and the acute dose are preformed (carotene exempt). Carotene conversion is x0 once p >= caroteneOff
        -- (S0202). No cap: hoardable to toxicity.
        vitA = {
            key = "retinol",
            key2 = "carotene",
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
        -- Vitamin D: one compartment at the parent half-life; p in units of serum 25(OH)D / 75 nmol/L (the 75 a
        -- design-phase-v1 game choice, open S1065). The cutaneous term kSun x outdoor daylight minutes is Task 11's
        -- to set; it ships 0 here, so with no sun no diet keeps D replete (formulas briefing L3).
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
            sun = {
                kSun = 0.0, -- p per outdoor daylight minute: 0 until Task 11 sets it, design-phase-v1 game choice (open S1064)
                note = "cutaneous term labelled; open row S1064 (Task 1)",
            },
        },
        -- Vitamin E: a ledger (tracked, no grade); the adipose turnover is open (S0213); no dietary deficiency.
        vitE = {
            key = "vitE",
            unit = "mg",
            kind = "ledger",
            R = {
                15, -- male RDA mg/d alpha-tocopherol, S0171
                15, -- female RDA mg/d alpha-tocopherol, S0171
            },
            ul = 300, -- mg/d supplemental (EFSA), S0173
        },
        -- Vitamin K: EFSA 1 ug/kg (ruling 6: the only requirement that closes both restriction trials); no clinical
        -- effect is defensible (S0963/S0964), so Plan 5 maps nothing on its grade. No UL (S0186).
        vitK = {
            key = "vitK",
            unit = "ug",
            kind = "pool",
            scale = "perKg",
            R = {
                1, -- male AI ug per kg body mass per day (EFSA), S0185
                1, -- female AI ug per kg body mass per day (EFSA), S0185
            },
            k = 0.25946357728426606, -- = calibAt(0.155, 13, 10/80): S0961 (plasma K1 to 15.5 % of baseline after 13 d at ~10 ug/d from an 80 ug/d baseline; R is the intake that holds p = 1, so the baseline, not the IOM AI S0184 that ruling 6 rejects); S0962 cross-check p(21) ~ 0.516 vs 0.529 measured
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Pantothenate: a ledger; no dietary deficiency, pool open (S0287). No UL (S0280).
        pantothenate = {
            unit = "mg",
            kind = "ledger",
            R = {
                5, -- male AI mg/d, S0277
                5, -- female AI mg/d, S0277
            },
        },
        -- Biotin: a counter of raw-egg-staple days (S0316: raw egg white blocks absorption; 28 d asymptomatic S0319;
        -- markers by day 14 S0320), stepped by Task 10. No vector key; pool open (S0315). No UL (S0322).
        biotin = {
            unit = "ug",
            kind = "counter",
            R = {
                30, -- male AI ug/d, S0310
                30, -- female AI ug/d, S0310
            },
            counter = {
                cosmeticDays = 90, -- raw-egg days to the cosmetic rung, design-phase-v1 game choice (open S1076)
            },
        },
        -- Iron: two compartments (A6), store S and haemoglobin iron H in mg, stepped by Task 10's ctx.two. The
        -- engine reads no L: Task 10 applies it zero-order on H. ironGrade = g. No pCap: eta(p) is the repletion limit.
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
                anaemiaP2 = 0.88, -- the same cut as p2Clinical, design-phase-v1 game choice (open S1079)
            },
            ul = 45, -- mg/d ingested (GI), rung 1, S0433/S1031
            acute = {
                perKg = {
                    20, -- mg/kg in one sitting, rung 2, S0442/S1032
                    60, -- mg/kg in one sitting, rung 3 (lethal), S1033
                },
            },
        },
        -- Zinc: no reserve; the 7-week change on 3-5 mg/d solved at the nonzero intake. The phytate inhibition (the
        -- magnesium slope reused, open S1084) is Task 10's. Its e24 drives copper (the 40 mg/d UL).
        zinc = {
            key = "zinc",
            unit = "mg",
            kind = "pool",
            R = {
                11, -- male RDA mg/d, S0444
                8, -- female RDA mg/d, S0444
            },
            k = 0.031437653896880594, -- = -ln((0.5 - 4/11)/(1 - 4/11))/49: K.nutrients.calibAt(0.5, 49, 4/11); 7 wk at 3-5 mg/d, S0450; f 0.5 open S1083 (J's 0.0310169 used 4/11 rounded to 0.36)
            ul = 40, -- mg/d, rung 1 and the copper drive, S0446/S1034
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Copper: derived; it falls only under zinc excess, dp/dt = -kcu x max(0, e24_zn - ulZn)/ulZn, and recovers at
        -- kcu toward 1 (Task 10). Dietary deficiency is unreported (S0475; the clinical signs S0474; S0537 the zinc x copper reading).
        copper = {
            unit = "ug",
            kind = "derived",
            R = {
                900, -- male RDA ug/d, S0470
                900, -- female RDA ug/d, S0470
            },
            derived = {
                from = "zinc",
                kcu = 0.02, -- per day, game choice (the zinc-to-copper dose-response is open S0572)
                ulZn = 40, -- mg/d zinc UL the loss runs above, S0446
            },
            ul = 10000, -- ug/d, unreachable from food, S0472
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
        },
        -- Magnesium: k = R_abs/store with the exchangeable soft-tissue store ~40 % of 25 g. The phytate factor
        -- exp(-0.00093 x mg) (S0536) and the alcohol/caffeine losses (open S1086/S1087) are Task 10's.
        magnesium = {
            key = "magnesium",
            unit = "mg",
            kind = "pool",
            R = {
                400, -- male RDA mg/d (19-30 y), S0419
                310, -- female RDA mg/d (19-30 y), S0419
            },
            absorb = 0.325, -- K.stomach.BIOAVAIL.magnesium, fractional absorption with no added phytate, S0536
            k = 0.013, -- = R_abs/store = 400 x 0.325/10 000 (t1/2 53 d), S0422/S0423
            ladder = {
                0.70, -- marginal: the generic rung, design-phase-v1 game choice (open S1057)
                0.45, -- depleted: the generic rung, design-phase-v1 game choice (open S1057)
                0.25, -- clinical (tetany): the generic rung, design-phase-v1 game choice (open S1085; timing open S0563)
            },
            ul = 350, -- mg/d from supplements only, S0421
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
            store = 10000, -- mg exchangeable soft tissue = 40 % of ~25 g, S0422/S0423
        },
        -- Calcium: a bone counter, bone += absorbed - 200 mg/d zero-order (Task 10); a season moves it < 1 %. Used
        -- for the calcium x iron factor and display. counter.absorb is the fraction the stomach ALREADY applies
        -- (K.stomach.BIOAVAIL.calcium): Task 10 must not apply it twice to an absorbed amount.
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
                absorb = 0.25, -- fractional absorption, S0413
                lossPerDay = 200, -- mg/d obligatory renal loss, S0414
                skeleton = {
                    1400, -- male skeletal calcium g at maturity, S0411
                    1200, -- female skeletal calcium g at maturity, S0411
                },
            },
            ul = 2500, -- mg/d, S0410
        },
        -- Iodine: k = R/thyroid store; thyroid up-regulation would slow it (direction only).
        iodine = {
            key = "iodine",
            unit = "ug",
            kind = "pool",
            R = {
                150, -- male RDA ug/d, S0456
                150, -- female RDA ug/d, S0456
            },
            k = 0.01, -- = R/store = 150/15 000 (t1/2 69 d), S0456/S0459
            ladder = {
                0.70, -- marginal: the generic rung, design-phase-v1 game choice (open S1057)
                0.45, -- depleted: the generic rung, design-phase-v1 game choice (open S1057)
                0.25, -- clinical (goitre/hypothyroid): the generic rung, design-phase-v1 game choice (open S1088; onset open S0464)
            },
            ul = 1100, -- ug/d, S0458
            pCap = 1.0, -- design-phase-v1 game choice: the default cap, no saturation row (ruling 4)
            store = 15000, -- ug thyroid iodine, S0459
        },
        -- Selenium: excess only (Keshan needs regional soil). The UL is the FNB's 400 (EFSA's 255, S1039, noted).
        -- No acute or lethal number ships: that row is open (S1054).
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
        -- Fibre: a counter, the 7-day EMA of intake/R (Task 10); relief needs sustained intake ~4 weeks (S0483).
        -- The ladder on the EMA is the counter's marginal/depleted, with no clinical rung.
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
                marginal = 0.5, -- EMA of intake/R, design-phase-v1 game choice (open S1090)
                depleted = 0.25, -- EMA of intake/R, design-phase-v1 game choice (open S1090)
            },
            ladder = {
                0.5, -- marginal = counter.marginal, design-phase-v1 game choice (open S1090)
                0.25, -- depleted = counter.depleted, design-phase-v1 game choice (open S1090)
                0.0, -- game choice: no clinical rung for fibre (open S1090)
            },
        },
        -- Essential fats (g LA + ALA): the PN-only evidence; real-food threshold open (S0571). No UL.
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
        -- Sodium and potassium: the fast pools (Task 8's K.fluids), not stepped by the engine. Potassium ships the
        -- settled 2019 AI (S0398), not the plan's 4700 (no register row carries it).
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
        -- Caffeine and ethanol: the acute states (Task 9's K.acute); no requirement, never graded here.
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
