# `x161p-20261006-035559` reading guide

**`x161p-20261006-035559/seats.json`** — produced by `testing/experiments/x161_seats_gate.py` on HEAD `5694730` (mod `9cc8d8d`, harness Lua `cfc8e7f`, probe `c9b76d0`, all clean) with the driver itself still untracked (written as `x162_seats_gate.py` and renamed before the commit, its content unchanged); it is committed unedited beside the artifact
(579.0 s wall for both boots; 2332146 bytes, sha256 `4d2c14bd…4e9c2ff862`, byte-for-byte identical to the run copy). **Plan 5 Task 4, gate 2 (the perception, trait and ownership seats)**: boot 1 `x16-seats` with `SleepAllowed` and `SleepNeeded` true and boot 2 `x16-seats-sleepoff` with both false, each in the server ini at seed, after ready and after the stop;
`Nutrition = false`, DayLength 1, one admin character. `doctor_clean` true; `verify` 8/8 `ok` on each boot; `client_lua_error` false and `server_error_count` 0 on each; the mod's `nutrients.stats.errors` 0 (512 and 188 minutes) and the handler's `fast.stats.failures` 0 (3226 and 1202 calls). This run is the smoke test of `sight.range`, `trait.local` and `event.watch` (`cfc8e7f`) and of TKX_StatWatch's hold and band arms (`c9b76d0`). **Skew-free.**

How to read it. `boot1` and `boot2` each carry `phases.<X>` (the arm's replies, and the tags of the reads it took), `phase_errors` (empty), `mod_error_checks`, the ini reads and `logs`. Every bus call is a row of `steps` with its `boot`. `stats_all`, `stats_get`, `health_reads` and `stat_writes` are the typed replies of both boots in order, each with its `boot` and `tag`; the `stats_all` index of every pair a row cites is in the register. `watches` are the TKX_StatWatch windows (`X82a`, `X82b`, `X82c`, `X87` on boot 1; `X83a`, `X83b`, `X83c` on boot 2), each also kept under its phase as `<arm>_watch`: per field `first`, `last`, `min`, `max` at full precision, `raw_strings` the first 60 ticks at 3 decimals; a hold's own status is `<arm>_hold_read` (`holdCalls` is the handler calls or ticks that wrote). The client probes' result files are kept whole: `X47.stand` and `X47.walking` (`anim-probe`), `X87.push_result` and `land_result` (`fall-probe`), `X86.W1_result`, `W2_result` and `W3_result` (`aim-probe`: `raw` the first 120 client ticks, `hist` every tick at 2 decimals, `events` the shots), `X84.result` and `X85.result` (`trait-watch`). `summaries` are copies made in the driver; cite the phases.
The subject stood at z = 1 after the X87 fall, and `zombie.near` then spawned no zombie, so X86's shots had no target. The HUNGRY damage tag fired every tick through the X87 window (401 in 400 samples): the handler's HUNGER had again reached level 4.

- **X82 (INTOXICATION)**: reduction 0 → 40 flat for 0.65 game hours; a beer +6.0 to 46, flat; reduction restored, a handler-path hold of 25 read 25 per tick and on the client, then decayed.
- **X84 (NIGHT_VISION)**: on the client 14 ms after the push, at 13:52.
- **X4b**: a client-only removal back on the client within 0.46 s, the server keeping the trait; with `SyncXp` in the same tick the server lost it at the next read; the edges emaciated, very underweight, very underweight, underweight; the mod restored 80 kg each time.
- **X85 (Short Sighted)**: sight range 6 → 2 → 6 (glasses) → 2 → 6 (trait removed).
- **X47 (`WalkSpeed`)**: 0.8 at every sample after the 0.3 write, both arms.
- **X87 (landing)**: one server `FALLDOWN` of 5.824, none on the client, no fracture; the direct client `DoLand(2.0)` fired nothing.
- **X86 (aiming)**: the aim flag false at 555 of 601 ticks; the delay 25.00 at every sample; the three attack events on the client.
- **X83 (FATIGUE, sleep off)**: the mod's write ~1e-4; the handler-path 0.42 on both sides; the `OnTick` 0.42 on the client only.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` session per boot, one fixture, one admin character. |
| `summaries` | copies | Derived copies of phase keys; cite the phase keys. |
| `boot1.phases.X82.a_watch.fields.intoxication.min`, `boot1.phases.X82.c_watch.fields.intoxication.min` | 0 | The window was armed before the write; the 0 is the pre-write value. |
| `boot1.phases.X86.W1_result.events`, `boot1.phases.X86.W2_result.events` | `ret=false` | `DoAttack`'s return value; the shot fired (the three events fired per shot); read `boot1.phases.X86.events_W2`. |
| `boot1.phases.X86.W2_unbump` | `ok` false | Sent after the window had closed, which had already dropped the standing bump. |
| `boot1.phases.X47.moving_server` | `moving` false | Read after the walking window, not during it. |
| `boot1.phases.X87.watch.dmg.HUNGRY` | 401 | The handler's HUNGER at level 4, not a landing reading. |
| `boot1.logs.server_luaerr`, `boot1.logs.client_luaerr`, `boot2.logs.server_luaerr`, `boot2.logs.client_luaerr` | 40, 16, 35 and 16 lines | Vanilla `AdvancedAnimator$1.visitFileFailed` and `IsoPropertyType.lookupOrDefaultStr` lines and the harness's own echo of the driver's error reads; none is a mod error. |
