"""x494-accept -- Plan 18 Task 4 (live): the acceptance of the symptom layer on a seeded Realistic fast with water
(starvation, then wet beriberi at clinical): the Pain, Endurance, Stress and Unhappy moodles at their predicted progress
on the server and on the client, then the release after a snack, each graded against the HEAD replay of the run's own
inputs.

One boot of profile x49-accept (fixture default, admin -debug; PZTestKit, the STAGED upload copy
release/NutritionRevamp at x49b_lib.STAGED_FROM and the probe TKX_Symptoms by its path, an observer only; Nutrition
false, DayLength 4, SLEEP OFF, NR.Mode 1, DeathPace 3, HealthCombine 2, Severity 1.0), build 42.21.0. The engine is
testing/experiments/x49b_lib.py (its docstring holds the phases, the floor seed, the effects in force, the grades and
every tolerance) on x48_lib.py's and x49_lib.py's frozen sessions. This file names the session, the prefix, the
profile, the artifact, the wall budget and the predictions. Written BEFORE the boot and never edited after the run
(CLAUDE.md s5).

THE SESSION: S (x48's reads, the probe watching admin, every part, a pair), H (the ring, x49b_lib.RING), W (start.json),
A (x484's seed at speed 1; speed 5 until starveAcute, the onset's wall bracket kept; speed 1), ON (40 s of pairs from
the onset), P1 (drain.pS 0.5; the floors seeded; 50 s of pairs), B (thiamine 0.30, polled to grade 4; 50 s of pairs), P2
(drain.pS 0.9; the floors seeded; 40 s of pairs), L (satiety.M 300, polled until starvation lapses; 16 s of pairs at
speed 1, then 46 s at speed 5), C (the clock back; the probe's errors; every part), R (the ring).

PREDICTIONS (x49b_prerun.json's x494, the HEAD replay of this schedule from the first sight with the mod's own creation
body; the live grades read the replay of the run's own inputs):
  P1   starvation alone at p 0.5: the endurance cap 0.355 (Endurance 2), the floors STRESS 0.30 (Stress 1) and
       UNHAPPINESS 25 (Unhappy 1), Torso_Lower's added pain held at 19.680769 (vanilla's PAIN target 15.351, mid 15.0:
       Pain 1).
  B    wet beriberi added at clinical: both lower legs at 12.95 (PAIN target 30.891, mid 30.0: Pain 2); the cap and the
       floors unchanged (beriberi's progress about 0).
  P2   p 0.9: cap 0.125 (Endurance 3), STRESS 0.55 (Stress 2), UNHAPPINESS 50 (Unhappy 2), Pain 2.
  L    the snack lapses starvation in the drain after it (mask 4, starvation recovering): the progress falls to its
       true BMI progress (about 0.0004), the cap eases to about 0.7295 and the floors to about 0; the lower torso is no
       longer set and falls 0.9 a game minute to 0 (the legs' Pain 1 left); UNHAPPINESS falls by the remembered target's
       fall (50 to about 0.03) at once; STRESS falls by vanilla's decay, about 0.0018 a game minute (Stress 1 by L2's
       end); ENDURANCE climbs under the eased cap (Endurance 2 or less by L2's end).
  The Pain moodle's first level 1 after the onset: 41.9-71.9 s on the server and 41.9-61.9 s on the client.

WALL: about 8.5 min (boot about 80 s, S/H about 20 s, W up to 60 s, A about 20 s, ON about 47 s, P1 about 63 s, B
about 62 s, P2 about 53 s, L about 75 s, C/R about 10 s, grading and teardown about 30 s); BUDGET_S 510, every arm
shortened to keep x49b_lib.CLOSE_RESERVE_S for C and R (the fake world runs S to R in 272 wall s).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
6. Takes no argument: a bare call boots the session.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x49b_lib as L                                                          # noqa: E402

KEY = "x494"
PREFIX = "x494"
PROFILE = "x49-accept"
ARTIFACT = "accept.json"
BUDGET_S = 510.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert _ME == L.SESSIONS[KEY]["driver"], f"the driver file {_ME} is not the session's"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.load_prerun().get(KEY) or {}
A = P.get("arms") or {}
SESSION = ("Plan 18 Task 4 x494: the symptom layer's live acceptance on a seeded Realistic fast with water (starvation, "
           "wet beriberi at clinical), the release after a snack; one boot of " + PROFILE)


def _lv(arm, k):
    return (A.get(arm) or {}).get("levels", {}).get(k)


PRED = {
    "OPT": "K.drain.OPT pace 3, combine 2, dayMin 90; SandboxVars.NR.Severity and the polled severity 1",
    "ONSET": f"starveAcute within {L.SEED_LEAD_H + L.L48.ONSET_SLACK_H} game h of the seed (prerun "
             f"{P.get('onset_after_seed_h')})",
    "P0_BASE": "no part holds added pain; PAIN, STRESS, UNHAPPY and ENDURANCE at level 0 at S",
    "BERI_ON": f"grade 4 and frac.3 near 1 within {L.L48.BERI_GM} game minutes of the thiamine write",
    "H1": "every ring path resolved at the start but frac.1 and frac.3", "RING": "every page read, errors 0",
    "Z": "no mod or probe error line, admin not parked, no probe-recorded error",
    "PAIN_PART": "Torso_Lower's added pain (and each painful part at an arm's end) within [target - 0.9 x 1.7 - 0.01, "
                 "target + 0.01] while set (prerun targets 19.680769 and 12.95)",
    "PAIN_TARGET": f"the server's PAIN at P1's and P2's end within [0.85 x the dipped target, the target + 0.01] "
                   f"(prerun targets {(A.get('P1') or {}).get('painTarget')} and {(A.get('P2') or {}).get('painTarget')})",
    "PAIN_ONSET": f"each side's first Pain 1 after the onset within its window (prerun server "
                  f"{(P.get('onset') or {}).get('window_s')} s, client {(P.get('onset') or {}).get('window_c')} s)",
    "PAIN_LEVELS": f"the last 5 pairs at Pain {_lv('P1', 'pain')} (P1), {_lv('B', 'pain')} (B), {_lv('P2', 'pain')} "
                   f"(P2) and {_lv('L2', 'pain')} (L2) on both sides",
    "PAIN_FOLLOWS": "each side's Pain level is its own PAIN's (FOLLOW_EPS 3.0) over P1, B, P2 and L1",
    "END_CAP": "the server's ENDURANCE at or under the cap in force plus one interval's worst climb",
    "END_LEVELS": f"Endurance {_lv('P1', 'endurance')} (P1), {_lv('B', 'endurance')} (B), {_lv('P2', 'endurance')} "
                  f"(P2) on every pair and both trackers",
    "STRESS_FLOOR": "the server's STRESS at or over the floor in force less one interval's vanilla decay",
    "UNHAPPY_FLOOR": "the server's UNHAPPINESS at or over the floor in force; moodLast.u at or over the floor",
    "STRESS_LEVELS": f"Stress {_lv('P1', 'stress')} (P1), {_lv('B', 'stress')} (B), {_lv('P2', 'stress')} (P2)",
    "UNHAPPY_LEVELS": f"Unhappy {_lv('P1', 'unhappy')} (P1), {_lv('B', 'unhappy')} (B), {_lv('P2', 'unhappy')} (P2)",
    "REL_LAPSE": f"starvation out of the mask, beriberi in, within {L.LAPSE_GM} game minutes of the snack (prerun "
                 f"mask {(P.get('lapse') or {}).get('mask')}, lag {(P.get('lapse') or {}).get('lag_m')} minutes)",
    "REL_PAIN": "the lower torso never set again after the lapse, falling 0.9 a game minute within 5 % to 0",
    "REL_END": f"the cap eased from {(P.get('lapse') or {}).get('cap_before')} to "
               f"{(P.get('lapse') or {}).get('cap_after')}; ENDURANCE never pulled down; Endurance 2 or less at L2's end",
    "REL_UNHAPPY": f"UNHAPPINESS falls by the remembered target's fall ({(P.get('lapse') or {}).get('u_before')} to "
                   f"{(P.get('lapse') or {}).get('u_after')}) at once; Unhappy 0 at L1's end",
    "REL_STRESS": f"STRESS never raised after the lapse, falling {L.STRESS_DECAY_GM} a game minute within 15 %; Stress "
                  f"1 at L2's end",
}
for _f in L.REPLAY_TOL:
    PRED[f"REPLAY_{_f}"] = f"within {L.REPLAY_TOL[_f][1]} of the HEAD replay of the run's own inputs"

if __name__ == "__main__":
    refusal = L.parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    L.main(KEY, _ME, SESSION, PRED, BUDGET_S)
