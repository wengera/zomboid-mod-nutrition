import pytest
from lupa import LuaRuntime
from .conftest import lua_file, make_lua


@pytest.fixture
def lua55(fs):
    """The Lua 5.5 host, for the number rendering only: Kahlua's tostring is Java's Double.toString, which
    round-trips a double the way 5.5's tostring does; the 5.1 host's %.14g is the less faithful one there."""
    return make_lua(fs, LuaRuntime)


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


def test_readkv_and_missing(lua, fs):
    fs.files["pzagent/admin/cmd.txt"] = "seq=3\ngoal=goto\nargs=1 2 run\n"
    t = lua.eval("PZA.readKV('pzagent/admin/cmd.txt')")
    assert t["seq"] == "3" and t["args"] == "1 2 run"
    assert lua.eval("PZA.readKV('nope.txt')") is None
    m = lua.eval("(function() local m = {}; PZA.missing(m, 'getX'); PZA.missing(m, 'getX'); return #m end)()")
    assert m == 1
