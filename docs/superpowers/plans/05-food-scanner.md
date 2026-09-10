# Slice 05 — P4a Food scanner + dataset — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A stdlib parser for the B42 script block format and a complete dataset of every vanilla food and drink item — every field in [`food-item-model.md`](../../vanilla/food-item-model.md)'s 114-key table plus identity, module, display name, category, tags and the `ReplaceOn*` links — cross-checked against the live game (count) and spot-checked field-for-field on ten items.

**Architecture:** `tools/food_scan.py` parses the generated script DSL into nested blocks, types each key from the slice-02 key table, joins `component FluidContainer` items to their `fluid` definitions and both to the EN translation JSONs, and writes `data/food-items.{csv,json}`. A new server-side harness command `items.count` counts the game's own loaded script items through `ScriptManager`, and `fluid.script <id>` reads a fluid's live nutrition; one experiment (`s05_food_scan.py`) collects the count and the ten spot checks into a tracked artifact.

**Tech Stack:** Python 3.13 (stdlib only), harness Lua (Kahlua), `pzt`, `pzdis` via `./pz.sh`.

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md`

## Global Constraints

- Build **42.20.4 (`b0bbce05d5`)**; evidence grades C/M/W on every claim row; brief commits (`Slice 05: …`) without attribution; one live server+client session at a time; the game install is **read-only**; every judgment call takes the default and gets a `docs/decisions.md` row; house doc skeleton with an **MP behavior** section; `cd` into the repo in every shell call (the cwd resets between calls).

---

## Header

- Slice: **05** · Phase P4a · Status: ready · Verify against 42.20.4 (`b0bbce05d5`) · Depends on: 02 · Estimate: 2 h.

## Cold-start context

- Repo `C:\Users\Angus\repos\project_zomboid`; charter `STRATEGY.md`; board `docs/progress.md`; ledger `docs/decisions.md`. Jar toolchain `cd C:\Users\Angus\pz-b42 && ./pz.sh grep|methods|refs|dump` (`WORKSPACE.md` there). Live server `python testing/pzt {run,scenario,doctor}`.
- **Script layout, verified in the install on 2026-09-10** — the spec's guess of `media/scripts/fluids/` is wrong, **there is no such directory**. Under `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\scripts\` sit `entities/`, `generated/`, `ragdolls/`, `xui/`, and everything this slice reads is under `generated/`: `items/food.txt` (15 525 lines, **722** `ItemType = base:food` blocks — the **only** file in the install holding one); `items/drainable.txt` (2 420 lines, **150** `base:drainable`, of which only `Vinegar2` and `Vinegar_Jug` carry `Calories`, both `0.0`); `fluids.txt` (20 `fluid` blocks) + `fluids_Alcoholic.txt` (18) + `fluids_Beverages.txt` (23) = **61 fluid definitions**, 44 with `Calories`; and `component FluidContainer { … }` **133** times across `items/*.txt` (`normal.txt` 125, `clothing.txt` 4, `container.txt` 2, `weapon.txt` 2) and **zero** times in `food.txt`/`drainable.txt` — so a B42 drink is a `base:normal` item with a fluid component, not a `Food`.
- Format facts: one `module Base` per file; braces on their own lines; every value line ends in a comma; **no comments anywhere** in `generated/`; `food.txt`/`drainable.txt` have **no nested blocks** (723 / 151 `{` lines = 1 module + 722 / 150 items); item names are unique and no key repeats in a block; values may contain spaces (`…;Stir fry:20;…`) and `|` (`Sandwich:5|Cooked`).
- **Display names are JSON in B42**, not `ItemName_EN.txt` (which does not exist): `media/lua/shared/Translate/EN/ItemName.json` — 4 889 entries keyed `Module.Name` (`"Base.Pop2": "Cola"`) — and `Fluids.json` — 197 entries keyed `Fluid_Name_<id>`. Plain UTF-8, no BOM, strict JSON.
- Key inventories recount exactly to slice 02's numbers: **78** distinct keys in `food.txt`, **82** in `drainable.txt`, **114** in the union. The typed key table with the Java field and runtime effect for all 114 is [`food-item-model.md`](../../vanilla/food-item-model.md) § "Key reference"; the loader is `Item.DoParam` (`02-notes.md` Q1) — **cite it, do not re-derive it**.
- **Harness reality that shapes the spot check** (ripples from 01/02, `docs/testing/README.md`): the client command `item.script <type>` answers only `HungerChange, ThirstChange, DaysFresh, DaysTotallyRotten, IsCookable, MinutesToCook, MinutesToBurn` — Kahlua does **not** expose `Calories`/`Carbohydrates`/`Lipids`/`Proteins` on the script `Item` by getter, `is`-getter or field (`client/PZTestKit_Client.lua:232-254`). Macros must be read off an **instantiated** item on the **server** with `item.get <user> <fullType>` (returns `TK.ITEM_STATE`: `calories, carbs, lipids, proteins, hungChange, thirstChange, offAge, offAgeMax, minutesToCook, minutesToBurn, …`). Items are spawned **server-side** with RCON `additem "admin" "<type>" 1` — a client-spawned item trips a server `SyncItemFields` NPE.
- Jar facts already verified for this slice: `ScriptManager.getAllItems()Ljava/util/ArrayList;`, `getAllFluidDefinitionScripts()`, `getAllCraftRecipes()`, `getAllEvolvedRecipesList()` all exist; `Item` exposes `getName/getModuleName/getFullName/getDisplayName/getDisplayCategory/getTags/getItemType`, and `ItemType.toString()` returns the `ResourceLocation` string (`base:food`). `Item` exposes **no** component accessor, so the fluid-container count has no live route. `FluidDefinitionScript` does expose real getters: `getFluidTypeString, getDisplayName, getCategories, hasPropertiesSet, getHungerChange, getThirstChange, getCalories, getCarbohydrates, getLipids, getProteins, getFatigueChange, getStressChange, getUnhappyChange, getAlcohol, getFluReduction, getPainReduction, getEnduranceChange, getFoodSicknessChange`.
- Kahlua rules: no `goto`; `%d` on a float is fatal; `pcall` does not catch "tried to call nil" — every Java member goes through `TK.call(obj, "method", …)` / `TK.field`. Iterate a Java list as `for i = 0, n - 1 do … all:get(i) … end`.
- Baselines to preserve: `python -m pytest tools/tests -q` → **14 passed**; `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references` → **0 findings** (the repo-wide run has 4 pre-existing findings under `docs/mods-survey/teardowns/`, owned by another slice — leave them).

## Questions

1. For all 722 `base:food` blocks: which of the 114 script keys each declares, with what value and what typed representation — and which are *absent* (absence is load-bearing: 225 blocks declare no `DaysFresh` and never age; `Base.Salt` declares no macro key at all).
2. Identity per item — module, script name, full type (`Base.X`), EN display name, `DisplayCategory`, `FoodType`, `Tags` — and do all `ReplaceOnCooked` / `ReplaceOnRotten` / `ReplaceOnUse` targets resolve to a scanned item id? Which do not?
3. Drinks: which items carry drinkable nutrition through a `component FluidContainer` + `fluid` definition instead of `Food` keys; what each of the 61 fluids declares; and is a fluid's `Calories` per **unit** (scaled by container `Capacity`/amount) or absolute? Start from `Fluid.getProperties()` → `SealedFluidProperties`, `FluidContainer.getAmount/getCapacity`, and the `getCalories` referents `zombie/entity/components/fluids/{Fluid,FluidContainer,FluidProperties,SealedFluidProperties}` and `zombie/characters/IsoGameCharacter`.
4. Does the scanner's `base:food` count equal `ScriptManager.getAllItems()` in the running game, and the fluid count equal `getAllFluidDefinitionScripts()`?
5. Do ten spot-checked items match the live game field-for-field on every field the game exposes?

## Method

### Task 1: Check for an existing parser, decide, record

**Files:** none written except `docs/decisions.md` (at Task 6) and the Task-1 finding quoted into `docs/vanilla/food-dataset-notes.md`.

- [x] **Step 1: Look at the exact candidates.** `cd C:\Users\Angus\pz-b42 && ls tools/ basegen/`, read `tools/{insulation_scan,vehicle_scan,packread,cp}.py` and `basegen/{catalog,spriteindex,entity_sprites}.py`; then `cd C:\Users\Angus\repos\project_zomboid && ls tools/` (`doc_lint.py`, `mod_inventory.py`, `wiki_mirror.py` — none parses scripts). Confirm with `grep -rln "media/scripts\|parse_block\|parse_script" --include=*.py C:/Users/Angus/pz-b42` → expect exactly `tools/insulation_scan.py` and `tools/vehicle_scan.py`.
- [x] **Step 2: Record what they are.** `insulation_scan.py:parse_file` (lines 15–48) is a line loop — `MODULE_RE`/`ITEM_RE`/`PROP_RE` plus a `{`/`}` depth counter — that **flattens every `Key = Value` into one dict regardless of nesting depth**, keeping the last write, so a `component FluidContainer`'s `Capacity`/`RainFactor` silently merges into the item's own keys. It is a script, not an importable module (module-level `VANILLA`/`WORKSHOP`, prints at import), it lives outside the repo, and it reads display names from `ItemName_*.txt`, a layout B42 no longer ships. `vehicle_scan.py` is a coarser regex-chunk reader with the same properties.
- [x] **Step 3: Take the default.** **Write a new nesting-aware parser inside `tools/food_scan.py`**, borrowing `insulation_scan.py`'s line-loop shape (`tools/README.md` already names it the house convention) and adding a block stack. Do **not** import from `pz-b42` — outside the repo, would not survive a clone. Carry the sentence into Task 6's decisions row.

### Task 2: `tools/food_scan.py` — parser + tests (TDD)

**Files:** Create `tools/food_scan.py`, `tools/tests/test_food_scan.py`.

**Interfaces (produces):** `parse_script(text, path="") -> list[Block]`; `Block = {"kind","name","module","file","line","props": {k: raw_str}, "lines": [str], "blocks": [Block]}` — `lines` holds every in-block entry that is not `Key = Value` (trailing comma stripped): a fluid's `Categories` entries (`Beverage`) and, for slice 06, recipe IO lines such as `item 1 [Base.BreadSlices] flags[ItemCount]`. `coerce(key, raw) -> int|float|bool|list|str` using `KEY_TYPES`. `load_translations(media_root) -> (items: dict, fluids: dict)`.

- [x] **Step 1: Write the tests first**, with fixtures quoted verbatim from the install (line numbers are the executor's re-check anchors):

Three fixtures, quoted verbatim from the install (elisions marked `# …` are whole omitted `Key = Value,` lines of the same block; keep the rest byte-exact):

```python
APPLE = """module Base
{
    item Apple
    {
        DisplayCategory = Food,
        ItemType = base:food,
        Weight = 0.2,
        EvolvedRecipe = Cake:16;FruitSalad:8;Pancakes:8;Muffin:8;PieSweet:16;Oatmeal:4;Salad:8,
        FoodType = Fruits,
        HungerChange = -16.0,
        ThirstChange = -7.0,
        Calories = 95.0,
        Carbohydrates = 25.13,
        Lipids = 0.31,
        Proteins = 0.47,
        DaysFresh = 5,
        DaysTotallyRotten = 8,
    }
}
"""                                     # items/food.txt:8658-8677 (Icon/CustomEatSound/*Model elided)

POP2 = """module Base
{
    item Pop2
    {
        DisplayCategory = Food,
        ItemType = base:normal,
        Weight = 0.3,
        EatType = Popcan,
        Tags = base:cookable;base:hasmetal;base:sealedbeveragecan,
        component FluidContainer
        {
            ContainerName = CanPop,
            Capacity = 0.3,
            CustomDrinkSound = DrinkingFromCan,
            Fluids
            {
                fluid = Cola:1.0,
            }
        }
    }
}
"""                                     # items/normal.txt:7038-7061 (Icon/*Model/FillFrom* elided)

COLA = """module Base
{
    fluid Cola
    {
        ColorReference = Cola,
        DisplayName = Fluid_Name_Cola,
        Categories
        {
            Beverage,
        }
        Properties
        {
            fatigueChange = -2.0,
            HungerChange = -12.0,
            ThirstChange = -30.0,
            UnhappyChange = -10.0,
            Calories = 400.0,
            Carbohydrates = 104.0,
            Lipids = 0.0,
            Proteins = 0.0,
        }
    }
}
"""                                     # fluids_Beverages.txt:1-33 (StressChange/alcohol/BlendWhiteList elided)
```

Required cases (mirror `tools/tests/test_doc_lint.py`'s style — plain `assert`, no fixtures framework):
`test_flat_item_block_parses` (Apple → `kind=="item"`, `module=="Base"`, `props["Calories"]=="95.0"`, 13 props, `blocks==[]`);
`test_typed_values` (`coerce("Calories","95.0")==95.0`; `coerce("DaysFresh","5")==5`; `coerce("IsCookable","true") is True`; `coerce("CannedFood","TRUE") is True`; `coerce("Tags","base:hasmetal;base:hideuncooked")==["base:hasmetal","base:hideuncooked"]`);
`test_value_with_spaces_and_pipe` (Apple's `EvolvedRecipe` splits to 7 entries; a Steak fixture keeps `Stir fry:20` intact and `Sandwich:5|Cooked` un-split);
`test_nested_component_is_not_flattened` (Pop2 → top-level props have **no** `Capacity`; `blocks[0]["kind"]=="component"`, `name=="FluidContainer"`, its `blocks[0]["name"]=="Fluids"` with `props["fluid"]=="Cola:1.0"`);
`test_fluid_block_properties` (Cola → `blocks` named `Categories`/`Properties`; `Properties.props["Calories"]=="400.0"`; category list `["Beverage"]`);
`test_absent_key_is_absent_not_zero` (a `Base.Salt` fixture: `"Calories" not in props`, `coerce`d record has `calories is None`, and `ThirstChange` is **+20.0** — a positive value that must not be sign-flipped);
`test_line_numbers_recorded` (Apple's block `line` is the `item Apple` line, 1-based);
`test_recipe_io_lines_kept` (see the controller amendment below the parser sketch);
`test_real_install_counts` — skipped with `unittest.skipUnless(os.path.isdir(SCRIPTS_ROOT), …)` when the install is absent — asserts 722 `base:food` in `items/food.txt`, 150 `base:drainable`, 61 `fluid` blocks over the three fluid files, 133 `component FluidContainer` over `items/*.txt`.

- [x] **Step 2: Write the parser** to make them pass. Shape:

```python
#!/usr/bin/env python3
"""Scan the vanilla script DSL for every food/drink item -> data/food-items.{csv,json}.

Stdlib only. The DSL is `module <M> { <kind> <Name> { Key = Value, ... <kind> <Name> { ... } } }`;
blocks nest (a drink is `item X { component FluidContainer { Fluids { fluid = Cola:1.0 } } }`),
so keys are kept per block and never flattened. See docs/vanilla/food-item-model.md for what
each key means and Item.DoParam for the loader that reads them in-game.
"""
import csv, json, os, re

MEDIA = r"D:/SteamLibrary/steamapps/common/ProjectZomboid/media"
HEAD_RE = re.compile(r"^\s*(module|item|fluid|evolvedrecipe|craftRecipe|component|[A-Za-z]\w*)\s+(\S+)\s*$")
BARE_RE = re.compile(r"^\s*([A-Za-z]\w*)\s*$")          # `Properties` / `Categories` / `Fluids`
PROP_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*(.*?)\s*,?\s*$")

def parse_script(text, path=""):
    roots, stack, module, pending = [], [], "Base", None
    for n, ln in enumerate(text.splitlines(), 1):
        s = ln.strip()
        if not s:
            continue
        if s == "{":
            if pending is None:                          # brace with no header: keep depth honest
                pending = {"kind": "?", "name": "?", "line": n}
            blk = {"kind": pending["kind"], "name": pending["name"], "module": module,
                   "file": path, "line": pending["line"], "props": {}, "blocks": []}
            (stack[-1]["blocks"] if stack else roots).append(blk)
            stack.append(blk); pending = None
            continue
        if s == "}":
            if stack:
                stack.pop()
            continue
        m = HEAD_RE.match(s)
        if m and not s.endswith(","):
            kind, name = m.group(1), m.group(2)
            if kind == "module":
                module = name
            pending = {"kind": kind, "name": name, "line": n}
            continue
        m = BARE_RE.match(s)
        if m:
            pending = {"kind": "block", "name": m.group(1), "line": n}
            continue
        m = PROP_RE.match(s)
        if m and stack:
            stack[-1]["props"][m.group(1)] = m.group(2)
    return roots
```

**Controller amendment (2026-09-10) — the parser is shared.** Slice 06 (`tools/recipe_scan.py`) imports `parse_script` and never writes a second walker, so the sketch above must also: (1) append every in-block line that matches neither a header, a brace nor `PROP_RE` to `stack[-1]["lines"]` with its trailing comma stripped — without this the `Categories { Beverage, }` case in `test_fluid_block_properties` fails and every recipe IO line is lost; (2) accept a header with the brace on the same line (`craftRecipe MakeToast {`) — open the block from that line; check with `grep -rl "{$" ` over `generated/` whether any shipped file uses the form, and support it either way; (3) strip `//` and `/* */` comments before parsing (none exist under `generated/` today; recipe files under `generated/entities/` are the ones to re-check). Add `test_recipe_io_lines_kept`: the `MakeToast` block from `generated/entities/appliances/workstations/entity_toaster_craftRecipe.txt:3` (quote it verbatim) parses to `kind == "craftRecipe"`, `props["time"] == "20"`, and `blocks` `inputs`/`outputs` whose `lines` are `["item 1 [Base.BreadSlices] flags[ItemCount]"]` and `["item 1 Base.Toast"]`.

`KEY_TYPES` is a dict over the 114 keys transcribed from `food-item-model.md`'s table (`int`: `DaysFresh, DaysTotallyRotten, MinutesToCook, MinutesToBurn, UnhappyChange, BoredomChange, StressChange, FoodSicknessChange, PoisonPower, fluReduction, painReduction, InverseCoughProbability, InverseCoughProbabilitySmoker, ConditionMax, Eattime, …`; `float`: `Calories, Carbohydrates, Lipids, Proteins, HungerChange, ThirstChange, Weight, WeightEmpty, enduranceChange, fatigueChange, ReduceInfectionPower, AlcoholPower, UseDelta, …`; `bool`: `IsCookable, CantEat, CannedFood, Packaged, Spice, GoodHot, BadCold, BadInMicrowave, DangerousUncooked, CantBeFrozen, FishingLure, RemoveNegativeEffectOnCooked, RemoveUnhappinessWhenCooked, IsDung, Medical, SurvivalGear, …`; `list(";")`: `Tags, EvolvedRecipe, ReplaceOnCooked, Researchablerecipes, RequireInHandOrInventory, SoundMap, IconsForTexture, StaticModelsByIndex, WorldStaticModelsByIndex`; everything else `str`). Bool follows the loader: only the literal `true` (any case) is true. An unlisted key stays a string and is flagged in the JSON's `meta.unknown_keys` — that is the mod-facing `defaultModData` path, not an error.

- [x] **Step 3: Run** — `cd C:\Users\Angus\repos\project_zomboid && python -m pytest tools/tests -q` → Expected: `29 passed` (14 existing + 15 new; if a case above collapses, never fewer than 24).
- [x] **Step 4: Commit** — `git commit -m "Slice 05: script block parser and tests"`

### Task 3: Build the dataset

**Files:** Modify `tools/food_scan.py` (the build half + `main`), Create `data/food-items.json`, `data/food-items.csv`, Modify `data/README.md`, `tools/README.md`.

- [x] **Step 1: Selection rule** (write it as a docstring, it is the dataset's definition):
  **(a)** every `base:food` block in `items/food.txt` (722) — `kind="food"`;
  **(b)** every `base:drainable` block in `items/drainable.txt` (150) — `kind="drainable"`, included because it is the other half of the 114-key union;
  **(c)** every item in any `generated/items/*.txt` carrying a `component FluidContainer` (133) — `kind="fluid_container"`;
  **(d)** every `fluid` definition from `fluids.txt`, `fluids_Alcoholic.txt`, `fluids_Beverages.txt` (61) as its own record set under the JSON's `fluids` key.
- [x] **Step 2: Joins.** Display name from `ItemName.json[f"{module}.{name}"]` (fluids from `Fluids.json[<DisplayName>]`, e.g. `Fluid_Name_Cola`), `None` when absent. `component FluidContainer` → `fluid_capacity` (`Capacity`), `fluid_ids` (each `Fluids.fluid` value split on `:`, first field), and the joined nutrition of the **first** listed fluid. `ReplaceOnCooked` / `ReplaceOnRotten` / `ReplaceOnUse` / `ReplaceOnDeplete` values are resolved against the scanned id set; unresolved targets go to `meta.unresolved_links` with the item and key that named them.
- [x] **Step 3: Write both files.** JSON: `{"meta": {...}, "items": [...], "fluids": [...]}` with `meta = {build: "42.20.4", jar_hash: "b0bbce05d5", generated: <UTC date>, tool: "tools/food_scan.py", sources: [<relative script paths>], counts: {food, drainable, fluid_container, fluids, unresolved_links}, unknown_keys: [...]}`; each item record carries `props_raw` (every key verbatim) **and** the typed fields, plus `source_file` + `source_line`. CSV: one row per item (fluids are joined, not rows) with these 47 columns — `id, module, name, kind, display_name, display_category, food_type, item_type, tags, nutrition_source, calories, carbohydrates, lipids, proteins, hunger_change, thirst_change, days_fresh, days_totally_rotten, cant_be_frozen, is_cookable, minutes_to_cook, minutes_to_burn, dangerous_uncooked, packaged, canned_food, cant_eat, spice, good_hot, bad_cold, unhappy_change, boredom_change, stress_change, fatigue_change, endurance_change, food_sickness_change, poison_power, alcohol_power, evolved_recipe, evolved_recipe_name, replace_on_cooked, replace_on_rotten, replace_on_use, on_cooked, on_eat, fluid_capacity, fluid_ids, weight` — plus a trailing `source_file, source_line`. An absent key is the **empty string**, never `0`; `nutrition_source` is `food_keys` or `fluid:<id>`. Write with `csv.writer(…, lineterminator="\n")` and `newline=""`.
- [x] **Step 4: Run and eyeball** — `python tools/food_scan.py` → Expected on stdout: `food 722 · drainable 150 · fluid_container 133 · fluids 61`. Then
  `python -c "import json;d=json.load(open('data/food-items.json'));i={x['id']:x for x in d['items']};a=i['Base.Apple'];print(a['calories'],a['carbohydrates'],a['days_fresh'],a['display_name']);print(i['Base.Salt']['calories'],i['Base.Salt']['thirst_change']);print(i['Base.Pop2']['nutrition_source'],i['Base.Pop2']['calories'])"`
  → Expected: `95.0 25.13 5 Apple` / `None 20.0` / `fluid:Cola 400.0`.
- [x] **Step 5: Document the columns** — add a `## food-items` section to `data/README.md` with one line per CSV column (name, type, the script key it comes from, empty-vs-zero rule) and the `meta` block's keys; move `food_scan.py` out of `tools/README.md`'s "Planned (P4)" list into a documented entry naming the four source files and the four `kind` values.
- [x] **Step 6: Commit** — `git commit -m "Slice 05: food/drink dataset"`

### Task 4: Harness `items.count` and `fluid.script` (server side)

**Files:** Modify `testing/PZTestKit/PZTestKit/42/media/lua/server/PZTestKit_Server.lua` (append before the `tick` block at the file's end), Modify `docs/testing/README.md`.

The fixture excludes `mods/`, so harness Lua changes need **no** re-provisioning.

- [x] **Step 1: Add both commands.**

```lua
-- ---- script-item census (slice 05) -------------------------------------------
-- ScriptManager.getAllItems() is the game's own loaded-item list: the cross-check for
-- tools/food_scan.py. ItemType.toString() returns the ResourceLocation ("base:food");
-- match on the suffix so a registry rename cannot silently zero the bucket. Item exposes
-- no component accessor, so fluid CONTAINERS have no live route -- only DEFINITIONS do.
local FLUID_GETTERS = { "HungerChange", "ThirstChange", "Calories", "Carbohydrates", "Lipids",
                        "Proteins", "FatigueChange", "StressChange", "UnhappyChange", "Alcohol",
                        "FluReduction", "PainReduction", "EnduranceChange", "FoodSicknessChange" }

local function listOf(sm, method)
    local ok, all = TK.call(sm, method)
    if not ok or all == nil then return nil, 0 end
    local _, n = TK.call(all, "size")
    return all, n or 0
end

TK.register("items.count", function()
    local sm = getScriptManager()
    local all, n = listOf(sm, "getAllItems")
    if all == nil then return "no ScriptManager:getAllItems" end
    local out = { total = 0, food = 0, byType = {}, foodByModule = {} }
    for i = 0, n - 1 do
        local _, sc = TK.call(all, "get", i)
        local _, t = TK.call(select(2, TK.call(sc, "getItemType")), "toString")
        t = tostring(t or "?")
        if sc ~= nil then
            out.byType[t] = (out.byType[t] or 0) + 1
            out.total = out.total + 1
            if string.find(string.lower(t), "food", 1, true) then
                out.food = out.food + 1
                local _, m = TK.call(sc, "getModuleName")
                m = tostring(m or "?")
                out.foodByModule[m] = (out.foodByModule[m] or 0) + 1
            end
        end
    end
    local _, fn = listOf(sm, "getAllFluidDefinitionScripts")
    out.fluidDefs = fn
    return out
end)

TK.register("fluid.script", function(argv)
    local all, n = listOf(getScriptManager(), "getAllFluidDefinitionScripts")
    if all == nil then return "no ScriptManager:getAllFluidDefinitionScripts" end
    local want = tostring(argv[1] or "")
    for i = 0, n - 1 do
        local _, f = TK.call(all, "get", i)
        local okid, id = TK.call(f, "getFluidTypeString")
        id = okid and tostring(id) or ""
        if id ~= "" and (id == want or id == "Base." .. want or "Base." .. id == want) then
            local out = { fluidType = id }
            local _, dn = TK.call(f, "getDisplayName"); out.displayName = dn
            local _, hp = TK.call(f, "hasPropertiesSet"); out.hasPropertiesSet = hp
            for _, g in ipairs(FLUID_GETTERS) do
                local okg, v = TK.call(f, "get" .. g)
                if okg then out[g] = v end
            end
            return out
        end
    end
    return "no fluid " .. want
end)
```

`select(2, TK.call(sc, "getItemType"))` yields the value (or `nil`), which `TK.call` then guards — the nil-safety rule is preserved without a second helper.

- [x] **Step 2: Smoke it** — `python testing/pzt doctor`, then `python testing/pzt run --hold 20`; while it holds, the run's report shows the harness loaded. Expected: PASS, 0 server errors. (The values are collected properly in Task 5; this step only proves the file still parses under Kahlua.)
- [x] **Step 3: Inventory the commands** — extend the server list in `docs/testing/README.md`'s command-bus bullet (the block that already names `item.get` / `item.set` / `item.age.tick`) with `items.count` (no args → `{total, food, byType, foodByModule, fluidDefs}`) and `fluid.script <fluidId>` (14 live property getters), and note that the food script `Item` exposes no macro getter to Kahlua, which is why `item.script` cannot answer them.
- [x] **Step 4: Commit** — `git commit -m "Slice 05: items.count and fluid.script harness commands"`

### Task 5: Live cross-check and the ten spot checks (M)

**Files:** Create `testing/experiments/s05_food_scan.py`, `testing/artifacts/<run-id>/food-scan.json`, Modify `testing/artifacts/README.md`.

Follow `testing/experiments/s02_lifecycle.py`: `new_run_dir("exp05")`, `make_server`/`make_client`, `ask(side, cmd, args)` from `_common.py`, `save()` before **and** after teardown, `hard_kill` in `finally`. One live session; nothing else running.

- [x] **Step 1: The ten items** — eight foods and two drinks, one per axis the dataset must get right: `Base.Apple` (plain, 7 evolved-recipe entries) · `Base.Steak` (cookable 50/70, `Stir fry:20`, `Sandwich:5|Cooked`) · `Base.CannedCorn` (`CannedFood`+`CantEat`+`Packaged`, **no** `DaysFresh` → `offAgeMax` stays `1000000000`) · `Base.CannedBologneseOpen` (opened can: thresholds + `ReplaceOnUse`) · `Base.BreadSlices` (`ReplaceOnCooked = Base.Toast`) · `Base.ConeIcecream` (`ReplaceOnRotten = Base.ConeIcecreamMelted`) · `Base.RatKing` (`DaysFresh == DaysTotallyRotten == 0`) · `Base.Salt` (spice, **no** macro key, `ThirstChange = +20.0`) · `Base.Pop2` (fluid container, `Capacity 0.3`, `Cola:1.0`) · `Base.JuiceBox` (`Capacity 0.2`, `JuiceGrape:1.0`, `Eattime 160`).
- [x] **Step 2: Collect.** Server `items.count`; then per item `server.rcon(f'additem "admin" "{t}" 1')`, wait `SPAWN_WAIT = 2.5`, `ask(server, "item.get", f"admin {t}")`; client `ask(client, "item.script", t)`; server `ask(server, "fluid.script", "Cola")` and `"JuiceGrape"`. Write all of it plus the scanner's records for the same ten ids into `<run_dir>/food-scan.json`.
- [x] **Step 3: Compare inside the experiment**, verdict in the artifact as `comparison`: per item, per field, `{script, live, source, match}` over `HungerChange/ThirstChange/DaysFresh/DaysTotallyRotten/IsCookable/MinutesToCook/MinutesToBurn` (client `item.script`) and `calories/carbs/lipids/proteins/hungChange/thirstChange/offAge/offAgeMax/minutesToCook/minutesToBurn` (server `item.get`). The instance transforms the script value: `HungerChange`/`ThirstChange` are **÷100** (`Item.InstanceItem`), `DaysFresh`→`offAge`, `DaysTotallyRotten`→`offAgeMax`, and an absent threshold reads back `1000000000`. Floats compare with `abs(a-b) <= 1e-4`; a mismatch is a **finding to document**, never a reason to hand-edit the dataset.
- [x] **Step 4: Run** — `python testing/experiments/s05_food_scan.py` → Expected: `items.count.food == 722`, `fluidDefs == 61`, all ten items matching on every compared field, `server_errors []`, well under 5 min wall. Copy the JSON byte-for-byte to `testing/artifacts/<run-id>/food-scan.json` (`sha256sum` it) and add the row to `testing/artifacts/README.md`'s Contents table. No time-speed change is made, so nothing needs restoring.
- [x] **Step 5: Commit** — `git commit -m "Slice 05: live count cross-check and ten-item spot check"`

### Task 6: `docs/vanilla/food-dataset-notes.md`, lint, ledgers

**Files:** Create `docs/vanilla/food-dataset-notes.md`, Modify `docs/vanilla/README.md`, `docs/progress.md`, `docs/decisions.md`.

- [x] **Step 1: Write the doc** in the house skeleton, header `**Verified against: 42.20.4 (`b0bbce05d5`)**` + date + slice, five-line summary, then: **Model** — what the dataset *is* (the four `kind` buckets with counts, the selection rule, empty-vs-zero, the `nutrition_source` rule, the CSV/JSON split), `Ev` column on every table; **Code map** — the source files with line counts plus the `ScriptManager`/`FluidDefinitionScript` methods the live check used; **MP behavior** — script data loads identically on both sides and is never synced, while the *instance* fields are server-owned (cite `food-item-model.md` § MP behaviour and the `ItemStatsPacket` zero-field leak), so a mod reading these numbers off a client instance may be reading another item's value: read the dataset, not the instance; **Discrepancies** — the Q3 answer (fluid nutrition per unit vs absolute) and any spot-check mismatch; **Open questions** — what Q2/Q3 left unresolved, e.g. unresolved `ReplaceOn*` targets; **Sources** — the four script paths with counts, the two translation JSONs, the jar methods, the run id and artifact path. Every claim row carries **C**, **M** (run id + `testing/artifacts/<run-id>/food-scan.json`) or **W**. Do **not** re-derive the 114-key table — link it.
- [x] **Step 2: Index and lint** — add the `food-dataset-notes.md` row to `docs/vanilla/README.md`'s Documents table (status **done** — slice 05). Run `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references` → Expected `0 finding(s)`; `python -m pytest tools/tests -q` → Expected `28 passed`.
- [x] **Step 3: Ledgers** — `docs/decisions.md` gets one row per default taken (at minimum: the new parser rather than reusing/importing `pz-b42`; the four-bucket selection rule including drainables; CSV curated / JSON complete; `fluid.script` added beside the spec's `items.count`; empty string for an absent key). `docs/progress.md`: 05 → `done` with date, commit range and a one-line outcome, and add the ripples for slice 06 (below).
- [x] **Step 4a: Commit** — `git commit -m "Slice 05: food dataset notes"` → `44d08b7`.
- [ ] **Step 4b: Push** — `git push`. The controller's, at slice close, together with `docs/progress.md`; see § Acceptance results.

## Deliverables

- `tools/food_scan.py`; `tools/tests/test_food_scan.py`
- `data/food-items.json`, `data/food-items.csv`; `data/README.md` + `tools/README.md` updated
- harness `items.count`, `fluid.script` (server); `docs/testing/README.md` inventory updated
- `testing/experiments/s05_food_scan.py`; `testing/artifacts/<run-id>/food-scan.json` + `testing/artifacts/README.md` row
- `docs/vanilla/food-dataset-notes.md`; `docs/vanilla/README.md`, `docs/progress.md`, `docs/decisions.md`

## Acceptance checks

1. `python tools/food_scan.py` prints `food 722 · drainable 150 · fluid_container 133 · fluids 61` and rewrites both data files.
2. The live `items.count` reports `food == 722` and `fluidDefs == 61` — equal to the scanner's counts (Q4).
3. All ten spot-checked items match field-for-field on every field the game exposes, recorded in the artifact's `comparison` (Q5); any mismatch is documented as a finding, not patched away.
4. `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references` → `0 finding(s)`.
5. `python -m pytest tools/tests -q` → green, ≥ 24 tests (14 pre-existing untouched).
6. `python testing/pzt run --hold 5` → PASS with the new commands loaded.
7. Every one of Q1–Q5 has a cited answer in `docs/vanilla/food-dataset-notes.md`.

## Expected decision points (defaults)

- **Drainables look out of scope** (only 2 carry `Calories`, both `0.0`) → include them anyway as `kind="drainable"`; they are half of the 114-key union and slice 06 joins recipe results across every kind. Log it.
- **`ItemType.toString()` returns something other than `base:food`** (e.g. bare `Food`) → the suffix match already handles it; record the raw string in `byType` and quote it in the doc rather than changing the comparison.
- **`getAllFluidDefinitionScripts` is not exposed to Kahlua** → drop `fluidDefs`/`fluid.script`, keep `items.count`, and grade the 61-fluid count **C** (scanner-only) with an open question. Do not block.
- **A fluid's nutrition turns out to be per unit of fluid** → keep the raw fluid value in the fluid record and add a computed `calories_per_container = fluid.Calories × Capacity × share` column with the arithmetic cited; if the jar reading is ambiguous after 20 minutes, ship the raw values, mark `nutrition_source` accordingly, and log the ambiguity as an open question for slice 06.
- **A spot-check field mismatches** → the dataset is not edited. Re-read the block at its `source_file:source_line`, confirm the instance transform (÷100, threshold sentinel), and if it still differs write it up under **Discrepancies** with both numbers.
- **An `additem` fails for a sealed/uneatable item** (`CannedCorn`, `RatKing`) → substitute the next item on the same axis (`Base.TinnedBeans` for the sealed can), record the substitution in the artifact and the doc.
- **The parse turns up a key not in the 114-key table** → it is a real finding (mods and new content land in `defaultModData`): keep it as a string, list it in `meta.unknown_keys`, and name it in the doc's open questions. Never drop it silently.

## Done protocol

- `docs/progress.md` 05 → **done** (date, commit range, outcome) with **ripples for slice 06**: (a) the join key is `data/food-items.json` → `items[].id` (`Base.<name>`), with `kind`, `calories/carbohydrates/lipids/proteins`, `hunger_change`, `is_cookable`, `replace_on_cooked`, `replace_on_rotten` and `evolved_recipe` the fields a recipe result resolves against; (b) B42 drinks are `base:normal` + `component FluidContainer` joined to `generated/fluids*.txt`, **not** `Food` items, and `media/scripts/fluids/` does not exist; (c) `parse_script` in `tools/food_scan.py` is the shared block reader — slice 06 imports it rather than writing a second one; (d) the live macro readback route is server `item.get` on an RCON-spawned instance, because `item.script` cannot answer the four macros.
- `docs/decisions.md` rows for every default taken; `testing/artifacts/README.md` row for the run; push.

## Acceptance results (2026-09-10)

Every step above ran and is ticked, with one exception noted at the end. Six tasks, ten
commits: `31478dd` (parser + tests), `0728c8e` (parser fixes: typed fluids, repeated keys,
multi-word headers), `948baa2` (`items.count` / `fluid.script`), `72ed836` (dataset),
`25870ad` (dataset fixes: the `values` helper, `replace_on_deplete` as column 48),
`5290bfb` (live count cross-check and ten spot checks), `b786881` (per-container fluid
columns — the plan's per-unit decision point firing), `6a30471` (driver provenance and the
artifact README disclosure), `705a12f` (`nutrition_source` empty where no nutrition key
exists), `abeb35e` (the live drink probe), plus this task's doc commit. Two live sessions
produced committed evidence: `exp05-20260910-084109` and `exp05b-20260910-093307`.

1. `python tools/food_scan.py` → **`food 722 · drainable 150 · fluid_container 133 ·
   fluids 61`**, verbatim, and both data files rewritten — `1005 items, 61 columns` to the CSV,
   `1005 items + 61 fluids` to the JSON, with `37 unresolved links, 6 missing display names,
   0 undefined fluid refs, 60 unknown keys`. Two consecutive runs are byte-identical, re-checked
   at every dataset change since. **The digests below are the committed files at the final fix
   wave** (the last commit that touches `data/`): JSON md5 `d0dc576d…` / sha256 `c71202bd…`, CSV
   md5 `1470c85c…` / sha256 `a5887934…`. Items and fluids are sorted by `id` and the only field
   that moves between days is the `meta.generated` build stamp. (The `e614ef18…` / `c74d487e…`
   pair first quoted here was `b786881`'s. The CSV moved once after it, at `705a12f`, and is
   unchanged since; the JSON moved at `705a12f` — `b3833cd3…` — and again in the fix wave, which
   added the one line `meta.counts.fluid_containers_initial_percent`.) The column count grew twice
   after the plan was written — 47 + 2 → 48 + 2 (`replace_on_deplete`) → 59 + 2 (the eleven
   per-litre columns) — and `data/README.md` is renumbered 1–61 to match.
2. **Q4: yes.** Live `items.count` reported `total 5092`, `food 722`,
   `byType["base:food"] 722`, `byType["base:drainable"] 150`, `foodByModule {Base: 722}` and
   `fluidDefs 61` — equal to the scanner and to the plan's expectations, on **two independent
   boots** (`t4probe-20260910-081129` and `exp05-20260910-084109`, byte-for-byte the same
   reply). The live fluid id set is *exactly equal* to the 61 script blocks in both directions,
   so the cross-check covers fluid identity and not just the count. `ItemType.toString()`
   returns the `base:food` ResourceLocation form, so that decision point never fired. The 133
   `fluid_container` count has **no** live route — the script `Item` exposes no component
   accessor — and stays grade C, recorded as an open question.
3. **Q5: yes, 0 mismatches.** Ten items, one per axis, spawned server-side and read on both
   sides: **182 fields compared, 170 matched, 12 `n/a`, 0 mismatched**, `summary.mismatches`
   `[]`, no substitution needed (the sealed, uneatable `Base.CannedCorn` spawned fine, so the
   ruled `Base.TinnedBeans` stand-in was never used). The 12 `n/a` are themselves the finding,
   not a gap: a `base:normal` fluid container's instance answers the four `InventoryItem`
   ageing/cooking fields and none of the six `Food` nutrition getters. Artifact
   `testing/artifacts/exp05-20260910-084109/food-scan.json` (`comparison`), 107.6 s,
   `server_errors []`.
4. `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references` → **`0
   finding(s)`**, run on the tree with `docs/vanilla/food-dataset-notes.md` in place. The 4
   pre-existing findings under `docs/mods-survey/teardowns/` stay deferred by the standing
   ruling in [`docs/decisions.md`](../../decisions.md).
5. `python -m pytest tools/tests -q` → **`59 passed in 0.70s`**, and **`60 passed`** after the
   final fix wave's added test — 14 pre-existing (untouched) plus 46 in
   `tools/tests/test_food_scan.py`, well above the plan's `≥ 24` floor. The step
   texts' `29 passed` / `28 passed` were written before the three fix rounds; nothing was
   deleted or weakened in any of them.
6. `python testing/pzt run --hold 5` → **met** by `run-20260910-081230`, a `--hold 20` run (a
   superset) on the harness file carrying both census commands: **PASS**, `server_stopped rc=0
   errors=0`, `faults []`, `server_errors []`; an earlier identical PASS is
   `run-20260910-080558`. The tick poller is registered at the *bottom* of
   `PZTestKit_Server.lua`, after the inserted block, so `ping server=ok:pong` is itself proof
   the whole file parsed under Kahlua. Task 5b later appended the `drink` command to the same
   file; that version has not been through `pzt run`, but it booted clean in
   `exp05b-20260910-093307` (`server_errors []`, `server_stopped rc=0`, doctor all-`ok`), which
   exercises the same load path.
7. **Q1–Q5 each have a cited answer** in [`docs/vanilla/food-dataset-notes.md`](../../vanilla/food-dataset-notes.md)
   § The five questions, one row per question with its evidence grade.

**Two plan expectations moved.** (a) The per-unit decision point fired: a fluid's `Properties`
are per **litre**, so the dataset gained `nutrition_basis`, `fluid_share`, `fluid_fill_litres`,
`fluid_pick_random`, `drinkable` and six `*_per_container` columns rather than the single
`calories_per_container` the plan sketched — and the multiplier is `fluid_fill_litres`, which
*is* the plan's `Capacity × share`. (b) The plan had no live drink measurement; one was added
as Task 5b (`exp05b-20260910-093307`), which closes slice 01's open question 11 and takes the
per-litre arithmetic from C to **C + M**: `+120.000031` kcal and `+31.200001` g carbs from one
0.3 L Cola can, `+60 / +15.6` at `f = 0.5`, `+80 / +23.999996` from a 0.2 L JuiceBox.

**What is not in this task's commit.** Step 4's `git push` and Step 3's `docs/progress.md`
half — the board row, its commit range and the slice-06 ripples — are the controller's
close-out. Step 3's `docs/decisions.md` half landed here: fourteen slice-05 rows (seventeen after the final fix wave).

- Post-fix-wave live check (`1c4dfa5`, the harness carrying `drink` and the reworked `fluid.script`): `python testing/pzt run --hold 5` → PASS (`run-20260910-104514`, server up 14.6 s, session ready 53.0 s, 0 server errors); probe `accept05-20260910-104622` (68.7 s): `items.count` total 5092 / food 722 / fluidDefs 61; `fluid.script Water` answered via the `getFluidType` route and `fluid.script Cola` via `getFluidTypeString`, both with `hasPropertiesSet true` and no `missingGetters`; `drink` answered its usage string; 0 server errors, 0 client Lua errors. Acceptance check 6 is therefore met on the tree as shipped.
