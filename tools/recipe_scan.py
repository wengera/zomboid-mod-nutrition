#!/usr/bin/env python3
"""Vanilla recipe dataset builder, on slice 05's shared reader for the script DSL.

`python tools/recipe_scan.py --out-dir data` parses the 42.20.4 scripts under `media/scripts/`
and writes four files:

* **`data/recipes.{json,csv}`** -- one row per `craftRecipe` block, its inputs and outputs parsed
  line by line, and -- where every consumed item input and every output resolves to a single row
  of `data/food-items.json` -- the nutrition delta the craft moves. See `parse_io` for the
  IO-line grammar, `input_charge` for what one input line really takes out of the world, and
  `nutrition_delta` for the arithmetic and its refusals.
* **`data/recipes.json`'s `replacements`** -- every `ReplaceOn{Cooked,Rotten,Use,Deplete}` link a
  food row declares, with the delta the swap moves. See `replacements`.
* **`data/evolved-recipes.{json,csv}`** -- the 63 `evolvedrecipe` blocks resolved to their
  ingredient lists the way `Item.OnScriptsLoaded` resolves them, each ingredient carrying what it
  contributes to the dish at Cooking 0 and Cooking 10. See `resolve_arms` for the two join arms
  and `contribution` for the summation.

`CSV_HEADER` / `EVOLVED_CSV_HEADER` name the flattened columns of the two CSVs; `RECORD_FIELDS`
and `EVOLVED_RECORD_FIELDS` name the JSON records' own fields. (Slice 06's Task 5 writes the
`data/README.md` section that documents them for a reader; until it lands those five constants
are the reference, not a forward pointer to prose that does not exist yet.)

Stdlib only. The block reader is `food_scan.parse_script` and nothing else: this tool never
walks the DSL itself. What that parser hands over for a recipe is

    craftRecipe MakeToast { time = 20, inputs { item 1 [Base.BreadSlices] flags[ItemCount] } }

as a Block whose `props`/`entries` hold the `Key = Value` lines and whose child blocks'
**`lines`** hold the IO lines -- `item 1 [Base.BreadSlices] flags[ItemCount]` is not a
`Key = Value` line at all, so it is a `lines` entry, and so are an `itemMapper`'s dotted
`Base.X = Base.Y` pairs (`food_scan`'s PROP_RE only accepts identifier keys, which is what keeps
the 56 mappers that name one result twice from collapsing). This module's `_mapper` is the only
place that splits such a line on `=`.

Three shapes in the shipped files are worth knowing before reading the code:

* **An `itemMapper` is `Result = Source`, many-to-one.** `RemoveFurMapper` maps 16 fur sources
  onto 3 crude-leather results (`entities/animals/craftRecipes/recipes_leather_prep.txt:251`),
  so the contract dict `itemMappers[name][result]` keeps only the last source of a repeated
  result; `itemMapperPairs` keeps every line in file order. The literal key `default` is a
  fallback result, not a mapper row, and lives in `itemMapperDefaults` (134 of the 225 mappers).
* **An output may name a mapper instead of a type** (`item 3 mapper:foodType`, 225 lines). Such
  a line resolves to **every** result of that mapper, so its `types` is a set of alternatives --
  which is exactly why it can carry no delta.
* **Absence is null, never 0** -- on a record and in the arithmetic's *inputs*. The one place a
  null becomes a number is a resolvable row that writes no line for one macro
  (`Base.Cornflour2` has a `HungerChange` and no `Calories`): the sum takes 0 there and the
  delta names the row and field in `absentMacros`, so the substitution is never silent.
* **A `-` / `+` line is a SUB-LINE of the input above it**, not an input of its own.
  `CraftRecipe.LoadIO @218-@317` attaches it to the preceding entry as its
  `consumeFromItemScript` / `createToItemScript` and never adds it to `inputs`, and
  `getInputCount()` is `inputs.size()` (`@0-@7 L257`). So a parsed line carries its attached
  lines in `subLines`, `inputCount` is the loader's own count (`MakePizza` 9, not 10;
  `MakeMilkFromPowderBucket` 2, not 3), and the CSV's `inputFluids` / `inputsRaw` still flatten
  them so nothing is hidden from a consumer.
* **An input line's `N` is a count of USES unless `flags[ItemCount]` says items** -- and for a
  `Food` one use is one raw `HungerChange` point, so `item 40 [Base.MincedMeat]` is one whole
  tub and `item 10 [Base.Icecream]` is a third of one. `input_charge` is the whole rule and
  `.superpowers/sdd/06-recipes/q-itemcount-notes.md` is the jar read behind it.

Two type universes, deliberately kept apart, because a `fluid_container` row is a vessel whose
nutrition is its fluid's, per litre:

* **`datasetTypes`** (and `meta.counts.recipesTouchingDatasetRow`, 413) -- every IO type of the
  recipe that is a row of `data/food-items.json` **at all**, vessels included.
* **`foodItemTypes`** (and `meta.counts.recipesTouchingFood`, 375) -- the `food` / `drainable`
  subset of the same list, i.e. the rows a delta may actually weigh (`food_item_ids`).

Counts, verified on 42.20.4 (2026-09-10): 969 `craftRecipe` blocks in 74 files, 0 legacy
`recipe` blocks. The 202 `inputs` blocks owned by a `component CraftRecipe` (an entity's own
build recipe, e.g. `entities/admin/entity_piano.txt:38`) are **not** craftRecipes and are not in
this dataset; they are counted in `meta.counts.componentCraftRecipes` because a raw grep of the
scripts for `mode:` or `flags[...]` sees them too. Also 63 `evolvedrecipe` blocks joined by 374
`EvolvedRecipe` carriers over 6902 (key, recipe) joins into 6881 ingredient rows, and 163
`ReplaceOn*` links (3 cooked, 8 rotten, 110 use, 42 deplete).
"""
import argparse, csv, datetime, json, math, os, re, sys

import food_scan

MEDIA = food_scan.MEDIA
# The stamp the datasets carry: the build these scripts come from and the jar its key tables were
# read from. Both halves are `food_scan`'s, so the two datasets can never claim different builds.
BUILD = "%s (%s)" % (food_scan.BUILD, food_scan.JAR_HASH)
SCRIPTS = "scripts"                            # under MEDIA; the whole tree is walked
GENERATED = "scripts/generated"                # source paths are relative to here when under it
FOOD_TXT = "items/food.txt"                    # rel path of the file `meta.foodJoinMisses` joins

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOOD_JSON = os.path.join(_REPO, "data", "food-items.json")
OUT_DIR = os.path.join(_REPO, "data")

# Ruling R2: the plan's contract names script keys; `data/food-items.json` carries lowercase
# typed fields. Every read of a food row goes through `food_value`, which resolves the name here
# first and falls back to the raw script key, so a caller holding either shape gets the value.
# A name this dataset does not carry maps to None and its dependent output is emitted as null.
FOOD_FIELDS = {
    "Calories": "calories",
    "Carbohydrates": "carbohydrates",
    "Lipids": "lipids",
    "Proteins": "proteins",
    "HungerChange": "hunger_change",
    "ThirstChange": "thirst_change",
    "EvolvedRecipe": "evolved_recipe",
    "EvolvedRecipeName": "evolved_recipe_name",
    "Spice": "spice",
    "IsCookable": "is_cookable",
    "MinutesToCook": "minutes_to_cook",
    "MinutesToBurn": "minutes_to_burn",
    "ReplaceOnCooked": "replace_on_cooked",
    "ReplaceOnRotten": "replace_on_rotten",
    "ReplaceOnUse": "replace_on_use",
    "ReplaceOnDeplete": "replace_on_deplete",
    "DaysFresh": "days_fresh",
    "DaysTotallyRotten": "days_totally_rotten",
    "Tags": "tags",
    "SourceFile": "source_file",
    "SourceLine": "source_line",
}

# The six the delta moves, as `(script key, delta field)`. The four macros are what `Nutrition`
# stores; hunger and thirst are the two `Stats` the same eat/drink path spends. Script units on
# both sides, the way data/README.md § Per litre, not per item states them -- no `/100`.
MACROS = (("Calories", "calories"), ("Carbohydrates", "carbohydrates"), ("Lipids", "lipids"),
          ("Proteins", "proteins"), ("HungerChange", "hungerChange"),
          ("ThirstChange", "thirstChange"))

# Ruling R3: which `nutrition_basis` values a delta may read, and what a row is refused for.
# `per_item` contributes; a `per_litre` row is a drink whose numbers are per litre of its fluid,
# and a row with no basis carries no nutrition key at all. A mapping with no `nutrition_basis`
# key whatsoever is a bare macro dict (a test fixture, or a caller's own table) and is read as
# `per_item` -- absence of the column, not an empty column.
BASIS_REFUSALS = {"per_litre": "fluid-sourced", None: "no-nutrition", "": "no-nutrition"}

# Which `data/food-items.json` kinds count as a *food item* when a count says "food": the eaten
# and the drainable rows, never a `fluid_container` (see `food_item_ids`).
FOOD_KINDS = ("food", "drainable")

# The one input flag that moves nutrition rather than gating or decorating: with it, each output
# takes `1/outputCount` of the *consumed instance's* macros instead of its own script's
# (`createOutputItems @1096-@1143 L1542-L1544` -> `Food.copyFoodFromSplit @0-@3 L2704` ->
# `copyNutritionFromRatio @0-@86 L2677-L2685`), so the craft is a split and conserves. The
# similarly named `InheritFoodAge` copies **age only** (`@1192-@1311 L1550-L1562`,
# `Food.copyAgeFrom`) and is NOT this flag -- `ScoopIceCream` carries it and really does move
# -105 kcal.
INHERIT_FOOD_FLAG = "InheritFood"

# Every field of a parsed IO line, in record order. A line that writes none of a token still
# carries the field: null for a scalar, `[]` for a list, `false` for the `overlayMapper` flag.
IO_FIELDS = ("kind", "amount", "variable", "types", "tags", "categories", "mode", "flags",
             "mappers", "mapper", "overlayMapper", "extras", "consumed", "amountIsItemCount",
             "amountUses", "subLines", "raw")

# `(record field, script key, typer)` for the keys a field claims. Everything else a recipe
# writes stays raw in `props` -- in 42.20.4 that is `overlayStyle`, `OnTest`, `recipeGroup`,
# `Icon`, `ResearchSkillLevel` and `ResearchAny`.
FIELD_KEYS = (
    ("time", "time", "int"),
    ("timedAction", "timedAction", "text"),
    ("category", "category", "text"),
    ("tags", "Tags", "list"),
    ("skillRequired", "SkillRequired", "list"),
    ("xpAward", "xpAward", "list"),
    ("needToBeLearn", "NeedToBeLearn", "bool"),
    ("autoLearnAll", "AutoLearnAll", "list"),
    ("autoLearnAny", "AutoLearnAny", "list"),
    ("allowBatchCraft", "AllowBatchCraft", "bool"),
    ("metaRecipe", "MetaRecipe", "text"),
    ("onCreate", "OnCreate", "text"),
    ("tooltip", "Tooltip", "text"),
)

# The JSON record's field order. `datasetTypes` / `foodItemTypes` / `delta` / `deltaReason` are
# the join `build` adds; they are present (as null) on a record `parse_text` alone produced, so
# every record has every field whatever built it. `inputCount` and `split` are not -- they are
# readings of the block itself, so `build_recipe` fills them and no food table is needed.
RECORD_FIELDS = (("name", "module", "sourceFile", "sourceLine")
                 + tuple(field for field, _key, _typer in FIELD_KEYS)
                 + ("inputs", "inputCount", "outputs", "itemMappers", "itemMapperPairs",
                    "itemMapperDefaults", "overlayMapper", "props", "fluidIO", "split",
                    "datasetTypes", "foodItemTypes", "delta", "deltaReason"))

# The CSV's columns: the record's own names, with the structured fields flattened. `inputsRaw` /
# `outputsRaw` join the IO lines with ` | ` (a parent's `subLines` follow it, so the flat file
# still shows every line the block writes; no vanilla IO line contains a pipe), every other list
# column joins with `;`, and the six `delta*` columns are empty when `deltaReason` says why.
# `deltaAbsentMacros` is the delta's own `absentMacros`, so the null-for-0 substitution is
# visible here too; the delta's `notes` and `destroyWaste` are JSON-only (a dict and a sentence).
CSV_HEADER = ["name", "module", "category", "time", "timedAction", "tags", "skillRequired",
              "xpAward", "needToBeLearn", "autoLearnAll", "autoLearnAny", "allowBatchCraft",
              "metaRecipe", "onCreate", "tooltip", "inputTypes", "inputTags", "inputFluids",
              "inputCount", "outputTypes", "itemMappers", "fluidIO", "split", "datasetTypes",
              "foodItemTypes", "deltaCalories", "deltaCarbohydrates", "deltaLipids",
              "deltaProteins", "deltaHungerChange", "deltaThirstChange", "deltaAbsentMacros",
              "deltaReason", "inputsRaw", "outputsRaw", "sourceFile", "sourceLine"]

_BRACKET_RE = re.compile(r"^([A-Za-z]\w*)\[(.*)\]$")     # tags[…], flags[…], variable[…]
_TYPES_RE = re.compile(r"^\[(.*)\]$")                    # [Base.Thread;Base.Twine]
_NUMBER_RE = re.compile(r"^[-+]?[0-9]*\.?[0-9]+$")
_COUNT_PREFIX_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)?:")  # `2:Base.BurlapPiece`, 86 entries
_LIST_TOKENS = {"tags": "tags", "flags": "flags", "mappers": "mappers", "categories": "categories"}


def _split(raw):
    """A `;`-separated bracket list or key value, with the empty parts dropped."""
    return [part for part in (p.strip() for p in raw.split(";")) if part]


def _type_id(entry):
    """One entry of a `[…]` type list, without the per-alternative count 86 entries carry.

    `[Base.BurlapPiece;2:Base.CottonBalls]` offers two ways to pay for the same craft and the
    second costs 2 rather than the line's amount. The dataset keeps the **id** (a food join needs
    it) and the whole line stays in the row's `raw`, which is where that count is still readable.
    """
    return _COUNT_PREFIX_RE.sub("", entry.strip())


def parse_io(line):
    """One `inputs` / `outputs` line, as a dict of `IO_FIELDS`.

    The grammar, verified over all 4398 IO lines of 42.20.4:

        item <N|variable[a:b]> [<Type;Type>]|tags[<t;t>]|<Type>|mapper:<name>
                               [mode:X] [flags[…]] [mappers[…]] [overlayMapper]
        -fluid <N> [<Fluid;Fluid>]|categories[<c;c>] [mode:mixture] [flags[…]]

    with the tokens after the amount in any order -- 34 distinct token shapes occur. `types` is
    the bracketed list, or an output's bare trailing token for one type (`item 1 Base.Toast`);
    `mapper` is the output form, which `parse_text` resolves to that mapper's results. A leading
    `-` marks a fluid the craft draws off -- every one of the 55 fluid lines writes it -- and the
    loader reads it as a SUB-LINE of the entry above (`attach_sub_lines`), not as an input of its
    own; the sign is stripped from `kind` and survives in `raw`. The **consumption rule is the
    mode**: `consumed = mode != "keep"`, so a line with no mode at all (an ingredient) and a
    `mode:destroy` line both consume, and only `mode:keep` (a tool, 1366 of the 1634 modes) does
    not. `energy` lines, and a `fluid` line without the `-`, do not occur in vanilla; a leading
    token that is neither `item` nor `fluid` is kept verbatim as `kind` rather than guessed at.
    An unrecognised token lands in `extras`, so nothing is dropped in silence.

    `amountIsItemCount` / `amountUses` split the amount's two readings, so the delta arithmetic
    is auditable from the row alone: with `flags[ItemCount]` `N` counts whole items and
    `amountUses` is null, without it `N` counts **uses** and `amountUses` is that number
    (`consumeInputFromItems @372 L1089`: `taken = isItemCount() ? 1f : item.getCurrentUses()`).
    Both describe the line as written -- an OUTPUT amount is always an item count whatever the
    line's flags say (`createOutputItems @39-@116 L1408-L1418`), which is `nutrition_delta`'s
    business and not the grammar's.
    """
    raw = line.strip()
    raw = raw[:-1].rstrip() if raw.endswith(",") else raw     # `lines` are stripped already; mods
    record = dict.fromkeys(IO_FIELDS)
    record.update({"types": [], "tags": [], "categories": [], "flags": [], "mappers": [],
                   "extras": [], "overlayMapper": False, "subLines": [], "raw": raw})
    parts = raw.split()
    head = parts[0] if parts else ""
    record["kind"] = head.lstrip("-+")
    rest = parts[1:]
    if rest and _NUMBER_RE.match(rest[0]):
        record["amount"] = float(rest[0])
        rest = rest[1:]
    for token in rest:
        bracket = _BRACKET_RE.match(token)
        types = _TYPES_RE.match(token)
        if bracket and bracket.group(1) == "variable":
            record["variable"] = bracket.group(2).strip()     # `1:20`; the amount stays null
        elif bracket and bracket.group(1) in _LIST_TOKENS:
            record[_LIST_TOKENS[bracket.group(1)]] = _split(bracket.group(2))
        elif types:
            record["types"] = [_type_id(e) for e in _split(types.group(1))]
        elif token.startswith("mode:"):
            record["mode"] = token[len("mode:"):]
        elif token.startswith("mapper:"):
            record["mapper"] = token[len("mapper:"):]
        elif token == "overlayMapper":                        # 3 input lines name the block bare
            record["overlayMapper"] = True
        elif "." in token:                                    # `item 1 Base.Toast`, a single type
            record["types"] = [_type_id(token)]
        else:
            record["extras"].append(token)
    record["consumed"] = record["mode"] != "keep"
    record["amountIsItemCount"] = "ItemCount" in record["flags"]
    record["amountUses"] = None if record["amountIsItemCount"] else record["amount"]
    return record


def is_sub_line(raw):
    """True for a `-`/`+` prefixed IO line -- one the loader hangs off the entry above it.

    `CraftRecipe.LoadIO @218-@317`: a `-` line becomes the preceding entry's
    `consumeFromItemScript` and a `+` line its `createToItemScript`; either way it is appended to
    `ioLines` and **not** to `inputs`, so `getInputCount()` (`inputs.size()`, `@0-@7 L257`) never
    counts it. 42.20.4 writes 55 such lines, all of them `-fluid` inside an `inputs` block.
    """
    return raw.lstrip().startswith(("-", "+"))


def attach_sub_lines(lines):
    """One side's parsed lines with every sub-line moved into the `subLines` of the line above.

    A leading sub-line has nothing to attach to (none in 42.20.4) and is kept as an entry of its
    own rather than dropped -- the loader would hang it off `inputs.get(-1)` and throw, so there
    is no behaviour to copy and losing the line would be worse than showing it.
    """
    out = []
    for line in lines:
        if is_sub_line(line["raw"]) and out:
            out[-1]["subLines"].append(line)
        else:
            out.append(line)
    return out


def io_lines(recipe, side):
    """Every parsed line of one side, sub-lines included, in file order -- the flat reading.

    The record nests sub-lines under their parent because that is what the loader does; a
    consumer that just wants "every line this block writes" (the CSV's `inputsRaw`, the fluid
    list, the type census) walks this instead of re-implementing the nesting.
    """
    for line in recipe[side] or ():
        yield line
        for sub in line["subLines"]:
            yield sub


def split_lines(recipe):
    """The input lines flagged `InheritFood` -- the ones whose macros pass into the outputs.

    A recipe with any of them is a **split**: each output is built from the result script and
    then overwritten with `1/outputCount` of the consumed instance's own nutrition
    (`createOutputItems @1096-@1143 L1542-L1544` -> `Food.copyFoodFromSplit`), so the outputs
    add back up to exactly what the flagged input gave and the craft conserves by construction.
    17 shipped lines carry the flag; 8 of them are on a recipe whose delta resolves.
    """
    return [line for line in io_lines(recipe, "inputs")
            if INHERIT_FOOD_FLAG in line["flags"]]


def _last(block, key):
    """The last value written for `key` -- what the loader keeps -- or None if it never is.

    Through `food_scan.values`, so the match is the loader's `equalsIgnoreCase` one: a mod
    writing `Time` reaches the same field the shipped `time` does.
    """
    written = food_scan.values(block, key)
    return written[-1] if written else None


def _typed(raw, typer):
    """A script value in the field's type. A value that will not parse is kept as its string."""
    if raw is None:
        return None
    if typer == "list":
        return _split(raw)
    if typer == "bool":                        # Boolean.parseBoolean: only the literal `true`
        return raw.strip().lower() == "true"
    if typer in ("int", "float"):
        try:
            return int(raw.strip()) if typer == "int" else float(raw.strip())
        except ValueError:
            return raw
    return raw


def _mapper(block):
    """One `itemMapper` / `overlayMapper` block, as `(pairs, default)`.

    The pairs are `[[result, source], …]` in file order, read off `lines` because a dotted key is
    not a `Key = Value` line to `food_scan`'s PROP_RE -- which is what keeps the 56 mappers that
    write one result twice from collapsing to their last source. `default` **is** an identifier
    key, so it arrives as a prop; it is a fallback result rather than a mapper row and is
    returned separately.
    """
    pairs = []
    for line in block["lines"]:
        left, sep, right = line.partition("=")
        if sep:
            pairs.append([left.strip(), right.strip()])
    return pairs, _last(block, "default")


def build_recipe(block):
    """One `craftRecipe` Block as a record of `RECORD_FIELDS` (no food join yet)."""
    record = dict.fromkeys(RECORD_FIELDS)
    record.update({"name": block["name"], "module": block["module"], "sourceFile": block["file"],
                   "sourceLine": block["line"], "itemMappers": {}, "itemMapperPairs": {},
                   "itemMapperDefaults": {}, "props": {}})
    claimed = set()
    for field, key, typer in FIELD_KEYS:
        record[field] = _typed(_last(block, key), typer)
        claimed.add(key.lower())
    for key, raw in block["entries"]:
        if key.lower() not in claimed:                        # `overlayStyle`, `OnTest`, `Icon`, …
            record["props"][key] = raw

    for child in block["blocks"]:
        if child["kind"] == "itemMapper":
            pairs, default = _mapper(child)
            record["itemMapperPairs"][child["name"]] = pairs
            record["itemMappers"][child["name"]] = {result: source for result, source in pairs}
            record["itemMapperDefaults"][child["name"]] = default
        elif child["kind"] == "block" and child["name"] == "overlayMapper":
            pairs, default = _mapper(child)
            record["overlayMapper"] = {"default": default, "pairs": pairs}

    for side in ("inputs", "outputs"):
        child = food_scan.named(block, side)
        # `null` is no such block (11 recipes ship none), `[]` is a block that is really empty
        # (`MakeMilkFromPowderBucket`) -- the same distinction `food_scan`'s `fluid_ids` draws.
        record[side] = (None if child is None
                        else attach_sub_lines([parse_io(line) for line in child["lines"]]))
    # `getInputCount()` is `inputs.size()`, which is this list AFTER the sub-lines moved into
    # their parents -- the number the live harness reads back (Task 4, exp06-20260910-112726).
    record["inputCount"] = None if record["inputs"] is None else len(record["inputs"])

    for line in record["outputs"] or ():
        if line["mapper"] and not line["types"]:
            pairs = record["itemMapperPairs"].get(line["mapper"], [])
            seen, resolved = set(), []
            for result, _source in pairs:                     # every result, in file order, once
                if result not in seen:
                    seen.add(result)
                    resolved.append(result)
            line["types"] = resolved
    record["fluidIO"] = any(line["kind"] == "fluid"
                            for side in ("inputs", "outputs")
                            for line in io_lines(record, side))
    record["split"] = bool(split_lines(record))
    return record


def parse_text(text, path=""):
    """Every `craftRecipe` in one script file, in file order, as records."""
    return [build_recipe(block)
            for block in food_scan.iter_blocks(food_scan.parse_script(text, path))
            if block["kind"] == "craftRecipe"]


def food_value(row, name):
    """A food row's value for the plan's `name`, whichever shape the row is in (Ruling R2).

    `data/food-items.json` rows carry `FOOD_FIELDS[name]`; a caller's own table may carry the
    script key itself. A name neither shape holds is None -- absent, never 0.
    """
    field = FOOD_FIELDS.get(name)
    if field is not None and field in row:
        return row[field]
    return row.get(name)


def _refusal(row):
    """Ruling R3: why this food row may not contribute, or None when it may.

    A mapping with no `nutrition_basis` key at all is a bare macro table, read as `per_item`.
    """
    if "nutrition_basis" not in row:
        return None
    return BASIS_REFUSALS.get(row["nutrition_basis"])


def _line_row(line, food):
    """`(row, None)` for an IO line that resolves to one food row, or `(None, why)`."""
    if line["variable"] is not None or line["amount"] is None:
        return None, "variable-amount"
    if line["types"] == ["*"]:
        return None, "wildcard"
    if len(line["types"]) > 1:
        return None, "multi-type"
    if not line["types"]:
        return None, "tags-only" if (line["tags"] or line["categories"]) else "no-type"
    row = food.get(line["types"][0])
    if row is None:
        return None, "not-in-dataset"
    return (row, None) if _refusal(row) is None else (None, _refusal(row))


def delta_terms(recipe, food):
    """`(terms, blockers)` -- the `(sign, line, row)` triples a delta sums, and what stopped it.

    A fluid line carries no macros (a fluid's nutrition is per litre of *fluid*) and a tool
    (`mode:keep`) is not consumed, so neither is a term. Everything else must resolve to one
    food row, or it is a blocker and there is no delta at all. Sub-lines are walked too (they
    are the fluid lines, so they never become terms) -- a blocker must not go unseen because the
    loader hung it off the entry above.
    """
    terms, blockers = [], []
    for side, sign in (("inputs", -1.0), ("outputs", 1.0)):
        for line in io_lines(recipe, side):
            if line["kind"] != "item" or (sign < 0 and not line["consumed"]):
                continue
            row, why = _line_row(line, food)
            if row is None:
                blockers.append({"side": side, "why": why, "raw": line["raw"]})
            else:
                terms.append((sign, line, row))
    return terms, blockers


def _row_kind(row):
    """`data/food-items.json`'s `kind` for the row, or the reading a bare macro table gets.

    A caller's own table (a test fixture, the plan's contract dict) has no `kind` column. Only a
    `Food` carries a `HungerChange` at all, so a row that writes one is read as a food and
    anything else as a plain one-use item -- never as a drainable, which no bare table can claim.
    """
    kind = row.get("kind")
    if kind is not None:
        return kind
    return "food" if food_value(row, "HungerChange") is not None else None


def uses_per_item(row):
    """`|HungerChange|` when the row's uses really are hunger points, else None.

    `Food.getMaxUses @11-@23 L2210-L2214` is `baseHunger == 0 ? 1 : (int)|baseHunger * 100|` and
    `baseHunger` is the script's `HungerChange / 100`, so one use is one raw `HungerChange` point
    -- but a food that writes **no** `HungerChange` (or a 0 one) holds exactly one use, and its
    uses are whole items. `|HungerChange| <= 1` lands in the same place, which is what the game's
    own `InputScript.isUsesPartialItem @0-@85 L182-L191` says when it demands `> 1f`.
    """
    hunger = food_value(row, "HungerChange")
    if hunger is None:
        return None
    return abs(hunger) if abs(hunger) > 1 else None


def input_charge(line, row):
    """What one consumed input line takes out of the world, as `(charged, wasted, notes)`.

    Both numbers are multiples of the row's own per-item macros, so `charged * macros(T)` is what
    the delta subtracts. The rule is `q-itemcount-notes.md` § What the dataset should compute,
    which is a read of `consumeInputFromItems @372 L1089` (`taken = isItemCount() ? 1f :
    item.getCurrentUses()`) and `processDestroyAndUsedItems @337-@490 L563-L577` ->
    `ItemUser.UseItem @28 L37-38` -> `Food.setCurrentUses @23-@35 L2228-L2233` ->
    `consumeHunger` -> `multiplyFoodValues(1 - consumed/|hungChange|)`:

    * `flags[ItemCount]` -- `N` whole items.
    * a `food` row whose `|HungerChange| > 1` -- `N` hunger points, so `N / |HungerChange|` of
      one item (`item 40 [Base.MincedMeat]` is one whole tub, `item 10 [Base.Icecream]` a third).
    * a `food` row that writes no usable `HungerChange` -- `getMaxUses` is 1, so `N` items, and
      the note says the uses scale was unreadable rather than leaving that silent.
    * a `drainable` row -- `N` is `N x UseDelta` of a bar and the dataset carries no `UseDelta`
      column, so the line charges **no macros at all** and says so.
    * anything else -- one use is the whole item, so `N` items.

    `mode:destroy` then annihilates whatever is left of the items it touched
    (`UseItem @260 L66-67` -> `RemoveItem`), so a line that charged a fraction is rounded up to
    the whole items it destroyed and the rounding is returned as `wasted`. The `ItemCount` branch
    already charges whole items and never wastes.
    """
    amount, item_id, notes = line["amount"], line["types"][0], []
    kind = _row_kind(row)
    if line["amountIsItemCount"]:
        items = amount
    elif kind == "drainable":
        items = 0.0
        notes.append("drainable input: %s uses are UseDelta steps of a bar, not nutrition "
                     "(consumeInputItemUsesInternal @0-@125 L960-L988), so the line charges "
                     "no macros" % item_id)
    elif kind == "food" and uses_per_item(row) is not None:
        items = amount / uses_per_item(row)
    elif kind == "food":
        items = amount
        notes.append("no-hunger-scale: %s writes no usable HungerChange, so Food.getMaxUses "
                     "(@11-@23 L2210-L2214, baseHunger == 0 ? 1) makes one use the whole item"
                     % item_id)
    else:
        items = amount
    wasted = 0.0
    if line["mode"] == "destroy" and not line["amountIsItemCount"]:
        # `RemoveItem` deletes the item whatever fraction of it the line paid for, so the honest
        # figure is the whole items destroyed; at least one, since a destroy line that selected
        # nothing could not have run. `q-itemcount-notes.md` § Open 3 is the same recommendation.
        whole = max(float(math.ceil(round(items, 9))), 1.0)
        if whole > items:
            notes.append("mode:destroy on %s: the line pays for %.6g item(s) and RemoveItem "
                         "(UseItem @260 L66-67) deletes %.6g, so the whole item is charged and "
                         "the difference is in destroyWaste" % (item_id, items, whole))
            wasted, items = whole - items, whole
    return items, wasted, notes


def nutrition_delta(recipe, food):
    """What this craft moves: Σ(outputs × item count) − Σ(what the consumed inputs really cost).

    `food` is `{id: row}` -- `data/food-items.json`'s items, or any table `food_value` can read.
    An OUTPUT's `N` is always a number of item instances (`createOutputItems @39-@116
    L1408-L1418` loops `N` times) and each instance carries the result script's own macros; an
    INPUT's `N` is a count of uses unless `flags[ItemCount]` says items, which is `input_charge`.
    Fluid lines carry no macros (a fluid's nutrition is per litre of *fluid*, not of the craft),
    so they are skipped; the row still says `fluidIO`. Tools (`mode:keep`) are not consumed and
    so are not weighed either.

    A **split** (an input flagged `InheritFood`) is zero by construction: the outputs are
    overwritten with `1/outputCount` of that input's consumed macros, so the flagged input and
    every output drop out of the sum and only any *other* consumed input can move the total.
    Vanilla's 8 resolvable splits have no other input, so all eight are exactly 0.

    Returns the six-macro dict plus `absentMacros`, `destroyWaste` and `notes`, or
    `{"reason", "blockers"}` when the sum would have to guess: a recipe with no outputs to weigh
    against, a variable amount, a wildcard or multi-type or tag-only line, a type no food row
    carries, or a row Ruling R3 refuses (a drink, or an item with no nutrition key at all). The
    reason names the offending lines verbatim, so a refusal can be checked against the file
    without re-deriving it.
    """
    if not recipe["outputs"]:
        return {"reason": "no-outputs", "blockers": []}
    terms, blockers = delta_terms(recipe, food)
    if blockers:
        return {"reason": " ; ".join("%s: %s" % (b["why"], b["raw"]) for b in blockers),
                "blockers": blockers}

    split = bool(split_lines(recipe))
    weighed, notes, wasted_any = [], set(), False
    if split:
        notes.add("split: an input carries %s, so each output is overwritten with 1/outputCount "
                  "of the consumed instance's own macros (createOutputItems @1096-@1143 "
                  "L1542-L1544 -> Food.copyFoodFromSplit @0-@3 L2704) -- that input and the "
                  "outputs cancel and the delta is 0 by construction" % INHERIT_FOOD_FLAG)
    for sign, line, row in terms:
        if sign > 0:                                   # an output N is ALWAYS an item count
            weighed.append((sign, line, row, 0.0 if split else line["amount"], 0.0))
            continue
        if split and INHERIT_FOOD_FLAG in line["flags"]:
            weighed.append((sign, line, row, 0.0, 0.0))
            continue
        charged, wasted, line_notes = input_charge(line, row)
        notes.update(line_notes)
        wasted_any = wasted_any or bool(wasted)
        weighed.append((sign, line, row, charged, wasted))

    delta, absent, waste = {}, set(), {}
    for key, field in MACROS:
        total, lost = 0.0, 0.0
        for sign, line, row, weight, wasted in weighed:
            value = food_value(row, key)
            if value is None:
                # The row is in the dataset and carries nutrition, but writes no line for THIS
                # key. The dataset reports that as null; the sum has to use a number, so it uses
                # the loader's own default of 0 -- and says so, per row and field.
                absent.add("%s:%s" % (line["types"][0], field))
                value = 0.0
            total += sign * value * weight
            lost += value * wasted
        delta[field] = round(total, 6)
        waste[field] = round(lost, 6)
    delta["absentMacros"] = sorted(absent)
    # the macros of the part `mode:destroy` threw away without spending a use on it -- null when
    # no line wasted anything, so the field is never a row of meaningless zeroes
    delta["destroyWaste"] = waste if wasted_any else None
    delta["notes"] = sorted(notes)
    return delta


def load_food(path=FOOD_JSON):
    """`data/food-items.json` as `({id: row}, meta)`; the fluid records are not joined here."""
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return {row["id"]: row for row in payload["items"]}, payload["meta"]


def dataset_types(recipe, food):
    """Every IO type of this recipe that is a row of `data/food-items.json` **at all**.

    Sorted and deduplicated, tools and multi-type alternatives included. This is the wider of
    the module docstring's two universes: it counts a `fluid_container` row (`Base.WaterBottle`)
    as much as an apple, so `foodItemTypes` -- not this -- is the list a nutrition question
    wants. Was called `foodTypes` through Task 3; renamed so the two cannot be confused.
    """
    hits = set()
    for side in ("inputs", "outputs"):
        for line in io_lines(recipe, side):
            if line["kind"] != "item":
                continue
            hits.update(t for t in line["types"] if t in food)
    return sorted(hits)


def food_item_types(recipe, food):
    """`dataset_types` narrowed to the `food` / `drainable` rows -- see `food_item_ids`."""
    items = food_item_ids(food)
    return [t for t in dataset_types(recipe, food) if t in items]


def food_item_ids(food):
    """The dataset ids that are *food items*: the `food` and `drainable` rows, never a container.

    A `fluid_container` row is a vessel whose nutrition is the fluid's, per litre (Ruling R3 and
    data/README.md § Per litre, not per item), so counting `Base.WaterBottle` as a food item a
    recipe produced would mean counting a litre of water as the bottle's calories. The delta
    still *reads* those rows -- and refuses them by name -- which is why `food` keeps all 1005.
    """
    return {item_id for item_id, row in food.items() if row.get("kind") in FOOD_KINDS}


# ---------------------------------------------------------------------------------------------
# Evolved recipes: the `evolvedrecipe` blocks, the keys that join an item to them, and what one
# ingredient contributes to the dish at Cooking 0 and 10.
# ---------------------------------------------------------------------------------------------

# `Item.DoParam` rewrites five `EvolvedRecipe` keys *before* the key is ever looked up
# (food-item-model.md § Key reference, `EvolvedRecipe` row). The table is exact, not folded:
# vanilla writes `RicePan` 3x, `RicePot` 1x and `Roasted Vegetables` 1x, and each of those keys
# would otherwise reach one recipe or none instead of the four its template names.
EVOLVED_ALIASES = {"RicePot": "Rice", "RicePan": "Rice", "PastaPot": "Pasta",
                   "PastaPan": "Pasta", "Roasted Vegetables": "Stir fry"}

# `(record field, script key, typer)` for an `evolvedrecipe` block. The ten keys vanilla writes
# plus `IsHidden` / `AllowFrozenItem`, which the loader reads and no shipped block sets.
EVOLVED_FIELD_KEYS = (
    ("displayName", "Name", "text"),
    ("baseItem", "BaseItem", "text"),
    ("resultItem", "ResultItem", "text"),
    ("template", "Template", "text"),
    ("maxItems", "MaxItems", "int"),
    ("cookable", "Cookable", "bool"),
    ("canAddSpicesEmpty", "CanAddSpicesEmpty", "bool"),
    ("addIngredientIfCooked", "AddIngredientIfCooked", "bool"),
    ("addIngredientSound", "AddIngredientSound", "text"),
    ("minimumWater", "MinimumWater", "float"),
    ("isHidden", "IsHidden", "bool"),
    ("allowFrozenItem", "AllowFrozenItem", "bool"),
)

EVOLVED_RECORD_FIELDS = (("name", "module", "sourceFile", "sourceLine")
                         + tuple(field for field, _key, _typer in EVOLVED_FIELD_KEYS)
                         + ("props", "ingredients"))

# One ingredient row: which item, the key that joined it, the keys that joined it *again*
# (21 vanilla pairs), and its contribution at the two cooking levels. `absentMacros` names the
# macros the item writes no line for -- `addItem` multiplies a Java float that defaults to 0, so
# such a contribution really is 0.0 in game, but the row says which zeroes are that and which are
# a measured 0 (the same distinction `nutrition_delta`'s `absentMacros` draws). It is
# level-independent, so it sits on the row rather than in both contributions.
EVOLVED_INGREDIENT_FIELDS = ("item", "key", "duplicateKeys", "use", "requiresCooked", "spice",
                             "evolvedRecipeName", "resolvedVia", "absentMacros", "sourceFile",
                             "sourceLine", "at0", "at10")

# The five macros `EvolvedRecipe.addItem` moves, as `(script key, contribution field)`.
CONTRIBUTION_MACROS = (("Calories", "calories"), ("Carbohydrates", "carbohydrates"),
                       ("Lipids", "lipids"), ("Proteins", "proteins"),
                       ("ThirstChange", "thirstChange"))

CONTRIBUTION_FIELDS = (("use", "hunger", "hungerAfterSkill", "share", "skillBonus",
                        "hungerClamped", "spice", "reason", "note")
                       + tuple(field for _key, field in CONTRIBUTION_MACROS))

# The two levels the dataset tabulates: an unskilled cook and a maxed one.
COOKING_LEVELS = (0, 10)

EVOLVED_CSV_HEADER = ["recipe", "resultItem", "item", "use", "requiresCooked", "spice", "share0",
                      "kcal0", "carbs0", "lipids0", "proteins0", "share10", "kcal10"]

_EVOLVED_INT_RE = re.compile(r"^[-+]?[0-9]+$")


def alias(key):
    """An `EvolvedRecipe` key as `Item.DoParam` stores it -- five names are rewritten in place."""
    return EVOLVED_ALIASES.get(key, key)


def _use_amount(raw):
    """`Name:<use>`'s use, in hunger points. `None` when the key writes no number at all."""
    raw = raw.strip()
    if _EVOLVED_INT_RE.match(raw):
        return int(raw)
    try:
        return float(raw)
    except ValueError:
        return None


def parse_evolved_key(value):
    """One `EvolvedRecipe` value as `[(name, use, requiresCooked), …]`, in file order.

    The script writes `Name:<use>[|Cooked]` joined by `;` (`Soup:5;Stew:5;Salad:5`);
    `data/food-items.json` ships that already split into a list (README row 39), and both shapes
    are accepted. `use` is hunger **points** -- `addItem` divides it by 100 (`@518 L333`) -- and a
    name may contain spaces (`Stir fry Griddle Pan:12`), so the number is taken from the **last**
    colon. The `|Cooked` suffix (60 lines / 213 keys of `food.txt`) means the ingredient counts
    only once the item is cooked; the alias table is *not* applied here, so a caller can still see
    the key the file wrote (`alias` is applied when the key is looked up).
    """
    if not value:
        return []
    raw = ";".join(value) if isinstance(value, (list, tuple)) else value
    out = []
    for entry in _split(raw):
        head, _pipe, suffix = entry.partition("|")
        name, sep, amount = head.rpartition(":")
        if not sep:                                    # a key with no `:<use>` at all
            name, amount = head, ""
        out.append((name.strip(), _use_amount(amount), suffix.strip().lower() == "cooked"))
    return out


def _evolved_template(recipe):
    """A recipe's `Template`, from either a record (`template`) or a raw key dict (`Template`)."""
    for key in ("Template", "template"):
        if key in recipe:
            return recipe[key]
    return None


def resolve_arms(key, recipes):
    """`{recipe name: "name"|"template"|"both"}` -- how `key` reaches each recipe it joins.

    `Item.OnScriptsLoaded @0–@234 L3029–L3047` attaches an ingredient through **two** arms: an
    exact-name lookup (`ScriptManager.getEvolvedRecipe`, `@43–@59 L3033–L3035`) and every recipe
    whose `Template` **`equalsIgnoreCase`** the key (`@122–@140 L3039`). Only the template arm
    folds case, which is the whole of `Base.Cinnamon`'s `ConeIceCream:1` against the recipe
    `ConeIcecream`: a case-sensitive expansion loses that pair and calls the key unmatched.
    An unmatched key throws `InvalidParameterException` in-game, so vanilla has none.
    """
    arms = {}
    if key in recipes:
        arms[key] = "name"
    folded = key.lower()
    for name in sorted(recipes):
        template = _evolved_template(recipes[name])
        if template is not None and template.lower() == folded:
            arms[name] = "both" if arms.get(name) == "name" else "template"
    return arms


def resolve_recipes(key, recipes):
    """Every recipe an `EvolvedRecipe` key joins, deduplicated and sorted. See `resolve_arms`."""
    return sorted(resolve_arms(key, recipes))


def contribution(item, use, level):
    """One ingredient's contribution to a dish. Formula: docs/vanilla/food-item-model.md
    § Evolved recipes (EvolvedRecipe.addItem @518-@1294 L333-L415) -- applied here, never
    re-derived, plus the one line that doc omits (`addItem`'s hunger clamp, `@934 L374-376`;
    see `hungerClamped`). Ignores the rotten branch (Cooking >= 7) and the spice branch (a Spice
    ingredient transfers no hunger and no macros); both are flagged on the row instead.

    Three flags carry what the verbatim formula leaves out, so nothing is silently wrong:

    * `spice` -- `Spice = true` sends the ingredient down `addItem @582–@775 L336–L359`, which
      moves no hunger and no macros at all, so the row's `share` is forced to 0.
    * `reason` -- `"no hunger"` for an ingredient whose `HungerChange` is 0 (no denominator, so
      no share), or Ruling R3's refusal for a row whose `nutrition_basis` is not `per_item`
      (a per-litre drink's macros may not be shared out by an item's hunger): the macros are
      then **null**, never 0, and the hunger arithmetic still stands.
    * `hungerClamped` -- `addItem @934 L374-376` clamps `hunger` down to `|HungerChange|` when
      the key asks for more hunger than the ingredient has, **before** the skill reduction. The
      brief's verbatim formula omits that line; fidelity to the loader wins, so the clamp is
      applied here and the flag is kept as the record of which rows it touched. At Cooking 0 the
      two readings agree anyway (`share` caps at 1 either way); at Cooking 10 they do not, and
      the 17 vanilla keys that over-ask -- 59 ingredient rows, `meta.counts.hungerClampRows` --
      are the whole difference. `Base.Cherry`'s `Oatmeal:5` against a hunger of 3 is one:
      `share` is 0.7 at Cooking 10, where the unclamped formula said 1.0.
    """
    hung = abs((food_value(item, "HungerChange") or 0.0) / 100.0)
    asked = use / 100.0
    clamped = bool(hung) and asked > hung
    hunger = hung if clamped else asked        # addItem @934 L374-376, before the skill cut
    after = hunger * (1.0 - 0.03 * level)
    share = min(abs(after / hung), 1.0) if hung else 0.0
    bonus = 1.0 + level / 15.0
    out = {"use": use, "hunger": hunger, "hungerAfterSkill": after,
           "share": share, "skillBonus": bonus, "hungerClamped": clamped,
           "spice": bool(food_value(item, "Spice")), "reason": None, "note": None}
    if not hung:
        out["reason"] = "no hunger"
    if out["spice"]:
        out["share"] = share = 0.0
        out["note"] = "spice branch: no hunger, no macros (addItem @582-@775 L336-L359)"
    refusal = _refusal(item)
    if refusal is not None:
        out["reason"] = refusal
    for src, dst in CONTRIBUTION_MACROS:
        out[dst] = None if refusal else (food_value(item, src) or 0.0) * bonus * share
    return out


def _round(value, places=6):
    """A committed float: rounded so the file diffs, `None` left alone -- absent is never 0."""
    return None if value is None else round(value, places)


def _rounded_contribution(item, use, level):
    """`contribution` with its floats rounded to the six places the datasets carry."""
    out = contribution(item, use, level)
    for field in ("hunger", "hungerAfterSkill", "share", "skillBonus") + tuple(
            field for _key, field in CONTRIBUTION_MACROS):
        out[field] = _round(out[field])
    return out


def build_evolved(block):
    """One `evolvedrecipe` Block as a record of `EVOLVED_RECORD_FIELDS` (no ingredients yet)."""
    record = dict.fromkeys(EVOLVED_RECORD_FIELDS)
    record.update({"name": block["name"], "module": block["module"], "sourceFile": block["file"],
                   "sourceLine": block["line"], "props": {}, "ingredients": []})
    claimed = set()
    for field, key, typer in EVOLVED_FIELD_KEYS:
        record[field] = _typed(_last(block, key), typer)
        claimed.add(key.lower())
    for key, raw in block["entries"]:
        if key.lower() not in claimed:                 # nothing in 42.20.4; a mod's key survives
            record["props"][key] = raw
    return record


def parse_evolved_text(text, path=""):
    """Every `evolvedrecipe` in one script file, in file order, as records."""
    return [build_evolved(block)
            for block in food_scan.iter_blocks(food_scan.parse_script(text, path))
            if block["kind"] == "evolvedrecipe"]


def _merge_via(first, second):
    """Two arms for one (recipe, item) pair: `both` unless they agree."""
    return first if first == second else "both"


def _ingredient(item_id, row, part, use, cooked, via):
    """One `EVOLVED_INGREDIENT_FIELDS` row for a (recipe, item) pair."""
    record = dict.fromkeys(EVOLVED_INGREDIENT_FIELDS)
    record.update({"item": item_id, "key": part, "duplicateKeys": [], "use": use,
                   "requiresCooked": cooked, "spice": bool(food_value(row, "Spice")),
                   "evolvedRecipeName": food_value(row, "EvolvedRecipeName"),
                   "resolvedVia": via, "sourceFile": food_value(row, "SourceFile"),
                   "sourceLine": food_value(row, "SourceLine"),
                   "absentMacros": sorted(dst for src, dst in CONTRIBUTION_MACROS
                                          if food_value(row, src) is None)})
    for level in COOKING_LEVELS:
        record["at%d" % level] = _rounded_contribution(row, use or 0, level)
    return record


def evolved_ingredients(recipes, food):
    """Join every `EvolvedRecipe` carrier onto the recipes its keys reach, in place.

    `recipes` is `{name: record}` from `build_evolved`; `food` is `{id: row}`. Each record's
    `ingredients` is filled with one row per (recipe, item), sorted by item id. Returns
    `(unmatched, census)`.

    A key may reach one recipe **twice** -- `Base.Seasoning_Basil` writes `RicePan:1` (aliased to
    `Rice`) and then `Rice:1`, and `Base.DriedApricots` writes `Pancakes:8` (template) and
    `Waffles:8` (name), both of which land on `Waffles`. There are 21 such joins in 42.20.4 and
    every one of them repeats the same `use`. The loader's map keeps the **last** key written, so
    that is the row's `key`; the collapsed ones are kept in `duplicateKeys`, and the two arms are
    merged (a pair reached by name *and* by template resolves `both`).
    """
    rows, census = {}, {
        "carriers": 0, "carriersFood": 0, "carriersDrainable": 0, "keyParts": 0, "pairs": 0,
        "pairsFromFoodTxt": 0, "ingredients": 0, "duplicateJoins": 0, "unmatchedKeys": 0,
        "aliasedKeyParts": 0, "cookedSuffixes": 0, "spiceIngredients": 0,
        "ingredientsRefusedByBasis": 0, "hungerClampRows": 0, "resolvedViaName": 0,
        "resolvedViaTemplate": 0, "resolvedViaBoth": 0, "distinctKeys": 0,
    }
    unmatched, distinct = [], set()
    for item_id in sorted(food):
        row = food[item_id]
        written = food_value(row, "EvolvedRecipe")
        if not written:
            continue
        census["carriers"] += 1
        kind = row.get("kind")
        if kind == "food":
            census["carriersFood"] += 1
        elif kind == "drainable":
            census["carriersDrainable"] += 1
        from_food_txt = food_value(row, "SourceFile") == "items/food.txt"
        parts = written if isinstance(written, (list, tuple)) else _split(written)
        for part, (name, use, cooked) in ((p, k) for p in parts for k in parse_evolved_key(p)):
            census["keyParts"] += 1
            census["cookedSuffixes"] += 1 if cooked else 0
            key = alias(name)
            census["aliasedKeyParts"] += 1 if key != name else 0
            distinct.add(name)
            arms = resolve_arms(key, recipes)
            if not arms:
                census["unmatchedKeys"] += 1
                unmatched.append({"item": item_id, "key": part, "lookupKey": key,
                                  "sourceFile": food_value(row, "SourceFile"),
                                  "sourceLine": food_value(row, "SourceLine")})
                continue
            for recipe_name in sorted(arms):
                census["pairs"] += 1
                census["pairsFromFoodTxt"] += 1 if from_food_txt else 0
                slot = (recipe_name, item_id)
                previous, via = rows.get(slot), arms[recipe_name]
                if previous is not None:               # the same pair, joined by a second key
                    census["duplicateJoins"] += 1
                    via = _merge_via(previous["resolvedVia"], via)
                rows[slot] = _ingredient(item_id, row, part, use, cooked, via)
                if previous is not None:
                    rows[slot]["duplicateKeys"] = previous["duplicateKeys"] + [previous["key"]]

    for name in recipes:
        recipes[name]["ingredients"] = []
    for slot in sorted(rows):                          # (recipe, item), so each list is by item
        recipes[slot[0]]["ingredients"].append(rows[slot])
    census["distinctKeys"] = len(distinct)
    for record in rows.values():
        census["ingredients"] += 1
        census["spiceIngredients"] += 1 if record["spice"] else 0
        census["hungerClampRows"] += 1 if record["at10"]["hungerClamped"] else 0
        census["resolvedVia" + record["resolvedVia"].capitalize()] += 1
        # Ruling R3, applied to a contribution: only `food` and `drainable` rows carry
        # `EvolvedRecipe` and every one of the 374 is `per_item`, so this stays 0 on vanilla
        census["ingredientsRefusedByBasis"] += 1 if record["at0"]["calories"] is None else 0
    return unmatched, census


def scan_evolved(root=MEDIA):
    """Every `evolvedrecipe` under `<root>/scripts`, as records, plus the files they came from.

    Returns `(recipes, files)`. The `sourceFile` convention is `scan`'s: relative to
    `scripts/generated` when the file is under it, to `scripts` otherwise. 42.20.4 ships 63
    blocks -- 62 in `evolvedrecipes.txt` and `AddBaitToChum` in
    `recipes/recipes_fishing_evolvedrecipe.txt`.
    """
    scripts_root = os.path.join(root, *SCRIPTS.split("/"))
    generated_root = os.path.join(root, *GENERATED.split("/"))
    recipes, files = [], set()
    for dirpath, _dirs, names in os.walk(scripts_root):
        for name in sorted(names):
            if not name.endswith(".txt"):
                continue
            path = os.path.join(dirpath, name)
            base = generated_root if path.startswith(generated_root + os.sep) else scripts_root
            rel = os.path.relpath(path, base).replace("\\", "/")
            with open(path, encoding="utf-8", errors="replace") as handle:
                found = parse_evolved_text(handle.read(), rel)
            if found:
                recipes.extend(found)
                files.add(rel)
    return recipes, sorted(files)


def build_evolved_dataset(root=MEDIA, food_path=FOOD_JSON):
    """Parse, join and stamp the evolved recipes: `(meta, recipes, unmatched)` ready to write."""
    food, food_meta = load_food(food_path)
    parsed, files = scan_evolved(root)
    recipes = sorted(parsed, key=lambda r: r["name"])
    by_name = {}
    for record in recipes:
        by_name.setdefault(record["name"], record)
    unmatched, census = evolved_ingredients(by_name, food)
    counts = dict(census)
    counts["evolvedRecipes"] = len(recipes)
    # a name written twice would shadow the first block the way the loader's map does; none in
    # 42.20.4, and the count says so rather than the dataset silently dropping a recipe
    counts["duplicateRecipeNames"] = len(recipes) - len(by_name)
    meta = {
        "build": BUILD,
        "generated": datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
        "tool": "tools/recipe_scan.py",
        "sources": {
            "scripts": "media/" + SCRIPTS,
            "files": files,
            "food_items": {"path": os.path.relpath(food_path, _REPO).replace("\\", "/"),
                           "build": food_meta.get("build"),
                           "jar_hash": food_meta.get("jar_hash"),
                           "generated": food_meta.get("generated")},
        },
        "counts": counts,
        "cookingLevels": list(COOKING_LEVELS),
    }
    return meta, recipes, unmatched


# ---------------------------------------------------------------------------------------------
# `ReplaceOn*`: the four one-for-one item swaps a food row can declare.
# ---------------------------------------------------------------------------------------------

# `(script key, trigger)` in the order the links are written. Semantics, all from
# food-item-model.md § Cooking / § Key reference:
#   cooked  -- on the cook transition and **only if not rotten**: each name is `AddItem`-ed with
#              `copyConditionStatesFrom(this)`, the original is removed and `Food.update`
#              *returns*, so the item is replaced and never flagged cooked (`@224–@412 L398–L421`)
#   rotten  -- `ReplaceOnRotten` makes `updateRotting` age the item every tick and, once rotten,
#              create the replacement, copy `age` + condition states and destroy the original
#              (`Food.updateRotting @20–@226 L662–L694`); `updateRotting` returns immediately on
#              any MP client, so that swap is server-only
#   use     -- the leftover container when the item is consumed (also the weight floor in `Eat`'s
#              custom-weight branch)
#   deplete -- what a drainable becomes when it runs out
REPLACEMENT_TRIGGERS = (("ReplaceOnCooked", "cooked"), ("ReplaceOnRotten", "rotten"),
                        ("ReplaceOnUse", "use"), ("ReplaceOnDeplete", "deplete"))
_TRIGGER_ORDER = {trigger: n for n, (_key, trigger) in enumerate(REPLACEMENT_TRIGGERS)}

REPLACEMENT_FIELDS = ("from", "to", "trigger", "sourceFile", "sourceLine", "delta", "deltaReason")


def replacement_delta(from_id, to_id, food):
    """What one swap moves: the replacement's macros minus the original's, one item for one item.

    The same six macros and the same Ruling R3 gate `nutrition_delta` uses, and the same
    `absentMacros` rule -- a row that writes no line for one macro sums as 0 and is named, so
    the substitution is never silent. Returns `{"reason": …}` when a side cannot be weighed:
    `not-in-dataset` for a target no food row carries (37 of the 163 links point at a pan, a
    tray or -- once -- at `Base.MugRed`, which no item block in the install defines).
    """
    source, target = food.get(from_id), food.get(to_id)
    if source is None or target is None:
        return {"reason": "not-in-dataset"}
    refusal = _refusal(source) or _refusal(target)
    if refusal is not None:
        return {"reason": refusal}
    delta, absent = {}, set()
    for key, field in MACROS:
        total = 0.0
        for sign, item_id, row in ((-1.0, from_id, source), (1.0, to_id, target)):
            value = food_value(row, key)
            if value is None:
                absent.add("%s:%s" % (item_id, field))
                value = 0.0
            total += sign * value
        delta[field] = round(total, 6)
    delta["absentMacros"] = sorted(absent)
    return delta


def replacements(food):
    """Every `ReplaceOn*` link in the food dataset, as `REPLACEMENT_FIELDS` records.

    One record per (item, target): `ReplaceOnCooked` is a `;`-list (README row 41) and the other
    three are single names. Sorted by trigger, then source, then target -- the committed order.
    42.20.4 ships 3 cooked, 8 rotten, 110 use and 42 deplete links.
    """
    out = []
    for item_id in sorted(food):
        row = food[item_id]
        for key, trigger in REPLACEMENT_TRIGGERS:
            written = food_value(row, key)
            if not written:
                continue
            targets = written if isinstance(written, (list, tuple)) else _split(written)
            for target in targets:
                record = dict.fromkeys(REPLACEMENT_FIELDS)
                record.update({"from": item_id, "to": target, "trigger": trigger,
                               "sourceFile": food_value(row, "SourceFile"),
                               "sourceLine": food_value(row, "SourceLine")})
                delta = replacement_delta(item_id, target, food)
                if "reason" in delta:
                    record["delta"], record["deltaReason"] = None, delta["reason"]
                else:
                    record["delta"], record["deltaReason"] = delta, None
                out.append(record)
    out.sort(key=lambda r: (_TRIGGER_ORDER[r["trigger"]], r["from"], r["to"]))
    return out


def _calories_absent_on_every_side(recipe, food):
    """True when a resolved delta's `calories` is 0 only because no contributing row writes one.

    The three cigarette crafts (`PackCigarettes`, `TakeACigarette`, `UnpackCigarettes`) are the
    whole set in 42.20.4: neither `Base.CigarettePack` nor `Base.CigaretteSingle` writes a
    `Calories` line, so their `0.0` is the substitution `absentMacros` declares, not a measured
    conservation like `MakeToast`'s.
    """
    terms, blockers = delta_terms(recipe, food)
    return bool(terms) and not blockers and all(food_value(row, "Calories") is None
                                                for _sign, _line, row in terms)


def build(recipes, food):
    """Join the food dataset onto parsed recipes and sort by name -- the committed row order."""
    out = sorted(recipes, key=lambda r: r["name"])
    items = food_item_ids(food)
    for record in out:
        record["datasetTypes"] = dataset_types(record, food)
        record["foodItemTypes"] = [t for t in record["datasetTypes"] if t in items]
        delta = nutrition_delta(record, food)
        if "reason" in delta:                         # `nutrition_delta` always returns a dict
            record["delta"], record["deltaReason"] = None, delta["reason"]
        else:
            record["delta"], record["deltaReason"] = delta, None
    return out


def scan(root=MEDIA):
    """Every `craftRecipe` under `<root>/scripts`, with a census of what else the walk saw.

    Returns `(recipes, census)`. A record's `sourceFile` is relative to `scripts/generated` when
    the file is under it (`recipes/recipes_cooking.txt`) and to `scripts` otherwise, which is the
    path convention `data/food-items.json` already uses.
    """
    scripts_root = os.path.join(root, *SCRIPTS.split("/"))
    generated_root = os.path.join(root, *GENERATED.split("/"))
    recipes, files = [], set()
    census = {"scriptFiles": 0, "legacyRecipeBlocks": 0, "itemMappers": 0, "overlayMappers": 0,
              "componentCraftRecipes": 0, "outputMapperIssues": [], "foodTxtItemIds": set()}
    for dirpath, _dirs, names in os.walk(scripts_root):
        for name in sorted(names):
            if not name.endswith(".txt"):
                continue
            path = os.path.join(dirpath, name)
            base = generated_root if path.startswith(generated_root + os.sep) else scripts_root
            rel = os.path.relpath(path, base).replace("\\", "/")
            census["scriptFiles"] += 1
            with open(path, encoding="utf-8", errors="replace") as handle:
                blocks = food_scan.parse_script(handle.read(), rel)
            for block in food_scan.iter_blocks(blocks):
                if rel == FOOD_TXT and block["kind"] == "item":
                    # the join universe of `foodJoinMisses`: every id `items/food.txt` defines,
                    # whether or not `tools/food_scan.py` kept a row for it
                    census["foodTxtItemIds"].add("%s.%s" % (block["module"], block["name"]))
                if block["kind"] == "recipe":            # the B41 form; the loader still reads it
                    census["legacyRecipeBlocks"] += 1
                elif block["kind"] == "component" and block["name"] == "CraftRecipe":
                    census["componentCraftRecipes"] += 1
                elif block["kind"] == "craftRecipe":
                    record = build_recipe(block)
                    census["itemMappers"] += len(record["itemMapperPairs"])
                    census["overlayMappers"] += 1 if record["overlayMapper"] else 0
                    for line in record["outputs"] or ():
                        # an output that names a mapper but resolves to no type: either the
                        # recipe defines no such mapper (none in 42.20.4) or the mapper it
                        # defines writes only a `default`, which is a fallback and not a row
                        # (`ExtractIronFromIronOre`, the one vanilla case -- its default
                        # `Base.CeramicCrucible_Iron` is on the record as `itemMapperDefaults`)
                        if line["mapper"] and not line["types"]:
                            census["outputMapperIssues"].append({
                                "recipe": record["name"], "mapper": line["mapper"],
                                "why": "no-rows" if line["mapper"] in record["itemMapperPairs"]
                                       else "undefined"})
                    recipes.append(record)
                    files.add(rel)
    census["fileList"] = sorted(files)
    census["files"] = len(files)
    census["outputMapperIssues"].sort(key=lambda m: (m["recipe"], m["mapper"]))
    census["foodTxtItemIds"] = sorted(census["foodTxtItemIds"])
    return recipes, census


def build_dataset(root=MEDIA, food_path=FOOD_JSON):
    """Parse, join and stamp: `(meta, recipes)` ready to write."""
    food, food_meta = load_food(food_path)
    parsed, census = scan(root)
    recipes = build(parsed, food)

    output_types = sorted({t for r in recipes for line in io_lines(r, "outputs")
                           if line["kind"] == "item" for t in line["types"]})
    food_items = food_item_ids(food)
    with_delta = [r for r in recipes if r["delta"] is not None]
    # Acceptance 3: an output type that `items/food.txt` really defines but `data/food-items.json`
    # carries no row for -- the join between the two datasets, checked rather than assumed. A
    # miss would mean the food scan dropped an item this scan can name, so the expected list is
    # empty; it is emitted whether or not it is, beside `outputMapperIssues`.
    food_txt_ids = set(census["foodTxtItemIds"])
    food_join_misses = [t for t in output_types if t in food_txt_ids and t not in food]
    counts = {
        "craftRecipes": len(recipes),
        "files": census["files"],
        "scriptFiles": census["scriptFiles"],
        "legacyRecipeBlocks": census["legacyRecipeBlocks"],
        "componentCraftRecipes": census["componentCraftRecipes"],
        "itemMappers": census["itemMappers"],
        "overlayMappers": census["overlayMappers"],
        "recipesWithoutOutputs": sum(1 for r in recipes if r["outputs"] is None),
        "recipesWithEmptyOutputs": sum(1 for r in recipes if r["outputs"] == []),
        "fluidRecipes": sum(1 for r in recipes if r["fluidIO"]),
        # every distinct type an `outputs` item line names, `mapper:` lines resolved to each of
        # their results -- then the two subsets: rows of the dataset at all, and rows that are
        # food items (`food_item_ids`, i.e. never a fluid container)
        "outputItemTypes": len(output_types),
        "outputItemTypesInDataset": sum(1 for t in output_types if t in food),
        "outputItemTypesInFoodDataset": sum(1 for t in output_types if t in food_items),
        # a recipe "touches" a row when any item line on either side names one, tools and
        # multi-type alternatives included. The two universes of the module docstring:
        # `recipesTouchingDatasetRow` counts `datasetTypes` (vessels included),
        # `recipesTouchingFood` the `food`/`drainable` subset `foodItemTypes`;
        # `recipesWithFoodOutput` is the outputs-only slice of the latter
        "recipesTouchingDatasetRow": sum(1 for r in recipes if r["datasetTypes"]),
        "recipesTouchingFood": sum(1 for r in recipes if r["foodItemTypes"]),
        "recipesWithFoodOutput": sum(1 for r in recipes if any(
            t in food_items for line in io_lines(r, "outputs") if line["kind"] == "item"
            for t in line["types"])),
        "foodJoinMisses": len(food_join_misses),
        "recipesWithDelta": len(with_delta),
        "recipesWithNonZeroCalorieDelta": sum(1 for r in with_delta if r["delta"]["calories"]),
        # of the zero-calorie deltas, those whose zero is `absentMacros`' substitution rather
        # than a conserved macro -- see `_calories_absent_on_every_side`
        "recipesWithCaloriesAbsentOnEverySide": sum(
            1 for r in with_delta if not r["delta"]["calories"]
            and _calories_absent_on_every_side(r, food)),
        # a craft whose output is `1/outputCount` of the input it consumed (`InheritFood`), so
        # its delta is 0 by construction -- see `split_lines`
        "splitRecipes": sum(1 for r in recipes if r["split"]),
        "splitRecipesWithDelta": sum(1 for r in with_delta if r["split"]),
        "recipesWithDestroyWaste": sum(1 for r in with_delta
                                       if r["delta"]["destroyWaste"] is not None),
        "inputSubLines": sum(len(line["subLines"]) for r in recipes
                             for line in (r["inputs"] or [])),
    }
    meta = {
        "build": BUILD,
        "generated": datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
        "tool": "tools/recipe_scan.py",
        "sources": {
            # the tree walked, the 74 files a craftRecipe was actually read from, and the
            # dataset the deltas were joined against -- with its own build stamp, so a rebuild
            # of one half against a stale other half is visible in the file
            "scripts": "media/" + SCRIPTS,
            "files": census["fileList"],
            "food_items": {"path": os.path.relpath(food_path, _REPO).replace("\\", "/"),
                           "build": food_meta.get("build"),
                           "jar_hash": food_meta.get("jar_hash"),
                           "generated": food_meta.get("generated")},
        },
        "counts": counts,
        "outputMapperIssues": census["outputMapperIssues"],
        "foodJoinMisses": food_join_misses,
    }
    return meta, recipes


def _cell(value):
    """A CSV cell, by `food_scan._cell`'s rule: absent is empty -- never `0`, `false` or `None`."""
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (list, tuple)):
        return ";".join(str(v) for v in value)
    return str(value)


def _side_values(recipe, side, field):
    """Sorted distinct `field` values over one side's item lines, sub-lines included."""
    out = set()
    for line in io_lines(recipe, side):
        if line["kind"] == "item":
            out.update(line[field])
    return sorted(out)


def _fluids(recipe):
    """A fluid line's ids, plus `category:<Name>` for a line that names categories instead.

    Every vanilla fluid line is a `-fluid` sub-line of the input above it, so this walks the
    flat reading -- the CSV's `inputFluids` column is unchanged by the nesting.
    """
    out = set()
    for side in ("inputs", "outputs"):
        for line in io_lines(recipe, side):
            if line["kind"] == "fluid":
                out.update(line["types"])
                out.update("category:" + c for c in line["categories"])
    return sorted(out)


def csv_row(recipe):
    """One CSV row, `CSV_HEADER` order."""
    delta = recipe["delta"] or {}
    row = dict(recipe)
    row.update({
        "inputTypes": _side_values(recipe, "inputs", "types"),
        "inputTags": _side_values(recipe, "inputs", "tags"),
        "inputFluids": _fluids(recipe),
        "outputTypes": _side_values(recipe, "outputs", "types"),
        "itemMappers": sorted(recipe["itemMappers"]),
        # the flat reading, so a sub-line follows the input it hangs off and no line is hidden
        "inputsRaw": " | ".join(line["raw"] for line in io_lines(recipe, "inputs")),
        "outputsRaw": " | ".join(line["raw"] for line in io_lines(recipe, "outputs")),
        "deltaAbsentMacros": delta.get("absentMacros"),
    })
    for _key, field in MACROS:
        row["delta" + field[0].upper() + field[1:]] = delta.get(field)
    return [_cell(row[name]) for name in CSV_HEADER]


def write_csv(path, recipes):
    """One row per recipe, `CSV_HEADER` order, LF endings -- the JSON twin carries the stamp."""
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        for record in recipes:
            writer.writerow(csv_row(record))


def write_json(path, meta, recipes, replacements_=None):
    """`{"meta", "recipes"}`; LF endings and a trailing newline, so the file is diffable.

    `replacements_` appends the `ReplaceOn*` links as a third key **after** `recipes`, so adding
    them to an existing dataset is a tail diff and nothing above it moves. Omitted, the file is
    byte-for-byte what this writer produced before those links existed.
    """
    payload = {"meta": meta, "recipes": recipes}
    if replacements_ is not None:
        payload["replacements"] = replacements_
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=1, ensure_ascii=False)
        handle.write("\n")


def evolved_csv_row(recipe, ingredient):
    """One CSV row for a (recipe, ingredient) pair, `EVOLVED_CSV_HEADER` order."""
    at0, at10 = ingredient["at0"], ingredient["at10"]
    row = {"recipe": recipe["name"], "resultItem": recipe["resultItem"],
           "item": ingredient["item"], "use": ingredient["use"],
           "requiresCooked": ingredient["requiresCooked"], "spice": ingredient["spice"],
           "share0": at0["share"], "kcal0": at0["calories"], "carbs0": at0["carbohydrates"],
           "lipids0": at0["lipids"], "proteins0": at0["proteins"],
           "share10": at10["share"], "kcal10": at10["calories"]}
    return [_cell(row[name]) for name in EVOLVED_CSV_HEADER]


def write_evolved_csv(path, recipes):
    """One row per (recipe, ingredient), recipe order then item order, LF endings."""
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(EVOLVED_CSV_HEADER)
        for record in recipes:
            for ingredient in record["ingredients"]:
                writer.writerow(evolved_csv_row(record, ingredient))


def write_evolved_json(path, meta, recipes, unmatched):
    """`{"meta", "recipes", "unmatchedKeys"}`; LF endings and a trailing newline."""
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump({"meta": meta, "recipes": recipes, "unmatchedKeys": unmatched}, handle,
                  indent=1, ensure_ascii=False)
        handle.write("\n")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=MEDIA, metavar="DIR",
                    help="game media directory whose scripts/ tree is scanned")
    ap.add_argument("--food", default=FOOD_JSON, metavar="FILE",
                    help="the food dataset the nutrition deltas are joined from")
    ap.add_argument("--out-dir", default=OUT_DIR, metavar="DIR",
                    help="directory the recipes / evolved-recipes datasets are written to")
    ns = ap.parse_args(argv)
    # the four writers below all assume the directory is there; a `--out-dir` that names a fresh
    # path is a normal thing to ask for, not an error to raise after the whole scan has run
    os.makedirs(ns.out_dir, exist_ok=True)
    food, _food_meta = load_food(ns.food)
    links = replacements(food)
    meta, recipes = build_dataset(ns.root, ns.food)
    out_json = os.path.join(ns.out_dir, "recipes.json")
    out_csv = os.path.join(ns.out_dir, "recipes.csv")
    write_json(out_json, meta, recipes, links)
    write_csv(out_csv, recipes)

    evo_meta, evolved, unmatched = build_evolved_dataset(ns.root, ns.food)
    evo_json = os.path.join(ns.out_dir, "evolved-recipes.json")
    evo_csv = os.path.join(ns.out_dir, "evolved-recipes.csv")
    write_evolved_json(evo_json, evo_meta, evolved, unmatched)
    write_evolved_csv(evo_csv, evolved)
    counts = meta["counts"]
    # ASCII only: this runs on a cp1252 console, where a print of `·` aborts the run
    print("craftRecipes %d in %d files, %d legacy recipe blocks, %d itemMappers"
          % (counts["craftRecipes"], counts["files"], counts["legacyRecipeBlocks"],
             counts["itemMappers"]))
    print("%d distinct output item types, %d of them food items; %d recipes touch a food item"
          % (counts["outputItemTypes"], counts["outputItemTypesInFoodDataset"],
             counts["recipesTouchingFood"]))
    print("%d recipes carry a nutrition delta, %d of them non-zero in calories"
          % (counts["recipesWithDelta"], counts["recipesWithNonZeroCalorieDelta"]))
    print("%d splits (delta 0 by construction), %d input sub-lines attached, %d food join misses"
          % (counts["splitRecipes"], counts["inputSubLines"], counts["foodJoinMisses"]))
    print("%d recipes, %d columns -> %s" % (len(recipes), len(CSV_HEADER), out_csv))
    print("%d recipes -> %s" % (len(recipes), out_json))
    evo = evo_meta["counts"]
    print("%d evolvedRecipes, %d carriers, %d key->recipe joins, %d unmatched keys"
          % (evo["evolvedRecipes"], evo["carriers"], evo["pairs"], evo["unmatchedKeys"]))
    print("%d ingredient rows (%d duplicate joins collapsed), %d spices -> %s"
          % (evo["ingredients"], evo["duplicateJoins"], evo["spiceIngredients"], evo_csv))
    print("%d ReplaceOn* links (%s) -> %s"
          % (len(links), ", ".join("%d %s" % (sum(1 for l in links if l["trigger"] == t), t)
                                   for _key, t in REPLACEMENT_TRIGGERS), out_json))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
