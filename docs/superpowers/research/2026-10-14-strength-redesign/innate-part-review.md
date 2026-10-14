# innate-part.tsv review (pre-mint, read-only)

Reviewer: claude-opus-5-5, 2026-10-14. All 28 settled citations resolved through PubMed efetch (title, first author, year, journal, DOI and PMID matched for every row). Full text read from Europe PMC for PMC7966212 (S7.4) and PMC6691166 (S7.9, S7.28); the O'Brien 2010, Zempo 2017, Silventoinen 2008, Arden 1997 and Tiainen 2004/2008 records have no open full text, so those rows are held to their abstracts.
Duplicates: no PMID or DOI in this part appears in docs/reference/science.tsv (S1915-S2141 included) or in lean-science, hypertrophy-science, review-science, advanced-recomp, surplus or neural parts. S7.9 and S7.28 share Trezise 2019 with different parameters (allowed). The open rows S7.29-S7.31 are distinct from S2130, S2140 and S2141.
Harvester arithmetic: none of the report's derived figures (CV 11.3 %, residual SD 5-12 %, 12.1/10.8/5.3 %, VA CV 7.6 %, 17.6 %, sigma_res) sits in any cell. The heritabilities S7.21-S7.25 are read as the records state them: only S7.21 (Reed 1991) is size-adjusted, and it says so from the record (anthropometric adjustment); none of the others claims adjustment.

## Verdicts

- S7.1 PASS
- S7.2 PASS
- S7.3 FIX range: `20 adults and 20 children of both sexes; tendon force corrected for EMG-estimated antagonist coactivation, interpolated-twitch activation and MRI moment arm; PCSA from MRI volume over ultrasound fascicle length; abstract only`
  (the clause "absolute values higher than other laboratories report (method-dependent)" is not in the record read; the full text is not open)
- S7.4 FIX range: `n = 53; MRI volume; no systematic training in the prior 18 months; numbers read from the PMC full text (PMC7966212), Results and Table 1; the paper does not report a correlation of MVT with quadriceps volume`
  (the old "reports no within-group MVT-volume correlation" reads as a null finding; the paper simply does not report one. All value numbers confirmed: MVT 247 +/- 43, 173-396, CVb 17 %; Table 1 volume, ACSAmax, effective PCSA and moment arm with their CVb; age 25 +/- 2 y)
- S7.5 FIX population: `men: 26 measured by MRI, then 160 university students and 99 athletes`
  ("Japanese" is not in the record)
- S7.6 FIX range: `n = 19, men and women pooled; isometric moment at 90 deg knee angle; abstract only`
  ("the sex difference inflates R2" is harvester inference, not in the record)
- S7.7 PASS
- S7.8 PASS
- S7.9 FIX value: `%VA 88.51 +/- 6.71 % before and 92.00 +/- 4.99 % after 10 wk of 6-RM lower-limb training (mean percent change +4.1 +/- 3.6 %, P <= 0.01); isometric torque 256.4 +/- 69.1 N.m before and 296.8 +/- 74.3 after (mean percent change +17.2 +/- 12.6 %)`
  (Table 1 gives 4.1 +/- 3.6 in its percent-change column, not as percentage points; the other numbers confirmed)
- S7.10 PASS
- S7.11 FIX population: `5 subjects, elbow flexors`
  ("healthy adults" is not in the record)
- S7.12 FIX grade: `COH`
  (an in vitro characterisation of fibres by MHC type is a cross-sectional observation, not a controlled dosing or depletion experiment)
- S7.13 PASS
- S7.14 FIX grade: `TXT`
  (a review summarising the authors' family and twin data, not an authority report)
- S7.15 FIX grade: `COH`; FIX range: `skinned type I and IIA fibres containing a single MHC isoform, 15 deg C; the spread is among fibres and the abstract does not split it by subject; abstract only`
  ("pooled across subjects" is inference; grade as S7.12)
- S7.16 PASS
- S7.17 PASS
- S7.18 FIX range: `25 MZ and 16 DZ pairs, the same sample size and age as Thomis 1997 (S7.17); abstract only`
  (that it is the same cohort is inference; the record does not say so)
- S7.19 PASS
- S7.20 PASS
- S7.21 PASS (the 65 % is the record's own adjusted estimate: weight, height, age and anthropometric fatness, muscle mass and frame size)
- S7.22 FIX range: `1582 MZ and 1864 same-sex DZ complete twin pairs plus 154970 full-brother pairs; measured in young adulthood; the 50-60 % are heritabilities of the strength measures themselves, not adjusted for body size, which enters only through the genetic correlations; the authors note twin samples may have inflated earlier heritability estimates through selective non-participation; abstract only`
  FIX population: `1139963 Swedish men measured in young adulthood, born 1951-1976`
  ("conscription" is not in the abstract)
- S7.23 FIX range: `24 articles, 58 measurements; I2 = 91.0 %; subgroup 95 % CIs: isometric grip 0.46-0.67, other isometric 0.47-0.52, isotonic 0.32-0.67, isokinetic 0.37-0.61, jumping 0.45-0.65; the abstract reports no adjustment for muscle size; abstract only`
  ("not adjusted for muscle size" stated as fact is not in the record; the CIs are)
- S7.24 PASS
- S7.25 PASS
- S7.26 PASS
- S7.27 PASS
- S7.28 FIX range: `n = 36, single-arm 10-wk 6-RM training with no control group; numbers read from the PMC full text (PMC6691166), Results and Discussion; "equally likely" is the authors' reading of the pre-post correlations, not a test of change against baseline strength; the 31 % and 14 % compare the range of the changes with the pre-training range (92.6 vs 297.1 N.m; 8.8 vs 63.4 cm2, proximal quadriceps CSA)`
  (all value numbers confirmed in the record; the ranking-persistence reading rests on r = 0.93/0.97/0.90, which the authors use to claim equal likelihood of gain, a claim their analysis does not test directly)
- S7.29 PASS (open)
- S7.30 PASS (open)
- S7.31 PASS (open)

## Count

31 rows: 18 PASS, 13 FIX, 0 DROP.
