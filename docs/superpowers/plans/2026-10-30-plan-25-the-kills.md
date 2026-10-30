# Plan 25: the kills — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a survival agent that kills more than it flees: iteration 13 turns the stomp into a dependable kill, ends the holds that froze E10 and F3, and gives the LLM source a truthful view and a second round of its prompt, read live over nine sessions.

**Architecture:** the Python planner under `testing/agent/base/planner/` (`survive.py`, `threat.py`, `fight.py`, `flee.py`, `doorway.py`, `water.py`, `care.py`, `goals.py`, `goal_prompt.py`, `llm.py`, `view.py`) over the unchanged PZA/1.7.1 Lua; the driver library (`shots.py`, `day.py`) and the grades (`gates_e.py`, `gates_f.py`) grown by appended, frozen-per-artifact functions; the chain drivers copied under their own key per session; every number in a brief from its register row or guide.

**Tech Stack:** Python 3 (pytest, the lupa-free fakes and the decision-golden replays), the PZA/1.7.1 Lua unchanged, the `claude` CLI for the LLM source.

**Spec:** `docs/superpowers/specs/2026-10-30-plan-25-the-kills-design.md` (its § 1 the readings, § 2 the work, § 3 the carried rulings).

## Global Constraints

- CLAUDE.md §§ 3, 5, 6 in full: pathspec commits, no `--amend`, the gates, one live session at a time under § 5 (doctor, ≥ 12 GB free read and ledgered, a quiescent tree outside the docs lane, a detached launch polled in foreground calls under 10 minutes), a driver never edited after its run, a gate function frozen once an artifact carries its output.
- The loop (P24-AF): implementers run their lane's tests with the slow marker off; the controller runs the full pzagent suite once per wave at a quiescent head; one ruling per task with its file:line and test spelled out; reviews bundled; a boot never waits on a lane.
- The decision goldens (six, `testing/tests/pzagent/test_replay_decisions.py`): re-recorded only under a named cause with the first moved line pinned and a rule-off seam reproducing the previous file byte for byte, as Task 32's `pre_t36` form.
- The metric is zombies killed (P24-Q), read off the act lines' `targetDead` results and the `zombie_dead` events (`grade_e9`), never off `loop.results` alone.
- A write-up brief's trace is a hypothesis the writer verifies; the four-step pattern (write-up, review, one fix round, re-review) precedes every mint.
- Sessions: nine at most (spec § 2.4); the kills table of the report grows one row per session.
- No edit under `mod/`; no JDK; no API key in the tree or environment; the model sees game state only.

---

### Task 1: The harness before the first boot — `grade_f6`, the shots' guard reading, the slow list

**Files:** modify `testing/agent/base/gates_f.py` (append `grade_f6`, `report_lines_f6`, `gate_f6`), `testing/agent/driverlib/shots.py` (the screen line's `guard` field), `testing/tests/slow_tests.txt`, `tools/tests/slow_tests.txt`; create `testing/agent/drivers/f_grade_6.py`, `testing/tests/pzagent/test_gates_f6.py`; extend `testing/tests/pzagent/test_shots.py`.

**Interfaces:**
- Consumes: `gates_e.grade_e9(record, logs)` and its kill reader (`e_kills_9`, Task 40 of Plan 24); `gates_f.grade_f5`; `shots.screen_guard(hwnd, rect, pid)` returning None or `(reason, other_class)`.
- Produces: `grade_f6(record, logs) -> dict` with `kills` from `e_kills_9` and every other key `grade_f5`'s; a screen index line carrying `guard: {"foreground_class": <str>, "passed": true}`; `shots.method_of(line)` unchanged.

- [ ] **Step 1: RED.** In `test_gates_f6.py`: `grade_f6` on `testing/artifacts/f_goals_4-20261030-114742/` reads `kills.planner` 5 with ids `[17072, 17060, 17071, 17073, 17098]` and `kills.events` 5; on `f_goals_2-20261029-041705/` reads 2; `grade_f5` on F3's `f_grade.txt` byte-identical (the frozen reproduction). In `test_shots.py`: a screen line from the fake taker carries `guard.foreground_class` (the client's own class) and `guard.passed` true; a window line carries `skipped_screen` as today and no `guard.passed`.
- [ ] **Step 2: run** `python -m pytest testing/tests/pzagent/test_gates_f6.py testing/tests/pzagent/test_shots.py -q -m "not slow"`: the new tests fail (`grade_f6` undefined; `guard` absent).
- [ ] **Step 3: implement** `grade_f6` appended at `gates_f.py`'s end: `g = grade_f5(record, logs); g["kills"] = gates_e.e_kills_9(record, logs); g["grade"] = "grade_f6"`; `report_lines_f6` prepends the kills headline naming the three sources (act lines, events, engine); `f_grade_6.py` is `f_grade_5.py`'s command line over `grade_f6`. In `shots.py`, the taker writes `guard` on every screen line from the guard's foreground read (the class name only, never a title).
- [ ] **Step 4: run** the two files: green; `python tools/bus_inventory.py --check` in sync.
- [ ] **Step 5: the slow list.** Run `python -m pytest tools/tests testing/tests -q --durations=60 -m "not slow" > .superpowers/sdd/2026-10-30-plan-25-the-kills/durations.txt 2>&1` once (the controller, at a quiescent head); every test over 2 s joins its `slow_tests.txt` by node id; `test_zz_coverage` stays listed.
- [ ] **Step 6: commit** `Plan 25: grade_f6 reads the kills off the act lines; the screen index line carries the guard's reading; the slow list re-derived (Task 1)` — pathspec on the files above.

### Task 2: The refactor debt as pure moves

**Files:** modify `testing/agent/base/planner/survive.py`, `threat.py`, `goals.py`; create `planner/hold.py` (the hold and spent reads: `_read_spent`, `_read_strain`, `_wounded_fight`, `_lone`), `planner/finish.py` (`_flee_finish`, `_finish_end`, `_finish_chaser`, the stomp wait), `planner/pull.py` (`_pulls`, `_pull_pin`, `_pull_waits`, `pulling`, `pull_from`, `_observe_edge`), `planner/goal_runner.py` (the runner) and `planner/goal_policies.py` (the sources' policies); their tests moved beside them.

**Interfaces:**
- Consumes: the `Threat` mixin's methods as `threat.py` holds them at `5e3ad986`; `goals.GoalRunner`, `ScriptedSource`, `LLMSource`.
- Produces: the same names re-exported from `threat.py` and `goals.py` through a lazy `__getattr__` (the frozen drivers import them from there); `assess()` reading every observe inside `_read` (`Care.observe`, `Night.observe`, the Fight's and Flee's) and `_apply` carrying every side effect.

- [ ] **Step 1: the pure move.** Cut the functions into the new modules without a changed line beyond imports and the mixin wiring; run `python -m pytest testing/tests/pzagent/test_replay_decisions.py -q -m "not slow"`: the six goldens byte-identical; commit `Plan 25: the hold, the finish and the pull in their own modules; the goal runner and policies split (a pure move, Task 2)`.
- [ ] **Step 2: the observes into `_read`.** RED: a test that `assess()` calls no `observe` after `_read` returns (a recording fake). Implement; the goldens that move (the observe order can shift a why) re-recorded under the named cause `OBSERVES_IN_READ` with `PRE_T2` pins and the switch-off reproduction; commit `Plan 25: the observes read in _read, every side effect in _apply (Task 2)`.
- [ ] **Step 3: the docstring.** `survive.py`'s history paragraphs (lines about 230–291 at `5e3ad986`) cut to one line per iteration naming its spec item (`2026-10-29-plan-24-the-group-design.md § 6 item N`); the module sizes in the report (`threat.py` under 700 lines, `goals.py` under 700); commit `Plan 25: survive.py's history as spec pointers (Task 2)`.

### Task 3: Survival iteration 13 (P25-A to P25-F)

**Files:** modify `planner/fight.py`, `planner/hold.py`, `planner/finish.py`, `planner/flee.py`, `planner/doorway.py`, `planner/care.py`, `planner/view.py`; tests `testing/tests/pzagent/test_survive_t.py` (new), the goldens.

**Interfaces:**
- Consumes: the frame's `body.armPain`, `body.strain`, `stats.endurance`, `zombies[].onFloor`, the shove result's `knockdown`, the act results; Task 2's modules.
- Produces: new why fields `corner` {`kind`: `swing`|`break`}, `finish_first` (the stomp sent before the attack's walk), `hold_walk` (the `strain` flee at a walk), `ride_wait`, `door_walk` {`stall`, `end`}, `fence_wait`; the view key `spent` {`kind`, `value`}.

The rulings (the controller's, 2026-10-30; each a rule with a test and a mutant):
- **P25-A, the corner under a hold** (as ruled by `review-t3.md` after the first build: the plan's first premise, "a halved swing beats a seventh shove", held nowhere in the register). After a shove whose result read `knockdown` false, the Fight breaks away through the gap the shove opened (a `steer` on the heading away from the pushed zombie's bearing) when a heading is clear; when none is, or one standing zombie is within `FIGHT_REACH`, it shoves again (#4373: the knock-down is a crit roll pain does not touch; #4374: the stomp that follows is outside #4370's divider), and takes the swing only while the swing is undivided (arm pain under `STRAIN_SOFT` and no endurance or tired hold); `SHOVE_REPEAT_S` 3.0 s applies to the break's pair only. The Doorway fight keeps its shove every time (the break would leave the chokepoint; #4416). Test: E11's last-minute geometry (two zombies at point blank, a shove read `knockdown` false, a clear heading) sends `steer`; one zombie at arm pain 219.9 sends `shove`; one zombie at arm pain under 10 with no hold sends `attack`.
- **P25-B, the stomp before a running attack.** A fallen target within `FINISH_R` takes the `stomp` before any `attack` walk toward a standing one beyond `FIGHT_REACH`. Test: E11's third target (fallen 4.3 s under `out of reach` attacks) gets the stomp on its first fallen frame.
- **P25-C, the endurance hold on the run.** Under the endurance hold the `strain` flee walks (`gait` `walk`) when no zombie is within `DANGER_R` and runs inside it; the hold releases above 0.80 as today, or after `HOLD_SPAN_MIN` 15 game minutes with no zombie within `DANGER_R` on the last `HOLD_QUIET_S` 20 s (the hypothesis of #4415: the run sends keep the endurance from the release line). The view carries `spent` {`kind`, `value`}. Test: F3's hold (set at 648, the flee lines) walks on the lines with no zombie within `DANGER_R` and releases by game minute 663 in a quiet replay.
- **P25-D, the ride waits for the next send.** A riding bandage in flight (`keepMoving`, until its `done`/`failed` result) blocks the hold's shoves and stomps; the Fight's own sends under attack within `KEEP_R` still pre-empt it. Test: E11's rides a112/a116 geometry keeps the bandage.
- **P25-E, the stand's stalled walk.** A doorway stand's walk whose position holds within 0.5 tiles for `DOOR_WALK_S` 20 s re-routes once through `reachable_adjacent` and then drops the plan (`doorway_left` `stall`). Test: E11's stall 11.44 tiles from the door.
- **P25-F, the fence wait** (the guides' change 4): a chasing target across a known hoppable edge (`hopN`/`hopW`) is neither sought across nor marked unreachable: the Fight stands in the stance `FENCE_BACK_R` 1.5 to 2.5 tiles back on its own side, faces the fence, and swings or stomps when the target crosses (its `onFloor` after the hop is P24-AQ's finish); left after `STAND_MAX_S` as today. Test: a fake fence row with the chaser across it.

- [ ] **Step 1: RED** `test_survive_t.py` with a test per rule and per refusal (the list above), a mutant per rule tallied in the report.
- [ ] **Step 2: run** `python -m pytest testing/tests/pzagent/test_survive_t.py -q`: fails.
- [ ] **Step 3: implement** rule by rule, one commit per ruling or shared function: `Plan 25: <the rule> (P25-x, survival iteration 13)`.
- [ ] **Step 4: goldens.** The six re-recorded only under the named cause with `PRE_T3` pins and each switch alone; E4/F1 carry the endurance hold, so P25-C moves them: attribute the first moved line.
- [ ] **Step 5: run** the lane: `python -m pytest testing/tests/pzagent/test_survive*.py testing/tests/pzagent/test_fight*.py testing/tests/pzagent/test_replay*.py -q -m "not slow"`; the controller's full pzagent gate at the wave's head.

### Task 4: The LLM source's second round

**Files:** modify `planner/view.py`, `planner/goal_runner.py`, `planner/llm.py`, `schema/goals.json`, `planner/goal_prompt.py`; tests `testing/tests/pzagent/test_view.py`, `test_llm.py`, `test_goals.py`.

**Interfaces:**
- Consumes: the view's `buildings[].looted`, the runner's cooled refusals, `EXPLORE_MAX_TILES` 60, `view.WHYS`, the hold why from Task 3 (`spent`).
- Produces: `world.looted(building) -> bool` as the one rule (every `wanted_uses` class present in the building met or its containers all read); the runner's refusal `{type, args, end: "cooled", why}` laid over `last_goal` once; `out of range` measured from the calling view's `pos`; the view line `hold: <kind> <value>` and the `Rest` goal's description naming it.

- [ ] **Step 1: RED.** A building with only capped clothing left reads `L`; a cooled answer reaches the next view's `last_goal` with `end` `cooled`; an `ExploreToward` 58 tiles from the calling view's `pos` and 62 from the collecting view's is accepted; the view renders `hold endurance 0.73` when the hold is set and nothing when not.
- [ ] **Step 2: run** the three test files: fails.
- [ ] **Step 3: implement**; `SYSTEM`'s line 3 names the hold (`Rest` when `hold` reads); principle 8 held (no path, constant or internal in `SYSTEM`); the goldens byte-identical (the scripted source unchanged).
- [ ] **Step 4: commit** `Plan 25: one looted rule, the cooled refusals carried, out-of-range from the calling view, the hold in the view (Task 4)`.

### Task 5: The drivers — `e_day_12` with `grade_e10`, `f_goals_5` for the night, `f_goals_6` unarmed, the fixture `agent-night`

**Files:** create `testing/agent/drivers/e_day_12.py`, `e_grade_10.py`, `f_goals_5.py`, `f_goals_6.py`, `testing/tests/pzagent/test_e_day_12.py`, `test_f_goals_5.py`, `test_f_goals_6.py`, `test_gates_e10.py`; modify `gates_e.py` (append `grade_e10`), `testing/profiles/agent-night.toml`; the fixture `testing/fixtures/agent-night/` provisioned by `python testing/pzt provision` (the controller, under § 5: a start hour of 20:00 is a world-generation value).

**Interfaces:**
- Consumes: Task 3's why fields; Task 1's `grade_f6`; the driver copy pattern (`e_day_11.py`, `f_goals_4.py`).
- Produces: `grade_e10` reading P25-A to P25-F (corner swings and breaks, first-frame stomps before attacks, hold walks and timed releases, ride waits, stall re-routes and drops, fence waits with their outcomes) over `grade_e9`; `f_goals_5.py` on the fixture `agent-night` (the night reached at the 90-minute day from 20:00) with its driver constant `FIXTURE = "agent-night"`; `f_goals_6.py` with `KIT_WEAPON = None` (the bat withheld) and the weapon want's reading in `grade_f6`.

- [ ] **Step 1:** `grade_e10` RED (a fixture per reading, a zero case and a counting case) then GREEN; `grade_e9` byte-identical on E11's `e_grade.txt`.
- [ ] **Step 2:** the three drivers copied under their own keys with their copy tests; the base sentences name the planner's commit at Task 4's close (renamed before each boot as a pre-run edit).
- [ ] **Step 3:** the controller provisions `agent-night` (doctor, memory, one session) and ledgers it; `pzt doctor` lists it.
- [ ] **Step 4: commits** `Plan 25: grade_e10 (Task 5)`, `Plan 25 e_day_12: the twelfth chain's driver (Task 5)`, `Plan 25 f_goals_5 and f_goals_6: the night and the unarmed LLM sessions (Task 5)`.

### Task 6: The sessions

Nine at most, each under § 5 with its artifact commit (files byte-identical, the stub guide, the row, the do-not-cite rows, the alias, a spec § 4 item), its write-up (a fresh opus writer, `[T<task>.n/M/n=1]`), its review, one fix round, its re-review and the mint, as Plan 24's Tasks 30, 34, 38 and 39:
- E12 (iteration 13) → iteration 14's rulings from its reading (Task 7) → E13 → iteration 15 → E14, E15, E16 as the budget allows;
- F4 (`f_goals_5`, the night: `Shelter` and `Rest` exercised) and F5 (`f_goals_6`, unarmed: the weapon want), F6 on the prompt's third round;
- a probe only if a Lua change needs one.

### Task 7: Iterations 14 and 15

Written as Task 3's shape from E12's and E13's write-ups (their research-notes threads name the next work); the rulings P25-G onward; each with its tests, mutants, goldens and a driver copy (`e_day_13`, `e_day_14`) with the next grade.

### Task 8: The docs

Name the combat rows #4368–#4377 from `platform/overview#routing` (a combat line in the routing table) — optional, a docs-lane task beside a session.

### Task 9: The close

The whole-pass review (opus), one consolidated fix wave and its re-review; the report `docs/superpowers/specs/2026-10-30-plan-25-the-kills-report.md` with the kills table; HISTORY.md; CLAUDE.md § 1 (the agent row) and § 3 (the baseline); the memory files (§ 8); the full pytest from a saved file; the push.
