# Plan 36 — the engagement: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the character picks where a fight happens and when a timed action starts, so it is never ambushed, overwhelmed, flanked or touched by a crawler, and keeps every zombie at the edge of melee range by swinging on the moving back step.

**Architecture:** the three-speed architecture stands (the Lua reflex at the client tick under a Python `Maneuver`, the planner at 2 Hz naming intents, the model above). Plan 36 adds one instrument to the frame (the `room` ring, PZA/1.14), tunes the reflex's contact cadence and crawler buffer, and gives the planner two pre-contact decisions: the engagement picker (the pull to a line, the cone trigger) and the action clock (time to contact before any timed action). Instruments and probe trials come before rules; proof is read on the trial rounds (CLAUDE.md § 5 Trials); one evidence session F22 at the end.

**Tech Stack:** Kahlua Lua (PZ Build 42.22.2 client), Python 3 planner, the PZA/1 schema generator (`tools/pza_schema.py`), the trial loop (`x_trial.py`, `driverlib/trial.py`, `tools/trial_score.py`), pytest.

**Spec:** `docs/superpowers/specs/2026-11-11-plan-36-the-engagement-design.md`

## Global Constraints

- Exploratory lane (P32-R): implementer tests and lint gates, no review per task; the next trial boot is the review. The evidence lane (F22, its write-up, `grade_x6`, the rows) takes one opus review.
- Every Lua change: `python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit testing/PZAgent` 0, `python tools/luabalance.py <files>` BALANCED, `python tools/pza_schema.py --check` in sync after `--write`; a smoke boot on the arena pair before any trial depends on it.
- A protocol change is an edit of `testing/agent/base/schema/pza1.json` followed by `--write`; PZA/1.14; `PZA.VERSION` in `PZAgent_Core.lua`.
- No new planner rule behind a version gate (Plan 35 removed them); a rule that needs the ring reads `World.can("room")` off the hello's caps only where an old ring must replay (the goldens announce PZA/1.11).
- Constants live in `policies.py` (planner) or the `K.` table of the Lua file that reads them, each with a one-line comment naming its source.
- Pathspec commits, subjects `Plan 36 Task N: <what>`; no Claude attribution; implementers never push.
- The trials' rules (CLAUDE.md § 5 Trials): a trial is one scored line; a hit is traced only where health was lost; the proof is read on the rounds; a narrow fix takes a pair smoke and one trial on the evidence fixture, not a restarted round.
- Angus's standing rules: never turn and run below `RETREAT_MAX_N` (the fighting retreat), the swing rides the back step, the back step goes only as far as the next swing lands, the shove is a chosen knock-down, every wound analyzed, kills and hits per kill the metrics.

---

### Task 1: The room ring (Lua, schema, the footwork's turns; opus, its own worktree)

**Files:**
- Modify: `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_StanceWork.lua` (the probe read becomes one shared function `K.workClearAlong(p, heading, maxTiles)` returning the clear distance and the stop kind; the ring `K.workRoom(p)` for eight headings; the turns read the ring)
- Modify: `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_Core.lua` (`PZA.VERSION` "1.14"; the frame's `me.room` written every third frame from `K.workRoom`)
- Modify: `testing/agent/base/schema/pza1.json` (`me.room`: `{h: [8 numbers, tiles clear], stop: [8 strings: "wall" | "hop" | "door" | "open"], tick}`; the hello's caps gain `room`), then `python tools/pza_schema.py --write`
- Modify: `testing/agent/base/world.py` (`World.room()` returns the latest ring or None; `World.room_open(bearing_deg)` the clear tiles along the nearest heading)
- Test: `testing/tests/pzagent/test_lua_footwork.py` (the shared read on a fake square grid: a wall at 1.5 tiles reads 1.0 clear and "wall"; a hoppable edge reads "hop"; a door square reads "door"; the ring's eight headings), `testing/tests/pzagent/test_world.py` (`room_open` picks the nearest heading)

**Interfaces:**
- Produces: `me.room` on every third frame; `World.room()`, `World.room_open(bearing)`; the Lua `K.workRoom(p)` table `{h = {...}, stop = {...}}` the melee's work tick reads once per tick.

- [ ] **Step 1:** write the failing Lua tests for `K.workClearAlong` on the fake grid (wall, hop, door, open to 3.0) and for `K.workRoom`'s eight headings; run `python -m pytest testing/tests/pzagent/test_lua_footwork.py -q`, expect FAIL on the missing names.
- [ ] **Step 2:** refactor the probe read of `PZAgent_StanceWork.lua` into `K.workClearAlong` (the existing isSolid, isSolidTrans, isBlockedTo and hop reads; a door square read through the square's door object, `IsoDoor`, the read guarded by `PZA.call`), and `K.workRoom` over the headings 0, 45, …, 315 degrees in 0.5-tile steps to 3.0; the turns of the footwork read `K.workRoom`'s cached table (refreshed when the player's square changes or every `K.WORK_ROOM_TICKS` = 3 ticks) instead of probing per heading.
- [ ] **Step 3:** run the tests, expect PASS; `kahlua_lint`, `luabalance` on both Lua files.
- [ ] **Step 4:** the schema: add `me.room` and the `room` cap to `pza1.json`; `python tools/pza_schema.py --write`; `--check` in sync; `PZA.VERSION` "1.14"; `PZAgent_Core.lua` writes `me.room` every third frame (a `tick` field names the client tick it was read on).
- [ ] **Step 5:** `World.room()` and `World.room_open(bearing_deg)` with tests; `python -m pytest testing/tests/pzagent/test_world.py testing/tests/pzagent/test_pza_schema.py testing/tests/pzagent/test_pza1.py -q` PASS.
- [ ] **Step 6:** the cost: the frame's `cost` leaf already carries the frame's ms; add `room_ms` to it (the ring's own time) so the probe trial can read it.
- [ ] **Step 7:** commit `Plan 36 Task 1: the room ring (me.room, PZA/1.14; the footwork's turns read it)` -- the touched files.
- [ ] **Step 8 (controller):** the pair smoke on the arena, then the probe trial: `x_trial.py --variant ladder --fixture arena-east --no-llm --goals hold --waves lone --minutes 3` read by a scratch script for the ring's stop kinds against the arena's walls and the map's blocked edges, and `room_ms` p50/p99; the row in `trials.md`; the ring's budget ruled (CLAUDE.md § 6 Rulings) before Task 3 reads it.

### Task 2: The contact cadence and the crawler buffer (Lua; opus, its own worktree, after Task 1 merges)

**Files:**
- Modify: `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_StanceMelee.lua` (the press during the back step; the swing-into-air count; the step forward on a staggered target; the shove as a knock-down; the nearest-attacker facing)
- Modify: `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_StanceWork.lua` (the step bounded by the next landing hit; the crawler buffer `K.CRAWLER_BUFFER_R` 2.0; the perpendicular step)
- Modify: `testing/agent/base/schema/pza1.json` (the press leaf gains `moving_back` (bool) and `air` (bool); the work leaf `shove_for`, `step_for` gains "stagger_in" and "crawler_buffer"), `--write`
- Test: `testing/tests/pzagent/test_lua_melee.py`, `test_lua_footwork.py`

**Interfaces:**
- Consumes: `K.workRoom` (Task 1) for the perpendicular step's open side.
- Produces: the leaf fields above, read by Task 5's scorer and grade.

- [ ] **Step 1 (controller, before the task):** the probe trial of the attack while walking backward: on the arena `lone` wave with a scratch overlay that holds the backward key through the press (the harness's `PZAgent_FacingProbe.lua` is the model of a probe act), read `attackStarted`, `moving`, `pace` and the landed hit across ten presses; the row in `trials.md`; the ruling names which cadence Task 2 builds (the press on the moving back step, or the press on the first tick of the stop).
- [ ] **Step 2:** failing tests: a retreat press launched with the back step held (`moving_back` true on its leaf); a press launched with the target's predicted landing distance beyond `reachOf` counts `air` and the retreat's back step stops while the target is beyond reach; a target in `staggerback` beyond reach gets one `step_for = "stagger_in"` then the press; two standing inside reach + point blank: the nearest is shoved (`shove_for = "knockdown"`), the next swung, the downed one stomped only with nothing standing within `K.MELEE_CROWD_R`; inside point blank the facing and the pin go to the attacker counted by `attackers` or the nearest standing; a crawler within 2.0 tiles: the perpendicular step toward the ring's open side before the next press, the stomp only with nothing standing within `K.MELEE_CROWD_R`.
- [ ] **Step 3:** implement each in the melee's tick order (the hit step first, then the work tick, then the crowd, then the press), the constants in `K.` with their sources; the headers of both files updated.
- [ ] **Step 4:** tests PASS; `kahlua_lint`, `luabalance`, `pza_schema --check`; commit `Plan 36 Task 2: the contact cadence (the press on the back step, the step keyed to the next hit, the chosen shove, the nearest attacker faced) and the crawler buffer`.
- [ ] **Step 5 (controller):** the pair smoke, then one `trio` and one `crawler` trial (Task 5's waves land first) read for `air`, `moving_back`, `shove_for`, `crawler@1`.

### Task 3: The engagement picker (planner; opus, the shared tree)

**Files:**
- Modify: `testing/agent/base/planner/group.py` (the leave at `GROUP_LEAVE_N` becomes the pull: a withdraw vector to the running melee; the spread and the cone reads; `engage_pull` logging)
- Modify: `testing/agent/base/planner/threat.py` (`_decide` passes the pull's vector as `policy.retreat`; the `many` run above `RETREAT_MAX_N` along `World.room_open`)
- Modify: `testing/agent/base/planner/dispatch.py` (the withdraw send carries the pull; the `leave` hold removed)
- Modify: `testing/agent/base/planner/policies.py` (`PULL_SPREAD_DEG` 60, `PULL_STOP_DEG` 45, `CONE_HALF_DEG` 60, `CONE_TRIGGER_R` 4.0, with comments)
- Test: `testing/tests/pzagent/test_survive_as.py` (new: replay fixtures of F21's lines 364 to 412 shape: three closing at a spread above 60 degrees send the melee with the withdraw along the bisector; the spread under 45 drops it; a zombie 120 degrees off the cone inside 4 tiles and closing sends the vector that brings it into the cone; the `many` run above `RETREAT_MAX_N` takes the ring's open heading; no `leave` hold line remains)

**Interfaces:**
- Consumes: `World.room_open` (Task 1); the melee's `withdraw` (Plan 35).
- Produces: `engage_pull {why, spread, n}` on the threat why, read by Task 5.

- [ ] **Step 1:** failing replay tests as listed; run `python -m pytest testing/tests/pzagent/test_survive_as.py -q`, FAIL.
- [ ] **Step 2:** implement in `group.py` (one method `_pull()` returning the vector or None, with the spread and the cone reads on the frame's listed standing zombies within `GROUP_ENTRY_R` for the spread and `CONE_TRIGGER_R` for the cone), wire it through `threat._decide` and the dispatch, delete the `leave` hold's branch and its tests by name (named in the report), refactor the docstrings to what remains.
- [ ] **Step 3:** lane tests PASS; the goldens `python -m pytest testing/tests/pzagent -k golden -q -m slow` (a moved line attributed to the removed hold or the pull, re-recorded under the named change); commit `Plan 36 Task 3: the engagement picker (the pull to a line, the cone trigger; the leave hold becomes the pull)`.

### Task 4: The action clock (planner; opus, the shared tree, after Task 3)

**Files:**
- Create: `testing/agent/base/planner/clock.py` (`time_to_contact(world)` per listed zombie: `(dist - reach) / speed_of(state)`; `ActionClock.allows(action_kind, duration_s)`; the speeds `WALK_TPS`, `LUNGE_TPS`, `CRAWL_TPS` from the probe of Step 1; `ACTION_MARGIN_S`; the durations per action kind from the drivers' records)
- Modify: `testing/agent/base/planner/care.py`, `care_yield.py` (the care's commit asks the clock; the rip rides the walk away; a running care is cut by the clock only, into the melee), `goal_runner.py` / `goal_policies.py` (loot and door interactions ask the clock), `flee.py` (a gain-distance leg along `World.room_open` when the clock refuses), `policies.py` (the constants)
- Test: `testing/tests/pzagent/test_clock.py` (new), `testing/tests/pzagent/test_survive_at.py` (new: F21's care lines 427 to 494 replayed: no rip starts under the margin; the rip rides the walk; the bandage at the stop the clock allows; the trials' door interaction with two thumping at 0.3 is refused and the melee sent)

**Interfaces:**
- Consumes: `World.room_open`; the melee dispatch (`_contact_rule`).
- Produces: `clock {action, ttc, need, waited}` on the why, read by Task 5.

- [ ] **Step 1 (controller, before the task):** the speeds probe: one arena `lone` trial and one `crawler` trial read by a scratch script for the walk's, the lunge's and the crawler's tiles a second from consecutive frames; the numbers in the rows and, at F22's mint, the register (the clock's source).
- [ ] **Step 2:** failing tests as listed; FAIL.
- [ ] **Step 3:** implement `clock.py` and the call sites; each site logs `clock`; a refused action's gain-distance leg is one leg, then the action completes (`finish-actions-gain-distance`).
- [ ] **Step 4:** lane tests, the goldens; commit `Plan 36 Task 4: the action clock (time to contact before any timed action; the rip rides the walk; a running care is cut by the clock only)`.

### Task 5: The waves, the scorer's cells and `grade_x6` (sonnet for the waves and scorer, opus for the grade; its own worktree)

**Files:**
- Modify: `testing/agent/driverlib/trial.py` (`trio`, `flank`, `crawler` waves; the crawler spawn through the harness's spawn command with the crawler state, or the wave dropped with the reason in the report), `tools/trial_score.py` (cells `air %`, `back %`, `cone bites`, `clock <0`, `crawler@1`, `room`; `--round` carries them), `docs/reference/tools.md`
- Create: `testing/agent/base/grades/x6.py` (`grade_x6`: `base = grade_x5`, the new readings; every live constant copied), `testing/agent/drivers/f_grade_18.py`, `e_grade_27.py`, `testing/tests/pzagent/test_grades_x6.py` (the F21 artifact under `x6` with every new reading empty and `base` byte-equal to `x5`'s; the mutation pass per reading), `test_f_grade_18.py`, `test_e_grade_27.py`, `tools/tests/test_trial_score.py` additions

- [ ] **Step 1:** the waves with their spawner tests; commit `Plan 36 Task 5a: the trio, flank and crawler waves`.
- [ ] **Step 2:** the scorer's cells with tests on synthetic logs (a broken reader fails each); commit `Plan 36 Task 5b: the scorer's air, back, cone, clock, crawler and room cells`.
- [ ] **Step 3:** `grade_x6` and the drivers with the F21 regrade test and the mutation pass; commit `Plan 36 Task 5c: grade_x6, f_grade_18 and e_grade_27`.

### Task 6: The trials (the controller)

- [ ] Rounds per § 2 on the arena waves (lone, pair, trio, flank, crawler), `agent` with the model (six), `street-1` (three); each a scored line; a hit traced where health was lost; fix rounds as narrow traced fixes with a pair smoke and one evidence-fixture trial each; the `--round` summary against Plan 35's final arm.

### Task 7: F22 and the close (sonnet for the driver copy; opus for the write-up and its one review)

- [ ] `f_goals_22.py` from `f_goals_21.py` with `grade_x6`, re-based to the proven head before the boot; the session under § 5; the artifact flow (the script re-reading every adapted cell, the regrade test); the shot sheet and visual pass; the write-up T106 with one opus review and the verbatim fix round; the mint; the close (the report, HISTORY, CLAUDE.md §§ 1 and 3, the lessons, the memory, the full parallel pytest, the push).
