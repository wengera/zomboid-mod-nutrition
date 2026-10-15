"""x433_regrade -- the regrade of Plan 13 Task 21's creation run (x433-20261015-052759), written after the run and committed
before it ran: an ANALYSIS script, not a driver (it boots nothing); x43_strength_lib.py stays as committed with its run
(the x30/x34/x36/x37 regrade precedent). Its output is a DERIVED artifact folder.

    python testing/experiments/x433_regrade.py [--out testing/artifacts/x433-regrade-YYYYMMDD]

One grade defect, a reply shape the committed grade did not read:
  R1  An empty trait list. The harness's JSON writer answers an empty Lua list as {} (docs/platform/harness.md, the
      reply-reading rules: `{}` for an empty list), and x43_strength_lib.traits_of reads any traitList that is not a
      list as unread, so case (a)'s state grade -- no pick, no band trait and no weight trait held on either side, the
      server's and bob's client's stats.get traitList both {} -- read unmeasured on a read that was made. R1 reads a
      traitList of {} as the empty list and re-runs x43_strength_lib.grade_case_state on every case's recorded
      observations; every other grade (body, strips) is copied from the run's own verdicts unchanged.
"""
import argparse
import copy
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import x43_strength_lib as L  # noqa: E402

RUN = "x433-20261015-052759"
SRC = os.path.join(REPO, "testing", "artifacts", RUN, "creation.json")


def empty_lists(pair):
    """R1: a stats.get traitList answered as {} (the harness's empty list) read as []."""
    p = copy.deepcopy(pair or {})
    for side in ("server_stats", "client_stats"):
        st = p.get(side)
        if isinstance(st, dict) and st.get("traitList") == {}:
            st["traitList"] = []
    return p


def regrade(d):
    out = {"run": RUN, "source": f"testing/artifacts/{RUN}/creation.json", "rules": ["R1"], "verdicts": {}}
    for lab, _p in L.CASES:
        c = copy.deepcopy((d.get("checks") or {}).get(f"C{lab}") or {})
        # the case as the run recorded it: t21_expect laid expect and want_stripped on it at the run's own grade
        before = (d.get("verdicts") or {}).get(f"21_{lab}_state") or {}
        c["pair"] = empty_lists(c.get("pair"))
        v, o = L.grade_case_state(c)
        out["verdicts"][f"21_{lab}_state"] = {"verdict": v, "observed": o, "run_verdict": before.get("verdict"),
                                              "r1_applied": c["pair"] != (d.get("checks") or {}).get(f"C{lab}", {})
                                              .get("pair")}
        for kind in ("body", "strips"):
            run_v = (d.get("verdicts") or {}).get(f"21_{lab}_{kind}") or {}
            out["verdicts"][f"21_{lab}_{kind}"] = {"verdict": run_v.get("verdict"), "copied": True}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "testing", "artifacts",
                                                  "x433-regrade-" + datetime.date.today().strftime("%Y%m%d")))
    a = ap.parse_args()
    with open(SRC, "rb") as fh:
        raw = fh.read()
    d = json.loads(raw.decode("utf-8"))
    out = regrade(d)
    out["source_sha256"] = hashlib.sha256(raw).hexdigest()
    out["lib"] = "testing/experiments/x43_strength_lib.py"
    out["summary"] = {k: v["verdict"] for k, v in out["verdicts"].items()}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "regrade.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(json.dumps(out["summary"], indent=1))


if __name__ == "__main__":
    main()
