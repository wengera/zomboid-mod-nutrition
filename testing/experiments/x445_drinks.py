"""x445-drinks -- Plan 14 Task 5, session V4 (live): coffee and beer in the vanilla game (the guide's S6a and S6b;
gap G5: intoxication and coffee were read only at DayLength 1, #2950, #2951).

One boot of profile x44-vanilla-sleep (fixture default, PZTestKit only, Nutrition true, DayLength 4, SleepAllowed and
SleepNeeded true, admin -debug), build 42.21.0. The engine is testing/experiments/x44_guide_lib.py (its docstring holds
the drink, the model and the grades); this file names the session, the run prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION (the source map's V4, the review's M-8):
  S  the sandbox, the clock's trueMult, minute.ring admin start (no paths), the model's start; speed 1.
  A  stats.set admin fatigue 0.5 and FATIGUE read; RCON additem Base.WaterBottle; fluid.fill admin Base.WaterBottle
     Coffee 0.25 (the server copy, x151r's route); drink.action Base.WaterBottle 1; FATIGUE (stats.all) polled to the
     drop and its settle; then FATIGUE read for one game hour (every game minute for the first 5 at speed 1, then every
     5 at speed 30: a deviation from the map's speed 1 for the hour's tail, named, to save about 3.5 min of wall).
  B  at speed 1, four beers back to back, each in its own prefilled 0.3 L container TYPE (Base.BeerCan,
     Base.BeerBottle, Base.BeerImported, Base.Pop2: drink.action takes the client's first item of a type and an
     emptied can stays a BeerCan, so a second BeerCan would be the drunk one; a deviation from the map's four
     Base.BeerCan, named), each spawned by RCON, its server copy filled with 0.3 L Beer by fluid.fill and drunk
     whole by drink.action, INTOXICATION polled to its rise and settle; then polled every 2 s until 0 (cap one game
     hour).
  C  the clock restored; R  the ring read and stopped.

PREDICTIONS (vanilla_model.simulate from the run's own start with sleep_allowed true; the numbers below from L.prerun):
  the coffee lowers FATIGUE by 0.025 (-0.1 a litre, #2949) and the value holds through the hour; each can adds 6.0
  INTOXICATION (400 x 0.015, the hunger factor 1 below HUNGER 0.6, #2923), decaying 45.36 a game hour at DayLength 4
  (#2922), so the four reach 0 about 0.53 game hours after the first.
  Grades: V4_A_coffee, V4_A_holds, V4_B_decay, V4_B_zero.

WALL: about 5.5 min (boot about 70 s, the coffee and its hour about 1.3 min, four cans about 40 s, the decay about
2 min at speed 1, teardown).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x44_guide_lib as L   # noqa: E402

KEY = "V4"
PROFILE = "x44-vanilla-sleep"
PREFIX = "x445"
ARTIFACT = "drinks.json"
BUDGET_S = 480.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 14 Task 5 V4: a 0.25 L coffee at FATIGUE 0.5 and four cans of beer in the vanilla game with sleep on; "
           "one boot of " + PROFILE)
PRED = {
    "prerun": L.prerun(KEY),
    "V4_A_coffee": "FATIGUE down 0.025 across the drink within 0.005",
    "V4_A_holds": "no FATIGUE read under 0.1 in the hour after",
    "V4_B_decay": "INTOXICATION's slope after the last can within 5 % of the model's -45.36 a game hour",
    "V4_B_zero": "INTOXICATION first read 0 within 0.05 game hour of the model's zero",
}


if __name__ == "__main__":
    L.main(KEY, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
