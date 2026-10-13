"""x36_grade -- the committed grade of Plan 11g Task 8 (the live checks of the final satiety and deficit model): an
ANALYSIS script, not a driver (it boots nothing). Written and committed before the first boot of the runs it grades;
its output is a DERIVED artifact folder (ruling T4-3: every number a row may cite is emitted by a committed script).

    python testing/experiments/x36_grade.py [--out testing/artifacts/x36-grade-YYYYMMDD]

The inputs are each session's artifact folder testing/artifacts/x36N-*/ (x361 course, x362 surplus, x363 drink, x364
fast; a session that did not run is skipped, named): the driver's document, events.json, start.json, start-stats.json,
player.json and the minute-ring pages. The tool is tools/replay_live.py at HEAD (sleep_allowed false, the ring's own
activity), the readings x36_gut_lib's pure functions.

Every session: the replay of live re-run; the tool's diff (DEFAULT_TOL: HUNGER 0.002, es 0.005, L 0.5 %, the 11f
tolerances) and x36_gut_lib.diff_floor under TOL_GRADE (M within 0.5 %, floor 1; the physical and the food fill within
0.002; the buffer kcal within 0.5 %, floor 0.5); the replay's rows equal to the session's committed replay.json rows on
HUNGER (a determinism check of the tool at HEAD).
x361: per course (C650, C400) course_reading from its landing row to the course's end: the graded diff, the live and
  replay request minutes, the nadir, the 15-minute series of HUNGER, M, the fills and the buffer; the study distance as
  readings: C650's request against the oracle anchor 240-300 min (S1247, S1248; test_satiety_meal_studies.py
  MEAL650_MIN, the hard replays' band 240/1.1-300x1.1) and C400's held-below minutes against >= 180
  (BREAKFAST_HOLD_MIN; this one at a request, not fasted at 08:00).
x362: the day (07:00-22:00 day 1) live and replay: the time-weighted mean HUNGER and the eight-point mean (x362's
  karl_points); the REST arm (x36_gut_lib.rest_arm_events: the three surplus meals' landings given maintenance portions
  of the session's maint_kcal / 3, on the live clock and record, ruling 11f-3) and its day; the change against REST in %
  (replay against the arm, and live against the arm) for both means, against Karl's BAL -55 % (S1325) and S1892's band
  -64 to -46 (a reading: Karl's arm also worked about 20 MJ a day, this body rested); es at 22:00 day 1 on each.
x363: the water's fills (drink_reading), the milk's, the courses; the swap arms (x265's form: the solid at the milk's
  first sip row, the milk's sips moved to the solid's landing row, every other event as live) and the request minutes
  at each slot; the liquid-over-solid interval ratio at each slot.
x364: the server's held level on the ring (ring_levels), the energy pairs re-graded (energy_pairs_grade), the es
  crossing of level 1 live and on the replay, and the fast's hours at the crossing.
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
import x36_gut_lib as L  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
DOCS = {"x361": "course.json", "x362": "surplus.json", "x363": "drink.json", "x364": "fast.json"}
MEAL650_MIN = (240.0, 300.0)       # S1247, S1248 (test_satiety_meal_studies.py MEAL650_MIN)
MEAL_TOL = 1.1                     # the hard replays' tolerance (ruling 11c-30; test_satiety_meal_studies.py TOL)
BREAKFAST_HOLD_MIN = 180.0         # test_satiety_meal_studies.py BREAKFAST_HOLD_MIN
LEVEL1 = 1.10                      # NR_Kernel_View.lua K.view.ENERGY_AT[1]


def _git(*a):
    import subprocess
    try:
        return subprocess.run(["git"] + list(a), cwd=REPO, capture_output=True, text=True).stdout.strip()
    except OSError:
        return None


def folder(pre):
    hits = sorted(d for d in os.listdir(ART) if d.startswith(pre + "-") and os.path.isdir(os.path.join(ART, d)))
    if not hits:
        return None
    if len(hits) != 1:
        raise SystemExit("expected one artifact folder for %s, found %r" % (pre, hits))
    return os.path.join(ART, hits[0])


def read(run, name):
    with open(os.path.join(run, name), encoding="utf-8") as fh:
        return json.load(fh)


class Sess:
    """One session's committed inputs and its replay re-run at HEAD."""

    def __init__(self, pre, run_dir=None):
        self.pre = pre
        self.dir = run_dir or folder(pre)
        self.doc = read(self.dir, DOCS[pre])
        files = [f for f in (L.g(self.doc, "verdicts", "RING", "observed", "files") or []) if f]
        self.ring, self.rpaths = (RL.load_ring([os.path.join(self.dir, f) for f in files]) if files else ([], []))
        self.ring = [r for r in self.ring if r.get("age") is not None]
        self.events = read(self.dir, "events.json")
        self.start = read(self.dir, "start.json")
        self.stats = read(self.dir, "start-stats.json")
        self.player = read(self.dir, "player.json")
        self.rows = self.replay(self.events)
        self.diff = RL.diff(self.rows, self.ring)
        self.grade = L.diff_floor(self.rows, self.ring)
        self.det = self.determinism()

    def replay(self, events):
        rows, _ = RL.replay_live(self.ring, events, self.start, paths=self.rpaths, user=L.USER, player=self.player,
                                 start_stats=self.stats, sleep_allowed=False)
        return rows

    def determinism(self):
        p = os.path.join(self.dir, "replay.json")
        if not os.path.isfile(p):
            return {"compared": 0, "note": "no replay.json"}
        old = {r["s"]: r for r in read(self.dir, "replay.json").get("rows") or []}
        n = mx = 0
        for r in self.rows:
            o = old.get(r["s"])
            if o is None or L.num(o.get("HUNGER")) is None or L.num(r.get("HUNGER")) is None:
                continue
            n += 1
            mx = max(mx, abs(o["HUNGER"] - r["HUNGER"]))
        return {"compared": n, "max_abs_HUNGER": mx}

    def summary(self):
        return {"run": os.path.basename(self.dir), "rows": len(self.ring), "events": len(self.events),
                "diff": {k: self.diff.get(k) for k in ("fields", "classes", "ok")} |
                        {"findings_n": len(self.diff.get("findings", [])), "findings": self.diff.get("findings", [])[:20]},
                "grade": self.grade, "determinism": self.det}


def eat_rows(doc, prefix):
    return [e for e in doc.get("eats") or [] if str(e.get("label", "")).startswith(prefix) and e.get("ring_s") is not None]


def grade_x361(S):
    out = {}
    by_lab = {e["label"]: e for e in S.doc.get("eats") or []}
    for c in S.doc.get("courses") or []:
        e = by_lab.get(c["label"]) or {}
        a0, a1 = e.get("ring_age"), c.get("end_age")
        if a0 is None or a1 is None:
            out[c["label"]] = {"error": "no landing row or no course end"}
            continue
        cr = L.course_reading(S.ring, S.rows, a0, a1)
        cr["landing_s"], cr["food"], cr["capped"] = e.get("ring_s"), e.get("food"), c.get("capped")
        out[c["label"]] = cr
    rd = {}
    c650 = out.get("C650") or {}
    lv = L.g(c650, "request", "live_min")
    rd["C650_request_vs_anchor"] = {"live_min": lv, "replay_min": L.g(c650, "request", "replay_min"),
                                    "anchor": list(MEAL650_MIN), "band": [MEAL650_MIN[0] / MEAL_TOL,
                                                                          MEAL650_MIN[1] * MEAL_TOL],
                                    "dist_to_anchor_mid": (lv - sum(MEAL650_MIN) / 2) if lv is not None else None,
                                    "inside_band": (MEAL650_MIN[0] / MEAL_TOL <= lv <= MEAL650_MIN[1] * MEAL_TOL)
                                    if lv is not None else None}
    c400 = out.get("C400") or {}
    lv4 = L.g(c400, "request", "live_min")
    rd["C400_held_vs_180"] = {"live_min": lv4, "replay_min": L.g(c400, "request", "replay_min"),
                              "anchor_min": BREAKFAST_HOLD_MIN,
                              "dist": (lv4 - BREAKFAST_HOLD_MIN) if lv4 is not None else None,
                              "note": "at a request, not fasted at 08:00: a reading"}
    return {"courses": out, "readings": rd}


def karl_points(S):
    import x362_surplus as D
    eats = S.doc.get("eats") or []
    return D.karl_points(S.ring, eats)


def grade_x362(S):
    import x362_surplus as D
    ages, notes = karl_points(S)
    day = {"live": L.day_reading(S.ring, D.DAY[0], D.DAY[1], ages),
           "replay": L.day_reading(S.rows, D.DAY[0], D.DAY[1], ages)}
    maint = L.num(L.g(S.doc, "readings", "maint_kcal"))
    out = {"ages": ages, "notes": notes, "day": day, "maint_kcal": maint}
    if maint is None:
        out["rest"] = {"error": "no maint_kcal in the document"}
        return out
    ev, meals = L.rest_arm_events(S.events, S.doc.get("eats") or [], set(D.SURPLUS), maint / 3.0)
    rest_rows = S.replay(ev)
    rest = L.day_reading(rest_rows, D.DAY[0], D.DAY[1], ages)

    def pct(a, b):
        return 100.0 * (a / b - 1.0) if (a is not None and b not in (None, 0)) else None
    es = {}
    for k, rows in (("live", S.ring), ("replay", S.rows), ("rest", rest_rows)):
        r = L.row_at(rows, D.DAY[1])
        es[k] = r.get("body.energyState") if r else None
    out["rest"] = {"meals": meals, "day": rest, "es_at_22": es,
                   "karl": {"study_bal": L.KARL_BAL, "band": list(L.KARL_BAND),
                            "replay_vs_rest_mean": pct(day["replay"]["mean"], rest["mean"]),
                            "replay_vs_rest_points": pct(day["replay"]["points_mean"], rest["points_mean"]),
                            "live_vs_rest_mean": pct(day["live"]["mean"], rest["mean"]),
                            "live_vs_rest_points": pct(day["live"]["points_mean"], rest["points_mean"])}}
    k = out["rest"]["karl"]
    for key in ("replay_vs_rest_mean", "replay_vs_rest_points", "live_vs_rest_mean", "live_vs_rest_points"):
        v = k[key]
        k[key + "_dist"] = (v - L.KARL_BAL) if v is not None else None
        k[key + "_in_band"] = (L.KARL_BAND[0] <= v <= L.KARL_BAND[1]) if v is not None else None
    return out


def grade_x363(S):
    by = {r["s"]: r for r in S.ring}
    sips = {d["label"]: list(d.get("ring_s") or []) for d in S.doc.get("drinks") or []}
    w, m = sips.get("W500") or [], sips.get("MILK") or []
    m0 = min(m) if m else None
    a_m0 = by[m0]["age"] if m0 in by else None
    out = {"W500": L.drink_reading(S.ring, S.rows, w, a_m0 if a_m0 is not None else S.ring[-1]["age"]),
           "MILK": L.drink_reading(S.ring, S.rows, m, (a_m0 or 0.0) + 1.0)}
    solid = next((e for e in S.doc.get("eats") or [] if e.get("label") == "SOLID" and e.get("ring_s") is not None), None)
    courses = {}
    if a_m0 is not None and solid is not None:
        courses["MILK"] = L.course_reading(S.ring, S.rows, a_m0, solid["ring_age"] - 1e-6)
    if solid is not None:
        courses["SOLID"] = L.course_reading(S.ring, S.rows, solid["ring_age"], S.ring[-1]["age"])
    out["courses"] = courses
    if m and solid is not None:
        milk_ev = [x for x in S.events if x.get("label") == "MILK"]
        base = [x for x in S.events if x.get("label") not in ("MILK", "SOLID")]
        shift = solid["ring_s"] - m0
        swapped = base + [{"s": m0, "kind": "eat", "food": L.MILKSOLID, "label": "SOLID_at_milk"}] + \
            [dict(x, s=x["s"] + shift, label="MILK_at_solid") for x in milk_ev]
        swapped.sort(key=lambda x: x["s"])
        rows_sw = S.replay(swapped)
        a_s = solid["ring_age"]
        as_live = {"milk_at_slot1": L.request_after(S.rows, a_m0), "solid_at_slot2": L.request_after(S.rows, a_s)}
        swap = {"solid_at_slot1": L.request_after(rows_sw, a_m0), "milk_at_slot2": L.request_after(rows_sw, a_s)}
        out["swap_arms"] = {"kind": "replay arms (ruling 11f-3): the milk's sips moved to the solid's landing row (as "
                                    "many rows on) and the solid put at the milk's first sip row",
                            "as_live": as_live, "swapped": swap,
                            "liquid_over_solid_slot1": (as_live["milk_at_slot1"] / swap["solid_at_slot1"])
                            if (as_live["milk_at_slot1"] and swap["solid_at_slot1"]) else None,
                            "liquid_over_solid_slot2": (swap["milk_at_slot2"] / as_live["solid_at_slot2"])
                            if (swap["milk_at_slot2"] and as_live["solid_at_slot2"]) else None}
    return out


def grade_x364(S):
    rl = L.ring_levels(S.ring)
    start = L.g(S.doc, "phases", "X", "start_age")
    first1 = next((c for c in rl["changes"] if c["to"] >= 1), None)

    def cross(rows):
        r = next((x for x in rows if L.num(x.get("body.energyState")) is not None
                  and x["body.energyState"] >= LEVEL1), None)
        return r.get("age") if r else None
    lc, rc = cross(S.ring), cross(S.rows)
    return {"ring_levels": rl, "level1_change": first1,
            "fast_h_at_level1": (first1["age"] - start) if (first1 and start is not None) else None,
            "es_cross_live_age": lc, "es_cross_replay_age": rc,
            "es_cross_diff_min": ((lc - rc) * 60) if (lc is not None and rc is not None) else None,
            "es_end": S.ring[-1].get("body.energyState") if S.ring else None,
            "energy_pairs": L.energy_pairs_grade(S.doc.get("energy_pairs") or [])}


GRADERS = {"x361": grade_x361, "x362": grade_x362, "x363": grade_x363, "x364": grade_x364}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ART, "x36-grade-" + datetime.date.today().strftime("%Y%m%d")))
    a = ap.parse_args(argv)
    doc = {"script": "testing/experiments/x36_grade.py", "commit": _git("rev-parse", "--short", "HEAD"),
           "replay_tool_commit": _git("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
           "lib_commit": _git("log", "-1", "--format=%h", "--", "testing/experiments/x36_gut_lib.py"),
           "tol_default": {k: list(v) for k, v in RL.DEFAULT_TOL.items()},
           "tol_grade": {k: list(v) for k, v in L.TOL_GRADE.items()}, "sessions": {}, "skipped": []}
    for pre in DOCS:
        if folder(pre) is None:
            doc["skipped"].append(pre)
            continue
        S = Sess(pre)
        doc["sessions"][pre] = S.summary() | {"readings": GRADERS[pre](S)}
    os.makedirs(a.out, exist_ok=True)
    p = os.path.join(a.out, "grade.json")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n")
    print(p)
    short = {k: {"diff_ok": v["diff"]["ok"], "grade_ok": v["grade"]["ok"]} for k, v in doc["sessions"].items()}
    print(json.dumps(short, indent=1))


if __name__ == "__main__":
    main()
