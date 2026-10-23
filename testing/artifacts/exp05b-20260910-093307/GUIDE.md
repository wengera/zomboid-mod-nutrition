# `exp05b-20260910-093307` reading guide

**`exp05b-20260910-093307/drink-probe.json`** — produced by
`testing/experiments/s05b_drink_probe.py`, the live drink probe (slice 05, task 5b), at the
commit that added it, together with the harness `drink` command it drives. Slice 05's **final
fix wave** then changed the script and that command in three ways this file predates, all of
them documentation-level. **No measured number in it moves**, and that is checked rather than
assumed: the comparator at HEAD was replayed offline against this file's own `drink` replies
and the dataset behind them, reproducing the stored verdict exactly — **72 fields compared,
69 matched, 3 mismatched**, the same three outer `calories` rows.

- **`meta.drift_rates.lipids` / `.proteins` are corrected** to `0.00113` / `0.00086` per
  game-second, with citations that measure *those* macros, and `drift()` now bands with them
  instead of with carbs' `0.0035`. In this file both keys read `0.0035` and both bands were
  therefore ~3× too wide — which can only excuse a row, never fail one. See *do not cite*.
  Replayed with the corrected bands the two rows still match, by ≈1e-4: the drift this run
  measured **is** the corrected rate.
- **The `OUTER_KEYS` identity map is gone.** The outer bracket reads each `stats.get` store
  under the same name the reply's `delta` uses. No key, no behaviour, nothing in this file.
- **`syncItemFields` gained a twin.** The command stored `TK.call`'s ok flag in that key and
  dropped the member's return value; at HEAD it reports both (`syncItemFields` keeps its
  meaning — the member was present and the call ran — beside `syncItemFieldsReturned`, `nil`
  on 42.20.4) and wraps the call, so a raise after the measurement cannot cost the reply. This
  file carries the flag alone, reading `true` on all three drinks. The same wave made
  `fluid.script` report an absent `getDisplayName` / `hasPropertiesSet` in `missingGetters`;
  this file's two `fluid_script` blocks predate that and both members answered.

The run itself is clean —
`server_errors []`, `client_quit rc=0`, `server_stopped rc=0`, doctor all-`ok` (recorded in
`meta.doctor`), dataset `705a12f` with `dataset_dirty false` and the sha256 of the bytes
actually read. Two of its **summary** keys mislead when quoted on their own and two of its
`meta.drift_rates` labels are simply wrong; all three entries are listed as *do not cite*
below. Every measured number in the file stands.

The file carries two readings of each drink, and only one of them is the measurement:

- **`comparison.<drink>.atomic`, `.container`, `.container_fill`, `.food_timer` and
  `.atomic_window_game_hours`** — the primary reading. Both snapshots are taken inside the one
  Lua call, on either side of the single `DrinkFluid` line, so the window is **zero game-time**
  (`atomic_window_game_hours.live == 0` on all three drinks) and no passive drain sits between
  them. That is **54 of the 72 compared fields (18 per drink), and all 54 matched.**
- **`comparison.<drink>.outer`** — corroboration only: `stats.get` on either side of the bus
  command, a 6–8 real-second window that *does* carry drift. **15 of its 18** banded rows
  matched.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| `summary.all_matched` and `summary.fields_mismatched` | `false` and `3` | True as defined, and **misleading as evidence about the fluid arithmetic**. All three are the same field — the **outer** bracket's `calories` row — on the three drinks, and each misses the band's lower edge by **0.002 / 0.008 / 0.008 kcal**. The band's lower edge is `expected − 0.016 × weight/80 × Δgame-s`, i.e. it assumes the idle burn is *exactly* the model rate; subtracting the drift-free atomic delta from the outer one gives the burn that actually occurred, at ratios **1.00183 / 1.00411 / 1.00561** — inside the residual this repo has already measured twice (**1.0049**, `exp03-20260910-045523`; **+0.4 / +0.4 / +0.7 %**, the three slice-04 scenario runs). So the three rows are the idle-burn model's known excess seen a third time, not a disagreement about the drink. Cite `summary.per_drink.<drink>.matched` alongside the `atomic` / `container` blocks, or the report's § 4 tables. The tolerance was deliberately **not** widened after the fact — see § 5 of slice 05's task-5b report, in the SDD workspace, outside the tree — so a re-run flags the same three rows for the same reason. |
| `comparison.<drink>.outer.calories.expected` | `119.233` / `58.977` / `79.233` | Not a prediction of anything the game does: it is the **midpoint of a band**, `no_drift_expectation + max_drift/2`, chosen so `diff` reads as a signed distance from the middle. The physical prediction is the sibling key `no_drift_expectation` (`120` / `60` / `80`), and the same row's `max_drift` is the other edge. |
| `meta.drift_rates.lipids` and `.proteins` (and the `max_drift` / `tolerance` of the six `comparison.<drink>.outer.lipids` / `.proteins` rows they set) | `"0.0035 per game-second (nutrition-core.md, M)"` | **Wrong rate, wrong citation.** The macro drains are three different constants, not one: `Nutrition.update @48/@66/@84 L76–L78` writes carbs `−0.0035`, lipids **`−0.00113`** and proteins **`−0.00086`** per game-second ([`facts/body-and-weight.md#passive-burn`](../../../docs/facts/body-and-weight.md#passive-burn), C+M `exp01-20260910-003929`; the same constants slice 03 fitted at `testing/experiments/s03_body.py:103`, measured ratios 0.9991 / 0.9972 / 0.9993 in `exp03-20260910-045523`). The citation quoted here ([`facts/body-and-weight.md#passive-burn`](../../../docs/facts/body-and-weight.md#passive-burn)) measures **carbohydrates only**. The labels are used for one thing — widening the outer bracket's band — so the error made those six bands ≈3× too wide, which can excuse a row but never fail one, and the file's own numbers reproduce the correct rates to four figures: subtracting each drink's expected gain from its outer delta and dividing by that window's own `worldAge` span gives lipids 0.00113000 / 0.00112995 / 0.00112984 and proteins 0.00086001 / 0.00085996 / 0.00085988. Cite the rates above and the run's own `outer.lipids` / `outer.proteins` deltas; the script at HEAD carries the corrected labels and bands. |
