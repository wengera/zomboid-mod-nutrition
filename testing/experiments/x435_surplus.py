"""x435-surplus -- Plan 13 Task 22b (live): the surplus growth arm, x434's growth smoke with E placed through inDay.

One boot of profile x43c-surplus (fixture default, admin -debug, NR.StrengthTimeScale 30, NR.StrengthIncidentalWeight
1), the STAGED release copy release/plan13-x43c (CLAUDE.md s5, x201), Nutrition false, DayLength 1, build 42.21.0. The
engine is testing/experiments/x43c_strength_lib.py (its docstring holds the phases, the reads and the grades); this
file names the task, the run prefix, the profile, the artifact, the wall budget and the predictions. Written BEFORE
the boot and never edited after the run (CLAUDE.md s5).

PREDICTIONS: body.inDay set to eeDay + 260 at the last drain before each close lands E (eb7[7]) within 20 kcal of
+260; each close's lm equals the kernel replay of the record's pre-close body under the close's own recorded inputs to
1e-6 kg and its T to 1e-9, on the surplus arm (E >= 0, the growth law's grow > 0, the energy gate saturated); the native
level is K.strength.heldLevel(level(lm, N0, T), the pre-close wroteL) with its band; at least three such closes.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x43c_strength_lib as L   # noqa: E402

TASK = "35"
PROFILE = "x43c-surplus"
PREFIX = "x435"
ARTIFACT = "surplus.json"
BUDGET_S = 1200.0
USER = "admin"
CLI = "client"
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 13 Task 22b: four days of surplus growth against the replay, E placed through inDay; one boot of "
           + PROFILE)
PRED = {
    "35_E<k>": "E at the close within 20 kcal of +260",
    "35_close<k>": "lm to 1e-6 kg and T to 1e-9 of the replay, on the surplus arm with grow > 0",
    "35_level<k>": "native heldLevel(level, the pre-close wroteL) and its band held",
    "35_surplus": "at least three closes with 35_E and 35_close as predicted",
}


if __name__ == "__main__":
    L.main(TASK, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME, user=USER, cli=CLI)
