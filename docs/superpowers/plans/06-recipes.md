# Slice 06 — P4b Recipes & cooking dataset — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The vanilla ingredient → result mapping as data: every `craftRecipe` block (inputs, outputs, item mappers, fluids), every `evolvedrecipe` block with its ingredient list resolved the way the game resolves it, and — joined against slice 05's item dataset — the nutrition delta of each transformation, so the item pass can ask "what does turning X into Y cost or create" without re-reading scripts.

**Architecture:** One new tool `tools/recipe_scan.py` that **imports** `tools/food_scan.py`'s block parser (05 owns the DSL parser, 06 owns the recipe schema) and reads `data/food-items.json` for nutrition; two JSON + two CSV datasets; a server-side harness file `PZTestKit_Server_Recipes.lua` whose `recipes.count` / `recipes.evolved` / `recipes.craft` cross-check the scan against `ScriptManager` in a live game; one experiment driver `testing/experiments/s06_recipes.py`; `docs/vanilla/recipes-dataset-notes.md`.

**Tech Stack:** Python 3.13 (stdlib only), harness Lua (Kahlua), `pzt`, `pzdis` via `./pz.sh`.

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md`

## Global Constraints

- Build **42.20.4 (`b0bbce05d5`)**; evidence grades C/M/W on every claim row; brief commits without attribution; one live session at a time; the game install is **read-only**; every judgment call takes the stated default and gets a `docs/decisions.md` row; house doc skeleton with an MP behaviour section; `python tools/doc_lint.py` must be 0.

---

## Header

- Slice: **06** · Phase P4b · Depends on: **05** (`tools/food_scan.py`, `data/food-items.json`) · Estimate: 2 h.

## Cold-start context

- Repo `C:\Users\Angus\repos\project_zomboid`; charter `STRATEGY.md`; board `docs/progress.md`; ledger `docs/decisions.md`. `cd` into the repo in **every** shell call — the cwd resets between calls. Python 3.13, stdlib only.
- Jar: `cd C:\Users\Angus\pz-b42 && ./pz.sh grep|methods|refs|dump` (`WORKSPACE.md` there). Game scripts, read-only: `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\scripts`.
- Live server: `python testing/pzt {doctor,run,boot,attach}`; harness at `testing/PZTestKit/PZTestKit/42/media/lua/{shared,server,client}/`; `TK.register(name, fn(argv, kv))`, `TK.result`, `TK.call(obj, "method", ...)`. **Kahlua:** no `goto`, `%d` on a float is fatal, `pcall` does not catch "tried to call nil" — every Java member goes through `TK.call`. Experiments are drivers `testing/experiments/sNN_*.py` on `_common.py` (`ask(side, cmd, args)`, `save`, `hard_kill`), one artifact JSON each.
- The authority on nutrition arithmetic is `docs/vanilla/food-item-model.md` — **cite it, never re-derive it**: § Evolved recipes (the summation), § Cooking (`ReplaceOnCooked`), § Key reference. `docs/superpowers/plans/02-notes.md` Q5 is the raw code map behind it; note its correction box — macros per unit of *dish hunger* rise **1.1667×** at Cooking 10, not 1.667×.
- Wave-1 findings that bind this slice: cooking changes **no** stored nutrition (the only nutrition state modifier in the game is `Eat`'s ÷5 for burnt; rotten keeps full macros), so a **type change** — `ReplaceOnCooked`, `ReplaceOnRotten`, or a `craftRecipe` — is the only way cooking or rotting moves calories. Script data is static and identical on both sides; what is sided is the *result item's* state, which slice 02 settled.

## Questions

1. **Format.** What exactly is a B42 `craftRecipe` block — top-level keys, the `inputs` / `outputs` / `itemMapper` / `overlayMapper` sub-blocks, and the grammar of an IO line? Which files hold them?
2. **Legacy.** Do legacy `recipe` blocks still exist in 42.20.4 — in the shipped scripts, and in the loader?
3. **Evolved recipes.** How does an item's `EvolvedRecipe = Name:use[|Cooked]` key reach a recipe — direct name, `Template`, the parse-time aliases — and is the match case-sensitive? How many (recipe, ingredient) pairs does vanilla have?
4. **Cooking deltas.** For every transformation that changes an item's type — a food-only `craftRecipe`, a `ReplaceOnCooked` link, a `ReplaceOnRotten` link — what is the macro/hunger delta, and does the data confirm that plain cooking (no type change) is a zero delta?
5. **Evolved deltas.** What does one unit of each ingredient contribute to its dish at Cooking 0 and Cooking 10, applying the cited summation to slice 05's numbers?
6. **Cross-check.** Do the scanned counts equal what the live game loaded (`ScriptManager.getAllCraftRecipes` / `getAllEvolvedRecipesList` / `getAllRecipes`), and does the Python template expansion equal `EvolvedRecipe.getPossibleItems()` per recipe?
7. **MP.** Is any of this per-side? (Expected: the dataset is not; the swaps and the perk level that drives the summation are.)

## What slice 06 consumes from slice 05 — the contract

Read-only, by exact name:

- `tools/food_scan.py` — the DSL block parser. Slice 06 **imports** it (`sys.path` insert + `import food_scan`, the pattern `tools/tests/test_doc_lint.py:2-3` already uses) and adds no second parser.
- `data/food-items.json` — a `meta` block plus one row per food item keyed by **full type** (`Base.Apple`). The only fields 06 reads: `Calories`, `Carbohydrates`, `Lipids`, `Proteins`, `HungerChange`, `ThirstChange`, `EvolvedRecipe`, `EvolvedRecipeName`, `Spice`, `IsCookable`, `MinutesToCook`, `MinutesToBurn`, `ReplaceOnCooked`, `ReplaceOnRotten`, `ReplaceOnUse`, `DaysFresh`, `DaysTotallyRotten`, `Tags`, and whatever the row carries for source file/line.
- `data/food-items.csv` is **not** read — JSON is the tool format (spec § Evidence and documentation standard).

Slice 05 is written in parallel with this plan, so the names above are a contract, not an observation. Task 1 verifies them against the real file and adapts **once, in one place**, without asking.

## Method

### Task 1: Contract check and the shared parser

**Files:** Read `tools/food_scan.py`, `data/food-items.json`; Modify `tools/food_scan.py` only if Step 3 requires it.

- [x] **Step 1: Confirm 05 landed** — `cd C:\Users\Angus\repos\project_zomboid && python -c "import json;d=json.load(open('data/food-items.json'));print(d['meta']);print(len(d.get('items',d)))"`. Expected: a `meta` naming build 42.20.4 and a row count at or above **722** (the `base:food` block count, `docs/vanilla/food-item-model.md` § Key reference; more if 05 also rows fluids/drainables). If the file is absent, set slice 06 `blocked` in `docs/progress.md` with "needs slice 05's dataset" and stop — do not build a substitute.
- [x] **Step 2: Pin the field names** — print `Base.Lettuce` and compare with the contract list. Put `FOOD_FIELDS = {...}` at the top of `recipe_scan.py` mapping this plan's names → the real ones; every later step reads through it. A field 05 does not carry maps to `None` and its dependent output is emitted as `null` with a `reason`. Any non-identity mapping → `docs/decisions.md`.
- [x] **Step 3: Pin the parser API** — `grep -n "^def \|^class \|^[A-Z_]\+ =" tools/food_scan.py`. Slice 06 needs comment stripping, the script-tree walk, and a **nested** block walker (item blocks are flat `Key = Value`; recipe blocks carry sub-blocks and lines that are not `Key = Value` at all). Slice 05 ships `parse_script(text, path)` → nested Block **dicts** with `props` (the `Key = Value` entries), `lines` (every other in-block entry — the recipe IO lines — trailing comma stripped) and `blocks` (children), plus `kind`/`name`/`module`/`file`/`line`; its plan was amended so that same-line brace headers and comments are handled too. **Use it.** If a Step 4 check fails, extend `parse_script` **in place** with a test in `tools/tests/test_food_scan.py` — never add a second walker. The `Block`/`iter_blocks` code below is the reference implementation this plan was validated with (its counts are Task 2's expected values): port a missing behaviour from it, not its API.

```python
class Block:
    """One `<kind> <name> { ... }`. `props` = the `Key = Value` entries, `lines` = the
    entries that are not (recipe IO lines), `children` = nested blocks, `line` = the
    1-based line of the header."""
    def __init__(self, kind, name, line):
        self.kind, self.name, self.line = kind, name, line
        self.props, self.lines, self.children = {}, [], []
    def child(self, kind):
        return next((c for c in self.children if c.kind == kind), None)

def strip_comments(text):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", text, flags=re.S))

HEAD_RX = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)(?:\s+(.+))?$")

def iter_blocks(text):
    """Top-level blocks, with `module` contents lifted to top level so an item /
    craftRecipe / evolvedrecipe block is reached the same way whatever its module.
    Vanilla generated scripts put one header per line with the brace on its own line or
    at the end of the header, so a header is any line whose next non-empty line opens
    `{`. No vanilla IO line contains `=`, so `=` alone decides prop vs line."""
    lines = [(n, l.strip()) for n, l in enumerate(strip_comments(text).splitlines(), 1)]
    lines = [(n, l) for n, l in lines if l]
    roots, stack, i = [], [], 0
    while i < len(lines):
        n, s = lines[i]
        skip = not s.endswith("{") and i + 1 < len(lines) and lines[i + 1][1].startswith("{")
        if s.endswith("{") or skip:
            head = s[:-1].strip() if s.endswith("{") else s
            m = HEAD_RX.match(head)
            kind, name = (m.group(1), (m.group(2) or "").strip()) if m else ("?", head)
            b = Block(kind, name, n)
            (stack[-1].children if stack else roots).append(b)
            stack.append(b)
            i += 2 if skip else 1
            continue
        if s.startswith("}"):
            if stack:
                stack.pop()
            i += 1
            continue
        if stack:
            for entry in (e.strip() for e in s.split(",")):
                if not entry:
                    continue
                k, sep, v = entry.partition("=")
                (stack[-1].props.__setitem__(k.strip(), v.strip()) if sep
                 else stack[-1].lines.append(entry))
        i += 1
    return [b for r in roots for b in (r.children if r.kind == "module" else [r])]
```

- [x] **Step 4: Prove it on the install** — a `python -c` that imports `food_scan`, walks every `*.txt` under `media/scripts` and prints the counts. Expected, verified 2026-09-10 on 42.20.4: `craftRecipe` **969**, `item` blocks **5105** of which `ItemType = base:food` **722**; `craftRecipe` children `inputs` **969**, `outputs` **958**, `itemMapper` **225**, `overlayMapper` **3**; IO leading tokens `inputs/item` **3355**, `outputs/item` **988**, `inputs/-fluid` **55**. Also check three named blocks: `MakeToast` (`generated/entities/appliances/workstations/entity_toaster_craftRecipe.txt:3`) has `props["time"] == "20"` and children `inputs`/`outputs` with one line each; `MakePizza` (`generated/recipes/recipes_cooking.txt:509`) has 10 input lines and `outputs.lines == ["item 1 Base.PizzaRecipe"]`; `OpenBagOfFrozenFood` (`:41`) has an `itemMapper` child named `foodType` whose `props` hold the four `Base.X = Base.Frozen_X` pairs.
- [x] **Step 5:** `python -m pytest tools/tests -q` → still green (14 tests before this slice adds any). Commit `Slice 06: shared script block parser` (skip if `food_scan.py` needed no change).

### Task 2: `craftRecipe` scanner → `data/recipes.json` + `data/recipes.csv`

**Files:** Create `tools/recipe_scan.py`, `tools/tests/test_recipe_scan.py`, `data/recipes.json`, `data/recipes.csv`.

**Format, verified on the install 2026-09-10** (reproduce this table in the notes doc, Ev C):

| Fact | Value |
|---|---|
| where `craftRecipe` blocks live | 42 files in `media/scripts/generated/recipes/`, 32 more under `media/scripts/generated/entities/*/{craftRecipes,cratRecipes,workstations}/` — note the shipped typo `cratRecipes`. Walk the tree; do not hardcode directories |
| the 10 blocks with no `outputs` | all in `recipes_fixing.txt` / `recipes_gasmasks.txt` (`SharpenBladeWithGrindstone`, `FixSaw`, the gas-mask filter swaps) |
| top-level keys | `time` 969, `Tags` 969, `category` 935, `timedAction` 889, `xpAward` 560, `SkillRequired` 458, `NeedToBeLearn` 385, `AutoLearnAll` 160, `OnCreate` 146, `AutoLearnAny` 126, `AllowBatchCraft` 112, `MetaRecipe` 72, `Tooltip` 38, `overlayStyle` 34, `OnTest` 20, `recipeGroup` 9, `Icon` 4, `ResearchSkillLevel` 2, `ResearchAny` 1 |
| IO line grammar | `item <N\|variable[…]> [<Type;Type>]\|tags[<t;t>] [mode:X] [flags[…]] [mappers[…]]`; outputs also `item N Base.Type` (bare) and `item N mapper:<name>` (225 lines); `-fluid <N> [<Fluid>]\|categories[…] [mode:mixture]` (55 lines, never a bare `fluid`, never `energy` in vanilla) |
| `mode:` values | `keep` 1502, `destroy` 244, `mixture` 26 (fluids only) |
| `flags[…]` | `;`-separated; the frequent ones are `MayDegradeLight` 1016, `Prop1` 440, `Prop2` 384, `IsNotDull` 219, `ItemCount` 185, `InheritFoodAge` 46 |
| `itemMapper` | `Result = Source` pairs; the literal key `default` appears 134 times and is not a result type |
| legacy `recipe` blocks | **zero** in the shipped scripts — but `ScriptType.Recipe` still registers the token `recipe` (`zombie/scripting/ScriptType.<clinit> @66–@74 L20`) and `zombie/scripting/objects/Recipe.Load(String,String)` still exists: the loader kept the format, vanilla stopped using it (Q2) |

- [x] **Step 1: Tests first** — `tools/tests/test_recipe_scan.py`, same style as `test_doc_lint.py` (sys.path insert, plain asserts). Fixtures are real blocks quoted from the install:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import recipe_scan

TOASTER = """module Base
{
    craftRecipe MakeToast
    {
        timedAction = Making,
        time = 20,
        category = Cooking,
        Tags = Toaster,
        inputs
        {
            item 1 [Base.BreadSlices] flags[ItemCount],
        }
        outputs
        {
            item 1 Base.Toast,
        }
    }
}"""   # media/scripts/generated/entities/appliances/workstations/entity_toaster_craftRecipe.txt:3

FROZEN = """module Base
{
    craftRecipe OpenBagOfFrozenFood
    {
        timedAction = UnPackSmallBag,
        time = 15,
        Tags = InHandCraft;Cooking;CanBeDoneInDark,
        category = Cooking,
        inputs
        {
            item 1 [Base.Frozen_ChickenNuggets;Base.Frozen_FishFingers] flags[AllowFrozenItem;InheritFoodAge] mappers[foodType],
        }
        outputs
        {
            item 3 mapper:foodType,
        }
        itemMapper foodType
        {
            Base.ChickenNuggets = Base.Frozen_ChickenNuggets,
            Base.FishFingers = Base.Frozen_FishFingers,
        }
    }
}"""   # media/scripts/generated/recipes/recipes_cooking.txt:41, two of its four mapper rows kept

# both lines are from the MakePizza block, recipes_cooking.txt:509
PIZZA_TOOL, PIZZA_FLUID = "item 1 tags[base:bowl] mode:keep", "-fluid 0.5 categories[Water] mode:mixture"

FOOD = {"Base.BreadSlices": {"Calories": 177.0, "Carbohydrates": 33.0, "Lipids": 2.22,     # food.txt:2123
                             "Proteins": 5.9, "HungerChange": -10.0, "ThirstChange": 0.0},
        "Base.Toast":       {"Calories": 177.0, "Carbohydrates": 33.0, "Lipids": 2.22,     # food.txt:6400
                             "Proteins": 5.9, "HungerChange": -8.0, "ThirstChange": 0.0}}

def test_flat_recipe_and_zero_macro_delta():
    """BreadSlices and Toast carry identical macros; only HungerChange differs. Per
    food-item-model.md, cooking changes no nutrition -- the type swap is the whole effect."""
    r = recipe_scan.parse_text(TOASTER, "toaster.txt")[0]
    assert (r["name"], r["time"], r["category"]) == ("MakeToast", 20, "Cooking")
    i, o = r["inputs"][0], r["outputs"][0]
    assert (i["types"], i["amount"], i["flags"], i["consumed"]) == (["Base.BreadSlices"], 1.0, ["ItemCount"], True)
    assert o["types"] == ["Base.Toast"] and o["amount"] == 1.0
    d = recipe_scan.nutrition_delta(r, FOOD)
    assert (d["calories"], d["carbohydrates"], d["lipids"], d["proteins"]) == (0.0, 0.0, 0.0, 0.0)
    assert d["hungerChange"] == 2.0

def test_mapper_output_resolves_to_every_target_and_blocks_the_delta():
    r = recipe_scan.parse_text(FROZEN, "cooking.txt")[0]
    assert r["itemMappers"]["foodType"]["Base.ChickenNuggets"] == "Base.Frozen_ChickenNuggets"
    assert sorted(r["outputs"][0]["types"]) == ["Base.ChickenNuggets", "Base.FishFingers"]
    assert r["outputs"][0]["mapper"] == "foodType" and r["outputs"][0]["amount"] == 3.0
    d = recipe_scan.nutrition_delta(r, FOOD)          # ambiguous input, unresolved outputs
    assert d is None or d.get("reason")

def test_io_line_grammar():
    t, f = recipe_scan.parse_io(PIZZA_TOOL), recipe_scan.parse_io(PIZZA_FLUID)
    assert t["tags"] == ["base:bowl"] and t["mode"] == "keep" and t["consumed"] is False
    assert (f["kind"], f["amount"], f["categories"], f["consumed"]) == ("fluid", 0.5, ["Water"], True)
```

- [x] **Step 2: Write `tools/recipe_scan.py`** — stdlib only, `mod_inventory.py` / `insulation_scan.py` style (module docstring, `main(argv)`, `--root`, `--out-dir`). Shape:
  - `parse_io(line)` → `{kind: "item"|"fluid", amount: float|None, variable: str|None, types: [], tags: [], categories: [], mode: str|None, flags: [], mappers: [], mapper: str|None, consumed: bool, raw: str}`. Bracketed lists split on `;`; a bare trailing token in an output is a single type; a leading `-` marks a consumed fluid; `variable[…]` → `amount=None`. **`consumed = mode != "keep"`** (no mode and `mode:destroy` both consume).
  - `parse_text(text, path)` → recipe dicts: `name`, `module`, `sourceFile`, `sourceLine`, `time` (int), `timedAction`, `category`, `tags`, `skillRequired`, `needToBeLearn`, `autoLearnAll`, `autoLearnAny`, `xpAward`, `onCreate`, `metaRecipe`, `allowBatchCraft`, `tooltip`, `inputs`, `outputs`, `itemMappers` (`{name: {result: source}}`), plus the untouched `props` for anything unlisted. An output `mapper:<name>` resolves to **every key** of that mapper except the literal `default`.
  - `nutrition_delta(recipe, food)` → `{calories, carbohydrates, lipids, proteins, hungerChange, thirstChange}` = Σ(outputs × amount) − Σ(**consumed** item inputs × amount); or `None`/`{"reason": …}` when any consumed item input or any output is not a single type present in `food`, or an amount is variable. Fluids contribute no macros; a recipe with fluid IO still gets its item-side delta plus `fluidIO: true`.
  - `scan(root)` walks every `*.txt` under `media/scripts`. Writer emits the spec's `meta` block: `build "42.20.4 (b0bbce05d5)"`, `generated`, `tool`, `sources` (scripts root + `data/food-items.json` and its meta build), `counts`.
- [x] **Step 3: Generate** — `python tools/recipe_scan.py --out-dir data`. Expected counts, verified while writing this plan: `craftRecipes` **969**, files **74**, distinct output item types **1693** of which **262** resolve to food items, recipes touching ≥ 1 food item **116**, recipes with a fully food-resolvable delta **31**, of those with a non-zero calorie delta **23**. A different number is a finding, not a failure: re-derive it, state both figures in the notes doc, never accept it silently.
- [x] **Step 4: Spot-check by hand** — print the `MakeToast`, `MakePizza`, `OpenBagOfFrozenFood` and `MillCornflour` rows. Expected: `MakeToast` all-zero macros with `hungerChange +2.0`; `MillCornflour` (`Base.CornSeed` → `Base.Cornflour2`) `calories −496.0`; `MakePizza` `delta = None` with a `reason` naming its `tags[…]` and `[*]` inputs.
- [x] **Step 5:** `python -m pytest tools/tests -q` green; commit `Slice 06: craftRecipe scanner and dataset`.

### Task 3: Evolved recipes, aliases and the `ReplaceOn*` links

**Files:** Modify `tools/recipe_scan.py`, `tools/tests/test_recipe_scan.py`; Create `data/evolved-recipes.json`, `data/evolved-recipes.csv`.

**Resolution rules, verified on the jar and the install 2026-09-10** (Ev C):

- **63** `evolvedrecipe` blocks: 62 in `media/scripts/generated/evolvedrecipes.txt`, 1 (`AddBaitToChum`) in `generated/recipes/recipes_fishing_evolvedrecipe.txt`. Keys and counts: `docs/superpowers/plans/02-notes.md` Q5 (`BaseItem`/`Name`/`ResultItem`/`MaxItems`/`Template` on all; `Cookable` 44, `CanAddSpicesEmpty` 42, `AddIngredientIfCooked` 37, `MinimumWater` 20, `AddIngredientSound` 11; `IsHidden` and `AllowFrozenItem` loader-only, 0 uses).
- **374** items carry `EvolvedRecipe` (372 in `food.txt`, 2 in `drainable.txt`), value `Name:use[|Cooked]` joined by `;` (60 `|Cooked` suffixes in `food.txt`).
- `zombie/scripting/objects/Item.OnScriptsLoaded(ScriptLoadMode)` attaches the item through **two** arms: (a) exact-name lookup `ScriptManager.getEvolvedRecipe(key)` `@43–@59 L3033–L3035`, and (b) every recipe whose `template` **`equalsIgnoreCase`** the key `@122–@140 L3039`. The template arm is case-insensitive; the name arm is a map lookup. Parse-time aliases applied earlier in `Item.DoParam`: `RicePot`/`RicePan` → `Rice`, `PastaPot`/`PastaPan` → `Pasta`, `Roasted Vegetables` → `Stir fry` (`food-item-model.md` § Key reference, `EvolvedRecipe` row) — vanilla really uses them (`RicePan` ×3, `RicePot` ×1, `Roasted Vegetables` ×1).
- The one vanilla case that discriminates the arms: `item Cinnamon` (`food.txt:13665`) declares `ConeIceCream:1` while the recipe and its template are `ConeIcecream` (`evolvedrecipes.txt:603`, `:610`). It joins **only** through the case-insensitive template arm; a case-sensitive expansion loses exactly that pair and reports a false "unmatched key".
- With those rules: **6902** (recipe, ingredient) pairs, **0** unmatched keys; `Salad` and `SaladClay` take **187** ingredients each.

- [x] **Step 1: Tests first.** The expected values are the *measured* Salad rows of `docs/vanilla/food-item-model.md` § Evolved recipes (run `exp02-20260910-030433`, dish 24.999998 kcal at Cooking 0 and 29.166666 at Cooking 10), reproduced by applying the cited formula to the script values — green means the code applies the documented rule and nothing else:

```python
LETTUCE = {"HungerChange": -15.0, "Calories": 54.0, "Carbohydrates": 10.33,
           "Lipids": 0.54, "Proteins": 4.9}    # food.txt:14467, EvolvedRecipe "... Salad:5 ..."
TOMATO  = {"HungerChange": -12.0, "Calories": 14.0, "Carbohydrates": 3.5,
           "Lipids": 0.2, "Proteins": 1.3}     # food.txt:91,    EvolvedRecipe "... Salad:6 ..."

def test_contribution_cooking_0():
    c, t = recipe_scan.contribution(LETTUCE, 5, 0), recipe_scan.contribution(TOMATO, 6, 0)
    assert round(c["share"], 6) == 0.333333 and t["share"] == 0.5 and c["skillBonus"] == 1.0
    assert round(c["calories"], 6) == 18.0 and round(t["calories"], 6) == 7.0
    assert round(c["calories"] + t["calories"], 4) == 25.0
    assert round(c["carbohydrates"] + t["carbohydrates"], 6) == 5.193333
    assert round(c["lipids"] + t["lipids"], 6) == 0.28
    assert round(c["proteins"] + t["proteins"], 6) == 2.283333

def test_contribution_cooking_10():
    c, t = recipe_scan.contribution(LETTUCE, 5, 10), recipe_scan.contribution(TOMATO, 6, 10)
    assert round(c["share"], 6) == 0.233333 and round(t["share"], 6) == 0.35
    assert round(c["skillBonus"], 4) == 1.6667
    assert round(c["calories"] + t["calories"], 4) == 29.1667

def test_key_resolution():
    assert recipe_scan.parse_evolved_key("Sandwich:5|Cooked;Salad:10") == [("Sandwich", 5, True), ("Salad", 10, False)]
    assert (recipe_scan.alias("RicePan"), recipe_scan.alias("Roasted Vegetables")) == ("Rice", "Stir fry")
    assert recipe_scan.resolve_recipes("ConeIceCream", {"ConeIcecream": {"Template": "ConeIcecream"}}) == ["ConeIcecream"]
```

- [x] **Step 2: Implement** `alias(key)`, `parse_evolved_key(value)`, `resolve_recipes(key, recipes)` (exact name **plus** case-insensitive template, deduped, sorted), and `contribution` applying the summation **verbatim** as cited:

```python
def contribution(item, use, level):
    """One ingredient's contribution to a dish. Formula: docs/vanilla/food-item-model.md
    § Evolved recipes (EvolvedRecipe.addItem @518-@1294 L333-L415) -- applied here, never
    re-derived. Ignores the rotten branch (Cooking >= 7) and the spice branch (a Spice
    ingredient transfers no hunger and no macros); both are flagged on the row instead."""
    hunger = use / 100.0
    after = hunger * (1.0 - 0.03 * level)
    hung = abs((item.get("HungerChange") or 0.0) / 100.0)
    share = min(abs(after / hung), 1.0) if hung else 0.0
    bonus = 1.0 + level / 15.0
    out = {"use": use, "hunger": hunger, "hungerAfterSkill": after,
           "share": share, "skillBonus": bonus}
    for src, dst in (("Calories", "calories"), ("Carbohydrates", "carbohydrates"),
                     ("Lipids", "lipids"), ("Proteins", "proteins"),
                     ("ThirstChange", "thirstChange")):
        out[dst] = (item.get(src) or 0.0) * bonus * share
    return out
```

  A `Spice = true` ingredient gets `share = 0`, `spice: true` and a note pointing at the spice branch; an ingredient whose `HungerChange` is 0 gets `share = 0` and `reason: "no hunger"`.
- [x] **Step 3: `data/evolved-recipes.json`** — `meta` + `recipes: [{name, sourceFile, sourceLine, baseItem, resultItem, template, maxItems, cookable, canAddSpicesEmpty, addIngredientIfCooked, minimumWater, ingredients: [{item, use, requiresCooked, spice, resolvedVia: "name"|"template"|"both", at0: {…}, at10: {…}}]}]` + `unmatchedKeys: []`. `data/evolved-recipes.csv`: one row per (recipe, ingredient) — `recipe, resultItem, item, use, requiresCooked, spice, share0, kcal0, carbs0, lipids0, proteins0, share10, kcal10`.
- [x] **Step 4: `ReplaceOn*` links** — add a `replacements` array to `data/recipes.json`: `{from, to, trigger: "cooked"|"rotten", delta: {…}|null}` for every food item carrying `ReplaceOnCooked` (a `;`-list) or `ReplaceOnRotten`. Expected from the install: **3** cooked links (`BreadSlices → Base.Toast` `food.txt:2132`, `→ Base.Baguette` `:2816`, `→ Base.Pancakes` `:10914`) and **8** rotten links (`:599` `SugarBeetSugarPot`, then `:12425`, `:12464`, `:12486`, `:12539`, `:12561`, `:12582`, `:12604` — the ice-cream melts). Semantics for the doc, from `food-item-model.md` § Cooking / § Key reference: `ReplaceOnCooked` fires on the cook transition **and only if not rotten** — each name is `AddItem`-ed with `copyConditionStatesFrom(this)`, the original is removed and `Food.update` **returns**, so the item is replaced and **never flagged cooked**; `ReplaceOnRotten` makes `updateRotting` age the item every tick and, once rotten, create the replacement, copy `age` + condition states and destroy the original — and `updateRotting` returns immediately on any MP client, so that swap is server-only.
- [x] **Step 5:** regenerate both datasets, `pytest` green, commit `Slice 06: evolved recipes and replacement links`.

### Task 4: Harness cross-check on the live server

**Files:** Create `testing/PZTestKit/PZTestKit/42/media/lua/server/PZTestKit_Server_Recipes.lua`, `testing/experiments/s06_recipes.py`.

A new file rather than an edit to `PZTestKit_Server.lua`, for the reason slice 03 used `PZTestKit_Client_Body.lua`: no collision with a parallel slice, and `PZTestKit_Server.lua` sorts before it, so `TK` is loaded first. Harness Lua needs no re-provisioning (the fixture excludes `mods/`).

- [x] **Step 1: The commands**

```lua
-- Slice 06: script-inventory counts read off ScriptManager, server side.
local function get(o, g, ...)                    -- nil-safe TK.call; preserves a false result
    if not o then return nil end
    local ok, v = TK.call(o, g, ...)
    if ok then return v end
    return nil
end
local function label(o)
    return tostring(get(o, "getFullName") or get(o, "getName") or get(o, "getFullType") or o)
end
local function collect(l)                       -- java List -> { names }, count
    local out, n = {}, get(l, "size") or 0
    for i = 0, n - 1 do local v = get(l, "get", i); if v then out[#out + 1] = label(v) end end
    return out, n
end
local function fields(o, getters)                -- run each getter, skip the ones Kahlua refuses
    local t = {}
    for _, g in ipairs(getters) do local v = get(o, g); if v ~= nil then t[g] = v end end
    return t
end

TK.register("recipes.count", function()
    local sm = getScriptManager()
    return { craft   = get(get(sm, "getAllCraftRecipes"), "size"),
             evolved = get(get(sm, "getAllEvolvedRecipesList"), "size"),
             legacy  = get(get(sm, "getAllRecipes"), "size"),
             unique  = get(get(sm, "getAllUniqueRecipes"), "size") }
end)

TK.register("recipes.evolved", function(argv)
    local r = get(getScriptManager(), "getEvolvedRecipe", argv[1])
    if not r then return "no evolved recipe " .. tostring(argv[1]) end
    local out = fields(r, { "getBaseItem", "getResultItem", "getMaxItems", "isCookable", "getMinimumWater" })
    out.name = argv[1]
    out.items, out.ingredientCount = collect(get(r, "getPossibleItems"))
    return out
end)

TK.register("recipes.craft", function(argv)
    local r = get(getScriptManager(), "getCraftRecipe", argv[1])
    if not r then return "no craft recipe " .. tostring(argv[1]) end
    local out = fields(r, { "getCategory", "getTime", "getInputCount", "getOutputCount" })
    out.name, out.outputs = argv[1], {}
    local outs = get(r, "getOutputs")
    for i = 0, (get(outs, "size") or 0) - 1 do
        local o = get(outs, "get", i)
        if o then
            out.outputs[#out.outputs + 1] = { amount = get(o, "getIntAmount"),
                                              items = collect(get(o, "getPossibleResultItems")) }
        end
    end
    return out
end)
TK.log("recipe commands loaded")
```

  `getTime` is overloaded (`()I` and `(IsoGameCharacter)I`). If Kahlua picks the wrong one and errors, drop it from that getter list and record the limitation in the notes doc — no acceptance depends on it.
- [x] **Step 2: The driver** — `testing/experiments/s06_recipes.py` on `_common.py`, one artifact `testing/artifacts/exp06-<stamp>/recipes.json`, ~2 min, one session, `python testing/pzt doctor` first. Phases: (a) `recipes.count`; (b) `recipes.evolved` for `Salad`, `SaladClay`, `ConeIcecream`, `Soup`, `AddBaitToChum`; (c) `recipes.craft` for ten recipes taken from `data/recipes.json` — `MakeToast`, `MakePizza`, `OpenBagOfFrozenFood`, `OpenEggCarton`, `MakeMilkFromPowderBucket`, `PutEggsInCarton`, `MillCornflour`, `MillSunflowerSeeds`, `GrindCornmeal`, and the first row in the file whose outputs resolve to a single food type; (d) compare each against the scanned row in Python and record `match: true|false` plus the differing fields.
- [x] **Step 3: Read the results.** Expected: `craft 969`, `evolved 63`, `legacy 0` (Q2 measured); `recipes.evolved Salad` and `SaladClay` → `ingredientCount 187` each; `ConeIcecream`'s item list **contains `Cinnamon`** (Q3 — the case-insensitive template arm, measured). Any mismatch is the finding: diff the two name sets in Python, name the missing/extra blocks, fix the scanner if the game is right.
- [x] **Step 4:** add the three commands to the server list in `docs/testing/README.md`; commit `Slice 06: recipes.count harness cross-check`.

### Task 5: Notes doc, ledgers, close

**Files:** Create `docs/vanilla/recipes-dataset-notes.md`; Modify `data/README.md`, `tools/README.md`, `docs/vanilla/README.md`, `docs/testing/README.md`, `docs/progress.md`, `docs/decisions.md`.

- [x] **Step 1: The doc**, house skeleton — header `Verified against: 42.20.4 (b0bbce05d5)` + date + slice; five-line summary; **Model** (Task 2's format table and Task 3's resolution rules, every table row graded, the summation *cited* to `food-item-model.md`, never restated as a derivation); **Code map** (`ScriptManager.getAllCraftRecipes` / `getAllEvolvedRecipesList` / `getAllRecipes`, `Item.OnScriptsLoaded @122–@140 L3039`, `EvolvedRecipe.addItem`, `Food.update`'s `ReplaceOnCooked` branch, `Food.updateRotting`); **Cooking deltas** (the zero-delta result with `MakeToast` worked through; the 3 + 8 `ReplaceOn*` rows; the 23 non-zero craft deltas, largest first); **MP behaviour** (the dataset is not sided — the same `ScriptManager` parses the same files on both — but the *effects* are: `updateRotting` and therefore every `ReplaceOnRotten` swap is server-only (`Food.updateRotting @13–@19 L658-659`), and the Cooking perk level that scales the evolved summation is owned by the server, so a client-side perk write silently runs the recipe at the server's level (`food-item-model.md` § MP behaviour, M `exp02-20260910-030433`)); **Discrepancies**; **Open questions**; **Sources** (script paths with line numbers, the jar cites, the artifact id).
- [x] **Step 2: Document the data** — extend `data/README.md` with every column of both CSVs and the top-level shape of both JSONs; replace the `evolved_recipes.py` line under "Planned (P4)" in `tools/README.md` with the real `recipe_scan.py` entry (invocation, outputs, that it imports `food_scan`'s parser); add the notes doc to `docs/vanilla/README.md`.
- [x] **Step 3: Acceptance** — run every check below and paste the outputs into this plan file under a new `## Acceptance results` heading.
- [x] **Step 4: Ledgers and push** — see Done protocol; commit `Slice 06: recipes dataset notes` and push.

## Deliverables

- `tools/recipe_scan.py`, `tools/tests/test_recipe_scan.py` (± in-place extensions to `parse_script` in `tools/food_scan.py`)
- `data/recipes.json`, `data/recipes.csv`, `data/evolved-recipes.json`, `data/evolved-recipes.csv`
- `testing/PZTestKit/.../server/PZTestKit_Server_Recipes.lua`; `testing/experiments/s06_recipes.py`; artifact `testing/artifacts/exp06-*/recipes.json`
- `docs/vanilla/recipes-dataset-notes.md`; `data/README.md`, `tools/README.md`, `docs/vanilla/README.md`, `docs/testing/README.md` updates

## Acceptance checks

1. `python tools/recipe_scan.py --out-dir data` writes all four data files, exits 0, and reports `craftRecipes 969`, `evolvedRecipes 63`, `pairs 6902`, `unmatchedKeys 0` — or explains each deviation in the notes doc.
2. Live cross-check: `recipes.count` returns `craft 969`, `evolved 63`, `legacy 0`, matching the scan; `recipes.evolved Salad` and `SaladClay` return `ingredientCount 187`, matching the Python expansion; the ten `recipes.craft` spot-checks match the scanned rows field for field.
3. Every `craftRecipe` output type that appears as an `item` block in `media/scripts/generated/items/food.txt` resolves to a `data/food-items.json` key — the scanner asserts this and lists any that do not (expected: none).
4. `python -m pytest tools/tests -q` green (14 existing + the new cases).
5. `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references` → 0 findings.
6. `python testing/pzt run --hold 5` → PASS (the new harness file loads with no Lua error).

## Expected decision points (defaults)

- **`parse_script` lacks something the recipe files need** (IO `lines`, a same-line brace header, a comment) → extend it in place with a test, leaving the item path's behaviour and tests intact. Do not write a second parser and do not refactor slice 05's item path.
- **A `data/food-items.json` field name differs** → map it in `FOOD_FIELDS` and carry on (ledger row). A field that is absent → the dependent output is `null` with a `reason`, never a guess.
- **Scanner counts differ from this plan's verified figures** → the live `recipes.count` is the arbiter; fix the scanner, and record both numbers and the cause in the notes doc.
- **A delta cannot be computed** (`tags[…]` input, multi-type input, `[*]` wildcard, variable amount, mapper output, unresolved type) → `delta: null` with a machine-readable `reason`; never pick a representative item.
- **Fluid inputs** (55 lines) → recorded verbatim, excluded from the macro delta, `fluidIO: true` on the row, stated as a limitation in the doc. Do not model fluid nutrition here — that is slice 05's fluids decision, and 06 does not depend on it.
- **Rotten and spice branches** of the evolved summation → not modelled per row; flagged (`spice: true`, and a doc line for the rotten branch's Cooking ≥ 7 gate) and cited.
- **The live slot is occupied** by another slice → do Tasks 1–3 and Task 5's writing first; Task 4 is the only step needing the server, and the datasets are complete without it (its rows stay ungraded until it runs).
- **`recipes.evolved ConeIcecream` does not list `Cinnamon`** → then something other than the template arm matched, or nothing did: re-read `Item.OnScriptsLoaded @43–@140`, correct § Model, and let the measurement win over this plan's reading.

## Done protocol

- `docs/progress.md`: 06 → `done` (date, commit range, one-line outcome) + ripples — the two datasets are the item pass's input for slices 12/14; the `Template` arm is case-insensitive; cooking's macro delta is zero in the data, so any cooking *value* the mod wants has to come from a type change or from new mechanics.
- `docs/decisions.md`: one row per default taken (separate tool importing `food_scan` vs a module inside it; `consumed = mode != "keep"`; fluids excluded from deltas; a non-identity `FOOD_FIELDS` mapping if there was one).
- `docs/testing/README.md`: the three new server commands in the inventory.
- Commit (`Slice 06: …`, no attribution trailer) and push.

## Acceptance results (2026-09-10)

Every step above ran and is ticked, with the two exceptions named at the end. Seven commits:
`ab26d41` (craftRecipe scanner + dataset), `21fa79d` (`recipes.count` / `recipes.evolved` /
`recipes.craft` and the live cross-check), `c6ef7f2` (evolved recipes, the `replacements` array),
`3c16632` (the `item.use` per-use probe), `6694568` (scanner fixes: input amounts, sub-lines,
join misses, the hunger clamp), `d94f0d9` (evolved fixes: dried-food thirst, spice hunger), plus
this task's doc commit. Two live sessions produced committed evidence:
`exp06-20260910-112726` and `exp06b-20260910-120123`.

1. **`python tools/recipe_scan.py --out-dir data` → exit 0, four files, counts as predicted.**
   Verbatim:

   ```
   craftRecipes 969 in 74 files, 0 legacy recipe blocks, 225 itemMappers
   1693 distinct output item types, 262 of them food items; 375 recipes touch a food item
   31 recipes carry a nutrition delta, 15 of them non-zero in calories
   17 splits (delta 0 by construction), 55 input sub-lines attached, 0 food join misses
   969 recipes, 37 columns -> data\recipes.csv
   969 recipes -> data\recipes.json
   63 evolvedRecipes, 374 carriers, 6902 key->recipe joins, 0 unmatched keys
   6881 ingredient rows (21 duplicate joins collapsed), 2522 spices -> data\evolved-recipes.csv
   59 rows hunger-clamped, 27 dried-food rows with their thirst line skipped
   163 ReplaceOn* links (3 cooked, 8 rotten, 110 use, 42 deplete) -> data\recipes.json
   ```

   `craftRecipes` **969**, `evolvedRecipes` **63**, `pairs` **6902**, `unmatchedKeys` **0** — all
   four exactly as this plan predicted. The doc task re-ran the scanner into a scratch directory
   rather than over `data/`, and all four outputs are **byte-identical** to the committed files
   (`cmp`), so the committed bytes are this run's. Three other figures in this plan did move and
   each is a Discrepancies row in the notes doc: 116 → **375** recipes touching a food item, 23 →
   **15** non-zero calorie deltas (+ 5 splits + 3 absent-on-every-side, which reconstructs 23),
   and "10 recipes with no outputs" → **11 + 26**.
2. **Live cross-check: counts yes, spot checks yes, and the plan's 187 was wrong.**
   `recipes.count` answered **craft 969 / evolved 63 / legacy 0** (+ `unique 0`, recorded and
   uncompared), equal to the scan and to this plan. `recipes.evolved Salad` and `SaladClay`
   answered **189**, not 187: the plan's figure counts `items/food.txt` only and omits
   `Base.Vinegar2` / `Base.Vinegar_Jug`, the two drainables its own "374 carriers = 372 + 2" line
   names. The dataset agrees with the **game** (189 / 189), and each of the five live ingredient
   lists is **set-equal** to the dataset's — 0 extra, 0 missing, both directions, on `Salad`,
   `SaladClay`, `ConeIcecream` (56, `Cinnamon` present — Q3's case-insensitive template arm),
   `Soup` (193) and `AddBaitToChum` (42). The ten `recipes.craft` spot checks compared **77
   fields, 75 matched** at run time; both misses are the one field `inputCount`
   (`MakePizza` 10 vs 9, `MakeMilkFromPowderBucket` 3 vs 2), which is the loader attaching a
   `-fluid` sub-line to the preceding input — the artifact's own `top_level_matches: true` rows
   said so at the time, the scanner adopted the loader's model in `6694568`, and the same
   comparison replayed offline against the artifact is now **10/10 recipes, 77/77 fields**.
   Artifact `testing/artifacts/exp06-20260910-112726/recipes.json`, 89.1 s, `server_errors []`,
   doctor all-`ok`, no world change.
3. **Every `items/food.txt` output type resolves to a `data/food-items.json` key.**
   `meta.foodJoinMisses` is `[]` and `meta.counts.foodJoinMisses` is **0** over the 1 693 distinct
   output types — the scanner collects the 722 ids that file defines and asserts the join in
   `test_real_install_counts`. Expected none, found none.
4. **`python -m pytest tools/tests -q` → `119 passed in 2.84s`.** 60 pre-existing (14 from before
   slice 05 plus slice 05's 46, all untouched) and **59** in `tools/tests/test_recipe_scan.py`;
   none skipped, so every install-gated test really ran against the game scripts and both
   datasets.
5. **`python tools/doc_lint.py docs/vanilla docs/modding docs/testing references` →
   `0 finding(s)`**, run on the tree with `docs/vanilla/recipes-dataset-notes.md` in place and
   with the § Evolved recipes hunger-clamp row added to `docs/vanilla/food-item-model.md`.
6. **`python testing/pzt run --hold 5` → met by the two live runs, not re-run here.** The doc task
   does not boot the game. `testing/` has not been touched since `3c16632`, so the harness in the
   tree is byte-for-byte the one both sessions loaded: `exp06-20260910-112726` booted
   `server/PZTestKit_Server_Recipes.lua` with all three recipe commands answering on fifteen
   probes, and `exp06b-20260910-120123` booted `PZTestKit_Server.lua` carrying `item.use` — both
   with `server_errors []`, `client_quit rc=0`, `server_stopped rc=0` and `pzt doctor` all-`ok`
   recorded in the artifact. Both artifacts are recorded as **skew-free** in
   `testing/artifacts/README.md` (script, command and artifact in one commit). That is the same
   load path `pzt run --hold 5` exercises; a dedicated smoke run remains the cheaper proof if the
   controller wants one.

**Two plan expectations moved, and one measurement was added beyond the plan.** (a) The plan's
"`item N`" was read as N items; it is N **uses** — for a `Food`, N raw `HungerChange` points. That
changed eight of the 31 resolvable deltas (`ScoopIceCream` −16 345 → **−105**, `MakeMeatPatty`
−11 388 → **+312**, five `InheritFood` splits to 0) and is the reason `data/recipes.json` gained
`amountIsItemCount`, `amountUses`, `subLines`, `split`, `destroyWaste` and the delta's `notes`.
(b) The evolved summation needed three branches the plan's verbatim block omits — the hunger
clamp (59 rows), the spice return (2 522 rows) and the `DRIED_FOOD` thirst skip (27 rows). (c)
Task 4b (`item.use`, `exp06b-20260910-120123`) was added to measure (a) rather than ship it as a
jar reading: 96 of 96 fields matched, `Base.Icecream` at 10 of 30 uses reading
`1680 → 1120 kcal` and `−0.30 → −0.20` hunger.

**What is not in this task's commit.** Step 4's `git push` and the `docs/progress.md` half of the
Done protocol — the board row, its commit range and the slice-07/12/14 ripples — are the
controller's close-out. Step 4's `docs/decisions.md` half landed here (eleven slice-06 rows), as did
`docs/testing/README.md`'s inventory, which Tasks 4 and 4b had already written in full (the three
recipe commands, `item.use`, both experiment drivers) and which this task therefore left
unchanged.
