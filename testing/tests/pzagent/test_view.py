"""The goal layer's view (Plan 23 Task 13, P23-10): `planner/view.py`'s `view(world, survive)`, the dict a goal source
reads (game state only), and `render(view)`, its text, one line per key and under 2048 bytes."""
import json

import pytest

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
    assert v["inventory_by_use"] == {"food": 2, "water": 1, "weapon": 0, "bandage": 0, "other": 0, "container": 0}
    assert v["needs_wanted"] == [] and v["want_shelter"] is False and v["last_goal"] is None
    assert v["events"] == ["item_added", "item_added", "item_added"]
    json.dumps(v, allow_nan=False)


def test_needs_wanted_lists_the_uses_marked_within_need_memory_s_water_first(tmp_path):
    r, sv = make(tmp_path)
    r.frame(thirst=0.3, hunger=0.3)
    sv.tick(r.world, r.acts)
    # named change, Plan 24 Task 10 (ruling P24-G 3): no water and no vessel held marks the container want too
    assert view(r.world, sv)["needs_wanted"] == ["water", "food", "container"] and V.NEED_USES[2] == "container"
    r.advance(V.NEED_MEMORY_S)
    r.frame()
    assert view(r.world, sv)["needs_wanted"] == ["water", "food", "container"]   # at NEED_MEMORY_S: still wanted
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
    assert b[0] == {"id": 1, "x": 110, "y": 201, "door": [110, 201], "dist": 10.5, "containers": 2, "looted": False,
                    "doors": 1, "visited": False, "shunned": False, "shelter": True,   # P24-B 3: x, y, door
                    "holds": {"bandage": 1, "food": 1}, "box": [110, 200, 112, 202]}   # P24-Y (Task 18)
    assert b[1]["containers"] == 1 and b[1]["looted"] is True and b[1]["dist"] == 20.5
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
    v["last_goal"] = {"type": "Rest", "args": {"seconds": 1.0}, "end": "failed", "why": "r" * 900}
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
    assert v["last_goal"] == {"type": "Rest", "args": {"seconds": 1.0}, "end": "done", "why": "done"}   # P24-B 3
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
    assert bl.count(";") == V.BUILDINGS_SHOWN - 1 and V.BUILDINGS_SHOWN == 6   # the 6 nearest only (P24-B 3)


# ================================================================ P24-B: the met ground, positions, failure meanings
def test_the_view_carries_the_met_ground_north(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 100.0, 190.0), zombie(2, 101.0, 190.0), zombie(3, 100.0, 191.0)])
    r.frame()                                                            # listed no more: the memory keeps them
    m = view(r.world, sv)["met"]
    assert m == {"dense": [100.3, 190.3], "n": 3, "bearing": "N", "dist": 9.7}


def test_the_met_ground_beyond_25_tiles_or_none_met_reads_null(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    assert view(r.world, sv)["met"] == {"dense": None, "n": 0, "bearing": None, "dist": None}
    r.frame(zombies=[zombie(1, 130.0, 200.0), zombie(2, 130.5, 200.0)])
    assert V.MET_VIEW_R == 25.0 and view(r.world, sv)["met"]["dense"] is None


def test_attackers_and_hit_reaction_come_off_the_frame(tmp_path):
    r, sv = make(tmp_path)
    r.frame(attackers=2, hit_reaction="HitReaction")
    v = view(r.world, sv)
    assert v["attackers"] == 2 and v["hit_reaction"] == "HitReaction"
    r.frame()
    v = view(r.world, sv)
    assert v["attackers"] == 0 and v["hit_reaction"] is None
    r.world.me = {k: x for k, x in r.world.me.items() if k not in ("attackers", "hitReaction")}   # a PZA/1.3 frame
    v = view(r.world, sv)
    assert v["attackers"] is None and v["hit_reaction"] is None


@pytest.mark.parametrize("row, why", [
    ({"state": "done", "reason": "arrived"}, "done"),
    ({"state": "done", "reason": "rested"}, "done"),
    ({"state": "failed", "reason": "stuck"}, "stuck"),
    ({"state": "failed", "reason": "no path"}, "stuck"),
    ({"state": "superseded", "reason": "attack"}, "superseded by the threat"),
    ({"state": "superseded", "reason": "walkTo"}, "superseded by the threat"),
    ({"state": "superseded", "reason": "steer"}, "superseded by the threat"),
    ({"state": "superseded", "reason": "hold"}, "superseded by the threat"),
    ({"state": "superseded", "reason": "consume"}, "superseded by an instinct"),
    ({"state": "failed", "reason": "nothing to loot"}, "looted already"),
    ({"state": "failed", "reason": "goal budget"}, "failed"),
    ({"state": "failed", "reason": "load"}, "failed"),
])
def test_last_goal_reads_the_end_and_its_meaning(row, why):
    assert V.why_of(row) == why and why in V.WHYS


def test_the_closed_set_of_meanings():
    """Named change, ruling P24-Y (Task 18): `in the woods`, the LLM source's refusal of an ExploreToward with no
    listed building within WOODS_R."""
    assert V.WHYS == ("done", "stuck", "superseded by the threat", "superseded by an instinct", "looted already",
                      "refused", "out of range", "in the woods", "failed")


def full_world(tmp_path):
    """big_world, a goal ended, the met ground north and a PZA/1.4 frame under attack: every key carries a value."""
    r, sv = big_world(tmp_path)
    sv.goals.history.append({"type": "ExploreToward", "args": {"x": 140, "y": 260}, "state": "superseded",
                             "reason": "attack", "startS": 0.0, "endS": 4.0, "source": "llm"})
    sv.goals.cooled[("LootBuilding", '{"building": 1003}')] = r.clock() + 30.0
    sv.need_marks = {"water": r.clock(), "food": r.clock()}
    r.frame(zombies=[zombie(i, 100.0 + i, 200.0) for i in range(1, 31)], attackers=2, hit_reaction="HitReaction")
    return r, sv


def test_render_carries_every_key_under_2048_bytes_on_the_full_fixture(tmp_path):
    r, sv = full_world(tmp_path)
    v = view(r.world, sv)
    for k in V.KEYS:
        assert v[k] is not None and v[k] != [] or k in ("weapon", "edge", "events", "stock_uses", "toward"), k
    assert v["met"]["n"] >= 3 and v["attackers"] == 2 and v["last_goal"]["why"] == "superseded by the threat"
    text = render(v)
    n = len(text.encode("utf-8"))
    print("render bytes on the full fixture:", n)
    assert n < V.RENDER_MAX
    lines = text.splitlines()
    assert [ln.split(":", 1)[0] for ln in lines] == list(V.KEYS)
    assert not any(ln.endswith("...") for ln in lines)                   # nothing cut on the full fixture
    bl = next(ln for ln in lines if ln.startswith("buildings:"))
    assert bl.count(";") == V.BUILDINGS_SHOWN - 1


def test_a_building_renders_its_square_door_distance_and_flags():
    """Named change, ruling P24-Y (Task 18): each building's line ends `h:` with what it is known to hold."""
    b = {"id": 3, "x": 110, "y": 201, "door": [110, 201], "dist": 10.5, "containers": 2, "looted": False,
         "doors": 1, "visited": True, "shunned": False, "holds": {"water": 1, "food": 3}}
    assert V._building(b) == "3 @110,201 door 110,201 10.5 c2 v h:food3,water1"
    b.update(door=None, looted=True, visited=False, shunned=True, holds={})
    assert V._building(b) == "3 @110,201 door - 10.5 c2 Ls h:-"


# ======================================== Task 3 fix 1: the render drop order (I2), an unsearched building (M1)
def overflow(v, extra):
    """`v` with three 400-byte events and `cooled` padded so its render without the events is RENDER_MAX - 1 + `extra`
    bytes (negative: under the cap; the events alone then push it over)."""
    v = dict(v, events=["e" * 400, "f" * 400, "g" * 400])

    def padded(n):
        w = dict(v, cooled=[{"type": "Rest", "args": {"pad": "p" * n}}] + list(v["cooled"]))
        return w, len(chr(10).join(V._lines(w, V.BUILDINGS_SHOWN, events=False)).encode("utf-8"))
    s0 = padded(0)[1]
    w, size = padded(V.RENDER_MAX - 1 + extra - s0)
    assert size == V.RENDER_MAX - 1 + extra
    return w


def test_the_events_go_first_when_they_alone_overflow(tmp_path):
    r, sv = full_world(tmp_path)
    v = overflow(view(r.world, sv), -50)
    text = render(v)
    lines = text.splitlines()
    assert "events: []" in lines
    bl = next(ln for ln in lines if ln.startswith("buildings:"))
    assert bl.count(";") == V.BUILDINGS_SHOWN - 1                        # all six kept
    assert not any(ln.endswith("...") for ln in lines)


def test_the_farthest_buildings_go_next_then_the_longest_line_is_halved(tmp_path):
    r, sv = full_world(tmp_path)
    v = overflow(view(r.world, sv), 60)                                  # the events out, still 60 over
    lines = render(v).splitlines()
    bl = next(ln for ln in lines if ln.startswith("buildings:"))
    shown = bl.count(";") + 1
    assert "events: []" in lines and 0 < shown < V.BUILDINGS_SHOWN
    assert bl.startswith("buildings: %s " % v["buildings"][0]["id"])    # the nearest kept, the farthest cut
    assert not any(ln.endswith("...") for ln in lines)
    v = overflow(view(r.world, sv), 600)                                 # beyond every building: a line halved
    lines = render(v).splitlines()
    assert "events: []" in lines and "buildings: " in lines
    assert next(ln for ln in lines if ln.startswith("cooled:")).endswith("...")
    assert [ln.split(":", 1)[0] for ln in lines] == list(V.KEYS)


def test_a_building_with_no_container_known_is_not_looted(tmp_path):
    """M1: unknown reads lootable: `looted` is true only with a container known and every one looted."""
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=100.0, y=201.5)
    b = view(r.world, sv)["buildings"][0]
    assert b["containers"] == 0 and b["looted"] is False and "L" not in V._building(b).split()[-1]
