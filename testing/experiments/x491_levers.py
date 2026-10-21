"""x491-levers -- Plan 18 Task 1, session 1 of 3 (live): added pain on one body part, on the 90-minute day.

One boot of profile x49-levers (fixture default, admin -debug; PZTestKit and the probe mod TKX_Symptoms by its path; no
NutritionRevamp; Nutrition false, DayLength 4, sleep on), build 42.21.0. The session engine, its schedule, tolerances,
grades and their falsifiers are testing/experiments/x49_lib.py's (its docstring, THE SESSIONS: x491); this file names
the session and boots it.

THE PHASES: S (the sandbox and clock read, speed 1, the probe watching admin, the log and ring reset, the baseline
parts and a pair), P1A (Torso_Lower held at added pain 20 for 140 s, a server and client pair every 2 s; the client's
unsynced BodyPart copy read), P1B (held at 40 for 90 s; one harness bodypart.set ... sync and the client's copy read
again), P2S (speed 5 for 25 s with the hold kept), REL (the hold released, 25 s of pairs), C (speed restored, the
minute log and the tick ring dumped, the part set back to 0).

THE GRADES: P0_BASE (precondition), P1_STEADY_A1, P1_STEADY_A2, P1_TARGET, P1_FOLLOWS, P1_RISE, P2_TICK, P2_GM,
P2_SPEED, REL_SNAP, Z (x49_lib's).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
6. Takes no argument: a bare call boots the session.

WALL: about 6.5 min (the boot about 80 s, the phases about 300 s); BUDGET_S 510 (x49_lib.SESSIONS).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x49_lib as L                                                           # noqa: E402

KEY = "x491"
PREFIX = "x491"
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["driver"] == _ME, f"x49_lib.SESSIONS names {L.SESSIONS[KEY]['driver']}, not {_ME}"

if __name__ == "__main__":
    refusal = L.parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    L.main(KEY, __file__)
