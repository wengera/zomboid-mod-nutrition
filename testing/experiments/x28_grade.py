"""x28_grade -- the committed grade of the Plan 11f Task 5r chain (x281..x284; research row 7, the steady eater, re-run
on the build where the sodium drain is fixed): an ANALYSIS script, not a driver (it boots nothing). Written and
committed before the chain's first boot; its output is a DERIVED artifact folder (ruling T4-3: every number a row may
cite is emitted by a committed script).

    python testing/experiments/x28_grade.py [--out testing/artifacts/x28-grade-YYYYMMDD]

The inputs are each session's artifact folder testing/artifacts/x28N-*/: steady-N.json (the driver's eats, stops,
refills and verdicts), events.json (the eats and the autoDrop drinks, x28_steady_lib change 4), start.json,
start-stats.json, player.json, the minute-ring pages and the slot files. The tool is tools/replay_live.py at HEAD with
the live server's sleep option (sleep_allowed false); its auto-drink detector runs as a check (counted, never injected).

What it writes:
  x28N.json     per session: the replay of live re-run (its diff under HUNGER 0.002, es 0.005, L 0.5 %), the detector's
                count beyond the autoDrop drinks and over the eats alone, the meal reads (live es at the read, the ring's
                and the replay's es on the first ring row after it), the refills.
  rows.json     row7: es at every hour of day 5 (01:00 .. 24:00, the ring row at or before each hour: live, and the
                session replay's row of the same s), the band 1.00 +/- 0.03 and the 0.005 agreement; the intake per
                chain day (landed eats at their ring age) over the live maint and the +/-3 % clause on days 2-5; the
                billed eeDay per mod day (07:00 to 07:00); the hourly es of the whole chain; the meal reads; a
                projection arm (a replay arm from x281's start record on a synthetic one-minute clock, hour offset 7:
                the maint and request meals at the live read ages sized by the arm's own es, the autoDrop drinks at
                their ring ages; a reading, no live counterpart) and the 70 kg man's server-path pins
                (test_replay_live_energy.py: ratios 1.0011, 0.9956, 0.997; es 1.0018-1.0022).
                drinking: per chain day the mod side (every ring row's autoDrop, LITRES_PER_THIRST x autoDrop litres;
                the writer's sip folds), the canteen side (each refill's fill less the next refill's left-over, booked
                on the day of the later refill), the food water of the landed eats (their declared water), the ring's
                coverage of the day (hours), and the drinking-volume oracle's band 2.0-3.0 L/d as a reading.
                sodium: per chain day fluids.na, fluids.water and naPlasma at the day's last ring row, naPlasma's min
                and max, the hyponatraemia grade's max (the mod's K.fluids.hyponatGrade), sweat6h's max, and the na
                change against K.fluids.BASAL_NA; the last session's slot records.
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
import x28_steady_lib as L  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
PREFIXES = ("x281", "x282", "x283", "x284")
TOL_ES = 0.005
STEADY = 0.03
INTAKE_TOL = 0.03
DRINK_BAND = (2.0, 3.0)        # the drinking-volume oracle's man (test_sodium_balance.py), L/d of beverages
MAN_PINS = {"ratios_days_1_3": [1.0011, 0.9956, 0.997], "es_day5": [1.0018, 1.0022],
            "source": "testing/tests/kernel/test_replay_live_energy.py test_the_steady_eater_on_the_server_path"}
ARM_PATHS = ("body.energyState", "body.eeDay", "fluids.na", "fluids.water", "fluids.naPlasma")


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


def food_water(full):
    """The declared water (g) of a study food (tkx_study_foods.txt via the tool's parser)."""
    spec = RL.study_foods().get(full) or {}
    for part in str(spec.get("declared") or "").split(";"):
        k, _, v = part.partition(":")
        if k.strip() == "water":
            return float(v)
    return 0.0


class Sess:
    def __init__(self, n, pre):
        self.n, self.pre = n, pre
        self.dir = folder(pre)
        self.doc = read(self.dir, "steady-%d.json" % n)
        files = [f for f in (L.g(self.doc, "verdicts", "RING", "observed", "files") or []) if f]
        self.ring, self.rpaths = (RL.load_ring([os.path.join(self.dir, f) for f in files]) if files else ([], []))
        self.ring = [r for r in self.ring if r.get("age") is not None]
        self.events = read(self.dir, "events.json") if os.path.isfile(os.path.join(self.dir, "events.json")) else []
        self.start = read(self.dir, "start.json")
        self.stats = read(self.dir, "start-stats.json")
        self.player = read(self.dir, "player.json") if os.path.isfile(os.path.join(self.dir, "player.json")) else None
        rec = self.start.get("rec", self.start)
        self.a0 = L.num(L.g(rec, "satiety", "t")) or L.num(rec.get("kineticsAge"))
        if not self.ring:
            self.rows, self.be, self.diff, self.detected, self.rep_by, self.alone = [], None, {"ok": None}, [], {}, []
            return
        self.rows, self.be = RL.replay_live(self.ring, self.events, self.start, paths=self.rpaths, user=L.USER,
                                            player=self.player, start_stats=self.stats,
                                            sleep_allowed=L.SLEEP_ALLOWED)
        self.diff = RL.diff(self.rows, self.ring)
        self.detected = RL.detect_autodrinks(self.ring, self.events)
        self.alone = RL.detect_autodrinks(self.ring, [e for e in self.events if e.get("label") != "autodrop"])
        self.rep_by = {r["s"]: r for r in self.rows}

    def summary(self):
        meals = []
        for st in self.doc.get("stops") or []:
            if st.get("kind") not in ("maint", "request"):
                continue
            a = L.num(L.g(st, "read", "age"))
            nxt = next((r for r in self.ring if a is not None and r["age"] > a + 1e-9), None)
            rp = self.rep_by.get(nxt["s"]) if nxt else None
            es_l = nxt.get("body.energyState") if nxt else None
            es_r = rp.get("body.energyState") if rp else None
            meals.append({"label": st["label"], "kind": st["kind"], "read_age": a, "hod": st.get("hod"),
                          "es_read": L.g(st, "read", "es"), "naPlasma_read": L.g(st, "read", "naPlasma"),
                          "ring_s": nxt["s"] if nxt else None, "es_ring": es_l, "es_replay": es_r,
                          "es_diff": (es_l - es_r) if (es_l is not None and es_r is not None) else None,
                          "target": st.get("target"), "carry_in": st.get("carry_in"), "portions": st.get("portions"),
                          "eaten_kcal": st.get("eaten_kcal"), "carry_out": st.get("carry_out")})
        refills = [{"label": st["label"], "age": st.get("age"), "left_l": st.get("left_l"),
                    "filled_l": st.get("filled_l"), "fill_ok": st.get("fill_ok"),
                    "thirst": L.g(st, "probe", "thirst"), "autoDrink": L.g(st, "probe", "autoDrink")}
                   for st in self.doc.get("stops") or [] if st.get("kind") == "refill"]
        drops = [e for e in self.events if e.get("label") == "autodrop"]
        return {"run_id": self.doc.get("run_id"), "rows": len(self.rows),
                "diff": {k: self.diff.get(k) for k in ("fields", "classes", "ok")} | {
                    "findings_n": len(self.diff.get("findings", [])), "findings": self.diff.get("findings", [])[:20]},
                "autodrop_events": {"n": len(drops), "water_g": sum(e["vec"]["water"] for e in drops)},
                "detector_beyond_autodrops": self.detected,
                "detector_alone": {"n": len(self.alone), "litres": sum(e["litres"] for e in self.alone)},
                "start_age": self.a0, "offset": self.be.R.offset if self.be is not None else None,
                "no_ring": not self.ring, "ring_first_age": self.ring[0]["age"] if self.ring else None,
                "ring_last_age": self.ring[-1]["age"] if self.ring else None, "meals": meals, "refills": refills,
                "driver_verdicts": {k: v.get("verdict") for k, v in (self.doc.get("verdicts") or {}).items()}}


def live_eats(sessions):
    """Every landed live eat with its ring age (else its polled landing age, named), its food and its stop."""
    out = []
    for S in sessions:
        stop_of = {}
        for st in S.doc.get("stops") or []:
            for lab in st.get("eats") or []:
                stop_of[lab] = st
        for e in S.doc.get("eats") or []:
            if not e.get("landed"):
                continue
            st = stop_of.get(e["label"]) or {}
            age, src = e.get("ring_age"), "ring"
            if age is None:
                age, src = e.get("landed_age_polled"), "polled"
            if age is None:
                continue
            out.append({"age": age, "age_source": src, "food": e["food"], "label": e["label"], "stop": st.get("label"),
                        "kind": st.get("kind"), "session": S.pre})
    out.sort(key=lambda x: x["age"])
    return out


def by_day(items):
    d = {}
    for age, v in items:
        k = L.day_of(age)
        d[k] = d.get(k, 0.0) + v
    return d


def row7(sessions, eats, maint):
    ring_all = [r for S in sessions for r in S.ring]
    d5 = []
    for h in range(1, 25):
        a = L.at(5, h)
        for S in sessions:
            if S.ring and S.ring[0]["age"] <= a <= S.ring[-1]["age"] + 1e-9:
                r = L.row_at(S.ring, a)
                rp = S.rep_by.get(r["s"])
                es, er = r.get("body.energyState"), (rp.get("body.energyState") if rp else None)
                d5.append({"hour": h, "age": a, "session": S.pre, "s": r["s"], "row_age": r["age"], "es": es,
                           "es_replay": er, "diff": (es - er) if (es is not None and er is not None) else None,
                           "replay_row_flags": {k: rp.get(k) for k in ("between", "suspect", "offline", "gap")}
                           if rp else None})
                break
    es5 = [x["es"] for x in d5 if x["es"] is not None]
    dif5 = [abs(x["diff"]) for x in d5 if x["diff"] is not None]
    hourly = []
    for S in sessions:
        if not S.ring:
            continue
        for h in range(int(S.ring[0]["age"]) + 1, int(S.ring[-1]["age"]) + 1):
            r = L.row_at(S.ring, h)
            if r is None:
                continue
            rp = S.rep_by.get(r["s"])
            hourly.append({"age": h, "day": L.day_of(h), "hod": (h + L.HOUR_OFFSET) % 24, "session": S.pre,
                           "es": r.get("body.energyState"), "es_replay": rp.get("body.energyState") if rp else None,
                           "HUNGER": r.get("HUNGER"), "THIRST": r.get("THIRST")})
    live_day = by_day([(e["age"], L.eat_kcal(e["food"])) for e in eats])
    intake = {}
    for d in sorted(live_day):
        k = live_day[d]
        intake[str(d)] = {"live_kcal": k, "over_maint": (k / maint) if maint else None,
                          "request_day": d in (2, 3, 4, 5),
                          "within_3pct": (abs(k / maint - 1) <= INTAKE_TOL) if (maint and d in (2, 3, 4, 5)) else None}
    billed = {}
    for k in range(0, 8):
        last = None
        for r in ring_all:
            if int(r["age"] // 24) == k and r.get("body.eeDay") is not None:
                last = r
        if last is not None:
            billed[k] = {"mod_day_ages": [24 * k, 24 * k + 24], "last_row_age": last["age"],
                         "eeDay": last["body.eeDay"], "complete": last["age"] > 24 * k + 23.9}
    return {"day5_hourly": d5, "hours_read": len(d5), "es_min": min(es5) if es5 else None,
            "es_max": max(es5) if es5 else None,
            "band_ok": (len(es5) == 24 and all(abs(x - 1) <= STEADY for x in es5)) if es5 else None,
            "hours_outside_band": [x["hour"] for x in d5 if x["es"] is not None and abs(x["es"] - 1) > STEADY],
            "replay_max_diff": max(dif5) if dif5 else None,
            "replay_ok": (len(dif5) == 24 and max(dif5) <= TOL_ES) if dif5 else None,
            "intake": intake, "maint_kcal": maint, "billed_by_mod_day": billed, "hourly_all": hourly,
            "man_pins": MAN_PINS}


def projection(sessions, maint):
    """A replay arm from x281's start record (synthetic one-minute clock, hour offset 7): each live meal stop as a tool
    meal at its live read age (maint: the live maint / 3; request: sized by the arm's own es), and the autoDrop drinks
    at their ring ages. A reading only."""
    S1 = sessions[0]
    ev = []
    for S in sessions:
        for st in S.doc.get("stops") or []:
            a = L.num(L.g(st, "read", "age"))
            if a is None:
                continue
            if st.get("kind") == "maint":
                ev.append({"age": a, "kind": "meal", "size": maint / 3.0, "food": L.MIX650})
            elif st.get("kind") == "request":
                ev.append({"age": a, "kind": "meal", "size": "request", "food": L.MIX650})
        for e in L.autodrop_events(S.ring):
            ev.append({"age": e["age"], "kind": "drink", "vec": e["vec"]})
    end = L.at(6, 0.25)
    ev = [e for e in ev if S1.a0 + 1e-9 < e["age"] < end - 1.0 / 60]     # inside the arm's synthetic clock
    ev.sort(key=lambda x: x["age"])
    rows, be = RL.replay_arm(ev, start=S1.start, minutes=int(round((end - S1.a0) * 60)), start_age=S1.a0,
                             paths=ARM_PATHS, player=S1.player, stats=S1.stats, hour_offset=L.HOUR_OFFSET,
                             sleep_allowed=L.SLEEP_ALLOWED)
    kd = by_day([(e["age"], e["kcal"] or 0.0) for e in be.eats if e["kind"] != "drink"])
    p5 = [L.row_at(rows, L.at(5, h)).get("body.energyState") for h in range(1, 25)]
    return {"note": "a replay arm, no live counterpart: x281's start record, the live meal read ages, the autoDrop "
                    "drinks at their ring ages (drinks in the attach gaps are absent)",
            "intake": {str(d): {"kcal": kd[d], "over_maint": kd[d] / maint} for d in sorted(kd)},
            "day5_es": [min(p5), max(p5)], "day5_hourly_es": p5,
            "band_ok": all(abs(x - 1) <= STEADY for x in p5)}


def drinking(sessions, eats):
    out = {}
    for S in sessions:
        for e in L.autodrop_events(S.ring):
            d = out.setdefault(str(L.day_of(e["age"])), {})
            d["mod_g"] = d.get("mod_g", 0.0) + e["vec"]["water"]
            d["autodrops"] = d.get("autodrops", 0) + 1
        prev = None
        for r in S.ring:
            d = out.setdefault(str(L.day_of(r["age"])), {})
            d["ring_rows"] = d.get("ring_rows", 0) + 1
            d["ring_hours"] = d.get("ring_hours", 0.0) + (r["age"] - prev["age"] if prev is not None and
                                                           L.day_of(prev["age"]) == L.day_of(r["age"]) else 0.0)
            if prev is not None:
                a, b = L.num(prev.get(L.WSIPS)), L.num(r.get(L.WSIPS))
                if a is not None and b is not None and b > a:
                    d["writer_sips"] = d.get("writer_sips", 0) + int(round(b - a))
            prev = r
    fills = []
    for S in sessions:
        for st in S.doc.get("stops") or []:
            if st.get("kind") == "refill":
                fills.append({"age": st.get("age"), "left_l": st.get("left_l"), "filled_l": st.get("filled_l"),
                              "label": st.get("label"), "session": S.pre})
    fills = [f for f in fills if f["age"] is not None]
    fills.sort(key=lambda f: f["age"])
    intervals = []
    for a, b in zip(fills, fills[1:]):
        if a["filled_l"] is None or b["left_l"] is None:
            continue
        drunk = a["filled_l"] - b["left_l"]
        intervals.append({"from": a["label"], "to": b["label"], "from_age": a["age"], "to_age": b["age"],
                          "drunk_l": drunk, "empty_at_end": b["left_l"] <= 1e-6})
        d = out.setdefault(str(L.day_of(b["age"])), {})
        d["canteen_l"] = d.get("canteen_l", 0.0) + drunk
        if b["left_l"] <= 1e-6:
            d["canteen_ran_dry"] = d.get("canteen_ran_dry", 0) + 1
    for e in eats:
        d = out.setdefault(str(L.day_of(e["age"])), {})
        d["food_water_g"] = d.get("food_water_g", 0.0) + food_water(e["food"])
    for k, d in out.items():
        d["mod_l"] = d.get("mod_g", 0.0) / 1000.0
        d["in_band"] = (DRINK_BAND[0] <= d["mod_l"] <= DRINK_BAND[1]) if d.get("ring_hours", 0) > 23.5 else None
    return {"by_day": dict(sorted(out.items(), key=lambda kv: int(kv[0]))), "intervals": intervals,
            "band_l_per_day": list(DRINK_BAND),
            "note": "mod side: every ring row's fluids.autoDrop x LITRES_PER_THIRST (rows missing in the attach gaps); "
                    "canteen side: each refill's fill less the next refill's left-over, booked on the later refill's "
                    "day (an interval that ran dry undercounts)"}


def sodium(sessions):
    K = L._kh_static().K
    out = {}
    for S in sessions:
        for r in S.ring:
            d = out.setdefault(str(L.day_of(r["age"])), {})
            for k in ("fluids.na", "fluids.water", "fluids.k", "fluids.naPlasma"):
                if L.num(r.get(k)) is not None:
                    d.setdefault(k + "_first", r[k])
                    d[k + "_end"] = r[k]
            d.setdefault("first_age", r["age"])
            d["last_age"] = r["age"]
            p = L.num(r.get("fluids.naPlasma"))
            if p is not None:
                d["naPlasma_min"] = min(d.get("naPlasma_min", p), p)
                d["naPlasma_max"] = max(d.get("naPlasma_max", p), p)
            sw = L.num(r.get("fluids.sweat6h"))
            if sw is not None:
                d["sweat6h_max"] = max(d.get("sweat6h_max", sw), sw)
    for d in out.values():
        d["grade_max"] = L.hypo_grade(d.get("naPlasma_min"))
        if d.get("fluids.na_end") is not None and d.get("fluids.na_first") is not None:
            span = d["last_age"] - d["first_age"]
            d["na_change"] = d["fluids.na_end"] - d["fluids.na_first"]
            d["na_change_per_24h"] = d["na_change"] / span * 24 if span > 0 else None
    last = sessions[-1]
    slots = []
    for f in sorted(os.listdir(last.dir)):
        if not (f.startswith("slot-") and f.endswith(".json")):
            continue
        with open(os.path.join(last.dir, f), encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
        doc = json.loads(lines[-1])
        rec = doc["rec"]
        fl = rec["fluids"]
        slots.append({"file": f, "gen": doc.get("gen"), "dead": rec.get("dead"), "satiety_t": rec["satiety"]["t"],
                      "fluids.na": fl.get("na"), "fluids.water": fl.get("water"), "fluids.k": fl.get("k")})
    return {"by_day": dict(sorted(out.items(), key=lambda kv: int(kv[0]))),
            "constants": {"BASAL_NA": float(K.fluids.BASAL_NA), "HYPO_NA": float(K.fluids.HYPO_NA),
                          "HYPO_CAP": float(K.fluids.HYPO_CAP),
                          "HYPONAT": [float(K.fluids.HYPONAT[i]) for i in (1, 2, 3)]},
            "grade_max_chain": (max(d["grade_max"] for d in out.values())
                                if out and all(d.get("grade_max") is not None for d in out.values()) else None),
            "last_slots": slots}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ART, "x28-grade-" + datetime.date.today().strftime("%Y%m%d")))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    sessions = []
    for n, pre in enumerate(PREFIXES, 1):
        try:
            sessions.append(Sess(n, pre))
        except SystemExit as e:
            print("skip %s: %s" % (pre, e))
    summ = {"tool_commit": _git("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
            "grade_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x28_grade.py"),
            "lib_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x28_steady_lib.py"),
            "sessions": {}}
    for S in sessions:
        doc = S.summary()
        with open(os.path.join(a.out, S.pre + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True, default=str)
        summ["sessions"][S.pre] = {"replay_ok": doc["diff"]["ok"], "fields": doc["diff"]["fields"],
                                   "detector_beyond_autodrops": len(doc["detector_beyond_autodrops"]),
                                   "autodrops": doc["autodrop_events"]["n"], "driver_verdicts": doc["driver_verdicts"]}
    rows = {}
    if sessions and sessions[0].pre == "x281":
        maint = L.num(L.g(sessions[0].doc, "readings", "maint_kcal"))
        eats = live_eats(sessions)
        r7 = row7(sessions, eats, maint)
        r7["meal_es"] = [m for S in sessions for m in S.summary()["meals"]]
        r7["projection"] = projection(sessions, maint)
        rows["row7"] = r7
        rows["drinking"] = drinking(sessions, eats)
        rows["sodium"] = sodium(sessions)
    with open(os.path.join(a.out, "rows.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, sort_keys=True, default=str)
    r7 = rows.get("row7") or {}
    summ["verdicts"] = {
        "R7BAND": r7.get("band_ok"), "R7REPLAY": r7.get("replay_ok"),
        "R7INTAKE": {d: v.get("within_3pct") for d, v in (r7.get("intake") or {}).items() if v.get("request_day")},
        "SODIUM_GRADE0": ((rows.get("sodium") or {}).get("grade_max_chain") == 0) if rows.get("sodium") else None,
        "SESSIONS_REPLAY_OK": {S.pre: S.diff.get("ok") for S in sessions}}
    with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summ, fh, indent=1, sort_keys=True, default=str)
    print(json.dumps(summ["verdicts"], indent=1))


if __name__ == "__main__":
    main()
