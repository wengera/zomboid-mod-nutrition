"""x44_beers -- the beer containers for x445b and x447 (Plan 14 Task 5 fix round 3), kept OUT of x44_guide_lib.py, which
is frozen with the runs x441-x446.

THE LIVE FINDING (x445-20261015-175946/drinks.json): of the four beer containers in x44_guide_lib.BEER_CONTAINERS,
Base.BeerBottle and Base.BeerImported are sealed in the item scripts (`OpeningRecipe = OpenBottleOfBeer` on the item and
`Opened = false` in its FluidContainer), so the server's fluid.fill read back 0 L (drinks[2] and drinks[3]: fill.ok
false, litres 0) and those beers never landed; V4_B_decay and V4_B_zero read unmeasured. Base.BeerCan (drinks[1]) and
Base.Pop2 (drinks[4]) filled to 0.300 L of Beer, passed the fill gate and landed.

THE CHOICE: four distinct container types, each a FluidContainer of Capacity 0.3 (the fill's 0.3 L reads back whole:
the fill handler's ok is the amount read back equal to the amount added, PZTestKit_Server.lua fluid.fill), with no
`Opened = false`, no `OpeningRecipe` and no fluid whitelist or blacklist in its component (so addFluid's canAddFluid
takes Beer), prefilled so both sides hold a full copy after the RCON spawn (the client's drink.action needs a non-empty
client copy). BeerCan and Pop2 worked live in x445; Pop and SodaCan carry the same CanPop component as Pop2
(media/scripts/generated/items/normal.txt, read-only). None of the four is one of x447's coffee containers
(WaterBottle, FountainCupWater, Pop3), so each drink still has its own type.

THE PRE-BOOT CHECK (script_check, run by both drivers before any run folder is made): each container's item block in
the install's scripts is read and must hold a FluidContainer of capacity at least BEER_L, no `Opened = false`, no
`OpeningRecipe`, no Whitelist or Blacklist, and the four types must be distinct and apart from the coffee types. The
fill's live read-back is still gated per drink by the lib's fill gate (review M-2).
"""
import os
import re

GAME_ITEMS = os.path.join(r"D:\SteamLibrary\steamapps\common\ProjectZomboid", "media", "scripts", "generated", "items",
                          "normal.txt")
BEERS = ("Base.BeerCan", "Base.Pop2", "Base.Pop", "Base.SodaCan")
BEER_L = 0.3
COFFEES = ("Base.WaterBottle", "Base.FountainCupWater", "Base.Pop3")
LIVE_EVIDENCE = {"Base.BeerCan": "x445-20261015-175946 drinks.json drinks[1].fill (ok, 0.300 L Beer)",
                 "Base.Pop2": "x445-20261015-175946 drinks.json drinks[4].fill (ok, 0.300 L Beer)"}


def item_block(text, full):
    """The item block of `full` (Module.Name) in a script text, and its first line's number, or (None, None)."""
    name = full.split(".", 1)[1]
    m = re.search(r"\n    item " + re.escape(name) + r"\s*\n    \{(.*?)\n    \}", text, re.S)
    if m is None:
        return None, None
    return m.group(1), text.count("\n", 0, m.start()) + 2


def container_check(text, full, litres=BEER_L):
    """One container's script facts and whether a `litres` fill of Beer can read back whole."""
    block, line = item_block(text, full)
    c = {"item": full, "line": line, "found": block is not None}
    if block is None:
        c["ok"] = False
        return c
    cap = re.search(r"Capacity\s*=\s*([\d.]+)", block)
    c["fluid_container"] = "component FluidContainer" in block
    c["capacity"] = float(cap.group(1)) if cap else None
    c["opened_false"] = re.search(r"Opened\s*=\s*false", block) is not None
    c["opening_recipe"] = "OpeningRecipe" in block
    c["fluid_filter"] = re.search(r"\b(Whitelist|Blacklist)\b", block) is not None
    c["prefilled"] = re.search(r"fluid\s*=\s*\w+:", block) is not None
    c["ok"] = (c["fluid_container"] and c["capacity"] is not None and c["capacity"] >= litres - 1e-9
               and not c["opened_false"] and not c["opening_recipe"] and not c["fluid_filter"] and c["prefilled"])
    return c


def script_check(beers=BEERS, path=GAME_ITEMS):
    """The pre-boot check: every beer container passes container_check, the four are distinct and none is a coffee
    container. Returns (checks, ok); an unreadable script is a refusal."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as e:
        return {"error": f"{type(e).__name__}: {e}"}, False
    rows = [container_check(text, b) for b in beers]
    out = {"containers": rows, "distinct": len(set(beers)) == len(beers),
           "apart_from_coffees": not set(beers) & set(COFFEES), "count": len(beers)}
    ok = all(r["ok"] for r in rows) and out["distinct"] and out["apart_from_coffees"] and len(beers) == 4
    return out, ok
