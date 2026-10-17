"""x453-overfull -- Plan 15 Task 11 (live): overeating on the food-timer bridge (Task 8): raw broccoli eaten from a
stomach seeded near the hard capacity stops at Overfull 4 with a refused eat; the refusal timer, the nausea and the
endurance ceiling at Overfull 3-4; the client's FOOD_EATEN against the server's.

One boot of profile x45g-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan15-x45g of
mod/NutritionRevamp at a97fec05, Nutrition false, DayLength 1, sleep off), build 42.21.0, the staged copy checked as
x452's. The engine is testing/experiments/x45g_lib.py. Written BEFORE the boot and never edited after the run.

THE SESSION: S, H (the ring), F (12 Base.Broccoli by RCON), SEED (the true multiplier to 0.2 through time.multiplier,
so a networked eat, which ends in real time (#3766), costs about a game minute of emptying; record.set
stomach.buffer.water to bring the stomach to 960 g (Overfull 2) and stomach.buffer.calories to 2000 kcal, so the solid
lane empties at about 0.31 % a game minute, K.stomach.solidFraction), X (one broccoli at a time, each eat after a read
settled 1.5 game minutes and 1.5 wall s past the last landing, until a read shows Overfull 4 with the server's
refusal timer above 3200 (a read at 4 without it waits one writer minute, then eats again if back under 4); then one
more eat
attempted (the stomach read again just before it), its validStart read and its landing waited 8 s;
a pair 1.5 s into the wait, the read a stale client fails; action.cancel; the hold's reads for 3 game minutes, kept
as readings; each read brackets its stats.get with two stomach reads, and the timer and endurance grades skip a read a
writer minute fell inside),
C (action.cancel; the clock restored from S's read), R.

PREDICTIONS (named before the run): a broccoli adds 32.95 g (NR_Data_Nutrients.lua: water 28.93, carbs 2.15, protein
0.91, fat 0.12, fibre 0.84); about 3 g a game minute empties. The HEAD replay at a97fec05 (`python
testing/experiments/x45g_prerun.py x453`: the seed at age 4.2 reading 957 g, a broccoli every 3 game minutes) reaches
Overfull 4 on the 7th eat, at 1108 g.
  OF_REACH      eats land from Overfull 2-3 until a read shows Overfull 4.
  OF_REFUSE     the eat at Overfull 4 (still 4 just before it, else unmeasured): validStart false on the client, no
                landing in 8 s, the stomach no heavier.
  OF_EARLY      no eat refused below Overfull 4.
  OF_TIMER      the food timer above 3200 (FOOD_EATEN 3, K.view TIMER_FULL 4400 at DayLength 1) on every settled
                Overfull 4 read; at or under 3200 below 4 (0 unsated: the seed leaves the meal pool alone).
  OF_NAUSEA     FOOD_SICKNESS 30 (foodSickStep) and SICK 1 or more at the trigger read, the first settled read at
                Overfull 4 ("at once").
  OF_ENDURANCE  ENDURANCE at most 0.735 and the endurance moodle 1 or more at Overfull 3-4 (NR.Severity 1.0).
  PAIRS_foodEaten every client FOOD_EATEN a server level of the push window.
  H1, RING, Z   as x452.
  Unmeasured by design: the server-side refusal through the open-and-eat craft (no harness command crafts).

WALL: about 4 min (boot about 55 s, S/H/F 12 s, SEED 3 s, X about 90 s, C/R 6 s, teardown 20 s); BUDGET_S 420.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x45g_lib as L   # noqa: E402

KEY = "x453"
PREFIX = "x453"
PROFILE = "x45g-mod"
ARTIFACT = "overfull.json"
BUDGET_S = 420.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 15 Task 11 x453: raw broccoli eaten from a stomach seeded at 960 g until Overfull 4, then a refused "
           "eat; the timer, the nausea and the endurance ceiling; one boot of " + PROFILE)
PRED = {
    "OF_REACH": "eats land from Overfull 2-3 until a read shows Overfull 4 (replay: the 7th eat, 1108 g)",
    "OF_REFUSE": "validStart false, no landing in 8 s, the stomach no heavier (still Overfull 4 at the attempt)",
    "OF_EARLY": "no eat refused below Overfull 4",
    "OF_TIMER": "timer > 3200 at settled Overfull 4, <= 3200 below",
    "OF_NAUSEA": "FOOD_SICKNESS >= 29.5 and SICK >= 1 at the first settled Overfull 4 read",
    "OF_ENDURANCE": "ENDURANCE <= 0.735 and the endurance moodle >= 1 at Overfull 3-4",
    "PAIRS_foodEaten": "every client level a server level of the push window, a transition read",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
