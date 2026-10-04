import math, pytest

C = dict(thirstIncrease=8.0e-6, thirstSleepingIncrease=1.0e-6, hungerIncrease=9.6e-6, hungerIncreaseWhenWellFed=0.0,
         hungerIncreaseWhileAsleep=1.0e-6, hungerIncreaseWhenExercise=1.92e-5, fatigueIncrease=3.45e-5,
         stressDecrease=3.0e-5, stressFromSoundsMultiplier=2.0e-5, stressFromBiteOrScratch=5.0e-5,
         stressFromHemophobic=3.333e-7, angerDecrease=1.0e-4, idleIncrease=5.0e-4, idleDecrease=6.0e-3,
         imobileEnduranceIncrease=3.1e-5, sleepDelayFraction=0.5)

BASE = dict(M=0.8, D=0.5, sd=1.0, asleep=False, ghost=False, hunger=0.2, thirst=0.1, fatigue=0.1, endurance=0.9,
            stress=0.05, anger=0.02, idleness=0.0, morale=1.0, nicotine=0.0, highThirst=False, lowThirst=False,
            heartyAppetite=False, lightEater=False, needsLess=False, needsMore=False, hemophobic=False, deaf=False,
            insomniac=False, nightOwl=False, sitting=False, foodEaten=0, exercising=False, running=False,
            thermoFatigue=1.0, thermoFluids=1.0, soundStress=0.0, partsBitten=0, partsScratched=0, infected=False,
            fakeInfected=False, totalBlood=0.0, veryClose=0, chasing=0, currentlyIdle=False, hasSquare=True,
            sameSquare=True, inRoom=False, idleTimer=0.0, bedFactor=1.0, timeOfSleep=0.0, delayToSleep=0.0,
            timeOfDay=8.0, minutesPerDay=60.0, endRegen=1.0, recoveryMod=1.0, allAsleep=False, fitnessLevel=5,
            unlimitedEndurance=False, painLevel=0, stressMoodle=0, sleepTransition=False)


def run(host, **kw):
    inp = dict(BASE); inp.update(kw)
    out = host.K.fast.output()
    host.K.fast.step(host.table(inp), out, host.table(C))
    return host.py(out)


def test_awake_idle_vanilla_rates(host):
    o = run(host)
    s = 0.8 * 0.5                                  # game-seconds this update
    assert o["thirst"] == pytest.approx(0.1 + 8.0e-6 * s, rel=1e-12)
    assert o["hunger"] == pytest.approx(0.2 + 9.6e-6 * (1 - 0.2) * s, rel=1e-12)
    assert o["fatigue"] == pytest.approx(0.1 + 3.45e-5 * 0.3 * s, rel=1e-12)      # deficit 0.1 floored to 0.3
    assert o["stress"] == pytest.approx(0.05 - 3.0e-5 * s, rel=1e-12)
    assert o["anger"] == pytest.approx(0.02 - 1.0e-4 * s, rel=1e-12)
    assert o["morale"] == 1.0 and o["fitness"] == 0.0
    assert o["lastEndurance"] == 0.9 and o["endurance"] == 0.9
    assert o["autoDrink"] is True and o["resetIdleness"] is False


def test_thirst_traits_and_thermo(host):
    s = 0.4
    assert run(host, highThirst=True)["thirst"] == pytest.approx(0.1 + 8.0e-6 * 2 * s, rel=1e-12)
    assert run(host, lowThirst=True)["thirst"] == pytest.approx(0.1 + 8.0e-6 * 0.5 * s, rel=1e-12)
    assert run(host, highThirst=True, lowThirst=True)["thirst"] == pytest.approx(0.1 + 8.0e-6 * s, rel=1e-12)
    assert run(host, thermoFluids=1.5)["thirst"] == pytest.approx(0.1 + 8.0e-6 * 1.5 * s, rel=1e-12)
    assert run(host, running=True)["thirst"] == pytest.approx(0.1 + 8.0e-6 * 1.2 * s, rel=1e-12)
    assert run(host, ghost=True)["thirst"] == 0.1                      # the ghost gate; autoDrink still runs
    assert run(host, ghost=True)["autoDrink"] is True


def test_hunger_arms(host):
    s, a = 0.4, 0.8
    assert run(host, exercising=True)["hunger"] == pytest.approx(0.2 + 1.92e-5 / 3 * a * s, rel=1e-12)
    assert run(host, exercising=True, foodEaten=2)["hunger"] == pytest.approx(0.2 + 1.92e-5 * a * s, rel=1e-12)
    assert run(host, foodEaten=1)["hunger"] == 0.2                      # well fed: the shipped constant is 0
    assert run(host, heartyAppetite=True)["hunger"] == pytest.approx(0.2 + 9.6e-6 * a * 1.5 * s, rel=1e-12)
    assert run(host, lightEater=True)["hunger"] == pytest.approx(0.2 + 9.6e-6 * a * 0.75 * s, rel=1e-12)
    assert run(host, sd=2.0)["hunger"] == pytest.approx(0.2 + 9.6e-6 * 2.0 * a * s, rel=1e-12)


def test_fatigue_awake_terms(host):
    s = 0.4
    assert run(host, endurance=0.2)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * 0.8 * s, rel=1e-12)
    assert run(host, needsLess=True)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * 0.3 * s * 0.7, rel=1e-12)
    assert run(host, needsLess=True, needsMore=True)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * 0.3 * s * 1.3, rel=1e-12)
    assert run(host, sitting=True, thermoFatigue=2.0)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * 0.3 * s * 2.0 / 1.5, rel=1e-12)


def test_stress_terms(host):
    s = 0.4
    o = run(host, soundStress=3.0, partsBitten=1, partsScratched=2, infected=True, hemophobic=True, totalBlood=10.0)
    expect = 0.05 + 3.0 * 2.0e-5 + 3 * (5.0e-5 * s) + 10.0 * 3.333e-7 * (0.8 / 0.8) * 0.5 - 3.0e-5 * s
    assert o["stress"] == pytest.approx(expect, rel=1e-12)
    assert run(host, soundStress=3.0, deaf=True)["stress"] == pytest.approx(0.05 - 3.0e-5 * s, rel=1e-12)
    assert run(host, fakeInfected=True)["stress"] == pytest.approx(0.05 + 5.0e-5 * s - 3.0e-5 * s, rel=1e-12)


def test_idleness_arms(host):
    s = 0.4
    o = run(host, veryClose=1, idleness=0.5)
    assert o["resetIdleness"] is True and o["idleness"] == 0.0
    o = run(host, currentlyIdle=True, idleTimer=1800.0, inRoom=True, idleness=0.1)
    assert o["idleness"] == pytest.approx(0.1 + 5.0e-4 * s + 5.0e-4 / 3 * s, rel=1e-12)
    assert o["idleTimer"] == pytest.approx(1800.0 + s)
    o = run(host, currentlyIdle=True, idleTimer=10.0, idleness=0.1)
    assert o["idleness"] == 0.1
    o = run(host, currentlyIdle=False, sitting=False, idleness=0.1)
    assert o["idleness"] == pytest.approx(0.1 - 6.0e-3 * s, rel=1e-12)
    assert run(host, sameSquare=False, idleTimer=50.0)["idleTimer"] == 0.0
    assert run(host, idleTimer=3600.5)["idleTimer"] == 3600.5          # saturated: no advance above 3600


def test_asleep_arms(host):
    s = 0.4
    o = run(host, asleep=True, thirst=0.1, hunger=0.2, fatigue=0.5, endurance=0.5, timeOfSleep=9.0, delayToSleep=8.5, bedFactor=1.1)
    dt = 1.0 / 60.0 / 60.0 * 0.8 / 2.0
    assert o["thirst"] == pytest.approx(0.1 + 1.0e-6 * s, rel=1e-12)
    assert o["hunger"] == pytest.approx(0.2 + 1.0e-6 * 0.8 * s, rel=1e-12)
    assert o["endurance"] == pytest.approx(0.5 + 3.1e-5 * 1.0 * 1.0 * 0.8 * 2.0, rel=1e-12)
    assert o["fatigue"] == pytest.approx(0.5 - dt / 5.0 * 0.7 * 1.1, rel=1e-12)
    assert o["timeOfSleep"] == pytest.approx(9.0 + dt, rel=1e-12)
    assert o["stress"] == 0.05                                           # no awake decay while asleep
    o = run(host, asleep=True, fatigue=0.2, timeOfSleep=9.0, delayToSleep=8.5, needsMore=True, insomniac=True)
    assert o["fatigue"] == pytest.approx(0.2 - dt / (7.0 * 1.18) * 0.3 * 0.5, rel=1e-12)
    o = run(host, asleep=True, fatigue=0.5, timeOfSleep=8.0, delayToSleep=8.5)
    assert o["fatigue"] == 0.5                                            # the delay gate holds
    assert run(host, asleep=True, allAsleep=True, endurance=0.5)["endurance"] == pytest.approx(0.5 + 3.1e-5 * 0.8 * 2.0 * 0.5, rel=1e-12)


def test_sleep_transition_seeds_the_mirrors(host):
    o = run(host, asleep=True, sleepTransition=True, timeOfDay=22.0, insomniac=True, painLevel=2, stressMoodle=1, bedFactor=0.6, nightOwl=True)
    d = min(2.0, (1.0 + (1 + 0.2 * 2)) * 1.2 * 0.6 * 0.5)
    assert o["timeOfSleep"] == pytest.approx(22.0 + 1.0 / 60.0 / 60.0 * 0.8 / 2.0, rel=1e-12)
    assert o["delayToSleep"] == pytest.approx(22.0 + d * 0.5, rel=1e-12)


def test_morale_and_fitness(host):
    assert run(host, stress=0.9)["morale"] == 1.0                        # add of 0 at ns >= 0.5, morale stays
    assert run(host, morale=0.2, stress=0.0)["morale"] == pytest.approx(min(1.0, 0.2 + 0.5 + 0.5 * 1e-4), rel=1e-9)
    assert run(host, fitnessLevel=0)["fitness"] == -1.0 and run(host, fitnessLevel=10)["fitness"] == 1.0


def test_endurance_stub_and_sentinel(host):
    assert run(host, unlimitedEndurance=True, endurance=0.3)["endurance"] == 1.0
    assert run(host, endurance=0.3)["lastEndurance"] == 0.3


def test_every_stat_stays_in_bounds_and_zero_dt_changes_nothing(host):
    o = run(host, M=0.0)
    for k in ("hunger", "thirst", "fatigue", "stress", "anger", "idleness", "endurance"):
        assert o[k] == BASE[k]
    o = run(host, thirst=0.9999999, hunger=0.9999999, stress=0.9999999, soundStress=1e9, M=1e6)
    for k in ("hunger", "thirst", "stress", "fatigue", "idleness", "morale"):
        assert 0.0 <= o[k] <= 1.0
    assert -1.0 <= o["fitness"] <= 1.0


def test_defaults_match_defines(host):
    d = host.py(host.K.fast.defaults())
    assert d == C


# Added beyond the brief (the coverage gate named these lines): the input field set the adapter
# fills, and the asleep arms the brief's tests leave unreached.
def test_input_field_set_covers_every_step_input(host):
    fields = set(host.py(host.K.fast.input()).keys())
    assert set(BASE) <= fields
    assert {"resting", "sleepingTablet"} <= fields


def test_asleep_remaining_arms(host):
    dt = 1.0 / 60.0 / 60.0 * 0.8 / 2.0
    o = run(host, asleep=True, fatigue=0.5, timeOfSleep=9.0, delayToSleep=8.5, needsLess=True, needsMore=True)
    assert o["fatigue"] == pytest.approx(0.5 - dt / (5.0 * 0.75) * 0.7, rel=1e-12)   # Needs Less tested first
    assert run(host, asleep=True, foodEaten=1)["hunger"] == 0.2                        # well fed: 0 shipped
    o = run(host, asleep=True, sleepTransition=True, timeOfDay=22.0, insomniac=True, painLevel=4, bedFactor=1.6)
    assert o["delayToSleep"] == pytest.approx(22.0 + 2.0 * 0.5, rel=1e-12)             # d capped at 2
    o = run(host, asleep=True, sleepTransition=True, timeOfDay=22.0, sleepingTablet=True, bedFactor=1.6)
    assert o["delayToSleep"] == pytest.approx(22.0 + 0.1 * 0.5, rel=1e-12)             # the tablet override
