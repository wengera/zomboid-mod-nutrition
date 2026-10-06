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


if __name__ == "__main__":
    unittest.main()
