"""x463b-hardkill -- Plan 16 Task 9 (live): the hard-kill arm: the store's record left ahead of a rolled-back world restores from the copy saved with the character (spec section 1.4, Task 3).

One boot of profile x46-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan16-x46 of
mod/NutritionRevamp at x46_lib.STAGED_FROM, Nutrition false, DayLength 1, sleep off), build 42.21.0. The staged copy is
made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan16-x46`) and checked
against mod/ at that commit; the engine is testing/experiments/x46_lib.py (its docstring holds the phases, the reads
and the grades with every tolerance). This file names the session, the prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION: S, F (two Bananas), ADV (1 game h at speed 5), SAVE (RCON save: the world and the players saved;
the age, the store's stamps and the backup counters read), EAT (one Banana; the store's after-eat save polled; the
banana's monotony entry read; 2 game h at speed 5, so the store's stamps run past the save by more than the
restart-to-sight span; the store's latest stamp read), KILL (the session's own server PID, the one its pzt Server
object started, read and recorded, then killed with taskkill /PID <it> /T /F; the exit awaited; the run folder's
players.db read without a lock: the admin blob's length and whether it holds the copy; the client quit through its
bus), UP (the same Server object started again on the run folder, its log in server-stdout-up.log; admin rejoins from
a fresh client restore in <run>/c1b; the record polled in memory; the world age, the backup and store counters, the
banana's monotony entry, the banana count and the copy's age and part count read), C.
No other process is ever killed (amendments s1).

PREDICTIONS (Task 3's load rule, NR_Server_Store S.pick):
  KILL_OWN      the PID killed is the recorded one and its process exited.
  ROLLBACK      the world age after the restart, and the record's lastSeen at the sight, under the store's latest
                stamp before the kill (precondition).
  RESTORED      backup.stats.restored 1 and store.stats.rewound 1 or more.
  CONSISTENT    the restored record holds the banana's eat iff the inventory lost the banana (the likely case: the
                copy is the save's, so no entry and both bananas back; an engine player save inside the eat-kill
                window gives the entry and one banana, consistent too).
  COPY_SAVED    the players.db admin blob holds the copy's key (the fixture's 4086-byte blob holds none).
  Z             no mod error line in either server log, admin not parked.

WALL: about 6 min (boot about 80 s, S/F/ADV about 25 s, SAVE 10 s, EAT up to 45 s, KILL about 15 s, the restart about
70 s, the rejoin about 40 s, UP's reads 10 s, closing and teardown about 40 s); BUDGET_S 480.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x46_lib as L   # noqa: E402

KEY = "x463b"
PREFIX = "x463b"
PROFILE = "x46-mod"
ARTIFACT = "hardkill.json"
BUDGET_S = 480.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.PRERUN.get(KEY) or {}
SESSION = ("Plan 16 Task 9 x463b: a world save, an eat, a kill of the session's own server and a restart: the copy on the character; one boot of " + PROFILE)
PRED = {
    "KILL_OWN": "the recorded server PID killed and exited",
    "ROLLBACK": "the world after the restart behind the store's latest stamp",
    "RESTORED": "the copy restored once, the record moved back",
    "CONSISTENT": "the record's banana eat iff the banana left the inventory",
    "COPY_SAVED": "the players.db blob holds the copy",
    "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
