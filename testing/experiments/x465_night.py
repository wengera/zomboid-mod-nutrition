"""x465-night -- Plan 16 Task 9 (live): a fast-forwarded night: every player asleep, the night booked with no loss to a stall (Task 2's carry, Task 4's latch).

One boot of profile x46-sleep (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan16-x46 of
mod/NutritionRevamp at x46_lib.STAGED_FROM, Nutrition false, DayLength 1, SleepAllowed and SleepNeeded true, FastForwardMultiplier at its default), build 42.21.0. The staged copy is
made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan16-x46`) and checked
against mod/ at that commit; the engine is testing/experiments/x46_lib.py (its docstring holds the phases, the reads
and the grades with every tolerance). This file names the session, the prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).
PRE-RUN EDIT: the driver review's fix round 1 (task-9-driver-review.md H1-H3, M1, M2, L1-L7), before any boot.

THE SESSION: S, H (x46_lib.NIGHT_RING), PRE (the server ini's FastForwardMultiplier read; 0.2 game h awake),
NIGHT (player.sleep.hold, acute.winSleptH polled to 7 h more (CLAUDE.md s5: never the unbroken run), the hold
cancelled and the flag cleared), POST (0.3 game h awake; the age and the record's lastSeen read), C, R. admin is the
only player, so every player sleeps. The night starts at the session's hour, not 23:00: the fast-forward keys on every
player asleep, not the hour.

PREDICTIONS (x46_prerun.json's x465: a synthetic night at x447's 3.2 game minutes a step with one 75-minute stall
books exactly its asleep hours and leaves no lag):
  FF_DEFAULT    FastForwardMultiplier 40.0, the default (precondition).
  NO_LOSS       winSleptH's gain within 0.05 h of the game hours of the steps the ring reads asleep.
  CAUGHT_UP     lastSeen within 2 game minutes of the world age after the night.
  H1, RING, Z   as x461a.
  Readings: the stall counters (players.stalls, substeps) over the night (a stall past 60 game minutes may not occur
  live; then the carry is not exercised and that is written so); the asleep share of the hold's span.

WALL: about 4.5 min (boot about 80 s, S/H/PRE about 30 s, NIGHT up to 150 s, about 20 s at the fast-forward's x447
rate, POST 12 s, closing and teardown about 50 s); BUDGET_S 400.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x46_lib as L   # noqa: E402

KEY = "x465"
PREFIX = "x465"
PROFILE = "x46-sleep"
ARTIFACT = "night.json"
BUDGET_S = 400.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.PRERUN.get(KEY) or {}
SESSION = ("Plan 16 Task 9 x465: a night with every player asleep under the game's own fast-forward; one boot of " + PROFILE)
PRED = {
    "FF_DEFAULT": "40.0", "NO_LOSS": f"within {L.NO_LOSS_TOL_H} h (prerun miss {P.get('miss_h')})",
    "CAUGHT_UP": f"within {L.CATCH_TOL_GM} game minutes",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
