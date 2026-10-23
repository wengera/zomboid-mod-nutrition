# `fit-hunger-curve-20261017b` reading guide

**`fit-hunger-curve-20261017b/fit-compact.json`** — 22024 bytes, sha256 `c368fa5d…53946e6e`, byte-identical to `testing/runs/fit-hunger-curve-20261017b/fit-compact.json`, the tool's whole output (no larger `fit.json` exists, so no `source_sha256` is kept). **Plan 15 Task 6c, the hunger curve re-fit on every meal's Peckish return; shipped.** `tools/fit_hunger_curve.py` at `0842b345` (`head`, committed), on the kernel of `0842b345`, whose knots are the chosen point (landed in `92df05d0`).

How to read it. Read it as `fit-hunger-curve-20261016` above, with these additions. `reading.meals` holds each meal's hours from the meal to HUNGER over 0.15 on the three-meal days 1 to 3 (`breakfast`, `lunch`, `dinner`), each the mean of two replays: the guide's water and the same water an hour later (`scenarios.WATER_SHIFT`); `reading.mealsByWater.guide` and `.shifted` are the two; `reading.censored` names a meal whose HUNGER never passed 0.15 before the next meal (none). `vanilla.meals` is `tools/vanilla_model.py`'s return after each can of the same schedule at DayLength 4. `reading.miss` carries one term per meal, the mean log ratio times its weight, and the shares' terms carry their weight (`search.weights`). `previous` and `previousReading` are the Task 6 knots and their scores on the same traces; `shipped` and `shippedReading` equal `chosen` and `reading`. `stability.knots[i].meals` adds each meal's return to the knot probes. `profile` is the Peckish knot (`X[3]`) across its bounds at 0.005, the others at the chosen point: the loss, each meal's return on day 2 (`meals`, in breakfast, lunch, dinner order), the shares and the fast's Peckish return (`t1`). `search` adds the scan that precedes the coordinate refinement (`scanStep`).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything here, as a study or a live reading | — | The mod's own satiety model replayed on the lupa host and mapped through the curve, against vanilla's modelled cadence; no study and no live game is read. |
