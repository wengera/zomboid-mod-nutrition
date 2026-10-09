# Satiety research 2, protein harvest (2026-10-09)

The harvest report of Task 22 of Satiety research 2 (2026-10-09), followed by its citation review. The review's corrections stand over the report wherever they disagree; the rows in docs/reference/science.tsv carry the corrected cells.

# Task 22 report: protein and satiety (Satiety research 2, 2026-10-09)

Model: claude-opus-5-5. Part file: `22-science-part.tsv`, 36 rows (S22.1–S22.36): 34 settled, 2 open, 0 unverified. `science_delta.py apply --dry-run` passes, and a full apply to a scratch copy of the register (S1337–S1372) reads 0 findings under `science_check.py`, as does `--part`.

Every settled row was resolved against its PubMed record: title, first author, year, journal, volume, pages and DOI. Europe PMC's REST search returned HTTP 503 under the parallel load, so the records came from NCBI E-utilities (esearch, esummary, efetch), which is the same MEDLINE record. Full texts came from Europe PMC (`fullTextXML`) where they were open access: Gosby 2011, Hansen 2021 and the Henschel 2023 comment. Every number is the source's own. Where a row says "I2 and certainty not read (abstract only)", the paper is not open access.

Already in the register and not re-minted: S1222 (Kohanmoo 2020, the VAS readings), S1223 (Dhillon 2016), S1224 (Marmonier 2000), S1225 (Raben 2003, the null) and S1249 (de Castro 1988).

## 1. Acute protein preloads against carbohydrate or fat, and dose

| Id | Source | Key value | Grade | Quality markers |
|---|---|---|---|---|
| S1222 (existing) | Kohanmoo 2020 | hunger −7 mm, fullness +10 mm, satiety +4 mm VAS | MA | k = 49 acute; I2 and GRADE not read |
| S1223 (existing) | Dhillon 2016 | fullness AUC +2,435.74 mm·240 min (95 % CI 1,375–3,496) | MA | k = 5 (28 by vote count) |
| S22.1 | Kohanmoo 2020 | CCK +30 pg/ml, GLP-1 +21; PYY and GIP unchanged; hormones move at ≥ 35 g, ratings at < 35 g | MA | mechanism only |
| S22.2 | Ben-Harchache 2021 | test meal −164 kJ (−299, −29); total intake +649 kJ (438, 861); ratings suppressed in 7 of 24 arms | MA | older adults; 7 studies, 22 arms |
| S22.4 | Qiu 2021 | next intake −111.2 kcal; fullness +7.4 mm; hunger −8.5 mm | MA | children; low quality; considerable inconsistency |
| S22.5 | Henschel 2023 | Qiu corrected to −106.8 kcal | MA | reanalysis; fullness and hunger not redone |
| S22.6 | Mollahosseini 2017 | whey against carbohydrate, short term: CAS −0.39 mm (−2.07, 1.30), I2 0 %; long term −4.13 mm | MA | k = 5 short-term, 3 long-term |
| S22.7 | Bertenshaw 2009 | pasta 637.6 / 596.9 / 546.9 / 533.6 g at control / 13 / 25 / 50 % protein; VAS null | RCT | n = 28 men |
| S1225 (existing) | Raben 2003 | no differences in hunger or intake | RCT | n = 19 |
| S22.35 (open) | — | a per-meal threshold of 25–30 g | — | — |

**Verdict.**
- **Best estimate.** At equal energy, a higher-protein preload lowers rated hunger by about 7–8.5 mm on a 100 mm VAS. Fullness rises about 7–10 mm; Dhillon's AUC averages 2,435.74 / 240 ≈ 10.1 mm across 4 h, which is my arithmetic, not the source's.
- **Next-meal intake** falls modestly: about 164 kJ (39 kcal) in older adults and about 107 kcal in children. The preload's own energy is not compensated: total intake rises by 649 kJ.
- **Certainty: low.** None of these meta-analyses gives a GRADE rating. Qiu's own authors call the trials low quality, and its published reanalysis found statistical errors. The contrasts vary from trial to trial. VAS outcomes are not blinded where the food differs.
- **Against it:** the one pool that isolates whey against carbohydrate is null (I2 0 %), and so is one crossover at similar energy density (Raben 2003, S1225). Veldhorst 2009's null at 25 En% compares protein sources, not protein against carbohydrate, and is not evidence here.
- **Dose.** No pooled source supports a threshold of 25–30 g per meal; that figure comes from narrative reviews. Kohanmoo's ratings moved below 35 g, and Bertenshaw's intake fell in steps across 13–50 % protein. The evidence is a graded response with no threshold. Certainty is low, and the gap is filed as open row S22.35.
- **What weaker evidence claims and the best does not support:** a sharp per-meal threshold; that hormone changes alone mean satiety (S22.1 is mechanism only); and large next-meal intake effects.

## 2. Protein source and digestion speed

| Id | Source | Key value | Grade | Quality |
|---|---|---|---|---|
| S22.8 | Hall 2003 | 48 g whey lowers buffet intake at 90 min against casein (P < 0.05; no magnitude given); CCK +60 %, GLP-1 +65 % | EXP | n not given in the abstract |
| S22.9 | Veldhorst 2009 | whey lowers hunger more only at 10 En%; no intake difference | RCT | n = 25 |
| S22.10 | Abou-Samra 2011 | compensation: casein 110 %, pea 103 %, whey 62 %, albumin 56 %, maltodextrin 51 %; no effect when eaten as a starter | RCT | n = 32 + 32 men |
| S22.11 | Kristensen 2016 | legume meal −12 % / −13 % intake, with its fibre unmatched | RCT | n = 43 |
| S22.12 | Nielsen 2018 | fibre-matched legume, meat and egg meals: no difference | RCT | n = 35 |
| S22.13 | Neacsu 2014 | soy against meat high-protein diet over 2 wk: same hunger and same weight loss | RCT | n = 20 |
| S22.18 (range) | Hansen 2021 | in 6 studies "no specific protein seemed superior"; not meta-analysable | MA | — |

**Verdict.**
- **Best estimate:** no consistent effect of protein source on intake once fibre and energy are matched. Certainty is low, from small single trials that point in opposite directions.
  - Hall finds whey above casein at 90 min. Abou-Samra finds casein and pea above whey at 30 min. Veldhorst finds whey ahead only at the lower dose, with no intake difference.
- **Digestion speed** shifts when the hormones peak: fast whey raises amino acids, CCK and GLP-1 more and earlier. It does not move behaviour consistently.
- **Plant against animal:** the Kristensen advantage disappears when fibre is matched (Nielsen 2018). The evidence favours Nielsen, because its design removes the confound.
- **Not supported:** "whey is the most satiating protein", and "plant protein is more satiating".

## 3. Chronic high-protein diets

| Id | Source | Key value | Grade | Quality |
|---|---|---|---|---|
| S22.14 | Weigle 2005 | ad libitum 30 % protein: intake −441 ± 63 kcal/d, −4.9 kg over 12 wk | EXP | n = 19, sequential, not randomised |
| S22.15 | Skov 1999 | 25 % against 12 % protein, ad libitum, 6 mo: −8.9 against −5.1 kg (difference 3.7, 1.3–6.2) | RCT | n = 65 |
| S22.16 | Due 2004 | at 12 mo, 6.2 against 4.3 kg, not significant | RCT | n = 50; more than 50 % lost by 24 mo |
| S22.17 | Wycherley 2012 | isocaloric: weight −0.79 kg, FFM +0.43 kg; satiety higher in 3 of 5 studies | MA | k = 24, n = 1063 |
| S22.18 | Hansen 2021 | weight −1.6 kg (1.2, 2.0) | MA | k = 37, I2 56 %, mostly high risk of bias |
| S22.3 | Ben-Harchache 2021 | longitudinal intake −54 kJ/d (−300, 193), null | MA | older adults, 12 arms |
| S22.19 | de Carvalho 2020 | fullness or satiety enhanced in 6 of 10 studies | MA (systematic review) | low level of evidence |
| S1222 range (existing) | Kohanmoo 2020 | 19 long-term trials: appetite ratings null | MA | — |
| S22.25 | Martens 2013 (see § 4) | 30 % protein over 12 d: 7.21 against 9.62 MJ/d | RCT | n = 79 |

**Verdict.**
- **Best estimate.** Ad libitum higher-protein diets lower energy intake and weight modestly over weeks: about 1.6 kg more loss in pooled trials, and in single trials about 440 kcal/d (Weigle) or about 2.4 MJ/d over 12 d (Martens, 30 against 15 %).
- **The effect wanes beyond 6–12 months** (Due 2004).
- **Long-term appetite ratings are null** in the pooled trials: Kohanmoo's 19 long-term trials and Ben-Harchache's longitudinal arms.
- **Certainty: low to moderate** for intake and weight (heterogeneous, unblinded, high risk of bias), and low for chronic appetite ratings.
- **Not supported:** that high protein keeps people less hungry for months. Intake falls without a sustained shift in the ratings.

## 4. Protein leverage

| Id | Source | Key value | Grade | Quality |
|---|---|---|---|---|
| S22.20 | Gosby 2011 | 10 against 15 % protein: energy +12 ± 4.5 % (4.34 MJ over 4 d), 70 % of it from between-meal foods; 15 → 25 % no change | RCT | n = 22 lean |
| S22.21 | Gosby 2011 | asymmetry: +4.5 kJ non-protein per kJ of protein short below 15 %; −1 kJ above | RCT | no CI given |
| S22.22 | Gosby 2011 | hunger rise 1–2 h after a 10 % breakfast 1.6 against 0.5 (10 cm VAS) | RCT | — |
| S22.23 | Gosby 2016 | 25 → 10 %: +14 % intake (the same trial); FGF-21 6× | RCT | not independent |
| S22.24 | Gosby 2014 | % protein negatively associated with intake across 38 trials (F = 6.9) | MA (pooled analysis) | slope not in the abstract |
| S22.25 | Martens 2013 | 5 / 15 / 30 %: 9.33 / 9.62 / 7.21 MJ/d; no leverage at 5 % | RCT | n = 79, 12 d |
| S22.26 | Martens 2014 | beef 5 / 15 / 30 %: 9.48 / 9.30 / 8.73 MJ/d; hunger higher at 5 % | RCT | n = 58, 12 d |
| S22.33 | Hall 2019 | ultra-processed diet +508 kcal/d, protein −2 ± 12 kcal/d | RCT | n = 20; not a test of leverage |
| S22.34 | Hägele 2025 | 30 % against 13 % protein ultra-processed diet: intake −196 ± 396 kcal/d | RCT | n = 21, 54 h |
| S22.27–S22.29 | Honfo 2024, Eriksen 2026, Grech 2022 | L = −0.37 (77 kJ per % protein), −0.36, −0.18 | COH | observational, self-reported |
| S22.30 | Saner 2023 | L −0.36 / −0.26 / −0.25 in children | COH | — |
| S22.31 | Kebbe 2023 | null in pregnancy (p = 0.30) | COH | n = 41 |
| S22.32 | Senior 2022 | observational L can be confounded by intake structure; causality is beyond the data | MODEL | method caveat |
| S22.36 (open) | — | a pooled randomised leverage gain with a CI | — | — |

**Verdict.**
- **The high-protein side** (diluting carbohydrate and fat with protein lowers intake) is consistent across randomised trials: Martens 2013 and 2014, Weigle, Hägele, and Gosby's 38-trial pooled analysis. Its size is about 0.6–2.4 MJ/d at 30 % protein. Certainty is moderate.
- **The low-protein side** (diluting protein raises intake), which is what matters for a survival diet, has one positive randomised trial: Gosby 2011, +12 % over 4 d, n = 22, with incomplete leverage. Two larger 12-day randomised trials found no rise at 5 % protein (Martens 2013, n = 79; Martens 2014, n = 58).
  - Population studies agree in direction: L −0.18 to −0.37, which at mean intakes is about 77 kJ less per extra % of energy from protein (Honfo). They are observational and self-reported, and Senior 2022 shows how such slopes can arise structurally.
  - The weight of evidence: real but small and inconsistent, at most about +12–14 % energy over days. It acts through between-meal snacking, not larger meals (Gosby: 70 % from anytime foods; breakfast intake unchanged). It is asymmetric, about 4.5 kJ per kJ of protein shortfall against 1 kJ per kJ of excess.
  - **Certainty: low.** The randomised trials conflict, and the bigger ones are null at 5 %.
- **Not supported:** the observational "strong" leverage (L ≈ −0.36) as a causal gain, and complete leverage. Every trial calls leverage incomplete.

## 5. Protein's effect on the level of hunger

The model reproduces S1224's timing but reads about 10× short of S1222's level. Which reading is right?
- **By quality, the level is the better-supported effect.** It rests on three pooled analyses:
  - Kohanmoo: k = 49, −7 mm hunger;
  - Dhillon: about +10 mm average fullness over 4 h;
  - Qiu: −8.5 mm in children.
- **S1224 is one 11-subject trial.** Its abstract reports no test of the differences between the snacks.
- **The pooled next-meal intake effects fit a mid-sized level:** −164 kJ (39 kcal) in older adults (S22.2) and −107 kcal in children (S22.5).
  - Under the spec's replay mapping (intake = 650 kcal × hunger / 0.25), the oracle's assumed level target of about 0.025 implies about 65 kcal. That sits inside the pooled intake range.
  - The model's 0.0027 implies about 7 kcal: about 10× short on hunger and about 6–15× short on intake.
  - A raw −7 mm read as 0.07 would imply about 182 kcal, which overshoots the intake pools. So the 0.025 target, not the raw 7 mm, is the defensible level.
- **Certainty: low.** The MAs are ungraded and heterogeneous, and the cleanest isolated contrast (whey against carbohydrate, S22.6) is null.
- **The verdict on the evidence's weight:** the timing reproduction does not make the level reading wrong. The model under-reads protein's acute level effect, and the evidence favours fixing the level while accepting a looser fit to Marmonier's absolute delays, which are already a named non-reproduction.

## 6. What this means for the model

**Supported (keep):**
- Protein counts per kcal with no source distinction. No protein source differs consistently from another: the single trials point in opposite directions (S22.8–S22.10), plant and animal meals do not differ once fibre is matched (S22.12) or over two weeks of dieting (S22.13), and Hansen 2021 found no superior protein (S22.18). So the vector's `proteins` grams are enough and no source key is needed.
- No per-meal threshold. A linear per-kcal weight in `K.satiety.feed` matches the graded dose-response (S22.7) and the effects below 35 g (S22.1).
- Neutral fibre, and fibre confounding protein comparisons. Kristensen's plant advantage disappears when fibre is matched (S22.12), which is consistent with ruling 11c-6.
- Carbohydrate equal to fat, with protein above both. Nothing here contradicts it.
- **Long-term appetite ratings stay flat** (Kohanmoo long-term, S22.3). The model has no chronic protein appetite term, which is correct.

**Argued against, with sizes:**
- **Protein's acute level effect is about 10× too small** (§ 5).
  - Raising `W_PROTEIN` on the pool alone would also lengthen the time to the request, and the Marmonier timing is already a non-reproduction.
  - A labelled option: let the eaten protein's kcal also add to fullness F for the stomach residence (a protein term in `sated`), or give protein a faster-decaying second pool. Either moves the level without moving the request time as much.
  - The target is a level contrast of about 0.025 under the oracle mapping, which is equivalent to 40–110 kcal less at the next meal for a preload of roughly 25 % against 10 % protein. Certainty is low.
- **No compensation for the preload's own energy** (S22.2: +649 kJ total). The model already books preload energy into P with incomplete suppression; this supports that it should not fully compensate. No change is needed; it is a check for the oracle.

**What the model leaves out:**
- **Chronic intake reduction on high-protein diets.** Through the repeated W_PROTEIN feed, the model gives some of it automatically. The evidence size is about 0.6–2.4 MJ/d at 25–30 % protein over 12 d–12 wk (Martens 2014 0.57 MJ/d; Hägele 2025 196 kcal/d; Weigle 2005 441 kcal/d; Martens 2013 2.41 MJ/d), and about 1.6 kg over months (moderate for direction, low for size). A game check: a player eating 30 %-protein food should, by the model, eat roughly 6–25 % fewer kcal ad libitum. If the oracle replays it far below that, the protein term is too weak, which matches the level finding.
- **Protein leverage on low-protein diets.**
  - The evidence: +12 % energy at 10 % against 15 % protein over 4 d, as between-meal hunger, asymmetric at 4.5:1.
  - Its certainty is low, against null randomised trials at 5 %.
  - In game terms, the mod would read a rolling 1–4 day protein-energy share from the intake history and raise between-meal hunger when it falls below about 15 %.
  - Under decision 5 (mixed evidence ships neutral), this is **not** shippable as an effect now. The open row S22.36 is the gap. If Angus wants it as a labelled game choice for gameplay (a rice-and-sugar survival diet drives snacking), the defensible cap is about +12 % of daily energy, ramping in over 1–2 days, never complete.
- **Hormone mechanisms** (CCK, GLP-1, FGF-21) are mechanism only, and nothing should read them.

## 7. Slug requests and supersede candidates

- **Slugs.** None requested.
  - The leverage rows use `protein`, because protein appetite is the regulated quantity.
  - The weight-only rows (S22.15–S22.18) use `body-composition`.
  - The intake and hunger rows use `satiety`.
- **Supersede candidates.** None.
  - S1222 stands. Its range line "appetite ratings moved at protein doses < 35 g" agrees with S22.1.
  - S1225 (Raben null) is joined by S22.6 (whey against carbohydrate null) as a quality-matched null beside the pooled positives. Both readings are kept, and the parameters name the disagreement.

## 8. Concerns

- **The `source` cell.** The brief says it should read "Satiety research 2, protein harvest (2026-10-09)", but `SOURCE_RX` requires `<path>.md § <heading>`. I used `docs/superpowers/specs/2026-10-08-satiety-physiology-design.md § 5. Evidence (the harvest), Satiety research 2, protein harvest (2026-10-09)`, following the Plan 11c precedent. The controller may want a different path.
- **Resolution route.** Europe PMC search was rate-limited (503), so the records were resolved through PubMed E-utilities. Full texts were read through Europe PMC where open.
- **Not read beyond the abstract:**
  - Kohanmoo 2020, Wycherley 2012 and Ben-Harchache 2021 are not open access, so their I2 and risk-of-bias verdicts were not read.
  - The CI of Henschel's corrected −106.8 kcal sits in a table that the text extraction did not carry.
- **Possible overlaps.** Hall 2019 (ultra-processed foods) may overlap Task 27 or Task 23; it is filed here only for its protein-intake reading. Eriksen 2026 is very recent (Appetite, May 2026).
- **Gosby 2016 repeats the Gosby 2011 trial's intake** (25 → 10 %, +14 %). It is not independent, and the row says so.

---

# Citation review

# Task 22 citation review (protein and satiety)

Model: claude-opus-5-5. Reviewer: read-only citation review, 2026-10-09.

## Method

All 31 distinct PMIDs of the 34 settled rows were fetched from PubMed E-utilities (efetch, abstract text; Europe PMC REST returned 503 after the first call). Full texts were read from PMC for Henschel 2023 (PMC10096717), Hansen 2021 (PMC8468854), Gosby 2011 (PMC3192127), Qiu 2021 (PMC8399074) and Grech 2022 (PMC9828743). For every settled row the title, first author, year, journal, volume, pages, DOI and PMID match the record, and every number in value, range and population was found verbatim in the abstract or full text. Grades match each source's design (Weigle 2005 EXP, sequential; Hall 2003 EXP, randomisation not stated; Senior 2022 MODEL; observational L rows COH).

## Verdict: FAIL (small fixes; no fabricated or misread row value)

## Defects

1. S22.5, range. The corrected CI and I2 are in Henschel 2023's Table 1, which is open (PMC10096717); the row says the table was not read, and the harvest rules require the CI and I2 in the range. Corrected cell:
   `the reanalysis keeps Qiu 2021's study selection and corrects two statistical errors (within-subject correlation in six crossovers; three multi-arm studies entered without adjustment) and data-extraction errors; random effects; corrected estimate 95% CI -130.3, -83.2 kcal, I2 = 51% (as published by Qiu 2021: -145.42, -76.9 kcal, I2 = 67%); a published comment; no certainty rating given`
2. S22.29, population. The full text gives the analysed sample. Corrected cell:
   `9341 adults >= 19 y, mean age 46.3 y; Australian National Nutrition and Physical Activity Survey 2011-2012`
3. Report § 1 verdict, "Against it". Veldhorst 2009's null at 25 En% is between protein sources (whey, casein, soy), not protein against carbohydrate; citing it as a null of protein's satiety effect is a between-arm contrast misread as the effect in question. Corrected bullet:
   `- **Against it:** the one pool that isolates whey against carbohydrate is null (I2 0 %), and so is one crossover at similar energy density (Raben 2003, S1225). Veldhorst 2009's null at 25 En% compares protein sources, not protein against carbohydrate, and is not evidence here.`
4. Report § 6, "Supported (keep)", first bullet. It says the sources "do not differ" citing S22.9–S22.13, but S22.8–S22.10 each report a difference between sources (in opposite directions); § 2's own verdict is "no consistent effect". Corrected bullet:
   `- Protein counts per kcal with no source distinction. No protein source differs consistently from another: the single trials point in opposite directions (S22.8–S22.10), plant and animal meals do not differ once fibre is matched (S22.12) or over two weeks of dieting (S22.13), and Hansen 2021 found no superior protein (S22.18). So the vector's `proteins` grams are enough and no source key is needed.`
5. Report § 6, "What the model leaves out", first bullet. "about 0.4–2.4 MJ/d" has no row behind its lower end (Weigle's 441 kcal/d is 1.85 MJ/d; the smallest row contrast is Martens 2014's 0.57 MJ/d), and "roughly 10–25 % fewer kcal" excludes Martens 2014's 6 % (8.73 against 9.30 MJ/d). Corrected sentences:
   `The evidence size is about 0.6–2.4 MJ/d at 25–30 % protein over 12 d–12 wk (Martens 2014 0.57 MJ/d; Hägele 2025 196 kcal/d; Weigle 2005 441 kcal/d; Martens 2013 2.41 MJ/d), and about 1.6 kg over months (moderate for direction, low for size). A game check: a player eating 30 %-protein food should, by the model, eat roughly 6–25 % fewer kcal ad libitum.`

## Residuals (no change required)

- Ben-Harchache 2021 is open access (PMC8009738); the report calls it not open access, and S22.2 and S22.3 could carry the I2 and risk-of-bias from the full text. Optional.
- Gosby 2011's abstract gives p = 0.02 for the 10 against 15 % intake rise, its Results P < 0.0001; S22.20 carries the abstract's figure, which is the source's own.
- S22.20 "foods available between meals": the paper's term is foods "available anytime"; S22.22's "between-meal snacking, not larger meals" is the harvester's reading of the 70 % / 30 % split, acceptable in a range cell.
- S22.7 (Bertenshaw 2009) is graded RCT; the abstract says repeated-measures crossover and does not state randomisation. Consistent with the register's precedent (S1224); EXP would be the conservative grade if the full text says not randomised.
- S22.6 population "adults": the abstract does not state the age group.
- S22.1 repeats S1222's dose sentence; it adds CCK and GLP-1, so it is a new value and not a duplicate.
- The `source` cell departs from the brief's form to satisfy SOURCE_RX (report § 8), and Task 27 used its own report path instead of the spec; the controller should make the wave consistent.
- The report's § 5 figures (0.025 target, 0.0027 model) were not traced to their oracle file; the 650 kcal × hunger / 0.25 mapping is in the spec (line 148) and the arithmetic is correct.
