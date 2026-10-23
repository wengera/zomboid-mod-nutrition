# `x132e-20261005-062748` reading guide

**`x132e-20261005-062748/eat.json`** — produced by `testing/experiments/x132_eat.py` at commit
`ac99278` (502.0 s wall; 300 090 bytes, sha256 `7b662d51…0a1ebe`, byte-for-byte identical to the run
copy). **X24 + X33, the first boot of session S-D, which ran no eat.** Profile `x13-eat` (PZTestKit,
TKX_ItemOverride, TKX_Nutrient, TKX_EatHook, NutritionRevamp — the probe loading **before** the mod),
mod tree `ffaed41` clean, probe `de10855`, harness Lua `7710d2d` clean, `doctor_clean true`, build
42.20.4; the five `verify` rows `ok`, `field_count_failures` empty; acceptance run
`x132d-20261005-060046`. **Consistent**: `x132_eat.py` was untracked at the run's commit, so git cannot confirm it unedited; `x132_eat_b.py`, the second boot's driver, differs from it only by the docstring, `PROFILE` and two `deviations` lines.

How to read it. Every completed eat (`Q1`–`Q4`, `P5`, `A6`, and `A7`/`A8`, whose stops did not
cancel) recursed between the two `ISEatFoodAction.complete` wrappers: TKX_EatHook wrapped at file
load, NutritionRevamp wrapped over it, TKX_EatHook re-wrapped at a boot event (`OnGameBoot` or `OnServerStarted`), and its first
closure — still inside the mod's wrapper — calls its saved original through `TKX_EatHook_Installed.orig`,
which the re-wrap had overwritten with the mod's wrapper. Each eat's `delta` reads `completes_server`
+498 and the mod's `eats` +497 for **one** action (the recursion depth to the Kahlua stack overflow),
`failures` +3, `lastError` `Stack overflow java.lang.RuntimeException`, the calories flat
(`kcal.server_corrected` within ±0.4) and the item untouched (`item.hungChange` −0.16, and in `A8` the −0.005 the guard arm set);
`server_errors` hold the overflow traces and `NetTimedAction.perform> Exception thrown` (112 server
errors). `OnEat` never fired (`onEat_server` +0): `Eat` was never reached. `A8.item_set` /
`A8.item_confirm` show the guard armed (`hungerChange` −0.005, `guard_value` 0.5) and the two
`player.stop` acks (`A7.stop_ack`, `A8.stop_ack`) sent 2.02 s after the queue; `cancels` stayed 0 in
both, the first reading that the bus's stop does not cancel a started eat. P0 stands: the record seeded
(`stomach.bulk` 7.683), both mod wraps and the probe's installed, `options.mode` 1 (takeover).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` boot**; the eat never ran, so nothing about X24, X33 or the intake landing was read. |
| `verdicts`, `summary` (every phase after `P0`) | `unmeasured` / `falsified` | The wrap cycle above, not a reading of the question each phase asks; `verdicts.A6_completed` `falsified` is the cycle too. Cite `phases.*.delta` and `server_errors` for the cycle itself. |
| `phases.*.delta.eats`, `phases.*.delta.completes_server` as a count of eats | `497`, `498` | One action recursing, not 497 eats. |
| `greps.lua_errors` | server 20, client 20 (saturated) | Vanilla boot noise plus the overflow traces; cite `server_error_count` 112 and `server_errors`. |
