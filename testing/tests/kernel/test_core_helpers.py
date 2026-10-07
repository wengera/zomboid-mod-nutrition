from .server_host import Host


def test_worldAge_is_nil_when_the_clock_read_fails():
    h = Host()
    h.G.getGameTime = h.rt.eval("function() error('boom') end")
    assert h.NR.worldAge() is None


def test_worldAge_reads_the_age():
    h = Host()
    h.T.age = 123.5
    assert h.NR.worldAge() == 123.5


def test_finite_rejects_nan_and_inf():
    h = Host()
    nan, inf = h.rt.eval("0/0"), h.rt.eval("1/0")
    assert h.NR.finite(1.0) and not h.NR.finite(nan) and not h.NR.finite(inf) and not h.NR.finite("1")


def test_num_falls_back_on_absent_raising_or_nonfinite():
    h = Host()
    o = h.rt.eval("{ a = function(s) return 2 end, b = function(s) error('x') end, c = function(s) return 0/0 end }")
    assert h.NR.num(o, "a", 7) == 2
    assert h.NR.num(o, "b", 7) == 7 and h.NR.num(o, "c", 7) == 7 and h.NR.num(o, "zz", 7) == 7
