"""x483-options -- Plan 17 Task 7 (live): the two Plan 17 sandbox options, NR.DeathPace 2 and NR.HealthCombine 3 (both
off their declared defaults 3 and 2), set in the server's options file, read back on the server, admin and bob, on the
exact bytes Angus uploads; the boot doubles as the clean 1.0.0 join (x471's design, Plan 16 Task 12).

One boot of profile x48-options (fixture two: admin -debug, role admin; bob release, role user; PZTestKit and the STAGED
upload copy release/NutritionRevamp at x48b_lib.STAGED_FROM, Nutrition false, DayLength 1, sleep off), build 42.21.0.
The profile's [sandbox.NR] block is merged into Server/pzt_SandboxVars.lua at seed. The engine is
testing/experiments/x48b_lib.py (its docstring holds the reads and the grades). This file names the session, the budget
and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

PREDICTIONS:
  INI         the seeded file's NR block holds DeathPace = 2 and HealthCombine = 3 (precondition).
  OPT_SERVER  SandboxVars.NR.DeathPace 2 and SandboxVars.NR.HealthCombine 3 on the server, in both read sets.
  OPT_ADMIN   the same on admin's client (the client's copy from the server at the join).
  OPT_BOB     the same on bob's client.
  MOD_READ    on the server, NutritionRevamp.server.options.deathPace 2 and .healthCombine 3 (the options poll) and
              NutritionRevamp.kernel.drain.OPT.pace 2 and .combine 3 (the players' minute), in both read sets.
  JOIN        admin and bob ready, the staged version "1.0.0" on all three sides, players [admin, bob], the user log's
              `"bob" fully connected` and no Anti-cheat line, no checksum-mismatch line.
  Z           no mod error line, admin not parked.
  Readings: each client's NutritionRevamp.server.options.deathPace and .healthCombine (predicted the declared defaults
  3 and 2: the poll is gated on NR.isServer(), so a client's copy is never polled; never a grade); the server's
  K.drain.OPT.dayMin (15 at DayLength 1) and options.readAt.

WALL: about 3.5 min (x471 took 175 s: server about 30 s, admin about 40 s, bob about 40 s, the reads and the 20 s hold,
teardown about 30 s); BUDGET_S 540.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x48b_lib as L   # noqa: E402

KEY = "x483"
PREFIX = "x483"
PROFILE = "x48-options"
ARTIFACT = "options.json"
BUDGET_S = 540.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert _ME == L.SESSIONS[KEY]["driver"], f"the driver file {_ME} is not the session's"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
SESSION = ("Plan 17 Task 7 x483: NR.DeathPace 2 and NR.HealthCombine 3 set in the server's options file, read back on "
           "the server, admin and bob; the clean 1.0.0 join; one boot of " + PROFILE)
PRED = {
    "INI": "the seeded NR block holds DeathPace = 2 and HealthCombine = 3",
    "OPT_SERVER": "SandboxVars.NR.DeathPace 2 and HealthCombine 3 on the server", "OPT_ADMIN": "2 and 3 on admin",
    "OPT_BOB": "2 and 3 on bob",
    "MOD_READ": "server options.deathPace 2 and healthCombine 3, K.drain.OPT.pace 2 and combine 3",
    "JOIN": "both ready, 1.0.0 on three sides, players [admin, bob], bob fully connected, no Anti-cheat or mismatch line",
    "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, _ME, SESSION, PRED, BUDGET_S)
