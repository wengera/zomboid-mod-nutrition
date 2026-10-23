# `x151r2-20261005-202409` reading guide

**`x151r2-20261005-202409/records2.json`** — produced by `testing/experiments/x151_records2.py` on HEAD `e178a22` with the driver itself still untracked; it is committed unedited beside the artifact
(859.9 s wall; 3455094 bytes, sha256 `b0bd3273…66cd83767`, byte-for-byte identical to the run copy). **Plan 4 Task 17b, acceptance 3 (the four arms x151r falsified, re-read after the fix wave)**:
one boot of `x15-records` (as x151r), `Nutrition = false`, DayLength 1, `SleepAllowed` and `SleepNeeded` true in the server ini at seed, after ready and after the stop; one admin character (female, fat 22.4 kg,
lean 57.6 kg, `slowMet` false). Mod `e178a22` clean, harness Lua `839dfdb` clean, `doctor_clean` true; `verify` 10/10 `ok`; `client_lua_error` false, `server_error_count` 0, the mod's `nutrients.stats.errors`
0 over 2261 minutes with 3 day closes and no `lastError` on the nutrients, intake or kinetics side. An earlier attempt the same minute (`x151r2-20261005-202223`) was stopped by the host during the client boot
and took no reading (ruling B3-1: not a run); nothing of it is committed. **Skew-free.**

How to read it. Every bus call is a row of `steps`. A row of `records` is one `witness.moddata` call on the server's `NutritionRevamp.players` (the `fluids`, `acute`, stomach `buffer`, Plan 2 `pool` and
`nutrients.iron` tables, `kineticsAge`, the body and nutrient scalars; scalars come back as strings); `quick` are glycogen reads during the squats; `pending` the server's transient `pendingAlc`, `pendingCaf`
and `lastMealCa` reads during C and D; `stats_all` the server's INTOXICATION reads; `sleep_reads` the server's `asleep` flag during the hold; `edits` the `globalmoddata.setpath` replies. `summaries` are derived
in the driver with the mod's own kernel run offline (lupa) at `e178a22`: `summaries.B.intervals` divides each interval's pool iron increment by the buffer's iron decrement and replays the stomach per minute
from the interval's first read, with the record's absorbed iron inferred from `S` and `H`; `summaries.C`/`summaries.D` replay the gut lane from the first read after the drink's last landing and fit the gut's
half-life per read pair; `summaries.E.intervals` replays the glycogen step per minute from each read; `summaries.F.rows` recomputes `K.acute.iu` and checks the bout invariants on each read;
`summaries.t0_predictions` holds the whole-dose-at-once kernel peaks.

- **B' (iron)**: 0.046585 mg per mg emptied at 400 mg buffer phytate, rising to 0.170694 as the loaf emptied, every bread interval within 8.6e-7 of the replay; the steak on an empty buffer 0.18.
- **C' (coffee)**: buffer and pool caffeine 0 throughout; `gutCaf` 94.98 at the landing's close; gut half-life 0.5000 h; `caf` peak 82.920 mg.
- **D' (beer)**: buffer and pool ethanol 0; `bac` peak 0.005682 % (whole dose at once: 0.006244 %); `alcDay` 11.85; no hangover.
- **E' (glycogen)**: at rest the store relaxed toward its target with no shivering draw, falling from 460.78 and, after the edit to 150, rising; squats read MET 3.0 at 27 of 42 quick reads and 3.8 at one.
- **F' (the held sleep)**: 64.37 game hours in 120 s; `awakeH` 0 from the second hold read on, one bout of 54.57 h; `debtH` and `iu` 0 throughout.
- **I' (cost)**: `bench_fast` 3.13 (warm-up, discarded), 3.24, 3.47 µs per call; `tick.rate` 10.112 and 10.107 ticks per second.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` session, one fixture, one admin character. |
| `verdicts` | `see_raw` | Every phase's verdict is a placeholder; the grade is in the report and the register, off the records. |
| `summaries.B.intervals[*]` with `landed_inside` true | e.g. `perMg` 0.701889 | A drink or a meal landed inside the interval, so the buffer's decrement is not what emptied. |
| `summaries.E.intervals[*].pred_dGlyc` where the two reads' MET differ | e.g. −4.668673 | The replay holds the first read's MET across the interval; read the same-MET intervals. |
| `pending[*].lastMealCa` | null | The handoff lives inside one server tick (Kinetics sets it, Nutrients consumes it), so a bus read between ticks finds nothing; null is not a meal calcium. |
| `phases.S0.sentinels.NR_IntakeDrink_Installed`, `phases.S0.sentinels.NR_IntakeWorld_Installed` | null | `lua.global` answers no value for a table. |
| `logs.server_luaerr`, `logs.client_luaerr` | 40 and 20 lines | Vanilla `AdvancedAnimator$1.visitFileFailed` lines the driver's pattern matches; none is a mod error. |
