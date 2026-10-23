# `x132b-20261005-071013` reading guide

**`x132b-20261005-071013/coboot.json`** — produced by `testing/experiments/x132_coboot.py` at commit `a02e8d9`
(477.1 s wall; 220 724 bytes, sha256 `5c9cb264…a542a5f4`, byte-for-byte identical to the run copy).
**X45a + X45b, session 1, two boots**: `boots.A` under `x13-coboot` (PZTestKit, NutritionRevamp,
ItemQuality, QuestSystem, QualityCooking, MoodleFramework, BeyondTen, TKX_EatProbe in `Mods=` order) and
`boots.B` under `x13-coboot-control` (the same without QualityCooking and its three requirements). Mod
`9f53324` (intake fix-3), probe `04cda41` (install once), harness Lua `7710d2d` clean, `doctor_clean true`
before each boot (`boots.*.doctor_clean`), build 42.20.4; four `verify` rows `ok` per boot,
`server_error_count` 0 in both. **Skew-free.** Acceptance run `x132e-20261005-063700`.

How to read it. Each boot reads the markers client first then server (`boots.*.markers.boot`, raw
`lua.global` replies; `boots.*.phases.markers` the summary), spawns a `Base.Apple` by RCON and waits for it
on the client (`boots.*.spawns`; `item.get` read 95 kcal, `hungChange` −0.16), then takes a snapshot
(`pre`), a 6 s calorie drift, a second snapshot (`pre2`, the baseline), `foodtimer.set admin 0`,
`eat.action Base.Apple 1`, nutrition polls until the server's corrected calories reach 92, and two
snapshots `post` (1.5 s later) and `late` (6 s after that). A snapshot is `stats.get` client then server,
`nutrition.get` server, the mod's record as one `witness.moddata` of `NutritionRevamp.players` (values are
**strings**, parsed by `to_num`), the intake and probe globals by `lua.global` on both sides, QuestSystem's
global store census (`global:QuestSystemPersistent players`) on both sides and the server's Apple.
`boots.*.phases.eat` holds the deltas: `kcal` (drift-corrected, `pred` 95), `probe`, `intake`, `finite`
(`blocking false` at `pre`, `post` and `late` in both boots: every mod value and HUNGER finite), `qc_store`.

- **X45a (`verdicts.X45a.observed.markers`)**: `QualityCooking.Server` a table (keyCount 1),
  `BeyondTen.VERSION` "1.3.4", `TKX_EatProbe.version` 1, `NutritionRevamp.version` "0.1.0", each on **both**
  sides; no join failure. The console grep (`boots.A.logs`) catches the engine's baseline
  `AdvancedAnimator$1.visitFileFailed` (31) and `IsoPropertyType.lookupOrDefaultStr` (5) exception lines,
  which the control boot carries too (16 and 5), two ItemQuality translation format warnings, and **one** Lua
  error from a co-booted mod: QuestSystem's client `OnGameStart` → `QuestTrackerPrefs.load:18` →
  `getFileReader` raising a Java `IOException` creating a file under a `QuestSystem/` folder the fresh client
  cache lacked (`boots.A.client_seen` carries `lua_error`; the client kept answering the bus).
- **X45b (`verdicts.X45b.observed`)**: boot A +94.80 kcal post, +94.93 late; boot B +95.34, +95.13; probe
  `enter` and `exit` +1 each, the client's 0 and 0; the mod's `eats` +1, `landed` +1, `failures` 0,
  `lastIntake.share` 1.0 in both. **`.outermost` read `true` in both boots** (also before the eat,
  `phases.eat.probe.outermost_pre`): the pre-registered `false` for boot A is falsified. The server log
  shows why: `[NutritionRevamp] intake: ISEatFoodAction.complete wrapped` at 07:10:28.907 precedes
  `[ItemQuality] server scripts loaded` at 07:10:28.931 — the server ran the mods' Lua in `Mods=` order, so
  the probe (last) wrapped QualityCooking's wrap, which wrapped the mod's. QualityCooking wrote no
  `cookingBuff` (`qc_buff_post` null; the store census `players` absent): the RCON Apple carries no cooking
  tier and `eatWithBuff` then only calls the original.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` eat per boot, one fixture, one admin character. |
| `verdicts.X45a.verdict`, `summary.verdicts.X45a` | `falsified` | The error pattern counted the engine's baseline exception lines present in the control too; read `verdicts.X45a.observed.markers` and `boots.A.logs.client_luaerr`. |
| `verdicts.X45b-A.verdict`, `verdicts.X45b.verdict`, `summary.verdicts` | `falsified` | Falsified on `.outermost` alone (predicted false, read true); every composition clause held — read `verdicts.X45b.observed.match`. |
| `boots.*.phases.eat.intake.bulk_delta` | 4.238 | A raw delta over a window of kinetics emptying, not decay-corrected; not a bulk reading. |
