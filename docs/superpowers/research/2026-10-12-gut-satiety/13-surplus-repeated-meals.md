# Gut satiety harvest 13: surplus and repeated meals (Plan 11g Task 1, Step 3)

Harvester: claude-opus-5-5, 2026-10-12. No tracked file was edited except this page and its part file,
`13-rows.tsv`. The part file holds 24 rows, provisional ids `S1919`–`S1942`: 21 settled and 3 open.
`python tools/science_check.py --part` reads 0 findings on it. No subagent ran, and no package was installed.

**Scope.** This harvest covers three things:
- Karl 2021's well-fed arm (BAL) in detail, beyond what S1325 already holds;
- overfeeding studies of 1 to 14 days that rate hunger;
- whether satiety builds up across a day's meals.

The plan asks for one statement: the figure a gut-stage (G) model must hit on a surplus day, and its tolerance (§ 5).

**Conventions.**
- A value marked **derived** is my arithmetic on reported numbers. The arithmetic is shown each time.
- A value marked **inference** is my reading, not the paper's.
- A figure value says how it was read.
- "Not found" means not found in the sources reached.

**Records resolved.** Every citation was resolved through the Europe PMC REST API (`resultType=core`): title, first
author, year, journal, volume, pages, PMID and DOI matched. Johnstone 1996 has no DOI in its record, so its row cites
the PMID only.

**Rows already in the register, cited here, not refiled.**
- S1325 (Karl 2021, the −55 % headline).
- S1224 (Marmonier 2000), S1247 (Callahan), S1277 (de Castro 1987, satiety per kcal by time of day), S1273 (Scheer,
  circadian hunger).
- S1608 (Ohkawara), S1609 (Speechly), S1612 (Levitsky and Pacanowski, breakfast), S1613 (Johnstone 2002, 36-h fast).
- S0059 (Bouchard 1990) and S0605 (Bray 2012) are overfeeding rows on body composition. They report no hunger.

---

## 1. Karl 2021, the well-fed arm

Sources: Karl JP et al. 2021, Br J Nutr 126:1571-1584 (doi:10.1017/S0007114521000131, pmid 33441218).
- The full-text HTML was read from Cambridge Core.
- The Table 1 and Table 2 images (`S0007114521000131_tab1.png`, `_tab2.png`) and Figures 1 and 4 were read directly.
- Supplement 2 (`S0007114521000131sup002.pdf`) was read: Suppl. Fig. 1 and Suppl. Tables 1–3.
- So was the parent trial's protocol (NCT03524690, `Prot_SAP_000.pdf`, version 7).
- Research 03 (`../2026-10-10-live-study-replays/03-karl-2021-facts.md`) already holds the participants, the
  expenditure, the balance formula and the activity. It is not repeated here.

### 1.1 The design facts a surplus oracle needs

- **Intake** (Table 1, S1923): REST 10.6, DEF 10.5, BAL 22.7 MJ/d. Macronutrient shares are matched (about
  60/10/30 % carbohydrate/protein/fat).
  - BAL ate 2.14 times REST's absolute food (derived: 22.7 / 10.6).
  - BAL's balance is +18 (sd 20) % against measured TDEE (DLW, n 9).
- **Meals.** "Meal times were also matched between conditions, but participants could request snacks at any time."
  The Discussion credits "the increased diet volume and more frequent snacking during BAL relative to DEF and REST".
  - Meal and snack counts per arm: not found.
  - The clock time of each rating: not found. The protocol gives REST as a lab day "from breakfast through dinner
    (~0600-~1900)"; SUSOPS sleep was 01:00–05:00.
- **Sampling.** Ratings were taken on a 10-cm pen-and-paper VAS, eight times a day: before and after breakfast, the
  morning exercise, lunch and dinner. REST is one day of eight ratings; each SUSOPS arm is three days.

### 1.2 The meal-by-meal profile (Suppl. Fig. 1B; S1920)

Suppl. Fig. 1 is vector artwork. I read each series' polyline coordinates from the PDF (PyMuPDF `get_drawings`, already
installed) and mapped them onto the panel's drawn y-axis (0 at y = 302.38 pt, 10 at y = 191.34 pt). The precision is
about 0.02 cm. The SEM bars were not read.

Mean hunger (cm):

| point | REST | BAL d1 | BAL d2 | BAL d3 | DEF d1 | DEF d2 | DEF d3 |
|---|---|---|---|---|---|---|---|
| pre-breakfast | 5.18 | 5.18 | 2.91 | 2.69 | 5.85 | 5.01 | 6.18 |
| post-breakfast | 2.25 | 1.02 | 0.13 | 0.27 | 4.51 | 2.57 | 4.11 |
| pre-exercise | 2.98 | 1.04 | 0.56 | 0.72 | 4.51 | 2.42 | 4.12 |
| post-exercise | 3.42 | 1.50 | 1.36 | 1.27 | 4.17 | 3.60 | 5.03 |
| pre-lunch | 7.04 | 4.13 | 3.68 | 3.65 | 6.17 | 5.76 | 6.89 |
| post-lunch | 2.35 | 0.25 | 0.54 | 0.47 | 4.62 | 3.52 | 4.42 |
| pre-dinner | 5.26 | 3.64 | 2.40 | 1.99 | 6.57 | 6.22 | 5.89 |
| post-dinner | 3.53 | 0.48 | 1.03 | 0.12 | 4.58 | 4.57 | 4.06 |

**Derived from the table:**
- **Means over the sampled points.** REST 4.00 cm over 8 points. BAL 1.71 cm over 24, which is −57 % against REST.
  DEF 4.81 cm, which is +20 %. The paper reports −55 % and +26 % as the mean of per-person percentages, so the
  group-mean ratio sits within 2 points for BAL.
- **BAL per day:** 2.16, 1.58 and 1.40 cm, which is −46 %, −61 % and −65 % against REST.
- **Post-meal troughs** (mean of post-breakfast, post-lunch and post-dinner):
  - REST 2.71 cm;
  - BAL 0.58, 0.57 and 0.29 cm on days 1–3 (0.48 cm over all nine);
  - DEF 4.57, 3.55 and 4.20 cm.
- **Pre-meal peaks** (mean of the three pre-meal points): REST 5.83 cm; BAL 4.32, 3.00 and 2.78 cm.
- **BAL pre-breakfast** on days 2 and 3 is 2.91 and 2.69 cm against 5.18 cm on day 1, which is −44 % and −48 %. Day 1's
  pre-breakfast point equals REST's (both 5.18), because it precedes any surplus.

**What the profile shows (inference).**
- **The surplus deepens the troughs.** BAL post-meal hunger sits at 0.1–1.0 cm, 1–10 % of the scale, against REST's
  2.3–3.5 cm. In other words, a G model's trough under large meals must reach about 0.05 on a 0–1 scale; today's
  model bottoms out near 0.08 (spec § 1).
- **It lowers the peaks.** Pre-meal BAL hunger is 25–60 % below REST.
- **It carries overnight.** Days 2–3 open at about half of day 1's pre-breakfast hunger. That carry-over makes the
  suppression grow day on day, as Suppl. Table 1 shows (S1921): hunger, BAL against REST, d = 0.75, 1.06, 1.15, with
  condition × day P = 0.02.

### 1.3 Regression on energy balance (Table 2; S1919)

Hunger change against REST = −26.8 % + (−1.1) × energy balance (%).
- n 9; P = 0.004 for the slope and P = 0.02 for the intercept.
- The x-intercept is −24 % (a 24 % deficit returns hunger to REST).
- In MJ/d the slope is −0.021 per MJ/d and the x-intercept −5.4 MJ/d.

**Derived:** at BAL's mean +18 %, the line predicts −26.8 − 1.1 × 18 = −46.6 %, against the observed −55 %.

**Inference.** The intercept says that at zero balance, with the high turnover and large meals of SUSOPS, hunger would
already sit about 27 % below the sedentary day. So roughly half of BAL's −55 % comes from the large absolute intake at
high turnover, and the rest from the surplus.

### 1.4 Gastric emptying and hormones (S1922, S1924)

- **Gastric emptying (SmartPill, swallowed after breakfast, then the normal schedule).** Median GET: REST 182 min,
  DEF 222, BAL 612 min.
  - Five subjects exceeded 10 h, five of them in BAL.
  - Excluding them, BAL 266 (sd 30), REST 152 (sd 54), DEF 207 (sd 40) min.
  - The authors attribute the long BAL times to food from later meals and snacks arriving before breakfast had emptied.
- **Inference for the model.** In BAL the stomach seldom empties between meals. Part of the BAL suppression is
  therefore carried by fullness (F), not only by the gut signal. A G model that empties the stomach by meal size will
  also see a fuller stomach in BAL, so F and G share the arm.
- **Hormones.**
  - After exercise (fed): ghrelin was higher, and PYY, GLP-1, PP and insulin lower, in DEF than in BAL (d 0.5–1.9).
  - Fasting: PYY, GLP-1, PP and insulin did not differ between arms; leptin and acylated ghrelin fell in DEF.
  - **Inference:** the gut-hormone difference is postprandial and gone by the morning fast, consistent with a gut signal
    that clears within hours. The overnight carry-over in hunger (§ 1.2) is not reflected in fasting PYY or GLP-1.

---

## 2. Overfeeding for 1 to 14 days

| study | surplus, days | hunger reading | row |
|---|---|---|---|
| Hägele 2019 | +25 %, 1 day per condition, at PAL 1.3/1.6/1.8 | 15-h hunger AUC −26 %, −25 %, −26 % against zero balance (derived) | S1930 |
| Thomas 2013 | +40 %, 1 day | next-morning fasting hunger 67.8 → 51.5 mm, −24 % (derived) | S1926 |
| Halliday 2020 | +40 %, 3 days | daily pre-meal hunger −23 % (OP) and −21 % (OR) (derived from Fig. 2B) | S1928 |
| Cornier 2004 | +50 %, 3 days | pre-meal hunger, thin 68 → 41 mm (−40 %, derived); reduced-obese 63 → 65 (n.s.) | S1925 |
| Cornier 2007 | +30 %, 2 days | lower hunger, higher satiety (direction only) | S1931 |
| Johnstone 1996 | +0.6 × RMR, 1 day, by macronutrient | protein more satiating on the day; no next-day intake effect | S1932 |
| Levitsky 2005 | +35 %, 13 days | intake afterwards back to baseline "immediately" (no hunger ratings) | S1933 |
| Wadden 2012 / Cahill 2011 | +70 %, 7 days | fasting acylated ghrelin +62.14 ng/L; fasting PYY up (no ratings) | S1934, S1935 |

### 2.1 Hägele 2019: the cleanest single-day surplus (S1930)

The design is 16 adults in a metabolic chamber.
- Each day is CR (75 %), zero EB or OF (125 %) of the requirement, measured in the ad libitum condition.
- Turnover is set at PAL 1.3, 1.6 or 1.8 by treadmill walking.
- Meals are at 07:00, 13:00 and 19:00 (50/35/15 % carbohydrate/fat/protein). VAS AUC runs 07:00–22:00.

Table 2 hunger (mm × 15 h), low / medium / high turnover:

| | low | medium | high |
|---|---|---|---|
| CR | 660 | 578 | 542 |
| zero EB | 559 | 466 | 409 |
| OF | 412 | 348 | 303 |

**Derived:**
- OF against EB: −26.3 %, −25.3 % and −25.9 %. That is about −1.0 % of hunger per % of surplus, the same as Karl's
  slope of −1.1 (S1919).
- High against low turnover at zero EB: 409 / 559, which is −26.8 %. The more food eaten at balance under more
  activity, the less hunger, and the size matches Karl's zero-balance intercept of −26.8 %.
- Fullness, OF against EB: +32.5 %, +27.8 % and +23.8 %.

The table tests turnover within each balance condition, not OF against EB, so the surplus contrasts are derived, not
tested. The paper was read through two independent passes of the publisher page; direct download is behind a bot
wall. The OF low-turnover SD (347) is as printed.

### 2.2 Thomas 2013: carry-over to the next morning, and the meal's increment (S1926, S1927)

After one day at +40 %, fasting hunger the next morning (at least 10 h fasted) fell from 67.8 to 51.5 mm. A test
breakfast sized at 25 % of the previous day's diet (so 40 % larger after OF) followed. Its 180-min hunger AUC was
8380 (EU) against 5882 (OF), −30 % (derived). However, "The incremental AUC ... did not differ by group or feeding
phase, suggesting that the differences in total AUC were driven by the differences in fasting ratings."

**Inference.** A 40 % bigger meal on top of a sated state did not produce a measurably bigger hunger drop. That points
to a saturating read: added gut load buys less on a full gut. Marmonier 2002 (S1939) agrees: a snack eaten in a
non-hungry state "has poor satiating efficiency irrespective of its composition" (a high-carbohydrate snack did not
delay dinner).

### 2.3 Halliday 2020: three days, then release (S1928, S1929)

- **During OF.** "OF decreased pre-meal hunger and PFC and increased post-meal satiety similarly in both groups during
  days 5-7". Fig. 2B pre-meal hunger, EU against OF:
  - OP 73.3 against 56.3 mm;
  - OR 79.8 against 62.8 mm.
  - I measured these as bar-top pixels against the figure's 40–100 mm axis, to about 0.5 mm.
- **Across the 3 overfed days,** Fig. 2A shows no progressive fall (read by eye: OR OF about 60, 61, 69 mm; OP OF about
  59, 52, 60 mm).
- **After OF.** "Following OF (ad libitum phase), VAS ratings of hunger, PFC, and satiety were similar to ratings given
  during the EU condition (P-values > 0.05)". Intake fell by 181.8 kcal (OR, P = 0.03) and 114.3 kcal (OP, n.s.), most
  of it on day 8.

**Inference.** The suppression lasts while the surplus is eaten and clears within about a day once it stops. A
multi-day store does not hold it.

### 2.4 Longer and free-living

- **Levitsky 2005.** After 13 days at +35 %, intake returned "immediately" to baseline.
- **De Castro 1998 (S1936).** In free-living diaries, one day's intake relates weakly to the next day's (r = −0.07) and
  more to the second day's (r = −0.18).
- **Johnstone 1996 and 1998.** A one-day overfeed did not change the next day's ad libitum intake. The 1998 study
  (monoglyceride against triglyceride) has no maintenance-against-overfeed hunger contrast in its abstract, so no row
  was filed.
- **Fasting hormones after 7 days at +70 %.** Acylated ghrelin rose (Wadden 2012), which is paradoxical, and PYY rose
  (Cahill 2011). Neither study rated hunger.
- **Beyond 14 days, out of scope, no rows.** Roberts 1990 (21 days, +1011 kcal/d: later voluntary intake −1991 kJ/d),
  Siervo 2008 and Jebb 2006 (3-week blocks at +20/40/60 %: intake after overfeeding "stimulated rather than suppressed"
  on average).

---

## 3. Satiety across a day's meals

**At balance there is no build-up within the day (inference from four sources).**
- **Karl's REST day (S1920).**
  - Pre-meal hunger: 5.18 (breakfast), 7.04 (lunch), 5.26 cm (dinner).
  - Post-meal: 2.25, 2.35, 3.53 cm. Post-dinner is the highest.
- **De Castro 1987 (S1277).** "humans obtain less satiety from a given amount of food later in the day than earlier".
- **Scheer (S1273).** The circadian rhythm raises evening hunger.
- **Ohkawara (S1608).** More frequent isoenergetic meals raise 24-h hunger AUC.

**The next meal largely resets the previous one (Thomas 2015, S1937).**
- A 25 %-of-day breakfast lowered pre-lunch hunger AUC by 51.1 cm × 240 min:
  - −50 % in habitual eaters (90.1 against 179, derived);
  - −37 % in skippers (86.2 against 137, derived).
- After a fixed lunch at 240 min (35 % of the day), post-lunch hunger AUC (270–540 min) was only 10.7 lower: 76.5
  against 87.3, −12 % (derived), with P = 0.116.
- Post-lunch satiety AUC stayed higher, by 31.5 (P = 0.005).
- Astbury 2011 (S1938): a 10 %-of-day breakfast lowered lunch intake by about 17 %.
- Levitsky and Pacanowski (S1612): a 335–360 kcal breakfast did not change lunch intake.

**Under a surplus, the carry-over grows and reaches the next morning.**
- Karl BAL: pre-breakfast −44 % and −48 % on days 2–3.
- Thomas 2013: −24 % fasting after one +40 % day.
- Cornier 2004 and Halliday 2020: pre-meal hunger −21 % to −40 %.

**Inference.** A G model with an hours-scale clearance does this by construction. Within a balanced day, each meal's
G mostly clears before the next. Under large or frequent meals, G never empties and its residual crosses the night.

---

## 4. Statements the plan asks of this harvest

1. **Karl's well-fed arm.**
   - The daily hunger suppression is −55 % against REST (95 % CI −73, −38; S1325).
   - It is the mean of eight VAS points a day (before and after each meal and the morning exercise) over three days
     of 22.7 MJ/d intake (2.14 × REST), at +18 % balance under PAEE 9–10 MJ/d.
   - The group-mean reconstruction from Suppl. Fig. 1B gives −57 %, with −46 %, −61 % and −65 % by day (derived).
2. **Overfeeding of 1–14 days.**
   - It lowers hunger by about 1 % per 1 % of surplus over a day: Hägele −26 % at +25 % (derived), and Karl's slope
     −1.1 %/%.
   - Pre-meal and fasting readings fall less per % of surplus: −21 % to −24 % at +40 % (Thomas 2013, Halliday 2020).
     The exception is Cornier 2004's thin group, −40 % at +50 %.
   - Reduced-obese adults showed no fall (Cornier 2004).
   - The effect clears within about a day of the surplus ending (Halliday 2020; Levitsky 2005).
3. **Satiety across a day's meals.**
   - At balance it does not build up meal on meal (Karl REST; Thomas 2015 −12 % n.s. past the next meal).
   - Under a surplus it carries over the night and deepens across days (Karl BAL d 0.75 → 1.15; pre-breakfast −44 to
     −48 %).

## 5. The figure a G model must hit

- **Target.** −55 % mean hunger, BAL against REST (S1325). The tolerance (inference) is ±9 points, which is one
  standard error from the reported CI (derived: (73 − 38) / (2 × 1.96) = 8.9). The acceptance band is −46 % to −64 %.
  - Today's model reads −45 %, just outside the band. That matches the spec's diagnosis.
  - The full 95 % CI (−73 to −38) is too wide to discriminate.
- **Sampling.** The oracle should average the model at the study's eight sampling points: before and after each
  meal, and before and after the morning exercise. The paper does not state how long after a meal the post-meal rating
  was taken. It should not average every awake minute
  (research 03, difference 1).
  - **REST** in the oracle should be one sedentary day at 10.6 MJ/d.
  - **BAL** should be 22.7 MJ/d at about 20 MJ/d TDEE, with three meal times matched to REST. The snack schedule is
    not given and is a design choice.
- **Shape checks** (secondary, inference, open row S1940):
  - BAL post-meal troughs about 0.05 on a 0–1 scale (0.48 cm mean; per day 0.58, 0.57, 0.29), against REST 0.27;
  - BAL pre-breakfast on days 2–3 about 0.28, against 0.52 on day 1;
  - per-day suppression growing from about −46 % to −65 %.
- **Tolerance for the shape checks.** I recommend ±0.05 on the unit scale. That is a design choice; no SEM was read.

## 6. What could not be found

- Karl 2021: meal and snack counts per arm, the clock times of the eight ratings, and per-meal energy. The SEMs in
  Suppl. Fig. 1 were not read. Suppl. Table 3 (hormone concentrations) was not read.
- **Any study rating hunger hourly through the 12–36 h after a surplus ends.** The decay is bounded only by Thomas 2013
  (still −24 % after at least 10 h) and Halliday 2020 (back to EU on the ad libitum days). Open row S1941.
- **Any study giving graded first-meal sizes with hunger sampled after the second and third meals.** It would give the
  meal-on-meal carry-over fraction; only Thomas 2015's one pair was found. Open row S1942.
- Full texts not reached:
  - Cornier 2004, Cornier 2007, Johnstone 1996, Levitsky 2005, Cahill 2011 and Astbury 2011 (read from the abstract only;
    no full text was sought);
  - Marmonier 2002 (the AJCN page returned 403, so the snack's energy is missing).
  These rows rest on abstracts and say so.
- Hägele 2019 OF-against-EB tests: not reported. The contrasts are derived.
- Reinbach 2009 (Clin Nutr 28:260-265; 3 weeks each at +25 % and −25 % energy balance) was found. Its abstract reports
  the bioactive treatments' effects within each balance condition, not hunger in positive against negative balance,
  so no row.

**Searches run.**
- Europe PMC: overfeeding/overfed/surplus × hunger/VAS; breakfast omission/skipping × hunger/day; titles of the named
  studies.
- WebSearch for Cornier 2004.
- Publisher pages: Cambridge Core (Karl), academic.oup.com (Hägele), PMC (Thomas 2013, Halliday 2020, Thomas 2015,
  Wadden 2012).

## 7. Recommendation for the model (inference)

1. **Feed G by absolute emptied kcal, not by balance.** Two independent studies give about −27 % hunger at zero balance
   when more food is eaten under higher turnover:
   - Karl's Table 2 intercept;
   - Hägele, high against low PAL at EB.

   About half of Karl's −55 % is that volume effect. A G fed by emptied kcal produces it directly. The energy-balance
   term then needs to carry only the residual surplus effect. This supports the spec's aim of letting
   `BALANCE_SPAN_KCAL` return toward its deficit-only fit.
2. **Keep the read saturating.** Thomas 2013's unchanged increment for a 40 % larger meal on a sated gut, and Marmonier
   2002's poor satiating efficiency of a snack eaten sated, both fit the near-logarithmic `gRead`.
3. **G's clearance must leave a residual across the night under large meals, but not across a day.**
   - Karl BAL's pre-breakfast is −44 %; Thomas 2013's next-morning fast is −24 %.
   - Halliday 2020 shows release within about a day.
   - Halliday also shows no progressive deepening over 3 days at +40 %, while Karl does at +18 % with doubled food.
     Karl's deepening fits G plus a fuller stomach (GET 612 min), not a slow third store.

   A single G whose half-life lets a large evening load survive about 6–10 h in part is the first thing to try. A
   second stage (A) is justified only if the overnight carry-over cannot be met without breaking the 0–6 h time
   courses (spec § 4, stage rule).
4. **Credit F in the BAL arm.** Karl's BAL stomach rarely empties between meals. The fit should let F carry part of the
   trough depth rather than forcing it all onto G.

## 8. Row map

| id | study | what |
|---|---|---|
| S1919 | Karl 2021 | Table 2 regression on balance |
| S1920 | Karl 2021 | Suppl. Fig. 1B profile (vector read) |
| S1921 | Karl 2021 | Suppl. Table 1 day-by-day effect sizes |
| S1922 | Karl 2021 | gastric emptying time (topic `digestion`) |
| S1923 | Karl 2021 | Table 1 intake and expenditure |
| S1924 | Karl 2021 | hormones, BAL against DEF |
| S1925 | Cornier 2004 | 3 d +50 %, thin against reduced-obese |
| S1926 | Thomas 2013 | fasting hunger after 1 d +40 % |
| S1927 | Thomas 2013 | test-breakfast AUC; increment null |
| S1928 | Halliday 2020 | 3 d +40 % VAS, then ad libitum |
| S1929 | Halliday 2020 | ad libitum intake, PYY, ghrelin |
| S1930 | Hägele 2019 | 15-h AUC by balance and turnover |
| S1931 | Cornier 2007 | 2 d +30 % (direction) |
| S1932 | Johnstone 1996 | macronutrient overfeed day |
| S1933 | Levitsky 2005 | 13 d +35 %, then intake |
| S1934 | Wadden 2012 | fasting ghrelin, 7 d +70 % |
| S1935 | Cahill 2011 | fasting PYY, 7 d +70 % |
| S1936 | de Castro 1998 | day-lagged intake autocorrelation |
| S1937 | Thomas 2015 | breakfast, pre- and post-lunch hunger |
| S1938 | Astbury 2011 | breakfast, preload appetite, lunch intake |
| S1939 | Marmonier 2002 | snack in a sated state |
| S1940 | open | the surplus-day target and its tolerance |
| S1941 | open | the clearance time of surplus suppression |
| S1942 | open | meal-on-meal carry-over fraction |

No new topic slug is requested: the rows use `satiety` and `digestion`.
