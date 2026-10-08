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

INTAKE = os.path.join(
    REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server", "NR_Server_Intake.lua"
)

# The session-host stubs: the previous getGameTime and NR_TEST_AGE are returned so the fixture's
# teardown puts them back and nothing leaks into a later module.
SETUP = r"""
function(age)
    local saved = { getGameTime = getGameTime, age = NR_TEST_AGE }
    NR_TEST_AGE = age
    getGameTime = function()
        return { getWorldAgeHours = function(self) return NR_TEST_AGE end }
    end
    return saved
end
"""

TEARDOWN = r"""
function(saved)
    getGameTime = saved.getGameTime
    NR_TEST_AGE = saved.age
end
"""

CASE = r"""
function(record, age)
    NR_TEST_AGE = age
    NR_TEST_PIPE = NR_TEST_PIPE or {}        -- the pipeline's context (Plan 10 R2), kept across calls here
    NutritionRevamp.server.kinetics.minute("admin", nil, record, NR_TEST_PIPE)
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


def _load(host, path, name):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, name)()


@pytest.fixture(scope="module")
def kin_host(host):
    # the self-heal reads NR.server.intake.isFinite (Intake loads before Kinetics in the game); a run
    # of this module alone loads it here, as test_intake_shape.py does
    if host.G.NutritionRevamp.server.intake is None:
        _load(host, INTAKE, "@NR_Server_Intake.lua")
    _load(host, KINETICS, "@NR_Server_Kinetics.lua")
    saved = host.rt.eval(SETUP)(100.0)
    try:
        yield host
    finally:
        host.rt.eval(TEARDOWN)(saved)


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


POISON = r"""
function(age)
    local K = NutritionRevamp.kernel
    local r = { stomach = K.stomach.seedFull(K.stomach.new()), pool = K.vector.new() }
    r.stomach.bulk = 0 / 0
    r.stomach.buffer.calories = 0 / 0
    r.pool.calories = 0 / 0
    r.kineticsAge = age
    return r
end
"""


@pytest.mark.parametrize("age", [None, 99.0])  # the first sight (dt 0) and a later minute (dt 1 h)
def test_nan_bulk_self_heals(kin_host, age):
    h = kin_host
    K = h.G.NutritionRevamp.kernel
    record = h.rt.eval(POISON)(age)
    f0 = KIN(h).stats.failures
    KIN(h).lastError = None
    run(h, record, 100.0)
    assert record["stomachFill"] == 1
    assert abs(record["stomach"]["bulk"] - K.stomach.FULL_BULK) < TOL
    for k in K.vector.KEYS.values():
        assert record["stomach"]["buffer"][k] == 0
        assert record["pool"][k] == 0
    assert isinstance(KIN(h).lastError, str) and "non-finite stomach fill" in KIN(h).lastError
    assert KIN(h).stats.failures == f0 + 1


FINITE_POOL = r"""
function(age, nanPool)
    local K = NutritionRevamp.kernel
    local r = { stomach = K.stomach.seedFull(K.stomach.new()), pool = K.vector.new() }
    r.stomach.bulk = 0 / 0
    r.pool.calories = 40
    if nanPool then r.pool.iron = 0 / 0 end
    r.kineticsAge = age
    return r
end
"""


@pytest.mark.parametrize("age", [None, 99.0])  # the first sight (dt 0) and a later minute (an empty buffer)
def test_nan_bulk_keeps_a_finite_pool(kin_host, age):
    h = kin_host
    K = h.G.NutritionRevamp.kernel
    record = h.rt.eval(FINITE_POOL)(age, False)
    f0 = KIN(h).stats.failures
    run(h, record, 100.0)
    assert record["stomachFill"] == 1
    assert abs(record["stomach"]["bulk"] - K.stomach.FULL_BULK) < TOL
    assert abs(record["pool"]["calories"] - 40) < TOL
    assert KIN(h).stats.failures == f0 + 1


def test_nan_bulk_and_a_nan_pool_key_resets_the_pool(kin_host):
    h = kin_host
    K = h.G.NutritionRevamp.kernel
    record = h.rt.eval(FINITE_POOL)(None, True)
    run(h, record, 100.0)
    assert record["stomachFill"] == 1
    assert abs(record["stomach"]["bulk"] - K.stomach.FULL_BULK) < TOL
    for k in K.vector.KEYS.values():
        assert record["pool"][k] == 0


BREAD = r"""
function()
    local K = NutritionRevamp.kernel
    local r = { stomach = K.stomach.new(), pool = K.vector.new() }
    local v = K.vector.new()
    v.calories = 532.0
    v.lipids = 6.66
    v.fibre = 4.4
    v.water = 65.0
    v.iron = 6.5
    v.phytate = 400.0
    v.calcium = 95.0
    K.stomach.ingest(r.stomach, v)
    return r
end
"""


def test_the_meal_context_is_passed_from_the_buffer(kin_host):
    # ruling T17-1 (x151r #2981): the first minute of a 400 mg phytate loaf absorbs 0.18 x exp(-1.36)
    # = 0.0461989 mg per mg of iron emptied, and the buffer's calcium before the emptying is handed on
    h = kin_host
    record = h.rt.eval(BREAD)()
    run(h, record, 100.0)
    run(h, record, 100.0 + 1 / 60)
    emptied = 6.5 - record["stomach"]["buffer"]["iron"]
    assert emptied > 0
    assert abs(record["pool"]["iron"] / emptied - 0.046198939851640065) < 1e-12
    assert h.G.NR_TEST_PIPE.mealCa == 95.0                 # the handoff rides the pipeline's context
    assert KIN(h).ctx.phytate == 400.0                     # the one context table, overwritten per step
    run(h, record, 100.0 + 2 / 60)
    assert h.G.NR_TEST_PIPE.mealCa < 95.0                  # the buffer before the second minute's emptying
    assert h.G.NR_TEST_PIPE.absorbed is not None
    run(h, record, 100.0 + 2 / 60)                         # no elapsed time: both handoffs cleared
    assert h.G.NR_TEST_PIPE.absorbed is None and h.G.NR_TEST_PIPE.mealCa is None
    assert KIN(h).lastAbsorbed is None and KIN(h).lastMealCa is None   # the per-username tables are gone


from .server_host import Host


def test_a_failed_clock_read_never_empties_the_stomach_on_the_next_minute():
    h = Host()
    p = h.player("admin")
    h.online(p)
    h.T.age = 500.0
    h.minute(); h.tick(5)                       # first sight and one worked minute at age 500
    fill0 = h.record("admin").stomachFill
    good = h.G.getGameTime
    h.G.getGameTime = h.rt.eval("function() error('clock') end")
    h.minute(); h.tick(5)                       # a minute whose clock read fails
    h.G.getGameTime = good
    h.T.age = 500.0 + 1 / 60
    h.minute(); h.tick(5)                       # the next good minute: one game minute later
    assert h.record("admin").kineticsAge == 500.0 + 1 / 60
    assert h.record("admin").stomachFill > fill0 - 0.01   # one minute of emptying, not 500 hours


def test_kinetics_skips_a_minute_without_a_clock():
    h = Host()
    rec = h.NR.server.store.get("k", 100.0)
    ctx = h.rt.eval("{ absorbed = {}, mealCa = 5 }")
    h.G.getGameTime = h.rt.eval("function() error('clock') end")
    h.NR.server.kinetics.minute("k", h.player("k"), rec, ctx)
    assert h.NR.server.kinetics.badAge == 1
    assert ctx.absorbed is None and ctx.mealCa is None and rec.kineticsAge is None


def test_a_failed_clock_read_never_creates_a_record():
    h = Host()
    h.G.getGameTime = h.rt.eval("function() error('clock') end")
    assert h.NR.server.store.get("nobody", h.NR.worldAge()) is None
    assert h.record("nobody") is None
