"""The food hedonics table (Plan 19 Task 5; spec docs/superpowers/specs/2026-10-21-dials-and-hedonics-design.md section
B.2, rulings R1 and R4 of the task's amendments).

    python tools/food_hedonics.py --check     exit 1 when the generated file differs from a fresh classification
    python tools/food_hedonics.py --write     regenerate it
    python tools/food_hedonics.py --list      print the plain foods and the class counts

The generated file is mod/NutritionRevamp/common/media/lua/shared/NR_Data_Hedonics.lua (NR.data.hedonics): per food
type, whether it is plain energy (R1) and its taste class (R4). The server reads it at the eat (Task 6); nothing is
classified per eat. A generated file is never edited by hand: a hedonics dial changed through tools/dials.py set is
followed by --write.

Each food of data/food-nutrients.json with a per-100 g record is classified by the kernel's own rules on the lupa host
(NR_Core.lua, the dial registry and the NR_Kernel*.lua files, as the kernel tests load them), so the table, the budget
oracle (tools/hedonics_budget.py) and the kernel read one rule:
- plain: K.hedonics.isPlain over the per-100 g protein, carbohydrate and fat grams, the sodium as % by weight (its mg a
  100 g over 1000), the kcal a 100 g and vanilla's UnhappyChange (data/food-items.json unhappy_change, 0 when unset);
- class: K.hedonics.tasteClass over the same grams, the monotony staple rule (K.monotony.isStaple of the full type and
  data/food-items.json food_type) and a sweet reading: the FoodType is one of SWEET_FOOD_TYPES, the item carries the
  base:sugar tag, or its FDC description names a sweet word (SWEET_WORDS, whole words). The data carries no sugars, so
  the sweet reading is the item's kind, a game choice of this tool.
"""
import argparse
import difflib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
KERNEL_TESTS = os.path.join(REPO, "testing", "tests", "kernel")
if KERNEL_TESTS not in sys.path:
    sys.path.insert(0, KERNEL_TESTS)
OUT_LUA = os.path.join(SHARED, "NR_Data_Hedonics.lua")
NUTRIENTS_JSON = os.path.join(REPO, "data", "food-nutrients.json")
ITEMS_JSON = os.path.join(REPO, "data", "food-items.json")

SWEET_FOOD_TYPES = ("Candy", "Fruits", "Berry", "Sugar", "Citrus", "Juice", "Chocolate", "Cocoa")
SWEET_TAG = "base:sugar"
CANDY_UNHAPPY = -1.0  # a game choice of the tool: an FDC candy record reads as a treat (Task 5 fix 1, F1)
SWEET_WORDS = ("candies", "candy", "candied", "chocolate", "cookie", "cookies", "cake", "cakes", "pie", "pies", "muffin",
               "muffins", "doughnut", "doughnuts", "donut", "pastry", "pastries", "syrup", "honey", "jam", "jams", "jelly",
               "jellies", "marmalade", "sugar", "sugars", "ice cream", "pudding", "frosting", "brownie", "brownies",
               "dessert", "desserts", "marshmallows", "gum", "fruit", "juice", "sweetened")
SWEET_RX = re.compile(r"\b(?:%s)\b" % "|".join(re.escape(w) for w in SWEET_WORDS), re.I)


def runtime():
    """A Lua 5.1 runtime with the shared code loaded as the kernel tests' host loads it (server_host: its stub environment,
    NR_Core.lua first, then every shared NR_*.lua in sorted order, the registry before the kernels)."""
    import lupa.lua51 as lua51
    import server_host
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(server_host.ENV)
    for path in server_host._shared_files():
        server_host._load(rt, path)
    return rt


def _items():
    with open(ITEMS_JSON, encoding="utf-8") as fh:
        return {it["id"]: it for it in json.load(fh)["items"]}


def _foods():
    with open(NUTRIENTS_JSON, encoding="utf-8") as fh:
        return json.load(fh)["items"]


def sweet(item, food):
    """The sweet reading of a food (the module docstring): its FoodType, its base:sugar tag or its FDC description."""
    if item.get("food_type") in SWEET_FOOD_TYPES:
        return True
    if SWEET_TAG in (item.get("tags") or []):
        return True
    return SWEET_RX.search(food.get("fdc_description") or "") is not None


def inputs(food, item):
    """The classifier's inputs of one food: (p, c, l, naPct, kcal100, unhappy, foodType), or None when the food has no
    per-100 g calories."""
    g = food.get("per_100g") or {}
    if g.get("calories") is None:
        return None
    unhappy = float(item.get("unhappy_change") or 0)
    if (food.get("fdc_description") or "").startswith("Candies,"):
        # an FDC candy record is a treat whatever vanilla scores the item (CandyPackage 0, its HardCandies -10)
        unhappy = min(unhappy, CANDY_UNHAPPY)
    return (float(g.get("proteins") or 0.0), float(g.get("carbs") or 0.0), float(g.get("lipids") or 0.0),
            float(g.get("sodium") or 0.0) / 1000.0, float(g["calories"]), unhappy, item.get("food_type"))


def classify(rt=None):
    """{fullType: (plain, class)} for every food of the nutrient data with a per-100 g record, by the kernel's rules."""
    rt = rt or runtime()
    K = rt.globals().NutritionRevamp.kernel
    items = _items()
    out = {}
    for food in _foods():
        ft = food["pz_id"]
        item = items.get(ft, {})
        x = inputs(food, item)
        if x is None:
            continue
        p, c, l, na, kcal100, unhappy, food_type = x
        plain = bool(K.hedonics.isPlain(p, c, l, na, kcal100, unhappy))
        staple = bool(K.monotony.isStaple(ft, food_type))
        out[ft] = (plain, str(K.hedonics.tasteClass(p, c, l, staple, sweet(item, food))))
    return out


def render(table):
    plain = sum(1 for v in table.values() if v[0])
    lines = [
        "-- NR_Data_Hedonics.lua -- not a kernel file: the food hedonics table (Plan 19 Task 5) and its loader.",
        "-- GENERATED by tools/food_hedonics.py from data/food-nutrients.json, data/food-items.json and the kernel's rules",
        "-- (K.hedonics.isPlain, K.hedonics.tasteClass, K.monotony.isStaple at the registry's hedonics dials); do not edit --",
        "-- regenerate with --write. Each entry is { plain, class }: whether the food is plain energy (R1) and its taste class",
        "-- (R4: sweet, savoury, fatty or staple). %d types, %d plain. A reader goes through the loader, never the table." % (len(table), plain),
        "local NR = NutritionRevamp",
        "NR.data = NR.data or {}",
        "NR.data.hedonics = {}",
        "",
        "local FOODS = {",
    ]
    for ft in sorted(table):
        p, cls = table[ft]
        lines.append('    ["%s"] = { %s, "%s" },' % (ft, "true" if p else "false", cls))
    lines += [
        "}",
        "",
        "-- Whether a type is plain energy and its taste class; false and nil for a type the table does not carry.",
        "function NR.data.hedonics.get(fullType)",
        "    local e = FOODS[fullType]",
        "    if e == nil then",
        "        return false, nil",
        "    end",
        "    return e[1], e[2]",
        "end",
        "",
    ]
    return "\n".join(lines)


def generate():
    return render(classify())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="exit 1 when NR_Data_Hedonics.lua differs from a fresh classification")
    g.add_argument("--write", action="store_true", help="regenerate NR_Data_Hedonics.lua")
    g.add_argument("--list", action="store_true", help="print the plain foods and the class counts")
    a = ap.parse_args(argv)
    if a.list:
        table = classify()
        for ft in sorted(t for t, v in table.items() if v[0]):
            print("plain  %-40s %s" % (ft, table[ft][1]))
        counts = {}
        for _, cls in table.values():
            counts[cls] = counts.get(cls, 0) + 1
        print("classes: %s" % ", ".join("%s %d" % (k, counts[k]) for k in sorted(counts)))
        return 0
    text = generate()
    if a.write:
        with open(OUT_LUA, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("food_hedonics: wrote %s" % os.path.relpath(OUT_LUA, REPO))
        return 0
    try:
        with open(OUT_LUA, encoding="utf-8", newline="") as fh:
            cur = fh.read()
    except OSError:
        cur = ""
    if cur == text:
        print("food_hedonics: in sync")
        return 0
    diff = difflib.unified_diff(cur.splitlines(), text.splitlines(), "committed", "fresh", lineterm="", n=0)
    for i, line in enumerate(diff):
        if i >= 40:
            print("...")
            break
        print(line)
    print("food_hedonics: out of sync; regenerate with --write")
    return 1


if __name__ == "__main__":
    sys.exit(main())
