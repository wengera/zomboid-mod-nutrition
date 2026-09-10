"""Slice 05, task 5b: the live drink probe -- what drinking a fluid container actually writes.

Everything the dataset says about a *fluid container*'s nutrition is arithmetic done on a jar
read: `FluidContainer.getProperties()` aggregates `perLitre x litres`, and
`IsoGameCharacter.DrinkFluid` adds that aggregate `x f` to `Nutrition` while `Stats` takes the
already-amount-weighted `FluidConsume` (`.superpowers/sdd/05-food-scanner/
q3-fluid-nutrition-notes.md` § Drink path). Nothing had ever *drunk* one --
`docs/vanilla/eating-pipeline.md`'s fluid rows and slice 01's open question #11 are grade C
throughout. This run makes three drinks and reads the stores on either side of each.

Three drinks, chosen to separate the three terms of `per-litre x litres x f`:

  1. `Base.Pop2` at `f = 1.0`  -- 0.3 L of Cola. Isolates `x litres`: if the columns were
     per-item the store would move by Cola's raw 400 kcal, and if they were per-litre-but-
     unweighted it would move by 400 as well; only `400 x 0.3 = 120` distinguishes them.
  2. `Base.Pop2` at `f = 0.5`  -- the same can, half drunk. Isolates `x f`, and with it the
     claim that `f` is a share of the *contents* (`removeFluid(getAmount() * f)`), so a full
     can at 0.5 must leave exactly 0.15 L.
  3. `Base.JuiceBox` at `f = 1.0` -- 0.2 L of JuiceGrape, a different fluid AND a different
     capacity, so a coincidence in (1) cannot survive it: 400 kcal/L x 0.2 = 80.

Four independent readings of the same claim per drink, so a single wrong one is visible
rather than fatal:

  * **the container's own aggregate** -- `getProperties()` read live off the spawned
    instance, against the dataset's `*_per_container` columns. This is the litres weighting
    on its own, with no character involved;
  * **`Nutrition`** -- calories / carbohydrates / lipids / proteins;
  * **`Stats`** -- HUNGER / THIRST, which arrive by the *other* route (the `FluidConsume`),
    and which the loader has already divided by 100;
  * **`BodyDamage.healthFromFoodTimer`** -- `(int)(timer + |hungerChange| * 13000)`, a third
    route to the same hunger number, and the one that shows the `(int)` truncation.

**Why the numbers are drift-free.** The `drink` command takes both snapshots *inside* one Lua
call, on either side of the single `DrinkFluid` line, so they are the same game tick and the
passive drain between them is zero rather than small -- `delta.worldAgeHours` in the reply is
the check on that, not an assumption. The `stats.get` bracket this script puts *around* the
command is the independent outer reading and it **does** carry drift; it is compared against a
band whose width is the maximum passive movement over its own measured `worldAge` window, at
the rates slice 03 and slice 04 measured on this same fixture (see `DRIFT_RATES`).

**Two primings, both required, both recorded.**

  * `CharacterStat.HUNGER` / `THIRST` clamp to `[0, 1]`. On a satiated character a drink's
    relief is silently discarded and the delta measures nothing (slice 01, `TK.setStat`'s
    note). Hunger and thirst are therefore set to 0.5 before every drink -- an order of
    magnitude above the largest relief here (0.09).
  * `Nutrition.setCalories` clamps `[-2200, 3700]` and the macros `[-500, 1000]`. Calories are
    primed to 500 and the three macros to 0 once, before the first drink: the three drinks add
    260 kcal and ~71 g of carbs in total, so no write can reach a clamp. The guard is checked
    against the measured `before` as well, per drink, and reported.

The run makes no world change -- no `settimespeed`, no sandbox write. The character writes and
the spawned cans land in the run directory's own COPY of the fixture (`fx.restore_server`), so
there is nothing to restore and teardown is the whole cleanup path. `data/` is never touched:
a number that disagrees is the finding, written into `comparison` with both values.

Everything lands in `<run_dir>/drink-probe.json`, copied byte-for-byte at the end to
`testing/artifacts/<run-id>/drink-probe.json`. Run with `python testing/pzt doctor` clean and
nothing else live; the doctor is re-run from here and its verdict is in the artifact.
"""
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/
from _common import ask, hard_kill, save
from pzt import fixture as fx
from pzt.paths import new_run_dir
from pzt.session import Timeline, make_client, make_server, teardown

USER = "admin"
SPAWN_WAIT = 2.5          # RCON additem -> item visible in the inventory (slices 01/02/05)
DRINK_SETTLE = 3.0        # after the drink, before the outer read: the 1 Hz PlayerStatsPacket
                          # beat. Immaterial to the server-side reading (the store is written
                          # synchronously inside DrinkFluid) -- it is here so the outer bracket
                          # is not racing the sync it does not depend on.

# The primings. See the module docstring for why each is required.
PRIME_HUNGER, PRIME_THIRST = 0.5, 0.5
PRIME_NUTRITION = (("calories", 500.0), ("carbs", 0.0), ("lipids", 0.0), ("proteins", 0.0))
NUTRITION_CLAMPS = {"calories": (-2200.0, 3700.0), "carbs": (-500.0, 1000.0),
                    "lipids": (-500.0, 1000.0), "proteins": (-500.0, 1000.0)}

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET = os.path.join(REPO, "data", "food-items.json")

# `Nutrition` and `Stats` are float32 on the Java side, so an exact compare is wrong even when
# the arithmetic is exact: 500 + 120 is exact, but 0 + 31.2 reads back 31.200001. The band is
# an absolute floor plus a relative term against the STORE's magnitude (not the delta's) --
# the delta is a difference of two float32s, so its error scales with the values it came from.
# 1e-6 x magnitude is ~16 float32 ULPs; 1e-4 absolute covers the stats, whose stores are O(1).
ATOMIC_ABS, ATOMIC_REL = 1e-4, 1e-6

# Passive movement of each store, per GAME-second, on this fixture at speed 1. Every one is
# MEASURED, not assumed, and the citation travels into the artifact:
#   calories  0.016 x weight/80        -- docs/vanilla/body-stats.md § Passive burn, ratio
#                                         1.0049 r^2 1.000000 (exp03-20260910-045523)
#   carbs     0.0035                   -- docs/vanilla/nutrition-core.md, -302.4/game-day
#                                         against 0.0035 x 86400, exact (scenario runs 2, 3)
#   lipids    0.00113                  -- the macro drains are THREE DIFFERENT rates, not one:
#   proteins  0.00086                     `Nutrition.update @48/@66/@84 L76-L78`
#                                         (eating-pipeline.md:225), the constants slice 03 fitted
#                                         at s03_body.py:103 -- exp03-20260910-045523 ratios
#                                         0.9991 / 0.9972 / 0.9993 (body-stats.md § Passive burn).
#                                         The run committed as exp05b-20260910-093307 labelled
#                                         both of these 0.0035 and banded them with it; the label
#                                         is a *do not cite* row in testing/artifacts/README.md
#                                         and the band it widened was ~3x too wide, which cannot
#                                         turn a mismatch into a match. Its own three windows
#                                         reproduce the rates above to four figures.
#   hunger    9.6e-6 x (1 - hunger)    -- body-stats.md § constants, ratio 1.0000 -- and it is
#                                         ZERO while FOOD_EATEN >= 1, which every drink here
#                                         switches on, so the band's low end is the real one
#   thirst    8.0e-6                   -- same table, ratio 1.0000, linear, no damping
# They are used only to WIDEN the outer bracket's tolerance, never to correct a number. The
# numbers `drift()` bands with and the labels the artifact carries come from one place, so a
# future fix cannot correct one and leave the other.
MACRO_DRIFT = {"carbs": 0.0035, "lipids": 0.00113, "proteins": 0.00086}
DRIFT_RATES = {
    "calories": "0.016 * weight/80 per game-second (body-stats.md § Passive burn, M exp03)",
    "carbs": "0.0035 per game-second (nutrition-core.md; s03_body.py:103, M exp03 ratio 0.9991)",
    "lipids": "0.00113 per game-second (eating-pipeline.md:225 / Nutrition.update @66 L77; "
              "s03_body.py:103, M exp03 ratio 0.9972)",
    "proteins": "0.00086 per game-second (eating-pipeline.md:225 / Nutrition.update @84 L78; "
                "s03_body.py:103, M exp03 ratio 0.9993)",
    "hunger": "9.6e-6 * (1 - hunger) per game-second, 0 while FOOD_EATEN >= 1 (body-stats.md, M)",
    "thirst": "8.0e-6 per game-second (body-stats.md, M)",
}

# The three drinks. `fluid` is the definition the dataset joins the container to; `note` says
# what the row is there to separate, and travels into the artifact.
DRINKS = [
    {"key": "pop2_whole", "type": "Base.Pop2", "fraction": 1.0, "fluid": "Cola",
     "note": "0.3 L of Cola drunk to the bottom: isolates the litres weighting -- 400 kcal/L "
             "x 0.3 L = 120, against the 400 a per-item reading of the column would give"},
    {"key": "pop2_half", "type": "Base.Pop2", "fraction": 0.5, "fluid": "Cola",
     "note": "a second, full can at f = 0.5: isolates f, and pins that f is a share of the "
             "CONTENTS (removeFluid(getAmount() * f)) -- a full can must be left at 0.15 L"},
    {"key": "juicebox_whole", "type": "Base.JuiceBox", "fraction": 1.0, "fluid": "JuiceGrape",
     "note": "0.2 L of JuiceGrape: a different fluid AND a different capacity, so a "
             "coincidence in the Cola rows cannot survive it -- 400 kcal/L x 0.2 L = 80"},
]

# (delta key in the `drink` reply, dataset column, factor). The factor is the loader's /100,
# which applies to hunger and thirst and to nothing else: `FluidDefinitionScript
# .getHungerChange @0-@10 L186` divides, `.getCalories @0-@7 L202` does not. The dataset keeps
# both raw (data/README.md), so the /100 is applied here, on the way to a Stats comparison.
NUTRITION_FIELDS = (("calories", "calories_per_container", 1.0),
                    ("carbs", "carbohydrates_per_container", 1.0),
                    ("lipids", "lipids_per_container", 1.0),
                    ("proteins", "proteins_per_container", 1.0),
                    ("hunger", "hunger_change_per_container", 0.01),
                    ("thirst", "thirst_change_per_container", 0.01))
# The same six against the container's OWN aggregate, which is not multiplied by f -- it is
# what a full container holds. Different key spelling: `getProperties()` answers
# hungerChange/thirstChange, `Nutrition`/`Stats` answer hunger/thirst. The /100 is here too:
# `getProperties()` aggregates the LOADER's values, which are already divided.
PROPERTY_FIELDS = (("calories", "calories_per_container", 1.0),
                   ("carbs", "carbohydrates_per_container", 1.0),
                   ("lipids", "lipids_per_container", 1.0),
                   ("proteins", "proteins_per_container", 1.0),
                   ("hungerChange", "hunger_change_per_container", 0.01),
                   ("thirstChange", "thirst_change_per_container", 0.01))
# The outer bracket reads the same six stores through `stats.get` (TK.bodySnapshot), which spells
# them exactly the way the `drink` reply's `delta` does -- so its rows are looked up under the
# same key, with no mapping in between.


def load_dataset(path):
    """`(data, error, sha256)` -- one read, hashed and decoded, so the digest is of the same
    bytes that were parsed. `s05_food_scan.py` explains why the digest and not just the commit:
    `git log -1` names the newest commit that TOUCHED the path, which is not the same question
    as where these bytes came from."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        return json.loads(raw.decode("utf-8")), None, hashlib.sha256(raw).hexdigest()
    except (ValueError, OSError, UnicodeDecodeError) as e:
        return None, f"{type(e).__name__}: {e}", None


def git_say(*args):
    """A short `git` answer, or the error string. Provenance only -- never fatal."""
    try:
        p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True,
                           timeout=30)
        if p.returncode != 0:
            return f"git rc={p.returncode}"
        return (p.stdout or "").strip()
    except Exception as e:                       # noqa: BLE001 - provenance, never fatal
        return f"{type(e).__name__}: {e}"


def doctor():
    """`pzt doctor` from inside the run: `(clean, text)`. The brief's precondition, recorded
    rather than remembered -- a run booted onto a dirty machine is not evidence."""
    try:
        p = subprocess.run([sys.executable, os.path.join(REPO, "testing", "pzt"), "doctor"],
                           capture_output=True, text=True, timeout=300)
        return p.returncode == 0, (p.stdout or "") + (p.stderr or "")
    except Exception as e:                       # noqa: BLE001 - reported, not raised
        return False, f"{type(e).__name__}: {e}"


def f32(x):
    """The nearest float32, as a Python float. Java holds `Nutrition`, `SealedFluidProperties`
    and every fluid property in `float`, so a prediction that has to survive a truncation
    boundary must be computed the same width (see `food_timer`)."""
    return struct.unpack("f", struct.pack("f", x))[0]


def num(v):
    """A number, or None for anything else (a missing key, an `{'error': ...}` reply)."""
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def dig(obj, *keys):
    for k in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    return obj


def tol(*magnitudes):
    """The float32 band: an absolute floor plus a relative term against the largest store
    involved. See ATOMIC_ABS / ATOMIC_REL."""
    m = max([abs(x) for x in magnitudes if isinstance(x, (int, float))] or [0.0])
    return ATOMIC_ABS + ATOMIC_REL * m


def row(expected, live, band, **extra):
    """One comparison row. `match` is False when either side is missing -- an absent live value
    is a failed reading, never an excused one (the `compare` rule of `s05_food_scan.py`)."""
    r = {"expected": expected, "live": live, "tolerance": band}
    r.update(extra)
    if expected is None or live is None:
        r["match"] = False
        r["note"] = "missing value"
    else:
        r["diff"] = live - expected
        r["match"] = abs(live - expected) <= band
    return r


def drift(dt_game_s, weight, hunger):
    """The largest passive movement of each store over `dt_game_s`, signed. Used to widen the
    OUTER bracket's tolerance only. `None` when the window could not be measured."""
    if dt_game_s is None:
        return None
    w = weight if isinstance(weight, (int, float)) else 80.0
    h = hunger if isinstance(hunger, (int, float)) else 0.0
    out = {"calories": -0.016 * (w / 80.0) * dt_game_s,
           "hunger": 9.6e-6 * max(0.0, 1.0 - h) * dt_game_s,
           "thirst": 8.0e-6 * dt_game_s}
    out.update({k: -rate * dt_game_s for k, rate in MACRO_DRIFT.items()})
    return out


def compare_drink(d, r, record):
    """One drink's four comparison tables, as `{container, container_fill, atomic, food_timer,
    outer, ...}` plus a flat `mismatches` list.

    Pure: it takes the harness replies and the dataset record and returns the block, so it can
    be replayed offline against a committed artifact (which is how it was tested before the
    live session, and how a later fix round can re-verify this run without re-running it).
    """
    frac, full_type = d["fraction"], d["type"]
    rep = (r or {}).get("drink") if isinstance((r or {}).get("drink"), dict) else {}
    block = {"item": full_type, "fraction": frac, "note": d["note"], "fluid_id": d["fluid"],
             "dataset_record_found": record is not None,
             "route": rep.get("route"), "finder": rep.get("finder"),
             "selection": rep.get("selected"), "candidates": rep.get("candidates"),
             "primary_fluid": rep.get("primaryFluid"),
             "primary_fluid_route": rep.get("primaryFluidRoute"),
             "reply_error": rep.get("error"), "container": {}, "atomic": {}, "outer": {},
             "mismatches": []}
    if r is None:
        block["error"] = "the drink phase never ran for this row"
        block["matched"] = False
        return block
    if record is None:
        block["error"] = f"no dataset record for {full_type}"
        block["matched"] = False
        return block
    bad = block["mismatches"]

    def flag(source, field, r_):
        if r_["match"] is not True:
            bad.append({"source": source, "field": field, "expected": r_["expected"],
                        "live": r_["live"], "tolerance": r_["tolerance"]})
        return r_

    # (a) the container's own aggregate, before the drink. No `f` in it: this is the litres
    #     weighting on its own -- per-litre x fluid_fill_litres, with no character involved.
    props = rep.get("containerProperties") or {}
    for live_key, column, factor in PROPERTY_FIELDS:
        base = record.get(column)
        exp = None if base is None else base * factor
        live = num(props.get(live_key))
        block["container"][live_key] = flag(
            "container aggregate", live_key,
            row(exp, live, tol(exp, live), dataset_column=column, factor=factor,
                basis="FluidContainer.getProperties() = per-litre x fluid_fill_litres "
                      "(recalculateCaches @234-@250 L632), read live before the drink"))
    fill = record.get("fluid_fill_litres")
    # `amount_before` is the guard on the assumption every other row here rests on: that the
    # spawned container is FULL. `fluid_fill_litres` is the full-container figure (capacity x
    # share), and 14 vanilla containers write `InitialPercentMin` / `InitialPercentMax` and spawn
    # part-filled at a random draw instead -- neither of these two does, and this row is what says
    # so per run rather than per reading of the scripts. A part-filled spawn fails it, and with it
    # every `x fill` expectation below, instead of quietly re-scaling them.
    block["container_fill"] = {
        "capacity": row(record.get("fluid_capacity"),
                        num(dig(rep, "before", "container", "capacity")), 1e-4),
        "amount_before": row(fill, num(dig(rep, "before", "container", "amount")), 1e-4),
        "amount_after": row(None if fill is None else fill * (1.0 - frac),
                            num(dig(rep, "after", "container", "amount")), 1e-4,
                            basis="removeFluid(getAmount() * f): f is a share of the CONTENTS, "
                                  "so a full container is left holding (1 - f) x fill")}
    for k, rr in block["container_fill"].items():
        flag("container fill", k, rr)

    # (b) the atomic in-command deltas: the primary reading, drift-free by construction.
    delta = rep.get("delta") or {}
    before_n = dig(rep, "before", "nutrition") or {}
    after_n = dig(rep, "after", "nutrition") or {}
    for live_key, column, factor in NUTRITION_FIELDS:
        base = record.get(column)
        exp = None if base is None else base * factor * frac
        block["atomic"][live_key] = flag(
            "atomic delta", live_key,
            row(exp, num(delta.get(live_key)),
                tol(exp, num(before_n.get(live_key)), num(after_n.get(live_key))),
                dataset_column=column, factor=factor, fraction=frac,
                before=num(before_n.get(live_key)), after=num(after_n.get(live_key)),
                basis=("dataset[%s] x %g x f" % (column, factor)
                       + ("  (the /100 the fluid script loader applies: "
                          "FluidDefinitionScript.getHungerChange @0-@10 L186)"
                          if factor != 1.0 else ""))))
    block["atomic"]["amount"] = flag(
        "atomic delta", "amount",
        row(None if fill is None else -fill * frac, num(delta.get("amount")), 1e-4,
            basis="removeFluid(getAmount() * f) on a full container"))
    # The window the two snapshots span. Anything but 0 means they were NOT the same tick and
    # the block above is not drift-free -- so it is a compared field, not a note.
    block["atomic_window_game_hours"] = row(
        0.0, num(delta.get("worldAgeHours")), 1e-5,
        basis="both snapshots are taken inside one Lua call, so the window must be 0. The band "
              "is 1e-5 game-hours = 0.036 game-seconds -- far below one tick (0.27 game-s at "
              "60 fps on this fixture's 16.03 game-s/real-s clock), so a genuine tick advance "
              "fails it while float noise does not; at that width the calorie drift it could "
              "hide is 6e-4 kcal. TK.json rounds to 6 decimals, so anything under 5e-7 "
              "game-hours reads back as exactly 0")
    flag("atomic delta", "worldAgeHours", block["atomic_window_game_hours"])

    # (c) healthFromFoodTimer: a third route to the same hunger number, and the (int) cast.
    #     Predicted twice. The jar's chain is float32 throughout -- loader `/100.0f`, then
    #     `addFromMultiplied(props, litres * f)`, then `* 13000.0f` -- and it lands just ABOVE
    #     the integer (468.00003 for a whole Pop2) where exact arithmetic lands just below
    #     (467.99999999999994). Straight past a truncation boundary those two disagree by a
    #     whole unit, which is a property of float32 and not of the model, so the compared
    #     expectation is the float32 chain and the band is one unit wide; both predictions and
    #     the untruncated values are recorded so the boundary is visible rather than hidden.
    h_litre, litres = record.get("hunger_change"), fill
    raw_f32 = raw_dbl = None
    if h_litre is not None and litres is not None:
        raw_f32 = f32(abs(f32(f32(f32(h_litre) / f32(100.0)) * f32(f32(litres) * f32(frac))))
                      * f32(13000.0))
    h_col = record.get("hunger_change_per_container")
    if h_col is not None:
        raw_dbl = abs(h_col * 0.01 * frac) * 13000.0
    ft_before = num(dig(rep, "before", "foodTimer"))
    exp_timer = None
    if raw_f32 is not None and ft_before is not None:
        exp_timer = float(int(ft_before + raw_f32)) - ft_before
    block["food_timer"] = row(exp_timer, num(delta.get("foodTimer")), 1.0,
                              before=ft_before, after=num(dig(rep, "after", "foodTimer")),
                              untruncated_float32=raw_f32, untruncated_exact=raw_dbl,
                              expected_from_exact=(None if raw_dbl is None or ft_before is None
                                                   else float(int(ft_before + raw_dbl))
                                                   - ft_before),
                              harness_prediction=num(rep.get("predictedFoodTimer")),
                              basis="(int)(timer + |hungerChange x f| * 13000), DrinkFluid "
                                    "@254-@286 L5896-L5897 -- the cast truncates the WHOLE "
                                    "sum. Band 1.0 = one truncation unit (see the comment)")
    flag("healthFromFoodTimer", "foodTimer", block["food_timer"])

    # (d) the outer bracket: the same six stores read through the bus on either side of the
    #     command. Its window carries real drift, so the band is widened by the maximum passive
    #     movement over the window it actually measured.
    ob, oa = r.get("outer_before_stats"), r.get("outer_after_stats")
    w0, w1 = num(dig(ob, "worldAge")), num(dig(oa, "worldAge"))
    dt = None if (w0 is None or w1 is None) else (w1 - w0) * 3600.0
    dr = drift(dt, num(dig(ob, "weight")), num(dig(ob, "hunger")))
    block["outer_window"] = {"world_age_before": w0, "world_age_after": w1, "game_seconds": dt,
                             "spans": "the bus round trips around the command plus "
                                      "DRINK_SETTLE", "max_drift": dr}
    for live_key, column, factor in NUTRITION_FIELDS:
        base = record.get(column)
        exp = None if base is None else base * factor * frac
        b, a = num(dig(ob, live_key)), num(dig(oa, live_key))
        live = None if (b is None or a is None) else a - b
        # The band is exactly [expected, expected + max drift], widened by the float band:
        # centring on the midpoint with a half-width of |drift|/2 + float band IS that
        # interval, and it keeps `diff` readable as a signed distance from the middle.
        move = (dr or {}).get(live_key, 0.0)
        block["outer"][live_key] = flag(
            "outer bracket", live_key,
            row(None if exp is None else exp + move / 2.0, live,
                abs(move) / 2.0 + tol(exp, b, a),
                dataset_column=column, no_drift_expectation=exp, before=b, after=a,
                max_drift=(dr or {}).get(live_key),
                basis="the no-drift expectation, banded by the maximum passive movement over "
                      "the measured window"))
    # The second, independent server read of the same stores. Recorded and left uncompared:
    # `nutrition.get` carries no clock, so it has no window of its own to band against -- it is
    # here as a witness that two different server commands see the same store.
    nb, na = r.get("outer_before_nutrition"), r.get("outer_after_nutrition")
    block["outer_nutrition_get"] = {
        k: {"before": num(dig(nb, k)), "after": num(dig(na, k)),
            "delta": (None if num(dig(nb, k)) is None or num(dig(na, k)) is None
                      else num(dig(na, k)) - num(dig(nb, k)))}
        for k in ("calories", "carbs", "lipids", "proteins", "hunger", "thirst")}

    # (e) clamp guard: was any write within reach of a Nutrition clamp?
    guards = {}
    for live_key, column, factor in NUTRITION_FIELDS:
        if live_key not in NUTRITION_CLAMPS:
            continue
        lo, hi = NUTRITION_CLAMPS[live_key]
        b = num(before_n.get(live_key))
        base = record.get(column)
        exp = None if base is None else base * factor * frac
        guards[live_key] = {"before": b, "expected_delta": exp, "clamp": [lo, hi],
                            "clear": (b is not None and exp is not None and lo < b + exp < hi)}
    block["clamp_guard"] = guards
    block["matched"] = not bad
    return block


rec = fx.load("default")
run_id, run_dir = new_run_dir("exp05b")
path = os.path.join(run_dir, "drink-probe.json")
tl = Timeline()
server = make_server(run_dir, rec)
clients = []
t_start = time.time()

doctor_clean, doctor_text = doctor()
data, data_err, data_sha = load_dataset(DATASET)
items_by_id = {r["id"]: r for r in (data or {}).get("items", [])}
fluids_by_id = {r["id"]: r for r in (data or {}).get("fluids", [])}
out = {"run_id": run_id,
       "meta": {"purpose": "live measurement of IsoGameCharacter.DrinkFluid against the "
                           "dataset's per-container fluid columns (slice 01 open question 11)",
                "dataset": os.path.relpath(DATASET, REPO).replace("\\", "/"),
                "dataset_commit": git_say("log", "-1", "--format=%h", "--",
                                          "data/food-items.json"),
                "dataset_sha256": data_sha,
                "dataset_dirty": bool(git_say("status", "--porcelain", "--",
                                              "data/food-items.json")),
                "dataset_read_error": data_err,
                "dataset_meta": (data or {}).get("meta"),
                "head_commit": git_say("rev-parse", "--short", "HEAD"),
                "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
                "spawn_wait_s": SPAWN_WAIT, "drink_settle_s": DRINK_SETTLE,
                "prime_hunger": PRIME_HUNGER, "prime_thirst": PRIME_THIRST,
                "prime_nutrition": dict(PRIME_NUTRITION),
                "atomic_tolerance": {"abs": ATOMIC_ABS, "rel": ATOMIC_REL,
                                     "why": "Nutrition and Stats are float32; the delta is a "
                                            "difference of two of them, so the band scales "
                                            "with the store, not with the delta"},
                "drift_rates": DRIFT_RATES,
                "drift_use": "the outer stats.get bracket's tolerance is widened by the "
                             "maximum passive movement over its own measured worldAge window; "
                             "no measured number is ever corrected by it",
                "world_changes": "none -- no settimespeed, no sandbox write. The primings and "
                                 "the spawned cans live in this run's COPY of the fixture."},
       "session": {}, "fluid_script": {}, "drinks": {}, "comparison": {}, "summary": {}}
print(f"dataset sha256 {str(data_sha)[:16]} ({len(items_by_id)} items, {len(fluids_by_id)} "
      f"fluids); doctor {'clean' if doctor_clean else 'DIRTY'}")
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
    out["session"]["stats_at_start"] = srv("stats.get", USER)
    # The two fluid definitions behind the three drinks, read live. Not a verdict here (slice
    # 05's own experiment already compared them field by field) -- it is the provenance of the
    # per-litre numbers whose litres-weighting this run is measuring.
    for fid in ("Cola", "JuiceGrape"):
        out["fluid_script"][fid] = srv("fluid.script", fid, timeout=45)
    tl.mark("session_probes", got=sorted(out["fluid_script"]))
    save(path, out, tl, server)

    # ---- 1. prime the nutrition stores once ---------------------------------
    primed = {}
    for field, value in PRIME_NUTRITION:
        primed[field] = srv("nutrition.set", f"{USER} {field} {value}")
    out["session"]["prime_nutrition"] = primed
    tl.mark("nutrition_primed")
    save(path, out, tl, server)

    # ---- 2. the three drinks -------------------------------------------------
    for d in DRINKS:
        key, full_type, frac = d["key"], d["type"], d["fraction"]
        tl.mark("drink_start", drink=key, item=full_type, f=frac)
        r = dict(d)
        # Registered before the sub-steps run, so a probe that wedges half way through leaves
        # the rows it did collect in the artifact rather than losing the whole drink.
        out["drinks"][key] = r
        # `item.get` answers the FIRST match, so this says whether the fixture (or a previous
        # drink in this run) already had one -- the `drink` reply's candidate list is the
        # definitive answer, this is the cheap independent one.
        pre = srv("item.get", f"{USER} {full_type}", timeout=20)
        r["pre_existing"] = pre if isinstance(pre, dict) else str(pre)
        ok, reply = server.rcon(f'additem "{USER}" "{full_type}" 1')
        r["rcon_additem"] = str(reply) if ok else f"rcon failed: {reply}"
        time.sleep(SPAWN_WAIT)
        # Prime AFTER the spawn wait, so as little as possible sits between the prime and the
        # drink. foodtimer first: DrinkFluid adds to whatever is there, and a known 0 makes the
        # (int) truncation readable.
        r["foodtimer_set"] = srv("foodtimer.set", f"{USER} 0")
        r["stats_set"] = srv("stats.set",
                             f"{USER} hunger {PRIME_HUNGER} thirst {PRIME_THIRST}")
        r["outer_before_stats"] = srv("stats.get", USER)
        r["outer_before_nutrition"] = srv("nutrition.get", USER)
        r["drink"] = srv("drink", f"{USER} {full_type} {frac}", timeout=45)
        tl.mark("drank", drink=key, route=str(dig(r["drink"], "route"))[:60])
        time.sleep(DRINK_SETTLE)
        r["outer_after_stats"] = srv("stats.get", USER)
        r["outer_after_nutrition"] = srv("nutrition.get", USER)
        save(path, out, tl, server)
    out["session"]["stats_at_end"] = srv("stats.get", USER)
    out["session"]["time_end"] = srv("time.snapshot")
    save(path, out, tl, server)

    # ---- 3. the comparison ---------------------------------------------------
    for d in DRINKS:
        key = d["key"]
        block = compare_drink(d, out["drinks"].get(key), items_by_id.get(d["type"]))
        out["comparison"][key] = block
        tl.mark("compared", drink=key, mismatches=len(block.get("mismatches") or []))
        save(path, out, tl, server)

    # ---- 4. the verdict ------------------------------------------------------
    per_drink, mismatches, fields, matched = {}, [], 0, 0
    for key, block in out["comparison"].items():
        n = m = 0
        for group in ("container", "atomic", "outer", "container_fill"):
            for fk, rr in (block.get(group) or {}).items():
                n += 1
                if rr.get("match") is True:
                    m += 1
        for extra in ("food_timer", "atomic_window_game_hours"):
            rr = block.get(extra)
            if isinstance(rr, dict) and "match" in rr:
                n += 1
                m += 1 if rr["match"] is True else 0
        per_drink[key] = {"fields": n, "matched": m,
                          "mismatched": len(block.get("mismatches") or []),
                          "route": block.get("route"), "ok": not block.get("mismatches")}
        for b in (block.get("mismatches") or []):
            mismatches.append(dict(b, drink=key))
        fields += n
        matched += m
    out["summary"] = {
        "drinks": len(out["comparison"]),
        "all_matched": bool(per_drink) and all(v["ok"] for v in per_drink.values())
                       and len(per_drink) == len(DRINKS),
        "fields_compared": fields, "fields_matched": matched,
        "fields_mismatched": len(mismatches),
        "per_drink": per_drink, "mismatches": mismatches,
        "routes": {k: v.get("route") for k, v in out["comparison"].items()},
        "dataset_sha256": out["meta"]["dataset_sha256"],
        "dataset_commit": out["meta"]["dataset_commit"],
        "dataset_dirty": out["meta"]["dataset_dirty"],
        "doctor_clean": doctor_clean,
    }
except Exception as e:                   # noqa: BLE001 - keep the rows already collected
    out["error"] = f"{type(e).__name__}: {e}"
    out["traceback"] = traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
    print(out["traceback"])
finally:
    # No world change to restore: no settimespeed, no sandbox write, and the primings and the
    # cans are in this run directory's own copy of the fixture. So teardown is the whole
    # cleanup path, exactly as in s05_food_scan.py.
    out["wall_seconds"] = round(time.time() - t_start, 1)
    save(path, out, tl, server)          # evidence on disk before the shutdown can go wrong
    try:
        teardown(tl, server, clients)    # graceful: the quit/stop rcs land in the timeline
    finally:
        hard_kill(server, clients)       # guaranteed, whatever teardown did
        out["wall_seconds"] = round(time.time() - t_start, 1)
        save(path, out, tl, server)      # the committed artifact: post-teardown timeline+errors
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "drink-probe.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied -> {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")
print(json.dumps(out.get("summary", out.get("error", "no summary")), indent=1)[:9000])
