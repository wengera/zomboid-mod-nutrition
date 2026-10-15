"""x436-creation -- Plan 13 Task 22b (live): creation after Tasks 10b and 10c (lean-scaled fat starts, fat-only thin
picks with fmRef at the no-pick fat, the body-fat thin axis, the display names, the creation re-pin).

One boot of profile x43c-creation (fixture two, admin -debug then bob, the subject), the STAGED release copy
release/plan13-x43c (CLAUDE.md s5, x201), Nutrition false, DayLength 1, build 42.21.0. The engine is
testing/experiments/x43c_strength_lib.py (its docstring holds the phases, the reads and the grades); this file names
the task, the run prefix, the profile, the artifact, the wall budget and the predictions. Written BEFORE the boot and
never edited after the run (CLAUDE.md s5).

PREDICTIONS (male values, NR.SexSpecific off; unemployed, no boost): every case's body equals the staged kernel's
K.body.create and K.body.new to 1e-9 (lean, fat, weight, body-fat share, fmRef, fatDep); (a) none: 20 % fat, level 5,
no trait; (b) Strong + Obese: 36.8 %, level 9, STRONG and Obese; (c) Weak + Overweight: 29.4 %, level 1, WEAK and
Overweight; (d) Underweight: 10 %, fatDep 0.556, level 5, Underweight held, energy state about 1.49 (level 3); (e) Weak
+ Very Underweight, legal since Task 10c: 6.5 %, fatDep 0.722, level 1, WEAK and Very Underweight, state about 1.65
(level 4), and after its first close refeeding risk 2 and PE grade 4; (f) Feeble + Underweight: 10 %, level 3, FEEBLE
and Underweight; (g) Obese + Overweight + Thick Skinned, Keen Hearing, Fast Healer: Obese stripped (the costlier of the
exclusive pair), then the budget's costliest positive picks; after the first minute levelDue false and the XP at
pinXp(n, frac); the client's labels Overly Lean, Gaunt and Overfat.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x43c_strength_lib as L   # noqa: E402

TASK = "36"
PROFILE = "x43c-creation"
PREFIX = "x436"
ARTIFACT = "creation.json"
BUDGET_S = 900.0
USER = "bob"
CLI = "client:bob"
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 13 Task 22b: seven respawns of bob with armed picks after Tasks 10b and 10c, and case (e)'s first "
           "close; one boot of " + PROFILE)
PRED = {
    "36_<case>_body": "lm, fm, F0, Fc, Pk, N0, fmRef, the weight, the body-fat share and fatDep equal K.body.create",
    "36_<case>_traits": "the rungs and band of K.body.new; weight, level, band and weight trait on both sides",
    "36_<case>_xp": "levelDue false after the first minute, two level writes, XP at pinXp(n, frac)",
    "36_<case>_strips": {"a": [], "b": [], "c": [], "d": [], "e": [], "f": [], "g": "obese, then the budget's"},
    "36_<case>_hunger": "energyState K.deficit.state(0, fatDep) within 0.02, its ENERGY_AT rung",
    "36_names": {"underweight": "Overly Lean", "veryunderweight": "Gaunt", "overweight": "Overfat"},
    "36_e_refeed": "refeedRisk 2 and PE grade 4 after the first close",
}


if __name__ == "__main__":
    L.main(TASK, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME, user=USER, cli=CLI)
