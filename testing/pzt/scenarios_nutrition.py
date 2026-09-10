"""Model check for the nutrition_3day_* scenarios (weight model: docs/vanilla/nutrition-core.md).

The scenario itself only drives the world and records the server's Nutrition object once a game
hour (server/scenarios/PZTestKit_Scenario_Nutrition.lua). The claim under test is the *model*:
`Nutrition.updateWeight` gains above `1000 + (w-80)*40` at `1.3e-5 kg/game-s * min(1, cal/4000)`
(x2 if carbs or lipids > 400, x3 above 700) and loses below `min(0, (w-70)*30)` at
`8.5e-6 * min(1, |cal|/2500)`. So the check integrates that model over the measured calorie
trace and compares the weight it predicts against the weight the game reported.

Two details decide whether the comparison means anything:

* **The prediction is integrated against its own predicted weight**, not against the measured
  one. Weight enters `rate()` only through the two thresholds, so the substitution would move
  *which branch fires*, never the accumulator -- the residual accumulates from `s[0]["weight"]`
  either way, and on all three committed runs the two integrations agree bit for bit (neither
  run's weight ever moves a threshold across its calorie trace). The reason to keep it is
  independence, not resolution: the prediction must be a forward simulation that reads the
  measured trace for calories and macros only, so that the one channel by which the measurement
  could steer its own prediction stays closed no matter what a later scenario does to weight.
* **Hourly samples with the left-endpoint calorie value are the resolution.** Calories move by
  ~58 kcal per idle game-hour, so treating the hour's opening value as constant across it biases
  the integral by ~0.025 kg over three game-days -- an order below the tolerance, and in the
  conservative direction for both scenarios (it over-predicts gain and under-predicts loss).

Everything else in the detail dict is diagnosis for when the comparison fails: what the clamps
swallowed, what the free-running drains actually were, and whether the character was asleep or
dead for part of it.
"""
import re

from .scenario import EVALUATORS

GAIN_RATE, LOSS_RATE = 1.3e-5, 8.5e-6      # kg per game-second (Nutrition.updateWeight)
CAL_MAX, CAL_MIN = 3700.0, -2200.0         # setCalories clamp (slice 01, C+M)
CARB_MIN = -500.0                          # setCarbohydrates clamp
MODEL_FIELDS = ("calories", "weight", "carbs", "lipids", "worldAge")
# The scenario's own feed line: "fed +2000: calories 1308.79 -> 3308.79 (asked 3308.79)".
FEED_RE = re.compile(r"fed \+(\S+): calories (\S+) -> (\S+) \(asked (\S+)\)")


def rate(calories, weight, carbs, lipids):
    """kg per game-second at this instant. Positive = gain, negative = loss, 0 in the dead band
    between the two thresholds."""
    gain_thr = 1000 + (weight - 80) * 40
    loss_thr = min(0.0, (weight - 70) * 30)
    if calories > gain_thr:
        r = GAIN_RATE * min(1.0, calories / 4000.0)
        if carbs > 700 or lipids > 700:
            r *= 3
        elif carbs > 400 or lipids > 400:
            r *= 2
        return r
    if calories < loss_thr:
        return -LOSS_RATE * min(1.0, abs(calories) / 2500.0)
    return 0.0


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _usable(s):
    """A sample the model can be integrated over. A getter this build does not expose leaves its
    key absent rather than raising (TK.call), so the guard is per key, not per run."""
    return isinstance(s, dict) and all(_num(s.get(k)) for k in MODEL_FIELDS)


def feeds(doc):
    """Every dose the scenario logged, with what the store kept: `asked - after` IS the clamp
    loss, and it is the first thing to look at when a gain run under-gains."""
    out = []
    for line in doc.get("log") or []:
        m = FEED_RE.search(str(line))
        if not m:
            continue
        try:
            dose, before, after, asked = (float(g) for g in m.groups())
        except ValueError:
            continue
        out.append({"dose": dose, "before": round(before, 1), "after": round(after, 1),
                    "asked": round(asked, 1), "lost_to_clamp": round(asked - after, 1)})
    return out


def drain(s, key, floor=None):
    """The store's free-running drain, per game-day, fitted over the intervals where it is
    actually free: falling (so no feed landed inside) and not truncated by its own floor. It is
    a cross-check against the C constants -- calories -0.016/game-s * (w/80) = -1382 kcal per
    game-day at 80 kg, carbs -0.0035/game-s = -302.4 per game-day -- and it is a mean over the
    window, so the weight term makes it drift a percent or two on a run that moves weight."""
    delta, hours = 0.0, 0.0
    for a, b in zip(s, s[1:]):
        if b[key] >= a[key]:
            continue
        if floor is not None and b[key] <= floor + 1.0:
            continue
        dh = b["worldAge"] - a["worldAge"]
        if dh <= 0:
            continue
        delta += b[key] - a[key]
        hours += dh
    return round(delta / hours * 24.0, 1) if hours > 0 else None


def evaluate(doc, tolerance=0.15):
    raw = doc.get("samples") or []      # TK.json cannot tell an empty Lua table from an object
    s = [x for x in raw if _usable(x)]
    if len(s) < 3:
        return False, {"reason": "too few usable samples", "usable": len(s), "recorded": len(raw)}

    predicted = s[0]["weight"]
    for a, b in zip(s, s[1:]):
        dt = (b["worldAge"] - a["worldAge"]) * 3600.0          # game-seconds between samples
        predicted += rate(a["calories"], predicted, a["carbs"], a["lipids"]) * dt
    measured_delta = s[-1]["weight"] - s[0]["weight"]
    predicted_delta = predicted - s[0]["weight"]
    tol = max(abs(predicted_delta) * tolerance, 0.05)
    ok = abs(measured_delta - predicted_delta) <= tol

    cal = [x["calories"] for x in s]
    hours = s[-1]["worldAge"] - s[0]["worldAge"]
    dosed = feeds(doc)
    detail = {
        "samples": len(s), "recorded_samples": len(raw), "game_hours": round(hours, 2),
        "measured_delta_kg": round(measured_delta, 3),
        "predicted_delta_kg": round(predicted_delta, 3),
        "residual_kg": round(measured_delta - predicted_delta, 3),
        "tolerance_kg": round(tol, 3),
        "weight_start_kg": round(s[0]["weight"], 3), "weight_end_kg": round(s[-1]["weight"], 3),
        "calories_start": round(cal[0], 1), "calories_end": round(cal[-1], 1),
        "calories_min": round(min(cal), 1), "calories_max": round(max(cal), 1),
        "samples_at_calorie_ceiling": sum(1 for c in cal if c >= CAL_MAX - 0.5),
        "samples_at_calorie_floor": sum(1 for c in cal if c <= CAL_MIN + 0.5),
        "calorie_burn_per_game_day": drain(s, "calories", floor=CAL_MIN),
        "carb_drain_per_game_day": drain(s, "carbs", floor=CARB_MIN),
        "carbs_end": round(s[-1]["carbs"], 1), "lipids_end": round(s[-1]["lipids"], 1),
        "feeds": dosed, "doses": len(dosed),
        "kcal_lost_to_clamp": round(sum(f["lost_to_clamp"] for f in dosed), 1),
        "asleep_any": any(x.get("asleep") is True for x in s),
        "dead_any": any(x.get("dead") is True for x in s),
        "resolution": "hourly samples, left-endpoint integration of updateWeight",
    }
    if hours > 0:
        detail["measured_kg_per_game_day"] = round(measured_delta / (hours / 24.0), 3)
        detail["predicted_kg_per_game_day"] = round(predicted_delta / (hours / 24.0), 3)
    if _num(s[-1].get("hunger")):
        detail["hunger_end"] = round(s[-1]["hunger"], 3)
    if _num(s[-1].get("thirst")):
        detail["thirst_end"] = round(s[-1]["thirst"], 3)
    if _num(s[-1].get("health")):
        detail["health_end"] = round(s[-1]["health"], 2)
    # A dead subject fails the run outright, however small the residual. Nutrition.update stops
    # on a corpse (run 1, scenario-20260910-052624: weight and the macros bit-flat for 37 game-
    # hours), so from the first dead sample on the trace carries no information about the model
    # -- and a death late enough in a run leaves a residual that is inside tolerance by
    # arithmetic rather than by the model holding. `within_tolerance` keeps the two verdicts
    # separable in the detail.
    detail["within_tolerance"] = ok
    if detail["dead_any"]:
        ok = False
        detail["reason"] = ("subject died: Nutrition.update stops on a corpse, so the samples "
                            "from the first dead one on measure nothing")
    return ok, detail


EVALUATORS["nutrition_3day_gain"] = evaluate
EVALUATORS["nutrition_3day_fast"] = evaluate
