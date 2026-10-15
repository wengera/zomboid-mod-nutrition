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
    assert L.prerun("V2")["weight_change_36h"] > 1.0


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
        assert b < 560.0, (drv, b)


# ---------------------------------------------------------------- the fake vanilla world
WALL_GAME_S = 16.0               # game seconds a wall second at DayLength 4, speed 1 (a game minute is 3.75 s)


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


class Vanilla:
    """A vanilla world on the model's own rate functions (VM1-VM16), stepped at most a game minute at a time, with a
    ring row at every game-minute boundary; `flags` move one mechanism off the model."""

    def __init__(self, results_dir, flags=None, sleep_allowed=False, age=0.4):
        self.f = flags or {}
        self.dir = results_dir
        self.sleep_allowed = sleep_allowed
        self.t, self.age, self.speed = 0.0, age, 1
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

    # -- the clock
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
                self.ring.append({"s": self.s, "age": self.age, "on": True, "HUNGER": self.st["hunger"],
                                  "THIRST": self.st["thirst"], "FATIGUE": self.st["fatigue"], "BOREDOM": 0.0,
                                  "UNHAPPINESS": 0.0, "norec": True})

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

    # -- the bus
    def snapshot(self):
        s = self.st
        return {"calories": s["calories"], "carbs": s["carbs"], "lipids": s["lipids"], "proteins": s["proteins"],
                "weight": s["weight"], "hunger": s["hunger"], "thirst": s["thirst"], "endurance": s["endurance"],
                "fatigue": s["fatigue"], "foodTimer": s["food_timer"], "standardFoodTime": 0.0,
                "traitList": list(self.traits) if self.traits else {}, "worldAge": self.age, "wall": self.t,
                "asleep": False, "moving": False}

    def rcon(self, cmd):
        m = re.match(r'settimespeed (\d+)', cmd)
        if m:
            self.speed = int(m.group(1))
            return True, "ok"
        m = re.match(r'additem "admin" "([^"]+)" (\d+)', cmd)
        if m:
            self.inv[m.group(1)] = self.inv.get(m.group(1), 0) + int(m.group(2))
            return True, "added"
        return False, "unknown"

    def ask(self, node, cmd, args="", timeout=20):
        a = args.split()
        if cmd == "ping":
            return "pong"
        if cmd == "players":
            return ["admin"]
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": int(L.hour_of(self.age)), "minutes": 0, "mult": self.speed * 4.7,
                    "trueMult": float(self.speed), "wall": self.t}
        if cmd == "time.multiplier":
            self.speed = float(a[0])
            return f"multiplier {a[0]}"
        if cmd == "lua.read":
            v = {"SandboxVars.Nutrition": True, "SandboxVars.DayLength": 4, "SandboxVars.StatsDecrease": 3,
                 "SandboxVars.MultiplierConfig.Global": 1, "SandboxVars.MultiplierConfig.GlobalToggle": True,
                 "SandboxVars.MultiplierConfig.Strength": 1}
            return {"ok": True, "side": "server", "root": a[0], "n": len(a) - 1,
                    "values": {p: v[p] for p in a[1:] if p in v}, "tables": {}, "types": {},
                    "missing": {p: "nil" for p in a[1:] if p not in v}}
        if cmd == "minute.ring":
            if a[1] == "start":
                self.ring_on = True
                return {"ok": True, "side": "server", "user": "admin", "armed": True, "cap": 4320, "paths": {}}
            if a[1] == "read":
                frm = int(a[2]) if len(a) > 2 else 1
                rows = [r for r in self.ring if r["s"] >= frm][:720]
                name = f"minute-ring-admin-{frm}"
                with open(os.path.join(self.dir, name + ".json"), "w", encoding="utf-8") as fh:
                    json.dump({"rows_list": rows, "paths": []}, fh)
                more = len([r for r in self.ring if r["s"] >= frm]) > 720
                return {"ok": True, "side": "server", "user": "admin", "from": frm, "rows": len(rows), "skipped": 0,
                        "next": frm + len(rows) if more else None, "more": more, "errors": 0, "result": name}
            self.ring_on = False
            return {"ok": True, "side": "server", "user": "admin", "stopped": True, "recorded": self.s}
        if cmd == "stats.get":
            return self.snapshot()
        if cmd == "stats.all":
            s = self.st
            return {"side": "server", "user": "admin", "worldAge": self.age, "mult": 1.0, "wall": self.t,
                    "stats": {"HUNGER": s["hunger"], "THIRST": s["thirst"], "FATIGUE": s["fatigue"],
                              "INTOXICATION": s["intox"]}, "missing": {}}
        if cmd == "stats.set":
            for k, v in zip(a[1::2], a[2::2]):
                self.st[k] = float(v)
            return dict(self.snapshot(), applied={k: "stats" for k in a[1::2]})
        if cmd in ("nutrition.get", "nutrition.set"):
            if cmd == "nutrition.set":
                self.st[a[1]] = float(a[2])
            return self.snapshot()
        if cmd == "health.get":
            return {"ok": True, "side": "server", "overall": self.st["health"], "health": self.st["health"], "parts": {}}
        if cmd == "moodle.level":
            s = self.st
            lv = (VM.food_eaten_level(s["food_timer"]) if a[1] == "FoodEaten"
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
                    "xpBefore": b, "xpAfter": self.xp}
        if cmd == "xp.grant":
            b = self.xp
            f = 1.5 if self.f.get("grant_factor") else VM.protein_factor(self.st["proteins"])
            self.xp += float(a[2]) * f
            return {"ok": True, "perk": "Strength", "amount": float(a[2]), "side": "server", "xpBefore": b,
                    "xpAfter": self.xp, "levelBefore": self.level, "levelAfter": self.level}
        if cmd == "item.get":
            n = self.inv.get(a[1], 0)
            return {"fullType": a[1], "id": 1000 + n} if n > 0 else {"fullType": a[1]}
        if cmd == "fluid.fill":
            self.fills[a[1]] = (a[2], float(a[3]))
            return {"ok": True, "side": "server", "fullType": a[1], "litres": float(a[3]), "fluid": a[2]}
        if cmd == "autodrink.probe":
            for full, (fluid, lit) in self.fills.items():
                if self.inv.get(full) and lit > 0:
                    return {"ok": True, "item": full, "litres": lit, "fluid": fluid, "containers": len(self.fills)}
            return {"ok": True, "containers": len(self.fills)}
        if cmd == "witness.chain":
            if a[1] == "isDead":
                return {"ok": True, "value": "true" if self.dead else "false", "hops": 1}
            return {"ok": True, "value": "pushups" if self.exe else "nil", "hops": 2}
        if cmd == "eat.action":
            if not self.inv.get(a[0]):
                return {"queued": True, "spawned": "client"}
            self.pending.append((self.t + 10.0, lambda full=a[0]: self.do_eat(full)))
            return {"queued": True, "fraction": 1, "spawned": "found", "itemId": 5}
        if cmd == "drink.action":
            self.pending.append((self.t + 4.0, lambda full=a[0]: self.do_drink(full)))
            return {"queued": True, "percentage": 1, "spawned": "found", "itemId": 6}
        if cmd == "exercise.do":
            self.exe = True
            self.pending.append((self.t + 80.0, self.set_done))
            return {"ok": True, "exercise": a[0], "minutes": int(a[1]), "queued": True, "queueLen": 1}
        if cmd == "action.cancel":
            self.exe = False
            return {"ok": True}
        return {"error": f"fake: unknown {cmd}"}


def run_vanilla(key, flags=None, budget=1e9):
    d = tempfile.mkdtemp()
    w = Vanilla(d, flags, sleep_allowed=L.SESSIONS[key]["sleep"])
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={"admin": FakeClient("admin")}, ask=w.ask, budget_s=budget,
              clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = FakeServer(w, d)
    S = L.Sess(xs, key, run_dir=d)
    try:
        S.body_run(S.phases())
        S.grade_all()
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert not out["phase_errors"], out["phase_errors"]
    return {k: v["verdict"] for k, v in out["verdicts"].items()}, out, w


def whys(out):
    return {k: v.get("observed", {}).get("why") for k, v in out["verdicts"].items() if v["verdict"] != "as_predicted"}


@pytest.mark.parametrize("key", ["V1a", "V1b", "V2", "V3", "V4"])
def test_vanilla_flow_as_predicted(key):
    v, out, w = run_vanilla(key)
    assert v and set(v.values()) == {"as_predicted"}, (v, whys(out))
    mi = out["model_inputs"]["scenario"]
    assert mi["start"]["hunger"] == pytest.approx(0.05, abs=0.01) and mi["events"]       # the read start, the events
    assert out["checks"]["restore"]["ok"] is True and w.speed == 1                       # the clock restored
    assert out["checks"]["R"]["pages"]


def test_v1a_reads_and_timer():
    v, out, w = run_vanilla("V1a")
    tb = [r for r in out["reads"]["timer"] if r["arm"] == "B"]
    assert len(tb) >= 8 and max(r["foodTimer"] for r in tb) > 2900          # 25 game minutes, one read a 10 s
    fz = out["verdicts"]["V1a_B_freeze"]["observed"]
    assert abs((fz["model_unfreeze_age"] - out["checks"]["B"]["eat"]["landed_age"]) * 60 - 17.33) < 0.1


def test_v1b_dies_and_stops():
    v, out, w = run_vanilla("V1b")
    assert w.dead and out["checks"]["X"]["dead"] and out["verdicts"]["V1b_death"]["verdict"] == "as_predicted"
    assert abs(out["checks"]["X"]["death"]["age"] - out["checks"]["X"]["write"]["ages"][0] - 36.4) < 0.3


def test_v2_eats_seven_and_restores():
    v, out, w = run_vanilla("V2")
    landed = [e for e in out["eats"] if e["landed"]]
    assert len(landed) == 7 and w.inv[L.TUNA] == 0
    rc = out["readings"]["weight_change"]
    assert rc["model"] > 1.0 and abs(rc["live"] - rc["model"]) < 0.02


def test_an_eat_at_the_calorie_cap_still_lands():
    v, out, w = run_vanilla("V2", {"no_cal": True})                        # the store never moves at the eat
    assert len([e for e in out["eats"] if e["landed"]]) == 7
    assert all(e["landed_by"] == ["hunger"] or "timer" in e["landed_by"] for e in out["eats"])
    assert v["V2_calories"] == "falsified" and v["V2_hunger"] == "as_predicted"


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
    ("V2", "hunger_fast", ("V2_hunger",)),
    ("V2", "weight_flat", ("V2_weight",)),
    ("V2", "burn_high", ("V2_calories",)),
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


def test_budget_stop_still_restores_and_reads():
    v, out, w = run_vanilla("V2", budget=60.0)
    assert out["budget_stop"]["phase"] == "X"
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
    request-driven HUNGER, the drinks and the night's booked sleep. It runs the phases, not the mechanics."""

    def __init__(self, results_dir):
        self.dir = results_dir
        self.t, self.age, self.speed = 0.0, 2.0, 1
        self.hunger, self.thirst = 0.1, 0.05
        self.eats = self.landed = self.sips = 0
        self.lw = 100.0
        self.ring, self.ring_on, self.s, self.paths = [], False, 0, []
        self.pending, self.inv, self.slept, self.hold = [], {}, 0.0, False

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
                    row = {"s": self.s, "age": k / 60.0, "on": True, "HUNGER": self.hunger, "THIRST": self.thirst,
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
            return True, "ok"
        m = re.match(r'additem "admin" "([^"]+)" (\d+)', cmd)
        if m:
            self.inv[m.group(1)] = self.inv.get(m.group(1), 0) + int(m.group(2))
            return True, "added"
        return False, "?"

    def eat_done(self, full):
        self.inv[full] -= 1
        self.eats += 1
        self.landed += 1
        self.hunger = 0.0

    def drink_done(self, full):
        self.inv[full] -= 1
        self.sips += 2

    def ask(self, node, cmd, args="", timeout=20):
        a = args.split()
        if cmd == "ping":
            return "pong"
        if cmd == "players":
            return ["admin"]
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": int(L.hour_of(self.age)), "minutes": 0, "mult": 1.0,
                    "trueMult": float(self.speed), "wall": self.t}
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
                return {"ok": True, "side": "server", "user": "admin", "armed": True}
            if a[1] == "read":
                name = "minute-ring-admin-1"
                with open(os.path.join(self.dir, name + ".json"), "w", encoding="utf-8") as fh:
                    json.dump({"rows_list": self.ring, "paths": self.paths}, fh)
                return {"ok": True, "from": 1, "rows": len(self.ring), "next": None, "more": False, "errors": 0,
                        "result": name}
            return {"ok": True, "stopped": True}
        if cmd == "stats.all":
            return {"side": "server", "worldAge": self.age, "stats": {"HUNGER": self.hunger, "THIRST": self.thirst}}
        if cmd == "nutrition.get":
            return {"calories": 1000.0, "carbs": 100.0, "lipids": 40.0, "proteins": 60.0, "weight": 65.0}
        if cmd == "item.get":
            n = self.inv.get(a[1], 0)
            return {"fullType": a[1], "id": 7 + n} if n else {"fullType": a[1]}
        if cmd == "foodtimer.set":
            return {"requested": 0, "before": 0, "set": True, "after": 0}
        if cmd == "eat.action":
            self.pending.append((self.t + 5.0, lambda f=a[0]: self.eat_done(f)))
            return {"queued": True, "fraction": 1, "spawned": "found", "itemId": 7}
        if cmd == "fluid.fill":
            return {"ok": True, "litres": float(a[3]), "fluid": a[2]}
        if cmd == "autodrink.probe":
            return {"ok": True, "item": None, "litres": None, "containers": 0}
        if cmd == "drink.action":
            self.pending.append((self.t + 3.0, lambda f=a[0]: self.drink_done(f)))
            return {"queued": True, "percentage": 1, "spawned": "found", "itemId": 8}
        if cmd == "player.sleep.hold":
            self.hold = a[1] != "0"
            if not self.hold:
                self.slept = 0.0
            return {"user": "admin", "armed": self.hold}
        if cmd == "player.sleep":
            return {"requested": False, "after": False}
        return {"error": f"fake: unknown {cmd}"}


@pytest.mark.parametrize("key", ["M1", "M2"])
def test_modded_flow_runs_its_phases(key, tmp_path):
    d = str(tmp_path)
    w = Modded(d)
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={"admin": FakeClient("admin")}, ask=w.ask, budget_s=1e9,
              clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = FakeServer(w, d)
    S = L.Sess(xs, key, run_dir=d)
    S.body_run(S.phases())
    assert not out["phase_errors"], out["phase_errors"]
    assert os.path.isfile(os.path.join(d, "start.json")) and S.eats and all(e["landed"] for e in S.eats)
    assert out["checks"]["restore"]["ok"] is True and w.speed == 1
    assert len(out["checks"]["H"]["ring_paths"]) <= 32
    if key == "M2":
        assert len(S.drinks) == 7 and all(dr["fluid"] in ("Coffee", "Beer") for dr in S.drinks)
        assert out["checks"]["X"]["nights"][0]["reached"] is True
    S.grade_all()
    assert out["verdicts"]["H1"]["verdict"] == "as_predicted" and out["verdicts"]["RING"]["verdict"] == "as_predicted"
    # the HEAD replay ran over the fake's ring: the fake's HUNGER and THIRST are not the mod's, so they are falsified,
    # and the energy state the fake never rings is unmeasured, never a pass
    assert out["replay"]["rows"] > 100
    assert out["verdicts"][f"{key}_replay_HUNGER"]["verdict"] == "falsified"
    assert out["verdicts"][f"{key}_replay_body.energyState"]["verdict"] == "unmeasured"
    assert out["model_inputs"]["sleep_allowed"] is (key == "M2")
    assert os.path.isfile(os.path.join(d, "events.json")) and os.path.isfile(os.path.join(d, "replay.json"))
    ev = json.load(open(os.path.join(d, "events.json"), encoding="utf-8"))
    assert [e["kind"] for e in ev].count("eat") == len(S.eats)
    if key == "M2":
        assert any(e["kind"] == "sleep" for e in ev) and "M2_hangover" in out["verdicts"]
