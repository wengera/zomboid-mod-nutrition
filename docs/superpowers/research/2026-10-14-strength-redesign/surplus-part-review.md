# Review of surplus-part.tsv (S5.1-S5.30)

Reviewer: claude-opus-5-5, read-only, 2026-10-14. Every PMID was resolved through NCBI efetch (all 24: title, first author, year, journal and DOI match the citation cells). Full texts read: Helms 2023 (PMC10620361), Henselmans 2026 (PMC13305566), Iraki 2019 (PMC6680710), Aragon 2017 (PMC5470183), Slater 2019 (PMC6710320), Hall 2008 (PMC2376744, PMC page), Isola 2025 (PMC11829922), Barakat 2020 (Ovid full text, Tables 2-4; Crossref confirms 42(5):7-21, CC BY-NC-ND). All other rows were checked against the PubMed abstract. Barakat's DOI resolved through Crossref. Camera 2012's full text returned 403, so how the depleted leg was allocated was not checked.

## Verdicts

- **S5.1 FIX.** The Table 2 numbers, the targets (the ± 1 %, 0.4-0.6 % and 1.4-1.6 % per two weeks), MyFitnessPal with weekly check-ins, the inclusion strengths and the Discussion quote all match the record. No cell holds harvester arithmetic. The labels "5 %" and "15 %" are the paper's estimated surpluses, set by weight-gain targets. The paper reports no achieved percentage. The Discussion's "similar energy surplus" comes from the outcomes, not from the intakes, which differ (+489 vs +719 kcal/d). That needs saying.
  `range` → `self-reported intake (MyFitnessPal, weekly check-ins); n = 6 / 6 / 5 completers; 8 wk; full text (PMC10620361) Methods and Table 2; no achieved surplus is reported as a percentage of maintenance; the Discussion's "similar energy surplus" for MOD and HIGH is the authors' reading of the outcomes (body mass +3.3 +/- 0.8 and +3.3 +/- 1.5 kg, Table 1), not of Table 2's intakes`
- **S5.2 FIX.** Every Table 1 change and every Table 6 group BF10 matches the record. The range overstates a contradiction: Statistics says "means ± 95% credible interval ... unless otherwise specified", and Table 1 specifies SD.
  `range` → `no between-arm effect sizes or credible intervals are reported for any site (Bayes factors only); Table 1 is mean +/- SD (Statistics: means +/- 95 % CrI unless otherwise specified); no lean-mass measure; n = 6 / 5 / 6`
- **S5.3 FIX.** The record exists: Nutrients 2026 18(12):1961, PMID 42356347, PMC13305566, with all ten authors as cited. Every number matches Results 3.4.2 and 3.4.1 exactly:
  - lean mass 0.76 ± 0.45 (-0.19 to 1.69, p = 0.109), PRO -0.20 ± 0.33, CHO 0.55 ± 0.33;
  - fat mass 0.15 (-0.42 to 0.71);
  - elbow-flexor thickness 0.05 (-0.09 to 0.19);
  - lateral-thigh thickness 0.03 (-0.27 to 0.31);
  - vastus lateralis CSA -0.45 (-3.40 to 2.49);
  - squat 1RM 1.53 (-3.52 to 6.57).

  The SEMs (0.36 kg, 0.12 cm, 0.06 cm, 0.5 cm2), the supplements, the 14 and 18 sets, and the population figures (26.7 ± 4.9 y, 9.7 ± 6.1 y, squat 1.9 ± 0.4, BMI 26.7 ± 2.7) also match. The grade `RCT` is right, because science.md counts a controlled crossover as RCT. The one defect: the ± values are SE (Statistics: "Estimated marginal means (±SE)"), and the cell does not say so.
  `value` → `CHO minus PRO, estimated marginal means (+/- SE): DXA lean mass +0.76 +/- 0.45 kg (95 % CI -0.19 to 1.69; p = 0.109; PRO -0.20 +/- 0.33, CHO +0.55 +/- 0.33 kg); fat mass +0.15 kg (-0.42 to 0.71); elbow-flexor thickness +0.05 cm (-0.09 to 0.19); lateral-thigh thickness +0.03 cm (-0.27 to 0.31); vastus lateralis CSA -0.45 cm2 (-3.40 to 2.49); squat 1RM +1.53 kg (-3.52 to 6.57); no outcome differed, first-period sensitivity ANCOVAs included`
- **S5.4 PASS.** Table 1 (mean ± SD) and Results 3.2 match: 2751 ± 645 vs 2266 ± 672, 485 kcal/d (99 to 871, p = 0.017), +33 g (1 to 65), protein 178 ± 47 vs 173 ± 48, the 251 kcal/d Atwater quote, adherence 99.67 vs 90.49 %. Dietary data were missing for 4 participants (Limitations).
- **S5.5 FIX.** The values match the abstract. The population's "about 23-27 y" is the harvester's paraphrase of the two group means.
  `population` → `32 athletes (19 male, 13 female); group means 27 +/- 7 y (peanut) and 23 +/- 3 y (carbohydrate)`
- **S5.6 FIX.** The values match the abstract. Lean mass and RMR are pooled-sample readings (N = 24), not a contrast between arms, and the cell does not say so.
  `range` → `abstract; 12 wk, 3 sessions/wk; arms: 33 g whey protein/day vs one fast-food meal a day (1350 kcal, 41 g protein); body weight, lean mass and RMR are pooled over both arms (N = 24), the abstract gives no per-arm lean mass and states the between-arm equality only in its conclusion; 12-month follow-up n = 19 back to baseline`
- **S5.7 PASS.** Iraki's full text matches: 1.7 vs 1.2 kg LBM, fat mass 1.1 vs 0.2 kg, and the 200-300 kcal quote. `TXT` is right for a secondary report. S1944 is the Garthe abstract reading, so this row is not a duplicate.
- **S5.8 PASS.** Both quotes and the Garthe intakes (3585 kcal, +544; 2964 kcal, -128) match Aragon's full text.
- **S5.9 PASS.** The composition, the 5,000-5,200 kJ, the 7,440 and 6,050 kJ/kg, the 29.4 kJ/g, the 3.6 kJ/g and the "not aware" sentence all match the full text.
- **S5.10 FIX.** The textbook clause drops the record's referent ("required to gain 1 kg of SMM") and one of its conditions ("or during heavy training loads").
  `value` → `"practitioners are advised to start conservatively with an energy surplus within the range of ~1,500-2,000 kJ/day and closely monitor response"; common textbook recommendations for the energy surplus required to gain 1 kg of skeletal muscle mass range from about 1,500-2,000 kJ/day in weight-stable athletes to an additional 4,000 kJ/day in those who struggle with lean mass gains or during heavy training loads`
- **S5.11 PASS.** All values match the full text: 17.6, 19.7 and 39.5 MJ/kg; h = 1.6, giving rho_L = 7.6; 3.8 giving 4; 2.8 giving 5.6; rho_F = 39.5. **Controller note:** this row answers the open row S0126 ("energy densities of fat tissue and lean tissue as explicit coefficients", only the 32.2 MJ/kg rule verified). Settle S0126 with these cells, or supersede S0126 with this row as its successor, rather than minting beside it.
- **S5.12 PASS.** All values match the abstract (28 kJ/g; 33.7 kJ/g; 43.6 % and 38.4 %; r 0.77 and 0.49; 33.8 kJ/g; 13 + 2 subjects plus 28 + 5 from the literature).
- **S5.13 PASS.** The values match the abstract. It is a declared different reading of S0055.
- **S5.14 PASS.**
- **S5.15 FIX.** The abstract calls postabsorptive leucine flux an index of proteolysis, and the synthesis index depends on an assumption about 13CO2 recovery. The cell gives neither.
  `value` → `with 1,600 extra kcal/day of carbohydrate, total urinary nitrogen fell 27 % vs 10 days of weight maintenance (protein accretion), postabsorptive nitrogen excretion unchanged; postabsorptive leucine flux (an index of proteolysis) +13 +/- 2 %; flux minus oxidation (a theoretical index of protein synthesis, assuming unchanged 13CO2 recovery) +12 +/- 3 %; insulin, glucagon and T3 about +20 %`
- **S5.16 PASS.**
- **S5.17 PASS.** The values match the abstract; the abstract itself prints p = 0.71.
- **S5.18 FIX.** The abstract says "healthy subjects" and gives no age.
  `population` → `healthy subjects (the abstract gives no age)`
- **S5.19 PASS.** The values match the abstract. `EXP` is defensible: nutrient vs placebo was randomised, but the row's glycogen contrast is within subject (one leg depleted against the rested leg), and its allocation was not checked.
- **S5.20 PASS.**
- **S5.21 FIX.** The record is "a systematic review", and science.md grades a systematic review `MA`.
  `grade` → `MA`
- **S5.22 PASS.** Every Table 2 and Table 3 entry matches the Ovid full text, including the Haun and Slater quotes. **Controller note:** the row states it settles S2047. Apply it as `settle S2047` (and drop "(settles S2047)" from the parameter), or supersede S2047 with this row as successor, so the gap does not stay open beside its answer.
- **S5.23 PASS.** Every Table 4 entry matches, and the Rossow cell matches as printed. **Controller note:** S2048 also names Schoenfeld 2020, which this row does not cover, so S2048 stays open and its bound should name S5.23 for Rossow and Pardue.
- **S5.24 PASS.**
- **S5.25 FIX.** The population has no n and no age.
  `population` → `12 male junior sumo wrestlers from a local club, 15 +/- 1 y, Japan`
- **S5.26 PASS.**
- **S5.27 FIX.** The energy-availability values, the male-control rise and the male-COMP correlation match the full text. The population has no group sizes.
  `population` → `drug-free physique athletes, Finland: 10 female and 13 male competitors, 10 female and 10 male non-dieting controls`
- **S5.28 PASS** (open row). It is not a duplicate: S1942 holds the abstract reading of the same record.
- **S5.29 PASS** (open row).
- **S5.30 PASS** (open row).

## Duplicates

There are no duplicate rows against science.tsv or the four other part files. Helms 2023 (S1943, S2033), Garthe 2013 (S1944), Iraki 2019 (S1946, S2060), Slater 2019 (S1947), Hall 2008 (S0051-S0053), Forbes 2000 (S0055) and Murphy 2022 (S1942) are each read here for different values.

## Count

30 rows: 19 PASS, 11 FIX (S5.1, S5.2, S5.3, S5.5, S5.6, S5.10, S5.15, S5.18, S5.21, S5.25, S5.27), 0 DROP. There are three controller notes on open rows: S0126 (answered by S5.11), S2047 (S5.22) and S2048 (S5.23).
