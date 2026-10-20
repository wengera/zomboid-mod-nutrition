"""x484-line -- Plan 17 Task 7 (live): the straight-line health drain of revision R1 (spec section 9) at Realistic pace
with Multiply, the guide's default line, which had no live proof on the straight-line build (x481's curve line was
DROPPED): starvation seeded past the onset as x481 did, held about two game hours on its line, then beriberi added as
x481 did, graded against the HEAD replay of the run's own inputs.

One boot of profile x48-line (fixture default, admin -debug, PZTestKit and the STAGED upload copy release/NutritionRevamp
at x48b_lib.STAGED_FROM, Nutrition false, DayLength 4, sleep off, NR.DeathPace 3, NR.HealthCombine 2), build 42.21.0.
The engine is testing/experiments/x48b_lib.py on x48_lib.py's Sess (their docstrings hold the phases, the placement of
the writes and the grades with every tolerance). This file names the session, the prefix, the profile, the artifact,
the wall budget and the predictions. Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION: S, H (x48_lib.RING), W (start.json), A (at speed 1: record.set satiety.M 0, then drain.fedAgeH to the age
less 30 h plus 0.1 h; speed 5 until starveAcute), O (2 game h at speed 5), B (at speed 1: record.set
nutrients.thiamine.p 0.3, under the clinical rung 0.4167; polled to the grade 4), P (1 game h at speed 5), C (the clock
back to the trueMult read at S), R.

PREDICTIONS (x48b_prerun.json's x484, the HEAD replay of this schedule from the first sight with the mod's own creation
body, lm 52.02 + fm 13.005 = 65.025 kg, no typed weight: the onset 0.133 game h after the seed at bmi0 22.487; the
target on the line 100 x (1 - pS), falling 0.043331 health a game hour (1.040 a game day) on the smoothed BMI clock;
health on the target (gap 0.0); the rate 85.536 a day, vanilla's level-4 floor, over the line's own 1.040; beriberi's
fraction 1.0 1.5 game minutes after the thiamine write; then the rate 88.393 and the target 100 x f1 x f3, the Add fold
parting from it by up to 1.55e-4 and Worst by 0.119; at the end health 99.751115 on the target):
  OPT        the first ring row: SandboxVars.NR.DeathPace 3 and HealthCombine 2, the polled options and K.drain.OPT the same,
             OPT.dayMin 90 (precondition).
  ONSET      a starveAcute row within 0.35 game h of the seed (precondition).
  LINE       the starvation rows to the thiamine: frac.1 = 1 - pS, target = 100 x frac.1, bRate the calibrated
             STARVE_DBMI; the target's slope within 1 % of 100 x STARVE_DBMI / (bmi0 - 12) a game hour.
  RATE       every row with starvation active at least r_hunger(90) x 24 = 85.536 a day; the starvation rows at that floor, the
             starvation-and-beriberi rows at the floor plus 2.857 (R1-5).
  TRACK      every active row after the onset: |health - target| <= 5e-4 (prerun gap 0.0).
  BERI_ON    the thiamine grade 4 and frac.3 in (0.999, 1] within 2.5 game minutes of the write.
  COMBINE    every row after the write with both fractions: the target 100 x (frac.1 x frac.3) within 1e-9, the combine 2;
             the Add fold parted from it by more than 1e-8 on some row.
  REPLAY_health, REPLAY_drain.target  every ring row within 0.002 of the HEAD replay of the run's own inputs.
  H1, RING, Z  as x481.

WALL: about 6 min (boot about 80 s, S/H about 10 s, W up to 60 s, A about 10 s, O 90 s, B about 10 s, P 45 s, C/R about
15 s, teardown about 30 s); BUDGET_S 480.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x48b_lib as L   # noqa: E402
import x48_lib as L48  # noqa: E402

KEY = "x484"
PREFIX = "x484"
PROFILE = "x48-line"
ARTIFACT = "line.json"
BUDGET_S = 480.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert _ME == L.SESSIONS[KEY]["driver"], f"the driver file {_ME} is not the session's"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.load_prerun().get(KEY) or {}
SESSION = ("Plan 17 Task 7 x484: Realistic pace with Multiply on the straight-line build, starvation seeded past the "
           "onset, held on its line, beriberi added; one boot of " + PROFILE)
PRED = {
    "OPT": "pace 3, combine 2 on the sandbox, the polled options and K.drain.OPT; dayMin 90",
    "ONSET": f"starveAcute within {L48.SEED_LEAD_H + L48.ONSET_SLACK_H} game h of the seed (prerun "
             f"{P.get('onset_after_seed_h')})",
    "LINE": f"frac.1 = 1 - pS, target = 100 x frac.1, bRate STARVE_DBMI; slope 100 x STARVE_DBMI / (bmi0 - 12) within "
            f"{L.LINE_TOL_REL} (prerun {(P.get('line') or {}).get('slope_h')} a game h at bmi0 "
            f"{(P.get('line') or {}).get('bmi0')})",
    "TRACK": f"|health - target| <= {L.TRACK_TOL} on every active row after the onset (prerun "
             f"{P.get('health_gap_max')})",
    "RATE": f"every row with starvation active at least r_hunger(90) x 24 = {L.r_hunger(90) * 24:.3f}; starvation at it, with beriberi "
            f"at it plus {100.0 * 24.0 / L.K_BERIBERI_DEATH_H:.3f}, within {L.RATE_TOL_REL}",
    "BERI_ON": f"grade 4 and frac.3 near 1 within {L48.BERI_GM} game minutes (prerun "
               f"{(P.get('beri') or {}).get('lag_gm')})",
    "COMBINE": f"target 100 x (f1 x f3) within {L.COMBINE_TOL} on every row after the write, the Add fold parted by "
               f"more than {L.COMBINE_SEP * L.COMBINE_TOL} (prerun {(P.get('combine') or {}).get('sep_add_max')})",
    "REPLAY_health": "within 0.002 of the HEAD replay", "REPLAY_drain.target": "within 0.002 of the HEAD replay",
    "H1": "every ring path resolved but the onset's", "RING": "every page read, errors 0",
    "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, _ME, SESSION, PRED, BUDGET_S)
