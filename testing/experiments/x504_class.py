"""x504-class -- Plan 19 Task 7, the fourth live session of the food hedonics: a dish's taste class by type-summed kcal
(R4) and Rule 6, the frame timer under a 60-record load (task-6-review's live items 8 and 9).

One boot of profile x50-hedonics (fixture default, admin -debug; PZTestKit and the STAGED upload copy release/
NutritionRevamp at x50_lib.STAGED_FROM 3760ae05; Nutrition false, DayLength 4, sleep off, NR.Mode 1, DeathPace 3,
HealthCombine 2), build 42.21.0, at speed 1 throughout (37.5 server ticks a game minute, x391d's spacing). The engine is
testing/experiments/x50_lib.py (its docstring holds the schedule and the grades). Written BEFORE the boot and never
edited after the run (CLAUDE.md s5).

THE SESSION: S, H, I (two Pans, four Carrots, two BaconRashers spawned server-side), A (Cooking set to 10 first, restored at C from S's read; a Stir fry of three Carrots and
one BaconRashers, UNHAPPINESS set to 60, eaten whole), B (one Carrots and one BaconRashers, the same), IDLE (the frame
timer for 60 s, no load), LOAD (ghost.load 60 mod feed and ghost.modq on: 59 ghost records beside admin on the mod's own
queue; the same window), Z6 (no load left), C, R.

PREDICTIONS (x50_prerun.json's x504): A savoury (carrots 77.13 kcal against bacon 40.09; the heaviest single portion
would read fatty), B fatty; each dish eat lowers UNHAPPINESS by its stored, scaled value x 1 or 1.25 (a negative value
with a utensil, #0048), the dishes made at Cooking 10; the 60-record load adds at most 20 ms to the end-to-end p99 and 25 ms to the longest window over
the idle arm, starves no minute event, and fails no ghost run (Plan 10c ruling 2); x391d's mod draws at this
spacing added 7 to 10 ms at the p99 (#3744), a reading beside it.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
6. Takes no argument: a bare call boots the session.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x50_lib as L                                                           # noqa: E402

KEY = "x504"
PREFIX = "x504"
PROFILE = "x50-hedonics"
ARTIFACT = "class.json"
BUDGET_S = L.SESSIONS[KEY]["budget_s"]
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert _ME == L.SESSIONS[KEY]["driver"], f"the driver file {_ME} is not the session's"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.load_prerun().get(KEY) or {}
SESSION = ("Plan 19 Task 7 x504: the taste class of two Stir fries by type-summed kcal, and the frame timer under a "
           "60-record load; one boot of " + PROFILE)
PRED = {
    "RING": "every page read, errors 0",
    "CLASS_A": f"{(P.get('A') or {}).get('class')} (by type {(P.get('A') or {}).get('by_type')}); @savoury rises, "
               "@fatty does not",
    "CLASS_B": f"{(P.get('B') or {}).get('class')}; @fatty rises",
    "DISH_EAT": "each dish eat's UNHAPPINESS delta = u x f x k within 0.3, u the read-time getUnhappyChange "
                "(negative), k one of 1 and 1.25 for both dishes, at Cooking 10 (x50_prerun.json's x504 dish_eat): A u -7.5, "
                "delta -7.5 or -9.375; B u -15, delta -15 or -18.75; unscaled -5/-6.25 and -10/-12.5 falsify",
    "IDLE": f"idle busy p99 <= {L.IDLE_BUSY_P99_MAX} ms, period p50 in {list(L.IDLE_PERIOD_BAND)}",
    "F": f"each arm >= {L.MIN_FRAMES} kept frames and >= {L.MIN_MINUTE_FRAMES} minute frames",
    "SMOKE": f"ghost.load and ghost.modq on ok with {L.N_LOAD - L.REALS} ghosts, runs > 0",
    "P99": f"the end-to-end p99 adds <= {L.RULE_P99} ms over idle",
    "MAX": f"the longest window adds <= {L.RULE_MAX} ms over idle",
    "STARVE": "starvedEvents 0",
    "S": "ghost failures 0, storeGhostKeys 0, neverRun 0",
    "Z": "no mod error line, no hedonics failure counter rising, admin not parked",
}

if __name__ == "__main__":
    refusal = L.parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    L.main(KEY, _ME, SESSION, PRED, BUDGET_S)
