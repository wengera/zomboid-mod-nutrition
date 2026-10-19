"""x461b-drinks -- Plan 16 Task 9 (live): x363's water, milk and solid on this build (restoring the guide's SE1 live lines), the ring's cold field fed to the replay (#3947).

One boot of profile x46-gut (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan16-x46 of
mod/NutritionRevamp at x46_lib.STAGED_FROM, Nutrition false, DayLength 1, sleep off, TKX_StudyFoods by its path), build 42.21.0. The staged copy is
made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan16-x46`) and checked
against mod/ at that commit; the engine is testing/experiments/x46_lib.py (its docstring holds the phases, the reads
and the grades with every tolerance). This file names the session, the prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).
PRE-RUN EDIT: the driver review's fix round 1 (task-9-driver-review.md H1-H3, M1, M2, L1-L7) and fix round 2
(task-9-driver-rereview.md N1-N3), before any boot.

THE SESSION: S (auto-drink off; restored at C from the flag read before), H (x46_lib.GUT_RING), W, F (TKX.MilkSolid), E (speed 5 until the seed plate has left
the stomach under 30 g), WA (0.5 L of Water from a WaterBottle at once at speed 1, 45 game minutes watched), MI (0.5 L
of CowMilk from a Base.Milk carton at once, 45 game minutes), SO (speed 5 until the server's HUNGER reaches 0.25, then
TKX.MilkSolid eaten at speed 1 and 45 game minutes watched), C, R.

PREDICTIONS (x46_prerun.json, the HEAD replay of this schedule from the first sight):
  W_PEAK, M_PEAK  the liquid lane's peak after each drink within 30 g of w_peak and m_peak.
  W_HALF        the water's liquid half-time within 3 game minutes of w_half_m.
  REPLAY_*      as x461a (x363's admission tolerances for the fills: stomachFill 0.002, stomach.liquid 2.0 g).
  COLD_FED, H1, RING, Z as x461a.

WALL: about 6.5 min (boot about 80 s, S/H/W up to 70 s, E about 35 s, WA and MI about 40 s each, SO up to 90 s to
the request and about 40 s after, closing and teardown about 50 s); BUDGET_S 480 keeps the call under about 9 min.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x46_lib as L   # noqa: E402

KEY = "x461b"
PREFIX = "x461b"
PROFILE = "x46-gut"
ARTIFACT = "drinks.json"
BUDGET_S = 480.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.PRERUN.get(KEY) or {}
SESSION = ("Plan 16 Task 9 x461b: 0.5 L of water, 0.5 L of CowMilk and TKX.MilkSolid at the next request, after the seed plate empties; one boot of " + PROFILE)
PRED = {
    "W_PEAK": f"within {L.LIQ_PEAK_TOL_G} g of {P.get('w_peak')} g",
    "W_HALF": f"within {L.LIQ_HALF_TOL_M} game minutes of {P.get('w_half_m')}",
    "M_PEAK": f"within {L.LIQ_PEAK_TOL_G} g of {P.get('m_peak')} g",
    "REPLAY_HUNGER": "within 0.002", "REPLAY_THIRST": "within 0.002 with the ring's cold fed",
    "REPLAY_body.energyState": "within 0.005", "REPLAY_stomachFill": "within 0.002",
    "REPLAY_stomach.liquid": "within 2.0 g", "COLD_FED": "the cold field on the ring rows and fed to the replay",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
