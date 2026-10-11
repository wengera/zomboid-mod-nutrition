"""x321-nicotine -- Plan 11f Task 8 session 1 of 3 (live): the Smoker trait, the smoke gate, day 0's maint meals and
request day 1, the withdrawal's rise from the gate smoke. One boot of profile x32-nicotine (fixture default, admin
-debug, Nutrition false, DayLength 1, sleep off) on the STAGED copy of the tree (release/x32-nicotine, staged fresh
from HEAD before the boot; mod/ is never booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine is
testing/experiments/x32_nicotine_lib.py (frozen with x321's run). The fixture is restored (the chain's first session).
Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

USAGE: python testing/experiments/x321_nicotine.py

THE x32 CHAIN (ruling T8-1): x311 (x31_nicotine_lib) sent trait.set the display name Smoker, which does not resolve
(no CharacterTrait.Smoker), so its gate smoke was a non-smoker's and the gate was falsified (F-T8-1). This chain sends
the static field name SMOKER (CharacterTrait.<clinit> @661-@667 L85) and phase S stops the session (no H, W or X)
when the trait list read back lacks Smoker (x32_nicotine_lib change b). Otherwise the design, the predictions and
the calendar are x311-x313's, re-run from a fresh fixture.

THIS SESSION: from the boot (about 11:12 day 0, age about 4.2) to 21:30 day 1 (age 38.5). Phase S adds the Smoker trait
on the server and pushes it (lib change 2). THE GATE (lib change 4), first in X at speed 1: a lighter and one
Base.CigaretteSingle spawned, the server's NICOTINE_WITHDRAWAL seeded at 0.2 by stats.setany (a new smoker's stat reads
0, so a smoke from 0 would show nothing), two game minutes, then the smoke by eat.action. IF THE GATE FAILS the scenario
stops (a named budget stop) and the chain stops: the task is reported, not re-run. Then, in age order, D0_13 (age 6.0),
R0_1630, D0_20, D1_08, R1_1030, D1_13, R1_1630, D1_20 (R0_1030 at age 3.5 lies before the session's start and is
skipped), each meal followed by its refill; then speed 5 to age 38.5.
PREDICTIONS (graded in `verdicts`): SLEEP_OFF the mod reads the server's sleep option as disabled (sleepDisabled true);
SMOKER the trait list read after trait.set holds Smoker; GATE and SMOKES the gate smoke is seen within 60 s: the
intake's eats counter rises by 1, the seeded stat falls from 0.2 to 0 (0.51 x f with f = 1, #3632, so the fall is
min(0.2, 0.51) = 0.2 within 1e-4), the landed counter does not rise (a cigarette has no table entry: the eat lands no
vector, as on the replay host), and the timer reads 0 after (the remainder over 0.51); RISE after the gate smoke the
stat stays 0 for about 5.56 game hours (the first ring row above 0 between 4.5 and 7.0 h after the smoke) and then
rises at about 0.01125 a game hour (least squares over the rows between 0 and the cap: 0.0100 to 0.0125), the
arithmetic of #3630 with #2922 at DayLength 1 (the multiplier sums to 120 x 15 = 1800 a game hour: the timer gains 0.18
a game hour, the stat 0.00005 / 8 x 1800), four times #3636's 12.7 game hours to the cap on the 60-minute day: the cap
is predicted about 50.9 game hours after the smoke (about age 55, in x322), not in this session; EXE no exe true row and
no asleep row; STOPS every meal of this session's span done (none missed), every eat landed, every refill read back;
REPLAY the session's replay of live (sleep_allowed false, the autoDrop drinks, the stat fed from the ring, the seed and
smoke markers) ok under HUNGER 0.002, es 0.005, L 0.5 %; SODIUM grade 0 on every chain day of the ring; H1, RING, F, Z
the engine's.
READINGS: the timer before the gate (unknown: a reading); the stat at the session's end (predicted about 0.32);
maint_kcal (the live body at D0_13; about 2,089 as x301); each meal's es read, target and portions.

RESEARCH ROW 12 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 12 | Nicotine withdrawal | S1576 (Stamford 1986), S1577 (Hall 1989) | `test_a_quitting_smokers_next_day_intake_sits_
  in_s1576s_band`, `test_the_nicotine_replay_is_pinned` (1.1304 next day; 48-day mean 1.1135); `test_writer_shape.py:
  1162-1181` | `trait.set admin Smoker add` + push; lighter + `Base.CigaretteSingle` by `eat.action`; ring
  NICOTINE_WITHDRAWAL, `satiety.nicH`, HUNGER for ~13 game h; smoke again (anchor reset); `lua.setpath ...satiety.nicH`
  nil (T2-F: no rise until a smoke) and to age - 91 x 24 (fade at half) | ~30 | 1 (fast) | w, nicH, factor =
  written/replay-without-nicotine; next-day request-level intake | factor = 1 + 0.1313 x clamp(w/0.51) x clamp(1 - d/182)
  within 1 % (`NR_Kernel_Satiety.lua:215-229`); next-day ratio within 2 % of 1.1304; the 48-day mean and week 26 are
  not runnable live (48 and 182 days) - only via the anchor edit |
THE TASK 8 AMENDMENTS (task-8-amendments.md, copied in substance): the factor multiplies hunger by
1 + NIC_MAX x clamp(w / 0.51) x clamp(1 - d / 182), NIC_MAX 0.1313 (constants read off NR_Kernel_Satiety.lua); w is the
server's NICOTINE_WITHDRAWAL, rising only for a Smoker (#3630, #3631), capped at 0.51 (#3632, #3633), about 12.7 game h
after a smoke at the 60-minute day (#3636; how DayLength 1 scales it is read here); d the days since the mod's anchor
satiety.nicH, reset when the stat falls (a smoke) or reads 0; a first-seen or healed anchor in withdrawal starts fully
faded (T2-F); a fall missed across a reconnect leaves the anchor unreset (T2-C); the server reads w through
getStats():get (#3637, never measured live: this task settles it); NICOTINE_WITHDRAWAL is in ALLOWED_FEED. Row 12: gate
first (Smoker, a smoke with a lighter through eat.action, the server's stat rising after; a smoke that cannot complete
stops the task); the withdrawal rise (factor within 1 % of the formula at every minute, live against replay); a second
smoke (anchor reset, w falls by 0.51 x f); T2-F (nicH nil while w > 0: the factor reads 1 until the next smoke); the
fade (nicH = age - 91 x 24: the factor reads 1 + NIC_MAX x clamp(w/0.51) x 0.5 within 1 %); a request-level next day in
withdrawal (s3.7 form 1), its ratio read against S1576's next-day pin 1.1304 as a reading.

THE DESIGN, NAMED BEFORE THE RUN (the whole chain; x32_nicotine_lib.SCHEDULE; at(d, h) = 24 d - 7 + h, world age 0 is
07:00 on day 0, #2890):
  The live body is the default fixture's admin: male, lean 65.6 kg, fat 14.4 kg (F-T4-3), made a Smoker at the boot.
  The gate smoke at about age 4.3 starts the rise: 0 to about age 9.9, the cap about age 55.2 (12:15 day 2).
  Day 0: maint meals at 13:00 and 20:00 (a third of the tool's maintenance, read once off the live body at D0_13).
  Days 1-4: request meals at 08:00, 13:00 and 20:00 (day 4 to 13:00): 650/0.25 x min(0.69, hungerTarget(0.75, es) x
  circadian(hour)), es read at the stop (NR_R.requestKcal); whole Mixed650, Mixed217 and Unit50 portions, the miss
  carried. THE MEAL IS NOT SIZED BY THE NICOTINE FACTOR (form 1 sizes by es and the hour): the factor is read in the
  written HUNGER, and the next-day intake ratio is read through the oracles' own mapping (650 x written / 0.25) over
  D2_20, D3_08 and D3_13, the three meals at the cap with the anchor unfaded (about 2.1-2.8 days old: the factor about
  1.1293-1.1298, the ratio about 1.129 against the pin's 1.1304, within 2 %).
  The anchor edits and the second smoke (x323, at the cap; lib change 6; THE ORDER DEPARTS FROM THE AMENDMENT'S smoke,
  T2-F, fade, because the edits read at the cap give the largest contrast and the smoke then shows the reset from a
  fully faded anchor): FADE at 15:00 day 3 (age 80; the factor about 1.0656 until T2F), T2F at 21:00 day 3 (age 86; the
  factor 1.0 until the smoke), SMOKE2 at 01:00 day 4 (age 90; the stat falls 0.51 to 0, the anchor follows the minute
  while the stat reads 0, then the rise from about age 95.6 reads unfaded).
  Drinking: to thirst by the engine's auto-drink from a server-side canteen (ruling T5R-1), refilled to 0.9 L after
  every meal and nicotine stop and at 10:30 and 16:30; no water food is eaten.
  Sessions: x321 (fresh fixture, to 21:30 day 1, age 38.5), x322 (to 11:30 day 3, age 74.5), x323 (to 14:30 day 4, age
  103.5), chained by server reuse.
  The replay feeds the stat from each ring row (the tool's feed); the seed and each smoke add a marker at the ring row
  that shows them, the edits setpath events placed off the ring (lib change 7); the activity off the ring's rate and
  exe (the tool, 3daaca9).
THE GRADING (after the chain, by the committed analysis script testing/experiments/x32_grade.py, into a staged artifact
folder testing/artifacts/x32-grade-<date>/): each session's replay of live (the tool at HEAD, sleep_allowed false)
under HUNGER 0.002, es 0.005, L 0.5 %; the factor live HUNGER / no-nicotine replay HUNGER (the same replay with
K.satiety.NIC_MAX 0) against 1 + NIC_MAX x clamp(w / 0.51) x clamp(1 - d / 182) on every graded uncapped ring row, 1 %,
by regime (before the gate smoke, w 0, the rise, the cap, the fade edit, T2-F, after the second smoke); the replay's own
factor; the withdrawal's threshold, slope and cap against the DayLength 1 arithmetic; the smokes' falls; the edits;
the next-day ratio as a reading against 1.1304.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x32_nicotine_lib as L   # noqa: E402

PROFILE = "x32-nicotine"
PREFIX = "x321"
PREV_PREFIX = None
ARTIFACT = "nicotine-1.json"
STAGE_ROOT = "release/x32-nicotine/NutritionRevamp"
STAGED_AT = "35c3049e"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
END_AGE = 38.5
SESSION = ("Plan 11f Task 8 session 1 of 3: the Smoker trait, the smoke gate, day 0's maint meals and request day 1, "
           "the withdrawal's rise, on the staged copy; one boot of " + PROFILE)
PRED = {
    "SLEEP_OFF": {"NutritionRevamp.server.nutrients.sleepDisabled": True},
    "SMOKER": {"trait list after trait.set": "holds Smoker (else the session stops in phase S, change b)"},
    "SMOKES": {"G_SMOKE": "seen within 60 s; eats +1; the seeded 0.2 falls to 0 (fall 0.2 within 1e-4); landed +0; "
                          "the timer 0 after"},
    "RISE": {"segment": -1, "bands": {"first_above_0.h_after_smoke": (4.5, 7.0), "slope_per_h": (0.0100, 0.0125)},
             "text": "0 for about 5.56 game h after the gate smoke, then about 0.01125 a game hour (#3630 with #2922 at "
                     "DayLength 1); the cap about 50.9 h after the smoke, in x322"},
    "EXE": {"exe true rows": 0, "asleep rows": 0},
    "STOPS": {"this session's span": "every meal done, none missed, every eat landed, every refill read back"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %), the stat fed from the ring"},
    "SODIUM": {"every chain day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
    "readings": {"w_at_end": 0.32, "maint_kcal": 2089.3, "factor_D1_08": 1.044, "factor_D1_13": 1.058,
                 "factor_D1_20": 1.078},
}


def scenario(S):
    S.run_schedule()


def grade(S, ring, rows_rep):
    L.session_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x321_nicotine.py", scenario,
              grade, end_age=END_AGE, add_smoker=True, gate_first=True).run()
