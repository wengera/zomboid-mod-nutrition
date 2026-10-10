"""x284-steady -- Plan 11f Task 5r session 4 of 4 (live): day 4's dinner and request-level day 5, row 7's last day. One boot of profile x28-steady (fixture
default, admin -debug, Nutrition false, DayLength 1, sleep off) on the STAGED copy of the tree (release/x28-steady,
staged fresh from HEAD before the boot; mod/ is never booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine
is testing/experiments/x28_steady_lib.py (frozen with x281's run). It copies x283's <run>/server and boots it again (reuse=True). Written BEFORE the boot with every
prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

USAGE: python testing/experiments/x284_steady.py <the x283 run id (testing/runs/<id>) or its folder>

THIS SESSION: from the attach (about 18:30 day 4, age 107.5) to 00:18 day 6 (age 137.3): D4_20, R4_2300, R5_0200, R5_0500, D5_08, R5_1030, D5_13, R5_1630, D5_20, R5_2300 (a refill before the session's start is skipped); the ring covers every hour of day 5, 01:00 to 24:00 (ages 114 to 137).
PREDICTIONS (graded in `verdicts`): STOPS every meal of this session's span done (none missed), every eat landed,
every refill read back; REPLAY the session's replay of live (sleep_allowed false, the autoDrop drinks) ok under
HUNGER 0.002, es 0.005, L 0.5 %, the auto-drink detector finding none beyond the autoDrop drinks; SODIUM grade 0 on
every chain day of the ring; H1, RING, F, Z the engine's. READINGS: day 4's and day 5's live kcal (predicted about 2,032 and 2,033, 0.973 x maint); es at every hour of day 5 (predicted 1.0447-1.0457: outside 1.00 +/- 0.03, C-5) and its replay twin (within 0.005); the drinking and the sodium guard per chain day (grade 0).

RESEARCH ROW 7 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 7 | Steady eater's balance | ruling C-8 (no study row) | `test_a_steady_eater_reads_balance_at_every_hour` (es
  1.0004-1.0005), `test_a_request_level_eater_eats_maintenance` (1.0075/0.994/0.9978) | shares row 6's chain: bob eats
  one maintenance day then request-level days 2-5 | ~120 | 0 extra (rides row 6, +1 session for days 4-5) | es each
  hour of day 5, intake per day | es within 1.00 +/- 0.03 every hour and within 0.005 of replay; intake within +/-3 % of
  maintenance |
THE TASK 5r BRIEF (task-5r-brief.md, copied): row 7 went unmeasured in Task 5 (the chain's admin died of the sodium
drain, F-T5-1, on chain day 4); Task 5b and its three fix rounds fixed the drain (basal sodium of 8 mmol/d with water
following sodium; thirst counts swallowed water; a bounded volume defence that relaxes the hypotonic cap; deficit-driven
sweat sodium; a dead record that stops stepping). The scenario: fresh fixture, admin, Nutrition = false, DayLength 1,
speed 5 (ruling S0-1), sleep disabled as in the x27 profile; one warm-up day eating maintenance, then request-level
days 2-5 sized by research s3.7 form 1, logging the es at each meal; the sessions chained by server reuse, each 15
minutes of wall time or less, with the departure flush at each end; TKX_StudyFoods (no sodium: the fixed build should
lose only the obligatory 8 mmol/d); fluids.na, naPlasma and sweat6h on the ring as a guard, with the hyponatraemia
grade. Grading: es within 1.00 +/- 0.03 at every hour of the last day, and within 0.005 of the replay; intake within
+/-3 % of maintenance on each request-level day; Task 5's projection read es at about 1.045 on this body (the request
mapping is calibrated to the 70 kg man): if live reproduces it the +/-0.03 clause fails as predicted, a reading under
candidate C-5, not a mod defect; the live-against-replay clause stays the gate. Drinking per day reported against the
drinking-volume oracle's 2.0-3.0 L/d as a reading on the live body; sodium and plasma per day, which must stay at
grade 0.

THE DESIGN, NAMED BEFORE THE RUN (the whole chain; x28_steady_lib.SCHEDULE; at(d, h) = 24 d - 7 + h, world age 0 is
07:00 on day 0, the fixture's first day, #2890):
  The live body is the default fixture's admin: male, lean 65.6 kg, fat 14.4 kg (F-T4-3), awake all day (sleep off:
  the record's sleep state frozen, #2961), so an idle day bills about 2,285 kcal (F-T5-3, 1.34 x REE), where the
  oracles' 70 kg man sleeps 23:00-07:00.
  Day 0 (from the boot, about 11:00): maint meals at 13:00 and 20:00 (x271's day -1: the fresh record's trailing
  window starts at its first sight). Day 1, the warm-up day: maint meals at 08:00, 13:00 and 20:00. A maint meal is a
  third of the tool's maintenance (NR_R.maint: REE(lm) + (COMPENDIUM.Default - MET_REST) x (fm + lm) x 16 h), read once
  off the live body at the first maint meal: about 2,089 kcal.
  Days 2-5: request meals at 08:00, 13:00 and 20:00: 650/0.25 x min(0.69, hungerTarget(0.75, es) x circadian(hour)),
  es the record's body.energyState read at the stop and hour the stop's (world age + 7) mod 24, on the mod's own
  kernels (NR_R.requestKcal on the lupa host). Whole Mixed650, Mixed217 and Unit50 portions (water 300 g and fibre 6 g
  per 650 kcal), the fewest eats within 25 kcal of the target plus the carry; the miss carried to the next meal.
  Drinking: to thirst, by the engine's own auto-drink (#2770; autodrink.set true at S) from a server-side canteen
  (Base.CanteenMilitaryFull, x151t's D, #2965) refilled to 0.9 L after every meal and at 02:00, 05:00, 10:30, 16:30
  and 23:00; no water food is eaten. (Task 5's amendments preferred no auto-drink; this re-run drinks to thirst
  because the brief's drinking reading is the drinking-volume oracle's, which drinks to thirst; the replay's drinks
  are the ring's fluids.autoDrop rows, the lib's change 4, and the tool's detector runs as a check.)
  Sessions (each its own driver): x281 (fresh fixture, to 16:30 day 1, age 33.5), x282 (to 04:30 day 3, age 69.5),
  x283 (to 16:30 day 4, age 105.5), x284 (to 00:18 day 6, age 137.3). Each chained session copies the previous
  <run>/server and boots it (reuse=True); the attach costs about 2 game hours at speed 1 (x272, x273), of which the
  mod's 60-minute offline clamp drops about 9 minutes (ruling S0-2); each session ends 1-1.5 game hours of margin
  before its successor's first meal.
THE GRADING (after the chain, by the committed analysis script testing/experiments/x28_grade.py, into a staged
artifact folder testing/artifacts/x28-grade-<date>/): each session's replay of live (the tool at HEAD, sleep_allowed
false, the autoDrop drinks) under HUNGER 0.002, es 0.005, L 0.5 %; row 7 on day 5 (es at 01:00 .. 24:00, live ring
against x284's replay of live); the intake per chain day over maint; the drinking, sodium and plasma per chain day.
PREDICTIONS FOR THE CHAIN (an offline replay arm on x271's start record, the same body, these meals, no water):
maint 2,089.3 kcal; request days 2-5 eat about 2,027, 2,030, 2,032 and 2,033 kcal (0.970, 0.972, 0.973, 0.973 x maint:
inside +/-3 %, day 2 at the edge, so whole-portion rounding may take it out); es on day 5 1.0447-1.0457 at every hour:
OUTSIDE row 7's 1.00 +/- 0.03, as pre-registered (C-5: the request mapping balances the 70 kg man's day at es 1, the
awake 80 kg body bills about 2,285); es live within 0.005 of the replay. Sodium: no sodium eaten, the obligatory
8 mmol/d only (fluids.na about -8 per day, about -45 mmol by 24:00 day 5); water follows sodium, so naPlasma stays near
140 (138-142) and the hyponatraemia grade 0 every day; sweat6h 0 (idle). Drinking to thirst: about 2.4-3.0 L/d (the
oracle's man at the band's top, about 3.0 L/d with 0.7 L/d of food water awake 16 h; here about 0.95 L/d of food water
and awake 24 h), the canteen side and the autoDrop side within about 10 % of each other.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x28_steady_lib as L   # noqa: E402

PROFILE = "x28-steady"
PREFIX = "x284"
PREV_PREFIX = 'x283'
ARTIFACT = "steady-4.json"
STAGE_ROOT = "release/x28-steady/NutritionRevamp"
STAGED_AT = "6f9145d"          # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
END_AGE = 137.3
SESSION = ("Plan 11f Task 5r session 4 of 4: day 4's dinner and request-level day 5, row 7's last day, on the staged copy; one boot of " + PROFILE)
PRED = {
    "STOPS": {"this session's span": "every meal done, none missed, every eat landed, every refill read back"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %), no auto-drink beyond the autoDrop drinks"},
    "SODIUM": {"every chain day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
    "readings": {"day4_kcal": 2032, "day5_kcal": 2033, "day5_es": [1.0447, 1.0457], "grade": 0},
}


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.session_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python testing/experiments/x284_steady.py <the x283 run id or folder>")
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x284_steady.py", scenario,
              grade, prev_run=L.resolve_run(sys.argv[1]), prev_prefix=PREV_PREFIX, end_age=END_AGE).run()
