"""World from PZA/1 lines (Plan 22 Task 9a): the frame's groups, zombies aged by wallMs, the map by square with its
containers and looted marks, the inventory by item id, damage from the client's events and the server's damage.watch
replies, the act lines, a byte-stable to_json and a replay of a state.log through FileTransport (delta frames merged
as live). The heuristics are Plan 21's (`testing/agent/world.py`, frozen), the regexes replaced by the dataset's use
(`agent.base.items`, Plan 23 Task 9); the square's edges, the line check, interiors and the empties are Task 9's.

The committed fixtures `fixtures/pza1-synthetic-1.log` and `.world.json` are written by `_write_synthetic` below, run
once by hand from the repository root:

    cd testing && python -c "from tests.pzagent.test_base_world import _regenerate; _regenerate()"

and pinned by two tests: the replay equals the committed JSON byte for byte, and the fake mod regenerates the log
byte for byte.
"""
import json
import os

import pytest

from agent.base import items
from agent.base.replay import replay as replay_summary
from agent.base.world import ZOMBIE_TTL_S, World

from . import fakemod
from .fakemod import DEFAULT_FRAME, FakeMod

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
LOG = os.path.join(FIX, "pza1-synthetic-1.log")
GOLDEN = os.path.join(FIX, "pza1-synthetic-1.world.json")

DOOR = {"open": False, "locked": False, "barricaded": False}
WINDOW = {"open": False, "locked": True, "barricaded": False}


def _dataset():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    with open(os.path.join(root, "data", "food-items.json"), encoding="utf-8") as f:
        return {it["id"]: it for it in json.load(f)["items"]}


DATA = _dataset()
assert DATA["Base.WaterBottle"]["kind"] == "fluid_container"     # the B42 bottle: a fluid container, never a Full name
WATER_ID = "Base.WaterBottle"


def replay(path):
    """The World a replay of `path` ends with (`agent.base.replay`, moved out of world.py under M6)."""
    return replay_summary(path).world


# -- the synthetic log ------------------------------------------------------------------------------------------------

def _sq(x, y, z=0, **k):
    return fakemod.square(**dict({"x": x, "y": y, "z": z, "light": 0.75}, **k))


SCAN_PARTS = [
    [_sq(100, 200, room="kitchen", building=7, door=DOOR,
         containers=[{"type": "fridge", "n": 1, "items": ["Base.CannedMilk"]}]),
     _sq(101, 200, room="kitchen", building=7)],
    [_sq(100, 201, room="kitchen", building=7, window=WINDOW),
     _sq(101, 201, room="kitchen", building=7, containers=[{"type": "crate", "n": 1, "items": ["Base.Hammer"]}],
         floor=["Base.Axe"])],
    [_sq(102, 200), _sq(102, 201, solid=True)],
]


def _write_synthetic(state_dir, sink=None):
    """The synthetic PZA/1 session: a hello, 30 frames (a full frame every 10, deltas between), two zombies that move
    then one dies, a `map full` scan of 3 parts (one door, one window, two containers), a `map delta` of the door
    opened, item_added x 3, item_removed x 1, a client damage event, two act lines. `sink`, a list, collects each
    keyed line the fake mod returns. Returns the FakeMod."""
    t = {"ms": 1_000_000}
    m = FakeMod(str(state_dir), clock=lambda: t["ms"] / 1000.0)
    if sink is not None:
        emit = m._emit
        m._emit = lambda kind, body, same=(): sink.append(emit(kind, body, same)) or sink[-1]

    def step():
        t["ms"] += 100

    m.hello()
    step()
    for i in range(30):
        me = dict(DEFAULT_FRAME["me"], x=100.0 + (i // 2) * 0.5, moving=i % 4 != 3)
        stats = dict(DEFAULT_FRAME["stats"], hunger=0.1 if i < 20 else 0.25)
        zs = [{"id": 11, "x": 110.0 - i * 0.25, "y": 200.0, "dist": 10.0 - i * 0.25,
               "hasTarget": i >= 5, "crawler": False, "health": 1.5}]
        if i < 15:
            zs.append({"id": 12, "x": 104.0, "y": 204.0 - i * 0.25, "dist": 5.5 - i * 0.125,
                       "hasTarget": True, "crawler": i >= 10, "health": 0.5})
        m.frame(me=me, stats=stats, zombies=zs, gameMin=480.0 + i)
        step()
        if i in (5, 6, 7):
            m.map_full(SCAN_PARTS[i - 5], scan_id=1, part=i - 4, parts=3, missing=["getModData"] if i == 6 else ())
            step()
        if i == 8:
            m.event("item_added", itemId=501, fullType="Base.CannedMilk", weight=0.75)
            m.event("item_added", itemId=502, fullType="Base.Hammer", weight=1.0)
            m.event("item_added", itemId=503, fullType="Base.WaterBottleFull", weight=1.25)
            step()
        if i == 12:
            m.map_delta(dict(SCAN_PARTS[0][0], door=dict(DOOR, open=True)))
            step()
        if i == 15:
            m.event("zombie_dead", id=12)
            step()
        if i == 18:
            m.event("item_removed", itemId=502, fullType="Base.Hammer")
            step()
        if i == 22:
            m.event("damage", tag="ZOMBIE", amount=0.5, side="client")
            step()
        if i == 24:
            m.act("a1", "accepted", "walkTo")
            step()
        if i == 26:
            m.act("a1", "done", "walkTo", result={"d": 0.25})
            step()
    return m


def _regenerate():
    """Write the committed fixtures (run once by hand; see the module docstring)."""
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        _write_synthetic(d)
        shutil.copyfile(os.path.join(d, "state.log"), LOG)
    with open(GOLDEN, "w", encoding="utf-8", newline="\n") as f:
        f.write(replay(LOG).to_json() + "\n")


# -- helpers ----------------------------------------------------------------------------------------------------------

def frame(wall, zombies=(), **groups):
    line = {"kind": "frame", "seq": 1, "tick": 1, "wallMs": wall, "gameMin": 480.0, "worldAge": 8.0,
            "zombies": list(zombies)}
    for g in ("me", "stats", "body", "load", "weapon", "action", "act", "cost"):
        line[g] = DEFAULT_FRAME[g]
    line.update(groups)
    return line


def zed(i, dist, x=0.0, y=0.0):
    return {"id": i, "x": x, "y": y, "dist": dist, "hasTarget": False, "crawler": False, "health": 1.0}


def mapline(squares, mode="full", scan_id=1, part=1, parts=1, missing=()):
    return {"kind": "map", "seq": 2, "tick": 2, "wallMs": 0, "mode": mode, "scanId": scan_id, "part": part,
            "parts": parts, "squares": list(squares), "missing": list(missing)}


def event(kind, wall=0, **fields):
    return dict({"kind": "event", "seq": 3, "tick": 3, "wallMs": wall, "event": kind, "gameMin": 480.0}, **fields)


def me_at(x, y):
    return dict(DEFAULT_FRAME["me"], x=x, y=y)


# -- frames and zombies -----------------------------------------------------------------------------------------------

def test_a_frame_fills_every_group_as_the_dict_it_carries():
    w = World()
    w.apply(frame(1000, load={"weight": 9.0, "max": 8.0, "level": 1, "n": 3}, action=None))
    assert w.me == DEFAULT_FRAME["me"] and w.me["x"] == 100.0
    assert w.stats == DEFAULT_FRAME["stats"] and w.body == DEFAULT_FRAME["body"]
    assert w.load["level"] == 1 and w.weapon["type"] == "Base.BaseballBat"
    assert w.action is None and w.act is None
    assert w.game_min == 480.0 and w.frame_wall_ms == 1000


def test_zombies_are_kept_by_id_and_age_out_by_wallMs():
    assert ZOMBIE_TTL_S == 10
    w = World()
    w.apply(frame(1000, [zed(7, 2.0, 1.0, 2.0)]))
    assert w.zombies[7] == {"x": 1.0, "y": 2.0, "dist": 2.0, "hasTarget": False, "crawler": False, "health": 1.0,
                            "seenWallMs": 1000}
    w.apply(frame(11000, []))
    assert 7 in w.zombies
    w.apply(frame(11001, []))
    assert 7 not in w.zombies


def test_a_zombie_dead_event_removes_it():
    w = World()
    w.apply(frame(0, [zed(1, 3.0), zed(2, 4.0)]))
    w.apply(event("zombie_dead", id=2))
    assert set(w.zombies) == {1}


def test_nearest_zombie_by_the_distance_from_the_current_me():
    w = World()
    assert w.nearest_zombie() is None
    w.apply(frame(0, [zed(1, 3.0, x=3.0), zed(2, 1.5, x=1.5), zed(3, None, x=2.0)], me=me_at(0.0, 0.0)))
    zid, z = w.nearest_zombie()
    assert zid == 2 and z["dist"] == 1.5


# M7 (the whole-pass review): the stored `dist` is the frame's, kept up to ZOMBIE_TTL_S after the zombie left the
# frames; a zombie whose id read nil was keyed None and reached `Attack(int(None))`.
def test_a_stale_zombie_ranks_by_its_distance_from_where_the_player_is_now():
    w = World()
    w.apply(frame(0, [zed(1, 1.0, x=1.0), zed(2, 2.0, x=-2.0)], me=me_at(0.0, 0.0)))
    w.apply(frame(1000, [zed(2, 3.0, x=-2.0)], me=me_at(-1.0, 0.0)))    # 1 left the frames; the player moved
    assert w.zombies[1]["dist"] == 1.0                                    # its stored dist: stale
    assert w.nearest_zombie()[0] == 2                                     # 1 is 2 tiles away now, 2 is 1


@pytest.mark.parametrize("zid", [None, "7", 7.0, True])
def test_a_zombie_whose_id_is_not_an_int_is_never_nearest(zid):
    w = World()
    w.apply(frame(0, [zed(zid, 0.5, x=0.5), zed(9, 4.0, x=4.0)], me=me_at(0.0, 0.0)))
    assert w.nearest_zombie()[0] == 9
    w = World()
    w.apply(frame(0, [zed(zid, 0.5, x=0.5)], me=me_at(0.0, 0.0)))
    assert w.nearest_zombie() is None


def test_an_unknown_kind_counts_and_never_raises():
    w = World()
    w.apply({"kind": "bogus", "seq": 1})
    w.apply({"seq": 2})
    assert w.unknown_kinds == 2


def test_merge_server_keeps_the_stats_and_their_wall():
    w = World()
    w.merge_server({"hunger": 0.5}, 1234)
    assert w.server == {"stats": {"hunger": 0.5}, "wallMs": 1234}


# -- the map ----------------------------------------------------------------------------------------------------------

def test_a_map_full_part_applies_its_squares_and_containers_at_once():
    w = World()
    w.apply(mapline(SCAN_PARTS[0], part=1, parts=3))
    assert set(w.map) == {(100, 200, 0), (101, 200, 0)}            # no whole-scan hold
    assert w.map[(100, 200, 0)]["door"] == DOOR
    assert w.containers == {(100, 200, 0, 0): {"type": "fridge", "n": 1, "items": ["Base.CannedMilk"],
                                               "looted": set()}}
    assert w.buildings == {7}
    w.apply(mapline(SCAN_PARTS[1], part=2, parts=3, missing=["getModData"]))
    w.apply(mapline(SCAN_PARTS[2], part=3, parts=3, missing=["getModData", "isSolid"]))
    assert len(w.map) == 6 and len(w.containers) == 2
    assert (101, 201, 0, 0) in w.containers                      # the floor list is not a container
    assert w.missing == ["getModData", "isSolid"] and w.map_lines == 3 and w.dropped_scans == 0


def test_a_looted_mark_survives_a_rescan_of_the_same_type_only():
    w = World()
    box = lambda typ: [_sq(1, 1, containers=[{"type": typ, "n": 1, "items": ["Base.Milk"]}])]
    w.apply(mapline(box("fridge")))
    w.mark_looted((1, 1, 0, 0))
    w.mark_looted((9, 9, 9, 9))                                   # unknown: ignored
    w.apply(mapline(box("fridge"), scan_id=2))
    assert w.containers[(1, 1, 0, 0)]["looted"] == set(items.USES)   # no use: looted for every use
    w.apply(mapline(box("crate"), scan_id=3))
    assert w.containers[(1, 1, 0, 0)]["looted"] == set()


# Plan 23 Task 11 fix 1 (review-t11 I1): a loot filters one use, so the looted mark is per use.
def test_a_container_looted_for_one_use_is_still_unlooted_for_another():
    w = World()
    w.apply(frame(0, me=me_at(0.0, 0.0)))
    w.apply(mapline([_sq(1, 0, containers=[{"type": "counter", "n": 2, "items": [WATER_ID, "Base.Apple"]}])]))
    w.mark_looted((1, 0, 0, 0), "water")
    assert w.containers[(1, 0, 0, 0)]["looted"] == {"water"}
    assert w.nearest_unlooted("water") is None and w.nearest_unlooted("food") == (1, 0, 0, 0)
    assert w.nearest_unlooted() is None                          # no want: any mark reads looted
    w.apply(mapline([_sq(1, 0, containers=[{"type": "counter", "n": 2, "items": [WATER_ID, "Base.Apple"]}])],
                    scan_id=2))
    assert w.containers[(1, 0, 0, 0)]["looted"] == {"water"}     # kept across a re-scan of the same type
    w.mark_looted((1, 0, 0, 0), "food")
    assert w.nearest_unlooted("food") is None
    assert json.loads(w.to_json())["containers"]["1,0,0,0"]["looted"] == ["food", "water"]


def test_an_unmarked_container_serialises_looted_false_and_exclude_skips_a_key():
    w = World()
    w.apply(frame(0, me=me_at(0.0, 0.0)))
    w.apply(mapline([_sq(1, 0, containers=[{"type": "fridge", "n": 1, "items": ["Base.Apple"]}]),
                     _sq(4, 0, containers=[{"type": "fridge", "n": 1, "items": ["Base.Apple"]}])]))
    assert json.loads(w.to_json())["containers"]["1,0,0,0"]["looted"] is False   # the goldens' bytes
    assert w.nearest_unlooted("food", exclude={(1, 0, 0, 0)}) == (4, 0, 0, 0)


def test_a_square_rescanned_with_fewer_containers_drops_the_stale_ones():
    w = World()
    two = [{"type": "fridge", "n": 1, "items": ["Base.Milk"]}, {"type": "crate", "n": 1, "items": ["Base.Nails"]}]
    w.apply(mapline([_sq(1, 1, containers=two)]))
    assert set(w.containers) == {(1, 1, 0, 0), (1, 1, 0, 1)}
    w.apply(mapline([_sq(1, 1, containers=two[:1])], mode="delta"))
    assert set(w.containers) == {(1, 1, 0, 0)}


def test_a_map_delta_replaces_one_square():
    w = World()
    w.apply(mapline(SCAN_PARTS[0]))
    w.apply(mapline([dict(SCAN_PARTS[0][0], door=dict(DOOR, open=True))], mode="delta"))
    assert w.map[(100, 200, 0)]["door"]["open"] is True
    assert w.map[(101, 200, 0)] == SCAN_PARTS[0][1]
    assert w.map_lines == 2 and w.dropped_scans == 0


def test_a_null_square_and_a_bad_damage_record_never_raise():
    w = World()
    w.apply(mapline([None, _sq(1, 1)]))
    w.merge_damage({"ok": True, "counts": {}, "n": 0, "last": [None, {"i": 1, "tag": "X", "amount": 1.0}],
                    "dropped": 0}, 5)
    assert set(w.map) == {(1, 1, 0)} and len(w.damage) == 1


def test_a_full_part_of_an_older_scan_is_dropped_and_counted():
    w = World()
    w.apply(mapline([_sq(5, 5)], scan_id=4))
    w.apply(mapline([_sq(1, 1)], scan_id=3, part=2, parts=2))
    assert w.dropped_scans == 1 and (1, 1, 0) not in w.map
    w.apply(mapline([_sq(6, 6)], scan_id=4, part=2, parts=2))     # the same scan's next part is not older
    w.apply(mapline([_sq(2, 2)], mode="delta", scan_id=1))        # a delta is never dropped
    assert w.dropped_scans == 1 and {(5, 5, 0), (6, 6, 0), (2, 2, 0)} <= set(w.map)


# -- inventory, damage, acts, events ----------------------------------------------------------------------------------

def test_item_events_build_the_inventory_by_id():
    w = World()
    w.apply(event("item_added", itemId=1, fullType="Base.Apple", weight=0.2))
    w.apply(event("item_added", itemId=2, fullType="Base.Hammer", weight=1.0))
    w.apply(event("item_removed", itemId=1, fullType="Base.Apple"))
    w.apply(event("item_removed", itemId=99, fullType="Base.Nails"))
    assert w.inventory == {2: {"fullType": "Base.Hammer", "weight": 1.0}}
    assert w.missing_items == 1 and len(w.events) == 4


def test_damage_lands_from_both_sides():
    w = World()
    w.apply(event("damage", wall=500, tag="ZOMBIE", amount=0.5, side="client"))
    reply = {"ok": True, "counts": {"HEAVYLOAD": 2}, "n": 2, "dropped": 0,
             "last": [{"i": 1, "tag": "HEAVYLOAD", "amount": 0.381, "wall": 10},
                      {"i": 2, "tag": "HEAVYLOAD", "amount": 0.381, "wall": 11}]}
    w.merge_damage(reply, 900)
    w.merge_damage(dict(reply, counts={"HEAVYLOAD": 3}, n=3,
                        last=reply["last"] + [{"i": 3, "tag": "HEAVYLOAD", "amount": 0.25, "wall": 12}]), 950)
    assert list(w.damage) == [
        {"tag": "ZOMBIE", "amount": 0.5, "side": "client", "wallMs": 500},
        {"tag": "HEAVYLOAD", "amount": 0.381, "side": "server", "wallMs": 900},
        {"tag": "HEAVYLOAD", "amount": 0.381, "side": "server", "wallMs": 900},
        {"tag": "HEAVYLOAD", "amount": 0.25, "side": "server", "wallMs": 950},
    ]
    assert w.damage_counts_server == {"HEAVYLOAD": 3} and w.damage_seen_i == {1, 2, 3}
    assert w.damage.maxlen == 500 and w.events.maxlen == 500


def test_act_lines_keep_the_last_per_aid_and_hello_and_reply():
    w = World()
    w.apply({"kind": "hello", "seq": 1, "tick": 0, "wallMs": 0, "proto": "PZA/1", "mod": "fake", "build": "42.21.0",
             "user": "agent", "rate": 10, "caps": ["walkTo"], "mode": "append"})
    a = {"kind": "act", "seq": 2, "tick": 1, "wallMs": 1, "aid": "a1", "type": "walkTo", "state": "accepted",
         "reason": "", "result": None, "snapshot": None}
    w.apply(a)
    w.apply(dict(a, seq=3, state="done", result={}))
    w.apply(dict(a, seq=4, aid="a2", state="rejected", reason="bad args"))
    w.apply({"kind": "reply", "seq": 5, "tick": 1, "wallMs": 2, "to": 4, "body": {"ok": True}})
    assert w.acts["a1"]["state"] == "done" and w.acts["a2"]["reason"] == "bad args"
    assert w.hello["proto"] == "PZA/1" and w.last_reply["to"] == 4 and w.unknown_kinds == 0


# -- the heuristics ---------------------------------------------------------------------------------------------------

def test_nearest_unlooted_filters_and_skips_the_looted_and_the_empty():
    w = World()
    w.apply(frame(0, me=me_at(0.0, 0.0)))
    w.apply(mapline([_sq(1, 0, containers=[{"type": "crate", "n": 1, "items": ["Base.Nails"]}]),
                     _sq(2, 0, containers=[{"type": "crate", "n": 0, "items": []}], floor=["Base.Apple"]),
                     _sq(5, 0, containers=[{"type": "fridge", "n": 1, "items": ["Base.CannedMilk"]}]),
                     _sq(9, 0, containers=[{"type": "shelf", "n": 1, "items": [WATER_ID]}])]))
    assert w.nearest_unlooted() == (1, 0, 0, 0)
    assert w.nearest_unlooted("food") == (5, 0, 0, 0)
    assert w.nearest_unlooted("water") == (9, 0, 0, 0)
    w.mark_looted((5, 0, 0, 0))
    assert w.nearest_unlooted("food") is None


def test_unexplored_edge_as_plan_21():
    w = World()
    assert w.unexplored_edge() is None
    w.apply(frame(0, me=me_at(1.0, 1.0)))
    w.apply(mapline([_sq(x, y, solid=(x, y) == (0, 0)) for x in range(3) for y in range(3)]))
    assert w.unexplored_edge() == (0, 1)       # (1,1) is interior; ties at distance 1 break by (x, y)


def test_the_heuristics_survive_a_null_me():
    w = World()
    w.apply(frame(0, me=None))
    w.apply(mapline([_sq(1, 0, containers=[{"type": "crate", "n": 1, "items": ["Base.Nails"]}])]))
    assert w.me is None and w.nearest_unlooted() == (1, 0, 0, 0) and w.unexplored_edge() == (1, 0)


# -- replay and the fixtures ------------------------------------------------------------------------------------------

def test_replay_of_the_committed_log_equals_the_committed_json_byte_for_byte():
    with open(GOLDEN, encoding="utf-8", newline="") as f:
        assert replay(LOG).to_json() + "\n" == f.read()


def test_the_fake_mod_regenerates_the_committed_log_byte_for_byte(tmp_path):
    _write_synthetic(tmp_path)
    with open(LOG, "rb") as f:
        assert (tmp_path / "state.log").read_bytes() == f.read()


def test_to_json_is_byte_stable_and_replay_merges_deltas_as_the_fake_wrote(tmp_path):
    a, b = replay(LOG).to_json(), replay(LOG).to_json()
    assert a == b
    wrote = []
    _write_synthetic(tmp_path, sink=wrote)                        # the keyed, SAME-free lines the fake wrote
    direct = World()
    for line in wrote:
        direct.apply(line)
    assert replay(str(tmp_path / "state.log")).to_json() == a
    assert json.loads(direct.to_json()) == json.loads(a)          # equal values (the wire writes 100.0 as 100)
    w = replay(LOG)
    assert w.stats["hunger"] == 0.25 and w.me["x"] == 107.0 and set(w.zombies) == {11}
    assert w.containers[(100, 200, 0, 0)]["items"] == ["Base.CannedMilk"]
    assert w.map[(100, 200, 0)]["door"]["open"] is True and w.missing == ["getModData"] and w.map_lines == 4
    assert w.inventory == {501: {"fullType": "Base.CannedMilk", "weight": 0.75},
                           503: {"fullType": "Base.WaterBottleFull", "weight": 1.25}}
    assert list(w.damage) == [{"tag": "ZOMBIE", "amount": 0.5, "side": "client", "wallMs": 1003100}]
    assert w.acts["a1"]["state"] == "done" and w.hello["proto"] == "PZA/1"
    assert w.nearest_unlooted("food") == (100, 200, 0, 0)
    assert w.unknown_kinds == 0 and w.dropped_scans == 0
    s = replay_summary(LOG)
    assert s.bad == 0 and s.gaps == 0 and s.gap_list == [] and s.world_json == a


def test_a_new_hello_resets_the_scan_and_damage_indexes():
    hello = {"kind": "hello", "seq": 1, "tick": 0, "wallMs": 0, "proto": "PZA/1", "mod": "fake", "build": "42.21.0",
             "user": "agent", "rate": 10, "caps": [], "mode": "append"}
    w = World()
    w.apply(hello)
    w.apply(mapline([_sq(5, 5)], scan_id=3))
    w.merge_damage({"ok": True, "counts": {}, "n": 1, "dropped": 0,
                    "last": [{"i": 1, "tag": "X", "amount": 1.0, "wall": 1}]}, 10)
    w.apply(dict(hello, seq=2))                                   # a client relaunch: scanId restarts
    w.apply(mapline([_sq(1, 1)], scan_id=1))
    assert (1, 1, 0) in w.map and w.dropped_scans == 0
    w.merge_damage({"ok": True, "counts": {}, "n": 1, "dropped": 0,
                    "last": [{"i": 1, "tag": "Y", "amount": 2.0, "wall": 2}]}, 20)
    assert [d["tag"] for d in w.damage] == ["X", "Y"]


def test_acts_are_keyed_by_string_and_damage_seen_i_renders_numerically():
    w = World()
    a = {"kind": "act", "seq": 2, "tick": 1, "wallMs": 1, "type": "stop", "state": "accepted", "reason": "",
         "result": None, "snapshot": None}
    w.apply(a)                                                    # no aid
    w.apply(dict(a, aid="a1"))
    assert set(w.acts) == {"None", "a1"}
    last = [{"i": i, "tag": "X", "amount": 1.0, "wall": 1} for i in (10, 9, 2)]
    w.merge_damage({"ok": True, "counts": {}, "n": 3, "dropped": 0, "last": last}, 5)
    assert json.loads(w.to_json())["damageSeenI"] == [2, 9, 10]


# -- M12 (the whole-pass review), ruling S-27: reasons.py's docstring rewritten, its code frozen -------------------------

def test_the_plan_21_reasons_module_imports_unchanged_and_names_no_deleted_file():
    import hashlib

    from agent import reasons
    from agent.base import pza1
    assert reasons.REASONS == frozenset({
        "bad args", "no square", "no path", "stuck", "superseded", "no door", "locked", "not adjacent", "no container",
        "not loaded", "empty", "no match", "none held", "interrupted", "not valid",
        "no weapon", "weapon broke", "low health", "cornered", "not allowed", "dead"})
    assert reasons.DONE == frozenset({"d=", "moved=", "open", "consumed", "clear", "at", "awake"})
    src = open(reasons.__file__, encoding="utf-8").read()
    code = src[src.index('"""', 3) + 3:]
    # the code below the docstring, byte for byte as frozen (sha256 read at b5ada9f9)
    assert hashlib.sha256(code.encode("utf-8")).hexdigest() == (
        "21d3b07c8562024ff8aa32c1d35e889327e61256dd1f2a871efc96e6c2063a96")
    assert "PZAgent_Act" not in reasons.__doc__ and "pza1.REASONS" in reasons.__doc__
    assert reasons.REASONS != pza1.REASONS


# ---- X4 fix pass fix 1 (ruling S-32): a dropped scan's aid kept for the planner ----------------------------------------

def test_a_scan_dropped_event_records_its_scans_aid_and_never_touches_the_act():
    w = World()
    act = {"kind": "act", "seq": 2, "tick": 2, "wallMs": 0, "aid": "a1", "type": "scan", "state": "done", "reason": "",
           "result": {"queued": 3}, "snapshot": None}
    w.apply(act)
    w.apply(event("scan_dropped", scanId=1, aid="a1", part=2, parts=3, reason="java raised"))
    assert w.scans_dropped == {"a1"} and w.acts["a1"] is act
    assert "scansDropped" not in json.loads(w.to_json())     # the planner's memory, like stuck: the goldens unchanged


# -- Plan 23 Task 9: the edges, the line, interiors, the inventory by use, the empties --------------------------------

def _grid(x0, y0, x1, y1, z=0, **over):
    """An open grid of squares (x0..x1, y0..y1) on floor z; `over` maps (x, y) to the fields laid over that square."""
    over = over.get("over", {})
    return [_sq(x, y, z, **over.get((x, y), {})) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def _world(squares, me=(0.0, 0.0)):
    w = World()
    w.apply(frame(0, me=me_at(*me)))
    w.apply(mapline(squares))
    return w


def test_blocked_reads_the_north_and_west_edge_both_ways():
    w = _world(_grid(0, 0, 2, 2, over={(1, 1): {"blockN": True}, (2, 1): {"blockW": True}}))
    assert w.blocked((1, 0, 0), (1, 1, 0)) and w.blocked((1, 1, 0), (1, 0, 0))    # (1,1)'s north edge
    assert w.blocked((1, 1, 0), (2, 1, 0)) and w.blocked((2, 1, 0), (1, 1, 0))    # (2,1)'s west edge
    assert not w.blocked((0, 1, 0), (1, 1, 0)) and not w.blocked((1, 1, 0), (1, 2, 0))
    assert not w.blocked((0, 0, 0), (0, 1, 0))


def test_blocked_counts_an_unknown_square_or_a_null_edge_blocked():
    w = _world(_grid(0, 0, 1, 0, over={(1, 0): {"blockW": None}}))
    assert w.blocked((0, 0, 0), (1, 0, 0))                     # a null edge
    assert w.blocked((0, 0, 0), (0, 1, 0))                     # (0,1) is not in the map
    assert w.blocked((0, 0, 0), (-1, 0, 0))
    with pytest.raises(ValueError):
        w.blocked((0, 0, 0), (2, 0, 0))                        # not adjacent


@pytest.mark.parametrize("over", [
    {(1, 0): {"blockW": True}},      # the edge between a and the corner square (1,0)
    {(0, 1): {"blockN": True}},      # the edge between a and the corner square (0,1)
    {(1, 1): {"blockN": True}},      # the edge between (1,0) and b
    {(1, 1): {"blockW": True}},      # the edge between (0,1) and b
    {(1, 0): {"solid": True}},       # a solid corner square
    {(0, 1): {"solid": True}},
])
def test_a_diagonal_is_blocked_by_any_edge_meeting_at_the_corner_or_a_solid_corner(over):
    a, b = (0, 0, 0), (1, 1, 0)
    assert not _world(_grid(-1, -1, 2, 2)).blocked(a, b)
    w = _world(_grid(-1, -1, 2, 2, over=over))
    assert w.blocked(a, b) and w.blocked(b, a)


def test_a_diagonal_ignores_an_edge_away_from_its_corner():
    w = _world(_grid(-1, -1, 2, 2, over={(0, 0): {"blockN": True, "blockW": True}, (2, 1): {"blockW": True}}))
    assert not w.blocked((0, 0, 0), (1, 1, 0))
    assert w.blocked((0, 0, 0), (-1, -1, 0))                   # the north-west corner meets both of (0,0)'s edges


def test_line_clear_stops_at_a_blocked_edge_entered_from_either_side():
    w = _world(_grid(0, 0, 4, 0, over={(2, 0): {"blockW": True}}), me=(0.5, 0.5))
    assert not w.line_clear((0.5, 0.5), (4.5, 0.5)) and not w.line_clear((4.5, 0.5), (0.5, 0.5))
    assert w.line_clear((0.5, 0.5), (1.9, 0.2))                # stops short of the edge
    assert w.line_clear((2.1, 0.5), (4.5, 0.5))                # starts past it


def test_line_clear_passes_an_open_edge_and_a_seen_but_unblocked_edge():
    w = _world(_grid(0, 0, 4, 0, over={(2, 0): {"edgeW": True}}), me=(0.5, 0.5))   # an open doorway: an edge, unblocked
    assert w.line_clear((0.5, 0.5), (4.5, 0.5))
    w = _world(_grid(0, 0, 0, 4, over={(0, 3): {"blockN": True}}), me=(0.5, 0.5))
    assert not w.line_clear((0.5, 0.5), (0.5, 4.5))            # the north edge, crossed going south


def test_line_clear_stops_at_a_solid_or_unknown_square_between_but_not_at_the_ends():
    w = _world(_grid(0, 0, 4, 0, over={(2, 0): {"solid": True}, (4, 0): {"solid": True}}), me=(0.5, 0.5))
    assert not w.line_clear((0.5, 0.5), (4.5, 0.5))
    assert w.line_clear((2.5, 0.5), (3.5, 0.5)) and w.line_clear((3.5, 0.5), (4.5, 0.5))
    w = _world([s for s in _grid(0, 0, 4, 0) if (s["x"], s["y"]) != (2, 0)], me=(0.5, 0.5))
    assert not w.line_clear((0.5, 0.5), (4.5, 0.5))
    assert w.line_clear((1.5, 0.5), (1.2, 0.7))                # one square: nothing crossed


def test_line_clear_walks_a_diagonal_through_its_corners():
    w = _world(_grid(0, 0, 3, 3), me=(0.5, 0.5))
    assert w.line_clear((0.5, 0.5), (3.5, 3.5))
    w = _world(_grid(0, 0, 3, 3, over={(2, 2): {"blockN": True}}), me=(0.5, 0.5))
    assert not w.line_clear((0.5, 0.5), (3.5, 3.5))            # the (1,1)->(2,2) step's corner edge


def test_line_clear_reads_the_players_floor():
    w = _world(_grid(0, 0, 4, 0, z=1), me=(0.5, 0.5))
    assert not w.line_clear((0.5, 0.5), (4.5, 0.5))            # the player is on z 0, the squares are on z 1
    w.apply(frame(1, me=dict(me_at(0.5, 0.5), z=1)))
    assert w.line_clear((0.5, 0.5), (4.5, 0.5))


def test_reachable_adjacent_leaves_out_the_blocked_side_of_a_door_square():
    door = {"blockN": True, "door": DOOR}                     # a closed door on (5,5)'s north edge
    w = _world(_grid(3, 3, 7, 7, over={(5, 5): door, (6, 6): {"solid": True}}), me=(5.5, 7.5))
    got = w.reachable_adjacent((5.5, 5.5), 0)
    assert got == [(5, 6, 0), (4, 6, 0), (4, 5, 0), (6, 5, 0)]
    assert (5, 4, 0) not in got and (4, 4, 0) not in got and (6, 4, 0) not in got   # the door's far side
    w2 = _world([s for s in _grid(3, 3, 7, 7) if (s["x"], s["y"]) != (4, 5)], me=(5.5, 7.5))
    assert (4, 5, 0) not in w2.reachable_adjacent((5.5, 5.5), 0)                  # an unmapped neighbour


def test_interiors_group_the_room_squares_by_building_and_doors_of_names_the_door_squares():
    sq = [_sq(1, 1, room="kitchen", building=7, door=DOOR), _sq(2, 1, room="kitchen", building=7),
          _sq(1, 2, room="hall", building=7), _sq(9, 9, room="shed", building=8, door=DOOR),
          _sq(5, 5), _sq(6, 5, building=7, door=DOOR)]
    w = _world(sq)
    assert w.interiors() == {7: [(1, 1, 0), (1, 2, 0), (2, 1, 0)], 8: [(9, 9, 0)]}
    assert w.doors_of(7) == [(1, 1, 0), (6, 5, 0)] and w.doors_of(8) == [(9, 9, 0)] and w.doors_of(3) == []
    assert w.buildings == {7, 8}


def _use(name):
    """What the dataset says an item is for (food, unless it is `cant_eat`, a sealed can: fix wave P I-4; a fluid
    container, water), None when it says nothing."""
    it = DATA.get(name) or {}
    if it.get("cant_eat"):
        return "other"
    return {"food": "food", "fluid_container": "water"}.get(it.get("kind"))


def test_by_use_sorts_the_inventory_by_the_datasets_use():
    w = World()
    names = {1: WATER_ID, 2: "Base.CannedBeans", 3: "Base.TinnedBeans", 4: "Base.Bowl", 5: "Base.Hammer",
             6: "Base.Bandage", 7: "Base.Nails"}
    for iid, ft in names.items():
        w.apply(event("item_added", itemId=iid, fullType=ft, weight=1.0))
    got = w.by_use()
    assert set(got) == set(items.USES)
    for iid, ft in names.items():
        want = _use(ft) or items.use_of(ft)
        assert iid in got[want], (ft, want, got)
        assert sum(iid in v for v in got.values()) == 1
    assert 1 in got["water"] and 5 in got["weapon"] and 6 in got["bandage"] and 7 in got["other"]
    assert got["food"] == sorted(got["food"])


def test_mark_empty_moves_an_id_out_of_water_and_to_json_carries_it_sorted():
    w = World()
    assert "emptyIds" not in json.loads(w.to_json())           # absent while empty (the goldens keep their bytes)
    w.apply(event("item_added", itemId=9, fullType=WATER_ID, weight=0.2))
    w.apply(event("item_added", itemId=4, fullType=WATER_ID, weight=0.2))
    assert w.by_use()["water"] == [4, 9]
    w.mark_empty(9)
    w.mark_empty(4)
    assert w.by_use()["water"] == [] and w.by_use()["other"] == [4, 9]
    assert json.loads(w.to_json())["emptyIds"] == [4, 9]
    assert w.to_json() == w.to_json()
    w.apply(event("item_removed", itemId=9))
    assert w.empty_ids == {4}


def test_nearest_unlooted_keys_on_the_datasets_use():
    w = World()
    w.apply(frame(0, me=me_at(0.0, 0.0)))
    w.apply(mapline([_sq(1, 0, containers=[{"type": "crate", "n": 1, "items": ["Base.Hammer"]}]),
                     _sq(3, 0, containers=[{"type": "shelf", "n": 1, "items": ["Base.Carrots"]}]),
                     _sq(6, 0, containers=[{"type": "shelf", "n": 1, "items": ["Base.DrinkingGlass"]}])]))
    assert DATA["Base.Carrots"]["kind"] == "food" and DATA["Base.DrinkingGlass"]["kind"] == "fluid_container"
    assert w.nearest_unlooted("food") == (3, 0, 0, 0)
    assert w.nearest_unlooted("water") == (6, 0, 0, 0)          # a glass the Plan 22 WATER_RX missed
    assert w.nearest_unlooted("weapon") == (1, 0, 0, 0)
    assert w.nearest_unlooted() == (1, 0, 0, 0)


def test_by_use_prefers_the_events_use_and_falls_back_to_the_dataset():
    w = World()
    w.apply(event("item_added", itemId=1, fullType="Base.PowerBar", weight=0.1, use="food"))
    w.apply(event("item_added", itemId=2, fullType="Base.Apple", weight=0.1, use="other"))
    w.apply(event("item_added", itemId=3, fullType="Base.Hammer", weight=1.0))
    got = w.by_use()
    assert got["food"] == [1] and 2 in got["other"] and got["weapon"] == [3]
    assert w.inventory[1]["use"] == "food" and "use" not in w.inventory[3]
    w.mark_empty(1)
    w.apply(event("item_added", itemId=4, fullType="Base.Bowl", weight=0.1, use="water"))
    w.mark_empty(4)
    assert 4 in w.by_use()["other"]


def test_by_use_reads_a_sealed_can_other_whatever_the_engines_use_and_a_stray_use_falls_back():
    w = World()
    w.apply(event("item_added", itemId=1, fullType="Base.TinnedBeans", weight=0.8, use="food"))   # N-3
    w.apply(event("item_added", itemId=2, fullType="Base.Apple", weight=0.1, use="zzz"))
    assert items.cant_eat("Base.TinnedBeans") and not items.cant_eat("Base.Apple")
    got = w.by_use()
    assert 1 in got["other"] and got["food"] == [2]


def test_world_minutes_without_a_world_age_counts_from_the_first_game_min_and_wraps_at_a_day():
    w = World()
    assert w.world_minutes() == 0.0
    w.game_min = 1430.0
    assert w.world_minutes() == 0.0
    w.game_min = 1439.0
    assert w.world_minutes() == 9.0
    w.game_min = 10.0                                   # past midnight: (10 - 1430) % 1440
    assert w.world_minutes() == 20.0


# -- fix wave P: the monotonic game clock (I-1), the map-version cache (M-4), the refused foods (I-4) -----------------

def test_world_minutes_reads_world_age_and_never_wraps_at_midnight():
    w = World()
    assert w.world_minutes() == 0.0
    w.apply(frame(0, gameMin=1439.0, worldAge=23.0 + 59.0 / 60.0))
    assert w.world_minutes() == pytest.approx(1439.0)
    w.apply(frame(0, gameMin=1.0, worldAge=24.0 + 1.0 / 60.0))   # 00:01 the next day: gameMin wrapped
    assert w.game_min == 1.0 and w.world_minutes() == pytest.approx(1441.0)
    w.apply(frame(0, gameMin=5.0, worldAge=None))                # a frame with no worldAge: gameMin since its first read (D-7)
    assert w.world_minutes() == 0.0
    w.apply(frame(0, gameMin=9.0, worldAge=None))
    assert w.world_minutes() == 4.0


def test_a_stuck_mark_made_before_midnight_expires_after_it():
    w = World()
    w.apply(frame(0, me=me_at(1.0, 1.0), gameMin=1430.0, worldAge=1430.0 / 60.0))
    w.apply(mapline([_sq(x, y) for x in range(3) for y in range(3)]))
    edge = w.unexplored_edge()
    w.mark_stuck(*edge)
    assert w.unexplored_edge() != edge
    w.apply(frame(0, me=me_at(1.0, 1.0), gameMin=10.0, worldAge=(1440.0 + 10.0) / 60.0))   # 20 game minutes on
    assert w.unexplored_edge() != edge
    w.apply(frame(0, me=me_at(1.0, 1.0), gameMin=50.0, worldAge=(1440.0 + 50.0) / 60.0))   # STUCK_TTL_MIN on
    assert w.unexplored_edge() == edge


def test_interiors_and_doors_are_cached_per_map_version():
    w = _world([_sq(1, 1, room="kitchen", building=7, door=DOOR), _sq(2, 1, room="kitchen", building=7)])
    v0 = w.map_version
    a = w.interiors()
    assert w.interiors() is a and w.map_version == v0           # no square applied: the same object
    walks = []
    real = World._index

    def counting(self):
        walks.append(1)
        return real(self)
    World._index = counting
    try:
        w.interiors(), w.doors_of(7), w.doors_of(8), w.interiors()
        assert walks == []                                      # every read off the cached index
        w.apply(mapline([_sq(9, 9, room="shed", building=8, door=DOOR)], scan_id=2))
        assert w.map_version > v0
        assert w.interiors() == {7: [(1, 1, 0), (2, 1, 0)], 8: [(9, 9, 0)]} and w.doors_of(8) == [(9, 9, 0)]
        w.doors_of(7)
        assert walks == [1]                                     # one walk per map version
    finally:
        World._index = real


def test_mark_refused_drops_a_food_from_by_use_and_to_json_carries_it_only_when_non_empty():
    w = World()
    golden = w.to_json()
    w.apply(event("item_added", itemId=8, fullType="Base.Apple", weight=0.2))
    w.apply(event("item_added", itemId=3, fullType="Base.Apple", weight=0.2))
    assert "refusedIds" not in json.loads(w.to_json())
    w.mark_refused(8)
    assert w.by_use()["food"] == [3] and 8 in w.by_use()["other"]
    assert json.loads(w.to_json())["refusedIds"] == [8]
    w.apply(event("item_removed", itemId=8))
    assert w.refused == {} and "refusedIds" not in json.loads(w.to_json())
    assert "refusedIds" not in golden


def test_a_refusal_excludes_the_food_for_refused_ttl_min_world_minutes_only():
    """P23-AD: a refused food reads `other` for REFUSED_TTL_MIN (120) world minutes from its refusal, then food again;
    `refusedIds` names the ids excluded now, and is absent once none is."""
    from agent.base.world import REFUSED_TTL_MIN
    assert REFUSED_TTL_MIN == 120
    w, twin = World(), World()                                         # the twin never refuses
    for x in (w, twin):
        x.apply(frame(0, gameMin=1400.0, worldAge=1400.0 / 60.0))
        x.apply(event("item_added", itemId=8, fullType="Base.Apple", weight=0.2))
    w.mark_refused(8)
    assert w.refused == {8: 1400.0}
    w.apply(frame(0, gameMin=20.0, worldAge=1460.0 / 60.0))           # +60, past midnight
    assert w.by_use()["food"] == [] and 8 in w.by_use()["other"]
    assert json.loads(w.to_json())["refusedIds"] == [8]
    for x in (w, twin):
        x.apply(frame(0, gameMin=81.0, worldAge=1521.0 / 60.0))       # +121
    assert w.by_use()["food"] == [8] and "refusedIds" not in json.loads(w.to_json())
    assert w.to_json() == twin.to_json()                               # nothing refused now: the same bytes
