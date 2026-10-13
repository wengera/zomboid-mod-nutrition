"""x36_gut_lib -- the session engine of the Plan 11g Task 8 drivers (x361..x364): the live checks of the final satiety
and deficit model on the staged copy of the tree at the final build (Plan 11g Tasks 6c and 7 with their fixes): the meal
pool M (record.satiety.M) fed at the eat and cleared per substep in Kinetics; F counted to the hard capacity (1100/730);
the physical fill (record.stomachFill) on both lanes at density 1 and the food fill (the solid lane alone, ruling T6c-1),
which the two "fed" gates read; the deficit drive (NR_Kernel_Deficit.lua: BALANCE_SPAN 3970.55, no floor, EX_BYPASS
0.282/0.405); the energy class held within ENERGY_BAND 0.01 on the server and carried by every mirror as
body_energyLevel (ruling T7-7). One driver a session, each on a fresh fixture restore (no chain).

It is x35_exercise_lib.py (Plan 11f Task 6r, frozen with x351's run) copied, not imported, with x34_monotony_lib.py's
patterns, and these changes:
  1. THE RING (30 paths): satiety.M (never P or G: the frozen libs x26-x35 ring those, the Task 4 and 6c review notes),
     satiety.S, satiety.L, satiety.t, body.energyState, body.met, stomachFill (the physical fill), stomach.liquid, the
     solid lane's buffer kcal (stomach.buffer.calories) and its five gram keys (water, proteins, carbs, lipids, fibre:
     the food fill is K.satiety.fill of their sum over K.stomach.CAPACITY_MAX_G, computed off the ring by food_fill
     with the mod's own kernel, since the record stamps only the physical fill), kineticsAge, body.inDay, body.eeDay,
     body.fm, body.lm, fluids.water, fluids.na, fluids.naPlasma, fluids.autoDrop, fluids.thirstTarget; and six globals:
     the writer's writes and sips, the intake's eats, landed and sips, and the server bus's last push signature for the
     admin (NutritionRevamp.server.bus.lastSig.admin: its thousands digit is the energy level the server holds,
     K.view.signatureEnergy; the server's held level every minute);
  2. NO BOUT, NO WALK, NO CHAIN: x35's exercise verbs, chain calendar and chain_pre are gone; each session restores the
     fixture fresh. The scenario verbs are to_request, to_stop, course (a meal's time course at speed 1 to its next
     request, at least min_h and at most max_h game hours after the landing), meal (maint, request or surplus sized,
     eaten at the slow clock so a meal's portions land within a few game minutes), drink (x35's), refill (x35's, the
     canteen only in a session that carries one: Session(canteen=True)), and energy_pair;
  3. THE ENERGY PAIR (Session.energy_pair, the amendments' same-second pairs): the client's mirror body_energyLevel and
     body_energyState, its moodle level (NutritionRevamp.client.moodles.levels.energy) and view class
     (NutritionRevamp.client.view.classes.energy) and its received count, read in one tick; at once the server's last
     push signature and push count in one tick; then the record's energy state. The pair's wall gap is kept;
     energy_pairs_grade compares the client's level with the server's held level, allowing the push gap
     (NR_Server_Bus.lua PUSH_GAP_MS, 60 s of wall clock) after a server level change, named as lag;
  4. THE READINGS (pure, shared with x36_grade.py): diff_floor (the tool's diff with a floor on a relative tolerance,
     and the derived foodFill), course_reading (a meal's time course live against the replay: every graded row's
     HUNGER, es, L, M, the two fills and the buffer kcal, the request minute, the nadir, a 15-minute series), day_reading
     (a day's time-weighted mean HUNGER and its values at named ages), drink_reading (the fills at a drink's sip rows)
     and rest_arm_events (the surplus day's REST arm: the surplus meals' landings given maintenance portions);
  5. THE AUTO-DRINK SIPS AS THE TOOL'S `autodrop` KIND (x34's and x35's form), in the canteen session; the canteen is
     refilled after every meal and at named refill stops.
Kept from x35: the phases (boot, S, H, W, X, R, D, Z), the slot files, the replay of live (tools/replay_live.py at HEAD,
the ring's own raw rate and exercise flag, the movement flag off the ring) and the artifact copy, the sodium guard's
per-day reading (fluid_days), the request reading, the plumbing.

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run (x361), this file is never edited (CLAUDE.md
s5). A later change is a new file and the drivers that use it name it.

The read-back is the replay's input and the tool is never tuned to a run (Plan 11f Global Constraints).
"""
import glob
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # testing/
sys.path.insert(0, HERE)                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.bus import resolve_side                                # noqa: E402
from pzt.harness import lint_paths                              # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, attach_clients, make_server,  # noqa: E402
                         teardown, verify)

REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL                                         # noqa: E402
USER = "admin"
SRV = "server"
CLI = "client"
NR = "NutritionRevamp"
MOD_DIR = "mod/NutritionRevamp"
MANIFEST_NAME = "MANIFEST.json"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_SERVER = LUA_DIR + "/server/PZTestKit_Server.lua"
HARNESS_CORE = LUA_DIR + "/shared/PZTestKit_Core.lua"
STUDY_FOODS = "testing/experiments/TKX_StudyFoods/common/media/scripts/tkx_study_foods.txt"
GAME_JAR = r"D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar"
APP_MANIFEST = r"D:\SteamLibrary\steamapps\appmanifest_108600.acf"
MEM_MIN_GB = 12.0
SPEED_FAST = 5
SLOW_MULT = 0.1674
H_REQ = 0.25
APPROACH = 0.246          # at speed 5 a poll spans about 3 game minutes, HUNGER about 0.0003 a minute near 0.25
SAVE_CAP_S = 80.0
SPAWN_CAP_S = 15.0
EAT_CAP_S = 60.0
DRINK_CAP_S = 60.0
FLUSH_CAP_S = 90.0
RESULT_WAIT_S = 30.0
POLL_S = 0.25
LOG_LIMIT = 400
BUF_KEYS = ("water", "proteins", "carbs", "lipids", "fibre")   # K.stomach.massOf's gram keys
BUF_KCAL = "stomach.buffer.calories"
FILL = "stomachFill"
LIQ = "stomach.liquid"
MPOOL = "satiety.M"
FOOD_FILL = "foodFill"     # derived off the ring (food_fill), never a record path
RING_RECORD = ("satiety.M", "satiety.S", "satiety.L", "satiety.t", "body.energyState", "body.met", FILL, LIQ,
               BUF_KCAL) + tuple("stomach.buffer." + k for k in BUF_KEYS) + (
               "kineticsAge", "body.inDay", "body.eeDay", "body.fm", "body.lm", "fluids.water", "fluids.na",
               "fluids.naPlasma", "fluids.autoDrop", "fluids.thirstTarget")
LASTSIG = "_G.NutritionRevamp.server.bus.lastSig.admin"
RING_GLOBALS = ("_G.NutritionRevamp.server.writer.stats.writes", "_G.NutritionRevamp.server.writer.stats.sips",
                "_G.NutritionRevamp.server.intake.stats.eats", "_G.NutritionRevamp.server.intake.stats.landed",
                "_G.NutritionRevamp.server.intake.stats.sips", LASTSIG)
EATS = "_G.NutritionRevamp.server.intake.stats.eats"
LANDED = "_G.NutritionRevamp.server.intake.stats.landed"
SIPS = "_G.NutritionRevamp.server.intake.stats.sips"
OPTIONAL_BEFORE_EAT = ()
WSIPS = "_G.NutritionRevamp.server.writer.stats.sips"
H1_EXTRA = ("firstSeen", "resets", "body.sex", "body.fm", "body.lm")
INTAKE_PATHS = ("NutritionRevamp.server.intake.stats.eats", "NutritionRevamp.server.intake.stats.landed",
                "NutritionRevamp.server.intake.stats.sips", "NutritionRevamp.server.intake.stats.failures")
FLUSH_PATHS = ("NutritionRevamp.server.players.online.admin", "NutritionRevamp.server.store.file.lastWrite.admin",
               "NutritionRevamp.server.store.file.stats.writes")
CLI_ENERGY = ("NutritionRevamp.client.mirror.body_energyLevel", "NutritionRevamp.client.mirror.body_energyState",
              "NutritionRevamp.client.moodles.levels.energy", "NutritionRevamp.client.view.classes.energy",
              "NutritionRevamp.client.received")
SRV_ENERGY = ("NutritionRevamp.server.bus.lastSig.admin", "NutritionRevamp.server.bus.effects.stats.pushes")
STAT_NAMES = {"HUNGER": "Hunger", "THIRST": "Thirst", "FATIGUE": "Fatigue", "BOREDOM": "Boredom",
              "UNHAPPINESS": "Unhappiness", "NICOTINE_WITHDRAWAL": "NicotineWithdrawal"}
# the session's extra diff (a reading beside the tool's DEFAULT_TOL; diff_floor carries the graded form)
TOL_EXTRA = {MPOOL: ("abs", 1.0), "satiety.S": ("abs", 1e-6), FILL: ("abs", 0.002), LIQ: ("abs", 2.0),
             BUF_KCAL: ("abs", 1.0)}
# the graded tolerances (the 11f ones for HUNGER, es and L, the plan's pre-registered DEFAULT_TOL; the rest named here,
# before the run): M within 0.5 % (floor 1 weighted kcal, where M falls toward 0), the two fills within 0.002 (the
# x35 lib's stomachFill bound), the buffer within 0.5 % (floor 0.5 kcal)
TOL_GRADE = {"HUNGER": ("abs", 0.002), "body.energyState": ("abs", 0.005), "satiety.L": ("rel", 0.005, 1e-9),
             MPOOL: ("rel", 0.005, 1.0), FILL: ("abs", 0.002), FOOD_FILL: ("abs", 0.002),
             BUF_KCAL: ("rel", 0.005, 0.5)}
SLEEP_ALLOWED = False      # the live server: SleepAllowed and SleepNeeded false (the fixture default; ruling T4-1)
HOUR_OFFSET = 7.0          # world age 0 is 07:00 on the default fixture (#2890): the hour of a world age a is (a + 7) % 24
KCAL_PER_H = RL.KCAL_PER_H  # 650 / 0.25: the intake mapping (ruling 11c-31), the tool's own constant
MIX650, MIX217, UNIT50 = "TKX.Mixed650", "TKX.Mixed217", "TKX.Unit50"
MIX400, MILKSOLID = "TKX.Mixed400", "TKX.MilkSolid"
PORTION_KCAL = {MIX650: 650.0, MIX217: 650.0 / 3, UNIT50: 50.0}   # one per-kcal composition (tkx_study_foods.txt)
MIX333, MIX667 = "TKX.Mixed333", "TKX.Mixed667"
OTHER_KCAL = {MIX333: 2000.0 / 6, MIX667: 2000.0 / 3, MIX400: 400.0, MILKSOLID: 314.15}
LATE_MAX_H = 1.0           # a meal stop already past by less than this at the session's start is done at once (late)
STOP_LEAD_H = 5 / 60.0     # speed 5 until this long before a stop, then speed 1 until its age
CANTEEN = "Base.CanteenMilitaryFull"   # x151t's D: a server-only canteen made and filled by the server fluid.fill
CANTEEN_L = 0.9            # the litres each refill puts in it (x151t's fill)
LITRES_PER_THIRST = 2.0    # NR_Server_Nutrients.lua NUT.LITRES_PER_THIRST: an autoDrop of x lands 2 x litres
AUTODROP = "fluids.autoDrop"
MET = "body.met"
RING_MOVING_LABEL = "ring-moving"
PUSH_GAP_S = 60.0          # NR_Server_Bus.lua PUSH_GAP_MS: at most one effects push per player per 60 s of wall clock
LAG_SLACK_S = 5.0          # the push rides the next slow minute after the gap, and the read's own wall resolution
PAIR_GAP_MAX_S = 1.0       # a pair's client and server reads within one wall second (the same-second rule)
KARL_RATIO = 22.7 / 10.6   # S1325 (Karl 2021) Table 1: BAL's intake over REST's, MJ/d (the surplus day's meal factor)
KARL_BAL = -55.0           # S1325: BAL against REST, %
KARL_BAND = (-64.0, -46.0)  # S1892: the band the gut oracle grades BAL in


def at(d, h):
    """The world age of clock hour h on day d (day 0 the fixture's first day: midnight before day d is 24 d - 7)."""
    return 24.0 * d - 7.0 + h


PORTION_TOL = 25.0         # a meal's portions sum within this of its target plus carry (half a Unit50)


def portions(kcal):
    """Whole portions for kcal: (n650, n217, n50), the fewest eats whose sum lies within PORTION_TOL of kcal (then the
    smaller miss); the carry takes the miss to the next meal. Returns ((n650, n217, n50), their kcal)."""
    best = None
    for a in range(0, 5):
        for b in range(0, 3):
            for c in range(0, 13):
                tot = a * 650.0 + b * 650.0 / 3 + c * 50.0
                miss = abs(kcal - tot)
                key = (0 if miss <= PORTION_TOL + 1e-9 else 1, a + b + c if miss <= PORTION_TOL + 1e-9 else 0,
                       round(miss, 6))
                if best is None or key < best[0]:
                    best = (key, (a, b, c), tot)
    return best[1], best[2]


def day_of(age):
    """The day of a world age (day 0 from midnight before the fixture's first 07:00, at age -7)."""
    return int(math.floor((age + 7.0) / 24.0 + 1e-12))


def eat_kcal(full):
    if full in PORTION_KCAL:
        return PORTION_KCAL[full]
    return OTHER_KCAL.get(full, 0.0)


def autodrop_events(rows):
    """The replay's auto-drink events from the ring (x35 change 3): each ring row reading fluids.autoDrop > 0 is the
    sip the writer folded in the drain before it, which the mod's own Nutrients step lands in the next drain after
    Kinetics; one tool `autodrop` event {s, g} at that row, g the water grams LITRES_PER_THIRST x autoDrop x 1000
    (ruling T9-4, replay_live 08eb7e60)."""
    out = []
    for r in rows:
        v = num(r.get(AUTODROP))
        if v is not None and v > 0 and r.get("s") is not None:
            out.append({"s": r["s"], "kind": "autodrop", "g": LITRES_PER_THIRST * v * 1000.0,
                        "label": "autodrop", "autoDrop": v, "age": r.get("age")})
    return out


def ring_moving_events(rows):
    """The replay's movement events off the ring (x35 change 2): one activity event {s, moving} before the drain of each
    online row whose `moving` flag differs from the last one seen, from the stand-in's still start. Never names rate,
    raw or exercising (the tool takes those off the ring itself)."""
    out = []
    cur = False
    for r in rows:
        if r.get("s") is None or r.get("on") is False:
            continue
        mv = r.get("moving")
        if not isinstance(mv, bool) or mv == cur:
            continue
        out.append({"s": r["s"], "kind": "activity", "moving": mv, "label": RING_MOVING_LABEL, "age": r.get("age")})
        cur = mv
    return out


def _kh_static():
    if "_KH" not in globals() or globals()["_KH"] is None:
        globals()["_KH"] = RL.ServerReplay(start=None, user=USER, sleep_allowed=SLEEP_ALLOWED)
    return globals()["_KH"]


def food_fill(row):
    """The food fill of a ring or replay row (change 1): K.satiety.fill of the solid lane's gram keys' sum over
    K.stomach.CAPACITY_MAX_G, on the mod's own kernel (K.stomach.foodFill's arithmetic); None when a key is absent."""
    vals = [num(row.get("stomach.buffer." + k)) for k in BUF_KEYS]
    if any(v is None for v in vals):
        return None
    K = _kh_static().K
    return float(K.satiety.fill(sum(vals), K.stomach.CAPACITY_MAX_G))


def energy_digit(sig):
    """The energy level a push signature holds (K.view.signatureEnergy): floor(sig / 1000) % 10; None for a non-number."""
    v = num(sig)
    if v is None:
        return None
    return int(math.floor(v / 1000.0)) % 10


def hypo_grade(na_plasma):
    """The mod's own K.fluids.hyponatGrade on the lupa host (0 at or above its first threshold)."""
    if num(na_plasma) is None:
        return None
    return int(_kh_static().K.fluids.hyponatGrade(float(na_plasma)))


def fluid_days(ring, events):
    """Per day, off the ring: the drinking (the autoDrop events' water; the writer's sip folds), and the sodium guard
    (fluids.na, fluids.water and naPlasma at the day's last row, naPlasma's min and max, the hyponatraemia grade's max
    by the mod's own kernel)."""
    out = {}
    on = [r for r in ring if num(r.get("age")) is not None]
    for e in events:
        if e.get("label") != "autodrop":
            continue
        d = out.setdefault(str(day_of(e["age"])), {})
        d["drunk_g_mod"] = d.get("drunk_g_mod", 0.0) + e["g"]
        d["autodrops"] = d.get("autodrops", 0) + 1
    prev = None
    for r in on:
        d = out.setdefault(str(day_of(r["age"])), {})
        d["rows"] = d.get("rows", 0) + 1
        d.setdefault("first_age", r["age"])
        d["last_age"] = r["age"]
        for k in ("fluids.na", "fluids.water", "fluids.naPlasma", "body.energyState"):
            if num(r.get(k)) is not None:
                d[k + "_end"] = r[k]
        p = num(r.get("fluids.naPlasma"))
        if p is not None:
            d["naPlasma_min"] = min(d.get("naPlasma_min", p), p)
            d["naPlasma_max"] = max(d.get("naPlasma_max", p), p)
        if prev is not None:
            a, b = num(prev.get(WSIPS)), num(r.get(WSIPS))
            if a is not None and b is not None and b > a:
                d["writer_sips"] = d.get("writer_sips", 0) + int(round(b - a))
        prev = r
    for d in out.values():
        lo = d.get("naPlasma_min")
        d["grade_max"] = hypo_grade(lo) if lo is not None else None
    return out


def row_at(rows, age):
    """The last row at or before age (None if none, or if the rows end before it)."""
    best = None
    for r in rows:
        a = num(r.get("age"))
        if a is None:
            continue
        if a <= age + 1e-9:
            best = r
        else:
            return best
    return None


def resolve_run(arg):
    """A run id (testing/runs/<id>) or a run folder."""
    if os.path.isdir(arg):
        return os.path.abspath(arg)
    p = os.path.join(REPO, "testing", "runs", arg)
    if os.path.isdir(p):
        return p
    raise SystemExit(f"no run folder {arg}")


ECHO_RX = re.compile(r"PZTK: ")
MOD_LIFE_RX = re.compile(r"minute: \w+ failed|players: hook failed|players: task|store: |writer: ")
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")


class Budget(Exception):
    """The wall budget passed: the scenario stops and the session goes on to its read-back and flush."""


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def free_gb():
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB"],
                           capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip().splitlines()[-1])
    except Exception as e:                     # noqa: BLE001
        return f"{type(e).__name__}: {e}"


def stray_clients():
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ProjectZomboid64.exe", "/FO", "CSV", "/NH"],
                           capture_output=True, text=True, timeout=60)
        return [ln for ln in r.stdout.splitlines() if "ProjectZomboid64" in ln]
    except Exception as e:                     # noqa: BLE001
        return [f"{type(e).__name__}: {e}"]


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def grep_noecho(log, rx, limit):
    hits, skipped = [], 0
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not rx.search(line):
                    continue
                if ECHO_RX.search(line):
                    skipped += 1
                    continue
                hits.append(line.strip()[:600])
                if len(hits) >= limit:
                    break
    except OSError:
        pass
    return hits, skipped


# ---------------------------------------------------------------- the read-back (pure)
def load_pages(run_dir, files):
    rows = {}
    for f in files:
        try:
            with open(os.path.join(run_dir, f), encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        for r in doc.get("rows_list") or []:
            rows[r["s"]] = r
    return [rows[s] for s in sorted(rows)]


def build_events(rows, eats, drinks):
    """The replay's event list from the ring and the driver's logs (x35's). eats: [{food, landed}] in queue order; an
    eat is keyed to the first ring row whose intake.stats.eats rose (one event per unit of the rise, in queue order).
    drinks: [{fluid, drunk, age0, age1}]; a ring row whose intake.stats.sips rose and whose age lies in
    [age0, age1 + 0.1] belongs to that drink, and its litres are split over those rows in proportion to the rise.
    Returns (events, notes)."""
    events, notes = [], []
    queue = [e for e in eats if e.get("landed")]
    qi = 0
    prev = None
    sip_rows = []
    for r in rows:
        if prev is not None:
            a, b = num(prev.get(EATS)), num(r.get(EATS))
            if a is not None and b is not None and b > a:
                for _ in range(int(round(b - a))):
                    if qi < len(queue):
                        events.append({"s": r["s"], "kind": "eat", "food": queue[qi]["food"],
                                       "label": queue[qi].get("label")})
                        queue[qi]["ring_s"] = r["s"]
                        queue[qi]["ring_age"] = r.get("age")
                        qi += 1
                    else:
                        notes.append(f"eats rose at s {r['s']} with no queued eat left")
            a, b = num(prev.get(SIPS)), num(r.get(SIPS))
            if a is not None and b is not None and b > a:
                sip_rows.append((r, b - a))
        prev = r
    if qi < len(queue):
        notes.append(f"{len(queue) - qi} landed eat(s) never seen in the ring")
    for d in drinks:
        if num(d.get("drunk")) is None or d["drunk"] <= 0:
            notes.append(f"drink {d.get('label')}: no litres drunk read; no event")
            continue
        mine = [(r, n) for r, n in sip_rows if num(r.get("age")) is not None
                and d["age0"] - 1e-9 <= r["age"] <= d["age1"] + 0.1]
        tot = sum(n for _, n in mine)
        if tot <= 0:
            notes.append(f"drink {d.get('label')}: no sip rows in the ring")
            continue
        d["ring_s"] = [r["s"] for r, _ in mine]
        for r, n in mine:
            events.append({"s": r["s"], "kind": "drink", "fluid": d["fluid"], "litres": d["drunk"] * n / tot,
                           "label": d.get("label")})
    events.sort(key=lambda e: e["s"])
    return events, notes


def request_after(rows, after_age, level=H_REQ, fasted=True):
    """Minutes from after_age to the first row past it whose HUNGER is back at `level`, after it first fell below
    (fasted=True); None if never."""
    seen_below = not fasted
    for r in rows:
        if num(r.get("age")) is None or r["age"] <= after_age + 1e-12 or num(r.get("HUNGER")) is None:
            continue
        x = r["HUNGER"]
        if not seen_below:
            if x < level - 1e-12:
                seen_below = True
            continue
        if x >= level - 1e-12:
            return (r["age"] - after_age) * 60
    return None


def at_minute(rows, after_age, minute, field="HUNGER"):
    """The field linearly interpolated at after_age + minute (game minutes) between the rows either side; with the
    nearest rows' ages. `field` may be FOOD_FILL (derived per row)."""
    t = after_age + minute / 60.0
    lo = hi = None
    lv = hv = None
    for r in rows:
        v = food_fill(r) if field == FOOD_FILL else num(r.get(field))
        if num(r.get("age")) is None or v is None:
            continue
        if r["age"] <= t:
            lo, lv = r, v
        elif hi is None:
            hi, hv = r, v
            break
    if lo is None or hi is None:
        return None
    if hi["age"] == lo["age"]:
        return {"value": lv, "lo_age": lo["age"], "hi_age": hi["age"]}
    w = (t - lo["age"]) / (hi["age"] - lo["age"])
    return {"value": lv + w * (hv - lv), "lo_age": lo["age"], "hi_age": hi["age"], "lo_s": lo.get("s"),
            "hi_s": hi.get("s")}


def mean_over(rows, after_age, minutes, field="HUNGER"):
    """The time-weighted mean of the field over (after_age, after_age + minutes], a step per row (each row's value
    held over its dtM before it)."""
    t1 = after_age + minutes / 60.0
    acc = span = 0.0
    prev_age = after_age
    for r in rows:
        if num(r.get("age")) is None or r["age"] <= after_age + 1e-12 or num(r.get(field)) is None:
            continue
        a = min(r["age"], t1)
        acc += r[field] * (a - prev_age)
        span += a - prev_age
        prev_age = a
        if r["age"] >= t1:
            break
    return (acc / span) if span > 0 else None


def _field(r, f):
    return food_fill(r) if f == FOOD_FILL else num(r.get(f))


def diff_floor(rep_rows, ring_rows, tol=None, window=None):
    """The replay rows against the ring rows matched on s (the tool's diff's classes: a between, suspect or offline
    replay row is not graded; a gap row is graded and marked), under tol {field: ("abs", b) | ("rel", b, floor)}: a
    relative error is |a - b| / max(|a|, floor). FOOD_FILL is derived per row (food_fill). window (a0, a1): only rows
    whose age lies in it. A field compared on no row is a finding. Returns {fields: {f: {n, max, over, worst_s}},
    findings (the first 40), findings_n, classes, ok}."""
    tol = TOL_GRADE if tol is None else tol
    by_s = {r["s"]: r for r in ring_rows if r.get("s") is not None}
    fields = {f: {"n": 0, "max": 0.0, "over": 0, "worst_s": None} for f in tol}
    findings = []
    cls = {"between": 0, "suspect": 0, "offline": 0, "gap": 0}
    for r in rep_rows:
        live = by_s.get(r.get("s"))
        if live is None:
            continue
        a0 = num(r.get("age"))
        if window is not None and (a0 is None or not (window[0] - 1e-9 <= a0 <= window[1] + 1e-9)):
            continue
        if r.get("offline"):
            cls["offline"] += 1
            continue
        if r.get("suspect"):
            cls["suspect"] += 1
            continue
        if r.get("between"):
            cls["between"] += 1
            continue
        if r.get("gap"):
            cls["gap"] += 1
        for f, spec in tol.items():
            a, b = _field(r, f), _field(live, f)
            if a is None or b is None:
                continue
            how, bound = spec[0], spec[1]
            if how == "abs":
                d = abs(a - b)
            else:
                fl = spec[2] if len(spec) > 2 else 0.0
                den = max(abs(a), fl)
                d = abs(a - b) / den if den > 0 else (0.0 if a == b else math.inf)
            st = fields[f]
            st["n"] += 1
            if d > st["max"]:
                st["max"], st["worst_s"] = d, r["s"]
            if d > bound:
                st["over"] += 1
                fd = {"s": r["s"], "field": f, "replay": a, "live": b, "d": d, "tol": list(spec)}
                if r.get("gap"):
                    fd["gap"] = True
                findings.append(fd)
    for f, st in fields.items():
        if st["n"] == 0:
            findings.append({"field": f, "n": 0, "why": "compared on 0 rows"})
    return {"fields": fields, "findings": findings[:40], "findings_n": len(findings), "classes": cls,
            "ok": not findings}


SERIES_FIELDS = ("HUNGER", MPOOL, FILL, FOOD_FILL, BUF_KCAL, LIQ, "body.energyState")


def course_reading(ring, rep_rows, a0, a1, tol=None, every_m=15.0):
    """A meal's time course (change 4): the rows aged in (a0, a1] (a0 the landing row's age), live against the replay:
    diff_floor under tol (TOL_GRADE); the live and replay request minutes after a0 and their difference against the
    request tolerance max(3 min, 2 %) (x26's); the HUNGER nadir (value and minute) live and replay; and a series every
    every_m game minutes of SERIES_FIELDS, live and replay (interpolated). Returns a dict."""
    d = diff_floor(rep_rows, ring, tol, window=(a0 + 1e-6, a1))
    lv, rp = request_after(ring, a0), request_after(rep_rows, a0)
    rtol = max(3.0, 0.02 * rp) if rp is not None else None

    def nadir(rows):
        best = None
        for r in rows:
            a, h = num(r.get("age")), num(r.get("HUNGER"))
            if a is None or h is None or a <= a0 + 1e-9 or a > a1 + 1e-9:
                continue
            if best is None or h < best[0]:
                best = (h, (a - a0) * 60)
        return {"HUNGER": best[0], "minute": best[1]} if best else None
    series = []
    m = 0.0
    while a0 + m / 60.0 <= a1 + 1e-9:
        row = {"minute": m}
        for f in SERIES_FIELDS:
            x, y = at_minute(ring, a0, m, f), at_minute(rep_rows, a0, m, f)
            row[f] = x["value"] if x else None
            row[f + "_replay"] = y["value"] if y else None
        series.append(row)
        m += every_m
    return {"a0": a0, "a1": a1, "minutes": (a1 - a0) * 60, "diff": d,
            "request": {"live_min": lv, "replay_min": rp, "tol_min": rtol,
                        "diff_min": (lv - rp) if (lv is not None and rp is not None) else None,
                        "ok": (abs(lv - rp) <= rtol) if (lv is not None and rp is not None) else None},
            "nadir": {"live": nadir(ring), "replay": nadir(rep_rows)}, "series": series,
            "ok": bool(d["ok"]) and (lv is None or rp is None or abs(lv - rp) <= rtol) and (lv is None) == (rp is None)}


def day_reading(rows, a0, a1, ages=()):
    """A day's HUNGER (change 4): the time-weighted mean over (a0, a1] (mean_over), and the values at the named ages
    (interpolated) with their mean."""
    pts = []
    for a in ages:
        x = at_minute(rows, a, 0.0)
        pts.append(x["value"] if x else None)
    good = [p for p in pts if p is not None]
    return {"a0": a0, "a1": a1, "mean": mean_over(rows, a0, (a1 - a0) * 60.0), "ages": list(ages), "points": pts,
            "points_mean": (sum(good) / len(good)) if good and len(good) == len(pts) else None}


def drink_reading(ring, rep_rows, sip_s, a1):
    """A drink's fills (change 4): at each sip row and through to a1, the ring's physical fill, food fill and liquid
    lane, with the replay's; the peak physical fill after the first sip (live and replay); the food fill's largest rise
    at a sip row over the row before it (a drink adds no food fill: none of its keys but water is in K.stomach.massOf's
    solid sum unless it carries macros)."""
    by = {r["s"]: r for r in ring if r.get("s") is not None}
    rep = {r["s"]: r for r in rep_rows if r.get("s") is not None}
    if not sip_s:
        return {"sip_s": [], "ok": None}
    s0 = min(sip_s)
    a_first = num((by.get(s0) or {}).get("age"))
    rows = [r for r in ring if r.get("s") is not None and r["s"] >= s0 - 1
            and num(r.get("age")) is not None and r["age"] <= a1 + 1e-9]
    peak = peak_r = None
    food_rise = None
    tab = []
    for r in rows:
        f, ff, q = num(r.get(FILL)), food_fill(r), rep.get(r["s"]) or {}
        tab.append({"s": r["s"], "age": r["age"], "fill": f, "foodFill": ff, "liquid": num(r.get(LIQ)),
                    "fill_replay": num(q.get(FILL)), "foodFill_replay": food_fill(q) if q else None,
                    "liquid_replay": num(q.get(LIQ)), "sip": r["s"] in sip_s})
        if r["s"] >= s0 and f is not None and (peak is None or f > peak):
            peak = f
        fr = num(q.get(FILL))
        if r["s"] >= s0 and fr is not None and (peak_r is None or fr > peak_r):
            peak_r = fr
    for s in sip_s:
        a, b = by.get(s - 1), by.get(s)
        if a is None or b is None:
            continue
        x, y = food_fill(a), food_fill(b)
        if x is not None and y is not None:
            food_rise = (y - x) if food_rise is None else max(food_rise, y - x)
    return {"sip_s": list(sip_s), "first_age": a_first, "peak_fill": peak, "peak_fill_replay": peak_r,
            "food_fill_rise_max": food_rise, "rows": tab[:120]}


def rest_arm_events(events, eats, labels, kcal):
    """The REST arm of the surplus day (ruling 11f-3: a replay arm on the live clock and record): every eat event of a
    meal whose label prefix is in `labels` is removed, and at that meal's first landing row the maintenance portions of
    `kcal` (portions(kcal), one eat event each, in the meal's order) are put instead; every other event as live.
    Returns (events, the arm's meals [{label, s, portions, kcal}])."""
    by_meal = {}
    for e in events:
        if e.get("kind") != "eat":
            continue
        lab = str(e.get("label") or "")
        meal = lab.rsplit("_", 1)[0]
        if meal in labels:
            by_meal.setdefault(meal, []).append(e)
    keep = [e for e in events if not (e.get("kind") == "eat" and str(e.get("label") or "").rsplit("_", 1)[0] in labels)]
    meals = []
    (a, b, c), tot = portions(kcal)
    for meal, evs in sorted(by_meal.items(), key=lambda kv: min(x["s"] for x in kv[1])):
        s = min(x["s"] for x in evs)
        i = 0
        for full, n in ((MIX650, a), (MIX217, b), (UNIT50, c)):
            for _ in range(n):
                keep.append({"s": s, "kind": "eat", "food": full, "label": f"REST_{meal}_{i}"})
                i += 1
        meals.append({"label": meal, "s": s, "portions": {MIX650: a, MIX217: b, UNIT50: c}, "kcal": tot})
    keep.sort(key=lambda e: e["s"])
    return keep, meals


def energy_pairs_grade(pairs, gap_s=PUSH_GAP_S, slack_s=LAG_SLACK_S):
    """The energy pairs (change 3): per pair the client's shown level (its mirror's body_energyLevel when a whole
    number, else K.view.mirrorEnergy's fallback: the rung of the mirrored body_energyState, read as the view's class)
    against the server's held level (the last push signature's energy digit). A pair is `equal`, `lag` (the server's
    level changed at most gap_s + slack_s wall seconds before the client read, and the client shows the level held
    before that change), or `mismatch`. The change's wall is the earliest it can have been: the server read of the
    last pair that still read the old level. Returns {pairs: [...], equal, lag, mismatch, changes, max_wall_gap,
    server_levels, steps_down, ok}: ok when no pair mismatches, every pair's wall gap is within PAIR_GAP_MAX_S, and
    the server's level never steps down."""
    rows, changes = [], []
    prev_lv, prev_wall = None, None
    cur_change = None
    steps_down = 0
    for p in pairs:
        s_lv = p.get("server_level")
        c_lv = p.get("client_level")
        sw = num(p.get("server_wall"))
        if prev_lv is not None and s_lv is not None and s_lv != prev_lv:
            cur_change = {"from": prev_lv, "to": s_lv, "after_wall": prev_wall, "seen_wall": sw, "age": p.get("age")}
            changes.append(cur_change)
            if s_lv < prev_lv:
                steps_down += 1
        cw = num(p.get("client_wall"))
        if c_lv is not None and s_lv is not None and c_lv == s_lv:
            kind = "equal"
        elif (cur_change is not None and c_lv == cur_change["from"] and cw is not None
              and cur_change["after_wall"] is not None and cw - cur_change["after_wall"] <= gap_s + slack_s):
            kind = "lag"
        else:
            kind = "mismatch"
        rows.append({"tag": p.get("tag"), "age": p.get("age"), "server_level": s_lv, "client_level": c_lv,
                     "client_moodle": p.get("client_moodle"), "client_view": p.get("client_view"),
                     "server_es": p.get("server_es"), "wall_gap": p.get("wall_gap"), "kind": kind})
        if s_lv is not None:
            prev_lv, prev_wall = s_lv, sw
    gaps = [abs(num(p.get("wall_gap"))) for p in pairs if num(p.get("wall_gap")) is not None]
    n = {k: sum(1 for r in rows if r["kind"] == k) for k in ("equal", "lag", "mismatch")}
    return {"pairs": rows, **n, "changes": changes, "max_wall_gap": max(gaps) if gaps else None,
            "server_levels": sorted({r["server_level"] for r in rows if r["server_level"] is not None}),
            "steps_down": steps_down,
            "ok": bool(rows) and n["mismatch"] == 0 and (not gaps or max(gaps) <= PAIR_GAP_MAX_S) and steps_down == 0}


def ring_levels(ring):
    """The server's held energy level per ring row (the lastSig digit), its changes [(s, age, from, to)], and whether
    it ever stepped down."""
    out, prev = [], None
    for r in ring:
        lv = energy_digit(r.get(LASTSIG))
        if lv is None:
            continue
        if prev is not None and lv != prev:
            out.append({"s": r.get("s"), "age": r.get("age"), "from": prev, "to": lv, "es": r.get("body.energyState")})
        prev = lv
    return {"changes": out, "steps_down": sum(1 for c in out if c["to"] < c["from"]), "last": prev}


# ---------------------------------------------------------------- the session
class Session:
    def __init__(self, profile_name, prefix, artifact, session_text, pred, stage_root, staged_at, budget_s,
                 driver_file, scenario, grade_fn=None, extra_meta=None, canteen=False):
        self.canteen = canteen
        self.pairs = []
        self.epairs = []
        self.carry = 0.0
        self.maint_kcal = None
        self._kh = None
        self.stops = []
        self.courses = []
        self.profile_name, self.prefix, self.artifact = profile_name, prefix, artifact
        self.pred, self.stage_root, self.staged_at = pred, stage_root, staged_at
        self.budget_s, self.scenario, self.grade_fn = budget_s, scenario, grade_fn
        self.prof = profile.load(profile_name)
        self.rec_fx = fx.load(self.prof.fixture)
        self.run_id, self.run_dir = new_run_dir(prefix)
        self.path = os.path.join(self.run_dir, artifact)
        self.tl, self.t0 = Timeline(), time.time()
        self.server, self.clients, self.started = None, {}, []
        self.cur = "pre"
        self.copied = []
        self.eats, self.drinks, self.marks, self.speeds = [], [], [], []
        doctor_clean, doctor_text = doctor()
        self.doctor_clean = doctor_clean
        self.out = {
            "run_id": self.run_id, "session": session_text, "driver": driver_file, "lib": "x36_gut_lib.py",
            "user": USER, "users": list(self.prof.users), "profile": self.prof.report(),
            "fixture": {"name": self.rec_fx.get("name"), "provision_run": self.rec_fx.get("provision_run"),
                        "build": self.rec_fx.get("build")},
            "argv": sys.argv[1:],
            "commit": git_say("rev-parse", "--short", "HEAD"),
            "mod_commit": git_say("log", "-1", "--format=%h", "--", MOD_DIR),
            "mod_dirty_not_booted": git_dirty(MOD_DIR)[0],
            "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
            "harness_lua_dirty": git_dirty(LUA_DIR)[0],
            "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
            "study_foods_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_StudyFoods"),
            "study_foods_dirty": git_dirty("testing/experiments/TKX_StudyFoods")[0],
            "replay_tool_commit": git_say("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
            "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/x36_gut_lib.py"),
            "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
            "host": {"free_gb_before_boot": free_gb(), "mem_min_gb": MEM_MIN_GB, "stray_clients": stray_clients()},
            "meta": {"staged_mod": stage_root + "/Contents/mods/NutritionRevamp", "staged_at": staged_at,
                     "staged_manifest": f"{stage_root}/{MANIFEST_NAME}", "canteen": canteen,
                     "phase_note": "a ring row is sampled inside EveryOneMinute before the mod's queue drains that "
                                   "minute: row k reads the state drain k-1 left (harness H2's comment block)",
                     "budget_s": budget_s, **(extra_meta or {})},
            "predictions": pred, "deviations": [],
            "world_changes": {"restored": "fixture default restored into the run dir (server and the admin client "
                                          "cache)", "left_in_place": []},
            "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
            "readings": {}, "eats": self.eats, "drinks": self.drinks, "marks": self.marks, "speeds": self.speeds,
            "stops": self.stops, "pairs": self.pairs, "energy_pairs": self.epairs, "courses": self.courses,
        }
        try:
            self.out["meta"]["staged_manifest_sha256"] = sha256_file(os.path.join(REPO, stage_root, MANIFEST_NAME))
            self.out["meta"]["harness_server_sha256"] = sha256_file(os.path.join(REPO, HARNESS_SERVER))
            self.out["meta"]["harness_core_sha256"] = sha256_file(os.path.join(REPO, HARNESS_CORE))
            self.out["meta"]["study_foods_sha256"] = sha256_file(os.path.join(REPO, STUDY_FOODS))
        except OSError as e:
            self.out["meta"]["hash_error"] = f"{type(e).__name__}: {e}"
        try:
            self.out["meta"]["jar_bytes"] = os.path.getsize(GAME_JAR)
            self.out["meta"]["jar_sha256"] = sha256_file(GAME_JAR)
            with open(APP_MANIFEST, encoding="utf-8", errors="replace") as fh:
                m = re.search(r'"buildid"\s+"(\d+)"', fh.read())
            self.out["meta"]["steam_buildid"] = m.group(1) if m else None
        except OSError as e:
            self.out["meta"]["install_read_error"] = f"{type(e).__name__}: {e}"

    # -- plumbing (x35's)
    def wall(self):
        return round(time.time() - self.t0, 3)

    def note(self, msg):
        self.out["notes"].append({"wall": self.wall(), "phase": self.cur, "note": msg})

    def persist(self):
        try:
            self.out["timeline"] = list(self.tl.items)
            if self.server is not None:
                self.out["server_errors"] = self.server.errors[:30]
                self.out["server_error_count"] = len(self.server.errors)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.out, fh, indent=1, default=str)
            os.replace(tmp, self.path)
        except Exception as e:                     # noqa: BLE001 - never raise on the write path
            print(f"could not write {self.path}: {type(e).__name__}: {e}")

    def step(self, name, side, cmd, args="", timeout=30, log=True):
        t_before, e_before = self.wall(), time.time()
        try:
            v = ask(resolve_side(side, self.server, self.clients), cmd, args, timeout=timeout)
        except Exception as e:                     # noqa: BLE001
            v = {"error": f"{type(e).__name__}: {e}"}
        t_after = self.wall()
        row = {"step": name, "side": side, "cmd": cmd, "args": args, "phase": self.cur, "wall_before": t_before,
               "wall_after": t_after, "epoch_ms_before": int(e_before * 1000), "epoch_ms_after": int(time.time() * 1000),
               "took": round(t_after - t_before, 3), "ack": v}
        if not isinstance(v, dict):
            row["ack_shape"] = type(v).__name__
        if log:
            self.out["steps"].append(row)
        return row

    def keep(self, r):
        a = dict(r["ack"]) if isinstance(r.get("ack"), dict) else {}
        a["wall"] = r["wall_before"]
        a["wall_after"] = r["wall_after"]
        a["side"] = a.get("side", r["side"])
        if not isinstance(r.get("ack"), dict):
            a["raw"] = r.get("ack")
        return a

    def lread(self, side, root, paths, tag, log=True):
        return self.keep(self.step(tag, side, "lua.read", " ".join([root] + list(paths)), log=log))

    def gread(self, name, tag):
        return self.keep(self.step(tag, SRV, "lua.global", name))

    def snap(self, tag, log=True):
        a = self.keep(self.step(tag, SRV, "time.snapshot", log=log))
        return {k: a.get(k) for k in ("worldAge", "hour", "minutes", "mult", "wall", "wall_after")} | {"tag": tag}

    def rcon(self, cmd, tag):
        t_before = self.wall()
        try:
            ok, rep = self.server.rcon(cmd)
        except Exception as e:                     # noqa: BLE001
            ok, rep = False, f"{type(e).__name__}: {e}"
        row = {"step": tag, "side": SRV, "cmd": "rcon", "args": cmd, "phase": self.cur, "wall_before": t_before,
               "wall_after": self.wall(), "ack": {"ok": ok, "reply": str(rep)[:300]}}
        self.out["steps"].append(row)
        self.tl.mark("rcon", cmd=cmd, ok=ok)
        return row["ack"]

    def parked(self):
        c = self.clients.get(USER) if isinstance(self.clients, dict) else None
        return c is not None and "lua_error" in getattr(c, "seen", {})

    def check(self):
        """The scenario's guard at every poll: the wall budget and the debugger park."""
        if self.wall() > self.budget_s:
            raise Budget(f"wall {self.wall()} s past the budget {self.budget_s} s")
        if self.parked():
            raise Budget("admin parked in the debugger")

    def wait_doc(self, name, after):
        try:
            return self.server.bus.wait_result(name, timeout=RESULT_WAIT_S, after=after)
        except Exception as e:                     # noqa: BLE001
            self.note(f"result {name}: {type(e).__name__}: {e}")
            return None

    def run_phase(self, name, fn):
        self.cur = name
        self.out["phase_walls"][name] = {"start": self.wall()}
        try:
            fn()
        except Budget as e:
            self.out["budget_stop"] = {"phase": name, "why": str(e), "wall": self.wall()}
            self.tl.mark("budget_stop", stopped_phase=name)     # F-T5-2: never phase= (Timeline.mark's own)
            self.note(f"phase {name} stopped: {e}")
        except Exception as e:                     # noqa: BLE001
            self.out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
            self.tl.mark("error", failed_phase=name, detail=str(e)[:200])     # F-T5-2
            self.note(f"phase {name} raised: {type(e).__name__}: {e}")
        self.out["phase_walls"][name]["end"] = self.wall()
        self.persist()

    # -- the clock verbs
    def _speed_row(self, mode, tag):
        s = self.snap(tag)
        self.speeds.append({"mode": mode, "age": s.get("worldAge"), "mult": s.get("mult"), "wall": s.get("wall")})
        return s

    def fast(self, tag="fast"):
        self.rcon(f"settimespeed {SPEED_FAST}", tag)
        return self._speed_row("fast", tag + "_t")

    def one(self, tag="one"):
        self.rcon("settimespeed 1", tag)
        return self._speed_row("one", tag + "_t")

    def slow(self, tag="slow"):
        self.rcon("settimespeed 1", tag + "_one")
        self.keep(self.step(tag, SRV, "time.multiplier", str(SLOW_MULT)))
        return self._speed_row("slow", tag + "_t")

    def age(self, tag="age"):
        return num(self.snap(tag, log=False).get("worldAge"))

    def hunger(self, tag="hunger"):
        a = self.keep(self.step(tag, SRV, "stats.all", USER, log=False))
        st = a.get("stats") or {}
        return num(st.get("HUNGER", st.get("Hunger"))), num(a.get("worldAge"))

    def wait_age(self, target, tag="wait"):
        while True:
            self.check()
            a = self.age(tag)
            if a is not None and a >= target:
                return a
            time.sleep(POLL_S)

    def to_request(self, label, level=H_REQ, approach=APPROACH, cap_age=None):
        """At the current speed until HUNGER >= approach, then speed 1 until HUNGER >= level, then slow(). Returns
        the crossing read {hunger, age}; cap_age: give up (slow(), return None) once the world age passes it."""
        h, a = self.hunger(label + "_h")
        while h is None or h < approach:
            self.check()
            if cap_age is not None and a is not None and a >= cap_age:
                self.slow(label + "_cap_slow")
                self.mark(label + "_cap", hunger=h)
                return None
            time.sleep(POLL_S)
            h, a = self.hunger(label + "_h")
        if h < level:
            self.one(label + "_one")
            while h is None or h < level:
                self.check()
                if cap_age is not None and a is not None and a >= cap_age:
                    self.slow(label + "_cap_slow")
                    self.mark(label + "_cap", hunger=h)
                    return None
                time.sleep(POLL_S)
                h, a = self.hunger(label + "_h")
        self.slow(label + "_slow")
        self.mark(label + "_request", hunger=h, read_age=a)
        return {"hunger": h, "age": a}

    def to_stop(self, age, label):
        """Speed 5 until STOP_LEAD_H before the stop, then speed 1 until its age; returns the arrival snapshot."""
        a = self.age(label + "_a")
        if a is not None and a < age - STOP_LEAD_H:
            self.fast(label + "_fast")
            self.wait_age(age - STOP_LEAD_H, label + "_wait_fast")
        self.one(label + "_one")
        self.wait_age(age, label + "_wait_one")
        return self.snap(label + "_arrive")

    def mark(self, name, **kw):
        a = self.age("mark_" + name)
        row = {"name": name, "age": a, "wall": self.wall(), **kw}
        self.marks.append(row)
        self.tl.mark("mark", name=name)
        return row

    # -- the intake verbs (x35's)
    def spawn(self, full_type, n=1, tag="spawn"):
        add = self.rcon(f'additem "{USER}" "{full_type}" {int(n)}', tag + "_additem")
        end = time.time() + SPAWN_CAP_S
        while time.time() < end:
            w = self.keep(self.step(tag + "_seen", CLI, "witness.fields", f"item {USER}/{full_type} getID"))
            if isinstance(w.get("resolved"), str) and w.get("resolved"):
                self.out["world_changes"]["left_in_place"].append(f"RCON additem {full_type} x{n}")
                return {"add": add, "seen": w}
            time.sleep(1.0)
        self.note(f"spawn {full_type}: the client never saw the RCON-added item")
        return {"add": add, "seen": None}

    def intake(self, tag):
        a = self.lread(SRV, "_G", INTAKE_PATHS, tag)
        v = a.get("values") or {}
        return {k.rsplit(".", 1)[-1]: num(v.get(k)) for k in INTAKE_PATHS}

    def eat(self, full_type, label):
        """foodtimer 0, eat.action <full_type> 1, landed polled until it rises (cap EAT_CAP_S)."""
        row = {"label": label, "food": full_type, "landed": False}
        self.eats.append(row)
        row["foodtimer"] = self.keep(self.step(label + "_foodtimer", SRV, "foodtimer.set", f"{USER} 0")).get("after")
        b = self.intake(label + "_before")
        row["before"] = b
        q = self.keep(self.step(label + "_eat", CLI, "eat.action", f"{full_type} 1"))
        row["queued"] = {k: q.get(k) for k in ("queued", "fraction", "spawned", "itemId", "validStart", "maxTime",
                                               "moodleFoodEaten", "wall")}
        if not q.get("queued"):
            row["queue_reply"] = q
            self.note(f"eat {label}: not queued: {str(q)[:300]}")
            return row
        end = time.time() + EAT_CAP_S
        while time.time() < end:
            if self.parked():
                break
            a = self.intake(label + "_poll")
            if a.get("landed") is not None and b.get("landed") is not None and a["landed"] > b["landed"]:
                row["landed"] = True
                row["after"] = a
                s = self.snap(label + "_landed_t")
                row["landed_age_polled"] = s.get("worldAge")
                row["landed_wall"] = s.get("wall")
                break
            time.sleep(POLL_S)
        if not row["landed"]:
            self.note(f"eat {label}: landed did not rise within {EAT_CAP_S} s")
        return row

    def drink(self, container, fluid, litres, label):
        """The container's SERVER copy filled with `litres` of `fluid` (fluid.fill, server; the client copy is the RCON
        spawn's, prefilled); autodrink.probe reads the litres before; drink.action <container> 1; sips polled until
        they stop rising for 3 polls after a rise (cap DRINK_CAP_S); autodrink.probe after."""
        row = {"label": label, "container": container, "fluid": fluid, "litres": litres, "drunk": None}
        self.drinks.append(row)
        row["fill"] = self.keep(self.step(label + "_fill", SRV, "fluid.fill", f"{USER} {container} {fluid} {litres}"))
        row["probe_before"] = self.keep(self.step(label + "_probe0", SRV, "autodrink.probe", USER))
        b = self.intake(label + "_before")
        row["before"] = b
        row["age0"] = self.age(label + "_age0")
        q = self.keep(self.step(label + "_drink", CLI, "drink.action", f"{container} 1"))
        row["queued"] = {k: q.get(k) for k in ("queued", "percentage", "spawned", "itemId", "filledRatioBefore", "wall")}
        if not q.get("queued"):
            row["queue_reply"] = q
            self.note(f"drink {label}: not queued: {str(q)[:300]}")
            return row
        end = time.time() + DRINK_CAP_S
        last, still, rose = b.get("sips"), 0, False
        while time.time() < end:
            if self.parked():
                break
            a = self.intake(label + "_poll")
            s = a.get("sips")
            if s is not None and last is not None and s > last:
                rose, still = True, 0
            elif rose:
                still += 1
            last = s
            if rose and still >= 3:
                break
            time.sleep(POLL_S)
        row["after"] = self.intake(label + "_after")
        row["age1"] = self.age(label + "_age1")
        row["probe_after"] = self.keep(self.step(label + "_probe1", SRV, "autodrink.probe", USER))
        l0 = num(g(row, "fill", "litres"))
        if g(row, "probe_before", "item") != container:
            self.note(f"drink {label}: the probe's first non-empty container before the drink is "
                      f"{g(row, 'probe_before', 'item')}, not {container}")
        l1 = num(g(row, "probe_after", "litres")) if g(row, "probe_after", "item") == container else 0.0
        row["drunk"] = (l0 - l1) if (l0 is not None and l1 is not None) else None
        row["sips"] = (num(row["after"].get("sips")) or 0) - (num(b.get("sips")) or 0)
        if not rose:
            self.note(f"drink {label}: sips never rose")
        return row

    def course(self, label, min_h, max_h, pair_every_m=None):
        """A meal's time course (change 2): from the last landed eat labelled `label` (its polled landing age), the world
        at speed 1 until HUNGER is back at H_REQ after falling below it and at least min_h game hours have passed, or
        max_h have; HUNGER polled about once a wall second; then slow(). With pair_every_m, a paired client/server
        stats read (Session.pair) every pair_every_m game minutes. Returns the course's row."""
        e = next((x for x in reversed(self.eats) if x.get("label") == label and x.get("landed")), None)
        a0 = num((e or {}).get("landed_age_polled")) or self.age(label + "_c0")
        c = {"label": label, "a0": a0, "min_h": min_h, "max_h": max_h, "request_age": None}
        self.courses.append(c)
        self.one(label + "_course_one")
        below, nxt = False, 0.0
        while True:
            self.check()
            h, a = self.hunger(label + "_ch")
            if h is not None and h < H_REQ:
                below = True
            if c["request_age"] is None and below and h is not None and h >= H_REQ:
                c["request_age"] = a
                self.mark(label + "_course_request", hunger=h, read_age=a)
            if pair_every_m and a is not None and a >= a0 + nxt / 60.0:
                self.pair(f"{label}_p{int(nxt)}")
                nxt += pair_every_m
            if a is not None and ((c["request_age"] is not None and a >= a0 + min_h) or a >= a0 + max_h):
                c["end_age"] = a
                break
            time.sleep(4 * POLL_S)
        self.slow(label + "_course_slow")
        c["capped"] = c["request_age"] is None
        return c

    def pair(self, tag):
        """A paired read (x35's, F-T9r-1's lesson): the client's stats.all, then at once the server's, each with its
        own wall stamps; the pair's wall gap is kept so a grade compares only reads taken within the same second."""
        c = self.keep(self.step(tag + "_cli", CLI, "stats.all"))
        s = self.keep(self.step(tag + "_srv", SRV, "stats.all", USER))

        def pick(a):
            stt = a.get("stats") or {}
            return {"HUNGER": num(stt.get("HUNGER", stt.get("Hunger"))),
                    "THIRST": num(stt.get("THIRST", stt.get("Thirst"))), "worldAge": num(a.get("worldAge")),
                    "wall": a.get("wall"), "wall_after": a.get("wall_after")}
        row = {"tag": tag, "client": pick(c), "server": pick(s)}
        cw, sw = num(row["client"]["wall"]), num(row["server"]["wall"])
        row["wall_gap"] = (sw - cw) if (cw is not None and sw is not None) else None
        self.pairs.append(row)
        return row

    def energy_pair(self, tag):
        """The energy pair (change 3): the client's CLI_ENERGY in one tick, at once the server's SRV_ENERGY in one tick,
        then the record's energy state and the world age. The levels: the server's held level is the signature's energy
        digit; the client's shown level is its mirror's body_energyLevel when a whole number, else its view's class."""
        c = self.lread(CLI, "_G", CLI_ENERGY, tag + "_cli", log=False)
        s = self.lread(SRV, "_G", SRV_ENERGY, tag + "_srv", log=False)
        b = self.lread(SRV, f"record:{USER}", ["body.energyState"], tag + "_rec", log=False)
        a = self.age(tag + "_a")
        cv, sv = c.get("values") or {}, s.get("values") or {}
        lv = num(cv.get(CLI_ENERGY[0]))
        view = num(cv.get(CLI_ENERGY[3]))
        shown = int(lv) if (lv is not None and lv == int(lv)) else (int(view) if view is not None else None)
        row = {"tag": tag, "age": a, "client_wall": c.get("wall"), "server_wall": s.get("wall"),
               "wall_gap": (num(s.get("wall")) - num(c.get("wall"))) if (num(s.get("wall")) is not None and
                                                                          num(c.get("wall")) is not None) else None,
               "client_mirror_level": lv, "client_mirror_es": num(cv.get(CLI_ENERGY[1])),
               "client_moodle": num(cv.get(CLI_ENERGY[2])), "client_view": view,
               "client_received": num(cv.get(CLI_ENERGY[4])), "client_level": shown,
               "server_sig": num(sv.get(SRV_ENERGY[0])), "server_level": energy_digit(sv.get(SRV_ENERGY[0])),
               "server_pushes": num(sv.get(SRV_ENERGY[1])),
               "server_es": num((b.get("values") or {}).get("body.energyState")),
               "client_missing": c.get("missing"), "server_missing": s.get("missing")}
        self.epairs.append(row)
        return row

    # -- the energy verbs (x35's)
    def kh(self):
        """The mod's own kernels on the lupa host (tools/replay_live.py's ServerReplay, no record): requestKcal and
        maint are the tool's NR_R lines."""
        if self._kh is None:
            self._kh = RL.ServerReplay(start=None, user=USER, sleep_allowed=SLEEP_ALLOWED)
        return self._kh

    def request_kcal(self, es, hod):
        return float(self.kh().R.requestKcal(es, hod, RL.H_REQ, KCAL_PER_H))

    def maint_of(self, fm, lm):
        k = self.kh()
        return float(k.R.maint(k.table({"fm": fm, "lm": lm})))

    def body_read(self, tag):
        paths = ["body.energyState", "body.fm", "body.lm", "body.eeDay", "body.inDay", "fluids.na", "fluids.water",
                 "fluids.naPlasma"]
        a = self.lread(SRV, f"record:{USER}", paths, tag)
        v = a.get("values") or {}
        out = {k.split(".", 1)[1]: num(v.get(k)) for k in paths}
        out["wall"] = a.get("wall")
        return out

    def eat_all(self, items, label):
        """Spawn then eat each (fullType, n) in order; returns the landed flags and the eats' labels."""
        for full, n in items:
            if n > 0:
                self.spawn(full, n, f"{label}_spawn_{full.split('.')[-1]}")
        landed, labs = [], []
        i = 0
        for full, n in items:
            for _ in range(n):
                lab = f"{label}_{i}"
                row = self.eat(full, lab)
                row["stop"] = label
                labs.append(lab)
                landed.append(row.get("landed") is True)
                i += 1
        return landed, labs

    def meal(self, kind, label, sched_age, factor=1.0):
        """A maint, surplus or request meal (change 2): es and the hour read; the kcal: maint is a third of the tool's
        maintenance (read once off the live body at the first maint or surplus meal), surplus that times `factor`,
        request the oracles' mapping; whole portions, the rounding carried on; eaten at the slow clock."""
        st = {"label": label, "kind": kind, "sched_age": sched_age, "factor": factor}
        self.stops.append(st)
        b = self.body_read(label + "_body")
        s = self.snap(label + "_read_t")
        age = num(s.get("worldAge"))
        st["read"] = {"es": b.get("energyState"), "fm": b.get("fm"), "lm": b.get("lm"), "eeDay": b.get("eeDay"),
                      "inDay": b.get("inDay"), "age": age, "hour": s.get("hour"), "minutes": s.get("minutes"),
                      "na": b.get("na"), "water": b.get("water"), "naPlasma": b.get("naPlasma")}
        hod = math.fmod(age + HOUR_OFFSET, 24.0) if age is not None else None
        st["hod"] = hod
        if kind in ("maint", "surplus"):
            if self.maint_kcal is None:
                self.maint_kcal = self.maint_of(b["fm"], b["lm"])
                self.out["readings"]["maint_kcal"] = self.maint_kcal
                self.out["readings"]["maint_body"] = {"fm": b["fm"], "lm": b["lm"], "age": age}
            target = self.maint_kcal / 3.0 * (factor if kind == "surplus" else 1.0)
        else:
            target = self.request_kcal(b["energyState"], hod)
        st["target"] = target
        st["carry_in"] = self.carry
        (a, c217, c50), tot = portions(target + self.carry)
        st["portions"] = {MIX650: a, MIX217: c217, UNIT50: c50}
        st["portion_kcal"] = tot
        items = [(MIX650, a), (MIX217, c217), (UNIT50, c50)]
        self.slow(label + "_slow")
        landed, labs = self.eat_all(items, label)
        st["eats"] = labs
        st["landed"] = landed
        eaten = 0.0
        k = 0
        for full, n in items:
            for _ in range(n):
                if landed[k]:
                    eaten += PORTION_KCAL[full]
                k += 1
        st["eaten_kcal"] = eaten
        self.carry = target + self.carry - eaten
        st["carry_out"] = self.carry
        st["age_done"] = self.age(label + "_done")
        self.out["readings"]["carry_out"] = self.carry
        if not all(landed):
            self.note(f"meal {label}: {landed.count(False)} portion(s) did not land; the carry takes them")
        return st

    def refill(self, label, sched_age=None):
        """The canteen's refill (x35's): autodrink.probe reads the first non-empty fluid container's litres, then the
        server fluid.fill puts CANTEEN_L of Water in the canteen (spawning it server-side the first time)."""
        st = {"label": label, "kind": "refill", "sched_age": sched_age}
        self.stops.append(st)
        pr = self.keep(self.step(label + "_probe", SRV, "autodrink.probe", USER))
        st["probe"] = {k: pr.get(k) for k in ("ok", "thirst", "autoDrink", "item", "litres", "fluid", "containers",
                                              "wall")}
        st["left_l"] = (num(pr.get("litres")) or 0.0) if pr.get("item") in (None, CANTEEN) else None
        if pr.get("item") not in (None, CANTEEN):
            self.note(f"refill {label}: the first non-empty container is {pr.get('item')}, not {CANTEEN}")
        f = self.keep(self.step(label + "_fill", SRV, "fluid.fill", f"{USER} {CANTEEN} Water {CANTEEN_L}"))
        st["fill"] = {k: f.get(k) for k in ("ok", "id", "spawned", "requested", "litres", "fluid", "capacity", "reason",
                                            "wall")}
        st["fill_ok"] = f.get("ok") is True
        st["filled_l"] = num(f.get("litres"))
        st["age"] = self.age(label + "_t")
        if not st["fill_ok"]:
            self.note(f"refill {label}: fluid.fill did not read back {CANTEEN_L} L: {str(f)[:300]}")
        return st

    def run_stops(self, schedule, end_age):
        """The session's stops [(age, kind, label[, factor])] from its start age to end_age (x35's run_schedule without
        the chain): a refill first in a canteen session; a meal stop already past by under LATE_MAX_H is done at once
        (late, named), an older one is missed (named, a deviation); a refill stop already past is skipped. Each meal is
        followed by a refill in a canteen session. Then speed 5 to end_age and speed 1."""
        X = self.out["phases"].setdefault("X", {})
        a0 = self.age("X_a0")
        X["start_age"], X["end_age"] = a0, end_age
        todo, missed, late, skipped = [], [], [], []
        for st in schedule:
            age, kind, label = st[0], st[1], st[2]
            if age >= end_age:
                continue
            if a0 is not None and age < a0:
                if kind == "refill":
                    skipped.append(label)
                elif a0 - age < LATE_MAX_H:
                    late.append(label)
                    todo.append(st)
                else:
                    missed.append(label)
                continue
            todo.append(st)
        X["late"], X["missed"], X["refills_skipped"] = late, missed, skipped
        if missed:
            self.out["deviations"].append(f"stops missed before this session's start: {missed}")
        if late:
            self.out["deviations"].append(f"stops done late at this session's start: {late}")
        if self.canteen:
            self.refill("X_refill0", a0)
        self.persist()
        for st in todo:
            self.check()
            age, kind, label = st[0], st[1], st[2]
            if kind in ("maint", "surplus", "request"):
                self.to_stop(age, label)
                self.meal(kind, label, age, st[3] if len(st) > 3 else 1.0)
                if self.canteen:
                    self.refill(label + "_R", age)
                self.fast(label + "_after_fast")
            elif kind == "refill":
                a = self.age(label + "_a")
                if a is not None and a < age:
                    self.fast(label + "_fast")
                    self.wait_age(age, label + "_wait_fast")
                if self.canteen:
                    self.refill(label, age)
            self.persist()
        self.check()
        a = self.age("X_tail_a")
        if a is not None and a < end_age:
            self.fast("X_tail_fast")
            self.wait_age(end_age, "X_tail_wait")
        self.one("X_end_one")
        X["done"] = True

    # -- the fixed phases
    def phase_S(self):
        P = self.out["phases"]["S"] = {}
        P["ready"] = [it for it in self.tl.items if it.get("phase") in ("client_launch", "client_ready")]
        P["players"] = self.keep(self.step("S_players", SRV, "players"))
        P["time"] = self.snap("S_time")
        P["mode"] = self.gread(f"{NR}.server.writer.mode", "S_mode")
        P["nutrition"] = self.keep(self.step("S_nutrition", SRV, "nutrition.get", USER))
        P["stats"] = self.keep(self.step("S_stats", SRV, "stats.all", USER))
        P["autodrink"] = self.keep(self.step("S_autodrink", SRV, "autodrink.set",
                                             f"{USER} {'true' if self.canteen else 'false'}"))

    def phase_H(self):
        P = self.out["phases"]["H"] = {}
        paths = list(RING_RECORD) + list(RING_GLOBALS)
        P["ring_paths"] = paths
        P["h1_record"] = self.lread(SRV, f"record:{USER}", list(RING_RECORD) + list(H1_EXTRA), "H_h1_record")
        P["h1_globals"] = self.lread(SRV, "_G", [p[3:] for p in RING_GLOBALS] + ["NutritionRevamp.version"],
                                     "H_h1_globals")
        P["ring_start"] = self.keep(self.step("H_ring_start", SRV, "minute.ring", " ".join([USER, "start"] + paths)))
        P["ring_start_snap"] = self.snap("H_ring_start_t")

    def phase_W(self):
        P = self.out["phases"]["W"] = {}
        first = self.lread(SRV, "_G", FLUSH_PATHS, "W_lw0")
        lw0 = num((first.get("values") or {}).get(FLUSH_PATHS[1]))
        P["lastWrite_before"] = lw0
        end = time.time() + SAVE_CAP_S
        polls = 0
        P["saved"] = False
        while time.time() < end:
            a = self.lread(SRV, "_G", FLUSH_PATHS[1:], "W_poll", log=False)
            polls += 1
            lw = num((a.get("values") or {}).get(FLUSH_PATHS[1]))
            if lw is not None and (lw0 is None or lw > lw0):
                P["saved"] = True
                P["lastWrite"] = lw
                P["saw_wall"] = a.get("wall")
                break
            time.sleep(POLL_S)
        P["polls"] = polls
        P["last"] = self.gread(f"{NR}.server.store.file.last.{USER}", "W_last")
        P["stats"] = self.keep(self.step("W_stats", SRV, "stats.all", USER))
        P["read"] = self.snap("W_read_t")
        txt = P["last"].get("value")
        if isinstance(txt, str):
            try:
                doc = json.loads(txt)
                rec = doc.get("rec") if isinstance(doc, dict) else None
                P["start_age"] = ((rec or {}).get("satiety") or {}).get("t")
                P["start_gen"] = doc.get("gen") if isinstance(doc, dict) else None
                with open(os.path.join(self.run_dir, "start.json"), "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(txt)
                self.copied.append("start.json")
            except ValueError as e:
                self.note(f"W: the saved line does not decode: {e}")
        st = {}
        stt = P["stats"].get("stats") or {}
        for k, cam in STAT_NAMES.items():
            v = stt.get(k, stt.get(cam))
            if num(v) is not None:
                st[k] = v
        with open(os.path.join(self.run_dir, "start-stats.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(st, fh, indent=1, sort_keys=True)
        self.copied.append("start-stats.json")

    def read_pages(self, tag, start_from=None, prefix=""):
        pages = []
        frm = start_from
        for _ in range(12):
            after = time.time() - 1.0
            args = f"{USER} read" + ("" if frm is None else f" {frm}")
            r = self.keep(self.step(f"{tag}_read", SRV, "minute.ring", args, timeout=60))
            pg = {"reply": r}
            name = r.get("result")
            if isinstance(name, str) and name:
                doc = self.wait_doc(name, after)
                pg["doc_rows"] = len((doc or {}).get("rows_list") or [])
                src = os.path.join(self.server.bus.results_dir, name + ".json")
                if doc is not None and os.path.isfile(src):
                    dest = prefix + name + ".json"
                    shutil.copyfile(src, os.path.join(self.run_dir, dest))
                    self.copied.append(dest)
                    pg["file"] = dest
            pages.append(pg)
            if not r.get("ok") or not r.get("more") or r.get("next") is None:
                break
            frm = r.get("next")
        return pages

    def phase_R(self):
        P = self.out["phases"]["R"] = {}
        P["pages"] = self.read_pages("R")
        last = P["pages"][-1]["reply"] if P["pages"] else {}
        P["next"] = last.get("next")

    def phase_D(self):
        P = self.out["phases"]["D"] = {}
        P["rcon_one"] = self.rcon("settimespeed 1", "D_rcon_one")
        P["q0"] = self.snap("D_q0")
        q0 = num(P["q0"].get("wall"))
        P["pre"] = self.lread(SRV, "_G", FLUSH_PATHS, "D_pre")
        c = self.clients.get(USER) if isinstance(self.clients, dict) else None
        tq = self.wall()
        P["quit_rc"] = c.quit() if c is not None else None
        P["quit_walls"] = [tq, self.wall()]
        self.tl.mark("client_quit", user=USER, rc=P["quit_rc"])
        end = time.time() + FLUSH_CAP_S
        P["flushed"] = False
        polls = []
        while time.time() < end:
            a = self.lread(SRV, "_G", FLUSH_PATHS, "D_poll", log=False)
            vals, miss = a.get("values") or {}, a.get("missing") or {}
            tabs, typs = a.get("tables") or {}, a.get("types") or {}
            on = FLUSH_PATHS[0]
            present = on in vals or on in tabs or on in typs
            lw = num(vals.get(FLUSH_PATHS[1]))
            polls.append({"wall": a.get("wall"), "online_present": present, "online_missing": miss.get(on),
                          "lastWrite": lw, "writes": vals.get(FLUSH_PATHS[2])})
            if not present and lw is not None and q0 is not None and lw >= q0:
                P["flushed"] = True
                P["flushed_wall"] = a.get("wall")
                break
            time.sleep(0.3)
        P["polls"] = polls[:5] + polls[-5:] if len(polls) > 10 else polls
        P["poll_count"] = len(polls)
        P["last"] = self.gread(f"{NR}.server.store.file.last.{USER}", "D_last")
        P["end_snap"] = self.snap("D_end_t")
        P["tail"] = self.read_pages("D_tail", (self.out["phases"].get("R") or {}).get("next"))
        P["stop"] = self.keep(self.step("D_ring_stop", SRV, "minute.ring", f"{USER} stop"))

    def phase_Z(self):
        P = self.out["phases"]["Z"] = {}
        errs = [str(e) for e in (self.server.errors if self.server is not None else [])]
        P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:10]
        P["admin_parked"] = self.parked()

    def read_logs(self, every):
        L = self.out["logs"] = {"patterns": {"life": MOD_LIFE_RX.pattern, "log": LOG_RX.pattern,
                                             "echo_excluded": ECHO_RX.pattern}, "limits": {"log": LOG_LIMIT},
                                "clients": {}}
        if self.server is not None:
            life, life_echo = grep_noecho(self.server.log_path, MOD_LIFE_RX, LOG_LIMIT)
            raw, echoed = grep_noecho(self.server.log_path, LOG_RX, LOG_LIMIT)
            L["server"] = {"life_lines": life, "life_echo_excluded": life_echo, "lines": raw,
                           "echo_lines_excluded": echoed}
        for c in every:
            u = getattr(c, "username", "?")
            lines, ech = grep_noecho(c.console, LOG_RX, 60)
            L["clients"].setdefault(u, []).append({"console": os.path.relpath(c.console, self.run_dir),
                                                   "lines": lines, "echo_lines_excluded": ech})

    def read_slots(self):
        S = self.out["slots"] = {"files": []}
        if self.server is None:
            return
        root = os.path.join(self.run_dir, "server")
        found = sorted(glob.glob(os.path.join(root, "**", "NutritionRevamp", "*", "p_*_*.json"), recursive=True))
        for f in found:
            rel = os.path.relpath(f, self.run_dir).replace(os.sep, "/")
            row = {"path": rel, "bytes": os.path.getsize(f), "sha256": sha256_file(f)}
            dest = "slot-" + os.path.basename(f)
            shutil.copyfile(f, os.path.join(self.run_dir, dest))
            self.copied.append(dest)
            row["copy"] = dest
            S["files"].append(row)

    # -- the read-back and the replay
    def ring_files(self):
        R = (g(self.out, "phases", "R", "pages") or []) + (g(self.out, "phases", "D", "tail") or [])
        return [p.get("file") for p in R if p.get("file")]

    def replay(self, files, tag="replay", write=True):
        """replay_live over the ring pages `files` from W's start record with the events built from the logs, the ring's
        autodrop rows and its movement flag (x35's); the raw rate and the exercise flag come from the ring inside the
        tool. Returns a dict."""
        RP = {}
        if not os.path.isfile(os.path.join(self.run_dir, "start.json")):
            RP["error"] = "no start record (phase W)"
            return RP
        with open(os.path.join(self.run_dir, "start.json"), encoding="utf-8") as fh:
            start = json.load(fh)
        with open(os.path.join(self.run_dir, "start-stats.json"), encoding="utf-8") as fh:
            start_stats = json.load(fh)
        rows = load_pages(self.run_dir, files)
        events0, notes = build_events(rows, self.eats, self.drinks)
        drops = autodrop_events(rows)
        moves = ring_moving_events(rows)
        # x35's hold-back: an autoDrop or movement event at or before the first ring row after the start record is
        # already in the start record (fluids.autoDrop is a stored input), so it is held back, named
        srec = start.get("rec", start) if isinstance(start, dict) else {}
        sa = num(g(srec, "satiety", "t"))
        if sa is None:
            sa = num(srec.get("kineticsAge")) if isinstance(srec, dict) else None
        first = next((r for r in rows if num(r.get("age")) is not None and (sa is None or r["age"] > sa + 1e-9)), None)
        held = [e for e in drops if first is not None and e["s"] <= first["s"]]
        drops = [e for e in drops if first is None or e["s"] > first["s"]]
        held_mv = [e for e in moves if first is not None and e["s"] <= first["s"]]
        moves = [e for e in moves if first is None or e["s"] > first["s"]]
        events = sorted(events0 + drops + moves, key=lambda e: e["s"])
        S = self.out["phases"].get("S") or {}
        nut = S.get("nutrition") or {}
        sex = g(self.out, "phases", "H", "h1_record", "values", "body.sex")
        player = {"female": sex == 2, "weight": num(nut.get("weight")) or 80.0,
                  "macros": [num(nut.get(k)) or 0.0 for k in ("calories", "carbs", "lipids", "proteins")]}
        RP["inputs"] = {"ring": files, "events_n": len(events), "notes": notes, "player": player,
                        "start_stats": start_stats, "start_age": g(self.out, "phases", "W", "start_age"),
                        "read_age": g(self.out, "phases", "W", "read", "worldAge")}
        if write:
            for name, obj in (("events.json", events), ("player.json", player)):
                with open(os.path.join(self.run_dir, name), "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(obj, fh, indent=1, sort_keys=True)
                self.copied.append(name)
            RP["inputs"]["cli"] = ("python tools/replay_live.py live --ring " + " ".join(files) +
                                   " --events events.json --start start.json --start-stats start-stats.json "
                                   "--player player.json --sleep-allowed false --out replay.json")
        rr, rpaths = RL.load_ring([os.path.join(self.run_dir, f) for f in files])
        t_r = time.time()
        RP["autodrops"] = {"n": len(drops), "water_g": sum(e["g"] for e in drops),
                           "held_in_start": held, "first_ring_s_after_start": first["s"] if first else None}
        RP["moving"] = {"n": len(moves), "held_in_start": held_mv}
        try:
            ron = [r for r in rr if r.get("age") is not None]
            left = RL.detect_autodrinks(ron, events)
            own = RL.detect_autodrinks(ron, events0)
            RP["autodrink_check"] = {"detected_beyond_autodrops": left, "injected": False,
                                     "detector_alone": {"n": len(own), "litres": sum(e["litres"] for e in own)}}
        except Exception as e:                     # noqa: BLE001
            RP["autodrink_check"] = {"error": f"{type(e).__name__}: {e}"}
        rows_out, be = RL.replay_live(rr, events, start, paths=rpaths, user=USER, player=player,
                                      start_stats=start_stats, sleep_allowed=SLEEP_ALLOWED)
        RP["seconds"] = round(time.time() - t_r, 2)
        RP["ring_activity"] = {"n": len(getattr(be, "ring_activity", None) or [])}
        d = RL.diff(rows_out, rr)
        dx = RL.diff(rows_out, rr, TOL_EXTRA)
        dg = diff_floor(rows_out, rr, TOL_GRADE)
        if write:
            doc = {"mode": "live", "offset": be.R.offset, "rows": rows_out, "diff": d, "eats": be.eats,
                   "diff_extra": dx, "diff_grade": dg, "dropped": getattr(be, "dropped", None), "events": events,
                   "ring_activity": getattr(be, "ring_activity", None)}
            with open(os.path.join(self.run_dir, "replay.json"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n")
            self.copied.append("replay.json")
        RP["offset"] = be.R.offset
        RP["rows"] = len(rows_out)
        RP["eats_replayed"] = len(be.eats)
        RP["diff"] = {k: d.get(k) for k in ("fields", "classes", "ok")} | {"findings": d.get("findings", [])[:40],
                                                                           "findings_n": len(d.get("findings", []))}
        RP["diff_extra"] = {k: dx.get(k) for k in ("fields", "classes", "ok")} | \
                           {"findings": dx.get("findings", [])[:40], "findings_n": len(dx.get("findings", []))}
        RP["diff_grade"] = dg
        RP["_rows"], RP["_ring"], RP["_events"] = rows_out, rr, events
        self.replay_events = events
        return RP

    def requests(self, rows_live, rows_rep, labels=None):
        """Per landed eat (or the labels given): the live and replay request minute after its landing row's age,
        under the request tolerance (3 game minutes or 2 %, the larger)."""
        out = {}
        for e in self.eats:
            if not e.get("landed") or e.get("ring_age") is None:
                continue
            lab = e["label"]
            if labels is not None and lab not in labels:
                continue
            a0 = e["ring_age"]
            lv = request_after(rows_live, a0)
            rp = request_after(rows_rep, a0)
            tol = max(3.0, 0.02 * rp) if rp is not None else None
            out[lab] = {"food": e["food"], "landing_s": e.get("ring_s"), "landing_age": a0,
                        "live_min": lv, "replay_min": rp,
                        "diff_min": (lv - rp) if (lv is not None and rp is not None) else None, "tol_min": tol,
                        "ok": (abs(lv - rp) <= tol) if (lv is not None and rp is not None) else None}
        return out

    # -- the whole run
    def body(self):
        for name, fn in (("S", self.phase_S), ("H", self.phase_H), ("W", self.phase_W),
                         ("X", lambda: self.scenario(self))):
            if self.parked():
                self.out["abort"] = f"admin parked in the debugger before phase {name}"
                break
            self.run_phase(name, fn)
        self.run_phase("R", self.phase_R)
        self.run_phase("D", self.phase_D)
        self.run_phase("Z", self.phase_Z)

    def grade_common(self):
        V = self.out["verdicts"]
        H = self.out["phases"].get("H") or {}
        rec = H.get("h1_record") or {}
        miss = rec.get("missing") or {}
        need = [p for p in RING_RECORD if p not in OPTIONAL_BEFORE_EAT]
        bad = {p: miss.get(p) for p in need if p in miss}
        st = H.get("ring_start") or {}
        V["H1"] = {"observed": {"ok": rec.get("ok"), "missing_needed": bad, "missing_all": miss,
                                "globals_missing": g(H, "h1_globals", "missing"),
                                "ring_start_ok": st.get("ok"), "armed": st.get("armed")},
                   "verdict": "as_predicted" if (rec.get("ok") is True and not bad and st.get("ok") is True)
                   else "falsified"}
        pages = (g(self.out, "phases", "R", "pages") or []) + (g(self.out, "phases", "D", "tail") or [])
        errs = [num(g(p, "reply", "errors")) for p in pages]
        V["RING"] = {"observed": {"pages": len(pages), "files": [p.get("file") for p in pages], "errors": errs,
                                  "overwritten": [g(p, "reply", "overwritten") for p in pages]},
                     "verdict": "as_predicted" if (pages and all(p.get("file") for p in pages)
                                                   and all((e or 0) == 0 for e in errs)) else "falsified"}
        D = self.out["phases"].get("D") or {}
        V["F"] = {"observed": {"flushed": D.get("flushed"), "polls": D.get("poll_count")},
                  "verdict": "as_predicted" if D.get("flushed") else "falsified"}
        Z = self.out["phases"].get("Z") or {}
        zl = Z.get("server_mod_error_lines") or []
        V["Z"] = {"observed": {"server_mod_error_lines": zl, "admin_lua_error": self.out.get("admin_lua_error")},
                  "verdict": "as_predicted" if (not zl and not self.out.get("admin_lua_error")) else "falsified"}

    def run(self):
        if not self.doctor_clean:
            self.out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
            self.persist()
            print(json.dumps(self.out["doctor"], indent=1))
            sys.exit(1)
        fg = self.out["host"]["free_gb_before_boot"]
        if not isinstance(fg, float) or fg < MEM_MIN_GB:
            self.out["error"] = f"free host memory {fg} GB under {MEM_MIN_GB}: not booted (CLAUDE.md s5)"
            self.persist()
            print(self.out["error"])
            sys.exit(1)
        lint_errors = lint_paths(self.prof.sources)
        self.out["lint_errors"] = lint_errors
        if lint_errors:
            self.out["error"] = "the layout lint found an ERROR in a profile mod folder; the session was not started"
            self.persist()
            print(json.dumps(lint_errors, indent=1))
            sys.exit(1)
        try:
            shutil.copyfile(os.path.join(REPO, self.stage_root, MANIFEST_NAME), os.path.join(self.run_dir, MANIFEST_NAME))
            self.copied.append(MANIFEST_NAME)
        except OSError as e:
            self.out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
        try:
            self.server = make_server(self.run_dir, self.rec_fx, mods=self.prof.mods, mod_sources=self.prof.sources,
                                      mod_skip=self.prof.skip, sandbox=self.prof.sandbox or None, ini=self.prof.ini)
            self.out["server_launch_wall"] = self.wall()
            self.server.start(timeout=self.prof.server_timeout)
            self.out["server_started_wall"] = self.wall()
            self.tl.mark("server_started")
            self.clients = attach_clients(self.run_dir, self.prof, self.server, self.rec_fx, self.tl,
                                          started=self.started)
            self.tl.mark("session_ready")
            self.out["session_ready_wall"] = self.wall()
            self.out["build"] = self.server.build
            self.out["verify"] = verify(self.prof, self.server, self.clients, self.tl)
            self.out["mods_not_found"] = {"server": sorted(set(self.server.mods_not_found)),
                                          **{u: sorted(set(c.mods_not_found)) for u, c in self.clients.items()}}
            self.persist()
            try:
                self.body()
            except Exception as e:                 # noqa: BLE001
                self.out["body_error"], self.out["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
                self.tl.mark("error", detail=str(e)[:200])
            self.persist()
        except Exception as e:                     # noqa: BLE001
            self.out["error"], self.out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
            self.tl.mark("error", detail=str(e)[:200])
        finally:
            every = list(self.started)
            try:
                if self.server is not None:
                    teardown(self.tl, self.server, [c for c in every if c.alive])
                    self.out["server_stop_wall"] = self.wall()
            except Exception as e:                 # noqa: BLE001
                self.out["teardown_error"] = f"{type(e).__name__}: {e}"
            finally:
                if self.server is not None:
                    hard_kill(self.server, every)
                adm = self.clients.get(USER) if isinstance(self.clients, dict) else None
                self.out["admin_lua_error"] = ("lua_error" in getattr(adm, "seen", ())) if adm is not None else None
                self.out["client_seen"] = [{"user": getattr(c, "username", str(i)), **dict(getattr(c, "seen", {}))}
                                           for i, c in enumerate(every)]
                if self.server is not None:
                    self.out["server_errors"] = self.server.errors[:30]
                    self.out["server_error_count"] = len(self.server.errors)
                self.out["host"]["free_gb_after"] = free_gb()
                for fn, key in ((lambda: self.read_logs(every), "logs_error"), (self.read_slots, "slots_error"),
                                (self.grade_common, "grade_common_error")):
                    try:
                        fn()
                    except Exception as e:         # noqa: BLE001
                        self.out[key] = f"{type(e).__name__}: {e}"
                self.persist()
                try:
                    files = self.ring_files()
                    if files:
                        RP = self.replay(files)
                        rows_rep, ring = RP.pop("_rows"), RP.pop("_ring")
                        RP.pop("_events", None)
                        self.out["replay"] = RP
                        self.out["readings"]["requests"] = self.requests(ring, rows_rep)
                        self.out["verdicts"]["REPLAY"] = {
                            "observed": {"ok": g(RP, "diff", "ok"), "fields": g(RP, "diff", "fields"),
                                         "classes": g(RP, "diff", "classes"), "findings_n": g(RP, "diff", "findings_n")},
                            "verdict": "as_predicted" if g(RP, "diff", "ok") else "falsified"}
                        self.out["verdicts"]["GRADE_DIFF"] = {
                            "observed": {"ok": g(RP, "diff_grade", "ok"), "fields": g(RP, "diff_grade", "fields"),
                                         "findings_n": g(RP, "diff_grade", "findings_n")},
                            "verdict": "as_predicted" if g(RP, "diff_grade", "ok") else "falsified"}
                        if self.grade_fn is not None:
                            self.grade_fn(self, ring, rows_rep)
                except Exception as e:             # noqa: BLE001
                    self.out.setdefault("replay", {})["error"] = f"{type(e).__name__}: {e}"
                    self.out["replay"]["traceback"] = traceback.format_exc()[-3000:]
                self.out["copied"] = sorted(set(self.copied))
                self.out["wall_seconds"] = round(time.time() - self.t0, 1)
                self.persist()
                dest_dir = os.path.join(REPO, "testing", "artifacts", self.run_id)
                try:
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.copyfile(self.path, os.path.join(dest_dir, self.artifact))
                    for f in sorted(set(self.copied)):
                        if os.path.isfile(os.path.join(self.run_dir, f)):
                            shutil.copyfile(os.path.join(self.run_dir, f), os.path.join(dest_dir, f))
                    print(f"copied to {dest_dir}")
                except Exception as e:             # noqa: BLE001
                    print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")
        print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in self.out.get("verdicts", {}).items()},
                          "requests": self.out["readings"].get("requests"),
                          "replay_ok": g(self.out, "replay", "diff", "ok"),
                          "replay_fields": g(self.out, "replay", "diff", "fields"),
                          "grade_fields": g(self.out, "replay", "diff_grade", "fields"),
                          "replay_error": g(self.out, "replay", "error"), "budget_stop": self.out.get("budget_stop"),
                          "error": self.out.get("error"), "body_error": self.out.get("body_error"),
                          "phase_errors": {k: v.get("error") for k, v in self.out.get("phase_errors", {}).items()},
                          "wall_seconds": self.out.get("wall_seconds"), "run_id": self.run_id,
                          "run_dir": self.run_dir}, indent=1, default=str)[:8000])
