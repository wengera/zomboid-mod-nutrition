"""x454-starve -- Plan 15 Task 11 (live): starvation on option B and the drain-and-floor engine (Tasks 4-6): the acute
onset at 30 unfed hours lifts the hunger cap and shows Starving, the severe-moodle constant goes to 0, health drains at
the starvation rate to its first floor and holds there, and eating then ends the state and health recovers.

One boot of profile x45g-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan15-x45g of
mod/NutritionRevamp at a97fec05, Nutrition false, DayLength 1, sleep off), build 42.21.0, the staged copy checked as
x452's. The engine is testing/experiments/x45g_lib.py. Written BEFORE the boot and never edited after the run.

THE SESSION: S, H (the ring), F (one CannedBologneseOpen by RCON), A (at speed 1: record.set satiety.M 0, then
drain.fedAgeH to the age less 29.75 h, so the onset falls 0.25 game h later; polled with pairs until 3 game minutes past
the onset; the constant read), B (health.reduce to 55; speed 5 with a health point every 0.5 s until 1.5 game h past the
floor), E (the can at speed 1; the constant and the drain read; 2 game h at speed 5 with health points), C, R.

PREDICTIONS (named before the run; K.drain and K.hybrid at a97fec05; the HEAD replay of this schedule, `python
testing/experiments/x45g_prerun.py x454`: the set at age 4.2, the onset at 4.45 at 30.0 unfed hours, HUNGER at most
0.69 before it and 1.0 on it, the floor 50 and the rate 25; the can 6.6 game h after the onset ends the state in the
same minute, HUNGER 0.033 and the meal pool 644 after it; health is the kernel arithmetic below):
  ONSET           the ring's first starveAcute row at 30 unfed hours (within 0.05 h), HUNGER over 0.70 there or on the
                  next row (the cap lifted, the minimum 0.71), at most 0.69 on every row between the set and it.
  STARVING_SHOWN  the server's HUNGRY moodle 4 on its last read within 3 game minutes after the onset row.
  CONST           the constant 0.0165 before the onset and 0 after it until the eat.
  DRAIN_RATE      health falls at 25 a game day (1.042 a game hour) within 15 % above the floor.
  FLOOR_HOLD      health holds within 0.3 of the ring's targetFloor (50 at the onset BMI) for 1.5 game hours.
  RECOVER         after the can, starveAcute false within 2 game minutes of the landing, the constant back to 0.0165,
                  health up by 0.5 or more over 2 game hours and never 0.3 under the landing's. Basis (review
                  L2): the Well Fed food heal, about 28 a game hour while the meal pool holds 435 or more and no drain
                  is active, or vanilla's regeneration alone, 0.43-1.07 a game hour (0.86 over 2 game h at HUNGRY or
                  THIRST 3); the levels and satiety.M at the eat are recorded.
  PAIRS_hungry    every client HUNGRY level a server level of the push window.
  H1, RING, Z     as x452.

WALL: about 4 min (boot about 55 s, S/H/F 12 s, A about 25 s, B about 55 s, E about 30 s, C/R 6 s, teardown 20 s);
BUDGET_S 420.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x45g_lib as L   # noqa: E402

KEY = "x454"
PREFIX = "x454"
PROFILE = "x45g-mod"
ARTIFACT = "starve.json"
BUDGET_S = 420.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 15 Task 11 x454: the acute starvation onset driven by record.set, Starving and the lifted cap, the "
           "drain to the first floor and its hold, then a can and the recovery; one boot of " + PROFILE)
PRED = {
    "ONSET": "first starveAcute row at 30 unfed h (+/- 0.05), HUNGER > 0.70 there or next, <= 0.69 before",
    "STARVING_SHOWN": "HUNGRY 4 on the last server read within 3 game minutes after the onset",
    "CONST": "0.0165 before the onset, 0 after it until the eat",
    "DRAIN_RATE": "25 a game day within 15 %",
    "FLOOR_HOLD": "within 0.3 of the ring's floor for 1.5 game h",
    "RECOVER": "starveAcute false within 2 game minutes, the constant 0.0165, health +0.5 over 2 game h",
    "PAIRS_hungry": "every client level a server level of the push window, a transition read",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
