"""x481-curve -- Plan 17 Task 4 (live): the remaining-fraction drain at Realistic pace with Multiply (spec 4.5 a and c):
the opening at the calibrated rate, starvation and beriberi combining, and an admin's switch of NR.DeathPace followed
within a game minute.

One boot of profile x48-curve (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan17-x48 of
mod/NutritionRevamp at x48_lib.STAGED_FROM, Nutrition false, DayLength 4, sleep off, NR.DeathPace 3, NR.HealthCombine 2),
build 42.21.0. The staged copy is made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out
release/plan17-x48`) and checked against mod/ at that commit; the engine is testing/experiments/x48_lib.py (its
docstring holds the phases, the placement of the writes and the grades with every tolerance). This file names the
session, the prefix, the profile, the artifact, the wall budget and the predictions. Written BEFORE the boot and never
edited after the run (CLAUDE.md s5).

THE SESSION: S, H (x48_lib.RING), W (start.json), A (at speed 1: record.set satiety.M 0, then drain.fedAgeH to the age
less 30 h plus 0.1 h; speed 5 until starveAcute), O (1 game h at speed 5), B (at speed 1: record.set
nutrients.thiamine.p 0.3, under the clinical rung 0.4167; polled to the grade 4), SW (0.5 game h at speed 5; at speed 1
SandboxVars.NR.DeathPace read, then sandbox.var NR.DeathPace 2; the polled K.drain.OPT.pace read until it follows; 5
game minutes at speed 1), P (0.75 game h at speed 5), C, R, K (NR.DeathPace back to the value read).

PREDICTIONS (x48_prerun.json's x481, the HEAD replay of this schedule from the first sight: the onset 0.133 game h after
the seed; the fixture's 80 kg body at bmi0 27.669 opens at 2.371 health a game hour, 0.665 of r_hunger(90) = 3.564, by
the curve's own body scaling (spec 1.2), under the cap 85.536 a day; beriberi's fraction 1.0 1.5 game minutes after the
thiamine write; the switch moves the target from 96.730 (no switch) to 95.033 in the first drain after the write, then
health falls at the summed rate 88.393 a day, 3.683 a game hour, toward it; at the end health 93.757 and the target
92.688):
  OPT        the first ring row: SandboxVars.NR.DeathPace 3 and HealthCombine 2, the polled options and K.drain.OPT the same,
             OPT.dayMin 90 (precondition).
  ONSET      a starveAcute row within 0.35 game h of the seed (precondition).
  OPEN_RATE  drain.rate 85.536 a day (r_hunger(90) x 24) within 1 % on every onset row before the thiamine.
  OPEN_SLOPE the health slope over the first 3 game minutes within 1 % of the kernel curve's for the ring's bmi0.
  BERI_ON    the thiamine grade 4 and frac.3 in (0.999, 1] within 2 game minutes of the write.
  COMBINE    every row with both fractions: the target 100 x frac.1 x frac.3 within 1e-6 x 100, the combine 2.
  FOLLOW     the first row nearer the switch arm, its drain within 1.2 game minutes of the age read before the write.
  CAP        the capped health slope within 1 % of drain.rate / 24.
  REPLAY_health, REPLAY_drain.target  every ring row within 0.002 of the HEAD replay of the run's own inputs.
  H1, RING, Z  as x461a.

WALL: about 5.5 min (boot about 80 s, S/H about 10 s, W up to 60 s, A about 10 s, O 45 s, B 5 s, SW about 50 s, P 34 s,
C/R/K about 15 s, teardown about 30 s); BUDGET_S 480.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x48_lib as L   # noqa: E402

KEY = "x481"
PREFIX = "x481"
PROFILE = "x48-curve"
ARTIFACT = "curve.json"
BUDGET_S = 480.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.load_prerun().get(KEY) or {}
SESSION = ("Plan 17 Task 4 x481: Realistic pace with Multiply, starvation seeded past the onset, beriberi added, "
           "NR.DeathPace switched to Shortened; one boot of " + PROFILE)
PRED = {
    "OPT": "pace 3, combine 2 on the sandbox, the polled options and K.drain.OPT; dayMin 90",
    "ONSET": f"starveAcute within {L.SEED_LEAD_H + L.ONSET_SLACK_H} game h of the seed (prerun "
             f"{P.get('onset_after_seed_h')})",
    "OPEN_RATE": f"drain.rate r_hunger(90) x 24 = {L.r_hunger(90) * 24:.3f} within {L.RATE_TOL_REL}",
    "OPEN_SLOPE": f"the kernel curve's opening for the live bmi0 within {L.OPEN_TOL_REL} (prerun "
                  f"{(P.get('open') or {}).get('pred')} a game h at bmi0 {(P.get('open') or {}).get('bmi0')})",
    "BERI_ON": f"grade 4 and frac.3 near 1 within {L.BERI_GM} game minutes",
    "COMBINE": "target 100 x f1 x f3 on every row with both", "FOLLOW": f"within {L.FOLLOW_GM} game minutes",
    "CAP": f"health at drain.rate / 24 within {L.CAP_TOL_REL} (prerun {(P.get('cap') or {}).get('slope_h')})",
    "REPLAY_health": "within 0.002 of the HEAD replay", "REPLAY_drain.target": "within 0.002 of the HEAD replay",
    "H1": "every ring path resolved but the onset's", "RING": "every page read, errors 0",
    "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
