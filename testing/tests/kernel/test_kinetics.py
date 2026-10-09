"""NR_Server_Kinetics.minute, driven end to end through a Lua stand-in for getGameTime.

The file is a server/ file the kernel host does not load, so it is loaded on top of the session host
the way test_intake_shape.py loads NR_Server_Intake.lua. Every world age is stubbed by hand; the
kernel math is the real kernel. A stub proves the wiring and the guards, not the engine's real
getWorldAgeHours, which the live runs read.
"""
import math
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
    local orig = K.stomach.drain
    K.stomach.drain = function() error("boom") end
    NR_TEST_AGE = age
    local ok, err = pcall(NutritionRevamp.server.kinetics.minute, "admin", nil, record)
    K.stomach.drain = orig
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


LN2 = 0.6931471805599453


def _frac(E, dtM):
    """K.stomach.solidFraction in doubles: the zero-order solid lane's share over dtM minutes, never above water's."""
    fw = 1 - math.exp(-LN2 * dtM / 13)
    if E <= 0:
        return fw
    left = (E + 1.25 / 0.0025) * math.exp(-0.0025 * dtM) - 1.25 / 0.0025
    fe = 1.0 if left <= 0 else max(0.0, 1 - left / E)
    return min(fe, fw)


def _substeps(E, dtM):
    """The adapter's drain of a dtM-minute gap (amendment 5): ceil(dtM) equal substeps of at most one minute."""
    n = max(1, math.ceil(dtM - 1e-9))
    for _ in range(n):
        E = E * (1 - _frac(E, dtM / n))
    return E


def test_first_call_lays_an_empty_stomach_and_stamps(kin_host):
    h = kin_host
    K = h.G.NutritionRevamp.kernel
    record = h.rt.table()
    run(h, record, 100.0)
    assert record["stomach"]["liquid"] == 0 and record["stomach"]["bulk"] is None
    for k in K.vector.KEYS.values():
        assert record["pool"][k] == 0
        assert record["stomach"]["buffer"][k] == 0
    assert record["stomachFill"] == 0                    # spec s4: a record with no stomach starts empty
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


def test_the_liquid_lane_half_empties_on_waters_half_time_with_no_energy(kin_host):
    # 13 one-minute substeps at WATER_HALF_MIN 13 (an empty solid lane): 215 g halves to 107.5 g, and F reads
    # LIQUID_WEIGHT x 107.5 / CAPACITY_MAX_G = 0.2 x 107.5 / 730 (amendment 2)
    h = kin_host
    record = rec(h, 0)
    record["stomach"]["liquid"] = 215.0
    run(h, record, 100.0)
    run(h, record, 100.0 + 13 / 60)
    assert abs(record["stomach"]["liquid"] - 107.5) < 1e-9
    assert abs(record["stomachFill"] - 0.2 * 107.5 / 730) < 1e-12


def test_second_call_moves_the_substepped_zero_order_share_into_the_pool(kin_host):
    # a 60-minute gap drains in 60 one-minute substeps (amendment 5): the solid rate rises with the load, so the
    # substeps leave more than one closed-form 60-minute step would once the water cap binds near the end
    h = kin_host
    record = rec(h, 100)
    run(h, record, 100.0)
    run(h, record, 101.0)
    left = _substeps(100.0, 60.0)
    assert abs(record["pool"]["calories"] - (100 - left)) < 1e-9
    assert abs(record["stomach"]["buffer"]["calories"] - left) < 1e-9
    assert abs(left - 100 * (1 - _frac(100, 60))) > 1e-3                # the substeps are not one closed-form step


def test_a_gap_over_sixty_minutes_drains_sixty_minutes_only(kin_host):
    # offline time is not integrated (as Metabolism and Nutrients clamp at 60 game minutes): three game hours drain
    # the same 60 one-minute substeps as one game hour
    h = kin_host
    record = rec(h, 100)
    run(h, record, 100.0)
    run(h, record, 103.0)
    assert abs(record["stomach"]["buffer"]["calories"] - _substeps(100.0, 60.0)) < 1e-9
    assert abs(record["kineticsAge"] - 103.0) < TOL


def test_no_emptied_vector_rides_the_context(kin_host):
    # amendment 1: P is fed at the eat, so the writer reads no emptied vector; only absorption's handoffs ride
    h = kin_host
    record = rec(h, 100)
    run(h, record, 100.0)
    run(h, record, 100.0 + 1 / 60)
    assert h.G.NR_TEST_PIPE.absorbed is not None and h.G.NR_TEST_PIPE.emptied is None


@pytest.mark.parametrize("age", [100.0, 99.0])
def test_zero_or_backwards_delta_empties_nothing(kin_host, age):
    h = kin_host
    record = rec(h, 100)
    run(h, record, 100.0)
    run(h, record, age)
    assert abs(record["stomach"]["buffer"]["calories"] - 100) < TOL
    assert abs(record["pool"]["calories"]) < TOL
    assert record["stomachFill"] == 0                    # energy with no mass reads empty
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
    assert abs(record["stomach"]["buffer"]["calories"] - 100) < TOL


def test_stats_count_minutes_and_players(kin_host):
    h = kin_host
    record = rec(h, 0)
    m0, p0 = KIN(h).stats.minutes, KIN(h).stats.players
    run(h, record, 100.0)
    run(h, record, 101.0)
    assert KIN(h).stats.minutes == m0 + 2
    assert KIN(h).stats.players == p0 + 2


POISON = r"""
function(age, field)
    local K = NutritionRevamp.kernel
    local r = { stomach = K.stomach.new(), pool = K.vector.new() }
    if field == "liquid" then
        r.stomach.liquid = 0 / 0
    else
        r.stomach.buffer.calories = 0 / 0
    end
    r.pool.calories = 0 / 0
    r.kineticsAge = age
    return r
end
"""


@pytest.mark.parametrize("field", ["liquid", "calories"])
@pytest.mark.parametrize("age", [None, 99.0])  # the first sight (dt 0) and a later minute (dt 1 h)
def test_a_nan_stomach_self_heals_empty(kin_host, age, field):
    h = kin_host
    K = h.G.NutritionRevamp.kernel
    record = h.rt.eval(POISON)(age, field)
    f0 = KIN(h).stats.failures
    KIN(h).lastError = None
    run(h, record, 100.0)
    assert record["stomachFill"] == 0 and record["stomach"]["liquid"] == 0
    for k in K.vector.KEYS.values():
        assert record["stomach"]["buffer"][k] == 0
        assert record["pool"][k] == 0
    assert isinstance(KIN(h).lastError, str) and "non-finite stomach fill" in KIN(h).lastError
    assert KIN(h).stats.failures == f0 + 1


FINITE_POOL = r"""
function(age, nanPool)
    local K = NutritionRevamp.kernel
    local r = { stomach = K.stomach.new(), pool = K.vector.new() }
    r.stomach.liquid = 0 / 0
    r.pool.calories = 40
    if nanPool then r.pool.iron = 0 / 0 end
    r.kineticsAge = age
    return r
end
"""


def test_a_nan_stomach_keeps_a_finite_pool(kin_host):
    # at first sight (dt 0): nothing drains, so the NaN never reaches the pool and a finite pool is kept; on a later
    # minute the drain carries the NaN into the pool first, and the pool's own check resets it (the test above)
    h = kin_host
    record = h.rt.eval(FINITE_POOL)(None, False)
    f0 = KIN(h).stats.failures
    run(h, record, 100.0)
    assert record["stomachFill"] == 0 and record["stomach"]["liquid"] == 0
    assert abs(record["pool"]["calories"] - 40) < TOL
    assert KIN(h).stats.failures == f0 + 1


def test_a_nan_stomach_and_a_nan_pool_key_resets_the_pool(kin_host):
    h = kin_host
    K = h.G.NutritionRevamp.kernel
    record = h.rt.eval(FINITE_POOL)(None, True)
    run(h, record, 100.0)
    assert record["stomachFill"] == 0
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


def test_the_guard_list_names_the_liquid_lane(kin_host):
    h = kin_host
    assert list(KIN(h).GUARD.values()) == ["liquid"]


@pytest.mark.parametrize("key", [
    "calories", "carbs", "lipids", "proteins", "fibre", "water", "vitC", "iron", "phytate",
    "retinol", "carotene", "vitD", "vitE", "vitK", "thiamine", "riboflavin", "niacin", "vitB6",
    "folate", "vitB12", "choline", "sodium", "potassium", "calcium", "magnesium", "zinc",
    "iodine", "selenium", "efa", "caffeine", "ethanol"])
def test_a_nan_in_any_buffer_key_resets_the_stomach(kin_host, key):
    h = kin_host
    r = rec(h, calories=300)
    run(h, r, 100.0)
    r.stomach.buffer[key] = float("nan")
    f0 = KIN(h).stats.failures
    run(h, r, 100.0)
    assert r.stomach.buffer.calories == 0 and r.stomachFill == 0
    assert KIN(h).stats.failures == f0 + 1


def test_a_heal_clears_the_minutes_handoff_and_keeps_the_pool_finite(kin_host):
    h = kin_host
    r = rec(h, calories=300)
    run(h, r, 100.0)
    r.stomach.buffer.vitC = float("nan")
    run(h, r, 100.0 + 1 / 60)                                     # a minute elapses: the absorbed vector takes the NaN
    ctx = h.rt.eval("function() return NR_TEST_PIPE end")()
    assert ctx.absorbed is None and ctx.mealCa is None
    assert all(math.isfinite(v) for v in r.pool.values())
    assert r.stomach.buffer.vitC == 0


def test_a_non_finite_liquid_lane_after_a_finite_fill_resets_the_stomach(kin_host):
    # an infinite lane with no minute elapsed (no drain to turn it NaN) clamps the fill to 1, which is finite, so only
    # the GUARD list catches it
    h = kin_host
    r = rec(h, calories=300)
    run(h, r, 100.0)
    r.stomach.liquid = float("inf")
    f0 = KIN(h).stats.failures
    run(h, r, 100.0)
    assert r.stomach.liquid == 0 and r.stomach.buffer.calories == 0 and r.stomachFill == 0
    assert KIN(h).stats.failures == f0 + 1


# Plan 11d close (ruling C-1): a buffer key that is nil or not a number raised in K.stomach.drain before the heal ran, so
# the stomach was never healed and the writer's F read failed every minute. The buffer check now runs before the
# drain: the stomach resets empty on the minute it is found, and the pool is kept.
@pytest.mark.parametrize("bad", [None, "x"])
@pytest.mark.parametrize("key", ["proteins", "calories", "water"])
def test_a_malformed_buffer_key_heals_within_one_minute(kin_host, key, bad):
    h = kin_host
    r = rec(h, calories=300)
    run(h, r, 100.0)
    r.stomach.buffer[key] = bad
    f0 = KIN(h).stats.failures
    run(h, r, 100.0 + 1 / 60)                                     # a minute elapses: the drain would read the key
    assert all(isinstance(v, (int, float)) and math.isfinite(v) for v in r.stomach.buffer.values())
    assert r.stomach.buffer.calories == 0 and r.stomachFill == 0
    assert all(math.isfinite(v) for v in r.pool.values())
    assert KIN(h).stats.failures == f0 + 1
    assert "malformed" in KIN(h).lastError
    run(h, r, 100.0 + 2 / 60)                                     # healed: the next minute runs clean
    assert KIN(h).stats.failures == f0 + 1


def test_a_malformed_liquid_lane_heals_within_one_minute(kin_host):
    h = kin_host
    r = rec(h, calories=300)
    run(h, r, 100.0)
    r.stomach.liquid = "x"
    run(h, r, 100.0 + 1 / 60)
    assert r.stomach.liquid == 0 and r.stomach.buffer.calories == 0 and r.stomachFill == 0
