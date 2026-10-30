# Plan 24: the group — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a chain that lives past one session: the threat instinct sees the group before it fights, the goal sources keep the character off met ground, and the next LLM session and chain read it live.

**Architecture:** the Python planner under `testing/agent/base/planner/` (`survive.py`'s threat plan, `policies.py`'s Fight and Flee, `goals.py`'s sources, `view.py`), `world.py` gaining the threat memory, a decision golden as the oracle for every change, the drivers as per-session copies, the write-ups minting rows.

**Tech Stack:** Python 3 (pytest, the offline fakes and replays), the PZA/1.3 Lua unchanged, the `claude` CLI for the LLM source.

**Spec:** `docs/superpowers/specs/2026-10-29-plan-24-the-group-design.md`.

## Global Constraints

- CLAUDE.md §§ 3, 5, 6 in full: pathspec commits, no `--amend`, the gates, one live session at a time under § 5 (doctor, ≥ 12 GB free read and ledgered, a quiescent tree, a detached launch polled in foreground), a driver never edited after its run, grades versioned per pass, no compatibility fallback, Kahlua rules for any Lua.
- The decision golden (spec § 2): recorded before any change to the threat plan; re-recorded only under a named change with each moved decision attributed in the task's report.
- A write-up brief's trace is a hypothesis the writer verifies (CLAUDE.md § 6); the writer's corrections replace the controller's row.
- Sessions: nine at most (spec § 4).

---

### Task 1: The decision golden
**Files:** create `testing/agent/base/replay_decisions.py`, `testing/tests/pzagent/test_replay_decisions.py`, `testing/tests/pzagent/golden/survive-decisions-e5.json`, `survive-decisions-f1.json`.
- [ ] `replay_decisions.run(artifact_dir) -> list[dict]`: one `Survive(source=ScriptedSource())` over the artifact's recorded inputs (`state.log` through `FileTransport` and `World.apply` in file order; the decision log's `inputs` per planner tick as the tick's inputs where the World cannot reproduce them), emitting per tick `{line, gameMin, branch, action {type, args}, why}`; the LLM source replaced by the scripted stand-in for F1 (the recorded goals are not replayed: the goal branch's decisions are excluded from the golden, the threat branch's included).
- [ ] The goldens recorded at HEAD for `testing/artifacts/e_day_5-20261028-201255/` and `f_goals-20261028-202437/`; the test reproduces each byte for byte; a mutation test shows a changed `CORNERED_R` moves the golden.
- [ ] Commit `Plan 24: the Survive decision golden over E5 and F1 (replay_decisions.py)`.

### Task 2: Survival iteration 5, the group (P24-A)
**Files:** modify `survive.py`, `policies.py`, `world.py`, `view.py` (the log fields), tests.
- [ ] The spec § 3.2's rules (a)–(g), each RED then GREEN with a mutant; the goldens re-recorded under the named change, every moved decision attributed in the report.
- [ ] Commits `Plan 24 survival 5: <what> (P24-A)`.

### Task 3: The goal sources avoid met ground (P24-B)
**Files:** modify `goals.py`, `view.py`, `llm.py` (the system prompt), tests.
- [ ] The view's `met`; the scripted edge choice away from the densest window; the LLM view's positions and failure meanings; tests; the goldens unmoved (the goal branch excluded).
- [ ] Commit `Plan 24: the goal sources avoid met ground; the LLM view's positions and failure meanings (P24-B)`.

### Task 4: F2
- [ ] `f_goals_2.py` (a copy of `f_goals.py` under its own key, the base named); the boot (controller); the write-up (opus writer); the rows minted.

### Task 5: E6
- [ ] `e_day_6.py`; the boot; on a day-cap survival the snapshot to `agent-s1` and session 2; the write-ups; the rows.

### Task 6: The jar reads (research, parallel to Tasks 1–3)
- [ ] `docs/superpowers/specs/2026-10-29-plan-24-jar-reads.md`: the pathfinder's edge rules against `isBlockedTo`; the server's death cause for a one-step fall; the melee swing's start conditions; claims where a reading settles a thread.

### Task 7: The refactors (A, B, C) after the sessions, each proven by the goldens unmoved.

### Task 8: The close
- [ ] The report `docs/superpowers/specs/2026-10-29-plan-24-the-group-report.md`, the rows, CLAUDE.md, HISTORY, the memory files, the full pytest saved and read, the push.

### Task 6b: The jar reads for the stance, the climb, the bandage, the rip, the wash and the look (research, parallel)
- [ ] The note `docs/superpowers/specs/2026-10-29-plan-24-jar-reads-2.md`; claims where a reading settles a thread; the proposed PZA/1.5 actions.

### Task 9: PZA/1.5 — aim, climb, bandage, rip, wash, look (the Lua)
- [ ] The schema, the skills, the frames' fields, the tests; the goldens re-recorded under the named change if the decoder moves them.

### Task 10: The stance fight, the care branch, the look-around (P24-G)
- [ ] The Fight's standing and backpedal rules; the `care` branch; the look-around; the climb in routes; tests and mutants; the decision goldens re-recorded with the moved decisions attributed.

### Task 11: F3 and the E6 chain on the new base
- [ ] The driver copies; the boots; the write-ups; the rows.

### Task 12: Survival iteration 7 — the stance opens the fight, the backpedal inside KEEP_R, no sprint, the bandage under a far threat (P24-N/O/P)
- [ ] The planner rules, tests, mutants; the goldens re-recorded under the named causes; then the E6 write-up and the seventh chain.

### Task 18: Survival iteration 8 — the fight sought, every walk a destination, the stuck door (P24-X/Y/Z)
- [ ] The planner rules, tests, mutants, goldens; then the E7 and probe write-ups and the eighth chain.

### Task 25: Jar reads 3 — muscle strain, the shove and stomp, the client's loaded window, the unwear
- [x] §§ 11–14 of the note; rows #4368–#4377 (868b5dd2).

### Task 26: Faster iteration loops — the suite's durations and the safe speed-ups
- [ ] The durations, the shared fixtures and caches, the slow marker, the loop analysis.

### Task 27: Survival iteration 10 — strain-aware fighting, the shove and the stomp, the loaded-window legs, unwear then rip (P24-AG/AH/AI/AJ)
- [ ] After PZA/1.7 (Task 9 fix 11); then the ninth chain's boot on it and the write-ups.

### Run sheet: Tasks 24 and 28–40 (from the ledger, at the close)

These tasks were briefed from the workspace and spec § 6 items 20–27 and never given a header above; each row names its subject and its commits.

| Task | Subject | Commits |
|---|---|---|
| 24 | The clothing and window round: the clothing record and `me.worn` in the World, the wear rule, the window past a stuck door, the clothing loot capped (fix 1) | `4ce95246`, `697ee0df`, `b11f1dc2`; re-anchors `947e66ac`, `8d874a75` |
| 28 | Notes from 22 written combat and survival guides mapped onto the planner's rules and the jar rows | `10daa32f` |
| 29 | The guides' strategy lines in the goal source's SYSTEM, the view keys they read, the bag and weapon wants (fix 1 reworded the lines and removed the bag want) | `bed744cb`, `0eb3660e`, `5338b2c7`; re-anchors `f09aeb3c`, `40729b35` |
| 30 | E9 write-up (the ninth chain's first session; artifact `abe2c52c`) | `434543ac` |
| 31 | The shot taker's window-content grab through `PrintWindow` when the guard refuses the screen (P24-AM; fix 1 sized by the window rect) | `f800b8a4`, `73f5ae42` |
| 32 | Survival iteration 11: the pull and the transparent solid, the doorway stand, the wounded fight and the fallen target, the care tick inside a long flee (P24-AN to P24-AS); fix 1 and fix 2 | `ae18c22a`, `89943cbb`, `d4639a31`, `45e099ea`; fix 1 `7eac71ab`, `a5c3c5d2`, `a7156b46`; fix 2 `6f13037c` |
| 33 | `grade_e7` and the tenth chain's driver `e_day_10.py` | `33c74fbc`, `4ba05b6d` |
| 34 | E10 write-up (the tenth chain's first session; artifact `48a56f5e`) | `c81c5202` |
| 35 | `grade_f5` and the LLM session's driver `f_goals_4.py` on the strategy prompt | `db7cd527`, `511e3efa` |
| 36 | Survival iteration 12: the pure move into `fight.py`, `flee.py` and `threat.py`, then P24-AT to P24-AY; fix 1 | `5bfbfff7`, `e1ecbd22`, `b2c49d96`, `1ad44f79`, `eaa1c9a3`, `da9af9b9`, `411dfc0e`; fix 1 `5e3ad986` |
| 37 | `grade_e8` and the eleventh chain's driver `e_day_11.py`; fix 1 | `4062cfd7`, `1d664ca9`; fix 1 `841343f3` |
| 38 | E11 write-up (the eleventh chain's first session; artifact `d0390058`) | `05e5c9c1` |
| 39 | F3 write-up (the third LLM goals session; artifact `8bc77fc4`) | `ee6352fa` |
| 40 | The kill count: `loop.results` keeps the shove and stomp results, `grade_e9` reads the kills off the act lines and the `zombie_dead` events | `9c3639f3`, `36950075` |
