"""x30_regrade -- the re-grade of x301 and x302 through the fixed replay tool (Plan 11f ruling T7-1, finding F-T7-1). An
ANALYSIS script, not a driver (it boots nothing). Written and committed before its output.

    python testing/experiments/x30_regrade.py [--out testing/artifacts/x30-regrade-YYYYMMDD]

F-T7-1: since the minute.ring rows carry the engine's raw rate and exe, replay_live built an activity event on nearly
every row and its diff marked the row after each as `between`, so the tool's own diff compared 0 rows. The fix leaves
ring-derived activity events out of `between`; only logged eats, drinks and other non-ring events keep the skip.

This script re-runs tools/replay_live.py at HEAD (the library entry replay_live + diff, the CLI's own path with
--sleep-allowed true) over the committed runs' inputs (events.json, start.json, start-stats.json, player.json and the
minute-ring pages the driver document names), reading them from testing/artifacts/x30N-*/ and modifying nothing there.
It writes one JSON per run (the tool's diff: fields, classes, ok, the first findings) and summary.json: per run the
graded n, the field maxima and ok.
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
RUNS = (("x301", "x301-20261011-085950", "sleep-1.json"), ("x302", "x302-20261011-091000", "sleep-2.json"))
USER = "admin"
SLEEP_ALLOWED = True


def read(d, name):
    with open(os.path.join(d, name), encoding="utf-8") as fh:
        return json.load(fh)


def regrade(run_id, doc_name):
    d = os.path.join(ART, run_id)
    doc = read(d, doc_name)
    files = [f for f in (((doc.get("verdicts") or {}).get("RING") or {}).get("observed") or {}).get("files") or [] if f]
    ring, paths = RL.load_ring([os.path.join(d, f) for f in files])
    ring = [r for r in ring if r.get("age") is not None]
    rows, be = RL.replay_live(ring, read(d, "events.json"), read(d, "start.json"), paths=paths, user=USER,
                              player=read(d, "player.json"), start_stats=read(d, "start-stats.json"),
                              sleep_allowed=SLEEP_ALLOWED)
    df = RL.diff(rows, ring)
    return {"run_id": run_id, "ring_rows": len(ring), "ring_activity_events": len(be.ring_activity),
            "tol": {k: list(v) for k, v in RL.DEFAULT_TOL.items()},
            "diff": {"ok": df["ok"], "fields": df["fields"], "classes": df["classes"],
                     "skipped_n": len(df["skipped"]), "findings_n": len(df["findings"]),
                     "findings": df["findings"][:20]}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ART, "x30-regrade-" + datetime.date.today().strftime("%Y%m%d")))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    summary = {}
    for name, run_id, doc_name in RUNS:
        res = regrade(run_id, doc_name)
        with open(os.path.join(a.out, name + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(res, fh, indent=1, sort_keys=True)
            fh.write("\n")
        f = res["diff"]["fields"]
        summary[name] = {"run_id": run_id, "graded_n": {k: v.get("n") for k, v in f.items()},
                         "field_max": {k: v.get("max") for k, v in f.items()}, "fields": f,
                         "classes": res["diff"]["classes"], "ok": res["diff"]["ok"]}
    with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({k: {"graded_n": v["graded_n"], "field_max": v["field_max"], "ok": v["ok"]}
                      for k, v in summary.items()}, indent=1))
    return 0 if all(v["ok"] for v in summary.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
