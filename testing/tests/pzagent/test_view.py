"""The goal layer's view (Plan 23 Task 13, P23-10): `planner/view.py`'s `view(world, survive)`, the dict a goal source
reads (game state only), and `render(view)`, its text, one line per key and under 2048 bytes."""
import json

from agent.base.planner import view as V
from agent.base.planner.goals import Rest
from agent.base.planner.survive import Survive
from agent.base.planner.view import render, view

from .test_night import house
from .test_policies import BAT, CRATE, FRIDGE, Rig, square, zombie


def make(tmp_path):
    r = Rig(tmp_path)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    return r, sv


def test_the_view_carries_the_briefs_keys_and_the_sources_reads(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=701, fullType="Base.WaterBottle", weight=1.0)
    r.event("item_added", itemId=702, fullType="Base.Apple", weight=0.2)
    r.event("item_added", itemId=703, fullType="Base.Apple", weight=0.2)
    r.frame(x=100.25, y=200.5, hunger=0.1, thirst=0.05, fatigue=0.2, hour=9.5, health=88.0, level=1, weight=6.0)
    v = view(r.world, sv)
    assert set(v) == set(V.KEYS)
    assert {"pos", "hour", "health", "needs", "needs_wanted", "load", "weapon", "inventory_by_use", "buildings",
            "zombies_near", "last_goal", "events", "want_shelter"} <= set(V.KEYS)
    assert v["pos"] == {"x": 100.25, "y": 200.5, "z": 0} and v["hour"] == 9.5 and v["health"] == 88.0
    assert v["needs"] == {"hunger": 0.1, "thirst": 0.05, "fatigue": 0.2}
    assert v["load"] == {"weight": 6.0, "max": 8.0, "level": 1} and v["weapon"] == BAT["type"]
    assert v["inventory_by_use"] == {"food": 2, "water": 1, "weapon": 0, "bandage": 0, "other": 0}
    assert v["needs_wanted"] == [] and v["want_shelter"] is False and v["last_goal"] is None
    assert v["events"] == ["item_added", "item_added", "item_added"]
    json.dumps(v, allow_nan=False)


def test_needs_wanted_lists_the_uses_marked_within_need_memory_s_water_first(tmp_path):
    r, sv = make(tmp_path)
    r.frame(thirst=0.3, hunger=0.3)
    sv.tick(r.world, r.acts)
    assert view(r.world, sv)["needs_wanted"] == ["water", "food"]
    r.advance(V.NEED_MEMORY_S)
    r.frame()
    assert view(r.world, sv)["needs_wanted"] == ["water", "food"]       # at NEED_MEMORY_S: still wanted
    r.advance(0.5)
    assert view(r.world, sv)["needs_wanted"] == [] and V.NEED_MEMORY_S == 120.0


def test_the_buildings_carry_containers_looted_doors_visited_and_distance(tmp_path):
    r, sv = make(tmp_path)
    sqs = house(1, 110) + house(2, 120)
    for s in sqs:
        if (s["x"], s["y"]) == (111, 201):
            s["containers"] = [CRATE, FRIDGE]
        if (s["x"], s["y"]) == (121, 201):
            s["containers"] = [FRIDGE]
    r.scan(sqs)
    r.frame(x=100.0, y=201.5)
    r.world.mark_looted((121, 201, 0, 0), "food")
    b = view(r.world, sv)["buildings"]
    assert [x["id"] for x in b] == [1, 2]                                # nearest first
    assert b[0] == {"id": 1, "dist": 10.5, "containers": 2, "looted": 0, "doors": 1, "visited": False,
                    "shunned": False, "shelter": True}
    assert b[1]["containers"] == 1 and b[1]["looted"] == 1 and b[1]["dist"] == 20.5
    sv.night.visited.add(2)
    sv.night.shunned[1] = 480.0
    b = view(r.world, sv)["buildings"]
    assert b[0]["shunned"] is True and b[1]["visited"] is True


def test_a_building_with_no_room_on_the_players_floor_is_no_shelter(tmp_path):
    r, sv = make(tmp_path)
    r.scan([dict(s, z=1) if s["room"] is not None else s for s in house(1, 110)])   # its rooms one floor up
    r.frame(x=100.0, y=201.5)
    b = view(r.world, sv)["buildings"]
    assert b[0]["id"] == 1 and b[0]["shelter"] is False


def test_the_view_only_reads_the_kit(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    other = Rig(tmp_path / "other")
    sv.goals.kit.bind(other.world, other.acts)
    view(r.world, sv)
    assert sv.goals.kit.loot.world is other.world and sv.goals.kit.explore.world is other.world


def test_render_stays_under_the_bound_on_oversized_strings(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    v = view(r.world, sv)
    v["events"] = ["x" * 900, "y" * 900, "z" * 900]
    v["last_goal"] = {"type": "Rest", "args": {"seconds": 1.0}, "state": "failed", "reason": "r" * 900}
    text = render(v)
    assert len(text.encode("utf-8")) < V.RENDER_MAX
    assert [ln.split(":", 1)[0] for ln in text.splitlines()] == list(V.KEYS)


def test_zombies_near_counts_within_six_twelve_and_twenty_five_tiles(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0), zombie(2, 108.0, 200.0), zombie(3, 120.0, 200.0),
                     zombie(4, 130.0, 200.0)])
    assert view(r.world, sv)["zombies_near"] == {"6": 1, "12": 2, "25": 3}


def test_last_goal_and_want_shelter_come_off_the_runner_and_the_night(tmp_path):
    r, sv = make(tmp_path)
    r.frame(fatigue=0.65)
    sv.goals.source.propose = lambda v: Rest(1.0)
    sv.tick(r.world, r.acts)
    r.advance(1.0)
    r.frame(fatigue=0.65)
    sv.tick(r.world, r.acts)
    v = view(r.world, sv)
    assert v["last_goal"] == {"type": "Rest", "args": {"seconds": 1.0}, "state": "done", "reason": "rested"}
    assert v["want_shelter"] is True


def test_the_view_names_the_edge_the_scanned_place_and_the_uses_a_loot_could_reach(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    v = view(r.world, sv)
    assert v["edge"] is None and v["scanned_here"] is False and v["stock_uses"] == []
    r.scan([square(x, y) for x in range(99, 102) for y in range(199, 202)]
           + [square(102, 200, containers=[FRIDGE])])
    sv.goals.kit.explore.scanned.add(sv.goals.kit.explore.place())
    v = view(r.world, sv)
    assert v["edge"] == [99, 200] and v["scanned_here"] is True and v["stock_uses"] == ["food"]


def big_world(tmp_path):
    """20 buildings of 3 x 3 rooms with a door each, 50 containers spread over them, and a busy frame."""
    r, sv = make(tmp_path)
    houses = [house(1000 + b, 110 + (b % 5) * 10, 200 + (b // 5) * 10) for b in range(20)]
    rooms = [[s for s in h if s["room"] is not None] for h in houses]
    for i in range(50):                                                  # round robin: 2 or 3 a building
        rooms[i % 20][i // 20]["containers"] = [dict(CRATE, items=["Base.Bandage", "Base.Apple", "Base.WaterBottle"])]
    r.scan([s for h in houses for s in h])
    for i in range(10):
        r.event("item_added", itemId=700 + i, fullType="Base.Apple", weight=0.2)
    r.frame(zombies=[zombie(i, 100.0 + i, 200.0) for i in range(1, 31)])
    return r, sv


def test_render_is_one_line_per_key_and_under_2048_bytes_on_a_big_world(tmp_path):
    r, sv = big_world(tmp_path)
    assert len(r.world.interiors()) == 20 and len(r.world.containers) == 50
    v = view(r.world, sv)
    assert len(v["buildings"]) == 20
    text = render(v)
    assert len(text.encode("utf-8")) < 2048 and len(text.encode("utf-8")) <= V.RENDER_MAX
    lines = text.splitlines()
    assert [ln.split(":", 1)[0] for ln in lines] == list(V.KEYS)
    bl = next(ln for ln in lines if ln.startswith("buildings:"))
    assert bl.count(";") == V.BUILDINGS_SHOWN - 1                        # the 10 nearest only
