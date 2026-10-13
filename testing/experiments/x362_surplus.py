"""x362-surplus -- Plan 11g Task 8 session 2 (live): a surplus day of three large meals on the final satiety and deficit
model. One boot of profile x36-gut (fixture default, admin -debug, Nutrition false, DayLength 1, sleep off) on the STAGED
copy of the tree at the final build (release/x36-gut, staged fresh from HEAD before the boot; mod/ is never booted)
plus TKX_StudyFoods by its path. Build 42.21.0. The engine is testing/experiments/x36_gut_lib.py (frozen with x361's
run). Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE TASK 8 AMENDMENTS (copied in substance): three large meals; grade the day's mean HUNGER against the replay, and
report the distance to Karl's well-fed figure as a reading (ruling 8-R).

THE DESIGN, NAMED BEFORE THE RUN:
  The live body is the default fixture's admin, awake all day and night (sleep off, #2961; Karl's subjects slept 4 h
  on the SUSOPS nights: named). Drinking to thirst by the engine's own auto-drink (#2770) from a server-side canteen
  (Base.CanteenMilitaryFull) refilled to 0.9 L at the session's start, after every meal and at 23:00 day 0 and 03:00
  day 1; the replay's sips are the ring's fluids.autoDrop rows as the tool's autodrop kind (ruling T9-4).
  Meals at Karl's assumed clock (07:00, 12:00, 18:00; test_replay_live_energy.py KARL_MEALS): day 0 at 12:00 and
  18:00 maintenance-sized (a third of the tool's maintenance, NR_R.maint, read once off the live body at the first
  meal), day 1 at 07:00, 12:00 and 18:00 surplus-sized (KARL_RATIO = 22.7 / 10.6 MJ/d, S1325 Table 1's BAL over REST,
  times the maintenance third); whole Mixed650, Mixed217 and Unit50 portions, the miss carried; each meal eaten at the
  slow clock; speed 5 between stops (speed 1 for STOP_LEAD_H before each). The session ends at 22:30 on day 1.
  The day read: day 1 from 07:00 to 22:00 (Karl's waking day), the time-weighted mean HUNGER (x36_gut_lib.day_reading)
  and its value at Karl's eight sampling points (the row before each surplus meal's first landing and its last
  landing row; 08:00 and 09:04, the study's walk window, ASSUMED clock).
PREDICTIONS (graded in `verdicts`: as_predicted / falsified / unmeasured):
  DAYMEAN  the live day mean HUNGER within 0.002 of the replay's (the 11f HUNGER tolerance on the mean), and the
           eight-point mean within 0.002.
  REPLAY   the whole session's replay diff ok under DEFAULT_TOL (HUNGER 0.002, es 0.005, L 0.5 %).
  GRADE_DIFF  the whole session under TOL_GRADE.
  STOPS    every meal stop done and landed, every refill read back.
  SODIUM   hyponatraemia grade 0 every day.
  H1, RING, F, Z  the engine's.
READINGS (never graded here; x36_grade.py emits them): the REST arm (ruling 11f-3: the surplus meals' landings given
  maintenance portions on the live clock and record) and the day's change against it in % (the time-weighted mean and
  the eight points), against Karl's BAL -55 % (S1325; S1892's band -64 to -46): Karl's arm also worked 20 MJ a day,
  this body rests (named, a reading only); es at 22:00; the M and fill series over the day.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x36_gut_lib as L   # noqa: E402

PROFILE = "x36-gut"
PREFIX = "x362"
ARTIFACT = "surplus.json"
STAGE_ROOT = "release/x36-gut/NutritionRevamp"
STAGED_AT = "7093079b"         # the mod tree's last commit; the copy is staged fresh from HEAD before the boot
BUDGET_S = 780.0
at = L.at
SCHEDULE = [(at(0, 12.0), "maint", "D0_12"), (at(0, 18.0), "maint", "D0_18"), (at(0, 23.0), "refill", "R0_23"),
            (at(1, 3.0), "refill", "R1_03"), (at(1, 7.0), "surplus", "S1_07", L.KARL_RATIO),
            (at(1, 12.0), "surplus", "S1_12", L.KARL_RATIO), (at(1, 18.0), "surplus", "S1_18", L.KARL_RATIO)]
END_AGE = at(1, 22.5)
DAY = (at(1, 7.0), at(1, 22.0))
WALK_AGES = (at(1, 8.0), at(1, 9.0 + 4 / 60.0))
SURPLUS = ("S1_07", "S1_12", "S1_18")
MEAN_TOL = 0.002
SESSION = ("Plan 11g Task 8 session 2: maintenance meals on day 0 and three surplus meals on day 1 at Karl's ratio, "
           "on the staged copy; one boot of " + PROFILE)
PRED = {
    "DAYMEAN": {"day 1 07:00-22:00": "live mean HUNGER and the eight-point mean within 0.002 of the replay's"},
    "REPLAY": {"whole session diff": "ok (HUNGER 0.002, es 0.005, L 0.5 %)"},
    "GRADE_DIFF": {"whole session": "ok under TOL_GRADE"},
    "STOPS": {"the session's stops": "every stop done, none missed, every eat landed, every refill read back"},
    "SODIUM": {"every day": "hyponatraemia grade 0"},
    "H1": {"ring record paths": "resolved"}, "RING": {"pages": "all read, errors 0"},
    "F": {"departure flush": "within 90 s"}, "Z": {"mod error lines": 0, "admin parked": False},
}


def karl_points(ring, eats, meals=SURPLUS, walk=WALK_AGES):
    """Karl's eight sampling ages off the ring: per surplus meal the age of the ring row before its first landing row
    and its last landing row's age; then the walk window's two ages. Returns (ages, notes)."""
    ages, notes = [], []
    by_s = {r["s"]: r for r in ring if r.get("s") is not None}
    for m in meals:
        ss = sorted(e["ring_s"] for e in eats if e.get("stop") == m and e.get("ring_s") is not None)
        if not ss:
            notes.append(f"{m}: no landing row")
            continue
        prev = by_s.get(ss[0] - 1)
        ages.append(prev["age"] if prev else by_s[ss[0]]["age"])
        ages.append(by_s[ss[-1]]["age"])
    ages += list(walk)
    return sorted(ages), notes


def scenario(S):
    S.run_stops(SCHEDULE, END_AGE)


def grade(S, ring, rows_rep):
    R, V = S.out["readings"], S.out["verdicts"]
    ages, notes = karl_points(ring, S.eats)
    live = L.day_reading(ring, DAY[0], DAY[1], ages)
    rep = L.day_reading(rows_rep, DAY[0], DAY[1], ages)
    R["day"] = {"live": live, "replay": rep, "notes": notes}
    d1 = (live["mean"] - rep["mean"]) if (live["mean"] is not None and rep["mean"] is not None) else None
    d2 = (live["points_mean"] - rep["points_mean"]) if (live["points_mean"] is not None and
                                                        rep["points_mean"] is not None) else None
    ok = d1 is not None and d2 is not None and abs(d1) <= MEAN_TOL and abs(d2) <= MEAN_TOL and len(ages) == 8
    V["DAYMEAN"] = {"predicted": PRED["DAYMEAN"], "observed": {"mean_d": d1, "points_mean_d": d2, "points": len(ages)},
                    "verdict": ("unmeasured" if d1 is None else "as_predicted" if ok else "falsified")}
    R["fluid_days"] = L.fluid_days(ring, L.autodrop_events(ring))
    stops = S.stops
    bad = [st["label"] for st in stops if not all(st.get("landed") or [True])]
    nofill = [st["label"] for st in stops if st.get("kind") == "refill" and not st.get("fill_ok")]
    X = S.out["phases"].get("X") or {}
    V["STOPS"] = {"predicted": PRED["STOPS"],
                  "observed": {"done": [st["label"] for st in stops], "missed": X.get("missed"), "late": X.get("late"),
                               "not_landed": bad, "fill_failed": nofill, "scenario_done": X.get("done"),
                               "budget_stop": S.out.get("budget_stop")},
                  "verdict": "as_predicted" if (X.get("done") and not X.get("missed") and not bad and not nofill)
                  else "falsified"}
    G = {d: {"grade_max": v.get("grade_max"), "naPlasma_min": v.get("naPlasma_min")} for d, v in R["fluid_days"].items()}
    V["SODIUM"] = {"predicted": PRED["SODIUM"], "observed": G,
                   "verdict": "as_predicted" if G and all(x.get("grade_max") == 0 for x in G.values()) else "falsified"}
    es = L.row_at(ring, DAY[1])
    R["es_at_22"] = es.get("body.energyState") if es else None


if __name__ == "__main__":
    L.Session(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, STAGE_ROOT, STAGED_AT, BUDGET_S, "x362_surplus.py",
              scenario, grade, canteen=True).run()
