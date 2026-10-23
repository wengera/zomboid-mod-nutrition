# `scenario-20260910-134012` reading guide

**`scenario-20260910-134012/scenario-smoke_clock.json`** — written by `pzt scenario smoke_clock
--profile mod-under-test --speed 30` (63 s wall; `RESULT: PASS`, exit 0). The same profile down
the scenario path: `profile: "mod-under-test"`, `fixture: "default"`, `build: 42.20.4`,
`side: "server"`, `user: "admin"`, `test.pass: true` (`"clock ok"`, 3 samples at game-minute 20),
`evaluation: {}` (no evaluator is registered for `smoke_clock`), `faults: []`, `server_errors: 0`.
The server log again carries `loading KeenPerception`, and the run's `pzt_SandboxVars.lua` again
reads `DayLength = 1` / `Zombies = 6` at 189/184 after the boot-time rewrite.

- **This run ran no `[[verify]]` probes, and the file has no `verify` key.** That is historical,
  not a property of the scenario path: `scenario.run` did not run a profile's probes until slice
  07's final fix wave (see the skew list above), so this artifact evidences that the profile's
  mods **loaded** — the `loading KeenPerception` line and the `profile` field — and not that they
  took effect. `run-20260910-133657` is the took-effect evidence for this mod set.

- **Read `cadence` as a finding about the profile, not about the harness.** This run is flagged
  `cadence_suspect: true` at `ticks_per_world_min: 0.22` — the tick counter advanced 20 times
  while the world advanced **91.05** game-minutes (`(endedWorldAge − startedWorldAge) × 60`;
  `world_min_per_wall_s: 45.89` × `wall_s: 2.0` is the same number rounded). The counter is
  advanced by the **game's** `Events.EveryOneMinute`, which the harness subscribes to — so what
  fell behind is the event, not the harness's arithmetic. The cause is the *combination* in this
  profile: `DayLength = 1` is a 15-minute day, so `--speed 30` demands `24 × 30 / 15 = 48`
  game-minutes of world clock per wall second, and the event delivered **10.08/s**
  (`ticks_per_wall_s`) — the only measurement of its ceiling anyone has. **8/s is the highest
  demand known to be sustainable**, not a measured ceiling: the three slice-04 scenario artifacts
  ran the same `--speed 30` on the same fixture at its **default** `DayLength = 4` (a 90-minute
  day → `24 × 30 / 90 = 8` game-min/wall-s) and recorded `ticks_per_world_min: 1.0` with
  `ticks_per_wall_s` 7.99–8.00. Where the real ceiling sits between 8 and 10.08 is unmeasured. So
  keep `24 × speed / day_minutes ≲ 8`; on `DayLength = 1` that is `--speed 5`, not 30.
- **`smoke_clock`'s own verdict is unaffected** and this is why it still reads PASS: every
  assertion it makes is counted in *ticks* (`t:every(5, …)`, `t:eventually`, `t:at(20, …)`), so
  the test measures the scheduler against itself. Its PASS here is **tick-relative and is not a
  clock proof at this cadence** — it says the scheduler dispatched in the right order, not that a
  game minute lasted a game minute. **Nothing fitted against the game clock on this run may be
  cited** — no rate, no per-game-hour figure, no `worldAge` span. Do not carry `DayLength = 1`
  into a nutrition scenario at speed without re-reading `cadence` first.
