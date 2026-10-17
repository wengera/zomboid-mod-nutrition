"""x45g_onset_regrade -- a derived artifact (Plan 15 Task 11 live review, F2): x454's and x455's ONSET graded on the
record's own starvation clock, their committed rings re-read, never re-run.

The minute ring samples on EveryOneMinute and reads the record the previous minute's step left: on every unfed row
`drain.starvedH` equals the previous row's age less `drain.fedAgeH`. x45g_lib.grade_onset computed the unfed hours off the
ring row's own age, one row ahead of the record, so its "the row before under 30 h" clause failed on the row whose step had
not yet seen 30 h. This regrade reads `drain.starvedH`: the first flagged row (drain.starveAcute true) after the set at 30
h (within ONSET_TOL_H, and the row before under 30), HUNGER over 0.70 on it or the next row, at most 0.69 + 1e-6 on every
row between the set and it; it also reports the lag identity's largest miss over the unfed rows.

`python testing/experiments/x45g_onset_regrade.py [--out <dir>]`; the default output is
testing/artifacts/x45g-onset-regrade-20261017/regrade.json. Frozen once its output is committed (CLAUDE.md s5).
"""
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RUNS = {"x454": ("x454-20261017-073220", "starve.json"), "x455": ("x455-20261017-073633", "bleed.json")}
OUT = os.path.join(REPO, "testing", "artifacts", "x45g-onset-regrade-20261017")
ONSET_H = 30.0                           # K.drain.STARVE_ONSET_H
ONSET_TOL_H = 0.05                       # x45g_lib.ONSET_TOL_H, unchanged
HUNGER_CAP = 0.69
HUNGRY_4 = 0.70


def num(v):
    if isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def grade_onset_record(rows, set_age):
    after = [r for r in rows if num(r.get("age")) is not None and r["age"] > set_age]
    i = next((k for k, r in enumerate(after) if r.get("drain.starveAcute") is True), None)
    if i is None:
        return "unmeasured", {"why": "no onset row after the set", "rows": len(after)}
    r = after[i]
    s = num(r.get("drain.starvedH"))
    s_prev = num(after[i - 1].get("drain.starvedH")) if i > 0 else None
    hs = [num(x.get("HUNGER")) for x in after[i:i + 2]]
    pre = [num(x.get("HUNGER")) for x in after[:i]]
    obs = {"onset_s": r.get("s"), "onset_age": r.get("age"), "starvedH": s, "starvedH_prev": s_prev,
           "prev_s": after[i - 1].get("s") if i > 0 else None, "hunger_at": hs,
           "pre_max": max([h for h in pre if h is not None], default=None)}
    if s is None:
        return "unmeasured", obs
    ok = (ONSET_H - 1e-9 <= s <= ONSET_H + ONSET_TOL_H and (s_prev is None or s_prev < ONSET_H)
          and any(h is not None and h > HUNGRY_4 for h in hs) and all(h is None or h <= HUNGER_CAP + 1e-6 for h in pre))
    return ("as_predicted" if ok else "falsified"), obs


def lag_identity(rows, set_age):
    """The largest |starvedH(k) - (age(k-1) - fedAgeH(k))| over the drive's unfed rows: after the set, before the first
    flagged row, both rows on the same (set) fedAgeH."""
    worst, n = 0.0, 0
    for a, b in zip(rows, rows[1:]):
        if b.get("drain.starveAcute") is True and num(b.get("age")) is not None and b["age"] > set_age:
            break
        if num(a.get("age")) is None or a["age"] <= set_age or num(a.get("drain.fedAgeH")) != num(b.get("drain.fedAgeH")):
            continue
        s, f, a0 = num(b.get("drain.starvedH")), num(b.get("drain.fedAgeH")), num(a.get("age"))
        if None in (s, f, a0):
            continue
        n += 1
        worst = max(worst, abs(s - (a0 - f)))
    return {"rows": n, "max_abs_diff_h": worst}


def ring_rows(run_dir):
    rows = {}
    for f in sorted(glob.glob(os.path.join(run_dir, "minute-ring-*.json"))):
        for r in json.load(open(f, encoding="utf-8")).get("rows_list") or []:
            rows[r["s"]] = r
    return [rows[s] for s in sorted(rows)]


def regrade_run(run_dir, artifact):
    raw = open(os.path.join(run_dir, artifact), "rb").read()
    d = json.loads(raw.decode("utf-8"))
    set_age = num(d["checks"]["A"]["set_age"])
    rows = ring_rows(run_dir)
    v, obs = grade_onset_record(rows, set_age)
    return {"verdict": v, "observed": obs, "set_age": set_age, "lag_identity": lag_identity(rows, set_age),
            "source_sha256": hashlib.sha256(raw).hexdigest()}


def main(argv):
    out = OUT
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    res = {"script": "testing/experiments/x45g_onset_regrade.py", "kind": "derived artifact (analysis, not a live run)",
           "runs": {}}
    for k, (run, art) in RUNS.items():
        res["runs"][k] = dict(regrade_run(os.path.join(REPO, "testing", "artifacts", run), art), run=run)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "regrade.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({k: (v["verdict"], v["observed"].get("starvedH_prev"), v["observed"].get("starvedH"),
                          v["lag_identity"]) for k, v in res["runs"].items()}, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
