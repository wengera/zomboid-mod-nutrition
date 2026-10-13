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
    assert record["stomach"]["liquid"] == 0
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
    # 13 one-minute substeps at WATER_HALF_MIN 13 (an empty solid lane): 215 g halves to 107.5 g, and the physical fill
    # reads 107.5 / CAPACITY_MAX_G, both lanes at density 1 (ruling T6c-1)
    h = kin_host
    record = rec(h, 0)
    record["stomach"]["liquid"] = 215.0
    run(h, record, 100.0)
    run(h, record, 100.0 + 13 / 60)
    assert abs(record["stomach"]["liquid"] - 107.5) < 1e-9
    assert abs(record["stomachFill"] - 107.5 / 730) < 1e-12


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
    # Plan 11g Task 4: the satiety pool is stepped inside this step (Task 6c: M cleared by K.satiety.drain), so no emptied vector rides the context to the writer;
    # only absorption's handoffs ride
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


@pytest.mark.parametrize("bad", [None, "x"])
def test_a_malformed_liquid_lane_heals_within_one_minute(kin_host, bad):
    # ruling C9-9 (reversing 11c-10): an absent liquid lane is malformed and heals like a string one
    h = kin_host
    r = rec(h, calories=300)
    run(h, r, 100.0)
    r.stomach.liquid = bad
    f0 = KIN(h).stats.failures
    run(h, r, 100.0 + 1 / 60)
    assert r.stomach.liquid == 0 and r.stomach.buffer.calories == 0 and r.stomachFill == 0
    assert KIN(h).stats.failures == f0 + 1


# Plan 11d Task 9b (the close fix wave's residual): a pool key that is nil or not a number raised in K.stomach.toPool.
# The pool check now runs before the drain, as the stomach's does: the pool resets to zero on the minute it is found,
# and the stomach is kept.
@pytest.mark.parametrize("bad", [None, "x"])
@pytest.mark.parametrize("key", ["calories", "iron"])
def test_a_malformed_pool_key_heals_within_one_minute(kin_host, key, bad):
    h = kin_host
    r = rec(h, calories=300)
    run(h, r, 100.0)
    r.pool[key] = bad
    f0 = KIN(h).stats.failures
    run(h, r, 100.0 + 1 / 60)                                     # a minute elapses: toPool would add into the key
    assert all(isinstance(v, (int, float)) and math.isfinite(v) for v in r.pool.values())
    assert r.stomach.buffer.calories > 0                          # the stomach is kept
    assert KIN(h).stats.failures == f0 + 1
    assert "malformed pool" in KIN(h).lastError
    run(h, r, 100.0 + 2 / 60)                                     # healed: the next minute runs clean
    assert KIN(h).stats.failures == f0 + 1


def test_a_pool_that_is_not_a_table_heals(kin_host):
    h = kin_host
    r = rec(h, calories=300)
    run(h, r, 100.0)
    r.pool = 5
    run(h, r, 100.0 + 1 / 60)
    assert all(isinstance(v, (int, float)) and math.isfinite(v) for v in r.pool.values())


# Plan 11g Task 4 fix 1 (ruling T4-3) and Task 6c (spec § 7): the meal pool M's clearance is Kinetics'. The intake
# feeds M at the eat (IN.feed, test_intake_shape.py); each substep of a gap clears it (K.satiety.mealClear) at
# MEAL_HALF_LIFE_H, scaled by the appetite trait and the sandbox's stats-decrease multiplier, and nothing the stomach
# empties feeds it. The writer seeds M at first sight and reads it.

def _satiety_constant(name):
    """A K.satiety constant read off the kernel file (fitted in Plan 11g Task 6, so no value is re-typed here)."""
    import os
    import re
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "mod", "NutritionRevamp", "common",
                        "media", "lua", "shared", "NR_Kernel_Satiety.lua")
    with open(path, encoding="utf-8") as fh:
        return float(re.search(r"^K\.satiety\.%s = ([0-9.]+)" % name, fh.read(), re.M).group(1))


HL = _satiety_constant("MEAL_HALF_LIFE_H")       # M's half-life in game hours


def _clear(dtM, trait=1.0):
    """K.satiety.mealClear's factor over dtM game minutes in doubles, in the kernel's operation order."""
    return math.exp(-LN2 * (dtM / 60) * trait / HL)


def test_a_minute_clears_m_and_the_emptying_feeds_nothing(kin_host):
    # 100 kcal with no macronutrient grams over a 60-minute gap: the stomach empties and the pool absorbs it, while M
    # is only cleared, substep by substep (Plan 11g Task 6c: M is fed at the eat, never by the emptying)
    h = kin_host
    r = rec(h, 100)
    r.satiety = h.rt.eval("{ M = 10, S = 0, L = 0 }")
    run(h, r, 100.0)
    assert r.satiety.M == 10                                       # no elapsed time: nothing cleared
    run(h, r, 101.0)
    m = 10.0
    for _ in range(60):
        m = m * _clear(1.0)
    assert abs(r.satiety.M - m) < 1e-12
    assert abs(r.pool.calories - (100 - _substeps(100.0, 60.0))) < 1e-9   # the emptied kcal is what the pool absorbed


def test_the_emptied_macronutrients_feed_nothing(kin_host):
    # protein alone in the solid lane, from M 0: the minute empties some of it and M stays 0 (the weighed feed is the
    # eat's, K.satiety.mealFeed through IN.feed)
    h = kin_host
    r = rec(h, 100)
    r.stomach.buffer.proteins = 25.0                               # 100 kcal by Atwater 4
    r.satiety = h.rt.eval("{ M = 0, S = 0, L = 0 }")
    run(h, r, 100.0)
    run(h, r, 100.0 + 1 / 60)
    assert r.stomach.buffer.calories < 100
    assert r.satiety.M == 0


@pytest.mark.parametrize("sat", [None, "{ S = 0, L = 0 }", "{ M = 0 / 0, S = 0, L = 0 }", "{ M = 1 / 0, S = 0, L = 0 }"])
def test_an_unseeded_m_is_left_for_the_writers_seed(kin_host, sat):
    # a record whose satiety is absent, or whose M is absent or non-finite, is not cleared: the writer seeds it from HUNGER
    h = kin_host
    r = rec(h, 300)
    if sat is not None:
        r.satiety = h.rt.eval(sat)
    f0 = KIN(h).stats.failures
    run(h, r, 100.0)
    run(h, r, 100.0 + 1 / 60)
    assert r.stomach.buffer.calories < 300                         # the stomach still empties
    if sat is None:
        assert r.satiety is None
    else:
        g = r.satiety.M
        assert g is None or not math.isfinite(g)
    assert KIN(h).stats.failures == f0


def test_a_non_finite_clearance_keeps_m_and_counts_a_failure(kin_host):
    h = kin_host
    K = h.G.NutritionRevamp.kernel
    r = rec(h, 300)
    r.satiety = h.rt.eval("{ M = 42, S = 0, L = 0 }")
    run(h, r, 100.0)
    orig = K.satiety.mealClear
    K.satiety.mealClear = h.rt.eval("function(M, dtH, t) return 0 / 0 end")
    try:
        f0 = KIN(h).stats.failures
        run(h, r, 100.0 + 1 / 60)
    finally:
        K.satiety.mealClear = orig
    assert r.satiety.M == 42
    assert KIN(h).stats.failures == f0 + 1
    assert "meal pool" in KIN(h).lastError
    run(h, r, 100.0 + 2 / 60)                                      # the next minute clears again
    assert 0 < r.satiety.M < 42
    assert KIN(h).stats.failures == f0 + 1


def test_meal_clears_at_its_half_life_of_game_time(kin_host):
    # one MEAL_HALF_LIFE_H of game time on an empty stomach halves M; a gap past 60 minutes clears over one hour only
    h = kin_host
    r = rec(h, 0)
    r.satiety = h.rt.eval("{ M = 6, S = 0, L = 0 }")
    run(h, r, 1.0)
    run(h, r, 1.0 + HL / 2)                                       # two steps: each under the 60-minute gap cap
    run(h, r, 1.0 + HL)
    assert r.satiety.M == pytest.approx(3.0)
    run(h, r, 1.0 + HL + 3)
    assert r.satiety.M == pytest.approx(3.0 * 2 ** (-1 / HL))


def _meal(h, r):
    K = h.G.NutritionRevamp.kernel
    v = K.vector.new()
    v.calories = 600.0
    v.proteins = 22.5
    v.carbs = 75.0
    v.lipids = 23.3
    v.water = 300.0
    K.stomach.ingest(r.stomach, v)
    r.satiety = h.rt.eval("{ M = 40, S = 0, L = 0 }")


def test_a_gap_reads_the_same_m_as_its_single_minutes(kin_host):
    # a 60-minute gap drains the stomach and clears M in one-minute substeps (K.satiety.drain), exactly as 60 single
    # minutes do; ages near 1 h keep the single minutes' world-age differences exact to about 1e-14
    h = kin_host
    a = rec(h, 0)
    b = rec(h, 0)
    _meal(h, a)
    _meal(h, b)
    run(h, a, 1.0)
    run(h, b, 1.0)
    run(h, a, 2.0)                                                 # one 60-minute gap
    for m in range(1, 61):
        run(h, b, 1.0 + m / 60)                                    # sixty single minutes
    assert abs(a.stomach.buffer.calories - b.stomach.buffer.calories) < 1e-9
    assert a.stomach.buffer.calories > 0                           # the meal is still emptying at the gap's end
    assert abs(a.satiety.M - b.satiety.M) < 1e-9
    assert abs(a.satiety.M - 40 * _clear(60.0)) < 1e-9            # nothing the hour emptied fed M: an hour's clearance


TRAIT_PLAYER = r"""
function(trait, asleep)
    return { getCharacterTraits = function(s) return { get = function(c, t) return t == trait end } end,
             isAsleep = function(s) return asleep end }
end
"""

CASE_PLAYER = r"""
function(record, age, player)
    NR_TEST_AGE = age
    NR_TEST_PIPE = NR_TEST_PIPE or {}
    NutritionRevamp.server.kinetics.minute("admin", player, record, NR_TEST_PIPE)
    return record
end
"""


@pytest.mark.parametrize("trait,sd,asleep,expected", [
    (None, 1, False, 3.0),                                         # one half-life
    (None, 1, True, 3.0),                                          # ruling 11c-24: no sleep read, game time asleep
    ("HA", 1, False, 6 * 2 ** -1.5),                               # #0485, vanilla's game number
    ("LE", 1, False, 6 * 2 ** -0.75),
    (None, 2, False, 6 * 2 ** -2),                                 # ruling 11c-11: trait x sd
    ("HA", 2, False, 6 * 2 ** -3),
])
def test_the_appetite_trait_and_the_sandbox_scale_the_clearance(kin_host, trait, sd, asleep, expected):
    h = kin_host
    saved = h.rt.eval("function() return { CharacterTrait, getSandboxOptions } end")()
    h.rt.execute("CharacterTrait = { HEARTY_APPETITE = 'HA', LIGHT_EATER = 'LE' }")
    h.rt.execute("getSandboxOptions = function() return { getStatsDecreaseMultiplier = function(s) return %r end } end"
                 % float(sd))
    h.G.NutritionRevamp.so = None
    try:
        p = h.rt.eval(TRAIT_PLAYER)(trait, asleep)
        r = rec(h, 0)
        r.satiety = h.rt.eval("{ M = 6, S = 0, L = 0 }")
        h.rt.eval(CASE_PLAYER)(r, 1.0, p)
        h.rt.eval(CASE_PLAYER)(r, 1.0 + HL / 2, p)                 # each step under the 60-minute gap cap
        h.rt.eval(CASE_PLAYER)(r, 1.0 + HL, p)
        assert r.satiety.M == pytest.approx(expected)
    finally:
        h.G.CharacterTrait = saved[1]
        h.G.getSandboxOptions = saved[2]
        h.G.NutritionRevamp.so = None


def test_a_restart_through_the_store_clears_m_over_the_gap(kin_host):
    # the stamp kineticsAge and M are stored (K.store.INPUTS), so a restart three hours later clears one capped hour
    h = kin_host
    K = h.G.NutritionRevamp.kernel
    r = rec(h, 0)
    r.satiety = h.rt.eval("{ M = 6, S = 0, L = 0 }")
    run(h, r, 1.0)
    back = K.store.load(K.store.inputsOnly(r), None, None)
    assert back.kineticsAge == 1.0 and back.satiety.M == 6
    run(h, back, 4.0)
    assert back.satiety.M == pytest.approx(6 * 2 ** (-1 / HL))


def test_a_stamp_rounded_to_fourteen_digits_adds_no_substep(kin_host):
    # Plan 11g Task 4 fix 1 (ruling T4-4): the stomach drains per substep, so the substep count reaches the stomach (and,
    # while G was fed at emptying, G). A world-age stamp that passed through a 14-significant-digit format (the harness
    # slot, x260b's mid-ring start) is off by up to about 3e-9 game minutes at 1000 h; that gap still runs
    # ceil(dtM - 1e-6) = 2 substeps, as the exact one does
    h = kin_host
    a = rec(h, 0)
    b = rec(h, 0)
    _meal(h, a)
    _meal(h, b)
    run(h, a, 1001.1833333333333)
    run(h, b, 1001.1833333333333)
    b.kineticsAge = float("%.14g" % b.kineticsAge)                 # 1001.1833333333: about 3.3e-11 h early
    assert 1e-9 < ((1001.1833333333333 + 2 / 60) - b.kineticsAge) * 60 - 2 < 1e-6
    run(h, a, 1001.1833333333333 + 2 / 60)
    run(h, b, 1001.1833333333333 + 2 / 60)
    assert abs(a.stomach.buffer.calories - b.stomach.buffer.calories) < 1e-7   # the same two substeps
    assert abs(a.satiety.M - b.satiety.M) < 1e-8                    # the 2e-9 min longer gap clears about 1.5e-9 more



def test_the_traits_handle_is_cached_per_player_object_and_dropped_at_departure(kin_host):
    # Rule 6 (Plan 11g close, ruling T10-1): KIN.traits reads getCharacterTraits once per player object, as W.hoist
    # does; a new object under the same name (a reconnect or a respawn, #3360) reads it again, and KIN.forget drops it
    h = kin_host
    make = h.rt.eval("function(C) return { getCharacterTraits = function(s) C.n = C.n + 1; return { get = "
                     "function(c, t) return false end } end } end")
    C = h.rt.eval("{ n = 0 }")
    KN = KIN(h)
    a, b = make(C), make(C)
    KN.traits("u", a); KN.traits("u", a)
    assert C.n == 1
    KN.traits("u", b)
    assert C.n == 2
    KN.forget("u")
    assert KN.h["u"] is None
    KN.traits(None, b); KN.traits(None, b)                    # no name: read afresh, nothing cached
    assert C.n == 4
