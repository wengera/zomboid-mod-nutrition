"""x45g_lib -- the session engine of Plan 15 Task 11's live sessions x452-x457: the game-feel changes (Plan 15
Tasks 4-10) checked in the running game on a dedicated server, one boot of profile x45g-mod per session.

Started from x45_lib.py (frozen with x451) and x44_guide_lib.py (frozen with x441-x447): their pre-boot checks, their
staged-copy gate, their harness-marker check, their clock control, their ring read and (x452) their HEAD-replay
bookkeeping are copied here, not imported, on testing/experiments/xlib.py (the bus step, the wall budget, the grade
recorder, RCON, the spawn, the abort/teardown/copy skeleton). x45_lib.py and x45-mod.toml are x451's and frozen, so
this lib and its profile take the name x45g ("game feel") rather than the plan's x45_lib / x45-mod.

THE PROFILE (testing/profiles/x45g-mod.toml): fixture default, admin (-debug), PZTestKit and the STAGED copy
release/plan15-x45g of mod/NutritionRevamp at STAGED_FROM (`python tools/release_pack.py stage mod/NutritionRevamp
--out release/plan15-x45g` before the boot; staged_gate checks it against release_pack.manifest() of mod/ at that commit
and refuses on a mismatch), Nutrition false (ruling T18-1), DayLength 1 (a game hour 37.5 wall s at speed 1), sleep off
(the curve's fit is sleep off, tools/fit_hunger_curve.py). Every session runs on it; the plan's x45-mod-sleep is not
needed: no session sleeps.

THE CLOCK. RCON settimespeed n (time.multiplier n only when the RCON command fails); x453 alone sets a fractional true
multiplier SLOW_MULT through time.multiplier (x391h ran at 0.1674, #3762), so a networked eat, which ends in real time
(#3766), costs few game minutes of gastric emptying. Every setting is restored from the trueMult read at phase S
(CLAUDE.md s5), never from a reply's echo. No client joins or relaunches during a session.

THE COMPRESSION (amendments s3). The record setters start a scenario near its point: record.set satiety.M 0 and
drain.fedAgeH (age - 30 + ONSET_LEAD_H) put the acute starvation onset (K.drain.STARVE_ONSET_H, 30 unfed hours) a
quarter game hour ahead (x454, x455); record.set fluids.water moves the body-water deficit to DEHYD_SEED_PCT (x456,
dehydPct = 100 x (weu - water) / 1000 / w is linear in water); record.set stomach.buffer.water and .calories seed the
stomach near SEED_G (x453). health.reduce takes health to HEALTH_SEED once starving so the drain reaches its first
floor in minutes (x454). Each set is recorded with its reply (before, after) and its world age.

THE SESSIONS (each under 10 wall minutes; PREDICTIONS sit in each driver):
  x452 day      S, H (the ring), W (the store's next save: start.json), F (the foods; the T9 reads), X (lunch at the
                next 12:30, dinner 6 h later, breakfast 13 h after that, 5 h after it; each meal a
                CannedBologneseOpen and a Banana, 645 kcal; DRINK_L of water DRINK_AFTER_H after each meal, a fresh
                container type each (DRINKS); server and client stats.get pairs throughout), C, R, T (the T9 reads
                after), Z.
  x453 overfull S, H, F (Broccoli x SPAWN_N), SEED (the slow clock, the stomach to SEED_G), X (one Broccoli at a time
                until Overfull 4, then one more eat attempted; the hold reads), C (the clock; action.cancel), R, Z.
  x454 starve   S, H, F (a CannedBologneseOpen), A (the onset), B (health to HEALTH_SEED, the drain to the floor and
                its hold), E (the can eaten; the recovery), C, R, Z.
  x455 bleed    S, H, N (four parts bleeding, not starving), A (the onset), SB (the same bleed, starving), SS
                (FOOD_SICKNESS 95, starving), K (the cleanup), C, R, Z.
  x456 water    S, H, A (the deficit to DEHYD_SEED_PCT, Parched at the onset), B (the drain to the floor and its
                hold), P (FOOD_SICKNESS 95 while Parched), C, R, Z.
  x457 thirst   S, H, BASE, HIGH (High Thirst added), OFF (removed), LOW (Low Thirst added), K (removed), C, R, Z.

THE GRADES (pure; each has a failing case in testing/tests/test_x45g_lib.py; a grade on no valid sample is unmeasured,
never as_predicted; every tolerance is named below, before any run):
  x452  EAT0          the ring's HUNGER at and after each meal's landing minute (EAT0_ROWS rows) at most EAT0_TOL.
        HYDRATED      every ring row not dehydrated and under DEHYD_ONSET_PCT (CLAUDE.md s5); x452's other grades
                      read only the rows before a first dehydrated row (hydrated_rows), noted.
        CAD_FEEL_P    each meal's Peckish return (HUNGER over 0.15, the ring) within CAD_P_TOL h of its band
                      CAD_P_TARGETS[meal], the HEAD replay of exactly this schedule (review M1; named after Task 6c's
                      re-fit, preboot refuses while any is None); vanilla_model's returns are recorded beside it.
        CAD_FEEL_H    the dinner's Hungry return (over 0.25) within CAD_H_TOL h of CAD_H_TARGET, named the same way.
        REPLAY_*      the HEAD kernel replay (tools/replay_live.replay_live, ServerReplay) of the ring from start.json
                      with the eats and the fill-gated drinks, under REPLAY_TOL (x446's).
        WF_SHOW       the server's FOOD_EATEN at 1 or more within WF_SHOW_GM game minutes of each meal's landing.
        WF_SPAN       the lunch's Well Fed end (the server reads) brackets the ring's satiety.M fall under WELL_FED_M
                      within WF_END_TOL_GM.
        PAIRS         every client FOOD_EATEN and HUNGRY level equals a server level read within PUSH_S before it (the
                      1 Hz push) or the last one before that window; PAIR_MIN pairs, one at a level over 0, and one
                      transition (a read the stale client can fail, review L4).
        (reading)     checks.wf_vs_vanilla: each meal's Well Fed span beside vanilla_model's at 90 and 15 minutes
                      (review M2: vanilla's scales as 1 / day length, the mod's does not; never a grade).
  x453  OF_REACH      Broccoli eaten from Overfull 3 or less lands until the stomach reads Overfull 4.
        OF_REFUSE     at Overfull 4 (still 4 on the read just before the attempt, else unmeasured) the next eat is
                      refused: validStart false on the client, no landing in REFUSE_WAIT_S, the stomach not heavier
                      by REFUSE_MASS_TOL.
        OF_EARLY      no eat refused below Overfull 4.
        OF_TIMER      the server's food timer above 3200 (FOOD_EATEN 3, #0511) on every settled Overfull 4 read, at or
                      under 3200 on every settled read below 4.
        OF_NAUSEA     FOOD_SICKNESS at least FOOD_SICK_STEP - NAUSEA_TOL and SICK at 1 or more at the trigger read,
                      the first settled read at Overfull 4 (review M4); the hold's reads are kept as readings.
        OF_ENDURANCE  ENDURANCE at most END_CAP + END_TOL and the endurance moodle at 1 or more on the settled reads at
                      Overfull 3 or more (unmeasured when NR.Severity is under 0.5, where the slowing is off).
        PAIRS         FOOD_EATEN, as x452.
  x454  ONSET         the ring's first starveAcute row at STARVE_ONSET_H unfed hours (ONSET_TOL_H), HUNGER over 0.70 on
                      it or the next row, and at most HUNGER_CAP + CAP_EPS on every row between the set and it.
        STARVING_SHOWN the server's HUNGRY at 4 on its first read ONSET_SHOW_GM after the onset row.
        CONST         the severe-moodle constant read 0 after the onset and the start's value before it.
        DRAIN_RATE    the health slope above the floor, before its reach, within DRAIN_TOL_REL of STARVE_RATE a day.
        FLOOR_HOLD    health within FLOOR_TOL of the ring's targetFloor over FLOOR_HOLD_GH after reaching it.
        RECOVER       after the can: starveAcute false within RECOVER_SHOW_GM, the constant back to the start's value,
                      health up by RECOVER_MIN over RECOVER_GH and never under the landing's by more than FLOOR_TOL
                      (review L2: the food heal, about 28 a game hour while M >= 435, or vanilla's regeneration alone,
                      0.43-1.07 a game hour, either clears it).
        PAIRS         HUNGRY, as x452.
  x455  ONSET, CONST  as x454.
        N_BLEED       the bleed's drain, not starving, within N_TOL_REL of x451's wound term plus red x M_H.
        S_BLEED       starving (constant 0) the same bleed drains at N's rate plus the starvation drain, within
                      S_TOL_REL of red x M_H; the re-applied counter rose.
        S_SICK        starving, SICK 4 (FOOD_SICKNESS 95) drains at red x M_H plus the starvation drain within
                      SICK_TOL_REL; the constant 0 at both ends.
  x456  DEHYD_ONSET   the ring's first dehydrated row at DEHYD_ONSET_PCT, THIRST over 0.84 on it or the next row, at
                      most THIRST_CAP + CAP_EPS before it.
        PARCHED_SHOWN the server's THIRST moodle at 4 on its first read ONSET_SHOW_GM after the onset row.
        CONST         as x454 (the onset is dehydration's).
        DEHYD_DRAIN   the health slope above the floor, before its reach, within DRAIN_TOL_REL of DEHYD_RATE a day.
        DEHYD_FLOOR   health within DEHYD_FLOOR_TOL of the ring's targetFloor over FLOOR_HOLD_GH after reaching it.
        BASAL         the ring's fluids.water loss within BASAL_TOL_REL of basalG(lm) / 24 a game hour.
        DEHYD_PACE    the live first-floor hour without water (the ring's dehydPct rise to 4 %, then the live drain)
                      within PACE_TOL_H of the kernel arithmetic for the live body (dehyd_pace).
        (reading)     checks.dehyd_spec: the live and the kernel hours beside the spec's SPEC_H (review M3).
        PAIRS         THIRST, as x452.
  x457  SCALE         the server's applied basal scale (NutritionRevamp.server.nutrients.fctx.basalScale, NR.read.trait)
                      reads 1, 1.5, 1 and 0.5 times the start's in BASE, HIGH, OFF and LOW, and BASE reads 1 at the
                      fixture's StatsDecrease 3.
        LOSS_<arm>    each arm's ring fluids.water loss within LOSS_TOL_REL of basalG(lm) x the arm's trait scale
                      (TRAIT_SCALE x BASE's applied scale) / 24 a game hour, plus the ring's cold diuresis.
        RATIO_<arm>   HIGH, OFF and LOW over BASE within RATIO_TOL of 1.5, 1 and 0.5.
        TRAITS        stats.get lists High Thirst and Low Thirst as each arm set them.
  every RING (pages read, errors 0), H1 (the ring's paths resolved at the start), Z (no mod error line, admin not
        parked).

UNMEASURED BY DESIGN (recorded under checks, never graded): Task 9's hunger-line hide (the harness cannot hover, and
lua.call passes scalars only, so the tooltip wrapper's draw cannot run; x452 reads the item's tag set before and after
and the client's tooltip counters); the server-side refusal through the open-and-eat craft (no harness command crafts;
x453 grades the client's isValidStart and the absent landing); Task 10's Game hangover (optional, no session room).

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run, this file is never edited (CLAUDE.md s5); a
later change is a new file and the drivers that use it name it.
"""
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                                   # testing/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import xlib as X                                                              # noqa: E402

REPO = X.REPO
SRV = X.SRV
CLI = "client"
LIB_FILE = "x45g_lib.py"
NR = "NutritionRevamp"
USER = "admin"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
MOD_DIR = "mod/NutritionRevamp"
PROFILE = "x45g-mod"
STAGE_OUT = "release/plan15-x45g"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_FROM = "718d4296"                 # the commit the staged copy is made from (mod/ last touched at 718d4296)
STAGED_CORE = "common/media/lua/shared/NR_Core.lua"
MANIFEST_NAME = "MANIFEST.json"
MIN_FREE_GB = 12.0
MOD_DAY_LENGTH = 1
DAY_MIN = 15.0                           # DayLength 1: a 15-minute day

SESSIONS = {
    "x452": {"driver": "x452_day.py", "artifact": "day.json"},
    "x453": {"driver": "x453_overfull.py", "artifact": "overfull.json"},
    "x454": {"driver": "x454_starve.py", "artifact": "starve.json"},
    "x455": {"driver": "x455_bleed.py", "artifact": "bleed.json"},
    "x456": {"driver": "x456_water.py", "artifact": "water.json"},
    "x457": {"driver": "x457_thirst.py", "artifact": "thirst.json"},
}

# ---- the clock -------------------------------------------------------------------------------------------------------
HOUR_OFFSET = 7.0                        # world age 0 is 07:00 on the default fixture (#2890)
SPEED_FAST = 5                           # x446's modded fast speed at DayLength 1
SLOW_MULT = 0.2                          # x453's true multiplier while it eats (a game minute 3.1 wall s)
LEAD_H = 3.0 / 60.0                      # the clock drops to speed 1 this long before a timed meal
POLL_S = 0.25
EAT_CAP_S = 30.0
SPEED_UNIT = "GameTime.getTrueMultiplier (the settimespeed number); mult is getMultiplier, the effective one (#3762)"

# ---- the mod and vanilla values the grades read (each with its source) -----------------------------------------------
HUNGRY_AT = (0.15, 0.25, 0.45, 0.70)     # VANILLA #0508 (strict greater-than, #0507)
THIRST_4 = 0.84                          # VANILLA #0509
HUNGER_CAP = 0.69                        # K.hybrid.defaults hungerCap (NR_Kernel_Hybrid.lua)
THIRST_CAP = 0.83                        # K.hybrid.defaults thirstCap
STARVING_MIN = 0.71                      # K.hybrid.defaults starvingMin
CAP_EPS = 1e-6
FED_M = 3.80654                          # K.hungerCurve.FED_M
WELL_FED_M = 435.0                       # K.view.WELL_FED_M
TIMER_REFUSE = 3200.0                    # FOOD_EATEN level 3 above it, vanilla's refusal (#0511, K.view.timerBand)
CAPACITY_MAX_G = 730.0                   # K.stomach.CAPACITY_MAX_G
CAPACITY_HARD_G = 1100.0                 # K.stomach.CAPACITY_HARD_G
OVERFULL_AT = (100.0 / 3.0, 200.0 / 3.0, 100.0)   # K.view.OVERFULL_AT
END_CAP = 0.73                           # NR_Data_Effects.lua enduranceCap at Overfull 3-4 (K.hybrid.capAt, DayLength 1)
SEVERITY_MIN = 0.5                       # NR_Data_Effects.lua enduranceCap sevMin
FOOD_SICK_STEP = 30.0                    # NR_Data_Effects.lua foodSickStep at Overfull 4
CONST_DEFAULT = 0.0165                   # BodyDamage.healthReductionFromSevereBadMoodles (#0516; x451)
M_H = 1800.0                             # the multiplier's sum over a game hour at DayLength 1 (#0518, #2922; x451 A)
WOUND_X451 = 5.963110742769263           # x451 C2's rate_per_gh: four parts at bleedingTime 5 with the constant at 0
STARVE_ONSET_H = 30.0                    # K.drain.STARVE_ONSET_H
STARVE_RATE = 25.0                       # K.drain.STARVE_RATE, health a game day
FIRST_FLOOR = 50.0                       # K.drain.FIRST_FLOOR
DEHYD_ONSET_PCT = 4.0                    # K.drain.DEHYD_KNOTS[1]
DEHYD_RATE = 200.0                       # K.drain.DEHYD_RATE, health a game day
BASAL_G = 2000.0                         # K.fluids.BASAL_G, g a day
BASAL_G_PER_LM = 32.0                    # K.fluids.BASAL_G_PER_LM
AVG_LEAN = 52.02                         # K.strength.averageLean() (spec section 3.4's 52.02)
WATER_PER_MMOL = 1000.0 / 140.0          # K.fluids.WATER_PER_MMOL: the euhydrated water weu follows the sodium pool
BASAL_NA = 8.0                           # K.fluids.BASAL_NA, mmol a day: weu falls WATER_PER_MMOL x BASAL_NA g a day
COLD_DIURESIS_LH = 0.1                   # K.fluids.COLD_DIURESIS_LH x clamp(coldMult - 1, 0, 1): litres a game hour
TRAIT_SCALE = {"BASE": 1.0, "HIGH": 1.5, "OFF": 1.0, "LOW": 0.5}   # K.fluids.HIGH_THIRST, LOW_THIRST
STATS_DECREASE_ONE = 3                   # the StatsDecrease enum whose multiplier is 1 (vanilla_model, #2765)
SPEC_H = 35.0                            # spec section 3.2: dehydration's first floor "by about 35 h"

# ---- the foods: the item pass's macros (NR_ItemPass_Food.txt), the script's HungerChange and FoodType (food.txt) -----
BOLOGNESE = "Base.CannedBologneseOpen"
BANANA = "Base.Banana"
BROCCOLI = "Base.Broccoli"
FOODS = {
    BOLOGNESE: {"cal": 540.00, "carb": 61.83, "lip": 22.19, "pro": 23.60, "hunger_script": -24.0, "foodType": "Meat"},
    BANANA: {"cal": 105.11, "carb": 26.97, "lip": 0.39, "pro": 1.29, "hunger_script": -16.0, "foodType": "Fruits"},
    BROCCOLI: {"cal": 11.02, "carb": 2.15, "lip": 0.12, "pro": 0.91, "hunger_script": -9.0,
               "foodType": "Vegetables"},
}
VANILLA_EAT = {BOLOGNESE: (-0.24, 540.0), BANANA: (-0.16, 105.0)}   # food.txt HungerChange / 100 and Calories
# x452's water (review H2): one fresh prefilled-water container TYPE a drink (normal.txt: WaterBottle 1.0 L, Canteen 0.9 L,
# Sportsbottle 1.0 L, each Fluids Water:1.0 and no sealed tag), spawned by RCON at its drink so auto-drink has no window,
# the server copy filled to DRINK_L of Water (fluid.fill), drink.action <type> 1 on the client: x44_guide_lib's route
# (x446, x447). Each drink sits DRINK_AFTER_H after a meal, when the solid lane has emptied enough that the drink keeps
# the stomach under Overfull 3 (a 668 g meal plus 0.5 L at once would read Overfull 4).
DRINKS = ("Base.WaterBottle", "Base.Canteen", "Base.Sportsbottle")
DRINK_FLUID = "Water"
DRINK_L = 0.5
DRINK_AFTER_H = 2.5
DRINK_CAP_S = 40.0
SETTLE_POLLS = 3

# ---- the record and global paths -------------------------------------------------------------------------------------
EATS_G = "_G.NutritionRevamp.server.intake.stats.eats"
LANDED_G = "_G.NutritionRevamp.server.intake.stats.landed"
SIPS_G = "_G.NutritionRevamp.server.intake.stats.sips"
INTAKE_PATHS = ("NutritionRevamp.server.intake.stats.eats", "NutritionRevamp.server.intake.stats.landed",
                "NutritionRevamp.server.intake.stats.sips")
RED_G = "_G.NutritionRevamp.server.writer.h.admin.red"
FT_G = "_G.NutritionRevamp.server.writer.h.admin.ft"
WRITES_G = "_G.NutritionRevamp.server.writer.stats.writes"
REAPPLIED_G = "_G.NutritionRevamp.server.writer.severeStats.reapplied"
SCALE_PATH = "NutritionRevamp.server.nutrients.fctx.basalScale"
SCALE_G = "_G." + SCALE_PATH
FLUSH_PATHS = ("NutritionRevamp.server.players.online.admin", "NutritionRevamp.server.store.file.lastWrite.admin")
STOMACH_PATHS = ("stomach.buffer.water", "stomach.buffer.proteins", "stomach.buffer.carbs", "stomach.buffer.lipids",
                 "stomach.buffer.fibre", "stomach.buffer.calories", "stomach.liquid")
DRAIN_PATHS = ("drain.active", "drain.state", "drain.targetFloor", "drain.rate")
RING = {
    "x452": ("satiety.M", "satiety.S", "satiety.L", "satiety.t", "satiety.hModel", "stomachFill", "stomach.liquid",
             "body.energyState", "body.met", "body.fm", "body.lm", "body.inDay", "body.eeDay", "kineticsAge",
             "fluids.water", "fluids.na", "fluids.naPlasma", "fluids.autoDrop", "fluids.thirstTarget",
             "fluids.dehydPct", "drain.active", "drain.dehydrated", EATS_G, LANDED_G, SIPS_G, WRITES_G, FT_G, RED_G),
    "x453": STOMACH_PATHS + ("stomach.volX", "stomachFill", "satiety.M", "effects.enduranceCap",
                             "effects.foodSickStep", "drain.active", EATS_G, LANDED_G, FT_G, WRITES_G),
    "x454": ("satiety.M", "drain.fedAgeH", "drain.starvedH", "drain.acuteH", "drain.starveAcute", "drain.starving",
             "drain.bmi0", "drain.drainThisMinute") + DRAIN_PATHS +
            ("body.fm", "body.lm", "stomachFill", EATS_G, LANDED_G, RED_G, REAPPLIED_G, FT_G),
    "x455": ("satiety.M", "drain.fedAgeH", "drain.starvedH", "drain.starveAcute", "drain.starving") + DRAIN_PATHS +
            ("effects.foodSickTarget", EATS_G, LANDED_G, RED_G, REAPPLIED_G),
    "x456": ("fluids.water", "fluids.dehydPct", "fluids.thirstTarget", "fluids.na", "fluids.k", "fluids.sweatLmin",
             "fluids.autoDrop", "drain.dehydrated") + DRAIN_PATHS +
            ("body.fm", "body.lm", "body.lx", "body.met", "body.coldMult", "stomach.liquid", "stomach.buffer.water",
             RED_G, REAPPLIED_G, LANDED_G, SIPS_G, SCALE_G),
    "x457": ("fluids.water", "fluids.dehydPct", "fluids.sweatLmin", "fluids.autoDrop", "body.lm", "body.met",
             "body.coldMult", "stomach.liquid", "stomach.buffer.water", SCALE_G, LANDED_G, SIPS_G),
}
H1_EXTRA = ("firstSeen", "body.sex", "body.fm", "body.lm", "body.lx")
STATS_KEYS = ("hunger", "thirst", "endurance", "fatigue", "weight", "foodTimer", "worldAge", "asleep", "moving")
STAT_NAMES = {"HUNGER": "Hunger", "THIRST": "Thirst", "FATIGUE": "Fatigue", "BOREDOM": "Boredom",
              "UNHAPPINESS": "Unhappiness", "NICOTINE_WITHDRAWAL": "NicotineWithdrawal"}

# ---- the tolerances and the scenario sizes (named before any run) ----------------------------------------------------
PUSH_S = 1.2                             # the 1 Hz stats packet plus a fifth of a second
TRANSITION_S = 3.0                       # review L4: a client read within this long after a server level change
PAIR_SLACK_S = 0.3
PAIR_MIN = 5
REPLAY_TOL = {"HUNGER": ("abs", 0.002), "body.energyState": ("abs", 0.005), "THIRST": ("abs", 0.002)}   # x446's
SAVE_CAP_S = 60.0
# x452
LUNCH_HOUR = 12.5
MIN_LEAD_H = 0.1
DINNER_GAP_H = 6.0
BREAKFAST_GAP_H = 13.0
TAIL_H = 5.0
MEAL = (BOLOGNESE, BANANA)
WF_WATCH1_GH = 0.65                      # the lunch's Well Fed watch at speed 1
WF_WATCH_GH = 0.1                        # the later meals' watch at speed 1
PAIR_EVERY_S = 1.5
FAST_PAIR_EVERY_S = 4.0
EAT0_TOL = 0.02
EAT0_ROWS = 3                            # the landing minute's row and the next two (the next minute's write)
# The cadence bands (review M1, the controller's ruling): each meal's Peckish return and the dinner's Hungry return
# graded against the HEAD replay of exactly this session's schedule (the foods, the drinks, the minutes), one band a
# meal. None until Task 6c's re-fit lands and the replay is re-derived: preboot refuses a boot while any is None.
CAD_P_TARGETS = {"lunch": None, "dinner": None, "breakfast": None}
CAD_P_TOL = 0.5
CAD_H_TARGET = None
CAD_H_TOL = 0.75
WF_SHOW_GM = 3.0
WF_END_TOL_GM = 2.0
SPAWN_BANANAS = 4                        # three eaten, one left for the T9 read after
T9_ITEM = BANANA
# x453
SPAWN_N = 12
SEED_G = 960.0                           # Overfull 2 (853-977 g), so the eats cross 3 and 4
SEED_KCAL = 2000.0                       # energy in the lane: emptying 0.31 % a game minute (K.stomach.solidFraction)
MAX_EATS = 10
SETTLE_GM = 1.5                          # game minutes after a landing before the next read (the writer's next minute)
SETTLE_WALL_S = 1.5                      # and the 1 Hz push
REFUSE_WAIT_S = 8.0
REFUSE_MASS_TOL = 10.0
HOLD_GM = 3.0
NAUSEA_TOL = 0.5
END_TOL = 0.005
# x454 / x455
ONSET_LEAD_H = 0.25                      # unfed hours set to STARVE_ONSET_H - ONSET_LEAD_H
ONSET_CAP_S = 45.0
ONSET_TOL_H = 0.05
ONSET_SHOW_GM = 3.0
HEALTH_SEED = 55.0
DRAIN_CAP_GH = 9.0
FLOOR_HOLD_GH = 1.5
FLOOR_TOL = 0.3
FLOOR_REACH = 0.2
DRAIN_TOL_REL = 0.15
DRAIN_MIN_GH = 1.0                       # the drain slope needs this span of game hours
POINT_EVERY_S = 0.5
RECOVER_GH = 2.0
RECOVER_MIN = 0.5                        # review L2: the regeneration floor alone gives about 0.86 over 2 game h
RECOVER_SHOW_GM = 2.0
WIN_S = 10.0
SETTLE_S = 1.5
BLEED_PARTS = (0, 1, 2, 3)               # x451's: Hand_L, Hand_R, ForeArm_L, ForeArm_R, BLEEDING 4
BLEED_TIME = 5.0
FOOD_SICK_W = 95.0                       # SICK 4 above 0.90 on the hundredth scale (#3130)
N_TOL_REL = 0.25
REGEN_STANDARD = 0.002                   # VANILLA #2354, the standard addition a multiplier unit
BLEED_WEIGHT = 0.6                       # the four bleeding parts' share (hands 0.1 + 0.1, forearms 0.2 + 0.2; review L1)
PARTS = 17                               # AddGeneralHealth adds y / 17 to each part below 100 (#3898)
S_TOL_REL = 0.15
SICK_TOL_REL = 0.20
# x456
DEHYD_SEED_PCT = 3.80
DEHYD_CAP_GH = 4.0
DEHYD_NEAR_PCT = 3.97                    # the clock drops to speed 1 here, so the onset is read at speed 1
DEHYD_FLOOR_TOL = 0.5
BASAL_TOL_REL = 0.03
PACE_TOL_H = 1.0
STOMACH_EMPTY_G = 1.0
# x457
WIN_GH = 3.0
ARM_SETTLE_GM = 3.0
LOSS_TOL_REL = 0.03
RATIO_TOL = {"HIGH": 0.05, "OFF": 0.03, "LOW": 0.03}

# ---- the harness markers the lib's commands need (the repository files and every deployed copy) ----------------------
HARNESS_FILES = {"PZTestKit_Server.lua": LUA_DIR + "/server/PZTestKit_Server.lua",
                 "PZTestKit_Client.lua": LUA_DIR + "/client/PZTestKit_Client.lua",
                 "PZTestKit_Client_Body.lua": LUA_DIR + "/client/PZTestKit_Client_Body.lua",
                 "PZTestKit_Core.lua": LUA_DIR + "/shared/PZTestKit_Core.lua"}
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": tuple(f'TK.register("{c}", function(' for c in (
        "minute.ring", "stats.get", "stats.all", "stats.setany", "health.get", "health.reduce", "moodle.level",
        "witness.chain", "record.set", "trait.set", "bodypart.set", "item.get", "autodrink.probe", "nutrition.get",
        "time.multiplier", "players", "fluid.fill")),
    "PZTestKit_Client.lua": tuple(f'TK.register("{c}", function(' for c in (
        "eat.action", "drink.action", "witness.chain", "action.cancel")),
    "PZTestKit_Client_Body.lua": tuple(f'TK.register("{c}", function(' for c in ("stats.get",)),
    "PZTestKit_Core.lua": tuple(f'TK.register("{c}", function(' for c in ("time.snapshot", "lua.read", "lua.global",
                                                                         "lua.call")),
}
ECHO_RX = re.compile(r"PZTK: ")
NEVER_RX = re.compile(r"(?!x)x")
LOG_RX = re.compile(r"NutritionRevamp|NR_|LuaError|STACK TRACE|lua error|attempted index|tried to call nil", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|failed:|STACK TRACE|attempted index|tried to call nil")


# ================================================================ small readers (pure)
def num(v):
    return X.num(v)


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def vals(a):
    v = a.get("values") if isinstance(a, dict) else None
    return v if isinstance(v, dict) else {}


def mid(row):
    """A kept reply's wall midpoint (xlib.Xs.keep writes wall and wall_after)."""
    a, b = num(g(row, "wall")), num(g(row, "wall_after"))
    if a is None or b is None:
        return None
    return (a + b) / 2.0


def hour_of(age):
    return math.fmod(age + HOUR_OFFSET, 24.0)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def is_true(v):
    return v is True


def stomach_mass(v):
    """K.mirror.stomachMass from a lua.read or ring row's stomach values: the solid buffer's mass keys plus the liquid
    lane, rounded half up as the mirror rounds (math.floor(g + 0.5)); None when a key is not a number."""
    keys = ("stomach.buffer.water", "stomach.buffer.proteins", "stomach.buffer.carbs", "stomach.buffer.lipids",
            "stomach.buffer.fibre", "stomach.liquid")
    xs = [num(v.get(k)) for k in keys]
    if any(x is None for x in xs):
        return None
    return math.floor(sum(xs) + 0.5)


def overfull_level(mass):
    """K.view.fullnessLevel: 0 at or under 730 g, 1 above, 2 from a third of the way to 1100 g, 3 from two thirds, 4 at
    1100 g; None for no mass."""
    if mass is None:
        return None
    d = 100.0 * clamp((mass - CAPACITY_MAX_G) / (CAPACITY_HARD_G - CAPACITY_MAX_G), 0.0, 1.0)
    if d <= 0:
        return 0
    return 1 + sum(1 for t in OVERFULL_AT if d >= t)


def basal_g_day(lm, scale=1.0):
    """K.fluids.basalG: (BASAL_G + BASAL_G_PER_LM x (lm - AVG_LEAN)) x scale, floored at 0."""
    return max((BASAL_G + BASAL_G_PER_LM * (lm - AVG_LEAN)) * scale, 0.0)


def fit_slope(points):
    """Least squares slope of [(x, y)]; None under two points or no spread."""
    pts = [(x, y) for x, y in points if x is not None and y is not None]
    if len(pts) < 2:
        return None
    n = len(pts)
    mx = sum(x for x, _ in pts) / n
    my = sum(y for _, y in pts) / n
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    if sxx <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in pts) / sxx


def ring_age(r):
    return num(r.get("age"))


def rows_between(rows, a0, a1):
    return [r for r in rows if ring_age(r) is not None and a0 < ring_age(r) <= a1]


def first_return(rows, a0, a1, thr, field="HUNGER"):
    """Hours from a0 to the first ring row in (a0, a1] with field strictly over thr; None when none."""
    for r in rows_between(rows, a0, a1):
        v = num(r.get(field))
        if v is not None and v > thr:
            return ring_age(r) - a0
    return None


def counts_row(rows, n, key=EATS_G):
    """The index of the first ring row whose counter reached n; None when none."""
    for i, r in enumerate(rows):
        v = num(r.get(key))
        if v is not None and v >= n:
            return i
    return None


def window_rate(w):
    """x451's: the health change between the window's two reads and the drain rate a game hour, the wall span converted
    by the game hours a wall second its two stats.get reads give. Positive rate = health falling."""
    h0, h1 = num(g(w, "h0", "overall")), num(g(w, "h1", "overall"))
    t0, t1 = mid(w.get("h0") or {}), mid(w.get("h1") or {})
    a0, a1 = num(g(w, "s0", "worldAge")), num(g(w, "s1", "worldAge"))
    u0, u1 = mid(w.get("s0") or {}), mid(w.get("s1") or {})
    r = {"dh": None, "dwall": None, "gh_per_s": None, "game_h": None, "rate_per_gh": None}
    if None in (h0, h1, t0, t1):
        return r
    r["dh"] = h1 - h0
    r["dwall"] = t1 - t0
    if None in (a0, a1, u0, u1) or u1 <= u0:
        return r
    r["gh_per_s"] = (a1 - a0) / (u1 - u0)
    r["game_h"] = r["dwall"] * r["gh_per_s"]
    if r["game_h"] > 0:
        r["rate_per_gh"] = -r["dh"] / r["game_h"]
    return r


def level_at_ends(w, name):
    """A moodle's level at both ends of a window (moodle.level replies lv0 and lv1)."""
    return num(g(w, "lv0", name, "level")), num(g(w, "lv1", name, "level"))


def const_of(reply):
    """The severe-moodle constant off a witness.chain getter reply, else None."""
    if not isinstance(reply, dict) or reply.get("ok") is not True:
        return None
    return num(reply.get("value"))


def day_plan(a):
    """x452's meals from X's start age a: lunch at the next 12:30 when at least MIN_LEAD_H ahead, else MIN_LEAD_H after
    a (noted); dinner DINNER_GAP_H after it; breakfast BREAKFAST_GAP_H after that (07:30 when lunch was at 12:30); the
    end TAIL_H after breakfast."""
    tod = hour_of(a)
    at = tod <= LUNCH_HOUR - MIN_LEAD_H
    lunch = a + (LUNCH_HOUR - tod if at else MIN_LEAD_H)
    dinner = lunch + DINNER_GAP_H
    breakfast = dinner + BREAKFAST_GAP_H
    return {"start": a, "lunch": lunch, "dinner": dinner, "breakfast": breakfast, "end": breakfast + TAIL_H,
            "lunch_at_1230": at}


# ================================================================ the grades (pure; each has a failing case)
def grade_pairs(pairs, key):
    """Every client level of `key` (a stats.get moodles key) in the set the server read within PUSH_S before the client
    read (to PAIR_SLACK_S after it), plus the last server level before that window; a client read with no server read
    before the window is not graded. pairs: [{s0, c, s1}] of kept stats.get rows. Needs PAIR_MIN graded client reads,
    one at a level over 0, and one transition (review L4): a read whose window holds a server level other than the one
    before it, or within TRANSITION_S after a server level change, the only read a stale client can fail."""
    srv = []
    for p in pairs:
        for k in ("s0", "s1"):
            t, lv = mid(p.get(k) or {}), num(g(p, k, "moodles", key))
            if t is not None and lv is not None:
                srv.append((t, lv))
    srv.sort()
    changes = [srv[i][0] for i in range(1, len(srv)) if srv[i][1] != srv[i - 1][1]]
    bad, n, nonzero, trans = [], 0, False, 0
    for p in pairs:
        t, lv = mid(p.get("c") or {}), num(g(p, "c", "moodles", key))
        if t is None or lv is None:
            continue
        before = [s for ts, s in srv if ts < t - PUSH_S]
        if not before:
            continue                     # no server read before the push window: the client's state unknown
        n += 1
        inwin = {s for ts, s in srv if t - PUSH_S <= ts <= t + PAIR_SLACK_S}
        allowed = set(inwin)
        allowed.add(before[-1])
        if any(s != before[-1] for s in inwin) or any(0 <= t - tc <= TRANSITION_S for tc in changes):
            trans += 1                   # a read near a level change: the one a stale client fails
        if lv > 0:
            nonzero = True
        if lv not in allowed:
            bad.append({"tag": p.get("tag"), "client": lv, "allowed": sorted(allowed), "wall": t})
    obs = {"key": key, "client_reads": n, "nonzero": nonzero, "transitions": trans, "mismatches": bad[:20],
           "n_bad": len(bad)}
    if n < PAIR_MIN or not nonzero or trans == 0:
        return "unmeasured", obs
    return ("as_predicted" if not bad else "falsified"), obs


def grade_eat0(meals, rows):
    """EAT0 (Task 6): HUNGER at most EAT0_TOL on the ring row where the eats counter reached each meal's count and the
    EAT0_ROWS - 1 rows after it."""
    obs = []
    for m in meals:
        n = m.get("eats_after")
        if not m.get("landed") or n is None:
            continue
        i = counts_row(rows, n)
        if i is None:
            obs.append({"label": m.get("label"), "why": "the eats counter never reached the meal's count"})
            continue
        hs = [num(rows[j].get("HUNGER")) for j in range(i, min(len(rows), i + EAT0_ROWS))]
        hs = [h for h in hs if h is not None]
        obs.append({"label": m.get("label"), "s": rows[i].get("s"), "hunger": hs,
                    "max": max(hs) if hs else None})
    measured = [o for o in obs if o.get("max") is not None]
    if not measured:
        return "unmeasured", {"meals": obs}
    ok = all(o["max"] <= EAT0_TOL for o in measured)
    return ("as_predicted" if ok else "falsified"), {"meals": obs, "tol": EAT0_TOL}


def grade_return(windows, target, tol):
    """CAD_FEEL_P and CAD_FEEL_H: windows [{label, ret (hours or None), span (hours the window covered), target (this
    window's band centre, else `target`)}]. A window with no target is unmeasured; one with no return whose span covers
    target + tol is a miss (falsified); one whose span does not is unmeasured; a return outside target +/- tol is
    falsified."""
    obs, measured, bad = [], 0, False
    for w in windows:
        ret, span = w.get("ret"), w.get("span")
        row = dict(w)
        target = w.get("target", target)
        row["target"] = target
        if target is None:
            row["verdict"] = "no band named"
            obs.append(row)
            continue
        if ret is None:
            if span is not None and span >= target + tol:
                row["verdict"] = "no return inside the band"
                bad = True
                measured += 1
            else:
                row["verdict"] = "window too short"
        else:
            measured += 1
            row["off_h"] = ret - target
            if abs(ret - target) > tol:
                bad = True
                row["verdict"] = "outside"
            else:
                row["verdict"] = "inside"
        obs.append(row)
    res = {"windows": obs, "tol_h": tol}
    if not measured:
        return "unmeasured", res
    return ("falsified" if bad else "as_predicted"), res


def grade_hydrated(rows):
    """HYDRATED (review H2; CLAUDE.md s5: a multi-day run asserts its character stays hydrated): every ring row has
    drain.dehydrated false and fluids.dehydPct under DEHYD_ONSET_PCT; unmeasured with no dehydPct on the ring."""
    pcts = [num(r.get("fluids.dehydPct")) for r in rows if num(r.get("fluids.dehydPct")) is not None]
    on = [r.get("s") for r in rows if is_true(r.get("drain.dehydrated"))]
    obs = {"rows": len(pcts), "max_pct": max(pcts) if pcts else None, "start_pct": pcts[0] if pcts else None,
           "dehydrated_rows": on[:10]}
    if not pcts:
        return "unmeasured", obs
    return ("as_predicted" if not on and max(pcts) < DEHYD_ONSET_PCT else "falsified"), obs


def hydrated_rows(rows):
    """The ring's rows before its first drain.dehydrated row (review H2: the onset writes the constant and the food
    timer, so later rows are excluded from x452's grades); (rows, the excluded count)."""
    for i, r in enumerate(rows):
        if is_true(r.get("drain.dehydrated")):
            return rows[:i], len(rows) - i
    return rows, 0


def grade_replay_field(diff, field):
    """x44's: one field of tools/replay_live.diff: unmeasured on 0 compared rows, falsified on any row over."""
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


def server_reads(pairs):
    """The server halves of the pairs (s0, s1), ordered by world age."""
    out = []
    for p in pairs:
        for k in ("s0", "s1"):
            r = p.get(k)
            if isinstance(r, dict) and num(r.get("worldAge")) is not None:
                out.append(r)
    out.sort(key=lambda r: num(r.get("worldAge")))
    return out


def grade_wf_show(meals, pairs):
    """WF_SHOW: for each landed meal, a server read in (landing, landing + WF_SHOW_GM] with FOOD_EATEN 1 or more."""
    srv = server_reads(pairs)
    obs, bad, n = [], False, 0
    for m in meals:
        a = num(m.get("landed_age"))
        if not m.get("landed") or a is None:
            continue
        win = [r for r in srv if a < num(r["worldAge"]) <= a + WF_SHOW_GM / 60.0]
        lv = [num(g(r, "moodles", "foodEaten")) for r in win]
        row = {"label": m.get("label"), "reads": len(win), "levels": lv}
        if win:
            n += 1
            row["shown"] = any((x or 0) >= 1 for x in lv)
            bad = bad or not row["shown"]
        obs.append(row)
    if not n:
        return "unmeasured", {"meals": obs}
    return ("falsified" if bad else "as_predicted"), {"meals": obs, "window_gm": WF_SHOW_GM}


def ring_wf_end(rows, a0, a1):
    """The age of the first ring row in (a0, a1] with satiety.M under WELL_FED_M; None when none."""
    for r in rows_between(rows, a0, a1):
        m = num(r.get("satiety.M"))
        if m is not None and m < WELL_FED_M:
            return ring_age(r)
    return None


def grade_wf_span(meal, pairs, rows, a_end):
    """WF_SPAN (the lunch): the server's last Well Fed read and its first read at 0 after the landing bracket the ring's
    M fall under WELL_FED_M, each side widened by WF_END_TOL_GM."""
    a = num(meal.get("landed_age")) if meal else None
    if a is None or not meal.get("landed"):
        return "unmeasured", {"why": "no landed lunch"}
    srv = [r for r in server_reads(pairs) if a < num(r["worldAge"]) <= a_end]
    on = [r for r in srv if (num(g(r, "moodles", "foodEaten")) or 0) >= 1]
    off = [r for r in srv if on and num(r["worldAge"]) > num(on[-1]["worldAge"])
           and num(g(r, "moodles", "foodEaten")) == 0]
    ring_end = ring_wf_end(rows, a, a_end)
    obs = {"landed_age": a, "ring_end": ring_end, "last_on": num(on[-1]["worldAge"]) if on else None,
           "first_off": num(off[0]["worldAge"]) if off else None, "tol_gm": WF_END_TOL_GM}
    if ring_end is None or not on or not off:
        return "unmeasured", obs
    tol = WF_END_TOL_GM / 60.0
    obs["ring_span_h"] = ring_end - a
    ok = obs["last_on"] - tol <= ring_end <= obs["first_off"] + tol
    return ("as_predicted" if ok else "falsified"), obs


def vanilla_meals(meal_ages, h0, day_length_min, hours):
    """vanilla_model.simulate of the same meals (each a CannedBologneseOpen and a Banana) from HUNGER h0 at the first
    meal's age; per meal its Peckish and Hungry returns and its Well Fed span (hours, None when none in the window)."""
    import vanilla_model as VM
    if not meal_ages:
        return []
    a0 = meal_ages[0]
    ev = []
    for t in meal_ages:
        for full in MEAL:
            hc, kcal = VANILLA_EAT[full]
            ev.append({"kind": "eat", "t_h": t - a0, "hunger_change": hc, "calories": kcal})
    out = VM.simulate({"hours": hours, "dt_min": 1, "start": {"hunger": h0},
                       "settings": {"day_length_min": day_length_min}, "events": ev})
    H, F = out["hunger"], out["food_eaten_level"]
    res = []
    for i, t in enumerate(meal_ages):
        s = t - a0
        e = (meal_ages[i + 1] - a0) if i + 1 < len(meal_ages) else hours
        row = {}
        for name, thr in (("peckish", HUNGRY_AT[0]), ("hungry", HUNGRY_AT[1])):
            k = next((tt for tt, v in H if s + 0.01 < tt < e and v > thr), None)
            row[name] = None if k is None else k - s
        k = next((tt for tt, v in F if s + 0.02 < tt < e and v == 0), None)
        row["well_fed_h"] = None if k is None else k - s
        res.append(row)
    return res


def wf_vs_vanilla(spans, van):
    """A reading, never a grade (review M2, the controller's ruling: the mod's Well Fed span is fixed in game hours and
    matched at the default 90-minute day; vanilla's scales as 1 / day length, an engine artifact kept as a stated
    bend): each meal's ring span beside vanilla_model's at the 90-minute and the profile's day."""
    out = []
    for i, s in enumerate(spans):
        out.append({"meal": i, "mod_h": s,
                    "vanilla_90_h": ((van.get("day90") or [])[i:i + 1] or [{}])[0].get("well_fed_h"),
                    "vanilla_profile_h": ((van.get("profile") or [])[i:i + 1] or [{}])[0].get("well_fed_h")})
    return out


def grade_of_reach(eats):
    """OF_REACH: a landed eat from Overfull 3 or less, and a landed eat whose settled read is Overfull 4."""
    landed = [e for e in eats if e.get("landed")]
    obs = {"landed": len(landed), "pre_levels": [e.get("pre_level") for e in eats],
           "post_levels": [e.get("post_level") for e in eats], "post_mass": [e.get("post_mass") for e in eats]}
    if not landed:
        return "unmeasured", obs
    below = any(e.get("pre_level") is not None and e["pre_level"] <= 3 for e in landed)
    reached = any(e.get("post_level") == 4 for e in landed)
    obs["from_below"], obs["reached"] = below, reached
    return ("as_predicted" if below and reached else "falsified"), obs


def grade_of_refuse(ref):
    """OF_REFUSE: the attempt at a settled Overfull 4, still at 4 on the read just before it (review M4): validStart
    false, no landing, the stomach not heavier."""
    if not ref or ref.get("pre_level") != 4:
        return "unmeasured", {"ref": ref, "why": "no attempt at Overfull 4"}
    if ref.get("level_at_attempt") != 4:
        return "unmeasured", {"ref": ref, "why": "the stomach left Overfull 4 before the attempt"}
    m0, m1 = num(ref.get("mass0")), num(ref.get("mass1"))
    ok = (ref.get("validStart") is False and not ref.get("landed")
          and m0 is not None and m1 is not None and m1 <= m0 + REFUSE_MASS_TOL)
    return ("as_predicted" if ok else "falsified"), {"ref": ref, "mass_tol": REFUSE_MASS_TOL}


def grade_of_early(eats):
    """OF_EARLY: no eat refused (validStart false) at a settled Overfull level of 3 or less."""
    tried = [e for e in eats if e.get("pre_level") is not None]
    early = [e.get("label") for e in tried if e["pre_level"] <= 3 and e.get("validStart") is False]
    if not tried:
        return "unmeasured", {"early": early}
    return ("falsified" if early else "as_predicted"), {"early": early, "tried": len(tried)}


def grade_of_timer(reads):
    """OF_TIMER: on settled reads, the timer above TIMER_REFUSE at Overfull 4 and at or under it below 4."""
    s = [r for r in reads if r.get("settled") and r.get("level") is not None and num(r.get("timer")) is not None]
    four = [r for r in s if r["level"] == 4]
    obs = {"settled": len(s), "four": len(four),
           "bad": [r for r in s if (r["level"] == 4) != (num(r["timer"]) > TIMER_REFUSE)][:10]}
    if not four:
        return "unmeasured", obs
    return ("falsified" if obs["bad"] else "as_predicted"), obs


def grade_of_nausea(hold):
    """OF_NAUSEA: the trigger read (the first settled read at Overfull 4, review M4: "at once"): FOOD_SICKNESS at least
    FOOD_SICK_STEP - NAUSEA_TOL and SICK at 1 or more."""
    if not hold or hold.get("level") != 4:
        return "unmeasured", {"hold": hold}
    fs, sick = num(hold.get("food_sick")), num(hold.get("sick"))
    if fs is None or sick is None:
        return "unmeasured", {"hold": hold}
    ok = fs >= FOOD_SICK_STEP - NAUSEA_TOL and sick >= 1
    return ("as_predicted" if ok else "falsified"), {"hold": hold}


def grade_of_endurance(reads, severity):
    """OF_ENDURANCE: settled reads at Overfull 3 or more: ENDURANCE at most END_CAP + END_TOL and the moodle at 1 or
    more; unmeasured when NR.Severity is under SEVERITY_MIN (the slowing off) or no such read."""
    s = [r for r in reads if r.get("settled2") and (r.get("level") or 0) >= 3 and num(r.get("endurance")) is not None]
    obs = {"reads": len(s), "severity": severity}
    if severity is None or severity < SEVERITY_MIN or not s:
        return "unmeasured", obs
    obs["bad"] = [r for r in s if num(r["endurance"]) > END_CAP + END_TOL or (num(r.get("end_moodle")) or 0) < 1]
    obs["max_endurance"] = max(num(r["endurance"]) for r in s)
    return ("falsified" if obs["bad"] else "as_predicted"), obs


def grade_onset(rows, set_age, flag="drain.starveAcute"):
    """ONSET: the ring's first `flag` row after set_age at STARVE_ONSET_H unfed hours (age - drain.fedAgeH) within
    ONSET_TOL_H, the row before it under; HUNGER over 0.70 on it or the next row; at most HUNGER_CAP + CAP_EPS on every
    row after the set before it."""
    after = [r for r in rows if ring_age(r) is not None and ring_age(r) > set_age]
    i = next((k for k, r in enumerate(after) if is_true(r.get(flag))), None)
    if i is None:
        return "unmeasured", {"why": "no onset row in the ring after the set", "rows": len(after)}
    r = after[i]

    def unfed(x):
        a, f = ring_age(x), num(x.get("drain.fedAgeH"))
        return None if a is None or f is None else a - f
    u = unfed(r)
    u_prev = unfed(after[i - 1]) if i > 0 else None
    hs = [num(x.get("HUNGER")) for x in after[i:i + 2]]
    pre = [num(x.get("HUNGER")) for x in after[:i]]
    obs = {"onset_s": r.get("s"), "onset_age": ring_age(r), "unfed": u, "unfed_prev": u_prev, "hunger_at": hs,
           "pre_max": max([h for h in pre if h is not None], default=None)}
    if u is None:
        return "unmeasured", obs
    ok = (abs(u - STARVE_ONSET_H) <= ONSET_TOL_H and (u_prev is None or u_prev < STARVE_ONSET_H)
          and any(h is not None and h > HUNGRY_AT[3] for h in hs)
          and all(h is None or h <= HUNGER_CAP + CAP_EPS for h in pre))
    return ("as_predicted" if ok else "falsified"), obs


def onset_age(rows, set_age, flag):
    for r in rows:
        if ring_age(r) is not None and ring_age(r) > set_age and is_true(r.get(flag)):
            return ring_age(r)
    return None


def grade_shown(pairs, a_on, key, level=4):
    """STARVING_SHOWN / PARCHED_SHOWN: the server's first read after the onset row (to ONSET_SHOW_GM after it) reads the
    moodle at `level`."""
    if a_on is None:
        return "unmeasured", {"why": "no onset"}
    win = [r for r in server_reads(pairs) if a_on < num(r["worldAge"]) <= a_on + ONSET_SHOW_GM / 60.0]
    lv = [num(g(r, "moodles", key)) for r in win]
    obs = {"onset_age": a_on, "key": key, "levels": lv, "window_gm": ONSET_SHOW_GM}
    if not win:
        return "unmeasured", obs
    return ("as_predicted" if lv and lv[-1] == level else "falsified"), obs


def grade_const(reads, a_on, a_off, red0):
    """CONST: every constant read (age, value) before the onset at red0 and every read in (onset, off) at 0; the
    ring's last-written values (writer.h.admin.red) are recorded beside it. Needs one read on each side."""
    pre = [(a, v) for a, v in reads if a is not None and v is not None and a_on is not None and a < a_on]
    on = [(a, v) for a, v in reads if a is not None and v is not None and a_on is not None
          and a_on < a and (a_off is None or a < a_off)]
    obs = {"pre": pre, "on": on, "red0": red0}
    if not pre or not on or red0 is None:
        return "unmeasured", obs
    ok = all(abs(v - red0) <= 1e-6 for _, v in pre) and all(abs(v) <= 1e-9 for _, v in on)
    return ("as_predicted" if ok else "falsified"), obs


def grade_drain_rate(points, floor, top, rate_day, a_max=None):
    """DRAIN_RATE / DEHYD_DRAIN: the least-squares health slope over the points strictly between floor + 0.5 and
    top - 0.3 and (review L3) before a_max, the floor's reach, spanning DRAIN_MIN_GH, within DRAIN_TOL_REL of
    rate_day / 24 a game hour."""
    pts = [(p["age"], p["overall"]) for p in points if p.get("age") is not None and p.get("overall") is not None
           and floor + 0.5 < p["overall"] < top - 0.3 and (a_max is None or p["age"] < a_max)]
    obs = {"n": len(pts), "floor": floor, "top": top, "predicted_per_gh": rate_day / 24.0}
    if len(pts) < 4 or pts[-1][0] - pts[0][0] < DRAIN_MIN_GH:
        return "unmeasured", obs
    s = fit_slope(pts)
    obs["rate_per_gh"] = -s
    obs["rate_per_day"] = -s * 24.0
    obs["rel_err"] = (-s * 24.0 - rate_day) / rate_day
    return ("as_predicted" if abs(obs["rel_err"]) <= DRAIN_TOL_REL else "falsified"), obs


def floor_at(rows, age):
    """The ring's drain.targetFloor at the last row at or before age (the first row when none before)."""
    best = None
    for r in rows:
        a = ring_age(r)
        if a is None or num(r.get("drain.targetFloor")) is None:
            continue
        if a <= age or best is None:
            best = num(r["drain.targetFloor"])
        if a > age:
            break
    return best


def grade_floor_hold(points, rows, tol, a_end=None):
    """FLOOR_HOLD / DEHYD_FLOOR: from the first point within FLOOR_REACH of the ring's floor, every point to a_end
    within tol of the floor at its age, the hold spanning FLOOR_HOLD_GH less a tenth."""
    pts = [p for p in points if p.get("age") is not None and p.get("overall") is not None
           and (a_end is None or p["age"] <= a_end)]
    i = next((k for k, p in enumerate(pts) if floor_at(rows, p["age"]) is not None
              and p["overall"] <= floor_at(rows, p["age"]) + FLOOR_REACH), None)
    if i is None:
        return "unmeasured", {"why": "the floor was not reached", "points": len(pts)}
    hold = pts[i:]
    dev = [p["overall"] - floor_at(rows, p["age"]) for p in hold]
    obs = {"reached_age": hold[0]["age"], "span_gh": hold[-1]["age"] - hold[0]["age"], "n": len(hold),
           "dev_min": min(dev), "dev_max": max(dev), "floor_first": floor_at(rows, hold[0]["age"]), "tol": tol}
    if obs["span_gh"] < FLOOR_HOLD_GH * 0.9:
        return "unmeasured", obs
    ok = all(abs(d) <= tol for d in dev)
    return ("as_predicted" if ok else "falsified"), obs


def grade_recover(rec):
    """RECOVER: rec {landed_age, off_age (the ring's first starveAcute false row after the landing), const_after,
    red0, points (after the landing)}."""
    a = num(rec.get("landed_age"))
    pts = [p for p in rec.get("points") or [] if p.get("overall") is not None and p.get("age") is not None]
    obs = {k: rec.get(k) for k in ("landed_age", "off_age", "const_after", "red0")}
    if a is None or not pts:
        return "unmeasured", obs
    h0 = pts[0]["overall"]
    span = pts[-1]["age"] - pts[0]["age"]
    obs.update({"h0": h0, "h_end": pts[-1]["overall"], "rise": pts[-1]["overall"] - h0, "span_gh": span,
                "min": min(p["overall"] for p in pts)})
    if span < RECOVER_GH * 0.9:
        return "unmeasured", obs
    off = num(rec.get("off_age"))
    ok = (off is not None and off - a <= RECOVER_SHOW_GM / 60.0
          and rec.get("const_after") is not None and rec.get("red0") is not None
          and abs(rec["const_after"] - rec["red0"]) <= 1e-6
          and obs["rise"] >= RECOVER_MIN and obs["min"] >= h0 - FLOOR_TOL)
    return ("as_predicted" if ok else "falsified"), obs


def grade_n_bleed(w, red0):
    """N_BLEED: the bleed's window rate within N_TOL_REL of WOUND_X451 + red0 x M_H, BLEEDING 4 at both ends."""
    r = window_rate(w)
    lv = level_at_ends(w, "BLEEDING")
    pred = None if red0 is None else WOUND_X451 + red0 * M_H
    obs = dict(r, levels=lv, predicted_per_gh=pred)
    if lv != (4, 4) or r["rate_per_gh"] is None or pred is None:
        return "unmeasured", obs
    obs["rel_err"] = (r["rate_per_gh"] - pred) / pred
    return ("as_predicted" if abs(obs["rel_err"]) <= N_TOL_REL else "falsified"), obs


def grade_s_bleed(ws, wn, red0, starve_gh, reapplied_delta):
    """S_BLEED: starving, the constant 0 at both ends, BLEEDING 4 at both ends: the rate minus N's minus the starvation
    drain within S_TOL_REL x red0 x M_H of 0, and the re-applied counter rose."""
    rs, rn = window_rate(ws), window_rate(wn)
    lv = level_at_ends(ws, "BLEEDING")
    c = (const_of(ws.get("k0")), const_of(ws.get("k1")))
    obs = {"S": rs, "N": rn, "levels": lv, "const": c, "starve_per_gh": starve_gh, "reapplied_delta": reapplied_delta,
           "bias_bound_per_gh": REGEN_STANDARD * M_H * BLEED_WEIGHT / PARTS,
           "parts_N_h0": g(wn, "h0", "parts")}
    if lv != (4, 4) or rs["rate_per_gh"] is None or rn["rate_per_gh"] is None or red0 is None or None in c:
        return "unmeasured", obs
    obs["excess_per_gh"] = rs["rate_per_gh"] - rn["rate_per_gh"] - starve_gh
    obs["tol_per_gh"] = S_TOL_REL * red0 * M_H
    ok = (abs(obs["excess_per_gh"]) <= obs["tol_per_gh"] and all(abs(x) <= 1e-9 for x in c)
          and (reapplied_delta or 0) > 0)
    return ("as_predicted" if ok else "falsified"), obs


def grade_sick(w, red0, extra_gh):
    """S_SICK / P_SICK: SICK 4 at both ends, the constant 0 at both ends: the rate within SICK_TOL_REL of red0 x M_H +
    extra_gh (the starvation drain while above the floor; 0 for P_SICK, whose health sits at the floor)."""
    r = window_rate(w)
    lv = level_at_ends(w, "SICK")
    c = (const_of(w.get("k0")), const_of(w.get("k1")))
    pred = None if red0 is None else red0 * M_H + extra_gh
    obs = dict(r, levels=lv, const=c, predicted_per_gh=pred)
    if lv != (4, 4) or r["rate_per_gh"] is None or pred is None or None in c:
        return "unmeasured", obs
    obs["rel_err"] = (r["rate_per_gh"] - pred) / pred
    ok = abs(obs["rel_err"]) <= SICK_TOL_REL and all(abs(x) <= 1e-9 for x in c)
    return ("as_predicted" if ok else "falsified"), obs


def grade_dehyd_onset(rows, set_age):
    """DEHYD_ONSET: the ring's first drain.dehydrated row after set_age has fluids.dehydPct at DEHYD_ONSET_PCT or more
    and the row before it under; THIRST over THIRST_4 on it or the next row; at most THIRST_CAP + CAP_EPS before it."""
    after = [r for r in rows if ring_age(r) is not None and ring_age(r) > set_age]
    i = next((k for k, r in enumerate(after) if is_true(r.get("drain.dehydrated"))), None)
    if i is None:
        return "unmeasured", {"why": "no onset row in the ring after the set", "rows": len(after)}
    r = after[i]
    p = num(r.get("fluids.dehydPct"))
    p_prev = num(after[i - 1].get("fluids.dehydPct")) if i > 0 else None
    ts = [num(x.get("THIRST")) for x in after[i:i + 2]]
    pre = [num(x.get("THIRST")) for x in after[:i]]
    obs = {"onset_s": r.get("s"), "onset_age": ring_age(r), "pct": p, "pct_prev": p_prev, "thirst_at": ts,
           "pre_max": max([t for t in pre if t is not None], default=None)}
    if p is None:
        return "unmeasured", obs
    ok = (p >= DEHYD_ONSET_PCT - 1e-9 and (p_prev is None or p_prev < DEHYD_ONSET_PCT)
          and any(t is not None and t > THIRST_4 for t in ts)
          and all(t is None or t <= THIRST_CAP + CAP_EPS for t in pre))
    return ("as_predicted" if ok else "falsified"), obs


def water_loss(rows, a0, a1):
    """The ring's fluids.water loss a game hour over (a0, a1] (least squares), with the conditions it needs (the stomach
    empty, both lanes at most STOMACH_EMPTY_G; no sweat; no landing or sip in the span) and the mean cold diuresis a
    game hour the rows carry (COLD_DIURESIS_LH x clamp(coldMult - 1, 0, 1) x 1000 g, K.fluids.losses), which the prediction
    adds."""
    rs = rows_between(rows, a0, a1)
    pts = [(ring_age(r), num(r.get("fluids.water"))) for r in rs]
    s = fit_slope(pts)
    cond = {"rows": len(rs), "span_gh": (ring_age(rs[-1]) - ring_age(rs[0])) if len(rs) > 1 else 0.0}
    cond["stomach_max"] = max([(num(r.get("stomach.liquid")) or 0) + (num(r.get("stomach.buffer.water")) or 0)
                               for r in rs], default=None)
    cond["sweat_max"] = max([num(r.get("fluids.sweatLmin")) or 0 for r in rs], default=None)
    cond["cold_max"] = max([num(r.get("body.coldMult")) or 1 for r in rs], default=None)
    colds = [COLD_DIURESIS_LH * clamp((num(r.get("body.coldMult")) or 1.0) - 1.0, 0.0, 1.0) * 1000.0 for r in rs]
    cond["cold_gh"] = sum(colds) / len(colds) if colds else 0.0
    land = [num(r.get(LANDED_G)) for r in rs if num(r.get(LANDED_G)) is not None]
    sips = [num(r.get(SIPS_G)) for r in rs if num(r.get(SIPS_G)) is not None]
    cond["landings"] = (land[-1] - land[0]) if land else None
    cond["sips"] = (sips[-1] - sips[0]) if sips else None
    cond["clean"] = (cond["stomach_max"] is not None and cond["stomach_max"] <= STOMACH_EMPTY_G
                     and (cond["sweat_max"] or 0) <= 0 and not cond["landings"] and not cond["sips"])
    return (None if s is None else -s), cond


def grade_loss(loss_gh, cond, lm, scale, tol_rel):
    """BASAL / LOSS_<arm>: the loss a game hour within tol_rel of basal_g_day(lm, scale) / 24 plus the span's mean cold
    diuresis, on a clean span of an hour or more."""
    pred = None if lm is None or scale is None else basal_g_day(lm, scale) / 24.0 + (cond.get("cold_gh") or 0.0)
    obs = {"loss_per_gh": loss_gh, "predicted_per_gh": pred, "lm": lm, "scale": scale, "cond": cond}
    if loss_gh is None or pred is None or not cond.get("clean") or cond.get("span_gh", 0) < 1.0 or pred <= 0:
        return "unmeasured", obs
    obs["rel_err"] = (loss_gh - pred) / pred
    return ("as_predicted" if abs(obs["rel_err"]) <= tol_rel else "falsified"), obs


def pct_rate(rows, a0, a1):
    """The ring's fluids.dehydPct rise a game hour over (a0, a1] (least squares); None under two rows."""
    return fit_slope([(ring_age(r), num(r.get("fluids.dehydPct"))) for r in rows_between(rows, a0, a1)])


def dehyd_pace(w, lm, pct_gh, drain_h, floor_reached, h_onset=100.0):
    """The live and the kernel first-floor hours without water from euhydration at full health. Live: DEHYD_ONSET_PCT
    over the ring's dehydPct rise a game hour, plus the drain's hours from the onset row to the floor, scaled from the
    health at the onset to 100. Kernel: DEHYD_ONSET_PCT / 100 x w kg x 1000 g over the deficit's growth a game hour,
    (basal_g_day(lm) - WATER_PER_MMOL x BASAL_NA) / 24 (the sodium loss lowers the euhydrated water, K.fluids.weu),
    plus (100 - floor) / (DEHYD_RATE / 24)."""
    out = {"w": w, "lm": lm, "pct_per_gh": pct_gh, "drain_h": drain_h, "floor": floor_reached, "h_onset": h_onset}
    if None in (w, lm, pct_gh, drain_h, floor_reached, h_onset) or pct_gh <= 0 or h_onset <= floor_reached:
        return out
    out["live_h"] = DEHYD_ONSET_PCT / pct_gh + drain_h * (100.0 - floor_reached) / (h_onset - floor_reached)
    grow = (basal_g_day(lm) - WATER_PER_MMOL * BASAL_NA) / 24.0
    out["kernel_h"] = DEHYD_ONSET_PCT / 100.0 * w * 1000.0 / grow + (100.0 - floor_reached) / (DEHYD_RATE / 24.0)
    return out


def grade_pace(p):
    """DEHYD_PACE: the live first-floor hour within PACE_TOL_H of the kernel's."""
    if p.get("live_h") is None:
        return "unmeasured", p
    return ("as_predicted" if abs(p["live_h"] - p["kernel_h"]) <= PACE_TOL_H else "falsified"), p


def dehyd_spec(p):
    """A reading, never a grade (review M3: graded, it would re-read DEHYD_PACE's hour against a band drawn round the
    kernel's): the live and the kernel first-floor hours beside the spec's SPEC_H and each one's gap to it."""
    return {"live_h": p.get("live_h"), "kernel_h": p.get("kernel_h"), "spec_h": SPEC_H,
            "live_gap_h": None if p.get("live_h") is None else p["live_h"] - SPEC_H,
            "kernel_gap_h": None if p.get("kernel_h") is None else p["kernel_h"] - SPEC_H}


def grade_scale(arms, stats_decrease):
    """SCALE: each arm's applied scale is TRAIT_SCALE x BASE's, and BASE's is 1 at StatsDecrease STATS_DECREASE_ONE."""
    base = num(g(arms, "BASE", "scale"))
    obs = {k: num(g(arms, k, "scale")) for k in TRAIT_SCALE}
    obs["stats_decrease"] = stats_decrease
    if base is None or any(obs[k] is None for k in TRAIT_SCALE):
        return "unmeasured", obs
    ok = all(abs(obs[k] - TRAIT_SCALE[k] * base) <= 1e-6 for k in TRAIT_SCALE)
    if stats_decrease == STATS_DECREASE_ONE:
        ok = ok and abs(base - 1.0) <= 1e-6
    return ("as_predicted" if ok else "falsified"), obs


def grade_ratio(arms, name):
    """RATIO_<arm>: the arm's loss over BASE's within RATIO_TOL[name] of TRAIT_SCALE[name]."""
    b, x = num(g(arms, "BASE", "loss")), num(g(arms, name, "loss"))
    obs = {"base": b, "arm": x, "want": TRAIT_SCALE[name], "tol": RATIO_TOL[name]}
    if not b or x is None or not g(arms, "BASE", "clean") or not g(arms, name, "clean"):
        return "unmeasured", obs
    obs["ratio"] = x / b
    return ("as_predicted" if abs(obs["ratio"] - TRAIT_SCALE[name]) <= RATIO_TOL[name] else "falsified"), obs


def grade_traits(arms):
    """TRAITS: stats.get lists High Thirst only in HIGH and Low Thirst only in LOW."""
    want = {"BASE": (False, False), "HIGH": (True, False), "OFF": (False, False), "LOW": (False, True)}
    obs, n, bad = {}, 0, False
    for k, (hi, lo) in want.items():
        t = g(arms, k, "traits")
        if not isinstance(t, dict):
            continue
        n += 1
        got = (t.get("HighThirst") is True, t.get("LowThirst") is True)
        obs[k] = {"want": [hi, lo], "got": list(got)}
        bad = bad or got != (hi, lo)
    if n < len(want):
        return "unmeasured", obs
    return ("falsified" if bad else "as_predicted"), obs


def grade_z(out):
    """Z: no mod error line in the server log and admin never parked; unmeasured when the logs were not read."""
    logs = out.get("logs")
    if not isinstance(logs, dict) or "mod_error" not in logs:
        return "unmeasured", {"why": "the logs were not read"}
    errs = logs["mod_error"]
    parked = out.get("admin_lua_error")
    obs = {"mod_error": errs[:10] if isinstance(errs, list) else errs, "admin_lua_error": parked}
    return ("as_predicted" if not errs and parked is False else "falsified"), obs


def grade_ring(pages):
    """RING: every page read with its file, and the ring's errors 0."""
    errs = [num(g(p, "reply", "errors")) for p in pages]
    if not pages:
        return "unmeasured", {"pages": 0}
    ok = all(p.get("file") for p in pages) and all((e or 0) == 0 for e in errs)
    return ("as_predicted" if ok else "falsified"), {"pages": len(pages), "errors": errs}


def grade_h1(h1, ring_start):
    """H1: the ring's record paths resolved at the start (lua.read missing none) and the ring armed."""
    miss = g(h1, "missing") or {}
    ok = g(h1, "ok") is True and g(ring_start, "ok") is True and not miss
    return ("as_predicted" if ok else "falsified"), {"missing": miss, "ring_ok": g(ring_start, "ok")}


# ================================================================ the x452 replay bookkeeping (x44's, this lib's foods)
def mod_eat_event(full, s, label=None):
    import replay_live as RL
    f = FOODS[full]
    return {"s": s, "kind": "eat", "fullType": full, "cal": RL.float32(f["cal"]), "carb": RL.float32(f["carb"]),
            "lip": RL.float32(f["lip"]), "pro": RL.float32(f["pro"]),
            "hunger": RL.float32(f["hunger_script"]) / 100.0, "foodType": f["foodType"], "label": label}


def build_events(rows, eats, drinks=()):
    """x44's: each landed eat keyed (in queue order) to the first ring row whose intake eats count rose; a drink's
    litres split over the ring rows whose sips rose inside [age0, age1 + 0.1]."""
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
    out = []
    for r in rows:
        v = num(r.get("fluids.autoDrop"))
        if v is not None and v > 0 and r.get("s") is not None:
            out.append({"s": r["s"], "kind": "autodrop", "g": 2.0 * v * 1000.0, "label": "autodrop",
                        "autoDrop": v, "age": r.get("age")})
    return out


def ring_moving_events(rows):
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


def replay_events(rows, eats, start_age, drinks=()):
    events0, notes = build_events(rows, eats, drinks)
    drops, moves = autodrop_events(rows), ring_moving_events(rows)
    first = next((r for r in rows if num(r.get("age")) is not None
                  and (start_age is None or r["age"] > start_age + 1e-9)), None)
    held = [e for e in drops + moves if first is not None and e["s"] <= first["s"]]
    keep = [e for e in drops + moves if first is None or e["s"] > first["s"]]
    events = sorted(events0 + keep, key=lambda e: e["s"])
    return events, {"notes": notes, "held_in_start": held,
                    "autodrops": len([e for e in keep if e["kind"] == "autodrop"]),
                    "moves": len([e for e in keep if e["kind"] == "activity"])}


def replay_grade(ring_rows, events, start, tol, paths=None, player=None, start_stats=None):
    """The HEAD kernel replay of the ring (tools/replay_live.replay_live, sleep off) and its diff under tol."""
    import replay_live as RL
    rows, be = RL.replay_live(ring_rows, events, start, paths=paths, user=USER, player=player,
                              start_stats=start_stats, sleep_allowed=False)
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


def profile_doc_checks(name, doc, text=""):
    """The profile's TOML: its name, its header naming its own file, the fixture, the one admin client, sleep off,
    PZTestKit and the staged copy, Nutrition false, DayLength 1, two version verify rows."""
    mods = [m.get("id") for m in doc.get("mods") or []]
    paths = [m.get("path") for m in doc.get("mods") or [] if m.get("id") == NR]
    sb = doc.get("sandbox") or {}
    srv = doc.get("server") or {}
    ver = doc.get("verify") or []
    return {"named_profile": name == PROFILE,
            "header_names_file": text.startswith(f"# testing/profiles/{name}.toml"),
            "fixture_default": doc.get("fixture") == "default",
            "one_admin_client": doc.get("clients", ["admin"]) == ["admin"],
            "sleep_off": srv.get("SleepAllowed") is False and srv.get("SleepNeeded") is False,
            "mods_staged": mods == ["PZTestKit", NR] and paths == [STAGE_MOD],
            "nutrition_false": sb.get("Nutrition") is False,
            "day_length": sb.get("DayLength") == MOD_DAY_LENGTH,
            "verify_version": sum(1 for v in ver if v.get("args") == f"{NR}.version") >= 2}


def predictions_named():
    """x452's cadence bands all named (review M1): no boot on a band still None."""
    return CAD_H_TARGET is not None and all(v is not None for v in CAD_P_TARGETS.values())


def preboot(key, profile_name, prefix, driver_file, repo=REPO):
    """The driver's prefix, profile and file name its session (CLAUDE.md s5); no artifact of the prefix committed; the
    profile's TOML; the harness markers in the repository. Returns (checks, ok)."""
    import tomllib
    c = {"key": key in SESSIONS, "prefix": prefix == key, "profile": profile_name == PROFILE,
         "driver_file": os.path.basename(driver_file) == g(SESSIONS, key, "driver")}
    c["no_prior_artifact"] = not glob.glob(os.path.join(repo, "testing", "artifacts", prefix + "-*"))
    if key == "x452":
        c["cadence_bands_named"] = predictions_named()
    try:
        with open(os.path.join(repo, "testing", "profiles", profile_name + ".toml"), encoding="utf-8") as fh:
            text = fh.read()
        prof = profile_doc_checks(profile_name, tomllib.loads(text), text)
    except (OSError, ValueError) as e:
        prof = {"profile_read": False, "error": f"{type(e).__name__}: {e}"}
    c["profile_checks"] = prof
    found, ok = harness_markers_ok(repo)
    c["harness_markers"] = ok
    c["harness_found"] = found
    good = all(v is True for k, v in c.items() if k not in ("profile_checks", "harness_found")) and \
        all(v is True for k, v in prof.items() if k != "error")
    return c, good


def staged_gate(repo=REPO, commit=STAGED_FROM, stage_root=STAGE_ROOT, stage_mod=STAGE_MOD):
    """x45's: the staged copy against release_pack.manifest() of mod/ at the pinned commit (a git archive into a scratch
    folder): the staged MANIFEST and the staged tree must both equal it; the staged NR_Core.lua's version is read for
    the verify rows."""
    import release_pack as RP
    M = {"commit": commit, "staged_manifest": f"{stage_root}/{MANIFEST_NAME}", "staged_mod": stage_mod}
    try:
        M["commit_full"] = subprocess.run(["git", "rev-parse", commit], cwd=repo, capture_output=True,
                                          text=True).stdout.strip()
        M["mod_commit"] = subprocess.run(["git", "log", "-1", "--format=%h", commit, "--", MOD_DIR], cwd=repo,
                                         capture_output=True, text=True).stdout.strip()
        with tempfile.TemporaryDirectory() as tmp:
            arch = subprocess.run(["git", "archive", "--format=tar", commit, MOD_DIR], cwd=repo, capture_output=True)
            if arch.returncode != 0:
                raise OSError(arch.stderr.decode("utf-8", "replace")[:300])
            import io
            import tarfile
            with tarfile.open(fileobj=io.BytesIO(arch.stdout)) as tf:
                tf.extractall(tmp, filter="data")
            pinned = RP.manifest(os.path.join(tmp, *MOD_DIR.split("/")))
        mpath = os.path.join(repo, stage_root, MANIFEST_NAME)
        M["staged_manifest_sha256"] = X.sha256_file(mpath)
        with open(mpath, encoding="utf-8") as fh:
            staged = json.load(fh)
        booted = RP.manifest(os.path.join(repo, stage_mod))
        M["files"] = len(pinned)
        M["staged_equals_commit"] = staged == pinned
        M["staged_tree_equals_commit"] = booted == pinned
        if staged != pinned:
            M["diff_staged_vs_commit"] = RP.diff(staged, pinned)
        if booted != pinned:
            M["diff_tree_vs_commit"] = RP.diff(booted, pinned)
        with open(os.path.join(repo, stage_mod, *STAGED_CORE.split("/")), encoding="utf-8") as fh:
            m = re.search(r'version\s*=\s*"([^"]+)"', fh.read())
        M["staged_version"] = m.group(1) if m else None
    except (OSError, ValueError, KeyError) as e:
        M["error"] = f"{type(e).__name__}: {e}"
    M["ok"] = (M.get("staged_equals_commit") is True and M.get("staged_tree_equals_commit") is True
               and "error" not in M)
    return M


# ================================================================ the session
class Sess:
    """One session's phases over an xlib.Xs; every wait goes through xs.clock and xs.sleep, so the tests run it fast."""

    def __init__(self, xs, key, run_dir=None):
        self.xs = xs
        self.out = xs.out
        self.key = key
        self.spec = SESSIONS[key]
        self.D = self.out.setdefault("checks", {})
        self.run_dir = run_dir
        self.speeds = self.out.setdefault("speeds", [])
        self.cur_speed = None
        self.restore_to = None
        self.pages = []
        self.eats = []
        self.pairs = []
        self.points = []
        self.consts = []                     # (age, value) of every constant read after S
        self.sets = self.out.setdefault("sets", [])
        self.drinks = []
        self.red0 = None

    # -- plumbing
    def k(self, tag, side, cmd, args="", log=True):
        return self.xs.keep(self.xs.step(tag, side, cmd, args, log=log))

    def lread(self, tag, side, root, paths, log=True):
        return self.k(tag, side, "lua.read", " ".join([root] + list(paths)), log=log)

    def rec(self, tag, paths, log=False):
        return vals(self.lread(tag, SRV, f"record:{USER}", paths, log=log))

    def sleep_until(self, t_end):
        while self.xs.clock() < t_end - 1e-6:
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

    def body_run(self, phases):
        """Each phase through xs.run_phase; once the budget stopped a phase or the bus died, only the closing phases
        (the clock restore, the cleanup, the ring read, the after-reads) still run."""
        closing = set(self.closing_names())
        for name, fn in phases:
            if self.xs.parked():
                self.out["abort"] = f"admin parked in the debugger before phase {name}"
                break
            stopped = self.out.get("budget_stop") or self.xs.bus_dead or self.out.get("stop_reason")
            if stopped and name not in closing:
                self.out.setdefault("skipped_phases", []).append(name)
                self.xs.note(f"phase {name} skipped: an earlier phase stopped")
                continue
            self.xs.run_phase(name, fn)

    def closing_names(self):
        return ("K", "C", "R", "T")

    # -- the clock
    def snap(self, tag, log=False):
        return self.xs.snap(tag, log=log)

    def age(self, tag="age"):
        return num(self.snap(tag).get("worldAge"))

    def speed(self, n, tag):
        """x44's: RCON settimespeed n; time.multiplier n only when the RCON command fails; the trueMult read after."""
        r = self.xs.rcon(f"settimespeed {int(n)}", tag)
        row = {"want": n, "rcon_ok": r.get("ok")}
        if not r.get("ok"):
            row["fallback"] = self.k(tag + "_mult", SRV, "time.multiplier", f"{n}").get("raw")
        s = self.snap(tag + "_t", log=True)
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

    def set_mult(self, v, tag):
        """A fractional true multiplier through time.multiplier (x453), read back off time.snapshot."""
        row = {"want": v, "reply": self.k(tag, SRV, "time.multiplier", f"{v}").get("raw")}
        s = self.snap(tag + "_t", log=True)
        row.update({"trueMult": num(s.get("trueMult")), "age": num(s.get("worldAge")), "tag": tag, "unit": SPEED_UNIT})
        row["ok"] = row["trueMult"] is not None and abs(row["trueMult"] - v) <= 1e-6 * max(1.0, v)
        self.speeds.append(row)
        self.cur_speed = v
        return row

    def clock_read(self, tag="S_clock"):
        s = self.snap(tag, log=True)
        self.restore_to = num(s.get("trueMult"))
        return s

    def restore_clock(self):
        """Phase C: the clock back to the trueMult read at phase S (an integer speed through RCON; time.multiplier for a
        fractional one, or when the RCON speed did not read back), read back."""
        v = self.restore_to
        row = {"restore_to": v}
        if v is None:
            self.xs.note("restore: the start's trueMult is unread; restored to speed 1")
            v = 1.0
        if abs(v - round(v)) < 1e-6 and round(v) >= 1:
            row["set"] = self.speed(int(round(v)), "C_restore")
        if not g(row, "set", "ok"):                 # a fractional start, or settimespeed left a time.multiplier value
            row["set_mult"] = {"reply": self.k("C_restore_mult", SRV, "time.multiplier", f"{v}").get("raw")}
        s = self.snap("C_restore_t", log=True)
        row["unit"] = SPEED_UNIT
        row["trueMult_after"] = num(s.get("trueMult"))
        row["ok"] = row["trueMult_after"] is not None and abs(row["trueMult_after"] - v) <= 1e-6 * max(1.0, v)
        self.D["restore"] = row

    def run_until(self, end_age, speed, tag, every_s=None, fn=None, stop=None, mult=False):
        """At `speed` (a true multiplier through time.multiplier when mult) until the world age reaches end_age or
        stop(age) holds; fn(age) every every_s wall seconds. Returns the last age read."""
        if mult:
            if self.cur_speed != speed:
                self.set_mult(speed, f"{tag}_mult")
        else:
            self.set_speed(speed, f"{tag}_speed")
        last, a = -1e18, None
        while True:
            self.xs.check()
            a = self.age(tag + "_a")
            if a is not None and (a >= end_age or (stop is not None and stop(a))):
                break
            if fn is not None and every_s is not None and self.xs.clock() - last >= every_s:
                last = self.xs.clock()
                fn(a)
                continue
            self.xs.sleep(POLL_S)
        return a

    # -- reads
    def stats(self, tag, side=SRV, log=False):
        a = self.k(tag, side, "stats.get", USER if side == SRV else "", log=log)
        row = {k: a.get(k) for k in STATS_KEYS}
        row["moodles"] = a.get("moodles") if isinstance(a.get("moodles"), dict) else {}
        row["traits"] = a.get("traits") if isinstance(a.get("traits"), dict) else {}
        row.update({"wall": a.get("wall"), "wall_after": a.get("wall_after"), "side": side, "raw": a.get("raw")})
        return row

    def pair(self, tag):
        p = {"tag": tag, "s0": self.stats(tag + "_s0"), "c": self.stats(tag + "_c", side=CLI),
             "s1": self.stats(tag + "_s1")}
        self.pairs.append(p)
        return p

    def health_point(self, tag):
        """A health read bracketed by two clock reads: its age the mean, its skew their spread."""
        a0 = num(self.snap(tag + "_a0").get("worldAge"))
        h = self.k(tag + "_h", SRV, "health.get", USER, log=False)
        a1 = num(self.snap(tag + "_a1").get("worldAge"))
        p = {"tag": tag, "overall": num(h.get("overall")), "age": None if None in (a0, a1) else (a0 + a1) / 2.0,
             "skew_gh": None if None in (a0, a1) else a1 - a0, "wall": h.get("wall"), "phase": self.xs.cur_phase}
        self.points.append(p)
        return p

    def health(self, tag):
        return num(self.k(tag, SRV, "health.get", USER).get("overall"))

    def moodle(self, tag, name):
        return self.k(tag, SRV, "moodle.level", f"{USER} {name}", log=False)

    def constant(self, tag):
        r = self.k(tag, SRV, "witness.chain", f"{USER} getBodyDamage.getHealthReductionFromSevereBadMoodles")
        v = const_of(r)
        a = num(self.snap(tag + "_t").get("worldAge"))
        self.consts.append((a, v))
        return r

    def food_sick(self, tag):
        a = self.k(tag, SRV, "stats.all", USER, log=False)
        return num(g(a, "stats", "FoodSickness"))

    def intake(self, tag):
        v = vals(self.lread(tag, SRV, "_G", INTAKE_PATHS, log=False))
        return {k.rsplit(".", 1)[-1]: num(v.get(k)) for k in INTAKE_PATHS}

    def record_set(self, tag, path, value):
        r = self.k(tag, SRV, "record.set", f"{USER} {path} {value}")
        a = num(self.snap(tag + "_t").get("worldAge"))
        row = {"tag": tag, "path": path, "value": value, "age": a,
               "reply": {k: r.get(k) for k in ("ok", "before", "after", "error")}}
        self.sets.append(row)
        if r.get("ok") is not True:
            self.xs.note(f"{tag}: record.set {path} {value} answered {r.get('error') or r.get('raw')!r}")
        return row

    # -- the ring (x44's)
    def ring_start(self, paths, tag="H_ring"):
        return self.k(tag, SRV, "minute.ring", " ".join([USER, "start"] + list(paths)))

    def read_pages(self, tag, start_from=None):
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
                    if os.path.abspath(src) != os.path.abspath(dst):
                        shutil.copyfile(src, dst)
                    self.xs.copied.append(name + ".json")
                    pg["file"] = name + ".json"
            pages.append(pg)
            if not r.get("ok") or not r.get("more") or r.get("next") is None:
                break
            frm = r.get("next")
        return pages

    def ring_rows(self):
        rows = {}
        for f in self.pages:
            try:
                with open(os.path.join(self.run_dir, f), encoding="utf-8") as fh:
                    doc = json.load(fh)
            except (OSError, ValueError, TypeError):
                continue
            for r in doc.get("rows_list") or []:
                rows[r["s"]] = r
        return [rows[s] for s in sorted(rows)]

    # -- the eat
    def spawn(self, full, n, tag):
        row = self.xs.spawn(full, n, tag)
        self.out.setdefault("spawns", []).append(row)
        return row

    def eat(self, full, label, cap_s=EAT_CAP_S):
        """eat.action <type> 1 on the admin client with NO foodtimer.set (the mod owns the food timer, Plan 15 Task 8);
        the landing is the server's intake landed counter rising. A spawned other than "found" stops the eats."""
        row = {"label": label, "food": full, "landed": False}
        self.eats.append(row)
        b = self.intake(label + "_before")
        row["before"] = b
        row["age0"] = self.age(label + "_age0")
        q = self.k(label + "_eat", CLI, "eat.action", f"{full} 1")
        row.update({k: q.get(k) for k in ("queued", "spawned", "itemId", "validStart", "maxTime", "moodleFoodEaten",
                                          "error", "raw")})
        self.xs.spawned_stop(q, label)

        def fn():
            a = self.intake(label + "_poll")
            return (a.get("landed") is not None and b.get("landed") is not None and a["landed"] > b["landed"]), a
        p = self.poll(label + "_land", fn, cap_s)
        row["landed"] = p["done"]
        row["after"] = p["last"]
        row["eats_after"] = g(p, "last", "eats")
        row["landed_age"] = self.age(label + "_landed_t")
        return row

    def drink(self, container, label):
        """x44's m_drink and fill_gate: the container spawned now (RCON, prefilled), its server copy filled to DRINK_L of
        DRINK_FLUID, autodrink.probe before (the fill gate: the probe's first container is this one, with the fluid),
        drink.action <container> 1, the intake sips polled until they stop rising for SETTLE_POLLS polls after a rise,
        the litres drunk off autodrink.probe after."""
        row = {"label": label, "container": container, "fluid": DRINK_FLUID, "litres": DRINK_L, "drunk": None}
        self.drinks.append(row)
        row["spawn"] = self.spawn(container, 1, label + "_spawn")
        row["fill"] = self.k(label + "_fill", SRV, "fluid.fill", f"{USER} {container} {DRINK_FLUID} {DRINK_L}")
        row["probe_before"] = self.k(label + "_probe0", SRV, "autodrink.probe", USER)
        fill, pb = row["fill"], row["probe_before"]
        want = DRINK_FLUID.lower()
        row["fill_ok"] = (fill.get("ok") is True and str(fill.get("fluid", "")).lower() == want
                          and pb.get("item") == container and str(pb.get("fluid", "")).lower() == want)
        if not row["fill_ok"]:
            self.xs.note(f"drink {label}: fill gate failed (fill {fill.get('ok')}/{fill.get('fluid')}, "
                         f"probe {pb.get('item')}/{pb.get('fluid')})")
        b = self.intake(label + "_before")
        row["age0"] = self.age(label + "_age0")
        q = self.k(label + "_drink", CLI, "drink.action", f"{container} 1")
        row["queued"] = {k: q.get(k) for k in ("queued", "percentage", "spawned", "itemId", "filledRatioBefore")}
        self.xs.spawned_stop(q, label)
        st = {"last": b.get("sips"), "still": 0, "rose": False}

        def fn():
            a = self.intake(label + "_poll")
            v = a.get("sips")
            if v is not None and st["last"] is not None and v > st["last"]:
                st["rose"], st["still"] = True, 0
            elif st["rose"]:
                st["still"] += 1
            st["last"] = v
            return st["rose"] and st["still"] >= SETTLE_POLLS, a
        self.poll(label + "_sips", fn, DRINK_CAP_S)
        row["landed"] = st["rose"]
        row["age1"] = self.age(label + "_age1")
        row["probe_after"] = self.k(label + "_probe1", SRV, "autodrink.probe", USER)
        l0 = num(g(row, "fill", "litres"))
        l1 = num(g(row, "probe_after", "litres")) if g(row, "probe_after", "item") == container else 0.0
        row["drunk"] = (l0 - l1) if (l0 is not None and l1 is not None) else None
        if not st["rose"]:
            self.xs.note(f"drink {label}: sips never rose")
        self.D.setdefault("X", {}).setdefault("drinks", []).append(row)
        return row

    # ======================================================== the shared phases
    def phase_S(self):
        P = self.D["S"] = {}
        P["players"] = self.xs.step("S_players", SRV, "players")["ack"]
        P["sandbox"] = vals(self.lread("S_sv", SRV, "_G", ("SandboxVars.Nutrition", "SandboxVars.DayLength",
                                                             "NutritionRevamp.version", "SandboxVars.NR.Severity",
                                                             "SandboxVars.StatsDecrease",
                                                             "NutritionRevamp.server.nutrients.sleepDisabled")))
        P["clock"] = self.clock_read()
        P["nutrition"] = self.k("S_nutrition", SRV, "nutrition.get", USER)
        P["stats_all"] = self.k("S_stats_all", SRV, "stats.all", USER)
        P["probe"] = self.k("S_probe", SRV, "autodrink.probe", USER)
        if (num(P["probe"].get("containers")) or 0) > 0 or P["probe"].get("item") is not None:
            self.xs.note(f"S: admin carries a fluid container ({P['probe'].get('item')}); an auto-drink can land")
        c = self.constant("S_const")
        P["const"] = c
        self.red0 = const_of(c)
        if self.red0 is None or abs(self.red0 - CONST_DEFAULT) > 1e-6:
            self.xs.note(f"S: the severe-moodle constant read {self.red0}, not {CONST_DEFAULT}")
        P["health"] = self.health("S_health")
        P["pair"] = self.pair("S_pair")

    def phase_H(self):
        P = self.D["H"] = {}
        paths = list(RING[self.key])
        rec = [p for p in paths if not p.startswith("_G.")]
        P["ring_paths"] = paths
        P["h1_record"] = self.lread("H_h1", SRV, f"record:{USER}", rec + list(H1_EXTRA))
        P["h1_globals"] = self.lread("H_h1g", SRV, "_G", [p[3:] for p in paths if p.startswith("_G.")])
        P["ring_start"] = self.ring_start(paths)

    def phase_R(self):
        P = self.D["R"] = {}
        P["pages"] = self.read_pages("R")
        P["stop"] = self.k("R_ring_stop", SRV, "minute.ring", f"{USER} stop")
        self.pages = [p.get("file") for p in P["pages"] if p.get("file")]

    # ======================================================== x452: the day
    def phase_W(self):
        """x44's m_W: the store's next save of the record, the saved line kept as start.json and the stats as
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
        stats = self.k("W_stats", SRV, "stats.all", USER)
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
        for k, name in STAT_NAMES.items():
            v = num(g(stats, "stats", name))
            if v is not None:
                st[k] = v
        P["start_stats"] = st
        if self.run_dir:
            with open(os.path.join(self.run_dir, "start-stats.json"), "w", encoding="utf-8", newline="\n") as fh:
                json.dump(st, fh, indent=1, sort_keys=True)
            self.xs.copied.append("start-stats.json")

    def t9_read(self, tag):
        """Task 9's hunger-line hide: the item's tag set (client witness.chain), the hide tag's presence (lua.call) and
        the client tooltip's hide counters. Never a grade: the wrapper's draw cannot run without a hover."""
        r = {"tags": self.k(tag + "_tags", CLI, "witness.chain",
                            f"getInventory.getFirstTypeRecurse({T9_ITEM}).getTags"),
             "hideTag": self.k(tag + "_hidetag", CLI, "lua.call", "NutritionRevamp.client.tooltip.hideTag"),
             "counters": vals(self.lread(tag + "_ctr", CLI, "_G", ("NutritionRevamp.client.tooltip.stats.hidden",
                                                                    "NutritionRevamp.client.tooltip.stats.shown",
                                                                    "NutritionRevamp.client.tooltip.stats.draws"))),
             # review L5: the band's entry live (T.probe, test-only: line count and source) and the option it gates on
             "probe": self.k(tag + "_probe", CLI, "lua.call", f"NutritionRevamp.client.tooltip.probe {T9_ITEM}"),
             "optionOn": self.k(tag + "_opt", CLI, "lua.call", "NutritionRevamp.client.tooltip.optionOn")}
        v = str(g(r, "tags", "value") or "")
        r["hide_tag_in_set"] = "hide_hunger_change" in v.lower()
        return r

    def phase_F(self):
        P = self.D["F"] = {}
        if self.key == "x452":
            P["bolognese"] = self.spawn(BOLOGNESE, 3, "F_bol")
            P["banana"] = self.spawn(BANANA, SPAWN_BANANAS, "F_ban")
            P["t9_before"] = self.t9_read("F_t9")
        elif self.key == "x453":
            P["broccoli"] = self.spawn(BROCCOLI, SPAWN_N, "F_broc")
        else:
            P["bolognese"] = self.spawn(BOLOGNESE, 1, "F_bol")

    def meal(self, label, watch_gh):
        m = {"label": label}
        m["bol"] = self.eat(BOLOGNESE, label + "_bol")
        m["ban"] = self.eat(BANANA, label + "_ban")
        m["landed"] = bool(m["bol"].get("landed") and m["ban"].get("landed"))
        m["landed_age"] = m["ban"].get("landed_age")
        m["eats_after"] = m["ban"].get("eats_after")
        self.D.setdefault("X", {}).setdefault("meals", []).append(m)
        end = (m["landed_age"] or self.age(label + "_a")) + watch_gh
        self.run_until(end, 1, label + "_wf", every_s=PAIR_EVERY_S, fn=lambda a: self.pair(label + "_wf"))
        return m

    def phase_X452(self):
        P = self.D.setdefault("X", {})
        a = self.age("X_a0")
        plan = P["plan"] = day_plan(a)
        if not plan["lunch_at_1230"]:
            self.xs.note(f"X: X started past 12:30 - {MIN_LEAD_H} h; lunch at {plan['lunch']:.3f}")
        acts = []
        for i, (name, watch) in enumerate((("lunch", WF_WATCH1_GH), ("dinner", WF_WATCH_GH),
                                           ("breakfast", WF_WATCH_GH))):
            acts.append((plan[name], name, lambda n=name, w=watch: self.meal(n, w)))
            acts.append((plan[name] + DRINK_AFTER_H, f"drink{i + 1}",
                         lambda c=DRINKS[i], i=i: self.drink(c, f"X_drink{i + 1}")))
        for at, name, fn in sorted(acts, key=lambda x: x[0]):
            self.run_until(at - LEAD_H, SPEED_FAST, f"X_{name}_fast", every_s=FAST_PAIR_EVERY_S,
                           fn=lambda x, n=name: self.pair(f"X_{n}_pre"))
            self.run_until(at, 1, f"X_{name}_one")
            fn()
        P["reached"] = self.run_until(plan["end"], SPEED_FAST, "X_tail", every_s=FAST_PAIR_EVERY_S,
                                      fn=lambda x: self.pair("X_tail"))

    def phase_T(self):
        self.D["T9"] = {"after": self.t9_read("T_t9"), "before": g(self.D, "F", "t9_before"),
                        "verdict": "unmeasured",
                        "why": "the harness cannot hover a tooltip and lua.call passes scalars only, so the wrapper's "
                               "draw (T.hide around ISToolTipInv.render) cannot run; the reads show the tag set "
                               "outside a draw and the client's hide counters"}

    # ======================================================== x453: Overfull
    def stomach(self, tag):
        v = self.rec(tag, STOMACH_PATHS)
        m = stomach_mass(v)
        return {"mass": m, "level": overfull_level(m), "values": v, "age": self.age(tag + "_t")}

    def of_read(self, tag, since_landing_age, settled_gm=SETTLE_GM):
        """One Overfull read: the stomach (record), the server's stats.get (timer, endurance, moodles) and a pair."""
        st = self.stomach(tag + "_st")
        p = self.pair(tag + "_pair")
        a = num(p["s1"].get("worldAge"))
        dt = None if a is None or since_landing_age is None else (a - since_landing_age) * 60.0
        row = {"tag": tag, "mass": st["mass"], "level": st["level"], "age": a, "timer": p["s1"].get("foodTimer"),
               "endurance": p["s1"].get("endurance"), "end_moodle": g(p, "s1", "moodles", "endurance"),
               "food_eaten": g(p, "s1", "moodles", "foodEaten"), "since_gm": dt,
               "settled": dt is None or dt >= settled_gm, "settled2": dt is None or dt >= 2 * settled_gm}
        self.D.setdefault("X", {}).setdefault("reads", []).append(row)
        return row

    def phase_SEED(self):
        P = self.D["SEED"] = {}
        P["slow"] = self.set_mult(SLOW_MULT, "SEED_slow")
        st = self.stomach("SEED_st0")
        P["before"] = st
        w = num(st["values"].get("stomach.buffer.water"))
        cal = num(st["values"].get("stomach.buffer.calories"))
        if st["mass"] is None or w is None:
            raise RuntimeError(f"the stomach did not read: {st}")
        P["water"] = self.record_set("SEED_water", "stomach.buffer.water", f"{w + (SEED_G - st['mass']):.3f}")
        P["calories"] = self.record_set("SEED_kcal", "stomach.buffer.calories", f"{max(cal or 0.0, SEED_KCAL):.3f}")
        P["after"] = self.stomach("SEED_st1")

    def phase_X453(self):
        """One Broccoli at a time from the seeded stomach; each eat follows a settled read (SETTLE_GM game minutes and
        SETTLE_WALL_S after the last landing); the first read at Overfull 4 takes the refusal attempt at once."""
        P = self.D.setdefault("X", {})
        P["eats"] = []
        last_land, pre, e = None, None, None
        for i in range(MAX_EATS + 1):
            pre = self.of_read(f"X_pre{i}", last_land)
            if e is not None:
                e["post_level"], e["post_mass"] = pre["level"], pre["mass"]
            if pre["level"] == 4:
                break
            if i == MAX_EATS:
                self.xs.note(f"X: {MAX_EATS} eats and Overfull {pre['level']} ({pre['mass']} g); no refusal attempt")
                return
            e = self.eat(BROCCOLI, f"X_eat{i}")
            e["pre_level"], e["pre_mass"] = pre["level"], pre["mass"]
            P["eats"].append(e)
            if not e["landed"]:
                self.xs.note(f"X_eat{i}: not landed (validStart {e.get('validStart')!r}) at Overfull {pre['level']}")
                return
            last_land = e["landed_age"]
            t_wall = self.xs.clock() + SETTLE_WALL_S
            self.run_until((last_land or 0.0) + SETTLE_GM / 60.0, SLOW_MULT, f"X_settle{i}", mult=True)
            self.sleep_until(t_wall)
        if pre is None or pre["level"] != 4:
            return
        P["trigger"] = dict(pre, food_sick=self.food_sick("X_trig_fs"),
                            sick=num(self.moodle("X_trig_sick", "SICK").get("level")))
        ref = {"pre_level": pre["level"], "mass0": pre["mass"], "timer0": pre["timer"], "settled": pre["settled"],
               "food_eaten0": pre["food_eaten"]}
        st0 = self.stomach("X_ref_st0")
        ref["level_at_attempt"], ref["mass_at_attempt"] = st0["level"], st0["mass"]
        b = self.intake("X_ref_before")
        q = self.k("X_ref_eat", CLI, "eat.action", f"{BROCCOLI} 1")
        ref.update({k: q.get(k) for k in ("queued", "spawned", "validStart", "moodleFoodEaten", "maxTime")})
        self.sleep_until(self.xs.clock() + REFUSE_WAIT_S)
        a = self.intake("X_ref_after")
        ref["landed"] = (a.get("landed") is not None and b.get("landed") is not None and a["landed"] > b["landed"])
        ref["mass1"] = self.stomach("X_ref_st")["mass"]
        P["refusal"] = ref
        P["cancel"] = self.k("X_ref_cancel", CLI, "action.cancel")
        hold = self.of_read("X_hold0", last_land)
        hold["food_sick"] = self.food_sick("X_hold_fs")
        hold["sick"] = num(self.moodle("X_hold_sick", "SICK").get("level"))
        P["hold"] = hold
        end = (self.age("X_hold_a") or 0.0) + HOLD_GM / 60.0
        self.run_until(end, SLOW_MULT, "X_hold", every_s=PAIR_EVERY_S, fn=lambda x: self.of_read("X_hold", last_land),
                       mult=True)

    def phase_C453(self):
        self.D["cancel_end"] = self.k("C_cancel", CLI, "action.cancel")
        self.restore_clock()

    # ======================================================== x454 / x455: starvation
    def phase_A(self):
        """The onset: satiety.M 0 then drain.fedAgeH (age - 30 + ONSET_LEAD_H), at speed 1 until the ring's record reads
        starveAcute (and the constant 0), polled with pairs."""
        P = self.D["A"] = {}
        self.set_speed(1, "A_one")
        P["pre"] = self.rec("A_pre", ("satiety.M", "drain.fedAgeH", "drain.starveAcute"), log=True)
        P["set_M"] = self.record_set("A_M", "satiety.M", "0")
        a = self.age("A_a")
        P["set_fed"] = self.record_set("A_fed", "drain.fedAgeH", f"{a - STARVE_ONSET_H + ONSET_LEAD_H:.6f}")
        P["set_age"] = P["set_M"]["age"]
        seen = {"on": None}

        def fn():
            v = self.rec("A_poll", ("drain.starveAcute", "drain.starvedH"))
            p = self.pair("A_pair")
            if is_true(v.get("drain.starveAcute")) and seen["on"] is None:
                seen["on"] = num(p["s1"].get("worldAge"))
            done = seen["on"] is not None and (num(p["s1"].get("worldAge")) or 0) >= seen["on"] + ONSET_SHOW_GM / 60.0
            return done, v
        P["poll"] = self.poll("A_onset", fn, ONSET_CAP_S, 0.5)
        P["onset_polled_age"] = seen["on"]
        P["const"] = self.constant("A_const")
        P["drain"] = self.rec("A_drain", DRAIN_PATHS + ("drain.starving", "drain.bmi0"), log=True)

    def phase_B(self):
        """Health to HEALTH_SEED (health.reduce), then the drain to the floor at speed 5 with health points, and the
        floor's hold for FLOOR_HOLD_GH."""
        P = self.D["B"] = {}
        h = self.health("B_h0")
        P["h0"] = h
        if h is not None and h > HEALTH_SEED:
            P["reduce"] = self.k("B_reduce", SRV, "health.reduce", f"{USER} {h - HEALTH_SEED:.4f}")
        P["h1"] = self.health("B_h1")
        a0 = self.age("B_a0") or 0.0
        state = {"reached": None}

        def fn(a):
            p = self.health_point("B_pt")
            fl = num(self.rec("B_floor", ("drain.targetFloor",)).get("drain.targetFloor"))
            if state["reached"] is None and p["overall"] is not None and fl is not None \
                    and p["overall"] <= fl + FLOOR_REACH:
                state["reached"] = p["age"]

        def stop(a):
            return state["reached"] is not None and a >= state["reached"] + FLOOR_HOLD_GH
        P["end"] = self.run_until(a0 + DRAIN_CAP_GH, SPEED_FAST, "B_drain", every_s=POINT_EVERY_S, fn=fn, stop=stop)
        P["reached_age"] = state["reached"]
        P["const"] = self.constant("B_const")
        self.D["B_end_age"] = P["end"]

    def phase_E(self):
        """The can at speed 1; the recovery at speed 5 for RECOVER_GH with health points; the constant after."""
        P = self.D["E"] = {}
        self.set_speed(1, "E_one")
        e = self.eat(BOLOGNESE, "E_eat")
        P["eat"] = e
        P["pair"] = self.pair("E_pair")
        a = e.get("landed_age") or self.age("E_a") or 0.0
        self.sleep_until(self.xs.clock() + 2.0)
        P["const"] = self.constant("E_const")
        P["drain"] = self.rec("E_drain", ("drain.starveAcute", "drain.active", "satiety.M"), log=True)
        self.run_until(a + RECOVER_GH, SPEED_FAST, "E_rec", every_s=POINT_EVERY_S,
                       fn=lambda x: self.health_point("E_pt"))
        P["end_pair"] = self.pair("E_end_pair")

    def window(self, name, hold_s, moodles=(), const=False):
        """x451's: h0 health, s0 stats, the moodles (and the constant); the hold; the moodles (and the constant), s1,
        h1."""
        w = {"hold_s": hold_s}
        w["h0"] = self.k(name + "_h0", SRV, "health.get", USER)
        t_end = self.xs.clock() + hold_s
        w["s0"] = self.k(name + "_s0", SRV, "stats.get", USER)
        w["lv0"] = {m: self.moodle(f"{name}_lv0_{m}", m) for m in moodles}
        if const:
            w["k0"] = self.constant(name + "_k0")
        w["r0"] = num(vals(self.lread(name + "_r0", SRV, "_G", (REAPPLIED_G[3:],))).get(REAPPLIED_G[3:]))
        self.sleep_until(t_end)
        w["r1"] = num(vals(self.lread(name + "_r1", SRV, "_G", (REAPPLIED_G[3:],))).get(REAPPLIED_G[3:]))
        if const:
            w["k1"] = self.constant(name + "_k1")
        w["lv1"] = {m: self.moodle(f"{name}_lv1_{m}", m) for m in moodles}
        w["s1"] = self.k(name + "_s1", SRV, "stats.get", USER)
        w["h1"] = self.k(name + "_h1", SRV, "health.get", USER)
        self.D.setdefault("windows", {})[name] = w
        return w

    def bleed(self, tag, on):
        rows = []
        for i in BLEED_PARTS:
            rows.append(self.k(f"{tag}_bt{i}", SRV, "bodypart.set",
                               f"{USER} {i} bleedingTime {BLEED_TIME if on else 0:g}"))
            rows.append(self.k(f"{tag}_bl{i}", SRV, "bodypart.set", f"{USER} {i} bleeding {'true' if on else 'false'}"))
        return rows

    def phase_N(self):
        self.set_speed(1, "N_one")
        self.D["N_bleed"] = self.bleed("N_on", True)
        self.xs.sleep(SETTLE_S)
        self.window("N", WIN_S, ("BLEEDING",), const=True)
        self.D["N_clear"] = self.bleed("N_off", False)

    def phase_SB(self):
        self.set_speed(1, "SB_one")
        self.D["SB_bleed"] = self.bleed("SB_on", True)
        self.xs.sleep(SETTLE_S)
        self.window("SB", WIN_S, ("BLEEDING",), const=True)
        self.D["SB_clear"] = self.bleed("SB_off", False)

    def sick_window(self, name):
        self.set_speed(1, name + "_one")
        self.D[name + "_on"] = self.k(name + "_on", SRV, "stats.setany", f"{USER} FOOD_SICKNESS {FOOD_SICK_W:g}")
        self.xs.sleep(SETTLE_S)
        self.window(name, WIN_S, ("SICK",), const=True)
        self.D[name + "_off"] = self.k(name + "_off", SRV, "stats.setany", f"{USER} FOOD_SICKNESS 0")

    def phase_SS(self):
        self.sick_window("SS")

    def phase_K455(self):
        self.D["K"] = {"bleed": self.bleed("K_off", False),
                       "sick": self.k("K_sick", SRV, "stats.setany", f"{USER} FOOD_SICKNESS 0")}

    # ======================================================== x456: no water
    def phase_A456(self):
        """The deficit to DEHYD_SEED_PCT (fluids.water by the linear dehydPct), then speed 5 until the record reads
        dehydrated, polled with pairs."""
        P = self.D["A"] = {}
        self.set_speed(1, "A_one")
        v = self.rec("A_pre", ("fluids.water", "fluids.dehydPct", "body.fm", "body.lm", "body.lx"), log=True)
        P["pre"] = v
        w = sum(num(v.get(k)) or 0.0 for k in ("body.fm", "body.lm", "body.lx"))
        water, pct = num(v.get("fluids.water")), num(v.get("fluids.dehydPct"))
        if water is None or pct is None or w <= 0:
            raise RuntimeError(f"the fluids did not read: {v}")
        P["w"] = w
        P["set_water"] = self.record_set("A_water", "fluids.water",
                                         f"{water - (DEHYD_SEED_PCT - pct) * 10.0 * w:.3f}")
        P["set_age"] = P["set_water"]["age"]
        self.run_until((P["set_age"] or 0.0) + 2.0 / 60.0, 1, "A_settle")
        P["after"] = self.rec("A_after", ("fluids.water", "fluids.dehydPct", "drain.dehydrated"), log=True)
        P["pair"] = self.pair("A_pair0")
        seen = {"on": None, "h": None, "pct": None}

        def near(a):
            seen["pct"] = num(self.rec("A_near_poll", ("fluids.dehydPct",)).get("fluids.dehydPct"))
        P["near"] = self.run_until((P["set_age"] or 0.0) + DEHYD_CAP_GH, SPEED_FAST, "A_near", every_s=0.5, fn=near,
                                   stop=lambda a: (seen["pct"] or 0.0) >= DEHYD_NEAR_PCT)

        def fn(a):
            r = self.rec("A_poll", ("drain.dehydrated", "fluids.dehydPct"))
            p = self.pair("A_pair")
            if is_true(r.get("drain.dehydrated")) and seen["on"] is None:
                seen["on"] = num(p["s1"].get("worldAge"))
                seen["h"] = self.health("A_h_onset")

        def stop(a):
            return seen["on"] is not None and a >= seen["on"] + ONSET_SHOW_GM / 60.0
        P["end"] = self.run_until((P["set_age"] or 0.0) + DEHYD_CAP_GH, 1, "A_onset", every_s=0.5, fn=fn, stop=stop)
        P["onset_polled_age"] = seen["on"]
        P["health_at_onset"] = seen["h"]
        P["const"] = self.constant("A_const")

    def phase_B456(self):
        P = self.D["B"] = {}
        a0 = self.age("B_a0") or 0.0
        state = {"reached": None, "pair_wall": -1e18}

        def fn(a):
            p = self.health_point("B_pt")
            fl = num(self.rec("B_floor", ("drain.targetFloor",)).get("drain.targetFloor"))
            if state["reached"] is None and p["overall"] is not None and fl is not None \
                    and p["overall"] <= fl + FLOOR_REACH:
                state["reached"] = p["age"]
            if self.xs.clock() - state["pair_wall"] >= FAST_PAIR_EVERY_S:
                state["pair_wall"] = self.xs.clock()
                self.pair("B_pair")

        def stop(a):
            return state["reached"] is not None and a >= state["reached"] + FLOOR_HOLD_GH
        P["end"] = self.run_until(a0 + DRAIN_CAP_GH, SPEED_FAST, "B_drain", every_s=POINT_EVERY_S, fn=fn, stop=stop)
        P["reached_age"] = state["reached"]
        P["const"] = self.constant("B_const")
        self.D["B_end_age"] = P["end"]

    def phase_P(self):
        self.sick_window("P")

    # ======================================================== x457: the thirst traits
    def arm(self, name, change=None):
        P = self.D.setdefault("arms", {}).setdefault(name, {})
        self.set_speed(SPEED_FAST, f"{name}_fast")
        if change is not None:
            trait, op = change
            P["set"] = self.k(f"{name}_trait", SRV, "trait.set", f"{USER} {trait} {op}")
        a = self.age(f"{name}_a0") or 0.0
        self.run_until(a + ARM_SETTLE_GM / 60.0, SPEED_FAST, f"{name}_settle")
        P["scale"] = num(vals(self.lread(f"{name}_scale", SRV, "_G", (SCALE_PATH,))).get(SCALE_PATH))
        st = self.stats(f"{name}_stats", log=True)
        P["traits"] = {"HighThirst": g(st, "traits", "HighThirst"), "LowThirst": g(st, "traits", "LowThirst")}
        P["start"] = self.age(f"{name}_start")
        P["end"] = self.run_until((P["start"] or 0.0) + WIN_GH, SPEED_FAST, f"{name}_win")
        P["scale_end"] = num(vals(self.lread(f"{name}_scale1", SRV, "_G", (SCALE_PATH,))).get(SCALE_PATH))

    def phase_BASE(self):
        self.arm("BASE")

    def phase_HIGH(self):
        self.arm("HIGH", ("HighThirst", "add"))

    def phase_OFF(self):
        self.arm("OFF", ("HighThirst", "remove"))

    def phase_LOW(self):
        self.arm("LOW", ("LowThirst", "add"))

    def phase_K457(self):
        self.D["K"] = {"low_off": self.k("K_low", SRV, "trait.set", f"{USER} LowThirst remove"),
                       "high_off": self.k("K_high", SRV, "trait.set", f"{USER} HighThirst remove")}

    # ======================================================== the session table
    def phases(self):
        S, H, R = ("S", self.phase_S), ("H", self.phase_H), ("R", self.phase_R)
        C = ("C", self.restore_clock)
        return {
            "x452": [S, H, ("W", self.phase_W), ("F", self.phase_F), ("X", self.phase_X452), C, R,
                     ("T", self.phase_T)],
            "x453": [S, H, ("F", self.phase_F), ("SEED", self.phase_SEED), ("X", self.phase_X453),
                     ("C", self.phase_C453), R],
            "x454": [S, H, ("F", self.phase_F), ("A", self.phase_A), ("B", self.phase_B), ("E", self.phase_E), C, R],
            "x455": [S, H, ("N", self.phase_N), ("A", self.phase_A), ("SB", self.phase_SB), ("SS", self.phase_SS),
                     ("K", self.phase_K455), C, R],
            "x456": [S, H, ("A", self.phase_A456), ("B", self.phase_B456), ("P", self.phase_P), C, R],
            "x457": [S, H, ("BASE", self.phase_BASE), ("HIGH", self.phase_HIGH), ("OFF", self.phase_OFF),
                     ("LOW", self.phase_LOW), ("K", self.phase_K457), C, R],
        }[self.key]

    # ======================================================== the grades
    def _g(self, name, res, falsifier):
        v, obs = res
        self.xs.grade(name, v, obs, falsifier)

    def grade_all(self):
        rows = self.ring_rows()
        self.out["ring_rows"] = len(rows)
        self._g("H1", grade_h1(g(self.D, "H", "h1_record"), g(self.D, "H", "ring_start")),
                "a ring path unresolved at the start")
        self._g("RING", grade_ring(g(self.D, "R", "pages") or []), "a ring page unread or a ring error")
        self._g("Z", grade_z(self.out), "a mod error line in the server log, or admin parked in the debugger")
        getattr(self, "grade_" + self.key)(rows)
        self.out["verdict_summary"] = {k: v.get("verdict") for k, v in self.out["verdicts"].items()}

    def grade_x452(self, rows):
        self._g("HYDRATED", grade_hydrated(rows), "a ring row dehydrated or at 4 % deficit or more")
        rows, cut = hydrated_rows(rows)
        if cut:
            self.xs.note(f"grades: {cut} ring row(s) from the first dehydrated row on are excluded (review H2)")
        meals = g(self.D, "X", "meals") or []
        self._g("EAT0", grade_eat0(meals, rows), f"HUNGER over {EAT0_TOL} on a meal's landing row or the next two")
        plan = g(self.D, "X", "plan") or {}
        ends = [g(m2, "bol", "age0") for m2 in meals[1:]] + [plan.get("end")]
        last = rows[-1]["age"] if rows else None
        wins_p, wins_h, spans = [], [], []
        for i, m in enumerate(meals):
            i0 = counts_row(rows, m.get("eats_after")) if m.get("eats_after") is not None else None
            a0 = ring_age(rows[i0]) if i0 is not None else None
            a1 = ends[i] if i < len(ends) and ends[i] is not None else last
            if a1 is not None and last is not None:
                a1 = min(a1, last)
            if a0 is None or a1 is None:
                continue
            wins_p.append({"label": m.get("label"), "meal_age": a0, "ret": first_return(rows, a0, a1, HUNGRY_AT[0]),
                           "span": a1 - a0, "target": CAD_P_TARGETS.get(m.get("label"))})
            if m.get("label") == "dinner":
                wins_h.append({"label": "dinner", "meal_age": a0, "ret": first_return(rows, a0, a1, HUNGRY_AT[1]),
                               "span": a1 - a0, "target": CAD_H_TARGET})
            e = ring_wf_end(rows, a0, a1)
            spans.append(None if e is None else e - a0)
        meal_ages = [w["meal_age"] for w in wins_p]
        van = {}
        if meal_ages:
            r0 = [r for r in rows if ring_age(r) is not None and ring_age(r) <= meal_ages[0]]
            h0 = num(r0[-1].get("HUNGER")) if r0 else 0.2
            hours = (plan.get("end") or meal_ages[-1] + TAIL_H) - meal_ages[0] + 0.5
            try:
                van = {"day90": vanilla_meals(meal_ages, h0, 90.0, hours),
                       "profile": vanilla_meals(meal_ages, h0, DAY_MIN, hours)}
            except Exception as e:                                       # noqa: BLE001 - recorded, not a grade
                van = {"error": f"{type(e).__name__}: {e}"}
        self.D["vanilla_cadence"] = van
        v, obs = grade_return(wins_p, None, CAD_P_TOL)
        obs["vanilla"] = van
        self.xs.grade("CAD_FEEL_P", v, obs,
                      f"a meal's Peckish return off its HEAD-replay band by more than {CAD_P_TOL} h")
        v, obs = grade_return(wins_h, None, CAD_H_TOL)
        obs["vanilla"] = van
        self.xs.grade("CAD_FEEL_H", v, obs,
                      f"the dinner's Hungry return off its HEAD-replay band by more than {CAD_H_TOL} h")
        self._g("WF_SHOW", grade_wf_show(meals, self.pairs), f"no FOOD_EATEN within {WF_SHOW_GM} game minutes")
        lunch = meals[0] if meals else None
        self._g("WF_SPAN", grade_wf_span(lunch, self.pairs, rows, ends[0] if ends else None),
                "the server's Well Fed end off the ring's M fall")
        self.D["wf_vs_vanilla"] = wf_vs_vanilla(spans, van)
        self._g("PAIRS_foodEaten", grade_pairs(self.pairs, "foodEaten"), "a client FOOD_EATEN no server read had")
        self._g("PAIRS_hungry", grade_pairs(self.pairs, "hungry"), "a client HUNGRY no server read had")
        self.grade_replay(rows)

    def grade_replay(self, rows):
        xs = self.xs
        start_path = os.path.join(self.run_dir or "", "start.json")
        if not rows or not os.path.isfile(start_path):
            self.out["replay"] = {"error": "no ring rows or no start record"}
            for f in REPLAY_TOL:
                xs.grade(f"REPLAY_{f}", "unmeasured", {"why": "no replay"}, "")
            return
        with open(start_path, encoding="utf-8") as fh:
            start = json.load(fh)
        start_stats = g(self.D, "W", "start_stats") or {}
        drinks = [d for d in self.drinks if d.get("fill_ok")]
        if len(drinks) < len(self.drinks):
            xs.note(f"{len(self.drinks) - len(drinks)} drink(s) failed the fill gate and leave the replay")
        events, book = replay_events(rows, self.eats, num(g(self.D, "W", "start_age")), drinks)
        nut = g(self.D, "S", "nutrition") or {}
        sex = g(self.D, "H", "h1_record", "values", "body.sex")
        player = {"female": sex == 2, "weight": num(nut.get("weight")) or 80.0,
                  "macros": [num(nut.get(k)) or 0.0 for k in ("calories", "carbs", "lipids", "proteins")]}
        if self.run_dir:
            for name, obj in (("events.json", events), ("player.json", player)):
                with open(os.path.join(self.run_dir, name), "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(obj, fh, indent=1, sort_keys=True)
                xs.copied.append(name)
        self.out["model_inputs"] = {"tool": "tools/replay_live.py replay_live (ServerReplay) at HEAD",
                                    "ring": self.pages, "events": "events.json", "start": "start.json",
                                    "start_stats": start_stats, "player": player, "sleep_allowed": False,
                                    "tol": {k: list(v) for k, v in REPLAY_TOL.items()}, "bookkeeping": book}
        try:
            rep, d, be = replay_grade(rows, events, start, REPLAY_TOL, paths=list(RING[self.key]), player=player,
                                      start_stats=start_stats)
        except Exception as e:                     # noqa: BLE001 - recorded, graded unmeasured
            self.out["replay"] = {"error": f"{type(e).__name__}: {e}"}
            for f in REPLAY_TOL:
                xs.grade(f"REPLAY_{f}", "unmeasured", {"why": "the replay raised"}, "")
            return
        if self.run_dir:
            with open(os.path.join(self.run_dir, "replay.json"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"rows": rep, "diff": d, "events": events,
                                     "offset": getattr(getattr(be, "R", None), "offset", None)},
                                    indent=1, sort_keys=True, default=str) + "\n")
            xs.copied.append("replay.json")
        self.out["replay"] = {"rows": len(rep), "classes": d.get("classes"), "fields": d.get("fields"),
                              "findings_n": len(d.get("findings") or [])}
        for f in REPLAY_TOL:
            self._g(f"REPLAY_{f}", grade_replay_field(d, f), f"{f} off the HEAD replay by more than {REPLAY_TOL[f][1]}")

    def grade_x453(self, rows):
        X_ = self.D.get("X") or {}
        eats = X_.get("eats") or []
        reads = X_.get("reads") or []
        sev = num(g(self.D, "S", "sandbox", "SandboxVars.NR.Severity"))
        self._g("OF_REACH", grade_of_reach(eats), "Overfull 4 never reached by the broccoli eats")
        self._g("OF_REFUSE", grade_of_refuse(X_.get("refusal")),
                "the eat at Overfull 4 valid on the client, landed, or the stomach heavier")
        self._g("OF_EARLY", grade_of_early(eats), "an eat refused below Overfull 4")
        self._g("OF_TIMER", grade_of_timer(reads), "the food timer not above 3200 at Overfull 4, or above it below 4")
        self._g("OF_NAUSEA", grade_of_nausea(X_.get("trigger")), "FOOD_SICKNESS under 30 or no SICK at Overfull 4")
        self._g("OF_ENDURANCE", grade_of_endurance(reads, sev), "ENDURANCE over the cap at Overfull 3 or more")
        self._g("PAIRS_foodEaten", grade_pairs(self.pairs, "foodEaten"), "a client FOOD_EATEN no server read had")

    def starve_grades(self, rows):
        A = self.D.get("A") or {}
        set_age = num(A.get("set_age"))
        if set_age is None:
            for n in ("ONSET", "CONST"):
                self.xs.grade(n, "unmeasured", {"why": "no set"}, "")
            return None
        self._g("ONSET", grade_onset(rows, set_age), "the onset off 30 unfed hours, Starving absent, or the cap broken")
        a_on = onset_age(rows, set_age, "drain.starveAcute")
        a_off = num(g(self.D, "E", "eat", "landed_age"))
        self._g("CONST", grade_const(self.consts, a_on, a_off, self.red0),
                "the constant not 0 while starving, or not the start's value before")
        return a_on

    def grade_x454(self, rows):
        a_on = self.starve_grades(rows)
        self._g("STARVING_SHOWN", grade_shown(self.pairs, a_on, "hungry"), "HUNGRY not 4 after the onset")
        b_end = num(self.D.get("B_end_age"))
        bpts = [p for p in self.points if p.get("phase") == "B"]
        fl = floor_at(rows, b_end) if b_end is not None else None
        self._g("DRAIN_RATE", grade_drain_rate(bpts, fl if fl is not None else FIRST_FLOOR, HEALTH_SEED,
                                               STARVE_RATE, num(g(self.D, "B", "reached_age"))),
                f"the drain off {STARVE_RATE} a game day by more than {DRAIN_TOL_REL:.0%}")
        self._g("FLOOR_HOLD", grade_floor_hold(bpts, rows, FLOOR_TOL, b_end), "health off the floor during the hold")
        E = self.D.get("E") or {}
        la = num(g(E, "eat", "landed_age"))
        off = None
        if la is not None:
            for r in rows:
                if ring_age(r) is not None and ring_age(r) > la - 1.0 / 60.0 and r.get("drain.starveAcute") is False:
                    off = ring_age(r)
                    break
        rec = {"landed_age": la, "off_age": off, "const_after": const_of(E.get("const")), "red0": self.red0,
               "points": [p for p in self.points if p.get("phase") == "E"]}
        self._g("RECOVER", grade_recover(rec), "starvation still on, the constant not restored, or health not rising")
        self._g("PAIRS_hungry", grade_pairs(self.pairs, "hungry"), "a client HUNGRY no server read had")

    def grade_x455(self, rows):
        self.starve_grades(rows)
        W = self.D.get("windows") or {}
        self._g("N_BLEED", grade_n_bleed(W.get("N") or {}, self.red0), "the bleed's drain off wound + red x M_H")
        starve_gh = STARVE_RATE / 24.0
        ws, wn = W.get("SB") or {}, W.get("N") or {}
        rd = None if ws.get("r0") is None or ws.get("r1") is None else ws["r1"] - ws["r0"]
        self._g("S_BLEED", grade_s_bleed(ws, wn, self.red0, starve_gh, rd),
                "starving, the bleed's drain off N's, the constant not 0, or nothing re-applied")
        self._g("S_SICK", grade_sick(W.get("SS") or {}, self.red0, starve_gh),
                "starving, SICK 4's drain off red x M_H, or the constant not 0")

    def grade_x456(self, rows):
        A = self.D.get("A") or {}
        set_age = num(A.get("set_age"))
        if set_age is None:
            for n in ("DEHYD_ONSET", "CONST", "PARCHED_SHOWN"):
                self.xs.grade(n, "unmeasured", {"why": "no set"}, "")
            return
        self._g("DEHYD_ONSET", grade_dehyd_onset(rows, set_age), "the onset off 4 %, Parched absent, or the cap broken")
        a_on = onset_age(rows, set_age, "drain.dehydrated")
        self._g("PARCHED_SHOWN", grade_shown(self.pairs, a_on, "thirst"), "THIRST moodle not 4 after the onset")
        self._g("CONST", grade_const(self.consts, a_on, None, self.red0),
                "the constant not 0 while Parched, or not the start's value before")
        b_end = num(self.D.get("B_end_age"))
        bpts = [p for p in self.points if p.get("phase") in ("A", "B")]
        fl = floor_at(rows, b_end) if b_end is not None else None
        self._g("DEHYD_DRAIN", grade_drain_rate(bpts, fl if fl is not None else FIRST_FLOOR, 100.0, DEHYD_RATE,
                                                num(g(self.D, "B", "reached_age"))),
                f"the drain off {DEHYD_RATE} a game day by more than {DRAIN_TOL_REL:.0%}")
        self._g("DEHYD_FLOOR", grade_floor_hold(bpts, rows, DEHYD_FLOOR_TOL, b_end),
                "health off the floor during the hold")
        lm = num(g(self.D, "H", "h1_record", "values", "body.lm"))
        loss, cond = water_loss(rows, set_age + 2.0 / 60.0, b_end if b_end is not None else set_age)
        self._g("BASAL", grade_loss(loss, cond, lm, 1.0, BASAL_TOL_REL),
                f"the basal loss off 2000 + 32 (lm - 52.02) g a day by more than {BASAL_TOL_REL:.0%}")
        reached = num(g(self.D, "B", "reached_age"))
        drain_h = None if reached is None or a_on is None else reached - a_on
        h_on = num(A.get("health_at_onset"))
        pr = pct_rate(rows, set_age + 2.0 / 60.0, b_end if b_end is not None else set_age)
        p = dehyd_pace(num(A.get("w")), lm, pr, drain_h, floor_at(rows, reached) if reached is not None else None,
                       h_on if h_on is not None else 100.0)
        self.D["pace"] = p
        self._g("DEHYD_PACE", grade_pace(p), f"the live first-floor hour off the kernel's by more than {PACE_TOL_H} h")
        self.D["dehyd_spec"] = dehyd_spec(p)
        self._g("P_SICK", grade_sick((self.D.get("windows") or {}).get("P") or {}, self.red0, 0.0),
                "Parched, SICK 4's drain off red x M_H, or the constant not 0")
        self._g("PAIRS_thirst", grade_pairs(self.pairs, "thirst"), "a client THIRST level no server read had")

    def grade_x457(self, rows):
        arms = self.D.get("arms") or {}
        lm = num(g(self.D, "H", "h1_record", "values", "body.lm"))
        base = num(g(arms, "BASE", "scale"))
        for name, A in arms.items():
            loss, cond = water_loss(rows, num(A.get("start")) or 0.0, num(A.get("end")) or 0.0)
            A["loss"], A["clean"], A["cond"] = loss, cond.get("clean"), cond
            want = TRAIT_SCALE.get(name, 1.0) * (base if base is not None else 1.0)   # the arm's expected scale
            self._g(f"LOSS_{name}", grade_loss(loss, cond, lm, want, LOSS_TOL_REL),
                    f"the {name} loss off basalG x the arm's trait scale by more than {LOSS_TOL_REL:.0%}")
        sd = num(g(self.D, "S", "sandbox", "SandboxVars.StatsDecrease"))
        self._g("SCALE", grade_scale(arms, sd), "an applied scale off 1 / 1.5 / 1 / 0.5 x BASE's")
        for name in ("HIGH", "OFF", "LOW"):
            self._g(f"RATIO_{name}", grade_ratio(arms, name),
                    f"the {name} loss over BASE's off {TRAIT_SCALE[name]} by more than {RATIO_TOL[name]}")
        self._g("TRAITS", grade_traits(arms), "a thirst trait not held as the arm set it")


# ================================================================ the driver's main
def main(key, prefix, profile_name, artifact, session_text, pred, budget_s, driver_file):
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_server, teardown, verify   # noqa: E402

    pre, ok = preboot(key, profile_name, prefix, driver_file)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str))
        print("a pre-boot check failed; the session was not started")
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
    mg = out["manifest_gate"] = staged_gate()
    want = f'"value": "{mg.get("staged_version")}"'
    vrows = [v for v in prof.verify if v.get("args") == f"{NR}.version"]
    mg["verify_rows_match"] = bool(vrows) and all(str(v.get("expect")) == want for v in vrows)
    if not (mg["ok"] and mg["verify_rows_match"]):
        xs.refuse(f"the staged copy does not match the pinned commit or the verify rows: {mg!r}; not started")
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
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
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
            for c in every:
                lines, _ = X.grep_noecho(c.console, LOG_RX, 80, ECHO_RX, NEVER_RX)
                L.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        xs.finish(teardown, hard_kill, every, read_logs=read_logs, grade_all=S.grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, artifact)
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "abort": out.get("abort"),
                      "budget_stop": out.get("budget_stop"), "stop_reason": out.get("stop_reason"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "logs_error": out.get("logs_error"),
                      "run_id": run_id, "run_dir": run_dir, "memory": out.get("memory"),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])
    return out
