"""x29_exercise_lib -- the session engine of the Plan 11f Task 6 drivers: research rows 9 (the acute appetite
suppression around a vigorous bout and its decay) and 10 (the exercise lag over 7 game days), live. x291 is the vigour
gate and the decay leg (ruling 11f-5: the vigorous paths gated first, no synthetic MET injected); x292..x296 are the lag
chain on one live body, each session copying the previous one's <run>/server (reuse=True). It is x28_steady_lib.py
(Plan 11f Task 5r, frozen with x281's run) copied, not imported, with these changes:
  1. the ring (29 paths, the harness takes 32): + body.exKcalDay, body.metMinDay, body.band2Day and body.trail.c.ex
     (the trail's closed exercise sum, the hours before the current one); - stomach.buffer.calories,
     stomach.buffer.water, lastIntake.litres and fluids.k;
  2. THE REPLAY'S ACTIVITY EVENTS ARE READ OFF THE RING (a design departure, the class of ruling T5R-1's autoDrop
     drinks; named): the server bills the engine's metabolic rate by class (NR_Server_Metabolism.lua readActivity,
     K.energy.classOf, K.energy.activityMet), and the harness cannot sample that rate once a game minute, so the
     replay is told what the drain billed. Ring row k reads the state drain k-1 left; its body.met is drain k-1's
     billed MET, so an event {s: row k-1, activity, rate, exercising} is due before drain k-1. The rate is the engine
     value CLASS_MET[c] of the class c that classOf reaches, bills COMPENDIUM[c] = body.met, and lies nearest the
     engine MET the drain's training increment implies (K.training.metMinutes: body.metMinDay's rise over
     (fm + lm) / 80 x dtM, plus MET_FLOOR 1.5; it tells LightWork from DefaultExercise, both billed 3.0); a class whose
     engine value lies at or under the floor takes the idle Default (1.5) when billed alike. exercising is the drain's
     band2Day rise under BAND2_MET (K.training.band: band 2 below 9.0 is a Fitness exercise or a swing); at or above
     9.0 it keeps the last value. The replay's stand-in never swings (isCurrentState false): a swing minute the live
     writer counts vigorous is a live-only rise, graded as a finding. No MET is injected live;
  3. the decay leg's lua.setpath of the record's satiety.S is a replay event {s, setpath satiety.S} at the ring row
     whose drain first stepped from the set value (setpath_events);
  4. the gate's legs (run_gate): idle, a Fitness set (exercise.do, polled at the server: witness.chain
     getFitness.getCurrentExe and getBodyDamage.getThermoregulator.getMetabolicRate, the record's body.met, S and
     band2Day), the satiety.S set, and melee (RCON createhorde, then attack.melee windows at the nearest zombie with
     the server's current state polled through witness.chain getCurrentState);
  5. the chain's calendar (chain_schedule): day 0 the fixture's first day (world age 0 is 07:00, #2890; at(d, h) =
     24 d - 7 + h), meals at 13:00 and 20:00 (day 0) and 08:00, 13:00 and 20:00 (days 1-7); a bout at 15:00 on days
     0-6 (the driver's exercise, repeated sets inside a BOUT_MIN window); canteen refills at 02:00 and after every
     meal and bout; the chain ends at 15:30 on day 7, seven days after the first bout. A meal is maintenance-sized:
     a third of the tool's maintenance (x28's maint meal) plus a third of the latest bout's billed kcal (the oracles'
     lag_run feeds the idle day plus the bout; test_replay_live_energy.py);
  6. the chain's artifact prefix is the driver's artifact name's (lag-N.json), and the last bout's kcal carries.
Kept from x28: the auto-drink to thirst from a server canteen (ruling T5R-1) and its autoDrop drink events, the sodium
guard, F-T5-2's run_phase fix, the phases (boot, S, H, W, X, R, D, Z), the slot files, the replay of live and the
artifact copy.

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run (x291), this file is never edited (CLAUDE.md
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
RING_RECORD = ("satiety.P", "satiety.S", "satiety.L", "satiety.t", "body.energyState", "body.met", "body.exKcalDay",
               "body.metMinDay", "body.band2Day", "body.trail.c.ex", "acute.debtH", "stomachFill", "stomach.liquid",
               "body.inDay", "kineticsAge", "body.eeDay", "body.fm", "body.lm", "fluids.water", "fluids.na",
               "fluids.naPlasma", "fluids.sweat6h", "fluids.autoDrop", "fluids.thirstTarget")
RING_GLOBALS = ("_G.NutritionRevamp.server.writer.stats.writes", "_G.NutritionRevamp.server.writer.stats.sips",
                "_G.NutritionRevamp.server.intake.stats.eats", "_G.NutritionRevamp.server.intake.stats.landed",
                "_G.NutritionRevamp.server.intake.stats.sips")
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
STAT_NAMES = {"HUNGER": "Hunger", "THIRST": "Thirst", "FATIGUE": "Fatigue", "BOREDOM": "Boredom",
              "UNHAPPINESS": "Unhappiness", "NICOTINE_WITHDRAWAL": "NicotineWithdrawal"}
TOL_EXTRA = {"satiety.P": ("rel", 0.005), "satiety.S": ("abs", 1e-6), "stomachFill": ("abs", 0.002)}
SLEEP_ALLOWED = False      # the live server: SleepAllowed and SleepNeeded false (the fixture default; ruling T4-1)
HOUR_OFFSET = 7.0          # world age 0 is 07:00 on the default fixture (#2890): the hour of a world age a is (a + 7) % 24
KCAL_PER_H = RL.KCAL_PER_H  # 650 / 0.25: the intake mapping (ruling 11c-31), the tool's own constant
MIX650, MIX217, UNIT50 = "TKX.Mixed650", "TKX.Mixed217", "TKX.Unit50"
PORTION_KCAL = {MIX650: 650.0, MIX217: 650.0 / 3, UNIT50: 50.0}   # one per-kcal composition (tkx_study_foods.txt)
MIX333, MIX667 = "TKX.Mixed333", "TKX.Mixed667"
LATE_MAX_H = 1.0           # a meal stop already past by less than this at the session's start is done at once (late)
STOP_LEAD_H = 5 / 60.0     # speed 5 until this long before a stop, then speed 1 until its age
CANTEEN = "Base.CanteenMilitaryFull"   # x151t's D: a server-only canteen made and filled by the server fluid.fill
CANTEEN_L = 0.9            # the litres each refill puts in it (x151t's fill)
LITRES_PER_THIRST = 2.0    # NR_Server_Nutrients.lua:106 NUT.LITRES_PER_THIRST: an autoDrop of x lands 2 x litres
AUTODROP = "fluids.autoDrop"
MET = "body.met"
MMD = "body.metMinDay"
BAND2 = "body.band2Day"
EXK = "body.exKcalDay"
TRAIL_EX = "body.trail.c.ex"
IDLE_RATE = 1.5            # the engine's Default class (a live idle player reads 1.50, #2875): the replay stand-in's own default
SET_S_PATH = "NutritionRevamp.server.store.records." + USER + ".satiety.S"   # the live record's acute state (lua.setpath)
EXE_CHAIN = "getFitness.getCurrentExe"                     # the server's current Fitness exercise (nil when none)
RATE_CHAIN = "getBodyDamage.getThermoregulator.getMetabolicRate"   # the server's engine metabolic rate (#2875)
STATE_CHAIN = "getCurrentState"                            # the server's current state object (its class name)
SET_START_CAP_M = 3.0      # a set whose exercise never shows at the server within this many game minutes is refused
SET_MIN_LEFT_M = 3.0       # a bout queues no set with less than this left in its window
REST_M = 5.0               # a refused set (the endurance moodle above ISFitnessUI.enduranceLevelThreshold) rests this long
MAX_SETS = 8               # sets per bout at most
BOUT_MIN = 60.0            # the bout's window, game minutes
MELEE_SWINGS = 20          # attack.melee's most swings a window (ATTACK_MAX_SWINGS)
MELEE_FIND_S = 60.0        # wall seconds to find a zombie within 2 tiles after a createhorde


def at(d, h):
    """The world age of clock hour h on chain day d (day 0 the fixture's first day: midnight before day d is 24 d - 7)."""
    return 24.0 * d - 7.0 + h


BOUT_H = 15.0              # the daily bout's clock hour
FIRST_BOUT = None          # set below: the world age of day 0's bout
END_CHAIN = at(7, 15.5)    # the chain's end: 15:30 on day 7, seven days after day 0's bout


def chain_schedule():
    """The lag chain's fixed stops [(age, kind, label)], in age order (research row 10; change 5):
      day 0 (the fixture's first day, from the boot at about 11:00): meals at 13:00 and 20:00;
      days 1-7: meals at 08:00, 13:00 and 20:00 (none after the chain's end);
      days 0-6: a bout at BOUT_H (15:00);
      days 0-7: a canteen refill at 02:00 (every meal and bout refills the canteen after it too)."""
    out = []
    for h in (13.0, 20.0):
        out.append((at(0, h), "maint", "D0_%02d" % h))
    for d in range(1, 8):
        for h in (8.0, 13.0, 20.0):
            out.append((at(d, h), "maint", "D%d_%02d" % (d, h)))
    for d in range(0, 7):
        out.append((at(d, BOUT_H), "bout", "B%d" % d))
    for d in range(0, 8):
        out.append((at(d, 2.0), "refill", "R%d_0200" % d))
    out.sort(key=lambda x: x[0])
    return [x for x in out if x[0] < END_CHAIN]


SCHEDULE = chain_schedule()
FIRST_BOUT = at(0, BOUT_H)


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
    """The chain day of a world age (day 0 from midnight before the fixture's first 07:00, at age -7)."""
    return int(math.floor((age + 7.0) / 24.0 + 1e-12))


def eat_kcal(full):
    if full in PORTION_KCAL:
        return PORTION_KCAL[full]
    return {MIX333: 2000.0 / 6, MIX667: 2000.0 / 3}.get(full, 0.0)


def autodrop_events(rows):
    """The replay's drink events from the ring (change 4): each ring row reading fluids.autoDrop > 0 is the sip the
    writer folded in the drain before it, landed by the next drain as LITRES_PER_THIRST x autoDrop litres of water
    (NR_Server_Nutrients.lua:423-432); one event {s, drink, vec {water g}} at that row."""
    out = []
    for r in rows:
        v = num(r.get(AUTODROP))
        if v is not None and v > 0 and r.get("s") is not None:
            out.append({"s": r["s"], "kind": "drink", "vec": {"water": LITRES_PER_THIRST * v * 1000.0},
                        "label": "autodrop", "autoDrop": v, "age": r.get("age")})
    return out


def _classes():
    """[(class, engine value, billed MET)] for every class K.energy.classOf reaches from its own engine value, in
    CLASS_LIST order (Fitness and ForestryAxe are not reached: a 6.0 reads HeavyWork, an 8.0 ClimbRope)."""
    if globals().get("_CLASSES") is None:
        K = _kh_static().K
        out = []
        for i in range(1, len(K.energy.CLASS_LIST) + 1):
            c = K.energy.CLASS_LIST[i]
            r = float(K.energy.CLASS_MET[c])
            if K.energy.classOf(r) == c and K.energy.COMPENDIUM[c] is not None:
                out.append((str(c), r, float(K.energy.COMPENDIUM[c])))
        globals()["_CLASSES"] = out
    return globals()["_CLASSES"]


def rate_for(met, est, prev_rate):
    """(class, engine value) for a billed MET (change 2): the reached classes billing `met`; the one nearest `est`, the
    engine MET the training increment implies, when it lies above K.training.MET_FLOOR; else the idle Default among
    those at or under the floor (they bill and train alike), else the one nearest the previous rate. (None, None) when
    no reached class bills `met`."""
    cands = [(c, r) for c, r, b in _classes() if abs(b - met) < 1e-9]
    if not cands:
        return None, None
    floor = float(_kh_static().K.training.MET_FLOOR)
    if est is not None and est > floor + 1e-6:
        return min(cands, key=lambda x: (abs(x[1] - est), x[1]))
    low = [x for x in cands if x[1] <= floor + 1e-9] or cands
    idle = [x for x in low if x[0] == "Default"]
    if idle:
        return idle[0]
    return min(low, key=lambda x: (abs(x[1] - prev_rate), x[1]))


def activity_events(rows):
    """The replay's activity events read off the ring (change 2). For consecutive rows (prev, r): r's body.met is the
    MET drain prev billed; est = MET_FLOOR + (r's body.metMinDay - prev's) / ((fm + lm) / MASS_REF x prev's dtM) when
    the increment is not negative (a day close resets it); exercising = r's body.band2Day rose over prev's while the
    class's engine value is under BAND2_MET (else the last value). One event {s: prev's s, activity, rate,
    exercising, moving false} each time (rate, exercising) changes from the stand-in's start (IDLE_RATE, false).
    Returns (events, unknown): unknown lists the rows whose billed MET no reached class bills."""
    K = _kh_static().K
    floor, ref, band2 = float(K.training.MET_FLOOR), float(K.training.MASS_REF), float(K.training.BAND2_MET)
    out, unknown = [], []
    cur_rate, cur_ex = IDLE_RATE, False
    on = [r for r in rows if num(r.get("age")) is not None and r.get("s") is not None]
    for prev, r in zip(on, on[1:]):
        met = num(r.get(MET))
        if met is None:
            continue
        est = None
        a, b = num(prev.get(MMD)), num(r.get(MMD))
        dt = num(prev.get("dtM"))
        w = (num(r.get("body.fm")) or 0.0) + (num(r.get("body.lm")) or 0.0)
        if a is not None and b is not None and b >= a and dt is not None and dt > 0 and w > 0:
            est = floor + (b - a) / ((w / ref) * dt)
        c, rate = rate_for(met, est, cur_rate)
        if c is None:
            unknown.append({"s": r["s"], "met": met})
            continue
        ex = cur_ex
        x, y = num(prev.get(BAND2)), num(r.get(BAND2))
        if x is not None and y is not None and y >= x and rate < band2:
            ex = (y - x) > 1e-9
        if rate != cur_rate or ex != cur_ex:
            out.append({"s": prev["s"], "kind": "activity", "rate": rate, "exercising": ex, "moving": False,
                        "label": "activity", "class": c, "met": met, "est": est, "age": prev.get("age")})
            cur_rate, cur_ex = rate, ex
    return out, unknown


def setpath_events(rows, setpaths, path="satiety.S"):
    """The replay's setpath events (change 3): for each logged lua.setpath of the record's `path` to v (age_before its
    world age just before the call), the first ring row from age_before - 2 game minutes on that reads v exactly (the
    set landed before that row's sample: due at its s), else the first row whose value rose over the row before it to
    at least v / 2 (a drain stepped from v: due at the row before it). Returns (events, notes)."""
    out, notes = [], []
    on = [r for r in rows if num(r.get("age")) is not None and r.get("s") is not None]
    for sp in setpaths:
        v, a0 = num(sp.get("value")), num(sp.get("age_before"))
        if v is None or a0 is None or not sp.get("ok"):
            notes.append("setpath %s: no value, no age or not ok; no event" % sp.get("label"))
            continue
        hit = None
        for i in range(1, len(on)):
            r, p = on[i], on[i - 1]
            if r["age"] < a0 - 2.0 / 60:
                continue
            x, y = num(r.get(path)), num(p.get(path))
            if x is None:
                continue
            if abs(x - v) <= 1e-12:
                hit = r["s"]
                break
            if y is not None and x > y + 1e-9 and x >= 0.5 * v:
                hit = p["s"]
                break
        if hit is None:
            notes.append("setpath %s: no ring row shows the set; no event" % sp.get("label"))
            continue
        out.append({"s": hit, "kind": "setpath", "path": path, "value": v, "label": sp.get("label"), "age_before": a0})
    return out, notes


def leg_rows(ring, a0, a1):
    """The ring rows with a0 < age <= a1."""
    return [r for r in ring if num(r.get("age")) is not None and a0 < r["age"] <= a1 + 1e-9]


def leg_reading(ring, a0, a1):
    """A leg's ring readings: the billed MET's max and the game minutes it read at or above HeavyWork's 6.0 (each row's
    dtM to the next row is the minute its drain billed; read on the row's own dtM), satiety.S's max and its rises (a
    rise is a vigorous drain: the writer steps S toward the kind's weight only while vigorous, toward 0 otherwise),
    band2Day's rise, and exKcalDay's rise (within one mod day)."""
    rows = leg_rows(ring, a0, a1)
    mets = [num(r.get(MET)) for r in rows if num(r.get(MET)) is not None]
    hi = float(_kh_static().K.energy.COMPENDIUM.HeavyWork)
    vig_m = sum((num(r.get("dtM")) or 0.0) for r in rows if (num(r.get(MET)) or 0.0) >= hi - 1e-9)
    rises, smax = [], None
    for p, r in zip(rows, rows[1:]):
        x, y = num(p.get("satiety.S")), num(r.get("satiety.S"))
        if x is not None and y is not None and y > x + 1e-12:
            rises.append({"s": r["s"], "age": r["age"], "S": y, "met": num(r.get(MET))})
    for r in rows:
        v = num(r.get("satiety.S"))
        if v is not None:
            smax = v if smax is None else max(smax, v)
    def rise(key):
        tot = 0.0
        for p, r in zip(rows, rows[1:]):
            x, y = num(p.get(key)), num(r.get(key))
            if x is not None and y is not None and y >= x:
                tot += y - x
        return tot
    hist = {}
    for m in mets:
        hist[str(m)] = hist.get(str(m), 0) + 1
    return {"rows": len(rows), "age0": a0, "age1": a1, "met_max": max(mets) if mets else None, "met_hist": hist,
            "minutes_at_or_over_6": vig_m, "S_max": smax, "S_rises": len(rises), "S_rise_rows": rises[:60],
            "band2_rise_min": rise(BAND2), "exKcal_rise": rise(EXK)}


def _kh_static():
    if "_KH" not in globals() or globals()["_KH"] is None:
        globals()["_KH"] = RL.ServerReplay(start=None, user=USER, sleep_allowed=SLEEP_ALLOWED)
    return globals()["_KH"]


def hypo_grade(na_plasma):
    """The mod's own K.fluids.hyponatGrade on the lupa host (0 at or above its first threshold)."""
    if num(na_plasma) is None:
        return None
    return int(_kh_static().K.fluids.hyponatGrade(float(na_plasma)))


def fluid_days(ring, events):
    """Per chain day, off the ring: the drinking (mod side: the autoDrop events' water; the writer's sip folds), and
    the sodium guard (fluids.na, fluids.water and naPlasma at the day's last row, naPlasma's min and max, the
    hyponatraemia grade's max by the mod's own kernel, sweat6h's max)."""
    out = {}
    on = [r for r in ring if num(r.get("age")) is not None]
    for e in events:
        if e.get("label") != "autodrop":
            continue
        d = out.setdefault(str(day_of(e["age"])), {})
        d["drunk_g_mod"] = d.get("drunk_g_mod", 0.0) + e["vec"]["water"]
        d["autodrops"] = d.get("autodrops", 0) + 1
    prev = None
    for r in on:
        d = out.setdefault(str(day_of(r["age"])), {})
        d["rows"] = d.get("rows", 0) + 1
        d.setdefault("first_age", r["age"])
        d["last_age"] = r["age"]
        for k in ("fluids.na", "fluids.water", "fluids.k", "fluids.naPlasma", "body.energyState"):
            if num(r.get(k)) is not None:
                d[k + "_end"] = r[k]
        p = num(r.get("fluids.naPlasma"))
        if p is not None:
            d["naPlasma_min"] = min(d.get("naPlasma_min", p), p)
            d["naPlasma_max"] = max(d.get("naPlasma_max", p), p)
        sw = num(r.get("fluids.sweat6h"))
        if sw is not None:
            d["sweat6h_max"] = max(d.get("sweat6h_max", sw), sw)
        if prev is not None:
            a, b = num(prev.get(WSIPS)), num(r.get(WSIPS))
            if a is not None and b is not None and b > a:
                d["writer_sips"] = d.get("writer_sips", 0) + int(round(b - a))
        prev = r
    for d in out.values():
        lo = d.get("naPlasma_min")
        d["grade_max"] = hypo_grade(lo) if lo is not None else None
    return out


def energy_readings(S, ring, rows_rep):
    """The session's energy readings (each also re-derivable from the committed ring and events by x29_grade.py):
    the last ring age; the live kcal eaten per chain day (landed eats at their ring age); per meal stop the live es
    read at the stop against the ring row and the replay row at the read's first ring row after it; the hourly es of
    the ring (the row at or before each whole hour) with its replay twin; the billed eeDay at each day's last row."""
    R = S.out["readings"]
    on = [r for r in ring if num(r.get("age")) is not None]
    R["last_ring_age"] = on[-1]["age"] if on else None
    by_day = {}
    for e in S.eats:
        if e.get("ring_age") is None:
            continue
        d = day_of(e["ring_age"])
        by_day[str(d)] = by_day.get(str(d), 0.0) + eat_kcal(e["food"])
    R["live_kcal_by_day"] = by_day
    rep_by = {r["s"]: r for r in rows_rep}
    meals = []
    for st in S.stops:
        if st.get("kind") not in ("maint", "request"):
            continue
        a = num(g(st, "read", "age"))
        nxt = next((r for r in on if a is not None and r["age"] > a + 1e-9), None)
        rr = rep_by.get(nxt["s"]) if nxt else None
        meals.append({"label": st["label"], "read_age": a, "es_read": g(st, "read", "es"),
                      "next_ring_s": nxt["s"] if nxt else None,
                      "es_ring_next": nxt.get("body.energyState") if nxt else None,
                      "es_replay_next": rr.get("body.energyState") if rr else None,
                      "target": st.get("target"), "eaten_kcal": st.get("eaten_kcal")})
    R["meal_es"] = meals
    hourly = []
    if on:
        h0 = math.ceil(on[0]["age"])
        h1 = math.floor(on[-1]["age"])
        i = 0
        for h in range(int(h0), int(h1) + 1):
            while i + 1 < len(on) and on[i + 1]["age"] <= h + 1e-9:
                i += 1
            r = on[i]
            if r["age"] > h + 1e-9:
                continue
            rp = rep_by.get(r["s"])
            hourly.append({"hour_age": h, "s": r["s"], "age": r["age"], "es": r.get("body.energyState"),
                           "es_replay": rp.get("body.energyState") if rp else None, "eeDay": r.get("body.eeDay"),
                           "HUNGER": r.get("HUNGER"), "THIRST": r.get("THIRST"),
                           "naPlasma": r.get("fluids.naPlasma"), "na": r.get("fluids.na")})
    R["hourly"] = hourly


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


def session_grade(S, ring, rows_rep, pred):
    """The per-session readings and verdicts every x29 driver grades: energy_readings; the drinking and the sodium
    guard per chain day (fluid_days over the ring's autoDrop rows); the refills' container side; STOPS (every scheduled
    stop of this session's span done, every eat landed; a refill stop before the session's start is skipped, named)."""
    energy_readings(S, ring, rows_rep)
    R = S.out["readings"]
    R["fluid_days"] = fluid_days(ring, autodrop_events(ring))     # every ring row's autoDrop (the replay holds some back)
    R["refills"] = [{"label": st["label"], "age": st.get("age"), "left_l": st.get("left_l"), "filled_l": st.get("filled_l"),
                     "fill_ok": st.get("fill_ok")} for st in S.stops if st.get("kind") == "refill" or st.get("refill")]
    X = S.out["phases"].get("X") or {}
    stops = S.stops
    bad = [st["label"] for st in stops if not all(st.get("landed") or [True])]
    nofill = [st["label"] for st in stops if (st.get("kind") == "refill" or st.get("refill")) and not st.get("fill_ok")]
    S.out["verdicts"]["STOPS"] = {
        "predicted": pred.get("STOPS"),
        "observed": {"done": [st["label"] for st in stops], "missed": X.get("missed"), "late": X.get("late"),
                     "refills_skipped": X.get("refills_skipped"), "not_landed": bad, "fill_failed": nofill,
                     "scenario_done": X.get("done"), "budget_stop": S.out.get("budget_stop")},
        "verdict": "as_predicted" if (X.get("done") and not X.get("missed") and not bad and not nofill)
        else "falsified"}
    G = {}
    for d, v in R["fluid_days"].items():
        G[d] = {"grade_max": v.get("grade_max"), "naPlasma_min": v.get("naPlasma_min")}
    S.out["verdicts"]["SODIUM"] = {
        "predicted": pred.get("SODIUM"), "observed": G,
        "verdict": "as_predicted" if G and all(x.get("grade_max") == 0 for x in G.values()) else "falsified"}


def bout_readings(S, ring):
    """Per bout stop: its sets (started, ended, the polls' billed MET and engine rate maxima, the server's exercise
    names seen), the bout's exKcalDay rise read at the stop, and the ring's leg reading from the bout's start to 15
    game minutes past its end (the engine rate's approach back to idle bills after the last set)."""
    out = []
    for st in S.stops:
        if st.get("kind") != "bout":
            continue
        sets = []
        for s in st.get("sets") or []:
            polls = s.get("polls") or []
            sets.append({"label": s.get("label"), "started": s.get("started"), "ended": s.get("ended"),
                         "requested_min": s.get("requested_min"), "age_queued": s.get("age_queued"),
                         "age_end": s.get("age_end"), "polls": len(polls),
                         "exe_seen": sorted({str(p.get("exe")) for p in polls}),
                         "met_max": max([p["met"] for p in polls if p.get("met") is not None], default=None),
                         "rate_max": max([p["rate"] for p in polls if p.get("rate") is not None], default=None)})
        a0, a1 = num(st.get("age0")), num(st.get("age1"))
        out.append({"label": st["label"], "sched_age": st.get("sched_age"), "age0": a0, "age1": a1,
                    "bout_kcal_read": st.get("bout_kcal"), "sets": sets,
                    "ring": leg_reading(ring, a0, a1 + 0.25) if (a0 is not None and a1 is not None) else None})
    return out


def leg_readings(S, ring):
    """Per gate leg: the ring's leg reading over the leg, and the leg's own logs (the set's polls, the melee's states)."""
    out = []
    for leg in S.legs:
        a0, a1 = num(leg.get("age0")), num(leg.get("age1"))
        row = {"label": leg["label"], "kind": leg["kind"], "age0": a0, "age1": a1,
               "ring": leg_reading(ring, a0, a1) if (a0 is not None and a1 is not None) else None}
        s = leg.get("set")
        if s:
            polls = s.get("polls") or []
            row["set"] = {"started": s.get("started"), "ended": s.get("ended"), "age_queued": s.get("age_queued"),
                          "age_end": s.get("age_end"), "polls": len(polls),
                          "exe_seen": sorted({str(p.get("exe")) for p in polls}),
                          "met_max": max([p["met"] for p in polls if p.get("met") is not None], default=None),
                          "rate_max": max([p["rate"] for p in polls if p.get("rate") is not None], default=None)}
        if leg.get("windows") is not None:
            states = {}
            for w in leg["windows"]:
                for x in w.get("states") or []:
                    states[str(x.get("state"))] = states.get(str(x.get("state")), 0) + 1
            row["melee"] = {"windows": len(leg["windows"]), "states": states,
                            "swings": [g(w, "result", "swings") for w in leg["windows"]],
                            "returns": [g(w, "result", "returns") for w in leg["windows"]],
                            "target_dead": [g(w, "result", "targetDead") for w in leg["windows"]],
                            "hordes": len(leg.get("hordes") or [])}
        out.append(row)
    return out


def decay_reading(ring, events, half_life):
    """The decay leg (row 9): from each setpath event's ring row e (value v, satiety.t at e = t_e), every later ring row
    k until S rises again reads S_k against v x 0.5^((satiety.t_k - t_e) / half_life), the exact solution of
    K.satiety.exerciseSuppression's step at rest (not vigorous). Rows whose prediction is under 1e-4 are listed, not
    graded."""
    out = []
    by_s = {r["s"]: i for i, r in enumerate(ring) if r.get("s") is not None}
    for e in events:
        if e.get("kind") != "setpath" or e.get("s") not in by_s:
            continue
        i0 = by_s[e["s"]]
        t_e = num(ring[i0].get("satiety.t"))
        v = e["value"]
        rows, prev = [], None
        for r in ring[i0 + 1:]:
            S_, t = num(r.get("satiety.S")), num(r.get("satiety.t"))
            if S_ is None or t is None or t_e is None:
                continue
            if prev is not None and S_ > prev + 1e-12:
                break
            pred = v * 0.5 ** ((t - t_e) / half_life)
            rows.append({"s": r["s"], "age": r["age"], "t": t, "S": S_, "pred": pred,
                         "rel": (abs(S_ / pred - 1) if pred >= 1e-4 else None), "HUNGER": r.get("HUNGER")})
            prev = S_
        graded = [x["rel"] for x in rows if x["rel"] is not None]
        out.append({"event": e, "t_e": t_e, "rows": rows, "graded": len(graded),
                    "max_rel": max(graded) if graded else None,
                    "ok": (bool(graded) and max(graded) <= 0.01)})
    return out


def gate_grade(S, ring, rows_rep, pred):
    """The vigour gate's per-session grade (x291): session_grade's, then per leg the ring's reading (billed MET, the
    minutes at or above 6.0, S's rises: a vigorous drain), the VIGOUR verdict per candidate against the driver's
    prediction (True, False or None: unmeasured, any reading as_predicted), and the DECAY verdict (every graded row
    within 1 % of the half-life decay)."""
    session_grade(S, ring, rows_rep, pred)
    R = S.out["readings"]
    R["legs"] = leg_readings(S, ring)
    V = {}
    pv = pred.get("VIGOUR") or {}
    for leg in R["legs"]:
        if leg["kind"] not in ("exercise", "melee"):
            continue
        rr = leg.get("ring") or {}
        vig = (rr.get("S_rises") or 0) > 0
        p = pv.get(leg["label"])
        V[leg["label"]] = {"predicted": p, "observed": {"vigorous": vig, "met_max": rr.get("met_max"),
                                                        "minutes_at_or_over_6": rr.get("minutes_at_or_over_6"),
                                                        "S_max": rr.get("S_max"), "S_rises": rr.get("S_rises")},
                           "verdict": "as_predicted" if (p is None or p == vig) else "falsified"}
    S.out["verdicts"]["VIGOUR"] = {"observed": V,
                                   "verdict": "as_predicted" if all(v["verdict"] == "as_predicted" for v in V.values())
                                   else "falsified"}
    hl = float(_kh_static().K.satiety.ACUTE_DECAY_HALF_LIFE_H)
    ev = getattr(S, "replay_events", None) or []
    R["decay"] = decay_reading(ring, ev, hl)
    S.out["verdicts"]["DECAY"] = {"predicted": pred.get("DECAY"),
                                  "observed": [{"s": d["event"]["s"], "graded": d["graded"], "max_rel": d["max_rel"]}
                                               for d in R["decay"]],
                                  "verdict": "as_predicted" if (R["decay"] and all(d["ok"] for d in R["decay"]))
                                  else "falsified"}


def chain_grade(S, ring, rows_rep, pred):
    """The lag chain's per-session grade (x292..x296): session_grade's, the bouts' readings and the BOUTS verdict
    (every bout of the session's span ran a set the server showed)."""
    session_grade(S, ring, rows_rep, pred)
    R = S.out["readings"]
    R["bouts"] = bout_readings(S, ring)
    bad = [b["label"] for b in R["bouts"] if not any(s.get("started") for s in b["sets"])]
    S.out["verdicts"]["BOUTS"] = {"predicted": pred.get("BOUTS"),
                                  "observed": {"bouts": [b["label"] for b in R["bouts"]], "no_set": bad,
                                               "kcal_read": [b["bout_kcal_read"] for b in R["bouts"]]},
                                  "verdict": "as_predicted" if (R["bouts"] and not bad) else "falsified"}


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


# ---------------------------------------------------------------- the read-back (pure; tested offline on x260's files)
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
    """The replay's event list from the ring and the driver's logs. eats: [{food, landed}] in queue order; an eat is
    keyed to the first ring row whose intake.stats.eats rose (one event per unit of the rise, in queue order).
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
    nearest rows' ages."""
    t = after_age + minute / 60.0
    lo = hi = None
    for r in rows:
        if num(r.get("age")) is None or num(r.get(field)) is None:
            continue
        if r["age"] <= t:
            lo = r
        elif hi is None:
            hi = r
            break
    if lo is None or hi is None:
        return None
    if hi["age"] == lo["age"]:
        return {"value": lo[field], "lo_age": lo["age"], "hi_age": hi["age"]}
    w = (t - lo["age"]) / (hi["age"] - lo["age"])
    return {"value": lo[field] + w * (hi[field] - lo[field]), "lo_age": lo["age"], "hi_age": hi["age"],
            "lo_s": lo.get("s"), "hi_s": hi.get("s")}


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


# ---------------------------------------------------------------- the session
class Session:
    def __init__(self, profile_name, prefix, artifact, session_text, pred, stage_root, staged_at, budget_s,
                 driver_file, scenario, grade_fn=None, extra_meta=None, prev_run=None, prev_prefix=None, end_age=None,
                 bout_ex=None):
        self.prev_run, self.prev_prefix, self.end_age = prev_run, prev_prefix, end_age
        self.bout_ex = bout_ex
        self.last_bout = 0.0
        self.setpaths, self.legs = [], []
        self.prev_doc = None
        self.carry = 0.0
        self.maint_kcal = None
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
            "run_id": self.run_id, "session": session_text, "driver": driver_file, "lib": "x29_exercise_lib.py",
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
            "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/x29_exercise_lib.py"),
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
            "stops": self.stops, "legs": self.legs, "setpaths": self.setpaths, "bout_ex": bout_ex,
            "chain": {"prev_run": prev_run, "prev_prefix": prev_prefix, "end_age": end_age},
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

    # -- plumbing (x260's)
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
        the crossing read {hunger, age}; cap_age: give up (return None) once the world age passes it."""
        h, a = self.hunger(label + "_h")
        while h is None or h < approach:
            self.check()
            if cap_age is not None and a is not None and a >= cap_age:
                self.mark(label + "_cap", hunger=h)
                return None
            time.sleep(POLL_S)
            h, a = self.hunger(label + "_h")
        if h < level:
            self.one(label + "_one")
            while h is None or h < level:
                self.check()
                time.sleep(POLL_S)
                h, a = self.hunger(label + "_h")
        self.slow(label + "_slow")
        self.mark(label + "_request", hunger=h, read_age=a)
        return {"hunger": h, "age": a}

    def to_age(self, target, label):
        """Fast until target - 6 game min, speed 1 until target - 1.5 game min, then slow()."""
        a = self.age(label + "_a")
        if a is not None and a < target - 6 / 60:
            self.wait_age(target - 6 / 60, label + "_wait_fast")
        a = self.age(label + "_a")
        if a is not None and a < target - 1.5 / 60:
            self.one(label + "_one")
            self.wait_age(target - 1.5 / 60, label + "_wait_one")
        self.slow(label + "_slow")
        h, a = self.hunger(label + "_h")
        self.mark(label + "_at", hunger=h, read_age=a, target=target)
        return {"hunger": h, "age": a}

    def mark(self, name, **kw):
        a = self.age("mark_" + name)
        row = {"name": name, "age": a, "wall": self.wall(), **kw}
        self.marks.append(row)
        self.tl.mark("mark", name=name)
        return row

    # -- the intake verbs
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
        """The container is spawned (RCON; both copies prefilled) and its SERVER copy refilled with `litres` of
        `fluid` (fluid.fill, server); autodrink.probe reads the litres before; drink.action <container> 1; sips
        polled until they stop rising for 3 polls after a rise (cap DRINK_CAP_S); autodrink.probe after."""
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

    # -- the chain (research s2; ruling S0-2)
    def chain_pre(self):
        """Before the boot: the previous session's artifact read (its carry, its maintenance kcal, its last ring age),
        its <run>/server copied whole into this run's folder (each session its own folder, so a failed session never
        damages the saved state), and the copied slot files listed with their sha256."""
        C = self.out["chain"]
        prev = self.prev_run
        if not os.path.isdir(os.path.join(prev, "server", "Server")):
            raise RuntimeError(f"the previous session has no server cache at {prev}/server")
        doc_path = next((os.path.join(prev, f) for f in sorted(os.listdir(prev))
                         if f.endswith(".json") and f.startswith(self.artifact.split("-")[0] + "-")), None)
        if doc_path is None:
            raise RuntimeError(f"no {self.artifact.split('-')[0]}-*.json artifact in {prev}")
        with open(doc_path, encoding="utf-8") as fh:
            self.prev_doc = json.load(fh)
        pid = self.prev_doc.get("run_id", "")
        if self.prev_prefix and not str(pid).startswith(self.prev_prefix + "-"):
            raise RuntimeError(f"the previous run {pid} is not a {self.prev_prefix} run")
        if self.prev_doc.get("error"):
            raise RuntimeError(f"the previous run {pid} carries an error: {self.prev_doc.get('error')}")
        R = self.prev_doc.get("readings") or {}
        self.carry = num(R.get("carry_out")) or 0.0
        self.maint_kcal = num(R.get("maint_kcal"))
        if self.maint_kcal is not None:
            self.out["readings"]["maint_kcal"] = self.maint_kcal
            self.out["readings"]["maint_body"] = R.get("maint_body")
        self.out["readings"]["carry_out"] = self.carry
        self.last_bout = num(R.get("last_bout_kcal")) or 0.0
        self.out["readings"]["last_bout_kcal"] = self.last_bout
        C.update({"prev_run_id": pid, "prev_artifact": os.path.basename(doc_path), "carry_in": self.carry,
                  "maint_kcal_in": self.maint_kcal, "last_bout_in": self.last_bout, "prev_last_ring_age": R.get("last_ring_age"),
                  "prev_end_snap": g(self.prev_doc, "phases", "D", "end_snap"),
                  "prev_flushed": g(self.prev_doc, "phases", "D", "flushed"),
                  "prev_stops": [st.get("label") for st in self.prev_doc.get("stops") or []]})
        t = time.time()
        shutil.copytree(os.path.join(prev, "server"), os.path.join(self.run_dir, "server"))
        C["copy_seconds"] = round(time.time() - t, 2)
        C["slots"] = [{"rel": os.path.relpath(f, self.run_dir).replace(os.sep, "/"), "bytes": os.path.getsize(f),
                       "sha256": sha256_file(f)}
                      for f in sorted(glob.glob(os.path.join(self.run_dir, "server", "**", "NutritionRevamp", "*",
                                                             "p_*_*.json"), recursive=True))]
        self.out["world_changes"]["restored"] = ("the previous session's <run>/server copied whole and booted again "
                                                 "(reuse=True); the admin client a fresh fixture restore")

    # -- the energy verbs (research s3.7 form 1)
    def kh(self):
        """The mod's own kernels on the lupa host (tools/replay_live.py's ServerReplay, no record): requestKcal and
        maint are the tool's NR_R lines, the ones its request and maint meals call."""
        if self._kh is None:
            self._kh = RL.ServerReplay(start=None, user=USER, sleep_allowed=SLEEP_ALLOWED)
        return self._kh

    def request_kcal(self, es, hod):
        return float(self.kh().R.requestKcal(es, hod, RL.H_REQ, KCAL_PER_H))

    def maint_of(self, fm, lm):
        k = self.kh()
        return float(k.R.maint(k.table({"fm": fm, "lm": lm})))

    def to_stop(self, age, label):
        """Speed 5 until STOP_LEAD_H before the stop, then speed 1 until its age; returns the arrival snapshot."""
        a = self.age(label + "_a")
        if a is not None and a < age - STOP_LEAD_H:
            self.fast(label + "_fast")
            self.wait_age(age - STOP_LEAD_H, label + "_wait_fast")
        self.one(label + "_one")
        self.wait_age(age, label + "_wait_one")
        return self.snap(label + "_arrive")

    def body_read(self, tag):
        paths = ["body.energyState", "body.fm", "body.lm", "body.eeDay", "body.inDay", "body.exKcalDay", "fluids.na",
                 "fluids.water",
                 "fluids.naPlasma", "fluids.sweat6h"]
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

    def meal(self, kind, label, sched_age):
        """A maint or request meal: es and the hour read, the kcal by the oracles' mapping, whole portions, the
        rounding carried on."""
        st = {"label": label, "kind": kind, "sched_age": sched_age}
        self.stops.append(st)
        b = self.body_read(label + "_body")
        s = self.snap(label + "_read_t")
        age = num(s.get("worldAge"))
        st["read"] = {"es": b.get("energyState"), "fm": b.get("fm"), "lm": b.get("lm"), "eeDay": b.get("eeDay"),
                      "inDay": b.get("inDay"), "age": age, "hour": s.get("hour"), "minutes": s.get("minutes"),
                      "na": b.get("na"), "water": b.get("water"), "naPlasma": b.get("naPlasma"),
                      "sweat6h": b.get("sweat6h")}
        hod = math.fmod(age + HOUR_OFFSET, 24.0) if age is not None else None
        st["hod"] = hod
        if kind == "maint":
            if self.maint_kcal is None:
                self.maint_kcal = self.maint_of(b["fm"], b["lm"])
                self.out["readings"]["maint_kcal"] = self.maint_kcal
                self.out["readings"]["maint_body"] = {"fm": b["fm"], "lm": b["lm"], "age": age}
            target = self.maint_kcal / 3.0 + self.last_bout / 3.0     # change 5: maintenance-sized
            st["bout_add"] = self.last_bout / 3.0
        else:
            target = self.request_kcal(b["energyState"], hod)
        st["target"] = target
        st["carry_in"] = self.carry
        (a, c217, c50), tot = portions(target + self.carry)
        st["portions"] = {MIX650: a, MIX217: c217, UNIT50: c50}
        st["portion_kcal"] = tot
        items = [(MIX650, a), (MIX217, c217), (UNIT50, c50)]
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
        self.out["readings"]["carry_out"] = self.carry
        if not all(landed):
            self.note(f"meal {label}: {landed.count(False)} portion(s) did not land; the carry takes them")
        return st

    def refill(self, label, sched_age=None):
        """The canteen's refill (change 3): autodrink.probe reads the first non-empty fluid container's litres (what is
        left of the last fill; none left reads 0), then the server fluid.fill puts CANTEEN_L of Water in the canteen
        (spawning it server-side the first time). Nothing is eaten. A stop row of kind refill."""
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

    # -- the exercise verbs (changes 4 and 5)
    def exe_poll(self, tag):
        """One poll at the server: its current Fitness exercise (EXE_CHAIN; the string "nil" when none), its engine
        metabolic rate (RATE_CHAIN), the record's billed MET, S, band2Day and exKcalDay, and the world age."""
        w = self.keep(self.step(tag + "_exe", SRV, "witness.chain", f"{USER} {EXE_CHAIN}", log=False))
        rt = self.keep(self.step(tag + "_rate", SRV, "witness.chain", f"{USER} {RATE_CHAIN}", log=False))
        rec = self.lread(SRV, f"record:{USER}", [MET, "satiety.S", BAND2, EXK], tag + "_rec", log=False)
        v = rec.get("values") or {}
        val = w.get("value")
        return {"age": self.age(tag + "_a"), "wall": self.wall(), "exe": val,
                "on": isinstance(val, str) and val not in ("", "nil"), "rate": num(rt.get("value")),
                "met": num(v.get(MET)), "S": num(v.get("satiety.S")), "band2": num(v.get(BAND2)),
                "exKcal": num(v.get(EXK))}

    def run_set(self, name, minutes, label, until_age):
        """One Fitness set: exercise.do <name> <minutes> (client), then exe_poll until the server's current exercise
        reads nil after it ran, or it never showed within SET_START_CAP_M game minutes (refused), or the world age
        passes until_age. Returns the set's row."""
        st = {"label": label, "exercise": name, "requested_min": int(max(1, round(minutes)))}
        q = self.keep(self.step(label + "_do", CLI, "exercise.do", f"{name} {st['requested_min']}"))
        st["queued"] = {k: q.get(k) for k in ("ok", "queued", "queueLen", "error", "queueError", "wall")}
        st["age_queued"] = self.age(label + "_aq")
        polls, started, ended = [], False, False
        while True:
            self.check()
            p = self.exe_poll(label + "_p")
            polls.append(p)
            a = p["age"]
            if p["on"]:
                started = True
            elif started:
                ended = True
                break
            if not started and a is not None and st["age_queued"] is not None and \
                    a > st["age_queued"] + SET_START_CAP_M / 60.0:
                break
            if a is not None and a >= until_age:
                break
            time.sleep(POLL_S)
        st.update({"started": started, "ended": ended, "polls": polls, "age_end": self.age(label + "_ae")})
        if not started:
            self.note(f"set {label}: the server never showed exercise {name} (refused or not started)")
        return st

    def bout(self, label, sched_age):
        """A bout (change 5): sets of self.bout_ex inside a BOUT_MIN window from its start, each asking for the window's
        remaining minutes; a refused set rests REST_M game minutes; at most MAX_SETS. The billed bout kcal is the
        record's exKcalDay rise over the window, read at the stop (the meals' bout add-on)."""
        st = {"label": label, "kind": "bout", "sched_age": sched_age, "exercise": self.bout_ex}
        self.stops.append(st)
        b0 = self.body_read(label + "_b0")
        a0 = self.age(label + "_a0")
        st.update({"age0": a0, "ex0": b0.get("exKcalDay"), "read0": b0})
        end = (a0 if a0 is not None else sched_age) + BOUT_MIN / 60.0
        sets = []
        st["sets"] = sets
        while len(sets) < MAX_SETS:
            self.check()
            a = self.age(label + "_a")
            if a is None or (end - a) * 60.0 < SET_MIN_LEFT_M:
                break
            s = self.run_set(self.bout_ex, (end - a) * 60.0, f"{label}_s{len(sets)}", end)
            sets.append(s)
            if not s["started"]:
                a = self.age(label + "_ar")
                if a is not None and a < end:
                    self.wait_age(min(end, a + REST_M / 60.0), label + "_rest")
        a = self.age(label + "_a1")
        if a is not None and a < end:
            self.wait_age(end, label + "_tail")
        b1 = self.body_read(label + "_b1")
        st.update({"age1": self.age(label + "_a1b"), "ex1": b1.get("exKcalDay"), "read1": b1})
        if num(st["ex0"]) is not None and num(st["ex1"]) is not None and st["ex1"] >= st["ex0"]:
            st["bout_kcal"] = st["ex1"] - st["ex0"]
            self.last_bout = st["bout_kcal"]
        else:
            st["bout_kcal"] = None
            self.note(f"bout {label}: no exKcalDay rise read; the meals keep the last bout's {self.last_bout} kcal")
        self.out["readings"]["last_bout_kcal"] = self.last_bout
        return st

    def leg_idle(self, label, minutes):
        leg = {"label": label, "kind": "idle", "minutes": minutes}
        self.legs.append(leg)
        self.one(label + "_one")
        a0 = self.age(label + "_a0")
        leg["age0"] = a0
        self.wait_age(a0 + minutes / 60.0, label + "_wait")
        leg["age1"] = self.age(label + "_a1")
        return leg

    def leg_exercise(self, label, name, minutes, rest_min):
        """A gate candidate: one set of `name` asking for `minutes`, then rest_min of rest after the set's own end."""
        leg = {"label": label, "kind": "exercise", "exercise": name, "minutes": minutes, "rest_min": rest_min}
        self.legs.append(leg)
        self.one(label + "_one")
        a0 = self.age(label + "_a0")
        leg["age0"] = a0
        leg["set"] = self.run_set(name, minutes, label + "_set", a0 + (minutes + SET_START_CAP_M) / 60.0)
        a = self.age(label + "_as")
        leg["age_set_end"] = a
        self.wait_age((a if a is not None else a0) + rest_min / 60.0, label + "_rest")
        leg["age1"] = self.age(label + "_a1")
        return leg

    def leg_set_s(self, label, value, minutes):
        """The decay leg (change 3): lua.setpath of the live record's satiety.S to `value` at rest, then the ring."""
        leg = {"label": label, "kind": "setS", "value": value, "minutes": minutes}
        self.legs.append(leg)
        self.one(label + "_one")
        b = self.snap(label + "_t0")
        r = self.keep(self.step(label + "_set", SRV, "lua.setpath", f"{SET_S_PATH} {value}"))
        a = self.snap(label + "_t1")
        sp = {"label": label, "path": "satiety.S", "value": value, "ok": r.get("ok") is True, "before": r.get("before"),
              "after": r.get("after"), "err": r.get("err"), "age_before": num(b.get("worldAge")),
              "age_after": num(a.get("worldAge")), "wall_before": b.get("wall"), "wall_after": a.get("wall")}
        self.setpaths.append(sp)
        leg["setpath"] = sp
        leg["age0"] = sp["age_before"]
        if not sp["ok"]:
            self.note(f"leg {label}: lua.setpath not ok: {str(r)[:300]}")
        self.wait_age((sp["age_after"] or sp["age_before"] or 0.0) + minutes / 60.0, label + "_wait")
        leg["age1"] = self.age(label + "_a1")
        return leg

    def leg_melee(self, label, windows, rest_min):
        """The swing candidate: RCON createhorde 1 (a zombie within 10 tiles); attack.melee MELEE_SWINGS at the
        nearest zombie within 2 tiles, retried every 2 s for MELEE_FIND_S (one more createhorde past half of it); each
        window polls the server's current state (STATE_CHAIN) and the record's MET, S and band2Day while it swings,
        then waits the client's attack-melee result; a dead target takes a new horde for the next window. Then rest."""
        leg = {"label": label, "kind": "melee", "windows": [], "hordes": [], "misses": 0}
        self.legs.append(leg)
        self.one(label + "_one")
        leg["age0"] = self.age(label + "_a0")
        c = self.clients.get(USER) if isinstance(self.clients, dict) else None
        leg["hordes"].append(self.rcon(f"createhorde 1 {USER}", label + "_horde"))
        t_find = time.time()
        while len(leg["windows"]) < windows:
            self.check()
            r = self.keep(self.step(label + "_atk", CLI, "attack.melee", str(MELEE_SWINGS)))
            if not r.get("ok"):
                leg["misses"] += 1
                waited = time.time() - t_find
                if waited > MELEE_FIND_S:
                    self.note(f"leg {label}: no zombie within 2 tiles for {MELEE_FIND_S} s; {len(leg['windows'])} "
                              f"window(s) run")
                    break
                if waited > MELEE_FIND_S / 2 and len(leg["hordes"]) < 2 + len(leg["windows"]):
                    leg["hordes"].append(self.rcon(f"createhorde 1 {USER}", label + "_horde"))
                time.sleep(2.0)
                continue
            started = time.time()
            w = {"reply": {k: r.get(k) for k in ("ok", "target", "swings", "weapon", "wall")},
                 "age0": self.age(label + "_wa0"), "states": []}
            while time.time() < started + MELEE_SWINGS * 1.2 + 3.0:
                self.check()
                s = self.keep(self.step(label + "_st", SRV, "witness.chain", f"{USER} {STATE_CHAIN}", log=False))
                rec = self.lread(SRV, f"record:{USER}", [MET, "satiety.S", BAND2], label + "_rec", log=False)
                v = rec.get("values") or {}
                w["states"].append({"wall": self.wall(), "state": s.get("value"), "met": num(v.get(MET)),
                                    "S": num(v.get("satiety.S")), "band2": num(v.get(BAND2))})
                time.sleep(0.2)
            res = None
            if c is not None:
                try:
                    res = c.bus.wait_result("attack-melee", timeout=10, after=started - 1.0)
                except Exception as e:             # noqa: BLE001
                    self.note(f"leg {label}: attack-melee result: {type(e).__name__}: {e}")
            w["result"] = res
            w["age1"] = self.age(label + "_wa1")
            leg["windows"].append(w)
            if isinstance(res, dict) and res.get("targetDead") and len(leg["windows"]) < windows:
                leg["hordes"].append(self.rcon(f"createhorde 1 {USER}", label + "_horde"))
                t_find = time.time()
        a = self.age(label + "_ar")
        self.wait_age((a if a is not None else leg["age0"]) + rest_min / 60.0, label + "_rest")
        leg["age1"] = self.age(label + "_a1")
        return leg

    def run_gate(self, legs):
        """The gate's legs in order: ("idle", label, minutes), ("exercise", label, name, minutes, rest_min),
        ("setS", label, value, minutes), ("melee", label, windows, rest_min), ("meal", label, fullType); all at speed
        1. A meal is spawned and eaten (eat_all)."""
        X = self.out["phases"].setdefault("X", {})
        X["start_age"] = self.age("X_a0")
        X["missed"], X["late"], X["refills_skipped"] = [], [], []
        self.one("X_one")
        for leg in legs:
            self.check()
            kind = leg[0]
            if kind == "idle":
                self.leg_idle(leg[1], leg[2])
            elif kind == "exercise":
                self.leg_exercise(leg[1], leg[2], leg[3], leg[4])
            elif kind == "setS":
                self.leg_set_s(leg[1], leg[2], leg[3])
            elif kind == "melee":
                self.leg_melee(leg[1], leg[2], leg[3])
            elif kind == "meal":
                st = {"label": leg[1], "kind": "gate_meal"}
                self.stops.append(st)
                landed, labs = self.eat_all([(leg[2], 1)], leg[1])
                st["eats"], st["landed"] = labs, landed
                st["age"] = self.age(leg[1] + "_t")
            self.persist()
        X["end_age"] = self.age("X_end")
        X["done"] = True

    def run_schedule(self):
        """The chain's stops from this session's age to end_age, then speed 5 to end_age. A refill first, at once (the
        canteen as the attach left it). A meal stop already past by under LATE_MAX_H is done at once (late, named), an
        older one is missed (named, a deviation; a bout counts as a meal); a refill stop already past is skipped (named, not a deviation: the
        first refill covers it). Each meal is followed by a refill. Refill stops run at speed 5 (no clock-sensitive
        reading)."""
        X = self.out["phases"].setdefault("X", {})
        a0 = self.age("X_a0")
        X["start_age"] = a0
        X["end_age"] = self.end_age
        prev = set(g(self.out, "chain", "prev_stops") or [])
        lo = num(g(self.prev_doc, "chain", "end_age")) if self.prev_doc is not None else None
        X["from_age"] = lo
        todo, missed, late, skipped = [], [], [], []
        for age, kind, label in SCHEDULE:
            if age >= self.end_age or label in prev or (lo is not None and age < lo):
                continue
            if a0 is not None and age < a0:
                if kind == "refill":
                    skipped.append(label)
                elif a0 - age < LATE_MAX_H and kind != "bout":
                    late.append(label)
                    todo.append((age, kind, label))
                else:
                    missed.append(label)
                continue
            todo.append((age, kind, label))
        X["late"], X["missed"], X["refills_skipped"] = late, missed, skipped
        if missed:
            self.out["deviations"].append(f"stops missed before this session's start: {missed}")
        if late:
            self.out["deviations"].append(f"stops done late at this session's start: {late}")
        self.refill("X_refill0", a0)
        self.persist()
        for age, kind, label in todo:
            self.check()
            if kind in ("maint", "request"):
                self.to_stop(age, label)
                self.meal(kind, label, age)
                self.refill(label + "_R", age)
            elif kind == "bout":
                self.to_stop(age, label)
                self.bout(label, age)
                self.refill(label + "_R", age)
            elif kind == "refill":
                a = self.age(label + "_a")
                if a is not None and a < age:
                    self.fast(label + "_fast")
                    self.wait_age(age, label + "_wait_fast")
                self.refill(label, age)
            self.persist()
        self.check()
        a = self.age("X_tail_a")
        if a is not None and a < self.end_age:
            self.fast("X_tail_fast")
            self.wait_age(self.end_age, "X_tail_wait")
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
        P["autodrink"] = self.keep(self.step("S_autodrink", SRV, "autodrink.set", f"{USER} true"))   # change 3

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
    def ring_files(self, prefix=""):
        R = (g(self.out, "phases", "R", "pages") or []) + (g(self.out, "phases", "D", "tail") or [])
        return [p.get("file") for p in R if p.get("file")]

    def replay(self, files, window=None, tag="replay", write=True):
        """replay_live over the ring pages `files` from W's start record with the events built from the logs;
        window (a0, a1): the diff restricted to replay rows whose age lies in it. Returns a dict."""
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
        # the first ring row after the start record reads the record's own state: an autoDrop it shows is pending IN
        # the start record (fluids.autoDrop is a stored input, NR_Kernel_Store.lua INPUTS), which the replay's first
        # drain lands, so its event would land it twice: those events are held back, named
        srec = start.get("rec", start) if isinstance(start, dict) else {}
        sa = num(g(srec, "satiety", "t"))
        if sa is None:
            sa = num(srec.get("kineticsAge")) if isinstance(srec, dict) else None
        first = next((r for r in rows if num(r.get("age")) is not None and (sa is None or r["age"] > sa + 1e-9)), None)
        held = [e for e in drops if first is not None and e["s"] <= first["s"]]
        drops = [e for e in drops if first is None or e["s"] > first["s"]]
        acts, unknown = activity_events(rows)                       # change 2
        held_act = [e for e in acts if first is not None and e["s"] <= first["s"]]
        acts = [e for e in acts if first is None or e["s"] > first["s"]]
        sets, sp_notes = setpath_events(rows, self.setpaths)       # change 3
        events = sorted(events0 + drops + acts + sets, key=lambda e: e["s"])
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
        RP["activity"] = {"n": len(acts), "held_in_start": held_act, "unknown_met": unknown}
        RP["setpaths"] = {"events": sets, "notes": sp_notes}
        RP["autodrops"] = {"n": len(drops), "water_g": sum(e["vec"]["water"] for e in drops),
                           "held_in_start": held, "first_ring_s_after_start": first["s"] if first else None}
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
        use = rows_out
        if window is not None:
            use = [r for r in rows_out if num(r.get("age")) is not None and window[0] - 1e-9 <= r["age"] <= window[1] + 1e-9]
            RP["window"] = list(window)
            RP["window_rows"] = len(use)
        d = RL.diff(use, rr)
        dx = RL.diff(use, rr, TOL_EXTRA)
        if write:
            doc = {"mode": "live", "offset": be.R.offset, "rows": rows_out, "diff": RL.diff(rows_out, rr),
                   "eats": be.eats, "diff_extra": RL.diff(rows_out, rr, TOL_EXTRA),
                   "dropped": getattr(be, "dropped", None), "events": events}
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
        if self.prev_run is not None:
            try:
                self.chain_pre()
            except Exception as e:                 # noqa: BLE001 - no boot without the previous session's state
                self.out["error"] = f"chain PRE failed, not booted: {type(e).__name__}: {e}"
                self.out["chain"]["traceback"] = traceback.format_exc()[-3000:]
                self.persist()
                print(self.out["error"])
                sys.exit(1)
        try:
            self.server = make_server(self.run_dir, self.rec_fx, mods=self.prof.mods, mod_sources=self.prof.sources,
                                      mod_skip=self.prof.skip, sandbox=self.prof.sandbox or None, ini=self.prof.ini,
                                      reuse=self.prev_run is not None)
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
                          "replay_error": g(self.out, "replay", "error"), "budget_stop": self.out.get("budget_stop"),
                          "error": self.out.get("error"), "body_error": self.out.get("body_error"),
                          "phase_errors": {k: v.get("error") for k, v in self.out.get("phase_errors", {}).items()},
                          "wall_seconds": self.out.get("wall_seconds"), "run_id": self.run_id,
                          "run_dir": self.run_dir}, indent=1, default=str)[:8000])
