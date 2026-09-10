"""Tests for the shared script-block parser.

Fixtures are quoted verbatim from the 42.20.4 install; every kept line is byte-exact and each
fixture's `# path:first-last` comment is the re-check anchor, naming whatever it elides (whole
`Key = Value,` lines, and for COLA a whole nested block).
"""
import csv, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import food_scan

SCRIPTS_DIR = os.path.join(food_scan.MEDIA, "scripts")
SCRIPTS_ROOT = os.path.join(SCRIPTS_DIR, "generated")
HAVE_INSTALL = os.path.isdir(SCRIPTS_ROOT)

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

STEAK = """module Base
{
    item Steak
    {
        DisplayCategory = Food,
        ItemType = base:food,
        Weight = 0.3,
        BadCold = true,
        BadInMicrowave = true,
        DangerousUncooked = true,
        EvolvedRecipe = Pizza:20;Stew:20;Stir fry:20;Sandwich:5|Cooked;Salad:10|Cooked;Pasta:20;Rice:20;Taco:5|Cooked;Burrito:10|Cooked;AddBaitToChum:20,
        FoodType = Beef,
        GoodHot = true,
        IsCookable = true,
        MinutesToCook = 50,
        MinutesToBurn = 70,
        DaysFresh = 2,
        DaysTotallyRotten = 4,
        HungerChange = -40.0,
        Calories = 220.0,
        Carbohydrates = 0.0,
        Lipids = 9.35,
        Proteins = 31.62,
        FishingLure = true,
    }
}
"""                                     # items/food.txt:9774-9800 (Icon/*Model/CookingSound elided)

SALT = """module Base
{
    item Salt
    {
        DisplayCategory = Food,
        EatType = GlugFood,
        ItemType = base:food,
        Weight = 0.2,
        CantBeFrozen = true,
        EvolvedRecipe = Pizza:1;Soup:1;Stew:1;Pie:1;Stir fry:1;Burger:1;Hotdog:1;Salad:1;Rice:1;Pasta:1;Sandwich:1;Taco:1;Burrito:1,
        Spice = true,
        HungerChange = -10.0,
        ThirstChange = 20.0,
        UnhappyChange = 20,
        FoodType = NoExplicit,
        Tags = base:minoringredient;base:salt,
    }
}
"""                                     # items/food.txt:13488-13505 (Icon/*Model elided)

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
"""                                     # items/normal.txt:7038-7062 (Icon/*Model/FillFrom* elided)

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
"""                                     # fluids_Beverages.txt:1-36; elided from `Properties` are the
                                        # 6 lines StressChange/alcohol/fluReduction/painReduction/
                                        # enduranceChange/foodSicknessChange, plus the whole sibling
                                        # block `BlendWhiteList { whitelist, categories { Beverage } }`

HAIRDYE = """module Base
{
    item HairDyeCommon
    {
        DisplayCategory = Appearance,
        ItemType = base:normal,
        Weight = 0.1,
        OnCreate = ItemCodeOnCreate.onCreateHairDyeBottle,
        Icon = HairDye,
        IconFluidMask = HairDye_Mask,
        WorldStaticModel = HairDyeBlond,
        component FluidContainer
        {
            ContainerName = BottleHairDye,
            PickRandomFluid = true,
            Capacity = 1.0,
            Fluids
            {
                fluid = HairDye:1.0:0.1:0.09:0.08,
                fluid = HairDye:1.0:0.83:0.67:0.27,
                fluid = HairDye:1.0:0.74:0.35:0.13,
                fluid = HairDye:1.0:0.62:0.42:0.17,
                fluid = HairDye:1.0:0.4:0.26:0.09,
                fluid = HairDye:1.0:1.0:0.84:0.45,
                fluid = HairDye:1.0:0.59:0.23:0.03,
                fluid = HairDye:1.0:1.0:0.18:0.4,
            }
        }
    }
}
"""                                     # items/normal.txt:2653-2679 (whole block, nothing elided)

HANDTORCH = """module Base
{
    item HandTorch
    {
        DisplayCategory = LightSource,
        ItemType = base:drainable,
        Weight = 0.5,
        Icon = Flashlight2,
        ActivatedItem = true,
        DisappearOnUse = false,
        KeepOnDeplete = true,
        LightDistance = 15,
        LightStrength = 1.8,
        MetalValue = 10.0,
        TorchCone = true,
        TorchDot = 0.5,
        UseDelta = 0.006,
        cantBeConsolided = true,
        primaryAnimMask = HoldingTorchRight,
        secondaryAnimMask = HoldingTorchLeft,
        StaticModel = HandTorch,
        WorldStaticModel = HandTorchGround,
        Tags = base:flashlight;base:flashlightpillar,
        SoundMap = Activate FlashlightOn,
        SoundMap = Deactivate FlashlightOff,
        Researchablerecipes = MakeImprovisedFlashlight;MakeImprovisedLantern,
    }
}
"""                                     # items/drainable.txt:979-1003 (whole block, nothing elided)

STIRFRY = """module Base
{
    evolvedrecipe Stir fry
    {
        BaseItem = Base.Pan,
        MaxItems = 4,
        ResultItem = Base.PanFriedVegetables,
        Cookable = true,
        Name = Prepare Stir-fry,
        Template = Stir fry,
    }
}
"""                                     # evolvedrecipes.txt:135-143 (whole block, nothing elided)

MAKETOAST = """module Base
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
}
"""                                     # entities/appliances/workstations/entity_toaster_craftRecipe.txt:1-18


def _one(text, kind, path=""):
    """The single block of `kind` anywhere in `text`."""
    hits = [b for b in food_scan.iter_blocks(food_scan.parse_script(text, path)) if b["kind"] == kind]
    assert len(hits) == 1, [(b["kind"], b["name"]) for b in hits]
    return hits[0]


def _named(block, name):
    return [b for b in block["blocks"] if b["name"] == name][0]


def _values(block, key):
    """Every value written to `key` in this block, in file order (see F2 / `entries`)."""
    return [raw for k, raw in block["entries"] if k == key]


def _pairs(blocks, parent=None):
    """Yield (parent_block_or_None, block) depth-first, so a test can assert real parenthood."""
    for block in blocks:
        yield parent, block
        yield from _pairs(block["blocks"], block)


def test_flat_item_block_parses():
    apple = _one(APPLE, "item")
    assert apple["kind"] == "item" and apple["name"] == "Apple"
    assert apple["module"] == "Base"
    assert apple["props"]["Calories"] == "95.0"
    assert len(apple["props"]) == 13, sorted(apple["props"])
    assert apple["blocks"] == []
    assert apple["lines"] == []
    # no key repeats here, so `entries` is `props` in file order
    assert apple["entries"] == list(apple["props"].items())
    assert apple["entries"][0] == ("DisplayCategory", "Food")


def test_typed_values():
    assert food_scan.coerce("Calories", "95.0") == 95.0
    assert food_scan.coerce("DaysFresh", "5") == 5
    assert food_scan.coerce("IsCookable", "true") is True
    assert food_scan.coerce("CannedFood", "TRUE") is True
    assert food_scan.coerce("Tags", "base:hasmetal;base:hideuncooked") == ["base:hasmetal", "base:hideuncooked"]


def test_bool_is_only_the_literal_true():
    """Item.DoParam uses Boolean.parseBoolean / equalsIgnoreCase("true") - nothing else is true."""
    assert food_scan.coerce("IsCookable", "false") is False
    assert food_scan.coerce("IsCookable", "1") is False
    assert food_scan.coerce("IsCookable", "yes") is False
    assert food_scan.coerce("IsCookable", "True") is True


def test_int_typed_key_with_a_float_literal():
    """The fluid files write `-10.0` into keys the item table types int - 141 such values."""
    properties = _named(_one(COLA, "fluid"), "Properties")
    assert properties["props"]["UnhappyChange"] == "-10.0"          # raw, straight off the line
    unhappy = food_scan.coerce("UnhappyChange", properties["props"]["UnhappyChange"])
    assert unhappy == -10 and isinstance(unhappy, int)              # not the string "-10.0"
    record = food_scan.coerce_props(properties["props"])
    assert record["UnhappyChange"] == -10 and isinstance(record["UnhappyChange"], int)
    assert record["Calories"] == 400.0                              # a float key is untouched
    assert food_scan.coerce("fluReduction", "0.0") == 0
    assert food_scan.coerce("StressChange", "-20.0") == -20
    # a fractional literal on an int key keeps its value rather than truncating it
    assert food_scan.coerce("UnhappyChange", "-10.5") == -10.5
    # and a value neither parse accepts still falls back to the raw string
    assert food_scan.coerce("UnhappyChange", "n/a") == "n/a"


def test_value_with_spaces_and_pipe():
    apple = _one(APPLE, "item")
    evolved = food_scan.coerce("EvolvedRecipe", apple["props"]["EvolvedRecipe"])
    assert len(evolved) == 7
    assert evolved[0] == "Cake:16" and evolved[-1] == "Salad:8"

    steak = _one(STEAK, "item")
    evolved = food_scan.coerce("EvolvedRecipe", steak["props"]["EvolvedRecipe"])
    assert len(evolved) == 10
    assert "Stir fry:20" in evolved            # a space inside a value survives
    assert "Sandwich:5|Cooked" in evolved      # the `|Cooked` suffix is not a separator
    assert "Sandwich:5" not in evolved


def test_nested_component_is_not_flattened():
    pop2 = _one(POP2, "item")
    assert "Capacity" not in pop2["props"]
    assert "ContainerName" not in pop2["props"]
    component = pop2["blocks"][0]
    assert component["kind"] == "component" and component["name"] == "FluidContainer"
    assert component["props"]["Capacity"] == "0.3"
    fluids = component["blocks"][0]
    assert fluids["name"] == "Fluids"
    assert fluids["props"]["fluid"] == "Cola:1.0"


def test_fluid_block_properties():
    cola = _one(COLA, "fluid")
    assert cola["name"] == "Cola"
    assert [b["name"] for b in cola["blocks"]] == ["Categories", "Properties"]
    assert _named(cola, "Properties")["props"]["Calories"] == "400.0"
    assert _named(cola, "Categories")["lines"] == ["Beverage"]
    assert _named(cola, "Categories")["props"] == {}
    assert _named(cola, "Categories")["entries"] == []


def test_repeated_key_kept_in_entries():
    """`item HairDyeCommon` writes 8 `fluid =` lines into one `Fluids` block; props keeps 1."""
    hairdye = _one(HAIRDYE, "item")
    fluids = _named(hairdye["blocks"][0], "Fluids")
    fluid_values = _values(fluids, "fluid")
    assert len(fluid_values) == 8
    assert fluid_values[0] == "HairDye:1.0:0.1:0.09:0.08"          # file order is preserved
    assert fluid_values[3] == "HairDye:1.0:0.62:0.42:0.17"
    assert fluid_values[-1] == "HairDye:1.0:1.0:0.18:0.4"
    assert fluids["props"]["fluid"] == fluid_values[-1]             # props is last-write-wins
    assert len(fluids["props"]) == 1 and len(fluids["entries"]) == 8
    assert fluids["lines"] == []                                   # they are props, not junk lines


def test_repeated_soundmap_kept():
    """`item HandTorch` maps two sounds; the doc's table counts both."""
    torch = _one(HANDTORCH, "item")
    assert _values(torch, "SoundMap") == ["Activate FlashlightOn", "Deactivate FlashlightOff"]
    assert torch["props"]["SoundMap"] == "Deactivate FlashlightOff"
    assert len(torch["entries"]) == len(torch["props"]) + 1        # exactly one collapsed repeat
    assert food_scan.coerce("SoundMap", _values(torch, "SoundMap")[0]) == ["Activate FlashlightOn"]


def test_multi_word_block_name():
    """A header is a header because the next line is `{` - so its name may contain spaces."""
    stirfry = _one(STIRFRY, "evolvedrecipe")
    assert stirfry["kind"] == "evolvedrecipe" and stirfry["name"] == "Stir fry"
    assert stirfry["line"] == 3
    assert stirfry["props"]["Name"] == "Prepare Stir-fry"
    assert stirfry["props"]["Template"] == "Stir fry"
    module = food_scan.parse_script(STIRFRY)[0]
    assert module["lines"] == []               # the header is not mis-filed as a line of the module
    assert [b["name"] for b in module["blocks"]] == ["Stir fry"]
    # the converse: a line no `{` follows stays a line even though it looks like `kind name`
    assert _named(_one(MAKETOAST, "craftRecipe"), "outputs")["lines"] == ["item 1 Base.Toast"]


def test_absent_key_is_absent_not_zero():
    salt = _one(SALT, "item")
    assert "Calories" not in salt["props"]
    record = food_scan.coerce_props(salt["props"])
    assert record.get("Calories") is None          # absent, never 0.0
    assert record["ThirstChange"] == 20.0          # positive: must not be sign-flipped
    assert record["UnhappyChange"] == 20 and isinstance(record["UnhappyChange"], int)
    assert record["Spice"] is True


def test_line_numbers_recorded():
    apple = _one(APPLE, "item", path="items/food.txt")
    assert apple["line"] == 3                      # the `item Apple` line, 1-based
    assert apple["file"] == "items/food.txt"
    module = food_scan.parse_script(APPLE)[0]
    assert module["kind"] == "module" and module["line"] == 1


def test_recipe_io_lines_kept():
    recipe = _one(MAKETOAST, "craftRecipe")
    assert recipe["name"] == "MakeToast"
    assert recipe["props"]["time"] == "20"
    assert _named(recipe, "inputs")["lines"] == ["item 1 [Base.BreadSlices] flags[ItemCount]"]
    assert _named(recipe, "outputs")["lines"] == ["item 1 Base.Toast"]


def test_same_line_brace_header():
    """No shipped file under generated/ uses it, but mods do; parse it the same way."""
    same_line = MAKETOAST.replace("MakeToast\n    {", "MakeToast {").replace("inputs\n        {", "inputs {")
    recipe = _one(same_line, "craftRecipe")
    assert recipe["line"] == 3
    assert recipe["props"]["time"] == "20"
    assert _named(recipe, "inputs")["lines"] == ["item 1 [Base.BreadSlices] flags[ItemCount]"]


def test_comments_stripped_without_shifting_line_numbers():
    text = APPLE.replace("    item Apple\n", "    // a note\n    /* two\n       lines */\n    item Apple\n")
    apple = _one(text, "item")
    assert apple["line"] == 6                      # 3 comment lines inserted before line 3
    assert apple["props"]["Calories"] == "95.0"
    assert apple["lines"] == []


def test_unknown_key_stays_a_string():
    """Item.DoParam's fall-through writes an unrecognised key to defaultModData - not an error."""
    assert food_scan.coerce("SomeModKey", "12") == "12"
    assert food_scan.is_known_key("SomeModKey") is False
    assert food_scan.is_known_key("Calories") is True
    assert food_scan.is_known_key("foodsicknesschange") is True   # matched case-insensitively


def test_canonical_key():
    """The fluid files' `foodSicknessChange` is the item files' `FoodSicknessChange`."""
    assert food_scan.canonical_key("foodSicknessChange") == "FoodSicknessChange"
    assert food_scan.canonical_key("FOODSICKNESSCHANGE") == "FoodSicknessChange"
    assert food_scan.canonical_key("Calories") == "Calories"
    assert food_scan.canonical_key("fluReduction") == "fluReduction"   # lowercase in the table too
    assert food_scan.canonical_key("SomeModKey") == "SomeModKey"       # unknown: unchanged
    # canonicalising never changes how the value types
    assert food_scan.coerce(food_scan.canonical_key("foodSicknessChange"), "0") == \
        food_scan.coerce("foodSicknessChange", "0")


def test_malformed_value_falls_back_to_string():
    """A mod's junk value must not abort a whole-tree scan."""
    assert food_scan.coerce("Calories", "n/a") == "n/a"
    assert food_scan.coerce("DaysFresh", "") == ""


def test_key_types_covers_the_114_documented_keys():
    assert len(food_scan.KEY_TYPES) == 114
    lists = sorted(k for k, t in food_scan.KEY_TYPES.items() if t is list)
    assert lists == ["EvolvedRecipe", "IconsForTexture", "ReplaceOnCooked", "RequireInHandOrInventory",
                     "Researchablerecipes", "SoundMap", "StaticModelsByIndex", "Tags",
                     "WorldStaticModelsByIndex"]
    # the two dead keys are still transcribed, as strings: they land in defaultModData
    assert food_scan.KEY_TYPES["IsWaterSource"] is str
    assert food_scan.KEY_TYPES["RainFactor"] is str


def _roots_of(*rel):
    out = []
    for r in rel:
        path = os.path.join(SCRIPTS_ROOT, *r.split("/"))
        text = open(path, encoding="utf-8", errors="replace").read()
        out.extend(food_scan.parse_script(text, r))
    return out


@unittest.skipUnless(HAVE_INSTALL, "game install not present at %s" % SCRIPTS_ROOT)
def test_real_install_counts():
    def blocks_of(*rel):
        return list(food_scan.iter_blocks(_roots_of(*rel)))

    food = blocks_of("items/food.txt")
    assert sum(1 for b in food if b["props"].get("ItemType") == "base:food") == 722

    drainable = blocks_of("items/drainable.txt")
    assert sum(1 for b in drainable if b["props"].get("ItemType") == "base:drainable") == 150

    fluids = blocks_of("fluids.txt", "fluids_Alcoholic.txt", "fluids_Beverages.txt")
    assert sum(1 for b in fluids if b["kind"] == "fluid") == 61

    items_dir = os.path.join(SCRIPTS_ROOT, "items")
    names = sorted(f for f in os.listdir(items_dir) if f.endswith(".txt"))
    every = _roots_of(*["items/" + f for f in names])
    containers = [(p, b) for p, b in _pairs(every)
                  if b["kind"] == "component" and b["name"] == "FluidContainer"]
    assert len(containers) == 133
    # nesting is real: every one of them sits inside an `item`, never at module level
    assert {p["kind"] for p, b in containers} == {"item"}
    assert {p["module"] for p, b in containers} == {"Base"}


@unittest.skipUnless(HAVE_INSTALL, "game install not present at %s" % SCRIPTS_ROOT)
def test_real_install_repeated_keys():
    """`props` alone drops 3512 repeat lines across generated/; `entries` keeps them."""
    normal = list(food_scan.iter_blocks(_roots_of("items/normal.txt")))
    pools = [b for b in normal if b["name"] == "Fluids"]
    assert len(pools) == 68
    assert sum(len(_values(b, "fluid")) for b in pools) == 145      # props alone would keep 68 …
    assert sum(1 for b in pools if len(_values(b, "fluid")) > 1) == 9   # … losing 77 lines, from 9
    hairdye = [b for b in normal if b["kind"] == "item" and b["name"] == "HairDyeCommon"][0]
    assert hairdye["line"] == 2653
    assert len(_values(_named(hairdye["blocks"][0], "Fluids"), "fluid")) == 8

    drainable = list(food_scan.iter_blocks(_roots_of("items/drainable.txt")))
    assert sum(len(_values(b, "SoundMap")) for b in drainable) == 34   # the doc's table
    assert sum(1 for b in drainable if "SoundMap" in b["props"]) == 27  # what props alone sees


@unittest.skipUnless(HAVE_INSTALL, "game install not present at %s" % SCRIPTS_ROOT)
def test_real_install_has_no_anonymous_blocks():
    """Every `{` under generated/ is opened by a header, including the 156 a `(\\S+)$` name misses."""
    total, multi_word, numbered = 0, 0, 0
    for dirpath, _dirs, names in os.walk(SCRIPTS_ROOT):
        for name in names:
            if not name.endswith(".txt"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, SCRIPTS_ROOT).replace("\\", "/")
            text = open(path, encoding="utf-8", errors="replace").read()
            for block in food_scan.iter_blocks(food_scan.parse_script(text, rel)):
                total += 1
                assert block["kind"] and block["name"], (rel, block["line"], block)
                assert "?" not in (block["kind"], block["name"]), (rel, block["line"], block)
                if " " in block["name"]:
                    multi_word += 1
                elif block["kind"] == "block" and not block["name"].isidentifier():
                    numbered += 1
    assert total == 34683                    # == the 34683 `{` lines these files contain
    assert multi_word == 114                 # 87 vehicles, 19 `fixing Fix …`, 6 evolved, 2 traits
    assert numbered == 42                    # vehicle templates' `items { 1 { … } }` step indices
    assert multi_word + numbered == 156       # the whole set the old header regex made anonymous

    evolved = list(food_scan.iter_blocks(_roots_of("evolvedrecipes.txt")))
    assert sum(1 for b in evolved if b["kind"] == "evolvedrecipe") == 62
    stirfry = [b for b in evolved if b["name"] == "Stir fry"][0]
    assert stirfry["kind"] == "evolvedrecipe" and stirfry["line"] == 135


@unittest.skipUnless(os.path.isdir(os.path.join(SCRIPTS_DIR, "xui")),
                     "game install not present at %s" % SCRIPTS_DIR)
def test_real_block_comments_stripped():
    """28 files under media/scripts/xui/ ship `/* */`; nothing under generated/ does."""
    rel = "xui/defaultskin/xs_ISButton.txt"
    text = open(os.path.join(SCRIPTS_DIR, *rel.split("/")), encoding="utf-8", errors="replace").read()
    assert "/*" in text                            # the file really is a comment fixture
    blocks = list(food_scan.iter_blocks(food_scan.parse_script(text, rel)))
    assert len(blocks) == 12, [(b["kind"], b["name"]) for b in blocks]
    assert [b["kind"] for b in blocks[:3]] == ["module", "xuiSkin", "block"]
    assert [b["name"] for b in blocks[:3]] == ["Base", "default", "ISButton"]
    for block in blocks:
        for key, raw in block["entries"]:
            assert "/*" not in raw and "*/" not in raw and "/*" not in key, (block["name"], key, raw)
        assert not any("/*" in line or "*/" in line for line in block["lines"]), block["name"]
    assert "title" not in blocks[2]["props"]       # `/* optional: title = some title, */`
    debug = [b for b in blocks if b["name"] == "S_Button_DebugCraft"][0]
    assert "backgroundColor" not in debug["props"]  # `/*backgroundColor = SandyBrown,*/`
    assert debug["props"]["borderColor"] == "Orange"
    assert debug["props"]["title"] == '"Debug Craft"'


@unittest.skipUnless(HAVE_INSTALL, "game install not present at %s" % SCRIPTS_ROOT)
def test_load_translations_reads_both_files():
    items, fluids = food_scan.load_translations(food_scan.MEDIA)
    assert items["Base.Apple"] == "Apple"
    assert fluids["Fluid_Name_Cola"] == "Cola"
    assert len(items) > 4000 and len(fluids) > 100


# ---------------------------------------------------------------------------------------------
# The dataset half: the selection rule, the joins, and the two writers
# ---------------------------------------------------------------------------------------------

HAIRDYE_FLUID = """module Base
{
    fluid HairDye
    {
        ColorReference = White,
        DisplayName = Fluid_Name_HairDye,
        Categories
        {
            Colors,
            HairDyes,
            Industrial,
            Hazardous,
        }
        Poison
        {
            maxEffect = Medium,
            minAmount = 0.2,
            diluteRatio = 0.1,
        }
    }
}
"""                                     # fluids.txt:274-298 (the whole BlendWhiteList block
                                        # elided); it has no `Properties` -- 10 of the 61 do not

# The next three are SYNTHETIC, not quoted from the install: 42.20.4 ships no such item. They
# pin rules the shipped files never exercise -- see test_selection_rule_is_first_match_wins and
# test_replace_links_resolve_against_the_dataset.
FOOD_WITH_CONTAINER = """module Base
{
    item TestFoodFlask
    {
        DisplayCategory = Food,
        ItemType = base:food,
        Weight = 0.4,
        Calories = 11.0,
        component FluidContainer
        {
            Capacity = 2.0,
            Fluids
            {
                fluid = Cola:1.0,
            }
        }
    }
}
"""

NOT_FOOD = """module Base
{
    item TestPlate
    {
        DisplayCategory = Food,
        ItemType = base:normal,
        Weight = 0.4,
    }
}
"""

DANGLING = """module Base
{
    item TestCanteen
    {
        DisplayCategory = Food,
        ItemType = base:drainable,
        Weight = 0.4,
        ReplaceOnUse = Base.Nowhere,
        ReplaceOnCooked = Base.Salt,
    }
}
"""


def _file(*fixtures):
    """One `module Base { ... }` text holding every fixture's blocks, so `select` sees one file."""
    body = []
    for text in fixtures:
        body.extend(text.strip().splitlines()[2:-1])   # drop `module Base` / `{` and the final `}`
    return "module Base\n{\n" + "\n".join(body) + "\n}\n"


def _trees(files):
    """{relative path: text} -> the {relative path: [Block]} shape `select` and `build` take."""
    return {rel: food_scan.parse_script(text, rel) for rel, text in files.items()}


def _dataset(files, item_names=None, fluid_names=None):
    """(items_by_id, fluids_by_id, misses) for a synthetic tree."""
    items, fluids, misses = food_scan.build(_trees(files), item_names, fluid_names)
    return {r["id"]: r for r in items}, {r["id"]: r for r in fluids}, misses


def _csv_rows(items):
    """Round-trip `items` through write_csv and read the file back."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "food-items.csv")
        food_scan.write_csv(path, items)
        with open(path, encoding="utf-8", newline="") as handle:
            raw = handle.read()
        assert "\r" not in raw                             # lineterminator="\n" with newline=""
        return list(csv.reader(raw.splitlines()))


SAMPLE = {
    "items/food.txt": _file(APPLE, SALT, NOT_FOOD),
    "items/drainable.txt": _file(HANDTORCH, DANGLING),
    "items/normal.txt": _file(POP2, HAIRDYE),
    "fluids_Beverages.txt": COLA,
    "fluids.txt": HAIRDYE_FLUID,
}


def test_selection_rule_assigns_one_kind_per_record():
    """(a) base:food in food.txt, (b) base:drainable in drainable.txt, (c) any FluidContainer."""
    items, fluids, _misses = _dataset(SAMPLE)
    assert {i: r["kind"] for i, r in items.items()} == {
        "Base.Apple": "food", "Base.Salt": "food",
        "Base.HandTorch": "drainable", "Base.TestCanteen": "drainable",
        "Base.Pop2": "fluid_container", "Base.HairDyeCommon": "fluid_container",
    }
    assert "Base.TestPlate" not in items          # in food.txt, but its ItemType is base:normal
    assert sorted(fluids) == ["Cola", "HairDye"]  # fluids are records, never CSV rows
    assert items["Base.Apple"]["source_file"] == "items/food.txt"
    assert items["Base.Apple"]["source_line"] == 3


def test_selection_rule_is_first_match_wins():
    """A base:food item that also owns a FluidContainer is one record, kind `food`, not two.

    No 42.20.4 item does this -- the three item rules are disjoint on the real install (see
    test_real_dataset_counts) -- so the fixture is synthetic and the rule is the guard.
    """
    items, _fluids, _misses = _dataset({"items/food.txt": FOOD_WITH_CONTAINER,
                                        "fluids_Beverages.txt": COLA})
    assert list(items) == ["Base.TestFoodFlask"]
    record = items["Base.TestFoodFlask"]
    assert record["kind"] == "food"
    # claimed by rule (a), so its own Calories stand and no fluid is joined
    assert record["nutrition_source"] == "food_keys" and record["calories"] == 11.0
    assert record["fluid_capacity"] is None and record["fluid_ids"] is None


def test_display_name_join_and_its_misses():
    items, fluids, misses = _dataset(SAMPLE, item_names={"Base.Apple": "Apple"},
                                     fluid_names={"Fluid_Name_Cola": "Cola"})
    assert items["Base.Apple"]["display_name"] == "Apple"
    assert items["Base.Salt"]["display_name"] is None         # absent, not the raw id
    assert fluids["Cola"]["display_name"] == "Cola"
    assert fluids["Cola"]["display_name_key"] == "Fluid_Name_Cola"
    assert fluids["HairDye"]["display_name"] is None
    assert misses["missing_display_names"] == [
        "Base.HairDyeCommon", "Base.HandTorch", "Base.Pop2", "Base.Salt", "Base.TestCanteen",
        "fluid:HairDye"]


def test_fluid_container_joins_the_first_listed_fluid():
    items, _fluids, misses = _dataset(SAMPLE)
    pop2 = items["Base.Pop2"]
    assert pop2["fluid_capacity"] == 0.3                       # the component's Capacity, typed
    assert pop2["fluid_ids"] == ["Cola"]
    assert pop2["nutrition_source"] == "fluid:Cola"
    assert pop2["calories"] == 400.0 and pop2["carbohydrates"] == 104.0
    assert pop2["unhappy_change"] == -10 and isinstance(pop2["unhappy_change"], int)
    assert pop2["item_type"] == "base:normal"                  # the item's own keys still stand
    assert pop2["days_fresh"] is None                          # a drink has none: absent, not 0

    # every `fluid =` value's first `:` field, in file order -- HairDyeCommon really lists 8
    hairdye = items["Base.HairDyeCommon"]
    assert hairdye["fluid_ids"] == ["HairDye"] * 8
    assert hairdye["nutrition_source"] == "fluid:HairDye"
    # HairDye is defined but carries no `Properties` block, so the joined nutrition is empty
    assert hairdye["calories"] is None and hairdye["thirst_change"] is None
    assert misses["unresolved_fluid_refs"] == []


def test_fluid_record_keeps_what_no_column_takes():
    _items, fluids, _misses = _dataset(SAMPLE)
    cola = fluids["Cola"]
    assert cola["categories"] == ["Beverage"]
    assert cola["fatigue_change"] == -2.0 and cola["boredom_change"] is None
    assert cola["poison"] is None
    assert cola["props_raw"] == {"ColorReference": "Cola", "DisplayName": "Fluid_Name_Cola"}
    assert cola["source_file"] == "fluids_Beverages.txt" and cola["source_line"] == 3
    hairdye = fluids["HairDye"]
    assert hairdye["categories"] == ["Colors", "HairDyes", "Industrial", "Hazardous"]
    assert hairdye["poison"] == {"diluteRatio": "0.1", "maxEffect": "Medium", "minAmount": "0.2"}
    assert hairdye["properties_raw"] == {}


def test_absent_key_is_null_in_json_and_empty_in_csv():
    """The dataset never invents a 0: Salt has no Calories line, so it has no calories."""
    items, _fluids, _misses = _dataset(SAMPLE)
    salt = items["Base.Salt"]
    assert salt["calories"] is None and salt["carbohydrates"] is None
    assert salt["thirst_change"] == 20.0                       # positive, not sign-flipped
    assert set(salt) == set(food_scan.CSV_HEADER) | {"props_raw"}   # every column, on every row
    row = _csv_rows([salt])[1]
    assert row[food_scan.CSV_HEADER.index("calories")] == ""
    assert row[food_scan.CSV_HEADER.index("thirst_change")] == "20.0"
    assert row[food_scan.CSV_HEADER.index("spice")] == "true"
    assert row[food_scan.CSV_HEADER.index("tags")] == "base:minoringredient;base:salt"
    # a real zero still prints as a zero -- only an absent key is blank
    assert food_scan._cell(0) == "0" and food_scan._cell(0.0) == "0.0"
    assert food_scan._cell(False) == "false" and food_scan._cell(None) == ""
    assert food_scan._cell([]) == ""


def test_csv_header_is_the_documented_schema():
    assert food_scan.CSV_HEADER == [
        "id", "module", "name", "kind", "display_name", "display_category", "food_type",
        "item_type", "tags", "nutrition_source", "calories", "carbohydrates", "lipids",
        "proteins", "hunger_change", "thirst_change", "days_fresh", "days_totally_rotten",
        "cant_be_frozen", "is_cookable", "minutes_to_cook", "minutes_to_burn",
        "dangerous_uncooked", "packaged", "canned_food", "cant_eat", "spice", "good_hot",
        "bad_cold", "unhappy_change", "boredom_change", "stress_change", "fatigue_change",
        "endurance_change", "food_sickness_change", "poison_power", "alcohol_power",
        "evolved_recipe", "evolved_recipe_name", "replace_on_cooked", "replace_on_rotten",
        "replace_on_use", "on_cooked", "on_eat", "fluid_capacity", "fluid_ids", "weight",
        "source_file", "source_line"]
    assert len(food_scan.COLUMNS) == 47 and len(food_scan.CSV_HEADER) == 49
    assert len(set(food_scan.CSV_HEADER)) == 49
    # every column that names a script key names one the loader actually reads
    assert all(food_scan.is_known_key(key) for _name, key in food_scan.COLUMNS if key)
    items, _fluids, _misses = _dataset(SAMPLE)
    rows = _csv_rows([items[i] for i in sorted(items)])
    assert rows[0] == food_scan.CSV_HEADER and len(rows) == 1 + len(items)
    assert all(len(row) == 49 for row in rows)


def test_replace_links_resolve_against_the_dataset():
    items, _fluids, misses = _dataset(SAMPLE)
    assert misses["unresolved_links"] == [
        {"item": "Base.TestCanteen", "key": "ReplaceOnUse", "target": "Base.Nowhere"}]
    # ReplaceOnCooked = Base.Salt resolves, because Salt is a record of this dataset
    assert not any(m["key"] == "ReplaceOnCooked" for m in misses["unresolved_links"])
    canteen = items["Base.TestCanteen"]
    assert canteen["replace_on_use"] == "Base.Nowhere"          # the value is kept either way
    assert canteen["replace_on_cooked"] == ["Base.Salt"]        # list-typed in KEY_TYPES


def test_props_raw_is_verbatim_and_keeps_repeats():
    items, _fluids, _misses = _dataset(SAMPLE)
    raw = items["Base.HandTorch"]["props_raw"]
    assert raw["SoundMap"] == ["Activate FlashlightOn", "Deactivate FlashlightOff"]
    assert raw["Weight"] == "0.5" and raw["LightDistance"] == "15"   # raw strings, not typed
    assert raw["Tags"] == "base:flashlight;base:flashlightpillar"    # unsplit
    assert "Capacity" not in items["Base.Pop2"]["props_raw"]         # the component is not flattened
    assert items["Base.HandTorch"]["weight"] == 0.5                  # the typed column is typed


def test_unknown_keys_uses_is_known_key():
    """`foodSicknessChange` differs from the table only in case, so it must not be flagged."""
    items, fluids, _misses = _dataset(SAMPLE)
    unknown = food_scan.unknown_keys([items[i] for i in sorted(items)],
                                     [fluids[i] for i in sorted(fluids)])
    assert "foodSicknessChange" not in unknown and "fatigueChange" not in unknown
    for key in ("ColorReference", "DisplayName", "IconFluidMask", "Capacity", "fluid",
                "maxEffect", "minAmount", "diluteRatio"):
        assert key in unknown, key
    assert unknown == sorted(unknown)
    assert not any(food_scan.is_known_key(k) for k in unknown)


_REAL = []


def _real_dataset():
    """build_dataset() once, shared by the install-gated dataset tests."""
    if not _REAL:
        _REAL.append(food_scan.build_dataset())
    return _REAL[0]


@unittest.skipUnless(HAVE_INSTALL, "game install not present at %s" % SCRIPTS_ROOT)
def test_real_dataset_counts():
    meta, items, fluids = _real_dataset()
    assert meta["counts"] == {"food": 722, "drainable": 150, "fluid_container": 133,
                              "fluids": 61, "unresolved_links": 37}
    assert len(items) == 1005 and len(fluids) == 61
    assert len({r["id"] for r in items}) == 1005          # the three item rules really are disjoint
    assert sum(meta["counts"][k] for k in ("food", "drainable", "fluid_container")) == len(items)
    assert [r["id"] for r in items] == sorted(r["id"] for r in items)     # stable ordering
    assert [r["id"] for r in fluids] == sorted(r["id"] for r in fluids)
    assert len(meta["sources"]) == 18                     # 15 items/*.txt + 3 fluid files
    assert meta["build"] == "42.20.4" and meta["jar_hash"] == "b0bbce05d5"


@unittest.skipUnless(HAVE_INSTALL, "game install not present at %s" % SCRIPTS_ROOT)
def test_real_dataset_spot_values():
    """The three records the plan's eyeball command prints, straight off the install."""
    _meta, items, fluids = _real_dataset()
    by_id = {r["id"]: r for r in items}
    apple = by_id["Base.Apple"]
    assert (apple["calories"], apple["carbohydrates"], apple["days_fresh"],
            apple["display_name"]) == (95.0, 25.13, 5, "Apple")
    assert apple["source_file"] == "items/food.txt" and apple["source_line"] == 8658
    salt = by_id["Base.Salt"]
    assert salt["calories"] is None and salt["thirst_change"] == 20.0
    pop2 = by_id["Base.Pop2"]
    assert pop2["nutrition_source"] == "fluid:Cola" and pop2["calories"] == 400.0
    cola = {r["id"]: r for r in fluids}["Cola"]
    assert cola["calories"] == 400.0
    # the fluid files write `foodSicknessChange`; canonical_key lands it in the item column
    assert cola["food_sickness_change"] == 0 and pop2["food_sickness_change"] == 0
    assert cola["properties_raw"]["alcohol"] == "0.0"       # no column: kept raw, flagged unknown
    assert all(r["display_name"] for r in fluids)           # all 61 fluid names translate


@unittest.skipUnless(HAVE_INSTALL, "game install not present at %s" % SCRIPTS_ROOT)
def test_real_dataset_join_misses():
    """Every miss is recorded, including one link 42.20.4 names but never defines."""
    meta, _items, _fluids = _real_dataset()
    assert meta["missing_display_names"] == [
        "Base.FruitSaladClay", "Base.HotDrinkCopper", "Base.HotDrinkGold", "Base.HotDrinkMetal",
        "Base.HotDrinkSilver", "Base.HotDrinkTumbler"]
    assert meta["unresolved_fluid_refs"] == []             # every referenced fluid is defined
    assert len(meta["unresolved_links"]) == 37
    assert {m["key"] for m in meta["unresolved_links"]} == {"ReplaceOnUse", "ReplaceOnDeplete"}
    assert {"item": "Base.HotDrinkRed", "key": "ReplaceOnUse",
            "target": "Base.MugRed"} in meta["unresolved_links"]
    assert "alcohol" in meta["unknown_keys"]               # the one fluid property with no table
    assert not any(food_scan.is_known_key(k) for k in meta["unknown_keys"])
