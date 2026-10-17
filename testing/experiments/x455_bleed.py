"""x455-bleed -- Plan 15 Task 11 (live): option B's re-applied drains (Task 5): while starving, with the severe-moodle
constant at 0, a four-part bleed and SICK 4 still drain health at vanilla's rates, re-applied by the writer.

One boot of profile x45g-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan15-x45g of
mod/NutritionRevamp at 718d4296, Nutrition false, DayLength 1, sleep off), build 42.21.0, the staged copy checked as
x452's. The engine is testing/experiments/x45g_lib.py. Written BEFORE the boot and never edited after the run.

THE SESSION: S, H (the ring), N (not starving, the constant 0.0165: four parts bleeding, bodypart.set bleedingTime 5 and
bleeding true on parts 0-3 as x451's C2; one 10 s window at speed 1, x451's window reads and the constant at both ends;
the bleed cleared), A (the onset as x454's), SB (the same bleed, starving), SS (FOOD_SICKNESS 95, SICK 4, starving),
K (the bleed and the sickness cleared), C, R.

PREDICTIONS (named before the run; red = 0.0165, M_H = 1800 at DayLength 1, x451's wound term 5.963 a game hour):
  ONSET, CONST  as x454 (no eat: the constant 0 on every read after the onset).
  N_BLEED       the bleed drains red x M_H + 5.963 = 35.66 a game hour within 25 %, BLEEDING 4 at both ends.
  S_BLEED       starving, the constant 0 at both ends, the same bleed drains N's rate plus the starvation drain (1.042)
                within 15 % of red x M_H (4.46 a game hour), and the writer's re-applied counter rose. N's rate
                carries vanilla's regeneration on the four bleeding parts, at most 0.002 x 1800 x 0.6 / 17 = 0.127 a
                game hour (review L1), recorded as bias_bound_per_gh.
  S_SICK        starving, SICK 4 drains red x M_H + 1.042 = 30.74 a game hour within 20 %, the constant 0 at both ends.
  H1, RING, Z   as x452.

WALL: about 3.5 min (boot about 55 s, S/H 8 s, N 15 s, A 25 s, SB 15 s, SS 15 s, K/C/R 8 s, teardown 20 s);
BUDGET_S 420.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x45g_lib as L   # noqa: E402

KEY = "x455"
PREFIX = "x455"
PROFILE = "x45g-mod"
ARTIFACT = "bleed.json"
BUDGET_S = 420.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 15 Task 11 x455: a four-part bleed before and after the acute starvation onset, and SICK 4 while "
           "starving: the drains option B re-applies; one boot of " + PROFILE)
PRED = {
    "ONSET": "first starveAcute row at 30 unfed h (+/- 0.05), HUNGER > 0.70 there or next, <= 0.69 before",
    "CONST": "0.0165 before the onset, 0 after it",
    "N_BLEED": "35.66 a game hour within 25 %",
    "S_BLEED": "N's rate + 1.042 within 4.46 a game hour, the constant 0, the re-applied counter rose",
    "S_SICK": "30.74 a game hour within 20 %, the constant 0",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
