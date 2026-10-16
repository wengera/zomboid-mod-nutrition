# Review of the volume part (S13.1–S13.6) and the β report

Reviewer: read-only citation review, 2026-10-16. Model: claude-opus-5-5.

Inputs: `.superpowers/sdd/game-feel-research/volume-part.tsv`, `volume-report.md`, `docs/reference/science.md`, the `science.tsv` header.

**Verdict: FAIL.** Two row cells need fixing (S13.3, S13.4). One relevant trial is missing, so there is a new row S13.7 and S13.6 changes with it. The report has four small fixes. All of β's arithmetic re-derives.

## Mechanical checks

- `python tools/science_check.py --part .superpowers/sdd/game-feel-research/volume-part.tsv` gave **0 findings**.
- **Duplicates: none.** No DOI or PMID in the part, and no record the open rows name, is in `docs/reference/science.tsv`: 10.1186/1475-2891-11-71, 22978828, 10.1016/s0031-9384(03)00055-6, 12782213, 10.1152/ajpgi.00117.2009, 19779010, the SR Legacy URL, 10.1016/j.foodres.2012.10.042 and 10.1016/j.foodres.2014.09.034. S0169 (open) only names SR Legacy as a future source, so S13.4 does not duplicate it.

## Citation resolution (Europe PMC core records; Crossref for the Elsevier DOIs)

| row | record | title, first author, year, journal, pages | numbers |
|---|---|---|---|
| S13.1 | pmid 22978828 = doi 10.1186/1475-2891-11-71 (PMC3502142) | match (Nguyen 2012, Nutr J 11:71) | every number matches the abstract: 35 (17 men, 18 women), 20–50 y, BMI 23 ± 2, 4 g/15 kcal, 27 g/100 kcal, 28 g/150 kcal, 200 mL, VAS at 30 min, 803/716/698/739 ± SDs, P < 0.01, compensation 220 ± 967, 76 ± 143, 42 ± 75 %. RCT fits the convention for a controlled crossover. |
| S13.2 | pmid 12782213 = doi 10.1016/s0031-9384(03)00055-6 | match (Bell 2003, Physiol Behav 78:593-600) | 36 women, 300/600 mL, 2067/4134 kJ, four other foods, and the finding all match. RCT fits a controlled crossover. |
| S13.3 | pmid 19779010 = doi 10.1152/ajpgi.00117.2009 | match (Kwiatek 2009, AJP GI 297:G894-901) | 12 combinations, 200–800 mL, 200–400 kcal, 16 subjects, 60 min, < 4 mmHg and P < 0.01 all match. **Defect 1** concerns the half-emptying sentence. EXP is acceptable: a factorial dosing experiment with no stated randomisation or control arm. |
| S13.4 | url (200 OK, 6074592 bytes, the same as `tools/.fdc/manifest.json`) | the local zip was re-read | 14449 rows match. Every example gram weight matches `food_portion.csv`: broccoli 169967 at 0.5 cup chopped = 78; raw broccoli 170379 at 1 cup chopped = 91; 172099 at 1 cup = 246; 174924 at cubes 35, slice 29, crumbs 45; popcorn 173141 at 1 cup = 7.9. Coverage of 346 and 201 of 361 ids re-derives from `data/food-nutrients.json` (items plus fluids) with a word-bounded unit match. AUTH is consistent with S1213 and S1214. **Defect 2** concerns the range cell. |
| S13.5 (open) | Le Bleis 2013 (Food Res Int 50:308-317) and Pentikäinen 2014 (66:356-364) resolve on Crossref | match | Abstracts read: Le Bleis reports rheology, moisture and particle size; Pentikäinen reports EMG work, particle size and in vitro starch hydrolysis. Neither reports bolus porosity, so the gap stands. A Europe PMC search for "bolus" AND "porosity" with bread, cereal, popcorn or snack found nothing that measures bolus or gastric porosity against the food. |
| S13.6 (open) | — | — | **Defect 3**: it misses Rolls 2014, a chewed-solid volume trial (below). |

## Defects in the rows

### Defect 1: S13.3, the value cell (an unlabelled reading of a self-contradictory abstract sentence)

The abstract's words are "GCV half-emptying time **decreased** with CL at 18 ± 6 min for each additional 100-kcal load (P < 0.001)". The same abstract also says "at any given volume, gastric emptying was slowed by higher CL". The row writes "rose" without saying that this is the harvester's reading. The full text (journals.physiology.org) could not be fetched to settle it.

Corrected `value`:

> the stomach expanded with meal volume, but the ratio of gastric content volume to meal volume at t0 diminished with increasing meal volume (P < 0.01); filling and early postprandial volume change were unaffected by calorie load; at any given volume gastric emptying was slowed by higher calorie load (P < 0.001), and the abstract states the gastric content half-emptying time "decreased with CL at 18 +/- 6 min for each additional 100-kcal load" (P < 0.001), read here as a rise of 18 +/- 6 min per 100 kcal (inference from the slowing; full text not read); intragastric pressure rose under 4 mmHg

Corrected `range`:

> factorial design, 12 iso-osmolar combinations of meal volume (200, 400, 600, 800 mL) and calorie load (200, 300, 400 kcal) of a multinutrient drink by nasogastric infusion; MRI and fibre-optic pressure over 60 min; t0 is the start of the fitted emptying model (end of infusion, inference); no certainty rating given

### Defect 2: S13.4, the range cell (the mod's own coverage count is not a property of the source)

"201 of the 361 FDC ids the mod maps carry a volume measure, 346 carry some portion" is a reading of `data/food-nutrients.json`, not of the USDA table. It belongs in the report, where § 4 already gives it. The cell should carry the source's own caveats. Every row's `measure_unit_id` is 9999 ("undetermined"; all 14449 rows checked), and that is the source fact a parser needs.

Corrected `range`:

> a cup volume is a packing volume that depends on the cut (bread: 1 cup crumbs 45 g, 1 cup cubes 35 g; one food may carry several slice weights, bread white 29 g and 25 g); every portion row carries measure_unit_id 9999 (undetermined), so the unit and count are read from the modifier text (water: serving 8 fl oz = 237 g)

### Defect 3: a missing chewed-solid volume trial, a new row S13.7, and S13.6's range cell

Rolls, Meengs and Roe 2014 crushed wheat flakes to 80, 60 and 40 % of their volume at constant weight. It resolves on Europe PMC (pmid 24656953) and Crossref (doi 10.1016/j.jand.2014.01.014; J Acad Nutr Diet 114(9):1411-1416; title, first author and year match). It is not in `science.tsv`.

It is the one trial that varies a chewed solid's plate volume at constant energy density. It supports the report's § 2 conclusion that chewed bulk acts through the eye and the portion taken, not through gastric fill. S13.6's "no such trial" stays true, because this trial measures self-served intake at the same meal and not a later meal, but the cell should name it.

New row (tab-separated in the part, cells given here one per line):

- id: `S13.7`
- topic: `satiety`
- parameter: `self-served and eaten breakfast intake of a wheat-flake cereal crushed to 80, 60 or 40 % of its standard volume at the same weight (chewed-solid volume at constant energy density, self-selected portion)`
- value: `as flake size was reduced subjects poured a smaller volume but a greater weight and energy of cereal (both P < 0.0001) and estimated a similar number of calories for all versions; they ate most of what they took, so breakfast energy intake rose from 286 +/- 18 kcal to 358 +/- 19 kcal, an increase of 34 +/- 7 % (mean +/- SEM, P < 0.0001)`
- range: `crossover, once a week for 4 weeks (2011-2012); a constant weight of cereal served in an opaque container, poured into a bowl with fat-free milk and noncalorie sweetener as desired and eaten ad libitum; mixed linear model; the effect acts on the portion taken, and no later meal was measured; no certainty rating given`
- population: `41 adults`
- grade: `RCT`
- citation: `Rolls BJ, Meengs JS, Roe LS 2014, J Acad Nutr Diet 114:1411-1416; doi:10.1016/j.jand.2014.01.014; pmid:24656953`
- source: `docs/superpowers/research/2026-10-16-game-feel/volume-report.md § 1. Volume at matched energy`
- status: `settled`

Corrected S13.6 `range`:

> no such trial located on Europe PMC, 2026-10-16: the matched-weight aeration trials are a liquid shake preload (S1483) and an ad libitum snack (satiation, S1484); the chewed-cereal trial at constant weight and reduced flake size measures the self-served portion at the same meal, not a later meal (Rolls 2014, S13.7); the popcorn and chips trial (S13.1) differs in energy as well as volume

The report's § 1 "Volume without weight (air, chewed solids)" and § 2 bullet "So the effect of chewed bulk is mainly oral and visual" should cite S13.7 beside S1484.

## The report

### β arithmetic: every derivation re-derives

- **(a) foam, from S1233 and S1483.** S1233 gives 5263 − 4703 = 560 kJ. S1483 gives 3368 − 2966 = 402 kJ. 402 / 560 = 0.718, which rounds to 0.72. 402 / 3368 = 11.94 % (the abstract's "12 %"), so 3368 is lunch without the preload. 560 / (5263 − 2088 = 3175) = 17.64 %, which also excludes the preload, so the two percentages are on the same basis. 11.94 / 17.64 = 0.677, which rounds to 0.68.
  - The premise that the 1998 extra volume was water is stated in Rolls 2000's Background ("increasing the volume of food by adding water"), and the report labels it as inferred.
  - The groups, 20 and 28 men, match S1233 and S1483.
- **(b) snack, from S1484.** 5.7 / 0.45 = 12.67 mL/g and 5.7 / 1.00 = 5.70 mL/g. 0.79 × 11.67 = 9.22, so 0.79 + 9.22β = 1 + 4.70β, which gives β = 0.21 / 4.52 = 0.0465, or 0.046.
  - Robustness, a reading: the rounded inputs imply a volume rise of 75.6 % against the paper's 73 %. Solving on the paper's 73 % instead (V_airy = 1.73 × V_dense) gives β = 0.21 / 4.37 = 0.048, so the point is not sensitive to the rounding.
- **(c) popcorn and chips, from S13.1.**
  - The meal reductions are 698 − 15 − 716 = −33, 739 − 100 − 716 = −77 and 803 − 150 − 716 = −63 kcal. These agree with the abstract's compensation figures: 33/15 = 220 %, 77/100 = 77 % (the paper gives 76 %) and 63/150 = 42 %.
  - Solving 77/63 = (27 + 1392.5β)/(28 + 208.6β) gives β = 0.0063. Solving 33/63 = (4 + 232.6β)/(28 + 208.6β) gives β = 0.0865.
  - The SDs are about 280 kcal against differences of 63 to 77, which matches "about four times".
- **§ 5 table.** It re-derives except for two cells (defect R2).

### Readings stated as readings

§ 3 labels its estimates as readings of register values and not rows, and § 2 labels its physical reasoning. The exceptions are below.

### Report defects

**R1 (§ 1, the Nguyen paragraph): an unlabelled derived figure and the wrong arm.**

- Old text: "Popcorn gave less hunger. The meal after the snack fell by 77 kcal after popcorn and 63 kcal after chips, against control."
- Replace with: "Six cups of popcorn gave less hunger than every other condition. Read from the combined intakes minus each snack's energy (a reading, not reported as such), the meal after the snack fell by 77 kcal after 6 cups of popcorn and 63 kcal after chips, against control."

**R2 (§ 5 table): two rounding errors.**

- Broccoli at β 0.15: 1000 + 0.15 × 516.6 = 1077.49, so 1078 should read **1077**.
- Bolognese at β 0.7: V = 540 × 236.588 / 246 = 519.34, so fill = 525.54, and 525 should read **526**.
- The bolognese error comes from using the rounded V of 519.

**R3 (§ 4, the source paragraph): "mostly 9999" is wrong.** All 14449 rows carry `measure_unit_id` 9999.

- Old text: "(mostly 9999, "undetermined", so the unit lives in the modifier text)"
- Replace with: "(9999, "undetermined", on every one of the 14449 rows, so the unit lives in the modifier text)"

**R4 (§ 3 recommendation and § 5): the mod's own broccoli item is raw, and that is not stated.**

- The worked example is the cooked id 169967 (boiled and drained, not steamed) at 1.52 mL/g. But `Base.Broccoli` maps to raw broccoli 170379, where 1 cup chopped = 91 g, or 2.60 mL/g. Only `Base.CannedBroccoli` maps to 169967.
- At β 0.05, 1 kg of raw broccoli reads 1080. At 0.15 it reads 1240, which is 24 % above its weight.
- Fixes:
  - § 5's first row label "1 kg steamed broccoli (169967)" becomes "1 kg boiled broccoli (169967, the mod's CannedBroccoli)".
  - Add a row: `| 1 kg raw broccoli, the mod's Broccoli (170379) | 1000 | 2.600 (1 cup chopped = 91 g) | 2600 | 1080 | 1240 | 2120 |`.
  - In § 3, the bullet "β will not make broccoli fill much more. Cooked broccoli has only 0.52 mL/g of excess volume…" gains this closing sentence: "Raw chopped broccoli, which the mod's Broccoli item maps to, has 1.60 mL/g of excess and gains 8 % at β = 0.05."

### Notes (no change required)

- In § 1, "A stable foam stays there longer" rests on Murray 2015's abstract ("slower decrease in the total gastric content (P < 0.05)"). S1485's cells carry only the appetite time. The sentence is true of the source, but S1485 does not carry it.
- Rolls 2025 (Appetite 213:108036, pmid 40324693) is a pooled analysis of 13 preloading studies. In it, energy compensation fell with preload weight (p < 0.0001). It would add to § 1's "Weight is the basis" if a further row is wanted.
