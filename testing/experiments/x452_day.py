"""x452-day -- Plan 15 Task 11 (live): a three-meal day on the calibrated hunger writer (Task 6) and the food-timer
bridge's Well Fed (Task 8): the cadence against the HEAD replay of this schedule (vanilla's beside it), Well Fed, the
eat's next write near 0, the client's FOOD_EATEN and HUNGRY against the server's, the character kept hydrated, and
Task 9's hunger-line reads (the hide unmeasured by design).

One boot of profile x45g-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan15-x45g of
mod/NutritionRevamp, Nutrition false, DayLength 1, sleep off), build 42.21.0. The staged copy is made before the boot
(`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan15-x45g`); the driver checks its MANIFEST
against mod/ at x45g_lib.STAGED_FROM and refuses on a mismatch (CLAUDE.md s5, x201). The engine is
testing/experiments/x45g_lib.py; this file names the session, the run prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run.

THE SESSION: S, H (the ring), W (the store's next save, the replay's start), F (3 CannedBologneseOpen and 4 Banana by
RCON; the T9 reads before), X (lunch at the next 12:30, dinner 6 h later, breakfast 13 h after that, 5 h after it;
each meal a can and a banana, 645 kcal, eaten at speed 1 with no foodtimer.set; 0.5 L of water 2.5 h after each meal
through x44's drink route, a fresh prefilled container type each (WaterBottle, Canteen, Sportsbottle), the server copy
filled with Water, drink.action, the sips polled; the lunch watched 0.65 game h at speed 1, the others 0.1; speed 5
between; server-client stats.get pairs throughout), C, R, T (the T9 reads after); x45g_lib's docstring.

PREDICTIONS (named before the run; review H1): the HEAD replay of exactly this schedule at a97fec05, Task 6c's re-fit
(`python testing/experiments/x45g_prerun.py x452`: tools/replay_live.ServerReplay, a fresh record seen at age 3.0 with
HUNGER 0.2, sleep off; the meals planned at minutes 330, 690 and 1470 from 07:00, the can landing 9 and the banana 16
game minutes after each (x45g_lib.EAT_CAN_GM, EAT_BAN_GM, read off x446's eat), each return measured from the banana's
minute as the grade measures it, 0.5 L of Water 150 minutes after the planned minute), in x45g_lib.CAD_P_TARGETS and
CAD_H_TARGET. Each meal's and drink's start offset from its planned minute is recorded (checks.X); the fast run takes no
pair in its last 0.35 game h, so the drop to speed 1 lands before the planned minute (re-review R1):
  HYDRATED       every ring row under 4 % deficit, none dehydrated, the ring reaching the plan's end (replay: at most
                 1.452 %, THIRST at most 0.267, the stomach at most 809 g, Overfull 1; the start's dehydPct recorded).
  EAT0           HUNGER at most 0.02 on each meal's landing row and the next two (replay 0 after each meal).
  CAD_FEEL_P     each meal's Peckish return within 0.5 h of its band: lunch 3.533, dinner 3.583, breakfast 4.033 h
                 (the dinner's depends on when the character last drank, review F8: the live drinks follow this
                 schedule). Recorded beside it,
                 vanilla_model's returns for the same cans: 4.9, 5.2 and 4.9 h at the 90-minute day; at the profile's
                 15-minute day dinner 7.6 h, lunch 5.87 h at a pre-lunch HUNGER of 0.3 (else past its window), and
                 breakfast past its tail (review L7).
  CAD_FEEL_H     the dinner's Hungry return within 0.75 h of 9.550 h (vanilla 8.82 h at the 90-minute day).
  REPLAY_*       the HEAD replay of the ring within x446's tolerances: HUNGER 0.002, body.energyState 0.005,
                 THIRST 0.002 on every graded row.
  WF_SHOW        FOOD_EATEN 1 or more within 3 game minutes of each landing.
  WF_SPAN        the lunch's Well Fed ends with the ring's satiety.M under 435, within 2 game minutes (replay 0.367 h from the
                 banana's minute).
  PAIRS_*        every client FOOD_EATEN and HUNGRY level a server level of the push window, with a transition read.
  H1, RING, Z    every ring path resolved, every page read with errors 0, no mod error line and admin not parked.
  Readings, not grades: checks.wf_vs_vanilla (review M2), checks.T9 (the hide unmeasured; T.probe and optionOn read).

WALL (review L6, re-planned with the drinks): boot about 55 s, S/H 8 s, the save wait up to 60 s, F 8 s, X about 300 s
(about 25 game hours at speed 5, three meals at about 15 s each plus the lunch's 24 s watch, three drinks at about 20 s
each), C/R/T 12 s, replay grading 10 s, teardown 20 s: about 7.9 min, at most about 9.1 min (BUDGET_S 500 plus the
closing phases, the grading and the teardown), under the 10-minute cap of a foreground call (CLAUDE.md s5). No split:
the day's record is one continuous state, and a reuse boot would add about 70 s.

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
BUDGET_S = 500.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 15 Task 11 x452: a three-meal day (lunch, dinner, breakfast; a can of bolognese and a banana each, "
           "0.5 L of water 2.5 h after each) on the calibrated hunger writer and the Well Fed bridge; one boot of "
           + PROFILE)
PRED = {
    "HYDRATED": "every ring row under 4 % deficit, none dehydrated, to the plan's end (replay at most 1.452 %)",
    "EAT0": "HUNGER <= 0.02 on each meal's landing row and the next two",
    "CAD_FEEL_P": "each Peckish return within 0.5 h of its HEAD-replay band: lunch 3.533, dinner 3.583, breakfast 4.033 h",
    "CAD_FEEL_H": "the dinner's Hungry return within 0.75 h of 9.550 h",
    "REPLAY_HUNGER": "within 0.002 of the HEAD replay on every graded row",
    "REPLAY_body.energyState": "within 0.005 of the HEAD replay on every graded row",
    "REPLAY_THIRST": "within 0.002 of the HEAD replay on every graded row",
    "WF_SHOW": "FOOD_EATEN >= 1 within 3 game minutes of each landing",
    "WF_SPAN": "the lunch's Well Fed end at the ring's M < 435 within 2 game minutes (replay 0.367 h)",
    "PAIRS_foodEaten": "every client level a server level of the push window, a transition read",
    "PAIRS_hungry": "every client level a server level of the push window, a transition read",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
