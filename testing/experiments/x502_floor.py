"""x502-floor -- Plan 19 Task 7, the second live session of the food hedonics: the plain-energy floor (R1) over repeated
plain eats, a relog with the clock running, and its release (task-6-review's live item 7), graded against the HEAD
replay of the run's own inputs (spec section B.5).

One boot of profile x50-hedonics (fixture default, admin -debug; PZTestKit and the STAGED upload copy release/
NutritionRevamp at x50_lib.STAGED_FROM 3760ae05; Nutrition false, DayLength 4, sleep off, NR.Mode 1, DeathPace 3,
HealthCombine 2), build 42.21.0, at speed 1 throughout. The engine is testing/experiments/x50_lib.py (its docstring holds
the schedule and the grades). Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION: S, H (the minute ring), W (the store's next save as the replay's start), I (a stick of butter and a jar of
peanut butter spawned server-side), E1-E4 (a tenth of the stick each, each landed, one writer minute, the ring record
read), OFF (admin relogs with the clock running), REL (half the peanut butter, not plain), C, R.

PREDICTIONS (x50_prerun.json's x502, the HEAD replay of this schedule from the first sight): hedonics.f 0, 0, 7.87,
21.86 after the four eats (the plain share 0.21, 0.42, 0.63, 0.84 over the 1500 kcal floor of the denominator); the
composed target moodLast.u 31.1 after the fourth; nothing in the ring moves across the relog but its hour stamp, which
moves by the absence; f 0 after the peanut butter (share 0.49), the target falling by f's fall (21.86).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
6. Takes no argument: a bare call boots the session.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x50_lib as L                                                           # noqa: E402

KEY = "x502"
PREFIX = "x502"
PROFILE = "x50-hedonics"
ARTIFACT = "floor.json"
BUDGET_S = L.SESSIONS[KEY]["budget_s"]
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert _ME == L.SESSIONS[KEY]["driver"], f"the driver file {_ME} is not the session's"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.load_prerun().get(KEY) or {}
SESSION = ("Plan 19 Task 7 x502: the plain-energy floor over four plain eats of butter, a relog, and its release; one "
           "boot of " + PROFILE)
PRED = {
    "H1": "every ring path resolved at the start but the hedonics, lastIntake and monotony paths (no eat yet)",
    "RING": "every page read, errors 0",
    "FLOOR_OF": "every ring read's f = floorOf(share) of its own slots",
    "RISE": f"f {[e.get('f') for e in P.get('eats') or []]} after the plain eats; the target at or over f",
    "LAST": "butter: plain, fatty, allies 1; peanut butter: not plain, fatty",
    "OFFLINE": f"slots, i, f and the target unchanged across the relog; s moved by the absence (the replay: "
               f"{(P.get('offline') or {}).get('s_moved_h')} h for {(P.get('minutes') or {}).get('off_m')} minutes)",
    "RELEASE": f"f 0 after the peanut butter; the target falls by f's fall ({(P.get('release') or {}).get('f_fall')})",
    "Z": "no mod error line, no hedonics failure counter rising, admin not parked",
}
for _f in L.REPLAY_TOL:
    PRED[f"REPLAY_{_f}"] = f"within {L.REPLAY_TOL[_f][1]} of the HEAD replay of the run's own inputs"

if __name__ == "__main__":
    refusal = L.parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    L.main(KEY, _ME, SESSION, PRED, BUDGET_S)
