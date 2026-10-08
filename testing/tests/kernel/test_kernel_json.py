import math
import pytest

FMT = "function(x) return string.format('%.17g', x) end"


def enc(host, t):
    return host.call("json.encode", t, host.rt.eval(FMT))


def test_round_trip_of_a_record_shape(host):
    t = host.rt.eval("""{ v = 3, username = 'ad"min\\\\', dead = false, firstSeen = 118.51666666666667,
        body = { fm = 12.25, eb7 = { 1, -2.5, 3 }, bandWeek = { { 1, 2 }, { 3, 4 } } },
        nutrients = { vitC = { p = 0.9999999999999999, g = 1 } }, pool = {}, [7] = 'seven' }""")
    out, err = host.call("json.decode", enc(host, t))
    assert err is None
    assert out.v == 3 and out.username == 'ad"min\\' and out.dead is False
    assert out.firstSeen == 118.51666666666667 and out.nutrients.vitC.p == 0.9999999999999999
    assert [out.body.eb7[i] for i in (1, 2, 3)] == [1, -2.5, 3]
    assert out.body.bandWeek[2][1] == 3 and out[7] == "seven"


def test_a_non_finite_number_encodes_null_and_decodes_absent(host):
    t = host.rt.eval("{ a = 0/0, b = 1/0, c = 2 }")
    out, err = host.call("json.decode", enc(host, t))
    assert out.a is None and out.b is None and out.c == 2


def test_an_empty_table_is_an_object(host):
    assert enc(host, host.rt.eval("{}")) == "{}"


def test_java_style_exponents_decode(host):
    out, err = host.call("json.decode", '{"a":1.0E-5,"b":-2.5E10,"c":1e-05}')
    assert out.a == pytest.approx(1.0e-5) and out.b == pytest.approx(-2.5e10) and out.c == pytest.approx(1e-5)


def test_control_characters_and_unicode_escapes(host):
    out, err = host.call("json.decode", '{"s":"a\\nb\\tc\\u0041"}')
    assert out.s == "a\nb\tcA"
    s = enc(host, host.rt.eval("{ s = 'x\\ny' }"))
    assert "\\n" in s


@pytest.mark.parametrize("bad", ['{"a":1', '{"a" 1}', '[1,2', '{"a":tru}', '', '{"a":"x}'])
def test_malformed_text_decodes_to_nil_and_an_error(host, bad):
    out, err = host.call("json.decode", bad)
    assert out is None and isinstance(err, str)


def test_a_control_character_a_function_and_a_boolean_key_encode(host):
    s = enc(host, host.rt.eval("{ c = string.char(1), f = function() end, [true] = 1 }"))
    assert "\\u0001" in s and '"f":null' in s and "true" not in s     # the boolean key is skipped
    out, err = host.call("json.decode", s)
    assert err is None and out.c == "\x01" and out.f is None


def test_the_literals_and_an_empty_array_decode(host):
    out, err = host.call("json.decode", '{"t":true,"f":false,"n":null,"e":[]}')
    assert err is None and out.t is True and out.f is False and out.n is None and len(out.e) == 0


@pytest.mark.parametrize("bad", ["[1e]", r'"\uZZZZ"', r'"\q"', "{1:2}", '{"a', "[1,}", "{} x"])
def test_every_decode_refusal_names_its_place(host, bad):
    out, err = host.call("json.decode", bad)
    assert out is None and err.startswith("json: ")


def test_control_bytes_encode_as_lowercase_hex_escapes(host):
    s = enc(host, host.rt.eval("{ c = string.char(31) .. string.char(10) .. string.char(2) }"))
    assert r"\u001f" in s and r"\n" in s and r"\u0002" in s


def test_a_mixed_table_keeps_every_key(host):
    for src in ("{ 1, 2, x = 3 }", "{ [2] = 'a', [3] = 'b', x = 'c' }", "{ 1, nil, 3, x = 4 }"):
        t = host.rt.eval(src)
        out, err = host.call("json.decode", enc(host, t))
        assert err is None and out.x is not None, src
    out, err = host.call("json.decode", enc(host, host.rt.eval("{ 1, 2, x = 3 }")))
    assert out[1] == 1 and out[2] == 2 and out.x == 3
    out, err = host.call("json.decode", enc(host, host.rt.eval("{ [2] = 'a', [3] = 'b', x = 'c' }")))
    assert out[2] == "a" and out[3] == "b" and out.x == "c"


def test_an_array_with_a_nan_keeps_its_indexes(host):
    s = enc(host, host.rt.eval("{ 1, 0/0, 3 }"))
    assert s == "[1,null,3]"
    out, err = host.call("json.decode", s)
    assert err is None and out[1] == 1 and out[2] is None and out[3] == 3


def test_hash_prefixed_string_keys_stay_strings(host):
    t = host.rt.eval("{ ['#5'] = 'a', ['##'] = 'b', ['#.0'] = 'c', ['#\f0'] = 'd', [5] = 'num' }")
    out, err = host.call("json.decode", enc(host, t))
    assert err is None
    assert out["#5"] == "a" and out["##"] == "b" and out["#.0"] == "c" and out["#\x0c0"] == "d"
    assert out[5] == "num" and out["5"] is None


@pytest.mark.parametrize("top", ["null", "5", "true", '"s"'])
def test_a_top_level_non_table_is_unreadable(host, top):
    out, err = host.call("json.decode", top)
    assert out is None and isinstance(err, str)
