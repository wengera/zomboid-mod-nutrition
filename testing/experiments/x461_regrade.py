"""x461_regrade -- a derived artifact (Plan 16 Task 9 phase 2): x461a's and x461b's COLD_FED graded again on their
committed artifacts, never re-run.

The frozen grade (x46_lib.grade_cold_fed) wanted `backend.ring_cold is True`, but tools/replay_live.replay_live at
dec29870 reports `ring_cold` as the list of cold events it fed, one per ring row whose cold value changed
(replay_live.ring_cold_events), so a cold that WAS fed read falsified. This script grades what the grade meant:
  COLD_FED_RG  every online ring row of the committed pages carries a numeric `cold`; the replay's recorded event list
               (`replay.ring_cold`, the same as `verdicts.COLD_FED.observed.backend_ring_cold`) is non-empty; and every
               recorded event is an event replay_live.ring_cold_events derives from the committed pages at HEAD (the
               same s and the same cold value), so the list is the ring's own cold and not a stray feed.
Unmeasured on a missing page or list.

`python testing/experiments/x461_regrade.py [--out <dir>]`; the default output is
testing/artifacts/x461-regrade-20261019/regrade.json. Frozen once its output is committed (CLAUDE.md s5).
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
RUNS = {"x461a": ("x461a-20261019-022413", "plate.json"), "x461b": ("x461b-20261019-022954", "drinks.json")}
OUT = os.path.join(REPO, "testing", "artifacts", "x461-regrade-20261019")


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def grade_cold_fed(rows, recorded, derived):
    """COLD_FED_RG (the module docstring): unmeasured with no rows or no recorded list."""
    on = [r for r in rows if r.get("on") is not False]
    o = {"rows": len(on), "rows_with_cold": sum(1 for r in on if is_num(r.get("cold"))),
         "recorded_events": None if recorded is None else len(recorded), "derived_events": len(derived or [])}
    if not on or not isinstance(recorded, list):
        return "unmeasured", dict(o, why="no ring rows or no recorded event list")
    have = {(e.get("s"), e.get("cold")) for e in derived or []}
    stray = [e for e in recorded if (e.get("s"), e.get("cold")) not in have]
    o["stray"] = stray[:10]
    ok = o["rows_with_cold"] == o["rows"] and len(recorded) > 0 and not stray
    return ("as_predicted" if ok else "falsified"), o


def rows_of(run_dir, pages):
    rows = {}
    for f in pages:
        with open(os.path.join(run_dir, f), encoding="utf-8") as fh:
            for r in json.load(fh).get("rows_list") or []:
                rows[r["s"]] = r
    return [rows[s] for s in sorted(rows)]


def regrade_one(art_dir, artifact):
    import replay_live as RL
    raw = open(os.path.join(art_dir, artifact), "rb").read()
    d = json.loads(raw.decode("utf-8"))
    pages = [p for p in d.get("model_inputs", {}).get("ring") or [] if p]
    rows = rows_of(art_dir, pages)
    recorded = (d.get("replay") or {}).get("ring_cold")
    derived = RL.ring_cold_events(rows)
    v, o = grade_cold_fed(rows, recorded, derived)
    o["frozen_verdict"] = d["verdicts"]["COLD_FED"]["verdict"]
    return {"verdict": v, "observed": o, "source_sha256": hashlib.sha256(raw).hexdigest(), "pages": pages,
            "falsifier": "a ring row without cold, an empty recorded list, or a recorded event the ring does not give"}


def main(argv):
    out = argv[argv.index("--out") + 1] if "--out" in argv else OUT
    res = {"verdicts": {}, "script": "testing/experiments/x461_regrade.py",
           "kind": "derived artifact (analysis, not a live run)", "sources": {}}
    for key, (run, art) in RUNS.items():
        r = regrade_one(os.path.join(REPO, "testing", "artifacts", run), art)
        res["sources"][key] = {"run": run, "artifact": art, "sha256": r.pop("source_sha256"), "pages": r.pop("pages")}
        res["verdicts"][f"{key}.COLD_FED_RG"] = r
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "regrade.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({k: v["verdict"] for k, v in res["verdicts"].items()}, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
