# `x151s-20261005-165844` reading guide

**`x151s-20261005-165844/sleep_gate.json`** — produced by `testing/experiments/x151_sleep_gate.py` on HEAD `839dfdb` with the driver itself still untracked; it is committed unedited beside the artifact
(757.4 s wall; 1 324 818 bytes, sha256 `d788312a…989742129`, byte-for-byte identical to the run copy). **Plan 4 Task 5, the sleep and alcohol gate**:
**two serial boots in one file**, `boot1` of `x15-sleep` (the server ini's `SleepAllowed` and `SleepNeeded` read `false` before the start, after ready and after the stop)
and `boot2` of `x15-sleep-on` (both read `true` at all three reads), each PZTestKit + NutritionRevamp Mode 1 with `NR.LegacyMirror` on + TKX_SleepWatch + TKX_BoozeWatch,
`Nutrition = false`, DayLength 1, one admin character; boot 2 started only after `pzt doctor` read clean (`boot1.doctor_after`).
Mod `c7ec86e` clean, harness Lua `839dfdb` clean (the server `fluid.fill` twin and `pill.take.held`, committed before the run; this run is their smoke test),
probe mods `3d588b5`/`ed4804a`, `doctor_clean` true; `verify` 8/8 `ok` on each boot; `client_lua_error` false and no server error on either boot. **Skew-free.**

How to read it. Every bus call is a row of `steps`, its name prefixed `boot1_`/`boot2_`. `TKX_SleepWatch` and `TKX_BoozeWatch` sample the server's player every tick
of an armed window (10 ticks per second: 600 samples in 60 000 ms); `<boot>.<arm>.watch.fields` holds each field's first, last, min, max and count, `watch.resets`
(SleepWatch) the ticks whose fatigue fell by more than 0.1 from the tick before, `watch.hist` the asleep histogram, `watch.raw` the first 50 ticks only.
Beside each window `polls` are server `stats.all` reads (the 24 stats with `worldAge`, `mult` and the server wall `srv_wall`), E's `stats.get`; `writes`/`set` are
`stats.setany` replies (`after` is the read-back in the same call) with the next server read in `next`; `records` are the mod's store keys and intake counters.
`summaries` holds per-window slopes between the first and last poll.

- **boot 1, A (the reset, measured)**: three FATIGUE 0.5 writes each read back 0.5; the probe saw 0.5 at one tick and counted three falls of more than 0.1 in 301 ticks
  (`watch.resets` 3, `fields.fat.max` 0.5, `min` 9.949e-05); the next server read after each write was 9.99e-05 to 1.01e-04, the reset plus one update of the handler's accrual.
- **boot 2, A2 (held)**: S0 read FATIGUE 0.00637 at first sight (accrued from 0, no reset); the write read 0.50060 at the next read and 0.55930 at the window's last tick, no fall counted in 600 ticks.
- **boot 1, B (beer)**: the RCON `Base.BeerCan` (0.3 L of Beer) was drunk by the game's drink action, no fallback; INTOXICATION rose with the litres
  (0.630 at 0.244 L left, 1.287, 2.703, 4.124, 5.054 with the can empty) to a probe peak of 5.0947, then read 0.0914 at the poll 24.7 s after the peak read and 0 at the next.
  HUNGER read 0.46 before the drink (the ×1 rung). The mod's wrapper counted 34 sips and 33 landings; `pool.ethanol` 7.937 + 3.913 buffered.
- **boot 1, B2 (the decay)**: INTOXICATION written 40 fell 0.20123 per wall second and 7.5599 per game hour (`summaries.boot1.B2.intox_slope`), `mult` 4.781–4.799, 28.088 at the window's end.
- **boot 1, C (trivial)**: FATIGUE was at its reset value (0.00011), so the coffee's write could only clamp it to 0 for one tick (`fields.fat.min` 0.0) before the next update restored 0.00011.
- **boot 2, C2 (the write survives)**: 0.2 L of Coffee by one server `DrinkFluid` call lowered FATIGUE 0.5765 → 0.5566 in one tick and it held, accruing from there.
- **D, D2 (the pill)**: `pill.take.held` queued the RCON `Base.PillsVitamins`; the server copy's uses fell 1.0 → 0.8 on each boot and STRESS rose (0.0077, 0.0071) and decayed;
  on boot 2 FATIGUE fell 0.6040 → 0.5641 in one tick; on boot 1 nothing showed (the reset). No intake counter moved, the caffeine pool held 0 and `lastIntake` did not change.
- **boot 2, E (a held sleep, sleep allowed)**: the probe read asleep at 1014 of 1200 ticks; the world clock ran 61.764 game hours in 115.998 s of server wall
  (`summaries.boot2.E.fatigue_slope`); FATIGUE fell 0.6009 → 0.0022 by world age 30.08 h and held 0 to 0.0022 after; HUNGER read 1 and THIRST 0.544 after the hold.
- **The OnPlayerUpdate read**: SleepWatch's `fatUpd` (an `OnPlayerUpdate` handler in the server file) stayed unset (`absent`) in all seven windows, 2903 ticks.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` session of two boots, one fixture, one admin character. |
| `boot*.*.watch.raw` | — | The first 50 ticks (5 s) of each window only. |
| `boot*.*.watch.fields.asleep`, `boot*.*.watch.fields.dUpd` | n 0, `reset` | The probe tracks a boolean only in its histogram and `dUpd` needs `fatUpd`; read `watch.hist`. |
| `summaries.*.fatigue_slope.per_wall_s`, `summaries.*.fatigue_slope.per_game_h` | e.g. 0.3567 | First-to-last over a window that holds a write, a drink, a pill or a whole sleep; read the polls either side. |
| `summaries.boot1.B.intox_slope.per_wall_s`, `summaries.boot1.B.intox_slope.per_game_h` | −0.0054, −0.2022 | Spans the rise and the fall; read `boot1.B.polls`. |
| `boot1.S0.markers.NR_IntakeDrink_Installed`, `boot2.S0.markers.NR_IntakeDrink_Installed` | null | `lua.global` answers no value for a table; the wrapper counted sips on boot 1. |
