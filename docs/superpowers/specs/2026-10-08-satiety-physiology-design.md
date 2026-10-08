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
