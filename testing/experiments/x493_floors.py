"""x493-floors -- Plan 18 Task 1, session 3 of 3 (live): a deep ENDURANCE cap, and the UNHAPPINESS and STRESS floors,
on the 90-minute day.

One boot of profile x49-levers (fixture default, admin -debug; PZTestKit and the probe mod TKX_Symptoms by its path; no
NutritionRevamp; Nutrition false, DayLength 4, sleep on), build 42.21.0. The session engine, its schedule, tolerances,
grades and their falsifiers are testing/experiments/x49_lib.py's (its docstring, THE SESSIONS: x493); this file names
the session and boots it.

THE PHASES: S (as x491's), E (ENDURANCE capped at 0.748, 0.74, 0.49, 0.24 and 0.09 in turn: each armed, 4 s of settle,
both sides' level trackers reset, 26 s of pairs every 2 s, the trackers read; then released and ENDURANCE set back to
1), F (BOREDOM capped at 0 throughout; UNHAPPINESS floors 25 then 50, each as an E arm, released and set to 0; STRESS
floors 0.30 then 0.55, released and set to 0), C (speed restored, the minute log and the tick ring dumped).

THE GRADES: P0_BASE (precondition), P4_LEVEL_0.74, P4_LEVEL_0.49, P4_LEVEL_0.24, P4_LEVEL_0.09, P4_TIGHT, P4_CLIMB,
P5_U25, P5_U50, P5_S30, P5_S55, Z (x49_lib's).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
6. Takes no argument: a bare call boots the session.

WALL: about 6.5 min (the boot about 80 s, nine arms of about 33 s); BUDGET_S 510 (x49_lib.SESSIONS).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x49_lib as L                                                           # noqa: E402

KEY = "x493"
PREFIX = "x493"
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["driver"] == _ME, f"x49_lib.SESSIONS names {L.SESSIONS[KEY]['driver']}, not {_ME}"

if __name__ == "__main__":
    refusal = L.parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    L.main(KEY, __file__)
