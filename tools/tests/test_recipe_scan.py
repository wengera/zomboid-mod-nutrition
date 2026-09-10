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
