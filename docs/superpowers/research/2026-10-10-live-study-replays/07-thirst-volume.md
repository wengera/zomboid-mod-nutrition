# Thirst satiation and volume defence: the harvest behind the two body-water fixes (Plan 11f)

Harvester: claude-opus-5-5, 2026-10-10. Read-only. No tracked file was edited except this page and its part file,
`07-thirst-volume-rows.tsv` (41 rows, provisional ids `S7.1`–`S7.41`; 37 settled, 4 open). No subagent ran.
`python tools/science_check.py --part` reads 0 findings on the part file.

**The two fixes.** The Task 5b review (ledger, findings 1 and 2) found two defects; ruling 5b-3 sends both to a fix
round after this harvest.
- **Fix A, over-drinking.** Thirst reads plasma osmolality only. Water already swallowed but not yet absorbed is
  ignored, so the character drinks again and again at waking.
- **Fix B, the unbounded hidden sodium deficit.** Water follows sodium, so a sodium-depleted body loses
  extracellular volume with no signal. The review's heat-work arm reached na -1520, water -12.3 kg, dehydPct 0 and
  plasma 140 by day 5.

**How the records were resolved.**
- Every settled row's record was resolved through Europe PMC: title, first author, year, journal, volume, pages,
  PMID and DOI matched.
- McCance 1936 has no PMID. It was resolved through Crossref (doi:10.1098/rspb.1936.0009: "Experimental sodium
  chloride deficiency in man", McCance RA, Proc R Soc Lond B 119:245-268, 1936). The full text came from a copy of
  the Royal Society PDF on a third-party host:
  `https://static1.squarespace.com/static/54ebbf42e4b0c686e91e4f76/t/62ba1c574375ff22e99a183d/1656364125970/Experimental+Sodium+Chloride+Deficiency+in+Man+1930s.pdf`.
  Its pages carry the stamp "Downloaded from https://royalsocietypublishing.org/ on 05 October 2021". Tables II and
  VIII, Fig. 1 and p. 263 were checked against the page images, not only the OCR.
- IOM 2005 chapter 4 (Water) and chapter 6 (Sodium and Chloride) were read whole from the NAP reader, with page
  numbers.

**Where the values came from.**
- For most journal rows, the abstract; each such row says so in its `range` cell.
- The full text was read for:
  - Péronnet 2012 (PMC3351614);
  - Robin 2026 (PMC13394449);
  - Mitra 2011 (PMC3145307);
  - Dunn 1973 (the JCI PDF);
  - McCance 1936.
- The full texts of Geelen 1984, Thompson 1987, Figaro 1997 and Seckl 1986 (journals.physiology.org) returned a bot
  wall. Their rows rest on the abstracts.

**Grades.**
- A controlled crossover in the same subjects is `RCT`, whether or not the abstract states the order:
  - Thompson 1987 (drink against water withheld);
  - Figaro 1997 (three arms);
  - Seckl 1986 (water against saline);
  - Engell 1987 ("systematically randomized");
  - Sutters 1993 (AVP against glucose infusion);
  - Vrijens 1999 (water against sports drink);
  - Li 2012 (four experiments in random order, sealed envelopes).
- Each RCT row's `range` cell says whether the order is stated.
- A pre-post or single-condition study is `EXP`. Dunn 1973 is rat data and its population says so.
- Raman 2004, Westerterp 2005 and Perrier 2013 are `COH`.
- The IOM report is `AUTH`.
- Mitra 2011, a narrative review, is `TXT`.

**Id mapping.** A dry run of `science_delta.py apply` on the part file passes and would mint `S7.n → S(1697+n)`
(S7.1 → S1698 … S7.41 → S1738) on today's register. The mapping holds only if nothing else is minted first. This
page uses the provisional ids.

**Open rows this harvest answers.**
- S1692 (McCance 1936, open: the full text had returned HTTP 403). S7.31 answers it with the daily urinary sodium
  series. The controller may supersede S1692 by S7.31, or settle it from S7.31's cells.
- S1091 (total body water as a fraction of lean mass, open). S7.9 gives 72.7 +/- 3.2 % of lean body mass. The mod's
  `TBW_PER_LM = 0.73` game choice could then cite it.
- S1695 (the hypotonic thirst cut-off) stays unanswered (§ 9).

---

## 1. Pre-absorptive satiation of thirst and vasopressin

**S7.1, Geelen 1984 (EXP, abstract).** 24 h without fluid, then 10 ml/kg tap water drunk in 105 s.
- "AVP fell to 2.4 +/- 0.3 pg/ml (P less than 0.05) within 3 min and reached the water-replete level of 1.8 +/- 0.3
  pg/ml 9 min after drinking started. Serum Na+ and Osm did not change until 30-60 min after drinking."
- The hydrated level was 1.7 +/- 0.2 and the dehydrated level 3.3 +/- 0.5 pg/ml.
- "The rapid fall in plasma AVP after rehydration took place in the absence of the expected changes in the primary
  regulators of plasma AVP (i.e., osmolality and plasma volume)."

**S7.2, Thompson 1987 (RCT, abstract).** Hypertonic saline raised Posm from 289 to 306 mosmol/kg and thirst from 1.4
to 7.4 cm.
- "within 5 min of drinking both plasma vasopressin and thirst were significantly lower than postinfusion. After 20
  min of drinking, plasma vasopressin had fallen from 6.5 +/- 0.9 to 1.3 +/- 0.3 pmol/l (P less than 0.001) and
  thirst from 7.7 +/- 0.5 to 1.0 +/- 0.2 cm (P less than 0.001) despite no significant change in plasma osmolality
  (306 +/- 0.9 to 304 +/- 0.8 mosmol/kg, P = 0.17), and the drinking of 1,200 +/- 60 ml of water, over 85% of the mean
  cumulative water intake in the 30-min drinking period."
- In the water-withheld control, "no fall in any of these parameters".

**S7.3, Figaro & Mack 1997 (RCT, abstract).** Three arms after the same dehydration: drinking (Con), nasogastric
infusion (Inf), and drinking with the swallowed water extracted (Ext).
- "Reflex inhibition of [AVP]p and thirst occurred within 5 min of rehydration in Con and Ext (P < 0.05) but not
  during Inf."
- "the reduction in [AVP]p during the first 5 min of Ext (-1.1 +/- 0.3 pg/ml) was less than that seen during Con
  (-2.1 +/- 0.4 pg/ml), suggesting that oropharyngeal stimulation is not the only factor."
- "During Con, subjects ingested 20.0 +/- 2.0 ml/kg of water but only drank 15% more (31.3 +/- 7.1 ml/kg) during Ext,
  demonstrating a clear role of oropharyngeal metering in limiting total fluid intake."
- The deficit was 28.6 +/- 1.4 ml/kg.
- The abstract's "15%" does not match 31.3 against 20.0. It is quoted as written.

**S7.4, Seckl 1986 (RCT, abstract).**
- "a significant fall in plasma AVP from 2.0 +/- 0.3 to 1.2 +/- 0.4 pmol/l (P less than 0.05) 5 min after drinking
  water and from 1.8 +/- 0.3 to 0.9 +/- 0.2 pmol/l (P less than 0.05) after hypertonic saline. Plasma osmolality fell
  30-60 min after water and was unchanged after saline."
- "Gargling with water reduced thirst but did not affect plasma AVP."
- The title calls the fall "transient". The abstract gives no rebound time (S7.38 is open).

**S7.5, Salata 1987 (EXP, abstract).** Ice chips after dehydration.
- "the mean plasma vasopressin level decreased promptly within 10 min from 2.8 to 1.8 pg/mL, and it remained low for
  30 min after ice ingestion."
- 100 mL of water at 25 C over 30 min did not change AVP.
- Under 3% NaCl infusion, AVP rose to 4.6 +/- 0.8 pg/mL "despite ice ingestion". A strong osmotic drive overrides
  the oropharyngeal reflex.

**S7.6, Rolls 1980 (EXP, abstract).**
- "subjects drank 65% of their total intake within 2.5 min. The marked decrease in drinking rate thereafter, and the
  alleviation of thirst, occurred before plasma dilution had become significant. This attenuation of drinking was
  subjectively attributed to stomach fullness."
- "Within 20 min systemic deficits were removed."

**S7.7, IOM 2005 p. 104 (AUTH).** "Other osmoreceptors located in the oropharynx, gastrointestinal tract, and
particularly the liver-portal system respond to drinking and modulate the thirst drive … before there were any
changes in plasma osmolality or volume."

## 2. Absorption of a drink and the fall in osmolality

**S7.8, Péronnet 2012 (EXP, full text).** 300 ml of D2O-labelled water after an overnight fast.
- Abstract: "Ingested water appeared in plasma and blood cells within 5 min and the half-life of absorption (~11-13
  min) indicates a complete absorption within ~75-120 min."
- Table 2, the absorption rate constant (ka) and absorption half-life (ta1/2):

  | group | ka (min-1) | ta1/2 (min) |
  |---|---|---|
  | group 1, n = 15 | 0.0715 +/- 0.0299 | 10.9 +/- 3.6 |
  | group 2, n = 21 | 0.0723 +/- 0.0401 | 12.9 +/- 7.0 |

- Discussion: absorption of the 300 ml at "~3.3-4 ml min-1".
- Discussion: this is "well below the maximal rate of gastric emptying and water absorption in the small intestine
  [~20-25 ml min-1 … and 12-15 ml min-1, respectively". Those maximal rates are cited from Lambert 1997, Murray 1994
  and Lee 1955.

The timing of the osmolality fall comes from S7.1 and S7.4:
- Geelen: "Serum Na+ and Osm did not change until 30-60 min after drinking."
- Seckl: "Plasma osmolality fell 30-60 min after water."

## 3. Daily drinking volumes

**S7.10, IOM 2005 pp. 88-89, Table 4-5 (AUTH).**
- "Water balance studies suggest that the required water intake to maintain water balance for resting adult men is
  approximately 2.5 L/day (Adolph, 1933; Newburgh et al., 1930). If modest physical activity is performed, the water
  intake requirements increase to approximately 3.2 L/day."
- In these studies "individuals self-selected the volume of consumed fluids (i.e., ad libitum water consumption)".
- Table rows:
  - Newburgh 1930: about 2.6 L/d;
  - Consolazio 1968, 24 men at rest: about 2.5 L/d;
  - Greenleaf 1977: about 3.2 L/d;
  - Yokozawa 1993, 3 women at bed rest: about 1.6 L/d.
- These are total water, drinks and food moisture together.

**S7.11, IOM 2005 p. 145 (AUTH).** "Fluids (drinking water and beverages) provided about 3.0 and 2.2 L/day for 19- to
30-year-old men and women, respectively, representing approximately 81 percent of total water intake … Water from
food provided 19 percent of total water intake, or 0.7 L/day for men and 0.5 L/day for women."

**S7.12, Raman 2004 (COH, abstract).** Deuterium turnover in 458 adults aged 40-79.
- "Preformed water intake, which is water from beverages and food moisture, averaged 3.0 l/day in men (range:
  1.4-7.7 l/day) and 2.5 l/day in women (range: 1.2-4.6 l/day)."
- "Urine production averaged 2.2 l/day in men … and 2.2 l/day in women."

**S7.13, Westerterp 2005 (COH, abstract).** "Water loss was highly reproducible and ranged from 0.20 to 0.35 l/MJ,
independent of season and activity level, with higher values in women."

**S7.14, Perrier 2013 (COH, abstract).** Low drinkers (≤ 1.2 l/d) against high drinkers (2-4 l/d). This is a
between-group comparison, not an effect.
- 24-h urine "1.0 (se 0.1) v. 2.4 (se 0.1) litres".
- Urine osmolality "767 (se 27) v. 371 (se 33) mOsm/kg".
- "Plasma osmolality was similar between the groups."

**S7.15, IOM 2005 pp. 102 and 105 (AUTH).**
- "Despite ad libitum drinking, humans tend to under-replace their fluid needs over the short term."
- "thirst mechanisms come into play over the ensuing 24 hours to trigger replacement of fluids lost."

**S7.16, Engell 1987 (RCT, abstract).** "During a one hour period of ad lib drinking, all subjects consumed
insufficient fluid to rehydrate back to baseline body weights"; "both hypovolemia and plasma osmolality contribute
significantly to fluid intake."

The existing rows S0088 (the total-water AI) and S1688 (minimum losses, net -1,050 to -3,100 mL/d) are not repeated.

## 4. Body fluid compartments

**S7.17, IOM 2005 p. 78 (AUTH).** "Body water is distributed between the ICF and the ECF, which contain 65 and 35
percent of TBW, respectively … An average 70-kg man has approximately 42 L of total body water, 28 L of ICF, and 14 L
of ECF, with the ECF comprising approximately 3 L of plasma and 11 L of interstitial fluid."

**S7.18, IOM 2005 p. 77, Table 4-1 (AUTH).** Total body water as a percentage of body weight:
- males 19-50 y: 59 (43-73);
- females 19-50 y: 50 (41-60);
- the whole adult population "approximately 60 percent of body weight, with a range from approximately 45 to 75
  percent".

**S7.9, Péronnet 2012 (EXP).** "60.7 +/- 4.1% body mass or 72.7 +/- 3.2% lean body mass". The authors call this "in
complete accordance" with fat-free-mass hydration "relatively stable at ~73%".

**S7.19, IOM 2005 pp. 97-98, Fig. 4-11 (AUTH).**
- The figure plots the change in plasma volume against the change in total body water across "16 studies
  representing 146 subjects".
- Its fit is "y = -1.0466 + 0.7270x" with "r = 0.56". The text read does not state the axis units.
- Diuretic dehydration gives "a much greater ratio of plasma loss to total body water loss" than exercise-heat
  dehydration does.

## 5. Non-osmotic vasopressin

**S7.20, Dunn 1973 (EXP, rat, full text, pp. 3215-3218).**
- Abstract: AVP "did not become significant until volume had decreased by 8% or more".
- "Significant increases in plasma AVP over control levels were observed only in those animals with an hematocrit
  greater than 39%, which corresponded to a fall in blood volume of about 7%."
- Fig. 5: "PAVP = 1.3e^0.17ΔVOL (r = 0.89, P < 0.001)".
- "hypovolemia was not an effective stimulus to AVP release unless the fall in volume exceeded 8-10% of normal. The
  2-fold rise in plasma AVP observed at this level of hypovolemia is very similar to that found in two other studies."
- Hypovolaemia steepened the AVP-osmolality slope. The rise was significant at a blood-volume fall of about 6 %, and
  "even greater" at about 14 %.
- The authors cite a preliminary human report: "removal of up to 6% of blood volume by phlebotomy has no effect on
  plasma AVP" (their ref. 11, not their data).

**S7.21, Robertson & Athar 1976 (EXP, abstract).** Plasma AVP against plasma osmolality in three states:
- recumbent: "y = 0.35 (x - 281.0)";
- upright, "a maneuver that reduces intrathoracic blood volume": "y = 0.31 (x - 277.8)";
- hypertonic saline infusion: "y = 0.32 (x - 282)".

The authors' reading: "the effects are relatively small and limited to adjustments in the set of the receptor toward
higher or lower levels of osmolality."

**S7.22, Goldsmith 1982 (EXP, abstract).** Graded lower-body negative pressure (LBNP) without hypotension.
- AVP (5.0 +/- 1.0 pg/ml) "did not change" and "still did not change significantly".
- "One subject became markedly hypotensive, and his AVP increased from 2.6 to 81 pg/ml."

**S7.23, Baylis 1978 (EXP, abstract).** "Large increases in plasma arginine vasopression concentration occurred only
in subjects that experienced syncopal symptoms and developed hypotension."

**S7.24, Tsuchihashi 1989 (EXP, abstract).** 30 mEq/d with 120 mg furosemide for 3 days, in 8 women.
- "Sodium depletion in the present study reduced body weight by 1.6 kg and increased hematocrit by 3.5%."
- "A significant (p less than 0.05) increase in plasma AVP" was seen, though no AVP values are given.

**S7.25, Mitra 2011 (TXT, full text, Physiology section).** "An 8-10% reduction in plasma volume detected by arterial
stretch receptors is required to induce an exponential increase in vasopressin release." The sentence cites no
primary study. It is the human-labelled restatement of the Dunn-type figure.

**S7.26, IOM 2005 p. 94 (AUTH).** "When solute and water are lost proportionately, such as with diarrhea or vomiting,
osmolality remains constant and vasopressin release is blunted. However, the resulting ECF loss will stimulate the
renin-angiotensin-aldosterone system."

## 6. Hypovolaemic thirst and orthostatic symptoms

**S7.27, Li 2012 (RCT: four experiments "in random order, determined by the sealed envelope method"; abstract).** Furosemide volume depletion, median 1.7 L.
- "Volume depletion (P < 0.001) and tap water (P < 0.03) both affected thirst by 13 mm per L of fluid."
- Median thirst rose "from 28 mm (21-43) to 59 mm (46-72, P < 0.001)" on a 0-100 mm scale.

**S7.28, Waldréus 2013 (EXP, abstract).** LBNP of 20-40 mmHg.
- Thirst "increased three-fold … from 11 … to 34".
- Thirst "correlated only with increase in heart rate and, independently, with reduction of mean arterial pressure".

**S7.29, IOM 2005 pp. 104-105 (AUTH).** "the volume receptors are activated by more drastic fluid losses";
"Triggering of thirst through hypovolemia requires more than small changes in blood volume."

**S7.30, Robin 2026 (EXP, full text).** 40 mg oral furosemide, then readings 3 h later.
- Table 2:
  - urine "1881 +/- 103 mL";
  - plasma volume "-15.3 +/- 1.5" %;
  - ECW 16.4 to 15.6 L ("-4.8 +/- 0.3%");
  - TBW 37.7 to 36.3 L.
- "At B1, HR was 7.1 +/- 2.1 beats min-1 higher in hypovolaemia than in control." Across all tilt angles it was
  6.8 +/- 1.1 higher.
- There was "no significant change in arterial pressure".
- Of 17 recruited, two had orthostatic events while hypovolaemic:
  - one had "a brief orthostatic intolerance episode while seated";
  - one "developed presyncope symptoms (light-headedness, sudden heart rate increase) at the final tilt angle of 45°
    head up tilt".
- The abstract gives the plasma-volume fall as "15.3 +/- 0.2%" and Table 2 as 15.3 +/- 1.5. Under an acute diuretic,
  the plasma fall is about three times the bioimpedance ECW fall.

## 7. Sodium depletion with water replacement

**S7.31, McCance 1936 Table VIII (EXP, p. 259).** R.A.M.'s urinary sodium on days 1-11 of a salt-free diet with
sweating, at an intake of 34-58 mg/d.

| day | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| urine Na (mg) | 3160 | 1300 | 378 | 133 | 66 | 31 | 26 | 25 | 11 | 17 | 10 |

- Sweat: 2680, 3000, 2500, 1900 and 880 mg on days 2, 3, 5, 8 and 10.
- Totals: urine 5157 mg, sweat 10,960 mg; "Net loss: 17,540".
- In recovery the urine stayed at 22 mg for two days on intakes near 5,600-5,900 mg, then rose to 370, 1450 and 4520
  mg.
- R.B.N. lost 22,516 mg (p. 260).

**S7.32, McCance 1936 pp. 262-263 (EXP), the two phases.**
- Fig. 1's scales are drawn so that "1 kg in weight = 3300 mg of sodium". The text calls this "the amount of sodium
  present (approximately) in a litre of serum or other extra-cellular fluid".
- "at first a removal of sodium was followed pari passu by a loss of an equivalent amount of water. So long as this
  was so … no change in the osmotic pressure of the body fluids had taken place. Further forced removal of sodium was
  no [sic] followed by an equivalent loss of water. The volume of the body fluids was relatively well maintained but
  only at the expense of the osmotic pressure, which fell."
- Water was "freely taken"; urine was 1500-2000 cc per day. Copious drinks were "apt to be followed by no diuresis at
  the expected time".
- Summary: the body "compromised between (a) maintenance of its total osmotic pressure at the expense of anhydraemia
  … and (b) maintenance of its plasma and extracellular fluid volumes at the expense of a reduction in the
  concentrations of sodium and chloride in the serum".
- Fig. 1, read by eye and approximate (also in the row's `range` cell):
  - weight and sodium fall together to about day 3, near 2 kg (about 6,000-7,000 mg on the sodium scale);
  - weight then holds near a 2-3 kg loss while the sodium loss runs on to about 17,000 mg by day 11.

**S7.33, McCance 1936 Table II and p. 253 (EXP).** R.B.N.'s blood; the day-11 column is partly empty.

| measure | before | day 9 | day 10 | after recovery |
|---|---|---|---|---|
| serum Na (mg/100 cc) | 340 | 308 | 302 | 342 |
| plasma Cl (mg/100 cc) | 361 | 291 | 275 | 361 |
| cell volume (%) | 44 | 56 | 56 | 40 |
| haemoglobin (% of normal) | 101 | 125 | 115 | 93 |

- Serum urea went from 31 to 84 mg/100 cc.
- R.A.M.'s serum freezing-point depression "rose from -0.596 C before the experiment began to -0.547 at the close of
  the deprivation period".
- Table X: Na lost 765 mEq (R.A.M.) and 980 mEq (R.B.N.).
- Summary: "At least 25 to 30% of the body's extracellular ions were removed."

**S7.34, McCance 1936, symptoms (EXP).**
- Summary: "aberrations of flavour, cramps, weakness, lassitude, and severe cardio-respiratory distress on exertion."
- p. 251: "the resting pulse rate remained normal, but the volume became very small"; "No fall of systolic or
  diastolic pressure accompanied the salt deficiency."
- p. 250, R.B.N.: "Thirsty all morning--drank a lot but water seems to make little difference."

**S7.35, Sutters 1993 (RCT, abstract).** 36 h of salt restriction. In the glucose arm:
- "plasma arginine vasopressin concentration fell (1.77 +/- 0.34 to 1.02 +/- 0.13 pg/ml)";
- "urine flow increased (67.9 +/- 11.5 to 89.8 +/- 17.1 ml/h)";
- "haemoconcentration occurred (packed cell volume 40.8 +/- 0.3 to 42.8 +/- 0.5%";
- "plasma sodium concentration fell (140 +/- 0.2 to 138 +/- 0.2 mmol/l)".

With vasopressin held up by infusion, "the diuresis was reversed" and "plasma sodium concentration fell further
(139.8 +/- 0.4 to 136.1 +/- 0.4 mmol/l)". This is McCance's phase 1 at the start of restriction: water leaves with
the sodium.

**S7.36, Vrijens & Rehrer 1999 (RCT, abstract).**
- "The rate of change in plasma sodium concentration … was greater with W than with G (-2.48 +/- 2.25 vs. -0.86 +/-
  1.61 mmol. l-1. h-1, P = 0.0198)."
- "One subject developed hyponatremia (plasma sodium 128 mmol/l) at exhaustion (2.5 h) in the W trial."

**S7.37, IOM 2005 p. 162 (AUTH).** "Hyponatremia is defined by a serum sodium level of less than 135 mmol/L, but
symptoms are usually not apparent unless the serum sodium level is less than 130 mmol/L."

## 8. What the two fixes' constants would be

Everything in this section is a **derivation** from the harvested values, or a **game choice** named as one. None of
it is a row.

### Fix A: count swallowed water toward satiation, absorb it at the measured rate

**Satiation precedes absorption: the pending water counts at full weight.**
- AVP is back to the water-replete level 9 min after drinking starts (S7.1).
- Thirst falls from 7.7 to 1.0 cm within 20 min while plasma osmolality is unchanged (S7.2). That is a fall of about
  87 % of the post-infusion rating (derivation: 6.7 / 7.7).
- Both happen while plasma osmolality has not moved, and osmolality falls only at 30-60 min (S7.1, S7.4).
- So the mod's view-c fix, which counts the liquid lane's pending water in the thirst view's c, has the physiology's
  direction. Weight 1.0 on the pending water is the simplest reading of S7.1 and S7.2: satiation is as complete as if
  absorbed, within minutes.
- The weight itself is a game choice. No study measures a fractional weight.
- Caveat: S7.5 shows a strong osmotic drive overriding the oropharyngeal reflex. S7.4's "transient" says the reflex
  fades if the water is not absorbed. How long it lasts is open (S7.38).

**Absorption rate.**
- The absorption half-life is 10.9-12.9 min, with ka 0.0715-0.0723 min-1 (S7.8, Table 2). As a time constant that is
  1/ka ≈ 13.8-14.0 min (derivation).
- First-order absorption holds at 300 ml, with about 99 % absorbed in about 75-90 min (the authors' own 7 × ta1/2).
- For a large drink, the cited ceilings are 12-15 ml/min intestinal absorption (about 720-900 ml/h, derivation) and
  20-25 ml/min gastric emptying (S7.8).
- A lane that empties water first-order with τ ≈ 14 min, capped near 12-15 ml/min, matches both readings.

**Drinking stops short of the deficit.**
- Figaro's drinkers took 20.0 ml/kg against a 28.6 ml/kg deficit, about 70 % (derivation: 20.0 / 28.6) (S7.3).
- Rolls's took 65 % of their intake in the first 2.5 min (S7.6).
- IOM: "humans tend to under-replace … over the short term", and the rest comes over "the ensuing 24 hours" (S7.15).
- A drinking bout that ends with the pending water still in the lane is therefore physiological. The remainder is
  made up at meals and later bouts.

**The drinking-volume oracle (sedentary, temperate, male reference).** Each reading is shown as daily drinks.

| source | reading | daily drinks |
|---|---|---|
| S7.10 ad libitum balance studies, resting men | about 2.5 L/d total water | about 2.0 L/d (derivation: 0.81 × 2.5, using S7.11's 81 % fluid share) |
| S7.11 survey median, men 19-30 | fluids 3.0 L/d | 3.0 L/d |
| S7.12 deuterium turnover, men 40-79 | preformed water 3.0 L/d | about 2.4 L/d (derivation: 0.81 × 3.0) |
| S7.13 water loss per energy | 0.20-0.35 l/MJ, about 2.0-3.5 L/d of total loss at 10 MJ/d (derivation) | about 1.0-2.7 L/d, after subtracting about 0.6-0.7 L of food water (S7.11) and about 0.25-0.35 L of metabolic water (S1688) (derivation) |

- **Oracle band: about 2.0-3.0 L/d of drinks for the male reference.**
- **For the female reference: about 1.6-2.2 L/d.** This rests on S7.10's three women at about 1.6 L/d of total water
  and S7.11's 2.2 L/d of fluids. The bottom is weakly supported.
- The review measured 4.0-5.8 L/d before the view-c fix and 3.3-3.8 L/d after (ledger, Task 5b review, finding 2).
  The second range still sits above the band's top. If the mod's food water is counted outside the drink lane, the
  basal turnover constant (3700/2700, S0088 as a game choice) is the next suspect. S7.10's balance figure of about
  2.5 L/d is the measured ad libitum total for resting men; the S0088 AI is a survey median.
- **Within-person spread:** a CV of 8 % (S7.12).
- **Between-person spread:** wide. Ranges run 1.4-7.7 L/d (S7.12), and habitual low drinkers keep a normal plasma
  osmolality (S7.14). The band is a central tendency, not a hard limit.

### Fix B: bound the hidden sodium deficit by a volume defence

**Reference compartment sizes.**
- ECF is 14 L in the 70-kg man, so 0.20 L/kg (derivation: 14 / 70) (S7.17). McCance also took ECF as 20 % of body
  weight (S7.33's range).
- Plasma is 3 L, so 0.043 L/kg (derivation).
- On the lean-mass basis the kernel uses, ECF = 0.35 × TBW. With TBW = 0.727 × LBM (S7.9), ECF ≈ 0.254 L per kg of
  lean mass (derivation: 0.35 × 0.727).
- McCance's own scale: 3300 mg Na per litre of ECF ≈ 143.5 mmol/L (derivation: 3300 / 23.0). This agrees with
  S1683's 140-145.

**Phase 1, isotonic loss: water follows sodium (what option B already does).**
- McCance's first days (S7.32) and Sutters's first 36 h (S7.35) show sodium leaving with an equivalent water volume.
  Plasma sodium is nearly unchanged (140 to 138 mmol/l), AVP falls and urine flow rises.
- IOM: an isotonic ECF loss leaves osmolality constant and "vasopressin release is blunted" (S7.26).
- Option B's behaviour is right up to a threshold.

**The threshold where the volume defence starts: about 8-10 % of blood or plasma volume.**
- Rat: AVP rises significantly from about a 7 % blood-volume fall and is "not an effective stimulus … unless the fall
  in volume exceeded 8-10%" (S7.20).
- Man: a 6 % phlebotomy has no effect (S7.20's cited report). LBNP without hypotension leaves AVP flat (S7.22,
  S7.23). A sodium depletion of 1.6 kg body weight with a 3.5 % haematocrit rise does raise AVP (S7.24).
- The review restatement is "8-10% reduction in plasma volume" (S7.25).
- Carrying this to ECF assumes plasma and ECF contract in proportion during a slow isotonic loss. That is a game
  choice: S7.19 and S7.30 show the plasma share varies with the cause, and under an acute diuretic plasma falls
  about three times faster than ECW.
- On that assumption, 8-10 % of a 14 L ECF is about 1.1-1.4 L, or about 160-200 mmol of sodium (derivation:
  0.08-0.10 × 14 L × 143.5 mmol/L).

**Above the threshold: the AVP response and its shape.**
- Rat shape: PAVP = 1.3 e^(0.17 ΔVOL), which is one e-fold per about 5.9 % of volume lost (derivation: 1 / 0.17)
  (S7.20).
- The osmotic threshold moves down. Upright posture shifts it from 281.0 to 277.8 mosmol/kg, which is -3.2
  (derivation) (S7.21). Hypovolaemia steepens the AVP-osmolality slope (S7.20).
- In model terms, past about 8 % the kidney's free-water clearance is throttled and further sodium loss stops taking
  water with it. Plasma sodium falls instead.
- The throttle's shape (exponential in the volume deficit, from the rat) and its full-defence point are game choices
  resting on S7.20 and S7.32.

**Where the volume is fully defended: McCance's plateau.**
- R.A.M. weighed 9 st 12 lb ≈ 62.6 kg (derivation) and held 43 g of extracellular sodium by the author's estimate,
  which implies about 13 L of ECF (derivation: 43 / 3.3).
- His weight loss levels off near 2-3 kg (Fig. 1 by eye, S7.32). That is about 15-23 % of his ECF (derivation),
  reached after about 6,000-7,000 mg (about 260-300 mmol) of the eventual 17,540 mg sodium loss (Fig. 1 by eye,
  derivation).
- Some of the weight is lean tissue: he lost 33.6 g of body nitrogen.
- So the defence starts near 8-10 % and is complete by about 15-23 % of ECF. Beyond that, sodium loss shows up as
  falling plasma sodium.

**Hyponatraemia at the end of a severe depletion.**
- McCance's serum sodium went from 340 to 302 mg/100 cc (S7.33). That is ≈ 147.9 to 131.4 mmol/L, about -11 %
  (derivation: ÷ 2.299). The old method's baseline is high against the modern 140, so the relative fall is the
  usable reading.
- The serum freezing point rose from -0.596 to -0.547 C, about -8 % in osmolality (derivation: 0.049 / 0.596). Urea
  rose, partly offsetting the sodium fall.
- This needed 765-980 mEq of sodium lost in 11 days (S7.33). The review's arm (na -1520 by day 5) is about 1.6-2.0
  times McCance's total loss (derivation). Its "water -12.3 kg" is close to the whole ECF of a 70-kg man (S7.17). Both
  are outside anything a living subject showed.
- Symptoms usually appear below 130 mmol/L (S7.37). McCance's subjects reached about 131 mmol/L (derived above) with
  cramps, loss of flavour and exertional distress (S7.34).

**Signals the fix can surface.**
- **Thirst from volume is weak:** about 13 mm on a 100 mm scale per litre of diuresis (S7.27), about 0.13 of full
  scale per litre (derivation). It "requires more than small changes" (S7.29). McCance's hyponatraemic subjects
  felt a thirst that water did not relieve (S7.34).
- **Cardiovascular, at about a 15 % plasma-volume fall:** resting HR about +7 bpm with arterial pressure unchanged,
  and orthostatic events in 2 of 17 (S7.30).
- **Cardiovascular, at McCance's severe end** (about 25-30 % of extracellular ions lost, cell volume 44 to 56 %):
  normal resting pulse rate and blood pressure, a small-volume pulse, severe distress on exertion and cramps (S7.33,
  S7.34).
- A plausible ladder, as a game choice resting on these rows:

  | ECF loss | signal |
  |---|---|
  | < 8 % | silent |
  | 8-15 % | AVP defence on, mild exertional tachycardia, weak thirst |
  | > 15 % | orthostatic intolerance and exertional distress; plasma sodium falls with further loss; symptoms below 130 mmol/L |

## 9. What could not be found

Four open rows are filed.

**S7.38: the rebound time of thirst or AVP after a drink that is not absorbed.**
- Seckl 1986 calls the fall transient, and Salata 1987 saw it hold for 30 min after ice.
- No abstract gives a rebound time, and the APS full texts were not reachable.

**S7.39: a human dose-response of AVP on percent volume loss without hypotension.**
- The exponential and the 8-10 % come from the rat.
- The human data read are:
  - a negative LBNP;
  - a cited 6 % phlebotomy;
  - an AVP rise without values.
- Leads: Robertson's human haemorrhage and phlebotomy work (the Dunn 1973 ref. 11 report), and Zerbe 1983; neither
  was read.

**S7.40: the volume-loss threshold of hypovolaemic thirst in humans.** Li 2012 gives a slope per litre and Waldréus
2013 a rise under LBNP. Neither gives a threshold.

**S7.41: graded orthostatic heart rate or tolerance against ECF loss in dietary sodium depletion.**
- What was read: one furosemide point (S7.30) and McCance's qualitative signs.
- El-Sayed & Hainsworth 1996 (Heart 75:134, PMC484248) is a lead: salt raised plasma volume and orthostatic
  tolerance in syncope patients. Its full text was blocked, and the population is syncope patients.

Not answered either:
- **S1695 (the hypotonic thirst cut-off).** No osmolality at which thirst is abolished was read. McCance's
  hyponatraemic subjects still reported a thirst-like sensation that water did not relieve (S7.34).
- **Thompson 1987's truncated abstract.** The full text would give the 30-min intake and the time course. It was
  not reachable.

**Tooling note.** The harvest installed `pymupdf` into the user's Python with `pip install` to render McCance's page
images. No repository file depends on it.
