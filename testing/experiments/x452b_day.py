"""x452b-day -- Plan 15 Task 14b (live): x452's three-meal day re-run on the mod tree whose stomach slows the liquid lane
only by drink-borne kcal (8a34a7de) and whose hunger curve is re-fitted on it (390636fe, fit-hunger-curve-20261017c):
x452's HEAD replay misses its HUNGER by 0.021 since (the guide's VALIDATION x452:HUNGER), so the hunger lines it proved
(H1, S1a, S2a, SH1, SH3) wait on this run. The cadence against the HEAD replay of this schedule (vanilla's beside it),
Well Fed, the eat's next write near 0, the client's FOOD_EATEN and HUNGRY against the server's, the character kept
hydrated, and Task 9's hunger-line reads (the hide unmeasured by design), as x452.

One boot of profile x45g-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan15-x45g of
mod/NutritionRevamp, Nutrition false, DayLength 1, sleep off), build 42.21.0. The staged copy is re-made from 390636fe
before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan15-x45g`); the driver checks
its MANIFEST against mod/ at x45i_lib.STAGED_FROM_B and refuses on a mismatch (CLAUDE.md s5, x201). The engine is
testing/experiments/x45i_lib.py on the frozen testing/experiments/x45g_lib.py; this file names the session, the run
prefix, the profile, the artifact, the wall budget and the predictions. Written BEFORE the boot and never edited after
the run.

THE SESSION: x452's (x45g_lib's docstring): S, H (the ring), W (the store's next save, the replay's start), F (3
CannedBologneseOpen and 4 Banana by RCON; the T9 reads before), X (lunch at the next 12:30, dinner 6 h later, breakfast
13 h after that, 5 h after it; each meal a can and a banana, 645 kcal, eaten at speed 1 with no foodtimer.set; 0.5 L of
water 2.5 h after each meal through x44's drink route, a fresh prefilled container type each (WaterBottle, Canteen,
Sportsbottle), the server copy filled with Water, drink.action, the sips polled; the lunch watched 0.65 game h at speed
1, the others 0.1; speed 5 between; server-client stats.get pairs throughout), C, R, T (the T9 reads after).

PREDICTIONS (named before the run): the HEAD replay of exactly this schedule at 390636fe (`python
testing/experiments/x45g_prerun.py x452`: tools/replay_live.ServerReplay, a fresh record seen at age 3.0 with HUNGER
0.2, sleep off; the meals planned at minutes 330, 690 and 1470 from 07:00, the can landing 9 and the banana 16 game
minutes after each, each return measured from the banana's minute as the grade measures it, 0.5 L of Water 150 minutes
after the planned minute), in x45i_lib.CAD_P_TARGETS_B and CAD_H_TARGET_B (x452's on a97fec05 beside each):
  HYDRATED       every ring row under 4 % deficit, none dehydrated, the ring reaching the plan's end (replay: at most
                 1.452 %, THIRST at most 0.2667, the stomach at most 790 g, Overfull 1; the start's dehydPct recorded).
  EAT0           HUNGER at most 0.02 on each meal's landing row and the next two (replay 0 after each meal).
  CAD_FEEL_P     each meal's Peckish return within 0.5 h of its band: lunch 3.483 (x452 3.533), dinner 3.533 (3.583),
                 breakfast 4.083 h (4.033). Recorded beside it, vanilla_model's returns for the same cans (x452's
                 reading: 4.9, 5.2 and 4.9 h at the 90-minute day).
  CAD_FEEL_H     the dinner's Hungry return within 0.75 h of 9.550 h (x452 9.550; vanilla 8.82 h at the 90-minute day).
  REPLAY_*       the HEAD replay of the ring within x446's tolerances: HUNGER 0.002, body.energyState 0.005,
                 THIRST 0.002 on every graded row (x452 read THIRST falsified on cold diuresis and an auto-drink, F5;
                 that reading stands for x452 and is predicted again here as x452's grade names it).
  WF_SHOW        FOOD_EATEN 1 or more within 3 game minutes of each landing.
  WF_SPAN        the lunch's Well Fed ends with the ring's satiety.M under 435, within 2 game minutes (replay 0.367 h from
                 the banana's minute).
  PAIRS_*        every client FOOD_EATEN and HUNGRY level a server level of the push window, with a transition read.
  H1, RING, Z    every ring path resolved, every page read with errors 0, no mod error line and admin not parked.
  Readings, not grades: checks.wf_vs_vanilla, checks.T9 (the hide unmeasured; T.probe and optionOn read).

WALL: x452's (about 7.9 min, at most about 9.1 min: BUDGET_S 500 plus the closing phases, the grading and the
teardown), under the 10-minute cap of a foreground call (CLAUDE.md s5). No split.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x45i_lib as L   # noqa: E402

KEY = "x452b"
PREFIX = "x452b"
PROFILE = "x45g-mod"
ARTIFACT = "day.json"
BUDGET_S = 500.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 15 Task 14b x452b: x452's three-meal day (lunch, dinner, breakfast; a can of bolognese and a banana "
           "each, 0.5 L of water 2.5 h after each) on the liquid lane slowed only by drink-borne kcal and the hunger "
           "curve's re-fit; one boot of " + PROFILE)
PRED = {
    "HYDRATED": "every ring row under 4 % deficit, none dehydrated, to the plan's end (replay at most 1.452 %)",
    "EAT0": "HUNGER <= 0.02 on each meal's landing row and the next two",
    "CAD_FEEL_P": "each Peckish return within 0.5 h of its HEAD-replay band: lunch 3.483, dinner 3.533, breakfast 4.083 h",
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
