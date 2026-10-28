"""Items by use (Plan 23 Task 9, P23-D): what an item a planner holds or sees is for, read off the food dataset.

This is the fallback: a live `item_added` carries the engine's own `use` (`W.useOf` in `PZAgent_World.lua`), which the
World prefers; the dataset answers for logs written before `item_added.use` and for a container's contents, which the
map names by full type only.

`data/food-items.json` (the 42.21.0 scan, `tools/food_scan.py`) lists its `items` with an `id` (the full type) and a
`kind`: `food`, `drainable` or `fluid_container`. `use_of(full_type)` answers, in this order:

- `food`: the dataset's `kind == "food"` (`FOOD_IDS`), except a food the dataset marks `cant_eat` (a sealed can,
  `CantEat = true`: vanilla's menu never offers its eat, though `ISEatFoodAction:isValid` would run it), which reads
  `other` (Plan 23 fix wave P, I-4);
- `water`: a `kind == "fluid_container"` item the dataset marks `drinkable`, unless every fluid it names
  (`fluid_ids`, non-empty) is one whose `fluids` record carries `poison` (Bleach, HairDye, TaintedWater, ...)
  (`DRINK_IDS`). A container named `...Empty` (`Base.PopEmpty`, `Base.BeerEmpty`) is a drinkable container in the
  dataset and reads water whatever its fill: the Lua refuses an empty one and the World's `mark_empty` remembers it;
- `bandage`: a full type holding `Bandage` or `Rag`, the Lua loot's own rule (`PZAgent_SkillsWorld.lua`, `bandage`),
  so `Base.RagFilter` reads bandage as the Lua reads it;
- `weapon`: a full type `WEAPON_RX` matches. The dataset names no weapon (its two `base:weapon` items are saucepans,
  fluid containers), so the weapon rule stays this name guess until a weapon dataset exists;
- `other`: everything else, a name the dataset does not carry and a non-drinkable or poison container included
  (`Base.PetrolCan`, the buckets).

`days_fresh(full_type)` is the dataset's `days_fresh` (None for a food that never spoils, or a name it does not carry):
the need's pick among foods, the most perishable first (fix wave P, I-4).

The dataset is read once (`functools.lru_cache` on the loader), from the repository root resolved off this file.
"""
import functools
import json
import os
import re

USES = ("food", "water", "weapon", "bandage", "other")
DATASET = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "food-items.json"))
WEAPON_RX = re.compile(r"\.(BaseballBat|Hammer|Axe|Crowbar|Knife|Pan|Pistol|Shotgun|Rifle)\b")
BANDAGE_WORDS = ("Bandage", "Rag")


@functools.lru_cache(maxsize=None)
def dataset():
    """The dataset's `(items, fluids)`, each keyed by id, read once."""
    with open(DATASET, encoding="utf-8") as f:
        d = json.load(f)
    return ({it["id"]: it for it in d["items"]}, {fl["id"]: fl for fl in d.get("fluids") or ()})


def _poison_only(item, fluids):
    """Whether every fluid the item names is a poison (an item naming none is not)."""
    ids = item.get("fluid_ids") or ()
    return bool(ids) and all((fluids.get(f) or {}).get("poison") for f in ids)


def _drinkable(item, fluids):
    return item.get("kind") == "fluid_container" and bool(item.get("drinkable")) and not _poison_only(item, fluids)


_ITEMS, _FLUIDS = dataset()
FOOD_IDS = frozenset(i for i, it in _ITEMS.items() if it.get("kind") == "food" and not it.get("cant_eat"))
DRINK_IDS = frozenset(i for i, it in _ITEMS.items() if _drinkable(it, _FLUIDS))


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


def days_fresh(full_type):
    """The dataset's `days_fresh` of a full type, else None."""
    v = (_ITEMS.get(full_type or "") or {}).get("days_fresh")
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
