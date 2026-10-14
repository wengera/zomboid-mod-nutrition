# Pre-mint citation review: advanced-recomp-part.tsv

Reviewer model: claude-opus-5-5. Each record was resolved by PubMed efetch (title, first author, author count, year, journal, volume, pages, DOI). Values were re-read against the abstract and, where the row cites full text, against the Europe PMC full text: Moro PMC5064803, Isola 2025 PMC11829922, Buechel PMC13202672, Schoenfeld PMC10204542, Hulmi PMC5222856, Chappell PMC8336548, Ribeiro PMC6942464, Helms PMC10620361, Smith PMC8167794, Antonio PMC4617900, Campbell PMC7739314 and the reply PMC7739255, and Robinson PMC4422265. Crossref was used for Barakat 2020 and for Hulmi's year.

Every citation resolved: the title matches, and so do the first author, year, journal, volume, pages and DOI or PMID. No row carries a number that is absent from its record. The defects found are harvester arithmetic placed in a cell, a within-group p read as a contrast, a misread error comparison, two population cells, a grade, and one duplicate.

## Verdicts

- **S3.1** FIX. The fat-mass kilograms are harvester arithmetic: the paper prints only the pre and post means and the % changes. The FFMI is also computed here, and the kcal figures are the baseline intakes.
  - `value`: `DXA FFM 73.08 +/- 3.88 to 73.72 +/- 4.27 kg (time-restricted) and 73.93 +/- 3.9 to 74.41 +/- 3.59 kg (normal), both n.s. (+0.86 vs +0.64 %); fat mass 10.90 +/- 3.51 to 9.28 +/- 2.47 kg in the time-restricted arm (p = 0.0005; -16.4 %) and 11.36 +/- 4.5 to 11.05 +/- 4.274 kg n.s. in the normal arm (-2.8 %), time x diet p = 0.0448; anthropometric arm and thigh muscle area n.s. in both; bench and leg-press 1RM n.s.`
  - `range`: `8 wk; n = 17 + 17; 100 % of estimated energy needs, baseline intake 2826 +/- 412 vs 3007 +/- 445 kcal/d and 2735 +/- 386 vs 2910 +/- 376 kcal/d during the trial; protein about 1.9 g/kg/d; baseline FFM 73.1 +/- 5.7 and 73.9 +/- 3.9 kg at 178 +/- 5 and 177 +/- 4 cm (Table 1); values from the full text, Tables 1-3`
- **S3.2** PASS. The abstract matches. The clause "CTRL training background mirrored that of COMP" was confirmed verbatim in Isola 2025 (PMC11829922), Methods.
- **S3.3** PASS.
- **S3.4** PASS. The abstract intervals match. The full text confirms age 28.3 +/- 6.2 y, the drug-tested federations, Australia, and that DXA was skipped at T2 because of the ~2-3 % shifts. The "wet mass" reading is the Discussion's.
- **S3.5** PASS. Section 3.5 and the Discussion confirm -0.36, -0.42 and -0.28 kg/wk, BF 14.5 to 5.8 % and 21.3 to 13.1 %, the male average of 2.8 g/kg/d and the speculation about essential fat.
- **S3.6** FIX. The control training SD is 1.1, not 1.2 (Methods). "Some individuals gained lean mass" is the Results' Figure 2E statement and is restated precisely below. The year is left at 2017: Crossref gives 2017-01-10 and PubMed gives volume 7 as 2016. S1911 cites the same record as 2016, so the controller may align the two.
  - `value`: `DXA lean mass 47.6 +/- 4.1 to 48.0 +/- 3.9 kg (+1.1 +/- 3.1 %, n.s.); InBody lean mass -3.0 +/- 4.4 % (p < 0.01); skinfold FFM -3.9 +/- 2.7 % (p < 0.001); vastus lateralis CSA by panoramic ultrasound decreased slightly (p < 0.05), triceps thickness unchanged; a few dieters had a small lean-mass increase (mean of DXA and bioimpedance), most a decrease or no change`
  - `range`: `n = 27 diet vs 23 weight-stable controls; training experience 3.5 +/- 1.4 y (diet) and 3.1 +/- 1.1 y (controls); full text Table 3, Results and Figure 2E`
- **S3.7** PASS.
- **S3.8** PASS. The UK is confirmed by the affiliations.
- **S3.9** FIX. The implied-FFM clause is harvester arithmetic. The register forbids it in a cell, and the abstract gives no lean figure.
  - `value`: `body weight 88.6 to 73.3 kg; body fat 17.5 to 7.4 %; the abstract gives no lean or fat-free mass figure`
- **S3.10** FIX. The Results match the row: 9.0 +/- 3.3, 1.8 +/- 3.0 (20.9 %), 6.8 +/- 1.1, 7.5 +/- 1.9, 1.6 +/- 1.4, 43.7 and 32.0 %. The abstract prints different figures, and the row should name that discrepancy.
  - `range`: `n = 4 (3 male); multi-frequency BIA (InBody 720); full text Results and Discussion; the abstract prints the loss as 8.6 +/- 4.1 kg and the regain as 7.9 +/- 1.6 kg, the Results as given here`
- **S3.11** PASS.
- **S3.12** DROP. This duplicates S4.2 in `review-science-part.tsv`: the same record (Garthe 2011, pmid:21558571), the same abstract and the same numbers. S4.2's population cell is fuller. Keep S4.2 only.
- **S3.13** FIX. 21.4 +/- 4.0 y is the fast group's age only.
  - `population`: `23 elite athletes completing the 6- and 12-month follow-up (slow n = 14, 23.5 +/- 3.3 y; fast n = 9, 21.4 +/- 4.0 y), Norway`
- **S3.14** FIX. p = 0.006 is the continuous group's within-group change, but as written it reads as the between-group contrast. In the authors' reply, the FFM and RMR changes did not differ between groups and only dry FFM did. The record the range cites is the authors' reply, not the comment itself.
  - `value`: `FFM -0.4 kg (refeed, 60.1 to 59.7) vs -1.3 kg (continuous, 66.4 to 65.1; p = 0.006 for this within-group change); dry FFM -0.2 vs -1.9 kg; fat mass -2.8 vs -2.3 kg; the between-group difference held for dry FFM only, the FFM and RMR changes not differing significantly (authors' reply)`
  - `range`: `n = 13 + 14; 7 wk; 4 d/wk training; a letter's intention-to-treat reanalysis found only dry FFM differed, which the authors' reply accepted (Campbell BI 2020, J Funct Morphol Kinesiol 5:86; doi:10.3390/jfmk5040086; pmid:33467301)`
- **S3.15** FIX. The "cannot separate muscle from fat" clause is reviewer inference sitting in the value cell. It moves to the range, labelled as inference. The group p is printed as 0.03, and the body fat is % body fat (Table 3).
  - `value`: `estimated skeletal muscle mass +2.7 % (36.7 to 37.7 kg, 67.5 kcal/kg/d) vs +1.1 % (36.1 to 36.5 kg, 50.1 kcal/kg/d), group difference p = 0.03; body fat 16.2 to 17.4 % (+7.4 % relative) vs 13.3 to 13.4 % (+0.8 %)`
  - `range`: `n = 6 + 5; 4 wk; 6 d/wk training; protein 1.8 vs 2.0 g/kg/d; steroid abstinence required only for 3 months; muscle mass estimated with the Lee 2000 equation (SMM = 0.244 x body weight + 7.8 x height + 6.6 x sex - 0.098 x age + race - 3.3), so a body-weight gain raises the estimate by construction and the outcome cannot separate muscle from fat (inference here, not the authors'); full text Methods and Tables 1-3`
- **S3.16** FIX. Table 1 prints the skinfold sum in "cm", so the mm reading needs a note. The age "24-29 y" is the range of the group means, not the ages themselves. The training criterion is now spelled out.
  - `range`: `n = 6 (maintenance) / 6 (5 %) / 5 (15 %) completers of 21 (2 female); 8 wk; full text Table 1 (mean +/- SD; Table 1 labels the skinfold sum cm, the values being mm); the 5 % and 15 % groups gained the same body mass; baseline bench 1RM 98.4 +/- 22.8 kg and squat 1.80 x body mass`
  - `population`: `17 lifters (2 female) with >= 1 y of resistance training and a bench >= 1.0 x and squat >= 1.5 x body mass (men), group mean ages 24.3-28.8 y, New Zealand`
- **S3.17** PASS.
- **S3.18** FIX. This is a single-arm supervised overfeeding intervention, a non-randomised dosing experiment, consistent with S3.25. The values, including the ~78-122 posterior interval, and the inclusion criteria were confirmed in the full text.
  - `grade`: `EXP`
- **S3.19** PASS.
- **S3.20** PASS. Germany is confirmed by the affiliations.
- **S3.21** PASS. The full text confirms the Bod Pod, Table 28.0-35.7 kcal/kg/d, the hydration caveat and the self-report limitation.
- **S3.22** PASS.
- **S3.23** PASS. EXP is borderline because the session was self-chosen with ad libitum intake, but it is acceptable.
- **S3.24** FIX. The DXA-lower-error and MFBIA-lower-error split by subgroup is the abstract's finding for fat-mass and BF% change. For FFM change, the errors were similar in the fat-loss subgroup and MFBIA was lower in the gain-both subgroup.
  - `value`: `group changes did not differ between 4C, DXA and MFBIA; DXA and MFBIA were equivalent to 4C for FFM change in all analyses; for FFM change their errors were similar in the whole group and in the subgroup that lost fat while gaining FFM (MFBIA showing proportional bias), and MFBIA had lower error in the subgroup that gained both; for fat-mass and body-fat % change DXA had lower error in the fat-loss subgroup and MFBIA in the fat-gain subgroup`
- **S3.25** PASS.
- **S3.26** PASS. This is not a duplicate of S0599, which is a different Helms 2014 record (pmid:24092765).
- **S3.27** PASS.
- **S3.28** PASS.
- **S3.29** PASS (open).
- **S3.30** PASS (open). Crossref confirms the title, Barakat, 2020, 42:7-21 and the DOI. This is the open companion of H.48 (unverified) and does not duplicate it.
- **S3.31** PASS (open). Rossow 14.8 to 4.5 %, Pardue DXA 13.8 to 5.1 % and Schoenfeld 2020's qualitative lean loss were all confirmed in the abstracts.

## Duplicates checked

These records already appear in `science.tsv` or in the sibling part files:

- Hulmi 2016/2017 is S1911. S3.6 is marked as a different reading.
- Helms 2023 is S1.29. S3.16 is a different reading.
- Antonio 2015 is H.43. S3.21 is a different reading.
- Barakat is H.48. S3.30 is open.
- Garthe 2011a is S4.2. S3.12 is a true duplicate, dropped.

No other PMID in this part appears in the register or the sibling parts.

## Count

PASS 20 · FIX 10 (S3.1, S3.6, S3.9, S3.10, S3.13, S3.14, S3.15, S3.16, S3.18, S3.24) · DROP 1 (S3.12) · total 31.
