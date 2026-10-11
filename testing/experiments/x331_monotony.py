"""x331-monotony -- Plan 11f Task 9 session 1 of 3 (live): monotony days 0 and 1 (the first and second eat of each arm).
One boot of profile x33-monotony (fixture default, admin -debug, Nutrition false, DayLength 1, sleep off) on the STAGED
copy of the tree (release/x33-monotony, staged fresh from HEAD before the boot; mod/ is never booted) plus
TKX_StudyFoods by its path. Build 42.21.0. The engine is testing/experiments/x33_monotony_lib.py (frozen with x331's
run). The fixture is restored (the chain's first session). Written BEFORE the boot with every prediction in it and
never edited after the run (CLAUDE.md s5, B3-1/B3-2).

USAGE: python testing/experiments/x331_monotony.py

THIS SESSION: from the boot (about 11:12 day 0, age about 4.2) to 16:00 day 1 (age 33.0): M0 (TKX.Mono450, 13:00 day
0, age 6), S0 (TKX.Staple450, 14:00, age 7), R0_1630, R1_1030, M1 (age 30), S1 (age 31), each eat followed by its
30-game-minute floor window at speed 1 and a refill (R0_1030 at age 3.5 lies before the start and is skipped); then
speed 5 to age 33.0.
PREDICTIONS (graded in `verdicts`): SLEEP_OFF sleepDisabled true; ADDS each eat's UNHAPPINESS add (post - pre on the
server's stats.all, the pair bracketing the landing) equals the kernel's delta on the live record within 1e-3:
M0 and S0 0 (the first eat of a type, n = 1, adds nothing: K.monotony.delta's max(0, n - 1)), M1 3.4129 and S1 0.8532
at exactly 24 h spacing (4.3 x 2^-1/3; x 0.25 for the staple, FoodType Bread) - the kernel's delta on the live ages,
not the nominal, is the graded twin; EQUAL each eat's BOREDOM add within 0.05 of its UNHAPPINESS add (BOREDOM set to 0
so vanilla's busy decrease cannot move it before the add; vanilla's drift between the pair's reads is the residual);
CLIENT M1's and S1's adds seen on the client's stats.all within about 3 s of the landing (the player-stats packet,
#0564, #3049; BOREDOM's arrival is unmeasured, #3656's bound: this session reads it); FLOOR no ring row in any eat's
30-minute window reads UNHAPPINESS below the post-add value (K.hybrid.write raises toward its target or subtracts a
target's fall, #3119; the target effects.unhappyTarget is read on the ring: predicted 0 at this point, so the floor
leaves the stat alone); STOPS every eat landed, every refill read back; EXE no exe true row and no asleep row; REPLAY
the session's replay of live (sleep_allowed false, the autoDrop drinks, the setany values as stat events) ok under
HUNGER 0.002, es 0.005, L 0.5 %; SODIUM grade 0 on every chain day; H1, RING, F, Z the engine's.
READINGS: the record's monotony.t entries before and after each eat (H1 bracketed keys; n after M1 about 1.794 =
2^-1/3 + 1); the monotony counter's rise per eat (1 for M1 and S1, 0 for M0 and S0: IN.addMood counts only a positive
add); UNHAPPINESS and BOREDOM over each day hold (unknown: a reading; no vanilla fall of UNHAPPINESS is expected,
#3119's reading; BOREDOM drifts by vanilla's idle rates, #3015).

RESEARCH ROW 13 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 13 | Monotony over 5 days, staple arm, effects floor | S1592-S1595, S1597 (direction; sizes are game choices anchored
  on #0042) | `test_the_fifth_daily_eat_reads_about_a_stale_item` (9.978), `test_staples_take_the_reduced_slope` (x 0.25),
  `test_the_cap_holds` (20), `test_a_partial_eat_counts_its_share...` | daily for 5 days: `TKX_StudyFoods.Mono450`
  (non-staple, mood changes 0) and `Staple450` (FoodType Bread); before each eat `stats.setany` BOREDOM and UNHAPPINESS
  to fixed values, read server before/after and the client's `stats.all`; ring UNHAPPINESS for 30 game min after each
  eat | ~100 | 2 (fast, chained) | the eat's BOREDOM and UNHAPPINESS delta, client arrival, UNHAPPINESS after the
  writer's floor minutes, `monotony.t` via H1 | fifth eat 9.978 +- 0.05 (non-staple), 2.4945 +- 0.05 (staple); delta
  equal on both stats; no fall below the post-eat value within 30 min (the floor builds on the add,
  `NR_Server_Intake.lua:870-872`); the +16.6/day tuning question (11e amendment 3) read and handed to Angus |
THE TASK 9 AMENDMENTS (task-9-amendments.md, copied in substance): delta = w x min(CAP, SLOPE x max(0, n - 1)), n the
decayed count of recent eats including this one, w = min(1, kcal / 400), SLOPE 4.3, CAP 20, half-life 72 h, window 168 h
from the latest eat, staples x 0.25 (constants read off NR_Kernel_Monotony.lua); the add is Stats.add on the server
after vanilla's JustAteFood (#3655, #3656); the effects floor (K.hybrid) only raises toward its target or subtracts a
target's fall (#3119; test 859dc98); BOREDOM's client arrival is unmeasured (#3656's bound): this task settles it.
Also monotony.t via H1 (the bracketed key form with the real item full type). The tuning read (ruling T3-2): the
steady UNHAPPINESS climb under a one-food diet, about +16.6/day predicted at a mood-neutral food, reported day by day.

THE DESIGN, NAMED BEFORE THE RUN (the whole chain; x33_monotony_lib.SCHEDULE; at(d, h) = 24 d - 7 + h, world age 0 is
07:00 on day 0, #2890):
  The live body is the default fixture's admin. Days 0-4: Mono450 at 13:00 (M<d>), Staple450 at 14:00 (S<d>), one
  each a day, w = 1 (450 kcal over the 400 kcal portion), so each arm's count runs on 24-hour spacing and the fifth
  eats (M4, S4) read the oracle's 9.978 and 2.4945 (the SLOPE was sized so that the fifth daily eat reads 9.98, the
  kernel's own comment: a live match is BY CONSTRUCTION of the constant, ruling 8-R; the live test is that the add
  path delivers the kernel's delta to both stats on the server and the client and that nothing in the minute takes
  it back).
  NO OTHER FOOD: 900 kcal a day for five days (a deficit, named; the effects layer may raise effects.unhappyTarget,
  which the ring carries and the floor reading names). Before each eat at speed 1: stats.setany BOREDOM 0 and
  UNHAPPINESS 20, 2 s settle, the client's and the server's stats.all, the record's entry, then the eat.
  Drinking: to thirst by the engine's auto-drink from a server-side canteen (ruling T5R-1), refilled to 0.9 L after
  every eat and at 10:30 and 16:30.
  Sessions: x331 (fresh fixture, to 16:00 day 1, age 33.0), x332 (to 04:00 day 3, age 69.0: M2, S2), x333
  (to 16:30 day 4, age 104.5: M3, S3, M4, S4), chained by server reuse.
  The replay feeds NICOTINE_WITHDRAWAL from each ring row (the tool's feed; 0 here) and takes the setany values as stat
  events (lib change 4); the activity off the ring's rate and exe (the tool, 3daaca9).
THE GRADING (after the chain, by the committed analysis script testing/experiments/x33_grade.py, into a staged artifact
folder testing/artifacts/x33-grade-<date>/): per eat the live adds, the kernel's delta on the live record, the
nominal 24-hour delta, the replay's own monotony delta at the eat (the replay's eats log), the client's arrival and
the floor window; the fifth eats against 9.978 +- 0.05 and 2.4945 +- 0.05; the climb: the day-by-day UNHAPPINESS a
one-food diet carries (the sum of one arm's live adds, UNHAPPINESS having no vanilla fall) against the kernel's daily
projection and its steady +16.54 a day; each session's replay of live under HUNGER 0.002, es 0.005, L 0.5 %.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x33_monotony_lib as L   # noqa: E402

PROFILE = "x33-monotony"
PREFIX = "x331"
PREV_PREFIX = None
ARTIFACT = "monotony-1.json"
STAGE_ROOT = "release/x33-monotony/NutritionRevamp"
STAGED_AT = "35c3049e"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
END_AGE = 33.0
SESSION = ("Plan 11f Task 9 session 1 of 3: monotony days 0 and 1 (M0, S0, M1, S1), on the staged copy; one boot of " +
           PROFILE)
PRED = {
    "SLEEP_OFF": {"NutritionRevamp.server.nutrients.sleepDisabled": True},
    "ADDS": {"M0": 0.0, "S0": 0.0, "M1": 3.4129, "S1": 0.8532,
             "rule": "UNHAPPINESS add = the kernel's delta on the live record within 1e-3 (the nominal at 24 h spacing)"},
    "EQUAL": {"every eat": "BOREDOM add within 0.05 of the UNHAPPINESS add"},
    "CLIENT": {"M1, S1": "the client's stats.all shows both adds within about 3 s of the landing"},
    "FLOOR": {"every eat": "no ring row in the 30-minute window below the post-add UNHAPPINESS; target 0"},
    "EXE": {"exe true rows": 0, "asleep rows": 0},
    "STOPS": {"this session's span": "every eat landed, none missed, every refill read back"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "SODIUM": {"every chain day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved (the monotony entries optional before a type's first eat)"},
    "RING": {"pages": "all read, errors 0"}, "F": {"departure flush": "within 90 s"},
    "Z": {"mod error lines": 0, "admin parked": False},
    "readings": {"n_after_M1": 1.7937, "monotony_counter_rise": {"M0": 0, "S0": 0, "M1": 1, "S1": 1}},
}


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.session_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x331_monotony.py", scenario,
              grade, end_age=END_AGE).run()
