# `x131s-20261004-200859` reading guide

**`x131s-20261004-200859/swtraits.json`** — produced by `testing/experiments/x131_swtraits.py` at commit
`1ae3425` with the harness Lua clean (`harness_lua_dirty` false) and `doctor_clean` true. Plan 1 Task 15:
**X42** in one live session of one boot, profile `x13-swtraits` (PZTestKit, `SomewhatTraits` and
`SomewhatTraitsCore` from workshop `3498347699`, their live `42.15/` trees read 2026-10-04, and
`TKX_TraitProbe`; the fixture's own sandbox, `DayLength` 4, a 90-minute day). Both `[[verify]]` rows
passed (`SWTraits.traits` resolved with 32 keys; the probe's `version` 1), no mod was missing,
`server_error_count` 0, `client_lua_error` false, client quit and server stop rc 0; 480.5 s wall.
sha256 `9dfbd28e…6ade98898` (244 332 bytes), byte-for-byte identical to its run copy. **Skew-free**: the
driver was written before the run and not edited after it.

How to read it. `arms.a`–`arms.f` are six 60 s idle arms in run order: `a` weight 75 trait absent, `b`
weight 75 trait held, `c`/`d` the same at 85, `e`/`f` at 80. Each row is one server `stats.get admin`:
`wall` is the server's own `getTimestampMs` at the snapshot (the series' clock), `calories`, `weight`,
`running`, `sprinting` and `traitList` (`held` is the driver's test for `adaptivemetabolism` in it).
`phases.W75`/`W85`/`W80` hold each pair's writes: `weight_set` and `cal_set_absent`/`cal_set_held`
(server `nutrition.set`, each with its `nutrition.get` read back), the grant
(`moddata.set admin TKX_grant SWTraits:SWAdaptiveMetabolism`) and `grant_wait` (server reads until the
list held it), the removal and `remove_wait`. `phases.summary.<pair>` is the grading: `slope_absent` and
`slope_held` (least squares, kcal per second on the server's clock), `slope_diff`, `absent_residuals`
and `held_residuals` (each poll interval's calorie change less the control's slope times its length),
`held_steps` (the intervals whose residual exceeds `step_floor_used`), `step_spacing_s` (for each pair
of consecutive steps, `lo` and `hi` bound the true spacing, since a step lies anywhere inside its
interval) and `cadence_mean_s`. The server polls were about 1.3 s apart.

- **The write reaches the store.** Weight 75: twelve steps of 0.3319–0.3339 kcal (median 0.3332), mean
  cadence 5.01 s; the held slope -0.1749 against -0.2404 absent (+0.0655 kcal/s). Weight 85: twelve
  steps of -0.3313 to -0.3355 (median -0.3347), mean cadence 5.09 s; -0.3388 against -0.2724
  (-0.0665). Every `step_spacing_s` bracket holds 5 s. Predicted: 60 / 90 × 0.5 = 0.3333 kcal per 5 s.
- **The dead band.** Weight 80: held -0.25664 against absent -0.25673, no step.
- **The controls.** No trait-absent arm showed a step (`control_steps` 0, residual spread 0.001–0.002
  kcal); the three absent slopes stand as the weights over 80 (0.937 and 1.061 against 0.9375 and
  1.0625). The grant held at the first read after it each time, and every removal left the list empty
  (`TKX_TraitProbe.grants` 3, `removes` 3).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, one fixture, one idle player, one build, one day length; 60 s per arm. |
| `phases.summary.W75.step_spacing`, `phases.summary.W85.step_spacing`, `summary.spacing` | min 3.7 / 3.695 s, max 6.003 / 6.406 s | The spread of the spacings between the end stamps of step-bearing intervals: a step lies anywhere inside an interval of about 1.3–2 s, so the extremes measure the polling, not the cadence. Read `phases.summary.<pair>.step_spacing_s` (each spacing's `lo`/`hi` bracket) and `cadence_mean_s`. |
| `phases.<pair>.cal_set_absent.readback.calories`, `phases.<pair>.cal_set_held.readback.calories` | 999.46–999.87 | The read back trails the write by one bus round trip of vanilla's drain; the write was 1000. |
