"""x27_grade -- the committed grade of the Plan 11f Task 5 energy chain (x271..x275; research rows 6-8): an ANALYSIS
script, not a driver (it boots nothing). Its output is a DERIVED artifact folder (ruling T4-3: every number a row may
cite is emitted by a committed script).

    python testing/experiments/x27_grade.py [--out testing/artifacts/x27-grade-YYYYMMDD]

The inputs are each session's committed artifact folder testing/artifacts/x27N-*/: energy-N.json (the driver's eats,
stops and verdicts), events.json, start.json, start-stats.json, player.json and the minute-ring pages. The tool is
tools/replay_live.py at HEAD with the live server's sleep option (sleep_allowed false) and the auto-drink detector as a
check (counted, never injected).

What it writes:
  x27N.json   per session: the replay of live re-run (its diff under HUNGER 0.002, es 0.005, L 0.5 %), the detector's
              count, the meal reads (live es at the read against the replay's es on the first ring row after it).
  rows.json   row 6: the chain's fast and fed arms (replay arms from x271's start record on a synthetic one-minute
              clock, the hour offset 7: the live eats before the fast's end at their ring ages, every water eat as live,
              each request meal at its live read age as the tool's request meal, size computed from the arm's own es;
              the fed arm adds three maint meals of the live maint kcal / 3 at 08:00, 13:00 and 20:00 on day 1),
              the intake per chain day of live and both arms, the day-2 and day-3 ratios (live over fed, fast arm over
              fed) and their agreement within 2 %, the replay ratios against S1613's 1.20 and S1614's 1.0, the fast's
              es at 12, 24 and 36 h (live ring, session replay, fast arm; eb24 the fast arm's, the ring has none), the
              energy ladder's first crossings; also a chain replay of live (every live eat at its ring age on the
              synthetic clock) for the es at each meal read.
              row 7: es at every hour of day 5 (live ring, session replay), the band 1.00 +/- 0.03 and the 0.005
              agreement, the intake per day over maint (and over the billed eeDay at the day's last ring row).
              row 8: x275's live 24 h mean written HUNGER from 08:00 day 6, its replay of live, the three-Mixed667 arm
              (x275's replay of live with the six Mixed333 eats replaced by Mixed667 at 08:00, 13:00 and 18:00, on the
              ring's clock), the ratios six over three, their agreement within 1 % and the band [0.9, 1.3].
  summary.json  each verdict.
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
import x27_energy_lib as L  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
PREFIXES = ("x271", "x272", "x273", "x276")   # x274 and x275 never ran: the chain admin died in x273 (F-T5-1)
ARTIFACT_N = {"x271": 1, "x272": 2, "x273": 3, "x276": 6}
TOL_RATIO = 0.02
TOL_ES = 0.005
TOL_ROW8 = 0.01
STEADY = 0.03
INTAKE_TOL = 0.03
ARM_PATHS = ("body.energyState", "body.eb24", "body.eeDay", "body.lm", "fluids.na", "fluids.water", "fluids.k")


def _git(*a):
    import subprocess
    try:
        return subprocess.run(["git"] + list(a), cwd=REPO, capture_output=True, text=True).stdout.strip()
    except OSError:
        return None


def folder(pre):
    hits = sorted(d for d in os.listdir(ART) if d.startswith(pre + "-"))
    if len(hits) != 1:
        raise SystemExit("expected one artifact folder for %s, found %r" % (pre, hits))
    return os.path.join(ART, hits[0])


def read(run, name):
    with open(os.path.join(run, name), encoding="utf-8") as fh:
        return json.load(fh)


class Sess:
    def __init__(self, n, pre):
        self.n, self.pre = n, pre
        self.dir = folder(pre)
        self.doc = read(self.dir, "energy-%d.json" % n)
        files = [f for f in (L.g(self.doc, "verdicts", "RING", "observed", "files") or []) if f]
        self.ring, self.rpaths = (RL.load_ring([os.path.join(self.dir, f) for f in files]) if files else ([], []))
        self.ring = [r for r in self.ring if r.get("age") is not None]
        self.events = read(self.dir, "events.json") if os.path.isfile(os.path.join(self.dir, "events.json")) else []
        self.start = read(self.dir, "start.json")
        self.stats = read(self.dir, "start-stats.json")
        self.player = read(self.dir, "player.json") if os.path.isfile(os.path.join(self.dir, "player.json")) else None
        rec = self.start.get("rec", self.start)
        self.a0 = L.num(L.g(rec, "satiety", "t")) or L.num(rec.get("kineticsAge"))
        if not self.ring:                      # x273: the lib's budget-stop TypeError skipped R and D (F-T5-2)
            self.rows, self.be, self.diff, self.detected, self.rep_by = [], None, {"ok": None}, [], {}
            return
        self.rows, self.be = RL.replay_live(self.ring, self.events, self.start, paths=self.rpaths, user=L.USER,
                                            player=self.player, start_stats=self.stats,
                                            sleep_allowed=L.SLEEP_ALLOWED)
        self.diff = RL.diff(self.rows, self.ring)
        self.detected = RL.detect_autodrinks(self.ring, self.events)
        self.rep_by = {r["s"]: r for r in self.rows}

    def summary(self):
        meals = []
        for st in self.doc.get("stops") or []:
            if st.get("kind") not in ("maint", "request", "six"):
                continue
            a = L.num(L.g(st, "read", "age"))
            nxt = next((r for r in self.ring if a is not None and r["age"] > a + 1e-9), None)
            rp = self.rep_by.get(nxt["s"]) if nxt else None
            es_l = nxt.get("body.energyState") if nxt else None
            es_r = rp.get("body.energyState") if rp else None
            meals.append({"label": st["label"], "kind": st["kind"], "read_age": a, "hod": st.get("hod"),
                          "es_read": L.g(st, "read", "es"), "ring_s": nxt["s"] if nxt else None, "es_ring": es_l,
                          "es_replay": es_r, "es_diff": (es_l - es_r) if (es_l is not None and es_r is not None)
                          else None, "target": st.get("target"), "carry_in": st.get("carry_in"),
                          "portions": st.get("portions"), "eaten_kcal": st.get("eaten_kcal"),
                          "carry_out": st.get("carry_out")})
        return {"run_id": self.doc.get("run_id"), "rows": len(self.rows),
                "diff": {k: self.diff.get(k) for k in ("fields", "classes", "ok")} | {
                    "findings_n": len(self.diff.get("findings", [])), "findings": self.diff.get("findings", [])[:20]},
                "autodrinks_detected": self.detected, "start_age": self.a0,
                "offset": self.be.R.offset if self.be is not None else None, "no_ring": not self.ring,
                "ring_first_age": self.ring[0]["age"] if self.ring else None,
                "ring_last_age": self.ring[-1]["age"] if self.ring else None, "meals": meals,
                "driver_verdicts": {k: v.get("verdict") for k, v in (self.doc.get("verdicts") or {}).items()}}


def live_eats(sessions):
    """Every landed live eat with its ring age, its food and its stop."""
    out = []
    for S in sessions:
        stop_of = {}
        for st in S.doc.get("stops") or []:
            for lab in st.get("eats") or []:
                stop_of[lab] = st
        for e in S.doc.get("eats") or []:
            st = stop_of.get(e["label"]) or {}
            age, src = e.get("ring_age"), "ring"
            if age is None and not S.ring and e.get("landed"):
                # no ring (x273): the eat's polled landing age (time.snapshot right after the landed count rose)
                age, src = e.get("landed_age_polled"), "polled"
            if age is None:
                continue
            out.append({"age": age, "age_source": src, "food": e["food"], "label": e["label"], "stop": st.get("label"),
                        "kind": st.get("kind"), "session": S.pre})
    out.sort(key=lambda x: x["age"])
    return out


def by_day(items):
    d = {}
    for age, kcal in items:
        k = L.day_of(age)
        d[k] = d.get(k, 0.0) + kcal
    return d


def arm_run(S1, events, end_age):
    a0 = S1.a0
    mins = int(round((end_age - a0) * 60))
    rows, be = RL.replay_arm(events, start=S1.start, minutes=mins, start_age=a0, paths=ARM_PATHS, player=S1.player,
                             stats=S1.stats, hour_offset=L.HOUR_OFFSET, sleep_allowed=L.SLEEP_ALLOWED)
    return rows, be, a0


def first_cross(rows, th, t0, t1):
    x = next((r for r in rows if t0 < r["age"] < t1 and r.get("body.energyState") is not None
              and r["body.energyState"] >= th), None)
    return None if x is None else {"age": x["age"], "h_after_fast_t0": x["age"] - t0}


def row6_7(sessions):
    S1 = sessions[0]
    eats = live_eats(sessions)
    stops = [st for S in sessions for st in (S.doc.get("stops") or [])]
    maint = L.num(L.g(S1.doc, "readings", "maint_kcal"))
    req = [st for st in stops if st.get("kind") == "request"]
    end = L.at(4, 0.0)        # the end of day 3: the chain admin died at 113.78 (00:46 day 4, x273)
    pre = [{"age": e["age"], "kind": "eat", "food": e["food"]} for e in eats
           if e["age"] < L.FAST_T1 and e["kind"] != "six"]
    water = [{"age": e["age"], "kind": "eat", "food": e["food"]} for e in eats
             if e["age"] >= L.FAST_T1 and e["kind"] == "water" and e["age"] < end]
    reqm = [{"age": L.g(st, "read", "age"), "kind": "meal", "size": "request", "food": L.MIX650} for st in req
            if L.num(L.g(st, "read", "age")) is not None and L.g(st, "read", "age") < end]
    fedm = [{"age": L.at(1, h), "kind": "meal", "size": maint / 3.0, "food": L.MIX650} for h in (8.0, 13.0, 20.0)]
    chain_live = [{"age": e["age"], "kind": "eat", "food": e["food"]} for e in eats if e["age"] < end]
    arms = {}
    proj = [{"age": L.at(d, h), "kind": "meal", "size": "request", "food": L.MIX650} for d in (4, 5)
            for h in (8.0, 13.0, 20.0)]
    for name, ev, e_end in (("fast", pre + water + reqm, end), ("fed", pre + water + reqm + fedm, end),
                            ("chain_live", chain_live, end),
                            ("row7_projection", pre + water + reqm + proj, L.at(6, 0.0))):
        ev = sorted(ev, key=lambda x: x["age"])
        rows, be, a0 = arm_run(S1, ev, e_end)
        arms[name] = {"rows": rows, "be": be, "by_day": by_day([(e["age"], e["kcal"] or 0.0) for e in be.eats])}
    live_day = by_day([(e["age"], L.eat_kcal(e["food"])) for e in eats])
    fed, fast = arms["fed"]["by_day"], arms["fast"]["by_day"]
    out = {"maint_kcal": maint, "arm_start_age": S1.a0, "arm_end_age": end,
           "intake_by_day": {"live": live_day, "fast_arm": fast, "fed_arm": fed,
                             "chain_live_arm": arms["chain_live"]["by_day"]}}
    ratios = {}
    for d, study in ((2, 1.20), (3, 1.0)):
        rl = live_day.get(d, 0.0) / fed[d] if fed.get(d) else None
        rr = fast.get(d, 0.0) / fed[d] if fed.get(d) else None
        ratios[str(d)] = {"live": rl, "replay": rr, "live_over_replay": (rl / rr) if (rl and rr) else None,
                          "ok": (abs(rl / rr - 1) <= TOL_RATIO) if (rl and rr) else None, "study": study,
                          "replay_over_study": (rr / study) if rr else None,
                          "within_1_1x": (max(rr / study, study / rr) <= 1.1) if rr else None}
    out["ratios"] = ratios
    # the fast's log
    log = {}
    ring_all = [r for S in sessions for r in S.ring]
    rep_all = {}
    for S in sessions:
        rep_all.update({(S.pre, r["s"]): r for r in S.rows})
    for hh in (12, 24, 36):
        a = L.FAST_T0 + hh
        ent = {"age": a}
        for S in sessions:
            if S.ring and S.ring[0]["age"] <= a <= S.ring[-1]["age"]:
                r = L.row_at(S.ring, a)
                rp = S.rep_by.get(r["s"])
                ent.update({"session": S.pre, "s": r["s"], "row_age": r["age"], "es_live": r.get("body.energyState"),
                            "es_session_replay": rp.get("body.energyState") if rp else None})
        fr = L.row_at(arms["fast"]["rows"], a)
        ent.update({"es_fast_arm": fr.get("body.energyState"), "eb24_fast_arm": fr.get("body.eb24")})
        log[str(hh)] = ent
    out["fast_log"] = log
    lad = {}
    for th in L.LADDER:
        lad[str(th)] = {"live": first_cross(ring_all, th, L.FAST_T0, L.FAST_T1),
                        "fast_arm": first_cross(arms["fast"]["rows"], th, L.FAST_T0, L.FAST_T1)}
    last_pre = max((e["age"] for e in eats if e["stop"] == "D0_20"), default=None)
    out["ladder"] = {"crossings": lad, "last_eat_before_fast_age": last_pre}
    # es at each meal read: live, session replay, chain replay of live, fast arm
    cl = arms["chain_live"]["rows"]
    mr = []
    for S in sessions:
        for m in S.summary()["meals"]:
            a = m["read_age"]
            c = L.row_at(cl, a) if a is not None else None
            f = L.row_at(arms["fast"]["rows"], a) if a is not None else None
            mr.append(m | {"es_chain_replay": c.get("body.energyState") if c else None,
                           "es_fast_arm": f.get("body.energyState") if f else None})
    out["meal_es"] = mr
    sess_es = [abs(m["es_diff"]) for m in mr if m.get("es_diff") is not None]
    out["R6ES"] = {"meal_reads_max_es_diff": max(sess_es) if sess_es else None,
                   "sessions_es_max": {S.pre: L.g(S.diff, "fields", "body.energyState", "max") for S in sessions},
                   "ok": bool(sess_es) and max(sess_es) <= TOL_ES and all(
                       (L.g(S.diff, "fields", "body.energyState", "max") or 0) <= TOL_ES for S in sessions)}
    # row 7: day 5
    d5 = []
    for h in range(1, 25):
        a = L.at(5, h)
        for S in sessions:
            if S.ring and S.ring[0]["age"] <= a <= S.ring[-1]["age"] + 1e-9:
                r = L.row_at(S.ring, a)
                rp = S.rep_by.get(r["s"])
                d5.append({"hour": h, "age": a, "session": S.pre, "s": r["s"], "es": r.get("body.energyState"),
                           "es_replay": rp.get("body.energyState") if rp else None})
                break
    es5 = [x["es"] for x in d5 if x["es"] is not None]
    dif5 = [abs(x["es"] - x["es_replay"]) for x in d5 if x["es"] is not None and x["es_replay"] is not None]
    # body.eeDay accumulates over the mod's day, floor(world age / 24) (07:00 to 07:00 here; the partition's close,
    # K.partition.closeDay at floor(ageH / 24) > body.dayIndex): the last ring row of each mod day k
    billed = {}
    for k in range(0, 8):
        last = None
        for r in ring_all:
            if int(r["age"] // 24) == k and r.get("body.eeDay") is not None:
                last = r
        if last is not None:
            billed[k] = {"mod_day_ages": [24 * k, 24 * k + 24], "last_row_age": last["age"],
                         "eeDay": last["body.eeDay"], "complete": last["age"] > 24 * k + 23.9,
                         "kcal_per_h": last["body.eeDay"] / (last["age"] - max(24 * k, ring_all[0]["age"]))
                         if last["age"] > max(24 * k, ring_all[0]["age"]) else None}
    intake = {}
    for d in (4, 5):
        k = live_day.get(d)
        intake[str(d)] = {"live_kcal": k, "over_maint": (k / maint) if (k and maint) else None,
                          "within_3pct": (abs(k / maint - 1) <= INTAKE_TOL) if (k and maint) else None,
                          "fed_arm_kcal": fed.get(d), "fed_over_maint": (fed[d] / maint) if fed.get(d) else None}
    pr = arms["row7_projection"]
    p5 = [L.row_at(pr["rows"], L.at(5, h)).get("body.energyState") for h in range(1, 25)]
    pmaint = {str(d): {"kcal": pr["by_day"].get(d), "over_maint": pr["by_day"][d] / maint if pr["by_day"].get(d)
                       else None} for d in (2, 3, 4, 5)}
    out["row7"] = {"live": "UNMEASURED: the chain admin died at age 113.78 (00:46 day 4, x273), before day 5",
                   "projection_note": "a replay arm only (no live counterpart): x271's start record, the live eats to "
                                      "the fast's end, the live request read ages on days 2-3, request meals at "
                                      "08:00, 13:00 and 20:00 on days 4-5, no water after day 3",
                   "projection_day5_es": [min(p5), max(p5)], "projection_day5_hourly_es": p5,
                   "projection_band_ok": all(abs(x - 1) <= STEADY for x in p5), "projection_intake": pmaint,
                   "day5_hourly": d5, "hours_read": len(d5),
                   "es_min": min(es5) if es5 else None, "es_max": max(es5) if es5 else None,
                   "band_ok": (len(es5) == 24 and all(abs(x - 1) <= STEADY for x in es5)) if es5 else None,
                   "replay_max_diff": max(dif5) if dif5 else None,
                   "replay_ok": (len(dif5) == 24 and max(dif5) <= TOL_ES) if dif5 else None,
                   "intake": intake, "billed_by_mod_day": billed}
    out["sodium"] = sodium(arms["chain_live"], ring_all)
    return out


def sodium(arm, ring_all):
    """Finding F-T5-1's trajectory on the chain replay of live (the fluids the arm steps as the live server does):
    the plasma sodium per game hour by the mod's own K.fluids.conc and naPlasma, its hyponatraemia grade, the first
    age of each grade; and the live ring's THIRST rows pinned at K.fluids.HYPO_CAP (the cap below HYPO_NA)."""
    be = arm["be"]
    K = be.K
    hourly, first = [], {}
    for r in arm["rows"][::60]:                  # one row a game hour (the synthetic clock steps one minute)
        if r.get("fluids.na") is None or r.get("body.lm") is None:
            continue
        t = be.table({"water": r["fluids.water"], "na": r["fluids.na"], "k": r.get("fluids.k") or 0.0})
        c = float(K.fluids.conc(t, r["body.lm"]))
        na = float(K.fluids.naPlasma(c))
        gr = int(K.fluids.hyponatGrade(na))
        hourly.append({"age": r["age"], "fluids.na": r["fluids.na"], "fluids.water": r["fluids.water"],
                       "naPlasma": na, "grade": gr})
        for k in range(1, gr + 1):
            first.setdefault(str(k), r["age"])
    cap = float(K.fluids.HYPO_CAP)
    pinned = [r for r in ring_all if r.get("THIRST") is not None and abs(r["THIRST"] - cap) < 1e-6]
    return {"constants": {"OSM_REF": float(K.fluids.OSM_REF), "BASAL_NA_FRAC": float(K.fluids.BASAL_NA_FRAC),
                          "AI_male_g_day": float(K.fluids.AI[1]), "HYPO_NA": float(K.fluids.HYPO_NA),
                          "HYPO_CAP": cap, "HYPONAT": [float(K.fluids.HYPONAT[i]) for i in (1, 2, 3)]},
            "basal_na_mmol_day": float(K.fluids.AI[1]) / 1000 * float(K.fluids.BASAL_NA_FRAC) * float(K.fluids.OSM_REF),
            "first_age_of_grade": first, "every_6h": hourly[::6],
            "live_thirst_rows_at_hypo_cap": len(pinned),
            "live_first_thirst_at_hypo_cap_age": pinned[0]["age"] if pinned else None}


def row8(S5, t0=L.at(0, 8.0), six_prefix="S0_"):
    """Row 8 on x276 (a fresh fixture; the window 08:00 day 0 to 08:00 day 1)."""
    rr, rows = S5.ring, S5.rows
    live = L.mean_over(rr, t0, 1440)
    rep = L.mean_over(rows, t0, 1440)
    six = [e for e in S5.events if str(e.get("label", "")).startswith(six_prefix)]
    ev = [e for e in S5.events if not str(e.get("label", "")).startswith(six_prefix)]
    three_ev = [{"age": t0 + 5.0 * k, "kind": "eat", "food": L.MIX667, "label": "T6_%d" % k} for k in range(3)]
    arm_rows, be = RL.replay_live(rr, ev + three_ev, S5.start, paths=S5.rpaths, user=L.USER, player=S5.player,
                                  start_stats=S5.stats, sleep_allowed=L.SLEEP_ALLOWED)
    three = L.mean_over(arm_rows, t0, 1440)
    last = rr[-1]["age"] if rr else None
    rl = live / three if (live and three) else None
    rp = rep / three if (rep and three) else None
    return {"window": [t0, t0 + 24.0], "ring_last_age": last, "covered": last is not None and last >= t0 + 24.0,
            "six_eats": six, "mean_live_six": live, "mean_replay_six": rep, "mean_arm_three": three,
            "ratio_live": rl, "ratio_replay": rp, "live_over_replay": (rl / rp) if (rl and rp) else None,
            "agree_1pct": (abs(rl / rp - 1) <= TOL_ROW8) if (rl and rp) else None,
            "band_ok": (0.9 <= rl <= 1.3) if rl else None,
            "server_path_70kg": {"live": 0.981, "held": 0.969}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ART, "x27-grade-" + datetime.date.today().strftime("%Y%m%d")))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    sessions = []
    for pre in PREFIXES:
        try:
            sessions.append(Sess(ARTIFACT_N[pre], pre))
        except SystemExit as e:
            print("skip %s: %s" % (pre, e))
    summ = {"tool_commit": _git("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
            "grade_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x27_grade.py"),
            "sessions": {}}
    for S in sessions:
        doc = S.summary()
        with open(os.path.join(a.out, S.pre + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True, default=str)
        summ["sessions"][S.pre] = {"replay_ok": doc["diff"]["ok"], "fields": doc["diff"]["fields"],
                                   "autodrinks": len(doc["autodrinks_detected"]),
                                   "driver_verdicts": doc["driver_verdicts"]}
    rows = {}
    if sessions and sessions[0].pre == "x271":
        rows["row6_7"] = row6_7([S for S in sessions if S.pre in ("x271", "x272", "x273")])
    s5 = next((S for S in sessions if S.pre == "x276"), None)
    if s5 is not None:
        rows["row8"] = row8(s5)
    with open(os.path.join(a.out, "rows.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, sort_keys=True, default=str)
    r67 = rows.get("row6_7") or {}
    summ["verdicts"] = {
        "R6RATIO": {k: v.get("ok") for k, v in (r67.get("ratios") or {}).items()},
        "R6ES": (r67.get("R6ES") or {}).get("ok"),
        "R7": "unmeasured live: the chain admin died at age 113.78 (x273), before day 5; rows.json row7 carries the "
              "replay-arm projection (projection_band_ok %s)" % (r67.get("row7") or {}).get("projection_band_ok"),
        "R8AGREE": (rows.get("row8") or {}).get("agree_1pct"), "R8BAND": (rows.get("row8") or {}).get("band_ok")}
    with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summ, fh, indent=1, sort_keys=True, default=str)
    print(json.dumps(summ["verdicts"], indent=1))


if __name__ == "__main__":
    main()
