# `x151w-20261005-161652` reading guide

**`x151w-20261005-161652/water_gate.json`** — produced by `testing/experiments/x151_water_gate.py` on HEAD `c0ac0bb` with the driver itself still untracked; it is committed unedited beside the artifact
(946.6 s wall; 4 005 735 bytes, sha256 `6aa82ea9…3e69602475`, byte-for-byte identical to the run copy). **Plan 4 Task 4, the water gate**:
one boot of `x15-water` (PZTestKit + NutritionRevamp Mode 1 with `NR.LegacyMirror` on + TKX_ThirstWatch, `Nutrition = false`) at DayLength 1, one admin character.
Mod `c0ac0bb` clean, harness Lua `a02db1f` clean, probe mod `76e95e4`, `doctor_clean` true; `verify` 6/6 `ok`; `client_lua_error` false.
The 6 server error lines are the one `ISDrinkFluidAction.new` raise of arm B2 (below). The first live use of Task 3's commands; every one answered. **Skew-free.**

How to read it. Every bus call is a row of `steps`. `TKX_ThirstWatch` samples the server's player every tick of an armed window
(10.1 ticks per second, arm F); `phases.<arm>.watch.fields` holds each field's first, last, min, max and sample count for that
window (n and absent reset before every window, so a stale key reads `reset`), `watch.raw` the first 50 ticks only. `summaries.<arm>`
adds the paired `witness.chain` polls (client first) of the five thermoregulator getters. `records` are the mod's store read
(`global:NutritionRevamp.players admin.*`), the drink wrapper's counters (`lua.global NutritionRevamp.server.intake.stats.*`) and the
client mirror's `pool_water`; `autodrink.probe` reads the server's THIRST and the first non-empty fluid container's litres in one tick.

- **S0**: the server's `autoDrink` flag read true by default; `autodrink.set false` read back false; no fluid container in the inventory.
- **A (getters live on the server; the climate half unmeasured)**: 600, 601 and 600 server samples, every getter numeric, no absent read.
  `climate.set 35` and `-10` answered ok with the admin value read back, and the manager's temperature read 35 and −10 at the next call,
  but the server's `extAir` read 22.0 at every tick of all three windows and `fluidsMult` 1.0: the character stood where the air read 22.0
  (outdoors on arm E it read 15.74–16.28), so whether the override reaches an outdoor character is unmeasured. The client's chain read
  `extAir` 27.0 and `energyMult` 1.0 at every poll of every window while the server's energy multiplier ran 1.0009 (S0) to 1.0659 (E).
- **B1 (as predicted, on 0.113 L)**: the RCON canteen arrived at the drink holding 0.11304 L, not its 0.9: `autoDrink` (flag back on)
  had drunk the rest at the THIRST writes before it. The drink counted 58 sips and 57 landings, `lastIntake` the canteen, `missing` empty;
  `pool.water` rose 0 → 112.867 over the 180 s poll with 0.168 left in the buffer — 113.036 g, the litres × 1000.
- **C (autoDrink fires under the handler; the wrapper does not see it)**: `C1` THIRST 0.0905–0.0991 for 11.5 s, litres held 0.6290;
  THIRST then crossed 0.1 by drain and the canteen fell to 0.4289 (0.2001 L) with THIRST 0.0047 after; `C2` THIRST written 0.3 read
  0.08562 at the next tick with the remaining 0.4289 L gone (the container branch); `C3` 0.5 with no water left: no drink. Sips, landings
  and pool plus buffer (113.036) unchanged across C. `autodrink.set false` at its end read back false; the next probe, 13.8 s later, read true.
- **D (as predicted)**: `water.take` found a source 5.7 tiles away holding 10000; the server's THIRST fell 0.4099 → 0.0012 within 7.3 s
  (window min 7.66e-5); sips, landings and the pool did not move. `watch.raw` covers the walk only.
- **E (trivial)**: `fluidsMult` 1.0 at every server tick idle (450) and walking (601); the walk moved `extAir` and the energy multiplier.
- **B2 (as predicted)**: `fluid.fill` filled a client `Base.Sportsbottle` with 1 L of Water; the server's chain found no such item; the
  server raised in `ISDrinkFluidAction.new` (`getFluidContainer` of nil, line 131); no sip, no landing; the client bottle kept 1 L.
- **F**: 102 ticks in 10.093 s, 10.106 ticks and 1.5994 world minutes per second.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one admin character. |
| `verdicts.A.verdict` | `falsified` | The driver's auto-grade: `extAir` did not move because the character's air read 22.0 throughout; the climate half is unmeasured. |
| `verdicts.*.verdict` | `see_raw` | Placeholders; the grades are the bullets above. |
| `records[*].mirror_pool_water` | 0 | The mirror is a snapshot sent on request, not a live read of the pool. |
| `phases.*.watch.raw` | — | The first 50 ticks (5 s) of each window only. |
| `phases.C.spawn.attempts[*].id` | 678729060 | B1's canteen: the client read finds the first canteen of the type. |
