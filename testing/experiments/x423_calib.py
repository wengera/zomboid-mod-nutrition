"""x423-calib -- Plan 13 Task 1 (live): the XP-per-set calibration and check 7's remaining Strength sources.

One boot of profile x42-calib: fixture default (admin, the -debug client, the subject), PZTestKit and the probe mod
TKX_TraitLevers by its path (testing/experiments/TKX_TraitLevers/42.21: its server AddXP recorder), no NutritionRevamp
(no mod/ file is booted), Nutrition false, DayLength 1, build 42.21.0. The engine is testing/experiments/x42c_calib_lib.py
(frozen with this run); its docstring names the three windows, the XP-cap gate, the reply shapes it reads and the
grades. Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE ORDER: S (the setting: the players, the clock, admin's role, the sandbox multipliers, the probe's newGame count,
admin's Fitness and Strength), P (the push-up set to exhaustion: the calibration), W (loaded movement: check 7), M
(melee on an RCON-spawned zombie: check 7; last, because the zombie stays in the world).

NAMED BEFORE THE RUN (the amendments' x423 against the brief's x422, taken by Task 0's re-run):
  - the run is x423, the driver x423_calib.py, its lib x42c_calib_lib.py (from x42b_levers_lib.py, the latest);
  - the set is asked for PUSHUP_ASK_M game minutes so exhaustion, not the timer, ends it (one game minute is 0.625 s
    at DayLength 1; vanilla-strength-rate s4 predicts about 78 s to exhaustion);
  - the melee target is spawned by RCON createhorde (x141a's route): zombie.near spawned none on this fixture (#2916)
    and x422's addZombiesInOutfit beside bob returned an empty list; no harness command is added;
  - the loaded walk runs WALK_S of wall clock (4.8 game hours; the amendments ask at least 2), loaded to LOAD_SHARE of
    the max weight;
  - the tree hit and the weapon-hit count are not run (no harness command produces them).

PREDICTIONS (graded in `verdicts`: as_predicted / falsified / unmeasured):
  pushups  every Strength event of the set is 6 x the protein factor (1 at the neutral store), about 58 reps and
           about 346 XP over about 78 s (vanilla-strength-rate s4); the numbers are the reading, not the grade.
  7_walk   loaded walking fires at least one positive Strength event (about 0.1 XP a real second, s3c).
  7_melee  a melee hit fires at least one positive Strength event (#2880: OnWeaponHitXp on the server).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x42c_calib_lib as L   # noqa: E402

PROFILE = "x42-calib"
PREFIX = "x423"
ARTIFACT = "calib.json"
BUDGET_S = 1200.0
SESSION = ("Plan 13 Task 1: the XP of one vanilla push-up set to exhaustion (the mod's xpPerSet) and check 7's "
           "remaining Strength sources (loaded movement, melee); one boot of " + PROFILE + ", fixture default, admin "
           "the subject")
PRED = {
    "pushups": {"each Strength event": "6 x the protein factor (1 at the neutral store)",
                "reading": "about 58 reps, about 346 XP, about 78 s (vanilla-strength-rate s4)"},
    "7_walk": {"loaded movement": "at least one positive Strength AddXP event (about 0.1 XP a real second)"},
    "7_melee": {"melee hit": "at least one positive Strength AddXP event (#2880)"},
}


if __name__ == "__main__":
    L.main(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, "x423_calib.py")
