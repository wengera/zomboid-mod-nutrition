"""x492-persist -- Plan 18 Task 1, session 2 of 3 (live): added pain's fall on a second day length, then whether it
survives a relog and a server restart.

One boot of profile x49-levers-d1 (fixture default, admin -debug; PZTestKit and the probe mod TKX_Symptoms by its path;
no NutritionRevamp; Nutrition false, DayLength 1, sleep on), build 42.21.0, with one client relaunch and one server
restart on the same run folder inside the session. The session engine, its schedule, tolerances, grades and their
falsifiers are testing/experiments/x49_lib.py's (its docstring, THE SESSIONS: x492); this file names the session and
boots it.

THE PHASES: S (as x491's), P2D (Torso_Lower held at 40 for 40 s on the 15-minute day, then released), RELOG (added pain
60 set once with no hold, read; admin quits; the players list polled until admin is gone; admin relaunched from a fresh
client restore in <run>/c1b; the server's bodypart.get polled until admin is back, the first read), RESTART (skipped
when under 230 s of the budget remain; added pain 60 set once, read; the minute log dumped; the server stopped
gracefully with admin connected, its quit saving the world and the players; admin's client killed; the server started
again on its run folder; admin relaunched in <run>/c1c; the first read), C.

THE GRADES: P0_BASE (precondition), P2_TICK_D1, P2_GM_D1, P3_RELOG, P3_RESTART, Z (x49_lib's).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
6. Takes no argument: a bare call boots the session. 7. Only this session's own server and client are stopped or
killed (a pre-existing ProjectZomboid64.exe is Angus's own client).

WALL: about 6 min (the boot about 80 s, the relog about 80 s, the restart about 130 s); BUDGET_S 510
(x49_lib.SESSIONS), so the closing phase, the teardown and a graceful stop still end under the 600 s foreground cap.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x49_lib as L                                                           # noqa: E402

KEY = "x492"
PREFIX = "x492"
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["driver"] == _ME, f"x49_lib.SESSIONS names {L.SESSIONS[KEY]['driver']}, not {_ME}"

if __name__ == "__main__":
    refusal = L.parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    L.main(KEY, __file__)
