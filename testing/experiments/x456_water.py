"""x456-water -- Plan 15 Task 11 (live): no water on the new water base and option B (Tasks 3-5): Parched shows at the
4 % dehydration onset as the thirst cap lifts, the constant goes to 0, health drains at the dehydration rate to its
first floor and holds, the first floor's hour without water against the kernel's and the spec's "about 35 h", the basal
loss against 2000 + 32 (lm - 52.02) g a day, and SICK 4 still draining while Parched.

One boot of profile x45g-mod (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan15-x45g of
mod/NutritionRevamp at a97fec05, Nutrition false, DayLength 1, sleep off), build 42.21.0, the staged copy checked as
x452's. The engine is testing/experiments/x45g_lib.py. Written BEFORE the boot and never edited after the run.

THE SESSION: S (the auto-drink probe: the fixture's admin carries no fluid container, x446), H (the ring), A (at speed
1: record.set fluids.water so the deficit reads 3.80 % (dehydPct is linear in water); speed 5 until dehydPct reads 3.97 %,
then speed 1 with pairs until 3 game minutes past the onset; the health at the onset; the constant), B (speed 5, a
health point every 0.5 s, until 1.5 game h past the floor), P (FOOD_SICKNESS 95 for one 10 s window at speed 1, then 0),
C, R.

PREDICTIONS (named before the run; the default body, lm 52.02 and fm 13.0 kg, x446's ring; lx 0 at first sight; the
HEAD replay of this schedule at a97fec05, `python testing/experiments/x45g_prerun.py x456`: w 65.025 kg, the set at age
4.2 to 3.80 %, the onset 1.62 game h later at 4.0013 % with THIRST 0.938 (at most 0.83 before), dehydPct rising
0.1245 % and water falling 83.333 g a game hour, the floor reached 6.35 game h after the onset at 47.12, the first-floor
hour 38.48 h):
  DEHYD_ONSET    the ring's first dehydrated row at 4.0 % (the row before under), THIRST over 0.84 there or next (the
                 cap lifted), at most 0.83 before it.
  PARCHED_SHOWN  the server's THIRST moodle 4 on its last read within 3 game minutes after the onset row.
  CONST          0.0165 before the onset, 0 after it.
  DEHYD_DRAIN    200 a game day (8.33 a game hour) within 15 % above the floor, before its reach.
  DEHYD_FLOOR    within 0.5 of the ring's targetFloor (50 at 4 %, 40 / 11 lower per further per cent) for 1.5 game h.
  BASAL          the ring's water loss 2000 + 32 (lm - 52.02) g a day (83.3 g a game hour at lm 52.02) within 3 %.
  DEHYD_PACE     the live first-floor hour without water within 1.0 h of the kernel's, which tracks the floor as it
                 deepens (about 0.45 a game hour past 4 %): 4 % of 65.0 kg over (2000 - 57.1) g a day is 32.1 h, plus
                 about 6.35 h of drain to a floor near 47.1: about 38.47 h (38.1 h to a floor of 50).
  Reading, not a grade (review M3): checks.dehyd_spec, the live and the kernel hours beside the spec's "about 35 h"
                 (the kernel +3.5 h, 10 %).
  P_SICK         Parched at the floor, SICK 4 drains red x M_H = 29.7 a game hour within 20 % (no floor heal at
                 THIRST 4), the constant 0 at both ends.
  PAIRS_thirst   every client THIRST level a server level of the push window.
  H1, RING, Z    as x452.

WALL: about 4 min (boot about 55 s, S/H 8 s, A about 30 s, B about 60 s, P 15 s, C/R 6 s, teardown 20 s); BUDGET_S 420.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x45g_lib as L   # noqa: E402

KEY = "x456"
PREFIX = "x456"
PROFILE = "x45g-mod"
ARTIFACT = "water.json"
BUDGET_S = 420.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 15 Task 11 x456: the body-water deficit driven by record.set to 3.80 %, Parched and the lifted cap at "
           "4 %, the drain to the first floor and its hold, the basal loss, and SICK 4 while Parched; one boot of "
           + PROFILE)
PRED = {
    "DEHYD_ONSET": "first dehydrated row at 4.0 %, THIRST > 0.84 there or next, <= 0.83 before",
    "PARCHED_SHOWN": "THIRST moodle 4 on the last server read within 3 game minutes after the onset",
    "CONST": "0.0165 before the onset, 0 after it",
    "DEHYD_DRAIN": "200 a game day within 15 %",
    "DEHYD_FLOOR": "within 0.5 of the ring's floor for 1.5 game h",
    "BASAL": "2000 + 32 (lm - 52.02) g a day within 3 %",
    "DEHYD_PACE": "the live first-floor hour within 1.0 h of the kernel's (about 38.47 h at the default body)",
    "P_SICK": "29.7 a game hour within 20 %, the constant 0",
    "PAIRS_thirst": "every client level a server level of the push window, a transition read",
    "H1": "every ring path resolved", "RING": "every page read, errors 0", "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
