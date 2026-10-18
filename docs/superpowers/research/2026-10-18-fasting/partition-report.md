# The fasting partition: how a fasting body splits its energy between fat and lean (Plan 16 Task 1)

Plan 16 Task 1, 2026-10-18. A science pass for spec § 3.1 (`docs/superpowers/specs/2026-10-18-pre-upload-design.md`):
what the deficit arm `K.partition.deficitLean` (`mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Partition.lua:61-80`)
should rest on in a prolonged total fast. The diagnosis is `.superpowers/sdd/plan-16-brainstorm/plan14-findings.md` § 1:
Alpert's fat-store ceiling (S0056, `FAT_CEIL_KCAL = 69`, `:15`) binds from day 1 of a fast, and with no protein intake
the whole overflow is paid by lean at 1816 kcal/kg. The default body loses 84 % of its weight as lean, and about half its
energy comes from lean.

The part file is `.superpowers/sdd/2026-10-18-plan-16-pre-upload/fasting-science.tsv` (provisional ids `S1.1`-`S1.11`).
§ 10 gives the two `settle` commands and the one `supersede` command for the controller.

## 1. Answer in brief

- **The evidence contradicts the ceiling as a limit in a fast.** Measured fasts give 13-18 % of energy from protein in a
  lean or normal man:
  - 17.5 % after day 13 in Benedict's 31-day subject;
  - 13.0-17.1 % over Jackson's 44 days;
  - about 13 % of TEE (17 % of BMR at TEE/BMR 1.3) at 20 % initial fat on Elia's curve.
  
  The mod at HEAD gives about 50 %. At that 13-18 % share, the fat store must deliver more than 69 kcal per kg of fat
  a day.
- **Alpert's 69 kcal/kg/d is what the Minnesota men's fat delivered, not a maximum.** Their measured fat loss, from Keys
  1950 Table 152, works out at 72 kcal/kg/d over weeks 0-12 and 63 over weeks 12-24 (my arithmetic, § 4). The Minnesota
  deficit was moderate. The Ranger course (S1910, the register's own row) took 66 % of initial fat in 56 days. That is
  about 111 kcal per kg of initial fat per day (my arithmetic from the abstract's ratios), 1.6 times the "ceiling".
- **Forbes alone (S0054, S0055) reproduces the evidence across body fat with no fitted constant.** Hall's energy
  densities (S0126) turn its lean weight share into a protein-energy share. That share is 13 % at the default body's
  20 % fat, against Elia's about 13 % of TEE. It is 6 % at the Obese body's 37 %, against about 7 %. Chow and Hall
  2008 give the coefficient, 10.4 kg, which settles S1056.
- **A protein-sparing term over time (option c) has support only in the obese**, where the ceiling does not bind
  anyway.
  - Elia 1999: the protein share "decreases with time in obese individuals … but shows little sign of a reduction in
    lean individuals … for up to a month" (S1.2).
  - Henry 1988: the P-ratio stays unchanged in normal subjects. The nitrogen fall follows the fall in metabolic rate,
    not a specific sparing (S1.4).
- **Recommendation: (a), drop the ceiling from the deficit arm.** § 8 gives each body's prediction and § 9 the case.

## 2. Sources and how each was read

Every citation was resolved against its record through Europe PMC, Crossref (via OpenAlex) or the archive record. Title,
first author and year matched.

| source | record | read |
|---|---|---|
| Elia M, Stubbs RJ, Henry CJ 1999, Obes Res 7:597-604 | doi:10.1002/j.1550-8528.1999.tb00720.x; pmid:10574520 | **full text** (8 pp) from a Wayback Machine copy of the publisher PDF (Wiley's own link returns 403). Figure 2 was digitised (§ 3) |
| Owen OE, Felig P, Morgan AP, Wahren J, Cahill GF 1969, J Clin Invest 48:574-583 | doi:10.1172/jci106016; pmid:5773093 | **full text** (JCI's PDF) |
| Cahill GF, Owen OE 1968, Trans Am Clin Climatol Assoc 79:13-20 | pmid:5667163 | **full text** (Wayback copy of the PMC PDF) |
| Benedict FG 1915, A Study of Prolonged Fasting, Carnegie Institution of Washington Publication 203 | url:https://archive.org/details/studyofprolonged00beneuoft | **full text** (archive OCR). Read: Table 27 (urinary N), the analysis of losses (p. 364) and the heat partition (pp. 413-414) |
| Keys A, Brožek J, Henschel A, Mickelsen O, Taylor HL 1950, The Biology of Human Starvation, vol. 1 | url:https://archive.org/details/cftri.1102biologyofhumanst0000ance_a5l1 | **full text** of the pages used. Tables 89, 151, 152 (pp. 175-176, 284) and Table 323 (p. 705), read from the page images |
| Chow CC, Hall KD 2008, PLoS Comput Biol 4:e1000045 | doi:10.1371/journal.pcbi.1000045; pmid:18369435 | **full text** (Europe PMC XML; equations from the arXiv version 0802.3234) |
| Alpert SS 2005, J Theor Biol 233:1-13 | doi:10.1016/j.jtbi.2004.08.029; pmid:15615615 | **abstract only**. The full text is closed: OpenAlex and Semantic Scholar list no open copy, and none was found on the web |
| Alpert SS 1988, Int J Obes 12:533-542 | pmid:3235270 | **abstract only**. Europe PMC now carries the abstract that S0058 lacked |
| Alpert SS 2007, Metabolism 56:363-372 | doi:10.1016/j.metabol.2006.10.018; pmid:17292725 | abstract only; context, no row |
| Henry CJ, Rivers JP, Payne PR 1988, Eur J Clin Nutr 42:543-549 | pmid:3066619 | **abstract only** |
| Jackson JM, Blaine D, Powell-Tuck J, Korbonits M, Carey A, Elia M 2006, Nutrition 22:889-897 | doi:10.1016/j.nut.2006.06.001; pmid:16928474 | **abstract only** |
| Owen OE, Smalley KJ, D'Alessio DA, Mozzoli MA, Dawson EK 1998, Am J Clin Nutr 68:12-34 | doi:10.1093/ajcn/68.1.12; pmid:9665093 | **abstract only** |
| Hall KD 2006, Am J Physiol Endocrinol Metab 291:E23-E37 | doi:10.1152/ajpendo.00523.2005; pmid:16449298 | full text, for context only (its Minnesota fluxes are model output, not measurements); no row |
| Henry CJ 1990, Eur J Clin Nutr 44:329-335 | pmid:2364921 | **not reached**: no abstract and no open copy. Elia 1999's Figure 2 is the same group's later compilation (Elia 1992, with Henry as co-author of the 1999 commentary) |

## 3. The protein share of energy against initial fat

**Elia, Stubbs and Henry 1999** (full text) compile total-starvation studies.
- **Figure 2** plots the protein share of BMR over a fast of more than 16 days against initial % body fat: 9 men and 4
  women as individuals, plus group means. It is drawn from Elia 1992.
- **Digitised points.** I calibrated the figure on its own ticks (0-40 % in 10s; 0-50 % fat in 10s) and located the
  circles by blob detection. The points are (fat %, protein % of BMR), ± about 1 point:
  - filled: (4.5, 31.2), (11.8, 23.6), (12.9, 17.1), (33.2, 18.5), (36.7, 6.2), (39.8, 8.9), (41.0, 5.5), (46.8, 4.9),
    (47.4, 9.3), (50.5, 3.6);
  - open: (37.8, 9.1), (38.0, 10.3), (42.0, 11.5), (45.0, 5.3), (47.0, 3.2).
- **My curve.** A log-linear least-squares fit through them gives about 38.2·e^(−0.0406·fat%) % of BMR. That is 29.4 at
  6.5 % fat, 17.0 at 20 % and 8.6 at 36.8 %. The fit is mine, so it goes in no cell.
- **The y axis is % of BMR**, not of TEE. Elia's theoretical curve assumes a TEE/BMR of 1.3. At that ratio the shares of
  TEE are about 23, 13 and 7 %.
- **The text says:**
  - "protein loss and percent energy derived from protein oxidation are 2- to 3-fold less in the obese than in the
    lean";
  - "the proportion of energy derived from protein oxidation decreases with time in obese individuals … but shows little
    sign of a reduction in lean individuals undergoing total starvation for up to a month";
  - "Fat becomes the major source of energy during starvation accounting for ~94 % of the energy expenditure in obese
    subjects and 78 % in lean subjects".

**Henry, Rivers and Payne 1988** (abstract): "during prolonged starvation in normal subjects the fraction of total
energy expenditure derived from protein (the P ratio) remained unchanged … urinary nitrogen was reduced … secondary to
the general reduction in metabolic rate, rather than to a specific sparing of protein". This stands against the
textbook protein-sparing reading (S0105, S0108, Kerndt and Cahill). The two are reconciled by body fat: sparing over
time is the obese response (Elia 1999).

**Jackson 2006** (abstract) followed a 44-day water-only fast by a non-obese man of 96.0 kg with 20 % fat:
- 25.5 % of mass lost, "a quarter to a third" of it fat;
- 20 % of total body protein and 20-25 % of FFM lost;
- TEE 1638-2155 kcal/d, of which 13.0-17.1 % came from protein oxidation.

**Benedict 1915** (full text) followed Levanzin's 31-day fast. He was 170.7 cm, 60.1 kg at examination and aged 40.
- **Losses:** 13.25 kg in all — "7.33 kilograms of water, 201 grams of carbohydrate, 3,650 grams of fat, and 1,664
  grams of protein" (p. 364).
- **Heat partition:** "After the thirteenth day, approximately 17.5 per cent of the heat was derived from the oxidation
  of the protein and the remainder from the combustion of fat". Glycogen gave 10-16 % on the first 3 days (pp. 413-414).

**Owen 1998** (abstract): five obese subjects fasting 21 days "lost body fat and fat-free mass in parallel".
"Aminogenic oxidation" was 7 % late in the fast.

**Forbes against this evidence.** The mod's lean weight share is forbes_c / (forbes_c + fm). Chow and Hall 2008 state
Forbes's law as F = D·exp(L/10.4), so dL/dF = 10.4/F; for weight lost, dL/dW = 10.4/(10.4 + F). Hall's densities (S0126:
1816 and 9441 kcal/kg) turn that weight share s into an energy share:

E_lean = s·1816 / (s·1816 + (1 − s)·9441)

| body | creation fat | Forbes energy share (instant) | Elia curve, % of TEE (at 1.3) | measured |
|---|---|---|---|---|
| Gaunt | 3.62 kg, 6.5 % | 36 % | about 23 % | Elia's 4.5 % man: 31 % of BMR |
| default | 13.0 kg, 20.0 % | 13 % | about 13 % | Jackson (20 % fat): 13.0-17.1 %; Benedict (lean): 17.5 % |
| Obese | 30.34 kg, 36.8 % | 6 % | about 7 % | Owen 1998: 7 % late; Elia: about 94 % from fat |

Forbes matches the evidence at the default and Obese bodies. It runs about 1.2-1.5 times high at the Gaunt end, where
Elia's curve rests on four lean individuals. Chow and Hall add that Hall, Bain and Chow "showed that the two compartment
macronutrient partition model … using Forbes's law … matched a wide range of data without any adjustable parameters".

## 4. Alpert's ceiling

**Alpert 2005** (abstract): "A limit on the maximum energy transfer rate from the human fat store in hypophagia is
deduced from experimental data of underfed subjects maintaining moderate activity levels … (290 ± 25) kJ/kgd … An exact
mathematical solution for the decrease of the FFM is derived for the case where the fat mass (FM) is in its limited
energy transfer mode."

The full text is closed, so the lean energy density Alpert pairs with his ceiling could not be read. Option (b) cannot be
re-based on Alpert's own value. Alpert 1988 (abstract) gives the closest published companion figures:
- **Energy density of weight lost** in Minnesota semistarvation: "4436 ± 869 kcal/kg (18.57 ± 3.60 MJ/kg)".
- **Lean energy density** "shows a general decline", attributed "to a decrease in the rate of protein catabolism".
- **Protein loss rate:** "0.48 ± 0.12 kg/wk" at first and "0.12 ± 0.03 kg/week" over the second 6 weeks.
- **Response times:** lean "64 ± 2 days", fat "135 ± 4 days".

These settle S0058 (§ 10).

**Where 69 comes from.** "Underfed subjects maintaining moderate activity" are most likely the Minnesota men (inference: the full text is closed; Alpert 1988 modelled semistarvation with the same two-reservoir model). Keys 1950 Table 152
(corrected compartments) reads:

| | C | S12 | S24 |
|---|---|---|---|
| body weight (kg) | 69.50 | 56.90 | 53.63 |
| fat (kg) | 9.66 | 4.95 | 2.78 |
| "active" tissue (kg) | 39.93 | 31.96 | 29.19 |
| thiocyanate space (kg) | 17.13 | 17.21 | 17.88 |

My arithmetic from that table:

| interval | fat lost | per day (kg) | kcal/d at 9441 | mean fat (kg) | per kg of fat |
|---|---|---|---|---|---|
| C to S12 (84 d) | 4.71 kg | 0.0561 | 529 | 7.31 | **72 kcal/kg/d** |
| S12 to S24 (84 d) | 2.17 kg | 0.0258 | 244 | 3.87 | **63 kcal/kg/d** |

So Alpert's 69 ± 6 is the rate the Minnesota men's fat supplied at their deficit. Those deficits were moderate: about
1500 kcal/d of intake (S2245) against a falling expenditure.

**Faster rates elsewhere.** Other cohorts draw fat faster with no sign of a hard limit:
- **Ranger course (S1910, register row):** body fat went from 14.3 % to 5.8 % with a 15.7 % weight loss in 8 weeks.
  Per 100 kg of starting mass that is 14.3 kg → 0.058 × 84.3 = 4.89 kg of fat. That is 66 % of initial fat in 56 days,
  0.0117 of initial fat a day, or about **111 kcal per kg of initial fat per day**, and about 165 per kg of mean fat. My
  arithmetic, independent of body weight.
- **Jackson 2006:** "a quarter to a third" of 24.5 kg is 6.1-8.2 kg of fat from 19.2 kg in 44 days. That is
  **68-91 kcal per kg of initial fat per day** (my arithmetic), at or above the ceiling, with protein at only 13-17 % of
  energy.
- **Elia's lean points:** 17-24 % of BMR from protein at 12-13 % initial fat means 76-83 % of BMR came from fat in men
  with only a few kilograms of it.

**Why HEAD fails.** HEAD caps fat at 69·fm kcal/d. In a fast the default body's deficit is about 1850 kcal/d against a
cap of about 890, so lean pays about 1000 kcal/d. That gives HEAD its 50 % protein energy, three to four times the
measured fasts. Alpert's own rule ("a restriction beyond what the fat store can supply … causes an immediate decrease in
the FFM") is a model statement fitted to one moderate-deficit dataset. It is not observed in total fasting.

## 5. Nitrogen excretion over a fast

- **Benedict 1915 (lean man, full text, Table 27).**
  - Urinary N averaged "over 10 grams" a day for the first 10 days. The highest was 11.87 g on day 4.
  - It ran 7.31-8.81 g/d over days 17-31, with the lowest, 6.94 g, on day 31.
  - Pre-fast intake had run "not far from 13 grams per day".
  - Elia 1999 cites this subject as "7.8 gN/day and BMR 1130 kcal/day on day 31".
- **Owen 1969 (11 obese inpatients, full text).**
  - "Daily nitrogen excretion decreased progressively for the 1st 4 wk of fasting after which it remained fairly
    constant at about 3-6 g/day."
  - In five catheterised subjects at 5-6 weeks: 4.66 ± 0.62 g/d (Table III), 42 % of it ammonia and urea 1.55 g/d
    (33 %).
- **Cahill and Owen 1968 (full text).**
  - Without ketone adaptation, the brain's 100-145 g/d of glucose would need "20 or more grams/day" of urinary N,
    "instead of the measured 3-6 grams excreted after several weeks of fasting".
  - Their reference man stores 15 kg of fat (141,000 kcal) and 6 kg of protein (24,000 kcal), for a theoretical survival
    of 4 months.
- **Elia 1999 Table 1:** lean subjects lose 24.0 gN per kg of weight lost, the obese 12.4 gN/kg.

**What it means for the mod.**
- Nitrogen falls in both lean and obese fasts. In lean subjects it falls by about a quarter over a month, alongside the
  falling heat output, so the protein share of energy stays about 17.5 % (Benedict; Henry 1988).
- In the obese it falls to about 40 % of the fed level by week 4, and the share falls with it (Elia).
- So an absolute lean-loss rate that falls with expenditure is already what Forbes plus the mod's falling expenditure
  give. A separate time-based sparing term is an obese-only refinement.

## 6. Keys 1950: body composition and strength

- **Composition.** Table 152 (§ 4) gives the corrected compartments for the 32 men at C, S12 and S24. Table 89 gives the
  uncorrected fat at 13.9, 7.5 and 5.2 % of gross weight. S2061 already cites the 5.2 %.
- **No weekly series.** The monograph gives no week-by-week composition: weight is weekly, composition only at C, S12,
  S24 and in rehabilitation.
- **Strength (S0657).** Table 323 (p. 705) gives handgrip and back lift at C, S12, S24, R6 and R12, not week by week. A
  weekly strength series does not exist in the monograph. I file the five-point series as S1.11 and recommend
  superseding S0657 with it (§ 10).

| | C | S12 | S24 | R6 | R12 |
|---|---|---|---|---|---|
| hand dynamometer, kg (SD) | 58.2 (7.6) | 47.2 (6.5) | 41.8 (6.3) | 42.3 | 47.2 |
| back dynamometer, kg (SD) | 165.4 (27.8) | 131.8 (19.8) | 116.1 (17.8) | 119.0 | 128.4 |

**Forbes against Minnesota.** I integrated Forbes's law from fm 9.66 to 2.78 kg (my arithmetic). It predicts a lean
change of 10.4·ln(2.78/9.66) = −12.95 kg. The measured fat-free change (body weight less fat) is −8.99 kg, while the
"active" tissue fell 10.74 kg as the extracellular space rose 0.75 kg (oedema). Forbes alone over-predicts lean loss in
Minnesota by up to 1.4 times. It does not under-predict, so the fix does not understate lean loss on the one long
semi-starvation series with measured composition.

## 7. The share of weight lost as lean, by day

| study | day | lean (fat-free) share of weight lost | notes |
|---|---|---|---|
| Benedict 1915, lean man | 31 | 0.71 non-fat (water 7.33, protein 1.66, glycogen 0.20, fat 3.65 of 13.25 kg) | protein alone is 12.6 %; the water includes extracellular and glycogen water |
| Jackson 2006, 20 % fat | 44 | 0.67-0.75 ("a quarter to a third" fat) | |
| Keys 1950, 13.9 % fat | 84 (S12) | 0.63 (7.89 of 12.60 kg; my arithmetic) | semi-starvation, not a total fast |
| Keys 1950 | 168 (S24) | 0.57 (8.99 of 15.87 kg; my arithmetic) | oedema inflates the fat-free mass |
| Elia 1999 Table 1, hypothetical lean 70 kg | at death | 0.70; fat 0.30 | 38 % of weight lost; survival 65 d at 1500 kcal/d |
| Elia 1999 Table 1, hypothetical obese 140 kg | at death | 0.37; fat 0.63 | 69 % lost; 270 d |

The measured weight shares are 0.6-0.75 in lean-to-normal men. They include extracellular water and glycogen water, which
the mod's lm (lean tissue at 1816 kcal/kg) does not carry. The energy shares (§ 3) are the cleaner test, and they are
13-18 %.

## 8. The three forms and their predictions

Each form was replayed on the lupa host with the guide's fast setup: `tools/mod_guide_series.py`'s `_guide_replay`,
sleep off, 4 L of water a day in eight drinks, no food, 160 days. The default and Obese bodies are spec § 3.3's; the thin
body is "Gaunt" (`VERY_UNDERWEIGHT`).
- **(a)** sets `partition.FAT_CEIL_KCAL` to 1e9.
- **(b)** keeps the ceiling but charges the overflow to lean at dry protein's density, 4706 kcal/kg (S0126's 19.7 MJ/kg).
  That is the most generous re-basing possible, since Alpert's own density could not be read.
- **(c)** keeps the ceiling but splits the overflow with a protein-sparing term, so that lean pays min(prot, 0.15) of
  it: the 13-17 % of Jackson and Benedict.

The script is in the scratchpad, not the repository; the controller can re-run it from this description. The replays loaded the working tree of 2026-10-18 (Plan 16 Task 2 uncommitted under `mod/`); Task 5 re-runs them from its own commit. The death is
the replay's first row with health gone, read with `viability`.

**How to read the columns.**
- **Lean weight share:** (lean lost) / (mass lost) from creation.
- **Lean energy share:** Δlm·1816 / (Δlm·1816 + Δfm·9441) over the interval. For (b) it understates the true protein
  energy, because the overflow is charged at 4706.

### Default body (65.0 kg, fat 13.0 kg = 20.0 %, BMI 22.4)

| form | death | lean weight share d7 / d14 / d30 / d45 / d60 / death | lean energy share d1-14 / d14-30 / d30-45 / d45-60 | lost by d43 | kg/d in week 3 | fat % at death | BMI at death; day BMI 12 is reached |
|---|---|---|---|---|---|---|---|
| HEAD | **62.09 d, starvation** | 0.84 / 0.85 / 0.85 / 0.85 / 0.84 / 0.84 | 0.53 / 0.52 / 0.50 / 0.50 | 35 % | 0.55 | 23.8 | 12.0; d62 |
| (a) | **77.21 d, wet beriberi** | 0.45 / 0.47 / 0.50 / 0.53 / 0.56 / 0.60 | 0.14 / 0.17 / 0.22 / 0.27 | 21 % | 0.32 | 7.4 | 13.7; d90 |
| (b) | 77.21 d, wet beriberi | 0.75 / 0.76 / 0.77 / 0.78 / 0.78 / 0.79 | (about 0.5 in protein energy) | 24 % | 0.37 | 19.1 | 13.4; d91 |
| (c) | 77.21 d, wet beriberi | 0.56 / 0.57 / 0.59 / 0.62 / 0.64 / 0.66 | 0.21 / 0.24 / 0.27 / 0.32 | 24 % | 0.36 | 10.1 | 13.0; d86 |

**Against the evidence:**
- **Weight lost:** 18 % by day 43 (S2243), Jackson's 25.5 % by day 44, and 0.3 kg/d by week 3 (S0104).
- **First 31 days:** Benedict's lean man lost 3.65 kg of fat and 1.66 kg of protein. (a) loses 4.90 kg of fat and
  4.88 kg of lean, about 1.9 kg of protein at Hall's 1.6 g water per g. HEAD loses 2.65 kg of fat and 14.67 kg of lean,
  about 5.6 kg of protein.
- **Fat share:** fat reaches 5 % at day 97 in (a), and never in HEAD or (b).

### Obese body (82.4 kg, fat 30.34 kg = 36.8 %, BMI 28.4)

| form | death | lean weight share d7 / d14 / d30 / d45 / d60 / death | lean energy share d1-14 / d14-30 / d30-45 / d45-60 | lost by d43 | fat % at death | BMI at death |
|---|---|---|---|---|---|---|
| HEAD | 77.21 d, wet beriberi | 0.26 / 0.26 / 0.28 / 0.33 / 0.39 / 0.44 | 0.06 / 0.08 / 0.13 / 0.17 | 14 % | 29.3 | 20.6 |
| (a) | 77.21 d, wet beriberi | 0.26 / 0.26 / 0.27 / 0.29 / 0.30 / 0.31 | 0.06 / 0.07 / 0.08 / 0.09 | 14 % | 26.6 | 21.5 |
| (b) | 77.21 d, wet beriberi | 0.26 / 0.26 / 0.28 / 0.31 / 0.34 / 0.38 | (overflow at 4706) | 14 % | 28.3 | 21.3 |
| (c) | 77.21 d, wet beriberi | 0.26 / 0.26 / 0.28 / 0.29 / 0.32 / 0.34 | 0.06 / 0.07 / 0.09 / 0.10 | 14 % | 27.1 | 21.4 |

- **The evidence:** Owen 1998 measures 7 % from amino acids late in a 21-day fast, and Elia about 94 % from fat.
- **Where the forms differ:** they agree to day 30. HEAD's lean share climbs once the shrinking fat brings the cap under
  the deficit (day 35 on). (a) holds 7-9 %, the measured obese range.
- **Death:** wet beriberi kills the Obese body first in every form, at BMI 20.6-21.5.

### Gaunt body (55.6 kg, fat 3.62 kg = 6.5 %, BMI 19.1)

| form | death | lean weight share d7 / d14 / d30 / death | lean energy share d1-14 / d14-30 / d30-45 | lost by d31 | fat % at death |
|---|---|---|---|---|---|
| HEAD | **31.02 d, starvation** (BMI 11.8) | 0.97 / 0.97 / 0.97 / 0.97 | 0.85 / 0.84 / 0.83 | 38.5 % | 8.4 |
| (a) | **41.14 d, starvation** (BMI 12.0) | 0.76 / 0.78 / 0.83 / 0.86 | 0.41 / 0.56 / 0.72 | 27.9 % | 1.8 (fm about 0.63 kg; the 0.5 kg floor is reached near day 46, after death) |
| (b) | 45.01 d, starvation (BMI 11.9) | 0.95 / 0.95 / 0.95 / 0.95 | (overflow at 4706) | 27.6 % | 7.6 |
| (c) | 40.11 d, starvation (BMI 12.0) | 0.81 / 0.82 / 0.85 / 0.87 | 0.48 / 0.58 / 0.71 | 29.3 % | 2.6 |

- **The evidence:** Elia's 4.5 %-fat man gets 31 % of BMR from protein, and her curve gives about 23 % of TEE at 6.5 %.
  (a)'s 41 % over days 1-14 is high by about 1.3-1.8 times. HEAD's 85 % is high by about 2.7-3.7 times.
- **Death:** in every form the Gaunt body dies of starvation first, on the BMI branch. Fat runs out by about day 40 in
  (a) and (c), and S2241 dates the "catastrophic protein catabolism" to "when fat stocks are used up".

### What each form does to the science

- **(a) Forbes alone.**
  - Matches the measured protein-energy share at the default (13-17 %, Jackson, Benedict) and Obese (about 7 %) bodies,
    and the rates of weight loss (S0104, S2243).
  - Lets fat reach S1910's floor region, and lets the share rise toward the end-stage (S2241).
  - Needs no new constant: forbes_c is the published 10.4 (S1056, settled).
  - It overshoots at the Gaunt end, and Forbes's rise as fat falls runs against Elia's and Henry's "little change over a
    month" in lean subjects (default: 14 % → 22 % by days 30-45).
- **(b) Re-based density.**
  - Only fewer kilograms: the energy partition is unchanged, still about 50 % from protein.
  - It contradicts every measured fast, and rests on a density Alpert's paper could not be read for.
  - Its default body still ends fatter (19.1 %) than it started.
- **(c) Ceiling with a sparing term.**
  - With the sparing calibrated to 15 %, it approximates (a) in the default fast.
  - It adds an open constant and keeps a ceiling the fasting data contradict.
  - The only time-based sparing the evidence supports is in the obese (Elia, Owen 1969), where the ceiling does not
    bind early anyway.
  - In a fed deficit it would still pay the overflow above 69·fm by lean.

## 9. Recommendation: form (a)

**Drop Alpert's ceiling from the deficit arm, so Forbes's share (forbes_c = 10.4, S1056 settled in place) times the
existing training and protein protection partitions the whole deficit.**

The case:
1. Three independent measured fasts give a protein share of energy that Forbes plus Hall's densities reproduce at the
   default body's fat, and the ceiling cannot. These are Benedict 1915 (17.5 %), Jackson 2006 (13.0-17.1 %) and Elia
   1999's compilation (about 13 % of TEE at 20 % fat).
2. The ceiling's 69 kcal/kg/d is the Minnesota men's own fat flux under a moderate deficit (§ 4: 72 and 63 from Keys's
   Table 152). The register's own S1910 shows 111 kcal per kg of initial fat a day. As a hard limit it is contradicted.
3. Forbes needs no fit, which suits spec § 3.2's fit discipline: no new constant, nothing at a bound. Chow and Hall
   report that it matched under- and over-feeding data "without any adjustable parameters". It over-predicts lean loss in
   Minnesota (§ 6), so it does not flatter the fix.
4. The weight-loss checks move onto the evidence: 21 % by day 43 against 18 % (S2243) and 25.5 % (Jackson), and
   0.32 kg/d in week 3 against 0.3 (S0104).

**Predicted outcomes under (a)** (cause and day, spec § 3.3):

| body | first killer | day | lean weight share at death | fat % at death |
|---|---|---|---|---|
| default | wet beriberi | 77.21 | 0.60 | 7.4 |
| Obese | wet beriberi | 77.21 | 0.31 | 26.6 |
| Gaunt | starvation (BMI 12 branch) | 41.14 | 0.86 | 1.8 |

The default and Obese deaths are the thiamine clock, not the partition: wet beriberi falls on the same day in every
form. As spec § 6 rules, that stands as the science gives it. The default body would otherwise reach BMI 12 on day 90.

**Caveats for Task 5 and its review.**
- **The Gaunt fast.** (a)'s fat falls to about 0.63 kg by death (1.8 %), reaching the 0.5 kg floor near day 46. S1910 puts the male floor at
  about 2.5 kg, below which loss comes from FFM.
  - Forbes's share at fm 2.5 is 0.81 by weight, 45 % by energy, which gives roughly that end-stage.
  - The 0.5 kg floor is a separate constant (S1167 open) that this pass did not re-examine. **The fat floor stays** (fix round 1, review F10): raising `fmMin` to S1910's 2.5 kg would drop unpaid fat energy at the clamp (`NR_Kernel_Strength.lua:334`) instead of routing it to lean. Any S1910 shaping belongs inside `deficitLean`.
  - Forbes overshoots the very lean protein share by about 1.3-1.8 times early in the Gaunt fast; there are too few
    lean points in Elia's figure to fit a correction.
- **The disuse arm** (`Partition.lua:114`) keeps S0056 and is untouched by (a). Under immobilisation, fat pays up to the
  ceiling and the remainder is unpaid. The same evidence weakens S0056 there too, but that arm is a different model
  (the disuse curve stands in for the lean arm) and is out of scope.
- **Fed deficits.** (a) also applies outside a fast. Plan 13's strength oracles were fitted with the ceiling in the arm
  and must be re-scored (spec § 3.4). Plan 13's deficit-week cases sit at moderate deficits where the ceiling rarely
  bound for the default body, but that is to be measured, not assumed.
- **Time course in the lean.** Forbes's share rises as fat falls: the default's energy share goes 14 % → 22 % → 27 %
  over days 1-14, 30-45 and 45-60. Elia and Henry report little change over a month in lean subjects, and Benedict's
  17.5 % was flat over days 13-31. The rise is mild to day 30 and steeper after, where the end-stage (S2241) is real.
  Not a reason to add a term.

## 10. Register actions for the controller

**Part file** `.superpowers/sdd/2026-10-18-plan-16-pre-upload/fasting-science.tsv` (apply with
`python tools/science_delta.py apply`). Eleven rows after fix round 1, in file order (S1.12 removed, F3):

| row | what it holds |
|---|---|
| S1.1 | Elia 1999, Figure 2: the protein share of BMR against initial % fat (digitised) |
| S1.2 | Elia 1999: the protein share over time, lean against obese, and the fat share of energy |
| S1.3 | Elia 1999, Table 1: hypothetical lean and obese fasts to death |
| S1.4 | Henry 1988: P-ratio unchanged in normal subjects |
| S1.5 | Jackson 2006: 44-day fast in a non-obese man |
| S1.6 | Benedict 1915: Levanzin's losses and heat partition |
| S1.7 | Benedict 1915: urinary nitrogen over a 31-day fast (lean) |
| S1.8 | Owen 1969: urinary nitrogen over 5-6 weeks (obese) |
| S1.9 | Cahill and Owen 1968: nitrogen after several weeks against the no-adaptation need; the stores |
| S1.10 | Keys 1950, Table 152: body compartments at C, S12 and S24 |
| S1.11 | Keys 1950, Table 323: grip and back strength at C, S12, S24, R6 and R12 |

The part file carries no rows for Owen 1998, Alpert 1988 or Alpert 2005:
- **Owen 1998.** Its 7 % is quoted here for comparison only. A row can be added if Task 5 wants it.
- **Alpert 1988.** It goes in through the S0058 `settle` below.
- **Alpert 2005.** No new value was read; S0056 stays settled on its abstract.

**Settle S0058** (Alpert 1988, abstract read). Run from the repository root:

```
python tools/science_delta.py settle S0058 --topic body-composition --grade TXT --value "energy density of weight loss in semistarvation 4436 +/- 869 kcal/kg (18.57 +/- 3.60 MJ/kg), coefficient of variation 0.19 over the first 12 weeks; energy density of the lean body mass change declines over the period; protein loss 0.48 +/- 0.12 kg/wk initially and 0.12 +/- 0.03 kg/wk over the second 6 weeks; response time of the lean body mass decrease 64 +/- 2 days and of the fat store 135 +/- 4 days" --range "two-reservoir energy model; abstract read (full text not reached); the abstract does not name the dataset (most likely the Minnesota experiment, Keys 1950: an inference)" --population "semistarved adults as modelled by the two-reservoir model" --citation "Alpert SS 1988, Int J Obes 12:533-542; pmid:3235270"
```

**Settle S1056** (the Forbes and Hall coefficient). Its row asks for "the lean share of a surplus or a deficit as a
fitted coefficient of initial body fat". Chow and Hall 2008 give it as Forbes's 10.4 kg.

```
python tools/science_delta.py settle S1056 --topic body-composition --grade MODEL --value "Forbes's law F = D exp(L/10.4), L and F in kg (D a free parameter), so the phase-plane slope (rho_F/rho_L) dF/dL = alpha = (rho_F/rho_L)(F/10.4) and the p-ratio p = 1/(1 + alpha); with Forbes's law the two-compartment partition model matched a wide range of data without any adjustable parameters (Hall, Bain and Chow)" --range "model review; the coefficient is Forbes's, fitted by him to cross-sectional body-composition data; full text read" --population "adults (Forbes's cross-sectional data); not infants" --citation "Chow CC, Hall KD 2008, PLoS Comput Biol 4:e1000045; doi:10.1371/journal.pcbi.1000045; pmid:18369435"
```

**Delete the S1.12 line from the part file before `python tools/science_delta.py apply`.** S1056 is settled in place by the command above, which keeps the mod's existing `S1056` token at `NR_Kernel_Strength.lua:37` valid (superseding it would fail `science_check --scan mod`). Fix round 1 already removed S1.12 from the part file, which now holds S1.1-S1.11. Task 5's amendments requote `NR_Kernel_Strength.lua:37`'s `(S1056 open)` as settled.

**Supersede S0657** with S1.11. The monograph has no weekly series; Table 323 is its strength series. Run `status S0657
superseded --successor <S1.11's id>`. No mod file cites S0657.

**S1166 and S1167** stay open. This pass found no measured time from fat exhaustion to death and no female floor.

## 11. Not reached, and what stays open

- **Alpert 2005's lean energy density** (closed full text). Option (b) is judged on its energy share, which no density
  can fix (§ 8), so the gap does not block the recommendation.
- **Henry 1990** (no abstract, no open copy). Elia 1999's Figure 2 compiles the same group's data.
- **Elia 1992**, the Nestlé Foundation chapter behind Figures 1 and 2, was not sought. The figure was read from its 1999
  reprint.
- **No row gives a complication hazard from day 40 (S2236)** or the time from fat exhaustion to death (S1166). Spec § 6's
  game choice, death by whatever the science gives first, stands.
