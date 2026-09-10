"""Slice 03 measured body side: passive burn, hunger/thirst decay, moodles, weight bands.

One live session (controller ruling, 2026-09-10) covering the matrix in
`docs/superpowers/plans/03-notes.md` -> "Experiment inputs". Every phase is saved to disk the
moment it finishes, so a wedge in a later row cannot cost the earlier numbers.

Three facts from the code map shape the whole design:

  * **The SERVER owns all of it.** Hunger and thirst tick only inside
    `updateStats_WakeState @8-@26 L10227` / `updateThirst @38-@73 L10377`
    (`GameServer.server || (!GameClient.client && IsoPlayer.getInstance() == this)`),
    endurance returns early on a client (`updateEndurance @0-@13 L3427`), and
    `Nutrition.update @42 L75` is `!GameClient.client` (Q7). So every rate here is fitted
    from SERVER samples; the client is read only at condition boundaries, as a convergence
    witness and as the subject of the two MP-authority rows.
  * **Rates are per GAME-second, not per real second** (Q0: `updateCalories` scales by
    `getGameWorldSecondsSinceLastUpdate()` and the stat updaters by the identical
    `getMultiplier() * getDeltaMinutesPerDay()`). Every fit below is therefore
    d<value>/d(`worldAge` * 3600), which makes it independent of `settimespeed` and of the
    fixture's minutes-per-day. That is what lets the accelerated conditions run at
    `settimespeed 30` in 24 s of wall time and still be compared with each other and with the
    coded constants.
  * **`S` (game-seconds per real second) is measured ONCE**, from the idle baseline at
    `settimespeed 1`, because it is the only quantity in the slice that is a property of the
    fixture rather than of the code. It is not needed by any ratio.

Rows, in the ruled priority order (numbering is the notes' matrix):
  1  idle baseline    -- settimespeed 1, >=300 s wall; all ratios; establishes S
  7  weight scaling   -- w 80 / 100 / 120 / 60, calorie burn ratio 1 / 1.25 / 1.5 / 0.75
  11 moodle sweep     -- HUNGRY and THIRST thresholds, level 0..4
  12 weight bands     -- hasTrait across 45..105 kg, plus the trait-refresh latency
  8  FOOD_EATEN gate  -- eat a steak, then hunger must be EXACTLY flat (the constant is 0)
  14 client weight    -- a client setWeight, and whether applyTraitFromWeight ever fires there
  13 MP regression    -- a client stats.set reverting inside the 1 Hz packet
  10 sandbox          -- StatsDecrease 1 / 5 vs 3; also settles the inferred key->value map
  9  traits           -- HeartyAppetite / LightEater / HighThirst / LowThirst
  2  asleep           -- setAsleep(true) server-side, if it holds
  3-6 movement        -- ONE attempt (ruling); n/a with a reason otherwise

Everything lands in <run_dir>/body.json, copied at the end to testing/artifacts/<run-id>/ and
to .superpowers/sdd/03-body-side/. ~20 minutes; run it with the machine idle
(`python testing/pzt doctor` first).
"""
import json
import os
import shutil
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/
from _common import ask, hard_kill, save
from pzt import fixture as fx
from pzt.paths import new_run_dir
from pzt.session import Timeline, make_client, make_server, teardown

USER = "admin"
FAST = 30                # accelerated multiplier for every condition except the baseline
BASELINE_SECONDS = 320   # >= 300 s wall at settimespeed 1 (ruling)
WINDOW_SECONDS = 24      # >= 20 s wall per accelerated condition (ruling)
SAMPLE_EVERY = 1.0       # target sampling period, seconds of wall time
SETTLE = 1.5             # after a write, before the first sample: one server tick + bus latency
SYNC_WAIT = 3.0          # >= 3 x the 1 Hz PlayerStatsPacket, for the MP-authority rows
SPAWN_WAIT = 2.5         # RCON additem -> item visible in the client's inventory

# Priming values. Calories are kept strictly inside updateWeight's neutral band so no window
# accidentally measures weight drift on top of the burn: gain fires above
# `1000 + (w-80)*40` and loss below `min(0, (w-70)*30)` (Q6 / slice 01).
PRIME = {"hunger": 0.20, "thirst": 0.20, "carbs": 500.0, "lipids": 400.0, "proteins": 400.0}
# One entry per weight any row writes, because a value outside the band for THAT weight is
# what nudged 45/50/55/60/65 off their set points in exp03-20260910-045523 (read-backs
# 45.0001 / 50.000099 / 55.000099 / 60.000757 / 65.000099) and cost the exact-boundary
# readings at 50 and 65. The band per weight, from `updateWeight`:
#     w    gain above          loss below        primed
#     45   1000+(45-80)*40=-400   (45-70)*30=-750   -550
#     50   -200                   -600              -400
#     55      0                   -450              -225
#     60    200                   -300               100
#     65    400                   -150               100
#     70    600                      0               500
#     75    800                      0               500
#     80   1000                      0               500
#     85   1200                      0               800
#     95   1600                      0               800
#    100   1800                      0               800
#    105   2000                      0               800
#    120   2600                      0               800
CALORIES_FOR_WEIGHT = {45: -550.0, 50: -400.0, 55: -225.0, 60: 100.0, 65: 100.0, 70: 500.0,
                       75: 500.0, 80: 500.0, 85: 800.0, 95: 800.0, 100: 800.0, 105: 800.0,
                       120: 800.0}


def weight_band(w):
    """updateWeight's neutral window at weight `w`: (loss-below, gain-above)."""
    return min(0.0, (w - 70) * 30.0), 1000.0 + (w - 80) * 40.0

STEAK = "Base.Steak"
# Coded constants, per game-second (Q1/Q2, defines.lua). The predictions are built from these.
K_HUNGER, K_HUNGER_EXERCISE, K_HUNGER_ASLEEP, K_HUNGER_WELLFED = 9.6e-6, 6.4e-6, 1.0e-6, 0.0
K_THIRST, K_THIRST_ASLEEP = 8.0e-6, 1.0e-6
K_CAL_IDLE, K_CAL_ASLEEP, K_CAL_RUN, K_CAL_WALK = 0.016, 0.003, 0.13, 0.078
K_CARBS, K_LIPIDS, K_PROTEINS = -0.0035, -0.00113, -0.00086
MOODLE_HUNGER = [0.10, 0.16, 0.26, 0.46, 0.71]      # expect levels 0,1,2,3,4 (> 0.15/.25/.45/.70)
MOODLE_THIRST = [0.10, 0.13, 0.26, 0.71, 0.85]      # expect levels 0,1,2,3,4 (> 0.12/.25/.70/.84)
BAND_WEIGHTS = [45, 50, 55, 65, 70, 75, 80, 85, 95, 100, 105]
BAND_EXPECTED = {45: "emaciated", 50: "emaciated", 55: "veryUnderweight", 65: "veryUnderweight",
                 70: "underweight", 75: "underweight", 80: None, 85: "overweight",
                 95: "overweight", 100: "obese", 105: "obese"}
# The snapshot's `traits` block also carries the four appetite/thirst traits; the band sweep
# must read only the five weight keys or a leftover HeartyAppetite would look like a band.
BAND_KEYS = ("emaciated", "veryUnderweight", "underweight", "overweight", "obese")
TRAIT_ROWS = [("HeartyAppetite", "appetite", 1.5), ("LightEater", "appetite", 0.75),
              ("HighThirst", "thirst", 2.0), ("LowThirst", "thirst", 0.5)]
SANDBOX_VALUES = [1, 5]                              # vs the default 3, which row 7's w80 is
SANDBOX_PREDICTED = {1: 2.0, 2: 1.6, 3: 1.0, 4: 0.8, 5: 0.65}   # inferred in the notes (I)
# Rows 3-6: the minimum number of CONSECUTIVE moving samples a movement fit needs. Consecutive,
# not merely present: `updateCalories` picks its constant per tick, so a slope taken over two
# moving samples with idle samples between them charges that idle time to the moving branch.
# exp03-20260910-045523 had 5 moving samples in one branch and only ONE adjacent pair, and the
# old count-only guard let a meaningless 1.2399 ratio into the tracked artifact.
MIN_CONTIGUOUS_MOVING = 4


def num(d, key):
    """The numeric at `key`, or None -- every read here can also be an error dict."""
    if isinstance(d, dict) and isinstance(d.get(key), (int, float)) and not isinstance(d.get(key), bool):
        return d[key]
    return None


def sub(d, key):
    return d[key] if isinstance(d, dict) and isinstance(d.get(key), dict) else {}


def as_int(v, default):
    """`StatsDecrease` is an ENUM option (`newEnumOption("StatsDecrease", 5, 3)`), so it has to
    go back over the bus as `3`, not `3.0` -- a float would reach `setValue` as a different
    Java type and could be refused silently."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return default
    return int(round(v))


def game_seconds(samples):
    """Elapsed game seconds per sample, measured from the FIRST sample of the list handed in.

    Relative, not absolute, on purpose: `worldAge` is ~1e4 hours on a used fixture, so an
    absolute game-second axis would be ~1e7 and the normal-equation determinant
    (`n*Sxx - Sx^2`) would lose most of its significant digits to cancellation in float64.
    Taking the origin here rather than inside `sample_window` also keeps a fit over the
    CONCATENATION of two windows (rows 3-6) on a single consistent axis."""
    wa = [num(s.get("v"), "worldAge") for s in samples]
    first = next((w for w in wa if w is not None), None)
    return [None if (w is None or first is None) else (w - first) * 3600.0 for w in wa]


def fit(samples, key):
    """Least squares of `key` against elapsed GAME seconds. The slope is the rate the coded
    constants predict; `endpoint` is the same number computed from the two ends only, kept
    because a disagreement between them is the signature of a step (a clamp, a moodle
    flipping mid-window) rather than of noise."""
    axis = game_seconds(samples)
    pts = [(x, s["v"][key]) for x, s in zip(axis, samples)
           if isinstance(x, (int, float))
           and isinstance(s.get("v"), dict)
           and isinstance(s["v"].get(key), (int, float))
           and not isinstance(s["v"].get(key), bool)]
    n = len(pts)
    if n < 3:
        return None
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxx = sum(p[0] * p[0] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    den = n * sxx - sx * sx
    if den == 0:
        return None
    slope = (n * sxy - sx * sy) / den
    inter = (sy - slope * sx) / n
    ybar = sy / n
    sstot = sum((p[1] - ybar) ** 2 for p in pts)
    ssres = sum((p[1] - (slope * p[0] + inter)) ** 2 for p in pts)
    span = pts[-1][0] - pts[0][0]
    return {"slope": slope, "n": n, "spanGameSeconds": round(span, 2),
            "r2": (round(1 - ssres / sstot, 6) if sstot > 0 else None),
            "first": pts[0][1], "last": pts[-1][1],
            "endpoint": ((pts[-1][1] - pts[0][1]) / span) if span else None,
            "mean": ybar}


def ratio(measured, predicted):
    if measured is None or predicted is None:
        return None
    if abs(predicted) < 1e-12:
        return "predicted 0" if abs(measured) < 1e-9 else "predicted 0, measured %.3g" % measured
    return round(measured / predicted, 4)


rec = fx.load("default")
run_id, run_dir = new_run_dir("exp03")
path = os.path.join(run_dir, "body.json")
tl = Timeline()
server = make_server(run_dir, rec)
clients = []
out = {"run_id": run_id, "rows": {}, "time_speed_fast": FAST,
       "constants": {"hungerIncrease": K_HUNGER, "hungerIncreaseWhenExercise/3": K_HUNGER_EXERCISE,
                     "hungerIncreaseWhileAsleep": K_HUNGER_ASLEEP,
                     "hungerIncreaseWhenWellFed": K_HUNGER_WELLFED,
                     "thirstIncrease": K_THIRST, "thirstSleepingIncrease": K_THIRST_ASLEEP,
                     "burnIdle": K_CAL_IDLE, "burnAsleep": K_CAL_ASLEEP, "burnRunning": K_CAL_RUN,
                     "burnWalking": K_CAL_WALK,
                     "macroDrain": {"carbs": K_CARBS, "lipids": K_LIPIDS, "proteins": K_PROTEINS}}}
weight0 = None
sandbox_before = None
traits_added = []
try:
    server.start()
    c, _ = make_client(run_dir, USER, server, rec)
    c.start()
    clients.append(c)
    c.wait_ready()
    tl.mark("session_ready")
    out["fixture"] = rec.get("name")
    out["build"] = server.build

    # ---- helpers -------------------------------------------------------------
    def srv(cmd, args="", timeout=25):
        return ask(server, cmd, args, timeout=timeout)

    def cli(cmd, args="", timeout=25):
        return ask(c, cmd, args, timeout=timeout)

    def timespeed(mult):
        ok, reply = server.rcon(f"settimespeed {mult}")
        return str(reply) if ok else f"rcon failed: {reply}"

    def snap():
        return srv("stats.get", USER, timeout=20)

    def prime(weight=None, hunger=None, thirst=None, calories=None, foodtimer=0.0):
        """Put the character in a known state before a rate window.

        `foodtimer` first and always: while the FOOD_EATEN moodle is up and the character is
        not exercising the hunger rate is `hungerIncreaseWhenWellFed` = 0 (Q2), so a leftover
        timer from an earlier row silently zeroes the very quantity being measured. The notes
        list this as a caveat the harness must handle.

        CALORIES BEFORE WEIGHT, then the trait refresh. The order is the whole point: each bus
        command is a round-trip of ~0.3 s of live server, so writing the weight while calories
        are still the PREVIOUS row's value leaves `updateWeight` a window to gain or lose
        against the wrong threshold. That is what put 60.000757 in row 7's w=60 window and
        50.000099 / 65.000099 in row 12 (exp03-20260910-045523), and at 50 and 65 the 1e-4 kg
        nudge is the difference between reading the band boundary and reading past it."""
        r = {}
        r["foodtimer"] = srv("foodtimer.set", f"{USER} {foodtimer}")
        w_int = int(weight if weight is not None else 80)
        cal = calories if calories is not None else CALORIES_FOR_WEIGHT.get(w_int, 500.0)
        r["calories"] = srv("nutrition.set", f"{USER} calories {cal}")
        r["caloriesRequested"] = cal
        r["weightBand"] = weight_band(w_int)     # (loss-below, gain-above) for the target weight
        if weight is not None:
            r["weight"] = srv("nutrition.set", f"{USER} weight {weight}")
            r["applytraits"] = srv("nutrition.applytraits", USER)
        for k in ("carbs", "lipids", "proteins"):
            r[k] = srv("nutrition.set", f"{USER} {k} {PRIME[k]}")
        h = PRIME["hunger"] if hunger is None else hunger
        t = PRIME["thirst"] if thirst is None else thirst
        r["stats"] = srv("stats.set", f"{USER} hunger {h} thirst {t}")
        return r

    def sample_window(seconds, every=SAMPLE_EVERY):
        """~1 Hz of `stats.get` on the server bus. One command per sample on purpose: every
        rate is d<value>/d<worldAge>, and splitting the clock read from the value reads across
        three bus round-trips would inject up to ~500 game-seconds of skew at settimespeed 30
        (see TK.bodySnapshot). `wall` is absolute so two concatenated windows stay on one
        axis; the game-second axis is derived from each sample's own `worldAge`."""
        samples, t0 = [], time.time()
        while time.time() - t0 < seconds:
            tick = time.time()
            v = snap()
            samples.append({"t": round(tick - t0, 2), "wall": round(tick, 3), "v": v})
            rest = every - (time.time() - tick)
            if rest > 0:
                time.sleep(rest)
        return samples

    def mean_of(samples, key):
        vals = [s["v"][key] for s in samples
                if isinstance(s.get("v"), dict)
                and isinstance(s["v"].get(key), (int, float))
                and not isinstance(s["v"].get(key), bool)]
        return (sum(vals) / len(vals)) if vals else None

    def predict(samples, ctx):
        w = mean_of(samples, "weight")
        h = mean_of(samples, "hunger")
        m = ctx.get("M", 1.0)
        appetite = ctx.get("appetite", 1.0)
        thirst_trait = ctx.get("thirstTrait", 1.0)
        wf = (w / 80.0) if w is not None else None
        hf = (1.0 - h) if h is not None else None
        mode = ctx.get("mode", "idle")
        if mode == "asleep":
            cal, hun, thi = K_CAL_ASLEEP, K_HUNGER_ASLEEP, K_THIRST_ASLEEP
        elif mode == "wellfed":
            cal, hun, thi = K_CAL_IDLE, K_HUNGER_WELLFED, K_THIRST
        elif mode == "running":
            cal, hun, thi = K_CAL_RUN, K_HUNGER_EXERCISE, K_THIRST
        elif mode == "walking":
            cal, hun, thi = K_CAL_WALK, K_HUNGER, K_THIRST
        else:
            cal, hun, thi = K_CAL_IDLE, K_HUNGER, K_THIRST
        return {"mode": mode, "meanWeight": w, "meanHunger": h, "statsDecreaseMultiplier": m,
                "appetiteTrait": appetite, "thirstTrait": thirst_trait,
                "calories": (-cal * wf) if wf is not None else None,
                "hunger": (hun * hf * m * appetite) if hf is not None else None,
                "thirst": thi * m * thirst_trait,
                "carbs": K_CARBS, "lipids": K_LIPIDS, "proteins": K_PROTEINS}

    FIT_KEYS = ("calories", "hunger", "thirst", "carbs", "lipids", "proteins", "weight",
                "endurance", "fatigue")

    def condition(label, seconds, ctx, samples=None):
        """A rate window: fits, predictions and the measured/predicted ratio per quantity."""
        if samples is None:
            samples = sample_window(seconds)
        fits = {k: fit(samples, k) for k in FIT_KEYS}
        pred = predict(samples, ctx)
        gs = [x for x in game_seconds(samples) if isinstance(x, (int, float))]
        wall = [s["wall"] for s in samples if isinstance(s.get("wall"), (int, float))]
        row = {"label": label, "context": ctx, "samples": len(samples),
               "wallSeconds": round((wall[-1] - wall[0]), 1) if len(wall) > 1 else 0,
               "gameSeconds": round(gs[-1] - gs[0], 1) if len(gs) > 1 else None,
               "gameHours": round((gs[-1] - gs[0]) / 3600.0, 4) if len(gs) > 1 else None,
               "measuredPerGameSecond": {k: (v["slope"] if v else None) for k, v in fits.items()},
               "predictedPerGameSecond": pred,
               "fits": fits,
               "raw": samples}
        row["measuredOverPredicted"] = {
            k: ratio(row["measuredPerGameSecond"].get(k), pred.get(k))
            for k in ("calories", "hunger", "thirst", "carbs", "lipids", "proteins")}
        # Moodle / posture flags actually observed across the window, so a row that silently
        # ran in the wrong branch is visible rather than showing up as a rate error.
        for flag in ("asleep", "running", "moving", "sprinting"):
            vals = {s["v"].get(flag) for s in samples if isinstance(s.get("v"), dict)}
            row.setdefault("observed", {})[flag] = sorted(str(v) for v in vals)
        lv = {}
        for s in samples:
            for k, v in sub(s.get("v"), "moodles").items():
                lv.setdefault(k, set()).add(v)
        row["observed"]["moodleLevels"] = {k: sorted(v) for k, v in lv.items()}
        row["observed"]["foodTimer"] = [num(samples[0].get("v"), "foodTimer"),
                                        num(samples[-1].get("v"), "foodTimer")] if samples else None
        return row

    def witnessed(label, seconds, ctx):
        """`condition`, with a CLIENT-side mirror read at both boundaries of the window.

        The client is authoritative for none of these values (every updater is server-gated,
        see the module docstring), so the mirror is a convergence witness and never a
        measurement: it says whether the client's copy tracked the server across the window.
        Taken at every accelerated boundary because exp03-20260910-045523 took it only at the
        session start, around row 1 and in rows 13/14 -- which is narrower than "at condition
        boundaries" and was reported as though it were not. The two extra round-trips sit
        OUTSIDE the fit: every rate is d<value>/d(that sample's own `worldAge`)."""
        before = cli("stats.get")
        row = condition(label, seconds, ctx)
        row["client_before"], row["client_after"] = before, cli("stats.get")
        return row

    def run_row(key, label, fn):
        """`fn` is handed the dict it must accumulate into, so a row that dies mid-way keeps
        whatever it had already read.

        Row 2 of exp03-20260910-045523 is why: it aborted inside its rate window, and the old
        code replaced the entire row with `{error, traceback}` -- discarding the `sleep_on`
        read-back and `heldAtWrite`, which were the only findings the row actually produced.
        The artifact still shows `r2_asleep` as three keys for that reason."""
        tl.mark("row_start", row=key)
        res = {}
        try:
            ret = fn(res)
        except Exception as e:                   # noqa: BLE001 - one row must not cost the rest
            res["error"] = f"{type(e).__name__}: {e}"
            res["traceback"] = traceback.format_exc()[-2000:]
            tl.mark("row_error", row=key, detail=str(e)[:120])
            print(res["traceback"])
        else:
            if ret is not res:                   # a row that built its own dict anyway
                if isinstance(ret, dict):
                    res.update(ret)
                else:
                    res["result"] = ret
        res["label"] = label
        out["rows"][key] = res
        save(path, out, tl, server)              # incremental: evidence survives a later wedge
        tl.mark("row_done", row=key)
        return res

    # ---- session context -----------------------------------------------------
    out["settimespeed_1_at_start"] = timespeed(1)
    out["time_at_start"] = srv("time.snapshot")
    out["players"] = srv("players")
    out["server_snapshot_at_start"] = snap()
    out["client_snapshot_at_start"] = cli("stats.get")
    weight0 = num(out["server_snapshot_at_start"], "weight")
    # The one sandbox multiplier on hunger/thirst (Q2). Reading it here also captures the
    # value to put back in `finally`, and -- if Kahlua exposes the getter -- settles the
    # inferred key->value mapping outright, before any rate is measured.
    out["sandbox_StatsDecrease"] = srv("sandbox.set", "StatsDecrease")
    sandbox_before = num(out["sandbox_StatsDecrease"], "before")
    out["sandbox_Nutrition"] = srv("sandbox.set", "Nutrition")
    tl.mark("context", weight=weight0, statsDecrease=sandbox_before,
            statsApi=(out["server_snapshot_at_start"].get("statsApi")
                      if isinstance(out["server_snapshot_at_start"], dict) else "?"))

    # ---- row 1: idle baseline at settimespeed 1 -------------------------------
    # The only condition that runs at real speed, because it is the only one that has to
    # answer an ABSOLUTE question: S, the fixture's game-seconds per real second. Everything
    # else is a ratio and cancels the clock.
    def row1(r):
        r.update({"settimespeed": timespeed(1), "prime": prime(weight=80)})
        time.sleep(SETTLE)
        r["client_before"] = cli("stats.get")
        samples = sample_window(BASELINE_SECONDS)
        r.update(condition("idle, settimespeed 1", BASELINE_SECONDS, {"mode": "idle", "M": 1.0},
                           samples=samples))
        r["client_after"] = cli("stats.get")
        # S from the world clock itself, then cross-checked against the calorie burn -- the
        # two are independent (one is GameTime, the other is updateCalories' own dt).
        axis = game_seconds(samples)
        pairs = [(s["wall"], x) for s, x in zip(samples, axis)
                 if isinstance(x, (int, float)) and isinstance(s.get("wall"), (int, float))]
        if len(pairs) > 1:
            dwall = pairs[-1][0] - pairs[0][0]
            r["S_fromWorldClock"] = round((pairs[-1][1] - pairs[0][1]) / dwall, 4) if dwall else None
        cal = fit(samples, "calories")
        w = mean_of(samples, "weight")
        if cal and w and r.get("S_fromWorldClock"):
            per_real = cal["slope"] * r["S_fromWorldClock"]
            r["caloriesPerRealSecond"] = round(per_real, 5)
            r["S_fromCalorieBurn"] = round(abs(per_real) / (K_CAL_IDLE * w / 80.0), 4)
        return r

    b = run_row("r1_idle_baseline", "row 1: idle baseline, settimespeed 1, S", row1)
    S = b.get("S_fromWorldClock")
    out["S_gameSecondsPerRealSecond"] = S
    # Every ratio in the notes' scale-free table, taken from the baseline window.
    base_rate = b.get("measuredPerGameSecond", {})
    bh = b.get("predictedPerGameSecond", {}).get("meanHunger")
    bw = b.get("predictedPerGameSecond", {}).get("meanWeight")
    out["baseline_ratios"] = {
        "dThirst/dHunger": {"measured": ratio(base_rate.get("thirst"), base_rate.get("hunger")),
                            "predicted": round(0.8333 / (1 - bh), 4) if bh is not None else None},
        "dCalories/dHunger": {"measured": ratio(abs(base_rate["calories"]), base_rate["hunger"])
                              if base_rate.get("calories") and base_rate.get("hunger") else None,
                              "predicted": round(1666.7 * (bw / 80.0) / (1 - bh), 1)
                              if (bh is not None and bw is not None) else None},
        "dCarbs/dCalories": {"measured": ratio(base_rate.get("carbs"), base_rate.get("calories")),
                             "predicted": round(0.21875 / (bw / 80.0), 5) if bw else None}}

    # ---- row 7: weight scaling ------------------------------------------------
    # `updateCalories @115 L104` scales every branch by getWeight()/80, so the burn ratio is
    # the cleanest single-variable test in the slice: nothing else in the formula moves.
    def row7(r):
        r.update({"settimespeed": timespeed(FAST), "windows": []})
        for w in (80, 100, 120, 60):
            p = prime(weight=w)
            time.sleep(SETTLE)
            row = witnessed(f"idle, weight {w}", WINDOW_SECONDS, {"mode": "idle", "M": 1.0})
            row["prime"], row["requestedWeight"] = p, w
            r["windows"].append(row)
        ref = next((x for x in r["windows"] if x["requestedWeight"] == 80), None)
        base = ref["measuredPerGameSecond"].get("calories") if ref else None
        r["burnRatiosVs80"] = [
            {"weight": x["requestedWeight"],
             "measuredWeight": x["predictedPerGameSecond"].get("meanWeight"),
             "caloriesPerGameSecond": x["measuredPerGameSecond"].get("calories"),
             "measuredRatio": ratio(x["measuredPerGameSecond"].get("calories"), base),
             "predictedRatio": round((x["predictedPerGameSecond"].get("meanWeight") or 0) / 80.0
                                     / ((ref["predictedPerGameSecond"].get("meanWeight") or 80) / 80.0), 4)
             if ref else None}
            for x in r["windows"]]
        r["settimespeed_1"] = timespeed(1)
        return r

    run_row("r7_weight_scaling", "row 7: burn scales with getWeight()/80", row7)

    # ---- row 11: moodle sweep -------------------------------------------------
    # Deliberately at settimespeed 1, not 30. This row is not a rate: it reads a threshold at a
    # pinned stat value, and the probe values sit 0.01 above the coded boundaries. At speed 30
    # hunger drifts ~4.5e-3 per second of wall time, so the settle wait alone would carry a
    # probe across its own boundary; at speed 1 the drift is ~1.5e-4/s and cannot.
    def row11(r):
        r.update({"settimespeed": timespeed(1), "thresholdsFromCode":
                  {"HUNGRY": [0.15, 0.25, 0.45, 0.70], "THIRST": [0.12, 0.25, 0.70, 0.84]},
                  "hunger": [], "thirst": []})
        srv("foodtimer.set", f"{USER} 0")
        for i, v in enumerate(MOODLE_HUNGER):
            srv("stats.set", f"{USER} hunger {v} thirst 0.05")
            time.sleep(SETTLE)
            s = snap()
            r["hunger"].append({"set": v, "readBack": num(s, "hunger"),
                                "level": sub(s, "moodles").get("hungry"), "expected": i,
                                "maxWeight": num(s, "maxWeight")})
        for i, v in enumerate(MOODLE_THIRST):
            srv("stats.set", f"{USER} thirst {v} hunger 0.05")
            time.sleep(SETTLE)
            s = snap()
            r["thirst"].append({"set": v, "readBack": num(s, "thirst"),
                                "level": sub(s, "moodles").get("thirst"), "expected": i,
                                "maxWeight": num(s, "maxWeight")})
        r["hungerLevelsMatch"] = all(x["level"] == x["expected"] for x in r["hunger"])
        r["thirstLevelsMatch"] = all(x["level"] == x["expected"] for x in r["thirst"])
        srv("stats.set", f"{USER} hunger {PRIME['hunger']} thirst {PRIME['thirst']}")
        return r

    run_row("r11_moodle_sweep", "row 11: HUNGRY / THIRST moodle thresholds", row11)

    # ---- row 12: weight bands + the trait-refresh latency ----------------------
    # Two separate questions. (a) Do the boundaries sit where `applyTraitFromWeight
    # @65-@217 L253-L266` says -- inclusive at 50 and at 100, with an OPEN normal interval
    # (75, 85)? Forced refresh, so this is a pure reading of the comparisons. (b) How long does
    # vanilla take to notice, given the >=2000-updateWeight counter (`@329-@357 L200-L203`)?
    # Measured once, unforced, and time-speed independent: the counter is per update call, not
    # per game-second.
    def row12(r):
        r.update({"settimespeed": timespeed(1), "bands": []})
        # (b) first, from a clean slate: weight 80 (no band) -> 105 (Obese), unforced.
        # Neutral at BOTH ends of the probe: 800 is under 80's gain threshold (1000) and over
        # 105's loss threshold (0), so neither the start weight nor the target can drift.
        srv("nutrition.set", f"{USER} calories {CALORIES_FOR_WEIGHT[105]}")
        srv("nutrition.set", f"{USER} weight 80")
        srv("nutrition.applytraits", USER)
        t0 = time.time()
        srv("nutrition.set", f"{USER} weight 105")
        latency, polls = None, []
        while time.time() - t0 < 60:
            s = snap()
            has = sub(s, "traits").get("obese")
            polls.append({"t": round(time.time() - t0, 2), "obese": has,
                          "weight": num(s, "weight")})
            if has is True:
                latency = round(time.time() - t0, 2)
                break
            time.sleep(1.0)
        r["refreshLatency"] = {"secondsToObese": latency, "cappedAt": 60, "polls": polls,
                               "note": "unforced; the counter is per updateWeight call, so this "
                                       "is a server-tick-rate measurement, not a game-time one"}
        # (a) the sweep, forced -- and PRIMED PER WEIGHT. `prime` writes the calorie value
        # `CALORIES_FOR_WEIGHT` holds for this weight BEFORE the weight itself, so
        # `updateWeight` has no threshold to cross between the weight write and the comparison
        # `applyTraitFromWeight` makes. Without it the low bands drift ~1e-4 kg past their own
        # boundary before the trait is computed, and the exact-boundary question at 50 and 65 --
        # which is the whole reason those two weights are in the sweep -- cannot be answered.
        # exp03-20260910-045523 predates this and left 50/65 unmeasured for exactly that reason.
        for w in BAND_WEIGHTS:
            p = prime(weight=w)
            applied = p.get("applytraits")
            s = snap()
            traits = sub(s, "traits")
            on = sorted(k for k in BAND_KEYS if traits.get(k) is True)
            read_back = num(s, "weight")
            r["bands"].append({"weight": w, "readBack": read_back,
                               "traitsOn": on, "expected": BAND_EXPECTED[w],
                               "match": (on == ([BAND_EXPECTED[w]] if BAND_EXPECTED[w] else [])),
                               "maxWeight": num(s, "maxWeight"),
                               "primedCalories": p.get("caloriesRequested"),
                               "caloriesAtRead": num(s, "calories"),
                               "weightBand": weight_band(w),
                               # The reading is only about the BOUNDARY if the weight is still
                               # exactly on it; otherwise the comparison never saw it.
                               "heldExactly": (read_back is not None and abs(read_back - w) < 1e-6),
                               "applyRoute": applied.get("applied") if isinstance(applied, dict) else None})
        r["allBandsMatch"] = all(x["match"] for x in r["bands"])
        r["allWeightsHeldExactly"] = all(x["heldExactly"] for x in r["bands"])
        # Put the band traits back to none before any later row reads them.
        srv("nutrition.set", f"{USER} weight 80")
        r["restore"] = srv("nutrition.applytraits", USER)
        return r

    run_row("r12_weight_bands", "row 12: weight -> band traits, and the refresh latency", row12)

    # ---- row 8: the FOOD_EATEN gate --------------------------------------------
    # `hungerIncreaseWhenWellFed = 0` (defines.lua:15), so the prediction is not "a small
    # slope" but EXACTLY flat -- the notes flag this and say to assert equality. The eat goes
    # through ISEatFoodAction (the real MP path, completed server-side) and the item is spawned
    # server-side by RCON, because a client-spawned item makes the server log a SyncItemFields
    # NPE (slice 01).
    def row8(r):
        r.update({"settimespeed": timespeed(1)})
        prime(weight=80)
        time.sleep(SETTLE)
        r["before"] = snap()
        ok, reply = server.rcon(f'additem "{USER}" "{STEAK}" 1')
        r["spawn"] = str(reply) if ok else f"rcon failed: {reply}"
        time.sleep(SPAWN_WAIT)
        r["eat_action"] = cli("eat.action", f"{STEAK} 1.0", timeout=30)
        time.sleep(6.0)                       # the timed action completes on the server
        r["after_eat"] = snap()
        r["foodTimerAfterEat"] = num(r["after_eat"], "foodTimer")
        r["foodEatenLevelAfterEat"] = sub(r["after_eat"], "moodles").get("foodEaten")
        # The timer decays by 1 x getMultiplier() per BodyDamage.Update tick (Q5), i.e. on a
        # frame clock rather than a game-time one -- MEASURED at 1438 units per REAL second at
        # settimespeed 30 (exp03-20260910-045523, this row's own window: 197 596.8 -> 186 096.2
        # across its first 8 s), so >34 000 across a 24 s window. A real eat fills it with at
        # most 11000 (`JustAteFood` cap), which would expire mid-window and take the gate with
        # it. Topped up well past that so the window measures the GATE and not its expiry;
        # `foodTimerAfterEat` above is the untouched reading of the real path.
        r["foodTimerDecayNote"] = ("1438 units/real-s at settimespeed 30 (measured in this "
                                   "row's own window, exp03-20260910-045523); 11000 from a "
                                   "real eat lasts under 8 real seconds there")
        r["foodtimer_topup"] = srv("foodtimer.set", f"{USER} 200000")
        srv("stats.set", f"{USER} hunger {PRIME['hunger']} thirst {PRIME['thirst']}")
        r["settimespeed_fast"] = timespeed(FAST)
        time.sleep(SETTLE)
        r.update(witnessed("idle, FOOD_EATEN >= 1", WINDOW_SECONDS, {"mode": "wellfed", "M": 1.0}))
        r["settimespeed_1"] = timespeed(1)
        # The equality assertion is only meaningful if the gate was up for EVERY sample. In
        # exp03-20260910-045523 the queued ISEatFoodAction completed 9 samples into the window,
        # so the window straddled the gate's edge and the whole-window flag came out `false` on
        # a segment whose gated half was in fact bit-exactly flat. Straddled -> no answer, and
        # the per-sample series in `raw` is what carries the finding.
        seen = sub(r.get("observed"), "moodleLevels").get("foodEaten") or []
        r["foodEatenLevelsAcrossWindow"] = seen
        hf = r.get("fits", {}).get("hunger")
        if seen and all(isinstance(v, int) and not isinstance(v, bool) and v >= 1 for v in seen):
            r["hungerExactlyFlat"] = (hf is not None and hf["first"] == hf["last"])
        else:
            r["hungerExactlyFlat"] = None
            r["hungerExactlyFlatReason"] = (
                "n/a: FOOD_EATEN was not >= 1 for every sample (levels seen: %s), so the window "
                "straddles the gate's edge -- split `raw` at the transition instead" % (seen,))
        r["clear"] = srv("foodtimer.set", f"{USER} 0")
        return r

    run_row("r8_food_eaten", "row 8: hunger freezes while FOOD_EATEN >= 1", row8)

    # ---- row 14: a client-side weight write -------------------------------------
    # New prediction from the code map: `updateWeight @317-@320 L198` puts the
    # `GameClient.client` early-out BEFORE setWeight and before applyTraitFromWeight, so a
    # client write should survive only until the next PlayerStatsPacket, and hasTrait("Obese")
    # should never turn true on this side no matter what the client's weight says.
    def row14(r):
        r.update({"server_before": snap()})
        r["client_before"] = cli("stats.get")
        r["client_set_105"] = cli("nutrition.set", "weight 105")
        r["client_immediately"] = cli("stats.get")
        r["clientWeightImmediately"] = num(r["client_immediately"], "weight")
        r["clientObeseImmediately"] = sub(r["client_immediately"], "traits").get("obese")
        time.sleep(SYNC_WAIT)
        r["client_after_sync"] = cli("stats.get")
        r["server_after_sync"] = snap()
        r["clientWeightAfterSync"] = num(r["client_after_sync"], "weight")
        r["clientObeseAfterSync"] = sub(r["client_after_sync"], "traits").get("obese")
        r["serverWeightAfterSync"] = num(r["server_after_sync"], "weight")
        sw = r["serverWeightAfterSync"]
        r["clientWriteReverted"] = (r["clientWeightAfterSync"] is not None and sw is not None
                                    and abs(r["clientWeightAfterSync"] - sw) < 0.01)
        return r

    run_row("r14_client_weight", "row 14: client setWeight, and applyTraitFromWeight client-side",
            row14)

    # ---- row 13: MP authority regression ----------------------------------------
    def row13(r):
        r.update({"server_set_0.3": srv("stats.set", f"{USER} hunger 0.3")})
        time.sleep(SYNC_WAIT)
        r["client_set_0.9"] = cli("stats.set", "hunger 0.9")
        polls, t0 = [], time.time()
        while time.time() - t0 < 6.0:
            s = cli("stats.get")
            polls.append({"t": round(time.time() - t0, 2), "clientHunger": num(s, "hunger")})
            if num(s, "hunger") is not None and num(s, "hunger") < 0.8:
                break
            time.sleep(0.4)
        r["clientPolls"] = polls
        r["revertedAfterSeconds"] = polls[-1]["t"] if polls and polls[-1]["clientHunger"] is not None \
            and polls[-1]["clientHunger"] < 0.8 else None
        r["server_after"] = snap()
        r["serverHungerAfter"] = num(r["server_after"], "hunger")
        return r

    run_row("r13_mp_regression", "row 13: a client stats.set reverts within the 1 Hz push", row13)

    # ---- row 10: sandbox StatsDecrease -------------------------------------------
    # The mapping 1 -> 2.0 ... 5 -> 0.65 is INFERRED in the notes (pzdis does not print the
    # tableswitch). Two independent settlements are collected: the multiplier the server itself
    # reports through getStatsDecreaseMultiplier (if Kahlua exposes it), and the measured
    # hunger/thirst rates. Calories must NOT move -- updateCalories reads no sandbox term.
    def row10(r):
        r.update({"windows": [], "predictedMapping": SANDBOX_PREDICTED, "before": sandbox_before})
        # The whole key->value map in five bus calls: the server exposes
        # getStatsDecreaseMultiplier(), so the mapping can be READ rather than inferred from
        # rates. The two measured windows below then confirm the read is the number the stat
        # updaters actually use.
        r["multiplierByValue"] = []
        for v in (1, 2, 3, 4, 5):
            res = srv("sandbox.set", f"StatsDecrease {v}")
            r["multiplierByValue"].append({
                "value": v,
                "optionAfter": res.get("after") if isinstance(res, dict) else None,
                "multiplier": res.get("statsDecreaseMultiplierAfter") if isinstance(res, dict) else None,
                "predicted": SANDBOX_PREDICTED.get(v),
                "route": res.get("route") if isinstance(res, dict) else None})
        r["mappingMatchesNotes"] = all(
            x["multiplier"] is not None and abs(x["multiplier"] - x["predicted"]) < 1e-6
            for x in r["multiplierByValue"])
        for v in SANDBOX_VALUES:
            setres = srv("sandbox.set", f"StatsDecrease {v}")
            prime(weight=80)
            timespeed(FAST)
            time.sleep(SETTLE)
            m = SANDBOX_PREDICTED.get(v, 1.0)
            row = witnessed(f"idle, StatsDecrease {v}", WINDOW_SECONDS, {"mode": "idle", "M": m})
            row["sandbox"] = setres
            row["reportedMultiplier"] = (setres.get("statsDecreaseMultiplierAfter")
                                         if isinstance(setres, dict) else None)
            row["requestedValue"] = v
            timespeed(1)
            r["windows"].append(row)
        r["restore"] = srv("sandbox.set", f"StatsDecrease {as_int(sandbox_before, 3)}")
        return r

    run_row("r10_sandbox_statsdecrease", "row 10: StatsDecrease 1 / 5 vs the default 3", row10)

    # ---- row 9: appetite / thirst traits -------------------------------------------
    def row9(r):
        r.update({"windows": []})
        for name, kind, factor in TRAIT_ROWS:
            add = srv("trait.set", f"{USER} {name} add")
            if isinstance(add, dict) and add.get("after") is True:
                traits_added.append(name)
            prime(weight=80)
            timespeed(FAST)
            time.sleep(SETTLE)
            ctx = {"mode": "idle", "M": 1.0}
            ctx["appetite" if kind == "appetite" else "thirstTrait"] = factor
            row = witnessed(f"idle, trait {name}", WINDOW_SECONDS, ctx)
            row["trait_add"], row["trait"], row["expectedFactor"], row["affects"] = add, name, factor, kind
            timespeed(1)
            row["trait_remove"] = srv("trait.set", f"{USER} {name} remove")
            if isinstance(row["trait_remove"], dict) and row["trait_remove"].get("after") is False:
                if name in traits_added:
                    traits_added.remove(name)
            r["windows"].append(row)
        return r

    run_row("r9_traits", "row 9: HeartyAppetite / LightEater / HighThirst / LowThirst", row9)

    # ---- row 2: asleep ---------------------------------------------------------------
    def row2(r):
        r.update({"sleep_on": srv("player.sleep", f"{USER} true")})
        held = isinstance(r["sleep_on"], dict) and r["sleep_on"].get("after") is True
        r["heldAtWrite"] = held
        if not held:
            r["result"] = "n/a: setAsleep(true) did not hold on the server"
            return r
        prime(weight=80)
        timespeed(FAST)
        time.sleep(SETTLE)
        r.update(witnessed("asleep", WINDOW_SECONDS, {"mode": "asleep", "M": 1.0}))
        timespeed(1)
        r["sleep_off"] = srv("player.sleep", f"{USER} false")
        # Persistence, not just the write. `heldAtWrite` is an immediate read-back and says
        # nothing about whether the flag survived the window; `player.sleep`'s own `before`
        # field is that reading, for free, at the far end of it. (In exp03-20260910-045523 the
        # only surviving instance of it -- teardown's -- was already `false`.)
        r["asleepAtWindowEnd"] = (r["sleep_off"].get("before")
                                  if isinstance(r["sleep_off"], dict) else None)
        r["asleepPersisted"] = (r["asleepAtWindowEnd"] is True)
        # The three asleep/idle ratios the notes predict, computed against row 7's w80 window.
        w80 = None
        r7 = out["rows"].get("r7_weight_scaling", {})
        for x in r7.get("windows", []):
            if x.get("requestedWeight") == 80:
                w80 = x
        if w80:
            ref, mine = w80["measuredPerGameSecond"], r["measuredPerGameSecond"]
            r["ratiosVsIdle"] = {
                "calories": {"measured": ratio(mine.get("calories"), ref.get("calories")),
                             "predicted": round(K_CAL_ASLEEP / K_CAL_IDLE, 5)},
                "hunger": {"measured": ratio(mine.get("hunger"), ref.get("hunger")),
                           "predicted": round(K_HUNGER_ASLEEP / K_HUNGER, 5)},
                "thirst": {"measured": ratio(mine.get("thirst"), ref.get("thirst")),
                           "predicted": round(K_THIRST_ASLEEP / K_THIRST, 5)}}
        return r

    run_row("r2_asleep", "row 2: setAsleep(true) -> the 0.003 burn branch", row2)

    # ---- rows 3-6: movement, ONE attempt --------------------------------------------
    # The ruling caps this at a single attempt. The client is the only side that can start the
    # walk (the server's copy of a remote player's movement comes from this client's position
    # updates), and the reading that decides the row is whether the SERVER's snapshot ever
    # reports `moving` true -- that is the flag `updateCalories @125 L106` actually branches on.
    def row3_6(r):
        r.update({"attempt": "client ISWalkToTimedAction + setRunning(true), sampled server-side",
                  "rows_5_6": "n/a: no trivially reliable automation. Row 5 needs a live "
                              "SwipeStatePlayer (a real attack against a target); row 6 needs a "
                              "queued ISBuildAction with materials and a build site. Neither is "
                              "one command, and the ruling caps this block at one attempt."})
        prime(weight=80)
        timespeed(FAST)
        time.sleep(SETTLE)
        samples = []
        for dx in (14, -14, 14, -14):
            r.setdefault("walks", []).append(cli("player.walk", f"{dx} 0 run", timeout=25))
            samples += sample_window(9.0, every=0.7)
        r["stop"] = cli("player.stop")
        timespeed(1)
        r["allSamples"] = samples          # kept whole: the per-branch fits below subset it

        def branch(want_running):
            """INDICES, not samples: contiguity is the property that decides the fit below."""
            return [i for i, s in enumerate(samples) if isinstance(s.get("v"), dict)
                    and s["v"].get("moving") is True
                    and (s["v"].get("running") is True) == want_running]

        def longest_run(idx):
            """The longest stretch of CONSECUTIVE sample indices in `idx`."""
            best, cur = [], []
            for i in idx:
                cur = cur + [i] if (cur and i == cur[-1] + 1) else [i]
                if len(cur) > len(best):
                    best = cur
            return best

        walking, running = branch(False), branch(True)
        r["serverSawMoving"] = len(walking) + len(running)
        r["serverSawWalking"], r["serverSawRunning"] = len(walking), len(running)
        r["movingSampleIndices"] = {"walking": walking, "running": running}
        r7 = out["rows"].get("r7_weight_scaling", {})
        w80 = next((x for x in r7.get("windows", []) if x.get("requestedWeight") == 80), None)
        # Fitted per branch, never over the union: `updateCalories` picks 0.13 / 0.078 / 0.016
        # from (IsRunning, isPlayerMoving) at each tick, so a mixed window averages three
        # different constants and measures none of them.
        #
        # And fitted only over CONSECUTIVE samples of a branch. A count-only guard is not
        # enough: exp03-20260910-045523 had 5 walking samples at indices 0,1,13,27,39 -- one
        # adjacent pair and three isolated ones -- and a least-squares line through them
        # charges ~35 s of idle time to the walking branch. It passed the old `len < 4` test
        # and put `caloriesRatioVsIdle.measured = 1.2399` (against a predicted 4.875) into the
        # tracked artifact, a number that measures the sampling gaps and nothing else.
        for name, idx, mode, k in (("row3_walking", walking, "walking", K_CAL_WALK),
                                   ("row4_running", running, "running", K_CAL_RUN)):
            best = longest_run(idx)
            if len(best) < MIN_CONTIGUOUS_MOVING:
                r[name] = {"result": "n/a: %d server samples in this branch, longest CONSECUTIVE "
                                     "run %d (need >= %d). A slope over non-adjacent moving "
                                     "samples charges the idle time between them to the moving "
                                     "branch; one attempt only, per the ruling."
                                     % (len(idx), len(best), MIN_CONTIGUOUS_MOVING),
                           "samplesInBranch": len(idx), "longestConsecutiveRun": len(best),
                           "sampleIndices": idx, "caloriesRatioVsIdle": None}
                continue
            row = condition(name, 0, {"mode": mode, "M": 1.0},
                            samples=[samples[i] for i in best])
            row["samplesInBranch"], row["longestConsecutiveRun"] = len(idx), len(best)
            row["sampleIndices"] = best
            if w80:
                row["caloriesRatioVsIdle"] = {
                    "measured": ratio(row["measuredPerGameSecond"].get("calories"),
                                      w80["measuredPerGameSecond"].get("calories")),
                    "predicted": round(k / K_CAL_IDLE, 4)}
            r[name] = row
        if not walking and not running:
            r["result"] = ("n/a: the server never observed isPlayerMoving() true, so no sample "
                           "sits in a moving branch of updateCalories")
        return r

    run_row("r3_6_movement", "rows 3-6: walking / running / swiping / timed action", row3_6)

    # ---- report-ready summary ---------------------------------------------------------
    def brief(row):
        if not isinstance(row, dict) or "measuredPerGameSecond" not in row:
            return None
        return {"label": row.get("label"), "samples": row.get("samples"),
                "wallSeconds": row.get("wallSeconds"), "gameHours": row.get("gameHours"),
                "measured": {k: row["measuredPerGameSecond"].get(k)
                             for k in ("calories", "hunger", "thirst", "carbs")},
                "predicted": {k: row["predictedPerGameSecond"].get(k)
                              for k in ("calories", "hunger", "thirst", "carbs")},
                "ratio": row.get("measuredOverPredicted"),
                "r2": {k: (row["fits"].get(k) or {}).get("r2") for k in ("calories", "hunger", "thirst")}}

    summary = {"S": S, "baselineRatios": out.get("baseline_ratios"),
               "weight0": weight0, "statsDecreaseAtStart": sandbox_before,
               "r1": brief(out["rows"].get("r1_idle_baseline", {}))}
    summary["r7"] = {"burnRatiosVs80": out["rows"].get("r7_weight_scaling", {}).get("burnRatiosVs80"),
                     "windows": [brief(x) for x in out["rows"].get("r7_weight_scaling", {}).get("windows", [])]}
    r11 = out["rows"].get("r11_moodle_sweep", {})
    summary["r11"] = {"hunger": r11.get("hunger"), "thirst": r11.get("thirst"),
                      "hungerLevelsMatch": r11.get("hungerLevelsMatch"),
                      "thirstLevelsMatch": r11.get("thirstLevelsMatch")}
    r12 = out["rows"].get("r12_weight_bands", {})
    summary["r12"] = {"allBandsMatch": r12.get("allBandsMatch"),
                      "bands": [{k: x.get(k) for k in ("weight", "traitsOn", "expected", "match", "maxWeight")}
                                for x in r12.get("bands", [])],
                      "refreshLatencySeconds": sub(r12, "refreshLatency").get("secondsToObese")}
    r8 = out["rows"].get("r8_food_eaten", {})
    summary["r8"] = {"foodTimerAfterEat": r8.get("foodTimerAfterEat"),
                     "foodEatenLevelAfterEat": r8.get("foodEatenLevelAfterEat"),
                     "hungerExactlyFlat": r8.get("hungerExactlyFlat"), "window": brief(r8)}
    summary["r14"] = {k: out["rows"].get("r14_client_weight", {}).get(k) for k in
                      ("clientWeightImmediately", "clientObeseImmediately", "clientWeightAfterSync",
                       "clientObeseAfterSync", "serverWeightAfterSync", "clientWriteReverted")}
    summary["r13"] = {k: out["rows"].get("r13_mp_regression", {}).get(k) for k in
                      ("revertedAfterSeconds", "serverHungerAfter", "clientPolls")}
    summary["r10_mapping"] = out["rows"].get("r10_sandbox_statsdecrease", {}).get("multiplierByValue")
    summary["r10_mappingMatchesNotes"] = out["rows"].get("r10_sandbox_statsdecrease", {}).get("mappingMatchesNotes")
    summary["r10"] = [{"value": x.get("requestedValue"), "reportedMultiplier": x.get("reportedMultiplier"),
                       "predictedMultiplier": SANDBOX_PREDICTED.get(x.get("requestedValue")),
                       **(brief(x) or {})}
                      for x in out["rows"].get("r10_sandbox_statsdecrease", {}).get("windows", [])]
    summary["r9"] = [{"trait": x.get("trait"), "affects": x.get("affects"),
                      "expectedFactor": x.get("expectedFactor"),
                      "traitHeld": (x.get("trait_add") or {}).get("after"),
                      "route": (x.get("trait_add") or {}).get("route"), **(brief(x) or {})}
                     for x in out["rows"].get("r9_traits", {}).get("windows", [])]
    r2 = out["rows"].get("r2_asleep", {})
    summary["r2"] = {"heldAtWrite": r2.get("heldAtWrite"), "result": r2.get("result"),
                     "ratiosVsIdle": r2.get("ratiosVsIdle"), "window": brief(r2)}
    r36 = out["rows"].get("r3_6_movement", {})
    summary["r3_6"] = {"serverSawMoving": r36.get("serverSawMoving"),
                       "serverSawWalking": r36.get("serverSawWalking"),
                       "serverSawRunning": r36.get("serverSawRunning"),
                       "result": r36.get("result"), "rows_5_6": r36.get("rows_5_6"),
                       "row3_walking": {"ratio": sub(r36, "row3_walking").get("caloriesRatioVsIdle"),
                                        "result": sub(r36, "row3_walking").get("result"),
                                        "window": brief(sub(r36, "row3_walking"))},
                       "row4_running": {"ratio": sub(r36, "row4_running").get("caloriesRatioVsIdle"),
                                        "result": sub(r36, "row4_running").get("result"),
                                        "window": brief(sub(r36, "row4_running"))}}
    out["summary"] = summary
except Exception as e:                   # noqa: BLE001 - a long experiment must keep the rows
    out["error"] = f"{type(e).__name__}: {e}"   # it already has; the traceback is recorded
    out["traceback"] = traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
    print(out["traceback"])
finally:
    # settimespeed is a WORLD change and must not outlive the run, whatever went wrong above.
    try:
        ok_rcon, reply = server.rcon("settimespeed 1")
        out["settimespeed_restored"] = str(reply) if ok_rcon else f"rcon failed: {reply}"
        tl.mark("settimespeed_restored", ok=ok_rcon)
    except Exception as e:                       # noqa: BLE001 - teardown path, never raise
        out["settimespeed_restored"] = f"{type(e).__name__}: {e}"
    # rcon's own reply is the admin command echoing back, not the world's state. `time.snapshot`
    # reads getGameTime() on the server, so this is the read-back that actually evidences the
    # one WORLD change this run makes having been put back.
    try:
        out["time_after_restore"] = ask(server, "time.snapshot", timeout=15)
    except Exception as e:                       # noqa: BLE001 - teardown path, never raise
        out["time_after_restore"] = f"{type(e).__name__}: {e}"
    # Character + world state this run moved, put back in the reverse order it was taken. The
    # session runs against a copy of the fixture restored into this run dir, so none of it can
    # leak into testing/fixtures/ -- the standing rule is to restore anyway, and a restore that
    # reports its read-back is also the last check that the harness commands still answer.
    for label, cmd, args in (
            ("asleep", "player.sleep", f"{USER} false"),
            ("weight", "nutrition.set", f"{USER} weight {weight0 if weight0 is not None else 80}"),
            ("weight_traits", "nutrition.applytraits", USER),
            ("foodtimer", "foodtimer.set", f"{USER} 0"),
            ("sandbox", "sandbox.set", f"StatsDecrease {as_int(sandbox_before, 3)}")):
        try:
            out.setdefault("restored", {})[label] = ask(server, cmd, args, timeout=15)
        except Exception as e:                   # noqa: BLE001 - teardown path, never raise
            out.setdefault("restored", {})[label] = f"{type(e).__name__}: {e}"
    for name in list(traits_added):
        try:
            out.setdefault("restored", {}).setdefault("traits", {})[name] = ask(
                server, "trait.set", f"{USER} {name} remove", timeout=15)
        except Exception as e:                   # noqa: BLE001 - teardown path, never raise
            out.setdefault("restored", {}).setdefault("traits", {})[name] = f"{type(e).__name__}: {e}"
    try:
        out["final_server_snapshot"] = ask(server, "stats.get", USER, timeout=15)
        out["final_client_snapshot"] = ask(clients[0], "stats.get", timeout=15) if clients else "no client"
    except Exception as e:                       # noqa: BLE001 - teardown path, never raise
        out["final_server_snapshot"] = f"{type(e).__name__}: {e}"
    save(path, out, tl, server)          # evidence on disk before the shutdown can go wrong
    try:
        teardown(tl, server, clients)    # graceful: the quit/stop rcs land in the timeline
    finally:
        hard_kill(server, clients)       # guaranteed, whatever teardown did
        # Case-insensitive by rule (slice 01: a case-sensitive grep produced a false negative
        # in exactly the flattering direction).
        try:
            log = os.path.join(run_dir, "server-stdout.log")
            hits = {"PlayerStats": [], "applyTraitFromWeight": [], "SyncItemFields": [],
                    "Nutrition": [], "setAsleep": []}
            needles = [(key, key.lower()) for key in hits]
            with open(log, encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    low = line.lower()
                    for key, needle in needles:
                        if needle in low and len(hits[key]) < 12:
                            hits[key].append(f"{i}: {line.rstrip()[:220]}")
            out["log_grep"] = hits
        except Exception as e:                   # noqa: BLE001 - teardown path, never raise
            out["log_grep"] = {"error": f"{type(e).__name__}: {e}"}
        save(path, out, tl, server)      # the committed artifact: post-teardown timeline+errors
        # Byte-for-byte copies of THAT file (the post-teardown one), so the tracked artifact and
        # the slice folder cannot drift from the run directory.
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for dest in (os.path.join(repo, "testing", "artifacts", run_id, "body.json"),
                     os.path.join(repo, ".superpowers", "sdd", "03-body-side", "body.json")):
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copyfile(path, dest)
                print(f"copied -> {dest}")
            except Exception as e:               # noqa: BLE001 - teardown path, never raise
                print(f"could not copy to {dest}: {type(e).__name__}: {e}")
print(json.dumps(out.get("summary", out.get("error", "no summary")), indent=1)[:9000])
