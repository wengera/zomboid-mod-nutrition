import json
import pytest
from lupa import LuaRuntime
import lupa.lua51 as lua51
from .conftest import lua_file, make_lua


@pytest.fixture
def lua55(fs):
    """The Lua 5.5 host, for the number rendering only: Kahlua's tostring is Java's Double.toString, which
    round-trips a double the way 5.5's tostring does; the 5.1 host's %.14g is the less faithful one there."""
    return make_lua(fs, LuaRuntime)


def py(v):
    """A Lua value as Python: a table with keys 1..n is a list (an empty table an empty dict), any other a dict."""
    if lua51.lua_type(v) != "table":
        return v
    keys = list(v.keys())
    if keys and all(isinstance(k, int) for k in keys) and sorted(keys) == list(range(1, len(keys) + 1)):
        return [py(v[i]) for i in range(1, len(keys) + 1)]
    return {k: py(v[k]) for k in keys}


def decode(lua, s):
    lua.globals()._s = s
    return lua.eval("PZA.decode(_s)")


def test_call_guard_nil_obj_and_missing_member(lua):
    ok, v = lua.eval("PZA.call(nil, 'getX')")
    assert ok is False
    obj = lua.eval("{getX = function(self) return 7 end}")
    assert lua.eval("PZA.call(...)", obj, "getX") == (True, 7)
    assert lua.eval("PZA.call(...)", obj, "getY")[0] is False


def test_json_empty_table_is_object_and_numbers_unrounded(lua55):
    lua = lua55
    assert lua.eval("PZA.json({})") == "{}"
    assert lua.eval("PZA.json({1.2345678901234567, 3})") == "[1.2345678901234567,3]"
    assert lua.eval("PZA.json({a='x\"y'})") == '{"a":"x\\"y"}'


def test_json_escapes_every_control_character(lua):
    lua.globals()._s = "a\x01b\x0cc\x1fd\n\te\x7f"
    out = lua.eval("PZA.json({msg = _s})")
    assert "\x01" not in out and "\x0c" not in out and "\x1f" not in out
    assert json.loads(out) == {"msg": "a\x01b\x0cc\x1fd\n\te\x7f"}
    assert py(decode(lua, out)) == {"msg": "a\x01b\x0cc\x1fd\n\te\x7f"}     # and back through the decoder


def test_missing_records_a_member_name_once(lua):
    m = lua.eval("(function() local m = {}; PZA.missing(m, 'getX'); PZA.missing(m, 'getX'); "
                 "PZA.missing(m, 'getY'); return m end)()")
    assert py(m) == ["getX", "getY"]
    assert lua.eval("PZA.readKV") is None                  # ruling S-5: the key=value reader left Core
    assert lua.eval("PZA.VERSION") == "1.0"


# ---- PZA.decode: one JSON value, nil on anything malformed -------------------------------------------------------

def test_decode_a_walk_to_command(lua):
    t = decode(lua, '{"seq":3,"aid":"a3","type":"walkTo","args":{"x":10,"y":20.5,"gait":"run"}}')
    assert py(t) == {"seq": 3, "aid": "a3", "type": "walkTo", "args": {"x": 10, "y": 20.5, "gait": "run"}}


def test_decode_every_command_form_of_the_schema(lua):
    cases = {
        '{"seq":1,"aid":"a1","type":"steer","args":{"vx":-0.5,"vy":1,"seconds":2.25,"gait":"walk"}}':
            {"seq": 1, "aid": "a1", "type": "steer", "args": {"vx": -0.5, "vy": 1, "seconds": 2.25, "gait": "walk"}},
        '{"seq":2,"aid":"a2","type":"attack","args":{"targetId":4711}}':
            {"seq": 2, "aid": "a2", "type": "attack", "args": {"targetId": 4711}},
        '{"seq":4,"aid":"a4","type":"interact","args":{"x":1,"y":2,"kind":"loot","filter":"food"}}':
            {"seq": 4, "aid": "a4", "type": "interact", "args": {"x": 1, "y": 2, "kind": "loot", "filter": "food"}},
        '{"seq":5,"aid":"a5","type":"equip","args":{"itemId":123456789012}}':
            {"seq": 5, "aid": "a5", "type": "equip", "args": {"itemId": 123456789012}},
        '{"seq":6,"aid":"a6","type":"stop","args":{}}': {"seq": 6, "aid": "a6", "type": "stop", "args": {}},
        '{"seq":7,"aid":"a7","type":"scan","args":{"r":12}}': {"seq": 7, "aid": "a7", "type": "scan", "args": {"r": 12}},
        '{"seq":8,"aid":"a8","type":"rate","args":{"hz":2.5}}': {"seq": 8, "aid": "a8", "type": "rate", "args": {"hz": 2.5}},
    }
    for s, want in cases.items():
        assert py(decode(lua, s)) == want, s


def test_decode_nested_arrays_literals_and_whitespace(lua):
    assert py(decode(lua, ' [ [1, [2, 3]], [], {"a": [true, false]} ] \n')) == [[1, [2, 3]], {}, {"a": [True, False]}]
    assert decode(lua, "true") is True
    assert decode(lua, "false") is False
    assert decode(lua, "-0.5") == -0.5


def test_decode_an_escaped_string(lua):
    assert decode(lua, r'"a\"b\\c\/d\ne\rf\tg"') == 'a"b\\c/d\ne\rf\tg'
    assert decode(lua, r'"Aé"') == "Aé"                 # \uXXXX as UTF-8 bytes
    assert decode(lua, r'"€"') == "€"
    assert decode(lua, r'"\u0001\u000c"') == "\x01\x0c"                 # a control byte


def test_decode_numbers_with_exponents(lua):
    assert decode(lua, "1e-04") == pytest.approx(1e-04)
    assert decode(lua, "[2.5E+3,-7,0]") is not None and py(decode(lua, "[2.5E+3,-7,0]")) == [2500, -7, 0]


def test_decode_null_in_an_object_leaves_the_key_absent(lua):
    t = decode(lua, '{"seq":9,"aid":null,"args":{"x":1,"gait":null}}')
    assert py(t) == {"seq": 9, "args": {"x": 1}}
    assert decode(lua, "null") is None


@pytest.mark.parametrize("bad", ["{", '{"a":}', "walkTo", '"unterminated', '{"a":1', '[1,2', '{"a" 1}', '{a:1}',
                                 "[1,]", '{"a":1,}', '"bad \\q escape"', '"\\u12"', "-", "1 2", '{"a":1} x', "",
                                 "   ", "[" * 10240, '{"a":' * 40 + "1" + "}" * 40, "tru", "nul"])
def test_decode_malformed_input_is_nil_and_raises_nothing(lua, bad):
    assert decode(lua, bad) is None


def test_decode_a_non_string_is_nil(lua):
    assert lua.eval("PZA.decode(nil)") is None
    assert lua.eval("PZA.decode(42)") is None


def test_decode_never_calls_loadstring(lua):
    with open(lua_file("shared/PZAgent_Core.lua"), encoding="utf-8") as fh:
        src = fh.read()
    assert "loadstring" not in src
    lua.execute("loadstring = function() error('loadstring called') end; load = loadstring")
    assert py(decode(lua, '{"seq":1,"args":[1,2]}')) == {"seq": 1, "args": [1, 2]}


def test_decode_depth_cap_is_32(lua):
    assert py(decode(lua, "[" * 32 + "]" * 32)) is not None
    assert decode(lua, "[" * 33 + "]" * 33) is None
