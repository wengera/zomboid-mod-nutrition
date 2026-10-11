"""x313-nicotine -- Plan 11f Task 8 session 3 of 3 (live): day 3's lunch at the cap, the fade edit, the T2-F edit, the
second smoke and the rise after it, day 4 to its lunch. One boot of profile x31-nicotine (fixture default, admin -debug,
Nutrition false, DayLength 1, sleep off) on the STAGED copy of the tree (release/x31-nicotine, staged fresh from HEAD
before the boot; mod/ is never booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine is
testing/experiments/x31_nicotine_lib.py (frozen with x311's run). The server is x312's <run>/server copied and booted
again (reuse=True). Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5,
B3-1/B3-2).

USAGE: python testing/experiments/x313_nicotine.py <the x312 run id or folder>

THIS SESSION: from the boot (about age 76.5) to 14:30 day 4 (age 103.5): D3_13 (age 78), FADE (80, 15:00 day 3),
R3_1630, D3_20 (85), T2F (86, 21:00 day 3), SMOKE2 (90, 01:00 day 4), D4_08 (97), R4_1030, D4_13 (102), each meal and
nicotine stop followed by its refill (R3_1030 at 75.5 lies before the session's start and is skipped); then speed 5 to
age 103.5. The edits run at speed 1: lua.setpath NutritionRevamp.server.store.records.admin.satiety.nicH, a
time.snapshot either side (lib change 5).
PREDICTIONS (graded in `verdicts`): SLEEP_OFF sleepDisabled true; SMOKER the trait list holds Smoker; EDITS FADE: the
anchor set to the world age at the set minus 91 x 24 and held by the drains (the stat at the cap never falls: laid
equals the value set, 1e-9), T2F: the anchor set to nil and re-laid by the next drain at that drain's age minus
182 x 24 (ruling T2-F: the stat reads above 0, no fall seen; within 1e-6); SMOKES SMOKE2 seen within 60 s, eats +1, the
stat falls from the cap by 0.51 within 1e-4 to 0 (#3632, f = 1), landed +0, the timer 0 after; RISE after SMOKE2 the
stat stays 0 for about 5.56 game h (the first ring row above 0 between 4.5 and 7.0 h after the smoke) and rises at about
0.01125 a game hour (0.0100-0.0125); EXE no exe true row and no asleep row; STOPS every meal and nicotine stop of this
session's span done, every eat landed, every refill read back; REPLAY ok under HUNGER 0.002, es 0.005, L 0.5 % (the
edits as setpath events placed off the ring, lib change 7); SODIUM grade 0; H1, RING, F, Z the engine's.
READINGS (the factor, by the grade): D3_13 about 1.1292 (the cap, the anchor about 2.8 days old; the third meal of the
next-day ratio); from FADE to T2F the formula about 1 + 0.1313 x 1 x 0.4999 = 1.0656 (D3_20 reads it); from T2F to the
smoke exactly 1.0 (the fade 0 at 182 days); after the smoke 1.0 while the stat reads 0 (the anchor follows the minute),
then 1 + 0.1313 x w / 0.51 x about 1 (D4_08 about 1.004, D4_13 about 1.018): the reset from a fully faded anchor.

THE DESIGN AND THE GRADING: as x311_nicotine.py's text (the whole chain), copied by reference: x31_nicotine_lib.py's
docstring and SCHEDULE, x31_grade.py's docstring. Research row 12 and the Task 8 amendments as copied in x311's text.
THE ORDER of the edits and the smoke departs from the amendment's (smoke, T2-F, fade), named in the lib (change 6).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x31_nicotine_lib as L   # noqa: E402

PROFILE = "x31-nicotine"
PREFIX = "x313"
PREV_PREFIX = "x312"
ARTIFACT = "nicotine-3.json"
STAGE_ROOT = "release/x31-nicotine/NutritionRevamp"
STAGED_AT = "35c3049e"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
END_AGE = 103.5
SESSION = ("Plan 11f Task 8 session 3 of 3: day 3's lunch at the cap, the fade and T2-F edits, the second smoke and "
           "the rise after it, day 4 to its lunch, on the staged copy; one boot of " + PROFILE)
PRED = {
    "SLEEP_OFF": {"NutritionRevamp.server.nutrients.sleepDisabled": True},
    "SMOKER": {"trait list across the restart": "holds Smoker"},
    "EDITS": {"FADE": "laid equals the value set (age - 91 x 24), 1e-9", "T2F": "re-laid at the drain's age - 182 x 24, 1e-6"},
    "SMOKES": {"SMOKE2": "seen within 60 s; eats +1; the stat falls 0.51 (within 1e-4) to 0; landed +0; the timer 0 after"},
    "RISE": {"segment": -1, "bands": {"first_above_0.h_after_smoke": (4.5, 7.0), "slope_per_h": (0.0100, 0.0125)},
             "text": "0 for about 5.56 game h after SMOKE2, then about 0.01125 a game hour"},
    "EXE": {"exe true rows": 0, "asleep rows": 0},
    "STOPS": {"this session's span": "every meal and nicotine stop done, none missed, every eat landed, every refill "
                                     "read back"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %), the stat fed from the ring, the edits placed"},
    "SODIUM": {"every chain day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
    "readings": {"factor_D3_13": 1.1292, "factor_fade": 1.0656, "factor_t2f": 1.0, "factor_D4_08": 1.004,
                 "factor_D4_13": 1.018},
}


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.session_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python testing/experiments/x313_nicotine.py <the x312 run id or folder>")
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x313_nicotine.py", scenario,
              grade, prev_run=L.resolve_run(sys.argv[1]), prev_prefix=PREV_PREFIX, end_age=END_AGE).run()
