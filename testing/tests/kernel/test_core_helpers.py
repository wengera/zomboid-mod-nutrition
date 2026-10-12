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


def test_obj_answers_nil_for_an_absent_or_raising_member():
    h = Host()
    o = h.rt.eval("{ a = function(s) return 5 end, b = function(s) error('x') end }")
    assert h.NR.obj(o, "a") == 5
    assert h.NR.obj(o, "b") is None and h.NR.obj(o, "zz") is None


def test_flag_is_true_only_for_true():
    h = Host()
    o = h.rt.eval("{ t = function(s) return true end, one = function(s) return 1 end, b = function(s) error('x') end }")
    assert h.NR.flag(o, "t") is True
    assert h.NR.flag(o, "one") is False and h.NR.flag(o, "b") is False and h.NR.flag(o, "zz") is False


def test_worldAge_rejects_an_infinite_age():
    h = Host()
    h.T.age = h.rt.eval("1/0")
    assert h.NR.worldAge() is None


def test_a_raising_member_is_logged_once_per_name():
    h = Host()
    o = h.rt.eval("{ b = function(s) error('broken') end }")
    for _ in range(3):
        h.NR.num(o, "b", 0)
    lines = [s for s in h.printed() if "call: b raised" in s]
    assert len(lines) == 1


def test_no_adapter_keeps_a_zero_age_wrapper():
    import glob, os, re
    from .server_host import SERVER
    bad = []
    for path in glob.glob(os.path.join(SERVER, "NR_Server_*.lua")):
        if os.path.basename(path) == "NR_Server_Fast.lua":
            continue                                   # deleted whole by Task 14
        text = open(path, encoding="utf-8").read()
        if re.search(r"worldAge\(\)\s*or\s*0|NR\.worldAge\(\)\s*or\s*0|okA and age or 0", text):
            bad.append(os.path.basename(path))
    assert bad == []


def test_sandbox_is_fetched_once_and_shared_by_kinetics_and_the_writer():
    # Plan 11g Task 6 (refactor carried from the Task 4 review): one cached sandbox object, NR.sandbox(), in place of
    # KIN.so and W.so
    h = Host()
    h.NR.so = None
    h.rt.execute("NR_SB_CALLS = 0; getSandboxOptions = function() NR_SB_CALLS = NR_SB_CALLS + 1; "
                 "return { getStatsDecreaseMultiplier = function(s) return 2 end } end")
    a = h.NR.sandbox()
    b = h.NR.sandbox()
    assert a is not None and h.rt.eval("function(x, y) return rawequal(x, y) end")(a, b)
    assert h.G.NR_SB_CALLS == 1
    assert h.NR.server.kinetics.so is None and h.NR.server.writer.so is None
    src = [open(p, encoding="utf-8").read() for p in _server_files("NR_Server_Kinetics.lua", "NR_Server_Writer.lua")]
    assert all("getSandboxOptions" not in s for s in src)


def test_sandbox_is_nil_and_refetched_while_the_global_is_absent_or_raises():
    h = Host()
    h.NR.so = None
    h.G.getSandboxOptions = None
    assert h.NR.sandbox() is None
    h.rt.execute("getSandboxOptions = function() error('not yet') end")
    assert h.NR.sandbox() is None and h.NR.so is None
    h.rt.execute("getSandboxOptions = function() return { k = 1 } end")
    assert h.NR.sandbox().k == 1


def _server_files(*names):
    import os
    from .server_host import SERVER
    return [os.path.join(SERVER, n) for n in names]
