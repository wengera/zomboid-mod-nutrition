# `x131c-20261004-181223` reading guide

**`x131c-20261004-181223/calcrepro.json`** — produced by `testing/experiments/x131_calcrepro.py` at commit
`0cc000d` (mod tree at `65d1e8d`, clean; probe mod `TKX_CalcStats` at `8783438`; harness Lua at `42425e9`,
clean; `doctor_clean true`; `acceptance_run "x131b-20261004-175911"`; 1123.0 s wall; 792 121 bytes, sha256
`21073741…8e473485`, byte-for-byte identical to the run copy). Plan 1 Task 11: **X34** with **X35**, **X32**
and **X46** riding, one session of **three boots** in one driver, each restored from the golden fixture into
its own run sub-directory and torn down before the next, all at `DayLength = 1` (a game-hour is 37.5 s wall):
`boots.A` the overlay control (`registered false`), `boots.B` the takeover (`registered true`), `boots.C`
the probe mod's registrant arms. Every boot: verification rows all `true`, `mods_not_found` empty,
`server_error_count 0`, `client_lua_error false`, no trace or `STACK TRACE` line in either log.
**Skew-free**: the driver was written before the run and not edited after it. A first launch under the
prefix `x131-calcrepro` was stopped while boot A's client was still joining, before any reading (the
register's run-id pattern refuses a hyphenated prefix); its run dir is not evidence and was not copied.

How to read it. A and B each carry nine hourly samples `boots.<A|B>.samples[k]` (k = 0–8, taken at whole
clock hours 11:00–19:00 in both boots), each a server `stats.all` (24 stats, `missing` empty on all 18) with
its own `worldAge`, a server `stats.get` (`body`), and the handler's `failures`, `disabledAt` and
`lastError`. `phases.X34.per_stat.<stat>.rows[k]` compares each segment's rate per game-hour (the delta
over the segment divided by that segment's own world-age span) of B against A, band
`max(2 % × |A rate|, 1e-4)`. `boots.B.x35` holds the sentinel window, taken after B's eighth sample;
`boots.A.x35` the same reads with no sentinel. `boots.C.arms.<arm>` holds each 20 s-wall arm (about 32
game-minutes): the key set, the counters at its start and end (client first), the `stats.all` thirst
series and the calorie store at its ends; `phases.C.arms.<arm>.fit` is the least-squares thirst slope per
game-second against `stats.all`'s own world age.

- **X32 — any registrant skips the updaters; the hook never fires on the client** (`verdicts.X32`,
  `verdicts.X32-client`, `phases.C`). `c1_calc` (no-op handler added through `Hook.CalculateStats.Add`):
  thirst delta exactly 0 over 36 reads and 1 886 game-s while calories fell 730.10 → 698.74, server
  `calls` +240; `c0_none` and `c2_calc_off`: slope 8.0e-6 per game-second, ratio 1.00000 to #0476. The
  client's `TKX_CalcStats.calls` read 0 at every one of the eight reads, the handler added there at file
  scope.
- **X46 — a second registrant changes nothing; a `false` return is not a control** (`verdicts.X46`).
  `c3_A` frozen (callsA +246); `c4_AB` frozen, callsA +245 and callsB +245; `c5_B` (B alone, returning
  false) frozen, callsB +247, callsA +0; `c6_none` thaw at ratio 1.00000. Calories drained in every arm.
- **X34 — `falsified` as graded, and largely trivial** (`verdicts.X34`, `phases.X34`). Thirst in band 8 of
  8 (B − A within 7e-6 per game-hour of 0.0288), hunger 8 of 8 (B ≈ 0.2 % lower, matching its higher
  starting hunger through `1 − h`). Idleness out of band in segments 1, 4, 5 and 7: each holds the clamp
  at 1 or the reset to 0 on movement, at a moment that differs between boots (starting idleness 0.542 in A
  against 0.577 in B; the walk's stop); segment 6, unclamped throughout, reads 0.600005 per game-hour in
  both. Stress, anger, morale (1.0), fitness (0.0) and endurance (1.0) flat in both boots, `trivial`.
  Fatigue sits at 1e-4 in both, the server's fatigue reset (character-stats.md#tick-order). B: `failures`
  0 at all nine samples, `disabledAt` never set, `calls` 41 → 3 391, hoist `missing` empty.
- **The sleep and running arms did not happen.** `player.sleep admin true` answered `after true` and the
  flag read `false` at the next sample in both boots (`boots.<A|B>.sleep_off.before false`);
  `player.walk 40 0 run` moved the player with `running false` at every check and endurance stayed 1
  (`boots.<A|B>.walks`). Segments 4–6 are walking and standing, whatever `constants.SEGMENTS` calls them.
- **X35 — `trivial` under its pre-written rule** (`verdicts.X35`, `phases.X35`). With `NR_sentinel 1` the
  server read 0.4242 within 0.76 s of the write; after a 1.5 s push window the client read
  `0.42419999837875366` (0.4242 as a float) at all ten resting pairs and all six "running" pairs, which
  stood still; `sentinelCalls` server 213, client 0. Off-arm: after `NR_sentinel 0` the client's endurance
  read 0.4290 → 0.4344 over four pairs and the server's rose at about 0.067 per game-hour — about 1.8e-4
  per handler call at the session's ~10.0 calls per wall second, some 180 × the 1e-6 tolerance — so the
  resting agreement is a discriminating reading of the order, and only the pre-written rule (a running
  pair required) makes the verdict `trivial`.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, one fixture, one player, one build. |
| `verdicts.X34`, `summary.verdicts.X34` | `falsified` | The falsifying stat is idleness, whose out-of-band hours are its clamp and reset timing, and seven of the nine graded stats are flat or pinned: read `phases.X34.per_stat.<stat>` row by row. |
| `phases.X34.per_stat.Fatigue.verdict` | `as_predicted` | Fatigue is pinned at 1e-4 by the server's fatigue reset in both boots; its rates are float noise of a few 1e-6 above the driver's 1e-7 "moved" threshold. Read it as trivial. |
| `constants.SEGMENTS`, `phases.X34.stress_first_measurement.segments` | `run`, `asleep` for segments 4–6 | The player walked (running false) and was never asleep at a sample: read `boots.<A\|B>.walks` and `samples[k].body.asleep`. |
| `boots.A.x35.run`, `boots.B.x35.run` | six pairs | No pair ran: the player stood still (`running false`, `moving false`). They are resting pairs. |
| `boots.B.x35.arrival` | one read at 0.76 s after the write | Inside the write's push window: an arrival-latency reading, ungraded. |
| `phases.X34.per_stat.Boredom`, `phases.X34.per_stat.Temperature` | `falsified` | Recorded, not graded: boredom follows idleness's clamp, and the body temperature is the thermoregulator's, outside the seven updaters, moved by the walk's timing. |
