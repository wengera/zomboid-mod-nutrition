# Plan 24: the group — design

Angus (2026-10-28, standing): the design strives for a character that fully plays and survives the game, scripted instincts for its reflexes and LLM-driven actions for its broader decisions; no design-approval round; the minutiae are Claude's to explore, prototype, iterate and improve; every boot under CLAUDE.md § 5. Angus (2026-10-29): "keep going, boot F1 when ready" — read as the next LLM session (F2) on the next planner base.

## 1. Goal

A chain that lives past one session. Plan 23's close report (`2026-10-28-plan-23-survivor-report.md` § 7) names why none did: four of six survival deaths came with a group gathering on the character while a fight or a corner held it in place, and the first limit is perception — the group was listed at the 12-tile edge while the threat branch counted within 6 (#4268). The close review (`.superpowers/sdd/2026-10-28-plan-23-survivor/review-close.md`) adds four planner findings from F1's log: a `walk` corner overrides the `health` flee, the point-blank re-pin alternates between two zombies, an approach walk is sent at point blank, and the group steer runs on a room square with a way out.

## 2. Principles (Plan 23's hold)

Instincts before goals; the planner host-side, no per-tick server work from the agent; every grade versioned per pass; a driver frozen from its run, the next pass a new file; every live reading a row with its artifact; a brief's trace of a live log is a hypothesis the writer verifies (CLAUDE.md § 6). New here: **a decision golden** — before any rule or refactor of the threat plan, `Survive`'s decisions over the recorded inputs of the E5 and F1 artifacts are recorded as a golden (`testing/tests/pzagent/golden/survive-decisions-*.json`), and every later change to the plan re-records it under a named change with each moved decision attributed (CLAUDE.md § 6's golden-trace rule applied to the planner).

## 3. The work

1. **The decision golden** (Task 1): a replay harness `testing/agent/base/replay_decisions.py` that runs one `Survive` over an artifact's recorded inputs (the state log through `World.apply`, the decision log's inputs) and emits the decisions by tick; the goldens for E5 and F1 recorded at the base before any change; a test that reproduces them byte for byte.
2. **Survival iteration 5, the group** (Task 2, ruling P24-A): (a) the threat read counts the whole listing (12 tiles) with a short threat memory (`World.met`: the squares where zombies were listed in the last `MET_TTL_MIN` game minutes, and the count of the densest 10-tile window), and the `many` reason fires on four or more listed within 12 whatever the count within 6; (b) a fight refuses to approach a zombie with others listed behind it (any held threat within the 20° cone beyond the target within 12 tiles ends the approach: the flee instead); (c) a `walk` corner yields to the `health` and `unarmed` reasons and to a running `many` episode when the last leg is not stuck (`stuck` and trapped corners keep the override); (d) the point-blank re-pin only when the pin itself is beyond point blank (hysteresis); (e) no approach walk at point blank; (f) inside with a way out, a group takes the exit walk at a sprint, never the steer; (g) `corner_kind` logged beside the corner's id; the breach test once per tick; `EXIT_STALL_S` and `STEP_STALL_S` one constant; `CORNERED_R`'s two quantities split; provenance comments on `CORNER_FREE_R`, `CLOSING_TICKS`, `SPRINT_MAX_S`. Each rule a test and a mutant; the goldens re-recorded under the named change with the moved decisions attributed.
3. **The goal sources avoid met ground** (Task 3, P24-B): the view carries `met` (the memory's dense squares and their bearing); the scripted edge choice and the LLM's system prompt prefer squares away from the densest window; the LLM view gains positions (the player's square, the buildings' squares) and the failure meanings the F1 write-up found missing (#4279).
4. **F2** (Task 4): `f_goals_2.py`, a copy of `f_goals.py` under its own key on the new base; the boot under § 5; the write-up with rows.
5. **E6** (Task 5): `e_day_6.py`; the boot; on a day-cap survival `pzt snapshot` to `agent-s1` and session 2 (`--session 2 --fixture agent-s1 --prev`), the chain's first second session; the write-up.
6. **The jar reads** (Task 6, research, parallel): the pathfinder's edge rules against `isBlockedTo` (the fence climb: #4261, #4269); the server's death cause for a one-step fall (#4252, #4272: `IsoPlayer` death/knockdown paths, `BodyDamage`); the melee swing's start conditions (the hit-interrupts-swing inference: #4210, #4262, #4271, #4285). Notes under `docs/superpowers/specs/2026-10-29-plan-24-jar-reads.md`, claims where a reading settles a thread.
7. **The refactors** (Task 7, after the golden and the sessions): A a `Corner` state and a pure ordered `assess()` logged by rule name; B `Flee` split into a shelter run, an exit run and a steer leg over one walk tracker; C one per-tick threat snapshot shared by the decision and the policies; each proven by the goldens unmoved.
8. **The close** (Task 8): the report, the rows, CLAUDE.md, HISTORY, the memory files, the push.

## 4. Sessions

Nine at most, one at a time, each under § 5: F2 and E6 (its chain up to three sessions) are the acceptance; the rest are spares for a re-boot or a second F.

## 5. Out of scope

The night and the needs stay unread unless a chain reaches them; the Lua's melee skill is not changed before the jar read says why swings do not start; no migration or compatibility work.
