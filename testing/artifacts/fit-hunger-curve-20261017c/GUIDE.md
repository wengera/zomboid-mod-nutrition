# `fit-hunger-curve-20261017c` reading guide

**`fit-hunger-curve-20261017c/fit-compact.json`** — 22654 bytes, sha256 `265b8e9c…f50a7006`, byte-identical to `testing/runs/fit-hunger-curve-20261017c/fit-compact.json`, the tool's whole output (no larger `fit.json` exists, so no `source_sha256` is kept). **Plan 15 Task 14b, the hunger curve re-fit on the liquid lane slowed only by drink-borne kcal; shipped until Plan 16 Task 4b's re-fit.** `tools/fit_hunger_curve.py` at `8a34a7de` (`head`, committed, unchanged since `a97fec05`), on the kernel of `8a34a7de`, whose liquid lane reads only drink-borne kcal and whose knots were Task 6c's; the chosen point is the knots landed in `390636fe`.

How to read it. Read it as `fit-hunger-curve-20261017b` above. `shipped` and `shippedReading` are the Task 6c knots (the kernel's at `8a34a7de`) scored on the new lane, not the chosen point; `previous` and `previousReading` stay the Task 6 knots (the tool's `PREVIOUS`, unchanged).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything here, as a study or a live reading | — | The mod's own satiety model replayed on the lupa host and mapped through the curve, against vanilla's modelled cadence; no study and no live game is read. |
