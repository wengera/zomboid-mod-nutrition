# Satiety from physiology: design (Plan 11c)

Status: approved in brainstorming on 2026-10-08 (Angus: "go ahead with your assumptions, spec, plan, build subagent driven"). It supersedes Decision 2 (c) of `2026-10-07-plan-11-decisions.md`: the relief keyed to vanilla's `getHungerChange`, the bulk factor β and the `NR.SatietyBulk` option. It keeps Decision 1, the hybrid: the writer writes HUNGER once a player-minute.

## 1. Goal

A character's hunger follows what they ate, as the evidence says food satiates: how much it fills the stomach and for how long, and how strongly its nutrients keep hunger away afterwards. On top of that, a calorie deficit drives hunger up. Vanilla's per-item hunger value no longer decides satiety.

Nonsensical vanilla recipes are not the mod's problem. Recipe conservation (Plan 11a Task 16) is a report and never a fix.

## 2. Decisions taken (Angus, 2026-10-08)

1. Two signals: stomach fullness F, and a post-absorptive satiety pool P.
2. Real physiology in game hours. A typical mixed meal of about 600–700 kcal satisfies an adult for about 4–5 game hours, which gives about three meals a day.
3. A deficit drive D from the energy state, kept beside the meal signals.
4. A soft cap: eating near stomach capacity brings discomfort, never a hard block.
5. Evidence is measured or neutral. Every shipped constant rests on a settled row of `docs/reference/science.tsv` (CLAUDE.md § 4.8). A component whose evidence is mixed or absent gets no special effect: it counts only through its energy and its mass.
6. Approach A: two compartments, reusing the existing stomach kernel.

## 3. Architecture

### 3.1 Units

- **`K.stomach`** (`NR_Kernel_Stomach.lua`, exists). It keeps its buffer, its emptying and its absorption, with four changes:
  - **Fill by mass.** `K.stomach.massOf(vector)` is the food's mass in grams: water + protein + carbohydrates + lipids + fibre, from the vector's gram keys. It replaces `bulkOf`'s mixed game-choice unit. `stomach.mass` replaces `stomach.bulk`. Fullness is mass over capacity: liquid and food volumes are taken as mass at density 1, which is the evidence's own approximation, and the harvest confirms it.
  - **A liquid lane.** A drink lands in `stomach.liquid`, a second buffer that empties with the liquid half-time. A food lands in the solid buffer. Water inside a food stays with the food. This is the mechanism behind the soup-against-water-alongside result, if the harvest settles it. If it does not settle, both lanes share one half-time and the design degrades to one buffer.
  - **The emptied vector.** Each step hands the energy that left the stomach, per macronutrient (`protein`, `carbohydrates`, `lipids` in kcal), to the satiety pool. `K.stomach.empty` already returns the emptied vector, so this is a read, not new work.
  - **The gastric constants.** `HALF_TIME_H` (S0130) and `compositionScale` (S0131) rest on open rows today. The harvest settles them or keeps them as labelled game choices.
- **`K.satiety`** (`NR_Kernel_Satiety.lua`, rewritten). It holds one state value in the record, `record.satiety = { P = number, v = 4 }`, and pure functions:
  - `K.satiety.fill(mass, capacity) -> F` in [0, 1]: `clamp(mass / capacity, 0, 1)`.
  - `K.satiety.feed(P, emptiedKcal) -> P`: `P + Σ_k w_k × kcal_k` over protein, carbohydrates and lipids. Each `w_k` is a settled weight; a neutral component takes the common weight.
  - `K.satiety.decay(P, dtH, halfLifeH, trait) -> P`: first-order decay, `P × exp(−ln2 × dtH × trait / halfLifeH)`.
  - `K.satiety.post(P) -> Pn` in [0, 1): `P / (P + P50)`, a saturating read whose half-point P50 is calibrated.
  - `K.satiety.sated(F, Pn) -> Z` in [0, 1]: `1 − (1 − a·F) × (1 − Pn)`. Either signal sates, and together they compound. The fullness weight `a` is calibrated.
  - `K.satiety.seedP(hunger, F, energyState) -> P`: the P for which `hungerTarget(sated(F, post(P)), energyState)` equals `hunger`, clamped at 0. This is the migration seed.
- **The hunger function.** It reuses `K.hybrid.hungerTarget(x, energyState)` with `x = Z`. Its `(1 − x) × energyState` term and its deficit floor `0.15 × max(0, energyState − 1)` are the deficit drive D. The floor's coefficient 0.15 is re-derived from the harvest's energy-restriction rows. The 0.69 cap stays.
- **The soft cap** sits in the intake, after an eat lands. If `stomach.mass > capacityMax`, the intake adds discomfort to the player. The effect, its size and its decay follow the 42.21 read of what vanilla already does when a full character eats; the plan's first wiring task reads it before designing the effect. It never blocks eating.

### 3.2 Data flow

- **Per eat or drink:** the delivered vector, with calories from vanilla's delivered macros and water and fibre from our data, goes into the solid lane (food) or the liquid lane (drink). Vanilla's `getHungerChange` is not read for satiety.
- **Per player-minute** (writer and kinetics, inside the budgeted queue):
  1. The stomach empties both lanes.
  2. The emptied energy feeds P.
  3. P decays.
  4. F is read from the mass.
  5. Z = sated(F, post(P)).
  6. The writer writes HUNGER = `hungerTarget(Z, energyState)`, capped at 0.69.

### 3.3 What stays

- The queue (Plan 11a Task 9).
- The writer's once-a-minute write and its other stats (Task 14).
- The store (Task 11).
- The heals and guards (Task 12). P and the stomach's new fields join the guard lists and CROSS gets writer rows.
- The bus.
- Vanilla's instant HUNGER drop on eating, which shows until the next minute's write; the limitation string says so.

### 3.4 What goes

- Task 15's `K.satiety.relief`, `bulkFactor`, `R0`, `LO`, `HI`, `BETA` and `add`.
- The `NR.SatietyBulk` sandbox option and its translation strings.
- `IN.sate`'s hunger-change read.
- The drink special case of rulings T15-2 and T15-3: a drink is water and sugar in the liquid lane now.
- `record.satietyStepped`. The v4 record's P replaces it.
- The vanilla rate-based decay of Task 15 (`K.satiety.rate`, `step`). P's measured half-life replaces vanilla's hunger rates for satiety.
- The traits (Hearty Appetite ×1.5, Light Eater ×0.75, #0485) stay as vanilla's own game numbers, applied to P's decay. They are vanilla game choices, not science, and are labelled so.

## 4. Edge cases

- **Migration (v3 to v4).** A v3 record carries `satiety` (Task 15's scalar) and maybe `satietyStepped`. On load both are dropped. On the writer's first step, P is seeded by `seedP(HUNGER, F, energyState)`, so a hungry character stays hungry and a fed one stays fed. A record with no stomach starts with an empty stomach, mass 0. The record version goes from 3 to 4.
- **Cooking, staleness, rotting.** Satiety follows composition. Cooking changes satiety only through the delivered calories it changes; vanilla's ×1.3 cooked hunger ladder no longer matters.
- **Partial eats** feed the eaten fraction of the vector, as today.
- **Zero-energy items** (salt, spices, pills) add only their small mass.
- **Eats by another mod through a direct `Eat`.** The reconcile path credits them as intake. The plan confirms they reach the stomach; if they do not, the limitation string names it.
- **Sleep.** Both lanes and P run on game time. Vanilla's sleeping hunger rate no longer applies to satiety.
- **Overlay mode (Mode 2).** Vanilla owns HUNGER, and the model steps without writing.
- **Non-finite state.** P is guarded. A non-finite P is re-seeded through `seedP`, and the heal counts it.

## 5. Evidence (the harvest)

The plan's first task is an Opus harvest. It writes science part files, which the controller applies with `tools/science_delta.py`, and it resolves every citation against its record before minting (§ 4.8). The effects to harvest:

1. **Macronutrient satiety per kcal** (protein against carbohydrate against fat), from preload studies and meta-analyses. This sets `w_k`.
2. **Energy density and food volume**, including water incorporated into food against water drunk alongside (Rolls's work). This sets `a` and the liquid lane's reality.
3. **Fibre**, total and viscous, and its effect on fullness and emptying. It may land neutral.
4. **Gastric emptying half-times** by meal size, composition and liquid against solid. This settles S0130 and S0131 or keeps them as game choices.
5. **Time to returning hunger after a mixed meal.** This is the 4–5 h anchor, and it sets the half-life and P50 jointly with `w_k`.
6. **Comfortable and maximal stomach capacity.** This sets `capacity` and `capacityMax`.
7. **Hunger under energy restriction**, from controlled trials and ghrelin and leptin studies. This re-derives the deficit floor.
8. **Contested effects, decided by the harvest under rule 5:** sugar against starch, liquid against solid calories, and fat's satiety per kcal.

Each constant's comment names its science row. A component with no settled row ships at the neutral value, and its limitation string says so.

### 5a. The harvest's outcome (rows S1222–S1272, minted 2026-10-08) and the design rulings it forces

The harvest and its Opus review settled what follows; the plan builds to it. It overrides § 3 where they disagree.

- **Solid emptying is linear, not first-order** (S1272, which supersedes S0130: Moore 1981, 77/146/277 min half-emptying for 300/900/1692 g). The energy-delivery rate is about 2–3 kcal/min (S0131 settled: Hunt 1985, an overall mean of 2.5 kcal/min). It rises with load and energy density (Hunt 1985, Hunt & Stubbs, Calbet).
  - The kcal/min figures come from liquid carbohydrate meals. Applying them to solids is a **labelled inference**, not a settled constant.
  - Calbet did not test fat. Whether fat, protein and carbohydrate slow emptying equally per kcal is unsettled, and the model treats them equally as the neutral choice.
  - **Ruling 11c-4:** the solid lane empties energy at a zero-order rate that rises with the buffered energy, calibrated to the rows. It replaces `K.stomach.emptyFraction`'s first-order half-time. A component with no energy (water, fibre) leaves in proportion as the energy does.
- **The liquid phase follows the meal.** Water drunk alone half-empties in about 13 min (Mudie). The liquid phase of a meal takes 40–178 min and grows with meal size (Moore 1981). An energy-dense drink empties by its energy (Camps 2016: 26.5 min at 100 kcal against 69.5 min at 500 kcal).
  - **Ruling 11c-5:** the liquid lane exists. Its rate is fast when the stomach holds no solid energy and slows as the solid lane's energy rises. A drink's own energy goes to the solid lane's energy budget, so a sugary drink empties at the energy rate. A fixed 13-min water lane inside a meal is not built.
- **Fibre is neutral** (ruling 11c-6). Clark & Slavin 2013 (78 % of 107 treatments null) and Wolever stand against Salleh, S0487 and Benini. Fibre counts only through its mass. Neutral is a named game choice resting on those paired rows.
- **Macronutrient weights** (ruling 11c-7):
  - Protein satiates more per kcal (Kohanmoo 2020, Dhillon 2016, Marmonier 2000, de Castro 1988), against Raben's null and the long-term nulls.
  - Carbohydrate against fat is disputed (Woodend, Melanson, Rolls 1999, Holt). The neutral ruling is to weight them equally. That is not an evidenced tie.
  - The size of the protein weight is a game choice, because S1268 is open, calibrated so the oracle's protein preload lands inside its studies' range.
- **Time to returning hunger** after a mixed meal is 247–321 min (Callahan 2004) and 320–425 min time-blinded (Cummings 2004). The 4–5 h anchor holds and is slightly conservative. P's half-life is a game choice (S1270 open) fitted jointly with P50 and the protein weight against these rows.
- **Capacity:**
  - 428 mL to satiation and 734 mL to maximum, for water drunk fast by young women (van Dyck 2016).
  - 937–1048 mL for slow nutrient drinks, measured while the stomach empties.
  - 1100 mL for a balloon (n = 4).
  - Tack 2003: volume, not kcal, sets maximum satiety. No solid-mass capacity exists.
  - **Ruling 11c-8:** comfortable capacity is about 430 mL of stomach mass and the soft cap's threshold about 730 mL. Each is a labelled inference from the water-load rows, applied to stomach mass at density 1. The nutrient-drink figures bound the cap from above.
- **The deficit floor stays a game choice.** The direction is settled (Polidori 2016, COH: about 100 kcal/d of appetite per kg lost; CALERIE 2 hunger < 10 mm over 2 y; ghrelin rises in non-RCTs, Jin 2025). S1271 (VAS per % deficit) is open. `hungerTarget`'s 0.15 keeps its label.
- **Contested effects ship neutral:** sugar against starch (absent), liquid against solid calories (mixed), fat per kcal (mixed). Each counts only through its energy and mass.

### 5b. The structure chosen by fit (structure D; ruling 11c-30, Angus 2026-10-08: "whichever model best fits what we would expect to see and tests match experimental outcome")

Spike 2 (`.superpowers/sdd/2026-10-08-plan-11c-satiety/task-4s2-report.md`) tested four structures; D's worst hard-target ratio is 1.040 (Rolls's three arms, Callahan from the request and fasted, the 650 kcal anchor, a fasted breakfast). The text below overrides §§ 2, 3.1, 3.2, 5a and 6 where they disagree.

**§ 3.1, `K.stomach`, the third bullet ("The emptied vector").** Replace it with:
> - **The emptied vector** feeds absorption only. Satiety is booked at the eat (ruling 11c-27).
> - `K.stomach.satietyMass(stomach)` is the hunger-relevant mass: the solid lane's mass plus `LIQUID_WEIGHT` × the liquid lane. Drunk liquid counts at a fifth, because water served as a beverage did not affect satiety (S1231) while a drink's volume did move intake (S1233). The 0.2 is fitted between the two.
> - The soft cap still reads `K.stomach.mass`, both lanes whole (S1250).

**§ 3.1, `K.satiety`.** Replace the `fill`, `feed`, `post` and `seedP` bullets, and the opening phrase "a post-absorptive satiety pool P" (also in § 2 item 1, as "a meal satiety pool P"), with:
> - `K.satiety.fill(satietyMass, capacity) -> F`: `clamp(satietyMass / capacity, 0, 1)` against `CAPACITY_MAX_G` (ruling 11c-19).
> - `K.satiety.feed(P, eatenVector) -> P`: `P + Σ_k w_k × kcal_k` over the eaten vector's protein, carbohydrates and lipids. It is called once per eat or drink with the delivered vector (a partial eat with its fraction), never per minute.
> - `K.satiety.post(P) -> Pn`: `1 − 1 / (1 + 3 × (P / P_REQ)^STEEP)`. With an empty stomach, P_REQ is the pool that reads the request level 0.25; 3 = (1 − 0.25) / 0.25. STEEP 0.08 makes the read near-logarithmic, so a snack leaves hunger intermediate and the time to the request grows with the log of the meal (S1247).
> - `K.satiety.sated(F, Pn)`: unchanged, `1 − (1 − FULL_WEIGHT·F)(1 − Pn)`.
> - `K.satiety.seedP(hunger, F, energyState) -> P`: the inverse of the read, `P_REQ × (pn / (3 (1 − pn)))^(1/STEEP)`, capped at `P_SEED_MAX`. The cap is the pool of a large meal, so a vanilla HUNGER of 0 does not seed a pool that sates for days.

**§ 3.2.**
- "Per eat or drink" gains: "and its weighted kcal feed P".
- In "Per player-minute": step 2 ("The emptied energy feeds P") is deleted, and step 4 becomes "F is read from the satiety mass".

**§ 5a.** Replace the "Time to returning hunger" bullet with:
> - **Time to returning hunger** after a mixed meal is 247–321 min (Callahan 2004) and 320–425 min time-blinded (Cummings 2004). The 4–5 h anchor holds.
>   - **Ruling 11c-27: the structure is chosen by fit.** P is fed at the eat with the eaten vector's weighted kcal. Emptying drives absorption. Fullness reads the food in the stomach plus a fifth of drunk liquid.
>   - The early-satiation evidence is spike 1's, all direction only: S1279 (ghrelin at its trough within 1 h), S1262, S1227, S1263, S1266 and S1274.
>   - **Fitted game choices (S1270 open):**
>     - HALF_LIFE_H 0.7 h, P_REQ 6 weighted kcal and STEEP 0.08 are fitted jointly against six readings: Callahan's three preloads from the request and fasted (S1247), the 650 kcal anchor, a fasted 400 kcal breakfast that holds below the request for 3 h, and Rolls's soup at its measured size.
>     - FULL_WEIGHT 0.6 and LIQUID_WEIGHT 0.2 are fitted to Rolls's three arms (S1231) and checked against S1233.
>     - W_PROTEIN stays 2.5 (S1268 open; no replay bounds it).
>   - **The Rolls replay.** Intake at a meal = 650 kcal × displayed hunger / 0.25, a labelled inference: the spec's typical meal eaten at the request level. The model gives 1182 / 1637 / 1732 kJ against 1209 / 1657 / 1639 kJ.
>   - **Energy density** satiates more per kcal through fullness. Eating to the same hunger takes 31 % fewer kcal at 1.05 than at 1.6 kcal/g (S1229: −16 % of daily intake with half the energy manipulated; S1230). The time to the request is unchanged.
>   - **Named non-reproductions:**
>     - Marmonier 2000's absolute snack delays (S1224, 60/34/25 min; the model reads 200/165/173). The bound of spike 1 holds: no additive pool meets both S1224 and S1247.
>     - Melanson's fasted 1 MJ drinks (S1228, 65/126 min; the model reads 236).
>     - Viscous fibre's own effect: fibre counts only through mass (ruling 11c-6).
>     - Displayed hunger never reaches 0 after a meal: 0.12 after 650 kcal, 0.07 after 1,500 kcal.

**§ 6.**
- The oracle feeds P at the eat and replays Callahan (both starts), the 650 kcal meal, the fasted breakfast and Rolls's three arms under the stated mapping.
- Its tolerance is 1.1x on those replays. S1233 is a check at 1.15x.
- The anchor reads 240–300 min with Cummings' 425 as the outer bound.

## Task 3 kernel functions it changes (NR_Kernel_Satiety.lua, plus one in NR_Kernel_Stomach.lua)
- **`K.satiety.post`:** the exponent form above, which replaces the hyperbola. It needs one `math.exp(STEEP × math.log(P / P_REQ))` and keeps the P ≤ 0 → 0 branch.
- **`K.satiety.seedP`:** the inverse of the new read. `PN_MAX` is replaced by `P_SEED_MAX`, a game choice of about 1,300 weighted kcal (a 1,000 kcal meal).
- **`K.satiety.feed`:** the code is unchanged. The comment becomes "the vector eaten", and the call moves to the intake.
- **`K.satiety.fill`:** the code is unchanged. The writer passes `K.stomach.satietyMass(st)` in place of `K.stomach.mass(st)`.
- **New `K.stomach.satietyMass(stomach)`:** `massOf(buffer) + LIQUID_WEIGHT × (stomach.liquid or 0)`. It is appended, so no line moves. `LIQUID_WEIGHT` lives in K.satiety or K.stomach.
- **Constants:**
  - HALF_LIFE_H 2.0 → 0.7.
  - P50 150 → retired for P_REQ 6 and STEEP 0.08.
  - FULL_WEIGHT 0.5 → 0.6.
  - LIQUID_WEIGHT 0.2 and P_SEED_MAX are new.
  - W_PROTEIN 2.5 is kept and relabelled.
- **The header comment:** "fed by the energy leaving the stomach" becomes "fed at the eat".
- **Unchanged:** `weigh`, `decay`, `sated`, `discomfort`, `circadian`, `K.hybrid.hungerTarget`, and both stomach lanes and `drain`.

### 5c. Physical activity (ruling 11c-29, rows S1297–S1336)

- **Acute suppression.** Vigorous work (the swing state and the metabolism model's heavy-work band; the run flag never reaches the server, x141a) suppresses hunger, decaying within 30–60 min (S1305, S1304). Its size is a labelled game choice anchored to ES 0.60–1.47 at 0.5–1.5 h (S1303, S1306; S1334 open). Resistance-type swinging is weighted smaller (S1301); walking adds nothing (S1302).
- **No same-day compensation.** The exercise share of the deficit (`exKcalDay`) enters the energy state through a lag: about zero the same day (S1312), fitted to Whybrow's ~30 % mean over days 3–16 (S1318). A food-restriction deficit keeps its same-day effect (S1312). The split into an exercise share and a food share is a game choice no row defines.
- **While exercising**, hunger takes the non-exercising branch's rate or lower. Vanilla breaks the post-meal freeze only in the fed branch (#0471), against S1299, S1300, S1303 and S1304.
- **Inactivity** never lowers hunger (S1330–S1332).
- **Heavy labour** (Karl 2021, S1325: hunger −55 % over 72 h in an 18 % surplus; +26 % in a deficit) is a replay the model may fail. If it fails, a total-deficit threshold (≥ 25 %) that bypasses the lag becomes a ruling.
- **Cold** gets no same-day term now (S1315 and S1316 are named).

## 6. Validation (the oracle)

- `testing/tests/kernel/test_satiety_meal_studies.py` replays at least three published protocols through the kernels, in game hours:
  1. A protein preload against an isoenergetic carbohydrate preload: the later hunger ordering and its size.
  2. Soup against the same casserole with water alongside: the fullness difference.
  3. A mixed meal of about 650 kcal: the time until hunger returns to its pre-meal level, 4–5 h.
- Each asserts the model lands inside the study's reported range, and each test cites its science rows.
- The oracle is accepted only after a mutation pass (CLAUDE.md § 6). Its reviewer patches `w_k`, the half-life, P50, `a`, the liquid lane and the deficit floor one at a time, and shows that each change fails a test.
- The golden trace moves. Its stand-ins write records whose stomach changes (mass, the liquid lane, P). The change is named: "satiety from physiology". The commit that re-records it walks the leaves and traces two.

## 7. Performance (Rule 6)

- A handful of arithmetic per player-minute inside the budgeted queue: two exponentials and a few multiplications. Task 15's scalar step measured 0.70 µs per writer step.
- The stomach's second lane doubles one emptying computation, which already runs per player-minute.
- No per-tick work. Each task reports its lupa cost beside Task 15's figure.

## 8. Plan 11c outline

The plan, written next, is ordered as follows:

1. **The harvest.** Science rows for § 5's eight topics (Opus). Its findings may simplify the design: a neutral liquid lane collapses to one buffer, a neutral fibre drops out. The controller rules on each such simplification.
2. **The stomach audit.** S0130 and S0131 settled or kept as game choices; `massOf` and the liquid lane, test-first.
3. **The kernel.** `K.satiety` rewritten (fill, feed, decay, post, sated, seedP) with the oracle and its mutation pass.
4. **Wiring.**
   - The intake routes drinks to the liquid lane.
   - The writer reads F, P and the energy state.
   - The 42.21 read of vanilla's overeating and the soft cap.
   - Migration to v4.
   - The guards and CROSS rows.
   - The golden re-recorded under its named change.
5. **Retiring Task 15's pieces** and the `NR.SatietyBulk` option. The removed option's key in a server's ini is ignored; the plan confirms this on the jar.
6. **Documentation.** The area and platform pages and their register rows; the limitation strings rewritten with the count kept or the golden's self-report line re-recorded.
7. **The close.** A whole-pass review, the fix wave, § 3's gates, and the memory.

Plan 11b's live acceptance and release run after 11c, on this model.
