"""The once-a-minute stat writer (Plan 11 Task 14; Decision 1 (c), the hybrid): NR_Server_Writer.lua on the shared
server host. The writer step is driven directly on a crafted record, so each obligation is one assertion: the
seven rise rates saved then zeroed (0, never nil) at the server's OnGameBoot and never at a client's; HUNGER,
THIRST and FATIGUE written once a minute in Mode 1 only; the auto-drink sip folded into the THIRST target and
handed to the pool; the floors stepped by elapsed world age; the writer after the eats and the effects in ORDER;
the boot warning beside Nutrition Makes Sense.

Since Plan 15 Task 6 the HUNGER written is the satiety model's own value, h_model (record.satiety.hModel), through the
calibrated curve (K.hungerCurve). This module tests the model's composition, so boot() takes the curve out by default
(CURVE_OFF, the pre-curve writer: the curve and its inverse the identity), and the written HUNGER reads h_model capped;
boot(curve=True) keeps the shipped curve, and the cases under "the calibrated curve" below check the two together. The
curve's own cases are test_kernel_hunger_curve.py.
"""
import math
import os
import re

import pytest
from .server_host import Host, REPO

ENV = r"""
NR_T.adds.OnGameBoot = {}
Events.OnGameBoot = { Add = function(fn) local l = NR_T.adds.OnGameBoot; l[#l + 1] = fn end, Remove = function(fn) end }
ZomboidGlobals = { HungerIncrease = 9.6e-6, HungerIncreaseWhenWellFed = 0.0, HungerIncreaseWhileAsleep = 1.0e-6,
                   HungerIncreaseWhenExercise = 1.92e-5, ThirstIncrease = 8.0e-6, ThirstSleepingIncrease = 1.0e-6,
                   FatigueIncrease = 3.45e-5, StressDecrease = 3.0e-5 }
SandboxVars = { NR = { Mode = NR_T.mode or 1 } }
CharacterStat = { HUNGER = "HUNGER", THIRST = "THIRST", FATIGUE = "FATIGUE", ENDURANCE = "ENDURANCE",
                  STRESS = "STRESS", UNHAPPINESS = "UNHAPPINESS", FOOD_SICKNESS = "FOOD_SICKNESS", PANIC = "PANIC",
                  TEMPERATURE = "TEMPERATURE", INTOXICATION = "INTOXICATION", NICOTINE_WITHDRAWAL = "NICOTINE_WITHDRAWAL",
                  BOREDOM = "BOREDOM" }
MoodleType = { FOOD_EATEN = "FOOD_EATEN" }
CharacterTrait = { NEEDS_LESS_SLEEP = "NLS", NEEDS_MORE_SLEEP = "NMS", INSOMNIAC = "INS", NIGHT_OWL = "NO",
                   HEARTY_APPETITE = "HA", LIGHT_EATER = "LE" }
NR_T.mods = {}
getActivatedMods = function() return { contains = function(s, id) return NR_T.mods[id] == true end } end
function NR_T.statsPlayer(p, values)
    local st = { v = values, sets = {} }
    st.get = function(s, k) return s.v[k] end
    st.set = function(s, k, x) s.v[k] = x; s.sets[k] = x end
    p.st = st
    p.getStats = function(s) return st end
    p.asleep = false
    p.isAsleep = function(s) return s.asleep end
    p.getMoodles = function(s) return { getMoodleLevel = function(m, k) return 0 end } end
    p.getCharacterTraits = function(s) return { get = function(c, t) return false end } end
    p.drunkReduction = nil
    p.getBodyDamage = function(s) return { setDrunkReductionValue = function(b, v) p.drunkReduction = v end,
                                           getThermoregulator = function(b) return nil end } end
    return p
end
"""

STATS = "{ HUNGER = 0.2, THIRST = 0.3, FATIGUE = 0.1, ENDURANCE = 0.9, STRESS = 0, UNHAPPINESS = 0, FOOD_SICKNESS = 0, PANIC = 0, TEMPERATURE = 37.0, INTOXICATION = 0 }"

RATES = ("HungerIncrease", "HungerIncreaseWhileAsleep", "HungerIncreaseWhenExercise", "ThirstIncrease",
         "ThirstSleepingIncrease", "FatigueIncrease", "HungerIncreaseWhenWellFed")


# The pre-curve writer (tools/replay_live.py's PRE_CURVE, the same override): the model's own value is written, capped.
CURVE_OFF = ("local K = NutritionRevamp.kernel\n"
             "K.hungerCurve.write = function(h, state) return h end\n"
             "K.hungerCurve.inverse = function(H) return H end\n"
             "K.hungerCurve.dip = function(c) return 1 end\n")


def boot(mode=1, curve=False):
    h = Host(extra_env=("NR_T = NR_T or {}\nNR_T.mode = %d\n" % mode) + ENV)
    if not curve:
        h.rt.execute(CURVE_OFF)
    h.fire("OnGameBoot")
    return h


def player(h, name="a"):
    return h.rt.eval("NR_T.statsPlayer")(h.player(name), h.rt.eval(STATS))


# Plan 11c Task 6: the written HUNGER, recomputed in doubles from the kernels' constants at HEAD (NR_Kernel_Satiety.lua,
# NR_Kernel_Deficit.lua): mealRead(M) = 1 - 1 / (1 + 3 (M / MEAL_REQ)^MEAL_STEEP); sated(F, Mn) = 1 - (1 - FULL_WEIGHT F) (1 - Mn),
# MEAL_REQ, MEAL_STEEP and FULL_WEIGHT read off the kernel file (fitted in Plan 11g Task 6c, so no value is re-typed here); hungerTarget(x, es) = clamp((1 - x) es, 0, 1), with no deficit floor since Plan 11g Task 7 fix 1 (ruling T7-1; 0.02 max(0, es - 1) was added from Plan 11f Task 2c fix 1, 1.0 before);
# circadian(h) = 1 + 0.085 cos(2 pi (h - 19.8333) / 24); acuteFactor(S) = 1 - 0.7 S; the writer's composition
# (amendment 3) min(0.69, hungerTarget x circadian x acuteFactor), the 0.69 the hybrid's hungerCap. The writer reads the
# body clock's hour (record.acute.bodyHour under sleep on, K.circadian.hour; Plan 16 Task 4), which the Nutrients step
# advances; step() sets age 100 + minute / 60 and, on a record with an acute table, the clock to fmod(age, 24) as a
# running clock would read, so minute m is hour 4 + m / 60.


def _satiety_constant(name):
    with open(os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Kernel_Satiety.lua"),
              encoding="utf-8") as fh:
        return float(re.search(r"^K\.satiety\.%s = ([0-9.]+)" % name, fh.read(), re.M).group(1))


MEAL_REQ = _satiety_constant("MEAL_REQ")
MEAL_STEEP = _satiety_constant("MEAL_STEEP")
FULL_WEIGHT = _satiety_constant("FULL_WEIGHT")
PROTEIN_FILL = _satiety_constant("PROTEIN_FILL")
MEAL_SEED_MAX = _satiety_constant("MEAL_SEED_MAX")


def _mread(M):
    return 0.0 if M <= 0 else 1 - 1 / (1 + 3 * math.exp(MEAL_STEEP * math.log(M / MEAL_REQ)))


def _circ(hour):
    return 1 + 0.085 * math.cos(6.283185307179586 * (hour - 19.8333) / 24)


def _hunger(M, F=0.6, es=1.0, minute=1, S=0.0):
    x = 1 - (1 - FULL_WEIGHT * F) * (1 - _mread(M))
    target = min(max((1 - x) * es, 0.0), 1.0)
    return min(0.69, target * _circ(math.fmod(100 + minute / 60, 24)) * (1 - 0.7 * min(max(S, 0.0), 1.0)))


# the default record's minute-1 HUNGER: M 6 reads mealRead(6), so H0 = (1 - FULL_WEIGHT x 0.6) x (1 - mealRead(6)), times
# the circadian factor at 04:01 (0.9540165460822252)
H0 = (1 - FULL_WEIGHT * 0.6) * (1 - _mread(6))
H1 = H0 * 0.9540165460822252


def record(h, **over):
    r = h.rt.eval("""{ stomachFill = 0.6, satiety = { M = 6, S = 0, L = 0 }, body = { energyState = 1, rmod = 1 },
        fluids = { thirstTarget = 0.3, autoDrop = 0 }, acute = { S = 0.2, circ = 0.05, frozen = false },
        effects = { fOff = 0.01, panicTarget = 10, stressTarget = 0, unhappyTarget = 0, foodSickTarget = 0,
                    tempTarget = 0, tempAdj = 0, intoxTarget = 0 } }""")
    for k, v in over.items():
        r[k] = v
    return r


def step(h, p, rec, minute, name="a", ctx=None):
    h.T.age = 100.0 + minute / 60
    a = rec.acute
    if h.rt.eval("type")(a) == "table":
        a.bodyOn = True
        a.bodyHour = math.fmod(100 + minute / 60, 24)
    h.NR.server.writer.step(name, p, rec, ctx)


def test_boot_saves_then_zeroes_the_seven_rates_to_zero_never_nil():
    h = boot()
    zg = h.G.ZomboidGlobals
    for k in RATES:
        assert zg[k] == 0, k
    assert zg.StressDecrease == 3.0e-5                       # not a rise rate: untouched
    assert h.NR.vanillaRate("HungerIncrease") == 9.6e-6 and h.NR.server.writer.zeroed is True


def test_the_saved_rates_answer_for_every_key():
    h = boot()
    rates = {k: h.NR.vanillaRate(k) for k in RATES}
    assert rates["HungerIncrease"] == 9.6e-6 and rates["FatigueIncrease"] == 3.45e-5
    assert rates["HungerIncreaseWhenWellFed"] == 0.0 and rates["ThirstSleepingIncrease"] == 1.0e-6
    assert all(v is not None for v in rates.values())


def test_overlay_leaves_the_rates_vanillas():
    h = boot(mode=2)
    assert h.G.ZomboidGlobals.HungerIncrease == 9.6e-6 and h.NR.server.writer.zeroed is False


def test_a_client_boot_changes_nothing():
    h = Host(extra_env="NR_T = NR_T or {}\nNR_T.mode = 1\n" + ENV)
    h.T.server = False
    h.fire("OnGameBoot")
    assert h.G.ZomboidGlobals.HungerIncrease == 9.6e-6


def test_a_minute_writes_hunger_thirst_and_fatigue():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    s = p.st.sets
    assert s.HUNGER == pytest.approx(H1) and s.THIRST == pytest.approx(0.3) and s.FATIGUE == pytest.approx(0.26)
    assert p.drunkReduction == 0
    assert h.NR.server.writer.stats.writes == 1


def test_the_stomach_fill_drives_hunger_through_its_weight():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.stomachFill = 0.0
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(_hunger(6, F=0.0))           # (1 - mealRead(6)) x c(04:01)
    assert p.st.sets.HUNGER == pytest.approx((1 - _mread(6)) * 0.9540165460822252)
    p2 = player(h, "b")
    rec2 = record(h)
    rec2.stomachFill = float("nan")                                        # a non-finite fill reads empty
    step(h, p2, rec2, 1, name="b")
    assert p2.st.sets.HUNGER == pytest.approx((1 - _mread(6)) * 0.9540165460822252)


def test_an_auto_drink_sip_is_folded_and_handed_to_the_pool():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)                                     # writes THIRST 0.3
    p.st.v.THIRST = 0.1                                    # vanilla's autoDrink drank between the writes (#3382)
    step(h, p, rec, 2)
    assert rec.fluids.autoDrop == pytest.approx(0.2)
    assert p.st.sets.THIRST == pytest.approx(0.1)          # the target less the sip: no re-drink at the write
    assert h.NR.server.writer.stats.sips == 1


def test_float_noise_thirst_drop_is_not_a_sip():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)                                     # writes THIRST 0.3
    p.st.v.THIRST = 0.3 - 1e-10                            # float noise seen live (x281-x284)
    step(h, p, rec, 2)
    assert rec.fluids.autoDrop == 0
    assert h.NR.server.writer.stats.sips == 0
    p.st.v.THIRST = p.st.sets.THIRST - 0.1                 # a real drink
    step(h, p, rec, 3)
    assert rec.fluids.autoDrop == pytest.approx(0.1)
    assert h.NR.server.writer.stats.sips == 1


def test_a_small_real_sip_is_still_a_sip():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    p.st.v.THIRST = p.st.sets.THIRST - 1e-3                # a small real sip, far above SIP_EPS (guards its upper bound)
    step(h, p, rec, 2)
    assert rec.fluids.autoDrop == pytest.approx(1e-3)
    assert h.NR.server.writer.stats.sips == 1


def test_a_landed_intake_is_never_counted_as_a_sip():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    p.st.v.THIRST = 0.1
    h.NR.server.intake.landed["a"] = True
    step(h, p, rec, 2)
    assert rec.fluids.autoDrop == 0 and h.NR.server.intake.landed["a"] is None


def test_the_intake_marks_a_landing():
    h = boot()
    rec = record(h)
    rec.stomach = h.K.stomach.new()                       # the landing's preconditions (IN.readAfterAndLand)
    rec.pool = h.K.vector.new()
    h.NR.server.intake.land(rec, "a", h.K.vector.new())
    assert h.NR.server.intake.landed["a"] is True


def test_panic_is_held_at_its_floor_once_a_minute():
    h = boot()
    p = player(h)
    rec = record(h)
    p.st.v.PANIC = 8.7444
    step(h, p, rec, 1)
    assert p.st.sets.PANIC == 10


def test_overlay_writes_the_floors_but_not_the_three_stats():
    h = boot(mode=2)
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER is None and p.st.sets.THIRST is None and p.st.sets.FATIGUE is None
    assert p.st.sets.PANIC == 10
    p.st.v.THIRST = 0.1                                    # Overlay: vanilla owns THIRST, no sip is captured
    step(h, p, rec, 2)
    assert rec.fluids.autoDrop == 0 and h.NR.server.writer.stats.sips == 0


def test_a_falling_unhappiness_target_releases_its_fall_once():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.effects.unhappyTarget = 40
    p.st.v.UNHAPPINESS = 40
    step(h, p, rec, 1)                                     # held at 40: nothing to write, the target remembered
    rec.effects.unhappyTarget = 10
    step(h, p, rec, 2)
    assert p.st.sets.UNHAPPINESS == pytest.approx(10)      # 40 less the target's fall of 30 (T1-2)


def test_the_sip_is_measured_from_the_written_value_not_the_read_one():
    h = boot()
    p = player(h)
    rec = record(h)
    p.st.v.THIRST = 0.5                                    # the pre-write read
    step(h, p, rec, 1)                                     # writes the target, 0.3
    assert p.st.sets.THIRST == pytest.approx(0.3)
    p.st.v.THIRST = 0.1                                    # a drink between the writes
    step(h, p, rec, 2)
    assert rec.fluids.autoDrop == pytest.approx(0.2)       # 0.3 written less 0.1, not 0.5 read less 0.1


def test_a_sip_adds_to_a_drop_still_pending():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    rec.fluids.autoDrop = 0.05                              # not yet landed by Nutrients
    p.st.v.THIRST = 0.1
    step(h, p, rec, 2)
    assert rec.fluids.autoDrop == pytest.approx(0.25)


def test_a_frozen_sleep_state_leaves_fatigue_alone():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.acute.frozen = True
    step(h, p, rec, 1)
    assert p.st.sets.FATIGUE is None and p.st.sets.HUNGER == pytest.approx(H1)


def test_asleep_the_endurance_regeneration_is_scaled_by_rmod():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.body.rmod = 0.5
    p.asleep = True
    p.st.v.ENDURANCE = 0.5
    step(h, p, rec, 1)                                     # no last value yet: nothing written
    assert p.st.sets.ENDURANCE is None
    p.st.v.ENDURANCE = 0.6                                  # vanilla regenerated 0.1 between the writes
    step(h, p, rec, 2)
    assert p.st.sets.ENDURANCE == pytest.approx(0.55)


def test_the_effects_writes_reach_their_stats():
    h = boot()
    p = player(h)
    rec = record(h)
    E = rec.effects
    E.tempTarget, E.tempAdj, E.intoxTarget, E.stressTarget, E.foodSickTarget = 37.5, 0.5, 3.0, 0.2, 30
    p.st.v.STRESS = 0.1
    step(h, p, rec, 1)
    step(h, p, rec, 2)
    s = p.st.sets
    assert s.TEMPERATURE == 37.5 and s.INTOXICATION == 3.0
    assert s.STRESS == pytest.approx(0.1 + 5.0e-5 * 60) and s.FOOD_SICKNESS == pytest.approx(25 / 3600 * 60)


def test_the_floors_step_by_elapsed_world_age():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.effects.unhappyTarget = 40
    step(h, p, rec, 1)
    step(h, p, rec, 31)                                    # thirty game minutes later
    assert p.st.sets.UNHAPPINESS == pytest.approx(22 / 3600 * 1800)


def test_an_unreadable_world_age_skips_the_minute():
    h = boot()
    p = player(h)
    rec = record(h)
    h.T.age = float("nan")
    h.NR.server.writer.step("a", p, rec, None)
    assert p.st.sets.HUNGER is None and h.NR.server.writer.stats.skipped == 1


def test_a_player_with_no_stats_object_is_left_alone():
    h = boot()
    rec = record(h)
    h.T.age = 100.0
    h.NR.server.writer.step("a", h.player("a"), rec, None)
    assert h.NR.server.writer.h["a"] is None and h.NR.server.writer.stats.writes == 0


def test_a_new_player_object_is_hoisted_again():
    h = boot()
    rec = record(h)
    p1 = player(h)
    step(h, p1, rec, 1)
    p2 = player(h)
    step(h, p2, rec, 2)                                    # a new hoist (ruling C-1); M is Kinetics' to clear (T4-3)
    assert h.G.rawequal(h.NR.server.writer.h["a"].p, p2) and p2.st.sets.HUNGER == pytest.approx(_hunger(6, minute=2))


def test_a_departure_drops_the_handles():
    h = boot()
    p = player(h)
    step(h, p, record(h), 1)
    for fn in h.NR.server.players.onDeparture.values():
        fn("a")
    assert h.NR.server.writer.h["a"] is None and h.NR.server.writer.inp["a"] is None


def test_the_writer_runs_after_the_eats_and_the_effects():
    h = Host()
    order = [h.NR.server.minute.ORDER[i] for i in range(1, len(h.NR.server.minute.ORDER) + 1)]
    assert order.index("writer") > order.index("nutrients") and order.index("writer") > order.index("effects")
    assert "fast" not in order and order[-1] == "store"
    assert h.G.rawequal(h.NR.server.minute.steps["writer"], h.NR.server.writer.step)


def test_the_effects_step_reads_the_writers_engine_reads():
    h = boot()
    p = player(h)
    step(h, p, record(h), 1)
    assert h.NR.server.writer.inp["a"].endurance == pytest.approx(0.9)
    assert h.NR.server.writer.inp["a"].endFold is None       # the endurance fold's flag, never on, is gone


def test_nutrition_makes_sense_draws_one_boot_warning():
    h = Host(extra_env="NR_T = NR_T or {}\n" + ENV + "\nNR_T.mods.NutritionMakesSense = true\n")
    lines = [s for s in h.printed() if "Nutrition Makes Sense is loaded" in s]
    assert len(lines) == 1 and h.NR.server.writer.stats.nms is True
    h2 = Host(extra_env="NR_T = NR_T or {}\n" + ENV)
    assert not [s for s in h2.printed() if "Nutrition Makes Sense" in s]


def test_the_warning_reaches_a_quiet_log():
    h = Host(extra_env="NR_T = NR_T or {}\n" + ENV
             + "\nSandboxVars.NR.LogLevel = 1\nNR_T.mods.NutritionMakesSense = true\n")
    assert h.NR.log.level == 1
    assert len([s for s in h.printed() if "Nutrition Makes Sense is loaded" in s]) == 1


def test_the_warning_keeps_the_compatibility_rows_promise():
    with open(os.path.join(REPO, "mod", "NutritionRevamp", "COMPATIBILITY.md"), encoding="utf-8") as fh:
        row = [ln for ln in fh.read().splitlines() if ln.startswith("| Nutrition Makes Sense")]
    assert len(row) == 1 and "the server log warns at boot when both are loaded" in row[0]
    h = Host(extra_env="NR_T = NR_T or {}\n" + ENV + "\nNR_T.mods.NutritionMakesSense = true\n")
    line = [s for s in h.printed() if "Nutrition Makes Sense is loaded" in s][0]
    assert "WARNING" in line and "COMPATIBILITY.md" in line and "run one of them" in line


def test_a_runtime_mode_change_is_logged_and_changes_no_rate():
    h = boot()
    h.G.SandboxVars.NR.Mode = 2
    h.NR.server.readOptions("poll")
    assert any("takes effect at the next restart" in s for s in h.printed())
    assert h.G.ZomboidGlobals.HungerIncrease == 0


def test_the_backslash_entry_form_draws_the_warning_too_defensive():
    # Defensive: on a dedicated server every getActivatedMods() entry is the bare id (#3569: GameServer.main strips
    # every backslash from Mods=), so the server never produces this form; a client's list was not read, and the
    # second check costs nothing.
    h = Host(extra_env="NR_T = NR_T or {}\n" + ENV + "\nNR_T.mods['\\\\NutritionMakesSense'] = true\n")
    assert len([s for s in h.printed() if "Nutrition Makes Sense is loaded" in s]) == 1


def test_the_self_report_names_the_boot_mode_not_the_polled_one():
    h = boot()
    h.G.SandboxVars.NR.Mode = 2
    h.NR.server.readOptions("poll")
    line = h.NR.selfReport("server")
    assert " mode=managed " in line and " rates=zeroed " in line
    assert " limitations=%d " % len(h.NR.server.writer.limitations) in line and " hook=" not in line


def test_the_satiety_bulk_option_and_task_15s_writer_pieces_are_retired():
    h = boot()
    assert h.NR.server.options.satietyBulk is None
    assert h.NR.server.writer.rates is None
    h.G.SwipeStatePlayer = h.rt.eval("{ instance = function() return NR_T end }")
    p = player(h)
    step(h, p, record(h), 1)
    assert h.NR.server.writer.h["a"].swipe is not None   # the swing handle stays: it marks resistance work (ruling T6-2)
    txt = os.path.join(REPO, "mod", "NutritionRevamp", "42.21", "media", "sandbox-options.txt")
    js = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "Translate", "EN",
                      "Sandbox.json")
    for path in (txt, js):
        with open(path, encoding="utf-8") as fh:
            assert "SatietyBulk" not in fh.read(), path


LIMITATION_FOUR = (
    "HUNGER, THIRST and FATIGUE are written once a game minute; an eat or a drink shows at once and the next write "
    "overwrites it with the satiety target, hungerTarget(sated(F, mealRead(M)), energyState) x the circadian factor x"
    " the acute exercise factor x the sleep-debt factor x the nicotine factor (the model's h_model), written through"
    " the calibrated curve (K.hungerCurve: a satisfying meal reads about 0 and Peckish and Hungry return on vanilla's"
    " cadence; unfed, the morning dip is taken out and HUNGER never falls; at the minute the meal pool empties in "
    "the morning, HUNGER steps up by the circadian dip (under 0.01); a level steps down only 0.02 under its "
    "threshold) and capped at 0.69 below starvation (K.hybrid.caps): F is the stomach's "
    "fullness mass (its satiety mass plus the protein term) over its 730 g comfortable maximum, counted on to the "
    "1100 g hard capacity, drunk liquid counting at 0.279 of its mass, and M the meal pool, the weighted kcal eaten, "
    "fed in full at the eat and cleared on game time asleep or awake by the kinetics step while the writer seeds and "
    "reads it, so h_model never reaches 0 after a meal, and a fresh record's first minute writes the vanilla HUNGER it "
    "finds (read back through the curve's inverse); a vanilla HUNGER under what the meal pool alone can write on an "
    "empty stomach (the curve of hungerTarget(0.786, energy state) times the minute's factors, the seed's cap "
    "MEAL_SEED_MAX) lands a real meal before that minute, the curve fit's plate of the guide's foods sized to the least "
    "kcal whose first write is within the dead zone of it, at most one 667 kcal plate, its kcal and nutrients counted "
    "like any meal (W.seedPlate);"
    " protein fills the satiety fullness while it is in the stomach (a fitted game choice); an eat another mod makes "
    "through a direct Eat call reaches the stomach and M through the reconcile path a minute late and as its macros "
    "only (no water or fibre mass), and a drink another mod makes through a direct DrinkFluid call outside the "
    "intake's wraps is not seen; an eat in a fresh record's first minute, before the writer has seeded M, is not fed "
    "into M (it shows only through the HUNGER the seed reads); the exercise share of the energy deficit enters hunger"
    " through a lag of weeks, so a regular exerciser who eats to balance reads lower hunger for weeks; heavy work the"
    " model does not class as vigorous (neither the swing state nor the heavy-work band) overshoots the hunger rise "
    "of a heavy labour deficit (S1325); past 730 g in the stomach the mod's own Overfull moodle rises in four levels "
    "to 1100 g, and at its level 4 the food-timer bridge holds vanilla's FOOD_EATEN timer at its level 3, so "
    "vanilla's own refusal greys the eat menu and the double-click eat (a drink with no food value is not refused) (W.foodTimer), "
    "and the server refuses an eat queued past the menu at Overfull 4 (NR_Server_IntakeGuard; a drink from a fluid container and a direct Eat call another mod makes are not refused); a drink lands sip by sip over its action, and drunk water leaves at a half-time of 13 min plus 0.12 min "
    "per kcal the drink itself carried, whatever food sits beside it (Plan 15 Task 14b), so a large drink right "
    "after a full meal can still hold level 4 for a few minutes; fibre sates only through its mass, and carbohydrate, sugar and starch take one "
    "weight per kcal (the evidence is mixed or absent), and fat and protein take fitted "
    "weights per kcal (0.879 and 2.50 times carbohydrate's, game choices of the fit); a vanilla HUNGER above "
    "the fullness "
    "ceiling, hungerTarget(0.5 F, energy state), that is (1 - 0.5 F) x es, times the minute's"
    " circadian, acute, sleep and nicotine factors, seeds an empty meal pool, so a fresh character's first written "
    "HUNGER drops to that ceiling's curve value; short sleep raises hunger by a factor capped at the pooled size, whether a step or"
    " graded is unsettled; the sleep factor steps at the acute record's 24 h window close, not at waking, so a short "
    "night that straddles the close reaches hunger in two steps a day apart; after a short night, nights of exactly "
    "the need repay nothing, so the rise holds until a longer night repays half its excess; right at a bout's end the"
    " acute term reads deeper than the pooled immediate-post effect; glycogen depletion no longer "
    "raises hunger, and a trailing-24 h deficit is bounded by the day's expenditure, so a sedentary fast plateaus at "
    "es about 1.19 to 1.29 by body size (1.2456 for the 70 kg man) from about 36 h, the balance term's cap is "
    "reached only by very heavy work, and higher energy "
    "states come from fat depletion; heat's lowering of intake is not modelled (cold reaches "
    "hunger through its expenditure); sugary drinks, ketosis, alcohol's aperitif effect and eating rate are neutral; "
    "an airy food sates by its weight plus 0.05 of its plate volume beyond its weight (a game choice; the physical "
    "fill and the Overfull moodle stay on mass); injury adds no expenditure; nicotine withdrawal raises hunger by a factor anchored on "
    "one small trial, fading over 26 weeks; a smoker who keeps smoking reads the rise between smokes, unfaded, and a "
    "character first seen in withdrawal reads none until a smoke; the deficit drive is fitted on the deficit "
    "studies alone, Karl 2021's well-fed arm held inside its band by the meal pool and the stomach's fill past 730 g "
    "rather than by the gut hormones the paper credits, so its post-meal troughs stay shallower than the study's; "
    "every Fitness set minute is vigorous resistance work for the acute term from the server's exercise flag, "
    "whatever the exercise and its billed MET (a light stretch and burpees alike)")


def test_limitation_four_names_the_overwrite_and_the_meal_pool():
    lim = list(Host().NR.server.writer.limitations.values())
    assert len(lim) == 15                                  # the self-report prints the count: 15 since Plan 15 Task 8 fix 1 (the long-day line; 14 since Task 5, option B's; 13 since Plan 11g Task 8, MC-29, ruling T8-1)
    assert lim[3] == LIMITATION_FOUR


# --- Plan 11 Task 19: the dry seam the harness's ghost runs use --------------------------------------------------

def test_a_dry_writer_computes_and_sets_nothing():
    h = boot()
    W = h.NR.server.writer
    p = player(h)
    rec = record(h)
    rec.fluids.autoDrop = 0.05
    h.NR.server.intake.landed["a"] = True
    W.dry = True
    step(h, p, rec, 1)
    p.st.v.THIRST = 0.1                                    # a fall a live writer would book as a sip
    step(h, p, rec, 2)
    assert len(list(p.st.sets.keys())) == 0                # no stat written
    assert rec.satiety.M == 6 and rec.satiety.S == 0   # the meal pool neither cleared nor seeded
    assert rec.fluids.autoDrop == 0.05                     # no sip folded into the pool
    assert h.NR.server.intake.landed["a"] is True          # the landing mark left for the real step
    assert W.h["a"] is None and W.inp["a"] is None         # nothing hoisted, no engine read
    assert W.stats.writes == 0 and W.stats.seeded == 0 and W.stats.skipped == 0
    assert W.stats.dry == 2                                # the dry minutes are counted on their own


def test_the_dry_seam_is_nil_by_default_and_a_cleared_seam_writes_again():
    h = boot()
    W = h.NR.server.writer
    assert W.dry is None and W.stats.dry == 0
    p = player(h)
    rec = record(h)
    W.dry = True
    step(h, p, rec, 1)
    W.dry = None
    step(h, p, rec, 2)
    assert p.st.sets.HUNGER is not None and W.stats.writes == 1


def test_a_dry_seam_set_to_anything_but_true_leaves_the_writer_live():
    h = boot()
    p = player(h)
    rec = record(h)
    h.NR.server.writer.dry = 1                             # only true dries the writer
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(H1) and h.NR.server.writer.stats.writes == 1


# --- Task 20 fix: the well-fed rate from the saved table (review A's F4), another mod re-assigning the rates -------

def test_the_well_fed_rate_is_the_one_saved_at_boot_not_the_default():
    h = Host(extra_env="NR_T = NR_T or {}\nNR_T.mode = 1\n" + ENV + "\nZomboidGlobals.HungerIncreaseWhenWellFed = 3.0e-6\n")
    h.fire("OnGameBoot")
    assert h.NR.vanillaRate("HungerIncreaseWhenWellFed") == 3.0e-6 and h.G.ZomboidGlobals.HungerIncreaseWhenWellFed == 0


def test_a_limitation_names_another_mod_re_assigning_the_rates():
    lim = list(Host().NR.server.writer.limitations.values())
    hits = [x for x in lim if "another mod" in x and "OnGameBoot" in x and "ZomboidGlobals" in x]
    assert len(hits) == 1
    assert "vanilla's drift" in hits[0] and "between the writer's minute writes" in hits[0]
    assert hits[0].startswith("another mod whose OnGameBoot handler runs after ours and sets ZomboidGlobals' hunger, "
                              "thirst or fatigue rise keys (before ZomboidGlobals.Load, #3364) restores vanilla's "
                              "drift between the writer's minute writes: HUNGER, THIRST and FATIGUE climb")


# --- Plan 11c Task 6: satiety from physiology in the writer (amendments 3 and 4) -----------------------------------

def test_a_record_with_p_writes_hunger_target_times_circadian_times_acute():
    h = boot()
    p = player(h)
    step(h, p, record(h), 1)
    assert p.st.sets.HUNGER == pytest.approx(H1)
    assert H1 == pytest.approx(_hunger(6))
    assert H1 == pytest.approx(H0 * _circ(4 + 1 / 60))


def test_the_energy_term_raises_the_hunger_of_a_deficit():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.body.energyState = 1.2                             # no deficit floor since Plan 11g Task 7 fix 1 (0.02 before Task 7)
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(H0 * 1.2 * 0.9540165460822252)
    assert p.st.sets.HUNGER == pytest.approx(_hunger(6, es=1.2))


def test_the_written_hunger_is_capped_at_0_69():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.stomachFill = 0.0
    rec.satiety.M = 0.0                                    # an empty stomach and an empty M: target 1 x c
    rec.body.energyState = 2.0
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(0.69)


def test_a_record_without_satiety_seeds_p_from_hunger():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.31
    rec = record(h)
    rec.satiety = None
    step(h, p, rec, 1)
    assert h.NR.server.writer.stats.seeded == 1
    assert rec.satiety.M == pytest.approx(h.K.satiety.seedMeal(0.31 / _circ(4 + 1 / 60), 0.6, 1))
    assert rec.satiety.S == 0 and rec.satiety.L == 0
    assert p.st.sets.HUNGER == pytest.approx(0.31)


@pytest.mark.parametrize("minute", [1, 721])               # 04:01 and 16:01: the circadian factor 0.954 and 1.046
def test_a_new_record_writes_back_the_hunger_it_read(minute):
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.4
    rec = h.K.store.new("a", 100.0)
    assert rec.satiety is None
    step(h, p, rec, minute)
    assert p.st.sets.HUNGER == pytest.approx(0.4)
    step(h, p, rec, minute + 1)
    assert h.NR.server.writer.stats.seeded == 1                            # seeded once, then stepped


def test_a_new_record_with_acute_suppression_writes_back_the_hunger_it_read():
    # S 0.5 (a bout just ended): the seed inverts hunger / (circadian x acuteFactor(0.5)) = 0.4 / (0.954 x 0.65), so
    # the first write is the 0.4 read, and the same holds for a HUNGER near the cap (0.6 / 0.65 = 0.92 before the cap)
    for hunger in (0.4, 0.6):
        h = boot()
        p = player(h)
        p.st.v.HUNGER = hunger
        rec = h.K.store.new("a", 100.0)
        rec.satiety = h.rt.eval("{ S = 0.5 }")
        step(h, p, rec, 1)
        assert p.st.sets.HUNGER == pytest.approx(hunger)
        assert rec.satiety.S == 0.5 and rec.satiety.M is not None


def test_a_stepped_m_survives_a_restart():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    saved = h.K.store.inputsOnly(rec)
    saved.body = None                                                       # the stand-in body is no stored body
    back = h.K.store.load(saved, None, None)
    assert back.satiety.M == pytest.approx(6)
    assert back.satiety.S == 0 and back.satiety.L == 0
    back.stomachFill = 0.6                                                  # kinetics stamps it each minute
    back.body = h.rt.eval("{ energyState = 1, rmod = 1 }")
    p2 = player(h)                                                          # the restart: a new object, a new hoist
    step(h, p2, back, 1)
    assert h.NR.server.writer.stats.seeded == 0 and p2.st.sets.HUNGER == pytest.approx(H1)


def test_a_non_finite_or_absent_m_is_seeded_again():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.31
    rec = record(h)
    rec.satiety.M = float("nan")
    step(h, p, rec, 1)
    W = h.NR.server.writer
    assert p.st.sets.HUNGER == pytest.approx(0.31) and W.stats.seeded == 1
    assert W.stats.guarded == 1                                             # a non-finite M is a heal too
    p2 = player(h, "b")
    p2.st.v.HUNGER = 0.31
    rec2 = record(h)
    rec2.satiety.M = None
    step(h, p2, rec2, 1, name="b")
    assert p2.st.sets.HUNGER == pytest.approx(0.31) and W.stats.seeded == 2
    assert W.stats.guarded == 1                                             # an absent M is a seed, not a heal


# Plan 11g Task 4 fix 1 (ruling T4-3): M's clearance is Kinetics' (test_kinetics.py: the half-life, the appetite
# traits, the sandbox multiplier, sleep, the 60-minute cap and a restart); the writer seeds M at first sight and reads
# it, so a seeded M passes every writer step unchanged.

def test_the_writer_leaves_m_to_kinetics_over_game_time():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 61)
    step(h, p, rec, 121)                                                    # two hour-long steps
    assert rec.satiety.M == 6
    assert p.st.sets.HUNGER == pytest.approx(_hunger(6, minute=121))


@pytest.mark.parametrize("trait,sd,asleep", [(None, 1, True), ("HA", 1, False), ("LE", 1, False), (None, 2, False)])
def test_no_trait_sandbox_or_sleep_read_moves_m_in_the_writer(trait, sd, asleep):
    h = boot()
    if sd != 1:
        h.G.getSandboxOptions = h.rt.eval("function() return { getStatsDecreaseMultiplier = function(s) return %r end } end"
                                          % float(sd))
    p = player(h)
    p.asleep = asleep
    if trait is not None:
        p.getCharacterTraits = h.rt.eval("function(s) return { get = function(c, t) return t == '%s' end } end" % trait)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 43)
    assert rec.satiety.M == 6


def test_a_gap_over_sixty_minutes_leaves_m_to_kinetics():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 181)                                                    # three game hours since the last write
    assert rec.satiety.M == 6


def test_overlay_writes_no_hunger_and_leaves_m():
    h = boot(mode=2)
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 43)
    assert p.st.sets.HUNGER is None and rec.satiety.M == 6


def test_the_writer_never_steps_m():
    # the writer calls neither the clearance nor the feed: a NaN from either would surface in M or in guarded
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    nan = h.rt.eval("function() return 0 / 0 end")
    orig = (h.K.satiety.mealClear, h.K.satiety.mealFeed)
    h.K.satiety.mealClear = nan
    h.K.satiety.mealFeed = nan
    try:
        step(h, p, rec, 2)
    finally:
        h.K.satiety.mealClear, h.K.satiety.mealFeed = orig
    assert rec.satiety.M == 6 and h.NR.server.writer.stats.guarded == 0
    assert p.st.sets.HUNGER == pytest.approx(_hunger(6, minute=2))


def swinging(h, p):
    h.G.SwipeStatePlayer = h.rt.eval("{ instance = function() return NR_T end }")   # any unique handle
    p.isCurrentState = h.rt.eval("function(s, st) return st == NR_T end")


def test_a_swing_steps_the_acute_state_as_resistance_work():
    # ACUTE_KIND.resistance 0.5, ACUTE_HALF_LIFE_H 0.5: 30 swinging minutes take S from 0 to 0.5 x (1 - 2^-1) = 0.25,
    # so the factor is 1 - 0.7 x 0.25 = 0.825
    h = boot()
    p = player(h)
    swinging(h, p)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 31)
    assert rec.satiety.S == pytest.approx(0.25)
    assert rec.satiety.M == 6                                               # M is Kinetics' to clear (T4-3)
    assert p.st.sets.HUNGER == pytest.approx(_hunger(6, minute=31, S=0.25))


def test_the_heavy_work_band_steps_the_acute_state_as_aerobic_work():
    # Metabolism's stamp body.met at the Compendium's HeavyWork 6.0 or above (the swing state absent): ACUTE_KIND
    # .aerobic 1, so 30 minutes take S to 1 x (1 - 2^-1) = 0.5; just under the band nothing moves
    h = boot()
    p = player(h)
    rec = record(h)
    rec.body.met = 6.0
    step(h, p, rec, 1)
    step(h, p, rec, 31)
    assert rec.satiety.S == pytest.approx(0.5)
    p2 = player(h, "b")
    rec2 = record(h)
    rec2.body.met = 5.99
    step(h, p2, rec2, 1, name="b")
    step(h, p2, rec2, 31, name="b")
    assert rec2.satiety.S == 0


def kind_step(h, p, rec, minute, cls=None, exercising=False, name="a"):
    ctx = h.rt.table()
    ctx.activityClass = cls
    ctx.exercising = exercising
    h.T.age = 100.0 + minute / 60
    h.NR.server.writer.step(name, p, rec, ctx)


@pytest.mark.parametrize("cls,met", [("Fitness", 6.0), ("FitnessHeavy", 9.0), ("ForestryAxe", 6.5), ("ClimbRope", 8.0)])
def test_resistance_type_classes_step_the_acute_state_as_resistance_work(cls, met):
    # Ruling T6-2 (S1301, S1305: resistance suppresses less): the metabolism class, not the MET alone, names the kind.
    # Billed at or above the heavy-work band, Fitness, FitnessHeavy, ForestryAxe and ClimbRope (a chop, T6-3) are resistance: 30 min
    # take S to ACUTE_KIND.resistance 0.5 x (1 - 2^-1) = 0.25, not the aerobic 0.5
    h = boot()
    p = player(h)
    rec = record(h)
    rec.body.met = met
    kind_step(h, p, rec, 1, cls)
    kind_step(h, p, rec, 31, cls)
    assert rec.satiety.S == pytest.approx(0.25)


@pytest.mark.parametrize("cls,met", [("HeavyWork", 6.0), ("Running10kmh", 9.3)])
def test_the_other_heavy_classes_stay_aerobic_work(cls, met):
    h = boot()
    p = player(h)
    rec = record(h)
    rec.body.met = met
    kind_step(h, p, rec, 1, cls)
    kind_step(h, p, rec, 31, cls)
    assert rec.satiety.S == pytest.approx(0.5)


def test_a_fitness_exercise_in_progress_is_resistance_work_whatever_the_class():
    # the engine classifies a 6.0 rate as HeavyWork, so the exercise flag (Fitness.getCurrentExe) is what names it
    h = boot()
    p = player(h)
    rec = record(h)
    rec.body.met = 6.0
    kind_step(h, p, rec, 1, "HeavyWork", True)
    kind_step(h, p, rec, 31, "HeavyWork", True)
    assert rec.satiety.S == pytest.approx(0.25)


def test_a_swing_minutes_hunger_is_never_above_the_same_minute_idle():
    # ruling 11c-29 (3): while exercising, hunger takes the non-exercising rate or lower; under a written target the
    # acute factor (at most 1) makes it hold by construction, minute by minute, here pinned over a bout and its tail
    h = boot()
    idle, busy = player(h, "a"), player(h, "b")
    swinging(h, busy)
    ri, rb = record(h), record(h)
    for m in range(1, 92, 5):
        if m == 61:
            busy.isCurrentState = h.rt.eval("function(s, st) return false end")   # the bout ends at minute 61
        step(h, idle, ri, m, name="a")
        step(h, busy, rb, m, name="b")
        assert busy.st.sets.HUNGER <= idle.st.sets.HUNGER + 1e-15, m
    assert busy.st.sets.HUNGER < idle.st.sets.HUNGER                       # the tail still shows the suppression


def test_a_non_finite_acute_state_or_lag_heals_and_counts():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.satiety.S = float("nan")
    rec.satiety.L = -5.0
    step(h, p, rec, 1)
    assert rec.satiety.S == 0 and rec.satiety.L == 0
    assert h.NR.server.writer.stats.guarded == 2
    p2 = player(h, "b")
    rec2 = record(h)
    rec2.satiety.S = 3.0                                                    # out of range: clamped, not counted
    step(h, p2, rec2, 1, name="b")
    assert rec2.satiety.S == 1 and h.NR.server.writer.stats.guarded == 2
    assert p2.st.sets.HUNGER == pytest.approx(H1 * 0.3)                     # acuteFactor(1) = 1 - 0.7


# --- Plan 11c close (ruling C-1): the writer's step across a reconnect or a restart ---------------------------------
# The writer stamps its last step's world age on record.satiety.t (game hours). A new IsoPlayer object (a reconnect, a
# respawn) or a restart re-hoists h with no ageH, so the step reads the gap from that stamp, clamped at maxStepS (60
# min) as a same-object gap is: S decays toward 0 at ACUTE_DECAY_HALF_LIFE_H 0.15 h over one hour (ruling 11d-1). M's
# clearance across the gap is Kinetics' (its stored kineticsAge, ruling T4-3), so the writer leaves M as it finds it.

def _fed(h, name="a"):
    p = player(h, name)
    rec = record(h)
    rec.satiety.M = 600.0
    rec.satiety.S = 1.0
    step(h, p, rec, 1, name=name)
    step(h, p, rec, 2, name=name)
    return p, rec


def test_the_writer_stamps_its_step_age_on_the_satiety_record():
    h = boot()
    p = player(h)
    rec = record(h)
    assert rec.satiety.t is None                                            # the fixture's record has no stamp
    step(h, p, rec, 1)
    assert rec.satiety.t == pytest.approx(100.0 + 1 / 60)
    assert rec.satiety.M == 6                                               # no stamp: the first minute steps 0
    step(h, p, rec, 7)
    assert rec.satiety.t == pytest.approx(100.0 + 7 / 60)


def test_a_reconnect_keeps_s_where_the_same_object_steps_it():
    # the review's probe2 under Plan 16 Task 2: a player away 180 game minutes returns as a new object, and the store's
    # resume moved satiety.t to the return, so S steps nothing; the same object handed a 180-minute step (a stall the
    # pipeline did not sub-step) is held to the writer's own 60-minute guard (maxStepS)
    h = boot()
    p, same = _fed(h, "a")
    M2, S2 = same.satiety.M, same.satiety.S
    step(h, p, same, 182, name="a")                                         # same object, 180 minutes later
    h2 = boot()
    _, back = _fed(h2, "a")
    assert back.satiety.M == M2 and back.satiety.S == S2
    assert h2.K.resume.resume(back, 100.0 + 182 / 60) > 0                   # the store's load at the return
    step(h2, player(h2, "a"), back, 182, name="a")                          # a new object, 180 minutes later
    assert same.satiety.M == M2
    assert same.satiety.S == pytest.approx(S2 * 2 ** (-1 / 0.15))
    assert back.satiety.M == M2
    assert back.satiety.S == S2
    assert back.satiety.t == pytest.approx(100.0 + 182 / 60)


def test_a_reconnect_after_the_resume_keeps_s():
    # Plan 16 Task 2 (the successor of test_a_reconnect_inside_the_clamp_decays_s_over_the_gap): 21 minutes away, the
    # resume moves satiety.t to the return, so the new object's first minute steps 0 and S is unchanged
    h = boot()
    _, rec = _fed(h)
    M2, S2 = rec.satiety.M, rec.satiety.S
    assert h.K.resume.resume(rec, 100.0 + 23 / 60) == pytest.approx(21 / 60)
    step(h, player(h), rec, 23)                                             # a new object 21 minutes later
    assert rec.satiety.S == S2
    assert rec.satiety.M == M2


def test_a_restart_through_the_store_keeps_s():
    # Plan 16 Task 2 (the successor of test_a_restart_through_the_store_decays_s): the store's load resumes the record,
    # so 180 minutes of server downtime and absence step S by nothing
    h = boot()
    W = h.NR.server.writer
    _, rec = _fed(h)
    M2, S2 = rec.satiety.M, rec.satiety.S
    saved = h.K.store.inputsOnly(rec)
    saved.body = None                                                       # the stand-in body is no stored body
    back = h.K.store.load(saved, None, None)
    assert back.satiety.t == pytest.approx(100.0 + 2 / 60)                  # INPUTS carry satiety.t
    back.stomachFill = 0.6
    back.body = h.rt.eval("{ energyState = 1, rmod = 1 }")
    W.h["a"] = None                                                         # the restart: no hoist survives
    assert h.K.resume.resume(back, 100.0 + 182 / 60) > 0                    # the store's load
    step(h, player(h), back, 182)
    assert W.stats.seeded == 0
    assert back.satiety.M == M2                                             # stored and left: Kinetics clears it
    assert back.satiety.S == S2


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_a_non_finite_stamp_heals_and_counts(bad):
    h = boot()
    W = h.NR.server.writer
    _, rec = _fed(h)
    M2 = rec.satiety.M
    rec.satiety.t = bad
    step(h, player(h), rec, 182)                                            # a new object: the stamp is read
    assert rec.satiety.M == M2                                              # read as no stamp: the minute steps 0
    assert W.stats.guarded == 1
    assert rec.satiety.t == pytest.approx(100.0 + 182 / 60)                 # re-stamped


def test_a_v3_or_fresh_record_has_no_stamp_and_steps_zero_on_its_first_minute():
    h = boot()
    p = player(h)
    rec = h.K.store.new("a", 100.0)
    rec.satiety = h.rt.eval("{ M = 6, S = 0.5 }")
    step(h, p, rec, 181)
    assert rec.satiety.M == 6 and rec.satiety.S == 0.5
    assert h.NR.server.writer.stats.guarded == 0


def test_a_dry_minute_leaves_the_stamp():
    h = boot()
    W = h.NR.server.writer
    p = player(h)
    rec = record(h)
    W.dry = True
    step(h, p, rec, 1)
    assert rec.satiety.t is None


# --- Plan 11d Task 5 fix (ruling T5-2): protein fills only the writer's satiety fullness ----------------------------

def chicken_stomach(h):
    # a 150 g cooked chicken breast in the solid lane: about 46.5 g protein, 5.4 g fat, 98.1 g water, 248 kcal
    st = h.K.stomach["new"]()
    v = h.K.vector["new"]()
    v.water, v.proteins, v.lipids, v.calories = 98.1, 46.5, 5.4, 248
    h.K.stomach.ingest(st, v)
    return st


def test_the_writers_f_reads_the_protein_while_stomach_fill_stays_physical():
    h = boot()
    W = h.NR.server.writer
    st = chicken_stomach(h)
    rec = record(h, stomach=st)
    rec.stomachFill = h.K.stomach.fill(st)                                  # the kinetics stamp
    assert rec.stomachFill == pytest.approx(150 / 730)                      # physical: no protein term
    assert W.satietyF(rec) == pytest.approx((150 + PROTEIN_FILL * 46.5) / 730)   # the writer's F: the protein fills
    assert W.satietyF(rec) > rec.stomachFill
    h.K.satiety.PROTEIN_FILL = 0
    try:
        assert h.K.stomach.fill(st) == rec.stomachFill and W.satietyF(rec) == pytest.approx(150 / 730)
    finally:
        h.K.satiety.PROTEIN_FILL = PROTEIN_FILL


def test_the_written_hunger_reads_the_protein_term():
    h = boot()
    p, p0 = player(h), player(h, "b")
    rec, rec0 = record(h, stomach=chicken_stomach(h)), record(h, stomach=chicken_stomach(h))
    rec0.stomach.buffer.proteins = 0                                        # the same mass less its protein term
    rec0.stomach.buffer.water = rec0.stomach.buffer.water + 46.5
    step(h, p, rec, 1)
    step(h, p0, rec0, 1, name="b")
    F = (150 + PROTEIN_FILL * 46.5) / 730
    assert p.st.sets.HUNGER == pytest.approx(_hunger(6, F=F))
    assert p0.st.sets.HUNGER == pytest.approx(_hunger(6, F=150 / 730)) and p.st.sets.HUNGER < p0.st.sets.HUNGER


def test_the_writers_f_falls_back_to_the_stamp():
    h = boot()
    W = h.NR.server.writer
    assert W.satietyF(record(h)) == 0.6                                     # no stomach: the stamp
    rec = record(h, stomach=h.rt.eval("{}"))
    assert W.satietyF(rec) == 0.6                                           # no buffer: the stamp
    st = chicken_stomach(h)
    st.buffer.proteins = float("nan")
    assert W.satietyF(record(h, stomach=st)) == 0.6                         # a non-finite F: the stamp
    rec = record(h)
    rec.stomachFill = float("nan")
    assert W.satietyF(rec) == 0                                             # and a non-finite stamp reads empty


# --- Plan 11d Task 6: the sleep-debt factor in the writer (ruling 11d-2, spec § 5d) ---------------------------------
# The written HUNGER is min(0.69, hungerTarget(sated(F, mealRead(M)), es) x circadian(h) x acuteFactor(S) x
# sleepFactor(debtH)), debtH read off record.acute.debtH; sleepFactor(d) = 1 + 0.18 clamp(d / 2, 0, 1), 1 for a
# non-finite debt (K.satiety.SLEEP_MAX 0.18, SLEEP_DEBT_FULL_H 2). The seed divides by the same three factors.

def _sleep(d):
    return 1 + 0.18 * min(max(d / 2, 0.0), 1.0)


@pytest.mark.parametrize("debt", [2.0, 5.0])               # a full debt and one past it: the factor's cap
def test_a_full_sleep_debt_raises_the_written_hunger_by_the_factors_cap(debt):
    h = boot()
    p = player(h)
    rec = record(h)
    rec.acute.debtH = debt
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(H1 * 1.18)


def test_a_partial_sleep_debt_raises_the_written_hunger_on_the_ramp():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.acute.debtH = 1.0
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(H1 * 1.09) and _sleep(1.0) == pytest.approx(1.09)


def test_the_sleep_factor_sits_inside_the_cap():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.acute.debtH = 2.0
    rec.body.energyState = 1.1                             # (H0 x 1.1 + 0.1) x 0.954; x 1.18 under the cap
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(_hunger(6, es=1.1) * 1.18)
    h2 = boot()
    p2 = player(h2)
    rec2 = record(h2)
    rec2.stomachFill = 0.0
    rec2.satiety.M = 0.0                                   # target 1 x 0.954: the cap binds with or without the debt
    rec2.acute.debtH = 2.0
    step(h2, p2, rec2, 1)
    assert p2.st.sets.HUNGER == pytest.approx(0.69)


@pytest.mark.parametrize("debt", [float("nan"), float("inf"), float("-inf"), -1.0, "x"])
def test_a_non_finite_or_bad_sleep_debt_reads_factor_one(debt):
    h = boot()
    p = player(h)
    rec = record(h)
    rec.acute.debtH = debt
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(H1)


def test_a_record_with_no_acute_state_reads_factor_one():
    h = boot()
    p = player(h)
    rec = record(h, acute=None)
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(H0)        # no acute state: sleep factor 1, and no body clock, circadian 1


@pytest.mark.parametrize("minute", [1, 721])               # 04:01 and 16:01: the circadian factor 0.954 and 1.046
def test_the_seed_writes_back_the_hunger_it_read_under_a_sleep_debt_and_acute_suppression(minute):
    # S 0.5 and a full debt: the seed inverts hunger / (circadian x acuteFactor(0.5) x sleepFactor(2)), so the first
    # write is the HUNGER read, near the cap too (0.6 / (0.65 x 1.18) before the cap)
    for hunger in (0.4, 0.6):
        for debt in (1.0, 2.0):
            h = boot()
            p = player(h)
            p.st.v.HUNGER = hunger
            rec = h.K.store.new("a", 100.0)
            rec.satiety = h.rt.eval("{ S = 0.5 }")
            rec.acute = h.rt.eval("{ debtH = %r }" % debt)
            step(h, p, rec, minute)
            assert p.st.sets.HUNGER == pytest.approx(hunger), (hunger, debt, minute)
            assert rec.satiety.S == 0.5 and rec.satiety.M is not None


def test_the_seed_divides_by_the_sleep_factor():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.31
    rec = record(h)
    rec.satiety = None
    rec.acute.debtH = 2.0
    step(h, p, rec, 1)
    assert rec.satiety.M == pytest.approx(h.K.satiety.seedMeal(0.31 / (_circ(4 + 1 / 60) * 1.18), 0.6, 1))
    assert p.st.sets.HUNGER == pytest.approx(0.31)


# --- Plan 11d Task 6 fix (ruling T6-1): the divisor guard. A product the factors make non-finite or not positive reads
# 1: the write is the factor-1 target and the seed divides by 1, so M is seeded finite.

@pytest.mark.parametrize("bad", ["0/0", "0"])
def test_a_non_finite_or_zero_factor_product_reads_one(bad):
    h = boot()
    h.K.satiety.acuteFactor = h.rt.eval("function(S) return %s end" % bad)
    p = player(h)
    step(h, p, record(h), 1)
    assert p.st.sets.HUNGER == pytest.approx(H0)                           # hungerTarget x 1: no circadian either
    h2 = boot()
    h2.K.satiety.circadian = h2.rt.eval("function(hour) return %s end" % bad)
    p2 = player(h2)
    p2.st.v.HUNGER = 0.31
    rec = record(h2)
    rec.satiety = None
    step(h2, p2, rec, 1)
    assert math.isfinite(rec.satiety.M) and rec.satiety.M == pytest.approx(h2.K.satiety.seedMeal(0.31, 0.6, 1))
    assert rec.satiety.M > 0 and p2.st.sets.HUNGER == pytest.approx(0.31)


# --- Plan 11d close (ruling C-1): a malformed stomach buffer never stops the writer ---------------------------------
# A buffer key the fullness mass reads that is nil or not a finite number reads the stamp record.stomachFill as F, so
# W.step still writes HUNGER, THIRST and FATIGUE (Kinetics heals the buffer on its own minute, test_kinetics.py).

@pytest.mark.parametrize("bad", [None, "x", "5"])
def test_a_malformed_buffer_key_reads_the_stamp_and_the_writer_still_writes(bad):
    h = boot()
    W = h.NR.server.writer
    p = player(h)
    st = chicken_stomach(h)
    st.buffer.proteins = bad
    rec = record(h, stomach=st)
    assert W.satietyF(rec) == 0.6                                           # the stamp
    step(h, p, rec, 1)
    s = p.st.sets
    assert s.HUNGER == pytest.approx(H1) and s.THIRST == pytest.approx(0.3) and s.FATIGUE == pytest.approx(0.26)
    assert W.stats.writes == 1


@pytest.mark.parametrize("key", ["water", "carbs", "lipids", "fibre", "calories", "vitC"])
def test_any_malformed_buffer_key_reads_the_stamp(key):
    h = boot()
    W = h.NR.server.writer
    st = chicken_stomach(h)
    st.buffer[key] = None
    assert W.satietyF(record(h, stomach=st)) == 0.6


def test_a_malformed_liquid_lane_reads_the_stamp():
    h = boot()
    W = h.NR.server.writer
    st = chicken_stomach(h)
    st.liquid = "x"
    assert W.satietyF(record(h, stomach=st)) == 0.6
    st.liquid = None                                                        # an absent lane is malformed (ruling C9-9)
    assert W.satietyF(record(h, stomach=st)) == 0.6


# --- Plan 11d close (ruling C-2): LIMITATION_FOUR's seed floor and ceiling in hungerTarget's form ----------------------
# floor: an empty stomach under a HUNGER below it seeds MEAL_SEED_MAX and writes hungerTarget(mealRead(MEAL_SEED_MAX), es) =
# SEED_FLOOR es times the factors (SEED_FLOOR 1 - mealRead(MEAL_SEED_MAX), 0.214 since Plan 11g Task 6c fix 1, 0.196 in Task 6c,
# 0.244 in Task 6, 0.203 before); ceiling: a HUNGER above hungerTarget(FULL_WEIGHT F, es) x the factors seeds M = 0
# and writes that ceiling. Review B's case moved to es 1.1 (Plan 11d Task 9d: at es 1.5 the floor's 1.0 reached the
# cap). Since Plan 11g Task 7 fix 1 hungerTarget has no deficit floor (ruling T7-1; 0.02 from Plan 11f Task 2c fix 1), so the deficit reaches both through es alone.

def _seeded(es, read, F, minute, S=0.0):
    h = boot()
    p = player(h)
    p.st.v.HUNGER = read
    rec = record(h)
    rec.stomachFill = F
    rec.body.energyState = es
    rec.satiety = h.rt.eval("{ S = %r }" % S)
    step(h, p, rec, minute)
    return p.st.sets.HUNGER, _circ(math.fmod(100 + minute / 60, 24)) * (1 - 0.7 * S)


@pytest.mark.parametrize("es", [1.1, 1.2])
def test_the_seed_floor_reads_hunger_targets_deficit_term(es):
    peak = round((19.8333 - 4) * 60)
    written, fac = _seeded(es, 0.1, 0.0, peak)
    floor = 1 - _mread(MEAL_SEED_MAX)
    assert written == pytest.approx(floor * es * fac, abs=5e-4)
    assert written > floor * fac                                           # the deficit raises the seed floor (through es)
    assert round(floor, 3) == 0.214                                        # LIMITATION_FOUR's figure


@pytest.mark.parametrize("es", [1.5, 2.0])
def test_the_seed_ceiling_reads_hunger_targets_deficit_term(es):
    written, fac = _seeded(es, 0.68, 1.0, 1, S=0.5)
    assert written == pytest.approx(min(1.0, (1 - FULL_WEIGHT) * es) * fac)   # hungerTarget clamps at 1
    assert written < 0.68


# --- Plan 11e Task 2 (rulings 11e-2 and T2-A): nicotine-withdrawal hunger ------------------------------------------
# The writer reads the server's NICOTINE_WITHDRAWAL once a minute and keeps its own anchor, record.satiety.nicH: the
# world age in game hours at the last minute the stat read 0 or fell. The hunger factor K.satiety.nicotineFactor(w,
# (ageH - nicH) / 24) multiplies the composition (circadian x acute, then through W.satietyFactor) and the seed divides
# by it. NIC_MAX 0.1313, the fade linear to 0 at 182 days.

NIC = 0.1313
AGE1 = 100.0 + 1 / 60                                                       # step()'s world age at minute 1


def _smoker(h, w):
    p = player(h)
    p.st.v.NICOTINE_WITHDRAWAL = w
    return p


@pytest.mark.parametrize("days,factor", [(0.0, 1 + NIC), (91.0, 1 + NIC / 2), (182.0, 1.0), (300.0, 1.0)])
def test_the_written_hunger_takes_the_nicotine_factor(days, factor):
    h = boot()
    p = _smoker(h, 0.51)
    rec = record(h)
    rec.satiety.nicH = AGE1 - days * 24
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(H1 * factor)
    assert rec.satiety.nicH == pytest.approx(AGE1 - days * 24)             # a capped, steady stat holds the anchor


def test_half_the_withdrawal_reads_half_the_rise():
    h = boot()
    p = _smoker(h, 0.255)
    rec = record(h)
    rec.satiety.nicH = AGE1 - 1.0
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(H1 * (1 + NIC * 0.5 * (1 - (1 / 24) / 182)))


def test_the_seed_divides_by_the_nicotine_factor():
    # a record with no M, a capped stat and an anchor 30 days back: the seed inverts hunger / (circadian x the
    # nicotine factor), so the first write is the 0.31 read
    h = boot()
    p = _smoker(h, 0.51)
    p.st.v.HUNGER = 0.31
    rec = record(h)
    rec.satiety = h.rt.eval("{ nicH = %r }" % (AGE1 - 30 * 24))
    step(h, p, rec, 1)
    nic = 1 + NIC * (1 - 30 / 182)
    assert h.NR.server.writer.stats.seeded == 1
    assert rec.satiety.M == pytest.approx(h.K.satiety.seedMeal(0.31 / (_circ(4 + 1 / 60) * nic), 0.6, 1))
    assert p.st.sets.HUNGER == pytest.approx(0.31)


@pytest.mark.parametrize("w", [None, "0.51", float("nan"), float("inf")])
def test_a_stat_that_is_not_a_finite_number_reads_one(w):
    h = boot()
    p = player(h)
    p.st.v.NICOTINE_WITHDRAWAL = w
    rec = record(h)
    rec.satiety.nicH = AGE1
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(H1)
    assert rec.satiety.nicH == AGE1                                         # an unread stat leaves the anchor
    assert h.NR.server.writer.stats.guarded == 0


def test_an_absent_stat_enum_reads_one_and_lays_no_anchor():
    h = boot()
    h.G.CharacterStat.NICOTINE_WITHDRAWAL = None
    p = _smoker(h, 0.51)
    rec = record(h)
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(H1)
    assert rec.satiety.nicH is None


def test_the_anchor_follows_a_zero_stat_holds_while_it_rises_and_resets_when_it_falls():
    h = boot()
    p = _smoker(h, 0.0)
    rec = record(h)
    step(h, p, rec, 1)
    assert rec.satiety.nicH == pytest.approx(AGE1)                          # a 0 stat lays the anchor at the minute
    step(h, p, rec, 2)
    assert rec.satiety.nicH == pytest.approx(100.0 + 2 / 60)                # and follows it while the stat stays 0
    p.st.v.NICOTINE_WITHDRAWAL = 0.2
    step(h, p, rec, 3)
    p.st.v.NICOTINE_WITHDRAWAL = 0.51
    step(h, p, rec, 600)
    assert rec.satiety.nicH == pytest.approx(100.0 + 2 / 60)                # a rising stat holds it
    assert p.st.sets.HUNGER > 0                                             # (the factor reads off the held anchor)
    p.st.v.NICOTINE_WITHDRAWAL = 0.3                                        # a part smoke lowers the stat
    step(h, p, rec, 601)
    assert rec.satiety.nicH == pytest.approx(100.0 + 601 / 60)
    step(h, p, rec, 602)                                                    # steady again: held
    assert rec.satiety.nicH == pytest.approx(100.0 + 601 / 60)


FADED = 182 * 24                                                            # NIC_FADE_DAYS in hours (ruling T2-F)


def test_a_first_anchor_laid_in_withdrawal_starts_fully_faded():
    # ruling T2-F: no fall seen is no evidence of a recent quit, so a first anchor laid while the stat reads above 0
    # sits NIC_FADE_DAYS back and the factor reads 1; a later fall (a smoke) lays it at the minute and the rise counts
    h = boot()
    p = _smoker(h, 0.51)
    rec = record(h)
    c = player(h, "b")                                                     # a non-smoking twin, the control
    c.st.v.NICOTINE_WITHDRAWAL = 0.0
    crec = record(h)
    step(h, p, rec, 1)
    step(h, c, crec, 1, "b")
    assert rec.satiety.nicH == pytest.approx(AGE1 - FADED)
    assert p.st.sets.HUNGER == pytest.approx(H1)
    step(h, p, rec, 2)
    step(h, c, crec, 2, "b")
    assert rec.satiety.nicH == pytest.approx(AGE1 - FADED)                  # a steady stat holds the faded anchor
    assert p.st.sets.HUNGER == pytest.approx(c.st.sets.HUNGER)
    p.st.v.NICOTINE_WITHDRAWAL = 0.255                                      # a smoke
    step(h, p, rec, 3)
    step(h, c, crec, 3, "b")
    assert rec.satiety.nicH == pytest.approx(100.0 + 3 / 60)
    p.st.v.NICOTINE_WITHDRAWAL = 0.51                                       # the rise between smokes
    step(h, p, rec, 4)
    step(h, c, crec, 4, "b")
    assert rec.satiety.nicH == pytest.approx(100.0 + 3 / 60)
    assert p.st.sets.HUNGER == pytest.approx(c.st.sets.HUNGER * (1 + NIC * (1 - (1 / 60 / 24) / 182)))


@pytest.mark.parametrize("w", [0.51, 0.1])
def test_a_first_anchor_in_withdrawal_is_neutral_at_any_level(w):
    h = boot()
    p = _smoker(h, w)
    rec = record(h)
    step(h, p, rec, 1)
    assert rec.satiety.nicH == pytest.approx(AGE1 - FADED)
    assert p.st.sets.HUNGER == pytest.approx(H1)
    assert h.NR.server.writer.stats.guarded == 0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), "x", True, AGE1 + 5])
def test_a_corrupt_anchor_in_withdrawal_heals_fully_faded_and_counts(bad):
    h = boot()
    p = _smoker(h, 0.51)
    rec = record(h)
    rec.satiety.nicH = bad
    step(h, p, rec, 1)
    assert rec.satiety.nicH == pytest.approx(AGE1 - FADED)
    assert h.NR.server.writer.stats.guarded == 1
    assert p.st.sets.HUNGER == pytest.approx(H1)


@pytest.mark.parametrize("bad", [float("nan"), "x", AGE1 + 5])
def test_a_corrupt_anchor_at_a_zero_stat_heals_to_the_minute_and_counts(bad):
    h = boot()
    p = _smoker(h, 0.0)
    rec = record(h)
    rec.satiety.nicH = bad
    step(h, p, rec, 1)
    assert rec.satiety.nicH == pytest.approx(AGE1)
    assert h.NR.server.writer.stats.guarded == 1
    assert p.st.sets.HUNGER == pytest.approx(H1)


def test_the_anchor_survives_a_restart_through_the_store():
    h = boot()
    W = h.NR.server.writer
    p = _smoker(h, 0.51)
    rec = record(h)
    rec.satiety.nicH = AGE1 - 91 * 24
    step(h, p, rec, 1)
    assert "satiety.nicH" in list(h.K.store.INPUTS.values())                # a stored input
    saved = h.K.store.inputsOnly(rec)
    saved.body = None
    back = h.K.store.load(saved, None, None)
    assert back.satiety.nicH == pytest.approx(AGE1 - 91 * 24)
    back.stomachFill = 0.6
    back.body = h.rt.eval("{ energyState = 1, rmod = 1 }")
    W.h["a"] = None
    step(h, _smoker(h, 0.51), back, 2)
    assert back.satiety.nicH == pytest.approx(AGE1 - 91 * 24)


# --- Plan 11f Task 9b (rulings T9-1, T9-3): monotony's floor, read once a writer minute -----------------------------
# record.monotony's target (K.monotony.target at the minute's world age) joins the effects' UNHAPPINESS target by
# sum, clamped at the surface's 59, and is the BOREDOM target alone; both rise at the hybrid's rates and are released
# by the target's fall.

def mono(h, n, last, staple=False):
    t = h.rt.eval("{ t = {} }")
    e = h.rt.eval("{}")
    e.n, e.last = n, last
    if staple:
        e.s = True
    t.t["Base.Apple"] = e
    return t


def test_a_monotonous_record_raises_both_floors_at_the_writer_minute():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.effects.panicTarget = 0                              # the default target 10 would hold BOREDOM's rise (panic above 5)
    rec.monotony = mono(h, 3, 100.0)                        # target 4.3 x 2 = 8.6 on both
    step(h, p, rec, 0)                                     # the hoist's first minute steps 0 s
    step(h, p, rec, 1)
    assert p.st.sets.UNHAPPINESS == pytest.approx(22 / 3600 * 60)
    assert p.st.sets.BOREDOM == pytest.approx(25 / 3600 * 60)
    for m in range(2, 40):
        step(h, p, rec, m)
    t = 4.3 * (3 * 2 ** (-(39 / 60) / 72.0) - 1)
    eps = h.K.hybrid.FLOOR_EPS                             # met, then the decaying target's fall held under one epsilon
    assert t <= p.st.v.UNHAPPINESS < t + eps and t <= p.st.v.BOREDOM < t + eps


def test_monotony_adds_to_the_effects_unhappiness_target_under_the_surface_cap():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.monotony = mono(h, 3, 100.0)
    rec.effects.unhappyTarget = 10
    p.st.v.UNHAPPINESS = 18.6
    p.st.v.BOREDOM = 8.6
    step(h, p, rec, 0)
    assert p.st.sets.UNHAPPINESS is None and p.st.sets.BOREDOM is None       # 10 + 8.6 held: nothing to write
    rec.effects.unhappyTarget = 55
    p.st.v.UNHAPPINESS = 58.9
    step(h, p, rec, 1)
    assert p.st.sets.UNHAPPINESS == pytest.approx(59)      # 55 + 8.6 clamped at the surface's 59 (#2369)


def test_the_monotony_release_lowers_the_stat_by_the_targets_fall_whatever_raised_it():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.monotony = mono(h, 3, 100.0)
    p.st.v.UNHAPPINESS = 30                                 # raised above the target by another source
    p.st.v.BOREDOM = 8.6
    step(h, p, rec, 0)
    rec.monotony = h.rt.eval("{ t = {} }")                  # the diet varied past the window: the target falls 8.6
    step(h, p, rec, 1)
    assert p.st.sets.UNHAPPINESS == pytest.approx(30 - 8.6)
    assert p.st.sets.BOREDOM == pytest.approx(0, abs=1e-12)


def test_a_staple_record_targets_a_quarter():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.effects.panicTarget = 0
    rec.monotony = mono(h, 3, 100.0, staple=True)
    for m in range(0, 61):
        step(h, p, rec, m)
    t = 0.25 * 4.3 * (3 * 2 ** (-1 / 72.0) - 1)              # a quarter of the level, an hour on
    eps = h.K.hybrid.FLOOR_EPS
    assert t <= p.st.v.UNHAPPINESS < t + eps and t <= p.st.v.BOREDOM < t + eps


def test_the_unhappiness_floor_holds_over_its_threshold_inside_the_dead_zone():
    # Plan 15 Task 9 (item 10c): a composed UNHAPPINESS target falling through the level-1 step 20 by less than
    # 0.02 x 20 is held 0.01 over it (K.monotony.hold against the remembered target), so the Unhappy moodle does not
    # blink; past the zone the target falls and the stat is lowered by the fall
    h = boot()
    p = player(h)
    rec = record(h)
    rec.effects.unhappyTarget = 20.5
    p.st.v.UNHAPPINESS = 20.5
    step(h, p, rec, 0)
    assert rec.moodLast.u == pytest.approx(20.5)
    rec.effects.unhappyTarget = 19.8
    step(h, p, rec, 1)
    assert rec.moodLast.u == pytest.approx(20.01)
    rec.effects.unhappyTarget = 19.0
    step(h, p, rec, 2)
    assert rec.moodLast.u == pytest.approx(19.0)


def test_no_monotony_writes_no_boredom():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 2)
    assert p.st.sets.BOREDOM is None and p.st.sets.UNHAPPINESS is None


def test_without_the_boredom_enum_unhappiness_still_takes_the_floor():
    h = boot()
    h.rt.execute("CharacterStat.BOREDOM = nil")
    p = player(h)
    rec = record(h)
    rec.monotony = mono(h, 3, 100.0)
    step(h, p, rec, 0)
    step(h, p, rec, 1)
    assert p.st.sets.UNHAPPINESS == pytest.approx(22 / 3600 * 60) and p.st.sets.BOREDOM is None


@pytest.mark.parametrize("raw", ["'junk'", "{ t = 4 }", "{ t = { ['Base.Apple'] = { n = 0 / 0, last = 1 } } }",
                                 "{ t = { ['Base.Apple'] = { n = 9, last = 999 } } }"])
def test_a_corrupt_monotony_is_reset_and_counted_and_targets_nothing(raw):
    h = boot()
    p = player(h)
    rec = record(h)
    rec.monotony = h.rt.eval(raw)
    g0 = h.NR.server.writer.stats.guarded
    step(h, p, rec, 1)
    assert h.NR.server.writer.stats.guarded == g0 + 1
    assert list(rec.monotony.t.keys()) == []
    assert p.st.sets.UNHAPPINESS is None and p.st.sets.BOREDOM is None


def test_a_non_finite_effects_target_reads_zero_beside_monotony():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.monotony = mono(h, 3, 100.0)
    rec.effects.unhappyTarget = float("nan")
    step(h, p, rec, 0)
    step(h, p, rec, 1)
    assert p.st.sets.UNHAPPINESS == pytest.approx(22 / 3600 * 60)     # monotony's target alone


def test_the_writer_reads_the_target_once_a_minute_and_no_eat_writes_mood():
    src = open(os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server", "NR_Server_Writer.lua"),
               encoding="utf-8").read()
    assert src.count("K.monotony.target(") == 1
    intake = open(os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server",
                               "NR_Server_Intake.lua"), encoding="utf-8").read()
    assert '"add"' not in intake and "addMood" not in intake


# --- Plan 11f Task 9b fix 2: the remembered floor targets live on the record (record.moodLast = { u, b }) ----------

def _held_floor(h, p, rec):
    """Hold a floor at the cap: n = 9 portions of one type at age 100 targets 30 on both stats; run until met."""
    rec.effects.panicTarget = 0                              # vanilla wipes BOREDOM while PANIC > 5 (the default target 10)
    rec.monotony = mono(h, 9, 100.0)
    for m in range(0, 110):
        step(h, p, rec, m)
    assert p.st.v.UNHAPPINESS == pytest.approx(30) and p.st.v.BOREDOM == pytest.approx(30)


def test_the_remembered_targets_are_written_on_the_record():
    h = boot()
    p = player(h)
    rec = record(h)
    _held_floor(h, p, rec)
    assert rec.moodLast.u == pytest.approx(30) and rec.moodLast.b == pytest.approx(30)


def test_a_reconnect_after_a_full_release_still_lands_the_fall_to_zero():
    h = boot()
    p = player(h)
    rec = record(h)
    _held_floor(h, p, rec)
    q = player(h, "a")                                       # a reconnect: a new player object, a new hoist
    q.st.v.UNHAPPINESS = p.st.v.UNHAPPINESS
    q.st.v.BOREDOM = p.st.v.BOREDOM
    assert not h.rt.eval("rawequal")(p, q)
    h.T.age = 100.0 + 118 + 200                              # offline past the window: the counts have faded to 0
    h.NR.server.writer.step("a", q, rec, None)
    assert q.st.v.UNHAPPINESS == pytest.approx(0, abs=1e-9)
    assert q.st.v.BOREDOM == pytest.approx(0, abs=1e-9)


def test_the_same_hoist_lands_the_same_release_to_zero():
    h = boot()
    p = player(h)
    rec = record(h)
    _held_floor(h, p, rec)
    h.T.age = 100.0 + 118 + 200
    h.NR.server.writer.step("a", p, rec, None)
    assert p.st.v.UNHAPPINESS == pytest.approx(0, abs=1e-9)
    assert p.st.v.BOREDOM == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize("raw", ["'x'", "{ u = 0 / 0, b = 'y' }", "{ u = 1 / 0 }", "{}"])
def test_a_corrupt_or_absent_moodlast_reads_zero_and_is_laid_again(raw):
    h = boot()
    p = player(h)
    rec = record(h)
    rec.moodLast = h.rt.eval(raw)
    rec.monotony = mono(h, 9, 100.0)
    step(h, p, rec, 0)
    step(h, p, rec, 1)
    assert p.st.sets.UNHAPPINESS == pytest.approx(22 / 3600 * 60)
    assert rec.moodLast.u == pytest.approx(30) and rec.moodLast.b == pytest.approx(30)


def test_the_boredom_rise_waits_while_panic_is_above_five_and_the_target_is_remembered():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.effects.panicTarget = 0
    rec.monotony = mono(h, 9, 100.0)
    p.st.v.PANIC = 7
    step(h, p, rec, 0)
    p.st.v.PANIC = 7
    step(h, p, rec, 1)
    assert p.st.sets.BOREDOM is None                         # vanilla resets it every tick: no useless write
    assert p.st.sets.UNHAPPINESS == pytest.approx(22 / 3600 * 60)
    assert rec.moodLast.b == pytest.approx(30)
    p.st.v.PANIC = 0
    step(h, p, rec, 2)
    assert p.st.sets.BOREDOM == pytest.approx(25 / 3600 * 60)


def test_the_monotony_table_is_healed_at_first_sight_and_not_every_minute():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.monotony = mono(h, 3, 100.0)
    step(h, p, rec, 0)
    g0 = h.NR.server.writer.stats.guarded
    rec.monotony = h.rt.eval("{ t = { ['Base.Apple'] = { n = 0 / 0, last = 1 } } }")   # corrupted mid-session
    step(h, p, rec, 1)
    assert h.NR.server.writer.stats.guarded == g0            # not scanned again: the eat's heal is its door
    q = player(h)                                            # a new object is first sight again
    step(h, q, rec, 2)
    assert h.NR.server.writer.stats.guarded == g0 + 1


# --- the calibrated curve (Plan 15 Task 6): the written HUNGER is the curve of h_model, which the record keeps ------

def test_the_written_hunger_is_the_curve_of_the_models_own_value():
    h = boot(curve=True)
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    assert rec.satiety.hModel == pytest.approx(H1)                       # the model's composition, unchanged
    assert p.st.sets.HUNGER == pytest.approx(h.K.hungerCurve.map(H1))    # written through the curve
    hc = boot(curve=False)
    pc = player(hc)
    step(hc, pc, record(hc), 1)
    assert pc.st.sets.HUNGER == pytest.approx(H1)                        # the pre-curve writer wrote h_model


def test_the_seed_inverts_the_curve_so_a_fresh_record_writes_back_the_hunger_it_read():
    # over the seed floor (the curve of 0.204, 0.163); 0.2 seeds an M under FED_M whose dip-free reseed would be fed, so
    # it keeps the first seed and the fasting hold writes the dip-free curve, over the read by the dip at most
    for read in (0.25, 0.31, 0.5):
        h = boot(curve=True)
        p = player(h)
        p.st.v.HUNGER = read
        rec = record(h)
        rec.satiety = h.rt.table_from({"S": 0, "L": 0})
        rec.stomachFill = 0.0
        step(h, p, rec, 1)
        assert p.st.sets.HUNGER == pytest.approx(read), read
        assert h.NR.server.writer.input.fed is False                     # unfed: the seed kept the dip in h_model
        assert rec.satiety.hModel == pytest.approx(h.K.hungerCurve.inverse(read) * 0.9540165460822252), read


def test_the_fed_flag_and_the_circadian_factor_reach_the_curve():
    h = boot(curve=True)
    p = player(h)
    rec = record(h)                                                      # M 6: fed (FED_M 3.8)
    step(h, p, rec, 1)
    inp = h.NR.server.writer.input
    assert inp.fed is True and inp.circ == pytest.approx(0.9540165460822252)
    rec.satiety.M = 1.0
    step(h, p, rec, 2)
    assert inp.fed is False


def test_a_seed_between_fed_and_unfed_writes_no_less_than_the_hunger_it_read():
    h = boot(curve=True)
    p = player(h)
    p.st.v.HUNGER = 0.1875                                               # the band's middle, 0.185-0.19 (0.2 before Task 6c)
    rec = record(h)
    rec.satiety = h.rt.table_from({"S": 0, "L": 0})
    rec.stomachFill = 0.0
    step(h, p, rec, 1)
    C = h.K.hungerCurve
    assert rec.satiety.M < C.FED_M and rec.satiety.hModel == pytest.approx(C.inverse(0.1875))
    assert 0.1875 < p.st.sets.HUNGER <= C.map(C.inverse(0.1875) / 0.9540165460822252) + 1e-12
