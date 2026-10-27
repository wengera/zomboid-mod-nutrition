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
17. Ruling: goto clears its walk at done (and sub-walks likewise) — the leftover walk corrupts the next goal's start — cost if wrong: a one-tile stop at each goal end.
18. Ruling (inline, ledger l.103, Task 8): Budget: a worst-case motion phase overruns 540 s and stops cleanly as NO-GO (ruled acceptable).
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
32. Ruling: gate_a was edited after pass 2's a_grade.txt as well (1406d70e); the report re-derives pass 2 key for key and the guide pins its gate commit; no regrade; the rule is now a versioned gate function per pass — cost if wrong: none for the recorded verdicts.
33. Ruling: the spec deviations the close found (no stuck event; SCAN_S dead; fixture agent sets only Zombies; the world golden synthetic; per-goal headers partial) are accepted for the spike and named in the report's addendum — cost if wrong: a later plan adds them.
34. Ruling (wording): direct member calls are allowed on getX/getY/getZ and on nil-checked file handles (readLine/close/write); everything else through PZA.call.

**Plan 21b** (added 2026-10-26 with § 7): the four rulings carried in from the opening of the plan file `docs/superpowers/plans/2026-10-26-plan-21b-agent-harness-go-with-changes.md`, then every `Ruling:` line of `.superpowers/sdd/2026-10-26-plan-21b-agent-harness-go-with-changes/progress.md`, verbatim and in order. A ruling that sits mid-line in the ledger is quoted from its `Ruling:`, with the ledger line named.

35. **P21b-0** Angus's order adopts the report's § 6 changes 1–3 as the pass-4 gate `gate_a4`; the spec's 3-pass budget is exceeded by this one ordered pass, named as such in the artifact's guide and the report's § 7 — cost if wrong: one 14-minute session.
36. **P21b-1** `BUDGET_S` for pass 4 is 800 s (pass 3 ran out of its 560 s budget after 19 of 20 legs on 14 s detour legs; CLAUDE.md § 5's split rule is about 15 minutes of wall time, and 800 s plus the boot stays under it) — cost if wrong: a longer session.
37. **P21b-2** The motion measure changes (change 3's first option); the legs keep starting from wherever the character settled (change 3's second option is not taken), so the detour legs stay in the artifact as a second reading of the route — cost if wrong: none for the graded figure.
38. **P21b-3** The two parked must-fix items (research-notes' "Must fix before Stage B" and "Must fix before Stage C") land in Tasks 1 and 2 before any boot, since all three boots follow in one plan — cost if wrong: none.
39. (ledger l.26, Task 2 review) Ruling: the pre-existing _settle_loots behaviour (a pre-empted loot's square is marked looted, policy.py L129-136) is carried to research-notes by Task 9's writer B, not fixed now — a threat-interrupted loot square is lost for the session, a dumb-spike behaviour the report can name — cost if wrong: one unretried container in Stage C.
40. (ledger l.29, Task 1 review) Ruling: no fix round before the boot — cost if wrong: none for the measurement.
41. Ruling: the scan15 NO-GO is Stage A's final verdict (no gate relaxed; the report's § 7 names the spec's § 4.4 fallback since the 20-square pass failed its scan gate) AND the Stage B and C boots proceed — Angus's order "run the go-with-changes boot" adopted the sequence the close message named (pass 4, then B, then C; the report's § 6 conditions neither on pass 4), and the failing gate measures a client-side scan stutter (5-7 ms ticks for ~49 ticks a scan), not the goals or survival B and C measure; the plan's Task 3 line "no further boot runs" is overridden by this ruling — cost if wrong: two unattended sessions (~105 min) Angus did not want, stoppable at any poll.
42. Ruling: one Stage B fix pass (spec § 4.2 budget 4; the plan's Task 5 allows one): b_actions_2.py — beside() excludes solidTrans and container squares; the pick ranks containers by dataset food and water-like items over the whole scan; the wide scan runs when no container holds food or water, so a stocked neighbour (and its door: `open` has never run live) is reached — built offline now, booted after Stage C ends (one session at a time) — cost if wrong: one ~5 min session.
43. Ruling: Stage C launches now, before B's fix pass, under the earlier ruling that Angus's order covers C; C's goals do not depend on the Stage B gate (the eat, drink, loot and goto goals all ran live; the completion failure is the fixture's stock) — cost if wrong: the 95-minute session.
44. Ruling: Task 5b is amended (task-5b-amendments.md, sent to the running implementer): the Lua adjacentTo skips isSolidTrans squares (its own commit + test), and the driver takes two picks per repetition (food container, water container; WATER_RX widened with DrinkingGlass|Mug, never Bleach) — spec § 4.2 says "loot each container food then water", so two containers are within the sequence — cost if wrong: one ~5 min session.
45. Ruling: spec § 4.3's one fix pass is forced — the four defects are mechanism (no disengage radius; no fight/flee hysteresis; a fight never re-evaluated; the pair-of-threats health rule) not luck — Task 7b: policy hysteresis + thin driver c_survive_2.py (c_survive.py frozen), booted after Stage B pass 2 — cost if wrong: one <= 95 min session and the implementer's time.
46. Ruling: two Lua defects join the Stage C fix pass as Task 7c, after Task 5b's Lua commit lands (one writer on Act.lua at a time): the fight goal steps toward its target until within the weapon's reach before attacking, and the flee goal runs — cost if wrong: the C2 session reads them again.
47. Ruling: no Stage B pass 3 (budget 2 of 4 used) — the completion gate is bound by the fixture's stock of fluid containers and by the sequence counting a failed `open` on a window the walk did not need; every goal functions live, which is what Stage B measures; the report says the gate as specified cannot pass on agent0 and names what a pass 3 would need (a stocked fixture or a sequence that opens only a door it must pass) — cost if wrong: a 6-minute session not run.
48. Ruling: Stage C ends at 2 of its 3 runs; no third run in this plan and no dense run (a death twice) — the fix pass's defects are fixed and read (no flap; the reach), and what remains is the game (three zombies at the spawn house against a walking flee) and the unexplained pre-contact health fall, which the write-up is asked to trace against the scan map; a third run without a diagnosed cause would read the same — cost if wrong: one 95-min session Angus can order with the diagnosis.
49. Ruling: the DISENGAGE_R count widening the "too many" rule is a defect of the pass-2 policy, named in the report and research-notes as the first fix of any third run (the hold uses 10 tiles; the count rules keep 6); no third run in this plan (the ruling above stands) — cost if wrong: none now.

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

Plan 21b ran these changes: § 7.

Model: claude-opus-5-5

## 7. The go-with-changes passes (Plan 21b, 2026-10-26)

Plan 21b booted five live sessions on 42.21. Each landed as a byte-identical artifact with a reading guide, and every path below is relative to `testing/artifacts/`:

| Run | Folder | Grade file | Verdict |
|---|---|---|---|
| Stage A pass 4 | `a_pipe_4-20261026-181848` | `a_grade_4.txt` | NO-GO on `scan15` alone |
| Stage B pass 1 | `b_actions-20261026-183143` | `b_grade.txt` | NO-GO on `completed` (0 of 5) |
| Stage B pass 2 | `b_actions_2-20261026-194009` | `b_grade.txt` | NO-GO on `completed` (2 of 5) |
| Stage C run 1 | `c_survive-20261026-183905` | `c_grade.txt` | died (no gate) |
| Stage C pass 2 | `c_survive_2-20261026-195516` | `c_grade.txt` | died (no gate) |

The guides are the authority for the readings, and the grade files are the authority for the verdicts. A number given here without a key is a guide's reading, and its section is named.

**In short.** The pipe and the action goals work live. Over the five runs the link read 0 gaps and 0 Lua errors. In the second Stage B pass, `goto`, `loot`, `eat`, `drink` and `scan` completed every time they were sent. Of the three changes in § 6, two closed their gates (the tick, the motion). The scan gate failed again: the 20-square parts halved the mean scan tick but not the worst one. No gate ended GO:
- Stage B's completion gate cannot pass on the `agent0` fixture.
- Both survival runs died of zombie damage, after 109 and 32 game minutes of the loop, before any need rose far enough to trigger an `eat`, `drink` or `sleep` goal.

### 7.1 What Plan 21b ran and why

Angus adopted § 6 with the order "run the go-with-changes boot" (ruling 35, P21b-0). The plan ran:
1. **Change 1, the tick gate on the 60 Hz mean.** `gate_a4` grades `tick_mean_ms_at60 < 1 ms` and reports the 5 Hz p99 ungraded beside it.
2. **Change 2, 20-square scan parts.** `S.SCAN_SQUARES_PER_TICK = 20`, against pass 3's 60 (`a_pipe_4-20261026-181848/GUIDE.md`, "How to read it").
3. **Change 3, motion graded from the ack to the first position change.** `grades.cmd_move_ms`: the first frame after the ack that moved more than `MOVE_EPS_TILES` 0.01 tiles in any direction. The legs still start wherever the character settled (ruling 37, P21b-2), so the detour legs stay in the artifact.

Pass 4 is a fourth Stage A pass, one beyond the spec's § 4.1 budget of three, which Angus ordered (ruling 35). It was graded by a new, versioned `gate_a4`. The frozen `gate_a` was not edited.

Before any boot, the two must-fix items parked at Plan 21's close landed (ruling 38, P21b-3):
- **Task 1, Lua.** Vanilla classes are index-checked before every action is built.
- **Task 2, the policy's cooldown.** The policy never cools a pre-empted goal and never passes over the threat branch.

Both commits are named in the guides' provenance: `942859f2` in `a_pipe_4-20261026-181848/GUIDE.md`, and the policy at `4744e066` in `c_survive-20261026-183905/GUIDE.md`.

Spec § 4.1 sends a Stage A NO-GO straight to the report. Ruling 41 overrode that: Stages B and C booted after pass 4's NO-GO, because the failing gate measures a client-side scan stutter, not the goals or survival that B and C measure. Each stage then took one fix pass:
- Stage B pass 2, on rulings 42 and 44.
- Stage C pass 2, on rulings 45 and 46.

### 7.2 Stage A pass 4 against its three changes

`a_pipe_4-20261026-181848/a_grade_4.txt`: `verdict` **NO-GO**. `pass.tick_mean_at60`, `pass.cmd_move_p90`, `pass.gaps`, `pass.lua_errors` and `pass.hello` are all true. `pass.scan15` is **false**.

| Change | Pass 3 reading | Pass 4 reading | `gate_a4` |
|---|---|---|---|
| 1. Tick gate on the 60 Hz mean | `tick_mean_ms_at60` 0.482 (`a_pipe_3-20261026-130558/a_pipe_3.json` `readings.rate60.tick_mean_ms_at60`) | `tick_mean_ms_at60` 0.7938888888888889 on `tick60_frames` 1800 | < 1 ms: **pass** |
| 2. Scan in 20-square parts | `scan15_ms_max` 7 with 60-square parts (`a_pipe_3-20261026-130558/a_grade.txt`) | `scan15_ms_max` 7; `scan15_latency_ms_max` 117, ungraded (pass 3: 75) | < 5 ms: **fail** |
| 3. Ack → first move | `cmd_motion_p90_ms` 8130, directional and do-not-cite; first change 77–180 ms (pass 3 `GUIDE.md` § 3) | `cmd_move_p90_ms` 195 on `cmd_move_n` 20, `cmd_move_paired` 20 | < 500 ms: **pass** |

All pass-4 readings are from `a_pipe_4-20261026-181848/a_grade_4.txt`.

- **The tick.** The 5 Hz p99 still reads 2 (`tick_p99_ms_at5` 2 on `tick_frames_at5` 300, ungraded), so `gate_a`'s `< 2` would still fail on the clock, as § 3 wall 1 says.
- **Motion.**
  - The graded legs read 110–220 ms (`a_pipe_4-20261026-181848/GUIDE.md` § 3). That is within one to two frame periods of the ack: frames are about 100 ms apart at rate 10, so the figure is frame-quantised, and its do-not-cite row bars citing it more finely.
  - The ungraded directional figure read 7629 (`cmd_motion_p90_ms`), the same detour as pass 3.
  - All 20 legs ended `done` (`events` `goal_done` 20, GUIDE, "How to read it"). None was voided (`a_grade_4.txt` `cmd_motion_voided` 0). The session finished inside `BUDGET_S` 800 at `wall_seconds` 610.8 with no budget stop (GUIDE, header).
- **The plumbing.** `gaps` 0, `lua_errors` 0, `mode` `append` (`a_grade_4.txt`); `state.log` seq 1–6351 with no gap (GUIDE § 4).

**The scan finding.** The 20-square parts halved the mean scan tick and left the worst one at 7 ms (`a_pipe_4-20261026-181848/GUIDE.md` § 1):
- **The mean fell.** A full part's tick averaged 2.29 ms, against pass 3's 4.3.
- **The tail stayed.** Over the 245 r = 15 ticks, 14 read 5 ms or more, and every scan held at least one.
- **The emit carries a per-line cost that does not shrink with the part.** Through the origin the emit reads 0.829 ms per KB, against pass 3's 0.495. A 2.1 KB part's emit reads 1.67 ms on average (the binned table), where pass 3's fit predicts about 1.39.
- **The whole scan costs more.** An r = 15 scan now emits 80–86 ms over 49 lines, against pass 3's 47–55 ms over 17, and its latency is 103–117 ms.
- **The projection did not hold.** Pass 3's projection of a 4.1–4.5 ms peak (§ 2 above) assumed the peak would sit about 2.7 ms above the mean tick. It sits about 4.7 ms above it.

**The host read slower than in pass 3, and the run cannot say why.** Every window's mean frame cost read 0.15–0.31 ms above pass 3's (`a_pipe_4-20261026-181848/GUIDE.md` § 2):

| Rate | Pass 4 mean (ms) | Pass 3 mean (ms) |
|---|---|---|
| 2 Hz | 1.017 | 0.792 |
| 5 Hz | 0.777 | 0.540 |
| 10 Hz | 0.705 | 0.552 |
| 60 Hz | 0.794 | 0.482 |

At 60 Hz the rise is spread over `pollMs`, `linkMs` and `senseMs`. Yet `PZAgent_Main.lua` and `PZAgent_Link.lua`, which hold the poll and the flush, did not change between the two passes' Lua. The guide does not separate a Lua cost from the host's state, and neither does this report. The per-KB emit rise above may share the same cause.

**The verdict** on `gate_a4` is **NO-GO on `scan15` alone**. It is Stage A's final verdict, and no gate was relaxed (ruling 41).

**What this says about the spec's § 4.4 fallback.** § 6 left the JVM-agent fallback "unwarranted unless the 20-square pass also fails its scan gate". The 20-square pass failed its scan gate, so the fallback's condition, and spec § 4.1's ("a cost line failing after 3 passes → … the report names the fallback (§ 4.4) and whether `PZAgent_Server.lua` would help"), is now met. On this evidence:
- **The failing cost is the client's own Lua.** The walk is a 0.567 ms mean per 20-square part, and the rest is a per-line serialise-and-append whose cost does not fall below about 1.7 ms for a 2 KB line (`a_pipe_4-20261026-181848/GUIDE.md` § 1). The file append happens in that Kahlua emit.
- **A JVM agent on a localhost socket** would replace the Kahlua serialisation and the file append with Java. Whether a socket write is cheaper per line than this append is **not measured**: no artifact of Plan 21 or 21b reads a socket or a JVM agent. Unless the agent also walked the squares in Java, it would leave the walk's cost where it is (inference).
- **A server-side scan (`PZAgent_Server.lua`)** would move the same Kahlua walk and emit off the client's frame and onto the server's frame. The server's frame is where this repository's Rule 6 judges cost (CLAUDE.md § 1). Its result would then have to reach Python through a server file or the bus, whose `stats.all` round trips are of the order of 0.5–2 s (§ 2 above, n = 3, do-not-cite). That is an inference: no server-side scan was built or measured.
- **The fallback is not recommended on this evidence.** It is named because its condition is met. What fails is a client-side stutter of 5–7 ms on a few ticks of an r = 15 scan, for a test tool: 14 of the 245 ticks of five r = 15 scans in pass 4. Neither alternative has a reading that says it is cheaper. A measurement comes before any build (§ 7.6).

### 7.3 Stage B — the actions

Spec § 4.2 runs a fixed sequence with no policy, on the zombie-free fixture `agent0`. Its gates are: sequences completed ≥ 4 of 5; failures carry a reason from the closed set; the server sees 5 of 5 eats.

**Pass 1** (`b_actions-20261026-183143/b_grade.txt`): `verdict` **NO-GO**.

| Gate | Reading | Pass |
|---|---|---|
| Sequences completed | `completed` 0 | false |
| Failure reasons in the closed set | `reasons_in_set` true, `reasons_outside_set` `[]` | true |
| Eats seen by the server | `eats_seen_by_server` 5 | true |

`failing_steps`: `goto:stuck`, `loot:no match`, `loot:not adjacent`.

- **The goals ran live for the first time.** Stage A ran only `goto`, and this was the first live run of `loot`, `eat` and `drink` (`b_actions-20261026-183143/GUIDE.md` § 4):
  - `eat`: 5 of 5 ended `consumed`.
  - `drink`: 5 of 5 ended `consumed`.
  - `loot`: 1 of 10 ended `done`, moving one `Base.Oatmeal`. That oatmeal was eaten and seen by the server.
  - `goto`: 9 of 10 ended `done`.
  - `scan`: 5 of 5, each 49 parts and 961 squares, with `missing` `[]`.
  - `open`: **never sent**, because no door or window lay on the straight line to any pick.
- **Every eat was seen by the server.** On every repetition the server's `nutrition.get` after the eat read hunger lower and calories higher (GUIDE § 3). The character was prepared first: the harness reset the food timer and set hunger to 0.3 before each eat. The deltas are therefore not food values (do-not-cite).
- **The fixture's stock** (GUIDE §§ 5 and 7, cause 1). No container square in reach held both a Food-class item and an item with a fluid container. The pick's fullType regexes matched none of the house's items, so every pick was ranked by distance alone. A row completes only when both of its loots end `done` on its single pick, so on this fixture `completed` read 0 whatever the pick.
- **The two beside-square defects, one in the driver and one in the Lua** (GUIDE § 7, cause 2). The driver's `beside` and the Lua's `adjacentTo` both keep any neighbour that is not `solid`. In repetition 5 they chose the kitchen stove, a `solidTrans` square that cannot be stood on. The `goto` there failed `stuck`, and both loots failed `not adjacent`, each after 360 ticks with the character unmoved. The state machines reported this correctly.
- **Clean plumbing.** `gaps` `[]`, `lua_errors` 0, 35 commands acked (GUIDE § 6 and header).

**Pass 2** (`b_actions_2-20261026-194009/b_grade.txt`): `verdict` **NO-GO**.

| Gate | Reading | Pass |
|---|---|---|
| Sequences completed | `completed` 2 | false |
| Failure reasons in the closed set | `reasons_in_set` true | true |
| Eats seen by the server | `eats_seen_by_server` 5 | true |

`failing_steps`: `goto:no water pick`, `loot:no water pick`, `open:locked`.

- **What changed** (rulings 42 and 44; `b_actions_2-20261026-194009/GUIDE.md`, "How to read it"):
  - Each repetition takes two picks, one food and one water. The food pick is ranked by the dataset's edible food ids, and the water pick by water-like fullTypes, with `Base.Bleach` excluded.
  - `beside_free` excludes squares that are `solid`, `solidTrans` or hold a container.
  - The Lua's `approach` skips `solidTrans` squares (`e1d298d3`).
  - An r = 25 scan runs when the r = 15 scan lacks a pick.
- **Pass 1's three failure details are gone** (GUIDE §§ 1 and 4):
  - `goto`: 13 of 13 ended `done`, none `stuck`.
  - `loot`: 8 of 8 ended `done`, moving 21 items in all.
  - Every eat was a looted item, and all 5 were seen by the server.
  - `drink`: 5 of 5 `consumed`.
  - Seven of the eight loots were queued from two squares (Chebyshev distance) away, and all of them moved their items.
  - Two repetitions completed end to end. The second walked about 29 tiles to a neighbouring house for its water.
- **`open` is live, but its `done` path is not.** Two opens were sent and both failed `locked`, on windows that every scan holding them reads `locked` true. In both rows, the `goto` that followed reached its target by another route (GUIDE § 4), so neither open was needed. This is a defect of the driver's sequence, not of the goal: `door_between` sends `open` on the planned straight line without reading the scan's `locked` flag (GUIDE § 7, cause 2). Row 3 failed on this step alone.
- **The gate is bound by the fixture.** Within r = 25 the scans saw only 4 water-like items, in 3 squares. A square picked for water is excluded for water afterwards, so at most 3 repetitions can hold a water pick. Rows 4 and 5 had none (GUIDE § 7, cause 1). **With these rules on `agent0`, `completed` cannot reach 4 whatever else goes right.** Food was not the limit: rep 5's wide scan still held 6 food items.

**Budget.** Spec § 4.2 allows 4 passes; **2 of 4 were used**. Ruling 47 stopped Stage B there. A pass 3 would change the measure, not the Lua, in two ways:
- Send `open` only when a `goto` fails, or skip a window or door the scan reads locked.
- Either let a water square be picked again while it still holds water, or give the fixture water within reach.

Without the water change, a pass 3 on `agent0` reads `completed` ≤ 3 by construction (GUIDE § 7).

### 7.4 Stage C — survival

Stage C has no gate (spec § 4.3). It ran the scripted policy on the `agent` fixture (Zombies = 5), with a bat spawned and equipped by the harness (`c_grade.txt` `start_kit_armed` true in both runs).

**Run 1** (`c_survive-20261026-183905`).

- **The death.** `c_grade.txt` `outcome` **died**, `survival_s` 407.43744254112244. The character died at `stop.gameMin` 670, 109 game minutes into the loop on a 90-minute day (GUIDE, "The stop").
  - It died of zombie damage. At the last decision, hunger, thirst and fatigue read 0.062, 0.055 and 0.109 (GUIDE, "The stop").
  - **No `eat`, `drink` or `sleep` goal was ever sent** (GUIDE § 1).
- **The loop held.** It ran 795 planner ticks and sent 45 goals, and every goal was acked and seen to end (`decisions_per_min` 6.626784183506872, `ticks_per_min` 117.07318724195474). `lua_errors_max_per_min` was 0, and the server answered 7 of 7 polls (GUIDE § 5).
- **`loot` worked.** 16 of 21 loots moved items. Three failed `not adjacent` on `solidTrans` neighbours: Stage B pass 1's neighbour rule, recurring live (GUIDE § 3).
- **`fight` and `flee` ran live for the first time, and neither ever ended `done`** (GUIDE § 3).
- **The four policy defects**, as ruling 45 names them, with the guide's evidence (GUIDE § 4):
  1. *No disengage radius* and 2. *no fight/flee hysteresis.* A zombie hovering at the 6-tile `DANGER_R` edge flipped the policy between flee and fight 8 times in 7.6 s.
  3. *A fight that is never re-evaluated.* Fight 27 stood for 210.1 s while a zombie waited at 2.74 tiles. Endurance fell from 0.951 to 0.318.
  4. *The pair-of-threats health rule.* The policy held fight 44 against two grabbing zombies until health fell under 40. That fight took health from 74.77 to 39.67 in 33.6 s.
- **The two Lua defects** (ruling 46; GUIDE § 4):
  - The `fight` goal only swings within 3 tiles and has no approach step.
  - The `flee` goal walked: `running` and `sprinting` read false on all 92 of its frames. The two zombies stayed 0.72–1.78 tiles behind it until the death.
- **An unexplained health fall** (GUIDE § 4). Over game minutes 574–587, health fell from 100 to 74.55 while the character looted, with no zombie within 12 tiles on any frame. The run's files do not show the cause.

**Pass 2** (`c_survive_2-20261026-195516`): the policy at `2715fdae`, the Lua at `704317f9`.

- **What changed** (GUIDE, "How to read it"):
  - *Hysteresis.* While a fight or flee runs, a zombie counts as a threat within `DISENGAGE_R` 10 tiles instead of 6.
  - *A stricter pair rule.* With two threats and health under 60, the bot flees (`pair`).
  - *A turn back to fight* needs a single threat and health of at least 60.
  - *A stall clock.* A fight flees after 20 s out of reach.
  - *The fight's approach.* It steps to the held weapon's reach before swinging.
  - *The flee's run.* It asks to run every tick.
- **The death, sooner.** `c_grade.txt` `outcome` **died**, `survival_s` 118.99958086013794. The character died at `stop.gameMin` 593, 32 game minutes into the loop.
  - It died of zombie damage, pinned in the open by three zombies, with needs under 0.02 (GUIDE, "The stop").
  - The loop ran 230 planner ticks and sent 25 goals (`decisions_per_min` 12.605086414236814, `ticks_per_min` 115.96679501097869). As in run 1, every goal sent was acked and seen to end.
- **What the fixes changed** (GUIDE §§ 2–4):
  - **The flap is gone.** The encounter took 5 threat goals, 3 of them superseded, against run 1's 10 superseded threat goals.
  - **The fight closed.** Fight 23 reached 0.48 tiles within about 2.4 s, and the stall clock never read above 2.0 s. No kill is read, and the frames cannot show a swing.
  - **The pair rule fled at health 59.93**, where run 1's fight held on down to 39.67.
- **Fights.** `c_grade.txt` `fights.count` 2, both ending `failed:superseded`. They lasted 0.54 s and 9.14 s, against run 1's 7 fights of 0.6–210.1 s.
- **What still failed** (GUIDE, conclusion):
  1. **The disengage radius widened the threat count.** On the tick after the first fight was sent, the count read 3 instead of 1, so the bot fled from a single zombie at 5.23 tiles. Ruling 49 names this the first fix of any third run.
  2. **The flee is flagged as a run but moves at a walk's pace.** `running` and `sprinting` read true on all 154 flee frames. Yet it moved at 1.588 and 1.402 tiles/s, against 1.591 tiles/s for a `goto` in the same run, and run 1's walking flee read 1.471 tiles/s. The zombies stayed within 0.46–1.54 tiles and pinned the character twice: one `cornered` at health 35.44, and one at the death. The frames do not show what drives the gait.
  3. **The looting fall recurred exactly** ("The looting fall, traced"):
     - Health fell from 100 to 74.56 over game minutes 568–578, with no zombie within 8.48 tiles and no window square crossed.
     - Every drop was a whole multiple of about 0.39.
     - The fall began at the 37th inventory item, a `Base.Shorts_LongDenim`. Run 1's fall began at the same item count and the same item.
     - It ended at the same health as run 1's (74.56 here, 74.55 there), after a loss of about 25.4 in each run.
     - Its cause is not read. The guide names the frame fields that would decide it: per-body-part damage, carried weight against carry capacity, and an encumbrance moodle. It refutes the driver docstring's reading ("looting with its back turned"): this fall came before any zombie came within 8.48 tiles and before any fight was sent.
- **Both survival runs shared two findings** (`c_survive-20261026-183905/GUIDE.md` § 1, `c_survive_2-20261026-195516/GUIDE.md` § 1):
  - **The needs were not exercised.** No `eat`, `drink` or `sleep` was sent in either run, so in survival those goals are unread.
  - **The policy did not count the loot as food.** `world.py`'s `FOOD_RX` puts `\b` after each name, so it misses `Base.CannedMilk`, `Base.TinnedSoup` and `Base.Macandcheese`. The policy's held-food list read `[]` while those items were in the inventory.
- **The dense run did not run.** Spec § 4.3 runs it only after a run survives, and both runs ended in a death (`c_survive_2-20261026-195516/GUIDE.md` § 6).
- **Budget.** Spec § 4.3 allows 3 runs; **2 of 3 were used**. Ruling 48 stopped there: a third run without a diagnosed cause for the fall, and without a flee that outpaces the zombies, would read the same.

### 7.5 The cost of the whole loop

| Quantity | Reading | Source |
|---|---|---|
| Frame tick mean at 60 Hz (the five measured spans; a mean of a 1 ms clock, not one tick, not the tail) | 0.794 ms over 1800 frames (pass 3: 0.482) | `a_pipe_4-20261026-181848/a_grade_4.txt` `tick_mean_ms_at60`, `tick60_frames` |
| Frame tick at 5 Hz, idle | p50 1, p99 2, max 3 ms; mean 0.777 | `a_pipe_4-20261026-181848/GUIDE.md` § 2 (`readings.rates.5`) |
| Per-tick cost across the survival loop at 5 Hz, run 1 | p50 1, p99 2, max 7 ms; mean 0.786 over 2080 frames | `c_survive-20261026-183905/c_grade.txt` `cost_p50`, `cost_p99`, `cost_max`, `cost_n`; mean from `GUIDE.md` § 5 |
| Per-tick cost across the survival loop at 5 Hz, pass 2 | p50 1, p99 2, max 6 ms; mean 0.845 over 645 frames | `c_survive_2-20261026-195516/c_grade.txt` `cost_*`; mean from `GUIDE.md` § 5 |
| The tail in the survival loops | run 1: 5 of its 7 frames of 4 ms or more directly follow an `ack`, on the tick that reads a new command and starts its goal (`pollMs` 4–5); pass 2: its one frame over 3 ms (6 ms, `pollMs` 5) likewise | each Stage C `GUIDE.md` § 5 |
| r = 15 scan, worst tick | 7 ms | `a_pipe_4-20261026-181848/a_grade_4.txt` `scan15_ms_max` |
| r = 15 scan, latency (walk plus every emit, ungraded) | 117 ms max | `a_grade_4.txt` `scan15_latency_ms_max` |
| r = 15 and r = 25 scans, ack → done part, client clock | 794–800 ms over 49 ticks, and 2156–2163 ms over 131 ticks | `b_actions_2-20261026-194009/GUIDE.md` § 5 |
| Ack → first move, p90 | 195 ms (within one to two 100 ms frame periods) | `a_pipe_4-20261026-181848/a_grade_4.txt` `cmd_move_p90_ms` |
| Bytes written per minute | 88350 at 2 Hz, 220784 at 5 Hz, 442210 at 10 Hz | `a_pipe_4-20261026-181848/GUIDE.md`, "How to read it" (`state_bytes_end − state_bytes_start`) |
| Planner rate | 117.07 and 115.97 ticks a minute against `PLANNER_HZ` 2 (120 a minute) | each Stage C `c_grade.txt` `ticks_per_min` |
| Lua errors | 0 in all five runs | `a_grade_4.txt` `lua_errors`; each Stage B `GUIDE.md` § 6; each Stage C `c_grade.txt` `lua_errors_max_per_min` |

The survival loop's goals, scans and nearby zombies left the 5 Hz frame cost where Stage A's idle 5 Hz window put it: the same p50 and p99, and means of 0.777–0.845 ms. Only the tail grew, on goal-start ticks.

### 7.6 Recommendation, restated

**Go-with-changes, as a tool for driving a character in a test. Not yet as a survival agent.**
- **The pipe holds.** Across the eight boots of Plans 21 and 21b the link read 0 gaps and 0 Lua errors, in append mode wherever a guide reads the mode (§ 1; § 7.5; the Stage B guides' § 6; the Stage C guides' gapless `state.log`).
- **The ack-to-walk responds within one to two frame periods.**
- **The mean frame cost stays under 1 ms**, measured with the run unable to tell its own Lua from the host.
- **Four goals do their job live:** `goto`, `loot`, `eat` and `drink` (§ 7.3). An eat lands on the server every time.
- **These are what a nutrition-mod test would drive.**
- **Survival is the open part.** The scripted bot died twice, both times to the goal layer's combat (a flee no faster than a walk) and to one policy rule, and once more to a health fall the frames cannot name.

**Spike D** (an LLM planning over `summary.py`'s view) is **still not worth running**. A baseline now exists, 407.4 s and 109 game minutes of loop in run 1 and 119.0 s and 32 game minutes in pass 2 (each Stage C `c_grade.txt` `survival_s`; `stop.gameMin` 670 and 593). But the two deaths were decided mostly below the planner (the one policy defect, ruling 49, is the exception):
- the flee cannot outpace the zombies;
- the ~25-point looting fall precedes any choice an LLM would make.

An LLM choosing among the same goals would meet the same floor. The needs, the part of survival a nutrition mod cares about, were never exercised. Revisit spike D once a scripted run lives long enough to send `eat`, `drink` and `sleep`.

**The next changes, in order of value:**

| # | Change | Size |
|---|---|---|
| 1 | **Trace the looting fall.** Add per-body-part damage, carried weight against carry capacity, and an encumbrance flag to the frame (the fields `c_survive_2-20261026-195516/GUIDE.md`, "The looting fall, traced", names). | A `PZAgent_Sense.lua` change and its offline tests; read on the next Stage C run. Each new member is checked in the jar first. |
| 2 | **Make the flee outpace a walk.** The run flags are set and the pace is a walk's; the frames do not say what drives the gait. | A jar read first, then a Lua change and its tests. |
| 3 | **Fix `DISENGAGE_R` widening the threat count** (ruling 49): the hold uses 10 tiles, and the count rules keep 6. | A `policy.py` edit and its tests. |
| 4 | **Fix `FOOD_RX`** so that `CannedMilk`, `TinnedSoup` and `Macandcheese` count as held food. Without it the `need` branch cannot eat what the loot brought back. | A `world.py` regex and its tests. |
| 5 | **The third Stage C run**, after 1–4: the last of the spec's 3 runs. | One detached session of up to about 95 minutes. |
| 6 | **Stage B pass 3**, if Angus wants the completion gate itself: `open` only when a `goto` fails or the scan reads the window unlocked, plus either a re-pickable water square or a stocked fixture. | A driver change and one session of about 6 minutes (ruling 47). |
| 7 | **Measure the scan tail before any fallback**: for example, emit fewer bytes per square, or probe a single write's cost by line size. | A Lua constant or a probe, then one Stage A session. |

**The JVM fallback's status.** Its condition is met, because the 20-square pass failed its scan gate (§ 7.2). It is **not recommended**. The failing cost is a client-side stutter on a few ticks of an r = 15 scan, and no artifact measures a socket, a JVM agent or a server-side scan. Change 7 would decide whether the stutter needs one.

### 7.7 Decisions taken

Plan 21b's rulings, verbatim, are appended to § 5 as items 35–49: the four P21b rulings from the plan file, then the ledger's `Ruling:` lines in order.

Model: claude-opus-5-5
