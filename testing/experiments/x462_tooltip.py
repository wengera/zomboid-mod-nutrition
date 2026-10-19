"""x462-tooltip -- Plan 16 Task 9 (live): the tooltip hide: the hunger line hidden with the option on and shown with it off (Task 8's tooltip.measure, measured without a hover).

One boot of profile x46-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan16-x46 of
mod/NutritionRevamp at x46_lib.STAGED_FROM, Nutrition false, DayLength 1, sleep off), build 42.21.0. The staged copy is
made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan16-x46`) and checked
against mod/ at that commit; the engine is testing/experiments/x46_lib.py (its docstring holds the phases, the reads
and the grades with every tolerance). This file names the session, the prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).
PRE-RUN EDIT: the driver review's fix round 1 (task-9-driver-review.md H1-H3, M1, M2, L1-L7) and fix round 2
(task-9-driver-rereview.md N1-N3), before any boot.

THE SESSION: S, F (a Banana: a fills-table food, Base.Banana 1.32 h at 105.11 kcal), TM (lua.call
NutritionRevamp.client.tooltip.optionOn before; tooltip.measure Base.Banana 1, then 0; optionOn after), C.

PREDICTIONS:
  T_ON          hideOn 1: ok, vanilla true (the banana's HungerChange is not 0), hungerLineDrawn false (the arm's
                height under the unwrapped baseline), tagLeft false.
  T_OFF         hideOn 0: ok, vanilla true, hungerLineDrawn true, tagLeft false.
  T_NATIVE      nativeTag false on the first call (no hide tag before any arm).
  T_RESTORED    both replies restored, optionOn reading the same before and after.
  Z             no mod error line, admin not parked.
  Readings: the heights (heightBase, heightOn, heightOff, lineDrop) and bandShown.

WALL: about 2.5 min (boot about 80 s, the phases about 20 s, teardown about 30 s); BUDGET_S 240.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x46_lib as L   # noqa: E402

KEY = "x462"
PREFIX = "x462"
PROFILE = "x46-mod"
ARTIFACT = "tooltip.json"
BUDGET_S = 240.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.PRERUN.get(KEY) or {}
SESSION = ("Plan 16 Task 9 x462: tooltip.measure on a Banana with the hide on and off; one boot of " + PROFILE)
PRED = {
    "T_ON": "hideOn 1: ok, vanilla true, hungerLineDrawn false, tagLeft false",
    "T_OFF": "hideOn 0: ok, vanilla true, hungerLineDrawn true, tagLeft false",
    "T_NATIVE": "nativeTag false on the first call", "T_RESTORED": "the option accessor restored",
    "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
