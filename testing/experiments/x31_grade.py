"""x31_grade -- the committed grade of Plan 11f Task 8 (research row 12, nicotine withdrawal): an ANALYSIS script, not a
driver (it boots nothing). Written and committed before the first boot of the runs it grades; its output is a DERIVED
artifact folder (ruling T4-3: every number a row may cite is emitted by a committed script).

    python testing/experiments/x31_grade.py [--out testing/artifacts/x31-grade-YYYYMMDD]

The inputs are each session's artifact folder testing/artifacts/x31N-*/: the driver's document (nicotine-1.json ..
nicotine-3.json), events.json (the eats, the autoDrop drinks, the smoke and seed markers and the anchor edits'
setpath events, x31_nicotine_lib changes 3-7), start.json, start-stats.json, player.json and the minute-ring pages. The
tool is tools/replay_live.py at HEAD with the live server's sleep option (sleep_allowed false); the activity comes from
the ring's rate and exe and the stat NICOTINE_WITHDRAWAL from each ring row (the tool's feed).

Every session: the replay of live re-run and graded twice: the tool's own diff (HUNGER 0.002, es 0.005, L 0.5 %), and
this script's diff, which skips a row only for an eat, a drink, a smoke or seed marker, or a row an anchor edit's timing
holds (lib change 7), under HUNGER 0.002, es 0.005, L 0.5 % and satiety.nicH within one game minute (the live anchor is
the drain's own age, the replay's the ring row's: a sub-minute skew). A second replay of the same events with
K.satiety.NIC_MAX 0 is the no-nicotine counterfactual.

Row 12:
  - THE FACTOR: on every graded ring row (not held, not suspect or offline in the replay) whose live, replay and
    counterfactual HUNGER are all under the 0.69 cap: live HUNGER / counterfactual HUNGER against
    K.satiety.nicotineFactor(w, d) = 1 + NIC_MAX x clamp(w / 0.51, 0, 1) x clamp(1 - d / 182, 0, 1), within 1 %, where
    w is the stat the replay was fed for the drain that wrote the row (the ring row before it) and d the row's own
    (satiety.t - satiety.nicH) / 24 (the live anchor at the drain's age); the replay's own factor (replay /
    counterfactual against the formula on the replay's own anchor); grouped by regime: before the gate smoke, w 0, the
    rise and the cap with the anchor unfaded (d under 10 days), the fade edit's span, the T2-F span and after the
    second smoke;
  - the withdrawal on the ring: after the gate smoke (x311 into x312) and after the second smoke (x313), the first row
    above 0 (hours after the smoke), the slope over the rows strictly between 0 and the cap (per game hour), the first
    row at the cap, against the DayLength 1 arithmetic of #3630 with #2922 (x31_nicotine_lib.RISE_THRESHOLD_H 5.556 h,
    RISE_RATE_PER_H 0.01125 a game hour, 50.89 h to the cap);
  - the smokes: the stat before and after, the fall against min(before, 0.51), the timer, the counters, and the anchor
    the ring shows at the smoke's row and the row after (reset to the drain's age);
  - the anchor edits: the value set, what the drain laid, the placement (lib change 7) and the factor over each span;
  - the next-day intake by the oracles' mapping (650 x written / 0.25) over D2_20, D3_08 and D3_13 (three meals at the
    cap with the anchor unfaded): live and replay over the counterfactual, against S1576's next-day pin 1.1304 on the
    oracle (test_the_nicotine_replay_is_pinned) as a reading (the 48-day mean and week 26 are out of reach live,
    ruling 11f-4);
  - the eating reads: per meal the es read, the ring's and the replay's es at the read, the target and the kcal eaten;
    the live kcal per chain day;
  - the guard (exe, moving, asleep rows) and the drinking and sodium per chain day (x30_grade's form).
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
import x31_nicotine_lib as L  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
CHAIN = (("x311", "nicotine-1.json"), ("x312", "nicotine-2.json"), ("x313", "nicotine-3.json"))
MM_PER_HUNGER = 65.0 / 0.25            # ruling 11c-31's request-anchored mapping (an assumption)
H_REQ = 0.25
CAP = 0.69
FACTOR_TOL = 0.01
UNFADED_D = 10.0                       # an anchor under this many days old reads as unfaded (the fade over 10 d: 5.5 %)
TOL_MINE = {"HUNGER": ("abs", 0.002), "body.energyState": ("abs", 0.005), "satiety.L": ("rel", 0.005),
            "satiety.nicH": ("abs", 1.0 / 60)}
NEXT_DAY = ("D2_20", "D3_08", "D3_13")
ORACLE_PINS = {
    "next_day_intake": 1.1304, "mean48": 1.1135, "band": [1.08, 1.14], "next_day_tolerance_rel": 0.02,
    "source": "testing/tests/kernel/test_satiety_meal_studies.py (test_the_nicotine_replay_is_pinned PIN_NEXT, "
              "PIN_MEAN48; test_a_quitting_smokers_next_day_intake_sits_in_s1576s_band NIC_BAND)"}
RISE_PRED = {"threshold_h": L.RISE_THRESHOLD_H, "rate_per_h": L.RISE_RATE_PER_H,
             "to_cap_h": L.RISE_THRESHOLD_H + L.NIC_W_MAX / L.RISE_RATE_PER_H,
             "source": "#3630 with #2922 at DayLength 1 (x31_nicotine_lib RISE_THRESHOLD_H, RISE_RATE_PER_H)"}


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


def no_nicotine(fn):
    """fn() with every server replay built inside it reading K.satiety.NIC_MAX = 0 (the no-nicotine counterfactual:
    nicotineFactor reads 1 at every withdrawal; the anchor itself is still kept)."""
    init = RL.ServerReplay.__init__

    def patched(self, *a, **kw):
        init(self, *a, **kw)
        self.K.satiety.NIC_MAX = 0

    RL.ServerReplay.__init__ = patched
    try:
        return fn()
    finally:
        RL.ServerReplay.__init__ = init


def kernel():
    return L._kh_static().K


def held_rows(events):
    """The ring rows this script's diff and the factor skip: every eat, drink, smoke or seed marker's row and the rows
    an anchor edit's timing holds."""
    out = set()
    for e in events:
        if e.get("s") is None:
            continue
        if e.get("kind") in ("eat", "drink") or e.get("label") in ("smoke", "seed"):
            out.add(e["s"])
        if e.get("kind") == "setpath":
            out.add(e["s"])
            out.update(e.get("hold") or [])
    return out


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
        self.hold = held_rows(self.events)
        self.use = [r for r in self.ring if self.a0 is None or r["age"] > self.a0 + 1e-9]
        self.prev_of = {b["s"]: a for a, b in zip(self.use, self.use[1:])}
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
        rows_nf, _ = no_nicotine(run)
        self.nf_by = {r["s"]: r for r in rows_nf}

    def summary(self):
        kinds = {}
        for e in self.events:
            k = e.get("label") if e.get("label") in ("smoke", "seed") else e.get("kind")
            kinds[k] = kinds.get(k, 0) + 1
        return {"run_id": self.doc.get("run_id"), "rows": len(self.rows), "events_by_kind": kinds,
                "held_rows": len(self.hold),
                "ring_activity_events": len(getattr(getattr(self, "be", None), "ring_activity", None) or []),
                "tool_diff": {k: self.diff.get(k) for k in ("fields", "classes", "ok")} | {
                    "findings_n": len(self.diff.get("findings", [])), "findings": self.diff.get("findings", [])[:20]},
                "diff": {k: self.mine.get(k) for k in ("fields", "classes", "ok")} | {
                    "findings_n": len(self.mine.get("findings", [])), "findings": self.mine.get("findings", [])[:40]},
                "start_age": self.a0, "ring_first_age": self.ring[0]["age"] if self.ring else None,
                "ring_last_age": self.ring[-1]["age"] if self.ring else None,
                "drain_skew": drain_skew(self),
                "driver_verdicts": {k: v.get("verdict") for k, v in (self.doc.get("verdicts") or {}).items()}}


def drain_skew(S):
    """The live drain's own age (a ring row's satiety.t) past the age of the ring row before it (the replay's drain
    age): min, max and mean in game minutes over the session's rows."""
    xs = []
    for r in S.use:
        p = S.prev_of.get(r["s"])
        t = L.num(r.get(L.SAT_T))
        if p is None or t is None:
            continue
        xs.append((t - p["age"]) * 60)
    if not xs:
        return None
    return {"n": len(xs), "min_m": min(xs), "max_m": max(xs), "mean_m": sum(xs) / len(xs)}


def factor_row(S, r):
    """One ring row's factor reading, or None when the row is not graded (held, suspect or offline in the replay, the
    first row after the start record, or a value missing)."""
    K = kernel()
    rp, nf, p = S.rep_by.get(r["s"]), S.nf_by.get(r["s"]), S.prev_of.get(r["s"])
    if rp is None or nf is None or p is None or r["s"] in S.hold or rp.get("suspect") or rp.get("offline"):
        return None
    h, hr, hn = L.num(r.get("HUNGER")), L.num(rp.get("HUNGER")), L.num(nf.get("HUNGER"))
    w = L.num(p.get(L.NW))
    t, a = L.num(r.get(L.SAT_T)), L.num(r.get(L.NIC))
    tr, ar = L.num(rp.get(L.SAT_T)), L.num(rp.get(L.NIC))
    if None in (h, hr, hn, w, t, a, tr, ar) or hn <= 0:
        return None
    d, dr = (t - a) / 24.0, (tr - ar) / 24.0
    capped = h >= CAP - 1e-9 or hr >= CAP - 1e-9 or hn >= CAP - 1e-9
    f_ = float(K.satiety.nicotineFactor(w, d))
    fr_ = float(K.satiety.nicotineFactor(w, dr))
    f, fr = h / hn, hr / hn
    return {"s": r["s"], "age": r["age"], "w": w, "d": d, "d_replay": dr, "HUNGER": h, "HUNGER_replay": hr,
            "HUNGER_nofactor": hn, "factor": f, "factor_replay": fr, "formula": f_, "formula_replay": fr_,
            "capped": capped, "rel": None if capped else abs(f / f_ - 1),
            "rel_replay": None if capped else abs(fr / fr_ - 1), "gap": bool(rp.get("gap")),
            "mm": (h - hn) * MM_PER_HUNGER}


def regimes(S):
    """The session's regime bounds: the gate smoke's ring s (the seed's marker before it), the fade and T2-F edits'
    shown rows and the second smoke's ring s, read off the event log."""
    smokes = [e for e in S.events if e.get("label") == "smoke"]
    seed = next((e["s"] for e in S.events if e.get("label") == "seed"), None)
    ed = {e["label"]: e for e in S.events if e.get("kind") == "setpath"}
    return {"seed_s": seed, "smoke_s": [e["s"] for e in smokes], "smoke_labels": [e.get("smoke") for e in smokes],
            "fade_s": (ed.get("edit-fade") or {}).get("s"), "t2f_s": (ed.get("edit-t2f") or {}).get("s")}


def regime_of(x, rg, cap=None):
    """A graded row's regime (see regimes)."""
    cap = L.NIC_W_MAX - 1e-4 if cap is None else cap
    s = x["s"]
    g2 = [v for v, lab in zip(rg["smoke_s"], rg["smoke_labels"]) if lab == "G_SMOKE"]
    sm2 = [v for v, lab in zip(rg["smoke_s"], rg["smoke_labels"]) if lab != "G_SMOKE"]
    if g2 and s <= g2[0]:
        return "before_gate_smoke"
    if sm2 and s > sm2[0]:
        return "after_second_smoke_w0" if x["w"] <= 0 else "after_second_smoke"
    if rg["t2f_s"] is not None and s > rg["t2f_s"]:
        return "t2f"
    if rg["fade_s"] is not None and s > rg["fade_s"]:
        return "fade_edit"
    if x["w"] <= 0:
        return "w0"
    if x["d"] >= UNFADED_D:
        return "faded_other"
    return "cap" if x["w"] >= cap else "rise"


def segments(rows):
    out = {}
    for x in rows:
        out.setdefault((x["session"], x["regime"]), []).append(x)
    res = []
    for (sess, reg), xs in out.items():
        ok = [x for x in xs if x["rel"] is not None]
        res.append({"session": sess, "regime": reg, "rows": len(xs), "graded": len(ok), "capped": len(xs) - len(ok),
                    "age0": xs[0]["age"], "age1": xs[-1]["age"],
                    "w_min": min(x["w"] for x in xs), "w_max": max(x["w"] for x in xs),
                    "d_min": min(x["d"] for x in xs), "d_max": max(x["d"] for x in xs),
                    "formula_min": min((x["formula"] for x in ok), default=None),
                    "formula_max": max((x["formula"] for x in ok), default=None),
                    "factor_min": min((x["factor"] for x in ok), default=None),
                    "factor_max": max((x["factor"] for x in ok), default=None),
                    "factor_mean": (sum(x["factor"] for x in ok) / len(ok)) if ok else None,
                    "factor_over_formula_mean": (sum(x["factor"] / x["formula"] for x in ok) / len(ok)) if ok else None,
                    "max_rel": max((x["rel"] for x in ok), default=None),
                    "max_rel_replay": max((x["rel_replay"] for x in ok), default=None),
                    "ok": bool(ok) and max(x["rel"] for x in ok) <= FACTOR_TOL})
    res.sort(key=lambda x: x["age0"])
    return res


def meal_reads(S):
    """Per meal stop of the session: the ring row at or before the stop's read age (before its eats), its factor
    reading; the es read and the ring's and replay's es."""
    out = []
    for st in S.doc.get("stops") or []:
        if st.get("kind") not in L.MEAL_KINDS:
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


def next_day(meals):
    """The next-day intake by the oracles' mapping over NEXT_DAY (live and replay over the counterfactual), and each
    meal's factor triple."""
    by = {m["label"]: m for m in meals}
    xs = [by[x]["factor"] for x in NEXT_DAY if x in by and by[x]["factor"] and not by[x]["factor"]["capped"]]
    per = []
    for lab in NEXT_DAY:
        f = (by.get(lab) or {}).get("factor") or {}
        per.append({"label": lab, "w": f.get("w"), "d": f.get("d"), "factor": f.get("factor"),
                    "factor_replay": f.get("factor_replay"), "formula": f.get("formula"), "capped": f.get("capped")})
    if len(xs) != len(NEXT_DAY):
        return {"labels": list(NEXT_DAY), "per_meal": per, "live": None, "replay": None,
                "why": "a meal of the day is missing, not graded or capped"}
    live = sum(x["HUNGER"] for x in xs) / sum(x["HUNGER_nofactor"] for x in xs)
    rep = sum(x["HUNGER_replay"] for x in xs) / sum(x["HUNGER_nofactor"] for x in xs)
    pin = ORACLE_PINS["next_day_intake"]
    return {"labels": list(NEXT_DAY), "per_meal": per, "live": live, "replay": rep,
            "formula": sum(x["formula"] * x["HUNGER_nofactor"] for x in xs) / sum(x["HUNGER_nofactor"] for x in xs),
            "live_over_pin": live / pin, "within_2pct_of_pin": abs(live / pin - 1) <= ORACLE_PINS["next_day_tolerance_rel"],
            "kcal_live_minus_control": sum(650.0 * (x["HUNGER"] - x["HUNGER_nofactor"]) / H_REQ for x in xs)}


def smokes_reading(sessions):
    """Per smoke: the driver's reads and the anchor the ring shows at the smoke's marker row and the row after."""
    out = []
    for S in sessions:
        by = {r["s"]: r for r in S.ring}
        mk = {e.get("smoke"): e for e in S.events if e.get("label") == "smoke"}
        for st in S.doc.get("stops") or []:
            if st.get("kind") != "smoke":
                continue
            e = mk.get(st["label"])
            r = by.get(e["s"]) if e else None
            r1 = by.get(e["s"] + 1) if e else None
            row = {"session": S.pre, "label": st["label"]}
            row.update({k: st.get(k) for k in ("smoked", "w_before", "w_after", "fall", "fall_expected", "timer_before",
                                                "timer_after", "eats_rose", "landed_rose", "age_before", "age_after")})
            row["fall_minus_expected"] = (st["fall"] - st["fall_expected"]) if (
                st.get("fall") is not None and st.get("fall_expected") is not None) else None
            for tag, x in (("ring_row", r), ("ring_row_after", r1)):
                row[tag] = ({"s": x["s"], "age": x["age"], "w": x.get(L.NW), "nicH": x.get(L.NIC), "t": x.get(L.SAT_T),
                             "nicH_minus_t": (L.num(x.get(L.NIC)) - L.num(x.get(L.SAT_T)))
                             if L.num(x.get(L.NIC)) is not None and L.num(x.get(L.SAT_T)) is not None else None}
                            if x else None)
            out.append(row)
    return out


def edits_reading(sessions, frows):
    out = []
    for S in sessions:
        evs = {e["label"]: e for e in S.events if e.get("kind") == "setpath"}
        for st in S.doc.get("stops") or []:
            if st.get("kind") not in ("fade", "t2f"):
                continue
            e = evs.get("edit-" + st["kind"]) or {}
            row = {"session": S.pre, "label": st["label"], "kind": st["kind"]}
            row.update({k: st.get(k) for k in ("value", "before_age", "after_age", "laid", "laid_t", "w")})
            if st["kind"] == "t2f" and L.num(st.get("laid")) is not None and L.num(st.get("laid_t")) is not None:
                row["laid_days_back"] = (st["laid_t"] - st["laid"]) / 24.0
            if st["kind"] == "fade" and L.num(st.get("value")) is not None and L.num(st.get("before_age")) is not None:
                row["set_days_back"] = (st["before_age"] - st["value"]) / 24.0
            row["event"] = {k: e.get(k) for k in ("s", "placement", "hold", "shown_s")}
            out.append(row)
    return out


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


def withdrawal(sessions):
    """The withdrawal on the chain's ring after each completed smoke (the gate smoke's segment runs across the session
    boundary), against RISE_PRED."""
    ring = [r for S in sessions for r in S.ring]
    ages = []
    for S in sessions:
        ages += [st.get("age_after") for st in S.doc.get("stops") or [] if st.get("kind") == "smoke" and st.get("smoked")]
    segs = L.withdrawal_reading(ring, ages)
    for x in segs:
        f = x.get("first_above_0")
        x["threshold_minus_pred_h"] = (f["h_after_smoke"] - RISE_PRED["threshold_h"]) if f else None
        x["rate_over_pred"] = (x["slope_per_h"] / RISE_PRED["rate_per_h"]) if x.get("slope_per_h") else None
        c = x.get("at_cap")
        x["to_cap_minus_pred_h"] = (c["h_after_smoke"] - RISE_PRED["to_cap_h"]) if c else None
    return {"segments": segs, "pred": RISE_PRED}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = a.out or os.path.join(ART, "x31-grade-%s" % datetime.date.today().strftime("%Y%m%d"))
    os.makedirs(out, exist_ok=True)
    sessions = []
    for pre, doc in CHAIN:
        try:
            sessions.append(Sess(pre, doc))
        except SystemExit as e:
            print("skip %s: %s" % (pre, e))
    K = kernel()
    per, meals, frows = {}, [], []
    for S in sessions:
        doc = S.summary()
        rg = regimes(S)
        fr = []
        for r in S.ring:
            x = factor_row(S, r)
            if x is not None:
                x["session"] = S.pre
                x["regime"] = regime_of(x, rg)
                fr.append(x)
        frows += fr
        meals += [dict(m, session=S.pre) for m in meal_reads(S)]
        doc["regimes"] = rg
        doc["guard"] = L.guard_reading(S.ring)
        per[S.pre] = doc
        with open(os.path.join(out, S.pre + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True, default=str)
    graded = [x for x in frows if x["rel"] is not None]
    allf = {"graded": len(graded), "capped": len(frows) - len(graded),
            "graded_with_w": sum(1 for x in graded if x["w"] > 0),
            "graded_factor_above_1": sum(1 for x in graded if x["formula"] > 1 + 1e-9),
            "max_rel": max((x["rel"] for x in graded), default=None),
            "max_rel_replay": max((x["rel_replay"] for x in graded), default=None),
            "max_rel_with_w": max((x["rel"] for x in graded if x["w"] > 0), default=None),
            "ok": bool(graded) and max(x["rel"] for x in graded) <= FACTOR_TOL}
    segs = segments(frows)
    row12 = {"factor_all": allf, "segments": segs, "meals": meals, "next_day_intake": next_day(meals),
             "withdrawal": withdrawal(sessions), "smokes": smokes_reading(sessions),
             "edits": edits_reading(sessions, frows), "es_by_day": es_by_day(sessions),
             "kcal_by_day": kcal_by_day(sessions), "oracle_pins": ORACLE_PINS,
             "constants": {"NIC_MAX": float(K.satiety.NIC_MAX), "NIC_FADE_DAYS": float(K.satiety.NIC_FADE_DAYS),
                           "NIC_WITHDRAWAL_MAX": float(K.satiety.NIC_WITHDRAWAL_MAX)}}
    rows = {"row12": row12, "drinking_sodium": drinking_sodium(sessions)}
    with open(os.path.join(out, "rows.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, sort_keys=True, default=str)
    sm = row12["smokes"]
    verdicts = {
        "REPLAY_OK": {p: {"tool": d["tool_diff"]["ok"], "mine": d["diff"]["ok"]} for p, d in per.items()},
        "FACTOR": allf["ok"],
        "FACTOR_SEGMENTS": {"%s@%s" % (x["session"], x["regime"]): x["ok"] for x in segs},
        "SMOKES_FALL": {x["label"]: (x["fall_minus_expected"] is not None and abs(x["fall_minus_expected"]) <= 1e-4)
                        for x in sm},
        "SMOKES_NO_LANDING": {x["label"]: not x.get("landed_rose") for x in sm},
        "NEXT_DAY_WITHIN_2PCT": row12["next_day_intake"].get("within_2pct_of_pin"),
        "EXE_FALSE": {p: d["guard"]["exe_true_rows"] == 0 and d["guard"]["exe_present_rows"] > 0
                      and d["guard"]["asleep_rows"] == 0 for p, d in per.items()},
        "SODIUM_GRADE_MAX": rows["drinking_sodium"]["grade_max_chain"]}
    summ = {"tool_commit": _git("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
            "grade_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x31_grade.py"),
            "lib_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x31_nicotine_lib.py"),
            "sessions": [S.pre for S in sessions], "verdicts": verdicts}
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summ, fh, indent=1, sort_keys=True, default=str)
    print(json.dumps(verdicts, indent=1, default=str))


if __name__ == "__main__":
    main()
