"""x443-tuna -- Plan 14 Task 5, session V2 (live): one food for 36 hours in the vanilla game (the guide's H2, S1a and
S3b; gap G3). One session (the ledger's ruling), not split.

One boot of profile x44-vanilla (fixture default, PZTestKit only, Nutrition true, DayLength 4, sleep off, admin -debug),
build 42.21.0. The engine is testing/experiments/x44_guide_lib.py (its docstring holds the clock, the eat, the model and
the grades); this file names the session, the run prefix, the profile, the artifact, the wall budget and the
predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION (the source map's V2, the review's I-9):
  S  the sandbox, the clock's trueMult, minute.ring admin start (no paths: HUNGER, BOREDOM and UNHAPPINESS every game
     minute), the model's start, seven Base.TunaTinOpen by RCON additem.
  X  at speed 1: nutrition.set admin calories 3000 and weight 80 (the values read first are kept), so the gain branch
     runs from hour 0 (above 1000 kcal at 80 kg, #0149); then at speed 30 to world age 36 (19:00 on day 2): a tin eaten
     whole at 08, 12, 16 and 20 on day 1 and 08, 12 and 16 on day 2 (the clock at speed 1 from 3 game minutes before
     each), the store every game hour (the Nutrition fields through stats.get, atomic with its age), stats.set
     admin thirst 0 every 6 game hours.
  C  the clock restored; R  the ring read and stopped.

PREDICTIONS (vanilla_model.simulate from the run's own start; the numbers below from the model's defaults, L.prerun):
  the weight gains about 1.41 kg over the 36 hours from the 3000-kcal store (1.3e-5 x min(1, cal / 4000) kg a
  game-second, #0152); the store ends near 3469 kcal; HUNGER follows VM1, VM3 and VM4 with each tin's -0.18; BOREDOM
  and UNHAPPINESS are readings only (the model has no mood).
  Grades: V2_hunger, V2_weight, V2_calories.

WALL: about 8.3 min (boot about 70 s, about 4.4 min of clock at speed 30, seven eats at speed 1 about 1.9 min,
teardown). BUDGET_S 555 ends the scenario cleanly if the boot runs long; the clock restore and the ring read still run.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x44_guide_lib as L   # noqa: E402

KEY = "V2"
PROFILE = "x44-vanilla"
PREFIX = "x443"
ARTIFACT = "tuna.json"
BUDGET_S = 555.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 14 Task 5 V2: four tins of tuna a day for 36 hours in the vanilla game from a 3000-kcal store; "
           "one boot of " + PROFILE)
PRED = {
    "prerun": L.prerun(KEY),
    "V2_hunger": "the ring's HUNGER within 0.003 of the model with the seven eats at their landing ages",
    "V2_weight": "every hourly weight within 0.02 kg of the model's gain",
    "V2_calories": "every hourly calorie store within 5 kcal + 1 % of the idle burn of the model",
}


if __name__ == "__main__":
    L.main(KEY, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
