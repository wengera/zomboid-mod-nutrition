"""x421-levers -- Plan 13 Task 0 Step 5 (live): the engine checks the lean-mass Strength redesign rests on, before any
build. One boot of profile x42-levers: fixture two (admin -debug, then bob, the release user-role client), PZTestKit and
the probe mod TKX_TraitLevers by its path (testing/experiments/TKX_TraitLevers/42.21: a restated base:obese block, the
Underweight and Overweight list edits at shared file scope, an OnNewGame writer and an AddXP recorder on the server, a
UI_trait_obesedesc marker), no NutritionRevamp (no mod/ file is booted), Nutrition false, DayLength 1, build 42.21.0.
The engine is testing/experiments/x42_levers_lib.py (frozen with this run); its docstring names the nine checks, the
respawn route, the reply shapes it reads and the two deviations from the brief's literal values (the pushup set asked
for PUSHUP_M game minutes; the melee target spawned beside bob by the probe's zombieNear). Written BEFORE the boot with
every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE ORDER: S (the setting: bob's role and access level, the run's AntiCheat* ini lines, the sandbox multipliers),
D (checks 1-3: trait.def of Obese, Underweight and Overweight on the server, bob's client and admin's client; the
probe's edits record on all three), N1 (bob's first death and respawn: checks 4 and 6), B (the debug write: check 6's
second half), N2 (creation.picks Strong Stout Obese Overweight, bob's second death and respawn: check 5), S7 (the three
Strength sources: check 7), S8 (the level-10 park: check 8), S9 (the pin under the anti-cheat, last because a kick ends
bob's session: check 9).

PREDICTIONS (graded in `verdicts`: as_predicted / falsified / unmeasured); the stop table is the plan's Task 0 Step 6.
  1  Obese reads cost -10, free false, no Fitness boost, Overweight excluded, on the server and on bob's client.
  2  Underweight reads no Fitness boost; Overweight excludes Obese and not Athletic, both sides; no edit error on the
     server or either client.
  3  bob's client definitions equal the server's for the three traits (the marker description a reading).
  4  the first same-second pair after the server's newGame lands: bob's client weight 77.7, OUT_OF_SHAPE held, STRONG
     not held, the client's Strength level the handler's stepped level.
  5  the server's known traits before the handler hold Strong, Stout, Obese and Overweight.
  6  the stepped level's Strength band on both sides (route_swaps); the perk.level debug write swaps no band (#2870).
  7  pushups, the melee hit and loaded movement each fire at least one positive Strength AddXP event for bob.
  8  one Strength event of 100 x the protein factor x the sandbox multiplier after the park; the level stays 10.
  9  bob stays online and no anti-cheat line shows across two check intervals after the pin pair.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x42_levers_lib as L   # noqa: E402

PROFILE = "x42-levers"
PREFIX = "x421"
ARTIFACT = "levers.json"
BUDGET_S = 1500.0
SESSION = ("Plan 13 Task 0 Step 5: the nine live engine checks (trait definitions on both sides, creation writes, the "
           "illegal pick list, the band swap, the AddXP sources, the level-10 park, the XP pin under the anti-cheat); "
           "one boot of " + PROFILE + ", fixture two, bob the subject")
PRED = {
    "1": {"Obese": "cost -10, free false, no Fitness boost, Overweight excluded; server and bob's client"},
    "2": {"Underweight": "no Fitness boost", "Overweight": "Obese excluded, Athletic not", "edits": "no error"},
    "3": {"client defs": "equal the server's for Obese, Underweight, Overweight"},
    "4": {"first pair": "client weight 77.7, OUT_OF_SHAPE held, STRONG not, Strength level the stepped level"},
    "5": {"server known traits before the handler": "Strong, Stout, Obese, Overweight all held"},
    "6": {"handler step": "the stepped level's band on both sides", "debug write": "no band swap (#2870)"},
    "7": {"pushups, melee, loaded movement": "each at least one positive Strength AddXP event"},
    "8": {"park at 9, grant 100 at level 10": "one event of 100 x protein factor x sandbox multiplier; level 10"},
    "9": {"perk.set 7, park 7, grant 30000": "bob online throughout 130 s; no anti-cheat line"},
}


if __name__ == "__main__":
    L.main(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, "x421_levers.py")
