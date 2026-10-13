"""x36_regrade -- the regrade of Plan 11g Task 8's surplus day (x362), written AFTER the runs, for one defect in the
GRADE, not in the readings (the x30_regrade and x34_regrade precedent: x36_grade.py and the x362 driver stay as
committed; their outputs stay staged beside this one's).

    python testing/experiments/x36_regrade.py [--out testing/artifacts/x36-regrade-YYYYMMDD]

R1 (Karl's eight points): x362_surplus.karl_points takes each surplus meal's "after" point at the meal's LAST LANDING
  ring row. That row is an event row: the live ring row there reads vanilla's own eat (the food's HungerChange applied
  to HUNGER between the writer's writes), which the replay does not model and the tool's diff never grades (its
  `between` class). So x362's DAYMEAN compared the live and replay HUNGER at three ungraded rows (live 0.026, 0.024,
  0.025 against the replay's 0.046, 0.044, 0.045), and the eight-point mean missed by -0.0074 for that reason alone;
  and x36_grade.py's Karl readings in the points form carry the same three rows. The fix: the "after" point is the
  first ring row after the meal's last landing row, the first row the writer has written since the meal (a graded row:
  the tool's diff compares it). The time-weighted mean is unchanged (it is no point read; the event rows weigh one
  ring row each, about a minute of the fifteen-hour window). Everything else is x36_grade.py's: the replay of live at
  HEAD, the REST arm (rest_arm_events, ruling 11f-3), the change against REST in %, against Karl's BAL -55 % (S1325)
  and S1892's band -64 to -46.
Emitted: the corrected eight ages; the live, replay and REST-arm day readings on them; DAYMEAN re-graded (the live mean
  and the eight-point mean within 0.002 of the replay's); the Karl change in both forms (replay and live against REST);
  and, for the record, the three event rows' live and replay HUNGER that R1 names.
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import x36_grade as G  # noqa: E402
import x36_gut_lib as L  # noqa: E402
import x362_surplus as D  # noqa: E402

MEAN_TOL = D.MEAN_TOL


def karl_points_r1(ring, eats, meals=D.SURPLUS, walk=D.WALK_AGES):
    """Karl's eight ages with R1's fix: per surplus meal the ring row before its first landing row and the first ring
    row after its last landing row; then the walk window's two ages. Returns (ages, the event rows R1 names, notes)."""
    ages, ev_rows, notes = [], [], []
    by_s = {r["s"]: r for r in ring if r.get("s") is not None}
    for m in meals:
        ss = sorted(e["ring_s"] for e in eats if e.get("stop") == m and e.get("ring_s") is not None)
        if not ss:
            notes.append(f"{m}: no landing row")
            continue
        prev, nxt = by_s.get(ss[0] - 1), by_s.get(ss[-1] + 1)
        ages.append(prev["age"] if prev else by_s[ss[0]]["age"])
        if nxt is None:
            notes.append(f"{m}: no ring row after the last landing row")
            continue
        ages.append(nxt["age"])
        ev_rows.append({"meal": m, "last_landing_s": ss[-1], "age": by_s[ss[-1]]["age"]})
    ages += list(walk)
    return sorted(ages), ev_rows, notes


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(G.ART, "x36-regrade-" + datetime.date.today().strftime("%Y%m%d")))
    a = ap.parse_args(argv)
    S = G.Sess("x362")
    eats = S.doc.get("eats") or []
    ages, ev_rows, notes = karl_points_r1(S.ring, eats)
    rep_by = {r["s"]: r for r in S.rows}
    live_by = {r["s"]: r for r in S.ring}
    for x in ev_rows:
        lr, rr = live_by.get(x["last_landing_s"]) or {}, rep_by.get(x["last_landing_s"]) or {}
        x.update({"live_HUNGER": lr.get("HUNGER"), "replay_HUNGER": rr.get("HUNGER"), "replay_between": rr.get("between")})
    live = L.day_reading(S.ring, D.DAY[0], D.DAY[1], ages)
    rep = L.day_reading(S.rows, D.DAY[0], D.DAY[1], ages)
    d1 = (live["mean"] - rep["mean"]) if (live["mean"] is not None and rep["mean"] is not None) else None
    d2 = (live["points_mean"] - rep["points_mean"]) if (live["points_mean"] is not None and
                                                        rep["points_mean"] is not None) else None
    ok = d1 is not None and d2 is not None and abs(d1) <= MEAN_TOL and abs(d2) <= MEAN_TOL and len(ages) == 8
    out = {"script": "testing/experiments/x36_regrade.py", "commit": G._git("rev-parse", "--short", "HEAD"),
           "run": os.path.basename(S.dir), "r1_event_rows": ev_rows, "ages": ages, "notes": notes,
           "day": {"live": live, "replay": rep},
           "DAYMEAN": {"predicted": "live mean HUNGER and the eight-point mean within 0.002 of the replay's",
                       "observed": {"mean_d": d1, "points_mean_d": d2, "points": len(ages)},
                       "verdict": ("unmeasured" if d1 is None else "as_predicted" if ok else "falsified")}}
    maint = L.num(L.g(S.doc, "readings", "maint_kcal"))
    if maint is not None:
        ev, meals = L.rest_arm_events(S.events, eats, set(D.SURPLUS), maint / 3.0)
        rest_rows = S.replay(ev)
        rest = L.day_reading(rest_rows, D.DAY[0], D.DAY[1], ages)

        def pct(x, y):
            return 100.0 * (x / y - 1.0) if (x is not None and y not in (None, 0)) else None
        k = {"study_bal": L.KARL_BAL, "band": list(L.KARL_BAND),
             "replay_vs_rest_mean": pct(rep["mean"], rest["mean"]),
             "replay_vs_rest_points": pct(rep["points_mean"], rest["points_mean"]),
             "live_vs_rest_mean": pct(live["mean"], rest["mean"]),
             "live_vs_rest_points": pct(live["points_mean"], rest["points_mean"])}
        for key in list(k):
            if key.endswith(("_mean", "_points")) and key not in ("study_bal",):
                v = k[key]
                k[key + "_dist"] = (v - L.KARL_BAL) if v is not None else None
                k[key + "_in_band"] = (L.KARL_BAND[0] <= v <= L.KARL_BAND[1]) if v is not None else None
        out["rest"] = {"meals": meals, "day": rest, "karl": k}
    os.makedirs(a.out, exist_ok=True)
    p = os.path.join(a.out, "regrade.json")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    print(p)
    print(json.dumps({"DAYMEAN": out["DAYMEAN"], "karl": (out.get("rest") or {}).get("karl")}, indent=1))


if __name__ == "__main__":
    main()
