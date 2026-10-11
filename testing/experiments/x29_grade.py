"""x29_grade -- the committed grade of Plan 11f Task 6 (research rows 9 and 10, exercise): an ANALYSIS script, not a
driver (it boots nothing). Written and committed before the first boot of the runs it grades; its output is a DERIVED
artifact folder (ruling T4-3: every number a row may cite is emitted by a committed script).

    python testing/experiments/x29_grade.py gate [--out testing/artifacts/x29-gate-YYYYMMDD]
    python testing/experiments/x29_grade.py lag  [--out testing/artifacts/x29-lag-YYYYMMDD]

The inputs are each session's artifact folder testing/artifacts/x29N-*/: the driver's document (gate-1.json, lag-N.json),
events.json (the eats, the autoDrop drinks, and x29_exercise_lib's activity and setpath events), start.json,
start-stats.json, player.json and the minute-ring pages. The tool is tools/replay_live.py at HEAD with the live server's
sleep option (sleep_allowed false).

Every session: the replay of live re-run, graded twice: the tool's own diff (HUNGER 0.002, es 0.005, L 0.5 %), whose
`between` rule skips the row before every event, the activity events included; and this script's diff, which skips a
row only for an eat, drink or setpath event (an activity event changes what the NEXT drain bills, so no ring row sits
between it and its effect; x29_exercise_lib change 2), under HUNGER 0.002, es 0.005, L 0.5 %, satiety.S 1e-6 and the
trail's closed exercise sum body.trail.c.ex 0.5 %.

gate (x291; row 9): per leg the ring's reading (the billed MET's max and histogram, the minutes at or above 6.0,
satiety.S's max and rises, band2Day's rise, the set's polls: the server's exercise names and engine rate); the decay
leg's S against the half-life decay (x29_exercise_lib.decay_reading, 1 %) and against the replay; the HUNGER factor:
on every ring row whose written HUNGER and the no-acute replay's (the same replay with K.satiety.ACUTE_MAX 0) are under
the 0.69 cap, live HUNGER / no-acute HUNGER against acuteFactor(S) = 1 - ACUTE_MAX x S on that row (1 %); the study
distance as readings: the replay oracle's 0.674 of control over a 60 min aerobic bout and -3.7 mm at 30 min after it
(testing/tests/kernel/test_satiety_activity.py test_the_bout_replay_pins_its_readings), against live's own mm
difference (live less no-acute, x 260 mm a unit, ruling 11c-31) 30 min after the set and, where a candidate reached
vigour, its mean ratio over the vigorous span.

lag (x292..x296; row 10): per session the agreement of satiety.L, es and body.trail.c.ex with the replay (0.5 %); per
bout its billed exercise kcal off the ring (exKcalDay's rise from the bout's start to 15 game minutes past its end);
L at each day's end and at 15:00 each day; the billed exercise kcal per chain day (every MET above the idle 1.3, the
post-bout tail included: x291 billed 1.9-2.0 for the hour after burpees) and the tail's return to idle; the lag's
share lagged(L) / bout kcal (K.energy.lagged: EX_LAG_GAIN x L) at each day's end and at 15:00 on day 7 (seven days
after day 0's bout), against the day's bout, the mean bout and the mean whole day's exercise kcal (days 1-6); the
server-path oracle's arm (test_replay_live_energy.py lag_run: the 70 kg man, Running15kmh for 53 min at 02:00, meals of
the idle day plus the bout) read at the same day ends and seven days after its first bout, and the oracles' pins
(Whybrow over days 3-16 0.2985, day 1 0.0414; E-MECHANIC 0.70 at 24 weeks; King 2011 at steady state 0.92 mm) as
readings; the drinking and the sodium per chain day (x28_grade's form).
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
import x29_exercise_lib as L  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
GATE = ("x291",)
CHAIN = ("x292", "x293", "x294", "x295", "x296")
MM_PER_HUNGER = 65.0 / 0.25            # ruling 11c-31's request-anchored mapping (an assumption)
CAP = 0.69
FACTOR_TOL = 0.01
LAG_TOL = 0.005
TOL_MINE = {"HUNGER": ("abs", 0.002), "body.energyState": ("abs", 0.005), "satiety.L": ("rel", 0.005),
            "satiety.S": ("abs", 1e-6), "body.trail.c.ex": ("rel", 0.005)}
ORACLE_PINS = {
    "bout_mean_ratio_60min_aerobic": 0.674, "mm_30min_after": -3.7,
    "source_bout": "testing/tests/kernel/test_satiety_activity.py test_the_bout_replay_pins_its_readings",
    "whybrow_days_3_16": 0.2985, "whybrow_day_1": 0.0414, "e_mechanic_24wk": 0.7, "king_2011_mm": 0.92,
    "source_lag": "testing/tests/kernel/test_replay_live_energy.py (test_whybrow_on_the_server_path, "
                  "test_e_mechanic_on_the_server_path, READ['king'])"}
ARM_RATE = {"Running15kmh": 9.5, "idle": 1.5}


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


def no_acute(fn):
    """fn() with every server replay built inside it reading K.satiety.ACUTE_MAX = 0 (the no-acute counterfactual)."""
    init = RL.ServerReplay.__init__

    def patched(self, *a, **kw):
        init(self, *a, **kw)
        self.K.satiety.ACUTE_MAX = 0

    RL.ServerReplay.__init__ = patched
    try:
        return fn()
    finally:
        RL.ServerReplay.__init__ = init


class Sess:
    def __init__(self, pre, doc_name, counterfactual=False):
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
        if not self.ring:
            self.rows, self.diff, self.mine, self.rep_by, self.na_by = [], {"ok": None}, {"ok": None}, {}, {}
            return
        run = lambda: RL.replay_live(self.ring, self.events, self.start, paths=self.rpaths, user=L.USER,  # noqa: E731
                                     player=self.player, start_stats=self.stats, sleep_allowed=L.SLEEP_ALLOWED)
        self.rows, _ = run()
        self.diff = RL.diff(self.rows, self.ring)
        hold = {e["s"] for e in self.events if e.get("kind") in ("eat", "drink", "setpath") and e.get("s") is not None}
        mine = []
        for r in self.rows:
            x = dict(r)
            x["between"] = r["s"] in hold
            mine.append(x)
        self.mine = RL.diff(mine, self.ring, TOL_MINE)
        self.rep_by = {r["s"]: r for r in self.rows}
        self.na_by = {}
        if counterfactual:
            rows_na, _ = no_acute(run)
            self.na_by = {r["s"]: r for r in rows_na}

    def summary(self):
        kinds = {}
        for e in self.events:
            kinds[e.get("kind")] = kinds.get(e.get("kind"), 0) + 1
        return {"run_id": self.doc.get("run_id"), "rows": len(self.rows), "events_by_kind": kinds,
                "tool_diff": {k: self.diff.get(k) for k in ("fields", "classes", "ok")} | {
                    "findings_n": len(self.diff.get("findings", [])), "findings": self.diff.get("findings", [])[:20]},
                "diff": {k: self.mine.get(k) for k in ("fields", "classes", "ok")} | {
                    "findings_n": len(self.mine.get("findings", [])), "findings": self.mine.get("findings", [])[:40]},
                "start_age": self.a0, "ring_first_age": self.ring[0]["age"] if self.ring else None,
                "ring_last_age": self.ring[-1]["age"] if self.ring else None,
                "driver_verdicts": {k: v.get("verdict") for k, v in (self.doc.get("verdicts") or {}).items()}}


# --- gate (row 9) ----------------------------------------------------------------------------------------------------

def factor_rows(S, a0=None, a1=None, min_S=None):
    """Per ring row (age in (a0, a1]): live HUNGER / no-acute HUNGER against 1 - ACUTE_MAX x S, both under the cap."""
    amax = float(L._kh_static().K.satiety.ACUTE_MAX)
    hold = {e["s"] for e in S.events if e.get("kind") in ("eat", "drink", "setpath") and e.get("s") is not None}
    out = []
    for r in S.ring:
        if a0 is not None and r["age"] <= a0:
            continue
        if a1 is not None and r["age"] > a1 + 1e-9:
            continue
        na = S.na_by.get(r["s"])
        h, s_ = L.num(r.get("HUNGER")), L.num(r.get("satiety.S"))
        hn = L.num(na.get("HUNGER")) if na else None
        if h is None or hn is None or s_ is None or hn <= 0 or r["s"] in hold:
            continue
        if min_S is not None and s_ < min_S:
            continue
        capped = h >= CAP - 1e-9 or hn >= CAP - 1e-9
        f = h / hn
        p = 1 - amax * min(max(s_, 0.0), 1.0)
        out.append({"s": r["s"], "age": r["age"], "S": s_, "HUNGER": h, "HUNGER_noacute": hn, "factor": f, "pred": p,
                    "rel": None if capped else abs(f / p - 1), "capped": capped,
                    "mm": (h - hn) * MM_PER_HUNGER})
    return out


def row_at(rows, age):
    return L.row_at(rows, age)


def gate(out):
    S = Sess("x291", "gate-1.json", counterfactual=True)
    doc = S.summary()
    hl = float(L._kh_static().K.satiety.ACUTE_DECAY_HALF_LIFE_H)
    legs = []
    for leg in S.doc.get("legs") or []:
        a0, a1 = L.num(leg.get("age0")), L.num(leg.get("age1"))
        row = {"label": leg["label"], "kind": leg["kind"], "age0": a0, "age1": a1,
               "ring": L.leg_reading(S.ring, a0, a1) if (a0 is not None and a1 is not None) else None}
        st = leg.get("set")
        if st:
            polls = st.get("polls") or []
            row["set"] = {"started": st.get("started"), "ended": st.get("ended"), "age_queued": st.get("age_queued"),
                          "age_end": st.get("age_end"), "polls": len(polls),
                          "exe_seen": sorted({str(p.get("exe")) for p in polls}),
                          "rate_max": max([p["rate"] for p in polls if p.get("rate") is not None], default=None),
                          "rates": [p.get("rate") for p in polls], "mets": [p.get("met") for p in polls]}
        if leg.get("windows") is not None:
            states = {}
            for w in leg["windows"]:
                for x in w.get("states") or []:
                    states[str(x.get("state"))] = states.get(str(x.get("state")), 0) + 1
            row["melee"] = {"windows": len(leg["windows"]), "states": states, "misses": leg.get("misses"),
                            "hordes": len(leg.get("hordes") or []),
                            "results": [{k: L.g(w, "result", k) for k in ("swings", "targetDead", "returns")}
                                        for w in leg["windows"]]}
        rr = row.get("ring") or {}
        if (rr.get("S_rises") or 0) > 0 and a0 is not None:
            vig = [x["age"] for x in rr["S_rise_rows"]]
            span = factor_rows(S, a0, max(vig))
            ok = [x for x in span if x["rel"] is not None]
            last = max(vig)
            r30 = row_at([x for x in factor_rows(S, a0, a1 + 2.0)], last + 0.5)
            row["vigorous_span"] = {"first_age": min(vig), "last_age": last, "rows": len(span),
                                    "mean_ratio": (sum(x["factor"] for x in ok) / len(ok)) if ok else None,
                                    "mm_30min_after_last": r30["mm"] if r30 else None}
        legs.append(row)
    decay = L.decay_reading(S.ring, S.events, hl)
    for d in decay:
        e = d["event"]
        for x in d["rows"]:
            rp = S.rep_by.get(x["s"])
            x["S_replay"] = L.num(rp.get("satiety.S")) if rp else None
            x["replay_diff"] = (x["S"] - x["S_replay"]) if x["S_replay"] is not None else None
        sp = next((s for s in S.doc.get("setpaths") or [] if s.get("label") == e.get("label")), {})
        a_set = L.num(sp.get("age_after")) or L.num(sp.get("age_before"))
        fr = factor_rows(S, a_set - 1.0 / 60, a_set + 1.0) if a_set is not None else []
        okf = [x["rel"] for x in fr if x["rel"] is not None]
        r30 = row_at(fr, a_set + 0.5) if a_set is not None else None
        rd = [abs(x["replay_diff"]) for x in d["rows"] if x["replay_diff"] is not None]
        d["factor"] = {"rows": fr, "graded": len(okf), "max_rel": max(okf) if okf else None,
                       "ok": bool(okf) and max(okf) <= FACTOR_TOL}
        d["replay_S_max_diff"] = max(rd) if rd else None
        d["mm_30min_after_set"] = r30["mm"] if r30 else None
        d["S_30min_after_set"] = r30["S"] if r30 else None
        d["age_set"] = a_set
    allf = factor_rows(S, min_S=1e-3)
    okall = [x["rel"] for x in allf if x["rel"] is not None]
    rows = {"legs": legs, "decay": decay, "half_life_h": hl,
            "factor_all_S_over_1e-3": {"graded": len(okall), "max_rel": max(okall) if okall else None,
                                       "ok": bool(okall) and max(okall) <= FACTOR_TOL},
            "oracle_pins": ORACLE_PINS}
    with open(os.path.join(out, "x291.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, default=str)
    with open(os.path.join(out, "rows.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"row9": rows}, fh, indent=1, sort_keys=True, default=str)
    vig = {x["label"]: (x.get("ring") or {}).get("S_rises", 0) > 0 for x in legs if x["kind"] in ("exercise", "melee")}
    return {"VIGOUR": vig,
            "DECAY_HALF_LIFE": all(d["ok"] for d in decay) if decay else None,
            "DECAY_FACTOR": all(d["factor"]["ok"] for d in decay) if decay else None,
            "FACTOR_ALL": rows["factor_all_S_over_1e-3"]["ok"],
            "REPLAY_OK": {"tool": S.diff.get("ok"), "mine": S.mine.get("ok")}}


# --- lag (row 10) ----------------------------------------------------------------------------------------------------

def rel(a, b, floor):
    if a is None or b is None:
        return None
    return abs(a - b) / max(abs(b), floor)


def lag_agreement(S):
    hold = {e["s"] for e in S.events if e.get("kind") in ("eat", "drink", "setpath") and e.get("s") is not None}
    out = {}
    for f, floor in (("satiety.L", 1.0), ("body.energyState", 1.0), ("body.trail.c.ex", 1.0)):
        n, worst, over = 0, 0.0, 0
        for r in S.rows:
            if r["s"] in hold or r.get("suspect") or r.get("offline"):
                continue
            lv = S.ring_by.get(r["s"])
            if lv is None:
                continue
            d = rel(L.num(lv.get(f)), L.num(r.get(f)), floor)
            if d is None:
                continue
            n += 1
            worst = max(worst, d)
            over += d > LAG_TOL
        out[f] = {"n": n, "max_rel": worst, "over": over, "ok": n > 0 and over == 0}
    return out


def bouts(sessions):
    out = []
    for S in sessions:
        for st in S.doc.get("stops") or []:
            if st.get("kind") != "bout":
                continue
            a0, a1 = L.num(st.get("age0")), L.num(st.get("age1"))
            rr = L.leg_reading(S.ring, a0, a1 + 0.25) if (a0 is not None and a1 is not None) else {}
            out.append({"label": st["label"], "session": S.pre, "day": L.day_of(st["sched_age"]), "age0": a0,
                        "age1": a1, "kcal_ring": rr.get("exKcal_rise"), "kcal_read": st.get("bout_kcal"),
                        "met_max": rr.get("met_max"), "met_hist": rr.get("met_hist"),
                        "minutes_at_or_over_6": rr.get("minutes_at_or_over_6"), "S_max": rr.get("S_max"),
                        "sets": len(st.get("sets") or []),
                        "sets_started": sum(1 for s in st.get("sets") or [] if s.get("started"))})
    return out


def ex_by_day(ring):
    """The billed exercise kcal per chain day (from 00:00): the sum of exKcalDay's non-negative rises between
    consecutive ring rows (the mod day's close at 07:00 resets it: that row's rise is lost, named), with the ring's
    hours that day; and the post-exercise tail: the game hours from each day's last row billing at or above 1.9 MET
    after 15:00 back to the idle 1.3."""
    out = {}
    for p, r in zip(ring, ring[1:]):
        d = L.day_of(r["age"])
        x = out.setdefault(d, {"kcal": 0.0, "hours": 0.0, "resets": 0})
        a, b = L.num(p.get(L.EXK)), L.num(r.get(L.EXK))
        if a is not None and b is not None:
            if b >= a:
                x["kcal"] += b - a
            else:
                x["resets"] += 1
        if L.day_of(p["age"]) == d:
            x["hours"] += r["age"] - p["age"]
    for d, x in out.items():
        x["complete"] = x["hours"] > 23.5
        rows = [r for r in ring if L.day_of(r["age"]) == d and r["age"] >= L.at(d, 15.0)]
        hi = [r for r in rows if (L.num(r.get(L.MET)) or 0) >= 1.9 - 1e-9]
        idle = [r for r in rows if hi and r["age"] > hi[-1]["age"] and (L.num(r.get(L.MET)) or 0) <= 1.3 + 1e-9]
        x["tail_back_to_idle_age"] = idle[0]["age"] if idle else None
    return out


def lag_series(sessions, bl):
    K = L._kh_static().K
    ring = [r for S in sessions for r in S.ring]
    kc = {b["day"]: b["kcal_ring"] for b in bl if b["kcal_ring"] is not None}
    mean_k = (sum(kc.values()) / len(kc)) if kc else None
    exd = ex_by_day(ring)
    full = [x["kcal"] for d, x in exd.items() if x["complete"] and 1 <= d <= 6]
    mean_day = (sum(full) / len(full)) if full else None
    days = []
    for d in range(0, 8):
        row = {"day": d}
        for name, a in (("at_1500", L.at(d, 15.0)), ("end", L.at(d, 24.0))):
            r = L.row_at(ring, a)
            if r is None or r["age"] < a - 0.25:
                row[name] = None
                continue
            Lv = L.num(r.get("satiety.L"))
            lag = float(K.energy.lagged(Lv)) if Lv is not None else None
            k = kc.get(d) if name == "end" else kc.get(d - 1)
            row[name] = {"age": a, "row_age": r["age"], "s": r["s"], "L": Lv, "lagged": lag,
                         "es": r.get("body.energyState"), "trail_c_ex": r.get("body.trail.c.ex"),
                         "share_day_bout": (lag / k) if (lag is not None and k) else None,
                         "share_mean_bout": (lag / mean_k) if (lag is not None and mean_k) else None,
                         "share_mean_day_ex": (lag / mean_day) if (lag is not None and mean_day) else None}
        days.append(row)
    return {"by_day": days, "bout_kcal_by_day": kc, "mean_bout_kcal": mean_k,
            "ex_kcal_by_day": {str(d): x for d, x in sorted(exd.items())}, "mean_day_ex_kcal_days_1_6": mean_day,
            "reading_7_days_after_first_bout": days[7]["at_1500"] if len(days) > 7 else None}


def oracle_arm(days=8):
    """test_replay_live_energy.py's lag_run, Whybrow's high dose (the 70 kg man, Running15kmh 53 min at 02:00, meals of
    the idle day plus the bout at FAST_MEAL_H), stepped `days` days at one minute; the share lagged(L) / the day's
    bout kcal at each day's end and seven days after the first bout."""
    sys.path.insert(0, os.path.join(REPO, "testing"))
    from tests.kernel import test_satiety_meal_studies as M    # noqa: E402
    be0 = RL.ServerReplay(start=None, user=L.USER, sleep_allowed=None)
    K = be0.K
    b = K.body.new(70.0, 1, be0.rt.table(), 5, 1, 1, 0)
    idle = K.energy.ree(b.lm) + (K.energy.COMPENDIUM.Default - K.energy.MET_REST) * 70.0 * 24
    kcal = 3.5 * 1000 / 4.184
    per = (K.energy.COMPENDIUM.Running15kmh - K.energy.COMPENDIUM.Default) * 70.0 / 60.0
    bout = int(round(kcal / per))
    ev = []
    for d in range(days):
        ev.append({"minute": d * 1440 + 120, "kind": "activity", "rate": ARM_RATE["Running15kmh"]})
        ev.append({"minute": d * 1440 + 120 + bout, "kind": "activity", "rate": ARM_RATE["idle"]})
        for h in M.FAST_MEAL_H:
            ev.append({"minute": int(d * 1440 + h * 60), "kind": "meal", "size": (idle + kcal) / 3})
    ev.sort(key=lambda e: e["minute"])
    rows, be = RL.replay_arm(ev, minutes=days * 1440, dtM=1, backend="server", paths=("satiety.L", "body.exKcalDay"),
                             player={"weight": 70.0, "female": False}, rng="half")
    k = [rows[d * 1440 + 120 + bout - 1]["body.exKcalDay"] - rows[d * 1440 + 119]["body.exKcalDay"] for d in range(days)]
    ends = [{"day": d, "share": float(be.K.energy.lagged(rows[d * 1440 + 1439]["satiety.L"])) / k[d]}
            for d in range(days)]
    seven = 7 * 1440 + 120 - 1
    return {"bout_min": bout, "bout_kcal": k, "share_at_day_end": ends,
            "share_7_days_after_first_bout": float(be.K.energy.lagged(rows[seven]["satiety.L"])) / k[6],
            "mean_share_days_3_to_7_ends": sum(x["share"] for x in ends[2:7]) / 5}


def drinking_sodium(sessions):
    K = L._kh_static().K
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
            sw = L.num(r.get("fluids.sweat6h"))
            if sw is not None:
                d["sweat6h_max"] = max(d.get("sweat6h_max", sw), sw)
            prev = r
    for d in out.values():
        d["grade_max"] = L.hypo_grade(d.get("naPlasma_min"))
        d["complete"] = d.get("ring_hours", 0) > 23.5
    return {"by_day": dict(sorted(out.items(), key=lambda kv: int(kv[0]))),
            "BASAL_NA": float(K.fluids.BASAL_NA),
            "grade_max_chain": max((d["grade_max"] for d in out.values() if d.get("grade_max") is not None),
                                   default=None)}


def lag(out):
    sessions = []
    for n, pre in enumerate(CHAIN, 1):
        try:
            sessions.append(Sess(pre, "lag-%d.json" % n))
        except SystemExit as e:
            print("skip %s: %s" % (pre, e))
    per = {}
    for S in sessions:
        doc = S.summary()
        doc["lag_agreement"] = lag_agreement(S)
        per[S.pre] = doc
        with open(os.path.join(out, S.pre + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True, default=str)
    bl = bouts(sessions)
    series = lag_series(sessions, bl)
    rows = {"row10": {"bouts": bl, "series": series, "oracle_arm": oracle_arm(), "oracle_pins": ORACLE_PINS,
                      "agreement": {p: d["lag_agreement"] for p, d in per.items()}},
            "drinking_sodium": drinking_sodium(sessions)}
    with open(os.path.join(out, "rows.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, sort_keys=True, default=str)
    return {"LAG_AGREEMENT": {p: all(v["ok"] for v in d["lag_agreement"].values()) for p, d in per.items()},
            "REPLAY_OK": {p: {"tool": d["tool_diff"]["ok"], "mine": d["diff"]["ok"]} for p, d in per.items()},
            "SODIUM_GRADE_MAX": rows["drinking_sodium"]["grade_max_chain"]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("part", choices=("gate", "lag"))
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = a.out or os.path.join(ART, "x29-%s-%s" % (a.part, datetime.date.today().strftime("%Y%m%d")))
    os.makedirs(out, exist_ok=True)
    verdicts = gate(out) if a.part == "gate" else lag(out)
    summ = {"tool_commit": _git("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
            "grade_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x29_grade.py"),
            "lib_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x29_exercise_lib.py"),
            "part": a.part, "verdicts": verdicts}
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summ, fh, indent=1, sort_keys=True, default=str)
    print(json.dumps(verdicts, indent=1, default=str))


if __name__ == "__main__":
    main()
