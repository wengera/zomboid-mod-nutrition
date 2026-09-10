# Progress board — research slices

Status of every slice in the [research-slices spec](superpowers/specs/2026-09-09-research-slices-design.md).
A session takes the first `ready` slice whose dependencies are `done`; see the
spec's run loop. Statuses: `ready` · `in progress` · `done` · `blocked`.

| # | Slice | Status | Date | Commit | Outcome |
|---|---|---|---|---|---|
| 01 | P1a · Intake pipeline | in progress | 2026-09-10 | (see resume note) | tools, doctor, harness commands, code map, mirrors done; matrix running; doc pending |
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

- **01** (SDD ledger: `.superpowers/sdd/01-intake-pipeline/progress.md`, plan `docs/superpowers/plans/01-intake-pipeline.md`): done — T1 tools (`755d420`, `eee86bc`), T2 doctor (`82f9806`), T3 harness commands + smoke (`21af6d1`, `eb123fd`), T4 code map (`docs/superpowers/plans/01-notes.md`, `a24010c`), T6 mirrors (`f076920`, `ab501ba`). Running — T5 experiment matrix (`testing/experiments/s01_eat_matrix.py`, results → `testing/artifacts/exp01-20260910-003929/eat-matrix.json`). Next — review T5, then T7 writes `docs/vanilla/eating-pipeline.md` and applies the S6-direction corrections listed in `.superpowers/sdd/01-intake-pipeline/task-7-brief.md`; then acceptance checks, ledgers, push.

## Ripples (findings that change a later slice's plan)

- (from 01) The **server** owns `Nutrition` in MP (client-side `setCalories` is overwritten within ~1 s by the 1 Hz `PlayerStatsPacket`; the eat action completes server-side). Slice 04's scenario must set/feed calories on the server bus (`nutrition.set <user> …`) and read server values; slice 03's decay measurements likewise read the server. `docs/testing/spikes.md` S6, `pipeline-design.md` and `docs/modding/patterns.md` state the reverse and are corrected in slice 01's Task 7.
- (from 01) Kahlua `pcall` does not catch "tried to call nil" — harness code must nil-check Java members before calling (`TK.call`); every later slice's Lua follows this.
- (from 01) B42 hunger/thirst are read with `Stats:get(CharacterStat.HUNGER/THIRST)`; `getHunger()`/`.hunger` are gone (slice 03).
- (from 01) Script-level Calories/Carbs/Lipids/Proteins have no Lua getter — slice 05's in-game cross-check must use item instances (`eat`'s `itemBefore`) or count-only checks.
