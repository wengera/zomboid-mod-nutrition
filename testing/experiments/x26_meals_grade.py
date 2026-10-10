"""x26_meals_grade -- the offline grader of the Plan 11f Task 4 meal runs (x261..x266): an ANALYSIS script, not a
driver (it boots nothing, and it may change after the runs; every driver is frozen).

Why it exists (finding F-T4-1, x261): tools/replay_live.py's host has no getServerOptions, so the mod's
NUT.readSleepOptions reads sleep as allowed (NR_Server_Nutrients.lua: an unreadable option reads true), while the live
server ran SleepAllowed/SleepNeeded false (the fixture's default; the profile sets neither), so the live record's sleep
state is frozen at rested (#2947, #2961) and the replay's is not: at the acute record's 24 h window close the replay
books the stand-in's waking hours as debt (debtH 7.5 in x261) and its sleep factor lifts HUNGER by 1.18 from then on.
The drivers' own replay (the tool as committed) is kept as graded; this script adds the SUPPLEMENTARY replay with the
live server's option mirrored -- NutritionRevamp.server.nutrients.sleepDisabled = true set in the replay host after it
is built, the value the live server's readSleepOptions computed -- and labels every number from it as such. Nothing in
the tool or the mod is changed.

    python testing/experiments/x26_meals_grade.py testing/artifacts/<run-id> [--json OUT]
prints, for the run: the whole-session diff of both replays, the per-eat request minutes (live, tool replay,
supplementary replay), and the driver's replay arms re-run on the supplementary replay.
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, HERE)
import replay_live as RL  # noqa: E402
import x26_meals_lib as L  # noqa: E402


class SleepOff(RL.ServerReplay):
    """The live server's sleep option mirrored: sleep disabled (SleepAllowed/SleepNeeded false)."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rt.execute("NutritionRevamp.server.nutrients.sleepDisabled = true")


class SleepOffNoCirc(SleepOff):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rt.execute("NutritionRevamp.kernel.satiety.circadian = function(h) return 1 end")


def load(run):
    art = [f for f in os.listdir(run) if f.endswith(".json") and f.split(".")[0] in
           ("meal-return", "snacks", "volume", "density", "liquid", "circadian")][0]
    with open(os.path.join(run, art), encoding="utf-8") as fh:
        doc = json.load(fh)
    files = doc["replay"]["inputs"]["ring"]
    rd = {}
    for name in ("events", "start", "start-stats", "player"):
        with open(os.path.join(run, name + ".json"), encoding="utf-8") as fh:
            rd[name] = json.load(fh)
    rr, rp = RL.load_ring([os.path.join(run, f) for f in files])
    return doc, rr, rp, rd


def replay(rr, rp, rd, events=None, cls=SleepOff):
    orig = RL.ServerReplay
    RL.ServerReplay = cls
    try:
        rows, be = RL.replay_live(rr, rd["events"] if events is None else events, rd["start"], paths=rp,
                                  user="admin", player=rd["player"], start_stats=rd["start-stats"])
    finally:
        RL.ServerReplay = orig
    return rows, be


def requests(doc, ring, tool_rows, sup_rows):
    out = {}
    for e in doc["eats"]:
        a0 = e.get("ring_age")
        if not e.get("landed") or a0 is None:
            continue
        lv, tr, sp = L.request_after(ring, a0), L.request_after(tool_rows, a0), L.request_after(sup_rows, a0)
        tol = max(3.0, 0.02 * sp) if sp is not None else None
        out[e["label"]] = {"landing_s": e.get("ring_s"), "landing_age": a0, "live": lv, "tool_replay": tr,
                           "sup_replay": sp, "live_minus_sup": (lv - sp) if (lv is not None and sp is not None) else None,
                           "tol": tol, "ok_sup": (abs(lv - sp) <= tol) if (lv is not None and sp is not None) else None}
    return out


def arm(rr, rp, rd, drop, add):
    ev = [x for x in rd["events"] if x.get("label") not in drop] + add
    ev.sort(key=lambda x: x["s"])
    return replay(rr, rp, rd, ev)[0]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    doc, rr, rp, rd = load(a.run)
    with open(os.path.join(a.run, "replay.json"), encoding="utf-8") as fh:
        tool = json.load(fh)
    sup, be = replay(rr, rp, rd)
    d = RL.diff(sup, rr)
    dx = RL.diff(sup, rr, L.TOL_EXTRA)
    res = {"run": doc["run_id"], "tool_diff": {k: tool["diff"].get(k) for k in ("fields", "classes", "ok")},
           "sup_diff": {k: d.get(k) for k in ("fields", "classes", "ok")}, "sup_findings": d["findings"][:10],
           "sup_diff_extra": {k: dx.get(k) for k in ("fields", "ok")},
           "requests": requests(doc, rr, tool["rows"], sup), "offset": be.R.offset}
    by = {e["label"]: e for e in doc["eats"] if e.get("ring_s") is not None}
    pre = doc["run_id"][:4]
    if pre == "x261":
        f = by.get("F400")
        if f:
            for name, rows in (("live", rr), ("sup", sup)):
                first = next((r for r in rows if r["age"] > f["ring_age"] + 1e-12 and r.get("HUNGER") is not None
                              and r["HUNGER"] < 0.25), None)
                back = L.request_after(rows, f["ring_age"])
                res.setdefault("F400_held", {})[name] = {
                    "first_below_min": (first["age"] - f["ring_age"]) * 60 if first else None, "return_min": back,
                    "held_min": back - (first["age"] - f["ring_age"]) * 60 if (first and back) else None}
        t = [by[k] for k in ("T217a", "T217b", "T217c") if k in by]
        if t:
            one = arm(rr, rp, rd, ("T217a", "T217b", "T217c"),
                      [{"s": t[0]["ring_s"], "kind": "eat", "food": "TKX.Mixed650"}])
            same = arm(rr, rp, rd, ("T217b", "T217c"),
                       [{"s": t[0]["ring_s"], "kind": "eat", "food": "TKX.Mixed217"}] * 2)
            a0 = t[0]["ring_age"]
            res["T217_arms"] = {"three_spread_live": L.request_after(rr, a0),
                                "three_spread_sup": L.request_after(sup, a0),
                                "one650_sup_arm": L.request_after(one, a0), "three_same_row_sup_arm":
                                L.request_after(same, a0)}
    if pre == "x262":
        arms = {}
        for k in ("P", "C", "F"):
            lunch, snack = by.get(k + "650"), by.get("S" + k)
            if not lunch or not snack:
                continue
            r = {}
            for alt in ("none", "P", "C", "F"):
                add = [] if alt == "none" else [{"s": snack["ring_s"], "kind": "eat", "food": "TKX.Snack" + alt}]
                rows = arm(rr, rp, rd, ("S" + k,), add)
                t = L.request_after(rows, snack["ring_age"])
                r[alt] = {"dinner_from_lunch": t + (snack["ring_age"] - lunch["ring_age"]) * 60 if t else None,
                          "mean180": L.mean_over(rows, snack["ring_age"], 180)}
            base = r["none"]["dinner_from_lunch"]
            dl = {x: r[x]["dinner_from_lunch"] - base for x in ("P", "C", "F")}
            arms[k] = {"lunch_tod": math.fmod(lunch["ring_age"] + be.R.offset, 24), "lunch_age": lunch["ring_age"],
                       "snack_after_lunch_min": (snack["ring_age"] - lunch["ring_age"]) * 60, "none": base,
                       "delays": dl, "p_minus_c": dl["P"] - dl["C"], "p_minus_f": dl["P"] - dl["F"],
                       "protein_vs_carb_mean180": r["C"]["mean180"] - r["P"]["mean180"]}
        res["snack_arms_sup"] = arms
    if pre == "x263":
        first = by.get("CAS")
        if first:
            s0, a0 = first["ring_s"], first["ring_age"]
            drops = ("CAS", "SOUP", "CW", "CW_water") + tuple("W%d" % n for n in range(100, 700, 100))
            w = [x for x in rd["events"] if x.get("label") == "CW_water"]
            shift = (w[0]["s"] - by["CW"]["ring_s"]) if (w and by.get("CW")) else 2
            out = {}
            for name, add in (("cas", [{"s": s0, "kind": "eat", "food": "TKX.Casserole"}]),
                              ("soup", [{"s": s0, "kind": "eat", "food": "TKX.Soup"}]),
                              ("cw", [{"s": s0, "kind": "eat", "food": "TKX.Casserole"},
                                      {"s": s0 + max(0, shift), "kind": "drink", "fluid": "Water", "litres": 0.356}])):
                h = L.at_minute(arm(rr, rp, rd, drops, add), a0, 17)
                out[name] = {"m17": h["value"] if h else None, "kJ": 10878.4 * h["value"] if h else None}
            res["rolls_arms_sup"] = out
            m17 = {}
            for lab in ("CAS", "SOUP", "CW"):
                e = by.get(lab)
                if e:
                    lv, sp = L.at_minute(rr, e["ring_age"], 17), L.at_minute(sup, e["ring_age"], 17)
                    m17[lab] = {"live": lv and lv["value"], "sup": sp and sp["value"]}
            res["m17_live"] = m17
        w0 = by.get("W100")
        if w0:
            drops = tuple("W%d" % n for n in range(100, 700, 100))
            ys = []
            for n in range(100, 700, 100):
                h = L.at_minute(arm(rr, rp, rd, drops, [{"s": w0["ring_s"], "kind": "eat", "food": "TKX.Water%d" % n}]),
                                w0["ring_age"], 1)
                ys.append(h["value"] if h else None)
            xs = list(range(100, 700, 100))
            r2 = None
            if all(y is not None for y in ys):
                mx, my = sum(xs) / 6, sum(ys) / 6
                sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
                r2 = sxy * sxy / (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
            m1 = {}
            for n in range(100, 700, 100):
                e = by.get("W%d" % n)
                if e:
                    lv, sp = L.at_minute(rr, e["ring_age"], 1), L.at_minute(sup, e["ring_age"], 1)
                    m1["W%d" % n] = {"live": lv and lv["value"], "sup": sp and sp["value"]}
            res["water_arms_sup"] = {"m1": ys, "r2": r2}
            res["m1_live"] = m1
    if pre == "x264":
        m = by.get("MARC")
        drops = ("MARC", "MSOUP", "DLO", "DHI", "MARC_water")
        if m:
            w = [x for x in rd["events"] if x.get("label") == "MARC_water"]
            shift = (w[0]["s"] - m["ring_s"]) if w else 2
            solid = arm(rr, rp, rd, drops, [{"s": m["ring_s"], "kind": "eat", "food": "TKX.Marc"},
                                             {"s": m["ring_s"] + max(0, shift), "kind": "drink", "fluid": "Water",
                                              "litres": 0.3}])
            soup = arm(rr, rp, rd, drops, [{"s": m["ring_s"], "kind": "eat", "food": "TKX.MarcSoup"}])
            res["marc_arms_sup"] = {"soup_mean180": L.mean_over(soup, m["ring_age"], 180),
                                    "solid_water_mean180": L.mean_over(solid, m["ring_age"], 180)}
        dd = by.get("DLO")
        if dd:
            lo = arm(rr, rp, rd, drops, [{"s": dd["ring_s"], "kind": "eat", "food": "TKX.Dense400Lo"}])
            hi = arm(rr, rp, rd, drops, [{"s": dd["ring_s"], "kind": "eat", "food": "TKX.Dense400Hi"}])
            res["dense_arms_sup"] = {"lo_mean180": L.mean_over(lo, dd["ring_age"], 180),
                                     "hi_mean180": L.mean_over(hi, dd["ring_age"], 180),
                                     "lo_req": L.request_after(lo, dd["ring_age"]),
                                     "hi_req": L.request_after(hi, dd["ring_age"])}
        means = {}
        for lab in ("MARC", "MSOUP", "DLO", "DHI"):
            e = by.get(lab)
            if e:
                means[lab] = {"live": L.mean_over(rr, e["ring_age"], 180), "sup": L.mean_over(sup, e["ring_age"], 180)}
        res["means_live"] = means
    if pre == "x265":
        milk = sorted(x["s"] for x in rd["events"] if x.get("label") == "MILK")
        solid = by.get("SOLID")
        ring_by = {r["s"]: r for r in rr}
        if milk and solid:
            a_m, a_s = ring_by[milk[0]]["age"], solid["ring_age"]
            res["anchored"] = {"MILK": {"live": L.request_after(rr, a_m), "sup": L.request_after(sup, a_m)},
                               "SOLID": {"live": L.request_after(rr, a_s), "sup": L.request_after(sup, a_s)}}
            shift = solid["ring_s"] - milk[0]
            mev = [x for x in rd["events"] if x.get("label") == "MILK"]
            sw = arm(rr, rp, rd, ("MILK", "SOLID"), [{"s": milk[0], "kind": "eat", "food": "TKX.MilkSolid"}] +
                     [dict(x, s=x["s"] + shift) for x in mev])
            res["swap_sup"] = {"solid_at_slot1": L.request_after(sw, a_m), "milk_at_slot2": L.request_after(sw, a_s)}
    if pre == "x266":
        nc, be2 = replay(rr, rp, rd, cls=SleepOffNoCirc)
        import re
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
            tod = math.fmod(prev[s] + be2.R.offset, 24)
            exp = 1 + amp * math.cos(2 * math.pi * (tod - peak) / 24)
            dv = abs((hl / hn) / exp - 1)
            n += 1
            worst = max(worst, dv)
            over += dv > 0.01
        res["factor_sup"] = {"A": amp, "PEAK": peak, "rows": n, "max_rel": worst, "over_1pct": over}
    text = json.dumps(res, indent=1, default=str)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
