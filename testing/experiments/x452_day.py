"""x452-day -- Plan 15 Task 11 (live): a three-meal day on the calibrated hunger writer (Task 6) and the food-timer
bridge's Well Fed (Task 8): the cadence and Well Fed against vanilla's, the eat's next write near 0, the client's
FOOD_EATEN and HUNGRY against the server's, and Task 9's hunger-line hide read (unmeasured by design).

One boot of profile x45g-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan15-x45g of
mod/NutritionRevamp at 718d4296, Nutrition false, DayLength 1, sleep off), build 42.21.0. The staged copy is made before
the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan15-x45g`); the driver checks its
MANIFEST against mod/ at the pinned commit and refuses on a mismatch (CLAUDE.md s5, x201). The engine is
testing/experiments/x45g_lib.py; this file names the session, the run prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run.

THE SESSION: S, H (the ring), W (the store's next save, the replay's start), F (3 CannedBologneseOpen and 4 Banana by
RCON; the T9 read before), X (lunch at the next 12:30, dinner 6 h later, breakfast 13 h after that, 5 h after it; each
meal a can and a banana, 645 kcal, eaten at speed 1 with no foodtimer.set; the lunch watched 0.65 game h at speed 1, the
others 0.1; speed 5 between; server-client stats.get pairs throughout), C, R, T (the T9 read after); x45g_lib's
docstring.

PREDICTIONS (named before the run; the offline numbers are the HEAD server replay of the same meals from a fresh record,
tools/replay_live.ServerReplay, and vanilla_model.simulate of the same cans):
  EAT0           HUNGER at most 0.02 on each meal's landing row and the next two (offline 0 after each meal).
  CAD_FEEL_P     each meal's Peckish return within 1.0 h of 3.8 h. Offline 2.97, 2.88 and 3.67 h, so the dinner's sits
                 0.08 h inside the band's edge: a falsified reading is possible and is written as such. Recorded
                 beside it, vanilla's returns for the same cans: 4.9, 5.2 and 4.9 h at the 90-minute day (the fit's
                 convention), 5.9 and 7.6 h at the profile's 15-minute day.
  CAD_FEEL_H     the dinner's Hungry return within 1.5 h of 8.0 h (offline 8.97 h; vanilla 8.82 h at the 90-minute day).
  REPLAY_*       the HEAD replay of the ring within x446's tolerances: HUNGER 0.002, body.energyState 0.005,
                 THIRST 0.002 on every graded row.
  WF_SHOW        FOOD_EATEN 1 or more within 3 game minutes of each landing.
  WF_SPAN        the lunch's Well Fed ends with the ring's satiety.M under 435, within 2 game minutes (offline 0.47 h).
  WF_VS_VANILLA  each meal's Well Fed span (offline 0.47 h) inside vanilla's for the same meal at the 15-minute day
                 (vanilla_model 1.17, 2.9 and 1.17 h).
  PAIRS_*        every client FOOD_EATEN and HUNGRY level a server level of the push window.
  H1, RING, Z    every ring path resolved, every page read with errors 0, no mod error line and admin not parked.

WALL: about 6.6 min (boot about 55 s, S/H 8 s, the save wait up to 70 s, X about 260 s for about 25 game hours,
C/R/T 10 s, teardown 20 s); BUDGET_S 480 keeps the call under 9.5 min (a foreground call, CLAUDE.md s5).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x45g_lib as L   # noqa: E402

KEY = "x452"
PREFIX = "x452"
PROFILE = "x45g-mod"
ARTIFACT = "day.json"
BUDGET_S = 480.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 15 Task 11 x452: a three-meal day (lunch, dinner, breakfast; a can of bolognese and a banana each) on "
           "the calibrated hunger writer and the Well Fed bridge; one boot of " + PROFILE)
PRED = {
    "EAT0": "HUNGER <= 0.02 on each meal's landing row and the next two",
    "CAD_FEEL_P": "each Peckish return within 1.0 h of 3.8 h (offline 2.97, 2.88, 3.67 h: the dinner's near the edge)",
    "CAD_FEEL_H": "the dinner's Hungry return within 1.5 h of 8.0 h (offline 8.97 h)",
    "REPLAY_HUNGER": "within 0.002 of the HEAD replay on every graded row",
    "REPLAY_body.energyState": "within 0.005 of the HEAD replay on every graded row",
    "REPLAY_THIRST": "within 0.002 of the HEAD replay on every graded row",
    "WF_SHOW": "FOOD_EATEN >= 1 within 3 game minutes of each landing",
    "WF_SPAN": "the lunch's Well Fed end at the ring's M < 435 within 2 game minutes (offline 0.47 h)",
    "WF_VS_VANILLA": "each Well Fed span inside vanilla's at the 15-minute day (1.17, 2.9, 1.17 h)",
    "PAIRS_foodEaten": "every client level a server level of the push window",
    "PAIRS_hungry": "every client level a server level of the push window",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
