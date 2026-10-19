"""x467-day -- Plan 16 Task 9 (live): a sleep-off three-meal day on the final curve (Task 4b), re-proving the guide's hunger lines H1, S1a, S2a, SH1 and SH3 (x452b's design).

One boot of profile x46-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan16-x46 of
mod/NutritionRevamp at x46_lib.STAGED_FROM, Nutrition false, DayLength 1, sleep off), build 42.21.0. The staged copy is
made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan16-x46`) and checked
against mod/ at that commit; the engine is testing/experiments/x46_lib.py (its docstring holds the phases, the reads
and the grades with every tolerance). This file names the session, the prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).
PRE-RUN EDIT: the driver review's fix round 1 (task-9-driver-review.md H1-H3, M1, M2, L1-L7), before any boot.

THE SESSION: x452's (x45g_lib's docstring): S, H (x452's ring plus acute.bodyOn and the writer's hunger factor), W,
F (3 CannedBologneseOpen and 4 Banana), X (lunch at the next 12:30, dinner 6 h later, breakfast 13 h after that, 5 h
after it; each a can and a banana at speed 1; 0.5 L of water 2.5 h after each meal from a fresh container type), C, R.

PREDICTIONS (x46_prerun.json's x467, the HEAD replay of exactly this schedule FROM THE FIRST SIGHT, its seed plate
included; x46_lib.install_bands puts them into x45g_lib's CAD bands in this process only):
  CAD_FEEL_P    each meal's Peckish return within 0.5 h of cad_p; CAD_FEEL_H the dinner's Hungry return within 0.75 h
                of cad_h.
  EAT0, HYDRATED, WF_SHOW, WF_SPAN, PAIRS_*, REPLAY_* (HUNGER 0.002, energyState 0.005, THIRST 0.002, the ring's cold
                fed)  as x452b's.
  NO_RHYTHM_DAY every ring row with the clock off and the hunger factor 1.
  H1, RING, Z   as x461a.

WALL: x452b's, about 7.5 min, at most about 9 min (BUDGET_S 500 plus the closing phases and teardown).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x46_lib as L   # noqa: E402

KEY = "x467"
PREFIX = "x467"
PROFILE = "x46-mod"
ARTIFACT = "day.json"
BUDGET_S = 500.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.PRERUN.get(KEY) or {}
SESSION = ("Plan 16 Task 9 x467: x452b's three-meal day on the final curve, sleep off; one boot of " + PROFILE)
PRED = {
    "CAD_FEEL_P": f"within 0.5 h of {(P.get('cad_p') or {})}", "CAD_FEEL_H": f"within 0.75 h of {P.get('cad_h')}",
    "EAT0": "HUNGER <= 0.02 on each landing row and the next two", "HYDRATED": "no row at 4 % deficit",
    "WF_SHOW": "FOOD_EATEN >= 1 within 3 game minutes", "WF_SPAN": "within 2 game minutes",
    "PAIRS_foodEaten": "every client level a server level (0.8 s)", "PAIRS_hungry": "as foodEaten",
    "REPLAY_HUNGER": "within 0.002", "REPLAY_body.energyState": "within 0.005",
    "REPLAY_THIRST": "within 0.002 with the ring's cold fed", "NO_RHYTHM_DAY": "the clock off, factor 1",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
