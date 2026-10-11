"""x344-monotony -- Plan 11f Task 9r session 4 of 3 (an optional fourth) (live): research row 13 (monotony) on the self-limiting
floor design, more of the release on the varied diet. One boot of profile x34-monotony (fixture default, admin -debug, Nutrition false, DayLength 1,
sleep off) on the STAGED copy of the tree (release/x34-monotony, staged fresh from HEAD before the boot; mod/ is never
booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine is testing/experiments/x34_monotony_lib.py (frozen
with x341's run). The server is x343's <run>/server copied and booted again (reuse=True). Written BEFORE the boot
with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

USAGE: python testing/experiments/x344_monotony.py <the x343 run id or folder>

THIS SESSION: OPTIONAL, run only when the chain's wall and memory allow: from the boot (about age 163.5) to
age 209.0: the varied diet at V7_0800 (169, SnackC), V7_1300 (174, SnackF), V7_1900 (180, Mixed650), V8_0800 (193,
Mixed217), V8_1300 (198, Marc), V8_1900 (204, Casserole); the refills and resets of the calendar; day-end reads E7
(184.5) and E8 (208.5).

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
PREDICTIONS (graded in `verdicts`): SLEEP_OFF sleepDisabled true; NOJUMP trivial; RELEASE the target falls from about
17.2 (age 170) to about 10.5 (age 209) on the nominal schedule; the stats fall with it; CLIENT the client's reads after each eat show the server's post values within 0.05; PANIC no ring row
reads the writer's PANIC above 5; EXE no exe true row, no asleep row; STOPS every stop done, every eat
landed, every refill read back; REPLAY ok under HUNGER 0.002, es 0.005, L 0.5 %; SODIUM grade 0; H1, RING,
F, Z the engine's.
THE GRADING: as x341_monotony.py's text, by the committed testing/experiments/x34_grade.py.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x34_monotony_lib as L   # noqa: E402

PROFILE = "x34-monotony"
PREFIX = "x344"
PREV_PREFIX = "x343"
ARTIFACT = "monotony-4.json"
STAGE_ROOT = "release/x34-monotony/NutritionRevamp"
STAGED_AT = "c648c178"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
END_AGE = 209.0
SESSION = ("Plan 11f Task 9r session 4 (optional): the monotony floor, more of the release, on the staged copy; one boot of " + PROFILE)
PRED = {
    "SLEEP_OFF": {"NutritionRevamp.server.nutrients.sleepDisabled": True},
    "CLIENT": {"every eat": "the client's reads show the server's post values within 0.05"},
    "PANIC": {"ring rows with the writer's PANIC above 5": 0},
    "EXE": {"exe true rows": 0, "asleep rows": 0},
    "STOPS": {"this session's span": "every stop done, every eat landed, every refill read back"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "SODIUM": {"every chain day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
    "NOJUMP": {"varied eats": "trivial (no target jump)"},
    "RELEASE": {"nominal schedule": "the target reads about 17.2 at age 170 and about 10.5 at age 209"},
}


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.session_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python testing/experiments/x344_monotony.py <the x343 run id or folder>")
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x344_monotony.py", scenario,
              grade, prev_run=L.resolve_run(sys.argv[1]), prev_prefix=PREV_PREFIX, end_age=END_AGE).run()
