# Sweat sodium adaptation: the harvest behind candidate C-14 (Plan 11f)

Harvester: claude-opus-5-5, 2026-10-10. Read-only. No tracked file was edited except this page and its part file,
`08-sweat-sodium-rows.tsv` (35 rows, provisional ids `S8.1`–`S8.35`; 32 settled, 3 open). No subagent ran.
`python tools/science_check.py --part` reads 0 findings on the part file.

**The defect (ruling 5b-5).** In the mod, a character's sweat sodium concentration is drawn once and never changes.
A salt-depleted heavy worker therefore keeps losing about 296 mmol/d in sweat. Fix 2's heat arm died at 2.4 times
McCance's total loss. In real bodies, sweat sodium concentration falls under a sodium deficit (aldosterone) and with
heat acclimatisation. This harvest prices that fall.

**How the records were resolved.**
- Every settled row's record was resolved through Europe PMC: title, first author, year, journal, volume, pages,
  PMID and DOI matched.
- McCance 1936 has no PMID. It was resolved through Crossref (S1728's record), and its full text is the copy named in
  `07-thirst-volume.md`.
- IOM 2005 chapter 6 was read from the NAP reader. The page numbers come from the reader's page anchors.

**Where the values came from.**
- Full text was read for:
  - Baker 2019 (PMC6773238): text, Table 1 and Table 5;
  - Baker 2017 (PMC5371639);
  - Mikkelsen 2019 (PMC6843002), with Table 2;
  - Cubel 2024 (PMC11583594);
  - Cage & Dobson 1965 (JCI PDF);
  - Locke 1951 (JCI PDF);
  - McCance 1936;
  - IOM 2005 chapter 6.
- For Chinevere 2008, Kirby & Convertino 1986, Buono 2007, Buono 2008, Buono 2018, Allsopp 1998, McCubbin 2019,
  Armstrong 1985, Klous 2020 and Baker 2022, the values come from the abstract; each row's `range` cell says so.

**Primaries that could not be read.** Several primaries were read only as Baker 2019 Table 5 or IOM 2005 restates
them. Each such row cites the restating source and is graded by it (`TXT` or `AUTH`):
- Allan & Wilson 1971, Robinson 1950/1955/1956, Kirby & Convertino 1986 and Weiner & Van Heyningen 1952 (J Appl
  Physiol) are behind journals.physiology.org's bot wall.
- McCance 1938 (J Physiol, PMC1395172) is a scan behind PMC's proof-of-work page.
- Allsopp 1998, Armstrong 1985 and McCubbin 2019 are Springer paywalls.
- Conn 1946-1949 has no indexed abstract.

**Grades.**
- A controlled crossover in the same subjects is `RCT`: McCubbin 2019 (double-blind randomised) and Armstrong 1985
  (two 8-day diets in the same nine men, order not stated).
- Allsopp 1998 is `RCT` as an inpatient controlled trial: men confined to a chamber on controlled intakes in three
  parallel groups. The allocation method is not stated.
- A pre-post acclimation series with no control arm is `EXP`: Chinevere, Kirby, Buono 2007 and 2018, Klous.
- Mikkelsen 2019 and Cubel 2024 are `EXP` for the sweat-sodium reading. Mikkelsen is a randomised trial, but sweat
  sodium was followed in the heat arm only, so the reading is within-arm. Cubel's sweat-sodium change is also
  within-arm, and its allocation is not stated.
- Cage & Dobson, Locke and McCance 1936 are `EXP`.
- Baker 2022 is `COH`, IOM 2005 is `AUTH`, and the Baker reviews are `TXT`.

**Within-arm against between-arm.** Every row's `range` cell says which it is.
- Most acclimation numbers are within-arm, day 1 against day 10.
- The diet contrasts are between-arm in crossovers: Armstrong, Hargreaves, McCubbin, Konikoff, Hamouti, Koenders.
- McCance 1938, Weiner and Komives are within-subject over time under a deficit.

**Id mapping.** A dry run of `science_delta.py apply` passes and would mint `S8.n → S(1738+n)`
(S8.1 → S1739 … S8.35 → S1773) on today's register. The mapping holds only if nothing else is minted first. This page
uses the provisional ids.

**Open rows this harvest touches.**
- **S0569** (open: "change in sweat sodium concentration with heat acclimation … settled by an acclimation study
  reporting sweat sodium before and after") is answered by S8.1 (Chinevere 54.49 to 36.22 mM) and S8.8 (Baker's
  30-60 %). The controller may supersede S0569 by S8.8, or by S8.1 for a primary.
- **S1171**, named in the brief, is not a sweat row. It is "the time from severe hyponatraemia to death without
  treatment" (Plan 5 ruling 13). This harvest does not touch it. The heat arm's death timing still rests on it.

---

## 1. The mod's sweat sodium today

**The constants and the draw.**
- `NR_Kernel_Fluids.lua:45`: `NA_SWEAT_MEAN = 37`, which is 55.9 mmol/h / 1.51 L/h (S0394 / S0090).
- `:46-49`: `NA_SWEAT_RANGE = {10, 90}` (S0518).
- `:109-112`: `naSweatOf(r) = 10 + 80 r²`, a per-character draw with mean 36.7.
- `NR_Server_Nutrients.lua:224-227` draws it once, in `ensure`, at record creation:
  `K.fluids.naSweatOf(roll(math.sqrt(27 / 80)))`.
- `K.fluids.new` stores it as `f.naSweat` (`:123-129`), and the store persists it (`NR_Kernel_Store.lua:97`,
  `"fluids.naSweat"`).

**The sweat rate.** `K.fluids.sweatLh` (`:159-163`):

    x = clamp((met - SWEAT_MET_LO) / (SWEAT_MET_HI - SWEAT_MET_LO), 0, SWEAT_CAP)   -- 3, 8, 1.5
    sweat L/h = SWEAT_LH (1.0) * x * thermoFluids * sweatK

**The loss.** `K.fluids.losses` (`:170-188`), at `:181`:

    f.na = f.na - sweatL * f.naSweat

- The concentration is a constant per character. Nothing reads `f.na` (the sodium balance, mmol against baseline),
  the sweat rate, the diet or any exposure history into it.
- The renal side does conserve. `clearance` (`:191-196`) removes only a surplus, and the comment at `:65` reads "a
  deficit is conserved". Only the sweat side never adapts.
- At the mean draw, 296 mmol/d is about 8.0 L/d of sweat (derivation: 296 / 37).

## 2. Heat acclimatisation

**S8.1, Chinevere 2008 (EXP, abstract).** "Sweat sodium concentration on day 10 (36.22 +/- 7.22 mM) was
significantly lower than day 1 (54.49 +/- 16.18 mM) (P < 0.05)". The setting was 10 days at 45 C, arm-bag sweat, and
sweat rate rose about 6 % (P = 0.12).

**S8.2, Kirby & Convertino 1986 (EXP, abstract, direction).** "the concentration and total content of sodium in
sweat as well as plasma aldosterone were significantly decreased from day 1 to day 10". The ratio of reabsorbed
sodium to aldosterone rose, so the gland grew more sensitive to aldosterone. IOM Table 6-3 (S8.20) tabulates the
concentrations: day 1 75-100, day 10 40-45 mmol/L.

**S8.3, Buono 2007 (EXP, abstract).** After 10 days, the y-intercept of the sweat sodium against sweat rate relation
fell "by ... 15 mmol/l". "the slopes of the relationships were not affected".

**S8.4, Buono 2018 (EXP, abstract, n = 4).**
- A significant downward shift appeared "on days 3, 5, and 7".
- "The response was very rapid and occurred following only 2 consecutive days of heat exposure (i.e., day 3 vs. day
  1 data)".
- Sweat sodium at a fixed rate "decreased linearly (r = - 0.50, p < 0.05) during the 7 days".

**S8.5, Mikkelsen 2019 (EXP within the heat arm, Table 2).** Weekly back-patch sweat sodium, mmol/L, mean +/- SE:

| first session | end wk 1 | end wk 2 | end wk 3 | end wk 4 | end wk 5 |
|---|---|---|---|---|---|
| 93 +/- 5 | 74 +/- 5 | 71 +/- 6 | 69 +/- 7 | 72 +/- 7 | 79 +/- 6 |

- The text says "leveling off after 2-3 weeks". Its "46 +/- 14%, from 91 +/- 5 … to 69 +/- 8 mmol/L" does not
  match Table 2's 93 as printed.
- The first week was 3 sessions at 35 C. By the end of it, (93 - 74) / (93 - 69) ≈ 0.79 of the week-3 drop had
  happened (derivation).

**S8.6, Cubel 2024 (EXP within-arm).**
- Sweat sodium fell "by 14.1 mmol/L (p = 0.006)" (17 +/- 12 %) over 5 weeks. The first week's fall was not
  significant.
- In the control arm, sweat sodium did not change (p = 0.279).
- **Decay:** "At the 2-week evaluation of decay, sweat sodium concentration [Na+] remained significantly lower than
  pre-HA (p = 0.025) and was not significantly different from post-HA". Sweat rate and performance had already
  returned to baseline.

**S8.7, Klous 2020 (EXP, pilot).** Sweat sodium, chloride and lactate fell "arm 25-34; back 21-27%" after 10 days
of heat acclimation.

**S8.8, Baker 2019 (TXT).**
- "the reported decrease in sweat [Na] and [Cl] after ~10 days of heat acclimation ranges from ~30% to 60%".
- "Na conservation may begin after just two consecutive days of heat exposure and sweat [Na] decreases linearly over
  time".
- The fall occurs "despite increases in sweating rate".

**S8.20, IOM 2005 Table 6-3 (AUTH, pp. 278-279).**
- Allan & Wilson 1971 (3 subjects, unacclimated and acclimated, 3 wk): "10-58" mmol/L.
- Kirby & Convertino: "Day 1:75-100", "Day 10:40-45".
- Consolazio 1963: "49-180".
- Inoue 1999: "45-60".
- Meyer 1992: "35-55".
- Allsopp 1998: losses of 50 / 78 / 105 mmol/d at 66 / 174 / 348 mmol/d intake.

**S8.23, IOM 2005 pp. 296-298 (AUTH).**
- "The amount of sodium lost in sweat is less in those acclimatized to the heat than in those who are not".
- "sweat sodium concentration averages about 35 mmol/L, with a range from 10 to 70 mmol/L".
- Consolazio's daily sweat sodium losses "fell from 487 mmol (11.2 g)/day (day 1) to 71 mmol (1.64 g)/day (day
  11)". The intake was 378 mmol/d (Table 6-3), below the day-1 sweat loss of 487 mmol/d, so a deficit early in the
  series is not excluded; the balance is not given.

## 3. Dietary sodium

**S8.18, McCubbin 2019 (RCT, double-blind crossover, abstract).** After 3 days at about 15 / 46 / 100 mg/kg/d of
sodium:
- "Estimated whole-body sweat [Na+] following UDiet was 10-11% higher than LNa and 10-12% lower than HNa
  (p < 0.001)".
- Sweat sodium "correlated with pre-exercise aldosterone (1st h r = - 0.568, 2nd h r = - 0.675; p < 0.01)".

**S8.16, Hargreaves 1989 (via Baker 2019 Table 5, TXT).** After 2 weeks at 50 against 150 mmol/d:
- whole-body sweat "38 mM Na" against "50 mM Na**";
- sweat rate 1.12 against 1.15 L/h (NS);
- loss 41 against 55 mmol/h.

The abstract adds that renin and aldosterone "were elevated after 2 weeks on the reduced salt intake".

**S8.21, IOM p. 308 (AUTH, Allsopp 1998).** At 66 mmol/d, "4.5 mmol (0.1 g) of sodium per hour was lost in sweat
during heat exposure prior to acclimation. After 5 days of acclimation, average sodium sweat losses dropped to 2.1
mmol (0.05 g)/hour".

**S8.24, Baker 2017 (TXT).**
- "compared with moderate Na+ intake (3-4 g/day), 8-14 days of high (8-9 g/day) or low (1-2 g/day) Na+ intake are
  associated with significant increases … or decreases … in sweat [Na+]".
- Sweat sodium varies "approximately … 15% day-to-day" within a person.

**S8.19, short or modest manipulations (Baker 2019 Table 5, TXT).**
- Konikoff, 3 days of +10.2 g/d NaCl: 31 against 26 mM Na (NS).
- Hamouti, sodium 1.5 h before exercise: 36 / 39 / 38 mM (NS).
- Koenders, 9 days at 58.6 against 165.1 mmol/d: 55 against 55 mM (NS).
- Costa, 6 weeks at 5.6 (Space diet) against 3.4 g/d (Formula diet), parallel groups, no statistics reported: whole
  body 21 against 17 mM.
- Table 1: "shorter duration (<=3 days) of Na manipulation has minimal or no impact".

**S8.25, Baker 2022 (COH).** Across 1,944 sweat tests, dietary sodium intake had no significant effect. "season of
the year (proxy for heat acclimatization)" and energy expenditure were the main predictors. The data are
between-person, so they do not test a within-person change of diet.

## 4. The deficit as the driver

This section answers the question in the brief: does a total-body sodium deficit itself, not the diet, lower sweat
sodium?

**For.**
- **S8.9, Baker 2019:** "the presence of a salt deficit is required for NaCl conservation to occur with heat
  acclimation. In studies where subjects consumed enough NaCl to replace losses … sweat [Na] and [Cl] did not change
  or increased slightly". The mechanism is "increased sensitivity of the sweat gland to circulating aldosterone".
- **S8.11, McCance 1938 (Baker Table 5).** Two men, crossover, repeated passive heat:
  - under deficiency, sweat went "72 to 33 mM Na" in 5-8 days, and the loss went 162 to 73 mmol;
  - on generous salt, sweat went "62 to 70 mM Na".
- **S8.12, Armstrong 1985 (Baker Table 5)** and **S8.15 (its abstract, RCT crossover)**, over 8 days of heat
  acclimation:
  - at 98 mmol/d, sweat went "45 to 26 mM Na*" and whole-body sodium "decreased 7.8% (-230.4 mmol)";
  - at 399 mmol/d, sweat went "41 to 56 mM Na* **" and whole-body sodium "increased 31.1% (+916.8 mmol)";
  - sweat rate did not differ.

  Acclimation in positive balance raised sweat sodium.
- **S8.13, Weiner & Van Heyningen 1952 (n = 1):**
  - week 1 at 300 mmol/d Cl: sweat "35 to 40 mM Cl";
  - week 2 at 16 mmol/d Cl: "40 to 13 mM Cl".
- **S8.14, Robinson 1956.** Euhydrated with 169 mmol Cl depleted, sweat went "28 to 17 mM Cl; decline started at 14 h
  and continued thru 25 h". With salt balance maintained it went only 25 to 21.
- **S8.29, McCance 1936 p. 245:** "E. ceased to lose significant amounts of NaCl in her sweat after 4 or 5 days".
  - R.A.M.'s per-bath sweat sodium (S1728) fell: 2680, 3000, 2500, 1900, 880 mg on days 2, 3, 5, 8 and 10.
  - No bath volume is tabulated, so no concentration can be read. The one bath record gives a 2150 g weight loss with
    800 cc drunk (p. 247), with no day number.
- **S8.30, Locke 1951 p. 336.** The sweat chloride-rate index falls on low-salt diets, high potassium or repeated heat
  and rises on high salt. "no significant changes in index values took place in a hypoadrenocortical patient when
  the salt intake was varied". The response needs "functionally intact adrenal cortices"; that the hormone is
  aldosterone is our gloss, since Locke 1951 predates its isolation.

**Against, or weaker.**
- **S8.17, Allsopp 1998 (abstract):** "a reduction (P < 0.01) in sweat sodium secretion for all three conditions";
  "These findings are inconsistent with the hypothesis that retention of sweat sodium is dependent upon a net body
  sodium deficit".
  - The high group was in positive balance (+14.7 mmol, S1669).
  - Baker notes the groups were not matched at baseline.
- **S8.1, S8.5, S8.6, S8.7.** The acclimation studies on free diets also show falls. Their sodium balance is unknown:
  heavy sweating on a free diet can run a deficit.

**Time course of the gland's response.**
- **S8.10, Baker 2019, restating Robinson:** "while the renal system responds to a salt deficiency or excess within
  1-3 h, the sweat glands typically require 1-4 days". The conclusions say "somewhat delayed (1-3 days)".
- **S8.35 (TXT), Cage & Dobson 1965 restating Conn 1963 and McConahay 1964:** "sodium concentration of sweat has not been
  shown to change until about 12 hours after the beginning of an acclimatizing stress"; "At least 5 hours of
  continuous intravenous administration of aldosterone is necessary".
- **Robinson 1956 (S8.14):** the decline started at 14 h.

**S8.22, IOM p. 277 (AUTH), Conn 1949.**
- "This reduction in sweat sodium concentration is a protective mechanism to minimize plasma volume loss".
- People "sweating 5 to 9 L/day could maintain sodium chloride balance on intakes ranging from as low as 1.9 g
  (83 mmol)/day to 3.2 g (139 mmol)/day". The units are as printed: 83 mmol is 1.9 g of sodium.

## 5. The floor

These are the lowest concentrations read under a deficit or acclimatisation, with the ratio to each arm's own start
(derivation: end / start):

| source | start → end | ratio | ion | days |
|---|---|---|---|---|
| Komives 1966 (S8.31) | 50 → 15 mM | 0.30 | Cl | days 8-13 of deficiency |
| Weiner 1952 (S8.13) | 40 → 13 mM | 0.33 | Cl | week 2 at 16 mmol/d |
| McCance 1938 (S8.11) | 72 → 33 mM | 0.46 | Na | 5-8 days of deficiency |
| Armstrong 1985 (S8.12) | 45 → 26 mM | 0.58 | Na | 8 days, low Na + heat |
| Robinson 1956 (S8.14) | 28 → 17 mM | 0.61 | Cl | 25 h, 169 mmol depleted |
| Kirby 1986 (S8.20) | 75-100 → 40-45 | 0.40-0.60 | Na | 10 days heat |
| Chinevere 2008 (S8.1) | 54.49 → 36.22 | 0.66 | Na | 10 days heat |
| Hargreaves 1989 (S8.16) | 50 vs 38 | 0.76 | Na | 2 weeks low diet (between-arm) |

**Absolute low ends.**
- Allan & Wilson 1971 reached 10 mmol/L (S8.20).
- The regional range starts at 10 (S0518, S8.27).
- At low sweat rates the forehead reads "as low as 10 to 20" (S8.28).

**Conn's balance as a check (derivation).** Balance on 83-139 mmol/d while sweating 5-9 L/d (S8.22) bounds sweat
sodium at or below 139 / 5 ≈ 27.8 mmol/L, and at 9 L/d at or below 139 / 9 ≈ 15.4 mmol/L. This ignores urine, so it
is an upper bound. It assumes IOM's mmol figures. If the "g … of sodium chloride" reading is the right one, 3.2 g NaCl
is about 55 mmol of sodium, and the bound falls to about 11 and 6 mmol/L.

**Chloride as a proxy.** Chloride tracks sodium almost exactly (S0518), so the chloride ratios (0.30, 0.33) are read
as the sodium floor.

## 6. Sweat rate

**Within a person, concentration rises with rate.**
- **S8.26, Buono 2008:** r = 0.73; secretion rises faster than reabsorption ("slope = 141 vs. 80").
- **S8.27, Baker 2019:** from forearm rate 0.25 to 0.82 mg/cm²/min, sweat went "19 +/- 5 to 59 +/- 10 mmol/L"; the
  reabsorbed share went from "86 +/- 3%" to "65 +/- 6%"; Fig. 6's fit is "y = 59.7(x)+6.7". "According to some
  studies, there may be" a threshold of "~0.3 mg/cm2/min … ~0.3 L/h" below which concentration does not rise.
- **S8.28, Cage & Dobson:** 10-20 to over 100 mEq/L on the same forehead.

**Between people, rate does not predict concentration.** Baker 2018 found no whole-body relation between people
(S8.27).

**Acclimation shifts the line down without changing its slope** (S8.3: intercept −15 mmol/L), even as the sweat rate
rises (S8.8).

**For the mod.** The mod's per-character draw already carries the between-person spread. A within-person rate term
would raise a heavy worker's concentration, the opposite direction to C-14, so it is not part of this fix. The rows
are here for a later candidate.

## 7. What the adaptation's constants would be

Every number below is computed from the rows above and labelled as a derivation. The shape of the curve is a game
choice.

**The driver: the deficit, read from `f.na`.**
- The rows that hold diet and acclimation apart (S8.9, S8.11, S8.12/S8.15, S8.13, S8.14) show the fall under a
  deficit and its absence or reversal in positive balance.
- The mod already stores that deficit as `f.na` (mmol against baseline). This needs no new stored field.
- The cost: Allsopp's high group and the free-diet acclimation studies (Mikkelsen, Cubel, Chinevere, Klous) show
  some fall without a known deficit. A deficit-only model will under-adapt a well-fed acclimatising worker. In the
  C-14 case, a salt-depleted worker, it errs on the safe side.

**The form:**

    deficit = max(-f.na, 0)                                          -- mmol
    r       = clamp(deficit / NA_SWEAT_DEF_FULL, 0, 1)
    naEff   = max(f.naSweat * (1 - (1 - NA_SWEAT_MIN_FRAC) * r), NA_SWEAT_ABS_MIN)
    f.na    = f.na - sweatL * naEff                                   -- replacing :181

`f.naSweat` stays the drawn baseline. The between-person spread survives, since acclimation shifts the line rather
than resetting it (S8.3).

**`NA_SWEAT_MIN_FRAC` ≈ 0.33.**
- This is the median of the three deficit arms of 5-13 days: Komives 0.30 (15/50), Weiner 0.325 (13/40, shown as
  0.33) and McCance 1938 0.46 (33/72) (derivation). Two of the three are chloride ratios. None of the three reports
  statistics (Baker Table 5 footnote), the arms have n = 1, 4 and 2, and none measured the deficit.
  The other arms were milder (Armstrong 0.58, 8 days at 98 mmol/d) or shorter (Robinson 0.61 at 25 h). Whether they
  had reached a floor is not known.
- At the mod's mean draw it gives 37 × 0.325 ≈ 12.0 mmol/L (derivation). That is within Conn's ≤ 15-28 mmol/L bound
  and above the absolute low end of 10.
- The heavy worker's 296 mmol/d falls to about 96 mmol/d (derivation: 296 × 0.325).
- **The alternative is 0.46** (McCance 1938, the one sodium floor). It reads only sodium values. It is weaker: two
  men, 5-8 days, the primary not read.

**`NA_SWEAT_DEF_FULL` ≈ 330 mmol.**
- The two arms with both a deficit and a ratio are Robinson 1956 (169 mmol, 0.607) and Armstrong 1985 (230.4 mmol,
  0.578). Their means are 199.7 mmol and 0.5925. Robinson's are a chloride depletion and a chloride ratio, read here as
  sodium proxies (S0518). Armstrong's ratio includes 8 days of heat acclimation, and its deficit is the whole-body
  sodium change over those 8 days.
- A line from (0, 1) through that mean has a slope of 0.00204 per mmol and reaches the 0.325 floor at about
  331 mmol (derivation). The (0, 1) anchor and the straight line are game choices, not a fit to a dose-response
  (open row S8.32).
- For an 80-kg body this sits above `DEFEND_ONSET` (0.08 × 16 L ECF ≈ 179 mmol, derivation from `:286` and
  `ECF_PER_KG`). Sweat conservation then starts before the volume defence does. Robinson's 14 h onset at a deficit
  below that onset agrees.
- **Do not ride `K.fluids.defence`.** It is 0 below DEFEND_ONSET, which would contradict Robinson's fall at a
  169 mmol deficit.

**`NA_SWEAT_ABS_MIN` = 10 mmol/L** is a game choice. It rests on the low end of S0518's regional range and of Allan
& Wilson's 10-58 mmol/L in IOM Table 6-3 (S8.20), a range that pools unacclimated and acclimated values. It is not a
measured floor. This keeps a low-drawn character (10) from going to 3.

**The time constant: none stored, and the lag comes from the deficit itself.**
- The rows give a gland lag of about 12-14 h to onset (S8.35, S8.14) and 1-4 days to the effect (S8.10). Buono 2018
  saw it after 2 days (S8.4). Mikkelsen had about 79 % of the drop within the first week (S8.5; derivation from
  Table 2 means, (93 - 74) / (93 - 69)).
- `f.na` is an integrator. At 296 mmol/d, a 169 mmol deficit builds in about 13.7 h (derivation: 169 / 296 × 24), and
  the full 331 mmol in about 27 h. This reproduces the 12-14 h onset and the 1-4-day span without a stored lag.
- A diet-only deficit builds more slowly, as Armstrong's 230 mmol over 8 days did, so the response is slower there,
  as S8.19's ≤3-day nulls show.
- If a true first-order lag were wanted, it needs one stored field. The rows put its time constant in days
  (S8.10 1-4 d; S8.5 most of the drop in week 1).

**Recovery.**
- When intake repays `f.na`, `naEff` returns to the draw along the same ramp.
- No row gives the sweat-side recovery time (open row S8.33).
- Cubel's acclimation decay (still lower 2 weeks after stopping, S8.6) concerns acclimation, not deficit. A
  deficit-only model recovers faster than an acclimated gland would.

**Acclimatisation without a deficit would need a new field.**
- The existing `sweat6h` EMA has a 6 h window (`EMA_MIN = 360`). It cannot hold an exposure history of days to weeks
  (onset 2-7 days, S8.4/S8.5; decay over 2 weeks, S8.6).
- A separate acclimation term, worth −15 mmol/L at a given rate (S8.3) or 17-30 % (S8.6, S8.8), would need a stored
  exposure EMA. This harvest recommends the deficit-only form for C-14 and leaves acclimation as a later candidate.

**What a test can check (derivations for an oracle).**
- With `f.na = 0`, `naEff = f.naSweat`, which is today's behaviour, so a fed character's golden trace is unmoved.
- At a 200 mmol deficit, `naEff / naSweat` ≈ 0.59, against Robinson 0.61 and Armstrong 0.58.
- Past about 331 mmol, `naEff / naSweat` = 0.325, against Weiner 0.33 and Komives 0.30.
- McCance 1936's subjects lost 765 and 980 mEq over 11 days (S1730), with sweat 10,960 mg ≈ 476.5 mmol for R.A.M.
  (derivation: / 23). A heat-arm replay can compare its cumulative sweat sodium against that figure. No sweat volume
  was tabulated, so the comparison is of totals, not of concentrations.

## 8. What could not be found

- **S8.32, open:** whole-body sweat sodium as a graded function of the deficit's size. Only single pairs were read.
  `NA_SWEAT_DEF_FULL` is therefore a two-point line, not a fitted dose-response.
- **S8.33, open:** the time course of sweat sodium recovery after a deficit is repaid.
- **S8.34, open:** daily sweat sodium from the first day of a salt-free diet. The primaries (Robinson 1950/1955,
  Conn 1946-1949, Allan & Wilson 1971) were reachable only as Baker 2019 and IOM 2005 restate them.
- McCance 1936 gives no sweat volume, so no concentration series could be read from S1728. Its Table VIII sweat column
  is mg per bath.
- The Buono 2018 and Kirby 1986 day-by-day concentrations, and the Allsopp 1998 concentrations, are in figures or
  tables behind paywalls or bot walls. Only the abstracts and IOM's tabulation were read. Baker 2019 Table 5 does
  tabulate Allsopp's final sweat sodium loss ("54 to 25", "64 to 39", "79 to 53 mmol Na"), with concentration NA.
- Knochel 1972 (JCI, read) reports sweat Na/K ratios only, not concentrations. No row was taken.
