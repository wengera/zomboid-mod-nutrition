"""Expenditure and energy state (NR_Kernel_Energy.lua), Plan 3 Task 7.

NR_Kernel_Energy.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.energy. Every expectation below is hand-computed
from the file's constants: REE = 19.7 * LM + 413 (S0004); the adaptive-thermogenesis magnitude 0.10,
full at half the fat store gone, tau 7 d on and 14 d off (a design-phase-v1 game choice; direction
S0013/S0016); the shivering cap 4.9 (S0048); the resting MET 1.0 (S0018/S0019); the engine Metabolics
values (#2632) and the Compendium METs per class (S0018-S0043); the timed-action band METs (#2720/#2638);
the Compendium load-walking floors (S0035); the engine load factor (#2649); the energy state (ruling 14).
"""
import math

import pytest

TOL = 1e-9


def _close(a, b):
    return abs(a - b) < TOL


def _body(host, **kw):
    d = dict(lm=65.6, fm=14.4, at=0.0, inDay=0.0, eeDay=0.0, ebDay=0.0, actKcalDay=0.0, exKcalDay=0.0,
             pDay=0.0, carbDay=0.0, lipDay=0.0)
    d.update(kw)
    return host.table(d)


# --- constants ---

def test_constants(host):
    e = host.K.energy
    assert e.REE_A == 19.7 and e.REE_B == 413
    assert e.AT_MAX == 0.10 and e.AT_FULL_DEP == 0.5 and e.AT_TAU_ON == 7 and e.AT_TAU_OFF == 14
    assert e.COLD_MAX == 4.9 and e.MET_REST == 1.0


CLASS_MET = dict(Sleeping=0.8, SeatedResting=1.0, StandingAtRest=1.1, SedentaryActivity=1.2, DrivingCar=1.4,
                 Default=1.5, LightDomestic=1.6, Walking2kmh=1.9, HeavyDomestic=2.0, UsingTools=2.5,
                 DefaultExercise=3.0, Walking5kmh=3.1, LightWork=3.2, MediumWork=3.9, JumpFence=4.0,
                 DiggingSpade=5.5, HeavyWork=6.0, Fitness=6.0, Running10kmh=6.9, ClimbRope=8.0,
                 ForestryAxe=8.0, FitnessHeavy=9.0, Running15kmh=9.5, MAX=10.3)

COMPENDIUM = dict(Sleeping=1.0, SeatedResting=1.0, StandingAtRest=1.3, SedentaryActivity=1.5, DrivingCar=1.4,
                  Default=1.3, LightDomestic=1.6, HeavyDomestic=2.0, UsingTools=2.5, DefaultExercise=3.0,
                  Walking2kmh=1.9, Walking5kmh=3.8, LightWork=3.0, MediumWork=4.0, HeavyWork=6.0,
                  JumpFence=4.0, DiggingSpade=5.0, Fitness=6.0, FitnessHeavy=9.0, Running10kmh=9.3,
                  ClimbRope=8.0, ForestryAxe=6.5, Running15kmh=14.8, MAX=14.8)


def test_class_met_table(host):
    assert host.py(host.K.energy.CLASS_MET) == CLASS_MET


def test_class_list_is_every_class_in_ascending_value_order(host):
    names = list(host.py(host.K.energy.CLASS_LIST).values())
    assert sorted(names) == sorted(CLASS_MET)
    values = [CLASS_MET[n] for n in names]
    assert values == sorted(values)


def test_compendium_table(host):
    assert host.py(host.K.energy.COMPENDIUM) == COMPENDIUM


def test_band_met_table(host):
    assert host.py(host.K.energy.BAND_MET) == {0.5: 1.0, 2: 2.5, 3: 6.0, 4: 4.3, 5: 5.5, 8: 7.0}


def test_load_floor_table(host):
    rows = host.py(host.K.energy.LOAD_FLOOR)
    assert [list(r.values()) for r in rows.values()] == [[2.3, 4.0], [6.8, 4.5], [22.7, 6.5]]


# --- bandMet, loadFloor, stripLoad ---

@pytest.mark.parametrize("mod,met", [(0.5, 1.0), (2, 2.5), (3, 6.0), (4, 4.3), (5, 5.5), (8, 7.0),
                                     (1, None), (7, None)])
def test_band_met(host, mod, met):
    assert host.K.energy.bandMet(mod) == met


@pytest.mark.parametrize("kg,met", [(0, 0), (2.29, 0), (2.3, 4.0), (6.7, 4.0), (6.8, 4.5), (10, 4.5),
                                    (22.6, 4.5), (22.7, 6.5), (60, 6.5)])
def test_load_floor(host, kg, met):
    assert host.K.energy.loadFloor(kg) == met


def test_strip_load(host):
    e = host.K.energy
    assert _close(e.stripLoad(2.0, 50, 100), 2.0 / 1.0875)
    assert _close(e.stripLoad(2.7, 200, 100), 2.7 / 1.35)          # the load fraction clamps at 1
    assert e.stripLoad(2.0, 0, 100) == 2.0
    assert e.stripLoad(2.0, 50, 0) == 2.0                           # maxW <= 0 reads unloaded
    assert e.stripLoad(2.0, 50, -1) == 2.0


# --- classOf ---

@pytest.mark.parametrize("met,name", [
    (3.08, "Walking5kmh"),
    (3.05, "DefaultExercise"),     # 3.05 - 3.0 < 3.1 - 3.05 in doubles: the nearest is DefaultExercise
    (1.5, "Default"),
    (9.4, "Running15kmh"),
    (0.1, "Sleeping"),
    (5.75, "DiggingSpade"),        # an exact tie (5.5 / 6.0) goes to the lower
    (9.25, "FitnessHeavy"),        # an exact tie (9.0 / 9.5) goes to the lower
    (6.0, "HeavyWork"),            # equal engine values: the first in CLASS_LIST
    (8.0, "ClimbRope"),
    (50, "MAX"),
])
def test_class_of(host, met, name):
    assert host.K.energy.classOf(met) == name


# --- activityMet ---

@pytest.mark.parametrize("cls,moving,mod,kg,met", [
    ("Default", False, 8, 0, 7.0),            # not moving: the timed-action band raises the bill
    ("Default", False, 1, 0, 1.3),            # modifier 1: no band
    ("HeavyWork", False, 2, 0, 6.0),          # the band never lowers the class value
    ("Walking5kmh", True, 8, 0, 3.8),         # moving ignores the band (#0462)
    ("Walking5kmh", True, 1, 10, 4.5),        # the load-walking floor
    ("Walking5kmh", True, 1, 1, 3.8),         # under the first floor
    ("Walking2kmh", True, 1, 30, 6.5),        # the heaviest floor
    ("Walking5kmh", False, 1, 30, 3.8),       # the floor applies only while moving
    ("Running10kmh", True, 1, 30, 9.3),       # running: no floor
    ("Unknown", False, 1, 0, 1.3),            # an unknown class reads standing quietly
])
def test_activity_met(host, cls, moving, mod, kg, met):
    assert host.K.energy.activityMet(cls, moving, mod, kg) == met


# --- REE and adaptive thermogenesis ---

def test_ree(host):
    assert _close(host.K.energy.ree(66), 1713.2)
    assert _close(host.K.energy.ree(65.6), 1705.32)


@pytest.mark.parametrize("fm,ref,at", [(7.2, 14.4, 0.10), (10.8, 14.4, 0.05), (14.4, 14.4, 0.0),
                                       (20, 14.4, 0.0), (0, 14.4, 0.10), (5, 0, 0), (5, -1, 0)])
def test_at_target(host, fm, ref, at):
    assert _close(host.K.energy.atTarget(fm, ref), at)


def test_at_step_on_and_off(host):
    e = host.K.energy
    assert _close(e.atStep(0, 0.1, True, 7), 0.1 * (1 - math.exp(-1)))
    assert _close(e.atStep(0.1, 0, False, 14), 0.1 * math.exp(-1))
    assert _close(e.atStep(0.05, 0.1, True, 0), 0.05)
    assert _close(e.atStep(0.05, 0.1, False, 0), 0.05)


# --- minute ---

REE_MIN = 1705.32 / 1440                 # (19.7 * 65.6 + 413) / 1440 = 1.184250
ACT_MIN = 2.8 * 80 / 60                  # (3.8 - 1.0) * (14.4 + 65.6) / 60 = 3.733333


def test_minute_awake_walking(host):
    b = _body(host)
    ee, act = host.K.energy.minute(b, 3.8, False, 1, 1)
    assert _close(ee, REE_MIN + ACT_MIN)
    assert _close(ee, 4.917583333333333)
    assert _close(act, ACT_MIN)
    assert _close(b.eeDay, ee) and _close(b.actKcalDay, act) and _close(b.ebDay, -ee)


def test_minute_cold_applies_only_at_rest(host):
    b = _body(host)
    ee, act = host.K.energy.minute(b, 3.8, False, 2, 1)
    assert _close(ee, REE_MIN + ACT_MIN)                            # not resting: coldK 1


def test_minute_resting_cold_doubles_ree(host):
    b = _body(host)
    ee, act = host.K.energy.minute(b, 1.0, True, 2, 1)
    assert _close(ee, 2 * REE_MIN) and act == 0


def test_minute_cold_clamps(host):
    ee, _ = host.K.energy.minute(_body(host), 1.0, True, 10, 1)
    assert _close(ee, 4.9 * REE_MIN)
    ee, _ = host.K.energy.minute(_body(host), 1.0, True, 0.5, 1)
    assert _close(ee, REE_MIN)                                      # never below 1


def test_minute_at_scales_ree(host):
    ee, _ = host.K.energy.minute(_body(host, at=0.1), 1.0, False, 1, 1)
    assert _close(ee, 0.9 * REE_MIN)


def test_minute_below_rest_bills_no_activity(host):
    ee, act = host.K.energy.minute(_body(host), 0.8, False, 1, 1)
    assert _close(ee, REE_MIN) and act == 0


def test_minute_scales_by_dt_and_accumulates(host):
    b = _body(host, inDay=1000.0)
    ee1, act1 = host.K.energy.minute(b, 3.8, False, 1, 10)
    assert _close(ee1, 10 * (REE_MIN + ACT_MIN)) and _close(act1, 10 * ACT_MIN)
    ee2, act2 = host.K.energy.minute(b, 3.8, False, 1, 5)
    assert _close(b.eeDay, ee1 + ee2) and _close(b.actKcalDay, act1 + act2)
    assert _close(b.ebDay, 1000 - ee1 - ee2)
    ee0, act0 = host.K.energy.minute(b, 3.8, False, 1, 0)
    assert ee0 == 0 and act0 == 0


def test_minute_idle_class_banks_no_exercise(host):
    # Ruling W-1: the idle class (COMPENDIUM.Default, 1.3 MET) is not exercise; actKcalDay still bills it
    b = _body(host)
    ee, act = host.K.energy.minute(b, 1.3, False, 1, 1)
    assert b.exKcalDay == 0
    assert _close(act, 0.3 * 80 / 60) and _close(b.actKcalDay, act)
    host.K.energy.minute(b, 0.8, True, 1, 60)
    assert b.exKcalDay == 0                                         # below the idle class: still 0


def test_minute_walking_banks_exercise_above_the_idle_class(host):
    # Ruling W-1: a walking minute banks (3.8 - 1.3) * 80 / 60 = 3.333333 kcal of exercise
    b = _body(host)
    host.K.energy.minute(b, 3.8, False, 1, 1)
    assert _close(b.exKcalDay, (3.8 - 1.3) * 80 / 60)
    assert _close(b.exKcalDay, 3.3333333333333335)
    host.K.energy.minute(b, 3.8, False, 1, 10)
    assert _close(b.exKcalDay, 11 * (3.8 - 1.3) * 80 / 60)


# --- intake ---

def test_intake_accumulates_and_eb_follows(host):
    b = _body(host, eeDay=300.0)
    a = host.table(dict(calories=250.0, proteins=12.0, carbs=30.0, lipids=9.0))
    host.K.energy.intake(b, a, 1)
    host.K.energy.intake(b, a, 1)
    assert _close(b.inDay, 500) and _close(b.pDay, 24) and _close(b.carbDay, 60) and _close(b.lipDay, 18)
    assert _close(b.ebDay, 200)


# --- eb24h and state ---

def test_eb24h(host):
    b = host.table(dict(ebDay=-500.0, eb7={1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: -1000.0}))
    e = host.K.energy
    assert _close(e.eb24h(b, 12), -1000)
    assert _close(e.eb24h(b, 0), -1500)
    assert _close(e.eb24h(b, 24), -500)


def test_eb24h_reads_hours_since_the_last_close(host):
    # Close fix wave (T18 defect 2): the blend runs on hours since the last close, clamped, so the
    # window never stretches past 24 h whatever the clock reads.
    b = host.table(dict(ebDay=250.0, eb7={1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 400.0}))
    e = host.K.energy
    assert _close(e.eb24h(b, 0), 650)
    assert _close(e.eb24h(b, 24), 250)
    assert _close(e.eb24h(b, 31), 250)
    assert _close(e.eb24h(b, 6), 250 + 400 * 0.75)


@pytest.mark.parametrize("eb,dep,es", [(-1500, 0, 1.5), (1500, 0, 0.5), (0, 1, 1.5), (-3000, 1, 2.0),
                                       (0, 0, 1.0), (-750, 0, 1.25), (3000, 0, 0.5), (3000, -1, 0.5),
                                       (-3000, 2, 2.0)])
def test_state(host, eb, dep, es):
    assert _close(host.K.energy.state(eb, dep), es)


# Plan 4 (the glycogen term, a game choice): E gains 0.3 x (1 - g); g omitted reads 1, so every Plan 3
# caller is byte-identical.
@pytest.mark.parametrize("eb,dep,g,es", [(0, 0, 1, 1.0), (0, 0, 0, 1.3), (0, 0, 0.5, 1.15),
                                         (-1500, 0, 0, 1.8), (-3000, 1, 0, 2.0), (3000, 0, 0, 0.8),
                                         (-750, 0.5, 0.5, 1.65)])
def test_state_glycogen_term(host, eb, dep, g, es):
    assert _close(host.K.energy.state(eb, dep, g), es)


def test_state_without_g_equals_g_one(host):
    e = host.K.energy
    for eb, dep in [(-1500, 0), (1500, 0), (0, 1), (-750, 0.25)]:
        assert e.state(eb, dep) == e.state(eb, dep, 1)
