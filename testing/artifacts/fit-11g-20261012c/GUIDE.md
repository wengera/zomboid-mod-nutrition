# `fit-11g-20261012c` reading guide

The reading of a compact fit, shared by the six Plan 11g fit folders, opens [`fit-11g-20261012/GUIDE.md`](../fit-11g-20261012/GUIDE.md).

**`fit-11g-20261012c/fit-compact.json`** and **`grid.json`** — `fit-compact.json` 14442 bytes, sha256 `23af38e7…562bbf2f`; `grid.json` 403 bytes, `2dfa1040…5b142ac0`; the full `fit.json` 53974539 bytes, sha256 `a37ca3bcacdaf730…`, in `testing/runs/fit-11g-20261012c/` (the 54 MB file ruling T6c-4 was made for). **Plan 11g Task 6c fix 1, the refit after the physical fill was decoupled; superseded.** `tools/fit_gut_satiety.py` on the working tree over `bc92b13f` (`head`), landed in `c2c96dd6` (the physical fill reads both lanes at density 1; the two "fed" gates read a food-only fill; Tieken read-only; `rolls98_slope` scored; LIQUID_WEIGHT fitted in (0, 0.19]); the committed tree at `c2c96dd6` reproduces the chosen loss (`evaluate({})` = 0.6718614860942925, the fix 1 report). The kernel and registry are `c2c96dd6`'s (38 scored oracles).

How to read it. A full grid of 11664 points (MEAL_STEEP 0.03, 0.045, 0.06, 0.08; MEAL_HALF_LIFE_H 0.4, 0.6, 0.9, 1.3; MEAL_REQ 1.5, 4.5, 15; FULL_WEIGHT 0.4, 0.5, 0.6; W_FAT 0.6, 0.9, 1.2; W_PROTEIN 1.5, 2.5, 3.5; LIQUID_WEIGHT 0.01, 0.1, 0.19; PROTEIN_FILL 4, 8, 12) and 20 refinement rounds at ×1.25, 11876 candidates; the chosen point is FULL_WEIGHT 0.517741, LIQUID_WEIGHT 0.19, MEAL_HALF_LIFE_H 0.583495, MEAL_REQ 3.80654, MEAL_STEEP 0.0353777, PROTEIN_FILL 8, W_FAT 0.881368, W_PROTEIN 2.4913, at loss 0.6718614860942925. **LIQUID_WEIGHT sits at its search bound 0.19**, a bound of the fix round's own, not a row: the fix 1 re-review found S1231's `rolls_drop` still passing past it. **Status: superseded** by `fit-11g-20261012d` (ruling T6c-5: S1231's null for water drunk alongside scored, the bound lifted to (0, 1]). Its `profile.LIQUID_WEIGHT` ends at the bound.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| every leaf of `chosen`, as the mod's satiety | LIQUID_WEIGHT 0.19 … | Superseded by `fit-11g-20261012d` (ruling T6c-5); its LIQUID_WEIGHT is a search bound, not a fitted value. |
| everything here, as a study reading | — | Model replays against the registry at `c2c96dd6`. |
