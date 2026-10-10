# Live study replays — 03: Karl 2021 (S1325) and Johnstone 2002 (S1613) from the primary sources

Research report, 2026-10-10, read-only (no boot, no commit). Author model: claude-opus-5-5.
Question: what a refit of the Karl 2021 oracle (`testing/tests/kernel/test_satiety_activity.py`, `karl_arm`/`karl`)
needs from the paper itself — the participants, the expenditure and how it was measured, the intake, the balance
formula, the activity — and whether the oracle's DEF is the study's quantity; and whether Johnstone 2002 reports body
mass and baseline intake.

Everything quoted below is verbatim. A value marked **inference** or **arithmetic** is mine, not the paper's.
"Not found" means not found in the sources reached, which are listed at the end.

## Sources reached

- **Karl 2021, full text** (open access, Cambridge Core): Karl JP, Hatch-McChesney A, Allen JT et al. "Effects of
  energy balance on appetite and physiological mediators of appetite during strenuous physical activity: secondary
  analysis of a randomised crossover trial", Br J Nutr 126:1571-1584, doi:10.1017/S0007114521000131. HTML at
  https://www.cambridge.org/core/journals/british-journal-of-nutrition/article/effects-of-energy-balance-on-appetite-and-physiological-mediators-of-appetite-during-strenuous-physical-activity-secondary-analysis-of-a-randomised-crossover-trial/7FAFA5390DFBE2FF27B4C87DCB4CCE68
  — Table 1 is an image (`S0007114521000131_tab1.png`), read directly. Supplement 2 (`...sup002.pdf`: Suppl. Fig. 1,
  Suppl. Tables 1-3) read. Supplement 1 (`...sup001.docx`) as served is a different paper's table (Multiethnic Cohort
  diet-quality scores) — a publisher mislink, not Karl's.
- **The parent trial's protocol** (NCT03524690, "Prot_SAP_000.pdf", protocol version 7, 18 July 2019):
  https://cdn.clinicaltrials.gov/large-docs/90/NCT03524690/Prot_SAP_000.pdf. The registry record has no results.
- **Hennigar 2021** (the parent report Karl cites as "Reference 34" for "Full details of the study design"): Am J Clin
  Nutr 113:359-369, doi:10.1093/ajcn/nqaa289, pmid 33184627 — **abstract only** (Europe PMC); the full text was 403
  at ajcn.nutrition.org, academic.oup.com and sciencedirect.com.
- **Johnstone 2002**: Int J Obes 26:1623-1628, doi:10.1038/sj.ijo.0802151 — **abstract only** (nature.com preview,
  Europe PMC); Unpaywall reports no OA copy; Southampton and Newcastle eprints hold no full text.

## 1. Participants

Karl 2021, Results, first paragraph:

> "Of the thirteen male volunteers enrolled, two volunteers withdrew for personal reasons and one withdrew due to
> injury. The ten volunteers (22 (sd 5) years, BMI: 27·0 (sd 3·5) kg/m2) who completed the study were included in
> this analysis."

Karl 2021, Methods, Participants: "Generally healthy, recreationally active (2–4 d/week aerobic and/or resistance
exercise), active duty male soldier volunteers, aged 18–39 years ..."

- **Body mass: not reported in Karl 2021.** Methods (body weight) says only "Height was measured in duplicate prior
  to the first SUSOPS period using a stadiometer. Nude, fasted body weights were measured each morning ..." — neither
  value is tabulated in the paper or its supplement.
- **Body mass from the parent report (same n = 10, same trial NCT03524690)**, Hennigar 2021 abstract, Methods:
  > "healthy male subjects (n = 10, mean ± SD age: 22.4 ± 5.4 y, weight: 87.3 ± 10.9 kg) with sufficient iron
  > status (serum ferritin 77.0 ± 36.7 ng/mL)."
- **Height: not found** (measured, per the quote above, but not reported in any source reached).
- **Body fat: not found.** RMR and VO2peak were measured (protocol, lines 703-708 and 712-717) but no values were
  found in the sources reached.
- Body-weight change: "mean energy balance was positive during BAL (Δbody weight = 0·6 kg (95 % CI 0·2, 1·2)).
  However, as planned, energy intake during DEF was 46 % of that measured during BAL, resulting in energy deficit and
  body weight loss (–1·2 kg (95 % CI −1·7, −0·7))." (Results, first paragraph.)

## 2. Expenditure: TDEE and PAEE

**Table 1** ("Energy expenditure, energy balance and dietary intake over the 72-h sustained operations (SUSOPS)
period", mean (sd)), read from the image:

| | REST | DEF | BAL |
|---|---|---|---|
| Energy balance (MJ/d)† | – | −8·6 (3·9) | 2·9* (3·6) |
| Energy balance (%)† | – | −43 (9) | 18* (20) |
| TDEE (MJ/d)† | – | 19·1 (4·1) | 20·0 (3·9) |
| PAEE (MJ/d)† | – | 9·2 (3·4) | 10·0 (3·1) |
| Dietary intake‡ Energy (MJ/d) | 10·6 (1·4) | 10·5 (0·7) | 22·7§ (1·6) |
| Carbohydrate (g/d) | 387 (49) | 382 (26) | 833§ (51) |
| Protein (g/d) | 68 (8) | 71 (3) | 139§ (12) |
| Fat (g/d) | 87 (11) | 84 (7) | 183§ (15) |
| Carbohydrate / protein / fat (% energy) | 59 / 11 / 31 | 59 / 11 / 30 | 60 / 10 / 30 |

Footnotes, verbatim: "TDEE, total daily energy expenditure measured by doubly labelled water; PAEE, physical activity
energy expenditure." "* Different from DEF, P < 0·001." "† Energy expenditure measured during SUSOPS only.
Between-condition comparisons analysed by paired-samples t test (n 9, one volunteer served as study control)." "‡
Analysed by general linear model with correlated errors (n 10)." "§ Different from REST and DEF, P < 0·001."

So the expenditure and balance rows are **n = 9**, the intake rows n = 10. The abstract's "about 9·6 MJ/d (2300
kcal/d)" is not a Table 1 cell; it sits between the two arms' PAEE (9·2 and 10·0) (arithmetic: their mean is 9·6).

**How TDEE was measured** — doubly labelled water, over each 72-h SUSOPS period:

- Karl 2021, Methods, Study design: "During SUSOPS, TDEE was measured using the doubly labelled water method as
  previously described (Reference 34)."
- Protocol, "Determination of Total Daily Energy Expenditure", lines 759-782: "Doubly labeled water (DLW) will be used
  to determine actual TDEE during SUSOPS 1 and SUSOPS 2 and verify the accuracy of estimated TDEE. ... Morning urine
  samples will be collected daily during each SUSOPS period to determine elimination rates over time." Analysis at
  Pennington (line 777).
- REST expenditure was not measured: REST intake was predicted, not a measured TDEE (Karl 2021, Methods): "This energy
  intake was calculated as the product of measured RMR and an activity factor of 1·3 to account for energy expended
  during activities of daily living."
- TDEE came in below plan (Results): "PAEE and TDEE measured during SUSOPS did not differ between DEF and BAL, but were
  less than planned due to some participants not being able to complete the prescribed exercise on all SUSOPS days
  (Table 1)." The target was "20·9–25·1 MJ/d (5000–6000 kcal/d)" (Methods).

**How PAEE was defined: not stated in Karl 2021** (the term appears only in the Introduction and in Table 1's
footnote "PAEE, physical activity energy expenditure"), **nor in the protocol** (no "PAEE" or "physical activity
energy" in its text). Hennigar 2021's methods would be the next place, and its full text was not reachable. So
whether 9·6 MJ covers all activity above rest or only the work bouts **cannot be quoted**.

**Inference (mine, from group means, not a reported formula):** TDEE − PAEE is 19·1 − 9·2 = 9·9 MJ/d (DEF) and
20·0 − 10·0 = 10·0 MJ/d (BAL). If REST intake (10·6 MJ/d = RMR × 1·3) is taken as the group's RMR × 1·3, the group RMR
is about 8·15 MJ/d; then PAEE ≈ 0·9 × TDEE − RMR (the usual "TDEE minus RMR minus a 10 % TEF" definition) gives 9·0
and 9·8 MJ/d, close to the table's 9·2 and 10·0, whereas TDEE − RMR would give about 10·9 and 11·8. That pattern
points to PAEE as **all expenditure above resting and food thermogenesis — the work bouts plus daily-living
activity**, not the bouts alone. It is an arithmetic consistency only; a refit that rests on it should say so.

## 3. Intake and the balance formula

**Intake per arm** (Table 1, above): REST 10·6 (1·4) MJ/d, DEF 10·5 (0·7) MJ/d, BAL 22·7 (1·6) MJ/d. DEF's intake
was therefore about the same as the sedentary REST day's. The planned amounts (Methods, Study design):

> "During one period, participants were provided enough food to maintain energy balance, defined as ±10 % of
> predicted TDEE during SUSOPS (BAL). During the other period, participants were kept in negative energy balance by
> providing only the amount of food estimated to meet 45 % of predicted TDEE during SUSOPS (DEF). ... Participants
> could eat no more or less than the amount of food provided, and water was allowed ad libitum."

and "Meal times were also matched between conditions, but participants could request snacks at any time." Diets
were mainly MRE rations.

**The balance formula: not written out in the paper.** Statistical analysis says only "Energy expenditure and energy
balance data were compared between conditions using paired t tests." Arithmetic on Table 1's means:
(10·5 − 19·1)/19·1 = −45·0 % against the reported −43 %, (22·7 − 20·0)/20·0 = +13·5 % against +18 %; and the MJ/d
row matches intake − TDEE (10·5 − 19·1 = −8·6 exactly; BAL 2·7 against 2·9, intake n 10 against expenditure n 9).
**Inference:** energy balance (%) = (intake − TDEE)/TDEE × 100, i.e. intake/TDEE − 1, against the DLW-measured
TDEE, computed per participant and then averaged (which is why the mean of the percentages differs from the
percentage of the means); the paper does not say so in words.

**The outcome the study reports** (Results, Appetite):

> "When averaged across the three SUSOPS days, mean hunger, desire to eat and prospective consumption ratings were all
> higher during DEF relative to REST (mean percentage difference (95 % CI); hunger: 26 % (95 % CI –3, 54); ...) and
> lower during BAL relative to REST (hunger: –55 % (95 % CI –73, –38); ...)"

Note the DEF hunger CI includes zero (−3 to 54). Table 2's footnote: "ΔDependent variables are percentage difference
of mean ratings throughout energy deficit (DEF) and energy balance (BAL) conditions relative to mean ratings during
sedentary condition (REST)." The ratings sampled (Methods, Appetite and food preferences):

> "During SUSOPS, self-reported appetite was measured daily before and after meals, and before and after the morning
> exercise session. During REST, measurements were collected before and after meals, and at the same times the
> morning exercise session was scheduled to begin and end during SUSOPS. Appetite measures relied on 10 cm pen and
> paper visual analogue scales ..."

Supplemental Figure 1 shows the eight timepoints per day: pre/post breakfast, pre/post exercise, pre/post lunch,
pre/post dinner. REST was one day: "volunteers spent 1 d (06.00–18.00 hours) in the laboratory for baseline appetite
testing (REST)". SUSOPS sleep: "sleep was restricted to 4 h/night (01.00–05.00 hours)".

**The oracle against the study** (`karl_arm`/`karl`, `test_satiety_activity.py` lines 266-301). The oracle's DEF is
`100 * (dfc / rest - 1)`, where each arm is the mean simulated hunger over every awake minute of 3 × 1440 min
(sleep 02:00-06:00 excluded). REST is 3 days at 2700 kcal intake with no work. The work arms add
`KARL_PAEE = 9.6e3 * KCAL_PER_KJ` = 2294 kcal/d to `ee = KARL_REST / 1440` and feed `1.18 * work` (BAL) and
`0.57 * work` (DEF), with `work = KARL_REST + KARL_PAEE` = 4994 kcal/d.

**The oracle's quantity has the same form as the study's — a percentage difference of condition-mean hunger against
REST-mean hunger — but it is not the same quantity.** The differences:

1. **Sampling.** The study averages 8 VAS readings a day, each taken immediately before or after a meal or the
   morning exercise session. The oracle averages every awake minute. The study's mean is weighted towards the
   pre-meal peaks and post-meal troughs (Suppl. Fig. 1), with nothing sampled in the afternoon or evening work.
2. **REST.** The study's REST is one sedentary day (06:00-18:00 ratings) three days before the first SUSOPS, at
   10·6 MJ/d. The oracle's REST is three simulated days at 2700 kcal = 11·30 MJ/d (arithmetic), awake 06:00-02:00.
3. **Expenditure.** The oracle's work-day expenditure is 4994 kcal = 20·90 MJ/d (arithmetic), against the measured
   TDEE of 19·1 (DEF) and 20·0 (BAL). It adds all 9·6 MJ on top of a REST of RMR × 1·3-like size; if PAEE already
   includes daily-living activity (the inference in § 2), the oracle double-counts that part.
4. **Intake.** The oracle's BAL intake is 1·18 × 20·90 = 24·66 MJ/d and its DEF intake 0·57 × 20·90 = 11·91 MJ/d
   (arithmetic), against the measured 22·7 and 10·5. The oracle applies the reported mean percentages to its own
   expenditure, so its absolute intakes run 1·4 to 2·0 MJ/d high. The study's DEF intake (10·5) is about the REST
   intake (10·6); the oracle's DEF intake (11·91) is above its REST intake (11·30).
5. **Meals.** The oracle feeds three equal meals at 07:00, 12:00 and 18:00. The study matched meal times across arms
   but let participants request snacks; the Discussion notes "the increased diet volume and more frequent snacking
   during BAL relative to DEF and REST".
6. **Work schedule.** The oracle uses 8 h a day at a flat rate (08-12, 13-17). The study's sessions are given in § 4
   (about 4·7 h of timed sessions plus a task battery), with the heaviest bout in the evening.

## 4. The activity: type and intensity

Karl 2021, Methods, Study design:

> "Daily physical activity during SUSOPS was divided into separate sessions that included walking with a weighted
> vest and backpack (mean weight: 33·5 (sd 0·2) kg) in the morning (64 (sd 6) min; 8·3 (sd 0·6) metabolic
> equivalents) and evening (122 (sd 7) min; 8·4 (sd 0·5) metabolic equivalents), a battery of military-relevant tasks
> in the late morning, and unweighted walking/jogging in the afternoon (94 (sd 46) min; 5·4 (sd 1·5) metabolic
> equivalents). The exact duration of activity was individualised to match the 20·9–25·1 MJ/d TDEE target."

The paper calls it "prolonged low-to-moderate intensity physical activity" (Methods, and the Discussion's first
sentence). The protocol, lines 712-717: "volunteers will be prescribed low-to-moderate intensity (30-65% of
pre-determined peak oxygen uptake, VO2peak and corresponding heart rate) endurance-type exercise". Its worked example
(lines 719-725) puts load carriage at "~50% of VO2peak is 6.7 METS" for an 85 kg man carrying 32 kg, and the task
battery at "approximately 100 kcal/d".

Timed sessions: 64 + 122 + 94 = 280 min ≈ 4·7 h a day (arithmetic) plus the task battery, whose duration is not given.
The measured % VO2peak during the sessions was **not found** — only the prescribed 30-65 % and the METs above.

## 5. Johnstone 2002 (S1613)

Only the abstract was reachable. Abstract, Aim: "a group of 24 healthy, lean men and women." Method:

> "During the 'fast' treatment, subjects were fed a maintenance diet on the day prior to the fast (day −1) to prevent
> overeating. They then consumed non-energy drinks only, from 20:00 h on day −1 to 08:00 h on day 2 (ad libitum
> feeding day), thus fasting for 36 h. On the 'maintenance' protocol, subjects received a maintenance diet throughout
> day 1. ... Body weight, blood glucose and respiratory quotient were used as compliance checks."

Results: "On day 2, average energy intake was 10.2 vs 12.2 MJ/day (s.e.d. 1.0) on the post-maintenance and post-fast
periods, respectively (P=0.049)." Conclusion: "a 36 h fast, which generated a negative energy balance of ∼12 MJ".

- **Body mass: not found** (the abstract says only "lean"; body weight was measured as a compliance check, but no
  value is given).
- **Baseline / maintenance intake: not found as a number.** The maintenance diet's energy is not given. The only
  intake figures are the day-2 ad libitum intakes (10.2 MJ/d after maintenance, 12.2 MJ/d after the fast) and the
  "∼12 MJ" deficit of the fast. Reading the ∼12 MJ as one day's maintenance intake would be an inference the abstract
  does not state.
- The full text (Int J Obes 26:1623-1628) is paywalled at Springer Nature, and no repository copy was found.
