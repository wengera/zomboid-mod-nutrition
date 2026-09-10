# Slice 02 — P1c Food item model & lifecycle — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A complete, cited reference of the food item: every script property that matters for nutrition and spoilage, the fresh → stale → rotten timeline (including fridge/freezer), cooking and burning transitions, evolved-recipe nutrition summation, and who owns item state in MP.

**Architecture:** Enumerate the keys of `scripts/generated/items/food.txt` and `drainable.txt`, map each to the loader (`zombie/scripting/objects/Item` / the food script class) and to the runtime (`zombie/inventory/types/Food.update`, `EvolvedRecipe`), then confirm the timeline and transitions on the live session with the `item.state` / `item.age` commands; write `docs/vanilla/food-item-model.md`.

**Tech Stack:** `pzdis` via `./pz.sh`, Python 3.13, harness Lua, `pzt`.

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md`

## Global Constraints

- Verified-against build: **42.20.4 (`b0bbce05d5`)**; evidence grades C/M/W on every claim; commit style brief + no attribution; one live session at a time; game install and workshop folder read-only; defaults + `docs/decisions.md` for judgment calls; house doc skeleton (summary → model → code map → MP behaviour → discrepancies → open questions → sources).

---

## Header

- Slice: **02** · Phase P1c · Depends on: 01 (harness commands, doc_lint, mirrors) · Estimate: 3 h.

## Cold-start context

- Repo `C:\Users\Angus\repos\project_zomboid`; charter `STRATEGY.md`; board `docs/progress.md`; ledger `docs/decisions.md`; spec above.
- Jar: `cd C:\Users\Angus\pz-b42 && ./pz.sh grep|methods|refs|dump …`. Game files: `D:\SteamLibrary\steamapps\common\ProjectZomboid\media`.
- Scripts: `media/scripts/generated/items/food.txt` — `module Base { item X { Key = Value, … } }`, `ItemType = base:food` (722 items); `drainable.txt` (150, `base:drainable`); evolved recipes `media/scripts/generated/evolvedrecipes.txt`; craft recipes `media/scripts/generated/recipes/*.txt` (`craftRecipe` blocks).
- Keys seen in `food.txt` (count of items using each): Weight/ItemType/DisplayCategory 722, HungerChange 606, Calories/Carbohydrates/Lipids/Proteins 597, DaysFresh/DaysTotallyRotten 497, EvolvedRecipe 372, FoodType 362, UnhappyChange 292, EatType 266, IsCookable 251, MinutesToCook 249, MinutesToBurn 246, EvolvedRecipeName 172, GoodHot 148, Packaged 129, BadInMicrowave 115, ThirstChange 112, ReplaceOnUse 110, Spice 109, CantEat 96, DangerousUncooked 81, BadCold 61, CantBeFrozen 51, PourType 49, CannedFood 41, RemoveUnhappinessWhenCooked 36, StressChange 28, OnCreate 21, OnEat 19, plus rarer ones (list them all with `grep -oE "^\s*[A-Za-z]+\s*=" food.txt | sort | uniq -c`).
- Live server: `python testing/pzt run`; harness commands from slice 01: `item.script <type>`, `item.state <type> <state>`, `eat`, `nutrition.get/set`; write experiments as `testing/experiments/s02_*.py` following `s01_eat_smoke.py`.
- Prior findings: `docs/vanilla/eating-pipeline.md` (slice 01), `docs/testing/spikes.md` S6 (server holds the player's inventory; client-side item edits never reach it; `sendItemStats` is server→client).

## Questions

1. Which script keys exist for food/drainable items in 42.20.4, what type is each, and which Java field/getter each populates (from the script loader)?
2. What is the exact aging model: `Age`, `DaysFresh`, `DaysTotallyRotten`, `OffAge`/`OffAgeMax`, `isFresh`/`isRotten`, `RottenTime`; how does time advance (`Food.update`, `updateAge`) and how do fridge (`isInFridge`?) and freezer (`isFrozen`, `FreezingTime`, `CantBeFrozen`) change the rate?
3. What happens to hunger and the four nutrition values as an item ages (stale, rotten) — scaling in `getHungChange`/`getCalories` or a state flag consumed by `Eat`?
4. Cooking: `IsCookable`, `MinutesToCook`, `MinutesToBurn`, `CookingTime`, `isCooked`/`isBurnt`, `ReplaceOnCooked`, `RemoveNegativeEffectOnCooked`, `DangerousUncooked`, `BadInMicrowave`, `GoodHot`/`BadCold` (heat: `getHeat`, `getInvHeat`) — what each does to the item and to eating.
5. Evolved recipes: how `EvolvedRecipe` sums ingredient hunger/nutrition into the result (`zombie/scripting/objects/EvolvedRecipe`, `addItem`, `Spice`, `MaxItems`, `MinimumWater`) and how cooking a pot of soup changes its values.
6. Packaged/canned: `Packaged`, `CannedFood`, `ReplaceOnUse`, `Cooked`-on-open — do cans age? what does opening do?
7. `Poison`, `PoisonPower`, `UseForPoison`, `PoisonDetectionLevel` — how poison rides on food and what it does (brief; it is in the eat pipeline).
8. **MP**: which side ages items (server for world containers? client for the player's inventory?), how a rotten transition reaches the other side, and what a mod must do to change an item's nutrition for an MP player (per S6: server-side edit + `sendItemStats`).

## Method

### Task 1: Script key inventory (C)

- [ ] **Step 1:** `cd D:\...\media\scripts\generated\items && grep -oE "^\s*[A-Za-z]+\s*=" food.txt | sed 's/[ =]//g' | sort | uniq -c | sort -rn > C:\Users\Angus\repos\project_zomboid\testing\runs\s02-food-keys.txt` and the same for `drainable.txt`.
- [ ] **Step 2:** Find the loader: `./pz.sh grep "HungerChange" --max 10` → expect `zombie/scripting/objects/Item` (or a `FoodScript`/`ItemScript` class); `./pz.sh dump <class> load` (or `parse`/`LoadItem`) and list every `case "<Key>"`-style branch: key → field/setter. Keys present in scripts but absent from the loader are **dead keys** — say so.
- [ ] **Step 3:** For each key write one row (Key · Type · Java field/getter · Runtime effect · Ev=C) in the notes.

### Task 2: Aging and spoilage (C then M)

- [ ] **Step 1 (C):** `./pz.sh methods zombie/inventory/types/Food | grep -iE "age|fresh|rotten|off|freez|frozen|fridge|update"`; dump `Food.update`, `updateAge` (or the method that advances `Age`), `isFresh`, `isRotten`, `getOffAge`, `getOffAgeMax`, `setFrozen`, `getFreezingTime`, and the fridge check (`./pz.sh grep "Fridge"` → the container-type test). Record the per-tick formula and every multiplier (freezer 0×? fridge ¼×? — read the constants).
- [ ] **Step 2 (C):** dump `Food.getHungChange` / `getCalories` / `getCarbohydrates` etc. to see if age scales them (compare with slice 01's findings; do not duplicate — cite).
- [ ] **Step 3 (M):** add a client command `item.age <type> <days>` (sets `it:setAge(days)`; returns `itemState(it)` from slice 01) and an experiment `testing/experiments/s02_aging.py`: spawn `Base.Steak` (DaysFresh/DaysTotallyRotten from `item.script`), set age to 0, DaysFresh−0.1, DaysFresh+0.1, DaysTotallyRotten+0.1 and read `fresh/rotten/hungChange/calories` at each; then set frozen and age again. Record run id.
- [ ] **Step 4 (M, accelerated):** with `settimespeed 30` (RCON via `server.rcon("settimespeed 30")`), leave a fresh item in the inventory for 1 game-day (≈ 3.2 min wall) and read its age: does the client age player-inventory items? Restore speed with `settimespeed 1`.

### Task 3: Cooking transitions (C then M)

- [ ] **Step 1 (C):** dump `Food.setCooked`, `setBurnt`, `getCookingTime`/`setCookingTime`, `isCookable`, `getHeat`, `setHeat`, `getReplaceOnCooked`, `isRemoveNegativeEffectOnCooked`, `isbDangerousUncooked`; find the cooking driver (`./pz.sh grep "MinutesToCook"` → the oven/campfire code, e.g. `zombie/iso/objects/IsoStove` or an entity component) and record the minute counters.
- [ ] **Step 2 (M):** experiment `s02_cooking.py`: `item.state Base.Steak cooked` then `eat` (slice 01 command) vs raw; `burnt`; note `DangerousUncooked` items raw (`Base.Steak` — does `Eat` apply sickness? read `Eat`'s poison/sickness branch from slice 01's notes).

### Task 4: Evolved recipes and packaging (C, M where cheap)

- [ ] **Step 1 (C):** `./pz.sh methods zombie/scripting/objects/EvolvedRecipe`; dump `addItem` (or `addItemToRecipe`), `getResultItem`, the hunger/nutrition summation and the `Spice`/`MaxItems`/`MinimumWater` checks; read `media/scripts/generated/evolvedrecipes.txt` and `media/lua/client/ISUI/ISInventoryPaneContextMenu.lua` (search `evolvedRecipe`) for the UI path.
- [ ] **Step 2 (M):** experiment `s02_evolved.py`: spawn `Base.Pot` with water? (if `MinimumWater` blocks, use `Base.BowlOfSaladRecipe`/a no-water template such as `Salad`), add two ingredients via Lua `recipe:addItem(base, ingredient, player)` (find the exact Lua-exposed method in `ISInventoryPaneContextMenu.lua`), read the result's `item.state` values, then `item.state <result> cooked` and read again.
- [ ] **Step 3 (C):** `Packaged`, `CannedFood`, `ReplaceOnUse`: `./pz.sh grep "CannedFood"` and dump the readers; note whether canned items have `DaysFresh` (grep `food.txt`).

### Task 5: MP ownership (M)

- [ ] **Step 1:** add a **server** command `item.set <username> <type> <field> <value>` in `PZTestKit_Server.lua` (find the player by name in `getOnlinePlayers()`, find the item by type in their inventory, apply `setCalories`/`setHungChange`/`setAge`/`setRotten` by field name, then `sendItemStats(item)`), and an experiment `s02_mp_item.py`: RCON `additem "admin" "Base.Apple" 1`, server `item.set admin Base.Apple calories 999`, client `witness.item Base.Apple` — does the client see 999? Then the reverse (client `item.tamper`, slice S6) is already known to fail: cite S6.
- [ ] **Step 2:** aging in MP: leave the apple for one accelerated game-day; `witness.item` — do client and server ages match?

### Task 6: Mirrors and doc

- [ ] **Step 1:** `python tools/wiki_mirror.py "Food spoilage" Refrigerator Freezer "Evolved recipes"` (skip any page that does not exist — the tool errors; log the page as absent in the doc's sources), write digests.
- [ ] **Step 2:** Write `docs/vanilla/food-item-model.md` in the skeleton: key reference table (all keys, `Ev` column), aging model as pseudo-code with constants, cooking table, evolved-recipe summation, packaging, poison (brief), **MP behaviour** with the `item.set` measurement, discrepancies vs mirrors, open questions, sources. Update `docs/vanilla/README.md` (row done).
- [ ] **Step 3:** `python tools/doc_lint.py` → 0 findings. Commit `git commit -m "Slice 02: food item model and lifecycle"`.

## Deliverables

- `docs/vanilla/food-item-model.md`; `docs/vanilla/README.md` updated
- harness: client `item.age`, server `item.set`; `testing/experiments/s02_{aging,cooking,evolved,mp_item}.py`
- mirrors for the pages fetched

## Acceptance checks

1. `python tools/doc_lint.py` → 0 findings.
2. Every key from the `food.txt`/`drainable.txt` key inventory appears in the reference table (mechanical: `python - <<EOF` that reads the key list file and greps the doc for each key; 0 missing).
3. At least 4 **M** rows (aging, cooking, evolved, MP) citing `exp02-*`/`s02` run ids.
4. `python testing/pzt run --hold 5` passes.

## Expected decision points (defaults)

- A key with no loader branch → mark "dead key (not read by 42.20.4)" rather than researching further.
- If `EvolvedRecipe` Lua calls need a UI context that fails headlessly → record the Java summation from bytecode (C) and mark the M row "not measurable via harness; needs UI".

## Done protocol

- `docs/progress.md`: 02 → `done` (+ ripples: e.g. clamp values for slice 04; aging side for the MP model doc).
- `docs/decisions.md` rows; push.
