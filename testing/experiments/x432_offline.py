"""x432-offline -- Plan 13 Task 20 (live): the offline gap (spec section 1, ruling 13-5): nothing moves while the player is offline.

One boot of profile x43-offline (fixture default, admin -debug), the STAGED release copy release/plan13-x43 (CLAUDE.md s5, x201), Nutrition
false, DayLength 1, build 42.21.0. The engine is testing/experiments/x43_strength_lib.py (its docstring holds the
phases, the reads and the grades); this file names the task, the run prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

PREDICTIONS: across a gap of at least 72 game hours dayIndex, sig7, p7, eb7, mass7, bandWeek, grace, Pk, lm,
fm and lx read unchanged, the vanilla Strength XP reads unchanged, and the next world-day boundary closes exactly one day.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x43_strength_lib as L   # noqa: E402

TASK = "20"
PROFILE = "x43-offline"
PREFIX = "x432"
ARTIFACT = "offline.json"
BUDGET_S = 720.0
USER = "admin"
CLI = "client"
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 13 Task 20: the offline gap; one boot of " + PROFILE)
PRED = {
    "20_gap": "every close-only field and ring equal across pre, away and first",
    "20_xp": "Strength XP and level equal before the quit and after the rejoin",
    "20_close": "dayIndex + 1 after the next boundary, one server close, each ring shifted once",
}


if __name__ == "__main__":
    L.main(TASK, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME, user=USER, cli=CLI)
