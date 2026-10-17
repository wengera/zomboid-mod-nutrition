"""The drain-and-floor engine (NR_Kernel_Drain.lua, K.drain; Plan 15 Task 4, spec section 3.2).

Every lethal state drains overall health at its own rate (health a game day) down to a floor that deepens with the
state's severity or its time since onset and reaches 0 at the state's death point (S2231-S2262): starvation by BMI to
12 (S2234), dehydration by deficit to 17 %, wet beriberi 5 weeks after clinical onset (S2255, an inference), scurvy and
pellagra at the game choices of 90 and 180 days, the sodium and iron rungs at their Plan 5 drain times. The first floor
is 50 and every floor stays above 10 (vanilla's sleep lock, #3900) until the state's final stage. Each expectation was
worked in Python doubles from the amendments' formulas before it was written.
"""
import pytest

TOL = 1e-12
H2 = 1.70 * 1.70
FAST_DEATHS = {                       # water-only fasts (dtM 1) at Plan 15 Task 4b: (body weight kg, days, death day, state)
    "default": (None, 63, 61.91, 1),  # starvation at BMI 12 (K.drain.STARVATION); thiamine clinical only at day 42
    "90 kg": (90.0, 78, 77.00, 3),    # wet beriberi (K.drain.BERIBERI): clinical at day 42 + 840 h, before BMI 12 (~day 120)
}


@pytest.fixture(scope="module")
def D(host):
    return host.K.drain


def floor(h, code, t=0.0, lm=52.02, fm=10.0, bmi0=22.0, dehyd=0.0):
    return h.K.drain.floor(code, t, h.table({"lm": lm, "fm": fm, "bmi0": bmi0, "dehydPct": dehyd}))


def record(h, unfed=None, inDay=0.0, wday=4, lm=52.02, fm=10.0, lx=0.0, dehyd=0.0, na=140.0, vitC=(1, 0),
           thiamine=(1, 0), niacin=(1, 0), iron=0, lastAgeH=100.0, at=100.0):
    """A record at world age `at`: fed (the meal pool at 10) unless `unfed` hours ago its pool was last fed (M 0 and
    drain.fedAgeH at - unfed, Plan 15 Task 6 fix 1)."""
    t = {
        "body": {"lm": lm, "fm": fm, "lx": lx, "inDay": inDay, "wday": wday},
        "nutrients": {"vitC": {"g": vitC[0], "ah": vitC[1]}, "thiamine": {"g": thiamine[0], "ah": thiamine[1]},
                      "niacin": {"g": niacin[0], "ah": niacin[1]}, "iron": {"x": iron}, "lastAgeH": lastAgeH},
        "fluids": {"dehydPct": dehyd, "naPlasma": na},
        "acute": {"starvedDays": 0},
        "satiety": {"M": 10.0},
    }
    if unfed is not None:
        t["satiety"]["M"] = 0.0
        t["drain"] = {"fedAgeH": at - unfed}
    rec = h.table(t)
    if unfed is not None:
        h.K.drain.ensure(rec)                       # the rest of the fresh table laid around the stamp
        for k, v in h.py(h.K.drain.new()).items():
            if k != "k72" and rec.drain[k] is None:
                rec.drain[k] = v
        rec.drain.k72 = h.K.drain.newK72()
    return rec


# --- the states -------------------------------------------------------------------------------------------------

def test_the_seven_states_and_their_death_points(host, D):
    S = host.py(D.states)
    assert [S[i]["name"] for i in range(1, 8)] == ["starvation", "scurvy", "beriberi", "pellagra", "hyponatraemia",
                                                   "dehydration", "iron"]
    assert all(S[i]["firstFloor"] == 50 for i in range(1, 8))
    assert [S[i]["death"] for i in range(1, 8)] == [12, 2160, 840, 4320, 6, 17, 24]
    assert [S[i]["clock"] for i in range(1, 8)] == ["bmi", "time", "time", "time", "time", "deficit", "time"]
    assert [S[i]["onset"] for i in range(1, 8)] == [30, 4, 4, 4, 3, 4, 3]       # Task 4 fix 1: dehydration at 4 %; Task 6 fix 1: 30 unfed hours
    assert (D.STARVATION, D.SCURVY, D.BERIBERI, D.PELLAGRA, D.HYPONAT, D.DEHYD, D.IRON, D.N) == (1, 2, 3, 4, 5, 6, 7, 7)
    assert D.BMI_DEATH == 12 and D.BERIBERI_DEATH_H == 35 * 24                 # S2234; S2255 five weeks
    assert D.SCURVY_DEATH_H == 90 * 24 and D.PELLAGRA_DEATH_H == 180 * 24      # the named game choices
    assert D.FIRST_FLOOR == 50 and D.SLEEP_FLOOR == 10 and D.NONE == 100


def test_the_rates_are_health_a_game_day_at_vanilla_pace(host, D):
    r = D.rate
    assert r(1) == 25 and 50 / r(1) == 2                                     # starvation: 50 in 2 days
    assert r(6) == 200 and 50 / r(6) * 24 == 6                               # dehydration: 50 in 6 h
    for code in (2, 3, 4):
        assert r(code) == pytest.approx(50 / 3, abs=TOL)                     # the deficiencies: 50 in 3 days
    assert r(5) == 400 and r(7) == 100                                       # 100 over 6 h and 24 h (Plan 5's)


def test_the_time_knots(host, D):
    assert host.py(D.timeKnots(72, 840, 48)) == {1: {1: 0, 2: 50}, 2: {1: 72, 2: 50}, 3: {1: 792, 2: 10},
                                                  4: {1: 840, 2: 0}}
    assert host.py(D.timeKnots(0, 6, 2)) == {1: {1: 0, 2: 50}, 2: {1: 4, 2: 10}, 3: {1: 6, 2: 0}}


# --- the floor schedules ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("code,T", [(2, 2160), (3, 840), (4, 4320)])
def test_a_deficiency_floor_holds_50_for_3_days_then_falls_to_10_two_days_before_death(host, D, code, T):
    assert floor(host, code, 0) == 50 and floor(host, code, 72) == 50
    mid = (72 + (T - 48)) / 2
    assert floor(host, code, mid) == pytest.approx(30, abs=1e-9)
    assert floor(host, code, T - 48) == pytest.approx(10, abs=1e-9)
    assert floor(host, code, T - 24) == pytest.approx(5, abs=1e-9)
    assert floor(host, code, T) == 0 and floor(host, code, T + 1000) == 0


@pytest.mark.parametrize("code,T", [(5, 6), (7, 24)])
def test_a_sodium_or_iron_floor_falls_from_50_to_10_two_hours_before_death(host, D, code, T):
    assert floor(host, code, 0) == 50
    assert floor(host, code, (T - 2) / 2) == pytest.approx(30, abs=1e-9)
    assert floor(host, code, T - 2) == pytest.approx(10, abs=1e-9)
    assert floor(host, code, T - 1) == pytest.approx(5, abs=1e-9)
    assert floor(host, code, T) == 0


def test_the_dehydration_floor_by_deficit(host, D):
    # fix 1 (ruling M1): the onset knot at 4 %, weariness and apathy (S2248); 10 at 15 %, 0 at 17 % kept
    f = lambda d: floor(host, 6, dehyd=d)
    assert f(4) == 50 and f(2) == 50                                         # the onset, held above it
    assert f(9.5) == pytest.approx(30, abs=1e-9)                             # halfway from 4 % to 15 %
    assert f(15) == pytest.approx(10, abs=1e-9)
    assert f(16) == pytest.approx(5, abs=1e-9)
    assert f(17) == 0 and f(25) == 0


def test_the_starvation_floor_by_bmi_from_its_onset(host, D):
    m = lambda bmi: bmi * H2                                                 # lm + fm at a BMI
    f = lambda bmi, bmi0=22.0: floor(host, 1, lm=40.0, fm=m(bmi) - 40.0, bmi0=bmi0)
    assert f(22) == pytest.approx(50, abs=1e-9)                              # at the onset BMI
    assert f(17.25) == pytest.approx(30, abs=1e-9)                           # halfway to the knee 12.5
    assert f(12.5) == pytest.approx(10, abs=1e-9)
    assert f(12.25) == pytest.approx(5, abs=1e-9)
    assert f(12) == pytest.approx(0, abs=1e-9) and f(11.5) == 0
    assert f(23) == pytest.approx(50, abs=1e-9)                              # above its onset: the first floor
    assert f(12.6, bmi0=12.4) == 50                                          # an onset at or under the knee: 50 above it
    assert D.starveFloor(12.25, 12.4) == pytest.approx(5, abs=1e-9)
    assert D.bmi(52.02, 10.0) == pytest.approx(62.02 / H2, abs=TOL)


SCHEDULES = [
    (2, [t * 6.0 for t in range(0, 2160 // 6 + 20)], 2160 - 48, 2160),
    (3, [t * 2.0 for t in range(0, 840 // 2 + 20)], 840 - 48, 840),
    (4, [t * 12.0 for t in range(0, 4320 // 12 + 20)], 4320 - 48, 4320),
    (5, [t / 60.0 for t in range(0, 6 * 60 + 60)], 4, 6),
    (7, [t / 12.0 for t in range(0, 24 * 12 + 24)], 22, 24),
]


@pytest.mark.parametrize("code,clock,final,death", SCHEDULES)
def test_a_time_floor_falls_monotonically_stays_over_10_until_the_final_stage_and_is_0_at_death(host, D, code, clock,
                                                                                                final, death):
    prev = 100
    for t in clock:
        f = floor(host, code, t)
        assert f <= prev, (code, t)
        if t < final:
            assert f > 10, (code, t)
        else:
            assert f <= 10, (code, t)
        if t >= death:
            assert f == 0, (code, t)
        else:
            assert f > 0, (code, t)
        prev = f


def test_the_severity_floors_fall_monotonically_over_10_until_the_final_stage(host, D):
    prev = 100
    for i in range(0, 1301):
        d = 5 + i * 0.01
        f = floor(host, 6, dehyd=d)
        assert f <= prev and ((f > 10) == (d < 15)) and ((f == 0) == (d >= 17)), d
        prev = f
    prev = 100
    for i in range(0, 1101):
        bmi = 22 - i * 0.01
        f = floor(host, 1, lm=30.0, fm=bmi * H2 - 30.0, bmi0=22.0)
        assert f <= prev + 1e-12 and ((f > 10 + 1e-9) == (bmi > 12.5 + 1e-9)), bmi
        if bmi <= 12 - 1e-9:
            assert f == 0, bmi
        prev = f


def test_a_heavier_body_reaches_the_bmi_death_point_later(host, D):
    # the same daily loss (0.3 kg, taken from fat and lean in proportion to the body): the floor's 0 at BMI 12 comes
    # later for the body with more fat, whose BMI starts higher and falls the same kg a day (S2235's direction)
    def days_to_death(lm, fm):
        bmi0 = (lm + fm) / H2
        for day in range(0, 2000):
            if floor(host, 1, lm=lm, fm=fm, bmi0=bmi0) == 0:
                return day
            w = lm + fm
            lm -= 0.3 * lm / w
            fm -= 0.3 * fm / w
        raise AssertionError("no death")
    lean = days_to_death(52.02, 10.0)
    heavy = days_to_death(52.02, 30.0)
    assert heavy > lean
    assert heavy - lean == pytest.approx(20.0 / 0.3, abs=1.5)               # the extra 20 kg at 0.3 kg a day


# --- the unfed hours, the trailing 72 h and the phases (Plan 15 Task 6 fix 1) -------------------------------------
# test_the_starved_hours, of the calendar-day counter K.drain.starvedH, is deleted with the function it tested (fix 1:
# the acute onset counts unfed hours continuously); the count is reset by name.

def test_the_starvation_phases(host, D):
    p = D.starvePhase
    assert [p(0), p(29.9), p(30), p(71.9), p(72), p(335.9), p(336), p(5000)] == [0, 0, 1, 1, 2, 2, 3, 3]
    assert host.py(D.STARVE_PHASE_H) == {1: 30, 2: 72, 3: 336}
    assert D.STARVE_ONSET_H == D.STARVE_PHASE_H[1]                            # weakness from the drain's onset


# --- the step -----------------------------------------------------------------------------------------------------

def test_a_fresh_drain_table_and_its_heal(host, D):
    assert host.py(D.new()) == {"bmi0": 0, "naH": 0, "feH": 0, "active": False, "state": 0, "targetFloor": 100,
                                "rate": 0, "drainThisMinute": 0, "starvedH": 0, "acuteH": 0,
                                "k72": {i: 0 for i in range(1, 73)}, "starving": False, "starveAcute": False,
                                "dehydrated": False}
    rec = host.table({})
    d = D.ensure(rec)
    assert host.rt.eval("rawequal")(rec.drain, d) and d.bmi0 == 0
    d.bmi0, d.naH, d.feH = float("nan"), float("inf"), "x"
    d.acuteH, d.fedAgeH, d.k72h = -1.0, float("nan"), float("inf")
    D.ensure(rec)
    assert (d.bmi0, d.naH, d.feH, d.acuteH) == (0, 0, 0, 0)
    assert d.fedAgeH is None and d.k72h is None and d.k72since is None    # a non-finite stamp heals to first sight


def test_a_record_with_no_state_reads_no_floor(host, D):
    rec = record(host)
    d = D.step(rec, 1.0, 100.0)
    assert (d.active, d.state, d.targetFloor, d.rate, d.drainThisMinute) == (False, 0, 100, 0, 0)
    assert d.starvedH == 0 and d.fedAgeH == 100.0                             # fed: the stamp at the minute
    assert D.take(d, 80.0) == 0
    bare = host.table({"body": {}})
    assert D.step(bare, 1.0, 100.0).active is False                         # a record missing its sub-tables


def test_each_state_starts_at_its_onset(host, D):
    cases = [
        (dict(unfed=30.0), 100.0, 1), (dict(vitC=(4, 0)), 100.0, 2), (dict(thiamine=(4, 10)), 100.0, 3),
        (dict(niacin=(4, 10)), 100.0, 4), (dict(na=111.9), 100.0, 5), (dict(dehyd=4.0), 100.0, 6),
        (dict(iron=3), 100.0, 7),
    ]
    for kw, age, code in cases:
        d = D.step(record(host, **kw), 1.0, age)
        assert d.active is True and d.state == code, kw
        assert d.rate == D.rate(code)
        assert d.drainThisMinute == pytest.approx(D.rate(code) / 1440, abs=TOL)
    under = [(dict(unfed=29.99), 100.0), (dict(vitC=(3, 9999)), 100.0), (dict(thiamine=(3, 9999)), 100.0),
             (dict(niacin=(3, 9999)), 100.0), (dict(na=112.0), 100.0), (dict(dehyd=3.99), 100.0), (dict(iron=2), 100.0)]
    for kw, age in under:
        assert D.step(record(host, **kw), 1.0, age).active is False, kw


def test_the_lowest_floor_wins_and_the_fastest_rate_drains(host, D):
    rec = record(host, thiamine=(4, 500), dehyd=6.0, iron=3)
    d = D.step(rec, 2.0, 100.0)
    beriberi = floor(host, 3, 500)                                            # 50 - 40 x (500 - 72) / 720
    assert beriberi == pytest.approx(50 - 40 * 428 / 720, abs=1e-9)
    assert d.state == 3 and d.targetFloor == pytest.approx(beriberi, abs=1e-9)
    assert d.rate == 200 and d.drainThisMinute == pytest.approx(200 * 2 / 1440, abs=TOL)
    tie = D.step(record(host, vitC=(4, 0), thiamine=(4, 0)), 1.0, 100.0)
    assert tie.state == 2 and tie.targetFloor == 50                           # a tie keeps the earlier code


def test_the_starving_and_dehydrated_flags_follow_their_states_whichever_floor_wins(host, D):
    # Plan 15 Task 5: the writer lifts its HUNGER and THIRST caps on these flags (K.hybrid.caps), so each follows its
    # own state's onset, not the winning code
    d = D.step(record(host), 1.0, 100.0)
    assert (d.starving, d.dehydrated) == (False, False)
    d = D.step(record(host, unfed=30.0), 1.0, 100.0)
    assert (d.starving, d.starveAcute, d.dehydrated) == (True, True, False)   # the acute onset (Plan 15 Task 6)
    d = D.step(record(host, dehyd=4.0), 1.0, 100.0)
    assert (d.starving, d.dehydrated) == (False, True)
    assert D.step(record(host, dehyd=3.99), 1.0, 100.0).dehydrated is False
    d = D.step(record(host, unfed=30.0, dehyd=5.0, thiamine=(4, 800)), 1.0, 100.0)
    assert d.state == 3 and (d.starving, d.dehydrated) == (True, True)       # beriberi's floor wins; both flags hold
    chronic = record(host, fm=12.9 * H2 - 52.02, inDay=1000.0)
    d = D.step(chronic, 1.0, 100.0)
    assert d.starving is True and d.starveAcute is False                     # the chronic-BMI onset counts too, not acute
    rec = record(host, dehyd=6.0)
    D.step(rec, 1.0, 100.0)
    rec.fluids.dehydPct = 1.0
    assert D.step(rec, 1.0, 100.0 + 1 / 60).dehydrated is False               # cleared with the state
    d = D.step(host.table({"body": {}}), 1.0, 100.0)
    assert d.starving is False and d.starveAcute is False                    # a record missing its sub-tables


def test_the_onset_bmi_is_stamped_once_and_cleared_when_starvation_ends(host, D):
    rec = record(host, unfed=48.0)
    d = D.step(rec, 1.0, 100.0)
    assert d.bmi0 == pytest.approx(62.02 / H2, abs=TOL) and d.targetFloor == pytest.approx(50, abs=1e-9)
    rec.body.fm = 5.0
    D.step(rec, 1.0, 100.0 + 1 / 60)
    assert d.bmi0 == pytest.approx(62.02 / H2, abs=TOL)                       # held while the state lasts
    assert d.targetFloor < 50
    rec.satiety.M = 10.0                                                      # a meal ends it (the pool fed)
    D.step(rec, 1.0, 100.0 + 2 / 60)
    assert d.active is False and d.bmi0 == 0


def test_the_sodium_and_iron_hours_accumulate_and_reset(host, D):
    rec = record(host, na=100.0, iron=3)
    for _ in range(60):
        D.step(rec, 1.0, 100.0)
    d = rec.drain
    assert d.naH == pytest.approx(1.0, abs=1e-9) and d.feH == pytest.approx(1.0, abs=1e-9)
    assert d.state == 5 and d.targetFloor == pytest.approx(50 - 40 / 4, abs=1e-9)   # 1 h into the 6 h state
    rec.fluids.naPlasma = 140.0
    rec.nutrients.iron.x = 0
    D.step(rec, 1.0, 100.0)
    assert (d.naH, d.feH, d.active) == (0, 0, False)


def test_the_world_age_defaults_to_the_nutrients_clock(host, D):
    rec = record(host, unfed=36.0, lastAgeH=100.0)
    assert D.step(rec, 1.0, None).starvedH == 36
    assert rec.drain.active is True


def test_a_non_finite_floor_leaves_its_state_out(host, D):
    rec = record(host, thiamine=(4, float("nan")), iron=3)
    d = D.step(rec, 1.0, 100.0)
    assert d.state == 7 and d.active is True                                 # beriberi skipped this minute
    rec.nutrients.iron.x = 0
    assert D.step(rec, 1.0, 100.0).active is False


def test_take_never_passes_the_floor(host, D):
    d = host.table({"active": True, "targetFloor": 40.0, "drainThisMinute": 0.5})
    assert D.take(d, 60.0) == 0.5
    assert D.take(d, 40.2) == pytest.approx(0.2, abs=1e-12)
    assert D.take(d, 40.0) == 0 and D.take(d, 30.0) == 0                    # at or under the floor: nothing
    assert D.take(d, float("nan")) == 0 and D.take(d, None) == 0
    d.active = False
    assert D.take(d, 60.0) == 0


def test_the_drain_is_independent_of_day_length(host, D):
    # the rates are per game day: a game hour drains rate / 24 whatever the server's DayLength
    rec = record(host, dehyd=8.0)
    total = 0.0
    for _ in range(60):
        total += D.step(rec, 1.0, 100.0).drainThisMinute
    assert total == pytest.approx(200 / 24, abs=1e-9)


# --- fix 1: the chronic-BMI onset (M3) and healing toward the floor (L2) -------------------------------------------

def test_a_bmi_under_13_is_starvation_whatever_the_days_intake(host, D):
    # BMI_CHRONIC: a low eater (6 kcal/kg today, no starved day) at BMI 12.9 starves; at 13.1 not
    assert D.BMI_CHRONIC == 13
    lm = 30.0
    fed = lambda bmi: record(host, inDay=6.0 * bmi * H2, lm=lm, fm=bmi * H2 - lm)
    d = D.step(fed(12.9), 1.0, 100.0)
    assert d.active is True and d.state == 1 and d.starvedH == 0
    assert d.bmi0 == pytest.approx(12.9, abs=1e-9) and d.targetFloor == pytest.approx(50, abs=1e-9)
    assert D.step(fed(13.1), 1.0, 100.0).active is False
    rec = fed(12.9)
    D.step(rec, 1.0, 100.0)
    rec.body.fm = 12.5 * H2 - lm
    assert D.step(rec, 1.0, 100.0).targetFloor == pytest.approx(10, abs=1e-9)   # 10 at the knee 12.5


def test_vanillas_regeneration_tier(host, D):
    a = D.regenAddition
    assert a(0, 0, 0, False) == 0.002 and a(1, 1, 1, False) == 0.002                 # #2354 standard
    assert a(2, 0, 0, False) == 0.0013 and a(0, 0, 2, False) == 0.0013                # level 2: reduced
    assert a(0, 3, 0, False) == 0.0008 and a(0, 0, 4, False) == 0.0008                # level 3, or SICK 4
    assert a(4, 0, 0, False) == 0 and a(0, 4, 3, False) == 0                          # HUNGRY or THIRST 4 (#2721)
    assert a(3, 3, 3, True) == 0.02 and a(0, 4, 0, True) == 0                         # asleep; #0515 zeroes it at 4
    assert D.UNITS_PER_MIN == 2 and D.PART_SPREAD == pytest.approx(17 / 5.05, abs=TOL)


def test_the_heal_reaches_the_floor_and_never_passes_it(host, D):
    d = host.table({"active": True, "targetFloor": 50.0})
    assert D.heal(d, 20.0, 0.24, 1.0) == pytest.approx(0.24, abs=TOL)               # vanilla's pace, uncapped
    assert D.heal(d, 49.95, 0.24, 1.0) == pytest.approx(0.05 * 17 / 5.05, abs=1e-9)  # capped at the floor
    assert D.heal(d, 49.995, 0.24, 1.0) == 0 and D.heal(d, 60.0, 0.24, 1.0) == 0    # at or above it
    assert D.heal(d, float("nan"), 0.24, 1.0) == 0 and D.heal(d, 20.0, float("nan"), 1.0) == 0
    health = 20.0
    for _ in range(2000):
        health += D.heal(d, health, 0.24, 1.0) * 5.05 / 17
        assert health <= 50.0 + 1e-9
    assert health == pytest.approx(50.0, abs=0.011)
    d.active = False
    assert D.heal(d, 20.0, 0.24, 1.0) == 0


@pytest.mark.parametrize("body", sorted(FAST_DEATHS))
def test_a_water_only_fast_kills_the_default_body_by_starvation_and_a_90_kg_body_by_beriberi(host, body):
    """End to end (the Task 4 review's M2, Plan 15 Task 4b): the whole server pipeline (tools/replay_live.replay_arm),
    water only (0.5 L every 6 h), until health reaches 0. Thiamine reaches the clinical grade at day 42 with none
    eaten, so wet beriberi kills at about day 77 (42 + 840 h): after the default body's BMI-12 death (day 61.9), before
    the 90 kg body's (about day 120)."""
    import os
    import sys
    tools = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                         "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import replay_live as RL
    weight, days, death_day, death_state = FAST_DEATHS[body]
    dtM = 1.0
    events = [{"minute": int(k * 360 / dtM), "kind": "drink", "fluid": "Water", "litres": 0.5} for k in range(days * 4)]
    paths = ["drain.state", "drain.targetFloor", "nutrients.thiamine.g"]
    deaths = []
    clinical = []
    orig = RL.ServerReplay.row

    def row(self, p):
        out = orig(self, p)
        st = self.p.st.body
        out["health"] = 100 - st.reduced + st.added
        return out
    RL.ServerReplay.row = row
    kw = {} if weight is None else {"player": {"weight": weight}}
    try:
        rows, _ = RL.replay_arm(events, minutes=int(days * 1440 / dtM), start_age=100.0, dtM=dtM, paths=paths, **kw)
    finally:
        RL.ServerReplay.row = orig
    t0 = rows[0]["age"] - dtM / 60
    for r in rows:
        if not clinical and r["nutrients.thiamine.g"] == 4:
            clinical.append((r["age"] - t0) / 24)
        if r["health"] <= 1e-6:
            deaths.append(((r["age"] - t0) / 24, r["drain.state"]))
            break
    assert deaths, "no death in %d days" % days
    day, state = deaths[0]
    assert state == death_state
    assert day == pytest.approx(death_day, abs=0.1)
    assert clinical[0] == pytest.approx(42, abs=0.01)    # both bodies: clinical at day 42 with none eaten


# --- Plan 15 Task 6 fix 1: the unfed hours and the trailing 72 h -----------------------------------------------------

def test_the_unfed_hours_count_across_a_record_day_with_no_reset(host, D):
    rec = record(host, unfed=0.0, at=23.5, wday=0)
    assert D.step(rec, 1.0, 23.5).starvedH == 0
    rec.body.wday = 1                                                          # the record day closes at 24
    d = D.step(rec, 1.0, 24.5)
    assert d.starvedH == pytest.approx(1.0, abs=TOL) and d.fedAgeH == 23.5
    rec.body.inDay = 10000.0                                                   # the day's intake no longer matters
    assert D.step(rec, 1.0, 26.0).starvedH == pytest.approx(2.5, abs=TOL)


def test_a_pool_at_fed_m_stamps_and_reads_0(host, D):
    rec = record(host, unfed=20.0)
    rec.satiety.M = host.K.hungerCurve.FED_M
    d = D.step(rec, 1.0, 100.0)
    assert d.starvedH == 0 and d.fedAgeH == 100.0
    rec.satiety.M = host.K.hungerCurve.FED_M * 0.999
    assert D.step(rec, 1.0, 101.0).starvedH == pytest.approx(1.0, abs=TOL)


def test_the_acute_onset_at_30_unfed_hours(host, D):
    assert D.STARVE_ONSET_H == 30
    assert D.step(record(host, unfed=29.99), 1.0, 100.0).starveAcute is False
    assert D.step(record(host, unfed=30.0), 1.0, 100.0).starveAcute is True


def test_first_sight_and_an_unseeded_pool_stamp_and_read_0(host, D):
    rec = record(host)
    rec.satiety = None
    d = D.step(rec, 1.0, 100.0)
    assert d.starvedH == 0 and d.fedAgeH == 100.0
    rec.satiety = host.table({})                                               # M not seeded yet
    assert D.step(rec, 1.0, 140.0).starvedH == 0
    assert D.unfedH(host.table({}), None, None) == 0                           # no clock: none
    assert D.unfedH(host.table({"fedAgeH": float("nan")}), host.table({"M": 0}), 50.0) == 0   # a bad stamp: first sight


def test_the_acute_clock_runs_on_through_a_snack_inside_the_state(host, D):
    rec = record(host, unfed=40.0)
    for m in range(60):
        d = D.step(rec, 1.0, 100.0 + m / 60)
    assert d.starveAcute is True and d.acuteH == pytest.approx(1.0, abs=1e-9)
    rec.satiety.M = 10.0                                                       # a snack: the pool fed
    d = D.step(rec, 1.0, 101.0)
    assert d.starveAcute is False and d.acuteH == 0 and d.starvedH == 0       # no 72 h window yet: the state ends


def kcal72_record(h, at):
    rec = record(h, unfed=0.0, at=at)
    rec.body.trail = h.K.body.newTrail(at)
    return rec


def eat_into_trail(h, rec, kcal, at):
    h.K.body.trailTo(rec.body.trail, at)
    h.K.body.trailAdd(rec.body.trail, "kcal", kcal)


def test_the_trailing_72_h_window_counts_absorbed_kcal(host, D):
    t0 = 1000.0
    rec = kcal72_record(host, t0)
    eat_into_trail(host, rec, 300.0, t0)
    assert D.step(rec, 1.0, t0).kcal72 is None                                 # under 72 h seen
    a = t0
    for hour in range(1, 73):
        a = t0 + hour
        host.K.body.trailTo(rec.body.trail, a)
        d = D.step(rec, 60.0, a)
        if hour == 30:
            eat_into_trail(host, rec, 250.0, a)
    assert d.kcal72 == pytest.approx(250.0, abs=1e-9)                           # the first 300 is past 72 h
    host.K.body.trailTo(rec.body.trail, a + 43)
    assert D.step(rec, 60.0, a + 43).kcal72 == pytest.approx(0, abs=1e-9)     # the 250 has left the window too


def test_a_200_kcal_snack_every_33_h_still_enters_the_acute_state(host, D):
    # the controller's ruling on the review's weak spot: a snack resets the unfed clock, but the trailing 72 h intake
    # at or under K72_MIN_KCAL (600, about 200 kcal a day; a window holds up to three snacks, 600) holds the acute onset
    assert D.K72_MIN_KCAL == 600
    t0 = 1000.0
    rec = kcal72_record(host, t0)
    acute = []
    for hour in range(0, 24 * 8):
        a = t0 + hour
        host.K.body.trailTo(rec.body.trail, a)
        if hour % 33 == 0:
            eat_into_trail(host, rec, 200.0, a)
            rec.satiety.M = 10.0
        else:
            rec.satiety.M = 0.0
        d = D.step(rec, 60.0, a)
        acute.append(d.starveAcute)
        if hour >= 72:
            assert d.kcal72 <= 600
    assert all(acute[72:]) and d.starving is True
    assert d.starvedH >= 30 + (24 * 8 - 1 - 72) - 1e-9                          # the clock ran on through the snacks


def test_the_window_survives_a_restart(host, D):
    t0 = 1000.0
    rec = kcal72_record(host, t0)
    for hour in range(0, 80):
        host.K.body.trailTo(rec.body.trail, t0 + hour)
        if hour == 70:
            eat_into_trail(host, rec, 400.0, t0 + hour)
        D.step(rec, 60.0, t0 + hour)
    want = rec.drain.kcal72
    assert want == pytest.approx(400.0, abs=1e-9)
    saved = host.py(host.K.store.inputsOnly(rec))["drain"]                     # what a save keeps
    assert set(saved) == {"bmi0", "naH", "feH", "fedAgeH", "acuteH", "k72", "k72h", "k72since"}
    assert len(saved["k72"]) == 72 and sum(saved["k72"].values()) == pytest.approx(400.0, abs=1e-9)
    rec.drain.k72s = None                                                      # derived: rebuilt after a load
    assert D.kcal72(rec.drain, rec.body.trail) == pytest.approx(400.0, abs=1e-9)


def test_the_window_over_600_kcal_leaves_the_acute_onset_to_the_unfed_hours(host, D):
    t0 = 1000.0
    rec = kcal72_record(host, t0)
    for hour in range(0, 80):
        host.K.body.trailTo(rec.body.trail, t0 + hour)
        rec.satiety.M = 0.0
        if hour == 60:
            eat_into_trail(host, rec, 601.0, t0 + hour)
            rec.satiety.M = 10.0                                               # the meal fed the pool: 19 unfed h by 79
        d = D.step(rec, 60.0, t0 + hour)
    assert d.kcal72 == pytest.approx(601.0, abs=1e-9) and d.starveAcute is False


def test_a_non_finite_slot_restarts_the_window(host, D):
    t0 = 1000.0
    rec = kcal72_record(host, t0)
    for hour in range(0, 3):
        host.K.body.trailTo(rec.body.trail, t0 + hour)
        D.step(rec, 60.0, t0 + hour)
    rec.drain.k72[(int(t0) + 1) % 72 + 1] = float("nan")
    rec.drain.k72s = None
    assert D.kcal72(rec.drain, rec.body.trail) is None
    assert rec.drain.k72since is None and rec.drain.k72h is None               # restarted: first sight again
    assert D.kcal72(rec.drain, None) is None                                  # an unreadable trail
