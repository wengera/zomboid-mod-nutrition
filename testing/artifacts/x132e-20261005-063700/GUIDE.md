# `x132e-20261005-063700` reading guide

**`x132e-20261005-063700/eat.json`** — produced by `testing/experiments/x132_eat_b.py` at commit
`ac99278` (442.0 s wall; 282 602 bytes, sha256 `2985ca40…c257b36a`, byte-for-byte identical to the run
copy). **X24 + X33, the second boot of session S-D**, the driver `x132_eat.py` verbatim but for the
profile `x13-eat-b` (NutritionRevamp loaded **before** TKX_EatHook, so the probe wraps outermost at file
load and neither install re-wraps) and two `deviations` lines written before the boot (the first boot's
cycle; its `player.stop` not cancelling). Mod `ffaed41`, probe `de10855`, harness Lua `7710d2d` clean,
`doctor_clean true`, build 42.20.4; five `verify` rows `ok`, `server_error_count 0`,
`client_lua_error false`, `field_count_failures` empty. **Skew-free.**

How to read it. Pre-run deviations (`deviations`): X24 eats `Base.Banana`, the only item
`TKX_OnEatProbe` is registered on (its Apple fires nothing); `Base.Apple` is 400 kcal in this profile
(TKX_ItemOverride); `foodtimer.set admin 0` before every action. Every phase is an `eat_phase` (the
`eat.action` ack, nutrition polls client first until the calories land, an immediate client
`stats.get`, then ~1.5 s later a `snapshot`: `stats.get` client then server, the mod's record as one
`witness.moddata` of the global table `NutritionRevamp.players` — values are **strings**, parsed by
`to_num` — the intake counters and the probe's globals by `lua.global`, the `TKX_eat_onEat_*`
player-modData counters client then server (a `missing` key reads 0), and `item.get`). Every counter
is a delta against the preceding snapshot; calories are drift-corrected (`phases.P0.drift.kcal_per_s`
−0.254 kcal/s); buffer and bulk deltas are corrected by the kinetics decay over `Δ kineticsAge`.

- **X24, settled once per portion (`verdicts.X24`)**: four `eat.action Base.Banana 0.25` on one id
  (`1822709913`; `hungChange` −0.12, −0.08, −0.04, then consumed) each wrote +26.20, +26.13, +26.19,
  +26.19 kcal (server, corrected; the client the same to 0.1) and moved `onEat_server` +1, `onEat_client`
  +1, the probe's `calls` +1 on each side, `completes_server` +1 and the mod's `eats` +1 and `landed` +1;
  `P5`, a whole fresh Banana, +104.81 kcal and +1 on every counter. The hook's `lastFraction` read
  0.25, 0.3333, 0.5, 1.0 on both sides — `Eat`'s rescaled fraction.
- **The two fractions, live (`verdicts.TWO_FRACTIONS` `unmeasured` because of Q4)**: over Q1–Q3 the
  mod's `lastIntake.share` 0.25, 0.25000005, 0.25 beside `frac` 0.25, 0.33333340, 0.50000005, and the
  buffer's calories rose 25.95, 26.10, 26.10 (decay-corrected; band 23.8–27.1 against 26.25); the bulk
  0.259, 0.261, 0.261 against 0.2625. The per-quarter verdicts `Q1`–`Q3` are `as_predicted`.
- **The finishing eats land NaN (`Q4`, `P5`, `A6` `falsified`, correctly)**: from `Q4_post` on, the
  record reads `"nan"` for `lastIntake.share`/`frac`, `stomach.bulk`, every buffer key and
  `stomachFill`; the `lua.global` walks answer `null`; `stats.get` answers `hunger` `null` on **both**
  sides (the harness's rendering of a non-finite number). The jar explains the share: `Eat` zeroes
  `hungChange` then `UseAndSync` → `Use` → `Food.setCurrentUses` → `consumeHunger(0)` divides 0 by 0, so
  the raw hunger the wrapper reads after the original is NaN. The counters and the calories of those
  phases stand (Q4 +26.19, P5 +104.81, A6 +399.83).
- **The hunger term (Q1–Q3)**: the server's hunger ~1.5 s after each eat equals `1 − stomachFill` to
  1e-8 (`phases.Q*.hunger`); the eat's own hunger write did not survive the next push.
- **X33 unmeasured (`verdicts.X33`)**: `A6` (a whole 400-kcal Apple) completed: +399.83 kcal, `eats`
  +1, `cancels` 0. `A7` and `A8`'s `player.stop` (2.02 s after the ack; the eat lands about 6.8 s after
  it) did not cancel: each read `eats` +1, `cancels` 0, `onEat` +1 on each side and the whole Banana
  (+105.21, +105.31 kcal), the item consumed. `A8` ran on a **fresh** Banana (`A7` consumed its own)
  with `hungChange` set to −0.005 (`item_confirm`, `guard_value` 0.5): the completed eat delivered the
  whole item. Neither cancel arm reached `serverStop`; the bus has no cancel for a started action.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` boot**, one fixture (DayLength 4, no time-speed change), one admin character, one Banana in quarters and one of each other item per arm. |
| `verdicts.A7_cancelled`, `verdicts.A8_guard`, `verdicts.X33`, `summary.x33` | `unmeasured` | No cancel happened; these say nothing about `serverStop` or its guard. |
| `phases.A7.buffer`, `phases.A7.bulk`, `phases.A8.buffer`, `phases.A8.bulk` | predictions 0, `within false` | The prediction took the share of a cancel that never happened, and the store was already NaN. |
| every record value from `Q4_post` on, as a number | `nan` / `null` | The mod's NaN landing (above), not a stomach state. |
| `snapshots.*.stats.*.hunger` from `Q4_post` on | `null` | A non-finite hunger, not an absent read. |
| `greps.lua_errors` | server 20, client 20 (saturated) | Vanilla `AdvancedAnimator` boot noise; cite `server_error_count` 0. |
