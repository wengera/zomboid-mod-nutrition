"""x443b-tuna -- Plan 14 Task 5, session V2 day 2 (live): one food for 36 hours in the vanilla game, its last 18 game
hours, on x443a's world (the controller's ruling on the review's concern 3: a reuse boot, no detached launch).

    python testing/experiments/x443b_tuna.py <x443a run id or run folder>

One boot of profile x44-vanilla (fixture default, PZTestKit only, Nutrition true, DayLength 4, sleep off, admin -debug),
build 42.21.0, on x443a's saved world: before the boot the lib's chain check reads x443a's run folder (its server cache,
its tuna-a.json artifact with an x443a run id, no error, abort or dead bus, and the anchor its phase X read) and refuses
otherwise; then <x443a run>/server is copied whole into this run and booted again (make_server reuse=True, x35's
route); the admin client is a fresh fixture restore. The engine is testing/experiments/x44_guide_lib.py; this file names
the session, the run prefix, the profile, the artifact, the wall budget and the predictions. Written BEFORE the boot and
never edited after the run (CLAUDE.md s5).

THE SESSION:
  S  as x443a (the model's own start read here, amendment 4), three Base.TunaTinOpen by RCON additem.
  X  no store write: at speed 30 to x443a's anchor plus 36 game hours: a tin eaten whole at the anchor plus 24, 28 and
     32 (one already past at the boot is eaten at once, named late), the store every game hour, stats.set admin thirst 0
     at the anchor plus 24 and 30.
  C  the clock restored; R  the ring read and stopped.

PREDICTIONS (vanilla_model.simulate from this run's own start): HUNGER, the weight and the store as x443a's grades;
L.prerun's weight_change_V2b is the model's share of the 36-hour gain in these 18 hours from the default start.
  Grades: V2b_hunger, V2b_weight, V2b_calories.

WALL: about 5.5 min (the copy under 1 s, boot about 80 s, 18 game hours at speed 30, three eats, teardown).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x44_guide_lib as L   # noqa: E402

KEY = "V2b"
PROFILE = "x44-vanilla"
PREFIX = "x443b"
ARTIFACT = "tuna-b.json"
BUDGET_S = 420.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 14 Task 5 V2, day 2: three tins of tuna in the last 18 game hours on x443a's world (a reuse boot); "
           "one boot of " + PROFILE)
PRED = {
    "prerun": L.prerun(KEY),
    "V2b_hunger": "the ring's HUNGER within 0.003 of the model with the tins at their landing ages",
    "V2b_weight": "every hourly weight within 0.02 kg of the model's gain",
    "V2b_calories": "every hourly calorie store within 5 kcal + 1 % of the idle burn of the model",
}


if __name__ == "__main__":
    L.main(KEY, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME,
           prev_run=sys.argv[1] if len(sys.argv) > 1 else None)
