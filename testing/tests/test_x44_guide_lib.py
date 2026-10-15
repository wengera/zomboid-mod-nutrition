"""Offline tests of testing/experiments/x44_guide_lib.py (Plan 14 Task 5, runs x441..x447): every grade with a failing
case and its zero-sample case, the chained vanilla model against vanilla_model.simulate, the guide's foods against the
install's scripts and the mod's item pass, the pre-boot checks on the real repository, a real run layout and a real
staged copy, the modded replay grade on the HEAD kernel, and each vanilla session's body run against a fake world
behind a fake bus, once as predicted and once per defect flag that must move a named grade off as_predicted.

The fake bus answers the harness's real reply shapes, read off the handlers' `@reply` lines
(docs/reference/harness-commands.md): stats.get {calories, carbs, lipids, proteins, weight, hunger, thirst, endurance,
fatigue, traitList, foodTimer, standardFoodTime, worldAge, wall, ...}; stats.set and nutrition.set the post-write
snapshot {calories, ..., hunger, thirst, applied}; stats.all {side, user, worldAge, mult, wall, stats, missing};
health.get {ok, side, overall, health, parts}; moodle.level {ok, side, user, moodle, level}; perk.xp {perk, user, side,
xp, level, serverWorldAge}; perk.park {ok, perk, levelBefore, levelAfter, xpBefore, xpAfter}; xp.grant {ok, perk,
amount, side, xpBefore, xpAfter, levelBefore, levelAfter}; item.get {fullType, ..., id}; fluid.fill {ok, side,
fullType, id, spawned, requested, litres, fluid, capacity}; autodrink.probe {ok, side, thirst, autoDrink, item, litres,
fluid, containers}; witness.chain {ok, value, hops}; eat.action {queued, fraction, spawned, itemId, ...}; drink.action
{queued, percentage, spawned, itemId, filledRatioBefore, before}; exercise.do {ok, exercise, minutes, queued,
queueLen}; action.cancel {ok, ...}; minute.ring start {ok, side, user, armed, ...}, read {ok, ..., next, more, errors,
result}, stop {ok, stopped}; lua.read {ok, side, root, n, values, tables, types, missing}; lua.global {side, name,
resolved, type, value}; time.snapshot {worldAge, hour, minutes, mult, trueMult, wall}; time.multiplier a string;
players a list of usernames; RCON (xlib.Xs.rcon) (ok, reply); ping "pong".
"""
import json
import math
import os
import re
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x44_guide_lib as L             # noqa: E402
import xlib as X                      # noqa: E402

REPO = L.REPO
VM = L.VM
GAME_SCRIPTS = r"D:\SteamLibrary\steamapps\common\ProjectZomboid\media\scripts\generated\items"
ITEM_PASS = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "scripts", "NR_ItemPass_Food.txt")
S_DEF = dict(L.PRERUN_SETTINGS)


def fresh_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
            "world_changes": {"left_in_place": []}}


# ---------------------------------------------------------------- the model chain
def test_chain_without_writes_is_simulate():
    ev = [L._eat_ev(0.5, L.BOLOGNESE)]
    scn = {"start": dict(L.PRERUN_START, hunger=0.1), "settings": S_DEF, "events": ev, "hours": 3.0, "dt_min": 1.0}
    a = L.model_chain(scn)
    b = VM.simulate({"start": dict(L.PRERUN_START, hunger=0.1), "settings": S_DEF, "events": ev, "hours": 3.0,
                     "dt_min": 1.0})
    for k in ("hunger", "thirst", "calories_store", "weight_kg", "food_timer"):
        assert len(a[k]) == len(b[k]) + 1                                   # the eat's cut carries a pre point
        for t2, v2 in b[k]:
            assert abs(L.series_at(a[k], t2) - v2) < 1e-9, (k, t2)        # at the eat, the post-eat value
    m = L.mark_of(a, None)
    assert m["pre"]["hunger"] > m["post"]["hunger"] and m["post"]["calories"] - m["pre"]["calories"] == 540.0


def test_chain_write_is_a_set_and_carries_the_rest():
    ev = [{"t_h": 1.0, "kind": "set", "values": {"hunger": 0.5}}]
    m = L.model_chain({"start": L.PRERUN_START, "settings": S_DEF, "events": ev, "hours": 2.0})
    assert abs(L.series_at(m["hunger"], 1.0) - 0.5) < 1e-12                  # the written start at the boundary
    assert L.series_at(m["hunger"], 0.999) < 0.04                            # before it, the rise from 0
    assert abs(L.series_at(m["thirst"], 1.5) - VM.THIRST_INCREASE * 1.5 * 3600) < 1e-9   # thirst carried through
    c = L.series_at(m["calories_store"], 2.0)
    assert abs(c - (800.0 - VM.BURN_IDLE * 7200)) < 0.05


def test_chain_grant_is_vm11():
    ev = [{"t_h": 0.1, "kind": "set", "values": {"strength_xp": 37500.0}},
          {"t_h": 0.2, "kind": "set", "values": {"proteins": 0.0}},
          {"t_h": 0.3, "kind": "grant", "amount": 29700.0},
          {"t_h": 0.4, "kind": "set", "values": {"proteins": 100.0}},
          {"t_h": 0.5, "kind": "exercise", "mode": "pushups", "reps": 60, "sets": 1}]
    m = L.model_chain({"start": dict(L.PRERUN_START, strength_level=5, strength_xp=37500.0), "settings": S_DEF,
                       "events": ev, "hours": 1.0})
    ev[2]["label"], ev[4]["label"] = "g", "set"
    m = L.model_chain({"start": dict(L.PRERUN_START, strength_level=5, strength_xp=37500.0), "settings": S_DEF,
                       "events": ev, "hours": 1.0})
    assert L.series_at(m["strength_xp"], 0.3 + 1e-6, step=True) == 67200.0
    assert L.mark_of(m, "g")["writes"]["strength_xp"] == 67200.0
    assert abs(L.model_set_delta(m, "set") - 540.0) < 1e-9
    assert L.series_at(m["strength_level"], 0.6, step=True) == 6


def test_prerun_headlines_are_the_maps():
    v1a, v1b, v3, v4 = L.prerun("V1a"), L.prerun("V1b"), L.prerun("V3"), L.prerun("V4")
    assert v1a["A_timer_after_eat"] == 0.0 and abs(v1a["B_freeze_min"] - 17.333) < 0.01
    assert abs(v1b["level4_h"] - 8.32) < 0.01 and abs(v1b["death_h"] - 36.4) < 0.05
    assert (v3["A"], v3["B_grant_xp_after"], v3["B"], v3["B_level"], v3["C"]) == (360.0, 67200.0, 540.0, 6, 252.0)
    assert v4["coffee_fatigue"] == -0.025 and v4["beer_gain_each"] == 6.0 and abs(v4["decay_per_h"] - 45.36) < 1e-9
    v2 = L.prerun("V2a")
    assert v2["weight_change_span"] > 1.0 and v2["span_h"] == 36.0 and L.prerun("V2b") == v2
    assert abs(v2["weight_change_V2a"] + v2["weight_change_V2b"] - v2["weight_change_span"]) < 1e-9


def test_series_helpers():
    s = [(0.0, 0.0), (1.0, 1.0), (2.0, 1.0), (2.0, 0.2), (3.0, 0.4)]
    assert L.series_at(s, 0.5) == 0.5 and L.series_at(s, 2.0) == 0.2 and L.series_at(s, 4.0) is None
    assert L.first_cross([(0, 0.6), (1, 0.65), (2, 0.75)], 0.7) == pytest.approx(1.5)
    assert L.first_at_or_below([(0, 30.0), (1, 20.0), (2, 10.0), (3, 0.0), (4, 0.0)], 0.0) == pytest.approx(3.0)
    assert L.first_at_or_below([(0, 300.0), (1, 120.0), (2, 0.0)], 0.0) == pytest.approx(1 + 120.0 / 180.0)
    assert L.crossings([(0, 0.1), (1, 0.2), (2, 0.3)], (0.15, 0.25)) == [1, 2]


def test_ages_of_hours():
    assert L.age_at(1, 8.0) == 1.0 and L.age_at(2, 19.0) == 36.0 and L.hour_of(36.0) == 19.0
    assert L.next_age_of_hour(2.0, 10.0) == 3.0 and L.next_age_of_hour(4.0, 10.0) == 27.0


# ---------------------------------------------------------------- the foods
def _script_items(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    out = {}
    for m in re.finditer(r"item\s+(\w+)\s*\{(.*?)\n\s*\}", text, re.S):
        props = dict((k.strip(), v.strip().rstrip(",")) for k, v in re.findall(r"^\s*(\w+)\s*=\s*([^\n]+)$",
                                                                                 m.group(2), re.M))
        out[m.group(1)] = props
    return out


@pytest.mark.skipif(not os.path.isdir(GAME_SCRIPTS), reason="the install's scripts are absent on this machine")
def test_vanilla_foods_are_the_install_scripts():
    items = _script_items(os.path.join(GAME_SCRIPTS, "food.txt"))
    for full, f in L.VANILLA_FOODS.items():
        p = items[full.split(".", 1)[1]]
        assert float(p["HungerChange"]) == f["hunger_script"], full
        assert (float(p["Calories"]), float(p["Carbohydrates"]), float(p["Lipids"]), float(p["Proteins"])) == \
            (f["calories"], f["carbs"], f["lipids"], f["proteins"]), full
        assert p["FoodType"] == f["foodType"], full
    text = open(os.path.join(GAME_SCRIPTS, "normal.txt"), encoding="utf-8", errors="replace").read()
    assert re.search(r"item BeerCan\s*\{.*?Capacity = 0\.3,.*?fluid = Beer:1\.0", text, re.S)
    for full in L.BEER_CONTAINERS + L.COFFEE_CONTAINERS:             # each a prefilled fluid container of its own
        m = re.search(r"\n    item " + full.split(".")[1] + r"\s*\n    \{(.*?)\n    \}", text, re.S)
        assert m and "component FluidContainer" in m.group(1) and re.search(r"fluid = \w+:", m.group(1)), full
    assert len(set(L.BEER_CONTAINERS + L.COFFEE_CONTAINERS)) == len(L.BEER_CONTAINERS + L.COFFEE_CONTAINERS)


def test_mod_foods_are_the_item_pass():
    items = _script_items(ITEM_PASS)
    p = items["CannedBologneseOpen"]
    f = L.MOD_FOODS[L.BOLOGNESE]
    assert (float(p["Calories"]), float(p["Carbohydrates"]), float(p["Lipids"]), float(p["Proteins"])) == \
        (f["cal"], f["carb"], f["lip"], f["pro"])
    assert "HungerChange" not in p                             # the pass leaves the script's hunger (spec 4.6)
    ev = L.mod_eat_event(L.BOLOGNESE, 7, "x")
    assert ev["kind"] == "eat" and ev["s"] == 7 and abs(ev["hunger"] + 0.24) < 1e-6 and ev["foodType"] == "Meat"


# ---------------------------------------------------------------- the grades (pure), each with its failing case
def _model_line(field, slope, hours=4.0, start=0.0):
    return {field: [(i / 60.0, start + slope * i / 60.0) for i in range(int(hours * 60) + 1)]}


def test_grade_curve():
    m = _model_line("hunger", 0.03)
    rows = [{"s": i, "age": 10.0 + i / 60.0, "HUNGER": 0.03 * i / 60.0} for i in range(0, 120)]
    v, o = L.grade_curve(rows, m, "HUNGER", "hunger", 10.0, 0.003, (10.0, 20.0))
    assert v == "as_predicted" and o["n"] == 120
    bad = [dict(r, HUNGER=r["HUNGER"] + 0.01) if r["s"] == 50 else r for r in rows]
    assert L.grade_curve(bad, m, "HUNGER", "hunger", 10.0, 0.003, (10.0, 20.0))[0] == "falsified"
    assert L.grade_curve(bad, m, "HUNGER", "hunger", 10.0, 0.003, (10.0, 20.0), skip_ages=[10.0 + 50 / 60])[0] == \
        "as_predicted"                                         # a row beside an event is not graded
    assert L.grade_curve([], m, "HUNGER", "hunger", 10.0, 0.003, (10.0, 20.0))[0] == "unmeasured"


def test_grade_reads():
    m = _model_line("calories_store", -57.6, start=800.0)
    reads = [{"age": 1.0 + h, "calories": 800.0 - 57.6 * h} for h in range(4)]
    assert L.grade_reads(reads, m, "calories", "calories_store", 1.0, 5.0, 0.01)[0] == "as_predicted"
    reads[2]["calories"] += 10.0
    v, o = L.grade_reads(reads, m, "calories", "calories_store", 1.0, 5.0, 0.01)
    assert v == "falsified" and o["over_n"] == 1
    assert L.grade_reads([], m, "calories", "calories_store", 1.0, 5.0)[0] == "unmeasured"


def test_grade_levels():
    m = {"food_timer": [(i / 60.0, max(0.0, 5000.0 - 180.0 * i)) for i in range(60)]}
    good = [{"age": i / 60.0, "level": VM.food_eaten_level(max(0.0, 5000.0 - 180.0 * i))} for i in range(0, 40, 3)]
    assert L.grade_levels(good, m, "food_timer", VM.FOOD_EATEN_THRESHOLDS, 0.0)[0] == "as_predicted"
    bad = [dict(r, level=r["level"] + 1) for r in good]
    assert L.grade_levels(bad, m, "food_timer", VM.FOOD_EATEN_THRESHOLDS, 0.0)[0] == "falsified"
    assert L.grade_levels([], m, "food_timer", VM.FOOD_EATEN_THRESHOLDS, 0.0)[0] == "unmeasured"


def test_grade_freeze():
    m = {"food_timer": [(i / 60.0, max(0.0, 3120.0 - 180.0 * i)) for i in range(60)]}
    zero = 3120.0 / 180.0 / 60.0
    rows = [{"age": i / 60.0, "HUNGER": 0.0 if i / 60.0 < zero else 1e-3 * (i / 60.0 - zero) * 60} for i in range(1, 40)]
    assert L.grade_freeze(rows, 0.001, m, 0.0)[0] == "as_predicted"
    early = [dict(r, HUNGER=0.002) if r["age"] > 0.1 else r for r in rows]          # rose inside the freeze
    assert L.grade_freeze(early, 0.001, m, 0.0)[0] == "falsified"
    late = [dict(r, HUNGER=0.0) if r["age"] < zero + 0.1 else r for r in rows]       # ended six minutes late
    assert L.grade_freeze(late, 0.001, m, 0.0)[0] == "falsified"
    assert L.grade_freeze(rows, None, m, 0.0)[0] == "unmeasured"


def test_grade_crossing_and_death():
    m = {"hunger": [(i / 60.0, 0.6 + 0.012 * i / 60.0) for i in range(600)],
         "health": [(i / 60.0, max(0.0, 100.0 - 10.0 * i / 60.0)) for i in range(800)]}
    rows = [{"age": 5.0 + i / 60.0, "HUNGER": 0.6 + 0.012 * i / 60.0} for i in range(600)]
    assert L.grade_crossing(rows, m, "hunger", "HUNGER", 0.7, 5.0, 0.1)[0] == "as_predicted"
    shifted = [dict(r, HUNGER=r["HUNGER"] + 0.004) for r in rows]
    assert L.grade_crossing(shifted, m, "hunger", "HUNGER", 0.7, 5.0, 0.1)[0] == "falsified"
    assert L.grade_crossing([], m, "hunger", "HUNGER", 0.7, 5.0, 0.1)[0] == "unmeasured"
    assert L.grade_death({"dead": True, "age": 15.1}, m, 5.0, 15.1)[0] == "as_predicted"
    assert L.grade_death({"dead": True, "age": 16.0}, m, 5.0, 16.0)[0] == "falsified"
    assert L.grade_death(None, m, 5.0, 16.0)[0] == "falsified"                       # alive past the model's death
    assert L.grade_death(None, m, 5.0, 14.0)[0] == "unmeasured"


def _xp_model(delta, label="A"):
    return {"_marks": [{"t_h": 0.5, "labels": [label], "writes": {"strength_xp": 37500.0},
                        "post": {"strength_xp": 37500.0 + delta}}]}


def test_grade_set():
    row = {"xp_before": {"xp": 37500.0}, "xp_after": {"xp": 37860.0}, "label": "A", "factor": 1.0, "exe_seen": True}
    assert L.grade_set(row, _xp_model(360.0), 0.0)[0] == "as_predicted"
    assert L.grade_set(dict(row, xp_after={"xp": 37800.0}), _xp_model(360.0), 0.0)[0] == "falsified"
    assert L.grade_set(dict(row, xp_after={"xp": 37848.0}), _xp_model(360.0), 0.0)[0] == "as_predicted"   # 2 reps
    assert L.grade_set(dict(row, exe_seen=False), _xp_model(360.0), 0.0)[0] == "unmeasured"
    assert L.grade_set(dict(row, label="Z"), _xp_model(360.0), 0.0)[0] == "unmeasured"     # no model set


def test_grade_grant_and_level():
    assert L.grade_grant({"xpAfter": 67200.0}, 67200.0)[0] == "as_predicted"
    assert L.grade_grant({"xpAfter": 82050.0}, 67200.0)[0] == "falsified"
    assert L.grade_grant({}, 67200.0)[0] == "unmeasured"
    assert L.grade_level_band({"level": 6}, {"traitList": ["base:stout"]}, 6)[0] == "as_predicted"
    assert L.grade_level_band({"level": 6}, {"traitList": {}}, 6)[0] == "falsified"            # no band
    assert L.grade_level_band({"level": 5}, {"traitList": ["Stout"]}, 6)[0] == "falsified"
    assert L.grade_level_band({}, {"traitList": []}, 6)[0] == "unmeasured"


def test_grade_coffee_and_holds():
    m = {"fatigue": [(0.0, 0.5), (0.1, 0.5), (0.1, 0.475), (1.0, 0.475)]}
    c = {"landed": True, "before": {"fatigue": 0.5, "worldAge": 0.05}, "after": {"fatigue": 0.476, "worldAge": 0.2},
         "hold": [{"age": 0.3, "fatigue": 0.48}, {"age": 0.9, "fatigue": 0.49}]}
    assert L.grade_coffee(c, m, 0.0)[0] == "as_predicted"
    assert L.grade_coffee(dict(c, after={"fatigue": 0.49, "worldAge": 0.2}), m, 0.0)[0] == "falsified"
    assert L.grade_coffee(dict(c, landed=False), m, 0.0)[0] == "unmeasured"
    assert L.grade_coffee_holds(c)[0] == "as_predicted"
    assert L.grade_coffee_holds(dict(c, hold=[{"age": 0.3, "fatigue": 0.0001}]))[0] == "falsified"
    assert L.grade_coffee_holds(dict(c, hold=[]))[0] == "unmeasured"


def test_grade_intox():
    m = {"intoxication": [(i / 60.0, max(0.0, 24.0 - 45.36 * i / 60.0)) for i in range(60)]}
    polls = [{"age": i / 60.0, "intox": max(0.0, 24.0 - 45.36 * i / 60.0)} for i in range(0, 60)]
    assert L.grade_intox_decay(polls, 0.0, m, 0.0)[0] == "as_predicted"
    slow = [{"age": p["age"], "intox": max(0.0, 24.0 - 38.0 * p["age"])} for p in polls]
    assert L.grade_intox_decay(slow, 0.0, m, 0.0)[0] == "falsified"
    assert L.grade_intox_zero(polls, 0.0, m, 0.0)[0] == "as_predicted"
    assert L.grade_intox_zero(slow, 0.0, m, 0.0)[0] == "falsified"
    assert L.grade_intox_decay(polls[:2], 0.0, m, 0.0)[0] == "unmeasured"
    assert L.grade_intox_zero([], 0.0, m, 0.0)[0] == "unmeasured"


def test_grade_replay_field_and_hangover():
    d = {"fields": {"HUNGER": {"n": 10, "max": 0.001, "over": 0}, "THIRST": {"n": 10, "max": 0.01, "over": 2},
                    "body.energyState": {"n": 0, "max": 0.0, "over": 0}}, "findings": []}
    assert L.grade_replay_field(d, "HUNGER")[0] == "as_predicted"
    assert L.grade_replay_field(d, "THIRST")[0] == "falsified"
    assert L.grade_replay_field(d, "body.energyState")[0] == "unmeasured"
    ring = [{"age": a / 10.0, "acute.hang": 1 if a >= 50 else 0} for a in range(100)]
    rep = [{"age": a / 10.0, "acute.hang": 1 if a >= 51 else 0} for a in range(100)]
    assert L.grade_hangover(ring, rep)[0] == "as_predicted"
    assert L.grade_hangover(ring, [dict(r, **{"acute.hang": 0}) for r in rep])[0] == "falsified"
    assert L.grade_hangover(ring, [dict(r, **{"acute.hang": 1 if r["age"] >= 8 else 0}) for r in rep])[0] == "falsified"
    assert L.grade_hangover([{"age": 1}], rep)[0] == "unmeasured"


# ---------------------------------------------------------------- the modded event building and replay
def test_build_events_eats_drinks_and_ring_kinds():
    rows = [{"s": 1, "age": 1.0, L.EATS_G: 0, L.SIPS_G: 0}, {"s": 2, "age": 1.02, L.EATS_G: 1, L.SIPS_G: 0},
            {"s": 3, "age": 1.04, L.EATS_G: 1, L.SIPS_G: 2, L.AUTODROP: 0.01, "moving": True},
            {"s": 4, "age": 1.06, L.EATS_G: 1, L.SIPS_G: 3, L.SLEPT: 0.0},
            {"s": 5, "age": 1.08, L.EATS_G: 1, L.SIPS_G: 3, L.SLEPT: 0.02}]
    eats = [{"food": L.BOLOGNESE, "landed": True, "label": "e"}]
    drinks = [{"fluid": "Coffee", "drunk": 0.25, "age0": 1.03, "age1": 1.06, "label": "c"}]
    ev, book = L.replay_events(rows, eats, drinks, start_age=0.5, sleep=True)
    kinds = [(e["s"], e["kind"]) for e in ev]
    assert (2, "eat") in kinds and (3, "autodrop") in kinds and (3, "activity") in kinds and (4, "sleep") in kinds
    dr = [e for e in ev if e["kind"] == "drink"]
    assert abs(sum(e["litres"] for e in dr) - 0.25) < 1e-12 and [e["s"] for e in dr] == [3, 4]
    assert book["sleeps"] == 1 and not book["notes"]
    ev2, book2 = L.replay_events(rows, eats, [dict(drinks[0], drunk=None)], start_age=0.5)
    assert any("no litres" in n for n in book2["notes"]) and not [e for e in ev2 if e["kind"] == "drink"]
    _ev3, book3 = L.replay_events(rows, eats, [], start_age=1.03)                    # held back in the start record
    assert any(e["kind"] == "autodrop" for e in book3["held_in_start"])


def _arm_ring(events, minutes):
    """A ring made by the HEAD replay itself (rows in the ring's phase: row k+1 reads the state drain k left)."""
    import replay_live as RL
    a0 = 2.0
    rows, _be = RL.replay_arm(events, minutes=minutes, start_age=a0, paths=("body.energyState",),
                              sleep_allowed=False)
    ring = [{"s": 1, "age": a0, "on": True, "hour": 9, "min": 0}]
    for k, r in enumerate(rows):
        x = {key: v for key, v in r.items() if key in ("HUNGER", "THIRST", "body.energyState", "hour", "min")}
        x.update({"s": k + 2, "age": a0 + (k + 1) / 60.0, "on": True})
        ring.append(x)
    return ring


def test_replay_grade_reproduces_its_own_ring_and_fails_a_shift():
    pytest.importorskip("lupa")
    events = [dict(L.mod_eat_event(L.BOLOGNESE, 0), age=2.2)]
    events[0].pop("s")
    ring = _arm_ring(events, 90)
    tol = dict(L.REPLAY_TOL)
    rows, d, _be = L.replay_grade(ring, [dict(e) for e in events], None, False, tol,
                                  paths=["body.energyState"], hour_offset=0.0)
    verdicts = {f: L.grade_replay_field(d, f)[0] for f in tol}
    assert set(verdicts.values()) == {"as_predicted"}, (verdicts, d.get("findings")[:3])
    bad = [dict(r, HUNGER=r["HUNGER"] + 0.01) if (r.get("HUNGER") is not None and r["s"] == 60) else r for r in ring]
    _rows, d2, _be2 = L.replay_grade(bad, [dict(e) for e in events], None, False, tol, paths=["body.energyState"],
                                     hour_offset=0.0)
    assert L.grade_replay_field(d2, "HUNGER")[0] == "falsified"
    assert L.grade_replay_field(d2, "THIRST")[0] == "as_predicted"


# ---------------------------------------------------------------- the pre-boot checks
def test_harness_markers_are_in_the_repository():
    found, ok = L.harness_markers_ok()
    assert ok, found


def test_deployed_marker_check_on_a_run_layout():
    with tempfile.TemporaryDirectory() as d:
        for fname, rel in L.HARNESS_FILES.items():
            side = rel.split("/")[-2]
            dst = os.path.join(d, "server", "Zomboid", "mods", "PZTestKit", "42", "media", "lua", side, fname)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(REPO, rel), dst)
        dm, ok = X.deployed_marker_check(d, list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)
        assert ok, dm
        p = os.path.join(d, "server", "Zomboid", "mods", "PZTestKit", "42", "media", "lua", "client",
                         "PZTestKit_Client.lua")
        with open(p, "w", encoding="utf-8") as out:
            out.write("-- emptied")
        assert X.deployed_marker_check(d, list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)[1] is False


def test_manifest_gate_on_a_real_staged_copy():
    import release_pack as RP
    with tempfile.TemporaryDirectory() as d:
        RP.stage(os.path.join(REPO, L.MOD_DIR), d)
        root = os.path.join(d, "NutritionRevamp")
        mod = os.path.join(root, "Contents", "mods", "NutritionRevamp")
        say = {("rev-parse", "HEAD"): "h", ("rev-parse", "--short", "HEAD"): "h"}
        out = {}
        mg = L.staged_gate(out, lambda *a: say.get(a, "c"), lambda p: (False, ""), stage_root=root, stage_mod=mod)
        assert mg["ok"] and mg["staged_version"] == "1.0.0", mg
        core = os.path.join(mod, *L.STAGED_CORE.split("/"))
        with open(core, "a", encoding="utf-8") as fh:
            fh.write("\n-- drift\n")
        assert L.staged_gate({}, lambda *a: "c", lambda p: (False, ""), stage_root=root, stage_mod=mod)["ok"] is False
        assert L.staged_gate({}, lambda *a: "c", lambda p: (True, "M"), stage_root=root, stage_mod=mod)["ok"] is False


@pytest.mark.parametrize("key", sorted(L.SESSIONS))
def test_preboot_passes_on_the_repository(key):
    spec = L.SESSIONS[key]
    drv = next(f for f in os.listdir(os.path.join(REPO, "testing", "experiments")) if f.startswith(spec["prefix"] + "_"))
    checks, ok = L.preboot(key, spec["profile"], spec["prefix"], drv)
    assert ok, checks
    assert L.preboot(key, spec["profile"], "x999", drv)[1] is False
    assert L.preboot(key, "x44-other", spec["prefix"], drv)[1] is False


def test_preboot_refuses_a_committed_artifact(tmp_path):
    shutil.copytree(os.path.join(REPO, "testing", "profiles"), tmp_path / "testing" / "profiles")
    for rel in L.HARNESS_FILES.values():
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(os.path.join(REPO, rel), dst)
    (tmp_path / "testing" / "artifacts").mkdir()
    assert L.preboot("V1a", "x44-vanilla", "x441", "x441_meal.py", repo=str(tmp_path))[1] is True
    (tmp_path / "testing" / "artifacts" / "x441-20261016-100000").mkdir()
    checks, ok = L.preboot("V1a", "x44-vanilla", "x441", "x441_meal.py", repo=str(tmp_path))
    assert ok is False and checks["no_prior_artifact"] is False


def test_profile_doc_checks_fail_a_wrong_profile():
    import tomllib
    with open(os.path.join(REPO, "testing", "profiles", "x44-vanilla.toml"), encoding="utf-8") as fh:
        text = fh.read()
    doc = tomllib.loads(text)
    assert all(L.profile_doc_checks("V1a", "x44-vanilla", doc, text).values())
    assert not L.profile_doc_checks("V4", "x44-vanilla", doc, text)["sleep_keys"]
    modded = dict(doc, mods=doc["mods"] + [{"id": "NutritionRevamp", "path": "mod/NutritionRevamp"}])
    assert not L.profile_doc_checks("V1a", "x44-vanilla", modded, text)["mods_harness_only"]
    with open(os.path.join(REPO, "testing", "profiles", "x44-mod.toml"), encoding="utf-8") as fh:
        mt = fh.read()
    md = tomllib.loads(mt)
    assert all(L.profile_doc_checks("M1", "x44-mod", md, mt).values())
    live = dict(md, mods=[md["mods"][0], {"id": "NutritionRevamp", "path": "mod/NutritionRevamp"}])
    assert not L.profile_doc_checks("M1", "x44-mod", live, mt)["mods_staged"]          # mod/ is never booted


@pytest.mark.skipif(not os.path.isdir(os.path.join(REPO, "testing", "fixtures", "default", "cache")),
                    reason="the default fixture is not provisioned on this machine")
@pytest.mark.parametrize("name", ["x44-vanilla", "x44-vanilla-sleep"])
def test_vanilla_profiles_load(name):
    from pzt import profile
    p = profile.load(name)
    assert p.mods == ["PZTestKit"] and p.sandbox.get("Nutrition") is True
    assert p.ini == {"SleepAllowed": name.endswith("sleep"), "SleepNeeded": name.endswith("sleep")}


def test_drivers_name_their_session():
    for key, spec in L.SESSIONS.items():
        drv = [f for f in os.listdir(os.path.join(REPO, "testing", "experiments")) if f.startswith(spec["prefix"] + "_")]
        assert len(drv) == 1, (key, drv)
        with open(os.path.join(REPO, "testing", "experiments", drv[0]), encoding="utf-8") as fh:
            text = fh.read()
        assert f'KEY = "{key}"' in text and f'PREFIX = "{spec["prefix"]}"' in text, drv
        assert f'PROFILE = "{spec["profile"]}"' in text and f'ARTIFACT = "{spec["artifact"]}"' in text, drv
        b = float(re.search(r"BUDGET_S = ([\d.]+)", text).group(1))
        assert b <= 500.0, (drv, b)                                     # re-review N-5: the whole call under 10 min


# ---------------------------------------------------------------- fix round 1: the pure additions
def test_moodle_names_are_moodletype_fields():
    # review I-1: MoodleType's static fields are upper case ('Hungry' is the registry id, not a Lua field)
    for name in (L.MOODLE_FOOD_EATEN, L.MOODLE_HUNGRY):
        assert re.match(r"^[A-Z_]+$", name), name
    with open(L.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for m in re.finditer(r"self\.moodle\([^,]+,\s*([^,)]+)", src):
        arg = m.group(1).strip()
        assert arg.startswith("MOODLE_") or re.match(r'^"[A-Z_]+"$', arg), arg


def test_grade_freeze_held_max_branch():
    # review M-7: one row 0.002 inside the freeze while the unfreeze lands on time
    m = {"food_timer": [(i / 60.0, max(0.0, 3120.0 - 180.0 * i)) for i in range(60)]}
    zero = 3120.0 / 180.0 / 60.0
    rows = [{"age": i / 60.0, "HUNGER": 0.0 if i / 60.0 < zero else 1e-3 * (i / 60.0 - zero) * 60} for i in range(1, 40)]
    rows[3]["HUNGER"] = 0.002
    v, o = L.grade_freeze(rows, 0.001, m, 0.0)
    assert v == "falsified" and o["why"] == "HUNGER rose inside the model's freeze"


def test_no_live_crossing_past_the_model_is_falsified():
    # review M-8: a plateau under 0.70 (#0174) and an INTOXICATION that never reaches 0
    m = {"hunger": [(i / 60.0, 0.6 + 0.012 * i / 60.0) for i in range(600)]}
    flat = [{"age": 5.0 + i / 60.0, "HUNGER": min(0.6999, 0.6 + 0.012 * i / 60.0)} for i in range(600)]
    v, o = L.grade_crossing(flat, m, "hunger", "HUNGER", 0.7, 5.0, 0.1, last_age=flat[-1]["age"])
    assert v == "falsified" and o["why"] == "no live crossing by the model's age plus the tolerance"
    assert L.grade_crossing(flat, m, "hunger", "HUNGER", 0.7, 5.0, 0.1, last_age=5.0 + 8.4)[0] == "unmeasured"
    mi = {"intoxication": [(i / 60.0, max(0.0, 24.0 - 45.36 * i / 60.0)) for i in range(60)]}
    stuck = [{"age": i / 60.0, "intox": 3.0} for i in range(60)]
    v, o = L.grade_intox_zero(stuck, 0.0, mi, 0.0, last_age=stuck[-1]["age"])
    assert v == "falsified" and o["why"] == "no live crossing by the model's age plus the tolerance"
    assert L.grade_intox_zero(stuck, 0.0, mi, 0.0)[0] == "unmeasured"


def test_grade_death_gone_is_unmeasured():
    m = {"health": [(i / 60.0, max(0.0, 100.0 - 10.0 * i / 60.0)) for i in range(800)]}
    v, o = L.grade_death(None, m, 5.0, 16.0, gone=True)
    assert v == "unmeasured" and o["why"] == "the player left the online list"
    assert L.grade_death(None, m, 5.0, 16.0)[0] == "falsified"


def test_coffee_unmeasured_on_a_failed_fill():
    m = {"fatigue": [(0.0, 0.5), (1.0, 0.5)]}
    c = {"landed": True, "fill_ok": False, "before": {"fatigue": 0.5, "worldAge": 0.1},
         "after": {"fatigue": 0.475, "worldAge": 0.2}}
    assert L.grade_coffee(c, m, 0.0)[0] == "unmeasured"


def test_m2_plan_is_relative_and_before_the_night():
    S = L.Sess(X.Xs(fresh_out(), node=str), "M2")
    for a in (3.3, 5.5, 9.0, 20.0):
        p = S.m2_plan(a)
        assert p["ok"] and p["coffees"][0] == pytest.approx(a + 0.1) and len(p["coffees"]) == 3, p
        assert p["beers"] >= p["coffees"][-1] + L.M2_BEER_GAP_H and p["night"] > p["beers"], p
        assert p["night"] - p["beers"] <= L.M2_NIGHT_MAX_GAP_H + 1e-9, p
    assert S.m2_plan(5.5)["night_at_23"] is True


def _chain_dir(tmp_path, **over):
    d = tmp_path / "x443a-20261016-100000"
    (d / "server" / "Server").mkdir(parents=True)
    doc = {"run_id": "x443a-20261016-100000", "checks": {"X": {"anchor": 2.4, "reached": 20.41}},
           "bus_dead": None, "budget_stop": None, "phase_errors": {}}
    doc.update(over)
    (d / "tuna-a.json").write_text(json.dumps(doc), encoding="utf-8")
    return d


def test_chain_check(tmp_path):
    d = _chain_dir(tmp_path)
    c, ok = L.chain_check(str(d))
    assert ok and c["anchor"] == 2.4, c
    assert L.chain_check(None)[1] is False
    assert L.chain_check(str(tmp_path / "nowhere"))[1] is False
    for over in ({"run_id": "x443-20261016-1"}, {"error": "boom"}, {"abort": "x"}, {"checks": {"X": {}}},
                 {"bus_dead": "X_a"}, {"budget_stop": {"phase": "X"}}, {"phase_errors": {"X": {"error": "e"}}},
                 {"unrun": [{"tag": "X", "age": 14.4, "kind": "timed"}]},
                 {"checks": {"X": {"anchor": 2.4, "reached": 12.4}}}):
        t = tmp_path / ("c" + str(abs(hash(json.dumps(over)))))
        t.mkdir()
        assert L.chain_check(str(_chain_dir(t, **over)))[1] is False, over
    shutil.rmtree(d / "server")
    assert L.chain_check(str(d))[1] is False


def test_run_to_records_unrun_actions():
    w = Vanilla(tempfile.mkdtemp())
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={}, ask=w.ask, clock=w.clock, sleep=w.sleep)
    S = L.Sess(xs, "V1a")
    a = w.age
    S.run_to(a + 0.5, [(a + 0.2, "read", lambda x: None), (a + 3.0, "read", lambda x: None)], L.SPEED_FAST, "T")
    assert len(out["unrun"]) == 1 and out["unrun"][0]["age"] == pytest.approx(a + 3.0)


# ---------------------------------------------------------------- the fake vanilla world (the real reply shapes)
WALL_GAME_S = 16.0               # game seconds a wall second at DayLength 4, speed 1 (a game minute is 3.75 s)
DL4_START = 2.35                 # the DL4 sessions' first reads on this fixture (x371 2.351, x372 2.359)
DL1_START = 3.2                  # the DL1 sessions' first reads (x361 3.234, x364 3.202, x301 3.184)
EFF = 4.75                       # getMultiplier against getTrueMultiplier (#3762)
NUT_KEYS = ("calories", "carbs", "lipids", "proteins", "weight", "hunger", "thirst", "statsApi", "incWeight",
            "incWeightLot", "decWeight")
GONE = "no online player admin"


class FakeClient:
    def __init__(self, user):
        self.username = user
        self.seen = {}
        self.alive = True


class FakeBus:
    def __init__(self, results_dir):
        self.results_dir = results_dir

    def wait_result(self, name, timeout=30, after=None):
        with open(os.path.join(self.results_dir, name + ".json"), encoding="utf-8") as fh:
            return json.load(fh)


class FakeServer:
    def __init__(self, world, results_dir):
        self.w = world
        self.errors = []
        self.bus = FakeBus(results_dir)

    def rcon(self, cmd):
        return self.w.rcon(cmd)


def ring_start_reply(paths):
    return {"ok": True, "side": "server", "user": "admin", "armed": True, "cap": 4320, "paths": list(paths) or {},
            "stats": ["HUNGER", "THIRST", "FATIGUE", "BOREDOM", "UNHAPPINESS", "NICOTINE_WITHDRAWAL"], "online": True,
            "probe": {}}


def ring_read_reply(world, frm, rows, more):
    return {"ok": True, "side": "server", "user": "admin", "from": frm, "rows": len(rows), "skipped": 0,
            "next": frm + len(rows) if more else None, "more": more,
            "oldest": world.ring[0]["s"] if world.ring else None, "newest": world.ring[-1]["s"] if world.ring else None,
            "recorded": len(world.ring), "overwritten": 0, "cap": 4320, "events": world.s, "errors": 0,
            "lastError": None, "gErrors": 0, "gLastError": None, "result": f"minute-ring-admin-{frm}",
            "file": f"pzt-results/minute-ring-admin-{frm}.json"}


def ring_stop_reply(world):
    return {"ok": True, "side": "server", "user": "admin", "stopped": True, "recorded": len(world.ring),
            "overwritten": 0, "errors": 0, "lastError": None}


def item_state(full, n, age):
    return {"fullType": full, "cooked": False, "burnt": False, "rotten": False, "frozen": False, "age": 0.0,
            "hungChange": None, "baseHunger": None, "calories": None, "carbs": None, "lipids": None, "proteins": None,
            "id": 1000 + n, "uses": 1, "fresh": True, "offAge": 1, "offAgeMax": 2, "freezingTime": 0,
            "cookingTime": 0, "heat": 1.0, "minutesToCook": 0, "minutesToBurn": 0, "thirstChange": 0,
            "hungerChange": None, "isCookable": False, "actualWeight": 0.3, "weight": 0.3, "customWeight": False,
            "lastCookMinute": 0, "serverWorldAge": age}


class Vanilla:
    """A vanilla world on the model's own rate functions (VM1-VM16), stepped at most a game minute at a time, with a
    ring row at every game-minute boundary; every reply in the harness's own shape (the @reply lines); `flags` move
    one mechanism or one reply off the real one."""

    def __init__(self, results_dir, flags=None, sleep_allowed=False, age=DL4_START, speed=1):
        self.f = flags or {}
        self.dir = results_dir
        self.sleep_allowed = sleep_allowed
        self.t, self.age, self.speed = 0.0, age, speed
        self.st = {"hunger": 0.05, "thirst": 0.02, "food_timer": 0.0, "calories": 800.0, "carbs": 50.0, "lipids": 30.0,
                   "proteins": 20.0, "weight": 80.0, "health": 100.0, "fatigue": 0.1, "intox": 0.0, "endurance": 1.0}
        self.xp, self.level, self.traits = 37500.0, 5, []
        self.inv = {}
        self.fills = {}
        self.pending = []
        self.exe = False
        self.ring, self.ring_on, self.s = [], False, 0
        self.dead = False
        self.sm = VM.stats_decrease_multiplier(3)

    def clock(self):
        return self.t

    def sleep(self, dt):
        end = self.t + dt
        while self.t < end - 1e-9:
            due = min([p[0] for p in self.pending if p[0] > self.t + 1e-12] + [end])
            self._advance(due - self.t)
            self.t = due
            for p in [p for p in self.pending if p[0] <= self.t + 1e-12]:
                self.pending.remove(p)
                p[1]()

    def _advance(self, dt_wall):
        game_s = dt_wall * WALL_GAME_S * self.speed
        while game_s > 1e-9:
            to_min = (math.floor(self.age * 60.0 + 1e-9) + 1) / 60.0 * 3600.0 - self.age * 3600.0
            step = min(game_s, max(to_min, 1e-6), 60.0)
            self._step(step)
            game_s -= step
            if abs(self.age * 60.0 - round(self.age * 60.0)) < 1e-7 and self.ring_on:
                self.s += 1
                self.ring.append({"s": self.s, "ev": self.s, "age": self.age, "dtM": 1.0,
                                  "hour": int(L.hour_of(self.age)), "min": 0, "on": not self.gone(),
                                  "HUNGER": self.st["hunger"], "THIRST": self.st["thirst"],
                                  "FATIGUE": self.st["fatigue"], "BOREDOM": 0.0, "UNHAPPINESS": 0.0,
                                  "NICOTINE_WITHDRAWAL": 0.0, "norec": True})

    def _step(self, sec):
        s = self.st
        if self.dead:
            self.age += sec / 3600.0
            return
        k = VM.HUNGER_INCREASE * self.sm * (1.2 if self.f.get("hunger_fast") else 1.0)
        decay = VM.food_timer_decay_per_s(90.0)
        rem = sec
        if s["food_timer"] > 0:
            rem -= min(rem, s["food_timer"] / decay)
        s["hunger"] = VM.hunger_step(s["hunger"], rem, k)
        s["food_timer"] = max(0.0, s["food_timer"] - decay * sec)
        s["thirst"] = VM.clamp(s["thirst"] + VM.THIRST_INCREASE * self.sm * (1.5 if self.f.get("thirst_fast") else 1)
                               * sec, 0.0, 1.0)
        w = s["weight"]
        if not self.f.get("weight_flat"):
            s["weight"] = w + VM.weight_rate(w, s["calories"], s["carbs"], s["lipids"]) * sec
        s["calories"] = VM.clamp(s["calories"] - VM.burn_rate("idle", w) * (1.2 if self.f.get("burn_high") else 1.0)
                                 * sec, VM.CAL_MIN, VM.CAL_MAX)
        s["carbs"] = VM.clamp(s["carbs"] - VM.CARB_DRAIN * sec, VM.MACRO_MIN, VM.MACRO_MAX)
        s["lipids"] = VM.clamp(s["lipids"] - VM.LIPID_DRAIN * sec, VM.MACRO_MIN, VM.MACRO_MAX)
        s["proteins"] = VM.clamp(s["proteins"] - VM.PROTEIN_DRAIN * sec, VM.MACRO_MIN, VM.MACRO_MAX)
        red = VM.DRUNK_REDUCTION * VM.multiplier_units_per_hour(90.0) / 3600.0 * (0.8 if self.f.get("intox_slow")
                                                                                   else 1.0)
        s["intox"] = max(0.0, s["intox"] - red * sec)
        hl = VM.moodle_level(s["hunger"], VM.HUNGRY_THRESHOLDS)
        tl = VM.moodle_level(s["thirst"], VM.THIRST_THRESHOLDS)
        loss = 0.0 if self.f.get("no_death") else VM.health_loss_per_hour(hl, tl, 90.0)
        s["health"] = max(0.0, s["health"] - loss * (1.5 if self.f.get("health_fast") else 1.0) * sec / 3600.0)
        if s["health"] <= 0.0:
            self.dead = True
        self.age += sec / 3600.0

    def gone(self):
        return bool(self.f.get("leave_at_death") and self.dead)

    # -- the actions
    def do_eat(self, full):
        s = self.st
        f = L.VANILLA_FOODS[full]
        self.inv[full] -= 1
        hc = f["hunger_script"] / 100.0
        s["hunger"] = VM.clamp(s["hunger"] + hc, 0.0, 1.0)
        s["calories"] = VM.clamp(s["calories"] + (0.0 if self.f.get("no_cal") else f["calories"]), VM.CAL_MIN,
                                 VM.CAL_MAX)
        for k in ("carbs", "lipids", "proteins"):
            s[k] = VM.clamp(s[k] + f[k], VM.MACRO_MIN, VM.MACRO_MAX)
        if self.f.get("fill_always") or (s["hunger"] <= 0.0 and not self.f.get("no_fill")):
            s["food_timer"] = min(s["food_timer"] + abs(hc) * VM.FOOD_TIMER_PER_HUNGER, VM.FOOD_TIMER_CAP)

    def do_drink(self, full):
        s = self.st
        fluid, lit = self.fills.get(full, ("Water", 1.0))
        self.fills[full] = (fluid, 0.0)
        if fluid == "Coffee" and self.sleep_allowed:
            per = -0.04 if self.f.get("coffee_weak") else VM.COFFEE_FATIGUE_PER_L
            s["fatigue"] += per * lit
            if self.f.get("coffee_reset"):
                self.pending.append((self.t + 20.0, lambda: s.__setitem__("fatigue", 0.0)))
        elif fluid == "Beer":
            s["intox"] += VM.intoxication_gain(VM.BEER_ALCOHOL_PER_L * lit, s["hunger"])

    def set_done(self):
        if not self.exe:
            return
        self.exe = False
        raw = 300.0 if self.f.get("short_set") else 360.0
        f = 1.0 if self.f.get("factor_flat") else VM.protein_factor(self.st["proteins"])
        self.xp += raw * f
        while self.level < 10 and self.xp >= VM.total_xp_for_level(self.level + 1):
            self.level += 1
            if not self.f.get("no_band"):
                self.traits = [t for t in self.traits if L.norm(t) not in L.MUSCLE]
                b = L.band_of(self.level)
                if b:
                    self.traits.append("base:" + b)

    # -- the replies
    def nut(self):
        s = self.st
        return {"calories": s["calories"], "carbs": s["carbs"], "lipids": s["lipids"], "proteins": s["proteins"],
                "weight": s["weight"], "hunger": s["hunger"], "thirst": s["thirst"], "statsApi": True,
                "incWeight": False, "incWeightLot": False, "decWeight": False}

    def snapshot(self):
        s = self.st
        return dict(self.nut(), endurance=s["endurance"], fatigue=s["fatigue"], moodles={}, traits={},
                    traitList=list(self.traits) if self.traits else {}, traitRoute="CharacterTraits",
                    maxWeight=8.0, foodTimer=s["food_timer"], standardFoodTime=0.0, asleep=False, running=False,
                    sprinting=False, moving=False, worldAge=self.age, mult=self.speed * EFF, wall=self.t)

    def true_mult(self):
        return float(self.speed) + (0.5 if self.f.get("mult_lie") else 0.0)

    def rcon(self, cmd):
        m = re.match(r'settimespeed (\d+)', cmd)
        if m:
            self.speed = int(m.group(1))
            return True, "Time speed set to " + m.group(1)
        m = re.match(r'additem "admin" "([^"]+)" (\d+)', cmd)
        if m:
            self.inv[m.group(1)] = self.inv.get(m.group(1), 0) + int(m.group(2))
            return True, "Item " + m.group(1) + " Added in admin's inventory."
        return False, "Unknown command " + cmd

    def ask(self, node, cmd, args="", timeout=20):
        a = args.split()
        if cmd == "ping":
            return "pong"
        if cmd == "players":
            return [] if self.gone() else ["admin"]
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": int(L.hour_of(self.age)), "minutes": 0, "mult": self.speed * EFF,
                    "trueMult": self.true_mult(), "wall": self.t}
        if cmd == "time.multiplier":
            self.speed = float(a[0])
            return f"mult={self.true_mult()} eff={self.speed * EFF}"
        if cmd == "lua.read":
            v = {"SandboxVars.Nutrition": True, "SandboxVars.DayLength": 4, "SandboxVars.StatsDecrease": 3,
                 "SandboxVars.MultiplierConfig.Global": 1, "SandboxVars.MultiplierConfig.GlobalToggle": True,
                 "SandboxVars.MultiplierConfig.Strength": 1}
            return {"ok": True, "side": "server", "root": a[0], "n": len(a) - 1,
                    "values": {p: v[p] for p in a[1:] if p in v}, "tables": {}, "types": {},
                    "missing": {p: "nil" for p in a[1:] if p not in v} or {}}
        if cmd == "minute.ring":
            if a[1] == "start":
                self.ring_on, self.ring, self.s = True, [], 0
                return ring_start_reply(a[2:])
            if a[1] == "read":
                frm = int(a[2]) if len(a) > 2 else 1
                rows = [r for r in self.ring if r["s"] >= frm][:720]
                with open(os.path.join(self.dir, f"minute-ring-admin-{frm}.json"), "w", encoding="utf-8") as fh:
                    json.dump({"rows_list": rows, "paths": []}, fh)
                return ring_read_reply(self, frm, rows, len([r for r in self.ring if r["s"] >= frm]) > 720)
            self.ring_on = False
            return ring_stop_reply(self)
        if self.gone():
            return GONE                                   # every player handler's findPlayer miss
        if cmd == "stats.get":
            return self.snapshot()
        if cmd == "stats.all":
            s = self.st
            return {"side": "server", "user": "admin", "worldAge": self.age, "mult": self.speed * EFF, "wall": self.t,
                    "stats": {"Hunger": s["hunger"], "Thirst": s["thirst"], "Fatigue": s["fatigue"],
                              "Intoxication": s["intox"], "Boredom": 0.0, "Unhappiness": 0.0}, "missing": {}}
        if cmd == "stats.set":
            for k, v in zip(a[1::2], a[2::2]):
                self.st[k] = float(v)
            return dict(self.nut(), applied={k: "Stats:set" for k in a[1::2]})
        if cmd in ("nutrition.get", "nutrition.set"):
            if cmd == "nutrition.set":
                self.st[a[1]] = float(a[2])
            return self.nut()
        if cmd == "health.get":
            return {"ok": True, "side": "server", "overall": self.st["health"], "health": self.st["health"], "parts": {}}
        if cmd == "moodle.level":
            if a[1] not in ("FOOD_EATEN", "HUNGRY"):
                return {"ok": False, "side": "server", "user": "admin", "reason": "no MoodleType." + a[1]}
            s = self.st
            lv = (VM.food_eaten_level(s["food_timer"]) if a[1] == "FOOD_EATEN"
                  else VM.moodle_level(s["hunger"], VM.HUNGRY_THRESHOLDS))
            return {"ok": True, "side": "server", "user": "admin", "moodle": a[1],
                    "level": lv + (1 if self.f.get("moodle_off") else 0)}
        if cmd == "perk.xp":
            return {"perk": a[-1], "user": "admin", "side": "server", "xp": self.xp if a[-1] == "Strength" else 5.0,
                    "level": self.level if a[-1] == "Strength" else 5, "serverWorldAge": self.age}
        if cmd == "perk.park":
            b = self.xp
            self.xp = VM.total_xp_for_level(int(a[2]))
            return {"ok": True, "perk": "Strength", "levelBefore": self.level, "levelAfter": self.level,
                    "xpBefore": b, "xpAfter": self.xp, "target": self.xp}
        if cmd == "xp.grant":
            b = self.xp
            f = 1.5 if self.f.get("grant_factor") else VM.protein_factor(self.st["proteins"])
            self.xp += float(a[2]) * f
            return {"ok": True, "perk": "Strength", "amount": float(a[2]), "side": "server", "xpBefore": b,
                    "xpAfter": self.xp, "levelBefore": self.level, "levelAfter": self.level}
        if cmd == "item.get":
            n = self.inv.get(a[1], 0)
            return item_state(a[1], n, self.age) if n > 0 else f"no item {a[1]} in admin's inventory"
        if cmd == "fluid.fill":
            refused = bool(self.f.get("fill_refused"))
            if not refused:
                self.fills[a[1]] = (a[2], float(a[3]))
            out = {"ok": not refused, "side": "server", "fullType": a[1], "id": 2000, "spawned": False,
                   "requested": float(a[3]), "litres": 0.0 if refused else float(a[3]),
                   "fluid": None if refused else a[2], "capacity": 0.3}
            if refused:
                out["reason"] = "read-back differs"
            return out
        if cmd == "autodrink.probe":
            out = {"ok": True, "side": "server", "thirst": self.st["thirst"], "autoDrink": True, "item": None,
                   "litres": None, "fluid": None, "containers": len(self.fills) + len(self.f.get("carried") or ())}
            if self.f.get("probe_other"):                 # another full container sits first in the inventory
                out.update({"item": "Base.WhiskeyFull", "litres": 0.5, "fluid": "Whiskey"})
                return out
            if self.f.get("probe_item_only") and self.fills:  # another container of the SAME fluid sits first
                fluid, lit = list(self.fills.values())[-1]
                out.update({"item": "Base.OtherBottle", "litres": lit or 0.3, "fluid": fluid})
                return out
            for full, (fluid, lit) in list(self.fills.items()) + [(c, ("Water", 1.0)) for c in
                                                                 self.f.get("carried") or ()]:
                if (self.inv.get(full) or full in (self.f.get("carried") or ())) and lit > 0:
                    out.update({"item": full, "litres": lit, "fluid": fluid})
                    break
            return out
        if cmd == "witness.chain":
            if a[1] == "isDead":
                if self.f.get("no_isdead"):
                    return {"ok": False, "failedAt": 1, "error": "no member isDead", "hops": 1}
                return {"ok": True, "value": "true" if self.dead else "false", "hops": 1}
            return {"ok": True, "value": "pushups" if self.exe else "nil", "hops": 2}
        if cmd == "eat.action":
            if not self.inv.get(a[0]):
                return {"queued": True, "fraction": 1, "spawned": "client", "itemId": 9, "itemBefore": {},
                        "validStart": True, "maxTime": 160, "moodleFoodEaten": 0, "before": self.nut()}
            self.pending.append((self.t + 10.0, lambda full=a[0]: self.do_eat(full)))
            return {"queued": True, "fraction": 1, "spawned": "found", "itemId": 5, "itemBefore": {},
                    "validStart": True, "maxTime": 160, "moodleFoodEaten": 0, "before": self.nut()}
        if cmd == "drink.action":
            self.pending.append((self.t + 4.0, lambda full=a[0]: self.do_drink(full)))
            return {"queued": True, "percentage": 1.0, "spawned": "found", "itemId": 6, "filledRatioBefore": 1.0,
                    "before": self.nut()}
        if cmd == "exercise.do":
            self.exe = True
            self.pending.append((self.t + 80.0, self.set_done))
            return {"ok": True, "exercise": a[0], "minutes": int(a[1]), "queued": True, "queueLen": 1}
        if cmd == "action.cancel":
            self.exe = False
            return {"ok": True, "before": 1, "after": 0, "current": None, "started": True, "adding": False,
                    "stopped": True, "javaBefore": 1, "javaAfter": 0, "cleared": True}
        return {"error": f"fake: unknown {cmd}"}


def run_vanilla(key, flags=None, budget=1e9, world=None, anchor=None, speed=1, keep=False):
    d = world.dir if world is not None else tempfile.mkdtemp()
    w = world or Vanilla(d, flags, sleep_allowed=L.SESSIONS[key]["sleep"], speed=speed)
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={"admin": FakeClient("admin")}, ask=w.ask, budget_s=budget,
              clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = FakeServer(w, d)
    S = L.Sess(xs, key, run_dir=d)
    S.anchor = anchor
    try:
        S.body_run(S.phases())
        S.grade_all()
    finally:
        if not keep:
            shutil.rmtree(d, ignore_errors=True)
    assert not out["phase_errors"], out["phase_errors"]
    return {k: v["verdict"] for k, v in out["verdicts"].items()}, out, w


def run_v2(flags=None):
    """x443a, then x443b on the same world with x443a's anchor (the reuse boot; the world does not move between)."""
    d = tempfile.mkdtemp()
    w = Vanilla(d, flags)
    va, oa, _ = run_vanilla("V2a", world=w, keep=True)
    vb, ob, _ = run_vanilla("V2b", world=w, anchor=oa["checks"]["X"]["anchor"])
    return va, oa, vb, ob, w


def whys(out):
    return {k: v.get("observed", {}).get("why") for k, v in out["verdicts"].items() if v["verdict"] != "as_predicted"}


@pytest.mark.parametrize("key", ["V1a", "V1b", "V3", "V4"])
def test_vanilla_flow_as_predicted(key):
    v, out, w = run_vanilla(key)
    assert v and set(v.values()) == {"as_predicted"}, (v, whys(out))
    mi = out["model_inputs"]["scenario"]
    assert mi["start"]["hunger"] == pytest.approx(0.05, abs=0.01) and mi["events"]       # the read start, the events
    assert out["model_inputs"]["a0"] >= DL4_START                                         # a realistic start age
    assert out["checks"]["restore"]["ok"] is True and w.speed == 1                       # the clock restored
    assert out["checks"]["R"]["pages"]
    assert bool(out.get("unrun")) is (key == "V1b")                    # V1b's reads past the death are listed unrun
    assert all(r["ok"] and r["unit"] == L.SPEED_UNIT for r in out["speeds"])
    assert out["checks"]["S"]["probe"]["item"] is None


def test_v2_split_on_one_world():
    va, oa, vb, ob, w = run_v2()
    assert set(va.values()) == {"as_predicted"} and set(vb.values()) == {"as_predicted"}, (whys(oa), whys(ob))
    assert set(va) == {"V2a_hunger", "V2a_weight", "V2a_calories"}
    anchor = oa["checks"]["X"]["anchor"]
    assert ob["checks"]["X"]["anchor"] == anchor and anchor >= DL4_START
    ea = [e for e in oa["eats"] if e["landed"]]
    eb = [e for e in ob["eats"] if e["landed"]]
    assert len(ea) == 4 and len(eb) == 3 and w.inv[L.TUNA] == 0
    assert [round(e["landed_age"] - anchor) for e in ea + eb] == [0, 4, 8, 12, 24, 28, 32]
    assert oa["checks"]["X"]["end_age"] == pytest.approx(anchor + 18.0)
    assert ob["checks"]["X"]["end_age"] == pytest.approx(anchor + 36.0)
    assert not any(s["step"].startswith("X_cal") for s in ob["steps"])                  # x443b writes no store
    assert abs(oa["readings"]["weight_change"]["live"] - oa["readings"]["weight_change"]["model"]) < 0.02
    assert not oa["checks"]["X"]["late_eats"]


def test_v1a_reads_and_timer():
    v, out, w = run_vanilla("V1a")
    tb = [r for r in out["reads"]["timer"] if r["arm"] == "B"]
    assert len(tb) >= 8 and max(r["foodTimer"] for r in tb) > 2900          # 25 game minutes, one read a 10 s
    fz = out["verdicts"]["V1a_B_freeze"]["observed"]
    assert abs((fz["model_unfreeze_age"] - out["checks"]["B"]["eat"]["landed_age"]) * 60 - 17.33) < 0.1
    assert out["verdicts"]["V1a_B_moodle"]["observed"]["n"] >= 8 and out["checks"]["B"]["slow_ok"] is True


def test_a_moodle_name_off_moodletype_is_unmeasured(monkeypatch):
    monkeypatch.setattr(L, "MOODLE_FOOD_EATEN", "FoodEaten")      # the registry id: moodle.level answers ok false
    v, out, _w = run_vanilla("V1a")
    assert v["V1a_B_moodle"] == "unmeasured"
    assert out["reads"]["food_eaten"][0]["reason"] == "no MoodleType.FoodEaten"


def test_v1b_dies_and_stops():
    v, out, w = run_vanilla("V1b")
    assert w.dead and out["checks"]["X"]["dead"] and out["verdicts"]["V1b_death"]["verdict"] == "as_predicted"
    assert abs(out["checks"]["X"]["death"]["age"] - out["checks"]["X"]["write"]["ages"][0] - 36.4) < 0.3


def test_v1b_death_through_health_alone():
    # review M-5: witness.chain cannot read isDead; the health-0 fallback still reads the death
    v, out, w = run_vanilla("V1b", {"no_isdead": True})
    assert v["V1b_death"] == "as_predicted" and out["checks"]["X"]["death"]["dead_raw"] is None


def test_v1b_player_gone_at_death_is_unmeasured():
    # review M-1: the player leaves the online list at health 0: both reads answer "no online player admin"
    v, out, w = run_vanilla("V1b", {"leave_at_death": True})
    assert v["V1b_death"] == "unmeasured"
    assert out["verdicts"]["V1b_death"]["observed"]["why"] == "the player left the online list"
    assert out["reads"]["health"][-1]["gone"] is True


def test_an_eat_at_the_calorie_cap_still_lands():
    va, oa, vb, ob, _w = run_v2({"no_cal": True})                         # the store never moves at the eat
    eats = oa["eats"] + ob["eats"]
    assert len([e for e in eats if e["landed"]]) == 7
    assert all(e["landed_by"] == ["hunger"] or "timer" in e["landed_by"] for e in eats)
    assert va["V2a_calories"] == "falsified" and va["V2a_hunger"] == "as_predicted"


def test_v3_sets_and_band():
    v, out, w = run_vanilla("V3")
    assert w.level == 6 and w.traits == ["base:stout"]
    assert [out["verdicts"][f"V3_{a}"]["observed"]["delta"] for a in "ABC"] == pytest.approx([360.0, 540.0, 252.0])


@pytest.mark.parametrize("key, flag, names", [
    ("V1a", "no_fill", ("V1a_B_freeze", "V1a_B_timer")),
    ("V1a", "fill_always", ("V1a_A_timer", "V1a_A_hunger")),
    ("V1a", "hunger_fast", ("V1a_A_hunger",)),
    ("V1a", "thirst_fast", ("V1a_thirst",)),
    ("V1a", "moodle_off", ("V1a_B_moodle",)),
    ("V1a", "burn_high", ("V1a_calories",)),
    ("V1b", "hunger_fast", ("V1b_hunger", "V1b_level4")),
    ("V1b", "health_fast", ("V1b_health", "V1b_death")),
    ("V1b", "no_death", ("V1b_health", "V1b_death")),
    ("V1b", "weight_flat", ("V1b_weight",)),
    ("V3", "short_set", ("V3_A",)),
    ("V3", "factor_flat", ("V3_B", "V3_C")),
    ("V3", "grant_factor", ("V3_B_grant",)),
    ("V3", "no_band", ("V3_B_level",)),
    ("V4", "coffee_weak", ("V4_A_coffee",)),
    ("V4", "coffee_reset", ("V4_A_holds",)),
    ("V4", "intox_slow", ("V4_B_decay", "V4_B_zero")),
])
def test_vanilla_defects(key, flag, names):
    v, out, _w = run_vanilla(key, {flag: True})
    for n in names:
        assert v[n] == "falsified", (n, v, whys(out))


@pytest.mark.parametrize("flag, names", [("hunger_fast", ("V2a_hunger", "V2b_hunger")),
                                         ("weight_flat", ("V2a_weight", "V2b_weight")),
                                         ("burn_high", ("V2a_calories", "V2b_calories"))])
def test_v2_defects(flag, names):
    va, oa, vb, ob, _w = run_v2({flag: True})
    v = dict(va, **vb)
    for n in names:
        assert v[n] == "falsified", (n, v)


def test_restore_returns_the_read_speed():
    # review M-4: the world starts at speed 3; the restore puts 3 back, not 1
    v, out, w = run_vanilla("V1a", speed=3)
    assert out["checks"]["restore"]["restore_to"] == 3 and out["checks"]["restore"]["ok"] is True and w.speed == 3
    assert set(v.values()) == {"as_predicted"}, whys(out)


def test_a_clock_that_reads_off_is_recorded_and_gates_v1a_slow_window():
    # review M-3 and M-4: trueMult answers off the settimespeed number: every speed row ok false, the restore not ok,
    # V1a_B_timer unmeasured (its cadence assumes speed 1); the other grades run on world ages
    v, out, w = run_vanilla("V1a", {"mult_lie": True})
    assert out["checks"]["restore"]["ok"] is False and not any(r["ok"] for r in out["speeds"])
    assert v["V1a_B_timer"] == "unmeasured" and v["V1a_B_freeze"] == "as_predicted"
    assert any("trueMult" in n["note"] for n in out["notes"])


def test_a_refused_fill_leaves_the_model():
    # review M-2: a refused fill drops the drink from the model; V4's grades read unmeasured, never a pass or a fail
    v, out, _w = run_vanilla("V4", {"fill_refused": True})
    assert v["V4_A_coffee"] == "unmeasured" and v["V4_B_decay"] == "unmeasured" and v["V4_B_zero"] == "unmeasured"
    assert not [e for e in out["model_inputs"]["scenario"]["events"] if e["kind"] == "drink"]
    assert all(d["fill_ok"] is False for d in out["drinks"])


def test_a_drink_that_lands_past_a_failed_gate_leaves_the_model():
    # review M-2: the fill succeeded and the drinks landed, but the probe's first container is another: the gate fails,
    # so no drink enters the model and V4's grades read unmeasured
    v, out, _w = run_vanilla("V4", {"probe_other": True})
    assert all(d["landed"] and d["fill_ok"] is False for d in out["drinks"])
    assert not [e for e in out["model_inputs"]["scenario"]["events"] if e["kind"] == "drink"]
    assert v["V4_A_coffee"] == "unmeasured" and v["V4_B_decay"] == "unmeasured"


def test_the_gate_reads_the_probe_item_alone():
    # re-review N-3: the probe's first container holds the drink's own fluid but is another item: the gate fails
    v, out, _w = run_vanilla("V4", {"probe_item_only": True})
    assert all(d["fill_ok"] is False for d in out["drinks"])
    assert not [e for e in out["model_inputs"]["scenario"]["events"] if e["kind"] == "drink"]


def test_v3_budget_stop_skips_its_later_arms():
    # re-review R-1: V3 names an arm C; a budget stop in arm A skips B and C (no C_* write, no set left running),
    # still restores the clock and reads the ring, and keeps the first budget_stop record
    v, out, w = run_vanilla("V3", budget=30.0)
    assert out["budget_stop"]["phase"] == "A" and out["skipped_phases"] == ["B", "C"]
    assert not any(s["step"].startswith("B_") or (s["step"].startswith("C_") and not s["step"].startswith("C_restore"))
                   for s in out["steps"])                               # the arm's writes; C_restore is phase Z's
    assert out["checks"]["restore"]["ok"] is True and w.speed == 1 and out["checks"]["R"]["pages"]
    assert [b["phase"] for b in out["budget_stops"]] == ["A"]


def test_the_first_budget_stop_is_kept():
    # re-review R-1: a closing phase that also hits the budget never overwrites the first stop's record
    out = fresh_out()
    S = L.Sess(X.Xs(out, node=str, ask=lambda *a, **k: {}), "V1a")

    def stop():
        raise X.Budget("past")

    def stop_closing():
        raise X.Budget("past again")
    S.restore_clock = stop_closing              # a closing phase by function, raising the budget again
    S.body_run((("A", stop), ("B", stop), ("C", S.restore_clock)))
    assert out["budget_stop"]["phase"] == "A" and out["skipped_phases"] == ["B"]
    assert [b["phase"] for b in out["budget_stops"]] == ["A", "C"]


def test_run_to_records_unrun_on_a_budget_stop():
    w = Vanilla(tempfile.mkdtemp())
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={}, ask=w.ask, clock=w.clock, sleep=w.sleep, budget_s=3.0)
    S = L.Sess(xs, "V1a")
    a = w.age
    with pytest.raises(X.Budget):
        S.run_to(a + 5.0, [(a + 4.0, "read", lambda x: None)], L.SPEED_FAST, "T")
    assert out["unrun"] and out["unrun"][0]["age"] == pytest.approx(a + 4.0)


def test_a_carried_container_is_noted():
    v, out, _w = run_vanilla("V1a", {"carried": ["Base.WaterBottle"]})
    assert out["checks"]["S"]["probe"]["item"] == "Base.WaterBottle"
    assert any("carries a filled container" in n["note"] for n in out["notes"])


def test_v4_zeroes_thirst_at_the_start():
    v, out, _w = run_vanilla("V4")
    assert out["checks"]["S"]["thirst"]["values"] == {"thirst": 0.0}


def test_budget_stop_skips_the_later_scenario_phases():
    # review M-12: after the budget stops arm A, arm B never writes; the restore and the ring read still run
    v, out, w = run_vanilla("V1a", budget=30.0)
    assert out["budget_stop"]["phase"] == "A" and out["skipped_phases"] == ["B"]
    assert not any(s["step"].startswith("B_") for s in out["steps"])
    assert out["checks"]["restore"]["ok"] is True and w.speed == 1 and out["checks"]["R"]["pages"]
    assert "model_inputs" in out


def test_spawned_client_stops_the_eats(tmp_path):
    d = str(tmp_path)
    w = Vanilla(d)
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={}, ask=w.ask, clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = FakeServer(w, d)
    S = L.Sess(xs, "V1a", run_dir=d)
    S.v1a_S = lambda: (S.phase_S(), None)                       # no spawn: eat.action answers "client"
    S.body_run((("S", S.v1a_S), ("A", S.v1a_A)))
    assert out["phase_walls"]["A"].get("stop_eats") and "client" in out["stop_reason"]


# ---------------------------------------------------------------- the modded sessions against a fake bus
class Modded:
    """A minimal modded world: the store's save, the intake and sip counters, the ring with the record paths, a
    request-driven HUNGER, the drinks and the night's booked sleep, every reply in the harness's own shape. It runs
    the phases, not the mechanics."""

    def __init__(self, results_dir, age=DL1_START, speed=1, flags=None):
        self.f = flags or {}
        self.dir = results_dir
        self.t, self.age, self.speed = 0.0, age, speed
        self.hunger, self.thirst = 0.1, 0.05
        self.eats = self.landed = self.sips = 0
        self.lw = 100.0
        self.ring, self.ring_on, self.s, self.paths = [], False, 0, []
        self.pending, self.inv, self.slept, self.hold = [], {}, 0.0, False
        self.fills = {}

    def clock(self):
        return self.t

    def sleep(self, dt):
        end = self.t + dt
        while self.t < end - 1e-12:
            due = min([p[0] for p in self.pending if p[0] > self.t] + [end])
            step = due - self.t
            mins = step / 0.625 * self.speed * (20.0 if self.hold else 1.0)
            n0 = math.floor(self.age * 60.0)
            self.age += mins / 60.0
            self.hunger = min(1.0, self.hunger + 0.0006 * mins)
            if self.hold:
                self.slept += mins / 60.0
            self.lw += step * 1000.0
            if self.ring_on:
                for k in range(n0 + 1, math.floor(self.age * 60.0) + 1):
                    self.s += 1
                    row = {"s": self.s, "ev": self.s, "age": k / 60.0, "dtM": 1.0, "hour": int(L.hour_of(k / 60.0)),
                           "min": k % 60, "on": True, "HUNGER": self.hunger, "THIRST": self.thirst,
                           L.EATS_G: self.eats, L.LANDED_G: self.landed, L.SIPS_G: self.sips,
                           L.SLEPT: self.slept if self.hold else 0.0}
                    self.ring.append(row)
            self.t = due
            for p in [p for p in self.pending if p[0] <= self.t + 1e-12]:
                self.pending.remove(p)
                p[1]()

    def rcon(self, cmd):
        m = re.match(r'settimespeed (\d+)', cmd)
        if m:
            self.speed = int(m.group(1))
            return True, "Time speed set to " + m.group(1)
        m = re.match(r'additem "admin" "([^"]+)" (\d+)', cmd)
        if m:
            self.inv[m.group(1)] = self.inv.get(m.group(1), 0) + int(m.group(2))
            return True, "Item " + m.group(1) + " Added in admin's inventory."
        return False, "Unknown command " + cmd

    def eat_done(self, full):
        self.inv[full] -= 1
        self.eats += 1
        self.landed += 1
        self.hunger = 0.0

    def drink_done(self, full):
        self.inv[full] -= 1
        self.fills[full] = (self.fills.get(full, ("Water", 0.0))[0], 0.0)
        self.sips += 2

    def ask(self, node, cmd, args="", timeout=20):
        a = args.split()
        if cmd == "ping":
            return "pong"
        if cmd == "players":
            return ["admin"]
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": int(L.hour_of(self.age)), "minutes": 0, "mult": self.speed * EFF,
                    "trueMult": float(self.speed), "wall": self.t}
        if cmd == "time.multiplier":
            self.speed = float(a[0])
            return f"mult={float(self.speed)} eff={self.speed * EFF}"
        if cmd == "lua.read":
            v = {"NutritionRevamp.server.store.file.lastWrite.admin": self.lw,
                 "NutritionRevamp.server.intake.stats.eats": self.eats,
                 "NutritionRevamp.server.intake.stats.landed": self.landed,
                 "NutritionRevamp.server.intake.stats.sips": self.sips, L.SLEPT: self.slept,
                 "SandboxVars.Nutrition": False, "SandboxVars.DayLength": 1, "NutritionRevamp.version": "1.0.0"}
            vals_ = {p: v.get(p, 0.0) for p in a[1:]}
            return {"ok": True, "side": "server", "root": a[0], "n": len(vals_), "values": vals_, "tables": {},
                    "types": {}, "missing": {}}
        if cmd == "lua.global":
            rec = {"gen": 1, "rec": {"satiety": {"t": self.age}}, "done": True}
            return {"side": "server", "name": a[0], "resolved": True, "type": "string", "value": json.dumps(rec)}
        if cmd == "minute.ring":
            if a[1] == "start":
                self.ring_on, self.paths = True, a[2:]
                return ring_start_reply(self.paths)
            if a[1] == "read":
                with open(os.path.join(self.dir, "minute-ring-admin-1.json"), "w", encoding="utf-8") as fh:
                    json.dump({"rows_list": self.ring, "paths": self.paths}, fh)
                return ring_read_reply(self, 1, self.ring, False)
            return ring_stop_reply(self)
        if cmd == "stats.all":
            return {"side": "server", "user": "admin", "worldAge": self.age, "mult": self.speed * EFF, "wall": self.t,
                    "stats": {"Hunger": self.hunger, "Thirst": self.thirst, "Fatigue": 0.1, "Boredom": 0.0,
                              "Unhappiness": 0.0, "NicotineWithdrawal": 0.0}, "missing": {}}
        if cmd == "nutrition.get":
            return {"calories": 1000.0, "carbs": 100.0, "lipids": 40.0, "proteins": 60.0, "weight": 65.0,
                    "hunger": self.hunger, "thirst": self.thirst, "statsApi": True, "incWeight": False,
                    "incWeightLot": False, "decWeight": False}
        if cmd == "item.get":
            n = self.inv.get(a[1], 0)
            return item_state(a[1], n, self.age) if n else f"no item {a[1]} in admin's inventory"
        if cmd == "foodtimer.set":
            return {"requested": 0, "before": 0, "set": True, "after": 0}
        if cmd == "eat.action":
            self.pending.append((self.t + 5.0, lambda f=a[0]: self.eat_done(f)))
            return {"queued": True, "fraction": 1, "spawned": "found", "itemId": 7, "itemBefore": {},
                    "validStart": True, "maxTime": 160, "moodleFoodEaten": 0, "before": {}}
        if cmd == "fluid.fill":
            refused = bool(self.f.get("fill_refused"))
            if not refused:
                self.fills[a[1]] = (a[2], float(a[3]))
            return {"ok": not refused, "side": "server", "fullType": a[1], "id": 3000, "spawned": False,
                    "requested": float(a[3]), "litres": 0.0 if refused else float(a[3]),
                    "fluid": None if refused else a[2], "capacity": 0.3}
        if cmd == "autodrink.probe":
            out = {"ok": True, "side": "server", "thirst": self.thirst, "autoDrink": True, "item": None,
                   "litres": None, "fluid": None, "containers": len(self.fills)}
            for full, (fluid, lit) in self.fills.items():
                if self.inv.get(full) and lit > 0:
                    out.update({"item": full, "litres": lit, "fluid": fluid})
                    break
            return out
        if cmd == "drink.action":
            self.pending.append((self.t + 3.0, lambda f=a[0]: self.drink_done(f)))
            return {"queued": True, "percentage": 1.0, "spawned": "found", "itemId": 8, "filledRatioBefore": 1.0,
                    "before": {}}
        if cmd == "player.sleep.hold":
            self.hold = a[1] != "0"
            if not self.hold:
                self.slept = 0.0
            return {"user": "admin", "seconds": float(a[1]), "before": False, "after": self.hold, "armed": self.hold,
                    "deadlineWall": self.t + float(a[1])}
        if cmd == "player.sleep":
            return {"requested": False, "before": False, "setAsleep": True, "after": False, "held": False}
        return {"error": f"fake: unknown {cmd}"}


def run_modded(key, tmp_path, monkeypatch, age=DL1_START, speed=1, flags=None):
    d = str(tmp_path)
    w = Modded(d, age=age, speed=speed, flags=flags)
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={"admin": FakeClient("admin")}, ask=w.ask, budget_s=1e9,
              clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = FakeServer(w, d)
    S = L.Sess(xs, key, run_dir=d)
    seen = {}
    real = L.replay_grade

    def spy(ring_rows, events, start, sleep_allowed, tol, **kw):
        seen["sleep_allowed"] = sleep_allowed
        seen["events"] = events
        return real(ring_rows, events, start, sleep_allowed, tol, **kw)
    monkeypatch.setattr(L, "replay_grade", spy)
    S.body_run(S.phases())
    assert not out["phase_errors"], out["phase_errors"]
    return S, out, w, seen, d


@pytest.mark.parametrize("key, age", [("M1", DL1_START), ("M2", 3.3), ("M2", 5.5)])
def test_modded_flow_runs_its_phases(key, age, tmp_path, monkeypatch):
    S, out, w, seen, d = run_modded(key, tmp_path, monkeypatch, age=age, speed=3)
    assert os.path.isfile(os.path.join(d, "start.json")) and S.eats and all(e["landed"] for e in S.eats)
    assert out["checks"]["restore"]["ok"] is True and w.speed == 3                      # the read speed restored
    assert len(out["checks"]["H"]["ring_paths"]) <= 32 and not out.get("unrun")
    if key == "M2":
        assert [d_["fluid"] for d_ in S.drinks] == ["Coffee"] * 3 + ["Beer"] * 4                # three and four
        assert all(d_["fill_ok"] for d_ in S.drinks)
        n = out["checks"]["X"]["nights"][0]
        assert n["reached"] is True and n["booked_h"] >= L.M2_NIGHT_H and "#2956" in n["note"]
        plan = out["checks"]["X"]["plan"]
        assert plan["coffees"][0] >= age and plan["ok"] and plan["end"] > plan["night"]
    S.grade_all()
    assert out["verdicts"]["H1"]["verdict"] == "as_predicted" and out["verdicts"]["RING"]["verdict"] == "as_predicted"
    # the HEAD replay ran over the fake's ring: the fake's HUNGER and THIRST are not the mod's, so they are falsified,
    # and the energy state the fake never rings is unmeasured, never a pass
    assert out["replay"]["rows"] > 100
    assert out["verdicts"][f"{key}_replay_HUNGER"]["verdict"] == "falsified"
    assert out["verdicts"][f"{key}_replay_body.energyState"]["verdict"] == "unmeasured"
    assert seen["sleep_allowed"] is (key == "M2")                                       # review M-6
    assert out["model_inputs"]["sleep_allowed"] is (key == "M2")
    assert os.path.isfile(os.path.join(d, "events.json")) and os.path.isfile(os.path.join(d, "replay.json"))
    ev = json.load(open(os.path.join(d, "events.json"), encoding="utf-8"))
    assert [e["kind"] for e in ev].count("eat") == len(S.eats)
    if key == "M2":
        assert any(e["kind"] == "sleep" for e in ev) and "M2_hangover" in out["verdicts"]
        assert [e["kind"] for e in ev].count("drink") >= 7


def test_modded_refused_fill_leaves_the_replay(tmp_path, monkeypatch):
    S, out, w, seen, d = run_modded("M2", tmp_path, monkeypatch, flags={"fill_refused": True})
    assert S.drinks and not any(d_["fill_ok"] for d_ in S.drinks)
    S.grade_all()
    assert not [e for e in seen["events"] if e["kind"] == "drink"]
    assert any("fill gate" in n["note"] for n in out["notes"])
