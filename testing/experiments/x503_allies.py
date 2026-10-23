"""x503-allies -- Plan 19 Task 7, the third live session of the food hedonics: alliesthesia (R3) at real eats on the
dedicated server, and the client's copy of a stale sad food after a Hungry eat (task-6-review's live items 5 and 6).

One boot of profile x50-hedonics (fixture default, admin -debug; PZTestKit and the STAGED upload copy release/
NutritionRevamp at x50_lib.STAGED_FROM 3760ae05; Nutrition false, DayLength 4, sleep off, NR.Mode 1, DeathPace 3,
HealthCombine 2), build 42.21.0, at speed 1 throughout. The engine is testing/experiments/x50_lib.py (its docstring holds
the schedule and the grades). Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION: S, H, I (butter, lard and a potato spawned server-side), R3S (three tenths of the butter, sated, with
UNHAPPINESS set to 60 first), I2C (the vanilla control: the potato aged stale, a quarter of it eaten sated with no
seed; the item read on both sides), R3H (the same butter eat Hungry: satiety.M 0 and HUNGER 0.32, held by the writer),
I2 (another quarter of the stale potato eaten Hungry; the item read on both sides), R3C (lard, Hungry, its eat cancelled
part way), C, R.

PREDICTIONS (x50_prerun.json's x503): the sated delta 6 (4.5 with a utensil), allies 1; the Hungry delta 3.6 (2.7),
allies 0.6; their per-unit ratio 0.6; every remainder's field the field before x the hunger left; the cancelled lard's
part scaled by 0.6; the stale potato's field 3.75 after the control and 2.5 after I2, its client field after I2
the server's 2.5 or its own before, never 12.5 (the read-time value an item-stats packet would write; I2 reads
unmeasured when the vanilla control's client field carries its read-time value too); the allies and restores counters
rise 3.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
6. Takes no argument: a bare call boots the session.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x50_lib as L                                                           # noqa: E402

KEY = "x503"
PREFIX = "x503"
PROFILE = "x50-hedonics"
ARTIFACT = "allies.json"
BUDGET_S = L.SESSIONS[KEY]["budget_s"]
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert _ME == L.SESSIONS[KEY]["driver"], f"the driver file {_ME} is not the session's"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.load_prerun().get(KEY) or {}
SESSION = ("Plan 19 Task 7 x503: alliesthesia at butter eaten sated and Hungry, a cancelled Hungry eat of lard, and a "
           "stale potato's client copy; one boot of " + PROFILE)
PRED = {
    "RING": "every page read, errors 0",
    "PRE": "HUNGER at or under 0.25 at the sated eat, over it at the three Hungry eats",
    "SATED": f"the delta one of {P.get('sated_delta')}, allies 1",
    "HUNGRY": f"the delta one of {P.get('hungry_delta')} (the sated arm's utensil factor), allies 0.6",
    "RATIO": "the Hungry over the sated delta per unit 0.6",
    "REMAINDER": "every remainder's field the field before x hung1 / hung0",
    "CANCEL": f"a part landed; its delta per unit one of {P.get('lard_per_frac')}, allies 0.6",
    "I2": f"the control I2C's client field not its read-time value (its server field "
          f"{P.get('potato_field_after_control')}); after I2 the client's field {P.get('potato_field_after')} or its "
          f"own before, never {P.get('potato_doubled_client')}",
    "COUNTS": f"{P.get('counts')}",
    "Z": "no mod error line, no hedonics failure counter rising, admin not parked",
}

if __name__ == "__main__":
    refusal = L.parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    L.main(KEY, _ME, SESSION, PRED, BUDGET_S)
