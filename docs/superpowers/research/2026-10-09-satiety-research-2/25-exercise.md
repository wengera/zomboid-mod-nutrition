# Satiety research 2, exercise and appetite, extended harvest (2026-10-09)

The harvest report of Task 25 of Satiety research 2 (2026-10-09), followed by its citation review. The review's corrections stand over the report wherever they disagree; the rows in docs/reference/science.tsv carry the corrected cells.

# Satiety research 2, Task 25: exercise and appetite, extended

Model: claude-opus-5-5. Status: DONE_WITH_CONCERNS (the concerns are at the end).

## Outputs
- `25-science-part.tsv` holds 40 rows, provisional ids S25.1 to S25.40: 37 settled, 0 unverified and 3 open.
  - Alone against the live register, the dry run mints them as S1337 to S1376. The real ids depend on the order in which the controller applies the seven parts.
- Topics:
  - `satiety`: 26 rows;
  - `energy`: 11 rows (total compensation, which counts intake and expenditure together, plus the military energy-balance rows);
  - the 3 open rows carry no topic.
- The source cell reads `25-report.md § Satiety research 2, exercise and appetite extended harvest (2026-10-09)`. The brief's plain form, "Satiety research 2, <topic> harvest (2026-10-09)", fails `sciencelib.SOURCE_RX` (`^\S+\.md § .+$`), so the cell names this report. The controller may rewrite it in one pass.
- Checks, all run in the scratch folder `sr2-25/`:
  - `science_delta.py apply --dry-run` passes against the live register.
  - The real apply on a copy, then `science_check.py --register <copy>`, gives 0 findings.
  - `science_check.py --part` gives 0 findings.
  - The live register is untouched: `science_check.py` gives 0, and `git status` shows only the pre-existing `.claude/worktrees/`.
- Resolution: I resolved every settled citation on 2026-10-09 through Europe PMC (REST, `resultType=core`). The title, first author, year, journal, volume, pages, DOI and pmid all match.
  - Most values come from the abstracts.
  - Four rows come from the full text:
    - Hu 2023: the against-control mean differences, I² and Egger. Source: the publisher PDF via a mirror, read whole.
    - King JA 2017: the mm values and the proportions. Source: the accepted manuscript in the SHURA repository.
    - Beaulieu 2021: the against-control intake and the fasting-hunger mm. Source: Europe PMC full text.
    - Flack 2020: the 50 % mean compensation index. Source: Europe PMC full text.
  - No value is rounded or derived. One interval in Hu 2023 is printed as `[-10.441, -5.492]` around an MD of -2.475 with p = 0.543, which looks like a sign typo. The row quotes it "as printed".
- Duplicates: I grepped the register for every first author and for the key terms. Two cases need explaining:
  - Beaulieu 2021 is already S1323, with the fair/good-quality subset and a qualitative fasting-hunger line. The two new rows (S25.17, S25.18) carry values S1323 does not: the all-studies against-control intake and the fasting hunger in mm. The apply did not flag them as duplicates.
  - Hu 2023 is already S1304, which notes that "the abstract gives no mean difference against control". S25.1 carries that difference, and S25.2 the protocol subgroups.

## 1. Intensity, and the size and duration of acute suppression

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S25.1 | Hu 2023 | against control, immediately post: hunger **-8.465 mm** [-13.095, -3.834]; PFC -15.863 mm; fullness +5.636 mm; **nothing at 30–90 min, nothing in AUC** | MA | 13 crossovers (12 pooled); I² 32 %; Cochrane RoB; no GRADE |
| S25.2 | Hu 2023 | at 30–90 min, HIIT/SIT vs MICT -6.347 mm; **SIT -10.430 mm** [-18.193, -2.249]; HIIT -2.475 (ns) | MA | 10 studies, 17 arms; I² 0–29.8 %; Egger p = 0.01 (publication bias) |
| S25.3 | King JA 2017 | **during exercise 41 vs 61 mm** (d 0.77); after exercise to 3–8 h 44 vs 44 mm (d 0.01); pre-meal 59 vs 64 mm; intake unchanged; 37 % suppressed beyond noise | RCT (pooled 17 crossovers) | n = 192 men; not systematic |
| S25.4 | Pélissier 2024 | individual appetite responses across 3 identical bouts inconsistent (ICC < 0.7); read as day-to-day noise | EXP | n = 20; paired against S1306 (Goltz) |
| S25.5 | Frampton 2022 | fasted vs fed exercise: hunger +13 to +23 mm, 24-h intake -2095 kJ | MA | 23 studies; network MA; the authors flag the design |

Already in the register: S1303 (Douglas 2017), S1304 (Hu 2023's abstract), S1305 (Dorling), S1306 (Goltz), S1309 (Hazell), S1314 (Rossi 2022: intensity does not change intake) and S1334 (open: the mm size and the decay).

**Verdict: settled with moderate certainty.**
- Best estimate: an aerobic bout at about 60–75 % VO2peak lowers hunger by about **20 mm during the bout**. That is 41 against 61 mm, about a third of control hunger (S25.3, n = 192).
- It lowers hunger by about **8.5 mm immediately after**, pooled (S25.1).
- The suppression is **gone by 30–90 min after the bout ends** (S25.1, pooled). Over the 3–8 h after, mean hunger equals control (S25.3).
- Sprint-interval work extends it: SIT keeps hunger about 10 mm under MICT at 30–90 min (S25.2). HIIT does not differ from MICT.
- Why moderate:
  - The populations are mostly young lean men.
  - The heterogeneity is small, and there is publication bias in the HIIT/SIT contrast.
  - King 2017 is one lab's pooled trials, not a systematic review.
- What the weaker evidence suggests and the best does not support:
  - **Suppression to 1.5 h** (Douglas 2017, S1303) and a 3-h AUC effect (Broom 2007, S1300): the pooled analysis finds none at 30–90 min and none in AUC.
  - **Reproducible individual "responders"** (Goltz 2018, S1306): King 2017 finds 60 % of individuals within measurement noise during exercise and 90 % after it, and Pélissier 2024 finds the individual changes inconsistent. The evidence weight favours treating the individual spread as mostly noise, which argues against a per-character trait. Goltz's design is stronger (replicated arms at 70 % VO2peak) and Pélissier's bout is a walk, so this is low certainty either way.
- Fed state (S25.5):
  - Exercising fasted gives higher hunger than exercising fed. This is the missing meal, which the model's pool already carries. It is not a separate exercise interaction.
  - The authors rate their own confidence low.

## 2. Mode: resistance, aerobic, swimming and cold water

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S25.9 | Liu 2023 | resistance at moderate and low load: hunger and PFC lower immediately after (p < 0.05); the two loads alike | RCT | n = 11 men |
| S25.10 | McCarthy 2024 | resistance to fatigue at 30 % and 90 % 1-RM: appetite suppressed **at 0 min only** (d > 1.10), not at 60 or 120 min; intake unchanged | EXP | n = 11 trained men |
| S25.8 | Cadieux 2014 | isoenergetic resistance vs aerobic: no intake difference at 0, 10 or 34 h; men ate more after resistance (1567 vs 1255 kcal); compensation correlated within a person across modes (r = 0.897) | RCT | n = 16 |
| S25.6 | Thackray 2020 | swimming +598 kJ vs rest (ES 0.47, CI 185–1010 kJ); cycling ES 0.31 (ns); swim vs cycle ns; same in both sexes | RCT | n = 32 |
| S25.7 | White 2005 | cold-water (20 °C) exercise: intake 877 kcal, 44 % above neutral water and 41 % above rest | RCT | n = 11 men |

Already in the register: S1301 (Broom 2009: resistance suppresses hunger during the session) and S1315 (Grigg 2023: water exercise +330 kJ, cold water +719 kJ vs neutral).

**Verdict on resistance: low certainty, with no pooled estimate.**
- Resistance work suppresses hunger acutely with a similar effect size to aerobic work (S25.9, S25.10, S1301). It is shorter-lived: gone by 60 min (S25.10).
- No trial shows resistance raising intake beyond aerobic work, except Cadieux's sex-specific acute meal.
- The narrative "less marked and inconsistent" (Dorling 2018, S1305) is a TXT reading. The newer RCTs do not support "less marked" for sessions taken to fatigue.

**Verdict on swimming and cold water: moderate certainty that water exercise raises the next meal.**
- Water exercise raises intake by about 330 kJ pooled (S1315), with 598 kJ in the largest single RCT (S25.6).
- Swimming does not differ significantly from land exercise (S1315's 78 kJ; S25.6's ES 0.16). The post-swim hunger claim is real against rest but is **not specific to water**.
- **Water temperature** is the stronger driver: cold water adds +719 kJ (S1315, 2 studies) and +44 % (S25.7). This links to the environmental rows in section 6.

## 3. Moderators: sex, training status, body fat

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S25.11 | Thackray 2016 | consensus: no sex difference acutely; at most partial compensation in both sexes; women's hormones respond more at the start of training | TXT | narrative |
| S25.12 | Hagobian 2013 | exercise to 30 % of daily EE: no sex effect on appetite or hormones; relative intake lower after exercise in both sexes | EXP | n = 21 |
| S25.13 | Hagobian 2009 | in women acylated ghrelin AUC +32 % (deficit) and +25 % (balance); in men unchanged | EXP | n = 18; hormone only, except the men's appetite |
| S25.14 | Tobin 2021 | men hungrier than women in every condition; no sex difference in relative intake | EXP | n = 24 |
| S25.15 | Stubbs 2002 (women) | 7 d of exercise: intake compensation **about 33 %** | EXP | n = 6 |
| S25.16 | Stubbs 2002 (men) | 7 d of exercise: **no** compensation (EI 11.6, 11.8, 11.8 MJ/d) | EXP | n = 6 |
| S25.28 | Höchsmann 2020 | low habitual MVPA predicts a larger intake rise (β -0.318, P = 0.001) and more compensation | RCT (secondary) | n = 108 |
| S25.24 | McNeil 2017 | a VO2peak gain predicts less compensation | RCT | n ≈ 560 |
| S25.39 (open) | — | the chronic sex difference at a matched dose | — | — |

Already in the register:
- S1303: Douglas 2017, lean against overweight;
- S1307: Li 2025, overweight or obese, hunger ES -0.35;
- S1298: Douglas 2016, a larger ghrelin fall at higher BMI;
- S1332: Beaulieu 2016, the J-curve by habitual activity;
- S1318: Whybrow 2008, men P = 0.031 and women P = 0.118.

**Verdict on sex.**
- **Acutely, settled with moderate certainty:** there is no sex difference in appetite or relative intake after exercise (S25.11, S25.12, S25.14, S25.6).
- **Chronically, unresolved, with very low certainty.** The small studies point opposite ways, and there is no pooled contrast:
  - Stubbs 2002 finds compensation in women but not men over 7 d.
  - Whybrow 2008 finds the reverse over 14 d.
  - Herrmann 2015 finds nonresponders' higher intake in men only.
  - The "women compensate" claim rests mainly on hormones (Hagobian 2009, mechanism only) and on the narrative.
- Pooling was not possible: no meta-analysis reports a sex subgroup for intake. Rossi 2022 (S1314) found sex non-significant as a subgroup for acute intake.

**Verdict on body fat: moderate certainty.**
- Overweight and obese adults show the same acute suppression (S1307: hunger ES -0.35) and a larger ghrelin fall (S1298).
- Body fat does not reverse the direction.

**Verdict on training status: low certainty.**
- Higher habitual activity or fitness predicts less compensation over weeks (S25.28, S25.24; S1332's J-curve).

## 4. Chronic training and compensation over weeks to months, and the lag question

| id | source | horizon | key value | grade | quality markers |
|---|---|---|---|---|---|
| S25.16 / S25.15 | Stubbs 2002 | 7 d | intake compensation 0 % (men), ~33 % (women) | EXP | n = 6 each |
| S25.21 | Hough 2020 | 7 d | intake compensation **~60 %** of exercise EE | EXP | n = 9 men |
| S25.19 | King NA 2009 | 12 wk | fasting and day-long hunger up (P < 0.0001); satiety of a fixed meal also up | EXP | n = 58, single arm |
| S25.20 | Myers 2019 | 12 wk | measured intake up (p = .028), pre-meal hunger up; compensation partial | EXP | n = 24 women, non-randomised |
| S25.17 | Beaulieu 2021 | median 12 wk | **intake vs control MD -13 [-83, 58] kcal/d** (25 arms, I² 6 %); pre-post -57 kcal/d | MA | 39 of 48 articles poor quality; intake mostly self-reported |
| S25.18 | Beaulieu 2021 | median 12 wk | fasting hunger **+8 (4, 11) mm** (pre-post) | MA | 19 arms, N = 375, I² 64 %; no control comparison |
| S25.26 | Riou 2019 | 3 mo | intake **unchanged**; compensation 49 % (low intensity) and 161 % (moderate), through an early, sustained fall in non-structured activity | RCT | n = 21 women |
| S25.25 | Flack 2020 | 12 wk | total compensation index **50 %** on average, independent of dose | RCT | n = 44 |
| S25.23 | Rosenkilde 2012 | 13 wk | 300 kcal/d: balance 83 % *more* negative than expected; 600 kcal/d: 20 % compensated; no intake change | RCT | n = 61 men |
| S25.22 | Church 2009 | 6 mo | compensation only at the highest dose (12 KKW: 1.2 kg) | RCT | n = 411 women |
| S25.27 | Herrmann 2015 | 10 mo | nonresponders ate more (men only) and moved less outside exercise | RCT | n = 74 |
| S25.29 | Flanagan 2024 | 24 wk | 48 % of people compensate in TDEE (-308 kcal/d), with no metabolic adaptation | RCT | E-MECHANIC subset |
| S25.30 | Silva 2018 | ≥ 7 d | non-exercise-activity compensation in 23 % of exercise-only arms | MA | 36 studies; underpowered |
| S25.31 | Donnelly 2014 | all | 75 % of randomised trials show no intake effect | MA | vote count, 103 studies |

Already in the register:
- S1317: Stubbs 2004, about 0.2 MJ/d of intake at 7 d;
- S1318: Whybrow 2008, about 30 % at 14 d;
- S1319: King NA 2008, compensators +268 kcal/d;
- S1320: Martin 2019, +90.7 and +123.6 kcal/d at 24 wk, DLW;
- S1321: Flack 2018, intake unchanged, 34–63 % total;
- S1322: Riou 2015, 18 % total, toward 84 % at about 80 wk;
- S1323: Beaulieu 2021, fair/good subset MD +102 [1, 203] kcal;
- S1335: open, the time constant.

**Verdict: settled in shape with moderate-to-low certainty. There is still no fitted time constant.**
1. **The intake share is partial and arrives within days to two weeks.**
   - 7 d: 0–60 % across four small trials (S1317, S25.15, S25.16, S25.21).
   - 14 d: about 30 % (S1318).
2. **It does not keep growing toward full intake compensation at 12–24 weeks.**
   - **What the higher-quality evidence shows** (fair/good-rated trials and objective intake):
     - a small rise of about **100 kcal/day**: S1323's fair/good subset gives MD +102 [1, 203] kcal;
     - S1320 gives +90.7 and +123.6 kcal/d by doubly labelled water;
     - the rise is **sub-proportional to dose**: 2.5 times the exercise gave +33 kcal/d more in S1320, and dose did not change compensation in S25.25 (Flack) or S25.24 (McNeil).
   - **What the all-quality pooling shows:** no intake difference against control (S25.17, MD -13 kcal/d). That pooling is dominated by poor-quality, self-reported studies, which under-report.
   - **The disagreement and how I weigh it.** Martin 2019 (S1320, DLW) and S1323's fair/good subset against S25.17's all-studies null are paired rows. The weight favours the **small positive rise** because:
     - the objective measure agrees with the better-rated subset;
     - self-report biases intake downward.
   - Either way the rise is far below the exercise expenditure at the higher doses.
3. **What does grow over months is total compensation, and most of that growth is not appetite.** It comes from:
   - falling non-exercise activity (S25.26 Riou 2019 early and sustained; S25.27 Herrmann; S25.30 Silva);
   - the body-energy loss itself (S1322's 84 % at about 80 weeks counts intake and expenditure together).
4. **Between-person spread is very large at every horizon.**
   - 26.6 % gained against expectation (McNeil, S25.24).
   - 48 % compensated in TDEE (S25.29).
   - Compensators ate +268 kcal/d (S1319).
5. On fasting hunger, training raises it by about 8 mm (S25.18) while the satiety of a fixed meal improves (S25.19).

**Does the evidence settle the 24-day lag? It rules out its shape, not just its constant.**
- A first-order lag of unit gain with τ = 24 d admits 1 - e^(-t/24) of the exercise deficit into the energy state:
  - 25 % by day 7;
  - 44 % by day 14;
  - 97 % by day 84 (12 weeks);
  - effectively 100 % by 24 weeks.
- The fit to Whybrow's days 3–16 works only because the curve is still rising there.
- By 12 weeks it predicts near-total appetite compensation. The evidence shows:
  - intake unchanged in Flack 2018, Riou 2019 and Rosenkilde 2012;
  - about 0 against control pooled (S25.17);
  - at most about 100 kcal/d against doses of several hundred kcal/day in the better data (S1320, S1323).
- The discrepancy at 12 weeks is roughly a factor of **2 to 3 or more** on the share of the exercise deficit that reaches hunger. Unit gain gives 97 %, against the evidence's 0 % to about 50 %. Even the 50 % is mostly non-appetite compensation (S25.25).
- The shape the evidence supports is a **lag of partial gain**. As a labelled game choice anchored to these rows:
  - gain about **0.3** (S1318; S25.15; Beaulieu's ~100 kcal/d against S1320's doses);
  - τ about **5–10 days**, so that most of the gain is reached within the first two weeks (S25.21, S1318);
  - no further growth after that.
- That fits both days 3–16 and Flack's 12 weeks.
- The long-run growth that does occur would then come from the mod's existing fat-depletion arm (`fatDep`) as body energy falls. It should not come from the exercise lag, or the two double-count.
- Recommendation: settle S1335 as "no time constant; the intake share is partial (about 30 %, range 0–60 %) by 1–2 weeks and does not grow with duration on average". The gain and τ above are a game choice.

## 5. Non-exercise activity: occupational labour, load carriage, military

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S25.32 | Tassone 2017 | combat-ration training of 3–34 d: weight -0.1 % to about -8.3 % (12 d); intake short of need | MA | 30 studies, narrative; many at risk of bias |
| S25.33 | Margolis 2013 | 64-d special forces course: balance **kept during moderate field work**, deficit **11.3 MJ/d (2700 kcal/d)** in simulated urban combat | COH | n = 36; DLW |
| S25.34 | Mandic 2019 | 8 h of military task circuits at 30, 21 and -10 °C: ration intake **unchanged** against sedentary (relative intake lower in all active conditions; 80 % in deficit) | RCT | n = 18 |
| S25.38 (open) | — | load carriage and appetite at a matched expenditure | — | — |

Already in the register: S1324–S1329 (Tharion, Karl 2021, Charlot ×2, Dawson, IOM), S1333 (Mayer, unverified) and S1336 (open: weeks of labour under scarcity).

**Verdict: settled in direction with moderate certainty.**
- People doing heavy sustained physical work eat **less than they spend** for days. Intake keeps pace with moderate work and falls behind strenuous work:
  - Margolis keeps balance during weapons drills and raids but runs a 2700 kcal/d deficit in urban combat.
  - Mandic finds intake unchanged on a day of 4 h of tasks.
- This extends Karl 2021 (S1325) and the expedition rows: intake catches up over 1–2 weeks only when food is ample and palatable.
- I found no occupational or manual-labour trial outside the military with measured appetite (Mayer 1956 is still unverified, S1333).
- I found no load-carriage appetite study. This is open (S25.38).

## 6. Environmental modifiers: heat, cold, altitude

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S25.35 | Shorten 2009 | exercise in heat (36 °C): intake not above rest, and relative intake below it (P = 0.002); neutral-temperature exercise raised intake above rest (P = 0.021) | RCT | n = 11 men |
| S25.36 | Crabtree 2015 | brisk walk at 8 °C: **1299 against 1172 kcal** at 20 °C (P < 0.05) | RCT | n = 16 overweight |
| S25.34 | Mandic 2019 | appetite lower in heat than cold; **intake unchanged** within 24 h | RCT | n = 18 |
| S25.7 | White 2005 | cold water +44 % | RCT | n = 11 |
| S25.37 | Matu 2018 | hypoxia: hunger SMD -0.15 (trivial); **intake SMD -0.50** (moderate) | MA | 28 studies; no GRADE |
| S25.40 (open) | — | heat or cold and intake over days of outdoor work | — | — |


Already in the register: S1316 (Millet 2021: cold g 0.44, heat g -0.39) and S1315 (Grigg: cold water +719 kJ).

**Verdict: moderate certainty in direction, low in size.**
- Acute **cold raises intake**: pooled g 0.44 (S1316), about +10 % after a cold walk (S25.36) and +44 % after cold water (S25.7).
- Acute **heat lowers it**: pooled g -0.39 (S1316); no post-exercise rise in heat (S25.35).
- The best-controlled 24-h field-task trial (S25.34) moved appetite ratings but **not intake**. The size is therefore uncertain beyond the next meal.
- These readings disagree:
  - S1316 (MA, 13 RCTs, acute) against S25.34 (RCT, 24 h). The MA is better evidence for the acute meal; S25.34 is the only reading at 24 h. Both stand.
  - S25.40 names the multi-day gap.
- Altitude lowers intake (moderate, S25.37/Matu). The game has no altitude, so this is noted only.

## 7. What the evidence says about the current model (§ 5c and #3616/#3617)

### Supported
- **An acute suppression term gated on vigorous work**, with walking excluded (S25.1, S25.3; S1302).
- **Its decay inside about an hour** (S25.1: nothing at 30–90 min; S25.3: post-exercise mean equal to control). The model's 0.5 game-hour half-life is consistent.
- **No same-day intake compensation**:
  - S25.3: intake unchanged at the next meal and over the day, n = 128;
  - S25.12 and S25.35: relative intake falls;
  - S1312 stands.
- **Inactivity never lowers hunger.** No new evidence contradicts S1330–S1332.
- **Heavy labour suppresses appetite against the deficit** (S25.33, S25.32). This supports the Karl replay and the ≥ 25 % bypass ramp in direction.

### Argued against, with the size of the discrepancy
1. **The lag's unit gain at τ = 24 d** (#3617). It admits 97 % of the exercise deficit by week 12. The evidence gives about 0–30 % of intake on average (S25.17, S1323, S1320, S25.25, S1321), which is roughly 3 times too much at 12 weeks.
   - What the mod would read: the same `exKcalDay` banked share.
   - What it would change: gain about 0.3 and τ about 5–10 d, as game choices anchored to S1318, S25.15, S25.21 and S1320; a plateau after 2 weeks.
   - Long-run growth is left to `fatDep`.
2. **The acute suppression's depth.**
   - The writer multiplies hunger by 1 - 0.7S, about -70 % at S = 1.
   - The best mm reading is -20 mm on a 61 mm control during exercise: 41 against 61, about -33 % (S25.3). After the bout the pooled value is -8.5 mm (S25.1).
   - On a proportional mapping the model's depth is about **twice** the evidence. The oracle passes because it is anchored to effect sizes (ES 0.60–1.47, S1303/S1306), and effect sizes are scaled by between-person SD, not by the hunger level.
   - Change: S ≈ 1 → factor about 0.65–0.7, that is 1 - 0.33S, if the design wants the mm reading. This is a ruling, because the ES anchor and the mm anchor disagree under the current mapping.
3. **Resistance work weighted 0.5.**
   - Resistance sessions to fatigue suppress hunger with effect sizes like aerobic work (d > 1.10, S25.10; S25.9; S1301). They only last shorter: gone by 60 min (S25.10).
   - The evidence would keep the depth and shorten the decay for resistance-classed work, rather than halving the depth. Low certainty: three small trials and no pooling.

### Left out, with size and certainty
- **Cold exposure raises intake and heat lowers it** (moderate direction, low size): g +0.44 and -0.39 at the next meal (S1316); +127 kcal after a cold walk (S25.36); +44 % after cold water (S25.7).
  - Under item 1's lag, cold's extra expenditure (`coldMult`) never reaches same-day hunger.
  - The game reads the character's temperature, the Hypothermia/Hyperthermia moodles and wetness.
  - A small acute multiplier on hunger from cold (up) and heat (down), limited to the next few hours, is what the evidence supports.
  - The size is a game choice, because S25.34 found no intake change over 24 h.
- **Fitness moderates compensation** (low certainty): higher habitual activity or VO2peak means less intake compensation (S25.28, S25.24, S1332). The game's Fitness perk could scale the lag gain down for fit characters. This is optional, and an `es` term should not be added for it alone.
- **Sprint-interval work extends suppression by about 10 mm at 30–90 min** (S25.2; low-moderate certainty, publication bias). The server never sees sprinting (x141a), so this is not observable. It needs no action.
- **Sex**: no acute difference (moderate certainty). Chronic is unresolved (S25.39 open). No sex term is supported.
- **Individual variability**: mostly measurement noise acutely (S25.3, S25.4). A per-character "compensator" trait is not supported by quality evidence, which argues against adding one.
- **Training raises fasting hunger about 8 mm while improving meal satiety** (S25.18, S25.19; moderate-low certainty). The lag already raises baseline hunger. The improved satiety quotient has no counterpart in the model; it is small, and leaving it out is defensible.

## 8. Slug requests and supersede candidates
- **Slugs:** none. `satiety` and `energy` cover every row.
- **Settle or supersede candidates (the controller rules):**
  - **S1334** (open: the pooled mm size against control, and the decay constant).
    - The size is now answered by S25.1: -8.465 mm immediately after. S25.3 gives -20 mm during.
    - The decay is bounded: none at 30–90 min, pooled.
    - Suggest settling the size through S25.1 and S25.3. Either keep a narrowed open row for the decay constant, or supersede S1334 → S25.1, S25.3, recording in the bound that no time constant is given.
  - **S1335** (open: the compensation time constant). It is not settled by a fitted constant. S25.15, S25.16, S25.21, S25.17, S25.25 and S25.24 narrow the bound to "partial within 1–2 weeks, no growth with duration on average".
  - **S1305** (Dorling 2018, TXT: resistance "less marked and not observed consistently") is weakened by S25.9 and S25.10. It is not superseded, because they are three small trials against a narrative and not a pooled estimate.
  - **Paired disagreements now in place:**
    - S1320 / S1323's fair/good subset against S25.17: training's intake rise.
    - S1306 against S25.4: the reproducibility of individual responses.
    - S1316 against S25.34: heat and cold, acute against 24 h.
    - S25.15 against S25.16 against S1318: 7–14 d compensation by sex.

## Concerns
- **The source cell does not follow the brief's literal form**, because that form fails `SOURCE_RX`. The cell names this report instead.
- **Two values come from author copies of the full text, not from the version of record:** King 2017's mm values come from the accepted manuscript, and Hu 2023's from a mirror of the publisher PDF.
- **Grading choices for the controller:**
  - King 2017 is graded RCT: pooled data from the authors' own randomised crossovers, not a systematic review.
  - These are graded EXP because randomisation is not stated in the abstract: Hagobian 2013 (counterbalanced), Tobin 2021, McCarthy 2024, Hough 2020 and Pélissier 2024.
  - Tassone 2017, Silva 2018 and Donnelly 2014 are systematic reviews without pooling, graded MA under science.md's definition.
- **Not minted:**
  - Moore 2024 (adolescents: no intake change, hunger +4.56 mm) and Hubner 2021 (older adults, hormones only): outside the game's population, or hormone-only.
  - Guédet 2025 (exercise timing): no adult pooled intake effect.
  - Anderson 2024: n = 14, hormone-led.
  - Wasse 2013: a p = 0.08 trend only.
  - Thomas 2012 and Doucet 2018: narrative or energy-balance-model conclusions without values beyond those in the rows.
- The **"weeks of labour under scarcity" gap (S1336) remains open.** No new study covers it.

## Review corrections (2026-10-09, 25-review.md)

The citation review's corrections stand over the text above wherever they disagree. Two model implications are overturned: (1) the lag's over-admission is about 1.1-1.9x on the objective (DLW) measure, not ~3x (Martin 2019's achieved exercise expenditure was about 102 and 232 kcal/d, so the +90.7 and +123.6 kcal/d intake rises are about 89 % and 53 % of it); the robust finding is a rise sub-proportional to dose, and a gain of 0.3 sits below the DLW reading; (2) 1 - 0.7S is not twice too deep during exercise (the mean factor over a 60-min bout is about 0.68, matching King's -33 %); the mismatch is the tail after the bout (-52.5 % at the bout's end, -26 % at 30 min after, against Hu's -8.465 mm immediately after and nothing at 30-90 min), which argues for a faster decay. 'No same-day intake compensation' rests on relative intake, which falls mechanically; absolute intake rose in S25.35's neutral arm and in S25.6 and S25.7. S25.14's sex difference is present without exercise and absent after resistance work. S25.18's fasting-hunger rise is pre-post with no control. The review's dictated replacements follow verbatim.

### The review's dictated text

1. **S25.2, `value`.** It repeats S1304's values: the pooled HIIT/SIT vs MICT MD of -6.347 mm [-12.054, -0.639] at 30-90 min, and the absence of a difference immediately after. Corrected cell:
   `subgroups of the pooled HIIT/SIT vs MICT hunger difference at 30-90 min (the pooled MD is S1304's; SMD = -0.258): HIIT (6 arms) MD = -2.475 mm, interval printed [-10.441, -5.492], p = 0.543; SIT (10 arms) MD = -10.430 mm, interval printed [-18.193, -2.249], p = 0.012; no HIIT/SIT vs MICT difference in hunger AUC`
2. **S25.2, `range`.** Corrected cell:
   `10 studies (17 study arms; the subgroups as printed hold 6 and 10); I2 = 0% for immediate hunger and AUC, 29.8% at 30-90 min; funnel-plot asymmetry, Egger intercept -5.35 (p = 0.01); both subgroup intervals printed asymmetric about their MD (the HIIT interval's midpoint implies an upper bound of 5.492); no GRADE rating given; read from the full text`
3. **S25.10, S25.12, S25.14 and S25.21, `grade`.** Each is a within-subject controlled crossover:
   - McCarthy 2024 has a CTRL session.
   - Hagobian 2013 is a counterbalanced crossover with rest.
   - Tobin 2021 has three conditions, one of them a sedentary control.
   - Hough 2020 calls itself "a 7-day crossover trial", with a no-exercise week.

   science.md defines `RCT` to include "a controlled crossover", and this wave's reviews of Tasks 23 and 27 ruled the same way. Corrected cell for each: `RCT`
4. **S25.5, `value`.** The 24-h intake difference names no comparison. Replace the clause `24-h intake MD -2095 kJ (95% CI -3910 to -280 kJ)` with:
   `24-h intake lower FastEx + NoMeal than FedEx + NoMeal (MD -2095 kJ; 95% CI -3910 to -280 kJ)`
5. **S25.18, `value`.** The brief asks for quality weighting. The source gives a quality-restricted estimate that the row leaves out. Corrected cell:
   `fasting hunger increased by 8 (4, 11) mm (p < 0.001; SMD = 0.327 [0.183, 0.471], small), and by 5 [2, 9] mm in studies rated fair/good (three studies, five arms, N = 79, p = 0.005); not influenced by intervention duration (2-24 weeks, p = 0.105); fasting fullness unchanged (MD = 1 [-3, 5] mm, p = 0.641); disinhibition decreased (SMD = -0.251 [-0.344, -0.159]); susceptibility to hunger unchanged (SMD = -0.014 [-0.142, 0.114])`
6. **Report § 4 (the second numbered point, and "Does the evidence settle the 24-day lag?") and § 7 "Argued against", item 1: the ~3x over-admission.** The report says S1320 gives "at most about 100 kcal/d against doses of several hundred kcal/day" and places S1320 inside "about 0-30 % of intake". That misreads the dose.
   - Martin 2019's Table 2 gives an achieved exercise expenditure of 17,114 and 38,956 kcal over 24 weeks. That is about 102 and 232 kcal/d.
   - The DLW intake rise of 90.7 and 123.6 kcal/d is therefore about 89 % and 53 % of the exercise expenditure.
   - The ~3x holds only against the self-reported and menu-measured nulls and S1318's 14-day reading.
   - The report's own weighting favours the objective DLW reading. On that reading the over-admission is about 1.1-1.9x, and a gain of 0.3 is below it.

   Corrected § 7 item 1, verbatim:
   `1. **The lag's unit gain at τ = 24 d** (#3617). It admits 1 - e^(-t/24) of the exercise deficit: 25 % by day 7, 44 % by day 14, 97 % by day 84 and about 100 % by 24 weeks. Against intake measured by doubly labelled water at 24 weeks (S1320, E-MECHANIC), the rise of 90.7 and 123.6 kcal/d is about 89 % and 53 % of the achieved exercise expenditure (17,114 and 38,956 kcal over 24 weeks, about 102 and 232 kcal/d, read from the trial's Table 2: an inference, not a register value), so unit gain over-admits by about 1.1 to 1.9 times there. Against the self-reported or menu-measured nulls (S25.17's all-studies MD -13 kcal/d; S1321; S25.23; S25.26) and S1318's 30 % over 14 days it over-admits by about 3 times or more. The size of the discrepancy rests on which intake measure is believed, and the objective one gives the smaller. What every reading shares is an intake rise sub-proportional to dose (2.3 times the expenditure gave +33 kcal/d more in S1320; dose did not change compensation in S25.24 or S25.25), which a proportional lag of any gain misses. What the mod would read: the same exKcalDay banked share. What it might change, as game choices anchored to S1318, S25.15, S25.16, S25.21 and S1320: a gain below 1 that falls with dose, or an absolute ceiling on the lagged kcal near the 90-125 kcal/d DLW rise, with τ about 5-10 d; long-run growth left to fatDep.`

   In § 4, replace `at most about 100 kcal/d against doses of several hundred kcal/day in the better data (S1320, S1323)` with:
   `+90.7 and +123.6 kcal/d by doubly labelled water against about 102 and 232 kcal/d of achieved exercise expenditure (S1320: about 89 % and 53 %), and +102 kcal/d in S1323's fair/good subset, whose doses are not pooled`

   Replace the S1335 recommendation with:
   `settle S1335 as "no time constant; intake compensation is partial within 1-2 weeks (0-60 % at 7 d, about 30 % at 14 d) and at 24 weeks is about 50-90 % of the exercise expenditure by doubly labelled water (S1320) against about 0 in self-reported pools (S25.17); sub-proportional to dose"`
7. **Report § 7 "Argued against", item 2: "1 - 0.7S about twice too deep".** This compares ACUTE_MAX at S = 1 with King's mean during exercise. S rises with a 0.5 game-hour half-life, so S reaches 1 only after about 2 h of continuous vigorous work.
   - Over a 60-min bout the mean S is 1 - 0.75/(2 ln 2) ≈ 0.46. The mean factor is then ≈ 0.68, or -32 %. That is King's -33 %.
   - The kernel's mismatch is the tail after the bout. S is 0.75 at the end of the bout (-52.5 %) and 0.375 thirty minutes later (-26 %). Hu pools -8.465 mm immediately after the bout and nothing at 30-90 min.

   Corrected item 2, verbatim:
   `2. **The acute suppression's depth and tail.** The writer multiplies hunger by 1 - 0.7S, and S rises toward 1 with a 0.5 game-hour half-life while vigorous (exerciseSuppression). Over a 60-min aerobic bout S averages about 0.46 (1 - 0.75/(2 ln 2)), so the mean factor is about 0.68, -32 %: on a proportional mapping this matches King 2017's mean during exercise, 41 against 61 mm, -33 % (S25.3; 11 of its 17 trials used 60-min bouts). The depth at S = 1 (-70 %) is about twice the mm reading, but S nears 1 only after about 2 h of continuous vigorous work. The discrepancy the evidence does show is the tail after the bout: S = 0.75 at the end of a 60-min bout gives -52.5 % and S = 0.375 thirty minutes later gives -26 %, against Hu 2023's pooled -8.465 mm immediately after and no significant effect at 30-90 min (S25.1). If the design wants the mm anchors, the change is a faster decay than rise (or a lower ACUTE_MAX with a faster decay), not a halved ACUTE_MAX alone. This is a ruling, because the ES anchor (S1303, S1306) and the mm anchors disagree under the current mapping.`
8. **Report § 7 "Supported", the bullet "No same-day intake compensation".** It cites relative intake (S25.12, S25.35). Relative intake falls mechanically when the exercise cost is subtracted. S25.35's neutral-temperature arm raised absolute intake above rest (P = 0.021). Corrected bullet:
   `- **No same-day intake compensation** for land exercise: S25.3 (intake unchanged at one meal, n = 60, and over the trial day, n = 128), S1310 (absolute intake ES 0.14, trivial) and S1312 stand. Exceptions with partial same-meal rises: running at 25 C (S25.35, P = 0.021 vs rest), swimming (S25.6, +598 kJ) and cold water (S25.7). Falls in relative intake (S25.12, S25.35) follow from subtracting the exercise cost and are not evidence on their own.`
9. **Report § 3 table, the S25.14 row.** It says "men hungrier than women in every condition". That is not so for resistance (p = 0.427), and the difference is present without exercise. Corrected key-value cell:
   `men's hunger AUC higher than women's after aerobic exercise (p = 0.025) and in control (p = 0.021), not after resistance (p = 0.427): a sex difference present without exercise; no sex difference in relative intake`
10. **Report § 4 point 5, and § 7's last bullet ("Training raises fasting hunger about 8 mm").** The 8 mm is a pre-post change in exercise arms with no control comparison. Corrected text for both places:
    `fasting hunger rises about 8 (4, 11) mm pre-post in exercise arms (S25.18; no control comparison, so time effects are not removed; 5 [2, 9] mm in the fair/good subset)`

---

# Citation review

# Task 25 citation review (exercise and appetite, extended)

Model: claude-opus-5-5. Verdict: FAIL. Nothing is fabricated, every citation resolves, and the row values are the sources' own numbers. The failures are one duplicate value, four grades, two value cells, and the report's model implications. Two of those implications do not follow from the rows or from the kernels.

## Method
- **Citations.** All 34 distinct PMIDs behind the 37 settled rows were fetched from the Europe PMC REST API (`resultType=core`). Title, first author, year, journal, volume, pages, DOI and PMID match the citation cell in every case.
- **Truncated abstracts.** Europe PMC cuts abstracts at a `<`. The cut abstracts were re-read from PubMed efetch: King JA 2017, Stubbs 2002 EJCN, McCarthy 2024, Mandic 2019, King NA 2009, Flack 2020, Myers 2019, Riou 2019, Cadieux 2014, Frampton 2022, Crabtree 2015, Shorten 2009 and McNeil 2017.
- **Full texts read:**
  - Hu 2023: the publisher PDF, hosted at fisiologiadelejercicio.com. Every MD, CI, I2 and Egger value in S25.1 and S25.2 is verbatim.
  - King JA 2017: the SHURA accepted manuscript (eprint 14893). Every value in S25.3 is verbatim, including the bout durations of 30 to 90 min (11 of the 17 studies used 60 min).
  - Beaulieu 2021: PMC8365695. S25.17 and S25.18 are verbatim.
  - Flack 2020: PMC7556238. The mean CI is 50 %, with 44 completers, 32 of them women.
  - Flanagan 2024: PMC11214370. It is E-MECHANIC.
  - Martin 2019 (S1320): PMC6735935, read for the achieved exercise dose.
- **The Hu 2023 HIIT interval.** It is printed as `[-10.441, -5.492]` around an MD of -2.475 with p = 0.543. The MD sits at the midpoint of -10.441 and +5.492, so the printed upper bound is a sign typo. Quoting it "as printed" is right. The SIT interval `[-18.193, -2.249]` is also printed asymmetric about its MD of -10.430, and the two subgroups as printed hold 6 + 10 = 16 arms against the 17 the paper states.
- **Kernels read:** `NR_Kernel_Energy.lua` (EX_LAG_TAU_D, exerciseLag, activityState) and `NR_Kernel_Satiety.lua` (ACUTE_MAX, ACUTE_HALF_LIFE_H, exerciseSuppression, acuteFactor).

## Defects
1. **S25.2, `value`.** It repeats S1304's values: the pooled HIIT/SIT vs MICT MD of -6.347 mm [-12.054, -0.639] at 30-90 min, and the absence of a difference immediately after. Corrected cell:
   `subgroups of the pooled HIIT/SIT vs MICT hunger difference at 30-90 min (the pooled MD is S1304's; SMD = -0.258): HIIT (6 arms) MD = -2.475 mm, interval printed [-10.441, -5.492], p = 0.543; SIT (10 arms) MD = -10.430 mm, interval printed [-18.193, -2.249], p = 0.012; no HIIT/SIT vs MICT difference in hunger AUC`
2. **S25.2, `range`.** Corrected cell:
   `10 studies (17 study arms; the subgroups as printed hold 6 and 10); I2 = 0% for immediate hunger and AUC, 29.8% at 30-90 min; funnel-plot asymmetry, Egger intercept -5.35 (p = 0.01); both subgroup intervals printed asymmetric about their MD (the HIIT interval's midpoint implies an upper bound of 5.492); no GRADE rating given; read from the full text`
3. **S25.10, S25.12, S25.14 and S25.21, `grade`.** Each is a within-subject controlled crossover:
   - McCarthy 2024 has a CTRL session.
   - Hagobian 2013 is a counterbalanced crossover with rest.
   - Tobin 2021 has three conditions, one of them a sedentary control.
   - Hough 2020 calls itself "a 7-day crossover trial", with a no-exercise week.

   science.md defines `RCT` to include "a controlled crossover", and this wave's reviews of Tasks 23 and 27 ruled the same way. Corrected cell for each: `RCT`
4. **S25.5, `value`.** The 24-h intake difference names no comparison. Replace the clause `24-h intake MD -2095 kJ (95% CI -3910 to -280 kJ)` with:
   `24-h intake lower FastEx + NoMeal than FedEx + NoMeal (MD -2095 kJ; 95% CI -3910 to -280 kJ)`
5. **S25.18, `value`.** The brief asks for quality weighting. The source gives a quality-restricted estimate that the row leaves out. Corrected cell:
   `fasting hunger increased by 8 (4, 11) mm (p < 0.001; SMD = 0.327 [0.183, 0.471], small), and by 5 [2, 9] mm in studies rated fair/good (three studies, five arms, N = 79, p = 0.005); not influenced by intervention duration (2-24 weeks, p = 0.105); fasting fullness unchanged (MD = 1 [-3, 5] mm, p = 0.641); disinhibition decreased (SMD = -0.251 [-0.344, -0.159]); susceptibility to hunger unchanged (SMD = -0.014 [-0.142, 0.114])`
6. **Report § 4 (the second numbered point, and "Does the evidence settle the 24-day lag?") and § 7 "Argued against", item 1: the ~3x over-admission.** The report says S1320 gives "at most about 100 kcal/d against doses of several hundred kcal/day" and places S1320 inside "about 0-30 % of intake". That misreads the dose.
   - Martin 2019's Table 2 gives an achieved exercise expenditure of 17,114 and 38,956 kcal over 24 weeks. That is about 102 and 232 kcal/d.
   - The DLW intake rise of 90.7 and 123.6 kcal/d is therefore about 89 % and 53 % of the exercise expenditure.
   - The ~3x holds only against the self-reported and menu-measured nulls and S1318's 14-day reading.
   - The report's own weighting favours the objective DLW reading. On that reading the over-admission is about 1.1-1.9x, and a gain of 0.3 is below it.

   Corrected § 7 item 1, verbatim:
   `1. **The lag's unit gain at τ = 24 d** (#3617). It admits 1 - e^(-t/24) of the exercise deficit: 25 % by day 7, 44 % by day 14, 97 % by day 84 and about 100 % by 24 weeks. Against intake measured by doubly labelled water at 24 weeks (S1320, E-MECHANIC), the rise of 90.7 and 123.6 kcal/d is about 89 % and 53 % of the achieved exercise expenditure (17,114 and 38,956 kcal over 24 weeks, about 102 and 232 kcal/d, read from the trial's Table 2: an inference, not a register value), so unit gain over-admits by about 1.1 to 1.9 times there. Against the self-reported or menu-measured nulls (S25.17's all-studies MD -13 kcal/d; S1321; S25.23; S25.26) and S1318's 30 % over 14 days it over-admits by about 3 times or more. The size of the discrepancy rests on which intake measure is believed, and the objective one gives the smaller. What every reading shares is an intake rise sub-proportional to dose (2.3 times the expenditure gave +33 kcal/d more in S1320; dose did not change compensation in S25.24 or S25.25), which a proportional lag of any gain misses. What the mod would read: the same exKcalDay banked share. What it might change, as game choices anchored to S1318, S25.15, S25.16, S25.21 and S1320: a gain below 1 that falls with dose, or an absolute ceiling on the lagged kcal near the 90-125 kcal/d DLW rise, with τ about 5-10 d; long-run growth left to fatDep.`

   In § 4, replace `at most about 100 kcal/d against doses of several hundred kcal/day in the better data (S1320, S1323)` with:
   `+90.7 and +123.6 kcal/d by doubly labelled water against about 102 and 232 kcal/d of achieved exercise expenditure (S1320: about 89 % and 53 %), and +102 kcal/d in S1323's fair/good subset, whose doses are not pooled`

   Replace the S1335 recommendation with:
   `settle S1335 as "no time constant; intake compensation is partial within 1-2 weeks (0-60 % at 7 d, about 30 % at 14 d) and at 24 weeks is about 50-90 % of the exercise expenditure by doubly labelled water (S1320) against about 0 in self-reported pools (S25.17); sub-proportional to dose"`
7. **Report § 7 "Argued against", item 2: "1 - 0.7S about twice too deep".** This compares ACUTE_MAX at S = 1 with King's mean during exercise. S rises with a 0.5 game-hour half-life, so S reaches 1 only after about 2 h of continuous vigorous work.
   - Over a 60-min bout the mean S is 1 - 0.75/(2 ln 2) ≈ 0.46. The mean factor is then ≈ 0.68, or -32 %. That is King's -33 %.
   - The kernel's mismatch is the tail after the bout. S is 0.75 at the end of the bout (-52.5 %) and 0.375 thirty minutes later (-26 %). Hu pools -8.465 mm immediately after the bout and nothing at 30-90 min.

   Corrected item 2, verbatim:
   `2. **The acute suppression's depth and tail.** The writer multiplies hunger by 1 - 0.7S, and S rises toward 1 with a 0.5 game-hour half-life while vigorous (exerciseSuppression). Over a 60-min aerobic bout S averages about 0.46 (1 - 0.75/(2 ln 2)), so the mean factor is about 0.68, -32 %: on a proportional mapping this matches King 2017's mean during exercise, 41 against 61 mm, -33 % (S25.3; 11 of its 17 trials used 60-min bouts). The depth at S = 1 (-70 %) is about twice the mm reading, but S nears 1 only after about 2 h of continuous vigorous work. The discrepancy the evidence does show is the tail after the bout: S = 0.75 at the end of a 60-min bout gives -52.5 % and S = 0.375 thirty minutes later gives -26 %, against Hu 2023's pooled -8.465 mm immediately after and no significant effect at 30-90 min (S25.1). If the design wants the mm anchors, the change is a faster decay than rise (or a lower ACUTE_MAX with a faster decay), not a halved ACUTE_MAX alone. This is a ruling, because the ES anchor (S1303, S1306) and the mm anchors disagree under the current mapping.`
8. **Report § 7 "Supported", the bullet "No same-day intake compensation".** It cites relative intake (S25.12, S25.35). Relative intake falls mechanically when the exercise cost is subtracted. S25.35's neutral-temperature arm raised absolute intake above rest (P = 0.021). Corrected bullet:
   `- **No same-day intake compensation** for land exercise: S25.3 (intake unchanged at one meal, n = 60, and over the trial day, n = 128), S1310 (absolute intake ES 0.14, trivial) and S1312 stand. Exceptions with partial same-meal rises: running at 25 C (S25.35, P = 0.021 vs rest), swimming (S25.6, +598 kJ) and cold water (S25.7). Falls in relative intake (S25.12, S25.35) follow from subtracting the exercise cost and are not evidence on their own.`
9. **Report § 3 table, the S25.14 row.** It says "men hungrier than women in every condition". That is not so for resistance (p = 0.427), and the difference is present without exercise. Corrected key-value cell:
   `men's hunger AUC higher than women's after aerobic exercise (p = 0.025) and in control (p = 0.021), not after resistance (p = 0.427): a sex difference present without exercise; no sex difference in relative intake`
10. **Report § 4 point 5, and § 7's last bullet ("Training raises fasting hunger about 8 mm").** The 8 mm is a pre-post change in exercise arms with no control comparison. Corrected text for both places:
    `fasting hunger rises about 8 (4, 11) mm pre-post in exercise arms (S25.18; no control comparison, so time effects are not removed; 5 [2, 9] mm in the fair/good subset)`

## Grading rulings on the report's flags
- **King JA 2017 graded RCT: accepted.** It aggregates the authors' own randomised crossovers into paired within-subject comparisons, with no systematic search and no between-study weighting. The range cell says "not a systematic review".
- **The five EXP rows.** McCarthy, Hagobian 2013, Tobin and Hough go to RCT (defect 3). Pélissier 2024 stays EXP pending its full text: it is a reliability design (one REST session, then three identical EX sessions), and the order of the sessions is not stated.
- **Tassone 2017, Silva 2018 and Donnelly 2014 graded MA: accepted.** science.md's `MA` includes "systematic review", and each range cell says no pooled estimate.

## Residuals
- **Stubbs 2002, both papers (S25.15, S25.16), graded EXP.** This matches the same-lab register rows S1318 (Whybrow) and S1330, but not S1317 (RCT) or the wave's crossover rulings. The controller rules on consistency.
- **Trial grade against reading design.** S25.24 (McNeil), S25.27 (Herrmann), S25.28 (Höchsmann) and S25.29 (Flanagan) are graded RCT for the trial. Their readings are non-randomised correlations or post-hoc responder splits, and the range cells could say so.
- **E-MECHANIC.** S25.28, S25.29 and S1320 all come from E-MECHANIC, so they are not independent readings.
- **S25.1, `range`.** "13 crossover studies" should read "13 randomised controlled studies" in Hu's words; the paper applies the crossover risk-of-bias tool. The value cell could also add satisfaction at 30-90 min (MD = 5.974 [0.889, 11.049], p = 0.021), and that SIT alone was significant against control for hunger at 30-90 min.
- **No other duplicates.** Apart from defect 1, no row duplicates a value in S1297-S1336. S25.17 and S25.18 carry Beaulieu values that S1323 does not, and no part 21-27 cites the same PMIDs.
- **Sources read in non-final versions.** The King 2017 mm values were read from the accepted manuscript. The Hu 2023 values were read from the hosted publisher PDF.
- **The source-cell form** (`25-report.md § …`) is left to the controller's uniform ruling at the mint.
