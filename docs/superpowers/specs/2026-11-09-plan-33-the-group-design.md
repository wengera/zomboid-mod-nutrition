# Plan 33 — the group (design)

Date: 2026-11-09. Owner: Angus; written by the controller under the standing direction (memories `drive-toward-full-survival`, `explore-prove-then-harden`, `combat-approach-not-flee`, `kills-metric`, `hits-per-kill-metric`) and ruling P32-R (the exploratory lane with no reviews, the evidence lane with one).

## 1. The problem

Plan 32 settled the facing: the body snaps onto the target at every press and through the stance (F18's presses median 0.0 degrees, #4703-#4712; ten trials with 7 to 11 kills and 0 to 1 hits). F18 then died in four minutes on the `agent` fixture under a group of four with a crawler underfoot. Its write-up and visual pass (`.superpowers/sdd/2026-11-08-plan-32-the-facing/task-7-f18-writeup-report.md`, `visual-review-f18.md`) read the chain:

- **The finish stalled.** The finish `a71` stomped its fallen target once (seq 3010, hp 2.85 to 2.48, a knock) and then held its `head` step from seq 3020 to 3175, fifteen act lines and 14.553 s, with no press: the character stood on the fallen zombie (`d` 0.0053 tiles) and the look gate `lookOn(st, off)` (`PZAgent_StanceMelee.lua` line 592) never passed, since the bearing to a target under the character's feet is numerically unstable; meanwhile three zombies (13648, 13651, 13653) walked in from 11.6 to 12.0 tiles. The handback at a standing zombie within `handbackR` could not fire until they arrived.
- **The crawler was never targeted.** The crawler 13649 lay within 0.4 tiles from game minute 608 and was the target on no line after 356; the fight's target choice takes the nearest standing zombie (`fight.py` line 914) and the finish only a fallen one it is pinned to.
- **The drag-down guard fled a character that could not move.** From the guard's first line (402) to the death (415), fourteen `flee:many` lines sent five `steer` runs while no frame read the character moving for 116 frames (seq 3512 to 3655), all of them under hit reactions; the run steers' headings pointed into a zombie at the side (the visual pass, shots 37 to 41).
- **The trials did not cover the fixture.** Seven trials on `street-1` and the arena proved the composition; none ran on the `agent` fixture with the model, where the group formed.

## 2. Goal and success criteria

The character leaves a forming group before it closes, finishes a fallen zombie without standing on it, stomps a crawler within reach before it bites, and never runs into a zombie at its side; read in trials on the `agent` fixture with the model, `street-1` and the arena pair, then in one evidence session. Success: (1) no `head` step longer than `HEAD_MAX_TICKS` in any trial (the finish presses or hands back); (2) a crawler within `CRAWLER_R` with a standing zombie within `DANGER_R` is the target of a stomp within two decision lines of its first listing in reach; (3) a trial's standing count within `GROUP_NEAR_R` reaches three in open ground on no more than one line per trial before a `leave` leg is sent; (4) no `steer` run whose heading passes within `SIDE_R` of a standing zombie; (5) the two metrics no worse than Plan 32's trials on street-1 and the arena (7 to 11 kills, 0 to 1 hits) and, on the `agent` fixture with the model, alive at the cap in two of three trials with the hits per kill under 1.0; (6) the evidence session F19 alive at its cap or dead by a cause the write-up traces to a rule the trials never reached.

## 3. Design

### 3.1 The finish (the reflex, `PZAgent_StanceMelee.lua`)

In `finish`: when `dh` is under `K.HEAD_LOOK_FLOOR` (0.15 tiles: the target under the character), the look gate is skipped and the stomp pressed at once (the earlier stomp at 0.27 landed); a `head` step that has run `K.HEAD_MAX_TICKS` (20 ticks, one second) without a press ends the melee `done handback` with `why head_stall` and the standing count, so the planner decides; `standingNear` reads every tick of the finish as it does. The leaf gains `head_ticks`. Tests on the lupa host: the stall reproduced with a fake whose look never settles (the old code holds `head` forever, the new presses at the floor and hands back at the cap); mutants per rule.

### 3.2 The crawler (the planner, `fight.py`, `threat.py`)

`CRAWLER_FIRST`: a zombie reading `crawler` or `onFloor` within `CRAWLER_R` (1.0 tile) while a standing zombie stands within `DANGER_R` becomes the target of a `finish` (the stomp) before the standing one is met, unless the standing one is within `STAND_MIN_R`; the pin returns to the standing zombie when the crawler reads dead or beyond `CRAWLER_R`. F18's line 356 onward replays with the crawler targeted.

### 3.3 The group's entry (the planner, `threat.py`)

`GROUP_LEAVE`: with two standing zombies within `GROUP_NEAR_R` closing (their distance falling over two lines) and no wall or doorway within `WALL_R` (1.5 tiles) at the character's back, the planner sends a `leave` leg toward the nearest building door or doorway the world knows within `LEAVE_R` (20 tiles), the stance resumed at the doorway (the doorway stand of P24-AO); with none known, a `steer` away from the group's centroid at a run for `LEAVE_S` (4 s), re-read each line; the third arrival never finds the character in open ground. `DRAG_GUARD_FIGHT`: the drag-down guard's flee, when the frame reads the character under a hit reaction or not moving for `STUCK_FRAMES` (10 frames), shoves the standing zombie in front instead of sending another run (the shove is the one press the engine allows under the reaction's end, #4372), and never sends a `steer` whose heading passes within `SIDE_R` (1.0 tile) of a standing zombie (`SIDE_CLEAR`: the heading rotated to the nearest clear bearing, else the shove). Replay tests on F18's lines 380 to 415.

### 3.4 The body between presses (the reflex and the stance)

`IDLE_SNAP`: while no melee runs and a standing zombie stands within `KEEP_R`, the Motor's per-frame hold snaps the body onto the nearest standing zombie (`FACING.hold` with the aim posture as the stance does), so the body never wanders between presses (the visual pass's shots 31, 33, 35, 36). Off while a `steer` or `walkTo` runs (the walk owns the facing).

### 3.5 The jar read

The crawler's bite: `IsoZombie`'s crawler attack range and the `CrawlerBite` reaction's trigger (`ZombieAttack`/`AttackState` for a crawler, the player's reach test), and whether a crawler within `STAND_MIN_R` can be stomped while a standing zombie attacks (the stomp's target square against `isOnFloor`). Rows minted with the evidence session's write-up.

### 3.6 The trials and the proof

The composition (3.1 to 3.4 behind switches on by default) against Plan 32's head `d31ca7d0` on three fixtures: the `agent` fixture with the model (`x_trial.py --variant ladder --fixture agent --waves none` with the model: the evidence driver's own goal source; a `--waves none` plan added to the trial loop if absent), `street-1` with the model and the arena pair; two rounds; the rows in `testing/trials/trials.md` with the facing columns and a new `head_ticks` max column. The proof: the metrics repeat across the rounds and the `agent` fixture's trials end alive at the cap in two of three.

### 3.7 Harden

One evidence session F19 (`f_goals_19.py` from `f_goals_18.py`, `grade_x3` adding the finish's `head_ticks`, the crawler targeting, the group-leave legs and the idle snap to `grade_x2`'s readings) under the full CLAUDE.md § 5, the write-up with its rows and the jar rows under one review, the close.

## 4. Out of scope

The LLM goal source's choices (where the model sends the character), the Dress's internals, the HEAD_AIM calibration, any change to the window glass gate, the deciders behind the fork.

## 5. Risks

`GROUP_LEAVE` may flee what Angus wants fought (two zombies): it fires only on two closing in open ground with no wall at the back, and the trials' flee minutes and kills decide; the idle snap costs Java calls per frame while idle near a zombie (a bench before and after); the head-step floor may press a stomp at a target the engine reads elsewhere (the leaf's `hp1` shows a miss, and the cap hands back).
