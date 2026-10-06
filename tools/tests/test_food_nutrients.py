"""Tests for the FDC join core (tools/food_nutrients.py, Plan 6 Task 2).

The CSV fixtures are quoted verbatim from the SR Legacy zip
(`tools/.fdc/FoodData_Central_sr_legacy_food_csv_2018-04.zip`, sha256 b8081729...6e5c2081643e6fd0;
its members sit under `FoodData_Central_sr_legacy_food_csv_2018-04/`) and from
`tools/.fdc/NutrientRetention.csv` (sha256 b863e891...ff9a84b1e5); every kept line is byte-exact
and its `# <file>:<line>` comment is the re-check anchor (line 1 is the header). A header line is
quoted from line 1 of its file. The tests that read the real files skip when `HAVE_FDC` is false,
as test_food_scan.py skips without the install.
"""
import os, re, shutil, subprocess, sys, tempfile, unittest, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import food_nutrients as fn

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LUA_SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
HAVE_FDC = fn.HAVE_FDC
HAVE_RETENTION = os.path.exists(fn.RETENTION_CSV)

NUTRIENT_CSV = "\n".join([
    '"id","name","unit_name","nutrient_nbr","rank"',               # nutrient.csv:1
    '"1003","Protein","G","203","600.0"',                           # nutrient.csv:6
    '"1004","Total lipid (fat)","G","204","800.0"',                 # nutrient.csv:7
    '"1005","Carbohydrate, by difference","G","205","1110.0"',      # nutrient.csv:8
    '"1008","Energy","KCAL","208","300.0"',                         # nutrient.csv:11
    '"1018","Alcohol, ethyl","G","221","18200.0"',                  # nutrient.csv:21
    '"1051","Water","G","255","100.0"',                             # nutrient.csv:54
    '"1079","Fiber, total dietary","G","291","1200.0"',             # nutrient.csv:82
    '"1100","Iodine, I","UG","314","6150.0"',                       # nutrient.csv:103
    '"1104","Vitamin A, IU","IU","318","7500.0"',                   # nutrient.csv:107
    '"1190","Folate, DFE","UG","435","7200.0"',                     # nutrient.csv:193
    '"1269","PUFA 18:2","G","618","13100.0"',                       # nutrient.csv:272
]) + "\n"

FOOD_NUTRIENT_CSV = "\n".join([
    '"id","fdc_id","nutrient_id","amount","data_points","derivation_id","min","max","median",'
    '"footnote","min_year_acquired"',                                          # food_nutrient.csv:1
    '"1631302","171688","1018","0","0","","","","","",""',                      # food_nutrient.csv:347630
    '"1631309","171688","1005","13.81","0","49","","","","",""',                # food_nutrient.csv:347637
    '"1631357","171688","1079","2.4","29","1","1.4","3.5","","",""',            # food_nutrient.csv:347685
]) + "\n"

FOOD_PORTION_CSV = "\n".join([
    '"id","fdc_id","seq_num","amount","measure_unit_id","portion_description","modifier",'
    '"gram_weight","data_points","footnote","min_year_acquired"',                        # food_portion.csv:1
    '"89191","171688","2","1","9999","","cup slices","109","60","",""',                   # food_portion.csv:7644
    '"89193","171688","4","1","9999","","medium (3"" dia)","182","113","",""',            # food_portion.csv:7646
]) + "\n"

FOOD_CSV = "\n".join([
    '"fdc_id","data_type","description","food_category_id","publication_date"',  # food.csv:1
    '"171688","sr_legacy_food","Apples, raw, with skin (Includes foods for USDA\'s Food '
    'Distribution Program)","9","2019-04-01"',                                     # food.csv:4178
]) + "\n"

FOOD_CATEGORY_CSV = "\n".join([
    '"id","code","description"',                     # food_category.csv:1
    '"9","0900","Fruits and Fruit Juices"',          # food_category.csv:10
]) + "\n"

MEASURE_UNIT_CSV = "\n".join([
    '"id","name"',                # measure_unit.csv:1
    '"9999","undetermined"',      # measure_unit.csv:123
]) + "\n"

RETENTION_CSV = "\n".join([
    "Retn_Code,FdGrp_CD,RetnDesc,Nutr_No,NutrDesc,Retn_Factor,Date",                # NutrientRetention.csv:1
    '1,1,"CHEESE,BAKED",301,"Calcium, Ca",100,Sep-75',                               # NutrientRetention.csv:2
    '5005,14,"ALC BEV,STIRRED,BKD/SIMMRD 30 MIN",301,"Calcium, Ca",Sep-75,',         # NutrientRetention.csv:4499
    '5005,14,"ALC BEV,STIRRED,BKD/SIMMRD 30 MIN",221,"Alcohol, ethyl",35,Sep-75',    # NutrientRetention.csv:4519
]) + "\n"

APPLE = 171688


def _write(directory, name, text):
    with open(os.path.join(directory, name), "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


class FixtureDir(unittest.TestCase):
    """A temp dir of the verbatim fixture CSVs: the loaders read a directory exactly as a zip."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        for name, text in (("nutrient.csv", NUTRIENT_CSV), ("food_nutrient.csv", FOOD_NUTRIENT_CSV),
                           ("food_portion.csv", FOOD_PORTION_CSV), ("food.csv", FOOD_CSV),
                           ("food_category.csv", FOOD_CATEGORY_CSV),
                           ("measure_unit.csv", MEASURE_UNIT_CSV),
                           ("NutrientRetention.csv", RETENTION_CSV)):
            _write(self.dir, name, text)


# ---- KEYS / UNITS / FDC table ----

class KeyTableTest(unittest.TestCase):

    def _lua(self, name):
        with open(os.path.join(LUA_SHARED, name), encoding="utf-8") as handle:
            return handle.read()

    def test_keys_match_the_kernel(self):
        text = self._lua("NR_Kernel_Vector.lua")
        body = re.search(r"K\.vector\.KEYS\s*=\s*\{(.*?)\}", text, re.S).group(1)
        self.assertEqual(tuple(re.findall(r'"(\w+)"', body)), fn.KEYS)
        self.assertEqual(len(fn.KEYS), 31)

    def test_units_match_the_contract(self):
        text = self._lua("NR_Data_Nutrients.lua")
        body = re.search(r"NR\.data\.UNITS\s*=\s*\{(.*?)\}", text, re.S).group(1)
        self.assertEqual(dict(re.findall(r'(\w+)\s*=\s*"(\w+)"', body)), fn.UNIT_OF)

    def test_table_covers_every_key_but_phytate(self):
        self.assertEqual(set(fn.FDC_NUTRIENT_NBR), set(fn.KEYS) - {"phytate"})
        self.assertIn("phytate", fn.NO_FDC_KEYS)
        for key, (nbrs, how) in fn.FDC_NUTRIENT_NBR.items():
            self.assertIn(how, ("first", "sum"), key)
            self.assertTrue(nbrs and all(isinstance(n, int) for n in nbrs), key)

    def test_the_two_multi_number_rows(self):
        self.assertEqual(fn.FDC_NUTRIENT_NBR["efa"], ((618, 619), "sum"))
        self.assertEqual(fn.FDC_NUTRIENT_NBR["folate"], ((435, 417), "first"))
        self.assertEqual(fn.FDC_NUTRIENT_NBR["calories"], ((208,), "first"))

    def test_unit_conversion_is_identity_only(self):
        self.assertEqual(fn.FDC_UNIT, {"KCAL": "kcal", "G": "g", "MG": "mg", "UG": "ug"})
        self.assertNotIn("IU", fn.FDC_UNIT)
        self.assertEqual(fn.contract_unit("vitC", "MG"), "mg")
        with self.assertRaises(ValueError):
            fn.contract_unit("vitC", "UG")        # mg <-> ug never silently
        with self.assertRaises(ValueError):
            fn.contract_unit("vitD", "IU")


# ---- loaders ----

class NutrientMapTest(FixtureDir):

    def test_map_is_nbr_to_internal_id(self):
        m = fn.load_nutrient_map(self.dir)
        self.assertEqual(m["208"], 1008)
        self.assertEqual(m["314"], 1100)
        self.assertEqual(len(m), 11)

    def test_resolve_keys_against_the_fixture(self):
        nutrients = fn.load_nutrients(self.dir)
        resolved = fn.resolve_keys(nutrients, strict=False)
        self.assertEqual(resolved["calories"], [(208, 1008)])
        self.assertEqual(resolved["iodine"], [(314, 1100)])
        self.assertEqual(resolved["efa"], [(618, 1269)])      # 619 is not in the fixture
        self.assertEqual(resolved["folate"], [(435, 1190)])
        with self.assertRaises(KeyError):
            fn.resolve_keys(nutrients)                        # strict: vitC's 401 is missing

    def test_an_iu_row_meeting_a_key_raises(self):
        synthetic = NUTRIENT_CSV.replace('"1008","Energy","KCAL","208"', '"1008","Energy","IU","208"')
        _write(self.dir, "nutrient.csv", synthetic)
        with self.assertRaises(ValueError):
            fn.resolve_keys(fn.load_nutrients(self.dir), strict=False)

    def test_a_wrong_metric_unit_raises(self):
        synthetic = NUTRIENT_CSV.replace('"Iodine, I","UG"', '"Iodine, I","MG"')
        _write(self.dir, "nutrient.csv", synthetic)
        with self.assertRaises(ValueError):
            fn.resolve_keys(fn.load_nutrients(self.dir), strict=False)


class FoodNutrientsTest(FixtureDir):

    def test_apple_join(self):
        rec = fn.load_food_nutrients(self.dir, [APPLE])[APPLE]
        self.assertEqual(set(rec), set(fn.KEYS))
        self.assertEqual(rec["carbs"], 13.81)
        self.assertEqual(rec["fibre"], 2.4)

    def test_a_zero_row_is_zero_and_an_absent_row_is_none(self):
        rec = fn.load_food_nutrients(self.dir, [APPLE])[APPLE]
        self.assertEqual(rec["ethanol"], 0.0)
        self.assertIsNotNone(rec["ethanol"])
        self.assertIsNone(rec["iodine"])       # no row: None, never 0
        self.assertIsNone(rec["phytate"])      # no FDC number at all
        self.assertIsNone(rec["calories"])     # its row is not in the three-row fixture

    def test_a_join_on_the_legacy_number_finds_nothing(self):
        # The trap: food_nutrient.nutrient_id is nutrient.id; 205 is the legacy nutrient_nbr.
        rows = fn.read_rows(self.dir, "food_nutrient.csv")
        self.assertEqual([r for r in rows if r["nutrient_id"] == "205"], [])
        self.assertEqual(len([r for r in rows if r["nutrient_id"] == "1005"]), 1)

    def test_an_unknown_id_reads_all_none(self):
        rec = fn.load_food_nutrients(self.dir, [1])[1]
        self.assertTrue(all(v is None for v in rec.values()))


class PortionAndFoodTest(FixtureDir):

    def test_portions_keep_the_modifier_verbatim(self):
        portions = fn.load_portions(self.dir, [APPLE])[APPLE]
        self.assertEqual(portions, [
            {"seq_num": 2, "amount": 1.0, "measure_unit": "undetermined", "modifier": "cup slices",
             "gram_weight": 109.0},
            {"seq_num": 4, "amount": 1.0, "measure_unit": "undetermined", "modifier": 'medium (3" dia)',
             "gram_weight": 182.0},
        ])

    def test_foods(self):
        self.assertEqual(fn.load_foods(self.dir, [APPLE]), {APPLE: {
            "description": "Apples, raw, with skin (Includes foods for USDA's Food Distribution Program)",
            "data_type": "sr_legacy_food", "food_category": "Fruits and Fruit Juices"}})

    def test_the_zip_and_the_dir_read_the_same(self):
        path = os.path.join(self.dir, "x.zip")
        with zipfile.ZipFile(path, "w") as z:
            for name in ("nutrient.csv", "food_nutrient.csv"):
                z.write(os.path.join(self.dir, name), "prefix_dir/" + name)
        with zipfile.ZipFile(path) as z:
            self.assertEqual(fn.load_food_nutrients(z, [APPLE]), fn.load_food_nutrients(self.dir, [APPLE]))


class RetentionTest(FixtureDir):

    def test_a_shifted_row_raises_naming_it(self):
        with self.assertRaises(ValueError) as ctx:
            fn.load_retention(os.path.join(self.dir, "NutrientRetention.csv"))
        self.assertIn("5005", str(ctx.exception))
        self.assertIn("Sep-75", str(ctx.exception))
        self.assertIn("line 3", str(ctx.exception))

    def test_skip_defective(self):
        table, skipped = fn.load_retention(os.path.join(self.dir, "NutrientRetention.csv"),
                                           skip_defective=True)
        self.assertEqual(table, {1: {301: 100}, 5005: {221: 35}})
        self.assertEqual(skipped, [{"line": 3, "retn_code": 5005, "nutr_no": 301, "retn_factor": "Sep-75"}])


# ---- checks ----

class AtwaterTest(unittest.TestCase):

    def test_apple_worked_row(self):
        # Apple 171688 per 100 g: 13.81 C, 2.4 F, 0.26 P, 0.17 fat; FDC Energy 52 kcal.
        rec = {"carbs": 13.81, "fibre": 2.4, "proteins": 0.26, "lipids": 0.17, "ethanol": None}
        self.assertAlmostEqual(fn.atwater(rec), 53.01, places=6)
        self.assertTrue(fn.fibre_known(rec))

    def test_none_is_zero_and_fibre_unknown_is_flagged(self):
        rec = {"carbs": 10.0, "fibre": None, "proteins": None, "lipids": 1.0, "ethanol": 2.0}
        self.assertAlmostEqual(fn.atwater(rec), 40.0 + 9.0 + 14.0)
        self.assertFalse(fn.fibre_known(rec))


class CliTest(unittest.TestCase):

    def test_help(self):
        out = subprocess.run([sys.executable, os.path.join(REPO, "tools", "food_nutrients.py"), "--help"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0)
        self.assertIn("usage", out.stdout)


# ---- the real files ----

@unittest.skipUnless(HAVE_FDC, "the SR Legacy zip is not fetched (python tools/fdc_fetch.py)")
class RealZipTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.zip = zipfile.ZipFile(fn.SR_LEGACY_ZIP)
        cls.nutrients = fn.load_nutrients(cls.zip)

    @classmethod
    def tearDownClass(cls):
        cls.zip.close()

    def test_nutrient_csv_row_count(self):
        # 474 data rows in the SR Legacy archive (the briefing's 477 is the Foundation archive's).
        self.assertEqual(len(fn.read_rows(self.zip, "nutrient.csv")), 474)

    def test_every_key_resolves_with_its_name(self):
        resolved = fn.resolve_keys(self.nutrients)     # strict: raises on a missing number or a bad unit
        self.assertEqual(set(resolved), set(fn.KEYS) - {"phytate"})
        for key, rows in resolved.items():
            self.assertEqual(len(rows), len(fn.FDC_NUTRIENT_NBR[key][0]), key)
            for nbr, nid in rows:
                self.assertEqual(self.nutrients[str(nbr)]["name"], fn.FDC_NAME[nbr], key)
                self.assertEqual(self.nutrients[str(nbr)]["id"], nid)

    def test_coverage(self):
        self.assertEqual(fn.coverage(self.zip), fn.SR_LEGACY_COVERAGE)

    def test_apple(self):
        rec = fn.load_food_nutrients(self.zip, [APPLE])[APPLE]
        self.assertEqual((rec["calories"], rec["carbs"], rec["fibre"], rec["proteins"], rec["lipids"]),
                         (52.0, 13.81, 2.4, 0.26, 0.17))
        self.assertIsNone(rec["iodine"])
        self.assertEqual(rec["ethanol"], 0.0)
        self.assertEqual(rec["folate"], 3.0)
        portions = fn.load_portions(self.zip, [APPLE])[APPLE]
        self.assertEqual([p["seq_num"] for p in portions], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(portions[3]["modifier"], 'medium (3" dia)')


@unittest.skipUnless(HAVE_RETENTION, "NutrientRetention.csv is not fetched (python tools/fdc_fetch.py)")
class RealRetentionTest(unittest.TestCase):

    def test_the_real_file_raises(self):
        with self.assertRaises(ValueError):
            fn.load_retention(fn.RETENTION_CSV)

    def test_exactly_24_defective_rows_all_on_5005(self):
        table, skipped = fn.load_retention(fn.RETENTION_CSV, skip_defective=True)
        self.assertEqual(len(skipped), 24)
        self.assertEqual({s["retn_code"] for s in skipped}, {5005})
        self.assertEqual({s["retn_factor"] for s in skipped}, {"Sep-75"})
        self.assertEqual(table[5005], {421: 100, 221: 35})
        self.assertEqual(len(table), 270)
        self.assertEqual(sum(len(v) for v in table.values()), 7018 - 24)


# ---- mapping ----

import csv, io, json

def _item(pz_id, kind, display, food_type=None, basis=None, macros=(None, None, None, None),
          spice=None, cant_eat=None, is_cookable=None, fluid_ids=None):
    cal, carb, lip, pro = macros
    return {"id": pz_id, "kind": kind, "display_name": display, "food_type": food_type,
            "nutrition_basis": basis, "calories": cal, "carbohydrates": carb, "lipids": lip,
            "proteins": pro, "spice": spice, "cant_eat": cant_eat, "is_cookable": is_cookable,
            "fluid_ids": fluid_ids}


# Base.Apple's four macros as data/food-items.json writes them (kcal, carbs, lipids, proteins).
APPLE_MACROS = (95.0, 25.13, 0.31, 0.47)

FIVE = {"meta": {"build": "42.20.4"},
        "items": [
            _item("Base.Apple", "food", "Apple", "Fruits", "per_item", APPLE_MACROS),
            _item("Base.Salt", "food", "Salt", "NoExplicit", "per_item", spice=True),
            _item("Base.WaterBottle", "fluid_container", "Water Bottle", basis="per_litre",
                  macros=(None, None, None, None), fluid_ids=["Water", "CarbonatedWater"]),
            _item("Base.Glue", "drainable", "Glue"),
        ],
        "fluids": [{"id": "Water", "kind": "fluid", "display_name": "Water", "calories": None,
                    "carbohydrates": None, "lipids": None, "proteins": None}]}


class MapDir(unittest.TestCase):
    """A temp dataset JSON and a temp mapping dir seeded from it."""

    DATA = FIVE

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.dataset = os.path.join(self.tmp, "food-items.json")
        with open(self.dataset, "w", encoding="utf-8") as handle:
            json.dump(self.DATA, handle)
        self.map = os.path.join(self.tmp, "map")
        fn.seed_map(self.map, self.dataset)

    def part(self, name):
        with open(os.path.join(self.map, name + ".csv"), encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def write_part(self, name, rows):
        fn.write_part(os.path.join(self.map, name + ".csv"), rows)

    def edit(self, part, pz_id, **cells):
        rows = self.part(part)
        for row in rows:
            if row["pz_id"] == pz_id:
                row.update(cells)
        self.write_part(part, rows)

    def check(self, allow_unfilled=True):
        return fn.check_map(self.map, self.dataset, allow_unfilled=allow_unfilled, out=io.StringIO())


class SeedTest(MapDir):

    def test_six_parts_with_the_schema(self):
        self.assertEqual(sorted(os.listdir(self.map)), sorted(p + ".csv" for p in fn.MAP_PARTS))
        for part in fn.MAP_PARTS:
            with open(os.path.join(self.map, part + ".csv"), encoding="utf-8", newline="") as handle:
                text = handle.read()
            self.assertEqual(text.split("\n")[0], ",".join(fn.MAP_COLUMNS))
            self.assertNotIn("\r", text)

    def test_the_parts_and_the_reasons(self):
        self.assertEqual([r["pz_id"] for r in self.part("produce")], ["Base.Apple"])
        self.assertEqual([r["pz_id"] for r in self.part("fluids")], ["Water"])
        for part in ("grains-legumes", "meat-fish-egg-dairy", "manufactured"):
            self.assertEqual(self.part(part), [])
        nn = {r["pz_id"]: (r["pz_kind"], r["no_nutrition_reason"]) for r in self.part("no-nutrition")}
        self.assertEqual(nn, {"Base.Glue": ("drainable", "not_food"),
                              "Base.Salt": ("food", "spice_only"),
                              "Base.WaterBottle": ("fluid_container", "fluid_sourced")})
        self.assertEqual([r["pz_id"] for r in self.part("no-nutrition")],
                         ["Base.Glue", "Base.Salt", "Base.WaterBottle"])    # sorted by pz_id

    def test_family_and_copied_cells(self):
        apple = self.part("produce")[0]
        self.assertEqual(apple["family"], "95.0|25.13|0.31|0.47")
        self.assertEqual((apple["pz_display"], apple["pz_kind"]), ("Apple", "food"))
        self.assertEqual({k: v for k, v in apple.items() if k not in ("pz_id", "pz_display", "pz_kind",
                                                                       "family")},
                         dict.fromkeys(set(fn.MAP_COLUMNS) - {"pz_id", "pz_display", "pz_kind", "family"},
                                       ""))
        self.assertEqual(self.part("no-nutrition")[1]["family"], "")     # Salt: no macro at all

    def test_never_overwrites(self):
        with self.assertRaises(FileExistsError):
            fn.seed_map(self.map, self.dataset)
        with self.assertRaises(FileExistsError):
            fn.seed_map(self.map, self.dataset, force=True)    # --force never overwrites a part

    def test_force_seeds_an_existing_dir_without_parts(self):
        other = os.path.join(self.tmp, "other")
        os.mkdir(other)
        _write(other, "README.md", "x\n")
        with self.assertRaises(FileExistsError):
            fn.seed_map(other, self.dataset)
        fn.seed_map(other, self.dataset, force=True)
        self.assertIn("produce.csv", os.listdir(other))

    def test_the_seed_passes_its_own_check_when_unfilled_is_allowed(self):
        counts = self.check()
        self.assertEqual(counts["violations"], [])
        self.assertEqual(counts["rows"], 5)
        self.assertEqual(counts["unfilled"], 2)        # Apple and the Water fluid
        self.assertEqual(counts["filled"], 3)
        self.assertEqual(counts["by_reason"], {"fluid_sourced": 1, "not_food": 1, "spice_only": 1})
        self.assertEqual(counts["by_kind"], {"drainable": 1, "fluid": 1, "fluid_container": 1, "food": 2})
        self.assertEqual(counts["parts"]["no-nutrition"], 3)
        self.assertEqual(counts["families"], 2)        # Apple's tuple and Salt's empty one

    def test_unfilled_fails_without_the_flag(self):
        counts = self.check(allow_unfilled=False)
        self.assertEqual(len(counts["violations"]), 2)
        self.assertTrue(all("unfilled" in v for v in counts["violations"]))


class PartRuleTest(unittest.TestCase):

    def test_kinds_and_buckets(self):
        part = fn.seed_part
        self.assertEqual(part({"kind": "fluid"}), "fluids")
        self.assertEqual(part(_item("a", "drainable", "x", basis="per_item", macros=(0.0, None, None, None))),
                         "no-nutrition")
        self.assertEqual(part(_item("a", "fluid_container", "x", basis="per_litre", fluid_ids=["Water"])),
                         "no-nutrition")
        self.assertEqual(part(_item("a", "food", "x", "Fruits")), "no-nutrition")      # empty basis
        food = lambda t, **kw: _item("a", "food", "x", t, "per_item", (1.0, 1.0, 1.0, 1.0), **kw)
        self.assertEqual(part(food("Herb", spice=True)), "no-nutrition")
        self.assertEqual(part(food("Vegetables")), "produce")
        self.assertEqual(part(food("Rice")), "grains-legumes")
        self.assertEqual(part(food("Insect")), "meat-fish-egg-dairy")
        self.assertEqual(part(food("Candy")), "manufactured")
        self.assertEqual(part(food(None)), "manufactured")
        self.assertEqual(part(food("SomeNewType")), "manufactured")
        # a sealed can keeps CantEat and still carries nutrition: a food part, not no-nutrition
        self.assertEqual(part(food("Fish", cant_eat=True)), "meat-fish-egg-dairy")
        self.assertEqual(part(_item("a", "food", "x", None, "per_item", cant_eat=True)), "no-nutrition")

    def test_the_bucket_lists_are_disjoint(self):
        lists = (fn.PRODUCE_TYPES, fn.GRAINS_LEGUMES_TYPES, fn.ANIMAL_TYPES, fn.MANUFACTURED_TYPES)
        seen = set()
        for types in lists:
            self.assertFalse(seen & set(types))
            seen |= set(types)

    def test_reasons(self):
        reason = fn.seed_reason
        self.assertEqual(reason(_item("Base.Bleach", "fluid_container", "Bleach", basis="per_litre",
                                      fluid_ids=["Bleach"])), "hazard")
        self.assertEqual(reason({"id": "Bleach", "kind": "fluid"}), "hazard")
        self.assertEqual(reason(_item("Base.RatPoison", "drainable", "Rat Poison", basis="per_item")), "hazard")
        self.assertEqual(reason(_item("Base.PillsVitamins", "drainable", "Vitamins")), "tobacco_or_drug")
        self.assertEqual(reason(_item("Base.CigaretteSingle", "food", "Cigarette", basis="per_item")),
                         "tobacco_or_drug")
        self.assertEqual(reason(_item("Base.Cow_Head_Angus", "food", "Cow Head")), "inedible_body_part")
        self.assertEqual(reason(_item("Base.CorpseAnimal", "food", "Animal Corpse")), "inedible_body_part")
        self.assertEqual(reason(_item("Base.SunflowerHead", "food", "Sunflower Head")), "")
        self.assertEqual(reason(_item("Base.Bag_LeatherWaterBag", "fluid_container", "Bag", basis="per_litre",
                                      fluid_ids=["Water"])), "fluid_sourced")
        self.assertEqual(reason(_item("Base.Vinegar2", "drainable", "Vinegar", basis="per_item",
                                      macros=(0.0, None, None, None))), "not_food")
        self.assertEqual(reason(_item("Base.ClayJar", "fluid_container", "Clay Jar", fluid_ids=[])),
                         "empty_container")
        self.assertEqual(reason(_item("Base.X", "food", "Pot of X", basis="per_item")), "vessel_only")
        self.assertEqual(reason(_item("Base.X", "food", "Pot of X", basis="per_item",
                                      macros=(5.0, 1.0, 0.0, 0.0))), "")
        self.assertEqual(reason(_item("Base.Salt", "food", "Salt", basis="per_item", spice=True)), "spice_only")
        self.assertEqual(reason(_item("Base.Apple", "food", "Apple", "Fruits", "per_item", APPLE_MACROS)), "")

    def test_family(self):
        self.assertEqual(fn.family_of({"calories": 720.0, "carbohydrates": 72.0, "lipids": 45.0,
                                       "proteins": 4.5}), "720.0|72.0|45.0|4.5")
        self.assertEqual(fn.family_of({"calories": 0.0, "carbohydrates": None, "lipids": None,
                                       "proteins": None}), "")


class CheckMapTest(MapDir):

    def assert_violation(self, counts, needle):
        self.assertTrue(any(needle in v for v in counts["violations"]), counts["violations"])

    def test_duplicate_across_parts_names_the_later_file(self):
        self.write_part("manufactured", self.part("produce"))
        counts = self.check()
        self.assertEqual(counts["duplicates"], 1)
        self.assert_violation(counts, "duplicate Base.Apple")
        dup = [v for v in counts["violations"] if "duplicate" in v][0]
        self.assertIn("produce.csv", dup)                # merge order: manufactured < produce
        self.assertTrue(dup.index("manufactured.csv") < dup.index("produce.csv"))

    def test_the_merge_order_is_filename_order(self):
        rows, errors = fn.read_map(self.map)
        self.assertEqual(errors, [])
        parts = [r["_part"] for r in rows]
        self.assertEqual(parts, sorted(parts))
        self.assertEqual(sorted(set(parts)), ["fluids", "no-nutrition", "produce"])

    def test_orphan(self):
        rows = self.part("produce")
        rows.append(dict(rows[0], pz_id="Base.Zombie"))
        self.write_part("produce", rows)
        counts = self.check()
        self.assertEqual(counts["orphans"], 1)
        self.assert_violation(counts, "orphan Base.Zombie")

    def test_unmapped(self):
        self.write_part("produce", [])
        counts = self.check()
        self.assertEqual(counts["unmapped"], 1)
        self.assert_violation(counts, "unmapped Base.Apple")

    def test_kind_mismatch(self):
        self.edit("produce", "Base.Apple", pz_kind="drainable")
        self.assert_violation(self.check(), "pz_kind")

    def test_open_enum(self):
        self.edit("produce", "Base.Apple", fdc_id="171688", fdc_source="sr_legacy", confidence="certain")
        self.assert_violation(self.check(), "confidence")
        self.edit("produce", "Base.Apple", confidence="exact", portion_source="fdc_portion:x")
        self.assert_violation(self.check(), "portion_source")
        self.edit("produce", "Base.Apple", portion_source="fdc_portion:4", state_baseline="boiled")
        self.assert_violation(self.check(), "state_baseline")
        self.edit("produce", "Base.Apple", state_baseline="raw", fdc_source="cofid")
        self.assert_violation(self.check(), "fdc_source")
        self.edit("no-nutrition", "Base.Glue", no_nutrition_reason="boring")
        self.assert_violation(self.check(), "no_nutrition_reason")

    def test_a_closed_row_passes(self):
        self.edit("produce", "Base.Apple", fdc_id="171688", fdc_source="sr_legacy", confidence="exact",
                  portion_grams="182", portion_source="vanilla_implied", state_baseline="raw")
        self.edit("fluids", "Water", fdc_id="174158", fdc_source="sr_legacy", confidence="exact")
        counts = self.check(allow_unfilled=False)
        self.assertEqual(counts["violations"], [])
        self.assertEqual(counts["by_confidence"], {"exact": 2})

    def test_fdc_id_and_reason_are_exclusive(self):
        self.edit("no-nutrition", "Base.Glue", fdc_id="1", fdc_source="sr_legacy", confidence="exact")
        self.assert_violation(self.check(), "both")

    def test_a_mapped_row_names_source_and_confidence(self):
        self.edit("produce", "Base.Apple", fdc_id="171688")
        counts = self.check()
        self.assert_violation(counts, "fdc_source")
        self.assert_violation(counts, "confidence")

    def test_guess_needs_notes(self):
        self.edit("produce", "Base.Apple", fdc_id="171688", fdc_source="sr_legacy", confidence="guess")
        counts = self.check()
        self.assertEqual(counts["guesses"], 1)
        self.assert_violation(counts, "guess")
        self.edit("produce", "Base.Apple", notes="no better entry")
        self.assertEqual(self.check()["violations"], [])

    def test_retention_code_only_on_cookable(self):
        self.edit("produce", "Base.Apple", cook_retention_code="5000")
        self.assert_violation(self.check(), "cook_retention_code")

    def test_a_bad_header_is_an_error(self):
        with open(os.path.join(self.map, "produce.csv"), "w", encoding="utf-8", newline="") as handle:
            handle.write("pz_id,notes\nBase.Apple,\n")
        self.assert_violation(self.check(), "header")

    def test_the_ref_hook(self):
        calls = []
        def hook(rows, records):
            calls.append(len(rows))
            return ["hooked"]
        fn.MAP_REF_CHECKS.append(hook)
        self.addCleanup(fn.MAP_REF_CHECKS.remove, hook)
        self.assertIn("hooked", self.check()["violations"])
        self.assertEqual(calls, [5])


class FamilySplitTest(MapDir):

    DATA = {"meta": {}, "fluids": [], "items": [
        _item("Base.CannedA", "food", "Can A", None, "per_item", (159.0, 1.0, 1.0, 35.0)),
        _item("Base.CannedB", "food", "Can B", None, "per_item", (159.0, 1.0, 1.0, 35.0)),
        _item("Base.CannedC", "food", "Can C", None, "per_item", (159.0, 1.0, 1.0, 35.0)),
    ]}

    def map_all(self, ids):
        rows = self.part("manufactured")
        for row, fid in zip(rows, ids):
            row.update(fdc_id=fid, fdc_source="sr_legacy", confidence="close")
        self.write_part("manufactured", rows)

    def test_one_family(self):
        self.assertEqual({r["family"] for r in self.part("manufactured")}, {"159.0|1.0|1.0|35.0"})
        self.assertEqual(self.check()["families"], 1)

    def test_an_agreeing_family_passes(self):
        self.map_all(["100", "100", "100"])
        counts = self.check()
        self.assertEqual((counts["violations"], counts["families_split"]), ([], 0))

    def test_a_split_family_without_notes_fails(self):
        self.map_all(["100", "100", "200"])
        counts = self.check()
        self.assertEqual(counts["families_split"], 1)
        self.assertTrue(any("family" in v and "Base.CannedC" in v for v in counts["violations"]))
        self.edit("manufactured", "Base.CannedC", notes="a different fish")
        counts = self.check()
        self.assertEqual((counts["violations"], counts["families_split"]), ([], 1))


class ImpliedPortionTest(FixtureDir):
    """The Task 2 Apple fixture plus Apple's energy, lipid and protein rows, quoted verbatim."""

    APPLE_EXTRA = (
        '"1631310","171688","1008","52","0","49","","","","",""',            # food_nutrient.csv:347638
        '"1631338","171688","1004","0.17","35","1","0.05","0.31","","",""',  # food_nutrient.csv:347666
        '"1631368","171688","1003","0.26","29","1","0.17","0.57","","",""',  # food_nutrient.csv:347696
    )

    def setUp(self):
        super().setUp()
        lines = FOOD_NUTRIENT_CSV.rstrip("\n").split("\n")
        # file order: 347630, 347637, 347638, 347666, 347685, 347696
        lines = lines[:3] + [self.APPLE_EXTRA[0], self.APPLE_EXTRA[1], lines[3], self.APPLE_EXTRA[2]]
        _write(self.dir, "food_nutrient.csv", "\n".join(lines) + "\n")
        self.fdc = fn.load_food_nutrients(self.dir, [APPLE])[APPLE]
        self.apple = _item("Base.Apple", "food", "Apple", "Fruits", "per_item", APPLE_MACROS)

    def test_apple_is_vanilla_implied(self):
        masses = fn.implied_masses(self.apple, self.fdc)
        self.assertEqual(set(masses), {"calories", "carbs", "lipids", "proteins"})
        for key, grams in masses.items():
            self.assertTrue(180.0 < grams < 183.0, (key, grams))
        verdict = fn.portion_verdict(self.apple, self.fdc, fn.load_portions(self.dir, [APPLE]).get(APPLE, []))
        self.assertEqual(verdict["portion_source"], "vanilla_implied")
        self.assertTrue(181.0 <= verdict["portion_grams"] <= 183.0)
        self.assertLessEqual(verdict["spread"], 1.1)
        self.assertEqual(verdict["usable"], 4)

    def test_a_wide_spread_lists_the_fdc_portions(self):
        skewed = dict(self.apple, lipids=3.1)            # ten times the apple's fat
        verdict = fn.portion_verdict(skewed, self.fdc, fn.load_portions(self.dir, [APPLE])[APPLE])
        self.assertIsNone(verdict["portion_source"])
        self.assertGreater(verdict["spread"], 1.1)
        self.assertEqual([(p["portion_source"], p["gram_weight"], p["modifier"]) for p in verdict["portions"]],
                         [("fdc_portion:2", 109.0, "cup slices"), ("fdc_portion:4", 182.0, 'medium (3" dia)')])

    def test_one_usable_macro_is_not_enough(self):
        only = dict(self.apple, calories=None, lipids=None, proteins=None)
        verdict = fn.portion_verdict(only, self.fdc, [])
        self.assertEqual(verdict["usable"], 1)
        self.assertIsNone(verdict["portion_source"])

    def test_the_driver_reads_the_mapping_or_an_fdc_argument(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        dataset = os.path.join(tmp, "food-items.json")
        with open(dataset, "w", encoding="utf-8") as handle:
            json.dump(FIVE, handle)
        mapdir = os.path.join(tmp, "map")
        fn.seed_map(mapdir, dataset)
        out = io.StringIO()
        self.assertEqual(fn.implied_portion("Base.Apple", mapdir, dataset, self.dir, out=out), [])
        self.assertIn("no fdc_id", out.getvalue())
        got = fn.implied_portion("Base.Apple", mapdir, dataset, self.dir, fdc=APPLE, out=io.StringIO())
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["portion_source"], "vanilla_implied")
        self.assertEqual(got[0]["fdc_id"], APPLE)


class RealMapTest(unittest.TestCase):
    """The committed mapping against the committed dataset."""

    def test_every_dataset_food_type_is_bucketed(self):
        with open(fn.DATASET_JSON, encoding="utf-8") as handle:
            items = json.load(handle)["items"]
        named = set(fn.PRODUCE_TYPES) | set(fn.GRAINS_LEGUMES_TYPES) | set(fn.ANIMAL_TYPES) | set(fn.MANUFACTURED_TYPES)
        types = {i["food_type"] for i in items if i["food_type"] is not None}
        self.assertEqual(types - named, set())

    @unittest.skipUnless(os.path.isdir(fn.MAP_DIR), "the mapping is not seeded")
    def test_the_committed_mapping_checks(self):
        counts = fn.check_map(allow_unfilled=True, out=io.StringIO())
        self.assertEqual(counts["violations"], [])
        self.assertEqual(counts["rows"], 1066)
        self.assertEqual((counts["unmapped"], counts["orphans"], counts["duplicates"]), (0, 0, 0))
        self.assertLessEqual(counts["guesses"], 40)       # ruling 10's budget


if __name__ == "__main__":
    unittest.main()
