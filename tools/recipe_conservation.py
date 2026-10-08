#!/usr/bin/env python3
"""Which food recipes create or destroy energy (Plan 11 Task 16; Decision 7 item 5), measured offline over
data/recipes.json (the recipe scan; 42.21.0 since Plan 11a Task R) with the item pass's re-based per-item macros.

Every line is costed by tools/recipe_scan.py's own accounting, never a second one: `nutrition_delta` sums what a
craft moves (outputs x item count minus what each consumed input really costs) and refuses a recipe it cannot weigh.
The rules it applies are docs/facts/cooking-and-recipes.md's: an input's N counts uses, one use one raw HungerChange
point (#0701), so N / |HungerChange| of an item; a food with no usable HungerChange costs N whole items (#0702); a
`flags[ItemCount]` line costs N whole items (#0700); a drainable input is charged no macros (#0703); a `mode:destroy`
line is charged up to the whole items RemoveItem deletes (#0704); a `mode:keep` line costs nothing (#0699); an
`InheritFood` input makes the craft a split whose delta is 0 by construction (#0706).

The food table is data/food-items.json's rows (kind, HungerChange and nutrition_basis exactly as the game loads
them: the item pass never writes HungerChange) with the four macros replaced by data/food-nutrients.json's re-based
per_item values wherever the item pass maps the item; an unmapped item keeps its vanilla macros, as the game does.

A recipe's class (Plan 11 ruling 11): `inherits` for a split; else `creates` when its outputs carry more than CREATE x
its inputs' calories, `destroys` under DESTROY x, else `conserves`. A recipe recipe_scan refuses is counted in
`skipped` under its first blocker's reason; one whose inputs include a drainable (charged nothing) is skipped as
`drainable`, because its inputs cannot be weighed.

A recipe whose `OnCreate` is a Java craft function that writes food values onto a created item (#3507; and
`openMacAndCheese`, read on 42.21 for Plan 11a Task 16) is weighed at what that Java leaves: `makeOmelette` and
`makeJar` (`copyFoodValuesFromList`, the consumed foods' values summed onto the output) are `inherits`;
`cutChicken` multiplies every created cut's macros by the bird's hunger over the cuts' summed hungers
(`RecipeCodeOnCreate.cutChicken @88-@233 L1145-L1157`); `openMacAndCheese` overwrites the first created
`base:pasta` item with a sixth of its own values (`@0-@20 L1313-L1314` -> `Food.copyFoodFromSplit` ->
`copyNutritionFromSplit`, 1/6); `makeCoffee` writes hunger only, so its outputs keep their script macros;
`cutFish` and `cutSmallAnimal` are not modelled and their recipes are skipped as `java-unmodelled`.
A row's `split` is true when exactly one consumed input line feeds two or more output items (a carcass cut, a
loaf sliced, a pack opened), the shape Decision 7 asks to conserve.

    python tools/recipe_conservation.py            print the creators and destroyers
    python tools/recipe_conservation.py --write    write data/recipe-conservation.json and NR_Data_Recipes.lua
    python tools/recipe_conservation.py --check    exit 1 when either file is out of date
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recipe_scan as rs  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(REPO, "data", "recipes.json")
ITEMS = rs.FOOD_JSON
FOODS = os.path.join(REPO, "data", "food-nutrients.json")
OUT_JSON = os.path.join(REPO, "data", "recipe-conservation.json")
OUT_LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Data_Recipes.lua")
CREATE = 1.10
DESTROY = 0.90
# data/food-nutrients.json's per_item key -> data/food-items.json's field (recipe_scan.FOOD_FIELDS' values)
REBASED = (("calories", "calories"), ("carbs", "carbohydrates"), ("lipids", "lipids"), ("proteins", "proteins"))
MACRO_KEYS = ("Calories", "Carbohydrates", "Lipids", "Proteins")
JAVA = "RecipeCodeOnCreate."
JAVA_INHERITS = (JAVA + "makeOmelette", JAVA + "makeJar")       # copyFoodValuesFromList (#3507)
JAVA_HUNGER_SCALE = JAVA + "cutChicken"                         # every cut x bird hunger / cuts' hunger
JAVA_PASTA_SPLIT = (JAVA + "openMacAndCheese", "base:pasta", 6)  # the first pasta output x 1/6
JAVA_MACROS_KEPT = (JAVA + "makeCoffee",)                       # writes hunger only
JAVA_UNMODELLED = (JAVA + "cutFish", JAVA + "cutSmallAnimal")


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def rebased_food(items, foods):
    """{id: row}: each data/food-items.json row, its four macros the item pass's per_item values where it maps one."""
    per = {}
    for row in foods["items"]:
        p = row.get("per_item") or {}
        if row.get("basis") == "per_item" and isinstance(p.get("calories"), (int, float)):
            per[row["pz_id"]] = p
    out = {}
    for row in items["items"]:
        r = dict(row)
        p = per.get(row["id"])
        if p is not None:
            for src, dst in REBASED:
                if isinstance(p.get(src), (int, float)):
                    r[dst] = p[src]
        out[row["id"]] = r
    return out


def outputs_total(recipe, food, key):
    """An output's N is always an item count (recipe_scan.nutrition_delta); a split's outputs weigh 0 there."""
    if rs.split_lines(recipe):
        return 0.0
    total = 0.0
    for line in rs.io_lines(recipe, "outputs"):
        if line["kind"] == "item":
            v = rs.food_value(food[line["types"][0]], key)
            total += (v or 0.0) * line["amount"]
    return total


def consumed_inputs(recipe):
    """The consumed item input lines (every line recipe_scan charges), sub-lines and tools left out."""
    return [line for line in rs.io_lines(recipe, "inputs") if line["kind"] == "item" and line["consumed"]]


def is_split(recipe):
    """One consumed input line feeding two or more output items: a carcass cut, a loaf sliced, a pack opened."""
    items = sum(line["amount"] or 0.0 for line in rs.io_lines(recipe, "outputs") if line["kind"] == "item")
    return len(consumed_inputs(recipe)) == 1 and items >= 2


def _hunger(row):
    v = rs.food_value(row, "HungerChange")
    return abs(v) if isinstance(v, (int, float)) else None


def java_scale(recipe, food, kout):
    """kout after the recipe's Java OnCreate (the module docstring), or None when the Java leaves it as built."""
    fn = recipe.get("onCreate")
    if fn == JAVA_HUNGER_SCALE:
        ins = [_hunger(food[line["types"][0]]) for line in consumed_inputs(recipe)]
        outs = [(_hunger(food[line["types"][0]]), line["amount"]) for line in rs.io_lines(recipe, "outputs")
                if line["kind"] == "item"]
        if len(ins) != 1 or ins[0] is None or any(h is None for h, _n in outs):
            return None
        scale = ins[0] / sum(h * n for h, n in outs)
        return {f: v * scale for f, v in kout.items()}
    if fn == JAVA_PASTA_SPLIT[0]:
        for line in rs.io_lines(recipe, "outputs"):
            row = food[line["types"][0]] if line["kind"] == "item" else None
            if row is not None and JAVA_PASTA_SPLIT[1] in (rs.food_value(row, "Tags") or ()):
                drop = 1.0 - 1.0 / JAVA_PASTA_SPLIT[2]          # one instance keeps a sixth of itself
                return {f: kout[f] - (rs.food_value(row, k) or 0.0) * drop
                        for k, f in rs.MACROS if k in MACRO_KEYS}
        return None
    return None


def weigh(recipe, food):
    """(row, None) for a recipe recipe_scan can weigh, else (None, the reason it is skipped)."""
    d = rs.nutrition_delta(recipe, food)
    if "reason" in d:
        return None, d["blockers"][0]["why"] if d["blockers"] else d["reason"]
    if any(n.startswith("drainable input") for n in d["notes"]):
        return None, "drainable"
    fn = recipe.get("onCreate")
    if fn in JAVA_UNMODELLED:
        return None, "java-unmodelled"
    kin, kout = {}, {}
    for key, field in rs.MACROS:
        if key in MACRO_KEYS:
            kout[field] = outputs_total(recipe, food, key)
            kin[field] = kout[field] - d[field]                # delta = outputs - what the inputs cost
    java = fn if fn and fn.startswith(JAVA) and (fn in JAVA_INHERITS or fn in JAVA_MACROS_KEPT
                                                 or fn in (JAVA_HUNGER_SCALE, JAVA_PASTA_SPLIT[0])) else None
    scaled = java_scale(recipe, food, kout)
    if scaled is not None:
        kout = scaled
    ratio = round(kout["calories"] / kin["calories"], 6) if kin["calories"] > 0 else None
    ratios = {f: round(kout[f] / kin[f], 6) for f in kin if kin[f] > 0 and kout[f] > 0}
    if rs.split_lines(recipe) or fn in JAVA_INHERITS:
        cls = "inherits"
    elif ratio is None:
        cls = "creates" if kout["calories"] > 0 else "conserves"
    elif ratio > CREATE:
        cls = "creates"
    elif ratio < DESTROY:
        cls = "destroys"
    else:
        cls = "conserves"
    return {"recipe": recipe["name"], "kcal_in": round(kin["calories"], 3), "kcal_out": round(kout["calories"], 3),
            "ratio": ratio, "macro_ratios": ratios, "notes": d["notes"], "class": cls, "java": java,
            "split": is_split(recipe)}, None


def measure(recipes, food):
    rows, skipped = [], {}
    for rec in recipes:
        row, why = weigh(rec, food)
        if row is None:
            skipped[why] = skipped.get(why, 0) + 1
        else:
            rows.append(row)
    rows.sort(key=lambda r: r["recipe"])
    return rows, skipped


def creators(rows):
    """{recipe: the inputs' kcal over the outputs'} for each creator with input energy (one with none is reported,
    never scaled: a factor of 0 would empty its outputs)."""
    return {r["recipe"]: r["kcal_in"] / r["kcal_out"] for r in rows if r["class"] == "creates" and r["kcal_in"] > 0}


CLASSES = ("conserves", "creates", "destroys", "inherits")


def emit_json(rows, skipped):
    """The rows, with meta.classes (every weighed recipe by class) and meta.splits (the split rows by class)."""
    classes = {c: sum(1 for r in rows if r["class"] == c) for c in CLASSES}
    splits = {c: sum(1 for r in rows if r["class"] == c and r["split"]) for c in CLASSES}
    return json.dumps({"meta": {"tool": "tools/recipe_conservation.py", "create": CREATE, "destroy": DESTROY,
                                "skipped": skipped, "classes": classes, "splits": splits}, "recipes": rows},
                      indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def emit_lua(rows):
    out = ["-- NR_Data_Recipes.lua -- not a kernel file: the craft-time conservation factors (Plan 11 Task 17).",
           "-- GENERATED by tools/recipe_conservation.py from data/recipes.json and the item pass's data; do not",
           "-- edit -- regenerate with --write. factor[recipe] = the inputs' kcal over the outputs' kcal, for each",
           "-- recipe whose re-based outputs carry more than %.2f x their inputs' energy (ruling 11)." % CREATE,
           "local NR = NutritionRevamp",
           "NR.data = NR.data or {}",
           "NR.data.recipes = { factor = {"]
    for name, f in sorted(creators(rows).items()):
        out.append('    ["%s"] = %s,' % (name, repr(round(f, 6))))
    out.append("} }")
    return "\n".join(out) + "\n"


def texts():
    food = rebased_food(load_json(ITEMS), load_json(FOODS))
    rows, skipped = measure(load_json(RECIPES)["recipes"], food)
    return [(OUT_JSON, emit_json(rows, skipped)), (OUT_LUA, emit_lua(rows))], rows, skipped


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--write", action="store_true")
    p.add_argument("--check", action="store_true")
    ns = p.parse_args(argv)
    files, rows, skipped = texts()
    if ns.check:
        stale = []
        for path, text in files:
            on_disk = open(path, encoding="utf-8", newline="").read() if os.path.exists(path) else None
            if on_disk != text:
                stale.append(path)
        for path in stale:
            print("recipe_conservation: stale %s; regenerate with --write" % path, file=sys.stderr)
        return 1 if stale else 0
    if ns.write:
        for path, text in files:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            print("wrote %s" % path)
        return 0
    for r in rows:
        if r["class"] in ("creates", "destroys"):
            print("%-28s %-9s %9.1f -> %9.1f kcal (x%s)" % (r["recipe"], r["class"], r["kcal_in"], r["kcal_out"],
                                                         r["ratio"]))
    print("skipped: %s" % json.dumps(skipped, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
