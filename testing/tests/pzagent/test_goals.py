"""The goal layer (Plan 23 Task 13, P23-10, P23-B): `schema/goals.json`, the five goal dataclasses of
`planner/goals.py` and their steps over the fake mod, `validate`, the scripted source's order, and the runner's
record, supersede and budget; end to end through `Survive`'s `goal` branch."""
import dataclasses
import json
import os

import pytest

from agent.base.planner import goals as G
from agent.base.planner.goals import (ExploreToward, GoalRunner, LootBuilding, Rest, ScriptedSource, Shelter, Stock,
                                      validate)
from agent.base.planner.survive import Survive

from .test_night import house
from .test_policies import CRATE, FRIDGE, SHELF, Rig, all_sends_valid, square, swing, zombie

TYPES = (ExploreToward, LootBuilding, Shelter, Stock, Rest)
WATER = {"type": "counter", "n": 1, "items": ["Base.WaterBottle"]}
TOOLS = {"type": "crate", "n": 1, "items": ["Base.BaseballBat"]}


def schema():
    with open(G.SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def entry(name):
    return next(e for e in schema()["oneOf"] if e["properties"]["type"]["const"] == name)


def inside(x, y, bid=1, **k):
    return square(x, y, room="kitchen", building=bid, **k)


class Src:
    """A source that answers its goals in order, then Rest(120); `views` keeps every view it was given."""
    NAME = "test"

    def __init__(self, *goals):
        self.goals, self.views = list(goals), []

    def propose(self, view):
        self.views.append(view)
        return self.goals.pop(0) if self.goals else Rest(120.0)


def run(r, goal, ticks=1):
    """Tick a lone goal through a runner `ticks` times, sending what it answers; the last command or None."""
    runner = GoalRunner(Src(goal), r.clock)
    cmd = None
    for _ in range(ticks):
        cmd = runner.tick(r.world, r.acts)
        if cmd is not None:
            runner.send(cmd)
    return runner, cmd


# ================================================================ goals.json and the dataclasses (P23-B)
def test_the_schema_lists_the_five_goals_each_closed_with_a_description():
    s = schema()
    names = [e["properties"]["type"]["const"] for e in s["oneOf"]]
    assert names == [t.TYPE for t in TYPES] == ["ExploreToward", "LootBuilding", "Shelter", "Stock", "Rest"]
    assert s["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    for e in s["oneOf"]:
        assert e["additionalProperties"] is False and e["description"]
        assert set(e["required"]) == set(e["properties"])
        assert all(p["description"] for p in e["properties"].values())
    assert entry("Rest")["properties"]["seconds"]["maximum"] == 120
    assert entry("Stock")["properties"]["kind"]["enum"] == ["water", "food"]


@pytest.mark.parametrize("cls", TYPES)
def test_each_dataclass_has_its_schema_entrys_fields(cls):
    props = set(entry(cls.TYPE)["properties"]) - {"type"}
    names = {f.name for f in dataclasses.fields(cls)} - set(G.RUN_FIELDS)
    assert names == props
    assert set(G.RUN_FIELDS) <= {f.name for f in dataclasses.fields(cls)}
    g = validate(dict({"type": cls.TYPE}, **G.EXAMPLES[cls.TYPE]))
    assert (g.state, g.reason, g.started_wall) == ("running", None, None)
    assert g.args() == G.EXAMPLES[cls.TYPE] and g.row()["type"] == cls.TYPE


# ================================================================ validate
@pytest.mark.parametrize("obj, cls", [
    ({"type": "ExploreToward", "x": 120, "y": 205}, ExploreToward),
    ({"type": "LootBuilding", "building": 3}, LootBuilding),
    ({"type": "Shelter", "building": 3}, Shelter),
    ({"type": "Stock", "kind": "food"}, Stock),
    ({"type": "Rest", "seconds": 120}, Rest),
    ({"type": "Rest", "seconds": 12.5}, Rest),
])
def test_validate_accepts_each_goal_and_returns_its_dataclass(obj, cls):
    g = validate(obj)
    assert type(g) is cls and g.args() == {k: v for k, v in obj.items() if k != "type"}


@pytest.mark.parametrize("obj, why", [
    ({"type": "Teleport", "x": 1}, "unknown goal type"),
    ({"x": 1, "y": 2}, "unknown goal type"),
    ({"type": "ExploreToward", "x": 1}, "missing"),
    ({"type": "Stock", "kind": "water", "n": 2}, "unexpected"),
    ({"type": "Rest", "seconds": 120.5}, "maximum"),
    ({"type": "Rest", "seconds": -1}, "minimum"),
    ({"type": "Stock", "kind": "all"}, "not in"),
    ({"type": "LootBuilding", "building": "3"}, "not of type integer"),
    ({"type": "LootBuilding", "building": 3.0}, "not of type integer"),
    ({"type": "LootBuilding", "building": True}, "not of type integer"),
    ({"type": "Rest", "seconds": "30"}, "not of type number"),
    ("Rest", "not an object"),
])
def test_validate_refuses_with_a_one_line_reason(obj, why):
    with pytest.raises(ValueError) as e:
        validate(obj)
    assert why in str(e.value) and "\n" not in str(e.value)


# ================================================================ the scripted source's order
def view(**k):
    v = {"pos": {"x": 100.4, "y": 200.6, "z": 0}, "needs_wanted": [], "want_shelter": False, "buildings": [],
         "edge": None, "scanned_here": True, "stock_uses": ["water", "food", "bandage", "weapon"],
         "load": {"weight": 4.5, "max": 8.0, "level": 0}}
    v.update(k)
    return v


def bld(bid, dist, containers=2, looted=0, doors=1, shunned=False, shelter=None):
    return {"id": bid, "dist": dist, "containers": containers, "looted": looted, "doors": doors, "visited": False,
            "shunned": shunned, "shelter": doors > 0 if shelter is None else shelter}


@pytest.mark.parametrize("v, want", [
    (view(needs_wanted=["food", "water"], want_shelter=True, buildings=[bld(1, 3.0)], edge=[110, 200]),
     Stock("water")),                                                     # a need first, water before food
    (view(needs_wanted=["food"], buildings=[bld(1, 3.0)]), Stock("food")),
    (view(needs_wanted=["water"], stock_uses=["food"], want_shelter=True, buildings=[bld(2, 9.0), bld(1, 3.0)]),
     Shelter(1)),                                                         # no water container: the shelter, nearest
    (view(want_shelter=True, buildings=[bld(1, 3.0, shunned=True), bld(2, 9.0, doors=0), bld(3, 12.0)]), Shelter(3)),
    (view(buildings=[bld(1, 3.0, looted=2), bld(2, 9.0), bld(3, 5.0, containers=0)], edge=[110, 200]),
     LootBuilding(2)),                                                    # the nearest with an unlooted container
    (view(want_shelter=True, buildings=[bld(1, 3.0, doors=0)], edge=[110, 200]), LootBuilding(1)),
    (view(want_shelter=True, buildings=[bld(1, 3.0, shelter=False)], edge=[110, 200]), LootBuilding(1)),   # I3
    (view(buildings=[bld(1, 3.0), bld(2, 9.0)], cooled=[{"type": "LootBuilding", "args": {"building": 1}}]),
     LootBuilding(2)),                                                    # I4: a cooled goal is passed over
    (view(cooled=[{"type": "Rest", "args": {"seconds": 30.0}}]), Rest(30.0)),   # the last resort stays
    (view(buildings=[bld(1, 3.0, looted=2)], edge=[110, 200]), ExploreToward(110, 200)),
    (view(scanned_here=False), ExploreToward(100, 200)),                  # no edge: scan the place first
    (view(needs_wanted=["water"], load={"weight": 9.0, "max": 8.0, "level": 2}, buildings=[bld(1, 3.0)],
          edge=[110, 200]), ExploreToward(110, 200)),                     # above LOOT_MAX_LEVEL: no loot goal
    (view(), Rest(30.0)),
])
def test_the_scripted_source_proposes_in_its_order(v, want):
    g = ScriptedSource().propose(v)
    assert (g.TYPE, g.args()) == (want.TYPE, want.args())
    assert ScriptedSource.NAME == "scripted"


# ================================================================ each goal's steps
def test_explore_toward_scans_the_place_then_walks_and_ends_done_on_arrival(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    g = ExploreToward(110, 200)
    runner, cmd = run(r, g)
    assert cmd.TYPE == "scan" and g.state == "running"
    assert runner.tick(r.world, r.acts) is None                          # its scan is current: held
    r.answer()
    r.frame()
    cmd = runner.tick(r.world, r.acts)
    assert (cmd.TYPE, cmd.args()) == ("walkTo", {"x": 110, "y": 200, "gait": "walk"})
    runner.send(cmd)
    r.answer()
    r.frame(x=110.2, y=200.4)
    runner.tick(r.world, r.acts)
    assert g.state == "done" and g.reason == "arrived" and runner.history[0]["state"] == "done"
    all_sends_valid(r)


def test_explore_toward_a_walk_failed_stuck_fails_the_goal_and_marks_the_square(tmp_path):
    r = Rig(tmp_path)
    r.frame(game_min=480.0)
    g = ExploreToward(110, 200)
    runner = GoalRunner(Src(g), r.clock)
    runner.kit.bind(r.world, r.acts)
    runner.kit.explore.scanned.add(runner.kit.explore.place())           # the place is scanned already
    runner.send(runner.tick(r.world, r.acts))
    assert r.cmd()[0] == "walkTo"
    r.answer({"state": "failed", "reason": "stuck"})
    r.frame(game_min=481.0)
    runner.tick(r.world, r.acts)
    assert (g.state, g.reason) == ("failed", "stuck") and (110, 200) in r.world.stuck


def test_loot_building_loots_only_its_own_containers_one_use_at_a_time(tmp_path):
    r = Rig(tmp_path)
    r.scan([inside(101, 200, containers=[TOOLS]), inside(102, 200, containers=[CRATE]),
            inside(103, 200, containers=[FRIDGE, SHELF]), square(99, 200, containers=[WATER]),
            inside(106, 200, bid=2, containers=[WATER])])
    r.frame()
    g = LootBuilding(1)
    runner = GoalRunner(Src(g), r.clock)
    seen = []
    for _ in range(5):
        r.frame()
        cmd = runner.tick(r.world, r.acts)
        if cmd is None:
            break
        runner.send(cmd)
        seen.append((cmd.args()["filter"], cmd.args()["x"]))
        r.answer()
    assert seen == [("food", 103), ("bandage", 102), ("weapon", 101)]   # water is in no container of building 1
    assert (g.state, g.reason) == ("done", "looted")
    all_sends_valid(r)


def test_loot_building_at_load_level_two_fails_load(tmp_path):
    r = Rig(tmp_path)
    r.scan([inside(101, 200, containers=[CRATE])])
    r.frame(level=2)
    g = LootBuilding(1)
    _, cmd = run(r, g)
    assert cmd is None and (g.state, g.reason) == ("failed", "load")


def test_stock_loots_the_nearest_of_its_kind_until_one_more_is_held(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(101, 200, containers=[CRATE]), square(103, 200, containers=[WATER]),
            square(105, 200, containers=[dict(WATER, type="sink")])])
    r.frame()
    g = Stock("water")
    runner, cmd = run(r, g)
    assert cmd.args() == {"x": 103, "y": 200, "kind": "loot", "filter": "water", "maxWeight": 8.0}
    r.answer()                                                           # took nothing: the next container
    r.frame()
    runner.send(runner.tick(r.world, r.acts))
    assert r.cmd()[1]["x"] == 105
    r.answer()
    r.event("item_added", itemId=801, fullType="Base.WaterBottle", weight=1.0)
    r.frame()
    runner.tick(r.world, r.acts)
    assert (g.state, g.reason) == ("done", "stocked")


def test_stock_with_no_container_of_its_kind_fails(tmp_path):
    r = Rig(tmp_path)
    r.scan([square(101, 200, containers=[CRATE])])
    r.frame()
    g = Stock("food")
    _, cmd = run(r, g)
    assert cmd is None and (g.state, g.reason) == ("failed", "none found")


def test_shelter_runs_the_nights_shelter_steps_and_ends_done_inside(tmp_path):
    r = Rig(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=100.0, y=201.5)
    g = Shelter(1)
    runner = GoalRunner(Src(g), r.clock)
    steps = []
    for pos in ((100.0, 201.5), (109.5, 201.5), (109.5, 201.5), (110.5, 200.5), (110.5, 200.5)):
        r.frame(x=pos[0], y=pos[1])
        cmd = runner.tick(r.world, r.acts)
        if cmd is None:
            break
        runner.send(cmd)
        steps.append(cmd.TYPE if cmd.TYPE != "interact" else cmd.kind)
        r.answer()
    assert steps == ["walkTo", "open", "walkTo", "close"]
    assert (g.state, g.reason) == ("done", "inside")
    assert g.why["step"] in ("close", "done")
    all_sends_valid(r)


def test_shelter_with_no_exterior_door_fails_and_a_shun_is_kept(tmp_path):
    r = Rig(tmp_path)
    r.scan([s for s in house(1, 110) if s["door"] is None])
    r.frame()
    g = Shelter(1)
    _, cmd = run(r, g)
    assert cmd is None and (g.state, g.reason) == ("failed", "no plan")
    r2 = Rig(tmp_path / "b")
    r2.scan(house(2, 110, door={"open": False, "locked": True, "barricaded": False}))
    r2.frame(x=109.5, y=201.5, game_min=500.0)
    g2 = Shelter(2)
    runner, cmd = run(r2, g2)
    assert cmd.TYPE == "interact" and cmd.kind == "open"
    r2.answer({"state": "failed", "reason": "locked"})
    r2.frame(x=109.5, y=201.5, game_min=501.0)
    runner.tick(r2.world, r2.acts)
    assert (g2.state, g2.reason) == ("failed", "shun") and runner.kit.shunned == {2: 501.0}


def test_rest_sends_nothing_for_its_seconds_then_ends_done(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    g = Rest(30.0)
    runner, cmd = run(r, g)
    assert cmd is None and g.state == "running" and runner.current is g
    r.advance(29.9)
    assert runner.tick(r.world, r.acts) is None and g.state == "running"
    r.advance(0.1)
    runner.tick(r.world, r.acts)
    assert (g.state, g.reason) == ("done", "rested") and r.acts.history == []


# ================================================================ the runner
def test_the_runners_record_rows_carry_the_contract_keys(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    runner = GoalRunner(Src(Rest(5.0), Rest(10.0)), r.clock)
    runner.tick(r.world, r.acts)
    r.advance(5.0)
    runner.tick(r.world, r.acts)                                         # the first ends, the second proposed
    assert len(runner.history) == 1 and runner.current.args() == {"seconds": 10.0}
    row = runner.history[0]
    assert row == {"type": "Rest", "args": {"seconds": 5.0}, "state": "done", "reason": "rested", "startS": 0.0,
                   "endS": 5.0, "source": "test"}
    assert ScriptedSource.NAME == "scripted" and GoalRunner(ScriptedSource(), r.clock).source.NAME == "scripted"


def test_rows_are_the_history_then_the_running_goal(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    runner = GoalRunner(Src(Rest(5.0), Rest(10.0)), r.clock)
    assert runner.rows() == []
    runner.tick(r.world, r.acts)
    r.advance(5.0)
    runner.tick(r.world, r.acts)
    r.advance(2.0)
    rows = runner.rows()
    assert rows[0] == runner.history[0] and rows[0] is not runner.history[0]
    assert rows[1] == {"type": "Rest", "args": {"seconds": 10.0}, "state": "running", "reason": None, "startS": 5.0,
                       "endS": None, "source": "test"}
    assert len(rows) == 2 and len(runner.history) == 1


def test_a_goal_past_goal_max_s_is_failed_and_replaced(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    g = ExploreToward(130, 200)                                          # its walk never ends: no frame pumps it
    src = Src(g, Rest(1.0))
    runner = GoalRunner(src, r.clock)
    runner.kit.bind(r.world, r.acts)
    runner.kit.explore.scanned.add(runner.kit.explore.place())
    runner.send(runner.tick(r.world, r.acts))
    assert r.cmd()[0] == "walkTo"
    r.advance(G.GOAL_MAX_S)
    runner.tick(r.world, r.acts)
    assert runner.history == []                                          # at GOAL_MAX_S exactly: still running
    r.advance(0.5)
    runner.tick(r.world, r.acts)
    assert runner.history[0]["state"] == "failed" and runner.history[0]["reason"] == "goal budget"
    assert runner.history[0]["endS"] == G.GOAL_MAX_S + 0.5 and runner.current.args() == {"seconds": 1.0}
    assert G.GOAL_MAX_S == 90.0
    assert runner.cooled == {}                                           # it had sent: no cool-down


def test_a_rest_is_budgeted_at_its_seconds_and_ends_rested_p23_w(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    runner = GoalRunner(Src(Rest(120.0)), r.clock)
    runner.tick(r.world, r.acts)
    assert runner.current.budget() == 120.0 and Rest(30.0).budget() == G.GOAL_MAX_S
    r.advance(100.0)
    runner.tick(r.world, r.acts)
    assert runner.history == []                                          # past GOAL_MAX_S: a rest runs on
    r.advance(20.0)
    runner.tick(r.world, r.acts)
    assert runner.history[0]["state"] == "done" and runner.history[0]["reason"] == "rested"


def test_the_runner_proposes_at_most_once_a_tick_and_cools_a_first_step_failure(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    src = Src(Stock("food"), Stock("food"), Rest(1.0), Stock("food"))   # Stock(food) fails at its first step
    runner = GoalRunner(src, r.clock)
    for _ in range(3):
        assert runner.tick(r.world, r.acts) is None
    assert len(src.views) == 3 and [h["reason"] for h in runner.history] == ["none found"]
    assert runner.cooled == {("Stock", '{"kind": "food"}'): 1000.0 + G.GOAL_COOL_S} and G.GOAL_COOL_S == 30.0
    assert runner.cooling() == [{"type": "Stock", "args": {"kind": "food"}}]
    assert runner.current.TYPE == "Rest"                                 # the refused tick wrote no row
    r.advance(G.GOAL_COOL_S)
    runner.tick(r.world, r.acts)                                         # the Rest ends; the cool-down passed: taken again
    assert [h["reason"] for h in runner.history] == ["none found", "rested", "none found"]


def test_a_refused_goal_is_named_in_why(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    runner = GoalRunner(Src(Stock("food"), Stock("food")), r.clock)
    runner.tick(r.world, r.acts)
    runner.tick(r.world, r.acts)
    assert runner.why["refused"] == {"type": "Stock", "args": {"kind": "food"}} and runner.current is None


@pytest.mark.parametrize("instinct", ["fight", "need"])
def test_a_rest_pre_empted_by_an_instinct_is_superseded_not_rested(tmp_path, instinct):
    """The spec gap: a goal that has sent nothing is superseded off its mark; closed in observe (I1), so the log reads
    it superseded on the tick after the instinct's send, its endS there."""
    r = Rig(tmp_path)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(Rest(30.0)))
    r.frame()
    sv.tick(r.world, r.acts)
    assert sv.goals.current.TYPE == "Rest" and sv.goals.current.mark is None
    r.advance(1.0)
    if instinct == "fight":
        frame = lambda: r.frame(zombies=[zombie(1, 103.0, 200.0)])
    else:
        r.event("item_added", itemId=701, fullType="Base.WaterBottle", weight=1.0)
        frame = lambda: r.frame(thirst=0.6)
    frame()
    sv.tick(r.world, r.acts)                                             # the instinct sends
    sent = r.acts.history[-1].type
    r.advance(1.0)
    frame()
    sv.tick(r.world, r.acts)                                             # the instinct holds: observe closes the rest
    lines = [json.loads(ln) for ln in (tmp_path / "decision.log").read_text(encoding="utf-8").splitlines()]
    assert lines[1]["goal"]["state"] == "running" and lines[2]["goal"]["state"] == "superseded"
    assert lines[2]["branch"] != "goal"
    row = sv.goals.history[0]
    assert (row["state"], row["reason"], row["endS"]) == ("superseded", sent, 2.0)
    r.advance(40.0)
    frame()
    sv.tick(r.world, r.acts)
    assert [h["state"] for h in sv.goals.history] == ["superseded"]      # never closed rested past its seconds


def test_a_goal_taken_after_an_instinct_reads_its_mark_and_is_not_superseded_by_it(tmp_path):
    r = Rig(tmp_path)
    r.event("item_added", itemId=701, fullType="Base.WaterBottle", weight=1.0)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(Rest(30.0)))
    r.frame(thirst=0.6)
    sv.tick(r.world, r.acts)
    r.answer()
    r.event("item_removed", itemId=701, fullType="Base.WaterBottle")
    r.frame()
    sv.tick(r.world, r.acts)
    g = sv.goals.current
    assert g.TYPE == "Rest" and g.mark is r.acts.history[-1]
    r.advance(1.0)
    r.frame()
    sv.tick(r.world, r.acts)
    assert sv.goals.current is g and g.state == "running"


def test_a_shelter_with_no_plan_is_shunned_in_the_shared_store(tmp_path):
    r = Rig(tmp_path)
    r.scan([s for s in house(1, 110) if s["door"] is None])
    r.frame(game_min=500.0)
    store = {}
    runner = GoalRunner(Src(Shelter(1)), r.clock, shunned=store)
    runner.tick(r.world, r.acts)
    assert runner.history[0]["reason"] == "no plan" and store == {1: 500.0} and runner.kit.shunned is store


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_validate_refuses_a_non_finite_number(bad):
    with pytest.raises(ValueError) as e:
        validate({"type": "Rest", "seconds": bad})
    assert "not finite" in str(e.value)


def test_a_view_is_built_only_when_a_goal_is_proposed(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    built = []
    runner = GoalRunner(Src(Rest(60.0)), r.clock)
    for _ in range(3):
        runner.tick(r.world, r.acts, lambda: built.append(1) or {"n": len(built)})
    assert built == [1]


def test_a_goal_pre_empted_by_a_threat_reads_superseded_and_is_proposed_again(tmp_path):
    r = Rig(tmp_path)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    r.scan([inside(101, 200, containers=[CRATE])])
    r.frame()
    sv.tick(r.world, r.acts)
    assert r.cmd() == ("interact", {"x": 101, "y": 200, "kind": "loot", "filter": "bandage", "maxWeight": 8.0})
    first = sv.goals.current
    assert first.TYPE == "LootBuilding" and first.args() == {"building": 1}
    r.frame(zombies=[zombie(1, 101.5, 200.0)])
    sv.tick(r.world, r.acts)
    assert r.cmd() == ("attack", {"targetId": 1})
    r.answer({"state": "done", "result": swing(True)})
    r.event("zombie_dead", id=1)
    r.frame()
    sv.tick(r.world, r.acts)
    assert first.state == "superseded" and sv.goals.history[0]["state"] == "superseded"
    assert sv.goals.history[0]["reason"] == "attack"
    again = sv.goals.current
    assert again is not first and (again.TYPE, again.args()) == ("LootBuilding", {"building": 1})
    assert r.cmd()[0] == "interact"


def test_survive_takes_the_source_given_and_defaults_to_the_scripted_one(tmp_path):
    r = Rig(tmp_path)
    assert isinstance(Survive(r.world, r.acts, str(tmp_path / "a.log"), r.clock).goals.source, ScriptedSource)
    src = Src(Rest(60.0))
    sv = Survive(r.world, r.acts, str(tmp_path / "b.log"), r.clock, source=src)
    r.frame()
    sv.tick(r.world, r.acts)
    assert sv.goals.source is src and len(src.views) == 1 and "needs_wanted" in src.views[0]
    d = json.loads((tmp_path / "b.log").read_text(encoding="utf-8").splitlines()[-1])
    assert d["branch"] == "goal" and d["goal"] == {"type": "Rest", "args": {"seconds": 60.0}, "state": "running",
                                                   "source": "test"}


def test_the_schema_path_is_the_tracked_file():
    assert os.path.normpath(G.SCHEMA_PATH).endswith(os.path.join("agent", "base", "schema", "goals.json"))
