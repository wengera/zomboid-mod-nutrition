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

