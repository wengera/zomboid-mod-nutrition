"""x295-lag -- Plan 11f Task 6 session 4 of 5 of the lag chain (live): research row 10, the exercise lag over 7 game days.
One boot of profile x29-exercise (fixture default, admin -debug, Nutrition false, DayLength 1, sleep off) on the STAGED
copy of the tree (release/x29-exercise, staged fresh from HEAD before the boot; mod/ is never booted) plus
TKX_StudyFoods by its path. Build 42.21.0. The engine is testing/experiments/x29_exercise_lib.py (frozen with x291's
run). It copies x294's <run>/server and boots it again (reuse=True). Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5,
B3-1/B3-2).

USAGE: python testing/experiments/x295_lag.py <the x294 run id (testing/runs/<id>) or its folder>

THIS SESSION: from the attach (about 18:30 day 4, age 107.5) to 04:30 day 6 (age 141.5): D4_20, R5_0200, D5_08, D5_13, B5, D5_20, R6_0200 (a refill stop before the session's start is skipped; each meal and bout is followed by
a refill).
READINGS: bout B5; the meals' es; the drinking and the sodium guard per chain day; the hourly es.

RESEARCH ROW 10 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 10 | Exercise lag over days | S1318 (Whybrow, days 3-16), S1312 (King 2011), S1325 (Karl 2021), S1320/S1664 (24 wk) |
  `test_whybrow_compensation_over_days_3_to_16_is_about_30_percent`, `test_king_2011_at_steady_state...`,
  `test_karl_2021_*`, `test_e_mechanic_at_24_weeks` | 7 game days: daily `exercise.do` sets (the most exercise kcal the
  server bills), maintenance-sized meals, ring `satiety.L`, `body.trail.ex.*`, es | ~168 | 3 (fast, chained) | L
  trajectory, the lag's share of the exercise deficit | L and es within 0.5 % of replay-of-live; Whybrow (16 d) and
  24-week readings not run live (16 days ~ 6 sessions, 24 weeks impossible) - the 7-day share is a reading against the
  oracle's day-7 value |
THE TASK 6 AMENDMENTS (copied in substance): daily bouts at the heaviest billable work, maintenance-sized meals; graded
against the replay: satiety.L, es and the trail's exercise ring within 0.5 %; the study distance: the lag's share of the
exercise deficit by day 7 against the server-path oracles (test_replay_live_energy.py: Whybrow, King, E-MECHANIC), as
readings; Whybrow's days 3-16 and the 24-week figures are out of reach live (ruling 11f-4). A chain by server reuse,
with the departure flush at each end.
THE GATE (x291-20261011-045658, before this chain, on the same build): no candidate reached vigour. Squats billed 1.9-2.0
MET (the server's engine rate at most 2.06), burpees 2.0-3.0 (rate at most 2.78; FitnessHeavy's 9.0 target), melee
unmeasured (no zombie came within 2 tiles); the HeavyWork actions have no harness command. Burpees bill the most
exercise kcal, so they are this chain's bout. After the burpee set the billing held 1.9-2.0 MET for the hour after it
and 1.6 later (exercise kcal above the idle 1.3: the tail counts in L). The decay leg passed (S within 8.9e-16 of the
0.15 h half-life).

THE DESIGN, NAMED BEFORE THE RUN (the whole chain; x29_exercise_lib.SCHEDULE; at(d, h) = 24 d - 7 + h, world age 0 is
07:00 on day 0, the fixture's first day, #2890):
  The live body is the default fixture's admin: male, lean 65.6 kg, fat 14.4 kg, awake all day (sleep off, #2961), an
  idle day billing about 2,280 kcal (x28-grade).
  Meals: day 0 at 13:00 and 20:00, days 1-7 at 08:00, 13:00 and 20:00 (none after 15:30 day 7). A meal is
  maintenance-sized: a third of the tool's maintenance (NR_R.maint, read once off the live body at D0_13: about 2,089
  kcal; x28's maint meal) plus a third of the latest bout's billed kcal (the record's exKcalDay rise over the bout's
  window, read at the stop; 0 before B0); whole Mixed650, Mixed217 and Unit50 portions, the miss carried.
  Bouts: 15:00 on days 0-6 (B0..B6): burpees (exercise.do burpees, each set asking for the window's remaining minutes)
  inside a 60-game-minute window at speed 1; a set the server never shows within 3 game minutes (refused: the
  endurance moodle above ISFitnessUI.enduranceLevelThreshold 2) rests 5 game minutes; at most 8 sets.
  Drinking: to thirst, by the engine's own auto-drink (#2770) from a server-side canteen (Base.CanteenMilitaryFull)
  refilled to 0.9 L after every meal and bout and at 02:00; the replay's drinks are the ring's fluids.autoDrop rows
  (ruling T5R-1, with its one-minute landing offset). The replay's activity is read off the ring (x29_exercise_lib
  change 2: body.met, metMinDay and band2Day; no MET is injected live).
  Sessions (each its own driver, each copying the previous <run>/server, reuse=True): x292 (fresh fixture, to 16:30
  day 1, age 33.5), x293 (to 04:30 day 3, age 69.5), x294 (to 16:30 day 4, age 105.5), x295 (to 04:30 day 6, age
  141.5), x296 (to 15:30 day 7, age 176.5). The attach costs about 2 game hours at speed 1 (ruling S0-2's offline clamp
  drops about 9 minutes); each session ends 1.5-2 game hours before its successor's first stop.
THE GRADING (after the chain, by the committed testing/experiments/x29_grade.py lag into a staged folder
testing/artifacts/x29-lag-<date>/): each session's replay of live (the tool's diff, and the script's diff that skips a
row only for an eat, drink or setpath); satiety.L, es and body.trail.c.ex against the replay within 0.5 %; the bouts'
billed kcal; L and the lag's share lagged(L) / exercise kcal at each day's end and at 15:00 day 7; the server-path
oracle arm (Whybrow's lag_run on the 70 kg man: 0.2407 seven days after its first bout; 0.0414 at day 0's end) and
the pins as readings; the drinking and the sodium per chain day.
PREDICTIONS FOR THE CHAIN: every bout runs at least one burpee set the server shows; the billed MET during the sets
2.0-3.0, never 6.0, so satiety.S stays 0 and no acute term moves hunger; the bout window bills about 60-100 kcal and
the whole day's exercise kcal (the tail included) about 100-250; L and es within 0.5 % of the replay at every graded
row (the activity read off the ring reproduces the billing exactly; the residual is the replay's own: HUNGER within
0.002, es within 0.005); the lag's share seven days after B0 about 0.24 of the mean day's exercise kcal (the lag
kernel's form; the oracle arm reads 0.2407), higher against the bout window's kcal alone (the tail is in L); es
about 1.03-1.07 (x28's standing deficit of about 190 kcal a day on this body, plus the unfed tail); sodium: the
obligatory 8 mmol/d plus a little sweat, naPlasma near 140, the hyponatraemia grade 0 every day.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x29_exercise_lib as L   # noqa: E402

PROFILE = "x29-exercise"
PREFIX = "x295"
PREV_PREFIX = 'x294'
ARTIFACT = "lag-4.json"
STAGE_ROOT = "release/x29-exercise/NutritionRevamp"
STAGED_AT = "5244b4a"          # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
END_AGE = 141.5
BOUT_EX = "burpees"            # the heaviest billable exercise at the gate (x291: billed 2.0-3.0 MET)
SESSION = ("Plan 11f Task 6 lag chain session 4 of 5: from the attach to 04:30 day 6, on the staged copy; one boot of " + PROFILE)
PRED = {
    "STOPS": {"this session's span": "every stop done, none missed, every eat landed, every refill read back"},
    "BOUTS": {"every bout": "at least one burpee set the server shows; billed 2.0-3.0 MET, never 6.0; S stays 0"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "SODIUM": {"every chain day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
    "readings": {'bouts': ['B5']},
}


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.chain_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python testing/experiments/x295_lag.py <the x294 run id or folder>")
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x295_lag.py", scenario,
              grade, prev_run=L.resolve_run(sys.argv[1]), prev_prefix=PREV_PREFIX, end_age=END_AGE,
              bout_ex=BOUT_EX).run()
