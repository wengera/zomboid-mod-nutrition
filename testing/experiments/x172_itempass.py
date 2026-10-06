"""x172-itempass -- Plan 6 Task 12, the acceptance boot of the item pass, LIVE. The first load of the
generated NR_Data_Nutrients.lua (317 898 B, 522 item entries + 47 fluid entries, 31 keys each),
NR_Data_Infer.lua (16 801 B) and NR_ItemPass_Food.txt (90 121 B, 522 partial `module Base` blocks) by
the game. ONE boot of profile `x17-itempass` (PZTestKit + NutritionRevamp Mode 1 LegacyMirror +
TKX_ItemOverride + TKX_DeclaredFood; `Nutrition = false`; DayLength 1, so a game minute is 0.625 s
wall; sleep false/false). The run id prefix is `x172`; ONE artifact `itempass.json`. Shape:
x161_fatigue.py (step, persist, run_phase, mod_error, the RCON spawn resolved on the client, the
record reads, the offline kernel in lupa) with x171_scripts.py's two-sided item reads.

THE LOAD TEST. A script error or a Lua error at boot is the primary reading: if the server log carries
a ScriptManager / InvalidParameterException / NR_ error line by first sight, or the client reached the
debugger, or the mod's data loaders are absent on either side, the arms after S0 and A are skipped
(nothing is worked around) and the session is torn down with both logs grepped.

WHERE THE EATEN VECTOR IS READ (decided before the run). The intake's per-minute ingested sum
(`NutritionRevamp.server.intake.lastIngested`) lives for one slow minute (0.625 s wall) and the record
carries no per-key ingested total, so the vector is read off the record's stomach buffer
(`NutritionRevamp.players admin.stomach.buffer`, global modData), which `IN.land` adds the vector into
(after the B12 ceiling, with caffeine and ethanol moved to the gut lane) and which kinetics empties by
ONE scalar fraction for every key each slow minute (K.stomach.empty). Before each eat or drink the
driver writes every one of the 31 buffer keys to 0 (`globalmoddata.setpath`) and reads them back; after
the landing the buffer is the landed vector times one unknown factor s = prod(1 - f) <= 1. The driver
takes s off a reference key (calories for a food, water for a fluid) and grades the other 30 keys of
buffer / s against the prediction: an exact test of the vector's SHAPE at 1e-6 relative, with the
reference key's own absolute value carried by s (reported; s must lie in (0, 1]). A second buffer read
a few seconds later checks the ratio method itself (the ratios unchanged while s falls).

ARMS (order fixed; eats first, because `eat.action` picks the client's FIRST item of a type and arm B's
client-local spawns would shadow an RCON item):
  S0  first sight: versions, the data loaders on both sides (`NutritionRevamp.data.nutrients.get`,
      `.fluids.get`, `.infer._default.n`), options, intake counters, items.count, server errors so far,
      the client debugger marker.
  A   the load: `items.count` total / foodByModule (baseline exp05-20260910-084109: total 5092, Base 722;
      prediction Base 722 and total 5092 + the TKX item blocks the two TKX scripts declare, counted from
      the files), the boot times (server launch to SERVER STARTED; client markers to ready; the session
      ready wall from the driver's start), three `tick.rate 20` windows against x161b's 10 s window, the
      generated files' sizes read from disk.
  C   Base.Apple eaten whole (RCON additem; `foodtimer.set 0`; client `eat.action Base.Apple 1`): the
      buffer against the TABLE's Apple entry x share (instance scale instBase / scriptHunger), macros the
      live getters x frac, K.retention.apply with the live flags, vitB12 through K.interact.b12Ceiling,
      caffeine and ethanol 0; `lastIntake.source` = `baseline` (IN.sourceOf's string for a table hit).
      THE RIVAL BLOCK: TKX_ItemOverride restates `item Apple` in full (Calories 400.0, Carbohydrates
      25.13, Lipids 0.31, Proteins 0.47) and `item Orange` (Calories 400.0). The replay is sorted by the
      stored script path (#1183): `media/scripts/nr_itempass_food.txt` < `media/scripts/tkx_item_override.txt`,
      so the TKX body replays last and wins every key it names (mod id, folder and display name sort the
      same way: X19 is not separated). The live Apple is therefore predicted at 400 / 25.13 / 0.31 / 0.47,
      not the pass's 94.59 / 25.12 / 0.31 / 0.47: arm C's macros follow the live item (IN.assemble), its
      27 other keys the table.
  C2  Base.Bread eaten whole the same way (a clean re-based food with no rival): the table's 40.02 mg
      phytate per item lands x share.
  D   TKX.FibreBar (no table entry, no FoodType line in its script): `source = inferred`; the vector =
      K.vector.infer(live macros, live getFoodType, NR.data.infer) x frac -- the template is whichever
      the live FoodType selects (its entry, else `_default`), recomputed from NR_Data_Infer.lua in lupa.
  E   TKX.DeclaredBar: `witness.moddata item:<id> NR_Nutrients` both sides before the eat (the X15
      route on a `module TKX` item); eaten: `source = declared`; the vector = K.vector.declared(the
      string read) with the item's own macros, x share; vitB12's 0.5 lands through the ceiling.
  F   Coffee 0.25 L (RCON additem Base.WaterBottle; server `fluid.fill admin Base.WaterBottle Coffee
      0.25`; client `drink.action Base.WaterBottle 1`): the buffer against NR.data.fluids.get("Coffee")
      x the litres drunk (container before - after); caffeine lands on the gut lane (pendingCaf, then
      acute.gutCaf / acute.caf): the rise of gutCaf + caf + pendingCaf against the dose, within 5 % (the
      caf elimination at the 5 h half-life over the read delay). Then Cola 0.25 L the same.
  B   eleven clean re-based foods + the two rival types: for each, RCON additem -> the server's
      `witness.fields` (the server's instance) and the client's (the replicated copy), a client-local
      `item.spawn` -> the client's own read (the client's own script), `witness.moddata NR_Nutrients`
      both sides (arm G), `item.script` both sides. Prediction per field: the script file's `%.2f`
      value as float32 for the four macros (the TKX value where the TKX body wins), the DATASET's
      HungerChange / ThirstChange / 100 as float32 (a null -> 0); compared at 1e-5 relative.
  G   every arm-B food and the eaten Apple: NR_Nutrients missing on both sides.
  I   Base.Bleach and Base.SoupBowlClay: no block in the script file; `item.script` both sides equal
      the dataset's own values. Base.Butter (mapped in no-nutrition.csv) is in arm B's list.
  H   the checksum's normal arm: both sides connected to the end (`lua.global TK.version` on the client
      last), no checksum line in either log (`will be kicked`, `checksums do not match`,
      `ChecksumUpdate`, `checksum-File doesn't match`). The account is the fixture's admin, whose role
      holds BypassLuaChecksum (#3139): this arm reads connection under the bypass, not the gate.
  Z   counters, lastError, the record's lastIntake, the client's TK.version, both logs.

PREDICTIONS are computed by `predict_offline()` BEFORE the boot from the three generated Lua files
(loaded in lupa with the kernel), the script file, the dataset and the two TKX scripts, and written into
the artifact's `predictions` at start; the eat and drink predictions that need live inputs (share, frac,
the live macros and flags, the litres) are recomputed in `grade_all()` from the same lupa state.

DEVIATIONS FROM THE AMENDMENTS (decided before the run):
  1. The eaten vector is read off the stomach buffer by the zero-then-ratio method above, not off an
     `ingested` record key (the record has none; `lastIngested` lives one slow minute).
  2. Items are spawned by RCON `additem` (server-instantiated, synced), not server `inventory.add`
     (which the client never hears of, so `eat.action` would spawn a client-local item the server
     refuses); x151r2 / x161f's route.
  3. TKX.FibreBar's script carries no FoodType line (the amendments say Fruits): the template is the
     one its live getFoodType selects, recomputed, whichever it is.
  4. The apple arm's macros follow the TKX_ItemOverride Apple body the profile carries (above); arm C2
     (Bread) is the clean table arm.
  5. items.count's prediction is total 5092 + the four TKX item blocks (FibreBar, FibreBarNamed,
     FibreBarJson, DeclaredBar), not "+ the two".
  6. tick.rate runs three 20 s windows (60 s), against x161b's one 10 s window (10.104011887072808).
  7. IN.typeInfo instances an item only for a dish or craft input; no arm eats one, so its cost is
     unmeasured here (stated, not read).
  8. The mod is not touched: HEAD's tree runs underneath every arm.

**The two rules a driver never breaks.**
  1. A driver is NEVER edited after its run; a post-run edit is a skew note.
  2. A reading that comes back trivial, unmeasured or falsified is written as such, never re-run.
"""
import glob
import json
import math
import os
import re
import shutil
import struct
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, grep_file, make_client,      # noqa: E402
                         make_server, teardown, verify)

PROFILE = "x17-itempass"
SESSION = ("Plan 6 Task 12, the item-pass acceptance: the generated table, inference templates and partial "
           "script blocks loaded live (A), re-based foods on both sides (B), the table, inferred and declared "
           "vectors landing (C, C2, D, E), the fluid table (F), no mod key on a vanilla food (G), the checksum's "
           "normal arm (H), reasoned records untouched (I); one boot of x17-itempass at DayLength 1")
ARTIFACT = "itempass.json"
USER = "admin"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
MOD_ROOT = os.path.join(REPO, "mod", "NutritionRevamp")
MOD_LUA = os.path.join(MOD_ROOT, "common", "media", "lua")
SHARED = os.path.join(MOD_LUA, "shared")
SCRIPT_FILE = os.path.join(MOD_ROOT, "common", "media", "scripts", "NR_ItemPass_Food.txt")
GEN_FILES = {"NR_Data_Nutrients.lua": os.path.join(SHARED, "NR_Data_Nutrients.lua"),
             "NR_Data_Infer.lua": os.path.join(SHARED, "NR_Data_Infer.lua"),
             "NR_ItemPass_Food.txt": SCRIPT_FILE}
TKX_OVERRIDE = os.path.join(REPO, "testing", "experiments", "TKX_ItemOverride", "42.20", "media", "scripts",
                            "tkx_item_override.txt")
TKX_DECLARED = os.path.join(REPO, "testing", "experiments", "TKX_DeclaredFood", "42.20", "media", "scripts",
                            "tkx_declared_food.txt")
# the stored replay key per #1183: the script path relative to the version dir (or common/), lowered
NR_STORED = "media/scripts/nr_itempass_food.txt"
TKX_STORED = "media/scripts/tkx_item_override.txt"
DATASET = os.path.join(REPO, "data", "food-items.json")
NUTRIENTS_JSON = os.path.join(REPO, "data", "food-nutrients.json")
SELFTEST = os.environ.get("X172_SELFTEST") == "1"

BASELINE_RUN = "exp05-20260910-084109"     # food-scan.json items_count (x171p read the same 5092 / 722)
BASELINE_TOTAL = 5092
BASELINE_BASE_FOOD = 722
X161B_RUN = "x161b-20261006-065751"
X161B_TICK = 10.104011887072808            # body.json phases.J.tick.result.ticksPerSecond (10 s window)

STORE = "NutritionRevamp.players"
INTAKE = "NutritionRevamp.server.intake"
COUNTERS = ("eats", "landed", "failures", "sips", "cancels", "declaredMalformed", "unreadableAfter", "passthrough")
KEYS = ("calories", "carbs", "lipids", "proteins", "fibre", "water", "vitC", "iron", "phytate", "retinol",
        "carotene", "vitD", "vitE", "vitK", "thiamine", "riboflavin", "niacin", "vitB6", "folate", "vitB12",
        "choline", "sodium", "potassium", "calcium", "magnesium", "zinc", "iodine", "selenium", "efa",
        "caffeine", "ethanol")
MACROS = "getCalories,getCarbohydrates,getLipids,getProteins,getHungChange,getThirstChange"
B_FIELDS = MACROS + ",getFullType,getDisplayCategory,getCategory,getFoodType,getID"
B_FIELD_COUNT = 11
EAT_FIELDS = (MACROS + ",getBaseHunger,getFoodType,isCooked,isBurnt,isRotten,isFrozen,getFullType,getID,"
              "getThirstChangeUnmodified")
EAT_FIELD_COUNT = 16
GETTER_KEY = {"getCalories": "calories", "getCarbohydrates": "carbs", "getLipids": "lipids", "getProteins": "proteins"}
SCRIPT_KEY = {"Calories": "getCalories", "Carbohydrates": "getCarbohydrates", "Lipids": "getLipids",
              "Proteins": "getProteins"}

B_FOODS = ("Base.Banana", "Base.Butter", "Base.Rabbitmeat", "Base.Crisps", "Base.Cereal", "Base.Bread",
           "Base.Steak", "Base.CannedCorn", "Base.CannedCornOpen", "Base.Cricket", "Base.Acorn")
RIVALS = ("Base.Apple", "Base.Orange")
I_TYPES = ("Base.Bleach", "Base.SoupBowlClay")
APPLE, BREAD, FIBRE, DECLARED = "Base.Apple", "Base.Bread", "TKX.FibreBar", "TKX.DeclaredBar"
BOTTLE = "Base.WaterBottle"
FLUIDS = (("Coffee", 0.25), ("Cola", 0.25))
REL_TOL = 1e-6          # the ratio test on the buffer
FIELD_REL_TOL = 1e-5    # the float32 getter test
CAF_TOL = 0.05
TICK_S, TICK_N = 20, 3
EAT_WAIT_S, LAND_POLL = 60, 0.6
DRINK_SETTLE_S = 30
SECOND_READ_DELAY = 4.0
SPAWN_WAIT, SPAWN_TRIES = 2.5, 6
HEALTH_GUARD = 40.0

LOG_RX = re.compile(r"NR_|NutritionRevamp|InvalidParameterException|ScriptManager|ItemPass|tkx_|TKX|"
                    r"Exception|ERROR|LuaError|STACK TRACE|tried to call nil|attempted to index", re.I)
LOG_LIMIT = 80
CHECKSUM_RX = re.compile(r"will be kicked|checksums do not match|ChecksumUpdate|checksum-File doesn't match|"
                         r"Timed out connection because checksum", re.I)
CHECKSUM_LIMIT = 20
LOAD_RX = re.compile(r"NR_Data_Nutrients|NR_Data_Infer|NR_ItemPass_Food", re.I)
LOAD_LIMIT = 20
BOOT_ERR_RX = re.compile(r"ScriptManager|InvalidParameterException|NR_[A-Z][A-Za-z_]*\.(lua|txt)|NutritionRevamp|"
                         r"nr_itempass", re.I)
MOD_ERR_RX = re.compile(r"NutritionRevamp|NR_[A-Z][A-Za-z_]*\.lua|intake: .*failed|nutrients: .* failed")


def to_num(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def f32(x):
    try:
        return struct.unpack("f", struct.pack("f", x))[0]
    except (OverflowError, struct.error, TypeError):
        return None


# ---------------------------------------------------------------- offline inputs (no game)
class Kernel:
    def __init__(self):
        import lupa.lua51 as lua51
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        files = ([os.path.join(SHARED, "NR_Core.lua")] + sorted(glob.glob(os.path.join(SHARED, "NR_Kernel*.lua")))
                 + sorted(glob.glob(os.path.join(SHARED, "NR_Data*.lua"))))
        self.files = [os.path.relpath(p, REPO).replace(os.sep, "/") for p in files]
        loader = self.rt.eval("function(src, name) return assert(loadstring(src, name)) end")
        for p in files:
            with open(p, encoding="utf-8") as fh:
                loader(fh.read(), "@" + os.path.basename(p))()
        self.NR = self.rt.globals().NutritionRevamp
        self.K = self.NR.kernel

    def table(self, d):
        t = self.rt.table()
        for k, v in d.items():
            t[k] = self.table(v) if isinstance(v, dict) else v
        return t

    def vec(self, t):
        if t is None:
            return None
        return {k: float(t[k]) if t[k] is not None else None for k in KEYS}

    def item(self, full):
        return self.vec(self.NR.data.nutrients.get(full))

    def fluid(self, name):
        return self.vec(self.NR.data.fluids.get(name))

    def infer_template(self, food_type):
        T = self.NR.data.infer
        hit = T[food_type] if food_type else None
        return ("type:" + food_type) if hit is not None else "_default"

    def infer(self, macros, food_type):
        m = self.table({"calories": macros["calories"], "carbs": macros["carbs"], "lipids": macros["lipids"],
                        "proteins": macros["proteins"]})
        return self.vec(self.K.vector.infer(m, food_type, self.NR.data.infer))

    def declared(self, s):
        v, extra = self.K.vector.declared(s)
        extra_py = None
        if extra is not None and not isinstance(extra, str):
            extra_py = [extra[i] for i in range(1, len(extra) + 1)]
        elif isinstance(extra, str):
            extra_py = extra
        return self.vec(v), extra_py

    def retention(self, v, flags):
        out = self.K.retention.apply(self.table(v), self.table(flags))
        return self.vec(out)

    def b12(self, a):
        return float(self.K.interact.b12Ceiling(a))

    def meat_scale(self, inst_base, script_hunger):
        return (inst_base / script_hunger) if script_hunger not in (0, None) else 1.0


def parse_blocks(fname):
    """{module: {item: {key: rawvalue}}} for a script file (block comments stripped; `,` ends a value)."""
    with open(fname, encoding="utf-8") as fh:
        text = re.sub(r"/\*.*?\*/", "", fh.read(), flags=re.S)
    out, module, item = {}, None, None
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^module\s+(\S+)", s)
        if m:
            module = m.group(1)
            out.setdefault(module, {})
            continue
        m = re.match(r"^item\s+(\S+)", s)
        if m and module is not None:
            item = m.group(1)
            out[module][item] = {}
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?),?\s*$", s)
        if m and module is not None and item is not None:
            out[module][item][m.group(1)] = m.group(2)
    return out


def load_dataset():
    with open(DATASET, encoding="utf-8") as fh:
        d = json.load(fh)
    return {r["id"]: r for r in d["items"]}


def load_nutrients_json():
    with open(NUTRIENTS_JSON, encoding="utf-8") as fh:
        d = json.load(fh)
    return {r["pz_id"]: r for r in d["items"]}, d.get("fluids")


def predict_field_set(full, nr_blocks, tkx_blocks, dataset):
    """The predicted getter values of one Base food under the replay order #1183 gives, with the two
    alternatives (NR last / TKX last) kept for the record."""
    mod, name = full.split(".", 1)
    nr = (nr_blocks.get(mod) or {}).get(name) or {}
    tkx = (tkx_blocks.get(mod) or {}).get(name) or {}
    ds = dataset.get(full) or {}
    order = sorted([(NR_STORED, "nr", nr), (TKX_STORED, "tkx", tkx)])
    merged, winner = {}, {}
    for _key, who, body in order:                       # replayed in sorted order, the last wins per key
        for sk in SCRIPT_KEY:
            if sk in body:
                merged[sk] = float(body[sk])
                winner[sk] = who
    for sk in SCRIPT_KEY:
        if sk not in merged:                            # neither body names it: vanilla's own value
            v = ds.get({"Calories": "calories", "Carbohydrates": "carbohydrates", "Lipids": "lipids",
                        "Proteins": "proteins"}[sk])
            merged[sk] = float(v) if v is not None else 0.0
            winner[sk] = "vanilla"
    pred = {SCRIPT_KEY[sk]: f32(merged[sk]) for sk in SCRIPT_KEY}
    hc, tc = ds.get("hunger_change"), ds.get("thirst_change")
    pred["getHungChange"] = f32((hc or 0.0) / 100.0)
    pred["getThirstChange"] = f32((tc or 0.0) / 100.0)
    alt_nr_only = {SCRIPT_KEY[sk]: f32(float(nr[sk])) for sk in SCRIPT_KEY if sk in nr}
    return {"pred": pred, "winner": winner, "nr_block": {k: nr.get(k) for k in SCRIPT_KEY if k in nr},
            "tkx_block": {k: tkx.get(k) for k in SCRIPT_KEY if k in tkx}, "sort_order": [o[0] for o in order],
            "nr_only_alternative": alt_nr_only,
            "dataset": {"hunger_change": hc, "thirst_change": tc, "calories": ds.get("calories"),
                        "carbohydrates": ds.get("carbohydrates"), "lipids": ds.get("lipids"),
                        "proteins": ds.get("proteins")}}


def predict_offline(KK):
    nr_blocks = parse_blocks(SCRIPT_FILE)
    tkx_blocks = parse_blocks(TKX_OVERRIDE)
    dec_blocks = parse_blocks(TKX_DECLARED)
    dataset = load_dataset()
    nj, _ = load_nutrients_json()
    P = {"files": {k: os.path.getsize(p) for k, p in GEN_FILES.items()},
         "script_blocks": len((nr_blocks.get("Base") or {})),
         "kernel_files": KK.files}
    new_items = sorted(f"TKX.{n}" for n in (tkx_blocks.get("TKX") or {})) + sorted(
        f"TKX.{n}" for n in (dec_blocks.get("TKX") or {}))
    P["items_count"] = {"total": BASELINE_TOTAL + len(new_items), "foodByModule.Base": BASELINE_BASE_FOOD,
                        "foodByModule.TKX": len(new_items), "new_items": new_items}
    P["B"] = {}
    for full in B_FOODS + RIVALS:
        P["B"][full] = predict_field_set(full, nr_blocks, tkx_blocks, dataset)
        P["B"][full]["in_script_file"] = full.split(".", 1)[1] in (nr_blocks.get("Base") or {})
        P["B"][full]["confidence"] = (nj.get(full) or {}).get("confidence")
        P["B"][full]["portion_source"] = (nj.get(full) or {}).get("portion_source")
    P["I"] = {}
    for full in I_TYPES:
        ds = dataset.get(full) or {}
        P["I"][full] = {"in_script_file": full.split(".", 1)[1] in (nr_blocks.get("Base") or {}),
                        "table_entry": KK.item(full) is not None,
                        "no_nutrition_reason": (nj.get(full) or {}).get("no_nutrition_reason"),
                        "dataset_props": {k: (ds.get("props_raw") or {}).get(k) for k in
                                          ("HungerChange", "ThirstChange", "DaysFresh", "DaysTotallyRotten",
                                           "IsCookable", "MinutesToCook", "MinutesToBurn")}}
    P["table"] = {t: KK.item(t) for t in (APPLE, BREAD, FIBRE, DECLARED)}
    P["table_json_per_item"] = {t: (nj.get(t) or {}).get("per_item") for t in (APPLE, BREAD)}
    P["fluids"] = {n: KK.fluid(n) for n, _l in FLUIDS}
    P["declared_script"] = ((dec_blocks.get("TKX") or {}).get("DeclaredBar") or {}).get("NR_Nutrients")
    P["fibrebar_script"] = (tkx_blocks.get("TKX") or {}).get("FibreBar")
    P["infer_templates"] = {"_default_n": float(KK.NR.data.infer["_default"].n),
                            "fibrebar_template_if_no_foodtype": KK.infer_template(None)}
    P["fibrebar_infer_if_no_foodtype"] = KK.infer({"calories": 250.0, "carbs": 30.0, "lipids": 5.0, "proteins": 8.0},
                                                  None)
    dv, extra = KK.declared(P["declared_script"] or "")
    P["declared_vector_from_script"] = dv
    P["declared_extra"] = extra
    P["b12_ceiling_0.5"] = KK.b12(0.5)
    return P


def buffer_prediction(KK, kind, live, table_vec=None, fluid_vec=None, litres=None, declared_str=None):
    """The vector IN.land adds to the stomach buffer, recomputed from the Lua files in lupa.
    kind: table | inferred | declared | fluid. live: the server's pre-eat fields + lastIntake's share/frac."""
    note = {}
    if kind == "fluid":
        v = {k: (fluid_vec[k] or 0.0) * litres for k in KEYS}
        ingested = dict(v)
    else:
        share, frac = live["share"], live["frac"]
        macros = {"calories": live["getCalories"], "carbs": live["getCarbohydrates"],
                  "lipids": live["getLipids"], "proteins": live["getProteins"]}
        if kind == "inferred":
            base = KK.infer(macros, live.get("getFoodType"))
            note["template"] = KK.infer_template(live.get("getFoodType"))
            factor, scale = frac, 1.0
        else:
            if kind == "declared":
                base, extra = KK.declared(declared_str)
                note["declared_extra"] = extra
                for k in ("calories", "carbs", "lipids", "proteins"):
                    base[k] = macros[k]
            else:
                base = dict(table_vec)
            scale = KK.meat_scale(live["getBaseHunger"], live["scriptHunger"])
            factor = share
        v = {k: (base[k] or 0.0) * scale * factor for k in KEYS}
        burnt = live.get("isBurnt") is True
        d = 5.0 if burnt else 1.0
        for k in ("calories", "carbs", "lipids", "proteins"):
            v[k] = macros[k] * frac / d
        flags = {"cooked": live.get("isCooked") is True, "burnt": burnt, "rotten": live.get("isRotten") is True,
                 "frozen": live.get("isFrozen") is True}
        v = KK.retention(v, flags)
        note.update({"scale": scale, "factor": factor, "flags": flags})
        ingested = dict(v)
    v["vitB12"] = KK.b12(v["vitB12"] or 0.0)
    v["caffeine"] = 0.0
    v["ethanol"] = 0.0
    return v, ingested, note


def ratio_grade(pred, buf, ref):
    """buffer / s against pred, s = buf[ref] / pred[ref]."""
    if not isinstance(buf, dict):
        return {"ok": False, "why": "no buffer"}
    b = {k: to_num(buf.get(k)) for k in KEYS}
    if b[ref] is None or not pred.get(ref):
        return {"ok": False, "why": f"reference {ref} unreadable or zero"}
    s = b[ref] / pred[ref]
    rows, ok, worst = {}, True, 0.0
    for k in KEYS:
        if b[k] is None:
            rows[k] = {"pred": pred[k], "buffer": None, "ok": False}
            ok = False
            continue
        m = b[k] / s
        p = pred[k]
        if p == 0:
            good = abs(m) <= 1e-9
            rel = None if good else float("inf")
        else:
            rel = abs(m - p) / abs(p)
            good = rel <= REL_TOL
            worst = max(worst, rel)
        ok = ok and good
        rows[k] = {"pred": p, "buffer": b[k], "measured": m, "rel": rel, "ok": good}
    s_ok = 0 < s <= 1 + 1e-9
    return {"ok": ok and s_ok, "s": s, "s_ok": s_ok, "ref": ref, "worst_rel": worst, "rows": rows}


def field_grade(fields, pred):
    if not isinstance(fields, dict):
        return {"ok": False, "why": "no fields"}
    rows, ok = {}, True
    for k, p in pred.items():
        g = fields.get(k)
        if not isinstance(g, (int, float)) or isinstance(g, bool):
            rows[k] = {"pred": p, "got": g, "ok": False}
            ok = False
            continue
        if p == 0:
            good = abs(g) <= 1e-7
            rel = None
        else:
            rel = abs(g - p) / abs(p)
            good = rel <= FIELD_REL_TOL
        ok = ok and good
        rows[k] = {"pred": p, "got": g, "rel": rel, "ok": good}
    return {"ok": ok, "rows": rows}


if SELFTEST:
    KK0 = Kernel()
    PP = predict_offline(KK0)
    print(json.dumps({k: PP[k] for k in ("files", "script_blocks", "items_count", "infer_templates",
                                         "declared_script", "declared_extra", "b12_ceiling_0.5")}, indent=1))
    for full in B_FOODS + RIVALS:
        print(full, PP["B"][full]["pred"], PP["B"][full]["winner"], PP["B"][full]["confidence"])
    print("I", json.dumps(PP["I"]))
    live = {"share": 1.0, "frac": 1.0, "getCalories": f32(94.59), "getCarbohydrates": f32(25.12),
            "getLipids": f32(0.31), "getProteins": f32(0.47), "getBaseHunger": f32(-0.16), "scriptHunger": -0.16}
    v, ing, note = buffer_prediction(KK0, "table", live, table_vec=PP["table"][APPLE])
    print("apple buffer pred", {k: v[k] for k in ("calories", "vitC", "fibre", "water", "vitB12")}, note)
    fake = {k: (v[k] * 0.9) for k in KEYS}
    print("ratio self", ratio_grade(v, fake, "calories")["ok"])
    live2 = dict(live, getCalories=250.0, getCarbohydrates=30.0, getLipids=5.0, getProteins=8.0, getFoodType=None)
    v2, _i, n2 = buffer_prediction(KK0, "inferred", live2)
    print("fibrebar", {k: v2[k] for k in ("calories", "fibre", "water", "vitC", "sodium")}, n2)
    live3 = dict(live, getCalories=180.0, getCarbohydrates=20.0, getLipids=6.0, getProteins=9.0,
                 getBaseHunger=f32(-0.15), scriptHunger=-0.15)
    v3, i3, n3 = buffer_prediction(KK0, "declared", live3, declared_str=PP["declared_script"])
    print("declared", {k: (v3[k], i3[k]) for k in ("fibre", "vitC", "iron", "calcium", "vitB12", "calories")}, n3)
    v4, i4, _n = buffer_prediction(KK0, "fluid", {}, fluid_vec=PP["fluids"]["Coffee"], litres=0.25)
    print("coffee", {k: (v4[k], i4[k]) for k in ("water", "caffeine", "potassium", "calories")})
    print("bread table phytate", PP["table"][BREAD]["phytate"], PP["table_json_per_item"][BREAD]["phytate"])
    sys.exit(0)


# ---------------------------------------------------------------- the session
KK = Kernel()
PRED = predict_offline(KK)
prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("x172")
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []
cur_phase = {"name": "pre"}


def wall():
    return round(time.time() - t0, 3)


doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "user": USER, "profile": prof.report(),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
    "mod_dirty": git_dirty("mod/NutritionRevamp")[0],
    "probe_commits": {m: git_say("log", "-1", "--format=%h", "--", f"testing/experiments/{m}")
                      for m in ("TKX_ItemOverride", "TKX_DeclaredFood")},
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "baseline": {"run": BASELINE_RUN, "file": "food-scan.json", "items_count.total": BASELINE_TOTAL,
                 "items_count.foodByModule.Base": BASELINE_BASE_FOOD,
                 "tick_run": X161B_RUN, "tick_path": "body.json phases.J.tick.result.ticksPerSecond",
                 "tick": X161B_TICK},
    "constants": {k: (list(v) if isinstance(v, tuple) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, tuple))
                  and k not in ("REPO", "LUA_DIR", "MOD_ROOT", "MOD_LUA", "SHARED", "SCRIPT_FILE", "TKX_OVERRIDE",
                                "TKX_DECLARED", "DATASET", "NUTRIENTS_JSON")},
    "predictions": PRED,
    "deviations": [
        "The eaten vector is read off the stomach buffer (every key zeroed by setpath before the eat, then "
        "buffer / s against the prediction, s off calories for a food and water for a fluid), not an `ingested` "
        "record key: the record has none and lastIngested lives one slow minute.",
        "Items are spawned by RCON additem (server-instantiated, synced), not server inventory.add (never sent to "
        "the client).",
        "TKX.FibreBar's script has no FoodType line (the amendments say Fruits): the template is whichever its live "
        "getFoodType selects.",
        "The profile's TKX_ItemOverride restates Base.Apple in full and Base.Orange's Calories; under #1183's sorted "
        "replay the TKX body replays after NR_ItemPass_Food.txt and wins the keys it names, so arm C's apple "
        "carries TKX's macros; arm C2 (Bread) is the clean table arm.",
        "items.count predicts total 5092 + the four TKX item blocks, not + 2.",
        "tick.rate: three 20 s windows against x161b's one 10 s window.",
        "IN.typeInfo runs only for a dish or craft input; no arm eats one: its cost is unmeasured.",
        "The mod at HEAD runs underneath every arm; mod/ untouched.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["the stomach buffer zeroed before each eat and drink", "foods spawned "
                                        "and eaten", "a WaterBottle filled twice and drunk"]},
    "steps": [], "notes": [], "spawns": [], "phases": {}, "phase_errors": {}, "phase_walls": {},
    "mod_error_checks": [], "summaries": {},
}


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


def persist():
    try:
        out["timeline"] = list(tl.items)
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def step(name, side, cmd, args="", timeout=30):
    t_before, e_before = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args, "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": int(e_before * 1000),
           "epoch_ms_after": int(time.time() * 1000), "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def gv(side, name, tag):
    a = ack(step(tag, side, "lua.global", name))
    if not a.get("resolved"):
        return None
    if "value" in a:
        v = a.get("value")
        n = to_num(v)
        return n if n is not None and not isinstance(v, str) else v
    return {"type": a.get("type"), "keyCount": a.get("keyCount")}


def counters(tag):
    return {k: to_num(gv(server, f"{INTAKE}.stats.{k}", f"{tag}_{k}")) for k in COUNTERS}


def rec(tag, keys):
    r = step(tag, server, "witness.moddata", f"global:{STORE} " + " ".join(f"{USER}.{k}" for k in keys))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    return {"tag": tag, "wall": r["wall_before"], "wall_after": r["wall_after"], "worldAge": a.get("worldAge"),
            "missing": a.get("missing"), "values": {k: vals.get(f"{USER}.{k}") for k in keys}}


def fields(side, subj, flds, tag):
    r = step(tag, side, "witness.fields", f"item {subj} {flds}")
    a = ack(r)
    return {"tag": tag, "wall": r["wall_before"], "reply": r["ack"], "fields": a.get("fields"),
            "count": a.get("count"), "nils": a.get("nils"), "missing": a.get("missing"), "resolved": a.get("resolved")}


def moddata(side, subj, tag):
    r = step(tag, side, "witness.moddata", f"item:{subj} NR_Nutrients")
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    return {"tag": tag, "reply": r["ack"], "value": vals.get("NR_Nutrients"), "missing": a.get("missing"),
            "keys": a.get("keys")}


def spawn(full_type, why):
    pre = ack(step(f"spawn_{why}_pre", server, "witness.fields", f"item {USER}/{full_type} getID"))
    pre_id = (pre.get("fields") or {}).get("getID")
    ok, reply = server.rcon(f'additem "{USER}" "{full_type}" 1')
    row = {"type": full_type, "why": why, "pre_server_id": pre_id, "rcon_ok": ok, "rcon_reply": str(reply)[:200],
           "wall_rcon": wall(), "attempts": []}
    for attempt in range(SPAWN_TRIES):
        time.sleep(SPAWN_WAIT)
        seen = ack(step(f"spawn_{why}_{attempt}", client, "witness.fields", f"item {USER}/{full_type} getID"))
        row["attempts"].append({"attempt": attempt + 1, "wall": wall(), "resolved": seen.get("resolved"),
                                "id": (seen.get("fields") or {}).get("getID")})
        if seen.get("resolved"):
            break
    srv = ack(step(f"spawn_{why}_sid", server, "witness.fields", f"item {USER}/{full_type} getID"))
    row["server_id"] = (srv.get("fields") or {}).get("getID")
    row["client_id"] = row["attempts"][-1]["id"] if row["attempts"] else None
    row["ids_agree"] = row["client_id"] is not None and row["client_id"] == row["server_id"]
    row["resolved"] = bool(row["attempts"] and row["attempts"][-1]["resolved"])
    out["spawns"].append(row)
    return row


def idstr(i):
    if isinstance(i, float) and i == int(i):
        i = int(i)
    return str(i)


def zero_buffer(tag):
    acks = []
    for k in KEYS:
        a = ack(step(f"{tag}_z_{k}", server, "globalmoddata.setpath", f"{STORE} {USER}.stomach.buffer.{k} 0"))
        acks.append({"key": k, "ok": a.get("ok"), "before": a.get("before"), "after": a.get("after"),
                     "err": a.get("err") or a.get("error")})
    back = rec(f"{tag}_zread", ["stomach.buffer"])
    buf = back["values"].get("stomach.buffer") or {}
    nonzero = {k: buf.get(k) for k in KEYS if to_num(buf.get(k)) not in (0.0,)}
    return {"acks": acks, "readback": back, "nonzero_after": nonzero, "all_zero": not nonzero}


POST_KEYS = ["stomach.buffer", "lastIntake", "kineticsAge", "stomach.bulk", "acute.gutCaf", "acute.caf"]


def wait_landed(tag, before, key="landed", cap=EAT_WAIT_S):
    end = wall() + cap
    i = 0
    while wall() < end:
        v = to_num(gv(server, f"{INTAKE}.stats.{key}", f"{tag}_poll{i}"))
        i += 1
        if v is not None and before is not None and v > before:
            return v, wall(), i
        time.sleep(LAND_POLL)
    return None, wall(), i


def mod_error(after):
    why = []
    errs = [str(e) for e in (server.errors if server is not None else [])]
    hits = [e[:400] for e in errs if MOD_ERR_RX.search(e) or BOOT_ERR_RX.search(e)]
    if hits:
        why.append({"server_error_lines": hits[:10]})
    le = gv(server, f"{INTAKE}.lastError", f"chk_{after}_ile")
    fl = to_num(gv(server, f"{INTAKE}.stats.failures", f"chk_{after}_ifail"))
    ne = to_num(gv(server, "NutritionRevamp.server.nutrients.stats.errors", f"chk_{after}_nerr"))
    nle = gv(server, "NutritionRevamp.server.nutrients.lastError", f"chk_{after}_nle")
    if le is not None or (fl or 0) > 0 or (ne or 0) > 0 or nle is not None:
        why.append({"intake_lastError": le, "intake_failures": fl, "nutrients_errors": ne, "nutrients_lastError": nle})
    if clients and "lua_error" in getattr(clients[0], "seen", ()):
        why.append({"client": "lua_error seen (parked in the debugger)"})
    h = ack(step(f"chk_{after}_h", server, "health.get", USER))
    o = to_num(h.get("overall"))
    if o is not None and o < HEALTH_GUARD:
        why.append({"health_guard": o})
    out["mod_error_checks"].append({"after": after, "wall": wall(), "found": why, "health": o})
    return why


def run_phase(name, fn):
    cur_phase["name"] = name
    out["phase_walls"][name] = {"start": wall()}
    try:
        fn()
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    out["phase_walls"][name]["end"] = wall()
    persist()


# ---------------------------------------------------------------- phases
DATA_PATHS = ("NutritionRevamp.version", "NutritionRevamp.data.nutrients.get", "NutritionRevamp.data.fluids.get",
              "NutritionRevamp.data.infer._default.n", "NutritionRevamp.data.infer.Fruits.n",
              "NutritionRevamp.data.infer._default.density.vitC", "NutritionRevamp.data.UNITS.phytate")


def phase_S0():
    P = out["phases"]["S0"] = {}
    P["data_client"] = {p: gv(client, p, f"S0_c_{i}") for i, p in enumerate(DATA_PATHS)}
    P["data_server"] = {p: gv(server, p, f"S0_s_{i}") for i, p in enumerate(DATA_PATHS)}
    P["options"] = {k: gv(server, f"NutritionRevamp.server.options.{k}", f"S0_opt_{k}")
                    for k in ("mode", "nutritionOn", "legacyMirror")}
    P["intake_wrapped"] = {k: gv(server, f"{INTAKE}.{k}", f"S0_w_{k}")
                           for k in ("wrapped", "wrappedDrink", "wrappedWorld")}
    P["counters"] = counters("S0_cnt")
    P["intake_lastError"] = gv(server, f"{INTAKE}.lastError", "S0_ile")
    P["record"] = rec("S0_rec", ["lastIntake", "stomach.buffer", "stomach.bulk", "kineticsAge", "acute.caf",
                                 "acute.gutCaf"])
    P["time"] = ack(step("S0_time", server, "time.snapshot"))
    P["server_errors_at_s0"] = list(server.errors)
    P["client_seen_at_s0"] = dict(getattr(client, "seen", {}))
    boot_hits = [e[:400] for e in server.errors if BOOT_ERR_RX.search(str(e))]
    missing = [p for p in DATA_PATHS if P["data_client"].get(p) is None or P["data_server"].get(p) is None]
    P["boot_error_lines"] = boot_hits
    P["data_missing"] = missing
    P["load_failed"] = bool(boot_hits or missing or "lua_error" in getattr(client, "seen", {}))


def phase_A():
    P = out["phases"]["A"] = {}
    r = step("A_items", server, "items.count")
    ic = ack(r)
    P["items_count_reply"] = r["ack"]
    fbm = ic.get("foodByModule") if isinstance(ic.get("foodByModule"), dict) else {}
    P["total"], P["food"], P["foodByModule"] = ic.get("total"), ic.get("food"), fbm
    P["base_food"], P["tkx_food"] = fbm.get("Base"), fbm.get("TKX")
    P["boot"] = {"server_launch_to_started_s": getattr(server, "t_started", None),
                 "client_markers_s": dict(getattr(client, "seen", {})),
                 "session_ready_wall": out.get("session_ready_wall"),
                 "server_started_wall": out.get("server_started_wall"),
                 "client_start_wall": out.get("client_start_wall")}
    P["files_on_disk"] = {k: os.path.getsize(p) for k, p in GEN_FILES.items()}
    P["ticks"] = []
    for i in range(TICK_N):
        after = time.time()
        arm = ack(step(f"A_tick{i}_arm", server, "tick.rate", str(TICK_S)))
        res = None
        if arm.get("armed"):
            try:
                res = server.bus.wait_result(arm.get("result") or "tick-rate", timeout=TICK_S + 25, after=after)
            except (RuntimeError, TimeoutError, OSError) as e:
                res = {"error": f"{type(e).__name__}: {e}"}
        P["ticks"].append({"i": i, "arm": arm, "result": res})
        persist()


def eat_arm(label, full, kind):
    P = out["phases"][label] = {"type": full, "kind": kind}
    sp = spawn(full, label)
    P["spawn"] = sp
    iid = sp["server_id"] if sp["server_id"] is not None else sp["client_id"]
    subj = f"{USER}/#{idstr(iid)}" if iid is not None else f"{USER}/{full}"
    P["subject"] = subj
    P["fields_client"] = fields(client, subj, EAT_FIELDS, f"{label}_fc")
    P["fields_server"] = fields(server, subj, EAT_FIELDS, f"{label}_fs")
    P["moddata_client"] = moddata(client, subj, f"{label}_mc")
    P["moddata_server"] = moddata(server, subj, f"{label}_ms")
    P["script_server"] = ack(step(f"{label}_script", server, "item.script", full))
    P["first_of_type_server"] = ack(step(f"{label}_first", server, "witness.fields", f"item {USER}/{full} getID"))
    P["counters_before"] = counters(f"{label}_c0")
    P["rec_before"] = rec(f"{label}_r0", ["lastIntake", "kineticsAge"])
    P["zero"] = zero_buffer(label)
    P["foodtimer"] = ack(step(f"{label}_ft", server, "foodtimer.set", f"{USER} 0"))
    r = step(f"{label}_eat", client, "eat.action", f"{full} 1")
    P["eat_wall"] = r["wall_before"]
    a = ack(r)
    P["eat"] = {k: a.get(k) for k in ("queued", "fraction", "spawned", "itemId", "validStart", "maxTime",
                                      "moodleFoodEaten")}
    if not a:
        P["eat"]["reply"] = r["ack"]
    v, w, n = wait_landed(label, P["counters_before"].get("landed"))
    P["landed"] = {"value": v, "wall": w, "polls": n}
    P["rec_after"] = rec(f"{label}_r1", POST_KEYS)
    time.sleep(SECOND_READ_DELAY)
    P["rec_after2"] = rec(f"{label}_r2", POST_KEYS)
    P["counters_after"] = counters(f"{label}_c1")
    P["intake_lastError"] = gv(server, f"{INTAKE}.lastError", f"{label}_ile")
    P["consumed_server"] = ack(step(f"{label}_gone", server, "witness.fields", f"item {subj} getID"))


def fluid_arm(label, fluid, litres_req):
    P = out["phases"][label] = {"fluid": fluid, "litres_requested": litres_req}
    have = ack(step(f"{label}_have", server, "witness.fields", f"item {USER}/{BOTTLE} getID"))
    if not have.get("resolved"):
        P["spawn"] = spawn(BOTTLE, label)
    P["fill"] = ack(step(f"{label}_fill", server, "fluid.fill", f"{USER} {BOTTLE} {fluid} {litres_req}"))
    chain = f"{USER} getInventory.getFirstTypeRecurse({BOTTLE}).getFluidContainer.getAmount"
    P["litres_before"] = to_num(ack(step(f"{label}_l0", server, "witness.chain", chain)).get("value"))
    P["counters_before"] = counters(f"{label}_c0")
    P["pending_before"] = gv(server, f"{INTAKE}.pendingCaf.{USER}", f"{label}_pc0")
    P["rec_before"] = rec(f"{label}_r0", ["lastIntake", "acute.gutCaf", "acute.caf", "kineticsAge"])
    P["zero"] = zero_buffer(label)
    r = step(f"{label}_drink", client, "drink.action", f"{BOTTLE} 1")
    P["drink_wall"] = r["wall_before"]
    P["drink"] = r["ack"] if isinstance(r["ack"], dict) else {"reply": r["ack"]}
    v, w, n = wait_landed(label, P["counters_before"].get("landed"))
    P["first_landing"] = {"value": v, "wall": w, "polls": n}
    # the sips: until the container stops moving (two equal reads) or the cap
    reads, last, stable = [], None, 0
    end = wall() + DRINK_SETTLE_S
    while wall() < end:
        lv = to_num(ack(step(f"{label}_lp{len(reads)}", server, "witness.chain", chain)).get("value"))
        reads.append({"wall": wall(), "litres": lv})
        if lv is not None and last is not None and abs(lv - last) < 1e-9:
            stable += 1
            if stable >= 2:
                break
        else:
            stable = 0
        last = lv
        time.sleep(1.0)
    P["litre_reads"] = reads
    P["litres_after"] = reads[-1]["litres"] if reads else None
    P["rec_after"] = rec(f"{label}_r1", POST_KEYS)
    P["pending_after"] = gv(server, f"{INTAKE}.pendingCaf.{USER}", f"{label}_pc1")
    time.sleep(SECOND_READ_DELAY)
    P["rec_after2"] = rec(f"{label}_r2", POST_KEYS)
    P["pending_after2"] = gv(server, f"{INTAKE}.pendingCaf.{USER}", f"{label}_pc2")
    P["counters_after"] = counters(f"{label}_c1")
    P["intake_lastError"] = gv(server, f"{INTAKE}.lastError", f"{label}_ile")


def phase_C():
    eat_arm("C", APPLE, "table")


def phase_C2():
    eat_arm("C2", BREAD, "table")


def phase_D():
    eat_arm("D", FIBRE, "inferred")


def phase_E():
    eat_arm("E", DECLARED, "declared")


def phase_F():
    fluid_arm("F_coffee", FLUIDS[0][0], FLUIDS[0][1])
    persist()
    fluid_arm("F_cola", FLUIDS[1][0], FLUIDS[1][1])


def phase_B():
    P = out["phases"]["B"] = {}
    for full in B_FOODS + RIVALS:
        R = P[full] = {}
        sp = spawn(full, "B_" + full.split(".")[1])
        R["spawn"] = sp
        iid = sp["server_id"] if sp["server_id"] is not None else sp["client_id"]
        subj = f"{USER}/#{idstr(iid)}" if iid is not None else f"{USER}/{full}"
        R["subject"] = subj
        R["fields_client"] = fields(client, subj, B_FIELDS, f"B_{full}_fc")
        R["fields_server"] = fields(server, subj, B_FIELDS, f"B_{full}_fs")
        R["moddata_client"] = moddata(client, subj, f"B_{full}_mc")
        R["moddata_server"] = moddata(server, subj, f"B_{full}_ms")
        sl = step(f"B_{full}_local", client, "item.spawn", full)
        m = re.search(r"id=(-?\d+)", str(sl["ack"]))
        R["local_spawn"] = sl["ack"]
        R["local_id"] = m.group(1) if m else None
        if R["local_id"] is not None:
            R["fields_local_client"] = fields(client, f"{USER}/#{R['local_id']}", B_FIELDS, f"B_{full}_flc")
            R["moddata_local_client"] = moddata(client, f"{USER}/#{R['local_id']}", f"B_{full}_mlc")
        R["script_client"] = ack(step(f"B_{full}_sc", client, "item.script", full))
        R["script_server"] = ack(step(f"B_{full}_ss", server, "item.script", full))
        persist()


def phase_I():
    P = out["phases"]["I"] = {}
    for full in I_TYPES + ("Base.Butter",):
        P[full] = {"client": ack(step(f"I_{full}_c", client, "item.script", full)),
                   "server": ack(step(f"I_{full}_s", server, "item.script", full))}


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["counters"] = counters("Z_cnt")
    P["intake_lastError"] = gv(server, f"{INTAKE}.lastError", "Z_ile")
    P["nutrients"] = {k: gv(server, f"NutritionRevamp.server.nutrients.stats.{k}", f"Z_ns_{k}")
                      for k in ("minutes", "errors")}
    P["nutrients_lastError"] = gv(server, "NutritionRevamp.server.nutrients.lastError", "Z_nle")
    P["kinetics"] = {k: gv(server, f"NutritionRevamp.server.kinetics.stats.{k}", f"Z_ks_{k}")
                     for k in ("minutes", "failures")}
    P["record"] = rec("Z_rec", ["lastIntake", "kineticsAge", "stomach.bulk"])
    P["health"] = ack(step("Z_h", server, "health.get", USER))
    P["tk_version_client"] = ack(step("Z_tkv_c", client, "lua.global", "TK.version"))
    P["tk_version_server"] = ack(step("Z_tkv_s", server, "lua.global", "TK.version"))
    P["client_seen"] = dict(getattr(client, "seen", {}))


PHASES = (("S0", phase_S0), ("A", phase_A), ("C", phase_C), ("C2", phase_C2), ("D", phase_D), ("E", phase_E),
          ("F", phase_F), ("B", phase_B), ("I", phase_I), ("Z", phase_Z))


def body():
    for name, fn in PHASES:
        run_phase(name, fn)
        if name == "A" and (out["phases"].get("S0") or {}).get("load_failed"):
            out["abort"] = {"after": "A", "why": "load test failed at first sight (S0.load_failed)"}
            note("the load test failed: the arms after A are skipped (a load error is the primary reading)")
            run_phase("Z", phase_Z)
            break
        if name in ("S0", "Z"):
            continue
        why = mod_error(name)
        if why:
            out["abort"] = {"after": name, "why": why}
            note(f"mod error or health guard after {name}: the arms stop here")
            run_phase("Z", phase_Z)
            break


# ---------------------------------------------------------------- grading (after the session)
def live_inputs(P):
    fs = (P.get("fields_server") or {}).get("fields") or {}
    li = ((P.get("rec_after") or {}).get("values") or {}).get("lastIntake") or {}
    sc = P.get("script_server") or {}
    sh = to_num(sc.get("HungerChange"))
    live = {k: fs.get(k) for k in ("getCalories", "getCarbohydrates", "getLipids", "getProteins", "getBaseHunger",
                                   "getFoodType", "isCooked", "isBurnt", "isRotten", "isFrozen", "getHungChange")}
    for k in ("getCalories", "getCarbohydrates", "getLipids", "getProteins", "getBaseHunger"):
        live[k] = to_num(live[k]) if live[k] is not None else 0.0
    live["scriptHunger"] = (sh / 100.0) if sh is not None else 0.0
    live["share"] = to_num(li.get("share"))
    live["frac"] = to_num(li.get("frac"))
    return live, li


def grade_eat(label, expect_source):
    P = out["phases"].get(label) or {}
    if not P:
        return {"ok": False, "why": "phase absent"}
    live, li = live_inputs(P)
    G = {"type": P.get("type"), "live": live, "lastIntake": li, "expect_source": expect_source,
         "source_ok": li.get("source") == expect_source, "zero_ok": (P.get("zero") or {}).get("all_zero"),
         "landed": P.get("landed"), "eat": P.get("eat")}
    if live["share"] is None or live["frac"] is None:
        G["ok"] = False
        G["why"] = "no share/frac on lastIntake"
        return G
    kind = P.get("kind")
    declared_str = (P.get("moddata_server") or {}).get("value")
    pred, ingested, n = buffer_prediction(KK, kind, live, table_vec=KK.item(P.get("type")) if kind == "table" else None,
                                          declared_str=declared_str)
    G["pred_buffer"], G["pred_ingested"], G["pred_note"] = pred, ingested, n
    buf1 = ((P.get("rec_after") or {}).get("values") or {}).get("stomach.buffer")
    buf2 = ((P.get("rec_after2") or {}).get("values") or {}).get("stomach.buffer")
    G["grade1"] = ratio_grade(pred, buf1, "calories")
    G["grade2"] = ratio_grade(pred, buf2, "calories")
    G["whole_eat"] = {"share": live["share"], "frac": live["frac"], "both_one": live["share"] == 1 and live["frac"] == 1}
    G["ok"] = bool(G["grade1"].get("ok") and G["grade2"].get("ok") and G["source_ok"] and G["zero_ok"])
    return G


def grade_fluid(label, fluid):
    P = out["phases"].get(label) or {}
    if not P:
        return {"ok": False, "why": "phase absent"}
    lb, la = P.get("litres_before"), P.get("litres_after")
    G = {"fluid": fluid, "litres_before": lb, "litres_after": la, "fill": P.get("fill"),
         "zero_ok": (P.get("zero") or {}).get("all_zero")}
    li = ((P.get("rec_after") or {}).get("values") or {}).get("lastIntake") or {}
    G["lastIntake"] = li
    G["source_ok"] = li.get("source") == "fluid"
    if lb is None or la is None:
        G["ok"] = False
        G["why"] = "litres unreadable"
        return G
    drunk = lb - la
    G["litres_drunk"] = drunk
    fv = KK.fluid(fluid)
    pred, ingested, _n = buffer_prediction(KK, "fluid", {}, fluid_vec=fv, litres=drunk)
    G["pred_buffer"], G["pred_ingested"] = pred, ingested
    buf1 = ((P.get("rec_after") or {}).get("values") or {}).get("stomach.buffer")
    buf2 = ((P.get("rec_after2") or {}).get("values") or {}).get("stomach.buffer")
    G["grade1"] = ratio_grade(pred, buf1, "water")
    G["grade2"] = ratio_grade(pred, buf2, "water")
    b0 = (P.get("rec_before") or {}).get("values") or {}
    a1 = (P.get("rec_after") or {}).get("values") or {}
    a2 = (P.get("rec_after2") or {}).get("values") or {}

    def cafsum(v, pend):
        g, c = to_num(v.get("acute.gutCaf")), to_num(v.get("acute.caf"))
        p = to_num(pend) if not isinstance(pend, dict) else None
        if g is None or c is None:
            return None
        return g + c + (p or 0.0)
    s0 = cafsum(b0, P.get("pending_before"))
    s1 = cafsum(a1, P.get("pending_after"))
    s2 = cafsum(a2, P.get("pending_after2"))
    dose = ingested["caffeine"]
    G["caffeine"] = {"dose_pred": dose, "sum_before": s0, "sum_after": s1, "sum_after2": s2,
                     "rise1": (s1 - s0) if s1 is not None and s0 is not None else None,
                     "rise2": (s2 - s0) if s2 is not None and s0 is not None else None}
    r1 = G["caffeine"]["rise1"]
    G["caffeine"]["ratio1"] = (r1 / dose) if r1 is not None and dose else None
    G["caffeine"]["ok"] = (G["caffeine"]["ratio1"] is not None and abs(1 - G["caffeine"]["ratio1"]) <= CAF_TOL)
    G["ok"] = bool(G["grade1"].get("ok") and G["grade2"].get("ok") and G["source_ok"] and G["zero_ok"]
                   and G["caffeine"]["ok"])
    return G


def grade_B():
    P = out["phases"].get("B") or {}
    S = {}
    for full in B_FOODS + RIVALS:
        R = P.get(full) or {}
        pr = PRED["B"][full]["pred"]
        g = {"server": field_grade((R.get("fields_server") or {}).get("fields"), pr),
             "client_replica": field_grade((R.get("fields_client") or {}).get("fields"), pr),
             "client_local": field_grade((R.get("fields_local_client") or {}).get("fields"), pr),
             "nr_server": (R.get("moddata_server") or {}).get("value"),
             "nr_client": (R.get("moddata_client") or {}).get("value"),
             "nr_local_client": (R.get("moddata_local_client") or {}).get("value"),
             "counts": [(R.get(x) or {}).get("count") for x in ("fields_server", "fields_client", "fields_local_client")],
             "winner": PRED["B"][full]["winner"], "confidence": PRED["B"][full]["confidence"],
             "portion_source": PRED["B"][full]["portion_source"]}
        alt = PRED["B"][full]["nr_only_alternative"]
        if full in RIVALS:
            g["nr_only_alternative_server"] = field_grade((R.get("fields_server") or {}).get("fields"), alt)
        g["ok"] = bool(g["server"].get("ok") and g["client_replica"].get("ok") and g["client_local"].get("ok"))
        g["G_no_key"] = g["nr_server"] is None and g["nr_client"] is None and g["nr_local_client"] is None
        S[full] = g
    return S


def grade_I():
    P = out["phases"].get("I") or {}
    S = {}
    for full in I_TYPES:
        dp = PRED["I"][full]["dataset_props"]
        R = P.get(full) or {}
        rows = {}
        for k, raw in dp.items():
            if raw is None:
                continue
            exp = (raw == "true") if raw in ("true", "false") else to_num(raw)
            for side in ("client", "server"):
                got = (R.get(side) or {}).get(k)
                good = (got == exp) if isinstance(exp, bool) else (to_num(got) is not None and exp is not None
                                                                   and abs(to_num(got) - exp) < 1e-6)
                rows[f"{side}.{k}"] = {"exp": exp, "got": got, "ok": good}
        strip = ("side", "via")
        cs = {k: v for k, v in (R.get("client") or {}).items() if k not in strip}
        ss = {k: v for k, v in (R.get("server") or {}).items() if k not in strip}
        S[full] = {"rows": rows, "sides_equal": bool(cs) and cs == ss, "client": cs, "server": ss,
                   "in_script_file": PRED["I"][full]["in_script_file"], "table_entry": PRED["I"][full]["table_entry"]}
        S[full]["ok"] = (all(r["ok"] for r in rows.values()) and S[full]["sides_equal"]
                         and not S[full]["in_script_file"] and not S[full]["table_entry"])
    return S


def grade_all():
    S = out["summaries"]
    A = out["phases"].get("A") or {}
    ticks = [((t.get("result") or {}).get("ticksPerSecond")) for t in A.get("ticks", [])]
    S["A"] = {"base_food": A.get("base_food"), "tkx_food": A.get("tkx_food"), "total": A.get("total"),
              "pred": PRED["items_count"],
              "base_ok": A.get("base_food") == BASELINE_BASE_FOOD,
              "total_ok": A.get("total") == PRED["items_count"]["total"],
              "ticks": ticks, "tick_baseline": X161B_TICK,
              "tick_ratio": [(t / X161B_TICK) if isinstance(t, (int, float)) else None for t in ticks],
              "boot": A.get("boot"), "files": A.get("files_on_disk"),
              "load_failed": (out["phases"].get("S0") or {}).get("load_failed")}
    S["C"] = grade_eat("C", "baseline")
    S["C2"] = grade_eat("C2", "baseline")
    S["D"] = grade_eat("D", "inferred")
    S["E"] = grade_eat("E", "declared")
    E = out["phases"].get("E") or {}
    S["E"]["moddata_before_eat"] = {"server": (E.get("moddata_server") or {}).get("value"),
                                    "client": (E.get("moddata_client") or {}).get("value"),
                                    "script": PRED["declared_script"]}
    D = out["phases"].get("D") or {}
    S["D"]["foodType_live"] = {"server": ((D.get("fields_server") or {}).get("fields") or {}).get("getFoodType"),
                               "server_nils": (D.get("fields_server") or {}).get("nils")}
    S["F_coffee"] = grade_fluid("F_coffee", "Coffee")
    S["F_cola"] = grade_fluid("F_cola", "Cola")
    S["B"] = grade_B()
    S["I"] = grade_I()
    C = out["phases"].get("C") or {}
    S["G"] = {"apple_eaten": {"server": (C.get("moddata_server") or {}).get("value"),
                              "client": (C.get("moddata_client") or {}).get("value")},
              "all_B_missing": all(v.get("G_no_key") for v in S["B"].values()) if S["B"] else None}
    logs = out.get("logs") or {}
    Z = out["phases"].get("Z") or {}
    S["H"] = {"server_checksum_lines": logs.get("server_checksum"), "client_checksum_lines": logs.get("client_checksum"),
              "client_kicked_marker": "kicked" in (Z.get("client_seen") or {}),
              "client_tk_version_last": (Z.get("tk_version_client") or {}).get("value"),
              "ok": not logs.get("server_checksum") and not logs.get("client_checksum")
              and (Z.get("tk_version_client") or {}).get("value") == 1}


if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    persist()
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)

try:
    server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini)
    out["server_launch_wall"] = wall()
    server.start(timeout=prof.server_timeout)
    out["server_started_wall"] = wall()
    tl.mark("server_started")
    client, _ = make_client(run_dir, USER, server, rec_fx)
    out["client_start_wall"] = wall()
    client.start()
    clients.append(client)
    client.wait_ready(timeout=prof.client_timeout)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)), "client": sorted(set(client.mods_not_found))}
    persist()
    try:
        body()
    except Exception as e:                     # noqa: BLE001 - keep the rows already collected
        out["body_error"], out["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    persist()
except Exception as e:                         # noqa: BLE001
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    try:
        if server is not None:
            teardown(tl, server, clients)
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, clients)
        out["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
        out["client_seen"] = dict(getattr(clients[0], "seen", {})) if clients else None
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
            out["server_t_started"] = getattr(server, "t_started", None)
            out["logs"] = {"server": grep_file(server.log_path, LOG_RX, LOG_LIMIT),
                           "server_checksum": grep_file(server.log_path, CHECKSUM_RX, CHECKSUM_LIMIT),
                           "server_load": grep_file(server.log_path, LOAD_RX, LOAD_LIMIT),
                           "limits": {"log": LOG_LIMIT, "checksum": CHECKSUM_LIMIT, "load": LOAD_LIMIT},
                           "patterns": {"log": LOG_RX.pattern, "checksum": CHECKSUM_RX.pattern,
                                        "load": LOAD_RX.pattern}}
            if clients:
                out["logs"]["client"] = grep_file(clients[0].console, LOG_RX, LOG_LIMIT)
                out["logs"]["client_checksum"] = grep_file(clients[0].console, CHECKSUM_RX, CHECKSUM_LIMIT)
                out["logs"]["client_load"] = grep_file(clients[0].console, LOAD_RX, LOAD_LIMIT)
        try:
            grade_all()
        except Exception as e:                 # noqa: BLE001
            out["summary_error"] = f"{type(e).__name__}: {e}"
            out["summary_traceback"] = traceback.format_exc()[-3000:]
        out["wall_seconds"] = round(time.time() - t0, 1)
        persist()
        dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

S = out.get("summaries") or {}
print(json.dumps({"A": S.get("A"), "ok": {k: (v.get("ok") if isinstance(v, dict) else None) for k, v in S.items()},
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error")}, indent=1, default=str)[:9000])
