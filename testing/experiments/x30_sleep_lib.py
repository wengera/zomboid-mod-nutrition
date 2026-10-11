"""x30_sleep_lib -- the session engine of the Plan 11f Task 7 drivers (x301, x302): research row 11 (sleep debt raises
hunger) live, on ONE live body over a chain of two sessions, with SleepAllowed and SleepNeeded true (profile x30-sleep;
#2947, #2948: with either false the sleep state freezes and the factor is inert, #2961). It is x28_steady_lib.py (Plan
11f Task 5r, frozen with x281's run) copied, not imported, with these changes:
  1. the server's sleep option: SLEEP_ALLOWED True; the replay is told --sleep-allowed true (the option the mod reads
     once at OnServerStarted, NUT.readSleepOptions, NR_Server_Nutrients.lua:127-143); phase S reads the mod's own
     NutritionRevamp.server.nutrients.sleepDisabled (must read false) and the admin's traits (stats.get: the sleep-need
     factor reads NEEDS_MORE_SLEEP / NEEDS_LESS_SLEEP, NR_Server_Nutrients.lua:149-162);
  2. the calendar (schedule): day 0 the fixture's first day (world age 0 is 07:00, #2890; at(d, h) = 24 d - 7 + h);
     maint meals at 13:00 and 20:00 on day 0; request-level meals at 08:00, 13:00 and 20:00 on days 1-4 (research s3.7
     form 1; the meal is sized by es and the hour only, never by the sleep factor); four nights: N0 rested (7.5 h, from
     21:45 day 0), N1 short (5.5 h, from 00:15 day 2), N2 recovery (9.5 h, from 20:30 day 2), N3 rested (7.5 h, from
     21:45 day 3); canteen refills at 10:30 and 16:30, after every meal and after every night (none inside a night);
  3. THE NIGHT (Session.night): at speed 1, player.sleep.hold <user> 600 holds the only player asleep (the world
     fast-forwards about 20x, #2956); the record's booked window sleep acute.winSleptH is polled through lua.read until
     the minutes booked since the night's start, plus the booking rate times the last poll's round trip, reach the
     night's target; then the hold is cancelled (player.sleep.hold <user> 0) and the flag cleared (player.sleep <user>
     false). THE NIGHT'S LENGTH IS ITS BOOKED SLEEP, NOT ITS HELD SPAN (a design choice, named): about 15 % of held
     minutes run awake (#2840, #3076), so a held 7.5 h would book about 6.4 h and the rested baseline would carry a
     debt; the oracles' nights are asleep minutes (test_satiety_meal_studies.py acute_night). The held span, the booked
     sleep and their ratio are logged per night. A night also stops at its cap age (the next meal plus 45 game
     minutes; that meal then runs late) or a wall cap, named. Before the hold the night's placement is read off acute.winStartH: the night must lie
     inside one 24 h window (the debt books at the window's close, #3638; the window's phase is the record's creation),
     a placement outside is a deviation, named;
  4. THE REPLAY'S SLEEP EVENTS ARE READ OFF THE RING (the class of ruling T5R-1's autoDrop drinks; named): the drain
     reads the server's isAsleep (NR_Server_Nutrients.lua:455, NR_Server_Metabolism.lua:188, NR_Server_Writer.lua:251)
     and the harness cannot sample it at the drain's tick (the hold's flag flickers, #2840), so the replay is told what
     the drain booked: acute.sleptH, the unbroken asleep run, is 0 after an awake drain and grows by the drain's dtH
     after an asleep one (K.acute.sleepMinute). Ring row k reads the state drain k-1 left, so drain k ran asleep when
     ring row k+1 reads acute.sleptH > 0, and the event {s: row k, sleep, asleep} is due before drain k
     (sleep_events; emitted where the state changes, from the stand-in's awake default). body.met (Sleeping bills
     COMPENDIUM.Sleeping 1.0) is a cross-check, counted;
  5. the ring (31 paths, the harness takes 32): + acute.sleptH, acute.winSleptH, acute.winStartH, acute.awakeH,
     acute.boutH, acute.S; - stomach.buffer.calories, stomach.buffer.water, lastIntake.litres, fluids.k; the
     rows also carry the harness's rate, exe and moving (3daaca9, ce56020f), from which the tool takes the activity
     (the sleep scenario is sedentary: exe must stay false, a guard);
  6. the per-session readings: per night its placement, held span, booked sleep, ratio, polls and the fast-forward
     rate; per window close on the ring the booked sleep, the debt before and after, the kernel's own booking of it
     (K.acute.SLEEP_NEED_H, REPAY, DEBT_MAX) and the replay's debt; the exe guard; the drinking and sodium guard as x28.
Kept from x28: the auto-drink to thirst from a server canteen (ruling T5R-1) and its autoDrop drink events, the sodium
guard, F-T5-2's run_phase fix, the request-meal sizing (NR_R.requestKcal), the phases (boot, S, H, W, X, R, D, Z), the
slot files, the replay of live and the artifact copy.

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run (x301), this file is never edited (CLAUDE.md
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
RING_RECORD = ("satiety.P", "satiety.S", "satiety.L", "satiety.t", "body.energyState", "body.met", "acute.debtH",
               "acute.sleptH", "acute.winSleptH", "acute.winStartH", "acute.awakeH", "acute.boutH", "acute.S",
               "stomachFill", "stomach.liquid", "body.inDay", "kineticsAge", "body.eeDay", "body.fm", "body.lm",
               "fluids.water", "fluids.na", "fluids.naPlasma", "fluids.sweat6h", "fluids.autoDrop", "fluids.thirstTarget")
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
SLEEP_ALLOWED = True       # the live server: SleepAllowed and SleepNeeded true (profile x30-sleep; change 1)
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
SLEPT = "acute.sleptH"
WIN_SLEPT = "acute.winSleptH"
WIN_START = "acute.winStartH"
DEBT = "acute.debtH"
MET = "body.met"
SLEEP_DISABLED = NR + ".server.nutrients.sleepDisabled"   # NUT.sleepDisabled (NR_Server_Nutrients.lua:127-143)
HOLD_S = 600               # player.sleep.hold's wall window, its maximum (PZTestKit_Server.lua player.sleep.hold)
NIGHT_WALL_CAP_S = 150.0   # a night still holding after this many wall seconds is stopped, named (about 20x: 9.5 h ~ 25 s)
NIGHT_CAP_LATE_H = 0.75    # a night stops by its cap age: the next meal stop plus this (that meal then runs late, named)
ASLEEP_FRACTION = 0.80     # the planning share of held minutes booked asleep (#2840: about 0.85); the placement check's
                           # predicted wake is the night's start plus target / ASLEEP_FRACTION
WAKE_SETTLE_S = 20.0       # after the cancel, wait until the booked sleep stops growing (two reads one game minute apart)
NEED_H = 7.5               # K.acute.SLEEP_NEED_H (read off the kernel at grade; this is the planning copy)
NIGHT_TOL_H = 0.25         # a night's booked sleep within this of its target is a night as planned (NIGHTS)


def at(d, h):
    """The world age of clock hour h on chain day d (day 0 the fixture's first day: midnight before day d is 24 d - 7)."""
    return 24.0 * d - 7.0 + h


NIGHTS = (("N0", 0, 21.75, 7.5, "rested"), ("N1", 2, 0.25, 5.5, "short"), ("N2", 2, 20.5, 9.5, "recovery"),
          ("N3", 3, 21.75, 7.5, "rested_after"))   # (label, day, clock hour of the hold, booked target h, role)


def schedule():
    """The chain's fixed stops [(age, kind, label, extra)], in age order (research row 11; the Task 7 amendments):
      day 0 (the fixture's first day, from the boot at about 11:00): maint meals at 13:00 and 20:00;
      days 1-4: request meals at 08:00, 13:00 and 20:00 (research s3.7 form 1; the oracles' FAST_MEAL_H), day 4 to 13:00;
      nights (NIGHTS): N0 rested 7.5 h from 21:45 day 0, N1 short 5.5 h from 00:15 day 2, N2 recovery 9.5 h from 20:30
      day 2, N3 rested 7.5 h from 21:45 day 3 (booked hours; change 3), extra the night's target and role;
      refill stops (the canteen back to CANTEEN_L, nothing eaten) at 10:30 and 16:30 on days 0-4; every meal and every
      night is followed by a refill too."""
    out = []
    for h in (13.0, 20.0):
        out.append((at(0, h), "maint", "D0_%02d" % h, None))
    for d in (1, 2, 3, 4):
        for h in (8.0, 13.0, 20.0):
            if d == 4 and h > 13.0:
                continue
            out.append((at(d, h), "request", "D%d_%02d" % (d, h), None))
    for label, d, h, target, role in NIGHTS:
        out.append((at(d, h), "night", label, {"target_h": target, "role": role}))
    for d in range(0, 5):
        for h in (10.5, 16.5):
            hhmm = "%02d%02d" % (int(h), int(round((h % 1) * 60)))
            out.append((at(d, h), "refill", "R%d_%s" % (d, hhmm), None))
    out.sort(key=lambda x: x[0])
    return out


SCHEDULE = schedule()


def next_meal_age(age):
    """The age of the first meal stop after age (None if none): a night's cap is this plus NIGHT_CAP_LATE_H."""
    for a, kind, _label, _x in SCHEDULE:
        if kind in ("maint", "request") and a > age + 1e-9:
            return a
    return None


def sleep_events(rows):
    """The replay's sleep events from the ring (change 4): drain k ran asleep when ring row k+1 reads acute.sleptH > 0
    (sleepMinute zeroes the run on an awake drain and adds the drain's dtH on an asleep one); the event {s: row k,
    sleep, asleep} is due before drain k, emitted where the state changes from the last (the stand-in starts awake).
    Offline rows (on false) are skipped: no drain runs for them. A dtH 0 asleep drain after an awake one reads 0 and is
    read awake (it books nothing). Returns the events."""
    on = [r for r in rows if r.get("on") is not False and r.get("s") is not None and num(r.get("age")) is not None]
    out = []
    last = False
    for r, nxt in zip(on, on[1:]):
        v = num(nxt.get(SLEPT))
        if v is None:
            continue
        asleep = v > 0
        if asleep != last:
            out.append({"s": r["s"], "kind": "sleep", "asleep": asleep, "label": "ring-sleep", "age": r.get("age")})
            last = asleep
    return out


def window_closes(rows):
    """The 24 h window closes on the ring: every row whose acute.winStartH rose over the row before (the drain between
    them closed one or more windows). Per close: the rows' s and ages, the window's booked sleep (the row before's
    acute.winSleptH: the closing drain is awake when the night lies inside its window), the debt before and after, and
    the kernel's own booking of it, clamp(debt + max(0, need - booked) - REPAY x max(0, booked - need), 0, DEBT_MAX),
    on the mod's K.acute constants."""
    K = _kh_static().K
    need, repay, cap = float(K.acute.SLEEP_NEED_H), float(K.acute.REPAY), float(K.acute.DEBT_MAX)
    on = [r for r in rows if num(r.get("age")) is not None]
    out = []
    for p, r in zip(on, on[1:]):
        w0, w1 = num(p.get(WIN_START)), num(r.get(WIN_START))
        if w0 is None or w1 is None or w1 <= w0 + 1e-9:
            continue
        booked = num(p.get(WIN_SLEPT))
        d0, d1 = num(p.get(DEBT)), num(r.get(DEBT))
        pred = None
        if booked is not None and d0 is not None:
            pred = min(max(d0 + max(0.0, need - booked) - repay * max(0.0, booked - need), 0.0), cap)
        out.append({"s_before": p.get("s"), "s_after": r.get("s"), "age_before": p["age"], "age_after": r["age"],
                    "win_start_before": w0, "win_start_after": w1, "windows": int(round((w1 - w0) / 24.0)),
                    "booked_h": booked, "debt_before": d0, "debt_after": d1, "debt_kernel": pred,
                    "kernel_diff": (d1 - pred) if (d1 is not None and pred is not None) else None,
                    "win_slept_after": num(r.get(WIN_SLEPT))})
    return out


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
    """The session's energy readings (each also re-derivable from the committed ring and events by x30_grade.py):
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


def guard_reading(ring):
    """The sedentary guard over the ring: rows whose harness exe (the server's exercise flag) reads true, rows whose
    moving reads true, and the cross-check of the sleep events against the billed MET (an asleep drain bills
    COMPENDIUM.Sleeping 1.0: the rows after an asleep drain whose body.met is not 1.0, and the rows after an awake drain
    that bill 1.0)."""
    on = [r for r in ring if num(r.get("age")) is not None]
    exe = [r["s"] for r in on if r.get("exe") is True]
    mv = [r["s"] for r in on if r.get("moving") is True]
    asleep_not_10, awake_10 = 0, 0
    for nxt in on[1:]:
        v, m = num(nxt.get(SLEPT)), num(nxt.get(MET))
        if v is None or m is None:
            continue
        if v > 0 and abs(m - 1.0) > 1e-9:
            asleep_not_10 += 1
        if v <= 0 and abs(m - 1.0) <= 1e-9:
            awake_10 += 1
    return {"rows": len(on), "exe_true_rows": len(exe), "exe_true_s": exe[:20], "moving_true_rows": len(mv),
            "moving_true_s": mv[:20], "exe_present_rows": sum(1 for r in on if "exe" in r),
            "met_check": {"asleep_rows_not_billed_sleeping": asleep_not_10, "awake_rows_billed_1_0": awake_10}}


def night_summary(st):
    """A night stop's readings: the placement, the target, the booked sleep, the held span, their ratio, the miss, the
    cancel's reason, the polls' count and round trip, the wall seconds of the hold and the fast-forward rate (game hours
    held per wall second of the hold)."""
    took = [p["took"] for p in st.get("polls") or [] if p.get("took") is not None]
    ws = g(st, "cancel", "wall_since_hold")
    return {"label": st.get("label"), "role": st.get("role"), "target_h": st.get("target_h"), "age0": st.get("age0"),
            "age1": st.get("age1"), "booked_h": st.get("booked_h"), "held_h": st.get("held_h"),
            "booked_over_held": st.get("booked_over_held"), "miss_h": st.get("miss_h"),
            "reason": g(st, "cancel", "reason"), "placement": st.get("placement"), "poll_n": st.get("poll_n"),
            "took_mean": (sum(took) / len(took)) if took else None, "wall_since_hold": ws,
            "debt_before": g(st, "before", "debtH"), "debt_after": g(st, "after", "debtH"),
            "game_h_per_wall_s": (st["held_h"] / ws) if (st.get("held_h") and ws) else None}


def session_grade(S, ring, rows_rep, pred):
    """The per-session readings and verdicts every x30 driver grades: energy_readings; the drinking and the sodium
    guard per chain day (fluid_days over the ring's autoDrop rows); the refills' container side; the nights; the window
    closes on the ring against the kernel's own booking and the replay's debt; the sedentary guard; STOPS (every
    scheduled meal and night of this session's span done, every eat landed; a refill stop before the session's start is
    skipped, named); SLEEP_ON (the mod read the server's sleep option as enabled); NIGHTS (each night stopped at its
    target, inside one window, booked within NIGHT_TOL_H of its target); CLOSES (each close's debt equals the kernel's
    booking within 1e-6, and the replay's within 1e-6); EXE (no exe true row)."""
    energy_readings(S, ring, rows_rep)
    R = S.out["readings"]
    R["fluid_days"] = fluid_days(ring, autodrop_events(ring))     # every ring row's autoDrop (the replay holds some back)
    R["refills"] = [{"label": st["label"], "age": st.get("age"), "left_l": st.get("left_l"), "filled_l": st.get("filled_l"),
                     "fill_ok": st.get("fill_ok")} for st in S.stops if st.get("kind") == "refill" or st.get("refill")]
    nights = [night_summary(st) for st in S.stops if st.get("kind") == "night"]
    R["nights"] = nights
    closes = window_closes(ring)
    rep_by = {r["s"]: r for r in rows_rep}
    for c in closes:
        rp = rep_by.get(c["s_after"])
        c["debt_replay"] = num(rp.get(DEBT)) if rp else None
        c["replay_diff"] = (c["debt_after"] - c["debt_replay"]) if (c["debt_after"] is not None and
                                                                    c["debt_replay"] is not None) else None
    R["closes"] = closes
    R["guard"] = guard_reading(ring)
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
    sd = g(S.out, "phases", "S", "sleep_disabled", "value")
    S.out["verdicts"]["SLEEP_ON"] = {"predicted": pred.get("SLEEP_ON"), "observed": {"sleepDisabled": sd},
                                     "verdict": "as_predicted" if sd is False else "falsified"}
    okn = [n for n in nights if n["reason"] == "target" and g(n, "placement", "inside_one_window")
           and n["miss_h"] is not None and abs(n["miss_h"]) <= NIGHT_TOL_H]
    S.out["verdicts"]["NIGHTS"] = {
        "predicted": pred.get("NIGHTS"),
        "observed": {n["label"]: {k: n[k] for k in ("target_h", "booked_h", "held_h", "booked_over_held", "reason")}
                     for n in nights},
        "verdict": "as_predicted" if nights and len(okn) == len(nights) else "falsified"}
    okc = [c for c in closes if c["kernel_diff"] is not None and abs(c["kernel_diff"]) <= 1e-6
           and c["replay_diff"] is not None and abs(c["replay_diff"]) <= 1e-6]
    S.out["verdicts"]["CLOSES"] = {
        "predicted": pred.get("CLOSES"),
        "observed": [{k: c[k] for k in ("age_after", "booked_h", "debt_before", "debt_after", "debt_kernel",
                                        "debt_replay")} for c in closes],
        "verdict": "as_predicted" if closes and len(okc) == len(closes) else "falsified"}
    S.out["verdicts"]["EXE"] = {"predicted": pred.get("EXE"), "observed": R["guard"],
                                "verdict": "as_predicted" if (R["guard"]["exe_true_rows"] == 0
                                                              and R["guard"]["exe_present_rows"] > 0) else "falsified"}


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
                 driver_file, scenario, grade_fn=None, extra_meta=None, prev_run=None, prev_prefix=None, end_age=None):
        self.prev_run, self.prev_prefix, self.end_age = prev_run, prev_prefix, end_age
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
            "run_id": self.run_id, "session": session_text, "driver": driver_file, "lib": "x30_sleep_lib.py",
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
            "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/x30_sleep_lib.py"),
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
            "stops": self.stops, "chain": {"prev_run": prev_run, "prev_prefix": prev_prefix, "end_age": end_age},
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
                         if f.endswith(".json") and f.startswith("sleep-")), None)
        if doc_path is None:
            raise RuntimeError(f"no sleep-*.json artifact in {prev}")
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
        C.update({"prev_run_id": pid, "prev_artifact": os.path.basename(doc_path), "carry_in": self.carry,
                  "maint_kcal_in": self.maint_kcal, "prev_last_ring_age": R.get("last_ring_age"),
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
        paths = ["body.energyState", "body.fm", "body.lm", "body.eeDay", "body.inDay", "fluids.na", "fluids.water",
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
            target = self.maint_kcal / 3.0
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

    def acute_read(self, tag, log=True):
        """The record's sleep state in one read (lua.read record:<user>); satiety.t is the last drain's age."""
        paths = [WIN_SLEPT, WIN_START, SLEPT, DEBT, "acute.awakeH", "acute.boutH", "acute.S", "satiety.t"]
        a = self.lread(SRV, f"record:{USER}", paths, tag, log=log)
        v = a.get("values") or {}
        out = {k.split(".", 1)[1]: num(v.get(k)) for k in paths}
        out["wall"], out["wall_after"] = a.get("wall"), a.get("wall_after")
        return out

    def night(self, label, sched_age, extra):
        """One night (change 3): at speed 1, the placement read off acute.winStartH, the hold, the booked sleep polled
        until it (plus the booking rate times the last round trip) reaches the target, the cancel and the flag cleared,
        then the settle (the booked sleep stops growing). A stop row of kind night."""
        target = float(extra["target_h"])
        st = {"label": label, "kind": "night", "sched_age": sched_age, "role": extra.get("role"), "target_h": target}
        self.stops.append(st)
        self.one(label + "_one")
        a0 = self.acute_read(label + "_a0")
        t0 = self.snap(label + "_t0")
        age0 = num(t0.get("worldAge"))
        st["before"], st["age0"] = a0, age0
        nxt = next_meal_age(age0 if age0 is not None else sched_age)
        cap_age = (nxt + NIGHT_CAP_LATE_H) if nxt is not None else None
        st["cap_age"] = cap_age
        ws, w0 = a0.get("winStartH"), a0.get("winSleptH")
        wake = (age0 + target / ASLEEP_FRACTION) if age0 is not None else None
        inside = (ws is not None and wake is not None and age0 > ws and wake < ws + 24.0)
        st["placement"] = {"win_start": ws, "win_end": (ws + 24.0) if ws is not None else None,
                           "predicted_wake_age": wake, "inside_one_window": inside}
        if not inside:
            self.out["deviations"].append(f"night {label}: the predicted night ({age0} to {wake}) is not inside one "
                                          f"window ({ws} + 24 h)")
        h = self.keep(self.step(label + "_hold", SRV, "player.sleep.hold", f"{USER} {HOLD_S}"))
        st["hold"] = {k: h.get(k) for k in ("armed", "before", "after", "error", "wall")}
        wall_hold = self.wall()
        polls, reason = [], None
        prev = None
        rate = None
        budget = None
        while True:
            try:
                self.check()
            except Budget as e:                    # the hold is always cancelled before the budget stop goes on
                budget, reason = e, "budget"
                break
            r = self.step(label + "_poll", SRV, "lua.read", f"record:{USER} {WIN_SLEPT} {WIN_START} satiety.t", log=False)
            ack = r.get("ack") if isinstance(r.get("ack"), dict) else {}
            v = ack.get("values") or {}
            ws1, w1, t1 = num(v.get(WIN_START)), num(v.get(WIN_SLEPT)), num(v.get("satiety.t"))
            mid = (r["wall_before"] + r["wall_after"]) / 2.0
            booked = (w1 - w0) if (w1 is not None and w0 is not None) else None
            if prev is not None and booked is not None and mid > prev[0]:
                inst = (booked - prev[1]) / (mid - prev[0])
                rate = inst if rate is None else 0.5 * rate + 0.5 * inst
            polls.append({"wall": round(mid, 3), "took": r["took"], "booked": booked, "drain_age": t1,
                          "win_start": ws1, "rate": rate})
            if booked is not None:
                prev = (mid, booked)
            if ws1 is not None and ws is not None and ws1 > ws + 1e-9:
                reason = "window_closed"
                break
            lead = (rate or 0.0) * r["took"]
            if booked is not None and booked + lead >= target:
                reason = "target"
                break
            if cap_age is not None and t1 is not None and t1 >= cap_age:
                reason = "cap_age"
                break
            if self.wall() - wall_hold > NIGHT_WALL_CAP_S:
                reason = "wall_cap"
                break
        c = self.keep(self.step(label + "_cancel", SRV, "player.sleep.hold", f"{USER} 0"))
        w = self.keep(self.step(label + "_wake", SRV, "player.sleep", f"{USER} false"))
        st["cancel"] = {"reason": reason, "hold_reply": {k: c.get(k) for k in ("before", "after", "wall")},
                        "wake_reply": {k: w.get(k) for k in ("before", "after", "held", "wall")},
                        "wall_since_hold": round(self.wall() - wall_hold, 3)}
        if reason != "target":
            self.out["deviations"].append(f"night {label}: stopped by {reason}, not its target")
        if budget is not None:
            raise budget
        end = time.time() + WAKE_SETTLE_S
        last = None
        settle = []
        while time.time() < end:
            x = self.acute_read(label + "_settle", log=False)
            settle.append({k: x.get(k) for k in ("winSleptH", "sleptH", "t", "wall")})
            if last is not None and x.get("winSleptH") == last.get("winSleptH") and x.get("t") is not None \
                    and last.get("t") is not None and x["t"] - last["t"] >= 1.0 / 60:
                break
            if last is None or x.get("winSleptH") != last.get("winSleptH"):
                last = x
            time.sleep(POLL_S)
        a1 = self.acute_read(label + "_a1")
        t1 = self.snap(label + "_t1")
        st["after"], st["age1"] = a1, num(t1.get("worldAge"))
        st["settle"] = settle
        st["polls"] = polls
        st["poll_n"] = len(polls)
        st["booked_h"] = (a1["winSleptH"] - w0) if (a1.get("winSleptH") is not None and w0 is not None) else None
        st["held_h"] = (st["age1"] - age0) if (st["age1"] is not None and age0 is not None) else None
        if st["booked_h"] is not None and st["held_h"]:
            st["booked_over_held"] = st["booked_h"] / st["held_h"]
        st["miss_h"] = (st["booked_h"] - target) if st["booked_h"] is not None else None
        self.mark(label + "_woke", booked_h=st["booked_h"], held_h=st["held_h"], reason=reason)
        return st

    def run_schedule(self):
        """The chain's stops from this session's age to end_age, then speed 5 to end_age. A refill first, at once (the
        canteen as the attach left it). A meal stop already past by under LATE_MAX_H is done at once (late, named), an
        older one is missed (named, a deviation); a night already past is missed (a deviation); a refill stop already
        past is skipped (named, not a deviation: the first refill covers it). Each meal and each night is followed by a
        refill. Refill stops run at speed 5 (no clock-sensitive reading)."""
        X = self.out["phases"].setdefault("X", {})
        a0 = self.age("X_a0")
        X["start_age"] = a0
        X["end_age"] = self.end_age
        prev = set(g(self.out, "chain", "prev_stops") or [])
        lo = num(g(self.prev_doc, "chain", "end_age")) if self.prev_doc is not None else None
        X["from_age"] = lo
        todo, missed, late, skipped = [], [], [], []
        for age, kind, label, extra in SCHEDULE:
            if age >= self.end_age or label in prev or (lo is not None and age < lo):
                continue
            if a0 is not None and age < a0:
                if kind == "refill":
                    skipped.append(label)
                elif kind != "night" and a0 - age < LATE_MAX_H:
                    late.append(label)
                    todo.append((age, kind, label, extra))
                else:
                    missed.append(label)
                continue
            todo.append((age, kind, label, extra))
        X["late"], X["missed"], X["refills_skipped"] = late, missed, skipped
        if missed:
            self.out["deviations"].append(f"stops missed before this session's start: {missed}")
        if late:
            self.out["deviations"].append(f"stops done late at this session's start: {late}")
        self.refill("X_refill0", a0)
        self.persist()
        for age, kind, label, extra in todo:
            self.check()
            if kind in ("maint", "request"):
                self.to_stop(age, label)
                self.meal(kind, label, age)
                self.refill(label + "_R", age)
            elif kind == "night":
                self.to_stop(age, label)
                self.night(label, age, extra)
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
        P["autodrink"] = self.keep(self.step("S_autodrink", SRV, "autodrink.set", f"{USER} true"))   # x28's change 3
        P["sleep_disabled"] = self.gread(SLEEP_DISABLED, "S_sleep_disabled")                        # change 1
        b = self.keep(self.step("S_body", SRV, "stats.get", USER))
        P["body"] = {k: b.get(k) for k in ("traits", "traitList", "asleep", "fatigue", "weight", "worldAge", "wall")}

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
        sleeps = sleep_events(rows)                        # change 4: the drains' booked asleep state, off the ring
        sleeps = [e for e in sleeps if first is None or e["s"] >= first["s"]]
        events = sorted(events0 + drops + sleeps, key=lambda e: e["s"])
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
                                   "--player player.json --sleep-allowed true --out replay.json")
        rr, rpaths = RL.load_ring([os.path.join(self.run_dir, f) for f in files])
        t_r = time.time()
        RP["autodrops"] = {"n": len(drops), "water_g": sum(e["vec"]["water"] for e in drops),
                           "held_in_start": held, "first_ring_s_after_start": first["s"] if first else None}
        RP["sleep_events"] = {"n": len(sleeps), "asleep_n": sum(1 for e in sleeps if e["asleep"])}
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
