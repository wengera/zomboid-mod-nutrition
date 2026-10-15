"""x436_regrade -- the regrade of Plan 13 Task 22b's creation run (x436-20261015-094119), written after the run and
committed before it ran: an ANALYSIS script, not a driver (it boots nothing); x43c_strength_lib.py stays as committed
with its runs (the x433 regrade precedent). Its output is a DERIVED artifact folder; the run's own 36_names verdict stays
as recorded.

    python testing/experiments/x436_regrade.py [--out testing/artifacts/x436-regrade-YYYYMMDD]

One grade defect, a prediction about a vanilla value not read before the run (CLAUDE.md s5):
  N1  36_names graded four labels, the mod's three display names and Obese's, which the driver predicted as "Obese"; the
      Obese trait's label is vanilla's own and the mod does not set it, so the clause tested nothing of the mod's. N1
      grades only the three traits the mod renames (Underweight, Very Underweight, Overweight) against the staged
      UI.json's names the run recorded (checks.S.want_names), off the client labels the run read (checks.S.labels).
      Obese's label is reported, not graded.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

RUN = "x436-20261015-094119"
SRC = os.path.join(REPO, "testing", "artifacts", RUN, "creation.json")
MOD_NAMES = ("underweight", "veryunderweight", "overweight")


def grade_mod_names(labels, want):
    """N1: the client's labels of the three renamed traits equal the staged display names; unmeasured when a label or
    a staged name is unread."""
    labels, want = labels or {}, want or {}
    obs = {"labels": {k: labels.get(k) for k in MOD_NAMES}, "want": {k: want.get(k) for k in MOD_NAMES},
           "obese_reported": labels.get("obese")}
    unread = [k for k in MOD_NAMES if not (isinstance(labels.get(k), str) and labels.get(k))
              or not (isinstance(want.get(k), str) and want.get(k))]
    if unread:
        obs["why"] = "unread: " + ", ".join(unread)
        return "unmeasured", obs
    bad = [k for k in MOD_NAMES if labels[k] != want[k]]
    obs["bad"] = bad
    if bad:
        obs["why"] = "label(s) off the display names: " + ", ".join(bad)
        return "falsified", obs
    return "as_predicted", obs


def regrade(d):
    S = (d.get("checks") or {}).get("S") or {}
    v, o = grade_mod_names(S.get("labels"), S.get("want_names"))
    run_v = ((d.get("verdicts") or {}).get("36_names") or {}).get("verdict")
    return {"run": RUN, "source": f"testing/artifacts/{RUN}/creation.json", "rules": ["N1"],
            "verdicts": {"36_names_mod": {"verdict": v, "observed": o, "run_verdict_36_names": run_v}}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "testing", "artifacts",
                                                  "x436-regrade-" + datetime.date.today().strftime("%Y%m%d")))
    a = ap.parse_args()
    with open(SRC, "rb") as fh:
        raw = fh.read()
    out = regrade(json.loads(raw.decode("utf-8")))
    out["source_sha256"] = hashlib.sha256(raw).hexdigest()
    out["summary"] = {k: v["verdict"] for k, v in out["verdicts"].items()}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "regrade.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(json.dumps(out["summary"], indent=1))


if __name__ == "__main__":
    main()
