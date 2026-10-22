"""x501-prep -- Plan 19 Task 7, the first live session of the food hedonics: preparation quality (R2) at real ingredient
adds on the dedicated server (task-6-review's live items 1 to 4).

One boot of profile x50-hedonics (fixture default, admin -debug; PZTestKit and the STAGED upload copy release/
NutritionRevamp at x50_lib.STAGED_FROM 3760ae05; Nutrition false, DayLength 4, sleep off, NR.Mode 1, DeathPace 3,
HealthCombine 2), build 42.21.0, at speed 1 throughout. The engine is testing/experiments/x50_lib.py (its docstring holds
the schedule, the jar model and the grades). Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION: S, I (the ingredients spawned server-side), D3, D0, D10 (a Stir fry of Carrots, Cabbage, Onion, Salt and
Butter on a Pan at each Cooking level, every add vanilla's ISAddItemInRecipe from the client, each read as a
server-client-server pair), RN (D3 and D10 renamed as vanilla's dialog does, then Potato added to each at its level), RL
(admin relogs; every dish read again; Pepper added to D3 and D10), C (Cooking back to the level read at S).

PREDICTIONS (x50_prerun.json's x501): the anchor D3 reads -5, -10, -15, -17, -25 after its five adds, stamp 1; D0 reads
those x 0.8 (-4 ... -20) and D10 x 1.5 (-7.5 ... -37.5), stamped 0.8 and 1.5, on the server and the client alike; D10's
stamp survives its rename and its Potato add reads -45 (compounded it would read -63.75); every stamp and value holds
across the relog, and D10's Pepper add reads -48; cooks and prepped rise 19, unprepped 10, no failure.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
6. Takes no argument: a bare call boots the session.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x50_lib as L                                                           # noqa: E402

KEY = "x501"
PREFIX = "x501"
PROFILE = "x50-hedonics"
ARTIFACT = "prep.json"
BUDGET_S = L.SESSIONS[KEY]["budget_s"]
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert _ME == L.SESSIONS[KEY]["driver"], f"the driver file {_ME} is not the session's"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.load_prerun().get(KEY) or {}
SESSION = ("Plan 19 Task 7 x501: preparation quality (R2) at real ingredient adds at Cooking 3, 0 and 10, a rename and "
           "a relog of stamped dishes; one boot of " + PROFILE)
PRED = {
    "WRAP": "hedonics.wrappedCook true at S; every perk.set read back at its level",
    "ANCHOR": f"the Cooking-3 dish reads {(P.get('stored') or {}).get('3')} after its adds, stamp 1",
    "SCALE": f"Cooking 0 reads {(P.get('stored') or {}).get('0')}, stamp 0.8; Cooking 10 reads "
             f"{(P.get('stored') or {}).get('10')}, stamp 1.5 (the anchor's values x prepScale)",
    "CLIENT": "every valid pair's client field and stamp equal the server's",
    "COUNTS": f"the counters rise {P.get('counts')}",
    "RENAME": f"D10's stamp 1.5 after its rename; its Potato add reads {P.get('rename_d10_potato')} (compounded "
              f"{P.get('compounded_d10_potato')})",
    "RELOG": f"every dish's stamp and value as before the relog on both sides; D10's Pepper add reads "
             f"{P.get('relog_d10_pepper')}",
    "Z": "no mod error line, no hedonics failure counter rising, admin not parked",
}

if __name__ == "__main__":
    refusal = L.parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    L.main(KEY, _ME, SESSION, PRED, BUDGET_S)
