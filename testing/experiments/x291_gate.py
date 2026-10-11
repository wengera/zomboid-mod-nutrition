"""x291-gate -- Plan 11f Task 6 session 1 (live): the vigour gate (ruling 11f-5) and the decay leg of research row 9.
One boot of profile x29-exercise (fixture default, admin -debug, Nutrition false, DayLength 1, sleep off) on the STAGED
copy of the tree (release/x29-exercise, staged fresh from HEAD before the boot; mod/ is never booted) plus
TKX_StudyFoods by its path. Build 42.21.0. The engine is testing/experiments/x29_exercise_lib.py (frozen with this
run). The fixture is restored. Written BEFORE the boot with every prediction in it and never edited after the run
(CLAUDE.md s5, B3-1/B3-2).

USAGE: python testing/experiments/x291_gate.py

RESEARCH ROW 9 (docs/superpowers/research/2026-10-10-live-study-replays/01-harness-facts.md s6, copied):
  | 9 | Acute exercise suppression | S1502 (King 2017), S1500 (Hu 2023), S1303, S1305, S1306, S1301, S1302 |
  `test_the_bout_tracks_the_pooled_mm_readings` (0.674 over the bout, -3.8 mm at +30), `test_the_suppression_is_gone_by...`,
  `test_resistance_swinging_suppresses_less...`, `test_brisk_walking...` | gate: 20 game min `exercise.do squats`, and
  `attack.melee` at an RCON-spawned zombie, reading `body.met`, `satiety.S` per minute; decay leg: `lua.setpath
  ...satiety.S 1` at rest and ring the decay | ~6 | 1 (slow) | S, met, HUNGER/(replay without acute) | likely
  unmeasured for the rise (squats bill 3-4 MET, #2984/#3000; the run flag never reaches the server, #2877); the decay
  leg passes at half-life 0.15 h within 1 % (`NR_Kernel_Satiety.lua:167`) - flagged |
  (The oracle's -3.8 mm reads -3.7 since Plan 11f Task 2c's refit: test_the_bout_replay_pins_its_readings.)
THE TASK 6 AMENDMENTS (ruling 11f-5, copied in substance): the writer's acute suppression needs the vigorous swing state
or a billed MET of 6.0 or more (W.vigorous, NR_Server_Writer.lua:162-169). Candidates: melee swings at an RCON-spawned
zombie (whether the server's copy of the player is in the swing state is unmeasured); the heaviest Fitness exercise the
server bills; any work action the server classes as HeavyWork. Read the billed body.met and the writer's vigorous flag
(the writer stores no flag: S rising between ring rows is a vigorous drain, since K.satiety.exerciseSuppression steps S
toward the kind's weight only while vigorous and toward 0 otherwise) for each candidate. If none reaches vigour, the
rise leg is recorded as unmeasured live, with its MET readings, and no synthetic MET is injected. The decay leg runs
either way: lua.setpath on satiety.S, then ring the decay at the 0.15 h half-life. Candidate C-2 (graded intensity in
place of the 6.0 bar) gains evidence either way.

THE CANDIDATES, NAMED BEFORE THE RUN (the actions and classes read on the install and the mod):
  squats: FitnessExercises.exercisesType.squats, metabolics = Metabolics.Fitness (engine 6.0); live squats billed
    3.0-4.0, the server's metabolic rate a bounded approach that reached 4.97 on a poll and 5.1 per tick (#2875, #2984,
    #3000). A rate at or above 5.75 classes HeavyWork (classOf's nearest, the tie to the earlier name; billed 6.0),
    and with the server's Fitness exercise set (ISFitnessAction:serverStart setCurrentExercise; NR_Server_Metabolism
    readActivity's exercising) it is resistance work, weight 0.5.
  burpees: the heaviest Fitness exercise exercise.do can queue: metabolics = Metabolics.FitnessHeavy (engine 9.0;
    barbellcurl, dumbbellpress and bicepscurl bill the same and need an item the harness command does not equip).
  HeavyWork actions (ISBuildAction, ISMultiStageBuild, ISAddCompost, ISGetCompost, ISDestroyStuffAction,
    ISPickAxeGroundCoverItem, ISPickupDung, ISScything, ISTakeGenerator, ISRemoveBurntVehicle; ISChopTreeAction is
    ForestryAxe 8.0 and ISClimbSheetRopeAction ClimbRope 8.0): each needs a world object or a tool the harness has no
    command to stage or queue, so this candidate is NOT RUN (a reading, not a refusal: it would need a harness change).
  melee: RCON createhorde 1 admin, then attack.melee 20 at the nearest zombie within 2 tiles (the client's
    DoAttack; a BaseballBat is equipped when the hands are empty), up to 3 windows; the server's current state polled
    through witness.chain getCurrentState while it swings; the writer's swing test is
    isCurrentState(SwipeStatePlayer.instance()) on the server's copy of the player.

THE LEGS (all at speed 1, a game minute 0.625 s): G_MEAL a Mixed650 at the start (HUNGER off the cap, so the acute
factor shows in the written HUNGER); IDLE 20 game min; SQUATS one set asking 20 min, then 40 min of rest; BURPEES one
set asking 20 min, then 45 min of rest; DECAY lua.setpath of NutritionRevamp.server.store.records.admin.satiety.S to
1 at rest, then 60 min; MELEE up to 3 windows, then 30 min of rest. About 6.5 game hours, about 250 s of wall.

PREDICTIONS (graded in `verdicts`): VIGOUR SQUATS not vigorous (billed 3.0-4.0, never 6.0: #2984, #3000); BURPEES
unmeasured (None: any reading is the reading; the rate's approach toward 9.0 is unread on 42.21); MELEE unmeasured
(None: the server's swing state is unread). DECAY: every graded ring row's S within 1 % of 0.5^((t - t_e) / 0.15)
from the set (x29_exercise_lib.decay_reading): at +30 game min about 0.099, the acute factor about 0.931. REPLAY the
session's replay of live (sleep_allowed false, the activity events read off the ring, the setpath event) ok under
HUNGER 0.002, es 0.005, L 0.5 %; a vigorous rise from a swing would be live-only (the stand-in never swings): a
finding, not a failure of the replay. The exercise minutes may show HUNGER above the replay if vanilla's own
exercise hunger lands between the writer's minutes (a reading). STOPS, SODIUM, H1, RING, F, Z the engine's.

THE GRADING (after the run, by the committed testing/experiments/x29_grade.py gate into a staged folder
testing/artifacts/x29-gate-<date>/): the legs' readings; the decay against the half-life (1 %) and the replay; the
HUNGER factor live / no-acute replay against 1 - 0.7 S (1 %) on every uncapped row with S over 1e-3; the study
distance as readings against the oracle's 0.674 and -3.7 mm.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x29_exercise_lib as L   # noqa: E402

PROFILE = "x29-exercise"
PREFIX = "x291"
ARTIFACT = "gate-1.json"
STAGE_ROOT = "release/x29-exercise/NutritionRevamp"
STAGED_AT = "5244b4a"          # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
SESSION = ("Plan 11f Task 6 session 1: the vigour gate (squats, burpees, melee) and the decay leg of row 9, on the "
           "staged copy; one boot of " + PROFILE)
LEGS = [
    ("meal", "G_MEAL", L.MIX650),
    ("idle", "IDLE", 20.0),
    ("exercise", "SQUATS", "squats", 20.0, 40.0),
    ("exercise", "BURPEES", "burpees", 20.0, 45.0),
    ("setS", "DECAY", 1, 60.0),
    ("melee", "MELEE", 3, 30.0),
]
PRED = {
    "VIGOUR": {"SQUATS": False, "BURPEES": None, "MELEE": None},
    "DECAY": {"every graded row": "S within 1 % of 0.5^((t - t_e) / 0.15)", "S_30min": 0.099, "factor_30min": 0.931},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "STOPS": {"this session's legs": "done"}, "SODIUM": {"every chain day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
}


def scenario(S):
    S.run_gate(LEGS)


def grade(S, ring, rows_rep):
    L.gate_grade(S, ring, rows_rep, PRED)


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x291_gate.py", scenario,
              grade).run()
