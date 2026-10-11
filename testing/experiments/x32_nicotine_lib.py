"""x32_nicotine_lib -- the session engine of the Plan 11f Task 8 drivers (x321, x322, x323): research row 12 (nicotine
withdrawal raises hunger) live, on ONE live body over a chain of three sessions, sleep off (profile x32-nicotine: the
fixture's SleepAllowed and SleepNeeded false; no drain runs asleep, and vanilla's withdrawal rise skips a sleeping
player, #3630).

It is x31_nicotine_lib.py (frozen with x311's run, whose gate was falsified) copied, not imported, under ruling T8-1,
with two changes:
  a. THE TRAIT KEY: trait.set takes the CharacterTrait static field name (PZTestKit_Server.lua:287-291: field =
     TRAIT_FIELDS[name] or name, then CharacterTrait[field]); the jar registers 'Smoker' into the static field SMOKER
     (CharacterTrait.<clinit> @661-@667 L85), so SMOKER is "SMOKER" (x311 sent "Smoker": no CharacterTrait.Smoker, the
     admin stayed a non-smoker and the gate smoke raised FoodSickness instead, F-T8-1);
  b. A HARD STOP IN PHASE S: after trait.set and trait.push (the first session) or at every later session's start, the
     trait list is read back (stats.get); without Smoker in it the session sets `abort` and runs no further scenario
     phase (H, W, X skipped; R, D, Z still run), named.
Accepted under ruling T8-1 and named here: the three-session chain at DayLength 1 (the rise to the cap is about 50.9
game hours after a smoke, four times the 60-minute day's 12.7, F-T8-3) and the order of the cap's stops (the fade
edit, then T2-F, then the second smoke, change 6 below).

x31_nicotine_lib.py was itself x30_sleep_lib.py (Plan 11f Task 7, frozen with x301's run) copied, not imported, with
these changes:
  1. sleep off: SLEEP_ALLOWED False (the replay takes --sleep-allowed false); the nights, the window closes and the
     ring's sleep events are gone; phase S reads the mod's own NutritionRevamp.server.nutrients.sleepDisabled (must
     read true) and acute.sleptH stays on the ring as a guard (no row after an asleep drain);
  2. THE SMOKER: phase S of the chain's first session adds the Smoker trait on the server (trait.set admin Smoker add)
     and pushes it (trait.push admin); every session reads the trait list (stats.get) and the server's time since the
     last smoke (witness.fields player admin getTimeSinceLastSmoke, the getter #3637 names);
  3. THE SMOKE (Session.smoke): a lighter (Base.Lighter) and one Base.CigaretteSingle spawned by RCON additem (seen on
     the client), foodtimer 0, eat.action Base.CigaretteSingle 1 (the real ISEatFoodAction, whose start spends the
     lighter, #3632-#3634), then the server's NICOTINE_WITHDRAWAL (stats.all) and the intake's eats counter polled until
     the counter rose and the stat fell (cap SMOKE_CAP_S); the stat, the timer and the counters read before and after;
  4. THE GATE (x321, Session.gate, before the schedule): the server's NICOTINE_WITHDRAWAL is SEEDED at SEED_W (0.2) by
     stats.setany so that a completed smoke shows as a fall (a new smoker's stat reads 0, so a smoke from 0 shows
     nothing); two game minutes later the gate smoke; the gate passes when the eats counter rose and the stat fell to
     max(0, SEED_W - 0.51) = 0 (#3632, f = 1); a failed gate stops the scenario (a named budget stop) and the chain;
  5. THE ANCHOR EDITS (Session.edit, x323): at speed 1, lua.setpath
     NutritionRevamp.server.store.records.admin.satiety.nicH to the world age minus FADE_SET_DAYS x 24 (half the fade,
     "fade"), or to nil (ruling T2-F, "t2f"), a time.snapshot either side, then the record read until two drains have
     run (what the writer laid);
  6. the calendar (schedule): x30's meals (day 0 maint at 13:00 and 20:00; request meals at 08:00, 13:00 and 20:00 on
     days 1-4, day 4 to 13:00; research s3.7 form 1, sized by es and the hour only, never by the nicotine factor) and
     refills (10:30, 16:30, after every meal and every nicotine stop); the nicotine stops on day 3-4 at the cap: fade at
     15:00 day 3, t2f at 21:00 day 3, smoke (the second) at 01:00 day 4. THE ORDER departs from the amendment's (smoke,
     T2-F, fade): the edits are read at the cap, where the factor's contrast is largest (1.1313 against 1.0656 against
     1.0), and the second smoke then shows the reset from a fully faded anchor; T2-F and the fade read after a smoke
     would sit at a withdrawal near 0, where every factor reads about 1;
  7. THE REPLAY'S NICOTINE EVENTS (build_events, seed_events, edit_events; named): the stat is fed from each ring row
     (the tool's feed, ALLOWED_FEED); a smoke and the seed each add a marker {s, kind stat, stat NICOTINE_WITHDRAWAL,
     value the ring row's own} at the first ring row that shows them (the smoke: the eats counter rose; the seed: the
     stat reads the seed), which the feed overwrites with the same value: it changes no input and marks the row before
     it 'between' (the stat moved between the drain and the row); a smoke never lands a vector live (the eat with no
     table entry is a no-op, as on the replay host) and is checked; an edit is a {s, kind setpath, path satiety.nicH,
     value} event due before the first drain that saw it: t2f at the row before the first ring row whose nicH reads
     satiety.t - NIC_FADE_DAYS x 24; fade at the row before the first row reading the set value when the setpath's
     after-snapshot precedes that row's satiety.t (the drain's age), at that row when the before-snapshot follows it,
     and otherwise at the row before with both rows named ambiguous;
  8. the ring (28 paths): + satiety.nicH; - acute.winSleptH, winStartH, awakeH, boutH (sleep off); the rows carry the
     harness's rate, exe and moving, and NICOTINE_WITHDRAWAL among the stats;
  9. the per-session readings: per smoke the stat before and after, the fall against 0.51, the timer, the counters; per
     edit the value set and what the drain laid; the withdrawal on the ring (the first row above 0 after each smoke,
     the slope over the rise, the first row at the cap); the exe guard; drinking and sodium as x30.
Kept from x30: the auto-drink to thirst from a server canteen (ruling T5R-1) and its autoDrop drink events, the sodium
guard, F-T5-2's run_phase fix, the request-meal sizing (NR_R.requestKcal), the phases (boot, S, H, W, X, R, D, Z), the
slot files, the replay of live and the artifact copy.

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run (x321), this file is never edited (CLAUDE.md
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
RING_RECORD = ("satiety.P", "satiety.S", "satiety.L", "satiety.t", "satiety.nicH", "body.energyState", "body.met",
               "acute.debtH", "acute.sleptH", "acute.S", "stomachFill", "stomach.liquid", "body.inDay", "kineticsAge",
               "body.eeDay", "body.fm", "body.lm", "fluids.water", "fluids.na", "fluids.naPlasma", "fluids.sweat6h",
               "fluids.autoDrop", "fluids.thirstTarget")
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
SLEEP_ALLOWED = False      # the live server: the fixture's SleepAllowed and SleepNeeded false (profile x32-nicotine; change 1)
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
DEBT = "acute.debtH"
MET = "body.met"
NIC = "satiety.nicH"       # the writer's anchor (W.nicotine, NR_Server_Writer.lua:441-458): a stored input
SAT_T = "satiety.t"        # the writer's last step age: ring row k+1's is drain k's world age
NW = "NICOTINE_WITHDRAWAL"
SLEEP_DISABLED = NR + ".server.nutrients.sleepDisabled"   # NUT.sleepDisabled (NR_Server_Nutrients.lua:127-143)
RECORD_PATH = NR + ".server.store.records." + USER        # the live record lua.setpath reaches (research s3.5)
CIG = "Base.CigaretteSingle"   # a smokable Food whose OnEat is consumeNicotine (#3633)
LIGHTER = "Base.Lighter"   # the fire ISEatFoodAction:start spends for a smokable (getRequireInHandOrInventory)
SMOKER = "SMOKER"          # trait.set's key: the static field CharacterTrait.SMOKER (registerBase 'Smoker', <clinit> L85)
SEED_W = 0.2               # the gate's seeded withdrawal: a full smoke (f = 1) removes 0.51 and leaves 0 (#3632)
NIC_W_MAX = 0.51           # CharacterStat.NICOTINE_WITHDRAWAL's cap (#3632; the grade reads K.satiety.NIC_WITHDRAWAL_MAX)
NIC_FADE_DAYS = 182        # K.satiety.NIC_FADE_DAYS (planning copy; the grade reads the kernel)
FADE_SET_DAYS = 91         # the fade edit sets the anchor this many days back: half the fade
SMOKE_CAP_S = 60.0         # a smoke not seen within this many wall seconds is a failed smoke (a 460-tick action)
EDIT_SETTLE_S = 20.0       # after an edit, the record is read until two drains have run (satiety.t two minutes on)
# The withdrawal rise at DayLength 1 (planning, arithmetic on #3630 with #2922: the multiplier sums to 120 x minutesPerDay
# a game hour, 1800 at the 15-minute day): the timer gains 1e-4 x 1800 = 0.18 a game hour, so the stat starts to rise
# 1 / 0.18 = 5.556 game hours after a smoke that leaves it at 0, then gains 0.00005 / 8 x 1 x 1800 = 0.01125 a game hour
# (k 1 while the timer reads under 10), reaching the 0.51 cap 45.33 game hours later, 50.89 after the smoke: four times
# #3636's 12.7 game hours on the 60-minute day (the same 1908 real seconds at time speed 1)
RISE_THRESHOLD_H = 1.0 / (1e-4 * 1800)
RISE_RATE_PER_H = 0.00005 / 8 * 1800


def at(d, h):
    """The world age of clock hour h on chain day d (day 0 the fixture's first day: midnight before day d is 24 d - 7)."""
    return 24.0 * d - 7.0 + h


NIC_STOPS = (("FADE", 3, 15.0, "fade"), ("T2F", 3, 21.0, "t2f"), ("SMOKE2", 4, 1.0, "smoke"))


def schedule():
    """The chain's fixed stops [(age, kind, label, extra)], in age order (research row 12; the Task 8 amendments):
      day 0 (the fixture's first day, from the boot at about 11:00): maint meals at 13:00 and 20:00;
      days 1-4: request meals at 08:00, 13:00 and 20:00 (research s3.7 form 1; the oracles' FAST_MEAL_H), day 4 to 13:00;
      the nicotine stops (change 6): the fade edit at 15:00 day 3, the T2-F edit at 21:00 day 3, the second smoke at
      01:00 day 4 (the gate smoke is the first session's, not scheduled);
      refill stops (the canteen back to CANTEEN_L, nothing eaten) at 10:30 and 16:30 on days 0-4; every meal and every
      nicotine stop is followed by a refill too."""
    out = []
    for h in (13.0, 20.0):
        out.append((at(0, h), "maint", "D0_%02d" % h, None))
    for d in (1, 2, 3, 4):
        for h in (8.0, 13.0, 20.0):
            if d == 4 and h > 13.0:
                continue
            out.append((at(d, h), "request", "D%d_%02d" % (d, h), None))
    for label, d, h, kind in NIC_STOPS:
        out.append((at(d, h), kind, label, None))
    for d in range(0, 5):
        for h in (10.5, 16.5):
            hhmm = "%02d%02d" % (int(h), int(round((h % 1) * 60)))
            out.append((at(d, h), "refill", "R%d_%s" % (d, hhmm), None))
    out.sort(key=lambda x: x[0])
    return out


SCHEDULE = schedule()
MEAL_KINDS = ("maint", "request")
NIC_KINDS = ("fade", "t2f", "smoke")


def marker(r, label):
    """The replay's marker for a stat that moved between a drain and ring row r (change 7): the ring row's own
    NICOTINE_WITHDRAWAL, which the feed then copies again; it marks the replay row with r's s as between."""
    return {"s": r["s"], "kind": "stat", "stat": NW, "value": r.get(NW), "label": label, "age": r.get("age")}


def seed_events(rows, seed_age, seed_w=SEED_W, tol=1e-6):
    """The seed's marker: the first ring row at or after seed_age (the setany's world age, before its reply) whose
    NICOTINE_WITHDRAWAL reads seed_w; [] when none (the seed never showed)."""
    if seed_age is None:
        return []
    for r in rows:
        a, w = num(r.get("age")), num(r.get(NW))
        if a is None or w is None or r.get("s") is None or a < seed_age - 1e-9:
            continue
        if abs(w - seed_w) <= tol:
            return [marker(r, "seed")]
    return []


def edit_events(rows, edits, fade_days=NIC_FADE_DAYS, tol=1e-6):
    """The anchor edits' setpath events (change 7), each due before the first drain that saw it. edits: the session's
    edit stops [{kind fade|t2f, label, value, before_age, after_age}]. A t2f: the first ring row after the edit's
    before-snapshot whose nicH reads its satiety.t - fade_days x 24 (the re-laid, fully faded anchor) is row k+1; the
    event sits at row k (a row reading nil is the edit seen before the drain). A fade: the first ring row j after the
    before-snapshot whose nicH equals the value set; the event sits at row j-1 when the after-snapshot precedes row j's
    satiety.t (drain j-1 ran after the set), at row j when the before-snapshot follows it, else at row j-1 with both
    rows named ambiguous. Returns (events, notes); each event carries hold, the ring rows whose grade the edit's timing
    leaves open."""
    on = [r for r in rows if r.get("s") is not None and num(r.get("age")) is not None and r.get("on") is not False]
    out, notes = [], []
    for e in edits:
        b0, a0 = num(e.get("before_age")), num(e.get("after_age"))
        lab = e.get("label")
        if b0 is None:
            notes.append("edit %s: no before-snapshot; no event" % lab)
            continue
        idx = None
        for i, r in enumerate(on):
            if r["age"] < b0 - 1.0 / 60:
                continue
            v, t = num(r.get(NIC)), num(r.get(SAT_T))
            if e["kind"] == "t2f":
                if v is not None and t is not None and abs(v - (t - fade_days * 24.0)) <= tol:
                    idx = i
                    break
            elif v is not None and abs(v - float(e["value"])) <= tol:
                idx = i
                break
        if idx is None or idx == 0:
            notes.append("edit %s: no ring row shows it; no event" % lab)
            continue
        r, prev = on[idx], on[idx - 1]
        nxt = [on[idx + 1]["s"]] if idx + 1 < len(on) else []
        if e["kind"] == "t2f":
            at_row, hold, how = prev, [prev["s"], r["s"]], "relaid"
        else:
            t = num(r.get(SAT_T))
            if t is not None and a0 is not None and a0 < t:
                at_row, hold, how = prev, [r["s"]], "after_snapshot_before_drain"
            elif t is not None and b0 > t:
                at_row, hold, how = r, [r["s"]] + nxt, "before_snapshot_after_drain"
            else:
                at_row, hold, how = prev, [r["s"]] + nxt, "ambiguous"
                notes.append("edit %s: the set straddles the drain at %r; placed before it, rows %r held" % (lab, t, hold))
        ev = {"s": at_row["s"], "kind": "setpath", "path": NIC, "value": None if e["kind"] == "t2f" else float(e["value"]),
              "label": "edit-" + e["kind"], "age": at_row.get("age"), "placement": how, "hold": hold,
              "shown_s": r["s"]}
        out.append(ev)
    return out, notes


def withdrawal_reading(rows, smoke_ages, cap=NIC_W_MAX):
    """The withdrawal on the ring after each smoke (its world age): the first ring row reading above 0 after it, the
    hours from the smoke to it, the slope of the stat over the rows strictly between 0 and the cap (least squares, per
    game hour), the first row at the cap (within 1e-4) and the rows' count. A segment ends at the next smoke."""
    on = [r for r in rows if num(r.get("age")) is not None and num(r.get(NW)) is not None]
    out = []
    ages = sorted(a for a in smoke_ages if a is not None)
    for i, a0 in enumerate(ages):
        a1 = ages[i + 1] if i + 1 < len(ages) else math.inf
        seg = [r for r in on if a0 < r["age"] < a1]
        first = next((r for r in seg if r[NW] > 0), None)
        capr = next((r for r in seg if r[NW] >= cap - 1e-4), None)
        mid = [(r["age"], r[NW]) for r in seg if 0 < r[NW] < cap - 1e-4]
        slope = None
        if len(mid) >= 3:
            n = len(mid)
            mx = sum(x for x, _ in mid) / n
            my = sum(y for _, y in mid) / n
            sxx = sum((x - mx) ** 2 for x, _ in mid)
            if sxx > 0:
                slope = sum((x - mx) * (y - my) for x, y in mid) / sxx
        out.append({"smoke_age": a0, "rows": len(seg),
                    "first_above_0": ({"s": first["s"], "age": first["age"], "w": first[NW],
                                       "h_after_smoke": first["age"] - a0} if first else None),
                    "slope_per_h": slope, "slope_rows": len(mid),
                    "slope_first_age": mid[0][0] if mid else None, "slope_last_age": mid[-1][0] if mid else None,
                    "at_cap": ({"s": capr["s"], "age": capr["age"], "w": capr[NW], "h_after_smoke": capr["age"] - a0}
                               if capr else None),
                    "last": ({"age": seg[-1]["age"], "w": seg[-1][NW]} if seg else None)})
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
    """The sedentary and awake guard over the ring: rows whose harness exe (the server's exercise flag) reads true, rows
    whose moving reads true, and rows reading acute.sleptH above 0 (a drain that ran asleep: none with sleep off)."""
    on = [r for r in ring if num(r.get("age")) is not None]
    exe = [r["s"] for r in on if r.get("exe") is True]
    mv = [r["s"] for r in on if r.get("moving") is True]
    asleep = [r["s"] for r in on if (num(r.get(SLEPT)) or 0) > 0]
    return {"rows": len(on), "exe_true_rows": len(exe), "exe_true_s": exe[:20], "moving_true_rows": len(mv),
            "moving_true_s": mv[:20], "exe_present_rows": sum(1 for r in on if "exe" in r),
            "asleep_rows": len(asleep), "asleep_s": asleep[:20]}


def smoker_in(traits):
    """Whether a trait read-back (a list of names, or one string) names the Smoker trait (any case, any prefix)."""
    if isinstance(traits, dict):
        traits = list(traits.keys()) + [str(v) for v in traits.values()]
    if isinstance(traits, (list, tuple)):
        return any("smoker" in str(x).lower() for x in traits)
    return traits is not None and "smoker" in str(traits).lower()


def smoke_ages(S):
    """The world ages of this session's completed smokes (their after-snapshot), in order."""
    return [st.get("age_after") for st in S.stops if st.get("kind") == "smoke" and st.get("smoked")]


def session_grade(S, ring, rows_rep, pred):
    """The per-session readings and verdicts every x32 driver grades: energy_readings; the drinking and the sodium
    guard per chain day (fluid_days over the ring's autoDrop rows); the refills' container side; the smokes; the edits;
    the withdrawal on the ring after each smoke (withdrawal_reading; a chain session's first segment starts at its
    first ring row); the guard; STOPS (every scheduled stop of this session's span done, every eat landed); SLEEP_OFF
    (the mod read the server's sleep option as disabled); SMOKER (the trait held); SMOKES (each smoke seen, the stat
    fell by min(before, 0.51) within 1e-4, no vector landed); EDITS (each edit shown on the ring as predicted: a t2f
    re-laid fully faded, a fade holding its value); EXE (no exe true row, no asleep row)."""
    energy_readings(S, ring, rows_rep)
    R = S.out["readings"]
    R["fluid_days"] = fluid_days(ring, autodrop_events(ring))     # every ring row's autoDrop (the replay holds some back)
    R["refills"] = [{"label": st["label"], "age": st.get("age"), "left_l": st.get("left_l"), "filled_l": st.get("filled_l"),
                     "fill_ok": st.get("fill_ok")} for st in S.stops if st.get("kind") == "refill" or st.get("refill")]
    smokes = [st for st in S.stops if st.get("kind") == "smoke"]
    R["smokes"] = [{k: st.get(k) for k in ("label", "smoked", "w_before", "w_after", "fall", "fall_expected",
                                           "timer_before", "timer_after", "eats_rose", "landed_rose", "age_before",
                                           "age_after", "reason")} for st in smokes]
    edits = [st for st in S.stops if st.get("kind") in ("fade", "t2f")]
    R["edits"] = [{k: st.get(k) for k in ("label", "kind", "value", "before_age", "after_age", "reply", "laid",
                                          "laid_t", "w")} for st in edits]
    on = [r for r in ring if num(r.get("age")) is not None]
    starts = smoke_ages(S)
    if on and (not starts or on[0]["age"] < starts[0]):
        starts = [on[0]["age"] - 1e-9] + starts
    R["withdrawal"] = withdrawal_reading(ring, starts)
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
    S.out["verdicts"]["SLEEP_OFF"] = {"predicted": pred.get("SLEEP_OFF"), "observed": {"sleepDisabled": sd},
                                      "verdict": "as_predicted" if sd is True else "falsified"}
    held = g(S.out, "phases", "S", "smoker_held")
    S.out["verdicts"]["SMOKER"] = {"predicted": pred.get("SMOKER"), "observed": {"held": held},
                                   "verdict": "as_predicted" if held is True else "falsified"}
    oks = [st for st in smokes if st.get("smoked") and st.get("fall") is not None and st.get("fall_expected") is not None
           and abs(st["fall"] - st["fall_expected"]) <= 1e-4 and not st.get("landed_rose")]
    if smokes or pred.get("SMOKES"):
        S.out["verdicts"]["SMOKES"] = {
            "predicted": pred.get("SMOKES"), "observed": R["smokes"],
            "verdict": "as_predicted" if smokes and len(oks) == len(smokes) else "falsified"}
    oke = []
    for st in edits:
        lv, lt = st.get("laid"), st.get("laid_t")
        if st["kind"] == "t2f" and lv is not None and lt is not None and abs(lv - (lt - NIC_FADE_DAYS * 24.0)) <= 1e-6:
            oke.append(st)
        if st["kind"] == "fade" and lv is not None and st.get("value") is not None and abs(lv - st["value"]) <= 1e-9:
            oke.append(st)
    if edits or pred.get("EDITS"):
        S.out["verdicts"]["EDITS"] = {
            "predicted": pred.get("EDITS"), "observed": R["edits"],
            "verdict": "as_predicted" if edits and len(oke) == len(edits) else "falsified"}
    S.out["verdicts"]["EXE"] = {"predicted": pred.get("EXE"), "observed": R["guard"],
                                "verdict": "as_predicted" if (R["guard"]["exe_true_rows"] == 0
                                                              and R["guard"]["exe_present_rows"] > 0
                                                              and R["guard"]["asleep_rows"] == 0) else "falsified"}
    rise = pred.get("RISE")
    if rise:
        ws = R["withdrawal"]
        obs = {"segments": ws}
        ok = True
        for key, (lo, hi) in (rise.get("bands") or {}).items():
            seg = ws[rise.get("segment", -1)] if ws else {}
            v = g(seg, *key.split(".")) if seg else None
            obs[key] = v
            ok = ok and v is not None and lo <= v <= hi
        S.out["verdicts"]["RISE"] = {"predicted": rise, "observed": obs, "verdict": "as_predicted" if ok else "falsified"}


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
    keyed to the first ring row whose intake.stats.eats rose (one event per unit of the rise, in queue order); a smoke
    (smoke true, eats_rose true: it rose the counter and landed nothing) takes its place in the queue and gives the
    marker (change 7) at that row instead of an eat.
    drinks: [{fluid, drunk, age0, age1}]; a ring row whose intake.stats.sips rose and whose age lies in
    [age0, age1 + 0.1] belongs to that drink, and its litres are split over those rows in proportion to the rise.
    Returns (events, notes)."""
    events, notes = [], []
    queue = [e for e in eats if e.get("landed") or (e.get("smoke") and e.get("eats_rose"))]
    qi = 0
    prev = None
    sip_rows = []
    for r in rows:
        if prev is not None:
            a, b = num(prev.get(EATS)), num(r.get(EATS))
            if a is not None and b is not None and b > a:
                for _ in range(int(round(b - a))):
                    if qi < len(queue) and queue[qi].get("smoke"):
                        events.append(dict(marker(r, "smoke"), smoke=queue[qi].get("label")))
                        queue[qi]["ring_s"] = r["s"]
                        queue[qi]["ring_age"] = r.get("age")
                        qi += 1
                    elif qi < len(queue):
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
                 add_smoker=False, gate_first=False):
        self.prev_run, self.prev_prefix, self.end_age = prev_run, prev_prefix, end_age
        self.add_smoker, self.gate_first = add_smoker, gate_first
        self.seed_age = None
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
            "run_id": self.run_id, "session": session_text, "driver": driver_file, "lib": "x32_nicotine_lib.py",
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
            "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/x32_nicotine_lib.py"),
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
                         if f.endswith(".json") and f.startswith("nicotine-")), None)
        if doc_path is None:
            raise RuntimeError(f"no nicotine-*.json artifact in {prev}")
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

    def nic_read(self, tag, log=True):
        """The server's stats (stats.all: NICOTINE_WITHDRAWAL, HUNGER, UNHAPPINESS, STRESS) and world age in one tick."""
        a = self.keep(self.step(tag, SRV, "stats.all", USER, log=log))
        st = a.get("stats") or {}
        return {"w": num(st.get(NW, st.get("NicotineWithdrawal"))), "hunger": num(st.get("HUNGER", st.get("Hunger"))),
                "unhappiness": num(st.get("UNHAPPINESS", st.get("Unhappiness"))),
                "stress": num(st.get("STRESS", st.get("Stress"))), "age": num(a.get("worldAge")), "wall": a.get("wall")}

    def timer(self, tag):
        """The server's time since the last smoke (witness.fields player <user> getTimeSinceLastSmoke, #3637)."""
        a = self.keep(self.step(tag, SRV, "witness.fields", f"player {USER} getTimeSinceLastSmoke"))
        f = a.get("fields") or {}
        return {"value": num(f.get("getTimeSinceLastSmoke")), "worldAge": a.get("worldAge"),
                "missing": a.get("missing"), "nils": a.get("nils"), "error": a.get("error")}

    def smoke(self, label, sched_age=None):
        """One smoke (change 3): a lighter and one cigarette spawned, foodtimer 0, eat.action CIG 1, then the stat and
        the intake counters polled until the eats counter rose and the stat fell (or read 0 from 0), cap SMOKE_CAP_S.
        A stop row of kind smoke; it also joins the eats queue (smoke true) for the replay's marker."""
        st = {"label": label, "kind": "smoke", "sched_age": sched_age, "food": CIG, "smoke": True, "landed": False,
              "smoked": False}
        self.stops.append(st)
        self.eats.append(st)
        st["spawn_lighter"] = self.spawn(LIGHTER, 1, label + "_spawn_lighter")
        st["spawn_cig"] = self.spawn(CIG, 1, label + "_spawn_cig")
        st["foodtimer"] = self.keep(self.step(label + "_foodtimer", SRV, "foodtimer.set", f"{USER} 0")).get("after")
        b = self.nic_read(label + "_w0")
        bi = self.intake(label + "_before")
        st["timer_before"] = self.timer(label + "_timer0").get("value")
        st["w_before"], st["age_before"], st["before"], st["stats_before"] = b["w"], b["age"], bi, b
        st["fall_expected"] = min(b["w"], NIC_W_MAX) if b["w"] is not None else None
        q = self.keep(self.step(label + "_eat", CLI, "eat.action", f"{CIG} 1"))
        st["queued"] = {k: q.get(k) for k in ("queued", "fraction", "spawned", "itemId", "validStart", "maxTime",
                                              "moodleFoodEaten", "wall")}
        if not q.get("queued"):
            st["queue_reply"] = q
            st["reason"] = "not_queued"
            self.note(f"smoke {label}: not queued: {str(q)[:300]}")
            return st
        end = time.time() + SMOKE_CAP_S
        polls = []
        while time.time() < end:
            if self.parked():
                st["reason"] = "parked"
                break
            a = self.intake(label + "_poll")
            n = self.nic_read(label + "_wpoll", log=False)
            rose = a.get("eats") is not None and bi.get("eats") is not None and a["eats"] > bi["eats"]
            fell = n["w"] is not None and b["w"] is not None and (n["w"] < b["w"] - 1e-6 or (b["w"] <= 0 and rose))
            polls.append({"w": n["w"], "eats": a.get("eats"), "age": n["age"], "wall": n["wall"]})
            if rose and fell:
                st["smoked"] = True
                st["reason"] = "seen"
                break
            time.sleep(POLL_S)
        if not st["smoked"] and st.get("reason") is None:
            st["reason"] = "cap"
            self.note(f"smoke {label}: not seen within {SMOKE_CAP_S} s")
        st["polls"] = polls[:5] + polls[-5:] if len(polls) > 10 else polls
        st["poll_n"] = len(polls)
        after = self.nic_read(label + "_w1")
        ai = self.intake(label + "_after")
        st["timer_after"] = self.timer(label + "_timer1").get("value")
        st["w_after"], st["age_after"], st["after"], st["stats_after"] = after["w"], after["age"], ai, after
        st["fall"] = (b["w"] - after["w"]) if (b["w"] is not None and after["w"] is not None) else None
        st["eats_rose"] = (ai.get("eats") or 0) - (bi.get("eats") or 0) if ai.get("eats") is not None else None
        st["landed_rose"] = (ai.get("landed") or 0) - (bi.get("landed") or 0) if ai.get("landed") is not None else None
        if st["landed_rose"]:
            self.out["deviations"].append(f"smoke {label}: the intake landed a vector ({st['landed_rose']})")
        self.mark(label + "_smoked", w_before=b["w"], w_after=after["w"], smoked=st["smoked"])
        return st

    def gate(self):
        """The smoke gate (change 4, the chain's first session, before the schedule): at speed 1, the stat read, seeded
        at SEED_W by stats.setany, two game minutes waited (the ring and a drain see the seed), then the gate smoke. A
        failed gate stops the scenario (a named budget stop)."""
        G = self.out["phases"]["X"].setdefault("gate", {})
        self.one("G_one")
        G["before"] = self.nic_read("G_w0")
        G["timer_before"] = self.timer("G_timer0")
        G["seed_before_age"] = self.age("G_seed_t0")
        G["seed"] = self.keep(self.step("G_seed", SRV, "stats.setany", f"{USER} {NW} {SEED_W}"))
        G["seed_after_age"] = self.age("G_seed_t1")
        self.seed_age = G["seed_before_age"]
        a = self.age("G_a")
        self.wait_age((a or 0) + 2.0 / 60, "G_wait")
        G["seeded"] = self.nic_read("G_w_seeded")
        st = self.smoke("G_SMOKE", G["seed_before_age"])
        ok = (st.get("smoked") is True and st.get("fall") is not None and abs(st["fall"] - SEED_W) <= 1e-4
              and not st.get("landed_rose"))
        G["passed"] = ok
        self.out["verdicts"]["GATE"] = {
            "predicted": {"smoke": "the eats counter rises and the seeded stat falls from 0.2 to 0 (0.51 x f, f = 1, "
                                   "#3632); no vector lands; the timer reads 0 after (the remainder over 0.51)"},
            "observed": {k: st.get(k) for k in ("smoked", "w_before", "w_after", "fall", "eats_rose", "landed_rose",
                                                "timer_before", "timer_after", "reason")},
            "verdict": "as_predicted" if ok else "falsified"}
        self.persist()
        if not ok:
            raise Budget("the smoke gate failed: " + json.dumps(self.out["verdicts"]["GATE"]["observed"], default=str))

    def edit(self, kind, label, sched_age=None):
        """An anchor edit (change 5) at speed 1: fade sets satiety.nicH to the world age minus FADE_SET_DAYS x 24, t2f
        sets it nil (ruling T2-F); a time.snapshot either side; then the record read until two drains have run since
        the set (satiety.t at least two game minutes past the after-snapshot): what the writer laid. A stop row."""
        st = {"label": label, "kind": kind, "sched_age": sched_age}
        self.stops.append(st)
        self.one(label + "_one")
        st["w"] = self.nic_read(label + "_w").get("w")
        b = self.snap(label + "_t0")
        a0 = num(b.get("worldAge"))
        value = "nil" if kind == "t2f" else repr(float(a0 - FADE_SET_DAYS * 24.0))
        st["value"] = None if kind == "t2f" else float(value)
        r = self.keep(self.step(label + "_set", SRV, "lua.setpath", f"{RECORD_PATH}.{NIC} {value}"))
        a = self.snap(label + "_t1")
        st["before_age"], st["after_age"] = a0, num(a.get("worldAge"))
        st["reply"] = {k: r.get(k) for k in ("ok", "path", "before", "after", "err")}
        if r.get("ok") is not True:
            self.out["deviations"].append(f"edit {label}: lua.setpath failed: {str(r)[:300]}")
        end = time.time() + EDIT_SETTLE_S
        reads = []
        while time.time() < end:
            x = self.lread(SRV, f"record:{USER}", [NIC, SAT_T], label + "_read", log=False)
            v = x.get("values") or {}
            reads.append({"nicH": num(v.get(NIC)), "t": num(v.get(SAT_T)), "wall": x.get("wall")})
            t = num(v.get(SAT_T))
            if t is not None and st["after_age"] is not None and t >= st["after_age"] + 2.0 / 60:
                break
            time.sleep(POLL_S)
        st["reads"] = reads[:3] + reads[-3:] if len(reads) > 6 else reads
        last = reads[-1] if reads else {}
        st["laid"], st["laid_t"] = last.get("nicH"), last.get("t")
        self.mark(label + "_edited", value=st["value"], laid=st["laid"], laid_t=st["laid_t"])
        return st

    def run_schedule(self):
        """The chain's stops from this session's age to end_age, then speed 5 to end_age. A refill first, at once (the
        canteen as the attach left it). A meal stop already past by under LATE_MAX_H is done at once (late, named), an
        older one is missed (named, a deviation); a nicotine stop already past is missed (a deviation); a refill stop
        already past is skipped (named, not a deviation: the first refill covers it). The gate (change 4) runs first
        in the chain's first session. Each meal and each nicotine stop is followed by a refill. Refill stops run at
        speed 5 (no clock-sensitive reading)."""
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
                elif kind in MEAL_KINDS and a0 - age < LATE_MAX_H:
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
        if self.gate_first:
            self.gate()
        self.refill("X_refill0", a0)
        self.persist()
        for age, kind, label, extra in todo:
            self.check()
            if kind in ("maint", "request"):
                self.to_stop(age, label)
                self.meal(kind, label, age)
                self.refill(label + "_R", age)
            elif kind == "smoke":
                self.to_stop(age, label)
                self.smoke(label, age)
                self.refill(label + "_R", age)
            elif kind in ("fade", "t2f"):
                self.to_stop(age, label)
                self.edit(kind, label, age)
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
        if self.add_smoker:                                                                         # change 2
            P["trait_set"] = self.keep(self.step("S_trait_set", SRV, "trait.set", f"{USER} {SMOKER} add"))
            P["trait_push"] = self.keep(self.step("S_trait_push", SRV, "trait.push", USER))
        b = self.keep(self.step("S_body", SRV, "stats.get", USER))
        P["body"] = {k: b.get(k) for k in ("traits", "traitList", "asleep", "fatigue", "weight", "worldAge", "wall")}
        P["smoker_held"] = (smoker_in(b.get("traitList")) or smoker_in(b.get("traits"))
                            or smoker_in((P.get("trait_push") or {}).get("traitList"))
                            or smoker_in((P.get("trait_set") or {}).get("traitList")))
        if not P["smoker_held"]:                                                                    # change b
            self.out["abort"] = ("phase S: the Smoker trait is not held after " +
                                 ("trait.set and trait.push" if self.add_smoker else "the restart") +
                                 " (stats.get traitList " + json.dumps(b.get("traitList"), default=str)[:200] + ")")
            self.out["deviations"].append(self.out["abort"])
        P["timer"] = self.timer("S_timer")
        P["nicotine"] = self.nic_read("S_w")

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
        seeds = seed_events(rows, self.seed_age)           # change 7: the gate's seed, a marker
        edits = [st for st in self.stops if st.get("kind") in ("fade", "t2f")]
        evs, enotes = edit_events(rows, edits)             # change 7: the anchor edits, setpath events
        notes = notes + enotes
        nic = [e for e in seeds + evs if first is None or e["s"] >= first["s"]]
        events = sorted(events0 + drops + nic, key=lambda e: e["s"])
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
        RP["autodrops"] = {"n": len(drops), "water_g": sum(e["vec"]["water"] for e in drops),
                           "held_in_start": held, "first_ring_s_after_start": first["s"] if first else None}
        RP["nicotine_events"] = {"seed": len(seeds), "edits": [{k: e.get(k) for k in ("s", "label", "value",
                                                                                     "placement", "hold", "shown_s")}
                                                               for e in evs],
                                 "smokes": sum(1 for e in events0 if e.get("label") == "smoke")}
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
            if self.out.get("abort"):                      # change b: no scenario phase after a failed trait check
                break
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
