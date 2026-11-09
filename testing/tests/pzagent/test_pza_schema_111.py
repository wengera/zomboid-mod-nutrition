"""PZA/1.11 (Plan 32 Task 1, the spec `2026-11-08-plan-32-the-facing-design.md` section 4.1): the facing ring in the
frame's me (fwdAngle, twist, aimAngle, appended after bodyAngle; autoWalk is me's own field since PZA/1) and the act
type probe with its args (the probeMode enum), its step result and its result; the hello's mod 1.11; a PZA/1.10 frame
decoding with the three fields None."""
import dataclasses
import json
import os
import random

import pytest

from agent.base import pza1
from .conftest import ROOT, lua_file
from .test_pza1 import lua_frame, rand_frame

SCHEMA = os.path.join(ROOT, "testing", "agent", "base", "schema", "pza1.json")
MODES = ("read", "snap_aimed", "unaimed_face", "unaimed_snap", "block_aim", "ignore_aim", "turn_k")
STEP = {"step", "tick", "b", "fwd", "body", "look", "twist", "aim", "aiming", "forceAim", "autoWalk", "err_body",
        "err_look"}
RESULT = {"ticks", "mode", "err_body_med", "err_body_p90", "err_look_med", "err_look_p90", "hold30", "aiming_share",
          "pressed", "press", "missing"}


def defs():
    with open(SCHEMA, encoding="utf-8") as fh:
        return json.load(fh)["$defs"]


@pytest.fixture
def lua_schema(lua):
    with open(lua_file("shared/PZAgent_Schema.lua"), encoding="utf-8") as fh:
        lua.execute(fh.read())
    return lua


def test_the_hello_s_mod_reads_1_11(lua):
    assert lua.eval("PZA.VERSION") == "1.11"
    assert "PZA/1.11" in json.load(open(SCHEMA, encoding="utf-8"))["description"]


def test_me_appends_the_facing_ring_after_body_angle():
    d = defs()["me"]
    assert pza1.GROUPS["me"][-5:] == ("lookAngle", "bodyAngle", "fwdAngle", "twist", "aimAngle")
    assert pza1.PRIOR["me"] == 11 and pza1.GROUPS["me"].count("autoWalk") == 1
    for k, member in (("fwdAngle", "getDirectionAngleRadians()"), ("twist", "getTwist()"),
                      ("aimAngle", "getAimVector")):
        assert d["properties"][k]["type"] == "number" and member in d["properties"][k]["description"], k
        assert "before PZA/1.11" in d["properties"][k]["description"], k


def test_a_1_10_frame_decodes_with_the_three_fields_none():
    f = rand_frame(random.Random(111))
    f["me"].update(fwdAngle=0.5, twist=-12.5, aimAngle=None)
    arr = json.loads(pza1.encode("frame", f))
    me = pza1.ORDER["frame"].index("me")
    assert arr[me][-3:] == [0.5, -12.5, None] and pza1.decode(arr) == f
    arr[me] = arr[me][:25]                                       # a PZA/1.10 me
    m = pza1.decode(arr)["me"]
    assert (m["fwdAngle"], m["twist"], m["aimAngle"]) == (None, None, None)
    assert m["bodyAngle"] == f["me"]["bodyAngle"] and m["autoWalk"] == f["me"]["autoWalk"]


def test_the_lua_encoder_writes_the_1_11_fields_as_python_does(lua_schema):
    f = rand_frame(random.Random(112), 4)
    f["me"].update(x=1.5, y=2.5, pace=0.5, fwdAngle=-0.75, twist=22.5, aimAngle=3.0)
    assert json.loads(lua_frame(lua_schema, f)) == json.loads(pza1.encode("frame", f))


def test_probe_is_an_action_type_with_its_eight_args_in_order():
    assert pza1.ACTION_TYPES[-1] == "probe"
    assert list(pza1.ACTION_ARGS["probe"].items()) == [
        ("mode", "probeMode"), ("targetId", "int"), ("x", "float"), ("y", "float"), ("ticks", "int"), ("k", "float"),
        ("vx", "float"), ("vy", "float")]
    assert pza1.PROBE_MODES == MODES and pza1._ENUMS["probeMode"] == MODES
    assert defs()["args_probe"]["required"] == ["mode"] and defs()["args_probe"]["additionalProperties"] is False


def test_the_probe_dataclass_defaults_and_its_mode_check():
    c = pza1.Probe("read")
    assert c.TYPE == "probe" and c.args() == {"mode": "read", "targetId": -1, "x": -1.0, "y": -1.0, "ticks": 60,
                                              "k": -1.0, "vx": 0.0, "vy": 0.0}
    assert [f.name for f in dataclasses.fields(c)] == list(pza1.ACTION_ARGS["probe"])
    with pytest.raises(ValueError):
        pza1.Probe("kick")


def test_the_lua_schema_carries_the_probe_modes_and_the_type(lua_schema):
    assert sorted(lua_schema.eval("PZA.schema.probeModes").keys()) == sorted(MODES)
    assert list(lua_schema.eval("PZA.schema.actions.probe").values()) == list(pza1.ACTION_ARGS["probe"])


def test_the_probe_s_step_result_and_result_keys():
    d = defs()
    assert set(d["result_probe_step"]["properties"]) == STEP
    assert set(d["result_probe"]["properties"]) == RESULT
    assert set(d["result_probe"]["properties"]["press"]["properties"]) == {"d_press", "look_off", "hp0", "hp1",
                                                                            "cut_by"}
    assert d["result_probe"]["x-type"] == "probe" and "x-role" not in d["result_probe_step"]


def test_a_probe_act_line_round_trips():
    body = {"kind": "act", "seq": 3, "tick": 1, "wallMs": 2, "aid": "a1", "type": "probe", "state": "progress",
            "reason": "", "result": {"step": 2, "tick": 41, "b": 0.5, "fwd": 0.25, "body": 0.125, "look": 0.5,
                                     "twist": 3.5, "aiming": True, "forceAim": True, "autoWalk": False,
                                     "err_body": -21.5, "err_look": 0.0}}
    assert pza1.decode(json.loads(pza1.encode("act", body))) == body
