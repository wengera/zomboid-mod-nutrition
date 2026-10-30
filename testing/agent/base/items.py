"""Items by use (Plan 23 Task 9, P23-D): what an item a planner holds or sees is for, read off the food dataset.

This is the fallback: a live `item_added` carries the engine's own `use` (`W.useOf` in `PZAgent_World.lua`), which the
World prefers; the dataset answers for logs written before `item_added.use` and for a container's contents, which the
map names by full type only.

`data/food-items.json` (the 42.21.0 scan, `tools/food_scan.py`) lists its `items` with an `id` (the full type) and a
`kind`: `food`, `drainable` or `fluid_container`. `use_of(full_type)` answers, in this order:

- `food`: the dataset's `kind == "food"` (`FOOD_IDS`), except a food the dataset marks `cant_eat` (a sealed can,
  `CantEat = true`: vanilla's menu never offers its eat, though `ISEatFoodAction:isValid` would run it), which reads
  `other` (Plan 23 fix wave P, I-4);
- `water` (PZA/1.4.1, ruling P24-F; PZA/1.5, the Task 9 amendment): a drinking vessel (`kind == "fluid_container"`,
  `drinkable`, `fluid_capacity` at most `DRINK_CAP_L`) that spawns holding only fluids that quench (`fluid_ids`,
  non-empty, every one in `DRINK_FLUIDS`: `WATER_FLUIDS`, or a dataset fluid in the `Beverage` category, neither
  `Hazardous` nor `Alcoholic`, without a poison block, whose `thirst_change` is below 0: a pop, a juice, a milk, a
  coffee) (`DRINK_IDS`), as the Lua's `W.drinkable` reads the engine's `isWaterSource` or a quenching beverage
  (TaintedWater left out: Hazardous, a poison). A Disinfectant (RubbingAlcohol), a bleach, a beer or a spirit is not
  water: F2 drank a Disinfectant 68 times with no thirst fall. A sealed can (tagged `SEALED_TAG`, `Base.Pop`,
  `Base.Pop2`) is not water either (PZA/1.5.1, Task 9 review minor 2): it spawns sealed, its `canPlayerEmpty()`
  false, which vanilla's drink menu refuses and the Lua's `W.drinkable` reads, so it reads `other`;
- `container` (PZA/1.4.1): a drinking vessel that spawns empty (no `fluid_ids`: `Base.PopEmpty`, `Base.Mugl`,
  `Base.Bowl`, `Base.GlassTumbler`), as the Lua's `W.waterVessel` reads an empty one that may hold water; checked
  after `weapon`, as the Lua's own order reads a saucepan;
- `bandage` (PZA/1.5.1, Task 9 review minor 5): a full type in `BANDAGE_IDS`, the items whose script sets
  `CanBandage = true` (the 42.21 install's `media/scripts/generated/items/normal.txt`), as the Lua's `W.useOf` reads
  `isCanBandage()`: the rags `rip` makes (`Base.RippedSheets`) and `wash` cleans read bandage, a `Base.Rag`, a
  `Base.RagFilter` or a `Base.BandageBox` does not;
- `weapon`: a full type `WEAPON_RX` matches. The dataset names no weapon (its two `base:weapon` items are saucepans,
  fluid containers), so the weapon rule stays this name guess until a weapon dataset exists;
- `other`: everything else, a name the dataset does not carry and a non-drinkable or poison container included
  (`Base.PetrolCan`, the buckets).

`clothing` (PZA/1.6, Plan 24 Task 9 fix 9, review-t18 ruling 5) is a use the engine answers live only (`W.useOf`: the
item's class is `Clothing`, with its `clothing` record of protection on `item_added` and `item_changed`); the food
dataset carries no garment, so `use_of` never answers it and a log written before PZA/1.6 reads a garment `other`.

`garment(full_type)` (PZA/1.6, Plan 24 Task 24) is the name guess a container's items are read by for the `clothing`
loot (a map line names full types only and no dataset carries a garment): the type names a jacket, hoodie, vest,
shirt, trousers, shorts, skirt, dress, socks, shoes, boots, gloves, hat, jumper, sweater, tracksuit, boilersuit, coat,
apron, scarf or helmet. It is a guess the Lua's `clothing` filter (the item's class is Clothing) corrects: a miss takes
nothing and marks the container (`no match`); it never reaches `use_of`, which stays the dataset's answer.

`days_fresh(full_type)` is the dataset's `days_fresh` (None for a food that never spoils, or a name it does not carry):
the need's pick among foods, the most perishable first (fix wave P, I-4).

The dataset is read once (`functools.lru_cache` on the loader), from the repository root resolved off this file.
"""
import functools
import json
import os
import re

USES = ("food", "water", "weapon", "bandage", "other", "container", "clothing")   # PZA/1.6: clothing, live only
WATER_FLUIDS = frozenset({"Water", "CarbonatedWater"})   # the jar's isWaterSource fluids, TaintedWater left out
DRINK_CAP_L = 3.0      # litres: vanilla's drink menu refuses a larger container (the Lua's W.DRINK_CAP_L)
DATASET = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "food-items.json"))
WEAPON_RX = re.compile(r"\.(BaseballBat|Hammer|Axe|Crowbar|Knife|Pan|Pistol|Shotgun|Rifle)\b")
GARMENT_RX = re.compile(r"\.(Jacket|Hoodie|Vest|Shirt|Tshirt|TShirt|Trousers|Shorts|Skirt|Dress|Socks|Shoes|Boots|Gloves|"
                        r"Hat|Jumper|Sweater|Tracksuit|Boilersuit|Coat|Apron|Scarf|Helmet)(_|$)")   # garment()'s name guess
SEALED_TAG = "base:sealedbeveragecan"   # the sealed pop cans' tag: spawned canPlayerEmpty false, never drunk
# every item whose script sets CanBandage = true (the 42.21 install, media/scripts/generated/items/normal.txt L8046-
# L10691), as the engine's isCanBandage() reads it
BANDAGE_IDS = frozenset("Base." + n for n in (
    "AlcoholBandage", "AlcoholRippedSheets", "Bandage", "BandageDirty", "Bandaid", "DenimStrips", "DenimStripsDirty",
    "LeatherStrips", "LeatherStripsDirty", "RippedSheets", "RippedSheetsDirty"))


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


def _quenches(fluid):
    """A dataset fluid a character drinks for thirst: a Beverage, neither Hazardous nor Alcoholic, with no poison block
    and a thirst change below 0."""
    cats = fluid.get("categories") or ()
    thirst = fluid.get("thirst_change")
    return ("Beverage" in cats and "Hazardous" not in cats and "Alcoholic" not in cats and not fluid.get("poison")
            and isinstance(thirst, (int, float)) and thirst < 0)


def _water(item):
    ids = item.get("fluid_ids") or ()
    return (_vessel(item) and bool(ids) and all(f in DRINK_FLUIDS for f in ids)
            and SEALED_TAG not in (item.get("tags") or ()))


_ITEMS, _FLUIDS = dataset()
DRINK_FLUIDS = WATER_FLUIDS | frozenset(i for i, f in _FLUIDS.items() if _quenches(f))
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
    if ft in BANDAGE_IDS:
        return "bandage"
    if WEAPON_RX.search(ft):
        return "weapon"
    if ft in VESSEL_IDS:
        return "container"
    return "other"


def garment(full_type):
    """Whether the full type's name reads a garment (GARMENT_RX), the `clothing` loot's guess of a container's item."""
    return bool(GARMENT_RX.search(full_type or ""))


def holds_use(full_type, use):
    """Whether a container item of `full_type` counts as `use` for a loot: `use_of`'s answer, and for `clothing` (which
    `use_of` never answers) `garment`'s guess."""
    return garment(full_type) if use == "clothing" else use_of(full_type) == use


def days_fresh(full_type):
    """The dataset's `days_fresh` of a full type, else None."""
    v = (_ITEMS.get(full_type or "") or {}).get("days_fresh")
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
