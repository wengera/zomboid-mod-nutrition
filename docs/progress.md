# Progress board — research slices

Status of every slice in the [research-slices spec](superpowers/specs/2026-09-09-research-slices-design.md).
A session takes the first `ready` slice whose dependencies are `done`; see the
spec's run loop. Statuses: `ready` · `in progress` · `done` · `blocked`.

| # | Slice | Status | Date | Commit | Outcome |
|---|---|---|---|---|---|
| 01 | P1a · Intake pipeline | done | 2026-09-10 | cd0f936..419f16a | `docs/vanilla/eating-pipeline.md` (67 modifiers, 24 measured; server owns Nutrition in MP); tools wiki_mirror/doc_lint, `pzt doctor`, harness experiment commands, 7 mirrors, tracked artifacts; acceptance in the plan file |
| 02 | P1c · Food item model & lifecycle | ready (needs 01) | | | |
| 03 | P1b · Body side | ready (needs 01) | | | |
| 04 | T2 · Accelerated nutrition scenario | ready (needs 01, 02) | | | |
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

_None._

## Ripples (findings that change a later slice's plan)

- (from 01) The **server** owns `Nutrition` in MP (client-side `setCalories` is overwritten within ~1 s by the 1 Hz `PlayerStatsPacket`; the eat action completes server-side). Slice 04's scenario must set/feed calories on the server bus (`nutrition.set <user> …`) and read server values; slice 03's decay measurements likewise read the server. `docs/testing/spikes.md` S6, `pipeline-design.md` and `docs/modding/patterns.md` stated the reverse and were corrected in slice 01 (Task 7).
- (from 01) Kahlua `pcall` does not catch "tried to call nil" — harness code must nil-check Java members before calling (`TK.call`); every later slice's Lua follows this.
- (from 01) B42 hunger/thirst are read with `Stats:get(CharacterStat.HUNGER/THIRST)` — the route every live snapshot answered with (M). `Stats` carries no `getHunger`/`getThirst` in its 34-method list (C, `./pz.sh methods zombie/characters/Stats`); the harness's `getHunger()`/`.hunger` fallbacks short-circuit and were never exercised, so "gone" rests on the method list, not on the run (slice 03).
- (from 01) Script-level Calories/Carbs/Lipids/Proteins have no Lua getter — slice 05's in-game cross-check must use item instances (`eat`'s `itemBefore`) or count-only checks.
