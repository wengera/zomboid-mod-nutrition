"""x434-growth -- Plan 13 Task 22 (live): the growth smoke against the model's own replay (ruling 8-R).

One boot of profile x43-growth (fixture default, admin -debug, NR.StrengthTimeScale 30, NR.StrengthIncidentalWeight
1), the STAGED release copy release/plan13-x43 (CLAUDE.md s5, x201), Nutrition false, DayLength 1, build 42.21.0. The
engine is testing/experiments/x43b_strength_lib.py (x43_strength_lib.py with two changes after x433; its docstring holds
the phases, the reads and the grades); this file names the task, the run prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

PREDICTIONS: each close's lm equals the kernel replay of the record's pre-close body under the close's own
recorded inputs to 1e-6 kg and its T to 1e-9; the native level follows floor(level(lm, N0, T) + 1e-9) and its band.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x43b_strength_lib as L   # noqa: E402

TASK = "22"
PROFILE = "x43-growth"
PREFIX = "x434"
ARTIFACT = "growth.json"
BUDGET_S = 900.0
USER = "admin"
CLI = "client"
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 13 Task 22: three days of growth against the replay; one boot of " + PROFILE)
PRED = {
    "22_close<k>": "lm to 1e-6 kg and T to 1e-9 of the replay",
    "22_level<k>": "native floor(level + 1e-9) and its band held",
}


if __name__ == "__main__":
    L.main(TASK, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME, user=USER, cli=CLI)
