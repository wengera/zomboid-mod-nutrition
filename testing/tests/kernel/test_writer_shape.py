"""The once-a-minute stat writer (Plan 11 Task 14; Decision 1 (c), the hybrid): NR_Server_Writer.lua on the shared
server host. The writer step is driven directly on a crafted record, so each obligation is one assertion: the
seven rise rates saved then zeroed (0, never nil) at the server's OnGameBoot and never at a client's; HUNGER,
THIRST and FATIGUE written once a minute in Mode 1 only; the auto-drink sip folded into the THIRST target and
handed to the pool; the floors stepped by elapsed world age; the writer after the eats and the effects in ORDER;
the boot warning beside Nutrition Makes Sense.
"""
import math
import os

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
                  TEMPERATURE = "TEMPERATURE", INTOXICATION = "INTOXICATION" }
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


def boot(mode=1):
    h = Host(extra_env=("NR_T = NR_T or {}\nNR_T.mode = %d\n" % mode) + ENV)
    h.fire("OnGameBoot")
    return h


def player(h, name="a"):
    return h.rt.eval("NR_T.statsPlayer")(h.player(name), h.rt.eval(STATS))


def record(h, **over):
    r = h.rt.eval("""{ stomachFill = 0.6, satietyStepped = true, body = { energyState = 1, rmod = 1 },
        fluids = { thirstTarget = 0.3, autoDrop = 0 }, acute = { S = 0.2, circ = 0.05, frozen = false },
        effects = { fOff = 0.01, panicTarget = 10, stressTarget = 0, unhappyTarget = 0, foodSickTarget = 0,
                    tempTarget = 0, tempAdj = 0, intoxTarget = 0 } }""")
    for k, v in over.items():
        r[k] = v
    return r


def step(h, p, rec, minute, name="a"):
    h.T.age = 100.0 + minute / 60
    h.NR.server.writer.step(name, p, rec, None)


def test_boot_saves_then_zeroes_the_seven_rates_to_zero_never_nil():
    h = boot()
    zg = h.G.ZomboidGlobals
    for k in RATES:
        assert zg[k] == 0, k
    assert zg.StressDecrease == 3.0e-5                       # not a rise rate: untouched
    assert h.NR.vanillaRate("HungerIncrease") == 9.6e-6 and h.NR.server.writer.zeroed is True


def test_the_saved_rates_answer_for_every_key():
    h = boot()
    rates = h.NR.vanillaRates()
    assert rates["HungerIncrease"] == 9.6e-6 and rates["FatigueIncrease"] == 3.45e-5
    assert rates["HungerIncreaseWhenWellFed"] == 0.0 and rates["ThirstSleepingIncrease"] == 1.0e-6
    assert sorted(rates.keys()) == sorted(RATES)


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
    rec = record(h, satiety=0.6)
    step(h, p, rec, 1)
    s = p.st.sets
    assert s.HUNGER == pytest.approx(0.4) and s.THIRST == pytest.approx(0.3) and s.FATIGUE == pytest.approx(0.26)
    assert p.drunkReduction == 0
    assert h.NR.server.writer.stats.writes == 1


def test_the_stomach_fill_no_longer_drives_hunger():
    h = boot()
    p = player(h)
    rec = record(h, satiety=0.6)
    rec.stomachFill = float("nan")
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(0.4)


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
    rec.stomach = h.K.stomach.seedFull(h.K.stomach.new())  # the landing's preconditions (IN.readAfterAndLand)
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
    rec = record(h, satiety=0.6)
    rec.acute.frozen = True
    step(h, p, rec, 1)
    assert p.st.sets.FATIGUE is None and p.st.sets.HUNGER == pytest.approx(0.4)


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
    rec = record(h, satiety=0.6)
    p1 = player(h)
    step(h, p1, rec, 1)
    p2 = player(h)
    step(h, p2, rec, 2)
    assert h.G.rawequal(h.NR.server.writer.h["a"].p, p2) and p2.st.sets.HUNGER == pytest.approx(0.4)


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
    assert h.NR.server.writer.inp["a"].endFold is False


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


# --- Plan 11 Task 15: the satiety scalar in the writer ----------------------------------------------------------

def moodle(h, p, level):
    p.getMoodles = h.rt.eval("function(n) return function(s) return { getMoodleLevel = function(m, k) return n end } end end")(level)


def test_a_record_with_satiety_writes_one_minus_s_through_the_energy_term():
    h = boot()
    p = player(h)
    rec = record(h, satiety=0.7)
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(0.3)


def test_the_energy_term_raises_the_hunger_of_a_deficit():
    h = boot()
    p = player(h)
    rec = record(h, satiety=0.7)
    rec.body.energyState = 1.5
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(0.3 * 1.5 + 0.15 * 0.5)


def test_a_record_without_satiety_seeds_it_from_hunger():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.31
    rec = record(h)
    step(h, p, rec, 1)
    assert rec.satiety == pytest.approx(0.69) and h.NR.server.writer.stats.seeded == 1
    assert p.st.sets.HUNGER == pytest.approx(0.31)


def test_a_new_record_for_a_hungry_character_seeds_from_hunger_never_zero():
    # ruling T15-1: K.store.new's S = 1 is never stepped as is; a pruned record, a mod added mid-save or a failed
    # first read gives a hungry character a fresh record, and its first minute writes its own HUNGER back
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.4
    rec = h.K.store.new("a", 100.0)
    assert rec.satiety == 1 and rec.satietyStepped is None
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(0.4)
    assert rec.satiety == pytest.approx(0.6) and rec.satietyStepped is True
    assert h.NR.server.writer.stats.seeded == 1


def test_a_stepped_record_keeps_its_scalar_across_a_restart():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.4
    rec = h.K.store.new("a", 100.0)
    step(h, p, rec, 1)
    rec.satiety = 0.9                                      # an eat since
    raw = h.K.store.inputsOnly(rec)
    assert raw.satietyStepped is True
    back = h.K.store.load(raw, None, None)
    p2 = player(h)                                         # the restart: a new object, a new hoist
    p2.st.v.HUNGER = 0.4
    step(h, p2, back, 2)
    assert back.satiety == pytest.approx(0.9) and h.NR.server.writer.stats.seeded == 1
    assert p2.st.sets.HUNGER == pytest.approx(0.1)


def test_a_v3_record_saved_without_the_mark_seeds_once():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.35
    raw = h.rt.eval("{ v = 3, username = 'a', firstSeen = 1.0, lastSeen = 2.0, resets = 0, dead = false, satiety = 1 }")
    rec = h.K.store.load(raw, None, None)
    assert rec.satietyStepped is None
    step(h, p, rec, 1)
    assert rec.satiety == pytest.approx(0.65) and p.st.sets.HUNGER == pytest.approx(0.35)
    step(h, p, rec, 2)
    assert h.NR.server.writer.stats.seeded == 1


def test_a_mark_present_but_not_true_seeds_from_hunger():
    # Task 15 fix 2: only a true mark means stepped; satietyStepped = false is seeded like a missing one
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.35
    raw = h.rt.eval("{ v = 3, username = 'a', firstSeen = 1.0, lastSeen = 2.0, resets = 0, dead = false, satiety = 1, satietyStepped = false }")
    rec = h.K.store.load(raw, None, None)
    assert rec.satietyStepped is False
    step(h, p, rec, 1)
    assert rec.satiety == pytest.approx(0.65) and p.st.sets.HUNGER == pytest.approx(0.35)
    assert h.NR.server.writer.stats.seeded == 1


def test_a_non_finite_scalar_is_seeded_again_from_hunger():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.31
    rec = record(h, satiety=float("nan"))
    step(h, p, rec, 1)
    assert rec.satiety == pytest.approx(0.69) and p.st.sets.HUNGER == pytest.approx(0.31)


def test_the_food_eaten_moodle_freezes_the_decay():
    h = boot()
    p = player(h)
    moodle(h, p, 1)                                        # before the first step: the hoist keeps the handle
    rec = record(h, satiety=0.7)
    step(h, p, rec, 1)
    step(h, p, rec, 31)                                    # thirty game minutes, the moodle up throughout
    assert rec.satiety == pytest.approx(0.7)


def test_with_the_moodle_down_the_scalar_decays_at_vanillas_idle_rate():
    h = boot()
    p = player(h)
    rec = record(h, satiety=0.7)
    step(h, p, rec, 1)
    step(h, p, rec, 31)
    assert rec.satiety == pytest.approx(0.7 * math.exp(-9.6e-6 * 1800))
    assert p.st.sets.HUNGER == pytest.approx(1 - 0.7 * math.exp(-9.6e-6 * 1800))


def test_the_decay_reads_the_rates_saved_at_boot():
    h = Host(extra_env="NR_T = NR_T or {}\nNR_T.mode = 1\n" + ENV + "\nZomboidGlobals.HungerIncrease = 2.0e-5\n")
    h.fire("OnGameBoot")
    assert h.NR.server.writer.rates.idle == 2.0e-5 and h.G.ZomboidGlobals.HungerIncrease == 0
    p = player(h)
    rec = record(h, satiety=0.7)
    step(h, p, rec, 1)
    step(h, p, rec, 31)
    assert rec.satiety == pytest.approx(0.7 * math.exp(-2.0e-5 * 1800))


def test_asleep_the_scalar_decays_at_the_sleeping_rate():
    h = boot()
    p = player(h)
    p.asleep = True
    rec = record(h, satiety=0.7)
    step(h, p, rec, 1)
    step(h, p, rec, 31)
    assert rec.satiety == pytest.approx(0.7 * math.exp(-1.0e-6 * 1800))


def test_running_decays_at_a_third_of_the_exercise_rate_and_never_freezes():
    h = boot()
    p = player(h)
    p.IsRunning = h.rt.eval("function(s) return true end")
    p.isPlayerMoving = h.rt.eval("function(s) return true end")
    rec = record(h, satiety=0.7)
    step(h, p, rec, 1)
    step(h, p, rec, 31)
    assert rec.satiety == pytest.approx(0.7 * math.exp(-1.92e-5 / 3 * 1800))
    moodle(h, p, 1)
    p2 = player(h)                                         # a new object: the hoist reads the moodle handle again
    p2.IsRunning, p2.isPlayerMoving, p2.getMoodles = p.IsRunning, p.isPlayerMoving, p.getMoodles
    rec2 = record(h, satiety=0.7)
    step(h, p2, rec2, 40)
    step(h, p2, rec2, 70)
    assert rec2.satiety == pytest.approx(0.7 * math.exp(-1.92e-5 * 1800))


def test_hearty_appetite_scales_the_decay_by_one_and_a_half():
    h = boot()
    p = player(h)
    p.getCharacterTraits = h.rt.eval("function(s) return { get = function(c, t) return t == 'HA' end } end")
    rec = record(h, satiety=0.7)
    step(h, p, rec, 1)
    step(h, p, rec, 31)
    assert rec.satiety == pytest.approx(0.7 * math.exp(-9.6e-6 * 1.5 * 1800))


def test_the_sandbox_decrease_multiplier_scales_the_decay():
    h = boot()
    h.G.getSandboxOptions = h.rt.eval("function() return { getStatsDecreaseMultiplier = function(s) return 2 end } end")
    p = player(h)
    rec = record(h, satiety=0.7)
    step(h, p, rec, 1)
    step(h, p, rec, 31)
    assert rec.satiety == pytest.approx(0.7 * math.exp(-9.6e-6 * 2 * 1800))

def test_the_satiety_bulk_option_reads_its_range():
    h = boot()
    assert h.NR.server.options.satietyBulk == 0.25
    for given, want in ((0.4, 0.4), (0.9, 0.5), (0.1, 0.25), (0.25, 0.25), (0.5, 0.5)):
        h.G.SandboxVars.NR.SatietyBulk = given
        h.NR.server.readOptions("poll")
        assert h.NR.server.options.satietyBulk == pytest.approx(want), given
    h.G.SandboxVars.NR.SatietyBulk = float("nan")
    h.NR.server.readOptions("poll")
    assert h.NR.server.options.satietyBulk == 0.25


LIMITATION_FOUR = (
    "HUNGER, THIRST and FATIGUE are written once a game minute; an eat or a drink shows at once and the next write "
    "overwrites it with the satiety target (1 - S through the energy term, capped at 0.69), so the eat or drink stays "
    "only through the satiety scalar it raised; an eat or a drink another mod makes through a direct Eat or "
    "DrinkFluid call, outside the intake's wraps, raises no S, so the next write takes its hunger relief back; "
    "hunger is that scalar stepped once a game minute, so it lags vanilla by up to a minute (5.8e-4 idle, 1.2e-3 "
    "exercising; Appendix D); under a calorie deficit vanilla's food-eaten freeze fires less often, and at the 0.69 "
    "cap a starving character can earn a freeze its scalar did not (Appendix D Question 4)")


def test_limitation_four_names_the_overwrite_and_the_scalar():
    lim = list(Host().NR.server.writer.limitations.values())
    assert len(lim) == 12                                  # the self-report prints the count (Task 20 fix: 12)
    assert lim[3] == LIMITATION_FOUR


# --- Task 15 fix 1: the exercise branches and the step clamp ----------------------------------------------------

def test_moving_without_running_decays_at_the_idle_rate():
    h = boot()
    p = player(h)
    p.IsRunning = h.rt.eval("function(s) return false end")
    p.isPlayerMoving = h.rt.eval("function(s) return true end")
    rec = record(h, satiety=0.7)
    step(h, p, rec, 1)
    step(h, p, rec, 31)
    assert rec.satiety == pytest.approx(0.7 * math.exp(-9.6e-6 * 1800))


def test_a_melee_swing_decays_at_the_exercise_rate():
    h = boot()
    h.G.SwipeStatePlayer = h.rt.eval("{ instance = function() return NR_T end }")   # any unique handle
    p = player(h)
    p.isCurrentState = h.rt.eval("function(s, st) return st == NR_T end")
    rec = record(h, satiety=0.7)
    step(h, p, rec, 1)
    step(h, p, rec, 31)
    assert rec.satiety == pytest.approx(0.7 * math.exp(-1.92e-5 / 3 * 1800))
    moodle(h, p, 1)
    p2 = player(h)
    p2.isCurrentState, p2.getMoodles = p.isCurrentState, p.getMoodles
    rec2 = record(h, satiety=0.7)
    step(h, p2, rec2, 40)
    step(h, p2, rec2, 70)
    assert rec2.satiety == pytest.approx(0.7 * math.exp(-1.92e-5 * 1800))   # exercise never freezes


def test_a_gap_over_sixty_minutes_decays_over_3600_seconds_only():
    h = boot()
    p = player(h)
    rec = record(h, satiety=0.7)
    step(h, p, rec, 1)
    step(h, p, rec, 1 + 180)                               # three game hours since the last write
    assert rec.satiety == pytest.approx(0.7 * math.exp(-9.6e-6 * 3600))


# --- Plan 11 Task 19: the dry seam the harness's ghost runs use --------------------------------------------------

def test_a_dry_writer_computes_and_sets_nothing():
    h = boot()
    W = h.NR.server.writer
    p = player(h)
    rec = record(h, satiety=0.6)
    rec.fluids.autoDrop = 0.05
    h.NR.server.intake.landed["a"] = True
    W.dry = True
    step(h, p, rec, 1)
    p.st.v.THIRST = 0.1                                    # a fall a live writer would book as a sip
    step(h, p, rec, 2)
    assert len(list(p.st.sets.keys())) == 0                # no stat written
    assert rec.satiety == 0.6 and rec.satietyStepped is True   # the scalar neither stepped nor re-marked
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
    rec = record(h, satiety=0.6)
    W.dry = True
    step(h, p, rec, 1)
    W.dry = None
    step(h, p, rec, 2)
    assert p.st.sets.HUNGER is not None and W.stats.writes == 1


def test_a_dry_seam_set_to_anything_but_true_leaves_the_writer_live():
    h = boot()
    p = player(h)
    rec = record(h, satiety=0.6)
    h.NR.server.writer.dry = 1                             # only true dries the writer
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(0.4) and h.NR.server.writer.stats.writes == 1


# --- Task 20 fix: the well-fed rate from the saved table (review A's F4), another mod re-assigning the rates -------

def test_the_well_fed_rate_is_the_one_saved_at_boot_not_the_default():
    h = Host(extra_env="NR_T = NR_T or {}\nNR_T.mode = 1\n" + ENV + "\nZomboidGlobals.HungerIncreaseWhenWellFed = 3.0e-6\n")
    h.fire("OnGameBoot")
    assert h.NR.server.writer.rates.wellFed == 3.0e-6 and h.G.ZomboidGlobals.HungerIncreaseWhenWellFed == 0
    p = player(h)
    moodle(h, p, 1)                                        # the FOOD_EATEN moodle up: the well-fed rate applies
    rec = record(h, satiety=0.7)
    step(h, p, rec, 1)
    step(h, p, rec, 31)
    assert rec.satiety == pytest.approx(0.7 * math.exp(-3.0e-6 * 1800))


def test_a_limitation_names_another_mod_re_assigning_the_rates():
    lim = list(Host().NR.server.writer.limitations.values())
    hits = [x for x in lim if "another mod" in x and "OnGameBoot" in x and "ZomboidGlobals" in x]
    assert len(hits) == 1
    assert "vanilla's drift" in hits[0] and "between the writer's minute writes" in hits[0]
