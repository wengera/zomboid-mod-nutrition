"""x442-starve -- Plan 14 Task 5, session V1b (live): starving to death in the vanilla game (the guide's S1b, S2a and
S2d; gap G2: a vanilla death by hunger was never measured, #0173, #0174).

One boot of profile x44-vanilla (fixture default, PZTestKit only, Nutrition true, DayLength 4, sleep off, admin -debug),
build 42.21.0. The engine is testing/experiments/x44_guide_lib.py (its docstring holds the clock, the model and the
grades); this file names the session, the run prefix, the profile, the artifact, the wall budget and the predictions.
Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION (the source map's V1b):
  S  the sandbox, the clock's trueMult, minute.ring admin start (no paths), the model's start.
  X  at speed 1: stats.set admin hunger 0.60 thirst 0; then at speed 30, no food: every game hour stats.set admin
     thirst 0 (the control: hunger and thirst are independent, #0500, #0501), the store (stats.get) and
     moodle.level admin HUNGRY; every quarter game hour health.get and witness.chain isDead; until admin reads dead
     or 40 game hours.
  C  the clock restored; R  the ring read and stopped. The server log is copied with the artifact (the death).

PREDICTIONS (vanilla_model.simulate from the run's own start; the numbers below from the model's defaults, L.prerun):
  HUNGER from 0.60 crosses 0.70 (HUNGRY 4) about 8.32 game hours later; health then falls 3.564 a game hour (VM10,
  DayLength 4; tier 3 regenerates nothing), reaching 0 about 36.4 game hours after the write; the calorie store falls
  57.6 kcal a game hour and the weight starts to fall once it is under 0 (VM8).
  Grades: V1b_hunger, V1b_level4, V1b_moodle, V1b_health, V1b_death, V1b_calories, V1b_weight.

WALL: about 6.5 min (boot about 70 s, 37 game hours at 8 game minutes a wall second about 4.6 min, teardown);
BUDGET_S 500 keeps the whole call under about 9 min.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x44_guide_lib as L   # noqa: E402

KEY = "V1b"
PROFILE = "x44-vanilla"
PREFIX = "x442"
ARTIFACT = "starve.json"
BUDGET_S = 500.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 14 Task 5 V1b: starving to death in the vanilla game from HUNGER 0.60, thirst held at 0 hourly; "
           "one boot of " + PROFILE)
PRED = {
    "prerun": L.prerun(KEY),
    "V1b_hunger": "the ring's HUNGER within 0.003 of the model until death",
    "V1b_level4": "HUNGER first above 0.70 within 0.1 game hour of the model's crossing",
    "V1b_moodle": "every hourly HUNGRY level the model's (0.15, 0.25, 0.45, 0.70)",
    "V1b_health": "every health read within 1.0 of the model's (3.564 a game hour at HUNGRY 4)",
    "V1b_death": "admin read dead within 0.5 game hour of the model's health zero",
    "V1b_calories": "every hourly calorie store within 5 kcal + 1 % of the idle burn of the model",
    "V1b_weight": "every hourly weight within 0.02 kg of the model",
}


if __name__ == "__main__":
    L.main(KEY, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
