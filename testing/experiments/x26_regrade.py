"""x26_regrade -- the committed tool re-run over the six Plan 11f Task 4 meal runs (x261..x266): an ANALYSIS script, not
a driver (it boots nothing). Its output is a DERIVED artifact (a tool re-run, not a live run).

Why: tools/replay_live.py at the time of the runs had no sleep input and no auto-drink detector, so the runs' own
replay verdicts of x261, x262 and x266 (the sleep option, F-T4-1) and x263 (the unlogged auto-drink, F-T4-2) read
falsified. The tool now takes the live server's sleep option as a required input (sleep_allowed) and the opt-in
detect_autodrink; this script re-runs it at HEAD over each committed run with the live server's option
(SleepAllowed and SleepNeeded false, the fixture default and the profile x26-meals) and the detector on, and writes
one JSON per run plus a summary of every row's verdict.

    python testing/experiments/x26_regrade.py [--out testing/artifacts/x26-regrade-YYYYMMDD]

The inputs are each run's committed events.json (the logged events only), start.json, start-stats.json, player.json and
minute-ring pages; nothing of the run's own replay output is read except its diff, for the before/after line. The
driver verdicts are copied unchanged from the run's artifact (they are the driver's, graded at the run) and labelled so.
"""
import argparse
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, HERE)
import replay_live as RL  # noqa: E402
import x26_meals_lib as L  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
ARTIFACTS = ("meal-return", "snacks", "volume", "density", "liquid", "circadian")
PREFIXES = ("x261", "x262", "x263", "x264", "x265", "x266")
SLEEP_ALLOWED = False                  # the live server: SleepAllowed and SleepNeeded false (the fixture default)
FIELDS = ("fields", "classes", "ok")


def run_folders():
    out = []
    for pre in PREFIXES:
        hits = sorted(d for d in os.listdir(ART) if d.startswith(pre + "-"))
        if len(hits) != 1:
            raise SystemExit("expected one artifact folder for %s, found %r" % (pre, hits))
        out.append(os.path.join(ART, hits[0]))
    return out


def read(run, name):
    with open(os.path.join(run, name), encoding="utf-8") as fh:
        return json.load(fh)


def artifact_doc(run):
    name = next(f for f in os.listdir(run) if f.endswith(".json") and f.split(".")[0] in ARTIFACTS)
    return read(run, name)


class Ctx:
    """One run's committed inputs and the tool re-run helpers; every arm is the tool at HEAD with the live server sleep
    option, the detected auto-drinks added as events (detected once from the live ring and the logged events)."""

    def __init__(self, doc, rr, rp, events, start, stats, player):
        self.doc, self.rr, self.rp, self.events = doc, rr, rp, events
        self.start, self.stats, self.player = start, stats, player
        self.inj = RL.detect_autodrinks(rr, events)
        self.by = {e["label"]: e for e in doc["eats"] if e.get("ring_s") is not None}
        self.offset = None

    def arm(self, drop=(), add=(), nocirc=False):
        ev = [x for x in self.events if x.get("label") not in drop] + list(add) + self.inj
        ev.sort(key=lambda x: x["s"])
        orig = RL.ServerReplay
        if nocirc:
            class NoCirc(orig):
                def __init__(self, *a, **k):
                    super().__init__(*a, **k)
                    self.rt.execute("NutritionRevamp.kernel.satiety.circadian = function(h) return 1 end")
            RL.ServerReplay = NoCirc
        try:
            rows, be = RL.replay_live(self.rr, ev, self.start, paths=self.rp, user=L.USER, player=self.player,
                                      start_stats=self.stats, sleep_allowed=SLEEP_ALLOWED)
        finally:
            RL.ServerReplay = orig
        self.offset = be.R.offset
        return rows


def req(rows, age):
    return L.request_after(rows, age)


def r_x261(c, rows, requests):
    rr, by = c.rr, c.by
    out = {"requests": requests}
    f = by.get("F400")
    if f:
        held = {}
        for name, rs in (("live", rr), ("replay", rows)):
            first = next((r for r in rs if r["age"] > f["ring_age"] + 1e-12 and r.get("HUNGER") is not None
                          and r["HUNGER"] < 0.25), None)
            back = req(rs, f["ring_age"])
            held[name] = {"first_below_min": (first["age"] - f["ring_age"]) * 60 if first else None,
                          "return_min": back,
                          "held_min": back - (first["age"] - f["ring_age"]) * 60 if (first and back) else None}
        out["F400_held"] = held
    t = [by[k] for k in ("T217a", "T217b", "T217c") if k in by]
    if t:
        one = c.arm(("T217a", "T217b", "T217c"), [{"s": t[0]["ring_s"], "kind": "eat", "food": "TKX.Mixed650"}])
        same = c.arm(("T217b", "T217c"), [{"s": t[0]["ring_s"], "kind": "eat", "food": "TKX.Mixed217"}] * 2)
        a0 = t[0]["ring_age"]
        out["T217_arms"] = {"three_spread_live": req(rr, a0), "three_spread_replay": req(rows, a0),
                            "one650_arm": req(one, a0), "three_same_row_arm": req(same, a0)}
    return out


def r_x262(c, rows, requests):
    out = {"requests": requests, "snack_arms": {}}
    for k in ("P", "C", "F"):
        lunch, snack = c.by.get(k + "650"), c.by.get("S" + k)
        if not lunch or not snack:
            continue
        r = {}
        for alt in ("none", "P", "C", "F"):
            add = [] if alt == "none" else [{"s": snack["ring_s"], "kind": "eat", "food": "TKX.Snack" + alt}]
            rs = c.arm(("S" + k,), add)
            t = req(rs, snack["ring_age"])
            r[alt] = {"dinner_from_lunch": t + (snack["ring_age"] - lunch["ring_age"]) * 60 if t else None,
                      "mean180": L.mean_over(rs, snack["ring_age"], 180)}
        base = r["none"]["dinner_from_lunch"]
        later = [e["ring_age"] for e in c.doc["eats"] if e.get("landed") and e.get("ring_age") is not None
                 and e["ring_age"] > snack["ring_age"] + 1e-9]
        cap = (min(later) - lunch["ring_age"]) * 60 if later else None     # the next live eat ends the arm
        if base is None or any(r[x]["dinner_from_lunch"] is None for x in ("P", "C", "F")) or (
                cap is not None and any(r[x]["dinner_from_lunch"] > cap for x in ("none", "P", "C", "F"))):
            out["snack_arms"][k] = {"censored": True, "next_live_eat_min_from_lunch": cap, "none": base,
                                    "dinner_from_lunch": {x: r[x]["dinner_from_lunch"] for x in r},
                                    "lunch_age": lunch["ring_age"]}
            continue
        dl = {x: r[x]["dinner_from_lunch"] - base for x in ("P", "C", "F")}
        out["snack_arms"][k] = {
            "censored": False, "lunch_tod": math.fmod(lunch["ring_age"] + c.offset, 24), "lunch_age": lunch["ring_age"],
            "snack_after_lunch_min": (snack["ring_age"] - lunch["ring_age"]) * 60, "none": base, "delays": dl,
            "p_minus_c": dl["P"] - dl["C"], "p_minus_f": dl["P"] - dl["F"],
            "protein_vs_carb_mean180": r["C"]["mean180"] - r["P"]["mean180"]}
    return out


def r_x263(c, rows, requests):
    rr, by = c.rr, c.by
    out = {"requests": requests, "injected": c.inj}
    first = by.get("CAS")
    drops = ("CAS", "SOUP", "CW", "CW_water") + tuple("W%d" % n for n in range(100, 700, 100))
    if first:
        s0, a0 = first["ring_s"], first["ring_age"]
        w = [x for x in c.events if x.get("label") == "CW_water"]
        shift = (w[0]["s"] - by["CW"]["ring_s"]) if (w and by.get("CW")) else 2
        arms = {}
        for name, add in (("casserole", [{"s": s0, "kind": "eat", "food": "TKX.Casserole"}]),
                          ("soup", [{"s": s0, "kind": "eat", "food": "TKX.Soup"}]),
                          ("casserole_water", [{"s": s0, "kind": "eat", "food": "TKX.Casserole"},
                                               {"s": s0 + max(0, shift), "kind": "drink", "fluid": "Water",
                                                "litres": 0.356}])):
            h = L.at_minute(c.arm(drops, add), a0, 17)
            arms[name] = {"minute17_hunger": h["value"] if h else None,
                          "kJ": KJ_PER_HUNGER * h["value"] if h else None}
        out["rolls_arms"] = {"kJ_per_hunger": KJ_PER_HUNGER, "arms": arms, "at_row_s": s0}
    m17 = {}
    for lab in ("CAS", "SOUP", "CW"):
        e = by.get(lab)
        if e:
            lv, sp = L.at_minute(rr, e["ring_age"], 17), L.at_minute(rows, e["ring_age"], 17)
            m17[lab] = {"live": lv and lv["value"], "replay": sp and sp["value"],
                        "diff": (lv["value"] - sp["value"]) if (lv and sp) else None}
    out["minute17"] = m17
    w0 = by.get("W100")
    if w0:
        xs = list(range(100, 700, 100))
        ys = []
        for n in xs:
            h = L.at_minute(c.arm(drops, [{"s": w0["ring_s"], "kind": "eat", "food": "TKX.Water%d" % n}]),
                            w0["ring_age"], 1)
            ys.append(h["value"] if h else None)
        r2 = None
        if all(y is not None for y in ys):
            mx, my = sum(xs) / 6, sum(ys) / 6
            sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            r2 = sxy * sxy / (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
        m1 = {}
        for n in xs:
            e = by.get("W%d" % n)
            if e:
                lv, sp = L.at_minute(rr, e["ring_age"], 1), L.at_minute(rows, e["ring_age"], 1)
                m1["W%d" % n] = {"live": lv and lv["value"], "replay": sp and sp["value"],
                                 "diff": (lv["value"] - sp["value"]) if (lv and sp) else None}
        out["water_arms"] = {"grams": xs, "minute1_hunger": ys, "r2": r2, "at_row_s": w0["ring_s"]}
        out["minute1"] = m1
    return out


def r_x264(c, rows, requests):
    rr, by = c.rr, c.by
    out = {"requests": requests}
    drops = ("MARC", "MSOUP", "DLO", "DHI", "MARC_water")
    m = by.get("MARC")
    if m:
        w = [x for x in c.events if x.get("label") == "MARC_water"]
        shift = (w[0]["s"] - m["ring_s"]) if w else 2
        solid = c.arm(drops, [{"s": m["ring_s"], "kind": "eat", "food": "TKX.Marc"},
                              {"s": m["ring_s"] + max(0, shift), "kind": "drink", "fluid": "Water", "litres": 0.3}])
        soup = c.arm(drops, [{"s": m["ring_s"], "kind": "eat", "food": "TKX.MarcSoup"}])
        a = L.mean_over(soup, m["ring_age"], 180)
        b = L.mean_over(solid, m["ring_age"], 180)
        out["marc_arms"] = {"at_row_s": m["ring_s"], "soup_mean180": a, "solid_water_mean180": b,
                            "soup_minus_solid_water": a - b if (a is not None and b is not None) else None,
                            "soup_never_higher": all(
                                (x["HUNGER"] <= y["HUNGER"] + 1e-12) for x, y in zip(soup, solid)
                                if x["age"] > m["ring_age"] and x["age"] <= m["ring_age"] + 3
                                and x.get("HUNGER") is not None and y.get("HUNGER") is not None)}
    dd = by.get("DLO")
    if dd:
        lo = c.arm(drops, [{"s": dd["ring_s"], "kind": "eat", "food": "TKX.Dense400Lo"}])
        hi = c.arm(drops, [{"s": dd["ring_s"], "kind": "eat", "food": "TKX.Dense400Hi"}])
        out["dense_arms"] = {"at_row_s": dd["ring_s"], "lo_mean180": L.mean_over(lo, dd["ring_age"], 180),
                             "hi_mean180": L.mean_over(hi, dd["ring_age"], 180),
                             "lo_req": req(lo, dd["ring_age"]), "hi_req": req(hi, dd["ring_age"])}
    order = [(lab, by[lab]) for lab in ("MARC", "MSOUP", "DLO", "DHI") if lab in by]
    means = {}
    for i, (lab, e) in enumerate(order):
        nxt = order[i + 1][1]["ring_age"] if i + 1 < len(order) else None
        mins = 180.0 if nxt is None else min(180.0, (nxt - e["ring_age"]) * 60)
        means[lab] = {"minutes_used": mins, "truncated_at_next_landing": mins < 180.0,
                      "live": L.mean_over(rr, e["ring_age"], mins), "replay": L.mean_over(rows, e["ring_age"], mins),
                      "live_180": L.mean_over(rr, e["ring_age"], 180), "replay_180": L.mean_over(rows, e["ring_age"], 180)}
    out["means"] = {"note": "the mean is read over the minutes_used after the landing: a window is cut at the next "
                            "eat's landing (MSOUP's 180 min run past DLO's landing at s424); live_180 and "
                            "replay_180 are the full 180 min, contaminated for a truncated arm",
                    "arms": means}
    return out


def r_x265(c, rows, requests):
    rr = c.rr
    out = {"requests": requests}
    milk = sorted(x["s"] for x in c.events if x.get("label") == "MILK")
    solid = c.by.get("SOLID")
    ring_by = {r["s"]: r for r in rr}
    if milk and solid:
        a_m, a_s = ring_by[milk[0]]["age"], solid["ring_age"]
        out["anchored"] = {"MILK": {"live": req(rr, a_m), "replay": req(rows, a_m)},
                           "SOLID": {"live": req(rr, a_s), "replay": req(rows, a_s)}}
        shift = solid["ring_s"] - milk[0]
        mev = [x for x in c.events if x.get("label") == "MILK"]
        sw = c.arm(("MILK", "SOLID"), [{"s": milk[0], "kind": "eat", "food": "TKX.MilkSolid"}] +
                   [dict(x, s=x["s"] + shift) for x in mev])
        sol_at1, milk_at2 = req(sw, a_m), req(sw, a_s)
        out["swap_arms"] = {"solid_at_slot1": sol_at1, "milk_at_slot2": milk_at2,
                            "liquid_over_solid": {"slot1": out["anchored"]["MILK"]["replay"] / sol_at1
                                                  if sol_at1 else None,
                                                  "slot2": milk_at2 / out["anchored"]["SOLID"]["replay"]
                                                  if (milk_at2 and out["anchored"]["SOLID"]["replay"]) else None}}
    rep_by = {q["s"]: q for q in rows}
    worst, n, at = 0.0, 0, None
    for r in rr:
        q = rep_by.get(r["s"])
        if q is None or q.get("between") or q.get("suspect") or q.get("offline"):
            continue
        if q.get("stomach.liquid") is None or r.get("stomach.liquid") is None:
            continue
        n += 1
        dv = abs(r["stomach.liquid"] - q["stomach.liquid"])
        if dv > worst:
            worst, at = dv, r["s"]
    out["liquid_lane"] = {"rows_compared": n, "max_abs_g": worst, "at_s": at}
    return out


def r_x266(c, rows, requests):
    rr, by = c.rr, c.by
    out = {"requests": requests}
    nc = c.arm(nocirc=True)
    with open(os.path.join(REPO, "mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Satiety.lua"),
              encoding="utf-8") as fh:
        src = fh.read()
    amp = float(re.search(r"K\.satiety\.CIRCADIAN_A\s*=\s*([0-9.]+)", src).group(1))
    peak = float(re.search(r"K\.satiety\.CIRCADIAN_PEAK_H\s*=\s*([0-9.]+)", src).group(1))
    ring_by = {r["s"]: r for r in rr}
    prev = {rr[i]["s"]: rr[i - 1]["age"] for i in range(1, len(rr))}
    worst, n, over = 0.0, 0, 0
    for q in nc:
        s = q["s"]
        if q.get("between") or q.get("suspect") or q.get("offline") or s not in ring_by or s not in prev:
            continue
        hn, hl = q.get("HUNGER"), ring_by[s].get("HUNGER")
        if hn is None or hl is None or hn <= 0 or hn * (1 + amp) >= 0.69 - 1e-9 or hl >= 0.69 - 1e-9:
            continue
        tod = math.fmod(prev[s] + c.offset, 24)
        exp = 1 + amp * math.cos(2 * math.pi * (tod - peak) / 24)
        dv = abs((hl / hn) / exp - 1)
        n += 1
        worst = max(worst, dv)
        over += dv > 0.01
    out["factor"] = {"A": amp, "PEAK_H": peak, "rows": n, "max_rel_error": worst, "over_1pct": over,
                     "definition": "live HUNGER over the no-circadian replay HUNGER, against 1 + A cos(2 pi (tod - "
                                   "PEAK_H) / 24) at the writing drain hour"}
    es_by = {r["s"]: r for r in rr}
    meals = {}
    for lab, e in by.items():
        a0 = e.get("ring_age")
        if a0 is None or lab.startswith("G") or not e.get("landed"):
            continue
        row = es_by.get(e["ring_s"])
        meals[lab] = {"landing_s": e["ring_s"], "landing_age": a0, "tod": math.fmod(a0 + c.offset, 24),
                      "es_before": row.get("body.energyState") if row else None,
                      "live_return_min": req(rr, a0), "replay_return_min": req(rows, a0),
                      "nofactor_return_min": req(nc, a0)}
    out["fixed_meals"] = meals
    wakes = {}
    for lab, w in ((c.doc.get("readings") or {}).get("wakes") or {}).items():
        age = w.get("age") if isinstance(w, dict) else None
        if age is None:
            continue
        lv, rp_ = L.at_minute(rr, age, 0), L.at_minute(rows, age, 0)
        wakes.setdefault(lab, {}).update({"age": age, "live_hunger": lv and lv["value"],
                                          "replay_hunger": rp_ and rp_["value"]})
    out["wakes"] = wakes
    return out


READERS = {"x261": r_x261, "x262": r_x262, "x263": r_x263, "x264": r_x264, "x265": r_x265, "x266": r_x266}
KJ_PER_HUNGER = 10878.4


def regrade(run):
    doc = artifact_doc(run)
    files = doc["replay"]["inputs"]["ring"]
    events, start = read(run, "events.json"), read(run, "start.json")
    stats, player = read(run, "start-stats.json"), read(run, "player.json")
    old = read(run, "replay.json")
    rr, rp = RL.load_ring([os.path.join(run, f) for f in files])
    res = {"run": doc["run_id"], "kind": "tool re-run at HEAD (a derived artifact, not a live run)",
           "flags": {"sleep_allowed": SLEEP_ALLOWED, "detect_autodrink": True}, "ring_files": files,
           "ring_rows": len(rr)}
    t0 = time.time()
    arms = {}
    for name, detect in (("sleep_only", False), ("sleep_and_autodrink", True)):
        rows, be = RL.replay_live(rr, events, start, paths=rp, user=L.USER, player=player, start_stats=stats,
                                  sleep_allowed=SLEEP_ALLOWED, detect_autodrink=detect)
        d = RL.diff(rows, rr)
        dx = RL.diff(rows, rr, L.TOL_EXTRA)
        arms[name] = {"diff": {k: d.get(k) for k in FIELDS}, "findings": d["findings"][:10],
                      "diff_extra": {k: dx.get(k) for k in ("fields", "ok")}, "injected": be.injected,
                      "offset": be.R.offset}
        if detect:
            reqs = {}
            for e in doc["eats"]:
                a0 = e.get("ring_age")
                if not e.get("landed") or a0 is None:
                    continue
                lv, rp_ = L.request_after(rr, a0), L.request_after(rows, a0)
                tol = max(3.0, 0.02 * rp_) if rp_ is not None else None
                reqs[e["label"]] = {"landing_s": e.get("ring_s"), "landing_age": a0, "live": lv, "replay": rp_,
                                    "tol": tol, "live_minus_replay": (lv - rp_) if (lv is not None and rp_ is not None)
                                    else None, "ok": (abs(lv - rp_) <= tol) if (lv is not None and rp_ is not None)
                                    else None}
            res["requests"] = reqs
    ctx = Ctx(doc, rr, rp, events, start, stats, player)
    res["injected_events"] = ctx.inj
    res["readings"] = READERS[doc["run_id"][:4]](ctx, rows, res["requests"])
    res["seconds"] = round(time.time() - t0, 2)
    res["regrade"] = arms["sleep_and_autodrink"]
    res["sleep_only"] = arms["sleep_only"]
    res["run_time_tool_diff"] = {k: old["diff"].get(k) for k in FIELDS}
    res["driver_verdicts"] = {k: v.get("verdict") for k, v in (doc.get("verdicts") or {}).items()}
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ART, "x26-regrade-" + time.strftime("%Y%m%d")))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    summary = {"kind": "derived: replay_live at HEAD over the committed runs, not a live run",
               "flags": {"sleep_allowed": SLEEP_ALLOWED, "detect_autodrink": True}, "runs": {}}
    for run in run_folders():
        res = regrade(run)
        name = res["run"].split("-")[0] + ".json"
        with open(os.path.join(a.out, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(res, indent=1, sort_keys=True) + "\n")
        g = res["regrade"]["diff"]
        summary["runs"][res["run"]] = {
            "file": name, "regrade_ok": g["ok"], "sleep_only_ok": res["sleep_only"]["diff"]["ok"],
            "run_time_tool_ok": res["run_time_tool_diff"]["ok"],
            "injected": [{"s": x["s"], "litres": x["litres"]} for x in res["regrade"]["injected"]],
            "HUNGER_max": (g["fields"].get("HUNGER") or {}).get("max"),
            "es_max": (g["fields"].get("body.energyState") or {}).get("max"),
            "requests": {k: {"live": v["live"], "replay": v["replay"], "ok": v["ok"]}
                         for k, v in res.get("requests", {}).items()},
            "driver_verdicts": res["driver_verdicts"]}
        print("%s regrade %s (sleep-only %s, run-time tool %s) injected %d"
              % (res["run"], "ok" if g["ok"] else "FAIL", res["sleep_only"]["diff"]["ok"],
                 res["run_time_tool_diff"]["ok"], len(res["regrade"]["injected"])))
    with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return 0 if all(r["regrade_ok"] for r in summary["runs"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
