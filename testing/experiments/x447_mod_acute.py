"""x447-mod-acute -- Plan 14 Task 5, session M2 (live): the mod's caffeine with its tolerance, blood alcohol, the
hangover and the sleep debt live at HEAD (the guide's S6; gaps G10, G15, G17: a hangover was never read live).

One boot of profile x44-mod-sleep (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan14-x44 of
mod/NutritionRevamp at HEAD, Nutrition false, DayLength 1, SleepAllowed and SleepNeeded true), build 42.21.0. The staged
copy is made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan14-x44`); the
driver checks its MANIFEST against a clean mod/ at HEAD and refuses on a mismatch (CLAUDE.md s5, x201). The engine is
testing/experiments/x44_guide_lib.py; this file names the session, the run prefix, the profile, the artifact, the wall
budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION (the source map's M2):
  S, H, W  as x446, the ring adding the acute states (acute.caf, cafTol, gutCaf, alc, bac, gutAlc, hang, hangH, debtH,
     sleptH, winSleptH, S) and effects.fOff.
  X  the schedule relative to X's start a (review I-2: the DL1 sessions start near world age 3.2 and phase W waits
     up to 80 s, so a clock-hour coffee could be past): at speed 5 between the stops and speed 1 at each, a 0.25 L
     coffee at a + 0.1, a + 3.1 and a + 6.1 game hours (each in its own prefilled container type, Base.WaterBottle,
     Base.FountainCupWater, Base.Pop3, spawned by RCON, the server copy refilled with Coffee by fluid.fill, the fill
     gated, drink.action); four beers back to back at least 3 game hours after the last coffee and not before 19:00
     (Base.BeerCan, Base.BeerBottle, Base.BeerImported, Base.Pop2, each server copy filled with 0.3 L Beer: one type
     a drink, see x44_guide_lib.BEER_CONTAINERS); the night at the next 23:00 (or 1 game hour after the beers when
     that 23:00 is more than 4 h away): player.sleep.hold, acute.sleptH polled to 4 booked game hours (cap 90 s),
     the hold cancelled and the flag cleared, the booked hours kept as a reading (the fast-forward rests on #2956,
     not re-read on 42.21); then 6 game hours after the night's end, a Base.CannedBologneseOpen at every request
     (HUNGER 0.25). Every planned stop must fall before the night, or X is refused. The replay's sleep events come
     off the ring's acute.sleptH (x30's rule).
  C  the clock restored; R  the ring read and stopped; Z  the mod's error lines and the debugger park.

PREDICTIONS: the HEAD kernel replay (ServerReplay, sleep_allowed true) of the ring's own clock from start.json, with
the drinks split over their sip rows, the eats, the ring's autoDrop, movement and sleep events, reproduces on every
graded row HUNGER within 0.002, body.energyState within 0.005, THIRST within 0.002, acute.caf within 1 mg, acute.bac
within 0.001, acute.hang within 0.5 (the flag itself) and acute.debtH within 0.05 h (named before the run); a hangover
is reached live iff the replay reaches one, its start within 0.25 game hour (M2_hangover).
  Grades: M2_replay_<field> for the seven fields, M2_hangover, H1, RING, Z.

WALL: about 7.5 min (boot about 80 s, the save wait up to 80 s, about 17 game hours awake at speed 5 about
2.1 min, seven drinks and the meals at speed 1 about 1.5 min, the night under 90 s, teardown); BUDGET_S 470
keeps the whole call under about 9 min (the controller's ruling: no detached launch).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x44_guide_lib as L   # noqa: E402

KEY = "M2"
PROFILE = "x44-mod-sleep"
PREFIX = "x447"
ARTIFACT = "acute.json"
BUDGET_S = 470.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
SESSION = ("Plan 14 Task 5 M2: three coffees and four beers, a 4-hour night, then meals at the request, "
           "on the staged copy at HEAD with sleep on; one boot of " + PROFILE)
PRED = {
    "M2_replay_HUNGER": "within 0.002 of the HEAD replay", "M2_replay_body.energyState": "within 0.005",
    "M2_replay_THIRST": "within 0.002", "M2_replay_acute.caf": "within 1 mg", "M2_replay_acute.bac": "within 0.001",
    "M2_replay_acute.hang": "the same flag", "M2_replay_acute.debtH": "within 0.05 game hour",
    "M2_hangover": "a hangover live iff in the replay, its start within 0.25 game hour",
    "H1": "every ring path resolved at the start", "RING": "every page read, errors 0",
    "Z": "no mod error line, admin not parked",
}


if __name__ == "__main__":
    L.main(KEY, PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
