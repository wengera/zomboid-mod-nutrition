"""Tests for tools/food_nutrients.py (Plan 6): the FDC join core (Task 2), the mapping (Task 3), the
extract (Task 5), the output with its checks (Task 6), the emitters (Task 9) and the inference
templates (Task 10).

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
APPLE_DESCRIPTION = "Apples, raw, with skin (Includes foods for USDA's Food Distribution Program)"   # food.csv:4178


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
from unittest import mock

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
        # Task 5: the FDC-backed referential checks skip here (their files are absent), so these
        # synthetic ids ("1", "100") meet only the Task 3 rules; RefCheckTest points them at fixtures
        absent = os.path.join(self.tmp, "absent")
        patcher = mock.patch.dict(fn.REF_SOURCES, {"sr_legacy": absent, "retention": absent})
        patcher.start()
        self.addCleanup(patcher.stop)

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

    def test_spice_foods_with_calories_are_foods(self):
        butter = _item("Base.Butter", "food", "Butter", "Dressing", "per_item", (3200.0, 0.0, 360.0, 3.0), spice=True)
        self.assertEqual(fn.seed_part(butter), "manufactured")
        self.assertEqual(fn.seed_reason(butter), "")
        herb = _item("Base.Basil", "food", "Basil", "Herb", "per_item", (0.1, 0.0, 0.0, 0.0), spice=True)
        self.assertEqual(fn.seed_part(herb), "no-nutrition")
        self.assertEqual(fn.seed_reason(herb), "spice_only")
        bare = _item("Base.Salt", "food", "Salt", "NoExplicit", "per_item", spice=True)
        self.assertEqual((fn.seed_part(bare), fn.seed_reason(bare)), ("no-nutrition", "spice_only"))

    def test_a_spice_drainable_is_spice_only(self):
        vinegar = _item("Base.Vinegar", "drainable", "Vinegar", basis="per_item", macros=(0.0, None, None, None),
                        spice=True)
        self.assertEqual(fn.seed_reason(vinegar), "spice_only")
        self.assertEqual(fn.seed_part(vinegar), "no-nutrition")

    def test_the_exact_hazard_ids_and_cigar(self):
        spray = _item("Base.GardeningSprayCigarettes", "drainable", "Spray", basis="per_item")
        self.assertEqual(fn.seed_reason(spray), "hazard")
        for pz_id in ("Base.RatPoison", "Base.CorrectionFluid", "Base.Bleach"):
            self.assertEqual(fn.seed_reason(_item(pz_id, "drainable", "x")), "hazard")
        self.assertEqual(fn.seed_reason(_item("Base.Cigarillo", "food", "Cigarillo", basis="per_item")),
                         "tobacco_or_drug")
        self.assertEqual(fn.seed_reason(_item("Base.Cigar", "food", "Cigar", basis="per_item")),
                         "tobacco_or_drug")

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

    def test_reason_kind_pairs(self):
        self.edit("produce", "Base.Apple", no_nutrition_reason="empty_container", notes="n")
        self.assert_violation(self.check(), "empty_container on a kind other than fluid_container")
        self.edit("no-nutrition", "Base.Glue", no_nutrition_reason="inedible_body_part")
        self.assert_violation(self.check(), "inedible_body_part on a kind other than food")
        self.edit("no-nutrition", "Base.Glue", no_nutrition_reason="vessel_only")
        self.assert_violation(self.check(), "vessel_only on a kind other than food")
        self.edit("no-nutrition", "Base.WaterBottle", no_nutrition_reason="fluid_sourced")
        counts = self.check()
        self.assertFalse(any("WaterBottle" in v and "kind other" in v for v in counts["violations"]))
        self.edit("no-nutrition", "Base.Glue", no_nutrition_reason="fluid_sourced")
        self.assert_violation(self.check(), "fluid_sourced on a kind other than fluid_container")

    def test_a_reason_on_a_food_with_calories_needs_notes(self):
        self.edit("produce", "Base.Apple", no_nutrition_reason="not_food")
        self.assert_violation(self.check(), "95.0 kcal, without notes")
        self.edit("produce", "Base.Apple", notes="the vessel rule")
        self.assertFalse(any("kcal" in v for v in self.check()["violations"]))

    def test_the_fdc_id_format(self):
        self.edit("produce", "Base.Apple", fdc_id="17x688", fdc_source="sr_legacy", confidence="exact")
        self.assert_violation(self.check(), "is not digits")
        self.edit("produce", "Base.Apple", fdc_id="17x688", fdc_source="literature")
        self.assertFalse(any("is not digits" in v for v in self.check()["violations"]))

    def test_the_guess_budget(self):
        rows = self.part("produce")
        rows[0].update(fdc_id="1", fdc_source="sr_legacy", confidence="guess", notes="n")
        self.write_part("produce", rows)
        self.assertFalse(any("guess budget" in v for v in self.check()["violations"]))
        saved = fn.GUESS_BUDGET
        fn.GUESS_BUDGET = 0
        self.addCleanup(setattr, fn, "GUESS_BUDGET", saved)
        self.assert_violation(self.check(), "guess budget: 1 guess rows, the budget is 0")
        self.assertEqual(saved, 40)

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

    def test_the_tie_break_is_numeric(self):
        self.map_all(["9", "100", "100"])
        self.assertEqual(sorted(["100", "9", "reason:x"], key=fn._id_order), ["9", "100", "reason:x"])
        # a 1-1 tie between 9 and 100 picks 9 as modal: the 100 row is the one reported
        rows = self.part("manufactured")
        rows[2].update(fdc_id="9")
        rows[1].update(fdc_id="100")
        rows[0].update(fdc_id="100")
        rows[2].update(fdc_id="9")
        self.write_part("manufactured", rows[:3])
        counts = self.check()
        self.assertEqual(counts["families_split"], 1)

    def test_a_reasoned_row_splits_the_family(self):
        self.map_all(["100", "100", "100"])
        self.edit("manufactured", "Base.CannedC", fdc_id="", fdc_source="", confidence="",
                  no_nutrition_reason="not_food")
        counts = self.check()
        self.assertEqual(counts["families_split"], 1)
        self.assertTrue(any("Base.CannedC" in v and "family" in v for v in counts["violations"]))
        self.edit("manufactured", "Base.CannedC", notes="a vessel")
        self.assertEqual(self.check()["families_split"], 1)
        self.assertFalse(any("family" in v for v in self.check()["violations"]))


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
        # the calorie-bearing seeded reasons are being mapped or noted in place by the curation waves;
        # the controller drops this filter at the waves' close
        open_rule = [v for v in counts["violations"] if "kcal, without notes" in v]
        self.assertEqual([v for v in counts["violations"] if v not in open_rule], [])
        self.assertEqual(counts["rows"], 1066)
        self.assertEqual((counts["unmapped"], counts["orphans"], counts["duplicates"]), (0, 0, 0))
        self.assertLessEqual(counts["guesses"], 40)       # ruling 10's budget


# ---- extract ----

import datetime, hashlib

SR_PREFIX = "FoodData_Central_sr_legacy_food_csv_2018-04/"
EGG = 171287

# The two-food zip: the Task 2 fixtures plus Egg's rows and the PUFA 18:3 rows, quoted verbatim.
EXTRACT_NUTRIENT_CSV = NUTRIENT_CSV + '"1270","PUFA 18:3","G","619","13900.0"\n'   # nutrient.csv:273

EXTRACT_FOOD_NUTRIENT_CSV = FOOD_NUTRIENT_CSV + "\n".join([
    '"1631310","171688","1008","52","0","49","","","","",""',                 # food_nutrient.csv:347638
    '"1631317","171688","1269","0.043","4","","","","","",""',                # food_nutrient.csv:347645
    '"1631318","171688","1270","0.009","4","","","","","",""',                # food_nutrient.csv:347646
    '"1597626","171287","1008","143","0","49","","","","",""',                # food_nutrient.csv:313954
    '"1597683","171287","1003","12.56","12","1","11.81","13.06","","",""',    # food_nutrient.csv:314011
    '"1597687","171287","1018","0","0","","","","","",""',                    # food_nutrient.csv:314015
    '"1597694","171287","1104","540","0","","","","","",""',                  # food_nutrient.csv:314022
    '"1597709","171287","1051","76.15","12","1","75.43","76.94","","",""',    # food_nutrient.csv:314037
    '"1597714","171287","1004","9.51","12","1","8.78","10.3","","",""',       # food_nutrient.csv:314042
    '"1597715","171287","1269","1.555","12","","1.317","2.01","","",""',      # food_nutrient.csv:314043
    '"1597716","171287","1270","0.048","12","","0.034","0.059","","",""',     # food_nutrient.csv:314044
    '"1597747","171287","1190","47","0","49","","","","",""',                 # food_nutrient.csv:314075
    '"1597748","171287","1005","0.72","0","49","","","","",""',               # food_nutrient.csv:314076
    '"1597756","171287","1079","0","1","1","","","","",""',                   # food_nutrient.csv:314084
]) + "\n"

EXTRACT_FOOD_CSV = FOOD_CSV + '"171287","sr_legacy_food","Egg, whole, raw, fresh","1","2019-04-01"\n'  # food.csv:3777

EXTRACT_FOOD_CATEGORY_CSV = FOOD_CATEGORY_CSV + '"1","0100","Dairy and Egg Products"\n'        # food_category.csv:2

EXTRACT_FOOD_PORTION_CSV = FOOD_PORTION_CSV + "\n".join([
    '"88374","171287","1","1","9999","","large","50","","",""',                     # food_portion.csv:6827
    '"88375","171287","2","1","9999","","extra large","56","","",""',               # food_portion.csv:6828
    '"88378","171287","6","1","9999","","medium","44","","",""',                    # food_portion.csv:6831
]) + "\n"

# Synthetic side tables (the schema of the committed ones; the values are the fixture's own).
IODINE_FIXTURE = ('key,food,iodine_ug_100g,page,note\n'
                  'egg-whole-raw,"Egg, whole, raw, fresh",49,1,a note\n'
                  'milk-whole,"Milk, whole, fluid",34,1,uncited\n')
PHYTATE_FIXTURE = ('family,phytate_mg_100g,source,note\n'
                   'lentils,890,a citation,a note\n'
                   'peas,720,a citation,uncited\n'
                   'flour,214.32,a fresh citation,basis=fresh; mg per 100 g edible portion\n')
INSECT_FIXTURE = ('key,order_or_taxon,basis,protein_g_100g,fat_g_100g,fibre_g_100g,carb_g_100g,ash_g_100g,'
                  'energy_kcal_100g,moisture_pct,source,page_or_table,note\n'
                  'rumpold2013:orthoptera,Orthoptera,dm,61.32,13.41,9.55,12.98,3.85,426.25,,a source,Table 4,a note\n'
                  'rumpold2013:diptera,Diptera,dm,49.48,22.75,13.56,6.01,10.31,409.78,,a source,Table 4,uncited\n')

EXTRACT_DATA = {"meta": {}, "fluids": [], "items": [
    _item("Base.Apple", "food", "Apple", "Fruits", "per_item", APPLE_MACROS),
    _item("Base.Lentils", "food", "Lentils", "Bean", "per_item", (300.0, 50.0, 1.0, 20.0)),
    _item("Base.Egg", "food", "Egg", "Egg", "per_item", (63.0, 0.4, 4.4, 5.6), is_cookable=True),
    _item("Base.Cricket", "food", "Cricket", "Insect", "per_item", (20.0, 1.0, 1.0, 3.0), is_cookable=True),
    _item("Base.Glue", "drainable", "Glue"),
]}


def _sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class ExtractFixture(MapDir):
    """A five-record dataset, its mapping filled, the two-food SR Legacy zip, the retention CSV, the
    three side tables and a manifest, every REF_SOURCES path pointed at them."""

    DATA = EXTRACT_DATA

    def setUp(self):
        super().setUp()
        fdc = os.path.join(self.tmp, "fdc")
        os.makedirs(fdc)
        self.zip = os.path.join(fdc, os.path.basename(fn.SR_LEGACY_ZIP))
        with zipfile.ZipFile(self.zip, "w") as archive:
            for name, text in (("nutrient.csv", EXTRACT_NUTRIENT_CSV),
                               ("food_nutrient.csv", EXTRACT_FOOD_NUTRIENT_CSV),
                               ("food_portion.csv", EXTRACT_FOOD_PORTION_CSV), ("food.csv", EXTRACT_FOOD_CSV),
                               ("food_category.csv", EXTRACT_FOOD_CATEGORY_CSV),
                               ("measure_unit.csv", MEASURE_UNIT_CSV)):
                archive.writestr(SR_PREFIX + name, text)
        self.retention = os.path.join(fdc, "NutrientRetention.csv")
        _write(fdc, "NutrientRetention.csv", RETENTION_CSV)
        for name, text in (("iodine.csv", IODINE_FIXTURE), ("phytate.csv", PHYTATE_FIXTURE),
                           ("insects.csv", INSECT_FIXTURE)):
            _write(self.tmp, name, text)
        self.manifest = os.path.join(fdc, "manifest.json")
        self.write_manifest()
        patcher = mock.patch.dict(fn.REF_SOURCES, {
            "iodine": os.path.join(self.tmp, "iodine.csv"), "phytate": os.path.join(self.tmp, "phytate.csv"),
            "insects": os.path.join(self.tmp, "insects.csv"), "sr_legacy": self.zip,
            "retention": self.retention, "manifest": self.manifest})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.out = os.path.join(self.tmp, "fdc-extract.json")
        self.edit("produce", "Base.Apple", fdc_id=str(APPLE), fdc_source="sr_legacy", confidence="exact",
                  fdc_description=APPLE_DESCRIPTION, portion_grams="182", portion_source="vanilla_implied", state_baseline="raw",
                  phytate_mg_100g="0", phytate_source="zero:fruit")
        self.edit("grains-legumes", "Base.Lentils", fdc_id=str(APPLE), fdc_source="sr_legacy",
                  fdc_description=APPLE_DESCRIPTION, confidence="proxy", notes="a synthetic stand-in", phytate_mg_100g="890",
                  phytate_source="schlemmer2009:lentils")
        self.edit("meat-fish-egg-dairy", "Base.Egg", fdc_id=str(EGG), fdc_source="sr_legacy",
                  fdc_description="Egg, whole, raw, fresh", confidence="exact", cook_retention_code="1", iodine_ref="iodine:egg-whole-raw",
                  phytate_mg_100g="0", phytate_source="zero:egg")
        self.edit("meat-fish-egg-dairy", "Base.Cricket", fdc_id="rumpold2013:orthoptera",
                  fdc_source="literature", confidence="guess", notes="the order mean, dry matter")
        self.edit("no-nutrition", "Base.Glue", no_nutrition_reason="not_food")

    def write_manifest(self, **override):
        rows = []
        for src in fn.fdc_fetch.sources():
            row = {"name": src["name"], "filename": src["filename"], "url": src["url"],
                   "fetched": "2026-10-06", "bytes": 1, "sha256": "0" * 64}
            if src["filename"] == os.path.basename(self.zip):
                row.update(bytes=os.path.getsize(self.zip), sha256=_sha256(self.zip))
            if src["filename"] == os.path.basename(self.retention):
                row.update(bytes=os.path.getsize(self.retention), sha256=_sha256(self.retention))
            row.update(override.get(src["filename"], {}))
            rows.append(row)
        with open(self.manifest, "w", encoding="utf-8") as handle:
            json.dump(rows, handle)

    def build(self):
        return fn.build_extract(self.map, self.dataset, self.out, out=io.StringIO())

    def assert_violation(self, counts, needle):
        self.assertTrue(any(needle in v for v in counts["violations"]), counts["violations"])


class RefCheckTest(ExtractFixture):

    def test_the_filled_fixture_passes(self):
        counts = self.check(allow_unfilled=False)
        self.assertEqual(counts["violations"], [])
        self.assertEqual(counts["ref_checks_skipped"], [])
        self.assertEqual(counts["cookable_without_code"], 1)       # the cricket: allowed, counted

    def test_a_dangling_iodine_key(self):
        self.edit("meat-fish-egg-dairy", "Base.Egg", iodine_ref="iodine:egg-boiled")
        self.assert_violation(self.check(), "iodine_ref 'iodine:egg-boiled'")

    def test_an_iodine_ref_without_its_prefix(self):
        self.edit("meat-fish-egg-dairy", "Base.Egg", iodine_ref="egg-whole-raw")
        self.assert_violation(self.check(), "iodine_ref 'egg-whole-raw'")

    def test_a_dangling_phytate_family(self):
        self.edit("grains-legumes", "Base.Lentils", phytate_source="schlemmer2009:beans")
        self.assert_violation(self.check(), "phytate_source 'schlemmer2009:beans'")

    def test_the_zero_families_are_closed(self):
        self.assertEqual(fn.ZERO_PHYTATE_FAMILIES,
                         ("dairy", "egg", "fish", "fruit", "meat", "oil", "sugar", "vegetable"))
        self.edit("produce", "Base.Apple", phytate_source="zero:grain")
        self.assert_violation(self.check(), "phytate_source 'zero:grain'")
        self.edit("produce", "Base.Apple", phytate_source="gupta2015:apple")
        self.assert_violation(self.check(), "phytate_source 'gupta2015:apple'")

    def test_a_dangling_literature_key(self):
        self.edit("meat-fish-egg-dairy", "Base.Cricket", fdc_id="rumpold2013:mantodea")
        self.assert_violation(self.check(), "literature fdc_id 'rumpold2013:mantodea'")

    def test_an_sr_legacy_id_absent_from_food_csv(self):
        self.edit("meat-fish-egg-dairy", "Base.Egg", fdc_id="174158")
        self.assert_violation(self.check(), "sr_legacy fdc_id 174158 is not in food.csv")

    def test_an_sr_legacy_description_not_verbatim(self):
        self.edit("produce", "Base.Apple", fdc_description="Apples, raw, with skin")
        got = [v for v in self.check()["violations"] if "fdc_description" in v]
        self.assertEqual(len(got), 1, got)
        self.assertIn("Base.Apple: fdc_description 'Apples, raw, with skin' is not food.csv's", got[0])

    def test_a_retention_code_absent_from_the_csv(self):
        self.edit("meat-fish-egg-dairy", "Base.Egg", cook_retention_code="77")
        self.assert_violation(self.check(), "cook_retention_code 77 is not in")
        self.edit("meat-fish-egg-dairy", "Base.Egg", cook_retention_code="5005")   # a defective code exists
        self.assertEqual(self.check()["violations"], [])

    def test_absent_fdc_files_skip_their_checks(self):
        absent = os.path.join(self.tmp, "absent")
        with mock.patch.dict(fn.REF_SOURCES, {"sr_legacy": absent, "retention": absent}):
            self.edit("meat-fish-egg-dairy", "Base.Egg", fdc_id="174158", cook_retention_code="77")
            counts = self.check()
        self.assertEqual(counts["ref_checks_skipped"], ["retention", "sr_legacy"])
        self.assertEqual(counts["violations"], [])

    def test_the_checks_are_registered(self):
        for check in (fn.check_iodine_refs, fn.check_phytate_sources, fn.check_literature_ids,
                      fn.check_sr_legacy_ids, fn.check_retention_codes, fn.check_sr_legacy_descriptions):
            self.assertIn(check, fn.MAP_REF_CHECKS)


class ExtractTest(ExtractFixture):

    def test_the_shape(self):
        got = self.build()
        self.assertEqual(sorted(got), ["foods", "insects", "iodine", "meta", "phytate", "retention"])
        self.assertEqual(sorted(got["foods"]), [str(EGG), str(APPLE)])
        egg = got["foods"][str(EGG)]
        self.assertEqual((egg["description"], egg["data_type"], egg["food_category"]),
                         ("Egg, whole, raw, fresh", "sr_legacy_food", "Dairy and Egg Products"))
        self.assertEqual(egg["nutrients"]["calories"], {"amount": 143.0, "unit": "KCAL", "nutrient_id": 1008})
        self.assertEqual(egg["nutrients"]["folate"], {"amount": 47.0, "unit": "UG", "nutrient_id": 1190})
        self.assertNotIn("phytate", egg["nutrients"])
        self.assertEqual(set(egg["nutrients"]), set(fn.KEYS) - {"phytate"})
        self.assertEqual([p["modifier"] for p in egg["portions"]], ["large", "extra large", "medium"])
        self.assertEqual(egg["portions"][0], {"seq_num": 1, "amount": 1.0, "measure_unit": "undetermined",
                                              "modifier": "large", "gram_weight": 50.0})

    def test_a_summed_key_is_exact_decimal(self):
        got = self.build()
        # 1.555 + 0.048 in binary floats is 1.6030000000000002; the extract writes the decimal sum
        self.assertEqual(got["foods"][str(EGG)]["nutrients"]["efa"],
                         {"amount": 1.603, "unit": "G", "nutrient_id": [1269, 1270]})
        self.assertEqual(got["foods"][str(APPLE)]["nutrients"]["efa"]["amount"], 0.052)
        with open(self.out, encoding="utf-8") as handle:
            self.assertIn('"amount": 1.603,', handle.read())

    def test_the_amounts_equal_the_join_core(self):
        with zipfile.ZipFile(self.zip) as archive:
            cells = fn.load_food_nutrient_cells(archive, [APPLE, EGG])
            core = fn.load_food_nutrients(archive, [APPLE, EGG])
        for fid in (APPLE, EGG):
            for key in set(fn.KEYS) - {"phytate"}:
                self.assertAlmostEqual(cells[fid][key]["amount"] or 0.0, core[fid][key] or 0.0, places=12)
                self.assertEqual(cells[fid][key]["amount"] is None, core[fid][key] is None, key)

    def test_the_null_rule(self):
        got = self.build()
        apple, egg = got["foods"][str(APPLE)]["nutrients"], got["foods"][str(EGG)]["nutrients"]
        self.assertIsNone(apple["iodine"]["amount"])                   # no row: null, never 0
        self.assertEqual(apple["iodine"]["unit"], "UG")
        self.assertEqual(apple["ethanol"]["amount"], 0.0)              # a 0 row: 0.0, never null
        self.assertEqual(egg["fibre"]["amount"], 0.0)
        self.assertEqual(apple["vitC"], {"amount": None, "unit": None, "nutrient_id": None})  # not in nutrient.csv
        missing = got["meta"]["counts"]["missing_nutrients"]
        self.assertEqual(set(missing), set(fn.KEYS) - {"phytate"})
        self.assertEqual(missing["iodine"], [EGG, APPLE])          # by numeric id
        self.assertEqual(missing["proteins"], [APPLE])
        self.assertEqual(missing["ethanol"], [])
        with open(self.out, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn('"amount": null', text)

    def test_only_the_cited(self):
        got = self.build()
        self.assertEqual(got["retention"], {"1": {"description": "CHEESE,BAKED", "factors": {"301": 100}}})
        self.assertEqual(got["iodine"], {"egg-whole-raw": {"food": "Egg, whole, raw, fresh",
                                                           "iodine_ug_100g": 49.0, "page": 1}})
        self.assertEqual(got["phytate"], {"lentils": {"phytate_mg_100g": 890.0, "source": "a citation",
                                                     "basis": "dry"}})
        self.assertEqual(list(got["insects"]), ["rumpold2013:orthoptera"])
        cricket = got["insects"]["rumpold2013:orthoptera"]
        self.assertEqual((cricket["protein_g_100g"], cricket["moisture_pct"], cricket["basis"]), (61.32, None, "dm"))
        self.assertNotIn("key", cricket)

    def test_the_meta(self):
        meta = self.build()["meta"]
        self.assertEqual((meta["build"], meta["jar_hash"], meta["tool"]),
                         ("42.21.0", "4a0e9546ec", "tools/food_nutrients.py"))  # 42.21.0 (2026-10-08 scan); 42.20.4 read 42.20.4, b0bbce05d5
        self.assertEqual(meta["generated"], datetime.datetime.now(datetime.timezone.utc).date().isoformat())
        self.assertEqual([s["name"] for s in meta["sources"]], [s["name"] for s in fn.fdc_fetch.sources()])
        sr = meta["sources"][0]
        self.assertEqual((sr["sha256"], sr["bytes"]), (_sha256(self.zip), os.path.getsize(self.zip)))
        self.assertEqual(sr["licence"], "CC0-1.0")
        counts = meta["counts"]
        self.assertEqual({k: v for k, v in counts.items() if k != "missing_nutrients"},
                         {"foods": 2, "retention_codes": 1, "defective_retention_rows": 1, "iodine_rows": 1,
                          "phytate_rows": 1, "insect_rows": 1, "cookable_without_code": 1})
        self.assertEqual(meta["defective_retention"],
                         {"5005": {"description": "ALC BEV,STIRRED,BKD/SIMMRD 30 MIN",
                                   "loadable_factors": {"221": 35},
                                   "skipped": [{"line": 3, "nutr_no": 301, "retn_factor": "Sep-75"}]}})

    def test_byte_stable_lf_and_sorted(self):
        self.build()
        with open(self.out, "rb") as handle:
            first = handle.read()
        self.build()
        with open(self.out, "rb") as handle:
            second = handle.read()
        self.assertEqual(first, second)
        self.assertNotIn(b"\r", first)
        self.assertTrue(first.endswith(b"}\n"))
        text = first.decode("utf-8")
        self.assertEqual(text, json.dumps(json.loads(text), indent=1, sort_keys=True, ensure_ascii=False) + "\n")

    def test_refuses_an_unfilled_mapping(self):
        self.edit("no-nutrition", "Base.Glue", no_nutrition_reason="")
        with self.assertRaises(fn.ExtractRefused) as caught:
            self.build()
        self.assertIn("unfilled", str(caught.exception))
        self.assertFalse(os.path.exists(self.out))

    def test_refuses_a_dangling_reference(self):
        self.edit("meat-fish-egg-dairy", "Base.Egg", iodine_ref="iodine:egg-boiled")
        with self.assertRaises(fn.ExtractRefused):
            self.build()
        self.assertFalse(os.path.exists(self.out))

    def test_refuses_without_the_fdc_files(self):
        with mock.patch.dict(fn.REF_SOURCES, {"retention": os.path.join(self.tmp, "absent")}):
            with self.assertRaises(fn.ExtractRefused) as caught:
                self.build()
        self.assertIn("retention", str(caught.exception))

    def test_refuses_a_file_the_manifest_does_not_hash(self):
        self.write_manifest(**{os.path.basename(self.zip): {"sha256": "f" * 64}})
        with self.assertRaises(fn.ExtractRefused) as caught:
            self.build()
        self.assertIn("sha256", str(caught.exception))

    def test_the_cli(self):
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            code = fn.main(["--build-extract", "--map-dir", self.map, "--dataset", self.dataset,
                            "--extract", self.out])
        self.assertEqual(code, 0)
        self.assertIn("2 foods", buf.getvalue())
        self.assertTrue(os.path.exists(self.out))


@unittest.skipUnless(os.path.exists(fn.EXTRACT_JSON), "data/fdc-extract.json is not built")
class RealExtractTest(unittest.TestCase):
    """The committed extract holds everything the committed mapping cites, and nothing more."""

    @classmethod
    def setUpClass(cls):
        with open(fn.EXTRACT_JSON, encoding="utf-8") as handle:
            cls.extract = json.load(handle)
        cls.rows, _errors = fn.read_map()

    def test_the_cited_ids_codes_and_keys(self):
        rows = self.rows
        self.assertEqual(set(self.extract["foods"]),
                         {r["fdc_id"] for r in rows if r["fdc_source"] == "sr_legacy"})
        self.assertEqual(set(self.extract["retention"]), {r["cook_retention_code"] for r in rows if r["cook_retention_code"]})
        self.assertEqual(set(self.extract["iodine"]), {r["iodine_ref"][len("iodine:"):] for r in rows if r["iodine_ref"]})
        self.assertEqual(set(self.extract["phytate"]),
                         {r["phytate_source"].split(":", 1)[1] for r in rows
                          if r["phytate_source"].startswith(("schlemmer2009:", "phyfoodcomp2019:"))})
        self.assertEqual(set(self.extract["insects"]), {r["fdc_id"] for r in rows if r["fdc_source"] == "literature"})

    def test_the_counts(self):
        meta = self.extract["meta"]
        counts = meta["counts"]
        self.assertEqual(counts["foods"], len(self.extract["foods"]))
        self.assertEqual(counts["retention_codes"], len(self.extract["retention"]))
        self.assertEqual(counts["defective_retention_rows"], 24)
        self.assertEqual(meta["defective_retention"]["5005"]["loadable_factors"], {"221": 35, "421": 100})
        self.assertEqual(len(meta["sources"]), 4)
        self.assertTrue(all(len(s["sha256"]) == 64 for s in meta["sources"]))
        for key, ids in counts["missing_nutrients"].items():
            for fid in ids:
                self.assertIsNone(self.extract["foods"][str(fid)]["nutrients"][key]["amount"])


# ---- build ----

def _fluid(pz_id, macros=(None, None, None, None), alcohol=None, hunger=None, thirst=None):
    cal, carb, lip, pro = macros
    props = {} if alcohol is None else {"alcohol": alcohol}
    return {"id": pz_id, "kind": "fluid", "display_name": pz_id, "calories": cal, "carbohydrates": carb,
            "lipids": lip, "proteins": pro, "hunger_change": hunger, "thirst_change": thirst,
            "properties_raw": props}


BUILD_DATA = {"meta": {"build": "42.20.4", "generated": "2026-09-10"},
              "items": EXTRACT_DATA["items"],
              "fluids": [_fluid("Beer", (500.0, 36.0, 0.0, 4.0), alcohol="0.05", hunger=-10.0, thirst=-20.0),
                         _fluid("SimpleSyrup", (0.0, 0.0, 0.0, 0.0), thirst=-30.0),
                         _fluid("Water", thirst=-50.0)]}

# the record keys every output record carries (the per-basis block apart)
RECORD_KEYS = {"pz_id", "kind", "basis", "family", "fdc_id", "fdc_source", "fdc_description", "confidence",
               "state_baseline", "cook_retention_code", "portion_grams", "portion_source", "iodine_ref",
               "phytate_source", "no_nutrition_reason", "notes", "per_100g", "vanilla", "checks"}
CHECK_KEYS = {"atwater_ratio", "atwater_outlier", "energy_vs_fdc_ratio", "proximate_sum", "fibre_le_carb",
              "retention_le_100", "out_of_range", "notes"}


def _overridden(rec, record):
    """The per-basis keys the build sets apart from per_100g x portion / 100 (the fluid overrides: the
    ethanol and, following it at 7 kcal/g, the energy of an alcoholic fluid; SimpleSyrup's water)."""
    keys = set()
    if rec["basis"] == "per_litre":
        if (record.get("properties_raw") or {}).get("alcohol") not in (None, ""):
            keys.update(("ethanol", "calories"))
        if rec["pz_id"] in fn.FLUID_LITRE_GRAMS:
            keys.add("water")
    return keys


class OutputShape(object):
    """The assertions a built output must pass, run on the fixture's and on the committed file."""

    def assert_shape(self, result, records):
        every = result["items"] + result["fluids"]
        self.assertEqual([r["pz_id"] for r in result["items"]], sorted(r["pz_id"] for r in result["items"]))
        self.assertEqual([r["pz_id"] for r in result["fluids"]], sorted(r["pz_id"] for r in result["fluids"]))
        self.assertEqual(sorted(r["pz_id"] for r in every), sorted(records))          # every id, once
        for rec in every:
            block = {"per_item": "per_item", "per_litre": "per_litre", "none": None}[rec["basis"]]
            want = RECORD_KEYS | ({block} if block else set())
            self.assertEqual(set(rec), want, rec["pz_id"])
            self.assertEqual(set(rec["per_100g"]), set(fn.KEYS), rec["pz_id"])
            self.assertEqual(set(rec["checks"]), CHECK_KEYS, rec["pz_id"])
            self.assertEqual(set(rec["vanilla"]), {"calories", "carbohydrates", "lipids", "proteins",
                                                   "hunger", "thirst"})
            # the basis is never mixed: a fluid is per litre, an item per item, a none record neither
            if rec["basis"] == "none":
                self.assertIsNone(rec["fdc_id"])
                self.assertIsNotNone(rec["no_nutrition_reason"])
                self.assertTrue(all(v is None for v in rec["per_100g"].values()))
            else:
                self.assertEqual(rec["basis"], "per_litre" if rec["kind"] == "fluid" else "per_item")
                self.assertNotIn("per_item" if rec["basis"] == "per_litre" else "per_litre", rec)
                self.assertEqual(set(rec[block]), set(fn.KEYS))
                for k in fn.KEYS:      # null is never 0: a null per 100 g stays null per item
                    if rec["per_100g"][k] is None and k not in _overridden(rec, records[rec["pz_id"]]):
                        self.assertIsNone(rec[block][k], (rec["pz_id"], k))
            for cell in ("fdc_id", "fdc_source", "confidence", "notes", "iodine_ref"):
                self.assertNotEqual(rec[cell], "", (rec["pz_id"], cell))      # empty is null
        self.assertTrue(all(r["kind"] == "fluid" for r in result["fluids"]))
        self.assertTrue(all(r["kind"] != "fluid" for r in result["items"]))

    def assert_round_trip(self, result, records):
        for rec in result["items"] + result["fluids"]:
            if rec["basis"] == "none":
                continue
            block, grams = rec[rec["basis"]], rec["portion_grams"]
            for k in set(fn.KEYS) - _overridden(rec, records[rec["pz_id"]]):
                if rec["per_100g"][k] is not None:
                    self.assertAlmostEqual(block[k], rec["per_100g"][k] * grams / 100.0, delta=1e-6,
                                           msg=(rec["pz_id"], k))

    def assert_counts(self, meta, result, records):
        counts = meta["counts"]
        every = result["items"] + result["fluids"]
        self.assertEqual(counts["unmapped"], [])
        self.assertEqual(counts["orphan_mappings"], [])
        self.assertEqual(counts["items"], len(result["items"]))
        self.assertEqual(counts["fluids"], len(result["fluids"]))
        self.assertEqual(counts["mapped"] + counts["no_nutrition"], len(every))
        self.assertEqual(counts["guesses"], sorted(r["pz_id"] for r in every if r["confidence"] == "guess"))
        self.assertLessEqual(len(counts["guesses"]), fn.GUESS_BUDGET)
        self.assertEqual(sum(counts["rebase_factor_bands"].values()), counts["mapped"])
        self.assertEqual(set(counts["out_of_range"]), set(fn.KEYS))
        self.assertEqual(counts["atwater_outliers"], len(counts["atwater_outlier_ids"]))
        self.assertEqual(sum(counts["by_confidence"].values()), counts["mapped"])


class BuildFixture(ExtractFixture):
    """ExtractFixture with three fluids and every mapped row's portion; the extract is built from the
    fixture zip, then the FDC paths are pointed at nothing, so every build here runs without the zips."""

    DATA = BUILD_DATA

    def setUp(self):
        super().setUp()
        self.edit("grains-legumes", "Base.Lentils", fdc_id=str(EGG), fdc_description="Egg, whole, raw, fresh",
                  portion_grams="100",
                  portion_source="judgement", state_baseline="dried")
        self.edit("meat-fish-egg-dairy", "Base.Egg", portion_grams="50", portion_source="fdc_portion:1",
                  state_baseline="raw")
        self.prepare()
        self.edit("meat-fish-egg-dairy", "Base.Cricket", portion_grams="15.6", portion_source="judgement",
                  state_baseline="raw")
        self.edit("fluids", "Beer", fdc_id=str(APPLE), fdc_source="sr_legacy", confidence="close",
                  fdc_description=APPLE_DESCRIPTION,
                  portion_grams="1010", portion_source="judgement", state_baseline="prepared")
        self.edit("fluids", "SimpleSyrup", fdc_id=str(APPLE), fdc_source="sr_legacy", confidence="proxy",
                  fdc_description=APPLE_DESCRIPTION,
                  portion_grams="615", portion_source="judgement", state_baseline="prepared",
                  notes="a synthetic stand-in for the sugar entry")
        self.edit("fluids", "Water", no_nutrition_reason="not_food")
        fn.build_extract(self.map, self.dataset, self.out, out=io.StringIO())
        empty = os.path.join(self.tmp, "empty-fdc")     # tools/.fdc/ as a fresh clone has it: empty
        os.makedirs(empty)
        patcher = mock.patch.dict(fn.REF_SOURCES, {
            name: os.path.join(empty, os.path.basename(fn.REF_SOURCES[name]))
            for name in ("sr_legacy", "retention", "manifest")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.json_out = os.path.join(self.tmp, "food-nutrients.json")
        self.csv_out = os.path.join(self.tmp, "food-nutrients.csv")
        self.records = fn.load_dataset(self.dataset)

    def prepare(self):
        """A hook for a subclass's own row edits, run before the extract is built."""

    def run_build(self):
        return fn.build(self.map, self.dataset, self.out, self.json_out, self.csv_out, out=io.StringIO())

    def rec(self, result, pz_id):
        return [r for r in result["items"] + result["fluids"] if r["pz_id"] == pz_id][0]


class PhytateBasisTest(BuildFixture):
    """The phytate step's branches: a fresh family taken as eaten, a dry one converted by the entry's
    water, and a fresh-prefixed family whose table row lacks the basis=fresh marker refused."""

    def prepare(self):
        self.edit("produce", "Base.Apple", phytate_mg_100g="214.32", phytate_source="phyfoodcomp2019:flour")

    def test_a_fresh_row_is_taken_as_eaten(self):
        result = self.run_build()
        apple = self.rec(result, "Base.Apple")
        self.assertEqual(apple["per_100g"]["phytate"], 214.32)         # no water conversion
        self.assertFalse([n for n in apple["checks"]["notes"] if n.startswith("phytate:")])

    def test_a_dry_row_is_converted(self):
        lentils = self.rec(self.run_build(), "Base.Lentils")
        self.assertAlmostEqual(lentils["per_100g"]["phytate"], 890 * (100 - lentils["per_100g"]["water"]) / 100,
                               places=6)

    def test_the_extract_carries_the_basis(self):
        with open(self.out, encoding="utf-8") as handle:
            phytate = json.load(handle)["phytate"]
        self.assertEqual((phytate["flour"]["basis"], phytate["lentils"]["basis"]), ("fresh", "dry"))

    def test_a_fresh_row_without_the_marker_raises(self):
        with open(self.out, encoding="utf-8") as handle:
            extract = json.load(handle)
        extract["phytate"]["flour"]["basis"] = "dry"
        row = {"pz_id": "Base.Apple", "iodine_ref": "", "phytate_source": "phyfoodcomp2019:flour",
               "phytate_mg_100g": "214.32"}
        with self.assertRaises(fn.ExtractRefused):
            fn.sr_per_100g(extract["foods"][str(APPLE)], row, extract, [])

    def test_the_checker_pairs_each_prefix_with_its_basis(self):
        for source in ("schlemmer2009:flour", "phyfoodcomp2019:lentils"):
            self.edit("produce", "Base.Apple", phytate_source=source)
            counts = fn.check_map(self.map, self.dataset, allow_unfilled=False, out=io.StringIO())
            self.assert_violation(counts, "phytate_source %r" % source)


class BuildTest(BuildFixture, OutputShape):

    def test_the_schema_and_the_basis(self):
        result = self.run_build()
        self.assertEqual(sorted(result), ["fluids", "items", "meta"])
        self.assert_shape(result, self.records)
        self.assertEqual([r["pz_id"] for r in result["fluids"]], ["Beer", "SimpleSyrup", "Water"])
        self.assertEqual(self.rec(result, "Water")["basis"], "none")
        self.assertEqual(self.rec(result, "Base.Glue")["basis"], "none")

    def test_the_units_round_trip(self):
        result = self.run_build()
        self.assert_round_trip(result, self.records)
        egg = self.rec(result, "Base.Egg")
        self.assertEqual(egg["per_item"]["calories"], 71.5)              # 143 kcal/100 g x 50 g
        self.assertEqual(egg["per_item"]["efa"], 0.8015)                 # the decimal sum 1.603, halved
        self.assertEqual(egg["portion_grams"], 50.0)
        self.assertEqual(egg["cook_retention_code"], 1)

    def test_the_null_rule(self):
        apple = self.rec(self.run_build(), "Base.Apple")
        self.assertIsNone(apple["per_100g"]["vitC"])          # no nutrient row: null, never 0
        self.assertIsNone(apple["per_item"]["vitC"])
        self.assertIsNone(apple["per_100g"]["iodine"])        # no iodine_ref: null
        self.assertEqual(apple["per_100g"]["ethanol"], 0.0)   # a measured 0 stays 0.0
        self.assertEqual(apple["per_item"]["ethanol"], 0.0)
        self.assertEqual(apple["vanilla"]["hunger"], None)

    def test_iodine_and_phytate(self):
        result = self.run_build()
        egg, lentils, apple = (self.rec(result, i) for i in ("Base.Egg", "Base.Lentils", "Base.Apple"))
        self.assertEqual(egg["per_100g"]["iodine"], 49.0)
        self.assertEqual(egg["per_item"]["iodine"], 24.5)
        self.assertEqual(apple["per_100g"]["phytate"], 0.0)                     # zero:fruit
        # 890 mg/100 g dry x (100 - 76.15 g water) / 100, the as-eaten conversion
        self.assertAlmostEqual(lentils["per_100g"]["phytate"], 890 * (100 - 76.15) / 100, places=6)
        self.assertTrue(any(n.startswith("phytate:") for n in lentils["checks"]["notes"]))  # cell 890 differs

    def test_phytate_without_water_is_null_with_a_note(self):
        self.edit("grains-legumes", "Base.Lentils", fdc_id=str(APPLE))   # the apple fixture has no water row
        lentils = self.rec(self.run_build(), "Base.Lentils")
        self.assertIsNone(lentils["per_100g"]["phytate"])
        self.assertIn("carries no water", " ".join(lentils["checks"]["notes"]))

    def test_the_literature_row(self):
        cricket = self.rec(self.run_build(), "Base.Cricket")
        p = cricket["per_100g"]
        self.assertAlmostEqual(p["proteins"], 61.32 * 0.3, places=6)
        self.assertAlmostEqual(p["lipids"], 13.41 * 0.3, places=6)
        self.assertAlmostEqual(p["fibre"], 9.55 * 0.3, places=6)
        self.assertAlmostEqual(p["carbs"], (12.98 + 9.55) * 0.3, places=6)     # NFE + fibre
        self.assertAlmostEqual(p["calories"], 426.25 * 0.3, places=6)
        self.assertAlmostEqual(p["water"], 70.0, places=6)
        self.assertIsNone(p["iron"])
        self.assertAlmostEqual(cricket["per_item"]["calories"], 426.25 * 0.3 * 0.156, places=6)
        self.assertEqual(cricket["fdc_source"], "literature")

    def test_the_fluid_overrides(self):
        result = self.run_build()
        beer, syrup = self.rec(result, "Beer"), self.rec(result, "SimpleSyrup")
        self.assertEqual(beer["per_100g"]["ethanol"], 0.0)                   # per_100g stays the entry's
        self.assertEqual(beer["per_litre"]["ethanol"], 39.45)                # 0.05 x 789, the property
        self.assertIn("alcohol property 0.05", " ".join(beer["checks"]["notes"]))
        self.assertEqual(syrup["per_litre"]["water"], 615.0)                 # 1230 - 615
        self.assertIn("the litre's 1230.0 g", " ".join(syrup["checks"]["notes"]))
        self.assertIsNone(syrup["checks"]["energy_vs_fdc_ratio"])            # vanilla 0 kcal
        self.assertNotIn("ethanol", " ".join(syrup["checks"]["notes"]))     # no alcohol property
        # ruling T6-1: the energy follows the game's ethanol, 7 kcal/g x (0 g FDC - 39.45 g property)
        self.assertAlmostEqual(beer["per_litre"]["calories"], 52 * 10.1 + 7 * 39.45, places=6)
        self.assertEqual(beer["per_100g"]["calories"], 52.0)                 # per_100g stays the entry's
        self.assertIn("calories: per_litre", " ".join(beer["checks"]["notes"]))
        self.assertNotIn("calories:", " ".join(syrup["checks"]["notes"]))
        self.assertAlmostEqual(beer["checks"]["energy_vs_fdc_ratio"], (52 * 10.1 + 7 * 39.45) / 500.0, places=4)

    def test_the_checks_on_the_fixture(self):
        result = self.run_build()
        egg, apple = self.rec(result, "Base.Egg"), self.rec(result, "Base.Apple")
        self.assertEqual(egg["checks"]["retention_le_100"], True)           # code 1: Ca 100
        self.assertIsNone(apple["checks"]["retention_le_100"])               # no code cited
        self.assertAlmostEqual(egg["checks"]["atwater_ratio"], round((4 * 0.72 + 4 * 12.56 + 9 * 9.51) / 143, 4))
        self.assertIs(egg["checks"]["atwater_outlier"], False)
        self.assertIsNone(apple["checks"]["proximate_sum"])                  # no water, no protein
        self.assertEqual(egg["checks"]["fibre_le_carb"], True)
        self.assertEqual(egg["checks"]["out_of_range"], [])

    def test_the_meta(self):
        result = self.run_build()
        meta = result["meta"]
        self.assertEqual((meta["build"], meta["jar_hash"], meta["tool"]),
                         ("42.21.0", "4a0e9546ec", "tools/food_nutrients.py"))  # 42.21.0 (2026-10-08 scan); 42.20.4 read 42.20.4, b0bbce05d5
        self.assertEqual(meta["generated"], datetime.datetime.now(datetime.timezone.utc).date().isoformat())
        with open(self.out, encoding="utf-8") as handle:
            extract = json.load(handle)
        self.assertEqual(meta["sources"], extract["meta"]["sources"])
        inputs = meta["inputs"]
        self.assertEqual(inputs["mapping"]["rows"], 8)
        self.assertEqual(sum(inputs["mapping"]["parts"].values()), 8)
        self.assertEqual(inputs["extract"]["generated"], extract["meta"]["generated"])
        self.assertEqual(inputs["extract"]["counts"]["foods"], 2)
        self.assertEqual(inputs["side_tables"]["iodine"]["rows"], 2)
        self.assertEqual(inputs["dataset"]["generated"], "2026-09-10")
        self.assert_counts(meta, result, self.records)
        c = meta["counts"]
        self.assertEqual((c["items"], c["fluids"], c["mapped"], c["no_nutrition"]), (5, 3, 6, 2))
        self.assertEqual(c["by_confidence"], {"close": 1, "exact": 2, "guess": 1, "proxy": 2})
        self.assertEqual(c["by_portion_source"], {"fdc_portion": 1, "judgement": 4, "vanilla_implied": 1})
        self.assertEqual(c["by_reason"], {"not_food": 2})
        self.assertEqual(c["guesses"], ["Base.Cricket"])
        self.assertEqual(c["cook_retention_set"], 1)
        self.assertEqual(c["cookable_without_code"], 1)
        self.assertEqual(c["rebase_factor_bands"]["none"], 1)                # SimpleSyrup, vanilla 0 kcal

    def test_byte_stable_lf_sorted_and_the_csv_twin(self):
        self.run_build()
        first = [open(p, "rb").read() for p in (self.json_out, self.csv_out)]
        self.run_build()
        second = [open(p, "rb").read() for p in (self.json_out, self.csv_out)]
        self.assertEqual(first, second)
        for blob in first:
            self.assertNotIn(b"\r", blob)
        text = first[0].decode("utf-8")
        self.assertEqual(text, json.dumps(json.loads(text), indent=1, sort_keys=True, ensure_ascii=False) + "\n")

    def test_the_csv_twin(self):
        result = self.run_build()
        with open(self.csv_out, encoding="utf-8", newline="") as handle:
            lines = handle.read().split("\n")
        self.assertEqual(lines[0], ",".join(fn.CSV_COLUMNS))                  # the header is line 1: no stamp
        with open(self.csv_out, encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        every = result["items"] + result["fluids"]
        self.assertEqual([r["pz_id"] for r in rows], [r["pz_id"] for r in every])
        self.assertEqual(len(fn.CSV_COLUMNS), len(set(fn.CSV_COLUMNS)))
        for key in fn.KEYS:
            self.assertIn(key, fn.CSV_COLUMNS)
            self.assertIn("p100_" + key, fn.CSV_COLUMNS)
        by = {r["pz_id"]: r for r in rows}
        self.assertEqual(by["Beer"]["basis"], "per_litre")
        self.assertEqual(by["Beer"]["ethanol"], "39.45")                     # the per-litre value
        self.assertEqual(by["Beer"]["p100_ethanol"], "0.0")
        self.assertEqual(by["Base.Apple"]["vitC"], "")                        # null -> empty, never 0
        self.assertEqual(by["Base.Glue"]["calories"], "")
        self.assertEqual(by["Base.Egg"]["fibre_le_carb"], "true")
        self.assertEqual(by["Base.Egg"]["cook_retention_code"], "1")

    def test_runs_without_the_zips(self):
        for name in ("sr_legacy", "retention", "manifest"):
            self.assertFalse(os.path.exists(fn.REF_SOURCES[name]))
        self.assertEqual(os.listdir(os.path.dirname(fn.REF_SOURCES["sr_legacy"])), [])
        with mock.patch.object(fn.zipfile, "ZipFile", side_effect=AssertionError("the build opened a zip")):
            result = self.run_build()
        self.assertEqual(result["meta"]["counts"]["mapped"], 6)

    def assert_refused(self, needle):
        with self.assertRaises(fn.BuildRefused) as caught:
            self.run_build()
        self.assertIn(needle, str(caught.exception))
        self.assertFalse(os.path.exists(self.json_out))
        self.assertFalse(os.path.exists(self.csv_out))

    def test_refuses_an_unfilled_mapping(self):
        self.edit("fluids", "Water", no_nutrition_reason="")
        self.assert_refused("unfilled")

    def test_refuses_over_the_guess_budget(self):
        with mock.patch.object(fn, "GUESS_BUDGET", 0):
            self.assert_refused("guess budget")

    def test_refuses_a_guess_or_a_proxy_without_notes(self):
        self.edit("fluids", "SimpleSyrup", notes="")
        self.assert_refused("a proxy without notes")
        self.edit("fluids", "SimpleSyrup", notes="back")
        self.edit("meat-fish-egg-dairy", "Base.Cricket", notes="")
        self.assert_refused("a guess without notes")

    def test_refuses_a_mapped_row_without_portion(self):
        self.edit("meat-fish-egg-dairy", "Base.Egg", portion_grams="")
        self.assert_refused("without portion_grams")

    def test_refuses_a_stale_extract(self):
        self.edit("meat-fish-egg-dairy", "Base.Egg", iodine_ref="iodine:milk-whole")   # a table row, not extracted
        self.assert_refused("re-run --build-extract")

    def test_the_cli(self):
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            code = fn.main(["--build", "--map-dir", self.map, "--dataset", self.dataset, "--extract", self.out,
                            "--out-json", self.json_out, "--out-csv", self.csv_out])
        self.assertEqual(code, 0)
        self.assertIn("5 items, 3 fluids, 6 mapped", buf.getvalue())
        self.edit("fluids", "Water", no_nutrition_reason="")
        err = io.StringIO()
        with mock.patch("sys.stdout", io.StringIO()), mock.patch("sys.stderr", err):
            code = fn.main(["--build", "--map-dir", self.map, "--dataset", self.dataset, "--extract", self.out,
                            "--out-json", self.json_out, "--out-csv", self.csv_out])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err.getvalue())


class RecordChecksTest(unittest.TestCase):
    """Each check on a synthetic violation: named, never clamped."""

    BASE = {"calories": 100.0, "carbs": 10.0, "fibre": 2.0, "proteins": 5.0, "lipids": 5.0, "water": 70.0}

    def vector(self, **cells):
        out = dict.fromkeys(fn.KEYS)
        out.update(self.BASE)
        out.update(cells)
        return out

    def test_a_clean_vector(self):
        got = fn.record_checks(self.vector(calories=4 * 8 + 2 * 2 + 4 * 5 + 9 * 5.0))
        self.assertEqual(got["out_of_range"], [])
        self.assertEqual(got["notes"], [])
        self.assertEqual((got["atwater_ratio"], got["atwater_outlier"]), (1.0, False))
        self.assertEqual(got["proximate_sum"], 90.0)
        self.assertIs(got["fibre_le_carb"], True)
        self.assertIsNone(got["retention_le_100"])

    def test_a_range_violation_is_named_not_clamped(self):
        vec = self.vector(sodium=50000.0, proteins=-1.0)
        got = fn.record_checks(vec)
        self.assertEqual(got["out_of_range"], ["proteins", "sodium"])          # KEYS order
        self.assertEqual(vec["sodium"], 50000.0)
        self.assertIn("range: sodium 50000.0 mg/100 g outside 0.0-40000.0", got["notes"])

    def test_every_key_has_a_range(self):
        self.assertEqual(set(fn.SANITY_RANGES), set(fn.KEYS))
        self.assertTrue(all(low <= high for low, high in fn.SANITY_RANGES.values()))

    def test_the_known_good_extremes_pass(self):
        self.assertEqual(fn.record_checks(self.vector(sodium=38758.0, iodine=2500.0, lipids=100.0))["out_of_range"],
                         [])

    def test_atwater_bands(self):
        # 4(10 - 2) + 2*2 + 4*5 + 9*5 = 101 kcal from the macros
        self.assertIs(fn.record_checks(self.vector(calories=101.0 / 1.11))["atwater_outlier"], True)
        self.assertIs(fn.record_checks(self.vector(calories=101.0 / 1.09))["atwater_outlier"], False)
        no_fibre = self.vector(calories=105.0 / 1.2, fibre=None)    # fibre null: 4*10 + 20 + 45 = 105
        self.assertIs(fn.record_checks(no_fibre)["atwater_outlier"], False)
        no_fibre["calories"] = 105.0 / 1.3
        got = fn.record_checks(no_fibre)
        self.assertIs(got["atwater_outlier"], True)
        self.assertIn("+/-25 %", got["notes"][0])

    def test_atwater_below_the_floor_is_not_flagged(self):
        got = fn.record_checks(self.vector(calories=5.0, carbs=0.0, fibre=0.0, proteins=0.5, lipids=0.0))
        self.assertEqual(got["atwater_ratio"], 0.4)
        self.assertIs(got["atwater_outlier"], False)

    def test_atwater_counts_ethanol(self):
        vec = dict.fromkeys(fn.KEYS)
        vec.update(calories=231.0, carbs=0.0, proteins=0.0, lipids=0.0, ethanol=33.4, water=66.6)
        self.assertAlmostEqual(fn.record_checks(vec)["atwater_ratio"], round(7 * 33.4 / 231.0, 4))

    def test_the_proximate_sum(self):
        got = fn.record_checks(self.vector(water=95.0))
        self.assertEqual(got["proximate_sum"], 115.0)
        self.assertIn("proximate", got["notes"][-1])
        self.assertEqual(got["out_of_range"], [])
        self.assertIsNone(fn.record_checks(self.vector(water=None))["proximate_sum"])

    def test_fibre_over_carbs(self):
        got = fn.record_checks(self.vector(fibre=12.0))
        self.assertIs(got["fibre_le_carb"], False)
        self.assertIsNone(fn.record_checks(self.vector(fibre=None))["fibre_le_carb"])

    def test_retention_over_100(self):
        got = fn.record_checks(self.vector(), {"401": 120, "301": 100})
        self.assertIs(got["retention_le_100"], False)
        self.assertIn("retention: factor 120 % on nutrient 401 > 100", got["notes"])
        self.assertIs(fn.record_checks(self.vector(), {"301": 100})["retention_le_100"], True)

    def test_the_rebase_bands(self):
        self.assertEqual([fn.rebase_band(x) for x in (None, 0.1, 0.5, 0.94, 0.95, 1.0, 1.05, 1.3, 2.0, 9.0)],
                         ["none", "<0.5", "0.5-0.8", "0.8-0.95", "0.95-1.05", "0.95-1.05", "1.05-1.25",
                          "1.25-2.0", ">2.0", ">2.0"])


class LiteratureTest(unittest.TestCase):
    """The side-table conversions, against the mapping notes' own arithmetic."""

    def cells(self, key, **over):
        base = {"basis": "dm", "protein_g_100g": None, "fat_g_100g": None, "fibre_g_100g": None,
                "carb_g_100g": None, "ash_g_100g": None, "energy_kcal_100g": None, "moisture_pct": None,
                "_key": key}
        base.update(over)
        return base

    def test_a_measured_moisture_sets_the_fraction(self):
        # kavle2023:eisenia-andrei: 83.68 % moisture, fresh = DM x 0.1632 -> 78.92 kcal (the Worm note)
        got = fn.literature_per_100g(self.cells("kavle2023:eisenia-andrei", protein_g_100g=53.75,
                                                fat_g_100g=19.3, carb_g_100g=23.26, ash_g_100g=3.69,
                                                energy_kcal_100g=483.56, moisture_pct=83.68))
        self.assertAlmostEqual(got["calories"], 78.92, places=2)
        self.assertAlmostEqual(got["proteins"], 8.77, places=2)
        self.assertAlmostEqual(got["water"], 83.68, places=6)
        self.assertAlmostEqual(got["carbs"], 23.26 * 0.1632, places=6)        # the cell includes fibre
        self.assertIsNone(got["fibre"])

    def test_an_empty_energy_and_carb_by_difference(self):
        # oonincx2012:porcellio-scaber: NFE 0.59 after NDF; 270.66 kcal DM x 0.3218 = 87.10 (the Pillbug note)
        got = fn.literature_per_100g(self.cells("oonincx2012:porcellio-scaber", protein_g_100g=41.2,
                                                fat_g_100g=11.5, fibre_g_100g=14.02, ash_g_100g=32.69,
                                                moisture_pct=67.82))
        self.assertAlmostEqual(got["calories"], (4 * 41.2 + 9 * 11.5 + 4 * 0.59) * 0.3218, places=4)
        self.assertAlmostEqual(got["carbs"], (100 - 41.2 - 11.5 - 32.69) * 0.3218, places=6)

    def test_an_nfe_cell_adds_fibre_and_an_empty_energy_sums(self):
        # rumpold2013:blattodea: no energy; 4P + 9F + 4 NFE = 516.42 kcal DM (the Cockroach note)
        got = fn.literature_per_100g(self.cells("rumpold2013:blattodea", protein_g_100g=57.3, fat_g_100g=29.9,
                                                fibre_g_100g=5.31, carb_g_100g=4.53, ash_g_100g=2.94))
        self.assertAlmostEqual(got["calories"], 516.42 * 0.3, places=4)
        self.assertAlmostEqual(got["carbs"], (4.53 + 5.31) * 0.3, places=6)
        self.assertGreaterEqual(got["carbs"], got["fibre"])

    def test_a_fresh_basis_is_not_scaled(self):
        got = fn.literature_per_100g(self.cells("x:y", basis="fresh", protein_g_100g=20.0, fat_g_100g=5.0,
                                                carb_g_100g=1.0, energy_kcal_100g=129.0, moisture_pct=72.0))
        self.assertEqual((got["proteins"], got["calories"], got["water"]), (20.0, 129.0, 72.0))


@unittest.skipUnless(os.path.exists(fn.NUTRIENTS_JSON), "data/food-nutrients.json is not built")
class RealNutrientsTest(unittest.TestCase, OutputShape):
    """The committed output: every dataset id, the schema, the round trip, the guess budget."""

    @classmethod
    def setUpClass(cls):
        with open(fn.NUTRIENTS_JSON, encoding="utf-8") as handle:
            cls.result = json.load(handle)
        cls.records = fn.load_dataset()

    def test_the_schema_and_the_basis(self):
        self.assert_shape(self.result, self.records)

    def test_the_units_round_trip(self):
        self.assert_round_trip(self.result, self.records)

    def test_the_counts(self):
        self.assert_counts(self.result["meta"], self.result, self.records)
        counts = self.result["meta"]["counts"]
        self.assertEqual(counts["fluids"], 61)
        self.assertEqual(counts["items"] + counts["fluids"], len(self.records))

    def test_the_csv_twin(self):
        with open(fn.NUTRIENTS_CSV, encoding="utf-8", newline="") as handle:
            text = handle.read()
        self.assertNotIn("\r", text)
        self.assertEqual(text.split("\n")[0], ",".join(fn.CSV_COLUMNS))
        rows = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual([r["pz_id"] for r in rows],
                         [r["pz_id"] for r in self.result["items"] + self.result["fluids"]])


# ---- the emitters (Task 9) ----

import food_scan

SEED_COMMIT = "7a2e490"     # the last commit whose NR_Data_Nutrients.lua is the Plan 2 hand seed
SEED_PATH = "mod/NutritionRevamp/common/media/lua/shared/NR_Data_Nutrients.lua"
SCRIPT_KEYS = {"DisplayCategory", "Calories", "Carbohydrates", "Proteins", "Lipids"}


def _vector(**values):
    out = dict((k, 0.0) for k in fn.KEYS)
    out.update(values)
    return out


def _out_rec(pz_id, kind="food", fdc_id="171688", confidence="exact", block=None):
    basis = "none" if fdc_id is None else ("per_litre" if kind == "fluid" else "per_item")
    rec = {"pz_id": pz_id, "kind": kind, "basis": basis, "fdc_id": fdc_id,
           "confidence": None if fdc_id is None else confidence}
    if fdc_id is not None:
        rec[basis] = block
    return rec


def _synthetic():
    """Three mapped foods, one reasoned food, one reasoned drainable, two fluids (one reasoned)."""
    items = [
        _out_rec("Base.Apple", block=_vector(calories=94.588, carbs=25.12039, proteins=0.47294, lipids=0.30923,
                                             iodine=None, vitC=8.3674)),
        _out_rec("Base.Bleach", kind="drainable", fdc_id=None),
        _out_rec("Base.Lard", fdc_id="171401", confidence="close",
                 block=_vector(calories=902.0, carbs=None, proteins=0.0, lipids=100.0)),
        _out_rec("Base.Pebble", fdc_id=None),
        _out_rec("Base.Seeds", fdc_id="170562", confidence="proxy",
                 block=_vector(calories=5.0, carbs=1.234, proteins=0.1, lipids=1e-05)),
    ]
    fluids = [
        _out_rec("Cola", kind="fluid", fdc_id="174852", confidence="close",
                 block=_vector(calories=436.8, carbs=107.744, water=929.344, caffeine=93.6, iodine=None)),
        _out_rec("TaintedBleach", kind="fluid", fdc_id=None),
    ]
    meta = {"generated": "2026-10-06", "inputs": {"mapping": {"rows": 7}, "extract": {"counts": {"foods": 3}}},
            "sources": [{"name": "FoodData Central SR Legacy", "release": "2018-04", "licence": "CC0-1.0"},
                        {"name": "USDA/FDA/ODS-NIH Iodine Database", "release": "4.0 (2024-10)",
                         "licence": "public-domain-US"}]}
    return {"meta": meta, "items": items, "fluids": fluids}


SYNTHETIC_RECORDS = {
    "Base.Apple": {"module": "Base", "display_category": "Food"},
    "Base.Lard": {"module": "Base", "display_category": "Food"},
    "Base.Seeds": {"module": "Base", "display_category": "Gardening"},
}

SYNTHETIC_SCRIPT = (
    "/* GENERATED by tools/food_nutrients.py from data/food-nutrients.json; do not edit - regenerate with "
    "--write. Re-bases Calories, Carbohydrates, Proteins and Lipids on every mapped base:food record; "
    "HungerChange and ThirstChange untouched (spec section 4.6). */\n"
    "module Base\n"
    "{\n"
    "    item Apple\n"
    "    {\n"
    "        DisplayCategory = Food,\n"
    "        Calories = 94.59,\n"
    "        Carbohydrates = 25.12,\n"
    "        Proteins = 0.47,\n"
    "        Lipids = 0.31,\n"
    "    }\n"
    "\n"
    "    item Lard\n"
    "    {\n"
    "        DisplayCategory = Food,\n"
    "        Calories = 902.00,\n"
    "        Carbohydrates = 0.00,\n"
    "        Proteins = 0.00,\n"
    "        Lipids = 100.00,\n"
    "    }\n"
    "\n"
    "    item Seeds\n"
    "    {\n"
    "        DisplayCategory = Gardening,\n"
    "        Calories = 5.00,\n"
    "        Carbohydrates = 1.23,\n"
    "        Proteins = 0.10,\n"
    "        Lipids = 0.00,\n"
    "    }\n"
    "}\n"
)


def _seed_text():
    """The Plan 2 seed at SEED_COMMIT, or None where git or the commit is unavailable."""
    try:
        out = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (SEED_COMMIT, SEED_PATH)],
                             capture_output=True)
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout.decode("utf-8").replace("\r\n", "\n")


class LuaNumberTest(unittest.TestCase):

    def test_repr_round_trips_the_awkward_floats(self):
        for v in (0.1, 1e-05, 94.6, 94.588, 1.0, 1.0 / 3.0, 48167.8, 0.30923, 2.5e-07, 0.0):
            text = fn.lua_number(v)
            self.assertEqual(float(text), v, text)
        self.assertEqual(fn.lua_number(0.1), "0.1")
        self.assertEqual(fn.lua_number(1e-05), "1e-05")
        self.assertEqual(fn.lua_number(94.6), "94.6")

    def test_an_integer_valued_float_keeps_its_point_and_null_is_a_bare_zero(self):
        self.assertEqual(fn.lua_number(1), "1.0")
        self.assertEqual(fn.lua_number(902.0), "902.0")
        self.assertEqual(fn.lua_number(0.0), "0.0")
        self.assertEqual(fn.lua_number(None), "0")

    def test_a_negative_or_non_finite_value_is_refused(self):
        for bad in (-0.5, float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(fn.EmitRefused):
                fn.lua_number(bad)

    def test_lua_reads_the_repr_back_exactly(self):
        try:
            import lupa.lua51 as lua51
        except ImportError:
            self.skipTest("lupa is not installed")
        rt = lua51.LuaRuntime()
        for v in (0.1, 1e-05, 94.6, 94.588, 1.0 / 3.0, 48167.8, 2.5e-07):
            self.assertEqual(rt.eval(fn.lua_number(v)), v)


class EmitScriptsTest(unittest.TestCase):

    def test_the_exact_text_of_three_records(self):
        self.assertEqual(fn.emit_scripts(_synthetic(), SYNTHETIC_RECORDS), SYNTHETIC_SCRIPT)

    def test_only_mapped_food_records_have_blocks(self):
        self.assertEqual([r["pz_id"] for r in fn.script_records(_synthetic())],
                         ["Base.Apple", "Base.Lard", "Base.Seeds"])

    def test_the_parse_back(self):
        roots = food_scan.parse_script(fn.emit_scripts(_synthetic(), SYNTHETIC_RECORDS), "synthetic.txt")
        self.assertEqual([(b["kind"], b["name"]) for b in roots], [("module", "Base")])
        items = roots[0]["blocks"]
        self.assertEqual([b["name"] for b in items], ["Apple", "Lard", "Seeds"])
        for block in items:
            self.assertEqual(block["kind"], "item")
            self.assertEqual(set(block["props"]), SCRIPT_KEYS)
        self.assertEqual(items[1]["props"]["Lipids"], "100.00")

    def test_a_record_outside_module_base_is_refused(self):
        records = dict(SYNTHETIC_RECORDS)
        records["Base.Lard"] = {"module": "Other", "display_category": "Food"}
        with self.assertRaises(fn.EmitRefused):
            fn.emit_scripts(_synthetic(), records)

    def test_a_missing_display_category_is_refused(self):
        records = dict(SYNTHETIC_RECORDS)
        records["Base.Seeds"] = {"module": "Base", "display_category": None}
        with self.assertRaises(fn.EmitRefused):
            fn.emit_scripts(_synthetic(), records)


class EmitLuaTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.text = fn.emit_lua(_synthetic())
        cls.lines = cls.text.split("\n")

    def test_the_header(self):
        self.assertEqual(self.lines[0], "-- NR_Data_Nutrients.lua -- not a kernel file: the per-type nutrient "
                                        "table and its loader (spec § 4.2, § 4.6).")
        self.assertEqual(self.lines[1], "-- GENERATED by tools/food_nutrients.py from data/food-nutrients.json "
                                        "(mapping 7 rows; extract 3 foods); do not edit "
                                        "— regenerate with --write.")
        self.assertEqual(self.lines[2], "-- Sources: FoodData Central SR Legacy 2018-04 (CC0-1.0); USDA/FDA/ODS-NIH "
                                        "Iodine Database 4.0 (2024-10) (public-domain-US).")

    def test_one_entry_per_mapped_record_every_key_in_order(self):
        entries = re.findall(r'^    \["([^"]+)"\] = \{ (.*) \},  -- SOURCE (\S+) (\S+)$', self.text, re.M)
        self.assertEqual([e[0] for e in entries], ["Base.Apple", "Base.Lard", "Base.Seeds", "Cola"])
        for _pz_id, body, _fdc, _conf in entries:
            self.assertEqual([kv.split(" = ")[0] for kv in body.split(", ")], list(fn.KEYS))
        self.assertEqual(entries[0][2:], ("171688", "exact"))
        self.assertEqual(entries[1][2:], ("171401", "close"))

    def test_null_is_a_bare_zero_and_numbers_are_repr(self):
        apple = re.search(r'\["Base.Apple"\] = \{ (.*) \}', self.text).group(1)
        self.assertIn("vitC = 8.3674,", apple)                    # a non-macro key: the shortest repr
        self.assertIn("iodine = 0,", apple)
        self.assertIn("vitD = 0.0,", apple)
        lard = re.search(r'\["Base.Lard"\] = \{ (.*) \}', self.text).group(1)
        self.assertIn("calories = 902.0, carbs = 0,", lard)      # a null macro is still a bare 0

    def test_an_item_macro_is_the_script_blocks_two_decimals(self):
        # ruling T9-1: the vector and the vanilla stores agree exactly on every re-based food
        apple = re.search(r'\["Base.Apple"\] = \{ (.*) \}', self.text).group(1)
        self.assertIn("calories = 94.59, carbs = 25.12, lipids = 0.31, proteins = 0.47,", apple)
        seeds = re.search(r'\["Base.Seeds"\] = \{ (.*) \}', self.text).group(1)
        self.assertIn("carbs = 1.23, lipids = 0.0, proteins = 0.1,", seeds)
        script = fn.emit_scripts(_synthetic(), SYNTHETIC_RECORDS)
        self.assertIn("Calories = 94.59,", script)
        cola = re.search(r'\["Cola"\] = \{ (.*) \}', self.text).group(1)
        self.assertIn("carbs = 107.744,", cola)                   # a fluid has no script block: unrounded

    def test_the_tables_and_the_tail(self):
        self.assertIn("\nlocal NUTRIENTS = {\n", self.text)
        self.assertIn("\nlocal FLUIDS = {\n", self.text)
        self.assertTrue(self.text.endswith("\n-- 3 items, 1 fluids, 31 keys\n"))
        self.assertNotIn("\r", self.text)
        self.assertNotIn("Bleach", self.text)
        self.assertNotIn("Pebble", self.text)

    def test_the_preamble_and_the_loaders_are_the_seeds(self):
        seed = _seed_text()
        if seed is None:
            self.skipTest("git or the seed commit is unavailable")
        self.assertIn("\n" + fn.LUA_PREAMBLE, seed)
        self.assertTrue(seed.endswith("\n" + fn.LUA_LOADERS))
        self.assertIn("\n" + fn.LUA_PREAMBLE, self.text)
        self.assertIn("NR.data.UNITS = {", fn.LUA_PREAMBLE)
        self.assertIn("function NR.data.nutrients.get(fullType)", fn.LUA_LOADERS)
        self.assertIn("function NR.data.fluids.get(fluidTypeString)", fn.LUA_LOADERS)

    def test_a_negative_value_is_refused(self):
        data = _synthetic()
        data["items"][0]["per_item"]["iron"] = -1.0
        with self.assertRaises(fn.EmitRefused):
            fn.emit_lua(data)


@unittest.skipUnless(os.path.exists(fn.NUTRIENTS_JSON), "data/food-nutrients.json is not built")
class GeneratedFilesTest(unittest.TestCase):
    """The committed emission: in sync with the JSON, parsed back, and --check catching a hand edit."""

    @classmethod
    def setUpClass(cls):
        with open(fn.NUTRIENTS_JSON, encoding="utf-8") as handle:
            cls.data = json.load(handle)

    def test_the_committed_files_are_a_fresh_emission(self):
        self.assertEqual(fn.check_generated(build_fresh=False), [])

    def test_the_committed_json_and_csv_are_a_fresh_build(self):
        self.assertEqual(fn.check_generated(), [])

    def test_the_script_file_parses_back(self):
        with open(fn.SCRIPT_PATH, encoding="utf-8", newline="") as handle:
            text = handle.read()
        self.assertNotIn("\r", text)
        self.assertNotIn("//", text)
        known = set(key for _name, key in food_scan.COLUMNS if key)
        self.assertTrue(SCRIPT_KEYS <= known)
        roots = food_scan.parse_script(text, fn.SCRIPT_PATH)
        self.assertEqual([(b["kind"], b["name"]) for b in roots], [("module", "Base")])
        blocks = roots[0]["blocks"]
        expected = fn.script_records(self.data)
        self.assertEqual(["Base." + b["name"] for b in blocks], [r["pz_id"] for r in expected])
        for block, rec in zip(blocks, expected):
            self.assertEqual(set(block["props"]), SCRIPT_KEYS, block["name"])
            for script_key, key in fn.SCRIPT_MACROS:
                self.assertEqual(block["props"][script_key], "%.2f" % rec["per_item"][key])
        self.assertNotIn("ItemType", text)
        self.assertNotIn("HungerChange", text.split("*/", 1)[1])
        self.assertNotIn("ThirstChange", text.split("*/", 1)[1])

    def test_the_lua_and_the_script_cover_the_same_foods(self):
        items, fluids = fn.lua_entries(self.data)
        self.assertEqual([r["pz_id"] for r in items], [r["pz_id"] for r in fn.script_records(self.data)])
        counts = self.data["meta"]["counts"]
        self.assertEqual(len(items) + len(fluids), counts["mapped"])

    def test_check_detects_a_one_byte_hand_edit(self):
        tmp = tempfile.mkdtemp()
        try:
            lua_path, script_path = os.path.join(tmp, "NR_Data_Nutrients.lua"), os.path.join(tmp, "s.txt")
            infer_path = os.path.join(tmp, "NR_Data_Infer.lua")
            paths = dict(lua_path=lua_path, script_path=script_path, infer_path=infer_path)
            texts = fn.generated_texts(**paths)
            self.assertEqual([p for p, _t in texts], [lua_path, script_path, infer_path])
            for path, text in texts:
                fn.write_text(path, text)
            self.assertEqual(fn.check_generated(build_fresh=False, **paths), [])
            with open(script_path, encoding="utf-8", newline="") as handle:
                text = handle.read()
            n = text.index("Calories = ") + len("Calories = ")
            edited = text[:n] + ("1" if text[n] != "1" else "2") + text[n + 1:]
            fn.write_text(script_path, edited)
            stale = fn.check_generated(build_fresh=False, **paths)
            self.assertEqual([p for p, _m in stale], [script_path])
            line = text[:n].count("\n") + 1
            self.assertTrue(stale[0][1].startswith("line %d: " % line), stale[0][1])
            fn.write_text(script_path, text.replace("\n", "\r\n"))
            stale = fn.check_generated(build_fresh=False, **paths)
            self.assertEqual([p for p, _m in stale], [script_path])
            fn.write_text(script_path, text)
            with open(infer_path, encoding="utf-8", newline="") as handle:
                infer = handle.read()
            fn.write_text(infer_path, infer.replace("n = ", "n = 1", 1))
            stale = fn.check_generated(build_fresh=False, **paths)
            self.assertEqual([p for p, _m in stale], [infer_path])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_cli_check(self):
        out = subprocess.run([sys.executable, os.path.join(REPO, "tools", "food_nutrients.py"), "--check"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("in sync", out.stdout)


# ---- Task 10: the alcoholic fluids' energy (ruling T6-1) and the inference templates ----

class EthanolEnergyTest(unittest.TestCase):

    def test_mead_follows_the_games_ethanol(self):
        # Mead: the FDC entry 103 g/L of ethanol against the property's 0.06 x 789 = 47.34 g/L
        self.assertAlmostEqual(fn.ethanol_energy(820.0, 103.0, 0.06 * 789) - 820.0, -389.62, places=6)

    def test_more_ethanol_in_the_game_adds_energy(self):
        self.assertAlmostEqual(fn.ethanol_energy(434.3, 39.39, 39.45), 434.3 + 7 * 0.06, places=6)

    def test_a_null_fdc_ethanol_reads_zero_and_the_energy_is_never_negative(self):
        self.assertAlmostEqual(fn.ethanol_energy(100.0, None, 10.0), 170.0, places=6)
        self.assertEqual(fn.ethanol_energy(100.0, 300.0, 0.0), 0.0)

    def test_the_constant_is_atwaters(self):
        self.assertEqual(fn.ETHANOL_KCAL_PER_G, 7.0)
        self.assertEqual(fn.atwater({"ethanol": 1.0}), fn.ETHANOL_KCAL_PER_G)


INFER_RECORDS = {
    "Base.Apple": {"food_type": "Fruits"}, "Base.Pear": {"food_type": "Fruits"},
    "Base.Plum": {"food_type": "Fruits"}, "Base.Ice": {"food_type": "Fruits"},
    "Base.Steak": {"food_type": "Meat"}, "Base.Pork": {"food_type": "Meat"},
    "Base.Gum": {"food_type": None}, "Base.Pot": {"food_type": "Fruits"},
    "Base.Pebble": {"food_type": "Fruits"}, "Base.Basil": {"food_type": "Herb"},
}


def _infer_data():
    """Four Fruits (one at 0 kcal), two Meat, one untyped food, a mapped drainable and a reasoned item."""
    items = [
        _out_rec("Base.Apple", block=_vector(calories=100.0, fibre=4.0, vitC=10.0)),
        _out_rec("Base.Basil", fdc_id=None),
        _out_rec("Base.Gum", block=_vector(calories=10.0, fibre=1.0, vitC=None)),
        _out_rec("Base.Ice", block=_vector(calories=0.0, fibre=9.0)),
        _out_rec("Base.Pear", block=_vector(calories=50.0, fibre=1.0, vitC=10.0)),
        _out_rec("Base.Pebble", fdc_id=None),
        _out_rec("Base.Plum", block=_vector(calories=200.0, fibre=2.0, vitC=None, iron=0.123456789)),
        _out_rec("Base.Pork", block=_vector(calories=300.0, iron=3.0)),
        _out_rec("Base.Pot", kind="drainable", block=_vector(calories=500.0, fibre=50.0)),
        _out_rec("Base.Steak", block=_vector(calories=100.0, iron=2.0)),
    ]
    data = _synthetic()
    data["items"] = items
    data["fluids"] = []
    return data


class InferTemplatesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.templates, cls.fallen = fn.infer_templates(_infer_data(), INFER_RECORDS)
        cls.text = fn.emit_infer(_infer_data(), INFER_RECORDS)

    def test_the_keys_are_every_non_macro_key(self):
        self.assertEqual(fn.INFER_KEYS, tuple(k for k in fn.KEYS if k not in ("calories", "carbs", "lipids",
                                                                             "proteins")))
        self.assertEqual(len(fn.INFER_KEYS), 27)
        for entry in self.templates.values():
            self.assertEqual(tuple(entry["density"]), fn.INFER_KEYS)

    def test_a_type_median_per_kcal_over_its_food_records_with_calories(self):
        fruits = self.templates["Fruits"]
        self.assertEqual(fruits["n"], 3)                              # Ice at 0 kcal, Pot a drainable
        self.assertEqual(fruits["density"]["fibre"], 0.02)            # 0.04, 0.02, 0.01
        self.assertEqual(fruits["density"]["vitC"], 0.1)              # 0.1, 0.2 and a null read as 0
        self.assertEqual(fruits["density"]["iron"], 0.0)              # 0, 0, 0.000617
        self.assertEqual(fruits["density"]["water"], 0.0)

    def test_default_is_over_every_mapped_food_record(self):
        default = self.templates["_default"]
        self.assertEqual(default["n"], 6)
        self.assertEqual(default["density"]["fibre"], 0.015)          # 0, 0, 0.01, 0.02, 0.04, 0.1

    def test_a_type_under_three_records_falls_back(self):
        self.assertNotIn("Meat", self.templates)
        self.assertNotIn("Herb", self.templates)
        self.assertEqual(self.fallen, {"Herb": 0, "Meat": 2})
        self.assertEqual(fn.INFER_MIN_RECORDS, 3)

    def test_six_significant_figures(self):
        templates, _fallen = fn.infer_templates(_infer_data(), dict(INFER_RECORDS, **{
            "Base.Steak": {"food_type": "Fruits"}, "Base.Pork": {"food_type": "Fruits"}}))
        self.assertEqual(templates["Fruits"]["density"]["iron"], 0.000617284)   # 0.123456789 / 200

    def test_the_text(self):
        lines = self.text.split("\n")
        self.assertTrue(lines[0].startswith("-- NR_Data_Infer.lua -- not a kernel file"))
        self.assertTrue(lines[2].startswith("-- GENERATED by tools/food_nutrients.py"))
        self.assertNotIn("generated 20", lines[2])
        self.assertIn("\nNR.data.infer = {\n", self.text)
        entries = re.findall(r'^    \["([^"]+)"\] = \{ n = (\d+), density = \{ (.*) \} \},$', self.text, re.M)
        self.assertEqual([(e[0], e[1]) for e in entries], [("Fruits", "3"), ("_default", "6")])
        for _t, _n, body in entries:
            self.assertEqual([kv.split(" = ")[0] for kv in body.split(", ")], list(fn.INFER_KEYS))
        self.assertIn("fibre = 0.02, water = 0.0, vitC = 0.1,", entries[0][2])
        self.assertIn("-- Falling back to _default (fewer than 3 mapped food records): Herb (0), Meat (2).",
                      self.text)
        self.assertTrue(self.text.endswith("\n-- 1 types, _default over 6 records\n"))
        self.assertNotIn("\r", self.text)

    def test_deterministic(self):
        self.assertEqual(fn.emit_infer(_infer_data(), INFER_RECORDS), self.text)
        shuffled = _infer_data()
        shuffled["items"] = list(reversed(shuffled["items"]))
        self.assertEqual(fn.emit_infer(shuffled, INFER_RECORDS), self.text)

    def test_lua_loads_it(self):
        try:
            import lupa.lua51 as lua51
        except ImportError:
            self.skipTest("lupa is not installed")
        rt = lua51.LuaRuntime()
        rt.execute("NutritionRevamp = {}")
        rt.execute(self.text)
        infer = rt.globals().NutritionRevamp.data.infer
        self.assertEqual(infer["Fruits"]["n"], 3)
        self.assertEqual(infer["_default"]["density"]["fibre"], 0.015)


@unittest.skipUnless(os.path.exists(fn.NUTRIENTS_JSON), "data/food-nutrients.json is not built")
class RealTask10Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(fn.NUTRIENTS_JSON, encoding="utf-8") as handle:
            cls.data = json.load(handle)
        cls.fluids = dict((r["pz_id"], r) for r in cls.data["fluids"])

    def test_mead_energy_follows_the_property_ethanol(self):
        mead = self.fluids["Mead"]
        fdc_kcal = mead["per_100g"]["calories"] * mead["portion_grams"] / 100.0
        fdc_eth = mead["per_100g"]["ethanol"] * mead["portion_grams"] / 100.0
        self.assertAlmostEqual(fdc_eth, 103.0, places=6)
        self.assertAlmostEqual(mead["per_litre"]["ethanol"], 47.34, places=6)
        self.assertAlmostEqual(mead["per_litre"]["calories"] - fdc_kcal, -389.62, places=4)
        self.assertIn("calories: per_litre", " ".join(mead["checks"]["notes"]))

    def test_a_soda_with_alcohol_zero_is_unchanged(self):
        cola = self.fluids["Cola"]
        self.assertAlmostEqual(cola["per_litre"]["calories"],
                               cola["per_100g"]["calories"] * cola["portion_grams"] / 100.0, places=6)
        self.assertNotIn("calories:", " ".join(cola["checks"]["notes"]))

    def test_the_committed_templates(self):
        templates, fallen = fn.infer_templates(self.data, fn.load_dataset())
        self.assertIn("_default", templates)
        self.assertIn("Fruits", templates)
        self.assertEqual(templates["_default"]["n"], len(fn.script_records(self.data)))
        self.assertTrue(all(e["n"] >= fn.INFER_MIN_RECORDS for e in templates.values()))
        self.assertTrue(all(n < fn.INFER_MIN_RECORDS for n in fallen.values()))


def test_a_side_table_edit_makes_the_extract_stale(tmp_path):
    paths = {}
    for name in ("iodine", "phytate", "insects"):
        dst = tmp_path / os.path.basename(fn.REF_SOURCES[name])
        shutil.copyfile(fn.REF_SOURCES[name], dst)
        paths[name] = str(dst)
    assert fn.check_side_tables(paths=paths) == []
    import csv, json
    with open(fn.EXTRACT_JSON, encoding="utf-8") as handle:
        used = set(json.load(handle)["iodine"])
    with open(paths["iodine"], encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    for row in rows[1:]:
        if row[0] in used:                                # a row the extract carries
            row[2] = str(float(row[2]) + 1.0)             # its iodine_ug_100g
            break
    with open(paths["iodine"], "w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(rows)
    stale = fn.check_side_tables(paths=paths)
    assert [p for p, _m in stale] == [fn.EXTRACT_JSON]


def test_check_generated_lists_every_stale_file(tmp_path):
    lua_path, script_path = str(tmp_path / "NR_Data_Nutrients.lua"), str(tmp_path / "s.txt")
    infer_path = str(tmp_path / "NR_Data_Infer.lua")
    paths = dict(lua_path=lua_path, script_path=script_path, infer_path=infer_path)
    for path, text in fn.generated_texts(**paths):
        fn.write_text(path, text + "-- edited\n")
    stale = fn.check_generated(build_fresh=False, **paths)
    assert sorted(p for p, _m in stale) == sorted([lua_path, script_path, infer_path])


def test_check_generated_lists_the_build_and_the_emitted_files_together(tmp_path):
    out_json, out_csv = str(tmp_path / "food-nutrients.json"), str(tmp_path / "food-nutrients.csv")
    shutil.copyfile(fn.NUTRIENTS_JSON, out_json)
    shutil.copyfile(fn.NUTRIENTS_CSV, out_csv)
    for path in (out_json, out_csv):
        with open(path, "a", encoding="utf-8", newline="") as handle:
            handle.write("\n")                            # the build's output no longer matches the disk
    lua_path, script_path = str(tmp_path / "NR_Data_Nutrients.lua"), str(tmp_path / "s.txt")
    infer_path = str(tmp_path / "NR_Data_Infer.lua")
    paths = dict(lua_path=lua_path, script_path=script_path, infer_path=infer_path)
    for path, text in fn.generated_texts(nutrients_json=fn.NUTRIENTS_JSON, **paths):
        fn.write_text(path, text + "-- edited\n")
    stale = fn.check_generated(build_fresh=True, nutrients_json=out_json, nutrients_csv=out_csv, **paths)
    listed = sorted(p for p, _m in stale)
    assert out_json in listed and out_csv in listed
    assert {lua_path, script_path, infer_path} <= set(listed)


def test_check_prints_a_refusal_and_exits_1(capsys, monkeypatch):
    def refuse(*a, **k):
        raise fn.BuildRefused("the mapping does not check clean")
    monkeypatch.setattr(fn, "check_generated", refuse)
    assert fn.main(["--check"]) == 1
    assert "food_nutrients: the mapping does not check clean" in capsys.readouterr().err


def test_the_lua_headers_carry_no_date():
    for path, text in fn.generated_texts():
        if path.endswith(".lua"):
            assert not re.search(r"generated \d{4}-\d{2}-\d{2}", "\n".join(text.splitlines()[:5])), path


if __name__ == "__main__":
    unittest.main()
