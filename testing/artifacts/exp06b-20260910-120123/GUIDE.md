# `exp06b-20260910-120123` reading guide

**`exp06b-20260910-120123/use-probe.json`** — produced by
`testing/experiments/s06b_use_probe.py`, the slice-06 per-use consumption probe, together
with the harness command it drives (`item.use` in `server/PZTestKit_Server.lua`). Script,
command and artifact landed in one commit (`3c16632`).

**Skew (slice 06's final fix wave).** Both the command and the driver have since been edited,
and **no measured number in this file moves**:

- *Harness*, `item.use`: (a) it now **refuses** an already-depleted instance —
  `currentUses == 0` would send `setCurrentUses(0)` into `consumeHunger((0−0)/100f)`, i.e.
  `r = |0/0|` = NaN, and `multiplyFoodValues(1 − NaN)` would write NaN into every macro. All
  three rows here were spawned whole (30 / 40 / 15 uses), so the guard never fires on this run.
  (b) `predicted` no longer carries `thirstChange` (see the *do not cite* row below).
  (c) `candidatesAfterError` is a new key for a **failed** post-call enumeration, which used to
  be indistinguishable from an empty inventory; the enumeration succeeded on all three rows
  here, so the key is absent either way. (d) Comment corrections only: the `replaceOnDeplete` /
  `sendItemStats` skip list and the `used/cur` exactness caveat, both below.
- *Driver*, `s06b_use_probe.py`: (a) `summary.per_item.<key>.ok` is now
  `block.matched is True` instead of `not block.mismatches` — `compare_item` returns early with
  `matched: false` and an *empty* `mismatches` list on three paths (the use phase never ran, no
  `data/food-items.json` record, no `before` snapshot) and every one of them was scoring as a
  pass; all three rows here reached the full comparison, so the verdict is identical.
  (b) The scaling rows' tolerance is now anchored on the two values being **compared** rather
  than on `before`, and a 0 expectation is compared exactly — the bands in this file's
  `scaling.*.tolerance` are therefore **wider than the script at HEAD would write** (e.g.
  `calories` on the Icecream row: 0.16801 here, 0.11201 at HEAD; on the two factor-0 rows,
  0.03001 / 0.01131 here against an exact compare at HEAD). Every row matched with room to
  spare either way — the replay below re-scores all 96 under the narrower rule and none moves.
  (c) `load_json` / `git_say` / `doctor` / `num` moved verbatim into `_common.py`.

The comparator replayed offline at HEAD against this artifact gives **3 of 3 items, 96 of 96
fields, `mismatches []`** — unchanged from the run's own verdict.

The run is clean — `server_errors []`, `client_quit rc=0`, `server_stopped rc=0`, doctor
all-`ok` (recorded in `meta.doctor`), 89.6 s wall, `data/recipes.json` at `c6ef7f2` with
`dataset_dirty false` and the sha256 of the bytes actually read. It makes **no world change**:
no `settimespeed`, no sandbox write, no character write. The only thing it touches is the three
items it spawns into this run's own copy of the fixture.

It is a **single-verdict** file: `summary.all_matched true`, **96 of 96** compared fields
matched across three items, `mismatches []`. What a reader does have to carry away is the
**route**:

- **`ItemUser.UseItem` was not reachable and was not used.**
  `comparison.<item>.route_attempts[0]` records `memberAbsent: true` — `ItemUser` is not a Lua
  global on 42.20.4, because `LuaManager$Exposer.shouldExpose @6–@14 L2833` is a strict
  `HashSet.contains` over the ~1000 classes `exposeAll()` registers and
  `zombie/inventory/ItemUser` is not one of them. Every row therefore ran through
  `item:setCurrentUses(currentUses − used)`, which **is** the line `UseItem @28 L37-38`
  executes and the only path by which crafting reaches hunger at all. What the fallback skips
  is UseItem's bookkeeping *after* the reduction, and for a `Food` that is exactly three
  things: the `replaceOnUse` spawn, `sendItemStats(item)` when uses **remain**
  (`@293 L73-74`), and `RemoveItem` at `@272 L68-70` when they do not. It is **not**
  `replaceOnDeplete` — that arm is behind `instanceof DrainableComboItem` (`@146 L53`) and a
  `Food` never reaches it, so an earlier wording of this row overstated what the fallback
  skips. No nutrition field moves in any of the three, and the skipped `sendItemStats` is a
  *client push* this command does not make on either route (every reading here is server-side,
  on the object the server holds), so the measurement is untouched; but the two fully consumed
  items **stayed in the inventory**
  (`candidates_after` length 1, `after.inContainer true`, `getCurrentUses() 0`) where the
  crafting code would have removed them. `depletion.removed_from_inventory` is compared
  against the expectation **for the route that ran**, which is why it reads
  `expected: false`. Removal-on-deplete is therefore still a *jar reading*, not an `M`.
- **Every scaled field is `before × (1 − used/currentUses)`, measured.**
  `Base.Icecream` at 10 of 30 uses: `hungChange −0.30 → −0.20`, `calories 1680 → 1120`,
  `carbs 180 → 120`, `lipids 84 → 56`, `proteins 26 → 17.333334`, `getCurrentUses() 30 → 20`.
  `Base.MincedMeat` 40/40 and `Base.Cheese` 15/15 both landed on 0 for every macro and for
  `getCurrentUses()`. `delta.worldAgeHours` is `0` on all three — both snapshots are taken
  inside the one Lua call — so none of these numbers carries passive drift.
  **Read the strength of that claim carefully: the FRACTIONAL factor rests on `Base.Icecream`
  alone.** It is the only row whose factor is neither 0 nor 1, and it carries the whole of the
  fractional evidence — seven fields (`hungChange`, four macros, `getCurrentUses()` and
  `getCurrentUsesFloat()`), including the `(int)` truncation that makes `30 → 20` a second,
  integer-valued reading of the same scaling. The other two rows are **boundary rows at factor
  0**: they rule out "one use = one item" and "N is a count of items" — 40 uses of a 40-use tub
  empties it rather than needing 40 tubs — but a model that scaled by *anything* vanishing at
  `used == cur` would satisfy them. Cite all three for the boundary and the Icecream row for
  the fraction.
- **`used/currentUses` is exact only for a whole item.** `getCurrentUses()` is
  `(int)|hungChange × 100|`, so `|hungChange| = cur/100` — and with it
  `1 − used/cur` — holds exactly only while `|hungChange| × 100` is a whole number. On a
  part-spent item the real argument is `1 − ((cur − used)/100)/|hungChange|`, a hair under it.
  Every item here was spawned fresh and `spawn_guard.current_uses_is_whole` checks that per
  row, which is what makes the shorthand legitimate for these three; `factor.float32` (the
  game's own arithmetic, replayed at float32 width) is what the compared expectations use and
  `factor.exact` carries the `1 − used/cur` reading beside it.
- **`getMaxUses()` and `baseHunger` do not move.** 30 / 40 / 15 and −0.30 / −0.40 / −0.15
  before *and* after, including on the two items consumed to nothing. This is what makes
  `currentUses` — not `maxUses` — the denominator of any *second* reduction on a part-eaten
  item; the two coincide only while the item is whole, and
  `spawn_guard.current_uses_is_whole` checks that per row rather than assuming it. Do not read
  the `1 − uses/maxUses` shorthand as general.
- **`comparison.<item>.recorded_uncompared` is recorded on purpose and compared against
  nothing.** `thirstChange` is there because `multiplyFoodValues @42 L2292` scales
  `getThirstChangeUnmodified()` while `TK.ITEM_STATE.thirstChange` reads the **modified**
  getter — comparing the two would be a defect in the script, not a finding. (All three items
  read 0 before and after, so nothing is hidden by it here.) `hungerChange` moved in lockstep
  with `hungChange` on all three rows only because each item was fresh and uncooked, so the
  read-time ladder is the identity.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| `items.<key>.use.predicted.thirstChange` | `0` on all three rows | **Not a prediction of anything the game does.** The harness built it as `before.thirstChange × factor`, and `before.thirstChange` is `TK.ITEM_STATE`'s reading of the **modified** getter, while `multiplyFoodValues @42 L2292` scales `getThirstChangeUnmodified()`. The two are the same number only where no modifier bites — which is why all three rows read 0 here and nothing is visibly wrong. The comparator never used it (`SCALED` deliberately excludes thirst; the before/after pair is in `comparison.<key>.recorded_uncompared`), and the command at HEAD no longer computes it. The other five `predicted` keys are sound and are compared as `harness_prediction` beside each scaling row. |
| `comparison.<key>.scaling.*.tolerance` | e.g. `0.16801` on `icecream_third.calories` | True as computed and **wider than the rule the script now applies**. The band was `ABS_FLOOR + REL × max(expected, live, before)`, so it was sized by the `before` value — the nutrition that is supposed to have *gone*. At HEAD the band is anchored on the two values being compared and a 0 expectation is compared exactly. Every row here matched under both rules (re-scored offline: 96/96), so the numbers stand; do not quote a tolerance from this file as the band the harness uses. |
