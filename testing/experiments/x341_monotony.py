"""x341-monotony -- Plan 11f Task 9r session 1 of 3 (live): research row 13 (monotony) on the self-limiting floor design,
Mono450 days 0-2 (the rise). One boot of profile x34-monotony (fixture default, admin -debug, Nutrition false,
DayLength 1, sleep off) on the STAGED copy of the tree (release/x34-monotony, staged fresh from HEAD before the boot;
mod/ is never booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine is
testing/experiments/x34_monotony_lib.py (frozen with x341's run). The fixture is restored (the chain's first session).
Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

USAGE: python testing/experiments/x341_monotony.py

THIS SESSION: from the boot (about 11:12 day 0, age about 4.2) to 14:00 day 2 (age 55.0): the first-eat gate (the
record's effects.panicTarget and the server's PANIC read; UNHAPPINESS and BOREDOM set to 0), then TKX.Mono450 at
M0_1300 (age 6), M0_1900 (12), M1_0800 (25), M1_1300 (30), M1_1900 (36), M2_0800 (49), M2_1300 (54), each at speed 1
with a 6-game-minute window and a refill; refills at 01:00, 04:00, 10:30, 16:30 and 22:00, BOREDOM reset to 0 with
those at 04:00, 10:30, 16:30 and 22:00; day-end reads E0 (age 16.5) and E1 (40.5); speed 5 between stops.

THE DESIGN (the whole chain; x34_monotony_lib.SCHEDULE; at(d, h) = 24 d - 7 + h, world age 0 is 07:00 on day 0, #2890):
  Days 0-4: Mono450 (450 kcal, a whole portion, FoodType NoExplicit, mood changes 0) at the oracle's MEALS_3 hours
  08:00, 13:00, 19:00 (test_kernel_monotony.py; day 0 from 13:00); days 5-8: a varied diet, each eat a TKX_StudyFoods
  type never eaten before (VARIED), so the target is Mono450's decaying level alone. Sessions: x341 (fresh, to age
  55.0), x342 (to age 113.5: the rest of the Mono450 leg), x343 (to age 161.5: the varied leg, the reconnect at 20:00 on
  day 5, at least 6 game hours away), x344 (optional, to age 209: more of the release). The kernel's constants are read
  off NR_Kernel_Monotony.lua by the grade (K.monotony on the lupa host): SLOPE 4.3, CAP 30, STAPLE 0.25, half-life
  72 h, window 168 h, BORED_MAX 49, FLOOR_EPS 0.05 (NR_Kernel_Hybrid.lua), the rises 22 (UNHAPPINESS) and 25 (BOREDOM)
  a game hour.
  Named departures: the BOREDOM resets (lib change 4: vanilla's idle rise would carry BOREDOM past the BORED level-2
  step 50 within about two days, where vanilla adds UNHAPPINESS); the refills every 3-6 game hours (the panic guard:
  the dehydration PANIC floor of 7 at a pool deficit of 1.5 %, NR_Data_Effects.lua:210-213, must stay off); only the
  study foods are eaten (Mono450: 1350 kcal a day, a deficit the effects layer may answer through
  effects.unhappyTarget, which the ring carries and the composition adds).
PREDICTIONS (graded in `verdicts`): SLEEP_OFF sleepDisabled true; GATE (the gate's reading) effects.panicTarget and
the server's PANIC read before the first eat: unknown (a fresh record's kernel-test default panicTarget is 10; the live
value is the reading; PANIC above 5 with no deficit is a finding and BOREDOM is then graded as wiped); NOJUMP no eat
moves UNHAPPINESS or BOREDOM by more than one writer minute's rise inside the bracketing pair (the target jumps at the
eat: M0_1900 by 4.3 x 2^(-6/72) = 4.059 and every later Mono450 eat by SLOPE x one portion = 4.3 until the cap
binds; the stats follow only at the writer minutes); CLIENT
the client's reads after each eat show the server's post values within 0.05; PANIC no ring row reads the writer's
PANIC above 5; EXE no exe true row, no asleep row; STOPS every stop done, every eat landed, every refill read back;
REPLAY the session's replay of live (sleep_allowed false, the autodrop events, the setany values as stat events) ok
under HUNGER 0.002, es 0.005, L 0.5 %; SODIUM grade 0 on every chain day; H1, RING, F, Z the engine's.
THE GRADING (after the chain, by the committed testing/experiments/x34_grade.py, into a staged artifact folder
testing/artifacts/x34-grade-<date>/): (a) no jump at the eat, the first rise at the next writer minute; (b) the stats
track the kernel's target (from the ring's Mono450 entry) within FLOOR_EPS plus one minute's lag, and the rise runs at
22 and 25 a game hour; (c) BOREDOM under 49 on every row; (d) on the varied diet the stats fall by the target's fall,
no single-minute drop over the decay's own per-minute fall plus FLOOR_EPS; (e) live UNHAPPINESS against the replay;
the per-day table against the oracle's floor_run on the run's nominal schedule; the reconnect; the day-end client reads.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x34_monotony_lib as L   # noqa: E402

PROFILE = "x34-monotony"
PREFIX = "x341"
PREV_PREFIX = None
ARTIFACT = "monotony-1.json"
STAGE_ROOT = "release/x34-monotony/NutritionRevamp"
STAGED_AT = "c648c178"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
END_AGE = 55.0
SESSION = ("Plan 11f Task 9r session 1 of 3: the monotony floor, Mono450 days 0-2 (the rise), on the staged copy; one "
           "boot of " + PROFILE)
PRED = {
    "SLEEP_OFF": {"NutritionRevamp.server.nutrients.sleepDisabled": True},
    "GATE": {"effects.panicTarget": "unknown (a reading)", "PANIC": "unknown (a reading); above 5 with no deficit is "
             "a finding"},
    "NOJUMP": {"every eat whose target jumps by 0.5 or more": "UNHAPPINESS and BOREDOM move by at most one writer "
               "minute's rise inside the pair", "target_jump": {"M0_1900": 4.059, "later": 4.3}},
    "CLIENT": {"every eat": "the client's reads show the server's post values within 0.05"},
    "PANIC": {"ring rows with the writer's PANIC above 5": 0},
    "EXE": {"exe true rows": 0, "asleep rows": 0},
    "STOPS": {"this session's span": "every stop done, every eat landed, every refill read back"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "SODIUM": {"every chain day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved (the monotony entries and moodLast optional before the first eat or write)"},
    "RING": {"pages": "all read, errors 0"}, "F": {"departure flush": "within 90 s"},
    "Z": {"mod error lines": 0, "admin parked": False},
}


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.session_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x341_monotony.py", scenario,
              grade, end_age=END_AGE).run()
