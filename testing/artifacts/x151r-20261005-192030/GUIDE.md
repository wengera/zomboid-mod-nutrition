# `x151r-20261005-192030` reading guide

**`x151r-20261005-192030/records.json`** — produced by `testing/experiments/x151_records.py` on HEAD `d3ec889` with the driver itself still untracked; it is committed unedited beside the artifact
(1395.8 s wall; 4 660 536 bytes, sha256 `193f74cf…888d82eb2`, byte-for-byte identical to the run copy). **Plan 4 Task 17, acceptance 2 (the records, caffeine, alcohol, glycogen, sleep debt, refeeding live)**:
one boot of `x15-records` (PZTestKit + NutritionRevamp Mode 1 with `NR.LegacyMirror` on, `OnsetSpeed` 30, `DeficienciesCanKill` and `ExcessEffectsOn` true + TKX_ThirstWatch, TKX_SleepWatch, TKX_BoozeWatch),
`Nutrition = false`, DayLength 1, `SleepAllowed` and `SleepNeeded` true in the server ini at seed, after ready and after the stop; one admin character (read at first sight: female, fat 22.4 kg, lean 57.6 kg,
`slowMet` false). Mod `cac63cc` clean, harness Lua `839dfdb` clean, `doctor_clean` true; `verify` 10/10 `ok`; `client_lua_error` false, `server_error_count` 0, the mod's `nutrients.stats.errors` 0 over 3120
minutes with 4 day closes and no `lastError`. **Skew-free.**

How to read it. Every bus call is a row of `steps`. The mod's record is read off the server's global modData `NutritionRevamp.players`: a row of `records` is one `witness.moddata` call (the `fluids`, `acute`,
stomach `buffer` and Plan 2 `pool` tables, the body and nutrient scalars, one server tick; scalars come back as strings); a row of `nut` is two calls (the 27 per-nutrient tables, the epoch, `lastAgeH`,
`allReplete` and the pool); `quick` are glycogen reads during the squats; `stats_all` the server's INTOXICATION reads; `sleep_reads` the server's `asleep` flag during the hold; `vitc_reads` the vitamin C
table during arm H; `edits` the `globalmoddata.setpath` and `sandbox.var` replies. Each phase names its rows by `tag`. `summaries` are derived in the driver with the mod's own kernel run offline (lupa):
`summaries.A.intervals` replays the records between consecutive `nut` reads from the earlier read with the pool's absorbed increments spread evenly, `summaries.B` divides each interval's absorbed iron by the
iron that left the buffer, `summaries.C.series[*].thalf_fit` is the half-life of each read pair with no caffeine absorbed between them, `summaries.F_iu` recomputes `K.acute.iu` from each read's own
`acute` and `fluids`, `summaries.G.closes` replays each day close from the read before it.

- **A (the records at OnsetSpeed 30)**: vitamin C takes no dial: `p` 0.99977 → 0.83406 over 95.6 game hours, grade 1 throughout. Twelve grade changes (vitD, folate, magnesium, iodine, vitK, fibre)
  each fell inside the read bracket that holds the replay's crossing; the replay's grades equal the read grades at all 54 intervals; `epoch` 14 = 12 grade changes + the two excess-output changes of arm H.
- **B (iron)**: 0.179025–0.179274 mg absorbed per mg leaving the buffer with the bread's phytate in it, 0.18 exactly with none; the factor acts on each minute's emptied share.
- **C (coffee)**: 107.0 mg in buffer plus pool; `caf` peaked at 55.95 mg; 39 read pairs fit a half-life of 5.0000 h.
- **D (beer)**: 11.85 g ethanol in buffer plus pool and in `alcDay`; `alc`, `bac` and `alcPeak` 0 at every read.
- **E (glycogen)**: `body.met` reached 4.0; the store fell on the minutes above 3 MET and at rest under the shivering term; `bg` 5.0 at every read.
- **F (the held sleep)**: 64.08 game hours in 120 s; no asleep run reached an hour, so `awakeH` kept rising; three windows closed; `debtH` 6.58 → 0.14 → 0.
- **G (refeeding)**: four closes, the first after the edits: `starvedDays` 12 to 15, `refeedRisk` 2, no window, no event.
- **H (the excess dial)**: `x` held 0 at `e24` 2500 with the dial off and read 1 at the first read after it came on.
- **I (cost)**: `bench_fast` 4.42, 3.55, 3.42 µs per call; `tick.rate` 10.103 and 10.104 ticks per second.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` session, one fixture, one admin character. |
| `verdicts` | `see_raw` | Every phase's verdict is a placeholder; the grade is in the report and the register, off the records. |
| `records[*].nutrients.allReplete`, `nut[*].allReplete`, `summaries.A.intervals[*].allReplete` | null | `witness.moddata` lists a nested leaf whose value is false under `missing`; null here means false, not absent. |
| `records[*].nutrients.anaemia`, `records[*].nutrients.vitDClinical` | null | The same false-leaf reading. |
| `records[*].body.inDayClosed` | null before the first close | The field does not exist until Metabolism's first day close. |
| `summaries.C.series[*].pred` | e.g. 3.5285 | The replay spreads each interval's absorbed caffeine evenly, up to 0.164 mg off the exact step; read `caf` and `thalf_fit`. |
| `summaries.E.series[*].dGlyc_kernel_at_met` | e.g. −0.1824 | The work term alone, without the shivering term the kernel adds above `coldMult` 1; read the `quick` rows. |
| `summaries.F.pred.measured_share` | e.g. `awakeH` 37.52 | Replayed at the `asleep` share of 35 `stats.get` reads (0.771), not the record's per-minute share; read the `records` of the hold. |
| `phases.S0.sentinels.NR_IntakeDrink_Installed`, `phases.S0.sentinels.NR_IntakeWorld_Installed` | null | `lua.global` answers no value for a table. |
| `logs.server_luaerr`, `logs.client_luaerr` | 40 and 20 lines | Vanilla `AdvancedAnimator$1.visitFileFailed` lines the driver's pattern matches; none is a mod error. |
