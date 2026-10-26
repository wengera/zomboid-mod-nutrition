# Plan 21: the agent harness — a feasibility exploration (design)

## Why

Angus asked on 2026-10-26 for "a more robust framework for running and even playing the game … a mod that will output all the player information and environment information in real time, with a harness that reads this and then controls the player programmatically. This is more of an exploratory project for now to determine feasibility and challenges."

The deliverable is a **feasibility report** with numbers, not a subsystem. Everything built is spike evidence, kept in the tree the harness way (drivers frozen after their run, artifacts byte-identical), with no promise that any of it survives a go decision.

## Decisions (Angus, 2026-10-26)

- **C: one interface, two users.** A shared state-and-action API; the scripted Python bot is built first, an LLM agent can sit on the same API later.
- **C: built in the harness, separable later.** It runs on `pzt` fixtures with harness-launched clients, but the mod never requires or calls `PZTestKit`, so it could ship on its own.
- **C: the exploration proves survival.** The pipe → basic actions → a scripted bot surviving a game day with zombies on. Each stage has a go/no-go gate.
- **1: a pure Lua mod over files.** Kahlua has no sockets; the Lua file writer is rooted at the cachedir's `Lua/` folder and allows `ini`, `cfg`, `txt`, `log`, `json` [#1866, #3558]. Python plans at 1–5 Hz; the mod's reflexes run at tick rate; the 0.3 s round trip [#1862] is absorbed by that split. A JVM agent is the measured fallback, named only if spike A's gate fails.
- **5 Hz, not 20.** The core frame defaults to 5 Hz; sudden things go out as `event` lines at once; the rate is a dial the spikes sweep.
- **One goal at a time.** The mod holds no queue; Python is the planner.
- **Unattended.** The plan runs without questions to Angus beyond the three named in § 7; every other decision is pre-ruled here or ledgered under § 7's defaults.

## 1. Components

### 1.1 The mod `PZAgent` — `testing/PZAgent/PZAgent/`

`mod.info` with `id=PZAgent`, a `42/media/lua/` tree like the harness. Rules for the folder:

- It never requires, references or calls `PZTestKit`; it carries its own JSON encoder and file-channel code (a copy, not an import).
- Every Java member call sits behind the index-first guard [#1714]; an unguarded raise parks the `-debug` client.
- Kahlua rules: no `goto`, no `%d` on floats, no `#` on Java lists, no `%g` of a value that can be tiny; `kahlua_lint` and `luabalance` green before any boot.
- Every file keeps a `-- @purpose / @args / @reply`-style header block per goal and per line kind, so the protocol is readable from the source.

| File | Owns |
|---|---|
| `client/PZAgent_Link.lua` | the transport: appends lines to `Lua/pzagent/<user>/state.log`, rotates at 8 MB to `state.<n>.log`, polls `Lua/pzagent/<user>/cmd.json` each tick by `seq`, writes `ack` lines |
| `client/PZAgent_Sense.lua` | the sensors: `frame` at the set rate, `event` on change, `scan` on demand or cadence; counts its own ms per tick |
| `client/PZAgent_Act.lua` | the goals as per-tick state machines (§ 2.3); the reflexes; reports goal status in every frame |
| `server/PZAgent_Server.lua` | **not built unless spike A's gate names it** (§ 4.1); until then the server-owned stats come over the harness bus |

### 1.2 Python — `testing/agent/`

Pure Python, no game dependency, every module tested offline.

| Module | Owns | Tested by |
|---|---|---|
| `link.py` | tails `state.log` and its rotations, yields parsed lines, writes `cmd.json` atomically (temp + rename), matches `ack`/status to `seq`, `await_goal(seq, timeout)` | a fake mod answering the real line shapes read off the Lua `@reply` blocks; rotation, gaps, partial lines |
| `world.py` | the running model: `me`, `zombies` (aged out after `ZOMBIE_TTL_S`), `map` (sparse squares, doors, windows, containers with `looted`), `server` (bus stats, own clocks), `events` (bounded deque); a pure function of the log | replay of a recorded log reproduces the model byte-for-byte (`world_replay` golden) |
| `policy/` | the behaviour tree (§ 3), ticked at `PLANNER_HZ` (2); writes `decision.log` with each decision's inputs | every branch has a unit case that fails it; a replayed log of a death reproduces its last ten decisions |
| `summary.py` | the compact text state for a future LLM agent; unused by the bot | golden against a recorded model |
| `drivers/a_pipe.py`, `b_actions.py`, `c_survive.py` | one per spike; import `testing/experiments/xlib.py`; boot through `pzt` | § 5's driver rules |

### 1.3 Test bed

- **Fixture `agent`**: `pzt provision --name agent --sandbox Zombies=<the sparse value of § 7.3>` plus the respawn keys the fixture's own sandbox file names set to off, standard spawn (a town; houses within scan radius). Provisioned once; ~2.5 min. Stage B turns zombies off through the profile's `[sandbox]` block (it merges, never replaces).
- **Profile `testing/profiles/agent.toml`**: mods `PZTestKit` (the bus, for server stats and `players`) and `PZAgent` (`path = "testing/PZAgent/PZAgent"`), `[server] SleepAllowed = true, SleepNeeded = true`, `[client] timeout = 120`, the fixture's 90-minute day, no multiplier. One client, `admin`, `-debug`.
- **Out of scope**: release clients, non-harness games, more than one bot, any edit under `mod/NutritionRevamp/`.

## 2. The wire

### 2.1 Lines, mod → Python (`state.log`, one JSON object per line)

Every line: `{kind, seq, tick, wallMs, gameMin, worldAge, ...}`. Numbers as Lua renders them, unrounded. `seq` is per-line and monotone; a gap is a finding.

| kind | when | body |
|---|---|---|
| `hello` | mod load, each Lua reset | `{modVersion, build, user, rate}` |
| `frame` | every `60 / rate` ticks (rate default 5) | position and facing; moving/running/sprinting; the queued action's class and progress; hunger, thirst, fatigue, endurance, panic, pain, health, sickness, wetness, temperature; moodle levels; held weapon {type, condition, ammo}; `zombies[]` within `ZOMBIE_RADIUS` (id, x, y, dist, hasTarget, crawler, reanimated where readable); `goal {seq, name, state, detail}`; `cost {senseMs, actMs, linkMs}` |
| `event` | at once | `zombie_enter`, `zombie_leave`, `hit {kind, part}`, `goal_done`, `goal_failed {reason}`, `item_added {fullType}`, `stuck`, `lua_error {msg}` (caught by the mod's own pcall, never raised) |
| `scan` | on `scan r` or every `SCAN_S` | squares in radius r: walkable, door {open, locked, barricaded}, window, container {type, looked, items[] when loaded}, floor items, room name, building id, light, hour |
| `ack` | on each accepted `cmd.json` | `{cmdSeq, ok, reason}` |

### 2.2 Commands, Python → mod (`cmd.json`)

`{seq, goal, args}`. The mod accepts a `seq` once, acks it, and pre-empts the running goal. `stop` clears. `rate n`, `scan r`, `radius n` are configuration commands that ack and run no goal.

### 2.3 Goals (`PZAgent_Act.lua`)

| Goal | per-tick behaviour | done | failed |
|---|---|---|---|
| `goto x y [run]` | path-walk through the game's own action; re-plan when blocked up to `REPLAN_MAX` | within 1 tile | no path; `REPLAN_MAX` exceeded (`stuck`) |
| `open x y` | walk adjacent, open the door or window | open | locked; not a door |
| `loot x y [filter]` | walk adjacent, open, transfer items matching `food|water|weapon|bandage` | transfer complete | container not loaded; empty |
| `eat T` / `drink` | the real timed actions | item consumed | none held; interrupted |
| `fight` | face the nearest threat, swing on cooldown, step back on the grab window | no threat within radius | weapon broke; health under `FLEE_HEALTH` → reports and Python decides |
| `flee x y` | run along a path away | at target | cornered (no path) |
| `sleep` | lie down when allowed | awake | not allowed; interrupted |
| `stop` | clear the queue | at once | — |

Every goal reports `state` and `detail` each frame; a failure's `reason` is one of a closed set the driver tests enumerate.

### 2.4 Server-owned stats

Python asks the harness bus (`stats.all`, `nutrition.get`) every `SERVER_POLL_S` (60) and merges into `world.server` with the bus reply's own clocks; never into `me`.

## 3. The policy (scripted bot)

Priorities, top wins; a goal is sent only when it differs from the running one:

1. **Threat**: zombie within `DANGER_R` → `fight` if armed and ≤ 2 threats, else `flee` to the farthest known walkable square from the threat centroid.
2. **Need**: thirst > `THIRST_T` or hunger > `HUNGER_T` → `drink`/`eat` from inventory; else mark the need and fall through.
3. **Sleep**: fatigue > `FATIGUE_T` and night → nearest known indoor square, `sleep`.
4. **Forage**: nearest known un-looted container → `goto`, `open`, `loot <need>`.
5. **Explore**: nearest unexplored building edge → `goto`, then `scan`.

The bot is deliberately dumb. A death with a readable cause in `decision.log` is a successful spike.

## 4. The loop: stages, gates, iteration

Each stage runs as one loop until its exit gate holds or its budget is spent. Every pass of a loop is: **build → offline tests green → doctor and memory gate → boot → measure → verdict → ledger line**. A FAIL verdict names the defect and opens the next pass; the budget is the stop.

### 4.0 Stage 0 — the scaffold (offline only)

Build: `PZAgent` with `hello`, `frame`, `ack`, `rate`, `stop`; `link.py`; `world.py` for frames; the fixture and profile files; the offline test suite.
Gate: `kahlua_lint`, `luabalance`, `mod_lint testing/PZAgent/PZAgent` 0; `pytest testing/agent/tests` green; `pzt doctor` passes with the profile resolved (no boot). Budget: no boots.

### 4.1 Stage A — the pipe (go/no-go 1)

Driver `a_pipe.py`: boot; sit still; `rate 2`, `rate 5`, `rate 10` for 60 s each; `scan 5`, `scan 10`, `scan 15` five times each; `goto` 10 tiles out and back, ten round trips; teardown.
Measures: per-tick `cost` p50/p99 per rate; scan cost per radius; cmd write → `ack` wallMs → first position change; `seq` gaps; bytes per minute.

| Gate | Pass |
|---|---|
| per-tick cost at 5 Hz | p99 < 2 ms |
| 15-tile scan | < 5 ms |
| cmd → motion | < 500 ms, p90 |
| gaps | 0 |
| client Lua errors | 0 |

Budget: 3 passes. Exit: all pass → **GO**; a cost line failing after 3 passes → **NO-GO, report names the fallback** (§ 4.4) and whether `PZAgent_Server.lua` would help; the plan continues to the report, not to B.

### 4.2 Stage B — the actions (go/no-go 2)

Driver `b_actions.py`: a fixed sequence, no policy: `scan 15` → `goto` nearest building → `open` its door → `loot` each container `food` then `water` → `eat` → `drink` → `goto` spawn. Five repetitions, zombies off (the `default` fixture's setting, overridden in the profile for B).
Measures: each goal's outcome, wall and game time; the failure reason distribution; `nutrition.get` after each eat against the frame's hunger.

| Gate | Pass |
|---|---|
| sequences completed | ≥ 4 of 5 |
| failures with a reason from the closed set | 100 % |
| eat seen by the server within `SERVER_POLL_S` | 5 of 5 |

Budget: 4 passes (a goal's state machine is the likely defect). Exit: pass → **GO**; else **NO-GO** with the failing goal named, on to the report.

### 4.3 Stage C — survival (the answer)

Driver `c_survive.py`: the policy, zombies on (`agent` fixture), one game day cap (90 wall minutes), a detached launch polled across foreground calls (§ 7). Then one fix pass if the first run forces it (the harness rule: one fix before the real run, named in the guide), then one run at a denser zombie setting if the first survived.
Measures: survival time; needs over time, client frame vs server reading; decisions per minute; fights and outcomes; the last ten decisions before any death; per-tick cost over the session; any `lua_error` events.

No pass/fail gate: the output is the report. **Stop conditions** end a run early: the client parks (bus dead 60 s), a `lua_error` storm (> 10/min), the memory gate failing mid-session, or death.

Budget: 3 runs.

### 4.4 The report — `docs/superpowers/specs/2026-10-26-agent-harness-report.md`

Written by a fresh Opus reviewer from the artifacts alone, never by the implementer. Sections: what works; the cost of each layer, with the numbers and their artifact keys; the walls found, each with its evidence; survival results; a recommendation (go / no-go / go-with-changes), and whether the LLM spike is worth running. Every number cites an artifact path; a claim with no artifact is cut. The fallback (a JVM agent on a localhost socket) is discussed only if a gate named it.

## 5. Rules that carry over unchanged

- § 5 of CLAUDE.md whole: doctor before every boot; one session repository-wide; the 12 GB gate read and ledgered; a driver tested offline against the real staged copy and a real run layout before its first boot; a driver never edited after its run; a trivial reading written as such; artifacts byte-identical under `testing/artifacts/<run-id>/` with `GUIDE.md` and a row in the register; `do-not-cite.csv` rows for wall-clock keys by wildcard sentence.
- The fake mod in Python answers the real line shapes read off the Lua source, empty-collection shapes included (`zombies: {}` when none, since the encoder renders an empty table as an object).
- A defect found in one driver is grepped across every unrun driver before the next boot.
- Pathspec commits; no `GIT_DIR`; no index-wide git; `testing/artifacts/x391f-20261013-113457/` is never staged.
- Rule 6 applies to the mod's own cost: the `cost` field is the measurement.

## 6. Verification before any "done"

- A stage's verdict is read off the artifact by a script committed with the driver (`a_grade.py` etc.), never off the driver's own console, and the grade script has an offline case that fails it.
- The report's reviewer re-derives every gate number from the artifacts.
- The plan closes with: full claims_check 0 (new rows minted for each gate reading, with the stage's artifact as evidence); the full pytest, count never dropping from 8329; `bus_inventory --check` untouched (the harness is not edited unless § 7's exception fires); CLAUDE.md § 2 unchanged.

## 7. Unattended operation

Angus is asked exactly three things, all before Task 1 of the plan:

1. **Detached launches**: approval, once, for the named sessions of stages A, B and C to be launched detached by the controller (§ 5 of CLAUDE.md; stage C's 90-minute session exceeds the 10-minute cap; A and B may too).
2. **The `agent` fixture**: approval to provision it (a new folder under `testing/fixtures/`, gitignored cache).
3. **Zombie settings**: the sparse and dense `Zombies=` values for the fixture and the stage C second run (the default if unanswered: the lowest non-zero population setting and one step above it).

Everything else is pre-ruled:

- **Memory gate**: the driver polls free memory every 60 s for up to 30 min; below 12 GB after that, the pass is ledgered `blocked: memory` and the loop waits for the next controller wake, never a boot.
- **Harness edit needed** (a reply shape a stage needs that the bus lacks): allowed only as its own commit under the harness rules, ledgered as the exception, and only for server-owned readings; otherwise `PZAgent_Server.lua` is built instead.
- **A gate failing on its budget**: NO-GO is a valid outcome; the loop moves to the report. No gate is relaxed to pass.
- **A ruling the controller must make** is written `Ruling: … — … — cost if wrong: …` in the ledger and surfaced in the report's "decisions taken" list for Angus's review.
- **Model sizing**: `opus` for the Lua mod, the grade scripts, every live session and the report; `sonnet` for the Python modules whose shapes the brief spells out.

## 8. Not in this exploration

The LLM agent (spike D) — named in the report's recommendation only. Multi-bot load. Release clients. Any mod-side intelligence beyond the reflexes in § 2.3. Any change to the nutrition mod.
