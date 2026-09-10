# Slice 03 — P1b Body side — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document how the body consumes what eating provides: passive calorie burn (`Nutrition.updateCalories`), hunger and thirst decay and their sandbox multipliers, the weight bands and their effects (fitness/strength XP gates, speed), the nutrition-driven moodles and their thresholds, and the appetite traits — each threshold cited and the main rates measured at accelerated time.

**Architecture:** Read `Nutrition.updateCalories`, the hunger/thirst update in `IsoGameCharacter`/`BodyDamage`/`Stats`, `SandboxOptions`, the moodle definitions (B42 moodles are script-registered `MoodleType`s), then measure decay rates at `settimespeed 30` with hourly samples through a small harness sampler; write `docs/vanilla/body-stats.md`.

**Tech Stack:** `pzdis`, harness Lua, `pzt`, Python.

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md`

## Global Constraints

- Build **42.20.4 (`b0bbce05d5`)**; evidence grades C/M/W; brief commits without attribution; one live session at a time; game install read-only; defaults + `docs/decisions.md`; house skeleton.

---

## Header

- Slice: **03** · Phase P1b · Depends on: 01 · Estimate: 2 h.

## Cold-start context

- Repo `C:\Users\Angus\repos\project_zomboid`; charter `STRATEGY.md`; board `docs/progress.md`; ledger `docs/decisions.md`.
- Jar: `cd C:\Users\Angus\pz-b42 && ./pz.sh …`; game Lua/scripts under `D:\SteamLibrary\steamapps\common\ProjectZomboid\media`.
- Known: `Nutrition.updateCalories` reads the player's action stack, `SwipeStatePlayer` / `ClimbOverFenceState` / `ClimbThroughWindowState`, `BodyDamage.getThermoregulator().getEnergyMultiplier()`, `getWeight`, `IsRunning`, `isPlayerMoving`, `getCalories` (from `./pz.sh dump zombie/characters/BodyDamage/Nutrition updateCalories`). The weight model is in `docs/vanilla/nutrition-core.md` (gain/loss thresholds and rates; bands Emaciated <50 … Obese >100; `canAddFitnessXp`).
- Hunger/thirst: `IsoGameCharacter.getStats()` → `zombie/characters/Stats`; `./pz.sh grep "getHunger"` hits `IsoGameCharacter`, `IsoPlayer`, `BodyDamage`, `NetworkPlayerAI` — the decay lives in one of those `update` methods.
- Moodles: `zombie/scripting/objects/MoodleType` has `register(...)` — find the script files with `find media/scripts -iname "*moodle*"` and the Lua that reads levels (`getMoodles():getMoodleLevel(MoodleType.X)`).
- Live server: `python testing/pzt run`; harness `nutrition.get` (calories/carbs/lipids/proteins/weight/hunger/thirst) and `nutrition.set` from slice 01; `settimespeed` via `server.rcon(...)`; experiments as `testing/experiments/s03_*.py`.

## Questions

1. `updateCalories`: the full passive-burn formula — base rate per game-second, the action/state multipliers (attacking, climbing), running/moving, the thermoregulator energy multiplier, the weight term; the resulting kcal/game-day at rest and while running.
2. Hunger and thirst: where and how fast they rise (per game-second constants), the sandbox multipliers (`SandboxOptions` — find the option names: hunger/thirst/"StatsDecrease"?), the trait modifiers (Hearty Appetite, Light Eater, Thirsty?), sleeping/resting effects.
3. What "hunger" is relative to calories: two independent stats (hunger a 0–1 need, calories a store) — what couples them, if anything (`Eat` reduces both; does hunger affect calorie burn?).
4. Weight bands → effects: the exact bands (`applyTraitFromWeight`), the traits set, and every effect of those traits: `canAddFitnessXp` gates, movement speed, endurance, combat (grep the trait names `Obese`, `Overweight`, `Underweight`, `VeryUnderweight`, `Emaciated` across the jar).
5. Moodles driven by nutrition: Hungry, Thirsty, `FoodEaten`, Overweight/Underweight (if moodles) — thresholds per level and what each level does (speed/damage/XP), from the moodle scripts and `zombie/characters/Moodles/Moodles.update`.
6. Traits: Hearty Appetite / Light Eater (hunger rate), Nutritionist (display only?), Weight Gain/Loss (thresholds from nutrition-core.md) — cite each.
7. **MP**: does the server run `updateCalories`/hunger for connected players, or only the client (S6 says nutrition is client-computed) — confirm from the guards in `Nutrition.update` and `IsoPlayer.update` (`isLocal`, `GameClient.bClient`) and measure: server mirror vs client after an accelerated hour.

## Method

### Task 1: Passive burn and hunger decay (C)

- [ ] **Step 1:** `./pz.sh dump zombie/characters/BodyDamage/Nutrition updateCalories` in full (all offsets) and `update`; transcribe the formula with the resolved constants.
- [ ] **Step 2:** `./pz.sh grep "getHunger" --max 20`; for `IsoGameCharacter`, `IsoPlayer`, `BodyDamage`: `./pz.sh methods <class> | grep -iE "hunger|thirst|updateStats|update\b"`; dump the update method(s) that write hunger/thirst; record constants and sandbox reads (`SandboxOptions` getters — `./pz.sh methods zombie/SandboxOptions | grep -iE "hunger|thirst|stat|nutrition"`).
- [ ] **Step 3:** traits: `./pz.sh grep "HeartyAppetite" --max 10`, `"LightEater"`, `"Thirsty"` → dump the readers.

### Task 2: Weight bands, traits, moodles (C)

- [ ] **Step 1:** dump `Nutrition.applyTraitFromWeight`, `applyWeightFromTraits`, `characterHaveWeightTrouble`, `canAddFitnessXp` (cross-check nutrition-core.md; extend, don't duplicate).
- [ ] **Step 2:** `./pz.sh grep "Obese" --max 20` (and `Overweight`, `Underweight`, `Emaciated`, `VeryUnderweight`): dump each reader outside `Nutrition` (movement speed in `IsoPlayer`/`IsoGameCharacter`, combat, endurance) and record the numbers.
- [ ] **Step 3:** moodles: `find media/scripts -iname "*moodle*"`, read the definitions; `./pz.sh methods zombie/characters/Moodles/Moodles`; dump `Moodles.update` sections for Hungry/Thirsty/FoodEaten/Heavy? — thresholds per level; then grep Lua `media/lua/**/*.lua` for `MoodleType.HUNGRY`/`THIRST` effects (speed etc. may be Java: `./pz.sh grep "HUNGRY"`).

### Task 3: Measured rates (M)

- [ ] **Step 1:** add a client command `stats.sample` → `{worldAge, calories, hunger, thirst, weight, endurance, fatigue}` (endurance/fatigue from `getStats()`), and `stats.sampler <minutesGame> <count>` that schedules samples on `EveryOneMinute` and writes `TK.result("stats_samples", {samples=[...]})` when done (reuse slice 04's scheduler if it already exists; otherwise a minimal `EveryOneMinute` counter here — slice 04 will generalize it).
- [ ] **Step 2:** experiment `testing/experiments/s03_decay.py`: `nutrition.set calories 0`, `settimespeed 30`, sample every 60 game-minutes for 24 game-hours (≈ 3.2 min wall) with the player idle; then a second run of 6 game-hours with the player running in circles (add `player.run <seconds>` command using `getPlayer():setRunning(true)` + a move target via `player:setX/Y`? simpler: `player:getPathFindBehavior2():pathToLocationF(x+10,y,z)` in a loop; if movement automation is fragile, measure resting only and mark running as an open question). Restore `settimespeed 1`.
- [ ] **Step 3:** compute kcal/game-day at rest, hunger and thirst per game-hour; compare with Task 1 constants; record run ids.
- [ ] **Step 4 (MP):** after the idle run, `witness.nutrition` — server vs client calories (S6 mechanism); grep the server log for any nutrition packet names found in Task 1 (Q7).

### Task 4: Mirrors and doc

- [ ] **Step 1:** `python tools/wiki_mirror.py Hunger Thirst Moodles Weight Traits` (skip absent pages), digests.
- [ ] **Step 2:** write `docs/vanilla/body-stats.md` (skeleton; tables with `Ev`), update `docs/vanilla/README.md` (`stats-moodles.md` row → body-stats.md done) and close the `updateCalories`/sandbox open questions in `nutrition-core.md` (cite this doc).
- [ ] **Step 3:** lint → 0; commit `Slice 03: body stats and moodles`.

## Deliverables

- `docs/vanilla/body-stats.md`; README/nutrition-core updates; mirrors
- harness `stats.sample`, `stats.sampler` (+ `player.run` if achieved); `testing/experiments/s03_decay.py`

## Acceptance checks

1. lint 0 findings; 2. Q1–Q7 answered with citations; 3. ≥ 3 M rows (rest burn, hunger rate, thirst rate) with run ids; 4. `pzt run --hold 5` passes.

## Expected decision points (defaults)

- Movement automation unreliable → measure at rest only; running burn stays C with an open-question note.
- Moodle effects split between Java and Lua → document the Java thresholds (C) and list the Lua readers; do not chase UI-only effects.

## Done protocol

- `docs/progress.md` 03 → done + ripples (burn rate constant → slice 04 prediction inputs); `docs/decisions.md`; push.
