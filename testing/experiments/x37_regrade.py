"""x37_regrade -- the regrade of Plan 11h Task 4 (x371, x372), written after the runs and committed before it ran: an
ANALYSIS script, not a driver (it boots nothing); x37_grade.py stays as committed (the x30/x34/x36 regrade precedent).
Its output is a DERIVED artifact folder.

    python testing/experiments/x37_regrade.py [--out testing/artifacts/x37-regrade-YYYYMMDD]

Two grade defects, both of a precondition the committed grade did not test, and a reading the grade did not emit:
  R1  RECORD read during the set. x37_fitness_lib.fit_poll reads the current exercise first and the wrapper's state
      three bus round trips later (about 1.5 game minutes at DayLength 4); on a set the flag showed on only one poll
      (x371's squats, x372's barbellcurl) that state read came after the set's serverStop, whose own counter had already
      risen in the same read (stops above the set's `before`), so the "during" read was not during the set. R1 counts a
      poll's record only when the poll's stops counter still equals the one before the set; a set with no such poll is
      unmeasured by poll and stands on its ring rows alone (the record on every flagged ring row, sampled before that
      minute's drain, the committed grade's second half).
  R2  END_MOVE's precondition. The harness's player.stop clears the client's Lua queue (ISTimedActionQueue:clearQueue),
      whose cancelQueue force-cancels only actions not yet started; a started ISFitnessAction is wiped from the table
      and never stopped, so the set never ended at the server and the movement end case was not reached. R2 marks
      END_MOVE unmeasured and emits the reading of what was measured instead: the flagged rows after the stop, their
      bills, the moving flag after the walk, and whether the set outlived its own asked timer.
  R3  TIMER_END (a reading the grade's observations hold but no verdict names): every set ended by its own timer, the
      wrapper's stops counter rose by one by the clear, and the record read nil at the clear and REST_M later; so no
      timer-ended set left a stale record (STALE has no row to grade: unmeasured, not falsified).
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
import x37_fitness_lib as L  # noqa: E402
import x37_grade as G  # noqa: E402


def record_polls(st):
    """R1: the polls that showed the flag while the wrapper's stops counter still equalled the one before the set."""
    b = L.num((st.get("before") or {}).get("stops"))
    out = []
    for p in st.get("polls") or []:
        if not p.get("on"):
            continue
        out.append({"age": p.get("age"), "exeType": p.get("exeType"), "stops": p.get("stops"),
                    "before_stop": b is not None and L.num(p.get("stops")) == b})
    return out


def r1(sets, ring):
    rows = []
    for st in sets:
        x = L.set_reading(ring, st)
        ps = record_polls(st)
        good = [p for p in ps if p["before_stop"]]
        rows.append({"label": st.get("label"), "exercise": st.get("exercise"), "polls_on": len(ps),
                     "polls_before_stop": len(good), "poll_records": sorted({str(p["exeType"]) for p in good}),
                     "poll_ok": (all(p["exeType"] == st.get("exercise") for p in good) if good else None),
                     "types_on_flagged": x.get("types_on_flagged"), "flagged_rows": x.get("flagged"),
                     "ring_ok": x.get("types_on_flagged") == [st.get("exercise")]})
    ok = bool(rows) and all(r["ring_ok"] and r["poll_ok"] is not False for r in rows)
    return {"sets": rows, "unmeasured_by_poll": [r["label"] for r in rows if r["poll_ok"] is None],
            "verdict": "as_predicted" if ok else "falsified"}


def r2(sets, ring):
    out = []
    for st in sets:
        if not st.get("stopped"):
            continue
        a_stop = L.num(st.get("stop_age"))
        first = L.num(st.get("first_on_age"))
        on = [r for r in ring if L.num(r.get("age")) is not None and r.get("s") is not None]
        after = [r for r in on if a_stop is not None and r["age"] > a_stop]
        by_s = {r["s"]: r for r in on}
        flagged_after = [r for r in after if L.flagged(r)]
        bills = [L.num((by_s.get(r["s"] + 1) or {}).get(L.MET)) for r in flagged_after if (r["s"] + 1) in by_s]
        online = [r for r in on if r.get("on") is True]
        last_flag = max((r["age"] for r in on if L.flagged(r)), default=None)
        out.append({"label": st.get("label"), "exercise": st.get("exercise"), "requested_min": st.get("requested_min"),
                    "first_on_age": first, "stop_age": a_stop, "stop_reply": st.get("stop"), "walk": st.get("walk"),
                    "cap_stop": st.get("cap_stop"), "ended": st.get("ended"), "clear_age": st.get("clear_age"),
                    "rows_after_stop": len(after), "flagged_rows_after_stop": len(flagged_after),
                    "bills_after_stop_hist": L._hist(bills), "type_met": L.exercise_met(st["exercise"])[0],
                    "moving_rows_after_stop": sum(1 for r in after if r.get("moving") is True),
                    "last_flagged_age": last_flag, "last_online_age": online[-1]["age"] if online else None,
                    "flag_minutes_after_stop": ((last_flag - a_stop) * 60) if (last_flag and a_stop) else None,
                    "outlived_own_timer": (last_flag is not None and first is not None
                                           and last_flag > first + (st.get("requested_min") or 0) / 60.0),
                    "record_at_clear_read": (st.get("at_clear") or {}).get("exeType"),
                    "record_after_rest": (st.get("after_rest") or {}).get("exeType"),
                    "fallbacks_delta": L.num((st.get("after_rest") or {}).get("fallbacks"))
                    - L.num((st.get("before") or {}).get("fallbacks"))})
    return {"stopped_sets": out, "verdict": "unmeasured",
            "why": "the harness stop (clearQueue) never stopped the started set: the movement end case was not reached"}


def r3(sets):
    rows = []
    for st in sets:
        e = L.end_case(st)
        if e["how"] != "timer":
            continue
        rows.append({k: e.get(k) for k in ("label", "exercise", "ran_min", "stops_delta_at_clear", "record_at_clear",
                                           "record_after_rest", "fallbacks_delta_after_rest")})
    ok = bool(rows) and all(r["stops_delta_at_clear"] == 1 and r["record_at_clear"] is None
                            and r["record_after_rest"] is None for r in rows)
    return {"sets": rows, "n": len(rows), "verdict": "as_predicted" if ok else "falsified"}


def regrade(pre):
    run = G.folder(pre)
    if run is None:
        return {"skipped": "no artifact folder"}
    doc = G.read(run, G.DOCS[pre])
    ring, _ = G.replay(run, doc, G.read(run, "events.json"))
    sets = doc.get("sets") or []
    return {"run": os.path.basename(run), "R1_RECORD": r1(sets, ring), "R2_END_MOVE": r2(sets, ring),
            "R3_TIMER_END": r3(sets),
            "flagged_rows_per_set": [{"label": st.get("label"), "flagged": L.set_reading(ring, st).get("flagged"),
                                      "requested_min": st.get("requested_min")} for st in sets]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(G.ART, "x37-regrade-" + datetime.date.today().strftime("%Y%m%d")))
    a = ap.parse_args(argv)
    res = {"script": "testing/experiments/x37_regrade.py", "commit": G._git("rev-parse", "--short", "HEAD"),
           "regrade_commit": G._git("log", "-1", "--format=%h", "--", "testing/experiments/x37_regrade.py"),
           "sessions": {pre: regrade(pre) for pre in G.DOCS}}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "regrade.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n")
    print(json.dumps({pre: {k: (v.get("verdict") if isinstance(v, dict) else None) for k, v in s.items()}
                      for pre, s in res["sessions"].items()}, indent=1))
    print("wrote", os.path.join(a.out, "regrade.json"))


if __name__ == "__main__":
    main()
