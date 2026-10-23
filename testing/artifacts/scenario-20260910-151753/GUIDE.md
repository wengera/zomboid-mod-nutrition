# `scenario-20260910-151753` reading guide

**`scenario-20260910-151753/scenario-smoke_clock.json`** — written by `pzt scenario smoke_clock
--profile mod-under-test --speed 5` (66.4 s wall; `RESULT: PASS`, exit 0) on the CLI at `a6b0b54`.
The same profile down the scenario path as `scenario-20260910-134012`, at a speed on the cadence
ceiling rather than six times over it.

- **The first scenario artifact with a `verify` key.** `scenario.run` ran the profile's two
  `trait.check` probes once the client was ready — `verify: [{side: "server", ok: true},
  {side: "client", ok: true}]` — before `settimespeed 5` and the test. This is the live evidence
  for `[[verify]]` on the scenario path that [`platform/harness.md#profiles`](../../../docs/platform/harness.md#profiles)
  cites; `profile: "mod-under-test"` is the resolved name.
- **`cadence` on the ceiling's edge.** `ticks_per_world_min: 1.018` over `game_minutes: 20`
  (`world_min_per_wall_s: 7.57`, `ticks_per_wall_s: 7.7`, `wall_s: 2.6`), no `cadence_suspect`.
  `DayLength = 1` is a 15-minute day, so `--speed 5` demands `24 × 5 / 15 = 8` game-minutes per
  wall-second — exactly the `≲ 8` rule's limit — and the game's `EveryOneMinute` kept up (7.57
  delivered, one tick per game-minute). With the slice-04 anchors (7.99–8.00 on the 90-minute day
  at `--speed 30`) that is two profiles reaching the ceiling and holding; `scenario-20260910-134012`
  at `48` demanded is the one that fell to 0.22.
- `test.pass: true` (`"clock ok"`, 3 samples, `startedWorldAge 3.128 → endedWorldAge 3.455`,
  about 19.7 game-minutes by world age), `evaluation: {}` (no evaluator for `smoke_clock`),
  `faults: []`, `server_errors` empty, `build: 42.20.4`, `fixture: default`.
