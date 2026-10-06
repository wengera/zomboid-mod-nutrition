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


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="The item-pass pipeline: vanilla foods joined to FDC SR Legacy nutrient vectors "
                    "(Plan 6). This build carries the join core only; the later flags land with "
                    "their tasks.")
    parser.parse_args(argv)
    parser.print_help()


if __name__ == "__main__":
    main()
