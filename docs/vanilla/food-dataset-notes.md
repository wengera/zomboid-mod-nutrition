# Food dataset — the vanilla food/drink scan and its live cross-check

**Verified against: 42.20.4 (`b0bbce05d5`)** · 2026-09-10 · slice 05 (P4a).
Evidence grades: **C** read from bytecode/Lua/shipped scripts (`file:line`, or
`Class.method @addr Lline` for the jar), **M** measured on the live dedicated server (run id +
artifact link), **W** wiki mirror (secondary — none is used here).
`C (arith.)` = arithmetic on C constants, shown inline — the dataset's eleven derived columns
(`nutrition_basis`, `fluid_share`, `fluid_fill_litres`, `fluid_pick_random`, `drinkable` and the
six `*_per_container`) are that grade, not the plain C of a value copied off a script line.
This document is about the **dataset**: what `data/food-items.json` / `.csv` contain, how the
scanner decides, and how far the numbers were checked against the running game. The **column
authority is [`data/README.md`](../../data/README.md)** § food-items — every column, type and
source key is listed there and is not repeated here. The 114 script keys and what each one does
in the engine are [food-item-model.md](food-item-model.md) § Key reference — **linked, never
re-derived**. Intake arithmetic is [eating-pipeline.md](eating-pipeline.md); the body side is
[body-stats.md](body-stats.md).

## Summary

1. **1 005 item records and 61 fluid records**, built by `tools/food_scan.py` from 18 shipped
   files under `media/scripts/generated/` into four buckets — 722 `food`, 150 `drainable`, 133
   `fluid_container`, 61 `fluid`. Three of the four counts were reproduced by the game's own
   `ScriptManager` on two separate boots; the fourth has no live route at all.
2. **A B42 drink is not a `Food` item.** It is a `base:normal` item carrying a
   `component FluidContainer` joined to a `fluid` definition in `generated/fluids*.txt`, and
   `media/scripts/fluids/` does not exist. Measured: a fluid container's *instance* answers the
   four `InventoryItem` ageing/cooking getters and **none** of the six `Food` nutrition getters —
   a drink's nutrition is only ever reachable through its fluid.
3. **A fluid's `Properties` are per litre, not per item.** The container multiplies them by the
   litres it holds, so a 0.3 L Cola can is 120 kcal, not Cola's 400. The dataset says which unit
   every row is in (`nutrition_basis`) and carries the multiplied-out `*_per_container` columns
   beside the raw ones. Measured live: drinking one full can wrote **+120.000031 kcal** and
   **+31.200001 g** carbs.
4. **Absence is load-bearing and is never a zero.** An absent key is `""` in the CSV and `null`
   in the JSON; a key that really writes `0` still prints `0`. Confirmed live in both directions
   — `Base.RatKing` (`DaysFresh = DaysTotallyRotten = 0`) reads back `offAge 0 / offAgeMax 0`
   while `Base.CannedCorn` (both keys absent) reads back the `1000000000` sentinel.
5. **Everything in the dataset is grade C** — every value is a line in a shipped file and every
   record names its `source_file:source_line`; the eleven derived columns are `C (arith.)`, the
   arithmetic shown beside each. The measured layer is two live runs: a census plus
   ten field-for-field spot checks (182 fields, 170 matched, 12 not applicable, **0 mismatched**)
   and a three-drink probe that closed slice 01's open question 11.

---

## Model

### The five questions, answered

| # | Question (plan 05) | Answer | Ev |
|---|---|---|---|
| Q1 | Which of the 114 script keys each `base:food` block declares, with what value and typed representation, and which are **absent** | Every record carries the typed columns plus `props_raw`, the block's own `Key = Value` lines verbatim; an absent key is `null` / `""`, never `0`. The item-level key union over `food.txt` + `drainable.txt` is **exactly the 114 documented keys, 0 unknown** — an independent confirmation of the slice-02 table | C — [food-item-model.md](food-item-model.md) § Key reference; `tools/food_scan.py` `KEY_TYPES` |
| Q2 | Identity per item, and do the `ReplaceOn*` targets resolve to a scanned id | `id` / `module` / `name` / `display_name` / `display_category` / `food_type` / `item_type` / `tags` on every row; **6** ids have no EN name; **37** links do not resolve (23 `ReplaceOnUse` + 14 `ReplaceOnDeplete`, **16** distinct targets), 15 of those targets being real items outside the food set and one being defined nowhere at all — see § Discrepancies row 2 | C — `meta.unresolved_links` / `meta.missing_display_names` |
| Q3 | Which items carry drinkable nutrition through a fluid, what each of the 61 fluids declares, and is a fluid's `Calories` **per unit** or absolute | **Per unit, and the unit is a litre.** § Per litre, not per item below | C + M `exp05b-20260910-093307` ([`drink-probe.json`](../../testing/artifacts/exp05b-20260910-093307/drink-probe.json)) |
| Q4 | Does the scanner's `base:food` count equal `ScriptManager.getAllItems()`, and the fluid count `getAllFluidDefinitionScripts()` | **Yes** — 722 food, 150 drainable and 61 fluid definitions, live and in the dataset, on two independent boots. The 133 `fluid_container` count has **no** live route: the script `Item` exposes no component accessor | M `exp05-20260910-084109` ([`food-scan.json`](../../testing/artifacts/exp05-20260910-084109/food-scan.json)); the container count C |
| Q5 | Do ten spot-checked items match the live game field-for-field on every field the game exposes | **Yes** — 182 fields compared, 170 matched, 12 not applicable, **0 mismatched**, no substitution needed. The 12 are the six `Food`-only getters on the two drinks | M `exp05-20260910-084109` ([`food-scan.json`](../../testing/artifacts/exp05-20260910-084109/food-scan.json)) |

### The four buckets and the selection rule

`food_scan.select` applies four rules, **first match wins**. The three item rules are disjoint on
42.20.4 (measured: no id is claimed twice), so the CSV is 1 005 rows and the ordering never fires;
it is still enforced, and tested with a synthetic fixture, because a mod can break it.

| kind | Rule | Count | Ev |
|---|---|---:|---|
| `food` | every `item` in `items/food.txt` with `ItemType = base:food` | 722 | C `items/food.txt` (15 525 lines); **M** live `items.count.food` and `byType["base:food"]` both 722 — `exp05-20260910-084109` ([`food-scan.json`](../../testing/artifacts/exp05-20260910-084109/food-scan.json)) |
| `drainable` | every `item` in `items/drainable.txt` with `ItemType = base:drainable` | 150 | C `items/drainable.txt` (2 420 lines); **M** live `byType["base:drainable"]` 150 — same run |
| `fluid_container` | every `item` in any of the 15 `items/*.txt` owning a `component FluidContainer` | 133 | C only — `normal.txt` 125, `clothing.txt` 4, `container.txt` 2, `weapon.txt` 2, and **zero** in `food.txt` / `drainable.txt`. `Item` exposes no component accessor, so there is no live census route |
| `fluid` | every `fluid` block in `fluids.txt` (20), `fluids_Alcoholic.txt` (18), `fluids_Beverages.txt` (23) | 61 | C; **M** live `items.count.fluidDefs` 61, and the live id set is **exactly equal** to the 61 script blocks in both directions — `exp05-20260910-084109` and Task 4's `t4probe-20260910-081129` |

`ItemType.toString()` really does return the `ResourceLocation` form `base:food` on this build —
recorded raw in `byType`, so a registry rename would be visible rather than silently zeroing a
bucket. Fluids are **joined into** container rows and also kept whole under the JSON's `fluids`
key; they are never rows of their own. Ev C + M, same run.

### Empty is not zero

| Case | CSV | JSON | Live read-back | Ev |
|---|---|---|---|---|
| The script writes no such key | `""` | `null` | the engine's own default, which is **not** always 0: `DaysFresh` / `DaysTotallyRotten` absent read back `1000000000` on both the script object and the instance (`Base.CannedCorn`) | C; **M** `exp05-20260910-084109` ([`food-scan.json`](../../testing/artifacts/exp05-20260910-084109/food-scan.json)) |
| The script writes a real `0` | `0` / `0.0` | `0` / `0.0` | `0` — `Base.RatKing` writes `DaysFresh = DaysTotallyRotten = 0` and its instance carries `offAge 0 / offAgeMax 0`, so it is born rotten | C; **M** same run |
| Half a block is written | the written half only | the written half only | the missing half takes its default independently — `Base.BreadSlices` has `MinutesToCook 4` and no `MinutesToBurn`, and reads back `4 / 120` | **M** same run |
| A container lists no fluid | `""` | `[]` for `fluid_ids`, `null` for the fill columns | 61 of the 133 containers spawn empty | C |

`null` (not a container) and `[]` (a container that lists no fluid) are distinguished in the JSON
and are both `""` in the CSV. Ev C.

### `nutrition_source`, `nutrition_basis`, and the fluid join

| Column value | What it means | Rows | Ev |
|---|---|---:|---|
| `nutrition_source = food_keys`, `nutrition_basis = per_item` | the row fills the nutrition columns from its own script keys | 653 | C |
| `nutrition_source = fluid:<id>`, `nutrition_basis = per_litre` | the row is a container and the columns are the **first** listed fluid's `Properties`, which are per litre | 72 | C; **M** the join checked live against `fluid.script Cola` / `fluid.script JuiceGrape` on all six nutrition fields — `exp05-20260910-084109` ([`food-scan.json`](../../testing/artifacts/exp05-20260910-084109/food-scan.json)) |
| both empty | the row **names no nutrition source** — no nutrition key on either side: 78 food, 141 drainable, 61 empty containers | 280 | C |

Carrying no nutrition *value* is a wider set than naming no *source*: **290** rows carry none,
the extra 10 being `per_litre` rows joined to a fluid whose `Properties` block is absent or holds
only `alcohol`. Those 10 keep `fluid:<id>` and `per_litre`, because
`nutrition_source` is `fluid:<id>` whenever a first fluid exists, **even when that fluid has no
`Properties` block** (10 of the 61): the nutrition genuinely comes from the fluid, and the fluid
genuinely has none. In 42.20.4 no fluid-container item writes a nutrition key of its own, so the
join never overwrites anything. Ev C.

**The container split.** The 133 containers are 63 single-fluid + 9 pick-random + 61 empty, and
`fluid_fill_litres` equals `fluid_capacity` on all 72 filled rows in 42.20.4 — every share in the
files is `1.0` bar `Base.BucketWaterDebug`'s `Water:10.0`, which the capacity clamp takes back to
its 10 L capacity. That
figure is the **full** container's: 14 of the 133 also write `InitialPercentMin` /
`InitialPercentMax` and spawn part-filled (§ Discrepancies row 7). Ev C —
`meta.counts.fluid_containers_filled` / `..._pick_random` / `..._empty` /
`..._initial_percent`.

### Per litre, not per item

*See also [`data/README.md`](../../data/README.md) § Per litre, not per item, which carries the
same chain against the column numbers, the worked `Base.Pop2` row and the part-fill caveat.*

A `fluid`'s `Properties` are the effect of **one litre**. The chain, and where each step lives:

| Step | Mechanism | Ev |
|---|---|---|
| The loader stores the script value as written | `FluidDefinitionScript.LoadProperties @0–@453 L367–L410` — fifteen `equalsIgnoreCase` keys, each `Float.parseFloat`, no arithmetic | C |
| Four getters divide by 100, the nutrition ones do not | `FluidDefinitionScript.getHungerChange @0–@10 L186` and its `getThirstChange` / `getStressChange` / `getFatigueChange` siblings divide; `.getCalories @0–@7 L202` and the three macro getters do not | C |
| The container multiplies by its litres | `FluidContainer.recalculateCaches @222–@250 L631–L632` calls `addFromMultiplied(fluid.getProperties(), litres)`, so `getProperties()` is already litres-weighted | C; **M** a full `Base.Pop2` reported `calories 120.000008`, not 400 — `comparison.pop2_whole.container` in [`drink-probe.json`](../../testing/artifacts/exp05b-20260910-093307/drink-probe.json) |
| The litres are a **full** container's | `FluidContainerScript.getInitialAmount @0–@11 L387-L388` defaults to `Capacity` when the script writes no initial amount, `FluidContainer.addInitialFluid @11–@17 L132` multiplies by the `:share` suffix parsed at `FluidContainerScript.readFluid @16–@29 L348-L349`, and `FluidContainer.addFluid @30–@45 L1003-L1004` clamps to the capacity — which is the `fluid_fill_litres` column. 14 containers **do** write an initial amount and spawn part-filled: § Discrepancies row 7 | C |
| Drinking spends that aggregate, times the fraction drunk | `IsoGameCharacter.DrinkFluid @23–@100 L5878–L5881` writes `setX(getX() + fc.getProperties().getX() * f)` | C; **M** below |

**Measured, three drinks, two fluids, two capacities, two fractions** — server-side
`DrinkFluid(InventoryItem, f, false)`, both snapshots taken inside the one Lua call so the window
is a single tick (`delta.worldAgeHours` read `0` on all three):

| Drink | f | Δcalories | Δcarbs | ΔHUNGER | ΔTHIRST | Fill left | Ev |
|---|---:|---:|---:|---:|---:|---|---|
| `Base.Pop2` (0.3 L Cola) | 1.0 | **+120.000031** | **+31.200001** | −0.036 | −0.090 | 0.3 → 0 L | **M** `exp05b-20260910-093307`, `comparison.pop2_whole.atomic` ([`drink-probe.json`](../../testing/artifacts/exp05b-20260910-093307/drink-probe.json)) |
| `Base.Pop2` | 0.5 | **+60.0** | **+15.6** | −0.018 | −0.045 | 0.3 → 0.15 L | **M** same run, `comparison.pop2_half.atomic` |
| `Base.JuiceBox` (0.2 L JuiceGrape) | 1.0 | **+80.0** | **+23.999996** | −0.020 | −0.060 | 0.2 → 0 L | **M** same run, `comparison.juicebox_whole.atomic` |

So `per-litre value × fluid_fill_litres × f` is **C + M**, and `f` is a share of the *current
contents*, not of the capacity: a full can at `f = 0.5` is left holding exactly half its fill.
`healthFromFoodTimer` gained `(int)(|hungerChange| × 13000)` = 468 / 234 / 260, the float32 sum
truncated. Ev **M**, same run.

**The `/100` is deliberately not applied in the dataset**, on either side: a fluid's
`HungerChange` and an item's are both stored raw, so a Cola can's
`hunger_change_per_container = −3.6` is directly comparable to an apple's `hunger_change = −16`,
and both become stat-bar units by dividing by 100. The unit traps that follow from that asymmetry
are in § Open questions. Ev C.

### The CSV/JSON split

- **CSV — curated.** 1 006 lines (header + 1 005), **61 columns**: 59 declared plus the trailing
  `source_file`, `source_line`. One row per item; fluids are joined, never rows. Zero quoted
  cells, LF line endings, and **no build stamp** — the header is line 1 so `csv.reader` and a
  spreadsheet import both work, and the pair's build is in the JSON's `meta`
  ([`docs/decisions.md`](../decisions.md), 2026-09-10, 05). The JSON is **2.35 MB** against the
  CSV's 237 KB: 41 126 of its lines are a `"column": null` (≈1.1 MB — the shape invariant, every
  column on every record) and `props_raw` is another ≈474 KB.
- **JSON — complete.** `{"meta", "items" (1005), "fluids" (61)}`. Every item record carries every
  declared column (absent as `null`) **plus** `props_raw`, the block's own lines verbatim,
  untyped and unsplit, with a repeated key becoming a list. Nested blocks are **not** flattened
  into `props_raw` — a container's `Capacity` reaches the record only as `fluid_capacity`. A
  fluid record additionally keeps `properties_raw`, `categories`, `poison` and its own source
  anchor.
- `meta` records the build, the jar hash, the 18 source paths, the ten counts (the tenth,
  `fluid_containers_initial_percent`, is § Discrepancies row 7's 14), and every join
  miss: `unresolved_links` (37), `missing_display_names` (6), `unresolved_fluid_refs` (0),
  `unknown_keys` (60). Nothing is swallowed.

Column-by-column definitions, the `meta` key table and the pick-random caveat:
[`data/README.md`](../../data/README.md) § food-items. Ev C.

---

## Code map

| Path | Where | What it does | Ev |
|---|---|---|---|
| `tools/food_scan.py` — parser half | `parse_script`, `values`, `canonical_key`, `coerce`, `KEY_TYPES`, `walk` / `named` / `iter_blocks` | the shared nesting-aware block reader: a `Block` is `kind` / `name` / `module` / `file` / `line` / `props` (last write wins, as the loader does) / `entries` (every `Key = Value` in file order, so a repeated key survives) / `lines` / `blocks`. `entries` earns its keep on **3 512** repeated prop lines `props` cannot see — 145 `fluid =` lines over 68 `Fluids` blocks and 34 `SoundMap` lines in `drainable.txt` are the two shapes in the scanned files — and `values(block, key)` is the reader for them. A header is decided by **lookahead** (a non-`Key = Value` line whose next logical line is `{`, `kind` the first token and `name` the rest), which is what parses the **156** shipped blocks with a multi-word or numeric name (`evolvedrecipe Stir fry`, the vehicle templates' `1` / `2`); all 34 683 blocks then parse with 0 anonymous opens. Slice 06 imports it rather than writing a second walker | C |
| `tools/food_scan.py` — build half | `select`, `build_item`, `build_fluid`, `build`, `write_csv`, `write_json`, `main` | the selection rule, the three joins and both output files | C |
| `media/scripts/generated/items/food.txt` | 15 525 lines | 722 `ItemType = base:food` blocks — the only file in the install holding one | C |
| `media/scripts/generated/items/drainable.txt` | 2 420 lines | 150 `base:drainable` blocks; only `Vinegar2` and `Vinegar_Jug` carry `Calories`, both `0.0` | C |
| `media/scripts/generated/items/*.txt` | 15 files | the 133 `component FluidContainer` blocks (`normal.txt` 125, `clothing.txt` 4, `container.txt` 2, `weapon.txt` 2) | C |
| `media/scripts/generated/fluids{,_Alcoholic,_Beverages}.txt` | 465 / 646 / 740 lines | the 61 `fluid` definitions; 51 carry a `Properties` block, 44 a `Calories` line | C |
| `media/lua/shared/Translate/EN/{ItemName,Fluids}.json` | 4 889 / 197 entries | display names, keyed `Module.Name` and `Fluid_Name_<id>` | C |
| `ScriptManager.getAllItems()` / `.getAllFluidDefinitionScripts()` | jar | the game's own loaded-definition lists — the live census both counts come off | C; **M** `exp05-20260910-084109` ([`food-scan.json`](../../testing/artifacts/exp05-20260910-084109/food-scan.json)) |
| `ScriptManager.getFluidDefinitionScript(name)` | jar | the by-name route; it answers to both `Cola` and `Base.Cola`, which is the join key slice 06 wants | C |
| `Item.getItemType().toString()` | jar | the `base:food` / `base:drainable` ResourceLocation strings the census buckets on | C; **M** same run |
| `FluidDefinitionScript.Load` / `.LoadProperties` / the fifteen property getters | jar `L367–L410`, `L182`–`L234` | the fluid loader and its four `/100` getters; `Load` is also why `getFluidTypeString()` is empty for an enum-backed fluid (§ Discrepancies row 3) | C |
| `FluidContainer.recalculateCaches` / `.removeFluid` / `.getProperties` | jar `L631–L632` / `L1103–L1138` / `L543-L544` | the two `addFromMultiplied` sites — the whole of the per-litre convention lives here, never in the loader | C |
| `IsoGameCharacter.DrinkFluid(FluidContainer,F,Z)` | jar `L5873–L5940` | the drink pipeline: `Nutrition` from the aggregate × `f`, `Stats` from the already-weighted `FluidConsume`, `healthFromFoodTimer`, and the server-only `SyncPlayerStats` | C; **M** `exp05b-20260910-093307` ([`drink-probe.json`](../../testing/artifacts/exp05b-20260910-093307/drink-probe.json)) |
| `Item.DoParam` / `Item.InstanceItem` | jar | the loader that reads these keys in-game and the copy onto the instance — described in [food-item-model.md](food-item-model.md), not re-derived here | C |
| harness | server `items.count`, `fluid.script <id>`, `item.get <user> <type>`, `drink <user> <type> [f]`; client `item.script <type>` | the live routes, documented in [`../testing/README.md`](../testing/README.md) § Command bus | **M** both runs |
| experiments | `testing/experiments/s05_food_scan.py`, `testing/experiments/s05b_drink_probe.py` | the two measured runs | **M** both runs |

---

## MP behaviour

**Script data is not networked at all; item *instances* are server-owned.** Those are two
different statements and the dataset sits entirely on the first side of the line.

| Fact | Mechanism | Ev |
|---|---|---|
| Both sides load the same script definitions from the same files, and no packet ever carries them | `ScriptManager` reads `media/scripts/` on each process at load. **The no-packet half is an inference, not a grep of the whole protocol:** the item packet slice 02 read field by field, `ItemStatsPacket`, carries *instance* state only — condition, cooked/burnt, `cookingTime`, heat, and the rest of its 39 applied fields — with no script key among them, and no other packet in that analysis carries one either. This is why `items.count` and `fluid.script` are **server-only commands and still the whole answer**: a client census counts the same objects | C — the packet field list in [food-item-model.md](food-item-model.md) § MP behaviour (slice 02); the harness consequence is in [`../testing/README.md`](../testing/README.md) § Command bus |
| A mod that changes a script key changes it on whichever side loaded the mod, with no runtime reconciliation | same mechanism: definitions are load-time state | C |
| The *instance* is server-owned for its entire lifecycle | a client never runs `Food.updateAge` or `updateRotting`; `age` / `offAge` / `offAgeMax` / `freezingTime` are not in `ItemStatsPacket` — [food-item-model.md](food-item-model.md) § MP behaviour | C; **M** (slice 02) `exp02-20260910-030433` ([`lifecycle.json`](../../testing/artifacts/exp02-20260910-030433/lifecycle.json)) |
| **A zero-valued instance field on a client can be carrying another item's value** | `ItemStatsPacket.write` skips twenty conditionally-written fields when they are zero, `parse` mirrors the guard, `applyItemStats` applies unconditionally, and the receiver reuses one cached packet object per type with no reset — [food-item-model.md](food-item-model.md) § A zero-valued packet field can arrive carrying another item's value | C; **M** for `cookingTime` (slice 02, same artifact) |
| Drinking completes on the server too, and pushes **stats but not nutrition** | an MP client never calls `DrinkFluid` (`ISDrinkFluidAction.lua:28` `if not isClient()`, `:43` `if isServer()`, and `NetTimedAction.perform @0–@27 L140` runs the completion server-side); `DrinkFluid @590–@672 L5937-L5938` sends only `SyncPlayerStats`, with no `EatFoodPacket` on this path, so a drink's calories reach a client only on the 1 Hz `PlayerStatsPacket` | C |
| The drink probe read the **server** only | every store in `exp05b-20260910-093307` was read through the server bus with the client attached purely so the player exists; `server_errors []` | **M** [`drink-probe.json`](../../testing/artifacts/exp05b-20260910-093307/drink-probe.json) |

**What this means for a mod.** Read the **dataset** (or a server-side instance) for what an item
*is*; never read a client-side instance and trust a zero. The dataset is exactly the load-time
definition both sides start from, so it cannot be stale in the way a mirrored instance can — and
a value it reports as absent is a value the client's copy is free to be wrong about. Anything
that *changes* what eating or drinking delivers has to run on the server, the same rule slices 01
and 03 reached for `Nutrition`, hunger and thirst. Ev C.

---

## Discrepancies

There is no wiki page for this dataset, so these are not wiki rows: they are places where two
sources of truth disagree, where vanilla's own data is defective, or where an earlier statement
in this library has been superseded.

| # | Claim / expectation | What is actually the case | Ev |
|---|---|---|---|
| 1 | Plan Q3 asked whether a fluid's `Calories` is per unit or absolute; the first dataset build copied the fluid's raw `Properties` straight into the same columns that are per **item** on a `food` row | **Per litre.** `Base.Pop2` read `400` kcal where the can delivers `120` — the columns silently mixed two units. Closed by adding `nutrition_basis`, the four fill columns and the six `*_per_container` columns; the raw per-litre values stay unchanged beside them | C; **M** `exp05b-20260910-093307` ([`drink-probe.json`](../../testing/artifacts/exp05b-20260910-093307/drink-probe.json)) |
| 2 | `items/food.txt:6531` `item HotDrinkRed` writes `ReplaceOnUse = Base.MugRed` (`:6541`) | **No file under `media/scripts` defines `item MugRed`** — yet `lua/shared/Translate/EN/ItemName.json:3069` carries `"Base.MugRed": "Mug"`. 42.20.4 translates an item it never defines: the definition went away and both its EN name and this link outlived it. A vanilla data defect, pinned by a test | C |
| 3 | `getFluidTypeString()` looks like the fluid's key | It names only **34 of the 61** definitions. `FluidDefinitionScript.Load` sets the enum `fluidType` when the name matches a built-in `FluidType` constant and leaves the string null, else `FluidType.Modded` plus the string — the two routes are mutually exclusive (the game's own Lua tests exactly that: `lua/client/DebugUIs/DebugMenu/Fluids/ISFluidCategoriesViewPanel.lua:229`). Pairing it with `getFluidType()` makes the harness exhaustive, and the live id set then equals the 61 script blocks | C; **M** `t4probe-20260910-081129` and `exp05-20260910-084109` ([`food-scan.json`](../../testing/artifacts/exp05-20260910-084109/food-scan.json)) |
| 4 | A `fluid_container` row's nutrition is that item's nutrition | For **five** containers it is one draw from a pool: `Base.Flask`, `Base.PopBottle`, `Base.PopBottleRare`, `Base.SodaCan`, `Base.WaterBottle` list several *different* fluids and the row carries only the first's — `Base.Flask` reports Gin's 2 630 kcal though the same flask can hold Rum, Scotch, Vodka or Whiskey. `fluid_ids` keeps the whole set and `meta.counts.multi_fluid_containers` counts them; nine containers in all set `PickRandomFluid` | C |
| 5 | Int-typed keys hold integers | The fluid files write float literals on them — 141 values such as `UnhappyChange = -10.0`, `StressChange = 0.0`, `fluReduction`, `painReduction`. The fluid loader parses floats; the scanner's `coerce` returns `int` for an integral literal, so one `KEY_TYPES` entry stays one Python type | C |
| 6 | Ten spot checks, one per axis the dataset must get right | **0 mismatches.** 182 fields compared, 170 matched, 12 not applicable — and the 12 are a finding, not a gap: an instance of a `base:normal` fluid container answers only the four `InventoryItem` ageing/cooking fields (`1000000000 / 1000000000 / 60 / 120`) and none of the six `Food` nutrition getters. No substitution was needed; the sealed, uneatable `Base.CannedCorn` spawned fine | **M** `exp05-20260910-084109` ([`food-scan.json`](../../testing/artifacts/exp05-20260910-084109/food-scan.json)) |
| 7 | `fluid_fill_litres` is what a container spawns holding | It is `capacity × share`, i.e. the **full**-container figure, and the per-container columns are "the nutrition of a full container". **14** `component FluidContainer` blocks additionally write `InitialPercentMin` / `InitialPercentMax` and the scanner does not model them — `Base.Flask` `0.0`–`1.0` (`items/normal.txt:14314`), `WineOpen` / `Wine2Open` `0.05`–`0.85` (`:6630`, `:6658`), `WaterDish` `0.05`–`0.95` (`:9510`), `Cologne` / `Perfume` `0.1`–`1.0` (`:2634`, `:2765`), the canteens, hydration packs, leather water bag, sports bottle and the two sprayers. Twelve of the fourteen list a fluid, and all fourteen are `meta.counts.fluid_containers_initial_percent`. **The mechanism, read since:** both keys land in `initialAmountMin` / `initialAmountMax` (`FluidContainerScript.load @207–@261 L202–L207`), and `getInitialAmount @12–@40 L390–L393` returns `min` when they are equal and `Rand.Next(min, max)` — a uniform draw, rolled once per container at `readFromScript @93–@106 L108` — otherwise. **The value is litres, not a percentage**, despite the key name: nothing multiplies it by `Capacity`, which is why `Base.WaterDish`'s `0.05`–`0.95` draw is clamped back to its 0.3 L capacity and `Base.CanteenCowboy` never spawns above 1 L of its 1.8. Same rows, in column terms, in [`data/README.md`](../../data/README.md) § Per litre, not per item | C |
| 8 | `summary.all_matched` in the drink probe reads `false` | **Do not cite it as evidence about the fluid arithmetic.** All 54 fields of the primary, drift-free reading matched; the three flagged rows are the *outer corroboration bracket*'s calorie row on each drink, short of its band by 0.002–0.008 kcal because the band assumes the idle burn is exactly `0.016 × weight/80` while this repo's own measurements put it above that — ratio 1.0049 in slice 03's `exp03-20260910-045523` and +0.4 / +0.4 / +0.7 % across slice 04's three scenario runs, against 1.0018 / 1.0041 / 1.0056 here. Cite the `atomic` and `container` blocks | **M** `exp05b-20260910-093307` ([`drink-probe.json`](../../testing/artifacts/exp05b-20260910-093307/drink-probe.json)); the *do not cite* rows are in [`testing/artifacts/README.md`](../../testing/artifacts/README.md) |
| 9 | [`data/README.md`](../../data/README.md) § Per litre, not per item said the fluid path had never been measured live (slice 01 open question 11) and proposed the probe | That sentence predated the drink probe, which then ran. **Corrected at the close of slice 05**: the section now cites `exp05b-20260910-093307` with the three drinks' numbers, and carries the row-7 part-fill caveat as well. Anything still quoting "never measured live" from this pair is a stale copy | **M** `exp05b-20260910-093307` ([`drink-probe.json`](../../testing/artifacts/exp05b-20260910-093307/drink-probe.json)) |

---

## Open questions

1. **37 unresolved `ReplaceOn*` links, 16 distinct targets.** 15 are ordinary items outside the
   food/drink set (pans in `weapon.txt`, `Base.EmptySandbag`, empty vessels in `normal.txt`) —
   the expected signal that a link leaves the dataset — and the sixteenth is the `Base.MugRed`
   defect above. Whether slice 06 wants those targets resolved against a wider item scan is open.
   Ev C.
2. **Four fluid-only property shapes have no row in the 114-key table**: `alcohol` (a fluid's
   `Properties`) and the `Poison` block's `maxEffect` / `minAmount` / `diluteRatio`. They are
   exactly what `coerce` cannot type and what `meta.unknown_keys` flags. `fluReduction` and
   `painReduction` are **not** among them — both are in the table and merely have no column.
   Worth a row in [food-item-model.md](food-item-model.md) or a slice-06 pass. Ev C.
3. **A pick-random row's numbers are one draw, not an expectation over the pool.** Anything that
   averages or worst-cases a spawn has to fan out through `fluid_ids` into the `fluids` records.
   Ev C.
4. **Unit traps a consumer of this dataset can walk into**, all latent in vanilla and all real for
   a mod. Ev C. (a) `endurance_change` is `/100` for an **item** (`Item.InstanceItem`) but not for
   a fluid (`FluidDefinitionScript.getEnduranceChange @0–@7 L230`); no shipped fluid writes a
   non-zero one, so a modded fluid would be off by 100×. (b) `unhappy_change` on a fluid row is
   applied **twice** when drunk — `DrinkFluid @222–@237 L5893` adds it to BOREDOM and
   `@238–@253 L5894` again to UNHAPPINESS — so a mood delta is `2 × unhappy_change × litres`;
   measured as `−3` on a full Cola can and `−10` on a JuiceBox. (c) `foodSicknessChange` has the
   **opposite sign convention** to `Eat`: `DrinkFluid @452–@484 L5926` requires `> 0`, `Eat @494
   L5791` requires `< 0`. All 61 fluids write `0`. (d) `f` is **unclamped** in `DrinkFluid` — the
   nutrition block multiplies before any clamp, so an `f` outside `[0, 1]` would deliver nutrition
   the container never gave up. (e) `ISDrinkFromBottle` (`shared/TimedActions/ISDrinkFromBottle.lua:70`)
   does not call `DrinkFluid` at all: it hardcodes `THIRST −0.1` per use and delivers **zero**
   nutrition. Its only caller chain starts at `doDrinkForThirstMenu`, which has no caller anywhere
   in `media/lua` — dead code in 42.20.4 that a mod reviving it would use to bypass fluid
   nutrition entirely.
5. **Four drink corners are still unmeasured** (q3 notes' Open #2/#4/#6/#7): the
   `DrinkFluid(FluidContainer, …)` overload, cancel semantics, the 100 ms anim-event cadence under
   `settimespeed`, and when the new fill and the new calories arrive on the *client* — the probe
   read the server only. Ev C.
6. **Fluid containers have no live census route.** The 133 count is scanner-only because the
   script `Item` exposes no component accessor to Kahlua; only fluid *definitions* can be read
   back. Ev C.
7. **`meta.unknown_keys` is 60, and that is a scope statement, not a defect.** Over
   `food.txt` + `drainable.txt` the miss count is **0** — the 114-key union holds exactly. Fifty
   of the sixty are item keys outside that union riding along on fluid-container items in
   `normal.txt` / `weapon.txt` / `clothing.txt` / `container.txt` (`SwingAnim`, `BodyLocation`,
   `WeightReduction`, `FillFromLakeSound`, …); the other ten are the joins' and the fluid files'
   own — `Capacity`, `fluid` and `PickRandomFluid` (component keys the dataset types itself into
   declared columns, so they never reach a `props_raw` and are listed because the *key* is
   outside the item table), `DisplayName`, `ColorReference`, `Categories`, and the four in open
   question 2. Ev C.
8. **How the game picks the spawn fill inside `InitialPercentMin` / `InitialPercentMax` is read
   but not measured.** The jar says a uniform `Rand.Next(min, max)` in litres, rolled once per
   container (§ Discrepancies row 7), and no run has watched one spawn: both drinks measured here
   are full containers, which is what `comparison.<drink>.container_fill.amount_before` checks per
   run. The recipe is cheap — RCON `additem "admin" "Base.WineOpen" 5`, then one
   `drink admin Base.WineOpen 0`, whose `candidates[]` rows carry each instance's `amount`: five
   draws from `0.05`–`0.85` against a `Capacity` of `1.0` separate a uniform draw from a fixed
   fraction and settle the litres-versus-percent reading from the outside. Whether the dataset
   should then carry the two bounds as columns, rather than only the
   `meta.counts.fluid_containers_initial_percent` count it has now, is open with it. Ev C.

**Closed by this slice.** Slice 01's open question 11 — *"the fluid path is C-only; no live
measurement of a fluid container was taken"* — and the q3 notes' Open #1 are both **closed** by
`exp05b-20260910-093307`: the per-litre arithmetic is now C + M on two fluids, two capacities and
two fractions. Slice 02's deferred minor *"empty RCON replies accepted without read-back"* is also
closed: both slice-05 drivers key spawn success on a server-side read-back rather than on the RCON
echo, and both runs hit the case it exists for — an `additem` that returned `""` for an item that
had in fact spawned (once in the census run, twice in the drink probe). Ev **M**, both runs.

---

## Sources

**Scripts (`D:\SteamLibrary\steamapps\common\ProjectZomboid\media\scripts\generated\`)**
`items/food.txt` (15 525 lines, 722 `base:food`; `item HotDrinkRed` at `:6531`),
`items/drainable.txt` (2 420 lines, 150 `base:drainable`) and the other 13 `items/*.txt`, four of
which hold the 133 `component FluidContainer` blocks (`items/normal.txt:7038` `item Pop2`,
`:14295` `item Flask`); then `fluids.txt` / `fluids_Alcoholic.txt` / `fluids_Beverages.txt`
(465 / 646 / 740 lines, 20 / 18 / 23 `fluid` blocks; `fluid Cola` at
`fluids_Beverages.txt:3`). There is **no**
`media/scripts/fluids/` directory, and no comment syntax is used anywhere under `generated/`
(28 files elsewhere under `media/scripts/xui/` do ship `/* */`, which is why the parser strips it).
The 18 files the scanner actually reads are listed in `meta.sources`.

**Translations** `media/lua/shared/Translate/EN/ItemName.json` (4 889 entries keyed `Module.Name`;
`"Base.MugRed"` at `:3069`) and `Fluids.json` (197 entries keyed `Fluid_Name_<id>`).

**Jar (pzdis, 42.20.4 `b0bbce05d5`)** `zombie/scripting/objects/ScriptManager` (`getAllItems`,
`getAllFluidDefinitionScripts`, `getFluidDefinitionScript`); `zombie/scripting/objects/Item`
(`DoParam`, `InstanceItem`, `getItemType`); `zombie/scripting/objects/FluidDefinitionScript`
(`Load`, `LoadProperties`, `hasPropertiesSet`, the fifteen property getters);
`zombie/scripting/objects/FluidContainerScript` (`readFluid`, `getInitialAmount`);
`zombie/entity/components/fluids/{Fluid,FluidContainer,FluidProperties,SealedFluidProperties,FluidConsume}`
(`setScript`, `recalculateCaches`, `getProperties`, `addFluid`, `addInitialFluid`, `removeFluid`,
`addFromMultiplied`, `getFilledRatio`); `zombie/characters/IsoGameCharacter.DrinkFluid` (all five
overloads); `zombie/network/packets/ItemStatsPacket` (via [food-item-model.md](food-item-model.md)).
The full bytecode read of the fluid path, with every address, is
`.superpowers/sdd/05-food-scanner/q3-fluid-nutrition-notes.md` (session record, not tracked); the
load-bearing addresses are quoted inline above so this document stands on its own.

**Lua** `shared/TimedActions/ISDrinkFluidAction.lua` (`:26–:30`, `:42–:48`, `:109–:120`),
`shared/TimedActions/ISDrinkFromBottle.lua:70`, `client/ISUI/ISInventoryPaneContextMenu.lua:2318`
(the `Capacity > 3.0` gate behind the `drinkable` column),
`client/DebugUIs/DebugMenu/Fluids/ISFluidCategoriesViewPanel.lua:229`.

**Measured run 1 — census and spot checks.** `exp05-20260910-084109`,
[`testing/artifacts/exp05-20260910-084109/food-scan.json`](../../testing/artifacts/exp05-20260910-084109/food-scan.json)
(sha256 `a8b3edef…`), 107.6 s, fixture `default`, build 42.20.4, `server_errors []`,
`server_stopped rc=0 errors=0`. Script `testing/experiments/s05_food_scan.py`. Cite its
`items_count`, `fluid_script` and `comparison` blocks. **Provenance caveat:** its
`meta.dataset_commit` reads `72ed836`, which is the newest commit that had *touched*
`data/food-items.json` at run time and **not** the provenance of the bytes — those were the fix
round committed a little later as `25870ad`, and the artifact identifies them itself
(`meta.dataset_meta.counts.multi_fluid_containers`, a key `72ed836` does not have). Across all
1 005 items and all 61 fluids, every one of the 13 columns this run compares is identical in the
two commits — **0 differences** — so the verdict holds against either; the later per-container
columns changed no compared field. `meta.dataset_commit` / `summary.dataset_commit` are a **do not
cite** row in [`testing/artifacts/README.md`](../../testing/artifacts/README.md), together with the
run's four `fluid.script` transform labels.

**Measured run 2 — the drink probe.** `exp05b-20260910-093307`,
[`testing/artifacts/exp05b-20260910-093307/drink-probe.json`](../../testing/artifacts/exp05b-20260910-093307/drink-probe.json)
(sha256 `ca2a8385…`), 120.9 s, fixture `default`, build 42.20.4, dataset `705a12f` clean,
`server_errors []`, doctor all-`ok`. Script `testing/experiments/s05b_drink_probe.py`; harness
command `drink`. **Cite only the `atomic` / `container` / `container_fill` / `food_timer` /
`atomic_window_game_hours` blocks** — `summary.all_matched` is `false` for the reason in
§ Discrepancies row 8 and is a *do not cite* row in
[`testing/artifacts/README.md`](../../testing/artifacts/README.md). Method notes that matter to
anyone re-running it: hunger and thirst were primed to 0.5 and the nutrition stores to 500 kcal
before each drink, because the fixture's admin sits near 0 where the `[0, 1]` clamp would swallow
the relief; idle burn on this fixture is ≈ −15.3 kcal per real minute at 80 kg, at 15.95 game-seconds
per real second.

**Earlier runs cited here** `t4probe-20260910-081129` (the first `items.count` / `fluid.script`
exercise, server-only, not committed as an artifact — the same reply is reproduced byte-for-byte in
`exp05-20260910-084109`), `exp01-20260910-003929` and `exp02-20260910-030433` (the *measured*
absent-key defaults the spot-check comparator expects, rather than assumed ones), and
`run-20260910-081230` (`pzt run --hold 20`, PASS, 0 server errors, on the harness file with both
census commands).

**Tooling and prior work in this library** [`data/README.md`](../../data/README.md) § food-items
(the column authority), `tools/README.md`, [food-item-model.md](food-item-model.md) (the 114-key
table, the aging/cooking model and the `ItemStatsPacket` analysis),
[eating-pipeline.md](eating-pipeline.md) (how these values reach `Stats` and `Nutrition`),
[nutrition-core.md](nutrition-core.md), [body-stats.md](body-stats.md) (the idle-burn model behind
§ Discrepancies row 8), [`../testing/README.md`](../testing/README.md) (the harness commands and
the experiment scripts), [`docs/superpowers/plans/05-food-scanner.md`](../superpowers/plans/05-food-scanner.md)
(the plan and its acceptance results).
