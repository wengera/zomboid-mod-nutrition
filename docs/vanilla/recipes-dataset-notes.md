# Recipes dataset — the vanilla craft/evolved recipe scan and its live cross-check

**Verified against: 42.20.4 (`b0bbce05d5`)** · 2026-09-10 · slice 06 (P4b).
Evidence grades: **C** read from bytecode/Lua/shipped scripts (`file:line`, or
`Class.method @addr Lline` for the jar), **M** measured on the live dedicated server (run id +
artifact link), **W** wiki mirror (secondary — none is used here).
`C (arith.)` = arithmetic on C constants, shown inline — every `delta` on a `craftRecipe` row,
every `at0` / `at10` contribution on an evolved-recipe ingredient and every `replacements[].delta`
is that grade, resting on one input-amount rule that is itself **M**.
This document is about the **datasets**: what `data/recipes.{json,csv}` and
`data/evolved-recipes.{json,csv}` contain, how the scanner decides, and how far the numbers were
checked against the running game. The **column authority is
[`data/README.md`](../../data/README.md)** § recipes and § evolved-recipes — every column, type
and source key is listed there and is not repeated here. The nutrition arithmetic these datasets
*apply* is [food-item-model.md](food-item-model.md) § Evolved recipes and § Cooking, and the 114
script keys are its § Key reference — **cited, never re-derived**. The item rows both datasets
join against are [food-dataset-notes.md](food-dataset-notes.md).

## Summary

1. **969 `craftRecipe` blocks in 74 files, 63 `evolvedrecipe` blocks, 0 legacy `recipe` blocks**,
   built by `tools/recipe_scan.py` (which imports slice 05's parser) into two JSON + two CSV
   files. All three counts were answered identically by the game's own `ScriptManager` on a live
   server.
2. **An input amount is a count of *uses*, not of items, unless the line carries
   `flags[ItemCount]`** — and for a `Food` one use is one raw `HungerChange` point. `item 10
   [Base.Icecream]` is a third of a tub, not ten tubs. That rule is **measured**: spending 10 of
   an ice-cream tub's 30 uses scaled every macro by `1 − used/currentUses`.
3. **Cooking moves no nutrition; only a *type change* does.** `MakeToast` is all-zero in the four
   macros with `hungerChange +2.0`, all 8 `ReplaceOnRotten` melts conserve every macro, and of the
   3 `ReplaceOnCooked` links none moves a macro. 31 of the 969 crafts resolve to a full macro
   delta and 15 of those are non-zero in calories — every one of them a recipe that changes what
   the item *is*.
4. **The evolved join is the game's own two arms, not a name match.** 374 carrier items write
   2 446 `EvolvedRecipe` key parts, which resolve across the 63 recipes into **6 902** (key part,
   recipe) joins → **6 881 dataset rows**, **0 unmatched keys**, `Salad` and `SaladClay` 189
   ingredients each. The five live ingredient lists match the Python expansion **name for name, in
   both directions**.
5. **Everything in both datasets is C or `C (arith.)`** — every value is a line in a shipped file
   and every record names its `sourceFile:sourceLine`. The measured layer is two live runs: the
   `ScriptManager` cross-check with ten field-for-field craft spot checks
   (`exp06-20260910-112726`) and the per-use consumption probe, 96 of 96 fields matched
   (`exp06b-20260910-120123`).

---

## Model

### The seven questions, answered

| # | Question (plan 06) | Answer | Ev |
|---|---|---|---|
| Q1 | What exactly is a B42 `craftRecipe` block — top-level keys, sub-blocks, IO grammar — and which files hold them? | § `craftRecipe` — the format and § The IO line grammar below; 969 blocks in **74** files (42 under `generated/recipes/`, 32 under `generated/entities/*/{craftRecipes,cratRecipes,workstations}/` — note the shipped typo `cratRecipes`) | C — `meta.sources.files`, `meta.counts` |
| Q2 | Do legacy `recipe` blocks still exist in 42.20.4 — in the scripts, and in the loader? | **Not in the scripts, yes in the loader.** Zero `recipe` blocks ship; `ScriptType` still registers the token (`zombie/scripting/ScriptType.<clinit> @66–@74 L20`) and `zombie/scripting/objects/Recipe.Load(String,String)` still exists — the format was kept, vanilla stopped using it | C; **M** live `getAllRecipes()` size **0** — `exp06-20260910-112726` ([`recipes.json`](../../testing/artifacts/exp06-20260910-112726/recipes.json)) |
| Q3 | How does an item's `EvolvedRecipe` key (`Name:use`, optionally suffixed `Cooked`) reach a recipe, and is the match case-sensitive? | Two arms — an exact-name map lookup **plus** every recipe whose `Template` `equalsIgnoreCase` the key, with five parse-time aliases applied first. The template arm is case-insensitive and it is the only arm that matches on 42.20.4's one miscased key. § Resolution rules | C — `Item.OnScriptsLoaded @43–@59 L3033–L3035`, `@122–@140 L3039`; **M** `ConeIcecream` lists `Cinnamon` — `exp06-20260910-112726` |
| Q4 | For every transformation that changes an item's type, what is the macro/hunger delta — and does the data confirm plain cooking is a zero delta? | **It confirms it.** § Cooking deltas: `MakeToast` 0/0/0/0 with hunger +2.0; the 8 rotten links conserve every macro; the 3 cooked links move no macro (one moves thirst, by absence). The 31 resolvable craft deltas are tabulated there | C (arith.) — `data/recipes.json` `delta` / `replacements[].delta` |
| Q5 | What does one unit of each ingredient contribute to its dish at Cooking 0 and Cooking 10? | `data/evolved-recipes.json` carries `at0` and `at10` per ingredient row — 6 881 rows × 2 — applying the cited summation. § The evolved summation | C (arith.); the formula itself C+M — [food-item-model.md](food-item-model.md) § Evolved recipes (`exp02-20260910-030433`) |
| Q6 | Do the scanned counts equal what the game loaded, and does the Python expansion equal `EvolvedRecipe.getPossibleItems()` per recipe? | **Yes to both.** craft 969 / evolved 63 / legacy 0 live, equal to the scan; ten craft recipes compared field for field — 77 raw rows, of which **10 are the live-vs-live `outputListSize` check**, so **67 dataset fields, 65 matched at run time** (the two misses are one field, § Discrepancies row 3) and **67 of 67** replayed against the fixed scanner; the five evolved lists are **set-equal** to the dataset's ingredient lists, 0 extra and 0 missing on either side (computed offline against the artifact — see § Resolution rules) | **M** `exp06-20260910-112726` ([`recipes.json`](../../testing/artifacts/exp06-20260910-112726/recipes.json)) |
| Q7 | Is any of this per-side? | **The data is not; three of its effects are.** § MP behaviour | C; **M** for the perk level — [food-item-model.md](food-item-model.md) § MP behaviour (`exp02-20260910-030433`) |

### `craftRecipe` — the format

Counts are **craftRecipe-scoped**: 202 further `inputs` blocks in the tree belong to a
`component CraftRecipe` — an entity's own build recipe (`entities/admin/entity_piano.txt:38`) —
and are censused separately as `meta.counts.componentCraftRecipes`, not scanned into this dataset
(§ Discrepancies row 2).

| Fact | Value | Ev |
|---|---|---|
| where the blocks live | **74** files: 42 in `media/scripts/generated/recipes/`, 32 under `generated/entities/*/{craftRecipes,cratRecipes,workstations}/`. The scanner walks all **1 004** `media/scripts/**/*.txt` and does not hardcode directories | C — `meta.sources.files`, `meta.counts.scriptFiles` |
| top-level keys, by how many of the 969 blocks write them | `time` 969, `Tags` 969, `category` 935, `timedAction` 889, `xpAward` 560, `SkillRequired` 458, `NeedToBeLearn` 385, `AutoLearnAll` 160, `OnCreate` 146, `AutoLearnAny` 126, `AllowBatchCraft` 112, `MetaRecipe` 72, `Tooltip` 38 — each a declared column — then `overlayStyle` 34, `OnTest` 20, `recipeGroup` 9, `Icon` 4, `ResearchSkillLevel` 2, `ResearchAny` 1, which land untyped in the record's `props` | C — counted off the 969 records |
| sub-blocks | `inputs` 969, `outputs` **958**, `itemMapper` 225, `overlayMapper` 3 | C |
| recipes with no outputs | **11 + 26 = 37**: 11 ship no `outputs` block at all and 26 ship an empty one. All 37 mutate an input through `OnCreate` instead of yielding an item, and all 37 read `deltaReason: "no-outputs"` | C — `meta.counts.recipesWithoutOutputs` / `…WithEmptyOutputs` (§ Discrepancies row 1) |
| IO lines | 3 355 `inputs/item` + **55** `inputs/-fluid` = 3 410 input lines; 988 `outputs/item` lines. No vanilla line is a bare `fluid` or an `energy` | C |
| `mode:` values | `keep` **1 366**, `destroy` **242**, `mixture` **26** (fluid lines only) | C — § Discrepancies row 2 |
| `flags[…]`, `;`-separated | `MayDegradeLight` 975, `Prop2` 384, `Prop1` 320, `IsNotDull` 214, **`ItemCount` 182**, **`InheritFoodAge` 46**, **`InheritFood` 17** — the last three are the only ones that change what a line costs or produces | C |
| `itemMapper` | `Result = Source` pairs, **1 599** lines over 225 mappers; **134** mappers also write the literal key `default`, which is *not* a result type. 56 mappers name one result twice (`RemoveFurMapper` maps 16 fur sources onto 3 leathers), so the record carries the lossless `itemMapperPairs` beside the contract dict `itemMappers[name][result] = source` | C — § Discrepancies row 6 |
| `overlayMapper` | 3 blocks (`DryLargeLeather`, `DryMediumLeather`, `DrySmallLeather`), each with a `default` and 5 pairs, plus 3 input lines ending in a bare `overlayMapper` token | C |
| `variable[<min>:<max>]` amounts | 66 lines over **33** recipes, all of them drying racks (`entity_Herb_Drying_Rack_craftRecipe.txt` 25, `entity_Drying_Rack_craftRecipe.txt` 8), on both sides of each recipe. The dataset writes `amount: null` + `variable: "1:20"` and refuses the delta | C — § Open questions 3 |
| legacy `recipe` blocks | **0** shipped, loader intact — Q2 above | C; **M** same run |

### The IO line grammar

```
item <N | variable[<min>:<max>]> [<Type;Type>] | tags[<t;t>] | mapper:<name> | [*]
     [mode:keep|destroy|mixture] [flags[…]] [mappers[…]] [overlayMapper]
-fluid <N> [<Fluid>] | categories[…] [mode:mixture]
```

- A bracketed list splits on `;`; an entry may carry a per-alternative count
  (`2:Base.BurlapPiece`, in `SewFootwrap`'s `item 6 [Base.DenimStrips;…;2:Base.BurlapPiece]`;
  86 such prefixes over 68 distinct pairs). `types` keeps the id and the count stays readable in
  the line's `raw`. Ev C.
- **`consumed = mode != "keep"`** — no `mode:` and `mode:destroy` both consume
  (`ItemUser.UseItem @28 L37-38` skips the reduction only when `keep` is true). Ev C.
- A leading `-` (or `+`) marks a fluid **sub-line**, which the loader attaches to the *preceding*
  input rather than adding to `inputs` (`CraftRecipe.LoadIO @218–@317`). The dataset nests those
  55 lines as `subLines` of the input above them and publishes `inputCount = len(inputs)` — the
  loader's own `inputs.size()`. Ev C; **M** the counter itself, `exp06-20260910-112726`.
- An output `mapper:<name>` resolves to **every key of that mapper except the literal `default`**.
  One mapper resolves to nothing at all under that rule and is listed in `meta.outputMapperIssues`
  (§ Discrepancies row 6). Ev C.
- Fluid lines are **recorded verbatim and excluded from the macro delta**: a fluid's nutrition is
  per litre and belongs to slice 05's fluid model, not here. 53 recipes carry fluid IO and are
  flagged `fluidIO: true`. Ev C — [food-dataset-notes.md](food-dataset-notes.md) § Per litre, not
  per item.

### The delta rule — what an input amount actually costs

This is the one place the dataset does arithmetic the scripts do not write down, so the rule is
stated in full. `nutrition_delta = Σ(outputs × their own script macros) − Σ(what each consumed
input line really spends)`, per macro, over `calories`, `carbohydrates`, `lipids`, `proteins`,
`hungerChange`, `thirstChange`.

| Line | What N costs | Ev |
|---|---|---|
| `mode:keep` | **nothing.** The line selects and reserves an item, rolls its `MayDegrade*` check and is never reduced (`ItemUser.UseItem @28 L37-38`) | C |
| `flags[ItemCount]` | **N whole items** (`CraftRecipeData.consumeInputFromItems @372 L1089` takes `1f` per item; `processDestroyAndUsedItems @337 L563` spends the item's whole remaining uses) | C |
| a `food` row whose `HungerChange` magnitude exceeds 1, no `ItemCount` | **N ÷ that magnitude, as a fraction of one item.** One use is one raw `HungerChange` point: `Food.getMaxUses @11–@23 L2210–L2214` is `(int) abs(baseHunger × 100)`, and the reduction runs `Food.setCurrentUses @23–@35 L2228–L2233` → `consumeHunger` → `multiplyFoodValues(1 − consumed / abs(hungChange))` | C; **M** `exp06b-20260910-120123` ([`use-probe.json`](../../testing/artifacts/exp06b-20260910-120123/use-probe.json)) |
| a `food` row with no usable `HungerChange` | **N whole items** — `getMaxUses` is `baseHunger == 0 ? 1`, so one use *is* the item. The row's `delta.notes` says so by name (`no-hunger-scale: …`), never silently | C |
| a `drainable` input | **no macros**, with a note: a drainable's uses are `UseDelta` steps of a bar (`consumeInputItemUsesInternal @0–@125 L960–L988`), not nutrition | C |
| `mode:destroy` on a non-`ItemCount` line | the charge is rounded **up to the whole items `RemoveItem` deletes** (`UseItem @260 L66-67`) and the annihilated remainder is published as `delta.destroyWaste`, so both readings — "hunger points moved" and "food removed from the world" — are recoverable. 1 vanilla row rounds up (`UnpackCigarettes`), and its `destroyWaste` is **null**: the row it destroys is the drainable `Base.CigarettePack`, which writes no macro key at all, so there is no macro to have been wasted and a block of six zeroes would read as a measured "0.0 kcal destroyed". `meta.counts.recipesWithDestroyWaste` is therefore **0**; the round-up itself is in that row's `delta.notes` | C |
| an input flagged `InheritFood` | the craft is a **split**: the output takes `1/outputCount` of the *consumed instance's* macros (`createOutputItems @1096–@1143 L1542–L1544` → `Food.copyFoodFromSplit @0–@3 L2704` → `copyNutritionFromRatio @0–@86 L2677–L2685`), so that input and every output drop out of the sum and the delta is 0 by construction. 17 recipes, 8 of them resolvable, all 8 zero in all six macros | C |
| `flags[InheritFoodAge]` | **not** a split — it copies age only (`createOutputItems @1192–@1311 L1550–L1562` → `Food.copyAgeFrom`). `ScoopIceCream` carries it and still costs 560 kcal of ice cream | C |
| an output line | **always an item count** (`createOutputItems @39–@116 L1408–L1418` loops N times), and the result carries its own script macros | C |

**Measured, three items, one session.** `item.use` spent uses on the exact rows this rule is
worked out on and read every `Food.multiplyFoodValues` field on either side of the single setter,
inside one Lua call (`delta.worldAgeHours` 0):

| Item | uses spent | `hungChange` | calories | carbs | lipids | proteins | Ev |
|---|---|---|---|---|---|---|---|
| `Base.Icecream` (`ScoopIceCream`'s `item 10`) | 10 of 30 | −0.30 → **−0.20** | 1680 → **1120** | 180 → **120** | 84 → **56** | 26 → **17.333334** | **M** `exp06b-20260910-120123` ([`use-probe.json`](../../testing/artifacts/exp06b-20260910-120123/use-probe.json)) |
| `Base.MincedMeat` (`MakeMeatPatty`'s `item 40`) | 40 of 40 | −0.40 → **0** | 300 → **0** | 0 | 30 → **0** | 46 → **0** | **M** same run |
| `Base.Cheese` (`MakePizza`'s `item 15`) | 15 of 15 | −0.15 → **0** | 113 → **0** | 0.87 → **0** | 9.33 → **0** | 6.4 → **0** | **M** same run |

96 of 96 compared fields matched, `mismatches []`. Two caveats travel with it: `getMaxUses()` and
`baseHunger` did **not** move, so the denominator is `currentUses` — equal to `maxUses` only while
the item is whole — and two of the three rows are boundary rows, so the *fractional* claim rests
on `Base.Icecream`'s seven independent fields. The **item removal** on depletion
(`UseItem @272 L68-70`) is still a jar reading: `ItemUser` is not exposed to Kahlua
(`LuaManager$Exposer.shouldExpose @6–@14 L2833`), so the probe ran `item:setCurrentUses(cur − used)`
— the exact line `UseItem @28 L37-38` executes — and nothing after it. Ev **M** for the scaling,
**C** for the removal.

**A delta is refused, never guessed.** When any consumed input or any output is not a single
dataset type with per-item nutrition, the record carries `delta: null` and a machine-readable
`deltaReason` naming the offending lines verbatim (`why: raw`, joined by ` ; `). The blocker kinds
are `tags-only`, `multi-type`, `wildcard` (`[*]`), `variable-amount`, `mapper`-shaped outputs,
`no-outputs`, `not-in-dataset`, `no-nutrition` and `fluid-sourced`. 938 of the 969 recipes are
refused for at least one of those reasons; **31 resolve**. Ev C.

**Absence is declared, not summed away.** A resolvable row that writes no line for one macro sums
as `0` and is *named* in `delta.absentMacros` (`"Base.Cornflour2:calories"`), so a zero is always
readable as measured, absent or substituted. Ev C — the same rule
[food-dataset-notes.md](food-dataset-notes.md) § Empty is not zero states for the item dataset.

**Ruling on units.** A delta term is taken only from a row whose `nutrition_basis` is `per_item`
(slice 05's column). A `per_litre` row contributes `fluid-sourced` and an empty basis
`no-nutrition` — the dataset never adds a per-litre number to a per-item one. Ev C.

### Resolution rules — how an item reaches an evolved recipe

`Item.OnScriptsLoaded @0–@234 L3029–L3047` attaches an item's `EvolvedRecipe = <Name>:<use>[|Cooked]`
key through **two** arms, with the parse-time aliases applied first in `Item.DoParam`. Cited, not
re-derived — [food-item-model.md](food-item-model.md) § Evolved recipes and § Key reference.

| Rule | On 42.20.4 | Ev |
|---|---|---|
| **(a) exact name** `ScriptManager.getEvolvedRecipe(key)` `@43–@59 L3033–L3035` | a map lookup, case-**sensitive** | C |
| **(b) every recipe whose `Template` `equalsIgnoreCase` the key** `@122–@140 L3039` | case-**insensitive**, and it does the work: `resolvedVia` is `template` on 4 748 rows, `both` on 2 133 and **`name` on 0**. Five key parts do match by name alone (`Waffles:8` on `Base.DriedApricots`, `Stir fry Griddle Pan:<n>` on the three pumpkins and `Base.Soybeans`), but each of those items also writes another key that reaches the same recipe by template, so every row merges to `both` | C |
| the five aliases (`RicePot`/`RicePan` → `Rice`, `PastaPot`/`PastaPan` → `Pasta`, `Roasted Vegetables` → `Stir fry`) | really used: 5 key parts (`RicePan` ×3, `RicePot` ×1, `Roasted Vegetables` ×1). Unaliased, `RicePan:1` would reach 1 recipe instead of 4. **Never live-checked**: the five `recipes.evolved` probes of `exp06-20260910-112726` are `Salad` / `SaladClay` / `ConeIcecream` / `Soup` / `AddBaitToChum`, none of which is an alias target, so this row rests on `Item.DoParam` alone — § Open questions 9 names the one probe that would settle it | C only |
| the one case that discriminates the arms | `item Cinnamon` (`items/food.txt:13665`) writes `ConeIceCream:1` while the recipe and its template are `ConeIcecream` (`evolvedrecipes.txt:603`, `:610`) — the only miscased key in the install. The row carries `resolvedVia: "template"`; a case-sensitive expansion loses exactly that pair and reports a false unmatched key | C; **M** the live `ConeIcecream` list contains `Cinnamon` / `Base.Cinnamon` — `exp06-20260910-112726` |
| the census | 63 recipes (62 in `evolvedrecipes.txt` + `AddBaitToChum` in `recipes/recipes_fishing_evolvedrecipe.txt`), **374** carriers (372 `food` + **2 `drainable`**), 2 446 key parts, 31 distinct keys, 213 of the parts carrying the `Cooked` suffix | C — `meta.counts` |
| the join | **6 902** (key part, recipe) joins → **6 881** rows; 21 land on a (recipe, item) pair twice, through an alias or through both arms, and every one repeats the same `use`, so the row keeps the last key written (the loader's map is last-write-wins) and names the collapsed ones in `duplicateKeys` | C — `meta.counts.pairs` / `ingredients` / `duplicateJoins` |
| unmatched keys | **0** — `unmatchedKeys` is empty, and an unmatched key would be recorded, never guessed at | C |
| the live check | `getPossibleItems()` for `Salad` / `SaladClay` / `ConeIcecream` / `Soup` / `AddBaitToChum` returned **189 / 189 / 56 / 193 / 42**, and each list is **set-equal** to the dataset's ingredient list for that recipe — 0 extra, 0 missing, in both directions. The five list sizes are the run's; the **set-equality is an offline computation** against the committed `itemFullTypes`. By controller ruling the run itself compared the evolved half to nothing — `data/evolved-recipes.json` did not exist yet — so `M` here means "measured lists, compared afterwards", not "verdict carried by the run" | **M** for the lists, `exp06-20260910-112726` ([`recipes.json`](../../testing/artifacts/exp06-20260910-112726/recipes.json)), `evolved.<name>.reply.itemFullTypes`; C (arith.) for the equality |

### The evolved summation

The arithmetic is **cited, not restated**: [food-item-model.md](food-item-model.md) § Evolved
recipes carries `EvolvedRecipe.addItem(base, ingredient, chef) @0–@1928 L265–L487` term by term,
with the measured Salad dish beside it. `data/evolved-recipes.json` applies that block — the whole
of its non-rotten path — per (recipe, ingredient) row at Cooking **0** and Cooking **10**:

| Branch of `addItem` | How the dataset models it | Ev |
|---|---|---|
| `hunger = use/100`, `hungerAfterSkill`, `share`, `skillBonus`, the four macros and thirst | applied verbatim as cited; `at0` / `at10` carry every term, not just the results | C (arith.) — the formula C+M, `exp02-20260910-030433` |
| the **hunger clamp** `@934 L374–376` (`hunger` capped at the ingredient's own `HungerChange` magnitude) | applied, and flagged where it bites: **17 keys over-ask**, expanding to **59 of the 6 881 rows** (`hungerClamped`, `meta.counts.hungerClampRows`). `Base.Cherry`'s `Oatmeal:5` against a hunger of 3 is `share 0.7` at Cooking 10, not 1.0 | C |
| the **`DRIED_FOOD` thirst skip** `@1316 L416` | applied: a tagged ingredient adds no thirst. It bites on **27** rows — `Base.Ramen`, `Base.Macaroni`, `Base.Pasta` across nine recipes each — which carry `thirstSkipped: true` (`meta.counts.driedFoodThirstRows`). The tag is on 577 rows in all; on the other 550 the thirst term was already 0 | C |
| the **spice branch** `@582–@775 L336–L359` | applied: a `Spice = true` ingredient returns before the hunger lines, so `share`, `hunger`, `hungerAfterSkill` and every macro are **0** on all **2 522** spice rows, with the row's `note` naming the branch. These are measured zeroes, not absences | C |
| the **rotten branch** (`0.05×`/`0.10×` base hunger at Cooking 7–8 / 9–10, refused below 7) | **not modelled per row** — the dataset publishes the fresh-ingredient contribution only. The gate is the one branch of `addItem` left out | C — [food-item-model.md](food-item-model.md) § Evolved recipes |
| a non-`per_item` ingredient row | macros `null` + `reason`, hunger arithmetic still emitted. Never fires on vanilla (`ingredientsRefusedByBasis` 0 — all 374 carriers are `per_item`) | C |

The Salad rows reproduce the measured dish off the generated dataset: lettuce `share` 0.333333 /
0.233333, tomato 0.5 / 0.35, `skillBonus` 1.0 / 1.6667, **dish 25.0 kcal at Cooking 0 and 29.1667
at Cooking 10**. Ev C (arith.), against **M** `exp02-20260910-030433`
([food-item-model.md](food-item-model.md) § Evolved recipes).

### The CSV/JSON split

- **`data/recipes.csv`** — 969 rows, **37 columns**, one row per recipe; IO lines are joined into
  `inputsRaw` / `outputsRaw` with ` | `. **`data/recipes.json`** — `{"meta", "recipes" (969),
  "replacements" (163)}`, `indent=1`, sorted by name, 3.4 MB.
- **`data/evolved-recipes.csv`** — 6 881 rows, 13 columns, one row per (recipe, ingredient).
  **`data/evolved-recipes.json`** — `{"meta", "recipes" (63), "unmatchedKeys" (0)}`, 7.7 MB, with
  the full `at0` / `at10` blocks the CSV only samples.
- Both JSONs are **byte-stable within one UTC day**: two runs of the scanner produce identical
  files, asserted by two install-gated tests and re-checked at every change. The one field that
  can differ between runs is `meta.generated`, which is today's UTC **date** — so a rebuild
  either side of midnight UTC differs in exactly that line and nothing else.
- `meta.sources` records the scripts root, the files a record was read from, and
  `data/food-items.json` with its own build / jar / generated stamps, so a rebuild of one half
  against a stale other half is visible **in the file**.
- Column-by-column definitions and the `meta` key tables:
  [`data/README.md`](../../data/README.md) § recipes and § evolved-recipes. Ev C.

---

## Code map

| Path | Where | What it does | Ev |
|---|---|---|---|
| `tools/recipe_scan.py` — craft half | `parse_io`, `attach_sub_lines`, `build_recipe`, `parse_text`, `input_charge`, `uses_per_item`, `delta_terms`, `nutrition_delta`, `scan`, `build_dataset` | the IO grammar, the sub-line nesting, the delta rule above, both writers | C |
| `tools/recipe_scan.py` — evolved half | `alias`, `parse_evolved_key`, `resolve_arms`, `resolve_recipes`, `contribution`, `evolved_ingredients`, `scan_evolved`, `build_evolved_dataset`, `replacement_delta`, `replacements` | the two join arms, the summation, the `ReplaceOn*` links | C |
| `tools/food_scan.py` | `parse_script` / `walk` / `named` / `values` / `coerce` | the **shared** nesting-aware block parser, imported unchanged — slice 06 adds no second walker. Mapper pairs are read from a block's `lines`, not `props` (§ Discrepancies row 6) | C |
| `data/food-items.json` | 1 005 item rows + 61 fluids | the nutrition side of every join, read through `FOOD_FIELDS` / `food_value` | C — [food-dataset-notes.md](food-dataset-notes.md) |
| `ScriptManager.getAllCraftRecipes()` / `.getAllEvolvedRecipesList()` / `.getAllRecipes()` / `.getAllUniqueRecipes()` | jar | the game's own loaded-definition lists — what `recipes.count` counts | C; **M** `exp06-20260910-112726` ([`recipes.json`](../../testing/artifacts/exp06-20260910-112726/recipes.json)) |
| `ScriptBucketCollection.getScript @45–@99 L78–L96` | jar | why `getCraftRecipe` / `getEvolvedRecipe` answer to both `Name` and `Base.Name` — measured on all fifteen probes | C; **M** same run |
| `Item.OnScriptsLoaded @43–@59 L3033–L3035`, `@122–@140 L3039` | jar | the two join arms; the second is `equalsIgnoreCase` on `Template` | C |
| `Item.DoParam` | jar | the five parse-time `EvolvedRecipe` aliases | C — [food-item-model.md](food-item-model.md) § Key reference |
| `EvolvedRecipe.addItem @0–@1928 L265–L487` | jar | the summation, the clamp `@934 L374–376`, the spice return `@582–@775 L336–L359`, the `DRIED_FOOD` thirst skip `@1316 L416` | C — [food-item-model.md](food-item-model.md) § Evolved recipes |
| `EvolvedRecipe.Load @142–@157 L102–L104`, `.getResultItem @0–@22 L685–L688` | jar | `isCookable()` is set by the **presence** of `Cookable`; `getResultItem()` strips the module (§ Discrepancies rows 4 and 5) | C; **M** same run |
| `CraftRecipe.LoadIO @218–@317`, `.getInputCount @0–@7 L257` | jar | a `-`/`+` sub-line attaches to the preceding input and never enters `inputs` | C; **M** same run |
| `CraftRecipeData.consumeInputFromItems @372 L1089` / `.processDestroyAndUsedItems @337–@490 L563–L577` / `.createOutputItems @39–@116 L1408–L1418` | jar | uses-vs-items, the reduction, and outputs as item counts | C |
| `ItemUser.UseItem @28 L37-38`, `@260 L66-67`, `@272 L68-70` | jar | the one line that spends uses, and the two removals after it | C; **M** for the spend, `exp06b-20260910-120123` |
| `Food.getMaxUses @11–@23 L2210–L2214` / `.setCurrentUses @23–@35 L2228–L2233` / `.consumeHunger @0–@17 L2714–L2715` / `.multiplyFoodValues @0–@156 L2288–L2303` | jar | one use = one `HungerChange` point, and what the reduction scales | C; **M** same run |
| `Food.update` `@224–@412 L398–L421` (the `ReplaceOnCooked` branch) | jar | the cook-transition swap: `AddItem` each name, `copyConditionStatesFrom`, remove the original, **return** — the item is never flagged cooked | C — [food-item-model.md](food-item-model.md) § Cooking |
| `Food.updateRotting @13–@19 L658-659`, `@20–@226 L662–L694` | jar | the rotten swap, and the `GameClient.client` early return that makes it server-only | C |
| `ISHandcraftAction.lua:222-234` | Lua | outputs are built *before* `processDestroyAndUsedItems` reduces the inputs | C |
| harness | server `recipes.count`, `recipes.evolved <name>`, `recipes.craft <name>` (`server/PZTestKit_Server_Recipes.lua`), `item.use <user> <fullType> <uses>` (`server/PZTestKit_Server.lua`) | the live routes, documented in [`../testing/README.md`](../testing/README.md) § Command bus | **M** both runs |
| experiments | `testing/experiments/s06_recipes.py`, `testing/experiments/s06b_use_probe.py` | the two measured runs | **M** both runs |

---

## Cooking deltas

### Plain cooking is a zero delta — `MakeToast` worked through

`entities/appliances/workstations/entity_toaster_craftRecipe.txt:3`, `time 20`,
`category Cooking`, `tags ["Toaster"]`:

```
inputs  { item 1 [Base.BreadSlices] flags[ItemCount] }   ->  1 whole slice
outputs { item 1 Base.Toast }                            ->  1 whole Toast
```

`Base.BreadSlices` (`items/food.txt:2123`) and `Base.Toast` are **177 kcal / 33 carbs / 2.22
lipids / 5.9 proteins** each; only `HungerChange` differs, −10 against −8. So the delta is
`0.0 / 0.0 / 0.0 / 0.0` with `hungerChange +2.0`, and `absentMacros` names the two thirst lines
neither block writes. The same transformation exists as a `ReplaceOnCooked` link
(`Base.BreadSlices → Base.Toast`) with the same numbers. Ev C (arith.); the mechanism C —
[food-item-model.md](food-item-model.md) § Cooking, where the only nutrition *state* modifier in
the game is `Eat`'s ÷5 for burnt.

**This is the slice's load-bearing negative result**: cooking as such moves no calories anywhere
in the data. Every non-zero row below is a recipe that changes what the item **is**.

### The 31 resolvable craft deltas, largest |kcal| first

`[IC]` marks an input the script flags `ItemCount` (so N is whole items); every other consumed
input is charged in uses by the rule above.

| Recipe | Consumed | Produced | Δ kcal | Δ hunger | Ev |
|---|---|---|---:|---:|---|
| `open_mac_and_cheese` | 1 × Macandcheese | 1 × Macaroni + 1 × cheese_powdered | 2800 | −74 | C (arith.) |
| `CutTurkey` | 1 × TurkeyWhole [IC] | 2 × TurkeyLegs + 2 × TurkeyWings + 2 × TurkeyFillet | −501 | −20 | C (arith.) |
| `GrindCornflour` | 20 × CornSeed [IC] | 1 × Cornflour2 | −496 | 20 | C (arith.) |
| `GrindCornmeal` | 20 × CornSeed [IC] | 1 × Cornmeal2 | −496 | 60 | C (arith.) |
| `MillCornflour` | 20 × CornSeed [IC] | 1 × Cornflour2 | −496 | 20 | C (arith.) |
| `MillCornmeal` | 20 × CornSeed [IC] | 1 × Cornmeal2 | −496 | 60 | C (arith.) |
| `MakeMeatPatty` | 40 × MincedMeat (= one whole tub) | 1 × MeatPatty | **+312** | 0 | C (arith.) + **M** `exp06b-20260910-120123` |
| `CutChicken` | 1 × ChickenWhole [IC] | 2 × Chicken + 2 × ChickenWings + 2 × ChickenFillet | −195 | −4 | C (arith.) |
| `MakeHotDog` | 1 × BunsHotdog_single [IC] + 1 × Hotdog_single [IC] | 1 × Hotdog | −142 | 0 | C (arith.) |
| `MakeTortillaChips` | 1 × Tortilla (= 1/5 of one) | 1 × TortillaChipsBaked | +112 | −14 | C (arith.) |
| `ScoopIceCream` | 1 × Cone [IC] + 10 × Icecream (= 1/3 of a tub) | 1 × ConeIcecream | **−105** | 0 | C (arith.) + **M** `exp06b-20260910-120123` |
| `MillSunflowerSeeds` | 6 × SunflowerSeeds [IC] | 1 × SeedPaste | −10 | 0 | C (arith.) |
| `OpenHotdogPack` | 1 × HotdogPack | 4 × Hotdog_single | −10 | −40 | C (arith.) |
| `MakeSquidCalamari` | 1 × Squid [IC] | 2 × SquidCalamari | +5 | 10 | C (arith.) |
| `SmashPumpkin` | 1 × Pumpkin [IC] | 5 × PumpkinSmashed | −4 | 0 | C (arith.) |
| `GetBaconBits` | 1 × BaconRashers [IC] | 4 × BaconBits | 0 | 0 | C (arith.) |
| `GetBaconRashers` | 1 × Bacon [IC] | 4 × BaconRashers | 0 | −4 | C (arith.) |
| `HalveFillet` † | 1 × FishFillet [IC] | 2 × FishFillet | 0 | 0 | C (arith.) |
| `HarvestRoe` † | 1 × FishRoeSac [IC] | 1 × FishRoe | 0 | 0 | C (arith.) |
| `MakeHalloweenPumpkin` † | 1 × Pumpkin [IC] | 1 × HalloweenPumpkin | 0 | 0 | C (arith.) |
| `MakeToast` | 1 × BreadSlices [IC] | 1 × Toast | 0 | +2 | C (arith.) |
| `OpenCandyPackage` | 1 × CandyPackage | 5 × Lollipop + 5 × MintCandy | 0 | −35 | C (arith.) |
| `PackCigarettes` ‡ | 20 × CigaretteSingle | 1 × CigarettePack | 0 | 0 | C (arith.) |
| `SliceBaloney` † | 1 × Baloney [IC] | 6 × BaloneySlice | 0 | 0 | C (arith.) |
| `SliceHam` † | 1 × Ham [IC] | 6 × HamSlice | 0 | 0 | C (arith.) |
| `SlicePumpkin` † | 1 × Pumpkin [IC] | 10 × PumpkinSliced | 0 | 0 | C (arith.) |
| `SliceSalami` † | 1 × Salami [IC] | 4 × SalamiSlice | 0 | 0 | C (arith.) |
| `SliceWatermelon` † | 1 × Watermelon [IC] | 10 × WatermelonSliced | 0 | 0 | C (arith.) |
| `SmashWatermelon` | 1 × Watermelon [IC] | 5 × WatermelonSmashed | 0 | 0 | C (arith.) |
| `TakeACigarette` ‡ | 1 × CigarettePack | 1 × CigaretteSingle | 0 | 0 | C (arith.) |
| `UnpackCigarettes` ‡ | 1 × CigarettePack | 20 × CigaretteSingle | 0 | 0 | C (arith.) |

† the 8 `InheritFood` **splits** — the delta is 0 by construction, not by conservation, and each
one has exactly one consumed input. ‡ the 3 `recipesWithCaloriesAbsentOnEverySide`: neither
cigarette row writes a `Calories` line, so their `0` is the `absentMacros` substitution.
`TakeACigarette` and `UnpackCigarettes` additionally charge a **drainable** input at 0 macros, and
`UnpackCigarettes` is the one row whose `mode:destroy` rounds that charge up to a whole item — its
`destroyWaste` is `null`, because the pack carries no macro to waste (`notes` records the round-up).

Everything else that reads 0 above **is** conservation — `1 × Watermelon 1 355 kcal =
10 × WatermelonSliced 135.5`. **15** rows are non-zero in calories
(`meta.counts.recipesWithNonZeroCalorieDelta`), and three of them are vanilla script
inconsistencies worth a mod's attention: `open_mac_and_cheese` creates 2 800 kcal,
`MakeMeatPatty` creates 312 out of nothing, and the four corn mills destroy 496 apiece because
neither `Base.Cornflour2` nor `Base.Cornmeal2` declares a macro key at all (each writes a
`HungerChange` and nothing else, so every one of those 496 kcal is an `absentMacros`
substitution). Ev C (arith.) throughout, on the measured
per-use rule.

### The `ReplaceOn*` links — 3 + 8, and 152 more

`data/recipes.json` `replacements` holds **163** records of
`{from, to, trigger, sourceFile, sourceLine, delta, deltaReason}`, sorted by trigger (cooked,
rotten, use, deplete). `sourceLine` is the **item block's** header line, the way every other record
in these datasets anchors; the `ReplaceOn*` key itself sits a few lines below it.

**3 `ReplaceOnCooked`** — each fires on the cook transition and only if not rotten; the original is
removed and `Food.update` **returns**, so the item is replaced and never flagged cooked
(`@224–@412 L398–L421`):

| from → to | anchor | Δ kcal | Δ hunger | Δ thirst | Ev |
|---|---|---:|---:|---:|---|
| `Base.BaguetteDough` → `Base.Baguette` | `items/food.txt:2807` | 0 | −8.0 | **−15.0** | C (arith.) |
| `Base.BreadSlices` → `Base.Toast` | `items/food.txt:2123` | 0 | +2.0 | 0 | C (arith.) |
| `Base.PancakesCraft` → `Base.Pancakes` | `items/food.txt:10906` | 0 | +4.0 | 0 | C (arith.) |

**None of the three moves a macro**, but they do not all "move only hunger" either:
`Base.BaguetteDough` writes `ThirstChange = 15` and `Base.Baguette` writes no thirst line at all,
so baking a baguette moves **−15.0** of thirst — an absent-vs-measured substitution, named in that
row's `absentMacros` as `Base.Baguette:thirstChange`. The other two rows' thirst `0` is a
both-sides-absent zero. Ev C (arith.).

**8 `ReplaceOnRotten`** — `updateRotting` ages the item every tick and, once rotten, creates the
replacement, copies `age` + condition states and destroys the original (`@20–@226 L662–L694`):
`Base.SugarBeetSyrupPot → Base.SugarBeetSugarPot` (`items/food.txt:576`) and the seven ice-cream
melts (`:12417`, `:12456`, `:12478`, `:12520`, `:12542`, `:12564`, `:12585` —
`ConeIcecream`, `ConeIcecreamToppings`, `Icecream`, `Creamocle`, `FudgeePop`, `IcecreamSandwich`,
`Popsicle`). **All 8 conserve every macro** — zero in all four macros *and* in hunger and thirst,
with only `thirstChange` in `absentMacros`. Ev C (arith.).

**110 `ReplaceOnUse` + 42 `ReplaceOnDeplete`.** 12 of the 163 links carry a delta (the 3 cooked,
the 8 rotten and `Base.Pumpkin → Base.PumpkinSeed`); the other 151 are refused **by name** — 114
`no-nutrition` (the target is a dataset row with no nutrition key: an empty tin, a mug, a bowl) and
37 `not-in-dataset`. Slice 05's finding survives untouched: `Base.HotDrinkRed → Base.MugRed`
(`items/food.txt:6531`) reads `not-in-dataset`, and a grep of all `media/scripts/**/*.txt` confirms
`Base.MugRed` is written by **no** `item` block — the only one of the 37 that is genuinely
undefined rather than merely not a food item (the other 36 are pans, trays, sandbags and a smoking
pipe). Ev C — [food-dataset-notes.md](food-dataset-notes.md) § Discrepancies row 2.

---

## MP behaviour

**The datasets are not sided; three of the things they describe are.** Script data is parsed
identically on both sides and never networked — the same `ScriptManager` reads the same
`media/scripts/` files in each process — so a scanned recipe is exactly the load-time definition
both sides start from.

| Fact | Mechanism | Ev |
|---|---|---|
| Both sides load the same `craftRecipe` / `evolvedrecipe` definitions and no packet carries them | `ScriptManager` reads `media/scripts/` per process at load; the item packet slice 02 read field by field carries *instance* state only. This is why `recipes.count` is a **server-only** command and still the whole answer | C — [food-dataset-notes.md](food-dataset-notes.md) § MP behaviour |
| Every `ReplaceOnRotten` swap is **server-only** | `Food.updateRotting` returns immediately on `GameClient.client` (`@13–@19 L658-659`), and it is the method that both ages the item and creates the replacement. A client never performs one of the 8 melts | C — [food-item-model.md](food-item-model.md) § MP behaviour |
| The cook transition — and therefore each `ReplaceOnCooked` swap — is driven by server-owned state | `Food.update` gates `updateAge` on `GameServer.server` (`@38–@46 L369-370`) and both `sendItemStats` calls in the cooking block are server-gated; the item instance is server-owned for its whole lifecycle | C — same section |
| The Cooking **perk level** that scales the evolved summation is server-owned | a server-side `setPerkLevelDebug` was visible to the client on the very next bus command; the client-side write was a no-op. So a client-side perk write silently runs the recipe at the **server's** level — `skillBonus` and `share` are the server's, whatever the client UI shows | **M** `exp02-20260910-030433` — [food-item-model.md](food-item-model.md) § MP behaviour |
| A recipe whose IO is a **drink** completes server-side too | **An inference, not a reading.** The citation behind it is about *drinking*: an MP client never calls `DrinkFluid`. Nothing here has read the *craft* completion path for a fluid IO line — that would be `ISHandcraftAction` / the `NetTimedAction` it runs under, which no slice has opened. Fluid nutrition is per litre and is excluded from these deltas anyway, so nothing in the dataset rests on it | C (inference) — [food-dataset-notes.md](food-dataset-notes.md) § MP behaviour |
| Do not read a **client-side instance** to decide what a craft consumed | `ItemStatsPacket` skips conditionally-written fields when they are zero and the receiver reuses one cached packet per type, so a zero-valued field on a client can be carrying another item's value | C — [food-item-model.md](food-item-model.md) § A zero-valued packet field can arrive carrying another item's value |

**What this means for a mod.** Read the dataset (or a server-side instance) for what a recipe *is*;
put anything that changes what crafting delivers on the **server**, the same rule slices 01, 03 and
05 reached for `Nutrition`, hunger, thirst and drinking. Ev C.

---

## Discrepancies

Not wiki rows — there is no wiki page for this dataset. These are places where the slice-06 plan,
an earlier report or vanilla's own data disagrees with what the files now say.

| # | Claim / expectation | What is actually the case | Ev |
|---|---|---|---|
| 1 | The plan: **10** recipes with no `outputs`, all in `recipes_fixing.txt` / `recipes_gasmasks.txt` | **11 + 26.** 11 ship no `outputs` block — the plan's list omits `scrap_jewellery`, which lives in `entities/blacksmith/craftRecipes/recipes_blacksmith_other_metals.txt:418`, outside both named files — and 26 more ship an `outputs { }` that is really empty (`recipes_fixing.txt:18`, `MakeMilkFromPowderBucket`, the can-openers, `DyeClothes`, …). `969 − 958 = 11` is the block count the plan's own step predicted, so only the prose was wrong | C — `meta.counts` |
| 2 | The plan's `mode:` / `flags[…]` table: `keep` 1 502, `destroy` 244, `mixture` 26; `MayDegradeLight` 1 016, `Prop1` 440, `IsNotDull` 219, `ItemCount` 185 | Those are a **raw grep of every script file**. 202 further `inputs` blocks belong to a `component CraftRecipe` (an entity's own build recipe) and carry 138 more `mode:` lines. Scoped to the 969 `craftRecipe` blocks: **keep 1 366 / destroy 242 / mixture 26**, `MayDegradeLight 975 / Prop2 384 / Prop1 320 / IsNotDull 214 / ItemCount 182 / InheritFoodAge 46`. The census count is `meta.counts.componentCraftRecipes` (202), so the two figures reconcile from the data — whether those entity build recipes belong in a later slice is § Open questions 1 | C |
| 3 | `summary.craft_all_matched: false` and `fields_mismatched: 2` in the exp06 artifact | **Do not cite either as evidence about the scanner.** Both misses are the same field, `inputCount`, on `MakePizza` (10 vs 9) and `MakeMilkFromPowderBucket` (3 vs 2), and neither side lost an input: the loader attaches a `-` sub-line to the preceding input and `getInputCount()` is `inputs.size()`. The artifact's own `top_level` / `top_level_matches` rows already recorded that the dataset's line list *minus* sub-lines equals the game's counter, and the scanner's fix round then adopted the loader's model — `data/recipes.json` now reads `inputCount` **9** and **2**, so the same comparison replayed offline is **10/10 recipes, 77/77 raw rows** (**67/67** once the ten live-vs-live `outputListSize` rows are set aside; it was 65/67 at run time). Cite `summary.fields_mismatched_other` (**0**) or `summary.per_recipe` | **M** `exp06-20260910-112726` ([`recipes.json`](../../testing/artifacts/exp06-20260910-112726/recipes.json)); the *do not cite* rows are in [`testing/artifacts/README.md`](../../testing/artifacts/README.md) |
| 4 | The plan: `Salad` and `SaladClay` take **187** ingredients each; the live probe's `salad_matches_plan` reads `false` | **189, and the plan's number is the wrong one.** 189 items write a `Salad:` key — 187 in `items/food.txt` and **2 in `items/drainable.txt`** (`Base.Vinegar2` `:869`, `Base.Vinegar_Jug` `:894`, both `Spice = true`). The plan's own 374 carriers = 372 food + 2 drainable, and its 6 902 pairs reproduce exactly **only** when both drainables count: over `food.txt` alone the pair count is 6 858, emitted as `meta.counts.pairsFromFoodTxt` so the plan's derivation stays reconstructible. An expansion that filters to food reports 187 and two false unmatched keys | **M** live `ingredientCount` 189 / 189 — `exp06-20260910-112726`; C for the two drainables |
| 5 | `isCookable()` reflects the `Cookable` value; `getResultItem()` is the script string | Neither. **`isCookable()` is set by the *presence* of the key** (`EvolvedRecipe.Load @142–@157 L102–L104` stores `iconst_1` and never reads the parsed value): `AddBaitToChum` writes `Cookable = false` and the game answers **true** — the only one of the 63 where a faithful text read and the game disagree, which is why `data/evolved-recipes.json` carries the *script* value (`cookable: false`) and this row carries the engine's. And **`getResultItem()` strips the module** (`@0–@22 L685–L688`), so the live `Salad` must be compared against the dataset's `Base.Salad`; `getBaseItem` is unstripped | **M** `exp06-20260910-112726`; C for both mechanisms |
| 6 | `itemMapper` pairs are `Key = Value` props, and a mapper resolves to at least one type | Neither is safely true. The shared parser only accepts identifier keys, so the **1 599 dotted mapper lines land in a block's `lines`** — deliberately: allowing dotted keys in `props` would collapse the 56 mappers that name one result twice down to their last source. The dataset reads them from `lines` and keeps them lossless in `itemMapperPairs`. And one mapper resolves to **nothing**: `ExtractIronFromIronOre`'s `SmeltMapper` writes only a `default`, so under the stated rule its output has `types: []`; the case is `meta.outputMapperIssues`, never special-cased into `types` | C |
| 7 | The plan: **116** recipes touch a food item; **23** have a non-zero calorie delta | **375** and **15 (+3)**. "Touching a food item" measured as *any* item line, either side, naming a `food`/`drainable` row is 375; ~100 alternative definitions were tried and none yields 116 (nearest: 305 single-type lines only, 182 outputs only, 150 `kind == food`, 141 both sides). The 23 is reconstructible but stale: it was 20 non-zero + 3 absent-on-every-side before the input-amount fix, and the corrected weights move five more rows to 0 through the split rule, leaving **15 + 5 splits + 3 absent**. `recipesTouchingFood`, `recipesWithFoodOutput` (182) and `recipesTouchingDatasetRow` (413) are all emitted so the definition is never implicit | C |
| 8 | An earlier build of this dataset: `ScoopIceCream` **−16 345** kcal, `MakeMeatPatty` **−11 388**, `HalveFillet` **+205**, `SliceSalami` **−66** | Superseded by the input-amount rule (§ The delta rule). `item 10 [Base.Icecream]` is 10/30 of a tub (**−105**), `item 40 [Base.MincedMeat]` is one whole tub (**+312**), and `HalveFillet` / `SliceSalami` / `HarvestRoe` / `SlicePumpkin` / `SliceBaloney` are `InheritFood` splits and therefore **0**. **Ten** of the 31 moved in at least one macro — `HalveFillet`, `HarvestRoe`, `MakeMeatPatty`, `MakeTortillaChips`, `ScoopIceCream`, `SliceBaloney`, `SliceHam`, `SlicePumpkin`, `SliceSalami`, `SliceWatermelon` — **seven** of them exact-`InheritFood` splits that went to 0 (the eighth split, `MakeHalloweenPumpkin`, was already 0), leaving **21** unchanged. An earlier "eight moved / five to 0 / 23 unchanged" counted calories and hunger only: `SliceHam` moved carbs −0.04 → 0 and `SliceWatermelon` moved carbs, lipids, proteins and thirst (−60 → 0) with kcal never leaving 0, and `MakeTortillaChips` (`item 1 [Base.Tortilla]`, one fifth of a tortilla, +80 → **+112**) is a moved row no artefact names. Any figure quoting the old numbers predates commit `6694568` | C (arith.); **M** for the rule, `exp06b-20260910-120123` ([`use-probe.json`](../../testing/artifacts/exp06b-20260910-120123/use-probe.json)) |
| 9 | An earlier report: "the 3 cooked links move only hunger" | One of them moves **thirst** as well — `Base.BaguetteDough → Base.Baguette`, −15.0, by absence rather than by measurement. The safe statement is the one above: none of the three moves a **macro** | C (arith.) |
| 10 | The evolved contribution is the summation "applied verbatim" | It is the whole of `addItem`'s **non-rotten** path: the hunger clamp, the spice return and the `DRIED_FOOD` thirst skip are all applied (59 / 2 522 / 27 rows). Before those rounds the dataset published a Cooking-10 share of 1.0 where the game gives 0.7, a spice hunger of `use/100` where the game moves none, and a thirst the game never adds for `Base.Ramen` / `Base.Macaroni` / `Base.Pasta`. Only the rotten branch is left unmodelled | C |

---

## Open questions

1. **202 `component CraftRecipe` blocks are censused but not scanned.** They are entity build
   recipes (`entities/admin/entity_piano.txt:38`) carrying their own `inputs` blocks, which is why
   a raw grep of the scripts counts more `mode:` lines than this dataset does. They are out of the
   plan's scope; whether the item pass wants them as a third dataset — and whether any of them
   consumes food — is open. `meta.counts.componentCraftRecipes` carries the count so the two
   universes can always be reconciled. Ev C.
2. **The removal on depletion is grade C, not M.** `ItemUser.UseItem`'s `RemoveItem` branch
   (`@272 L68-70`) cannot be exercised from Lua on 42.20.4 — `ItemUser` is not exposed — so
   everything the dataset says about a `mode:destroy` line *annihilating* the rest of an item rests
   on a jar reading. Reaching it needs a real `ISHandcraftAction` craft, not an item command. Ev C.
3. **`variable[1:20]` versus `isVariableAmount()`.** 33 drying recipes write a range on **both**
   sides (66 lines), while `.superpowers/sdd/06-recipes/q-itemcount-notes.md` reads
   `InputScript.isVariableAmount @0–@17 L375` (`amount != maxamount`) as never firing in vanilla
   and pins `calculatedVariableInputRatio` at 1.0. Both cannot be right about these lines. Nothing
   in the dataset depends on the answer — every one of the 33 is `amount: null` with
   `deltaReason` starting `variable-amount` — but a mod that wants a drying-rack delta has to
   settle it first, and the cheap settlement is one live `recipes.craft DryBasil` reading
   `getInputCount` and the input's `getAmount` / `getMaxAmount`. Ev C.
4. **The rotten branch of the evolved summation is not per-row.** An ingredient added rotten
   contributes `0.05 ×` (Cooking 7–8) or `0.10 ×` the base hunger and is refused below Cooking 7;
   the dataset publishes the fresh contribution only. A mod that cares about cooking with rotten
   stock needs that arm computed, and it needs the *instance's* rotten flag, which is not script
   data. Ev C.
5. **`data/food-items.json` carries no `UseDelta` column**, so the drainable rule is unconditional
   (`0 macros + a note`) where the jar's own test is `is_drainable && UseDelta < 1`. Both vanilla
   drainable inputs are cigarette packs with null macros, so nothing is at stake today; a modded
   drainable food input with real macros would be weighed at 0 and only the note would say why.
   Ev C.
6. **A second partial-use row would widen the measured base.** The fractional half of the per-use
   rule rests on `Base.Icecream` alone (seven fields plus the `(int)` truncation of
   `getCurrentUses()`); `Base.Salt` at 1 of 10 — `MakePizza`'s own line — is a two-minute probe on
   the existing `item.use` command. Ev C.
7. **`meta.outputMapperIssues` is one row today.** If a mod ships a mapper with only a `default`,
   its outputs silently resolve to nothing; whether the scanner should widen the rule to take the
   default as a type is a decision the vanilla data does not force. Ev C.
8. **The 37 recipes with no outputs mutate their input through `OnCreate`.** The dataset records
   the hook name and refuses the delta; what those Lua functions actually do to nutrition (if
   anything) is unread. Ev C.
9. **The five parse-time `EvolvedRecipe` aliases were never live-checked.** `RicePot` / `RicePan`
   → `Rice`, `PastaPot` / `PastaPan` → `Pasta`, `Roasted Vegetables` → `Stir fry`
   (§ Resolution rules) rest entirely on `Item.DoParam`: the run's five `recipes.evolved` probes
   are `Salad` / `SaladClay` / `ConeIcecream` / `Soup` / `AddBaitToChum`, and not one of them is
   an alias target. Five key parts depend on it, and unaliased `RicePan:1` would reach one recipe
   instead of four. The settlement is one live probe — **`recipes.evolved RicePot`**: on the
   aliased reading the name resolves to nothing (`Rice` is the recipe, `RicePot` only a key), and
   the four `Rice`-templated recipes' `getPossibleItems()` lists must contain the items whose keys
   are written `RicePot:<n>` / `RicePan:<n>`. Ev C.

---

## Sources

**Scripts (`D:\SteamLibrary\steamapps\common\ProjectZomboid\media\scripts\generated\`)**
The 74 files holding the 969 `craftRecipe` blocks, listed in `meta.sources.files` — 42 under
`recipes/` (`recipes_cooking.txt:41` `OpenBagOfFrozenFood`, `:509` `MakePizza`, `:1091`
`ScoopIceCream`, `:1171` `open_mac_and_cheese`) and 32 under
`entities/*/{craftRecipes,cratRecipes,workstations}/`
(`entities/appliances/workstations/entity_toaster_craftRecipe.txt:3` `MakeToast`,
`entities/agricultural/workstations/entity_stone_mill_craftRecipe.txt:3` `MillCornflour`,
`entities/blacksmith/craftRecipes/recipes_blacksmith_other_metals.txt:418` `scrap_jewellery`);
`evolvedrecipes.txt` (62 blocks; `ConeIcecream` at `:603` with its `Template` at `:610`) and
`recipes/recipes_fishing_evolvedrecipe.txt` (`AddBaitToChum`, `Cookable = false` at `:9`);
`items/food.txt` (the 372 food carriers, the 3 + 8 `ReplaceOn*` sources, `item Cinnamon` at
`:13665`) and `items/drainable.txt` (`Base.Vinegar2` `:869`, `Base.Vinegar_Jug` `:894`). The
scanner walks all 1 004 `media/scripts/**/*.txt`; the 74 it read a recipe from are in `meta`.

**Jar (pzdis, 42.20.4 `b0bbce05d5`)** `zombie/scripting/objects/ScriptManager`
(`getAllCraftRecipes`, `getAllEvolvedRecipesList`, `getAllRecipes`, `getAllUniqueRecipes`,
`getCraftRecipe`, `getEvolvedRecipe`); `zombie/scripting/ScriptBucketCollection.getScript`;
`zombie/scripting/objects/Item` (`OnScriptsLoaded`, `DoParam`); `zombie/scripting/objects/Recipe`
and `zombie/scripting/ScriptType`; `zombie/scripting/objects/EvolvedRecipe` (`Load`, `addItem`,
`getResultItem`, `getFullResultItem`);
`zombie/scripting/entity/components/crafting/{CraftRecipe,InputScript,OutputScript,InputFlag}`
(`LoadIO`, `getInputCount`, `isItemCount`, `isUsesPartialItem`, `getIntAmount`);
`zombie/entity/components/crafting/{CraftRecipeData,CraftRecipeManager}`
(`consumeInputFromItems`, `processDestroyAndUsedItems`, `createOutputItems`,
`consumeInputItemUsesInternal`); `zombie/inventory/ItemUser.UseItem`;
`zombie/inventory/types/Food` (`getMaxUses`, `getCurrentUses`, `setCurrentUses`, `consumeHunger`,
`multiplyFoodValues`, `copyFoodFromSplit`, `copyNutritionFromRatio`, `copyAgeFrom`, `update`,
`updateRotting`); `zombie/Lua/LuaManager$Exposer.shouldExpose`. The full bytecode read of the
input-amount path, with every address, is `.superpowers/sdd/06-recipes/q-itemcount-notes.md`
(session record, not tracked); the load-bearing addresses are quoted inline above so this document
stands on its own.

**Lua** `media/lua/shared/Entity/TimedActions/ISHandcraftAction.lua:222-234` (outputs are built
before the inputs are reduced), `media/lua/server/BuildingObjects/ISBuildIsoEntity.lua:570` (the
same route for buildables), `media/lua/client/.../ISWidgetInput.lua:554`, `:558-561` (the UI's own
"N Uses" reading of `isUsesPartialItem`).

**Measured run 1 — the `ScriptManager` cross-check.** `exp06-20260910-112726`,
[`testing/artifacts/exp06-20260910-112726/recipes.json`](../../testing/artifacts/exp06-20260910-112726/recipes.json)
(sha256 `6cf20856…`), 89.1 s, fixture `default`, build 42.20.4, `server_errors []`, doctor
all-`ok`, no world change. Script `testing/experiments/s06_recipes.py`; harness commands
`recipes.count` / `recipes.evolved` / `recipes.craft`. **Cite `counts`, `comparison` and the
verbatim `evolved.<name>.reply` lists** — `summary.craft_all_matched` /
`summary.fields_mismatched` and `summary.evolved_observations.salad_matches_plan` are *do not
cite* rows in [`testing/artifacts/README.md`](../../testing/artifacts/README.md) (§ Discrepancies
rows 3 and 4). The evolved half was recorded *before* slice 06 built the evolved dataset, by
sequencing ruling; the set-equality verdict in § Resolution rules is this document's, computed
offline against the committed artifact.

**Measured run 2 — the per-use consumption probe.** `exp06b-20260910-120123`,
[`testing/artifacts/exp06b-20260910-120123/use-probe.json`](../../testing/artifacts/exp06b-20260910-120123/use-probe.json)
(sha256 `6a9a83a0…`), 89.6 s, fixture `default`, build 42.20.4, `server_errors []`, doctor
all-`ok`. Script `testing/experiments/s06b_use_probe.py`; harness command `item.use`. Single
verdict, **96/96 fields matched**, no *do not cite* rows; read § 5 of its report for the one gap
(removal on depletion) and `comparison.<item>.recorded_uncompared` for the two fields recorded on
purpose without a comparison.

**Earlier runs cited here** `exp02-20260910-030433` (the measured Salad dish behind the summation,
and the server-owned Cooking perk level — [food-item-model.md](food-item-model.md)),
`exp05-20260910-084109` and `exp05b-20260910-093307` (the item dataset both scans join against —
[food-dataset-notes.md](food-dataset-notes.md)).

**Tooling and prior work in this library** [`data/README.md`](../../data/README.md) § recipes and
§ evolved-recipes (the column authority), `tools/README.md` (`recipe_scan.py`'s invocation),
[food-item-model.md](food-item-model.md) (the summation, the cooking model, the 114-key table),
[food-dataset-notes.md](food-dataset-notes.md) (the item rows and the per-litre fluid rule),
[eating-pipeline.md](eating-pipeline.md) (how any of these numbers reach `Stats` and `Nutrition`),
[`../testing/README.md`](../testing/README.md) (the four harness commands and the two experiment
drivers), [`../decisions.md`](../decisions.md) (the judgment calls behind the schema),
[`docs/superpowers/plans/06-recipes.md`](../superpowers/plans/06-recipes.md) (the plan and its
acceptance results).
