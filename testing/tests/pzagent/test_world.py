"""World: the model built from the Lua's lines; replay is deterministic."""
import json
import os
from agent.world import World, replay

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
LOG = os.path.join(FIX, "log-synthetic-1.log")


def frame(wall, zombies, x=0.0, y=0.0):
    return {"kind": "frame", "seq": 1, "tick": 1, "wallMs": wall, "gameMin": 1, "worldAge": 1.0,
            "x": x, "y": y, "z": 0, "zombies": zombies}


def scan(squares):
    return {"kind": "scan", "seq": 2, "tick": 2, "wallMs": 0, "r": 1, "squares": squares, "missing": []}


def sq(x, y, **k):
    return dict({"x": x, "y": y, "z": 0, "solid": False, "containers": [], "floor": []}, **k)


def test_apply_frame_zombies_age_out():
    w = World()
    z = {"id": 7, "x": 1.0, "y": 2.0, "dist": 2.0, "hasTarget": False, "crawler": False}
    w.apply(frame(1000, [z]))
    assert w.zombies[7]["seenWallMs"] == 1000
    w.apply(frame(10999, {}))          # an empty list arrives as {}
    assert 7 in w.zombies
    w.apply(frame(11001, {}))
    assert 7 not in w.zombies


def test_scan_fills_map_and_containers():
    w = World()
    w.apply(scan([sq(1, 1, building=5, containers=[{"type": "fridge", "n": 1, "items": ["Base.Milk"]}]), sq(2, 1)]))
    assert (1, 1, 0) in w.map and (2, 1, 0) in w.map
    assert w.containers[(1, 1, 0, 0)] == {"type": "fridge", "n": 1, "items": ["Base.Milk"], "looted": False}
    assert w.buildings == {5}
    w.mark_looted((1, 1, 0, 0))
    w.apply(scan([sq(1, 1, containers=[{"type": "fridge", "n": 1, "items": ["Base.Milk"]}])]))
    assert w.containers[(1, 1, 0, 0)]["looted"] is True


def test_nearest_unlooted_filters_food():
    w = World()
    w.apply(frame(0, {}, x=0.0, y=0.0))
    w.apply(scan([sq(1, 0, containers=[{"type": "crate", "n": 1, "items": ["Base.Nails"]}]),
                  sq(5, 0, containers=[{"type": "fridge", "n": 1, "items": ["Base.Milk"]}]),
                  sq(9, 0, containers=[{"type": "shelf", "n": 1, "items": ["Base.Apple"]}])]))
    assert w.nearest_unlooted() == (1, 0, 0, 0)
    assert w.nearest_unlooted("food") == (5, 0, 0, 0)
    w.mark_looted((5, 0, 0, 0))
    assert w.nearest_unlooted("food") == (9, 0, 0, 0)
    w.mark_looted((9, 0, 0, 0))
    assert w.nearest_unlooted("food") is None


def test_unexplored_edge():
    w = World()
    assert w.unexplored_edge() is None
    w.apply(frame(0, {}, x=1.0, y=1.0))
    w.apply(scan([sq(x, y, solid=(x, y) == (0, 0)) for x in range(3) for y in range(3)]))
    # (1,1) is interior; the nearest edge squares are at distance 1; ties break by (x, y)
    assert w.unexplored_edge() == (0, 1)


def test_replay_golden():
    with open(os.path.join(FIX, "log-synthetic-1.world.json"), encoding="utf-8") as f:
        golden = json.load(f)
    assert replay(LOG).to_json() == golden


def test_replay_is_byte_stable():
    a = json.dumps(replay(LOG).to_json(), sort_keys=True)
    b = json.dumps(replay(LOG).to_json(), sort_keys=True)
    assert a == b


def test_nearest_unlooted_skips_empty_containers():
    w = World()
    w.apply(frame(0, {}))
    w.apply(scan([sq(1, 0, containers=[{"type": "crate", "n": 0, "items": []}]),
                  sq(4, 0, containers=[{"type": "crate", "n": 1, "items": ["Base.Nails"]}])]))
    assert w.nearest_unlooted() == (4, 0, 0, 0)


def test_food_heuristic_has_word_boundary():
    from agent.world import FOOD_RX
    assert FOOD_RX.search("Base.Ham") and not FOOD_RX.search("Base.Hammer")


def test_unknown_kind_is_counted_not_applied():
    w = World()
    w.apply({"kind": "bogus", "seq": 1})
    w.apply({"kind": "ack", "cmdSeq": 1, "ok": True})
    assert w.unknown_kinds == 1 and w.last_ack["cmdSeq"] == 1


def test_goal_event_settles_the_running_goal_by_goal_seq():
    w = World()
    f = frame(0, {}); f["goal"] = {"seq": 4, "name": "goto", "state": "running", "detail": ""}
    w.apply(f)
    w.apply({"kind": "event", "seq": 9, "tick": 3, "wallMs": 1, "event": "goal_failed", "goalSeq": 3, "reason": "superseded"})
    assert w.goal["state"] == "running"                       # an older goal's event leaves the running one alone
    w.apply({"kind": "event", "seq": 10, "tick": 4, "wallMs": 2, "event": "goal_failed", "goalSeq": 4, "reason": "stuck"})
    assert w.goal == {"seq": 4, "name": "goto", "state": "failed", "detail": "stuck"}
    assert w.events[-1]["goalSeq"] == 4
    w.apply(f)
    w.apply({"kind": "event", "seq": 11, "tick": 5, "wallMs": 3, "event": "goal_done", "goalSeq": 4})
    assert w.goal["state"] == "done"
