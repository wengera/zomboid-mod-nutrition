"""Items by use (Plan 23 Task 9, P23-D): what an item a planner holds or sees is for, read off the food dataset.

This is the fallback: a live `item_added` carries the engine's own `use` (`W.useOf` in `PZAgent_World.lua`), which the
World prefers; the dataset answers for logs written before `item_added.use` and for a container's contents, which the
map names by full type only.

`data/food-items.json` (the 42.21.0 scan, `tools/food_scan.py`) lists its `items` with an `id` (the full type) and a
`kind`: `food`, `drainable` or `fluid_container`. `use_of(full_type)` answers, in this order:

- `food`: the dataset's `kind == "food"` (`FOOD_IDS`), except a food the dataset marks `cant_eat` (a sealed can,
  `CantEat = true`: vanilla's menu never offers its eat, though `ISEatFoodAction:isValid` would run it), which reads
  `other` (Plan 23 fix wave P, I-4);
- `water` (PZA/1.4.1, ruling P24-F): a drinking vessel (`kind == "fluid_container"`, `drinkable`, `fluid_capacity`
  at most `DRINK_CAP_L`) that spawns holding water only, every fluid it names (`fluid_ids`, non-empty) one of
  `WATER_FLUIDS` (`DRINK_IDS`), as the Lua's `W.drinkable` reads the engine's `isWaterSource` (TaintedWater left out,
  a poison). A Disinfectant (RubbingAlcohol), a pop, a bleach or a juice is not water: F2 drank a Disinfectant 68
  times with no thirst fall;
- `container` (PZA/1.4.1): a drinking vessel that spawns empty (no `fluid_ids`: `Base.PopEmpty`, `Base.Mugl`,
  `Base.Bowl`, `Base.GlassTumbler`), as the Lua's `W.waterVessel` reads an empty one that may hold water; checked
  after `weapon`, as the Lua's own order reads a saucepan;
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

USES = ("food", "water", "weapon", "bandage", "other", "container")
WATER_FLUIDS = frozenset({"Water", "CarbonatedWater"})   # the jar's isWaterSource fluids, TaintedWater left out
DRINK_CAP_L = 3.0      # litres: vanilla's drink menu refuses a larger container (the Lua's W.DRINK_CAP_L)
DATASET = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "food-items.json"))
WEAPON_RX = re.compile(r"\.(BaseballBat|Hammer|Axe|Crowbar|Knife|Pan|Pistol|Shotgun|Rifle)\b")
BANDAGE_WORDS = ("Bandage", "Rag")


@functools.lru_cache(maxsize=None)
def dataset():
    """The dataset's `(items, fluids)`, each keyed by id, read once."""
    with open(DATASET, encoding="utf-8") as f:
        d = json.load(f)
    return ({it["id"]: it for it in d["items"]}, {fl["id"]: fl for fl in d.get("fluids") or ()})


def _vessel(item):
    """A container a character drinks from: a drinkable fluid container of at most DRINK_CAP_L litres."""
    cap = item.get("fluid_capacity")
    return (item.get("kind") == "fluid_container" and bool(item.get("drinkable"))
            and isinstance(cap, (int, float)) and cap <= DRINK_CAP_L)


def _water(item):
    ids = item.get("fluid_ids") or ()
    return _vessel(item) and bool(ids) and all(f in WATER_FLUIDS for f in ids)


_ITEMS, _FLUIDS = dataset()
FOOD_IDS = frozenset(i for i, it in _ITEMS.items() if it.get("kind") == "food" and not it.get("cant_eat"))
DRINK_IDS = frozenset(i for i, it in _ITEMS.items() if _water(it))
VESSEL_IDS = frozenset(i for i, it in _ITEMS.items() if _vessel(it) and not it.get("fluid_ids"))


def cant_eat(full_type):
    """Whether the dataset marks the full type `cant_eat` (a sealed can): the engine's `IsFood` is true of it, the menu
    never offers its eat."""
    return bool((_ITEMS.get(full_type or "") or {}).get("cant_eat"))


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
    if ft in VESSEL_IDS:
        return "container"
    return "other"


def days_fresh(full_type):
    """The dataset's `days_fresh` of a full type, else None."""
    v = (_ITEMS.get(full_type or "") or {}).get("days_fresh")
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
