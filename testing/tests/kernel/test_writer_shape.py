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


# Plan 11c Task 6: the written HUNGER, recomputed in doubles from the kernels' constants at HEAD (NR_Kernel_Satiety.lua,
# NR_Kernel_Hybrid.lua): post(P) = 1 - 1 / (1 + 3 (P / P_REQ)^STEEP), P_REQ 6, STEEP 0.05; sated(F, Pn) = 1 - (1 - 0.55 F)
# (1 - Pn), FULL_WEIGHT 0.55 (both refit in Plan 11d Task 5, ruling 11d-5); hungerTarget(x, es) = clamp((1 - x) es + 1.0 max(0, es - 1), 0, 1), DEFICIT_FLOOR 1.0;
# circadian(h) = 1 + 0.085 cos(2 pi (h - 19.8333) / 24); acuteFactor(S) = 1 - 0.7 S; the writer's composition
# (amendment 3) min(0.69, hungerTarget x circadian x acuteFactor), the 0.69 the hybrid's hungerCap. The host's clock
# reads the hour of day as fmod(age, 24), and step() sets age 100 + minute / 60, so minute m is hour 4 + m / 60.
def _post(P):
    return 0.0 if P <= 0 else 1 - 1 / (1 + 3 * math.exp(0.05 * math.log(P / 6)))


def _circ(hour):
    return 1 + 0.085 * math.cos(6.283185307179586 * (hour - 19.8333) / 24)


def _hunger(P, F=0.6, es=1.0, minute=1, S=0.0):
    x = 1 - (1 - 0.55 * F) * (1 - _post(P))
    target = min(max((1 - x) * es + 1.0 * max(0.0, es - 1), 0.0), 1.0)
    return min(0.69, target * _circ(math.fmod(100 + minute / 60, 24)) * (1 - 0.7 * min(max(S, 0.0), 1.0)))


# the default record's minute-1 HUNGER: P 6 = P_REQ reads post 0.75, so (1 - 0.55 x 0.6) x (1 - 0.75) = 0.1675, times
# the circadian factor at 04:01 (0.9540165460822252)
H1 = 0.15979777146877272


def record(h, **over):
    r = h.rt.eval("""{ stomachFill = 0.6, satiety = { P = 6, S = 0, L = 0 }, body = { energyState = 1, rmod = 1 },
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
    assert p.st.sets.HUNGER == pytest.approx(_hunger(6, F=0.0))           # (1 - 0.55 x 0) x (1 - 0.75) x c(04:01)
    assert p.st.sets.HUNGER == pytest.approx(0.25 * 0.9540165460822252)
    p2 = player(h, "b")
    rec2 = record(h)
    rec2.stomachFill = float("nan")                                        # a non-finite fill reads empty
    step(h, p2, rec2, 1, name="b")
    assert p2.st.sets.HUNGER == pytest.approx(0.25 * 0.9540165460822252)


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
    step(h, p2, rec, 2)                                    # a new hoist: the stamp's minute decays P (ruling C-1)
    assert h.G.rawequal(h.NR.server.writer.h["a"].p, p2) and p2.st.sets.HUNGER == pytest.approx(_hunger(6 * 2 ** (-(1 / 60) / 0.7), minute=2))


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


def test_the_satiety_bulk_option_and_task_15s_writer_pieces_are_retired():
    h = boot()
    assert h.NR.server.options.satietyBulk is None
    assert h.NR.server.writer.rates is None
    h.G.SwipeStatePlayer = h.rt.eval("{ instance = function() return NR_T end }")
    p = player(h)
    step(h, p, record(h), 1)
    assert h.NR.server.writer.h["a"].swipe is not None   # the swing handle stays: it marks resistance work (ruling T6-2)
    txt = os.path.join(REPO, "mod", "NutritionRevamp", "42.20.4", "media", "sandbox-options.txt")
    js = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "Translate", "EN",
                      "Sandbox.json")
    for path in (txt, js):
        with open(path, encoding="utf-8") as fh:
            assert "SatietyBulk" not in fh.read(), path


LIMITATION_FOUR = (
    "HUNGER, THIRST and FATIGUE are written once a game minute; an eat or a drink shows at once and the next write "
    "overwrites it with the satiety target, hungerTarget(sated(F, post(P)), energyState) x the circadian factor x the "
    "acute exercise factor x the sleep-debt factor, capped at 0.69: F is the stomach's fullness mass (its satiety mass plus the protein term) over its 730 g maximum, drunk liquid "
    "counting at a fifth, and P the meal pool, fed at the eat with the eaten vector's weighted kcal and decaying on "
    "game time asleep or awake, so displayed hunger never reaches 0 after a meal (about 0.1 after a typical meal, about 0.09 at a full "
    "stomach), and a vanilla HUNGER below the seed floor reads it on its first minute: hungerTarget(0.797, energy state), that is 0.203 x es + 1.0 x max(0, es - 1), times the minute's circadian, acute and sleep factors "
    "(an empty stomach's read at the seed's cap P_SEED_MAX); protein fills the satiety fullness while it is in the stomach (a fitted game choice); an eat another mod makes through a direct Eat call reaches the stomach and P through the reconcile path a minute late and as its "
    "macros only (no water or fibre mass), and a drink another mod makes through a direct DrinkFluid call outside the "
    "intake's wraps is not seen; an eat landing in a fresh record's first minute, before the writer has seeded P, "
    "shows only through the HUNGER the seed reads; the exercise share of the energy deficit enters hunger through a "
    "lag of weeks, so a regular exerciser who eats to balance reads lower hunger for weeks; heavy work the model does "
    "not class as vigorous (neither the swing state nor the heavy-work band) overshoots the hunger rise of a heavy "
    "labour deficit (S1325); past 730 g in the stomach the mod's own Overfull moodle rises in four levels to 1100 g "
    "(the soft cap: shown, never a block), and vanilla's own refusal to start an eat at the FOOD_EATEN moodle's level "
    "3 stands; fibre sates only through its mass, and carbohydrate, sugar, starch and fat take one weight per kcal (the evidence is mixed or absent: rulings 11c-6 and 11c-7); a vanilla HUNGER above the fullness ceiling, hungerTarget(0.55 F, energy state), that is (1 - 0.55 F) x es + 1.0 x max(0, es - 1), times the minute's circadian, acute and sleep factors, seeds an empty pool, so a fresh character's first written HUNGER drops to that ceiling; short sleep raises hunger by a factor capped at the pooled size, whether a step or graded is unsettled; the sleep factor steps at the acute record's 24 h window close, not at waking, so a short night that straddles the close reaches hunger in two steps a day apart; after a short night, nights of exactly the need repay nothing, so the rise holds until a longer night repays half its excess; right at a bout's end the acute term reads deeper than the pooled immediate-post effect (ruling T1-3); glycogen depletion no longer raises hunger, and a trailing-24 h deficit is bounded by the day's expenditure, so a sedentary fast plateaus at es about 1.13 from about 36 h, the balance term's cap is reached only by very heavy work, and higher energy states come from fat depletion (rulings T4-1 and 9c-1); heat's lowering of intake is not modelled (cold reaches hunger through its expenditure); sugary drinks, ketosis, alcohol's aperitif effect, aerated foods' volume and eating rate are neutral; injury adds no expenditure")


def test_limitation_four_names_the_overwrite_and_the_pool():
    lim = list(Host().NR.server.writer.limitations.values())
    assert len(lim) == 12                                  # the self-report prints the count: kept at 12
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
    assert rec.satiety.P == 6 and rec.satiety.S == 0   # the pool neither decayed nor seeded
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
    assert H1 == pytest.approx(0.1675 * _circ(4 + 1 / 60))


def test_the_energy_term_raises_the_hunger_of_a_deficit():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.body.energyState = 1.2                             # Plan 11d Task 9d: at 1.5 the floor's 1.0 reaches the cap
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx((0.1675 * 1.2 + 1.0 * 0.2) * 0.9540165460822252)
    assert p.st.sets.HUNGER == pytest.approx(_hunger(6, es=1.2))


def test_the_written_hunger_is_capped_at_0_69():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.stomachFill = 0.0
    rec.satiety.P = 0.0                                    # an empty stomach and an empty pool: target 1 x c
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
    assert rec.satiety.P == pytest.approx(h.K.satiety.seedP(0.31 / _circ(4 + 1 / 60), 0.6, 1))
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
        assert rec.satiety.S == 0.5 and rec.satiety.P is not None


def test_a_stepped_pool_survives_a_restart():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    saved = h.K.store.inputsOnly(rec)
    saved.body = None                                                       # the stand-in body is no stored body
    back = h.K.store.load(saved, None, None)
    assert back.satiety.P == pytest.approx(6)
    assert back.satiety.S == 0 and back.satiety.L == 0
    back.stomachFill = 0.6                                                  # kinetics stamps it each minute
    back.body = h.rt.eval("{ energyState = 1, rmod = 1 }")
    p2 = player(h)                                                          # the restart: a new object, a new hoist
    step(h, p2, back, 1)
    assert h.NR.server.writer.stats.seeded == 0 and p2.st.sets.HUNGER == pytest.approx(H1)


def test_a_non_finite_or_absent_pool_is_seeded_again():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.31
    rec = record(h)
    rec.satiety.P = float("nan")
    step(h, p, rec, 1)
    W = h.NR.server.writer
    assert p.st.sets.HUNGER == pytest.approx(0.31) and W.stats.seeded == 1
    assert W.stats.guarded == 1                                             # a non-finite P is a heal too
    p2 = player(h, "b")
    p2.st.v.HUNGER = 0.31
    rec2 = record(h)
    rec2.satiety.P = None
    step(h, p2, rec2, 1, name="b")
    assert p2.st.sets.HUNGER == pytest.approx(0.31) and W.stats.seeded == 2
    assert W.stats.guarded == 1                                             # an absent pool is a seed, not a heal


def test_p_decays_at_its_half_life_of_game_time():
    # HALF_LIFE_H 0.7: two game hours leave 6 x 2^(-2 / 0.7) weighted kcal
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 61)
    step(h, p, rec, 121)                                                    # two hour-long steps (the cap is 60 min)
    assert rec.satiety.P == pytest.approx(6 * 2 ** (-2 / 0.7))


def test_sleep_does_not_slow_the_decay():
    h = boot()
    p = player(h)
    p.asleep = True
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 43)                                                     # 42 game minutes: one half-life
    assert rec.satiety.P == pytest.approx(3.0)                             # ruling 11c-24: P runs on game time asleep


def test_hearty_appetite_scales_the_decay_by_one_and_a_half():
    h = boot()
    p = player(h)
    p.getCharacterTraits = h.rt.eval("function(s) return { get = function(c, t) return t == 'HA' end } end")
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 43)
    assert rec.satiety.P == pytest.approx(6 * 2 ** -1.5)                   # #0485, vanilla's game number


def test_light_eater_scales_the_decay_by_three_quarters():
    h = boot()
    p = player(h)
    p.getCharacterTraits = h.rt.eval("function(s) return { get = function(c, t) return t == 'LE' end } end")
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 43)
    assert rec.satiety.P == pytest.approx(6 * 2 ** -0.75)


def test_the_sandbox_decrease_multiplier_scales_the_decay():
    h = boot()
    h.G.getSandboxOptions = h.rt.eval("function() return { getStatsDecreaseMultiplier = function(s) return 2 end } end")
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 43)
    assert rec.satiety.P == pytest.approx(6 * 2 ** -2)                     # ruling 11c-11: trait x sd


def test_a_gap_over_sixty_minutes_decays_over_one_hour_only():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 181)                                                    # three game hours since the last write
    assert rec.satiety.P == pytest.approx(6 * 2 ** (-1 / 0.7))


def test_overlay_steps_p_without_writing_hunger():
    h = boot(mode=2)
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 43)
    assert p.st.sets.HUNGER is None and rec.satiety.P == pytest.approx(3.0)


def test_a_p_the_decay_made_non_finite_is_restamped():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    orig = h.K.satiety.decay
    h.K.satiety.decay = h.rt.eval("function(P, dtH, hl, t) return 0 / 0 end")
    try:
        step(h, p, rec, 2)
    finally:
        h.K.satiety.decay = orig
    assert rec.satiety.P == pytest.approx(6) and h.NR.server.writer.stats.guarded == 1
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
    P = 6 * 2 ** (-0.5 / 0.7)
    assert rec.satiety.P == pytest.approx(P)
    assert p.st.sets.HUNGER == pytest.approx(_hunger(P, minute=31, S=0.25))


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


# --- Plan 11c close (ruling C-1): the writer's decay across a reconnect or a restart --------------------------------
# The writer stamps its last step's world age on record.satiety.t (game hours). A new IsoPlayer object (a reconnect, a
# respawn) or a restart re-hoists h with no ageH, so the step reads the gap from that stamp, clamped at maxStepS (60
# min) as a same-object gap is: P decays at HALF_LIFE_H 0.7 h and S toward 0 at ACUTE_DECAY_HALF_LIFE_H 0.15 h over one hour (ruling 11d-1).

def _fed(h, name="a"):
    p = player(h, name)
    rec = record(h)
    rec.satiety.P = 600.0
    rec.satiety.S = 1.0
    step(h, p, rec, 1, name=name)
    step(h, p, rec, 2, name=name)
    return p, rec


def test_the_writer_stamps_its_step_age_on_the_pool():
    h = boot()
    p = player(h)
    rec = record(h)
    assert rec.satiety.t is None                                            # the fixture's record has no stamp
    step(h, p, rec, 1)
    assert rec.satiety.t == pytest.approx(100.0 + 1 / 60)
    assert rec.satiety.P == 6                                               # no stamp: the first minute steps 0
    step(h, p, rec, 7)
    assert rec.satiety.t == pytest.approx(100.0 + 7 / 60)


def test_a_reconnect_decays_p_and_s_as_the_same_object_does():
    # the review's probe2: a player away 180 game minutes returns as a new object; P and S take the 60-minute catch-up
    h = boot()
    p, same = _fed(h, "a")
    P2, S2 = same.satiety.P, same.satiety.S
    step(h, p, same, 182, name="a")                                         # same object, 180 minutes later
    h2 = boot()
    _, back = _fed(h2, "a")
    assert back.satiety.P == P2 and back.satiety.S == S2
    step(h2, player(h2, "a"), back, 182, name="a")                          # a new object, 180 minutes later
    assert same.satiety.P == pytest.approx(P2 * 2 ** (-1 / 0.7))
    assert same.satiety.S == pytest.approx(S2 * 2 ** (-1 / 0.15))
    assert back.satiety.P == pytest.approx(same.satiety.P)
    assert back.satiety.S == pytest.approx(same.satiety.S)
    assert back.satiety.t == pytest.approx(100.0 + 182 / 60)


def test_a_reconnect_inside_the_clamp_decays_over_the_gap():
    h = boot()
    _, rec = _fed(h)
    P2 = rec.satiety.P
    step(h, player(h), rec, 23)                                             # a new object 21 minutes later
    assert rec.satiety.P == pytest.approx(P2 * 2 ** (-(21 / 60) / 0.7))


def test_a_restart_through_the_store_decays_the_pool():
    h = boot()
    W = h.NR.server.writer
    _, rec = _fed(h)
    P2, S2 = rec.satiety.P, rec.satiety.S
    saved = h.K.store.inputsOnly(rec)
    saved.body = None                                                       # the stand-in body is no stored body
    back = h.K.store.load(saved, None, None)
    assert back.satiety.t == pytest.approx(100.0 + 2 / 60)                  # INPUTS carry satiety.t
    back.stomachFill = 0.6
    back.body = h.rt.eval("{ energyState = 1, rmod = 1 }")
    W.h["a"] = None                                                         # the restart: no hoist survives
    step(h, player(h), back, 182)
    assert W.stats.seeded == 0
    assert back.satiety.P == pytest.approx(P2 * 2 ** (-1 / 0.7))
    assert back.satiety.S == pytest.approx(S2 * 2 ** (-1 / 0.15))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_a_non_finite_stamp_heals_and_counts(bad):
    h = boot()
    W = h.NR.server.writer
    _, rec = _fed(h)
    P2 = rec.satiety.P
    rec.satiety.t = bad
    step(h, player(h), rec, 182)                                            # a new object: the stamp is read
    assert rec.satiety.P == P2                                              # read as no stamp: the minute steps 0
    assert W.stats.guarded == 1
    assert rec.satiety.t == pytest.approx(100.0 + 182 / 60)                 # re-stamped


def test_a_v3_or_fresh_record_has_no_stamp_and_steps_zero_on_its_first_minute():
    h = boot()
    p = player(h)
    rec = h.K.store.new("a", 100.0)
    rec.satiety = h.rt.eval("{ P = 6, S = 0.5 }")
    step(h, p, rec, 181)
    assert rec.satiety.P == 6 and rec.satiety.S == 0.5
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
    assert W.satietyF(rec) == pytest.approx((150 + 8 * 46.5) / 730)        # the writer's F: the protein fills
    assert W.satietyF(rec) > rec.stomachFill
    h.K.satiety.PROTEIN_FILL = 0
    try:
        assert h.K.stomach.fill(st) == rec.stomachFill and W.satietyF(rec) == pytest.approx(150 / 730)
    finally:
        h.K.satiety.PROTEIN_FILL = 8


def test_the_written_hunger_reads_the_protein_term():
    h = boot()
    p, p0 = player(h), player(h, "b")
    rec, rec0 = record(h, stomach=chicken_stomach(h)), record(h, stomach=chicken_stomach(h))
    rec0.stomach.buffer.proteins = 0                                        # the same mass less its protein term
    rec0.stomach.buffer.water = rec0.stomach.buffer.water + 46.5
    step(h, p, rec, 1)
    step(h, p0, rec0, 1, name="b")
    F = (150 + 8 * 46.5) / 730
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
# The written HUNGER is min(0.69, hungerTarget(sated(F, post(P)), es) x circadian(h) x acuteFactor(S) x
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
    rec.body.energyState = 1.1                             # (0.1675 x 1.1 + 0.1) x 0.954 = 0.271; x 1.18 under the cap
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(_hunger(6, es=1.1) * 1.18)
    h2 = boot()
    p2 = player(h2)
    rec2 = record(h2)
    rec2.stomachFill = 0.0
    rec2.satiety.P = 0.0                                   # target 1 x 0.954: the cap binds with or without the debt
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
    assert p.st.sets.HUNGER == pytest.approx(H1)


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
            assert rec.satiety.S == 0.5 and rec.satiety.P is not None


def test_the_seed_divides_by_the_sleep_factor():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.31
    rec = record(h)
    rec.satiety = None
    rec.acute.debtH = 2.0
    step(h, p, rec, 1)
    assert rec.satiety.P == pytest.approx(h.K.satiety.seedP(0.31 / (_circ(4 + 1 / 60) * 1.18), 0.6, 1))
    assert p.st.sets.HUNGER == pytest.approx(0.31)


# --- Plan 11d Task 6 fix (ruling T6-1): the divisor guard. A product the factors make non-finite or not positive reads
# 1: the write is the factor-1 target and the seed divides by 1, so P is seeded finite.

@pytest.mark.parametrize("bad", ["0/0", "0"])
def test_a_non_finite_or_zero_factor_product_reads_one(bad):
    h = boot()
    h.K.satiety.acuteFactor = h.rt.eval("function(S) return %s end" % bad)
    p = player(h)
    step(h, p, record(h), 1)
    assert p.st.sets.HUNGER == pytest.approx(0.1675)                       # hungerTarget x 1: no circadian either
    h2 = boot()
    h2.K.satiety.circadian = h2.rt.eval("function(hour) return %s end" % bad)
    p2 = player(h2)
    p2.st.v.HUNGER = 0.31
    rec = record(h2)
    rec.satiety = None
    step(h2, p2, rec, 1)
    assert math.isfinite(rec.satiety.P) and rec.satiety.P == pytest.approx(h2.K.satiety.seedP(0.31, 0.6, 1))
    assert rec.satiety.P > 0 and p2.st.sets.HUNGER == pytest.approx(0.31)


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
# floor: an empty stomach under a HUNGER below it seeds P_SEED_MAX and writes hungerTarget(0.797, es) = 0.203 es +
# 1.0 max(0, es - 1) times the factors; ceiling: a HUNGER above hungerTarget(0.55 F, es) x the factors seeds P = 0
# and writes that ceiling. Review B's case moved to es 1.1 (Plan 11d Task 9d: at es 1.5 the floor's 1.0 reaches the cap).

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
    assert written == pytest.approx((0.203 * es + 1.0 * max(0.0, es - 1)) * fac, abs=5e-4)
    assert written > 0.203 * es * fac                                      # the old clause's form reads short
    if es == 1.1:
        assert round(written, 4) == 0.3508


@pytest.mark.parametrize("es", [1.5, 2.0])
def test_the_seed_ceiling_reads_hunger_targets_deficit_term(es):
    written, fac = _seeded(es, 0.68, 1.0, 1, S=0.5)
    assert written == pytest.approx(min(1.0, (1 - 0.55) * es + 1.0 * max(0.0, es - 1)) * fac)   # hungerTarget clamps at 1
    assert written < 0.68
