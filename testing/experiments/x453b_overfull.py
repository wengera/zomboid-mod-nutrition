"""x453b-overfull -- Plan 15 Task 11 (live review F6): Overfull 4, its refused eat, its refusal timer and its nausea,
re-measured after x453 (frozen) stopped at Overfull 3.

One boot of profile x45g-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan15-x45g of
mod/NutritionRevamp at a97fec05, Nutrition false, DayLength 1, sleep off), build 42.21.0, the staged copy checked as
x452's. The engine is testing/experiments/x45h_lib.py on the frozen testing/experiments/x45g_lib.py. Written BEFORE the
boot and never edited after the run.

THE SESSION: S, H (x453's ring), F (3 Base.Broccoli), SEED (the true multiplier 0.05; record.set stomach.buffer.calories
2000 first, then stomach.buffer.water to 1085 g, Overfull 3, re-set once if the stomach reads under 1070 g), X (one
broccoli, about +30 g; the server's food timer polled every 0.5 s until above 3200; the trigger read: the stomach, a
pair, FOOD_SICKNESS and SICK; the refusal attempt and its 8 s wait with a pair at 1.5 s; action.cancel; 3.5 game
minutes of hold reads), C, R.

PREDICTIONS (named before the run; K.view, NR_Data_Effects and K.hybrid at a97fec05):
  OF_REACH      the broccoli lands from Overfull 3 and the trigger read shows Overfull 4.
  OF_REFUSE     at Overfull 4 the next eat is refused: validStart false on the client, no landing in 8 s, the stomach no
                heavier (unmeasured if the stomach left Overfull 4 before the attempt).
  OF_EARLY      the one eat at Overfull 3 is not refused.
  OF_TIMER      the server's food timer above 3200 (TIMER_FULL 4400) on every settled bracketed read at Overfull 4.
  OF_NAUSEA     FOOD_SICKNESS 30 (foodSickStep, at least 29.5) and SICK 1 or more at the trigger read.
  OF_ENDURANCE  ENDURANCE at most 0.735 and the endurance moodle 1 or more on the settled reads at Overfull 3-4.
  PAIRS_foodEaten every client FOOD_EATEN a server level of the push window (its own later read admitted to 0.8 s), with
                a transition read; every pair saved under checks.pairs.
  H1, RING, Z   as x452.

WALL: about 3.5 min (boot about 55 s, S/H/F 12 s, SEED 4 s, X about 70 s: the eat 5 s, the timer poll up to 15 s, the
refusal 10 s, the hold about 45 s; C/R 6 s, teardown 20 s); BUDGET_S 360.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x45h_lib as L   # noqa: E402

KEY = "x453b"
PREFIX = "x453b"
PROFILE = "x45g-mod"
ARTIFACT = "overfull.json"
BUDGET_S = 360.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 15 Task 11 x453b: one broccoli from a stomach seeded at 1085 g at a 0.05 multiplier, the refusal timer, "
           "a refused eat, the nausea and the endurance ceiling at Overfull 4; one boot of " + PROFILE)
PRED = {
    "OF_REACH": "the broccoli lands from Overfull 3 and the trigger read shows Overfull 4",
    "OF_REFUSE": "validStart false, no landing in 8 s, the stomach no heavier (still Overfull 4 at the attempt)",
    "OF_EARLY": "the eat at Overfull 3 not refused",
    "OF_TIMER": "timer > 3200 on every settled bracketed Overfull 4 read",
    "OF_NAUSEA": "FOOD_SICKNESS >= 29.5 and SICK >= 1 at the trigger read",
    "OF_ENDURANCE": "ENDURANCE <= 0.735 and the endurance moodle >= 1 at Overfull 3-4",
    "PAIRS_foodEaten": "every client level a server level of the push window (slack 0.8 s), a transition read",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
