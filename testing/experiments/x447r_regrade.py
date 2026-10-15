"""x447r_regrade -- the regrade of Plan 14 Task 6's M2 run (x447-20261015-181709), written after the run and
committed before it ran: an ANALYSIS script, not a driver (it boots nothing; named x447r_, not x447_, so the x447_
prefix stays the driver's alone, test_drivers_name_their_session); x44_guide_lib.py stays as committed with its runs
(the x436 regrade precedent). Its output is a DERIVED artifact folder; the run's own verdicts stay as recorded.

    python testing/experiments/x447r_regrade.py [--out testing/artifacts/x447-regrade-YYYYMMDD]

THE DEFECT. The run's second coffee (Base.FountainCupWater) was queued and never drunk (drunk 0.0), so its full cup
stayed the autodrink probe's first container, and the five later drinks (coffee 3, beers 1-4) each failed the lib's
fill gate on its probe clause although each fill read ok and each was drunk live (drinks[2..6].drunk 0.25 / 0.3). By
the lib's rule a gate failure leaves the replay, so the run's replay lacked five landed drinks and its seven M2 grades
measured the missing inputs, not the kernel.

THE REGRADE. The same lib functions on the run's own committed inputs (the three ring pages, acute.json's eats, drinks
and phase W start, start.json, player.json), with one change: a drink enters the replay when it was drunk live
(`drunk` > 0), not when its gate passed. Each drink's litres are split over the ring rows whose intake sips counter
rose inside its own [age0, age1 + 0.1] window (the lib's build_events) -- the ring's own record of when each drink
landed; no drink time is supplied by this script. A drunk drink with no sip row in its window is UNRECORDED, and then
every replay grade and the hangover stay unmeasured.

GRADES.
  REP     the run's own event list rebuilt from its gate-passed drinks equals the committed events.json, and its HEAD
          replay's per-field n/max/over equal the run's recorded `replay.fields` (the tool and mod/ unchanged since
          the run: replay_live.py at d31ec5a0, mod/ at 498bd4a5) -- the regrade reproduces the run before it changes it.
  INPUTS  every live-drunk drink is in the regrade's events by its label with its litres summed to `drunk`, and no
          other drink is; falsified otherwise (a dropped or an extra drink), and then the field grades are unmeasured.
  M2r_<field>  the seven replay fields under the run's own tolerances (lib REPLAY_TOL and ACUTE_TOL), the lib's
          grade_replay_field (unmeasured on zero compared rows).
  M2r_hangover the lib's grade_hangover (live and replay first acute.hang within HANG_TOL_H; unmeasured on no row).
"""
import argparse
import copy
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))

import x44_guide_lib as L   # noqa: E402

RUN = "x447-20261015-181709"
SRC_DIR = os.path.join(REPO, "testing", "artifacts", RUN)
ARTIFACT = "acute.json"
PAGES = ("minute-ring-admin-1.json", "minute-ring-admin-721.json", "minute-ring-admin-1441.json")
LITRE_TOL = 1e-9
SIP_PAD_H = 0.1                      # the lib's build_events window: [age0, age1 + 0.1]


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load(src_dir=SRC_DIR):
    """The run's committed inputs: its artifact, ring rows (keyed and sorted by s, the lib's ring_rows), start record,
    player and the committed events.json."""
    def rd(name):
        with open(os.path.join(src_dir, name), encoding="utf-8") as fh:
            return json.load(fh)
    d = rd(ARTIFACT)
    rows = {}
    for p in PAGES:
        for r in rd(p).get("rows_list") or []:
            rows[r["s"]] = r
    W = (d.get("checks") or {}).get("W") or {}
    return {"d": d, "rows": [rows[s] for s in sorted(rows)], "start": rd("start.json"), "player": rd("player.json"),
            "events_run": rd("events.json"), "start_age": L.num(W.get("start_age")),
            "start_stats": W.get("start_stats") or {},
            "sha256": {n: sha(os.path.join(src_dir, n)) for n in (ARTIFACT, "start.json", "player.json",
                                                                   "events.json") + PAGES}}


def landed(drinks):
    """The regrade's rule: a drink drunk live."""
    return [x for x in drinks if (L.num(x.get("drunk")) or 0) > 0]


def gate_passed(drinks):
    """The run's rule (the lib's grade_mod): a drink whose fill gate passed."""
    return [x for x in drinks if x.get("fill_ok")]


def sip_rows(rows, drink):
    """The ring rows inside the drink's window whose sips counter rose, each with its rise."""
    out, prev = [], None
    a0, a1 = L.num(drink.get("age0")), L.num(drink.get("age1"))
    for r in rows:
        if prev is not None and a0 is not None and a1 is not None:
            a, b = L.num(prev.get(L.SIPS_G)), L.num(r.get(L.SIPS_G))
            age = L.num(r.get("age"))
            if a is not None and b is not None and b > a and age is not None and a0 - 1e-9 <= age <= a1 + SIP_PAD_H:
                out.append({"s": r["s"], "age": age, "sips": b - a})
        prev = r
    return out


def check_inputs(rows, drinks, events):
    """INPUTS: every live-drunk drink is in the events by label with its litres summed to `drunk`, no other drink is,
    and each live-drunk drink has sip rows in its window (else it is unrecorded). Returns (verdict, observed)."""
    want = {x.get("label"): L.num(x.get("drunk")) for x in landed(drinks)}
    unrec = [lb for lb in want if not sip_rows(rows, next(x for x in drinks if x.get("label") == lb))]
    got = {}
    for e in events:
        if e.get("kind") == "drink":
            got[e.get("label")] = got.get(e.get("label"), 0.0) + (L.num(e.get("litres")) or 0.0)
    missing = sorted(lb for lb in want if lb not in got)
    extra = sorted(lb for lb in got if lb not in want)
    off = sorted(lb for lb in want if lb in got and abs(got[lb] - want[lb]) > LITRE_TOL)
    obs = {"landed": want, "in_events": got, "missing": missing, "extra": extra, "litres_off": off,
           "unrecorded": unrec, "sip_rows": {lb: [r["s"] for r in sip_rows(rows, x)] for x in drinks
                                             for lb in [x.get("label")] if lb in want}}
    if not want:
        obs["why"] = "no drink was drunk live"
        return "unmeasured", obs
    if unrec:
        obs["why"] = "a drink drunk live has no sip row in the ring: its landing is unrecorded"
        return "unmeasured", obs
    if missing or extra or off:
        obs["why"] = "the events drop, add or mis-size a live-drunk drink"
        return "falsified", obs
    return "as_predicted", obs


def tolerances():
    tol = dict(L.REPLAY_TOL)
    tol.update(L.ACUTE_TOL)
    return tol


def grade_fields(diff, ring, rep_rows, inputs_verdict):
    """The seven field grades and the hangover; every one unmeasured unless INPUTS is as predicted."""
    out = {}
    if inputs_verdict != "as_predicted":
        for f in tolerances():
            out[f"M2r_{f}"] = {"verdict": "unmeasured", "observed": {"why": "INPUTS not as predicted"}}
        out["M2r_hangover"] = {"verdict": "unmeasured", "observed": {"why": "INPUTS not as predicted"}}
        return out
    for f in tolerances():
        v, o = L.grade_replay_field(diff, f)
        out[f"M2r_{f}"] = {"verdict": v, "observed": o}
    v, o = L.grade_hangover(ring, rep_rows)
    out["M2r_hangover"] = {"verdict": v, "observed": o}
    return out


def build(inp, select):
    drinks = copy.deepcopy(inp["d"].get("drinks") or [])
    eats = copy.deepcopy(inp["d"].get("eats") or [])
    events, book = L.replay_events(inp["rows"], eats, select(drinks), inp["start_age"], sleep=True)
    return drinks, events, book


def replay(inp, events):
    return L.replay_grade(inp["rows"], events, inp["start"], True, tolerances(), paths=list(L.M2_RING),
                          player=inp["player"], start_stats=inp["start_stats"])


def norm(x):
    return json.loads(json.dumps(x, sort_keys=True, default=str))


def reproduce(inp):
    """REP: the run's own events and replay field stats, rebuilt."""
    _, ev, _ = build(inp, gate_passed)
    same_events = norm(ev) == norm(inp["events_run"])
    run_fields = ((inp["d"].get("replay") or {}).get("fields")) or {}
    obs = {"events_equal": same_events, "run_fields": run_fields}
    if not same_events or not run_fields:
        obs["why"] = "the run's events do not rebuild" if not same_events else "the run recorded no replay fields"
        return ("falsified" if not same_events else "unmeasured"), obs
    _, diff, _ = replay(inp, ev)
    got = {f: {k: (diff.get("fields") or {}).get(f, {}).get(k) for k in ("n", "max", "over")} for f in run_fields}
    want = {f: {k: run_fields[f].get(k) for k in ("n", "max", "over")} for f in run_fields}
    obs["rebuilt_fields"] = got
    if norm(got) != norm(want):
        obs["why"] = "the rebuilt replay's field stats differ from the run's"
        return "falsified", obs
    return "as_predicted", obs


def regrade(inp, select=landed, rep=True):
    out = {"run": RUN, "source": f"testing/artifacts/{RUN}/", "source_sha256": inp.get("sha256"),
           "rule": "a drink enters the replay when drunk live (drunk > 0), split over its own sip rows", "verdicts": {}}
    if rep:
        v, o = reproduce(inp)
        out["verdicts"]["REP"] = {"verdict": v, "observed": o}
    drinks, events, book = build(inp, select)
    v, o = check_inputs(inp["rows"], drinks, events)
    out["verdicts"]["INPUTS"] = {"verdict": v, "observed": o}
    out["bookkeeping"] = book
    out["events"] = events
    diff, rep_rows = {}, []
    if v == "as_predicted":
        rep_rows, diff, be = replay(inp, events)
        out["replay"] = {"rows": len(rep_rows), "classes": diff.get("classes"), "fields": diff.get("fields"),
                         "findings_n": len(diff.get("findings") or []), "offset": be.R.offset}
        out["_replay_rows"], out["_diff"] = rep_rows, diff
    out["verdicts"].update(grade_fields(diff, inp["rows"], rep_rows, v))
    run_v = inp["d"].get("verdicts") or {}
    for k in list(out["verdicts"]):
        if k.startswith("M2r_"):
            src = "M2_hangover" if k == "M2r_hangover" else "M2_replay_" + k[len("M2r_"):]
            out["verdicts"][k]["run_verdict"] = (run_v.get(src) or {}).get("verdict")
    out["summary"] = {k: x["verdict"] for k, x in out["verdicts"].items()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "testing", "artifacts", "x447-regrade-20261015"))
    a = ap.parse_args()
    out = regrade(load())
    rep_rows, diff = out.pop("_replay_rows", []), out.pop("_diff", {})
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "replay.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"rows": rep_rows, "diff": diff, "events": out["events"]}, indent=1, sort_keys=True,
                            default=str) + "\n")
    with open(os.path.join(a.out, "regrade.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(out["summary"], indent=1))
    sys.exit(0 if out["summary"].get("REP") == "as_predicted" and out["summary"].get("INPUTS") == "as_predicted"
             else 1)


if __name__ == "__main__":
    main()
