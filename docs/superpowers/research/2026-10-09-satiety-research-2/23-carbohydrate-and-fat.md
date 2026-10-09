# Satiety research 2, carbohydrate and fat harvest (2026-10-09)

The harvest report of Task 23 of Satiety research 2 (2026-10-09), followed by its citation review. The review's corrections stand over the report wherever they disagree; the rows in docs/reference/science.tsv carry the corrected cells.

# Task 23 report: carbohydrate and fat and satiety (carbohydrate quality, fat quality, processing)

Model: claude-opus-5-5. Satiety research 2, harvester 23, 2026-10-09.

The part file is `23-science-part.tsv`, with 42 rows: 40 settled, 2 open and 0 unverified.
- On a scratch copy of the register, `science_delta.py apply --dry-run` minted S23.1–S23.42 as S1337–S1378.
- The real apply on that copy, then `science_check.py --register <copy>`, gave 0 findings. `science_check.py --part` also gave 0 findings.
- The real register is untouched.

Every settled row was resolved against Europe PMC, with title, first author and year matched. I read every number from the abstract, through Europe PMC or PubMed. Where Europe PMC had the full text, I read the numbers from it: Hall 2019, Sun 2016 and Dicken 2025.

**The source cell.** The brief says the cell reads "Satiety research 2, … harvest (2026-10-09)". That string fails `SOURCE_RX` (`<report>.md § <heading>`). So I used the form of S1334–S1336: `docs/superpowers/specs/2026-10-08-satiety-physiology-design.md § 5a, Satiety research 2, carbohydrate and fat harvest (2026-10-09)`. The controller can rewrite it uniformly across the seven parts.

**Already in the register and not re-minted:**
- Woodend 2001 (S1227)
- Melanson 1999 (S1228)
- Rolls 1999 (S1229)
- Raben 2003 (S1225)
- Holt 1995 (S1226)
- Marmonier 2000 (S1224)
- Thornhill 2019 (S1261)
- Anderson 2010 (S1262)
- Anderson & Woodend 2003 (S1263)
- DiMeglio & Mattes 2000 (S1264)
- Mourao 2007 (S1265)
- Almiron-Roig 2013 (S1266)
- Almiron-Roig 2003 (S1267)
- Nymo 2017 (S1259)
- Reynolds 2019 (S0507, S0508)
- the energy-density MA (S1230)

**Read but not minted:**
- Page 2013 (JAMA, fructose against glucose): its outcomes are hypothalamic blood flow and hormones only, so it is mechanism-only.
- Kozimor 2013: PYY only, with no behavioural difference.
- Mumme 2015 (MCT and weight): not satiety; the review flags commercial bias.
- Stewart 2011 (oleic acid thresholds and intraduodenal suppression): a single small study; the Tucker 2017 MA carries the sensing question.

## 1. Fat against carbohydrate per kcal (the fat paradox)

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S23.1 | Blundell 1993 | a 362 kcal carbohydrate supplement suppressed appetite at 90 min; the same fat supplement did nothing; obese subjects ate 2x the energy from high-fat items | EXP | n not given; no certainty rating |
| S23.2 | Lissner 1987 | 2 wk covert: −11.3 % intake on low-fat, +15.4 % on high-fat, relative to medium-fat | EXP | n = 24; fat and ED co-vary |
| S23.3 | Stubbs 1995a | 7 d calorimeter: energy balance −0.27 / 0.77 / 2.58 MJ/d at 20/40/60 % fat | EXP | n = 6; fat and ED co-vary |
| S23.4 | Stubbs 1995b | free-living intake 9.11 / 10.32 / 12.78 MJ/d | EXP | n = 7 |
| S23.5 | Hooper 2020 (Cochrane) | lower fat, ≥ 6 mo, no weight-loss intent: −1.4 kg (−1.7 to −1.1) | MA | 26 RCTs, n = 53,875; I² 75 %; GRADE high |
| S23.6 | Hall 2021 | low-fat diet: 689 ± 73 kcal/d less intake than keto (544 final week) | RCT | n = 20 inpatient crossover |

**Verdict.**
- **Best estimate.** At matched energy density, fat and carbohydrate sate alike per kcal: Rolls 1999 (S1229) and Raben 2003 (S1225), both already in the register.
  - The passive overconsumption of high-fat diets is large: +15 % (S23.2) and +2.6 MJ/d (S23.3).
  - In every covert-manipulation study, though, it travels with energy density.
  - Over months the fat share moves intake only a little: −1.4 kg for a lower-fat diet (S23.5).
- **Certainty.**
  - Moderate that the overconsumption is mostly energy density: the Rolls test separates the two, and the MA is GRADE high on the chronic size.
  - Low on any per-kcal ordering of fat against carbohydrate.
- **What the lower-quality evidence says that the best does not support:**
  - Blundell 1993 reads fat as having no satiety at all, and Melanson (S1228) reads it as more satiating. Neither survives a test at matched energy density.
  - Boden 2005 (S23.41, an uncontrolled inpatient study) reads low-carbohydrate as cutting intake by about 1,000 kcal/d. That is against the usual diet, not against an isoenergetic-density control. Hall 2021, an RCT, reads the high-fat keto diet as giving more intake than low-fat. **The RCT wins.**

## 2. Sugar against starch, GI and GL, fructose against glucose, sucrose

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S23.7 | Sun 2016 | breakfast GI → next-meal intake ES −0.01 (−0.21, 0.18) | MA | 11 trials, n = 183; I² 46 %; one high-quality trial |
| S23.8 | Bornet 2007 | short-term (1 d) low GI more satiating; long-term inconclusive | MA (SR, unpooled) | 32 studies; industry authors |
| S23.9 | Zafar 2019 | low-GI diets: small weight benefit; SMD −0.26 where ΔGI ≥ 20 | MA | 101 studies, n = 8,527 |
| S23.10 | Te Morenga 2012 | isoenergetic sugar-for-carbohydrate swap: 0.04 kg (−0.04 to 0.13); ad libitum ± sugar ∓0.80 / +0.75 kg | MA | 30 RCTs and 38 cohorts; GRADE methods |
| S23.11 | Raben 2002 | 10 wk sucrose supplements (mostly drinks): intake +1.6 MJ/d, weight +1.6 kg | RCT | n = 41 |
| S23.12 | Sørensen 2014 | the same trial at week 10: sucrose group less full, despite +3.3 MJ | RCT | n = 22 subgroup |
| S23.14 | Akhavan 2007 | 300 kcal solutions: sucrose = HFCS = G50:F50; high-glucose cut intake more | RCT | n = 12 and 19 |
| S23.15 | Rodin 1990 | fructose preload cut buffet intake more than glucose | RCT | n not given |
| S23.16 | Luo 2015 | fructose: more hunger and more desire for food than glucose | RCT | n = 24 |

**Verdict.**
- **GI.** The best estimate is no effect of GI on the next meal's intake (Sun, low certainty: small, mostly low-quality trials with moderate heterogeneity).
  - The time-course difference (fast carbohydrate acts at about 1 h, slow at 2–3 h; S1262, S1263) is real but small and offsetting.
  - Bornet's positive short-term reading is unpooled, industry-authored and confounded by fibre, so it is weaker than the Sun null.
- **Sugar against other carbohydrate per kcal.** No difference: the isoenergetic swap does nothing to weight (Te Morenga, moderate certainty). Sugar acts through the energy it adds ad libitum, which is the liquid-sugar question in § 3.
- **Fructose against glucose.** Very low certainty. Three small crossovers disagree: Akhavan and Luo find glucose more sating, Rodin finds fructose more sating. Sucrose and HFCS do not differ (Akhavan). This stays neutral.

## 3. Liquid sugar and sugar-sweetened beverages

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S23.17 | Malik 2013 | adding SSBs in adult RCTs: +0.85 kg (0.50, 1.20) | MA | 5 trials, n = 292 (adults); no GRADE |
| S23.13 | Reid 2007 | 1800 kJ/d of sucrose drinks for 4 wk: intake up by just under 1000 kJ/d over baseline, so food fell by about 800 kJ; no appetite effect | RCT | n = 133 women |
| S23.18 | Mattes 1996 | intake rose on every beverage day; cola energy got little compensation | EXP | n = 16 |
| S23.19 | de Ruyter 2012 | masked 104 kcal/d drink for 18 mo: weight +1.02 kg against sugar-free (CI −1.54 to −0.48) | RCT | n = 641 children, double-blind |
| (S1264) | DiMeglio & Mattes 2000 | −17 % compensation for liquid against 118 % for solid | RCT | already in the register |

**Verdict.**
- **Best estimate.** Liquid sugar is under-compensated over days to months.
  - Adding SSBs raises weight (Malik's adult RCTs; de Ruyter's double-blind 18-month trial; Raben's +1.6 MJ/d).
  - The size of the compensation spans from about −17 % (DiMeglio, n = 15) to roughly 45 %, which is Reid's 1800 kJ added against an intake rise of just under 1000 kJ.
    - That 45 % is my arithmetic on Reid's two figures, not the paper's own number.
- **Certainty.** Moderate that the compensation is incomplete; low on its size.
- **What the lower-quality evidence says.** Acute single-preload studies are inconclusive about liquids against solids (S1266, S1267). The weakness of liquid sugar is a days-to-weeks effect, not a one-meal effect.

## 4. Fat type: MCT against LCT, saturation, omega-3, oral fat sensing

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S23.20 | Maher & Clegg 2021 | MCT against LCT: intake ES −0.444 (−0.808, −0.080); no appetite-rating effect | MA | 11 of 17 studies, n = 291 total |
| S23.21 | Van Wymelbeke 1998 | any added fat delayed the meal request; the MCT lunch was smaller; MUFA = SFA | RCT | n = 12, time-blinded |
| S23.22 | St-Onge 2014 | lunch 532 kcal after MCT against 804 kcal after LCT | RCT | n = 7 |
| S23.23 | Feltrin 2004 | intraduodenal C12 cut intake to 1,747 kJ (control 4,604) with nausea; C10 did not | RCT | n = 8; infusion, mechanism only |
| S23.24 | Alfenas & Mattes 2003 | butter = canola = peanut oil on appetite and 24 h intake | EXP | n not given |
| S23.25 | Sasanfar 2024 | n-3: appetite SMD 0.458 (−0.327, 1.242), null; desire to eat SMD 1.07 | MA | 15 CTs, n = 1,504 |
| S23.26 | Parra 2008 | high n-3 during restriction: more fullness and less hunger at 2 h | RCT | n = 233, VAS only |
| S23.27 | Tucker 2017 | fatty-acid taste thresholds: lean = obese | MA | 7 studies |

**Verdict.**
- **MCT.** It may lower the next meal's intake modestly (ES −0.44). Certainty is low: the studies are small and heterogeneous, and the review gives no certainty rating.
  - Appetite ratings do not move.
  - The one mechanism study (Feltrin) shows the gut fat signal rising steeply with chain length: C12 suppresses intake, C10 does not. That runs against an MCT satiety mechanism through the gut.
- **Saturated against unsaturated LCT.** No difference (moderate certainty; two independent trials agree).
- **Omega-3.** The pooled null on overall appetite is the best estimate. Parra's positive reading is one trial with VAS outcomes only. Sasanfar's rise in desire to eat is a secondary outcome.
- **Oral fat sensing.** Not related to adiposity (Tucker MA). It has no game-relevant magnitude.

## 5. Ultra-processed food

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S23.28 | Hall 2019 | +508 ± 106 kcal/d on UPF; weight +0.9 against −0.9 kg | RCT | n = 20 inpatient, 2 wk per arm |
| S23.29 | Hall 2019 (mechanism) | eating rate +17 kcal/min; consumed ED 1.36 against 1.09 kcal/g; non-beverage ED of meals 1.957 against 1.057; hunger, liking and fullness unchanged | RCT | the same trial |
| S23.30 | Hamano 2024 | +813.5 kcal/d (342.4–1284.7); +1.1 kg in 1 wk; fewer chews per kcal | RCT | n = 9, open-label |
| S23.31 | Dicken 2025 | 8 wk under guideline-matched diets: weight change −2.06 % against −1.05 % (Δ −1.01 %) | RCT | n = 55 / 50 ITT; intake self-reported |
| S23.32 | Robinson 2026 | intake SMD 0.18–0.44, significance model-dependent; weight 0.65; eating rate 0.96; appetite unchanged; SMD 0.71 if UPF had higher ED against 0.02 if matched | MA | 10 RCTs; certainty low (the authors' rating) |
| S23.33 | Barros 2026 | fixed-energy UPF preloads: no effect on dinner intake (−24.5 kcal); ED moved hunger by 3.6 mm | RCT | n = 19 |
| S23.34 | Teo 2022 | hard against soft texture: −26 % energy; 482.9 against 789.4 kcal | RCT | n = 50 |
| S23.35 | Fazzino 2023 | meal intake rose with ED, eating rate and hyper-palatable items across 4 diets | COH | 2,733 meals |
| S23.36 | Robinson 2014 | slower eating: lower intake, SMD 0.45 (0.25, 0.65); no effect on later hunger to 3.5 h | MA | 22 studies, high heterogeneity |
| S23.42 (open) | — | the processing effect at matched ED, eating rate and nutrient profile | — | — |

**Verdict.**
- **Best estimate.** UPF diets, as trials have built them, raise ad libitum intake: about +500 kcal/d inpatient, and about 1 % of body weight over 8 weeks free-living.
- **The mechanism.** The best synthesis (Robinson 2026, low certainty) puts the effect on energy density (SMD 0.71 against 0.02 at matched ED) and eating rate. Processing per se does not appear in it.
  - No trial shows a hunger or fullness difference: Hall 2019, Robinson 2026 and Barros 2026 all find none.
  - The excess intake is satiation (meal size) through rate and density, not a weaker satiety afterwards.
- **Certainty.** Moderate that UPF-as-tested raises intake; low that processing matters beyond energy density and eating rate.
- **Lower quality.** Hamano's +813 kcal/d is a 9-person open-label trial and is likely an overestimate.

## 6. Ketogenic and low-carbohydrate diets

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S23.37 | Gibson 2015 | ketosis under a VLED or KLCD: less hunger and more fullness; the changes are small | MA | pooled mm not read (paywalled abstract) |
| S23.38 | Sumithran 2013 | ketotic (BHB 0.48 mmol/l): the weight-loss ghrelin rise was suppressed and appetite was lower than after refeeding | EXP | n = 39 |
| S23.39 | Stubbs BJ 2018 | ketone ester (BHB 3.3 mM): hunger and desire to eat suppressed at 1.5 h against dextrose | RCT | n = 15 |
| S23.40 | Boden 2005 | a 14 d low-carbohydrate inpatient diet: intake 3111 → 2164 kcal/d | EXP | n = 10, no control |
| S23.6 | Hall 2021 | ad libitum keto gave 689 kcal/d more than low-fat | RCT | n = 20 |
| S23.41 (open) | — | the pooled mm and the BHB threshold | — | — |

**Verdict.**
- **Best estimate.** Ketosis blunts the rise in appetite that an energy deficit otherwise brings: Gibson (MA), Sumithran, and S1259 (Nymo) already in the register. Exogenous ketones suppress hunger acutely.
  - It is not a stronger per-meal satiety. Fed ad libitum, a keto diet gives more intake than a low-fat diet (Hall 2021, RCT).
- **Certainty.** Moderate for the direction under deficit; low for the size, since Gibson's pooled mm are unread and S23.41 is open.
- **Lower quality.** Boden's spontaneous −947 kcal/d is an uncontrolled before-after study in diabetic inpatients. It does not support "low-carb sates more per kcal".

## What the evidence says about the current model

### The shipped choices it supports

1. **Carbohydrate = fat at weight 1 per kcal in P** (ruling 11c-7).
   - The best evidence finds no per-kcal difference at matched energy density (S1229, S1225).
   - The fat paradox is carried by energy density, which the model already reads: high-fat foods carry fewer grams per kcal, so the fullness F is lower. The spec reads 31 % fewer kcal to the same hunger at 1.05 against 1.6 kcal/g.
   - That is the right order of magnitude against Lissner's ±11–15 % and Stubbs' covert diets.
   - **Keep.**
2. **Sugar = starch** (S23.10's isoenergetic null; S23.7's GI null). **Keep.**
   - The GI time-course split (about 1 h against 2–3 h; S1262, S1263) is not worth modelling: the next-meal intake effect pools to ES −0.01.
3. **Fat type neutral.** Saturated = unsaturated (S23.21, S23.24); omega-3 null (S23.25).
   - MCT is the one candidate: ES −0.44, low certainty.
   - No vanilla item is an MCT source except arguably coconut. **Keep neutral.**
4. **Contested effects ship neutral at the single-meal level.** That holds for fructose against glucose and for the acute liquid-against-solid preload.

### What it argues against, with the size of the discrepancy

1. **Liquid sugar is fully credited to P.**
   - Today a drink's carbohydrate kcal feed P at weight 1, like a solid's, and only its mass is down-weighted to LIQUID_WEIGHT 0.2 in F.
   - Over days, the evidence says liquid sugar is compensated at about −17 % to about 45 %, against about 100 % or more for solids (S1264 118 %).
   - **Size.** For a player drinking soda, the model over-sates by roughly half to all of the drink's kcal. de Ruyter reads about 1 kg extra gain over 18 months from 104 kcal/d.
   - **What the mod would read and change.**
     - It reads the item's `drinkable` / fluid flag, or the liquid lane the eat already routes to.
     - It feeds P with `W_LIQUID_CARB × kcal_carb` for drunk carbohydrate, with a game-choice value of about 0.3–0.5.
     - Certainty is moderate on the direction and low on the size.
     - **The weak spot.** Acute preload evidence (S1266, S1267) is inconclusive, and the fitted oracle (Callahan's liquid preloads, S1247) used liquid meals that did sate. A chronic-only discount cannot be expressed in a per-eat pool without moving the Callahan replay.
     - So the honest options are:
       - (a) keep the neutral ruling as a named non-reproduction of the chronic SSB rows;
       - (b) discount only carbohydrate-dominant drinks with no protein or fat (soda, juice), which leaves Callahan's mixed liquid meal untouched;
       - Angus should rule.
2. **Ketosis has no term.**
   - The deficit drive (`K.hybrid.hungerTarget`'s 0.15 floor) rises with deficit regardless of diet.
   - Evidence: in ketosis the deficit-driven appetite rise is blunted (Gibson, Sumithran, S1259). Fed ad libitum, a fat-heavy keto diet does not sate more per meal (Hall 2021).
   - **What the mod would read and change.**
     - It reads a rolling carbohydrate intake (for example, under about 50 g/day over the last 2–3 days, a game choice) together with the energy-deficit state.
     - It damps the deficit-drive term, not P.
     - Relevant to a meat-only diet, a starving player, or a fasting player.
     - The size is open (S23.41), so it ships as a labelled game choice or not at all.

### What it leaves out that the evidence says matters

1. **Eating rate and texture** (S23.36 SMD 0.45; S23.34 −26 % for hard food; S23.29 +17 kcal/min on UPF).
   - The mod cannot see how fast a player eats beyond the vanilla eat-action time.
   - It could read a per-item texture class, but no dataset field gives one.
   - Moderate certainty. **Leave out.** It is a satiation-at-the-meal effect, and the game's player chooses how much to eat anyway.
2. **Processing as a flag.**
   - The game can read processing: `Packaged` on 142 records, `CannedFood` on 41, `food_type = Candy` on 25 (all from `data/food-items.json`), plus weight for energy density.
   - The best evidence says the UPF intake effect is energy density and eating rate (S23.32: SMD 0.02 at matched ED; S23.33: no satiety effect at fixed energy). It also says appetite ratings do not differ.
   - **Recommendation.** Do not add a processing term. Energy density through F already gives a 2.8 kcal/g packaged snack less satiety per kcal than a 1.1 kcal/g stew.
     - (The 2.8 kcal/g is the energy density of Hall 2019's ultra-processed snacks, from its Table 1, read off the full text but not carried in a row.)
   - Low certainty. Moderate that adding a flag would double-count energy density.
3. **The chronic fat share** (Hooper −1.4 kg, GRADE high). It is small and already within what the energy-density path produces. **No change.**

## Slug requests and supersede candidates

- **Slugs.** None needed.
  - S23.27 (fat taste thresholds) uses the existing `perception` slug.
  - The UPF rows sit under `satiety`. A `processing` slug is not warranted for 9 rows whose measured quantity is intake.
- **Supersede candidates.** None. No row is contradicted by better evidence of the same quantity.
  - S1264 (DiMeglio, liquid compensation −17 %) stands against S23.13 (Reid, partial compensation over 4 weeks) as a paired disagreement, and both stay settled.
  - The larger trials (Reid n = 133 and de Ruyter n = 641, against DiMeglio n = 15) favour "partly compensated, incompletely" over "not compensated at all".
- **Paired disagreements minted** (each parameter names its pairing):
  - S23.7 (Sun) against S23.8 (Bornet) on GI. The evidence favours Sun: it is pooled, and Bornet is industry-authored, unpooled and fibre-confounded.
  - S23.14 (Akhavan) and S23.16 (Luo) against S23.15 (Rodin) on fructose. Very low certainty; neutral.
  - S23.25 (Sasanfar) against S23.26 (Parra) on n-3. The evidence favours the Sasanfar MA's overall null.
  - S23.13 (Reid) against S1264 (DiMeglio) on liquid sugar.
  - S23.6 (Hall 2021) against S23.40 (Boden) on low-carbohydrate intake. The evidence favours Hall: an RCT against an uncontrolled study.

## Concerns

- **Gibson 2015's pooled mm values were not read.** The full text is paywalled. S23.37 is directional and S23.41 names the gap.
- **The magnitudes of Rodin 1990, Van Wymelbeke 1998 and Alfenas 2003 are not in their abstracts.** Their rows carry directions only.
- **Robinson 2026 is online ahead of print.** Its citation has no volume or issue (pmid 42746678). The same authors posted a 2026 preprint, which I did not cite.
- **Hall 2019 has two rows** (intake and mechanism) with the same citation. The checker passes them.
- **The source cell's form differs from the brief's literal string** (see the top of this report).

## Review corrections (2026-10-09, 23-review.md)

The citation review's corrections to this report's prose stand over the text above wherever they disagree; read 23-review.md items 6-11 and its residuals. In short: Boden 2005 is S23.40 and uncontrolled; S23.3's 2.58 MJ/d is the high-fat diet's energy balance, not the overconsumption fat causes; Hall 2021 against Boden is not a direct disagreement (different comparators), and Hall 2021's keto contrast is confounded by energy density and food source, so it does not show that fat or ketosis sates less per kcal; the certainty that ultra-processed food as tested raises intake is low to moderate (the MA S23.32 rates it low); Reid 2007's 'just under 1000 kJ' is a within-group change from baseline, so the 45 % compensation has no control behind it; de Ruyter's +1.02 kg and Boden's -947 kcal/d are this report's arithmetic, not the papers' figures; saturated against unsaturated fat is low, not moderate, certainty.

---

# Citation review

# Task 23 citation review (carbohydrate, fat, processing, ketosis)

Model: claude-opus-5-5. Read-only reviewer, 2026-10-09.

Method: all 39 distinct PMIDs were fetched from PubMed E-utilities, because Europe PMC REST returned 503. Title, first author, year, journal, volume and pages matched for every settled row. All 39 DOIs resolved through Crossref to the same title and first author; Hamano 2024's DOI timed out at Crossref, but it is the DOI PubMed carries. Full texts were read from PMC for Sun 2016 (PMC4728651), Hall 2019 (PMC7946062), Dicken 2025 (PMC12532614) and Sasanfar 2024 (PMC10821539). Te Morenga 2012's cohort OR was checked against the WHO eLENA commentary, because the BMJ full text returned 403.

Verified to the source: every number in S23.1, S23.5-S23.9, S23.11, S23.12, S23.14-S23.17, S23.20-S23.23 and S23.25-S23.40. From the full texts:
- Sun: the ES, Q and I2.
- Hall 2019: 17 +/- 1 kcal/min, 7.4 +/- 0.9 g/min, 1.36 vs 1.09 kcal/g, 1.957 vs 1.057, r = 0.45 (p = 0.047) and hunger -1.7 +/- 2.5.
- Dicken: -327.3 kcal/d (s.e. 110.2), 32 and 35 diaries, 90.9 % female.

The Reid "45 %" is in no row cell.

## Verdict: FAIL

## Defects

1. S23.10, value and population. The ad libitum reduction is written "-0.80 kg (95% CI 0.39 to 1.21": the estimate is signed and the CI is not. The SSB cohort OR 1.55 comes from the cohort studies in children (five cohorts), not from children and adults.
   Corrected value: `ad libitum: reduced sugars associated with a decrease in body weight of 0.80 kg (95% CI 0.39 to 1.21; P < 0.001), increased sugars with a comparable increase of 0.75 kg (0.30 to 1.19; P = 0.001); isoenergetic exchange of sugars with other carbohydrates: 0.04 kg (-0.04 to 0.13), no change; cohorts in children: highest vs lowest sugar-sweetened beverage intake OR 1.55 (1.32 to 1.82) for overweight or obesity at 1 y`
   Corrected population: `adults on ad libitum diets (trials of 2 weeks or more); children (the sugar-sweetened beverage cohort analysis)`
2. S23.2, S23.3, S23.4, S23.18 and S23.24, grade: `EXP` -> `RCT`.
   - Each is a within-subject controlled crossover. science.md defines RCT as "a randomised controlled trial, a controlled crossover or an inpatient controlled trial".
   - Register precedent: S1229 (Rolls 1999), the same covert within-subject design, is graded RCT, and PubMed types Stubbs 1995a as a Randomized Controlled Trial.
   - EXP is for non-randomised depletion or dosing experiments without that control.
3. S23.19, parameter. "(sugar calories not compensated over months)" claims a compensation reading the trial does not measure: the trial measures weight against a masked sugar-free arm.
   Corrected parameter: `weight gain over 18 months on a masked 250 mL/d sugar-sweetened beverage (104 kcal) vs a sugar-free beverage (sugar calories incompletely compensated over months)`
4. S23.13, value. "reduced carbohydrate, fat and protein intake from food" does not match the abstract, which reads "total carbohydrate intake", fat and protein "compared with sweetener supplements". "From food" is the harvester's gloss, and the comparator is dropped.
   Corrected value: `sucrose drinks (4 x 250 ml/d, 1800 kJ/d) vs sweetener drinks (67 kJ/d): by 4 weeks sucrose supplements significantly reduced total carbohydrate, fat and protein intake compared with sweetener supplements (all P < 0.001); mean daily energy intake increased by just under 1000 kJ compared with baseline (P < 0.001), with a non-significant trend to weight gain in those receiving sucrose; no effects on appetite or mood; the expectancy labelling had no effect`
5. S23.8, population. "mostly healthy adults" is not in the record.
   Corrected population: `human intervention studies (participant characteristics not given in the abstract)`
6. Report, § 1 verdict. "Boden 2005 (S23.41, ...)" has the wrong id: Boden is S23.40, and S23.41 is the open ketosis row.
   Corrected: `Boden 2005 (S23.40, an uncontrolled inpatient study)`.
7. Report, § 1 verdict. "+2.6 MJ/d (S23.3)" reads Stubbs 1995a's high-fat energy BALANCE (intake minus expenditure, 2.58 MJ/d) as the overconsumption caused by fat. The contrast with the other diets lies between the balances (-0.27 / 0.77 / 2.58 MJ/d), and any difference between them is harvester arithmetic.
   Corrected: `daily energy balance rose from -0.27 MJ/d on the low-fat to 2.58 MJ/d on the high-fat diet (S23.3)`.
8. Report, §§ 1 and 6: Hall 2021 against Boden 2005, "the RCT wins". This compares two sources with different comparators.
   - Boden compares low-carbohydrate with the patients' usual diet.
   - Hall compares keto with a minimally processed, plant-based, low-fat diet that was also far lower in energy density; the row's own range says so.
   - They do not test the same contrast, so neither overturns the other.
   - The § 6 sentence "a keto diet gives more intake than a low-fat diet ... not a stronger per-meal satiety" ignores the energy-density confound that the report applies everywhere else.

   Corrected § 6 sentence: `Fed ad libitum, a keto diet gave more intake than a lower-energy-density plant-based low-fat diet (Hall 2021, RCT); the contrast is confounded by energy density and food source, so it does not show that fat or ketosis sates less per kcal. Boden 2005 compares against the usual diet, a different contrast, and is uncontrolled.`
   Corrected pairing line: `S23.6 (Hall 2021) beside S23.40 (Boden): different comparators, not a direct disagreement`.
9. Report, § 5 certainty. "Moderate that UPF-as-tested raises intake" goes beyond the best synthesis: S23.32 rates its evidential certainty low, and its intake significance varies between models. The verdict gives no reason for exceeding the MA's own rating.
   Corrected: `Low to moderate that UPF-as-tested raises intake: the inpatient and free-living RCTs agree in direction, but the MA (S23.32) rates certainty low and its intake effect is model-dependent.`
10. Report, § 3 Reid. The table cell "so food fell by about 800 kJ" and the 45 % are harvester arithmetic. The "just under 1000 kJ" is a within-group change from baseline, not a contrast with the sweetener arm, so the 45 % has no control behind it.
    - The table cell should read `1800 kJ/d of sucrose drinks for 4 wk: intake up by just under 1000 kJ/d over baseline; no appetite effect`.
    - The § 3 note should add `(a within-group change from baseline, not against the sweetener arm)`.
11. Report: two pieces of harvester arithmetic are not flagged as such.
    - § 3, de Ruyter "+1.02 kg" (7.37 - 6.35).
    - § 6, Boden "-947 kcal/d" (3111 - 2164). The paper's own figure is a 1027 kcal/d energy DEFICIT, which is a different quantity.

    Mark both as arithmetic, or use the source's figures.

## Residuals (not defects)
- S23.1 (Blundell 1993) is graded EXP. It is a symposium paper reporting the group's preload experiments: arguably RCT for the crossovers, defensible as EXP for the paper. The controller decides.
- Population details not in the abstracts, with the full texts unreachable, so they stay unverified: S23.2 "free-living on provided diets", S23.3 "lean men" and S23.9 "adults".
- The source cell carries the spec-path prefix on all 42 rows; this is the harvester's workaround for SOURCE_RX. The controller should rule on it uniformly across the seven parts.
- Report § 4 rates saturated = unsaturated LCT at moderate certainty, but it rests on two small trials (n = 12, and one whose n is not given). Low is the more defensible rating.
- Report § 3 cites de Ruyter as favouring "partly compensated". The trial shows incomplete compensation, but it cannot separate partial compensation from none.
- Report § 6, the Gibson table cell says "paywalled abstract". The abstract is free; it is the full text that is paywalled.
- The report's "Blundell 1993 reads fat as having no satiety at all" overstates the paper, which says satiety is weak ("disproportionately weak").
- The 2.80 kcal/g snack energy density in the report's model section is confirmed in Hall 2019 Table 1: ultra-processed snacks 2.80, unprocessed snacks 1.49.
