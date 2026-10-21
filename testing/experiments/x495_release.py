"""x495-release -- Plan 18 Task 4, the second live session (controller ruling T4-2): the release of the symptom layer
after a snack, which x494-20261021-121229 left unmeasured (its own budget stopped it at phase L). x494 is frozen; this is
a new driver on a new lib.

One boot of profile x49-accept (x494's: fixture default, admin -debug; PZTestKit, the STAGED upload copy
release/NutritionRevamp at x49b_lib.STAGED_FROM 6ee7c8d1 and the observer probe TKX_Symptoms; Nutrition false, DayLength
4, sleep off, NR.Mode 1, DeathPace 3, HealthCombine 2, Severity 1.0), build 42.21.0. The engine is
testing/experiments/x49c_lib.py on x49b_lib.py (its docstring holds the schedule, the measured budget and the grades).
Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE SESSION: S (the S pair retried until valid), H, W, A (x484's seed to the onset), P1 (drain.pS 0.5; the floors 0.30
and 25 seeded once; no pairs), B (thiamine 0.30, wet beriberi at clinical; 90 s of pairs before the lapse), L
(satiety.M 240, the 200 kcal snack's pool, polled to the lapse; 16 s of pairs at speed 1, then 80 s at speed 5, about
107 game minutes), C, R.

PREDICTIONS (x49c_prerun.json's x495, the HEAD replay of this schedule from the first sight):
  B    starvation at p 0.5 and wet beriberi: cap 0.355 (Endurance 2), floors 0.30 (Stress 1) and 25 (Unhappy 1), the
       lower torso 19.680769 and both lower legs 12.95 (PAIN target 30.891, mid 30.0: Pain 2).
  L    the snack lapses starvation in the drain after it (mask 4, recovering); the cap eases 0.355 -> about 0.7297, the
       floors to about 0, the remembered UNHAPPINESS target 25 -> about 0.022; health heals from about 98.29 to its
       target (the replay at it 20 game minutes after the lapse; live later, the stand-in's heal leads: F2); the lower
       torso decays 0.9 a game minute to 0 (the legs' Pain 1 left); STRESS falls 0.0018 a game minute from 0.30 (Stress
       0 by about 28 game minutes); ENDURANCE climbs to Endurance 1 under the eased cap.

WALL (x49c_lib.predicted_wall, off x494's measured costs): the lapse at about 317 s, the phases' end about 435 s, the
worst call about 520 s with the bounded teardown; BUDGET_S 470 (the arms cut at 445 s).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
6. Takes no argument: a bare call boots the session.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x49c_lib as L                                                          # noqa: E402

KEY = "x495"
PREFIX = "x495"
PROFILE = "x49-accept"
ARTIFACT = "release.json"
BUDGET_S = 470.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert _ME == L.SESSIONS[KEY]["driver"], f"the driver file {_ME} is not the session's"
assert L.SESSIONS[KEY]["profile"] == PROFILE and L.SESSIONS[KEY]["artifact"] == ARTIFACT
P = L.load_prerun().get(KEY) or {}
LP = P.get("lapse") or {}
SESSION = ("Plan 18 Task 4 x495: the symptom layer's release after a snack on a seeded Realistic fast (starvation at "
           "p 0.5, wet beriberi at clinical); one boot of " + PROFILE)
PRED = {
    "OPT": "K.drain.OPT pace 3, combine 2, dayMin 90; SandboxVars.NR.Severity and the polled severity 1",
    "ONSET": "starveAcute within 0.35 game h of the seed",
    "P0_BASE": "no part holds added pain; PAIN, STRESS, UNHAPPY and ENDURANCE at level 0 at S (a valid pair)",
    "BERI_ON": "grade 4 and frac.3 near 1 within 2.5 game minutes of the thiamine write",
    "H1": "every ring path resolved at the start but frac.1 and frac.3", "RING": "every page read, errors 0",
    "Z": "no mod or probe error line, admin not parked, no probe-recorded error",
    "PAIN_PART": "the lower torso and both lower legs within their bands before the lapse (targets 19.680769, 12.95)",
    "PAIN_TARGET": "the server's PAIN at B's end within [0.85 x the dipped target, 30.901]",
    "PAIN_LEVELS": "Pain 2 at B's end and Pain 1 at L2's (the legs alone), both sides",
    "PAIN_FOLLOWS": "each side's Pain level is its own PAIN's over B and L1",
    "END_CAP": "the server's ENDURANCE at or under the cap in force plus one interval's worst climb",
    "END_LEVELS": "Endurance 2 at B on every pair and both trackers",
    "STRESS_FLOOR": "STRESS at or over 0.30 less one interval's decay at B",
    "UNHAPPY_FLOOR": "UNHAPPINESS at or over 25 at B; moodLast.u carries the floor",
    "STRESS_LEVELS": "Stress 1 at B", "UNHAPPY_LEVELS": "Unhappy 1 at B",
    "REL_LAPSE": f"starvation out of the mask, beriberi in, within 2.5 game minutes of the snack (prerun mask "
                 f"{LP.get('mask')}, lag {LP.get('lag_m')} minutes)",
    "REL_PAIN": "the lower torso never set again after the lapse, falling 0.9 a game minute within 5 % to its own end",
    "REL_END": f"the cap eased from {LP.get('cap_before')} to {LP.get('cap_after')}; ENDURANCE never pulled down "
               f"under the cap (held at it once it climbs there); "
               f"Endurance 1 at L2's end on both sides",
    "REL_UNHAPPY": f"UNHAPPINESS falls by the remembered target's fall ({LP.get('u_before')} to {LP.get('u_after')}) "
                   f"at once; Unhappy 0 at L1's end",
    "REL_STRESS": "STRESS never raised after the lapse, falling 0.0018 a game minute within 15 %; Stress 0 at L2's end",
    "REL_HEAL": "after the lapse health never over its target, never taken, and at the target by 50 game minutes",
}
for _f in L.B.REPLAY_TOL:
    PRED[f"REPLAY_{_f}"] = f"within {L.B.REPLAY_TOL[_f][1]} of the HEAD replay of the run's own inputs"

if __name__ == "__main__":
    refusal = L.parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    L.main(KEY, _ME, SESSION, PRED, BUDGET_S)
