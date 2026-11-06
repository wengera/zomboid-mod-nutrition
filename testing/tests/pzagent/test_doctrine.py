"""The doctrine variant (Plan 31 Task 11, D: `planner/doctrine/`, `Survive(control="doctrine")`): the arbiter's six
priorities and its resume slot, the situation's wants, each intent's `done` and `failed`, and the decision line's keys,
on the fake mod. Every decision rule has a test here that fails without it; the replay over two committed rings is
`test_doctrine_replay.py`."""
import math

import pytest

from agent.base.planner import survive as S
from agent.base.planner.doctrine import constants as K
from agent.base.planner.doctrine import intents as I
from agent.base.planner.doctrine import situation as SI
from agent.base.planner.doctrine.arbiter import Arbiter
from agent.base.planner.doctrine.assess import doctrine_of
from agent.base.planner.doctrine.intents import INTENTS, Intent
from agent.base.planner.doctrine.situation import Memory, Want
from agent.base.planner.doctrine.source import Resume
from agent.base.planner.goals import ExploreToward, LootBuilding

from .fakemod import CAPS_17, MELEE_CAPS
from .test_policies import BAT, Rig, grid, square, zombie
from .test_survive import decisions, last, tick
from .test_survive_ag import SHUT, door_ground
from .test_survive_g import Src, part, zd

CAPS = tuple(MELEE_CAPS)
KILL_END = "kill" if I.MEET else "dead"   # the melee's end on a kill: PZA/1.10's, PZA/1.9's
ME = (100.0, 200.0)


# ================================================================ the fixtures
def rig(tmp_path, goal=None, caps=CAPS, source=None, ground=True):
    r = Rig(tmp_path, caps=caps)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock,
                   source=Src(goal) if source is None else source, control="doctrine")
    if ground:
        r.scan(grid(80, 125, 180, 220))
    return r, sv


def idle(zid, x, y):
    return zd(zid, x, y, has_target=False)


def line(tmp_path):
    return last(tmp_path)


def doc(tmp_path):
    return line(tmp_path)["inputs"]["doctrine"]


def bleed(i=1, bt=5.0):
    return {"bleeding": 1, "parts": [part(i, bleeding=True, bleedingTime=bt)]}


def hold_bandage(r, iid=40):
    r.event("item_added", itemId=iid, fullType="Base.Bandage", weight=0.1, use="bandage")


def wants(r, mem=None, now=None):
    return SI.read(r.world, mem or Memory(), r.clock() if now is None else now)


def kinds(ws):
    return [w.kind for w in ws]


# ================================================================ the arbiter (pure: fake intents)
class Fake(Intent):
    """An intent of any kind and priority whose end the test sets."""

    def __init__(self, want, log):
        self.kind, self.p, self.target, self.ids = want.kind, want.p, want.target, tuple(want.ids)
        self.end, self.log, self.why, self.state, self.m, self.last = None, log, {}, "x", None, None

    def check(self):
        return self.end

    def covers(self, want):
        return want.kind == "strike" and self.kind == "fight" and want.target in self.ids

    def suspend(self):
        self.log.append(("suspend", self.kind))

    def resume(self):
        self.log.append(("resume", self.kind))


def W(kind, target=None, ids=()):
    return Want(K.PRIORITY_NAMES.index(kind), kind, target, {}, ids)


def arb():
    log = []
    a = Arbiter()

    def make(want, prev):
        return Fake(want, log)
    return a, make, log


def test_the_six_priorities_are_in_the_spec_s_order():
    assert K.PRIORITY_NAMES == ("strike", "dress", "avoid", "fight", "door", "order")
    assert (K.P_STRIKE, K.P_DRESS, K.P_AVOID, K.P_FIGHT, K.P_DOOR, K.P_ORDER) == tuple(range(6))
    assert set(INTENTS) == set(K.PRIORITY_NAMES)


def test_a_bleed_preempts_a_travel_and_the_travel_waits_in_the_slot():
    a, make, log = arb()
    a.step([W("order")], make)
    travel = a.current
    ev = a.step([W("dress", 1), W("order")], make)
    assert a.current.kind == "dress" and a.slot is travel and ev["preempted_by"] == {"was": "order", "p": 5}
    assert log == [("suspend", "order")]


def test_a_strike_preempts_every_other_priority():
    for kind in ("dress", "avoid", "fight", "door", "order"):
        a, make, _ = arb()
        a.step([W(kind, 7, (7,))], make)
        was = a.current
        a.step([W("strike", 9, (9,)), W(kind, 7, (7,))], make)
        assert a.current.kind == "strike" and a.slot is was, kind


def test_nothing_of_equal_or_lower_priority_interrupts():
    a, make, _ = arb()
    a.step([W("fight", 1, (1,)), W("order")], make)
    first = a.current
    for ws in ([W("fight", 2, (2,)), W("order")], [W("door", {"x": 1}), W("order")], [W("order")]):
        ev = a.step(ws, make)
        assert a.current is first and ev["preempted_by"] is None
    assert a.equal_switches == 0


def test_a_fight_is_never_preempted_by_a_strike_at_its_own_zombie_but_is_by_one_at_another():
    a, make, _ = arb()
    a.step([W("fight", 1, (1, 2)), W("order")], make)
    fight = a.current
    a.step([W("strike", 2, (2,)), W("fight", 1, (1, 2))], make)
    assert a.current is fight
    a.step([W("strike", 3, (3,)), W("fight", 1, (1, 2))], make)
    assert a.current.kind == "strike" and a.slot is fight


def test_the_loot_resumes_after_the_strike_ends():
    a, make, log = arb()
    a.step([W("order")], make)
    loot = a.current
    a.step([W("strike", 9, (9,)), W("order")], make)
    a.current.end = ("done", "press")
    ev = a.step([W("order")], make)
    assert a.current is loot and ev["resumed"] is True and a.slot is None
    assert ev["ended"] == {"intent": "strike", "p": 0, "end": "done", "why": "press"}
    assert log == [("suspend", "order"), ("resume", "order")]


def test_a_higher_want_starts_before_the_slot_resumes_and_the_slot_is_kept():
    a, make, _ = arb()
    a.step([W("order")], make)
    loot = a.current
    a.step([W("strike", 9, (9,)), W("order")], make)
    a.current.end = ("done", "press")
    a.step([W("dress", 1), W("order")], make)
    assert a.current.kind == "dress" and a.slot is loot


def test_a_slot_intent_that_ended_meanwhile_is_dropped():
    a, make, _ = arb()
    a.step([W("fight", 1, (1,)), W("order")], make)
    fight = a.current
    a.step([W("strike", 9, (9,)), W("fight", 1, (1,))], make)
    fight.end = ("done", "gone")
    a.current.end = ("done", "press")
    ev = a.step([W("order")], make)
    assert a.current.kind == "order" and ev["resumed"] is False and a.slot is None


def test_the_slot_is_one_deep_the_newest_preempted_kept():
    a, make, _ = arb()
    a.step([W("order")], make)
    a.step([W("fight", 1, (1,)), W("order")], make)
    fight = a.current
    a.step([W("strike", 9, (9,)), W("fight", 1, (1,))], make)
    assert a.slot is fight


def test_an_ended_intent_hands_its_end_to_the_next_start():
    a, make, _ = arb()
    a.step([W("fight", 1, (1,)), W("order")], make)
    a.current.end = ("failed", "dud")
    ev = a.step([W("fight", 2, (2,)), W("order")], make)
    assert a.current.target == 2 and ev["ended"]["end"] == "failed" and a.equal_switches == 0


# ================================================================ the situation (pure over a World)
def world(tmp_path, zs=(), weapon=BAT, ground=True, **frame):
    r = Rig(tmp_path, caps=CAPS)
    if ground:
        r.scan(grid(80, 125, 180, 220))
    r.frame(zombies=list(zs), weapon=weapon, **frame)
    return r


def test_one_standing_zombie_near_while_armed_is_fought_whatever_the_health(tmp_path):
    r = world(tmp_path, [zombie(1, 105.0, 200.0)], health=3.0)
    ws = wants(r)
    assert kinds(ws) == ["fight", "order"] and ws[0].target == 1 and ws[0].ids == (1,)


def test_a_zombie_inside_the_strike_radius_is_struck_first(tmp_path):
    r = world(tmp_path, [zombie(1, 101.4, 200.0)])
    ws = wants(r)
    assert kinds(ws)[:2] == ["strike", "fight"] and ws[0].target == 1
    assert ws[0].why["reach"] == pytest.approx(BAT["reach"] + K.STRIKE_MARGIN)


def test_the_strike_radius_is_the_bare_hands_unarmed(tmp_path):
    r = world(tmp_path, [zombie(1, 101.4, 200.0)], weapon=None)
    assert SI.strike_r(r.world) == K.UNARMED_REACH and kinds(wants(r))[0] != "strike"


def test_attackers_strike_the_nearest_standing_one(tmp_path):
    r = world(tmp_path, [zombie(1, 102.5, 200.0)], attackers=1)
    assert kinds(wants(r))[0] == "strike"


def test_three_aware_within_group_r_are_avoided_toward_a_named_refuge(tmp_path):
    r = world(tmp_path, [zombie(1, 104.0, 200.0), zombie(2, 104.5, 201.0), zombie(3, 104.0, 199.0)])
    ws = wants(r)
    assert kinds(ws) == ["avoid", "order"]
    ref = ws[0].target
    assert ref["kind"] == "open" and ref["label"] == "avoid_open" and ref["square"][0] < 100


def test_three_strung_out_are_fought_one_at_a_time(tmp_path):
    r = world(tmp_path, [zombie(1, 102.5, 200.0), zombie(2, 106.0, 200.0), zombie(3, 105.5, 201.0)])
    ws = wants(r)
    assert kinds(ws) == ["fight", "order"] and ws[0].ids == (1,) and ws[0].why["strung"] is True


def test_an_unarmed_pair_is_avoided(tmp_path):
    r = world(tmp_path, [zombie(1, 104.0, 200.0), zombie(2, 104.0, 201.0)], weapon=None)
    assert kinds(wants(r)) == ["avoid", "order"]


def test_an_armed_pair_is_one_fight(tmp_path):
    r = world(tmp_path, [zombie(1, 104.0, 200.0), zombie(2, 104.0, 201.0)])
    ws = wants(r)
    assert kinds(ws) == ["fight", "order"] and set(ws[0].ids) == {1, 2}


def test_an_unaware_zombie_is_not_fought(tmp_path):
    r = world(tmp_path, [idle(1, 105.0, 200.0)])
    assert kinds(wants(r)) == ["order"]


def test_a_fallen_zombie_near_with_none_standing_is_finished(tmp_path):
    z = dict(idle(1, 102.0, 200.0), onFloor=True)
    r = world(tmp_path, [z])
    ws = wants(r)
    assert kinds(ws) == ["fight", "order"] and ws[0].why["downed"] is True


def test_a_failed_avoid_s_hold_turns_the_group_into_the_stance(tmp_path):
    r = world(tmp_path, [zombie(1, 104.0, 200.0), zombie(2, 104.5, 201.0), zombie(3, 104.0, 199.0)])
    mem = Memory(avoid_until=r.clock() + 5.0)
    ws = wants(r, mem)
    assert kinds(ws) == ["fight", "order"] and ws[0].target == 1


def test_a_bleeding_part_with_nothing_within_keep_r_is_dressed(tmp_path):
    r = world(tmp_path, [zombie(1, 106.0, 200.0)], wounds=bleed())
    hold_bandage(r)
    ws = wants(r)
    assert kinds(ws) == ["dress", "fight", "order"] and ws[0].target == 1 and ws[0].why["with"] == "bandage"


def test_a_standing_zombie_within_keep_r_puts_the_dress_off(tmp_path):
    r = world(tmp_path, [zombie(1, 102.0, 200.0)], wounds=bleed())
    hold_bandage(r)
    assert "dress" not in kinds(wants(r))


def test_a_bleed_with_nothing_to_dress_it_marks_the_bandage_want(tmp_path):
    r = world(tmp_path, wounds=bleed())
    mem = Memory()
    assert "dress" not in kinds(wants(r, mem)) and mem.bandage_want is True


def test_a_failed_dress_holds_the_next_until_a_dressing_is_added(tmp_path):
    r = world(tmp_path, wounds=bleed())
    hold_bandage(r)
    mem = Memory(dress_hold=(frozenset(r.world.inventory), r.clock()))
    assert "dress" not in kinds(wants(r, mem))
    hold_bandage(r, 41)
    assert kinds(wants(r, mem))[0] == "dress" and mem.dress_hold is None


def test_a_skipped_zombie_is_not_fought_but_still_struck(tmp_path):
    r = world(tmp_path, [zombie(1, 101.4, 200.0)])
    mem = Memory(skip={1: r.clock() + 5.0})
    assert kinds(wants(r, mem)) == ["strike", "order"]


def test_a_dead_zombie_is_in_no_want(tmp_path):
    r = world(tmp_path, [zombie(1, 101.4, 200.0)])
    mem = Memory(dead={1: r.clock() + 5.0})
    assert kinds(wants(r, mem)) == ["order"]


def test_health_is_read_by_no_want(tmp_path):
    a = kinds(wants(world(tmp_path / "a", [zombie(1, 105.0, 200.0)], health=100.0)))
    b = kinds(wants(world(tmp_path / "b", [zombie(1, 105.0, 200.0)], health=1.0)))
    assert a == b == ["fight", "order"]


@pytest.fixture
def house(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "c").mkdir()
    return tmp_path


def opened(squares):
    """`door_ground` with its door's square read open as a scan reads an open door: its west edge not blocked."""
    return [dict(q, blockW=False) if (q["x"], q["y"]) == (10770, 10633) else q for q in squares]


def door_world(tmp_path, me, zs, door=SHUT, weapon=BAT):
    r = Rig(tmp_path, caps=CAPS)
    ground = door_ground(door)
    r.scan(opened(ground) if door.get("open") else ground)
    r.frame(x=me[0], y=me[1], zombies=[zombie(i, x, y, me=me) for i, x, y in zs], weapon=weapon)
    return r


def test_a_zombie_behind_a_closed_door_is_a_door_decision_never_a_fight(tmp_path):
    me = (10773.0, 10633.5)
    r = door_world(tmp_path, me, [(9, 10769.5, 10633.5)])
    ws = wants(r)
    assert kinds(ws) == ["door", "order"]
    plan = ws[0].target
    assert plan["decision"] == "stance_open" and plan["door"] == (10770, 10633, 0) and plan["zid"] == 9


THREE_BEHIND = [(9, 10769.5, 10633.5), (10, 10768.8, 10633.5), (11, 10768.0, 10633.5)]   # all within DOOR_R of AT_POST
AT_POST = (10771.6, 10633.5)


def test_three_behind_a_door_are_left(house):
    r = door_world(house / "a", AT_POST, THREE_BEHIND)
    ws = wants(r)
    assert kinds(ws) == ["door", "order"] and ws[0].target["decision"] == "leave" and ws[0].why["n_behind"] == 3


def test_a_zombie_behind_a_wall_is_in_no_want(tmp_path):
    me = (10773.0, 10633.5)
    r = door_world(tmp_path, me, [(9, 10769.5, 10631.5)])
    assert kinds(wants(r)) == ["order"]


def test_a_decided_leave_is_not_decided_again_for_the_same_zombies(tmp_path):
    r = door_world(tmp_path, AT_POST, THREE_BEHIND)
    mem = Memory()
    w0 = wants(r, mem)[0]
    mem.doors[w0.target["edge"]] = ("leave", w0.ids, r.clock())
    assert kinds(wants(r, mem)) == ["order"]
    assert kinds(wants(r, mem, now=r.clock() + K.DOOR_DECIDED_S)) == ["door", "order"]


def test_an_open_door_is_no_portal(tmp_path):
    me = (10773.0, 10633.5)
    r = door_world(tmp_path, me, [(9, 10769.5, 10633.5)], door=dict(SHUT, open=True))
    assert kinds(wants(r))[0] == "fight"


def test_a_known_door_outdoors_is_the_refuge_before_open_ground(tmp_path):
    me = (10774.0, 10633.5)
    zs = [(1, 10778.0, 10633.5), (2, 10778.0, 10634.5), (3, 10778.0, 10632.5)]
    r = door_world(tmp_path, me, zs)
    ws = wants(r)
    assert ws[0].kind == "avoid"
    ref = ws[0].target
    assert ref["kind"] == "door" and ref["label"] == "avoid_refuge" and ref["door"] == (10770, 10633, 0)
    assert ref["square"][0] <= 10769   # a room square inside the door


def test_inside_with_the_group_outside_the_building_is_the_refuge(tmp_path):
    me = (10765.5, 10633.5)
    zs = [(1, 10772.0, 10633.5), (2, 10772.0, 10634.5), (3, 10772.0, 10632.5)]
    r = door_world(tmp_path, me, zs, door=dict(SHUT, open=True))
    ref = SI.refuge(r.world, [z for z in r.world.zombies.values()])
    assert ref["kind"] == "inside" and ref["label"] == "avoid_refuge"


def test_a_refused_refuge_square_is_never_chosen_again(tmp_path):
    r = world(tmp_path, [zombie(1, 104.0, 200.0), zombie(2, 104.5, 201.0), zombie(3, 104.0, 199.0)])
    zs = list(r.world.zombies.values())
    first = SI.refuge(r.world, zs)
    second = SI.refuge(r.world, zs, [first["square"]])
    assert second is not None and second["square"][:2] != first["square"][:2]


# ================================================================ the intents on the fake mod
def test_the_doctrine_loads_by_name_and_names_itself_on_the_line(tmp_path):
    r, sv = rig(tmp_path, goal=ExploreToward(110, 200))
    r.frame()
    a = tick(r, sv)
    d = line(tmp_path)
    assert sv.control == "doctrine" and a.type == "scan" and d["branch"] == "goal"
    assert d["inputs"]["doctrine"]["intent"] == "order" and d["inputs"]["doctrine"]["p"] == K.P_ORDER
    assert d["inputs"]["intent"] == {"kind": "travel", "target": [110, 200]}
    assert set(d["inputs"]["doctrine"]) >= {"intent", "p", "why", "state", "target", "preempted_by", "resumed"}


def test_a_strike_sends_the_melee_at_the_zombie_in_reach(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[zombie(1, 101.3, 200.0)])
    a = tick(r, sv)
    d = line(tmp_path)
    assert (a.type, a.args["targetId"], a.args["mode"]) == ("melee", 1, "strike")
    if I.MEET:   # Task 2's meet: no back leg and no swing close in its arguments at all
        assert "backVx" not in a.args and "closeR" not in a.args
    else:        # today's melee: no back step, no swing close
        assert a.args["backVx"] == 0.0 and a.args["backVy"] == 0.0 and a.args["closeR"] == 0.0
    assert a.args["floorSwing"] is True
    assert d["branch"] == "threat" and d["inputs"]["intent"] == {"kind": "strike", "target": 1}
    assert d["inputs"]["doctrine"]["p"] == K.P_STRIKE


def test_the_strike_is_a_shove_under_arm_pain_over_spent_pain(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[zombie(1, 101.3, 200.0)], wounds={"armPain": K.SPENT_PAIN + 1.0})
    a = tick(r, sv)
    assert (a.type, a.args["mode"]) == ("melee", "shove")


def test_a_strike_ends_done_on_its_press_and_hands_the_melee_to_the_fight(tmp_path):
    r, sv = rig(tmp_path)
    zs = [zombie(1, 101.3, 200.0)]
    r.frame(zombies=zs)
    first = tick(r, sv)
    r.answer("progress", "done")   # the span ends: no kill, no counts (a result-less done)
    r.advance(0.5)
    r.frame(zombies=[zombie(1, 103.0, 200.0)])
    tick(r, sv)
    d = doctrine_of(sv)
    assert d.arbiter.current.kind == "fight"
    assert doc(tmp_path)["ended"]["intent"] == "strike"


def test_a_strike_fails_when_the_build_cannot_run_the_melee(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[idle(1, 101.3, 200.0)])
    tick(r, sv)
    r.fake.answer({"melee": [{"state": "failed", "reason": "not loaded"}]})
    r.pump()
    r.frame(zombies=[idle(1, 101.3, 200.0)])
    tick(r, sv)
    ended = doc(tmp_path)["ended"]
    assert ended == {"intent": "strike", "p": 0, "end": "failed", "why": "not loaded"}


def test_a_fight_stands_in_the_stance_facing_a_chaser_beyond_the_melee(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[zombie(1, 106.0, 200.0)])
    a = tick(r, sv)
    d = line(tmp_path)
    assert (a.type, a.args["targetId"], a.args["vx"], a.args["vy"]) == ("aim", 1, 0.0, 0.0)
    assert d["branch"] == "threat" and d["inputs"]["intent"] == {"kind": "fight", "target": 1}
    assert d["inputs"]["doctrine"]["state"] == "stand"


def test_a_fight_closes_on_an_idle_zombie_it_knows(tmp_path):
    r, sv = rig(tmp_path)
    z = dict(idle(1, 108.0, 200.0), known=True)
    r.frame(zombies=[z])
    a = tick(r, sv)
    assert a.type == "walkTo" and a.args["gait"] == "walk" and a.args["x"] > 100.0
    assert doc(tmp_path)["state"] == "close"


def test_a_fight_presses_the_melee_within_its_release(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[zombie(1, 102.2, 200.0)])
    a = tick(r, sv)
    assert (a.type, a.args["mode"]) == ("melee", "strike") and doc(tmp_path)["intent"] == "fight"


def test_a_fight_strings_a_pair_arriving_together(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[zombie(1, 106.0, 200.0), zombie(2, 106.5, 200.5)])
    a = tick(r, sv)
    d = line(tmp_path)
    assert a.type == "aim" and a.args["vx"] < 0.0 and d["inputs"]["intent"]["play"] == "string"
    assert d["inputs"]["doctrine"]["state"] == "string"


def test_a_fight_fails_dud_after_dud_n_strikes_that_lowered_nothing(tmp_path):
    r, sv = rig(tmp_path)
    zs = [zombie(1, 102.2, 200.0)]
    r.frame(zombies=zs)
    tick(r, sv)
    for _ in range(K.DUD_N):
        r.fake.answer({"melee": ["accepted", {"state": "done", "result": {"end": "time", "swings": 1, "hp0": 1.0,
                                                                         "hp1": 1.0}}]})
        r.pump()
        r.advance(0.5)
        r.frame(zombies=zs)
        tick(r, sv)
        if doctrine_of(sv).mem.skip:
            break
    d = doctrine_of(sv)
    assert 1 in d.mem.skip
    assert any(e[:3] == ("fight", K.P_FIGHT, "failed") and e[3] == "dud" for e in d.arbiter.ends)


@pytest.mark.skipif(not I.MEET, reason="Task 2's meet (PZA/1.10) is not on this tree: its `lost` end is new")
def test_a_fight_fails_dud_when_the_meet_ends_lost_no_progress(tmp_path):
    r, sv = rig(tmp_path)
    zs = [zombie(1, 102.2, 200.0)]
    r.frame(zombies=zs)
    tick(r, sv)
    r.fake.answer({"melee": ["accepted", {"state": "done", "result": {"end": "lost", "why": "no progress",
                                                                     "swings": 3, "hp0": 1.0, "hp1": 1.0}}]})
    r.pump()
    r.frame(zombies=zs)
    tick(r, sv)
    d = doctrine_of(sv)
    assert 1 in d.mem.skip and ("fight", K.P_FIGHT, "failed", "dud") in d.arbiter.ends


def test_a_fight_is_not_preempted_by_the_strike_at_its_own_zombie(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[zombie(1, 102.2, 200.0)])
    a = tick(r, sv)
    assert a.type == "melee" and doc(tmp_path)["intent"] == "fight"
    r.answer("accepted")
    n = len(r.acts.history)
    r.frame(zombies=[zombie(1, 101.3, 200.0)])
    tick(r, sv)
    d = doc(tmp_path)
    assert d["intent"] == "fight" and d["preempted_by"] is None and "strike" in d["wants"]
    assert len(r.acts.history) == n   # the running melee goes on: nothing sent


def test_a_fight_fails_stall_when_its_chaser_never_closes(tmp_path):
    r, sv = rig(tmp_path)
    zs = [zombie(1, 106.0, 200.0)]
    for i in range(int(K.STALL_S / 0.5) + 3):
        r.frame(zombies=zs)
        tick(r, sv)
        r.advance(0.5)
    d = doctrine_of(sv)
    assert 1 in d.mem.skip
    assert ("fight", K.P_FIGHT, "failed", "stall") in d.arbiter.ends


def test_a_fight_ends_done_when_its_zombie_is_gone(tmp_path):
    r, sv = rig(tmp_path, goal=ExploreToward(110, 200))
    r.frame(zombies=[zombie(1, 106.0, 200.0)])
    tick(r, sv)
    r.event("zombie_dead", id=1)
    r.frame(zombies=[])
    tick(r, sv)
    assert doc(tmp_path)["ended"] == {"intent": "fight", "p": 3, "end": "done", "why": "gone"}
    assert doc(tmp_path)["intent"] == "order"


def test_a_kill_is_counted_once_and_logged_on_the_threat_why(tmp_path):
    r, sv = rig(tmp_path)
    zs = [zombie(1, 102.2, 200.0)]
    r.frame(zombies=zs)
    tick(r, sv)
    r.fake.answer({"melee": ["accepted", {"state": "done", "result": {"end": KILL_END, "kill": True, "swings": 1,
                                                                     "hp0": 0.2, "hp1": 0.0}}]})
    r.pump()
    r.frame(zombies=zs)
    tick(r, sv)
    d = line(tmp_path)
    assert d["inputs"]["branches"]["threat"]["kill"] == 1 and r.world.kills == 1
    assert 1 in doctrine_of(sv).mem.dead


def test_a_dress_preempts_the_goal_and_the_goal_resumes_after(tmp_path):
    r, sv = rig(tmp_path, goal=ExploreToward(110, 200))
    r.frame()
    tick(r, sv)
    goal = sv.goals.current
    hold_bandage(r)
    r.frame(wounds=bleed(), )
    a = tick(r, sv)
    d = line(tmp_path)
    assert a.type == "stop" and d["branch"] == "care" and d["inputs"]["doctrine"]["intent"] == "dress"
    assert d["inputs"]["doctrine"]["preempted_by"] == {"was": "order", "p": 5}
    assert d["inputs"]["doctrine"]["slot"] == "order"
    r.answer()
    r.frame()   # the part no longer bleeding: the Dress ends done
    tick(r, sv)
    d = doc(tmp_path)
    assert d["ended"]["intent"] == "dress" and d["intent"] == "order" and d["resumed"] is True
    assert sv.goals.current is not None and sv.goals.current.args() == goal.args()
    assert d["resumed_goal"] == "ExploreToward"


def test_a_dress_rides_a_running_walk_for_an_upper_part(tmp_path):
    r, sv = rig(tmp_path, goal=ExploreToward(110, 200))
    sv.goals.kit.explore.scanned.add((100, 200))   # the place scanned: the goal's first send is its walk
    r.frame()
    tick(r, sv)
    r.answer("accepted")
    hold_bandage(r)
    r.frame(wounds=bleed(1))
    a = tick(r, sv)
    assert a.type == "bandage" and a.args["keepMoving"] is True and a.args["part"] == 1


def test_a_dress_that_fails_holds_the_next_off(tmp_path):
    r, sv = rig(tmp_path)
    hold_bandage(r)
    r.frame(wounds=bleed())
    tick(r, sv)
    r.event("item_removed", itemId=40)
    r.answer()
    r.frame(wounds=bleed(), )
    tick(r, sv)
    d = doctrine_of(sv)
    assert ("dress", K.P_DRESS, "failed", "nothing") in d.arbiter.ends
    assert d.mem.dress_hold is not None
    r.frame(wounds=bleed())
    tick(r, sv)
    assert doc(tmp_path)["intent"] == "order"


def test_an_avoid_runs_to_its_refuge_with_the_flee_reason_on_the_threat_why(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[zombie(1, 104.0, 200.0), zombie(2, 104.5, 201.0), zombie(3, 104.0, 199.0)])
    a = tick(r, sv)
    d = line(tmp_path)
    assert a.type == "walkTo" and a.args["gait"] == "run" and a.args["x"] < 100.0
    assert d["branch"] == "threat" and d["inputs"]["branches"]["threat"]["flee"] == "group"
    assert d["inputs"]["intent"]["kind"] == "avoid_open" and d["inputs"]["intent"]["target"] == [
        math.floor(a.args["x"]), math.floor(a.args["y"])]


def test_an_avoid_ends_done_when_the_group_thins_and_the_fight_takes_the_rest(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[zombie(1, 104.0, 200.0), zombie(2, 104.5, 201.0), zombie(3, 104.0, 199.0)])
    tick(r, sv)
    r.event("zombie_dead", id=3)
    r.frame(zombies=[zombie(1, 104.0, 200.0), zombie(2, 104.5, 201.0)])
    tick(r, sv)
    d = doc(tmp_path)
    assert d["ended"] == {"intent": "avoid", "p": 2, "end": "done", "why": "thinned"} and d["intent"] == "fight"


def test_an_avoid_ends_done_clear(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(zombies=[zombie(1, 104.0, 200.0), zombie(2, 104.5, 201.0), zombie(3, 104.0, 199.0)])
    tick(r, sv)
    for zid in (1, 2, 3):
        r.event("zombie_dead", id=zid)
    r.frame(zombies=[])
    tick(r, sv)
    assert doc(tmp_path)["ended"]["why"] == "clear"


def test_an_avoid_holds_the_stance_at_its_refuge_never_a_second_leg(tmp_path):
    r, sv = rig(tmp_path)
    zs = [zombie(1, 104.0, 200.0), zombie(2, 104.5, 201.0), zombie(3, 104.0, 199.0)]
    r.frame(zombies=zs)
    a = tick(r, sv)
    there = (a.args["x"], a.args["y"])
    r.answer()
    me = there
    r.frame(x=me[0], y=me[1], zombies=[zombie(z["id"], me[0] + z["x"] - 100.0, z["y"], me=me) for z in zs])
    a = tick(r, sv)
    d = line(tmp_path)
    assert a.type == "aim" and a.args["vx"] == 0.0 and d["inputs"]["doctrine"]["state"] == "hold"
    assert d["inputs"]["intent"]["kind"] == "fight_hold" and "flee" not in d["inputs"]["branches"]["threat"]


def test_an_avoid_fails_after_its_route_fails_twice_and_the_fight_takes_the_nearest(tmp_path):
    r, sv = rig(tmp_path)
    zs = [zombie(1, 104.0, 200.0), zombie(2, 104.5, 201.0), zombie(3, 104.0, 199.0)]
    r.frame(zombies=zs)
    tick(r, sv)
    for _ in range(K.ROUTE_TRIES):
        r.fake.answer({"walkTo": ["accepted", {"state": "failed", "reason": "stuck"}]})
        r.pump()
        r.frame(zombies=zs)
        tick(r, sv)
    d = doctrine_of(sv)
    assert ("avoid", K.P_AVOID, "failed", "route") in d.arbiter.ends
    assert d.mem.avoid_until > r.clock() and doc(tmp_path)["intent"] == "fight"


def test_an_avoid_with_no_refuge_fails_at_once(tmp_path, monkeypatch):
    monkeypatch.setattr(SI, "refuge", lambda *a, **k: None)
    r, sv = rig(tmp_path)
    r.frame(zombies=[zombie(1, 104.0, 200.0), zombie(2, 104.5, 201.0), zombie(3, 104.0, 199.0)])
    tick(r, sv)
    d = doctrine_of(sv)
    assert ("avoid", K.P_AVOID, "failed", "no refuge") in d.arbiter.ends and doc(tmp_path)["intent"] == "fight"


def test_a_door_with_one_behind_takes_the_post_then_opens(tmp_path):
    me = (10773.0, 10633.5)
    r = Rig(tmp_path, caps=CAPS)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(None), control="doctrine")
    r.scan(door_ground())
    r.frame(x=me[0], y=me[1], zombies=[zombie(9, 10769.5, 10633.5, me=me)])
    a = tick(r, sv)
    d = line(tmp_path)
    assert (a.type, a.args["targetId"], a.args["vx"]) == ("aim", 9, -1.0)
    assert d["inputs"]["intent"] == {"kind": "filter_door", "target": [10770, 10633]}
    assert d["inputs"]["branches"]["threat"]["door_held"]["decision"] == "stance_open"
    r.answer()
    me = (10771.6, 10633.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(9, 10769.5, 10633.5, me=me)])
    a = tick(r, sv)
    assert (a.type, a.args["x"], a.args["y"], a.args["kind"]) == ("interact", 10770, 10633, "open")


def test_a_door_whose_open_fails_is_left(tmp_path):
    me = (10771.6, 10633.5)
    r = Rig(tmp_path, caps=CAPS)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(None), control="doctrine")
    r.scan(door_ground())
    r.frame(x=me[0], y=me[1], zombies=[zombie(9, 10769.5, 10633.5, me=me)])
    a = tick(r, sv)
    assert a.type == "interact"
    r.fake.answer({"interact": ["accepted", {"state": "failed", "reason": "locked"}]})
    r.pump()
    r.frame(x=me[0], y=me[1], zombies=[zombie(9, 10769.5, 10633.5, me=me)])
    tick(r, sv)
    d = doctrine_of(sv)
    assert ("door", K.P_DOOR, "failed", "open locked") in d.arbiter.ends
    assert r.world.marked_doors() and doc(tmp_path)["intent"] == "order"


def test_a_door_left_marks_it_and_hands_the_tick_to_the_order(tmp_path):
    me = (10773.0, 10633.5)
    r = Rig(tmp_path, caps=CAPS)
    goal = ExploreToward(10765, 10633)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(goal), control="doctrine")
    r.scan(door_ground())
    me = AT_POST
    r.frame(x=me[0], y=me[1], zombies=[zombie(i, x, y, me=me) for i, x, y in THREE_BEHIND])
    tick(r, sv)
    d = doc(tmp_path)
    assert d["ended"]["intent"] == "door" and d["ended"]["why"] == "leave" and d["intent"] == "order"
    assert (10770, 10633, 0) in r.world.marked_doors()


def test_the_memory_drops_its_expired_entries(tmp_path):
    r, sv = rig(tmp_path)
    r.frame()
    tick(r, sv)
    d = doctrine_of(sv)
    now = r.clock()
    d.mem.doors[((1, 1, 0), "N")] = ("leave", (9,), now - K.DOOR_DECIDED_S)
    d.mem.doors[((2, 2, 0), "N")] = ("leave", (9,), now)
    d.mem.skip.update({1: now, 2: now + 5.0})
    d.mem.dead.update({3: now - 1.0})
    r.frame()
    tick(r, sv)
    assert list(d.mem.doors) == [((2, 2, 0), "N")] and d.mem.skip == {2: now + 5.0} and d.mem.dead == {}


def test_the_order_runs_the_need_before_the_goal(tmp_path):
    r, sv = rig(tmp_path, goal=ExploreToward(110, 200))
    r.event("item_added", itemId=50, fullType="Base.WaterBottleFull", weight=1.0, use="water")
    r.frame(thirst=0.5)
    a = tick(r, sv)
    d = line(tmp_path)
    assert a.type == "consume" and d["branch"] == "need" and d["inputs"]["intent"] == {"kind": "needs"}


def test_a_goal_superseded_by_a_strike_resumes_after_it(tmp_path):
    r, sv = rig(tmp_path, goal=ExploreToward(110, 200))
    r.frame()
    tick(r, sv)
    r.answer("accepted")
    r.frame(zombies=[idle(1, 101.3, 200.0)])
    a = tick(r, sv)
    assert a.type == "melee"
    r.answer("done")
    r.event("zombie_dead", id=1)
    r.frame(zombies=[])
    tick(r, sv)
    assert sv.goals.history[0]["state"] == "superseded"
    assert sv.goals.current is not None and sv.goals.current.args() == {"x": 110, "y": 200}
    assert doc(tmp_path)["resumed_goal"] == "ExploreToward"


def test_a_goal_is_resumed_at_most_resume_max_times():
    class Inner:
        NAME = "scripted"

        def propose(self, view):
            return None
    s = Resume(Inner())
    row = {"type": "ExploreToward", "args": {"x": 1, "y": 2}, "state": "superseded", "reason": "melee"}
    got = []
    for _ in range(K.RESUME_MAX + 2):
        s.note(row)
        got.append(s.propose({}))
    assert sum(1 for g in got if g is not None) == K.RESUME_MAX
    s.note(dict(row, type="Rest", args={"seconds": 5.0}))
    assert s.queued is None


def test_the_prefetch_asks_the_model_only_and_hands_its_answer_to_the_next_ask():
    class Model:
        NAME = "llm"

        def __init__(self):
            self.asks = 0

        def propose(self, view):
            self.asks += 1
            return ExploreToward(5, 6) if self.asks == 2 else None

        def totals(self):
            return {"n": self.asks}
    m = Model()
    s = Resume(m)
    s.prefetch(dict, 0.0)
    s.prefetch(dict, 1.0)   # under PREFETCH_S: not asked
    s.prefetch(dict, 0.0 + K.PREFETCH_S)
    assert m.asks == 2 and s.held is not None and s.totals() == {"n": 2}
    assert s.propose({}).args() == {"x": 5, "y": 6} and m.asks == 2
    scripted = Resume(Src(ExploreToward(1, 1)))
    scripted.prefetch(dict, 0.0)
    assert scripted.held is None


def test_the_order_prefetches_while_a_loot_runs_and_not_otherwise(tmp_path, monkeypatch):
    r, sv = rig(tmp_path)
    r.frame()
    tick(r, sv)
    d = doctrine_of(sv)
    calls = []
    monkeypatch.setattr(d.source, "prefetch", lambda view_fn, now: calls.append(now))

    class Loot:
        TYPE, running = "LootBuilding", True
    order = d.arbiter.current
    assert order.kind == "order"
    sv.goals.current = Loot()
    order._prefetch()
    sv.goals.current = ExploreToward(1, 1)
    order._prefetch()
    assert calls == [r.clock()]


def test_the_ladder_s_door_read_is_off_under_the_doctrine_only(tmp_path):
    r, sv = rig(tmp_path)
    r.frame()
    tick(r, sv)
    assert sv.DOOR_HELD is False and S.Survive.DOOR_HELD is True
    assert isinstance(sv.goals.source, Resume)


def test_the_decision_line_keeps_the_fork_s_contract(tmp_path):
    r, sv = rig(tmp_path)
    r.frame(x=101.0, y=202.0, zombies=[zombie(1, 106.0, 202.0, me=(101.0, 202.0))])
    tick(r, sv)
    d = line(tmp_path)
    assert (d["inputs"]["x"], d["inputs"]["y"]) == (101.0, 202.0) and d["branch"] == "threat"
    assert {"need", "consume_refused", "cooled", "branches", "doctrine", "intent"} <= set(d["inputs"])
    assert "control" not in d and "control" not in d["inputs"]


def test_equal_priority_switches_read_zero_over_a_mixed_run(tmp_path):
    r, sv = rig(tmp_path, goal=ExploreToward(110, 200))
    script = ([[]] * 2 + [[zombie(1, 106.0, 200.0)]] * 3 + [[zombie(1, 106.0, 200.0), zombie(2, 105.0, 203.0)]] * 3
              + [[zombie(2, 105.0, 203.0)]] * 2 + [[]] * 2)
    for zs in script:
        r.frame(zombies=zs)
        tick(r, sv)
        r.advance(0.5)
    assert doctrine_of(sv).arbiter.equal_switches == 0
    assert len(decisions(tmp_path)) == len(script)


def test_every_send_is_valid_against_the_schema(tmp_path):
    from .test_policies import all_sends_valid
    r, sv = rig(tmp_path, goal=ExploreToward(110, 200))
    for zs in ([], [zombie(1, 106.0, 200.0)], [zombie(1, 101.3, 200.0)],
               [zombie(1, 104.0, 200.0), zombie(2, 104.5, 201.0), zombie(3, 104.0, 199.0)]):
        r.frame(zombies=zs)
        tick(r, sv)
        r.advance(0.5)
    all_sends_valid(r)


def test_the_constants_name_their_sources():
    import inspect
    src = inspect.getsource(K)
    for name in ("GROUP_N", "GROUP_R", "GROUP_CLEAR_R", "ENGAGE_R", "STALL_S", "STRING_GAP"):
        assert name in src and getattr(K, name) is not None
    assert K.GROUP_N == 3 and K.ENGAGE_R == 9.0 and K.GROUP_R == 6.0 and K.GROUP_CLEAR_R == 10.0
