"""x274-day5 -- Plan 11f Task 5 session 4 of 5 (live): request-level day 5 (row 7's graded day). One boot of profile x27-energy (fixture
default, admin -debug, Nutrition false, DayLength 1, sleep off) on the STAGED copy of the tree (release/x27-energy,
staged fresh from HEAD before the boot; mod/ is never booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine
is testing/experiments/x27_energy_lib.py (frozen with x271's run). It copies x273's <run>/server and boots it again (reuse=True). Written BEFORE the boot with every prediction in
it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

USAGE: python testing/experiments/x274_day5.py <the x273 run id (testing/runs/<id>) or its folder>

THIS SESSION: from the attach (about 01:15 day 5) to 04:00 day 6 (age 164.0): D5_08, W5_1030, D5_13, W5_1630, D5_20, W5_2330.
PREDICTIONS (graded in `verdicts`): STOPS every stop of this session's span done (none missed), every eat
landed; REPLAY the session's replay of live (sleep_allowed false) ok under HUNGER 0.002, es 0.005, L 0.5 %, the
auto-drink detector finding none; H1, RING, F, Z the engine's. READINGS: day 5's live kcal (predicted about 2,030, 0.972 x maint); es at every hour of day 5 (predicted 1.042-1.045, outside row 7's 1.00 +/- 0.03).

RESEARCH ROWS 6-8 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 6 | 36 h fast, next-day intake | S1613 (Johnstone 2002), S1614 (Clayton 2016), S1255 (deficit pin) |
  `test_the_36_h_fast_ratios_sit_within_their_studies` (1.1x), `test_the_36_h_fast_intake_ratios_are_pinned` (1.304,
  0.986), `test_the_fasts_glycogen_is_logged_and_pinned` (es 1.0/1.087/1.13; eb24 -1/-1301/-1950) | warm-up day + day 0
  maintenance; fast 20:00 day 0 -> 08:00 day 2; days 2-3 request-level meals by s3.7 form 1; the fed arm is bob in
  parallel (fixture `two`) or the replay | ~108 | 2 (fast, chained) | es and eb24h at 12/24/36 h, kcal per day per arm |
  es within 0.005 of replay-of-live; live day-2/day-3 ratios within 2 % of replay; replay vs 1.20 / 1.0 at 1.1x (the
  oracle's 70 kg man vs the live body: named) |
  | 7 | Steady eater's balance | ruling C-8 (no study row) | `test_a_steady_eater_reads_balance_at_every_hour` (es
  1.0004-1.0005), `test_a_request_level_eater_eats_maintenance` (1.0075/0.994/0.9978) | shares row 6's chain: bob eats
  one maintenance day then request-level days 2-5 | ~120 | 0 extra (rides row 6, +1 session for days 4-5) | es each
  hour of day 5, intake per day | es within 1.00 +/- 0.03 every hour and within 0.005 of replay; intake within +/-3 % of
  maintenance |
  | 8 | Six meals vs three | S1608 (Ohkawara 2013), S1607 (Raynor 2015) | `test_six_meals_against_three_is_pinned_inside_
  the_band` (0.969, state held), `..._with_the_energy_state_live_is_pinned` (0.994) | warm-up day; from 08:00 admin eats
  three `Mixed667`, bob six `Mixed333` every 150 min (fixture `two`), same mass | ~48 | 1 (fast) | 24 h mean written
  HUNGER per arm | ratio within 1 % of replay-of-live and within [0.9, 1.3]; S1608's direction stays a named
  non-reproduction (#3622) |
THE AMENDMENTS (task-5-amendments.md, copied): row 6: a warm-up day and a maintenance day 0, then a fast from 20:00 on
day 0 to 08:00 on day 2, then request-level days 2 and 3; eat by research s3.7 form 1, the oracle's mapping, and log the
es read at each meal; the fed arm is the replay arm of the same live body with the fast's events replaced by
maintenance meals (ruling 11f-3); grading: the live day-2 and day-3 ratios within 2 % of the replay, and es within
0.005; the replay's ratio is a reading against S1613's 1.20 and S1614's 1.0, with its distance named; the live body
differs from the 70 kg man. Row 7: rides row 6's chain (one more session for days 4-5 if needed): request-level days at
maintenance; es within 1.00 +/- 0.03 at every hour, and within 0.005 of the replay; intake within +/-3 % of maintenance
per day. Row 8: three Mixed667 from 08:00, against six Mixed333 every 150 min, on sequential days or one arm as a
replay arm; the 24 h mean written-HUNGER ratio within 1 % of the replay, and within [0.9, 1.3].

THE DESIGN, NAMED BEFORE THE RUN (the whole chain; x27_energy_lib.SCHEDULE; world age 0 is 07:00, #2890):
  The live body is the default fixture's admin: male, lean 65.6 kg, fat 14.4 kg (F-T4-3), awake all day (sleep off:
  the record's sleep state frozen, #2961), so an idle day bills about 2,258 kcal (Default class all 24 h; x261's
  reading 1.344 x REE), where the oracles' 70 kg man sleeps 23:00-07:00.
  Day -1 (the fixture's first day, from the session's start, about 11:00): the warm-up, maint meals at 13:00 and 20:00
  (the fresh record's empty trailing window starts at its first sight; the oracle's three warm days are not run).
  Day 0: maint meals at 08:00, 13:00 and 20:00. A maint meal is a third of the tool's maintenance (NR_R.maint, the
  oracles' definition: REE(lm) + (COMPENDIUM.Default - MET_REST) x (fm + lm) x 16 h, a 16 h waking day), read once
  off the live body at the first maint meal: about 2,089 kcal, about 170 kcal under the awake body's billed day.
  Day 1: the fast (20:00 day 0 to 08:00 day 2, 36 h); water stops only.
  Days 2-5: request meals at 08:00, 13:00 and 20:00: 650/0.25 x min(0.69, hungerTarget(0.75, es) x circadian(hour)),
  es the record's body.energyState read at the stop and hour the stop's (world age + 7) mod 24, on the mod's own
  kernels (NR_R.requestKcal on the lupa host, the line the tool's request meal calls).
  Day 6: six Mixed333 every 150 min from 08:00 (row 8's live arm); the three-Mixed667 arm is a replay arm of the same
  session (ruling 11f-3: one arm live, one replayed), the six eats replaced by Mixed667 at 08:00, 13:00 and 18:00.
  Portions: each meal is whole Mixed650, Mixed217 and Unit50 portions (one per-kcal composition, water 300 g and fibre
  6 g per 650 kcal), the fewest eats within 25 kcal of the target plus the carry; the miss is carried to the next meal,
  so a day's intake stays within about 25 kcal of its targets. Eats run at speed 1, one after another (a meal spreads
  over some game minutes; each eat lands on its own ring row and the replay takes it there).
  Water: 900 g as food (TKX.Water600 and TKX.Water300) at 10:30, 16:30 and 23:30 on days -1 to 5 (through the fast) and
  at 06:00 on day 6, none inside row 8's window. No fluid container is ever spawned, so the engine's auto-drink (#2770;
  the flag does not hold, #2941) has nothing to drink; the replay runs the detector as a check only.
  Sessions: x271 (to 08:00 day 1, the fast's 12 h), x272 (to 02:00 day 3), x273 (to 23:00 day 4), x274 (to 04:00 day 6),
  x275 (row 8, to 08:18 day 7). Each chained session copies the previous <run>/server and boots it (reuse=True); the
  attach runs about 73 game minutes at speed 1, of which the mod's 60-minute offline clamp drops about 9 (ruling S0-2),
  then W reads the start record at the store's next save; the stops of its span are run from there.
THE GRADING (after the chain, by the committed analysis script testing/experiments/x27_grade.py, into a staged
artifact folder): each session's replay of live (the tool at HEAD, sleep_allowed false) under HUNGER 0.002, es 0.005,
L 0.5 %; the fast and fed arms as replay arms from x271's start record on a synthetic one-minute clock (the live eats
before the fast at their ring ages, the water stops as live, the request meals at the live read ages; the fed arm adds
three maint meals on day 1); the live and replay ratios on days 2 and 3 over the fed arm's intake (within 2 %); row 7
on day 5; row 8 on x275's ring.
PREDICTIONS FOR THE CHAIN (an offline replay arm on x261's start record, the same body, the schedule above with exact
kcal): maint 2,089.3 kcal; es at the fast's 12, 24 and 36 h 1.034, 1.259 and 1.374 (eb24 -193, -1585, -2278); the
energy ladder's level 1 at about 14.8 h and level 2 at about 22.5 h after 20:00 day 0, level 3 not reached (the 70 kg
man asleep: about 17 h and 25.6 h, ruling 2c-5); intake day 2 about 2,440, day 3 about 1,958 against the fed arm's
2,028 and 2,031: r2 about 1.203 (S1613 1.20: 1.003x), r3 about 0.964 (S1614 1.0: 0.964x); days 4 and 5 about 2,041 and
2,030 (0.977 and 0.972 x maint, inside +/-3 %), es on day 5 1.042-1.045 at every hour: OUTSIDE row 7's 1.00 +/- 0.03 (the
request mapping balances the 70 kg man's 1,949 kcal day at es 1; the awake 80 kg body bills about 2,258, so its
request-level eater settles at a trailing deficit, es about 1.045); row 8's six over three about 0.981, inside
[0.9, 1.3] (the 70 kg man on the server path: 0.981 live, 0.969 held)."

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x27_energy_lib as L   # noqa: E402

PROFILE = "x27-energy"
PREFIX = "x274"
PREV_PREFIX = 'x273'
ARTIFACT = "energy-4.json"
STAGE_ROOT = "release/x27-energy/NutritionRevamp"
STAGED_AT = "983ebd6"          # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
END_AGE = 164.0
SESSION = ("Plan 11f Task 5 session 4 of 5: request-level day 5 (row 7's graded day), on the staged copy; one boot of " + PROFILE)
PRED = {
    "STOPS": {"this session's span": "every stop done, none missed, every eat landed"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %), auto-drinks detected 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
    "readings": {"day5_kcal": 2030, "day5_es": [1.042, 1.045]},
}


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.session_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python testing/experiments/x274_day5.py <the x273 run id or folder>")
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x274_day5.py", scenario,
              grade, prev_run=L.resolve_run(sys.argv[1]), prev_prefix=PREV_PREFIX, end_age=END_AGE).run()
