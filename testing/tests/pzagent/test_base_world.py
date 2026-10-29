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


def test_unknown_open_reads_an_unmapped_diagonal_corner_open_and_the_default_refuses_it():
    """Survival 1 fix round 3 (F5): a diagonal step between two known squares, one corner square unmapped."""
    a, b = (0, 0, 0), (1, 1, 0)
    w = _world([s for s in _grid(-1, -1, 2, 2) if (s["x"], s["y"]) != (0, 1)], me=(0.5, 0.5))
    assert w.blocked(a, b) and w.blocked(b, a)
    assert not w.blocked(a, b, unknown_open=True) and not w.blocked(b, a, unknown_open=True)
    assert not w.line_clear((0.5, 0.5), (1.5, 1.5)) and w.line_clear((0.5, 0.5), (1.5, 1.5), unknown_open=True)
    w = _world(_grid(-1, -1, 2, 2, over={(0, 1): {"solid": True}}), me=(0.5, 0.5))   # a known solid corner: as today
    assert w.blocked(a, b, unknown_open=True)
    w = _world([s for s in _grid(-1, -1, 2, 2, over={(1, 0): {"blockW": True}}) if (s["x"], s["y"]) != (0, 1)],
               me=(0.5, 0.5))                                   # the known corner's edge still blocks
    assert w.blocked(a, b, unknown_open=True)


def test_openings_name_the_open_doorway_of_a_room_whose_doors_are_broken():
    """Survival 2 (ruling P23-AJ 3 as amended, the chain's E2): building 3's bathroom, its doors broken (door debris
    on the floor, no door record anywhere), one doorway on the west edge of (2, 2) and, beside it as on E2's map, a
    smashed window on the west edge of (2, 1) (its record `open` false, `edgeW` true, `blockW` false): the openings
    are the doorway only (fix round 1, the review's G1 and M3); a window on a south edge, held by the square below,
    is none either; a shut edge, a null edge and an unmapped neighbour are none."""
    debris = ["Base.UnusableWood", "Base.Doorknob", "Base.Hinge"]
    over = {}
    for x in (2, 3):
        for y in (1, 2, 3):
            over[(x, y)] = {"room": "bathroom", "building": 3, "blockW": x == 2 and y == 3, "blockN": y == 1,
                            "edgeW": x == 2 and y != 2}
    over[(2, 1)]["window"] = {"open": False, "locked": True, "barricaded": False}   # smashed: blockW false
    over[(2, 2)]["floor"] = debris
    for y in (1, 2, 3):
        over[(4, y)] = {"blockW": True}
    over[(2, 4)] = {"blockN": True}
    over[(3, 4)] = {"blockN": False, "edgeN": True, "window": {"open": False, "locked": True, "barricaded": False}}
    w = _world(_grid(0, 0, 5, 5, over=over), me=(2.5, 2.5))
    assert w.doors_of(3) == []
    assert w.openings(3) == [((2, 2, 0), (1, 2, 0))]
    assert not w.blocked((2, 1, 0), (1, 1, 0)) and not w.blocked((3, 3, 0), (3, 4, 0))   # open edges, windows both
    over[(2, 2)].update(blockW=True, door=DOOR)                    # the doorway shut: a closed door's edge
    w = _world(_grid(0, 0, 5, 5, over=over), me=(2.5, 2.5))
    assert w.openings(3) == []
    over[(3, 1)]["blockN"] = None                                  # a null edge reads blocked
    w = _world(_grid(0, 0, 5, 5, over=over), me=(2.5, 2.5))
    assert w.openings(3) == []
    over[(3, 1)]["blockN"] = False                                 # open, its neighbour unmapped: none
    w = _world([s for s in _grid(0, 0, 5, 5, over=over) if (s["x"], s["y"]) != (3, 0)], me=(2.5, 2.5))
    assert w.openings(3) == []
    w = _world(_grid(0, 0, 5, 5, over=over), me=(2.5, 2.5))       # mapped: the step out reads open
    assert w.openings(3) == [((3, 1, 0), (3, 0, 0))]


def test_door_way_reads_the_door_s_own_edge():
    """Survival 3, the coordinator's amendment 5 to ruling P23-AM (E2's and E3's bedroom door): a 2 x 2 building 5 at
    x 2..3, y 2..3 in an open yard. A closed door on the north edge of (2, 2) leads out to (2, 1); a door kept on the
    outdoor square (3, 4) below the room on its north edge (a south-wall door; the scan reads no building there, fix
    round 1's R2: it is building 5's by its room) leads out from (3, 3) to (3, 4); an
    open door on the west edge of (3, 2), between the two room squares, with the wall to the north (blockN true) leads
    in; the same door closed is ambiguous (one edge out, one in) and is none; a door whose only edge leads to an
    unmapped or solid square, or that stands on no flagged edge, is none."""
    shut = {"open": False, "locked": False, "barricaded": False}
    opened = {"open": True, "locked": False, "barricaded": False}
    over = {}
    for x in (2, 3):
        for y in (2, 3):
            over[(x, y)] = {"room": "bedroom", "building": 5, "blockN": y == 2, "edgeN": y == 2,
                            "blockW": x == 2, "edgeW": x == 2}
    for y in (2, 3):
        over[(4, y)] = {"blockW": True, "edgeW": True}
    over[(2, 2)].update(door=shut, edgeW=False, blockW=False)                     # its west edge open floor here
    over[(1, 2)] = {"solid": True}
    over[(3, 4)] = {"door": shut, "blockN": True, "edgeN": True}   # the south-wall door, held outside, no building
    over[(3, 2)].update(door=opened, edgeW=True, blockW=False)                    # the room-to-room door, open
    w = _world(_grid(0, 0, 5, 5, over=over), me=(0.5, 0.5))
    assert w.door_way((2, 2, 0)) == ((2, 2, 0), (2, 1, 0))
    assert w.door_way((3, 4, 0)) == ((3, 3, 0), (3, 4, 0))
    assert w.door_building((3, 4, 0)) == 5 and (3, 4, 0) in w.doors_of(5) and (3, 4, 0) not in w.doors_of(None)
    assert w.door_way((3, 2, 0)) is None                                          # leads in: the bedroom's west
    over[(3, 2)].update(door=shut, blockW=True)
    w = _world(_grid(0, 0, 5, 5, over=over), me=(0.5, 0.5))
    assert w.door_way((3, 2, 0)) is None                                          # one edge out, one in
    over[(3, 2)].update(edgeW=False, blockW=False)
    w = _world(_grid(0, 0, 5, 5, over=over), me=(0.5, 0.5))
    assert w.door_way((3, 2, 0)) == ((3, 2, 0), (3, 1, 0))                        # its north edge alone: out
    w = _world([s for s in _grid(0, 0, 5, 5, over=over) if (s["x"], s["y"]) != (2, 1)], me=(0.5, 0.5))
    assert w.door_way((2, 2, 0)) is None                                          # unmapped across: none
    over[(2, 1)] = {"solid": True}
    w = _world(_grid(0, 0, 5, 5, over=over), me=(0.5, 0.5))
    assert w.door_way((2, 2, 0)) is None and w.door_way((2, 3, 0)) is None        # solid across; no door record
    over[(2, 2)].update(edgeN=False)
    w = _world(_grid(0, 0, 5, 5, over=over), me=(0.5, 0.5))
    assert w.door_way((2, 2, 0)) is None                                          # no flagged edge


def test_door_way_an_open_door_s_own_edge_leads_out_past_its_wall_and_a_south_wall_door_is_an_exit():
    """Amendment 5's finer reading: a room's corner square (2, 3) of building 5 with an open door on its west edge to
    the yard (blockW false) and its north edge a wall (blockN true) to the room square (2, 2): the door leads out
    west, the wall's room ignored (read without the open door's own edge it would be one edge out, one in). A
    south-wall door held outside (no building on its square, the live shape) is building 5's exit whose inner square
    is the room's (`night.exits`); with the room above it building 6's, it is building 6's door."""
    from agent.base.planner import night as N
    shut = {"open": False, "locked": False, "barricaded": False}
    opened = {"open": True, "locked": False, "barricaded": False}
    over = {}
    for x in (2, 3):
        for y in (2, 3):
            over[(x, y)] = {"room": "bedroom", "building": 5, "blockN": y == 2, "edgeN": y == 2,
                            "blockW": x == 2, "edgeW": x == 2}
    over[(2, 3)].update(door=opened, blockW=False, blockN=True, edgeN=True)
    over[(3, 4)] = {"door": shut, "blockN": True, "edgeN": True}
    w = _world(_grid(0, 0, 5, 5, over=over), me=(0.5, 0.5))
    assert w.door_way((2, 3, 0)) == ((2, 3, 0), (1, 3, 0))
    assert {"inner": (3, 3, 0), "outer": (3, 4, 0), "door": (3, 4, 0)} in N.exits(w, 5, 0)
    over[(3, 3)]["building"] = 6
    w = _world(_grid(0, 0, 5, 5, over=over), me=(0.5, 0.5))
    assert (3, 4, 0) in w.doors_of(6) and (3, 4, 0) not in w.doors_of(5) and N.exterior_doors(w, 6, 0) == [(3, 4, 0)]


# -- survival 4 (ruling P23-AP 1): the stuck pairs, the flood and the edge in the open --------------------------------
GATE = {"open": False, "locked": True, "barricaded": False}


def pocket():
    """A 13 x 13 yard: a fence row on the north edges of y 8 (x 0..12) with a locked gate at (5, 8), and a fence line
    on the west edges of x 8 from y 3 to y 7, so (5, 7) stands in a pocket open to the west and north (E4's square
    north of a locked gate, its targets south of the fence or east of the line)."""
    over = {(x, 8): {"blockN": True} for x in range(13)}
    over[(5, 8)] = {"blockN": True, "edgeN": True, "door": GATE}
    over.update({(8, y): {"blockW": True} for y in range(3, 8)})
    return _grid(0, 0, 12, 12, over=over)


def test_the_survival_4_world_constants():
    from agent.base import world as W
    assert (W.STUCK_AREA_N, W.REACH_LIMIT) == (2, 400)


def test_flood_honours_the_blocked_edges_the_locked_gate_and_its_limit():
    w = _world(pocket(), me=(5.5, 7.5))
    f = w.flood((5, 7, 0))
    assert (5, 7, 0) in f and (0, 7, 0) in f and (12, 0, 0) in f      # round the line's north end
    assert (5, 8, 0) not in f and (5, 12, 0) not in f and not any(sq[1] >= 8 for sq in f)
    assert w.reachable((5, 7, 0), (12, 2, 0)) and not w.reachable((5, 7, 0), (5, 9, 0))
    assert len(w.flood((5, 7, 0), limit=5)) == 5 and not w.reachable((5, 7, 0), (0, 7, 0), limit=5)
    assert w.flood((40, 40, 0)) == {(40, 40, 0)}                        # an unmapped start floods nothing more


def test_two_unmoved_stuck_walks_from_the_players_square_leave_only_edges_in_the_open():
    """The pocket: the nearest edge (5, 12) lies across the fence. One stuck pair keeps it; the second in a row from
    the player's square (`stuck_here`) answers the nearest edge whose straight line is clear, (0, 7), the line along
    row 7; a pair from a square two off restarts the run (fix round 1, M1: one touching it continues it),
    `clear_stuck_run` ends it, the player more than 1.0 tile from the square's centre or STUCK_TTL_MIN on reads it no
    more."""
    w = _world(pocket(), me=(5.5, 7.5))
    assert w.unexplored_edge() == (5, 12) and not w.stuck_here()
    w.mark_stuck_pair((5, 7), (6, 12))
    assert not w.stuck_here() and w.unexplored_edge() == (5, 12)
    w.mark_stuck_pair((5, 7), (7, 12))
    assert w.stuck_run["to"] == [(6, 12), (7, 12)] and w.stuck_here()
    assert w.unexplored_edge() == (0, 7) and w.line_clear((5.5, 7.5), (0.5, 7.5))
    assert not w.line_clear((5.5, 7.5), (5.5, 12.5))
    w.mark_stuck_pair((3, 7), (5, 12))
    assert w.stuck_run == {"from": (3, 7), "to": [(5, 12)], "at": w.world_minutes()} and not w.stuck_here()
    w.mark_stuck_pair((5, 7), (6, 12))
    w.mark_stuck_pair((5, 7), (7, 12))
    w.apply(frame(0, me=me_at(4.4, 7.5)))
    assert not w.stuck_here()                                           # 1.1 tiles off the square's centre
    w.apply(frame(0, me=me_at(5.5, 7.5), worldAge=8.0 + 60.0 / 60.0))
    assert not w.stuck_here()                                           # STUCK_TTL_MIN on
    w.apply(frame(0, me=me_at(5.5, 7.5)))
    w.mark_stuck_pair((5, 7), (6, 12))
    assert w.stuck_here()
    w.clear_stuck_run()
    assert w.stuck_run is None and not w.stuck_here() and w.unexplored_edge() == (5, 12)
    w.mark_stuck_pair((5, 7), (6, 12))
    assert "stuck_run" not in w.to_json() and "stuckRun" not in w.to_json()   # the planner's memory: goldens unmoved


def test_stuck_in_a_closed_pen_no_edge_is_answered():
    """Every edge's line crosses the pen's fence: none, so the goal source loots or scans."""
    over = {(x, y): {} for x in range(7) for y in range(7)}
    for x in range(2, 5):
        over[(x, 2)] = {"blockN": True}
        over[(x, 5)] = {"blockN": True}
    for y in range(2, 5):
        over[(2, y)] = dict(over.get((2, y), {}), blockW=True)
        over[(5, y)] = dict(over.get((5, y), {}), blockW=True)
    w = _world(_grid(0, 0, 6, 6, over=over), me=(3.5, 3.5))
    assert w.unexplored_edge() is not None
    w.mark_stuck_pair((3, 3), (0, 3))
    w.mark_stuck_pair((3, 3), (3, 0))
    assert w.stuck_here() and w.unexplored_edge() is None
    assert w.flood((3, 3, 0)) == {(x, y, 0) for x in range(2, 5) for y in range(2, 5)}


def test_stuck_an_edge_the_bounded_flood_never_reaches_is_not_answered():
    """A 31 x 31 open yard: every edge lies 15 tiles off, its line clear, but the flood stops at REACH_LIMIT squares
    (radius 9-10): no edge is reachable, so none is answered."""
    w = _world(_grid(0, 0, 30, 30), me=(15.5, 15.5))
    edge = w.unexplored_edge()
    assert edge is not None and w.line_clear((15.5, 15.5), (edge[0] + 0.5, edge[1] + 0.5))
    w.mark_stuck_pair((15, 15), (0, 15))
    w.mark_stuck_pair((15, 15), (30, 15))
    assert w.stuck_here() and len(w.flood((15, 15, 0))) == 400 and w.unexplored_edge() is None
    assert not w.reachable((15, 15, 0), edge + (0,)) and w.reachable((15, 15, 0), edge + (0,), limit=961)


def test_stuck_a_reachable_edge_whose_line_crosses_a_fence_is_not_answered():
    """The pocket with the yard run west to x -10: the nearest edge the flood reaches, (12, 7), lies round the north end
    of the x 8 fence line, its straight line across it; the answer is the nearest reached edge in the open, (5, 0)."""
    w = _world(_grid(-10, 0, -1, 12) + pocket(), me=(5.5, 7.5))
    w.mark_stuck_pair((5, 7), (5, 12))
    w.mark_stuck_pair((5, 7), (6, 12))
    assert w.reachable((5, 7, 0), (12, 7, 0)) and not w.line_clear((5.5, 7.5), (12.5, 7.5))
    assert w.unexplored_edge() == (5, 0)


def test_stuck_here_holds_through_a_half_tile_drift_across_the_squares_edge():
    """Fix round 1, M1: the player nudged half a tile west across (5, 7)'s edge, onto (4, 7): still stuck there, and a
    pair from (4, 7) continues the run from (5, 7)."""
    w = _world(pocket(), me=(5.5, 7.5))
    w.mark_stuck_pair((5, 7), (6, 12))
    w.apply(frame(0, me=me_at(4.9, 7.5)))
    w.mark_stuck_pair((4, 7), (7, 12))
    assert w.stuck_run["from"] == (5, 7) and len(w.stuck_run["to"]) == 2 and w.stuck_here()
    assert w.unexplored_edge() == (0, 7)


def test_stuck_after_stuck_walk_cap_walks_in_the_open_no_edge_is_answered():
    """Fix round 1, R2: past the two pairs that restrict the edge, STUCK_WALK_CAP (3) more in a row (walks in the open
    failing unmoved too): no edge, so the source loots or scans."""
    from agent.base import world as W
    assert W.STUCK_WALK_CAP == 3
    w = _world(pocket(), me=(5.5, 7.5))
    for i in range(W.STUCK_AREA_N + W.STUCK_WALK_CAP - 1):
        w.mark_stuck_pair((5, 7), (0, i))
    assert w.unexplored_edge() is not None
    w.mark_stuck_pair((5, 7), (1, 0))
    assert w.unexplored_edge() is None


# -- Plan 24 PZA/1.4 (ruling P24-C): a hoppable edge is crossable by a climb, for the flood and reachability only -------

def fence_row(hop=True):
    """A 5 x 5 yard with a fence on the north edges of y 2 (x 0..4): blocked, and hoppable when `hop`."""
    return _grid(0, 0, 4, 4, over={(x, 2): {"blockN": True, "edgeN": True, "hopN": hop} for x in range(5)})


def test_apply_keeps_the_hop_flags_on_the_square_record():
    w = _world([_sq(0, 0, blockN=True, hopN=True), _sq(1, 0, blockW=True, hopW=True)])
    assert (w.map[(0, 0, 0)]["hopN"], w.map[(0, 0, 0)]["hopW"]) == (True, False)
    assert (w.map[(1, 0, 0)]["hopN"], w.map[(1, 0, 0)]["hopW"]) == (False, True)


def test_blocked_with_climb_crosses_a_hoppable_edge_both_ways_and_nothing_else():
    w = _world(_grid(0, 0, 2, 2, over={(1, 1): {"blockN": True, "hopN": True}, (2, 1): {"blockW": True, "hopW": True},
                                       (0, 1): {"blockN": True}, (1, 2): {"blockN": True, "hopN": None}}))
    for a, b in (((1, 0, 0), (1, 1, 0)), ((1, 1, 0), (2, 1, 0))):     # (1,1)'s north edge, (2,1)'s west edge
        assert w.blocked(a, b) and w.blocked(b, a)                     # the default read: blocked, as isBlockedTo
        assert not w.blocked(a, b, climb=True) and not w.blocked(b, a, climb=True)
    assert w.blocked((0, 0, 0), (0, 1, 0), climb=True)                 # a wall: no hop flag
    assert w.blocked((1, 1, 0), (1, 2, 0), climb=True)                 # a null hop read is no climb
    assert w.blocked((0, 0, 0), (1, 1, 0), climb=True)                 # a diagonal never climbs: its corner edges hold
    assert not w.blocked((0, 0, 0), (0, 0, 0), climb=True)


def test_the_flood_and_reachable_cross_a_hoppable_fence_and_the_line_never_does():
    w = _world(fence_row(), me=(2.5, 0.5))
    assert w.reachable((2, 0, 0), (2, 4, 0)) and (0, 4, 0) in w.flood((2, 0, 0))
    assert not w.line_clear((2.5, 0.5), (2.5, 4.5))
    walled = _world(fence_row(hop=False), me=(2.5, 0.5))
    assert not walled.reachable((2, 0, 0), (2, 4, 0)) and not any(sq[1] >= 2 for sq in walled.flood((2, 0, 0)))


# -- Plan 24 survival 5 (ruling P24-A (a)): the met memory ------------------------------------------------------------

def test_the_met_memory_keeps_each_listed_zombie_for_met_ttl_min_and_drops_the_dead():
    from agent.base import world as W
    assert (W.MET_TTL_MIN, W.MET_R) == (10, 10.0)
    w = World()
    w.apply(frame(0, zombies=[zed(1, 3.0, 103.0, 200.0), zed(2, 5.0, 105.0, 200.0), zed(None, 2.0, 102.0, 200.0)],
                  worldAge=8.0))
    assert w.met == {1: (103.0, 200.0, 480.0), 2: (105.0, 200.0, 480.0)}   # an id-less zombie is never met
    w.apply(frame(60000, zombies=[zed(1, 3.0, 104.0, 200.0)], worldAge=8.0 + 5 / 60.0))
    assert w.met[1] == (104.0, 200.0, 485.0) and w.met[2] == (105.0, 200.0, 480.0)   # unlisted, still met
    assert 2 not in w.zombies                    # the World's own TTL is wall seconds, the memory's game minutes
    w.apply(frame(70000, worldAge=8.0 + 10 / 60.0))
    assert set(w.met) == {1, 2}                                # 10 minutes on: not older than MET_TTL_MIN
    w.apply(frame(80000, worldAge=8.0 + 10.5 / 60.0))
    assert set(w.met) == {1}
    w.apply({"kind": "event", "event": "zombie_dead", "id": 1, "seq": 2, "tick": 2, "wallMs": 80001})
    assert w.met == {}
    old = frame(90000, zombies=[zed(3, 1.0, 101.0, 200.0)])
    del old["worldAge"]
    w.apply(old)
    assert w.met == {} and w._gm0 is None                     # no worldAge: nothing met, the fallback untouched
    assert "met" not in json.loads(w.to_json())


def test_met_density_counts_the_distinct_zombies_met_within_r_and_the_window_is_the_densest():
    w = World()
    east = [zed(i, 0.0, 110.0 + 0.5 * i, 200.0) for i in range(1, 6)]           # five at 110.5..112.5
    w.apply(frame(0, zombies=east + [zed(9, 0.0, 100.0, 185.0)]))                 # one 15 tiles south
    w.apply(frame(1000, zombies=[zed(1, 0.0, 111.0, 200.0)]))                      # 1 moved: one id, one entry
    assert w.met_density(111.5, 200.0) == 5 and w.met_density(100.0, 185.0, r=1.0) == 1
    assert w.met_density(100.0, 200.0, r=5.0) == 0
    cx, cy, n = w.met_window()
    assert n == 5 and cx == pytest.approx((111.0 + 111.0 + 111.5 + 112.0 + 112.5) / 5) and cy == 200.0
    assert World().met_window() is None
