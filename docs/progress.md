# Progress board — research slices

Status of every slice in the [research-slices spec](superpowers/specs/2026-09-09-research-slices-design.md).
A session takes the first `ready` slice whose dependencies are `done`; see the
spec's run loop. Statuses: `ready` · `in progress` · `done` · `blocked`.

| # | Slice | Status | Date | Commit | Outcome |
|---|---|---|---|---|---|
| 01 | P1a · Intake pipeline | done | 2026-09-10 | cd0f936..419f16a | `docs/vanilla/eating-pipeline.md` (67 modifiers, 24 measured; server owns Nutrition in MP); tools wiki_mirror/doc_lint, `pzt doctor`, harness experiment commands, 7 mirrors, tracked artifacts; acceptance in the plan file |
| 02 | P1c · Food item model & lifecycle | done | 2026-09-10 | 0c3d6b7..e44610c | `docs/vanilla/food-item-model.md` (114 keys, aging/cooking/evolved models, 36 measured rows); lifecycle harness commands + `s02_lifecycle.py`; artifact `exp02-20260910-030433`; 3 mirrors; ItemStats packet analysis incl. the zero-field leak |
| 03 | P1b · Body side | in progress | 2026-09-10 | (see resume note) | code map research running |
| 04 | T2 · Accelerated nutrition scenario | in progress | 2026-09-10 | (see resume note) | test layer + scenario runner being built (server-side per the slice-01/03 ripples) |
| 05 | P4a · Food scanner + dataset | ready (needs 02; plan in wave 2) | | | |
| 06 | P4b · Recipes & cooking dataset | ready (needs 05; plan in wave 2) | | | |
| 07 | T1 · Profile builder | ready (plan in wave 2) | | | |
| 08 | P3a · Nutrition-mod catalog | ready (needs 07; plan in wave 3) | | | |
| 09 | P3b · Teardown 1 | ready (needs 07, 08; plan in wave 3) | | | |
| 10 | P3c · Teardown 2 | ready (needs 07, 08; plan in wave 3) | | | |
| 11 | P3d · Teardown 3 | ready (needs 07, 08; plan in wave 3) | | | |
| 12 | P2a · Platform reference | ready (needs 07; plan in wave 4) | | | |
| 13 | P2b · Moddability wall map | ready (needs 12; plan in wave 4) | | | |
| 14 | P5 · Feasibility notes | ready (needs all; plan in wave 4) | | | |

## Resume notes (in-progress slices)

- **03** (SDD ledger `.superpowers/sdd/03-body-side/progress.md`, plan `docs/superpowers/plans/03-body-side.md`): running — Tasks 1+2 code map → `docs/superpowers/plans/03-notes.md`. Next — Task 3 live sampling on the server (one session), Task 4 doc.

- **04** (SDD ledger `.superpowers/sdd/04-nutrition-scenario/progress.md`, plan `docs/superpowers/plans/04-nutrition-scenario.md`): running — Tasks 1+2 (`shared/PZTestKit_Test.lua`, server-side scenarios, `pzt scenario --side`); the plan's client-side scenario design is superseded by the ledger's rulings (server owns Nutrition; feed +2000 twice per game-day under the 3700 clamp). Next — Task 3 scenarios + evaluator, Task 4 doc.

## Ripples (findings that change a later slice's plan)

- (from 02) Item aging (`age`/`offAge`/`freezingTime`) runs only on the server and never travels in `ItemStatsPacket`; `setRotten(true)` and `setFrozen(true)` write dead/undone fields (use `setAge(offAgeMax+1)` / `freeze()`); slice 05's in-game spot checks must read item state on the server.
- (from 02) `ItemStatsPacket` reuses cached packet objects without reset and writes 20 fields only when non-zero while applying them unconditionally: a zero-valued field arrives carrying the previous packet's value. Any slice (or the mod) reading `cookingTime`, `hungChange`, calories/macros etc. client-side on freshly synced items must treat zeros with suspicion; slice 13 (wall map) records it as a platform hazard.
- (from 02) Cooking skill scales extracted macros by (1 + lvl/15) and shrinks hunger by (1 − 0.03·lvl) in evolved recipes — Cooking 10 creates ~17 % of calories; relevant to slice 06's recipe dataset and the item pass.
- (from 02) Measured-artifact skew rule: when a fix round follows the last live run, `testing/artifacts/README.md` discloses the script/artifact delta (applied for exp01 and exp02).

- (from 01) The **server** owns `Nutrition` in MP (client-side `setCalories` is overwritten within ~1 s by the 1 Hz `PlayerStatsPacket`; the eat action completes server-side). Slice 04's scenario must set/feed calories on the server bus (`nutrition.set <user> …`) and read server values; slice 03's decay measurements likewise read the server. `docs/testing/spikes.md` S6, `pipeline-design.md` and `docs/modding/patterns.md` stated the reverse and were corrected in slice 01 (Task 7).
- (from 01) Kahlua `pcall` does not catch "tried to call nil" — harness code must nil-check Java members before calling (`TK.call`); every later slice's Lua follows this.
- (from 01) B42 hunger/thirst are read with `Stats:get(CharacterStat.HUNGER/THIRST)` — the route every live snapshot answered with (M). `Stats` carries no `getHunger`/`getThirst` in its 34-method list (C, `./pz.sh methods zombie/characters/Stats`); the harness's `getHunger()`/`.hunger` fallbacks short-circuit and were never exercised, so "gone" rests on the method list, not on the run (slice 03).
- (from 01) Script-level Calories/Carbs/Lipids/Proteins have no Lua getter — slice 05's in-game cross-check must use item instances (`eat`'s `itemBefore`) or count-only checks.
