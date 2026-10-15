"""x44_guide_lib -- the session engine of Plan 14 Task 5's live drivers for the player guide (vanilla Project Zomboid
against the Nutrition Revamp mod): the vanilla-baseline sessions (x441 V1a, x442 V1b, x443a and x443b V2 on one world,
x444 V3, x445 V4) and two modded gap sessions (x446 M1, x447 M2), the source map's section 5 as corrected by its fix
round (docs/superpowers/research/2026-10-15-mod-guide/source-map.md; the review's corrections, task-1-review.md, bind).
Fix round 1 (task-5-review.md): I-1, I-2 and M-1 to M-13 applied; V2 split into x443a and x443b (a reuse boot).

Started from x43c_strength_lib.py (frozen with x436; its plumbing, its staged-copy gate and its harness-marker check are
copied here, not imported), on testing/experiments/xlib.py (the bus step, the wall budget, the grade recorder, RCON, the
spawn, the abort/teardown/copy skeleton). The modded sessions' ring, start record, event building and replay are ported
from x36_gut_lib.py (frozen with x361), on the HEAD tool tools/replay_live.py.

THE VANILLA SESSIONS (profile x44-vanilla: fixture default, PZTestKit ONLY -- no NutritionRevamp and no TKX probe --
Nutrition true, the fixture's DayLength 4 (a 90-minute day), sleep off; V4 alone on x44-vanilla-sleep, the same with
[server] SleepAllowed and SleepNeeded true, because fatigue holds only then, #2949). The lib reads nothing of the mod:
no record.*, no lua.read of a record, no NR mirror. Every harness command it uses is a row of
docs/reference/harness-commands.md: minute.ring (no paths), stats.set, stats.get, stats.all, nutrition.get,
nutrition.set, health.get, moodle.level, perk.xp, perk.park, xp.grant, item.get, fluid.fill, autodrink.probe,
witness.chain, time.snapshot, time.multiplier, players, lua.read (_G SandboxVars only), ping (server); eat.action,
drink.action, exercise.do, action.cancel (client); and RCON additem and settimespeed.
  The clock: RCON settimespeed 30 between events (8 game minutes a wall second at DayLength 4, one tick a game minute,
  #1776), settimespeed 1 around every eat and drink (a networked action ends in real time, #3766); time.multiplier is
  the fallback only when the RCON command fails; the clock is restored at the end from the trueMult read at phase S
  (CLAUDE.md s5: a setting is restored from the value read before it was set).
  The eat: RCON additem (xlib.Xs.spawn, confirmed by item.get) before, then eat.action <type> 1 on the client with NO
  foodtimer.set (the map's I-3: it always writes); the landing is the server's calorie store rising by at least half
  the item's kcal (stats.get polled at speed 1); the model's eat sits at the midpoint of the last two polls' ages.
  A write (stats.set or nutrition.set) is bracketed by two age reads; its read-back values enter the model as a write
  at the brackets' mean age.

THE MODEL (each vanilla grade's prediction): tools/vanilla_model.py simulate() for the same events from the run's own
start state, read at phase S (stats.get, health.get, stats.all, perk.xp in one sequence) and fed to the model. The
model has no write event, so model_chain() cuts the session at every write (stats.set, nutrition.set, perk.park, and
xp.grant through vanilla_model.strength_xp_grant, the model's own VM11 arithmetic) and runs simulate() per segment,
carrying the end state with the write's read-back applied. The output's `model_inputs` holds the exact scenario
(start, settings, events, hours, dt_min, a0), so Task 7 re-runs it.

THE MODDED SESSIONS (profiles x44-mod, sleep off, and x44-mod-sleep, sleep on: PZTestKit and the STAGED copy
release/plan14-x44 of mod/NutritionRevamp at HEAD (`python tools/release_pack.py stage mod/NutritionRevamp --out
release/plan14-x44` before the boot; the driver checks it against release_pack.manifest() of a clean mod/ and never
stages), Nutrition false (ruling T18-1), DayLength 1). Phases S, H (the ring with record paths), W (the start record:
the store's saved line), X, C (the clock restored), R (the ring read and stopped). The grade is the HEAD kernel replay
(tools/replay_live.py replay_live, the ServerReplay backend) of the ring's own clock from the start record, with the
eats, the drinks, the ring's autoDrop and movement events and (M2) the ring's sleep events, passing sleep_allowed as
the profile sets it.

THE GRADES (pure; each has a failing case in testing/tests/test_x44_guide_lib.py; a grade on zero samples is
unmeasured, never as_predicted; every tolerance is named here, before any run):
  curve    a ring field against the model at each row's age, rows within EVENT_SKIP_H of an event skipped (the eat
           lands between two rows); HUNGER_TOL, THIRST_TOL.
  reads    a scalar read (stats.get calories, weight or foodTimer; health.get overall) against the model
           at the read's own server age; CAL_TOL (+ CAL_TOL_REL of the hours' idle burn), WEIGHT_TOL, HEALTH_TOL,
           TIMER_TOL.
  levels   a moodle level read against the model's level at the paired stats.get's age, reads within MOODLE_SKEW_H of
           a model crossing skipped.
  freeze   V1a arm B: HUNGER held at 0 after the eat and leaving it within FREEZE_TOL_H of the model's timer-zero age.
  crossing V1b: the ring's HUNGER first above 0.70 within LEVEL_TOL_H of the model's crossing.
  death    V1b: isDead (or overall health 0) first read within DEATH_TOL_H of the model's health-zero age.
  set      V3: a push-up set's Strength XP delta against the model's within REP_TOL reps x 6 x the model's factor.
  grant    V3: xp.grant's xpAfter against vanilla_model.strength_xp_grant within XP_TOL.
  level    V3: perk.xp's level and the band trait stats.get lists against the model's level and its band (#2157).
  coffee   V4: FATIGUE across the drink against the model's change within FATIGUE_TOL; it holds for a game hour
           (no read under FATIGUE_RESET).
  intox    V4: the decay slope after the last beer within INTOX_DECAY_REL of the model's, and the first zero read within
           INTOX_ZERO_TOL_H of the model's zero age.
  replay   M1, M2: per field, the replay rows against the ring under REPLAY_TOL (M2 adds ACUTE_TOL); a field compared on
           no row is unmeasured; the hangover (M2) reached live iff the replay reaches it, within HANG_TOL_H.

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run, this file is never edited (CLAUDE.md s5); a
later change is a new file and the drivers that use it name it.
"""
import bisect
import glob
import json
import math
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                    # testing/
sys.path.insert(0, HERE)                                     # experiments/

import xlib as X                                                 # noqa: E402

REPO = X.REPO
sys.path.insert(0, os.path.join(REPO, "tools"))
import vanilla_model as VM                                       # noqa: E402

SRV = X.SRV
LIB_FILE = "x44_guide_lib.py"
NR = "NutritionRevamp"
USER = "admin"
CLI = "client"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
MOD_DIR = "mod/NutritionRevamp"
STAGE_OUT = "release/plan14-x44"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_CORE = "common/media/lua/shared/NR_Core.lua"
MANIFEST_NAME = "MANIFEST.json"
MIN_FREE_GB = 12.0

# ---- the sessions (amendments item 2; the map's section 5) -----------------------------------------------------------
SESSIONS = {
    "V1a": {"prefix": "x441", "profile": "x44-vanilla", "kind": "vanilla", "sleep": False, "artifact": "meal.json"},
    "V1b": {"prefix": "x442", "profile": "x44-vanilla", "kind": "vanilla", "sleep": False, "artifact": "starve.json"},
    "V2a": {"prefix": "x443a", "profile": "x44-vanilla", "kind": "vanilla", "sleep": False, "artifact": "tuna-a.json"},
    "V2b": {"prefix": "x443b", "profile": "x44-vanilla", "kind": "vanilla", "sleep": False, "artifact": "tuna-b.json",
            "chain_from": "V2a"},
    "V3": {"prefix": "x444", "profile": "x44-vanilla", "kind": "vanilla", "sleep": False, "artifact": "strength.json"},
    "V4": {"prefix": "x445", "profile": "x44-vanilla-sleep", "kind": "vanilla", "sleep": True,
           "artifact": "drinks.json"},
    "M1": {"prefix": "x446", "profile": "x44-mod", "kind": "mod", "sleep": False, "artifact": "fast.json"},
    "M2": {"prefix": "x447", "profile": "x44-mod-sleep", "kind": "mod", "sleep": True, "artifact": "acute.json"},
}
VANILLA_DAY_LENGTH = 4                 # the fixture's own (docs/platform/harness.md fixture table): a 90-minute day
MOD_DAY_LENGTH = 1
DAY_LENGTH_MIN = {1: 15.0, 4: 90.0}    # SandboxVars.DayLength to the day's real minutes (VM3, VM10, VM16 read it)

# ---- the foods and fluids --------------------------------------------------------------------------------------------
BOLOGNESE = "Base.CannedBologneseOpen"
TUNA = "Base.TunaTinOpen"
BEER = "Base.BeerCan"
BOTTLE = "Base.WaterBottle"
# the install's script values (media/scripts/generated/items/food.txt; read-only), what vanilla's eat adds (VM4, VM7)
VANILLA_FOODS = {
    BOLOGNESE: {"hunger_script": -24.0, "calories": 540.0, "carbs": 68.0, "lipids": 22.0, "proteins": 18.0,
                "foodType": "Meat"},
    TUNA: {"hunger_script": -18.0, "calories": 370.0, "carbs": 0.0, "lipids": 34.0, "proteins": 15.0,
           "foodType": "Fish"},
}
# the mod's item pass (mod/NutritionRevamp/common/media/scripts/NR_ItemPass_Food.txt) re-bases the macros; HungerChange
# and FoodType stay the script's; the replay's eat event carries them as the live getters read them (float32)
MOD_FOODS = {BOLOGNESE: {"cal": 540.00, "carb": 61.83, "lip": 22.19, "pro": 23.60, "hunger_script": -24.0,
                         "foodType": "Meat"}}
COFFEE_L = 0.25                        # the map's cup (x151r's)
BEER_L = 0.3                           # the BeerCan's Capacity, prefilled Beer (normal.txt; #2950)
# One container TYPE a drink. drink.action takes the client's first item of the type (findOrSpawn's
# getFirstTypeRecurse) and an emptied can stays a BeerCan (normal.txt: FluidContainer, no ReplaceOnUse), so a second
# can of the same type would be the drunk one; and fluid.fill refills only the SERVER copy (its comment block), so
# the client's copy must still be full for the client's action. Each drink therefore takes a fresh, prefilled type
# (RCON additem: both sides hold it full), its server copy filled with the drink's fluid by fluid.fill (x151r's route).
BEER_CONTAINERS = ("Base.BeerCan", "Base.BeerBottle", "Base.BeerImported", "Base.Pop2")   # each 0.3 L prefilled
COFFEE_CONTAINERS = ("Base.WaterBottle", "Base.FountainCupWater", "Base.Pop3")

# ---- the clock -------------------------------------------------------------------------------------------------------
HOUR_OFFSET = 7.0                      # world age 0 is 07:00 on the default fixture (#2890)
SPEED_FAST = 30                        # vanilla: 8 game minutes a wall second at DayLength 4 (#1776)
MOD_SPEED_FAST = 5                     # modded, DayLength 1 (x364's)
LEAD_MIN = 3.0                         # game minutes before a timed eat or drink at which the clock drops to speed 1
POLL_S = 0.25
EAT_CAP_S = 40.0
DRINK_CAP_S = 40.0
SETTLE_POLLS = 3
SPEED_UNIT = "GameTime.getTrueMultiplier (the settimespeed number); mult is getMultiplier, the effective one"
# MoodleType's static fields are upper case ('Hungry' is the registry id, not a Lua field; review I-1): moodle.level
# indexes MoodleType[name] and answers {ok=false, reason="no MoodleType.<name>"} on a miss
MOODLE_FOOD_EATEN = "FOOD_EATEN"
MOODLE_HUNGRY = "HUNGRY"
MOVED_SHARE = 0.25                     # a drink has landed once its stat moved a quarter of the model's change

# ---- the tolerances (named before any run) ---------------------------------------------------------------------------
HUNGER_TOL = 0.003
THIRST_TOL = 0.003
EVENT_SKIP_H = 2.0 / 60.0
TIMER_TOL = 100.0                      # food-timer units (3 a game-second at DayLength 4: about 33 game seconds)
MOODLE_SKEW_H = 1.0 / 60.0
FREEZE_TOL_H = 2.0 / 60.0
FREEZE_EPS = 0.0005                    # HUNGER at or under this reads frozen at 0
CAL_TOL = 5.0
CAL_TOL_REL = 0.01                     # of the idle burn over the hours since the segment start (VM6)
WEIGHT_TOL = 0.02
HEALTH_TOL = 1.0
LEVEL_TOL_H = 0.1
DEATH_TOL_H = 0.5
REP_TOL = 2
XP_TOL = 1.0
FATIGUE_TOL = 0.005
FATIGUE_RESET = 0.1
INTOX_DECAY_REL = 0.05
INTOX_ZERO_TOL_H = 0.05
INTOX_FIT_MIN = 1.0                    # the decay fit reads INTOXICATION above this only (the floor clamps it at 0)
MODEL_DT_MIN = 1.0

# ---- V1a -------------------------------------------------------------------------------------------------------------
V1A_HUNGER_A = 0.25
V1A_HUNGER_B = 0.10
V1A_ARM_A_H = 6.0
V1A_ARM_B_H = 2.0
V1A_TIMER_WINDOW_M = 25.0
V1A_TIMER_EVERY_S = 10.0
# ---- V1b -------------------------------------------------------------------------------------------------------------
V1B_HUNGER = 0.60
V1B_CAP_H = 40.0
V1B_HEALTH_EVERY_H = 0.25
V1B_HUNGRY_4 = 0.70                    # #0508, strict
# ---- V2 --------------------------------------------------------------------------------------------------------------
V2_CALORIES = 3000.0
V2_WEIGHT = 80.0
# V2 is two sessions on one world (the controller's ruling on the review's concern 3): x443a writes the store and runs
# the first V2_SPLIT_H game hours from its anchor (the age after the writes); x443b boots x443a's saved world again
# (a reuse boot) and runs on to the anchor plus V2_SPAN_H. The schedule is relative to the anchor (review M-11): the DL4
# sessions start near world age 2.35 (x371 2.351, x372 2.359), past 08:00 on day 1.
V2_EAT_OFFSETS = (0.0, 4.0, 8.0, 12.0, 24.0, 28.0, 32.0)   # four tins on day 1, three on day 2, from the anchor
V2_SPAN_H = 36.0
V2_SPLIT_H = 18.0
V2_THIRST_EVERY_H = 6.0
# ---- V3 --------------------------------------------------------------------------------------------------------------
V3_PARK_LEVEL = 5
V3_GRANT = 29700.0                     # 37500 + 29700 = 67200, 300 under level 6's 67500 (#2102)
V3_PROTEINS = (("A", 0.0), ("B", 100.0), ("C", -400.0))
PUSHUP_ASK_M = 60                      # game minutes asked: the set ends at exhaustion first (x423)
SET_START_CAP_S = 20.0
SET_CAP_S = 200.0
EXE_CLEAR_CAP_S = 20.0
BANDS = (("weak", 1), ("feeble", 4), (None, 5), ("stout", 8), ("strong", 10))   # #2157 (x43c's)
MUSCLE = ("weak", "feeble", "stout", "strong")
# ---- V4 --------------------------------------------------------------------------------------------------------------
V4_FATIGUE = 0.5
V4_HOLD_H = 1.0
V4_HOLD_SLOW_M = 5.0                   # the first game minutes after the coffee read at speed 1, the rest at speed 30
V4_BEERS = 4
V4_INTOX_EVERY_S = 2.0
V4_INTOX_CAP_H = 1.0

# ---- the modded sessions ---------------------------------------------------------------------------------------------
H_REQ = 0.25
APPROACH = 0.246
SAVE_CAP_S = 80.0
LITRES_PER_THIRST = 2.0                # NR_Server_Nutrients.lua NUT.LITRES_PER_THIRST
AUTODROP = "fluids.autoDrop"
SLEPT = "acute.sleptH"
EATS_G = "_G.NutritionRevamp.server.intake.stats.eats"
LANDED_G = "_G.NutritionRevamp.server.intake.stats.landed"
SIPS_G = "_G.NutritionRevamp.server.intake.stats.sips"
LASTSIG = "_G.NutritionRevamp.server.bus.lastSig.admin"
INTAKE_PATHS = ("NutritionRevamp.server.intake.stats.eats", "NutritionRevamp.server.intake.stats.landed",
                "NutritionRevamp.server.intake.stats.sips")
FLUSH_PATHS = ("NutritionRevamp.server.players.online.admin", "NutritionRevamp.server.store.file.lastWrite.admin",
               "NutritionRevamp.server.store.file.stats.writes")
RING_GLOBALS = ("_G.NutritionRevamp.server.writer.stats.writes", "_G.NutritionRevamp.server.writer.stats.sips",
                EATS_G, LANDED_G, SIPS_G, LASTSIG)
M1_RING = ("satiety.M", "satiety.S", "satiety.L", "satiety.t", "stomachFill", "stomach.liquid", "body.energyState",
           "body.met", "body.fm", "body.lm", "body.inDay", "body.eeDay", "kineticsAge", "fluids.water", "fluids.na",
           "fluids.naPlasma", AUTODROP, "fluids.thirstTarget", "fluids.dehydPct") + RING_GLOBALS
M2_RING = ("satiety.M", "satiety.S", "satiety.L", "satiety.t", "stomachFill", "stomach.liquid", "body.energyState",
           "body.met", "kineticsAge", "fluids.water", AUTODROP, "fluids.thirstTarget", "acute.caf", "acute.cafTol",
           "acute.gutCaf", "acute.alc", "acute.bac", "acute.gutAlc", "acute.hang", "acute.hangH", "acute.debtH",
           SLEPT, "acute.winSleptH", "acute.S", "effects.fOff") + RING_GLOBALS
H1_EXTRA = ("firstSeen", "body.sex", "body.fm", "body.lm")
STAT_NAMES = {"HUNGER": "Hunger", "THIRST": "Thirst", "FATIGUE": "Fatigue", "BOREDOM": "Boredom",
              "UNHAPPINESS": "Unhappiness", "NICOTINE_WITHDRAWAL": "NicotineWithdrawal", "INTOXICATION": "Intoxication"}
REPLAY_TOL = {"HUNGER": ("abs", 0.002), "body.energyState": ("abs", 0.005), "THIRST": ("abs", 0.002)}
ACUTE_TOL = {"acute.caf": ("abs", 1.0), "acute.bac": ("abs", 0.001), "acute.hang": ("abs", 0.5),
             "acute.debtH": ("abs", 0.05)}
HANG_TOL_H = 0.25
M1_FAST_H = 24.0
M1_REQUEST_CAP_H = 12.0
# M2's schedule is relative to phase X's start (review I-2: the DL1 sessions start near world age 3.2 and phase W
# waits up to 80 s, about 2.1 game hours, so a 10:00 coffee has passed before X)
M2_COFFEE_OFFSETS = (0.1, 3.1, 6.1)    # game hours from X's start
M2_BEER_GAP_H = 3.0                    # the beers at least this long after the last coffee, and not before 19:00
M2_BEER_HOUR = 19.0
M2_NIGHT_HOUR = 23.0
M2_NIGHT_MAX_GAP_H = 4.0               # the night at the next 23:00 when that is at most this long after the beers,
M2_NIGHT_FALLBACK_H = 1.0              # else this long after them (named in the plan)
M2_NIGHT_H = 4.0
M2_DAY2_H = 6.0                        # day 2: meals at the request for this long after the night's end
FAST_FORWARD_NOTE = ("the night's fast-forward rests on #2956 (x151s, DL1, build 42.20.4; the fast-forward an "
                     "inference), not re-read on 42.21; the booked hours are the reading")
HOLD_S = 600
NIGHT_CAP_S = 90.0
WAKE_SETTLE_S = 5.0

# ---- the harness markers the lib's commands need (the repository files and every deployed copy) ----------------------
HARNESS_FILES = {"PZTestKit_Server.lua": LUA_DIR + "/server/PZTestKit_Server.lua",
                 "PZTestKit_Client.lua": LUA_DIR + "/client/PZTestKit_Client.lua",
                 "PZTestKit_Core.lua": LUA_DIR + "/shared/PZTestKit_Core.lua"}
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": tuple(f'TK.register("{c}", function(' for c in (
        "minute.ring", "stats.set", "stats.get", "stats.all", "nutrition.get", "nutrition.set", "health.get",
        "moodle.level", "perk.xp", "perk.park", "xp.grant", "item.get", "fluid.fill", "autodrink.probe",
        "witness.chain", "time.multiplier", "player.sleep", "player.sleep.hold", "foodtimer.set", "players")),
    "PZTestKit_Client.lua": tuple(f'TK.register("{c}", function(' for c in (
        "eat.action", "drink.action", "exercise.do", "action.cancel")),
    "PZTestKit_Core.lua": tuple(f'TK.register("{c}", function(' for c in ("time.snapshot", "lua.read",
                                                                         "lua.global")),
}
ECHO_RX = re.compile(r"PZTK: ")
NEVER_RX = re.compile(r"(?!x)x")
LOG_RX = re.compile(r"NutritionRevamp|NR_|LuaError|STACK TRACE|lua error|attempted index|tried to call nil", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|failed:|STACK TRACE|attempted index|tried to call nil")
STATS_GET_KEYS = ("calories", "carbs", "lipids", "proteins", "weight", "hunger", "thirst", "endurance", "fatigue",
                  "foodTimer", "standardFoodTime", "asleep", "moving", "worldAge", "wall")


# ================================================================ pure helpers
def num(v):
    return X.num(v)


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def fmtnum(v):
    return repr(float(v))


def vals(a):
    return (a or {}).get("values") or {}


def norm(name):
    """A trait name in one spelling: lower case, the registry prefix and every space or underscore dropped."""
    s = str(name).lower().split(":")[-1]
    return re.sub(r"[\s_]", "", s)


def traits_of(stats):
    lst = (stats or {}).get("traitList")
    if lst == {}:
        lst = []                                         # the harness answers an empty list as {}
    if not isinstance(lst, list):
        return None
    return [norm(t) for t in lst]


def band_of(level):
    """The Strength band trait vanilla's remap holds at a level (#2157), or None."""
    lv = num(level)
    if lv is None:
        return None
    for name, top in BANDS:
        if lv <= top:
            return name
    return "strong"


def bands_held(traits):
    return sorted(t for t in (traits or []) if t in MUSCLE)


def stat_of(reply, name):
    """One stat off a stats.all reply ({stats: {NAME or CamelName: value}})."""
    st = (reply or {}).get("stats") or {}
    return num(st.get(name, st.get(STAT_NAMES.get(name, name))))


def hour_of(age):
    return (age + HOUR_OFFSET) % 24.0


def age_at(day, hour):
    """The world age of clock hour `hour` on day `day` (day 1 the fixture's first day)."""
    return 24.0 * (day - 1) + hour - HOUR_OFFSET


def next_age_of_hour(age, hour):
    """The first world age at or after `age` whose clock reads `hour`."""
    a = age_at(1, hour)
    while a < age - 1e-9:
        a += 24.0
    return a


def appetite_of(traits):
    t = set(traits or [])
    if "heartyappetite" in t:
        return 1.5
    if "lighteater" in t:
        return 0.75
    return 1.0


# ================================================================ the vanilla model (VM1-VM16 through simulate)
START_KEYS = {"hunger": "hunger", "thirst": "thirst", "weight_kg": "weight_kg", "calories": "calories_store",
              "carbs": "carbs", "lipids": "lipids", "proteins": "proteins", "health": "health",
              "food_timer": "food_timer", "fatigue": "fatigue", "intoxication": "intoxication",
              "strength_xp": "strength_xp", "strength_level": "strength_level"}
WRITE_KEYS = {"hunger": "hunger", "thirst": "thirst", "fatigue": "fatigue", "calories": "calories",
              "weight": "weight_kg", "carbs": "carbs", "lipids": "lipids", "proteins": "proteins",
              "strength_xp": "strength_xp", "strength_level": "strength_level", "food_timer": "food_timer"}
WRITE_KINDS = ("set", "grant")


def start_state(stats, health=None, stats_all=None, xp=None):
    """The model's start off the phase-S reads: stats.get (hunger, thirst, weight, the stores, fatigue, foodTimer),
    health.get overall, stats.all INTOXICATION and perk.xp Strength. A key read as None is left out (the model's default
    stands, named in the reply's `defaulted`)."""
    s = stats or {}
    st = {"hunger": num(s.get("hunger")), "thirst": num(s.get("thirst")), "weight_kg": num(s.get("weight")),
          "calories": num(s.get("calories")), "carbs": num(s.get("carbs")), "lipids": num(s.get("lipids")),
          "proteins": num(s.get("proteins")), "fatigue": num(s.get("fatigue")), "food_timer": num(s.get("foodTimer")),
          "health": num((health or {}).get("overall")), "intoxication": stat_of(stats_all, "INTOXICATION")}
    if xp is not None:
        st["strength_xp"] = num(xp.get("xp"))
        st["strength_level"] = num(xp.get("level"))
        if st["strength_level"] is not None:
            st["strength_level"] = int(st["strength_level"])
    out = {k: v for k, v in st.items() if v is not None}
    out["defaulted"] = sorted(k for k, v in st.items() if v is None)
    return out


def apply_write(state, e, settings):
    st = dict(state)
    if e["kind"] == "set":
        for k, v in (e.get("values") or {}).items():
            key = WRITE_KEYS.get(k)
            if key is not None and num(v) is not None:
                st[key] = int(v) if key == "strength_level" else float(v)
    elif e["kind"] == "grant":
        xp = st.get("strength_xp", VM.total_xp_for_level(int(st.get("strength_level", VM.START_LEVEL))))
        xp, made = VM.strength_xp_grant(xp, float(e["amount"]), st.get("proteins", 0.0),
                                        settings.get("xp_multiplier", 1.0), False, settings.get("protein_factor"))
        st["strength_xp"] = xp
        lv = int(st.get("strength_level", VM.START_LEVEL))
        while lv < 10 and xp >= VM.total_xp_for_level(lv + 1):
            lv += 1                                       # #2122
        st["strength_level"] = lv
    return st


def _state_of(res):
    st = {sk: res[ser][-1][1] for sk, ser in START_KEYS.items()}
    st["strength_level"] = int(st["strength_level"])
    return st


def model_chain(scn):
    """simulate() run per segment (see the module docstring), the session cut at every event's age: at a cut the
    writes apply to the carried state first, then simulate() starts the segment with that cut's other events at its
    own t = 0 (applied before its first point). scn: {start, settings, events, hours, dt_min}; an event's t_h is game
    hours from the session start a0. Returns {series: [(t_h, value), ...]}, each cut carrying two points (the segment
    before it ends, then the state after the cut's writes and events), and "_marks": per cut {t_h, labels, pre (the
    state before the cut), writes (after its writes), post (after its events too)}, so an event's own jump is read
    off its mark, never interpolated."""
    st = {k: v for k, v in (scn.get("start") or {}).items() if k != "defaulted"}
    st.setdefault("strength_level", VM.START_LEVEL)
    st.setdefault("strength_xp", VM.total_xp_for_level(int(st["strength_level"])))
    settings = dict(scn.get("settings") or {})
    hours = float(scn["hours"])
    dt = float(scn.get("dt_min", MODEL_DT_MIN))
    events = sorted(scn.get("events") or [], key=lambda e: e["t_h"])
    cuts = sorted({max(0.0, e["t_h"]) for e in events if e["t_h"] < hours})
    bounds = [0.0] + [c for c in cuts if c > 0.0] + [hours]
    out = {k: [] for k in VM.SERIES}
    marks = []
    for t0, t1 in zip(bounds, bounds[1:]):
        here = [e for e in events if abs(max(0.0, e["t_h"]) - t0) < 1e-12]
        mark = {"t_h": t0, "labels": [e.get("label") for e in here], "pre": dict(st)}
        for e in here:
            if e["kind"] in WRITE_KINDS:
                st = apply_write(st, e, settings)
        mark["writes"] = dict(st)
        seg = [dict(e, t_h=0.0) for e in here if e["kind"] not in WRITE_KINDS]
        span = t1 - t0
        if span <= 0.0:
            continue
        n = max(1, int(math.ceil(span * 60.0 / dt - 1e-9)))
        res = VM.simulate({"hours": span * (1.0 + 1e-12), "dt_min": span * 60.0 / n, "start": st,
                           "settings": settings, "events": seg})
        mark["post"] = {sk: res[ser][0][1] for sk, ser in START_KEYS.items()}
        if here:
            marks.append(mark)
        for k in VM.SERIES:
            out[k].extend((t0 + t, v) for t, v in res[k])
        st = _state_of(res)
    out["_marks"] = marks
    return out


def mark_of(model, label):
    """The cut that carries the event or write labelled `label`, or None."""
    return next((m for m in model.get("_marks") or [] if label in m["labels"]), None)


def series_at(series, t, step=False):
    """The model's value at t (game hours from a0): linear between points, or the last point at or before t (step);
    at a write's boundary the written value; None outside the series."""
    if not series:
        return None
    ts = [p[0] for p in series]
    if t < ts[0] - 1e-9 or t > ts[-1] + 1e-9:
        return None
    j = bisect.bisect_right(ts, t + 1e-12) - 1
    j = max(0, j)
    if step or j >= len(series) - 1 or abs(ts[j] - t) < 1e-12:
        return series[j][1]
    t0, v0 = series[j]
    t1, v1 = series[j + 1]
    if t1 <= t0:
        return v1
    return v0 + (v1 - v0) * (t - t0) / (t1 - t0)


def first_cross(series, level, after=0.0):
    """The first t past `after` where the series rises strictly above `level` (linear between points), or None."""
    prev = None
    for t, v in series:
        if t < after - 1e-12:
            prev = (t, v)
            continue
        if v > level:
            if prev is None or prev[1] > level or prev[0] < after - 1e-12:
                return t
            t0, v0 = prev
            return t0 + (t - t0) * (level - v0) / (v - v0) if v != v0 else t
        prev = (t, v)
    return None


def first_at_or_below(series, level, after=0.0):
    """The first t past `after` where the series falls to `level` or under, linear between points; a point sitting
    exactly on a clamped `level` (the model floors the timer, health and intoxication at 0) is reached along the slope
    of the two points before it."""
    prev, prev2 = None, None
    for t, v in series:
        if t >= after - 1e-12 and v <= level:
            if prev is not None and prev[0] >= after - 1e-12 and prev[1] > level and t > prev[0]:
                t0, v0 = prev
                cut = t0 + (t - t0) * (v0 - level) / (v0 - v)
                if v == level and prev2 is not None and prev2[1] > v0 and prev[0] > prev2[0]:
                    slope = (v0 - prev2[1]) / (t0 - prev2[0])
                    cut = min(cut, t0 + (level - v0) / slope)
                return cut
            return t
        prev2, prev = prev, (t, v)
    return None


def crossings(series, thresholds, after=0.0):
    """Every t where the moodle level (count of thresholds strictly below the value) changes."""
    out = []
    last = None
    for t, v in series:
        if t < after:
            continue
        lv = sum(1 for th in thresholds if v > th)
        if last is not None and lv != last:
            out.append(t)
        last = lv
    return out


PRERUN_START = {"hunger": 0.0, "thirst": 0.0, "weight_kg": 80.0, "calories": 800.0, "health": 100.0,
                "food_timer": 0.0, "fatigue": 0.0, "intoxication": 0.0}
PRERUN_SETTINGS = {"day_length_min": 90.0, "stats_decrease": 3, "appetite": 1.0, "sleep_allowed": False,
                   "xp_multiplier": 1.0}


def _eat_ev(t, full):
    f = VANILLA_FOODS[full]
    return {"t_h": t, "kind": "eat", "hunger_script": f["hunger_script"], "calories": f["calories"],
            "carbs": f["carbs"], "lipids": f["lipids"], "proteins": f["proteins"]}


def prerun(key):
    """The headline numbers the model predicts BEFORE the run, from the model's own defaults (a fresh 80 kg character
    at 800 kcal, T2.3) and the session's planned writes and events at their planned times; the graded predictions are
    re-run from the run's own read start. Returns a dict of numbers."""
    S = dict(PRERUN_SETTINGS)
    if key == "V1a":
        ev = [{"t_h": 0.0, "kind": "set", "values": {"hunger": V1A_HUNGER_A, "thirst": 0.0}}, _eat_ev(0.05, BOLOGNESE),
              {"t_h": 6.1, "kind": "set", "values": {"hunger": V1A_HUNGER_B}}, _eat_ev(6.15, BOLOGNESE)]
        m = model_chain({"start": PRERUN_START, "settings": S, "events": ev, "hours": 8.5})
        tz = first_at_or_below(m["food_timer"], 0.0, after=6.15 + 1e-6)
        return {"A_hunger_after_eat": series_at(m["hunger"], 0.06),
                "A_timer_after_eat": series_at(m["food_timer"], 0.06),
                "A_hunger_6h": series_at(m["hunger"], 6.05), "B_timer_after_eat": series_at(m["food_timer"], 6.15),
                "B_freeze_min": None if tz is None else (tz - 6.15) * 60.0}
    if key == "V1b":
        ev = [{"t_h": 0.0, "kind": "set", "values": {"hunger": V1B_HUNGER, "thirst": 0.0}}]
        ev += [{"t_h": float(h), "kind": "set", "values": {"thirst": 0.0}} for h in range(1, int(V1B_CAP_H))]
        m = model_chain({"start": PRERUN_START, "settings": S, "events": ev, "hours": V1B_CAP_H})
        return {"level4_h": first_cross(m["hunger"], V1B_HUNGRY_4), "death_h": first_at_or_below(m["health"], 0.0),
                "health_per_h_at_4": VM.health_loss_per_hour(4, 0, 90.0)}
    if key in ("V2a", "V2b"):
        ev = [{"t_h": 0.0, "kind": "set", "values": {"calories": V2_CALORIES, "weight": V2_WEIGHT}}]
        ev += [_eat_ev(o, TUNA) for o in V2_EAT_OFFSETS]
        t = V2_THIRST_EVERY_H
        while t < V2_SPAN_H:
            ev.append({"t_h": t, "kind": "set", "values": {"thirst": 0.0}})
            t += V2_THIRST_EVERY_H
        m = model_chain({"start": PRERUN_START, "settings": S, "events": ev, "hours": V2_SPAN_H})
        w = m["weight_kg"]
        mid = series_at(w, V2_SPLIT_H)
        return {"span_h": V2_SPAN_H, "weight_change_span": w[-1][1] - V2_WEIGHT,
                "weight_change_V2a": mid - V2_WEIGHT, "weight_change_V2b": w[-1][1] - mid,
                "calories_end": m["calories_store"][-1][1]}
    if key == "V3":
        x5 = VM.total_xp_for_level(V3_PARK_LEVEL)
        g_xp = VM.strength_xp_grant(x5, V3_GRANT, 0.0)[0]
        return {"A": VM.strength_xp_grant(x5, VM.pushup_set_xp(), 0.0)[1], "B_grant_xp_after": g_xp,
                "B": VM.strength_xp_grant(g_xp, VM.pushup_set_xp(), 100.0)[1],
                "B_level": VM.level_for_xp(VM.strength_xp_grant(g_xp, VM.pushup_set_xp(), 100.0)[0]),
                "C": VM.strength_xp_grant(x5, VM.pushup_set_xp(), -400.0)[1]}
    if key == "V4":
        gain = VM.intoxication_gain(VM.BEER_ALCOHOL_PER_L * BEER_L, 0.0)
        rate = VM.intoxication_decay_per_hour(90.0)
        return {"coffee_fatigue": VM.fatigue_change(COFFEE_L), "beer_gain_each": gain, "decay_per_h": rate,
                "zero_after_first_h": V4_BEERS * gain / rate}
    return {}


# ================================================================ the grades (pure)
def near_event(age, ages, skip_h=EVENT_SKIP_H):
    return any(abs(age - a) <= skip_h for a in ages)


def grade_curve(rows, model, field, series, a0, tol, window, skip_ages=(), skip_h=EVENT_SKIP_H):
    """A ring field against the model at each row's age in window (a0-relative ages are model t)."""
    lo, hi = window
    n, worst, over = 0, 0.0, []
    for r in rows or []:
        a, v = num(r.get("age")), num(r.get(field))
        if a is None or v is None or a < lo - 1e-9 or a > hi + 1e-9 or r.get("on") is False:
            continue
        if near_event(a, skip_ages, skip_h):
            continue
        m = series_at(model.get(series) or [], a - a0)
        if m is None:
            continue
        n += 1
        d = abs(v - m)
        if d > worst:
            worst = d
        if d > tol:
            over.append({"s": r.get("s"), "age": a, "live": v, "model": m, "d": d})
    obs = {"field": field, "n": n, "max": worst, "tol": tol, "over_n": len(over), "over": over[:20],
           "window": [lo, hi]}
    if n == 0:
        obs["why"] = "no ring row compared"
        return "unmeasured", obs
    if over:
        obs["why"] = f"{len(over)} row(s) off the model by more than {tol}"
        return "falsified", obs
    return "as_predicted", obs


def grade_reads(reads, model, key, series, a0, tol, rel_burn=None):
    """Scalar reads [{age, <key>}] against the model at each read's own age; rel_burn adds CAL_TOL_REL of the idle
    burn over the hours since a0 to the tolerance."""
    n, worst, over, rows = 0, 0.0, [], []
    for r in reads or []:
        a, v = num(r.get("age")), num(r.get(key))
        if a is None or v is None:
            continue
        m = series_at(model.get(series) or [], a - a0)
        if m is None:
            continue
        t = tol + (rel_burn * VM.burn_rate() * 3600.0 * max(0.0, a - a0) if rel_burn else 0.0)
        d = abs(v - m)
        n += 1
        worst = max(worst, d)
        rows.append({"age": a, "live": v, "model": m})
        if d > t:
            over.append({"age": a, "live": v, "model": m, "d": d, "tol": t})
    obs = {"key": key, "n": n, "max": worst, "tol": tol, "rel_burn": rel_burn, "over_n": len(over),
           "over": over[:20], "pairs": rows[:60]}
    if n == 0:
        obs["why"] = "no read compared"
        return "unmeasured", obs
    if over:
        obs["why"] = f"{len(over)} read(s) off the model"
        return "falsified", obs
    return "as_predicted", obs


def grade_levels(reads, model, series, thresholds, a0, skew_h=MOODLE_SKEW_H):
    """Moodle level reads [{age, level}] against the model's level of `series` at each read's age; reads within skew_h
    of a model crossing are skipped."""
    s = model.get(series) or []
    cross = [c + a0 for c in crossings(s, thresholds)]
    n, bad = 0, []
    for r in reads or []:
        a, lv = num(r.get("age")), num(r.get("level"))
        if a is None or lv is None or near_event(a, cross, skew_h):
            continue
        m = series_at(s, a - a0)
        if m is None:
            continue
        want = sum(1 for th in thresholds if m > th)
        n += 1
        if int(lv) != want:
            bad.append({"age": a, "level": lv, "want": want, "model": m})
    obs = {"n": n, "bad_n": len(bad), "bad": bad[:20], "crossings": cross}
    if n == 0:
        obs["why"] = "no level read compared"
        return "unmeasured", obs
    if bad:
        obs["why"] = f"{len(bad)} level read(s) off the model's"
        return "falsified", obs
    return "as_predicted", obs


def grade_freeze(rows, eat_age, model, a0, tol_h=FREEZE_TOL_H):
    """V1a arm B: HUNGER frozen at 0 after the eat; the first ring row above FREEZE_EPS after it within tol_h of the
    model's timer-zero age (the first model point at or after the eat with food_timer 0)."""
    obs = {"eat_age": eat_age, "tol_h": tol_h}
    if eat_age is None:
        obs["why"] = "the eat never landed"
        return "unmeasured", obs
    tz = first_at_or_below(model.get("food_timer") or [], 0.0, after=eat_age - a0 + 1e-6)
    obs["model_unfreeze_age"] = None if tz is None else tz + a0
    if tz is None:
        obs["why"] = "the model's timer never ran out in the window"
        return "unmeasured", obs
    after = [r for r in rows or [] if num(r.get("age")) is not None and num(r.get("HUNGER")) is not None
             and r["age"] > eat_age + 1e-9]
    held = [r for r in after if r["age"] < tz + a0 - tol_h]
    obs["held_rows"] = len(held)
    obs["held_max"] = max((r["HUNGER"] for r in held), default=None)
    first = next((r for r in after if r["HUNGER"] > FREEZE_EPS), None)
    obs["live_unfreeze_age"] = None if first is None else first["age"]
    if not held or first is None:
        obs["why"] = "no ring row inside the freeze, or none after it"
        return "unmeasured", obs
    if obs["held_max"] > FREEZE_EPS:
        obs["why"] = "HUNGER rose inside the model's freeze"
        return "falsified", obs
    obs["miss_h"] = first["age"] - (tz + a0)
    if abs(obs["miss_h"]) > tol_h:
        obs["why"] = f"the freeze ended {obs['miss_h']:+.4f} h off the model's"
        return "falsified", obs
    return "as_predicted", obs


def grade_crossing(rows, model, series, field, level, a0, tol_h, after_age=None, last_age=None):
    """The ring's field first above `level` (after after_age) within tol_h of the model's crossing; no live crossing
    with the session past the model's age plus tol_h (last_age) is falsified (review M-8: a plateau under 0.70,
    #0174)."""
    t = first_cross(model.get(series) or [], level, after=0.0 if after_age is None else after_age - a0)
    live = next((r for r in rows or [] if num(r.get("age")) is not None and num(r.get(field)) is not None
                 and (after_age is None or r["age"] >= after_age) and r[field] > level), None)
    obs = {"model_age": None if t is None else t + a0, "live_age": None if live is None else live["age"],
           "level": level, "tol_h": tol_h, "last_age": last_age}
    if t is not None and live is None and last_age is not None and last_age > t + a0 + tol_h:
        obs["why"] = "no live crossing by the model's age plus the tolerance"
        return "falsified", obs
    if t is None or live is None:
        obs["why"] = "the model or the ring never crossed"
        return "unmeasured", obs
    obs["miss_h"] = live["age"] - (t + a0)
    if abs(obs["miss_h"]) > tol_h:
        obs["why"] = f"crossed {obs['miss_h']:+.3f} h off the model"
        return "falsified", obs
    return "as_predicted", obs


def grade_death(death, model, a0, last_age, tol_h=DEATH_TOL_H, gone=False):
    """The first read reading admin dead (isDead, or overall health at 0) within tol_h of the model's health-zero age;
    unmeasured when the session ended before the model's age plus tol_h without a death read, or when the last read
    found the player gone from the online list (review M-1)."""
    t = first_at_or_below(model.get("health") or [], 0.0)
    obs = {"model_age": None if t is None else t + a0, "live_age": (death or {}).get("age"), "tol_h": tol_h,
           "last_age": last_age, "gone": gone}
    if t is None:
        obs["why"] = "the model never reaches health 0 in its hours"
        return "unmeasured", obs
    if gone and not (death or {}).get("dead"):
        obs["why"] = "the player left the online list"
        return "unmeasured", obs
    if not (death or {}).get("dead"):
        if last_age is not None and last_age > t + a0 + tol_h:
            obs["why"] = "alive past the model's death age plus the tolerance"
            return "falsified", obs
        obs["why"] = "the session ended before the model's death age plus the tolerance"
        return "unmeasured", obs
    obs["miss_h"] = death["age"] - (t + a0)
    if abs(obs["miss_h"]) > tol_h:
        obs["why"] = f"died {obs['miss_h']:+.3f} h off the model"
        return "falsified", obs
    return "as_predicted", obs


def model_set_delta(model, label):
    """The model's Strength XP gained by the set labelled `label`: its cut's state after the events less after the
    writes."""
    m = mark_of(model, label)
    if m is None or "post" not in m:
        return None
    return m["post"]["strength_xp"] - m["writes"]["strength_xp"]


def grade_set(row, model, a0):
    """V3: one set's XP delta (perk.xp after minus before) against the model's within REP_TOL reps x 6 x the factor."""
    row = row or {}
    x0, x1 = num(g(row, "xp_before", "xp")), num(g(row, "xp_after", "xp"))
    pred = model_set_delta(model, row.get("label"))
    f = num(row.get("factor"))
    obs = {"xp_before": x0, "xp_after": x1, "pred": pred, "factor": f, "exe_seen": row.get("exe_seen"),
           "stop_reason": row.get("stop_reason"), "set_s": row.get("set_s")}
    if x0 is None or x1 is None or pred is None or f is None or not row.get("exe_seen"):
        obs["why"] = "a read is missing, or the set was never seen on the server"
        return "unmeasured", obs
    obs["delta"] = x1 - x0
    tol = REP_TOL * VM.XP_PER_REP * f
    obs["tol"] = tol
    obs["reps_live"] = (x1 - x0) / (VM.XP_PER_REP * f) if f else None
    if abs((x1 - x0) - pred) > tol:
        obs["why"] = f"delta {x1 - x0} off the model's {pred} by more than {tol}"
        return "falsified", obs
    return "as_predicted", obs


def grade_grant(reply, pred):
    obs = {"xpBefore": (reply or {}).get("xpBefore"), "xpAfter": (reply or {}).get("xpAfter"), "pred": pred,
           "tol": XP_TOL}
    x = num(obs["xpAfter"])
    if x is None or pred is None:
        obs["why"] = "xp.grant's reply or the model's value is missing"
        return "unmeasured", obs
    if abs(x - pred) > XP_TOL:
        obs["why"] = f"xpAfter {x} off the model's {pred}"
        return "falsified", obs
    return "as_predicted", obs


def grade_level_band(xp_read, stats, want_level):
    """V3 arm B: perk.xp's level the model's, and the band trait list holding exactly that level's band (#2157)."""
    lv = num((xp_read or {}).get("level"))
    tr = traits_of(stats)
    want_b = [band_of(want_level)] if (want_level is not None and band_of(want_level)) else []
    obs = {"level": lv, "want_level": want_level, "bands": bands_held(tr), "want_bands": want_b}
    if lv is None or tr is None or want_level is None:
        obs["why"] = "the level or the trait list is unread"
        return "unmeasured", obs
    bad = []
    if int(lv) != int(want_level):
        bad.append(f"level {lv} not {want_level}")
    if bands_held(tr) != want_b:
        bad.append(f"bands {bands_held(tr)} not {want_b}")
    if bad:
        obs["why"] = "; ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def grade_coffee(c, model, a0):
    """V4 arm A: FATIGUE after the drink minus before against the model's change within FATIGUE_TOL."""
    c = c or {}
    b, a = num(g(c, "before", "fatigue")), num(g(c, "after", "fatigue"))
    t0, t1 = num(g(c, "before", "worldAge")), num(g(c, "after", "worldAge"))
    s = model.get("fatigue") or []
    pred = None
    if t0 is not None and t1 is not None:
        m0, m1 = series_at(s, t0 - a0), series_at(s, t1 - a0)
        pred = None if (m0 is None or m1 is None) else m1 - m0
    obs = {"before": b, "after": a, "pred": pred, "tol": FATIGUE_TOL, "landed": c.get("landed"),
           "fill_ok": c.get("fill_ok")}
    if c.get("fill_ok") is False:
        obs["why"] = "the coffee's fill gate failed (review M-2)"
        return "unmeasured", obs
    if b is None or a is None or pred is None or not c.get("landed"):
        obs["why"] = "the drink never landed, or a read is missing"
        return "unmeasured", obs
    obs["delta"] = a - b
    if abs((a - b) - pred) > FATIGUE_TOL:
        obs["why"] = f"FATIGUE moved {a - b}, the model {pred}"
        return "falsified", obs
    return "as_predicted", obs


def grade_coffee_holds(c):
    """V4 arm A: through the hour after the drink no FATIGUE read under FATIGUE_RESET (the write holds, VM15)."""
    c = c or {}
    polls = [p for p in c.get("hold") or [] if num(p.get("fatigue")) is not None]
    obs = {"n": len(polls), "min": min((p["fatigue"] for p in polls), default=None), "reset_at": FATIGUE_RESET,
           "landed": c.get("landed"), "hours": c.get("hold_h")}
    if not polls or not c.get("landed"):
        obs["why"] = "no read in the hour, or the drink never landed"
        return "unmeasured", obs
    if obs["min"] < FATIGUE_RESET:
        obs["why"] = "FATIGUE fell to its reset inside the hour"
        return "falsified", obs
    return "as_predicted", obs


def fit_slope(points):
    """Least-squares slope of [(x, y)], or None under 3 points."""
    if len(points) < 3:
        return None
    n = float(len(points))
    mx = sum(p[0] for p in points) / n
    my = sum(p[1] for p in points) / n
    sxx = sum((p[0] - mx) ** 2 for p in points)
    if sxx <= 0:
        return None
    return sum((p[0] - mx) * (p[1] - my) for p in points) / sxx


def grade_intox_decay(polls, last_drink_age, model, a0):
    """V4 arm B: INTOXICATION's slope (per game hour) over the polls after the last can, while above INTOX_FIT_MIN,
    against the model's slope over the same span within INTOX_DECAY_REL."""
    pts = [(p["age"], p["intox"]) for p in polls or [] if num(p.get("age")) is not None
           and num(p.get("intox")) is not None and last_drink_age is not None
           and p["age"] > last_drink_age + EVENT_SKIP_H and p["intox"] > INTOX_FIT_MIN]
    live = fit_slope(pts)
    s = model.get("intoxication") or []
    mpts = [(a, series_at(s, a - a0)) for a, _v in pts]
    mpts = [(a, v) for a, v in mpts if v is not None and v > INTOX_FIT_MIN]
    pred = fit_slope(mpts)
    obs = {"n": len(pts), "live_per_h": live, "model_per_h": pred, "rel_tol": INTOX_DECAY_REL}
    if live is None or pred is None or pred == 0:
        obs["why"] = "under three reads above the fit floor"
        return "unmeasured", obs
    obs["rel"] = abs(live - pred) / abs(pred)
    if obs["rel"] > INTOX_DECAY_REL:
        obs["why"] = f"slope {live} off the model's {pred}"
        return "falsified", obs
    return "as_predicted", obs


def grade_intox_zero(polls, last_drink_age, model, a0, tol_h=INTOX_ZERO_TOL_H, last_age=None):
    """V4 arm B: the first poll reading INTOXICATION 0 after the last can's model event within tol_h of the model's
    zero age after it (intoxication cannot reach 0 between the cans: each adds 6, the decay between them is under 1)."""
    t = None
    if last_drink_age is not None:
        t = first_at_or_below(model.get("intoxication") or [], 0.0, after=last_drink_age - a0 + 1e-6)
    live = next((p for p in polls or [] if num(p.get("age")) is not None and num(p.get("intox")) is not None
                 and last_drink_age is not None and p["age"] > last_drink_age and p["intox"] <= 0.0), None)
    obs = {"model_age": None if t is None else t + a0, "live_age": None if live is None else live["age"],
           "tol_h": tol_h, "last_age": last_age}
    if t is not None and live is None and last_age is not None and last_age > t + a0 + tol_h:
        obs["why"] = "no live crossing by the model's age plus the tolerance"
        return "falsified", obs
    if t is None or live is None:
        obs["why"] = "the model or the polls never read zero"
        return "unmeasured", obs
    obs["miss_h"] = live["age"] - (t + a0)
    if abs(obs["miss_h"]) > tol_h:
        obs["why"] = f"zero {obs['miss_h']:+.4f} h off the model"
        return "falsified", obs
    return "as_predicted", obs


def grade_replay_field(diff, field):
    """One field of tools/replay_live.diff: unmeasured on 0 compared rows (never a pass), falsified on any row over."""
    st = g(diff, "fields", field) or {}
    obs = {"field": field, "n": st.get("n"), "max": st.get("max"), "over": st.get("over"),
           "worst_s": st.get("worst_s"), "findings": [f for f in (diff or {}).get("findings") or []
                                                      if f.get("field") == field][:20]}
    if not st or not st.get("n"):
        obs["why"] = "the field was compared on no row"
        return "unmeasured", obs
    if st.get("over"):
        obs["why"] = f"{st['over']} row(s) over the tolerance"
        return "falsified", obs
    return "as_predicted", obs


def grade_hangover(ring, rep_rows, tol_h=HANG_TOL_H):
    """M2: the ring's acute.hang reaches 1 iff the replay's does, the first ages within tol_h."""
    def first(rows):
        r = next((r for r in rows or [] if num(r.get("acute.hang")) == 1 and num(r.get("age")) is not None), None)
        return None if r is None else r["age"]
    seen = [r for r in ring or [] if num(r.get("acute.hang")) is not None]
    live, rep = first(ring), first(rep_rows)
    obs = {"live_age": live, "replay_age": rep, "rows": len(seen), "tol_h": tol_h}
    if not seen:
        obs["why"] = "the ring never read acute.hang"
        return "unmeasured", obs
    if live is None and rep is None:
        obs["why"] = "neither reached a hangover"
        return "unmeasured", obs
    if live is None or rep is None:
        obs["why"] = "one side reached a hangover and the other did not"
        return "falsified", obs
    obs["miss_h"] = live - rep
    if abs(obs["miss_h"]) > tol_h:
        obs["why"] = f"the hangover began {obs['miss_h']:+.3f} h off the replay"
        return "falsified", obs
    return "as_predicted", obs


# ================================================================ the modded sessions' event building (x36's, ported)
def mod_eat_event(full, s, label=None):
    """The replay's eat of a vanilla food the mod re-bases: the item pass's macros and the script's hunger and FoodType,
    as the live getters read them (float32); the nutrients beyond the macros come from the mod's own table."""
    import replay_live as RL
    f = MOD_FOODS[full]
    return {"s": s, "kind": "eat", "fullType": full, "cal": RL.float32(f["cal"]), "carb": RL.float32(f["carb"]),
            "lip": RL.float32(f["lip"]), "pro": RL.float32(f["pro"]),
            "hunger": RL.float32(f["hunger_script"]) / 100.0, "foodType": f["foodType"], "label": label}


def build_events(rows, eats, drinks):
    """x36's build_events: an eat keyed to the first ring row whose intake eats count rose (queue order); a drink's
    litres split over the ring rows whose sips rose inside [age0, age1 + 0.1]. Returns (events, notes)."""
    events, notes = [], []
    queue = [e for e in eats if e.get("landed")]
    qi, prev, sip_rows = 0, None, []
    for r in rows:
        if prev is not None:
            a, b = num(prev.get(EATS_G)), num(r.get(EATS_G))
            if a is not None and b is not None and b > a:
                for _ in range(int(round(b - a))):
                    if qi < len(queue):
                        events.append(mod_eat_event(queue[qi]["food"], r["s"], queue[qi].get("label")))
                        queue[qi]["ring_s"], queue[qi]["ring_age"] = r["s"], r.get("age")
                        qi += 1
                    else:
                        notes.append(f"eats rose at s {r['s']} with no queued eat left")
            a, b = num(prev.get(SIPS_G)), num(r.get(SIPS_G))
            if a is not None and b is not None and b > a:
                sip_rows.append((r, b - a))
        prev = r
    if qi < len(queue):
        notes.append(f"{len(queue) - qi} landed eat(s) never seen in the ring")
    for d in drinks:
        if num(d.get("drunk")) is None or d["drunk"] <= 0:
            notes.append(f"drink {d.get('label')}: no litres drunk read; no event")
            continue
        mine = [(r, n) for r, n in sip_rows if num(r.get("age")) is not None and num(d.get("age0")) is not None
                and num(d.get("age1")) is not None and d["age0"] - 1e-9 <= r["age"] <= d["age1"] + 0.1]
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


def autodrop_events(rows):
    """x36's: each ring row reading fluids.autoDrop > 0 is one `autodrop` event {s, g} at that row."""
    out = []
    for r in rows:
        v = num(r.get(AUTODROP))
        if v is not None and v > 0 and r.get("s") is not None:
            out.append({"s": r["s"], "kind": "autodrop", "g": LITRES_PER_THIRST * v * 1000.0, "label": "autodrop",
                        "autoDrop": v, "age": r.get("age")})
    return out


def ring_moving_events(rows):
    """x36's: one activity event {s, moving} wherever the ring's online `moving` flag changes, from a still start."""
    out, cur = [], False
    for r in rows:
        if r.get("s") is None or r.get("on") is False:
            continue
        mv = r.get("moving")
        if not isinstance(mv, bool) or mv == cur:
            continue
        out.append({"s": r["s"], "kind": "activity", "moving": mv, "label": "ring-moving", "age": r.get("age")})
        cur = mv
    return out


def sleep_events(rows):
    """x30's: drain k ran asleep when ring row k+1 reads acute.sleptH > 0; one sleep event {s: row k, asleep} where
    the state changes, from an awake start; offline rows skipped."""
    on = [r for r in rows if r.get("on") is not False and r.get("s") is not None and num(r.get("age")) is not None]
    out, last = [], False
    for r, nxt in zip(on, on[1:]):
        v = num(nxt.get(SLEPT))
        if v is None:
            continue
        asleep = v > 0
        if asleep != last:
            out.append({"s": r["s"], "kind": "sleep", "asleep": asleep, "label": "ring-sleep", "age": r.get("age")})
            last = asleep
    return out


def replay_events(rows, eats, drinks, start_age, sleep=False):
    """The replay's whole event list and its bookkeeping: the logged eats and drinks (build_events), the ring's autoDrop
    and movement events and (sleep) its sleep events; an autoDrop or movement event at or before the first ring row
    after the start record is held back (the record already holds it, x35's rule)."""
    events0, notes = build_events(rows, eats, drinks)
    drops, moves = autodrop_events(rows), ring_moving_events(rows)
    sleeps = sleep_events(rows) if sleep else []
    first = next((r for r in rows if num(r.get("age")) is not None
                  and (start_age is None or r["age"] > start_age + 1e-9)), None)
    held = [e for e in drops + moves + sleeps if first is not None and e["s"] <= first["s"]]
    keep = [e for e in drops + moves + sleeps if first is None or e["s"] > first["s"]]
    events = sorted(events0 + keep, key=lambda e: e["s"])
    return events, {"notes": notes, "held_in_start": held,
                    "autodrops": len([e for e in keep if e["kind"] == "autodrop"]),
                    "moves": len([e for e in keep if e["kind"] == "activity"]),
                    "sleeps": len([e for e in keep if e["kind"] == "sleep"]),
                    "first_ring_s_after_start": None if first is None else first["s"]}


def replay_grade(ring_rows, events, start, sleep_allowed, tol, paths=None, player=None, start_stats=None,
                 hour_offset=None):
    """The HEAD kernel replay of the ring (tools/replay_live.replay_live) and its diff under tol. Returns (rows, diff,
    backend)."""
    import replay_live as RL
    rows, be = RL.replay_live(ring_rows, events, start, paths=paths, user=USER, player=player,
                              start_stats=start_stats, sleep_allowed=sleep_allowed, hour_offset=hour_offset)
    return rows, RL.diff(rows, ring_rows, tol), be


# ================================================================ the pre-boot checks (offline; tested)
def harness_markers_ok(repo=REPO):
    found = {}
    for fname, rel in HARNESS_FILES.items():
        try:
            with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""
        found[fname] = {mk: (mk in text) for mk in HARNESS_MARKERS[fname]}
    return found, all(all(d.values()) for d in found.values())


def profile_doc_checks(key, name, doc, text=""):
    """A profile's TOML (parsed) against its session: the fixture, the one client, the mods (vanilla: PZTestKit alone;
    modded: PZTestKit and the staged copy), Nutrition and DayLength, the sleep keys, the verify rows, and its header
    line naming its own file. Returns {check: bool}."""
    spec = SESSIONS[key]
    mods = [m.get("id") for m in doc.get("mods") or []]
    sb = doc.get("sandbox") or {}
    srv = doc.get("server") or {}
    ver = doc.get("verify") or []
    c = {"named_profile": name == spec["profile"],
         "header_names_file": text.startswith(f"# testing/profiles/{name}.toml"),
         "fixture_default": doc.get("fixture") == "default",
         "one_admin_client": doc.get("clients", ["admin"]) == ["admin"],
         "sleep_keys": srv.get("SleepAllowed") is spec["sleep"] and srv.get("SleepNeeded") is spec["sleep"]}
    if spec["kind"] == "vanilla":
        c["mods_harness_only"] = mods == ["PZTestKit"]
        c["nutrition_true"] = sb.get("Nutrition") is True
        c["day_length"] = sb.get("DayLength", VANILLA_DAY_LENGTH) == VANILLA_DAY_LENGTH
        c["verify_nutrition_on"] = any(v.get("args") == "SandboxVars.Nutrition" and v.get("expect") == '"value": true'
                                       for v in ver)
        c["verify_mod_absent"] = any(v.get("args") == NR and v.get("expect") == '"resolved": false' for v in ver)
    else:
        paths = [m.get("path") for m in doc.get("mods") or [] if m.get("id") == NR]
        c["mods_staged"] = mods == ["PZTestKit", NR] and paths == [STAGE_MOD]
        c["nutrition_false"] = sb.get("Nutrition") is False
        c["day_length"] = sb.get("DayLength") == MOD_DAY_LENGTH
        c["verify_version"] = sum(1 for v in ver if v.get("args") == f"{NR}.version") >= 2
    return c


def preboot(key, profile_name, prefix, driver_file, repo=REPO):
    """The pre-boot checks, offline: the driver's prefix, profile and file name its session (CLAUDE.md s5); no artifact
    of the prefix committed; the profile's TOML; the harness markers in the repository. Returns (checks, ok)."""
    import tomllib
    spec = SESSIONS[key]
    c = {"prefix": prefix == spec["prefix"], "profile": profile_name == spec["profile"],
         "driver_file": os.path.basename(driver_file).startswith(prefix + "_")}
    c["no_prior_artifact"] = not glob.glob(os.path.join(repo, "testing", "artifacts", prefix + "-*"))
    p = os.path.join(repo, "testing", "profiles", profile_name + ".toml")
    try:
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        doc = tomllib.loads(text)
        prof = profile_doc_checks(key, profile_name, doc, text)
    except (OSError, ValueError) as e:
        prof = {"profile_read": False, "error": f"{type(e).__name__}: {e}"}
    c["profile_checks"] = prof
    found, ok = harness_markers_ok(repo)
    c["harness_markers"] = ok
    c["harness_found"] = found
    good = all(v is True for k, v in c.items() if k not in ("profile_checks", "harness_found")) and \
        all(v is True for k, v in prof.items() if k != "error")
    return c, good


def chain_check(prev_run, key="V2b", repo=REPO):
    """A chained session's previous run (V2b after V2a), offline: its run folder (an id under testing/runs or a path)
    holds the server cache to boot again and its own artifact, whose run id carries the previous prefix, which reads no
    error, abort, dead bus, budget stop, phase error or unrun action, whose phase X read the anchor and reached the
    anchor plus V2_SPLIT_H (re-review N-1: a short x443a would lose a tin from the 36-hour line). Returns
    (checks, ok)."""
    src = SESSIONS[SESSIONS[key]["chain_from"]]
    c = {"prev_run": prev_run}
    if not prev_run:
        c["why"] = "no previous run named (the driver takes x443a's run id or folder as its first argument)"
        return c, False
    d = prev_run if os.path.isdir(str(prev_run)) else os.path.join(repo, "testing", "runs", str(prev_run))
    c["dir"] = d
    c["dir_ok"] = os.path.isdir(d)
    c["server_cache"] = os.path.isdir(os.path.join(d, "server", "Server"))
    doc = None
    try:
        with open(os.path.join(d, src["artifact"]), encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as e:
        c["artifact_error"] = f"{type(e).__name__}: {e}"
    c["artifact"] = isinstance(doc, dict)
    doc = doc if isinstance(doc, dict) else {}
    c["run_id"] = doc.get("run_id")
    c["prefix_ok"] = str(doc.get("run_id") or "").startswith(src["prefix"] + "-")
    # bus_dead is written by xlib.Xs.finish (out["bus_dead"] = the tag the bus died after, else None)
    c["clean"] = not doc.get("error") and not doc.get("abort") and not doc.get("bus_dead")
    c["no_budget_stop"] = not doc.get("budget_stop")
    c["no_phase_errors"] = not doc.get("phase_errors")
    c["no_unrun"] = not doc.get("unrun")
    c["anchor"] = num(g(doc, "checks", "X", "anchor"))
    c["prev_reached"] = num(g(doc, "checks", "X", "reached"))
    c["reached_split"] = (c["anchor"] is not None and c["prev_reached"] is not None
                          and c["prev_reached"] >= c["anchor"] + V2_SPLIT_H - 1e-9)
    ok = all(c[k] for k in ("dir_ok", "server_cache", "artifact", "prefix_ok", "clean", "no_budget_stop",
                            "no_phase_errors", "no_unrun", "reached_split"))
    return c, ok


def staged_gate(out, git_say, git_dirty, repo=REPO, stage_root=STAGE_ROOT, stage_mod=STAGE_MOD):
    """x43c's: the staged copy's MANIFEST and tree against release_pack.manifest() of a clean mod/ (xlib.manifest_gate),
    and the staged NR_Core.lua's version."""
    import release_pack as RP
    mg = out["manifest_gate"] = X.manifest_gate(RP, repo, MOD_DIR, stage_root, stage_mod, MANIFEST_NAME, git_say,
                                                git_dirty)
    try:
        with open(os.path.join(repo, stage_mod, *STAGED_CORE.split("/")), encoding="utf-8") as fh:
            m = re.search(r'version\s*=\s*"([^"]+)"', fh.read())
        mg["staged_version"] = m.group(1) if m else None
    except OSError as e:
        mg["staged_version_error"] = f"{type(e).__name__}: {e}"
    return mg


def keep_server_log(log_path, run_dir, copied):
    """x43c's: the server log is named for the artifact copy, never copied onto itself."""
    dst = os.path.join(run_dir, "server-stdout.log")
    if os.path.abspath(log_path) != os.path.abspath(dst):
        shutil.copyfile(log_path, dst)
    copied.append("server-stdout.log")


# ================================================================ the session
class Sess:
    """One session's scenario over an xlib.Xs; every wait goes through xs.clock and xs.sleep, so the tests run it
    fast."""

    def __init__(self, xs, key, run_dir=None):
        self.xs = xs
        self.out = xs.out
        self.key = key
        self.spec = SESSIONS[key]
        self.D = self.out.setdefault("checks", {})
        self.run_dir = run_dir
        self.a0 = None
        self.start = None
        self.settings = None
        self.events = []                    # the model's events (vanilla), t_h from a0
        self.writes = []
        self.reads = {}
        self.eats, self.drinks = [], []
        self.speeds = self.out.setdefault("speeds", [])
        self.cur_speed = None
        self.restore_to = None
        self.anchor = None                  # V2's anchor age (V2b: off x443a's artifact)
        self.dead = False
        self.gone = False
        self.death = None
        self.pages = []

    # -- plumbing
    def k(self, tag, side, cmd, args="", log=True):
        return self.xs.keep(self.xs.step(tag, side, cmd, args, log=log))

    def lread(self, tag, side, root, paths, log=True):
        return self.k(tag, side, "lua.read", " ".join([root] + list(paths)), log=log)

    def sleep_until(self, t_end):
        while self.xs.clock() < t_end:
            self.xs.check()
            self.xs.sleep(min(POLL_S, max(0.0, t_end - self.xs.clock())))

    def poll(self, tag, fn, cap_s, sleep_s=POLL_S):
        end = self.xs.clock() + cap_s
        n, done, last = 0, False, None
        while True:
            done, last = fn()
            n += 1
            if done or self.xs.clock() >= end:
                break
            self.xs.check()
            self.xs.sleep(sleep_s)
        if not done:
            self.xs.note(f"{tag}: not reached inside {cap_s} s")
        return {"done": done, "last": last, "polls": n}

    def closing(self, fn):
        """A closing phase, chosen by its function, never by its letter (re-review R-1: V3 names an arm C): the clock
        restore, the ring read and the mod's error read."""
        return fn in (self.restore_clock, self.phase_R, self.m_Z)

    def body_run(self, phases):
        """Each phase through xs.run_phase; once the budget stopped a phase, only the closing phases (Sess.closing)
        still run and each later scenario phase is skipped with a note (review M-12: a scenario phase writes before its
        first check). The first budget stop stays the artifact's `budget_stop`; any later one is listed in
        `budget_stops` (re-review R-1)."""
        for name, fn in phases:
            if self.xs.parked():
                self.out["abort"] = f"admin parked in the debugger before phase {name}"
                break
            first = self.out.get("budget_stop")
            if first and not self.closing(fn):
                self.out.setdefault("skipped_phases", []).append(name)
                self.xs.note(f"phase {name} skipped: the budget stopped an earlier phase")
                continue
            self.xs.run_phase(name, fn)
            now = self.out.get("budget_stop")
            if now is not None and now is not first:
                self.out.setdefault("budget_stops", []).append(now)
                if first is not None:
                    self.out["budget_stop"] = first

    def read(self, kind, row):
        self.reads.setdefault(kind, []).append(row)
        return row

    # -- the clock
    def snap(self, tag, log=True):
        return self.xs.snap(tag, log=log)

    def age(self, tag="age"):
        return num(self.snap(tag, log=False).get("worldAge"))

    def speed(self, n, tag):
        """RCON settimespeed n; time.multiplier n only when the RCON command fails; the trueMult read after,
        recorded."""
        r = self.xs.rcon(f"settimespeed {int(n)}", tag)
        row = {"want": n, "rcon_ok": r.get("ok")}
        if not r.get("ok"):
            row["fallback"] = self.k(tag + "_mult", SRV, "time.multiplier", fmtnum(n)).get("raw")
        s = self.snap(tag + "_t")
        row.update({"trueMult": num(s.get("trueMult")), "mult": num(s.get("mult")), "age": num(s.get("worldAge")),
                    "wall": s.get("wall"), "tag": tag, "unit": SPEED_UNIT})
        row["ok"] = row["trueMult"] is not None and abs(row["trueMult"] - n) < 1e-6
        if not row["ok"]:
            self.xs.note(f"speed {tag}: trueMult {row['trueMult']} after settimespeed {n} ({SPEED_UNIT})")
        self.speeds.append(row)
        self.cur_speed = n
        return row

    def set_speed(self, n, tag):
        if self.cur_speed != n:
            self.speed(n, tag)

    def clock_read(self, tag="S_clock"):
        s = self.snap(tag)
        self.restore_to = num(s.get("trueMult"))
        return s

    def restore_clock(self):
        """Phase C: the clock back to the trueMult read at phase S (an integer speed through RCON, else
        time.multiplier), read back."""
        v = self.restore_to
        row = {"restore_to": v}
        if v is None:
            self.xs.note("restore: the start's trueMult is unread; restored to speed 1")
            v = 1.0
        if abs(v - round(v)) < 1e-6 and round(v) >= 1:
            row["set"] = self.speed(int(round(v)), "C_restore")
        else:
            row["set"] = {"reply": self.k("C_restore_mult", SRV, "time.multiplier", fmtnum(v)).get("raw")}
        s = self.snap("C_restore_t")
        row["unit"] = SPEED_UNIT
        row["trueMult_after"] = num(s.get("trueMult"))
        row["ok"] = row["trueMult_after"] is not None and abs(row["trueMult_after"] - v) <= 1e-6 * max(1.0, v)
        self.D["restore"] = row

    def run_to(self, end_age, actions, fast, tag):
        """At speed `fast` to end_age. actions [(age, kind, fn)], kind "timed" (the clock drops to speed 1 at the age
        minus LEAD_MIN, fn(age) runs at once, then the clock returns to fast) or "read" (fn(age) at its age, at the
        current speed). Stops at end_age, a death, the player gone from the online list, or the budget (Budget
        propagates). Actions still pending at the stop are noted and listed in out["unrun"]. Returns the last age
        read."""
        pending = sorted(actions, key=lambda x: x[0])
        a = None
        try:
            a = self._run_loop(end_age, pending, fast, tag)
        finally:
            if pending:
                left = [{"tag": tag, "age": at, "kind": kind} for at, kind, _fn in pending]
                self.out.setdefault("unrun", []).extend(left)
                self.xs.note(f"run_to {tag}: {len(left)} action(s) never ran (stopped at age {a})")
        return a

    def _run_loop(self, end_age, pending, fast, tag):
        self.set_speed(fast, f"{tag}_fast")
        a = None
        while True:
            self.xs.check()
            a = self.age(tag + "_a")
            if a is None:
                self.xs.sleep(POLL_S)
                continue
            ran = False
            while pending and not self.stopped():
                at, kind, fn = pending[0]
                lead = LEAD_MIN / 60.0 if kind == "timed" else 0.0
                if a < at - lead:
                    break
                pending.pop(0)
                if kind == "timed":
                    self.set_speed(1, f"{tag}_one")
                fn(a)
                if kind == "timed" and not self.stopped():
                    self.set_speed(fast, f"{tag}_fast")
                ran = True
                a = self.age(tag + "_a2") or a
            if self.stopped() or a >= end_age:
                break
            if not ran:
                self.xs.sleep(POLL_S)
        return a

    def stopped(self):
        return self.dead or self.gone

    # -- reads
    def stats_get(self, tag, log=True):
        a = self.k(tag, SRV, "stats.get", USER, log=log)
        row = {k: a.get(k) for k in STATS_GET_KEYS}
        row["traitList"] = a.get("traitList")
        row["error"] = a.get("error")
        return row

    def stats_all(self, tag, log=True):
        return self.k(tag, SRV, "stats.all", USER, log=log)

    def nutrition(self, tag):
        """The hourly store read (the map's nutrition.get fields) through stats.get, whose reply carries the same
        Nutrition fields and the server's own world age in one tick, so the graded value and its age cannot skew."""
        a = self.k(tag, SRV, "stats.get", USER)
        row = {k: num(a.get(k)) for k in ("calories", "carbs", "lipids", "proteins", "weight", "hunger", "thirst")}
        row["age"] = num(a.get("worldAge"))
        return self.read("nutrition", row)

    def health(self, tag):
        a = self.k(tag, SRV, "health.get", USER, log=False)
        s = self.snap(tag + "_t", log=False)
        return {"overall": num(a.get("overall")), "health": num(a.get("health")), "age": num(s.get("worldAge")),
                "ok": a.get("ok"), "reason": a.get("reason"), "raw": a.get("raw")}

    def moodle(self, tag, name, age=None):
        a = self.k(tag, SRV, "moodle.level", f"{USER} {name}", log=False)
        return {"moodle": name, "level": num(a.get("level")), "age": age, "ok": a.get("ok"), "reason": a.get("reason")}

    def perk_xp(self, tag):
        a = self.k(tag, SRV, "perk.xp", f"{USER} Strength")
        return {"xp": num(a.get("xp")), "level": num(a.get("level")), "worldAge": num(a.get("serverWorldAge")),
                "error": a.get("error")}

    def dead_check(self, tag):
        """isDead (witness.chain) and the overall health (health.get, the fallback at 0). Both handlers answer the
        string "no online player <user>" once the player has left the online list: then the row is `gone`, the run
        stops and V1b_death is unmeasured, never "alive past" (review M-1; #3278 read isDead true while the player
        was still found)."""
        d = self.k(tag + "_dead", SRV, "witness.chain", f"{USER} isDead", log=False)
        h = self.health(tag + "_hp")
        dead = str(d.get("value")).lower() == "true" or (h["overall"] is not None and h["overall"] <= 0.0)
        gone = all(str(x or "").startswith("no online player") for x in (d.get("raw"), h.get("raw")))
        row = {"dead": dead, "dead_raw": d.get("value"), "dead_error": d.get("error"), "overall": h["overall"],
               "age": h["age"], "gone": gone}
        self.read("health", row)
        if gone and not self.gone:
            self.gone = True
            self.xs.note("admin left the online list: the death read is unmeasured")
        if dead and not self.dead:
            self.dead = True
            self.death = row
            self.xs.note(f"admin read dead at age {row['age']}")
        return row

    def start_read(self, tag="S_start", strength=False):
        """The model's start: stats.get, health.get, stats.all and (strength) perk.xp Strength in one sequence; a0 is
        the stats.get's own server age."""
        st = self.stats_get(tag + "_stats")
        h = self.health(tag + "_health")
        sa = self.stats_all(tag + "_all")
        xp = self.perk_xp(tag + "_xp") if strength else None
        row = {"stats": st, "health": h, "stats_all": sa, "xp": xp}
        self.a0 = num(st.get("worldAge"))
        self.start = start_state(st, h, sa, xp)
        self.D["start"] = row
        return row

    def settings_read(self, tag="S_sv"):
        keys = ("SandboxVars.Nutrition", "SandboxVars.DayLength", "SandboxVars.StatsDecrease",
                "SandboxVars.MultiplierConfig.Global", "SandboxVars.MultiplierConfig.GlobalToggle",
                "SandboxVars.MultiplierConfig.Strength")
        return vals(self.lread(tag, SRV, "_G", keys))

    def model_settings(self, sv, traits):
        dl = num(sv.get("SandboxVars.DayLength"))
        sd = num(sv.get("SandboxVars.StatsDecrease"))
        out = {"day_length_min": DAY_LENGTH_MIN.get(int(dl)) if dl is not None else None,
               "stats_decrease": int(sd) if sd is not None else None, "appetite": appetite_of(traits),
               "sleep_allowed": bool(self.spec["sleep"]), "xp_multiplier": 1.0}
        unread = [k for k in ("day_length_min", "stats_decrease") if out[k] is None]
        if unread:
            self.xs.note(f"settings unread: {unread}; the model takes its defaults (DayLength 4, StatsDecrease 3)")
        for k, dflt in (("day_length_min", 90.0), ("stats_decrease", 3)):
            if out[k] is None:
                out[k] = dflt
        return out

    # -- writes and events
    def write(self, tag, cmd, args, keys):
        """stats.set or nutrition.set bracketed by two age reads; the read-back of `keys` is the model's write at the
        brackets' mean age."""
        b0 = self.age(tag + "_a0")
        r = self.k(tag, SRV, cmd, f"{USER} {args}")
        b1 = self.age(tag + "_a1")
        v = {k: num(r.get(k)) for k in keys}
        row = {"tag": tag, "cmd": cmd, "args": args, "values": v, "ages": [b0, b1], "applied": r.get("applied")}
        self.writes.append(row)
        if b0 is not None and b1 is not None and self.a0 is not None and all(x is not None for x in v.values()):
            self.events.append({"t_h": (b0 + b1) / 2.0 - self.a0, "kind": "set", "values": v, "label": tag})
        else:
            self.xs.note(f"write {tag}: a bracket or a read-back is missing; no model write")
        return row

    def spawn(self, full, n, tag):
        row = self.xs.spawn(full, n, tag)
        self.D.setdefault("spawns", []).append(row)
        return row

    def eat(self, full, label):
        """eat.action <full> 1 (no foodtimer.set); landed at the first stats.get poll whose calorie store rose by half
        the item's kcal, or whose HUNGER fell by half of min(the item's hunger, HUNGER before), or whose food timer rose
        by TIMER_TOL (the store clamps at 3700, VM7, so near the cap the calories alone would never move)."""
        row = {"label": label, "food": full, "landed": False}
        self.eats.append(row)
        b = self.stats_get(label + "_b")
        row["before"] = b
        q = self.k(label + "_eat", CLI, "eat.action", f"{full} 1")
        row["queued"] = {k: q.get(k) for k in ("queued", "fraction", "spawned", "itemId", "validStart", "maxTime",
                                               "moodleFoodEaten", "error", "raw", "wall")}
        self.xs.spawned_stop(q, label)
        kcal = VANILLA_FOODS[full]["calories"]
        hc = abs(VANILLA_FOODS[full]["hunger_script"]) / 100.0
        prev = {"age": num(b.get("worldAge"))}

        def fn():
            a = self.stats_get(label + "_poll", log=False)
            c0, c1 = num(b.get("calories")), num(a.get("calories"))
            h0, h1 = num(b.get("hunger")), num(a.get("hunger"))
            t0, t1 = num(b.get("foodTimer")), num(a.get("foodTimer"))
            sig = {"calories": c0 is not None and c1 is not None and c1 - c0 >= 0.5 * kcal,
                   "hunger": h0 is not None and h1 is not None and h0 > FREEZE_EPS and h0 - h1 >= 0.5 * min(hc, h0),
                   "timer": t0 is not None and t1 is not None and t1 - t0 >= TIMER_TOL}
            done = any(sig.values())
            if done:
                row["landed_by"] = sorted(k for k, v in sig.items() if v)
            else:
                prev["age"] = num(a.get("worldAge"))
            return done, a
        p = self.poll(label + "_land", fn, EAT_CAP_S)
        row["landed"] = p["done"]
        row["after"] = p["last"]
        a1 = num((p["last"] or {}).get("worldAge"))
        if p["done"] and a1 is not None and self.a0 is not None:
            a_ev = (prev["age"] + a1) / 2.0 if prev["age"] is not None else a1
            row["landed_age"] = a_ev
            f = VANILLA_FOODS[full]
            self.events.append({"t_h": a_ev - self.a0, "kind": "eat", "hunger_script": f["hunger_script"],
                                "calories": f["calories"], "carbs": f["carbs"], "lipids": f["lipids"],
                                "proteins": f["proteins"], "label": label})
        return row

    def drink(self, container, fluid, litres, label, stat, sign, expect):
        """A vanilla drink: the container's server copy filled with `litres` of `fluid` (fluid.fill; None keeps the
        prefilled can), autodrink.probe before; drink.action <container> 1; `stat` (stats.all) polled until it has
        moved by MOVED_SHARE of `expect` in direction `sign` and then held for SETTLE_POLLS polls; the probe after. The
        model's
        drink sits at the midpoint of the first moved poll and the settle."""
        row = {"label": label, "container": container, "fluid": fluid, "landed": False}
        self.drinks.append(row)
        if fluid is not None:
            row["fill"] = self.k(label + "_fill", SRV, "fluid.fill", f"{USER} {container} {fluid} {litres}")
        row["probe_before"] = self.k(label + "_probe0", SRV, "autodrink.probe", USER)
        self.fill_gate(row, container, fluid)
        b = self.stats_all(label + "_b")
        row["before"] = {"value": stat_of(b, stat), "worldAge": num(b.get("worldAge"))}
        q = self.k(label + "_drink", CLI, "drink.action", f"{container} 1")
        row["queued"] = {k: q.get(k) for k in ("queued", "percentage", "spawned", "itemId", "filledRatioBefore",
                                               "error", "raw", "wall")}
        self.xs.spawned_stop(q, label)
        v0 = row["before"]["value"]
        polls = []
        state = {"moved": None, "still": 0, "last": v0}

        def fn():
            a = self.stats_all(label + "_poll", log=False)
            v, age = stat_of(a, stat), num(a.get("worldAge"))
            polls.append({"age": age, "value": v})
            if v is None or v0 is None:
                return False, a
            if state["moved"] is None and sign * (v - v0) >= MOVED_SHARE * abs(expect):
                state["moved"] = age
            elif state["moved"] is not None:
                state["still"] = state["still"] + 1 if abs(v - state["last"]) < 1e-9 or sign * (v - state["last"]) < 0 \
                    else 0
            state["last"] = v
            return state["moved"] is not None and state["still"] >= SETTLE_POLLS, a
        p = self.poll(label + "_land", fn, DRINK_CAP_S)
        row["polls"] = polls
        row["landed"] = state["moved"] is not None
        row["settled"] = p["done"]
        row["probe_after"] = self.k(label + "_probe1", SRV, "autodrink.probe", USER)
        l0 = num(g(row, "fill", "litres")) if fluid is not None else num(g(row, "probe_before", "litres"))
        l1 = num(g(row, "probe_after", "litres")) if g(row, "probe_after", "item") == container else 0.0
        row["drunk"] = (l0 - l1) if (l0 is not None and l1 is not None) else None
        settle_age = polls[-1]["age"] if polls else None
        if row["landed"] and not row["fill_ok"]:
            self.xs.note(f"drink {label}: landed but its fill gate failed; no model event")
        if row["landed"] and row["fill_ok"] and self.a0 is not None:
            a_ev = (state["moved"] + settle_age) / 2.0 if settle_age is not None else state["moved"]
            row["event_age"] = a_ev
            row["first_moved_age"] = state["moved"]
            row["settle_age"] = settle_age
            lit = row["drunk"] if (row["drunk"] is not None and row["drunk"] > 0) else litres
            row["model_litres"] = lit
            self.events.append({"t_h": a_ev - self.a0, "kind": "drink", "litres": lit,
                                "fluid": {"Coffee": "coffee", "Beer": "beer", None: "beer"}[fluid], "label": label})
        return row

    def fill_gate(self, row, container, fluid):
        """Review M-2: fluid.fill's ok and read-back fluid, and the probe's first non-empty container and its fluid, all
        the drink's own; a miss is noted and the drink leaves the model (vanilla) or the replay (modded)."""
        fill = row.get("fill") or {}
        pb = row.get("probe_before") or {}
        want = str(fluid or "").lower()
        row["fill_ok"] = (fill.get("ok") is True and str(fill.get("fluid", "")).lower() == want
                          and pb.get("item") == container and str(pb.get("fluid", "")).lower() == want)
        if not row["fill_ok"]:
            self.xs.note(f"drink {row.get('label')}: fill gate failed (fill {fill.get('ok')}/{fill.get('fluid')}, "
                         f"probe {pb.get('item')}/{pb.get('fluid')})")
        return row["fill_ok"]

    def probe_start(self, P):
        """Review M-13: the start's first non-empty fluid container (the auto-drink rule); a carried one is noted."""
        P["probe"] = self.k("S_probe", SRV, "autodrink.probe", USER)
        if P["probe"].get("item") is not None:
            self.xs.note(f"S: admin carries a filled container {P['probe'].get('item')} "
                         f"({P['probe'].get('litres')} L {P['probe'].get('fluid')})")

    # -- the ring
    def ring_start(self, paths=(), tag="S_ring"):
        r = self.k(tag, SRV, "minute.ring", " ".join([USER, "start"] + list(paths)))
        self.D["ring_start"] = r
        return r

    def read_pages(self, tag, start_from=None):
        """x36's: every page from start_from on, each result doc waited for and copied into the run folder."""
        pages, frm = [], start_from
        for _ in range(12):
            after = self.xs.clock() - 1.0
            args = f"{USER} read" + ("" if frm is None else f" {frm}")
            r = self.k(f"{tag}_read", SRV, "minute.ring", args)
            pg = {"reply": {k: r.get(k) for k in ("ok", "from", "rows", "skipped", "next", "more", "oldest", "newest",
                                                  "recorded", "overwritten", "errors", "lastError", "result")}}
            name = r.get("result")
            if isinstance(name, str) and name and self.xs.server is not None:
                doc = self.xs.wait_doc(name, after)
                pg["doc_rows"] = len((doc or {}).get("rows_list") or [])
                src = os.path.join(self.xs.server.bus.results_dir, name + ".json")
                if doc is not None and os.path.isfile(src) and self.run_dir:
                    dst = os.path.join(self.run_dir, name + ".json")
                    if os.path.abspath(src) != os.path.abspath(dst):        # never onto itself (x43's SameFileError)
                        shutil.copyfile(src, dst)
                    self.xs.copied.append(name + ".json")
                    pg["file"] = name + ".json"
            pages.append(pg)
            if not r.get("ok") or not r.get("more") or r.get("next") is None:
                break
            frm = r.get("next")
        return pages

    def phase_R(self):
        P = self.D["R"] = {}
        P["pages"] = self.read_pages("R")
        P["stop"] = self.k("R_ring_stop", SRV, "minute.ring", f"{USER} stop")
        self.pages = [p.get("file") for p in P["pages"] if p.get("file")]

    def ring_rows(self):
        rows = {}
        for f in self.pages:
            try:
                with open(os.path.join(self.run_dir, f), encoding="utf-8") as fh:
                    doc = json.load(fh)
            except (OSError, ValueError):
                continue
            for r in doc.get("rows_list") or []:
                rows[r["s"]] = r
        return [rows[s] for s in sorted(rows)]

    # ======================================================== the vanilla phase S
    def phase_S(self, strength=False):
        P = self.D["S"] = {}
        P["players"] = self.xs.step("S_players", SRV, "players")["ack"]
        P["sandbox"] = self.settings_read()
        P["clock"] = self.clock_read()
        P["ring"] = self.ring_start()
        self.probe_start(P)
        P["start"] = self.start_read(strength=strength)
        traits = traits_of(g(P, "start", "stats"))
        P["traits"] = traits
        self.settings = self.model_settings(P["sandbox"], traits)
        P["settings"] = self.settings

    # ======================================================== V1a: a measured meal
    def v1a_body(self):
        return (("S", self.v1a_S), ("A", self.v1a_A), ("B", self.v1a_B), ("C", self.restore_clock),
                ("R", self.phase_R))

    def v1a_S(self):
        self.phase_S()
        self.spawn(BOLOGNESE, 2, "S_spawn")

    def hourly(self, a_from, a_to, fn, every=1.0):
        out = []
        t = math.floor(a_from / every + 1e-9) * every + every
        while t < a_to - 1e-9:
            out.append((t, "read", fn))
            t += every
        return out

    def v1a_A(self):
        A = self.D["A"] = {}
        self.set_speed(1, "A_one")
        A["write"] = self.write("A_set", "stats.set", f"hunger {V1A_HUNGER_A} thirst 0", ("hunger", "thirst"))
        A["eat"] = self.eat(BOLOGNESE, "A_eat")
        A["timer_after"] = self.stats_get("A_timer")
        self.read("timer", {"age": num(A["timer_after"].get("worldAge")),
                            "foodTimer": num(A["timer_after"].get("foodTimer")), "arm": "A"})
        a = self.age("A_a")
        A["end_age"] = (A["eat"].get("landed_age") or a) + V1A_ARM_A_H
        A["reached"] = self.run_to(A["end_age"], self.hourly(a, A["end_age"], lambda x: self.nutrition("A_nut")),
                                   SPEED_FAST, "A")

    def v1a_B(self):
        B = self.D["B"] = {}
        n0 = len(self.speeds)
        self.set_speed(1, "B_one")
        B["write"] = self.write("B_set", "stats.set", f"hunger {V1A_HUNGER_B}", ("hunger",))
        B["eat"] = self.eat(BOLOGNESE, "B_eat")
        t_end = (B["eat"].get("landed_age") or self.age("B_a0") or 0.0) + V1A_TIMER_WINDOW_M / 60.0
        polls = 0
        while True:
            self.xs.check()
            st = self.stats_get("B_timer", log=False)
            age = num(st.get("worldAge"))
            m = self.moodle("B_moodle", MOODLE_FOOD_EATEN, age)
            self.read("timer", {"age": age, "foodTimer": num(st.get("foodTimer")),
                                "standardFoodTime": num(st.get("standardFoodTime")), "hunger": num(st.get("hunger")),
                                "arm": "B"})
            self.read("food_eaten", m)
            polls += 1
            if age is None or age >= t_end:
                break
            self.sleep_until(self.xs.clock() + V1A_TIMER_EVERY_S)
        B["timer_polls"] = polls
        rows = self.speeds[n0:]
        B["slow_rows"] = rows
        B["slow_ok"] = self.cur_speed == 1 and all(r.get("ok") for r in rows) and \
            (bool(rows) or bool(self.speeds) and self.speeds[-1].get("ok"))
        a = self.age("B_a")
        B["end_age"] = (B["eat"].get("landed_age") or a) + V1A_ARM_B_H
        B["reached"] = self.run_to(B["end_age"], self.hourly(a, B["end_age"], lambda x: self.nutrition("B_nut")),
                                   SPEED_FAST, "B")

    # ======================================================== V1b: starving to death
    def v1b_body(self):
        return (("S", self.v1b_S), ("X", self.v1b_X), ("C", self.restore_clock), ("R", self.phase_R))

    def v1b_S(self):
        self.phase_S()

    def v1b_hour(self, a):
        if self.dead:
            return
        self.write(f"X_thirst_{a:.2f}", "stats.set", "thirst 0", ("thirst",))
        self.nutrition(f"X_nut_{a:.2f}")
        m = self.moodle(f"X_hungry_{a:.2f}", MOODLE_HUNGRY, self.age(f"X_hungry_{a:.2f}_t"))
        self.read("hungry", m)

    def v1b_X(self):
        P = self.D["X"] = {}
        self.set_speed(1, "X_one")
        P["write"] = self.write("X_set", "stats.set", f"hunger {V1B_HUNGER} thirst 0", ("hunger", "thirst"))
        a = self.age("X_a0")
        end = a + V1B_CAP_H
        acts = self.hourly(a, end, self.v1b_hour)
        acts += self.hourly(a, end, lambda x: self.dead_check(f"X_d_{x:.2f}"), V1B_HEALTH_EVERY_H)
        P["end_cap"] = end
        P["reached"] = self.run_to(end, acts, SPEED_FAST, "X")
        P["dead"] = self.dead
        P["death"] = self.death

    # ======================================================== V2: one food for 36 hours
    def v2_half(self):
        return (0.0, V2_SPLIT_H) if self.key == "V2a" else (V2_SPLIT_H, V2_SPAN_H)

    def v2_body(self):
        return (("S", self.v2_S), ("X", self.v2_X), ("C", self.restore_clock), ("R", self.phase_R))

    def v2_S(self):
        self.phase_S()
        lo, hi = self.v2_half()
        self.spawn(TUNA, sum(1 for o in V2_EAT_OFFSETS if lo <= o < hi), "S_spawn")

    def v2_X(self):
        """V2a: the store written (calories 3000, weight 80; the values read first kept), the anchor read, then the
        first V2_SPLIT_H game hours. V2b: x443a's anchor (main's chain check, off its artifact), then on to the anchor
        plus V2_SPAN_H. A tin's age is the anchor plus its offset (a tin already past is eaten at once, named late)."""
        P = self.D["X"] = {}
        self.set_speed(1, "X_one")
        lo, hi = self.v2_half()
        if self.key == "V2a":
            P["read_first"] = {k: g(self.D, "start", "stats", k) for k in ("calories", "weight")}
            P["calories"] = self.write("X_cal", "nutrition.set", f"calories {V2_CALORIES!r}", ("calories", "weight"))
            P["weight"] = self.write("X_wt", "nutrition.set", f"weight {V2_WEIGHT!r}", ("calories", "weight"))
            self.out["world_changes"]["left_in_place"].append(
                f"nutrition.set calories {V2_CALORIES} and weight {V2_WEIGHT} (read first: {P['read_first']})")
            self.anchor = self.age("X_anchor")
        P["anchor"] = self.anchor
        if self.anchor is None:
            self.xs.note("X: no anchor age; the scenario is not run")
            return
        a = self.age("X_a0") or self.anchor
        acts, late = [], []
        for i, off in enumerate(V2_EAT_OFFSETS):
            if not (lo <= off < hi):
                continue
            ea = self.anchor + off
            if a is not None and ea < a:
                late.append(ea)
            acts.append((ea if a is None else max(ea, a), "timed", (lambda x, i=i: self.eat(TUNA, f"X_eat{i + 1}"))))
        end = self.anchor + hi
        acts += self.hourly(a, end, lambda x: self.nutrition(f"X_nut_{x:.2f}"))
        t = V2_THIRST_EVERY_H
        while t < V2_SPAN_H:
            if lo < t < hi and self.anchor + t > a:
                acts.append((self.anchor + t, "read", (lambda x: self.write(f"X_thirst_{x:.2f}", "stats.set",
                                                                            "thirst 0", ("thirst",)))))
            t += V2_THIRST_EVERY_H
        P["late_eats"] = late
        P["end_age"] = end
        P["reached"] = self.run_to(end, acts, SPEED_FAST, "X")
        self.nutrition("X_nut_end")

    # ======================================================== V3: Strength experience
    def v3_body(self):
        return (("S", self.v3_S), ("A", lambda: self.v3_set("A")), ("B", lambda: self.v3_set("B")),
                ("C", lambda: self.v3_set("C")), ("Z", self.restore_clock), ("R", self.phase_R))

    def v3_S(self):
        self.phase_S(strength=True)
        self.D["S"]["fitness"] = self.k("S_fit", SRV, "perk.xp", f"{USER} Fitness")
        self.set_speed(1, "S_one")

    def exe(self, tag):
        r = self.k(tag, SRV, "witness.chain", f"{USER} getFitness.getCurrentExe", log=False)
        v = r.get("value")
        return {"wall": r.get("wall"), "value": v, "on": v not in (None, "nil", "") and r.get("ok") is not False}

    def pushup_set(self, w, tag):
        """x42c's set: endurance 1, exercise.do pushups, the server's exercise flag polled until it clears by itself
        (the set ends at exhaustion) or SET_CAP_S (then action.cancel), then the flag's clear waited for."""
        w["rest"] = self.k(tag + "_rest", SRV, "stats.set", f"{USER} endurance 1")
        w["xp_before"] = self.perk_xp(tag + "_xp0")
        a0 = self.age(tag + "_t0")
        w["ask"] = self.k(tag + "_ask", CLI, "exercise.do", f"pushups {PUSHUP_ASK_M}")
        t_ask = self.xs.clock()
        w["exe_seen"], first, last = False, None, None
        while True:
            e = self.exe(tag + "_exe")
            if e["on"]:
                w["exe_seen"] = True
                last = e["wall"]
                first = first if first is not None else e["wall"]
            elif w["exe_seen"]:
                w["stop_reason"] = "ended"
                break
            elif self.xs.clock() - t_ask > SET_START_CAP_S:
                w["stop_reason"] = "never_started"
                break
            if self.xs.clock() - t_ask > SET_CAP_S:
                w["stop_reason"] = "cap"
                break
            self.sleep_until(self.xs.clock() + POLL_S * 2)
        if w["stop_reason"] in ("cap", "never_started"):
            w["cancel"] = self.k(tag + "_cancel", CLI, "action.cancel")
            w["cleared"] = self.poll(tag + "_clear", lambda: (not self.exe(tag + "_clr")["on"], None),
                                     EXE_CLEAR_CAP_S)["done"]
        a1 = self.age(tag + "_t1")
        w["set_s"] = (last - first) if (first is not None and last is not None) else None
        w["ages"] = [a0, a1]
        self.sleep_until(self.xs.clock() + 1.0)
        w["xp_after"] = self.perk_xp(tag + "_xp1")
        w["label"] = tag
        if a0 is not None and self.a0 is not None:
            w["t_h"] = a0 - self.a0
            dur = ((a1 - a0) * 60.0) if a1 is not None else 0.0
            self.events.append({"t_h": w["t_h"], "kind": "exercise", "mode": "pushups", "reps": VM.REPS_PER_SET,
                                "sets": 1, "duration_min": max(0.0, dur), "label": tag})

    def v3_set(self, arm):
        w = self.D[arm] = {"arm": arm}
        prot = dict(V3_PROTEINS)[arm]
        if arm == "B":
            pa0 = self.age("B_park_a0")
            w["park"] = self.k("B_park", SRV, "perk.park", f"{USER} Strength {V3_PARK_LEVEL}")
            pa1 = self.age("B_park_a1")
            xa = num(w["park"].get("xpAfter"))
            if xa is not None and pa0 is not None and pa1 is not None:
                self.events.append({"t_h": (pa0 + pa1) / 2.0 - self.a0, "kind": "set", "values": {"strength_xp": xa},
                                    "label": "B_park"})
            w["xp_park"] = self.perk_xp("B_xp_park")
        w["protein"] = self.write(f"{arm}_protein", "nutrition.set", f"proteins {0.0 if arm == 'B' else prot!r}",
                                  ("proteins",))
        if arm == "B":
            ga0 = self.age("B_grant_a0")
            w["grant"] = self.k("B_grant", SRV, "xp.grant", f"{USER} Strength {V3_GRANT!r}")
            ga1 = self.age("B_grant_a1")
            if ga0 is not None and ga1 is not None:
                self.events.append({"t_h": (ga0 + ga1) / 2.0 - self.a0, "kind": "grant", "amount": V3_GRANT,
                                    "label": "B_grant"})
            w["xp_grant"] = self.perk_xp("B_xp_grant")
            w["protein2"] = self.write("B_protein2", "nutrition.set", f"proteins {prot!r}", ("proteins",))
        self.pushup_set(w, arm)
        if arm == "B":
            w["stats_after"] = self.stats_get("B_traits")

    # ======================================================== V4: coffee and beer
    def v4_body(self):
        return (("S", self.v4_S), ("A", self.v4_A), ("B", self.v4_B), ("C", self.restore_clock), ("R", self.phase_R))

    def v4_S(self):
        self.phase_S()
        self.set_speed(1, "S_one")
        self.D["S"]["thirst"] = self.write("S_thirst", "stats.set", "thirst 0", ("thirst",))   # review M-13

    def v4_A(self):
        A = self.D["A"] = {}
        A["write"] = self.write("A_fatigue", "stats.set", f"fatigue {V4_FATIGUE}", ())
        f = self.stats_get("A_fat0")
        if num(f.get("fatigue")) is not None and A["write"]["ages"][1] is not None:
            self.events.append({"t_h": num(f.get("worldAge")) - self.a0, "kind": "set",
                                "values": {"fatigue": num(f.get("fatigue"))}, "label": "A_fatigue_read"})
        A["spawn"] = self.spawn(BOTTLE, 1, "A_spawn")
        d = self.drink(BOTTLE, "Coffee", COFFEE_L, "A_coffee", "FATIGUE", -1, VM.COFFEE_FATIGUE_PER_L * COFFEE_L)
        c = {"landed": d["landed"], "drink": d, "fill_ok": d.get("fill_ok")}
        polls = d.get("polls") or []
        firstm = next((p for p in polls if p.get("age") == d.get("first_moved_age")), None)
        pre = [p for p in polls if d.get("first_moved_age") is not None and p.get("age") is not None
               and p["age"] < d["first_moved_age"]]
        c["before"] = {"fatigue": d["before"]["value"], "worldAge": d["before"]["worldAge"]}
        if pre:
            c["before"] = {"fatigue": pre[-1]["value"], "worldAge": pre[-1]["age"]}
        c["after"] = {"fatigue": polls[-1]["value"], "worldAge": polls[-1]["age"]} if (polls and firstm) else {}
        a = self.age("A_hold_a0")
        c["hold"], c["hold_h"] = [], V4_HOLD_H
        if a is not None:
            def hold_read(x):
                s = self.stats_get("A_hold", log=False)
                c["hold"].append({"age": num(s.get("worldAge")), "fatigue": num(s.get("fatigue"))})
            acts = []
            t = a + V4_HOLD_SLOW_M / 60.0
            step = 1.0 / 60.0
            u = a
            while u < a + V4_HOLD_H:
                acts.append((u, "read", hold_read))
                u += step if u < t else 5.0 / 60.0
            self.set_speed(1, "A_hold_one")
            self.run_to_mixed(a + V4_HOLD_H, acts, t)
        self.D["A"]["coffee"] = c

    def run_to_mixed(self, end_age, acts, fast_from):
        """At speed 1 until fast_from, then at SPEED_FAST to end_age, running each read action at its age."""
        slow = [x for x in acts if x[0] < fast_from]
        fast = [x for x in acts if x[0] >= fast_from]
        self.run_to(fast_from, slow, 1, "A_hold_s")
        self.run_to(end_age, fast, SPEED_FAST, "A_hold_f")
        self.set_speed(1, "A_hold_back")

    def v4_B(self):
        B = self.D["B"] = {"cans": []}
        self.set_speed(1, "B_one")
        for i, cont in enumerate(BEER_CONTAINERS[:V4_BEERS]):
            self.spawn(cont, 1, f"B_spawn{i + 1}")
            gain = VM.intoxication_gain(VM.BEER_ALCOHOL_PER_L * BEER_L, 0.0)
            d = self.drink(cont, "Beer", BEER_L, f"B_beer{i + 1}", "INTOXICATION", 1, gain)
            B["cans"].append({k: d.get(k) for k in ("landed", "settled", "event_age", "first_moved_age",
                                                    "settle_age", "drunk", "model_litres", "fill_ok")})
        polls = []
        a = self.age("B_p0")
        end = (a or 0.0) + V4_INTOX_CAP_H
        B["poll_end"] = end

        def fn():
            s = self.stats_all("B_intox", log=False)
            v, age = stat_of(s, "INTOXICATION"), num(s.get("worldAge"))
            polls.append({"age": age, "intox": v})
            return (v is not None and v <= 0.0) or (age is not None and age >= end), None
        self.poll("B_zero", fn, 600.0, V4_INTOX_EVERY_S)
        for d in self.drinks:
            for p in d.get("polls") or []:
                if d["label"].startswith("B_beer"):
                    polls.append({"age": p["age"], "intox": p["value"]})
        B["polls"] = sorted((p for p in polls if p.get("age") is not None), key=lambda p: p["age"])

    # ======================================================== the vanilla grades
    def scenario(self, end_age):
        """The model's scenario to the session's last read (V1b: on to the cap, so a death the session did not reach
        in time still has the model's age)."""
        hours = max(0.0, end_age - self.a0, V1B_CAP_H + 1.0 if self.key == "V1b" else 0.0) + 2.0 / 60.0
        return {"start": self.start, "settings": self.settings, "events": list(self.events), "hours": hours,
                "dt_min": MODEL_DT_MIN}

    def last_age(self):
        ages = [num(r.get("age")) for r in self.ring_rows()] + [num(r.get("age")) for k in self.reads
                                                                  for r in self.reads[k]]
        ages = [a for a in ages if a is not None]
        return max(ages) if ages else None

    def grade_vanilla(self):
        xs = self.xs
        self.out["reads"] = self.reads
        self.out["writes"] = self.writes
        self.out["eats"] = self.eats
        self.out["drinks"] = self.drinks
        if self.a0 is None or self.start is None:
            self.out["model_error"] = "no start read; nothing graded"
            return
        end = self.last_age() or self.a0
        scn = self.scenario(end)
        self.out["model_inputs"] = {"a0": self.a0, "scenario": scn, "tool": "tools/vanilla_model.py simulate, chained "
                                    "at each write by testing/experiments/x44_guide_lib.py model_chain"}
        model = model_chain(scn)
        rows = [r for r in self.ring_rows() if num(r.get("age")) is not None and r["age"] >= self.a0]
        ev_ages = [e["t_h"] + self.a0 for e in self.events]
        fn = getattr(self, "grade_" + self.key.lower())
        fn(model, rows, ev_ages)
        self.out["verdict_summary"] = {k: v.get("verdict") for k, v in self.out["verdicts"].items()}
        xs.persist()

    def _g(self, name, res, falsifier):
        v, o = res
        self.xs.grade(name, v, o, falsifier)

    def grade_v1a(self, model, rows, ev_ages):
        a0 = self.a0
        A, B = self.D.get("A") or {}, self.D.get("B") or {}
        ea, eb = g(A, "eat", "landed_age"), g(B, "eat", "landed_age")
        b_write = g(B, "write", "ages")
        a_end = (b_write[0] if b_write and b_write[0] is not None else A.get("end_age")) or a0
        if ea is not None:
            self._g("V1a_A_hunger", grade_curve(rows, model, "HUNGER", "hunger", a0, HUNGER_TOL, (ea, a_end), ev_ages),
                    "a ring HUNGER off the model by more than HUNGER_TOL in arm A (a freeze the model does not have)")
        else:
            self.xs.grade("V1a_A_hunger", "unmeasured", {"why": "arm A's eat never landed"}, "")
        ta = [r for r in self.reads.get("timer") or [] if r.get("arm") == "A"]
        self._g("V1a_A_timer", grade_reads(ta, model, "foodTimer", "food_timer", a0, TIMER_TOL),
                "the timer after arm A's eat off the model's (filled where the model's gate says no fill)")
        tb = [r for r in self.reads.get("timer") or [] if r.get("arm") == "B"]
        if B.get("slow_ok") is False:
            self.xs.grade("V1a_B_timer", "unmeasured", {"why": "arm B's window ran with a speed row not ok (its 10-s "
                                                               "cadence assumes speed 1)",
                                                        "slow_rows": B.get("slow_rows")}, "")
        else:
            self._g("V1a_B_timer", grade_reads(tb, model, "foodTimer", "food_timer", a0, TIMER_TOL),
                    "a timer read in arm B's 25 minutes off the model's fill and decay")
        fe = [dict(r, age=r.get("age")) for r in self.reads.get("food_eaten") or []]
        self._g("V1a_B_moodle", grade_levels(fe, model, "food_timer", VM.FOOD_EATEN_THRESHOLDS, a0),
                "a FoodEaten moodle level off the model's timer level")
        rb = [r for r in rows if eb is not None and r["age"] >= eb]
        self._g("V1a_B_freeze", grade_freeze(rb, eb, model, a0),
                "HUNGER rising inside the freeze, or the freeze ending off the model's 3120-unit timer")
        if eb is not None:
            self._g("V1a_B_hunger", grade_curve(rows, model, "HUNGER", "hunger", a0, HUNGER_TOL,
                                                (eb, B.get("end_age") or eb), ev_ages),
                    "a ring HUNGER off the model in arm B")
        else:
            self.xs.grade("V1a_B_hunger", "unmeasured", {"why": "arm B's eat never landed"}, "")
        self._g("V1a_thirst", grade_curve(rows, model, "THIRST", "thirst", a0, THIRST_TOL, (a0, 1e9), ev_ages),
                "a ring THIRST off the model by more than THIRST_TOL")
        self._g("V1a_calories", grade_reads(self.reads.get("nutrition"), model, "calories", "calories_store", a0,
                                            CAL_TOL, CAL_TOL_REL), "an hourly calorie store off the model's burn")

    def grade_v1b(self, model, rows, ev_ages):
        a0 = self.a0
        X_ = self.D.get("X") or {}
        w = X_.get("write") or {}
        start = (w.get("ages") or [None, None])[1] or a0
        end = (self.death or {}).get("age") or X_.get("reached") or 1e9
        self._g("V1b_hunger", grade_curve(rows, model, "HUNGER", "hunger", a0, HUNGER_TOL, (start, end), ev_ages),
                "a ring HUNGER off the model by more than HUNGER_TOL while starving")
        last_ring = max((r["age"] for r in rows), default=None)
        self._g("V1b_level4", grade_crossing(rows, model, "hunger", "HUNGER", V1B_HUNGRY_4, a0, LEVEL_TOL_H, start,
                                             last_ring),
                "HUNGER crossing 0.70 (HUNGRY 4) off the model's crossing by more than LEVEL_TOL_H")
        self._g("V1b_moodle", grade_levels(self.reads.get("hungry"), model, "hunger", VM.HUNGRY_THRESHOLDS, a0),
                "an hourly Hungry moodle level off the model's")
        hr = [{"age": r.get("age"), "overall": r.get("overall")} for r in self.reads.get("health") or []
              if not r.get("dead")]
        self._g("V1b_health", grade_reads(hr, model, "overall", "health", a0, HEALTH_TOL),
                "a health read off the model's VM10 drain (3.564 a game hour at HUNGRY 4) by more than HEALTH_TOL")
        hreads = self.reads.get("health") or []
        gone = bool(hreads) and bool(hreads[-1].get("gone"))
        self._g("V1b_death", grade_death(self.death, model, a0, X_.get("reached"), gone=gone),
                "death off the model's health-zero age by more than DEATH_TOL_H, or alive past it")
        nut = self.reads.get("nutrition")
        self._g("V1b_calories", grade_reads(nut, model, "calories", "calories_store", a0, CAL_TOL, CAL_TOL_REL),
                "an hourly calorie store off the model's burn")
        self._g("V1b_weight", grade_reads(nut, model, "weight", "weight_kg", a0, WEIGHT_TOL),
                "an hourly weight off the model's VM8 loss")

    def grade_v2(self, model, rows, ev_ages):
        a0, k = self.a0, self.key
        w = g(self.D, "X", "weight", "ages") or [None, None]
        start = w[1] or a0
        self._g(f"{k}_hunger", grade_curve(rows, model, "HUNGER", "hunger", a0, HUNGER_TOL, (start, 1e9), ev_ages),
                "a ring HUNGER off the model with four tins a day")
        nut = [r for r in self.reads.get("nutrition") or [] if num(r.get("age")) is not None and r["age"] >= start]
        self._g(f"{k}_weight", grade_reads(nut, model, "weight", "weight_kg", a0, WEIGHT_TOL),
                "an hourly weight off the model's VM8 gain from the 3000-kcal store")
        self._g(f"{k}_calories", grade_reads(nut, model, "calories", "calories_store", a0, CAL_TOL, CAL_TOL_REL),
                "an hourly calorie store off the model's arithmetic")
        R = self.out.setdefault("readings", {})
        R["mood"] = {f: [(r.get("age"), r.get(f)) for r in rows[::15] if num(r.get(f)) is not None]
                     for f in ("BOREDOM", "UNHAPPINESS")}
        R["anchor"] = self.anchor
        R["span_h"] = [self.v2_half()[0], self.v2_half()[1]]
        if nut:
            m0 = series_at(model["weight_kg"], nut[0]["age"] - a0)
            m1 = series_at(model["weight_kg"], nut[-1]["age"] - a0)
            R["weight_change"] = {"live": (nut[-1].get("weight") or 0) - (nut[0].get("weight") or 0),
                                  "model": None if (m0 is None or m1 is None) else m1 - m0,
                                  "from_age": nut[0]["age"], "to_age": nut[-1]["age"]}

    grade_v2a = grade_v2
    grade_v2b = grade_v2

    def grade_v3(self, model, rows, ev_ages):
        a0 = self.a0
        for arm, _p in V3_PROTEINS:
            w = self.D.get(arm) or {}
            m = mark_of(model, w.get("label") or arm)
            if m is not None:
                w["model_proteins"] = m["writes"].get("proteins")
                w["factor"] = VM.protein_factor(w["model_proteins"]) if w["model_proteins"] is not None else None
            self._g(f"V3_{arm}", grade_set(w, model, a0),
                    "the set's XP delta off the model's 360 x the protein factor by more than REP_TOL reps")
        B = self.D.get("B") or {}
        mg = mark_of(model, "B_grant")
        pred = mg["writes"]["strength_xp"] if mg is not None else None
        self._g("V3_B_grant", grade_grant(B.get("grant"), pred),
                "xp.grant's xpAfter off vanilla_model.strength_xp_grant at the read protein store")
        mb = mark_of(model, "B")
        want = mb["post"]["strength_level"] if (mb is not None and "post" in mb) else None
        self._g("V3_B_level", grade_level_band(B.get("xp_after"), B.get("stats_after"), want),
                "the level after arm B's set off the model's, or the band trait off #2157's band of it")

    def grade_v4(self, model, rows, ev_ages):
        a0 = self.a0
        A = self.D.get("A") or {}
        self._g("V4_A_coffee", grade_coffee(A.get("coffee"), model, a0),
                "FATIGUE across the coffee off the model's -0.1 a litre by more than FATIGUE_TOL")
        self._g("V4_A_holds", grade_coffee_holds(A.get("coffee")),
                "FATIGUE falling to its reset within the hour (the write did not hold with sleep on)")
        B = self.D.get("B") or {}
        cans = [c for c in B.get("cans") or [] if c.get("landed") and c.get("fill_ok")]
        if len(cans) < V4_BEERS:
            for n in ("V4_B_decay", "V4_B_zero"):
                self.xs.grade(n, "unmeasured", {"why": f"{len(cans)} of {V4_BEERS} cans landed with their fill gate",
                                                "cans": B.get("cans")}, "")
            return
        last = max((c.get("settle_age") or c.get("event_age") for c in cans), default=None) if cans else None
        last_ev = max((c.get("event_age") for c in cans if c.get("event_age") is not None), default=None)
        self._g("V4_B_decay", grade_intox_decay(B.get("polls"), last, model, a0),
                "INTOXICATION's decay off the model's 0.504 x day minutes a game hour by more than INTOX_DECAY_REL")
        last_poll = max((p["age"] for p in B.get("polls") or [] if num(p.get("age")) is not None), default=None)
        self._g("V4_B_zero", grade_intox_zero(B.get("polls"), last_ev, model, a0, last_age=last_poll),
                "INTOXICATION reaching 0 off the model's zero age by more than INTOX_ZERO_TOL_H")
        R = self.out.setdefault("readings", {})
        R["intox_peak"] = max((p["intox"] for p in B.get("polls") or [] if num(p.get("intox")) is not None),
                              default=None)
        R["intox_model_peak"] = max((v for _t, v in model.get("intoxication") or []), default=None)

    # ======================================================== the modded sessions
    def m_paths(self):
        return M1_RING if self.key == "M1" else M2_RING

    def intake(self, tag):
        v = vals(self.lread(tag, SRV, "_G", INTAKE_PATHS, log=False))
        return {k.rsplit(".", 1)[-1]: num(v.get(k)) for k in INTAKE_PATHS}

    def m_S(self):
        P = self.D["S"] = {}
        P["players"] = self.xs.step("S_players", SRV, "players")["ack"]
        P["sandbox"] = vals(self.lread("S_sv", SRV, "_G", ("SandboxVars.Nutrition", "SandboxVars.DayLength",
                                                             "NutritionRevamp.version",
                                                             "NutritionRevamp.server.nutrients.sleepDisabled")))
        P["clock"] = self.clock_read()
        P["nutrition"] = self.k("S_nutrition", SRV, "nutrition.get", USER)
        P["stats"] = self.stats_all("S_stats")
        self.probe_start(P)

    def m_H(self):
        P = self.D["H"] = {}
        paths = list(self.m_paths())
        rec = [p for p in paths if not p.startswith("_G.")]
        P["ring_paths"] = paths
        P["h1_record"] = self.lread("H_h1", SRV, f"record:{USER}", rec + list(H1_EXTRA))
        P["h1_globals"] = self.lread("H_h1g", SRV, "_G", [p[3:] for p in paths if p.startswith("_G.")])
        P["ring_start"] = self.ring_start(paths, "H_ring")

    def m_W(self):
        """x36's: wait for the store's next save of the record, then keep the saved line as start.json and the stats as
        start-stats.json (the replay's start)."""
        P = self.D["W"] = {}
        lw0 = num(vals(self.lread("W_lw0", SRV, "_G", FLUSH_PATHS)).get(FLUSH_PATHS[1]))
        P["lastWrite_before"] = lw0

        def fn():
            lw = num(vals(self.lread("W_poll", SRV, "_G", FLUSH_PATHS[1:], log=False)).get(FLUSH_PATHS[1]))
            return (lw is not None and (lw0 is None or lw > lw0)), lw
        p = self.poll("W_save", fn, SAVE_CAP_S)
        P["saved"] = p["done"]
        last = self.k("W_last", SRV, "lua.global", f"{NR}.server.store.file.last.{USER}")
        stats = self.stats_all("W_stats")
        P["read"] = self.snap("W_read_t")
        txt = last.get("value")
        if isinstance(txt, str):
            try:
                doc = json.loads(txt)
                rec = doc.get("rec") if isinstance(doc, dict) else None
                P["start_age"] = ((rec or {}).get("satiety") or {}).get("t")
                if self.run_dir:
                    with open(os.path.join(self.run_dir, "start.json"), "w", encoding="utf-8", newline="\n") as fh:
                        fh.write(txt)
                    self.xs.copied.append("start.json")
            except ValueError as e:
                self.xs.note(f"W: the saved line does not decode: {e}")
        st = {}
        for k in ("HUNGER", "THIRST", "FATIGUE", "BOREDOM", "UNHAPPINESS", "NICOTINE_WITHDRAWAL"):
            v = stat_of(stats, k)
            if v is not None:
                st[k] = v
        P["start_stats"] = st
        if self.run_dir:
            with open(os.path.join(self.run_dir, "start-stats.json"), "w", encoding="utf-8", newline="\n") as fh:
                json.dump(st, fh, indent=1, sort_keys=True)
            self.xs.copied.append("start-stats.json")

    def hunger(self, tag):
        a = self.stats_all(tag, log=False)
        return stat_of(a, "HUNGER"), num(a.get("worldAge"))

    def to_request(self, label, cap_age):
        """x36's: at MOD_SPEED_FAST until HUNGER >= APPROACH, then speed 1 until H_REQ; None past cap_age."""
        self.set_speed(MOD_SPEED_FAST, label + "_fast")
        h, a = self.hunger(label + "_h")
        while h is None or h < H_REQ:
            self.xs.check()
            if a is not None and a >= cap_age:
                return None
            if h is not None and h >= APPROACH:
                self.set_speed(1, label + "_one")
            self.xs.sleep(POLL_S)
            h, a = self.hunger(label + "_h")
        self.set_speed(1, label + "_one")
        return {"hunger": h, "age": a}

    def m_eat(self, full, label):
        """x36's eat: foodtimer 0 (xlib.Xs.eat_queue, as the existing modded drivers), eat.action, landed polled."""
        row = {"label": label, "food": full, "landed": False}
        self.eats.append(row)
        b = self.intake(label + "_before")
        row["before"] = b
        q = self.xs.eat_queue(full, label)
        row["queued"] = q

        def fn():
            a = self.intake(label + "_poll")
            return (a.get("landed") is not None and b.get("landed") is not None and a["landed"] > b["landed"]), a
        p = self.poll(label + "_land", fn, EAT_CAP_S)
        row["landed"] = p["done"]
        row["after"] = p["last"]
        row["landed_age_polled"] = self.age(label + "_landed_t")
        return row

    def m_drink(self, container, fluid, litres, label):
        """x36's drink: the server copy filled (fluid.fill; None keeps the prefilled can), drink.action, the sips polled
        until they stop rising for SETTLE_POLLS polls after a rise; the litres drunk off autodrink.probe."""
        row = {"label": label, "container": container, "fluid": fluid or "Beer", "litres": litres, "drunk": None}
        self.drinks.append(row)
        if fluid is not None:
            row["fill"] = self.k(label + "_fill", SRV, "fluid.fill", f"{USER} {container} {fluid} {litres}")
        row["probe_before"] = self.k(label + "_probe0", SRV, "autodrink.probe", USER)
        self.fill_gate(row, container, row["fluid"])
        b = self.intake(label + "_before")
        row["age0"] = self.age(label + "_age0")
        q = self.k(label + "_drink", CLI, "drink.action", f"{container} 1")
        row["queued"] = {k: q.get(k) for k in ("queued", "percentage", "spawned", "itemId", "filledRatioBefore")}
        self.xs.spawned_stop(q, label)
        st = {"last": b.get("sips"), "still": 0, "rose": False}

        def fn():
            a = self.intake(label + "_poll")
            s = a.get("sips")
            if s is not None and st["last"] is not None and s > st["last"]:
                st["rose"], st["still"] = True, 0
            elif st["rose"]:
                st["still"] += 1
            st["last"] = s
            return st["rose"] and st["still"] >= SETTLE_POLLS, a
        self.poll(label + "_sips", fn, DRINK_CAP_S)
        row["age1"] = self.age(label + "_age1")
        row["probe_after"] = self.k(label + "_probe1", SRV, "autodrink.probe", USER)
        l0 = num(g(row, "fill", "litres")) if fluid is not None else num(g(row, "probe_before", "litres"))
        l1 = num(g(row, "probe_after", "litres")) if g(row, "probe_after", "item") == container else 0.0
        row["drunk"] = (l0 - l1) if (l0 is not None and l1 is not None) else None
        if not st["rose"]:
            self.xs.note(f"drink {label}: sips never rose")
        return row

    def m1_body(self):
        return (("S", self.m_S), ("H", self.m_H), ("W", self.m_W), ("X", self.m1_X), ("C", self.restore_clock),
                ("R", self.phase_R), ("Z", self.m_Z))

    def m1_X(self):
        P = self.D["X"] = {}
        self.spawn(BOLOGNESE, 1, "X_spawn")
        a0 = self.age("X_a0") or 0.0
        P["request"] = self.to_request("X_req", a0 + M1_REQUEST_CAP_H)
        if P["request"] is None:
            self.xs.note("X: no request inside the cap; the eat is at the cap")
        P["eat"] = self.m_eat(BOLOGNESE, "X_eat")
        a = P["eat"].get("landed_age_polled") or self.age("X_a1") or a0
        P["fast_end"] = a + M1_FAST_H
        P["reached"] = self.run_to(P["fast_end"], [], MOD_SPEED_FAST, "X_fast")

    def m2_body(self):
        return (("S", self.m_S), ("H", self.m_H), ("W", self.m_W), ("X", self.m2_X), ("C", self.restore_clock),
                ("R", self.phase_R), ("Z", self.m_Z))

    def night(self, label):
        """x30's night, shortened: player.sleep.hold, acute.sleptH polled until M2_NIGHT_H booked or NIGHT_CAP_S, then
        the hold cancelled and the flag cleared."""
        n = {"label": label, "age0": self.age(label + "_a0")}
        n["hold"] = self.k(label + "_hold", SRV, "player.sleep.hold", f"{USER} {HOLD_S}")

        def fn():
            v = num(vals(self.lread(label + "_slept", SRV, f"record:{USER}", (SLEPT,), log=False)).get(SLEPT))
            return (v is not None and v >= M2_NIGHT_H), v
        p = self.poll(label + "_poll", fn, NIGHT_CAP_S, 0.5)
        n["booked"] = p["last"]
        n["reached"] = p["done"]
        n["cancel"] = self.k(label + "_cancel", SRV, "player.sleep.hold", f"{USER} 0")
        n["wake"] = self.k(label + "_wake", SRV, "player.sleep", f"{USER} false")
        self.sleep_until(self.xs.clock() + WAKE_SETTLE_S)
        n["age1"] = self.age(label + "_a1")
        n["booked_h"] = n["booked"]
        n["note"] = FAST_FORWARD_NOTE
        return n

    def m2_plan(self, a):
        """The relative schedule (review I-2): coffees at X's start plus M2_COFFEE_OFFSETS, the beers at least
        M2_BEER_GAP_H after the last and not before 19:00, the night at the next 23:00 when that is within
        M2_NIGHT_MAX_GAP_H of the beers (else M2_NIGHT_FALLBACK_H after them)."""
        coffees = [a + o for o in M2_COFFEE_OFFSETS]
        beers = max(coffees[-1] + M2_BEER_GAP_H, next_age_of_hour(a, M2_BEER_HOUR))
        n23 = next_age_of_hour(beers, M2_NIGHT_HOUR)
        night = n23 if n23 - beers <= M2_NIGHT_MAX_GAP_H else beers + M2_NIGHT_FALLBACK_H
        return {"start": a, "coffees": coffees, "beers": beers, "night": night,
                "night_at_23": night == n23, "ok": all(x < night for x in coffees + [beers])}

    def m2_X(self):
        P = self.D["X"] = {}
        a = self.age("X_a0") or 0.0
        plan = P["plan"] = self.m2_plan(a)
        if not plan["ok"]:
            self.xs.note(f"X refused: a planned action is not before the night: {plan}")
            P["refused"] = True
            return
        acts = []
        for i, ca in enumerate(plan["coffees"]):
            def coffee(x, i=i):
                self.spawn(COFFEE_CONTAINERS[i], 1, f"X_cup{i + 1}")
                self.m_drink(COFFEE_CONTAINERS[i], "Coffee", COFFEE_L, f"X_coffee{i + 1}")
            acts.append((ca, "timed", coffee))

        def beers(x):
            for j, cont in enumerate(BEER_CONTAINERS[:V4_BEERS]):
                self.spawn(cont, 1, f"X_beerspawn{j + 1}")
                self.m_drink(cont, "Beer", BEER_L, f"X_beer{j + 1}")
        acts.append((plan["beers"], "timed", beers))
        acts.append((plan["night"], "timed", lambda x: P.setdefault("nights", []).append(self.night("N1"))))
        self.run_to(plan["night"] + 0.01, acts, MOD_SPEED_FAST, "X1")
        n_end = g((P.get("nights") or [{}])[-1], "age1") or self.age("X_night_end")
        end = (n_end if n_end is not None else plan["night"] + M2_NIGHT_H) + M2_DAY2_H
        plan["end"] = end
        k = 0
        P["meals"] = []
        while True:
            self.xs.check()
            r = self.to_request(f"X_req{k}", end)
            if r is None:
                break
            self.spawn(BOLOGNESE, 1, f"X_mspawn{k}")
            P["meals"].append(self.m_eat(BOLOGNESE, f"X_meal{k}"))
            k += 1
        P["reached"] = self.age("X_end")

    def m_Z(self):
        P = self.D["Z"] = {}
        errs = [str(e) for e in (self.xs.server.errors if self.xs.server is not None else [])]
        P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:10]
        P["admin_parked"] = self.xs.parked()

    def grade_mod(self):
        """The replay of the ring at HEAD and the per-field grades; inputs written beside the artifact."""
        import replay_live as RL
        xs = self.xs
        self.out["eats"], self.out["drinks"] = self.eats, self.drinks
        rows = self.ring_rows()
        H = self.D.get("H") or {}
        miss = g(H, "h1_record", "missing") or {}
        xs.grade("H1", "as_predicted" if (g(H, "h1_record", "ok") is True and g(H, "ring_start", "ok") is True
                                          and not miss) else "falsified",
                 {"missing": miss, "ring_ok": g(H, "ring_start", "ok")}, "a ring path unresolved at the start")
        pages = g(self.D, "R", "pages") or []
        errs = [num(g(p, "reply", "errors")) for p in pages]
        xs.grade("RING", "as_predicted" if (pages and all(p.get("file") for p in pages)
                                            and all((e or 0) == 0 for e in errs)) else
                 ("unmeasured" if not pages else "falsified"), {"pages": len(pages), "errors": errs},
                 "a ring page unread or a ring error")
        Z = self.D.get("Z") or {}
        xs.grade("Z", "as_predicted" if not Z.get("server_mod_error_lines") and not Z.get("admin_parked")
                 else "falsified", Z, "a mod error line or the admin parked")
        start_path = os.path.join(self.run_dir or "", "start.json")
        if not rows or not os.path.isfile(start_path):
            self.out["replay"] = {"error": "no ring rows or no start record"}
            for f in list(REPLAY_TOL) + (list(ACUTE_TOL) if self.key == "M2" else []):
                xs.grade(f"{self.key}_replay_{f}", "unmeasured", {"why": "no replay"}, "")
            return
        with open(start_path, encoding="utf-8") as fh:
            start = json.load(fh)
        start_stats = g(self.D, "W", "start_stats") or {}
        sa = num(g(self.D, "W", "start_age"))
        sleep = self.key == "M2"
        drinks = [d for d in self.drinks if d.get("fill_ok")]
        if len(drinks) < len(self.drinks):
            xs.note(f"{len(self.drinks) - len(drinks)} drink(s) failed the fill gate and leave the replay")
        events, book = replay_events(rows, self.eats, drinks, sa, sleep=sleep)
        nut = g(self.D, "S", "nutrition") or {}
        sex = g(H, "h1_record", "values", "body.sex")
        player = {"female": sex == 2, "weight": num(nut.get("weight")) or 80.0,
                  "macros": [num(nut.get(k)) or 0.0 for k in ("calories", "carbs", "lipids", "proteins")]}
        tol = dict(REPLAY_TOL)
        if sleep:
            tol.update(ACUTE_TOL)
        rpaths = list(self.m_paths())
        if self.run_dir:
            for name, obj in (("events.json", events), ("player.json", player)):
                with open(os.path.join(self.run_dir, name), "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(obj, fh, indent=1, sort_keys=True)
                xs.copied.append(name)
        self.out["model_inputs"] = {"tool": "tools/replay_live.py replay_live (ServerReplay) at HEAD",
                                    "ring": self.pages, "events": "events.json", "start": "start.json",
                                    "start_stats": start_stats, "player": player, "sleep_allowed": self.spec["sleep"],
                                    "tol": {k: list(v) for k, v in tol.items()}, "bookkeeping": book,
                                    "cli": ("python tools/replay_live.py live --ring " + " ".join(self.pages) +
                                            " --events events.json --start start.json --start-stats start-stats.json "
                                            "--player player.json --sleep-allowed " +
                                            ("true" if self.spec["sleep"] else "false") + " --out replay.json")}
        try:
            rep, d, be = replay_grade(rows, events, start, self.spec["sleep"], tol, paths=rpaths, player=player,
                                      start_stats=start_stats)
        except Exception as e:                     # noqa: BLE001 - recorded, graded unmeasured
            self.out["replay"] = {"error": f"{type(e).__name__}: {e}"}
            for f in tol:
                xs.grade(f"{self.key}_replay_{f}", "unmeasured", {"why": "the replay raised"}, "")
            return
        if self.run_dir:
            with open(os.path.join(self.run_dir, "replay.json"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"rows": rep, "diff": d, "events": events, "offset": be.R.offset},
                                    indent=1, sort_keys=True, default=str) + "\n")
            xs.copied.append("replay.json")
        self.out["replay"] = {"rows": len(rep), "classes": d.get("classes"), "fields": d.get("fields"),
                              "findings_n": len(d.get("findings") or []), "offset": be.R.offset}
        for f in tol:
            self._g(f"{self.key}_replay_{f}", grade_replay_field(d, f),
                    f"{f} off the HEAD replay by more than {tol[f][1]} on a graded row")
        if sleep:
            self._g("M2_hangover", grade_hangover(rows, rep),
                    "a hangover on one side only, or its start off the replay's by more than HANG_TOL_H")
        self.out["verdict_summary"] = {k: v.get("verdict") for k, v in self.out["verdicts"].items()}
        _ = RL

    # -- the session table
    def phases(self):
        return {"V1a": self.v1a_body, "V1b": self.v1b_body, "V2a": self.v2_body, "V2b": self.v2_body,
                "V3": self.v3_body,
                "V4": self.v4_body, "M1": self.m1_body, "M2": self.m2_body}[self.key]()

    def grade_all(self):
        if self.spec["kind"] == "vanilla":
            self.grade_vanilla()
        else:
            self.grade_mod()


# ================================================================ the live run
def main(key, profile_name, prefix, artifact, session_text, pred, budget_s, driver_file, prev_run=None):
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_server, teardown, verify   # noqa: E402

    spec = SESSIONS[key]
    pre, ok = preboot(key, profile_name, prefix, driver_file)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str))
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    chain = None
    if spec.get("chain_from"):
        chain, cok = chain_check(prev_run, key)
        if not cok:
            print(json.dumps({"chain": chain}, indent=1, default=str))
            print("the previous run fails the chain check; the session was not started")
            sys.exit(1)
    prof = profile.load(profile_name)
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(prefix)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"restored": f"fixture {prof.fixture} restored into the run dir", "left_in_place": []}}
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, predictions=pred, user=USER)
    xs.path = os.path.join(run_dir, artifact)
    S = Sess(xs, key, run_dir=run_dir)
    if chain is not None:
        S.anchor = chain["anchor"]
        out["chain"] = chain
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "session_key": key, "session": session_text, "driver": driver_file, "lib": LIB_FILE,
        "user": USER, "profile": prof.report(), "preboot": pre,
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
        "harness_lua_dirty": git_dirty(LUA_DIR)[0],
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + LIB_FILE),
        "model_commit": git_say("log", "-1", "--format=%h", "--", "tools/vanilla_model.py"),
        "replay_tool_commit": git_say("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
        "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                      if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict,
                                                                             re.Pattern)) and k not in ("REPO",)},
        "predictions": pred, "meta": {"budget_s": budget_s},
    })
    if not doctor_clean:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"]:
        xs.refuse("the harness Lua is dirty; commit before the boot (CLAUDE.md s5)")
    if spec["kind"] == "mod":
        mg = staged_gate(out, git_say, git_dirty)
        want = f'"value": "{mg.get("staged_version")}"'
        vrows = [v for v in prof.verify if v.get("args") == f"{NR}.version"]
        mg["verify_rows_match"] = bool(vrows) and all(str(v.get("expect")) == want for v in vrows)
        if not (mg["ok"] and mg["verify_rows_match"]):
            xs.refuse(f"the staged copy does not match the clean tree or the verify rows: {mg!r}; not started")
        try:
            shutil.copyfile(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME), os.path.join(run_dir, MANIFEST_NAME))
            xs.copied.append(MANIFEST_NAME)
        except OSError as e:
            out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(prof.sources)
    if out["lint_errors"]:
        xs.refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")
    server = None
    try:
        if chain is not None:                    # the reuse boot: the previous run's saved world (x35's route)
            t = xs.wall()
            shutil.copytree(os.path.join(chain["dir"], "server"), os.path.join(run_dir, "server"))
            chain["copy_seconds"] = round(xs.wall() - t, 2)
            out["world_changes"]["restored"] = (f"the previous run {chain['run_id']}'s <run>/server copied whole and "
                                                "booted again (reuse=True); the admin client a fresh fixture restore")
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog, reuse=chain is not None)
        holder["server"] = server
        xs.server = server
        out["server_launch_wall"] = xs.wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = xs.wall()
        tl.mark("server_started")
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, started=started))
        tl.mark("session_ready")
        out["session_ready_wall"] = xs.wall()
        out["build"] = server.build
        out["verify"] = verify(prof, server, clients, tl)
        dm, okm = X.deployed_marker_check(run_dir, list(HARNESS_MARKERS), HARNESS_MARKERS)
        xs.mem("ready")
        xs.persist()
        if xs.abort_on_missing_marker(dm, okm):
            pass
        elif not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            S.body_run(S.phases())
    except Exception as e:                         # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            L = out["logs"] = {"patterns": {"log": LOG_RX.pattern}}
            if server is not None:
                L["server"], L["server_echo_excluded"] = X.grep_noecho(server.log_path, LOG_RX, 300, ECHO_RX,
                                                                         NEVER_RX)
                L["mod_error"] = [ln for ln in L["server"] if MOD_ERR_RX.search(ln)][:40]
                if key == "V1b":
                    try:
                        keep_server_log(server.log_path, run_dir, xs.copied)
                    except OSError as e:
                        L["log_copy_error"] = f"{type(e).__name__}: {e}"
            for c in every:
                lines, _ = X.grep_noecho(c.console, LOG_RX, 80, ECHO_RX, NEVER_RX)
                L.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        xs.finish(teardown, hard_kill, every, read_logs=read_logs, grade_all=S.grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, artifact)
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "abort": out.get("abort"),
                      "budget_stop": out.get("budget_stop"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "logs_error": out.get("logs_error"),
                      "run_id": run_id, "run_dir": run_dir, "memory": out.get("memory"),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])
    return out
