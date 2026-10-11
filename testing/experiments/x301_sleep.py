"""x301-sleep -- Plan 11f Task 7 session 1 of 2 (live): day 0's maint meals, the rested night N0, request day 1, the
short night N1 and day 2 to its lunch, the first two window closes. One boot of profile x30-sleep (fixture default,
admin -debug, Nutrition false, DayLength 1, SleepAllowed and SleepNeeded TRUE) on the STAGED copy of the tree
(release/x30-sleep, staged fresh from HEAD before the boot; mod/ is never booted) plus TKX_StudyFoods by its path. Build
42.21.0. The engine is testing/experiments/x30_sleep_lib.py (frozen with x301's run). The fixture is restored (the
chain's first session). Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md
s5, B3-1/B3-2).

USAGE: python testing/experiments/x301_sleep.py

THIS SESSION: from the boot (about 11:00 day 0, age about 4.2) to 14:30 day 2 (age 55.5): R0_1030 (age 3.5) is before
the session's start and skipped; D0_13, R0_1630, D0_20, N0 (rested, 7.5 h booked, from 21:45 day 0), D1_08, R1_1030,
D1_13, R1_1630, D1_20, N1 (short, 5.5 h booked, from 00:15 day 2), D2_08, R2_1030, D2_13 (each meal and night followed
by its refill). The record is created at the first sight (about age 4.2), so its 24 h windows close at about 11:12
each day (#2986: the first window opens at the record's creation): C0 at about age 28.2 books N0, C1 at about 52.2
books N1.
PREDICTIONS (graded in `verdicts`): SLEEP_ON the mod reads the server's sleep option as enabled (sleepDisabled false);
NIGHTS N0 and N1 each stop at their booked target, inside one window, booked within 0.25 h of 7.5 and 5.5, booked over
held about 0.80-0.90 (#2840: about 15 % of held updates run awake), the world about 20x its waking rate while held
(#2956: about 0.53 game h per wall s); CLOSES C0 books about 7.5 h and leaves the debt 0, C1 books about 5.5 h and
leaves about 2.0 h (1.75-2.0), each equal to the kernel's own booking and the replay's within 1e-6; EXE no exe true row
(sedentary); STOPS every meal and night of this session's span done (none missed), every eat landed, every refill
read back; REPLAY the session's replay of live (sleep_allowed true, the autoDrop drinks, the ring's sleep events) ok
under HUNGER 0.002, es 0.005, L 0.5 %; SODIUM grade 0 on every chain day of the ring; H1, RING, F, Z the engine's.
READINGS: maint_kcal (the live body at D0_13; predicted 2,089.3, fm 14.4, lm 65.6); each meal's es read, target,
portions and carry; per night its placement, held span, booked sleep and polls; per close the booked sleep and the
debt; the live kcal per chain day (day 0 about 1,393, day 1 about 2,009); the drinking and the sodium guard per day.

RESEARCH ROW 11 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 11 | Sleep debt | S1284 (Zhu 2019), S1565 (Fenton 2021), S1564, S1567 (Markwald 2013) |
  `test_one_short_night_raises_hunger_at_the_request_by_the_pooled_size` (11.7 mm, debt 2.0),
  `..._next_day_intake_within_the_pooled_band` (1.18), `test_recovery_sleep_reverses_the_factor_partially` (debt 1.0,
  1.09), `test_a_short_night_across_two_windows_splits_its_debt` (1.5/0.5, 1.135) | profile with both sleep keys;
  fixture `default` (one player, so the fast-forward runs); nights by `player.sleep.hold`: 7.5 h rested, 5.5 h short in
  phase with the window close, 9.5 h recovery; request-level meals each day | ~96 | 2 (fast days, fast-forward nights)
  | `acute.sleptH`, `debtH` at each close, written HUNGER at the meals, factor = written/replay-without-sleep | factor
  = 1 + 0.18 x clamp(debtH/2) within 1 % (`NR_Kernel_Satiety.lua:187-196`); the booked debt differs from the held night
  because ~15 % of held minutes run awake (#2840) - the replay uses the booked minutes; replay vs study as pinned |
THE TASK 7 AMENDMENTS (task-7-amendments.md, copied in substance): the profile sets SleepAllowed and SleepNeeded true;
the replay takes --sleep-allowed true (NUT.readSleepOptions, NR_Server_Nutrients.lua:127-143); player.sleep.hold
re-asserts sleep, about 85 % of updates run asleep (#2840, #3076); with the only player asleep the world fast-forwards
about 20x (#2956); the hold is cancelled at a target; the debt books once per 24 h window at its close (#3638), the
window's phase the record's creation, so the driver reads the acute fields and places the short night inside one
window; meals request-level each day (s3.7 form 1); grading: acute.sleptH and debtH at each close (the replay uses the
booked asleep minutes, not the held ones), the written HUNGER at the meals, the factor written / (replay with no sleep
factor) within 1 % of 1 + 0.18 x clamp(debtH / 2) (constants read off NR_Kernel_Satiety.lua), live against replay within
the tolerances; study distances as readings; the energy ladder and the eating reads ride along; the scenario is
sedentary, the ring's exe a guard (must stay false).

THE DESIGN, NAMED BEFORE THE RUN (the whole chain; x30_sleep_lib.SCHEDULE; at(d, h) = 24 d - 7 + h, world age 0 is
07:00 on day 0, #2890):
  The live body is the default fixture's admin: male, lean 65.6 kg, fat 14.4 kg (F-T4-3).
  Day 0 (from the boot, about 11:00): maint meals at 13:00 and 20:00 (a third of the tool's maintenance, read once off
  the live body at D0_13: about 2,089 kcal). Days 1-4: request meals at 08:00, 13:00 and 20:00 (day 4 to 13:00):
  650/0.25 x min(0.69, hungerTarget(0.75, es) x circadian(hour)), es read at the stop, on the mod's own kernels
  (NR_R.requestKcal); whole Mixed650, Mixed217 and Unit50 portions, the miss carried. THE MEAL IS NOT SIZED BY THE SLEEP
  FACTOR (form 1 sizes by es and the hour): the factor is read in the written HUNGER, and the next-day intake ratio of
  the oracle is read through its own mapping (650 x written / 0.25) as a reading.
  Nights (booked targets; the lib's change 3): N0 rested 7.5 h from 21:45 day 0; N1 short 5.5 h from 00:15 day 2; N2
  recovery 9.5 h from 20:30 day 2; N3 rested 7.5 h from 21:45 day 3. A night is held at speed 1 by player.sleep.hold and
  cancelled when the record's booked window sleep (acute.winSleptH) since the night's start, plus the booking rate
  times the poll's round trip, reaches the target; then player.sleep false. THE NIGHT'S LENGTH IS ITS BOOKED SLEEP, not
  its held span (about 15 % of held minutes run awake, #2840; held 7.5 h would book about 6.4 h and give the rested
  baseline a 1.1 h debt); the held span is logged. Each night lies inside one window (the closes at about 11:12), so
  "in phase with the window close" is read as: the night is not split by a close, and the close after it books it
  whole. The 24 h windows are the record's, from its creation at the first sight: the debt steps at about 11:12, not at
  waking, so each 08:00 breakfast reads the previous window's debt (a known limitation, NR_Server_Writer.lua:22).
  Drinking: to thirst by the engine's auto-drink from a server-side canteen (ruling T5R-1), refilled to 0.9 L after
  every meal and night and at 10:30 and 16:30 (none inside a night); no water food is eaten.
  Sessions: x301 (fresh fixture, to 14:30 day 2, age 55.5), x302 (to 13:30 day 4, age 102.5), chained by server reuse.
  The replay's sleep events are read off the ring's acute.sleptH (the lib's change 4); its activity off the ring's rate
  and exe (the tool, 3daaca9).
THE GRADING (after the chain, by the committed analysis script testing/experiments/x30_grade.py, into a staged
artifact folder testing/artifacts/x30-grade-<date>/): each session's replay of live (the tool at HEAD, sleep_allowed
true) under HUNGER 0.002, es 0.005, L 0.5 %, acute.debtH 1e-6; per close the booked sleep and the debt, live against the
kernel and the replay; the factor live HUNGER / no-sleep-factor replay HUNGER (the same replay with
K.satiety.SLEEP_MAX 0) against 1 + SLEEP_MAX x clamp(debtH / SLEEP_DEBT_FULL_H) on every graded uncapped ring row and
at each meal's read, 1 %; the replay's own factor; the study distances as readings.
PREDICTIONS FOR THE CHAIN (an offline replay arm: a fresh 80 kg male record at age 4.2, these meals, the booked
nights): es at the meals 1.01-1.07; request days 1-3 eat about 2,009, 1,993 and 1,965 kcal; the debt 0 after C0, 2.0
after C1 (the factor 1.18 at D2_13, D2_20 and D3_08), 1.0 after C2 (1.09 at D3_13, D3_20, D4_08), 1.0 after C3 (a night
of exactly the need repays nothing; N3's small overshoot repays half of itself); live the booked targets give each debt
within about 0.15 h of these; written HUNGER at the meal reads about 0.25-0.36 (uncapped); the factor live within 1 % of
the formula at every graded uncapped row, the replay's own within 1e-6. Sodium: none eaten, about 8 mmol/d basal,
grade 0. Drinking about 2-3 L/d.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x30_sleep_lib as L   # noqa: E402

PROFILE = "x30-sleep"
PREFIX = "x301"
PREV_PREFIX = None
ARTIFACT = "sleep-1.json"
STAGE_ROOT = "release/x30-sleep/NutritionRevamp"
STAGED_AT = "35c3049e"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
END_AGE = 55.5
SESSION = ("Plan 11f Task 7 session 1 of 2: day 0's maint meals, the rested night N0, request day 1, the short night N1 "
           "and day 2 to its lunch, on the staged copy; one boot of " + PROFILE)
PRED = {
    "SLEEP_ON": {"NutritionRevamp.server.nutrients.sleepDisabled": False},
    "NIGHTS": {"N0": "booked 7.5 +/- 0.25 h at its target, inside one window", "N1": "booked 5.5 +/- 0.25 h",
               "booked_over_held": "0.80-0.90", "game_h_per_wall_s": "about 0.53 (20x the waking 1.6 game min/s)"},
    "CLOSES": {"C0": "booked ~7.5, debt 0", "C1": "booked ~5.5, debt 1.75-2.0",
               "each": "the kernel's booking and the replay's debt within 1e-6"},
    "EXE": {"exe true rows": 0},
    "STOPS": {"this session's span": "every meal and night done, none missed, every eat landed, every refill read back"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %), sleep events off the ring"},
    "SODIUM": {"every chain day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
    "readings": {"maint_kcal": 2089.3, "day0_kcal": 1393, "day1_kcal": 2009, "es_meals": "1.01-1.07",
                 "factor_D2_13": 1.18},
}


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.session_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x301_sleep.py", scenario,
              grade, end_age=END_AGE).run()
