# Plan 21: the agent harness — feasibility report

Can a pure-Lua client mod that streams state to files, driven by a Python planner, run a Project Zomboid character, and what does that cost? On 42.21 the plumbing works. Over three boots the file link held in append mode with 0 gaps, 0 bad lines and 0 Lua errors. A `goto` goal walked the character every time it was alive: 19 of 19 legs ended `done` in pass 3. A frame tick costs about half a millisecond: the mean over 1803 consecutive frame ticks was 0.482 ms. Even so, Stage A ended **NO-GO** on its three-pass budget, and no gate passed on the final pass apart from the link's own gates (hello, gaps, Lua errors). Each failure has a named cause, and none of them is a broken pipe:
- The tick gate (`p99 < 2 ms`) sits at the resolution of the 1 ms clock.
- The 15-tile scan's worst tick was 7 ms against a 5 ms gate. That cost comes from the size of each emitted line, not from walking the squares.
- The motion gate's p90 of 8130 ms comes from a directional measurement on a route that detours out of the spawn house. The walk itself started 77–180 ms after each ack.

Stages B (the actions) and C (survival) were built and tested offline but were **not run**, so this report has no survival result.

## 1. What works

- **The file link.** `hello.mode` read `append` in all three runs (`testing/artifacts/a_pipe-20261026-101003/a_pipe.json` `mode`; `testing/artifacts/a_pipe_2-20261026-115846/a_pipe_2.json` `mode`; `testing/artifacts/a_pipe_3-20261026-130558/a_pipe_3.json` `mode`). Each run read `gaps` 0 and `bad` 0, `missing` `[]` (no missing Java member in the frame or the scans) and `lua_errors` 0, in the same three files.
  - Frames arrived at the commanded rate:
    - Pass 1 (`readings.rates.<2|5|10>.frames`): 121, 301 and 600 frames at 2, 5 and 10 Hz, against 120, 300 and 600 expected.
    - Pass 2 (`a_pipe_2.json` `readings.rates.*.frames`): 120, 300 and 601.
    - Pass 3 (`a_pipe_3.json` `readings.rates.*.frames`): 120, 300 and 601, and 1803 frames in the 30 s window at 60 Hz against 1800 expected (`readings.rate60.frames`, `readings.rate60.expected`).
  - `dropped_max` was 0 at every rate (per the GUIDE.md of each run).
  - In pass 3, every scan's parts reassembled to the full square count: 121, 441 and 961 squares at r = 5, 10 and 15, with `missing` `[]` (`a_pipe_3.json` `readings.scans.<r>[*].squares`, `.missing`). Replaying `state.log` through `agent/world.py`'s `World` dropped no scan (`testing/artifacts/a_pipe_3-20261026-130558/GUIDE.md`, "Bytes per part").
- **Goals that ran live:** only `goto`.
  - Pass 3: 19 of 19 graded legs ended `done` within 1 tile, with 0 `goal_failed` (`a_pipe_3.json` `readings.motion[*].goal`, `events`).
  - Pass 2: 19 legs ended `done` and 1 ended `goal_failed` (`a_pipe_2.json` `events`).
  - The other goals were built and unit-tested only: `stop`, `open`, `loot`, `eat`, `drink`, `fight`, `flee` and `sleep` (`testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_Act.lua`, `A.goals[...]`). No artifact reads them.
- **The command round trip.** Every command was acked in the log. The `ack` line counts were 38, 38 and 40 (`state.log` line census in each run's `GUIDE.md` file table). Scans and motion legs were acked as well (`readings.scans.*[*]`, `readings.motion[*].ack`).
  - The server bus also answered `stats.all` three times per run, with complete stats (`readings.server[*].ack`). Its times are in § 2.

## 2. The cost of each layer

Every `*Ms` cost leaf is the difference of two integer `getTimestampMs` stamps. A small value therefore bounds the true cost rather than measuring it, and only a mean over many frames resolves below 1 ms. Each run's do-not-cite rows say this too (`docs/reference/do-not-cite.csv`, the `readings.rates.*.tickMs` rows).

**Per-tick cost** (the sum of the poll, act, scan-step, sense and previous-flush leaves):

- **At 5 Hz:** p50 1, 1 and 0 ms and p99 2 ms in all three passes, read as "at or below about 2 ms". The means were 0.714, 0.623 and 0.540 ms (`testing/artifacts/a_pipe-20261026-101003/a_grade.txt` `tick_p99_ms_at5`; the per-key table in each `GUIDE.md` from `readings.rates.5`).
- **The best reading — 60 Hz, a frame every tick:** a mean of **0.482 ms** per frame tick over 1803 frames: `tick_sum` 869 ms over 30031 ms of client wall time (`a_pipe_3.json` `readings.rate60.tick_mean_ms_at60`, `.tick_sum`, `.frames`).
  - By leaf: 0.21 ms flush, 0.16 ms poll, 0.11 ms sense, about 0 for act and scan step (pass 3 `GUIDE.md`, read off `state.log`).
  - This is the mean of the measured spans. It does not cover the `OnTick` dispatch, and it is not a tail figure.
- **Rate does not raise the cost per frame:** pass 3's means were 0.792, 0.540 and 0.552 ms at 2, 5 and 10 Hz (`readings.rates.*`, per `GUIDE.md`).
- **Bytes written per minute:** 88372 at 2 Hz, 220794 at 5 Hz and 442252 at 10 Hz (pass 3, `state_bytes_end − state_bytes_start`). A 5 Hz frame is about 736 bytes (pass 2 `GUIDE.md` § 2).

**The scan.**

- **Walking squares:** about 0.016–0.018 ms per square.
  - Pass 1 fit `scanMs ≈ 0.91 + 0.0162 × squares` over 15 one-tick scans (`a_pipe.json` `readings.scans.*[*].scanMs`).
  - Pass 2's 60-square chunks averaged about 1.0 ms each (`a_pipe_2.json` `readings.scans.*[*].scanMsPerTick`).
  - In pass 3, a full 60-square part's walk averaged 1.09 ms at r = 15 (`a_pipe_3.json` `readings.scans.15[*].partStepMs`).
- **The emit** (serialising the line and appending it to the file):
  - Pass 2's whole lines cost about 0.445 ms per KB through the origin, `−1.10 + 0.460 × KB`. That is 44–45 ms in a single tick for the 99.3 KB r = 15 line (`a_pipe_2.json` `readings.scans.*[*].scanEmitMs`).
  - Pass 3's 140 part lines (0.38–8.54 KB) cost 0.495 ms per KB through the origin, `0.51 + 0.418 × KB` (`a_pipe_3.json` `readings.scans.*[*].partEmitMs`). That is about half a millisecond fixed per line plus the slope.
- **The three emit shapes at r = 15** (worst tick):

  | Shape | Worst tick | Source |
  |---|---|---|
  | One tick (pass 1) | 14–21 ms | `readings.scans.15[*].scanMs`; pass 1's committed `a_grade.txt` `scan15_ms_max` 21 |
  | Walk chunked, one emit (pass 2) | 45 ms on the completing tick; the walk steps alone ≤ 3 ms | `a_pipe_2-20261026-115846/a_grade.txt` `scan15_ms_max` 45; `scanStepMaxMs` |
  | Parts, one line per tick (pass 3) | 7 ms; a part's tick 3–7 ms, mean 4.3 | `a_pipe_3-20261026-130558/a_grade.txt` `scan15_ms_max` 7 |

  - The whole r = 15 scan takes 61–75 ms of summed cost across 17 ticks (`a_pipe_3.json` `scan15_latency_ms_max` 75, ungraded).
  - The run's largest single tick was 8 ms, in an r = 10 scan (scanId 9; `GUIDE.md` § 1).
- **Projected part sizes** (a projection, which do-not-cite marks "not a reading"; pass 3 `GUIDE.md` § 1):
  - 30 squares: a peak tick of about 4.8–5.1 ms, which is at the gate.
  - 20 squares: about 4.1–4.5 ms, which is under it.
  - The only small parts that were measured, the r = 10 last parts (21 squares, 2.33 KB), read ticks of 1–2 ms.

**The bus.** Each run has n = 3 `stats.all` round trips (`readings.server[*].rttMs`):
- Pass 1: 1509.0, 2011.8 and 1762.9 ms, taken with the character dead.
- Pass 2: 1010.6, 506.0 and 2013.0 ms.
- Pass 3: 1008.2, 759.4 and 1262.6 ms.

The register lists all of these as do-not-cite (`n = 3`). They are shown here only as the order of magnitude, 0.5–2 s, not as a figure.

**The walk.**
- On a direct path the client-clock ack→first motion (0.2 tiles in the commanded direction) read:
  - pass 2's 18 clean legs (cmdSeq 21–38): 412–498 ms, p90 496 (`a_pipe_2.json` `grades.cmd_motion_ms`, legs named in `GUIDE.md` § 3);
  - pass 3's −x legs: 395–496 ms (`a_pipe_3.json` `readings.motion[*]`, cmdSeq 22–38 even).
- The first position change of any kind came 5–11 ticks (77–180 ms) after the ack on every leg in passes 2 and 3 (read off each `state.log`, `GUIDE.md` § 3). The rest of the 0.4–0.5 s is the walk's ramp to 0.2 tiles plus the 6-tick frame period.
- **On a detour** the directional figure measures the route, not the latency. Pass 3's +x legs read 7462–8545 ms (`a_pipe_3.json` `cmd_motion_p90_ms` 8130), which the register lists as do-not-cite. Those legs walked 24.7–26.2 tiles in about 14 s (pass 3 `GUIDE.md` § 3).

## 3. The walls

1. **The 1 ms clock against a 2 ms gate.**
   - `PZA.now` is `getTimestampMs`, so the 5 Hz `tickMs` is a sum of integer leaves.
   - The p99 read 2 in all three passes (`a_grade.txt` `tick_p99_ms_at5` 2 in each run), while the means were 0.54–0.79 ms and the 60 Hz mean was 0.482 ms (`a_pipe_3.json` `readings.rate60.tick_mean_ms_at60`).
   - At 5 Hz no single leaf reached 2 ms more than once in 300 frames (pass 3 `GUIDE.md` § 2).
   - The gate cannot separate 1.2 ms from 1.9 ms, so it failed because of the clock, not because of a measured cost. No sub-millisecond source reachable from Lua was read in this plan (every `GUIDE.md` says "not read here").
2. **The emit cost of a scan line.**
   - Writing to the file costs about 0.45–0.5 ms per KB, plus about 0.5 ms per line (§ 2; `a_pipe_2.json` and `a_pipe_3.json` `scanEmitMs` / `partEmitMs`).
   - At about 100–120 bytes per square, any part of 60 squares or more puts more than 3 ms of emit on one tick. That is why the scan gate failed at 7 ms in pass 3 (`a_pipe_3-20261026-130558/a_grade.txt` `scan15_ms_max`). The walk itself fits within a tick.
3. **Directional first motion on a detour.**
   - `agent0`'s spawn is inside building 8's living room. The straight line east crosses a closed window at (11001, 9699), and the path leaves by the south-west door (pass 3 `GUIDE.md` § 3, from the r = 15 scan in `state.log`).
   - Every +x leg first walked away from the target for 6.2–6.7 s, so the first frame 0.2 tiles east came 7.5–8.5 s in (`a_pipe_3.json` `readings.motion[*].first_motion`).
   - The grade's p90 of 8130 ms reads this geometry, not pipe latency.
   - The same detour broke pass 2's progress-based stuck rule. Leg 1 failed `stuck` with a healthy character on a valid path, and leg 2 read 3661 ms because the failed goal's walk was left in the queue (`a_pipe_2.json` `readings.motion[0..1]`, do-not-cite as defect legs).
   - Pass 3's no-movement stuck rule held: the longest stationary run was 7 frame intervals, against `STUCK_TICKS` 90 (pass 3 `GUIDE.md` § 3).
   - The motion phase's budget cut it at 19 legs (`a_pipe_3.json` `budget_stop`), because each detour leg took about 14 s.
4. **The `agent` fixture kept zombies under a boot-time `Zombies = 6`.**
   - In pass 1 the first frame already listed a zombie 7 tiles away. A zombie with `hasTarget` appeared during the first motion leg, 58 `hit` events followed, and health first read 0 at frame seq 2070 (`testing/artifacts/a_pipe-20261026-101003/state.log`, per its `GUIDE.md`).
   - Nine legs therefore went unpaired and the motion grade read `Infinity` (`a_pipe-20261026-101003/a_grade.txt` `cmd_motion_p90_ms`, `cmd_motion_paired` 11).
   - The cause is settled: `Zombies` is fixed at world generation, so a boot-time value does not change a provisioned world and a fresh fixture is the remedy (#1811). The zombie-free fixture `agent0` removed the confound: health read 100 and `nZombies` 0 in every frame of passes 2 and 3 (`voided_legs` 0 in both).
5. **The lupa test host (a host-only caveat).**
   - The offline Lua tests run under lupa 2.8's Lua 5.1 with `collectgarbage('stop')`. With the collector running, a Python object's wrapper was seen to resolve to a different object after 541 calls (`testing/tests/pzagent/conftest.py`, `make_lua` docstring).
   - The real client is Kahlua on the JVM, so this limits only the offline tests: a collector-dependent defect would surface only at a boot. This caveat has no artifact behind it; it is a reading of the test host's code.
6. **The live tick-cost figure covers a frame tick's measured spans only.** The 0.482 ms mean excludes the `OnTick` dispatch, and on a non-frame tick it is an upper bound (pass 3 `GUIDE.md` § 2).

## 4. Survival results

None: Stage C was not run (ledger ruling, § 5 below). `c_survive.py` is built, tested offline and reviewed. If run, it would read:
- survival time;
- needs over time, with client-frame hunger, thirst, fatigue and health paired with the server's `Hunger` in the same wall second;
- decisions per minute;
- fights and their outcomes (with a bat equipped from a start kit);
- the outcome distribution of every goal;
- the per-tick cost across the session;
- `lua_error` events;
- the last ten decisions before any death.

It stops on death, a dead bus, a `lua_error` storm, low memory, the one-game-day cap or the budget (`testing/agent/drivers/c_survive.py` docstring).

**What each unrun stage would cost, so Angus can order it:**

- **Stage B** (`testing/agent/drivers/b_actions.py`): one boot of `agent-nozombies`, which points at fixture `agent0` (`testing/profiles/agent-nozombies.toml` line 2, and the driver's docstring). It runs five repetitions of scan → open → goto → loot food/water → eat → drink → goto spawn, with a wall budget of `BUDGET_S` 560 s, about 10 min (`b_actions.py` lines 71–79). Its gates are spec § 4.2's:
  - at least 4 of 5 sequences complete;
  - every failure carries a reason from the closed set;
  - the server sees 5 of 5 eats.
- **Stage C:** one detached session of `agent` (`Zombies = 5`) with `DAY_CAP_S` 5400 s and `BUDGET_S` 5700 s, about 95 min (`c_survive.py` lines 80–94). If the character survives, the same loop runs again on `agent-dense` (`Zombies = 4`; `c_survive_dense.py`).

## 5. Decisions taken

The `Ruling:` lines of `.superpowers/sdd/2026-10-26-plan-21-agent-harness/progress.md`, verbatim, in order, with the rulings the ledger records inline (its lines 96, 103 and 157) quoted at their place:

1. Ruling: P21-0 cmd.txt is key=value, not JSON — no Lua JSON decoder in the tree; the bus reads the same form — cost if wrong: a JSON decoder added later, the Python send() changed, nothing else.
2. Ruling: P21-1 the link probes append at load and falls back to chunk files — append mode is unexercised in the harness — cost if wrong: stage A measures the wrong mode's cost once; the mode is in `hello`.
3. Ruling: P21-2 stage C launched detached by Start-Process, polled via the persisted artifact — no xlib helper detaches; CLAUDE.md § 5 names this route — cost if wrong: a stuck session noticed one poll late (120 s).
4. Ruling: P21-3 Lua tested offline under lupa with Python stubs; a missing member is reported, never raised — the kernel tests' host pattern — cost if wrong: a stub shape that differs from the engine's hides a defect until the first boot, where the debug client parks and the pass is spent.
5. Ruling: Task 9 may call the goto machine as `A.goals["goto"].tick(p, g.sub)` with `g.sub` built by `A.goals["goto"].start` — the table is public — cost if wrong: none; a refactor at Task 9.
6. Ruling: self-review's goal_done/goal_failed events are added in Task 5 (Main emits an `event` when the status state changes to done/failed) — spec § 2.1 lists them — cost if wrong: one more line kind for Python to ignore.
7. Ruling: PZAgent carries mod.info at the root and at 42/mod.info, identical, as PZTestKit does — the engine reads the version folder first (#1558) and mod_lint's mod-info-place warns otherwise; the plan's Task 1 named the root only — cost if wrong: one duplicate three-line file.
8. Ruling: rotation switches the live file name (state.<n>.log) instead of copying; init starts a fresh segment when state.log exists; a failed write keeps its batch (buffer capped 2000, L.dropped) — the brief's copy is an unbounded hitch — cost if wrong: Python already orders by seq across all state*.log, so nothing downstream changes.
9. Ruling: the tests package is renamed testing/tests/pzagent (git mv) and conftest inserts testing/ on sys.path; tests import agent.* directly — the plan's folder name collided — cost if wrong: one rename.
10. Ruling (process): Tasks 2-fix and 3 ran in parallel and both touched conftest.py; both landed cleanly but it violated the disjoint-files rule — no two implementers run at once from here unless their file sets are disjoint by name in the briefs.
11. Ruling: Task 4's brief test unpacks S.events wrongly; S.events returns (ev, cur) as Task 5 consumes — the test takes the tuple — cost if wrong: none.
12. Ruling: getX/getY/getZ may be called directly on a player, zombie or square (as the harness does); every other Java member goes through PZA.call — cost if wrong: none on these three, present on every receiver.
13. Ruling: spec § 2.1 fields the plan dropped — action {class,n}, sickness, wetness, temperature, scan hour — are added in Task 4 fix 1 where the jar has the member; hit {kind, part}, zombie reanimated and container looked stay out of the spike (Python tracks looted) — cost if wrong: a field added later.
14. Ruling: every position goal takes absolute world coordinates (goto included; the plan's goto dx dy is dropped) — the planner works from scan coordinates and an offset goes stale while moving — cost if wrong: Task 8's motion phase computes x±10 from the frame.
15. Ruling: not adjacent and interrupted join loot's closed set; a loot timeout with nothing moved fails interrupted; open handles windows through ISOpenCloseWindow when the install has it.
16. Ruling (inline, ledger l.96, Task 5b): A command-tick flush is not counted (ruled; the frame tick's own write is the cost).
17. Ruling (inline, ledger l.103, Task 8): Budget: a worst-case motion phase overruns 540 s and stops cleanly as NO-GO (ruled acceptable).
18. Ruling: goto clears its walk at done (and sub-walks likewise) — the leftover walk corrupts the next goal's start — cost if wrong: a one-tile stop at each goal end.
19. Ruling: Stage B resets the server's food timer and sets hunger 0.3 before each eat (recorded in world_changes) — the stage grades the actions, not the appetite — cost if wrong: the eat reading is of a prepared character, said in the guide.
20. Ruling: pass 2 is allowed (budget 3): the scan is spread over ticks (a chunked scan, N squares per tick, the line emitted when complete), and the walk's stuck detector is re-worked after the write-up's state-log analysis names the cause; the tick gate is re-read on pass 2 with the clock quantisation named in the guide — cost if wrong: one more boot.
21. Ruling: a zombie-free fixture agent0 (Zombies=6) is provisioned for Stages A and B (the nozombies profile points at it); fixture agent (Zombies=5) stays for Stage C — a sandbox change at boot does not despawn — cost if wrong: one 2.5-min provision.
22. Ruling: pass 2 Lua: goto fails 'dead' at health 0; stuck judged by progress toward the target (distance not falling for STUCK_TICKS) rather than identical x,y; the scan chunked at 60 squares per tick, the line emitted when complete; driver a_pipe_2.py voids a leg during which health fell or a zombie was within radius; the tick gate stays and the guide names the 1 ms quantisation.
23. Ruling: the scan15 gate reads the max per-tick scan step (the frame-cost quantity Rule 6 cares about) against 5 ms; the chunk sum is reported as the scan's latency — the spec's gate guards the frame, not the total — cost if wrong: a latency the report states anyway.
24. Ruling: gate_a changed after pass 1's a_grade.txt was committed (the scan15 gate now needs per-tick figures a pass-1 artifact lacks); pass 1's verdict stands as graded at 3e550f1f (NO-GO either way: the character died) and its guide names that commit; no regrade — cost if wrong: a reader re-running a_grade on the pass-1 artifact sees scan15 fail for a missing field, which the guide explains.
25. Ruling: pass 3 (the last of the budget): the scan is emitted in parts (one scanPart line per tick, ≤ 60 squares, part i/n; World reassembles; the gate's per-tick term is max(step + that tick's part-emit)); a 30 s rate-60 window reports the mod's ms per second ÷ 60 as the sub-ms mean tick cost beside the quantised p99; the p99 gate stays as written and the report says what the clock can resolve — cost if wrong: one more boot.
26. Ruling: the start kit equips the spawned bat through the harness's client weapon.equip (recorded under readings.start_kit.armed) — an unarmed policy flees every threat and the stage would measure nothing about fighting — cost if wrong: one harness command in the readings.
27. Ruling: the in-session memory stop is LIVE_MIN_FREE_GB = 0.5 on two consecutive 5-minute reads (the 12 GB floor is pre-boot only; the host runs at 2-3 GB with the game up) — cost if wrong: a thrashing host ends the run later than it could; every read is recorded.
28. Ruling: bus_dead needs two consecutive failed polls (the dispatch said 60 s = one poll) — a single transient double failure must not end a 90-minute session.
29. Ruling (inline, ledger l.157, Task 10 fix 2): no separate re-review for a 3-test driver change that mirrors the reviewed a_pipe_3 pattern; the Stage B boot is its smoke test.
30. Ruling: the brief's rate-5 line was the controller's error, named here.
31. Ruling: Stage A ends NO-GO on its 3-pass budget as the spec's § 4.1 and § 7 rule (no gate relaxed); the plan goes to the report (Task 13); Stages B and C are built, offline-tested and reviewed but not run — the report names their boot cost so Angus can order them — cost if wrong: two sessions Angus can start by one line.

**Re-derivation of the gates.** `python testing/agent/drivers/a_grade.py <artifact>` at HEAD `9f7c001d` (exit 1 on each):

- **Pass 2:** it reproduces the committed `a_grade.txt` key for key, adding only the new `tick_mean_ms_at60` null.
- **Pass 3:** it reproduces it exactly.
- **Pass 1:** it disagrees with the committed file, as ruling 24 foresaw. The committed `a_pipe-20261026-101003/a_grade.txt` (graded at `3e550f1f`) reads `scan15_ms_max` 21. The re-derivation reads `scan15_ms_max` null and `scan15_latency_ms_max` 21, because the pass-1 artifact has no per-tick scan figures. Every `pass.*` value and the verdict (**NO-GO**) are the same.

**Addendum (the close review).** `d0c06574` (Task 10 fix 2) changed the Stage B driver's `scan_parts`: the scan it waits for is the `scanId` whose part 1 follows the ack, it awaits that scan's `done` part, and it checks `partsSeen` against `parts`. Ruling 29 waived its separate re-review and named the Stage B boot as its smoke test. The whole-branch review at the plan's close read it and found it correct; the Stage B smoke test it was to get never ran, since Stage B was not booted (ruling 31).

## 6. Recommendation

**Go-with-changes.** In all three passes, nothing measured shows a cost of the Lua-on-files layer that breaks the frame budget, as opposed to a gate failing:
- The mean frame tick is 0.482 ms (§ 2).
- A scan's walk fits in a tick.
- The walk responds within 77–180 ms of the ack.

Each NO-GO gate is answered by a change:

1. **Restate the tick gate on the 60 Hz mean.** `tick_mean_ms_at60` < 1 ms would have passed at 0.482 ms. Alternatively, keep `p99 < 2 ms` only alongside a finer clock, if one can be found from Lua. Size: a `gate_a` edit and its tests; no boot.
2. **Emit the scan in 20-square parts.** The projection puts the peak tick at about 4.1–4.5 ms, which only a run would confirm. Size: one constant (`S.SCAN_SQUARES_PER_TICK`) plus one Stage A boot of about 10 min. That boot would be a fourth pass outside the spent budget, so Angus has to order it.
3. **Fix how motion is measured.** Grade ack → first position change, which was 77–180 ms on every leg, or start the motion phase from open ground outside the `agent0` house. Size: a driver and grade change, folded into the same boot as change 2.

After that, **Stage B** (about 10 min, one boot on `agent0`) and then **Stage C** (about 95 min detached on `agent`, then the dense run) are what answer survival. They are built; each needs only an order.

**Spike D** (an LLM planning from `summary.py`'s view) is not worth running yet. No artifact reads the actions or survival under the scripted policy, so an LLM run would have no baseline to beat and no proof that the goals it would call work live. Revisit it after Stage C.

**The JVM-agent fallback.** Spec § 4.1 names the fallback when a cost line fails after three passes, and two cost lines did fail: the tick p99 and the 15-tile scan (`a_pipe_3-20261026-130558/a_grade.txt` `pass.tick_p99_at5`, `pass.scan15` false). Neither failure is a measured cost that a localhost socket is known to remove:
- The tick failure is the clock's resolution.
- The scan failure is the per-KB emit of a file append, which a smaller part size addresses.

No artifact measures a JVM agent or a `PZAgent_Server.lua` scan, so neither can be recommended on this evidence. The fallback stays unwarranted unless the 20-square pass also fails its scan gate.

Model: claude-opus-5-5
