"""x34_grade -- the committed grade of Plan 11f Task 9r (research row 13, monotony on the self-limiting floor design):
an ANALYSIS script, not a driver (it boots nothing). Written and committed before the first boot of the runs it
grades; its output is a DERIVED artifact folder (ruling T4-3: every number a row may cite is emitted by a committed
script).

    python testing/experiments/x34_grade.py [--out testing/artifacts/x34-grade-YYYYMMDD]

The inputs are each session's artifact folder testing/artifacts/x34N-*/ (x341, x342, x343, and x344 when it ran): the
driver's document (monotony-N.json), events.json, start.json, start-stats.json, player.json and the minute-ring pages.
The tool is tools/replay_live.py at HEAD with the live server's sleep option (sleep_allowed false). The kernel is the
mod's own on the lupa host (K.monotony, K.hybrid; constants read off it, never typed here).

Per ring row k (sampled inside EveryOneMinute before that minute's drain, so it shows what drain k - 1 left, and the
writer's input table W.input as drain k - 1 read it, x34_monotony_lib change 7):
  - THE TWIN: Mono450's level by K.monotony.level on the row's entry {n, last} at the row's satiety.t (the drain's
    age), composed as the writer composes it (min(effects.unhappyTarget + level, 59) for UNHAPPINESS, min(level,
    BORED_MAX) for BOREDOM), against the writer's own inp.unhappyTarget and inp.boredTarget on the row (rows where an
    eat landed after the drain are skipped: the record books the eat before the next drain reads it);
  - THE FLOOR MODEL: K.hybrid.floor run on the live inputs of drain k - 1 (the stat on row k - 1, the writer's target
    on row k, the remembered target moodLast on row k - 1, the rise over the drain's dtS from the satiety.t step; the
    BOREDOM rise 0 when the writer read PANIC above 5) against the stat on row k: UNHAPPINESS equal within float32
    noise; BOREDOM at or above it by vanilla's idle rise between the drain and the row (rows next to a BOREDOM set are
    skipped);
  - (b) TRACKING: rows not rising (the stat within FLOOR_EPS of the remembered target) read the stat within FLOOR_EPS
    of the twin (plus float32 noise); rising rows rise at the floor's rate (22 and 25 a game hour);
  - (a) NO JUMP at each eat: the bracketing pair (the lib's reading), the ring's eat-minute change and the next
    writer minute's rise, against the target's jump at the eat;
  - (c) BOREDOM under BORED_MAX 49 on every row, and the remembered and the writer's BOREDOM targets at or under it;
  - (d) THE RELEASE (the varied leg, after the last Mono450 eat's rise is met): the largest single-row fall of each stat
    against the decay's own steepest per-minute fall times the row's minutes plus FLOOR_EPS, and the stats' total fall
    against the twin's;
  - (e) live UNHAPPINESS and BOREDOM against the replay's on every row the tool grades;
  - THE RECONNECT: the stats at the quit, the first row after the join (before its drain) and after the first drain,
    against the twin;
  - THE DAY TABLE: per chain day the eats, the twin at the day-end read, the server's and the client's UNHAPPINESS and
    BOREDOM there, PANIC's maximum, against the oracle's floor (test_kernel_monotony.floor_run's form, minute by minute
    on the lupa host) on the run's nominal calendar and on the live eat ages, and the oracle's own 14-day table
    (mono14: MEALS_3 from day 0);
  - the guard, the panic reading, the drinking and the sodium per chain day, and each session's tool diff.
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
import x34_monotony_lib as L  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
CHAIN = (("x341", "monotony-1.json"), ("x342", "monotony-2.json"), ("x343", "monotony-3.json"),
         ("x344", "monotony-4.json"))
F32 = 1e-4                 # float32 noise on a stat of 0-100 (a stat is a Java float; the model runs in doubles)
TWIN_TOL = 1e-6            # the twin against the writer's own target (both doubles)
DRIFT_MAX = 0.1            # vanilla's idle BOREDOM rise between a drain and the next row (x33: about 0.03 a minute)
REPLAY_TOL_EXTRA = 1e-3    # live against replay: FLOOR_EPS plus this (a held fall may land one row apart)
UNHAPPY_HI = 59.0          # NR_Server_Writer W.UNHAPPY_HI (the effects surface's cap, NR_Data_Effects SURF hi)
MEALS_3_MIN = (8 * 60, 13 * 60, 19 * 60)


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


def kernel():
    return L._kh_static().K


def num(v):
    return L.num(v)


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
        if not self.ring:
            self.rows, self.diff, self.be = [], {"ok": None}, None
            return
        self.rows, self.be = RL.replay_live(self.ring, self.events, self.start, paths=self.rpaths, user=L.USER,
                                            player=self.player, start_stats=self.stats, sleep_allowed=L.SLEEP_ALLOWED)
        self.diff = RL.diff(self.rows, self.ring)

    def marks(self):
        """{s: {between, suspect, offline, gap}} off the replay rows (the tool's link_marks)."""
        return {r["s"]: {k: bool(r.get(k)) for k in ("between", "suspect", "offline", "gap")} for r in self.rows}

    def stops(self, kind):
        return [st for st in (self.doc.get("stops") or []) if st.get("kind") == kind]

    def summary(self):
        kinds = {}
        for e in self.events:
            kinds[e.get("kind")] = kinds.get(e.get("kind"), 0) + 1
        return {"run_id": self.doc.get("run_id"), "rows": len(self.rows), "events_by_kind": kinds,
                "ring_activity_events": len(getattr(self.be, "ring_activity", None) or []),
                "tool_diff": {k: self.diff.get(k) for k in ("fields", "classes", "ok")} | {
                    "findings_n": len(self.diff.get("findings", [])), "findings": self.diff.get("findings", [])[:20]},
                "ring_first_age": self.ring[0]["age"] if self.ring else None,
                "ring_last_age": self.ring[-1]["age"] if self.ring else None,
                "driver_verdicts": {k: v.get("verdict") for k, v in (self.doc.get("verdicts") or {}).items()},
                "host": self.doc.get("host"), "wall_seconds": self.doc.get("wall_seconds")}


# --- the per-row twin and floor model ------------------------------------------------------------------------------

def twin(K, r, age=None):
    """Mono450's level at the row's drain age and the writer's composition of it: (level, u target, b target)."""
    a = num(r.get(L.SAT_T)) if age is None else age
    if a is None:
        a = num(r.get("age"))
    lv = L.kernel_target(K, num(r.get(L.MONO_PATHS[0])), num(r.get(L.MONO_PATHS[1])), a)
    eu = num(r.get(L.UTARGET))
    if eu is None or not math.isfinite(eu):
        eu = 0.0
    return lv, min(eu + lv, UNHAPPY_HI), min(lv, float(K.monotony.BORED_MAX))


def floor_model(K, v0, ut, last, rise):
    """K.hybrid.floor on the lupa host: the value the floor writes (v0 when it writes nothing) and the target kept."""
    v, keep = K.hybrid.floor(float(v0), float(ut), float(last), float(rise))
    return (float(v) if v is not None else float(v0)), float(keep)


def landed_between(p, r):
    a, b = num(p.get(L.LANDED)), num(r.get(L.LANDED))
    return a is not None and b is not None and b > a


def near_set(r, set_rows, stat):
    return any(abs(r["s"] - s) <= 1 for (s, st) in set_rows if st == stat)


def row_table(S, K):
    """Per graded row pair (p = row k - 1, r = row k) the twin, the model and the tracking reading. A pair is graded
    when both rows are online, neither is suspect or offline in the tool's marks, s advances by 1 and both carry the
    stats, the writer's inputs and moodLast."""
    marks = S.marks()
    sets = [(e["s"], e["stat"]) for e in S.events if e.get("kind") == "stat"]
    rise_u = float(K.hybrid.defaults().moodRiseUnhappy)
    rise_b = float(K.hybrid.defaults().moodRiseBored)
    eps = float(K.hybrid.FLOOR_EPS)
    out = []
    for p, r in zip(S.ring, S.ring[1:]):
        if r["s"] != p["s"] + 1 or p.get("on") is False or r.get("on") is False:
            continue
        m = marks.get(r["s"], {})
        if m.get("suspect") or m.get("offline"):
            continue
        need = (num(p.get("UNHAPPINESS")), num(r.get("UNHAPPINESS")), num(p.get("BOREDOM")), num(r.get("BOREDOM")),
                num(r.get(L.IN_UT)), num(r.get(L.IN_BT)), num(p.get(L.MOOD_U)), num(p.get(L.MOOD_B)),
                num(r.get(L.MOOD_U)), num(r.get(L.MOOD_B)), num(p.get(L.SAT_T)), num(r.get(L.SAT_T)))
        if any(x is None for x in need):
            continue
        u0, u1, b0, b1, iut, ibt, lu0, lb0, lu1, lb1, t0, t1 = need
        dts = max(0.0, (t1 - t0) * 3600.0)
        dts = min(dts, float(K.hybrid.defaults().maxStepS))
        panic = num(r.get(L.IN_PANIC))
        mu, ku = floor_model(K, u0, iut, lu0, rise_u * dts)
        rb = 0.0 if (panic is not None and panic > 5) else rise_b * dts
        mb, kb = floor_model(K, b0, ibt, lb0, rb)
        lv, tu, tb = twin(K, r)
        eat = landed_between(p, r)
        row = {"s": r["s"], "age": r["age"], "drain_age": t1, "dtM_drain": dts / 60.0, "U": u1, "B": b1,
               "U_prev": u0, "B_prev": b0, "in_ut": iut, "in_bt": ibt, "moodLast_u": lu1, "moodLast_b": lb1,
               "level": lv, "twin_u": tu, "twin_b": tb, "eat_after_drain": eat, "panic": panic,
               "model_u": mu, "model_b": mb, "keep_u": ku, "keep_b": kb,
               "u_minus_model": u1 - mu, "b_minus_model": b1 - mb, "keep_u_minus_moodLast": ku - lu1,
               "keep_b_minus_moodLast": kb - lb1,
               "twin_u_minus_in": (iut - tu) if not eat else None, "twin_b_minus_in": (ibt - tb) if not eat else None,
               "near_b_set": near_set(r, sets, "BOREDOM") or near_set(p, sets, "BOREDOM"),
               "near_u_set": near_set(r, sets, "UNHAPPINESS") or near_set(p, sets, "UNHAPPINESS"),
               "between": m.get("between", False), "gap": m.get("gap", False)}
        row["u_rising"] = u1 < lu1 - eps - F32
        row["b_rising"] = b1 < lb1 - eps - F32
        out.append(row)
    return out


def summarize_rows(rows, K):
    """The row grades: TWIN, MODEL, TRACK, RISE and BORED_MAX, each with its counts and worst rows."""
    eps = float(K.hybrid.FLOOR_EPS)
    bmax = float(K.monotony.BORED_MAX)
    tw = [x for x in rows if x["twin_u_minus_in"] is not None]
    tw_bad = [x for x in tw if abs(x["twin_u_minus_in"]) > TWIN_TOL or abs(x["twin_b_minus_in"]) > TWIN_TOL]
    mu = [x for x in rows if not x["near_u_set"]]
    mu_bad = [x for x in mu if abs(x["u_minus_model"]) > F32]
    mb = [x for x in rows if not x["near_b_set"] and not (x["panic"] is not None and x["panic"] > 5)]
    mb_bad = [x for x in mb if not (-F32 <= x["b_minus_model"] <= DRIFT_MAX)]
    keep_bad = [x for x in rows if abs(x["keep_u_minus_moodLast"]) > TWIN_TOL]
    tr = [x for x in rows if not x["u_rising"] and not x["near_u_set"] and not x["eat_after_drain"]]
    tr_bad = [x for x in tr if abs(x["U"] - x["twin_u"]) > eps + F32]
    trb = [x for x in rows if not x["b_rising"] and not x["near_b_set"] and not x["eat_after_drain"]
           and not (x["panic"] is not None and x["panic"] > 5)]
    trb_bad = [x for x in trb if x["B"] < x["twin_b"] - eps - F32]
    rise_u = [x for x in rows if x["u_rising"] and not x["near_u_set"] and x["dtM_drain"] > 0]
    rise_b = [x for x in rows if x["b_rising"] and not x["near_b_set"] and x["dtM_drain"] > 0
              and not (x["panic"] is not None and x["panic"] > 5)]

    def rate(xs, a, b):
        rs = [(x[a] - x[b]) / x["dtM_drain"] * 60.0 for x in xs if x[a] > x[b]]
        if not rs:
            return {"n": 0}
        rs.sort()
        return {"n": len(rs), "min": rs[0], "median": rs[len(rs) // 2], "max": rs[-1]}

    def worst(xs, key, k=5):
        return [{"s": x["s"], "age": x["age"], key: x[key]} for x in sorted(xs, key=lambda x: -abs(x[key]))[:k]]
    return {
        "rows": len(rows),
        "TWIN": {"graded": len(tw), "over": len(tw_bad), "tol": TWIN_TOL,
                 "max_abs_u": max((abs(x["twin_u_minus_in"]) for x in tw), default=None),
                 "max_abs_b": max((abs(x["twin_b_minus_in"]) for x in tw), default=None),
                 "worst": worst(tw_bad or tw, "twin_u_minus_in")},
        "MODEL_U": {"graded": len(mu), "over": len(mu_bad), "tol": F32,
                    "max_abs": max((abs(x["u_minus_model"]) for x in mu), default=None),
                    "worst": worst(mu_bad or mu, "u_minus_model")},
        "MODEL_B": {"graded": len(mb), "outside": len(mb_bad), "band": [-F32, DRIFT_MAX],
                    "min": min((x["b_minus_model"] for x in mb), default=None),
                    "max": max((x["b_minus_model"] for x in mb), default=None),
                    "worst": worst(mb_bad or mb, "b_minus_model")},
        "KEEP_U": {"graded": len(rows), "over": len(keep_bad)},
        "TRACK_U": {"graded": len(tr), "over": len(tr_bad), "tol": eps + F32,
                    "max_abs": max((abs(x["U"] - x["twin_u"]) for x in tr), default=None),
                    "worst": [{"s": x["s"], "age": x["age"], "U": x["U"], "twin_u": x["twin_u"]} for x in tr_bad[:5]]},
        "TRACK_B": {"graded": len(trb), "under": len(trb_bad), "tol": eps + F32,
                    "max_over_twin": max((x["B"] - x["twin_b"] for x in trb), default=None),
                    "min_over_twin": min((x["B"] - x["twin_b"] for x in trb), default=None)},
        "RISE_U_PER_H": rate(rise_u, "U", "U_prev"), "RISE_B_PER_H": rate(rise_b, "B", "B_prev"),
        "RISE_U_ROWS": len(rise_u), "RISE_B_ROWS": len(rise_b),
        "BORED_MAX": {"B_max": max((x["B"] for x in rows), default=None),
                      "moodLast_b_max": max((x["moodLast_b"] for x in rows), default=None),
                      "in_bt_max": max((x["in_bt"] for x in rows), default=None), "bound": bmax,
                      "ok": all(x["B"] < bmax and x["moodLast_b"] <= bmax and x["in_bt"] <= bmax for x in rows)},
        "U_max": max((x["U"] for x in rows), default=None), "twin_u_max": max((x["twin_u"] for x in rows), default=None)}


# --- (a) the eats ------------------------------------------------------------------------------------------------------

def eat_ring(S, K, st, rows_by_s):
    """One eat's ring reading: the row the landing first shows (its LANDED rose), the stats' change into it (the eat's
    minute) and over the next rows (the writer minutes), the writer's target before and after, and the rows until the
    stat meets the new target."""
    out = {"label": st.get("label"), "food": st.get("food")}
    ring = S.ring
    idx = next((i for i in range(1, len(ring)) if landed_between(ring[i - 1], ring[i])
                and num(ring[i]["age"]) >= (num(st.get("landed_age_polled")) or 0) - 0.1), None)
    if idx is None or idx + 2 >= len(ring):
        out["ring"] = None
        return out
    p, r, n1 = ring[idx - 1], ring[idx], ring[idx + 1]
    out["landing_s"] = r["s"]
    out["landing_age"] = r["age"]
    out["eat_minute_change_U"] = (num(r.get("UNHAPPINESS")) or 0) - (num(p.get("UNHAPPINESS")) or 0)
    out["eat_minute_change_B"] = (num(r.get("BOREDOM")) or 0) - (num(p.get("BOREDOM")) or 0)
    out["in_ut_before"] = num(r.get(L.IN_UT))
    out["in_ut_after"] = num(n1.get(L.IN_UT))
    out["target_jump_writer"] = ((out["in_ut_after"] or 0) - (out["in_ut_before"] or 0))
    out["next_minute_change_U"] = (num(n1.get("UNHAPPINESS")) or 0) - (num(r.get("UNHAPPINESS")) or 0)
    out["next_minute_change_B"] = (num(n1.get("BOREDOM")) or 0) - (num(r.get("BOREDOM")) or 0)
    out["next_dtM"] = ((num(n1.get(L.SAT_T)) or 0) - (num(r.get(L.SAT_T)) or 0)) * 60.0
    met = None
    for j in range(idx + 1, min(len(ring), idx + 400)):
        x = ring[j]
        if num(x.get("UNHAPPINESS")) is not None and num(x.get(L.IN_UT)) is not None and \
                x["UNHAPPINESS"] >= x[L.IN_UT] - float(K.hybrid.FLOOR_EPS) - F32:
            met = j
            break
    out["met_rows"] = (met - idx) if met is not None else None
    out["met_game_min"] = ((ring[met]["age"] - r["age"]) * 60.0) if met is not None else None
    rise = float(K.hybrid.defaults().moodRiseUnhappy) * out["next_dtM"] * 60.0
    out["next_rise_bound"] = rise
    big = out["target_jump_writer"] >= 0.5
    out["first_rise_at_next_minute"] = (big and 0 < out["next_minute_change_U"] <= rise + F32) if big else None
    out["no_jump_in_eat_minute"] = abs(out["eat_minute_change_U"]) <= rise + F32 if big else None
    return out


def eats_table(sessions, K):
    out = []
    for S in sessions:
        lib = {x["label"]: x for x in (L.g(S.doc, "readings", "mono_eats") or [])}
        rows_by_s = {r["s"]: r for r in S.ring}
        for st in S.stops("mono"):
            x = dict(lib.get(st.get("label")) or L.eat_reading(st, K))
            x["session"] = S.pre
            x["ring"] = eat_ring(S, K, st, rows_by_s)
            out.append(x)
    return out


# --- (d) the release -----------------------------------------------------------------------------------------------

def release(sessions, rows_all, K, eats):
    """The varied leg after the last Mono450 eat's rise is met: per stat the largest single-row fall against the
    steepest per-minute fall of the decay (the oracle's steep) times the row's drain minutes plus FLOOR_EPS, and the
    stat's total fall against the twin's."""
    eps = float(K.hybrid.FLOOR_EPS)
    cap = float(K.monotony.CAP)
    slope = float(K.monotony.SLOPE)
    steep = slope * (cap / slope + 1) * math.log(2) / float(K.monotony.HALF_LIFE_H) / 60.0
    monos = [e for e in eats if e.get("food") == L.MONO and e.get("landed")]
    if not monos:
        return {"measured": False}
    last = max(num(e.get("landed_age_polled")) or 0 for e in monos)
    start = last + 2.0
    rs = [x for x in rows_all if x["age"] >= start]
    if not rs:
        return {"measured": False, "from_age": start}
    out = {"measured": True, "from_age": start, "to_age": rs[-1]["age"], "rows": len(rs), "steep_per_min": steep}
    for st, key, near in (("U", "twin_u", "near_u_set"), ("B", "twin_b", "near_b_set")):
        xs = [x for x in rs if not x[near] and not x["eat_after_drain"]]
        drops = [(x[st + "_prev"] - x[st], x) for x in xs]
        bad = [(d, x) for d, x in drops if d > steep * x["dtM_drain"] + eps + F32]
        big = max(drops, key=lambda t: t[0]) if drops else None
        out[st] = {"graded": len(xs), "over": len(bad), "max_drop": big[0] if big else None,
                   "max_drop_s": big[1]["s"] if big else None, "max_drop_dtM": big[1]["dtM_drain"] if big else None,
                   "bound_at_max": (steep * big[1]["dtM_drain"] + eps) if big else None,
                   "first": xs[0][st] if xs else None, "last": xs[-1][st] if xs else None,
                   "twin_first": xs[0][key] if xs else None, "twin_last": xs[-1][key] if xs else None,
                   "writes": sum(1 for d, x in drops if d > 0)}
        if xs:
            out[st]["fall"] = xs[0][st] - xs[-1][st]
            out[st]["twin_fall"] = xs[0][key] - xs[-1][key]
            out[st]["fall_minus_twin"] = out[st]["fall"] - out[st]["twin_fall"]
    out["U"]["falling_minutes"] = sum(1 for x in rs if x["U_prev"] > x["U"])
    return out


# --- the reconnect -------------------------------------------------------------------------------------------------

def reconnect(sessions, K):
    """The reconnect stop (lib change 6): the quit, the away span, and on the ring the last online row before the
    departure, the first online row after the join (the stats as loaded, before that minute's drain) and the row after
    its drain, against the twin."""
    eps = float(K.hybrid.FLOOR_EPS)
    for S in sessions:
        st = next(iter(S.stops("reconnect")), None)
        if st is None:
            continue
        out = {"session": S.pre, "label": st.get("label"), "done": st.get("done"), "away_h": st.get("away_h"),
               "away_from_age": st.get("away_from_age"), "departed": st.get("departed"),
               "server_pre": {k: L.g(st, "server_pre", k) for k in ("UNHAPPINESS", "BOREDOM", "PANIC", "worldAge")},
               "record_pre": L.g(st, "record_pre", "values"), "record_away": L.g(st, "record_away", "values"),
               "record_before_join": L.g(st, "record_before_join", "values"),
               "client_after": {k: L.g(st, "client_after", k) for k in ("UNHAPPINESS", "BOREDOM", "worldAge")}}
        ser = st.get("after_series") or []
        out["after_series"] = [{"age": L.g(x, "server", "worldAge"), "U": L.g(x, "server", "UNHAPPINESS"),
                                "B": L.g(x, "server", "BOREDOM"), "writes": x.get("writes"),
                                "moodLast_u": L.g(x, "record", "values", L.MOOD_U)} for x in ser]
        ring = S.ring
        q = num(st.get("away_from_age"))
        off = [i for i, r in enumerate(ring) if r.get("on") is False]
        out["offline_rows"] = len(off)
        if off:
            i0, i1 = off[0], off[-1]
            before = ring[i0 - 1] if i0 > 0 else None
            first_on = ring[i1 + 1] if i1 + 1 < len(ring) else None
            after = ring[i1 + 2] if i1 + 2 < len(ring) else None
            out["ring_last_online"] = ({k: before.get(k) for k in ("s", "age", "UNHAPPINESS", "BOREDOM", L.MOOD_U,
                                                                    L.MOOD_B)} if before else None)
            out["ring_first_online"] = ({k: first_on.get(k) for k in ("s", "age", "UNHAPPINESS", "BOREDOM", L.MOOD_U,
                                                                       L.MOOD_B, L.IN_UT, "norec")}
                                        if first_on else None)
            if after is not None:
                lv, tu, tb = twin(K, after)
                out["ring_after_first_drain"] = {"s": after["s"], "age": after["age"], "U": after.get("UNHAPPINESS"),
                                                 "B": after.get("BOREDOM"), "in_ut": after.get(L.IN_UT),
                                                 "moodLast_u": after.get(L.MOOD_U), "twin_u": tu, "twin_b": tb,
                                                 "level": lv}
                u = num(after.get("UNHAPPINESS"))
                out["U_minus_twin"] = (u - tu) if u is not None else None
                out["landed_on_target"] = (u is not None and abs(u - tu) <= eps + F32)
                if first_on is not None and num(first_on.get("UNHAPPINESS")) is not None and before is not None:
                    out["U_held_while_away"] = first_on["UNHAPPINESS"] - (num(before.get("UNHAPPINESS")) or 0)
                    out["fall_while_away_twin"] = (num(before.get(L.MOOD_U)) or 0) - tu
        out["quit_age"] = q
        return out
    return {"measured": False}


# --- the oracle ----------------------------------------------------------------------------------------------------

def oracle_run(K, eats, start_age, end_age, u0=0.0, b0=0.0):
    """test_kernel_monotony.floor_run's form on the lupa host: one write a game minute from start_age to end_age, eats
    [(age, fullType)] booked at their minute (weight 1, non-staple), the kernel's target and K.hybrid.write. Returns
    [(age, u, b, tu)]."""
    m = K.monotony.new()
    inp, outp, c = K.hybrid.input(), K.hybrid.output(), K.hybrid.defaults()
    u, b, lu, lb = u0, b0, 0.0, 0.0
    ev = sorted(eats)
    i = 0
    rows = []
    n = int(math.floor((end_age - start_age) * 60.0)) + 1
    for k in range(n):
        age = start_age + k / 60.0
        while i < len(ev) and ev[i][0] <= age + 1e-9:
            K.monotony.record(m, ev[i][1], ev[i][0], 1, False)
            i += 1
        tu, tb = K.monotony.target(m, age)
        inp.dtS, inp.unhappy, inp.unhappyTarget, inp.lastUnhappyTarget = 60, u, tu, lu
        inp.bored, inp.boredTarget, inp.lastBoredTarget = b, tb, lb
        K.hybrid.write(inp, outp, c)
        if outp.unhappy is not None:
            u = outp.unhappy
        if outp.bored is not None:
            b = outp.bored
        lu, lb = outp.unhappyTarget, outp.boredTarget
        rows.append((age, float(u), float(b), float(tu)))
    return rows


def at_age(rows, age):
    best = None
    for r in rows:
        if r[0] <= age + 1e-9:
            best = r
        else:
            break
    return best


def day_table(sessions, K, eats, gate_age, end_age):
    """Per chain day: the eats, the day-end read (server and client), the twin there, the ring's maxima, and the
    oracle on the nominal calendar and on the live eat ages."""
    nominal = [(a, x) for a, kind, lab, x in L.SCHEDULE if kind == "mono" and gate_age <= a <= end_age]
    live = [(num(e.get("landed_age_polled")), e.get("food")) for e in eats
            if e.get("landed") and num(e.get("landed_age_polled")) is not None]
    o_nom = oracle_run(K, nominal, gate_age, end_age)
    o_live = oracle_run(K, live, gate_age, end_age)
    out = {}
    for S in sessions:
        for st in S.stops("dayend"):
            d = L.day_of(num(st.get("sched_age")) or 0)
            s0, c = st.get("server0") or {}, st.get("client") or {}
            rv = L.g(st, "record", "values") or {}
            a = num(s0.get("worldAge"))
            lv = L.kernel_target(K, rv.get(L.MONO_PATHS[0]), rv.get(L.MONO_PATHS[1]), a)
            on, ol = at_age(o_nom, a) if a else None, at_age(o_live, a) if a else None
            row = {"day": d, "label": st.get("label"), "session": S.pre, "age": a, "sched_age": st.get("sched_age"),
                   "server_U": s0.get("UNHAPPINESS"), "server_B": s0.get("BOREDOM"), "server_PANIC": s0.get("PANIC"),
                   "client_U": c.get("UNHAPPINESS"), "client_B": c.get("BOREDOM"), "client_PANIC": c.get("PANIC"),
                   "client_age": c.get("worldAge"), "moodLast_u": rv.get(L.MOOD_U), "moodLast_b": rv.get(L.MOOD_B),
                   "effects_unhappyTarget": rv.get(L.UTARGET), "panicTarget": rv.get(L.PTARGET),
                   "dehydPct": rv.get(L.DEHYD), "n": rv.get(L.MONO_PATHS[0]), "level": lv,
                   "oracle_nominal_U": on[1] if on else None, "oracle_nominal_target": on[3] if on else None,
                   "oracle_live_U": ol[1] if ol else None, "oracle_live_target": ol[3] if ol else None}
            for k in ("U", "B"):
                sv, cv = num(row["server_" + k]), num(row["client_" + k])
                row["client_minus_server_" + k] = (cv - sv) if (sv is not None and cv is not None) else None
            su = num(row["server_U"])
            row["U_minus_oracle_live"] = (su - row["oracle_live_U"]) if (su is not None and ol) else None
            row["U_minus_oracle_nominal"] = (su - row["oracle_nominal_U"]) if (su is not None and on) else None
            out[str(d)] = row
    for e in eats:
        d = str(e.get("day"))
        if d in out:
            out[d]["eats"] = out[d].get("eats", 0) + (1 if e.get("landed") else 0)
            out[d].setdefault("foods", []).append(e.get("food"))
    for S in sessions:
        for r in S.ring:
            if num(r.get("age")) is None:
                continue
            d = str(L.day_of(r["age"]))
            if d not in out:
                continue
            o = out[d]
            for k, f in (("ring_U_max", "UNHAPPINESS"), ("ring_B_max", "BOREDOM"), ("ring_panic_max", L.IN_PANIC),
                         ("ring_twin_level_max", None)):
                v = num(r.get(f)) if f else L.kernel_target(K, num(r.get(L.MONO_PATHS[0])), num(r.get(L.MONO_PATHS[1])),
                                                             num(r.get(L.SAT_T)) or r["age"])
                if v is not None:
                    o[k] = max(o.get(k, v), v)
    mono14 = oracle_run(K, [(d * 24.0 + mm / 60.0, L.MONO) for d in range(14) for mm in MEALS_3_MIN], 0.0, 14 * 24.0)
    table14 = []
    for d in range(14):
        rs = [r for r in mono14 if d * 24.0 <= r[0] < (d + 1) * 24.0]
        table14.append({"day": d, "U_max": max(r[1] for r in rs), "U_end": rs[-1][1], "target_end": rs[-1][3]})
    first_cap = next((r[0] for r in o_live if r[1] >= float(K.monotony.CAP) - 1e-9), None)
    return {"days": dict(sorted(out.items(), key=lambda kv: int(kv[0]))), "oracle_mono14": table14,
            "oracle_live_first_cap_age": first_cap,
            "oracle_nominal_U_max": max((r[1] for r in o_nom), default=None),
            "oracle_live_U_max": max((r[1] for r in o_live), default=None),
            "nominal_eats": len(nominal), "live_eats": len(live)}


# --- (e) live against replay -------------------------------------------------------------------------------------

def vs_replay(S, K):
    eps = float(K.hybrid.FLOOR_EPS)
    by = {r["s"]: r for r in S.ring}
    out = {}
    for stat in ("UNHAPPINESS", "BOREDOM"):
        xs = []
        for r in S.rows:
            if r.get("between") or r.get("suspect") or r.get("offline"):
                continue
            lv = by.get(r["s"])
            if lv is None or num(lv.get(stat)) is None or num(r.get(stat)) is None:
                continue
            xs.append((lv[stat] - r[stat], r["s"]))
        if not xs:
            out[stat] = {"n": 0}
            continue
        w = max(xs, key=lambda t: abs(t[0]))
        out[stat] = {"n": len(xs), "max_abs": abs(w[0]), "worst_s": w[1], "worst_live_minus_replay": w[0],
                     "rows_over": sum(1 for d, s in xs if abs(d) > eps + REPLAY_TOL_EXTRA),
                     "tol": eps + REPLAY_TOL_EXTRA, "min": min(d for d, s in xs), "max": max(d for d, s in xs)}
    return out


def resets(sessions, rows_all, K):
    """Each BOREDOM reset (lib change 4): the value it replaced, the twin there, and the floor's rise back to it."""
    eps = float(K.hybrid.FLOOR_EPS)
    out = []
    for S in sessions:
        sets = [x for x in (S.doc.get("sets") or []) if x.get("stat") == "BOREDOM"]
        ev = {e.get("label"): e for e in S.events if e.get("kind") == "stat" and e.get("stat") == "BOREDOM"}
        for x in sets:
            e = ev.get("setany-" + str(x.get("label")))
            row = {"session": S.pre, "label": x.get("label"), "before": x.get("before"), "after": x.get("after"),
                   "ok": x.get("ok"), "age": x.get("after_age"), "event_s": e.get("s") if e else None}
            if e:
                rs = [r for r in rows_all if r["s"] > e["s"] and r["age"] >= (num(x.get("after_age")) or 0)
                      and r["age"] <= (num(x.get("after_age")) or 0) + 3.0]
                met = next((r for r in rs if r["B"] >= r["twin_b"] - eps - F32), None)
                row["twin_b_at_set"] = rs[0]["twin_b"] if rs else None
                row["met_game_min"] = ((met["age"] - num(x.get("after_age"))) * 60.0) if met else None
                if met and rs:
                    row["mean_rise_per_h"] = (met["B"] - rs[0]["B_prev"]) / max(1e-9, met["age"] - rs[0]["age"] +
                                                                                rs[0]["dtM_drain"] / 60.0)
            out.append(row)
    return out


def guard(sessions):
    return {S.pre: L.guard_reading(S.ring) for S in sessions}


def drinking_sodium(sessions):
    K = kernel()
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
            for k in ("fluids.na", "fluids.water", "fluids.naPlasma", "body.energyState", L.DEHYD):
                if num(r.get(k)) is not None:
                    d.setdefault(k + "_first", r[k])
                    d[k + "_end"] = r[k]
            p = num(r.get("fluids.naPlasma"))
            if p is not None:
                d["naPlasma_min"] = min(d.get("naPlasma_min", p), p)
                d["naPlasma_max"] = max(d.get("naPlasma_max", p), p)
            dh = num(r.get(L.DEHYD))
            if dh is not None:
                d["dehydPct_max"] = max(d.get("dehydPct_max", dh), dh)
            prev = r
    for d in out.values():
        d["grade_max"] = L.hypo_grade(d.get("naPlasma_min"))
        d["complete"] = d.get("ring_hours", 0) > 23.5
    return {"by_day": dict(sorted(out.items(), key=lambda kv: int(kv[0]))), "BASAL_NA": float(K.fluids.BASAL_NA),
            "grade_max_chain": max((d["grade_max"] for d in out.values() if d.get("grade_max") is not None),
                                   default=None)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = a.out or os.path.join(ART, "x34-grade-%s" % datetime.date.today().strftime("%Y%m%d"))
    os.makedirs(out, exist_ok=True)
    sessions = []
    for pre, doc in CHAIN:
        try:
            sessions.append(Sess(pre, doc))
        except SystemExit as e:
            print("skip %s: %s" % (pre, e))
    K = kernel()
    rows_all = []
    per = {}
    for S in sessions:
        rt = row_table(S, K)
        rows_all += rt
        sm = S.summary()
        sm["rows_grade"] = summarize_rows(rt, K)
        sm["vs_replay"] = vs_replay(S, K)
        sm["panic"] = L.panic_reading(S.ring)
        per[S.pre] = sm
        with open(os.path.join(out, S.pre + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(sm, fh, indent=1, sort_keys=True, default=str)
    eats = eats_table(sessions, K)
    gate = L.g(sessions[0].doc, "phases", "X", "gate") if sessions else None
    gate_age = num(L.g(gate, "set_unhappy", "after_age")) or (sessions[0].ring[0]["age"] if sessions else 0.0)
    end_age = max((S.ring[-1]["age"] for S in sessions if S.ring), default=gate_age)
    row13 = {
        "constants": {k: float(getattr(K.monotony, k)) for k in ("SLOPE", "CAP", "HALF_LIFE_H", "WINDOW_H", "STAPLE",
                                                                  "MEAL_KCAL", "BORED_MAX")} |
        {"FLOOR_EPS": float(K.hybrid.FLOOR_EPS), "moodRiseUnhappy_per_h": float(K.hybrid.defaults().moodRiseUnhappy) * 3600,
         "moodRiseBored_per_h": float(K.hybrid.defaults().moodRiseBored) * 3600},
        "gate": {"panicTarget": L.g(gate, "record", "values", L.PTARGET), "PANIC": L.g(gate, "server_before", "PANIC"),
                 "UNHAPPINESS_before": L.g(gate, "server_before", "UNHAPPINESS"),
                 "BOREDOM_before": L.g(gate, "server_before", "BOREDOM"),
                 "UNHAPPINESS_after": L.g(gate, "server_after", "UNHAPPINESS"),
                 "BOREDOM_after": L.g(gate, "server_after", "BOREDOM"),
                 "client_after": {k: L.g(gate, "client_after", k) for k in ("UNHAPPINESS", "BOREDOM", "PANIC")},
                 "dehydPct": L.g(gate, "record", "values", L.DEHYD), "age": gate_age} if gate else None,
        "eats": eats,
        "rows": summarize_rows(rows_all, K),
        "release": release(sessions, rows_all, K, eats),
        "reconnect": reconnect(sessions, K),
        "days": day_table(sessions, K, eats, gate_age, end_age),
        "resets": resets(sessions, rows_all, K),
        "guard": guard(sessions),
    }
    rows = {"row13": row13, "drinking_sodium": drinking_sodium(sessions)}
    with open(os.path.join(out, "rows.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, sort_keys=True, default=str)
    R = row13["rows"]
    real = [e for e in eats if (e["ring"] or {}).get("target_jump_writer", 0) >= 0.5]
    days = row13["days"]["days"]
    rc = row13["reconnect"]
    verdicts = {
        "A_NO_JUMP_PAIR": {e["label"]: e["no_jump"] for e in eats if (e.get("target_jump") or 0) >= 0.5},
        "A_FIRST_RISE_NEXT_MINUTE": {e["label"]: (e["ring"] or {}).get("first_rise_at_next_minute") for e in real},
        "A_NO_JUMP_RING": {e["label"]: (e["ring"] or {}).get("no_jump_in_eat_minute") for e in real},
        "B_TWIN": R["TWIN"]["over"] == 0 and R["TWIN"]["graded"] > 0,
        "B_MODEL_U": R["MODEL_U"]["over"] == 0 and R["MODEL_U"]["graded"] > 0,
        "B_MODEL_B": R["MODEL_B"]["outside"] == 0 and R["MODEL_B"]["graded"] > 0,
        "B_TRACK_U": R["TRACK_U"]["over"] == 0 and R["TRACK_U"]["graded"] > 0,
        "B_TRACK_B": R["TRACK_B"]["under"] == 0 and R["TRACK_B"]["graded"] > 0,
        "C_BORED_UNDER_49": R["BORED_MAX"]["ok"],
        "D_RELEASE": ({k: row13["release"][k]["over"] == 0 for k in ("U", "B")}
                      if row13["release"].get("measured") else None),
        "E_REPLAY": {p: {k: (v.get("rows_over") == 0 if v.get("n") else None) for k, v in s["vs_replay"].items()}
                     for p, s in per.items()},
        "RECONNECT_LANDED": rc.get("landed_on_target"),
        "RECONNECT_AWAY_GE_6H": (rc.get("away_h") or 0) >= L.AWAY_H if rc.get("away_h") is not None else None,
        "CLIENT_DAYEND": {d: (abs(v.get("client_minus_server_U") or 99) <= 0.05 and
                              abs(v.get("client_minus_server_B") or 99) <= 0.05) for d, v in days.items()},
        "PANIC_OVER_5_ROWS": {p: s["panic"]["panic_over_5_rows"] for p, s in per.items()},
        "REPLAY_TOOL_OK": {p: s["tool_diff"]["ok"] for p, s in per.items()},
        "SODIUM_GRADE_MAX": rows["drinking_sodium"]["grade_max_chain"],
        "EXE_FALSE": {p: gg["exe_true_rows"] == 0 and gg["exe_present_rows"] > 0 and gg["asleep_rows"] == 0
                      for p, gg in row13["guard"].items()}}
    summ = {"tool_commit": _git("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
            "grade_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x34_grade.py"),
            "lib_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x34_monotony_lib.py"),
            "sessions": [S.pre for S in sessions], "verdicts": verdicts}
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summ, fh, indent=1, sort_keys=True, default=str)
    print(json.dumps(verdicts, indent=1, default=str))


if __name__ == "__main__":
    main()
