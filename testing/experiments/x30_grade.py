"""x30_grade -- the committed grade of Plan 11f Task 7 (research row 11, sleep debt): an ANALYSIS script, not a driver
(it boots nothing). Written and committed before the first boot of the runs it grades; its output is a DERIVED
artifact folder (ruling T4-3: every number a row may cite is emitted by a committed script).

    python testing/experiments/x30_grade.py [--out testing/artifacts/x30-grade-YYYYMMDD]

The inputs are each session's artifact folder testing/artifacts/x30N-*/: the driver's document (sleep-1.json,
sleep-2.json), events.json (the eats, the autoDrop drinks and the ring's sleep events, x30_sleep_lib changes 3-4),
start.json, start-stats.json, player.json and the minute-ring pages. The tool is tools/replay_live.py at HEAD with the
live server's sleep option (sleep_allowed true); the activity comes from the ring's rate and exe (the tool's default).

Every session: the replay of live re-run and graded twice: the tool's own diff (HUNGER 0.002, es 0.005, L 0.5 %), whose
`between` rule skips the row after every event, the sleep events included; and this script's diff, which skips a row
only for an eat or drink event (a sleep event changes what the NEXT drain books, so no ring row sits between it and its
effect; x29_grade's rule for activity events), under HUNGER 0.002, es 0.005, L 0.5 %, acute.debtH 1e-6 and
acute.winSleptH 1e-6. A second replay of the same events with K.satiety.SLEEP_MAX 0 is the no-sleep-factor
counterfactual.

Row 11:
  - per night (the driver's stop): the target, the booked sleep, the held span, their ratio, the cancel's reason, the
    fast-forward (held game hours per wall second);
  - per window close on the ring (x30_sleep_lib.window_closes): the booked sleep, the debt before and after, the
    kernel's own booking and the replay's debt;
  - THE FACTOR: on every graded ring row (not an eat or drink row, not suspect or offline) whose live, replay and
    counterfactual HUNGER are all under the 0.69 cap: live HUNGER / counterfactual HUNGER against
    K.satiety.sleepFactor(the row's live acute.debtH) = 1 + SLEEP_MAX x clamp(debtH / SLEEP_DEBT_FULL_H, 0, 1), 1 %;
    the replay's own factor (replay / counterfactual against sleepFactor(the replay's debtH)); grouped by the live debt
    between closes (a segment), and at each meal's read (the ring row at or before the stop's read age);
  - the study distances as readings (the oracles' pins, test_satiety_meal_studies.py): after the short night's close,
    the rise at the first meal in mm (0.25 x (factor - 1) x 260, ruling 11c-31's mapping, against 11.7 mm at debt 2.0),
    the next-day intake ratio by the oracles' own mapping (the sum of 650 x written / 0.25 over the meals the debt
    holds for, against the counterfactual's: 1.18, band 1.10-1.19); after the recovery close the debt (1.0) and the
    factor (1.09); after the rested night that follows, the debt held; the split case (1.5/0.5, 1.135) is not run live
    (the chain's short night is in phase: named);
  - the eating reads and the energy ladder: per meal the es read, the ring's and the replay's es at the read, the
    target and the kcal eaten; the live kcal per chain day; es per chain day (min, max);
  - the sedentary guard (exe, moving, the billed Sleeping MET against the sleep events);
  - the drinking and the sodium per chain day (x29_grade's form).
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
import x30_sleep_lib as L  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
CHAIN = (("x301", "sleep-1.json"), ("x302", "sleep-2.json"))
MM_PER_HUNGER = 65.0 / 0.25            # ruling 11c-31's request-anchored mapping (an assumption)
H_REQ = 0.25
CAP = 0.69
FACTOR_TOL = 0.01
TOL_MINE = {"HUNGER": ("abs", 0.002), "body.energyState": ("abs", 0.005), "satiety.L": ("rel", 0.005),
            "acute.debtH": ("abs", 1e-6), "acute.winSleptH": ("abs", 1e-6)}
ORACLE_PINS = {
    "short_night_debt": 2.0, "short_night_rise_mm": 11.7, "s1284_rise_mm": 13.4, "next_day_intake": 1.18,
    "next_day_intake_band": [1.10, 1.19], "recovery_debt": 1.0, "recovery_factor": 1.09,
    "split_debts_at_closes": [0.0, 1.5, 2.0, 2.0], "split_factor_next_day": 1.135,
    "source": "testing/tests/kernel/test_satiety_meal_studies.py (test_one_short_night_raises_hunger_at_the_request_"
              "by_the_pooled_size, test_one_short_night_raises_next_day_intake_within_the_pooled_band, "
              "test_recovery_sleep_reverses_the_factor_partially, test_a_short_night_across_two_windows_splits_its_debt)"}


def _git(*a):
    import subprocess
    try:
        return subprocess.run(["git"] + list(a), cwd=REPO, capture_output=True, text=True).stdout.strip()
    except OSError:
        return None


def folder(pre):
    hits = sorted(d for d in os.listdir(ART) if d.startswith(pre + "-") and os.path.isdir(os.path.join(ART, d)))
    if len(hits) != 1:
        raise SystemExit("expected one artifact folder for %s, found %r" % (pre, hits))
    return os.path.join(ART, hits[0])


def read(run, name):
    with open(os.path.join(run, name), encoding="utf-8") as fh:
        return json.load(fh)


def no_sleep_factor(fn):
    """fn() with every server replay built inside it reading K.satiety.SLEEP_MAX = 0 (the no-sleep-factor
    counterfactual: sleepFactor reads 1 at every debt; the debt itself is still booked)."""
    init = RL.ServerReplay.__init__

    def patched(self, *a, **kw):
        init(self, *a, **kw)
        self.K.satiety.SLEEP_MAX = 0

    RL.ServerReplay.__init__ = patched
    try:
        return fn()
    finally:
        RL.ServerReplay.__init__ = init


class Sess:
    def __init__(self, pre, doc_name):
        self.pre = pre
        self.dir = folder(pre)
        self.doc = read(self.dir, doc_name)
        files = [f for f in (L.g(self.doc, "verdicts", "RING", "observed", "files") or []) if f]
        self.ring, self.rpaths = (RL.load_ring([os.path.join(self.dir, f) for f in files]) if files else ([], []))
        self.ring = [r for r in self.ring if r.get("age") is not None]
        self.events = read(self.dir, "events.json") if os.path.isfile(os.path.join(self.dir, "events.json")) else []
        self.start = read(self.dir, "start.json")
        self.stats = read(self.dir, "start-stats.json")
        self.player = read(self.dir, "player.json") if os.path.isfile(os.path.join(self.dir, "player.json")) else None
        rec = self.start.get("rec", self.start)
        self.a0 = L.num(L.g(rec, "satiety", "t")) or L.num(rec.get("kineticsAge"))
        self.ring_by = {r["s"]: r for r in self.ring}
        self.hold = {e["s"] for e in self.events if e.get("kind") in ("eat", "drink") and e.get("s") is not None}
        if not self.ring:
            self.rows, self.diff, self.mine, self.rep_by, self.nf_by = [], {"ok": None}, {"ok": None}, {}, {}
            return
        run = lambda: RL.replay_live(self.ring, self.events, self.start, paths=self.rpaths, user=L.USER,  # noqa: E731
                                     player=self.player, start_stats=self.stats, sleep_allowed=L.SLEEP_ALLOWED)
        self.rows, self.be = run()
        self.diff = RL.diff(self.rows, self.ring)
        mine = []
        for r in self.rows:
            x = dict(r)
            x["between"] = r["s"] in self.hold
            mine.append(x)
        self.mine = RL.diff(mine, self.ring, TOL_MINE)
        self.rep_by = {r["s"]: r for r in self.rows}
        rows_nf, _ = no_sleep_factor(run)
        self.nf_by = {r["s"]: r for r in rows_nf}

    def summary(self):
        kinds = {}
        for e in self.events:
            kinds[e.get("kind")] = kinds.get(e.get("kind"), 0) + 1
        return {"run_id": self.doc.get("run_id"), "rows": len(self.rows), "events_by_kind": kinds,
                "ring_activity_events": len(getattr(getattr(self, "be", None), "ring_activity", None) or []),
                "tool_diff": {k: self.diff.get(k) for k in ("fields", "classes", "ok")} | {
                    "findings_n": len(self.diff.get("findings", [])), "findings": self.diff.get("findings", [])[:20]},
                "diff": {k: self.mine.get(k) for k in ("fields", "classes", "ok")} | {
                    "findings_n": len(self.mine.get("findings", [])), "findings": self.mine.get("findings", [])[:40]},
                "start_age": self.a0, "ring_first_age": self.ring[0]["age"] if self.ring else None,
                "ring_last_age": self.ring[-1]["age"] if self.ring else None,
                "driver_verdicts": {k: v.get("verdict") for k, v in (self.doc.get("verdicts") or {}).items()}}


def kernel():
    return L._kh_static().K


def factor_row(S, r):
    """One ring row's factor reading, or None when the row is not graded (an eat or drink row, suspect or offline in the
    replay, or a value missing)."""
    K = kernel()
    rp, nf = S.rep_by.get(r["s"]), S.nf_by.get(r["s"])
    if rp is None or nf is None or r["s"] in S.hold or rp.get("suspect") or rp.get("offline"):
        return None
    h, hr, hn = L.num(r.get("HUNGER")), L.num(rp.get("HUNGER")), L.num(nf.get("HUNGER"))
    d, dr = L.num(r.get(L.DEBT)), L.num(rp.get(L.DEBT))
    if h is None or hr is None or hn is None or d is None or dr is None or hn <= 0:
        return None
    capped = h >= CAP - 1e-9 or hr >= CAP - 1e-9 or hn >= CAP - 1e-9
    p, pr = float(K.satiety.sleepFactor(d)), float(K.satiety.sleepFactor(dr))
    f, fr = h / hn, hr / hn
    return {"s": r["s"], "age": r["age"], "debt": d, "debt_replay": dr, "HUNGER": h, "HUNGER_replay": hr,
            "HUNGER_nofactor": hn, "factor": f, "factor_replay": fr, "formula": p, "formula_replay": pr,
            "capped": capped, "rel": None if capped else abs(f / p - 1), "rel_replay": None if capped else abs(fr / pr - 1),
            "gap": bool(rp.get("gap")), "mm": (h - hn) * MM_PER_HUNGER}


def factor_rows(S):
    out = []
    for r in S.ring:
        x = factor_row(S, r)
        if x is not None:
            out.append(x)
    return out


def segments(rows):
    """The graded factor rows grouped by the live debt (one segment per run of an unchanged debt)."""
    out = []
    for x in rows:
        if out and abs(out[-1]["debt"] - x["debt"]) <= 1e-12:
            seg = out[-1]
        else:
            seg = {"debt": x["debt"], "age0": x["age"], "rows": []}
            out.append(seg)
        seg["age1"] = x["age"]
        seg["rows"].append(x)
    res = []
    for seg in out:
        ok = [x for x in seg["rows"] if x["rel"] is not None]
        res.append({"debt": seg["debt"], "age0": seg["age0"], "age1": seg["age1"], "rows": len(seg["rows"]),
                    "graded": len(ok), "capped": len(seg["rows"]) - len(ok),
                    "formula": ok[0]["formula"] if ok else None,
                    "factor_min": min((x["factor"] for x in ok), default=None),
                    "factor_max": max((x["factor"] for x in ok), default=None),
                    "factor_mean": (sum(x["factor"] for x in ok) / len(ok)) if ok else None,
                    "factor_replay_mean": (sum(x["factor_replay"] for x in ok) / len(ok)) if ok else None,
                    "max_rel": max((x["rel"] for x in ok), default=None),
                    "max_rel_replay": max((x["rel_replay"] for x in ok), default=None),
                    "ok": bool(ok) and max(x["rel"] for x in ok) <= FACTOR_TOL})
    return res


def meal_reads(S):
    """Per meal stop of the session: the ring row at or before the stop's read age (before its eats), its live,
    replay and counterfactual HUNGER, the debt, the factor triple; the es read and the ring's and replay's es."""
    out = []
    for st in S.doc.get("stops") or []:
        if st.get("kind") not in ("maint", "request"):
            continue
        a = L.num(L.g(st, "read", "age"))
        r = L.row_at(S.ring, a) if a is not None else None
        x = factor_row(S, r) if r is not None else None
        rp = S.rep_by.get(r["s"]) if r is not None else None
        out.append({"label": st["label"], "kind": st["kind"], "sched_age": st.get("sched_age"), "read_age": a,
                    "late_h": (a - st["sched_age"]) if (a is not None and st.get("sched_age") is not None) else None,
                    "ring_s": r["s"] if r else None, "ring_age": r["age"] if r else None,
                    "es_read": L.g(st, "read", "es"), "es_ring": r.get("body.energyState") if r else None,
                    "es_replay": rp.get("body.energyState") if rp else None, "target": st.get("target"),
                    "eaten_kcal": st.get("eaten_kcal"), "portions": st.get("portions"), "factor": x})
    return out


def study(meals, closes):
    """The study distances as readings, off the chain's meal reads and closes (ORACLE_PINS)."""
    by = {m["label"]: m for m in meals}

    def ratio(labels):
        xs = [by[x]["factor"] for x in labels if x in by and by[x]["factor"] and not by[x]["factor"]["capped"]]
        if len(xs) != len(labels):
            return None
        return {"labels": labels, "live": sum(x["HUNGER"] for x in xs) / sum(x["HUNGER_nofactor"] for x in xs),
                "replay": sum(x["HUNGER_replay"] for x in xs) / sum(x["HUNGER_nofactor"] for x in xs)}

    def first(label):
        m = by.get(label)
        x = m["factor"] if m else None
        if not x:
            return None
        return {"label": label, "debt": x["debt"], "factor": x["factor"], "factor_replay": x["factor_replay"],
                "formula": x["formula"], "rise_mm": H_REQ * (x["factor"] - 1) * MM_PER_HUNGER,
                "rise_mm_replay": H_REQ * (x["factor_replay"] - 1) * MM_PER_HUNGER,
                "rise_mm_formula": H_REQ * (x["formula"] - 1) * MM_PER_HUNGER}
    deb = [c["debt_after"] for c in closes]
    return {"short": {"debt_after_close": deb[1] if len(deb) > 1 else None, "first_meal": first("D2_13"),
                      "next_day_intake": ratio(["D2_13", "D2_20", "D3_08"])},
            "recovery": {"debt_after_close": deb[2] if len(deb) > 2 else None, "first_meal": first("D3_13"),
                         "next_day_intake": ratio(["D3_13", "D3_20", "D4_08"])},
            "rested_after": {"debt_after_close": deb[3] if len(deb) > 3 else None, "first_meal": first("D4_13")},
            "rested_baseline": {"debt_after_close": deb[0] if deb else None,
                                "meals": ratio(["D1_13", "D1_20", "D2_08"])},
            "split_case": "not run live: the chain's short night lies inside one window (in phase); the oracle's "
                          "phased case (1.5/0.5, 1.135) needs a second short night across a close from a rested debt",
            "oracle_pins": ORACLE_PINS}


def es_by_day(sessions):
    out = {}
    for S in sessions:
        for r in S.ring:
            e = L.num(r.get("body.energyState"))
            if e is None:
                continue
            d = out.setdefault(str(L.day_of(r["age"])), {"min": e, "max": e})
            d["min"], d["max"] = min(d["min"], e), max(d["max"], e)
    return out


def kcal_by_day(sessions):
    out = {}
    for S in sessions:
        for e in S.doc.get("eats") or []:
            if not e.get("landed") or e.get("ring_age") is None:
                continue
            d = str(L.day_of(e["ring_age"]))
            out[d] = out.get(d, 0.0) + L.eat_kcal(e["food"])
    return out


def drinking_sodium(sessions):
    K = kernel()
    out = {}
    for S in sessions:
        for e in L.autodrop_events(S.ring):
            d = out.setdefault(str(L.day_of(e["age"])), {})
            d["mod_l"] = d.get("mod_l", 0.0) + e["vec"]["water"] / 1000.0
        prev = None
        for r in S.ring:
            d = out.setdefault(str(L.day_of(r["age"])), {})
            d["ring_hours"] = d.get("ring_hours", 0.0) + (r["age"] - prev["age"] if prev is not None and
                                                           L.day_of(prev["age"]) == L.day_of(r["age"]) else 0.0)
            for k in ("fluids.na", "fluids.water", "fluids.naPlasma"):
                if L.num(r.get(k)) is not None:
                    d.setdefault(k + "_first", r[k])
                    d[k + "_end"] = r[k]
            p = L.num(r.get("fluids.naPlasma"))
            if p is not None:
                d["naPlasma_min"] = min(d.get("naPlasma_min", p), p)
                d["naPlasma_max"] = max(d.get("naPlasma_max", p), p)
            prev = r
    for d in out.values():
        d["grade_max"] = L.hypo_grade(d.get("naPlasma_min"))
        d["complete"] = d.get("ring_hours", 0) > 23.5
    return {"by_day": dict(sorted(out.items(), key=lambda kv: int(kv[0]))), "BASAL_NA": float(K.fluids.BASAL_NA),
            "grade_max_chain": max((d["grade_max"] for d in out.values() if d.get("grade_max") is not None),
                                   default=None)}


def asleep_agreement(S):
    """HUNGER, es and the debt live against the replay on the ring rows after an asleep drain (acute.sleptH > 0)."""
    n, h, e = 0, 0.0, 0.0
    for r in S.ring:
        if (L.num(r.get(L.SLEPT)) or 0) <= 0 or r["s"] in S.hold:
            continue
        rp = S.rep_by.get(r["s"])
        if rp is None or rp.get("suspect") or rp.get("offline"):
            continue
        a, b = L.num(r.get("HUNGER")), L.num(rp.get("HUNGER"))
        c, d = L.num(r.get("body.energyState")), L.num(rp.get("body.energyState"))
        if a is None or b is None or c is None or d is None:
            continue
        n += 1
        h, e = max(h, abs(a - b)), max(e, abs(c - d))
    return {"rows": n, "HUNGER_max_diff": h, "es_max_diff": e}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = a.out or os.path.join(ART, "x30-grade-%s" % datetime.date.today().strftime("%Y%m%d"))
    os.makedirs(out, exist_ok=True)
    sessions = []
    for pre, doc in CHAIN:
        try:
            sessions.append(Sess(pre, doc))
        except SystemExit as e:
            print("skip %s: %s" % (pre, e))
    K = kernel()
    per, nights, closes, meals, frows, segs = {}, [], [], [], [], []
    for S in sessions:
        doc = S.summary()
        cl = L.window_closes(S.ring)
        for c in cl:
            rp = S.rep_by.get(c["s_after"])
            c["session"] = S.pre
            c["debt_replay"] = L.num(rp.get(L.DEBT)) if rp else None
            c["replay_diff"] = (c["debt_after"] - c["debt_replay"]) if (c["debt_after"] is not None and
                                                                        c["debt_replay"] is not None) else None
        closes += cl
        for st in S.doc.get("stops") or []:
            if st.get("kind") == "night":
                nights.append(dict(L.night_summary(st), session=S.pre))
        fr = factor_rows(S)
        frows += fr
        sg = segments(fr)
        for x in sg:
            x["session"] = S.pre
        segs += sg
        meals += [dict(m, session=S.pre) for m in meal_reads(S)]
        doc["guard"] = L.guard_reading(S.ring)
        doc["asleep_agreement"] = asleep_agreement(S)
        doc["sleep_events"] = {"n": sum(1 for e in S.events if e.get("kind") == "sleep"),
                               "asleep": sum(1 for e in S.events if e.get("kind") == "sleep" and e.get("asleep"))}
        per[S.pre] = doc
        with open(os.path.join(out, S.pre + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True, default=str)
    graded = [x for x in frows if x["rel"] is not None]
    allf = {"graded": len(graded), "capped": len(frows) - len(graded),
            "max_rel": max((x["rel"] for x in graded), default=None),
            "max_rel_replay": max((x["rel_replay"] for x in graded), default=None),
            "max_rel_with_debt": max((x["rel"] for x in graded if x["debt"] > 1e-9), default=None),
            "graded_with_debt": sum(1 for x in graded if x["debt"] > 1e-9),
            "ok": bool(graded) and max(x["rel"] for x in graded) <= FACTOR_TOL}
    row11 = {"nights": nights, "closes": closes, "factor_all": allf, "segments": segs, "meals": meals,
             "study": study(meals, closes), "es_by_day": es_by_day(sessions), "kcal_by_day": kcal_by_day(sessions),
             "constants": {"SLEEP_MAX": float(K.satiety.SLEEP_MAX), "SLEEP_DEBT_FULL_H": float(K.satiety.SLEEP_DEBT_FULL_H),
                           "SLEEP_NEED_H": float(K.acute.SLEEP_NEED_H), "REPAY": float(K.acute.REPAY),
                           "WINDOW_H": float(K.acute.WINDOW_H)}}
    rows = {"row11": row11, "drinking_sodium": drinking_sodium(sessions)}
    with open(os.path.join(out, "rows.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, sort_keys=True, default=str)
    verdicts = {
        "REPLAY_OK": {p: {"tool": d["tool_diff"]["ok"], "mine": d["diff"]["ok"]} for p, d in per.items()},
        "CLOSES_KERNEL": all(c["kernel_diff"] is not None and abs(c["kernel_diff"]) <= 1e-6 for c in closes)
        if closes else None,
        "CLOSES_REPLAY": all(c["replay_diff"] is not None and abs(c["replay_diff"]) <= 1e-6 for c in closes)
        if closes else None,
        "FACTOR": allf["ok"],
        "FACTOR_SEGMENTS": {"%s@%.4f" % (x["session"], x["debt"]): x["ok"] for x in segs},
        "NIGHTS_AT_TARGET": {n["label"]: n["reason"] == "target" for n in nights},
        "EXE_FALSE": {p: d["guard"]["exe_true_rows"] == 0 and d["guard"]["exe_present_rows"] > 0 for p, d in per.items()},
        "SODIUM_GRADE_MAX": rows["drinking_sodium"]["grade_max_chain"]}
    summ = {"tool_commit": _git("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
            "grade_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x30_grade.py"),
            "lib_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x30_sleep_lib.py"),
            "sessions": [S.pre for S in sessions], "verdicts": verdicts}
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summ, fh, indent=1, sort_keys=True, default=str)
    print(json.dumps(verdicts, indent=1, default=str))


if __name__ == "__main__":
    main()
