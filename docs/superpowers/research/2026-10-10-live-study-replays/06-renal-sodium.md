# Renal sodium and water handling: the harvest behind the sodium-drain fix (Plan 11f)

Harvester: claude-opus-5-5, 2026-10-10. Read-only. No tracked file was edited except this page and its part file,
`06-renal-sodium-rows.tsv` (33 rows, provisional ids `S6.1`–`S6.33`; 27 settled, 6 open). No subagent ran.

**How the records were resolved.** Every settled row's record was resolved through Europe PMC (title, first author,
year, journal, volume, pages, PMID, DOI) and, for the two books, through the National Academies reader, before the value
was copied.
- Values come from the text read:
  - the abstract, for most journal rows;
  - the full text, for van den Bosch 2021 (PMC efetch) and Lucko 2018 (PMC page);
  - EFSA 2019's full text (Europe PMC XML);
  - IOM 2005 chapters 4 and 6, read whole from the NAP reader, with page numbers.
- A value quoted from an abstract is marked as such in its row's `range` cell.
- `05-sodium-drain.md` § 4 named a set of candidate sources. Three of them could not be read: Strauss 1958, Hollenberg
  1980 and McCance 1936. Each is filed as an open row (§ 9).
- 05 gives Lucko 2018's journal as "Nutrients". The record is *J Clin Hypertens* 20:1220–1229.

**Grades.**
- A metabolic-ward or controlled dosing experiment that is not randomised is `EXP`.
- A randomised-order crossover is `RCT` (van den Bosch 2021; Heer 2000, "a controlled, randomized study"; He 2005's
  month-long arm).
- The IOM and EFSA reports are `AUTH`. Where an authority restates a primary source that was not itself read (Dahl 1958,
  Holbrook 1984, Allsopp 1998, Dontas 1972), the row cites the authority and names the primary in `range`.

**Id mapping.** A dry run of `science_delta.py apply` on the part file passes and would mint `S6.n → S(1664+n)`
(S6.1 → S1665 … S6.33 → S1697) on today's register. The mapping holds only if nothing else is minted first. § 7 uses
the provisional ids.

---

## 1. Obligatory sodium losses

**S6.1 — total obligatory loss (IOM 2005, AUTH).**
- p. 275: "When substantial sweating does not occur, total obligatory sodium losses are very small, up to 0.18 g/day or
  8 mmol/day (Table 6-1) (Dahl, 1958)."
- Table 6-1, in mmol/d: urine 0.2–1.5; skin (nonsweating) 1.1; feces 0.4–5.4; total 1.7–8.0.
- p. 270 restates the figure: "Under conditions of maximal adaptation and without sweating, the minimal amount of sodium
  required to replace losses is estimated to be no more than 0.18 g (8 mmol)/day."
- p. 276: "Obligatory urinary losses of sodium in adults are approximately 23 mg (1 mmol)/day (Dole et al., 1950)."
- Population: adults in a temperate climate.

**S6.2 — the Yanomamo (Oliver 1975, COH, abstract).**
- "In twenty-four hour urine collections on adult male Indians, excretion of sodium averaged only 1 plus or minus 1.5
  (SD) mEq."
- IOM p. 276 gives the n (26 men) and a later study (Rose 1988, n = 195) at 0.9 ± 2.3 mmol/d.
- The plasma renin activity was "comparable to those of civilized subjects placed for brief periods on 10 mEq sodium
  diets".
- Design: cross-sectional, life-long no-salt culture, tropical.

**S6.3 — faecal loss (EFSA 2019 § 2.3.4.2, AUTH).**
- Faecal losses were "relatively stable and limited to a few mmol/day for sodium intakes over a range between 1.2 and
  12.7 g/day (50 and 550 mmol/day)".
- Holbrook 1984: "56 ± 26 mg/day (2.4 ± 1.1 mmol/day), representing less than 2% of sodium intake". That was 28
  free-living US adults at a mean intake of 148 mmol/d.

**S6.4 — dermal loss without sweating (IOM 2005 p. 277, AUTH).**
- "less than 0.025 g (1.1 mmol)/day (Dahl, 1958; Dahl et al., 1955)";
- "In another study, estimated obligatory dermal losses of sodium ranged from 0.046 to 0.09 g (2 to 4 mmol)/day
  (Fregly, 1984)."

**S6.5 — balance at three intakes with heat exposure (IOM 2005 Table 6-2, p. 277, from Allsopp 1998, AUTH).**
- After 8 days, in mmol:

  | intake | n | urine | faeces | 12-h sweat | balance |
  |---|---|---|---|---|---|
  | 66 | 9 | 32.4 | 1.4 | 24.8 | +0.2 |
  | 174 | 9 | 92.3 | 5.4 | 39.1 | +29.1 |
  | 348 | 7 | 251.3 | 14.2 | 52.6 | +14.7 |

- Faecal sodium rises with intake. It stays at or below 5.4 mmol/d up to 174 mmol/d.
- These men sweated at 40 °C for 10 h a day, so the urine column is not the temperate share.

## 2. Renal adaptation to a change in intake

**S6.6 — Epstein & Hollenberg 1976 (EXP, abstract): the primary kinetic.**
- 89 healthy subjects; intake restricted to 10 mEq sodium and 100 mEq potassium per day.
- "The daily reduction in urine sodium … conformed well to an exponential function." The half-time was:
  - under 30 years: "-17.6 ± 0.7 hours" (the sign is the abstract's);
  - 30 to 59 years: "23.4 ± 1.1 hours";
  - over 60 years: "30.9 ± 2.8 hours".
- Values are given as +/- (the abstract does not name SD or SE).
- The abstract does not give the pre-restriction intake.

**S6.7 — EFSA 2019 § 2.3.4.1 (AUTH).**
- "In experiments in which subjects at a steady state were shifted to a lower level of sodium intake, the half-life for
  the reduction in renal sodium excretion was about 24 h (Strauss et al., 1958; Epstein and Hollenberg, 1976) and,
  consequently, a steady state between sodium intake and urinary sodium excretion is considered to be achieved within a
  few days (Cogswell et al., 2013)."
- IOM 2005 p. 310 adds that older adults adapt "much slower" but reach "less than 10 mmol/day" (Epstein and Hollenberg,
  1976).

**S6.8 — Bijlsma 1991 (EXP, abstract): a step up.**
- "sodium balance was recorded after the switch from LS (20 mmol/day) to HS (300 mmol/day) diet. Cumulative sodium
  balance was equal with (441 ± 45 mmol) or without (458 ± 45 mmol) nitrendipine treatment."
- n = 8 healthy volunteers.
- The abstract gives neither the collection length nor whether ± is SD or SE.

**S6.9 — Heer 2009 (EXP, abstract): a step up, from a 9-man metabolic ward trial.** It also feeds § 4.
- Body mass 71.4 kg. Consecutive intakes: 0.7, then 2.8, then 7.7 mmol NaCl/kg/d.
- "During average normal NaCl intake, 193 (SEM 19) mmol Na were retained and ECV (+2.02 (SEM 0.31) litres) and PV
  (+0.57 (SEM 0.13) litres) increased."
- "During high NaCl intake, 244 (SEM 77) mmol Na were retained but ECV did not increase (ECV −0.54 (SEM 0.30) litres)."

**Reading.** Under a first-order excretion, a step ΔI leaves a cumulative balance of ΔI × τ. Derived from the rows
above (harvester arithmetic, never a cell):

| source | reading | τ |
|---|---|---|
| Epstein, < 30 y | t½ 17.6 h | 25.4 h |
| Epstein, 30–59 y | t½ 23.4 h | **33.8 h** |
| Epstein, > 60 y | t½ 30.9 h | 44.6 h |
| EFSA | t½ about 24 h | 34.6 h |
| Heer 2009 | 193 mmol over a step of (2.8 − 0.7) × 71.4 = 149.9 mmol/d | 30.9 h (27.9–33.9 h over ± 1 SEM) |
| Bijlsma | 458 mmol over a step of 280 mmol/d | 39.3 h (35.4–43.1 h) |

Three designs (a step down, two steps up), three labs and four decades agree that τ is about 1.3–1.6 days for adults.

## 3. Urinary recovery at steady state

**S6.10 — Lucko 2018 (MA, full text).**
- "The pooled estimate for the percentage of sodium excreted in urine for all studies included in the meta-analysis was
  92.8% (95% CI 90.7, 95.0, heterogeneity 95.1%, P < 0.001)."
- 35 studies at a constant intake for at least 3 days; adults 18–80; 22 of the studies in healthy people.
- By stabilisation period: 3 d, 114.4 % (95.1–133.6); 4–5 d, 109.9 % (101.5–118.3); 7+ d, **93.9 % (90.8–96.9)**.
- EFSA gives the healthy-only estimate as 93.7 % (90.5–96.8).
- Lucko's own discussion: "When there is a substantive sustained change in dietary sodium, it can take 3 or more days
  before a new steady state urine excretion of sodium is achieved."
- No certainty rating given.

**S6.11 — IOM 2005 p. 276 (AUTH).** "90 to 95 percent of total intake is excreted in urine (Holbrook et al., 1984;
Pietinen, 1982)."

**S6.12 — Lerchl 2015 (EXP, abstract).**
- 10 men over 105 and 205 days at fixed intakes of 12, 9 and 6 g salt/d.
- "Urinary recovery of dietary salt was 92% of recorded intake, indicating long-term steady-state sodium balance in both
  studies."

## 4. Plasma sodium constancy and water retained with sodium

**S6.14 — van den Bosch 2021 (RCT, full text, Table 1).** 70 healthy men, 7 days at 200 and at 50 mmol/d in randomised
order. High vs low sodium:
- plasma sodium 140 ± 3 vs 138 ± 3 mmol/L;
- body weight 80.6 vs 79.2 kg;
- ECFV 17.4 vs 16.5 L/1.73 m²;
- urinary volume 1722 vs 1835 ml (p 0.2);
- urinary sodium 230 vs 38 mmol/24 h.

So a four-fold intake difference moves plasma sodium by 2 mmol/L and body weight by 1.4 kg. Urine volume does not move.

**S6.16 and S6.17 — He 2005.**
- (EXP) From 350 to 10–20 mmol/d for 5 days, plasma sodium falls "approximately 3 mmol/L".
- (RCT) From about 170 to about 100 mmol/d for a month, it falls 0.4 ± 0.2 mmol/L.

**S6.18 — IOM 2005 p. 92.** Plasma osmolality "rarely varies beyond ± 2 percent and is controlled around a set-point of
280 to 290 mOsmol/kg".

**S6.19 — IOM 2005 p. 273.** Sodium concentration is 140 mmol/L in plasma, 145 mmol/L in interstitial fluid and
150 mmol/L in plasma water.

**Isotonic retention, and where it fails.**
- S6.9: on a step from low to normal intake, 193 mmol retained came with +2.02 L of ECV. That is 10.5 mL per mmol
  (derived), more than isotonic.
- S6.9: on a step from normal to high, 244 mmol retained came with no ECV gain.
- S6.15, Heer 2000 (RCT, abstract): 32 men, 50–550 meq NaCl/d. Plasma volume rose 315 ± 37 ml at 550, but "total body
  water did not increase. In parallel, body mass also did not increase."
- S6.13, Rakova 2013 (EXP, abstract): at a constant intake, total-body sodium swung ±200–400 mmol "without parallel
  changes in body weight and extracellular water".

**Reading.**
- Across the low-to-normal band (about 50–200 mmol/d), sodium retained or lost is accompanied by water, near or above
  isotonic.
- At high intakes, and over weekly rhythms, sodium is stored without water (the osmotically inactive store).
- Option B's isotonic `weu` is supported in the band a game diet occupies (S6.14's 50–200, the sim's 120–223). It
  overstates water retention at very high intakes.

## 5. Maximal water excretion and urine osmolality

**S6.20 — IOM 2005 (AUTH).**
- p. 74: water toxicity follows intakes that "greatly exceeded the kidney's maximal excretion rate of approximately 0.7
  to 1.0 L/hour".
- p. 83: urine output "can transiently increase to approximately 600 to 1,000 mL/hour with water loading (Freund et al.,
  1995; Noakes et al., 2001; Speedy et al., 2001)".

**S6.21 — Noakes 2001 (EXP, abstract).** 6 healthy men at rest drank 0.9–1.8 L/h for 3 h.
- "All control subjects gained weight (2.7 ± 0.2 kg) because the rate of oral fluid intake exceeded the peak rate of
  urine production (778 ± 39 ml/h)."
- Plasma sodium fell "from 144 ± 2.6 to 136 ± 1.1 mmol/l".
- "Free water clearance reached a maximum of 11.2 ± 0.9 ml/min after 2 hours."
- Values are given as +/- (the abstract does not name SD or SE)M.

**S6.22 — IOM 2005.**
- p. 100: "Normal values for urine osmolality vary from 50 to 1,200 mOsmol/L (Tilkian et al., 1995)."
- p. 82: at maximal concentration (about 1,200), "the minimum urine output is approximately 500 mL/day".

**S6.23 — IOM 2005 pp. 81–82.**
- Western diets impose "an average of 650 mOsmol of electrolytes and other solutes" a day.
- Dontas 1972: maximal urine osmolality was 1,089 mOsm/kg in young men, with a minimum urine output of 392 mL/d.
  Older men and women reached 808 and 843 mOsm/kg, with 700 and 1,086 mL/d.

**Derived.** 650 mOsm/d at the 50 mOsm/kg floor caps sustained water diuresis at about 13 L/d (about 540 mL/h) on a
normal solute load. This is arithmetic, and the solute-limit row (S6.32) is open.

## 6. Salt as a sodium reference

**S6.27 — IOM 2005 (AUTH).**
- p. 269: "To convert mmol to mg of sodium, chloride, or of sodium chloride, multiply mmol by 23, 35.5, or 58.5."
- p. 322: salt is "(23/58.5)—39.3%" sodium.

So 1 g of NaCl is 1000 / 58.5 = 17.1 mmol of sodium (derived). This is the factor a `Base.Salt` vector would use.

## 7. The open rows S1096, S0564, S1099 and S1093

**S1093 — the obligatory daily water loss at rest: settled by S6.24.**
- IOM 2005 Table 4-2 (p. 80) gives minimum losses for sedentary adults without sweating, in mL/d: respiratory 250–350,
  urinary 500–1,000, faecal 100–200, insensible 450–1,900; metabolic production +250–350; net 1,050–3,100.
- The mod's basal turnover (S0088's AI of 3.7 L as turnover) sits above that range.
- The fixed isotonic urine (65 % of 3.7 L = 2.4 L/d) is 2.4 times the top of the obligatory urinary range. Most of it
  should flex with water intake rather than be charged.
- Proposed: `status S1093 superseded --successor <S6.24's id>`.

**S1096 — the renal time constant of a sodium surplus: settled by S6.8 and S6.9 (steps up) with S6.6 and S6.7 (steps
down).**
- Proposed: superseded, with successors S6.6, S6.8 and S6.9.
- The strongest primary is Epstein (n = 89, an age-banded exponential fit). It is a step down. The step-up readings are
  small (n = 8 and n = 9), but they agree within about ±20 % (§ 2).

**S0564 — the repletion time constant after depletion: partly answered.**
- S6.8 (from 20 to 300 mmol/d) and S6.9 (from 0.7 to 2.8 mmol/kg/d) are repletions from an adapted low intake. They give
  the cumulative retention, and so τ.
- A repletion after a true deficit (a negative balance, McCance-style) was not read (S6.28 open).
- Proposed: superseded, with successors S6.8 and S6.9, if the controller accepts "repletion from an adapted low intake"
  as the question. Otherwise keep it open, naming S6.28.

**S1099 — osmotic thirst: threshold and slope settled, cap open.**
- S6.25, Thompson 1986 (n = 10): "Thirst (cm) = 0.3 (plasma osmolality-281)"; vasopressin "= 0.4 (plasma
  osmolality-285)".
- S6.26, Davison 1984 (n = 8): a conscious desire to drink at 298 ± 2.0 mOsm/kg postpartum and 287 ± 1.6 in pregnancy.
- These two disagree on onset: 281 is an extrapolated VAS intercept, 298 the first conscious desire. They stand as a
  pair, and the choice between them is a ruling.
- The suppression of thirst below normal (the mod's cap below 135 mmol/L) has no row (S6.31 open).
- Proposed: superseded, with successors S6.25, S6.26 and S6.31.
- These rows still do not justify `HYPO_CAP` 0.11 (05 § 7). The cap stays a game choice. 05's argument that it must sit
  below vanilla's 0.1 autodrink literal (#2770) is mechanical, not physiological.

## 8. What option B's constants would be

These figures are computed only from the rows above. The arithmetic is mine and never goes in a cell.

### BASAL, the obligatory sodium loss: 8 mmol/d

**Source.** S6.1, the IOM's "up to 0.18 g/day or 8 mmol/day". Its parts, from Table 6-1:
- urine 0.2–1.5 mmol/d, in line with the Yanomamo's 1 ± 1.5 (S6.2);
- skin 1.1 (2–4 in Fregly, S6.4);
- faeces 0.4–5.4 (S6.3 gives 2.4 ± 1.1 at 148 mmol/d).

**Shape.** The current term `basalG / 1000 × BASAL_NA_FRAC × OSM_REF` scales with sex through `AI`.
- Kept in that shape, 8 mmol/d for the male reference means `BASAL_NA_FRAC` = 8 / (3.7 × 140) = **0.0154**. The female
  value then falls to 5.8 mmol/d.
- No source gives a sex difference in obligatory sodium loss. A plain mmol/d constant, decoupled from water turnover,
  matches the evidence better.
- 05's "about 0.019" (10 mmol/d) is above the IOM ceiling.

**Check against S6.10.** At steady state, urine = I − 8.
- At 120.4 mmol/d, urine is 93.4 % of intake.
- At 148 mmol/d, 94.6 %.
- Both fall inside Lucko's 92.8 % (90.7–95.0) and the IOM's 90–95 %.
- At 222.9 mmol/d, 96.4 % sits just above Lucko's interval. That is because faecal loss in fact grows with intake (S6.5:
  14.2 mmol/d at 348). The error is about 5 mmol/d at most and does not matter to plasma.

### τ, the adaptation time constant: 33.8 h for the reference adult

**Source.** S6.6's 30–59 y half-time, 23.4 h / ln 2. The table in § 2 gives the age bands and the cross-checks:
- 25.4 h for an adult under 30;
- 44.6 h over 60;
- EFSA's "about 24 h" half-life gives 34.6 h;
- the step-up retentions give 30.9 h (S6.9) and 39.3 h (S6.8).

**`NA_TAU_H` today.**
- The code's surplus clearance is first order, so its steady-state pool is `(I − BASAL) × τ`. That is the cumulative
  retention these studies measure, so the structure is right and only the constant moves.
- The current `NA_TAU_H` = 24 h reads as a time constant. That is about the under-30 band (25.4 h), and about 30 % short
  of the reference adult.
- **If 24 h was meant as EFSA's half-life, τ should be 34.6 h.**

**Effect of the change.**
- At 33.8 h, the steady pool at 120.4 mmol/d is (120.4 − 8) × 1.41 d = 158 mmol.
- In option B, that pool carries 158 × 7.14 = 1.13 kg of water. 05's sim showed +1.2 kg at τ = 24 h and BASAL 10.
- Against S6.14, a 50→200 mmol/d step predicts 150 × 1.41 = 211 mmol retained, or about 1.5 kg at 7.14 g/mmol. Measured:
  1.4 kg of body weight. The two agree.

### CLEAR_GH, the maximal free-water clearance: 672 g/h

**Source.** S6.21's maximal free-water clearance of 11.2 ± 0.9 mL/min = 672 g/h (618–726 g/h over ± 1 SEM).
- Peak urine flow in the same subjects was 778 ± 39 mL/h. That includes the solute-bearing fraction.
- S6.20's authority range is 0.7–1.0 L/h.

**Why the free-water figure.** Option B clears water above the euhydration set point. That water is solute-free, so the
free-water clearance is the matching quantity.

**Against today's value.** The current 320 g/h comes from S0521, an alcohol-diuresis reading: 1279 mL over 4 h after
1 L of beer. It is not a maximum and is about half the measured ceiling. At 320 g/h the model makes hyponatraemia from
drinking about twice as easy as the evidence does.

**Caveats.**
- The maximum is reached "after 2 hours" of loading. A zero-order 672 g/h from the first minute overstates early
  clearance.
- The ceiling falls with a low solute intake (S6.32 open). The derived 13 L/d at 650 mOsm/d means a near-solute-free
  diet caps sustained clearance lower.

### k, water retained per mmol of sodium retained: 7.14 g/mmol

**Source.**
- S6.19's plasma sodium of 140 mmol/L gives 1000 / 140 = 7.14 g/mmol.
- Its interstitial 145 mmol/L gives 6.90 g/mmol.
- Option B's `weu = 1000 × t0 × (f.na + f.k) / p0`, with `p0 = 140 × 0.73 × lm`, is this k whenever `t0 = 0.73 × lm`.

**Measured.**
- S6.9: 10.5 mL ECV per mmol on a low-to-normal step.
- S6.14: 1.4 kg of weight over the 211 mmol predicted at τ 33.8 h, or 6.6 g/mmol (derived; ECFV 0.9 L/1.73 m² gives
  4.3 mL/mmol).
- Near zero at high intakes: S6.9's high step, S6.15, S6.13.

**Ruling material.** 7.14 g/mmol is supported in the low-to-normal band. At sustained high intakes, the stated limit
is that some sodium is stored without water.

**Potassium.** `weu` also adds `f.k`. No row here prices water retained with a potassium surplus. That term stays
labelled as a game choice, or wants its own harvest.

### Plasma constancy, the check on option B as a whole

S6.14 shows 2 mmol/L of plasma difference between 50 and 200 mmol/d. S6.16 shows about 3 mmol/L after 5 days at
10–20 mmol/d. S6.18 shows about ±2 % osmolality across normal life.

05's option B sim held plasma at 140.4–141.1 mmol/L on every diet, and its zero-sodium arm lost about 0.7 L instead of
falling in plasma. That is a little *more* constant than people are. S6.16 says a near-zero diet should cost about
3 mmol/L over 5 days.

This does not block the fix. It is a stated limit of the isotonic `weu`, alongside 05's limit 3.

## 9. What could not be found

**McCance 1936.**
- The record resolves: *Proc R Soc Lond B* 119:245–268, doi:10.1098/rspb.1936.0009.
- The full text returned HTTP 403, and Europe PMC has no abstract.
- Filed open as S6.28.

**Strauss 1958.**
- The record resolves: *AMA Arch Intern Med* 102:527–536, doi:10.1001/archinte.1958.00260210013003, pmid:13582242.
- No abstract or full text could be read.
- Filed open as S6.29. Its half-life reaches the register only through EFSA (S6.7).

**Hollenberg 1980.**
- The record resolves: *Kidney Int* 17:423–429, doi:10.1038/ki.1980.50, pmid:7392417.
- The publisher returned HTTP 403.
- Filed open as S6.30.

**Thirst suppression below normal plasma sodium or osmolality.** No human value was read. Filed open as S6.31.

**Maximal free-water clearance as a function of solute intake.**
- Berl 2008 (*J Am Soc Nephrol* 19:1076–1078, pmid:18337482) states the dependence without numbers in its abstract.
- The full text returned HTTP 402.
- Filed open as S6.32.

**A measured plasma-sodium rise per % of body mass lost as pure water.** None was found. Filed open as S6.33. It is
arithmetic from the open Edelman row S1092.

**Rakova 2013's urinary recovery fraction.** Cell Metab returned 403. The 92 % comes from the companion Lerchl 2015
(S6.12) instead.

**Rakova 2017 (*J Clin Invest*, free-water accrual at high salt).** The PMC full text would not download. The JCI page
gave no plasma-sodium or body-water values, so it is not filed.
