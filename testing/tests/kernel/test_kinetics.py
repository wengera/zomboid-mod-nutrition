"""NR_Server_Kinetics.minute, driven end to end through a Lua stand-in for getGameTime.

The file is a server/ file the kernel host does not load, so it is loaded on top of the session host
the way test_intake_shape.py loads NR_Server_Intake.lua. Every world age is stubbed by hand; the
kernel math is the real kernel. A stub proves the wiring and the guards, not the engine's real
getWorldAgeHours, which the live runs read.
"""
import os
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KINETICS = os.path.join(
    REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server", "NR_Server_Kinetics.lua"
)
TOL = 1e-9

SETUP = r"""
function(age)
    NR_TEST_AGE = age
    getGameTime = function()
        return { getWorldAgeHours = function(self) return NR_TEST_AGE end }
    end
end
"""

CASE = r"""
function(record, age)
    NR_TEST_AGE = age
    NutritionRevamp.server.kinetics.minute("admin", nil, record)
    return record
end
"""

NEWREC = r"""
function(calories, seeded)
    local r = {}
    if seeded then
        r.stomach = NutritionRevamp.kernel.stomach.new()
        NutritionRevamp.kernel.stomach.seedFull(r.stomach)
        r.pool = NutritionRevamp.kernel.vector.new()
        if calories > 0 then
            local v = NutritionRevamp.kernel.vector.new()
            v.calories = calories
            r.stomach.buffer.calories = calories
        end
    end
    return r
end
"""

RAISING = r"""
function(record, age)
    local K = NutritionRevamp.kernel
    local orig = K.stomach.empty
    K.stomach.empty = function() error("boom") end
    NR_TEST_AGE = age
    local ok, err = pcall(NutritionRevamp.server.kinetics.minute, "admin", nil, record)
    K.stomach.empty = orig
    return ok, err
end
"""


@pytest.fixture(scope="session")
def kin_host(host):
    with open(KINETICS, encoding="utf-8") as fh:
        src = fh.read()
    chunk = host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@NR_Server_Kinetics.lua")
    chunk()
    host.rt.eval(SETUP)(100.0)
    return host


def KIN(h):
    return h.G.NutritionRevamp.server.kinetics


def rec(h, calories=0, seeded=True):
    return h.rt.eval(NEWREC)(calories, seeded)


def run(h, record, age):
    return h.rt.eval(CASE)(record, age)


def test_first_call_seeds_and_stamps(kin_host):
    h = kin_host
    K = h.G.NutritionRevamp.kernel
    record = h.rt.table()
    run(h, record, 100.0)
    assert abs(record["stomach"]["bulk"] - K.stomach.FULL_BULK) < TOL
    assert abs(record["stomach"]["bulk"] - 8.0) < TOL
    for k in K.vector.KEYS.values():
        assert record["pool"][k] == 0
        assert record["stomach"]["buffer"][k] == 0
    assert abs(record["stomachFill"] - 1.0) < TOL
    assert abs(record["kineticsAge"] - 100.0) < TOL


def test_first_call_leaves_a_buffer_untouched(kin_host):
    h = kin_host
    record = h.rt.table()
    stomach = h.rt.eval(NEWREC)(100, True)
    record["stomach"] = stomach["stomach"]
    record["pool"] = stomach["pool"]
    run(h, record, 100.0)  # no kineticsAge yet: dtH is 0
    assert abs(record["stomach"]["buffer"]["calories"] - 100) < TOL
    assert abs(record["pool"]["calories"]) < TOL
    assert abs(record["stomach"]["bulk"] - 8.0) < TOL


def test_second_call_empties_on_the_half_time_empty_buffer(kin_host):
    h = kin_host
    record = rec(h, 0)
    run(h, record, 100.0)
    run(h, record, 102.0)  # exactly HALF_TIME_H, composition scale 1
    assert abs(record["stomach"]["bulk"] - 4.0) < TOL
    assert abs(record["stomachFill"] - 0.5) < TOL
    assert abs(record["kineticsAge"] - 102.0) < TOL


def test_second_call_moves_half_the_buffer_into_the_pool(kin_host):
    h = kin_host
    record = rec(h, 100)
    run(h, record, 100.0)
    assert abs(record["stomach"]["buffer"]["calories"] - 100) < TOL
    run(h, record, 102.0)
    assert abs(record["pool"]["calories"] - 50) < TOL
    assert abs(record["stomach"]["buffer"]["calories"] - 50) < TOL


@pytest.mark.parametrize("age", [100.0, 99.0])
def test_zero_or_backwards_delta_empties_nothing(kin_host, age):
    h = kin_host
    record = rec(h, 100)
    run(h, record, 100.0)
    run(h, record, age)
    assert abs(record["stomach"]["bulk"] - 8.0) < TOL
    assert abs(record["stomach"]["buffer"]["calories"] - 100) < TOL
    assert abs(record["pool"]["calories"]) < TOL
    assert abs(record["stomachFill"] - 1.0) < TOL
    assert abs(record["kineticsAge"] - age) < TOL


def test_pcall_keeps_the_walk_alive(kin_host):
    h = kin_host
    record = rec(h, 100)
    run(h, record, 100.0)
    before = KIN(h).stats.minutes
    ok, err = h.rt.eval(RAISING)(record, 102.0)
    assert ok is True  # minute itself did not raise
    assert isinstance(KIN(h).lastError, str) and "boom" in KIN(h).lastError
    assert KIN(h).stats.minutes == before + 1
    assert record["stomach"] is not None and abs(record["stomach"]["bulk"] - 8.0) < TOL


def test_stats_count_minutes_and_players(kin_host):
    h = kin_host
    record = rec(h, 0)
    m0, p0 = KIN(h).stats.minutes, KIN(h).stats.players
    run(h, record, 100.0)
    run(h, record, 101.0)
    assert KIN(h).stats.minutes == m0 + 2
    assert KIN(h).stats.players == p0 + 2
