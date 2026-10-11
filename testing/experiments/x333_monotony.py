"""x333-monotony -- Plan 11f Task 9 session 3 of 3 (live): monotony days 3 and 4 (the fourth and fifth eat of each arm). One boot of profile x33-monotony (fixture default,
admin -debug, Nutrition false, DayLength 1, sleep off) on the STAGED copy of the tree (release/x33-monotony, staged fresh
from HEAD before the boot; mod/ is never booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine is
testing/experiments/x33_monotony_lib.py (frozen with x331's run). The server is x332's <run>/server copied and booted
again (reuse=True). Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5,
B3-1/B3-2).

USAGE: python testing/experiments/x333_monotony.py <the x332 run id or folder>

THIS SESSION: from the boot (about age 71) to 16:30 day 4 (age 104.5): R3_1030 (age 75.5), M3 (age 78), S3 (79),
R3_1630, R4_1030, M4 (age 102), S4 (103), each eat followed by its 30-game-minute floor window at speed 1 and a refill;
then speed 5 to age 104.5 (R4_1630 at 105.5 lies past the end).
PREDICTIONS (graded in `verdicts`): SLEEP_OFF sleepDisabled true; ADDS each eat's UNHAPPINESS add (post - pre on the
server's stats.all, the pair bracketing the landing) equals the kernel's delta on the live record within 1e-3, the
record carried over the restart (the slot's monotony.t; the entries read by H1 at S): M3 8.2717 and S3 2.0679, M4 9.9782 and S4 2.4946 (the fifth eats: the oracle's 9.978 and 2.4945, +- 0.05 at the grade) at exactly 24 h spacing
(the kernel's delta on the live ages is the graded twin); EQUAL each eat's BOREDOM add within 0.05 of its UNHAPPINESS
add; CLIENT every add seen on the client's stats.all within about 3 s of the landing; FLOOR no ring row in any eat's
30-minute window reads UNHAPPINESS below the post-add value (the target effects.unhappyTarget read on the ring); STOPS
every eat landed, every refill read back; EXE no exe true row and no asleep row; REPLAY ok under HUNGER 0.002, es 0.005,
L 0.5 %; SODIUM grade 0; H1, RING, F, Z the engine's.
READINGS: the record's monotony.t entries at S and before and after each eat (n after M4 about 3.320); UNHAPPINESS and BOREDOM over the day holds (a reading).

THE DESIGN AND THE GRADING: as x331_monotony.py's text (the whole chain), copied by reference: x33_monotony_lib.py's
docstring and SCHEDULE, x33_grade.py's docstring. Research row 13 and the Task 9 amendments as copied in x331's text.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x33_monotony_lib as L   # noqa: E402

PROFILE = "x33-monotony"
PREFIX = "x333"
PREV_PREFIX = "x332"
ARTIFACT = "monotony-3.json"
STAGE_ROOT = "release/x33-monotony/NutritionRevamp"
STAGED_AT = "35c3049e"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
END_AGE = 104.5
SESSION = ("Plan 11f Task 9 session 3 of 3: monotony days 3 and 4 (M3, S3, M4, S4), on the staged copy; one boot of " + PROFILE)
PRED = {
    "SLEEP_OFF": {"NutritionRevamp.server.nutrients.sleepDisabled": True},
    "ADDS": {"M3": 8.2717, "S3": 2.0679, "M4": 9.9782, "S4": 2.4946, "rule": "UNHAPPINESS add = the kernel's delta on the live record within 1e-3 (the nominal at 24 h spacing); the fifth eats 9.978 and 2.4945 within 0.05 at the grade"},
    "EQUAL": {"every eat": "BOREDOM add within 0.05 of the UNHAPPINESS add"},
    "CLIENT": {"every eat": "the client's stats.all shows both adds within about 3 s of the landing"},
    "FLOOR": {"every eat": "no ring row in the 30-minute window below the post-add UNHAPPINESS"},
    "EXE": {"exe true rows": 0, "asleep rows": 0},
    "STOPS": {"this session's span": "every eat landed, none missed, every refill read back"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "SODIUM": {"every chain day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
    "readings": {"n_after_M3": 2.9237, "n_after_M4": 3.3205},
}


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.session_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python testing/experiments/x333_monotony.py <the x332 run id or folder>")
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x333_monotony.py", scenario,
              grade, prev_run=L.resolve_run(sys.argv[1]), prev_prefix=PREV_PREFIX, end_age=END_AGE).run()
