"""Slice 05 measured cross-check: the scanner's dataset against the running game.

One live session (server + client) that answers the two questions `data/food-items.json`
cannot answer about itself, because both halves of it were parsed out of the same text files
by the same tool:

  1. **Is the population right?** `items.count` walks `ScriptManager.getAllItems()` inside the
     loaded game and counts the `base:food` scripts and the fluid definitions. The dataset's
     counts come from `tools/food_scan.py` reading `media/scripts/generated/` as text. Two
     independent routes to the same numbers -- expected food 722, fluidDefs 61, drainable 150.
  2. **Does a record describe the item the game actually builds?** Ten items, one per axis the
     dataset has to get right (see `ITEMS`), spawned SERVER-side with RCON `additem` -- a
     client-spawned item is invisible to the server and makes `Eat` log a `SyncItemFields` NPE
     (S6, slice 01) -- and then read back on both sides:

       * client `item.script <type>` -> the SCRIPT `Item`'s seven getters: the same numbers the
         scanner parsed, but off the loaded script object rather than the file;
       * server `item.get admin <type>` -> the INSTANCE's fields: what `Item.InstanceItem` made
         of those numbers, which is what every eat/aging/cooking path in the game reads.

The instance transforms the script value, and those transforms are the second half of the
check: `HungerChange`/`ThirstChange` are divided by 100, `DaysFresh`/`DaysTotallyRotten` become
`offAge`/`offAgeMax` 1:1 **in days** (measured, exp02-20260910-030433: Steak's 2/4 read back as
2/4, not 48/96), and a threshold the script does not set reads back 1000000000.

Two rules keep the comparison honest:

  * **An absent key is not a zero.** The dataset writes `null` where the script has no such
    line, so the expected live value is that key's DEFAULT, and the defaults are themselves
    measured rather than assumed -- `SCRIPT_DEFAULTS` / `INSTANCE_DEFAULTS` below carry the
    run and the item each one was read off.
  * **A fluid container's nutrition is not the item's.** `build_item` overwrites every
    nutrition column of a `fluid_container` with its first listed fluid's and records
    `nutrition_source = fluid:<id>`, so `Base.Pop2.calories` is Cola's 400 while Pop2's own
    script block carries no nutrition line at all. Comparing that 400 against the item's script
    getter would compare two different things. The item routes therefore expect the DEFAULT for
    those six columns -- which is exactly the claim `nutrition_source` makes, under test -- and
    the number itself is checked against `fluid.script Cola` / `fluid.script JuiceGrape` in each
    drink's `fluid` route.

A mismatch is a FINDING, written into `comparison` and the report and left there. Nothing here
edits `data/` or `tools/`, and the artifact is copied byte-for-byte after teardown, never
hand-corrected.

Everything lands in `<run_dir>/food-scan.json`, copied at the end to
`testing/artifacts/<run-id>/food-scan.json`. No world change is made (no `settimespeed`), so
nothing needs restoring; run it with `python testing/pzt doctor` clean and nothing else live.
"""
import hashlib
import json
import os
import shutil
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
SPAWN_WAIT = 2.5         # RCON additem -> item visible in the inventory (slices 01/02)
TOL = 1e-4               # float compare: the instance fields come back as float32
ABSENT = 1000000000      # the "no threshold" sentinel, on both the script and the instance
EXPECT_FOOD, EXPECT_FLUIDDEFS, EXPECT_DRAINABLE = 722, 61, 150

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET = os.path.join(REPO, "data", "food-items.json")
DATASET_RETRIES, DATASET_RETRY_WAIT = 4, 5.0   # the file may be mid-regeneration; see load_dataset

# The ten, one per axis the dataset must get right (plan, Task 5 step 1). The note travels into
# the artifact so a reader can see what each row is there to catch.
ITEMS = [
    ("Base.Apple", "plain food: 7 evolved-recipe entries, both thresholds, no cooking keys "
                   "(so MinutesToCook/MinutesToBurn must read back as the 60/120 defaults)"),
    ("Base.Steak", "cookable 50/70, EvolvedRecipe carries a space (Stir fry:20) and a "
                   "|Cooked qualifier (Sandwich:5|Cooked); no ThirstChange"),
    ("Base.CannedCorn", "CannedFood+CantEat+Packaged sealed can with NO DaysFresh/"
                        "DaysTotallyRotten -> offAge/offAgeMax must stay 1000000000"),
    ("Base.CannedBologneseOpen", "opened can: both thresholds AND ReplaceOnUse"),
    ("Base.BreadSlices", "ReplaceOnCooked = Base.Toast; MinutesToCook 4 with no MinutesToBurn"),
    ("Base.ConeIcecream", "ReplaceOnRotten = Base.ConeIcecreamMelted; Packaged = false (the "
                          "false-vs-absent case)"),
    ("Base.RatKing", "DaysFresh == DaysTotallyRotten == 0 -- a present-but-zero threshold, "
                     "which is not the same input as an absent one"),
    ("Base.Salt", "spice: no macro key at all (calories/carbs/lipids/proteins all null) and a "
                  "POSITIVE ThirstChange (+20)"),
    ("Base.Pop2", "fluid container: Capacity 0.3, Fluids = Cola:1.0, nutrition_source fluid:Cola"),
    ("Base.JuiceBox", "fluid container: Capacity 0.2, Fluids = JuiceGrape:1.0, Eattime 160"),
]
# Ruling (plan decision point, task-5-amendments): an `additem` that fails for a sealed or
# uneatable item is answered by substituting the next item on the same axis and recording it --
# never by editing the dataset to match. Only the sealed-can axis has a ruled stand-in.
SUBSTITUTES = {"Base.CannedCorn": "Base.TinnedBeans"}
# The fluids behind the two drinks. `fluid.script` takes either `Cola` or `Base.Cola`, and
# reports which accessor named the definition (`fluidTypeRoute`) -- metadata, not a property,
# so it is recorded and never compared.
DRINK_FLUIDS = {"Base.Pop2": "Cola", "Base.JuiceBox": "JuiceGrape"}

# ---- what a missing key reads back as ---------------------------------------------------
# MEASURED, not assumed. `Base.HotDrink` has no DaysFresh, no DaysTotallyRotten and no
# HungerChange, and `item.script Base.HotDrink` in exp01-20260910-003929 answered
# 1000000000 / 1000000000 / 0. `Base.Apple` has no cooking keys and answered
# IsCookable false, MinutesToCook 60, MinutesToBurn 120 in the same run -- and its INSTANCE in
# exp02-20260910-030433 carries minutesToCook 60 / minutesToBurn 120, so the instance inherits
# the script defaults rather than zeroing them. `Base.Steak` has no ThirstChange and its
# instance reads thirstChange 0 (exp02), which is 0/100.
SCRIPT_DEFAULTS = {"HungerChange": 0.0, "ThirstChange": 0.0, "DaysFresh": ABSENT,
                   "DaysTotallyRotten": ABSENT, "IsCookable": False,
                   "MinutesToCook": 60, "MinutesToBurn": 120}
INSTANCE_DEFAULTS = {"calories": 0.0, "carbs": 0.0, "lipids": 0.0, "proteins": 0.0,
                     "hungChange": 0.0, "thirstChange": 0.0, "offAge": ABSENT,
                     "offAgeMax": ABSENT, "minutesToCook": 60, "minutesToBurn": 120}

# (live key, dataset column, factor). factor None = no arithmetic (booleans).
SCRIPT_FIELDS = (("HungerChange", "hunger_change", 1.0),
                 ("ThirstChange", "thirst_change", 1.0),
                 ("DaysFresh", "days_fresh", 1.0),
                 ("DaysTotallyRotten", "days_totally_rotten", 1.0),
                 ("IsCookable", "is_cookable", None),
                 ("MinutesToCook", "minutes_to_cook", 1.0),
                 ("MinutesToBurn", "minutes_to_burn", 1.0))
INSTANCE_FIELDS = (("calories", "calories", 1.0),
                   ("carbs", "carbohydrates", 1.0),
                   ("lipids", "lipids", 1.0),
                   ("proteins", "proteins", 1.0),
                   ("hungChange", "hunger_change", 0.01),
                   ("thirstChange", "thirst_change", 0.01),
                   ("offAge", "days_fresh", 1.0),
                   ("offAgeMax", "days_totally_rotten", 1.0),
                   ("minutesToCook", "minutes_to_cook", 1.0),
                   ("minutesToBurn", "minutes_to_burn", 1.0))
# Of those ten, only these six are `Food` getters; `offAge`/`offAgeMax`/`minutesToCook`/
# `minutesToBurn` are `InventoryItem`'s and every item carries them. So only these six may be
# absent from a `base:normal` fluid container's `item.get` -- measured in
# exp05-20260910-084109, where Pop2's instance answered 1000000000/1000000000/60/120 for the
# other four. An absence outside this set is a FINDING, not an "n/a" (see `compare`).
FOOD_ONLY_INSTANCE_FIELDS = ("calories", "carbs", "lipids", "proteins", "hungChange",
                             "thirstChange")
NOT_A_FOOD = ("fluid container: the instance is not a Food, so this Food-only getter does not "
              "answer; the four InventoryItem fields (offAge/offAgeMax/minutesToCook/"
              "minutesToBurn) must answer and do")
# The fluid definition's own getters against the dataset's fluid record. The /100 pair is the
# same ARITHMETIC as the item side's, applied somewhere else -- by the fluid script loader, with
# no item and no `Item.InstanceItem` involved (see FLUID_TRANSFORM): `fluids_Beverages.txt`
# writes `HungerChange = -12.0` for Cola and `fluid.script Cola` answers -0.12, while
# Calories/Carbohydrates/Lipids/Proteins are carried 1:1 (400 / 104 / 0 / 0).
FLUID_FIELDS = (("Calories", "calories", 1.0),
                ("Carbohydrates", "carbohydrates", 1.0),
                ("Lipids", "lipids", 1.0),
                ("Proteins", "proteins", 1.0),
                ("HungerChange", "hunger_change", 0.01),
                ("ThirstChange", "thirst_change", 0.01))
# 10 of the 61 fluids carry no `Properties` block at all, so a null column there means the
# definition sets no such key and the getter answers 0 -- the same rule as the item side.
FLUID_DEFAULTS = {k: 0.0 for k, _, _ in FLUID_FIELDS}
# The columns `build_item` overwrites from the joined fluid (a subset of NUTRITION_COLUMNS:
# the ones this experiment compares).
FLUID_SOURCED = {"calories", "carbohydrates", "lipids", "proteins", "hunger_change",
                 "thirst_change"}

# How each route's rows are LABELLED in the artifact: `(scale, absent key)`. The arithmetic is
# the same /100 on both, but it is applied in two different places and the artifact must not
# attribute one to the other: on an item it is the instance constructor (`Item.InstanceItem`
# reading the script `Item`), on a fluid it is the fluid script loader
# (`FluidDefinitionScript.getHungerChange @0-@10 L186` -- `fluids_Beverages.txt` writes Cola's
# `HungerChange = -12.0` and `fluid.script Cola` answers -0.12, with no item involved). Same
# for a null column: on the item route it means the ITEM script sets no such key, on the fluid
# route it means the FLUID definition does not (10 of the 61 fluids carry no `Properties`
# block at all).
ITEM_TRANSFORM = ("x%g (Item.InstanceItem)",
                  "default (the item script sets no such key)")
FLUID_TRANSFORM = ("x%g (FluidDefinitionScript.getHungerChange @0-@10 L186, the fluid script "
                   "loader)",
                   "default (the fluid definition sets no such key)")


def load_dataset(path):
    """The dataset, read ONCE at the start of the run: `(data, error, sha256)`.

    A concurrent fix round may be regenerating this file (it is rewritten whole, so a read can
    land mid-write and raise `ValueError`); the retry is for that and only that, and it sleeps
    BETWEEN attempts, never after the last one.

    The digest is taken of the SAME bytes that were parsed -- one read, hashed and decoded --
    rather than of a second read that a concurrent regeneration could have changed underneath.
    It is what makes the artifact self-identifying: `meta.dataset_commit` can only name a
    commit, and a working tree that has moved on makes that name wrong (see `git_short`)."""
    last = None
    for attempt in range(DATASET_RETRIES):
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
            return json.loads(raw.decode("utf-8")), None, hashlib.sha256(raw).hexdigest()
        except (ValueError, OSError, UnicodeDecodeError) as e:
            last = f"{type(e).__name__}: {e}"
            print(f"dataset unreadable (attempt {attempt + 1}/{DATASET_RETRIES}): {last}")
            if attempt + 1 < DATASET_RETRIES:
                time.sleep(DATASET_RETRY_WAIT)
    return None, last, None


def git_short(rel_path):
    """`git log -1 --format=%h -- <path>`: the newest commit that TOUCHED the path.

    That equals the provenance of the bytes just read only when the working tree is clean
    there. It is not the same question, and in exp05-20260910-084109 the two answers differed:
    the file had been regenerated by a concurrent fix round a minute before the run, so this
    returned `72ed836` -- the commit before that regeneration -- for bytes that were committed
    afterwards as `25870ad`. So the answer is recorded next to `dataset_sha256` (the bytes
    actually read) and `dataset_dirty` (below), which together identify the file without
    needing the index to agree with it."""
    try:
        p = subprocess.run(["git", "-C", REPO, "log", "-1", "--format=%h", "--", rel_path],
                           capture_output=True, text=True, timeout=30)
        return (p.stdout or "").strip() or f"git said nothing (rc={p.returncode})"
    except Exception as e:                       # noqa: BLE001 - provenance, never fatal
        return f"{type(e).__name__}: {e}"


def git_dirty(rel_path):
    """`git status --porcelain -- <path>` non-empty: the working tree differs from the index or
    HEAD, so `git_short`'s commit is NOT where the bytes came from.

    Returns `(dirty, note)`. `dirty` is `True` / `False` when git answered and **`None`** when it
    could not be asked -- unknown is a third state, and it must not be a truthy error string in
    the flag's own slot, where `if dirty:` would read it as "dirty" and a JSON consumer would
    have to type-check before believing it. The reason travels beside it as
    `meta.dataset_dirty_note`. Provenance, never fatal."""
    try:
        p = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", rel_path],
                           capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            return None, f"git status rc={p.returncode}"
        return bool((p.stdout or "").strip()), None
    except Exception as e:                       # noqa: BLE001 - provenance, never fatal
        return None, f"{type(e).__name__}: {e}"


def same(expected, live):
    """`abs(a-b) <= 1e-4` for numbers (the instance fields are float32: Steak's 31.62 reads
    back 31.620001), exact otherwise. Booleans first, because `isinstance(True, int)`."""
    if isinstance(expected, bool) or isinstance(live, bool):
        return bool(expected) == bool(live)
    if isinstance(expected, (int, float)) and isinstance(live, (int, float)):
        return abs(expected - live) <= TOL
    return expected == live


def compare(record, live, fields, defaults, source, absent_ok=None, route_nutrition=False,
            transform=ITEM_TRANSFORM):
    """One route's `{script, live, source, match}` rows, plus the provenance of each expectation.

    `script` is what the dataset says the live field must be AFTER the transform; `dataset` is
    the raw record value it came from (null where the script has no such key, in which case
    `script` is the measured default). `transform` is that route's `(scale, absent)` label pair
    -- the /100 belongs to `Item.InstanceItem` on an item route and to the fluid script loader
    on a fluid one, and the artifact says which.

    `absent_ok` is a per-FIELD `{live_key: why}` map, not a blanket permission: `match` is
    `"n/a"` only for a key that route legitimately cannot carry, and every other absence is a
    mismatch. That is counted apart from both matches and mismatches."""
    rows, bad = {}, []
    # `_common.ask` reports a wedged side as `{"error": ...}` -- a dict, so without the second
    # clause every field of it would take the "key absent" branch and a container's six
    # Food-only rows would be excused as "n/a". A failed read is a mismatch on every field, not
    # a legitimate absence. None of the three replies compared here carries an `error` key when
    # it succeeds (`TK.itemState`, `scriptValues`, `fluid.script` build their keys from fixed
    # lists), so the test is safe.
    live_ok = isinstance(live, dict) and "error" not in live
    scale_label, absent_label = transform
    for live_key, column, factor in fields:
        raw = record.get(column) if record else None
        row = {"dataset": raw}
        if route_nutrition and record and column in FLUID_SOURCED:
            # See the module docstring: the record's number here is the FLUID's, not the item's,
            # so the expectation is the default. The number is kept as `dataset_routed` rather
            # than dropped, so the artifact still shows WHICH value was routed past and a reader
            # can check it against the `fluid` route's rows.
            row["dataset_routed"] = raw
            row["dataset"] = None
            row["routed_to"] = record.get("nutrition_source")
            raw = None
        if raw is None:
            row["script"] = defaults.get(live_key)
            row["transform"] = absent_label
        elif factor in (None, 1.0):              # None = boolean, no arithmetic
            row["script"] = raw
            row["transform"] = "identity"
        else:
            row["script"] = raw * factor
            row["transform"] = scale_label % factor
        row["source"] = source
        if not live_ok:
            row["live"], row["match"] = None, False
            row["note"] = "no reply: " + str(live)[:160]
        elif live_key in live:
            row["live"] = live[live_key]
            row["match"] = same(row["script"], live[live_key])
        else:
            why = (absent_ok or {}).get(live_key)
            row["live"], row["live_absent"] = None, True
            row["match"] = "n/a" if why else False
            if why:
                row["note"] = why
        if row["match"] is False:
            bad.append({"field": live_key, "source": source, "script": row["script"],
                        "live": row["live"], "dataset_column": column})
        rows[live_key] = row
    return rows, bad


rec = fx.load("default")
run_id, run_dir = new_run_dir("exp05")
path = os.path.join(run_dir, "food-scan.json")
tl = Timeline()
server = make_server(run_dir, rec)
clients = []
t_start = time.time()
data, data_err, data_sha = load_dataset(DATASET)
dataset_dirty, dataset_dirty_note = git_dirty("data/food-items.json")
items_by_id = {r["id"]: r for r in (data or {}).get("items", [])}
fluids_by_id = {r["id"]: r for r in (data or {}).get("fluids", [])}
out = {"run_id": run_id,
       "meta": {"dataset": os.path.relpath(DATASET, REPO).replace("\\", "/"),
                # The three together are the provenance: the commit NAMES a version, the sha256
                # IS the bytes read, and `dataset_dirty` says whether the first can be trusted
                # to be the second (see `git_short`).
                "dataset_commit": git_short("data/food-items.json"),
                "dataset_sha256": data_sha,
                "dataset_dirty": dataset_dirty,
                "dataset_dirty_note": dataset_dirty_note,
                "dataset_read_error": data_err,
                "dataset_meta": (data or {}).get("meta"),
                "dataset_items": len(items_by_id), "dataset_fluids": len(fluids_by_id),
                "expected": {"food": EXPECT_FOOD, "fluidDefs": EXPECT_FLUIDDEFS,
                             "drainable": EXPECT_DRAINABLE},
                "tolerance": TOL, "spawn_wait_s": SPAWN_WAIT,
                "script_defaults": SCRIPT_DEFAULTS, "instance_defaults": INSTANCE_DEFAULTS},
       "items_count": None, "fluid_script": {}, "spot_checks": {}, "comparison": {},
       "summary": {}}
dirty_note = ""
if dataset_dirty:
    dirty_note = " [DIRTY: the bytes are NOT that commit]"
elif dataset_dirty is None:
    dirty_note = f" [dirty unknown: {dataset_dirty_note}]"
print(f"dataset {out['meta']['dataset_commit']}{dirty_note}"
      f" sha256 {str(data_sha)[:16]}: {len(items_by_id)} items, {len(fluids_by_id)} fluids")
try:
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

    def spawn(full_type):
        """RCON additem, settle, then the server's own reading of the instance."""
        ok, reply = server.rcon(f'additem "{USER}" "{full_type}" 1')
        line = str(reply) if ok else f"rcon failed: {reply}"
        time.sleep(SPAWN_WAIT)
        return line, srv("item.get", f"{USER} {full_type}")

    # ---- 1. the census -------------------------------------------------------
    out["items_count"] = srv("items.count", timeout=60)
    tl.mark("items_count", ok=isinstance(out["items_count"], dict))
    save(path, out, tl, server)

    # ---- 2. the two fluid definitions ---------------------------------------
    for fid in sorted(set(DRINK_FLUIDS.values())):
        out["fluid_script"][fid] = srv("fluid.script", fid, timeout=45)
    tl.mark("fluid_script", got=sorted(out["fluid_script"]))
    save(path, out, tl, server)

    # ---- 3. the ten spot checks ---------------------------------------------
    for full_type, axis in ITEMS:
        tl.mark("item_start", item=full_type)
        row = {"axis": axis, "requested": full_type}
        # `item.get` finds the FIRST match (`getFirstTypeRecurse`, PZTestKit_Server.lua:284),
        # not the newest, so a pre-existing copy in the fixture's inventory would be the one
        # read below. Asked before the spawn so the artifact says whether that happened.
        pre = srv("item.get", f"{USER} {full_type}", timeout=20)
        row["pre_existing"] = pre if isinstance(pre, dict) else str(pre)
        row["had_one_before_spawn"] = isinstance(pre, dict)
        row["rcon_additem"], live_get = spawn(full_type)
        spawned = full_type
        if not isinstance(live_get, dict) and full_type in SUBSTITUTES:
            # The ruling: same axis, recorded, dataset untouched.
            sub = SUBSTITUTES[full_type]
            row["substituted"] = {"for": full_type, "with": sub,
                                  "why": f"additem/item.get failed: {str(live_get)[:200]}"}
            row["rcon_additem_substitute"], live_get = spawn(sub)
            spawned = sub
            tl.mark("substituted", item=full_type, with_=sub)
        row["spawned"] = spawned
        row["item_get"] = live_get
        row["item_script"] = ask(c, "item.script", spawned, timeout=30)
        out["spot_checks"][full_type] = row
        save(path, out, tl, server)

        record = items_by_id.get(spawned)
        block = {"axis": axis, "spawned": spawned, "kind": (record or {}).get("kind"),
                 "nutrition_source": (record or {}).get("nutrition_source"),
                 "dataset_record_found": record is not None}
        if record is None:
            block["error"] = f"no dataset record for {spawned}"
            out["comparison"][full_type] = block
            continue
        is_container = str(record.get("nutrition_source", "")).startswith("fluid:")
        # A fluid container is a `base:normal` item with a FluidContainer component, not a
        # `Food`, so the six Food-only getters `TK.itemState` reads do not exist on the
        # instance. That is the expected reading, not a miss -- but only for those six: the
        # other four are `InventoryItem`'s and their absence would be a finding, so the
        # permission is per field.
        absent_ok = {k: NOT_A_FOOD for k in FOOD_ONLY_INSTANCE_FIELDS} if is_container else None
        block["script"], bad_s = compare(record, row["item_script"], SCRIPT_FIELDS,
                                         SCRIPT_DEFAULTS, "item.script",
                                         route_nutrition=is_container)
        block["instance"], bad_i = compare(record, live_get, INSTANCE_FIELDS,
                                           INSTANCE_DEFAULTS, "item.get", absent_ok=absent_ok,
                                           route_nutrition=is_container)
        bad = bad_s + bad_i
        if full_type in DRINK_FLUIDS:
            fid = DRINK_FLUIDS[full_type]
            frec = fluids_by_id.get(fid)
            block["fluid_id"] = fid
            block["fluid"], bad_f = compare(frec, out["fluid_script"].get(fid), FLUID_FIELDS,
                                            FLUID_DEFAULTS, f"fluid.script {fid}",
                                            transform=FLUID_TRANSFORM)
            bad += bad_f
            # The scanner's own join, checked inside the dataset: the item's nutrition columns
            # must BE the fluid's, which is what `nutrition_source` claims and what makes the
            # live fluid reading evidence about the item record at all.
            block["fluid_join"] = {col: {"item": record.get(col),
                                         "fluid": (frec or {}).get(col),
                                         "match": same(record.get(col), (frec or {}).get(col))}
                                   for col in sorted(FLUID_SOURCED)}
            for col, jr in block["fluid_join"].items():
                if not jr["match"]:
                    bad.append({"field": col, "source": "dataset join", "script": jr["fluid"],
                                "live": jr["item"], "dataset_column": col})
        block["mismatches"] = bad
        block["matched"] = not bad
        out["comparison"][full_type] = block
        tl.mark("item_done", item=full_type, mismatches=len(bad))
        save(path, out, tl, server)

    # ---- 4. the verdict ------------------------------------------------------
    cnt = out["items_count"] if isinstance(out["items_count"], dict) else {}
    by_type = cnt.get("byType") or {}
    dcounts = ((data or {}).get("meta") or {}).get("counts") or {}
    counts = {"food": {"live": cnt.get("food"), "dataset": dcounts.get("food"),
                       "expected": EXPECT_FOOD},
              "fluidDefs": {"live": cnt.get("fluidDefs"), "dataset": dcounts.get("fluids"),
                            "expected": EXPECT_FLUIDDEFS},
              "drainable": {"live": by_type.get("base:drainable"),
                            "dataset": dcounts.get("drainable"), "expected": EXPECT_DRAINABLE},
              "base_food_bucket": {"live": by_type.get("base:food"),
                                   "dataset": dcounts.get("food"), "expected": EXPECT_FOOD}}
    for k, v in counts.items():
        v["match"] = v["live"] == v["expected"] == v["dataset"]
    fields = matched = na = 0
    per_item, mismatches = {}, []
    for full_type, block in out["comparison"].items():
        n = m = z = 0
        for route in ("script", "instance", "fluid"):
            for key, r in (block.get(route) or {}).items():
                n += 1
                if r["match"] is True:
                    m += 1
                elif r["match"] == "n/a":
                    z += 1
        per_item[full_type] = {"fields": n, "matched": m, "na": z,
                               "mismatched": len(block.get("mismatches") or []),
                               "spawned": block.get("spawned"),
                               "ok": not block.get("mismatches")}
        for bad in (block.get("mismatches") or []):
            mismatches.append(dict(bad, item=full_type))
        fields += n
        matched += m
        na += z
    out["summary"] = {
        "counts": counts,
        "counts_all_match": all(v["match"] for v in counts.values()),
        "items_checked": len(out["comparison"]),
        "items_all_matched": all(v["ok"] for v in per_item.values()) and len(per_item) == len(ITEMS),
        "fields_compared": fields, "fields_matched": matched, "fields_na": na,
        "fields_mismatched": len(mismatches),
        "per_item": per_item, "mismatches": mismatches,
        "substitutions": {k: v["substituted"] for k, v in out["spot_checks"].items()
                          if v.get("substituted")},
        "pre_existing_instances": sorted(k for k, v in out["spot_checks"].items()
                                         if v.get("had_one_before_spawn")),
        "dataset_commit": out["meta"]["dataset_commit"],
        "dataset_sha256": out["meta"]["dataset_sha256"],
        "dataset_dirty": out["meta"]["dataset_dirty"],
        "dataset_dirty_note": out["meta"]["dataset_dirty_note"],
    }
except Exception as e:                   # noqa: BLE001 - keep the rows already collected
    out["error"] = f"{type(e).__name__}: {e}"
    out["traceback"] = traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
    print(out["traceback"])
finally:
    # This experiment makes no world change (no settimespeed, no character write) -- the only
    # thing it leaves behind is ten spawned items in a COPY of the fixture inside this run dir,
    # which the run dir owns. So there is nothing to restore, and the teardown is the whole
    # cleanup path.
    out["wall_seconds"] = round(time.time() - t_start, 1)
    save(path, out, tl, server)          # evidence on disk before the shutdown can go wrong
    try:
        teardown(tl, server, clients)    # graceful: the quit/stop rcs land in the timeline
    finally:
        hard_kill(server, clients)       # guaranteed, whatever teardown did
        out["wall_seconds"] = round(time.time() - t_start, 1)
        save(path, out, tl, server)      # the committed artifact: post-teardown timeline+errors
        # A byte-for-byte copy of THAT file, so the tracked artifact cannot drift from the run
        # directory that produced it.
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "food-scan.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied -> {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")
print(json.dumps(out.get("summary", out.get("error", "no summary")), indent=1)[:9000])
