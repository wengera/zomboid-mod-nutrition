"""x463a_regrade -- a derived artifact (Plan 16 Task 9 phase 2): x463a's WRITTEN graded again on its committed
artifact, never re-run.

The frozen grade (x46_lib.grade_written) compared the return row's HUNGER, THIRST and FATIGUE with the last two online
ring rows before the quit, at 1e-6. The ring samples at each minute event, before that minute's write, and the quit's
disconnect save holds the write of the minute after the last ring row: x463a's FATIGUE read one more minute's fall.
This script admits that one write:
  WRITTEN_RG   on the first return row whose stamps moved (x46_lib.resumed_row), each written stat equals one of the
               last two online pre rows (STAT_TOL), or lies between the last row's value and one more step at the last
               step's rate (last + (last - prev)), widened by STAT_TOL: the disconnect's one-minute-later write, and
               no more. Unmeasured with no return row or fewer than two pre rows.
The freeze itself (AWAY_STILL, FREEZE, STAMPS) held and is not regraded.

`python testing/experiments/x463a_regrade.py [--out <dir>]`; the default output is
testing/artifacts/x463a-regrade-20261019/regrade.json. Frozen once its output is committed (CLAUDE.md s5).
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
RUN = "x463a-20261019-023729"
OUT = os.path.join(REPO, "testing", "artifacts", "x463a-regrade-20261019")
WRITTEN = ("HUNGER", "THIRST", "FATIGUE")
STAT_TOL = 1e-6                          # x46_lib.STAT_TOL


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def admitted(prev, last, ret, tol=STAT_TOL):
    """ret is prev, last, or within one step past last at the last step's rate (either direction), widened by tol."""
    if None in (prev, last, ret):
        return False
    if abs(ret - prev) <= tol or abs(ret - last) <= tol:
        return True
    nxt = last + (last - prev)
    lo, hi = min(last, nxt) - tol, max(last, nxt) + tol
    return lo <= ret <= hi


def grade_written(rows_pre, ret_row):
    last = [r for r in rows_pre if r.get("on") is not False][-2:]
    if ret_row is None or len(last) < 2:
        return "unmeasured", {"why": "no resumed row or fewer than two online rows before the quit"}
    o = {"row_s": ret_row.get("s"), "ret": {k: ret_row.get(k) for k in WRITTEN},
         "pre": [{k: r.get(k) for k in WRITTEN} for r in last], "per_stat": {}}
    ok = True
    for k in WRITTEN:
        p, l_, r = num(last[0].get(k)), num(last[1].get(k)), num(ret_row.get(k))
        a = admitted(p, l_, r)
        o["per_stat"][k] = {"prev": p, "last": l_, "ret": r, "next_at_rate": None if None in (p, l_) else 2 * l_ - p,
                            "admitted": a}
        ok = ok and a
    return ("as_predicted" if ok else "falsified"), o


def main(argv):
    import x46_lib as L
    out = argv[argv.index("--out") + 1] if "--out" in argv else OUT
    art = os.path.join(REPO, "testing", "artifacts", RUN)
    raw = open(os.path.join(art, "freeze.json"), "rb").read()
    d = json.loads(raw.decode("utf-8"))
    pre = json.load(open(os.path.join(art, "minute-ring-admin-1-pre.json"), encoding="utf-8"))["rows_list"]
    post = json.load(open(os.path.join(art, "minute-ring-admin-1.json"), encoding="utf-8"))["rows_list"]
    pre.sort(key=lambda r: r.get("s") or 0)
    post.sort(key=lambda r: r.get("s") or 0)
    ret = L.resumed_row(post, d["checks"]["OFF"]["away0"])
    v, o = grade_written(pre, ret)
    o["frozen_verdict"] = d["verdicts"]["WRITTEN"]["verdict"]
    res = {"verdicts": {"WRITTEN_RG": {"verdict": v, "observed": o,
                                       "falsifier": "a written stat beyond one step of the last pre-quit row's rate"}},
           "source": f"testing/artifacts/{RUN}/freeze.json", "source_sha256": hashlib.sha256(raw).hexdigest(),
           "script": "testing/experiments/x463a_regrade.py", "kind": "derived artifact (analysis, not a live run)"}
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "regrade.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({k: v["verdict"] for k, v in res["verdicts"].items()}, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
