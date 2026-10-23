# `exp03-20260910-045523` reading guide

**`exp03-20260910-045523/body.json`** — produced by `testing/experiments/s03_body.py` at commit
`752d748`. Slice 03's **fix round 1** and its final fix wave changed the script in six ways this
file therefore predates. The rates it carries are unaffected — every fit is `d<value>/d(worldAge)`
and none of the changes touches that — but four keys in it are wrong, and are listed as *do not
cite* below.

- **Row 12 now primes calories per weight** (`CALORIES_FOR_WEIGHT` gained an entry for all
  eleven band weights). This run primed 500 kcal once and swept the weights against it, so
  `updateWeight`'s gain branch — which fires above `1000 + (w−80)·40`, i.e. above −400 at 45 kg
  and above +400 at 65 kg — nudged the low weights off their set points before
  `applyTraitFromWeight` compared them: `rows.r12_weight_bands.bands[].readBack` reads
  **45.0001 / 50.000099 / 55.000099 / 65.000099** against weights 45 / 50 / 55 / 65. **The
  exact-boundary behaviour at 50 kg and at 65 kg is therefore not measured by this file**, and
  the two `match: false` entries are that drift, not a disagreement with the code.
- **`prime()` now writes calories before the weight**, so no window is exposed to the previous
  row's calorie value for the round-trip between the two writes. Visible here as
  `rows.r7_weight_scaling.windows[3]` (the w = 60 window) running at a measured mean weight of
  **60.000757**: its 0.7503 burn ratio is computed against that measured weight, so it stands,
  but the set point did not hold.
- **A failed row now keeps its partial results.** `run_row` used to replace the whole row with
  `{error, traceback}`. That is why `rows.r2_asleep` in this file has exactly three keys: the
  successful `player.sleep true` reply and `heldAtWrite` were discarded by the error handler,
  not missing from the run. (The traceback shows where it really died — `s03_body.py:665` →
  `condition()` → `sample_window()` → `snap()`, i.e. inside the rate window, after the sleep
  write, all eight `prime()` writes and `settimespeed 30` had succeeded.)
- **The movement fit now requires ≥ 4 *consecutive* moving samples**, not 4 anywhere in the
  window. See *do not cite* below.
- **The client mirror is now read at every accelerated window's boundaries.** In this file
  `stats.get` on the client exists only at the session start, around row 1, and in rows 13 and
  14 — there is no client witness for rows 7, 8, 9, 10, 2 or 3–6.
- **The teardown now reads the clock back** (`time_after_restore`, a server-side
  `time.snapshot` after `settimespeed 1`). Absent here, so this run's restoration of the one
  world change it makes rests on the RCON echo in `settimespeed_restored` — which is the admin
  command repeating itself, not the world's state.

Two guards added after this run also change what a *future* file says about rows 8 and 12, and
both are listed as *do not cite* below: `summary.r8.hungerExactlyFlat` (fix round 1) and
`summary.r12.allBandsMatch` (the final fix wave — the script now writes `null` plus
`allBandsMatchReason` unless every band weight held exactly, and surfaces
`allWeightsHeldExactly` and per-band `heldExactly` in the summary; this file has none of those
keys, and its `rows.r12_weight_bands.allWeightsHeldExactly` is `null` because the per-band
`heldExactly` flag did not exist either).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| `rows.r3_6_movement.row3_walking.caloriesRatioVsIdle` and `summary.r3_6.row3_walking.ratio` | `measured: 1.2399` (vs `predicted: 4.875`) | The branch has 5 moving samples at indices 0, 1, 13, 27, 39 — one adjacent pair and three isolated ones. A least-squares line through them charges ~35 s of idle time to the walking branch, so the number measures the sampling gaps. The current guard writes `null` here. **Rows 3–6 are not measured.** |
| `summary.r8.hungerExactlyFlat` | `false` | The queued `ISEatFoodAction` completed 9 samples into the window, so the whole-window fit straddles the gate. The gated segment (samples 0–8) is in fact bit-exactly flat at hunger `0.2`; read `rows.r8_food_eaten.raw` split at sample 9. The current script writes `null` plus a reason when the gate is not up for every sample. |
| `summary.r12.allBandsMatch` | `false` | The two `false` bands are the 50 kg / 65 kg weight drift above, not a band-boundary mismatch. **Seven** of the eleven weights held exactly (70 / 75 / 80 / 85 / 95 / 100 / 105 — those whose gain threshold sat above the primed 500 kcal); the four low ones (45 / 50 / 55 / 65) drifted, and **nine of the eleven bands match**. The current script writes `null` plus `allBandsMatchReason` whenever a weight drifted, and surfaces `allWeightsHeldExactly`. |
| `rows.r8_food_eaten.foodTimerDecayNote` | `"~1200 units/real-s at settimespeed 30 (measured at speed 1 in the smoke run); 11000 from a real eat lasts <10 s there"` | Wrong in mechanism and ~20 % out in number. The decay is not on a frame/real clock: it is `minutesPerDay/30` units per **game**-second — **3.000** on this fixture's 90-minute day, measured flat across this row's own samples 0–8 (the same file's `rows.r8_food_eaten.raw`), 2.0 on the 60-minute default, frame-rate independent and, in game time, independent of `settimespeed`. The real wall-clock figure at speed 30 on this fixture is ≈1 438 units/real-s, not ~1 200. Read [`facts/body-and-weight.md#moodles`](../../../docs/facts/body-and-weight.md#moodles) instead; the note text is corrected in the current script. |
