# Plan 33: the group — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the character leaves a forming group before it closes, finishes a fallen zombie without standing on it, stomps a crawler within reach before it bites, never runs into a zombie at its side, and keeps its body on the nearest zombie between presses; proven in trials on the `agent` fixture with the model, `street-1` and the arena pair, then one evidence session.

**Architecture:** four switched changes on Plan 32's composition (`d31ca7d0` and after): the finish's head-step floor and cap in the Lua reflex, the crawler-first target and the group-leave and drag-guard rules in the planner's threat and fight modules, the idle snap in the reflex's hold; a `--waves none` trial plan so the `agent` fixture runs under the trial loop with the model; `grade_x3` reading the new leaves; one evidence session F19.

**Tech Stack:** Python 3 (pytest with pytest-xdist, lupa for the Lua tests, the fakes), Kahlua Lua, the register tools, `git worktree`.

**Spec:** `docs/superpowers/specs/2026-11-09-plan-33-the-group-design.md` (§ 1 the chain F18 read, § 2 the success criteria, § 3 the design, § 5 the risks). The record behind it: Plan 32's report `docs/superpowers/specs/2026-11-09-plan-32-the-facing-report.md` § 5 and § 7, F18's rows #4703-#4712, `.superpowers/sdd/2026-11-08-plan-32-the-facing/task-7-f18-writeup-report.md` and `visual-review-f18.md`.

## Global Constraints

- CLAUDE.md §§ 3, 4, 5, 6 in full: pathspec commits, the gates (the parallel pytest gate), the machine-safety rules on every boot (doctor, the memory read with no floor, one live session at a time, Angus's own client never touched, no OS cursor, a console shown or minimized, a detached launch only past the ten-minute cap), the evidence rules on Task 6's session alone (P31-T).
- **Ruling P32-R:** Tasks 1 to 5 are the exploratory lane (no review; the next trial boot is the review; a harness Lua change takes a smoke boot before trials depend on it); Task 6 the evidence lane (one opus review at the mint, the fix round applying the reviewer's texts).
- **The trials cover the evidence fixture:** every trials round runs the `agent` fixture with the model beside `street-1` and the arena pair (CLAUDE.md § 5 Trials, Plan 32's lesson).
- Kahlua rules for every harness Lua file; every member index-checked; every flag restored on every exit path; a Lua edit appends new sites at the end of its file or re-anchors every `repo:` pointer into it in the same commit; `luabalance`, `kahlua_lint`, `hotpath_lint`, `bus_inventory --check`, `pza_schema --check` gate every harness commit.
- The decision goldens move only under a named change with every moved line attributed; a unit test of an earlier rule whose fixture a new rule reaches is pinned with the new rule's switch off.
- The metrics are kills, hits per kill (both counts) and the facing columns in every trial row, plus the new `head_ticks` max column.
- Models: opus for the reflex (Task 1), the planner rules (Tasks 2, 3), `grade_x3` and the write-up with its review; sonnet for the trial plan and the driver copy (Tasks 4, 6a) and a root-file edit.

---

### Task 1: The finish's head-step floor and cap, the idle snap (the reflex)

**Files:** modify `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_StanceMelee.lua` (`finish`: skip the look gate when `dh < K.HEAD_LOOK_FLOOR` 0.15; the `head` step counts `st.headTicks` and at `K.HEAD_MAX_TICKS` 20 ends `done handback` with `why head_stall`, the standing count and distances; the leaf gains `head_ticks`; the `FACING` table gains `idle(p, zid)` for the idle snap: while no melee runs and the Motor's idle hold is on, the body snapped each frame onto the nearest standing zombie within `K.IDLE_SNAP_R` (`KEEP_R` 2.5), the aim posture kept, off while a steer or walk runs), `PZAgent_Motor.lua` (the per-frame hold calls `FACING.idle` under `K.IDLE_SNAP`), `PZAgent_Stance.lua` only if the aim leg's hold must yield to the idle snap; the schema untouched unless the leaf's keys are enumerated (`result_melee_step.press`); tests `test_lua_melee.py` (the stall reproduced on a fake whose look never settles: the old gate holds `head`, the new presses at the floor and hands back at the cap with the count), `test_lua_motor.py`/`test_lua_stance.py` (the idle snap's calls and its silence under a walk), a mutant per rule.

**Interfaces:** produces the leaf keys `head_ticks` and the handback `why head_stall`; `K.HEAD_LOOK_FLOOR`, `K.HEAD_MAX_TICKS`, `K.IDLE_SNAP`, `K.IDLE_SNAP_R`.

- [ ] RED/GREEN per rule; the gates; the frozen regrades byte-identical; commits `Plan 33 Task 1: the finish's head-step floor and cap`, `Plan 33 Task 1: the idle snap`.

### Task 2: The crawler first (the planner)

**Files:** modify `testing/agent/base/planner/fight.py` (`CRAWLER_FIRST`: a zombie reading `crawler` or `onFloor` within `CRAWLER_R` 1.0 while a standing one is within `DANGER_R` is the pin of a `finish` before the standing one is met, unless the standing one is within `STAND_MIN_R`; the pin returns to the standing zombie when the crawler reads dead or beyond `CRAWLER_R`), `policies.py` (`CRAWLER_R`), tests: the F18 replay from line 356 (the crawler targeted), the pins of earlier finish tests with the switch off, a mutant.

- [ ] RED/GREEN; the goldens re-recorded under the named change if a ring reaches the rule, every moved line attributed; commit `Plan 33 Task 2: CRAWLER_FIRST`.

### Task 3: The group's entry and the drag guard (the planner)

**Files:** modify `testing/agent/base/planner/threat.py` (`GROUP_LEAVE`: two standing within `GROUP_NEAR_R` closing over two lines with no wall or doorway within `WALL_R` 1.5 at the back sends a `leave` leg toward the nearest known door or doorway within `LEAVE_R` 20 (the doorway stand resumed there), else a run from the centroid for `LEAVE_S` 4 s; `DRAG_GUARD_FIGHT`: the drag-down guard under a hit reaction or `STUCK_FRAMES` 10 unmoving frames shoves the standing zombie in front instead of a run; `SIDE_CLEAR`: no `steer` whose heading passes within `SIDE_R` 1.0 of a standing zombie, the heading rotated to the nearest clear bearing else the shove), `policies.py` (the constants), `edges.py`/`doorway.py` if the leave leg reuses them; tests: F18's lines 380 to 415 replayed (the guard's lines become shoves or clear steers), a synthetic two-closing case (the leave leg), the pins, a mutant per rule.

- [ ] RED/GREEN; the goldens under the named change; commits per rule.

### Task 4: The trial plan `none` and `grade_x3` (the instrument)

**Files:** modify `testing/agent/driverlib/trial.py` (`WAVE_PLANS["none"]`: no spawns, the fixture's own zombies; `--fixture agent` accepted), `testing/tests/pzagent/test_x_trial.py`; create `testing/agent/base/grades/x3.py` (`grade_x3`: `grade_x2` under `base` plus `head_ticks` {max, over_cap, by melee}, `crawler_first` {lines, stomps, kills}, `group_leave` {legs, to a door, runs, the standing count at each}, `drag_guard` {shoves, clear steers, runs refused}, `idle_snap` {frames, median body error between presses}), `testing/agent/drivers/f_grade_15.py`, `e_grade_24.py`; `tools/trial_score.py` gains `head_ticks max`; tests `test_grades_x3.py` with a mutation pass, `test_trial_score.py`.

- [ ] RED/GREEN; commits `Plan 33 Task 4: the trial plan none`, `Plan 33 Task 4: grade_x3 and the scorecard's head_ticks column`.

### Task 5: The trials (the controller boots, P31-T)

Two rounds against Plan 32's head `d31ca7d0` (a snapshot): the `agent` fixture with the model (`--fixture agent --waves none`), `street-1` with the model, the arena pair; a smoke boot of Task 1's Lua first (`x_trial.py --fixture arena-east --waves lone --no-llm --goals hold`); the rows in `testing/trials/trials.md`; the ruling on the proof (spec § 3.6).

### Task 6: The evidence session and the close

`f_goals_19.py` from `f_goals_18.py` with `grade_x3` and `f_grade_15.py` (Task 6a, sonnet); the session under the full § 5; the artifact flow (the script re-reading cells by shape); the visual pass; the write-up T102 with the jar rows T103 (the crawler's bite) under one review; the mint; the close (the report, HISTORY, CLAUDE.md §§ 1 and 3, the lessons, the memory files, the full parallel pytest, the push).
