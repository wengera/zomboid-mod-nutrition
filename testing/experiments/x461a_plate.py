"""x461a-plate -- Plan 16 Task 9 (live): water beside a meal: a 667 kcal plate, then 500 mL of water at once (spec section 4.2), the ring's cold field fed to the replay (#3947).

One boot of profile x46-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan16-x46 of
mod/NutritionRevamp at x46_lib.STAGED_FROM, Nutrition false, DayLength 1, sleep off), build 42.21.0. The staged copy is
made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan16-x46`) and checked
against mod/ at that commit; the engine is testing/experiments/x46_lib.py (its docstring holds the phases, the reads
and the grades with every tolerance). This file names the session, the prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).
PRE-RUN EDIT: the driver review's fix round 1 (task-9-driver-review.md H1-H3, M1, M2, L1-L7) and fix round 2
(task-9-driver-rereview.md N1-N3) and N4 (task-9-driver-rereview2.md), before any boot.

THE SESSION: S (auto-drink off; restored at C from the flag read before), H (x46_lib.GUT_RING; the ring's cold field
rides every row), W (start.json), F (a can
of bolognese, a banana and two broccoli: 667.15 kcal), E (speed 5 until the first sight's seed plate has left the
stomach under 30 g), P (at speed 1 the four eaten one after another, then 0.5 L of Water from a WaterBottle at once,
0.75 game h watched at speed 1 with server-client pairs), T (1 game h at speed 5), C, R.

PREDICTIONS (testing/experiments/x46_prerun.json, the HEAD replay of exactly this schedule from the first sight):
  OF_MIN_3, OF_MIN_4  the game minutes at Overfull 3 or more and at 4 after the plate's first landing within 3 of the
                prerun's (of_m3 2.0, of_m4 0.0): bands, not reach tests (0 to 5 minutes at 3 or more passes; whether
                Overfull 3 was reached is the reading checks.overfull.reached_3); OF_PEAK the peak stomach mass within
                40 g of of_peak, the real check beside the REPLAY grades.
  REPLAY_*      the HEAD replay of the run's own ring (start.json, the eats, the sips as logged, the cold fed) within
                HUNGER 0.002, THIRST 0.002, body.energyState 0.005, stomachFill 0.002 and stomach.liquid 2.0 g.
  COLD_FED      the ring rows carry the cold field and the replay fed it (THIRST without it: checks.cold_ablation).
  H1, RING, Z   every ring path resolved, every page read with errors 0, no mod error line and admin not parked.

WALL: about 5 min (boot about 80 s, S/H/W up to 70 s, E about 35 s, P about 70 s, T 10 s, closing and teardown about
50 s); BUDGET_S 420 keeps the call under about 8 min.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x46_lib as L   # noqa: E402

KEY = "x461a"
PREFIX = "x461a"
PROFILE = "x46-mod"
ARTIFACT = "plate.json"
BUDGET_S = 420.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.PRERUN.get(KEY) or {}
SESSION = ("Plan 16 Task 9 x461a: a 667 kcal plate, then 0.5 L of water at once, after the seed plate empties; one boot of " + PROFILE)
PRED = {
    "OF_MIN_3": f"within {L.OF_TOL_MIN} game minutes of {P.get('of_m3')}: a band, not a reach test",
    "OF_MIN_4": f"within {L.OF_TOL_MIN} game minutes of {P.get('of_m4')}",
    "OF_PEAK": f"within {L.OF_PEAK_TOL_G} g of {P.get('of_peak')} g",
    "REPLAY_HUNGER": "within 0.002", "REPLAY_THIRST": "within 0.002 with the ring's cold fed",
    "REPLAY_body.energyState": "within 0.005", "REPLAY_stomachFill": "within 0.002",
    "REPLAY_stomach.liquid": "within 2.0 g", "COLD_FED": "the cold field on the ring rows and fed to the replay",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
