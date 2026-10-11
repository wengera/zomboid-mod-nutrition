"""x35_grade -- the committed grade of Plan 11f Task 6r (research rows 9 and 10 re-run under the C-17 activity billing,
rulings C17-1, C17-3, C17-5): an ANALYSIS script, not a driver (it boots nothing). Written and committed before the
first boot of the runs it grades; its output is a DERIVED artifact folder (ruling T4-3: every number a row may cite is
emitted by a committed script).

    python testing/experiments/x35_grade.py [--out testing/artifacts/x35-grade-YYYYMMDD]

The inputs are each session's artifact folder testing/artifacts/x35N-*/ (x351, x352, x353): the driver's document
(lag-N.json), events.json (the eats, the autodrop sips and the movement events x35_exercise_lib took off the ring),
start.json, start-stats.json, player.json and the minute-ring pages. The tool is tools/replay_live.py at HEAD with the
live server's sleep option (sleep_allowed false); it takes the raw rate and the exercise flag off the ring itself
(ring_activity_events), so the replay's billing is the mod's own on the engine's fields (ruling C17-3).

Every session: the replay of live re-run, graded by the tool's own diff (HUNGER 0.002, es 0.005, L 0.5 %) and by this
script's diff, which skips a row only for an eat, drink or autodrop event (an activity event changes what the NEXT
drain bills), under HUNGER 0.002, es 0.005, L 0.5 %, satiety.S 1e-6 and body.trail.c.ex 0.5 %; the billed MET
(body.met) row by row against the replay's (MET_TOL), each mismatch listed with the ring's flags; the after-burn pool
body.epoc against the replay (0.5 %, floor 1 kcal).

row 9 (x351's B0: one burpee set, then three game hours at rest at speed 1):
  BILLED_6_FROM_FIRST: the drain of the set's first flagged ring row bills Fitness (6.0) on the next row, the drain
    before it does not, and every flagged drain's next row bills 6.0 but at most one at each flagged run's edges;
  EXE_END: the ring's first unflagged row after the set within one row of the engine rate's first falling sample, and
    within one row of the driver's first poll reading the flag clear (the poll's own resolution named);
  IDLE_AFTER: the first unflagged drain (the flag's clear minute counts as falling) and every later still drain in the
    rest bill the idle Default (1.3): tail rows at most 1, against x29's 445-469 kcal tail (the C-17 report's live
    readings, carried as the before);
  EPOC: the pool off the ring row by row against its own step (pool + 0.10 x the drain's exercise kcal, released
    1 - exp(-dt / 30 game min), dt off satiety.t; max relative error), and the released total (the inflows less the
    pool's rise over the window) against EPOC_F x the set's exercise kcal (exKcalDay's rise over the set), 1 %;
  S_RISE and S_DECAY: on every drain billing 6.0 S steps toward the resistance weight on ACUTE_HALF_LIFE_H, on every
    other toward 0 on ACUTE_DECAY_HALF_LIFE_H (the exact step on satiety.t; graded where the prediction is >= 1e-4);
  FACTOR: live HUNGER over a no-acute replay's (K.satiety.ACUTE_MAX 0) against 1 - ACUTE_MAX x S, both under the 0.69
    cap, from a minute before the set to the rest's end (1 %); and live HUNGER against the replay's there;
  the study distance as readings: the mean live / no-acute ratio over the set and the mm difference 30 min after it
    (ruling 11c-31's 65 mm a quarter), against the oracle's 0.674 and -3.7 mm (a 60 min aerobic bout; the kinds
    differ, so the distance is named, not graded); the paired client/server HUNGER reads within one wall second.
walk leg (x353's B5): every drain read moving with the raw rate falling (the ring's sample) bills at most
  Walking5kmh (3.8, C17-5); the moving drains' MET histogram.
row 10 (the chain): per session satiety.L, es, body.trail.c.ex and body.epoc against the replay (0.5 %); per bout its
  billed exercise kcal off the ring (exKcalDay's rise over the bout's start to its rest's end); the exercise kcal per
  chain day; L, lagged(L) = EX_LAG_GAIN x L and es at each day's end and at 15:00 each day; the lag's share at 15:00 on
  day 5 (five days after B0, the chain's last bout) against the mean complete day's exercise kcal (days 1-4), the mean
  bout and the day-4 bout; the server-path oracle arm (Whybrow's lag_run on the 70 kg man, x29_grade's) read five
  days after its first bout and at each day's end; x29's committed series (testing/artifacts/x29-lag-20261011) read at
  the same point as the before (its share against its own days 1-6 denominator and against days 1-4 recomputed); the
  oracles' pins as readings.
gaps: every break in the ring across the chain (the attaches between sessions, offline rows, the tool's gap rows),
  each with whether it falls inside a bout's three hours after its set (the after-burn's window).
drinking and sodium per chain day (x29_grade's form).
"""
import argparse
import datetime
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import replay_live as RL  # noqa: E402
import x35_exercise_lib as L  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
CHAIN = ("x351", "x352", "x353")
ROW9_BOUT = "B0"
WALK_BOUT = "B5"
LAST_DAY = 5                           # the share read at 15:00 on this day (five days after B0)
X29_LAG = "x29-lag-20261011"
X29_TAIL_KCAL = (445.0, 469.0)         # the C-17 report: the live tail after a 1 h set before the fix (task-c17-fix-report)
MM_PER_HUNGER = 65.0 / 0.25            # ruling 11c-31's request-anchored mapping (an assumption)
CAP = 0.69
FACTOR_TOL = 0.01
LAG_TOL = 0.005
EPOC_TOL = 0.01
MET_TOL = 1e-9
REST_H = 3.0                           # row 9's rest, and every bout's after-burn window for the gap check
TOL_MINE = {"HUNGER": ("abs", 0.002), "body.energyState": ("abs", 0.005), "satiety.L": ("rel", 0.005),
            "satiety.S": ("abs", 1e-6), "body.trail.c.ex": ("rel", 0.005)}
HOLD_KINDS = ("eat", "drink", "autodrop")
ORACLE_PINS = {
    "bout_mean_ratio_60min_aerobic": 0.674, "mm_30min_after": -3.7,
    "source_bout": "testing/tests/kernel/test_satiety_activity.py test_the_bout_replay_pins_its_readings",
    "whybrow_days_3_16": 0.2985, "whybrow_day_1": 0.0414, "e_mechanic_24wk": 0.7, "king_2011_mm": 0.92,
    "source_lag": "testing/tests/kernel/test_replay_live_energy.py (test_whybrow_on_the_server_path, "
                  "test_e_mechanic_on_the_server_path, READ['king'])",
    "x29_share_7_days": 0.2500, "x29_tail_kcal": list(X29_TAIL_KCAL)}
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


def K():
    return L._kh_static().K


class Sess:
    def __init__(self, pre, doc_name, counterfactual=False, run_dir=None):
        self.pre = pre
        self.dir = run_dir or folder(pre)
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
        self.hold = {e["s"] for e in self.events if e.get("kind") in HOLD_KINDS and e.get("s") is not None}
        if not self.ring:
            self.rows, self.diff, self.mine, self.rep_by, self.na_by = [], {"ok": None}, {"ok": None}, {}, {}
            return
        run = lambda: RL.replay_live(self.ring, self.events, self.start, paths=self.rpaths, user=L.USER,  # noqa: E731
                                     player=self.player, start_stats=self.stats, sleep_allowed=L.SLEEP_ALLOWED)
        self.rows, be = run()
        self.ring_activity_n = len(getattr(be, "ring_activity", None) or [])
        self.diff = RL.diff(self.rows, self.ring)
        mine = []
        for r in self.rows:
            x = dict(r)
            x["between"] = r["s"] in self.hold
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
                "ring_activity_events": getattr(self, "ring_activity_n", None),
                "tool_diff": {k: self.diff.get(k) for k in ("fields", "classes", "ok")} | {
                    "findings_n": len(self.diff.get("findings", [])), "findings": self.diff.get("findings", [])[:20]},
                "diff": {k: self.mine.get(k) for k in ("fields", "classes", "ok")} | {
                    "findings_n": len(self.mine.get("findings", [])), "findings": self.mine.get("findings", [])[:40]},
                "start_age": self.a0, "ring_first_age": self.ring[0]["age"] if self.ring else None,
                "ring_last_age": self.ring[-1]["age"] if self.ring else None,
                "driver_verdicts": {k: v.get("verdict") for k, v in (self.doc.get("verdicts") or {}).items()}}

    def bout(self, label):
        return next((st for st in self.doc.get("stops") or [] if st.get("kind") == "bout" and st.get("label") == label),
                    None)


# --- every session -----------------------------------------------------------------------------------------------------

def rel(a, b, floor):
    if a is None or b is None:
        return None
    return abs(a - b) / max(abs(b), floor)


def agreement(S):
    """satiety.L, es, the trail's closed exercise sum and the after-burn pool against the replay (0.5 %), skipping only
    the held rows (eat, drink, autodrop), suspect and offline ones."""
    out = {}
    for f, floor in (("satiety.L", 1.0), ("body.energyState", 1.0), ("body.trail.c.ex", 1.0), (L.EPOC, 1.0)):
        n, worst, over, worst_s = 0, 0.0, 0, None
        for r in S.rows:
            if r["s"] in S.hold or r.get("suspect") or r.get("offline"):
                continue
            lv = S.ring_by.get(r["s"])
            if lv is None:
                continue
            d = rel(L.num(lv.get(f)), L.num(r.get(f)), floor)
            if d is None:
                continue
            n += 1
            if d > worst:
                worst, worst_s = d, r["s"]
            over += d > LAG_TOL
        out[f] = {"n": n, "max_rel": worst, "worst_s": worst_s, "over": over, "ok": n > 0 and over == 0}
    return out


def met_agreement(S):
    """The billed MET (body.met) on every graded row against the replay's: matches within MET_TOL, and each mismatch
    with the ring's exe, moving and raw rate on the row and the row before (the drain's own sample)."""
    n, same, bad = 0, 0, []
    for r in S.rows:
        if r.get("suspect") or r.get("offline"):
            continue
        lv = S.ring_by.get(r["s"])
        a, b = L.num(r.get(L.MET)), (L.num(lv.get(L.MET)) if lv else None)
        if a is None or b is None:
            continue
        n += 1
        if abs(a - b) <= MET_TOL:
            same += 1
            continue
        prev = S.ring_by.get(r["s"] - 1) or {}
        bad.append({"s": r["s"], "age": lv.get("age"), "live": b, "replay": a, "exe": lv.get("exe"),
                    "exe_prev": prev.get("exe"), "moving": lv.get("moving"), "moving_prev": prev.get("moving"),
                    "rate": lv.get("rate"), "rate_prev": prev.get("rate"), "gap": bool(r.get("gap")),
                    "between": bool(r.get("between"))})
    return {"n": n, "same": same, "mismatches": len(bad), "rows": bad[:60]}


# --- row 9 -------------------------------------------------------------------------------------------------------------

def window(ring, a0, a1):
    return [r for r in ring if a0 < r["age"] <= a1 + 1e-9]


def factor_rows(S, a0, a1):
    """Per ring row with a0 < age <= a1: live HUNGER / no-acute HUNGER against 1 - ACUTE_MAX x S (both under the cap),
    and live HUNGER against the replay's."""
    amax = float(K().satiety.ACUTE_MAX)
    out = []
    for r in window(S.ring, a0, a1):
        na, rp = S.na_by.get(r["s"]), S.rep_by.get(r["s"])
        h, s_ = L.num(r.get("HUNGER")), L.num(r.get("satiety.S"))
        hn = L.num(na.get("HUNGER")) if na else None
        hr = L.num(rp.get("HUNGER")) if rp else None
        if h is None or hn is None or s_ is None or hn <= 0 or r["s"] in S.hold:
            continue
        capped = h >= CAP - 1e-9 or hn >= CAP - 1e-9
        f = h / hn
        p = 1 - amax * min(max(s_, 0.0), 1.0)
        out.append({"s": r["s"], "age": r["age"], "S": s_, "HUNGER": h, "HUNGER_noacute": hn, "HUNGER_replay": hr,
                    "factor": f, "pred": p, "rel": None if capped else abs(f / p - 1), "capped": capped,
                    "replay_abs": abs(h - hr) if hr is not None else None, "mm": (h - hn) * MM_PER_HUNGER})
    return out


def set_marks(rows, bout):
    """The set's markers off the ring rows of a bout's span: f and l the first and last flagged rows (index into
    rows), the engine rate's first falling sample after f (rate below the row before by more than K.energy.FALL_EPS),
    the first row at or after the driver's first poll reading the flag clear."""
    flags = [i for i, r in enumerate(rows) if L.flagged(r)]
    if not flags:
        return None
    f, l = flags[0], flags[-1]
    eps = float(K().energy.FALL_EPS)
    turn = next((i for i in range(f + 1, len(rows)) if L.num(rows[i].get("rate")) is not None
                 and L.num(rows[i - 1].get("rate")) is not None and rows[i]["rate"] < rows[i - 1]["rate"] - eps), None)
    clears = [s.get("clear_age") for s in bout.get("sets") or [] if s.get("clear_age") is not None]
    clear = max(clears) if clears else None
    at_clear = next((i for i, r in enumerate(rows) if clear is not None and r["age"] >= clear - 1e-9), None)
    return {"f": f, "l": l, "turn": turn, "at_clear": at_clear, "clear_age": clear, "runs": L._runs(flags)}


def epoc_check(rows, m):
    """The pool off the ring against its own step (module docstring, EPOC). Inflow at drain k (ring rows k -> k + 1):
    EPOC_F x exKcalDay's rise when the drain billed Fitness (row k + 1's body.met 6.0), else 0; the pool's predicted
    value at row k + 1: (pool_k + inflow) x exp(-dt / (60 EPOC_TAU_H)), dt = 60 x (satiety.t_k+1 - satiety.t_k)."""
    k = K()
    f_, tau = float(k.energy.EPOC_F), float(k.energy.EPOC_TAU_H)
    fit = float(k.energy.COMPENDIUM.Fitness)
    s0 = max(m["f"] - 1, 0)
    pool0 = L.num(rows[s0].get(L.EPOC)) or 0.0
    inflow, released, worst, graded = 0.0, 0.0, 0.0, 0
    set_ex = 0.0
    out_rows = []
    for i in range(s0, len(rows) - 1):
        p, r = rows[i], rows[i + 1]
        x, y = L.num(p.get(L.EXK)), L.num(r.get(L.EXK))
        exk = (y - x) if (x is not None and y is not None and y >= x) else 0.0
        on = abs((L.num(r.get(L.MET)) or 0.0) - fit) < 1e-9 and exk > 0
        if on:
            set_ex += exk
        inn = f_ * exk if on else 0.0
        a, b = L.num(p.get(L.EPOC)) or 0.0, L.num(r.get(L.EPOC))
        ta, tb = L.num(p.get("satiety.t")), L.num(r.get("satiety.t"))
        if b is None or ta is None or tb is None:
            continue
        dt = 60.0 * (tb - ta)
        pred = (a + inn) * math.exp(-dt / (60.0 * tau))
        inflow += inn
        released += (a + inn) - b
        if pred > 1e-6:
            e = abs(b / pred - 1)
            graded += 1
            worst = max(worst, e)
        if len(out_rows) < 400:
            out_rows.append({"s": r["s"], "age": r["age"], "epoc": b, "pred": pred, "inflow": inn, "dt_min": dt})
    pool_end = L.num(rows[-1].get(L.EPOC)) or 0.0
    tot = inflow - (pool_end - pool0)
    target = f_ * set_ex
    return {"EPOC_F": f_, "EPOC_TAU_H": tau, "pool_start": pool0, "pool_end": pool_end, "inflow": inflow,
            "released_sum": released, "released_total": tot, "set_ex_kcal": set_ex, "target": target,
            "released_over_target": (tot / target) if target else None,
            "ok": bool(target) and abs(tot / target - 1) <= EPOC_TOL, "step_graded": graded, "step_max_rel": worst,
            "rows": out_rows}


def s_steps(rows):
    """S on every drain of rows (k -> k + 1): toward the resistance weight on ACUTE_HALF_LIFE_H when row k + 1 bills 6.0
    or more (W.vigorous: body.met >= HeavyWork with the exercise flag: resistance), else toward 0 on
    ACUTE_DECAY_HALF_LIFE_H; the exact step on satiety.t."""
    k = K()
    up, down = float(k.satiety.ACUTE_HALF_LIFE_H), float(k.satiety.ACUTE_DECAY_HALF_LIFE_H)
    w = float(k.satiety.ACUTE_KIND.resistance)
    hi = float(k.energy.COMPENDIUM.HeavyWork)
    rise, dec = [], []
    for p, r in zip(rows, rows[1:]):
        a, b = L.num(p.get("satiety.S")), L.num(r.get("satiety.S"))
        ta, tb = L.num(p.get("satiety.t")), L.num(r.get("satiety.t"))
        if a is None or b is None or ta is None or tb is None:
            continue
        vig = (L.num(r.get(L.MET)) or 0.0) >= hi - 1e-9
        if vig:
            pred = w + (a - w) * 0.5 ** ((tb - ta) / up)
            rise.append({"s": r["s"], "age": r["age"], "S": b, "pred": pred, "rel": abs(b / pred - 1) if pred else None})
        else:
            pred = a * 0.5 ** ((tb - ta) / down)
            dec.append({"s": r["s"], "age": r["age"], "S": b, "pred": pred,
                        "rel": abs(b / pred - 1) if pred >= 1e-4 else None})
    gr = [x["rel"] for x in rise if x["rel"] is not None]
    gd = [x["rel"] for x in dec if x["rel"] is not None]
    return {"weight": w, "half_life_up_h": up, "half_life_down_h": down,
            "rise": {"rows": len(rise), "max_rel": max(gr) if gr else None, "S_max": max((x["S"] for x in rise),
                                                                                       default=None),
                     "ok": bool(gr) and max(gr) <= 1e-9, "first": rise[:5]},
            "decay": {"rows": len(dec), "graded": len(gd), "max_rel": max(gd) if gd else None,
                      "ok": bool(gd) and max(gd) <= 0.01, "first": dec[:5]}}


def row9(S):
    k = K()
    st = S.bout(ROW9_BOUT)
    if st is None:
        return {"measured": False, "why": "no %s stop in %s" % (ROW9_BOUT, S.pre)}
    a0, a1 = L.num(st.get("age0")), L.num(st.get("age1"))
    rows = window(S.ring, a0 - 2.0 / 60, a1)
    m = set_marks(rows, st)
    if m is None:
        return {"measured": False, "why": "no flagged ring row in the bout"}
    fit, idle = float(k.energy.COMPENDIUM.Fitness), float(k.energy.COMPENDIUM.Default)
    f, l = m["f"], m["l"]
    met = lambda i: L.num(rows[i].get(L.MET)) if 0 <= i < len(rows) else None  # noqa: E731
    on = [met(i + 1) for i in range(f, l + 1) if L.flagged(rows[i]) and i + 1 < len(rows)]
    miss = sum(1 for x in on if x is None or abs(x - fit) > 1e-9)
    first = {"first_flag_s": rows[f]["s"], "first_flag_age": rows[f]["age"], "billed_next": met(f + 1),
             "billed_before": met(f), "rate_at_first_flag": rows[f].get("rate"),
             "flagged_drains": len(on), "billed_fitness": len(on) - miss, "not_fitness": miss,
             "flag_runs": len(m["runs"])}
    first["ok"] = (first["billed_next"] is not None and abs(first["billed_next"] - fit) < 1e-9
                   and (first["billed_before"] is None or abs(first["billed_before"] - fit) > 1e-9)
                   and miss <= 2 * len(m["runs"]))
    fu = l + 1
    end = {"last_flag_s": rows[l]["s"], "last_flag_age": rows[l]["age"],
           "first_unflagged_s": rows[fu]["s"] if fu < len(rows) else None,
           "first_unflagged_age": rows[fu]["age"] if fu < len(rows) else None,
           "rate_turn_s": rows[m["turn"]]["s"] if m["turn"] is not None else None,
           "rows_unflag_minus_turn": (fu - m["turn"]) if m["turn"] is not None else None,
           "poll_clear_age": m["clear_age"],
           "rows_unflag_minus_poll": (fu - m["at_clear"]) if m["at_clear"] is not None else None}
    end["ok"] = end["rows_unflag_minus_turn"] is not None and abs(end["rows_unflag_minus_turn"]) <= 1
    end["ok_poll"] = end["rows_unflag_minus_poll"] is not None and abs(end["rows_unflag_minus_poll"]) <= 1
    after = [{"s": rows[j]["s"], "age": rows[j]["age"], "met": met(j), "moving": rows[j - 1].get("moving"),
              "rate": rows[j - 1].get("rate")} for j in range(l + 2, len(rows))]
    still = [x for x in after if x["moving"] is not True]
    over = [x for x in still if x["met"] is not None and x["met"] > idle + 1e-9]
    tk = 0.0
    for j in range(l + 2, len(rows)):
        x, y = L.num(rows[j - 1].get(L.EXK)), L.num(rows[j].get(L.EXK))
        if x is not None and y is not None and y >= x:
            tk += y - x
    idle_after = {"clear_minute_s": rows[l + 2]["s"] if l + 2 < len(rows) else None,
                  "clear_minute_met": met(l + 2), "still_rows": len(still), "tail_rows": len(over),
                  "tail": over[:20], "moving_rows": len(after) - len(still), "tail_kcal": tk,
                  "rest_h": (rows[-1]["age"] - rows[l]["age"]) if rows else None,
                  "x29_tail_kcal": list(X29_TAIL_KCAL)}
    idle_after["ok"] = (idle_after["clear_minute_met"] is not None and abs(idle_after["clear_minute_met"] - idle) < 1e-9
                        and len(over) <= 1)
    ep = epoc_check(rows, m)
    sv = s_steps(rows)
    fr = factor_rows(S, rows[f]["age"] - 1.0 / 60, a1)
    okf = [x["rel"] for x in fr if x["rel"] is not None]
    rp = [x["replay_abs"] for x in fr if x["replay_abs"] is not None]
    on_set = [x for x in fr if rows[f]["age"] < x["age"] <= rows[l + 1]["age"] + 1e-9 and x["rel"] is not None]
    r30 = L.row_at(fr, rows[l]["age"] + 0.5)
    factor = {"graded": len(okf), "max_rel": max(okf) if okf else None, "ok": bool(okf) and max(okf) <= FACTOR_TOL,
              "replay_hunger_max_abs": max(rp) if rp else None,
              "mean_ratio_over_set": (sum(x["factor"] for x in on_set) / len(on_set)) if on_set else None,
              "mm_30min_after_set": r30["mm"] if r30 else None, "S_30min_after_set": r30["S"] if r30 else None,
              "min_ratio": min((x["factor"] for x in fr), default=None), "rows": fr[:400]}
    pairs = []
    for p in S.doc.get("pairs") or []:
        if not str(p.get("tag", "")).startswith(ROW9_BOUT + "_"):
            continue
        c, s = p.get("client") or {}, p.get("server") or {}
        gap = L.num(p.get("wall_gap"))
        d = (abs(c["HUNGER"] - s["HUNGER"]) if (L.num(c.get("HUNGER")) is not None and L.num(s.get("HUNGER"))
                                                  is not None) else None)
        pairs.append({"tag": p.get("tag"), "wall_gap": gap, "same_second": gap is not None and abs(gap) <= 1.0,
                      "client_HUNGER": c.get("HUNGER"), "server_HUNGER": s.get("HUNGER"), "abs_diff": d,
                      "server_age": s.get("worldAge")})
    same = [x["abs_diff"] for x in pairs if x["same_second"] and x["abs_diff"] is not None]
    sets = [{k_: s_.get(k_) for k_ in ("label", "requested_min", "age_queued", "clear_age", "started", "ended")}
            for s_ in st.get("sets") or []]
    return {"measured": True, "session": S.pre, "age0": a0, "age1": a1, "sets": sets,
            "set_minutes_flagged": sum(L.num(rows[i + 1].get("dtM")) or 0.0 for i in range(f, l + 1)
                                       if L.flagged(rows[i]) and i + 1 < len(rows)),
            "billed_6_from_first": first, "exe_end": end, "idle_after": idle_after, "epoc": ep, "S": sv,
            "factor": factor, "pairs": {"rows": pairs, "same_second_max_abs": max(same) if same else None,
                                        "same_second_n": len(same)},
            "oracle_pins": ORACLE_PINS}


def walk_leg(S):
    """B5's walk: every drain read moving with the raw rate falling bills at most Walking5kmh (C17-5)."""
    k = K()
    st = S.bout(WALK_BOUT)
    if st is None or not st.get("walk"):
        return {"measured": False, "why": "no %s walk in %s" % (WALK_BOUT, S.pre)}
    w = st["walk"]
    a0, a1 = L.num(w.get("age0")), L.num(w.get("age1"))
    rows = window(S.ring, a0 - 1.0 / 60, a1 + 3.0 / 60)
    cap = float(k.energy.COMPENDIUM.Walking5kmh)
    eps = float(k.energy.FALL_EPS)
    mv, mvf = [], []
    for p, r in zip(rows, rows[1:]):
        if p.get("moving") is not True or L.flagged(p):
            continue
        x = {"s": r["s"], "age": r["age"], "met": L.num(r.get(L.MET)), "rate": p.get("rate")}
        mv.append(x)
        prev = S.ring_by.get(p["s"] - 1) or {}
        if L.num(p.get("rate")) is not None and L.num(prev.get("rate")) is not None and p["rate"] < prev["rate"] - eps:
            mvf.append(x)
    over = [x for x in mvf if x["met"] is not None and x["met"] > cap + 1e-9]
    return {"measured": bool(mvf), "session": S.pre, "age0": a0, "age1": a1, "walks": len(w.get("walks") or []),
            "moving_polls": w.get("moving_polls"), "polls": len(w.get("polls") or []),
            "moving_rows": len(mv), "moving_falling_rows": len(mvf), "cap": cap,
            "met_hist_moving_falling": L._hist([x["met"] for x in mvf]), "met_hist_moving": L._hist([x["met"] for x in mv]),
            "over_cap": over[:20], "ok": bool(mvf) and not over, "rows": mvf[:60]}


# --- row 10 ------------------------------------------------------------------------------------------------------------

def bouts(sessions):
    out = []
    for S in sessions:
        for st in S.doc.get("stops") or []:
            if st.get("kind") != "bout":
                continue
            a0, a1 = L.num(st.get("age0")), L.num(st.get("age1"))
            rr = L.leg_reading(S.ring, a0, a1) if (a0 is not None and a1 is not None) else {}
            bl = L.billing_reading(S.ring, a0, a1) if (a0 is not None and a1 is not None) else {}
            out.append({"label": st["label"], "session": S.pre, "day": L.day_of(st["sched_age"]), "age0": a0,
                        "age1": a1, "set_end_age": st.get("set_end_age"), "kcal_ring": rr.get("exKcal_rise"),
                        "kcal_read": st.get("bout_kcal"), "met_hist": rr.get("met_hist"),
                        "flagged_rows": bl.get("flagged"), "on_flag_billed_fitness": bl.get("on_flag_billed_fitness"),
                        "on_flag_rows": bl.get("on_flag_rows"), "tail_rows": bl.get("tail_rows"),
                        "tail_moving_rows": bl.get("tail_moving_rows"), "tail_kcal": bl.get("tail_kcal"),
                        "epoc_max": bl.get("epoc_max"), "S_max": rr.get("S_max"),
                        "sets": len(st.get("sets") or []),
                        "sets_started": sum(1 for s in st.get("sets") or [] if s.get("started")),
                        "flagged_minutes": sum(1 for r in L.leg_rows(S.ring, a0, a1) if L.flagged(r))
                        if a0 is not None else None})
    return out


def ex_by_day(ring):
    """The billed exercise kcal per chain day (from 00:00): exKcalDay's non-negative rises between consecutive ring
    rows (the mod day's close at 07:00 resets it: that row's rise is lost, named), with the ring's hours that day."""
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
    for x in out.values():
        x["complete"] = x["hours"] > 23.5
    return out


def lag_series(sessions, bl):
    k = K()
    ring = [r for S in sessions for r in S.ring]
    kc = {b["day"]: b["kcal_ring"] for b in bl if b["kcal_ring"] is not None}
    mean_k = (sum(kc.values()) / len(kc)) if kc else None
    exd = ex_by_day(ring)
    full = [x["kcal"] for d, x in exd.items() if x["complete"] and 1 <= d <= LAST_DAY - 1]
    mean_day = (sum(full) / len(full)) if full else None
    days = []
    for d in range(0, LAST_DAY + 1):
        row = {"day": d}
        for name, a in (("at_1500", L.at(d, 15.0)), ("end", L.at(d, 24.0))):
            r = L.row_at(ring, a)
            if r is None or r["age"] < a - 0.25:
                row[name] = None
                continue
            Lv = L.num(r.get("satiety.L"))
            lag = float(k.energy.lagged(Lv)) if Lv is not None else None
            kk = kc.get(d) if name == "end" else kc.get(d - 1)
            row[name] = {"age": a, "row_age": r["age"], "s": r["s"], "L": Lv, "lagged": lag,
                         "es": r.get("body.energyState"), "trail_c_ex": r.get("body.trail.c.ex"),
                         "share_day_bout": (lag / kk) if (lag is not None and kk) else None,
                         "share_mean_bout": (lag / mean_k) if (lag is not None and mean_k) else None,
                         "share_mean_day_ex": (lag / mean_day) if (lag is not None and mean_day) else None}
        days.append(row)
    return {"by_day": days, "bout_kcal_by_day": kc, "mean_bout_kcal": mean_k,
            "ex_kcal_by_day": {str(d): x for d, x in sorted(exd.items())},
            "mean_day_ex_kcal_days_1_%d" % (LAST_DAY - 1): mean_day, "complete_days_in_mean": len(full),
            "reading_at_last_day_1500": days[LAST_DAY]["at_1500"]}


def oracle_arm(days=LAST_DAY + 1, after=LAST_DAY):
    """x29_grade's oracle arm (test_replay_live_energy.py lag_run, Whybrow's high dose on the 70 kg man), read at each
    day's end and `after` days after its first bout (the bout at 02:00)."""
    sys.path.insert(0, os.path.join(REPO, "testing"))
    from tests.kernel import test_satiety_meal_studies as M    # noqa: E402
    be0 = RL.ServerReplay(start=None, user=L.USER, sleep_allowed=None)
    k = be0.K
    b = k.body.new(70.0, 1, be0.rt.table(), 5, 1, 1, 0)
    idle = k.energy.ree(b.lm) + (k.energy.COMPENDIUM.Default - k.energy.MET_REST) * 70.0 * 24
    kcal = 3.5 * 1000 / 4.184
    per = (k.energy.COMPENDIUM.Running15kmh - k.energy.COMPENDIUM.Default) * 70.0 / 60.0
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
    kk = [rows[d * 1440 + 120 + bout - 1]["body.exKcalDay"] - rows[d * 1440 + 119]["body.exKcalDay"] for d in range(days)]
    ends = [{"day": d, "share": float(be.K.energy.lagged(rows[d * 1440 + 1439]["satiety.L"])) / kk[d]}
            for d in range(days)]
    at = after * 1440 + 120 - 1
    return {"bout_min": bout, "bout_kcal": kk, "share_at_day_end": ends,
            "share_%d_days_after_first_bout" % after: float(be.K.energy.lagged(rows[at]["satiety.L"])) / kk[after - 1]}


def x29_before():
    """x29's committed series (the before, on the pre-C-17 build) at 15:00 on LAST_DAY: its share against its own days
    1-6 denominator, and lagged(L) against its days 1..LAST_DAY-1 mean recomputed; its exercise kcal by day."""
    p = os.path.join(ART, X29_LAG, "rows.json")
    if not os.path.isfile(p):
        return {"read": False}
    with open(p, encoding="utf-8") as fh:
        s = json.load(fh)["row10"]["series"]
    at = (s["by_day"][LAST_DAY] or {}).get("at_1500") or {}
    exd = s.get("ex_kcal_by_day") or {}
    full = [exd[str(d)]["kcal"] for d in range(1, LAST_DAY) if str(d) in exd and exd[str(d)].get("complete")]
    m = (sum(full) / len(full)) if full else None
    return {"read": True, "source": X29_LAG + "/rows.json row10.series", "at_1500": at,
            "share_own_denominator_days_1_6": at.get("share_mean_day_ex"),
            "mean_day_ex_days_1_%d" % (LAST_DAY - 1): m,
            "share_days_1_%d" % (LAST_DAY - 1): (at.get("lagged") / m) if (m and at.get("lagged") is not None) else None,
            "ex_kcal_by_day": {d: x.get("kcal") for d, x in exd.items()}, "share_7_days": ORACLE_PINS["x29_share_7_days"]}


def gaps(sessions):
    """Every break in the chain's ring: the attach between sessions (the last ring age of one, the first of the next),
    offline rows, and the replay's gap rows; each with whether it falls inside a bout's REST_H after its set's end."""
    tails = []
    for S in sessions:
        for st in S.doc.get("stops") or []:
            if st.get("kind") == "bout":
                e = L.num(st.get("set_end_age"))
                if e is not None:
                    tails.append((st["label"], e, e + REST_H))

    def inside(a, b):
        return [lab for lab, x, y in tails if a < y and b > x]
    out = []
    for p, q in zip(sessions, sessions[1:]):
        if p.ring and q.ring:
            a, b = p.ring[-1]["age"], q.ring[0]["age"]
            out.append({"kind": "attach", "from": p.pre, "to": q.pre, "age_from": a, "age_to": b, "hours": b - a,
                        "inside_tail": inside(a, b)})
    for S in sessions:
        off = [r for r in S.ring if r.get("on") is False]
        if off:
            out.append({"kind": "offline", "session": S.pre, "rows": len(off), "age_from": off[0]["age"],
                        "age_to": off[-1]["age"], "inside_tail": inside(off[0]["age"], off[-1]["age"])})
        for r in S.rows:
            if r.get("gap"):
                out.append({"kind": "gap_row", "session": S.pre, "s": r["s"], "age": r.get("age"), "dtM": r.get("dtM"),
                            "inside_tail": inside(L.num(r.get("age")) - 2.0 / 60, L.num(r.get("age")))
                            if L.num(r.get("age")) is not None else None})
    return {"tails": [{"bout": lab, "from": x, "to": y} for lab, x, y in tails], "breaks": out,
            "inside_any_tail": [b for b in out if b.get("inside_tail")]}


def drinking_sodium(sessions):
    k = K()
    out = {}
    for S in sessions:
        for e in L.autodrop_events(S.ring):
            d = out.setdefault(str(L.day_of(e["age"])), {})
            d["mod_l"] = d.get("mod_l", 0.0) + e["g"] / 1000.0
        prev = None
        for r in S.ring:
            d = out.setdefault(str(L.day_of(r["age"])), {})
            d["ring_hours"] = d.get("ring_hours", 0.0) + (r["age"] - prev["age"] if prev is not None and
                                                           L.day_of(prev["age"]) == L.day_of(r["age"]) else 0.0)
            for key in ("fluids.na", "fluids.water", "fluids.naPlasma"):
                if L.num(r.get(key)) is not None:
                    d.setdefault(key + "_first", r[key])
                    d[key + "_end"] = r[key]
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
            "BASAL_NA": float(k.fluids.BASAL_NA),
            "grade_max_chain": max((d["grade_max"] for d in out.values() if d.get("grade_max") is not None),
                                   default=None)}


def grade(out, sessions):
    per = {}
    for S in sessions:
        doc = S.summary()
        doc["agreement"] = agreement(S)
        doc["met_agreement"] = met_agreement(S)
        per[S.pre] = doc
        with open(os.path.join(out, S.pre + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True, default=str)
    s9 = next((S for S in sessions if S.bout(ROW9_BOUT) is not None), None)
    sw = next((S for S in sessions if S.bout(WALK_BOUT) is not None), None)
    r9 = row9(s9) if s9 is not None else {"measured": False, "why": "no session holds %s" % ROW9_BOUT}
    wl = walk_leg(sw) if sw is not None else {"measured": False, "why": "no session holds %s" % WALK_BOUT}
    bl = bouts(sessions)
    series = lag_series(sessions, bl)
    arm = oracle_arm()
    rows = {"row9": r9, "walk": wl,
            "row10": {"bouts": bl, "series": series, "oracle_arm": arm, "x29_before": x29_before(),
                      "oracle_pins": ORACLE_PINS, "agreement": {p: d["agreement"] for p, d in per.items()}},
            "gaps": gaps(sessions), "drinking_sodium": drinking_sodium(sessions)}
    with open(os.path.join(out, "rows.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, sort_keys=True, default=str)
    g = lambda d, *ks: L.g(d, *ks)  # noqa: E731
    return {"BILLED_6_FROM_FIRST": g(r9, "billed_6_from_first", "ok"), "EXE_END": g(r9, "exe_end", "ok"),
            "EXE_END_POLL": g(r9, "exe_end", "ok_poll"), "IDLE_AFTER": g(r9, "idle_after", "ok"),
            "EPOC": g(r9, "epoc", "ok"), "S_RISE": g(r9, "S", "rise", "ok"), "S_DECAY": g(r9, "S", "decay", "ok"),
            "FACTOR": g(r9, "factor", "ok"), "WALK_CAP": wl.get("ok"),
            "LAG_AGREEMENT": {p: all(v["ok"] for k_, v in d["agreement"].items() if k_ != L.EPOC or v["n"])
                              for p, d in per.items()},
            "MET_MISMATCHES": {p: d["met_agreement"]["mismatches"] for p, d in per.items()},
            "REPLAY_OK": {p: {"tool": d["tool_diff"]["ok"], "mine": d["diff"]["ok"]} for p, d in per.items()},
            "GAPS_INSIDE_TAIL": len(rows["gaps"]["inside_any_tail"]),
            "SODIUM_GRADE_MAX": rows["drinking_sodium"]["grade_max_chain"]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = a.out or os.path.join(ART, "x35-grade-%s" % datetime.date.today().strftime("%Y%m%d"))
    os.makedirs(out, exist_ok=True)
    sessions = []
    for n, pre in enumerate(CHAIN, 1):
        try:
            sessions.append(Sess(pre, "lag-%d.json" % n, counterfactual=(n == 1)))
        except SystemExit as e:
            print("skip %s: %s" % (pre, e))
    verdicts = grade(out, sessions)
    summ = {"tool_commit": _git("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
            "grade_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x35_grade.py"),
            "lib_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x35_exercise_lib.py"),
            "mod_commit": _git("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
            "sessions": [S.pre for S in sessions], "verdicts": verdicts}
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summ, fh, indent=1, sort_keys=True, default=str)
    print(json.dumps(verdicts, indent=1, default=str))


if __name__ == "__main__":
    main()
