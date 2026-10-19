"""x471-options -- Plan 16 Task 12 (live), boot A: an NR sandbox option set in the server's options file reads back on
the server, admin and bob, on the exact bytes Angus uploads; the boot doubles as the clean release join.

One boot of profile x47-options (fixture two: admin -debug, role admin; bob release, role user; PZTestKit and the STAGED
upload copy release/NutritionRevamp at x47_lib.STAGED_FROM, Nutrition false, DayLength 1, sleep off), build 42.21.0. The
profile's [sandbox.NR] VisibilityMode = 3 (the declared default 2) is merged into Server/pzt_SandboxVars.lua at seed. The
engine is testing/experiments/x47_lib.py (its docstring holds the reads and the grades). This file names the session, the
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

PREDICTIONS:
  INI         the seeded file's NR block holds VisibilityMode = 3 (precondition).
  OPT_SERVER  SandboxVars.NR.VisibilityMode reads 3 on the server, in both read sets.
  OPT_ADMIN   the same on admin's client (the client's copy from the server at the join).
  OPT_BOB     the same on bob's client.
  MOD_READ    NutritionRevamp.server.options.visibilityMode 3 on the server and NutritionRevamp.client.view.optionLevel 3
              on both clients (the mod's own reads, at OnServerStarted and at OnCreatePlayer).
  JOIN        admin and bob ready, the staged version "1.0.0" on all three sides, players [admin, bob], the user log's
              `"bob" fully connected` and no Anti-cheat line, no checksum-mismatch line.
  Z           no mod error line, admin not parked.
  Readings: each client's view.level and view.hasTrait; the server's options.readAt.

WALL: about 4 min (server about 30 s, admin about 40 s, bob about 40 s, the reads and the 20 s hold, teardown about 30 s);
BUDGET_S 540.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x47_lib as L   # noqa: E402

KEY = "x471"
BUDGET_S = 540.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME == L.SESSIONS[KEY]["driver"], f"the driver file {_ME} is not the session's"
SESSION = ("Plan 16 Task 12 x471: NR.VisibilityMode 3 set in the server's options file, read back on the server, admin "
           "and bob; the clean release join; one boot of " + L.SESSIONS[KEY]["profile"])
PRED = {
    "INI": "the seeded NR block holds VisibilityMode = 3",
    "OPT_SERVER": "SandboxVars.NR.VisibilityMode 3 on the server", "OPT_ADMIN": "3 on admin",
    "OPT_BOB": "3 on bob", "MOD_READ": "server options.visibilityMode 3, client view.optionLevel 3 on both",
    "JOIN": "both ready, 1.0.0 on three sides, players [admin, bob], bob fully connected, no Anti-cheat or mismatch line",
    "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, _ME, SESSION, PRED, BUDGET_S)
