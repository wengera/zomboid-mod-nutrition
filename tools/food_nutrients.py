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
            + 9.0 * _zero(record.get("lipids")) + 7.0 * _zero(record.get("ethanol")))


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
HAZARD_IDS = ("Bleach", "RatPoison", "CorrectionFluid")
TOBACCO_IDS = ("Cigarette", "Tobacco", "Pills")
BODY_PART_RE = re.compile(r"[._](Head|Skull|Corpse|Hide|Leather)")   # an id token: not SunflowerHead
VESSEL_RE = re.compile(r"Bowl|Pot|Pan")

# The dataset's four macro columns -> the FDC keys (family order: kcal|carbs|lipids|proteins).
MACROS = (("calories", "calories"), ("carbohydrates", "carbs"), ("lipids", "lipids"), ("proteins", "proteins"))

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


def seed_part(record):
    """The part a dataset record seeds into (the README's part rule)."""
    kind = record.get("kind")
    if kind == "fluid":
        return "fluids"
    if kind in ("drainable", "fluid_container"):
        return "no-nutrition"
    if not record.get("nutrition_basis") or record.get("spice") is True:
        return "no-nutrition"
    if record.get("cant_eat") is True and not _has_macro(record):
        return "no-nutrition"
    return _BUCKET.get(record.get("food_type"), "manufactured")


def seed_reason(record):
    """The pre-filled `no_nutrition_reason` guess, or "" (the curator fills)."""
    pz_id, kind = record["id"], record.get("kind")
    if any(s in pz_id for s in HAZARD_IDS):
        return "hazard"
    if any(s in pz_id for s in TOBACCO_IDS):
        return "tobacco_or_drug"
    if kind == "food" and BODY_PART_RE.search(pz_id):
        return "inedible_body_part"
    if kind == "drainable":
        return "not_food"
    if kind == "fluid_container":
        return "fluid_sourced" if record.get("fluid_ids") else "empty_container"
    if record.get("spice") is True:
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


def _family_violations(rows, records):
    """`(families, split, violations)` over the food rows whose dataset basis is per item; the empty
    tuple counts as one family (the briefing's 342) and is never split-checked."""
    families, members = set(), {}
    for row in rows:
        rec = records.get(row["pz_id"])
        if rec is None or rec["kind"] != "food" or rec.get("nutrition_basis") != "per_item":
            continue
        families.add(row["family"])
        if row["family"] and row["fdc_id"]:
            members.setdefault(row["family"], []).append(row)
    split, out = 0, []
    for family in sorted(members):
        group = members[family]
        tally = {}
        for row in group:
            tally[row["fdc_id"]] = tally.get(row["fdc_id"], 0) + 1
        if len(tally) < 2:
            continue
        split += 1
        modal = sorted(tally, key=lambda fid: (-tally[fid], fid))[0]
        for row in group:
            if row["fdc_id"] != modal and not row["notes"].strip():
                out.append("%s %s: family %s splits (fdc_id %s against the family's %s) without notes"
                           % (_where(row), row["pz_id"], family, row["fdc_id"], modal))
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
    filled = sum(1 for r in rows if r["fdc_id"] or r["no_nutrition_reason"])
    counts = {
        "rows": len(rows),
        "parts": {p: sum(1 for r in rows if r["_part"] == p) for p in sorted({r["_part"] for r in rows})},
        "by_kind": _tally(r["pz_kind"] for r in rows),
        "by_reason": _tally(r["no_nutrition_reason"] for r in rows),
        "by_confidence": _tally(r["confidence"] for r in rows),
        "filled": filled, "unfilled": len(rows) - filled,
        "families": families, "families_split": split,
        "guesses": sum(1 for r in rows if r["confidence"] == "guess"),
        "unmapped": len(unmapped), "orphans": len(orphans), "duplicates": duplicates,
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
    parser.add_argument("--map-dir", default=MAP_DIR, help="the mapping directory")
    parser.add_argument("--dataset", default=DATASET_JSON, help="the food dataset JSON")
    args = parser.parse_args(argv)
    if args.seed_map:
        sizes = seed_map(args.map_dir, args.dataset, force=args.force)
        print(json.dumps(sizes))
        return 0
    if args.check_map:
        counts = check_map(args.map_dir, args.dataset, allow_unfilled=args.allow_unfilled)
        return 1 if counts["violations"] else 0
    if args.implied_portion:
        implied_portion(args.implied_portion, args.map_dir, args.dataset, fdc=args.fdc)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
