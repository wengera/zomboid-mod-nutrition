# `x221-20261007-083259` reading guide

**`x221-20261007-083259/globals.json`** — produced by `testing/experiments/x221_globals.py`, written before the boot and committed at `21a667b` with the probe `testing/experiments/TKX_GlobalsProbe` and the profile `testing/profiles/x22-globals.toml` before the run, unedited since, on HEAD `21a667b` (harness Lua `fadf698`, clean; `mod/` not booted)
(346.2 s wall; `globals.json` 853406 bytes, sha256 `8acde077…bd39d02e`, byte-for-byte identical to the run copy). **Plan 10 Task S1, the zeroed-drains alternative to the takeover**: fixture `two`, `admin` -debug then `bob` release, Nutrition false, DayLength 1, SleepAllowed and SleepNeeded true; every verify row ok; `server_error_count` 0; `admin` not parked.

How to read it. The probe zeroes `ThirstIncrease` and `ThirstSleepingIncrease` at file scope and `HungerIncrease`, `HungerIncreaseWhileAsleep`, `HungerIncreaseWhenExercise` and `FatigueIncrease` in an `OnGameBoot` handler, and keeps string fields in the global `TKX_G` (`phases.A`). The Lua table is a mirror once `ZomboidGlobals.Load` has run, so `phases.A`'s table reads say what Lua held, and the drift in B, B2, D and E says what the Java statics held. Each game minute, on the server, the probe reads each online player's three stats (pre), writes 0.3, 0.2 and 0.1 through `stats:set(CharacterStat.X, v)` and reads them back (post); a ring row per player per minute carries `d = pre − that player's previous post` (`phases.<P>.ring.rows`; `verdicts.<P>.observed.ring` summarises them per user, split by the server's `isAsleep` at the minute; `agg` is the probe's own per-user maximum |d| over the phase).

- **A** (server): `fileScope` `ThirstIncrease=0;ThirstSleepingIncrease=0`; `bootFired` `1`, `bootSide` `server`; `bootTableBefore` shows the two thirst keys already 0 and the four others at their shipped values; `bootSet` the four keys 0; `bootDayLength` `1` (the profile's value) while `fileScopeDayLength` read `4`; `startedTable` all seven keys 0 at `OnServerStarted`.
- **B** (writer on, both awake, 55 minutes per user): every ring delta 0 for all three stats on `admin` and `bob`; 52 server reads of `admin` 0.5 s apart all at the written floats; neither player carried a fluid container (`phases.S0.autodrink`, `containers` 0), so auto-drink never had a source.
- **B2** (writer paused, 1944.39 game-seconds between the two `stats.all` reads): HUNGER, THIRST and FATIGUE did not move across 20 reads (span 0 each); STRESS, set to 0.5, fell from 0.49885 to 0.44052, 0.058332 against the 0.058332 that 3e-5 per game-second predicts; BOREDOM rose from 0.1005 to 0.3784.
- **C**: five client-first pairs each on `admin` and `bob`, every client value equal to the server's for all three stats.
- **D** (`admin` held asleep 75 s, 42 of 60 server reads `asleep` true): 92 minutes flagged asleep, every HUNGER and THIRST delta 0, every FATIGUE delta negative, −4.56e-4 to −7.99e-4, mean −6.15e-4 per game minute; 13 minutes inside the hold read `asleep` false at the minute and still show FATIGUE deltas of −4.56e-4 to −6.85e-4. The mid-hold pair read 0.09977 on the client against 0.1 on the server.
- **E** (`settimespeed 30`, the multiplier 145.10; 23.41 game hours across the reads): 309 minutes per user in `agg`, the last 107 ring rows per user read, every delta 0; the multiplier read 4.781 after the restore.
- **F** (`admin`'s stats object hoisted): `benchSet` (three sets) 0.8, 0.9 and 0.6 µs per call (10 000 calls each); `benchGetSet` (three gets and three sets) 1.4, 1.6 and 1.6 µs; `benchNoop` 0.09 µs (100 000); `benchMinute` (the probe's whole instrumented minute for one player: name, asleep, six reads, three writes, the ring string) 11 µs (2000).
- **Z**: no line naming the probe file; `writeErrors` `0` over 3215 writes in 737 minutes.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, two idle characters, one host. |
| `predictions`, `constants`, `deviations`, `world_changes`, `meta.desk`, `meta.routes`, `meta.targets`, `meta.ring_row`, `verdicts.*.predicted` | the driver's tables and text | Written before the run; not readings. |
| `phases.A.admin.bootFired`, `phases.A.admin.bootSet`, `verdicts.A.observed.admin.bootFired`, `verdicts.A.observed.admin.bootSet` | `1`, the four keys 0 | The client's handler ran, but where the client's `OnGameBoot` falls against its own `Load` was not read; the client's statics play no part in the player updaters. |
| `phases.A.server.fileScopeDayLength`, `verdicts.A.observed.server.fileScopeDayLength` | `4` | Only that the file scope did not see the profile's 1; which default or file the 4 came from was not read. |
| `verdicts.D.observed.ring.admin.awake` | 13 rows, dF −4.56e-4 to −6.85e-4 | Minutes inside the sleep hold whose `isAsleep` read false at the minute; the hold re-asserts the flag every tick, so the minute's other ticks were asleep. Not an awake reading. |
| `phases.D.mid_pair.client`, `verdicts.D.observed.mid_pair.client` | fatigue 0.09977, `asleep` false | The client's copy at one instant inside a write minute; its asleep flag is the client's own. |
| `verdicts.B.observed.autodrink_before`, `verdicts.B.observed.autodrink_after` | no container | Auto-drink had no source, so B says nothing about auto-drink under the writer. |
