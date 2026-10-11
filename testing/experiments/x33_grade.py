"""x33_grade -- the committed grade of Plan 11f Task 9 (research row 13, monotony over five game days): an ANALYSIS
script, not a driver (it boots nothing). Written and committed before the first boot of the runs it grades; its output
is a DERIVED artifact folder (ruling T4-3: every number a row may cite is emitted by a committed script).

    python testing/experiments/x33_grade.py [--out testing/artifacts/x33-grade-YYYYMMDD]

The inputs are each session's artifact folder testing/artifacts/x33N-*/: the driver's document (monotony-1.json ..
monotony-3.json), events.json (the eats, the autoDrop drinks and the setany values as stat events, x33_monotony_lib
changes 3-4), start.json, start-stats.json, player.json and the minute-ring pages. The tool is tools/replay_live.py at
HEAD with the live server's sleep option (sleep_allowed false); the activity comes from the ring's rate and exe.

Every session: the replay of live re-run and graded by the tool's own diff (HUNGER 0.002, es 0.005, L 0.5 %); the
replay's own monotony delta at each eat (its eats log: the stand-in's Stats.add, by construction the kernel's); live
UNHAPPINESS against the replay's on every ring row the replay grades (the stand-in has no vanilla mood updater, so a
difference between eats is vanilla's own term).

Row 13:
  - PER EAT: the day, the food, the record's n before and after, the server's add on each stat (post - pre, the pair
    bracketing the landing), the kernel's delta on the live record (K.monotony's constants, the entry read before the
    eat decayed to the age the record booked), the nominal delta at exact 24-hour spacing, the replay's delta, the
    client's first read showing the add, and the floor window (UNHAPPINESS over the 30 game minutes after the landing
    against the post-add value; the target's maximum);
  - THE FIFTH EATS: M4's UNHAPPINESS and BOREDOM adds against 9.978 +- 0.05, S4's against 2.4945 +- 0.05 (the oracle
    pins of test_kernel_monotony.py: the SLOPE was sized to the first, so a live match is by construction of the
    constant, ruling 8-R; the live content is the add path);
  - EQUAL: each eat's BOREDOM add against its UNHAPPINESS add;
  - CLIENT: each nonzero add on the client;
  - FLOOR: no fall below the post-add value in any window;
  - THE CLIMB (ruling T3-2, the tuning question): per arm the live UNHAPPINESS adds day by day and their running sum
    (the UNHAPPINESS a one-food diet carries, UNHAPPINESS having no vanilla fall, #3119's reading), against the
    kernel's daily projection (one eat of one type a day, days 0-13, and three a day) and the steady daily add
    SLOPE x (1 / (1 - 2^(-24 / HALF_LIFE_H)) - 1); the live day holds (UNHAPPINESS between eats);
  - the guard (exe, moving, asleep rows) and the drinking and sodium per chain day (x32_grade's form).
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
import x33_monotony_lib as L  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
CHAIN = (("x331", "monotony-1.json"), ("x332", "monotony-2.json"), ("x333", "monotony-3.json"))
FIFTH = {"M4": 9.978, "S4": 2.4945}
FIFTH_TOL = 0.05
ORACLE_PINS = {"fifth_non_staple": 9.978, "fifth_staple": 2.4945, "tolerance": FIFTH_TOL,
               "source": "testing/tests/kernel/test_kernel_monotony.py (test_the_fifth_daily_eat_reads_about_a_stale_item, "
                         "test_staples_take_the_reduced_slope); research 01 s6 row 13"}
PROJECT_DAYS = 14


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

    def replay_eats(self):
        """The replay's own monotony delta per eat (its eats log, in order), keyed by the event label."""
        evs = [e for e in self.events if e.get("kind") == "eat"]
        out = {}
        log = [x for x in (getattr(self.be, "eats", None) or []) if x.get("kind") == "eat"]
        for e, x in zip(evs, log):
            out[e.get("label")] = {"fullType": x.get("fullType"), "kcal": x.get("kcal"), "boredom": x.get("boredom"),
                                   "unhappy": x.get("unhappy"), "age": x.get("age")}
        return out

    def unhappy_vs_replay(self):
        """Live UNHAPPINESS against the replay's on every row the tool's diff grades (not between, suspect or
        offline): max abs difference and the rows, so vanilla's own term shows."""
        by = {r["s"]: r for r in self.ring}
        xs = []
        for r in self.rows:
            if r.get("between") or r.get("suspect") or r.get("offline"):
                continue
            lv = by.get(r["s"])
            if lv is None or L.num(lv.get("UNHAPPINESS")) is None or L.num(r.get("UNHAPPINESS")) is None:
                continue
            xs.append((abs(lv["UNHAPPINESS"] - r["UNHAPPINESS"]), r["s"], lv["UNHAPPINESS"], r["UNHAPPINESS"]))
        if not xs:
            return {"n": 0}
        w = max(xs)
        return {"n": len(xs), "max_abs": w[0], "worst_s": w[1], "worst_live": w[2], "worst_replay": w[3],
                "rows_over_1e3": sum(1 for x in xs if x[0] > 1e-3)}

    def summary(self):
        kinds = {}
        for e in self.events:
            kinds[e.get("kind")] = kinds.get(e.get("kind"), 0) + 1
        return {"run_id": self.doc.get("run_id"), "rows": len(self.rows), "events_by_kind": kinds,
                "ring_activity_events": len(getattr(self.be, "ring_activity", None) or []),
                "tool_diff": {k: self.diff.get(k) for k in ("fields", "classes", "ok")} | {
                    "findings_n": len(self.diff.get("findings", [])), "findings": self.diff.get("findings", [])[:20]},
                "unhappy_vs_replay": self.unhappy_vs_replay(),
                "ring_first_age": self.ring[0]["age"] if self.ring else None,
                "ring_last_age": self.ring[-1]["age"] if self.ring else None,
                "driver_verdicts": {k: v.get("verdict") for k, v in (self.doc.get("verdicts") or {}).items()}}


def eat_table(sessions, K):
    """Per mono eat, in chain order: the session's reading (x33_monotony_lib.eat_reading, re-derived here from the
    stop rows), the nominal delta, the replay's delta, the floor window off the session's ring."""
    out = []
    for S in sessions:
        rep = S.replay_eats()
        for st in S.doc.get("stops") or []:
            if st.get("kind") != "mono":
                continue
            x = L.eat_reading(st, K)
            x["session"] = S.pre
            k = int(x["day"]) if x.get("day") is not None else None
            x["nominal_delta"] = L.nominal_delta(K, k, bool(x["staple"])) if k is not None else None
            r = rep.get(st.get("label"))
            x["replay"] = r
            x["replay_minus_add"] = ({"BOREDOM": r["boredom"] - x["add"]["BOREDOM"] if x["add"]["BOREDOM"] is not None else None,
                                      "UNHAPPINESS": r["unhappy"] - x["add"]["UNHAPPINESS"]
                                      if x["add"]["UNHAPPINESS"] is not None else None} if r else None)
            x["window"] = L.floor_window(S.ring, L.num(st.get("landed_age_polled")) or 0.0,
                                         L.num(L.g(st, "post", "UNHAPPINESS")))
            out.append(x)
    return out


def fifth(eats):
    out = {}
    for lab, pin in FIFTH.items():
        x = next((e for e in eats if e["label"] == lab), None)
        if x is None:
            out[lab] = {"pin": pin, "measured": False}
            continue
        a = x["add"]
        out[lab] = {"pin": pin, "measured": True, "unhappy_add": a["UNHAPPINESS"], "bored_add": a["BOREDOM"],
                    "unhappy_minus_pin": a["UNHAPPINESS"] - pin if a["UNHAPPINESS"] is not None else None,
                    "bored_minus_pin": a["BOREDOM"] - pin if a["BOREDOM"] is not None else None,
                    "kernel_delta": x["kernel_delta"], "nominal_delta": x["nominal_delta"],
                    "unhappy_within": a["UNHAPPINESS"] is not None and abs(a["UNHAPPINESS"] - pin) <= FIFTH_TOL,
                    "bored_within": a["BOREDOM"] is not None and abs(a["BOREDOM"] - pin) <= FIFTH_TOL}
    return out


def projection(K, eats_per_day=1, days=PROJECT_DAYS, hours=(13.0,)):
    """The kernel's projection for a one-food diet: eats_per_day eats of one non-staple type a day at `hours`, w 1,
    from an empty record; per day the day's adds and the running sum of UNHAPPINESS (clamped at 100), with no vanilla
    term (offline arithmetic on K.monotony, never a measurement)."""
    nb, last = None, None
    run, out = 0.0, []
    hrs = list(hours)[:eats_per_day]
    for d in range(days):
        day_add = 0.0
        for h in hrs:
            age = 24.0 * d + h
            dl, c, n = L.kernel_delta(K, nb, last, age, False)
            nb, last = n, age
            day_add += dl
        run = min(100.0, run + day_add)
        out.append({"day": d, "add": day_add, "unhappy": run})
    return out


def climb(eats, sessions, K):
    """The tuning read (ruling T3-2): per arm the live UNHAPPINESS add per day and its running sum, the kernel's
    projection, the steady daily add, and the live day holds."""
    half = float(K.monotony.HALF_LIFE_H)
    steady = float(K.monotony.SLOPE) * (1.0 / (1.0 - 2.0 ** (-24.0 / half)) - 1.0)
    arms = {}
    for food, tag in ((L.MONO, "mono"), (L.STAPLE, "staple")):
        xs = sorted((e for e in eats if e["food"] == food), key=lambda e: e["day"] if e["day"] is not None else 99)
        run, rows = 0.0, []
        for e in xs:
            a = e["add"]["UNHAPPINESS"]
            run += a or 0.0
            rows.append({"day": e["day"], "label": e["label"], "add": a, "kernel_delta": e["kernel_delta"],
                         "nominal_delta": e["nominal_delta"], "running_sum": run})
        arms[tag] = rows
    holds = []
    for S in sessions:
        holds += [dict(h, session=S.pre) for h in (L.g(S.doc, "readings", "day_hold") or [])]
    p1 = projection(K, 1)
    p3 = projection(K, 3, hours=(8.0, 13.0, 20.0))
    first100 = lambda p: next((x["day"] for x in p if x["unhappy"] >= 100.0 - 1e-9), None)  # noqa: E731
    return {"arms": arms, "steady_daily_add": steady, "projection_one_a_day": p1, "projection_three_a_day": p3,
            "one_a_day_reaches_100_on_day": first100(p1), "three_a_day_reaches_100_on_day": first100(p3),
            "day_holds": holds,
            "note": "the running sum is the UNHAPPINESS a one-food diet carries from each arm's adds with no vanilla "
                    "term (the live day holds show whether one acted); the projections are offline arithmetic"}


def guard(sessions):
    return {S.pre: L.guard_reading(S.ring) for S in sessions}


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
            for k in ("fluids.na", "fluids.water", "fluids.naPlasma", "body.energyState"):
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = a.out or os.path.join(ART, "x33-grade-%s" % datetime.date.today().strftime("%Y%m%d"))
    os.makedirs(out, exist_ok=True)
    sessions = []
    for pre, doc in CHAIN:
        try:
            sessions.append(Sess(pre, doc))
        except SystemExit as e:
            print("skip %s: %s" % (pre, e))
    K = kernel()
    for S in sessions:
        with open(os.path.join(out, S.pre + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(S.summary(), fh, indent=1, sort_keys=True, default=str)
    eats = eat_table(sessions, K)
    ff = fifth(eats)
    row13 = {"eats": eats, "fifth": ff, "climb": climb(eats, sessions, K), "oracle_pins": ORACLE_PINS,
             "constants": {k: float(getattr(K.monotony, k)) for k in ("SLOPE", "CAP", "HALF_LIFE_H", "WINDOW_H",
                                                                       "STAPLE", "MEAL_KCAL")},
             "guard": guard(sessions)}
    rows = {"row13": row13, "drinking_sodium": drinking_sodium(sessions)}
    with open(os.path.join(out, "rows.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, sort_keys=True, default=str)
    nz = [e for e in eats if (e["kernel_delta"] or 0) > 0]
    verdicts = {
        "REPLAY_OK": {S.pre: S.diff.get("ok") for S in sessions},
        "FIFTH": {k: {"unhappy": v.get("unhappy_within"), "bored": v.get("bored_within")} for k, v in ff.items()},
        "ADDS_EQUAL_KERNEL": {e["label"]: (e["add"]["UNHAPPINESS"] is not None and e["kernel_delta"] is not None
                                           and abs(e["add"]["UNHAPPINESS"] - e["kernel_delta"]) <= L.ADD_TOL) for e in eats},
        "EQUAL_STATS": {e["label"]: (e["add_equal"] is not None and e["add_equal"] <= L.EQUAL_TOL) for e in eats},
        "CLIENT": {e["label"]: e["client_first_add"] is not None for e in nz},
        "FLOOR_NO_FALL": {e["label"]: e["window"].get("no_fall") for e in eats},
        "EXE_FALSE": {p: g["exe_true_rows"] == 0 and g["exe_present_rows"] > 0 and g["asleep_rows"] == 0
                      for p, g in row13["guard"].items()},
        "SODIUM_GRADE_MAX": rows["drinking_sodium"]["grade_max_chain"]}
    summ = {"tool_commit": _git("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
            "grade_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x33_grade.py"),
            "lib_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x33_monotony_lib.py"),
            "sessions": [S.pre for S in sessions], "verdicts": verdicts}
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summ, fh, indent=1, sort_keys=True, default=str)
    print(json.dumps(verdicts, indent=1, default=str))


if __name__ == "__main__":
    main()
