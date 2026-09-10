#!/usr/bin/env python3
"""Vanilla food/drink dataset builder, on a shared reader for the script DSL.

`python tools/food_scan.py` parses the 42.20.4 scripts and writes
`data/food-items.json` + `data/food-items.csv`. See `select` for the selection rule (what is
and is not in the dataset), `build` for the joins, and data/README.md for the columns.

Stdlib only. The DSL is `module <M> { <kind> <Name> { Key = Value, ... <kind> <Name> { ... } } }`;
blocks nest (a drink is `item X { component FluidContainer { Fluids { fluid = Cola:1.0 } } }`),
so keys are kept **per block** and never flattened -- a `component FluidContainer`'s `Capacity`
must not land on the item that owns it. See docs/vanilla/food-item-model.md for what each key
means and `Item.DoParam` for the loader that reads them in-game.

`parse_script` is shared with tools/recipe_scan.py (slice 06), so it stays generic. Two shapes in
the shipped files do not fit "one block is a dict of keys", and each has its own field:

* **A key may repeat inside one block.** `props` is the last-write-wins dict the loader builds for
  a scalar key; `entries` is `[(key, raw), ...]` for *every* `Key = Value` line, in file order.
  Read a multi-valued key with `values(block, key)`, which is `entries` filtered the way the
  loader matches a key: `item HairDyeCommon`'s `Fluids` block has 8 `fluid =` lines (77 across
  `items/normal.txt`) and `item HandTorch` has 2 `SoundMap` lines -- `props` keeps only the last
  of each.
* **A block name may contain spaces** (`evolvedrecipe Stir fry`, `fixing Fix Hunting Rifle`). A line
  is a header iff the next logical line is `{`; `kind` is its first token and `name` the rest.
  `item 1 Base.Toast`, which no `{` follows, therefore stays a `lines` entry.

Anything else in a block is kept verbatim in `lines`: a fluid's `Categories` entries (`Beverage`)
and a recipe's IO lines (`item 1 [Base.BreadSlices] flags[ItemCount]`). `itemMapper`'s dotted
pairs (`Base.Cow_Skull = Base.Cow_Head_Angus`) land there too, on purpose: PROP_RE only accepts
identifier keys, and a mapper repeats the same left-hand side.

The parser half (parse_script .. load_translations) is shared with tools/recipe_scan.py; the
dataset half (COLUMNS .. main) is this tool's own.
"""
import csv, datetime, json, os, re

MEDIA = r"D:/SteamLibrary/steamapps/common/ProjectZomboid/media"

HEAD_RE = re.compile(r"^([A-Za-z]\w*)\s+(.+)$")         # `item Apple`, `evolvedrecipe Stir fry`
PROP_RE = re.compile(r"^([A-Za-z_]\w*)\s*=\s*(.*?)\s*,?$")

_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _strip_comments(text):
    """Drop `//` and `/* */`, keeping the line count so recorded line numbers stay true.

    Nothing under media/scripts/generated/ carries either form in 42.20.4, but 28 files under
    media/scripts/xui/ do use `/* */` (25 of them in xui/defaultskin/), full-line and inline --
    `/*backgroundColor = SandyBrown,*/` in xs_ISButton.txt. No shipped file uses `//`; mods do.
    """
    text = _BLOCK_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return _LINE_COMMENT_RE.sub("", text)


def _logical_lines(text):
    """Yield (line_number, stripped_text), splitting `craftRecipe MakeToast {` into two entries.

    Every shipped file puts the brace on its own line; the same-line form is a mod convention.
    Splitting it here is what lets `parse_script` recognise a header by a single rule -- the next
    logical line is `{`.
    """
    for n, raw in enumerate(_strip_comments(text).splitlines(), 1):
        s = raw.strip()
        if len(s) > 1 and s.endswith("{") and "=" not in s:
            yield n, s[:-1].strip()
            s = "{"
        if s:
            yield n, s


def _innermost(stack):
    """The block a line belongs to, or None at file level.

    Entries are Blocks except for a `{` that no header preceded -- mod junk, never shipped. Those
    push None so the matching `}` cannot pop a real parent, and their contents fall through to the
    enclosing block rather than into an invented anonymous one.
    """
    for block in reversed(stack):
        if block is not None:
            return block
    return None


def parse_script(text, path=""):
    """Parse one script file into a list of top-level (usually `module`) Blocks.

    Block = {"kind", "name", "module", "file", "line", "props": {k: raw_str},
             "entries": [(k, raw_str)], "lines": [str], "blocks": [Block]}
    `line` is the 1-based line of the block's header; `props`/`entries` values stay raw (`coerce`
    types them). See the module docstring for `entries` vs `props` and for header detection.
    """
    logical = list(_logical_lines(text))
    roots, stack, module, pending = [], [], "Base", None
    for i, (n, s) in enumerate(logical):
        if s == "{":
            if pending is None:                 # a brace no header opened: keep the depth honest
                stack.append(None)
                continue
            parent = _innermost(stack)
            block = {"kind": pending[0], "name": pending[1], "module": module, "file": path,
                     "line": pending[2], "props": {}, "entries": [], "lines": [], "blocks": []}
            (parent["blocks"] if parent else roots).append(block)
            stack.append(block)
            pending = None
            continue
        if s == "}":
            if stack:
                stack.pop()
            continue
        m = PROP_RE.match(s)                    # before the header test: `Weight =0.2` is a prop
        if m:
            block = _innermost(stack)
            if block is not None:
                block["props"][m.group(1)] = m.group(2)
                block["entries"].append((m.group(1), m.group(2)))
            continue
        if i + 1 < len(logical) and logical[i + 1][1] == "{":
            m = HEAD_RE.match(s)
            if m:                               # `item Apple`, `evolvedrecipe Stir fry`
                kind, name = m.group(1), m.group(2)
                if kind == "module":
                    module = name
            else:                               # `Properties` / `Categories` / `Fluids`
                kind, name = "block", s
            pending = (kind, name, n)
            continue
        block = _innermost(stack)
        if block is not None:
            block["lines"].append(s[:-1].rstrip() if s.endswith(",") else s)
    return roots


def iter_blocks(blocks):
    """Yield every block depth-first, parents before children."""
    for block in blocks:
        yield block
        yield from iter_blocks(block["blocks"])


def walk(blocks, parent=None):
    """Yield (parent_block_or_None, block) depth-first, so a caller can see real parenthood.

    `iter_blocks` when the parent does not matter; this when it does -- a `component
    FluidContainer` is only a drink's container if the block that owns it is an `item`.
    """
    for block in blocks:
        yield parent, block
        yield from walk(block["blocks"], block)


def named(block, name):
    """The first child block called `name` (`Fluids`, `Properties`, `Poison`), or None."""
    for child in block["blocks"]:
        if child["name"] == name:
            return child
    return None


def values(block, key):
    """Every raw value this block writes to `key`, in file order; `[]` if it writes none.

    Keys match the way `Item.DoParam`'s equalsIgnoreCase chain matches them, through
    `canonical_key`, so a fluid file's `foodSicknessChange` answers to `FoodSicknessChange`.
    Reads `entries`, so every line is kept and not just the last: `item HairDyeCommon`'s
    `Fluids` block writes 8 `fluid =` lines that `props` collapses to one. See the module
    docstring for `entries` vs `props`.
    """
    wanted = canonical_key(key).lower()
    return [raw for written, raw in block["entries"] if canonical_key(written).lower() == wanted]


def _key_types():
    """The 114 script keys of docs/vanilla/food-item-model.md, by parsed value type."""
    groups = (
        (int, """BoredomChange ChanceToSpawnDamaged ColorBlue ColorGreen ColorRed ConditionMax
                 DaysFresh DaysTotallyRotten Eattime FoodSicknessChange InverseCoughProbability
                 InverseCoughProbabilitySmoker LightDistance MinutesToBurn MinutesToCook PoisonPower
                 StressChange UnhappyChange VehicleType fluReduction painReduction ticksPerEquipUse"""),
        (float, """AlcoholPower Calories Carbohydrates ConditionLowerStandard FireFuelRatio
                   HungerChange LightStrength Lipids MetalValue Proteins ReduceInfectionPower
                   ScaleWorldIcon ThirstChange TorchDot UseDelta Weight WeightEmpty enduranceChange
                   fatigueChange"""),
        (bool, """ActivatedItem BadCold BadInMicrowave CanStoreWater CannedFood CantBeFrozen CantEat
                  DangerousUncooked DisappearOnUse FishingLure GoodHot IsCookable IsDung KeepOnDeplete
                  MechanicsItem Medical Packaged RemoveNegativeEffectOnCooked
                  RemoveUnhappinessWhenCooked Spice SurvivalGear TorchCone UseWhileEquipped
                  UseWhileUnequipped UseWorldItem cantBeConsolided"""),
        (list, """EvolvedRecipe IconsForTexture ReplaceOnCooked RequireInHandOrInventory
                  Researchablerecipes SoundMap StaticModelsByIndex Tags WorldStaticModelsByIndex"""),
        (str, """AnimalFeedType AttachmentType ConsolidateOption CookingSound CustomContextMenu
                 CustomEatSound DisplayCategory DoubleClickRecipe EatType EquipSound EvolvedRecipeName
                 FillFromDispenserSound FillFromTapSound FoodType HerbalistType Icon IconColorMask
                 ItemType MakeUpType OnCooked OnCreate OnEat OpeningRecipe PourType ReplaceInPrimaryHand
                 ReplaceInSecondHand ReplaceOnDeplete ReplaceOnExtinguish ReplaceOnRotten ReplaceOnUse
                 StaticModel Tooltip UnequipSound WorldStaticModel primaryAnimMask secondaryAnimMask
                 IsWaterSource RainFactor"""),   # the last two are dead keys: they reach defaultModData
    )
    out = {}
    for value_type, names in groups:
        out.update(dict.fromkeys(names.split(), value_type))
    return out


KEY_TYPES = _key_types()
# Item.DoParam is a chain of equalsIgnoreCase comparisons, so key case does not matter to the
# loader: the fluid files' `foodSicknessChange` is the item files' `FoodSicknessChange`.
_KEY_TYPES_CI = {k.lower(): v for k, v in KEY_TYPES.items()}
_CANONICAL_KEYS = {k.lower(): k for k in KEY_TYPES}


def is_known_key(key):
    """False for a key no loader branch reads -- it becomes `defaultModData`, not an error."""
    return key.lower() in _KEY_TYPES_CI


def canonical_key(key):
    """The `KEY_TYPES` spelling of `key`; an unknown key comes back unchanged.

    The fluid files write `foodSicknessChange` where the item files (and the doc table) write
    `FoodSicknessChange`, and the loader's equalsIgnoreCase does not care. Canonicalise before
    merging a fluid's `Properties` into an item record, or the record grows both spellings.
    """
    return _CANONICAL_KEYS.get(key.lower(), key)


def coerce(key, raw):
    """Type a raw script value the way the loader does; an unknown key stays a string.

    Bool is `Boolean.parseBoolean` / `equalsIgnoreCase("true")`: only the literal `true` is true.

    An int-typed key may carry a float literal -- the fluid files write `UnhappyChange = -10.0`
    and `fluReduction = 0.0` into keys the item table types int (141 such values in 42.20.4, all
    of them integral). Those parse through float and come back as an int (`-10.0` -> `-10`); a
    genuinely fractional literal on an int key would keep its float value. Only a value neither
    parse accepts (a mod's `Calories = n/a`) is returned unchanged rather than raised, so one
    malformed item cannot abort a whole-tree scan.
    """
    value_type = _KEY_TYPES_CI.get(key.lower(), str)
    if value_type is bool:
        return raw.strip().lower() == "true"
    if value_type is list:
        return [part for part in (p.strip() for p in raw.split(";")) if part]
    if value_type is float:
        try:
            return float(raw.strip())
        except ValueError:
            return raw
    if value_type is int:
        try:
            return int(raw.strip())
        except ValueError:
            pass
        try:
            number = float(raw.strip())
        except ValueError:
            return raw
        return int(number) if number.is_integer() else number
    return raw


def coerce_props(props):
    """`coerce` every entry of a block's props. An absent key stays absent -- never 0."""
    return {k: coerce(k, v) for k, v in props.items()}


def load_translations(media_root):
    """(items, fluids) display names: `Base.Apple` -> "Apple", `Fluid_Name_Cola` -> "Cola".

    B42 ships these as JSON under lua/shared/Translate/EN (the B41 `ItemName_EN.txt` layout is
    gone). A missing file yields {} so a scan can run without the install; a malformed one raises.
    """
    base = os.path.join(media_root, "lua", "shared", "Translate", "EN")
    return _load_json(os.path.join(base, "ItemName.json")), _load_json(os.path.join(base, "Fluids.json"))


def _load_json(path):
    try:
        handle = open(path, encoding="utf-8-sig")
    except OSError:
        return {}
    with handle:
        return json.load(handle)


# --------------------------------------------------------------------------------------------
# The dataset: data/food-items.json + data/food-items.csv
# --------------------------------------------------------------------------------------------

BUILD = "42.20.4"
JAR_HASH = "b0bbce05d5"
SCRIPTS = "scripts/generated"                  # under MEDIA; every source path is relative to it
FOOD_FILE = "items/food.txt"
DRAINABLE_FILE = "items/drainable.txt"
FLUID_FILES = ("fluids.txt", "fluids_Alcoholic.txt", "fluids_Beverages.txt")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(_REPO, "data", "food-items.json")
OUT_CSV = os.path.join(_REPO, "data", "food-items.csv")

# The dataset's row schema: (column, script key it is read from). A None key is derived -- see
# `build`. The order is the CSV's column order and the JSON record's field order, and
# data/README.md documents one line per column; `source_file` / `source_line` trail every row.
COLUMNS = (
    ("id", None), ("module", None), ("name", None), ("kind", None), ("display_name", None),
    ("display_category", "DisplayCategory"),
    ("food_type", "FoodType"),
    ("item_type", "ItemType"),
    ("tags", "Tags"),
    ("nutrition_source", None),
    ("nutrition_basis", None),
    ("calories", "Calories"),
    ("carbohydrates", "Carbohydrates"),
    ("lipids", "Lipids"),
    ("proteins", "Proteins"),
    ("hunger_change", "HungerChange"),
    ("thirst_change", "ThirstChange"),
    ("days_fresh", "DaysFresh"),
    ("days_totally_rotten", "DaysTotallyRotten"),
    ("cant_be_frozen", "CantBeFrozen"),
    ("is_cookable", "IsCookable"),
    ("minutes_to_cook", "MinutesToCook"),
    ("minutes_to_burn", "MinutesToBurn"),
    ("dangerous_uncooked", "DangerousUncooked"),
    ("packaged", "Packaged"),
    ("canned_food", "CannedFood"),
    ("cant_eat", "CantEat"),
    ("spice", "Spice"),
    ("good_hot", "GoodHot"),
    ("bad_cold", "BadCold"),
    ("unhappy_change", "UnhappyChange"),
    ("boredom_change", "BoredomChange"),
    ("stress_change", "StressChange"),
    ("fatigue_change", "fatigueChange"),
    ("endurance_change", "enduranceChange"),
    ("food_sickness_change", "FoodSicknessChange"),
    ("poison_power", "PoisonPower"),
    ("alcohol_power", "AlcoholPower"),
    ("evolved_recipe", "EvolvedRecipe"),
    ("evolved_recipe_name", "EvolvedRecipeName"),
    ("replace_on_cooked", "ReplaceOnCooked"),
    ("replace_on_rotten", "ReplaceOnRotten"),
    ("replace_on_use", "ReplaceOnUse"),
    ("on_cooked", "OnCooked"),
    ("on_eat", "OnEat"),
    ("fluid_capacity", None),
    ("fluid_ids", None),
    # The fill, and the per-litre nutrition multiplied through it. All ten are derived, and all ten
    # are null on a row that owns no `component FluidContainer` -- see `build_item` for the
    # arithmetic and its cites.
    ("fluid_share", None),
    ("fluid_fill_litres", None),
    ("fluid_pick_random", None),
    ("drinkable", None),
    ("calories_per_container", None),
    ("carbohydrates_per_container", None),
    ("lipids_per_container", None),
    ("proteins_per_container", None),
    ("hunger_change_per_container", None),
    ("thirst_change_per_container", None),
    ("weight", "Weight"),
    # The last declared column, appended rather than slotted beside the other `ReplaceOn*` columns
    # when it was added (fix round 1) and left there since.
    ("replace_on_deplete", "ReplaceOnDeplete"),
)
TRAILING = ("source_file", "source_line")
CSV_HEADER = [name for name, _key in COLUMNS] + list(TRAILING)

# Which column a fluid's `Properties` key feeds when a container's nutrition is joined. Derived
# from COLUMNS so the two can never drift; the fluid files' `foodSicknessChange` reaches
# `food_sickness_change` through `canonical_key`. In 42.20.4 that covers 11 of the 14 keys a
# `Properties` block writes -- `alcohol`, `fluReduction` and `painReduction` have no column and
# stay in the fluid record's `properties_raw` (the item-side `alcohol_power` is `AlcoholPower`,
# a different key on a different scale, so it is never filled from `alcohol`).
_KEY_TO_COLUMN = {key: name for name, key in COLUMNS if key}

# The columns a fluid may fill -- what a `Properties` block can say about a consumable's effect
# on the body. Identity, packaging, cooking, weight and the links stay the item's own. Three of
# them (`boredom_change`, `poison_power`, `alcohol_power`) no shipped fluid writes; they are here
# because a fluid *may* write the key, and a fluid record keeps the column as null either way.
NUTRITION_COLUMNS = tuple(name for name, key in COLUMNS if name in {
    "calories", "carbohydrates", "lipids", "proteins", "hunger_change", "thirst_change",
    "unhappy_change", "boredom_change", "stress_change", "fatigue_change", "endurance_change",
    "food_sickness_change", "poison_power", "alcohol_power"})

# `(per-litre column, its x litres twin)`. A fluid's `Properties` are per **one litre**, so on a
# `fluid_container` row the six columns on the left are not what the item delivers -- the right-hand
# column is. The engine does this multiply itself, in `FluidContainer.recalculateCaches @222-@250
# L631-L632` (`propertiesCache.addFromMultiplied(fluid.getProperties(), litres)`), before
# `IsoGameCharacter.DrinkFluid @23-@100 L5878-L5881` reads the aggregate. Only these six of the 14
# NUTRITION_COLUMNS get a twin: they are the six the drink path actually spends
# (`DrinkFluid` -> `Nutrition` for the four macros, -> `Stats` for hunger and thirst).
# See .superpowers/sdd/05-food-scanner/q3-fluid-nutrition-notes.md.
PER_CONTAINER_COLUMNS = tuple((name, name + "_per_container") for name in (
    "calories", "carbohydrates", "lipids", "proteins", "hunger_change", "thirst_change"))

# `ISInventoryPaneContextMenu.lua:2318` refuses the Drink menu outright for a bigger container, so
# `drinkable` is the fill's "can a player drink this at all" flag. 16 of the 133 fail it.
DRINKABLE_MAX_CAPACITY = 3.0

# Resolved against the dataset's own id set; a target outside it is a `meta.unresolved_links`
# row. `ReplaceOnCooked` is list-typed in KEY_TYPES, the other three are strings. All four have a
# column of their own, so a row shows the link as well as the miss.
REPLACE_KEYS = ("ReplaceOnCooked", "ReplaceOnRotten", "ReplaceOnUse", "ReplaceOnDeplete")


def _raw_entries(block):
    """`{key: raw}` for every `Key = Value` line, verbatim; a key written twice becomes a list.

    This is a record's `props_raw`. It is built from `entries`, not `props`, so the 7 repeated
    `SoundMap` lines in the selection survive; keys are sorted because their file order is not
    semantic to the loader, but a repeated key keeps its file order inside its list. Repeats are
    gathered with `values`, i.e. the loader's way, so two spellings of one key (`Weight` and
    `weight` in one block) would share a list under the first spelling seen -- no block in any
    file this tool reads does that.
    """
    out, seen = {}, set()
    for key, _raw in block["entries"]:
        if key.lower() in seen:
            continue
        seen.add(key.lower())
        written = values(block, key)
        out[key] = written[0] if len(written) == 1 else written
    return dict(sorted(out.items()))


def _capacity(raw):
    """A FluidContainer's `Capacity`, in litres.

    KEY_TYPES is the *item* key table (docs/vanilla/food-item-model.md), and `Capacity` is a
    component key, so `coerce` would leave it a string. `fluid_capacity` is a declared column of
    this dataset, so the dataset types it: float, or the raw string if it will not parse.
    """
    try:
        return float(raw)
    except ValueError:
        return raw


def _flag(raw):
    """A component key's bool. `Boolean.parseBoolean`: only the literal `true` is true.

    The component keys are outside KEY_TYPES for the same reason `Capacity` is, so `coerce` would
    leave `PickRandomFluid = true` the string `"true"`; `fluid_pick_random` is a declared column.
    """
    return raw.strip().lower() == "true"


def _share(raw):
    """The share of a `fluid = <id>[:share[:r:g:b]]` line, defaulting to 1.0.

    `FluidContainerScript.readFluid @16-@29 L348-L349` splits the value on `:` and reads the second
    field as the fluid's percentage (a five-field form adds an RGB colour, `@32-@76 L351-L355`); a
    line that writes only an id leaves the script's own default of 1.0. A share that will not parse
    comes back as the raw string, the way `_capacity` does.
    """
    parts = raw.split(":")
    if len(parts) < 2 or not parts[1].strip():
        return 1.0
    try:
        return float(parts[1].strip())
    except ValueError:
        return parts[1].strip()


def _round(value):
    """6 decimals: the product of two script decimals, minus the binary-float dust.

    `-12.0 * 0.3` is `-3.5999999999999996` in IEEE 754 and `104.0 * 0.3` is `31.200000000000003`;
    both are an artefact of the multiply, not of the files, which write at most two decimals for a
    `Capacity` and two for a property. 7 of the 72 filled rows carry such a product.
    """
    return round(value, 6)


def _fill_litres(capacity, share):
    """`min(Capacity x share, Capacity)` -- the litres a container spawns holding.

    `FluidContainer.readFromScript @93-@106 L108` reads `FluidContainerScript.getInitialAmount()`,
    which defaults to `Capacity` when no `InitialAmount` key was written (`@0-@11 L387-L388`, and no
    vanilla script writes one); `addInitialFluid @11-@17 L132` multiplies it by the share, and
    `addFluid @30-@45 L1003-L1004` clamps the result to what is left of the capacity -- which is
    what `Base.BucketWaterDebug`'s `Water:10.0` into a `Capacity = 10.0` runs into, the only share
    in 42.20.4 that is not `1.0`. `None` unless both terms are numbers: without a parsable capacity
    and share there is no auditable fill.
    """
    if not isinstance(capacity, (int, float)) or not isinstance(share, (int, float)):
        return None
    return _round(min(capacity * share, capacity))


def load_trees(media_root=MEDIA):
    """Parse every source script into `{relative path: [top-level Block]}`.

    The 15 `items/*.txt` (every one, because a FluidContainer may sit in any of them) plus the
    three fluid files. Paths are relative to `<media_root>/scripts/generated` and are what a
    record's `source_file` and `meta.sources` report.
    """
    root = os.path.join(media_root, *SCRIPTS.split("/"))
    names = sorted(f for f in os.listdir(os.path.join(root, "items")) if f.endswith(".txt"))
    trees = {}
    for rel in ["items/" + f for f in names] + list(FLUID_FILES):
        path = os.path.join(root, *rel.split("/"))
        with open(path, encoding="utf-8", errors="replace") as handle:
            trees[rel] = parse_script(handle.read(), rel)
    return trees


def select(trees):
    """The dataset's definition: which script blocks are records, and what `kind` each gets.

    Four rules, applied in this order over `trees` ({relative path: [Block]}); the first rule
    that claims a block wins, so a record is never emitted twice:

    a. every `item` in `items/food.txt` whose `ItemType` is `base:food`  ->  kind `food` (722);
    b. every `item` in `items/drainable.txt` whose `ItemType` is `base:drainable`  ->  kind
       `drainable` (150) -- in because it is the other half of the 114-key union, so the dataset
       covers every key the doc's table describes, not just the eaten ones;
    c. every `item` in any `items/*.txt` that owns a `component FluidContainer`  ->  kind
       `fluid_container` (133) -- a drink's nutrition lives in the fluid, not on the item. Owns
       means the component's own parent block: one nested deeper claims nothing, so no record is
       ever minted for a block that is not an `item`. All 133 in 42.20.4 sit straight in one;
    d. every `fluid` in `fluids.txt` / `fluids_Alcoholic.txt` / `fluids_Beverages.txt` (61), as
       its own record set under the JSON's `fluids` key, never as a CSV row.

    In 42.20.4 the three item rules are disjoint (no `base:food` or `base:drainable` item owns a
    FluidContainer, and none of the three sets repeats an id), so the counts sum to the 1005
    records; the ordering only matters for a mod that breaks that.

    Deliberately out: `base:food` items that a mod puts in another file (the rule is per file,
    the way the game's own split is), every non-food `item` (weapons, clothing) unless it owns a
    FluidContainer, and recipes -- `evolvedrecipes.txt` and `recipes/` are slice 06.

    Returns `([(kind, item_block, fluid_container_block_or_None), ...], [fluid_block, ...])`.
    """
    claimed, items = set(), []

    def claim(kind, block, container=None):
        if id(block) in claimed:
            return
        claimed.add(id(block))
        items.append((kind, block, container))

    def items_of(rel):
        return [b for b in iter_blocks(trees.get(rel, [])) if b["kind"] == "item"]

    def item_type(block):
        """`ItemType` as the loader reads it: case-insensitively, last line wins."""
        written = values(block, "ItemType")
        return written[-1] if written else None

    for block in items_of(FOOD_FILE):
        if item_type(block) == "base:food":
            claim("food", block)
    for block in items_of(DRAINABLE_FILE):
        if item_type(block) == "base:drainable":
            claim("drainable", block)
    for rel in sorted(r for r in trees if r.startswith("items/")):
        for parent, block in walk(trees[rel]):
            # the parent must be the `item` itself: a FluidContainer nested deeper (inside another
            # component) would otherwise mint a record for a block that is not an item at all.
            if (block["kind"] == "component" and block["name"] == "FluidContainer"
                    and parent is not None and parent["kind"] == "item"):
                claim("fluid_container", parent, block)

    fluids = [b for rel in FLUID_FILES for b in iter_blocks(trees.get(rel, []))
              if b["kind"] == "fluid"]
    return items, fluids


def build_fluid(block, fluid_names):
    """One `fluid` record: identity, display name, categories, typed nutrition, raws.

    The typed fields are the same lowercase names the item columns use, so joining a fluid into
    a container is a straight copy of whichever of them the fluid writes. `properties_raw` keeps
    every `Properties` key verbatim (including the three with no column), `poison` the `Poison`
    block a hazardous fluid carries, `props_raw` the fluid block's own keys.
    """
    properties = named(block, "Properties")
    categories = named(block, "Categories")
    poison = named(block, "Poison")
    display_key = block["props"].get("DisplayName")
    record = {
        "id": block["name"],
        "module": block["module"],
        "name": block["name"],
        "kind": "fluid",
        "display_name": fluid_names.get(display_key) if display_key else None,
        "display_name_key": display_key,
        "color_reference": block["props"].get("ColorReference"),
        "categories": list(categories["lines"]) if categories else [],
    }
    record.update(dict.fromkeys(NUTRITION_COLUMNS))
    for key, raw in (properties["props"].items() if properties else ()):
        column = _KEY_TO_COLUMN.get(canonical_key(key))
        if column in NUTRITION_COLUMNS:
            record[column] = coerce(key, raw)
    record["properties_raw"] = _raw_entries(properties) if properties else {}
    record["poison"] = _raw_entries(poison) if poison else None
    record["props_raw"] = _raw_entries(block)
    record["source_file"] = block["file"]
    record["source_line"] = block["line"]
    return record


def build_item(kind, block, container, fluids_by_id, item_names, misses):
    """One item record: the typed columns, the fluid join, `props_raw`, and the source anchor.

    Every column is present on every record. An absent script key is `None` -- never `0`, and
    never a guess: the dataset only ever carries what a line in the file says.

    A `fluid_container` is joined to the **first** fluid its `Fluids` block lists: `fluid_ids`
    is every `fluid =` value's first `:`-field in file order (`HairDye:1.0:0.1:...` -> `HairDye`),
    `fluid_capacity` is the component's `Capacity`, and whatever nutrition columns that first
    fluid writes replace the item's own, with `nutrition_source` = `fluid:<id>`. Every other
    record reads `food_keys`. 9 pick-random containers list several `fluid =` lines: 4 repeat one
    id (`HairDyeCommon` lists `HairDye` 8 times) and 5 list *different* fluids
    (`meta.counts.multi_fluid_containers`), so `Base.Flask` carries Gin's nutrition alone though
    it can also hold Rum, Scotch, Vodka or Whiskey -- `fluid_ids` keeps the whole set. In 42.20.4
    no fluid-container item writes a nutrition key of its own, so the replacement never actually
    loses a value; 10 of the 61 fluids carry no `Properties` block at all, so `fluid:Dye` with
    empty nutrition is a real and correct row.

    **The joined values are per litre, and the item's own are per item**, which is what
    `nutrition_basis` says on every row and what the six `_per_container` columns resolve: a
    fluid's `Properties` are the effect of one litre of it (`FluidDefinitionScript.LoadProperties
    @0-@453 L367-L410` parses them literally; `FluidContainer.recalculateCaches @222-@250
    L631-L632` is what multiplies them by the litres in the container), so `Base.Pop2` is 400 kcal
    of Cola per litre but `400 x 0.3 = 120` kcal of can. The fill facts make that arithmetic
    auditable from the row: `fluid_share` off the first `fluid =` line, `fluid_fill_litres` =
    `min(capacity x share, capacity)`, `fluid_pick_random` off the component's `PickRandomFluid`
    (the row then carries **one draw** of the pool, not the item's value) and `drinkable` =
    `fluid_capacity <= 3.0`. The `/100` that turns `hunger_change` / `thirst_change` into stat
    units is *not* applied on either side (`getHungerChange @7 L186` vs `getCalories @0 L202`), so
    a can's `-3.6` stays comparable to an apple's `-16`. See
    .superpowers/sdd/05-food-scanner/q3-fluid-nutrition-notes.md for the whole read.
    """
    record = dict.fromkeys(CSV_HEADER)
    item_id = "%s.%s" % (block["module"], block["name"])
    record.update({"id": item_id, "module": block["module"], "name": block["name"], "kind": kind,
                   "display_name": item_names.get(item_id), "nutrition_source": "food_keys",
                   "source_file": block["file"], "source_line": block["line"]})
    if item_id not in item_names:
        misses["missing_display_names"].append(item_id)
    # `props`, not `entries`: a column is a scalar, so a key written twice takes its last value,
    # the way the loader does. No column key repeats in 42.20.4 (only `SoundMap` does, and it
    # has no column); `props_raw` keeps every line either way.
    for key, raw in block["props"].items():
        column = _KEY_TO_COLUMN.get(canonical_key(key))
        if column:
            record[column] = coerce(key, raw)

    if container is not None:
        # the three component keys are read through `values`, i.e. the loader's equalsIgnoreCase
        # way, and take their last line -- exactly as the item keys above do
        capacity = values(container, "Capacity")
        if capacity:
            record["fluid_capacity"] = _capacity(capacity[-1])
        record["fluid_pick_random"] = any(_flag(raw)
                                          for raw in values(container, "PickRandomFluid"))
        if isinstance(record["fluid_capacity"], (int, float)):
            record["drinkable"] = record["fluid_capacity"] <= DRINKABLE_MAX_CAPACITY
        # `[]` (an empty jar: a container listing no fluid) is not `None` (no container at all)
        pool = named(container, "Fluids")
        raws = values(pool, "fluid") if pool else []
        ids = [raw.split(":")[0].strip() for raw in raws]
        record["fluid_ids"] = ids
        if ids:
            record["nutrition_source"] = "fluid:" + ids[0]
            record["fluid_share"] = _share(raws[0])
            record["fluid_fill_litres"] = _fill_litres(record["fluid_capacity"],
                                                       record["fluid_share"])
            fluid = fluids_by_id.get(ids[0])
            if fluid is None:
                misses["unresolved_fluid_refs"].append({"item": item_id, "fluid_id": ids[0]})
            else:
                for column in NUTRITION_COLUMNS:
                    record[column] = fluid[column]
            litres = record["fluid_fill_litres"]
            if litres is not None:
                for column, derived in PER_CONTAINER_COLUMNS:
                    # a key the fluid never writes stays absent here too: `x 0.3` of nothing is
                    # nothing, not `0.0` (`fluid Water` writes only `ThirstChange`)
                    if isinstance(record[column], (int, float)):
                        record[derived] = _round(record[column] * litres)

    # Which unit the nutrition columns are in -- after the join, so a container reads `per_litre`
    # even when the fluid it names carries no `Properties` at all. A row that carries no nutrition
    # value from either side has no basis to report, and says so with `None` rather than a guess.
    if record["nutrition_source"].startswith("fluid:"):
        record["nutrition_basis"] = "per_litre"
    elif any(record[column] is not None for column in NUTRITION_COLUMNS):
        record["nutrition_basis"] = "per_item"

    record["props_raw"] = _raw_entries(block)
    return record


def _link_targets(block, key):
    """Every id `key` names on this block, in file order (`ReplaceOnCooked` is list-typed)."""
    out = []
    for raw in values(block, key):
        value = coerce(key, raw)
        out.extend(value if isinstance(value, list) else [value])
    return [t for t in out if t]


def build(trees, item_names=None, fluid_names=None):
    """Join the selected blocks into `(items, fluids, misses)`, sorted by id.

    Joins, in order: display names off `ItemName.json` / `Fluids.json`; a container's fluids off
    the fluid records; then `ReplaceOnCooked` / `ReplaceOnRotten` / `ReplaceOnUse` /
    `ReplaceOnDeplete` against the dataset's own id set. A link whose target is not a record --
    a cooking pan, an empty sandbag, or `Base.MugRed`, which 42.20.4 names but never defines --
    is a `misses["unresolved_links"]` row naming the item, the key and the target; the target's
    own value stays in the record either way.
    """
    item_names = item_names or {}
    fluid_names = fluid_names or {}
    selected, fluid_blocks = select(trees)
    misses = {"unresolved_links": [], "missing_display_names": [], "unresolved_fluid_refs": []}

    fluids = sorted((build_fluid(b, fluid_names) for b in fluid_blocks), key=lambda r: r["id"])
    for record in fluids:
        if record["display_name"] is None:
            misses["missing_display_names"].append("fluid:" + record["id"])
    fluids_by_id = {r["id"]: r for r in fluids}

    built = [(build_item(kind, block, container, fluids_by_id, item_names, misses), block)
             for kind, block, container in selected]
    built.sort(key=lambda pair: pair[0]["id"])
    items = [record for record, _block in built]

    known = {r["id"] for r in items}
    for record, block in built:
        for key in REPLACE_KEYS:
            for target in _link_targets(block, key):
                if target not in known:
                    misses["unresolved_links"].append(
                        {"item": record["id"], "key": key, "target": target})
    misses["unresolved_links"].sort(key=lambda m: (m["item"], m["key"], m["target"]))
    misses["missing_display_names"].sort()
    misses["unresolved_fluid_refs"].sort(key=lambda m: (m["item"], m["fluid_id"]))
    return items, fluids, misses


def unknown_keys(items, fluids):
    """Sorted script keys the dataset carries that `is_known_key` rejects -- kept as raw strings.

    Scoped to keys whose value actually reaches a record, not to every key in the files scanned:
    the item records' `props_raw` (a fluid-container item in `weapon.txt` or `clothing.txt`
    brings weapon and clothing keys with it), the component's `Capacity` and `fluid`, and the
    fluid records' own keys (`DisplayName`, `ColorReference`, `alcohol`, the `Poison` block).
    KEY_TYPES is the food + drainable union by design, so this list is expected to be non-empty.

    Three of the keys listed are not kept raw, and none of them reaches a `props_raw` at all: they
    belong to the `component FluidContainer`, and the dataset types them itself into declared
    columns -- `Capacity` floated into `fluid_capacity`, `fluid` split into `fluid_ids` and
    `fluid_share`, `PickRandomFluid` flagged into `fluid_pick_random`. They are *injected* into the
    list below because the **key** is outside the item key table, which is what this list reports;
    it is not a claim that their values stayed strings.
    """
    seen = set()
    for record in items:
        seen.update(record["props_raw"])
        if record["fluid_capacity"] is not None:
            seen.add("Capacity")
        if record["fluid_ids"]:
            seen.add("fluid")
        if record["fluid_pick_random"]:
            seen.add("PickRandomFluid")
    for record in fluids:
        seen.update(record["props_raw"])
        seen.update(record["properties_raw"])
        seen.update(record["poison"] or ())
    return sorted(k for k in seen if not is_known_key(k))


def build_dataset(media_root=MEDIA):
    """Parse, select, join and stamp: `(meta, items, fluids)` ready to write."""
    trees = load_trees(media_root)
    item_names, fluid_names = load_translations(media_root)
    items, fluids, misses = build(trees, item_names, fluid_names)
    counts = {kind: sum(1 for r in items if r["kind"] == kind)
              for kind in ("food", "drainable", "fluid_container")}
    counts["fluids"] = len(fluids)
    # Containers whose `Fluids` block lists more than one *distinct* id: only the first one's
    # nutrition reaches the row, so this is the count of rows whose columns are one of several
    # possible fills. 5 in 42.20.4; a container repeating a single id is not one of them.
    counts["multi_fluid_containers"] = sum(
        1 for r in items if r["fluid_ids"] and len(set(r["fluid_ids"])) > 1)
    # The fill split, over the same 133 rows: a container spawns holding its listed fluid
    # (`fluid_fill_litres`) or nothing at all. 72 + 61 in 42.20.4, and 9 of the 72 fill from a pool
    # rather than from one named fluid, which is what makes their nutrition one draw of several.
    counts["fluid_containers_filled"] = sum(1 for r in items if r["fluid_ids"])
    counts["fluid_containers_pick_random"] = sum(1 for r in items if r["fluid_pick_random"])
    counts["fluid_containers_empty"] = sum(1 for r in items if r["fluid_ids"] == [])
    counts["unresolved_links"] = len(misses["unresolved_links"])
    meta = {
        "build": BUILD,
        "jar_hash": JAR_HASH,
        "generated": datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
        "tool": "tools/food_scan.py",
        "sources": sorted(trees),
        "counts": counts,
        "unknown_keys": unknown_keys(items, fluids),
        "unresolved_links": misses["unresolved_links"],
        "missing_display_names": misses["missing_display_names"],
        "unresolved_fluid_refs": misses["unresolved_fluid_refs"],
    }
    return meta, items, fluids


def _cell(value):
    """A CSV cell. An absent value is the empty string -- never `0`, never `False`, never `None`."""
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, list):
        return ";".join(str(v) for v in value)
    return str(value)


def write_csv(path, items):
    """One row per item, CSV_HEADER order. Fluids are joined into those rows, never rows of their own."""
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        for record in items:
            writer.writerow([_cell(record[name]) for name in CSV_HEADER])


def write_json(path, meta, items, fluids):
    """`{"meta", "items", "fluids"}`; LF endings and a trailing newline, so the file is diffable."""
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump({"meta": meta, "items": items, "fluids": fluids}, handle,
                  indent=1, ensure_ascii=False)
        handle.write("\n")


def main():
    meta, items, fluids = build_dataset()
    write_json(OUT_JSON, meta, items, fluids)
    write_csv(OUT_CSV, items)
    counts = meta["counts"]
    print("food %d · drainable %d · fluid_container %d · fluids %d"
          % (counts["food"], counts["drainable"], counts["fluid_container"], counts["fluids"]))
    print("%d items, %d columns -> %s" % (len(items), len(CSV_HEADER), OUT_CSV))
    print("%d items + %d fluids -> %s" % (len(items), len(fluids), OUT_JSON))
    print("joins: %d unresolved links, %d missing display names, %d undefined fluid refs, "
          "%d unknown keys"
          % (len(meta["unresolved_links"]), len(meta["missing_display_names"]),
             len(meta["unresolved_fluid_refs"]), len(meta["unknown_keys"])))


if __name__ == "__main__":
    main()
