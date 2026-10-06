#!/usr/bin/env python3
"""The item-pass pipeline: vanilla food records joined to USDA FoodData Central nutrient vectors.

Plan 6's tool. It reads three committed inputs -- the vanilla dataset `data/food-items.json`
(tools/food_scan.py), the hand-curated mapping `data/food-nutrient-map/*.csv` and the SR Legacy
extract the mapping cites -- and, at extract time only, the FDC source files `tools/fdc_fetch.py`
puts under the gitignored `tools/.fdc/`. It follows the scanners' conventions (tools/food_scan.py,
tools/recipe_scan.py): stdlib only, a module of plain functions, `main()` with argparse, an absent
value written as `None`/null and never `0`. Each later task adds its section below its own divider.

**The join trap.** FDC carries two nutrient numberings: `nutrient.id` (FDC's internal id, e.g.
1008) and `nutrient.nutrient_nbr` (the legacy NDB/SR number everyone quotes, e.g. 208).
`food_nutrient.nutrient_id` joins on `nutrient.id`; a join on the legacy number returns nothing.
So the key table below is written in legacy numbers (the readable, citable form) and every join goes
through the `nutrient_nbr -> nutrient.id` map built from `nutrient.csv` first.

**The units contract** is `NR.data.UNITS` (mod/NutritionRevamp/common/media/lua/shared/
NR_Data_Nutrients.lua), copied here as `UNIT_OF` and pinned by a test that reads the Lua file. An FDC
`unit_name` converts to the contract's unit by identity only (KCAL->kcal, G->g, MG->mg, UG->ug);
an `IU` row, or any unit that is not the key's, meeting a contract key RAISES -- mg and ug are never
converted silently. Values are per 100 g as FDC stores them; per item / per litre is a later step.

**Absence.** A food with no `food_nutrient` row for a key reads `None`; a row of `0` reads `0.0`.
"""
import argparse, csv, io, os, zipfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
FDC_DIR = os.path.join(TOOLS, ".fdc")
SR_LEGACY_ZIP = os.path.join(FDC_DIR, "FoodData_Central_sr_legacy_food_csv_2018-04.zip")
RETENTION_CSV = os.path.join(FDC_DIR, "NutrientRetention.csv")
HAVE_FDC = os.path.exists(SR_LEGACY_ZIP)


# ---- KEYS / UNITS / FDC table ----

# K.vector.KEYS, in order (NR_Kernel_Vector.lua); a test parses the Lua file and asserts equality.
KEYS = ("calories", "carbs", "lipids", "proteins", "fibre", "water", "vitC", "iron", "phytate",
        "retinol", "carotene", "vitD", "vitE", "vitK", "thiamine", "riboflavin", "niacin", "vitB6",
        "folate", "vitB12", "choline", "sodium", "potassium", "calcium", "magnesium", "zinc",
        "iodine", "selenium", "efa", "caffeine", "ethanol")

# NR.data.UNITS (NR_Data_Nutrients.lua); a test parses the Lua file and asserts equality.
UNIT_OF = {"calories": "kcal", "carbs": "g", "lipids": "g", "proteins": "g", "fibre": "g", "water": "g",
           "vitC": "mg", "iron": "mg", "phytate": "mg",
           "retinol": "ug", "carotene": "ug", "vitD": "ug", "vitE": "mg", "vitK": "ug", "thiamine": "mg",
           "riboflavin": "mg", "niacin": "mg", "vitB6": "mg", "folate": "ug", "vitB12": "ug", "choline": "mg",
           "sodium": "mg", "potassium": "mg", "calcium": "mg", "magnesium": "mg", "zinc": "mg", "iodine": "ug",
           "selenium": "ug", "efa": "g", "caffeine": "mg", "ethanol": "g"}

# FDC unit_name -> contract unit, identity only. IU is deliberately absent: an IU row raises.
FDC_UNIT = {"KCAL": "kcal", "G": "g", "MG": "mg", "UG": "ug"}

# Keys with no FDC nutrient at all: phytate comes from the literature column (ruling 9).
NO_FDC_KEYS = ("phytate",)

# key -> ((legacy nutrient_nbr, ...), how). "first": the first number a food carries a row for;
# "sum": the sum of the rows present (None when none is). Verified against the SR Legacy
# nutrient.csv on 2026-10-06 (Task 2); this table is the authority, the draft key table was its seed.
#   folate: 435 "Folate, DFE" first (the contract is DFE; 6482 SR foods), 417 "Folate, total" the
#           fallback (6851) -- the research briefing's "DFE has 0 rows" is wrong for SR Legacy.
#   efa:    618 "PUFA 18:2" + 619 "PUFA 18:3", the undifferentiated totals (7031 / 6940 SR foods),
#           not 675 / 851, the n-6 c,c and n-3 ALA isomers (1842 / 1967): the larger coverage wins.
#           The totals include minor isomers (trans, n-6 18:3), so efa reads slightly high on a
#           food whose fat carries them.
#   vitD:   328 (UG); 324 is the same value in IU and is never used.
FDC_NUTRIENT_NBR = {
    "calories": ((208,), "first"),
    "carbs": ((205,), "first"),
    "lipids": ((204,), "first"),
    "proteins": ((203,), "first"),
    "fibre": ((291,), "first"),
    "water": ((255,), "first"),
    "vitC": ((401,), "first"),
    "iron": ((303,), "first"),
    "retinol": ((319,), "first"),
    "carotene": ((321,), "first"),
    "vitD": ((328,), "first"),
    "vitE": ((323,), "first"),
    "vitK": ((430,), "first"),
    "thiamine": ((404,), "first"),
    "riboflavin": ((405,), "first"),
    "niacin": ((406,), "first"),
    "vitB6": ((415,), "first"),
    "folate": ((435, 417), "first"),
    "vitB12": ((418,), "first"),
    "choline": ((421,), "first"),
    "sodium": ((307,), "first"),
    "potassium": ((306,), "first"),
    "calcium": ((301,), "first"),
    "magnesium": ((304,), "first"),
    "zinc": ((309,), "first"),
    "iodine": ((314,), "first"),
    "selenium": ((317,), "first"),
    "efa": ((618, 619), "sum"),
    "caffeine": ((262,), "first"),
    "ethanol": ((221,), "first"),
}

# The SR Legacy nutrient.csv name of every number above (a real-zip test pins each).
FDC_NAME = {
    208: "Energy", 205: "Carbohydrate, by difference", 204: "Total lipid (fat)", 203: "Protein",
    291: "Fiber, total dietary", 255: "Water", 401: "Vitamin C, total ascorbic acid", 303: "Iron, Fe",
    319: "Retinol", 321: "Carotene, beta", 328: "Vitamin D (D2 + D3)",
    323: "Vitamin E (alpha-tocopherol)", 430: "Vitamin K (phylloquinone)", 404: "Thiamin",
    405: "Riboflavin", 406: "Niacin", 415: "Vitamin B-6", 435: "Folate, DFE", 417: "Folate, total",
    418: "Vitamin B-12", 421: "Choline, total", 307: "Sodium, Na", 306: "Potassium, K",
    301: "Calcium, Ca", 304: "Magnesium, Mg", 309: "Zinc, Zn", 314: "Iodine, I", 317: "Selenium, Se",
    618: "PUFA 18:2", 619: "PUFA 18:3", 262: "Caffeine", 221: "Alcohol, ethyl",
}

# SR Legacy foods (of 7793) carrying a value per key, measured 2026-10-06 by `coverage()` and pinned
# by a real-zip test; a multi-number key counts a food carrying any of its numbers (folate 6855 of
# which 6482 carry the DFE row; efa 7036, of which 7031 carry 618 and 6940 carry 619 -- so 101 foods
# (96 with 618 alone, 5 with 619 alone) sum one of the two and read low).
SR_LEGACY_COVERAGE = {
    "calories": 7793, "carbs": 7793, "lipids": 7793, "proteins": 7793, "fibre": 7231, "water": 7793,
    "vitC": 7332, "iron": 7713, "phytate": None, "retinol": 6788, "carotene": 5440, "vitD": 5185, "vitE": 5580,
    "vitK": 5054, "thiamine": 7402, "riboflavin": 7421, "niacin": 7402, "vitB6": 7262,
    "folate": 6855, "vitB12": 7113, "choline": 4611, "sodium": 7709, "potassium": 7516,
    "calcium": 7708, "magnesium": 7421, "zinc": 7406, "iodine": 0, "selenium": 6865,
    "efa": 7036, "caffeine": 5215, "ethanol": 5399,
}


def contract_unit(key, fdc_unit):
    """The contract unit an FDC `unit_name` converts to for `key`, by identity; raises otherwise."""
    unit = FDC_UNIT.get(fdc_unit)
    if unit is None:
        raise ValueError("%s: FDC unit %r has no identity conversion (an IU row never meets a "
                         "contract key)" % (key, fdc_unit))
    if unit != UNIT_OF[key]:
        raise ValueError("%s: FDC unit %r is %s, the contract is %s -- never converted silently"
                         % (key, fdc_unit, unit, UNIT_OF[key]))
    return unit


# ---- loaders ----

def _open_member(source, name):
    """A text stream over `name` in a zip (matched by basename, any folder prefix) or a directory."""
    if isinstance(source, zipfile.ZipFile):
        hits = [m for m in source.namelist() if m == name or m.endswith("/" + name)]
        if len(hits) != 1:
            raise KeyError("%s: %d members named %s" % (source.filename, len(hits), name))
        return io.TextIOWrapper(source.open(hits[0]), encoding="utf-8", newline="")
    return open(os.path.join(source, name), encoding="utf-8", newline="")


def read_rows(source, name):
    """Every data row of one CSV as a dict of strings."""
    with _open_member(source, name) as handle:
        return list(csv.DictReader(handle))


def _number(text):
    """A CSV number: `None` for the empty cell, else a float (`"0"` is `0.0`, never `None`)."""
    return None if text == "" else float(text)


def load_nutrients(source):
    """`{nutrient_nbr: {"id", "name", "unit_name"}}` from nutrient.csv, keyed by the legacy number's
    string as written (`"208"`, `"321.1"`). Rows with no legacy number are skipped (one in SR Legacy
    carries an empty `nutrient_nbr`); a repeated non-empty number is an error."""
    out = {}
    for row in read_rows(source, "nutrient.csv"):
        nbr = row["nutrient_nbr"]
        if nbr == "":
            continue
        if nbr in out:
            raise ValueError("nutrient.csv: nutrient_nbr %s appears twice" % nbr)
        out[nbr] = {"id": int(row["id"]), "name": row["name"], "unit_name": row["unit_name"]}
    return out


def load_nutrient_map(source):
    """`{nutrient_nbr: nutrient.id}` -- the map every join goes through (the join trap)."""
    return {nbr: row["id"] for nbr, row in load_nutrients(source).items()}


def resolve_keys(nutrients, strict=True):
    """`{key: [(nutrient_nbr, nutrient.id), ...]}` in the table's order, each unit checked against
    the contract (raises `ValueError` on IU or a wrong unit). `strict` raises `KeyError` on a number
    nutrients lacks; otherwise the missing number is dropped (a key with none left is omitted)."""
    out = {}
    for key, (nbrs, _how) in FDC_NUTRIENT_NBR.items():
        rows = []
        for nbr in nbrs:
            row = nutrients.get(str(nbr))
            if row is None:
                if strict:
                    raise KeyError("%s: nutrient_nbr %d is not in nutrient.csv" % (key, nbr))
                continue
            contract_unit(key, row["unit_name"])
            rows.append((nbr, row["id"]))
        if rows:
            out[key] = rows
    return out


def _combine(how, values):
    present = [v for v in values if v is not None]
    if not present:
        return None
    return present[0] if how == "first" else sum(present)


def load_food_nutrients(source, fdc_ids):
    """`{fdc_id: {key: amount_per_100g or None}}` for every requested id and every KEYS key,
    joining `food_nutrient.nutrient_id` on `nutrient.id`. An id with no rows reads all None."""
    resolved = resolve_keys(load_nutrients(source), strict=False)
    wanted = {int(i) for i in fdc_ids}
    by_nid = {}
    for key, rows in resolved.items():
        for _nbr, nid in rows:
            by_nid[nid] = None
    raw = {i: {} for i in wanted}
    for row in read_rows(source, "food_nutrient.csv"):
        fid = int(row["fdc_id"])
        if fid in wanted:
            nid = int(row["nutrient_id"])
            if nid in by_nid:
                raw[fid][nid] = _number(row["amount"])
    out = {}
    for fid in wanted:
        rec = {}
        for key in KEYS:
            if key not in resolved:
                rec[key] = None
                continue
            how = FDC_NUTRIENT_NBR[key][1]
            rec[key] = _combine(how, [raw[fid].get(nid) for _nbr, nid in resolved[key]])
        out[fid] = rec
    return out


def coverage(source):
    """`{key: foods carrying a value}` over the source's food_nutrient.csv (a multi-number key counts
    a food carrying any of its numbers); `None` for a key with no FDC number."""
    resolved = resolve_keys(load_nutrients(source), strict=False)
    foods = {}
    for row in read_rows(source, "food_nutrient.csv"):
        if row["amount"] != "":
            foods.setdefault(int(row["nutrient_id"]), set()).add(row["fdc_id"])
    out = {}
    for key in KEYS:
        if key not in resolved:
            out[key] = None
            continue
        seen = set()
        for _nbr, nid in resolved[key]:
            seen |= foods.get(nid, set())
        out[key] = len(seen)
    return out


def load_foods(source, fdc_ids):
    """`{fdc_id: {"description", "data_type", "food_category"}}` (the category's description)."""
    wanted = {int(i) for i in fdc_ids}
    categories = {row["id"]: row["description"] for row in read_rows(source, "food_category.csv")}
    out = {}
    for row in read_rows(source, "food.csv"):
        fid = int(row["fdc_id"])
        if fid in wanted:
            out[fid] = {"description": row["description"], "data_type": row["data_type"],
                        "food_category": categories.get(row["food_category_id"])}
    return out


def load_portions(source, fdc_ids):
    """`{fdc_id: [{seq_num, amount, measure_unit, modifier, gram_weight}]}` in seq_num order; the
    `modifier` string verbatim (the portion rule records it), `measure_unit` the unit's name."""
    wanted = {int(i) for i in fdc_ids}
    units = {row["id"]: row["name"] for row in read_rows(source, "measure_unit.csv")}
    out = {}
    for row in read_rows(source, "food_portion.csv"):
        fid = int(row["fdc_id"])
        if fid in wanted:
            out.setdefault(fid, []).append({
                "seq_num": int(row["seq_num"]), "amount": _number(row["amount"]),
                "measure_unit": units.get(row["measure_unit_id"], row["measure_unit_id"]),
                "modifier": row["modifier"], "gram_weight": _number(row["gram_weight"])})
    for rows in out.values():
        rows.sort(key=lambda r: r["seq_num"])
    return out


def load_retention(path, skip_defective=False):
    """`{retn_code: {nutr_no: factor_percent}}` from the USDA retention CSV (Release 6).

    A non-integer `Retn_Factor` RAISES `ValueError` naming the row: on code 5005 the CSV shifts 24
    rows one column left (`Retn_Factor` reads `Sep-75`, `Date` empty), and a loader that coerced them
    would invent factors. With `skip_defective=True` it returns `(table, skipped)`, `skipped` the
    list of `{"line", "retn_code", "nutr_no", "retn_factor"}` left out (the extract names them)."""
    table, skipped = {}, []
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            line = reader.line_num
            code, nutr, factor = int(row["Retn_Code"]), int(row["Nutr_No"]), row["Retn_Factor"]
            if not factor.isdigit():
                if not skip_defective:
                    raise ValueError("%s line %d: Retn_Code %d Nutr_No %d has a non-integer "
                                     "Retn_Factor %r" % (os.path.basename(path), line, code, nutr, factor))
                skipped.append({"line": line, "retn_code": code, "nutr_no": nutr, "retn_factor": factor})
                continue
            table.setdefault(code, {})[nutr] = int(factor)
    return (table, skipped) if skip_defective else table


# ---- checks ----

def _zero(value):
    return 0.0 if value is None else value


def atwater(record):
    """Energy from the macros, fibre-aware: `4(carbs - fibre) + 2 fibre + 4 proteins + 9 lipids +
    7 ethanol`, a None read as 0. FDC's carbohydrate is by difference and includes fibre, which yields
    about 2 kcal/g rather than 4. Read with `fibre_known`: a None fibre widens the comparison band."""
    carbs, fibre = _zero(record.get("carbs")), _zero(record.get("fibre"))
    return (4.0 * (carbs - fibre) + 2.0 * fibre + 4.0 * _zero(record.get("proteins"))
            + 9.0 * _zero(record.get("lipids")) + ETHANOL_KCAL_PER_G * _zero(record.get("ethanol")))


def fibre_known(record):
    """Whether `atwater` saw a fibre value (False when it read a None fibre as 0)."""
    return record.get("fibre") is not None


# ---- mapping ----
#
# The hand-curated mapping is a directory of part CSVs (ruling 2), one schema, merged in filename
# order, one row per dataset id across all parts; data/food-nutrient-map/README.md is its page.
# `seed_map` writes the parts once from the dataset's own id list (never a wish list); `check_map`
# is the coverage and closure test; `implied_portion` is the curators' portion instrument (ruling 4).

import json, re, sys
import food_scan

REPO = os.path.dirname(TOOLS)
DATASET_JSON = os.path.join(REPO, "data", "food-items.json")
MAP_DIR = os.path.join(REPO, "data", "food-nutrient-map")

MAP_COLUMNS = ("pz_id", "pz_display", "pz_kind", "family", "fdc_id", "fdc_source", "fdc_description",
               "confidence", "portion_grams", "portion_source", "cook_retention_code", "state_baseline",
               "iodine_ref", "phytate_mg_100g", "phytate_source", "no_nutrition_reason", "notes")
MAP_PARTS = ("produce", "grains-legumes", "meat-fish-egg-dairy", "manufactured", "fluids", "no-nutrition")

FDC_SOURCES = ("sr_legacy", "foundation", "iodine_db_r4", "literature", "derived")
CONFIDENCES = ("exact", "close", "proxy", "guess")
PORTION_SOURCES = ("vanilla_implied", "judgement")            # plus fdc_portion:<seq_num>
PORTION_FDC_RE = re.compile(r"^fdc_portion:\d+$")
FDC_ID_RE = re.compile(r"^\d+$")
STATE_BASELINES = ("raw", "cooked", "canned", "dried", "frozen", "prepared")
NO_NUTRITION_REASONS = ("not_food", "empty_container", "fluid_sourced", "inedible_body_part", "hazard",
                        "vessel_only", "spice_only", "tobacco_or_drug")
KINDS = ("food", "drainable", "fluid_container", "fluid")

# The FoodType buckets of the four food parts: the 43 named values of the 2026-09-10 dataset, every
# one listed once (a test asserts a re-scan's new value is noticed). A value in none of the lists,
# and a food with no FoodType, goes to `manufactured`.
PRODUCE_TYPES = ("Berry", "Citrus", "Fruits", "Greens", "Herb", "HotPepper", "Mushroom", "Nut", "Seed",
                 "Vegetable", "Vegetables")
GRAINS_LEGUMES_TYPES = ("Bean", "Bread", "Pasta", "Rice", "Thickener")
ANIMAL_TYPES = ("Bacon", "Beef", "Cheese", "Egg", "Fish", "Game", "Insect", "Meat", "Milk", "Poultry",
                "Roe", "Sausage", "Seafood", "Venison")
MANUFACTURED_TYPES = ("Candy", "CatFood", "Chocolate", "Cocoa", "Coffee", "DogFood", "Dressing", "Juice",
                      "NoExplicit", "Oil", "Stock", "Sugar", "Tea")
_BUCKET = dict([(t, "produce") for t in PRODUCE_TYPES] + [(t, "grains-legumes") for t in GRAINS_LEGUMES_TYPES]
               + [(t, "meat-fish-egg-dairy") for t in ANIMAL_TYPES])

# The pre-filled reason guesses (the curator confirms), first match wins, in this order.
HAZARD_IDS = ("Base.GardeningSprayCigarettes", "Base.RatPoison", "Base.CorrectionFluid", "Base.Bleach", "Bleach")
HAZARD_SUBSTRINGS = ("Bleach", "RatPoison", "CorrectionFluid")   # the fallback after the exact ids
TOBACCO_IDS = ("Cigarette", "Cigar", "Tobacco", "Pills")          # Cigar also matches Cigarillo
SPICE_ONLY_KCAL = 5       # a Spice record at or above this many kcal is a food the pass re-bases
GUESS_BUDGET = 40         # ruling 10: the most `guess` rows the mapping may hold
BODY_PART_RE = re.compile(r"[._](Head|Skull|Corpse|Hide|Leather)")   # an id token: not SunflowerHead
VESSEL_RE = re.compile(r"Bowl|Pot|Pan")

# The dataset's four macro columns -> the FDC keys (family order: kcal|carbs|lipids|proteins).
MACROS = (("calories", "calories"), ("carbohydrates", "carbs"), ("lipids", "lipids"), ("proteins", "proteins"))
MACRO_KEYS = tuple(key for _col, key in MACROS)                 # the vector keys of the four macros

# Task 5's referential checks (iodine_ref -> data/iodine-db-r4.csv, phytate_source -> the science
# rows) append here: each is `check(rows, records) -> [violation, ...]`, `rows` the merged mapping
# rows (each with `_part` and `_line`), `records` `{dataset id: record}`.
MAP_REF_CHECKS = []


def load_dataset(path=DATASET_JSON):
    """`{id: record}` over the dataset's items and fluids (a fluid record's kind is `fluid`)."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    out = {}
    for rec in list(data["items"]) + list(data["fluids"]):
        if rec["id"] in out:
            raise ValueError("%s: id %s appears twice" % (path, rec["id"]))
        out[rec["id"]] = rec
    return out


def family_of(record):
    """The four-macro tuple string `kcal|carbs|lipids|proteins` as food_scan prints the cells; empty
    when any of the four is absent (ruling 3)."""
    values = [record.get(col) for col, _key in MACROS]
    if any(v is None for v in values):
        return ""
    return "|".join(food_scan._cell(v) for v in values)


def _has_macro(record):
    return any(record.get(col) is not None for col, _key in MACROS)


def _spice_only(record):
    """A Spice record with none of the four macros, or under SPICE_ONLY_KCAL kcal (ruling T3-1)."""
    if record.get("spice") is not True:
        return False
    cal = record.get("calories")
    return not _has_macro(record) or (cal is not None and cal < SPICE_ONLY_KCAL)


def seed_part(record):
    """The part a dataset record seeds into (the README's part rule)."""
    kind = record.get("kind")
    if kind == "fluid":
        return "fluids"
    if kind in ("drainable", "fluid_container"):
        return "no-nutrition"
    if not record.get("nutrition_basis") or _spice_only(record):
        return "no-nutrition"
    if record.get("cant_eat") is True and not _has_macro(record):
        return "no-nutrition"
    return _BUCKET.get(record.get("food_type"), "manufactured")


def seed_reason(record):
    """The pre-filled `no_nutrition_reason` guess, or "" (the curator fills)."""
    pz_id, kind = record["id"], record.get("kind")
    if pz_id in HAZARD_IDS or any(s in pz_id for s in HAZARD_SUBSTRINGS):
        return "hazard"
    if any(s in pz_id for s in TOBACCO_IDS):
        return "tobacco_or_drug"
    if kind == "food" and BODY_PART_RE.search(pz_id):
        return "inedible_body_part"
    if kind == "drainable":
        return "spice_only" if record.get("spice") is True else "not_food"
    if kind == "fluid_container":
        return "fluid_sourced" if record.get("fluid_ids") else "empty_container"
    if _spice_only(record):
        return "spice_only"
    if kind == "food" and not _has_macro(record) and VESSEL_RE.search(record.get("display_name") or ""):
        return "vessel_only"
    return ""


def seed_rows(records):
    """`{part: [row, ...]}` for every part, each part sorted by pz_id."""
    parts = {p: [] for p in MAP_PARTS}
    for pz_id in sorted(records):
        rec = records[pz_id]
        row = dict.fromkeys(MAP_COLUMNS, "")
        row.update(pz_id=pz_id, pz_display=rec.get("display_name") or "", pz_kind=rec["kind"],
                   family=family_of(rec), no_nutrition_reason=seed_reason(rec))
        parts[seed_part(rec)].append(row)
    return parts


def write_part(path, rows):
    """One part CSV: the schema header, QUOTE_MINIMAL, LF, UTF-8, no stamp row, sorted by pz_id."""
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MAP_COLUMNS, quoting=csv.QUOTE_MINIMAL,
                                lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in sorted(rows, key=lambda r: r["pz_id"]):
            writer.writerow(row)


def seed_map(map_dir=MAP_DIR, dataset_path=DATASET_JSON, force=False):
    """Write the six parts from the dataset; `{part: rows}`. Never overwrites: any existing part
    CSV refuses always, and an existing non-empty directory refuses unless `force` (which seeds
    beside non-CSV files such as the README, never over a part)."""
    if os.path.isdir(map_dir):
        present = os.listdir(map_dir)
        if any(name.endswith(".csv") for name in present):
            raise FileExistsError("%s already holds part CSVs; the seed never overwrites" % map_dir)
        if present and not force:
            raise FileExistsError("%s is not empty; --force seeds beside its non-CSV files" % map_dir)
    else:
        os.makedirs(map_dir)
    parts = seed_rows(load_dataset(dataset_path))
    for part in MAP_PARTS:
        write_part(os.path.join(map_dir, part + ".csv"), parts[part])
    return {part: len(parts[part]) for part in MAP_PARTS}


def read_map(map_dir=MAP_DIR):
    """`(rows, errors)`: every part's rows in filename order (each with `_part` and `_line`), and the
    files whose header is not the schema (their rows are not read)."""
    rows, errors = [], []
    for name in sorted(n for n in os.listdir(map_dir) if n.endswith(".csv")):
        with open(os.path.join(map_dir, name), encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != MAP_COLUMNS:
                errors.append("%s: header is not the mapping schema" % name)
                continue
            for row in reader:
                row["_part"], row["_line"] = name[:-4], reader.line_num
                rows.append(row)
    return rows, errors


def _where(row):
    return "%s.csv:%d" % (row["_part"], row["_line"])


def _is_number(text, positive=False):
    try:
        value = float(text)
    except ValueError:
        return False
    return value > 0 if positive else value >= 0


def _row_violations(row, record, allow_unfilled):
    out, where, pz_id = [], _where(row), row["pz_id"]
    if record is not None and row["pz_kind"] != record["kind"]:
        out.append("%s %s: pz_kind %r, the dataset says %r" % (where, pz_id, row["pz_kind"], record["kind"]))
    for col, allowed in (("fdc_source", FDC_SOURCES), ("confidence", CONFIDENCES),
                         ("state_baseline", STATE_BASELINES), ("no_nutrition_reason", NO_NUTRITION_REASONS)):
        if row[col] and row[col] not in allowed:
            out.append("%s %s: %s %r is not in the enum" % (where, pz_id, col, row[col]))
    if row["portion_source"] and row["portion_source"] not in PORTION_SOURCES \
            and not PORTION_FDC_RE.match(row["portion_source"]):
        out.append("%s %s: portion_source %r is not in the enum" % (where, pz_id, row["portion_source"]))
    if row["fdc_id"] and row["no_nutrition_reason"]:
        out.append("%s %s: both fdc_id and no_nutrition_reason" % (where, pz_id))
    elif not row["fdc_id"] and not row["no_nutrition_reason"] and not allow_unfilled:
        out.append("%s %s: unfilled (neither fdc_id nor no_nutrition_reason)" % (where, pz_id))
    if row["fdc_id"]:
        for col in ("fdc_source", "confidence"):
            if not row[col]:
                out.append("%s %s: fdc_id without %s" % (where, pz_id, col))
    if row["confidence"] == "guess" and not row["notes"].strip():
        out.append("%s %s: a guess without notes" % (where, pz_id))
    reason = row["no_nutrition_reason"]
    if reason in ("fluid_sourced", "empty_container") and row["pz_kind"] != "fluid_container":
        out.append("%s %s: %s on a kind other than fluid_container" % (where, pz_id, reason))
    if reason in ("inedible_body_part", "vessel_only") and row["pz_kind"] != "food":
        out.append("%s %s: %s on a kind other than food" % (where, pz_id, reason))
    if reason and reason != "fluid_sourced" and record is not None and not row["notes"].strip():
        # a fluid_sourced container's calories are its fluid's per litre, not the item's (#1881): the
        # reason IS the per-litre basis, so that one reason needs no note
        cal = record.get("calories")
        if cal is not None and cal >= SPICE_ONLY_KCAL:
            out.append("%s %s: no_nutrition_reason %s on a record with %s kcal, without notes"
                       % (where, pz_id, reason, cal))
    if row["fdc_id"] and row["fdc_source"] in ("sr_legacy", "foundation") and not FDC_ID_RE.match(row["fdc_id"]):
        out.append("%s %s: fdc_id %r is not digits for %s" % (where, pz_id, row["fdc_id"], row["fdc_source"]))
    if row["cook_retention_code"]:
        if not row["cook_retention_code"].isdigit():
            out.append("%s %s: cook_retention_code %r is not an integer" % (where, pz_id, row["cook_retention_code"]))
        if record is not None and record.get("is_cookable") is not True:
            out.append("%s %s: cook_retention_code on a row that is not IsCookable" % (where, pz_id))
    if row["portion_grams"] and not _is_number(row["portion_grams"], positive=True):
        out.append("%s %s: portion_grams %r is not a positive number" % (where, pz_id, row["portion_grams"]))
    if row["phytate_mg_100g"] and not _is_number(row["phytate_mg_100g"]):
        out.append("%s %s: phytate_mg_100g %r is not a number >= 0" % (where, pz_id, row["phytate_mg_100g"]))
    return out


def _source_key(row):
    """A family member's source: its fdc_id, or `reason:<reason>` for a row with no composition."""
    return row["fdc_id"] or "reason:" + row["no_nutrition_reason"]


def _id_order(key):
    """The tie-break order: numeric ids by value, ahead of any non-numeric key, which goes by text."""
    return (0, int(key), "") if key.isdigit() else (1, 0, key)


def _family_violations(rows, records):
    """`(families, split, violations)` over the food rows whose dataset basis is per item; the empty
    tuple counts as one family (the briefing's 342) and is never split-checked."""
    families, members = set(), {}
    for row in rows:
        rec = records.get(row["pz_id"])
        if rec is None or rec["kind"] != "food" or rec.get("nutrition_basis") != "per_item":
            continue
        families.add(row["family"])
        if row["family"] and (row["fdc_id"] or row["no_nutrition_reason"]):
            members.setdefault(row["family"], []).append(row)
    split, out = 0, []
    for family in sorted(members):
        group = members[family]
        tally = {}
        for row in group:
            tally[_source_key(row)] = tally.get(_source_key(row), 0) + 1
        if len(tally) < 2:
            continue
        split += 1
        modal = sorted(tally, key=lambda k: (-tally[k],) + _id_order(k))[0]
        for row in group:
            if _source_key(row) != modal and not row["notes"].strip():
                out.append("%s %s: family %s splits (%s against the family's %s) without notes"
                           % (_where(row), row["pz_id"], family, _source_key(row), modal))
    return len(families), split, out


def _tally(values):
    out = {}
    for v in values:
        if v:
            out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items()))


def check_map(map_dir=MAP_DIR, dataset_path=DATASET_JSON, allow_unfilled=False, out=None):
    """The coverage and closure test; prints and returns the counts, `violations` among them."""
    out = sys.stdout if out is None else out
    records = load_dataset(dataset_path)
    rows, violations = read_map(map_dir)
    seen, duplicates = {}, 0
    for row in rows:
        first = seen.get(row["pz_id"])
        if first is not None:
            duplicates += 1
            violations.append("duplicate %s: %s and %s" % (row["pz_id"], _where(first), _where(row)))
        else:
            seen[row["pz_id"]] = row
    orphans = sorted(pz_id for pz_id in seen if pz_id not in records)
    unmapped = sorted(pz_id for pz_id in records if pz_id not in seen)
    violations += ["orphan %s (%s): not a dataset id" % (pz_id, _where(seen[pz_id])) for pz_id in orphans]
    violations += ["unmapped %s: no row in any part" % pz_id for pz_id in unmapped]
    for row in rows:
        violations += _row_violations(row, records.get(row["pz_id"]), allow_unfilled)
    families, split, family_violations = _family_violations(list(seen.values()), records)
    violations += family_violations
    for check in MAP_REF_CHECKS:
        violations += check(rows, records)
    guesses = sum(1 for r in rows if r["confidence"] == "guess")
    if guesses > GUESS_BUDGET:
        violations.append("guess budget: %d guess rows, the budget is %d" % (guesses, GUESS_BUDGET))
    filled = sum(1 for r in rows if r["fdc_id"] or r["no_nutrition_reason"])
    counts = {
        "rows": len(rows),
        "parts": {p: sum(1 for r in rows if r["_part"] == p) for p in sorted({r["_part"] for r in rows})},
        "by_kind": _tally(r["pz_kind"] for r in rows),
        "by_reason": _tally(r["no_nutrition_reason"] for r in rows),
        "by_confidence": _tally(r["confidence"] for r in rows),
        "filled": filled, "unfilled": len(rows) - filled,
        "families": families, "families_split": split,
        "guesses": guesses,
        "unmapped": len(unmapped), "orphans": len(orphans), "duplicates": duplicates,
        "cookable_without_code": cookable_without_code(rows, records),
        "ref_checks_skipped": ref_checks_skipped(),
        "violations": violations,
    }
    for line in violations:
        print("VIOLATION " + line, file=out)
    print(json.dumps({k: v for k, v in counts.items() if k != "violations"}, sort_keys=True), file=out)
    print("%d violation(s)" % len(violations), file=out)
    return counts


def implied_masses(record, fdc_rec):
    """`{fdc key: grams}` -- the mass each vanilla macro implies against the FDC per-100 g value,
    `vanilla / (fdc / 100)`, for the macros where both are present and non-zero."""
    out = {}
    for col, key in MACROS:
        vanilla, per100 = record.get(col), fdc_rec.get(key)
        if vanilla and per100:
            out[key] = vanilla / (per100 / 100.0)
    return out


def portion_verdict(record, fdc_rec, portions):
    """Ruling 4's first two steps: `vanilla_implied` (the mean implied mass) when >= 2 macros are
    usable and their spread max/min <= 1.1; else the FDC portions with their modifier verbatim."""
    masses = implied_masses(record, fdc_rec)
    spread = max(masses.values()) / min(masses.values()) if masses else None
    verdict = {"masses": masses, "usable": len(masses), "spread": spread,
               "portion_source": None, "portion_grams": None, "portions": []}
    if len(masses) >= 2 and spread <= 1.1:
        verdict["portion_source"] = "vanilla_implied"
        verdict["portion_grams"] = round(sum(masses.values()) / len(masses), 1)
    else:
        verdict["portions"] = [{"portion_source": "fdc_portion:%d" % p["seq_num"], "amount": p["amount"],
                                "modifier": p["modifier"], "gram_weight": p["gram_weight"]}
                               for p in portions]
    return verdict


def implied_portion(pz_id, map_dir=MAP_DIR, dataset_path=DATASET_JSON, source=None, fdc=None, out=None):
    """Print and return the portion verdict for one mapped row (`pz_id`) or every row with an
    integer fdc_id (`"all"`), joined on the row's fdc_id or on `fdc`. `source` is the SR Legacy zip
    (default) or a directory of its CSVs."""
    out = sys.stdout if out is None else out
    records = load_dataset(dataset_path)
    rows, errors = read_map(map_dir)
    for line in errors:
        print("ERROR " + line, file=out)
    wanted = [r for r in rows if pz_id == "all" or r["pz_id"] == pz_id]
    if pz_id != "all" and not wanted:
        print("%s: no row in the mapping" % pz_id, file=out)
    jobs = []
    for row in wanted:
        fid = str(fdc) if fdc is not None else row["fdc_id"]
        if not fid.isdigit():
            if pz_id != "all":
                print("%s: no fdc_id (pass --fdc <id>)" % row["pz_id"], file=out)
            continue
        jobs.append((row, int(fid)))
    if not jobs:
        return []
    close = False
    if source is None:
        source, close = zipfile.ZipFile(SR_LEGACY_ZIP), True
    try:
        ids = sorted({fid for _row, fid in jobs})
        nutrients = load_food_nutrients(source, ids)
        portions = load_portions(source, ids)
    finally:
        if close:
            source.close()
    results = []
    for row, fid in jobs:
        verdict = portion_verdict(records.get(row["pz_id"], {}), nutrients[fid], portions.get(fid, []))
        verdict.update(pz_id=row["pz_id"], fdc_id=fid)
        results.append(verdict)
        masses = " ".join("%s=%.1f" % (k, v) for k, v in verdict["masses"].items()) or "none usable"
        spread = "%.3f" % verdict["spread"] if verdict["spread"] is not None else "-"
        print("%s fdc %d: %s; spread %s" % (row["pz_id"], fid, masses, spread), file=out)
        if verdict["portion_source"]:
            print("  vanilla_implied %.1f g" % verdict["portion_grams"], file=out)
        else:
            for p in verdict["portions"]:
                print("  %s %s g (%s %s)" % (p["portion_source"], food_scan._cell(p["gram_weight"]),
                                             food_scan._cell(p["amount"]), p["modifier"]), file=out)
            if not verdict["portions"]:
                print("  no FDC portion: judgement", file=out)
    return results


# ---- extract ----
#
# Task 5. The referential checks (appended to MAP_REF_CHECKS, so `check_map` always runs them) and
# `build_extract`, which writes data/fdc-extract.json: the SR Legacy foods, the retention codes and
# the side-table rows the merged mapping cites, and nothing else, with the sources' provenance. Every
# path the checks and the build read is a REF_SOURCES entry. The two FDC files are gitignored: when one
# is absent its check is skipped and named in check_map's `ref_checks_skipped` (a fresh clone still
# checks the committed tables), and the build refuses. The three side tables are committed, so an
# absent one is a violation.

import datetime, decimal
import fdc_fetch

EXTRACT_JSON = os.path.join(REPO, "data", "fdc-extract.json")
REF_SOURCES = {
    "iodine": os.path.join(REPO, "data", "iodine-db-r4.csv"),        # key, food, iodine_ug_100g, page, note
    "phytate": os.path.join(REPO, "data", "phytate-literature.csv"),  # family, phytate_mg_100g, source, note
    "insects": os.path.join(REPO, "data", "insect-literature.csv"),   # key, ..., the literature cells
    "sr_legacy": SR_LEGACY_ZIP,                                       # a zip, or a directory of its CSVs
    "retention": RETENTION_CSV,
    "manifest": os.path.join(FDC_DIR, "manifest.json"),               # tools/fdc_fetch.py's
}
FDC_REF_SOURCES = ("retention", "sr_legacy")    # the gitignored ones: absent -> skipped, never a violation

IODINE_PREFIX = "iodine:"                       # iodine_ref = iodine:<key of the iodine table>
PHYTATE_LIT_PREFIX = "schlemmer2009:"           # phytate_source = schlemmer2009:<family of the phytate table>
PHYTATE_FRESH_PREFIX = "phyfoodcomp2019:"       # phytate_source = phyfoodcomp2019:<family>, a FRESH-weight (as eaten) value
PHYTATE_FRESH_MARKER = "basis=fresh"            # the side table's `note` of every phyfoodcomp2019 family begins with it
PHYTATE_ZERO_PREFIX = "zero:"                   # phytate_source = zero:<one of the closed families>
PHYTATE_TABLE_PREFIXES = (PHYTATE_LIT_PREFIX, PHYTATE_FRESH_PREFIX)
# The families the literature places at zero phytate (Task 4's amendment; the waves cite each one).
ZERO_PHYTATE_FAMILIES = ("dairy", "egg", "fish", "fruit", "meat", "oil", "sugar", "vegetable")
INSECT_NUMBER_COLUMNS = ("protein_g_100g", "fat_g_100g", "fibre_g_100g", "carb_g_100g", "ash_g_100g",
                         "energy_kcal_100g", "moisture_pct")
EXTRACT_SOURCES = ("sr_legacy", "literature")   # the fdc_source values the build resolves


class ExtractRefused(ValueError):
    """The build's refusal: the mapping does not check clean, an FDC file is absent, or a file the
    build reads does not hash to its manifest row."""


def read_table(path, key_col):
    """`{key: row}` over a committed side table (all cells strings); a repeated key raises."""
    with open(path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    out = {}
    for row in rows:
        if row[key_col] in out:
            raise ValueError("%s: %s %r appears twice" % (os.path.basename(path), key_col, row[key_col]))
        out[row[key_col]] = row
    return out


class _FdcSource(object):
    """`with _FdcSource(path) as source:` -- a ZipFile over a zip path (closed on exit), or the
    directory path itself (the loaders read either)."""

    def __init__(self, path):
        self.path, self.zip = path, None

    def __enter__(self):
        if os.path.isdir(self.path):
            return self.path
        self.zip = zipfile.ZipFile(self.path)
        return self.zip

    def __exit__(self, *exc):
        if self.zip is not None:
            self.zip.close()
        return False


def sr_legacy_ids(path):
    """Every `fdc_id` of the SR Legacy food.csv, as ints."""
    with _FdcSource(path) as source:
        return {int(row["fdc_id"]) for row in read_rows(source, "food.csv")}


def retention_codes(path):
    """Every `Retn_Code` of the retention CSV, the defective rows' code included."""
    with open(path, encoding="utf-8", newline="") as handle:
        return {int(row["Retn_Code"]) for row in csv.DictReader(handle)}


def retention_descriptions(path):
    """`{retn_code: RetnDesc}` (the first row's description of each code)."""
    out = {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out.setdefault(int(row["Retn_Code"]), row["RetnDesc"])
    return out


def ref_checks_skipped():
    """The FDC_REF_SOURCES whose file is absent (their checks did not run), sorted."""
    return sorted(name for name in FDC_REF_SOURCES if not os.path.exists(REF_SOURCES[name]))


def cookable_without_code(rows, records):
    """Mapped IsCookable rows with no cook_retention_code (the literature insects): counted, allowed."""
    return sum(1 for r in rows if r["fdc_id"] and not r["cook_retention_code"]
               and (records.get(r["pz_id"]) or {}).get("is_cookable") is True)


def _table_violation(name):
    return ["referential: the %s table %s is absent" % (name, REF_SOURCES[name])]


def check_iodine_refs(rows, records):
    """Every `iodine_ref` is `iodine:<key>` with the key a row of the iodine table."""
    if not os.path.exists(REF_SOURCES["iodine"]):
        return _table_violation("iodine")
    keys = read_table(REF_SOURCES["iodine"], "key")
    out = []
    for row in rows:
        ref = row["iodine_ref"]
        if ref and not (ref.startswith(IODINE_PREFIX) and ref[len(IODINE_PREFIX):] in keys):
            out.append("%s %s: iodine_ref %r does not resolve to a key of %s"
                       % (_where(row), row["pz_id"], ref, os.path.basename(REF_SOURCES["iodine"])))
    return out


def _fresh_family(entry):
    """True where a phytate table row's `note` carries the fresh-weight marker."""
    return entry["note"].startswith(PHYTATE_FRESH_MARKER)


def check_phytate_sources(rows, records):
    """Every `phytate_source` is empty, `schlemmer2009:<a dry-weight family of the phytate table>`,
    `phyfoodcomp2019:<a family whose note begins basis=fresh>` or `zero:<one of ZERO_PHYTATE_FAMILIES>`."""
    if not os.path.exists(REF_SOURCES["phytate"]):
        return _table_violation("phytate")
    families = read_table(REF_SOURCES["phytate"], "family")
    out = []
    for row in rows:
        src = row["phytate_source"]
        if not src:
            continue
        if (src.startswith(PHYTATE_LIT_PREFIX) and src[len(PHYTATE_LIT_PREFIX):] in families
                and not _fresh_family(families[src[len(PHYTATE_LIT_PREFIX):]])):
            continue
        if (src.startswith(PHYTATE_FRESH_PREFIX) and src[len(PHYTATE_FRESH_PREFIX):] in families
                and _fresh_family(families[src[len(PHYTATE_FRESH_PREFIX):]])):
            continue
        if src.startswith(PHYTATE_ZERO_PREFIX) and src[len(PHYTATE_ZERO_PREFIX):] in ZERO_PHYTATE_FAMILIES:
            continue
        out.append("%s %s: phytate_source %r resolves to neither a family of %s on its own basis nor a zero family"
                   % (_where(row), row["pz_id"], src, os.path.basename(REF_SOURCES["phytate"])))
    return out


def check_literature_ids(rows, records):
    """Every `literature` row's fdc_id is a key of the insect literature table."""
    if not os.path.exists(REF_SOURCES["insects"]):
        return _table_violation("insects")
    keys = read_table(REF_SOURCES["insects"], "key")
    return ["%s %s: literature fdc_id %r is not a key of %s"
            % (_where(r), r["pz_id"], r["fdc_id"], os.path.basename(REF_SOURCES["insects"]))
            for r in rows if r["fdc_source"] == "literature" and r["fdc_id"] and r["fdc_id"] not in keys]


def check_sr_legacy_ids(rows, records):
    """Every `sr_legacy` fdc_id is a row of the zip's food.csv (skipped when the zip is absent)."""
    if not os.path.exists(REF_SOURCES["sr_legacy"]):
        return []
    ids = sr_legacy_ids(REF_SOURCES["sr_legacy"])
    return ["%s %s: sr_legacy fdc_id %s is not in food.csv" % (_where(r), r["pz_id"], r["fdc_id"])
            for r in rows if r["fdc_source"] == "sr_legacy" and FDC_ID_RE.match(r["fdc_id"])
            and int(r["fdc_id"]) not in ids]


def check_retention_codes(rows, records):
    """Every `cook_retention_code` is a Retn_Code of the retention CSV (skipped when it is absent)."""
    if not os.path.exists(REF_SOURCES["retention"]):
        return []
    codes = retention_codes(REF_SOURCES["retention"])
    return ["%s %s: cook_retention_code %s is not in %s"
            % (_where(r), r["pz_id"], r["cook_retention_code"], os.path.basename(REF_SOURCES["retention"]))
            for r in rows if r["cook_retention_code"].isdigit() and int(r["cook_retention_code"]) not in codes]


MAP_REF_CHECKS.extend([check_iodine_refs, check_phytate_sources, check_literature_ids,
                       check_sr_legacy_ids, check_retention_codes])


def load_food_nutrient_cells(source, fdc_ids):
    """`{fdc_id: {key: {"amount", "unit", "nutrient_id"}}}` for every FDC key (phytate has none):
    `amount` per 100 g (None when no row carries a value, never 0), `unit` the FDC `unit_name`,
    `nutrient_id` the `nutrient.id` the value came from -- for a "sum" key (efa) the list of the ids
    summed, the sum taken in decimal on the CSV strings so it is never re-rounded by binary floats.
    A key whose numbers are all absent from nutrient.csv reads all three None. The amounts equal
    `load_food_nutrients`' (a test pins it)."""
    nutrients = load_nutrients(source)
    resolved = resolve_keys(nutrients, strict=False)
    unit_by_id = {row["id"]: row["unit_name"] for row in nutrients.values()}
    nids = {nid for rows in resolved.values() for _nbr, nid in rows}
    wanted = {int(i) for i in fdc_ids}
    raw = {i: {} for i in wanted}
    for row in read_rows(source, "food_nutrient.csv"):
        fid = int(row["fdc_id"])
        if fid in wanted and row["amount"] != "":
            nid = int(row["nutrient_id"])
            if nid in nids:
                raw[fid][nid] = row["amount"]
    out = {}
    for fid in wanted:
        cells = {}
        for key in KEYS:
            if key in NO_FDC_KEYS:
                continue
            rows = resolved.get(key)
            if not rows:
                cells[key] = {"amount": None, "unit": None, "nutrient_id": None}
                continue
            present = [(nid, raw[fid][nid]) for _nbr, nid in rows if nid in raw[fid]]
            if FDC_NUTRIENT_NBR[key][1] == "first":
                nid, text = present[0] if present else (rows[0][1], None)
                cells[key] = {"amount": None if text is None else float(text), "unit": unit_by_id[nid],
                              "nutrient_id": nid}
            else:
                ids = [nid for nid, _text in present] or [nid for _nbr, nid in rows]
                amount = float(sum(decimal.Decimal(text) for _nid, text in present)) if present else None
                cells[key] = {"amount": amount, "unit": unit_by_id[ids[0]], "nutrient_id": ids}
        out[fid] = cells
    return out


def _float_or_none(text):
    return None if text == "" else float(text)


def _verify_manifest(sources, read_paths):
    """Each file the build reads must hash to its manifest row (by basename); raises otherwise."""
    rows = {s["filename"]: s for s in sources}
    for path in read_paths:
        if os.path.isdir(path):
            continue
        row = rows.get(os.path.basename(path))
        if row is None:
            raise ExtractRefused("%s has no row in the manifest" % path)
        if fdc_fetch.sha256_file(path) != row["sha256"]:
            raise ExtractRefused("%s: sha256 differs from the manifest's %s (re-run tools/fdc_fetch.py)"
                                 % (path, row["sha256"]))


def extract_sources():
    """`fdc_fetch.sources()` with each file's sha256 and bytes from the manifest (None when absent)."""
    with open(REF_SOURCES["manifest"], encoding="utf-8") as handle:
        manifest = {row["filename"]: row for row in json.load(handle)}
    out = []
    for src in fdc_fetch.sources():
        row = manifest.get(src["filename"], {})
        src["sha256"], src["bytes"] = row.get("sha256"), row.get("bytes")
        out.append(src)
    return out


def build_extract(map_dir=MAP_DIR, dataset_path=DATASET_JSON, out_path=EXTRACT_JSON, out=None):
    """Write data/fdc-extract.json from the merged mapping, the SR Legacy zip, the retention CSV and the
    three side tables (every path a REF_SOURCES entry); return the extract. Refuses (ExtractRefused,
    nothing written) unless `check_map` without --allow-unfilled is clean and both FDC files are
    present and hash to the manifest. Byte-stable within one UTC day: sorted keys, indent 1, LF."""
    out = sys.stdout if out is None else out
    log = io.StringIO()
    counts = check_map(map_dir, dataset_path, allow_unfilled=False, out=log)
    if counts["violations"]:
        raise ExtractRefused("the mapping does not check clean (%d violation(s)); the first: %s"
                             % (len(counts["violations"]), "; ".join(counts["violations"][:5])))
    if counts["ref_checks_skipped"]:
        raise ExtractRefused("the build reads the FDC files; absent: %s (python tools/fdc_fetch.py)"
                             % ", ".join("%s %s" % (n, REF_SOURCES[n]) for n in counts["ref_checks_skipped"]))
    sources = extract_sources()
    _verify_manifest(sources, [REF_SOURCES["sr_legacy"], REF_SOURCES["retention"]])
    rows, _errors = read_map(map_dir)
    records = load_dataset(dataset_path)
    mapped = [r for r in rows if r["fdc_id"]]
    unsupported = sorted({r["fdc_source"] for r in mapped} - set(EXTRACT_SOURCES))
    if unsupported:
        raise ExtractRefused("fdc_source %s: the extract resolves only %s"
                             % (", ".join(unsupported), ", ".join(EXTRACT_SOURCES)))
    sr_ids = sorted({int(r["fdc_id"]) for r in mapped if r["fdc_source"] == "sr_legacy"})
    codes = sorted({int(r["cook_retention_code"]) for r in rows if r["cook_retention_code"]})
    iodine_keys = sorted({r["iodine_ref"][len(IODINE_PREFIX):] for r in rows if r["iodine_ref"]})
    families = sorted({r["phytate_source"][len(prefix):] for r in rows for prefix in PHYTATE_TABLE_PREFIXES
                       if r["phytate_source"].startswith(prefix)})
    insect_keys = sorted({r["fdc_id"] for r in mapped if r["fdc_source"] == "literature"})

    with _FdcSource(REF_SOURCES["sr_legacy"]) as source:
        described = load_foods(source, sr_ids)
        cells = load_food_nutrient_cells(source, sr_ids)
        portions = load_portions(source, sr_ids)
    foods = {}
    for fid in sr_ids:
        food = dict(described[fid])
        food.update(nutrients=cells[fid], portions=portions.get(fid, []))
        foods[str(fid)] = food

    table, skipped = load_retention(REF_SOURCES["retention"], skip_defective=True)
    descriptions = retention_descriptions(REF_SOURCES["retention"])
    retention = {str(code): {"description": descriptions[code],
                             "factors": {str(nbr): pct for nbr, pct in table.get(code, {}).items()}}
                 for code in codes}
    defective = {}
    for row in skipped:
        code = row["retn_code"]
        entry = defective.setdefault(str(code), {
            "description": descriptions[code], "skipped": [],
            "loadable_factors": {str(nbr): pct for nbr, pct in table.get(code, {}).items()}})
        entry["skipped"].append({"line": row["line"], "nutr_no": row["nutr_no"], "retn_factor": row["retn_factor"]})

    iodine_table = read_table(REF_SOURCES["iodine"], "key")
    iodine = {k: {"food": iodine_table[k]["food"], "iodine_ug_100g": float(iodine_table[k]["iodine_ug_100g"]),
                  "page": int(iodine_table[k]["page"])} for k in iodine_keys}
    phytate_table = read_table(REF_SOURCES["phytate"], "family")
    fresh_cited = {r["phytate_source"][len(PHYTATE_FRESH_PREFIX):] for r in rows
                   if r["phytate_source"].startswith(PHYTATE_FRESH_PREFIX)}
    for f in families:
        if (f in fresh_cited) != _fresh_family(phytate_table[f]):
            raise ExtractRefused("phytate family %s: the %s prefix and the table note's %r marker disagree"
                                 % (f, PHYTATE_FRESH_PREFIX if f in fresh_cited else PHYTATE_LIT_PREFIX,
                                    PHYTATE_FRESH_MARKER))
    phytate = {f: {"phytate_mg_100g": float(phytate_table[f]["phytate_mg_100g"]),
                   "source": phytate_table[f]["source"],
                   "basis": "fresh" if _fresh_family(phytate_table[f]) else "dry"} for f in families}
    insect_table = read_table(REF_SOURCES["insects"], "key")
    insects = {}
    for k in insect_keys:
        cells_k = {col: (_float_or_none(v) if col in INSECT_NUMBER_COLUMNS else v)
                   for col, v in insect_table[k].items() if col != "key"}
        insects[k] = cells_k

    missing = {key: [fid for fid in sr_ids if cells[fid][key]["amount"] is None]
               for key in KEYS if key not in NO_FDC_KEYS}
    meta = {
        "build": food_scan.BUILD,
        "jar_hash": food_scan.JAR_HASH,
        "generated": datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
        "tool": "tools/food_nutrients.py",
        "sources": sources,
        "counts": {"foods": len(foods), "retention_codes": len(retention),
                   "defective_retention_rows": len(skipped), "iodine_rows": len(iodine),
                   "phytate_rows": len(phytate), "insect_rows": len(insects),
                   "cookable_without_code": counts["cookable_without_code"],
                   "missing_nutrients": missing},
        "defective_retention": defective,
    }
    extract = {"meta": meta, "foods": foods, "retention": retention, "iodine": iodine,
               "phytate": phytate, "insects": insects}
    text = json.dumps(extract, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    with open(out_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    print("%d foods, %d retention codes, %d iodine, %d phytate, %d insect rows -> %s (%d bytes)"
          % (len(foods), len(retention), len(iodine), len(phytate), len(insects), out_path,
             len(text.encode("utf-8"))), file=out)
    return extract


# ---- build ----
#
# Task 6. `build` writes data/food-nutrients.json and its CSV twin from four committed inputs only: the
# dataset, the merged mapping, the extract and the three side tables (through check_map's referential
# checks). It reads no value from the FDC zips; check_map's two referential checks open them when present
# and skip when absent, so the build still runs without them. One record per dataset id, `{"meta", "items", "fluids"}` as food-items.json.
#
# The vectors. `per_100g` is the composition source per 100 g in the contract's units: an SR Legacy
# entry's amounts from the extract (the FDC unit converted by identity, `contract_unit`, which raises
# on any other unit), with two keys FDC lacks filled from the side tables --
#   iodine:  the iodine table's ug/100 g on a row with `iodine_ref`, else null (FDC has no iodine);
#   phytate: on a `schlemmer2009:<family>` row, the table's mg/100 g DRY weight put on the as-eaten
#            basis with the FDC entry's own water, `phytate = dry_mg_100g x (100 - water_g_100g) / 100`
#            (wave 4a's conversion; null, with a note, where the entry carries no water); on a
#            `phyfoodcomp2019:<family>` row, the table's mg/100 g as the database states it, a FRESH
#            weight (the family's note begins `basis=fresh`), taken as eaten with no conversion; `0.0`
#            on a `zero:<family>` row; null otherwise;
# and a literature row's vector read off the insect table by `literature_per_100g`. `per_item` (an item)
# or `per_litre` (a fluid, ruling 7: `portion_grams` is the litre's mass) is `per_100g x portion_grams /
# 100`, except three named overrides on a fluid's per-litre block, each written into `checks.notes`:
#   ethanol: the fluid's `alcohol` property x 789 g/L (the game's property is the design input; the
#            FDC value and the ratio go to the note);
#   calories: on the same fluids the energy follows the game's ethanol at 7 kcal/g (ruling T6-1),
#            `ethanol_energy`: the FDC energy - 7 x (the FDC ethanol - the property's), never below 0, a
#            null FDC ethanol read as 0; noted where it moves (per_100g keeps the entry's own energy);
#   water:   SimpleSyrup's litre is 1230 g of which the 615 g portion is the sugar entry, so its water
#            is 1230 - 615 g (FLUID_LITRE_GRAMS).
# A record with no composition (a `no_nutrition_reason`) has basis `none`, an all-null `per_100g` and no
# per-basis block.
#
# The checks never clamp; a value outside its range is NAMED in `checks.out_of_range` and kept. On
# per_100g: the Atwater ratio (`atwater`, fibre-aware, ethanol at 7 kcal/g) against the entry's own
# energy, an outlier outside +/-10 % (+/-25 % where fibre is null); the per-key sanity ranges; the
# proximate sum water + proteins + lipids + carbs <= 102 g; fibre <= carbs; and every factor of the
# row's cited retention code <= 100. `energy_vs_fdc_ratio` (the record's per-item or per-litre energy over
# vanilla's calories) is informational: the re-base factor, banded in `meta.counts.rebase_factor_bands`.

NUTRIENTS_JSON = os.path.join(REPO, "data", "food-nutrients.json")
NUTRIENTS_CSV = os.path.join(REPO, "data", "food-nutrients.csv")

# Per-100 g plausibility, (low, high) in the contract's unit; the Plan 6 briefing's table (section E)
# with its hardest real case, and a judgement (marked) for the keys that table does not list.
SANITY_RANGES = {
    "calories": (0.0, 910.0),        # oils at 884; lard ~902
    "proteins": (0.0, 90.0),         # gelatin / dried egg white ~88
    "lipids": (0.0, 100.0),          # pure oil at 100
    "carbs": (0.0, 100.0),           # sugar at 100
    "fibre": (0.0, 80.0),            # wheat bran ~43; psyllium higher
    "water": (0.0, 100.0),           # water + protein + fat + carb + ash ~ 100
    "vitC": (0.0, 2000.0),           # acerola ~1 678 mg
    "iron": (0.0, 130.0),            # fortified cereal; dried spirulina
    "phytate": (0.0, 7000.0),        # judgement: maize germ 6 390 mg/100 g dry, the side table's highest
    "retinol": (0.0, 20000.0),       # retinol (FDC 319): beef liver ~9 440 ug; cod-liver oil higher
    "carotene": (0.0, 30000.0),      # judgement: paprika ~26 000 ug beta-carotene, the spice tail
    "vitD": (0.0, 250.0),            # cod-liver oil ~250 ug
    "vitE": (0.0, 150.0),            # wheat-germ oil ~149 mg
    "vitK": (0.0, 1800.0),           # parsley / dried basil ~1 700 ug
    "thiamine": (0.0, 25.0),         # fortified cereal
    "riboflavin": (0.0, 25.0),       # fortified cereal
    "niacin": (0.0, 100.0),          # fortified cereal
    "vitB6": (0.0, 25.0),            # fortified cereal
    "folate": (0.0, 2500.0),         # fortified cereal; brewer's yeast
    "vitB12": (0.0, 100.0),          # clams ~98.9 ug
    "choline": (0.0, 1500.0),        # judgement: raw egg yolk ~820 mg, dried yolk higher
    "sodium": (0.0, 40000.0),        # table salt ~38 800 mg
    "potassium": (0.0, 20000.0),     # cream of tartar ~16 500 mg
    "calcium": (0.0, 8000.0),        # dried basil / fortified
    "magnesium": (0.0, 1000.0),      # rice bran ~781 mg
    "zinc": (0.0, 100.0),            # oysters ~78 mg
    "iodine": (0.0, 3000.0),         # dried kelp; the wide tail is real
    "selenium": (0.0, 2000.0),       # Brazil nuts ~1 917 ug
    "efa": (0.0, 100.0),             # judgement: the table's omega-3 row (0-60 g, flaxseed oil ~53 ALA)
                                     # does not bound efa, which adds linoleic 18:2 (safflower oil ~75 g)
    "caffeine": (0.0, 6000.0),       # judgement: instant coffee / tea powders, a few thousand mg
    "ethanol": (0.0, 100.0),         # judgement: pure ethanol
}
ATWATER_BAND = 0.10              # the Atwater ratio's band where fibre is known (briefing section E)
ATWATER_BAND_NO_FIBRE = 0.25     # ... and where fibre is null
ATWATER_MIN_KCAL = 10.0          # below this per-100 g energy the ratio is computed but never flagged:
                                 # FDC rounds a near-zero energy (coffee, tea at 1-2 kcal) to a whole kcal
PROXIMATE_MAX = 102.0            # water + proteins + lipids + carbs, allowing ash and rounding
RETENTION_MAX = 100              # a cited retention factor, percent
ETHANOL_G_PER_L = 789            # g of ethanol in a litre at alcohol = 1.0 (ruling 7)
ETHANOL_KCAL_PER_G = 7.0         # the Atwater energy of ethanol, as `atwater` reads it (ruling T6-1)
FLUID_LITRE_GRAMS = {"SimpleSyrup": 1230.0}   # the mapping note's litre mass where portion_grams is a
                                              # solute's mass, not the litre's (the 1:1 syrup)
INSECT_DM_FRACTION = 0.30        # the dry-matter fraction of a fresh invertebrate with no measured
                                 # moisture: a game choice (science row S1188, open)
INSECT_NFE_PREFIXES = ("rumpold2013:",)   # the side-table keys whose carb cell is the nitrogen-free
                                          # extract (fibre excluded); the others' cell includes fibre
REBASE_BANDS = ((None, 0.5, "<0.5"), (0.5, 0.8, "0.5-0.8"), (0.8, 0.95, "0.8-0.95"),
                (0.95, 1.05, "0.95-1.05"), (1.05, 1.25, "1.05-1.25"), (1.25, 2.0, "1.25-2.0"),
                (2.0, None, ">2.0"))
VANILLA_FIELDS = (("calories", "calories"), ("carbohydrates", "carbohydrates"), ("lipids", "lipids"),
                  ("proteins", "proteins"), ("hunger", "hunger_change"), ("thirst", "thirst_change"))
RECORD_STRINGS = ("family", "fdc_id", "fdc_source", "fdc_description", "confidence", "state_baseline",
                  "portion_source", "iodine_ref", "phytate_source", "no_nutrition_reason", "notes")
CSV_HEAD = ("pz_id", "kind", "basis", "family", "fdc_id", "fdc_source", "fdc_description", "confidence",
            "state_baseline", "cook_retention_code", "portion_grams", "portion_source", "iodine_ref",
            "phytate_source", "no_nutrition_reason")
CSV_CHECKS = ("atwater_ratio", "atwater_outlier", "energy_vs_fdc_ratio", "proximate_sum", "fibre_le_carb",
              "retention_le_100", "out_of_range", "check_notes")
CSV_COLUMNS = (CSV_HEAD + tuple("vanilla_" + name for name, _col in VANILLA_FIELDS) + KEYS
               + tuple("p100_" + k for k in KEYS) + CSV_CHECKS)


class BuildRefused(ValueError):
    """The build's refusal: the mapping does not check clean, or the extract does not hold a row the
    mapping cites (re-run --build-extract)."""


def _r6(value):
    return None if value is None else round(value, 6)


def _rel(path):
    """A path as the meta records it: relative to the repository with `/`, or its basename outside it."""
    full = os.path.abspath(path)
    if full.startswith(REPO + os.sep):
        return os.path.relpath(full, REPO).replace(os.sep, "/")
    return os.path.basename(full)


def literature_per_100g(cells):
    """A literature row's per-100 g fresh vector from its side-table cells (as the extract carries them):
    each dry-matter value x the dry-matter fraction f, where f = (100 - moisture_pct) / 100 when the source
    measured moisture, else INSECT_DM_FRACTION (0.30, a game choice), and f = 1 on a `fresh` basis. Keys:
    proteins, lipids, fibre, water (100 - 100 f on dry matter; the moisture cell on a fresh basis), carbs
    in FDC's by-difference convention (fibre included: the carb cell plus fibre where the cell is the
    nitrogen-free extract, INSECT_NFE_PREFIXES' rows; the cell itself where it includes fibre; 100 - protein
    - fat - ash where it is empty), and calories (the energy cell, or where empty `4 P + 9 F + 4 C`, C the
    carb cell or by difference after fibre and ash -- the sum the side table's notes computed and the
    mapping's portions rest on). Every other key is null."""
    key = cells.get("_key", "")
    protein, fat, fibre = cells["protein_g_100g"], cells["fat_g_100g"], cells["fibre_g_100g"]
    carb, ash, energy, moisture = (cells["carb_g_100g"], cells["ash_g_100g"], cells["energy_kcal_100g"],
                                   cells["moisture_pct"])
    if cells["basis"] == "fresh":
        frac, water = 1.0, moisture
    else:
        frac = (100.0 - moisture) / 100.0 if moisture is not None else INSECT_DM_FRACTION
        water = 100.0 - 100.0 * frac
    if carb is None:
        carbs_dm = 100.0 - _zero(protein) - _zero(fat) - _zero(ash)
        energy_carb = carbs_dm - _zero(fibre)
    else:
        carbs_dm = carb + _zero(fibre) if key.startswith(INSECT_NFE_PREFIXES) else carb
        energy_carb = carb
    if energy is None:
        energy = 4.0 * _zero(protein) + 9.0 * _zero(fat) + 4.0 * energy_carb
    out = dict.fromkeys(KEYS)
    out.update(calories=energy * frac, proteins=None if protein is None else protein * frac,
               lipids=None if fat is None else fat * frac, fibre=None if fibre is None else fibre * frac,
               carbs=carbs_dm * frac, water=water)
    return {k: _r6(v) for k, v in out.items()}


def sr_per_100g(food, row, extract, notes):
    """An SR Legacy row's per-100 g vector: the extract's amounts by identity unit, iodine and phytate
    from the side tables (the module comment's rules). Appends a note where the phytate cannot convert
    or differs from the mapping's own `phytate_mg_100g` cell by more than its 0.1 rounding."""
    out = dict.fromkeys(KEYS)
    for key, cell in food["nutrients"].items():
        if cell["amount"] is not None:
            contract_unit(key, cell["unit"])
            out[key] = cell["amount"]
    if row["iodine_ref"]:
        out["iodine"] = extract["iodine"][row["iodine_ref"][len(IODINE_PREFIX):]]["iodine_ug_100g"]
    src = row["phytate_source"]
    if src.startswith(PHYTATE_ZERO_PREFIX):
        out["phytate"] = 0.0
    elif src.startswith(PHYTATE_FRESH_PREFIX):
        fresh = extract["phytate"][src[len(PHYTATE_FRESH_PREFIX):]]
        if fresh.get("basis") != "fresh":
            raise ExtractRefused("%s: %s is not a basis=fresh family of the phytate table" % (row["pz_id"], src))
        out["phytate"] = _r6(fresh["phytate_mg_100g"])
        cell = row["phytate_mg_100g"]
        if cell and abs(float(cell) - out["phytate"]) > 0.05 + 1e-9:
            notes.append("phytate: %s mg/100 g fresh against the mapping cell %s" % (out["phytate"], cell))
    elif src.startswith(PHYTATE_LIT_PREFIX):
        dry = extract["phytate"][src[len(PHYTATE_LIT_PREFIX):]]["phytate_mg_100g"]
        if out["water"] is None:
            notes.append("phytate: %s is %s mg/100 g dry weight and the entry carries no water; null"
                         % (src, food_scan._cell(dry)))
        else:
            out["phytate"] = _r6(dry * (100.0 - out["water"]) / 100.0)
            cell = row["phytate_mg_100g"]
            if cell and abs(float(cell) - out["phytate"]) > 0.05 + 1e-9:
                notes.append("phytate: %s mg/100 g as eaten against the mapping cell %s" % (out["phytate"], cell))
    return out


def record_checks(per_100g, factors=None):
    """The per_100g checks, never clamping: `{atwater_ratio, atwater_outlier, proximate_sum, fibre_le_carb,
    retention_le_100, out_of_range, notes}`. `factors` is the cited retention code's `{nutr_no: pct}`, or
    None where the row cites none. A check whose inputs are null reads null."""
    notes, cal = [], per_100g.get("calories")
    ratio = outlier = None
    if cal and any(per_100g.get(k) is not None for k in ("carbs", "lipids", "proteins")):
        ratio = round(atwater(per_100g) / cal, 4)
        band = ATWATER_BAND if fibre_known(per_100g) else ATWATER_BAND_NO_FIBRE
        outlier = abs(ratio - 1.0) > band and cal >= ATWATER_MIN_KCAL
        if outlier:
            notes.append("atwater: %s kcal from the macros against %s, ratio %s outside +/-%d %%"
                         % (_r6(atwater(per_100g)), food_scan._cell(cal), ratio, round(band * 100)))
    proximate = None
    parts = [per_100g.get(k) for k in ("water", "proteins", "lipids", "carbs")]
    if all(v is not None for v in parts):
        proximate = _r6(sum(parts))
        if proximate > PROXIMATE_MAX:
            notes.append("proximate: water + proteins + lipids + carbs = %s g > %s" % (proximate, PROXIMATE_MAX))
    fibre, carbs = per_100g.get("fibre"), per_100g.get("carbs")
    fibre_le_carb = None if fibre is None or carbs is None else fibre <= carbs
    if fibre_le_carb is False:
        notes.append("fibre %s g > carbs %s g" % (fibre, carbs))
    retention_ok = None
    if factors is not None:
        over = sorted((int(n), pct) for n, pct in factors.items() if pct > RETENTION_MAX)
        retention_ok = not over
        for nbr, pct in over:
            notes.append("retention: factor %d %% on nutrient %d > %d" % (pct, nbr, RETENTION_MAX))
    out_of_range = []
    for key in KEYS:
        value = per_100g.get(key)
        low, high = SANITY_RANGES[key]
        if value is not None and not low <= value <= high:
            out_of_range.append(key)
            notes.append("range: %s %s %s/100 g outside %s-%s" % (key, food_scan._cell(value), UNIT_OF[key],
                                                                  food_scan._cell(low), food_scan._cell(high)))
    return {"atwater_ratio": ratio, "atwater_outlier": outlier, "proximate_sum": proximate,
            "fibre_le_carb": fibre_le_carb, "retention_le_100": retention_ok, "out_of_range": out_of_range,
            "notes": notes}


def rebase_band(ratio):
    """The REBASE_BANDS label of an energy_vs_fdc_ratio, `none` for a null ratio; bands are [low, high)."""
    if ratio is None:
        return "none"
    for low, high, label in REBASE_BANDS:
        if (low is None or ratio >= low) and (high is None or ratio < high):
            return label


def ethanol_energy(calories, fdc_ethanol, property_ethanol):
    """A fluid's per-litre energy with its ethanol moved from the FDC entry's to the game property's
    (ruling T6-1): `calories - 7 x (fdc_ethanol - property_ethanol)`, a None fdc_ethanol read as 0,
    never below 0."""
    return max(0.0, calories - ETHANOL_KCAL_PER_G * (_zero(fdc_ethanol) - property_ethanol))


def _alcohol(record):
    raw = (record.get("properties_raw") or {}).get("alcohol")
    return None if raw in (None, "") else raw


def build_record(row, record, extract):
    """One output record for a mapping row and its dataset record (the module comment's rules)."""
    kind = record["kind"]
    out = {"pz_id": row["pz_id"], "kind": kind}
    for col in RECORD_STRINGS:
        out[col] = row[col] or None
    out["cook_retention_code"] = int(row["cook_retention_code"]) if row["cook_retention_code"] else None
    out["portion_grams"] = float(row["portion_grams"]) if row["portion_grams"] else None
    out["vanilla"] = {name: record.get(col) for name, col in VANILLA_FIELDS}
    notes = []
    if not row["fdc_id"]:
        out["basis"] = "none"
        out["per_100g"] = dict.fromkeys(KEYS)
        checks = record_checks(out["per_100g"])
        checks["energy_vs_fdc_ratio"] = None
        out["checks"] = checks
        return out
    basis = "per_litre" if kind == "fluid" else "per_item"
    out["basis"] = basis
    if row["fdc_source"] == "literature":
        cells = dict(extract["insects"][row["fdc_id"]], _key=row["fdc_id"])
        per_100g = literature_per_100g(cells)
    else:
        per_100g = sr_per_100g(extract["foods"][row["fdc_id"]], row, extract, notes)
    out["per_100g"] = per_100g
    grams = out["portion_grams"]
    block = {k: (None if v is None else _r6(v * grams / 100.0)) for k, v in per_100g.items()}
    if basis == "per_litre":
        alcohol = _alcohol(record)
        if alcohol is not None:
            grams_l = float(decimal.Decimal(alcohol) * ETHANOL_G_PER_L)
            fdc = block["ethanol"]
            given = "no value" if fdc is None else "%s g" % food_scan._cell(fdc)
            ratio = "" if not fdc else ", ratio %s" % round(grams_l / fdc, 4)
            notes.append("ethanol: per_litre %s g from the alcohol property %s x %d; the FDC entry gives %s%s"
                         % (food_scan._cell(grams_l), alcohol, ETHANOL_G_PER_L, given, ratio))
            block["ethanol"] = grams_l
            kcal = block["calories"]
            if kcal is not None and _zero(fdc) != grams_l:
                moved = _r6(ethanol_energy(kcal, fdc, grams_l))
                notes.append("calories: per_litre %s kcal = the entry's %s kcal - %s x (%s - %s g ethanol)"
                             % (food_scan._cell(moved), food_scan._cell(kcal), food_scan._cell(ETHANOL_KCAL_PER_G),
                                food_scan._cell(_zero(fdc)), food_scan._cell(grams_l)))
                block["calories"] = moved
        litre = FLUID_LITRE_GRAMS.get(row["pz_id"])
        if litre is not None:
            water = _r6(litre - grams)
            notes.append("water: per_litre %s g = the litre's %s g - the %s g portion; the entry gives %s g"
                         % (food_scan._cell(water), food_scan._cell(litre), food_scan._cell(grams),
                            food_scan._cell(block["water"])))
            block["water"] = water
    out[basis] = block
    factors = None
    if out["cook_retention_code"] is not None:
        factors = extract["retention"][str(out["cook_retention_code"])]["factors"]
    checks = record_checks(per_100g, factors)
    checks["notes"] = notes + checks["notes"]
    vanilla_kcal = out["vanilla"]["calories"]
    energy = block["calories"]
    checks["energy_vs_fdc_ratio"] = (round(energy / vanilla_kcal, 4)
                                     if vanilla_kcal and energy is not None else None)
    out["checks"] = checks
    return out


def _stale(rows, extract):
    """The mapping citations the extract does not hold (each a refusal line)."""
    out = []
    for r in rows:
        if r["fdc_source"] == "sr_legacy" and r["fdc_id"] and r["fdc_id"] not in extract["foods"]:
            out.append("%s: sr_legacy %s" % (r["pz_id"], r["fdc_id"]))
        if r["fdc_source"] == "literature" and r["fdc_id"] and r["fdc_id"] not in extract["insects"]:
            out.append("%s: literature %s" % (r["pz_id"], r["fdc_id"]))
        if r["cook_retention_code"] and r["cook_retention_code"] not in extract["retention"]:
            out.append("%s: retention code %s" % (r["pz_id"], r["cook_retention_code"]))
        if r["iodine_ref"] and r["iodine_ref"][len(IODINE_PREFIX):] not in extract["iodine"]:
            out.append("%s: %s" % (r["pz_id"], r["iodine_ref"]))
        src = r["phytate_source"]
        for prefix in PHYTATE_TABLE_PREFIXES:
            if src.startswith(prefix) and src[len(prefix):] not in extract["phytate"]:
                out.append("%s: %s" % (r["pz_id"], src))
    unsupported = sorted({r["fdc_source"] for r in rows if r["fdc_id"]} - set(EXTRACT_SOURCES))
    out += ["fdc_source %s: the build resolves only %s" % (s, ", ".join(EXTRACT_SOURCES)) for s in unsupported]
    return out


def _table_rows(name):
    with open(REF_SOURCES[name], encoding="utf-8", newline="") as handle:
        return sum(1 for _row in csv.DictReader(handle))


def build_counts(records, rows, check_counts, dataset_ids):
    """`meta.counts`, every counter the build computed."""
    mapped = [r for r in records if r["basis"] != "none"]
    seen = {r["pz_id"] for r in rows}
    portion = _tally((r["portion_source"] or "").split(":")[0] for r in mapped)
    out_of_range = dict((k, sum(1 for r in mapped if k in r["checks"]["out_of_range"])) for k in KEYS)
    bands = dict((label, 0) for _lo, _hi, label in REBASE_BANDS)
    bands["none"] = 0
    for r in mapped:
        bands[rebase_band(r["checks"]["energy_vs_fdc_ratio"])] += 1
    return {
        "items": sum(1 for r in records if r["kind"] != "fluid"),
        "fluids": sum(1 for r in records if r["kind"] == "fluid"),
        "by_kind": _tally(r["kind"] for r in records),
        "by_basis": _tally(r["basis"] for r in records),
        "mapped": len(mapped),
        "no_nutrition": sum(1 for r in records if r["no_nutrition_reason"]),
        "by_confidence": _tally(r["confidence"] for r in mapped),
        "by_fdc_source": _tally(r["fdc_source"] for r in mapped),
        "by_state_baseline": _tally(r["state_baseline"] for r in mapped),
        "by_reason": _tally(r["no_nutrition_reason"] for r in records),
        "by_portion_source": portion,
        "cook_retention_set": sum(1 for r in records if r["cook_retention_code"] is not None),
        "cookable_without_code": check_counts["cookable_without_code"],
        "atwater_checked": sum(1 for r in mapped if r["checks"]["atwater_ratio"] is not None),
        "atwater_outliers": sum(1 for r in mapped if r["checks"]["atwater_outlier"]),
        "atwater_outlier_ids": sorted(r["pz_id"] for r in mapped if r["checks"]["atwater_outlier"]),
        "out_of_range": out_of_range,
        "out_of_range_records": sum(1 for r in mapped if r["checks"]["out_of_range"]),
        "proximate_over_102": sum(1 for r in mapped if (r["checks"]["proximate_sum"] or 0) > PROXIMATE_MAX),
        "fibre_over_carbs": sum(1 for r in mapped if r["checks"]["fibre_le_carb"] is False),
        "retention_over_100": sum(1 for r in mapped if r["checks"]["retention_le_100"] is False),
        "rebase_factor_bands": bands,
        "guesses": sorted(r["pz_id"] for r in records if r["confidence"] == "guess"),
        "unmapped": sorted(i for i in dataset_ids if i not in seen),
        "orphan_mappings": sorted(i for i in seen if i not in dataset_ids),
    }


def write_nutrients_csv(path, records):
    """The flat twin: one row per record (items then fluids, as the JSON), CSV_COLUMNS, the per-basis
    block under the bare key names (the `basis` column says which), `per_100g` under `p100_`, a null as
    the empty string, lists joined by `;`; LF, no stamp row. The mapping's free-text `notes` stays in the
    JSON; `check_notes` joins the checks' notes by ` | `."""
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for rec in records:
            block = rec.get(rec["basis"]) or {}
            checks = rec["checks"]
            row = [rec[c] for c in CSV_HEAD] + [rec["vanilla"][name] for name, _col in VANILLA_FIELDS]
            row += [block.get(k) for k in KEYS] + [rec["per_100g"][k] for k in KEYS]
            row += [checks[c] for c in CSV_CHECKS[:-1]] + [" | ".join(checks["notes"]) or None]
            writer.writerow([food_scan._cell(v) for v in row])


def build(map_dir=MAP_DIR, dataset_path=DATASET_JSON, extract_path=EXTRACT_JSON, out_json=NUTRIENTS_JSON,
          out_csv=NUTRIENTS_CSV, out=None):
    """Write data/food-nutrients.json and .csv; return the output. Refuses (BuildRefused, nothing written)
    unless check_map is clean without --allow-unfilled (the guess budget and the notes on a guess among
    its rules), every proxy carries notes, every mapped row has portion_grams, and the extract holds every
    citation. Reads no value from an FDC zip.
    Byte-stable within one UTC day: sorted keys, indent 1, LF."""
    out = sys.stdout if out is None else out
    counts = check_map(map_dir, dataset_path, allow_unfilled=False, out=io.StringIO())
    refusals = list(counts["violations"])
    rows, _errors = read_map(map_dir)
    refusals += ["%s %s: a proxy without notes" % (_where(r), r["pz_id"])
                 for r in rows if r["confidence"] == "proxy" and not r["notes"].strip()]
    refusals += ["%s %s: an fdc_id without portion_grams" % (_where(r), r["pz_id"])
                 for r in rows if r["fdc_id"] and not r["portion_grams"]]
    guesses = [r["pz_id"] for r in rows if r["confidence"] == "guess"]
    if len(guesses) > GUESS_BUDGET:
        refusals.append("guess budget: %d guess rows, the budget is %d" % (len(guesses), GUESS_BUDGET))
    if refusals:
        raise BuildRefused("the mapping does not check clean (%d violation(s)); the first: %s"
                           % (len(refusals), "; ".join(refusals[:5])))
    with open(extract_path, encoding="utf-8") as handle:
        extract = json.load(handle)
    stale = _stale(rows, extract)
    if stale:
        raise BuildRefused("the extract does not hold %d citation(s) (re-run --build-extract): %s"
                           % (len(stale), "; ".join(stale[:5])))
    with open(dataset_path, encoding="utf-8") as handle:
        dataset = json.load(handle)
    records = load_dataset(dataset_path)
    by_id = {r["pz_id"]: r for r in rows}
    items = [build_record(by_id[pz_id], records[pz_id], extract)
             for pz_id in sorted(records) if records[pz_id]["kind"] != "fluid"]
    fluids = [build_record(by_id[pz_id], records[pz_id], extract)
              for pz_id in sorted(records) if records[pz_id]["kind"] == "fluid"]
    ext_meta = extract["meta"]
    ext_counts = {k: v for k, v in ext_meta["counts"].items() if k != "missing_nutrients"}
    ext_counts["missing_nutrients"] = {k: len(v) for k, v in ext_meta["counts"]["missing_nutrients"].items()}
    parts = {}
    for r in rows:
        parts[r["_part"] + ".csv"] = parts.get(r["_part"] + ".csv", 0) + 1
    meta = {
        "build": food_scan.BUILD,
        "jar_hash": food_scan.JAR_HASH,
        "generated": datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
        "tool": "tools/food_nutrients.py",
        "sources": ext_meta["sources"],
        "inputs": {
            "dataset": {"path": _rel(dataset_path), "generated": (dataset.get("meta") or {}).get("generated"),
                        "build": (dataset.get("meta") or {}).get("build")},
            "mapping": {"path": _rel(map_dir), "rows": len(rows), "parts": dict(sorted(parts.items()))},
            "extract": {"path": _rel(extract_path), "generated": ext_meta.get("generated"), "counts": ext_counts},
            "side_tables": {name: {"path": _rel(REF_SOURCES[name]), "rows": _table_rows(name)}
                            for name in ("insects", "iodine", "phytate")},
        },
        "counts": build_counts(items + fluids, rows, counts, set(records)),
    }
    result = {"meta": meta, "items": items, "fluids": fluids}
    text = json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    with open(out_json, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    write_nutrients_csv(out_csv, items + fluids)
    c = meta["counts"]
    print("%d items, %d fluids, %d mapped, %d no_nutrition; %d Atwater outliers, %d out-of-range records -> %s "
          "(%d bytes), %s" % (c["items"], c["fluids"], c["mapped"], c["no_nutrition"], c["atwater_outliers"],
                               c["out_of_range_records"], out_json, len(text.encode("utf-8")), out_csv), file=out)
    return result


# ---- emit ----
#
# Task 9. The two shipped artefacts, emitted from data/food-nutrients.json alone (and, for the script
# file, the dataset's DisplayCategory), so each is a pure function of committed inputs:
#   --emit-lua      mod/.../shared/NR_Data_Nutrients.lua: the per-type nutrient table and its loader. One
#                   line per item record with basis `per_item` and an `fdc_id` (a reasoned record has no
#                   entry: the loader returns nil and the intake's fallback takes over), then one per
#                   fluid record with basis `per_litre`; every K.vector.KEYS key in order; a JSON null is
#                   written `0` (the kernel sums numbers; the JSON keeps the absence) and every number
#                   with Python's shortest round-trip `repr`, so `0.0` is a measured zero and `0` an
#                   absence -- save an ITEM's four macros, written at the script block's `%.2f` value
#                   (ruling T9-1) so the vector and the vanilla stores agree exactly on every re-based
#                   food (ruling 6); a fluid has no script block and keeps its full value. The header's
#                   role, `NR.data.UNITS` and the loaders are literal text pinned to the Plan 2 seed's
#                   (LUA_PREAMBLE, LUA_LOADERS).
#   --emit-scripts  mod/.../scripts/NR_ItemPass_Food.txt: one partial `module Base` item block per mapped
#                   FOOD record (kind `food`, `fdc_id`, basis `per_item`), sorted by id: DisplayCategory
#                   (the dataset's value) and the four macros at `%.2f`; no ItemType (X15, #1018), never
#                   HungerChange or ThirstChange, no drainable, container or fluid block. LF and no date,
#                   so the file is byte-identical on every machine that emits it from the same JSON. Its
#                   header is a `/* */` block: the engine's ScriptParser.stripComments removes block
#                   comments only (#2426) and a block comment in a loaded item script is measured
#                   stripped (#1446); a `//` line would run on into the next value.
#   --emit-infer    mod/.../shared/NR_Data_Infer.lua (Task 10, ruling 13): NR.data.infer, the density
#                   templates the intake's fallback inference reads (K.vector.infer). Per FoodType (the
#                   dataset's spelling), over the mapped FOOD records of that type (script_records) with
#                   calories > 0: for every K.vector.KEYS key but the four macros (INFER_KEYS; fibre and
#                   water included, per kcal like the rest -- one uniform rule), the median of
#                   per_item[key] / per_item.calories, a null read as 0 (what the table delivers for it),
#                   at six significant figures; `n` the record count. A type with fewer than
#                   INFER_MIN_RECORDS records has no entry (named in the header; the reader falls back
#                   to `_default`, the same medians over every such record). A judgement from the pass's
#                   own medians, not a measurement.
#   --check         every generated file against a fresh emission, byte for byte (the JSON against a
#                   fresh --build with its `meta.generated` date taken from the file on disk); exit 1
#                   naming the first differing line. --write regenerates everything.

import shutil, tempfile, textwrap

LUA_DATA_PATH = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared",
                             "NR_Data_Nutrients.lua")
SCRIPT_PATH = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "scripts", "NR_ItemPass_Food.txt")
INFER_PATH = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Data_Infer.lua")
INFER_MIN_RECORDS = 3      # a FoodType with fewer mapped food records falls back to `_default` (ruling 13)
SCRIPT_MACROS = (("Calories", "calories"), ("Carbohydrates", "carbs"), ("Proteins", "proteins"),
                 ("Lipids", "lipids"))
LUA_KEY_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")     # a table key needs no escaping
SCRIPT_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")    # an item name the script grammar takes bare
# Further generated files, appended by later tasks as (path, emit(data, records) -> text); --check and
# --write cover them with the three below (Task 10's NR_Data_Infer.lua is a named one, `infer_path`).
EXTRA_EMITTERS = []

LUA_PREAMBLE = r'''local NR = NutritionRevamp
local K = NR.kernel
NR.data = NR.data or {}
NR.data.nutrients = {}
NR.data.fluids = {}

-- The units contract: the unit of every vector key, per item (per litre for a fluid). Plan 6's
-- pipeline emits these units and the kernel's coefficients assume them -- K.stomach.ironFactor's
-- per-MILLIGRAM phytate and vitamin C slopes (the rows cited there) and K.stomach.BIOAVAIL per the
-- same key -- so a seed or generated value in any other unit misreads by the conversion factor
-- (phytate in grams read about 1000x too weak an inhibition). Every K.vector.KEYS key is listed, and
-- nothing else.
-- The Plan 4 keys: micrograms for retinol, carotene (beta-carotene), vitD, vitK, folate (DFE), vitB12,
-- iodine and selenium; grams for efa (linoleic plus alpha-linolenic acid) and ethanol; milligrams for
-- the rest. ASCII "ug" rather than the micro sign, so the string is one byte per character.
NR.data.UNITS = { calories = "kcal", carbs = "g", lipids = "g", proteins = "g", fibre = "g", water = "g",
                  vitC = "mg", iron = "mg", phytate = "mg",
                  retinol = "ug", carotene = "ug", vitD = "ug", vitE = "mg", vitK = "ug", thiamine = "mg",
                  riboflavin = "mg", niacin = "mg", vitB6 = "mg", folate = "ug", vitB12 = "ug", choline = "mg",
                  sodium = "mg", potassium = "mg", calcium = "mg", magnesium = "mg", zinc = "mg", iodine = "ug",
                  selenium = "ug", efa = "g", caffeine = "mg", ethanol = "g" }
'''

LUA_LOADERS = r'''-- A fresh zeroed vector of the declared keys filled from the seed entry, so a reader cannot mutate
-- the seed; nil if the entry is absent.
local function copyOf(seed)
    if seed == nil then
        return nil
    end
    local v = K.vector.new()
    for key, value in pairs(seed) do
        v[key] = value
    end
    return v
end

-- The per-item loader every reader goes through.
function NR.data.nutrients.get(fullType)
    return copyOf(NUTRIENTS[fullType])
end

-- The per-litre fluid loader every reader goes through.
function NR.data.fluids.get(fluidTypeString)
    return copyOf(FLUIDS[fluidTypeString])
end
'''


class EmitRefused(ValueError):
    """A value the emitters will not write: negative, not finite, or an id that needs escaping."""


def lua_number(value):
    """`0` for a JSON null; else the float's shortest round-trip repr (`1.0`, `1e-05`, `94.588`)."""
    if value is None:
        return "0"
    v = float(value)
    if v != v or v in (float("inf"), float("-inf")) or v < 0:
        raise EmitRefused("not a finite non-negative number: %r" % (value,))
    return repr(v)


def script_macro(value):
    """An item macro as the script block carries it: `%.2f` of the value (0.0 for a null), as a float."""
    lua_number(value)                                            # the same refusal on a bad value
    return float("%.2f" % float(value or 0.0))


def _lua_value(key, value, item):
    """An entry's value text: an ITEM's macro at the script block's two decimals (ruling T9-1, a null
    still a bare 0), anything else the shortest repr."""
    if item and value is not None and key in MACRO_KEYS:
        return lua_number(script_macro(value))
    return lua_number(value)


def _lua_entry(key, block, comment, item=False):
    if not LUA_KEY_RE.match(key):
        raise EmitRefused("an id the emitter will not quote: %r" % (key,))
    body = ", ".join("%s = %s" % (k, _lua_value(k, block[k], item)) for k in KEYS)
    return '    ["%s"] = { %s },  -- %s' % (key, body, comment)


def lua_entries(data):
    """(items, fluids): the records the Lua table carries, in the JSON's (id) order."""
    items = [r for r in data["items"] if r["basis"] == "per_item" and r["fdc_id"]]
    fluids = [r for r in data["fluids"] if r["basis"] == "per_litre" and r["fdc_id"]]
    return items, fluids


def emit_lua(data):
    """The whole NR_Data_Nutrients.lua text from a food-nutrients output."""
    meta = data["meta"]
    items, fluids = lua_entries(data)
    sources = "; ".join("%s %s (%s)" % (s["name"], s["release"], s["licence"]) for s in meta["sources"])
    out = [
        "-- NR_Data_Nutrients.lua -- not a kernel file: the per-type nutrient table and its loader "
        "(spec § 4.2, § 4.6).",
        "-- GENERATED by tools/food_nutrients.py from data/food-nutrients.json (generated %s; mapping %d rows; "
        "extract %d foods); do not edit — regenerate with --write."
        % (meta["generated"], meta["inputs"]["mapping"]["rows"], meta["inputs"]["extract"]["counts"]["foods"]),
        "-- Sources: %s." % sources,
        "-- Items per item, fluids per litre, every K.vector.KEYS key on every entry; a number is the JSON's",
        "-- value exactly (save an item's four macros, at the script block's two decimals so the vector and",
        "-- the vanilla stores agree), `0.0` a measured zero and `0` an absence (null in the JSON). A food or",
        "-- fluid with no entry has no mapping (a no_nutrition_reason): its loader returns nil, and the intake",
        "-- infers its vector (NR_Data_Infer.lua). Each entry's trailing comment is SOURCE <fdc_id> <confidence>.",
        "-- The script half of the item pass is NR_ItemPass_Food.txt.",
        "-- A reader goes through the loaders, never the tables.",
        "-- Units: NR.data.UNITS below (ug = micrograms).",
    ]
    text = "\n".join(out) + "\n" + LUA_PREAMBLE
    text += "\n-- Per-item vectors (data/food-nutrients.json `per_item`).\nlocal NUTRIENTS = {\n"
    text += "".join(_lua_entry(r["pz_id"], r["per_item"], "SOURCE %s %s" % (r["fdc_id"], r["confidence"]),
                               item=True) + "\n"
                    for r in items)
    text += "}\n\n-- Per-litre fluid vectors (data/food-nutrients.json `per_litre`).\nlocal FLUIDS = {\n"
    text += "".join(_lua_entry(r["pz_id"], r["per_litre"], "SOURCE %s %s" % (r["fdc_id"], r["confidence"])) + "\n"
                    for r in fluids)
    text += "}\n\n" + LUA_LOADERS
    text += "\n-- %d items, %d fluids, %d keys\n" % (len(items), len(fluids), len(KEYS))
    return text


def script_records(data):
    """The FOOD records the script file re-bases, in id order."""
    return [r for r in data["items"] if r["kind"] == "food" and r["fdc_id"] and r["basis"] == "per_item"]


def emit_scripts(data, records):
    """The whole NR_ItemPass_Food.txt text; `records` is the dataset `{id: record}` (DisplayCategory)."""
    lines = ["/* GENERATED by tools/food_nutrients.py from data/food-nutrients.json; do not edit - regenerate "
             "with --write. Re-bases Calories, Carbohydrates, Proteins and Lipids on every mapped base:food "
             "record; HungerChange and ThirstChange untouched (spec section 4.6). */",
             "module Base", "{"]
    for n, rec in enumerate(script_records(data)):
        pz_id = rec["pz_id"]
        source = records.get(pz_id)
        if source is None or source.get("module") != "Base" or not pz_id.startswith("Base."):
            raise EmitRefused("%s: not a Base record of the dataset" % pz_id)
        name = pz_id[len("Base."):]
        category = source.get("display_category")
        if not SCRIPT_NAME_RE.match(name) or not category or not SCRIPT_NAME_RE.match(category):
            raise EmitRefused("%s: a name or DisplayCategory the script grammar does not take bare" % pz_id)
        if n:
            lines.append("")
        lines += ["    item %s" % name, "    {", "        DisplayCategory = %s," % category]
        for script_key, key in SCRIPT_MACROS:
            lines.append("        %s = %.2f," % (script_key, script_macro(rec["per_item"][key])))
        lines.append("    }")
    lines.append("}")
    return "\n".join(lines) + "\n"


INFER_KEYS = tuple(k for k in KEYS if k not in MACRO_KEYS)     # the 27 keys a template carries


def _median(values):
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _sig6(value):
    return float("%.6g" % value)


def _density(recs):
    """{key: median per-kcal density} over records with calories > 0, a null read as 0, 6 significant
    figures, in INFER_KEYS order."""
    return dict((k, _sig6(_median([(r["per_item"][k] or 0.0) / r["per_item"]["calories"] for r in recs])))
                for k in INFER_KEYS)


def infer_templates(data, records):
    """({FoodType or `_default`: {"n", "density"}}, {fallen-back FoodType: record count}) over the
    mapped food records (script_records) with calories > 0; `records` is the dataset `{id: record}`
    (its `food_type`). A type with fewer than INFER_MIN_RECORDS records is not a template; every
    FoodType the dataset spells is either a template or fallen back."""
    usable = [r for r in script_records(data) if (r["per_item"]["calories"] or 0.0) > 0]
    by_type = {}
    for rec in usable:
        food_type = (records.get(rec["pz_id"]) or {}).get("food_type")
        if food_type:
            by_type.setdefault(food_type, []).append(rec)
    spelled = set(r.get("food_type") for r in records.values() if r.get("food_type"))
    templates, fallen = {}, {}
    for food_type in sorted(spelled | set(by_type)):
        recs = by_type.get(food_type, [])
        if not LUA_KEY_RE.match(food_type):
            raise EmitRefused("a FoodType the emitter will not quote: %r" % (food_type,))
        if len(recs) < INFER_MIN_RECORDS:
            fallen[food_type] = len(recs)
        else:
            templates[food_type] = {"n": len(recs), "density": _density(recs)}
    if usable:
        templates["_default"] = {"n": len(usable), "density": _density(usable)}
    return templates, fallen


def emit_infer(data, records):
    """The whole NR_Data_Infer.lua text: NR.data.infer, the FoodType density templates."""
    templates, fallen = infer_templates(data, records)
    types = sorted(t for t in templates if t != "_default")
    default_n = templates["_default"]["n"] if "_default" in templates else 0
    out = [
        "-- NR_Data_Infer.lua -- not a kernel file: the per-FoodType density templates the intake's fallback",
        "-- inference reads (K.vector.infer; spec § 4.2, Plan 6 ruling 13).",
        "-- GENERATED by tools/food_nutrients.py from data/food-nutrients.json and data/food-items.json "
        "(generated %s); do not edit — regenerate with --write." % data["meta"]["generated"],
        "-- A judgement from the pass's own medians, not a measurement. Per FoodType (the dataset's spelling),",
        "-- over the item pass's mapped food records of that type with calories > 0: for every K.vector.KEYS",
        "-- key but the four macros (fibre and water included), the median of per_item[key] / per_item.calories,",
        "-- a null read as 0 (what the table delivers), in the key's NR.data.UNITS unit per kcal, at six",
        "-- significant figures; n is the record count. `_default` is the same over every such record. A type",
        "-- with fewer than %d records has no entry and its reader falls back to `_default`." % INFER_MIN_RECORDS,
    ]
    out += textwrap.wrap("Falling back to _default (fewer than %d mapped food records): %s."
                         % (INFER_MIN_RECORDS, ", ".join("%s (%d)" % (t, fallen[t]) for t in sorted(fallen))
                            or "none"), width=100, initial_indent="-- ", subsequent_indent="-- ")
    out += [
        "local NR = NutritionRevamp",
        "NR.data = NR.data or {}",
        "",
        "NR.data.infer = {",
    ]
    for food_type in types + (["_default"] if "_default" in templates else []):
        entry = templates[food_type]
        body = ", ".join("%s = %s" % (k, lua_number(entry["density"][k])) for k in INFER_KEYS)
        out.append('    ["%s"] = { n = %d, density = { %s } },' % (food_type, entry["n"], body))
    out += ["}", "", "-- %d types, _default over %d records" % (len(types), default_n)]
    return "\n".join(out) + "\n"


def _load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def generated_texts(nutrients_json=NUTRIENTS_JSON, dataset_path=DATASET_JSON, lua_path=LUA_DATA_PATH,
                    script_path=SCRIPT_PATH, infer_path=INFER_PATH):
    """[(path, text)] for every file emitted from the output JSON."""
    data = _load_json(nutrients_json)
    records = load_dataset(dataset_path)
    out = [(lua_path, emit_lua(data)), (script_path, emit_scripts(data, records)),
           (infer_path, emit_infer(data, records))]
    out += [(path, emit(data, records)) for path, emit in EXTRA_EMITTERS]
    return out


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def first_difference(expected, actual):
    """`line <n>: expected <a!r> / on disk <b!r>` at the first differing line, or None if equal."""
    if expected == actual:
        return None
    exp, act = expected.split("\n"), actual.split("\n")
    for n in range(max(len(exp), len(act))):
        a = exp[n] if n < len(exp) else "<end of file>"
        b = act[n] if n < len(act) else "<end of file>"
        if a != b:
            return "line %d: expected %r / on disk %r" % (n + 1, a[:160], b[:160])
    return "the files differ in their line endings or final newline"


def _read_text(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def check_generated(map_dir=MAP_DIR, dataset_path=DATASET_JSON, extract_path=EXTRACT_JSON,
                    nutrients_json=NUTRIENTS_JSON, nutrients_csv=NUTRIENTS_CSV, lua_path=LUA_DATA_PATH,
                    script_path=SCRIPT_PATH, build_fresh=True, infer_path=INFER_PATH):
    """[(path, message)] for every generated file out of sync; empty when all are in sync."""
    stale = []
    if build_fresh:
        tmp = tempfile.mkdtemp(prefix="food_nutrients_check_")
        try:
            fresh_json, fresh_csv = os.path.join(tmp, "out.json"), os.path.join(tmp, "out.csv")
            try:
                fresh = build(map_dir, dataset_path, extract_path, fresh_json, fresh_csv, out=io.StringIO())
            except BuildRefused as refused:
                return [(nutrients_json, "the build refuses: %s" % refused)]
            on_disk = _read_text(nutrients_json)
            if on_disk is None:
                stale.append((nutrients_json, "missing"))
            else:
                try:
                    fresh["meta"]["generated"] = json.loads(on_disk)["meta"]["generated"]
                except (ValueError, KeyError, TypeError):
                    pass
                text = json.dumps(fresh, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
                diff = first_difference(text, on_disk)
                if diff:
                    stale.append((nutrients_json, diff))
            on_disk_csv = _read_text(nutrients_csv)
            diff = "missing" if on_disk_csv is None else first_difference(_read_text(fresh_csv), on_disk_csv)
            if diff:
                stale.append((nutrients_csv, diff))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if stale:
            return stale
    for path, text in generated_texts(nutrients_json, dataset_path, lua_path, script_path, infer_path):
        on_disk = _read_text(path)
        diff = "missing" if on_disk is None else first_difference(text, on_disk)
        if diff:
            stale.append((path, diff))
    return stale


def write_generated(map_dir=MAP_DIR, dataset_path=DATASET_JSON, extract_path=EXTRACT_JSON,
                    nutrients_json=NUTRIENTS_JSON, nutrients_csv=NUTRIENTS_CSV, lua_path=LUA_DATA_PATH,
                    script_path=SCRIPT_PATH, out=None, infer_path=INFER_PATH):
    """--write: --build, then every emitter. Returns [(path, bytes)]."""
    out = sys.stdout if out is None else out
    build(map_dir, dataset_path, extract_path, nutrients_json, nutrients_csv, out=out)
    written = []
    for path, text in generated_texts(nutrients_json, dataset_path, lua_path, script_path, infer_path):
        write_text(path, text)
        written.append((path, len(text.encode("utf-8"))))
        print("%s (%d bytes)" % (path, written[-1][1]), file=out)
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="The item-pass pipeline: vanilla foods joined to FDC SR Legacy nutrient vectors "
                    "(Plan 6). The later flags land with their tasks.")
    parser.add_argument("--seed-map", action="store_true",
                        help="write the six mapping parts from the dataset (never overwrites a part)")
    parser.add_argument("--force", action="store_true",
                        help="with --seed-map: seed into an existing directory holding no part CSV")
    parser.add_argument("--check-map", action="store_true",
                        help="the coverage and closure test over the mapping; exit 1 on a violation")
    parser.add_argument("--allow-unfilled", action="store_true",
                        help="with --check-map: a row with neither fdc_id nor reason passes")
    parser.add_argument("--implied-portion", metavar="PZ_ID|all",
                        help="print the four implied masses, their spread and the portion verdict")
    parser.add_argument("--fdc", type=int, metavar="FDC_ID",
                        help="with --implied-portion: join on this fdc_id instead of the row's")
    parser.add_argument("--build-extract", action="store_true",
                        help="write data/fdc-extract.json from the mapping, the FDC files and the side "
                             "tables; refuses unless --check-map is clean")
    parser.add_argument("--extract", default=EXTRACT_JSON,
                        help="the extract: written by --build-extract, read by --build")
    parser.add_argument("--build", action="store_true",
                        help="write data/food-nutrients.json and .csv from the dataset, the mapping, the "
                             "extract and the side tables (never the FDC zips); refuses unless the mapping "
                             "checks clean and the extract holds every citation")
    parser.add_argument("--out-json", default=NUTRIENTS_JSON, help="with --build: the JSON path")
    parser.add_argument("--out-csv", default=NUTRIENTS_CSV, help="with --build: the CSV path")
    parser.add_argument("--map-dir", default=MAP_DIR, help="the mapping directory")
    parser.add_argument("--dataset", default=DATASET_JSON, help="the food dataset JSON")
    parser.add_argument("--emit-lua", action="store_true",
                        help="write NR_Data_Nutrients.lua (the per-type table and its loader) from the JSON")
    parser.add_argument("--emit-scripts", action="store_true",
                        help="write NR_ItemPass_Food.txt (the partial module Base blocks) from the JSON")
    parser.add_argument("--emit-infer", action="store_true",
                        help="write NR_Data_Infer.lua (the FoodType density templates) from the JSON and the "
                             "dataset")
    parser.add_argument("--check", action="store_true",
                        help="every generated file against a fresh build and emission; exit 1 on a difference")
    parser.add_argument("--write", action="store_true",
                        help="regenerate everything: --build, then every emitter")
    args = parser.parse_args(argv)
    if args.check:
        stale = check_generated(args.map_dir, args.dataset, args.extract, args.out_json, args.out_csv)
        for path, message in stale:
            print("STALE %s: %s" % (_rel(path), message), file=sys.stderr)
        if stale:
            print("regenerate with: python tools/food_nutrients.py --write", file=sys.stderr)
            return 1
        print("in sync: the JSON, the CSV and %d emitted file(s)" % (3 + len(EXTRA_EMITTERS)))
        return 0
    if args.write:
        try:
            write_generated(args.map_dir, args.dataset, args.extract, args.out_json, args.out_csv)
        except (BuildRefused, EmitRefused) as refused:
            print("REFUSED " + str(refused), file=sys.stderr)
            return 1
        return 0
    if args.emit_lua or args.emit_scripts or args.emit_infer:
        data = _load_json(args.out_json)
        try:
            if args.emit_lua:
                text = emit_lua(data)
                write_text(LUA_DATA_PATH, text)
                print("%s (%d bytes)" % (LUA_DATA_PATH, len(text.encode("utf-8"))))
            if args.emit_scripts:
                text = emit_scripts(data, load_dataset(args.dataset))
                write_text(SCRIPT_PATH, text)
                print("%s (%d bytes)" % (SCRIPT_PATH, len(text.encode("utf-8"))))
            if args.emit_infer:
                text = emit_infer(data, load_dataset(args.dataset))
                write_text(INFER_PATH, text)
                print("%s (%d bytes)" % (INFER_PATH, len(text.encode("utf-8"))))
        except EmitRefused as refused:
            print("REFUSED " + str(refused), file=sys.stderr)
            return 1
        return 0
    if args.seed_map:
        sizes = seed_map(args.map_dir, args.dataset, force=args.force)
        print(json.dumps(sizes))
        return 0
    if args.check_map:
        counts = check_map(args.map_dir, args.dataset, allow_unfilled=args.allow_unfilled)
        return 1 if counts["violations"] else 0
    if args.build_extract:
        try:
            build_extract(args.map_dir, args.dataset, args.extract)
        except ExtractRefused as refused:
            print("REFUSED " + str(refused), file=sys.stderr)
            return 1
        return 0
    if args.build:
        try:
            build(args.map_dir, args.dataset, args.extract, args.out_json, args.out_csv)
        except BuildRefused as refused:
            print("REFUSED " + str(refused), file=sys.stderr)
            return 1
        return 0
    if args.implied_portion:
        implied_portion(args.implied_portion, args.map_dir, args.dataset, fdc=args.fdc)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
