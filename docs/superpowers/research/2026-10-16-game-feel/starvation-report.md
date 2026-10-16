# Lethal states on science's clock: starvation, dehydration and three deficiencies

Date: 2026-10-16. Asked by: the game-feel outline (`docs/superpowers/specs/2026-10-16-game-feel-outline.md`), Workstream B. In that design, each state that can kill in reality drains health early at game pacing, down to a floor that deepens on science's clock and reaches 0 at the state's real time to death. This report gives each state's timeline and the inputs the floor curve needs.

Part file: `.superpowers/sdd/game-feel-research/starvation-part.tsv`, rows S11.1–S11.32. Of these, 31 are settled and 1 is open. `python tools/science_check.py --part` reports 0 findings.

Revised after the citation review `starvation-part-review.md`: its row defects 1–7a are applied with its cell texts, and its report items below. The changes to existing register rows are in `.superpowers/sdd/game-feel-research/starvation-existing.tsv`, taken from the review's text.

Each settled citation was resolved against its Europe PMC record (pmid, title, first author, year, journal). CAIN is cited by URL and was read directly. Full text was read for these sources: Gétaz 2012 (the journal PDF); Speakman 2013, Davies 2025, Casper 2020, Armstrong 2021, Sawka 2015, Watson 2011 and Hemstreet 2024 (Europe PMC full text); and Flamm 2021 (full text, in German). The other rows rest on their abstracts.

These sources could not be read:

- Peel 1997 BMJ (pmid:9353494): PMC and BMJ refuse the fetch, and it is scanned only.
- Keys 1945 interim report (DTIC): the fetch is refused.
- Keys 1950 monograph: a book, not read.
- Hodges 1969 and 1971: Elsevier refuses the fetch.
- Adolph 1947: a book, not read.
- Bennett & Islas 2025: the fetch is refused.
- Leiter & Marliss 1982 and Henry 1990: no abstract.

Arithmetic that is mine, not the sources', is marked **(arithmetic)** and appears only in this report, never in a row.

## 0. Rows that already exist, and which open rows this harvest touches

The register already holds most of the shape. This harvest cites those rows and does not duplicate them.

- **Starvation:**
  - S0104: weight loss of 0.9 kg/d in week 1, falling to 0.3 kg/d by week 3, in obese subjects.
  - S0105–S0108: the fuel sequence.
  - S0112: Collins, survival at BMI < 10 with care.
  - S0113: the Minnesota symptom set.
  - S1910: the male fat floor of 4–6 %.
  - S2180: Minnesota lost 25 % of body weight, 70 % of fat and 27 % of FFM.
  - Hunger under ketosis: S1259, S1451 and S1452.
  - Malnutrition and healing or infection: S0946–S0948, S0954, S0955, S0972 and S0973.
- **Dehydration:**
  - S0092–S0094, S0706, S0709, S0894 and S0895: the ≥ 2 % thresholds for performance and cognition.
  - S0624: strength −5.5 %.
  - S1021: core temperature per % of deficit.
  - S1688: net loss at rest of 1,050–3,100 mL/d.
  - The parallel water harvest (S12.x) sets about 2000 g/day of basal net loss as a game choice.
- **Deficiencies:**
  - Scurvy: S0224–S0227, S0965 and S0966.
  - Thiamine: S0239 (a pool of ~30 mg), S0240 (half-life 9–18 d), S0242 (signs below 0.5 mg/d) and S0244–S0249.
  - Pellagra: S0271 (signs at 50–60 d) and S0272.

The open rows touched, with a recommended action for each:

| open row | what this harvest found | recommended action |
|---|---|---|
| S0111 survival time in total starvation | S11.1 (CAIN: 46–73 d), S11.2 (Davies: mean 61 d, range 46–73), S11.3 (Speakman: 62.5 d, range 11–115) | `status S0111 superseded --successor` with the minted ids of S11.1, S11.2 and S11.3 (S0111 asks the general range, not only the Maze ten) |
| S0103 time to death without water | no healthy-adult reading. The available readings are S11.20 ("a few days", no count), S11.21–S11.23 (VSED in ill, elderly people: median 7 d, mean 10 d, 85 % within 15 d) and S11.24 (the 3-day rule has no evidence) | keep S0103 open, and rewrite its bound to name these rows and the unreadable Adolph 1947 table |
| S1101 life-threatening water deficit | S11.18 (Adolph via Armstrong) gives delirium at about 11 % and no urine output at about 19 %. No death threshold is stated. | keep it open. Its bound should name S11.18 as the direction. |
| S1166 time from exhausted fat to death | nothing measured. Gétaz (S11.11) says only that catastrophic protein catabolism follows. | keep it open; rewrite its bound in the same commit as S0111's supersession, because the current bound says "the survival time is open S0111" |
| S1167 the fat fraction counted as exhausted | S1910 (the male floor) already stands. Nothing found for women. | keep it open; rewrite its stale bound, which says "no settled row gives an essential-fat floor" although S1910 is settled |
| S1168 time from clinical scurvy to death | nothing usable. S11.29 is one adult case that presented after two weeks of symptoms, then developed right heart failure, cardiogenic shock and cardiac arrests in hospital, and recovered on vitamin C. | keep it open. Name S11.29 as the mechanism. |
| S1169 time from clinical thiamine deficiency to fatal cardiac beriberi | S11.25 (symptom onset 1–37 d before admission, median 33 d, with deaths within 48 h of admission among ICU cases), S11.26 (2 months of polished rice, then deaths on board) | keep it open with a new bound. S11.25's median of 33 days is onset to admission for all 33 admitted, 29 of whom survived; the four deaths occurred in intensive care with no onset times of their own. Settling would put a cohort median and a treated decompensation window in place of a per-patient untreated course. |
| S1170 time from clinical niacin deficiency to death | S11.30 ("many years"), S11.31 (7,000 deaths against 250,000 cases a year) | keep it open. The direction is years, not weeks. |
| S0243 time from a thiamine-free diet to clinical deficiency | S11.28 (4–5 weeks at 0.5 mg/d gave only subclinical depletion), and S11.25's quoted review (stores deplete within 1–3 months). No zero-thiamine experiment was read. | keep it open |
| S2061 Minnesota end fat % | the record is already in the register: Friedl 1994 (pmid:8002550, S1910's citation) quotes 5.2 % by underwater weighing after a 25 % body-weight reduction in the 1950 Minnesota study | settle it from Friedl 1994 (grade EXP, the primary's, as for S0240), with the review's settle cells |

## 1. Total starvation with water

### Evidence

- **Death:**
  - The ten 1981 Maze hunger strikers died at 46, 59, 60, 61, 61, 61, 62, 66, 71 and 73 days (S11.1). The review mean is 61 days, range 46–73 (S11.2).
  - Across 20 political hunger strikers since 1920, the mean is 62.5 days, range 11–115 (S11.3).
  - Guidance gives survival "for up to 2 to 2.5 months" in normal-weight persons, with "serious complications and death … especially from the fortieth day on" (S11.6).
- **Death point by body size:** BMI 12 is held to be the point of no recovery, and a model uses BMI ≤ 13 (S11.4). Collins's Somali survivors at BMI 10 are the exception (S0112).
- **Body fat sets the clock.** Survival rises with stored fat. For an obese woman of BMI 37.2, the models predict 249–289 days (S11.5).
- **Thresholds:**
  - Close monitoring after a 10 % weight loss, and serious medical problems from about 18 % (S11.7).
  - Hospitalisation at T < 35.5 °C, at pulse < 35/min, at BMI < 16.5–18, or when fasting lasts > 2 weeks, to start refeeding (S11.8).
  - Liberated civilians in Western Holland in 1945 showed temperatures ≤ 35 °C, pulse about 40 and systolic pressure 80 (S11.16).
- **Fuel:** glycogen is gone in 2–3 days; amino acids then serve for a few days; in prolonged fasting protein supplies about 10 % of energy; catastrophic protein catabolism follows once fat is exhausted (S11.11).
- **Signs, as the guidance lists them** (S11.9). The list order is not an order of onset; Gétaz gives no frequencies, no day of onset and no order of onset, except that hunger comes at the beginning and loss of appetite after, and that the late, sometimes irreversible signs come with longer fasting:
  - hunger at the beginning, then loss of appetite;
  - apathy and irritability;
  - headache, dizziness, difficulty getting up and moving, stroke;
  - anxiety, sadness, insomnia, poor concentration;
  - abdominal pain, peptic ulcers, nausea, constipation (sometimes diarrhoea);
  - very painful nephrolithiasis, renal failure;
  - falling blood pressure and breathing rate;
  - with longer fasting: limb paralysis, blindness, coma, death.

  The hunger-strike cohorts add the following:
  - In 33 strikers fasting 6–24 days, depression and abdominal pain predominated, and they had "an apparent absence of thirst" (S11.12).
  - Thirst falls during fasting (S11.10).
  - Eight strikers lost about 18 % by day 43 and all survived (S11.13).
- **Semi-starvation (Minnesota, 24 weeks at about 1500 kcal/d):**
  - The men lost 16 kg from 69 kg.
  - Work capacity fell to 28 % of control and running time to 21 % (S11.15).
  - Unsteadiness, weakness and inability to do hard work became universal (S11.15).
  - Depression and hypochondriasis scores rose (S11.15).
  - Anaemia, apathy, oedema and neurological deficits appeared (S0113).
- **Appetite over a fast:** the direction is that hunger eases once the subject is in ketosis.
  - The guidance's patient list gives "hunger at the beginning then loss of appetite" (S11.9).
  - On a ketogenic VLED, fasting hunger rose by day 3 and then stopped rising while ketosis held (S1259). Appetite stayed lower than after refeeding (S1452), and the pooled direction is the same (S1451).
  - These ketosis rows are from obese adults on very-low-energy diets, not from lean adults in a total fast. They support "hunger eases after about day 3" as a direction only, with no magnitude.
- **Partial fasting** (sugar or liquids with thiamine) stretches the course to 130–324 days and ends in Wernicke-Korsakoff rather than early death (S11.14). Gétaz's "much later stage than a total fast" says the same.
- **Not timed:** the day of onset of cold intolerance, dizziness, impaired healing and infection. This is open row S11.17. The healing and infection effects of malnutrition stand in S0946–S0973 without a clock.

### Recommended timeline (lean adult, about BMI 22, total fast with water)

**(inference: day bands are a game-pacing choice; only day 2–3 glycogen, day 40 and day 46–73 rest on rows)**

| phase | days | what science says |
|---|---|---|
| hungry | 0–3 | strong hunger; glycogen gone by day 2–3 (S11.11); fast early weight loss (S0104) |
| ketotic lull | 3–14 | hunger eases (S11.9, S1259 as a direction); weakness, dizziness on standing, headache, apathy, irritability (S11.9); thirst blunted, so a dehydration risk (S11.10, S11.12) |
| wasting | 14–40 | 10 % loss is the monitoring line (S11.7); low mood, insomnia, poor concentration (S11.9, S11.12); cold, slow pulse (S11.8, S11.16); work capacity falling toward Minnesota's quarter of control (S11.15, in semi-starvation) |
| critical | 40 to death | serious complications and death "from the fortieth day on" (S11.6); about 18 % loss marks serious problems (S11.7); hypothermia < 35.5 °C and pulse < 35 (S11.8) |
| death | about 61 (46–73) | S11.1, S11.2; Speakman's wider series 62.5 (11–115) (S11.3); body-size end point BMI 12–13 (S11.4) |

### Floor-curve inputs

- **Drain start:** day 3, at the end of glycogen. This is a game-pacing choice; the early drain may start sooner.
- **Floor at 1.0 until about day 14,** or until 10 % loss (S11.7).
- **Floor knees:** about 18 % loss, or day 40 (S11.6, S11.7).
- **Floor = 0 at the earlier of two points:**
  - day 61 for the reference man, with a spread of 46–73 (S11.2);
  - BMI 13 (S11.4).
- **The two anchors do not agree, and choosing between them is a ruling.** For a BMI-22 man to reach BMI 13 he must lose 41 % of his weight **(arithmetic)**. The 43-day strikers had lost only about 18 % (S11.13). Two options:
  - Key the floor to fat mass, with the Speakman model's shape (S11.5): survival scales with fat stored.
  - Key it to days, using 61 d for the reference and scaling by fat mass relative to the reference.

  Either way, an obese character survives far longer (S11.5). That is the evidenced direction, and it is the property the floor must keep.
- **Partial intake** (some food) slows the clock a great deal (S11.14), so the floor should advance with the energy deficit, not with days since the last meal.

## 2. Dehydration without water

### Evidence

- **Signs by body-water deficit** (S11.18; Adolph's desert walkers, positions read off Armstrong 2021's Fig. 1 to the nearest 0.5 %; the review's pixel re-measurement agreed within 0.3 points and placed apathy at 4.2 % and dizziness at 5.8 %; the order of first report, not a threshold for every man):
  - about 2 %: thirst, vague discomfort
  - about 3 %: anorexia
  - about 4 %: flushed skin, impatience, weariness, apathy
  - about 4.5 %: lagging walking pace
  - about 5 %: headache, stumbling, "oppressed by heat"
  - about 6 %: dizziness, indistinct speech, shortness of breath, cyanosis
  - about 9 %: spasticity
  - about 11 %: delirium
  - about 12.5 %: inability to swallow
  - about 14.5 %: painful urination
  - about 19 %: no urine output
- **Performance:**
  - Hypohydration starts above 2 % (S11.19, S0092).
  - Endurance is impaired in most studies above 3 % (S11.19), and the impairment grows by about 1.5 % per °C of skin temperature above 27 °C (S11.19).
  - Strength falls 5.5 % (S0624).
  - Cognition is affected from 2 % (S0895).
- **Time to death:**
  - Absolute fasting, with neither food nor fluid, "is not compatible with life for more than a few days" (S11.20).
  - People who voluntarily stop eating and drinking, almost all old and ill, die in a median of 7 days (S11.22). The mean is 10 days, range one to two weeks (S11.23), and 85 % die within 15 days (S11.21).
  - The "3 days" rule has no evidence (S11.24).
  - No healthy-adult time to death was readable, at rest or in heat (S0103 stays open). Adolph's survival-by-temperature table is the known source, and it is unread.
- **Rate of the deficit at rest, temperate:**
  - The net loss is 1,050–3,100 mL/d (S1688). The water harvest's game choice is about 2000 g/d.
  - At 2000 g/d, a 70 kg man loses about 2.9 % of body mass a day **(arithmetic)**. He reaches 6 % on about day 2, 11 % (delirium) on about day 4, and 15–19 % on about days 5–7 **(arithmetic)**.
  - This sits between "a few days" (S11.20) and the VSED medians (S11.22, S11.23).
  - In heat, sweat adds litres per hour of work (the sweat rows), and the same thresholds arrive within hours to a day or two **(arithmetic, direction only)**.

### Recommended timeline (keyed on deficit % of body mass, not on time)

| deficit | state |
|---|---|
| 0–2 % | thirst (S11.18) |
| 2–4 % | performance and cognition down (S11.19, S0895, S0624); anorexia at about 3 % (S11.18) |
| 4–6 % | weariness, apathy, headache, stumbling, dizziness (S11.18); heat strain (S0709, S1021) |
| 6–11 % | indistinct speech, dyspnoea, cyanosis at about 6 %, spasticity at about 9 % (S11.18); life-threatening in direction (S1101 open) |
| 11 % and up | delirium (about 11 %), cannot swallow (about 12.5 %) (S11.18) |
| about 15–19 % | painful urination, then anuria (about 19 %) (S11.18); death is the floor's end (no row states a lethal %) |

### Floor-curve inputs

- **Drain start:** about 4 %, at weariness and apathy, or 6 % at dizziness (S11.18).
- **Floor knee:** about 11 %, at delirium.
- **Floor = 0 at about 15–19 % deficit.** The evidence is anuria at about 19 % and an inability to swallow at about 12.5 % (S11.18). The exact lethal % is a game choice inside that band, because S1101 stays open.
- The clock is the deficit itself. With the water harvest's 2000 g/d basal loss, rest in temperate conditions gives about 5–7 days to death **(arithmetic)**. That agrees with "a few days" (S11.20) and the VSED medians of 7–10 days (S11.22, S11.23). Heat shortens it through the sweat model, with no separate constant.

## 3. Lethal deficiencies

**Scurvy (vitamin C).**

- Onset:
  - About 40 days after withdrawal in controlled studies (S0225).
  - About 1 month below about 10 mg/d (S0965).
  - 161 days in one self-experiment (S0224).
- Signs: S0227, S0958, S0966.
- Death:
  - Untreated scurvy "can be fatal" (S0965).
  - One adult case presented after two weeks of symptoms, then developed right heart failure, cardiogenic shock and cardiac arrests in hospital, and recovered on vitamin C (S11.29).
  - No time from clinical scurvy to death was found. S1168 stays open. The Hodges and Sheffield records hold the experimental courses and were not reachable, and the historical naval and goldfield sources give no per-patient course.
- **Recommendation:**
  - Onset of the clinical grade at about 30–40 days of nil intake (S0965, S0225).
  - The end of the floor stays a labelled game choice (Plan 5 ruling 13 shipped death 168 game hours after 30 days at the clinical grade). The evidence supports a death in weeks after clinical scurvy, by cardiopulmonary failure or haemorrhage, but gives no count.

**Wet beriberi (thiamine).**

- Depletion:
  - The pool is about 30 mg (S0239), with a half-life of 9–18 d (S0240), and signs appear below 0.5 mg/d (S0242).
  - 4–5 weeks at 0.5 mg/d gave only subclinical depletion (S11.28).
  - A thiamine-poor diet "can deplete body stores within one to three months", a review quoted in S11.25.
  - Fishermen became ill after "almost two months" of polished rice (S11.26).
- Course to death:
  - In the Mogadishu outbreak, symptom onset came 1–37 days before admission (median 33). All four deaths were ICU cases and came within 48 hours of admission (S11.25).
  - Case fatality was 1.0–1.7 % in large outbreaks with care (S11.25, S11.27) and 13 % at sea without it (S11.26).
  - Shoshin is fulminant (S0245), and the response to thiamine comes within hours to days (S0249).
- **Recommendation:**
  - **(inference)** Clinical deficiency at about 4–8 weeks of near-zero intake. No row measures near-zero intake to clinical onset: S11.28 is 0.5 mg/d and stays subclinical, a lower bound for 0.5 mg/d, not for zero; S11.26 is polished rice plus seafood; S11.25's quote is about depleted stores, not clinical onset.
  - A symptomatic wet phase of up to about a month (median 33 d before admission, S11.25), ending in a fulminant decompensation that kills within about 2 days (S11.25).
  - **(inference)** The floor reaches 0 about 5 weeks after clinical onset, with a steep last 48 hours. This adds the median onset-to-admission of all 33 admitted (29 of whom survived) to the decedents' < 48 h in intensive care; the four decedents' own onset times are not given. It cannot settle S1169, which stays open. Plan 5 shipped 7 d + 72 h.

**Pellagra (niacin).**

- Onset:
  - Signs at 50–60 days on a low-niacin corn diet (S0271).
  - The outbreak followed a 5-month interruption of groundnut distribution (S11.32).
- Four Ds: diarrhoea, dermatitis, dementia, death (S0272).
- Course to death:
  - "The disease can persist for many years and finally lead to death, sometimes by suicide in a delirious state" (S11.30).
  - The US epidemic peaked at about 250,000 cases and 7,000 deaths a year (S11.31). Deaths were about 2.8 % of reported cases in a peak year **(arithmetic)**, a case-fatality ratio with heavy under-reporting, not a time course; the slow course rests on S11.30 ('many years').
  - No day count exists, so S1170 stays open.
- **Recommendation:**
  - Clinical onset at about 50–60 days (S0271).
  - Diarrhoea and dermatitis first, dementia later (S0272).
  - The floor deepens over months, not days. Plan 5's 60 d + 336 h is far faster than history.
  - If game pacing needs pellagra to kill within one play-through, that is a ruling against the evidence, and it should be stated as one.

## 4. Floor-curve inputs in one table

| state | clock variable | drain start | knee | floor = 0 | rows |
|---|---|---|---|---|---|
| total starvation (water) | days of deficit, scaled by fat mass; or loss % / BMI | day 3 (glycogen gone) | about 18 % loss or day 40 | day 61 (46–73) for a lean man, or BMI 12–13, whichever first (ruling) | S11.1–S11.8, S11.11, S0104, S11.5 |
| dehydration | body-water deficit % | 4–6 % | about 11 % (delirium) | about 15–19 % (game choice in band) | S11.18, S11.19, S11.20–S11.23 |
| scurvy | days at the clinical grade | clinical at about 30–40 d nil intake | — | game choice (S1168 open), weeks | S0225, S0965, S11.29 |
| wet beriberi | days at the clinical grade | clinical at about 4–8 weeks **(inference)** | final 48 h fulminant | about 5 weeks after clinical onset **(inference)**; S1169 stays open | S11.25–S11.28, S0239–S0245 |
| pellagra | months at the clinical grade | clinical at 50–60 d | dementia phase | months to years (S1170 open) | S0271, S0272, S11.30–S11.32 |

## 5. Gaps

- The Adolph 1947 survival-by-temperature table (no water, rest against walking, by air temperature) is the one source that would give the dehydration clock in heat. It is in the book and in the military survival manuals, and only unofficial copies were reachable.
- Peel 1997 BMJ and the 1945 Keys interim report would give the hunger-strike stage list and the Minnesota per-week signs. Both refused the fetch.
- The Hodges 1969/1971 and Sheffield 1953 scurvy experiments hold the per-sign days. They are paywalled or scanned.
- No per-patient time from clinical scurvy, beriberi or pellagra to death was found anywhere. Outbreak and historical sources give case fatality or "years", not survival curves.
