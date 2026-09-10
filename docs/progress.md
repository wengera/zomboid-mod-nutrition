# Progress board — research slices

Status of every slice in the [research-slices spec](superpowers/specs/2026-09-09-research-slices-design.md).
A session takes the first `ready` slice whose dependencies are `done`; see the
spec's run loop. Statuses: `ready` · `in progress` · `done` · `blocked`.

| # | Slice | Status | Date | Commit | Outcome |
|---|---|---|---|---|---|
| 01 | P1a · Intake pipeline | done | 2026-09-10 | cd0f936..419f16a | `docs/vanilla/eating-pipeline.md` (67 modifiers, 24 measured; server owns Nutrition in MP); tools wiki_mirror/doc_lint, `pzt doctor`, harness experiment commands, 7 mirrors, tracked artifacts; acceptance in the plan file |
| 02 | P1c · Food item model & lifecycle | done | 2026-09-10 | 0c3d6b7..e44610c | `docs/vanilla/food-item-model.md` (114 keys, aging/cooking/evolved models, 36 measured rows); lifecycle harness commands + `s02_lifecycle.py`; artifact `exp02-20260910-030433`; 3 mirrors; ItemStats packet analysis incl. the zero-field leak |
| 03 | P1b · Body side | done | 2026-09-10 | 22ce6c2..5b9b959 (interleaved with slice 04) | `docs/vanilla/body-stats.md` (passive burn, hunger/thirst rates and multipliers, moodle thresholds, weight bands, appetite traits; 57 measured rows, `exp03-20260910-045523`); body-side harness commands (server `stats.get`, `trait.set`, `player.sleep`, ...; client `player.walk`) + `s03_body.py`; 5 mirrors; corrections across nutrition-core/eating-pipeline/patterns (client computes and discards weight; recovery-mod deficit penalties are dead code; FOOD_EATEN timer is game-time; THIRST level-4 health loss at 5x the hunger rate, found through the slice-04 death run) |
| 04 | T2 · Accelerated nutrition scenario | done | 2026-09-10 | 3b1ac80..afac230 (interleaved with slice 03) | harness test layer (`TK.test`, `t:at/every/eventually`, `test.run` on the server bus) + `pzt scenario --side server`; three 3-day runs at 30x (`scenario-20260910-05{2624,4012,5029}`): weight model verified to sub-gram accuracy (+2.526 vs +2.551 kg gain, -1.426 vs -1.412 kg fast); run 1 died of thirst at game-hour 35 (`setCalories` is not food; THIRST level-4 health drain found and confirmed on the jar); `nutrition-core.md` § Verified on server; `pzt doctor` port states; scenario verdicts now fail on server/client errors |
| 05 | P4a · Food scanner + dataset | in progress | 2026-09-10 | (see resume note) | shared script parser being built (Tasks 1+2) |
| 06 | P4b · Recipes & cooking dataset | ready (needs 05; plan `superpowers/plans/06-recipes.md`) | | | |
| 07 | T1 · Profile builder | ready (plan `superpowers/plans/07-profile-builder.md`) | | | |
| 08 | P3a · Nutrition-mod catalog | ready (needs 07; plan in wave 3) | | | |
| 09 | P3b · Teardown 1 | ready (needs 07, 08; plan in wave 3) | | | |
| 10 | P3c · Teardown 2 | ready (needs 07, 08; plan in wave 3) | | | |
| 11 | P3d · Teardown 3 | ready (needs 07, 08; plan in wave 3) | | | |
| 12 | P2a · Platform reference | ready (needs 07; plan in wave 4) | | | |
| 13 | P2b · Moddability wall map | ready (needs 12; plan in wave 4) | | | |
| 14 | P5 · Feasibility notes | ready (needs all; plan in wave 4) | | | |

## Resume notes (in-progress slices)

- **05** (SDD ledger `.superpowers/sdd/05-food-scanner/progress.md`, plan `docs/superpowers/plans/05-food-scanner.md`): running — Tasks 1+2 (`tools/food_scan.py` parser + tests). Next — Task 3 dataset, Task 4 harness `items.count`/`fluid.script`, Task 5 live cross-check (needs the live slot), Task 6 doc.

## Ripples (findings that change a later slice's plan)

- (from 02) Item aging (`age`/`offAge`/`freezingTime`) runs only on the server and never travels in `ItemStatsPacket`; `setRotten(true)` and `setFrozen(true)` write dead/undone fields (use `setAge(offAgeMax+1)` / `freeze()`); slice 05's in-game spot checks must read item state on the server.
- (from 02) `ItemStatsPacket` reuses cached packet objects without reset and writes 20 fields only when non-zero while applying them unconditionally: a zero-valued field arrives carrying the previous packet's value. Any slice (or the mod) reading `cookingTime`, `hungChange`, calories/macros etc. client-side on freshly synced items must treat zeros with suspicion; slice 13 (wall map) records it as a platform hazard.
- (from 02) Cooking skill scales extracted macros by (1 + lvl/15) and shrinks hunger by (1 − 0.03·lvl) in evolved recipes — Cooking 10 creates ~17 % of calories; relevant to slice 06's recipe dataset and the item pass.
- (from 02) Measured-artifact skew rule: when a fix round follows the last live run, `testing/artifacts/README.md` discloses the script/artifact delta (applied for exp01 and exp02).

- (from 01) The **server** owns `Nutrition` in MP (client-side `setCalories` is overwritten within ~1 s by the 1 Hz `PlayerStatsPacket`; the eat action completes server-side). Slice 04's scenario must set/feed calories on the server bus (`nutrition.set <user> …`) and read server values; slice 03's decay measurements likewise read the server. `docs/testing/spikes.md` S6, `pipeline-design.md` and `docs/modding/patterns.md` stated the reverse and were corrected in slice 01 (Task 7).
- (from 01) Kahlua `pcall` does not catch "tried to call nil" — harness code must nil-check Java members before calling (`TK.call`); every later slice's Lua follows this.
- (from 01) B42 hunger/thirst are read with `Stats:get(CharacterStat.HUNGER/THIRST)` — the route every live snapshot answered with (M). `Stats` carries no `getHunger`/`getThirst` in its 34-method list (C, `./pz.sh methods zombie/characters/Stats`); the harness's `getHunger()`/`.hunger` fallbacks short-circuit and were never exercised, so "gone" rests on the method list, not on the run (slice 03).
- (from 01) Script-level Calories/Carbs/Lipids/Proteins have no Lua getter — slice 05's in-game cross-check must use item instances (`eat`'s `itemBefore`) or count-only checks.

- (from 03) **THIRST level 4 drains health at five times the hunger rate** (`BodyDamage.Update` `/10` vs `/50`, per multiplier unit; 17.82 health/game-hour on the 90-minute fixture, 11.88 on a 60-minute day — day-length dependent). Any scenario or teardown session that runs longer than ~29 game-hours must manage thirst, or the subject dies (slice 04 lost its first run to it). P5 can treat "dying of thirst" as a live vanilla mechanic.
- (from 03) The `FOOD_EATEN` timer is a game-time quantity (`minutesPerDay/30` units per game-second; 11 000 cap ≈ 1.02 game-hours). Scenario authors who rely on the eat gate reason in game time, not real seconds or frames.
- (from 03) Weight-band traits are applied on the server (`applyTraitFromWeight`) and `getKnownTraits()` returns lowercased names; whether they reach the client at all is open (body-stats.md open question 10). Teardowns that probe traits read the server and match case-insensitively.
- (from 03) `StatsDecrease` never touches calories; the only nutrition-side sandbox lever is `Nutrition` on/off (slice 01) — the profile builder (07) needs no calorie multiplier key.
- (from 04) The harness test layer (`TK.test`, `t:at/every/eventually`, `test.run` on the server bus) and `pzt scenario --side server` are the L2/L3 base for every later live slice; scenarios live under `server/scenarios/` and run server-side.
- (from 04) `setCalories` is not food: a scenario that feeds the calorie store must pin hunger and thirst each sample, and `Nutrition.update` stops on a corpse (weight freezes at the death value). The next `nutrition_3day_*` run is the first to exercise the `thirst` sample column and the dead-subject verdict — nothing has yet.
- (from 04) The decoded weight model is verified on the live server to sub-gram accuracy over three game-days (residuals are hourly-sampling bias); P5 and the item pass can rely on it. Under the 3 700 clamp, two +2 000 doses a day lose 4 790 of 12 000 kcal — intake pacing is a balance lever slices 12–14 must account for.
