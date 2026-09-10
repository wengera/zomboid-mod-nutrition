# Progress board — research slices

Status of every slice in the [research-slices spec](superpowers/specs/2026-09-09-research-slices-design.md).
A session takes the first `ready` slice whose dependencies are `done`; see the
spec's run loop. Statuses: `ready` · `in progress` · `done` · `blocked`.

| # | Slice | Status | Date | Commit | Outcome |
|---|---|---|---|---|---|
| 01 | P1a · Intake pipeline | ready | | | |
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

_None yet._
