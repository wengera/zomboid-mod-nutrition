# Game feel: Nutrition Revamp intertwined with the game — design

Status: for Angus's review. It grows out of the 2026-10-16 game-feel review:
- the decisions, in Angus's words: `.superpowers/sdd/game-feel-review/decisions.md`;
- the evidence: `report.md` and `seesaw.md` beside that file;
- the outline: `docs/superpowers/specs/2026-10-16-game-feel-outline.md`;
- the research: `docs/superpowers/research/2026-10-16-game-feel/` (volume, water and starvation reports, each citation-reviewed) and the game-code checks in `.superpowers/sdd/game-feel-research/jar-checks.md`;
- the science rows S2209–S2262, minted at 7bf376d6, af5ad2ee and 32efd2fc.

## 1. Principles (Angus, 2026-10-16)
1. **"Subjective things closer to vanilla, objective things science supported."**
   - **Vanilla:** pacing, how often things come up, effect sizes, when a crisis lands, and how signals are presented.
   - **Science:** which effects happen, their order, relative severity, triggers, and real energy and water needs.
   - Where they conflict, the guide states the bend.
2. **Survival difficulty that comes from real physiology is where the mod is meant to be tougher than vanilla.** That covers the food economy (item 4) and the body's slow record (items 6 and 7).
3. **Health drains signal damage, not lethality:**
   - a state drains health early, at vanilla's pacing, to a floor;
   - the floor deepens on science's clock and reaches 0 only at the state's real death point;
   - every real killer kills then, with no toggle;
   - `NR.DeficienciesCanKill` is removed.

## 2. Hunger and eating
### 2.1 The calibrated hunger writer (item 3)
The study-fitted satiety model is unchanged and yields its internal hunger, h_model. The value written to HUNGER is `H = curve(h_model)`, a monotone curve calibrated so that:
- a satisfying meal (about a third of the day's kcal) reads H ≈ 0;
- on a three-meal day, Peckish (H > 0.15) returns about 4 h after the meal and Hungry (H > 0.25) about 6–8 h after, vanilla's cadence;
- a snack (≤ 200 kcal) moves H less than a meal;
- above the model's fasting plateau, the curve hands over to the starvation stage (§ 3.1).

The study tests and oracles read h_model before the curve. A dead zone at each moodle threshold, about 0.02, stops blinking (item 10b). The morning circadian dip applies only when fed, so H never falls during a fast (item 10a, a stated bend).

### 2.2 Fullness between weight and volume (item 11)
- The satiety mass becomes `w + β × (V − w)`, with V a food's plate volume:
  - β = 0.05, a game choice inside the evidence's range of 0–0.1 (S1484, S2209 to S2215);
  - 0.15 is the highest defensible value.
- The stomach's physical capacities (730 g comfortable, 1,100 g hard) stay on mass.
- A new `ml_per_g` column in the food table comes from USDA SR Legacy portions (S2212). The parse rules are in volume-report.md § 4:
  - the unit is in the modifier text;
  - the cut matters;
  - a dry-mapped item eaten cooked takes the cooked food's measure.
- Drunk water counts at its own mass; β touches no liquid.

### 2.3 Overfull consequences and the eating block (item 11)
- **Overfull 3:** a movement and endurance penalty of vanilla size, labelled a game choice.
- **Overfull 4:** nausea (a FOOD_SICKNESS rung) and refused eating.
- **The refusal is vanilla's own.** Each minute the mod writes vanilla's food timer (`setHealthFromFoodTimer`) from its own fullness:
  - 1–3200 shows Well Fed;
  - above 3200 at Overfull 4 greys out eating in every vanilla path, including the server's open-and-eat craft (jar-checks Check 1).
- No vomit: vanilla has no vomit path the server can drive (Plan 15 Task 8); Overfull 4 is nausea and the refusal.
- A drink lands whole in its minute, so 500 g drunk right after a 667 kcal plate still holds Overfull 4 for about 5 min (Task 14b; it was 23).

### 2.4 Well Fed (item 3)
- Well Fed shows from the timer above after a satisfying meal.
- Vanilla's food heal, 0.015 health per timer unit, which runs through any drain: the mod sets `setHealthFromFood(0)` while any drain state is active.
- Otherwise it keeps a gentle heal, a game choice in vanilla's spirit, with a size for the plan to set.
- The mod re-writes it after a load, since it is not saved.

### 2.5 Real energy needs (item 4)
- About 2,000 kcal a day at rest is unchanged, and there is no metabolism option.
- The vanilla hunger line in the tooltip is replaced by "fills you for about N h" and the kcal.

## 3. Starvation, dehydration and lethal deficiencies (items 2, 5)
### 3.1 Lifting the caps (option B)
- **The caps lift:** the 0.69 hunger cap at true starvation (§ 3.2's stage 2), and the 0.83 thirst cap at Parched.
- **What shows:** vanilla's own Starving and Parched moodles.
- **Vanilla's level-4 drain is switched off:** while HUNGER or THIRST is at level 4, the mod sets vanilla's shared drain constant to 0, so vanilla's day-length-scaled starvation and thirst deaths never run.
- **The mod re-applies the drains that constant also carries,** at vanilla's rates, while it is 0:
  - sickness;
  - bleeding;
  - heavy load;
  - weight under 35 kg.
- **It re-writes the constant after every load.**
- **A live run proves** that bleeding and sickness still hurt while starving.
- **Overlay (Mode 2) is vanilla's here (Plan 15 close, ruling M2):** vanilla owns hunger and thirst, so its own level-4 hunger and thirst drains, and their deaths, run as in the base game, and the mod's starvation and dehydration drain states do not run. The deficiency, sodium and iron drains still do, and the starvation clock and its effect phases still run.
- **The fresh-record seed plate also lands in Overlay** (Plan 15 Task 13 fix 1, I2): its kcal, nutrients and stomach mass count, though no first hunger write is made there. The writer's Overlay limitation line names both.

### 3.2 The drain-and-floor model
**Drain:** each state drains overall health through `ReduceGeneralHealth`. That spreads evenly with no wound and never overshoots (jar-checks Check 2). The rate is per game day, independent of day length.

**Floor:**
- Each state holds a floor that deepens on science's clock and reaches 0 at the state's death point.
- While a drain state is active, the mod suppresses regeneration and the food heal, so health holds at the floor without a sawtooth.
- **Floors stay above 10 until the final stage,** because at 10 or below vanilla wakes any sleeper every tick. The last stage before death is sleepless by design.

| State | First signs (science) | Vanilla-paced first floor | Death point (science) |
|---|---|---|---|
| Starvation | days 0–3: hunger; days 3–14: weakness, dizziness, apathy (S2231–S2262) | about 50 health by about day 2.5–4 | **BMI ≈ 12** (S2231–S2262; Speakman 12, ≤ 13) |
| Dehydration | 2 % thirst; 2–4 % performance; 4–6 % weary, apathetic, dizzy (about 4.2 % and 5.8 %, S2248); about 11 % delirium | from the 4 % onset (about 32 h at rest), about 50 by about 38 h (ruling M1) | **about 17 % body-water deficit**, a game choice inside 15–19 % (about 5–7 days at rest) |
| Wet beriberi | clinical after weeks on a thiamine-poor diet | vanilla-paced from clinical | about 5 weeks after clinical (an inference, S2255; S1169 open) |
| Scurvy | clinical at about 30–40 days | vanilla-paced from clinical | a game choice of months (S1168 open) |
| Pellagra | clinical at about 50–60 days | vanilla-paced from clinical | months to years (S1170 open) |

The other lethal states (sodium, iron) keep their current conditions under the same model.

### 3.3 Effects in science's order, at vanilla's sizes
- **Starvation:** weakness, then cold intolerance and slower healing, then infection and mood.
  - Appetite eases after about day 3 (direction only, S2231–S2262), but the Starving moodle stays on screen. That is the stated bend.
  - The phase bands are a game-pacing choice.
- **Dehydration:**
  - 2 %: fatigue and endurance;
  - 3–4 %: weakness and heat intolerance;
  - about 4–6 %: apathy and dizziness. Panic moves here from 1.5 %;
  - 10 %+: confusion and collapse.

### 3.4 The water base
- Basal net water loss is `2000 + 32 × (lm − 52.02)` g a day (S2216–S2230, water-report.md). It replaces `K.fluids.AI` 3700/2700.
- It is sex-neutral and anchored on the mod's no-trait lean mass.
- Sweat, cold and alcohol losses stay on top.
- High Thirst (×1.5–2) and Low Thirst (×0.5), plus the stat-decrease option, scale basal loss only.

## 4. Moodles and signals (items 1, 8, 10c–10e)
- **Removed:** the Energy moodle (item 1) and the Hydration moodle (item 10e). The internal energy state stays.
- **The Deficiency moodle** reads only nutrients whose grade drives an effect, with a test keeping its list in step with the effects table (item 8).
- **A dead zone on the monotony mood floor** (item 10c).
- **A new option** hides level 1 of Stimulant, Sleep and Excess (item 10d).
- **Panel lines:**
  - "weakened by starvation" or the active drain state;
  - a weight trend: "losing", "steady" or "gaining";
  - dehydration %.

## 5. Coffee, beer and sleep (item 9)
- **Science:** caffeine absorption, clearance, tolerance and withdrawal; alcohol clearance at about one drink an hour; the hangover's timing; sleep debt and its hunger effect.
- **Game sizes, the default:**
  - a cup's peak fatigue relief at about 2× vanilla's;
  - about 6 intoxication per beer, stacking;
  - a mild hangover.
- **A new option** (a name like `NR.StimulantRealism`): Game or Realistic. Realistic keeps today's strengths.

## 6. Unchanged by decision
- Weight at science's pace, with the panel trend (item 6).
- Strength at 4 years to level 10, with detraining from science (item 7).

## 7. Verification
**Offline:**
- each new constant is tested against its row;
- the curve against the vanilla cadence;
- the floors against the death points;
- the golden re-records under named causes;
- the oracles re-pointed at h_model.

**Live sessions:**
1. A three-meal day: the cadence and Well Fed against vanilla.
2. Overeating: 1 kg of broccoli stops partway, and Overfull 4 refuses the eat.
3. A starvation run: the cap lifts, Starving shows, health reaches the first floor, and eating recovers it.
4. A starvation run with a bleed or sickness: vanilla's other drains still apply.
5. A no-water run: Parched, and the first floor around 35 h.
6. High Thirst on and off.

## 8. Follow-on edits
- **The guide:** every chart a change moves, and notes 10f and 10g.
- **The README, COMPATIBILITY and CHANGELOG.**
- **Register rows to supersede:** the caps, the Energy and Hydration moodles, the water base, the stimulant strengths, the old lethality times and `NR.DeficienciesCanKill`.
- **The jar-checks delta (J1.1–J2.3):** renamed to T ids and minted with owner sentences in the plan's first task.

## 9. Order
1. The jar-checks claims and the live checks of § 3.1's constant handling.
2. § 3, the floors, caps and water base.
3. § 2, the writer, fullness, Overfull and Well Fed.
4. § 4.
5. § 5.
6. The live sessions.
7. The guide and docs.

## 10. Game choices the plan sets (labelled in code)
The plan's design list, then every game choice the tasks made, each labelled "game choice" in its code comment.

**The design list:**
- the curve's knots;
- the dead-zone width;
- the Overfull 3 penalty size;
- the gentle Well Fed heal;
- each floor's curve and drain rate;
- dehydration's 17 % death point;
- scurvy's and pellagra's death times;
- the stimulant game sizes.

**Water (Task 3, § 3.4):**
- the water anchor `LM_REF` 52.02 kg, the no-trait lean mass;
- the trait multipliers on basal loss: High Thirst ×1.5 (inside the decision's ×1.5–2) and Low Thirst ×0.5.

**Thiamine (Task 4b):** the clinical onset at 42 days with none eaten (ruling M2), inside S2255's one to three months.

**Thirst and hunger caps (Task 5, § 3.1):**
- the thirst knots 1/2/3/4 % → 0.12/0.25/0.45/0.84, with 0.45 at 3 % for the osmotic term and Parched on the 4 % onset;
- the 0.71 starving minimum, over HUNGRY level 4's strict 0.70, under the acute onset only (ruling I2).

**The hunger curve (Tasks 6 and 6c, § 2.1):**
- the knots 0.099, 0.214688, 0.299375, 0.42875 and 0.734688 (Task 14b's re-fit on the new liquid lane, fit-hunger-curve-20261017c; Task 6c's foot 0.097 and X[3] 0.210312 before);
- **The liquid lane (Task 14b, § 2.2):** drunk water is slowed only by the drink's own kcal (`stomach.liqKcal`; S2265–S2277, science, not a game choice); the report's 0.02 min per plate kcal hedge, a game choice, is declined.
- the dead zone 0.02 and the hold offset `HOLD_EPS` 0.001;
- the fed threshold `FED_M` 3.80654 weighted kcal (the meal pool's request level, `MEAL_REQ`);
- the per-meal compromise and its weights (breakfast 0.5, lunch and dinner 1, the breakfast carry-over halved);
- dinner's return 23 % short of vanilla's, from the evening circadian rise, a stated bend;
- the 21 % hungry share, a stated bend;
- Well Fed fixed in game hours (the meal pool at `WELL_FED_M` or more), while vanilla's food timer scales with the day length.

**The starvation onset (Task 6 fixes, § 3.2):**
- the acute onset after 30 unfed hours (`STARVE_ONSET_H`), on the continuous unfed clock;
- the fallback: the intake absorbed today and over the three closed record days, with what is still in the stomach, at or under 600 kcal (`RECENT_MIN_KCAL`), read over the record's day buckets after three day closes;
- the meal spell `SUSPEND_M` 236.44 weighted kcal, the pool a 200 kcal mixed snack lands (Plan 15 close, H1): only a fed spell that reached it suspends the fallback or, inside the state, resets the unfed clock, so an hourly floret no longer keeps a starving body out of the state. A floret diet begun from a fed body with no fast first stays out of the acute onset (its intake is over the fallback's 600) until the chronic onset at BMI 13 catches it, a stated limit;
- `BMI_CHRONIC` 13, the chronic onset whatever the intake (ruling M3), inside S2234's 12–13;
- the starvation phase hours 30, 72 and 336 (S2247 open).

**The floors and rates (Tasks 4 and 4b, § 3.2):**
- the first floor 50 and the knee `BMI_KNEE` 12.5;
- `DEF_HOLD_H` 72 (three days at the first floor) and `DEF_FINAL_H` 48 (the last two days, 10 to 0);
- the rates a game day: starvation 25, dehydration 200, the deficiencies 50/3; sodium 400 and iron 100 (100 over their 6 h and 24 h);
- the death times: scurvy 90 days, pellagra 180 days, sodium 6 h and iron 24 h after onset, the last 2 h from 10 to 0 (`ACUTE_FINAL_H`).

**Volume (Task 7, § 2.2):** β 0.05 and the family judgements.

**The food-timer bridge and Overfull (Task 8, §§ 2.3–2.4):**
- Well Fed at M ≥ 435 (`WELL_FED_M`);
- the timer band values by day length (`K.view.timerValues`: each held through its minute's drain, never under the 90-minute values);
- the endurance cap 0.73 at Overfull 3 and 4, sized by `capAt`, with `END_FLOOR` 0.51 just above level 1's 0.5;
- Endurance level 1's costs, which the cap brings: Heavy Load level 1's base-speed cut and the 0.07 combat cut (#2313, #2324);
- the food heal 0.0087 × 90 / dayMin per multiplier unit while Well Fed (`REGEN_FOOD`), 0 at Overfull 4 and under a drain;
- FOOD_SICKNESS 30 at Overfull 4 (nausea as SICK 1).

**Display (Task 9, § 4):**
- `DEHYD_SHOW` 1 %, the panel's dehydration line;
- `FILL_MIN_H` 0.5 h, the tooltip's fill step;
- `FILL_TOL` 0.10, the kcal share within which the fill line shows;
- the weight trend read off `K.body.flags`.

**Stimulants (Task 10, § 5):**
- the S6b schedule behind the 20/31 peaks;
- "a held cup";
- the 0.05 % hangover threshold;
- the hangover unhappiness 21/42.

**The fresh-record seed plate (Task 13 fix 1):** the plate of the guide's foods sized to the least kcal whose first write is within the dead zone of the spawn HUNGER, at most one 667 kcal plate. It also lands in Overlay (I2), and the writer's limitation line names it.

**Measurement (Task 13 F14):** the food-economy bend, about 3.75 cans a day against vanilla's 2.3, is the decisions' estimate. No register row carries it, so no page states it as a number; about 2,000 kcal a day is about 3.7 of vanilla's 540 kcal cans.
