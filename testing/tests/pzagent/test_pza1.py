"""The generated PZA/1 module (testing/agent/base/pza1.py, Plan 22 Task 1) and its Lua twin PZAgent_Schema.lua:
round trips on the Python side, and the one-schema-two-hosts check that the Lua encoder writes what Python encodes."""
import dataclasses
import json
import os
import random

import pytest

from agent.base import pza1
from .conftest import lua_file

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCHEMA = os.path.join(ROOT, "testing", "agent", "base", "schema", "pza1.json")


def lua_float(rng, lo=-1000.0, hi=1000.0):
    """A float as the Lua 5.1 host renders it (%.14g), so the round trip is exact."""
    return float("%.14g" % rng.uniform(lo, hi))


def maybe(rng, v, p=0.1):
    return None if rng.random() < p else v


def rand_frame(rng, seq=1):
    def b():
        return rng.random() < 0.5
    zombies = [{"id": rng.randrange(1, 9999), "x": lua_float(rng), "y": lua_float(rng), "dist": lua_float(rng, 0, 30),
                "hasTarget": b(), "crawler": b(), "health": maybe(rng, lua_float(rng, 0, 2))}
               for _ in range(rng.choice([0, 0, 1, 2, 5]))]
    parts = [{"i": i, "h": lua_float(rng, 0, 100)} for i in rng.sample(range(17), rng.choice([0, 1, 3]))]
    return {
        "kind": "frame", "seq": seq, "tick": rng.randrange(0, 10 ** 6), "wallMs": rng.randrange(10 ** 12, 2 * 10 ** 12),
        "gameMin": lua_float(rng, 0, 10 ** 5), "worldAge": maybe(rng, lua_float(rng, 0, 1000)),
        "me": {"x": lua_float(rng), "y": lua_float(rng), "z": rng.randrange(0, 3), "dir": rng.choice(["N", "SE", "W"]),
               "pace": lua_float(rng, 0, 6), "moving": b(), "running": b(), "sprinting": b(), "forceRun": b(),
               "forceSprint": b(), "autoWalk": maybe(rng, b()), "zombiesSeen": rng.randrange(0, 200),
               "zombiesListed": rng.randrange(0, 6), "hour": maybe(rng, lua_float(rng, 0, 24))},
        "stats": {k: lua_float(rng, 0, 1) for k in pza1.GROUPS["stats"]},
        "body": {"health": lua_float(rng, 0, 100), "bleeding": rng.randrange(0, 3), "scratched": rng.randrange(0, 3),
                 "bitten": 0, "parts": parts},
        "load": {"weight": lua_float(rng, 0, 30), "max": 12, "level": rng.randrange(0, 4), "n": rng.randrange(0, 40)},
        "weapon": maybe(rng, {"type": "Base.Axe", "cond": rng.randrange(0, 10), "reach": lua_float(rng, 0, 2),
                              "ammo": maybe(rng, rng.randrange(0, 15), 0.5)}, 0.3),
        "action": maybe(rng, {"class": "ISWalkToTimedAction", "n": rng.randrange(1, 4)}, 0.5),
        "act": maybe(rng, {"aid": "a%s" % rng.randrange(100), "state": rng.choice(pza1.ACT_STATES)}, 0.5),
        "zombies": rng.choice([zombies, zombies, None]) if not zombies else zombies,
        "cost": {"tickMs": lua_float(rng, 0, 5), "actMs": lua_float(rng, 0, 1), "senseMs": lua_float(rng, 0, 1),
                 "mapMs": lua_float(rng, 0, 1), "linkMs": lua_float(rng, 0, 1), "tickMaxMs": lua_float(rng, 0, 9),
                 "over5": rng.randrange(0, 4), "dropped": 0, "pollMs": lua_float(rng, 0, 1),
                 "startMs": lua_float(rng, 0, 9), "maxActMs": lua_float(rng, 0, 9), "maxSenseMs": lua_float(rng, 0, 3),
                 "maxMapMs": lua_float(rng, 0, 3), "maxLinkMs": lua_float(rng, 0, 3), "maxPollMs": lua_float(rng, 0, 1),
                 "maxStartMs": lua_float(rng, 0, 9)},
    }


def rand_square(rng):
    def b():
        return rng.random() < 0.5

    def portal():
        return {"open": b(), "locked": b(), "barricaded": b()}
    return {"x": rng.randrange(0, 20000), "y": rng.randrange(0, 20000), "z": rng.randrange(0, 3), "solid": b(),
            "solidTrans": b(), "light": lua_float(rng, 0, 1), "room": maybe(rng, "kitchen", 0.5),
            "building": maybe(rng, rng.randrange(1, 500), 0.5), "door": maybe(rng, portal(), 0.7),
            "window": maybe(rng, portal(), 0.7),
            "containers": [{"type": rng.choice(["fridge", "counter"]), "n": 2, "items": ["Base.Apple", "Base.Water"]}
                           for _ in range(rng.choice([0, 0, 1, 2]))],
            "floor": rng.choice([[], ["Base.Plank"], ["Base.Axe", "Base.Nails"]]),
            "blockN": b(), "blockW": b(), "edgeN": b(), "edgeW": b()}


def rand_map(rng, seq=1):
    return {"kind": "map", "seq": seq, "tick": rng.randrange(0, 10 ** 6), "wallMs": rng.randrange(10 ** 12, 2 * 10 ** 12),
            "mode": rng.choice(["full", "delta"]), "scanId": rng.randrange(1, 50), "part": 1, "parts": 3,
            "squares": [rand_square(rng) for _ in range(rng.randrange(0, 41))],
            "missing": rng.choice([[], ["getModData"], ["getContainerCount", "getWindow"]])}


def test_frame_round_trips_over_200_random_frames():
    rng = random.Random(22)
    for i in range(200):
        f = rand_frame(rng, i)
        line = pza1.encode("frame", f)
        assert line.startswith('["frame",')
        assert pza1.decode(json.loads(line)) == f


def test_map_round_trips_with_0_to_40_squares():
    rng = random.Random(23)
    sizes = set()
    for i in range(200):
        m = rand_map(rng, i)
        sizes.add(len(m["squares"]))
        line = pza1.encode("map", m)
        assert line.startswith('["map",')
        assert pza1.decode(json.loads(line)) == m
    assert 0 in sizes and max(sizes) >= 35


def test_an_elided_group_is_true_and_merge_delta_restores_it():
    rng = random.Random(24)
    base = rand_frame(rng, 1)
    f = dict(rand_frame(rng, 2), stats=base["stats"], cost=base["cost"])
    arr = json.loads(pza1.encode("frame", f, same=("stats", "cost")))
    assert arr[pza1.ORDER["frame"].index("stats")] is True and arr[pza1.ORDER["frame"].index("cost")] is True
    d = pza1.decode(arr)
    assert d["stats"] is pza1.SAME and d["cost"] is pza1.SAME and d["me"] == f["me"]
    assert pza1.merge_delta(d, base) == f
    with pytest.raises(ValueError):
        pza1.merge_delta(d, d)                               # a base that elides the group itself


def test_same_names_groups_only():
    rng = random.Random(25)
    with pytest.raises(ValueError):
        pza1.encode("frame", rand_frame(rng), same=("zombies",))
    with pytest.raises(ValueError):
        pza1.encode("map", rand_map(rng), same=("squares",))


def test_decode_refuses_a_wrong_arity_and_an_unknown_kind():
    rng = random.Random(26)
    arr = json.loads(pza1.encode("frame", rand_frame(rng)))
    with pytest.raises(ValueError):
        pza1.decode(arr[:-1])
    with pytest.raises(ValueError):
        pza1.decode(arr + [0])
    bad = list(arr)
    me = pza1.ORDER["frame"].index("me")
    bad[me] = bad[me][:pza1.PRIOR["me"] - 1]                  # shorter than any writer wrote (PZA/1.1)
    with pytest.raises(ValueError):
        pza1.decode(bad)
    m = json.loads(pza1.encode("map", dict(rand_map(rng), squares=[rand_square(rng)])))
    sq = pza1.ORDER["map"].index("squares")
    m[sq][0] = m[sq][0] + [1]
    with pytest.raises(ValueError):
        pza1.decode(m)
    with pytest.raises(ValueError):
        pza1.decode(["ghost", 1, 2, 3])
    with pytest.raises(ValueError):
        pza1.decode({"kind": "ghost"})
    with pytest.raises(ValueError):
        pza1.decode({"kind": "frame"})                       # a positional kind never travels keyed


def test_a_keyed_act_round_trips():
    act = {"kind": "act", "seq": 41, "tick": 900, "wallMs": 1761550000123, "aid": "a7", "type": "attack", "state": "done", "reason": "",
           "result": {"swings": 3, "attackStarted": True, "meleeDelay": 0.5, "targetDead": True},
           "snapshot": {"me": {"x": 1.5, "y": 2.25, "z": 0, "health": 88.5}, "nearest": None}}
    line = pza1.encode("act", act)
    assert json.loads(line) == act
    assert line == json.dumps(act, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert pza1.decode(json.loads(line)) == act
    ev = {"kind": "event", "seq": 42, "tick": 901, "wallMs": 1761550000140, "event": "damage", "gameMin": 123.5, "tag": "HEAVYLOAD", "amount": 0.39, "side": "client"}
    assert pza1.decode(json.loads(pza1.encode("event", ev))) == ev


def test_every_keyed_kind_requires_the_envelope():
    act = {"kind": "act", "seq": 7, "tick": 120, "wallMs": 1761550000500, "aid": "a1", "type": "stop", "state": "done",
           "reason": "", "result": {}, "snapshot": {"me": {"x": 1, "y": 2, "z": 0, "health": 100}, "nearest": None}}
    assert pza1.decode(act) == act
    for k in pza1.KINDS:
        assert pza1.ORDER[k][:4] == pza1.ENVELOPE, k
    for f in pza1.ENVELOPE[1:]:
        bare = {k: v for k, v in act.items() if k != f}
        with pytest.raises(ValueError):
            pza1.decode(bare)
        with pytest.raises(ValueError):
            pza1.encode("act", bare)
    for kind, body in (("hello", {"proto": "PZA/1", "mod": "0.3", "build": "42.21.0", "user": "admin", "rate": 5,
                                  "caps": list(pza1.ACTION_TYPES), "mode": "append"}),
                       ("reply", {"to": 3, "body": {}}),
                       ("event", {"event": "overflow", "gameMin": 1.5, "queued": 4, "cut": 2})):
        line = dict(body, kind=kind, seq=1, tick=2, wallMs=3)
        assert pza1.decode(json.loads(pza1.encode(kind, line))) == line
        with pytest.raises(ValueError):
            pza1.decode(dict(body, kind=kind))


def test_the_constants():
    assert pza1.PROTO == "PZA/1"
    assert pza1.KINDS == ("hello", "frame", "map", "event", "act", "reply")
    assert pza1.POSITIONAL == ("frame", "map")
    for k in pza1.POSITIONAL:
        assert pza1.ORDER[k][:4] == ("kind", "seq", "tick", "wallMs")
    for k in pza1.KINDS:
        assert pza1.ORDER[k][0] == "kind"
    assert set(pza1.GROUPS) == {"me", "stats", "body", "load", "weapon", "action", "act", "cost"}
    assert set(pza1.RECORDS) == {"zombie", "part", "square", "container", "portal"}
    assert pza1.GAITS == ("walk", "run", "sprint")
    assert pza1.ACTION_TYPES == ("walkTo", "steer", "attack", "interact", "equip", "consume", "drop", "stop", "scan", "rate",
                                 "sleep")
    assert pza1.ACTION_ARGS["interact"]["filter"] == "filter"
    assert pza1.ACTION_ARGS["interact"]["maxWeight"] == "float" and pza1.ACTION_ARGS["sleep"] == {}
    assert pza1.ACTION_ARGS["interact"]["kind"] == "ikind"
    assert pza1.ACTION_ARGS["walkTo"] == {"x": "float", "y": "float", "gait": "gait"}
    assert pza1.ACTION_ARGS["scan"] == {"r": "int"} and pza1.ACTION_ARGS["stop"] == {}
    assert "damage" in pza1.EVENT_KINDS and "overflow" in pza1.EVENT_KINDS


def test_every_reason_is_a_string_in_the_schemas_enum():
    enum = json.load(open(SCHEMA, encoding="utf-8"))["$defs"]["reason"]["enum"]
    assert isinstance(pza1.REASONS, frozenset) and pza1.REASONS == frozenset(enum)
    assert all(isinstance(r, str) for r in pza1.REASONS) and len(enum) == 22
    assert "not safe" in pza1.REASONS and "not allowed" in pza1.REASONS


def test_the_command_dataclasses():
    assert pza1.WalkTo(1, 2).args() == {"x": 1, "y": 2, "gait": "walk"}
    assert pza1.WalkTo.TYPE == "walkTo"
    assert pza1.Steer(1.0, 0.0, 2.5, "run").args() == {"vx": 1.0, "vy": 0.0, "seconds": 2.5, "gait": "run"}
    assert pza1.Interact(3, 4, "loot").args() == {"x": 3, "y": 4, "kind": "loot", "filter": "all", "maxWeight": 0.0}
    assert pza1.Interact(1, 2, "loot", "food").args() == {"x": 1, "y": 2, "kind": "loot", "filter": "food",
                                                         "maxWeight": 0.0}
    assert pza1.Interact(1, 2, "loot", "food", 12.5).args()["maxWeight"] == 12.5
    assert type(pza1.Interact(1, 2, "loot").maxWeight) is float
    assert pza1.Stop().args() == {} and pza1.Stop.TYPE == "stop"
    assert pza1.Sleep().args() == {} and pza1.Sleep.TYPE == "sleep"
    assert pza1.Rate(5).args() == {"hz": 5} and pza1.Scan(8).TYPE == "scan"
    classes = (pza1.WalkTo, pza1.Steer, pza1.Attack, pza1.Interact, pza1.Equip, pza1.Consume, pza1.Drop, pza1.Stop,
               pza1.Scan, pza1.Rate, pza1.Sleep)
    assert tuple(c.TYPE for c in classes) == pza1.ACTION_TYPES
    for c in classes:
        assert tuple(f.name for f in dataclasses.fields(c)) == tuple(pza1.ACTION_ARGS[c.TYPE])


# ---- one schema, two hosts: the Lua encoder against the Python one ----------------------------------------------

def lua_lit(v):
    """A Python value as a Lua literal (no proxies): a None in a dict is an absent key, so nil."""
    if v is None:
        return "nil"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(v, list):
        return "{" + ", ".join(lua_lit(x) for x in v) + "}"
    if isinstance(v, dict):
        return "{" + ", ".join("[%s] = %s" % (lua_lit(k), lua_lit(x)) for k, x in v.items() if x is not None) + "}"
    raise TypeError(v)


@pytest.fixture
def lua_schema(lua):
    with open(lua_file("shared/PZAgent_Schema.lua"), encoding="utf-8") as fh:
        lua.execute(fh.read())
    return lua


def lua_frame(L, f, same=()):
    L.execute("_body = " + lua_lit(f))
    L.execute("_same = " + lua_lit({g: True for g in same}))
    return L.eval("PZA.enc.frame(_body, _same)")


def test_the_lua_frame_encoder_writes_what_python_encodes(lua_schema):
    rng = random.Random(27)
    f = rand_frame(rng, 9)
    f.update(seq=9, tick=1234, wallMs=1761550000123, gameMin=4321.25, worldAge=31.5)
    f["me"].update(x=10.5, y=-20.125, z=0, pace=3.71, autoWalk=False)
    f["load"].update(weight=19.555, max=12, level=3, n=37)
    f["weapon"] = {"type": "Base.Axe", "cond": 7, "reach": 1.45, "ammo": None}          # a nil field in weapon
    f["action"] = {"class": 'IS"Walk\\To', "n": 2}                                       # a quote and a backslash
    f["zombies"] = [{"id": 11, "x": 12.5, "y": 13.0, "dist": 2.5, "hasTarget": True, "crawler": False, "health": 0.75},
                    {"id": 12, "x": 14.25, "y": 9.0, "dist": 4.0, "hasTarget": False, "crawler": True, "health": 1.0}]
    py = pza1.encode("frame", f)
    out = lua_frame(lua_schema, f)
    assert json.loads(out) == json.loads(py)
    assert out == py                                        # the same bytes, for these values
    assert json.loads(out)[pza1.ORDER["frame"].index("weapon")][3] is None

    f["zombies"] = []
    f["weapon"] = None                                      # the group null
    assert json.loads(lua_frame(lua_schema, f)) == json.loads(pza1.encode("frame", f))
    same = ("stats", "cost", "weapon")
    out = lua_frame(lua_schema, f, same)
    assert json.loads(out) == json.loads(pza1.encode("frame", f, same=same))
    assert pza1.merge_delta(pza1.decode(json.loads(out)), f) == f

    rng = random.Random(28)
    for i in range(50):
        g = rand_frame(rng, i)
        assert json.loads(lua_frame(lua_schema, g)) == json.loads(pza1.encode("frame", g)), i


def test_the_lua_map_encoder_writes_what_python_encodes(lua_schema):
    m = {"kind": "map", "seq": 3, "tick": 77, "wallMs": 1761550000999, "mode": "full", "scanId": 2, "part": 1,
         "parts": 1, "missing": ["getWindow", 'odd"name\\'],
         "squares": [
             {"x": 100, "y": 200, "z": 0, "solid": False, "solidTrans": False, "light": 0.8, "room": "kitchen",
              "building": 12, "door": {"open": False, "locked": True, "barricaded": False}, "window": None,
              "containers": [{"type": "fridge", "n": 2, "items": ["Base.Apple", "Base.WaterBottle"]}], "floor": [],
              "blockN": True, "blockW": False, "edgeN": True, "edgeW": False},
             {"x": 101, "y": 200, "z": 0, "solid": True, "solidTrans": False, "light": 0.25, "room": None,
              "building": None, "door": None, "window": None, "containers": [], "floor": ["Base.Plank"],
              "blockN": False, "blockW": True, "edgeN": False, "edgeW": True}]}
    L = lua_schema
    L.execute("_body = " + lua_lit(m))
    out = L.eval("PZA.enc.map(_body)")
    assert json.loads(out) == json.loads(pza1.encode("map", m))
    assert pza1.decode(json.loads(out)) == m
    # Task 6's watch compares one square's encoding with the one it last sent
    L.execute("_sq = " + lua_lit(m["squares"][0]))
    assert json.loads(L.eval("PZA.enc.square(_sq)")) == json.loads(pza1.encode("map", m))[pza1.ORDER["map"].index("squares")][0]


def test_the_lua_value_rule_is_core_json(lua_schema):
    L = lua_schema
    for lit in ("nil", "true", "false", "0", "-3", "1.5", "1e15", "123456789012", "0/0", "1/0", "-1/0", "0.1",
                "'a\"b\\\\c\\n'"):
        assert L.eval("PZA.enc.v(%s)" % lit) == L.eval("PZA.json(%s)" % lit), lit


def test_the_lua_schema_tables(lua_schema):
    L = lua_schema
    assert L.eval("PZA.schema.PROTO") == "PZA/1"
    assert L.eval("PZA.schema.reasons['bad args']") is True
    assert L.eval("PZA.schema.reasons['ghost']") is None
    assert L.eval("table.concat(PZA.schema.actions.walkTo, ',')") == "x,y,gait"
    assert L.eval("table.concat(PZA.schema.order.frame, ',')") == ",".join(pza1.ORDER["frame"])
    assert L.eval("table.concat(PZA.schema.groups.me, ',')") == ",".join(pza1.GROUPS["me"])
    assert L.eval("table.concat(PZA.schema.records.square, ',')") == ",".join(pza1.RECORDS["square"])
    assert L.eval("PZA.schema.gaits.sprint") is True
    assert L.eval("table.concat(PZA.schema.events.damage, ',')") == "tag,amount,side"


# ---- the descriptions the fix wave corrected (M3): what Main writes ----------------------------------------------

COST = {
    "tickMs": "The previous tick's whole body in ms (a single tick on the 1 ms clock).",
    "actMs": "This tick's skill tick in ms (a single tick).",
    "senseMs": "This tick's events and frame read in ms (a single tick).",
    "mapMs": "This tick's scan or watch step in ms (a single tick).",
    "linkMs": "The previous tick's flush in ms.",
    "tickMaxMs": "The worst body since the last frame, in ms.",
    "over5": "The bodies of 5 ms or more since the last frame.",
    "dropped": "The number of lines dropped.",
    "pollMs": "This tick's command poll in ms, the ack write included (a single tick).",
    "startMs": "This tick's command start in ms, Main's scan or rate answer or the runner's start (a single tick).",
    "maxActMs": "The worst skill tick since the last frame, in ms.",
    "maxSenseMs": "The worst events and frame read since the last frame, in ms.",
    "maxMapMs": "The worst scan or watch step since the last frame, in ms.",
    "maxLinkMs": "The worst flush since the last frame, in ms.",
    "maxPollMs": "The worst command poll since the last frame, in ms.",
    "maxStartMs": "The worst command start since the last frame, in ms.",
}


def test_the_cost_descriptions_name_single_tick_spans_never_a_mean():
    with open(SCHEMA, encoding="utf-8") as fh:
        props = json.load(fh)["$defs"]["cost"]["properties"]
    assert {k: v["description"] for k, v in props.items()} == COST


# ---- (M4): what attack does, before any LLM reads it ------------------------------------------------------------

TOOLS = os.path.join(ROOT, "testing", "agent", "base", "schema", "tools.json")
ATTACK = ("One swing at the target: done when the swing ends; read `result.attackStarted` and the target's health in the "
          "next frame; a target out of reach is approached first within the skill's budget, else `out of reach`.")


def test_the_attack_description_is_one_swing_in_the_schema_the_tools_and_the_module():
    with open(SCHEMA, encoding="utf-8") as fh:
        assert json.load(fh)["$defs"]["args_attack"]["description"] == ATTACK
    with open(TOOLS, encoding="utf-8") as fh:
        tool = [t for t in json.load(fh) if t["name"] == "attack"]
    assert len(tool) == 1 and tool[0]["description"] == ATTACK
    assert ATTACK in open(os.path.join(ROOT, "testing", "agent", "base", "pza1.py"), encoding="utf-8").read()


# ---- X4 fix pass 1: the fields appended to me and cost, and a line written before them -------------------------------

def test_me_and_cost_append_their_new_fields_after_the_prior_prefix():
    assert pza1.GROUPS["me"][11:] == ("zombiesSeen", "zombiesListed", "hour")
    assert pza1.GROUPS["cost"][8:] == ("pollMs", "startMs", "maxActMs", "maxSenseMs", "maxMapMs", "maxLinkMs",
                                       "maxPollMs", "maxStartMs")
    assert pza1.PRIOR == {"me": 11, "cost": 8, "square": 12}


def test_a_frame_written_before_the_append_decodes_with_the_new_fields_none_and_no_shorter_or_longer_one_does():
    """X4 fix pass 1b (PZA/1.1): a group array from its x-prior arity up to its order decodes, the trailing fields
    None; below x-prior or past the order it is refused."""
    rng = random.Random(29)
    arr = json.loads(pza1.encode("frame", rand_frame(rng)))
    me, cost = pza1.ORDER["frame"].index("me"), pza1.ORDER["frame"].index("cost")
    old = list(arr)
    old[me], old[cost] = arr[me][:11], arr[cost][:8]
    d = pza1.decode(old)
    assert list(d["me"]) == list(pza1.GROUPS["me"]) and list(d["cost"]) == list(pza1.GROUPS["cost"])
    assert d["me"]["zombiesSeen"] is None and d["me"]["zombiesListed"] is None and d["me"]["x"] == arr[me][0]
    assert all(d["cost"][k] is None for k in pza1.GROUPS["cost"][8:]) and d["cost"]["tickMs"] == arr[cost][0]
    for g, n in (("me", 12), ("me", 13), ("cost", 9), ("cost", 15)):
        ok = list(arr)
        i = pza1.ORDER["frame"].index(g)
        ok[i] = arr[i][:n]
        assert pza1.decode(ok)[g][pza1.GROUPS[g][n]] is None
    for g, n in (("me", 10), ("me", 15), ("cost", 7), ("cost", 17)):
        bad = list(arr)
        i = pza1.ORDER["frame"].index(g)
        bad[i] = (arr[i] + [0] * n)[:n]
        with pytest.raises(ValueError):
            pza1.decode(bad)


# ---- X4 fix pass fix 1 (ruling S-32, review M-1): the scan_dropped event and the door event's reach ------------------

def test_scan_dropped_is_an_event_kind_with_its_fields_and_round_trips():
    assert "scan_dropped" in pza1.EVENT_KINDS
    assert pza1.EVENT_FIELDS["scan_dropped"] == ("scanId", "aid", "part", "parts", "reason")
    body = {"seq": 4, "tick": 9, "wallMs": 1, "event": "scan_dropped", "gameMin": 480.0, "scanId": 2, "aid": "a3",
            "part": 2, "parts": 3, "reason": "java raised"}
    assert pza1.decode(json.loads(pza1.encode("event", body))) == dict(body, kind="event")
    props = json.load(open(SCHEMA, encoding="utf-8"))["$defs"]["event_scan_dropped"]["properties"]
    assert [props[f]["type"] for f in ("scanId", "aid", "part", "parts", "reason")] == [
        "integer", "string", "integer", "integer", "string"]


def test_the_door_event_names_the_watchs_ring_and_its_lag():
    d = json.load(open(SCHEMA, encoding="utf-8"))["$defs"]["event_door"]["description"]
    assert "6-tile ring" in d and "2.3 s" in d and "10 Hz" in d


# ---- Plan 23 Task 4: PZA/1.2 --------------------------------------------------------------------------------------

def test_the_fake_mods_square_helper_is_a_full_square_with_its_edges_false():
    from .fakemod import DEFAULT_FRAME, square
    sq = square(x=3, blockN=True)
    assert tuple(sq) == pza1.RECORDS["square"] and sq["x"] == 3 and sq["blockN"] is True
    assert (sq["blockW"], sq["edgeN"], sq["edgeW"]) == (False, False, False)
    m = {"kind": "map", "seq": 1, "tick": 0, "wallMs": 0, "mode": "full", "scanId": 1, "part": 1, "parts": 1,
         "squares": [sq], "missing": []}
    assert pza1.decode(json.loads(pza1.encode("map", m))) == m
    with pytest.raises(ValueError):
        square(ghost=1)
    assert DEFAULT_FRAME["me"]["hour"] == 8.0 and tuple(DEFAULT_FRAME["me"]) == pza1.GROUPS["me"]


# ---- PZA/1.3: the death event (ruling P23-AO) -----------------------------------------------------------------------

def test_death_is_an_event_kind_with_its_fields_and_round_trips():
    assert "death" in pza1.EVENT_KINDS
    assert pza1.EVENT_FIELDS["death"] == ("worldAge", "x", "y", "z", "health", "via", "zombiesKilled")   # optional last
    body = {"seq": 4251, "tick": 90000, "wallMs": 1, "event": "death", "gameMin": 627.0, "worldAge": 10.45,
            "x": 10770.67, "y": 10640.48, "z": 0, "health": 19.506973266601562, "zombiesKilled": 1, "via": "hook"}
    assert pza1.decode(json.loads(pza1.encode("event", body))) == dict(body, kind="event")
    props = json.load(open(SCHEMA, encoding="utf-8"))["$defs"]["event_death"]["properties"]
    assert [props[f]["type"] for f in pza1.EVENT_FIELDS["death"]] == [
        "number", "number", "number", "number", "number", "string", "integer"]
    req = json.load(open(SCHEMA, encoding="utf-8"))["$defs"]["event_death"]["required"]
    assert "zombiesKilled" not in req and set(req) == set(pza1.EVENT_FIELDS["death"]) - {"zombiesKilled"}  # review M2
    body.pop("zombiesKilled")                                    # an unread kill count: the key absent
    assert pza1.decode(json.loads(pza1.encode("event", body))) == dict(body, kind="event")
