"""x372-fitness -- Plan 11h Task 4 session 2 (live): one set each of barbellcurl, dumbbellpress and bicepscurl, each
ended by its own timer, then the movement end case (a squats set asked for 20 game minutes, stopped 3 game minutes after
its flag showed by player.stop then player.walk), on the final build of Plan 11h (C-2: each Fitness exercise billed at its own Compendium MET from the type
NR_Server_Fitness records at the set's start). One boot of profile x37-fitness (fixture default, admin -debug, Nutrition
false, DayLength 4 -- the fixture's own day length, 1 h 30 min of wall clock a game day, a game minute 3.75 s at speed 1
-- sleep off) on the STAGED copy of the tree at the final build (release/x37-fitness, staged fresh from HEAD before the
boot; mod/ is never booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine is
testing/experiments/x37_fitness_lib.py (frozen with x371's run). Written BEFORE the boot with every prediction in it and
never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE TASK 4 AMENDMENTS (copied in substance): all seven exercises, one set of each of about 3-5 game minutes, through the
harness's exercise.do; each set reads the wrapper's record (lua.read of NutritionRevamp.server.fitness.exeType.admin)
during the set and after it ends, the billed MET on every ring minute (which must equal the table), exeFallbacks (which
must not rise for a known type), live against the replay within the 11f tolerances, and the client's moodles in
same-second pairs; two end cases: a set ended by its own timer (x371's four and this session's three) and one
stopped by movement (here).
A stale record is acceptable only if no later minute bills it. DayLength: the shipping (fixture) day length if the
session budget allows; it does here (named: 4).

THE DESIGN, NAMED BEFORE THE RUN:
  The fresh fixture's admin, awake, eats and drinks nothing (the sessions last under two game hours). From the
  scenario's start the world runs at speed 1. A moodle pair (x37_fitness_lib.moodle_pair) at the start; then for each
  exercise in SETS, in order (the heavy one last): the server's endurance moodle is read and, above 1, the world runs
  at speed 5 until it is at most 1 (ensure_rested); the set is asked for ASK_M game minutes (exercise.do) and followed
  by fit_poll until the server's flag clears (x35's sets ran 1.2-2.5 times their ask: followed OVERRUN_M past it); a
  moodle pair once the flag and the record show, the wrapper's state at the clear, a moodle pair, REST_M game minutes
  at speed 1, the state again. A set refused (no flag within SET_START_CAP_M) is rested and asked once more. Then the
  movement case (STOP): rested, a squats set asked for 20 game minutes, and 3 game minutes after the flag first shows
  player.stop (the client queue's cancel: the action's forceStop, the route vanilla's movement press takes in
  ISFitnessAction.update; the harness has no movement key press, so the cancel stands for it, named) then player.walk
  WALK_DX tiles; followed to the clear, REST_M at speed 1 (the walk then stopped by player.stop), the state again.
  Then a final moodle pair. NO ITEM IS CARRIED: the barbell and dumbbell exercises are asked with no Base.BarBell or
  Base.DumbBell in the inventory (the UI checks the item, ISFitnessUI; ISFitnessAction checks only the endurance moodle
  and the vehicle), so the inventory weight, which the mod's load factor reads, does not move (named departure).
PREDICTIONS (graded in `verdicts`: as_predicted / falsified / unmeasured):
  SETS      every set of SETS starts and ends by its own timer (the flag clears with no stop asked).
  END_MOVE  the stopped set: the flag clears after the stop; the wrapper's stops counter rises by one by the clear
            (the cancel reaches serverStop) and the record reads nil at the clear and REST_M later; no drain after its
            last flagged row bills squats' MET as an exercise (STALE's test over its rows).
  RECORD    for each set, the record read during the set equals the asked type, and every flagged ring row carries it
            (the wrapper records self.exeDataType at serverStart).
  BILLED    every flagged drain bills the asked type's EXERCISE_MET (squats 3.0, pushups 3.8, situp 3.8, burpees 7.5),
            at most one off per flagged run's edge (the ring samples a few ticks before the drain, x35's skew rule);
            BILLED_EXACT, a reading, counts every off drain. (The squats set of the movement case too.)
  FALLBACKS exeFallbacks does not rise over any set.
  STALE     a record left after a timer-ended set (completion calls no serverStop, Task 2 review info 4) bills nothing:
            every drain after a set's last flagged row that still carries the record bills what the flag_only replay
            arm bills (the record cleared off the flag); every set here, the stopped one too.
  MET_REPLAY the billed MET live equals the replay's on every row (the replay given the ring's recorded type).
  REPLAY    the whole session's replay diff ok under DEFAULT_TOL (HUNGER 0.002, es 0.005, L 0.5 %).
  GRADE_DIFF the whole session under TOL_GRADE (L, epoc, trail.c.ex 0.5 % floor 1; body.met exact).
  MOODLES   every NR moodle class on the client equals the server's held class (the push signature's digits) or lags
            a change by the push gap (60 s of wall clock plus 5 s); every pair within one wall second. The vanilla
            moodles in the same pairs are a reading.
  H1, RING, F, Z  the engine's.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x37_fitness_lib as L   # noqa: E402

PROFILE = "x37-fitness"
PREFIX = "x372"
ARTIFACT = "fitness-2.json"
STAGE_ROOT = "release/x37-fitness/NutritionRevamp"
STAGED_AT = "328ffe22"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 660.0
ASK_M = 3
SETS = ("barbellcurl", "dumbbellpress", "bicepscurl")
STOP = ("squats", 20, 3.0)     # the movement case: (type, asked game minutes, game minutes of flag before the stop)
SESSION = ("Plan 11h Task 4 session 2: one timer-ended set each of barbellcurl, dumbbellpress and bicepscurl, then a "
           "squats set stopped by player.stop and player.walk, at speed 1, DayLength 4, on the staged copy; one boot "
           "of " + PROFILE)
PRED = {
    "SETS": {"sets": list(SETS), "end": "each by its own timer"},
    "END_MOVE": {"stopped set": "flag clears; stops +1 by the clear; record nil at the clear and after the rest"},
    "RECORD": {"record": "the asked type during the set and on every flagged ring row"},
    "BILLED": {"flagged drains": "the asked type's EXERCISE_MET, at most one off per run edge"},
    "FALLBACKS": {"exeFallbacks": "no rise over any set"},
    "STALE": {"stale record": "bills nothing (equal to the flag_only arm on every stale drain)"},
    "MET_REPLAY": {"billed MET": "live equals the replay on every row"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "GRADE_DIFF": {"whole session": "ok under TOL_GRADE"},
    "MOODLES": {"NR moodle pairs": "equal or within the push gap; pairs within 1 s"},
    "H1": {"ring record paths": "resolved (body.epoc optional before the first set)"},
    "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
}


def scenario(S):
    X = S.out["phases"]["X"] = {}
    X["start_age"] = S.age("X_a0")
    S.one("X_one")
    S.moodle_pair("P_start")
    for i, name in enumerate(SETS):
        S.check()
        S.ensure_rested(f"R{i}")
        st = S.run_set(name, ASK_M, f"S{i}_{name}")
        if not st["started"]:
            S.ensure_rested(f"R{i}b")
            S.run_set(name, ASK_M, f"S{i}b_{name}")
    if STOP is not None:
        S.ensure_rested("RM")
        S.run_set(STOP[0], STOP[1], "M_" + STOP[0], stop_after_m=STOP[2])
    S.moodle_pair("P_final")
    X["done"] = True


def grade(S, ring, rows_rep, rows_flag):
    R, V = S.out["readings"], S.out["verdicts"]
    gs = L.grade_sets(S.sets, ring, rows_rep, rows_flag)
    R["sets"] = gs["sets"]
    R["met_live_vs_replay"] = gs.get("met_live_vs_replay")
    R["met_live_vs_flag_only"] = gs.get("met_live_vs_flag_only")
    R["stale_rows_vs_flag_only"] = gs.get("stale_rows_vs_flag_only")
    ends = [x["end"] for x in gs["sets"]]
    R["end_cases"] = ends
    timer = [x for x in gs["sets"] if x["end"]["how"] == "timer"]
    asked = [x for x in gs["sets"] if x["end"]["how"] != "refused"]
    done = {x["exercise"] for x in timer}
    V["SETS"] = {"predicted": PRED["SETS"], "observed": [{k: e.get(k) for k in ("label", "exercise", "how", "ran_min")}
                                                         for e in ends],
                 "verdict": "as_predicted" if set(SETS) <= done else "falsified"}

    def per(key):
        return [{"label": x["label"], key: x.get(key)} for x in asked]
    V["RECORD"] = {"predicted": PRED["RECORD"],
                   "observed": [{"label": x["label"], "record_during": x["end"]["record_during"],
                                 "types_on_flagged": x.get("types_on_flagged")} for x in asked],
                   "verdict": ("unmeasured" if not asked else "as_predicted" if all(x["record_ok"] for x in asked)
                               else "falsified")}
    V["BILLED"] = {"predicted": PRED["BILLED"],
                   "observed": [{"label": x["label"], "table_met": x.get("asked_met"), "billed_hist": x.get("billed_hist"),
                                 "flagged_drains": len(x.get("bills") or []), "ok": x.get("billed_asked_ok"),
                                 "flag_runs": x.get("flag_runs")} for x in asked],
                   "verdict": ("unmeasured" if not asked else "as_predicted" if all(x["billed_ok_verdict"] for x in asked)
                               else "falsified")}
    V["BILLED_EXACT"] = {"predicted": "a reading", "observed": per("billed_all"),
                         "verdict": "as_predicted" if asked and all(x["billed_all"] for x in asked) else "falsified"}
    V["FALLBACKS"] = {"predicted": PRED["FALLBACKS"], "observed": per("fallbacks_delta"),
                      "verdict": ("unmeasured" if not asked else "as_predicted" if all(x["fallbacks_ok"] for x in asked)
                                  else "falsified")}
    st = gs.get("stale_rows_vs_flag_only") or {}
    V["STALE"] = {"predicted": PRED["STALE"],
                  "observed": {"stale_rows": [x.get("stale_rows") for x in asked],
                               "stale_billed_type_met": [x.get("stale_billed_type_met") for x in asked],
                               "vs_flag_only": {k: st.get(k) for k in ("n", "mismatches", "ok")}},
                  "verdict": ("unmeasured" if not st.get("n") else "as_predicted" if st.get("ok") else "falsified")}
    m = gs.get("met_live_vs_replay") or {}
    V["MET_REPLAY"] = {"predicted": PRED["MET_REPLAY"], "observed": {k: m.get(k) for k in ("n", "mismatches", "rows")},
                       "verdict": "as_predicted" if m.get("ok") else "falsified"}
    mv = [x for x in gs["sets"] if x["end"]["how"] == "stopped"]
    R["end_move"] = [x["end"] for x in mv]
    ok_mv = bool(mv) and all(e["end"].get("stops_delta_at_clear") == 1 and e["end"].get("record_at_clear") is None
                             and e["end"].get("record_after_rest") is None for e in mv)
    V["END_MOVE"] = {"predicted": PRED["END_MOVE"], "observed": R["end_move"],
                     "verdict": ("unmeasured" if not mv else "as_predicted" if ok_mv else "falsified")}
    mp = L.moodle_pairs_grade(S.mpairs)
    R["moodle_pairs"] = mp
    R["vanilla_pairs"] = L.vanilla_pairs_reading(S.mpairs)
    V["MOODLES"] = {"predicted": PRED["MOODLES"],
                    "observed": {k: mp.get(k) for k in ("pairs", "equal", "lag", "mismatch", "max_wall_gap")},
                    "verdict": ("unmeasured" if not S.mpairs else "as_predicted" if mp["ok"] else "falsified")}


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x372_fitness.py",
              scenario, grade).run()
