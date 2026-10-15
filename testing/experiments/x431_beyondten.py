"""x431-beyondten -- Plan 13 Task 19 (live): the level write with BeyondTen loaded (spec section 12.2; rulings 13-10, 13-42, 13-43).

One boot of profile x43-beyondten (fixture default, admin -debug, BeyondTen by workshop item 3765241705), the STAGED release copy release/plan13-x43 (CLAUDE.md s5, x201), Nutrition
false, DayLength 1, build 42.21.0. The engine is testing/experiments/x43_strength_lib.py (its docstring holds the
phases, the reads and the grades); this file names the task, the run prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

PREDICTIONS: the sentinel holds a wrapper; a shown 12.3 writes native 10, XP 337500 (BeyondTen's park) and
BeyondTen's stored XP masteryXp(12.3), the mirror body_level 12.3; a 1000-XP grant raises sigDay by 1000 x incidental
with the level at 10; a forced rust pass leaves 10; a shown 9.5 writes native 9, XP 412500, STRONG alone on both sides.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x43_strength_lib as L   # noqa: E402

TASK = "19"
PROFILE = "x43-beyondten"
PREFIX = "x431"
ARTIFACT = "beyondten.json"
BUDGET_S = 600.0
USER = "admin"
CLI = "client"
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 13 Task 19: the BeyondTen level write, grant, rust pass and leave; one boot of " + PROFILE)
PRED = {
    "19_sentinel": "NR_StrengthGuardInstalled a table with a wrapper function",
    "19_write12": {"level": 10, "xp": 337500, "stored": "masteryXp(12.3) over BeyondTen's own costs", "body_level": 12.3},
    "19_grant": {"d_sigDay": "1000 x incidental", "level": 10},
    "19_rust": {"level after a forced rust pass": 10, "outermost": "a reading only (ruling 13-43)"},
    "19_write95": {"level": 9, "xp": 412500, "bands": "STRONG alone, server and client"},
}


if __name__ == "__main__":
    L.main(TASK, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME, user=USER, cli=CLI)
