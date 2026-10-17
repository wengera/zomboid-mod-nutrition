"""The calibrated hunger curve's fit (Plan 15 Task 6; spec docs/superpowers/specs/2026-10-16-game-feel-design.md
section 2.1).

    python tools/fit_hunger_curve.py [--out <dir>]

The satiety model's own hunger, h_model (record.satiety.hModel), does not depend on the curve that maps it to the
HUNGER written to the game (K.hungerCurve.write): the curve reads h_model, the meal pool M (fed or not), the hour's
circadian factor and the HUNGER it wrote last, and writes nothing the model reads after a record's first minute (the
seed). So the fit runs the mod's server pipeline (tools/replay_live.py ServerReplay, the default body from a fresh
record at 07:00, sleep off, the guide's water: 500 g every 2 h from 08:00 to 22:00) once per scenario, keeps each
minute's h_model, M, hour and starvation flags, and scores candidate knots on a Python mirror of the curve stage
(stage()). The chosen knots are then set on the Lua kernel and replayed for real, and the mirror must reproduce the
written HUNGER within 1e-9 at every minute (verify()).

The scenarios (meals of PLATE, the guide's foods, sized to MEAL_KCAL, a third of 2,000 kcal):
- three: three meals a day at 07:30, 12:30 and 18:30 for DAYS_THREE days; read on days 1 to 3, waking hours 07:00 to
  23:00;
- fast: two such days, then breakfast at 07:30 on day 2 and nothing more for 60 h; read from that breakfast.
The vanilla side (tools/vanilla_model.py, DayLength 4, StatsDecrease 3): the three-meal days with a can of bolognese
(hunger -0.24, 540 kcal) at each meal from a hunger of 0.25, the review's 38 % of waking hours at level 1 or more and
4.5 % at level 2 or more (game-feel review Q3); and the cadence after a meal that takes HUNGER to its floor (one can at
a hunger of 0.25, which leaves 0.01 under the food timer): each level's return in hours.

The loss, each miss squared and summed (each target's tolerance is the size it is divided by):
- the deepest post-meal HUNGER of the three-meal days over 0.02 (MIN_AFTER), in units of 0.02;
- the waking shares at level 1 and level 2, relative to vanilla's (level 2 against at least 0.05);
- the hours to levels 1, 2 and 3 after the fast's breakfast, and to the 0.69 cap, as log ratios to vanilla's; these
  read the curve's own climb (the starvation flags off, curve_only()), and Starving as written (the acute onset, 30
  unfed hours, K.drain.STARVE_ONSET_H) is reported beside them.

The foot: X[2], the flat foot's end, is no searched knot (no loss term moves while every satisfying meal reads 0): it is
the highest of the three-meal days' lowest h_model after a meal, rounded up to 0.001 (foot()), so a 667 kcal meal reads
0 and anything less sating reads above it.

The search: a coordinate refinement from START (the foot set) over the other four knots (X[3] to X[6]), each moved by
its step up and down and kept when the loss falls, the step halved after a round with no move, until the step is under 1e-4; a
knot is kept strictly inside (its neighbours, BOUNDS). The stability check (CLAUDE.md section 6, fits): each knot at
x0.95 and x1.05 with the loss and every target, and a meal-size sweep (200 to 1,300 kcal at the fast's breakfast) with
its deepest HUNGER and its return to levels 1 and 2. A knot at or within one step of its bound is reported. Nothing
here writes a tracked file: --out writes fit-compact.json (the chosen point, every target's value and miss, the
stability readings, the search spec, the scenarios and the HEAD commit) into a gitignored folder (testing/runs/ by
default); the committed artifact is that file copied byte-identical (testing/artifacts/fit-hunger-curve-<date>/): the
compact file is the whole output, so no sha256 of a larger fit.json is kept.
"""
import argparse
import json
import math
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import replay_live as RL  # noqa: E402
import vanilla_model as VM  # noqa: E402

DAY = 1440
HOUR_OFFSET = 7.0                      # world age 0 is 07:00 (tools/mod_guide_series.HOUR_OFFSET)
MEAL_MIN = (30, 330, 690)              # 07:30, 12:30 and 18:30: vanilla's three cans at these hours read the review's 38 %
MEAL_KCAL = 667.0                      # a third of 2,000 kcal (spec section 2.1)
PLATE = ["Base.CannedBologneseOpen", "Base.Bread", "Base.Apple", "Base.Orange", "Base.Burger", "Base.TunaTinOpen"]
WATER_MIN = (60, 180, 300, 420, 540, 660, 780, 900)
WATER_G = 500.0
DAYS_THREE = 4
FED_DAYS = 2                           # the fast's fed days before its breakfast
FAST_H = 60
WAKE_MIN = 16 * 60                     # 07:00 to 23:00
THRESHOLDS = (0.15, 0.25, 0.45, 0.70)  # VANILLA #0508
CAP = 0.69                             # K.hybrid's hungerCap
STARVING_MIN = 0.71                    # K.hybrid's starvingMin
MIN_AFTER = 0.02                       # a satisfying meal reads H <= 0.02 at its lowest (Task 6 amendments)
AFTER_MIN = 120                        # minutes after a meal its lowest HUNGER is read over
VANILLA_CAN = {"hunger_change": -0.24, "calories": 540.0}
VANILLA_START = 0.25
SWEEP_KCAL = (200.0, 400.0, 667.0, 1000.0, 1300.0)
Y = (0.0, 0.0, 0.15, 0.25, 0.45, 0.70, 1.0)
START = (0.105, 0.225, 0.275, 0.38, 0.63)
BOUNDS = ((0.02, 0.30), (0.10, 0.45), (0.12, 0.55), (0.20, 0.65), (0.40, 0.95))
STEP0 = 0.02
STEP_MIN = 1e-4
PATHS = ("satiety.hModel", "satiety.M", "drain.starving", "drain.starveAcute")


# ---- the scenarios -------------------------------------------------------------------------------------------------

def water(days):
    return [{"minute": d * DAY + m, "kind": "autodrop", "g": WATER_G} for d in range(days) for m in WATER_MIN]


def meal(minute, kcal):
    return {"minute": minute, "kind": "meal", "size": kcal, "plate": list(PLATE)}


def three_events():
    return [meal(d * DAY + m, MEAL_KCAL) for d in range(DAYS_THREE) for m in MEAL_MIN] + water(DAYS_THREE)


def fast_minutes():
    return FED_DAYS * DAY + MEAL_MIN[0] + FAST_H * 60


def fast_events(kcal=MEAL_KCAL):
    n = fast_minutes()
    days = n // DAY + 1
    ev = [meal(d * DAY + m, MEAL_KCAL) for d in range(FED_DAYS) for m in MEAL_MIN]
    ev.append(meal(FED_DAYS * DAY + MEAL_MIN[0], kcal))
    return [e for e in ev + water(days) if e["minute"] < n]


def replay(events, minutes, knots=None):
    """The server pipeline from a fresh record; knots (X[2] to X[6]) set on the kernel first. Returns (rows, backend)."""
    be = RL.ServerReplay(hour_offset=HOUR_OFFSET, rng="half", sleep_allowed=False)
    if knots is not None:
        set_knots(be.K, knots)
    ev = sorted((e for e in events if e["minute"] < minutes), key=lambda e: e["minute"])   # none past the window
    rows = RL.run(be, RL.synthetic_ages(minutes), ev, list(PATHS), start_age=0.0)
    return rows, be


def set_knots(K, knots):
    for i, x in enumerate(knots):
        K.hungerCurve.X[i + 2] = float(x)


def shipped(K):
    return tuple(float(K.hungerCurve.X[i]) for i in range(2, 7))


# ---- the curve stage's mirror --------------------------------------------------------------------------------------

def curve_map(h, X):
    if h <= X[0]:
        return Y[0]
    for i in range(1, len(X)):
        if h <= X[i]:
            return Y[i - 1] + (Y[i] - Y[i - 1]) * (h - X[i - 1]) / (X[i] - X[i - 1])
    return Y[-1]


def circadian(K, age):
    tod = math.fmod(age + HOUR_OFFSET, 24.0)
    return 1 + K["A"] * math.cos(6.283185307179586 * (tod - K["PEAK"]) / 24)


def stage(trace, knots, C, h0):
    """K.hungerCurve.write and K.hybrid.write's caps over a trace (see the module docstring), from a first HUNGER h0;
    C holds the kernel constants the stage reads. Returns the written HUNGER per row."""
    X = (0.0,) + tuple(knots) + (1.0,)
    out = []
    prev = h0
    for r in trace:
        h = r["satiety.hModel"]
        fed = r["satiety.M"] >= C["FED_M"]
        if not fed:
            c = circadian(C, r["age"])
            x = h / c if 0 < c < 1 else h
            H = max(curve_map(x, X), prev)
        else:
            H = curve_map(h, X)
            for t in THRESHOLDS:
                if prev > t and t - C["DEAD_ZONE"] < H <= t:
                    H = min(prev, t + C["HOLD_EPS"])
                    break
        cap, lo = CAP, 0.0
        if r.get("drain.starving"):
            cap = 1.0
            if r.get("drain.starveAcute"):
                lo = STARVING_MIN
        H = min(max(H, lo), cap)
        out.append(H)
        prev = H
    return out


def constants(K):
    return {"A": float(K.satiety.CIRCADIAN_A), "PEAK": float(K.satiety.CIRCADIAN_PEAK_H),
            "FED_M": float(K.hungerCurve.FED_M), "DEAD_ZONE": float(K.hungerCurve.DEAD_ZONE),
            "HOLD_EPS": float(K.hungerCurve.HOLD_EPS)}


# ---- the readings --------------------------------------------------------------------------------------------------

def level(v):
    return sum(1 for t in THRESHOLDS if v > t)


def shares(H, days=range(1, DAYS_THREE)):
    wake = [H[d * DAY + m] for d in days for m in range(WAKE_MIN)]
    return (sum(1 for v in wake if level(v) >= 1) / len(wake), sum(1 for v in wake if level(v) >= 2) / len(wake))


def deepest(H, meals):
    """The highest of the meals' lowest HUNGER over AFTER_MIN minutes after each."""
    return max(min(H[m:m + AFTER_MIN]) for m in meals)


def returns(H, start):
    """Hours from minute start to the first HUNGER over each threshold, and to the cap (None when never)."""
    out = []
    for t in THRESHOLDS[:3]:
        k = next((i for i in range(start, len(H)) if H[i] > t), None)
        out.append(None if k is None else (k - start) / 60.0)
    k = next((i for i in range(start, len(H)) if H[i] >= CAP - 1e-9), None)
    out.append(None if k is None else (k - start) / 60.0)
    k = next((i for i in range(start, len(H)) if H[i] > THRESHOLDS[3]), None)
    out.append(None if k is None else (k - start) / 60.0)     # Starving: reported, not scored (the acute onset, 30 unfed hours)
    return out


def vanilla():
    """vanilla_model's three-can day shares and the fast's returns (levels 1-4, hours after the breakfast can)."""
    ev = [dict(VANILLA_CAN, t_h=d * 24 + m / 60.0, kind="eat") for d in range(DAYS_THREE) for m in MEAL_MIN]
    out = VM.simulate({"hours": DAYS_THREE * 24, "dt_min": 1, "start": {"hunger": VANILLA_START}, "events": ev})
    H = [v for _, v in out["hunger"]][1:]
    s1, s2 = shares(H)
    ev = [dict(VANILLA_CAN, t_h=0.0, kind="eat")]
    out = VM.simulate({"hours": FAST_H, "dt_min": 1, "start": {"hunger": VANILLA_START}, "events": ev})
    F = [v for _, v in out["hunger"]]
    ret = []
    for t in THRESHOLDS:
        k = next(i for i in range(len(F)) if F[i] > t)
        ret.append(k / 60.0)
    return {"share1": s1, "share2": s2, "returns": ret, "after": min(F[:AFTER_MIN])}


def read(knots, traces, C, V):
    three, fast = traces["three"], traces["fast"]
    H3 = stage(three["rows"], knots, C, three["h0"])
    HF = stage(fast["rows"], knots, C, fast["h0"])
    HC = stage(fast["curve"], knots, C, fast["h0"])
    meals = [d * DAY + m for d in range(1, DAYS_THREE) for m in MEAL_MIN]
    s1, s2 = shares(H3)
    b = FED_DAYS * DAY + MEAL_MIN[0]
    ret = returns(HC, b)[:4] + returns(HF, b)[4:]      # the curve's own climb, then Starving as written
    r = {"deepest": deepest(H3, meals), "share1": s1, "share2": s2, "returns": ret}
    miss = {"deepest": max(0.0, r["deepest"] - MIN_AFTER) / MIN_AFTER,
            "share1": (s1 - V["share1"]) / V["share1"],
            "share2": (s2 - V["share2"]) / max(V["share2"], 0.05)}
    for i, name in enumerate(("t1", "t2", "t3", "tcap")):
        t = ret[i]
        miss[name] = 10.0 if t is None else math.log(t / V["returns"][i])
    r["miss"] = miss
    r["loss"] = sum(v * v for v in miss.values())
    return r


def ordered(knots):
    if any(k <= 0 or k >= 1 for k in knots):
        return False
    return all(knots[i] < knots[i + 1] for i in range(len(knots) - 1))


def inside(knots):
    return all(lo <= k <= hi for k, (lo, hi) in zip(knots, BOUNDS))


def foot(trace3):
    """The flat foot's end: the highest of the three-meal days' lowest h_model over AFTER_MIN minutes after each meal,
    rounded up to 0.001, so every such meal reads 0 and a smaller one reads above it (the most graded snacks)."""
    rows = trace3["rows"]
    meals = [d * DAY + m for d in range(1, DAYS_THREE) for m in MEAL_MIN]
    low = max(min(r["satiety.hModel"] for r in rows[m:m + AFTER_MIN]) for m in meals)
    return math.ceil(low * 1000.0) / 1000.0


def search(traces, C, V, start=START):
    best = tuple(start)
    best_r = read(best, traces, C, V)
    step = STEP0
    tried = 1
    while step >= STEP_MIN:
        moved = False
        for i in range(1, len(best)):                      # the foot (X[2]) is foot()'s, not searched
            for sgn in (1, -1):
                cand = list(best)
                cand[i] = round(cand[i] + sgn * step, 6)
                cand = tuple(cand)
                if not ordered(cand) or not inside(cand):
                    continue
                r = read(cand, traces, C, V)
                tried += 1
                if r["loss"] < best_r["loss"] - 1e-12:
                    best, best_r, moved = cand, r, True
        if not moved:
            step = step / 2
    return best, best_r, tried


def curve_only(rows):
    """The trace with the starvation flags off: the curve's own climb to the cap, which the knots set (the acute onset's
    0.71 minimum, Plan 15 Task 6 fix 1, would otherwise lift H to the cap at the onset whatever the top knot)."""
    return [dict(r, **{"drain.starving": False, "drain.starveAcute": False}) for r in rows]


def trace(rows, be):
    keep = [{"age": r["age"], "satiety.hModel": r["satiety.hModel"], "satiety.M": r["satiety.M"],
             "drain.starving": bool(r.get("drain.starving")), "drain.starveAcute": bool(r.get("drain.starveAcute")),
             "HUNGER": r["HUNGER"]} for r in rows]
    return {"rows": keep}


def verify(knots, C):
    """The chosen knots replayed for real: the mirror on the run's own trace reproduces its written HUNGER."""
    worst = 0.0
    for events, n in ((three_events(), DAYS_THREE * DAY), (fast_events(), fast_minutes())):
        rows, be = replay(events, n, knots)
        t = trace(rows, be)
        H = stage(t["rows"][1:], knots, C, rows[0]["HUNGER"])
        worst = max(worst, max(abs(a - r["HUNGER"]) for a, r in zip(H, rows[1:])))
    return worst


def stability(best, traces, C, V):
    out = {"knots": [], "sweep": []}
    for i in range(len(best)):
        for f in (0.95, 1.05):
            cand = list(best)
            cand[i] = cand[i] * f
            cand = tuple(cand)
            if not ordered(cand):
                out["knots"].append({"knot": i + 2, "factor": f, "ordered": False})
                continue
            r = read(cand, traces, C, V)
            out["knots"].append({"knot": i + 2, "factor": f, "loss": r["loss"], "deepest": r["deepest"],
                                 "share1": r["share1"], "share2": r["share2"], "returns": r["returns"]})
    b = FED_DAYS * DAY + MEAL_MIN[0]
    for kcal in SWEEP_KCAL:
        rows, be = replay(fast_events(kcal), fast_minutes())
        t = trace(rows, be)
        H = stage(t["rows"], best, C, 0.2)
        ret = returns(H, b)
        out["sweep"].append({"kcal": kcal, "before": H[b - 1], "lowest": min(H[b:b + AFTER_MIN]),
                             "hModelLowest": min(r["satiety.hModel"] for r in rows[b:b + AFTER_MIN]),
                             "t1": ret[0], "t2": ret[1]})
    return out


def at_bound(best):
    out = []
    for i, (k, (lo, hi)) in enumerate(zip(best, BOUNDS)):
        if i == 0:
            continue
        if k - lo < STEP0 or hi - k < STEP0:
            out.append(i + 2)
    return out


def fit():
    rows3, be = replay(three_events(), DAYS_THREE * DAY)
    C = constants(be.K)
    traces = {"three": {"rows": trace(rows3, be)["rows"], "h0": 0.2}}
    rowsf, _ = replay(fast_events(), fast_minutes())
    rf = trace(rowsf, be)["rows"]
    traces["fast"] = {"rows": rf, "curve": curve_only(rf), "h0": 0.2}
    V = vanilla()
    x0 = foot(traces["three"])
    best, r, tried = search(traces, C, V, (x0,) + tuple(START[1:]))
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    return {"head": head, "search": {"method": "coordinate", "step0": STEP0, "stepMin": STEP_MIN, "bounds": "BOUNDS",
                                     "foot": "foot(): not searched"},
            "scenarios": {"MEAL_MIN": list(MEAL_MIN), "MEAL_KCAL": MEAL_KCAL, "PLATE": list(PLATE),
                          "WATER_MIN": list(WATER_MIN), "WATER_G": WATER_G, "DAYS_THREE": DAYS_THREE,
                          "FED_DAYS": FED_DAYS, "FAST_H": FAST_H, "HOUR_OFFSET": HOUR_OFFSET,
                          "SWEEP_KCAL": list(SWEEP_KCAL), "VANILLA_CAN": dict(VANILLA_CAN),
                          "VANILLA_START": VANILLA_START},
            "vanilla": V, "start": list(START), "foot": x0, "bounds": [list(b) for b in BOUNDS], "candidates": tried,
            "chosen": list(best), "reading": r, "atBound": at_bound(best), "shipped": list(shipped(be.K)),
            "shippedReading": read(shipped(be.K), traces, C, V), "verify": verify(best, C),
            "stability": stability(best, traces, C, V)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join(REPO, "testing", "runs", "fit-hunger-curve"))
    a = ap.parse_args(argv)
    res = fit()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "fit-compact.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print(json.dumps({k: res[k] for k in ("chosen", "atBound", "verify", "candidates")}))
    print("reading", json.dumps(res["reading"]))
    print("shipped", res["shipped"], json.dumps(res["shippedReading"]))
    print("vanilla", json.dumps(res["vanilla"]))
    for s in res["stability"]["knots"]:
        print("knot", json.dumps(s))
    for s in res["stability"]["sweep"]:
        print("sweep", json.dumps(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
