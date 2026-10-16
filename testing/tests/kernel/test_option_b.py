"""Option B (Plan 15 Task 5; spec section 3.1; jar-checks Check 3; run x451): the writer's half.

While the HUNGER or THIRST the writer leaves stands at moodle level 4, NR_Server_Writer holds the player's
severe-moodle constant (BodyDamage.setHealthReductionFromSevereBadMoodles) at 0, so vanilla's day-length-scaled
HUNGRY-4 and THIRST-4 drains never run and the mod's floors own those crises; otherwise it writes back vanilla's value,
read once per player object from the getter. It writes at first sight (the constant is not saved, x451) and then only
when the wanted value changes. While the constant was 0 over the minute just past it re-applies the other terms the
constant carries (SICK 4, BLEEDING 4, HEAVY_LOAD above 2, the 35 kg floor) at vanilla's rates (#2356, #3881, #2922).
The writer is driven directly (test_writer_shape's host and record); the stand-in body damage counts every call.
"""
import pytest

from . import test_writer_shape as WS

BODY = r"""
function(p, C, red, health)
    MoodleType.SICK = "SICK"; MoodleType.BLEEDING = "BLEEDING"; MoodleType.HEAVY_LOAD = "HEAVY_LOAD"
    CharacterStat.ZOMBIE_INFECTION = "ZOMBIE_INFECTION"
    p.st.v.ZOMBIE_INFECTION = 0
    local bd = { red = red, health = health, sets = {}, reduced = {}, wound = 0 }
    local function count(name) C[name] = (C[name] or 0) + 1; C.n = C.n + 1 end
    bd.getHealthReductionFromSevereBadMoodles = function(s) count("get"); return s.red end
    bd.setHealthReductionFromSevereBadMoodles = function(s, v) count("set"); s.red = v; s.sets[#s.sets + 1] = v end
    bd.ReduceGeneralHealth = function(s, v) count("reduce"); s.reduced[#s.reduced + 1] = v; s.health = s.health - v end
    bd.getOverallBodyHealth = function(s) count("health"); return s.health end
    bd.getGeneralWoundInfectionLevel = function(s) count("wound"); return s.wound end
    bd.setDrunkReductionValue = function(s, v) end
    local thermo = { target = 2.0 }
    thermo.getMetabolicTarget = function(t) count("met"); return t.target end
    bd.getThermoregulator = function(s) return thermo end
    p.getBodyDamage = function(s) return bd end
    p.bd, p.thermo = bd, thermo
    p.levels = { SICK = 0, BLEEDING = 0, HEAVY_LOAD = 0 }
    local moodles = { getMoodleLevel = function(m, t) count("level"); return p.levels[t] or 0 end }
    p.getMoodles = function(s) return moodles end
    p.vehicle = nil
    p.getVehicle = function(s) count("vehicle"); return s.vehicle end
    p.strain = {}
    p.addBackMuscleStrain = function(s, v) count("strain"); s.strain[#s.strain + 1] = v end
    return p
end
"""

RED = 0.0165            # the BodyDamage constructor's constant (#0516), as the getter answers it
UNITS_MIN = 2 * 90      # multiplier units a game minute at the 90-minute day (#2922): 120 x 90 / 60


def setup(red=RED, health=100.0, mode=1):
    h = WS.boot(mode)
    p = WS.player(h)
    C = h.rt.eval("{ n = 0 }")
    h.rt.eval(BODY)(p, C, red, health)
    return h, p, C


def starving(h, **over):
    rec = WS.record(h, **over)
    rec.drain = h.rt.table_from({"starving": True, "dehydrated": False})
    return rec


def sets(p):
    return [p.bd.sets[i] for i in range(1, len(p.bd.sets) + 1)]


def reduced(p):
    return [p.bd.reduced[i] for i in range(1, len(p.bd.reduced) + 1)]


def test_the_first_sight_writes_vanillas_value_read_from_the_getter_and_a_steady_minute_calls_nothing():
    h, p, C = setup(red=0.02)                       # not the literal: whatever the getter answers is vanilla's
    rec = WS.record(h)
    WS.step(h, p, rec, 1)
    assert sets(p) == [0.02] and C.get == 1         # written at first sight (unsaved, x451), read once
    n = C.n
    for m in range(2, 12):
        WS.step(h, p, rec, m)
    assert C.n == n                                 # Rule 6: no Java call on a steady minute
    assert h.NR.server.writer.h["a"].red == 0.02


def test_level_4_sets_the_constant_to_0_and_its_end_restores_vanillas():
    h, p, C = setup()
    rec = starving(h)
    WS.step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(0.71)  # the starving minimum, over HUNGRY 4's strict 0.70
    assert sets(p) == [0]
    WS.step(h, p, rec, 2)
    assert sets(p) == [0]                           # held: no second write
    rec.drain = None                                # starvation ends: HUNGER falls under 0.69 again
    WS.step(h, p, rec, 3)
    assert p.st.sets.HUNGER <= 0.69 and sets(p) == [0, RED]


def test_parched_thirst_sets_the_constant_to_0():
    h, p, C = setup()
    rec = WS.record(h)
    rec.fluids.thirstTarget = 0.9
    WS.step(h, p, rec, 1)
    assert p.st.sets.THIRST == pytest.approx(0.83) and sets(p) == [RED]     # capped under level 4: vanilla's value
    rec.drain = h.rt.table_from({"starving": False, "dehydrated": True})
    WS.step(h, p, rec, 2)
    assert p.st.sets.THIRST == pytest.approx(0.9) and sets(p) == [RED, 0]   # the cap lifts: Parched, constant 0


def test_overlay_never_touches_the_constant():
    h, p, C = setup(mode=2)
    rec = starving(h)
    for m in range(1, 4):
        WS.step(h, p, rec, m)
    assert sets(p) == [] and (C.get or 0) == 0


def test_a_new_player_object_is_written_at_its_first_sight():
    # a reload, a reconnect or a respawn builds a new BodyDamage at the constructor's value (x451's E): the new hoist
    # writes the wanted value again whatever the last object held
    h, p, C = setup()
    rec = starving(h)
    WS.step(h, p, rec, 1)
    assert sets(p) == [0]
    p2 = WS.player(h)
    C2 = h.rt.eval("{ n = 0 }")
    h.rt.eval(BODY)(p2, C2, RED, 100.0)
    WS.step(h, p2, rec, 2)
    assert sets(p2) == [0] and C2.get == 1


def test_an_unreadable_constant_is_never_written():
    h, p, C = setup(red=0)                          # no positive read: no value to restore, so the writer stays off
    rec = starving(h)
    for m in range(1, 4):
        WS.step(h, p, rec, m)
    assert sets(p) == [] and C.get == 1
    assert h.NR.server.writer.severeStats.unread == 1


def test_no_term_is_re_applied_on_the_minute_the_constant_first_goes_to_0():
    h, p, C = setup()
    p.levels.SICK = 4
    rec = starving(h, effects=h.rt.table_from({"foodSickTarget": 90}))
    p.st.v.FOOD_SICKNESS = 90
    WS.step(h, p, rec, 1)                           # the constant was vanilla's over the minute just past
    assert reduced(p) == [] and (C.level or 0) == 0


@pytest.mark.parametrize("sick,food,zombie,want", [(4, 90, 0, 1), (4, 10, 20, 0), (3, 90, 0, 0)])
def test_sickness_4_on_the_food_arm_is_re_applied_at_the_whole_constant(sick, food, zombie, want):
    h, p, C = setup()
    rec = starving(h)
    WS.step(h, p, rec, 1)
    p.levels.SICK = sick
    p.st.v.FOOD_SICKNESS = food
    p.st.v.ZOMBIE_INFECTION = zombie
    WS.step(h, p, rec, 2)
    got = reduced(p)
    if want:
        assert got == [pytest.approx(RED * UNITS_MIN)]      # 2.97 a game minute: 178.2 a game hour (#2356, #2922)
    else:
        assert got == []


def test_the_wound_infection_arm_needs_the_option():
    h, p, C = setup()
    rec = starving(h)
    WS.step(h, p, rec, 1)
    p.levels.SICK = 4
    p.st.v.FOOD_SICKNESS = 0
    p.bd.wound = 30
    WS.step(h, p, rec, 2)
    assert reduced(p) == []                         # WoundInfectionFactor absent (its default 0): the arm is off
    h.G.SandboxVars.WoundInfectionFactor = 1
    WS.step(h, p, rec, 3)
    assert reduced(p) == [pytest.approx(RED * UNITS_MIN)]


def test_bleeding_4_is_re_applied_and_the_day_length_scales_it():
    h, p, C = setup()
    rec = starving(h)
    WS.step(h, p, rec, 1)
    p.levels.BLEEDING = 4
    WS.step(h, p, rec, 2)
    assert reduced(p) == [pytest.approx(RED * UNITS_MIN)]
    h.G.getSandboxOptions = h.rt.eval("function() return { getDayLengthMinutes = function(s) return 60 end } end")
    h.NR.so = None
    WS.step(h, p, rec, 3)
    assert reduced(p)[1] == pytest.approx(RED * 2 * 60)    # 11.88 / 60 a game minute on the 60-minute day (#0518's scale)
    p.levels.BLEEDING = 3
    WS.step(h, p, rec, 4)
    assert len(reduced(p)) == 2


def test_heavy_load_is_its_expected_value_held_at_75_with_half_to_back_strain():
    h, p, C = setup()
    rec = starving(h)
    WS.step(h, p, rec, 1)
    p.levels.HEAVY_LOAD = 3
    WS.step(h, p, rec, 2)
    y = RED * UNITS_MIN / 2                         # 0.1 x the constant over (5 - 3) / 10, per unit
    assert reduced(p) == [pytest.approx(y)] and p.strain[1] == pytest.approx(y / 2)
    p.levels.HEAVY_LOAD = 4
    p.bd.health = 75.5
    WS.step(h, p, rec, 3)
    assert reduced(p)[1] == pytest.approx(0.5)     # held to health - 75: vanilla's term stops at 75
    WS.step(h, p, rec, 4)
    assert len(reduced(p)) == 2                     # at 75: off


@pytest.mark.parametrize("cond", ["asleep", "vehicle", "seated", "level2"])
def test_heavy_load_waits_on_its_conditions(cond):
    h, p, C = setup()
    rec = starving(h)
    WS.step(h, p, rec, 1)
    p.levels.HEAVY_LOAD = 4
    if cond == "asleep":
        p.asleep = True
    elif cond == "vehicle":
        p.vehicle = h.rt.table()
    elif cond == "seated":
        p.thermo.target = 1.0                       # SeatedResting's MET (#2632)
    else:
        p.levels.HEAVY_LOAD = 2
    WS.step(h, p, rec, 2)
    assert reduced(p) == [] and len(p.strain) == 0


def test_the_35_kg_floor_is_re_applied_as_one_set_weight_call():
    h, p, C = setup()
    rec = starving(h, body=h.rt.table_from({"energyState": 1, "rmod": 1, "fm": 1.0, "lm": 33.0, "lx": 0.5}))
    WS.step(h, p, rec, 1)
    h.rt.eval("function() local g = getGameTime; getGameTime = function() local t = g(); "
              "t.getMultiplier = function(s) return 1.6 end; return t end end")()
    WS.step(h, p, rec, 2)
    assert reduced(p) == [pytest.approx(RED * 1.6)]       # the constant x the multiplier, per call (#3881)
    rec.body.fm = 1.6                                      # 35.1 kg: over the floor
    WS.step(h, p, rec, 3)
    assert len(reduced(p)) == 1


def test_every_term_together_is_one_health_call():
    h, p, C = setup()
    rec = starving(h)
    WS.step(h, p, rec, 1)
    p.levels.SICK, p.levels.BLEEDING, p.levels.HEAVY_LOAD = 4, 4, 4
    p.st.v.FOOD_SICKNESS = 90
    WS.step(h, p, rec, 2)
    assert reduced(p) == [pytest.approx(3 * RED * UNITS_MIN)]
    assert h.NR.server.writer.severeStats.reapplied == 1


def test_the_last_minute_at_0_is_still_re_applied_as_the_constant_returns():
    h, p, C = setup()
    rec = starving(h)
    WS.step(h, p, rec, 1)
    p.levels.BLEEDING = 4
    rec.drain = None
    WS.step(h, p, rec, 2)                           # the minute just past ran at 0: re-applied, then restored
    assert reduced(p) == [pytest.approx(RED * UNITS_MIN)] and sets(p) == [0, RED]
    WS.step(h, p, rec, 3)
    assert len(reduced(p)) == 1                     # vanilla's own term runs again


def test_without_water_level_3_shows_near_24_h_and_parched_near_32_h():
    # the whole server pipeline (tools/replay_live.replay_arm), the default body at rest with nothing drunk: the new
    # thirst knots with the osmotic drive put level 3 (THIRST over 0.70) at 3 % and Parched (over 0.84) at the 4 %
    # dehydration onset, where the writer's 0.83 cap lifts (vanilla: 24.3 h and 29.17 h at its own rate, #0495); the
    # deficit reaches 3 % at 24.0 h and 4 % at 32.0 h on the water base (Plan 15 Task 4 fix 1's timeline). The
    # suggested 3 % knot of 0.70 read level 3 at 20.6 h here, the osmotic drive adding about 0.45 at 3 %.
    import os
    import sys
    tools = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                         "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import replay_live as RL
    rows, _ = RL.replay_arm([], minutes=40 * 60, start_age=100.0, dtM=1.0, paths=["fluids.dehydPct", "drain.dehydrated"])
    t0 = rows[0]["age"] - 1 / 60

    def first(pred):
        for r in rows:
            if pred(r):
                return r["age"] - t0
        return None

    l3 = first(lambda r: r.get("THIRST", 0) > 0.70)
    l4 = first(lambda r: r.get("THIRST", 0) > 0.84)
    onset = first(lambda r: r.get("drain.dehydrated") is True)
    assert l3 == pytest.approx(24.0, abs=0.5)
    assert l4 == pytest.approx(32.0, abs=0.5)
    assert onset is not None and abs(l4 - onset) <= 2 / 60          # Parched shows with the dehydration state
    assert max(r.get("THIRST", 0) for r in rows if r["age"] - t0 < onset) <= 0.83 + 1e-12   # capped under level 4 before it
