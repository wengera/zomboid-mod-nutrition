# Plan 22: the agent base — report

Plan 22 rebuilt Plan 21's file-linked agent as candidate K1. It has a thin Lua motor and sensor, a typed protocol (`PZA/1`) generated from one schema, every multi-step policy in Python, and a transport seam that could take a sidecar later (spec `docs/superpowers/specs/2026-10-27-plan-22-agent-base-design.md` § 1). On 42.21 the base works as a channel: across the four sessions this plan booted (X4, X5 and two acceptance runs), the pipe read 0 gaps, 0 Lua errors and 0 parks. A `walkTo` moved within 128–181 ms of its accept line. The kept map held all 43 walls, doors, windows and containers that a second scan found. The client's copy of a zombie's health matched the server's to the third decimal. Under the Python survival planner one character lived 64.70197677612305 game minutes and killed five zombies. Plan 21b's Stage C pass 2 lived 32 (its run 1, before the policy fixes, 109; § 4). Still, nothing in the plan ended GO:

- **X4 graded NO-GO** on its two cost gates. The 60 Hz tick mean read 1.672203765227021 ms against < 1, and the worst tick 19 ms against ≤ 3. The cost sits in the base's own per-tick sense read and map watch, and in a burst on every command's accept. It does not sit in the emit: the sidecar trigger did not fire (ruling S-18).
- **The acceptance's run 2 died** of zombie wounds, explained by the frames. Run 1 was stopped by the instrument at 134 game minutes, alive (ruling S-24).
- **The needs were never exercised.** No `consume` was sent in either run.

Paths below are relative to `testing/artifacts/` unless they begin with `docs/`, `testing/` or `tools/`. A guide line `GUIDE.md:<n>` is that guide's line at commit `3c0e33f1`. Two fix rounds edited guides in place and appended `## Corrections` sections, so no cited line moved: `a38424ae` and `acaa5986` (Plan 22 Task 16 fix 1) edited the X4 and X5 guides, and `f411a698` and `3c0e33f1` (the Task 19a fix round) edited the two acceptance guides. Every other guide is unchanged since `a8a5d8ae`. A row `#NNNN` is `docs/reference/claims.tsv` at `3c0e33f1`. "Ledger L<n>" is a line of `.superpowers/sdd/2026-10-27-plan-22-agent-base/progress.md` (gitignored), and a task report is that workspace's `task-N-report.md`.

| Session | Folder | Graded by | Verdict |
|---|---|---|---|
| Probe (X1 motor, X2 bench, X3 load; the design wave) | `p22_probe-20261027-032502` | the driver's `verdicts` | no gate (#4197–#4202) |
| X4, the link | `x4_link-20261027-171916` | `gate_x4` (`x4_grade.txt`) | **NO-GO** on `tick_mean_at60` and `worst_tick` (`x4_link-20261027-171916/GUIDE.md:173`) |
| X5, combat | `x5_combat-20261027-173248` | `measure_x5` | no gate: a measurement with pass lines (`x5_combat-20261027-173248/GUIDE.md:163`) |
| Acceptance run 1 | `d_survive-20261027-173724` | `grade_d` (`d_grade.txt`) | undecided: the instrument stopped it (`d_survive-20261027-173724/GUIDE.md:90`) |
| Acceptance run 2 | `d_survive-20261027-175917` | `grade_d` (`d_grade.txt`) | died, explained by the frames (wound arm) (`d_survive-20261027-175917/GUIDE.md:85`) |

X4, X5 and both acceptance runs ran the same Lua: PZAgent 1.0 on `PZA/1`, at `c8493a0e` (`x4_link-20261027-171916/GUIDE.md:3`, `x5_combat-20261027-173248/GUIDE.md:3`, `d_survive-20261027-175917/GUIDE.md:3`).

## 1. What the base is now

**The schema: one file, three generated targets.** `testing/agent/base/schema/pza1.json` (720 lines) is the one source of `PZA/1`. `tools/pza_schema.py` (712 lines) renders three targets from it: the Lua header `PZAgent_Schema.lua`, the Python module `testing/agent/base/pza1.py`, and the LLM tool descriptions `testing/agent/base/schema/tools.json`. `--check` exits 1 when any target differs from a fresh render (the tool's docstring, L1–L12). Counted from the file:

- **6 line kinds** (`x-kinds`): `hello`, `frame`, `map`, `event`, `act`, `reply`.
- **8 frame groups**: `me`, `stats`, `body`, `load`, `weapon`, `action`, `act`, `cost`.
- **5 records**: `part`, `zombie`, `square`, `portal`, `container`.
- **8 event kinds**, **10 action types** and **20 reasons** in the closed `reason` enum.
- 3 gaits and 59 `$defs` in all.

`tools.json` holds one tool per action type, 10 in all. Spec § 4 also named the fake mod's validators and a generated `reasons.py` among the generator's targets. As built, the reason set lives in the generated `pza1.py` as `REASONS` (L54). The fake mod writes every line through `pza1.encode` and checks commands against `ACTION_ARGS` with its own code (`testing/tests/pzagent/fakemod.py` docstring). Plan 21's `testing/agent/reasons.py` stays, frozen (P22-0).

**The protocol.**
- `frame` and `map` lines are positional: arrays in the schema's `x-order`. The other four kinds are keyed JSON.
- Every line carries the envelope `kind`, `seq`, `tick` and `wallMs` (ruling S-7), and `seq` rises in file order (ruling S-11).
- A delta frame elides a group whose encoding equals the last one sent, writing it as `true`. `zombies` is never elided, and a full frame goes out every `L.FULL_EVERY = 10` frames (P22-3; base rule S-6).
- `cmd.txt` and `ack.txt` each hold one JSON line (ruling S-5).
- The map budget is 1.5 KB of positional bytes a tick (`L.BUDGET_BYTES = 1536`; plan, Global Constraints, spec § 8).

**The Lua** (`testing/PZAgent/PZAgent/42/media/lua/`). Line counts are by `wc -l` at `a8a5d8ae`. The last commit under `testing/PZAgent` is `c8493a0e` (Plan 22 Task 9 fix 2), the Lua every session ran:

| File | Lines | Job (plan, Architecture) |
|---|---|---|
| `shared/PZAgent_Core.lua` | 205 | `PZA.call`/`PZA.field`, the keyed JSON encoder, the JSON decoder for `cmd.txt` |
| `shared/PZAgent_Schema.lua` | 319 | generated: field orders, enums, the positional encoders `PZA.enc.*` (ruling S-1) |
| `client/PZAgent_Link.lua` | 261 | one buffer, one flush a tick, the byte budget, the backlog, overflow |
| `client/PZAgent_Main.lua` | 169 | the tick order, `hello`, the `scan` and `rate` commands (P22-5), the `cost` group |
| `client/PZAgent_Map.lua` | 272 | the scan job and the watch's dirty set |
| `client/PZAgent_Motor.lua` | 56 | the `OnPlayerUpdate` gait: `setForceRun`/`setForceSprint` re-asserted every frame (#4197, #4198) |
| `client/PZAgent_Sense.lua` | 509 | the frame and the events |
| `client/PZAgent_Skills.lua` | 922 | the typed one-step actions and their runner |
| total | 2713 | |

**The Python** (`testing/agent/base/`, line counts at `a8a5d8ae`):

| Module | Lines | Job (its docstring) |
|---|---|---|
| `pza1.py` | 336 | generated: kinds, orders, enums, `encode`, `decode`, `merge_delta`, the command dataclasses |
| `transport/__init__.py` | 30 | the `Transport` protocol (`send(cmd)`, `lines()`, `gaps`, `bad`, `cmd_seq`) and the sidecar designed in six lines (L6–L11) |
| `transport/files.py` | 144 | `FileTransport`: tails `state.log`, decodes, merges deltas (S-6), writes `cmd.txt` |
| `actions.py` | 134 | typed sends: `sent → accepted → progress* → done/failed`, `rejected`, `timeout` |
| `world.py` | 281 | `World`, a pure function of the lines: frame groups, zombies, the map, inventory, server damage |
| `planner/__init__.py` | 18 | the `Planner` protocol: "scripted policies now, an LLM tool-caller later" |
| `planner/policies.py` | 281 | `Fight`, `Flee`, `Explore`, `LootHouse` over the one-step skills |
| `planner/survive.py` | 252 | `Survive`: threat, need, forage, explore; no sleep (P22-1); `decision.log` |
| `gates.py` | 574 | `gate_x4`, `measure_x5`, `grade_d`; the sidecar trigger stated before X4 |

**The transport seam.** `FileTransport` is the one built transport. The sidecar is designed in six lines (`transport/__init__.py` L6–L11):
- a `SocketTransport` with the same two methods;
- one `PZA/1` line per datagram, or newline-framed over TCP;
- the same decode and delta merge;
- the same seq guard and command line;
- "built only if X4 fires its trigger".

**The ten action types.** `attack`, `consume`, `drop`, `equip`, `interact`, `rate`, `scan`, `steer`, `stop` and `walkTo`, the `caps` of every session's `hello` (`x4_link-20261027-171916/GUIDE.md:10`). Fight, flee, explore and loot-house are Python policies (spec § 5).

**The two harness commands** were added at `e4d5b71b` (`x5_combat-20261027-173248/GUIDE.md:3`). Both are in `docs/reference/harness-commands.md`:
- `damage.watch <user> [since <i>]` (L25) gives per-tag `OnPlayerGetDamage` counts and the last 200 records. It is the one server listener (spec § 9).
- `zombie.get <onlineId>` (L160) is a server read of one zombie (P22-7).

**The test base** (`testing/tests/pzagent/`):
- **The fake mod** `fakemod.py` writes every line through `pza1.encode`.
- **The fault test** `test_lua_faults.py` runs every skill against a bare player, a raising player and absent vanilla classes. It asserts that nothing raises out of the runner or `S.frame` (ruling S-15; its docstring).
- **The encoder property tests** in `test_pza1.py`: 200 random frames (L76) and 200 random maps of 0–40 squares (L85) round-trip through `encode`/`decode`.
- **The replay test** `test_base_world.py` L348 replays a synthetic fixture log (`fixtures/pza1-synthetic-1.log`) to its committed JSON byte for byte. Spec § 10 asked for "golden replays of every live run's `state.log`", but no test in the folder replays a live run's `state.log`; the drivers' tests use the artifact paths only for their pre-boot checks (a reading of the test files).
- **The counts.** The full suite at `a9513b21` read "9331 passed, 28 skipped, 3300 subtests passed" (`full-pytest-a9513b21.txt` L131) against the plan's baseline of 8840 passed. The `testing/tests/pzagent` folder at `6925886d` read "976 passed" (`task-18-fix-1-pytest-folder.txt`).
- **The reset.** 153 collected ids left the suite between `ba5c4024` and Task 6 (`task-6-report.md` L141–L151). Of them, 10 are `test_lua_bench.py`'s, 109 are `test_lua_act.py`'s (101 tests, counted per parametrized case) and 4 are `test_b_actions.py`'s static tests: the deleted tests of the removed Lua. The rest were rewritten or moved. Their names are in the Appendix.

**The drivers and gates**, each frozen once its run took place (spec § 2):
- `testing/agent/drivers/x4_link.py` (608 lines) and `x4_grade.py` (37), graded by `gate_x4`.
- `x5_combat.py` (843), reported by `measure_x5`.
- `d_survive.py` (906) and `d_grade.py` (49), graded by `grade_d`.
- All of them sit on `_dlib.py` (105).

`gate_x4` is frozen now that an artifact carries its output (`x4_link-20261027-171916/GUIDE.md:3`), and a second X4 pass gets a `gate_x4_2` (ruling S-18). `d_survive.py` ran twice unedited; run 2 differed by the `files.py` fix `6925886d` alone (`d_survive-20261027-175917/GUIDE.md:3`).

**What Plan 21's layer still does (P22-0).** `testing/agent/link.py`, `world.py`, `policy.py`, `reasons.py`, `summary.py`, `grades.py` and `grade_c.py` stay in place, frozen with the drivers that import them. Those drivers are `a_pipe*.py`, `b_actions*.py`, `c_survive*.py`, `p22_probe.py`, `a_grade*.py`, `b_grade.py` and `c_grade.py` (the plan's Global Constraints). Their tests (`test_link.py`, `test_world.py`, `test_policy.py`, `test_summary.py` and the drivers' tests) still run in the folder. Nothing in the new base imports them.

## 2. The cost of each layer (X4)

Every `cost` field is an integer span on the 1 ms `getTimestampMs` clock (P22-4). A single reading is a bound. A mean over many readings is the clock's mean of the measured span (`x4_link-20261027-171916/GUIDE.md:34`).

In X4, `tickMs` times the **previous tick's whole body**. Pass 4's `tickMs` was the **sum of its five measured leaves** (`x4_link-20261027-171916/GUIDE.md:31`; `a_pipe_4-20261026-181848/GUIDE.md:23`). So the two tick means are not one quantity on one instrument; the named spans are the comparable part.

| Quantity | X4 (`x4_link-20261027-171916`) | Plan 21b pass 4 (`a_pipe_4-20261026-181848`) | Probe X2 bench (`p22_probe-20261027-032502`) |
|---|---|---|---|
| Tick mean at 60 Hz | **1.672203765227021 ms** over 1806 frames; p50 2, p99 3, max 9 (`GUIDE.md:40`; #4203) | 0.794 over 1800, the five leaves' sum, max 7 (`GUIDE.md:83`) | — |
| sense (events and frame read) | 0.7115171650055371 (`GUIDE.md:46`) | `senseMs` 0.167 (`GUIDE.md:81`) | — |
| map watch / scan step | 0.3449612403100775 (`GUIDE.md:47`) | `scanStepMs` 0.004, standing (`GUIDE.md:80`) | — |
| flush (`linkMs`) | 0.2691029900332226, worst 2 (`GUIDE.md:48`, `GUIDE.md:75`; #4204) | `linkMs` 0.339 (`GUIDE.md:82`) | open + 2740 B write + close 138 µs (`GUIDE.md:114`; #4200) |
| skills (`actMs`) | 0.0005537098560354374 (`GUIDE.md:49`) | `actMs` 0.003 (`GUIDE.md:79`) | — |
| unattributed (the poll, the frame's positional encode, an act line's encode, the timers) | 0.3462603878116344 (`GUIDE.md:52`) | `pollMs` 0.281 (`GUIDE.md:78`) | poll 54 µs (`GUIDE.md:102`); positional encode 148 µs for 1244 B (`GUIDE.md:113`) |
| Worst tick | **19 ms**, one of ticks 1–4: the init or the watch's first ticks; `over5` 31 over 600.066 s (`GUIDE.md:54`, `GUIDE.md:70`; #4207) | 60 Hz max 7 (`GUIDE.md:83`); r = 15 scan worst 7 (`GUIDE.md:34`) | — |
| Command bursts | all 24 commands (2 `rate`, 2 `scan`, 20 `walkTo`) fell in a window whose worst tick read 5–9 ms; the `rate` 60 tick 182 read 9, of which 7 are unattributed (`GUIDE.md:60`, `GUIDE.md:70`; #4207) | — | — |
| A 20-square scan part | 1150–1689 bytes positional; a part's flush read `linkMs` 0 on 8 and 1 on 8, which bounds it near half a millisecond without measuring it (`GUIDE.md:80`) | 2102–2103 B of JSON, 1.67 ms emit (`GUIDE.md:60`) | `PZA.json` 1250 µs for 2740 B (`GUIDE.md:95`) |
| r = 15 scan | 49 parts, 961 squares in 0.828 s; the window holding the scan command and its first five parts read 8 (`GUIDE.md:84`, `GUIDE.md:62`) | worst tick 7, latency 117 (`GUIDE.md:34`, `GUIDE.md:36`) | — |
| ack/accept → first move | p50 146, p90 **165**, 128–181 ms over 20 legs, all `done` (`GUIDE.md:128`; #4206) | `cmd_move_p90_ms` 195, 110–220 ms (`GUIDE.md:38`) | — |
| Pipe | 0 gaps, 0 bad, 0 Lua errors, 0 parks, `dropped` 0 on every frame (`GUIDE.md:11`) | 0 gaps, 0 Lua errors (`GUIDE.md:32`) | — |

**What the tick is made of.** Pass 4 read sense 0.167 ms. X4 reads 0.7115171650055371 ms for the sense read and 0.3449612403100775 ms for a map watch that Plan 21 did not run (spec § 6). Together these two hold **1.0564784053156147 ms** of the 1.672203765227021 ms mean (`x4_link-20261027-171916/GUIDE.md:52`). The flush, which was the emit's cost in Plan 21b, fell from pass 4's 0.339 to 0.2691029900332226. The X2 bench predicted this: the JSON encoder held 74.85 % of pass 4's 1.67 ms emit, and a positional encoder costs about an eighth of it (`p22_probe-20261027-032502/GUIDE.md:111`, `GUIDE.md:113`; #4200).

**The flush against the sidecar trigger** (spec § 8 (6): fire on an emit above 1 ms mean or 3 ms worst per tick at the budget):
- **The gate's reading** averages `linkMs` over the 486 frames reading above 0: mean 1.0576131687242798, worst 3, so `sidecar_trigger` reads "fired" (`x4_link-20261027-171916/GUIDE.md:74`). On the 1 ms clock a mean over the readings above 0 is at least 1 by construction (`GUIDE.md:34`).
- **The window's reading.** Over the 60 Hz window every tick flushed: mean **0.2691029900332226 ms**, worst **2** (`GUIDE.md:75`; #4204).
- **The emit with its encode is bounded, not measured.** The frame's encode is untimed. The flush plus the tick's unattributed remainder bounds the emit at a mean of 0.6155124653739612 ms. Its worst is 3 on twelve ticks and 8 on tick 182 alone, the `rate` 60 command's tick (`GUIDE.md:76`; #4204).
- **Ruling S-18** reads the trigger as **not fired**: the gate's "fired" is the clock's artifact, and the window's mean and worst are under 1 ms and 3 ms (ledger L128). The guide agrees on the flush, and on the bound everywhere but tick 182 (`GUIDE.md:78`).

**The map.**
- The kept map held 6 of 6 walls, 3 of 3 doors, 13 of 13 windows and 21 of 21 containers that the final scan found: ratio 1.0 on all 43 features, a door opened during the walk included (`x4_link-20261027-171916/GUIDE.md:94`–`GUIDE.md:99`; #4205).
- The final scan's window was shifted. 91 of its 961 squares were never in the kept map, so square coverage was 870 of 961. None of the 91 carries one of the four kinds, so each kind's `absent` reads 0 (`GUIDE.md:90`).
- The watch sent one delta during the walk, the door's change (`GUIDE.md:86`).

**The verdict.** `gate_x4` reads **NO-GO** on `tick_mean_at60` (1.672203765227021 against < 1.0) and `worst_tick` (`tickMaxMs` 19, `over5` 31, against ≤ 3 and 0). It reads GO on `gaps`, `lua_errors`, `parks`, `cmd_move_p90` (165 < 500) and `map_kept` (`x4_link-20261027-171916/GUIDE.md:165`–`GUIDE.md:173`).

**Ruling S-19** carried the plan on to X5 and the acceptance as go-with-findings (ledger L129). The plan's one X4 fix pass, `x4_link_2.py` graded by the same `gate_x4`, has **not run**. Per S-19 it runs after the consolidated fix wave, which has not run either, so that the re-measure reads the fixed base once. Its content, as S-19 and the guide name it:
- **the watch's per-tick budget at 60 Hz**: the sense read and the map watch every tick, 1.0564784053156147 ms of the mean;
- **the init burst**: the 19 ms tick within ticks 1–4;
- **the command-accept burst**: every command's 5–9 ms window, with 7 ms of tick 182 unattributed. No field times the poll, a command's start or an act line's encode, so the burst has no cause in the artifact (`x4_link-20261027-171916/GUIDE.md:135`).

**The cost under the planner** (10 Hz frames, the frame tick read in `tickMaxMs` and `over5`):
- **Run 1:** `tickMaxMs` 16 in the first frame's window (ticks 1–6: the init and the first sight); `over5` 185 over 183 frames. 147 of 181 commands fell in a 5–11 ms window, and 28 of the 183 slow windows hold no line (`d_survive-20261027-173724/GUIDE.md:94`).
- **Run 2:** `tickMaxMs` 18 in the first frame's window (ticks 1–6: the init and the first sight); `over5` 457 over 443 frames. 125 of 149 commands fell in a 5–14 ms window, and **229 of the 443 slow windows hold no line** (`d_survive-20261027-175917/GUIDE.md:139`; #4213).
- That window holds the hello, 32 `map` lines and 8 `item_added` events, so the frames do not pin either tick to the init, as X4's #4207 left its own 19 ms (`d_survive-20261027-173724/GUIDE.md:94`; `d_survive-20261027-175917/GUIDE.md:139`).
- Each guide classes its slow windows exclusively, by the first kind each holds. Run 1: 145 hold an accept line, 8 a `map` line, 1 an act's end and 1 an event, 183 in all (`d_survive-20261027-173724/GUIDE.md:94`). Run 2: 122 accept, 53 `map`, 18 end, 13 event and 8 `progress` only, 443 in all (`d_survive-20261027-175917/GUIDE.md:139`).
- On the same Lua, run 2's `senseMs` mean read 1.5794209702660407 ms against run 1's 0.9645982498011137, with 1.54 GB free at ready. The frames do not separate the host, the map deltas and the zombies as the cause (`d_survive-20261027-175917/GUIDE.md:139`, `GUIDE.md:16`).

## 3. The actions (X5)

X5 gave the agent a bat through `equip`, spawned one zombie a tile away for each of up to five encounters, and let the Python `Fight` (5 Hz) attack. The driver read the target from the server before each send and after each end (`x5_combat-20261027-173248/GUIDE.md:5`). It stopped on its own health rule at 49.84945297241211 in encounter 3, with three encounters run (`GUIDE.md:14`).

| Reading | Value | Source |
|---|---|---|
| `attackStarted` share | **10 of 15** `done` attacks (0.6666666666666666). The 5 that never started fired no `swing` event and ended 1510–1513 ms after their accept (#4210). The guide reads the skill's `SWING_MS` 1500 timeout as their end, an inference that #4210 now keeps in its bound. Distance does not separate them. | `GUIDE.md:100`; #4210 |
| `meleeDelay` (the largest read per swing) | min 0, p50 8, max 12 over 15: 12 on seven, 8 on two, 0 on six. Every `swing` event read 0 on the tick `isAttackStarted` first read true. | `GUIDE.md:102`; #4210 |
| The client's copy against a server read | **15 of 15** unvoided pairs within 0.5, read 6.0–45.5 ms apart; the largest difference **0.0009746551513671875**; three pairs equal to every digit. 2 pairs voided: the kill and a rejected attack. | `GUIDE.md:104`; #4208 |
| Kills | 1 of 3 encounters: encounter 1's zombie 9932, killed by a12 (`targetDead` true, `zombie_dead` at seq 759) | `GUIDE.md:56` |
| Health lost | 13.808998107910156 (encounter 1) and 33.297000885009766 (encounter 3): the instrumented fight's, not the agent's | `GUIDE.md:52`, `GUIDE.md:123` |

**The two copies.** The differences are a three-decimal rounding carried forward: a hit lands the same amount on both copies, and the server's copy later reads the client's value rounded. Which side rounds, and through what, the replies do not name (`x5_combat-20261027-173248/GUIDE.md:106`–`GUIDE.md:108`). So the client's copy of zombie health is the planner's to read. Spec § 13 left it open; X5 answers it on n = 1 (#4208).

**The loop latency.** From the first frame listing a new zombie to the accept line of the first attack, the raw loop read 2040 and 2236 ms. The driver's own synchronous `zombie.get` before the send held 2011 and 2019 ms of that, leaving a net of 29 and 217 ms (`x5_combat-20261027-173248/GUIDE.md:116`–`GUIDE.md:119`).

The net is not all the agent's: during a bus step the driver neither pumps frames nor ticks the `Fight`.
- **Encounter 1.** The `zombie.near` step returned at the sight frame's own millisecond, so the 29 ms is the agent's.
- **Encounter 3.** The sight frame came 53 ms into the step, and the step returned 205 ms after it.

**The agent's own loop read 29 ms in encounter 1 and 12 ms in encounter 3** (`GUIDE.md:119`; #4209): the frame read, the `World`, a 5 Hz `Fight` tick, the `cmd.txt` write and the Lua's poll and accept. Ruling S-26 allows this subtraction of the instrument's own wait, never cited as a reading of the game (ledger L163). The raw `measure_x5.loop_ms` (p50 2040, p90 2236) is barred from citation as the agent's latency (`GUIDE.md:183`).

**The instrument's cost.**
- The driver's docstring priced each server round trip at about 0.3 s. Before a swing they read 2011–2019 ms on 11 of 17 attacks and 759–1762 ms on the other 6; after a swing's end, 257–1511 ms. Over 48 bus steps the mean was 1.1881458333333332 s (`x5_combat-20261027-173248/GUIDE.md:121`). #1862's 0.3 s bus round trip, an unverified reading from a quiet restored-fixture run, did not hold under combat.
- During those reads the driver neither pumped frames nor ticked the `Fight`. Consecutive attack accepts lay 2098–4098 ms apart, and the zombies hit between swings, so **`health_lost` measures the instrumented fight** (`GUIDE.md:123`).

**The voided encounter** (ruling S-22). The server spawned encounter 2's zombie at 1.35 tiles, inside `S.ZOMBIE_RADIUS` 12, and **no frame listed it under any id**. The frames name the gap but not its cause, and no server read names the zombie (`x5_combat-20261027-173248/GUIDE.md:58`).

**Encounter 3 fought the wrong zombie.** The `Fight` attacks the nearest zombie. That was the fixture's own 9833 at health 3.509999990463257, not the spawned 9934, so encounter 3's approach series, `killed` false and `server_end` all describe 9934, which was never attacked (`x5_combat-20261027-173248/GUIDE.md:60`).

**Where the fight reflex sits, and why** (ruling S-21, ledger L135). The reflex stays in **Python**. The ruling rested on a loop of 29 and 217 ms net, and a 2 Hz planner adds at most 500 ms, which is under the second or more a zombie needs to close from outside the bat's reach. The ruling is provisional on the acceptance's fights, because both X5 spawns landed inside `FIGHT_REACH` 2.0. The corrected loop, 29 and 12 ms, "leaves the ruling's direction unchanged" (`x5_combat-20261027-173248/GUIDE.md:175`).

The X5 guide qualifies S-21's premise with one approach from outside reach, by 9833 while no `Fight` ran. That zombie was inside 2.0 tiles for 1097–1298 ms before it stood at 0.5362608709767315 tiles. A 2 Hz planner plus the agent's 29 ms loop is at most 529 ms. It would have accepted its attack before contact by **568 to 769 ms** (`GUIDE.md:173`, `GUIDE.md:175`). It is one zombie, met outside a fight, and its distance on the client's copy is resolved to its steps (`GUIDE.md:173`).

The acceptance did not show the failure S-21 named as its cost if wrong, which was health lost before the first started swing:
- **Run 2.** Fights 1 and 2 ended at health 100 with every attack started (`d_survive-20261027-175917/GUIDE.md:70`, `GUIDE.md:72`). Fight 3's first stage killed three zombies with no fall (`GUIDE.md:76`). The first wound came later in fight 3 (`GUIDE.md:79`).
- **Run 1.** The character's health rose through its one fight (`d_survive-20261027-173724/GUIDE.md:69`).

So the ruling holds on these readings, which are one fixture's (n = 1).

## 4. The acceptance against Stage C

Both acceptance runs used the same driver, `d_survive.py` at `95596a91`, on fixture `agent` (Zombies 5) with a bat. The Python `Survive` planner ticked at 2 Hz.

- **Run 1** stopped on the instrument. At loop second 493.31356549263 the transport's `os.replace` of `cmd.txt.tmp` onto `cmd.txt` raised `PermissionError` on the session's 182nd command: a Windows sharing violation with the client's per-tick poll (`d_survive-20261027-173724/GUIDE.md:14`).
- **Ruling S-24** kept run 1 as an artifact and fixed the transport (`6925886d`: `FileTransport.send` retries the replace up to `REPLACE_TRIES` 50 times, `REPLACE_SLEEP_S` 0.01 s apart; `d_survive-20261027-175917/GUIDE.md:3`). Run 2 then ran the base as built: run 1's fight and stuck-walk findings were deliberately left unfixed (ledger L143).
- Whether the retry ever fired in run 2 is not read, because the artifact carries no `replace_retries` (`d_survive-20261027-175917/GUIDE.md:13`).

| | Stage C pass 2 (`c_survive_2-20261026-195516`) | Run 1 (`d_survive-20261027-173724`) | Run 2 (`d_survive-20261027-175917`) |
|---|---|---|---|
| Loop wall time | 119.0 s (`GUIDE.md:32`) | 493.31356549263 s (`GUIDE.md:35`) | 244.22170305252075 s (`GUIDE.md:35`) |
| Game minutes under the planner | 32, minutes 561–593 (`GUIDE.md:32`) | 131.17252349853516 from minute 562; 133.99852752685547 from the first frame (`GUIDE.md:35`) | **64.70197677612305** from minute 563; 68.23087692260742 from the first frame (`GUIDE.md:35`; #4211) |
| End | died: zombie damage, pinned by three zombies (`GUIDE.md:34`) | the instrument's stop, alive at 94.65937042236328; `grade_d` undecided (`GUIDE.md:90`) | died at game minute 628 of zombie wounds, explained (`GUIDE.md:112`; #4212) |
| Kills | none read (`d_survive-20261027-175917/GUIDE.md:135`) | none: no `zombie_dead` event (`GUIDE.md:15`) | five, in three fights (`GUIDE.md:68`) |
| Needs at their peak | hunger 0.019512178376317024, thirst 0.016872486099600792, fatigue 0.021534033119678497 at the last decision (`GUIDE.md:34`) | all under 0.09 (`GUIDE.md:61`) | 0.03711867332458496, 0.038536421954631805, 0.04827094078063965 (`GUIDE.md:62`) |
| The looting fall | about 25 health while looting, cause not read (#4192) | 31 falls summing 17.371551513671875 at load levels 2–4; the server heard `HEAVYLOAD` 41 times, 17.8106250166893 (`GUIDE.md:84`–`GUIDE.md:85`) | 41 falls summing 21.58819580078125; `HEAVYLOAD` 46 times, 22.161251097917557 (`GUIDE.md:64`) |
| The flee's pace | 1.402 and 1.588 tiles/s, a walk's (`d_survive-20261027-175917/GUIDE.md:135`) | no flee | 2.4209284443556203 to 2.858544156025982 tiles/s with `forceRun` true; 0.11000671853839812 and 0.10667066999222216 tiles/s when pinned (`GUIDE.md:133`) |

**Minutes lived.** Stage C's pass 2, the run after its policy fixes, read 119.0 s of loop and 32 game minutes. Stage C's run 1 had lived 109 game minutes of loop, dying of zombie damage after four policy defects (`docs/superpowers/specs/2026-10-26-agent-harness-report.md` L362, L368), so run 2 here outlived the pass, not Stage C's longest run. Run 2 lived 244.22170305252075 s and 64.70197677612305 game minutes under the planner, killed five zombies, and died the same way: a flee begun late and pinned by two zombies (`d_survive-20261027-175917/GUIDE.md:135`). Run 1 had lived 131.17252349853516 game minutes under the planner when the instrument stopped it.

**The Plan 21b findings the base answered:**
- **The flee runs.** The base's force-run (#4197) made run 2's first flee run at 2.4209284443556203–2.858544156025982 tiles/s, where Stage C's walked. `sprinting` still read false on every flee frame, `forceSprint` included, so the sprint the probe read (#4198) did not come, and the frames do not say why (`d_survive-20261027-175917/GUIDE.md:133`).
- **The looting fall is the heavy-load drain.** The frame's `load` group now reads the level. Run 1's 31 falls came at level 3 or 4, or on the first frames after the level fell to 2, with the character standing. The server heard `HEAVYLOAD` and nothing else (`d_survive-20261027-173724/GUIDE.md:84`–`GUIDE.md:86`), the drain the probe read (#4201). The `LootHouse` guard dropped one item a planner tick down to level 2, but one loot can carry the level from 2 to 4 at once (`GUIDE.md:82`).
- **`FOOD_RX`.** The base's regex now matches `CannedMilk`, `TinnedSoup` and `Macandcheese`, which Plan 21's missed. No need branch answered, so nothing was eaten (`d_survive-20261027-175917/GUIDE.md:62`).

**The fights, and what the frames show.**
- **Run 1: 103 started swings that hit nothing.** The `Fight` sent 103 `attack`s at zombie 32404. Every one ended `done` with `{attackStarted true, meleeDelay 12, swings 1, targetDead false}`.
  - The zombie's health read 1.1670000553131104 on all 1530 frames listing it. The character's health rose (`d_survive-20261027-173724/GUIDE.md:67`, `GUIDE.md:69`).
  - They stood 1.097299103652225 tiles apart on the diagonal for 1245 frames (`GUIDE.md:70`).
  - The kept map holds **a closed, locked door on the zombie's own square**, the only door, window or solid square within two squares. The square record carries no edge, so the map cannot say whether that door lay between them (`GUIDE.md:71`).
  - The fight could not end: the policy's stall clock restarts while the target is within `FIGHT_REACH` 2.0 (`GUIDE.md:72`).
- **Run 2's stand-off** with zombie 30435 repeated the pattern: ten started swings, one of which moved its health. The two stood one square apart, and the map shows no obstacle (`d_survive-20261027-175917/GUIDE.md:77`).
- **Run 1's stuck walks.** The `explore` branch sent 20 `walkTo`s to the same edge square (10742, 10642). Each failed `stuck` without a step, and each was re-sent after the cooldown's 10 null ticks, because the unexplored edge never changed (`d_survive-20261027-173724/GUIDE.md:77`, `GUIDE.md:79`).

**Run 2's death, explained.** Fight 3 ran in six stages (`d_survive-20261027-175917/GUIDE.md:74`–`GUIDE.md:81`):
1. **The first wound.** It came at seq 4346: a fall of 1.4251480102539062, `bleeding` 1, zombie 30436 at 0.7827555074141651 tiles (`GUIDE.md:94`; #4212).
2. **The wounds' rise.** The body rose to `bleeding` 7, `scratched` 3 and `bitten` 3 by seq 4697, each rise with a zombie within 0.2987403491388689–0.7827555074141651 tiles (`GUIDE.md:105`, `GUIDE.md:110`; #4212).
3. **The bleed-out.** The 28.01776885986328 health left at seq 4698 fell in ten steps of 2.6698150634765625–2.6762161254882812 (seq 4706–4807) and a last of 1.2806167602539062 (seq 4824), each 405–599 ms after the fall before it. From seq 4706 to the death no zombie stood nearer than 1.5895053962743115 tiles. Before seq 4706 the nearest stood closer: 30431 was 0.6934501481073865 tiles off at seq 4698 (`GUIDE.md:106`–`GUIDE.md:110`; #4212).

`grade_d` explained the death by its **wound arm** (ruling S-16), but from a bleed frame (seq 4410). Its 300-frame window opened **49 frames after the first wound** (`GUIDE.md:89`). The tagged arm failed: the window's 280 server records cover only its last 3400 ms, because 807 earlier records aged out of `damage.watch`'s 200-record list between the driver's 30 s polls. Even all 807 at the largest amount read would sum to at most 70.8068135289941, under the 73.040771484375 the arm needs. The wound terms fire no server event (#2364; `GUIDE.md:87`).

**The policy around the death.** Each step is a policy reading:
- The pair rule needs health under 60, so the fight ran on through the wounds with two zombies in reach from health 80.57986450195312.
- `pair` first fired at 59.415531158447266 (`d_survive-20261027-175917/GUIDE.md:117`–`GUIDE.md:118`).
- The flee's first two sprint steers were pinned at load level 4, after load `max` fell 12 → 11 → 10 with the weight unchanged (`GUIDE.md:110`, `GUIDE.md:133`).

**The needs.** No `consume` was sent in either run (`d_survive-20261027-173724/GUIDE.md:45`; `d_survive-20261027-175917/GUIDE.md:50`). The need branch's thresholds are 0.5, and the peaks stayed under 0.09 in run 1 and 0.05 in run 2 (`d_survive-20261027-173724/GUIDE.md:61`; `d_survive-20261027-175917/GUIDE.md:62`). So in survival, eating and drinking under the planner are still unread. The client's hunger matched the server's to within 0.00012223597150295973 and 0.0001224195584654808 (`d_survive-20261027-173724/GUIDE.md:61`; `d_survive-20261027-175917/GUIDE.md:62`).

**The planner's loop cost.** Run 2's planner did not tick during the driver's synchronous server reads:
- every 60 s, the `stats.all` and `players` reads stalled it 2.813 to 3.573 s;
- every 30 s, the `damage.watch` read stalled it 0.8 to 1.453 s;
- the last stall, during the bleed-out, left the character standing for 1457 ms. The bleed ran on at the same rate, so the death did not turn on it (`d_survive-20261027-175917/GUIDE.md:119`).

## 5. The walls still standing

1. **The 1 ms clock** (P22-4). It leaves several costs unreadable:
   - any single span under a millisecond;
   - the frame's positional encode, which sits inside no timed span;
   - the emit's mean, which is bounded at 0.6155124653739612 ms and not measured;
   - the cause of the 7 unattributed ms in tick 182 (`x4_link-20261027-171916/GUIDE.md:135`, `GUIDE.md:137`–`GUIDE.md:138`).

   JFR needs a JDK, and its flag changes the client's JVM arguments (spec § 11), so the plan has no finer instrument.
2. **The client is deaf to body damage.** `BodyDamage.Update` returns at once on a client for the local player (#2597). The wound terms go through `CombatManager.applyDamage` and fire no `OnPlayerGetDamage`; only the bleeding term does (#2364). The server's `damage.watch` is the only ear:
   - In X5 it heard only `BLEEDING`, at most 2.988 of the 57.68889617919922 health the frames lost (`x5_combat-20261027-173248/GUIDE.md:131`).
   - Its 200-record list overflowed at a 30 s poll in run 2, losing 807 of 1122 records (`d_survive-20261027-175917/GUIDE.md:87`).

   The frames' health and wound counts are the only reading of a zombie's blow.
3. **The sidecar trigger's reading.** The gate's filter averages `linkMs` over the frames reading above 0, which is at least 1 by construction, so its "fired" is the clock's artifact. On the honest population, every flushing tick of the 60 Hz window, the flush read 0.2691029900332226 ms mean and 2 worst. Ruling S-18 reads the trigger as not fired (`x4_link-20261027-171916/GUIDE.md:74`–`GUIDE.md:78`). A `gate_x4_2` reading the window is minted only if a second X4 pass runs (ledger L128).
4. **The fight that hits nothing.** Run 1 swung 103 times against a locked door's square, and run 2 held a stand-off. The square record names a door but not its edge, and it records no wall or fence that is not a solid square (`d_survive-20261027-173724/GUIDE.md:71`, `d_survive-20261027-175917/GUIDE.md:77`). The `Fight`'s stall clock restarts inside `FIGHT_REACH`, so such a fight never ends (`d_survive-20261027-173724/GUIDE.md:72`). **Open.**
5. **The stuck walk's re-send.** `explore` re-sends a failed walk to an unchanged edge after each cooldown: 20 times in run 1 (`d_survive-20261027-173724/GUIDE.md:79`). Why the walk never moved, the frames do not say (`GUIDE.md:80`). **Open.**
6. **The loot overload.** Looting with filter `all` carries the load past level 3 in one loot, and the guard drops one item a tick. Run 1 dropped 33 items and run 2 dropped 50 (`d_survive-20261027-173724/GUIDE.md:82`; `d_survive-20261027-175917/GUIDE.md:64`). **Open.**
7. **The instrument's cost on a fight.** X5's synchronous server reads, 0.257–2.019 s each, set the fight's pace (`x5_combat-20261027-173248/GUIDE.md:121`, `GUIDE.md:141`). The acceptance driver's reads stall the planner every 30 and 60 s (`d_survive-20261027-175917/GUIDE.md:119`). #1862's 0.3 s did not hold. **Open.**
8. **The window-shifted final scan.** X4's `map_kept` read fidelity over the 870 squares both scans covered. The kept map's fidelity on squares that only the watch sent is not read (`x4_link-20261027-171916/GUIDE.md:140`). **Open:** for `x4_link_2.py`.
9. **The schema's cost-field wording.** `pza1.json` describes the `cost` fields as means since the last frame, but `PZAgent_Main.lua` writes single-tick spans (`x4_link-20261027-171916/GUIDE.md:29`; `task-13-report.md` concern 5). **Open.**
10. **No live-run replay.** Spec § 10's golden replays of every live run's `state.log` were not built. The one replay test reads a synthetic fixture (§ 1). **Open.**
11. **`tools.json`'s `attack` description** says "Step to the weapon's reach of a zombie, face it and swing until it dies or the skill ends." The skill calls `DoAttack` once and ends when `isAttackStarted` has read true and then false, when the target is dead, or after `SWING_MS` (`x5_combat-20261027-173248/GUIDE.md:31`). An LLM reading the tool would expect a fight, not a swing (a reading of the two files). **Open.**
12. **X5's sight and targeting.** Encounter 2's spawn was listed by no frame (S-22; `x5_combat-20261027-173248/GUIDE.md:58`). The `Fight` targets the nearest zombie, not the encounter's (`GUIDE.md:60`). An X5 re-run needs a clear spawn or a fight pinned to its zombie (`task-16-report.md` concern 2). **Open.**

**The parked items: all open, apart from the two write-up fix rounds (Tasks 16 and 19a).** The consolidated fix wave has not run, and the ledger has no line saying any of these items landed (ledger L156: "The parked items are collected in fixwave-sources-ledger.txt and fixwave-sources-reports.md"). The Task 16 and Task 19a rows are the exceptions: their fixes landed, as the rows say.

| Task | Item | Source |
|---|---|---|
| 9 | `K.OFF_SETTERS` mirrors `MO.off`'s three setters: fold the guard into `MO.off` and drop the copy, with two stale `MO.off` comments | ledger L118–L119; `task-9-fix-2-report.md` concern 2 |
| 9 | `offSafely` before `emitAct` | ledger L119 |
| 9 | an S-15 pass over Map's readers (`scanStart` on a raising player is one `lua_error`) | ledger L119; `task-9-fix-2-report.md` concern 3 |
| 5 | derive the `door` event from the Map watch's delta (the Sense door walk read 0.3–0.75 ms a call on lupa) | ledger L97; `task-5-report.md` concern 1 |
| 5, 6 | one portal rule in Map; the `portalOf`/`kindOf` and `getm` duplicates across files | ledger L97, L109 |
| 4 | split `PZAgent_Skills.lua` (863 lines at the review, 922 now) | ledger L92 |
| 4 | `reasons.py`'s stale docstring | ledger L92 |
| 14, 17 | the drivers' copied helpers want a non-frozen driverlib | ledger L105, L117 |
| 3, 4 | the `walkTo`/`steer` mid-skill dead arms are untested | ledger L93 |
| 9b | `attack`'s sub-walk that cannot queue burns `APPROACH_MS` before `out of reach` | ledger L115 |
| 2 | the Link's backlog copying and chunk reload | ledger L82 |
| 9a | `World.damage_seen_i` grows without bound; the prune's O(squares × containers); the fixture script patches `FakeMod._emit`; map and events stored by reference | ledger L79; `task-9-report.md` concern 2 |
| 1 | `wallMs` typed integer on keyed kinds; keyed `encode` `allow_nan`; a non-UTF-8 target under `--check`; no test of the dataclasses' enum check; `json.load(open())` in tests; `same.%s` not through `_lidx` | ledger L71 |
| 3 | `act.type` echoes an unknown type; `snapshot` omitted on `accepted`/`progress` though the schema requires it; minors 3–5 and 7 | ledger L85–L86 |
| 6 | `MP.missing` never emitted; a cut part's squares stay seen; the schema's cost descriptions; minor 6 | ledger L109 |
| 7 | `damage.watch` has no unwatch; `since` accepts a non-integer; the marker test checks presence; a wasted read on a failed get | ledger L68 |
| 8 | `gaps` typing | ledger L74 |
| 11, 17 | `PARK_RX` pinned by string; `main` tested only statically; the provenance test pins x5's line numbers; a 5–15 MB `decision.log` | ledger L99, L117 |
| 13 | three Minor and three Nit of the X4 write-up's review | ledger L152 |
| 16 | the X5 write-up's fix round on #4209 (I1) and M1–M5, N1–N3, landed at `a38424ae` and `acaa5986`; its scoped re-review had been dispatched with no verdict ledgered when this report was written | ledger L162–L163 |
| 19 (Writer A) | the acceptance write-up's review FAILED, on #4212's last clause (wider than its frames) and on three settled research-notes threads left standing as open; Minors: "18 ms, at its init" and the slow-window splits; Nit: the 200-record cap's line. **Landed** at `f411a698` (the guides and pages: #4212's bleed-out scoped to seq 4706–4824, the worst ticks placed in the first frame's window, the splits restated under a stated rule, the cap cited at `PZTestKit_Server.lua` L5055, the three threads' bullets removed from research-notes) and `3c0e33f1` (the register fill); its re-review is not in this report's sources | `review-t19a.md` findings 1–5; ledger L164; both acceptance guides' `## Corrections` |
| 18 fix 1 | an unrelated comment alignment on `files.py`'s `self.bad`; no test that another exception propagates unchanged | ledger L149 |
| 19 (acceptance) | the fight that hits nothing; `grade_d`'s wound-arm window opening 49 frames after the first wound; `damage.watch`'s 200-record list at a 30 s poll; run 1's artifacts row cited by no page; run 2's higher cost on the same Lua; the transport retry the frozen driver does not record | `task-19a-report.md` concerns 1–5 and 7 |

## 6. Decisions taken

**The rulings carried in from the plan's opening** (`docs/superpowers/plans/2026-10-27-plan-22-agent-base.md`), verbatim:

- **P22-0** Plan 21's Python layer stays in place, frozen with the drivers that import it (`c_survive.py` imports `agent.policy`, `agent.world`, `agent.link`; `grades.py` and `grade_c.py` are committed grade scripts); the PZA/1 base is the package `testing/agent/base/`, and nothing under `testing/agent/*.py` or `testing/agent/drivers/` from before this plan is edited — cost if wrong: a second `world.py` beside the first, named in each module's docstring.
- **P22-1** The action list is spec § 5's closed list; `sleep` is not in it, so no sleep skill is built, the acceptance policy has no sleep branch, and the Lua `sleep` goal leaves with the machines (its tests named in the reset) — cost if wrong: a later schema addition under the gate.
- **P22-2** The inventory's first sight: after `hello`, the Lua emits one `item_added{itemId, fullType, weight}` event per item held, and `World.inventory` is built from `item_added`/`item_removed` alone (`equip`, `consume` and `drop` take the ids it holds) — cost if wrong: a wrong id is a typed `none held`.
- **P22-3** A delta frame elides at group granularity: a group (`me`, `stats`, `body`, `load`, `weapon`, `action`, `act`, `cost`) whose encoding equals the last full frame's is sent as the JSON literal `true`; `zombies` is never elided; a full frame every `L.FULL_EVERY = 10` frames and on every rate change — cost if wrong: a few hundred bytes a frame.
- **P22-4** The worst-tick instrument is the 1 ms `getTimestampMs` clock, stated in the gate: JFR's `jfr` tool needs a JDK (none) and a `-XX:StartFlightRecording` flag changes the client's JVM arguments (§ 11) — cost if wrong: a 1 ms quantisation the guide names.
- **P22-5** `scan{r}` and `rate{hz}` are commands answered by one `act` line in state `done` (their result `{queued: true}` / `{hz}`), so every command has one reply shape — cost if wrong: none.
- **P22-6** `PZAgent_Bench.lua` leaves (probe instrumentation; X4 reads the costs off the frames' `cost` group) and `PZA.VERSION` becomes `"1.0"` — cost if wrong: the probe artifact keeps the bench readings.
- **P22-7** X5's server read of a zombie is a new narrow harness command `zombie.get <onlineId>` beside `damage.watch` (Task 7); no existing command reads a zombie by id — cost if wrong: one more bus site.
- **P22-8** `interact` takes `{x, y, kind, filter}` and no `objectId`: the map lines identify doors, windows and containers by square, and no line carries an object id — cost if wrong: a later schema field.
- **P22-9** The acceptance run keeps `c_survive.py`'s accepted form (one detached session, `DAY_CAP_S = 5400`, the stop conditions bounding it), since a survival run cannot be split into 15-minute sessions without ending the character's day — cost if wrong: one long session.

**The session rulings** (the ledger, which is gitignored, so they are recorded here). Each line gives what was ruled, why, and the cost if wrong. The ledger has no S-9.

- **S-1** (L47) The generator exports every record and group encoder as `PZA.enc.<name>`, because Task 6's watch needs `PZA.enc.square`. Cost if wrong: a few exported names.
- **S-2** (L48) Tasks 2–5 rewrite in place, with the folder transiently red only in the files Tasks 3–6 rewrite or delete, green again at Task 6. One giant Task 2–6 would be unreviewable. Cost if wrong: four commits with a red `pzagent` folder.
- **S-3** (L49) Task 2 adds the cross-host test: a Lua-emitted frame and map line decode through `pza1.decode`, per "one schema, two hosts". Cost if wrong: one test.
- **S-4** (L50) Lanes: the Lua lane (Tasks 2→6) is serial, and Tasks 7 and 8 run beside it on disjoint files. Cost if wrong: an index-lock retry.
- **S-5** (L66) `cmd.txt` and `ack.txt` are each one JSON line read through `PZA.decode`, and `PZA.readKV` and `L.ack` leave. Cost if wrong: one tiny reader.
- **S-6** (L66) The delta base is the last sent encoding of each group, so the Python reader merges each delta into its running frame, and a delta before any full frame is bad. Cost if wrong: a reader merging from the wrong base.
- **S-7** (L69) Every kind carries the required `seq`/`tick`/`wallMs` envelope (spec § 4). Cost if wrong: three fields a line.
- **S-8** (L69) `map.missing` is an array of member names, not a count. Cost if wrong: a few bytes a part.
- **S-10** (L73) Task 9 runs in two phases (World first, the Lua fault test after Task 6), so the Python lane does not idle. Cost if wrong: two commits for one task.
- **S-11** (L82) Every line's seq rises in file order: backlog bodies are stamped and encoded at flush and the budget is checked on the encoded size, because Task 8's gap detection depends on it. Cost if wrong: the encode moves to the flush tick.
- **S-12** (L85) `K.tick`/`K.start` guard a skill's raise (`failed interrupted` / `rejected bad args`, counted). Cost if wrong: one pcall.
- **S-13** (L97) Task 5's fix round waits for Task 6's commit, because both edit `PZAgent_Sense.lua`. Cost if wrong: an hour's delay.
- **S-14** (L109) The watch's dirty key excludes light, because the dirty set means a world change. Cost if wrong: a light-only change is not pushed.
- **S-15** (L114) A raising Java member is a supported fault: the runner and Sense contain it, and `steer` needs `setAutoWalk`. Cost if wrong: a few pcalls on the tick.
- **S-16** (L117) A death is explained by a tagged arm or by a wound arm (a wound rising with a zombie within `DANGER_R`) over a 300-frame window, because the server hears no wound damage (#2364). Cost if wrong: an over-generous wound arm, which the guide's line-by-line reading corrects.
- **S-17** (L124) Angus's message of 17:11 ("please continue and iterate without waiting on me to confirm it if there is anything pending") approves the three sessions, each still gated at its own boot. Cost if wrong: one or two unwanted 13–95-minute sessions.
- **S-18** (L128) The sidecar trigger's "fired" is a quantisation artifact and is read as not fired, so K2's spike does not run and `gate_x4` stays frozen. Cost if wrong: a skipped spike that the emit's cost warranted.
- **S-19** (L129) Go-with-findings: X5 and the acceptance run on X4's NO-GO, and the one X4 fix pass runs after the consolidated fix wave. Cost if wrong: X5 and the acceptance measured on a base whose 60 Hz cost later changes, and a second X4 boot of 14 minutes either way.
- **S-20** (L130) Task 13's writer, editing docs and artifacts only, may run beside the X5 boot. Cost if wrong: a dirty-tree preboot stop, which is not a run.
- **S-21** (L135) The fight reflex stays in Python, provisional on the acceptance's fights. Cost if wrong: a Python reflex that loses the first exchange to a lunge, and a Lua `fight` skill in a later plan.
- **S-22** (L136) X5 counts as a run, and encounter 2's void goes to the guide and the fix wave. Cost if wrong: a Sense defect reaching the acceptance unfixed.
- **S-23** (L137) The acceptance boots beside the X4 and X5 write-ups. Cost if wrong: one 95-minute session wasted on a shared defect.
- **S-24** (L143) Run 1 is kept as an artifact, the transport retry is fixed, and run 2 runs the unchanged driver with the fight and stuck-walk findings left unfixed. The stop was the instrument's, not the game's. Cost if wrong: 95 minutes repeating run 1's ineffective fight.
- **S-25** (L158) A `run:` pointer may name a container when the claim cites none of its do-not-cite children and those children are text or wildcard clock leaves; narrowing is preferred. Cost if wrong: a pointer nominally covering a barred key.
- **S-26** (L163) A bus step's reply time may be subtracted from an agent-loop reading to remove the instrument's own wait (#4209 is the use), but it is never cited as a reading of the game. Cost if wrong: a loop number that leans on an instrument table.

The ledger also records unnumbered rulings:
- Task 7's minors parked (L68).
- Task 1's minors split between Task 2 and the fix wave (L71).
- Task 8's `current` and delta-after-gap readings accepted (L72).
- Task 10's choices accepted: a superseded loot is not marked looted (L87).
- Task 6's `scan` result: the parts count, with whole-number `hz` and `r` (L108).
- Task 17's literal `death_explained` rule (L116), superseded by S-16.

## 7. Recommendation

**Plan 23 should make the scripted day survivable and readable on this base before an LLM drives it.** The order:
1. **The consolidated fix wave.** The § 5 table, with the Lua cost edits that S-19 names.
2. **The X4 fix pass** (`x4_link_2.py` under `gate_x4`, one boot of about 14 minutes, S-19):
   - the watch's per-tick budget at 60 Hz;
   - the init burst;
   - the command-accept burst, which first needs a timed span for the poll and a command's start, since the artifact names no cause for it.
3. **The fixture and policy work the sessions named:**
   - a square record that carries a door's or wall's edge, so the map can show what stands between a fighter and its target;
   - a `Fight` that stalls on the target's health, not on its distance;
   - an `explore` that does not re-send a walk that failed `stuck` to the same edge;
   - a loot that stops before level 3, not a drop after it;
   - `damage.watch` read often enough, or kept long enough, that bleeding does not age out;
   - `grade_d`'s wound window opened at the first wound;
   - server reads that do not stall the planner.

   A new acceptance driver goes with them, since `d_survive.py` is frozen.
4. **An acceptance session that lives long enough to send `consume`.** Neither run did (§ 4), and the needs are what a nutrition-mod test drives.

Why this order, from §§ 2–5:
- **The channel works.** 0 gaps and 0 Lua errors in every session, a 128–181 ms move, and a client copy that agrees with the server.
- **The X4 NO-GO is the base's own per-tick work, not the emit.** The sidecar trigger did not fire.
- **Both acceptance endings sit below any planner:** a fight the map could not explain, a walk re-sent twenty times, a load that pinned the last flee at level 4, and a death window the server's records could not fill.

**The alternatives, with their downsides:**
- **An LLM planner on `schema/tools.json` now.** The base gives it ten typed tools generated from the same schema as the wire, a `Planner` protocol written for "an LLM tool-caller later" (`planner/__init__.py`), and a `World` that is a pure function of the lines. It lacks four things:
  - a state view for the model: the base has no `summary` module, and Plan 21's `summary.py` is frozen with the old layer (P22-0);
  - an `attack` description that says one swing (§ 5, wall 11);
  - a map that names obstacles' edges;
  - a reflex budget it could meet. The acceptance's 2 Hz planner already stalls 2.813–3.573 s a minute on the bus (`d_survive-20261027-175917/GUIDE.md:119`), and the one approach read from outside reach left a margin of 568 to 769 ms over a 2 Hz planner plus the agent's 29 ms loop (§ 3). A model's own latency is not measured in this plan.

  An LLM run now would meet the same floor the scripted policy met, as Plan 21b found for spike D. *This recommendation's weak spot:* scripted fixes can keep running into game mechanics, a pinned flee for example, that an LLM might route around. Only an LLM run would read that, and this plan has none.
- **The sidecar (K2).** **It did not fire.** The flush per flushing tick read 0.2691029900332226 ms and its worst 2 ms (S-18; #4204), and the X2 bench found every emit cost on the Lua side (`p22_probe-20261027-032502/GUIDE.md:120`). Building it would move a cost the base has already cut, needs a JDK (spec § 11), and leaves the sense read and the map watch, which hold the 60 Hz tick, where they are. *Its weak spot:* the emit with its encode is bounded, not measured (§ 5, wall 1), and tick 182's 8 ms bound does not separate the encode from the command.
- **Only the X4 fix pass.** It would read a cheaper 60 Hz tick, but it would leave the two acceptance endings and the unexercised needs exactly where they are. A 10 Hz session's frame tick is what the planner runs on, and it read 1–3 ms on most standing windows (`x4_link-20261027-171916/GUIDE.md:156`).

## Appendix: the tests deleted with the removed Lua

Per the plan's test-reset rule. Names from the task reports; `test_lua_act.py`'s names are also recoverable with `git show ba5c4024:testing/tests/pzagent/test_lua_act.py`.

- **`test_lua_bench.py`, 10, with `PZAgent_Bench.lua`** (P22-6; `task-2-report.md` L89–L91): `test_every_bench_arm_is_a_function_of_no_arguments`, `test_json_is_the_part_of_20_squares_at_2_to_3_5_kb`, `test_no_sort_and_compact_parse_and_compact_is_20_positional_lists`, `test_open_write_opens_one_writer_per_call_and_appends_the_part`, `test_the_bench_file_before_the_link_is_initialised`, `test_a_held_writer_opens_once_and_appends_each_write`, `test_every_arm_tolerates_a_nil_writer`, `test_poll_reads_cmd_txt_through_the_file_reader`, `test_main_init_emits_the_bench_line_after_hello`, `test_a_second_held_open_closes_the_first_writer`.
- **`test_b_actions.py`, 4 static tests of `PZAgent_Act.lua`'s header** (`task-4-report.md` L198–L205): `test_reasons_equal_the_act_headers_reasons_line`, `test_every_failed_detail_the_act_file_sets_is_in_the_set`, `test_done_equals_the_act_headers_done_line_and_every_done_detail_is_in_it`, `test_no_failed_pair_uses_a_done_detail_and_no_done_pair_a_failed_one`.
- **`test_lua_act.py`, 101, with `PZAgent_Act.lua`'s goal machines** (`task-4-report.md` L207, its re-cover map from L213; `task-4-act-tests.txt`): `test_goto_queues_walk_and_reports_done_within_one_tile`, `test_goto_no_square_fails_and_stuck_replans_then_fails`, `test_unknown_goal_and_stop`, `test_main_tick_emits_hello_frames_at_rate_and_acks_config`, `test_main_tick_catches_a_raise_and_emits_lua_error_once`, `test_new_goal_clears_running_walk_and_reports_superseded`, `test_main_reports_superseded_event_and_scan_lands_with_its_ack`, `test_open_walks_adjacent_first_then_queues_the_open`, `test_open_adjacent_skips_the_walk_and_thumpable_door_counts`, `test_open_failures`, `test_open_that_never_opens_is_locked_and_an_open_door_is_done_at_once`, `test_open_a_locked_door_is_toggled_and_locked_is_read_after`, `test_loot_food_transfers_matches_and_reports_moved`, `test_loot_filters`, `test_loot_failures`, `test_eat_consumed_and_failures`, `test_eat_refuses_a_non_food_before_the_constructor_and_ignores_bags`, `test_drink_skips_poison_and_prefers_clean_water`, `test_drink_consumed_and_failures`, `test_every_failed_detail_is_in_the_header_reasons_line`, `test_goto_target_is_world_coordinates_not_an_offset`, `test_open_window_through_iso_open_close_window`, `test_open_prefers_the_door_when_a_square_holds_both`, `test_loot_timeout_fails_interrupted_when_nothing_moved_else_reports_moved`, `test_frame_link_ms_is_the_previous_frames_flush`, `test_tick_without_a_player_before_init_polls_and_writes_nothing`, `test_raise_before_init_counts_and_never_re_raises`, `test_tick_inits_the_link_before_its_first_poll`, `test_goto_done_clears_its_walk`, `test_open_sub_walk_is_cleared_before_the_open_is_queued`, `test_drink_with_is_poisonous_absent_is_none_held`, `test_fight_faces_and_swings_on_the_1200_ms_cooldown`, `test_fight_waits_beyond_fight_r_and_ignores_the_dead`, `test_fight_steps_back_two_tiles_inside_the_grab_window`, `test_fight_done_clear_after_60_quiet_ticks`, `test_fight_failures`, `test_fight_never_calls_an_absent_do_attack`, `test_flee_runs_to_its_target_and_is_done_at`, `test_flee_replans_every_30_ticks_away_from_the_zombie_centroid`, `test_flee_replan_keeps_its_walk_when_the_away_square_is_unknown`, `test_flee_cornered_on_no_square_or_stuck`, `test_sleep_calls_the_vanilla_ground_sleep_and_is_done_awake`, `test_sleep_not_allowed_when_the_call_raises_or_sleep_never_comes`, `test_sleep_interrupted_when_woken_by_a_hit_or_a_zombie`, `test_task11_details_are_in_the_header_reasons_and_done_lines`, `test_goto_fails_dead_at_once_when_health_reads_zero`, `test_a_dead_player_refuses_every_goal_and_an_absent_health_is_not_dead`, `test_main_acks_a_dead_players_goal_with_reason_dead`, `test_goto_moving_without_approaching_is_never_stuck`, `test_goto_whose_path_grows_the_distance_is_never_stuck`, `test_an_unmoving_player_replans_then_fails_stuck_and_the_failure_clears_the_walk`, `test_every_failed_goto_exit_clears_its_walk`, `test_a_failed_sub_walk_clears_once_for_open`, `test_main_scan_is_queued_and_emitted_one_part_per_tick`, `test_main_second_scan_replaces_a_running_one_and_its_parts_stop`, `test_each_part_carries_the_previous_parts_emit_and_the_next_frame_the_last_ones`, `test_sleep_on_a_client_honours_sleep_allowed`, `test_sleep_needed_refuses_within_an_hour_of_the_last_sleep`, `test_fight_clears_a_step_back_dropped_when_the_zombies_leave`, `test_fight_clears_a_step_back_that_failed`, `test_flee_resets_running_when_it_ends`, `test_a_dead_player_may_still_stop_a_running_goal`, `test_the_frame_after_a_completed_scan_carries_its_emit_cost_once`, `test_a_goto_without_the_vanilla_walk_class_fails_no_path_and_raises_nothing`, `test_a_goto_without_the_vanilla_queue_fails_no_path_and_raises_nothing`, `test_a_loot_without_the_vanilla_transfer_class_fails_not_loaded`, `test_an_eat_whose_constructor_lacks_new_is_refused_before_any_call`, `test_an_action_without_is_valid_start_or_a_missing_queue_is_refused_before_any_call`, `test_an_open_whose_constructor_lacks_new_or_whose_queue_lacks_add_fails_no_door`, `test_loot_approach_skips_a_solidtrans_neighbour_and_walks_to_the_next_free_one`, `test_fight_steps_toward_a_zombie_out_of_reach_and_never_swings_there`, `test_fight_swings_inside_reach_and_queues_no_step`, `test_flee_asks_to_run_and_sprint_every_tick_and_clears_both_once_at_the_end`, `test_a_walking_step_never_asks_to_run`, `test_reach_is_the_weapons_max_range_times_range_mod_times_the_margin`, `test_a_walking_player_closes_on_a_standing_zombie_and_swings_inside_the_weapons_reach`, `test_a_closing_walk_that_ends_short_of_reach_swings_from_there_and_never_re_queues`, `test_a_superseded_flee_and_a_stop_clear_the_run_and_sprint_flags`, `test_a_walk_arm_asks_nothing_and_its_done_turns_every_motor_ask_off`, `test_a_setrun_arm_asks_run_and_sprint_every_tick_from_the_tick`, `test_a_forcerun_arm_sets_the_motor_flag_and_never_calls_set_force_run_from_the_tick`, `test_the_forcerun_arm_reaches_the_player_through_the_on_player_update_handler`, `test_a_forcerun_tick_arm_asks_set_force_run_every_tick_and_leaves_the_motor_flag_clear`, `test_a_forcesprint_arm_sets_both_motor_flags`, `test_a_toggle_arm_sets_toggle_to_run_once_and_restores_the_value_read_before`, `test_an_unknown_arm_is_bad_args`, `test_a_stuck_failure_turns_the_motor_off`, `test_a_no_square_failure_turns_the_motor_off`, `test_a_superseded_goto_and_a_stop_turn_the_motor_off`, `test_a_flee_sub_walk_takes_no_motor_off_at_its_end`, `test_autowalk_sets_auto_walk_and_its_direction_once_and_is_done_at_its_deadline`, `test_autowalk_once_asks_set_force_run_exactly_once`, `test_autowalk_forcerun_sets_the_motor_flag_until_its_end`, `test_autowalk_bad_args`, `test_autowalk_without_vector2_fails_not_loaded`, `test_autowalk_fails_dead_when_health_reads_zero`, `test_drop_queues_one_floor_drop_per_matching_item_up_to_n_and_reports_moved`, `test_drop_none_held_and_bad_args`, `test_drop_without_the_vanilla_class_or_a_square_fails_not_loaded`, `test_drop_interrupted_at_the_budget_with_none_gone_else_moved`, `test_autowalk_once_asks_set_force_run_on_its_second_tick_only`.

Model: claude-opus-5-5
