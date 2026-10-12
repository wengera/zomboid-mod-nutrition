# Nutrient transit and absorption: harvest 12 for the gut stage G (Plan 11g Task 1)

Harvester: claude-opus-5-5, 2026-10-12. No tracked file was edited except this page and its part file,
`12-rows.tsv` (32 rows, minted as S1839–S1870; 30 settled, 2 open).
No subagent ran. `python tools/science_check.py --part docs/superpowers/research/2026-10-12-gut-satiety/12-rows.tsv`
reads 0 findings.

**The question (plan Task 1 Step 2).** The gut stage G is fed by what the stomach empties each minute and is cleared
first-order. This harvest collects small-intestinal transit, glucose and amino-acid appearance curves, and the
intestinal nutrient-infusion studies that deliver nutrients past the stomach and measure hunger or intake. It states a
defensible first-order clearance half-life for a gut signal, with its range.

**How the records were resolved.**
- Every settled row's record was resolved through the Europe PMC REST API (title, first author, year, journal,
  volume, pages, PMID and DOI matched) except the arXiv preprint (S1841, S1842), resolved through the arXiv API
  (title, five authors, 2023-07-31).
- Full text was read for Trommelen 2023 (PMC10772463, Results and Figure 6 legend), Groen 2015 (PMC4640549, Results
  and Figure 5) and Ritschel 2023 (arXiv HTML, Appendix A, Table A.1).
- Every other row's value comes from the abstract, and each row's `range` cell says so. The full texts of the
  Adelaide infusion studies are on journals.physiology.org (HTTP 403 to the fetcher) or AJCN without a PMC copy.

**Existing rows used, not duplicated.** Gastric emptying: S1242 (Brener 1983, steady duodenal delivery 2.13 kcal/min),
S1272, S1243, S1245, S1234. Intraduodenal fatty acids: S1437 (Feltrin 2004). The open row S1270 ("half-life of
post-absorptive satiety after the stomach has emptied") is the gap this harvest addresses; § 6 gives the derived
answer, and no duplicate row was filed for it.

## 1. Small-intestinal transit

- **Capsule transit (S1839, Nandhra 2023).** A systematic review of 22 studies (1,885 healthy volunteers) gives
  small-intestinal transit of 3.3–7 h across studies. A capsule is indigestible, so this bounds how long a meal's
  residue stays in the small intestine. It does not show how long its nutrients stay unabsorbed.
- **Return of hunger (S1840, Sepple & Read 1989).** Hunger's postprandial rise correlated with the time for 90 % of the
  meal to empty (r = 0.75, 10 men). It began in three subjects with over 40 % of the meal still in the stomach. It
  kept rising after emptying stopped, and it was unrelated to plasma glucose. The authors read the return of hunger as
  "directly related to a decline in the exposure of the upper small intestine to nutrient stimuli".
- **Not found as numbers.** Read 1980 (Gastroenterology 79:1276) and Wang 2015 (Aliment Pharmacol Ther 42:761, 215
  volunteers) measured meal and capsule transit, but their abstracts carry no transit values. Their full texts were
  not reachable.

## 2. Glucose appearance

- **Model constants (S1841, S1842, both via Ritschel 2023's Table A.1).**
  - Dalla Man's gut compartment absorbs at kabs 0.023 /min. Derived: half-life 30.1 min, mean residence 43.5 min.
    Gastric emptying in that model runs between kmin 0.0076 and kmax 0.0465 /min.
  - Hovorka's lumped absorption time constant is 40 min.
  - The primaries (IEEE Trans Biomed Eng 2006 and 2007; Physiol Meas 2004) are paywalled and were not read. The rows
    cite the restating source and are graded `TXT`, as the 11f sweat harvest did for restated primaries.
- **Meal appearance (S1843, Woerle 2003).** Over 6 h after a meal carrying about 78 g glucose, splanchnic tissues
  took up about 23 g at first, and about 75 g left the systemic circulation (11 volunteers). The meal's glucose is
  thus essentially all absorbed within the 6 h (inference from the disposal balance, not a measured absorption).
- **Glycaemic index is not appearance rate (S1844, S1845).** Corn flakes and bran cereal (50 g available
  carbohydrate) gave the same rate of appearance over 180 min despite a GI ratio above 2 (Schenk 2003, n = 6).
  Pasta gave a slower exogenous appearance than bread with the same glycaemic response (Eelderink 2012, n = 10).
  Blood glucose is therefore a poor proxy for the gut's nutrient flux.
- **Glucose dips and hunger (S1846, Wyatt 2021).** The dip at 2–3 h predicted hunger at 2–3 h (r = 0.16) and intake
  at 3–4 h (r = 0.19) in 1,070 people. The correlations are real but small.

## 3. Amino-acid appearance

- **Load sets the duration (S1847, Trommelen 2023, Figures 6A and 6D).**
  - After 25 g milk protein, 51 %, 62 % and 66 % of the protein appeared in the circulation by 4, 8 and 12 h.
  - After 100 g it did not plateau: 26 %, 44 % and 53 % by 4, 8 and 12 h.
  - Derived: 100 g released 26 g in the first 4 h (6.5 g/h).
  - Derived: if the 25 g curve is treated as first-order towards its 12-h value, 51/66 = 77 % is out by 4 h, a
    half-time of 4 h × ln 2 / ln(1/0.227) = 1.9 h from ingestion. That includes gastric emptying.
- **Casein (S1848, Groen 2015).** 55.3 % of 20 g casein's phenylalanine appeared in 5 h. Its appearance rate peaked
  at 90 min (Figure 5A).
- **Fast and slow proteins (S1849, Boirie 1997).** Whey gave "a dramatic but short increase", and casein "a prolonged
  plateau ... probably because of a slow gastric emptying" (abstract only).

## 4. Fat residence

- **Fat stays in the gut wall for hours (S1850, Robertson 2003).** Fat from a 50 g load was still stored in the
  jejunal mucosa at 6 h. A glucose drink at 5 h released it as a chylomicron peak. Some of a fatty meal's nutrient
  is therefore still in the gut wall when the next meal arrives.

## 5. Intestinal nutrient infusion and appetite

These studies put nutrients past the stomach, separating the gut signal from gastric distension (F). The pattern
across them:

1. **At physiological delivery the gut signal alone is weak.**
   - Cecil 1998 (S1851): 400 kcal of soup infused into the duodenum at the rate of normal gastric emptying gave no
     significant fall in hunger and no fullness. The same soup intragastrically suppressed appetite, and orally it
     suppressed appetite most.
   - Duodenal infusions at or below the normal emptying rate (about 2 kcal/min, S1242) mostly left the next meal
     unchanged:
     - glucose at 1 and 2 kcal/min (S1852);
     - lipid at 0.25 and 1.5 kcal/min (S1853);
     - lipid at 1.33 kcal/min for 150 min (S1854);
     - protein at 0.5 and 1.5 kcal/min (S1855).
   - Fructose at 2 kcal/min (S1859) is the exception at this rate: it lowered intake.
2. **Above it, intake mostly falls.**
   - Glucose at 4 kcal/min for 120 min (S1852).
   - Lipid at 4 kcal/min for 50 min (S1853): 1,139 against 1,289 kcal, derived −150 kcal for 200 kcal infused. The
     same load and duration in Pilichiewicz 2006 (S1854, n = 11) had no significant effect on appetite or energy
     intake, so the two studies disagree at this rate.
   - Protein at 3 kcal/min (S1855).
   - Lipid or protein at 3 kcal/min for 90 min (S1856).
   - Lipid at 2.86 kcal/min for 120 min: −22 % against saline and −15 % against glucose (S1857, S1858).
   - Lipid's effect partly comes with nausea (S1856).
3. **The macronutrient order at equal kcal is weak.**
   - In the duodenum, lipid sated more than glucose in young men (S1857, S1858).
   - Protein matched lipid at 3 kcal/min, with less nausea (S1856).
   - Fructose beat glucose (S1859).
   - A pooled analysis of nine studies found only small, scattered gut determinants of intake (S1868).
4. **Position matters more than macronutrient.**
   - The duodenum beat the mid-jejunum for glucose at 1 kcal/min (S1860).
   - The ileum beat the duodenum per kcal for glucose (−22 %; derived: about 4.2 times the infused 235 kJ; S1862) and for
     protein (628.5 against 733.6 kcal; S1863).
   - About 52 kcal of fat, casein or sucrose into the ileum cut the next meal by 122–188 kcal (S1864).
   - As little as 3 g of ileal fat raised satiety during and after the perfusion (S1865).
   - Jejunal and ileal lipid at 4.9 kcal/min each cut intake (S1866).
   - Ileal corn oil cut intake from 1,591 to 1,016 kcal (derived: −575 kcal) and slowed gastric emptying about
     threefold (t½ 203 against 68 min) (S1867).
   - Inference: in ordinary meals nutrient reaches the ileum mainly when delivery outruns proximal absorption.
5. **Time course.**
   - GLP-1 rose at 15–30 min of a 1 kcal/min glucose infusion and fell back to baseline while the infusion went on;
     GIP and insulin stayed up (S1861).
   - After a 4 kcal/min lipid arm stopped, PYY and the motor effects persisted (S1854), but appetite and intake were
     unchanged.
   - No study read varies the delay between an infusion's end and the test meal (open row S1869, § 7).

## 6. The statements the plan asks for

**A defensible first-order clearance half-life for a gut signal: 0.75 h (45 min), range 0.5–2 h.** This is inference,
derived from the rows above; no source measures it directly (§ 7).

- **Lower bound, 0.5 h.** A signal that tracks the nutrient load in the proximal small intestine clears about as fast
  as the lumen does.
  - The modelled gut compartment for glucose has a 30 min half-life (S1841), whose primary fit is unidentified.
  - GLP-1 fell back to baseline while a low duodenal glucose load continued (S1861). That is adaptation under
    continued delivery, not clearance after the nutrient has gone, so it does not support a fast clearance of G.
  - Hunger returns as gastric emptying ends, even before the stomach is empty (S1840).
  - A G much faster than this would make hunger mirror the emptying rate minute by minute.
- **Upper bound, 2 h.** A slower signal follows the nutrients that stay longer in the gut.
  - Protein appearance has a derived half-time of about 1.9 h from ingestion at 25 g, longer at 100 g (S1847).
  - Fat is still held in the jejunal wall at 5–6 h (S1850).
  - PYY and motor suppression outlast a high lipid load (S1854).
  - Transit of the meal's tail takes 3.3–7 h (S1839).
  - Beyond about 2 h the persistence is hormonal or post-absorptive. That is the absorbed stage A of the spec's stage
    rule, not G.
- **Central value, 0.75 h.** It sits where carbohydrate clears (0.5 h) and leans towards protein and fat for a mixed
  meal.
  - Today's P half-life is 0.7 h, a near-coincidence.
  - The difference is the feed. P was fed in full at the eat. G is fed through emptying, and a 650 kcal meal at
    2.13 kcal/min (S1242) takes about 305 min to empty (derived). G's satiety therefore lasts hours longer than P's at
    the same half-life.

**One stage or two, from this harvest's side.** Two time scales are visible in the transit and absorption evidence:

- a proximal one of tens of minutes (carbohydrate absorption, the early GLP-1 response, hunger tracking emptying);
- a persistent one of hours (protein appearance at large loads, fat in the gut wall, PYY persistence, the ileal brake).

A single G at about 0.75 h should carry carbohydrate-led meals. Large, protein-rich or fat-rich meals are where a
second stage, or a nutrient-specific clearance, would earn its place. This is evidence only; the stage rule decides.

## 7. What could not be found

- **No direct clearance measurement.** No study read measures hunger or intake at several delays after an intestinal
  infusion stops (open row S1869).
- **No luminal time course.** No study gives the unabsorbed nutrient mass in the small-intestinal lumen over time
  after a mixed meal (open row S1870). MRI small-bowel water content (Dellschaft 2022, 29 studies) measures water,
  not nutrient.
- **Abstract-only intake studies.** The intake values of the 2007 glucose-load and 2012 protein-load studies are not
  in their abstracts; their full texts were behind a 403 or a paywall.
- **Unread model primaries.** The Dalla Man (2006, 2007) and Hovorka (2004) primaries were not read; the constants
  rest on Ritschel 2023's restatement.
- **Studies read and not filed.**
  - Sundaresan 2023 (AJCN 118:646, PMC10517208): its abstract gives n = 14 with obesity and n = 11 without, while its
    methods and figure legends give n = 14 lean and n = 11 with obesity. Its quoted VAS hunger values rise while the
    text says hunger was "almost abolished". Not filed.
  - Lavin 1998 (AJCN 68:591): an insulin-clamp design whose abstract gives no infusion rate. Not filed.
  - Read 1980, Wang 2015 and Degen 1996: no transit values in the abstracts. Not filed.
  - Boirie 1997's full text was reachable only through a summarising fetcher whose paraphrase was unreliable, so its
    row is the abstract alone.

**Searched.** Europe PMC queries on intraduodenal, jejunal and ileal infusion with intake, appetite or hunger (title
and abstract, 1980–2025, human), on "after cessation" and "post-infusion" persistence, on small-bowel transit
scintigraphy and capsule normal values, on meal rate-of-appearance tracer studies, and on intrinsically labelled
protein appearance. Plus the arXiv API, NCBI eutils and PMC HTML for full texts.

**Tools.** No package was installed. Page rendering of the arXiv PDF needs `pdftoppm` (poppler-utils), which is
absent; the arXiv HTML version was read instead.

## 8. Recommendation for the model (inference)

1. **Clearance.**
   - Start the fit at `G_HALF_LIFE_H` = 0.75 h and bound it to 0.5–2 h.
   - A fit that pushes past 2 h is the signal for the stage rule's A, not for a longer G.
   - Label the value a game choice bounded by S1841, S1847, S1850, S1854 and S1861, or settle S1270 with it as a
     derived value.
2. **Weights.**
   - The infusion evidence supports at most a modest order, fat ≈ protein > glucose, in the proximal gut (S1856–S1859).
     It is abstract-level, n = 10–20, and partly confounded by nausea.
   - The neutral weight of 1 (ruling 11c-7) is defensible for carbohydrate.
   - Fat and protein weights above 1 should come from the protein-contrast oracle, not from these rows.
3. **Read shape.**
   - At normal delivery rates the gut signal alone barely moves hunger (S1851–S1855). It acts mainly with gastric
     fullness.
   - A steep `G_STEEP` (a threshold-like read) matches the 3–4 kcal/min threshold in the infusion studies, which is disputed: lipid at 4 kcal/min for 50 min lowered intake in S1853 and had no effect in S1854.
4. **Mechanism candidates for the ledger.**
   - **Distal spill.** Large meals deliver nutrient past the proximal absorptive capacity, and ileal nutrient is
     2.4–4.2 times as potent per kcal (the 4.2 is ileal against duodenal glucose, S1862; the 2.4 is the low end of ileal fat, casein or
     sucrose against saline, S1864; the comparators differ). A surplus day of large meals would therefore sate more per kcal
     than the same energy spread thin. That is a candidate route to Karl's well-fed arm without the energy-balance term.
   - **An F × G interaction in place of the probabilistic OR.** The gut signal amplifies gastric fullness rather than
     acting alone (S1851; French & Cecil 2001, Physiol Behav 74:729, a review not filed). The candidate is an
     interaction term in place of `1 − (1 − F)(1 − G)`.
