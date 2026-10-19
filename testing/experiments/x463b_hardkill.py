"""x463b-hardkill -- Plan 16 Task 9 (live): the hard-kill arm: the store's record left ahead of a rolled-back world restores from the copy saved with the character (spec section 1.4, Task 3).

One boot of profile x46-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan16-x46 of
mod/NutritionRevamp at x46_lib.STAGED_FROM, Nutrition false, DayLength 1, sleep off), build 42.21.0. The staged copy is
made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan16-x46`) and checked
against mod/ at that commit; the engine is testing/experiments/x46_lib.py (its docstring holds the phases, the reads
and the grades with every tolerance). This file names the session, the prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).
PRE-RUN EDIT: the driver review's fix round 1 (task-9-driver-review.md H1-H3, M1, M2, L1-L7), before any boot.

THE SESSION: S, F (two Bananas), ADV (1 game h at speed 5; the store's lastWrite read), SAVE (a slot write after
ADV polled at speed 1 and the backup's writes read at 1 or more, so the character holds its copy (review H2); then
RCON save: the world and the players saved; else KILL and UP are skipped and the arm's grades read unmeasured), EAT
(one Banana; the store's after-eat write polled; the banana's monotony entry read; 2 game h at speed 5; the slot
FILE's next write polled and its latest stamp read off its text, lua.global ...store.file.last.admin (review H1): the
stamp the load rule compares with the world), KILL (the session's own server PID, the one its pzt Server object
started, read, recorded and persisted, then killed with taskkill /PID <it> /T /F, its return code and the process
alive before recorded; the exit awaited; the run folder's players.db read without a lock: the admin blob's length and
whether it holds the copy; the session's own client PID recorded and that client killed, a client of a dead server
(the controller's ruling; review L1, L2)), UP (the same Server object started again on the run folder, its log in
server-stdout-up.log; admin rejoins from a fresh client restore in <run>/c1b; in the poll iteration that first sees the
record: the record, the world age, the backup and store counters and the copy's age and part count (review L5); then
the banana count), C.
No other process is ever killed (amendments s1).

PREDICTIONS (Task 3's load rule, NR_Server_Store S.pick):
  KILL_OWN      the PID killed is the recorded one and its process exited.
  ROLLBACK      the world age after the restart, and the record's lastSeen at the sight, under the store FILE's
                latest stamp before the kill (precondition; the in-memory latest a reading).
  RESTORED      backup.stats.restored 1 and aheadKept 0. The likely copy is the world save's, so the restored record
                resumes FORWARD onto the clock (store.stats.resumes); a later 180 s snapshot's copy still ahead moves
                back (rewound): the direction is a reading.
  ON_CLOCK      the restored record's latest stamp within 2 game minutes of the world age at the sight.
  CONSISTENT    graded on RESTORED as predicted and a record read that answered: the restored record holds the
                banana's eat iff the inventory lost the banana (the likely case: no entry and both bananas back; an
                engine player save inside the eat-kill window gives the entry and one banana, consistent too).
  COPY_SAVED    the players.db admin blob holds the copy's key (the fixture's 4086-byte blob holds none).
  Z             no mod error line in either server log, admin not parked.

WALL (re-planned at the review's fix round, L2): expected about 6.5 min (boot about 80 s, S/F/ADV about 30 s, SAVE's
write wait about 30 s and the settle 8 s, EAT about 25 s and the file's next write about 45 s, KILL about 5 s with the
client killed, the restart about 70 s, the rejoin about 40 s, UP's reads about 10 s, closing and teardown about 30 s).
The worst case with every cap hit (SAVE's and the file's write waits at 70 s each, the eat's write wait at 70 s, a slow
restart and the relaunch's wait_ready at the profile's 180 s, which no budget guards) is about 13.5 min: OVER the
10-minute foreground cap; the controller rules on a detached launch before this session runs. BUDGET_S 480.

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
    "ROLLBACK": "the world after the restart and at the sight behind the store file's latest stamp",
    "RESTORED": "the copy restored once, no ahead store kept (the direction a reading)",
    "ON_CLOCK": "the restored record on the world clock within 2 game minutes",
    "CONSISTENT": "on a restore: the record's banana eat iff the banana left the inventory",
    "COPY_SAVED": "the players.db blob holds the copy",
    "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
