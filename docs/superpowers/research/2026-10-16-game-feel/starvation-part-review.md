# Citation review: the starvation, dehydration and lethal-deficiency part (S11.1–S11.32)

Date: 2026-10-16. Reviewer: a read-only citation reviewer (claude-opus-5-5). Inputs: `.superpowers/sdd/game-feel-research/starvation-part.tsv`, `starvation-report.md` in this folder, `docs/reference/science.md` and the `science.tsv` header.

**Verdict: FAIL.** Seven row defects, all fixable by the cell texts below; no citation fails to resolve and no grade is wrong. The open-row changes need four corrections: S1169 should stay open rather than settle, S1166 and S1167 have stale bounds, and S2061 can be settled from a record already in the register. Once the cells below are applied, the part can be minted without a re-review, apart from a scoped look at S11.18.

## Checks run

- `python tools/science_check.py --part .superpowers/sdd/game-feel-research/starvation-part.tsv` gives **0 findings**.
- **Duplicates: none.** None of the 20 DOIs or PMIDs in the part, and not the CAIN URL either, appears in `docs/reference/science.tsv`. The one substring hit, `s0899-9007`, belongs to a different Nutrition article (`(00)00421-4`, S1542). The Friedl 1994 reading in S1910 overlaps S2061, not any S11 row (see the S2061 section below).
- **Records:** every PMID was resolved through the Europe PMC REST API, and title, first author, year, journal, volume and pages match each row. Gétaz 2012 was also resolved through Crossref (`research@example.org`). Korcok 1981 (pmid:7288960), Peel 1997 (9353494), Leiter & Marliss 1982 (7131684) and Henry 1990 (2364921) resolve too. None of the last three has an abstract, as the report says.
- **Sources read:**
  - Full text: CAIN `dead.htm` (fetched, HTTP 200); the Gétaz 2012 journal PDF from smw.ch, all 5 pages; and, from Europe PMC, Davies 2025, Speakman 2013, Casper 2020, Hemstreet 2024, Armstrong 2021 with its Fig. 1 image, Sawka 2015, Watson 2011, Flamm 2021 and Bollet 1992.
  - Abstracts only: Kalk, Faintuch, Başoğlu, Ganzini, Bolt, Ness, Doung-ngern, Ahoua, Wood, Kurnick and Malfait.

## Row by row

| row | record | numbers against the source | grade / inference |
|---|---|---|---|
| S11.1 | url 200 | All ten names, ages (23–30), dates and days without food match the page (Sands 66, Hughes 59, McCreesh 61, O'Hara 61, McDonnell 61, Hurson 46, Lynch 71, Doherty 73, McElwee 62, Devine 60). The page's day counts are inclusive: 1 Mar to 5 May is 65 elapsed days, and the page says 66. The row correctly carries the page's counts. | COH, as a series of recorded deaths, is acceptable. **Minor, defect 1:** Lynch's start date is given only as "xx May 1981 (?)". |
| S11.2 | ok | Davies: "survived for a mean of 61 days (range 46–73 days)", "at least in healthy young males", ref. 11 Korcok. Matches. | TXT is right. Davies says "IRA", but three of the ten were INLA (S11.1). This is the source's wording, so it is not a defect. |
| S11.3 | ok | 20 records, all but one male; mean 62.5 d, range 11–115; 61.4 kg American in 1920, survived 63 d. Matches. | **Defect 2.** The paper calls the American's death a fatal fast ("starved himself to death"), not a strike. "Unknown for 19 of the 20" assumes he is one of the 20, which the paper does not state. |
| S11.4 | ok | The BMI 12 quote is verbatim; the death point is BMI ≤ 13 (Eqn 13); the four readings are cited and Collins at BMI 10 is noted, "perhaps influenced by their unusual height". Matches. | TXT is right. |
| S11.5 | ok | 100 kg, 1.64 m, aged 35, BMI 37.2; 289/249/268 days; divergence around day 35; near-linear loss after day 30; females survive longer below 20 kg of fat (BMI about 25), where the difference is minimal; model 1 exact at 63 d; 592 adults aged 18–89 (the Fig. 1 caption says 18–93). Matches. | MODEL is right. |
| S11.6 | ok | "2 to 2.5 months" cites ref. 12 (Cahill 1998), and "fortieth day on" is in the same paragraph. Matches. | TXT is right. |
| S11.7 | ok | 10 % and about 18 %, citing [3, 13] (WMA 2006, Peel). Matches. | TXT is right. |
| S11.8 | ok | Table 2 matches: > 10 %, BMI < 16.5–18 (15), T < 35.5 °C, < 35/min, > 2 weeks, "no consensus, to re-evaluate regularly". The row leaves out two non-clinical indications (co-morbidities; to help resolve the conflict). This is acceptable. | TXT is right. |
| S11.9 | ok | **Defect 3.** The quoted list drops "stroke" from the third item and "very painful" from the sixth. The parameter's phrase "in the order the guidance gives them" is accurate, but the report reads this list order as an order of onset (see the report section below). | TXT is right. |
| S11.10 | ok | Both statements are verbatim, citing [13]. | TXT is right. |
| S11.11 | ok | 2 or 3 days; "a few days"; about 10 %; "catastrophic protein catabolism … other complications arise before"; refs [11] Mehanna and [13] Peel. Matches. | TXT is right. |
| S11.12 | ok | All of the abstract matches: 33 subjects, 6–24 d, refeeding after 6–27 d, one-third, 6 lean, 10 %. | COH is right. |
| S11.13 | ok | The abstract matches: about 18 %, 43 d, one-half diarrhoea, 9 d. | COH is right. |
| S11.14 | ok | The numbers match the abstract. | **Defect 4.** "Partial fasting" and "Turkey" are both unlabelled inferences: the abstract states neither the intake nor the country (Turkey comes from the affiliation, Izmir). "Total fasting duration" also misreads the abstract's "total duration of fasting". |
| S11.15 | ok | 36 conscientious objectors; 3500 kcal/day and 69 kg; 16 kg on 1500 kcal/day; 41 % and 69 % "of the control value" (verbatim, ambiguous in the source); 28 % and 21 %; the complaint inventory; universal unsteadiness; MMPI. Matches. | TXT is right. |
| S11.16 | ok | The Table 1 row for Burger 1945 matches: Hgb ~11, ≤ 35 °C, 40 bpm, 80 mmHg, oedema in a minority. **Minor, defect 5:** the citation has no article number (`e0010`). | TXT is right. |
| S11.17 | ok (open) | The open form is right: topic, grade, value and citation are empty. The three PMIDs resolve and have no abstract. | n/a |
| S11.18 | figure read | See the S11.18 section below. **Defect 6.** | TXT is right. |
| S11.19 | ok | > 2 % (about 3 % of total body water), "vast majority … exceeded 3 %", 27 °C plus 1.5 % per 1 °C (the Key Points give ~1 %, the Fig. 7 caption ~1.3 %, and the text 27.3 °C and ~1.5 %). Matches. | TXT is right. |
| S11.20 | ok | Verbatim, p. 2; no citation follows the sentence. Matches. | TXT is right. |
| S11.21 | ok | 85 % within 15 days; 102 of 307; 74 vs 64 years. Matches. | COH (a survey) is right. |
| S11.22 | ok | Median 7 days; the symptoms; 99 cases; 72 %; 70 %, 76 % and 77 %. Matches. | COH is right. |
| S11.23 | ok | Mean 10 days, range one to two weeks; 17 publications; 8 rated moderately high or high; 80+; about half with dementia or other conditions. Matches. | MA (a systematic review) is right. |
| S11.24 | ok | Verbatim. | TXT is right. |
| S11.25 | ok | Text and Table 3 give onset 1–37 days before admission (median 33), 4/33 (12.1 %), "four (from among the five ICU patients) died within 48 hours of admission", 4/241 (1.7 %) and the one-to-three-month quote (ref. 6). Matches. The paper does not say whether the 4 hospital deaths are the same 4 as the outbreak's, and the row does not claim it. | COH is right. |
| S11.26 | ok | Almost two months; 28 crew; 53.6 %; 2 died (13 %); median age 28. **Minor, defect 7a:** the abstract's 15 are "three confirmed and 12 probable", not "15 probable". | COH is right. |
| S11.27 | ok | 14.1 %; 1.0 % (7/712); 115/597; a fifth of the thiamine; mean age 28. Matches. | COH is right. |
| S11.28 | ok | Double blind with random capsule assignment; 19 men; 500 µg per day in the diet; 10 depleted, 9 controls on 5 mg; no measurable ill effect. Matches. | RCT is right. |
| S11.29 | ok | Two weeks of symptoms; then severe pulmonary hypertension, right heart failure, cardiogenic shock and cardiac arrests; complete resolution; the "first adult case" belief. Matches. | COH (a case report) is right. |
| S11.30 | ok | The German sentence is verbatim, and the translation is faithful. **Minor, defect 5:** the record is a supplement (`133 Suppl 1:1–21`). | TXT is right. |
| S11.31 | ok | The abstract gives at least 250,000 cases and 7,000 deaths a year in 15 southern states; the introduction gives "over 3 million cases and 100,000 deaths in the U.S." (the body text says "in the reporting states"). Matches. | TXT is right. |
| S11.32 | ok | The numbers match the abstract. | **Defect 7.** The parameter reads "followed a 5-month cessation" as a 5-month lag. The abstract gives the length of the interruption, not a time from loss to outbreak. |

## Defects and the corrected cells

Each defect gives the cell to replace, as `row · column`, then the full corrected text.

**1. S11.1 · range (minor).** The page does not give every start date.

> ten deaths, 5 May to 20 August 1981; the page gives each death date and days without food, and each start date except Lynch's ("xx May 1981 (?)"); it gives no fluid or salt intake, body weight or height

**2. S11.3 · value and range.** The 1920 case is a fatal fast, and his membership of the 20 is not stated.

value:
> average time to death 62.5 days (range 11 to 115 days); the one fatal fast with a known start weight and height, an American of 61.4 kg who starved himself to death in 1920, lasted 63 days

range:
> 20 records found by the authors, all but one male; start weight and height known for only one fatal fast, which the paper does not say is among the 20

**3. S11.9 · parameter, value and range.** Restore the two dropped words, and say that the list order is not an order of onset.

parameter:
> symptoms of a prolonged hunger strike, as the guidance lists them (list order, not order of onset)

value:
> "sensation of hunger at the beginning then loss of appetite"; apathy and irritability; headache, dizziness, difficulty getting up and moving, stroke; anxiety, sadness, insomnia, impaired concentration; abdominal pain, peptic ulcers, nausea, constipation (sometimes diarrhoea); very painful nephrolithiasis, renal failure; reduced blood pressure and respiratory rate; with longer fasting, sometimes irreversible: limb paralysis, blindness, coma, and death from neurological, cardiac, pulmonary or renal problems

range:
> patient-information list (Table 3); no frequencies, no day of onset and no order of onset

**4. S11.14 · parameter, value, range and population.** Label both inferences.

parameter:
> duration and neurological outcome of prolonged fasting with oral thiamine (survivors)

value:
> total duration of fasting 130 to 324 days (mean 199 days); all 41 had neurological findings consistent with Wernicke-Korsakoff syndrome despite 200–600 mg/day oral thiamine for 60–294 days; altered consciousness lasting 3 to 31 days, gaze-evoked horizontal nystagmus, truncal ataxia and amnesia in all

range:
> n = 41 examined; the abstract does not state the intake besides thiamine: partial fasting (some intake) is an inference from the 130–324 day durations, which exceed total-starvation survival (S11.1–S11.3)

population:
> 41 prisoners (mean age 28.6) who took part in a hunger strike between 2000 and 2002; Turkey is inferred from the authors' affiliation (Izmir), not stated in the abstract

**5. S11.16 and S11.30 · citation (minor).** Complete the article number and the supplement.

S11.16:
> Hemstreet DE, Weisz GM 2024, Rambam Maimonides Med J 15:e0010; doi:10.5041/rmmj.10524; pmid:38717179

S11.30:
> Flamm H 2021, Wien Klin Wochenschr 133 Suppl 1:1–21; doi:10.1007/s00508-021-01840-z; pmid:33881635

**6. S11.18 · value and range.** See the S11.18 section below.

**7. S11.32 · parameter.** The 5 months are how long the groundnut distribution was interrupted, not a lag.

> pellagra outbreak after a 5-month interruption of the main dietary niacin source (groundnut distribution)

**7a. S11.26 · value (minor).**

> the crew ate only seafood and polished rice for almost two months prior to symptoms; 15 cases (3 confirmed, 12 probable) among 28 crew (attack rate 53.6 %); two persons died while on board (case fatality 13 %)

## S11.18: the Armstrong Fig. 1 reading

The figure is open: PMC's `nutrients-13-00887-g001.jpg`, 791×463 px. I located the x-axis ticks by pixel (0 to −20 % at x = 14.5 to 726.5, about 35.6 px per 1 %) and measured the left edge of each symptom's mark against them:

| sign | measured % | row |
|---|---|---|
| thirst | 2.0 | 2 |
| vague discomfort | 2.2 | 2 |
| disturbed economy of movement | 2.4 | 2.5 |
| anorexia | 3.1 | 3 |
| flushed skin, impatience, weariness | 4.1 | 4 |
| **apathy** | **4.2** | **4.5** |
| lagging walking pace | 4.4 | 4.5 |
| oppressed by heat | 4.9 | 5 |
| headache | 5.0 | 5 |
| stumbling | 5.2 | 5 |
| **dizziness** | **5.8** | **6** |
| indistinct speech, shortness of breath, cyanosis | 6.0–6.3 (on the 6 % gridline) | 6 |
| spasticity | 9.0 | 9 |
| delirium | 11.0 | 11 |
| inability to swallow | 12.4 | 12.5 |
| painful urination | 14.7 | 14.5 |
| no urine output | 18.7 | 19 |

- The gridlines are at 2, 6, 10, 14 and 18 %, as the row says.
- The caption ("the approximate water deficit of its first report") and the text ("Tamb > 37 °C", "not subject to statistical analyses") match.
- The text calls the men "soldiers", which is consistent with the population cell.

**Judgement.** The implementer's reading is good to within ±0.3 points everywhere except apathy. Apathy sits with the 4 % cluster, and putting it at 4.5 % moves it past lagging walking pace, which inverts the figure's order. Dizziness is closer to 5.75 % than 6 %. The range cell's caveat ("read by eye", "approximate", "not subject to statistical analyses") is honest, but it does not give the reading's resolution. The fix below states the resolution and that a re-measurement was made.

value:
> about 2 % of body mass: thirst, vague discomfort; about 2.5 %: disturbed economy of movement; about 3 %: anorexia; about 4 %: flushed skin, impatience, weariness, apathy; about 4.5 %: lagging walking pace; about 5 %: oppressed by heat, headache, stumbling; about 6 %: dizziness, indistinct speech, shortness of breath, cyanosis; about 9 %: spasticity; about 11 %: delirium; about 12.5 %: inability to swallow; about 14.5 %: painful urination; about 19 %: no urine output

range:
> positions read off Figure 1 to the nearest 0.5 % (a pixel re-measurement against the axis ticks agreed within 0.3 points); the figure's marks give "the approximate water deficit of its first report" (axis 0 to −20 % body-mass change, gridlines at 2, 6, 10, 14, 18 %); the observations were "not subject to statistical analyses"; the order of first report, not a threshold for every man

## The report: its arithmetic and its unlabelled inferences

- **Dehydration (§ 2): correct.** 2000 g/day on 70 kg is 2.86 % a day. That reaches 6 % on day 2.1, 11 % on day 3.85, 15 % on day 5.25 and 19 % on day 6.65, which matches "about days 5–7". The comparison with the VSED medians (S11.22, S11.23) is labelled as agreement. The reader should keep in mind that those cohorts were old, ill and in bed.
- **Starvation (§ 1): the BMI arithmetic is correct.** BMI 22 to 13 is 1 − 13/22 = 40.9 %, which the report gives as 41 %.
  - The "Signs and their order" list numbers Table 3's list 1–7 as if it were a sequence of onset. Gétaz gives no order of onset (defect 3).
  - The phase table's day bands ("ketotic lull 3–14", "wasting 14–40") are therefore the report's construction. They should be headed **(inference: day bands are a game-pacing choice; only day 2–3 glycogen, day 40 and day 46–73 rest on rows)**.
- **Beriberi (§ 3): an unlabelled inference.**
  - "Clinical deficiency at about 4–8 weeks of near-zero intake" rests on three rows, none of which is near-zero intake to clinical onset:
    - S11.28 is 0.5 mg/d and stays subclinical, so it is a lower bound for 0.5 mg/d, not for zero.
    - S11.26 is polished rice plus seafood.
    - S11.25's quote is about stores being depleted, not about clinical onset.
  - "Floor = 0 about 5 weeks after clinical onset" adds the median onset-to-admission of all 33 admitted (29 of whom survived) to the decedents' < 48 h in intensive care. The four decedents' own onset times are not given.
  - Both lines must be marked **(inference)**. They cannot settle S1169 (see the S1169 ruling below).
- **Pellagra (§ 3): wrong arithmetic framing.**
  - 7,000/250,000 = 2.8 % is a crude case-fatality ratio of a peak year's reported cases (Bollet also gives "at least 35 non-fatal cases for each death"). It is not "3 % of cases a year" as a hazard.
  - A low case fatality does not show that pellagra kills slowly. The "years" direction rests on S11.30 alone.
  - Replace the sentence with: "Deaths were about 2.8 % of reported cases in a peak year **(arithmetic)**, a case-fatality ratio with heavy under-reporting, not a time course; the slow course rests on S11.30 ('many years')."
  - "An outbreak followed 5 months after groundnuts stopped" should read "the outbreak followed a 5-month interruption of groundnut distribution (S11.32)" (defect 7).
- **Scurvy (§ 0 table and § 3): imprecise wording.** S11.29's patient presented after two weeks of symptoms and developed shock in hospital. Write "presented after two weeks of symptoms, then developed right heart failure, cardiogenic shock and cardiac arrests in hospital, and recovered on vitamin C".

## The existing open rows

Ids below assume the part is applied next onto S2230, so S11.*n* becomes S(2230 + *n*): S11.1 → S2231, S11.2 → S2232, S11.3 → S2233, S11.11 → S2241, S11.18 → S2248, S11.20–S11.32 → S2250–S2262. Run the `science_delta.py apply` command first and use the ids it prints.

`science_delta.py` has no subcommand that rewrites an open row's `range` (bound) cell; `settle` and `status` are its only row edits. The "keep open, new bound" rows below are therefore direct cell edits by the controller, as in 3262bfb5. Each text is the complete new `range` cell.

**S0111: supersede. Right.** S11.1 and S11.2 answer "survival time under total starvation" for young men with water. I recommend adding S11.3 (Speakman's 20-record series) as a third successor, because S0111 asks about the general range, not just the Maze ten.

```
python tools/science_delta.py status S0111 superseded --successor "S2231, S2232, S2233"
```

**S1169: do not settle. Keep it open with a new bound.** S1169 asks for the time from clinical deficiency to fatal cardiac beriberi without treatment.

- S11.25's median of 33 days is onset to admission for all 33 admitted, of whom 29 survived. The four deaths occurred in intensive care with no onset times of their own.
- S11.26 gives deaths at sea with no time from onset.
- Settling the row would put a cohort median and a treated decompensation window in the place of a per-patient untreated course.

New `range` cell:

> direction only: S0244 and S0245 give the wet and fulminant presentations and a rapid deterioration; S2255 gives symptom onset 1–37 days (median 33) before admission among 33 admitted soldiers, of whom 4 died within 48 hours of admission in intensive care, with no onset-to-death time for the four; S2256 gives two deaths at sea after almost two months of polished rice and seafood, with no time from onset; the time to clinical deficiency is open S0243; the plan ships death 72 game hours after 7 days at the clinical grade as game choices (Plan 5 ruling 13)

**S0103: keep it open. Right.** New `range` cell:

> no healthy-adult time to death without water was read: S2250 gives absolute fasting as "not compatible with life for more than a few days" with no count; S2251, S2252 and S2253 give 85 % dead within 15 days, a median of 7 days and a mean of 10 days in mostly elderly or ill people voluntarily stopping eating and drinking; S2254 finds no evidence for the 3-day rule; Adolph 1947 (Physiology of Man in the Desert, the survival table by air temperature) was not read

**S1101: keep it open. Right.** New `range` cell:

> direction only: S0709 gives severe strain at about 4 %, and S2248 (Adolph's desert walkers, read off Armstrong 2021 Fig. 1) gives delirium first reported at about 11 %, inability to swallow at about 12.5 % and no urine output at about 19 %, with no deficit stated as lethal; S0103 (open) asks the time to death without water, not a deficit; the plan ships SEVERE_DEHYD_PCT 10 as a labelled game choice for Plan 5's lethality mapping (Plan 4 ruling 8, Task 8 review residual b)

**S1166: keep it open. Right, but the bound must change in the same commit as S0111's supersession.** The current bound says "the survival time is open S0111". New `range` cell:

> direction only: S0112 gives the lowest body-mass index compatible with survival and S0113 the course of semi-starvation; S2231 and S2232 give death at 46–73 days (mean 61) of total starvation with water in young men, and S2241 says only that a catastrophic protein catabolism follows exhausted fat stocks, other complications arising before, with no time; the plan ships 72 game hours from the reserve floor as a game choice (Plan 5 ruling 13)

**S1167: keep it open. Right, but the current bound is stale.** It says "no settled row gives an essential-fat floor", but S1910, minted 2026-10-13, is settled and gives the male floor. New `range` cell:

> direction only: S1910 gives the male floor of 4-6 % body fat (DXA; about 2.5 kg) in healthy men under prolonged deficit, past which further loss comes from fat-free mass; no row gives a female floor; the plan ships 0.04 for men and 0.10 for women as game choices (Plan 5 ruling 13)

**S1168: keep it open. Right.** New `range` cell:

> direction only: S0225 gives signs at about 40 days of withdrawal and S0965 that scurvy can be fatal, no time to death; S2259 is one adult case that presented after two weeks of symptoms, then developed right heart failure, cardiogenic shock and cardiac arrests in hospital and recovered on vitamin C, no untreated course; the timing of the signs is open S0210; the plan ships death 168 game hours after 30 days at the clinical grade as game choices (Plan 5 ruling 13)

**S1170: keep it open. Right.** New `range` cell:

> direction only: S0272 gives death as the fourth D of untreated pellagra, S2260 that the disease can persist for many years before death, and S2261 at least 7,000 deaths a year against at least 250,000 reported cases a year at the US epidemic's peak, a count with no per-patient course; the status fraction at onset is open S1068; the plan ships death 336 game hours after 60 days at the clinical grade as game choices (Plan 5 ruling 13)

**S0243: keep it open. Right.** New `range` cell:

> not verified: S0242 gives clinical signs below 0.5 mg/d; S2258 gives only subclinical depletion after 4 to 5 weeks at 0.5 mg/d; S2255 quotes a review that a thiamine-poor diet can deplete body stores within one to three months; S2256 gives wet beriberi after almost two months of polished rice and seafood; no zero-thiamine depletion study with a day count was read

**S2061: the report says "not found", but the record is in the register already.** S1910's citation, Friedl 1994 (pmid:8002550), states in its abstract that the Minnesota men reached "5.2% by underwater weighting" after a 25 % body-weight reduction. I resolved the abstract and that sentence is in it. S2061 can be settled from that record, keeping the review's 5–6 % as consistent:

```
python tools/science_delta.py settle S2061 --topic body-composition --grade EXP --value "5.2 % body fat by underwater weighing at the end of semistarvation, after a 25 % body-weight reduction (the 1950 Minnesota study as Friedl 1994 reports it); height-corrected final fat 0.9 +/- 0.7 kg/m2" --range "secondary reading in the Friedl 1994 abstract; the Keys 1950 monograph not read; the number of men measured is not given" --population "the men of the Minnesota Experiment at the end of 24 wk of semistarvation" --citation "Friedl KE, Moore RJ, Martinez-Lopez LE, Vogel JA, Askew EW, Marchitelli LJ, Hoyt RW, Gordon CC 1994, J Appl Physiol 77:933-940; doi:10.1152/jappl.1994.77.2.933; pmid:8002550"
```

The grade follows the S0240 precedent: a number quoted from a primary takes the primary's grade, and Minnesota was a non-randomised controlled depletion experiment. If the controller would rather not settle from a secondary quotation, keep S2061 open with this `range` cell:

> the Friedl 1994 abstract (pmid:8002550, the S1910 record) quotes 5.2 % by underwater weighing after a 25 % body-weight reduction in the 1950 Minnesota study; the Dulloo 1997 re-analysis abstract (pmid:9062520) gives no fat percentage and the Keys 1950 monograph was not read
