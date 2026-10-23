# `x132d-20261005-060046` reading guide

**`x132d-20261005-060046/drink.json`** — produced by `testing/experiments/x132_drink.py` at commit
`f1968b6` (312.0 s wall; 126 330 bytes, sha256 `7fbeae35…c35e9562`, byte-for-byte identical to the run
copy). **X13**, the first live run of the intake engine: one boot of `x13-drink` (PZTestKit,
NutritionRevamp, TKX_DrinkHook), mod tree `ffaed41` clean, probe `2b8e702`, harness Lua `7710d2d` clean,
`doctor_clean true`, build 42.20.4; the six `verify` rows all `ok`, `mods_not_found` empty on both
sides, `server_error_count 0`, `client_lua_error false`, `field_count_failures` empty (every
`witness.moddata` read answered `count 4`). The acceptance run named is `x132c-20261005-041640`; this
boot is the smoke test of Task 12's harness commits. **Skew-free**: the driver was written for this
run and not edited after it.

How to read it. Six `snapshots` (`P0`, `P1_post`, `P3_pre`, `P3_post`, `P2_pre`, `P2_post`), each the
nutrition pair (client first), the `TKX_Drink` global-modData counters read on **both** sides (each Lua
state writes only its own table, so the `_server` keys are read off `moddata.server` and the
`_client` keys off `moddata.client`), and the `lua.global` walks of the probe's own counters, the
mod's `NutritionRevamp.server.intake.stats` and the admin record (`stomach.bulk` beside
`kineticsAge`, `lastIntake`). Phase order **P0, P1, P3, P2**. **P1**: client `drink.action
Base.Pop2` on an RCON-spawned full can. **P3**: client `drink.action Base.JuiceBox 0.5` — a
pre-run deviation from the brief's second Pop2, because an emptied Pop2 stays a `Base.Pop2` and
`findOrSpawn` takes the first (`deviation`). **P2**: the control, server `drink admin Base.Pop2` on a
second RCON can (one direct `DrinkFluid`, the timed action off). Calorie deltas are drift-corrected by
the P0 rate (`phases.P0.drift.kcal_per_s` −0.260 kcal/s, two server reads 6.5 s apart); bulk deltas
are decay-corrected by `exp(−ln2·Δ kineticsAge / 2 h)` (`bulk_read`), the ingest-only delta then
lying in the strict band `[pred × decay, pred]` (the driver's reported `accept_band` widens it by 3 % + 0.06).

- **The counters (raw, `snapshots.*.moddata`)**: server `updateEat_server` 0 → 29 → 61 and
  `complete_server` 0 → 1 → 2 across P1 and P3, unchanged across P2; the client's table stayed empty
  at every tag (all four keys `missing`, `keyCount 0`), and the client's `TKX_DrinkHook.updateEat` /
  `.complete` and the mod's client-VM `passthrough` stayed 0, so no `updateEat` call was seen in the
  client's Lua state (the client install itself is not witnessed). The mod's `stats.sips` matched the probe call for call (29, then 61),
  `landed` 28 and 59 (one call per drink removed no litres), `failures` 0, `lastError` unset.
- **The landing**: P1 bulk 7.638 → 10.743 over 0.233 game-hours, ingest delta 3.697 against
  `bulkOf(Cola × 0.3 L)` 3.87 (inside the strict decay band 3.570–3.87; the tolerance-widened `accept_band` is 3.394–4.046); `lastIntake` `fluid` / `Base.Pop2`, last sip
  0.01228 L. P3 ingest 1.150 against 1.265 (below the strict lower edge 1.180 and inside only the pre-declared tolerance band 1.082–1.363), `lastIntake` `Base.JuiceBox`, last sip
  0.00433 L. P2 ingest −0.054 (flat), `lastIntake` still `Base.JuiceBox`.
- **The stores**: P1 +120.48 kcal drift-corrected (raw +107.37 over 50.4 s), P3 +40.12, P2 ack
  `delta.calories` 120.00006 with the snapshot pair at +120.14. The client's calories trailed the
  server's by about one poll (`phases.P1.polls`, `phases.P3.polls`) and reached the same totals.
- **The automated grades of `P1a_sides`, `P1b_sips`, `P3_half` and `X13` are wrong and are
  re-graded off the raw reads**: the driver's `counters()` passed `witness.moddata`'s values, which
  the harness renders with `tostring`, through `_common.num`, which answers `None` for a string, so
  every present counter graded `null` (the absent `_client` keys graded 0). Off the raw reads P1a,
  P1b and P3 are as predicted and X13 is **settled CAN** (server fires, client silent, against a
  control that moved the stores and fired nothing). `P0`, `P1c_landing`, `P1d_calories`,
  `P1e_client_arrival`, `P2_control` read numbers only and stand; `P1f_mirror` is `trivial` (the
  mirror's `stomachFill` stayed 1, `received` 1).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, one fixture (DayLength 4, no time-speed change), one admin character, one can per arm. |
| `verdicts.P1a_sides`, `verdicts.P1b_sips`, `verdicts.P3_half`, `verdicts.X13`, `summary.x13`, `summary.verdicts` | `falsified` / `unmeasured` / `falsified` / `falsified` / `B7 negative` | The string-to-`None` grading fault above; cite the `snapshots.*.moddata` values and the `lua.global` walks. |
| every `counter_delta` and `summary.counters_*` `_server` key | `null` | The same fault: a parse failure, not an absent counter. |
| `greps.lua_errors` | server 17, client 12 | The `Exception thrown` alternative matched vanilla boot noise the server's collector treats as baseline; cite `server_error_count` 0. |
| `greps.syncitemfields.server` | 1 | The harness's own echo of the P2 reply; no SyncItemFields error. |
| `verdicts.P1e_client_arrival` as a latency | 3.521 s both | Each poll is a 1.5–2 s client-then-server pair; it bounds arrival within a poll or two and measures no latency. |
| `stomachFill` after P1 | `1` | Clamped at bulk ≥ 8; cite `stomach.bulk`. |
