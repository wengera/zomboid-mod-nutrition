"""x37_grade -- the committed grade of Plan 11h Task 4 (one set of each of the seven Fitness exercises live, on the final
build of Plan 11h): an ANALYSIS script, not a driver (it boots nothing). Written and committed before the first boot of
the runs it grades; its output is a DERIVED artifact folder (ruling T4-3: every number a row may cite is emitted by a
committed script).

    python testing/experiments/x37_grade.py [--out testing/artifacts/x37-grade-YYYYMMDD]

The inputs are each session's artifact folder testing/artifacts/x37N-*/ (x371 fitness-1, x372 fitness-2; a session
that did not run is skipped, named): the driver's document, events.json, events-flag-only.json, start.json,
start-stats.json, player.json and the minute-ring pages. The tool is tools/replay_live.py at HEAD (sleep_allowed false,
the ring's own activity, the exercise type set from the ring by setpath events), the readings x37_fitness_lib's pure
functions.

Per session:
  REPLAY     the replay of live re-run with the ring's own recorded type (exetype_events) and the tool's diff
             (DEFAULT_TOL: HUNGER 0.002, es 0.005, L 0.5 %, the 11f tolerances) and diff_floor under TOL_GRADE (L, the
             after-burn pool and the exercise trail 0.5 % floor 1, the billed MET exact); its rows equal to the
             session's committed replay.json on HUNGER and body.met (a determinism check of the tool at HEAD);
  FLAG_ONLY  the counterfactual arm (the type set only on flagged rows) re-run;
  SETS       per set (the driver's document's `sets`): set_reading and end_case; RECORD (the record read during the
             set equals the asked type, and every flagged ring row carries it), BILLED (every flagged drain bills the
             asked type's MET; at most one off per flagged run's edge for the verdict, the exact count beside),
             FALLBACKS (exeFallbacks does not rise over a known type's set), STALE (the drains after a set's last flagged
             row that still carry its record bill what the flag_only arm bills: the stale record bills nothing);
  END        the two end cases: the sets ended by their own timer, and the set stopped by the movement case (player.stop
             then player.walk): how each ended, the record and the wrapper's stops at the clear and REST_M later;
  MOODLES    the NR moodle pairs re-graded (moodle_pairs_grade) and the vanilla moodles in the same pairs (a reading).
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
import replay_live as RL  # noqa: E402
import x37_fitness_lib as L  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
DOCS = {"x371": "fitness-1.json", "x372": "fitness-2.json"}


def _git(*a):
    import subprocess
    try:
        return subprocess.run(["git"] + list(a), cwd=REPO, capture_output=True, text=True).stdout.strip()
    except OSError:
        return None


def folder(pre):
    hits = sorted(d for d in os.listdir(ART) if d.startswith(pre + "-") and os.path.isdir(os.path.join(ART, d)))
    if not hits:
        return None
    if len(hits) != 1:
        raise SystemExit("expected one artifact folder for %s, found %r" % (pre, hits))
    return os.path.join(ART, hits[0])


def read(run, name):
    with open(os.path.join(run, name), encoding="utf-8") as fh:
        return json.load(fh)


def ring_files(doc):
    pages = (L.g(doc, "phases", "R", "pages") or []) + (L.g(doc, "phases", "D", "tail") or [])
    return [p.get("file") for p in pages if p.get("file")]


def replay(run, doc, events):
    start, stats, player = read(run, "start.json"), read(run, "start-stats.json"), read(run, "player.json")
    rr, rpaths = RL.load_ring([os.path.join(run, f) for f in ring_files(doc)])
    rows, _ = RL.replay_live(rr, events, start, paths=rpaths, user=L.USER, player=player, start_stats=stats,
                             sleep_allowed=L.SLEEP_ALLOWED)
    return rr, rows


def determinism(rows, committed):
    by = {r["s"]: r for r in committed.get("rows") or []}
    dh = dm = 0.0
    n = 0
    for r in rows:
        q = by.get(r["s"])
        if q is None:
            continue
        n += 1
        for f, acc in (("HUNGER", "h"), (L.MET, "m")):
            a, b = L.num(r.get(f)), L.num(q.get(f))
            if a is not None and b is not None:
                if acc == "h":
                    dh = max(dh, abs(a - b))
                else:
                    dm = max(dm, abs(a - b))
    return {"rows": n, "hunger_max_abs": dh, "met_max_abs": dm}


def grade_session(pre):
    run = folder(pre)
    if run is None:
        return {"skipped": "no artifact folder"}
    doc = read(run, DOCS[pre])
    out = {"run": os.path.basename(run), "doc": DOCS[pre]}
    events = read(run, "events.json")
    events_fo = read(run, "events-flag-only.json")
    ring, rows = replay(run, doc, events)
    _, rows_fo = replay(run, doc, events_fo)
    d = RL.diff(rows, ring)
    out["diff"] = {k: d.get(k) for k in ("fields", "classes", "ok")} | {"findings": d.get("findings", [])[:40],
                                                                       "findings_n": len(d.get("findings", []))}
    out["diff_grade"] = L.diff_floor(rows, ring, L.TOL_GRADE)
    out["determinism"] = determinism(rows, read(run, "replay.json"))
    out["determinism_flag_only"] = determinism(rows_fo, read(run, "replay-flag-only.json"))
    sets = doc.get("sets") or []
    gs = L.grade_sets(sets, ring, rows, rows_fo)
    out["sets"] = gs["sets"]
    out["met_live_vs_replay"] = gs.get("met_live_vs_replay")
    out["met_live_vs_flag_only"] = gs.get("met_live_vs_flag_only")
    out["stale_rows_vs_flag_only"] = gs.get("stale_rows_vs_flag_only")
    out["table"] = [{"label": x["label"], "exercise": x["exercise"], "how": x["end"]["how"],
                     "record_during": x["end"]["record_during"], "types_on_flagged": x.get("types_on_flagged"),
                     "flagged_drains": len(x.get("bills") or []), "billed_hist": x.get("billed_hist"),
                     "table_met": x.get("asked_met"), "billed_asked_ok": x.get("billed_asked_ok"),
                     "fallbacks_delta": x.get("fallbacks_delta"), "stale_rows": x.get("stale_rows"),
                     "stale_billed_type_met": x.get("stale_billed_type_met"), "record_ok": x.get("record_ok"),
                     "billed_all": x.get("billed_all")} for x in gs["sets"]]
    out["end_cases"] = [x["end"] for x in gs["sets"]]
    out["moodle_pairs"] = L.moodle_pairs_grade(doc.get("moodle_pairs") or [])
    out["vanilla_pairs"] = L.vanilla_pairs_reading(doc.get("moodle_pairs") or [])
    out["fitness_at_start"] = L.g(doc, "phases", "S", "fitness")
    sel = [x for x in gs["sets"] if x["end"]["how"] in ("timer", "stopped")]
    V = {}
    V["RECORD"] = bool(sel) and all(x["record_ok"] for x in sel)
    V["BILLED"] = bool(sel) and all(x["billed_ok_verdict"] for x in sel)
    V["BILLED_EXACT"] = bool(sel) and all(x["billed_all"] for x in sel)
    V["FALLBACKS"] = bool(sel) and all(x["fallbacks_ok"] for x in sel)
    st = gs.get("stale_rows_vs_flag_only") or {}
    V["STALE"] = st.get("ok") if st.get("n") else None
    V["MET_REPLAY"] = (gs.get("met_live_vs_replay") or {}).get("ok")
    V["REPLAY"] = bool(d.get("ok"))
    V["GRADE_DIFF"] = bool(out["diff_grade"]["ok"])
    V["MOODLES"] = out["moodle_pairs"]["ok"]
    out["verdicts"] = V
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ART, "x37-grade-" + datetime.date.today().strftime("%Y%m%d")))
    a = ap.parse_args(argv)
    res = {"script": "testing/experiments/x37_grade.py", "commit": _git("rev-parse", "--short", "HEAD"),
           "grade_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x37_grade.py"),
           "lib_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x37_fitness_lib.py"),
           "tool_commit": _git("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
           "mod_commit": _git("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
           "tol_default": {k: list(v) for k, v in RL.DEFAULT_TOL.items()},
           "tol_grade": {k: list(v) for k, v in L.TOL_GRADE.items()}, "sessions": {}}
    for pre in DOCS:
        res["sessions"][pre] = grade_session(pre)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "grade.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n")
    print(json.dumps({pre: (s.get("verdicts") or s) for pre, s in res["sessions"].items()}, indent=1, default=str))
    print("wrote", os.path.join(a.out, "grade.json"))


if __name__ == "__main__":
    main()
