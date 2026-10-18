"""The calibrated hunger curve's fit (Plan 15 Tasks 6 and 6c, Plan 16 Task 4b; spec
docs/superpowers/specs/2026-10-16-game-feel-design.md section 2.1).

    python tools/fit_hunger_curve.py [--out <dir>]

The satiety model's own hunger, h_model (record.satiety.hModel), does not depend on the curve that maps it to the
HUNGER written to the game (K.hungerCurve.write): the curve reads h_model, the meal pool M (fed or not), the hour's
circadian factor and the HUNGER it wrote last, and writes nothing the model reads after a record's first minute (the
seed). So the fit runs the mod's server pipeline (tools/replay_live.py ServerReplay, the default body from a fresh
record at 07:00, the guide's water: 500 g every 2 h from 08:00 to 22:00) once per scenario and configuration, keeps
each minute's h_model, M, body-clock hour and starvation flags, and scores candidate knots on a Python mirror of the
curve stage (stage()). The chosen knots are then set on the Lua kernel and replayed for real, and the mirror must
reproduce the written HUNGER within 1e-9 at every minute of every configuration (verify()). The knots shipped before
(PREVIOUS, fit-hunger-curve-20261017c) are read beside the chosen point.

The configurations (Plan 16 Task 4b): every scenario runs on both server sleep settings, through the shipped code path
(no replay overlay):
- off: SleepAllowed or SleepNeeded false, vanilla multiplayer's default; the mod has no daily rhythm (K.circadian.hour
  is nil, the circadian factor 1, Plan 16 Task 4), and the character never sleeps;
- on: both true; the character sleeps 23:00 to 07:00 each night (SLEEP_MIN, 8 h, over the 7.5 h need, so no sleep
  debt), and the body clock (seeded at the world hour on the record's first minute) is reset to 07:00 by each full
  sleep, so the rhythm reads the body clock's hour.
The loss is the configurations' losses weighted by W_CONFIG (sleep off first, 2:1, a game choice), over their sum. The
vanilla targets are the same for both (the controller's ruling: the targets unchanged); vanilla's own sleep-on cadence
(the same nights, vanilla_model's asleep hunger rate) is read beside them, never scored.

The scenarios (meals of PLATE, the guide's foods, sized to MEAL_KCAL, a third of 2,000 kcal):
- three: three meals a day at 07:30, 12:30 and 18:30 for DAYS_THREE days; read on days 1 to 3, waking hours 07:00 to
  23:00;
- fast: two such days, then breakfast at 07:30 on day 2 and nothing more for 60 h; read from that breakfast.
The vanilla side (tools/vanilla_model.py, DayLength 4, StatsDecrease 3): the three-meal days with a can of bolognese
(hunger -0.24, 540 kcal) at each meal from a hunger of 0.25, the review's 38 % of waking hours at level 1 or more and
4.5 % at level 2 or more (game-feel review Q3), and each meal's return to Peckish on days 1 to 3 (Task 6c: breakfast
1.17 h, lunch 4.25 h, dinner 5.00 h); and the cadence after a meal that takes HUNGER to its floor (one can at a hunger
of 0.25, which leaves 0.01 under the food timer): each level's return in hours.

The loss, each miss squared and summed (each target's tolerance is the size it is divided by):
- the deepest post-meal HUNGER of the three-meal days over 0.02 (MIN_AFTER), in units of 0.02;
- the waking shares at level 1 and level 2, relative to vanilla's (level 2 against at least 0.05), each times W_SHARE;
- each meal's return to Peckish on the three-meal days 1 to 3 (Task 6c): the mean over the days of the log ratio to
  vanilla's return after the same meal, times its W_MEAL; a meal whose HUNGER never passes 0.15 before the next meal
  reads the hours to that meal (censored, named in `censored`). Each return is the mean of two replays, the guide's
  water and the same water WATER_SHIFT minutes later (three_events(shift)): a drink of water lowers h_model, so on one
  water schedule a meal's return jumps by up to 0.6 h where the Peckish knot crosses the top of a drink's dip (dinner's
  last drink at 22:00: at X[3] 0.205 dinner reads 3.35 h, at 0.21 3.98 h), and the loss's minimum sat on that edge;
  a return that does not hang on when the last drink fell reads both schedules (Task 6c);
- the hours to levels 1, 2 and 3 after the fast's breakfast, and to the 0.69 cap, as log ratios to vanilla's; these
  read the curve's own climb (the starvation flags off, curve_only()), and Starving as written (the acute onset, 30
  unfed hours, K.drain.STARVE_ONSET_H) is reported beside them.

The foot: X[2], the flat foot's end, is no searched knot (no loss term moves while every satisfying meal reads 0): it is
the highest of the three-meal days' lowest h_model after a meal, rounded up to 0.001 (foot()), so a 667 kcal meal reads
0 and anything less sating reads above it.

The weights (Task 6c): vanilla's breakfast can (0.24) does not cover the night's rise (to 0.356), so vanilla carries
0.116 of hunger past breakfast and reads Peckish 1.17 h after it; that carry-over is also most of vanilla's level-1
share (4.3 of its 6.1 h). The satiety model keeps no additive residual of the earlier hunger: a satisfying meal resets
the meal pool, so h_model after a 667 kcal meal is set by the meal (0.084 after breakfast, 0.076 after lunch, 0.097
after dinner, the guide's water), and the hunger before carries only through the gut fill and the deficit drive
(skipping breakfast brings lunch's Peckish about 1 h earlier, Task 6c review); so no curve of h_model meets the
breakfast's 1.17 h and the satisfying meals' 4.25-5.00 h at once (Task 6c's finding). Nor can it
make dinner outlast lunch, as vanilla's does (its dinner can lands on the floor and fills the Well Fed timer, which
holds hunger): the circadian factor (S1273, peak 19:50) and dinner's higher floor lift h_model after dinner, so dinner
wears off first. The terms that read vanilla's residual, breakfast and the level-1 share, weigh W_CARRY; the level-2
share takes the same weight so the two shares stay one group (it reads 0.031 across the Peckish knot's basin, so it
moves no knot but X[4]); the others weigh 1.

The search: a scan of each of the other four knots (X[3] to X[6]) in turn over its BOUNDS at SCAN_STEP, the others held
(the loss is piecewise constant in whole minutes and has more than one valley), then a coordinate refinement from the
scan's point, each knot moved by its step up and down and kept when the loss falls, the step halved after a round with
no move, until the step is under 1e-4; a knot is kept strictly inside (its neighbours, BOUNDS). The Peckish knot's
profile (profile(), PROFILE_STEP) records the loss, each meal's return, the shares and the fast's Peckish return across
its bounds. The stability check (CLAUDE.md section 6, fits): each knot at x0.95 and x1.05 with the loss and every
target (each meal's return included), and a meal-size sweep (200 to 1,300 kcal at the fast's breakfast) with its
deepest HUNGER and its return to levels 1 and 2. A knot at or within one step of its bound is reported. Nothing
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
PREVIOUS = (0.099, 0.214688, 0.299375, 0.42875, 0.734688)   # fit-hunger-curve-20261017c's knots (Plan 15 Task 14b), read beside
MEALS = ("breakfast", "lunch", "dinner")
W_CARRY = 0.5                          # Task 6c: the terms that read vanilla's breakfast carry-over (the docstring)
W_MEAL = (W_CARRY, 1.0, 1.0)           # breakfast, lunch, dinner
W_SHARE = W_CARRY                      # the level-1 and level-2 shares
SCAN_STEP = 0.0025
WATER_SHIFT = 60                       # Task 6c: the meal returns also read on the water an hour later (the docstring)
PROFILE_STEP = 0.005
BOUNDS = ((0.02, 0.30), (0.10, 0.45), (0.12, 0.55), (0.20, 0.65), (0.40, 0.95))
STEP0 = 0.02
STEP_MIN = 1e-4
PATHS = ("satiety.hModel", "satiety.M", "drain.starving", "drain.starveAcute", "acute.bodyHour", "acute.bodyOn")
SLEEP_MIN = 960                        # 23:00: a sleep-on scenario sleeps 23:00 to 07:00 each night (the docstring)
CONFIGS = ("off", "on")                # Plan 16 Task 4b: the server's sleep setting, off (the default) and on
W_CONFIG = {"off": 2.0, "on": 1.0}     # game choice (Plan 16 Task 4b, spec section 6): sleep off, vanilla multiplayer's default, weighs first
SHIPPED_CONFIG = "off"                 # the configuration a server runs unless its admin turns sleep on


# ---- the scenarios -------------------------------------------------------------------------------------------------

def water(days, shift=0):
    return [{"minute": d * DAY + m + shift, "kind": "autodrop", "g": WATER_G} for d in range(days) for m in WATER_MIN]


def meal(minute, kcal):
    return {"minute": minute, "kind": "meal", "size": kcal, "plate": list(PLATE)}


def nights(days):
    """Asleep 23:00 to 07:00 on each of the days (a sleep-on scenario's nights)."""
    ev = []
    for d in range(days):
        ev.append({"minute": d * DAY + SLEEP_MIN, "kind": "sleep", "asleep": True})
        ev.append({"minute": (d + 1) * DAY, "kind": "sleep", "asleep": False})
    return ev


def three_events(shift=0, config=SHIPPED_CONFIG):
    ev = [meal(d * DAY + m, MEAL_KCAL) for d in range(DAYS_THREE) for m in MEAL_MIN] + water(DAYS_THREE, shift)
    return ev + nights(DAYS_THREE) if config == "on" else ev


def fast_minutes():
    return FED_DAYS * DAY + MEAL_MIN[0] + FAST_H * 60


def fast_events(kcal=MEAL_KCAL, config=SHIPPED_CONFIG):
    n = fast_minutes()
    days = n // DAY + 1
    ev = [meal(d * DAY + m, MEAL_KCAL) for d in range(FED_DAYS) for m in MEAL_MIN]
    ev.append(meal(FED_DAYS * DAY + MEAL_MIN[0], kcal))
    ev = ev + water(days) + (nights(days) if config == "on" else [])
    return [e for e in ev if e["minute"] < n]


def replay(events, minutes, knots=None, config=SHIPPED_CONFIG):
    """The server pipeline from a fresh record; knots (X[2] to X[6]) set on the kernel first. Returns (rows, backend).
    config is the server's sleep setting ("off" or "on", CONFIGS), answered to the options poll the mod reads every
    minute; the rhythm is the shipped code's (Plan 16 Task 4: none with sleep off, the body clock with sleep on), no
    replay overlay. A sleep-on scenario's nights are its events' (three_events, fast_events)."""
    if config not in CONFIGS:
        raise ValueError("unknown configuration %r" % (config,))
    be = RL.ServerReplay(hour_offset=HOUR_OFFSET, rng="half", sleep_allowed=(config == "on"))
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


def circadian(K, hour):
    """K.satiety.circadian at the body clock's hour; 1 with no hour (sleep off, or the clock not running)."""
    if hour is None:
        return 1.0
    return 1 + K["A"] * math.cos(6.283185307179586 * (hour - K["PEAK"]) / 24)


def stage(trace, knots, C, h0):
    """K.hungerCurve.write and K.hybrid.write's caps over a trace (see the module docstring), from a first HUNGER h0;
    C holds the kernel constants the stage reads. Returns the written HUNGER per row."""
    X = (0.0,) + tuple(knots) + (1.0,)
    out = []
    prev = h0
    for r in trace:
        h = r["satiety.hModel"]
        fed = r["satiety.M"] >= C["FED_M"]
        cap = 1.0 if r.get("drain.starving") else CAP
        if prev > cap:                                   # a lifted cap or the starving minimum just ended: re-seeded
            prev = 0.0
        if not fed:
            c = circadian(C, r["body"])
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


def meal_returns(H, days=range(1, DAYS_THREE)):
    """Each meal's hours to the first HUNGER over 0.15 after it, on each of the days: {meal: [(hours, censored)]}. A
    meal whose HUNGER does not pass 0.15 before the next meal reads the hours to that meal, censored."""
    out = {}
    for j, name in enumerate(MEALS):
        vals = []
        for d in days:
            b = d * DAY + MEAL_MIN[j]
            e = d * DAY + (MEAL_MIN[j + 1] if j + 1 < len(MEAL_MIN) else DAY + MEAL_MIN[0])
            e = min(e, len(H))
            k = next((i for i in range(b, e) if H[i] > THRESHOLDS[0]), None)
            vals.append(((e - b) / 60.0, True) if k is None else ((k - b) / 60.0, False))
        out[name] = vals
    return out


def vanilla(config=SHIPPED_CONFIG):
    """vanilla_model's three-can day shares and the fast's returns (levels 1-4, hours after the breakfast can). The
    scored targets are config "off"'s; "on" sleeps the same nights as the mod's sleep-on scenarios (23:00 to 07:00,
    sleep allowed) and is read beside them, never scored, its meals with their censored names (a return the night
    outlasts reads the hours to the next meal) and a level never reached in the fast None."""
    sleep = config == "on"
    nights_h = [dict(kind="sleep", t_h=d * 24 + SLEEP_MIN / 60.0, duration_h=8.0) for d in range(DAYS_THREE)]
    ev = [dict(VANILLA_CAN, t_h=d * 24 + m / 60.0, kind="eat") for d in range(DAYS_THREE) for m in MEAL_MIN]
    out = VM.simulate({"hours": DAYS_THREE * 24, "dt_min": 1, "start": {"hunger": VANILLA_START},
                       "settings": {"sleep_allowed": sleep}, "events": ev + (nights_h if sleep else [])})
    H = [v for _, v in out["hunger"]][1:]
    s1, s2 = shares(H)
    meals = meal_returns([v for _, v in out["hunger"]])     # index = minute: the eat lands on its own minute
    censored = sorted(k for k, v in meals.items() if any(c for _, c in v))
    if not sleep:
        assert not censored
    meals = {k: [t for t, _ in v] for k, v in meals.items()}
    ev = [dict(VANILLA_CAN, t_h=0.0, kind="eat")]
    first = (SLEEP_MIN - MEAL_MIN[0]) / 60.0                 # the fast's first night, from its 07:30 breakfast
    nights_f = [dict(kind="sleep", t_h=first + 24 * k, duration_h=8.0) for k in range(int(FAST_H // 24) + 1)]
    out = VM.simulate({"hours": FAST_H, "dt_min": 1, "start": {"hunger": VANILLA_START},
                       "settings": {"sleep_allowed": sleep}, "events": ev + (nights_f if sleep else [])})
    F = [v for _, v in out["hunger"]]
    ret = []
    for t in THRESHOLDS:
        k = next((i for i in range(len(F)) if F[i] > t), None)
        ret.append(None if k is None else k / 60.0)
    r = {"share1": s1, "share2": s2, "returns": ret, "after": min(F[:AFTER_MIN]), "meals": meals}
    if sleep:
        r["censored"] = censored
    return r


def read_config(knots, traces, C, V):
    """One configuration's readings and loss: traces holds its "three" (rows, shifted, h0) and "fast" (rows, curve,
    h0) traces."""
    three, fast = traces["three"], traces["fast"]
    H3 = stage(three["rows"], knots, C, three["h0"])
    HF = stage(fast["rows"], knots, C, fast["h0"])
    HC = stage(fast["curve"], knots, C, fast["h0"])
    meals = [d * DAY + m for d in range(1, DAYS_THREE) for m in MEAL_MIN]
    s1, s2 = shares(H3)
    b = FED_DAYS * DAY + MEAL_MIN[0]
    ret = returns(HC, b)[:4] + returns(HF, b)[4:]      # the curve's own climb, then Starving as written
    mr = meal_returns(H3)
    ms = meal_returns(stage(three["shifted"], knots, C, three["h0"]))
    r = {"deepest": deepest(H3, meals), "share1": s1, "share2": s2, "returns": ret,
         "meals": {k: [(a + b) / 2.0 for (a, _), (b, _) in zip(v, ms[k])] for k, v in mr.items()},
         "mealsByWater": {"guide": {k: [t for t, _ in v] for k, v in mr.items()},
                          "shifted": {k: [t for t, _ in v] for k, v in ms.items()}},
         "censored": sorted(k for k in MEALS if any(c for _, c in mr[k] + ms[k]))}
    miss = {"deepest": max(0.0, r["deepest"] - MIN_AFTER) / MIN_AFTER,
            "share1": W_SHARE * (s1 - V["share1"]) / V["share1"],
            "share2": W_SHARE * (s2 - V["share2"]) / max(V["share2"], 0.05)}
    for j, name in enumerate(MEALS):
        logs = [math.log(t / v) for t, v in zip(r["meals"][name], V["meals"][name])]
        miss[name] = W_MEAL[j] * sum(logs) / len(logs)
    for i, name in enumerate(("t1", "t2", "t3", "tcap")):
        t = ret[i]
        miss[name] = 10.0 if t is None else math.log(t / V["returns"][i])
    r["miss"] = miss
    r["loss"] = sum(v * v for v in miss.values())
    return r


def read(knots, traces, C, V):
    """Both configurations (traces[config], read_config) and the joint loss: their losses weighted by W_CONFIG, over
    the weights' sum."""
    per = {c: read_config(knots, traces[c], C, V) for c in CONFIGS}
    loss = sum(W_CONFIG[c] * per[c]["loss"] for c in CONFIGS) / sum(W_CONFIG[c] for c in CONFIGS)
    return {"loss": loss, "configs": per}


def ordered(knots):
    if any(k <= 0 or k >= 1 for k in knots):
        return False
    return all(knots[i] < knots[i + 1] for i in range(len(knots) - 1))


def inside(knots):
    return all(lo <= k <= hi for k, (lo, hi) in zip(knots, BOUNDS))


def foot(traces):
    """The flat foot's end: the highest of the three-meal days' lowest h_model over AFTER_MIN minutes after each meal,
    over every configuration's traces (traces[config]["three"]), rounded up to 0.001, so every such meal reads 0 and a
    smaller one reads above it (the most graded snacks)."""
    meals = [d * DAY + m for d in range(1, DAYS_THREE) for m in MEAL_MIN]
    low = max(min(r["satiety.hModel"] for r in traces[c]["three"]["rows"][m:m + AFTER_MIN])
              for c in CONFIGS for m in meals)
    return math.ceil(low * 1000.0) / 1000.0


def grid(lo, hi, step):
    n = int(round((hi - lo) / step))
    return [round(lo + i * step, 6) for i in range(n + 1)]


def search(traces, C, V, start=START):
    best = tuple(start)
    best_r = read(best, traces, C, V)
    tried = 1
    for i in range(1, len(best)):                          # the scan: each knot over its bounds, the others held
        for x in grid(BOUNDS[i][0], BOUNDS[i][1], SCAN_STEP):
            cand = tuple(x if j == i else best[j] for j in range(len(best)))
            if not ordered(cand) or not inside(cand):
                continue
            r = read(cand, traces, C, V)
            tried += 1
            if r["loss"] < best_r["loss"] - 1e-12:
                best, best_r = cand, r
    step = STEP0
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
    """The rows the stage reads; body is the body clock's hour the writer read (acute.bodyHour while acute.bodyOn is
    true, else None: Nutrients steps the clock before the writer, and nothing after it moves it in the minute)."""
    keep = [{"age": r["age"], "satiety.hModel": r["satiety.hModel"], "satiety.M": r["satiety.M"],
             "drain.starving": bool(r.get("drain.starving")), "drain.starveAcute": bool(r.get("drain.starveAcute")),
             "body": r.get("acute.bodyHour") if r.get("acute.bodyOn") is True else None,
             "HUNGER": r["HUNGER"]} for r in rows]
    return {"rows": keep}


def traces_of(config):
    """One configuration's traces at the kernel's knots: (traces, backend)."""
    rows3, be = replay(three_events(0, config), DAYS_THREE * DAY, config=config)
    rows3s, _ = replay(three_events(WATER_SHIFT, config), DAYS_THREE * DAY, config=config)
    rowsf, _ = replay(fast_events(MEAL_KCAL, config), fast_minutes(), config=config)
    rf = trace(rowsf, be)["rows"]
    return ({"three": {"rows": trace(rows3, be)["rows"], "shifted": trace(rows3s, be)["rows"], "h0": 0.2},
             "fast": {"rows": rf, "curve": curve_only(rf), "h0": 0.2}}, be)


def all_traces():
    """Every configuration's traces: ({config: traces}, the last backend)."""
    out = {}
    be = None
    for c in CONFIGS:
        out[c], be = traces_of(c)
    return out, be


def verify(knots, C):
    """The chosen knots replayed for real: the mirror on the run's own trace reproduces its written HUNGER, in every
    configuration."""
    worst = 0.0
    for c in CONFIGS:
        for events, n in ((three_events(0, c), DAYS_THREE * DAY), (three_events(WATER_SHIFT, c), DAYS_THREE * DAY),
                          (fast_events(MEAL_KCAL, c), fast_minutes())):
            rows, be = replay(events, n, knots, config=c)
            t = trace(rows, be)
            H = stage(t["rows"][1:], knots, C, rows[0]["HUNGER"])
            worst = max(worst, max(abs(a - r["HUNGER"]) for a, r in zip(H, rows[1:])))
    return worst


def summary(r):
    """One configuration's cadence (read_config): each meal's return on day 2 (the two waters' mean), the shares, the
    fast's returns and the loss."""
    return {"loss": r["loss"], "deepest": r["deepest"], "share1": r["share1"], "share2": r["share2"],
            "returns": r["returns"], "meals": {m: r["meals"][m][1] for m in MEALS}}


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
            out["knots"].append({"knot": i + 2, "factor": f, "loss": r["loss"],
                                 "configs": {c: summary(r["configs"][c]) for c in CONFIGS}})
    b = FED_DAYS * DAY + MEAL_MIN[0]
    for c in CONFIGS:
        for kcal in SWEEP_KCAL:
            rows, be = replay(fast_events(kcal, c), fast_minutes(), config=c)
            t = trace(rows, be)
            H = stage(t["rows"], best, C, 0.2)
            ret = returns(H, b)
            out["sweep"].append({"config": c, "kcal": kcal, "before": H[b - 1], "lowest": min(H[b:b + AFTER_MIN]),
                                 "hModelLowest": min(r["satiety.hModel"] for r in rows[b:b + AFTER_MIN]),
                                 "t1": ret[0], "t2": ret[1]})
    return out


def profile(best, traces, C, V, knot=3):
    """One knot (X[3], the Peckish knot, or X[4], the Hungry knot) across its bounds at PROFILE_STEP, the others at the
    chosen point: the joint loss and, per configuration, its loss, each meal's return on day 2, the shares and the
    fast's Peckish and Hungry returns."""
    i = knot - 2
    out = []
    for x in grid(BOUNDS[i][0], BOUNDS[i][1], PROFILE_STEP):
        cand = tuple(x if j == i else best[j] for j in range(len(best)))
        if not ordered(cand):
            continue
        r = read(cand, traces, C, V)
        row = {"x%d" % knot: x, "loss": r["loss"]}
        for c in CONFIGS:
            rc = r["configs"][c]
            row[c] = {"loss": rc["loss"], "meals": [rc["meals"][m][1] for m in MEALS], "share1": rc["share1"],
                      "share2": rc["share2"], "t1": rc["returns"][0], "t2": rc["returns"][1]}
        out.append(row)
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
    traces, be = all_traces()
    C = constants(be.K)
    V = vanilla()
    x0 = foot(traces)
    best, r, tried = search(traces, C, V, (x0,) + tuple(START[1:]))
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    return {"head": head, "search": {"method": "scan, then coordinate", "scanStep": SCAN_STEP, "step0": STEP0,
                                     "stepMin": STEP_MIN, "bounds": "BOUNDS", "foot": "foot(): not searched",
                                     "weights": {"meals": dict(zip(MEALS, W_MEAL)), "shares": W_SHARE,
                                                 "others": 1.0, "configs": dict(W_CONFIG)}},
            "scenarios": {"MEAL_MIN": list(MEAL_MIN), "MEAL_KCAL": MEAL_KCAL, "PLATE": list(PLATE),
                          "WATER_MIN": list(WATER_MIN), "WATER_G": WATER_G, "WATER_SHIFT": WATER_SHIFT,
                          "DAYS_THREE": DAYS_THREE,
                          "FED_DAYS": FED_DAYS, "FAST_H": FAST_H, "HOUR_OFFSET": HOUR_OFFSET,
                          "SWEEP_KCAL": list(SWEEP_KCAL), "VANILLA_CAN": dict(VANILLA_CAN),
                          "VANILLA_START": VANILLA_START, "CONFIGS": list(CONFIGS), "SLEEP_MIN": SLEEP_MIN},
            "vanilla": V, "vanillaSleepOn": vanilla("on"), "start": list(START), "foot": x0, "bounds": [list(b) for b in BOUNDS], "candidates": tried,
            "chosen": list(best), "reading": r, "atBound": at_bound(best), "shipped": list(shipped(be.K)),
            "shippedReading": read(shipped(be.K), traces, C, V), "previous": list(PREVIOUS),
            "previousReading": read(PREVIOUS, traces, C, V), "verify": verify(best, C),
            "stability": stability(best, traces, C, V), "profile": profile(best, traces, C, V, 3),
            "profileHungry": profile(best, traces, C, V, 4)}


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
    print("previous", res["previous"], json.dumps(res["previousReading"]))
    print("vanilla", json.dumps(res["vanilla"]))
    print("vanillaSleepOn", json.dumps(res["vanillaSleepOn"]))
    for s in res["stability"]["knots"]:
        print("knot", json.dumps(s))
    for s in res["stability"]["sweep"]:
        print("sweep", json.dumps(s))
    for s in res["profile"] + res["profileHungry"]:
        print("profile", json.dumps(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
