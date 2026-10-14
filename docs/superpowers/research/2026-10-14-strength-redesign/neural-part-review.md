# Review of neural-part.tsv (S6.1-S6.52)

Reviewer model: claude-opus-5-5. All 51 PMIDs were resolved through PubMed efetch (title, first author, year, journal, DOI matched for every settled row). Full texts read: PMC12296774 (Saeterbakken 2025, the sub-group SMDs and the 2.2-2.6 ratio are the authors' own, Discussion) and PMC7191505 (Maden-Wilkinson 2020, Results). Duplicate check run by PMID and DOI against docs/reference/science.tsv (S0001-S2089) and lean-science, hypertrophy-science, review-science, advanced-recomp and surplus part files. `python tools/science_check.py --part neural-part.tsv`: 0 findings.

Transfer rows (S6.1, S6.2, S6.7): S6.1 and S6.2 are within-group changes on two tests in the same people (a between-test contrast, read correctly; no arm contrast is claimed). S6.7 is a true between-arm contrast (TEST vs HYPER, 90 % CIs as published), read correctly. The 4-yr rows (S6.31-S6.34) hold no harvester height adjustment: the height and moment-arm statements in S6.32 are the paper's own (PMC Results).

## Verdicts

- S6.1 FIX `range`: n = 32 across three 12-wk programmes; the contralateral leg was the control in the isometric programme only, with no control in the two lifting programmes; the authors attribute most of the lifting gain to coordination of stabilising muscle groups
  (the abstract names the contralateral leg as a control in Study 1, so "no external control group" understated it)
- S6.2 PASS
- S6.3 PASS
- S6.4 PASS (untrained 1.27/0.58, trained 0.75/0.29, multi-joint 0.33, single-joint 0.70 and the ratio 2.2-2.6 all read in the PMC Discussion)
- S6.5 PASS
- S6.6 FIX `population`: trainees in the included studies, which tested back squat, deadlift or power clean 1RM against the isometric mid-thigh pull or squat; the authors apply the findings to athlete populations
  ("mostly resistance-trained athletes" is not in the record)
- S6.7 PASS
- S6.8 PASS
- S6.9 PASS
- S6.10 PASS
- S6.11 PASS
- S6.12 PASS
- S6.13 PASS
- S6.14 PASS
- S6.15 PASS
- S6.16 PASS
- S6.17 PASS
- S6.18 PASS
- S6.19 PASS
- S6.20 PASS
- S6.21 PASS
- S6.22 PASS
- S6.23 PASS
- S6.24 PASS
- S6.25 PASS
- S6.26 PASS
- S6.27 PASS
- S6.28 PASS
- S6.29 PASS
- S6.30 PASS
- S6.31 FIX `value`: MVT: 4 yr +60 % vs untrained and +39 % vs 12 wk; 12 wk +15 % vs untrained; quadriceps ACSAmax 4 yr +50 % vs untrained and +42 % vs 12 wk; agonist EMG at MVT +44 % (4 yr) and +33 % (12 wk) vs untrained, not different between trained groups; antagonist EMG at the highest common torque -69 % in 4 yr vs untrained (ES 1.18); torque-antagonist EMG slope lower with longer training (4 yr < 12 wk < untrained; 0.001 < P <= 0.094, ES 0.56-1.31)
  (the slope ordering is not significant across all pairs; the record gives P up to 0.094)
- S6.32 FIX (duplicate record of minted S0648, Maden-Wilkinson 2020, which already carries MVT +60 %, volume +56 %, PCSA +41 %, specific tension +9 %, moment arm +4 % and fascicle length +11 %; narrowed to what S0648 lacks)
  - `parameter`: body size, absolute torque, specific tension and the single predictor of knee-extensor strength in 4-yr trained vs untrained men (the percentage differences in torque, volume, PCSA and fascicle length are S0648)
  - `value`: trained group taller and heavier (183 +/- 6 vs 176 +/- 2 cm; 91 +/- 10 vs 73 +/- 10 kg); MVT 388 +/- 70 vs 245 +/- 43 N.m; maximal voluntary specific tension 36.1 +/- 5.3 vs 33.3 +/- 4.5 N/cm2 (+8 % in the results, P = 0.04; +9 % in the abstract, as S0648 carries); patellar-tendon moment arm +4 %, not different once normalised to height (P = 0.92); quadriceps volume alone explained MVT in stepwise regression (R2 = 0.81)
  - (the original cell also listed 33.3 vs 36.1 in untrained-first order beside 388 vs 245 in trained-first order; the new cell is trained-first throughout)
- S6.33 PASS
- S6.34 PASS
- S6.35 PASS
- S6.36 PASS
- S6.37 PASS
- S6.38 PASS
- S6.39 PASS
- S6.40 PASS
- S6.41 PASS (open; both records resolve, no abstract)
- S6.42 FIX `value`: baseline across the whole drug-tested dataset b = 0.55 (males), 0.50 (females); decays to 0.47 (males) and 0.41 (females) at the all-time top-20 level
  (the record's "general population baselines" means the whole lifter dataset, not untrained people; the row's "general-population baseline" reads as non-lifters)
- S6.43 PASS
- S6.44 FIX
  - `population`: 468 men and women aged 18-88 y, a heterogeneous sample
  - `range`: n = 468, 18-88 y; whole-body MRI; whole-sample means across all ages, with relative SM falling from the third decade; skeletal muscle, not fat-free mass; an erratum (J Appl Physiol 116:1342, 2014; doi:10.1152/japplphysiol.zdg-1052-corr.2014) was not read
  (values 33.0 vs 21.0 kg and 38.4 vs 30.6 % confirmed in the abstract; the share is an all-age mean, not a young-adult value, and PubMed lists an erratum whose content could not be fetched)
- S6.45 PASS
- S6.46 FIX (overlaps minted S1938, the same Narici 1989 record with CSA +8.5 %, MVC +20.8 % and the detraining time course; narrowed to the neural readings)
  - `parameter`: neural activation (iEMG) of the trained and untrained legs over 60 days of training (the CSA and MVC time course through detraining is S1938)
  - `value`: trained leg iEMG +42.4 +/- 16.5 % (mean +/- SEM, p < 0.01) after 60 days beside CSA +8.5 % and MVC +20.8 % (S1938); untrained leg: no CSA change, iEMG +24.8 +/- 10 % and MVC +8.7 +/- 4.3 % (both NS)
- S6.47 PASS
- S6.48 PASS
- S6.49 FIX `value`: experiment A over 24 wk: 1RM +27 % (M) and +29 % (E) (experiment B: +29 % and +23 %); biceps femoris coactivation in the 1RM fell from 41 +/- 11 % to 32 +/- 9 % in the elderly (P < 0.05) in the first 8 wk; 3 wk detraining (experiment A): isometric force -6 % (M, P < 0.05), -4 % (E, NS); 24 wk detraining (experiment B): CSA fell, 1RM -6 % (M) and -4 % (E), isometric force -12 % (M) and -9 % (E)
  (the 1RM gains quoted were experiment A's only, while the 24-wk detraining numbers are experiment B's)
- S6.50 PASS
- S6.51 PASS (open)
- S6.52 PASS (open)

## Count
52 rows: 44 PASS, 8 FIX (S6.1, S6.6, S6.31, S6.32, S6.42, S6.44, S6.46, S6.49), 0 DROP.
