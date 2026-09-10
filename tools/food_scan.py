#!/usr/bin/env python3
"""Shared reader for the vanilla script DSL (items, fluids, recipes, entities).

Stdlib only. The DSL is `module <M> { <kind> <Name> { Key = Value, ... <kind> <Name> { ... } } }`;
blocks nest (a drink is `item X { component FluidContainer { Fluids { fluid = Cola:1.0 } } }`),
so keys are kept **per block** and never flattened -- a `component FluidContainer`'s `Capacity`
must not land on the item that owns it. See docs/vanilla/food-item-model.md for what each key
means and `Item.DoParam` for the loader that reads them in-game.

`parse_script` is shared with tools/recipe_scan.py (slice 06), so it stays generic: any in-block
entry that is not `Key = Value` is kept verbatim in the block's `lines` -- a fluid's `Categories`
entries (`Beverage`) and a recipe's IO lines (`item 1 [Base.BreadSlices] flags[ItemCount]`).
`itemMapper`'s dotted pairs (`Base.Cow_Skull = Base.Cow_Head_Angus`) land there too, on purpose:
PROP_RE only accepts identifier keys, and a mapper repeats the same left-hand side, which a dict
would silently collapse.

The dataset writer (data/food-items.{csv,json}) is slice 05 Task 3 and is not here yet.
"""
import json, os, re

MEDIA = r"D:/SteamLibrary/steamapps/common/ProjectZomboid/media"

HEAD_RE = re.compile(r"^([A-Za-z]\w*)\s+(\S+)$")        # `item Apple`, `component FluidContainer`
BARE_RE = re.compile(r"^([A-Za-z]\w*)$")                # `Properties` / `Categories` / `Fluids`
PROP_RE = re.compile(r"^([A-Za-z_]\w*)\s*=\s*(.*?)\s*,?$")

_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _strip_comments(text):
    """Drop `//` and `/* */`, keeping the line count so recorded line numbers stay true.

    No file under media/scripts/generated/ carries either form in 42.20.4; mods do.
    """
    text = _BLOCK_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return _LINE_COMMENT_RE.sub("", text)


def _logical_lines(text):
    """Yield (line_number, stripped_text), splitting `craftRecipe MakeToast {` into two entries.

    Every shipped file puts the brace on its own line; the same-line form is a mod convention.
    """
    for n, raw in enumerate(_strip_comments(text).splitlines(), 1):
        s = raw.strip()
        if len(s) > 1 and s.endswith("{") and "=" not in s:
            yield n, s[:-1].strip()
            s = "{"
        if s:
            yield n, s


def parse_script(text, path=""):
    """Parse one script file into a list of top-level (usually `module`) Blocks.

    Block = {"kind", "name", "module", "file", "line", "props": {k: raw_str},
             "lines": [str], "blocks": [Block]}
    `line` is the 1-based line of the block's header, `props` values stay raw (see `coerce`).
    """
    roots, stack, module, pending = [], [], "Base", None
    for n, s in _logical_lines(text):
        if s == "{":
            head = pending or {"kind": "?", "name": "?", "line": n}
            block = {"kind": head["kind"], "name": head["name"], "module": module,
                     "file": path, "line": head["line"], "props": {}, "lines": [], "blocks": []}
            (stack[-1]["blocks"] if stack else roots).append(block)
            stack.append(block)
            pending = None
            continue
        if s == "}":
            if stack:
                stack.pop()
            continue
        m = PROP_RE.match(s)                    # before HEAD_RE: `Weight =0.2` is a prop, not a header
        if m:
            if stack:
                stack[-1]["props"][m.group(1)] = m.group(2)
            continue
        m = HEAD_RE.match(s)
        if m:
            if m.group(1) == "module":
                module = m.group(2)
            pending = {"kind": m.group(1), "name": m.group(2), "line": n}
            continue
        m = BARE_RE.match(s)
        if m:
            pending = {"kind": "block", "name": m.group(1), "line": n}
            continue
        if stack:
            stack[-1]["lines"].append(s[:-1].rstrip() if s.endswith(",") else s)
    return roots


def iter_blocks(blocks):
    """Yield every block depth-first, parents before children."""
    for block in blocks:
        yield block
        yield from iter_blocks(block["blocks"])


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


def is_known_key(key):
    """False for a key no loader branch reads -- it becomes `defaultModData`, not an error."""
    return key.lower() in _KEY_TYPES_CI


def coerce(key, raw):
    """Type a raw script value the way the loader does; an unknown key stays a string.

    Bool is `Boolean.parseBoolean` / `equalsIgnoreCase("true")`: only the literal `true` is true.
    A value the loader would reject (`InvalidParameterException`) is returned unchanged rather
    than raised, so one malformed mod item cannot abort a whole-tree scan.
    """
    value_type = _KEY_TYPES_CI.get(key.lower(), str)
    if value_type is bool:
        return raw.strip().lower() == "true"
    if value_type is list:
        return [part for part in (p.strip() for p in raw.split(";")) if part]
    if value_type in (int, float):
        try:
            return value_type(raw.strip())
        except ValueError:
            return raw
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
