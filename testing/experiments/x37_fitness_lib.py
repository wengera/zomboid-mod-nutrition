"""x37_fitness_lib -- the session engine of the Plan 11h Task 4 drivers (x371, x372): one set of each of the seven
vanilla Fitness exercises live on the staged copy of the tree at the final build of Plan 11h (C-2, exercise grading:
NR_Server_Fitness.lua wraps ISFitnessAction.serverStart and serverStop and records self.exeDataType per username in
NutritionRevamp.server.fitness.exeType; while the server's exercise flag is set, MET.readBilled bills the recorded
type's K.energy.EXERCISE_MET -- squats 3.0, pushups and situp 3.8, burpees 7.5, barbellcurl, dumbbellpress and
bicepscurl 3.5 -- and a set minute with no known type bills the flat Fitness class 6.0 and counts
NutritionRevamp.server.metabolism.stats.exeFallbacks; W.vigorous reads every flagged, awake minute as
resistance-vigorous). One driver a session, each on a fresh fixture restore (no chain).

It is x36_gut_lib.py (Plan 11g Task 8, frozen with x361's run) copied, not imported, with x35_exercise_lib.py's set
verbs, and these changes:
  1. THE RING (32 paths, the harness's cap): the record's satiety.M, S, L, t, body.energyState, body.met (the billed
     MET: ring row k + 1 reads what drain k billed), body.exKcalDay, body.epoc (absent until the first flagged minute,
     F-T6r-1: optional in H1), body.trail.c.ex, stomachFill, stomach.liquid, kineticsAge, body.inDay, body.eeDay,
     body.fm, body.lm, fluids.water, fluids.na, fluids.naPlasma, fluids.sweat6h, fluids.autoDrop; and eleven globals:
     the writer's writes and sips, the intake's eats, landed and sips, the bus's last push signature for the admin, the
     WRAPPER'S RECORD NutritionRevamp.server.fitness.exeType.admin (a string, absent when nil), the wrapper's starts,
     stops and untyped counters, and the metabolism's exeFallbacks. Every row also carries the harness's raw engine
     rate `rate`, the exercise flag `exe` and the movement flag `moving`. The x36 buffer gram keys and the thirst
     target are dropped for room (no meal is eaten in these sessions);
  2. THE SET (Session.run_set, x35's with a shorter ask): exercise.do <type> <minutes> on the client (the harness
     queues the game's own ISFitnessAction:new(p, name, minutes, exeData, exeData.type)), then a poll loop at the
     server (Session.fit_poll: the current exercise, the engine rate, the record's billed MET, S and epoc, the wrapper's
     record and counters and exeFallbacks in one lua.read, the world age) until the flag reads clear after it ran, or it
     never showed within SET_START_CAP_M game minutes (refused: rested and asked once more), or the world age passes the
     ask plus OVERRUN_M (x35's F-T6r-2: sets ran 1.2-2.5 times their ask); the clear's world age and the wrapper's
     record at the clear and REST_M game minutes later (the stale-record read). A set may be STOPPED instead
     (stop_after_m): after that many game minutes of a showing flag, player.stop clears the client's queue (the
     ISTimedActionQueue cancel: the action's forceStop, the route vanilla's movement press also takes, ISFitnessAction
     .update) and player.walk moves the character, the movement end case; the harness has no movement key press, so
     the cancel stands for it (named);
  3. THE PAIRS (Session.moodle_pair, the amendments' same-second pairs): the client's NR moodle levels (energy,
     hydration, stimulant, sleep, overfull: NutritionRevamp.client.moodles.levels) and received count in one tick, at
     once the server's last push signature and push count in one tick (its digits are the same five classes,
     K.view.pushSignature); then the client's stats.get and at once the server's (the vanilla moodles hungry, thirst,
     foodEaten, heavyLoad, endurance, each side computing its own, and HUNGER, endurance). moodle_pairs_grade: an NR
     class is equal, lags a server change by at most the push gap (60 s of wall clock plus 5 s), or mismatches;
  4. THE REPLAY'S EXERCISE TYPE (exetype_events): the replay tool's stand-in has no exercise type, so the lib sets the
     replay host's own NutritionRevamp.server.fitness.exeType.admin from the ring with the tool's `setpath` event
     wherever the ring's value changes (absent = nil), before that row's drain, the same timing as the tool's ring
     activity events; the counterfactual arm `flag_only` sets it only on flagged rows (cleared on every unflagged
     one), so a stale record that billed anything would show as a difference between live and that arm;
  5. THE READINGS (pure, shared with x37_grade.py): billing_rows (per flagged drain the next row's billed MET against
     EXERCISE_MET of the ring's recorded type, and of the set's asked type), set_reading (per set: the flagged runs,
     the record on them, the bill, the fallbacks' rise, the stale record after the clear and what the unflagged rows
     with it billed), met_agreement (the billed MET live against the replay, every row, exact to 1e-9) and the
     graded diff under TOL_GRADE (the 11f tolerances: HUNGER 0.002, es 0.005, L, epoc and trail.c.ex 0.5 %).
Kept from x36: the phases (boot, S, H, W, X, R, D, Z), the slot files, the replay of live (tools/replay_live.py at HEAD,
the ring's own raw rate and exercise flag, the movement flag off the ring), the artifact copy, the plumbing.

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run (x371), this file is never edited (CLAUDE.md
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
LIB_FILE = "x37_fitness_lib.py"
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
SAVE_CAP_S = 80.0
SPAWN_CAP_S = 15.0
FLUSH_CAP_S = 90.0
RESULT_WAIT_S = 30.0
POLL_S = 0.25
LOG_LIMIT = 400
BUF_KEYS = ("water", "proteins", "carbs", "lipids", "fibre")   # K.stomach.massOf's gram keys (not rung here)
FILL = "stomachFill"
LIQ = "stomach.liquid"
MPOOL = "satiety.M"
MET = "body.met"
EXK = "body.exKcalDay"
EPOC = "body.epoc"
TRAIL_EX = "body.trail.c.ex"
FOOD_FILL = "foodFill"     # derived off the ring (food_fill); None here, the buffer keys are not rung
RING_RECORD = ("satiety.M", "satiety.S", "satiety.L", "satiety.t", "body.energyState", MET, EXK, EPOC, TRAIL_EX, FILL,
               LIQ, "kineticsAge", "body.inDay", "body.eeDay", "body.fm", "body.lm", "fluids.water", "fluids.na",
               "fluids.naPlasma", "fluids.sweat6h", "fluids.autoDrop")
LASTSIG = "_G.NutritionRevamp.server.bus.lastSig.admin"
EXETYPE = "_G.NutritionRevamp.server.fitness.exeType.admin"      # the wrapper's record (absent when nil)
FIT_STARTS = "_G.NutritionRevamp.server.fitness.stats.starts"
FIT_STOPS = "_G.NutritionRevamp.server.fitness.stats.stops"
FIT_UNTYPED = "_G.NutritionRevamp.server.fitness.stats.untyped"
FALLBACKS = "_G.NutritionRevamp.server.metabolism.stats.exeFallbacks"
RING_GLOBALS = ("_G.NutritionRevamp.server.writer.stats.writes", "_G.NutritionRevamp.server.writer.stats.sips",
                "_G.NutritionRevamp.server.intake.stats.eats", "_G.NutritionRevamp.server.intake.stats.landed",
                "_G.NutritionRevamp.server.intake.stats.sips", LASTSIG, EXETYPE, FIT_STARTS, FIT_STOPS, FIT_UNTYPED,
                FALLBACKS)
EATS = "_G.NutritionRevamp.server.intake.stats.eats"
LANDED = "_G.NutritionRevamp.server.intake.stats.landed"
SIPS = "_G.NutritionRevamp.server.intake.stats.sips"
OPTIONAL_BEFORE_EAT = (EPOC,)   # the after-burn pool is made by the first flagged minute (F-T6r-1)
WSIPS = "_G.NutritionRevamp.server.writer.stats.sips"
H1_EXTRA = ("firstSeen", "resets", "body.sex", "body.fm", "body.lm")
FLUSH_PATHS = ("NutritionRevamp.server.players.online.admin", "NutritionRevamp.server.store.file.lastWrite.admin",
               "NutritionRevamp.server.store.file.stats.writes")
# the wrapper's state read in one tick at every set poll (the _G root, so no leading _G.)
FIT_PATHS = tuple(p[3:] for p in (EXETYPE, FIT_STARTS, FIT_STOPS, FIT_UNTYPED, FALLBACKS)) + (
    "NutritionRevamp.server.fitness.stats.failures", "NutritionRevamp.server.fitness.stats.passthrough",
    "NutritionRevamp.server.fitness.wrappedStart", "NutritionRevamp.server.fitness.wrappedStop",
    "NutritionRevamp.server.fitness.lastError")
NR_CLASSES = ("energy", "hydration", "stimulant", "sleep", "overfull")
CLI_MOODLES = tuple("NutritionRevamp.client.moodles.levels." + c for c in NR_CLASSES) + (
    "NutritionRevamp.client.received",)
SRV_SIG = ("NutritionRevamp.server.bus.lastSig.admin", "NutritionRevamp.server.bus.effects.stats.pushes")
SIG_DIGIT = {"overfull": 10000, "energy": 1000, "hydration": 100, "stimulant": 10, "sleep": 1}   # K.view.pushSignature
VANILLA_MOODLES = ("hungry", "thirst", "foodEaten", "heavyLoad", "endurance")   # TK.MOODLES
STAT_NAMES = {"HUNGER": "Hunger", "THIRST": "Thirst", "FATIGUE": "Fatigue", "BOREDOM": "Boredom",
              "UNHAPPINESS": "Unhappiness", "NICOTINE_WITHDRAWAL": "NicotineWithdrawal"}
# the graded tolerances, named before the runs: the 11f ones (HUNGER 0.002, es 0.005; L, the after-burn pool and the
# exercise trail 0.5 %, floor 1), the billed MET exact (1e-9: the replay bills by the same kernel from the same type)
TOL_GRADE = {"HUNGER": ("abs", 0.002), "body.energyState": ("abs", 0.005), "satiety.L": ("rel", 0.005, 1.0),
             EPOC: ("rel", 0.005, 1.0), TRAIL_EX: ("rel", 0.005, 1.0), MET: ("abs", 1e-9)}
MET_TOL = 1e-9
SLEEP_ALLOWED = False      # the live server: SleepAllowed and SleepNeeded false (the fixture default; ruling T4-1)
HOUR_OFFSET = 7.0          # world age 0 is 07:00 on the default fixture (#2890)
KCAL_PER_H = RL.KCAL_PER_H
AUTODROP = "fluids.autoDrop"
LITRES_PER_THIRST = 2.0    # NR_Server_Nutrients.lua NUT.LITRES_PER_THIRST: an autoDrop of x lands 2 x litres
RING_MOVING_LABEL = "ring-moving"
RING_EXETYPE_LABEL = "ring-exetype"
PUSH_GAP_S = 60.0          # NR_Server_Bus.lua PUSH_GAP_MS: at most one effects push per player per 60 s of wall clock
LAG_SLACK_S = 5.0          # the push rides the next slow minute after the gap, and the read's own wall resolution
PAIR_GAP_MAX_S = 1.0       # a pair's client and server reads within one wall second (the same-second rule)
# the set verbs (x35's, change 2)
EXE_CHAIN = "getFitness.getCurrentExe"                     # the server's current Fitness exercise (nil when none)
RATE_CHAIN = "getBodyDamage.getThermoregulator.getMetabolicRate"   # the server's engine metabolic rate (#2875)
MOVE_CHAIN = "isPlayerMoving"
SET_START_CAP_M = 3.0      # a set whose exercise never shows at the server within this many game minutes is refused
OVERRUN_M = 15.0           # a running set is followed this many game minutes past its ask at most
REST_M = 4.0               # game minutes at speed 1 after a set's clear (the stale-record read at its end)
ENDURANCE_MAX = 2          # ISFitnessUI.enduranceLevelThreshold: a set starts only at or under this endurance moodle
ENDURANCE_REST_CAP_M = 40.0   # game minutes at speed 5 at most waiting for the endurance moodle to come down
WALK_DX = 6                # tiles the movement end case walks
EXERCISES = ("squats", "pushups", "situp", "burpees", "barbellcurl", "dumbbellpress", "bicepscurl")
ITEMS = {"barbellcurl": "Base.BarBell", "dumbbellpress": "Base.DumbBell", "bicepscurl": "Base.DumbBell"}


def _kh_static():
    if "_KH" not in globals() or globals()["_KH"] is None:
        globals()["_KH"] = RL.ServerReplay(start=None, user=USER, sleep_allowed=SLEEP_ALLOWED)
    return globals()["_KH"]


def exercise_met(name):
    """The mod's own K.energy.exerciseMet(name) on the lupa host: (met, known)."""
    K = _kh_static().K
    met, known = K.energy.exerciseMet(name)
    return float(met), bool(known)


def fitness_met():
    return float(_kh_static().K.energy.COMPENDIUM.Fitness)


def idle_met():
    return float(_kh_static().K.energy.COMPENDIUM.Default)


def day_of(age):
    """The day of a world age (day 0 from midnight before the fixture's first 07:00, at age -7)."""
    return int(math.floor((age + 7.0) / 24.0 + 1e-12))




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


def food_fill(row):
    """The food fill of a ring or replay row (change 1): K.satiety.fill of the solid lane's gram keys' sum over
    K.stomach.CAPACITY_MAX_G, on the mod's own kernel (K.stomach.foodFill's arithmetic); None when a key is absent."""
    vals = [num(row.get("stomach.buffer." + k)) for k in BUF_KEYS]
    if any(v is None for v in vals):
        return None
    K = _kh_static().K
    return float(K.satiety.fill(sum(vals), K.stomach.CAPACITY_MAX_G))




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




# ---------------------------------------------------------------- the exercise readings (pure; change 5)
def ring_type(r):
    """The wrapper's record on a ring row: the string, or None (the path absent when the record is nil)."""
    v = r.get(EXETYPE)
    return v if isinstance(v, str) else None


def flagged(r):
    """Whether a ring row's sample read the server's exercise flag set (the drain of that minute reads it a few ticks
    later)."""
    return r.get("exe") is True


def exetype_events(rows, flag_only=False):
    """The replay's exercise type (change 4): one tool `setpath` event {s, path EXETYPE, value} before the drain of each
    online row whose recorded type differs from the last one set (from nil at the start), so the replay host's own
    NutritionRevamp.server.fitness.exeType.admin holds what the live server held when the row was sampled. flag_only:
    the counterfactual arm, the type set only on flagged rows and cleared on every unflagged one."""
    out = []
    cur = None
    for r in rows:
        if r.get("s") is None or r.get("on") is False:
            continue
        v = ring_type(r)
        if flag_only and not flagged(r):
            v = None
        if v == cur:
            continue
        out.append({"s": r["s"], "kind": "setpath", "path": EXETYPE, "value": v, "label": RING_EXETYPE_LABEL,
                    "age": r.get("age")})
        cur = v
    return out


def _consecutive(rows):
    """[(row, next row)] for the online rows whose sequence numbers follow on."""
    on = [r for r in rows if r.get("s") is not None]
    return [(a, b) for a, b in zip(on, on[1:]) if b["s"] == a["s"] + 1]


def billing_rows(ring, a0=None, a1=None, asked=None):
    """Per flagged drain (ring row k sampled with the flag set, row k + 1 reading what drain k billed): the recorded type
    on row k, the billed MET on row k + 1, the expected MET (K.energy.exerciseMet of the recorded type; the Fitness class
    6.0 with none), and, with `asked`, the asked type's MET. Rows with a0 < age <= a1 when given."""
    out = []
    for p, r in _consecutive(ring):
        a = num(p.get("age"))
        if a0 is not None and (a is None or a <= a0):
            continue
        if a1 is not None and (a is None or a > a1 + 1e-9):
            continue
        if not flagged(p):
            continue
        t = ring_type(p)
        exp, known = exercise_met(t) if t is not None else (fitness_met(), False)
        billed = num(r.get(MET))
        row = {"s": p["s"], "age": a, "type": t, "known": known, "billed": billed, "expected": exp,
               "ok": billed is not None and abs(billed - exp) <= MET_TOL}
        if asked is not None:
            am = exercise_met(asked)[0]
            row["asked_met"] = am
            row["ok_asked"] = billed is not None and abs(billed - am) <= MET_TOL
        out.append(row)
    return out


def _runs(idx):
    out = []
    for i in idx:
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def _delta(rows, key):
    vals = [num(r.get(key)) for r in rows if num(r.get(key)) is not None]
    return (vals[-1] - vals[0]) if len(vals) >= 2 else (0.0 if vals else None)


def set_reading(ring, st, rest_m=REST_M):
    """One set off the ring (change 5): the rows from the set's queueing to REST_M game minutes after its clear (or its
    last poll); the flagged runs; the recorded types on the flagged rows; the bills (billing_rows, the asked type's MET
    beside); the wrapper's starts, stops and untyped and the metabolism's exeFallbacks over the window; and the stale
    record: the unflagged rows after the last flagged row whose sample still read a recorded type, with what each
    drain billed (row k + 1's MET) and the moving flag."""
    a0 = num(st.get("age_queued"))
    end = num(st.get("clear_age")) or num(st.get("age_end"))
    if a0 is None or end is None:
        return {"label": st.get("label"), "rows": 0}
    a1 = end + rest_m / 60.0
    rows = [r for r in ring if num(r.get("age")) is not None and a0 - 1e-9 <= r["age"] <= a1 + 1e-9]
    idx = [i for i, r in enumerate(rows) if flagged(r)]
    bills = billing_rows(ring, a0 - 1e-6, a1, asked=st.get("exercise"))
    types = sorted({str(ring_type(rows[i])) for i in idx})
    out = {"label": st.get("label"), "exercise": st.get("exercise"), "asked_met": exercise_met(st["exercise"])[0],
           "a0": a0, "a1": a1, "rows": len(rows), "flagged": len(idx), "flag_runs": len(_runs(idx)),
           "types_on_flagged": types, "bills": bills, "billed_ok": sum(1 for b in bills if b["ok"]),
           "billed_asked_ok": sum(1 for b in bills if b.get("ok_asked")),
           "billed_hist": _hist([b["billed"] for b in bills]),
           "starts_delta": _delta(rows, FIT_STARTS), "stops_delta": _delta(rows, FIT_STOPS),
           "untyped_delta": _delta(rows, FIT_UNTYPED), "fallbacks_delta": _delta(rows, FALLBACKS)}
    if idx:
        out["first_flag_s"], out["last_flag_s"] = rows[idx[0]]["s"], rows[idx[-1]]["s"]
        out["flag_minutes"] = sum((num(rows[i + 1].get("dtM")) or 0.0) for i in idx if i + 1 < len(rows))
        stale = []
        by_s = {r["s"]: r for r in ring if r.get("s") is not None}
        for r in rows[idx[-1] + 1:]:
            t = ring_type(r)
            if t is None or flagged(r):
                continue
            nx = by_s.get(r["s"] + 1) or {}
            stale.append({"s": r["s"], "age": r["age"], "type": t, "billed_next": num(nx.get(MET)),
                          "type_met": exercise_met(t)[0], "moving": r.get("moving")})
        out["stale_rows"] = len(stale)
        out["stale"] = stale[:40]
        out["stale_billed_type_met"] = sum(1 for x in stale if x["billed_next"] is not None
                                           and abs(x["billed_next"] - x["type_met"]) <= MET_TOL)
    return out


def met_agreement(ring, rep_rows, only_s=None):
    """The billed MET live against a replay, matched on s, exact to MET_TOL on every online replay row (the between
    rows included: the bill is the drain's own, not an event's); only_s restricts to those sequence numbers."""
    by = {r["s"]: r for r in ring if r.get("s") is not None}
    n, bad = 0, []
    for q in rep_rows:
        s = q.get("s")
        if s not in by or q.get("offline"):
            continue
        if only_s is not None and s not in only_s:
            continue
        a, b = num(q.get(MET)), num(by[s].get(MET))
        if a is None or b is None:
            continue
        n += 1
        if abs(a - b) > MET_TOL:
            bad.append({"s": s, "age": by[s].get("age"), "replay": a, "live": b, "exe": by[s].get("exe"),
                        "type": ring_type(by[s])})
    return {"n": n, "mismatches": len(bad), "rows": bad[:40], "ok": n > 0 and not bad}


def _hist(vals):
    h = {}
    for v in vals:
        h[str(v)] = h.get(str(v), 0) + 1
    return h


def sig_digit(sig, cls):
    """The class level a push signature holds (K.view.pushSignature's digits): floor(sig / place) % 10."""
    v = num(sig)
    if v is None:
        return None
    return int(math.floor(v / SIG_DIGIT[cls])) % 10


def energy_digit(sig):
    return sig_digit(sig, "energy")


def moodle_pairs_grade(pairs, gap_s=PUSH_GAP_S, slack_s=LAG_SLACK_S):
    """The NR moodle pairs (change 3): per pair and class, the client's moodle level against the server's held class
    (the last push signature's digit). equal; lag (the server's class changed at most gap_s + slack_s wall seconds
    before the client read, and the client shows the class held before); or mismatch. The change's wall is the earliest
    it can have been: the server read of the last pair that still read the old class. Returns {classes: {c: {equal,
    lag, mismatch, changes}}, rows, equal, lag, mismatch, max_wall_gap, ok}: ok when no class mismatches and every
    pair's wall gap is within PAIR_GAP_MAX_S."""
    per = {}
    rows = []
    for c in NR_CLASSES:
        prev_lv, prev_wall, cur = None, None, None
        st = per[c] = {"equal": 0, "lag": 0, "mismatch": 0, "changes": []}
        for p in pairs:
            s_lv = sig_digit(p.get("server_sig"), c)
            c_lv = num((p.get("client_levels") or {}).get(c))
            sw, cw = num(p.get("server_wall")), num(p.get("client_wall"))
            if prev_lv is not None and s_lv is not None and s_lv != prev_lv:
                cur = {"from": prev_lv, "to": s_lv, "after_wall": prev_wall, "seen_wall": sw, "tag": p.get("tag")}
                st["changes"].append(cur)
            if c_lv is not None and s_lv is not None and c_lv == s_lv:
                kind = "equal"
            elif (cur is not None and c_lv == cur["from"] and cw is not None and cur["after_wall"] is not None
                  and cw - cur["after_wall"] <= gap_s + slack_s):
                kind = "lag"
            else:
                kind = "mismatch"
            st[kind] += 1
            rows.append({"tag": p.get("tag"), "class": c, "server": s_lv, "client": c_lv, "kind": kind})
            if s_lv is not None:
                prev_lv, prev_wall = s_lv, sw
    gaps = [abs(num(p.get("wall_gap"))) for p in pairs if num(p.get("wall_gap")) is not None]
    n = {k: sum(per[c][k] for c in NR_CLASSES) for k in ("equal", "lag", "mismatch")}
    return {"classes": per, "rows": rows, **n, "pairs": len(pairs), "max_wall_gap": max(gaps) if gaps else None,
            "ok": bool(pairs) and n["mismatch"] == 0 and (not gaps or max(gaps) <= PAIR_GAP_MAX_S)}


def vanilla_pairs_reading(pairs):
    """The vanilla moodles in the same pairs (a reading): per moodle, the pairs whose client level equals the server's,
    and the differing pairs; the largest same-second HUNGER and endurance differences."""
    out = {m: {"equal": 0, "differ": 0, "rows": []} for m in VANILLA_MOODLES}
    dh, de = [], []
    for p in pairs:
        cm, sm = p.get("client_moodles") or {}, p.get("server_moodles") or {}
        for m in VANILLA_MOODLES:
            a, b = num(cm.get(m)), num(sm.get(m))
            if a is None or b is None:
                continue
            if a == b:
                out[m]["equal"] += 1
            else:
                out[m]["differ"] += 1
                out[m]["rows"].append({"tag": p.get("tag"), "client": a, "server": b})
        for k, acc in (("hunger", dh), ("endurance", de)):
            a, b = num((p.get("client_body") or {}).get(k)), num((p.get("server_body") or {}).get(k))
            if a is not None and b is not None:
                acc.append(abs(a - b))
    gaps = [abs(num(p.get("stats_wall_gap"))) for p in pairs if num(p.get("stats_wall_gap")) is not None]
    return {"moodles": out, "hunger_max_abs": max(dh) if dh else None, "endurance_max_abs": max(de) if de else None,
            "max_wall_gap": max(gaps) if gaps else None, "pairs": len(pairs)}


def end_case(st):
    """A set's end (amendments 3): how it ended (timer: the flag cleared with no stop asked; stopped: after the
    driver's player.stop; capped: still running at the follow cap), and the wrapper's record and counters at the clear
    and REST_M game minutes later against the ones before the set."""
    b, c, r = st.get("before") or {}, st.get("at_clear") or {}, st.get("after_rest") or {}
    how = ("refused" if not st.get("started") else "stopped" if st.get("stopped") else
           "capped" if not st.get("ended") else "timer")

    def d(x, k):
        a, z = num(b.get(k)), num(x.get(k))
        return (z - a) if (a is not None and z is not None) else None
    return {"label": st.get("label"), "exercise": st.get("exercise"), "how": how,
            "requested_min": st.get("requested_min"), "first_on_age": st.get("first_on_age"),
            "clear_age": st.get("clear_age"), "stop_age": st.get("stop_age"),
            "ran_min": ((num(st.get("clear_age")) - num(st.get("first_on_age"))) * 60
                        if num(st.get("clear_age")) is not None and num(st.get("first_on_age")) is not None else None),
            "record_during": st.get("record_during"), "record_at_clear": c.get("exeType"),
            "record_after_rest": r.get("exeType"),
            "starts_delta_at_clear": d(c, "starts"), "stops_delta_at_clear": d(c, "stops"),
            "stops_delta_after_rest": d(r, "stops"), "fallbacks_delta_after_rest": d(r, "fallbacks"),
            "untyped_delta_after_rest": d(r, "untyped"), "failures_delta_after_rest": d(r, "failures")}


def grade_sets(sets, ring, rep_rows, rep_flag_rows=None):
    """Every set's readings and the verdicts' observations (change 5): per set set_reading and end_case; RECORD (the
    wrapper's record read during the set by the poll, and on every flagged ring row, equals the asked type); BILLED (every
    flagged drain bills the asked type's MET, but at most one per flagged run's edges, x35's skew rule); FALLBACKS (no
    exeFallbacks rise over a known type's set); STALE (no unflagged drain with a stale record bills that type's MET,
    unless the counterfactual flag_only replay bills the same: the bill is then the class's own); and the billed MET
    live against the replay on every row. Returns a dict."""
    per = []
    for st in sets:
        x = set_reading(ring, st)
        x["end"] = end_case(st)
        bills = x.get("bills") or []
        miss = len(bills) - (x.get("billed_asked_ok") or 0)
        x["record_ok"] = (st.get("record_during") == st.get("exercise")
                          and x.get("types_on_flagged") == [st.get("exercise")])
        x["billed_ok_verdict"] = bool(bills) and miss <= 2 * max(1, x.get("flag_runs") or 0)
        x["billed_all"] = bool(bills) and miss == 0
        x["fallbacks_ok"] = (x.get("fallbacks_delta") or 0) == 0
        per.append(x)
    out = {"sets": per}
    if rep_rows is not None:
        out["met_live_vs_replay"] = met_agreement(ring, rep_rows)
    if rep_flag_rows is not None:
        stale_s = set()
        for x in per:
            for r in x.get("stale") or []:
                stale_s.add(r["s"] + 1)
        out["met_live_vs_flag_only"] = met_agreement(ring, rep_flag_rows)
        out["stale_rows_vs_flag_only"] = met_agreement(ring, rep_flag_rows, only_s=stale_s) if stale_s else \
            {"n": 0, "mismatches": 0, "rows": [], "ok": None}
    return out


# ---------------------------------------------------------------- the session
class Session:
    def __init__(self, profile_name, prefix, artifact, session_text, pred, stage_root, staged_at, budget_s,
                 driver_file, scenario, grade_fn=None, extra_meta=None):
        self.canteen = False
        self.pairs = []
        self.mpairs = []
        self.sets = []
        self.rests = []
        self._kh = None
        self.stops = []
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
            "run_id": self.run_id, "session": session_text, "driver": driver_file, "lib": LIB_FILE,
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
            "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + LIB_FILE),
            "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
            "host": {"free_gb_before_boot": free_gb(), "mem_min_gb": MEM_MIN_GB, "stray_clients": stray_clients()},
            "meta": {"staged_mod": stage_root + "/Contents/mods/NutritionRevamp", "staged_at": staged_at,
                     "staged_manifest": f"{stage_root}/{MANIFEST_NAME}",
                     "phase_note": "a ring row is sampled inside EveryOneMinute before the mod's queue drains that "
                                   "minute: row k reads the state drain k-1 left (harness H2's comment block)",
                     "budget_s": budget_s, **(extra_meta or {})},
            "predictions": pred, "deviations": [],
            "world_changes": {"restored": "fixture default restored into the run dir (server and the admin client "
                                          "cache)", "left_in_place": []},
            "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
            "readings": {}, "eats": self.eats, "drinks": self.drinks, "marks": self.marks, "speeds": self.speeds,
            "stops": self.stops, "sets": self.sets, "rests": self.rests, "moodle_pairs": self.mpairs,
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

    def mark(self, name, **kw):
        a = self.age("mark_" + name)
        row = {"name": name, "age": a, "wall": self.wall(), **kw}
        self.marks.append(row)
        self.tl.mark("mark", name=name)
        return row

    # -- the intake verbs (x35's)
    def body_read(self, tag):
        paths = ["body.energyState", "body.fm", "body.lm", "body.eeDay", "body.inDay", "fluids.na", "fluids.water",
                 "fluids.naPlasma"]
        a = self.lread(SRV, f"record:{USER}", paths, tag)
        v = a.get("values") or {}
        out = {k.split(".", 1)[1]: num(v.get(k)) for k in paths}
        out["wall"] = a.get("wall")
        return out


    # -- the set verbs (change 2)
    def fit_read(self, tag, log=False):
        """The wrapper's state in one tick at the server (FIT_PATHS: the record, its counters, exeFallbacks, the wrap
        flags, the last error) and the world age."""
        f = self.lread(SRV, "_G", FIT_PATHS, tag + "_fit", log=log)
        v = f.get("values") or {}
        return {"age": self.age(tag + "_a"), "wall": f.get("wall"),
                "exeType": v.get(FIT_PATHS[0]), "starts": num(v.get(FIT_PATHS[1])), "stops": num(v.get(FIT_PATHS[2])),
                "untyped": num(v.get(FIT_PATHS[3])), "fallbacks": num(v.get(FIT_PATHS[4])),
                "failures": num(v.get(FIT_PATHS[5])), "passthrough": num(v.get(FIT_PATHS[6])),
                "wrappedStart": v.get(FIT_PATHS[7]), "wrappedStop": v.get(FIT_PATHS[8]), "lastError": v.get(FIT_PATHS[9])}

    def fit_poll(self, tag):
        """One poll at the server: its current Fitness exercise (EXE_CHAIN; the string "nil" when none), its engine
        metabolic rate, the record's billed MET, S, after-burn pool and exKcalDay, and the wrapper's state (fit_read)."""
        w = self.keep(self.step(tag + "_exe", SRV, "witness.chain", f"{USER} {EXE_CHAIN}", log=False))
        rt = self.keep(self.step(tag + "_rate", SRV, "witness.chain", f"{USER} {RATE_CHAIN}", log=False))
        rec = self.lread(SRV, f"record:{USER}", [MET, "satiety.S", EPOC, EXK], tag + "_rec", log=False)
        f = self.fit_read(tag)
        v = rec.get("values") or {}
        val = w.get("value")
        return {**f, "exe": val, "on": isinstance(val, str) and val not in ("", "nil"), "rate": num(rt.get("value")),
                "met": num(v.get(MET)), "S": num(v.get("satiety.S")), "epoc": num(v.get(EPOC)),
                "exKcal": num(v.get(EXK)), "wall": self.wall()}

    def endurance(self, tag):
        a = self.keep(self.step(tag, SRV, "stats.get", USER, log=False))
        return num((a.get("moodles") or {}).get("endurance")), num(a.get("endurance")), num(a.get("worldAge"))

    def ensure_rested(self, label):
        """Before a set: the server's endurance moodle read; above ENDURANCE_MAX - 1, speed 5 until it is at most
        ENDURANCE_MAX - 1 (ENDURANCE_REST_CAP_M game minutes at most), then speed 1. Returns the reads."""
        m, e, a = self.endurance(label + "_end0")
        row = {"label": label, "moodle0": m, "endurance0": e, "age0": a, "rested": False}
        if m is not None and m > ENDURANCE_MAX - 1:
            row["rested"] = True
            self.fast(label + "_rest_fast")
            cap = (a or 0.0) + ENDURANCE_REST_CAP_M / 60.0
            while True:
                self.check()
                m, e, a = self.endurance(label + "_end")
                if (m is not None and m <= ENDURANCE_MAX - 1) or (a is not None and a >= cap):
                    break
                time.sleep(4 * POLL_S)
            self.one(label + "_rest_one")
        row.update({"moodle1": m, "endurance1": e, "age1": a})
        self.rests.append(row)
        return row

    def run_set(self, name, minutes, label, stop_after_m=None):
        """One Fitness set (change 2): exercise.do <name> <minutes> (client), then fit_poll until the server's current
        exercise reads nil after it ran (clear_age), or it never showed within SET_START_CAP_M game minutes (refused),
        or the world age passes the ask plus OVERRUN_M (capped: player.stop then, named). The first poll that shows the
        flag and a record takes the moodle pair `<label>_mid`. stop_after_m: the movement end case (player.stop then
        player.walk WALK_DX tiles, that many game minutes after the flag first showed). After the clear: the wrapper's
        state at once (at_clear), a moodle pair, REST_M game minutes at speed 1, the state again (after_rest)."""
        st = {"label": label, "exercise": name, "requested_min": int(max(1, round(minutes))),
              "stop_after_m": stop_after_m, "stopped": False}
        self.sets.append(st)
        st["before"] = self.fit_read(label + "_f0")
        q = self.keep(self.step(label + "_do", CLI, "exercise.do", f"{name} {st['requested_min']}"))
        st["queued"] = {k: q.get(k) for k in ("ok", "queued", "queueLen", "error", "queueError", "wall")}
        st["age_queued"] = self.age(label + "_aq")
        polls, started, ended = [], False, False
        st["clear_age"] = st["first_on_age"] = st["record_during"] = None
        cap_age = (st["age_queued"] or 0.0) + (st["requested_min"] + OVERRUN_M) / 60.0
        while True:
            self.check()
            p = self.fit_poll(label + "_p")
            polls.append(p)
            a = p["age"]
            if p["on"]:
                if not started:
                    started, st["first_on_age"] = True, a
                if st["record_during"] is None and isinstance(p.get("exeType"), str):
                    st["record_during"] = p["exeType"]
                    st["record_during_age"] = a
                    self.moodle_pair(label + "_mid")
                if (stop_after_m is not None and not st["stopped"] and a is not None
                        and a >= st["first_on_age"] + stop_after_m / 60.0):
                    st["stop"] = {k: v for k, v in self.keep(self.step(label + "_stop", CLI, "player.stop")).items()
                                  if k in ("cleared", "clearError", "clientMoving", "wall")}
                    st["stop_age"] = self.age(label + "_sa")
                    r = self.keep(self.step(label + "_walk", CLI, "player.walk", f"{WALK_DX} 0"))
                    st["walk"] = {k: r.get(k) for k in ("queued", "error", "queueError", "clientMoving", "target",
                                                         "wall")}
                    st["stopped"] = True
            elif started:
                ended = True
                st["clear_age"] = a
                break
            if not started and a is not None and st["age_queued"] is not None and \
                    a > st["age_queued"] + SET_START_CAP_M / 60.0:
                break
            if a is not None and a >= cap_age:
                break
            time.sleep(POLL_S)
        st.update({"started": started, "ended": ended, "polls": polls, "age_end": self.age(label + "_ae")})
        if not started:
            self.note(f"set {label}: the server never showed exercise {name} (refused or not started)")
            return st
        if not ended:
            self.note(f"set {label}: still running at the follow cap ({OVERRUN_M} game minutes past its ask); "
                      "player.stop")
            st["cap_stop"] = {k: v for k, v in self.keep(self.step(label + "_capstop", CLI, "player.stop")).items()
                              if k in ("cleared", "clearError", "clientMoving", "wall")}
            end = time.time() + 20.0
            while time.time() < end:
                p = self.fit_poll(label + "_pc")
                polls.append(p)
                if not p["on"]:
                    st["clear_age"] = p["age"]
                    break
                time.sleep(POLL_S)
        st["at_clear"] = self.fit_read(label + "_fc", log=True)
        self.moodle_pair(label + "_end")
        base = num(st.get("clear_age")) or num(st["at_clear"].get("age"))
        if base is not None:
            self.wait_age(base + REST_M / 60.0, label + "_rest")
        if st["stopped"]:
            st["walk_stop"] = {k: v for k, v in self.keep(self.step(label + "_walkstop", CLI, "player.stop")).items()
                               if k in ("cleared", "clearError", "clientMoving", "wall")}
        st["after_rest"] = self.fit_read(label + "_fr", log=True)
        return st

    def moodle_pair(self, tag):
        """The moodle pair (change 3): the client's NR moodle levels and received count in one tick, at once the
        server's last push signature and push count in one tick; then the client's stats.get and at once the server's
        (the vanilla moodles, HUNGER and endurance). Each pair's wall gap is kept."""
        c = self.lread(CLI, "_G", CLI_MOODLES, tag + "_cli", log=False)
        s = self.lread(SRV, "_G", SRV_SIG, tag + "_srv", log=False)
        cb = self.keep(self.step(tag + "_cbody", CLI, "stats.get", "", log=False))
        sb = self.keep(self.step(tag + "_sbody", SRV, "stats.get", USER, log=False))
        cv, sv = c.get("values") or {}, s.get("values") or {}

        def body(a):
            return {"hunger": num(a.get("hunger")), "endurance": num(a.get("endurance")), "worldAge": num(a.get("worldAge"))}
        row = {"tag": tag, "client_wall": c.get("wall"), "server_wall": s.get("wall"),
               "wall_gap": (num(s.get("wall")) - num(c.get("wall"))) if (num(s.get("wall")) is not None and
                                                                          num(c.get("wall")) is not None) else None,
               "client_levels": {cl: num(cv.get(CLI_MOODLES[i])) for i, cl in enumerate(NR_CLASSES)},
               "client_received": num(cv.get(CLI_MOODLES[-1])),
               "server_sig": num(sv.get(SRV_SIG[0])), "server_pushes": num(sv.get(SRV_SIG[1])),
               "client_moodles": cb.get("moodles"), "server_moodles": sb.get("moodles"),
               "client_body": body(cb), "server_body": body(sb),
               "stats_wall_gap": (num(sb.get("wall")) - num(cb.get("wall"))) if (num(sb.get("wall")) is not None and
                                                                                  num(cb.get("wall")) is not None) else None,
               "client_missing": c.get("missing"), "server_missing": s.get("missing")}
        self.mpairs.append(row)
        return row

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
        P["fitness"] = self.fit_read("S_fit", log=True)     # the wraps installed (wrappedStart, wrappedStop)

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

    def replay(self, files, tag="replay", write=True, flag_only=False):
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
        types = exetype_events(rows, flag_only=flag_only)
        events = sorted(events0 + drops + moves + types, key=lambda e: e["s"])
        S = self.out["phases"].get("S") or {}
        nut = S.get("nutrition") or {}
        sex = g(self.out, "phases", "H", "h1_record", "values", "body.sex")
        player = {"female": sex == 2, "weight": num(nut.get("weight")) or 80.0,
                  "macros": [num(nut.get(k)) or 0.0 for k in ("calories", "carbs", "lipids", "proteins")]}
        RP["inputs"] = {"ring": files, "events_n": len(events), "notes": notes, "player": player,
                        "start_stats": start_stats, "start_age": g(self.out, "phases", "W", "start_age"),
                        "read_age": g(self.out, "phases", "W", "read", "worldAge")}
        suffix = "-flag-only" if flag_only else ""
        if write:
            for name, obj in (("events" + suffix + ".json", events), ("player.json", player)):
                with open(os.path.join(self.run_dir, name), "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(obj, fh, indent=1, sort_keys=True)
                self.copied.append(name)
            RP["inputs"]["cli"] = ("python tools/replay_live.py live --ring " + " ".join(files) +
                                   " --events events" + suffix + ".json --start start.json --start-stats start-stats.json "
                                   "--player player.json --sleep-allowed false --out replay" + suffix + ".json")
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
        dg = diff_floor(rows_out, rr, TOL_GRADE)
        if write:
            doc = {"mode": "live", "offset": be.R.offset, "rows": rows_out, "diff": d, "eats": be.eats,
                   "diff_grade": dg, "flag_only": flag_only, "dropped": getattr(be, "dropped", None), "events": events,
                   "ring_activity": getattr(be, "ring_activity", None)}
            with open(os.path.join(self.run_dir, "replay" + suffix + ".json"), "w", encoding="utf-8",
                      newline="\n") as fh:
                fh.write(json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n")
            self.copied.append("replay" + suffix + ".json")
        RP["offset"] = be.R.offset
        RP["rows"] = len(rows_out)
        RP["eats_replayed"] = len(be.eats)
        RP["diff"] = {k: d.get(k) for k in ("fields", "classes", "ok")} | {"findings": d.get("findings", [])[:40],
                                                                           "findings_n": len(d.get("findings", []))}
        RP["exetype_events"] = {"n": len(types), "flag_only": flag_only}
        RP["diff_grade"] = dg
        RP["_rows"], RP["_ring"], RP["_events"] = rows_out, rr, events
        self.replay_events = events
        return RP

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
                        RPf = self.replay(files, flag_only=True)
                        rows_flag = RPf.pop("_rows")
                        RPf.pop("_ring", None)
                        RPf.pop("_events", None)
                        self.out["replay_flag_only"] = RPf
                        self.out["verdicts"]["REPLAY"] = {
                            "observed": {"ok": g(RP, "diff", "ok"), "fields": g(RP, "diff", "fields"),
                                         "classes": g(RP, "diff", "classes"), "findings_n": g(RP, "diff", "findings_n")},
                            "verdict": "as_predicted" if g(RP, "diff", "ok") else "falsified"}
                        self.out["verdicts"]["GRADE_DIFF"] = {
                            "observed": {"ok": g(RP, "diff_grade", "ok"), "fields": g(RP, "diff_grade", "fields"),
                                         "findings_n": g(RP, "diff_grade", "findings_n")},
                            "verdict": "as_predicted" if g(RP, "diff_grade", "ok") else "falsified"}
                        if self.grade_fn is not None:
                            self.grade_fn(self, ring, rows_rep, rows_flag)
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
                          "replay_ok": g(self.out, "replay", "diff", "ok"),
                          "replay_fields": g(self.out, "replay", "diff", "fields"),
                          "grade_fields": g(self.out, "replay", "diff_grade", "fields"),
                          "replay_error": g(self.out, "replay", "error"), "budget_stop": self.out.get("budget_stop"),
                          "error": self.out.get("error"), "body_error": self.out.get("body_error"),
                          "phase_errors": {k: v.get("error") for k, v in self.out.get("phase_errors", {}).items()},
                          "wall_seconds": self.out.get("wall_seconds"), "run_id": self.run_id,
                          "run_dir": self.run_dir}, indent=1, default=str)[:8000])
