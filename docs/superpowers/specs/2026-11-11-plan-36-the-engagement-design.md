# Plan 36 — the engagement: design

Date 2026-11-11. Owner Angus; controller Fable. Opens on Plan 35's close (`2026-11-10-plan-35-the-footwork-report.md` § 6) and Angus's directions of 2026-11-11 (memories `proof-on-rounds-less-ceremony`, `swing-while-backpedalling`, with `fighting-retreat`, `combat-approach-not-flee`, `finish-actions-gain-distance`, `always-an-objective`).

## 1. Why

One-on-one and one-on-two fights are solved: zero hits across every arena trial of Plan 35, 0.1 hits a kill on the street, contact 2.2 to 2.6 s a trial against the control's 10.8. Every death and nearly every bite of the week had one shape: the character was already busy with one fight when the situation changed under it. F21 (`#4759`–`#4768`): a group arrived while the reflex pressed at point blank; two bites came from 76 to 116 degrees off the body while the engagement's `leave` hold kept the reflex pressing against the planner's leave; the run that followed steered into a mapped fence edge and office walls with a hedge the frames cannot see at the back; seven rips were superseded and three parts bled from 68 to 13 health; the last bite came standing unmoved at a fence edge. The trials' other bites: a door interaction with two zombies thumping at 0.3 tiles, a shelter walk with a zombie pathing in from 1.6, a crawler creeping in under a standing fight.

None of these is a swing-timing fault. They are about where the fight happens and when it starts, decided seconds before contact. Angus's framing (2026-11-11): avoid being ambushed or overwhelmed without being a coward; keep zombies at the edge of melee range; never be touched by a crawler; never let zombies come in from several angles. His rules for the edge: swinging while backpedalling keeps any one zombie from closing, even with three; the backpedal goes only as far as the next swing still lands, and a target that staggers out of reach gets a step in, the hit, then the step back; the shove is rarely needed and is a deliberate knock-down that neutralises one of several, never the fallback for a missed swing.

## 2. Criteria (read on the trial rounds, P31-T; proven when the reading repeats on both fixtures; one evidence session F22 at the end for the record)

1. The arena arms (`lone`, `pair`, the new `trio`, `flank` and `crawler` waves of § 3.6): alive at the cap with 0 hits, as Plan 35's lone and pair were; 0 bites from behind the engagement cone (§ 3.3's reading) on every arm.
2. The `agent` fixture with the model, six trials: deaths no more than Plan 35's final arm (0 in 4, 1 in 6 before it), kills median not below 11, contact seconds median not above 2.6, hits a kill (the union) not above 0.1; `street-1` three trials alive.
3. Swings into the air (a press launched with the target beyond reach at its landing, § 3.2's reading) under 10 % of presses on every arm; presses launched while moving backward the majority of the retreat's presses.
4. No timed action started with the time to contact below its margin (§ 3.4's reading reads 0 on every arm); every rip, bandage, loot and door interaction that starts completes or is cut by the clock, never by a steer.
5. No frame with a crawler inside 1.0 tile while a standing zombie is pressed (§ 3.5's reading).
6. Every wound in F22 traced to its cause in the write-up; the kills and the two hit counts in its table.

## 3. Design

### 3.1 The room instrument (first, before any rule: the Plan 32 lesson)

The frames do not see a hedge, a solid square or a fence edge behind the body; F21's three engagement bites had a solid square 123 to 177 degrees off the body within 2 tiles, and the footwork's heading could not read it. PZA/1.14 adds to the frame's `me` a `room` ring: for eight headings 45 degrees apart from the world's +x, the clear distance along the heading (0.0 to 3.0 tiles in 0.5 steps) by `PZAgent_StanceWork.lua`'s probe read (the square readable, not `isSolid`, not `isSolidTrans`, not `isBlockedTo` from the previous square, no hoppable crossed edge: one shared function the footwork and the ring both call), plus, per heading, whether the stop was a hoppable edge or a door (the footwork and the planner treat a hop or a door as an exit, a wall as none). Read every third frame (the cost measured in the frame's `cost` leaf and bounded before any rule depends on it: a probe trial on the arena reads the ring against the arena's known walls and the map's blocked edges; a street trial reads it against the map). The footwork's own heading turns (`K.WORK_TURNS`) read the ring instead of probing per tick, so the step is never sent into a heading the ring reads closed, and the withdraw vector the planner sends is clamped by the ring on the Lua side.

### 3.2 The contact cadence (the Lua reflex, under `work`)

- The press rides the back step: during the retreat (a withdraw vector, or the band step) the backward movement is held through the press; the reflex never stops to swing. A probe before the rule reads what the engine does to an attack started while walking backward in the aim stance (the frames' `moving`, `pace` and the press leaf's `attackStarted` through one arena trial).
- The step is keyed to the next landing hit, not to a distance band: the back step continues only while the target's predicted position at the swing's landing (the existing `d_collide_pred` and `closingOf` reads) stays within `reachOf`; a target that staggers out of reach (its state `staggerback` or `hitreaction` and its distance beyond reach) gets one step forward, the press, then the step back. A press launched with the target beyond reach at its landing is a swing into the air, counted on the leaf (`air = true`) and in the grade.
- The shove is a choice, not a fallback: with two or more standing zombies inside reach plus `K.WORK_POINT_BLANK_R`, the reflex shoves the nearest (the knock-down), swings the next, and stomps the downed one when nothing standing is within `K.MELEE_CROWD_R`; a missed swing on a lone target is answered by the next swing on the back step. The leaf carries `shove_for = "knockdown"`.
- The nearest attacker's facing: inside point blank the reflex faces the zombie with `attackers` counting it or the nearest standing one, not the pinned target, and re-pins to it (F21's bites 2 and 3 at 76 to 116 degrees).

### 3.3 The engagement picker (the planner: where the fight happens)

- The pull to a line: when two or more standing zombies are closing within `GROUP_ENTRY_R` with a bearing spread above 60 degrees, the planner sends the melee with a withdraw vector along the bisector away from their centroid (the existing `withdraw`), clamped to the ring's open headings, until the spread falls under 45 degrees or the nearest is within reach; then the vector is dropped and the reflex stands. The pull is the fight's setup, not a flee: the melee runs throughout, and the fighting retreat's cadence (§ 3.2) presses whoever enters reach.
- The cone trigger: a standing zombie more than 90 degrees off the engagement cone (the bearing of the pinned target, 60 degrees either side) inside 4 tiles and closing sends the withdraw vector that brings it into the cone, before contact. Logged `engage_pull {why: spread | cone, spread, n}`; counted in the grade with the bites from behind the cone (a reaction run whose attacker's bearing is over 90 degrees off the body at onset: F21's reading, now a scorecard cell).
- The `leave` hold goes: the planner's leave at `GROUP_LEAVE_N` becomes the pull (a withdraw vector to the running melee), never a hold against it; above `RETREAT_MAX_N` the run as today, along the ring's most open heading toward the shelter or the door the map reads, never into a heading the ring reads closed. Fix 1's `_contact_rule` stays.

### 3.4 The action clock (the planner: when a timed action may start)

- Every listed zombie's time to contact: its distance less the reach, over its gait's speed (a probe trial measures the walk's, the lunge's and the crawler's tiles a second from the frames before the constants are written; the probe's numbers go to the register as the clock's source).
- A timed action (`rip`, `unwear`, `bandage`, `loot`, the door `interact`, a `scan` that stands) starts only when the smallest time to contact exceeds the action's duration plus `ACTION_MARGIN_S`; otherwise the planner first gains distance (a leg along the ring's most open heading away from the nearest until the clock allows), then the action runs to its end: a running timed action is cut only when the clock falls under the margin (the cut sends the melee, never a steer), never superseded by a flee's steer. The care chain under a bleed: the rip rides the walk away (`RipClothing` carries `CanBeDoneWhileWalking` on 42.22.2, `#4735`), the bandage at the stop the clock allows. Logged `clock {action, ttc, need, waited}`; the grade counts actions started under the margin (must read 0) and actions cut by a steer (must read 0).

### 3.5 The crawler buffer

A crawler within `CRAWLER_BUFFER_R` (2.0 tiles) ends the standing position: the reflex steps perpendicular to the crawler's bearing (the ring's open side) before pressing the standing target again, and stomps the crawler only when nothing standing is within `K.MELEE_CROWD_R`; the repulsion's crawler weight stays. The grade counts frames with a crawler inside 1.0 tile while a standing zombie is pressed (must read 0 on the `crawler` arm).

### 3.6 The trials and the instruments

- New waves in `driverlib/trial.py`: `trio` (three at 8 tiles, bearings −60, 0, +60), `flank` (one at 8 tiles ahead, a second at 8 tiles 120 degrees off ten seconds later), `crawler` (one standing at 8 tiles and one crawler at 5 tiles 90 degrees off; the spawner sets the crawler state or the wave is dropped with the reason in the report).
- The scorer's new cells: `air %` (swings into the air over presses), `back %` (presses launched moving backward over the retreat's presses), `cone bites`, `clock <0`, `crawler@1`, `room` (the ring's read count and its stop kinds); `grade_x6` the same, frozen for F22.
- A probe trial per instrument before its rule (§§ 3.1, 3.2, 3.4), each a `--probe` plan of `x_trial.py` on the arena, read by a scratch script, its numbers in the trial's row.

## 4. Out of scope

Objectives beyond combat (Angus's `always-an-objective` and the clear-then-loot loop) take Plan 37 once the engagement holds; the door and shelter decisions in contact beyond the clock and the ring; the bare-handed melee (a `no weapon` end still hands to the ladder); the model's goal choices.

## 5. Risks

The attack-while-walking-backward read (§ 3.2) may show the engine cancels the walk or the attack; then the cadence becomes step-press-step with the press on the first tick of the stop, measured the same way. The ring's cost at 10 Hz may exceed the frame budget; it reads every third frame and drops to four headings if the cost leaf says so. The pull can walk the fight toward a second group the frames list farther out; the picker reads every listed zombie's bearing, not only the closing ones. The clock's speeds are measured, not assumed; a wrong constant shows as actions cut by the clock, read in the trials.
