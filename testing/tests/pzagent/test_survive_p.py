"""Survival 12 (survival iteration 11; Plan 24 Task 32): ruling P24-AO, the doorway stand (`planner/doorway.py`): a
`many` flee against at most DOOR_STAND_N standing zombies within DANGER_R takes a known building's door and, where the
close would go, fights in the doorway from the square inside the threshold; it leaves only once DANGER_R has been
empty for DOOR_HOLD_S, under the health flee line or unarmed, the door then closed from inside as today's shelter
close. The fake mod over PZA/1.7, on `test_survive`'s shelter world (building 1's 3 x 3 interior at x 112, its west
door at (112, 201), the approach square (111, 201))."""
import pytest

from agent.base.planner import doorway as D
from agent.base.planner import survive as S

from .test_night import CLOSED, OPEN
from .test_policies import CAPS_14, all_sends_valid, zombie
from .test_survive import group, make, shelter_world, threat_why, tick

POST = (112.5, 200.5)   # the enter step's square inside the threshold (the plan's `inside`)


def z(zid, x, y, me=POST, floor=False, has_target=True):
    return dict(zombie(zid, x, y, me=me), onFloor=True if floor else None, hasTarget=has_target)


def why(r):
    return threat_why(r.dir)


def to_post(r, sv, zs=None, **frame):
    """Run the `many` flee's shelter steps (approach, open, enter) to the post; return the tick's command."""
    shelter_world(r, CLOSED)
    r.frame(x=100.0, y=201.5, zombies=zs or group(), **frame)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 201.5, "gait": "run"}) and why(r)["flee"] == "many"
    r.answer()
    me = (111.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=group(8.0, me), **frame)
    tick(r, sv)
    assert r.cmd()[1]["kind"] == "open"
    r.answer()
    shelter_world(r, OPEN)
    r.frame(x=me[0], y=me[1], zombies=group(8.0, me), **frame)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 112.5, "y": 200.5, "gait": "run"})
    r.answer()
    r.frame(x=POST[0], y=POST[1], zombies=group(8.0, POST), **frame)
    a = tick(r, sv)
    return a


def stood(tmp_path, **k):
    r, sv = make(tmp_path, **k)
    a = to_post(r, sv)
    assert a is not None and a.type == "aim" and why(r)["doorway"] == 1 and sv.flee.plan["step"] == "stand"
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    return r, sv


def test_the_doorway_constants():
    assert (D.DOOR_STAND_N, D.DOOR_HOLD_S) == (3, 10.0) and S.Survive.DOORWAY is True


def test_a_many_flee_against_three_takes_the_door_and_stands_in_it_instead_of_closing_it(tmp_path):
    """P24-AO: the shelter steps run as today to the enter; where the close went, the stand: the Doorway fight (mode
    `fight`, the Flee and its plan kept), the stance held facing the nearest listed zombie (an `aim` of (0, 0)), the
    plan marked a stand at the pick (`stand`, its door's way kept)."""
    r, sv = make(tmp_path)
    a = to_post(r, sv)
    w = why(r)
    assert a.type == "aim" and (a.args["vx"], a.args["vy"]) == (0.0, 0.0) and a.args["targetId"] in (1, 2, 3)
    assert w["doorway"] == 1 and w["fight"] is True and w["leg"] == "stand" and w["door"] == [112, 201]
    assert isinstance(sv.fight, D.Doorway) and sv.mode == "fight" and sv.flee is not None
    plan = sv.flee.plan
    assert plan["stand"] is True and plan["stood"] is True and plan["way"] == ((112, 201, 0), (111, 201, 0))
    assert not any(a.type == "interact" and a.args["kind"] == "close" for a in r.acts.history)
    all_sends_valid(r)


def test_a_zombie_stepping_into_the_doorway_is_swung_at_from_the_stance(tmp_path):
    """Whatever reaches FIGHT_REACH on a line not read blocked is swung at (the running stance leg gives way); one on
    the approach square, its diagonal across the wall, is not in reach."""
    r, sv = stood(tmp_path)
    r.frame(x=POST[0], y=POST[1], zombies=[z(1, 111.5, 201.5)] + group(8.0, POST)[1:])
    assert tick(r, sv) is None and "holding" in why(r)               # the approach square: the wall's diagonal
    r.frame(x=POST[0], y=POST[1], zombies=[z(1, 112.3, 201.6)] + group(8.0, POST)[1:])
    a = tick(r, sv)
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and why(r)["doorway"] == 1 and why(r)["stance"] is True


def test_the_shove_at_point_blank_then_the_swing(tmp_path):
    """A standing zombie at point blank in the doorway is shoved first (once a swing), then swung at."""
    r, sv = stood(tmp_path)
    zs = [z(1, 112.5, 201.4)] + group(8.0, POST)[1:]
    r.frame(x=POST[0], y=POST[1], zombies=zs)
    a = tick(r, sv)
    assert (a.type, a.args) == ("shove", {"targetId": 1}) and why(r)["shove"] == "doorway"
    r.answer({"state": "done", "result": {"knockdown": False, "attackStarted": True, "targetDead": False}})
    r.frame(x=POST[0], y=POST[1], zombies=zs)
    assert tick(r, sv).type == "attack"


def test_a_fallen_zombie_in_the_doorway_is_stomped(tmp_path):
    r, sv = stood(tmp_path)
    r.frame(x=POST[0], y=POST[1], zombies=[z(1, 112.5, 201.6, floor=True)] + group(8.0, POST)[1:])
    a = tick(r, sv)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and why(r)["doorway"] == 1


def test_a_kill_at_the_doorway_is_a_kill(tmp_path):
    r, sv = stood(tmp_path)
    zs = [z(1, 112.3, 201.6)] + group(8.0, POST)[1:]
    r.frame(x=POST[0], y=POST[1], zombies=zs)
    tick(r, sv)
    r.answer({"state": "done", "result": {"swings": 1, "attackStarted": True, "meleeDelay": 0.0, "targetDead": True}})
    r.frame(x=POST[0], y=POST[1], zombies=group(8.0, POST)[1:])
    tick(r, sv)
    assert r.world.kills == 1 and why(r)["kill"] == 1


def test_the_stand_ends_once_danger_r_is_empty_for_door_hold_s_and_the_door_is_closed_from_inside(tmp_path):
    """Leaving: no zombie within DANGER_R for DOOR_HOLD_S (the group standing off at 7 to 8 tiles, still held): the
    plan goes back to its close, sent from inside (flee `doorway`), then the sheltered hold as today."""
    r, sv = stood(tmp_path)
    far = group(8.0, POST)
    r.advance(D.DOOR_HOLD_S - 0.5)
    r.frame(x=POST[0], y=POST[1], zombies=far)
    tick(r, sv)
    assert why(r).get("doorway") == 1
    r.advance(0.5)
    r.frame(x=POST[0], y=POST[1], zombies=far)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 112, "y": 201, "kind": "close", "filter": "all", "maxWeight": 0.0})
    assert why(r)["flee"] == "doorway" and sv.flee.plan["left"] == "quiet" and sv.mode == "flee"
    r.answer()
    shelter_world(r, CLOSED)
    r.frame(x=POST[0], y=POST[1], zombies=far)
    assert tick(r, sv) is None and why(r)["flee"] == "held_inside"


def test_a_zombie_within_danger_r_restarts_the_hold(tmp_path):
    r, sv = stood(tmp_path)
    r.advance(D.DOOR_HOLD_S - 1.0)
    r.frame(x=POST[0], y=POST[1], zombies=[z(1, 108.0, 200.5)] + group(8.0, POST)[1:])   # 4.5 tiles: within DANGER_R
    tick(r, sv)
    r.advance(2.0)
    r.frame(x=POST[0], y=POST[1], zombies=group(8.0, POST))
    tick(r, sv)
    assert why(r).get("doorway") == 1 and not any(a.args.get("kind") == "close" for a in r.acts.history)


def test_the_stand_ends_under_the_health_flee_line(tmp_path):
    r, sv = stood(tmp_path)
    r.frame(x=POST[0], y=POST[1], zombies=[z(1, 112.3, 201.6)] + group(8.0, POST)[1:], health=S.FLEE_HEALTH - 1.0)
    tick(r, sv)
    assert r.cmd()[1]["kind"] == "close" and sv.flee.plan["left"] == "health" and why(r)["flee"] == "doorway"


@pytest.mark.parametrize("case", ["four", "pair", "no_aim", "off"])
def test_no_stand_and_the_close_as_today(tmp_path, case):
    """The refusals: four standing within DANGER_R; a flee whose reason is not `many` (two within DANGER_R under
    FLEE_HEALTH_PAIR, `pair`); a build with no stance (PZA/1.4); DOORWAY off (the rule before); the flee steps run to
    the close as today."""
    r, sv = make(tmp_path, caps=CAPS_14 if case == "no_aim" else None)
    sv.DOORWAY = case != "off"
    zs, health = group(), 100.0
    if case == "four":
        zs = zs + [zombie(4, 97.0, 203.0, me=(100.0, 201.5))]
    if case == "pair":
        zs, health = zs[:2], 50.0
    shelter_world(r, CLOSED)
    r.frame(x=100.0, y=201.5, zombies=zs, health=health)
    tick(r, sv)
    assert why(r)["flee"] == ("pair" if case == "pair" else "many") and sv.flee.plan.get("stand") is None
    me = (111.5, 201.5)
    for door, at in ((CLOSED, me), (OPEN, me), (OPEN, POST)):
        r.answer()
        if door is OPEN:
            shelter_world(r, OPEN)
        r.frame(x=at[0], y=at[1], zombies=group(8.0, at), health=health)
        tick(r, sv)
    assert r.cmd()[1]["kind"] == "close" and not isinstance(sv.fight, D.Doorway)


def test_the_drag_down_guard_does_not_leave_the_doorway(tmp_path):
    """The stand's premise is the one-tile front against #4290's three: two attackers read at the doorway keep the
    stand (the swing), where in the open the guard flees the group."""
    r, sv = stood(tmp_path)
    r.frame(x=POST[0], y=POST[1], zombies=[z(1, 112.3, 201.6)] + group(8.0, POST)[1:], attackers=2)
    a = tick(r, sv)
    assert a.type == "attack" and why(r)["doorway"] == 1 and "group" not in why(r)


def test_at_strain_hard_the_doorway_never_swings(tmp_path):
    """P24-AP on the post: at armPain 25 a zombie in reach beyond point blank is faced, never swung at; at point blank
    the shove goes every time."""
    r, sv = stood(tmp_path)
    zs = [z(1, 112.3, 201.6)] + group(8.0, POST)[1:]
    r.frame(x=POST[0], y=POST[1], zombies=zs, wounds={"armPain": 25.0})
    a = tick(r, sv)
    assert a.type == "aim" and why(r)["wounded"] == 25.0 and (a.args["vx"], a.args["vy"]) == (0.0, 0.0)
    assert a.args["targetId"] == 1
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    r.frame(x=POST[0], y=POST[1], zombies=zs, wounds={"armPain": 25.0})
    assert tick(r, sv) is None                                         # the leg facing it holds: no churn
    zs = [z(1, 112.5, 201.4)] + group(8.0, POST)[1:]
    r.frame(x=POST[0], y=POST[1], zombies=zs, wounds={"armPain": 25.0})
    assert tick(r, sv).type == "shove"
    r.answer({"state": "done", "result": {"knockdown": False, "attackStarted": True, "targetDead": False}})
    r.frame(x=POST[0], y=POST[1], zombies=zs, wounds={"armPain": 25.0})
    assert tick(r, sv).type == "shove"                                 # every time at STRAIN_HARD
    assert not any(x.type == "attack" for x in r.acts.history)


def test_off_the_post_the_stand_walks_back_inside(tmp_path):
    r, sv = stood(tmp_path)
    r.frame(x=110.5, y=201.5, zombies=group(8.0, (110.5, 201.5)))
    a = tick(r, sv)
    assert (a.type, a.args) == ("walkTo", {"x": 112.5, "y": 200.5, "gait": "walk"}) and why(r)["step"] == "return"


def test_stand_ready_counts_the_standing_within_danger_r(tmp_path):
    from .test_policies import Rig
    r = Rig(tmp_path)
    r.frame(zombies=[z(i, 103.0, 200.0 + i, me=(100.0, 200.0)) for i in range(4)])
    assert not D.stand_ready(r.world)
    r.frame(zombies=[z(i, 103.0, 200.0 + i, me=(100.0, 200.0), floor=i == 0) for i in range(4)])
    assert D.stand_ready(r.world)                                      # a fallen one is no standing attacker
    r.frame(zombies=[z(i, 103.0, 200.0 + i, me=(100.0, 200.0)) for i in range(4)])
    assert D.stand_ready(r.world, skip={1}) is True                     # one read dead is no attacker either
    r.frame(zombies=[], weapon=None)
    assert not D.stand_ready(r.world)
