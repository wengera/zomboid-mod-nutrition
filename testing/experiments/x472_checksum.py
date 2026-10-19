"""x472-checksum -- Plan 16 Task 12 (live), boot B: a one-byte Lua comment change on bob's client gets the checksum
kick, on the exact bytes Angus uploads.

One boot of profile x47-checksum (fixture two: admin -debug, role admin, which bypasses the gate (#3139); bob release,
role user; PZTestKit and the STAGED upload copy release/NutritionRevamp at x47_lib.STAGED_FROM on the server and admin,
Nutrition false, DayLength 1, sleep off), build 42.21.0. Before the boot x47_lib.make_bob_copy copies the staged folder to
release/x472-bob (gitignored) and changes ONE byte inside NR_Core.lua's first comment line ('its version' ->
'its versiom'); the profile's [client_overrides.bob] gives bob that copy. mod/ and release/NutritionRevamp are never
edited. The engine is testing/experiments/x47_lib.py. This file names the session, the budget and the predictions.
Written BEFORE the boot and never edited after the run (CLAUDE.md s5). `pzt run` is not used: the kick is expected and
the grade comes off the artifact (the raising-probe rule).

PREDICTIONS (x223a's reading on 42.20.4 and the frozen spike copy, expected again on 42.21.0 and the upload copy):
  COPY        (precondition) one file, one byte, inside a comment line; the CR-dropped MD5 differs.
  DEPLOYED    (precondition) server and admin carry the staged NR_Core.lua, bob the copy.
  KICK        bob never reaches ready; the user log's Anti-cheat="ChecksumUpdate" line for bob (reason "Lua incorrect
              checksum", action Kick), the stdout's `user bob will be kicked ... checksums do not match`, and bob's
              connections log's `force-disconnect` `checksum-File doesn't match the one on the server` naming
              media/lua/shared/nr_core.lua.
  ADMIN_STAYS admin answers TK.version at the end; players [admin].
  Z           no mod error line, admin not parked.

WALL: about 5 min (server about 30 s, admin about 40 s, bob watched OBS_S 180 s, teardown about 30 s); BUDGET_S 540.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x47_lib as L   # noqa: E402

KEY = "x472"
BUDGET_S = 540.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME == L.SESSIONS[KEY]["driver"], f"the driver file {_ME} is not the session's"
SESSION = ("Plan 16 Task 12 x472: bob's NR_Core.lua one byte off the staged copy inside a comment; the Lua checksum "
           "kick; one boot of " + L.SESSIONS[KEY]["profile"])
PRED = {
    "COPY": "one file, one byte, in a comment line, CR-dropped MD5 differing",
    "DEPLOYED": "server and admin staged, bob the copy",
    "KICK": "bob never ready; Anti-cheat ChecksumUpdate for bob, will be kicked, force-disconnect checksum",
    "ADMIN_STAYS": "admin answers at the end; players [admin]",
    "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, _ME, SESSION, PRED, BUDGET_S)
