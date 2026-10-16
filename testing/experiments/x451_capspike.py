"""x451-capspike -- Plan 15 Task 2 (live): vanilla's shared severe-moodle constant
BodyDamage.healthReductionFromSevereBadMoodles set to 0 from server Lua, the drains it carries, and a reload.

One boot of profile x45-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan15-x451 of
mod/NutritionRevamp at af2a2d20, Nutrition false, DayLength 1, sleep off), build 42.21.0, then a reuse boot of the same
run folder for phase E. The staged copy is made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp
--out release/plan15-x451`); the driver checks its MANIFEST against mod/ at the pinned commit and refuses on a mismatch
(CLAUDE.md s5, x201). The engine is testing/experiments/x45_lib.py; this file names the session, the run prefix, the
profile, the artifact, the wall budget and the predictions. Written BEFORE the boot and never edited after the run.

THE SESSION: S, A, LW_A, B, LW_B, C1, C2, D, K on boot 1; E after the reuse boot (x45_lib's docstring).

PREDICTIONS (named before the run; red = 0.0165, M_H = 1800 at DayLength 1):
  ROUTE  witness.chain's setter call answers ok and the getter reads 0 (B), the value S read (D) and 0.0042 (K).
  A      HUNGER 0.80 and THIRST 0.90 drain health at red x 1800 x (1/50 + 1/10) = 3.564 a game hour, within 10 %.
  LW_A   five Nutrition.setWeight(30) calls cost 5 x red x mult beyond A's slope, within 0.5-1.5 of it.
  B      with the constant 0 at HUNGRY 4 and THIRST 4, health holds within 0.02 and no HUNGRY or THIRST tag fires.
  LW_B   the same five calls cost nothing (within 0.02).
  C1     with the constant 0 at SICK 4 (FOOD_SICKNESS 95), health holds within 0.02 and no SICK tag fires.
  C2     with the constant 0 and four parts bleeding (BLEEDING 4), health still falls (by 0.1 or more) through the
         per-part wound term, whose BLEEDING tag still fires; no SICK, HUNGRY or THIRST tag fires.
  D      with the constant restored, health falls faster than in C2 by red x 1800 x (1/50 + 1/10 + 1 + 1) = 62.96 a game
         hour (the active factors read at D's start), within 15 %, and the HUNGRY, THIRST and SICK tags fire again.
  E      after the reload the constant reads 0.0165, not K's 0.0042: it is not saved ([J1.5]).
  Z      no mod error line, admin not parked.

WALL: about 5.5 min (boot about 60 s, boot 1's phases about 2.5 min, the reuse boot about 70 s, teardown); BUDGET_S 470
keeps the whole call under 10 min (a foreground call, CLAUDE.md s5).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x45_lib as L   # noqa: E402

PROFILE = "x45-mod"
PREFIX = "x451"
ARTIFACT = "capspike.json"
BUDGET_S = 470.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 15 Task 2: the severe-moodle constant set to 0 from server Lua, the drains it carries (HUNGRY, "
           "THIRST, SICK, BLEEDING, LOWWEIGHT), restored, and read after a reuse boot; one boot of " + PROFILE +
           " and one reuse boot")
PRED = {
    "ROUTE_B_const": "setter ok, getter reads 0", "ROUTE_D_const": "setter ok, getter reads S's value",
    "ROUTE_K_const": "setter ok, getter reads 0.0042",
    "A": "3.564 a game hour within 10 %", "LW_A": "5 x red x mult within 0.5-1.5",
    "B": "health within 0.02, no HUNGRY or THIRST tag", "LW_B": "within 0.02",
    "C1": "health within 0.02, no SICK tag", "C2": "health falls >= 0.1, BLEEDING tag fires, no SICK/HUNGRY/THIRST tag",
    "D": "D minus C2 = 62.96 a game hour within 15 %, HUNGRY/THIRST/SICK tags fire",
    "E": "0.0165 after the reload, not 0.0042",
}

if __name__ == "__main__":
    L.main(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
