# Review: the water harvest part file (S12.1–S12.16) and its report

Date: 2026-10-16. Reviewer: read-only citation review, model `claude-opus-5-5`.
Inputs: `.superpowers/sdd/game-feel-research/water-part.tsv`, `water-report.md` (this folder), `docs/reference/science.md`, the `science.tsv` header.

**Verdict: FAIL.** The citations all resolve and every number checked matches its source. The failures are in locators and labels: a figure legend quoted as "Results", a single-visit median quoted without its visit, a derived share that the paper itself states, and uninferred inferences. The report also has three errors in its prose. Each fix below is exact cell text, and none changes the recommendation of about 2000 g/day.

`python tools/science_check.py --part .superpowers/sdd/game-feel-research/water-part.tsv` → `0 findings`.

## 1. Citation resolution

| row(s) | record | resolved through | title, first author, year | verdict |
|---|---|---|---|---|
| S12.1–S12.6 | doi:10.1126/science.abm8668, pmid:36423296 | Europe PMC (PMC9764345 author manuscript read in full at pmc.ncbi.nlm.nih.gov) | "Variation in human water turnover associated with environmental and lifestyle factors", Yamada Y, 2022, Science 378:909-915 | match |
| S12.8, S12.9 | doi:10.1017/s0007114512003601, pmid:22935250 | Europe PMC, full text PMC3638312 | "Hydration biomarkers in free-living adults with different levels of habitual fluid consumption", Perrier E, 2013, Br J Nutr 109:1678-1687 | match |
| S12.10 | doi:10.1186/s12937-020-0523-6, pmid:31996207 | Europe PMC, full text PMC6990513 | "Trends in tap and bottled water consumption among children and adults in the United States: analyses of NHANES 2011-16 data", Vieux F, 2020, Nutr J 19:10 | match |
| S12.11 | doi:10.3390/nu11030657, pmid:30889919 | Europe PMC (abstract) | Stookey JD, 2019, Nutrients 11:657 (E657) | match |
| S12.12 | pmid:1807842 | Europe PMC (abstract) | "Insensible water loss in resting adults in Kandy, Sri Lanka", Ratnatunga PC, 1991, Ceylon Med J 36:151-154 | match |
| S12.7 | doi:10.2903/j.efsa.2010.1459 | Crossref (title, NDA Panel, EFSA Journal 8(3), 2010-03); abstract from OpenAlex | "Scientific Opinion on Dietary Reference Values for water", EFSA NDA Panel, 2010 | match |
| S12.13 | WHO PDF url | fetched (HTTP 200, application/pdf) | Technical note 9, "Updated: July 2013", Table 9.1 | match |
| S12.14 (gap) | pmid:6706769 | Europe PMC | Pivarnik JM 1984, J Appl Physiol 56:613-618; the abstract gives no per-gram yields | match |
| S12.15 (gap) | pmid:27612366 | Europe PMC | Charkoudian N 2016, Mil Med 181:1142-1150 | match |

**Mirror reading of EFSA (S12.7): accepted.** OpenAlex reconstructs the publisher's abstract from its inverted index. I rebuilt the abstract independently and every sentence quoted in S12.7 is verbatim, "(P 95 3.1 L)" and "(P95 4.0 L)" included. The reconstruction drops some dashes ("800 1000 mL/day"), but none of the quoted text is affected. An abstract-only reading is honest, provided the row keeps its note that only the abstract was read, which it does.

## 2. Numbers against the source

Every quoted number was matched, except for the locator issues in § 3. In detail:
- Yamada:
  - eq. 1 and eq. 2 coefficients;
  - 47.1 %;
  - 0.33 ± 0.09 L/MJ;
  - the ~10 % and 2–3 % shares;
  - the 20–50 % food share;
  - 3729/1875;
  - 23 countries (abstract) against 26 (manuscript);
  - eq. 1 reproduces the worked examples, 3184 and 2666 mL/d.
- Perrier: 0.74 (sd 0.37) and 2.70 (sd 0.40) L, 0.55 (0.41–0.81) and 0.68 (0.51–0.88) L, 56 % male at 31.3 y and 31 % male at 32.1 y, 500 mOsm/l, approximately 80 %.
- Vieux: 2718, 1066, 1036 and 618 mL/d, and about 40 %.
- Stookey: 42 (2), 14 (1), 43 (2) and 16 (1) mL/kg; RR 1.36 (1.10–1.68) and 1.70 (1.49–1.95).
- Ratnatunga: 1,333, 1,230 and 1,423 ml; 1,000–1,200 ml; 63 adults (44 men); 6 men.
- WHO Table 9.1: every cell.

## 3. Row defects (exact corrected cells)

**D1 — S12.1 `value`: the locator is wrong.** Both quoted sentences are from the legend of Fig. 2 in the author manuscript, not from the Results text. The 4.3 L/d is also the men's figure near the age-30 peak, not an adult mean.
Corrected `value`:
`Fig. 2 legend (author manuscript PMC9764345): "Water turnover increases with age until about 30 years and is higher in men (4.3 L/d) than women (3.4 L/d). Water turnover significantly decreases after 30 years in men and 55 years in women, reaching an average water turnover of 3.1 and 2.8 L/d in men and women aged over 70 years, respectively"`

**D2 — S12.1 `range`: the quote's place and the inference are not labelled.** The "incredibly large" sentence is in the same Fig. 2 legend. The clause after the semicolon is Yamada's Fig. 1 framing.
Corrected `range`:
`Fig. 2 legend: "the variation in water turnover is incredibly large – the low end for men and women is ~1–1.5 L/day while the upper end is around ~6 L/day – and the outliers lie in the 10L/d range"; turnover includes metabolic water and water taken up from air, not only intake (Fig. 1A; S12.5); the 4.3 L/d is read in the legend against the rise to about age 30, so it is the men's figure near the peak, not an all-adult mean (inference from the legend's wording)`

**D3 — S12.9 `value`: the food-water medians are from one visit only, and the non-significance is dropped.** The paper says "During V5" and "no significant between-group differences during V3, V4 and V5".
Corrected `value`:
`Results: "LD consuming 0·74 (sd 0·37) litres and HD consuming 2·70 (sd 0·40) litres (P < 0·001)"; "The amount of water from food was largely similar between the groups, with Wilcoxon rank-sum tests revealing no significant between-group differences during V3, V4 and V5. During V5, the median (Q1–Q3) volume of water obtained from food was 0·55 litres (0·41–0·81) in the LD group, and 0·68 litres (0·51–0·88) in the HD group"; abstract: "Plasma osmolality was similar between the groups, suggesting physiological adaptations to preserve plasma osmolality despite low fluid intake"`

**D4 — S12.10 `range`: the 23 % is labelled as harvester arithmetic, but the paper states it.** The paper's Results also give the sex split (Table 1), which the abstract's pooled mean hides.
Corrected `value`:
`abstract: "Total dietary water (2718 mL/d) came from water (1066 mL/d), other beverages (1036 mL/d) and from food moisture (618 mL/d)"; Results: "Total water intake was 2718 mL/d, of which 2100 mL/d (77%) came from water and other beverages and 618 mL/d (23%) came from food moisture"; Table 1, mean (SE): males 2949 (36) total, 664 (6) food moisture; females 2495 (25) total, 574 (7) food moisture mL/d; abstract: "Only about 40% of the NHANES sample on average followed US recommendations for adequate water intakes"`
Corrected `range`:
`two 24-h dietary recalls (self-report); the "All" and sex rows pool everyone over 4 y (children and adults); Table 1 SEs as given`

**D5 — S12.11 `parameter` and `range`: a unit is missing, and the RR does not say what it compares.**
Corrected `parameter`:
`total and plain water intake per kg body mass associated with meeting hydration criteria (serum sodium 135-144 mmol/L and urine osmolality < 500 mmol/kg), NHANES 2009-2012`
Corrected `range`:
`adjusted RR of meeting the hydration criteria for TWI ≥ 45 mL/kg or PWI ≥ 20 mL/kg, US population 19-50 y: 1.36 (95% CI 1.10-1.68) males, 1.70 (1.49-1.95) females; the medians are of those meeting the criteria, not a minimum`

**D6 — S12.12 `range`: the climate reading is an inference without a label.**
Corrected `range`:
`abstract only; skin plus respiratory loss together; inference: a tropical town, so an upper reading for a temperate climate (S1688 gives respiratory 250-350 and insensible 450-1,900 mL/d)`

**D7 — S12.15 `range`: the abstract was read and holds no value. "Not read for a value" misstates this.**
Corrected `range`:
`Charkoudian 2016 (Mil Med 181:1142-1150, doi:10.7205/milmed-d-15-00291, pmid:27612366) describes the US Army SWET planning application; its abstract (read in Europe PMC) gives no drinking-water value, and the equations it implements (TB MED 507 and their update) were not read`

**Advisory (not a FAIL item) — S12.7 `population`.** The abstract counts adolescents from 14 y as adults and sets the same AI for the elderly. "in the EU" does not come from the abstract.
Suggested `population`:
`adults (adolescents from 14 y counted as adults; the same AI for the elderly), EU reference populations, at moderate temperature and PAL 1.6`

**Grades:** all fit.
- S12.1–S12.6, S12.9–S12.12: COH. These are cohort, cross-sectional or regression sources.
- S12.7 and S12.13: AUTH.
- S12.8: COH. It is graded by Perrier's own design, and its range labels it as a secondary reading of the AUTH opinion.

**Inference labels:** apart from D2 and D6, they are adequate. S12.2's "not a minimum", S12.5's "not measured in this cohort" and S12.13's "not a physiological minimum" are all written in the range as readings.

## 4. Duplicates

I grepped every doi, pmid and url against `docs/reference/science.tsv`:
- abm8668, s12937-020-0523-6, nu11030657, 1807842, efsa.2010.1459, the WHO note, milmed-d-15-00291 and 6706769: no hits. The S2094 "Yamada" hit is a different paper.
- s0007114512003601 (Perrier 2013) is already S1711. S12.8 and S12.9 take different parameters from the same record: the EFSA basis, the 80 % share, fluid volumes and food water, where S1711 has the urine and plasma markers. They are not duplicates.
- S1686–S1688 and S1707–S1711 are cited, not re-minted.

**S12.7 against S0089: a duplicate parameter, so a controller ruling is needed.** S0089 is the open row "adequate intake of total water (EFSA 2010)" on the same record. S12.7 answers it fully: the AI values come from the abstract, and the citation resolves.
- **Recommended:** drop S12.7 from the part and run `science_delta.py settle S0089` with S12.7's topic, value, range, population, grade and citation cells. This keeps the original id and leaves no twin row. S12.8–S12.16 then renumber down by one.
- **Alternative:** mint S12.7 and run `status S0089 superseded --successor <S12.7's id>`.
- If S12.7 is minted, S0089 must not be left `open`.

## 5. The route arithmetic (report § 1)

Re-derived from the rows the report cites:
- respiratory 300: the midpoint of S1688's 250–350;
- skin 450: S1688's insensible floor;
- faeces 150: the midpoint of 100–200;
- urine: 650 mOsm (S1687) / 500 mOsm/L (S12.8) = 1.30 L;
- gross 300 + 450 + 150 + 1300 = **2200**;
- minus metabolic 300 (the midpoint of S1688's +250 to +350) = **1900**, rounded to 2000;
- 1900 and 2000 both sit inside S1688's net range of 1,050–3,100 mL/d.

The arithmetic is correct. Two report errors and one labelling gap follow.

**D8 — report § 1, second paragraph: the urine figure is wrong.** If 2.2 L of drink plus food is the net loss, gross is 2.2 + 0.3 = 2.5 L. Non-urine routes are 0.9 L, so urine is about **1.6 L**, not 1.5 L.
Corrected sentence:
`That figure means about 1.6 L of urine a day (2.2 + 0.3 metabolic − 0.9 breath, skin and faeces), which is still well below the 2.2 L average measured by isotope turnover (S1709).`

**D9 — report § 1 table, urine row: the label is missing.** The 1300 g is above S1688's minimum urinary range of 500–1,000 mL/d. It is urine at the EFSA "desirable" osmolarity, not an obligatory minimum. The row should say so, so that "a minimum should" in the bounds is not read as true of the urine term.
Corrected `rests on` cell:
`about 650 mOsm/d of solute on a Western diet (S1687), excreted at EFSA's "desirable" 500 mOsm/L (S12.8); above S1688's minimum urine of 500–1,000 mL/d by choice, not an obligatory loss`

**D10 — report § 1, "Average, not minimum": the 4.3 L/d is misattributed.**
- S12.1 does not say men aged 20–35 average 4.3 L/d. The legend says turnover rises until about age 30 and is 4.3 L/d in men.
- Raman (S1709) studied adults aged 40–79, so the "temperate adults" there are middle-aged and older.

Corrected bullet:
`- **Average, not minimum:** isotope turnover in men rises to about 4.3 L/d near age 30 (S12.1, Fig. 2 legend).`

Other cross-checks: all correct.
- Yamada eq. 1, 65 kg man, 30 y, PAL 1.4, 50 % RH, high HDI: 2807 mL/d at 10 °C and 3170 mL/d at 20 °C, so 2.8 and 3.2 are correct.
- 85 % of those is 2.39–2.69 L, so 2.4–2.7 is correct.
- Mifflin, 65 kg, 175 cm, 30 y man: 1599 kcal. At PAL 1.4 that is 9.37 MJ, and 0.20–0.35 L/MJ gives 1.87–3.28 L.
- 42 mL/kg × 65 kg = 2.73 L.
- 2000/3700 = 54 %.
- 618/2718 = 22.7 %.

## 6. S1688, S0088 and S0515 (report § 9.5)

- S1688 is the IOM Table 4-2 minimum-loss table ("Estimation of Minimum Daily Water Losses and Production"). The report is **correct**, and the outline's "S1688 = adequate intake" is a mislabel.
- S0088 is the IOM/NASEM AI, 3.7 and 2.7 L/d, and is settled.

**D11 — report § 1 and § 9.5: S0515 is superseded and should not be cited as a live AI row.** S0515 holds the same AI but is `superseded` with successor S0088. The mod's comment cites S0088 alone, and a `--scan` would fail an S0515 token.
Corrected § 9.5 sentence:
`That is a mislabel: S1688 is the IOM minimum-loss table, and the AI row is S0088 (S0515, an earlier copy of the same AI, is superseded by S0088).`
Corrected § 1 bullet:
`- The IOM/NASEM AI is 3.7 L/d for men and 2.7 L/d for women (S0088). This is today's `K.fluids.AI`.`

## 7. The lean-mass scaling (report § 9.2) against S12.3

- **The arithmetic is correct:** 2000 / 55 = 36.4 g per kg of lean mass a day, and × 40 kg = 1455 g.
- **The support claim overreaches.**
  - S12.3 is an affine regression: a marginal 37.34 mL of *turnover* per kg FFM, beside a PAL term, climate and age terms and a −984.8 intercept. It is not a proportional scale through zero.
  - The closeness of 36 to 37.34 is a coincidence of the chosen reference man (2000/55). It is not S12.3's coefficient, and it is applied to net intake-side loss, not to turnover.
  - Under the report's own conditions, eq. 2 gives 3009 mL/d for 55 kg FFM and 2448 mL/d for 40 kg FFM, a ratio of **0.81**. The proportional scale gives **0.73**, so it overstates the lean-mass gap that S12.3 measures.
- What S12.3 *does* support is the qualitative point: given FFM, the sex term is not significant.

**D12 — report § 9.2, third and fifth bullets: the wording needs correcting.**
Corrected third bullet:
`- A lean-mass scale fits the model, which already reads `body.lm` for TBW. The proportional form `basalG/day = BASAL_PER_LM × lm`, with BASAL_PER_LM ≈ 2000 / 55 ≈ 36 g per kg of lean mass a day, is a game choice: S12.3 is affine (37.34 mL of turnover per kg FFM beside fixed terms), and at equal PAL, age and climate its eq. 2 gives a 40 kg-FFM person 0.81 of a 55 kg-FFM person. An affine form, `basalG/day = 2000 + 32 × (lm − 55)` (32 ≈ 0.85 × 37.34, the intake share of S12.5 applied to S12.3's slope), follows S12.3 more closely and gives the 40 kg-lean woman about 1520 g (0.76). The reference man's 55 kg of lean mass is the report's assumption, not a cited value.`
Corrected fifth bullet:
`- Either scale is a game choice: S12.3 supports dropping the sex term once lean mass is known, not the proportional constant; the REE scale rests on S12.4's water-per-energy ratio.`

## 8. Can S12.7 settle S0089?

**Yes.** S0089's parameter is "adequate intake of total water (EFSA 2010)", and its range names exactly the EFSA Journal 8(3):1459 record whose values "were not read". S12.7 reads those values from the abstract:
- AI 2.0 L/d for women (P95 3.1 L) and 2.5 L/d for men (P95 4.0 L);
- the same AI for the elderly;
- moderate temperature and PAL 1.6.

The abstract is the record's own text. Crossref resolves title, author and year, which meets the minting rule. Settle in place, as recommended in § 4. The settled bound should keep S12.7's note that only the abstract was read, through mirrors.

## 9. Defect list

| # | where | problem |
|---|---|---|
| D1 | S12.1 value | the Fig. 2 legend is quoted as "Results" |
| D2 | S12.1 range | the legend locator and the inference are unlabelled |
| D3 | S12.9 value | the V5-only medians and the non-significance are omitted |
| D4 | S12.10 value, range | the source-stated 23 % is relabelled as derived; the sex split is omitted |
| D5 | S12.11 parameter, range | a unit is missing; the RR comparison is unstated |
| D6 | S12.12 range | the climate inference is unlabelled |
| D7 | S12.15 range | "abstract not read for a value" is wrong; the abstract has no value |
| D8 | report § 1 | the outline's 2.2 L implies 1.6 L of urine, not 1.5 L |
| D9 | report § 1 table | the urine 1300 is above S1688's minimum urine and is not flagged as a choice |
| D10 | report § 1 | the 4.3 L/d is misattributed to "men aged 20–35" |
| D11 | report § 1, § 9.5 | S0515 is cited as a live AI row, but it is superseded by S0088 |
| D12 | report § 9.2 | the proportional 36 g/kg is presented as resting on S12.3, but S12.3 is affine (ratio 0.81 against 0.73) |
| ruling | S12.7 / S0089 | a duplicate parameter: settle S0089 in place, or supersede it |
