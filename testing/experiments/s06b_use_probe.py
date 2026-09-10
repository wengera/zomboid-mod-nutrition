"""Slice 06, task 4b: the live use probe -- what consuming N *uses* of a food actually does
to it.

`data/recipes.json`'s nutrition deltas rest on one rule, and until this run every word of it
was a jar reading (`.superpowers/sdd/06-recipes/q-itemcount-notes.md`, grade C throughout).
A `craftRecipe` input line WITHOUT `flags[ItemCount]` charges N **uses**, and for a `Food`
one use is one raw `HungerChange` point:

    CraftRecipeData.processDestroyAndUsedItems @453 L576
        ItemUser.UseItem(item, true, false, ceil(remaining), keep, destroy)
    ItemUser.UseItem     @18     L34          used = Math.min(item.getCurrentUses(), count)
                         @28-@41 L37-38       if (!keep) setCurrentUses(getCurrentUses() - used)
                         @272    L68-70       uses <= 0 && !isKeepOnDeplete() -> RemoveItem
    Food.setCurrentUses  @6      L2230        a `baseHunger == 0` branch sits AHEAD of the
                                              call below, so an item with no hunger scale
                                              never reaches consumeHunger (the same zero
                                              baseHunger `getMaxUses` answers 1 for)
                         @23-@35 L2228-L2233  consumeHunger((getCurrentUses() - n) / 100f)
    Food.consumeHunger   @0-@17  L2714-L2715  r = |a / hungChange|; multiplyFoodValues(1 - r)
    Food.getCurrentUses  @14-@26 L2219-L2223  (int)|hungChange  * 100|
    Food.getMaxUses      @11-@23 L2210-L2214  (int)|baseHunger * 100|

`|hungChange| = currentUses/100`, so `r = used/currentUses` and every field
`multiplyFoodValues` writes -- `hungChange`, `calories`, `carbohydrates`, `proteins`,
`lipids` and the mood block -- comes out scaled by **`1 - used/currentUses`**. That last
step is an EQUALITY only while `|hungChange| * 100` is a whole number, i.e. on an item
whose uses have never been part-spent: `getCurrentUses()` truncates (`(int)`), so on a
nibbled item `cur/100` is a hair under `|hungChange|` and the real argument is
`1 - ((cur - n)/100) / |hungChange|`, a hair under `1 - used/cur`. `used/cur` is the
readable form and the harness's own `predictedFactor`; `factor32()` below replays the
arithmetic the game actually does (`amount / hungChange`), which is what the compared
expectations use, and `factor.exact` carries the `1 - used/cur` reading beside it. All
three rows here are spawned whole, so the two agree to the last float32 bit. The
denominator is `currentUses`, **not** `maxUses`: `multiplyFoodValues` moves `hungChange`
(and with it `getCurrentUses()`) but never `baseHunger` (and with it `getMaxUses()`), so the
two are equal only while the item is whole. Every item here is spawned fresh and the
`spawn_guard` block below *checks* they are equal rather than assuming it -- that check is
what makes the `1 - uses/maxUses` shorthand in the brief legitimate for these three rows.

Three items, chosen to separate the fraction from the boundary:

  1. `Base.Icecream` (`HungerChange -30`, 1680 kcal) at **10 uses** -- a THIRD of a tub.
     The only row where the factor is neither 0 nor 1, so it is the one that can tell
     `1 - used/cur` apart from "one use = one item" (which would empty it) and from
     "N is a count of items" (which would need 10 tubs). Predicted: `hungChange -0.30 ->
     -0.20`, `calories 1680 -> 1120`, `carbs 180 -> 120`, `lipids 84 -> 56`,
     `proteins 26 -> 17.33`. This is exactly `ScoopIceCream`'s
     `item 10 [Base.Icecream]` line and the open question #1 of the notes.
  2. `Base.MincedMeat` (`-40`) at **40 uses** -- `MakeMeatPatty`'s whole line. 40/40 = one
     whole tub: the factor is 0, every macro must land on 0, and `getCurrentUses()` with it.
  3. `Base.Cheese` (`-15`) at **15 uses** -- `MakePizza`'s line, the same boundary reached
     from a different magnitude, so a coincidence in (2) cannot survive it.

**Why the numbers are drift-free.** `item.use` takes both snapshots *inside* one Lua call,
on either side of the single setter, so they are the same game tick; `delta.worldAgeHours`
in the reply is a compared field, not an assumption. Nothing here is a rate, so unlike
slice 05's drink probe there is no outer drift band to widen -- the independent outer
reading is an `item.get` on either side, and its only job is to confirm a second server
command sees the same object (`independent_read`, keyed on the item's `getID()` because
`item.get`'s finder answers the FIRST match while `item.use` picks the fullest).

**Predictions are computed at float32 width.** `Food` holds every one of these in a Java
`float`, and the chain has an `(int)` truncation at the end of it: `getCurrentUses()` is
`(int)|hungChange * 100|`, so a `hungChange` that lands a hair below the integer reads back
one use short. `f32()` replays the chain the way the JVM runs it and the untruncated exact
value is recorded next to it, so a boundary is visible rather than hidden (the
`healthFromFoodTimer` pattern of `s05b_drink_probe.py`).

**The route matters and is recorded.** `ItemUser` is *not* exposed to Lua on 42.20.4 --
`LuaManager$Exposer.shouldExpose @6-@14 L2833` is a strict `HashSet.contains` over the ~1000
classes `exposeAll()` registers and `zombie/inventory/ItemUser` is not one of them -- so the
harness falls back to `item:setCurrentUses(cur - used)`, which is *literally the line*
`UseItem @28 L37-38` executes and is the only way crafting reaches hunger at all (no
crafting class calls `setHungChange` / `consumeHunger` / `multiplyFoodValues`). What the
fallback skips is UseItem's bookkeeping *after* the reduction, and for a `Food` that is
exactly three things: the `replaceOnUse` spawn, `sendItemStats @293 L73-74` when uses remain,
and `RemoveItem` at `@272 L68-70` when they do not. It is **not** `replaceOnDeplete`: that arm
is behind `instanceof DrainableComboItem` (`@146 L53`) and a `Food` never enters it. None of
the three moves a nutrition field, so the measurement is untouched; but a depleted item stays
in the inventory, and `depletion.removed_from_inventory` is compared against the expectation
*for the route that actually ran* rather than against the one the crafting code would have
taken.

The run makes no world change -- no `settimespeed`, no sandbox write, no character write. The
spawned items land in the run directory's own COPY of the fixture (`fx.restore_server`), so
teardown is the whole cleanup path. `data/` is never touched: a number that disagrees is the
finding, written into `comparison` with both values.

**Wall time and the timeline are ~0.5 s apart.** `wall_seconds` is measured around the whole
script (`t_start` is set before `pzt doctor` runs) while the `timeline` marks start at
`session_ready`; and each `tl.mark` is stamped when the bus reply lands, not when the game
acted. So a timeline span read as a duration is short by roughly half a second against the
wall clock, and neither is a game-time reading -- the only game-time number here is
`delta.worldAgeHours`, taken inside the command handler, and it is 0.

**Replaying the comparator offline.** `compare_item` is pure -- replies in, block out -- so a
committed artifact can be re-scored at HEAD without booting the game. That is how the
comparator was checked before the live session (four synthetic replies: a whole reply, one
with no `before`, one for a type with no food record, and one where the use phase never ran --
the three early returns plus the happy path), and how a later fix round re-verifies this run.
Everything above the `LIVE SESSION BELOW` marker is definitions, so:

    p = "testing/experiments/s06b_use_probe.py"
    src = open(p, encoding="utf-8").read().rsplit("# ==== LIVE SESSION BELOW", 1)[0]
    ns = {"__file__": p}; exec(compile(src, p, "exec"), ns)
    art = json.load(open("testing/artifacts/exp06b-20260910-120123/use-probe.json"))
    foods = {r["id"]: r for r in json.load(open("data/food-items.json"))["items"]}
    for spec in ns["ITEMS"]:
        block = ns["compare_item"](spec, art["items"][spec["key"]], foods.get(spec["type"]))

At HEAD that gives **3 of 3 items matched, 96 of 96 fields**, unchanged from the run's own
verdict. Feed it a hand-built reply dict instead of `art["items"][...]` to exercise the three
early returns; each must come back `matched: False` with an empty `mismatches` list, which is
why the summary scores `ok` off `matched` and not off that list.

Everything lands in `<run_dir>/use-probe.json`, copied byte-for-byte at the end to
`testing/artifacts/<run-id>/use-probe.json`. Run with `python testing/pzt doctor` clean and
nothing else live; the doctor is re-run from here and its verdict is in the artifact.
"""
import json
import os
import shutil
import struct
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/
# `load_json` / `git_say` / `doctor` / `num` used to be defined here word for word, and in
# three sibling drivers. Slice 06's final fix wave promoted the identical copies into
# `_common.py`; the bodies are unchanged, so nothing this script writes into an artifact moves.
from _common import ask, doctor, git_say, hard_kill, load_json, num, save
from pzt import fixture as fx
from pzt.paths import new_run_dir
from pzt.session import Timeline, make_client, make_server, teardown

USER = "admin"
SPAWN_WAIT = 2.5          # RCON additem -> item visible in the inventory (slices 01/02/05)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# The dataset whose deltas rest on the rule under test. Not read for expectations -- the
# expectations come from the live `before` snapshot and the food scripts -- but its digest
# and dirty flag travel into the artifact, because "which recipes.json was standing when this
# was measured" is the question a later reader will ask.
RECIPES = os.path.join(REPO, "data", "recipes.json")
# Slice 05's committed food census: the source of the per-item script macros the `spawn_guard`
# block checks the spawned instance against. Using the dataset rather than literals ties the
# guard to something already validated live (exp05-20260910-084109).
FOODS = os.path.join(REPO, "data", "food-items.json")

# `Food` is float32 throughout, and TK.json rounds to 6 decimals on the way out, so an exact
# compare is wrong even where the arithmetic is exact. ABS_FLOOR covers that rounding (worst
# case 5e-7 per value) with room to spare; REL is the brief's 1e-4 relative band.
ABS_FLOOR, REL = 1e-5, 1e-4

ITEMS = [
    {"key": "icecream_third", "type": "Base.Icecream", "uses": 10,
     "note": "10 of 30 uses -- a THIRD of a tub, ScoopIceCream's own `item 10 "
             "[Base.Icecream]` line. The only row whose factor is neither 0 nor 1, so it is "
             "the one that separates `1 - used/currentUses` from `one use = one item` and "
             "from `N is a count of items`. Predicted -0.30 -> -0.20 and 1680 -> 1120 kcal"},
    {"key": "mincedmeat_whole", "type": "Base.MincedMeat", "uses": 40,
     "note": "40 of 40 uses -- MakeMeatPatty's whole line. Factor 0: every macro and "
             "getCurrentUses() must land on 0, and the depletion branch fires"},
    {"key": "cheese_whole", "type": "Base.Cheese", "uses": 15,
     "note": "15 of 15 uses -- MakePizza's line. The same boundary from a different "
             "magnitude, so a coincidence in the MincedMeat row cannot survive it"},
]

# (live key in the item snapshot, dataset column). `multiplyFoodValues` writes all five --
# `setHungChange(getHungChange() * f)` @20 L2290, `setCalories` @104 L2298, `setCarbohydrates`
# @114 L2299, `setProteins` @124 L2300, `setLipids` -- so all five scale by the same factor.
# `thirstChange` is deliberately NOT here: `multiplyFoodValues @42 L2292` multiplies
# `getThirstChangeUnmodified()` while `TK.ITEM_STATE.thirstChange` reads the MODIFIED getter,
# so the two are not the same number and comparing them would be a defect in this script
# rather than a finding. It is recorded uncompared in `recorded_uncompared`.
SCALED = (("hungChange", None), ("calories", "calories"), ("carbs", "carbohydrates"),
          ("lipids", "lipids"), ("proteins", "proteins"))
# The macro columns of `data/food-items.json`, for the spawn guard.
SCRIPT_COLUMNS = (("calories", "calories"), ("carbs", "carbohydrates"),
                  ("lipids", "lipids"), ("proteins", "proteins"))


def f32(x):
    """The nearest float32, as a Python float. Every field in the chain is a Java `float`,
    and the chain ends at an `(int)` truncation, so a prediction that has to survive that
    boundary must be computed the same width."""
    return struct.unpack("f", struct.pack("f", x))[0]


def dig(obj, *keys):
    for k in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    return obj


def tol(*magnitudes):
    """The float32 + JSON-rounding band: an absolute floor plus a relative term against the
    largest value involved. See ABS_FLOOR / REL.

    Pass the values being COMPARED and nothing else. Handing it a `before` value as well
    anchors the band on the number that is supposed to have *moved*: at factor 0 the
    expectation is 0 and `tol(0, 0, 1680)` is 0.168 kcal of slack around zero -- a band on the
    tub, not on the reading. `banded()` is the caller that gets this right, including the 0
    case, which needs no band at all."""
    m = max([abs(x) for x in magnitudes if isinstance(x, (int, float))] or [0.0])
    return ABS_FLOOR + REL * m


def row(expected, live, band, **extra):
    """One comparison row. `match` is False when either side is missing -- an absent live
    value is a failed reading, never an excused one (the `compare` rule of
    `s05_food_scan.py`)."""
    r = {"expected": expected, "live": live, "tolerance": band}
    r.update(extra)
    if expected is None or live is None:
        r["match"] = False
        r["note"] = "missing value"
    else:
        r["diff"] = live - expected
        r["match"] = abs(live - expected) <= band
    return r


def eq_row(expected, live, **extra):
    """An exact compare, for ints and booleans -- `row()` with a zero band would still do
    arithmetic on a bool."""
    r = {"expected": expected, "live": live, "tolerance": 0}
    r.update(extra)
    if expected is None or live is None:
        r["match"] = False
        r["note"] = "missing value"
    else:
        r["match"] = expected == live
    return r


def banded(expected, live, **extra):
    """A float compare whose band is anchored on the two values being compared -- and an EXACT
    compare when the expectation is 0.

    Zero is the case the band cannot express: `ABS_FLOOR + REL * 0` is 1e-5, which is not a
    tolerance so much as a rounding allowance, and every value the boundary rows here predict
    at 0 comes back as an integer 0 from `TK.json`. So a 0 expectation goes through `eq_row`
    and says exactly that -- the field is gone, not nearly gone. Anything else keeps
    `ABS_FLOOR + REL * max(|expected|, |live|)`, the float32 + JSON-rounding band."""
    if expected == 0:                    # covers -0.0; None falls through to the banded branch
        return eq_row(expected, live, **extra)
    return row(expected, live, tol(expected, live), **extra)


def factor32(hung_before, used):
    """`multiplyFoodValues`' argument, replayed at float32 width:

        amount = (float)(currentUses - n) / 100f     Food.setCurrentUses @23-@35
        r      = |amount / hungChange|               Food.consumeHunger  @0-@9
        factor = 1f - r                              Food.consumeHunger  @10-@14

    `currentUses - n` is `used`, and it is an int before the `i2f`."""
    hb = f32(hung_before)
    if hb == 0.0:
        return None
    amount = f32(f32(float(used)) / f32(100.0))
    return f32(f32(1.0) - abs(f32(amount / hb)))


def uses_of(hung):
    """`Food.getCurrentUses() = (int)|hungChange * 100|` -- `f2i` truncates toward zero, and
    so does Python's `int()`."""
    if hung is None:
        return None
    return int(abs(f32(f32(hung) * f32(100.0))))


def compare_item(spec, r, record):
    """One item's four comparison tables plus a flat `mismatches` list.

    Pure: it takes the harness replies and the food record and returns the block, so it can
    be replayed offline against a committed artifact -- which is how it was tested before the
    live session, and how a later fix round can re-verify this run without re-running it."""
    full_type, want = spec["type"], spec["uses"]
    rep = r.get("use") if isinstance(r, dict) and isinstance(r.get("use"), dict) else {}
    block = {"item": full_type, "requested_uses": want, "note": spec["note"],
             "food_record_found": record is not None,
             "route": rep.get("route"), "finder": rep.get("finder"),
             "selection": rep.get("selected"), "candidates": rep.get("candidates"),
             "candidates_after": rep.get("candidatesAfter"),
             "route_attempts": rep.get("routeAttempts"), "reply_error": rep.get("error"),
             "keep_on_deplete": rep.get("keepOnDeplete"),
             "disappear_on_use": rep.get("disappearOnUse"),
             "spawn_guard": {}, "scaling": {}, "depletion": {}, "independent_read": {},
             "mismatches": []}
    if not isinstance(r, dict):
        block["error"] = "the use phase never ran for this row"
        block["matched"] = False
        return block
    if record is None:
        block["error"] = f"no data/food-items.json record for {full_type}"
        block["matched"] = False
        return block
    bad = block["mismatches"]

    def flag(source, field, r_):
        if r_["match"] is not True:
            bad.append({"source": source, "field": field, "expected": r_["expected"],
                        "live": r_["live"], "tolerance": r_["tolerance"]})
        return r_

    before, after = rep.get("before") or {}, rep.get("after") or {}
    if not before:
        block["error"] = "the item.use reply carried no `before` snapshot: " + str(rep)[:300]
        block["matched"] = False
        return block

    # (a) spawn guard -- is this a WHOLE, script-fresh instance? Every expectation below is
    #     built on the live `before`, so this is the block that says the live `before` is the
    #     item the recipe dataset thinks it is. `current_uses == max_uses` is the one that
    #     licenses the brief's `1 - uses/maxUses` shorthand for these rows.
    hc_script = record.get("hunger_change")
    g = block["spawn_guard"]
    g["max_uses"] = eq_row(None if hc_script is None else int(abs(hc_script)),
                           num(before.get("maxUses")),
                           basis="Food.getMaxUses = (int)|baseHunger * 100| = |script "
                                 "HungerChange|")
    g["current_uses_is_whole"] = eq_row(num(before.get("maxUses")),
                                        num(before.get("currentUses")),
                                        basis="a freshly spawned item must be whole, and only "
                                              "then is maxUses the scaling denominator")
    hung_exp = None if hc_script is None else f32(f32(hc_script) / f32(100.0))
    g["hung_change"] = row(hung_exp, num(before.get("hungChange")),
                           tol(hung_exp, num(before.get("hungChange"))),
                           basis="Item.InstanceItem stores HungerChange/100 (food-item-model.md)")
    for live_key, column in SCRIPT_COLUMNS:
        g[live_key] = row(record.get(column), num(before.get(live_key)),
                          tol(record.get(column), num(before.get(live_key))),
                          dataset_column=column)
    g["in_container"] = eq_row(True, before.get("inContainer"),
                               basis="the spawned item is in the player's inventory before "
                                     "the call")
    # The precondition every reading below rests on, checked per run rather than assumed:
    # `item.get`'s finder answers the FIRST match while `item.use` picks the fullest, so with
    # more than one instance in the inventory the two commands can be looking at different
    # items and `independent_read` / `removed_from_inventory` stop meaning what they say. The
    # same shape as `s05b_drink_probe.py`'s full-container `amount_before` guard.
    cands_before = rep.get("candidates")
    g["instances_before"] = eq_row(1, None if cands_before is None else len(cands_before),
                                   basis="exactly one instance of this type in the inventory "
                                         "when the command ran")
    for k, rr in g.items():
        flag("spawn guard", k, rr)

    # (b) the scaling -- THE measurement. Expectations are the float32 chain applied to the
    #     LIVE `before`, so a wrong spawn shows up in (a) rather than silently moving these.
    used = num(rep.get("usedUses"))
    cur0 = num(before.get("currentUses"))
    hung0 = num(before.get("hungChange"))
    f_32 = None if (hung0 is None or used is None) else factor32(hung0, used)
    f_exact = None if (cur0 in (None, 0) or used is None) else 1.0 - used / cur0
    block["factor"] = {"used_uses": used, "current_uses_before": cur0,
                       "float32": f_32, "exact": f_exact,
                       "harness_prediction": num(rep.get("predictedFactor")),
                       "min_rule": "used = min(getCurrentUses(), requested) -- UseItem @18 L34",
                       "basis": "multiplyFoodValues(1 - used/currentUses); the compared "
                                "expectations use the float32 value"}
    block["scaling"]["used_uses"] = flag(
        "scaling", "used_uses",
        eq_row(None if cur0 is None else min(cur0, want), used,
               basis="Math.min(item.getCurrentUses(), count), UseItem @18 L34"))
    for live_key, column in SCALED:
        b = num(before.get(live_key))
        exp = None if (b is None or f_32 is None) else f32(f32(b) * f_32)
        exp_exact = None if (b is None or f_exact is None) else b * f_exact
        a = num(after.get(live_key))
        # `banded`, not `row(..., tol(exp, a, b))`: the `before` value has no business in the
        # band. On the two factor-0 rows it would have allowed 0.168 kcal (Icecream) or 0.030
        # (MincedMeat) of slack around an expectation of exactly 0 -- a band sized by the
        # nutrition that is supposed to be gone. `banded` compares 0 exactly and sizes every
        # other row on the two numbers actually being compared.
        block["scaling"][live_key] = flag(
            "scaling", live_key,
            banded(exp, a, before=b, expected_from_exact=exp_exact,
                   harness_prediction=num(dig(rep, "predicted", live_key)),
                   dataset_column=column,
                   basis="multiplyFoodValues(1 - used/currentUses) -- Food.multiplyFoodValues "
                         "@20/@104/@114/@124 L2290/L2298/L2299/L2300"))
    # `getCurrentUses()` is `(int)|hungChange * 100|`, so it is a SECOND, integer-valued
    # reading of the same scaling -- and the one that shows the truncation. Predicted from
    # the float32 hungChange, with the exact-arithmetic prediction beside it; the band is one
    # truncation unit wide because straight past a boundary the two disagree by exactly one
    # and that is a property of float32, not of the model.
    exp_hung32 = None if (hung0 is None or f_32 is None) else f32(f32(hung0) * f_32)
    exp_hung_ex = None if (hung0 is None or f_exact is None) else hung0 * f_exact
    block["scaling"]["currentUses"] = flag(
        "scaling", "currentUses",
        row(uses_of(exp_hung32), num(after.get("currentUses")), 1.0,
            before=cur0, expected_from_exact=uses_of(exp_hung_ex),
            basis="Food.getCurrentUses = (int)|hungChange * 100| @14-@26 L2219-L2223; band is "
                  "one truncation unit"))
    block["scaling"]["usesFloat"] = flag(
        "scaling", "usesFloat",
        banded(None if exp_hung32 is None else abs(exp_hung32), num(after.get("uses")),
               basis="Food.getCurrentUsesFloat = |hungChange| @14-@21 L2239-L2243"))
    block["scaling"]["max_uses_unmoved"] = flag(
        "scaling", "max_uses_unmoved",
        eq_row(num(before.get("maxUses")), num(after.get("maxUses")),
               basis="multiplyFoodValues never touches baseHunger, so getMaxUses() must not "
                     "move -- this is what makes currentUses, not maxUses, the denominator "
                     "of any SECOND reduction"))
    block["scaling"]["base_hunger_unmoved"] = flag(
        "scaling", "base_hunger_unmoved",
        banded(num(before.get("baseHunger")), num(after.get("baseHunger")),
               basis="the same claim read off the float rather than the int"))
    # Both snapshots are taken inside one Lua call, so the window must be 0. A compared field,
    # not a note: anything else means the block above is not drift-free.
    block["atomic_window_game_hours"] = row(
        0.0, num(dig(rep, "delta", "worldAgeHours")), 1e-5,
        basis="before/after are taken on either side of the single setter INSIDE one command "
              "handler. Band 1e-5 game-hours = 0.036 game-seconds, far below one tick; "
              "TK.json rounds to 6 decimals so anything under 5e-7 reads back as exactly 0")
    flag("atomic window", "worldAgeHours", block["atomic_window_game_hours"])

    # (c) the depletion branch. `removed_from_inventory` is route-dependent BY DESIGN:
    #     ItemUser.UseItem removes a depleted item (@272 L68-70), the setCurrentUses fallback
    #     is the reduction line only and does not. So the expectation is computed for the
    #     route that actually ran, and the route is in the block.
    route = str(rep.get("route") or "")
    via_useitem = route.startswith("ItemUser.UseItem(")
    emptied = (used is not None and cur0 is not None and used >= cur0)
    keep_on_deplete = rep.get("keepOnDeplete")
    expect_removed = bool(emptied and via_useitem and keep_on_deplete is not True)
    cands_after = rep.get("candidatesAfter")
    d = block["depletion"]
    d["expected_emptied"] = emptied
    d["route_removes_on_deplete"] = via_useitem
    if emptied:
        d["current_uses_after"] = eq_row(0, num(after.get("currentUses")),
                                         basis="used >= currentUses, so the uses reach 0")
    else:
        d["current_uses_after"] = eq_row(
            True, num(after.get("currentUses")) not in (None, 0),
            basis="a partial consumption must leave uses above 0",
            live_uses=num(after.get("currentUses")))
    flag("depletion", "current_uses_after", d["current_uses_after"])
    d["removed_from_inventory"] = flag(
        "depletion", "removed_from_inventory",
        eq_row(expect_removed,
               None if cands_after is None else (len(cands_after) == 0),
               basis="ItemUser.UseItem @272 L68-70 removes a depleted item; the "
                     "setCurrentUses fallback is the reduction line only, so on that route a "
                     "depleted item is expected to STAY -- expectation computed for the route "
                     "that ran (" + (route[:60] or "none") + ")"))
    d["still_in_container"] = eq_row(not expect_removed, after.get("inContainer"),
                                     basis="InventoryItem.getContainer() != null, the same "
                                           "claim read off the item instead of the inventory")
    flag("depletion", "still_in_container", d["still_in_container"])

    # (d) the independent outer read: `item.get` on either side of the command. Its only job
    #     is to confirm a SECOND server command sees the same object with the same values --
    #     nothing here is a rate, so there is no drift band to widen. Keyed on getID(),
    #     because `item.get`'s finder answers the FIRST match while `item.use` picks the
    #     fullest; if the ids differ the two commands are simply looking at different items
    #     and comparing their fields would be a fiction.
    gb = r.get("get_before") if isinstance(r.get("get_before"), dict) else None
    ga = r.get("get_after") if isinstance(r.get("get_after"), dict) else None
    ir = block["independent_read"]
    ir["item_get_before_found"] = eq_row(True, gb is not None,
                                         basis="the RCON spawn is keyed on item.get, not on "
                                               "the RCON reply (which is empty on success)")
    flag("independent read", "item_get_before_found", ir["item_get_before_found"])
    ir["same_instance_before"] = flag(
        "independent read", "same_instance_before",
        eq_row(num(before.get("id")), num(dig(gb, "id")),
               basis="item.get's getFirstTypeRecurse vs item.use's fullest-then-newest pick "
                     "-- with one instance in the inventory (spawn_guard.instances_before) "
                     "the two cannot disagree"))
    ir["item_get_after_found"] = eq_row(not expect_removed, ga is not None,
                                        basis="a removed item is no longer findable; on the "
                                              "setCurrentUses route it still is")
    flag("independent read", "item_get_after_found", ir["item_get_after_found"])
    ir["raw_get_after"] = r.get("get_after") if ga is None else None
    if ga is not None and num(dig(ga, "id")) == num(after.get("id")):
        for live_key, _ in SCALED:
            a1, a2 = num(after.get(live_key)), num(ga.get(live_key))
            ir[live_key] = flag("independent read", live_key,
                                row(a1, a2, tol(a1, a2),
                                    basis="the same field read by a second server command"))
        ir["currentUses"] = flag("independent read", "currentUses",
                                 eq_row(num(after.get("currentUses")),
                                        uses_of(num(ga.get("uses")))))
    elif ga is not None:
        ir["note"] = ("item.get after the call answered a DIFFERENT instance (id "
                      + str(num(dig(ga, "id"))) + " vs " + str(num(after.get("id")))
                      + "); its fields are recorded, not compared")
        ir["other_instance"] = ga

    block["recorded_uncompared"] = {
        "thirstChange": {"before": num(before.get("thirstChange")),
                         "after": num(after.get("thirstChange")),
                         "why": "multiplyFoodValues @42 L2292 scales "
                                "getThirstChangeUnmodified() while TK.ITEM_STATE reads the "
                                "MODIFIED getter -- not the same number, so comparing them "
                                "would be a defect in this script, not a finding"},
        "hungerChange": {"before": num(before.get("hungerChange")),
                         "after": num(after.get("hungerChange")),
                         "why": "the read-time getter that applies the cooked/burnt/stale "
                                "ladder (02-notes Q3); recorded so `hungChange` moving while "
                                "this does not (or vice versa) is visible"},
        "age": {"before": num(before.get("age")), "after": num(after.get("age"))},
    }
    block["matched"] = not bad
    return block


# ==== LIVE SESSION BELOW ==== everything above this line is definitions, so an offline replay
# execs the file up to this marker and calls `compare_item` itself (see the module docstring).
rec = fx.load("default")
run_id, run_dir = new_run_dir("exp06b")
path = os.path.join(run_dir, "use-probe.json")
tl = Timeline()
server = make_server(run_dir, rec)
clients = []
t_start = time.time()

doctor_clean, doctor_text = doctor()
foods, foods_err, foods_sha = load_json(FOODS)
recipes, recipes_err, recipes_sha = load_json(RECIPES)
foods_by_id = {r["id"]: r for r in (foods or {}).get("items", [])}
out = {"run_id": run_id,
       "meta": {"purpose": "live measurement of what consuming N USES of a food does to it "
                           "-- the rule data/recipes.json's nutrition deltas rest on "
                           "(06-recipes/q-itemcount-notes.md, Open #1)",
                "rule": "every field multiplyFoodValues writes is scaled by "
                        "(1 - used/currentUses), used = min(getCurrentUses(), requested); "
                        "maxUses and baseHunger do not move",
                "dataset": os.path.relpath(RECIPES, REPO).replace("\\", "/"),
                "dataset_commit": git_say("log", "-1", "--format=%h", "--",
                                          "data/recipes.json"),
                "dataset_sha256": recipes_sha,
                "dataset_dirty": bool(git_say("status", "--porcelain", "--",
                                              "data/recipes.json")),
                "dataset_read_error": recipes_err,
                "dataset_meta": (recipes or {}).get("meta"),
                "foods_dataset": os.path.relpath(FOODS, REPO).replace("\\", "/"),
                "foods_commit": git_say("log", "-1", "--format=%h", "--",
                                        "data/food-items.json"),
                "foods_sha256": foods_sha,
                "foods_dirty": bool(git_say("status", "--porcelain", "--",
                                            "data/food-items.json")),
                "foods_read_error": foods_err,
                "foods_use": "the per-item script macros the spawn_guard block checks the "
                             "spawned instance against; every scaling expectation is built "
                             "from the LIVE before snapshot, not from this file",
                "head_commit": git_say("rev-parse", "--short", "HEAD"),
                "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
                "spawn_wait_s": SPAWN_WAIT,
                "tolerance": {"abs": ABS_FLOOR, "rel": REL,
                              "why": "Food is float32 and TK.json rounds to 6 decimals; the "
                                     "relative term is the brief's 1e-4"},
                "world_changes": "none -- no settimespeed, no sandbox write, no character "
                                 "write. The spawned items live in this run's COPY of the "
                                 "fixture."},
       "session": {}, "items": {}, "comparison": {}, "summary": {}}
print(f"recipes sha256 {str(recipes_sha)[:16]}; foods sha256 {str(foods_sha)[:16]} "
      f"({len(foods_by_id)} items); doctor {'clean' if doctor_clean else 'DIRTY'}")
for line in doctor_text.strip().splitlines():
    print("  doctor| " + line)

try:
    if not doctor_clean:
        raise RuntimeError("pzt doctor is not clean -- refusing to boot: " + doctor_text[:400])
    server.start()
    c, _ = make_client(run_dir, USER, server, rec)
    c.start()
    clients.append(c)
    c.wait_ready()
    tl.mark("session_ready")
    out["fixture"] = rec.get("name")
    out["build"] = server.build

    def srv(cmd, args="", timeout=30):
        return ask(server, cmd, args, timeout=timeout)

    # ---- 0. session start ----------------------------------------------------
    out["session"]["players"] = srv("players")
    out["session"]["time_start"] = srv("time.snapshot")
    save(path, out, tl, server)

    # ---- 1. the three items --------------------------------------------------
    for spec in ITEMS:
        key, full_type, uses = spec["key"], spec["type"], spec["uses"]
        tl.mark("item_start", item=full_type, uses=uses)
        r = dict(spec)
        # Registered before the sub-steps run, so a probe that wedges half way through leaves
        # the rows it did collect in the artifact rather than losing the whole item.
        out["items"][key] = r
        # `item.get` answers the FIRST match, so this says whether the fixture already had
        # one. The `item.use` reply's candidate list is the definitive answer; this is the
        # cheap independent one, and it is why `same_instance_before` is a compared field.
        pre = srv("item.get", f"{USER} {full_type}", timeout=20)
        r["pre_existing"] = pre if isinstance(pre, dict) else str(pre)
        ok, reply = server.rcon(f'additem "{USER}" "{full_type}" 1')
        # An empty RCON reply is NOT a failed spawn -- success is keyed on `item.get`.
        r["rcon_additem"] = str(reply) if ok else f"rcon failed: {reply}"
        time.sleep(SPAWN_WAIT)
        r["get_before"] = srv("item.get", f"{USER} {full_type}", timeout=20)
        r["use"] = srv("item.use", f"{USER} {full_type} {uses}", timeout=45)
        tl.mark("used", item=full_type, route=str(dig(r["use"], "route"))[:70])
        r["get_after"] = srv("item.get", f"{USER} {full_type}", timeout=20)
        save(path, out, tl, server)
    out["session"]["time_end"] = srv("time.snapshot")
    save(path, out, tl, server)

    # ---- 2. the comparison ---------------------------------------------------
    for spec in ITEMS:
        key = spec["key"]
        block = compare_item(spec, out["items"].get(key), foods_by_id.get(spec["type"]))
        out["comparison"][key] = block
        tl.mark("compared", item=key, mismatches=len(block.get("mismatches") or []))
        save(path, out, tl, server)

    # ---- 3. the verdict ------------------------------------------------------
    per_item, mismatches, fields, matched = {}, [], 0, 0
    for key, block in out["comparison"].items():
        n = m = 0
        for group in ("spawn_guard", "scaling", "depletion", "independent_read"):
            for fk, rr in (block.get(group) or {}).items():
                if not isinstance(rr, dict) or "match" not in rr:
                    continue
                n += 1
                if rr.get("match") is True:
                    m += 1
        rr = block.get("atomic_window_game_hours")
        if isinstance(rr, dict) and "match" in rr:
            n += 1
            m += 1 if rr["match"] is True else 0
        # `matched`, NOT `not mismatches`: `compare_item` returns early with `matched: False`
        # and an EMPTY `mismatches` list on three paths -- the use phase never ran (`:275`), no
        # `data/food-items.json` record for the type (`:279`), and a reply with no `before`
        # snapshot (`:292`) -- and an empty list is falsy, so the emptiness test would have
        # scored a row that was never measured as a pass. All three rows of
        # `exp06b-20260910-120123` reached the comparison with a `before`, so the two readings
        # agree on that run (3/3 either way); this is the latent case closed.
        per_item[key] = {"fields": n, "matched": m,
                         "mismatched": len(block.get("mismatches") or []),
                         "route": block.get("route"),
                         "factor": dig(block, "factor", "float32"),
                         "ok": block.get("matched") is True}
        for b in (block.get("mismatches") or []):
            mismatches.append(dict(b, item=key))
        fields += n
        matched += m
    out["summary"] = {
        "items": len(out["comparison"]),
        "all_matched": bool(per_item) and all(v["ok"] for v in per_item.values())
                       and len(per_item) == len(ITEMS),
        "fields_compared": fields, "fields_matched": matched,
        "fields_mismatched": len(mismatches),
        "per_item": per_item, "mismatches": mismatches,
        "routes": {k: v.get("route") for k, v in out["comparison"].items()},
        "dataset_sha256": out["meta"]["dataset_sha256"],
        "dataset_commit": out["meta"]["dataset_commit"],
        "dataset_dirty": out["meta"]["dataset_dirty"],
        "foods_sha256": out["meta"]["foods_sha256"],
        "doctor_clean": doctor_clean,
    }
except Exception as e:                   # noqa: BLE001 - keep the rows already collected
    out["error"] = f"{type(e).__name__}: {e}"
    out["traceback"] = traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
    print(out["traceback"])
finally:
    # No world change to restore: no settimespeed, no sandbox write, no character write, and
    # the spawned items are in this run directory's own copy of the fixture. So teardown is
    # the whole cleanup path, exactly as in s05b_drink_probe.py.
    out["wall_seconds"] = round(time.time() - t_start, 1)
    save(path, out, tl, server)          # evidence on disk before the shutdown can go wrong
    try:
        teardown(tl, server, clients)    # graceful: the quit/stop rcs land in the timeline
    finally:
        hard_kill(server, clients)       # guaranteed, whatever teardown did
        out["wall_seconds"] = round(time.time() - t_start, 1)
        save(path, out, tl, server)      # the committed artifact: post-teardown timeline+errors
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "use-probe.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied -> {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")
print(json.dumps(out.get("summary", out.get("error", "no summary")), indent=1)[:9000])
