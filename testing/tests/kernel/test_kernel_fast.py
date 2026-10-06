import math, pytest

F03 = 0.30000001192092896                          # the float 0.3f the jar compares against (jar report section 9)

C = dict(thirstIncrease=8.0e-6, thirstSleepingIncrease=1.0e-6, hungerIncrease=9.6e-6, hungerIncreaseWhenWellFed=0.0,
         hungerIncreaseWhileAsleep=1.0e-6, hungerIncreaseWhenExercise=1.92e-5, fatigueIncrease=3.45e-5,
         stressDecrease=3.0e-5, stressFromSoundsMultiplier=2.0e-5, stressFromBiteOrScratch=5.0e-5,
         stressFromHemophobic=3.333e-7, angerDecrease=1.0e-4, idleIncrease=5.0e-4, idleDecrease=6.0e-3,
         imobileEnduranceIncrease=3.1e-5, sleepDelayFraction=0.5,
         extEps=0.1, moodRiseStress=5.0e-5, hungerCap=0.69, thirstCap=0.83)   # Plan 5 (Task 7)

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
            thirstTarget=0.1,                                   # Plan 4: thirst is the pool's view; equal to the read
            fOwned=False, fFrozen=False, fS=0.0, fCirc=0.0, fOff=0.0, solAddH=0.0, solMul=1.0,   # Plan 5: the
            endFold=False, endLast=1.0, dmod=1.0, stressTarget=0.0,
            resting=False, sleepingTablet=False)                              # defaults, Plan 1 arms


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
@pytest.mark.parametrize("target,want", [(0.0, 0.0), (0.37, 0.37), (1.2, 0.83), (-0.3, 0.0)])   # Plan 5: cap 0.83
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
    assert run(host, stomachFill=0.0, hunger=0.0)["hunger"] == 0.69   # Plan 5 ruling 14: the view's cap


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


# --- Plan 5 (Task 7): the FATIGUE writer (ruling 11), the sleep-onset latency (B6), the endurance fold
# (ruling 15), the stress floor (ruling 9) and the view caps (ruling 14). Hand values in Python doubles.

import os, re

KERNEL_FAST = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                           "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Kernel_Fast.lua")

CIRC_0100 = 0.08485281374238571                    # 0.12 * cos(2 pi (1 - 4) / 24), I-B1c at 01:00
CAF_OFF_107 = 0.35 * 107 / (107 + 150) * (1 - 0.6 * 0)   # cafOffset at 107 mg, tolerance 0
F_OFF_IB1 = min(0.005 * 6, 0.10) - CAF_OFF_107 + 0.0      # debt 6 h, fOffNut 0
DT = 1.0 / 60.0 / 60.0 * 0.8 / 2.0                  # game-hours asleep per BASE update


def test_input_plan5_defaults(host):
    d = host.py(host.K.fast.input())
    want = dict(fOwned=False, fFrozen=False, fS=0, fCirc=0, fOff=0, solAddH=0, solMul=1, endFold=False,
                endLast=1, dmod=1, rmod=1, stressTarget=0)
    assert {k: d[k] for k in want} == want


def test_input_field_set_covers_every_inp_the_region_reads(host):
    src = open(KERNEL_FAST, encoding="utf-8").read()
    region = src[src.index("-- @fastpath"):src.index("-- @endfastpath")]
    read = set(re.findall(r"\binp\.(\w+)", region))
    assert read <= set(host.py(host.K.fast.input()).keys())
    assert read <= set(BASE)


def test_ib1_owned_fatigue_hand_value(host):
    assert CAF_OFF_107 == 0.14571984435797664
    for asleep in (False, True):
        o = run(host, asleep=asleep, fOwned=True, fS=0.5, fCirc=CIRC_0100, fOff=F_OFF_IB1,
                timeOfSleep=9.0, delayToSleep=8.5)
        assert o["fatigue"] == 0.5 + CIRC_0100 + F_OFF_IB1          # the kernel's association, bit-exact
        # the briefing's 0.4691329693844091 sums 0.03 and -cafOffset separately: one ulp away
        assert o["fatigue"] == pytest.approx(0.4691329693844091, rel=1e-15, abs=0)


def test_owned_fatigue_ignores_the_vanilla_terms_and_clamps(host):
    for kw in (dict(), dict(endurance=0.1), dict(needsMore=True, sitting=True, thermoFatigue=3.0), dict(sd=4.0)):
        assert run(host, fOwned=True, fS=0.4, fCirc=0.02, fOff=0.01, **kw)["fatigue"] == 0.4 + 0.02 + 0.01
    assert run(host, fOwned=True, fS=0.95, fCirc=0.12, fOff=0.1)["fatigue"] == 1.0
    assert run(host, fOwned=True, fS=0.01, fCirc=-0.12, fOff=-0.2)["fatigue"] == 0.0


def test_owned_asleep_keeps_the_time_of_sleep_advance(host):
    o = run(host, asleep=True, fOwned=True, fatigue=0.5, fS=0.3, timeOfSleep=9.0, delayToSleep=8.5, bedFactor=1.1)
    assert o["fatigue"] == 0.3
    assert o["timeOfSleep"] == pytest.approx(9.0 + DT, rel=1e-12)
    assert o["endurance"] == pytest.approx(0.9 + 3.1e-5 * 0.8 * 2.0, rel=1e-12)


def test_frozen_writes_the_engine_reset_back(host):
    for asleep in (False, True):
        o = run(host, asleep=asleep, fOwned=True, fFrozen=True, fatigue=1.03e-4, fS=0.7, fCirc=0.1, fOff=0.05,
                timeOfSleep=9.0, delayToSleep=8.5)
        assert o["fatigue"] == 1.03e-4


def test_unowned_is_the_plan1_arm_whatever_the_slow_scalars(host):
    for kw in (dict(), dict(asleep=True, fatigue=0.5, timeOfSleep=9.0, delayToSleep=8.5),
               dict(asleep=True, fatigue=0.2, timeOfSleep=9.0, delayToSleep=8.5, insomniac=True)):
        plain = run(host, **kw)
        assert run(host, fFrozen=True, fS=0.9, fCirc=0.1, fOff=0.1, **kw) == plain
    assert run(host)["fatigue"] == pytest.approx(0.1 + 3.45e-5 * F03 * 0.4, rel=1e-12)


def test_sleep_onset_latency_terms(host):
    o = run(host, asleep=True, sleepTransition=True, timeOfDay=22.0, solMul=1.2, solAddH=0.1)
    assert o["delayToSleep"] == pytest.approx(22.0 + (0.3 * 1.2 + 0.1) * 0.5, rel=1e-12)
    o = run(host, asleep=True, sleepTransition=True, timeOfDay=22.0, insomniac=True, painLevel=4, bedFactor=1.6,
            solMul=1.2, solAddH=0.1)
    assert o["delayToSleep"] == pytest.approx(22.0 + 2.0 * 0.5, rel=1e-12)          # the cap still binds
    o = run(host, asleep=True, sleepTransition=True, timeOfDay=22.0, solMul=0.6)
    assert o["delayToSleep"] == pytest.approx(22.0 + 0.3 * 0.6 * 0.5, rel=1e-12)


def test_ic1_endurance_fold_hand_values(host):
    o = run(host, endFold=True, endLast=0.8, endurance=0.799, dmod=1.5)
    assert o["endurance"] == 0.8 + (0.799 - 0.8) * 1.5
    assert o["endurance"] == pytest.approx(0.7985, rel=1e-12)
    o = run(host, endFold=True, endLast=0.8, endurance=0.8005, rmod=0.8)
    assert o["endurance"] == 0.8 + (0.8005 - 0.8) * 0.8
    assert o["endurance"] == pytest.approx(0.8004, rel=1e-12)
    assert o["lastEndurance"] == 0.8005                              # the stub still stamps the stat read


def test_endurance_fold_passes_an_external_jump(host):
    assert run(host, endFold=True, endLast=0.5, endurance=0.8, dmod=2.0, rmod=0.5)["endurance"] == 0.8
    assert run(host, endFold=True, endLast=0.8, endurance=0.5, dmod=2.0, rmod=0.5)["endurance"] == 0.5
    assert run(host, endFold=True, endLast=0.8, endurance=0.8, dmod=2.0, rmod=0.5)["endurance"] == 0.8


def test_endurance_fold_unit_coefficients_are_the_identity(host):
    for e0 in (1.0, 0.8, 0.5, 0.3, 0.12):
        for d in (-0.0999, -0.012, -4.55e-4, 3.1e-5, 0.0015, 0.0999):
            x = min(1.0, max(0.0, e0 + d))
            assert run(host, endFold=True, endLast=e0, endurance=x)["endurance"] == x


def test_endurance_fold_then_the_cheat_and_the_asleep_regen(host):
    assert run(host, endFold=True, endLast=0.8, endurance=0.799, dmod=1.5, unlimitedEndurance=True)["endurance"] == 1.0
    o = run(host, endFold=True, asleep=True, endLast=0.5, endurance=0.5005, rmod=0.8)
    folded = 0.5 + (0.5005 - 0.5) * 0.8
    assert o["endurance"] == pytest.approx(folded + 3.1e-5 * 0.8 * 2.0 * 0.8, rel=1e-12)


def test_endurance_fold_off_is_the_plan1_arm(host):
    assert run(host, endLast=0.8, endurance=0.799, dmod=1.5, rmod=0.8)["endurance"] == 0.799
    assert run(host, asleep=True, endLast=0.8, endurance=0.5)["endurance"] == pytest.approx(0.5 + 3.1e-5 * 0.8 * 2.0, rel=1e-12)


def test_stress_floor_rises_at_vanilla_bite_rate(host):
    s = 0.4
    o = run(host, stress=0.0, stressTarget=0.06)
    assert o["stress"] == pytest.approx(5.0e-5 * s, rel=1e-12)            # the decay clamps at 0, then the rise
    o = run(host, stress=0.05, stressTarget=0.06)
    assert o["stress"] == pytest.approx(0.05 - 3.0e-5 * s + 5.0e-5 * s, rel=1e-12)
    o = run(host, asleep=True, stress=0.05, stressTarget=0.06)
    assert o["stress"] == pytest.approx(0.05 + 5.0e-5 * s, rel=1e-12)      # asleep: no decay, the floor applies


def test_stress_floor_holds_exactly_at_the_target(host):
    assert run(host, stress=0.06, stressTarget=0.06)["stress"] == 0.06
    assert run(host, stress=0.0599999, stressTarget=0.06)["stress"] == 0.06
    assert run(host, asleep=True, stress=0.06, stressTarget=0.06)["stress"] == 0.06
    assert run(host, stress=0.3, stressTarget=0.06)["stress"] == pytest.approx(0.3 - 3.0e-5 * 0.4, rel=1e-12)
    assert run(host, stress=0.05)["stress"] == pytest.approx(0.05 - 3.0e-5 * 0.4, rel=1e-12)   # target 0: vanilla


def test_hunger_view_capped_under_level_4(host):
    for kw in (dict(stomachFill=0.0), dict(stomachFill=0.2, energyState=3.0), dict(stomachFill=0.3),
               dict(asleep=True, stomachFill=0.0)):
        assert run(host, **kw)["hunger"] == 0.69
    assert run(host, stomachFill=0.32)["hunger"] == pytest.approx(0.68, rel=1e-12)


def test_thirst_view_capped_under_level_4_whatever_the_target(host):
    for kw in (dict(thirstTarget=0.95), dict(thirstTarget=1.0), dict(ghost=True, thirst=0.9),
               dict(thirst=0.9, thirstTarget=float("nan")), dict(asleep=True, thirstTarget=0.84)):
        assert run(host, **kw)["thirst"] == 0.83
    assert run(host, thirstTarget=0.8)["thirst"] == 0.8


# --- Plan 5 (Task 9): the fast HANDLER (NR_Server_Fast.lua) fills the Plan 5 inputs and writes the floors,
# the temperature target, endurance under the fold and INTOXICATION. The file names Java at hoist, so it
# is loaded in a runtime of its own over stubs (the shape of test_intake_shape.py's FAST_STUBS) with a
# get/set counter per stat. s = M x D = 2 x 3 = 6 game-seconds per update.

import lupa.lua51 as lua51

FAST_HANDLER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                            "mod", "NutritionRevamp", "common", "media", "lua", "server", "NR_Server_Fast.lua")
SHARED_DIR = os.path.dirname(KERNEL_FAST)
S_TICK = 6.0
RISE_PANIC = 24 / 3600                              # one PANIC band per game hour (ruling 9; open S1146)
RISE_UNHAPPY = 22 / 3600                            # one UNHAPPINESS band per game hour
RISE_SICK = 25 / 3600                               # one SICK level per game hour on FOOD_SICKNESS's 0-100 scale

HANDLER_STUBS = r"""
function(withIds)
    CharacterStat = { HUNGER = "HUNGER", THIRST = "THIRST", FATIGUE = "FATIGUE", ENDURANCE = "ENDURANCE",
                      STRESS = "STRESS", ANGER = "ANGER", IDLENESS = "IDLENESS", MORALE = "MORALE",
                      NICOTINE_WITHDRAWAL = "NICOTINE", FITNESS = "FITNESS" }
    if withIds then
        CharacterStat.PANIC = "PANIC"
        CharacterStat.UNHAPPINESS = "UNHAPPINESS"
        CharacterStat.FOOD_SICKNESS = "FOOD_SICKNESS"
        CharacterStat.TEMPERATURE = "TEMPERATURE"
        CharacterStat.INTOXICATION = "INTOXICATION"
    end
    MoodleType = { FOOD_EATEN = "FOOD_EATEN", PAIN = "PAIN", STRESS = "STRESSM" }
    CharacterTrait = setmetatable({}, { __index = function(t, k) return k end })
    Perks = { Fitness = "Fitness" }
    IsoPlayer = { allPlayersAsleep = function() return false end }
    local gt = { getMultiplier = function(s) return 2 end, getDeltaMinutesPerDay = function(s) return 3 end,
                 getMinutesPerDay = function(s) return 60 end, getTimeOfDay = function(s) return 8 end,
                 getWorldAgeHours = function(s) return 1 end }
    getGameTime = function() return gt end
    local so = { getStatsDecreaseMultiplier = function(s) return 1 end,
                 getEnduranceRegenMultiplier = function(s) return 1 end }
    getSandboxOptions = function() return so end
    local env = { vals = { THIRST = 0.2, ENDURANCE = 0.7, MORALE = 1, FATIGUE = 0.1 }, gets = {}, sets = {},
                  drunk = {}, asleep = false }
    local stats = {
        get = function(s, k)
            env.gets[k] = (env.gets[k] or 0) + 1
            return env.vals[k] or 0
        end,
        set = function(s, k, v)
            env.sets[k] = (env.sets[k] or 0) + 1
            env.vals[k] = v
        end,
        setLastEndurance = function(s, v) end,
        getNumVeryCloseZombies = function(s) return 0 end,
        getNumChasingZombies = function(s) return 0 end,
    }
    local bd = {
        getThermoregulator = function(s) return nil end,
        setDrunkReductionValue = function(s, v) env.drunk[#env.drunk + 1] = v end,
    }
    local F = function(s) return false end
    local Z = function(s) return 0 end
    local p = {
        getStats = function(s) return stats end,
        getCharacterTraits = function(s) return { get = function(t, k) return false end } end,
        getMoodles = function(s) return { getMoodleLevel = function(m, k) return 0 end } end,
        getBodyDamage = function(s) return bd end,
        isAsleep = function(s) return env.asleep end,
        isGhostMode = F, isSitOnGround = F, isSittingOnFurniture = F, isResting = F,
        IsRunning = F, isPlayerMoving = F, isCurrentState = F, isCurrentlyIdle = F,
        getCurrentSquare = function(s) return nil end, getLastSquare = function(s) return nil end,
        getTotalBlood = Z, getBedType = function(s) return "none" end, getPerkLevel = function(s, k) return 5 end,
        isUnlimitedEndurance = F, setTimeOfSleep = function(s, v) end, getRecoveryMod = function(s) return 1 end,
        getX = Z, getY = Z, getZ = Z, getSleepingTabletEffect = Z, getIdleSquareTime = Z,
        autoDrink = function(s) end,
    }
    env.p = p
    return env
end
"""


@pytest.fixture
def hrt():
    import glob
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    for path in [os.path.join(SHARED_DIR, "NR_Core.lua")] + sorted(glob.glob(os.path.join(SHARED_DIR, "NR_Kernel*.lua"))) + [FAST_HANDLER]:
        with open(path, encoding="utf-8") as fh:
            load(fh.read(), "@" + os.path.basename(path))()
    rt.globals().NutritionRevamp.log.level = 0
    return rt


def _rec(rt, effects=None, acute=None, body=None):
    rec = rt.eval("function() return {} end")()
    if effects is not None:
        rec.effects = rt.table_from(effects)
    if acute is not None:
        rec.acute = rt.table_from(acute)
    if body is not None:
        rec.body = rt.table_from(body)
    return rec


def _handler(rt, record, withIds=True, endFoldOn=None, intoxOwned=None, registered=False):
    env = rt.eval(HANDLER_STUBS)(withIds)
    FAST = rt.globals().NutritionRevamp.server.fast
    if endFoldOn is not None:
        FAST.endFoldOn = endFoldOn
    if intoxOwned is not None:
        FAST.intoxOwned = intoxOwned
    FAST.registered = registered
    h = FAST.adopt("u", env.p)
    assert h is not None, FAST.lastError
    h.record = record
    return env, FAST, h


def _tick(env, FAST, n=1):
    for _ in range(n):
        FAST.handler(env.p)
        assert FAST.stats.failures == 0, FAST.lastError


def _n(tbl, k):
    v = tbl[k]
    return 0 if v is None else v


def test_handler_hoist_ids_flags_and_last_input(hrt):
    env, FAST, h = _handler(hrt, _rec(hrt))
    assert h.PANIC == "PANIC" and h.UNHAPPINESS == "UNHAPPINESS" and h.FOOD_SICKNESS == "FOOD_SICKNESS"
    assert h.TEMPERATURE == "TEMPERATURE" and h.INTOXICATION == "INTOXICATION"
    assert h.effOn is True
    assert hrt.eval("rawequal")(FAST.lastInp["u"], h.inp)   # the same table, no copy (Task 8 reads it)
    assert h.moodFloor.unhappy == 0 and h.moodFloor.panic is None   # only the UNHAPPINESS floor is remembered (the release)
    assert h.out.endurance == 0.7                            # endLast seeded from the stat at hoist
    assert h.endFoldOn is False                              # X35 open: the fold ships unapplied
    assert h.intoxOwned is True                              # X82 settled (gate 2, ruling T4-1)
    assert h.floor(2.5) == 2                                 # math.floor's handle is untouched


def test_handler_fills_the_plan5_inputs(hrt):
    rec = _rec(hrt, effects=dict(fOff=0.03, solAddH=0.15, solMul=0.6, stressTarget=0.25),
               acute=dict(S=0.4, circ=0.05, frozen=False), body=dict(dmod=1.5, rmod=0.8, energyState=1.0))
    env, FAST, h = _handler(hrt, rec, endFoldOn=True)
    _tick(env, FAST)
    i = h.inp
    assert (i.fOwned, i.fFrozen, i.fS, i.fCirc, i.fOff) == (True, False, 0.4, 0.05, 0.03)
    assert (i.solAddH, i.solMul, i.dmod, i.rmod, i.stressTarget) == (0.15, 0.6, 1.5, 0.8, 0.25)
    assert i.endFold is True
    assert env.vals["FATIGUE"] == pytest.approx(0.4 + 0.05 + 0.03, rel=1e-12)   # the owned writer reached the stat


def test_handler_inputs_read_neutral_on_nil_and_nan(hrt):
    nan = float("nan")
    rec = _rec(hrt, effects=dict(fOff=nan, solAddH=nan, solMul=nan, stressTarget=nan),
               acute=dict(S=0.3, circ=nan, frozen=True), body=dict(dmod=nan, rmod=nan))
    env, FAST, h = _handler(hrt, rec, endFoldOn=True)
    _tick(env, FAST)
    i = h.inp
    assert (i.fOwned, i.fFrozen, i.fS, i.fCirc, i.fOff) == (True, True, 0.3, 0, 0)
    assert (i.solAddH, i.solMul, i.dmod, i.rmod, i.stressTarget) == (0, 1, 1, 1, 0)
    # no acute table, or an unreadable S: the Plan 1 FATIGUE arm (never a written 0)
    for acute in (None, dict(S=nan, circ=0.0, frozen=False)):
        env, FAST, h = _handler(hrt, _rec(hrt, acute=acute))
        _tick(env, FAST)
        assert h.inp.fOwned is False and h.inp.endFold is False
        assert h.inp.fS == 0 and h.inp.stressTarget == 0
        assert env.vals["FATIGUE"] > 0.1                     # vanilla's awake accrual ran


def test_handler_panic_floor_rises_holds_and_never_overshoots(hrt):
    rec = _rec(hrt, effects=dict(panicTarget=0.1))
    env, FAST, h = _handler(hrt, rec)
    env.vals["PANIC"] = 0
    _tick(env, FAST)
    assert env.vals["PANIC"] == pytest.approx(RISE_PANIC * S_TICK, rel=1e-12)    # 0.04
    _tick(env, FAST)
    assert env.vals["PANIC"] == pytest.approx(2 * RISE_PANIC * S_TICK, rel=1e-12)
    _tick(env, FAST)
    assert env.vals["PANIC"] == 0.1                                               # capped at the target
    sets = _n(env.sets, "PANIC")
    _tick(env, FAST, 3)
    assert env.vals["PANIC"] == 0.1 and _n(env.sets, "PANIC") == sets             # held: no set at the floor
    env.vals["PANIC"] = 30                                                         # vanilla's own panic above
    _tick(env, FAST)
    assert env.vals["PANIC"] == 30 and _n(env.sets, "PANIC") == sets


def test_handler_floors_read_and_write_nothing_at_target_zero(hrt):
    nan = float("nan")
    for t in (0, nan, None):
        eff = dict(panicTarget=t, unhappyTarget=t, foodSickTarget=t, tempTarget=t, tempAdj=-0.2)
        eff = {k: v for k, v in eff.items() if v is not None}
        env, FAST, h = _handler(hrt, _rec(hrt, effects=eff), intoxOwned=False)
        env.vals.PANIC, env.vals.UNHAPPINESS, env.vals.FOOD_SICKNESS, env.vals.TEMPERATURE = 5, 7, 9, 37
        _tick(env, FAST, 3)
        for k in ("PANIC", "UNHAPPINESS", "FOOD_SICKNESS", "TEMPERATURE", "INTOXICATION"):
            assert _n(env.gets, k) == 0 and _n(env.sets, k) == 0, (t, k)


def test_handler_food_sickness_floor_at_one_level_per_hour(hrt):
    env, FAST, h = _handler(hrt, _rec(hrt, effects=dict(foodSickTarget=30)))
    env.vals["FOOD_SICKNESS"] = 29.99
    _tick(env, FAST)
    assert env.vals["FOOD_SICKNESS"] == 30                                        # 29.99 + 0.0417 capped
    env.vals["FOOD_SICKNESS"] = 10
    _tick(env, FAST)
    assert env.vals["FOOD_SICKNESS"] == pytest.approx(10 + RISE_SICK * S_TICK, rel=1e-12)


def test_handler_unhappiness_floor_and_its_release(hrt):
    rec = _rec(hrt, effects=dict(unhappyTarget=0.1))
    env, FAST, h = _handler(hrt, rec)
    env.vals["UNHAPPINESS"] = 0
    _tick(env, FAST)
    assert env.vals["UNHAPPINESS"] == pytest.approx(RISE_UNHAPPY * S_TICK, rel=1e-12)
    _tick(env, FAST, 3)
    assert env.vals["UNHAPPINESS"] == 0.1 and h.moodFloor.unhappy == 0.1
    # a rise of the target: no release, the floor climbs
    rec.effects.unhappyTarget = 10
    env.vals["UNHAPPINESS"] = 10                                                   # say it reached it
    _tick(env, FAST)
    assert env.vals["UNHAPPINESS"] == 10 and h.moodFloor.unhappy == 10
    env.vals["UNHAPPINESS"] = 14                                                   # vanilla's boredom added 4
    # a fall of the target: the difference released ONCE
    rec.effects.unhappyTarget = 4
    _tick(env, FAST)
    assert env.vals["UNHAPPINESS"] == 8 and h.moodFloor.unhappy == 4
    sets = _n(env.sets, "UNHAPPINESS")
    _tick(env, FAST, 3)
    assert env.vals["UNHAPPINESS"] == 8 and _n(env.sets, "UNHAPPINESS") == sets   # never again
    # a fall to 0 releases, floored at 0, and then reads nothing
    env.vals["UNHAPPINESS"] = 2
    rec.effects.unhappyTarget = 0
    _tick(env, FAST)
    assert env.vals["UNHAPPINESS"] == 0 and h.moodFloor.unhappy == 0
    gets = _n(env.gets, "UNHAPPINESS")
    _tick(env, FAST, 2)
    assert _n(env.gets, "UNHAPPINESS") == gets


def test_a_new_record_at_the_minute_resets_the_unhappiness_floor(hrt):
    # the Task 9 review residual: after a respawn the old floor must not release against the new record
    rec = _rec(hrt, effects=dict(unhappyTarget=4))
    env, FAST, h = _handler(hrt, rec)
    env.vals["UNHAPPINESS"] = 4
    _tick(env, FAST)
    assert h.moodFloor.unhappy == 4
    FAST.onMinute("u", env.p, rec)                                                # the same record: untouched
    assert h.moodFloor.unhappy == 4
    FAST.onMinute("u", env.p, _rec(hrt, effects=dict(unhappyTarget=1)))           # a new record: reset
    assert h.moodFloor.unhappy == 0
    sets = _n(env.sets, "UNHAPPINESS")
    _tick(env, FAST)
    assert env.vals["UNHAPPINESS"] == 4 and _n(env.sets, "UNHAPPINESS") == sets   # no release fired


@pytest.mark.parametrize("adj,target,core,written", [
    (-0.2, 36.8, 37.0, True),       # cold side, core above the target: pulled down
    (-0.2, 36.8, 36.5, False),      # cold side, core already below: its own fall never warmed
    (0.3, 37.3, 37.0, True),        # heat side, core below: pushed up
    (0.3, 37.3, 37.5, False),       # heat side, core above: never cooled
    (0, 37.0, 36.0, False),         # no adjustment: no side
])
def test_handler_temperature_target_only_on_the_offset_side(hrt, adj, target, core, written):
    env, FAST, h = _handler(hrt, _rec(hrt, effects=dict(tempTarget=target, tempAdj=adj)), intoxOwned=False)
    env.vals["TEMPERATURE"] = core
    _tick(env, FAST)
    assert _n(env.gets, "TEMPERATURE") == 1
    assert _n(env.sets, "TEMPERATURE") == (1 if written else 0)
    assert env.vals["TEMPERATURE"] == (target if written else core)


def test_handler_endurance_every_tick_under_the_fold(hrt):
    rec = _rec(hrt, effects=dict(), body=dict(dmod=1.5, rmod=0.8))
    env, FAST, h = _handler(hrt, rec, endFoldOn=True)
    env.vals["ENDURANCE"] = 0.6999                          # vanilla drained 1e-4 since the seed 0.7
    _tick(env, FAST)
    assert _n(env.sets, "ENDURANCE") == 1
    assert env.vals["ENDURANCE"] == pytest.approx(0.7 - 1e-4 * 1.5, rel=1e-12)
    assert h.inp.endLast == 0.7
    e1 = env.vals["ENDURANCE"]
    env.vals["ENDURANCE"] = e1 + 1e-4                        # a regeneration since our write
    _tick(env, FAST)
    assert h.inp.endLast == e1
    assert env.vals["ENDURANCE"] == pytest.approx(e1 + 1e-4 * 0.8, rel=1e-12)
    assert _n(env.sets, "ENDURANCE") == 2


def test_handler_endurance_asleep_only_without_the_fold(hrt):
    for fold, eff in ((False, dict()), (True, None)):       # the switch off, or no effects table yet
        env, FAST, h = _handler(hrt, _rec(hrt, effects=eff, body=dict(dmod=1.5)), endFoldOn=fold)
        env.vals["ENDURANCE"] = 0.6999
        _tick(env, FAST, 2)
        assert h.inp.endFold is False
        assert _n(env.sets, "ENDURANCE") == 0 and env.vals["ENDURANCE"] == 0.6999
        env.asleep = True
        _tick(env, FAST)
        assert _n(env.sets, "ENDURANCE") == 1


def test_handler_intoxication_from_the_target_when_owned(hrt):
    rec = _rec(hrt, effects=dict(intoxTarget=25))
    env, FAST, h = _handler(hrt, rec)
    env.vals["INTOXICATION"] = 31                           # a beer's vanilla jump since the last tick
    _tick(env, FAST)
    assert env.vals["INTOXICATION"] == 25
    _tick(env, FAST, 2)
    assert _n(env.sets, "INTOXICATION") == 3                # every tick
    rec.effects.intoxTarget = float("nan")
    env.vals["INTOXICATION"] = 12
    _tick(env, FAST)
    assert env.vals["INTOXICATION"] == 12                   # a NaN target writes nothing
    env, FAST, h = _handler(hrt, _rec(hrt, effects=dict(intoxTarget=25)), intoxOwned=False)
    env.vals["INTOXICATION"] = 31
    _tick(env, FAST, 2)
    assert env.vals["INTOXICATION"] == 31 and _n(env.sets, "INTOXICATION") == 0
    env, FAST, h = _handler(hrt, _rec(hrt), intoxOwned=True)   # no effects table yet: vanilla's stays
    env.vals["INTOXICATION"] = 31
    _tick(env, FAST)
    assert env.vals["INTOXICATION"] == 31 and _n(env.sets, "INTOXICATION") == 0


def test_handler_drunk_reduction_zeroed_at_hoist_when_owned_and_registered(hrt):
    env, FAST, h = _handler(hrt, _rec(hrt), intoxOwned=True, registered=True)
    assert list(env.drunk.values()) == [0]
    env, FAST, h = _handler(hrt, _rec(hrt), registered=False)          # overlay: vanilla's decay stays
    assert list(env.drunk.values()) == []
    env, FAST, h = _handler(hrt, _rec(hrt), intoxOwned=False, registered=True)
    assert list(env.drunk.values()) == []


def test_handler_install_zeroes_and_uninstall_restores_the_drunk_reduction(hrt):
    env, FAST, h = _handler(hrt, _rec(hrt), intoxOwned=True, registered=False)
    hrt.execute("Hook = { CalculateStats = { Add = function(f) end, Remove = function(f) end } }")
    assert FAST.install() is True
    assert list(env.drunk.values()) == [0]
    FAST.uninstall()
    assert list(env.drunk.values()) == [0, 0.0042]                     # BodyDamage's constructor value, #2919


def test_handler_missing_effect_ids_disable_the_writes_not_the_handler(hrt):
    rec = _rec(hrt, effects=dict(panicTarget=10, unhappyTarget=10, foodSickTarget=30, intoxTarget=25,
                                 tempTarget=36.8, tempAdj=-0.2))
    env, FAST, h = _handler(hrt, rec, withIds=False)
    assert h.effOn is False
    _tick(env, FAST, 3)


def test_handler_limitations_and_region_strings():
    src = open(FAST_HANDLER, encoding="utf-8").read()
    lims = src[src.index("limitations = {"):src.index("local FAST = NR.server.fast")]
    assert "and the effects floors for at most one slow-clock minute" in lims
    assert "X35" in lims and "INTOXICATION" in lims
    region = src[src.index("local function body(h)"):src.index("-- @endfastpath")]
    assert "local E = h.record.effects" in region and "local A = h.record.acute" in region
    assert "inp.endLast = out.endurance" in region
    assert "if dm == nil or dm ~= dm then" in region
    assert "h.setDrunk" not in region                       # the reduction is set at the hoist, never per tick
    assert "math." not in region
