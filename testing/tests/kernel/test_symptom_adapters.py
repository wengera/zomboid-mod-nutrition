"""The symptom adapters (Plan 18 Task 3; spec docs/superpowers/specs/2026-10-21-symptoms-design.md, sections 2-3).

K.effects.symptoms (Task 2) leaves on record.effects the added pain per body part (E.pain, E.painOn), the endurance cap
(E.enduranceCap, the lower of the Overfull row's and the causes') and the mood floors (E.stressFloor, E.unhappyFloor).
These cases pin what the server makes of them:

- the effects adapter sets each painful part's added pain (BodyPart.setAdditionalPain) once a player-minute while its
  cause is active, only when the part reads under the target, so a higher added pain (vanilla's treatment actions add
  to it) is never lowered, and makes no body-part call at all with no cause active;
- the writer folds the floors in through its existing ops: STRESS toward the higher of the rows' target and the floor,
  UNHAPPINESS's floor the higher of the effects' target and the floor, released by the fall when the floor drops (#3119,
  Task 2 review carry C2);
- the endurance cap path is unchanged when only the Overfull row applies.

Driven on golden_trace's decorated player (its parts answer FromIndex and the added pain; NR_T.decayPain applies
vanilla's server decay between minutes by hand) and on test_writer_shape's crafted record.
"""
import pytest

from . import golden_trace
from .test_writer_shape import boot, player, record, step

HEAD = 8            # BodyPartType.Head's ordinal (VANILLA BodyPartType.<clinit> L21)
DECAY_90 = 0.9      # vanilla's added-pain decay a game minute at the 90-minute day (0.01 x dayMin, Plan 18 Task 1 J3)


def _minute(h, m):
    h.T.age = golden_trace.START_AGE + m / 60.0
    h.minute()
    h.tick(golden_trace.TICKS)


def _g1(dehydrated=True):
    """g1 online four minutes, then (dehydrated) its body water set 12 % short: dehydration (code 6) active, Head its
    pain part. Returns the host, the stand-in and the record."""
    h = golden_trace.new_host()
    g1 = golden_trace._new_player(h, "g1", golden_trace.MACROS["g1"])
    h.online(g1)
    for m in range(1, 4):
        _minute(h, m)
    rec = h.record("g1")
    if dehydrated:
        b = rec["body"]
        rec["fluids"]["water"] = -0.12 * (b["fm"] + b["lm"] + b["lx"]) * 1000.0
    _minute(h, 4)
    return h, g1, rec


def _head(g1):
    return g1.st.parts["Head"]


def test_a_painful_part_is_set_to_its_target_once_a_player_minute_under_vanillas_decay():
    h, g1, rec = _g1()
    assert rec["drain"]["mask"] == 32 and rec["effects"]["painOn"] is True
    target = rec["effects"]["pain"][HEAD]
    head = _head(g1)
    assert head.addPain == target and head.painSets == 1
    for m in range(5, 15):
        h.T.decayPain(DECAY_90)
        _minute(h, m)
        assert head.addPain == rec["effects"]["pain"][HEAD]
    assert head.painSets == 11
    # no other part takes added pain: the stand-in made only the Head part on demand
    others = [n for n in g1.st.parts.keys() if n != "Head" and g1.st.parts[n].painSets is not None]
    assert others == []


def test_the_part_is_looked_up_once_and_again_only_after_a_first_sight():
    # the lookup (FromIndex, getBodyPart) is kept on the adapter's transient memory: the first painful minute pays it,
    # later minutes none; a forget (first sight, departure) or a new record looks it up again
    h = golden_trace.new_host()
    C = h.rt.eval("{ n = 0 }")
    h.rt.eval("function(C) local f = BodyPartType.FromIndex; BodyPartType.FromIndex = function(i) C.n = C.n + 1; return f(i) end end")(C)
    g1 = golden_trace._new_player(h, "g1", golden_trace.MACROS["g1"])
    h.online(g1)
    for m in range(1, 4):
        _minute(h, m)
    assert C.n == 0
    rec = h.record("g1")
    b = rec["body"]
    rec["fluids"]["water"] = -0.12 * (b["fm"] + b["lm"] + b["lx"]) * 1000.0
    for m in range(4, 14):
        h.T.decayPain(DECAY_90)
        _minute(h, m)
    assert C.n == 1 and _head(g1).painSets == 10
    h.NR.server.effects.forget("g1")
    h.T.decayPain(DECAY_90)
    _minute(h, 14)
    assert C.n == 2 and _head(g1).painSets == 11


def test_a_part_already_at_or_over_its_target_is_not_written():
    # vanilla's treatment actions add to a part's added pain (ISDisinfect, ISStitch, ISRemoveBullet, ISCleanBurn: set(get
    # + n)): a minute never lowers it, and resumes the target once vanilla's decay brings it under
    h, g1, rec = _g1()
    head = _head(g1)
    head.addPain = 60.0
    sets = head.painSets
    for m in range(5, 9):
        _minute(h, m)
    assert head.addPain == 60.0 and head.painSets == sets
    head.addPain = rec["effects"]["pain"][HEAD] - 0.5
    _minute(h, 9)
    assert head.addPain == rec["effects"]["pain"][HEAD] and head.painSets == sets + 1
    _minute(h, 10)                                      # exactly at the target (no decay): no write
    assert head.painSets == sets + 1


def test_no_cause_makes_no_body_part_call():
    h, g1, rec = _g1(dehydrated=False)
    C = h.rt.eval("{ n = 0, by = {} }")
    from .test_minute_pipeline import ENGINE_COUNT
    h.rt.eval(ENGINE_COUNT)(g1, C)
    for m in range(5, 15):
        _minute(h, m)
    assert rec["drain"]["mask"] == 0 and rec["effects"]["painOn"] is False
    for k in ("getAdditionalPain", "setAdditionalPain"):
        assert (C.by[k] or 0) == 0, k
    assert C.by["getBodyPart"] == 4 * 10          # Metabolism's four leg parts a minute only (the splint read)
    assert g1.st.parts["Head"] is None            # no part looked up by index


def test_the_pain_stops_when_the_cause_stops_and_decays_on_its_own():
    h, g1, rec = _g1()
    head = _head(g1)
    rec["fluids"]["water"] = 0.0
    h.T.decayPain(DECAY_90)
    _minute(h, 5)
    assert rec["drain"]["mask"] == 0 and rec["effects"]["painOn"] is False
    sets, left = head.painSets, head.addPain
    for m in range(6, 10):
        h.T.decayPain(DECAY_90)
        _minute(h, m)
    assert head.painSets == sets
    assert head.addPain == pytest.approx(max(0.0, left - 4 * DECAY_90))


def test_a_dead_record_takes_no_pain():
    h, g1, rec = _g1()
    head = _head(g1)
    sets = head.painSets
    rec["dead"] = True
    h.T.decayPain(DECAY_90)
    h.NR.server.effects.minute("g1", g1, rec, rec["body"], 1.0, h.T.age, None)
    assert head.painSets == sets


# --- the writer's floors ------------------------------------------------------------------------------------------

STRESS_RISE = 5.0e-5 * 60      # K.hybrid.defaults moodRiseStress a game second, one 60-second minute
UNHAPPY_RISE = 22 / 3600 * 60  # moodRiseUnhappy


def _writer(**effects):
    h = boot()
    p = player(h)
    rec = record(h)
    for k, v in effects.items():
        rec.effects[k] = v
    return h, p, rec


def test_the_stress_floor_raises_stress_when_over_the_rows_target():
    h, p, rec = _writer(stressTarget=0.1, stressFloor=0.30)
    step(h, p, rec, 1)                                  # the first minute steps 0 seconds (no stamp yet)
    step(h, p, rec, 2)
    assert p.st.sets["STRESS"] == pytest.approx(STRESS_RISE)
    p.st.v["STRESS"] = 0.299
    step(h, p, rec, 3)
    assert p.st.sets["STRESS"] == pytest.approx(0.30)


def test_the_rows_stress_target_wins_when_higher_and_no_floor_reads_as_before():
    h, p, rec = _writer(stressTarget=0.4, stressFloor=0.30)
    step(h, p, rec, 1)
    p.st.v["STRESS"] = 0.399
    step(h, p, rec, 2)
    assert p.st.sets["STRESS"] == pytest.approx(0.4)
    h2, p2, rec2 = _writer(stressTarget=0.0)          # no floor field at all: no write, as before Plan 18
    step(h2, p2, rec2, 1)
    assert p2.st.sets["STRESS"] is None


def test_the_unhappiness_floor_raises_unhappiness_over_the_effects_target():
    h, p, rec = _writer(unhappyTarget=5, unhappyFloor=25)
    step(h, p, rec, 1)
    step(h, p, rec, 2)
    assert p.st.sets["UNHAPPINESS"] == pytest.approx(UNHAPPY_RISE)
    assert rec.moodLast.u == 25
    h2, p2, rec2 = _writer(unhappyTarget=30, unhappyFloor=25)
    step(h2, p2, rec2, 1)
    assert rec2.moodLast.u == 30


def test_a_dropping_unhappiness_floor_releases_its_fall():
    # Task 2 review carry C2: vanilla never lowers UNHAPPINESS between writes (x493), so the floor's release is #3119's
    # subtraction: a floor falling from 50 to 0 lowers the stat by 50, whatever else raised it
    h, p, rec = _writer(unhappyFloor=50)
    p.st.v["UNHAPPINESS"] = 50
    step(h, p, rec, 1)
    assert rec.moodLast.u == 50
    p.st.v["UNHAPPINESS"] = 53                         # another source raised it 3 over the floor
    rec.effects.unhappyFloor = 0
    step(h, p, rec, 2)
    assert p.st.sets["UNHAPPINESS"] == pytest.approx(3)
    assert rec.moodLast.u == 0


def test_the_endurance_cap_path_is_unchanged_when_only_the_overfull_row_applies():
    # the Overfull row alone (Plan 15 Task 8): its 0.73 composes to enduranceCap with no cause, and the writer pulls a
    # higher ENDURANCE to capAt(0.73) = 0.73 at the 90-minute day, as at b335e181
    K = golden_trace.new_host().NR.kernel
    h = golden_trace.new_host()
    E = h.K.effects.new()
    E.rowEndCap = 0.73
    D = h.rt.eval("{ mask = 0, recovering = 0, frac = {} }")
    h.K.effects.symptoms(E, h.NR.data.effects, D, 1, False, 0)
    assert E.symCap == 1 and E.enduranceCap == pytest.approx(0.73)
    hw, p, rec = _writer(enduranceCap=0.73)
    step(hw, p, rec, 1)
    assert p.st.sets["ENDURANCE"] == pytest.approx(K.hybrid.capAt(0.73, 90))
    assert p.st.sets["ENDURANCE"] == pytest.approx(0.73)


# --- the replay host's rows (tools/replay_live.py) ------------------------------------------------------------------

def test_the_replay_rows_carry_the_pain_targets_the_cap_and_the_floors():
    import os
    import sys
    from .server_host import REPO
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import replay_live as RL
    from .test_replay_live_health import START, starve_events
    rows, be = RL.replay_arm(starve_events(3), minutes=12, start_age=START, sleep_allowed=False,
                             paths=("drain.active", "drain.mask"))
    assert "effects.enduranceCap" not in rows[0]       # the first minute's row: no record yet (first sight)
    before = [r for r in rows[1:] if r.get("drain.active") is not True]
    on = [r for r in rows if r.get("drain.active") is True]
    assert before and len(on) >= 8
    for r in before:
        assert r["painTarget"] == 0 and not any(k.startswith("effects.pain.") for k in r)
        assert r["effects.enduranceCap"] == 1 and r["effects.stressFloor"] == 0 and r["effects.unhappyFloor"] == 0
    torso = 7                                            # starvation's part, Torso_Lower (modifier 0.78)
    mod = be.K.effects.PAIN_MOD[torso]
    for r in on:
        assert r["drain.mask"] == 1
        assert r["effects.pain.%d" % torso] == pytest.approx(15 / mod + 0.005 * 90, rel=1e-12)
        assert [k for k in r if k.startswith("effects.pain.")] == ["effects.pain.%d" % torso]
        assert r["painTarget"] == pytest.approx(r["effects.pain.%d" % torso] * mod, rel=1e-12)
        assert r["effects.enduranceCap"] < 1 and r["effects.enduranceCap"] == r["effects.symCap"]
        assert r["ENDURANCE"] == pytest.approx(be.K.hybrid.capAt(r["effects.enduranceCap"], 90), rel=1e-12)
        assert r["STRESS"] <= r["effects.stressFloor"] + 1e-12
    # the stand-in's part holds the written target (no decay modelled by the replay)
    assert be.p.st.parts["Torso_Lower"].addPain == pytest.approx(on[-1]["effects.pain.%d" % torso], rel=1e-12)


def test_a_stale_pain_table_with_no_cause_writes_nothing():
    # the painOn gate (Rule 6): a pain table left non-zero with painOn false is never written (mutant: gate removed)
    h, g1, rec = _g1(dehydrated=False)
    E = rec["effects"]
    E["pain"][HEAD] = 5.0
    E["painOn"] = False
    _minute(h, 5)
    assert g1.st.parts["Head"] is None


def test_a_new_body_object_is_looked_up_again_without_a_forget():
    # the cache's body key (L.painBd): a body the cache did not see is looked up afresh (mutant: key removed)
    h, g1, rec = _g1()
    g2 = golden_trace._new_player(h, "g2", golden_trace.MACROS["g1"])
    bd2 = g2.getBodyDamage(g2)
    h.rt.eval("function(p, bd) p.getBodyDamage = function(s) return bd end end")(g1, bd2)
    h.T.decayPain(DECAY_90)
    _minute(h, 5)
    assert g2.st.parts["Head"] is not None and g2.st.parts["Head"].painSets == 1
