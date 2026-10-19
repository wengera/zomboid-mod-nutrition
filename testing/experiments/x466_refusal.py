"""x466-refusal -- Plan 16 Task 9 (live): the server refusal: a directly queued eat at Overfull 4 is refused, the item untouched, the record unchanged and the client queue cleared; a drink still lands (spec section 4.1, Task 6).

One boot of profile x46-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan16-x46 of
mod/NutritionRevamp at x46_lib.STAGED_FROM, Nutrition false, DayLength 1, sleep off), build 42.21.0. The staged copy is
made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan16-x46`) and checked
against mod/ at that commit; the engine is testing/experiments/x46_lib.py (its docstring holds the phases, the reads
and the grades with every tolerance). This file names the session, the prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).
PRE-RUN EDIT: the driver review's fix round 1 (task-9-driver-review.md H1-H3, M1, M2, L1-L7), before any boot.

THE SESSION: S, H (x453's ring), F (two Broccoli), SEED (true multiplier 0.05; record.set the stomach's calories to
2000 first, then its water to 1150 g, Overfull 4, re-set once under 1110 g; the server's food timer polled above 3200),
X (the stomach, the timer, the meal pool, the intake and guard counters, the Broccoli's server copy and count read;
action.cancel, the client queue read empty before the eat (review M2); eat.action Base.Broccoli on the client, its
spawned "found"; 8 wall s; the same reads again; action.cancel; then 0.2 L of Water from a
WaterBottle drunk), C (action.cancel, the clock restored), R.

PREDICTIONS (x46_prerun.json's x466: the seed reads Overfull 4 and holds it 14 game minutes, so the attempt, under a
game minute after the timer poll at 0.05, falls inside it):
  REACHED       Overfull 4 and the food timer above 3200 at the attempt (precondition).
  REFUSED       eatGuard.stats.refused and held up by 1, the intake's landed counter unchanged.
  (ITEM_INTACT, RECORD_KEPT and QUEUE_CLEARED are graded only when the guard's refused and held both rose by 1: the
                server saw the eat; else unmeasured, never a pass on a client-side refusal.)
  ITEM_INTACT   the Broccoli's id and hunger change unchanged and the count unchanged.
  RECORD_KEPT   the meal pool not raised, the stomach no heavier by 10 g, the eats count unchanged.
  QUEUE_CLEARED action.cancel finds the client queue empty.
  DRINK_LANDS   the water's sips rose and at least 0.15 L drunk.
  H1, RING, Z   as x461a.

WALL: about 4 min (boot about 80 s, S/H/F about 25 s, SEED up to 65 s, X about 35 s, closing and teardown about 50 s);
BUDGET_S 360.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x46_lib as L   # noqa: E402

KEY = "x466"
PREFIX = "x466"
PROFILE = "x46-mod"
ARTIFACT = "refusal.json"
BUDGET_S = 360.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.PRERUN.get(KEY) or {}
SESSION = ("Plan 16 Task 9 x466: a directly queued Broccoli at Overfull 4, then 0.2 L of water; one boot of " + PROFILE)
PRED = {
    "REACHED": "Overfull 4, the timer above 3200", "REFUSED": "refused +1, held +1, nothing landed",
    "ITEM_INTACT": "the same id, hunger change and count", "RECORD_KEPT": "M and the stomach unchanged by the eat",
    "QUEUE_CLEARED": "the client queue empty", "DRINK_LANDS": f"sips rose, at least {L.DRINK_MIN_L} L",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
