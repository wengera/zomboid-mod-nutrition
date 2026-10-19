"""x463a-freeze -- Plan 16 Task 9 (live): the offline freeze: a logout of at least 3 game days, then a rejoin, every record value and written stat unchanged (spec section 1).

One boot of profile x46-sleep (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan16-x46 of
mod/NutritionRevamp at x46_lib.STAGED_FROM, Nutrition false, DayLength 1, sleep on (the body clock runs, so its freeze is read too)), build 42.21.0. The staged copy is
made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan16-x46`) and checked
against mod/ at that commit; the engine is testing/experiments/x46_lib.py (its docstring holds the phases, the reads
and the grades with every tolerance). This file names the session, the prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).
PRE-RUN EDIT: the driver review's fix round 1 (task-9-driver-review.md H1-H3, M1, M2, L1-L7) and fix round 2
(task-9-driver-rereview.md N1-N3), before any boot.

THE SESSION: S, H (x46_lib.FREEZE_PATHS: 8 stamps and 22 values), PRE (a can and 0.25 L of Coffee from a
WaterBottle, 0.3 game h at speed 1: a stomach, a meal pool and caffeine in flight), OFF (the record read; admin quits;
once the server lists nobody the record read away; the ring read and stopped; time.multiplier 30 until the world age is
72.5 game h past the record's lastSeen; the multiplier restored, read back; the record read again; the ring started
again; admin rejoins from a fresh client restore in <run>/c1b; lastSeen polled until the resume moved it; 0.1 game h at
speed 1), C, R.

PREDICTIONS (equalities, read off the kernel's resume: K.resume.resume moves the stamps alone, the return minute runs
nothing):
  AWAY_STILL    every FREEZE path equal between the away read and the read before the rejoin.
  FREEZE        on the first return ring row whose stamps moved, every value path equal to the away read (1e-9).
  STAMPS        on that row every stamp moved by the one gap (1e-6 h), and store.stats.resumedH grew by that gap.
  WRITTEN       that row's HUNGER, THIRST and FATIGUE equal one of the last two online rows before the quit (1e-6).
  H1, RING, Z   as x461a.

WALL: about 6 min (boot about 80 s, S/H/PRE about 45 s, the quit and departure about 10 s, the gap about 100 s, the
rejoin about 40 s, the return about 15 s, closing and teardown about 50 s); BUDGET_S 480. No split was needed: the
hard-kill arm is its own session, x463b.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x46_lib as L   # noqa: E402

KEY = "x463a"
PREFIX = "x463a"
PROFILE = "x46-sleep"
ARTIFACT = "freeze.json"
BUDGET_S = 480.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.PRERUN.get(KEY) or {}
SESSION = ("Plan 16 Task 9 x463a: a logout of 72 game hours or more and a rejoin, the record and the written stats unchanged; one boot of " + PROFILE)
PRED = {
    "AWAY_STILL": "every FREEZE path equal away and before the rejoin",
    "FREEZE": "every value path equal on the first resumed row, the gap at least 72 h",
    "STAMPS": "every stamp moved by the one gap, resumedH the gap",
    "WRITTEN": "HUNGER, THIRST and FATIGUE equal to the last online rows'",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
