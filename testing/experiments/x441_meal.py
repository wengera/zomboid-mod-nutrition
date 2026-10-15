"""x441-meal -- Plan 14 Task 5, session V1a (live): a measured meal in the vanilla game (the guide's H1 and S1c;
gap G1).

One boot of profile x44-vanilla (fixture default, PZTestKit only, Nutrition true, DayLength 4, sleep off, admin -debug),
build 42.21.0. The engine is testing/experiments/x44_guide_lib.py (its docstring holds the clock, the eat, the model and
the grades); this file names the session, the run prefix, the profile, the artifact, the wall budget and the
predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION (the source map's V1a, the review's I-3: the timer read by stats.get, no foodtimer.set):
  S  the sandbox (Nutrition, DayLength, StatsDecrease), the clock's trueMult (restored at C), minute.ring admin start
     (no paths: HUNGER and THIRST every game minute), the model's start (stats.get, health.get, stats.all), two
     Base.CannedBologneseOpen by RCON additem.
  A  at speed 1: stats.set admin hunger 0.25 thirst 0; eat one can whole (HUNGER to 0.01: not at its minimum, so no
     timer fill, #3597); stats.get's foodTimer read; then 6 game hours at speed 30, the store hourly.
  B  at speed 1: stats.set admin hunger 0.10; eat the second can (HUNGER to 0: the timer filled); for 25 game minutes
     at speed 1 every 10 s stats.get (foodTimer, standardFoodTime) beside moodle.level admin FOOD_EATEN; then 2 game
     hours at speed 30, the store hourly (the Nutrition fields through stats.get, atomic with its server age).
  C  the clock restored; R  the ring read and stopped.

PREDICTIONS (vanilla_model.simulate from the run's own start; the numbers below from the model's defaults, L.prerun):
  arm A's eat leaves HUNGER at about 0.012 and the timer unfilled, HUNGER rising at once (about 0.196 after 6 h);
  arm B's eat fills the timer 3120 units (0.24 x 13000), held at 0 HUNGER for about 17.3 game minutes (3 units a
  game-second at DayLength 4), the FOOD_EATEN moodle stepping down at 3200/1600/0; THIRST linear at 8e-6 a game-second;
  the calorie store falling 57.6 kcal a game hour at 80 kg plus each can's 540.
  Grades: V1a_A_hunger, V1a_A_timer, V1a_B_timer, V1a_B_moodle, V1a_B_freeze, V1a_B_hunger, V1a_thirst, V1a_calories.

WALL: about 5 min (boot about 70 s, arm A about 1 min, arm B about 2 min, teardown).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x44_guide_lib as L   # noqa: E402

KEY = "V1a"
PROFILE = "x44-vanilla"
PREFIX = "x441"
ARTIFACT = "meal.json"
BUDGET_S = 480.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 14 Task 5 V1a: a measured meal in the vanilla game (two cans of bolognese, the food-eaten timer); "
           "one boot of " + PROFILE)
PRED = {
    "prerun": L.prerun(KEY),
    "V1a_A_hunger": "the ring's HUNGER after arm A's eat within 0.003 of the model (no freeze)",
    "V1a_A_timer": "foodTimer after arm A's eat the model's (unfilled) within 100 units",
    "V1a_B_timer": "every arm-B timer read the model's 3120 fill less 3 a game-second within 100 units",
    "V1a_B_moodle": "every FOOD_EATEN level read the model's (thresholds 0, 1600, 3200, 4800)",
    "V1a_B_freeze": "HUNGER held at 0 and leaving it within 2 game minutes of the model's timer zero",
    "V1a_B_hunger": "the ring's HUNGER in arm B within 0.003 of the model",
    "V1a_thirst": "the ring's THIRST within 0.003 of the model",
    "V1a_calories": "every hourly calorie store within 5 kcal + 1 % of the idle burn of the model",
}


if __name__ == "__main__":
    L.main(KEY, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
