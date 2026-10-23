# `x151t-20261005-183551` reading guide

**`x151t-20261005-183551/thirst.json`** — produced by `testing/experiments/x151_thirst.py` on HEAD `cac63cc` with the driver itself still untracked; it is committed unedited beside the artifact
(1131.5 s wall; 3 179 355 bytes, sha256 `793e9459…8c423cf3`, byte-for-byte identical to the run copy). **Plan 4 Task 16, acceptance 1 (thirst and water live)**, the first boot of the whole Plan 4 build:
one boot of `x15-thirst` (PZTestKit + NutritionRevamp Mode 1 with `NR.LegacyMirror` on, `OnsetSpeed` 1, `DeficienciesCanKill` true + TKX_ThirstWatch), `Nutrition = false`, DayLength 1,
the fixture's sleep options false/false, one admin character (read at first sight: female, fat 22.4 kg, lean 57.6 kg). Mod `cac63cc` clean, harness Lua `839dfdb` clean, probe mod `76e95e4`,
`doctor_clean` true; `verify` 6/6 `ok`; `client_lua_error` false, `server_error_count` 0, the mod's `nutrients.stats.errors` 0 over 1689 minutes and no `lastError`. **Skew-free.**

How to read it. Every bus call is a row of `steps`. The mod's record is read off the server's global modData `NutritionRevamp.players` in one `witness.moddata` call per row of
`records` (the `fluids` and `acute` tables, the stomach `buffer`, the body and nutrient scalars, one server tick each; body and nutrient scalars come back as strings); each phase names its rows
by `tag` (`phases.<arm>.polls[*].rec`, `before`, `after`, `holds`). `stats_pairs` are client-first `stats.get` pairs (THIRST and the moodle levels on each side). `phases.<arm>.watch` is a TKX_ThirstWatch
window (the server's THIRST every tick: `fields` first/last/min/max/n, `raw` the first 50 ticks only, five decimals). `phases.D.fast`/`slow` are quick reads of `autoDrop`, the buffer's water and the
canteen's litres (`probe`). `edits` are the `globalmoddata.setpath` and `sandbox.var` replies. `mirror_checks` are a fresh client `requestMirror`, the client's mirror keys, then a server record.
`summaries` are derived in the driver: `summaries.<arm>.series` copy record values; `summaries.A`/`B` `cmp` pair each live value with the mod's own kernel run offline (lupa) on the basal loss alone.

- **A (first sight)**: 4.949 game minutes after the fluids' creation `water` read −9.280568 g (the basal draw −9.280121), `na` the basal draw exactly; `epoch` 0, `allReplete` true, `frozen` true.
  THIRST stepped once per slow minute to the stamped target; it rose 0.015177 → 0.054019 over the 60 s window with the view.
- **B (ten hours at rest)**: at 604.93 game minutes `dehydPct` 1.43687, `thirstTarget` 0.24594, `na` the kernel's basal value exactly, `water` 15.25 g below the basal-only kernel value
  (the prediction leaves out the cold-diuresis term at the `coldMult` 1.009–1.023 the record read). The moodle read 1 from THIRST 0.1255 and 2 at 0.2697 on both sides.
- **D (the bracket)**: a server canteen of 0.9 L drunk by `autoDrink` in two sips one stamp apart, each landed through `autoDrop`; no wrapper sip.
- **C (1 L)**: 61 sips and landings; the water plus buffer balance rose 999.29 g net of the basal draw; the view fell at once and the deficit as the water absorbed; the surplus cleared.
- **F (cola)**: 30 sips, 29 landings; 12.0000005 mg of sodium accounted (absorbed plus buffered), the seed's 0.3 L × 40 mg/L.
- **F2/E (edits)**: +8 L read naPlasma 113.03 with the target 0; na −1000 at a 2.13 % view read 121.23 with the target 0.11; the kill cap held the target at 0.83 at an 8.94 % view and lifted to 1.0.
- **I (world water)**: a source 5.7 tiles away; 13 world sips and 5 landings; the balance rose 831.49 g net of the basal draw; the view fell 0.41193 → 0.24198.
- **G (trivial)**: the walk took `body.met` to 3.0 at most, so the sweat term stayed 0 and `sweatActive` false.
- **H (cost)**: `bench_fast` 3.15, 3.25, 3.08 µs per call; `tick.rate` 10.105–10.107 ticks per second.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` session, one fixture, one admin character. |
| `verdicts` | `see_raw` | Every phase's verdict is a placeholder; the grade is in the report and the register, off the records. |
| `summaries.B.hand_80kg_male` | e.g. thirst 0.31421 | The Task 11 hand case (80 kg male), not this run's female subject. |
| `summaries.F2`, `summaries.E` (the `kernel` sub-keys) | e.g. c 0.80760 | The kernel view on the first-sight mass (80 kg) while the live mass had moved to 79.697 kg; read the live `c`, `naPlasma` and `thirstTarget` beside them. |
| `phases.S0.sentinels` | null | `lua.global` answers no value for a table. |
| `phases.S0.nutrients_stats.heals`, `phases.A.nutrients_stats.heals`, `phases.Z.nutrients_stats.heals` | null | No such counter. |
| `logs.server_luaerr` | 40 lines | The driver's own pattern also matches the harness's `lua.global` log lines for the mod's error fields; none is a mod error. |
