"""x433-creation -- Plan 13 Task 21 (live): the creation run (spec section 3.2; rulings 13-16 under Task 17's fix 3, 13-46).

One boot of profile x43-creation (fixture two, admin -debug then bob, the subject), the STAGED release copy release/plan13-x43 (CLAUDE.md s5, x201), Nutrition
false, DayLength 1, build 42.21.0. The engine is testing/experiments/x43_strength_lib.py (its docstring holds the
phases, the reads and the grades); this file names the task, the run prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

PREDICTIONS: (a) none: the none body, level 5, no band; (b) Strong + Overweight: Strong's body, level 9,
STRONG and OVERWEIGHT; (c) Strong + Very Underweight: thin lean, level 3 (3.83), FEEBLE and VERY_UNDERWEIGHT; (d) Feeble +
Obese + Overweight + the extras: Obese, Thick Skinned and Fast Healer stripped in that order, Feeble's body with
Overweight; (e) Weak + Underweight: Weak stripped, the none lean thinned, level 3 (3.75), FEEBLE and UNDERWEIGHT.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x43_strength_lib as L   # noqa: E402

TASK = "21"
PROFILE = "x43-creation"
PREFIX = "x433"
ARTIFACT = "creation.json"
BUDGET_S = 900.0
USER = "bob"
CLI = "client:bob"
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 13 Task 21: five respawns of bob with armed picks; one boot of " + PROFILE)
PRED = {
    "21_<case>_body": "lm, fm, F0, Fc, Pk, N0 equal the creation table to 1e-9",
    "21_<case>_state": "weights lm + lx + fm, levels floor(level + 1e-9), the band and weight trait on both sides",
    "21_<case>_strips": {"a": [], "b": [], "c": [], "d": ["obese", "thickskinned", "fasthealer"], "e": ["weak"]},
}


if __name__ == "__main__":
    L.main(TASK, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME, user=USER, cli=CLI)
