# Hormone and hunger time courses after meals of known size and composition (Plan 11g Task 1, harvest 11)

Harvester: claude-opus-5-5, 2026-10-12. No tracked file was edited except this page and its part file,
`11-rows.tsv` (41 rows, ids S1799–S1839 from the reserved block S1799–S1858; 40 settled, 1 open). No subagent ran.
`python tools/science_check.py --part 11-rows.tsv` reads 0 findings.

**The question.** The satiety model is replacing the meal pool P (fed in full at the eat, half-life 0.7 game h)
with a gut stage G fed by what the stomach empties each minute. This harvest collects the gut-hormone (CCK,
PYY, GLP-1, ghrelin) and hunger time courses over 0–6 h after meals of stated size and composition. It answers
three questions: one post-absorptive phase in hunger or two; the apparent half-time of each; and which
macronutrient contrasts are robust and which are null.

**How the records were resolved.**
- Every row's record was resolved through the Europe PMC REST API: title, first author, year, journal, volume,
  pages, PMID and DOI matched. The citation cell carries the record as `doi:` and `pmid:`.
- One row (S1811) is a medRxiv preprint. Europe PMC indexes it as a preprint (PPR1289701), with the DOI in the
  citation; it has no PMID and was not peer reviewed. Its `range` cell says so.

**Where the values came from.**
- Full text was read (PubMed Central HTML) for:
  - Steinert 2017 (sections III.B, IV.A–B, V.B–C, VI.B);
  - Foster-Schubert 2008 (Methods, Results, Table 1, Table 3, Figure 3 legend, Discussion);
  - Lewis 2015 (Methods, Results, Figures 3 and 5 legends);
  - van der Klaauw 2013 (Methods, Table 2, Results, Figure 1 legend);
  - Giezenaar 2018 (Tables 1 and 2, Results);
  - Tieken 2007 (Methods, Table 2, Results);
  - Diekmann 2026 (Methods, Table 2, Results, Discussion);
  - Wyatt 2021 (Methods, Table 1, Results).
- The Parastika 2026 preprint was read from the medRxiv PDF (abstract, Methods 2.3, Results 3.3).
- For Liddle 1985, Adrian 1985, Elliott 1993, le Roux 2005 and 2006, de Graaf 1992, Gibbons 2013 and 2016,
  Belza 2013, Blom 2006, Smeets 2008, Batterham 2006, Rolls 1991, Juvonen 2009 and 2011, Karhunen 2010,
  Martens 2011, Santangelo 1998 and Sepple & Read 1989, the values come from the abstract; each row's `range`
  cell says so.

**Grades.**
- A controlled crossover in the same subjects is `RCT`, whether or not the abstract names the allocation (the 11f
  precedent). This covers Foster-Schubert, Lewis, van der Klaauw, Belza, Blom, Smeets, Giezenaar, Tieken,
  Martens, Santangelo, Juvonen 2009 and 2011, Karhunen, Diekmann, Gibbons 2016, de Graaf and the Parastika
  preprint.
- A single-meal hormone study whose abstract states no within-subject design is `EXP`: Liddle, Adrian, Elliott,
  le Roux 2005 and 2006, Gibbons 2013, Batterham 2006 (human part), Rolls 1991 and Sepple & Read.
- Wyatt 2021 is `COH` (an observational analysis inside a feeding cohort). Steinert 2017 is `TXT`.

**Rows already in the register, cited and not duplicated.**
- S1247: Callahan 2004, the meal-request interval and the ghrelin nadir by preload energy.
- S1248: Cummings 2004, the intermeal interval.
- S1279: Cummings 2001, the diurnal intermeal ghrelin.
- S1225: Raben 2003, the macronutrient null over 5 h.
- S1222 and S1379: Kohanmoo 2020, the pooled protein appetite and hormone differences.
- S1386: Hall 2003, whey against casein.
- S1235: Goetze 2007, isovolumic fat, protein and glucose meals.
- S1474: Stribiţcaia, liquid against solid.
- S1224: Marmonier 2000. S1228: Melanson 1999.
- S0131 and S1243: Hunt's caloric emptying rate and its macronutrient slowing.
- Two open rows this harvest speaks to but does not close: S1270 (the half-life of post-absorptive satiety) and
  S1268 (per-kcal satiety weights by macronutrient). § 7 gives the derivations, labelled as inference.

## 1. Hormone kinetics

- **Ghrelin** falls after a meal and rises gradually until the next. Its plasma half-life is about 30 min, so
  its postprandial course mostly reflects inhibited secretion (Steinert 2017, S1799).
  - The nadir comes 99 min after a carbohydrate drink, 186 min after protein and 169 min after lipid, all 500
    kcal-class (Foster-Schubert, S1812).
  - It comes at 60 min after a 540 kcal meal replacement (Tieken, S1834).
  - It falls to 2 h and then rises over 2–6 h after a ~1,000 kcal meal (Diekmann, S1827).
- **CCK** rises within 10–15 min (S1800, S1803). After 1,470–1,600 kcal mixed meals it reaches about 3 pM at
  30 min and 5–7 pM at 60–90 min (S1800).
  - It peaks at 62 min after a solid-liquid meal and at 94 min after the same meal homogenised (Santangelo,
    S1836; not significant).
  - After 120 kcal of whey it is back to control by 180 min; after 280 kcal it is still raised at 180 min (5.3
    against 3.1 pmol/L; Giezenaar, S1824).
  - In the same subjects the stomach had emptied 98–100 % of the 120 kcal drink by 180 min, but only 75–86 % of
    the 280 kcal drink (S1825).
- **GLP-1** after carbohydrate starts at 5–15 min, peaks at 15–30 min and is back to baseline by 3–4 h (S1801).
  - Protein and lipid give slower, more sustained rises; mixed meals sometimes give a second peak at 60–120 min
    (S1801).
  - After equicaloric 375 kcal loads it peaks at 30 min after carbohydrate and 150 min after fat (Elliott, S1805).
- **PYY** starts at 15–30 min and peaks at 60–90 min. It stays raised for several hours, so morning fasting
  levels come only hours after an evening meal (S1802, S1804).
  - It is still above baseline 6 h after a ~1,000 kcal meal (Diekmann, S1827).

## 2. Meal size

- Ghrelin suppression deepens with meal energy:
  - Callahan's nadir is 80, 73 and 61 % of baseline at 7.5, 16 and 33 % of daily expenditure (S1247, in the
    register);
  - le Roux 2005 reports it over 250–3,000 kcal (S1806).
- PYY rises in grades with meal energy (R² = 0.96; le Roux 2006, S1807).
- **Lewis 2015 (S1808, S1809)** cut a mixed solid breakfast of about 790 kcal (men) or 610 kcal (women) by 20 %
  and by 40 % (derived: kJ / 4.184).
  - The 40 % cut lowered PYY at 120 and 240 min and GLP-1 at every time point.
  - It raised hunger at every time point from 30 to 240 min.
  - The 20 % cut did neither: there was no condition-by-time interaction for PYY, GLP-1 or hunger.
  - Lunch intake at 240 min did not differ.
- de Graaf 1992 (S1810): appetite ratings fell with energy across 100, 250 and 400 kcal liquid breakfasts, with
  no macronutrient difference and no effect on later intake.
- Parastika 2026 (S1811, a preprint): across 0, 600, 900 and 1,200 kcal drinks, hunger iAUC over 0–3 h fell as
  preload energy rose, and acyl ghrelin fell in grades. The values are in figures only.

**Robust:** meal size moves every hormone and hunger in a graded way. The hunger difference is detectable at
about a 40 % step (about 245–315 kcal) and not at a 20 % step (about 120–160 kcal) (Lewis; derived: kJ step / 4.184, men and women).

## 3. Macronutrient at equal energy

**Protein.**
- **Hormones (robust).** Protein raised PYY and GLP-1:
  - van der Klaauw, S1817;
  - Belza, dose-dependent: +20 % GLP-1 and +14 % PYY3-36 at 50 % against 14 % protein energy (S1819);
  - Batterham 2006, S1823;
  - Giezenaar, at 60 and 180 min (S1824).
  It lowered ghrelin for longer: the largest decremental AUC in Foster-Schubert (S1812), and Blom 2006 (S1821).
- **Hunger (mixed).**
  - Positive: Belza −25 % hunger at 50 % protein (S1820); Smeets satiety AUC 263 against 236 mm·h (S1822);
    Giezenaar load-dependent in men only (S1826); the pooled S1222.
  - Null: van der Klaauw (n = 8, S1818), Blom (n = 15, S1821), Foster-Schubert (S1814), Raben (S1225).
  - Blom also slowed gastric emptying with protein (S1821). Some of protein's effect is therefore already in
    the mod's stomach (S1243).

**Fat against carbohydrate.**
- **Hormones (robust).** Fat raised CCK faster and higher (Gibbons 2016, S1816) and raised PYY and GLP-1 more
  (Gibbons 2013, S1815; Diekmann PYY iAUC +8,600 min·pg/mL, S1827).
- **Ghrelin.** Fat suppressed ghrelin least: 21 % against 30 % for carbohydrate (Foster-Schubert, S1812).
- **Hunger (null or reversed).**
  - No difference in hunger or fullness: Gibbons 2016 (S1816), Rolls 1991 at 30, 90 and 180 min (S1830),
    de Graaf (S1810), van der Klaauw (S1818).
  - Diekmann found *more* hunger after the high-fat meal (S1828). That contrast is confounded by 4.6 g more fibre
    in the low-fat meal.

**Carbohydrate's late phase.**
- After a glucose-based drink, acyl ghrelin rebounded to 37 % above baseline in hours 3–6 (Foster-Schubert,
  S1813). Hunger ratings did not differ (S1814; the authors flag VAS problems).
- In 1,070 free-living adults, a larger glucose dip at 2–3 h went with more hunger at 2–3 h (+9 %, largest
  against smallest quartile) and a shorter time to the next meal (−24 min). The correlations are weak, r about
  0.15 (Wyatt, S1829).
- This is a real but small late effect. A first-order G cannot express an overshoot.

## 4. Fibre

- At equal composition, a low-viscosity oat-bran drink (1,250 kJ) gave more satiety, more CCK, GLP-1 and PYY,
  and a deeper ghrelin fall than the high-viscosity one. It also emptied faster (Juvonen 2009, S1831).
- Psyllium-enriched meals blunted the ghrelin and PYY responses and prolonged PYY, but appetite ratings were
  mostly similar (Karhunen 2010, S1832).
- **Null for a G weight.** Viscous fibre slows delivery and blunts hormones; hunger does not move consistently.
  The stomach already carries this (S1350, S1355 in the register).

## 5. Liquid against solid

- **Solid against liquid meal replacement (Tieken 2007, S1833, S1834), 540 kcal each.**
  - Hunger reached its nadir at 15 min after both, began to rise within 60 min, and stayed lower after the solid
    at every time point.
  - At 4 h, hunger was 14 ± 10 % above fasting after the liquid and 45 ± 19 % below fasting after the solid.
  - Ghrelin stayed below baseline at 4 h after the solid only. CCK did not differ.
  - Caveat: the products differed in composition.
- **Chicken, solid against blended, at equal energy density, weight and volume (Martens 2011, S1835).** The solid
  suppressed hunger more: 79 against 52 mm at 20 min and 61 against 44 mm at 115 min. Ghrelin did not differ.
- **A 2,573 kJ vegetable meal homogenised against eaten as solid and liquid (Santangelo 1998, S1836).** The
  homogenised form was more satiating and emptied slower (255 against 214 min). CCK peaked later (94 against
  62 min; not significant).
- **A milk-protein gel against liquids (Juvonen 2011, S1837).** The gel gave a lower but more sustained CCK and
  more fullness.
- **Robust for hunger**, and it agrees with S1474. The hormone side is inconsistent: ghrelin moves in one study
  of two, and CCK does not differ. Food form acts through the stomach (volume, emptying), not through a per-kcal
  gut weight.

## 6. Hunger time course and phases

- Hunger reaches its nadir early (15 min, S1833) and then rises steadily. It is back above fasting by 4 h after
  540 kcal of liquid, and still below baseline at 6 h after ~1,000 kcal (S1828).
- The return of hunger correlates with the time for 90 % of the meal to empty (r = 0.75, S1860). In three of ten
  subjects it starts to rise while over 40 % of the meal is still in the stomach, and keeps rising after emptying has stopped.
- Spontaneous meal requests come 247–321 min after preloads of 7.5–33 % of daily expenditure (S1247), and
  320–425 min after a lunch (S1248).
- **The two-phase literature.** It defines an early (0–60 min) and a late (60–180 min) satiety phase by analysis
  window (Gibbons 2013, S1815).
  - In the late window, GLP-1, not PYY, correlated with hunger (S1815).
  - CCK correlated with hunger in neither window (S1816).
  - Ghrelin tracked hunger (S1815). Callahan found no relation between ghrelin recovery and the meal request
    (S1247).

## 7. The statements the plan asks for

**One phase or two? One in hunger ratings, two in the hormones.**
- Inference from the figure shapes: the hunger time courses read here look like a single early nadir followed by a
  monotone recovery (Tieken, Lewis, Diekmann, Giezenaar, van der Klaauw, Martens). Only Tieken states the nadir in
  text (15 min); the others were read from figures that were not digitised or from abstracts.
- None shows a second dip or plateau that would mark a separate late phase. Two signals would sum smoothly in a
  rating, so this does not rule them out; it means the data cannot identify them.
- The hormones do split:
  - a fast proximal family: CCK, and GLP-1 after carbohydrate;
  - a slow distal family: PYY, and GLP-1 after fat and protein;
  - ghrelin, which can overshoot late after carbohydrate.
- Hunger follows neither family cleanly. Of the hormones, it relates to ghrelin and to late GLP-1 only (S1815,
  S1816).

**Apparent half-times (derived values; inference, not readings).**
- **Early (CCK) phase.**
  - Rise: 10–15 min (S1800). Peak: 30–90 min, later for larger, slower-emptying meals (S1800, S1836).
  - Fall after delivery stops: the 30 g whey drink finished emptying by about 126 min in men and 176 min in
    women (Table 1 of S1825). Sex-averaged CCK was back near control at 180 min (3.4 against 3.1 pmol/L), down
    from 5.4 against 3.5 at 60 min (S1824).
  - Derived: the excess fell from 1.9 to 0.3 pmol/L between 60 and 180 min, (5.4 − 3.5) to (3.4 − 3.1). That
    is log2(1.9 / 0.3) = 2.7 halvings in 120 min, an apparent t½ of about 45 min (derived: 120 / 2.7)
    including the slow tail of emptying (late-phase emptying 0.3–0.5 kcal/min, Table 1).
  - The decay after delivery ends is faster than that, but these data cannot say how much faster: two points,
    sex-averaged, and the end of emptying differs by sex. Read 0.75 h as an inferred point estimate for CCK with no upper cap: the 180 min excess (3.4 against 3.1 pmol/L) is not significant, so the endpoint cannot be told from 0 or from about 1 pmol/L (an excess of 1.0 would give about 130 min), and at 60 min only 72 % (men) and 65 % (women) of the drink had emptied.
- **Ghrelin.**
  - Plasma t½ is about 30 min (S1799); suppression lasts as long as secretion is inhibited.
  - Nadir: 60–186 min, by composition (S1812, S1834). Recovery to baseline: about 4 h after 500–540 kcal
    (S1834 liquid; S1813 carbohydrate).
- **Late (PYY/GLP-1) phase.**
  - PYY peaks at 60–90 min and stays raised for several hours (S1802), past 6 h after ~1,000 kcal (S1827).
  - GLP-1 after carbohydrate is back by 3–4 h (S1801); after fat it peaks at 150 min (S1805).
  - Compare the stomach. At Hunt's mean caloric emptying of 2.5 kcal/min (S0131), 1,000 kcal takes about
    400 min (derived: 1,000 / 2.5) and 540 kcal about 216 min (derived: 540 / 2.5).
  - So the hormone persistence lasts about as long as gastric delivery does. Nothing read here requires a
    post-delivery clearance of more than about an hour.
  - Caveat on composition: Hunt's 2.5 kcal/min is for Polycose liquid meals, and fat and protein slow emptying per kcal (S1243), so a mixed solid meal of this size takes longer.
- **Hunger.** The recovery takes about 4 h at 540 kcal and over 6 h at ~1,000 kcal. That scales with emptying
  time, not with a fixed decay. A G fed by emptying, with a short clearance, produces this shape directly.

**Robust and null contrasts.**

| Contrast | Hormones | Hunger |
|---|---|---|
| Meal size | robust, graded (S1247, S1806, S1807, S1808, S1811) | robust, graded at ≥ 40 % steps (S1809, S1810, S1811, S1247) |
| Protein against carbohydrate or fat | robust (PYY, GLP-1, CCK up; ghrelin down longer) | modest and inconsistent: positive in Belza, Smeets and the pooled S1222; null in 4 single studies |
| Fat against carbohydrate | robust (CCK, PYY, GLP-1 up; ghrelin less suppressed) | null (S1810, S1816, S1818, S1830), once reversed (S1828) |
| Carbohydrate late phase | ghrelin rebound +37 % at 3–6 h (S1813) | null in the same study (S1814); weak cohort link to glucose dips (S1829) |
| Fibre (viscosity, psyllium) | blunted or slowed (S1831, S1832) | mostly null (S1832); low viscosity more satiating (S1831) |
| Liquid against solid | ghrelin in one study of two; CCK null | robust: solid less hungry (S1833, S1835, S1836; S1474) |

## 8. Recommendation for the model (inference)

- **One stage.** Build G only. The hunger data show one recovery phase, and its length scales with how long the
  stomach takes to empty. A G fed by the stomach's drain reproduces that through the feed, not through a long
  clearance. The A stage is not demanded by any reading here.
  - The one candidate for it is carbohydrate's late ghrelin overshoot (S1813). A two-stage first-order chain
    cannot produce an overshoot either. If ever wanted, it is a separate mechanism candidate (a carbohydrate
    rebound term), not A.
- **G_HALF_LIFE_H.**
  - Evidence bound: the post-delivery hormone decay is short, an apparent t½ of about 0.75 h for CCK including the emptying tail (a point estimate, inference, no upper cap, derived above); ghrelin's
    plasma half-life is about 0.5 h (S1799).
  - Suggested fit window: 0.25–1.5 h, starting near 0.5 h. Wider than the CCK bound, because PYY's distal
    persistence may add a slower tail. Pin it against the hunger-recovery oracles, not the hormones.
  - S1270 stays open: no record states a decay constant for a satiety signal. Its bound may cite this
    derivation.
- **Macronutrient weights (S1268).**
  - **W_FAT = 1.** Fat raises the hormones but not satiety at equal energy in the hunger-rating studies (four nulls, one reversal). Contrary readings: S1228 (Melanson 1999: the meal request came 126 ± 21 min after a high-fat drink against 65 ± 15 min after a simple-carbohydrate drink) and S1224 (Marmonier 2000: protein, then carbohydrate, then fat by request delay) both say fat satiates more per kcal. A time-to-request measure disagrees with the VAS nulls, so S1268 stays open, and the weight is not settled here: Task 6 fits W_FAT with S1228 and S1224 on one side and the hunger nulls on the other, and labels the result a ruling (ruling T2-3).
  - **W_CARB = 1.**
  - **W_PROTEIN** is the only weight with direct hunger support: Belza −25 % at 50 % against 14 % protein energy,
    Smeets +11 % satiety AUC (derived: 263 / 236), and the pooled S1222. Four single studies are null.
    - Its effect also runs partly through slower emptying (S1821; S1243 in the stomach). The fit should allow
      W_PROTEIN slightly above 1 and check that the stomach's protein slowing does not already carry S1222.
  - **No fibre term.** Fibre acts through viscosity and emptying, and hunger does not move consistently (S1831,
    S1832).
- **Liquid against solid** stays in the stomach (volume and emptying), not in G.
- **Oracles this harvest supports.**
  - Tieken's 540 kcal liquid against solid at 4 h (+14 % against −45 % of fasting hunger), with the composition
    caveat.
  - Diekmann's ~1,000 kcal meal still below baseline hunger at 6 h.
  - Lewis's graded hunger at a 40 % cut, with no difference at 20 %; the values are in Figure 5 only, see § 9.
  - Callahan's request intervals (S1247), already an oracle.

## 9. What was searched and what could not be found

**Searched.**
- Europe PMC queries by title for each named study.
- Topic queries combining hunger with PYY, GLP-1, ghrelin or CCK and meal size, energy content or time course.
- Web searches for meal-size dose-response studies with hormones and VAS.
- Open-access full text through PubMed Central; publisher pages for Gibbons 2013 (OUP, bot wall) and Liddle
  1985 (JCI, scan only).

**Not found or not read.**
- Tabulated hunger values at fixed timepoints for three or more meal sizes of one composition. Lewis 2015 and
  the Parastika preprint give them in figures only; de Graaf 1992 gives them in words. Filed as the open row
  S1839.
  - The tool that would fill it is a figure digitiser such as WebPlotDigitizer, on Lewis 2015 Figure 5. Nothing
    was installed.
- The full texts of Gibbons 2013 (OUP bot wall), le Roux 2005 and 2006, Belza 2013, Blom 2006 (AJCN), Smeets
  2008, Batterham 2006, Martens 2011 and Santangelo 1998 (paywalls), and Liddle 1985 (a scan). Their rows rest
  on abstracts.
- Any study that fits a first-order decay constant to a gut-hormone or hunger signal after gastric delivery
  ends.
- A measured plasma half-life for CCK or PYY in a record read here.
- Ghrelin's 30 min half-life is Steinert's citation of its refs 20 and 800, which were not read.

## Id table

| Id | Source | Section |
|---|---|---|
| S1799–S1802 | Steinert 2017 (ghrelin, CCK, GLP-1, PYY) | § 1 |
| S1803 | Liddle 1985 | § 1 |
| S1804 | Adrian 1985 | § 1 |
| S1805 | Elliott 1993 | § 1 |
| S1806 | le Roux 2005 | § 2 |
| S1807 | le Roux 2006 | § 2 |
| S1808, S1809 | Lewis 2015 (hormones; hunger) | § 2 |
| S1810 | de Graaf 1992 | § 2 |
| S1811 | Parastika 2026 (preprint) | § 2 |
| S1812–S1814 | Foster-Schubert 2008 (ghrelin; rebound; hunger null) | § 3 |
| S1815 | Gibbons 2013 | § 3 |
| S1816 | Gibbons 2016 | § 3 |
| S1817, S1818 | van der Klaauw 2013 (hormones; hunger) | § 3 |
| S1819, S1820 | Belza 2013 (hormones; hunger) | § 3 |
| S1821 | Blom 2006 | § 3 |
| S1822 | Smeets 2008 | § 3 |
| S1823 | Batterham 2006 | § 3 |
| S1824–S1826 | Giezenaar 2018 (hormones; emptying, topic digestion; hunger) | § 3 |
| S1827, S1828 | Diekmann 2026 (hormones; hunger) | § 3 |
| S1829 | Wyatt 2021 | § 3 |
| S1830 | Rolls 1991 | § 3 |
| S1831 | Juvonen 2009 | § 4 |
| S1832 | Karhunen 2010 | § 4 |
| S1833, S1834 | Tieken 2007 (hunger; hormones) | § 5 |
| S1835 | Martens 2011 | § 5 |
| S1836 | Santangelo 1998 | § 5 |
| S1837 | Juvonen 2011 | § 5 |
| S1860 | Sepple & Read 1989 | § 6 |
| S1839 (open) | tabulated hunger at three meal sizes | § 9 |
