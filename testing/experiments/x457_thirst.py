"""x457-thirst -- Plan 15 Task 11 (live): the thirst traits on the water base (Task 3): High Thirst on and off and Low
Thirst, read as the basal scale the server applies (NR.read.trait, NutritionRevamp.server.nutrients.fctx.basalScale) and
as the ring's water loss in four arms.

One boot of profile x45g-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan15-x45g of
mod/NutritionRevamp at a97fec05, Nutrition false, DayLength 1, sleep off), build 42.21.0, the staged copy checked as
x452's. The engine is testing/experiments/x45g_lib.py. Written BEFORE the boot and never edited after the run.

THE SESSION: S, H (the ring), then four arms at speed 5, each the trait change (trait.set on the server), 3 game minutes
to settle, the applied scale and stats.get's traits read, then 3 game hours of the ring's fluids.water: BASE (no
change), HIGH (HighThirst add), OFF (HighThirst remove), LOW (LowThirst add); K (both removed), C, R. A fresh record's
stomach is empty and the fixture's admin carries no fluid container, so the loss is the basal alone (the conditions
are read on the ring: both stomach lanes under 1 g, no sweat, no landing or sip; a cold diuresis the ring's
coldMult carries is added to the prediction).

PREDICTIONS (named before the run; K.fluids.basalG and thirstTrait at a97fec05; the fixture's StatsDecrease 3, a
multiplier of 1; the HEAD replay of the four arms, `python testing/experiments/x45g_prerun.py x457`, with the two thirst
traits added to its host's CharacterTrait: the applied scale 1, 1.5, 1 and 0.5, the losses 83.341, 124.992, 83.326 and
41.667 g a game hour, the ratios 1.4998, 0.9998 and 0.5000):
  SCALE        the applied scale reads 1.0, 1.5, 1.0 and 0.5 in BASE, HIGH, OFF and LOW (Task 3's NR.read.trait check).
  LOSS_<arm>   each arm's loss within 3 % of basalG(lm) x scale / 24: 83.3, 125.0, 83.3 and 41.7 g a game hour at lm
               52.02.
  RATIO_<arm>  HIGH, OFF and LOW over BASE within 0.05, 0.03 and 0.03 of 1.5, 1 and 0.5.
  TRAITS       stats.get lists High Thirst in HIGH only and Low Thirst in LOW only.
  H1, RING, Z  as x452.

WALL: about 3.5 min (boot about 55 s, S/H 8 s, four arms of 3.05 game h at speed 5 about 100 s, K/C/R 8 s, teardown
20 s); BUDGET_S 420.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x45g_lib as L   # noqa: E402

KEY = "x457"
PREFIX = "x457"
PROFILE = "x45g-mod"
ARTIFACT = "thirst.json"
BUDGET_S = 420.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 15 Task 11 x457: High Thirst on and off and Low Thirst, the applied basal scale and the ring's water "
           "loss in four arms; one boot of " + PROFILE)
PRED = {
    "SCALE": "1.0, 1.5, 1.0, 0.5",
    "LOSS_BASE": "83.3 g a game hour within 3 % (lm 52.02)", "LOSS_HIGH": "125.0 within 3 %",
    "LOSS_OFF": "83.3 within 3 %", "LOSS_LOW": "41.7 within 3 %",
    "RATIO_HIGH": "1.5 +/- 0.05", "RATIO_OFF": "1.0 +/- 0.03", "RATIO_LOW": "0.5 +/- 0.03",
    "TRAITS": "High Thirst in HIGH only, Low Thirst in LOW only",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
