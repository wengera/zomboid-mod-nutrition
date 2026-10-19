"""x464-bodyclock -- Plan 16 Task 9 (live): the body clock: seeded at the world hour, kept through a nap, reset to 07:00 by a full sleep, stopped with sleep off and re-seeded with sleep on, the poll following an admin's change (spec section 2).

One boot of profile x46-sleep (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan16-x46 of
mod/NutritionRevamp at x46_lib.STAGED_FROM, Nutrition false, DayLength 1, SleepAllowed and SleepNeeded true), build 42.21.0. The staged copy is
made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan16-x46`) and checked
against mod/ at that commit; the engine is testing/experiments/x46_lib.py (its docstring holds the phases, the reads
and the grades with every tolerance). This file names the session, the prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).
PRE-RUN EDIT: the driver review's fix round 1 (task-9-driver-review.md H1-H3, M1, M2, L1-L7) and fix round 2
(task-9-driver-rereview.md N1-N3), before any boot.

THE SESSION: S, H (x46_lib.CLOCK_RING), TR (0.25 game h at speed 1), NAP (player.sleep.hold, acute.winSleptH
polled to 1.5 h more, the hold cancelled and the flag cleared, 0.3 game h awake so the bout closes), FULL (the same to
5 h), OFF (SleepAllowed read off the run's server ini; the world age read, THEN RCON changeoption SleepAllowed false;
the polled setting read every 0.25 s as a reading; 0.4 game h at speed 1), ON (changeoption SleepAllowed back to the
value read; 0.2 game h), C (the clock, and SleepAllowed restored if ON did not run (review L3)), R.

PREDICTIONS (x46_prerun.json's x464 replays the nap and the full sleep: the seed on the world hour, the nap's close
on it, the full sleep's close at 07:00 plus the gap, about 10.6 h off the world hour):
  TRACK         before the nap, bodyHour within 0.05 h of the world hour on every ring row.
  NAP_KEEP      the nap booked 1-4 h; after its close bodyHour still within 0.05 h of the world hour.
  FULL_RESET    the full sleep booked 4 h or more; after its close bodyHour within 0.1 h of 07:00 plus the game hours
                since the last asleep row, and more than 1 h off the world hour.
  POLL_OFF, POLL_ON  the first ring row after the change whose polled setting reads the new value falls within 2.5
                game minutes of an age read right after the RCON (re-review N1: the ring samples before the mod's poll,
                so two minute events; the gap from the age read before the RCON is a reading).
  NO_RHYTHM     from the first row after the flip, bodyOn false, the hunger factor 1, acute.circ 0, bodyHour held.
  RESEED        the first row with the clock back on reads bodyHour within 0.05 h of the world hour.
  H1, RING, Z   as x461a.

WALL: about 5 min (boot about 80 s, S/H/TR about 30 s, NAP about 25 s, FULL about 30 s, OFF and ON about 40 s,
closing and teardown about 50 s); BUDGET_S 420.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x46_lib as L   # noqa: E402

KEY = "x464"
PREFIX = "x464"
PROFILE = "x46-sleep"
ARTIFACT = "bodyclock.json"
BUDGET_S = 420.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.PRERUN.get(KEY) or {}
SESSION = ("Plan 16 Task 9 x464: a nap, a full sleep and the sleep setting toggled off and on; one boot of " + PROFILE)
PRED = {
    "TRACK": "bodyHour on the world hour before any sleep", "NAP_KEEP": "a nap leaves the clock on the world hour",
    "FULL_RESET": f"07:00 plus the time since waking within {L.RESET_TOL_H} h (prerun close {P.get('full_close_body')})",
    "POLL_OFF": f"within {L.POLL_GM} game minutes", "POLL_ON": f"within {L.POLL_GM} game minutes",
    "NO_RHYTHM": "bodyOn false, hunger factor 1, circ 0, phase held", "RESEED": "seeded on the world hour",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
