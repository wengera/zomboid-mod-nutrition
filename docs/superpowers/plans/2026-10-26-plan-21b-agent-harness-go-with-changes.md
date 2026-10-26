# Plan 21b — the agent harness, the go-with-changes passes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the three changes the Plan 21 report's § 6 recommends (grade the tick on the 60 Hz mean; emit the scan in 20-square parts; grade motion as ack → first position change) in one Stage A pass 4 boot, then the built-but-unrun Stage B and Stage C sessions, and amend the report with their numbers.

**Architecture:** The same pipe (PZAgent, a pure-Lua client mod streaming JSON lines to files; `testing/agent/` reading them and sending goals). Pass 4 is a new driver `a_pipe_4.py` on the frozen chain and a new versioned gate `gate_a4`; Stage B runs `b_actions.py` and Stage C `c_survive.py` as committed, after the two parked must-fix items land. Every run lands as a byte-identical artifact with a guide, a register row and do-not-cite rows; the report takes a dated § 7.

**Tech Stack:** Kahlua (Lua 5.1 dialect) under lupa 5.1 for the offline tests; Python 3 (`pytest`); the harness `testing/pzt` (doctor, provision, run); detached `Start-Process` launches polled through the persisted artifact.

**Spec:** `docs/superpowers/specs/2026-10-26-agent-harness-design.md` (§ 4 the loop and gates; § 4.4 the report), as amended by the report `docs/superpowers/specs/2026-10-26-agent-harness-report.md` § 6 (the three changes), which Angus adopted with the order "run the go-with-changes boot" on 2026-10-26.

## Global Constraints

- Spec § 4: every pass is build → offline tests green → doctor and memory gate → boot → measure → verdict → ledger line; no gate is relaxed to pass. Stage A's 3-pass budget was spent; pass 4 is the one extra pass Angus ordered, graded by `gate_a4` (ruling P21b-0 below).
- Spec § 4.1 gates as amended by the report § 6: tick `tick_mean_ms_at60 < 1 ms` (the 5 Hz p99 reported ungraded beside it); 15-tile scan per-tick cost `< 5 ms`; cmd → first position change `< 500 ms` p90 over at least 20 unvoided legs; gaps 0; client Lua errors 0; hello mode append or chunk.
- Spec § 4.2 gates (Stage B): sequences completed ≥ 4 of 5; failures with a reason from the closed set 100 %; eat seen by the server 5 of 5. Budget 4 passes. Spec § 4.3 (Stage C): no gate; stop conditions; budget 3 runs; the dense run only if the first survived.
- CLAUDE.md § 5 binds every boot: `python testing/pzt doctor` first; one live session repository-wide; never `-safemode`; ≥ 12 GB host memory free, read and ledgered; detached launches by the controller, polled across foreground calls; a driver is never edited after its run; a gate function whose output an artifact carries is versioned per pass, never edited (`gate_a`, `gate_a4`); a grade script with committed output is frozen (`a_grade.py` → `a_grade_4.py`); a world-generation sandbox value is set by provisioning a fixture, never by a profile.
- CLAUDE.md § 6: pathspec commits only; no `--amend`; no Claude attribution; implementers never push; no subagent runs `git stash`, `checkout --`, `reset`, `restore`, `add -N`, `add -f` or any index-wide command; page writers never edit `docs/reference/claims.tsv` (a delta file the controller applies); the frozen drivers `a_pipe.py`, `a_pipe_2.py`, `a_pipe_3.py` and every committed artifact JSON, `state.log` and `a_grade.txt` are never edited.
- Kahlua rules for every PZAgent Lua file: no `goto`, no `%d` on floats, no `#` on Java lists, no `%g` of a value that can be tiny; every Java member reached through `PZA.call`/`PZA.field` except `getX`/`getY`/`getZ` and nil-checked file handles; a vanilla Lua class or function is index-checked (`X ~= nil and X.new ~= nil`) before it is called, never trusted to `pcall` alone (#0957: a caught raise still parks a `-debug` client).
- Lints before any Lua commit: `python tools/kahlua_lint.py testing/PZAgent` 0, `python tools/luabalance.py <each touched .lua>` green, `python tools/mod_lint.py testing/PZAgent/PZAgent` 0 ERROR. Tests: `python -m pytest testing/tests/pzagent -q` saved to a file and read back (319 passed at Plan 21's close; the count never drops). The full `python -m pytest tools/tests testing/tests -q` once per task that touches `testing/agent/` or the Lua, saved and read back (baseline 8649 passed, 28 skipped).
- The run order is pass 4 → Stage B → Stage C (→ the dense run); each later boot is gated on the earlier verdict as the spec's § 4 says, and a NO-GO ends the plan at the report's § 7.

## Rulings carried in from the plan's opening

- **P21b-0** Angus's order adopts the report's § 6 changes 1–3 as the pass-4 gate `gate_a4`; the spec's 3-pass budget is exceeded by this one ordered pass, named as such in the artifact's guide and the report's § 7 — cost if wrong: one 14-minute session.
- **P21b-1** `BUDGET_S` for pass 4 is 800 s (pass 3 ran out of its 560 s budget after 19 of 20 legs on 14 s detour legs; CLAUDE.md § 5's split rule is about 15 minutes of wall time, and 800 s plus the boot stays under it) — cost if wrong: a longer session.
- **P21b-2** The motion measure changes (change 3's first option); the legs keep starting from wherever the character settled (change 3's second option is not taken), so the detour legs stay in the artifact as a second reading of the route — cost if wrong: none for the graded figure.
- **P21b-3** The two parked must-fix items (research-notes' "Must fix before Stage B" and "Must fix before Stage C") land in Tasks 1 and 2 before any boot, since all three boots follow in one plan — cost if wrong: none.

---

### Task 1: Pass 4's Lua, gate and driver (20-square parts; index-first guards; `gate_a4`; `a_pipe_4.py`; `a_grade_4.py`)

**Files:**
- Modify: `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_Sense.lua` (`S.SCAN_SQUARES_PER_TICK`; the timed-action-queue read near its L97)
- Modify: `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_Act.lua` (`queueWalk` near L88; `open`'s ctor near L311; `loot`'s transfer near L388; `queueConsume` L404–408; `sleep`'s `onConfirmSleep` near L647)
- Modify: `testing/agent/grades.py` (append `gate_a4` and its constants; `gate_a` untouched)
- Create: `testing/agent/drivers/a_pipe_4.py`, `testing/agent/drivers/a_grade_4.py`
- Modify tests: `testing/tests/pzagent/test_lua_sense.py` (the constant and the part count), `testing/tests/pzagent/test_lua_act.py` (the guards)
- Create tests: `testing/tests/pzagent/test_a_pipe_4.py`

**Interfaces:**
- Consumes: `a_pipe_3.Pipe3` (frozen; `one_goto` is inherited from `a_pipe_2.Pipe2`, which records `x0`, `y0`, `ack`, `first_motion` per leg row and the leg's frames in `self.frames` as `(frame, readPyMs)` with each frame's `seq`, `wallMs`, `x`, `y`); `grades.gate_a`'s helpers `pct`, `_num`, `scan_tick_ms`, `scan_latency_ms`, `_count`, `MODES`, `SCAN15_MS`, `CMD_MOTION_P90_MS`, `MOTION_COMMANDS`, `MIN_FRAME_SHARE`.
- Produces: `grades.gate_a4(out)` returning the same keys as `gate_a` plus `cmd_move_p90_ms`, `cmd_move_n`, `cmd_move_paired`, `tick60_frames` and `pass` keys `tick_mean_at60`, `scan15`, `cmd_move_p90`, `gaps`, `lua_errors`, `hello` (`tick_p99_ms_at5` and `cmd_motion_p90_ms` stay in the output, ungraded); each motion row of `a_pipe_4.json` carries `first_move {seq, wallMs, x, y, readPyMs}` or None beside `first_motion`.

- [ ] **Step 1: The Lua constant.** `S.SCAN_SQUARES_PER_TICK = 20` with its comment naming pass 3's reading (60-square parts read 3–7 ms a tick, the emit about 0.5 ms per KB plus about 0.5 ms a line; a 20-square part projects to about 4.1–4.5 ms peak: `testing/artifacts/a_pipe_3-20261026-130558/GUIDE.md` § 1). `test_lua_sense.py`: the assert on the constant reads 20 and the radius-15 job yields ⌈961/20⌉ = 49 contiguous parts whose squares' union equals the synchronous scan's (keep every existing part test; where a test set the constant to 4 it stays).
- [ ] **Step 2: The index-first guards (research-notes "Must fix before Stage B").** Before each call, the vanilla class and the member are index-checked and a missing one is the goal's own failure reason, never a raise under `pcall`:
  - `queueWalk`: `ISTimedActionQueue ~= nil and ISTimedActionQueue.add ~= nil and ISWalkToTimedAction ~= nil and ISWalkToTimedAction.new ~= nil`, else return `false, "no walk action"` (goto then fails with the reason it already uses for a refused walk — read `failWalk` and keep its reason set; add no new reason to the `-- reasons:` header unless one is needed, and then add it to `agent/reasons.py` in the same commit).
  - `open`: `ctor ~= nil and ctor.new ~= nil` (the existing `ctor == nil` check widened), and `ISTimedActionQueue.add` checked as above.
  - `loot`: `ISInventoryTransferAction ~= nil and ISInventoryTransferAction.new ~= nil` once before the loop; a missing class is not "no match", so the goal fails with the existing `not loaded` reason (the vanilla class not loaded), said in the comment.
  - `queueConsume`: `ctor ~= nil and ctor.new ~= nil` before `ctor:new`; `act.isValidStart ~= nil` before calling it; `ISTimedActionQueue.add` as above.
  - `sleep`: `fn` is already nil-checked; `ISWorldObjectContextMenu.onConfirmSleep` is vanilla Lua that can raise inside itself, which no index check prevents: keep the `pcall`, and add a comment that this is the one site whose raise would park a `-debug` client, with the vanilla function named (quote its signature from the install's `media/lua/client/` in the report: `grep -rn "onConfirmSleep" D:/SteamLibrary/steamapps/common/ProjectZomboid/media/lua/client/`, read-only).
  - `PZAgent_Sense.lua` L97: `ISTimedActionQueue ~= nil and ISTimedActionQueue.getTimedActionQueue ~= nil` before the call; the returned object nil-checked and its `queue` read only when it is a Lua table (`type(q) == "table"`; `#q` is then a Lua length, not a Java one).
  Tests in `test_lua_act.py` / `test_lua_sense.py`: with `ISWalkToTimedAction = nil` a `goto` fails with its reason and raises nothing; with `ISInventoryTransferAction = nil` a loot at a container fails `not loaded`; with `ctor.new = nil` an eat returns `false` from `queueConsume`; with `ISTimedActionQueue = nil` the frame carries no `action` and raises nothing.
- [ ] **Step 3: Lints and the Lua tests.** `python tools/kahlua_lint.py testing/PZAgent`, `python tools/luabalance.py` on each touched .lua (HEAD copies first, then the working tree), `python tools/mod_lint.py testing/PZAgent/PZAgent`; `python -m pytest testing/tests/pzagent -q > <saved file>` read back. Commit (pathspec): `Plan 21b Task 1 Lua: 20-square scan parts; vanilla classes index-checked before every action build` over `testing/PZAgent testing/tests/pzagent testing/agent/reasons.py` (the last only if touched).
- [ ] **Step 4: `gate_a4`.** Append to `grades.py`, under a `# ==== Stage A pass 4 (the report's § 6 changes)` banner, `TICK_MEAN_MS_AT60 = 1.0`, `MOVE_EPS_TILES = 0.01` and:
  - `cmd_move_ms(motion_rows)`: per row, `first_move.wallMs - ack.wallMs`, +inf when either is missing (the same shape as `cmd_motion_ms`).
  - `gate_a4(out)`: the docstring states each gate as the report's § 6 words it. `tick_mean_at60`: `readings.rate60.tick_mean_ms_at60 < TICK_MEAN_MS_AT60` on at least `MIN_FRAME_SHARE` of `rate60.expected` frames (`rate60.frames`); `scan15` as `gate_a` (over `readings.scans.15`, `scan_tick_ms`); `cmd_move_p90`: p90 of `cmd_move_ms` over the unvoided motion rows `< CMD_MOTION_P90_MS` over at least `MOTION_COMMANDS` rows; `gaps`, `lua_errors`, `hello` as `gate_a`. The output carries, ungraded, `tick_p99_ms_at5` (as `gate_a` computes it) and `cmd_motion_p90_ms` (the directional measure, `cmd_motion_ms`), both named ungraded in the docstring. A missing reading fails its gate.
  - `gate_a` is not edited (a committed `a_grade.txt` carries its output: CLAUDE.md § 5).
- [ ] **Step 5: The driver `a_pipe_4.py`.** Built as `a_pipe_3.py` was (read it whole; import `a_pipe` as AP, `a_pipe_2` as AP2, `a_pipe_3` as AP3; a `Pipe4(AP3.Pipe3)`): `KEY = "a_pipe_4"`, `DRIVER = "a_pipe_4.py"`, `ARTIFACT = "a_pipe_4.json"`, `PROFILE = "testing/profiles/agent-nozombies.toml"`, `PASS3_RUN = "a_pipe_3-20261026-130558"`, `BUDGET_S = 800.0` (ruling P21b-1), `MOVE_EPS_TILES` imported from grades, the other constants inherited and named in `CONSTANTS` as pass 3 names pass 2's. The docstring: why a pass 4 (the three changes, each with its pass-3 reading and guide section), the phases (pass 3's unchanged except motion), and the motion row's new `first_move`: the first frame with `seq > ack.seq` whose `hypot(x - x0, y - y0) > MOVE_EPS_TILES` (`x0`, `y0` the settled position the row already records), `{seq, wallMs, x, y, readPyMs}`; `first_motion` (the directional reading) is kept beside it, ungraded. `one_goto` calls `super().one_goto(trip, dx)` then adds `first_move` from `self.frames` (the frames after the send: find them by `seq > row["ack"]["seq"]`; a refused or unacked row gets `first_move = None`). `new_out` adds `pass3_run`. `driver_checks`/`preboot`/`main` as pass 3's with the new names; `main` prints `cmd_move_p90_ms` from `grades.gate_a4` of the out dict beside `tick_mean_ms_at60`.
- [ ] **Step 6: `a_grade_4.py`.** A copy of `a_grade.py` over `gate_a4` (`a_grade.py` is frozen: its output is committed in three artifacts).
- [ ] **Step 7: Tests `test_a_pipe_4.py`** (model them on `test_a_pipe_3.py`): the static refusal of any argument; the constants name the file, key, artifact, profile and `BUDGET_S == 800.0`; a FakeMod4 whose frames move 0.3 tiles south-west first (a detour) and east later → `first_move` is the first moved frame and `first_motion` the later one; `gate_a4` arithmetic: a rate60 row with mean 0.48 and enough frames passes `tick_mean_at60`, 1.2 fails, a short window fails; `cmd_move_p90`: 20 rows at 120 ms → GO on that gate, 19 rows → fail, one row with no `first_move` → +inf counted; `tick_p99_ms_at5` and `cmd_motion_p90_ms` are present in the output and absent from `pass`; `a_grade_4.main` exit codes on a GO and a NO-GO dict written to a temp file.
- [ ] **Step 8: Tests and commit.** `python -m pytest testing/tests/pzagent -q` saved and read back; then the full `python -m pytest tools/tests testing/tests -q` saved and read back. Commit (pathspec): `Plan 21b Task 1: gate_a4 (the tick on the 60 Hz mean; motion as ack to first position change), a_pipe_4 and a_grade_4` over `testing/agent/grades.py testing/agent/drivers/a_pipe_4.py testing/agent/drivers/a_grade_4.py testing/tests/pzagent/test_a_pipe_4.py`.

### Task 2: The policy's cooldown (research-notes "Must fix before Stage C")

**Files:**
- Modify: `testing/agent/policy.py` (`_note_failures`, `tick`'s cooling test)
- Test: `testing/tests/pzagent/test_policy.py`

**Interfaces:**
- Consumes: `World.events` (each goal event carries `goalSeq`, `state`, `detail`; read `PZAgent_Main.lua`'s `goalEvent` and `world.py`'s `_event` to quote the exact state a pre-empted goal is reported with — the Lua's `A.start` returns the old goal's status and Main emits an event for it; quote the line), `Policy._finished`.
- Produces: `Policy._note_failures` counts a goal as failed only when its state is `failed` and its detail is not the pre-emption one; `Policy.tick` never passes over the `threat` branch for a cooling choice.

- [ ] **Step 1: Read and quote.** In the report, quote the Lua line that emits a pre-empted goal's event and its state/detail, and `_finished`'s mapping, so the fix names the real value (do not guess "superseded": read it).
- [ ] **Step 2: Failing tests.** In `test_policy.py` (read its fixtures first and reuse them): (a) a goal pre-empted by the policy's own next send (its event in the pre-empted form) leaves `last_failed` None and the same goal is chosen again at once; (b) a `fight` that failed (`no weapon` or `weapon broke`, the Lua's own reasons) while a threat is within `DANGER_R` → the threat branch still answers on the next tick (`flee` when unarmed, by `_armed`), never passed over to `need`/`forage`; (c) a `loot` that failed stays cooled for `FAILED_COOLDOWN_TICKS` (the existing behaviour, asserted so the fix is scoped).
- [ ] **Step 3: The fix.** `_note_failures` skips the pre-empted form; `tick` applies `_cooling` to every branch but `threat` (a comment: a threat is never waited out; the branch's own choice adapts, `flee` when unarmed). Update the module docstring's HEURISTIC bullet.
- [ ] **Step 4: Tests and commit.** `python -m pytest testing/tests/pzagent/test_policy.py testing/tests/pzagent/test_c_survive.py -q` saved and read back, then the folder. Commit (pathspec): `Plan 21b Task 2: the policy never cools a pre-empted goal and never passes over the threat branch` over `testing/agent/policy.py testing/tests/pzagent/test_policy.py`.

### Task 3: Stage A pass 4 — the boot (controller)

- [ ] `python testing/pzt doctor`; free memory ≥ 12 GB read and ledgered; the tree clean at the Task 1/2 commits; no live session.
- [ ] Detached launch: `python testing/agent/drivers/a_pipe_4.py` through `Start-Process` with stdout/stderr to the run dir; polled across foreground calls through the persisted artifact until `finished`.
- [ ] `python testing/agent/drivers/a_grade_4.py testing/runs/<run>/a_pipe_4.json > a_grade_4.txt`; the verdict ledgered. GO → Task 4 then 5. NO-GO on `scan15` → the fallback the spec's § 4.4 names is reported in Task 9 and no further boot runs. NO-GO on another gate → the controller rules (a defect found → one fix pass is outside this plan's budget: the report says so).

### Task 4: Pass 4's write-up (a fresh opus writer, artifacts only)

**Files:**
- Create: `testing/artifacts/a_pipe_4-<stamp>/{a_pipe_4.json, state.log, a_grade_4.txt, GUIDE.md}` (the first three byte-identical copies of the run's files; the controller commits them with the artifacts-register row and do-not-cite rows)

- [ ] The guide in the form of `testing/artifacts/a_pipe_3-20261026-130558/GUIDE.md` (How to read it; Verdicts; one section per gate with the numbers and their keys; the three changes against their pass-3 readings; a Do-not-cite section with the wildcard sentence for wall-clock leaves); every number cites a key; the derivation of `cmd_move_p90_ms` from the rows shown; the part-size projection checked against the measured 20-square peak.
- [ ] The controller: the artifacts-register row, do-not-cite rows, `python tools/claims_check.py --staged` 0, the commit `Plan 21b Stage A pass 4: artifact a_pipe_4-<stamp> (...), its guide, register row and do-not-cite rows`.

### Task 5: Stage B — the boot (controller; gated on pass 4 GO)

- [ ] `b_actions.py` unchanged since its review (`git log -1 -- testing/agent/drivers/b_actions.py`); its preboot checks pass offline (`python -c` over `b_actions.preboot`); doctor; memory; detached launch; polled; `python testing/agent/drivers/b_grade.py <artifact> > b_grade.txt`; the verdict ledgered. NO-GO with the failing goal named → spec § 4.2 allows up to 4 passes: one fix pass is in this plan's budget (a new driver `b_actions_2.py`, a fresh brief naming the defect, the Lua fix reviewed) and no more.

### Task 6: Stage B's write-up (a fresh opus writer) and artifact commit (controller)

- [ ] As Task 4 for `b_actions-<stamp>/{b_actions.json, state.log, b_grade.txt, GUIDE.md}`: each repetition's steps and reasons, the server-seen eats with their `nutrition.get` readings, the failure-reason distribution against `REASONS`, the game and wall clocks per step.

### Task 7: Stage C — the boot (controller; gated on Stage B GO)

- [ ] `c_survive.py` unchanged since its review, its preboot offline; doctor; memory; the detached launch (~95 min); polled every few minutes through the persisted artifact's `loop` (wallS, ticks, needs, the last decisions, memory) until `finished`; `python testing/agent/drivers/c_grade.py <artifact> > c_grade.txt`.
- [ ] If the character survived the day cap: provision the dense fixture (`python testing/pzt provision --name agent-dense --sandbox Zombies=4`, Angus's "provision the fixture, use the defaults" of 2026-10-26 covering it), set `testing/profiles/agent-dense.toml`'s `fixture = "agent-dense"` and update its description, commit the profile (pathspec) and the fixture record if the harness tracks one, then launch `c_survive_dense.py` the same way. If it died, the dense run is skipped and the guide says why (spec § 4.3).

### Task 8: Stage C's write-up (a fresh opus writer) and artifact commits (controller)

- [ ] As Task 4 for `c_survive-<stamp>/` (and `c_survive_dense-<stamp>/`): survival time; the needs series client against server; decisions per minute; fights and outcomes; the last ten decisions before a death; per-tick cost over the session; lua_error events; the stop condition. `decision.log` is committed byte-identical beside the JSON when the run kept it.

### Task 9: The evidence layer and the report's § 7 (two writers on disjoint files, then the controller)

**Files:**
- Modify: `docs/superpowers/specs/2026-10-26-agent-harness-report.md` (a dated § 7 "The go-with-changes passes (Plan 21b)": pass 4 against its three changes; Stage B; Stage C; the recommendation restated — go / no-go for spike D now that a survival baseline exists or not; the JVM fallback's status) — writer A, from the artifacts and guides alone.
- Modify: `docs/platform/harness.md` `#agent` (new tagged sentences for the pass-4 tick mean gate, the 20-square part cost, the ack → first-move p90, Stage B's completion and server-seen eats, Stage C's survival and decision rate), `docs/reference/research-notes.md` (the four settled threads re-pointed or removed: the first-motion measure, Stages B and C unrun, the two must-fix items; the dense fixture line updated), `docs/reference/run-aliases.csv` — writer B, with a `task-9-delta.tsv` the controller applies (ids from the register's next unused).
- Controller: `claims_delta.py apply`, `claims_check.py --fix-tags` once, the full checker 0, `page_lint`, `cited-by --write`, `contradictions --check`; `docs/superpowers/HISTORY.md`'s Plan 21 entry extended with 21b; CLAUDE.md § 3 baseline and the router row's report pointer unchanged (the report file is the same).

- [ ] Writer A: the § 7 with every number citing `testing/artifacts/<run>/<file>` and a key; nothing from the implementers' reports; `Model:` line.
- [ ] Writer B: the sentences, the delta, the notes; `Model:` line.
- [ ] Controller: apply, gates, commit, the whole-pass review (opus), one fix wave, re-review, the close commit, push, memory.
