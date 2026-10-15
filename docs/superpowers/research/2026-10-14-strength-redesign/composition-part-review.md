# Review of composition-part.tsv (S10.1-S10.10)

Model: claude-opus-5-5. Reviewed 2026-10-15, read-only. Every PMID was resolved on Europe PMC (core record), and in each case the title, authors, year, journal, volume, pages and DOI matched the row: 31897524, 42319968, 22238392, 23906445, 37837581, 27002421 (Blonde, in the S10.5 range), 23850055 (Cefalu, S10.6), 24447775, 17075583 and 27804272. Values were re-read in the abstracts, and in the open full text for McCrimmon 2020 (PMC6997246, Tables 1-2), Jobanputra 2026 (PMC13282017, section 3.8), Jahangiri 2023 (PMC10597985, Tables 2-3), Heymsfield 2014 (PMC3970209) and Polidori 2016 (PMC5108589, Tables 1-2). Bolinder 2012 and 2014 and Chaston 2007 are paywalled, so their values were checked against their abstracts, and the Bolinder figures also against Jahangiri Table 3.

`python tools/science_check.py --part .superpowers/sdd/strength-research/composition-part.tsv` reports 0 findings.

**Verdict: FAIL.** The citations are clean and no number is absent from its record. The defects are of four kinds:
- harvester arithmetic in a cell: the fat-share divisions in S10.1-S10.5 and the S10.8 complement;
- a duplicate of an existing register row: S10.7 duplicates S2051, and S10.9's exercise clause duplicates S2052;
- a between-arm mean difference written as a change (S10.2);
- one secondary reading missed (S10.6) and one inference stated as fact (S10.10).

## Duplicates against science.tsv

- 10.1111/obr.12143 (Heymsfield 2014) is already cited by S2051 and S2052.
  - S2051 has the same parameter as S10.7: the Quarter FFM Rule, its 0.25, the Webster regression 15.5 + 1.28 and the 22/78 split. S10.7 as filed is a duplicate. The fix narrows it to the readings S2051 lacks.
  - S2052 already carries Chaston's three pooled trials (0.27 +/- 0.06, 0.13 +/- 0.04, 0.17 +/- 0.14). The S10.9 fix drops that clause.
  - S10.8, the Forbes curve, is a distinct parameter, so it stays and names S2051 in its range.
- 10.1002/oby.21653 (Polidori 2016) is already S1254, the ~100 kcal/day per kg effect, graded COH. S10.10's parameter, the model's composition assumptions and fitted constant, is distinct, so it stays, graded MODEL, and names S1254.
- No other DOI or PMID in the part is in the register.

## Verdicts

- **S10.1 FIX.** All the numbers are in the record. Table 2 prints the changes as -2.62 (0.45) and -1.48 (0.28), which the text rounds. Each is an ANCOVA change adjusted to the pooled baseline. The fat share 2.6/4.1 = 0.63 is harvester arithmetic; with the table's precision it would be 0.64. The division belongs in the report.
  - value: `total fat mass -2.62 kg (SE 0.45) and total lean mass -1.48 kg (SE 0.28) at week 52 with canagliflozin 300 mg (Table 2; ANCOVA estimates adjusted to the pooled baseline); total fat plus lean mass -4.1 kg (post hoc)`
- **S10.2 FIX.** The 21 % (95 % CI 9-33 %, I2 41.8 %), 31 % and 28 % (22-34 %) figures, the 33 studies and the intervention-arm-only definition are in section 3.8. Two defects:
  - The -1.04 kg is the pooled mean difference against placebo or an active comparator, with I2 19 %. It is not the arm's mean change.
  - The complement 0.79 is harvester arithmetic in the value cell. LBM excludes bone, so the remainder is not all fat in any case.
  - The methods list also includes hydrostatic weighing and skinfolds.
  - value: `21 % of overall weight loss was lean body mass under SGLT2 inhibitors (31 % under GLP-1 receptor agonists; 28 % across both classes)`
  - range: `SGLT2 inhibitors 95 % CI 9 % to 33 %, I2 = 41.8 %; both classes 95 % CI 22 % to 34 %, I2 = 47.4 %; 33 studies in the proportion analysis across both classes (intervention arms only, change in lean mass divided by change in weight); lean measured as FFM, LBM (FFM minus bone) or skeletal muscle mass by DXA, BIA, MRI, ADP, hydrostatic weighing or skinfolds; SGLT2i LBM mean difference against comparator -1.04 kg (95 % CI -1.45 to -0.64, I2 = 19 %, 15 studies)`
- **S10.3 FIX.** The numbers match the abstract exactly, but the fat share 1.48/2.08 = 0.71 is harvester arithmetic.
  - value: `placebo-corrected change at week 24: total body weight -2.08 kg, DXA total fat mass -1.48 kg`
- **S10.4 FIX.** The -4.54 and -2.80 kg match the abstract. Jahangiri Table 3 lists them as the dapagliflozin group's own changes, with fat-free mass -1.30 kg, which confirms the within-arm reading. The fat share 2.80/4.54 = 0.62 is harvester arithmetic.
  - value: `dapagliflozin arm change over 102 weeks: weight -4.54 kg, DXA fat mass -2.80 kg`
- **S10.5 FIX.** Table 3 row 3 and the "approximately 37%" sentence match the record, as do n 63/73 and BMI 30.9/31.6 from Table 2. Two defects:
  - The 0.68 and 0.67 are harvester arithmetic.
  - The Table 3 values are the canagliflozin arms' own changes (marked * against placebo), not placebo-corrected. The range should say so.
  - Note for the report: in this table fat plus fat-free mass (2.8 and 3.6 kg) exceeds the weight change (2.5 and 3.2 kg). Fat over weight would be 0.76 and 0.75, not 0.68 and 0.67; see the report notes below.
  - value: `100 mg: weight -2.5 kg, fat mass -1.9 kg, fat-free mass -0.9 kg; 300 mg: weight -3.2 kg, fat mass -2.4 kg, fat-free mass -1.2 kg (review Table 3, changes within the canagliflozin arms at week 26); the review states the proportional loss of fat-free mass was consistent at approximately 37 %`
  - range: `secondary tabulation: the primary (Blonde 2016, Postgrad Med 128:371-380, doi:10.1080/00325481.2016.1169894, pmid:27002421) is paywalled and its abstract gives no numbers; the review labels the substudy CANTATA-SU in its text but tabulates the older-adult study (n = 63 and 73, baseline BMI 30.9 and 31.6); within-arm changes, each marked significant against placebo; the tabulated fat plus fat-free change exceeds the weight change`
- **S10.6 FIX (stays open).** The harvester missed a secondary reading. Jahangiri 2023 Table 3 row 12 tabulates Cefalu 2013 (CANTATA-SU) DXA at 52 weeks:
  - canagliflozin 100 / 300 mg: baseline weight 84.4 / 85.9 kg, weight change -4.4 / -4.2 kg;
  - baseline fat mass 28.2 / 29.3 kg, fat-mass change "NR";
  - baseline fat-free mass 47.7 / 44.6 kg, fat-free-mass change -0.9 / -1.1 kg.

  The fat change is not reported, and the baseline columns do not add up (28.2 + 47.7 = 75.9 against 84.4 kg). The row therefore stays open, but it names the reading.
  - population: `the primary (Lancet 382:941-950, doi:10.1016/S0140-6736(13)60683-2, pmid:23850055) is paywalled and its abstract carries no body-composition number; a secondary table (Jahangiri 2023, Diabetes Ther 14:2015-2030, Table 3, pmid:37837581) gives canagliflozin 100 / 300 mg at 52 weeks weight -4.4 / -4.2 kg and fat-free mass -0.9 / -1.1 kg but the fat-mass change as NR, and its baseline columns do not sum to body weight; the manufacturer medical-information page states about 2/3 of the loss was fat and about 1/3 lean across two phase 3 DXA studies, citing a 2012 congress abstract (Toubro) with no resolvable record`
- **S10.7 FIX (duplicate of S2051).** S2051 already holds the rule, its 0.25 and its Webster origin. The new content is the review's cross-sectional estimates and the Keys-Brozek ratios. The phrase "no firm theoretical basis" is not the review's; the Conclusions say the rule "is at best an approximation that has a limited mechanistic basis". The review also gives Webster's women as aged 14-60 and ranging widely in adiposity, not as obese women.
  - parameter: `cross-sectional estimates of the fat-free share of a weight change against the Quarter FFM Rule (S2051 carries the rule and its origin)`
  - value: `taking the mid-range slopes of the NHANES-based Thomas FFM-fat relations gives dFFM/dW of 0.37 for men and 0.32 for women, with no race differences; the Webster excess-weight approach applied to the same relations gives 0.36 and 0.31; Keys, Brozek and Grande's three obesity-tissue approaches gave 0.36, 0.36 and 0.27; the review concludes the Quarter FFM Rule "is at best an approximation that has a limited mechanistic basis"`
  - range: `predicted fractions for weight change within the mid-range of the functions, assuming the body remodels as cross-sectional data predict; not measured longitudinal losses; same record as S2051`
  - population: `adult (age >= 18 y) NHANES men and women with DXA body composition (Thomas model), as restated in a critical narrative review`
- **S10.8 FIX.** Equations 1 and 2 match. "fitted to stratified group mean data" and "a cross-sectional sample of relatively young women" match. Two defects:
  - "applies to modest changes about the starting fat mass" is not in this record. It is Polidori 2016's wording, in S10.10.
  - The complement FM/(10.4 + FM) is harvester algebra in the value cell.
  - value: `FFM = 10.4 ln(fat mass) + 14.2 (kg); differentiated, dFFM/dW = 10.4/(10.4 + fat mass); the larger the fat mass the smaller the fat-free share`
  - range: `fitted to stratified group means of a cross-sectional sample of relatively young women within a specified height range; the review notes longitudinal studies support the cross-sectional remodelling assumption, with the proviso that very large weight excursions are rarely reported with careful body-composition methods; extends S0054 and S0055 (direction only)`
- **S10.9 FIX.** Every number is in Heymsfield's text, and Chaston's abstract confirms the 26 cohorts, r2 = 0.31 and P = 0.006. Two defects:
  - The three-trial exercise clause duplicates S2052, so it is dropped.
  - Under the S2052 precedent, a row resting on a systematic review with pooled data (Chaston) beside a narrative review takes the left-most grade, `MA`.
  - value: `dFFM/dW 27 +/- 7 % in men and 20 +/- 7 % in women (P = 0.08); the share rose with the degree of caloric restriction (r2 = 0.31, P = 0.006), with no additional variance explained by initial BMI, magnitude of weight loss, sex or reported exercise`
  - range: `26 dietary and behavioural cohorts losing more than 10 kg, fixed-effect pooling; the sex means are Heymsfield 2014's reading of Chaston 2007 (the Chaston abstract gives the restriction association, not the sex means); the exercise trials are S2052`
  - grade: `MA`
- **S10.10 FIX.** The α definition, C = 10.4 kg, FM fixed at FM0, ρ_FM 9300, ρ_FFM 1100 and β 0.24 (Table 1), k_P = 95 kcal/day per kg, and the Table 2 population (153 vs 89; 57 % women; 55 ± 11 y; 87 ± 21 kg; BMI 32 ± 6) all match. Two defects:
  - "initial fat mass per subject estimated by the model from baseline characteristics" is not stated. The paper says only that it used "measured body weight, BW, and baseline patient characteristics", and it does not say how FM0 was obtained.
  - The paper restricts its analysis to the group mean.
  - range: `no CI given for k_P; fitted to the group-mean weight and intake course (the analysis was restricted to the group mean because UGE was assumed, ~90 g/day, not measured per subject); how FM0 was obtained is not stated and FM0 is not reported (the paper says it used baseline patient characteristics); same record as S1254, which carries the ~100 kcal/day effect`

## Report notes (composition-report.md)

1. **The S10.5 denominator.** The conversion divides by the fat share of weight lost, but the report uses fat/(fat + fat-free) = 0.67-0.68 for S10.5. The table's own weight change gives fat/weight = 1.9/2.5 = 0.76 and 2.4/3.2 = 0.75, in line with the review's "approximately 37 %" fat-free share. For S10.1 the two denominators nearly coincide (4.1 against 4.2 kg), so it is unaffected. The S10.5 line of the conversion table should read 0.75-0.76, giving 132-133 kcal/day per kg of fat.
2. **The CANTATA-SU reading weighs against 0.63.** The report says CANTATA-SU "could not be read", but Jahangiri Table 3 gives its 52-week fat-free share as 0.9/4.4 and 1.1/4.2 of weight. That is 0.20 and 0.26, a fat share by complement of about 0.74-0.80, with the caveat that the table is internally inconsistent. With S10.5 corrected to 0.75-0.76, McCrimmon's 0.63-0.64 is the low outlier among the canagliflozin readings, not their centre. The recommendation of 0.63 and 160 kcal/day should name that. The canagliflozin readings span 0.63-0.80 (about 125-160 kcal/day per kg of fat), and the Forbes and quarter-rule value of 0.75-0.76 sits in the middle of that span.
3. **The quarter-rule wording.** The phrase "finds no firm theoretical basis" should read "a limited mechanistic basis" (the review's Conclusions).
4. **The fluid inference.** The claim that DXA "lean" loss includes osmotic-diuresis water is harvester inference with no row behind it. It should be labelled as inference where it is used to discount the 0.63.
5. **The duplicates.** The § 2 bullets for S10.7 and S10.9 should name S2051 and S2052 as the rows already holding the quarter rule and the exercise trials.
