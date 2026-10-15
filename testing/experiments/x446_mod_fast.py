"""x446-mod-fast -- Plan 14 Task 5, session M1 (live): the mod's hunger and thirst pipeline re-proved at HEAD after Plan
13's creation body and Plan 11g's satiety rework, and THIRST graded against a replay for the first time (gaps G7, G8).

One boot of profile x44-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan14-x44 of
mod/NutritionRevamp at HEAD, Nutrition false, DayLength 1, sleep off), build 42.21.0. The staged copy is made before the
boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan14-x44`); the driver checks its
MANIFEST against a clean mod/ at HEAD and refuses on a mismatch (CLAUDE.md s5, x201). The engine is
testing/experiments/x44_guide_lib.py; this file names the session, the run prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION (the source map's M1, the review's I-12):
  S  the sandbox, the mod's version and sleep option, the clock's trueMult, nutrition.get and stats.all.
  H  the record's ring paths resolved (lua.read record:admin) and minute.ring admin start with them (satiety, the
     stomach fill, the energy state, the body's lean and fat, the fluids with fluids.autoDrop, the intake and writer
     counters, the bus signature).
  W  the store's next save waited for: the saved line is start.json and the stats start-stats.json.
  X  a fresh record carrying no filled fluid container (as x364; autodrink.set is not used, #2941); one
     Base.CannedBologneseOpen by RCON; at speed 5 to the first request (HUNGER 0.25, speed 1 from 0.246), the can eaten
     (foodtimer 0 then eat.action, the existing modded drivers' route); then 24 game hours of fast at speed 5. Any
     auto-drink the writer folds is logged off the ring's fluids.autoDrop as `autodrop` events.
  C  the clock restored; R  the ring read and stopped; Z  the mod's error lines and the debugger park.

PREDICTIONS: the HEAD kernel replay (tools/replay_live.py replay_live, ServerReplay, sleep_allowed false) of the ring's
own clock from start.json, with the eat (the item pass's macros, the script's hunger) and the ring's autoDrop and
movement events, reproduces HUNGER within 0.002, body.energyState within 0.005 and THIRST within 0.002 (named before
the run) on every graded row. Grades: M1_replay_HUNGER, M1_replay_body.energyState, M1_replay_THIRST, H1, RING, Z.

WALL: about 7.5 min (boot about 80 s, the save wait up to 80 s, about 30 game hours at speed 5 about 4 min, teardown).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x44_guide_lib as L   # noqa: E402

KEY = "M1"
PROFILE = "x44-mod"
PREFIX = "x446"
ARTIFACT = "fast.json"
BUDGET_S = 540.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 14 Task 5 M1: one can of bolognese at the first request, then a 24-hour fast, on the staged copy at "
           "HEAD; one boot of " + PROFILE)
PRED = {
    "M1_replay_HUNGER": "within 0.002 of the HEAD replay on every graded row",
    "M1_replay_body.energyState": "within 0.005 of the HEAD replay on every graded row",
    "M1_replay_THIRST": "within 0.002 of the HEAD replay on every graded row",
    "H1": "every ring path resolved at the start", "RING": "every page read, errors 0",
    "Z": "no mod error line, admin not parked",
}


if __name__ == "__main__":
    L.main(KEY, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
