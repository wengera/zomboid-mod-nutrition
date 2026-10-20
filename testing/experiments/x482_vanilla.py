"""x482-vanilla -- Plan 17 Task 4 (live): the remaining-fraction drain at Vanilla pace with Add, the plain-vanilla corner
(spec 4.5 b): the starving character dies on vanilla's clock, against the HEAD replay of its own inputs and beside x442.

One boot of profile x48-vanilla (fixture default, admin -debug, PZTestKit and the STAGED copy release/plan17-x48 of
mod/NutritionRevamp at x48_lib.STAGED_FROM, Nutrition false, DayLength 4, sleep off, NR.DeathPace 1, NR.HealthCombine 3),
build 42.21.0. The staged copy is made before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out
release/plan17-x48`) and checked against mod/ at that commit; the engine is testing/experiments/x48_lib.py. This file
names the session, the prefix, the profile, the artifact, the wall budget and the predictions. Written BEFORE the boot
and never edited after the run (CLAUDE.md s5).

THE SESSION: S, H (x48_lib.RING), W (start.json), A (at speed 1: record.set satiety.M 0, then drain.fedAgeH to the age
less 30 h plus 0.1 h; speed 30 until starveAcute), D (speed 30, a game hour 7.5 wall s, until admin reads dead, polled
each wall second with health.get and isDead, or the prerun's death plus 1.5 game h, or the budget), E (the after-death
reads), C (the clock back to the trueMult read at S), R. The server log is copied with the artifact (the death).

PREDICTIONS (x48_prerun.json's x482, the HEAD replay of this schedule from the first sight: the onset 0.117 game h
after the seed; health on vanilla's line, 3.564 a game hour at the 90-minute day; the death 28.05 game h after the onset
drain, 28.17 after the seed's write; x442 died 36.45 game h after its HUNGER write and 28.12 after its level-4
crossing, so the reading's differences are -8.28 h after the write (the onsets differ) and -0.07 h after the onset):
  OPT        the first ring row: SandboxVars.NR.DeathPace 1 and HealthCombine 3, the polled options and K.drain.OPT the same,
             OPT.dayMin 90 (precondition).
  ONSET      a starveAcute row within 0.35 game h of the seed (precondition).
  SLOPE      the health slope between 95 and 5 within 1 % of r_hunger(90) = 3.564 a game hour.
  DEATH      the first ring row reading dead (or health 0) within 0.05 game h of the replay's death.
  REPLAY_health, REPLAY_drain.target  every ring row to the death within 0.002 of the HEAD replay.
  H1, RING, Z  as x461a.
  (reading)  checks.x442: the death after the write and after the onset beside x442's (never a grade).
  If the death does not fit the budget, DEATH is unmeasured and checks.projection holds the line's projected death.

WALL: about 7 min (boot about 80 s, S/H about 10 s, W up to 60 s, A about 5 s, D about 215 s, E 5 s, C/R about 15 s,
teardown about 30 s); BUDGET_S 530.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x48_lib as L   # noqa: E402

KEY = "x482"
PREFIX = "x482"
PROFILE = "x48-vanilla"
ARTIFACT = "vanilla.json"
BUDGET_S = 530.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.load_prerun().get(KEY) or {}
SESSION = ("Plan 17 Task 4 x482: Vanilla pace with Add, starvation seeded past the onset, held at speed 30 to the "
           "death; one boot of " + PROFILE)
PRED = {
    "OPT": "pace 1, combine 3 on the sandbox, the polled options and K.drain.OPT; dayMin 90",
    "ONSET": f"starveAcute within {L.SEED_LEAD_H + L.ONSET_SLACK_H} game h of the seed (prerun "
             f"{P.get('onset_after_seed_h')})",
    "SLOPE": f"r_hunger(90) = {L.r_hunger(90):.3f} a game hour within {L.SLOPE_TOL_REL}",
    "DEATH": f"within {L.DEATH_TOL_H} game h of the replay's death (prerun {P.get('death_after_seed_h')} game h after "
             f"the seed)",
    "REPLAY_health": "within 0.002 of the HEAD replay to the death",
    "REPLAY_drain.target": "within 0.002 of the HEAD replay to the death",
    "H1": "every ring path resolved but the onset's", "RING": "every page read, errors 0",
    "Z": "no mod error line, admin not parked",
}

if __name__ == "__main__":
    L.main(KEY, PREFIX, PROFILE, ARTIFACT, SESSION, PRED, BUDGET_S, _ME)
