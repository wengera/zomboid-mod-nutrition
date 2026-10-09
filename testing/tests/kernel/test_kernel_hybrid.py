import pytest

NAN = float("nan")


def run(host, **kw):
    inp, out, c = host.call("hybrid.input"), host.call("hybrid.output"), host.call("hybrid.defaults")
    for k, v in kw.items():
        inp[k] = v
    host.call("hybrid.write", inp, out, c)
    return out


def test_the_hunger_target_moved_from_the_takeover(host):
    assert host.call("hybrid.hungerTarget", 1.0, 1.0) == 0
    assert host.call("hybrid.hungerTarget", 0.5, 1.0) == pytest.approx(0.5)
    assert host.call("hybrid.hungerTarget", 1.0, 1.5) == pytest.approx(0.5)   # the deficit floor 1.0 x 0.5 (Plan 11d Task 9d)


def test_mode_1_writes_hunger_thirst_and_fatigue_under_their_caps(host):
    out = run(host, mode=1, hungerTarget=0.9, thirst=0.2, thirstTarget=0.95, fOwned=True, fS=0.3, fCirc=0.05,
              fOff=0.02)
    assert out.hunger == pytest.approx(0.69) and out.thirst == pytest.approx(0.83)
    assert out.fatigue == pytest.approx(0.37)


def test_frozen_or_unowned_fatigue_is_never_written(host):
    assert run(host, mode=1, fOwned=True, fFrozen=True, fS=0.3).fatigue is None
    assert run(host, mode=1, fOwned=False).fatigue is None


def test_a_nil_thirst_target_writes_no_thirst(host):
    out = run(host, mode=1, thirst=0.2, thirstTarget=None)
    assert out.thirst is None


def test_a_non_finite_thirst_target_writes_no_thirst(host):
    assert run(host, mode=1, thirst=0.2, thirstTarget=NAN).thirst is None


def test_the_sip_is_folded_into_the_thirst_write(host):
    out = run(host, mode=1, thirst=0.1, lastThirst=0.3, sipOK=True, thirstTarget=0.3)
    assert out.sip == pytest.approx(0.2) and out.thirst == pytest.approx(0.1)


def test_no_sip_is_counted_when_an_intake_landed_or_on_the_first_write(host):
    assert run(host, mode=1, thirst=0.1, lastThirst=0.3, sipOK=False, thirstTarget=0.3).sip == 0
    assert run(host, mode=1, thirst=0.1, lastThirst=None, sipOK=True, thirstTarget=0.3).sip == 0
    assert run(host, mode=1, thirst=0.4, lastThirst=0.3, sipOK=True, thirstTarget=0.3).sip == 0


def test_overlay_writes_no_hunger_thirst_or_fatigue(host):
    out = run(host, mode=2, hungerTarget=0.5, thirst=0.1, lastThirst=0.3, thirstTarget=0.3, fOwned=True, fS=0.3,
              panicTarget=10, panic=8)
    assert out.hunger is None and out.thirst is None and out.fatigue is None and out.sip == 0
    assert out.panic == 10


def test_panic_is_held_at_its_target_only_when_below(host):
    assert run(host, panic=8.7444, panicTarget=10).panic == 10
    assert run(host, panic=11, panicTarget=10).panic is None
    assert run(host, panic=0, panicTarget=0).panic is None
    assert run(host, panic=0, panicTarget=NAN).panic is None


def test_the_stress_and_sickness_floors_rise_by_elapsed_game_time(host):
    out = run(host, dtS=60, stress=0.0, stressTarget=0.1, foodSick=0, foodSickTarget=30)
    assert out.stress == pytest.approx(5.0e-5 * 60)
    assert out.foodSick == pytest.approx(25 / 3600 * 60)
    out = run(host, dtS=7200, stress=0.0, stressTarget=1.0)          # a step over 60 minutes integrates 60
    assert out.stress == pytest.approx(5.0e-5 * 3600)                # 0.18, not the unclamped 0.36


def test_a_zero_or_negative_step_rises_nothing(host):
    for dt in (0, -600):
        out = run(host, dtS=dt, stress=0.2, stressTarget=1.0, foodSick=0, foodSickTarget=30)
        assert out.stress in (None, pytest.approx(0.2))
        assert out.foodSick in (None, pytest.approx(0))


def test_unhappiness_rises_toward_its_target_and_releases_a_fall_once(host):
    out = run(host, dtS=60, unhappy=0, unhappyTarget=20, lastUnhappyTarget=0)
    assert out.unhappy == pytest.approx(22 / 3600 * 60) and out.unhappyTarget == 20
    out = run(host, dtS=60, unhappy=20, unhappyTarget=5, lastUnhappyTarget=20)
    assert out.unhappy == pytest.approx(5)
    out = run(host, dtS=60, unhappy=3, unhappyTarget=NAN, lastUnhappyTarget=0)
    assert out.unhappy is None and out.unhappyTarget == 0


def test_temperature_is_written_only_on_the_adjustments_far_side(host):
    assert run(host, temp=37.0, tempTarget=37.5, tempAdj=0.5).temp == 37.5
    assert run(host, temp=37.6, tempTarget=37.5, tempAdj=0.5).temp is None
    assert run(host, temp=37.6, tempTarget=37.2, tempAdj=-0.2).temp == 37.2
    assert run(host, temp=37.0, tempTarget=0, tempAdj=0).temp is None


def test_intoxication_is_written_when_finite(host):
    assert run(host, intoxTarget=12.5).intox == 12.5
    assert run(host, intoxTarget=None).intox is None
    assert run(host, intoxTarget=NAN).intox is None


def test_the_asleep_endurance_gain_is_scaled_by_rmod(host):
    out = run(host, asleep=True, endurance=0.6, lastEndurance=0.5, rmod=0.5)
    assert out.endurance == pytest.approx(0.55)
    assert run(host, asleep=False, endurance=0.6, lastEndurance=0.5, rmod=0.5).endurance is None
    assert run(host, asleep=True, endurance=0.4, lastEndurance=0.5, rmod=0.5).endurance is None
