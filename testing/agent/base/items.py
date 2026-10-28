"""Items by use (Plan 23 Task 9, P23-D): what an item a planner holds or sees is for, read off the food dataset.

`data/food-items.json` (the 42.21.0 scan, `tools/food_scan.py`) lists its `items` with an `id` (the full type) and a
`kind`: `food`, `drainable` or `fluid_container`. `use_of(full_type)` answers, in this order:

- `food`: the dataset's `kind == "food"` (`FOOD_IDS`);
- `water`: the dataset's `kind == "fluid_container"` (`DRINK_IDS`): any fluid container the character can drink from,
  whatever its name or its fill (the Lua refuses an undrinkable or empty one; the World's `mark_empty` remembers that);
- `bandage`: a full type holding `Bandage` or `Rag`, the Lua loot's own rule (`PZAgent_SkillsWorld.lua`, `bandage`);
- `weapon`: a full type `WEAPON_RX` matches. The dataset names no weapon (its two `base:weapon` items are saucepans,
  fluid containers), so the weapon rule stays this name guess until a weapon dataset exists;
- `other`: everything else, a name the dataset does not carry included.

The dataset is read once (`functools.lru_cache` on the loader), from the repository root resolved off this file.
"""
import functools
import json
import os
import re

USES = ("food", "water", "weapon", "bandage", "other")
DATASET = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "food-items.json"))
WEAPON_RX = re.compile(r"\.(BaseballBat|Hammer|Axe|Crowbar|Knife|Pan|Pistol|Shotgun|Rifle)")
BANDAGE_WORDS = ("Bandage", "Rag")


@functools.lru_cache(maxsize=None)
def kinds():
    """{full type: kind} for every item of the dataset, read once."""
    with open(DATASET, encoding="utf-8") as f:
        return {it["id"]: it.get("kind") for it in json.load(f)["items"]}


FOOD_IDS = frozenset(i for i, k in kinds().items() if k == "food")
DRINK_IDS = frozenset(i for i, k in kinds().items() if k == "fluid_container")


def use_of(full_type):
    """The use of an item by its full type: one of USES."""
    ft = full_type or ""
    if ft in FOOD_IDS:
        return "food"
    if ft in DRINK_IDS:
        return "water"
    if any(w in ft for w in BANDAGE_WORDS):
        return "bandage"
    if WEAPON_RX.search(ft):
        return "weapon"
    return "other"
