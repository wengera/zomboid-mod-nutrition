import math, pytest

F03 = 0.30000001192092896                          # the float 0.3f the jar compares against (jar report section 9)

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
            unlimitedEndurance=False, painLevel=0, stressMoodle=0, sleepTransition=False,
            stomachFill=0.8, energyState=1.0, rmod=1.0,         # Plan 2: hunger is the view of the fill, 1 - 0.8
            thirstTarget=0.1)                                   # Plan 4: thirst is the pool's view; equal to the read


def run(host, **kw):
    inp = dict(BASE); inp.update(kw)
    out = host.K.fast.output()
    host.K.fast.step(host.table(inp), out, host.table(C))
    return host.py(out)


def test_awake_idle_vanilla_rates(host):
    o = run(host)
    s = 0.8 * 0.5                                  # game-seconds this update
    assert o["thirst"] == 0.1                                     # Plan 4: the pool's view, no drain
    assert o["hunger"] == pytest.approx(1 - 0.8, rel=1e-12)       # Plan 2: derived from stomach fill, no drain
    assert o["fatigue"] == pytest.approx(0.1 + 3.45e-5 * F03 * s, rel=1e-12)      # deficit 0.1 floored to 0.3f
    assert o["stress"] == pytest.approx(0.05 - 3.0e-5 * s, rel=1e-12)
    assert o["anger"] == pytest.approx(0.02 - 1.0e-4 * s, rel=1e-12)
    assert o["morale"] == 1.0 and o["fitness"] == 0.0
    assert o["lastEndurance"] == 0.9 and o["endurance"] == 0.9
    assert o["autoDrink"] is True and o["resetIdleness"] is False


# Plan 4 (ruling 8): thirst is the water pool's view, inp.thirstTarget, written every tick whatever the
# stat read; the Plan 1 drain arms (traits, thermoFluids, running, the sleeping rate) are gone.
@pytest.mark.parametrize("target,want", [(0.0, 0.0), (0.37, 0.37), (1.2, 1.0), (-0.3, 0.0)])
def test_thirst_is_the_pool_view(host, target, want):
    o = run(host, thirst=0.6, thirstTarget=target)
    assert o["thirst"] == want
    assert o["autoDrink"] is True


def test_thirst_view_ignores_the_drain_inputs(host):
    for kw in (dict(highThirst=True), dict(lowThirst=True), dict(thermoFluids=1.5), dict(running=True),
               dict(asleep=True), dict(M=1e6)):
        assert run(host, thirst=0.2, thirstTarget=0.37, **kw)["thirst"] == 0.37


def test_thirst_view_nan_target_passes_the_stat_through(host):
    o = run(host, thirst=0.42, thirstTarget=float("nan"))
    assert o["thirst"] == 0.42
    assert o["autoDrink"] is True


def test_thirst_view_ghost_gate_skips(host):
    o = run(host, ghost=True, thirst=0.1, thirstTarget=0.9)
    assert o["thirst"] == 0.1                                           # the ghost gate; autoDrink still runs
    assert o["autoDrink"] is True


def test_thirst_input_defaults(host):
    d = host.py(host.K.fast.input())
    assert d["thirstTarget"] == 0
    assert {"highThirst", "lowThirst", "running", "thermoFluids"} <= set(d)   # adapters never shrink an input


# Plan 2 (Task 11): hunger is derived from stomach fill every tick (spec section 4.2), replacing the
# Plan 1 vanilla drain arms; the stomach is the state, hunger the view.
def test_hunger_full_stomach_reads_sated_whatever_the_stat_read(host):
    assert run(host, stomachFill=1.0, hunger=0.7)["hunger"] == 0.0
    assert run(host, stomachFill=1.0, hunger=0.0, asleep=True)["hunger"] == 0.0


def test_hunger_empty_stomach_reads_starving(host):
    assert run(host, stomachFill=0.0, hunger=0.0)["hunger"] == 1.0


def test_hunger_rises_as_the_fill_falls(host):
    assert run(host, stomachFill=0.6)["hunger"] == pytest.approx(0.4, rel=1e-12)
    assert run(host, stomachFill=0.6, asleep=True)["hunger"] == pytest.approx(0.4, rel=1e-12)
    assert run(host, stomachFill=0.3)["hunger"] > run(host, stomachFill=0.6)["hunger"]


# Plan 3 (Task 7, ruling 14): the energy state scales the fill term and, under deficit (E > 1), adds a
# floor 0.15 * (E - 1), so a starving character who just ate bulk still feels hungry.
def test_hunger_energy_state_scales_the_target(host):
    assert run(host, stomachFill=0.6, energyState=1.0)["hunger"] == pytest.approx(0.4, rel=1e-12)
    assert run(host, stomachFill=0.6, energyState=0.5)["hunger"] == pytest.approx(0.2, rel=1e-12)
    assert run(host, stomachFill=0.6, energyState=1.5)["hunger"] == pytest.approx(0.6 + 0.075, rel=1e-12)
    assert run(host, stomachFill=1.0, energyState=1.5)["hunger"] == pytest.approx(0.075, rel=1e-12)


def test_hunger_target_clamps_both_ends(host):
    assert host.K.fast.hungerTarget(1.5, 1.0) == 0.0
    assert host.K.fast.hungerTarget(0.0, 3.0) == 1.0
    assert host.K.fast.hungerTarget(0.25, 1.0) == pytest.approx(0.75, rel=1e-12)


@pytest.mark.parametrize("fill,es,h", [(1, 1, 0.0), (1, 1.5, 0.075), (0.5, 1, 0.5), (0.5, 2, 1.0),
                                       (1, 0.5, 0.0), (1, 2.0, 0.15), (0.5, 0.5, 0.25)])
def test_hunger_target_deficit_floor(host, fill, es, h):
    assert host.K.fast.hungerTarget(fill, es) == pytest.approx(h, rel=1e-12, abs=1e-15)


def test_hunger_ignores_the_drain_inputs(host):
    base = run(host, stomachFill=0.6)["hunger"]
    for kw in (dict(exercising=True), dict(foodEaten=2), dict(heartyAppetite=True), dict(lightEater=True),
               dict(sd=2.0), dict(M=1e6)):
        assert run(host, stomachFill=0.6, **kw)["hunger"] == base


def test_eat_time_hunger_write_is_overwritten(host):
    # vanilla's eat wrote hunger 0.1; the tick writes the stomach's view, not the stat it read
    assert run(host, hunger=0.1, stomachFill=0.6)["hunger"] == pytest.approx(0.4, rel=1e-12)


def test_input_defaults_read_full_and_neutral(host):
    inp = host.py(host.K.fast.input())
    assert inp["stomachFill"] == 1 and inp["energyState"] == 1


def test_fatigue_awake_terms(host):
    s = 0.4
    assert run(host, endurance=0.2)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * 0.8 * s, rel=1e-12)
    assert run(host, needsLess=True)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * F03 * s * 0.7, rel=1e-12)
    assert run(host, needsLess=True, needsMore=True)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * F03 * s * 1.3, rel=1e-12)
    assert run(host, sitting=True, thermoFatigue=2.0)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * F03 * s * 2.0 / 1.5, rel=1e-12)


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
    assert o["thirst"] == 0.1                                     # Plan 4: the pool's view asleep too
    assert o["hunger"] == pytest.approx(1 - 0.8, rel=1e-12)       # Plan 2: derived from stomach fill, no drain
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


def test_endurance_stub(host):
    assert run(host, unlimitedEndurance=True, endurance=0.3)["endurance"] == 1.0
    assert run(host, endurance=0.3)["lastEndurance"] == 0.3


def test_every_stat_stays_in_bounds_and_zero_dt_changes_nothing(host):
    o = run(host, M=0.0)
    for k in ("thirst", "fatigue", "stress", "anger", "idleness", "endurance"):
        assert o[k] == BASE[k]
    assert o["hunger"] == pytest.approx(1 - BASE["stomachFill"], rel=1e-12)   # Plan 2: the fill's view, not a drain
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
    assert run(host, asleep=True, foodEaten=1)["hunger"] == pytest.approx(1 - 0.8, rel=1e-12)   # Plan 2: fill, not foodEaten
    o = run(host, asleep=True, sleepTransition=True, timeOfDay=22.0, insomniac=True, painLevel=4, bedFactor=1.6)
    assert o["delayToSleep"] == pytest.approx(22.0 + 2.0 * 0.5, rel=1e-12)             # d capped at 2
    o = run(host, asleep=True, sleepTransition=True, timeOfDay=22.0, sleepingTablet=True, bedFactor=1.6)
    assert o["delayToSleep"] == pytest.approx(22.0 + 0.1 * 0.5, rel=1e-12)             # the tablet override


# Regression tests for the jar corrections (review I1): each pins a place where the brief's
# arithmetic differed from the jar's, so reverting the kernel to the brief's code fails here.
def test_stress_clamps_after_each_term(host):
    o = run(host, stress=0.99999, soundStress=10.0)
    assert o["stress"] == pytest.approx(1 - 3e-5 * 0.4, rel=1e-12)       # sound term clamps at 1, then the decay


def test_morale_reads_stress_after_the_decay(host):
    o = run(host, stress=0.500005, morale=0.2)
    assert o["morale"] == pytest.approx(0.7 + (0.5 - (0.500005 - 1.2e-5)) * 1e-4, rel=1e-9)


def test_endurance_deficit_reads_after_the_cheat_reset(host):
    o = run(host, unlimitedEndurance=True, endurance=0.2)
    assert o["fatigue"] == pytest.approx(0.1 + 3.45e-5 * F03 * 0.4, rel=1e-12)


def test_resting_divides_fatigue_but_sitting_blocks_the_idleness_decrease(host):
    base = run(host)["fatigue"] - 0.1
    o = run(host, resting=True, idleness=0.1)
    assert o["fatigue"] - 0.1 == pytest.approx(base / 1.5, rel=1e-9)
    assert o["idleness"] == pytest.approx(0.1 - 6e-3 * 0.4, rel=1e-12)   # resting does not block the decrease
    assert run(host, sitting=True, idleness=0.1)["idleness"] == 0.1


def test_sleep_split_compares_against_the_float_0_3(host):
    # 0.3000000075 lies between the double 0.3 and the float 0.3f: Java's fatigue <= 0.3f takes the slow arm
    dt = 1.0 / 60.0 / 60.0 * 0.8 / 2.0
    assert 0.3 < 0.3000000075 < F03
    o = run(host, asleep=True, fatigue=0.3000000075, timeOfSleep=9.0, delayToSleep=8.5)
    assert o["fatigue"] == pytest.approx(0.3000000075 - dt / 7.0 * 0.3, rel=1e-12)


# Plan 3 (Task 11, ruling 2): the asleep endurance regeneration is the one endurance arm the handler owns,
# scaled by the regeneration coefficient rmod; rmod 1 reproduces Plan 1's value exactly.
def test_asleep_regen_scales_with_rmod(host):
    plan1 = 3.1e-5 * 1.0 * 1.0 * 0.8 * 2.0
    assert run(host, asleep=True, endurance=0.5)["endurance"] == pytest.approx(0.5 + plan1, rel=1e-12)
    assert run(host, asleep=True, endurance=0.5, rmod=1.0)["endurance"] == run(host, asleep=True, endurance=0.5)["endurance"]
    assert run(host, asleep=True, endurance=0.5, rmod=2.0)["endurance"] == pytest.approx(0.5 + 2 * plan1, rel=1e-12)
    assert run(host, asleep=True, endurance=0.5, rmod=0.25)["endurance"] == pytest.approx(0.5 + 0.25 * plan1, rel=1e-12)
    assert run(host, endurance=0.5, rmod=2.0)["endurance"] == 0.5                  # awake: the takeover never writes it
    assert host.py(host.K.fast.input())["rmod"] == 1
