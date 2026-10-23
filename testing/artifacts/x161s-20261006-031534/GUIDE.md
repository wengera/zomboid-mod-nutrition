# `x161s-20261006-031534` reading guide

**`x161s-20261006-031534/surfaces.json`** — produced by `testing/experiments/x161_surfaces_gate.py` on HEAD `d2301d6` (mod `9cc8d8d`, harness Lua `8da117d`, probe `b3469c9`, all clean) with the driver itself still untracked; it is committed unedited beside the artifact
(716.4 s wall; 3915399 bytes, sha256 `0b10b090…cb59f42b01`, byte-for-byte identical to the run copy). **Plan 5 Task 3, gate 1 (the health, stat and body-part surfaces)**: one boot of `x16-surfaces`, `Nutrition = false`,
DayLength 1, `SleepAllowed` and `SleepNeeded` true in the server ini at seed, after ready and after the stop; one admin character. `doctor_clean` true; `verify` 6/6 `ok`; `client_lua_error` false, `server_error_count` 0, the
mod's `nutrients.stats.errors` 0 over 1028 minutes and no `lastError`. An earlier attempt (`x161s-20261006-031310`) was stopped by the host for low memory during the client boot and took no reading (ruling B3-1: not a run);
nothing of it is committed. **Skew-free.**

How to read it. Every bus call is a row of `steps`. `stats_all` holds every `stats.all` reply on either side (`side`, the answering side's `sideWall` in ms on the one shared machine clock, `worldAge`, `mult`, `stats`
keyed by registry id); `stats_get`, `health_reads`, `part_reads`, `part_writes`, `stat_writes`, `temp_reads`, `regen_reads` and `regen_writes` are the typed replies, each tagged. `watches` are the TKX_StatWatch
windows in order (`X78`, `X81`, `X88`, `X75a`, `X75b`, `X75c`, `X76a`, `X76c`, `X35`): per field `first`, `last`, `min`, `max` at full precision, `raw` the first 60 ticks parsed from `raw_strings` (3 decimals,
TEMPERATURE and core 2), `dmg` the `OnPlayerGetDamage` tag counts and sums, where `-1` is the value the driver wrote before the window (never fired in it); a damage tag that neither reset nor fired in a window carries the previous window's count (`BLEEDING` reads 151 in every window after X78's, and `SICK` 287 in X35's). `phases.<X>` reference those rows by tag;
`summaries` are derived in the driver (least-squares slopes, the session clock `summaries.clock`: 37.59185054444087 wall seconds per game hour, multiplier 4.5155–4.8053 per tick, 10.105 ticks per second).
The character's HUNGER, which the mod's handler writes, rose from 0.0229 at first sight to 1 by world age 9.43 h, so the HUNGRY moodle read level 4 from the X80 phase on: every later window carries the HUNGRY
drain (one tag per tick) and the regeneration tier 3.

- **X75 (POISON)**: 8 written held and fell 1.80001 per game hour, FOOD_SICKNESS rose 5.40003 per game hour; no POISON tag at POISON 24 with FOOD_SICKNESS 11–13; with FOOD_SICKNESS 24 the tag fired 538 times once it crossed 25.
- **X76 (FOOD_SICKNESS)**: 30 at POISON 0 fell 2.69995 per game hour; the client copies 29.83, 59.84 and 94.94; at 95 the SICK tag fired 287 times, 0.0790 per tick.
- **X77 (health.reduce 10)**: the client's overall and part health matched an earlier server read within about one read interval from the second client read on.
- **X78 (bleedingTime 20)**: the client read the value without `syncBodyPart` 1.27 s after the write and stepped with the server every ~1.8 s; with it, at once.
- **X79 (infection)**: +0.01809 per game hour untreated, −0.35914 with alcohol; the two-call fold read 1.18 × the vanilla slope.
- **X80 (regeneration)**: both windows at HUNGRY level 4 (tier 3): the halving unmeasured; the written constants held for 31.9 s.
- **X81 (TEMPERATURE)**: one write of core + 0.4 moved the core 0.20000 at the next tick.
- **X88 (delta 0.5 per tick)**: UNHAPPINESS +0.5 per tick, PANIC +0.32044; after the window PANIC fell, UNHAPPINESS stayed 100.
- **X35 (ENDURANCE 0.6)**: the client's copies lagged the server's series by 370–1162 ms.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` session, one fixture, one admin character. |
| `verdicts` | `see_raw` | Every phase's verdict is a placeholder; the grade is in the report and the register, off the raw. |
| `summaries.X75.a_poison_watch`, `summaries.X75.a_fs_watch` | e.g. `per_game_h` 3.2368 | The window was armed before POISON was written, so `first` is the pre-write 0; read `summaries.X75.a_poison_statsall` and `a_fs_statsall`. |
| `phases.X76.watch_a.dmg` | `POISON` 538 | The counters were not reset before this window; the values are X75c's. |
| `summaries.X76.c_dmg`, `summaries.X75.c_dmg` | — | Read `phases.X76.watch_c.dmg` and `phases.X75.watch_c.dmg` (the same values; cite the raw). |
| `phases.X75.c_health_after`, `phases.X76.c_health_after` | `c_health_after` | Both phases wrote the same tag; read `health_reads[109]` (X75) and `health_reads[137]` (X76). |
| `summaries.X81.fraction_of_gap` | 0.49986 | Measured from the `temp.core` read before the write, not the stat the write replaced; read `phases.X81.write` and `phases.X81.watch.fields.core`. |
| `summaries.X80.pred_per_game_h` | 3.6, 1.8 | Tier-0 predictions; both windows ran at tier 3. |
| `logs.server_luaerr`, `logs.client_luaerr` | 40 and 12 lines | Vanilla `AdvancedAnimator$1.visitFileFailed` and `IsoPropertyType.lookupOrDefaultStr` lines and the harness's own log echo of the driver's `lastError` and `errors` reads, all of which the driver's pattern matches; none is a mod error. |
