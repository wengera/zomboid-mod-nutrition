import pytest

NAN = float("nan")


def run(host, **kw):
    inp, out, c = host.call("hybrid.input"), host.call("hybrid.output"), host.call("hybrid.defaults")
    for k, v in kw.items():
        inp[k] = v
    host.call("hybrid.write", inp, out, c)
    return out


def test_the_hunger_target_moved_from_the_takeover(host):
    assert host.call("deficit.hungerTarget", 1.0, 1.0) == 0
    assert host.call("deficit.hungerTarget", 0.5, 1.0) == pytest.approx(0.5)
    assert host.call("deficit.hungerTarget", 1.0, 1.5) == 0                    # the deficit floor 0 (Plan 11g Task 7; 0.02 x 0.5 = 0.01 from Plan 11f Task 2c fix 1, 1.0 from Plan 11d Task 9d)
    assert host.call("deficit.hungerTarget", 0.5, 1.5) == pytest.approx(0.75)


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


def test_the_unhappiness_floor_never_pulls_an_added_stat_down(host):
    # Plan 11e close: monotony's (and a food's) UNHAPPINESS add above a positive floor target is kept;
    # a target's fall subtracts only that fall
    out = run(host, dtS=60, unhappy=35, unhappyTarget=20, lastUnhappyTarget=20)
    assert out.unhappy is None
    out = run(host, dtS=60, unhappy=35, unhappyTarget=15, lastUnhappyTarget=20)
    assert out.unhappy == pytest.approx(30)


# --- Plan 11f Task 9b (ruling T9-1, T9-3): the BOREDOM floor, monotony's second target -------------------------------


def test_boredom_rises_toward_its_target_at_one_bored_level_a_game_hour(host):
    out = run(host, dtS=60, bored=0, boredTarget=20, lastBoredTarget=0)
    assert out.bored == pytest.approx(25 / 3600 * 60) and out.boredTarget == 20
    out = run(host, dtS=3600, bored=0, boredTarget=20, lastBoredTarget=0)
    assert out.bored == pytest.approx(20)


def test_a_falling_boredom_target_releases_its_fall_once(host):
    out = run(host, dtS=60, bored=20, boredTarget=5, lastBoredTarget=20)
    assert out.bored == pytest.approx(5)
    out = run(host, dtS=60, bored=3, boredTarget=0, lastBoredTarget=20)
    assert out.bored == 0                                               # never below 0
    out = run(host, dtS=60, bored=35, boredTarget=15, lastBoredTarget=20)
    assert out.bored == pytest.approx(30)                               # only the fall, whatever raised it


def test_a_boredom_at_or_over_its_target_is_left_alone(host):
    assert run(host, dtS=60, bored=35, boredTarget=20, lastBoredTarget=20).bored is None
    assert run(host, dtS=60, bored=0, boredTarget=0, lastBoredTarget=0).bored is None


def test_a_non_finite_boredom_target_reads_zero(host):
    out = run(host, dtS=60, bored=3, boredTarget=NAN, lastBoredTarget=0)
    assert out.bored is None and out.boredTarget == 0
    out = run(host, dtS=60, bored=3, boredTarget=None, lastBoredTarget=0)
    assert out.bored is None and out.boredTarget == 0


def test_the_default_input_writes_no_boredom(host):
    out = run(host, dtS=60)
    assert out.bored is None and out.boredTarget == 0 and out.unhappy is None


# --- Plan 11f Task 9b fix 1 (Rule 6): the floor holds a fall under FLOOR_EPS and folds it into the next write ------


def test_the_floor_epsilon_is_a_labelled_game_choice(host):
    assert host.K.hybrid.FLOOR_EPS == 0.05
    import os
    import re
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    src = open(os.path.join(repo, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Kernel_Hybrid.lua"),
               encoding="utf-8").read()
    line = re.search(r"^K\.hybrid\.FLOOR_EPS = .*$", src, re.M).group(0)
    assert "game choice" in line and "Rule 6" in line and "Task 9b fix 1" in line


@pytest.mark.parametrize("stat", ["unhappy", "bored"])
def test_a_fall_under_the_epsilon_is_held_and_the_old_target_remembered(host, stat):
    out = run(host, dtS=60, **{stat: 10, stat + "Target": 9.97, "last" + stat.capitalize() + "Target": 10})
    assert out[stat] is None and out[stat + "Target"] == 10


@pytest.mark.parametrize("stat", ["unhappy", "bored"])
def test_held_falls_fold_into_the_next_write_with_no_drift(host, stat):
    # the remembered target stays 10 while the target falls 0.03, then 0.06 in all: the whole 0.06 is subtracted
    out = run(host, dtS=60, **{stat: 10, stat + "Target": 9.94, "last" + stat.capitalize() + "Target": 10})
    assert out[stat] == pytest.approx(9.94, abs=1e-12) and out[stat + "Target"] == 9.94


@pytest.mark.parametrize("stat", ["unhappy", "bored"])
def test_a_fall_to_zero_lands_whatever_its_size(host, stat):
    out = run(host, dtS=60, **{stat: 0.03, stat + "Target": 0, "last" + stat.capitalize() + "Target": 0.03})
    assert out[stat] == 0 and out[stat + "Target"] == 0


@pytest.mark.parametrize("stat,rise", [("unhappy", 22 / 60), ("bored", 25 / 60)])
def test_a_held_fall_still_lets_a_stat_under_its_target_rise(host, stat, rise):
    out = run(host, dtS=60, **{stat: 5, stat + "Target": 9.97, "last" + stat.capitalize() + "Target": 10})
    assert out[stat] == pytest.approx(5 + rise) and out[stat + "Target"] == 10


@pytest.mark.parametrize("stat", ["unhappy", "bored"])
def test_a_rising_target_is_remembered_as_it_is(host, stat):
    out = run(host, dtS=60, **{stat: 10, stat + "Target": 10.01, "last" + stat.capitalize() + "Target": 10})
    assert out[stat + "Target"] == 10.01


def test_the_boredom_rise_waits_while_panic_is_above_five_and_the_target_is_remembered(host):
    out = run(host, dtS=60, bored=0, boredTarget=30, lastBoredTarget=30, panic=7)
    assert out.bored is None and out.boredTarget == 30
    out = run(host, dtS=60, bored=0, boredTarget=30, lastBoredTarget=30, panic=5)
    assert out.bored == pytest.approx(25 / 60)


def test_the_panic_wait_does_not_hold_the_unhappiness_rise_or_a_boredom_fall(host):
    out = run(host, dtS=60, unhappy=0, unhappyTarget=30, lastUnhappyTarget=30, panic=7)
    assert out.unhappy == pytest.approx(22 / 60)
    out = run(host, dtS=60, bored=20, boredTarget=0, lastBoredTarget=10, panic=7)
    assert out.bored == pytest.approx(10)
