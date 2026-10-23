# `fit-11g-20261012b` reading guide

The reading of a compact fit, shared by the six Plan 11g fit folders, opens [`fit-11g-20261012/GUIDE.md`](../fit-11g-20261012/GUIDE.md).

**`fit-11g-20261012b/fit-compact.json`** and **`grid.json`** — `fit-compact.json` 8818 bytes, sha256 `28505113…3b9dcf1c`; `grid.json` 392 bytes, `84e2e8aa…6be3cca9`; the full `fit.json` 13352874 bytes, sha256 `1827da9aa05d698f…`, in `testing/runs/fit-11g-20261012b/`. **Plan 11g Task 6c, the meal pool M fed at the eat; superseded.** `tools/fit_gut_satiety.py` on the working tree over `35d503b5` (`head`; the spec amendment: G fed at the eat, fullness counted to the hard capacity, the stability checks), whose build, rename (G to M), registry and refit landed in `bc92b13f`; the committed tree at `bc92b13f` reproduces the chosen loss (`evaluate({})` = 1.3609102108203415, the Task 6c report). The kernel it fitted and the registry it scored (`gut_oracles.py`, with the three stability checks) are `bc92b13f`'s.

How to read it. A grid of 2880 points (MEAL_STEEP 0.02, 0.035, 0.05, 0.08, 0.15; MEAL_HALF_LIFE_H 0.4, 0.6, 0.9, 1.5; MEAL_REQ 2, 5, 15, 50; FULL_WEIGHT 0.4, 0.5, 0.6; W_FAT 0.6, 0.8, 1.0; W_PROTEIN 1.5, 2.5; LIQUID_WEIGHT 0.033, 0.15; PROTEIN_FILL 8) and 6 refinement rounds at ×1.25, 2968 candidates; the chosen point is FULL_WEIGHT 0.5, LIQUID_WEIGHT 0.0151122, MEAL_HALF_LIFE_H 0.6, MEAL_REQ 4.47214, MEAL_STEEP 0.0559017, PROTEIN_FILL 8, W_FAT 0.894427, W_PROTEIN 2.5, at loss 1.3609102108203415. MEAL_STEEP sits inside its grid (not degenerate, the Task 6c review). **Status: superseded** by `fit-11g-20261012c`: the Task 6c review found LIQUID_WEIGHT unconverged toward 0 and, through the shared weight, driving the physical stomach fill (500 mL of water reading a fill of 0.010), so the physical fill was decoupled from the satiety weight (ruling T6c-1), Tieken's three entries became reading-kind (T6c-2) and S1233's slope joined the loss (T6c-3). Cite it only as that fit's record.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| every leaf of `chosen`, as the mod's satiety | LIQUID_WEIGHT 0.0151122 … | Superseded by `fit-11g-20261012c` and `fit-11g-20261012d` (rulings T6c-1 to T6c-5); never shipped past `bc92b13f`. |
| everything here, as a study reading | — | Model replays against the registry at `bc92b13f`. |
