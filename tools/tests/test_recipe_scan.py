"""Tests for the `craftRecipe` scanner.

Fixtures are quoted verbatim from the 42.20.4 install; every kept line is byte-exact and each
fixture's `# path:first-last` comment is the re-check anchor, naming whatever it elides. The
food rows are quoted twice over: `FOOD` in the script-key shape the plan's contract used, and
`DATASET` in the lowercase typed shape `data/food-items.json` actually ships (slice 05), so the
tests pin both halves of `FOOD_FIELDS`.
"""
import csv, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import recipe_scan

SCRIPTS_ROOT = os.path.join(recipe_scan.MEDIA, "scripts", "generated")
HAVE_INSTALL = os.path.isdir(SCRIPTS_ROOT)
FOOD_JSON = recipe_scan.FOOD_JSON
HAVE_FOOD = os.path.isfile(FOOD_JSON)

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

MILL = """module Base
{
    craftRecipe MillCornflour
    {
        time = 100,
        timedAction = UseStoneQuern,
        Tags = Stone_Mill,
        category = Farming,
        inputs
        {
            item 20 [Base.CornSeed] flags[ItemCount],
        }
        outputs
        {
            item 1 Base.Cornflour2,
        }
    }
}"""   # entities/agricultural/workstations/entity_stone_mill_craftRecipe.txt:1-18 (whole block)

DRYING = """module Base
{
    craftRecipe DryCorn
    {
        time = 172800,
        Tags = DryingRackGrain,
        category = Farming,
        overlayStyle = Corn,
        inputs
        {
            item variable[1:20] [Base.Corn] flags[ItemCount] mode:destroy,
        }
        outputs
        {
            item variable[1:20] Base.CornSeed,
        }
    }
}"""   # entities/agricultural/workstations/entity_Drying_Rack_craftRecipe.txt:1-17 (whole block)

FORGE = """module Base
{
    craftRecipe Forge_BarHalf_From_Chunk
    {
        time = 500,
        SkillRequired = Blacksmith:0,
        timedAction = HammerMetalStanding,
        Tags = PrimitiveForge,
        category = Blacksmithing,
        xpAward = Blacksmith:10,
        inputs
        {
            item 2 tags[base:charcoal],
            item 2 [Base.IronChunk;Base.SteelChunk;Base.IronBarQuarter;Base.SteelBarQuarter] mappers[metalType] flags[IsExclusive],
            item 1 tags[base:hammer;base:clubhammer] mode:keep flags[Prop1;MayDegradeLight],
        }
        outputs
        {
            item 1 mapper:metalType,
        }
        itemMapper metalType
        {
            Base.IronBarHalf = Base.IronChunk,
            Base.SteelBarHalf = Base.SteelChunk,
            Base.SteelBarHalf = Base.SteelBarQuarter,
            default = Base.IronBarHalf,
        }
    }
}"""   # entities/blacksmith/craftRecipes/recipes_blacksmith_bar.txt:56-82, the block's name and one
       # `mode:keep` tool line elided (`base:crudetongs`); 56 of the 225 mappers repeat a result
       # this way, and 134 write a `default`

MILK = """module Base
{
    craftRecipe MakeMilkFromPowderBucket
    {
        timedAction = Making,
        Icon = Item_WaterDrop,
        time = 70,
        Tags = InHandCraft;Cooking;CanBeDoneInDark,
        category = Cooking,
        OnCreate = RecipeCodeOnCreate.makeMilkFromPowder,
        inputs
        {
            item 1 tags[base:bucket] mode:keep,
            -fluid 10.0 [Water],
            item 10 [Base.AnimalMilkPowder],
        }
        outputs
        {
        }
    }
}"""   # recipes/recipes_cooking.txt:1-20 (whole block) -- an `outputs` block that is really empty

# `data/food-items.json` rows, trimmed to the columns a delta reads. Values are verbatim from the
# shipped dataset (`items/food.txt` lines in the comments); `Base.Cornflour2` writes no `Calories`
# line at all, which is why its four macro columns are null rather than 0.
DATASET = {
    "Base.CornSeed": {"nutrition_basis": "per_item", "calories": 24.8, "carbohydrates": 7.6,
                      "lipids": 0.56, "proteins": 1.32, "hunger_change": -4.0,
                      "thirst_change": None},                                    # food.txt:15006
    "Base.Cornflour2": {"nutrition_basis": "per_item", "calories": None, "carbohydrates": None,
                        "lipids": None, "proteins": None, "hunger_change": -60.0,
                        "thirst_change": None},                                  # food.txt:5236
    "Base.Corn": {"nutrition_basis": "per_item", "calories": 88.0, "carbohydrates": 19.0,
                  "lipids": 1.35, "proteins": 3.27, "hunger_change": -14.0,
                  "thirst_change": -5.0},                                        # food.txt:4834
    # a drink: its nutrition is the fluid's, per litre -- R3 says such a row blocks the delta
    "Base.Milk": {"nutrition_basis": "per_litre", "calories": 615.0, "carbohydrates": 49.0,
                  "lipids": 32.5, "proteins": 33.0, "hunger_change": -50.0,
                  "thirst_change": -80.0},
    # a row that carries no nutrition key on either side: basis null
    "Base.AnimalMilkPowder": {"nutrition_basis": None, "calories": None, "carbohydrates": None,
                              "lipids": None, "proteins": None, "hunger_change": None,
                              "thirst_change": None},
}


# --------------------------------------------------------------------------------------------
# The three tests of the plan's Task 2 Step 1, verbatim
# --------------------------------------------------------------------------------------------

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


# --------------------------------------------------------------------------------------------
# The grammar, the block shape and the delta rules the plan states in prose
# --------------------------------------------------------------------------------------------

def test_every_io_field_is_present_on_every_line():
    """A line that writes no `mode:` still has the key -- absent is null / empty, never missing."""
    line = recipe_scan.parse_io("item 1 [Base.Toast]")
    assert set(line) == set(recipe_scan.IO_FIELDS)
    assert (line["mode"], line["mapper"], line["variable"]) == (None, None, None)
    assert (line["tags"], line["categories"], line["flags"], line["mappers"]) == ([], [], [], [])
    assert line["overlayMapper"] is False and line["extras"] == []
    assert line["raw"] == "item 1 [Base.Toast]"


def test_consumed_is_mode_not_keep():
    """`mode:keep` is a tool, `mode:destroy` and a line with no mode at all are ingredients."""
    assert recipe_scan.parse_io("item 1 [Base.Saw] flags[AllowDestroyedItem] mode:destroy")["consumed"] is True
    assert recipe_scan.parse_io("item 6 tags[base:flour]")["consumed"] is True
    assert recipe_scan.parse_io("item 1 tags[base:rollingpin] mode:keep")["consumed"] is False


def test_bracket_lists_split_on_semicolons_and_drop_a_count_prefix():
    """86 bracket entries carry a `<count>:` prefix; the id is kept and `raw` keeps the line."""
    line = recipe_scan.parse_io("item 5 [Base.BurlapPiece;2:Base.CottonBalls] flags[Prop1;IsExclusive]")
    assert line["types"] == ["Base.BurlapPiece", "Base.CottonBalls"]
    assert line["flags"] == ["Prop1", "IsExclusive"]
    assert "2:Base.CottonBalls" in line["raw"]


def test_variable_amount_is_null_and_blocks_the_delta():
    """`variable[1:20]` is a player-chosen count (66 lines, the drying racks) -- no fixed delta."""
    r = recipe_scan.parse_text(DRYING, "rack.txt")[0]
    i, o = r["inputs"][0], r["outputs"][0]
    assert (i["amount"], i["variable"], i["types"]) == (None, "1:20", ["Base.Corn"])
    assert (o["amount"], o["variable"], o["types"]) == (None, "1:20", ["Base.CornSeed"])
    assert r["props"] == {"overlayStyle": "Corn"}          # a key no field claims is kept verbatim
    d = recipe_scan.nutrition_delta(r, DATASET)
    assert d["reason"].startswith("variable-amount") and "variable[1:20]" in d["reason"]


def test_mapper_default_is_not_an_output_type_and_repeats_are_kept():
    """`default` is a fallback result, not a mapper row; 56 mappers name one result twice."""
    r = recipe_scan.parse_text(FORGE, "forge.txt")[0]
    assert sorted(r["outputs"][0]["types"]) == ["Base.IronBarHalf", "Base.SteelBarHalf"]
    assert r["itemMapperDefaults"] == {"metalType": "Base.IronBarHalf"}
    assert "default" not in r["itemMappers"]["metalType"]
    # the contract dict is `{result: source}` and so keeps the LAST source of a repeated result
    assert r["itemMappers"]["metalType"]["Base.SteelBarHalf"] == "Base.SteelBarQuarter"
    # ... and the pair list keeps every line, in file order, so nothing is lost
    assert r["itemMapperPairs"]["metalType"] == [
        ["Base.IronBarHalf", "Base.IronChunk"], ["Base.SteelBarHalf", "Base.SteelChunk"],
        ["Base.SteelBarHalf", "Base.SteelBarQuarter"]]
    assert r["inputs"][1]["mappers"] == ["metalType"]
    assert r["skillRequired"] == ["Blacksmith:0"] and r["xpAward"] == ["Blacksmith:10"]


def test_fluid_input_flags_the_row_and_contributes_no_macros():
    """`-fluid 10.0 [Water]` is a fluid, so it is neither an item input nor a macro term."""
    r = recipe_scan.parse_text(MILK, "cooking.txt")[0]
    fluid = r["inputs"][1]
    assert (fluid["kind"], fluid["amount"], fluid["types"]) == ("fluid", 10.0, ["Water"])
    assert r["fluidIO"] is True
    assert r["outputs"] == []                              # the block is there and really is empty
    d = recipe_scan.nutrition_delta(r, DATASET)
    assert d["reason"] == "no-outputs"                     # nothing to weigh the inputs against


def test_absent_outputs_block_is_null_not_an_empty_list():
    """`fluid_ids`'s rule, applied to IO: `[]` is an empty block, `null` is no block at all."""
    text = TOASTER.replace("""        outputs
        {
            item 1 Base.Toast,
        }
""", "")
    r = recipe_scan.parse_text(text, "toaster.txt")[0]
    assert r["outputs"] is None and r["inputs"] != []
    assert recipe_scan.nutrition_delta(r, FOOD)["reason"] == "no-outputs"


def test_nutrition_basis_gates_the_delta():
    """R3: only a `per_item` row contributes; a drink and a nutrition-less row block instead."""
    drink = MILL.replace("Base.CornSeed", "Base.Milk")
    d = recipe_scan.nutrition_delta(recipe_scan.parse_text(drink, "m.txt")[0], DATASET)
    assert d["reason"].startswith("fluid-sourced") and "Base.Milk" in d["reason"]
    powder = MILL.replace("Base.CornSeed", "Base.AnimalMilkPowder")
    d = recipe_scan.nutrition_delta(recipe_scan.parse_text(powder, "m.txt")[0], DATASET)
    assert d["reason"].startswith("no-nutrition") and "Base.AnimalMilkPowder" in d["reason"]
    missing = MILL.replace("Base.CornSeed", "Base.Hammer")
    d = recipe_scan.nutrition_delta(recipe_scan.parse_text(missing, "m.txt")[0], DATASET)
    assert d["reason"].startswith("not-in-dataset") and "Base.Hammer" in d["reason"]


def test_absent_macro_sums_as_zero_and_is_named():
    """`Base.Cornflour2` writes no `Calories` line, so 20 CornSeed become -496 kcal of flour.

    The dataset reports that absence as null; the arithmetic has to use a number, so the sum
    takes 0 and the delta names every row/field it did that for.
    """
    r = recipe_scan.parse_text(MILL, "mill.txt")[0]
    d = recipe_scan.nutrition_delta(r, DATASET)
    assert d["calories"] == -496.0                         # 0 - 20 x 24.8
    assert round(d["carbohydrates"], 6) == -152.0 and round(d["lipids"], 6) == -11.2
    assert round(d["proteins"], 6) == -26.4
    assert d["hungerChange"] == 20.0                       # -60 - 20 x -4
    assert d["thirstChange"] == 0.0                        # neither row writes ThirstChange
    assert "Base.Cornflour2:calories" in d["absentMacros"]
    assert "Base.CornSeed:thirstChange" in d["absentMacros"]
    assert d["absentMacros"] == sorted(d["absentMacros"])


def test_food_fields_maps_the_plan_names_onto_the_shipped_dataset():
    """R2: the contract's script-case names are the dataset's lowercase typed fields."""
    assert recipe_scan.FOOD_FIELDS["Calories"] == "calories"
    assert recipe_scan.FOOD_FIELDS["HungerChange"] == "hunger_change"
    assert recipe_scan.FOOD_FIELDS["EvolvedRecipe"] == "evolved_recipe"
    assert recipe_scan.FOOD_FIELDS["ReplaceOnCooked"] == "replace_on_cooked"
    # both shapes read the same value: the dataset's field wins, a raw script key still works
    row = DATASET["Base.CornSeed"]
    assert recipe_scan.food_value(row, "Calories") == 24.8
    assert recipe_scan.food_value(FOOD["Base.Toast"], "HungerChange") == -8.0
    assert recipe_scan.food_value(row, "Spice") is None    # a field this trimmed row does not carry


def test_overlay_mapper_block_and_its_inline_token():
    """3 input lines name `overlayMapper` bare, and 3 recipes carry the block it refers to."""
    text = """module Base
{
    craftRecipe DryLargeLeather
    {
        time = 604800,
        Tags = DryLeatherLarge,
        category = Farming,
        inputs
        {
            item 1 tags[base:leathercrudewetlarge] mappers[DryLeatherLarge] overlayMapper,
        }
        outputs
        {
            item 1 mapper:DryLeatherLarge,
        }
        itemMapper DryLeatherLarge
        {
            Base.Leather_Crude_Large_Tan_Wet = Base.Leather_Crude_Large_Wet,
        }
        overlayMapper
        {
            Base.Leather_Crude_Large_Tan_Wet = LargeLeather,
            default = LargeLeather,
        }
    }
}"""   # entities/animals/craftRecipes/recipes_leather_prep.txt:54-84, tag list and fur rows trimmed
    r = recipe_scan.parse_text(text, "leather.txt")[0]
    assert r["inputs"][0]["overlayMapper"] is True and r["inputs"][0]["extras"] == []
    assert r["overlayMapper"] == {"default": "LargeLeather",
                                  "pairs": [["Base.Leather_Crude_Large_Tan_Wet", "LargeLeather"]]}
    assert r["outputs"][0]["types"] == ["Base.Leather_Crude_Large_Tan_Wet"]


def test_recipe_record_carries_every_field_and_its_source_anchor():
    r = recipe_scan.parse_text(TOASTER, "entities/appliances/workstations/entity_toaster_craftRecipe.txt")[0]
    assert set(r) == set(recipe_scan.RECORD_FIELDS)
    assert (r["module"], r["sourceLine"]) == ("Base", 3)
    assert r["sourceFile"] == "entities/appliances/workstations/entity_toaster_craftRecipe.txt"
    assert r["tags"] == ["Toaster"] and r["timedAction"] == "Making"
    assert r["needToBeLearn"] is None and r["skillRequired"] is None   # absent: null, never false/0
    assert r["itemMappers"] == {} and r["overlayMapper"] is None
    assert r["props"] == {}


# --------------------------------------------------------------------------------------------
# The two writers
# --------------------------------------------------------------------------------------------

def _rows(recipes):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "recipes.csv")
        recipe_scan.write_csv(path, recipes)
        with open(path, encoding="utf-8", newline="") as handle:
            raw = handle.read()
        assert "\r" not in raw                             # lineterminator="\n" with newline=""
        return list(csv.reader(raw.splitlines()))


def test_csv_is_one_row_per_recipe_in_the_declared_column_order():
    recipes = recipe_scan.build(recipe_scan.parse_text(TOASTER, "toaster.txt")
                                + recipe_scan.parse_text(MILL, "mill.txt"), DATASET | FOOD)
    rows = _rows(recipes)
    assert rows[0] == recipe_scan.CSV_HEADER and len(rows) == 3
    assert all(len(row) == len(recipe_scan.CSV_HEADER) for row in rows)
    header = recipe_scan.CSV_HEADER
    toast = rows[1 + [r["name"] for r in recipes].index("MakeToast")]
    assert toast[header.index("name")] == "MakeToast"
    assert toast[header.index("inputTypes")] == "Base.BreadSlices"
    assert toast[header.index("deltaCalories")] == "0.0"
    assert toast[header.index("deltaHungerChange")] == "2.0"
    assert toast[header.index("deltaReason")] == ""        # a resolved delta names no blocker
    assert toast[header.index("fluidIO")] == "false"
    mill = rows[1 + [r["name"] for r in recipes].index("MillCornflour")]
    assert mill[header.index("deltaCalories")] == "-496.0"
    assert mill[header.index("outputTypes")] == "Base.Cornflour2"


def test_a_blocked_delta_writes_its_reason_and_no_numbers():
    recipes = recipe_scan.build(recipe_scan.parse_text(DRYING, "rack.txt"), DATASET)
    row = _rows(recipes)[1]
    header = recipe_scan.CSV_HEADER
    assert row[header.index("deltaCalories")] == ""        # absent, never 0
    assert row[header.index("deltaReason")].startswith("variable-amount")
    assert recipes[0]["delta"] is None and recipes[0]["deltaReason"]


def test_json_is_sorted_and_byte_stable():
    recipes = recipe_scan.build(recipe_scan.parse_text(MILL, "mill.txt")
                                + recipe_scan.parse_text(TOASTER, "toaster.txt"), DATASET | FOOD)
    assert [r["name"] for r in recipes] == ["MakeToast", "MillCornflour"]   # sorted by name
    meta = {"build": recipe_scan.BUILD, "counts": {"craftRecipes": len(recipes)}}
    with tempfile.TemporaryDirectory() as tmp:
        first = os.path.join(tmp, "a.json")
        second = os.path.join(tmp, "b.json")
        recipe_scan.write_json(first, meta, recipes)
        recipe_scan.write_json(second, meta, recipes)
        raw = open(first, encoding="utf-8", newline="").read()
        assert raw == open(second, encoding="utf-8", newline="").read()
        assert "\r" not in raw and raw.endswith("\n")
        payload = json.loads(raw)
    assert payload["meta"]["build"] == "42.20.4 (b0bbce05d5)"
    assert [r["name"] for r in payload["recipes"]] == ["MakeToast", "MillCornflour"]


# --------------------------------------------------------------------------------------------
# Evolved recipes: the key grammar, the two join arms, and the summation
# --------------------------------------------------------------------------------------------

EVOLVED = """module Base
{
    evolvedrecipe Salad
    {
        BaseItem = Base.Bowl,
        MaxItems = 6,
        ResultItem = Base.Salad,
        Name = Make Salad,
        Template = Salad,
    }

    evolvedrecipe SaladClay
    {
        BaseItem = Base.ClayBowl,
        MaxItems = 6,
        ResultItem = Base.SaladClay,
        Name = Make Salad,
        Template = Salad,
    }

    evolvedrecipe RicePan
    {
        BaseItem = Base.WaterSaucepanRice,
        MaxItems = 4,
        ResultItem = Base.RicePan,
        Cookable = true,
        AddIngredientIfCooked = true,
        Name = Prepare Rice,
        CanAddSpicesEmpty = true,
        Template = Rice,
    }

    evolvedrecipe ConeIcecream
    {
        BaseItem = Base.ConeIcecream,
        MaxItems = 3,
        ResultItem = Base.ConeIcecreamToppings,
        Name = Prepare Ice Cream Cone,
        CanAddSpicesEmpty = true,
        Template = ConeIcecream,
    }

    evolvedrecipe Oatmeal
    {
        BaseItem = Base.Oatmeal,
        MaxItems = 3,
        ResultItem = Base.Oatmeal,
        AddIngredientIfCooked = true,
        Name = Oatmeal,
        CanAddSpicesEmpty = true,
        Template = Oatmeal,
        Cookable = true,
    }
}"""   # evolvedrecipes.txt:220-235 (Salad, SaladClay), :268-278 (RicePan), :603-611 (ConeIcecream),
       # :635-645 (Oatmeal) -- five of the 63 blocks, each byte-exact, nothing else elided

# The two ingredients of the measured Salad run, in the plan's own script-key shape.
LETTUCE = {"HungerChange": -15.0, "Calories": 54.0, "Carbohydrates": 10.33,
           "Lipids": 0.54, "Proteins": 4.9}    # food.txt:14467, EvolvedRecipe "... Salad:5 ..."
TOMATO = {"HungerChange": -12.0, "Calories": 14.0, "Carbohydrates": 3.5,
          "Lipids": 0.2, "Proteins": 1.3}      # food.txt:91,    EvolvedRecipe "... Salad:6 ..."

# … and as `data/food-items.json` ships them. Every value is verbatim from the shipped dataset;
# only the `evolved_recipe` lists are trimmed, to the keys that reach the five fixture recipes.
EVO_FOOD = {
    "Base.Lettuce": {"nutrition_basis": "per_item", "calories": 54.0, "carbohydrates": 10.33,
                     "lipids": 0.54, "proteins": 4.9, "hunger_change": -15.0,
                     "thirst_change": -7.0, "spice": None, "evolved_recipe_name": None,
                     "evolved_recipe": ["Salad:5"],            # of 6 keys
                     "source_file": "items/food.txt", "source_line": 14467},
    # a spice, and the one vanilla key that only the case-insensitive template arm matches
    "Base.Cinnamon": {"nutrition_basis": "per_item", "calories": 1.0, "carbohydrates": 0.0,
                      "lipids": 0.0, "proteins": 0.0, "hunger_change": -5.0,
                      "thirst_change": None, "spice": True, "evolved_recipe_name": None,
                      "evolved_recipe": ["ConeIceCream:1"],    # of 10 keys
                      "source_file": "items/food.txt", "source_line": 13665},
    # two keys that reach one recipe: `RicePan` is aliased to `Rice` at parse time, and `Rice`
    # is written out a line later -- one of the 21 vanilla joins a recipe sees twice
    "Base.Seasoning_Basil": {"nutrition_basis": "per_item", "calories": 0.4,
                             "carbohydrates": 0.0, "lipids": 0.0, "proteins": 0.0,
                             "hunger_change": -20.0, "thirst_change": None, "spice": True,
                             "evolved_recipe_name": "Basil",
                             "evolved_recipe": ["RicePan:1", "Rice:1"],   # of 12 keys, in order
                             "source_file": "items/food.txt", "source_line": 11647},
    # `use` 5 against a hunger of 3: the game clamps `hunger` here and this formula does not
    "Base.Cherry": {"nutrition_basis": "per_item", "calories": 5.0, "carbohydrates": 1.31,
                    "lipids": 0.0, "proteins": 0.09, "hunger_change": -3.0,
                    "thirst_change": -1.0, "spice": None, "evolved_recipe_name": None,
                    "evolved_recipe": ["Oatmeal:5"],           # of 7 keys
                    "source_file": "items/food.txt", "source_line": 8700},
}


def _evolved(food=None):
    """The fixture recipes, keyed by name, with `food`'s carriers joined onto them."""
    recipes = recipe_scan.parse_evolved_text(EVOLVED, "evolvedrecipes.txt")
    by_name = {r["name"]: r for r in recipes}
    unmatched, census = recipe_scan.evolved_ingredients(by_name, food or EVO_FOOD)
    return by_name, unmatched, census


# --- the plan's Task 3 Step 1, verbatim ------------------------------------------------------

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


# --- the grammar and the two arms ------------------------------------------------------------

def test_parse_evolved_key_reads_the_dataset_list_shape_too():
    """`data/food-items.json` ships the key already split on `;` (README row 39)."""
    assert recipe_scan.parse_evolved_key(["Sandwich:5|Cooked", "Salad:10"]) == [
        ("Sandwich", 5, True), ("Salad", 10, False)]
    assert recipe_scan.parse_evolved_key("Stir fry Griddle Pan:12") == [
        ("Stir fry Griddle Pan", 12, False)]           # a key with spaces, and a name-arm-only one
    assert recipe_scan.parse_evolved_key(None) == [] and recipe_scan.parse_evolved_key("") == []


def test_alias_rewrites_only_the_five_parse_time_names():
    """`Item.DoParam` rewrites the key before it is ever looked up; everything else is verbatim."""
    assert recipe_scan.alias("RicePot") == "Rice" and recipe_scan.alias("PastaPan") == "Pasta"
    assert recipe_scan.alias("PastaPot") == "Pasta"
    assert recipe_scan.alias("Salad") == "Salad"       # not an alias: unchanged
    assert recipe_scan.alias("ricepan") == "ricepan"   # the alias table is exact, not folded


def test_template_arm_is_case_insensitive_and_the_name_arm_is_not():
    """`Base.Cinnamon`'s `ConeIceCream:1` is the one vanilla key that discriminates the arms."""
    recipes = {r["name"]: r for r in recipe_scan.parse_evolved_text(EVOLVED, "e.txt")}
    assert recipe_scan.resolve_recipes("ConeIceCream", recipes) == ["ConeIcecream"]
    assert recipe_scan.resolve_arms("ConeIceCream", recipes) == {"ConeIcecream": "template"}
    # the exact-name key reaches the same recipe through both arms
    assert recipe_scan.resolve_arms("ConeIcecream", recipes) == {"ConeIcecream": "both"}
    # one `Salad:` key reaches both bowls; only the recipe called `Salad` matches by name
    assert recipe_scan.resolve_arms("Salad", recipes) == {"Salad": "both", "SaladClay": "template"}
    assert recipe_scan.resolve_recipes("Rice", recipes) == ["RicePan"]      # template only
    assert recipe_scan.resolve_recipes("RicePan", recipes) == ["RicePan"]   # name only, unaliased
    assert recipe_scan.resolve_recipes("Nope", recipes) == []


def test_ingredients_join_through_the_alias_and_carry_their_key():
    by_name, unmatched, census = _evolved()
    assert unmatched == []
    salad = {i["item"]: i for i in by_name["Salad"]["ingredients"]}
    assert sorted(salad) == ["Base.Lettuce"]
    assert salad["Base.Lettuce"]["key"] == "Salad:5" and salad["Base.Lettuce"]["use"] == 5
    assert salad["Base.Lettuce"]["resolvedVia"] == "both"
    assert salad["Base.Lettuce"]["requiresCooked"] is False
    assert salad["Base.Lettuce"]["evolvedRecipeName"] is None
    # the same key reaches the second bowl through the template arm alone
    assert [i["item"] for i in by_name["SaladClay"]["ingredients"]] == ["Base.Lettuce"]
    assert by_name["SaladClay"]["ingredients"][0]["resolvedVia"] == "template"
    # `RicePan:1` reaches `RicePan` only because DoParam rewrote it to `Rice`, and `Rice:1`
    # reaches it again: one row, the later key, and the collapsed one named beside it
    rice = by_name["RicePan"]["ingredients"][0]
    assert (rice["item"], rice["key"]) == ("Base.Seasoning_Basil", "Rice:1")
    assert rice["duplicateKeys"] == ["RicePan:1"] and rice["resolvedVia"] == "template"
    assert rice["evolvedRecipeName"] == "Basil" and rice["spice"] is True
    assert census["pairs"] == 6 and census["ingredients"] == 5 and census["duplicateJoins"] == 1


def test_an_unmatched_key_is_recorded_and_never_guessed_at():
    food = {"Base.Ghost": dict(EVO_FOOD["Base.Lettuce"], evolved_recipe=["Nope:5", "Salad:5"])}
    by_name, unmatched, census = _evolved(food)
    assert unmatched == [{"item": "Base.Ghost", "key": "Nope:5", "lookupKey": "Nope",
                          "sourceFile": "items/food.txt", "sourceLine": 14467}]
    assert census["unmatchedKeys"] == 1 and census["pairs"] == 2      # the Salad key still joins


def test_a_spice_transfers_no_hunger_and_no_macros():
    """`Spice = true` takes the ingredient down the spice branch: no hunger, no macro transfer."""
    c = recipe_scan.contribution(EVO_FOOD["Base.Cinnamon"], 1, 10)
    assert c["spice"] is True and c["share"] == 0.0
    assert (c["calories"], c["carbohydrates"], c["lipids"], c["proteins"]) == (0.0, 0.0, 0.0, 0.0)
    assert "spice branch" in c["note"]
    assert c["skillBonus"] == recipe_scan.contribution(LETTUCE, 1, 10)["skillBonus"]


def test_an_ingredient_with_no_hunger_has_no_share():
    c = recipe_scan.contribution({"HungerChange": 0.0, "Calories": 100.0}, 5, 0)
    assert c["share"] == 0.0 and c["calories"] == 0.0 and c["reason"] == "no hunger"
    assert recipe_scan.contribution({"Calories": 100.0}, 5, 0)["reason"] == "no hunger"


def test_ruling_r3_nulls_the_macros_of_a_non_per_item_row():
    """A `per_litre` row's numbers are per litre of fluid, so they may not be shared out."""
    drink = dict(EVO_FOOD["Base.Lettuce"], nutrition_basis="per_litre")
    c = recipe_scan.contribution(drink, 5, 0)
    assert c["reason"] == "fluid-sourced"
    assert (c["calories"], c["proteins"], c["thirstChange"]) == (None, None, None)
    assert round(c["share"], 6) == 0.333333               # the hunger arithmetic still holds
    empty = dict(EVO_FOOD["Base.Lettuce"], nutrition_basis=None)
    assert recipe_scan.contribution(empty, 5, 0)["reason"] == "no-nutrition"


def test_the_games_hunger_clamp_is_flagged_not_applied():
    """`Base.Cherry` writes `Salad:5` against a hunger of 3, where `addItem` clamps `hunger`."""
    c = recipe_scan.contribution(EVO_FOOD["Base.Cherry"], 5, 10)
    assert c["hungerClamped"] is True and c["share"] == 1.0     # the game would give 0.7 here
    assert recipe_scan.contribution(LETTUCE, 5, 10)["hungerClamped"] is False


def test_evolved_record_carries_every_field_and_its_source_anchor():
    by_name, _unmatched, _census = _evolved()
    salad = by_name["Salad"]
    assert set(salad) == set(recipe_scan.EVOLVED_RECORD_FIELDS)
    assert (salad["module"], salad["sourceFile"], salad["sourceLine"]) == ("Base", "evolvedrecipes.txt", 3)
    assert (salad["baseItem"], salad["resultItem"], salad["template"]) == ("Base.Bowl", "Base.Salad", "Salad")
    assert salad["maxItems"] == 6 and salad["displayName"] == "Make Salad"
    # absent is null, never false: `Salad` writes none of the three flags, `RicePan` writes two
    assert (salad["cookable"], salad["canAddSpicesEmpty"], salad["addIngredientIfCooked"]) == (None, None, None)
    assert salad["minimumWater"] is None and salad["props"] == {}
    rice = by_name["RicePan"]
    assert (rice["cookable"], rice["canAddSpicesEmpty"], rice["addIngredientIfCooked"]) == (True, True, True)
    ing = salad["ingredients"][0]
    assert set(ing) == set(recipe_scan.EVOLVED_INGREDIENT_FIELDS)
    assert set(ing["at0"]) == set(ing["at10"]) == set(recipe_scan.CONTRIBUTION_FIELDS)
    # `Base.Lettuce` writes all five macros; `Base.Cinnamon` writes no `ThirstChange`, so its
    # 0.0 there is the loader's default and the row says so rather than implying a measured 0
    assert ing["absentMacros"] == []
    cone = by_name["ConeIcecream"]["ingredients"][0]
    assert cone["item"] == "Base.Cinnamon" and cone["absentMacros"] == ["thirstChange"]
    assert cone["at0"]["thirstChange"] == 0.0


def test_evolved_csv_is_one_row_per_recipe_ingredient_pair():
    by_name, _unmatched, _census = _evolved()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "evolved-recipes.csv")
        recipe_scan.write_evolved_csv(path, [by_name[n] for n in sorted(by_name)])
        raw = open(path, encoding="utf-8", newline="").read()
    assert "\r" not in raw
    rows = list(csv.reader(raw.splitlines()))
    header = recipe_scan.EVOLVED_CSV_HEADER
    assert rows[0] == header and len(rows) == 6            # 5 pairs + the header
    assert all(len(row) == len(header) for row in rows)
    lettuce = [r for r in rows[1:] if r[header.index("recipe")] == "Salad"
               and r[header.index("item")] == "Base.Lettuce"][0]
    assert lettuce[header.index("resultItem")] == "Base.Salad"
    assert lettuce[header.index("use")] == "5" and lettuce[header.index("spice")] == "false"
    assert lettuce[header.index("share0")] == "0.333333" and lettuce[header.index("kcal0")] == "18.0"
    assert lettuce[header.index("share10")] == "0.233333" and lettuce[header.index("kcal10")] == "21.0"
    assert [r[header.index("recipe")] for r in rows[1:]] == sorted(
        r[header.index("recipe")] for r in rows[1:])       # sorted by recipe, then by ingredient


# --------------------------------------------------------------------------------------------
# The `ReplaceOn*` links
# --------------------------------------------------------------------------------------------

REPLACE_FOOD = {
    "Base.BreadSlices": {"kind": "food", "nutrition_basis": "per_item", "calories": 177.0,
                         "carbohydrates": 33.0, "lipids": 2.22, "proteins": 5.9,
                         "hunger_change": -10.0, "thirst_change": None,
                         "replace_on_cooked": ["Base.Toast"], "source_file": "items/food.txt",
                         "source_line": 2123},                                # food.txt:2132
    "Base.Toast": {"kind": "food", "nutrition_basis": "per_item", "calories": 177.0,
                   "carbohydrates": 33.0, "lipids": 2.22, "proteins": 5.9,
                   "hunger_change": -8.0, "thirst_change": None,
                   "source_file": "items/food.txt", "source_line": 6400},
    "Base.ConeIcecream": {"kind": "food", "nutrition_basis": "per_item", "calories": 300.0,
                          "carbohydrates": 39.0, "lipids": 15.0, "proteins": 5.0,
                          "hunger_change": -20.0, "thirst_change": None,
                          "replace_on_rotten": "Base.ConeIcecreamMelted",
                          "replace_on_use": "Base.MugRed",   # the slice-05 undefined target
                          "source_file": "items/food.txt", "source_line": 12417},
}


def test_replacement_links_carry_the_trigger_and_the_swap_delta():
    links = recipe_scan.replacements(REPLACE_FOOD)
    assert [(l["from"], l["to"], l["trigger"]) for l in links] == [
        ("Base.BreadSlices", "Base.Toast", "cooked"),
        ("Base.ConeIcecream", "Base.ConeIcecreamMelted", "rotten"),
        ("Base.ConeIcecream", "Base.MugRed", "use")]
    toast = links[0]
    assert set(toast) == set(recipe_scan.REPLACEMENT_FIELDS)
    assert toast["sourceFile"] == "items/food.txt" and toast["sourceLine"] == 2123
    # cooking changes no nutrition; the swap is the whole effect, and it is +2 hunger relief
    assert toast["delta"] == {"calories": 0.0, "carbohydrates": 0.0, "lipids": 0.0,
                              "proteins": 0.0, "hungerChange": 2.0, "thirstChange": 0.0,
                              "absentMacros": ["Base.BreadSlices:thirstChange",
                                               "Base.Toast:thirstChange"]}
    assert toast["deltaReason"] is None
    # a target no food row carries is kept as an unresolved link, never guessed at
    assert links[2]["delta"] is None and links[2]["deltaReason"] == "not-in-dataset"
    assert links[1]["delta"] is None and links[1]["deltaReason"] == "not-in-dataset"


def test_recipes_json_carries_replacements_after_the_recipes():
    recipes = recipe_scan.build(recipe_scan.parse_text(TOASTER, "toaster.txt"), DATASET | FOOD)
    links = recipe_scan.replacements(REPLACE_FOOD)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "recipes.json")
        recipe_scan.write_json(path, {"build": recipe_scan.BUILD}, recipes, links)
        raw = open(path, encoding="utf-8", newline="").read()
    payload = json.loads(raw)
    assert list(payload) == ["meta", "recipes", "replacements"]   # appended, so the diff is a tail
    assert len(payload["replacements"]) == 3
    # a writer called without the array writes exactly what it wrote before this task
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "recipes.json")
        recipe_scan.write_json(path, {"build": recipe_scan.BUILD}, recipes)
        assert list(json.loads(open(path, encoding="utf-8").read())) == ["meta", "recipes"]


# --------------------------------------------------------------------------------------------
# The install: the counts, and the four rows the plan spot-checks by hand
# --------------------------------------------------------------------------------------------

_REAL = []


def _real_dataset():
    """build_dataset() once, shared by the install-gated tests."""
    if not _REAL:
        _REAL.append(recipe_scan.build_dataset())
    return _REAL[0]


@unittest.skipUnless(HAVE_INSTALL and HAVE_FOOD, "game install or food dataset not present")
def test_real_install_counts():
    """The plan's Task 2 Step 3 figures, with two re-derived (see the report's deviations)."""
    meta, recipes = _real_dataset()
    counts = meta["counts"]
    assert counts["craftRecipes"] == 969 and len(recipes) == 969
    assert counts["files"] == 74 and counts["scriptFiles"] == 1004
    assert counts["legacyRecipeBlocks"] == 0
    assert counts["itemMappers"] == 225 and counts["overlayMappers"] == 3
    # 202 `component CraftRecipe` blocks are an entity's own build recipe, not a craftRecipe --
    # they are why a raw grep of the scripts counts more `mode:` and `flags[…]` than this dataset
    assert counts["componentCraftRecipes"] == 202
    # 37 recipes yield no item at all -- they mutate an input through `OnCreate` (opening a can,
    # sharpening a blade, dyeing clothes). The plan expected "10 blocks with no outputs": 11 ship
    # no `outputs` block and 26 more ship an empty one (`recipes_fixing.txt:18`).
    assert counts["recipesWithoutOutputs"] == 11 and counts["recipesWithEmptyOutputs"] == 26
    assert counts["outputItemTypes"] == 1693
    assert counts["outputItemTypesInFoodDataset"] == 262   # `food` + `drainable` rows
    assert counts["outputItemTypesInDataset"] == 295       # … plus the 33 fluid containers
    # The plan predicted 116 "recipes touching a food item". No definition reproduces that:
    # every item line on either side naming a food/drainable row gives 375, outputs only 182,
    # single-type lines only 305. Reported as measured, with the definition above them.
    assert counts["recipesTouchingFood"] == 375
    assert counts["recipesWithFoodOutput"] == 182
    assert counts["recipesWithDelta"] == 31                # the plan's figure, exactly
    # The plan predicted 23 non-zero calorie deltas: 20 really are non-zero and 3 more (the
    # cigarette crafts) are zero only because no row on either side writes a `Calories` line.
    assert counts["recipesWithNonZeroCalorieDelta"] == 20
    assert counts["recipesWithCaloriesAbsentOnEverySide"] == 3
    assert [r["name"] for r in recipes] == sorted(r["name"] for r in recipes)
    assert len({r["name"] for r in recipes}) == 969        # every craftRecipe name is unique
    assert meta["build"] == "42.20.4 (b0bbce05d5)"
    assert meta["sources"]["food_items"]["build"] == "42.20.4"
    # one output mapper resolves to no type at all: `SmeltMapper` writes only a `default`, so
    # what the craft really yields is that default (`Base.CeramicCrucible_Iron`, on the record
    # as `itemMapperDefaults`), which the plan's "every key except `default`" rule cannot name
    assert meta["outputMapperIssues"] == [
        {"recipe": "ExtractIronFromIronOre", "mapper": "SmeltMapper", "why": "no-rows"}]
    smelt = {r["name"]: r for r in recipes}["ExtractIronFromIronOre"]
    assert smelt["outputs"][0]["types"] == []
    assert smelt["itemMapperDefaults"] == {"SmeltMapper": "Base.CeramicCrucible_Iron"}


@unittest.skipUnless(HAVE_INSTALL and HAVE_FOOD, "game install or food dataset not present")
def test_real_install_spot_rows():
    """The four rows the plan prints by hand, straight off the install."""
    _meta, recipes = _real_dataset()
    by_name = {r["name"]: r for r in recipes}

    toast = by_name["MakeToast"]
    assert toast["sourceFile"] == "entities/appliances/workstations/entity_toaster_craftRecipe.txt"
    assert toast["sourceLine"] == 3 and toast["time"] == 20
    assert toast["delta"] == {"calories": 0.0, "carbohydrates": 0.0, "lipids": 0.0,
                              "proteins": 0.0, "hungerChange": 2.0, "thirstChange": 0.0,
                              "absentMacros": ["Base.BreadSlices:thirstChange",
                                               "Base.Toast:thirstChange"]}

    mill = by_name["MillCornflour"]
    assert mill["delta"]["calories"] == -496.0             # 20 x Base.CornSeed -> Base.Cornflour2
    assert mill["deltaReason"] is None

    pizza = by_name["MakePizza"]
    assert pizza["delta"] is None
    assert "tags[base:flour]" in pizza["deltaReason"] and "[*]" in pizza["deltaReason"]
    assert pizza["fluidIO"] is True and len(pizza["inputs"]) == 10

    frozen = by_name["OpenBagOfFrozenFood"]
    assert sorted(frozen["outputs"][0]["types"]) == [
        "Base.ChickenNuggets", "Base.FishFingers", "Base.FrenchFries", "Base.TatoDots"]
    assert frozen["delta"] is None and frozen["deltaReason"]


@unittest.skipUnless(HAVE_INSTALL and HAVE_FOOD, "game install or food dataset not present")
def test_real_install_writers_are_deterministic():
    """A second run must be byte-identical: the files are committed data."""
    meta, recipes = _real_dataset()
    with tempfile.TemporaryDirectory() as tmp:
        paths = [os.path.join(tmp, name) for name in ("a.json", "b.json", "a.csv", "b.csv")]
        recipe_scan.write_json(paths[0], meta, recipes)
        recipe_scan.write_json(paths[1], meta, recipes)
        recipe_scan.write_csv(paths[2], recipes)
        recipe_scan.write_csv(paths[3], recipes)
        assert open(paths[0], "rb").read() == open(paths[1], "rb").read()
        assert open(paths[2], "rb").read() == open(paths[3], "rb").read()
        rows = list(csv.reader(open(paths[2], encoding="utf-8", newline="").read().splitlines()))
    assert len(rows) == 970 and rows[0] == recipe_scan.CSV_HEADER


# --------------------------------------------------------------------------------------------
# The install: the evolved-recipe join and the ReplaceOn* links
# --------------------------------------------------------------------------------------------

_REAL_EVOLVED = []


def _real_evolved():
    """build_evolved_dataset() once, shared by the install-gated tests."""
    if not _REAL_EVOLVED:
        _REAL_EVOLVED.append(recipe_scan.build_evolved_dataset())
    return _REAL_EVOLVED[0]


@unittest.skipUnless(HAVE_INSTALL and HAVE_FOOD, "game install or food dataset not present")
def test_real_install_evolved_counts():
    """The plan's Task 3 figures, with the one re-derived (see the report's deviation E1)."""
    meta, recipes, unmatched = _real_evolved()
    counts = meta["counts"]
    assert counts["evolvedRecipes"] == 63 and len(recipes) == 63
    # 62 in evolvedrecipes.txt, `AddBaitToChum` in the fishing file
    assert meta["sources"]["files"] == ["evolvedrecipes.txt",
                                        "recipes/recipes_fishing_evolvedrecipe.txt"]
    assert counts["carriers"] == 374 and counts["carriersFood"] == 372
    assert counts["carriersDrainable"] == 2
    # every key resolves: 6902 (key part x recipe) joins, 21 of which repeat a (recipe, item)
    assert counts["pairs"] == 6902 and unmatched == [] and counts["unmatchedKeys"] == 0
    assert counts["ingredients"] == 6881 and counts["duplicateJoins"] == 21
    assert counts["cookedSuffixes"] == 213 and counts["aliasedKeyParts"] == 5
    # R3 never fires: all 374 carriers are `per_item` rows (the amendment's assertion)
    assert counts["ingredientsRefusedByBasis"] == 0
    by_name = {r["name"]: r for r in recipes}
    # The plan predicted 187 ingredients for each Salad bowl. That is the `items/food.txt`-only
    # figure: `Base.Vinegar2` and `Base.Vinegar_Jug` (`items/drainable.txt`) also write `Salad:1`,
    # and the same plan's 6902 counts them, so the two figures cannot both be right.
    assert len(by_name["Salad"]["ingredients"]) == 189
    assert len(by_name["SaladClay"]["ingredients"]) == 189
    assert counts["pairsFromFoodTxt"] == 6858
    drainables = [i["item"] for i in by_name["Salad"]["ingredients"]
                  if i["sourceFile"] == "items/drainable.txt"]
    assert drainables == ["Base.Vinegar2", "Base.Vinegar_Jug"]
    # `item Cinnamon` writes `ConeIceCream:1`; the recipe and its template are `ConeIcecream`,
    # so it joins through the case-insensitive template arm alone
    cinnamon = [i for i in by_name["ConeIcecream"]["ingredients"] if i["item"] == "Base.Cinnamon"]
    assert len(cinnamon) == 1 and cinnamon[0]["key"] == "ConeIceCream:1"
    assert cinnamon[0]["resolvedVia"] == "template" and cinnamon[0]["spice"] is True
    assert [r["name"] for r in recipes] == sorted(r["name"] for r in recipes)
    assert meta["build"] == "42.20.4 (b0bbce05d5)"
    assert meta["sources"]["food_items"]["build"] == "42.20.4"


@unittest.skipUnless(HAVE_INSTALL and HAVE_FOOD, "game install or food dataset not present")
def test_real_install_salad_reproduces_the_measured_dish():
    """Lettuce + Tomato in `Salad`, against the measured run `exp02-20260910-030433`."""
    _meta, recipes, _unmatched = _real_evolved()
    salad = {r["name"]: r for r in recipes}["Salad"]
    rows = {i["item"]: i for i in salad["ingredients"]}
    lettuce, tomato = rows["Base.Lettuce"], rows["Base.Tomato"]
    assert (lettuce["use"], tomato["use"]) == (5, 6)
    assert lettuce["at0"]["share"] == 0.333333 and tomato["at0"]["share"] == 0.5
    assert round(lettuce["at0"]["calories"] + tomato["at0"]["calories"], 4) == 25.0
    assert round(lettuce["at10"]["calories"] + tomato["at10"]["calories"], 4) == 29.1667
    assert round(lettuce["at0"]["carbohydrates"] + tomato["at0"]["carbohydrates"], 6) == 5.193333
    assert round(lettuce["at0"]["lipids"] + tomato["at0"]["lipids"], 6) == 0.28
    assert round(lettuce["at0"]["proteins"] + tomato["at0"]["proteins"], 6) == 2.283333


@unittest.skipUnless(HAVE_INSTALL and HAVE_FOOD, "game install or food dataset not present")
def test_real_install_replacement_links():
    """3 cooked + 8 rotten, plus the `use` / `deplete` swaps the same dataset carries."""
    food, _meta = recipe_scan.load_food()
    links = recipe_scan.replacements(food)
    by_trigger = {}
    for link in links:
        by_trigger.setdefault(link["trigger"], []).append(link)
    assert [(l["from"], l["to"], l["sourceLine"]) for l in by_trigger["cooked"]] == [
        ("Base.BaguetteDough", "Base.Baguette", 2807),      # ReplaceOnCooked at food.txt:2816
        ("Base.BreadSlices", "Base.Toast", 2123),           # … :2132
        ("Base.PancakesCraft", "Base.Pancakes", 10906)]     # … :10914
    assert len(by_trigger["rotten"]) == 8
    assert [l["from"] for l in by_trigger["rotten"]] == [
        "Base.ConeIcecream", "Base.ConeIcecreamToppings", "Base.Creamocle", "Base.FudgeePop",
        "Base.Icecream", "Base.IcecreamSandwich", "Base.Popsicle", "Base.SugarBeetSyrupPot"]
    assert len(by_trigger["use"]) == 110 and len(by_trigger["deplete"]) == 42
    assert all(link["sourceFile"] in ("items/food.txt", "items/drainable.txt") for link in links)
    # the slice-05 finding: `Base.MugRed` is written by no item block in the install
    mugred = [l for l in links if l["to"] == "Base.MugRed"]
    assert len(mugred) == 1 and mugred[0]["from"] == "Base.HotDrinkRed"
    assert mugred[0]["delta"] is None and mugred[0]["deltaReason"] == "not-in-dataset"
    toast = [l for l in by_trigger["cooked"] if l["to"] == "Base.Toast"][0]
    assert toast["delta"]["calories"] == 0.0 and toast["delta"]["hungerChange"] == 2.0


@unittest.skipUnless(HAVE_INSTALL and HAVE_FOOD, "game install or food dataset not present")
def test_real_install_evolved_writers_are_deterministic():
    """A second run must be byte-identical: the files are committed data."""
    meta, recipes, unmatched = _real_evolved()
    with tempfile.TemporaryDirectory() as tmp:
        paths = [os.path.join(tmp, name) for name in ("a.json", "b.json", "a.csv", "b.csv")]
        recipe_scan.write_evolved_json(paths[0], meta, recipes, unmatched)
        recipe_scan.write_evolved_json(paths[1], meta, recipes, unmatched)
        recipe_scan.write_evolved_csv(paths[2], recipes)
        recipe_scan.write_evolved_csv(paths[3], recipes)
        assert open(paths[0], "rb").read() == open(paths[1], "rb").read()
        assert open(paths[2], "rb").read() == open(paths[3], "rb").read()
        raw = open(paths[2], encoding="utf-8", newline="").read()
        rows = list(csv.reader(raw.splitlines()))
    assert "\r" not in raw
    assert len(rows) == 6882 and rows[0] == recipe_scan.EVOLVED_CSV_HEADER
