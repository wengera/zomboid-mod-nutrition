"""x364-fast -- Plan 11g Task 8 session 4 (live): the energy class across a resting fast on the final deficit model
(BALANCE_SPAN 3970.55, the class held within ENERGY_BAND 0.01 on the server, every mirror carrying the held level as
body_energyLevel, ruling T7-7). One boot of profile x36-gut (fixture default, admin -debug, Nutrition false, DayLength
1, sleep off) on the STAGED copy of the tree at the final build (release/x36-gut, staged fresh from HEAD before the boot;
mod/ is never booted) plus TKX_StudyFoods by its path. Build 42.21.0. The engine is testing/experiments/x36_gut_lib.py
(frozen with x361's run). Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md
s5, B3-1/B3-2).

THE TASK 8 AMENDMENTS (copied in substance): the energy moodle across a fast, if the session budget allows: a short fast
that crosses level 1 shows the client level equal to the server's held level at each read (same-second pairs).

THE DESIGN, NAMED BEFORE THE RUN:
  The fresh fixture's admin eats nothing and drinks nothing (no container carried; the server's autodrink flag false;
  THIRST rises toward the writer's cap, as in x261); awake (sleep off). From the scenario's start the world runs at
  speed 5 to END_AGE (about 32 game hours of fast from the boot's 11:00), an energy pair (x36_gut_lib.energy_pair: the
  client's mirror level, mirror state, moodle level, view class and received count in one tick, at once the server's
  last push signature and push count in one tick, then the record's es) every PAIR_M game minutes; the ring carries the
  server's held level every minute (the signature's energy digit).
  ENERGY_AT (NR_Kernel_View.lua): level 1 at es 1.10, 2 at 1.25. A fresh record's trailing window starts empty (no
  prior intake), so the fast's es rises from the record's first-sight state; the crossing hour is a reading (the 70 kg
  man's resting fast from balance crosses level 1 at 18.1 h, test_a_sedentary_fast_never_steps_an_energy_level_down).
PREDICTIONS (graded in `verdicts`: as_predicted / falsified / unmeasured):
  LEVEL    the server's held level reaches 1 within the session, and never steps down on the ring (a resting fast,
           ruling T7-2).
  CLIENT   every energy pair's client level equals the server's held level, or lags it by the push gap (60 s of wall
           clock plus 5 s slack after the server's change, showing the level held before; energy_pairs_grade); every
           pair within one wall second; the client's moodle level and view class equal its mirror level (a reading).
  REPLAY   the whole session's replay diff ok under DEFAULT_TOL (HUNGER 0.002, es 0.005, L 0.5 %).
  GRADE_DIFF  the whole session under TOL_GRADE.
  H1, RING, F, Z  the engine's.
READINGS: the world age and the fast's hours at the server's level-1 change (ring and pairs); es at the end; the
  replay's level-1 crossing (es over ENERGY_AT[1] on the replay rows) beside the live one.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x36_gut_lib as L   # noqa: E402

PROFILE = "x36-gut"
PREFIX = "x364"
ARTIFACT = "fast.json"
STAGE_ROOT = "release/x36-gut/NutritionRevamp"
STAGED_AT = "7093079b"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 700.0
END_AGE = 36.0                 # 19:00 on day 1
PAIR_M = 15.0
LEVEL1 = 1.10                  # NR_Kernel_View.lua K.view.ENERGY_AT[1]
SESSION = ("Plan 11g Task 8 session 4: a resting fast at speed 5 with energy pairs every 15 game minutes, on the staged "
           "copy; one boot of " + PROFILE)
PRED = {
    "LEVEL": {"server held level": "reaches 1; never steps down on the ring"},
    "CLIENT": {"energy pairs": "client level equal to the server's held level or within the push gap; pairs within 1 s"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "GRADE_DIFF": {"whole session": "ok under TOL_GRADE"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
}


def scenario(S):
    X = S.out["phases"]["X"] = {}
    X["start_age"] = S.age("X_a0")
    S.energy_pair("E_start")
    S.fast("X_fast")
    nxt = (X["start_age"] or 0.0) + PAIR_M / 60.0
    while True:
        S.check()
        a = S.age("X_a")
        if a is not None and a >= END_AGE:
            break
        if a is not None and a >= nxt:
            S.energy_pair(f"E_{a:.3f}")
            nxt = a + PAIR_M / 60.0
        time.sleep(L.POLL_S)
    S.one("X_end_one")
    S.energy_pair("E_end")
    X["done"] = True


def grade(S, ring, rows_rep):
    R, V = S.out["readings"], S.out["verdicts"]
    rl = L.ring_levels(ring)
    R["ring_levels"] = rl
    first1 = next((c for c in rl["changes"] if c["to"] >= 1), None)
    start = (S.out["phases"].get("X") or {}).get("start_age")
    R["level1"] = {"ring_change": first1, "fast_h_from_scenario_start":
                   (first1["age"] - start) if (first1 and start is not None) else None}
    rep1 = next((r for r in rows_rep if L.num(r.get("body.energyState")) is not None
                 and r["body.energyState"] >= LEVEL1), None)
    live1 = next((r for r in ring if L.num(r.get("body.energyState")) is not None
                  and r["body.energyState"] >= LEVEL1), None)
    R["es_crossing"] = {"live_age": live1.get("age") if live1 else None, "replay_age": rep1.get("age") if rep1 else None}
    R["es_end"] = ring[-1].get("body.energyState") if ring else None
    reached = first1 is not None or any((p.get("server_level") or 0) >= 1 for p in S.epairs)
    V["LEVEL"] = {"predicted": PRED["LEVEL"], "observed": {"reached_1": reached, "steps_down": rl["steps_down"],
                                                          "changes": rl["changes"], "last": rl["last"]},
                  "verdict": "as_predicted" if (reached and rl["steps_down"] == 0) else "falsified"}
    eg = L.energy_pairs_grade(S.epairs)
    R["energy_pairs"] = eg
    agree = [p for p in S.epairs if p.get("client_mirror_level") is not None]
    R["client_views"] = {"pairs": len(S.epairs),
                         "moodle_eq_mirror": sum(1 for p in agree if p.get("client_moodle") == p.get("client_mirror_level")),
                         "view_eq_mirror": sum(1 for p in agree if p.get("client_view") == p.get("client_mirror_level")),
                         "with_mirror_level": len(agree)}
    V["CLIENT"] = {"predicted": PRED["CLIENT"],
                   "observed": {k: eg.get(k) for k in ("equal", "lag", "mismatch", "changes", "max_wall_gap",
                                                       "server_levels", "steps_down")},
                   "verdict": ("unmeasured" if not S.epairs else "as_predicted" if eg["ok"] and reached
                               else "falsified")}


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x364_fast.py",
              scenario, grade).run()
