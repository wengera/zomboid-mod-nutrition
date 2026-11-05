# Plan 31: the rebuild — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a player-like control of the character, rebuilt rather than tuned: a swing that lands and is pressed while squared on an attacking zombie, a finish aimed at the head, a dressing that stops and tears clothing before anything else, one intent held at a time, and a fast trial loop that compares three deciders against the current planner in many short scored sessions before one composition is hardened.

**Architecture:** three layers with one owner each (spec § 2): the decider (a variant package under `testing/agent/base/planner/`, forked by `Survive(control=...)` at the top of `assess`, the ladder the default and the control arm), the plays (shared executors: the meet, the finish, the spent meet, the dress, the walks, over the Lua reflex `PZAgent_StanceMelee.lua` under PZA/1.10), and the model (strategic by default; the tactician variant tests the alternative). The trial loop (spec § 4 item 5): two fixtures made by the game's own RCON commands, a generic driver booted from a `git archive` snapshot with the main tree's fixture caches, a scripted scorecard appending to a tracked trials log, five-minute loops inside one foreground call.

**Tech Stack:** Python 3 (pytest, the fakes, lupa for the Lua tests and the decision-golden replays), Kahlua Lua (`kahlua_lint.py`, `luabalance.py`), `tools/pza_schema.py`, RCON through `xlib`'s `xs.rcon`, the `claude` CLI for the LLM source, the register tools (`claims_check.py`, `claims_delta.py`, `page_lint.py`, `reference_gen.py`), `git archive` and `git worktree`.

**Spec:** `docs/superpowers/specs/2026-11-05-plan-31-the-rebuild-design.md` (§ 0 the directions, § 1 the readings, § 2 the architecture, § 3 the variants, § 4 Phase 0, § 5 Explore, § 6 the jar reads, § 7 Harden, § 8 the measures, § 9 the risks, § 10 what the plan settles).

## Global Constraints

- CLAUDE.md §§ 3, 4, 5, 6 in full at the plan's commit: pathspec commits, no `--amend`, the gates, the machine-safety rules on every boot (doctor, the one-client floor of 10 GB available read and ledgered with the Java working sets in every memory row, one live session at a time, Angus's own client never touched, no OS cursor, a console shown or minimized, a detached launch only past the ten-minute cap and only after Angus approves it), ledger times read off the clock, briefs on disk before dispatch, every dispatch naming its model, the no-429 rule before an LLM boot.
- **Ruling P31-T (Task 0):** a trial is not evidence. A trial run stays in `testing/runs/`, is never auto-copied into `testing/artifacts/`, and only `testing/trials/trials.md` is tracked; no row, page or brief cites a trial; the evidence rules (a driver never edited after its run, a frozen grade per artifact, the artifact commit with its do-not-cite rows, the visual pass by a reviewer, the write-up and the mint, the quiescent tree) apply to Harden's evidence sessions and to no trial; a trial may boot from a snapshot of any commit or branch head while the main tree changes; a planner-package lane may run in a worktree. Every wound in a trial is traced to the press or leg before it in the trial's three lines.
- The Lua reflex and the PZA schema are frozen for Explore once Task 2 lands (PZA/1.10); a variant that needs a Lua change names it in its trial row and waits for Harden.
- The decision goldens (`testing/tests/pzagent/test_replay_decisions.py`) stay byte-identical with `control="ladder"` (the fork adds no field to the ladder's decision line); a variant's own goldens are its own files.
- No `mod/` edit; no JDK; no API key in the tree or environment; the model sees game state only; the sprint is never sent; the jar toolchain at `C:\Users\Angus\pz-b42` is read-only; the install under `D:\SteamLibrary` is read-only.
- The metrics are kills and hits per kill (the frames' reaction runs and the union with the reflex's `hit` steps, both stated); a trial row carries both, the minutes fleeing or retreating, the minutes toward a named target, the wounds dressed within one game minute, the melees superseded before their swing, the end and the health at the end.
- Models: opus for the reflex, the variants, the scorecard's readers, every review of evidence and the whole-pass review; sonnet for a task whose code the brief spells out (the fork, the environment paths, the probe library, the snapshot tool, a root-file edit) and scoped re-reviews.

---

## Phase 0: what every variant needs

### Task 0: Ruling P31-T and the trials log's home

**Files:** modify `CLAUDE.md` § 5 (one bullet, **Trials**, the ruling's text of the Global Constraints) and § 6 (the lanes bullet: a planner-package lane may run in a worktree during Explore); modify `docs/process/lessons.md` (the story under `#live-runs`: why a trial is not evidence, F15's three hours of process for ten minutes of play, Angus's direction of 2026-11-05); create `testing/trials/trials.md` (the table's header row: `trial | variant | commit | fixture | minutes | kills | hits (runs / union) | hits per kill | min fleeing | min toward target | dressed <1 min | melees superseded | end | health | seen`).

- [ ] Write the three edits; `python tools/page_lint.py docs/process/lessons.md` 0; `python tools/claims_check.py --staged` 0.
- [ ] Commit: `Plan 31 Task 0: ruling P31-T, a trial is not evidence (CLAUDE.md § 5 and § 6, the lessons story, testing/trials/trials.md)`.

The controller makes this edit itself (a root-file edit); its review is the whole-pass review.

### Task 1: The `control=` fork

**Files:** modify `testing/agent/base/planner/survive.py` (`Survive.__init__(…, control="ladder")`; `assess` dispatches: `ladder` runs today's body moved verbatim into `_assess_ladder`, any other name resolves a package `planner.<control>` exposing `assess(survive, frame) -> Decision`); create `testing/agent/base/planner/control.py` (`CONTROLS`, `load(name)` by `importlib`, a `ControlError` for an unknown name); create `testing/tests/pzagent/test_control.py`.

**Interfaces:** produces `Survive(control=name)`; a variant package exposes `assess(survive, frame)` returning the same `Decision` `_apply` takes today, and may keep its own state on `survive.control_state`.

- [ ] Tests first: an unknown name raises `ControlError` at construction; `control="ladder"` leaves every golden byte-identical (the six `survive-decisions-*.json` replays pass unchanged); a stub package registered in the test returns a `Decision` and `_apply` sends it.
- [ ] Implement; the ladder body moved, not rewritten; the lane tests and the six goldens green.
- [ ] Commit: `Plan 31 Task 1: the Survive(control=...) fork, the ladder the default and the by-name variant loader`.

### Task 2: The meet, the finish and the spent meet (the reflex, PZA/1.10)

**Files:** modify `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_StanceMelee.lua` (the melee's new phases), `PZAgent_Sense.lua` (two frame fields: `me.bodyAngle`, the body's actual forward angle from the Java getter the jar review names for J5; each fallen zombie's `headX`/`headY` or `proneDir`, from the bone position the floor-attack test reads for J1), `testing/agent/base/schema/pza1.json` (the fields, `PZA.VERSION` 1.10, the melee's new arguments and act leaves) with `python tools/pza_schema.py --write`; modify `testing/agent/base/planner/maneuvers/melee.py` and `dispatch.py` (the new arguments; the `closeR` press replaced); modify `testing/agent/base/actions.py`; tests under `testing/tests/pzagent/` (the Lua under lupa with the fake player, the maneuver's offline cases).

**The behaviour** (spec § 4 items 1, 2 and 2b; the constants from the jar rows of Task 9, read from `docs/platform/agent.md` once minted, never from memory):
- **The meet.** From `FACE_R` (about 3 tiles) the facing is written to the target every tick. The press waits until `|bodyAngle − bearing| ≤ PRESS_ANGLE` (J5) and the predicted distance at the collision, `d − v·t_c` with `v` the closing rate over the last three ticks and `t_c = 0.25 / combatSpeed` plus one update, is inside `[PRESS_LO, reach]`, the press itself made beyond the bat's `MinRange` (J2: inside it the press is a shove). An idle zombie is walked to in the stance and pressed at the reach. After a press: no back step and no pause; knocked down → the finish; lowered → press again as the swing ends; did nothing → press again while the angle holds (J4: a player mid-attack facing the zombie within 45 degrees is never bitten; J3: a landed hit cancels its attack). A `shove` only when the zombie is inside `MinRange` at the press.
- **The finish.** The facing is pointed at the fallen zombie's head (J1) and the floor swing pressed within the bat's floor reach, else the stomp within 0.3 tiles; repeated until `zombie_dead`, with no time end; a standing zombie inside `HANDBACK_R` (2 tiles) hands back to the meet, and a standing zombie beyond it never breaks the finish.
- **The spent meet.** With the arms' pain over 10 or the endurance or tired moodle at 2 (read from the frame's body and moodles), the meet is shove then stomp (the stomp is not divided by the arms' pain, #4370).
- **The press log.** Each press's act leaf: `{d_press, d_collide_pred, body_angle_off, hp0, hp1, knock, cut_by}` (`cut_by` the hit reaction or supersession that ended the clip early, else empty).
- **Nothing ends on time.** The melee ends `kill`, `handback`, `lost` (the target unreachable or gone) or `superseded`; the planner's `done time` end goes.

- [ ] Tests first (lupa): the facing written from `FACE_R`; no press while the body angle is off; the press at the predicted band and not at the raw distance; a press that did nothing followed by a press, never a back step; the finish aimed at the head position and never broken by a zombie beyond `HANDBACK_R`; the spent meet's shove and stomp; the press leaf's seven keys. Offline cases for the maneuver's new arguments and the acts' parse.
- [ ] Implement; `python tools/luabalance.py` green (HEAD copies first, then the tree), `python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit testing/PZAgent` 0, `pza_schema.py --check` and `bus_inventory.py --check` in sync; a bench of the reflex's per-tick cost before and after (the hot-path rule).
- [ ] Commit: `Plan 31 Task 2: the meet, the finish aimed at the head and the spent meet (PZA/1.10: the body angle and the fallen head in the frame, the press log, no back step, no time end)`. The Lua and the schema are frozen for Explore from this commit.

### Task 3: The environment paths

**Files:** modify `testing/pzt/paths.py` (`PZT_FIXTURES` and `PZT_RUNS` read from the environment with today's defaults); create `testing/tests/test_paths.py`.

- [ ] Tests first: the defaults unchanged with the variables unset; each variable honoured when set.
- [ ] Implement; commit: `Plan 31 Task 3: pzt's fixture and run roots read from PZT_FIXTURES and PZT_RUNS`.

### Task 4: The probe library

**Files:** create `testing/agent/driverlib/probe.py` (`claude_available`, `probe_argv`, `claude_answers` lifted from the frozen `testing/agent/drivers/f_goals_16.py` lines 92 to 163, the frozen driver untouched); create `testing/tests/pzagent/test_probe.py` (the frozen driver's own tests of those three functions copied against the library).

- [ ] Commit: `Plan 31 Task 4: the claude -p probe lifted into driverlib/probe.py`.

### Task 5: The snapshot tool

**Files:** create `tools/trial_snapshot.py` (`python tools/trial_snapshot.py <commit-or-WORKTREE> [--root <scratch>]`: `git archive` of the commit, or the working tree with its diff applied, into `<root>/<sha>/`, one tree per sha reused when present; writes `TRIAL_STAMP.json` {commit, dirty, diff_sha256, made_at}; prints the launch line with `PZT_FIXTURES` and `PZT_RUNS` pointing at the main tree); create `tools/tests/test_trial_snapshot.py` (git under `tools/tests/gitenv.scrubbed_env`).

- [ ] Tests first: a clean commit's tree matches `git archive`; a dirty tree's stamp carries `dirty` true and the diff's hash; a second call reuses the tree; the launch line names both roots.
- [ ] Commit: `Plan 31 Task 5: trial_snapshot.py, a trial's tree from a commit or the working tree with its stamp`.

### Task 6: The trial driver

**Files:** create `testing/agent/drivers/x_trial.py` (`--variant <name> --fixture <name> [--minutes N, default 5] [--no-llm] [--waves <plan>] [--teleport X,Y] [--make-fixture <name>]`; refuses any other argument, tested statically); create `testing/agent/driverlib/trial.py` (the boot through `day.boot_and_run` without `copy_run` and without the chain's next steps; `trial.json` written at the run's root: the variant, the switch values, the commit or `TRIAL_STAMP.json`'s content, the fixture, the minutes, the wave plan; the pre-boot checks offline against the staged copy and a real run layout, the `claude -p` probe only without `--no-llm`; the wave thread sending `createhorde2` over `xs.rcon` at the square computed from the character's position plus each wave's distance and bearing, the plans `lone` (one zombie at 8 tiles every 60 s), `pair` (two at 8 tiles, 70 degrees apart, every 90 s), `street` (none); `--teleport` sends `teleportto "admin" X,Y,0` over RCON before the loop and `--make-fixture` tears down and runs `pzt snapshot --from-run <run> <name>`); create `testing/tests/pzagent/test_x_trial.py`.

**Interfaces:** consumes `Survive(control=…)` (Task 1), `driverlib/probe.py` (Task 4), the paths (Task 3); produces the run folder with `trial.json` for Task 7.

- [ ] Tests first: the static refusal; `trial.json`'s keys; the wave squares at a bearing; the probe skipped under `--no-llm`; no auto-copy into `testing/artifacts/`; the fixture-making path's commands in order against the fake RCON.
- [ ] Commit: `Plan 31 Task 6: x_trial.py, the generic trial driver with waves, the teleport and the fixture snapshot`.

### Task 7: The scorecard and the trials log

**Files:** create `tools/trial_score.py` (`python tools/trial_score.py <run> [--seen "…"] [--rescore-all]`: reads `trial.json`, the record, `decision.log`, the state log and `goals.log` through `agent.base.replay_decisions.read_record`/`align` and the live readers imported from `agent.base.grades.f12` and `e21` (the union hits, the kills matched to the events, the standing minutes, the melee reader); adds four readings: the minutes fleeing or retreating (lines whose action is a flee, retreat or avoid leg), the minutes moving toward a named target (lines under a goal or play with a target label whose distance to it falls), the wounds dressed within one game minute of the first bleeding frame (by part), the melees superseded before their swing; prints the row and appends it to `testing/trials/trials.md`; `--rescore-all` rebuilds the table from every run folder under `testing/runs/x_trial-*`); create `tools/tests/test_trial_score.py` (one failing case per reading against F15's committed artifact and a synthetic ring per new reading).

- [ ] Tests first; implement; commit: `Plan 31 Task 7: trial_score.py and the trials log`.

### Task 8: The dress maneuver

**Files:** create `testing/agent/base/planner/maneuvers/dress.py` (`Dress(part)`: stop (a `stop` command and a wait for `me.moving` false), the held bandage or rag first, else `unwear` the outer cotton garment, `rip`, then `bandage` the part with the rag; an unwashed rag accepted while bleeding; ends `done` when the part's `bleeding` clears, `failed` with nothing to tear, `superseded` only by a standing zombie within `KEEP_R`; an upper-body part may ride a walk when the planner asks); modify `care.py` (the item choice exposed as a function the maneuver calls) and `dispatch.py` (the maneuver registered); tests under `testing/tests/pzagent/`.

**Interfaces:** produces `maneuvers.Dress` for every variant and for the ladder's care branch behind the switch `DRESS_MANEUVER` (off for the ladder's goldens).

- [ ] Tests first: the stop before the unwear (F15's nine `moving` refusals); the rip when no dressing is held; the end on the part's `bleeding` false; superseded only inside `KEEP_R`.
- [ ] Commit: `Plan 31 Task 8: the Dress maneuver, stop, tear and bandage as one commitment`.

### Task 9: The jar rows T97

The controller mints the 14 claims of `jar-read-swing.md` as corrected by `review-jar-read-swing.md` (FAIL rows dropped, FIX rows corrected, claim 9 requoted without inner double quotes) on `docs/platform/agent.md` beside the combat mechanics, the owner sentences written by the controller from the review's wording, under `tools/claims_delta.py`; the staged checker 0, the full checker 0, `cited-by` in sync.

- [ ] Commit: `Plan 31: the swing jar read's rows (T97 -> #…: the hit location and the head, the collision's re-check, the knock-down and the stagger, the zombie's attack, the turn, windows and fences)`.

### Task 10: The fixtures and the smoke trials (live)

**Files:** `testing/fixtures/arena-east/fixture.json` and `testing/fixtures/street-1/fixture.json` (tracked; the caches gitignored); the first two rows of `testing/trials/trials.md`.

- [ ] Boot 1 (under § 5): `x_trial.py --variant ladder --fixture agent --no-llm --teleport <X,Y> --make-fixture arena-east --minutes 1`, the square about 15 tiles from (10764, 10618) chosen off F15's map in the brief; the RCON reply to `teleportto` read and ledgered.
- [ ] Boot 2: the same for `street-1` beside a row of unlooted houses named in the brief.
- [ ] Boot 3: `x_trial.py --variant ladder --fixture arena-east --no-llm --waves lone` for five minutes; `createhorde2`'s spawn confirmed at the bearing; the scorecard's row appended with three lines of what was seen.
- [ ] Boot 4: `x_trial.py --variant ladder --fixture street-1 --minutes 5` with the model; the row appended.
- [ ] Commit the two fixtures and the two rows: `Plan 31 Task 10: the arena-east and street-1 fixtures and the ladder's two smoke trials`.

A failure of either RCON form is fixed in the driver as a pre-run edit named in the commit (a trial driver is not frozen) and the boot repeated.

---

## Explore

### Task 11: The three variants, in parallel worktrees

Three implementers (opus), each in its own worktree on a branch `p31/<variant>`, each reading its proposal and spec § 3, each delivering a package, its tests and its own decision goldens, and never touching the Lua, the schema, `survive.py`, `dispatch.py` or another package:

- **D, `planner/doctrine/`** (`rebuild-proposal-intent-machine.md`, `rebuild-proposal-combat-doctrine.md`): `arbiter.py` (the six priorities in order, the one-deep resume slot, the decision line `{intent, p, why, state, preempted_by, resumed}`), `intents.py` (Strike, Fight, Dress, Avoid, Door, Loot, Travel, Stock, Rest, each with `done`, `failed`, `maneuver`), `constants.py` (GROUP_N, GROUP_R, GROUP_CLEAR_R, ENGAGE_R, STALL_S, each with its source). Fight runs the meet and the finish of Task 2; Dress runs Task 8; Avoid walks at a run to a named refuge from `night.exits`/`policies.exit_plan` and sneaks once out of sight; Door decides once on arrival; the standing order is the goal walks with the model prefetched during a Loot.
- **U, `planner/utility/`** (`rebuild-proposal-situation-utility.md`): `features.py`, `acts.py` (the generators), `models.py` (λ_hit and P_kill fitted on the committed rings with their n and ±5 % probes reported), `weights.py` (a dial registry), `select.py` (the scores, the commitment margin and spans, the five interrupts, the decision line's `scores`, `runner_up`, `margin`, `held_by`); the verdict set and the linear program under `tools/utility_fit.py` with its compact artifact under `data/fits/`.
- **T, `planner/tactician/`** (`rebuild-proposal-model-tactician.md`): `plays.py`, `trigger.py`, `tview.py`, `fallback.py` (Angus's rules as a table), `table.py` (the cached table), `source.py` (the triggered `claude -p` call, one in flight, coalesced, validated late), `schema/plays.json`, `plays.log`; and **the offline bench first**: `tools/tactician_bench.py` over 200 recorded trigger views from F2 to F15 and E19 to E23, scoring the table and two model configurations (`--model haiku`, the default) on validity, rubric violations, self-agreement and latency. If the table ties the model on 95 % or more of the views with no more violations, T's trials run the table and the result is written in the trials log's seen column.

Each variant's `assess` returns the shared `Decision`; each carries a `README.md` naming what it drops of the ladder and why. The controller cherry-picks each branch to `main` after its review (`git show <c> | git apply` where the intent-to-add entries refuse the pick), or trials boot from the branch head by the snapshot tool.

- [ ] Per variant: the offline tests green, one review (opus), one fix round, the merge or the branch head named for its trials.

### Task 12: Round one, twelve trials

For each of D, U, T and L: two `arena-east` trials with `--no-llm --waves lone` and `--waves pair`, and one `street-1` trial with the model (T's street trial is its model or its table per the bench). Each boot under § 5's machine-safety rules; each row appended by the scorecard with three lines of what was seen, every wound traced to the press or leg before it. The ledger ticks each trial off a twelve-row table.

- [ ] Commit the rows after each pair of trials: `Plan 31 Task 12: trials <n>-<m> (<variants>)`.

### Task 13: The composition

One read (opus) across the twelve rows and their run folders names what worked in each variant (a decider, a play, a constant, a view) and proposes one or two compositions, each behind its own package `planner/mix_<n>/` built by an implementer from the existing packages' parts; a composition that differs from a variant by a constant alone is refused.

- [ ] The read, the build, one review; the packages merged or their branch heads named.

### Task 14: Round two

The compositions and the round's best variant, two arena trials and one street trial each; the rows appended; a ranking written at the end of `testing/trials/trials.md` by kills, hits per kill, the minutes fleeing and the minutes toward a target.

- [ ] Commit: `Plan 31 Task 14: round two and the ranking`.

---

## Harden

### Task 15: The composition's full treatment

The best composition by the ranking: its package made the default of `Survive(control=…)` behind a named switch, its tests completed, a grade module `grades/x1.py` (the trial's readings plus the evidence readings, every live name copied, P26-Q), two drivers (`e_day_25.py`, `f_goals_17.py`) with their tests, and two evidence sessions under the full § 5 with their artifacts, visual passes, write-ups and rows (T98, T99). If the composition beats the ladder across the trials and the sessions, the ladder's path and its pinned tests are deleted by name in the task report and the six old goldens retired with their rows pinned; if not, the report says so and the ladder stays the default.

### Task 16: The close

The whole-pass review, one fix wave and its re-review; the report `docs/superpowers/specs/<date>-plan-31-the-rebuild-report.md` (the trials table, the sessions table with kills, hits and hits per kill, the rulings, what the next plan takes); HISTORY.md; CLAUDE.md §§ 1 and 3; the lessons stories; the full repository pytest from a saved file; the memory files; the push.
