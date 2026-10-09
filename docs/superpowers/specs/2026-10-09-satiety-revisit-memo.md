# Satiety revisit memo: the quality-weighted evidence against the shipped model (Satiety research 2)

Date: 2026-10-09. For: Angus. Status: for decision; nothing here is built.

The inputs are:
- the seven harvest reports and their citation reviews, under `docs/superpowers/research/2026-10-09-satiety-research-2/`, where a review's correction stands over its report;
- rows S1337–S1630, minted at 261f804;
- the shipped Plan 11c model: the spec's §§ 5a–5c, `body-effects#hunger-from-satiety` (#3613–#3626), the three kernels, the writer and the two oracle tests.

How to read it:
- An "S" id is a science row and a "#" id a claims row. A mod file and line is the code that shows the game state a term would read.
- "My arithmetic" marks a number I derived. No source states it.
- A hunger size given in mm is turned into displayed HUNGER through the oracle's request-anchored mapping: about 65 mm pre-meal is read as 0.25. That mapping is a labelled assumption (ruling 11c-31), and no row gives a pre-meal VAS.
- **Cost** counts only the server writer's per-player-minute step. No candidate adds per-tick work. The baseline is 0.70 µs per writer step (spec § 7).
- Any change that moves a stand-in's HUNGER re-records the golden trace under a named change (CLAUDE.md § 6). Stand-in g4 runs at rate 6.0 (`testing/tests/kernel/golden_trace.py:401`), so every exercise change moves it. One re-record per plan is enough.

## 1. What the stronger evidence confirms

- **Fibre counts only through its mass (#3626).**
  - Of the soluble fibres, only polydextrose lowers later intake (S1338, which supersedes S1237).
  - Fructans and resistant starch are null (S1344, S1346).
  - Fibre added to juice does not sate (S1366).
  - The 172 kcal cereal result is not a fibre effect: white bread matched it (S1353).
  - Chronic viscous fibre gives −0.33 kg with no measured hunger change (S1369).
- **Carbohydrate and fat weigh the same per kcal; the fat paradox runs through energy density (ruling 11c-7).**
  - The covert high-fat diets co-vary fat with energy density (S1416–S1418).
  - A lower-fat diet gives −1.4 kg (S1419, GRADE high).
- **Sugar weighs the same as starch.**
  - Swapping sugar for other carbohydrate at equal energy gives 0.04 kg (S1424).
  - Breakfast GI has no effect on next-meal intake: ES −0.01 (S1421).
- **Energy density acts through fullness F.** People eat a near-constant weight of food (S1472). A 25 % lower density gives 24 % lower intake (S1473), and 77 % of a served-energy difference reaches the daily total (S1470). This matches the spec's elasticity of about 0.9.
- **Water inside food stays with the food; a drink's water counts at 0.2.**
  - Soup lowers the meal by 20 % (S1466), and a low-density salad by 7–12 % (S1468).
  - Water drunk 30 min before the meal is null in young adults (S1458), and water drunk after it is null (S1461).
  - Corney's −23 % for water drunk immediately before (S1460) is under-read about 2.5 times, from an empty stomach. This is named, not fixed.
- **The capacities of about 430 g and 730 g hold.** A gastric load of 400 mL or more cuts intake (S1481).
- **Protein needs no source key and no per-meal threshold.**
  - Meals with matched fibre do not differ by source (S1390), nor does soy against meat over 2 weeks (S1391), nor any protein in a review (S1396).
  - Dose is graded with no step (S1385, S1379; S1413 open).
- **The pool P ignores palatability, staleness and variety.** Palatability changes how much is eaten at the meal, not later hunger (S1599).
- **No meal-frequency term.** The review finds mostly nulls (S1607).
- **Inactivity never lowers hunger.** Nothing new contradicts S1330–S1332.
- **Land exercise brings no same-day compensation.** Intake is unchanged at the meal and over the day (S1502), absolute intake is trivial (S1310) and S1312 stands. The exceptions are water, cold and neutral-temperature running (S1505, S1506, S1534).
- **The suppression's depth during a bout matches.** Over a 60-min bout, 1 − 0.7 S averages about −32 %, against King's −33 % (S1502).
- **Heavy labour falls behind its deficit.** Margolis finds a 2700 kcal/d deficit in urban combat (S1532), consistent with the Tassone review (S1531). This supports the Karl replay and the bypass ramp in direction.
- **Short fasts are under-compensated.** The next day's intake is +7–20 % and gone by day 3 (S1613–S1615). That fits a weak energy-state term.

## 2. Candidate changes, ranked by evidence strength times game impact

### C1. The exercise suppression's tail after the bout (#3616)
- **Finding.**
  - The pooled meta-analysis gives −8.465 mm hunger immediately after a bout and nothing at 30–90 min (S1500).
  - The pooled crossovers give −33 % during the bout and control-level hunger over 3–8 h (S1502, n = 192).
  - Under the shipped kernel, the bout's end reads −52.5 % and 30 min later −26 % (rise and decay share a 0.5 h half-life, `NR_Kernel_Satiety.lua:137`).
  - The oracle's ES band (S1303, S1306) requires ES ≥ 0.60 at trial hour 1.5, which is 30 min after the bout. That contradicts S1500.
- **Certainty: moderate.** A meta-analysis plus a pooled analysis of 17 crossovers, against single crossovers. Mostly young lean men.
- **Game size.** After an hour of chopping or training, hunger now reads about a quarter lower half an hour after the work stops. On the pooled evidence it should be back to normal.
- **What it reads.** The swing state and the billed MET, as today (`NR_Server_Writer.lua:170-177`; #3616). Nothing new.
- **Cost.**
  - One constant, `ACUTE_DECAY_HALF_LIFE_H`, and one branch in `exerciseSuppression`. Per-minute work is unchanged.
  - No record field.
  - The oracle: the ES band test (`test_satiety_activity.py:313`) is re-anchored on the mm readings S1500 and S1502, and the Karl replay (#3621) is re-run.
  - The golden trace moves.
- **Options.**
  - (a) Do nothing.
    - Gain: the oracle stays as accepted.
    - Downside: it keeps an anchor the better evidence contradicts.
  - (b) A faster decay than rise: the rise stays 0.5 h and the decay becomes about 0.15 h (a game choice).
    - My arithmetic: −5 % at 30 min after.
    - Gain: ACUTE_MAX stays 0.7, so the Karl replay keeps its footing.
    - Weak spot: the bout's end still reads −52.5 %, deeper than S1500's immediate-post reading.
  - (c) A lower ACUTE_MAX (about 0.35) with a fast rise and a fast decay.
    - Gain: it fits the bout's end better.
    - Downside: my arithmetic puts the Karl surplus arm near −35 % against −55 %, outside the replay's 1.5×.
- **Recommendation: (b).** Also settle S1334 through S1500 and S1502.

### C2. Sleep debt raises next-day intake (new term)
- **Finding.**
  - Intake rises +204 kcal/d at ≤ 5.5 h of sleep (S1565, chosen after risk-of-bias appraisal) and +385 kcal under partial sleep loss (S1564).
  - S1284 gives +252.8 kcal/d and +13.4 mm hunger.
  - The rise reverses with recovery sleep (S1567).
  - Whether the rise is a step or graded with the hours lost is not settled (S1568, S1282).
- **Certainty: moderate.** Three meta-analyses agree.
- **Game size.** About 10–19 % of a 2,000 kcal day (my arithmetic). Under the mapping, 13.4 mm is about +0.05 HUNGER at the request level, or about ×1.2 (my arithmetic). A player would notice it after a short night.
- **What it reads.** The mod's own sleep state:
  - the debt hours in `record.acute.debtH` (`NR_Kernel_Acute.lua:192`, updated at `:480`);
  - the asleep flag (`NR_Server_Writer.lua:260`).
  - On a server with sleep disabled, the sleep state freezes at rested (`NR_Kernel_Acute.lua:411-432`), so the term would never fire there.
- **Cost.**
  - One multiply and two constants. No record field.
  - A new oracle replay: S1284 or S1565, read as an intake ratio under the mapping.
  - The golden trace moves wherever a stand-in carries debt.
- **Options.**
  - (a) Neutral. Downside: the best-evidenced omission stays out.
  - (b) A hunger factor that rises with `debtH` to a cap anchored to S1284 and S1565, falling as the debt is repaid.
    - Weak spot: mapping the mod's debt hours onto the studies' "≤ 5.5 h" protocols, and the factor's shape (step or graded), are game choices.
    - Part of the effect may be late-night snacking rather than hunger, though S1284's hunger rating did rise.
- **Recommendation: (b).**

### C3. New oracle replays: a 36 h fast, and six meals against three
- **Finding.**
  - After a 36 h fast, the next day's intake is 12.2 against 10.2 MJ (S1613).
  - After a day at 25 % of requirement, intake is +7 % on day 2 and back to normal by day 3 (S1614).
  - Six meals against three raise the hunger AUC 1.14 times (S1608). The review's vote count is mostly null (S1607).
- **Certainty: moderate** for the fast (three crossovers agree) and **low** for meal frequency.
- **Game size.** These are diagnostics, not features. They test:
  - the deficit floor of 0.15 and the −eb/1500 slope (`NR_Kernel_Energy.lua:265`), both game choices (S1271 open);
  - the near-logarithmic read (STEEP 0.08).
  - #3622 already names the deficit drive's 22 mm same-day rise against S1255's < 10 mm.
- **What it reads.** Nothing. It is test-only.
- **Cost.** Two kernel replays. No mod change and no trace change.
- **Options.**
  - (a) Skip. Downside: the deficit drive stays checked only against S1255.
  - (b) Add both as pinned readings first, and harden them after a ruling.
    - Weak spot: "next-day intake at the request level" needs the same labelled intake mapping.
- **Recommendation: (b).** A failure here is a finding about the deficit floor, to rule on, not to patch.

### C4. The exercise lag's gain and time constant (#3617)
- **Finding.**
  - The unit-gain lag at τ = 24 d admits 25 % of the exercise deficit by day 7, 44 % by day 14, 97 % by day 84 and about 100 % by 24 weeks.
  - By doubly labelled water at 24 weeks, intake rose 90.7 and 123.6 kcal/d against an achieved exercise expenditure of about 102 and 232 kcal/d, which is 89 % and 53 % (S1320, from the review's reading of the trial's Table 2). So the lag over-admits about 1.1–1.9 times on the objective measure.
  - The self-reported pools read about 0 (S1516). Self-report under-reports, so the objective reading is weighted higher.
  - Every reading is sub-proportional to dose (S1320, S1523, S1524). No proportional lag captures that.
  - The 14-day reading stays about 30 % (S1318); 7-day trials range 0–60 % (S1514, S1515, S1520).
- **Certainty: low to moderate.** E-MECHANIC is one trial behind S1320, S1527 and S1528, and the doses are far below heavy game work.
- **Game size: small.**
  - Take a character burning 400 kcal/d above idle who eats to balance. At week 12, unit gain reads balance (es about 1.00). A gain of 0.7 leaves es about 0.96, so hunger reads about 4 % lower, indefinitely (my arithmetic).
  - Days 3–16 barely change.
- **What it reads.** The same banked `exKcalDay` (`NR_Kernel_Energy.lua:235`). Nothing new.
- **Cost.**
  - One constant, `EX_LAG_GAIN`, one multiply, and a refit of `EX_LAG_TAU_D`. No record field.
  - The oracle: the Whybrow replay is refit, and a new 24-week E-MECHANIC check is added.
  - The golden trace moves.
- **Options.**
  - (a) Do nothing.
    - Downside: a regular exerciser eventually compensates fully, which no trial shows (S1524's total compensation is 50 %).
  - (b) A gain of about 0.7 and τ refit to about 16 d.
    - My arithmetic puts days 3–16 near 30 % and the plateau at 0.7, the middle of the 53–89 %.
    - Weak spot: it rests mainly on one trial at low doses, and it is still proportional to dose.
  - (c) A ceiling on the lagged kcal near the 90–125 kcal/d DLW rise.
    - Downside: it extrapolates an absolute figure from 102–232 kcal/d doses to heavy game work, which the bypass ramp already handles.
- **Recommendation: (b), at low priority.** Leave S1335 open and narrow its bound.

### C5. Protein's hunger level, about 10 times short (#3622, S1222)
- **Finding.** Three pooled analyses support a level effect:
  - hunger −7 mm and fullness +10 mm (S1222);
  - a 4-h fullness AUC (S1223);
  - next-meal intake −164 kJ in older adults (S1380) and −106.8 kcal in children (S1383, corrected).
  
  Against them, the cleanest isolated contrast, whey against carbohydrate, is null with I² 0 % (S1384), and so is S1225.
  - The model's contrast is 0.0027 against a target of about 0.025 under the mapping (`test_satiety_meal_studies.py:36-40`).
- **Certainty: low.** The meta-analyses are ungraded and heterogeneous, and no row gives a per-trial protein contrast. The 0.025 target itself rests on the mapping.
- **Game size.** A meat-heavy meal against a starchy one would leave hunger visibly lower for a few hours, about a tenth of the request level. Today the difference is invisible.
- **What it reads.** The protein grams already in the stomach's solid lane. Every key leaves in proportion to the energy (#3613), and `massOf` sums the gram keys (spec § 3.1).
- **Cost by option.**
  - (c) adds one multiply-add in fill and no record field.
  - (d) adds a record field, its guard and CROSS rows, and one more exponential a minute.
  - Both need the Callahan, Rolls and Marmonier replays re-run, and both move the golden trace.
- **Options.**
  - (a) Keep it a named non-reproduction. Downside: protein stays nearly invisible on the hunger bar.
  - (b) Raise W_PROTEIN. Downside: ×2 already fails the Marmonier differences.
  - (c) A protein term in F during the protein's stomach residence. Weak spot: it is a fitting device, and no row names gastric fullness from protein.
  - (d) A faster second pool for protein. Downside: new state and more migration surface, against maintainability.
- **Recommendation: try (c) as an oracle spike.**
  - Ship it only if every hard replay holds at 1.1×.
  - Otherwise stay at (a).

### C6. Ambient temperature (no new term)
- **Finding.**
  - Cold raises intake (g 0.44) and heat lowers it (g −0.39), pooled from 13 RCTs; the row carries no certainty rating (S1316).
  - A day at 19 °C adds +411 kcal (13 %) while cold and nothing the next day (S1569).
  - Heating gives −176 kcal (S1572).
  - Hunger ratings mostly do not move (S1570, S1572), and a 24-h field trial left intake unchanged (S1533).
- **Certainty.** Moderate in direction, low in size. The multi-day effect is open (S1539).
- **Game size.** Winter and heat waves would make characters hungrier or less hungry by about 10–15 %.
- **What it reads.**
  - Cold already reaches hunger the same day. The resting REE is multiplied by the thermoregulator's energy multiplier (`NR_Server_Metabolism.lua:199`, `NR_Kernel_Energy.lua:228`), which flows into the 24-h balance and the energy state. My arithmetic puts a ×1.2 resting day at about +10 % hunger, the same order as S1569.
  - Heat would read the TEMPERATURE stat (#2372; already read at `NR_Server_Writer.lua:288`).
- **Cost.** For heat only: one read and one multiply. No record field. The golden trace moves (g1 runs cold).
- **Options.**
  - (a) Keep as is, with cold through expenditure and heat neutral.
    - Weak spot: heat's measured direction stays out.
  - (b) A heat-down factor while hyperthermic.
    - Downside: hunger is the only lever, and the ratings did not move in the trials, so a hunger cut overstates them.
  - (c) Cold up as well.
    - Downside: it double-counts the expenditure path.
- **Recommendation: (a).** Name heat in the limitation string.

### C7. Illness (no new term yet)
- **Finding.**
  - Intake falls during fever or diarrhoea: −5–6 % in total and −20–30 % of solids, in infants (S1540).
  - Inpatients under-eat (S1541).
  - Endotoxin sickness is confined to the acute phase (S1543). That reading is an inference from a composite symptom score.
  - The size of adult infection anorexia is open (S1544), and so is nausea's effect on intake (S1548).
- **Certainty.** High in direction, low in size.
- **What it reads.**
  - FOOD_SICKNESS, already read (`NR_Server_Writer.lua:284`; #2205). It is food poisoning, closer to nausea, which is unmeasured (S1548).
  - SICKNESS is a registered stat (#2205). What raises it on a 42.21 dedicated server has not been read here, and I am not sure the game exposes an infection state there.
- **Cost.** One read and one multiply. No record field.
- **Options.**
  - (a) Neutral. Downside: a sick character's appetite is untouched.
  - (b) A labelled cut on SICKNESS after a jar read shows what drives it. Weak spot: an infant-anchored size.
- **Recommendation: (a) now, plus a jar read of SICKNESS;** reconsider (b) after it. Keep FOOD_SICKNESS neutral.

### C8. Sugary drinks, partially compensated (no new term)
- **Finding.**
  - Added sugar-sweetened beverages raise weight in adult RCTs (S1431), and a masked 18-month drink did too (S1433).
  - Intake rose on beverage days (S1265, S1432), and soda was not compensated in one trial (S1264).
  - Single preloads are inconclusive (S1266, S1267), and Callahan's liquid preloads did sate (S1247).
- **Certainty.** Moderate that compensation is incomplete over weeks; low on its size. No row gives a controlled share.
- **Game size: low.** Soda and juice are a small share of a survival diet.
- **What it reads.** The drink route at the eat (`NR_Server_Intake.lua:214`).
- **Cost.** At the eat only. No record field.
- **Options.**
  - (a) Neutral, named.
    - Weak spot: a moderate-certainty direction stays out.
  - (b) Discount the P-feed of drinks that carry carbohydrate and no protein or fat, by 0.3–0.5.
    - Downside: it expresses a weeks-long effect as a per-drink discount the acute trials do not show.
- **Recommendation: (a),** with the limitation string naming it.

### C9. Ketosis damps the deficit drive (no new term)
- **Finding.**
  - Ketosis blunts the deficit's rise in appetite (S1451, S1452, S1259), and exogenous ketones suppress hunger (S1453).
  - The size and the β-hydroxybutyrate threshold are open (S1455).
  - Hall 2021 (S1420) is confounded by energy density and food source. It does not show that keto sates less.
- **Certainty.** Moderate in direction, low in size.
- **A conflict worth knowing.** The energy state adds 0.3 × (1 − g) as muscle glycogen g falls (`NR_Kernel_Energy.lua:265`, a game choice with no row). If a low-carbohydrate diet runs g down in the mod's glycogen kernel, which I have not checked, the model raises hunger exactly where these rows find it blunted.
- **What it reads.** The daily carbohydrate total (`NR_Kernel_Energy.lua:244`) and g.
- **Options.**
  - (a) Neutral. Downside: the conflict above stands.
  - (b) Damp the deficit terms after about 2–3 days under about 50 g/d of carbohydrate (a game choice). Downside: it needs a window field, and its size rests on an open row.
- **Recommendation: (a)** until S1455 has a size. Check g's path in the C3 fast replay.

### C10. Resistance work weighted 0.5 (#3616)
- **Finding.** Resistance sessions taken to fatigue suppress hunger about as much as aerobic work (S1508; S1509, d > 1.10 at 0 min; S1301), and the suppression is gone by 60 min. S1305, a narrative review, says it is "less marked".
- **Certainty: low.** Three small trials, no pooling.
- **Game size.** The swing state stands in for resistance work, and melee is common. A depth of 1.0 would double suppression in fights.
- **Options.**
  - (a) Keep 0.5. Weak spot: the newer trials say equal depth.
  - (b) Depth 1.0 with C1's fast decay. Downside: low certainty, and the swing state is not the trials' session to fatigue.
- **Recommendation: (a).**

### C11–C15. Low priority, with recommendations

| | Finding (rows) | Certainty | Reads | Options and downsides | Recommendation |
|---|---|---|---|---|---|
| C11 Monotony | Liking falls with repeated daily exposure (S1592–S1595, S1597); intake is inconsistent (S1595, S1596); staples resist it (S1593) | moderate for liking, low for intake | the eat; vanilla's per-item boredom and unhappiness adjustments are #0041–#0043; it needs a per-player recent-eats field | (a) none: survival-diet monotony stays absent; (b) Bored and Unhappy deltas at the eat: a new record field, a mood design outside satiety, with a game-choice slope | defer to its own mood design; never in hunger |
| C12 Nicotine withdrawal | +227 kcal/d (S1576, one experiment with n = 13), fading by 26 weeks (S1577); the weight gain is pooled (S1575) | low size | the NICOTINE_WITHDRAWAL stat is registered (#2205); whether it moves on a dedicated server is unread | (a) neutral; (b) a hunger factor: its size rests on one small experiment | (a); a jar read first |
| C13 Alcohol aperitif | food +343 kJ after alcohol, and its energy is not compensated (S1578); 32 g against 8 g (S1580); no row tests 8 g against 0 g | moderate | blood alcohol (`NR_Kernel_Acute.lua:292`) | (a) neutral; ethanol's kcal still feed P (#3622), which the evidence does not support; (b) exclude ethanol's kcal from P, or add a next-meal bump: about 80 kcal, small | (a), named |
| C14 Aerated food volume | twice the volume at equal energy gives −12 % at the next meal (S1483); S1484 is satiation of the snack itself | low to moderate | a per-item volume field the data lack | (a) neutral: popcorn and crisps under-sate; (b) a sourced per-item volume factor in the food pipeline | (a), named |
| C15 Injury | burn metabolism at 130–140 % of predicted (S1549); appetite falls after surgery (S1550); open S1551 | low | wound timers (`NR_Server_Effects.lua:93-98`); the energy model adds no injury expenditure, so the conflict with the deficit drive is latent today | (a) none; (b) an appetite cut | (a), plus a rule: any future injury hypermetabolism must not feed the deficit drive |

## 3. Things to leave neutral

- **Fibre's own effect:** S1338, S1344, S1346, S1366 and S1369. The whole-grain subgroup matched on calories is non-significant and low in certainty (S1365).
- **Glycaemic index:** next-meal ES −0.01 (S1421). Bornet's positive reading is unpooled and industry-authored (S1422).
- **Fat type:**
  - saturated and unsaturated fat do not differ, at low certainty (S1435, S1438);
  - omega-3 has a pooled null on overall appetite (S1439, against S1440);
  - MCT gives ES −0.44 at low certainty (S1434), and no game food is an MCT source.
- **Stress:** g 0.114 overall; in strong-quality studies g 0.039, small but significant (p = .018), with quality contrasts that are not significant (S1552, S1553). The laboratory and exam nulls are S1555 and S1558.
- **Mood:** negative mood raises eating only in restrained eaters (S1560, weighted over S1561).
- **Boredom:** the effect is a rise in snacking when food is at hand, against a sad film, not a neutral one (S1562, S1563). It has no size.
- **Caffeine:** null or transient (S1582–S1584).
- **Mild dehydration (≤ 3 %):** two null RCTs (S1585, S1586). Deeper dehydration is open (S1587).
- **Eating rate:** it moves meal size (S1486, S1487) but not later hunger (S1486, S1488), and the player governs it.
- **Palatability:** it changes satiation, not later satiety (S1599 over S1602).
- **Social eating:** SMD 0.76 with friends and null with strangers (S1619, S1620), partly through longer meals. Meal size is the player's.

## 4. Open gaps that would change a decision

- **The request-anchored mapping (65 mm read as 0.25).** No row gives a pre-meal VAS. C1, C2 and C5 all convert through it.
- **S1334:** the post-bout decay constant (C1).
- **S1335:** the compensation time course, and dose-response at heavy-work doses. The one trial is at 102–232 kcal/d (C4).
- **S1268** and **S1414:** the protein weight as a pooled ratio, and protein leverage (C5).
- **Step against graded:** the sleep-loss rise has no row (C2).
- **S1271:** hunger per percent of deficit, which bounds the deficit floor the C3 replays test.
- **S1455:** ketosis size and threshold (C9).
- **Illness and injury:**
  - S1544, the size of adult infection anorexia;
  - S1548, nausea on intake;
  - S1551, pain or injury on appetite;
  - S1545, the energy-expenditure rise per °C of fever (C7, C15).
- **S1539:** heat or cold over days of outdoor work (C6).
- **Jar reads:** what drives SICKNESS and NICOTINE_WITHDRAWAL on a dedicated server (C7, C12).

## 5. Decisions for Angus

1. **C1:** re-anchor the acute term on the pooled mm readings with a faster decay than rise, and settle S1334? Recommended: yes.
2. **C2:** add a sleep-debt hunger factor, graded on the mod's debt hours and capped at the pooled size? Recommended: yes.
3. **C3:** add the 36 h fast and six-against-three-meal replays as pinned readings? Recommended: yes.
4. **C4:** give the exercise lag a gain of about 0.7 with τ refit (about 16 d)? Recommended: yes, at low priority.
5. **C5:** spike a protein term in fullness, and ship it only if every hard replay holds at 1.1×? Recommended: yes, as a spike.
6. **C6:** leave temperature to cold's expenditure path and name heat? Recommended: yes.
7. **C7:** a jar read of SICKNESS before any illness term, with FOOD_SICKNESS kept neutral? Recommended: yes.
8. **C8, C9, C13, C14:** keep sugary drinks, ketosis, the aperitif and aerated volume neutral, each named in the limitation string? Recommended: yes.
9. **C10:** keep resistance at 0.5? Recommended: yes.
10. **C11:** monotony as a separate mood design after Plan 11b, never in hunger? Recommended: yes.
11. **C15:** a standing rule that injury expenditure, if ever modelled, does not feed the deficit drive? Recommended: yes.
12. **Packaging:** land 1–5 as one plan, with one golden re-record named "satiety revisit"? Recommended: yes.
