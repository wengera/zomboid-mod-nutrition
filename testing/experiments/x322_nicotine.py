"""x322-nicotine -- Plan 11f Task 8 session 2 of 3 (live): request day 2 and day 3's breakfast, the withdrawal reaching
its cap. One boot of profile x32-nicotine (fixture default, admin -debug, Nutrition false, DayLength 1, sleep off) on
the STAGED copy of the tree (release/x32-nicotine, staged fresh from HEAD before the boot; mod/ is never booted) plus
TKX_StudyFoods by its path. Build 42.21.0. The engine is testing/experiments/x32_nicotine_lib.py (frozen with x321's
run). The server is x321's <run>/server copied and booted again (reuse=True). Written BEFORE the boot with every
prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

USAGE: python testing/experiments/x322_nicotine.py <the x321 run id or folder>

THE x32 CHAIN (ruling T8-1): x311 (x31_nicotine_lib) sent trait.set the display name Smoker, which does not resolve
(no CharacterTrait.Smoker), so its gate smoke was a non-smoker's and the gate was falsified (F-T8-1). This chain sends
the static field name SMOKER (CharacterTrait.<clinit> @661-@667 L85) and phase S stops the session (no H, W or X)
when the trait list read back lacks Smoker (x32_nicotine_lib change b). Otherwise the design, the predictions and
the calendar are x311-x313's, re-run from a fresh fixture.

THIS SESSION: from the boot (about age 40.5, 2 game hours after x321's end at 38.5, as x282 followed x281) to 11:30 day
3 (age 74.5): D2_08 (age 49), R2_1030, D2_13 (54), R2_1630, D2_20 (61), D3_08 (73), each meal followed by its refill;
then speed 5 to age 74.5. No smoke and no edit in this session.
PREDICTIONS (graded in `verdicts`): SLEEP_OFF sleepDisabled true; SMOKER the trait list holds Smoker across the restart
(the player save); RISE the stat carried over the restart (the server's stat and timer are the player's, saved) and
still rising at about 0.01125 a game hour (0.0100-0.0125 over the rows between 0 and the cap) until the first ring row
at the cap 0.51 between ages 53.0 and 58.0 (predicted about 55.2: the gate smoke at about 4.3 plus 50.9 h), then held
at the cap; the anchor satiety.nicH held across the restart where x321 left it (the stored input; no fall seen, the
stat never below the hoist's last read); EXE no exe true row and no asleep row; STOPS every meal of this session's span
done, every eat landed, every refill read back; REPLAY ok under HUNGER 0.002, es 0.005, L 0.5 %; SODIUM grade 0; H1,
RING, F, Z the engine's.
READINGS: the factor at the meals (live, by the grade): D2_08 about 1.113 (the stat about 0.44), D2_13 about 1.127
(0.496), D2_20 about 1.1298 and D3_08 about 1.1294 (the cap, the anchor about 2.1 and 2.6 days old); the timer and the
stat at S.

THE DESIGN AND THE GRADING: as x321_nicotine.py's text (the whole chain), copied by reference: x32_nicotine_lib.py's
docstring and SCHEDULE, x32_grade.py's docstring. Research row 12 and the Task 8 amendments as copied in x321's text.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x32_nicotine_lib as L   # noqa: E402

PROFILE = "x32-nicotine"
PREFIX = "x322"
PREV_PREFIX = "x321"
ARTIFACT = "nicotine-2.json"
STAGE_ROOT = "release/x32-nicotine/NutritionRevamp"
STAGED_AT = "35c3049e"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
END_AGE = 74.5
SESSION = ("Plan 11f Task 8 session 2 of 3: request day 2 and day 3's breakfast, the withdrawal reaching its cap, on "
           "the staged copy; one boot of " + PROFILE)
PRED = {
    "SLEEP_OFF": {"NutritionRevamp.server.nutrients.sleepDisabled": True},
    "SMOKER": {"trait list across the restart": "holds Smoker (else the session stops in phase S, change b)"},
    "RISE": {"segment": -1, "bands": {"slope_per_h": (0.0100, 0.0125), "at_cap.age": (53.0, 58.0)},
             "text": "carried over the restart, still about 0.01125 a game hour, the cap 0.51 about age 55.2"},
    "EXE": {"exe true rows": 0, "asleep rows": 0},
    "STOPS": {"this session's span": "every meal done, none missed, every eat landed, every refill read back"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %), the stat fed from the ring"},
    "SODIUM": {"every chain day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
    "readings": {"factor_D2_08": 1.113, "factor_D2_13": 1.127, "factor_D2_20": 1.1298, "factor_D3_08": 1.1294},
}


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.session_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python testing/experiments/x322_nicotine.py <the x321 run id or folder>")
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x322_nicotine.py", scenario,
              grade, prev_run=L.resolve_run(sys.argv[1]), prev_prefix=PREV_PREFIX, end_age=END_AGE).run()
