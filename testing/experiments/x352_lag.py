"""x352-lag -- Plan 11f Task 6r session 2 of 3 of the exercise chain (live): research row 9 (the acute appetite
suppression around one Fitness set and its decay, on B0) and row 10 (the exercise lag), re-run under the C-17 activity
billing (rulings C17-1, C17-3, C17-5). One boot of profile x35-exercise (fixture default, admin -debug, Nutrition false,
DayLength 1, sleep off) on the STAGED copy of the tree (release/x35-exercise, staged fresh from HEAD before the boot;
mod/ is never booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine is
testing/experiments/x35_exercise_lib.py (frozen with x351's run). It copies x351's <run>/server and boots it again
(reuse=True).
Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

USAGE: python testing/experiments/x352_lag.py <the x351 run id (testing/runs/<id>) or its folder>

THIS SESSION: from the attach (about 06:30 day 2, age 47.5) to 04:30 day 4 (age 93.5): D2_08, D2_13, B2, D2_20,
R3_0200, D3_08, D3_13, B3, D3_20, R4_0200 (a refill stop before the session's start is skipped; each meal and bout is
followed by a refill).
READINGS: bouts B2 and B3; the meals' es; the drinking and the sodium guard per chain day; the hourly es.

THE TASK 6r AMENDMENTS (copied in substance):
  | 9  | One Fitness set of about 60 game min (burpees), then 3 game h at rest | Billed 6.0 from the first flagged minute.
       exe false within one row of the set's end, and billing 1.3 from the next still minute (C-17 review finding 6).
       The EPOC pool released total equals 0.10 x the set's exercise kcal within 1 %. S rises at the vigorous rate and
       decays at the 0.15 h half-life. Factor within 1 % of replay. Exercise tail at most 1 row, against x29's 445-469
       kcal tail. |
  | 10 | The lag over as many game days as about 3 sessions allow: one daily set, maintenance-sized meals | L, es and the
       exercise ring within 0.5 % of replay. Lag share at the last day read against the server-path oracles (Whybrow,
       King, E-MECHANIC) as readings, and against x29's 0.2500 as the before/after. |
  | walk | A moving fall: walk after a set | Billed at most Walking5kmh on the falling moving minutes (C17-5) |
  Grading frame (8-R): live against replay proves the billing in the live game; the study distance is a reading only.
  Name every attach gap inside a tail.

THE DESIGN, NAMED BEFORE THE RUN (the whole chain; x35_exercise_lib.SCHEDULE; at(d, h) = 24 d - 7 + h, world age 0 is
07:00 on day 0, the fixture's first day, #2890):
  The live body is the default fixture's admin: male, lean 65.6 kg, fat 14.4 kg, awake all day (sleep off, #2961).
  Meals: day 0 at 13:00 and 20:00, days 1-5 at 08:00, 13:00 and 20:00 (none after 17:30 day 5). A meal is
  maintenance-sized: a third of the tool's maintenance (NR_R.maint, read once off the live body at D0_13) plus a third
  of the latest bout's billed kcal (the record's exKcalDay rise from the bout's start to its rest's end, read at the
  stop; 0 before B0); whole Mixed650, Mixed217 and Unit50 portions, the miss carried.
  Bouts: 15:00 on days 0-5 (B0..B5): burpees (exercise.do burpees, each set asking for the window's remaining minutes)
  inside a 60-game-minute window at speed 1, a running set followed until the server's exercise flag clears (60 game
  minutes past the window at most); a refused set rests 5 game minutes; at most 8 sets. Then the rest at speed 1: 180
  game minutes after B0's set (row 9), 20 after the others, never past 5 game minutes before the next stop. Paired
  client/server stats.all reads at 0, 15, 30, 60, 120 and 180 minutes after each set (as far as the rest reaches).
  B5 (x353) is followed by the walk leg: 30 game minutes of player.walk 14 tiles back and forth.
  Drinking: to thirst, by the engine's own auto-drink (#2770) from a server-side canteen (Base.CanteenMilitaryFull)
  refilled to 0.9 L after every meal and bout and at 02:00; the replay's sips are the ring's fluids.autoDrop rows as the
  tool's autodrop kind (ruling T9-4). The replay's activity is the engine's own: the raw rate and the exercise flag off
  the ring inside tools/replay_live.py (ring_activity_events, ruling C17-3), the movement flag off the ring by the lib
  (ring_moving_events); no body.met read-back, no MET injected live.
  Sessions (each its own driver, each copying the previous <run>/server, reuse=True): x351 (fresh fixture, to 04:30
  day 2, age 45.5), x352 (to 04:30 day 4, age 93.5), x353 (to 17:30 day 5, age 130.5). The attach costs about 2 game
  hours; each session ends about 3.5 game hours before its successor's first stop and 11 or more after the last set,
  so no attach falls inside a bout's tail or after-burn.
THE GRADING (after the chain, by the committed testing/experiments/x35_grade.py into a staged folder
testing/artifacts/x35-grade-<date>/): every session's replay of live (the tool's diff and the script's), the billed MET
row by row against the replay, satiety.L, es, body.trail.c.ex and body.epoc within 0.5 %; row 9 on B0 (the module
docstring of x35_grade.py: BILLED_6_FROM_FIRST, EXE_END, IDLE_AFTER, EPOC, S_RISE, S_DECAY, FACTOR, the paired reads);
the walk leg on B5; row 10's series and the share at 15:00 day 5 against the oracle arm (0.1823 five days after its
first bout) and x29's at the same point (0.2045 on its own denominator, 0.1917 on days 1-4); the gaps; the sodium.
PREDICTIONS FOR THIS SESSION:
  B2 and B3: as B0 in x351 (6.0 on the flagged drains, 1.3 on the still drains after; tail rows 0); billed bout kcal
  about 376-660; the attach falls at about 04:30-06:30, 13.5 game hours after B1's set: no tail or after-burn inside
  it (the pool down to about e^-27 of itself). The replay of live as in x351. Sodium grade 0 every day.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x35_exercise_lib as L   # noqa: E402

PROFILE = "x35-exercise"
PREFIX = "x352"
PREV_PREFIX = 'x351'
ARTIFACT = "lag-2.json"
STAGE_ROOT = "release/x35-exercise/NutritionRevamp"
STAGED_AT = "c648c178"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 840.0
END_AGE = 93.5
BOUT_EX = "burpees"            # the heaviest exercise exercise.do queues (x291); every set now bills 6.0 whatever it is
WALK_BOUTS = ()
REST_ONE = {}
SESSION = ("Plan 11f Task 6r chain session 2 of 3: from the attach to 04:30 day 4, on the staged copy; one boot of " +
           PROFILE)
PRED = {
    "STOPS": {"this session's span": "every stop done, none missed, every eat landed, every refill read back"},
    "BOUTS": {"every bout": "at least one burpee set the server shows"},
    "BILLING": {"every bout": "flagged drains bill 6.0 (at most one off at each run's edges); still rows after the set "
                              "bill no exercise beyond one row; the pool fills"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "SODIUM": {"every chain day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
    "readings": {"bouts": ["B2", "B3"]},
}


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.chain_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python testing/experiments/x352_lag.py <the x351 run id or folder>")
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x352_lag.py", scenario,
              grade, prev_run=L.resolve_run(sys.argv[1]), prev_prefix=PREV_PREFIX, end_age=END_AGE, bout_ex=BOUT_EX,
              walk_bouts=WALK_BOUTS, rest_one=REST_ONE).run()
