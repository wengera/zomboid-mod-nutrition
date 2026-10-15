"""x444-strength -- Plan 14 Task 5, session V3 (live): Strength experience in the vanilla game (the guide's H3 and S4;
gap G4: the protein factors, #2112, and a live level crossing with its band trait, #2157, are code-only).

One boot of profile x44-vanilla (fixture default, PZTestKit only, Nutrition true, DayLength 4, sleep off, admin -debug),
build 42.21.0. The engine is testing/experiments/x44_guide_lib.py (its docstring holds the set, the model and the
grades); this file names the session, the run prefix, the profile, the artifact, the wall budget and the predictions.
Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION (the source map's V3, the review's I-1 and I-2), at speed 1 throughout:
  S  the sandbox (the experience multipliers), the clock's trueMult, minute.ring admin start (no paths), the model's
     start with perk.xp Strength, perk.xp Fitness.
  A  nutrition.set admin proteins 0 (the factor-1 control); stats.set admin endurance 1; perk.xp before; exercise.do
     pushups 60 (the set ends at exhaustion, x423; the server's exercise flag polled, action.cancel at a 200 s cap);
     perk.xp after.
  B  in this order: perk.park admin Strength 5 (37 500); nutrition.set admin proteins 0; xp.grant admin Strength 29700
     WHILE the store is 0 (xp.grant goes through addXp, so the factor would apply: 67 200, 300 under level 6's 67 500,
     #2102); nutrition.set admin proteins 100; endurance 1; the set; perk.xp after; stats.get's traitList.
  C  nutrition.set admin proteins -400; endurance 1; the set; perk.xp after.
  Z  the clock restored; R  the ring read and stopped.

PREDICTIONS (vanilla_model: the sets at their own ages, the writes and the grant through strength_xp_grant; the
numbers below from L.prerun): A +360 (factor 1); B's grant to 67 200, its set +540 (x1.5) crossing to level 6 with the
band trait Stout; C +252 (x0.7).
  Grades: V3_A, V3_B, V3_C (each within 2 reps x 6 x the factor), V3_B_grant (within 1 XP), V3_B_level.

WALL: about 6 min (boot about 70 s, three sets of about 80 s with their reads, teardown).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x44_guide_lib as L   # noqa: E402

KEY = "V3"
PROFILE = "x44-vanilla"
PREFIX = "x444"
ARTIFACT = "strength.json"
BUDGET_S = 480.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 14 Task 5 V3: three push-up sets at protein stores 0, 100 and -400 and a level crossing in the "
           "vanilla game; one boot of " + PROFILE)
PRED = {
    "prerun": L.prerun(KEY),
    "V3_A": "+360 within 12 XP (factor 1)",
    "V3_B_grant": "xpAfter 67200 within 1 XP (factor 1 at store 0)",
    "V3_B": "+540 within 18 XP (factor 1.5)",
    "V3_B_level": "level 6 and the band trait Stout alone",
    "V3_C": "+252 within 8.4 XP (factor 0.7)",
}


if __name__ == "__main__":
    L.main(KEY, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
