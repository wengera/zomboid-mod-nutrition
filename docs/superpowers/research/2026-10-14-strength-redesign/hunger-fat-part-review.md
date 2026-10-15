# Review of hunger-fat-part.tsv (S9.1-S9.26)

Model: claude-opus-5-5. Reviewed 2026-10-15, read-only. Every PMID was resolved by PubMed efetch (title, first author, year, journal, DOI all matched). Values were re-read in the abstracts, and in the full text for Kissileff 2012 (PMC3260066, Tables 1-3), Dulloo 2018 (PMC5945583), Germain 2014 (PMC5189928) and Buechel 2026 (PMC13202672, Tables 1-2).

Duplicates: S9.5 is the same record as S1617 (Kissileff 2012, pmid:22237063), and as filed it has the same parameter. The fix below narrows it to the size of the change from Tables 1-3, which S1617 says the abstract does not give. S9.23 is the same record as S2021 (Buechel 2026). Its parameter, energy intake, is distinct, so it stays and its range names S2021. S9.8-S9.10 (Dulloo 2018) are a review of the primary re-analysis S1616 (Dulloo 1997). They are not duplicates. None of the 26 rows duplicates a row in the other part files.

## Verdicts

- **S9.1** PASS.
- **S9.2** PASS.
- **S9.3** PASS.
- **S9.4** PASS.
- **S9.5** FIX. This row is the contrast the design rests on. As filed it gave three group means, and the report took the 18 mm from its own subtraction, although Table 3 prints the paired differences. The leptin-against-placebo arm was randomly assigned in a single-blind crossover, so the grade is RCT, as S1617 already has it. The reduced-weight against initial-weight contrast is not randomised: the initial period always came first.
  - parameter: `size of the satiation change at a stable weight 10 % below usual, placebo vs leptin replacement (Tables 1-3; S1617 carries the abstract's direction)`
  - value: `post-meal fullness on a 150-mm scale 110.8 (initial weight) vs 93.1 (reduced weight, placebo) vs 107.7 mm (reduced weight, leptin), SEM 6.9; paired differences placebo - initial -17.8 mm (SEM 7.3, P = 0.013), leptin - placebo +14.6 mm (SEM 7.3, P = 0.029), leptin - initial -3.1 mm (P = 0.675); pre-meal fullness 21.8 vs 16.1 vs 21.8 mm (placebo - initial -5.7, P = 0.174); test-meal intake 948.7 vs 924.1 vs 931.0 kcal (SEM 86.9), not different; fat mass 62.5 to 49.5 kg; leptin 57.0 vs 45.8 vs 61.4 ng/mL`
  - range: `inpatient, weight-maintaining liquid diet; the initial-weight period always came first, then 5 wk each of placebo or replacement-dose leptin, randomly assigned in a single-blind crossover with a 2-wk washout; ratings pooled over ad libitum and fixed meals (Tables 1-3); the reduced-weight vs initial contrast is not randomised`
  - grade: `RCT`
- **S9.6** PASS.
- **S9.7** PASS.
- **S9.8** PASS. Every clause is the review's own text: "despite the complete recovery of body weight and fat mass, hyperphagia still persisted for some time until the complete restoration of FFM", and the "memory" of the initial fat and FFM. The course is a single-group time course of n = 12 read off a figure, and the range says so.
  - A caution for the design: the primary re-analysis, S1616, has the hyperphagia correlating more strongly with fat recovery (r -0.6) than with FFM recovery (r -0.5). The lean drive is additional to the fat drive, not a replacement for it.
- **S9.9** PASS. The 25-29 % loss and the 4-5 kg Ranger overshoot are in the text.
- **S9.10** PASS.
- **S9.11** PASS.
- **S9.12** FIX. The abstract does not say the data are from baseline.
  - parameter: `association of fat-free mass, fat mass and BMI with meal size and daily energy intake in obese adults (the level of fat does not predict intake)`
  - range: `objectively measured laboratory intake within a 12-wk intervention; the abstract does not name the time point`
- **S9.13** PASS.
- **S9.14** PASS.
- **S9.15** PASS.
- **S9.16** FIX. The citation lacks the volume and pages, which are now issued.
  - citation: `Alruwaili A, Trotman H, Haenebalcke L et al 2026, Int J Obes (Lond) 50:1945-1952; doi:10.1038/s41366-026-02115-1; pmid:42230984`
- **S9.17** PASS. "Similar" is the abstract's word for a non-significant difference between groups of 7.
- **S9.18** FIX. The abstract says leptin was "significantly lower in AN subjects", not "only" in them. "Only" adds an inference the abstract does not state.
  - value: `PYY higher in constitutional thinness than in anorexia nervosa or controls; ghrelin lowest in constitutional thinness and highest in anorexia nervosa; leptin significantly lower in anorexia nervosa; leptin and PYY circadian profiles in constitutional thinness not different from controls, blunted in anorexia nervosa`
- **S9.19** FIX. Two problems:
  - The row read a within-group change as a contrast. "REE rose in the thin group only" is a significant change from baseline in one group and a non-significant one in the other, with no between-group test in the abstract.
  - "(P = 0.26)" was not labelled as against baseline. The +2640 kJ is per day (630 kcal/d; full text).
  - value: `+2640 kJ/d (630 kcal/d) of fat for 4 wk: constitutionally thin women gained +0.22 +/- 0.18 kg (P = 0.26 vs baseline) vs controls +0.72 +/- 0.26 kg (P = 0.03 vs baseline; P = 0.01 between groups); after overfeeding fasting total and acylated ghrelin lower than in controls (P = 0.01 and 0.03) and post-meal PYY and GLP-1 responses earlier and higher; REE rose from baseline in the thin group (P = 0.031) and not significantly in controls, with no between-group test in the abstract`
- **S9.20** PASS.
- **S9.21** FIX. Three problems:
  - The P = 0.008 is a within-group condition contrast in the thin women, with no group-by-condition test.
  - The sessions were randomly ordered, so this is a controlled crossover and grades RCT. The group contrast itself is observational.
  - The abstract also reports that this sample's thin women were lower in fat percentage. That is the one direct "stable and lower-fat" reading in the constitutional-thinness set.
  - value: `no condition or group effect on hunger; within the thin group, ad libitum intake was lower after exercise with energy replacement than after rest (P = 0.008), with no group-by-condition test in the abstract; the thin women had lower fat mass percentage (P = 0.003) and fat-free mass (P < 0.001) than the normal-weight women`
  - range: `exploratory crossover of three randomly ordered sessions (rest, exercise, exercise with energy replacement); the thin vs normal-weight contrast is observational`
  - grade: `RCT`
- **S9.22** PASS. The within-group changes stand beside the controls' null, as the abstract gives them.
- **S9.23** FIX. Every number checks against Table 2 and the text. The intake course, however, is a single-group change with no control, and the range does not carry what limits reading it as an appetite drive:
  - The refeeding was coached.
  - The instruments differ: a weighed diary before competition and an app after it.
  - The authors say some athletes may have entered T0 already partly restricted, with RMR below predicted.
  - range: `single-group observational, no control; DXA; intake by 7-day weighed diary before competition and by tracking app after it, with refeeding under coach or dietitian guidance; T0 RMR was below predicted and some athletes may have entered partially restricted; T1.5 n = 13, T4 n = 18; the body-composition changes are also S2021`
- **S9.24** PASS (open).
- **S9.25** PASS (open).
- **S9.26** PASS (open). Its pmid:37218855 is S2022's record.

## Notes on the report, not the cells

- The report's "about 18 mm (my subtraction)" should cite Table 3's -17.8 mm (P = 0.013) instead.
- S9.23 does not cleanly fit "hyperphagia until lean mass is restored". At 12 wk FFM was already +1.6 kg above baseline, yet intake stayed +10.3 kcal/kgFFM/d above it.

## Count

26 rows: 19 PASS (3 of them open), 7 FIX (S9.5, S9.12, S9.16, S9.18, S9.19, S9.21, S9.23), 0 DROP.
