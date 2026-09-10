"""Tests for the shared script-block parser.

Fixtures are quoted verbatim from the 42.20.4 install (elided lines are whole
`Key = Value,` lines of the same block; every kept line is byte-exact). The
`# path:first-last` comment on each is the re-check anchor.
"""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import food_scan

SCRIPTS_ROOT = os.path.join(food_scan.MEDIA, "scripts", "generated")
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
"""                                     # fluids_Beverages.txt:1-36 (StressChange/alcohol/BlendWhiteList elided)

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


def test_flat_item_block_parses():
    apple = _one(APPLE, "item")
    assert apple["kind"] == "item" and apple["name"] == "Apple"
    assert apple["module"] == "Base"
    assert apple["props"]["Calories"] == "95.0"
    assert len(apple["props"]) == 13, sorted(apple["props"])
    assert apple["blocks"] == []
    assert apple["lines"] == []


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


@unittest.skipUnless(HAVE_INSTALL, "game install not present at %s" % SCRIPTS_ROOT)
def test_real_install_counts():
    def blocks_of(*rel):
        out = []
        for r in rel:
            path = os.path.join(SCRIPTS_ROOT, *r.split("/"))
            text = open(path, encoding="utf-8", errors="replace").read()
            out.extend(food_scan.iter_blocks(food_scan.parse_script(text, r)))
        return out

    food = blocks_of("items/food.txt")
    assert sum(1 for b in food if b["props"].get("ItemType") == "base:food") == 722

    drainable = blocks_of("items/drainable.txt")
    assert sum(1 for b in drainable if b["props"].get("ItemType") == "base:drainable") == 150

    fluids = blocks_of("fluids.txt", "fluids_Alcoholic.txt", "fluids_Beverages.txt")
    assert sum(1 for b in fluids if b["kind"] == "fluid") == 61

    items_dir = os.path.join(SCRIPTS_ROOT, "items")
    names = sorted(f for f in os.listdir(items_dir) if f.endswith(".txt"))
    every = blocks_of(*["items/" + f for f in names])
    containers = [b for b in every if b["kind"] == "component" and b["name"] == "FluidContainer"]
    assert len(containers) == 133
    # nesting is real: every one of them sits inside an item, not at module level
    assert all(b["module"] == "Base" for b in containers)


@unittest.skipUnless(HAVE_INSTALL, "game install not present at %s" % SCRIPTS_ROOT)
def test_load_translations_reads_both_files():
    items, fluids = food_scan.load_translations(food_scan.MEDIA)
    assert items["Base.Apple"] == "Apple"
    assert fluids["Fluid_Name_Cola"] == "Cola"
    assert len(items) > 4000 and len(fluids) > 100
