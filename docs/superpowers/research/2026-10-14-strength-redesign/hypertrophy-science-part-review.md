# Review: hypertrophy-science-part.tsv (68 rows)

Reviewer model: claude-opus-5-5. Every PMID was fetched one record at a time through PubMed efetch, and its title, first author, year, journal, volume and pages matched the citation cell. The PMIDs are 60 unique, because H.1/H.2 and H.29/H.51 share records. Full texts were read where a cell depends on them: the Pelland SportRxiv preprint PDF (v2, last modified September 2024), and through Europe PMC/PMC Trommelen 2023 (PMC10772463), Räntilä 2025 (PMC12659766), Seaborne 2018 (PMC5789890), Murphy & Koehler 2020 (PMC8233264), Antonio 2015 (PMC4617900) and Serrano 2025 (PMC13188836). Barakat 2020 was resolved through Crossref. Duplicates were checked by PMID and author against `docs/reference/science.tsv` and the other three part files.

## Verdicts

- H.1 PASS. All numbers are confirmed in the preprint: §4.6.1 gives 35 studies, 220 effects, 1,032 participants, R2 22.3/73.3 % and slope 0.24 % [0.15, 0.33]. §5.4 gives the 12.25-set mean and says few studies go above about 25 sets. Table 2A gives the tiers, and SDES is 2.05 %. Population 79.1 % male and 25.16 y come from the published abstract, and 28 untrained and 39 trained studies come from preprint §4.3. Overlaps S0577 (the qualitative reading of the same record) but adds the numeric reading, so it is not a duplicate.
- H.2 PASS. Preprint §4.6.2 gives 66 studies, 490 effects, 2,020 participants, R2 marginal 26.1 % and slope 0.21 % [0.16, 0.26]. Table 2B gives the tiers, and SDES is 3.96 %.
- H.3 PASS.
- H.4 PASS.
- H.5 PASS. The ΣMT and ROI-FFM values match the abstract.
- H.6 PASS.
- H.7 PASS.
- H.8 PASS. The 7.0 % is the hypertrophy odds (the 9.8 % is strength), as stated.
- H.9 PASS.
- H.10 PASS.
- H.11 PASS.
- H.12 PASS.
- H.13 PASS.
- H.14 FIX. The abstract says frequency and volume-load were "reduced" and gives RST1 = 50.3 % and RST2 = 57.1 % without saying whether these are the cut or the remainder. "Cut to" reads more than the record says.
  - `value` = `after 8 wk of training (QCSA +5.8 to +6.9 %), 8 wk at 1 or 2 sessions/wk with training frequency and volume-load reduced (the abstract gives RST1 = 50.3 % and RST2 = 57.1 % without saying whether that is the cut or the remainder) kept 1RM and QCSA unchanged; the ceased-training group lost half-squat 1RM (22.6 %) and QCSA (5.4 %) relative to the training period`
- H.15 PASS.
- H.16 PASS.
- H.17 PASS.
- H.18 PASS.
- H.19 PASS.
- H.20 PASS.
- H.21 PASS.
- H.22 PASS.
- H.23 PASS.
- H.24 PASS. A rodent group design graded EXP follows the register's practice of grading animal studies by their design.
- H.25 PASS.
- H.26 PASS.
- H.27 PASS.
- H.28 PASS.
- H.29 PASS.
- H.30 PASS.
- H.31 PASS.
- H.32 PASS.
- H.33 PASS. The 24 h net balance (-0.0413) is omitted, which is acceptable.
- H.34 PASS. The population cell honestly says age and sex are not in the abstract, and the full text is not open access.
- H.35 PASS.
- H.36 PASS.
- H.37 PASS. Random-order crossover graded RCT, which is correct.
- H.38 FIX. The ~20 % and ~40 % figures are confirmed in the Results ("Prolonged muscle protein synthetic response"). However, the "< 15 % of the increment" figure is the authors' re-expression of the oxidation rates of two EARLIER studies (their refs 18 and 19, Moore et al. and Witard et al.), not this trial's measurement. This trial's own finding is that oxidation rose with 100 g but was negligible relative to whole-body protein synthesis (Fig. 2J).
  - `value` = `Results: myofibrillar protein synthesis rates were about 20 % higher in the 0-4 h period and about 40 % higher in the 4-12 h period after 100 g than after 25 g; the anabolic response lasted > 12 h; amino-acid oxidation rose with 100 g but was negligible relative to whole-body protein synthesis; Discussion: the oxidation rates of two earlier dose-response studies (the authors' refs 18 and 19, Moore et al. and Witard et al.), re-expressed relative to protein intake, were < 15 % of the increment in ingested protein`
- H.39 PASS.
- H.40 PASS.
- H.41 PASS.
- H.42 PASS.
- H.43 PASS. The full text confirms unequal randomisation (73 volunteered, 48 completed), so RCT stands. It is paired with S3.21 by design and is not a duplicate.
- H.44 PASS.
- H.45 PASS.
- H.46 FIX. The PMC full text Methods say "randomized, single-blind repeated-measures crossover trial" with conditions in random order, so a crossover was graded below RCT. The population is in the full text.
  - `grade` = `RCT`
  - `population` = `seven resistance-trained young adults analysed (five men, two women), 22 +/- 2 y, 6 +/- 1 y of training, lean`
  - `range` = `randomised single-blind crossover of three 3-day conditions (15 vs 40 kcal/kg FFM) with >= 2 wk washout; serial blood draws after 5 x 5 squats on day 3; n = 7 analysed; design and sample from the PMC full text (Methods, Results)`
- H.47 PASS.
- H.48 PASS, as `unverified`. Crossref resolves the title, authors, SCJ 42(5):7-21 and 2020. The text was not read, so `unverified` is the honest status. S3.30 (advanced-recomp) is its open companion, not a duplicate.
- H.49 FIX. The abstract reads "reaching ~50-60% of baseline 6 years later", and "above baseline" is the harvester's reading of an ambiguous phrase. The full text is not open access.
  - `value` = `a linear-log relationship in all models; by about 1-2 y strength had practically plateaued; about 30-50 % gain over the first year, "reaching ~50-60% of baseline 6 years later" (the abstract's words, read as a gain over baseline); sex, body weight and age had minimal interaction`
- H.50 PASS.
- H.51 FIX. Table 1 values are confirmed (26.2/30.3/27.2/31.3 and 9.1/10.6/9.8/11.3 cm2), and the size responses did not differ between RT1 and RT2. The `range` cell carries harvester arithmetic ("derived: about 76 % … 53 %").
  - `range` = `n = 20 training + 27 control; ultrasound; values from the PMC full text, Table 1 (means; the table gives +/- SD) and section 3.1`
- H.52 PASS.
- H.53 PASS. Confirmed in the PMC Results and the Fig. 1C legend (n = 7, mean +/- SEM). It is distinct from S0620.
- H.54 PASS.
- H.55 PASS.
- H.56 PASS.
- H.57 PASS.
- H.58 PASS.
- H.59 PASS.
- H.60 PASS. Confirmed on the PMC page: myonuclei are lost over longer periods, and the methylome, transcriptome and proteome carry the memory.
- H.61 PASS.
- H.62 PASS. Title-level only, as the row states. The record has no abstract.
- H.63 PASS.
- H.64 PASS (open).
- H.65 PASS (open).
- H.66 FIX (open). The range cites a part-file id (S1.29) that will not exist after the mint.
  - `range` = `no record matching a Ribeiro 2023 energy-surplus trial was found in PubMed or Crossref; the closest surplus trial is Helms 2023 (Sports Med Open 9:102, pmid:37914977; the lean-science part's S1.29, to be cited by its minted S id when applied)`
- H.67 PASS (open). Its S0605 and S0606 readings match the register.
- H.68 PASS (open).

## Count

68 rows: 62 PASS, 6 FIX (H.14, H.38, H.46, H.49, H.51, H.66) and 0 DROP. No bibliographic defect was found, and no duplicate needs dropping.
