"""Survival 18 (survival iteration 16; Plan 25 Task 14; E14, `e_day_14-20261030-235607`, rows #4472-#4481). The fake
mod over PZA/1.7.1, on `test_survive`'s shelter world (building 1's 3 x 3 kitchen at x 112, its west door at
(112, 201), the stand's post on the threshold square (112, 201)).

- P25-U, the stand leaves at two attackers: the stand's `drag` end fires at DRAG_DOWN_N - 1 attackers (E14 read three
  0.101 s before `EndDeath`, two 3.001 s before), logged `doorway_left` "drag" and `doorway_drag` (the count).
- P25-V, the stand ends when a standing zombie reads inside its room: off the door square and not the stand's target
  (E14's five crossed the window square beside the door while the stand faced the door), logged `doorway_left`
  "inside" and `doorway_inside` {id, square}; the room bounded by its name (`doorway.stand_room`), not the building.
- P25-W, a stand's end under a group (`wound`, `drag`, `inside`) walks out by the way out, never the close (E14's
  close shut the kitchen door with five zombies inside): the trapped hold with no way out (P25-Q's care on its tick);
  `quiet` and `off` keep their close and drop; logged `doorway_exit` {end, exit}.
"""
from agent.base.planner import doorway as D
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .test_night import OPEN, house
from .test_policies import all_sends_valid, grid, square
from .test_survive import group, tick
from .test_survive_g import part
from .test_survive_p import POST, stood
from .test_survive_p import why as door_why
from .test_survive_p import z as dz


def test_the_iteration_16_switches():
    assert S.T6_SWITCHES == ("STAND_DRAG_EARLY", "STAND_INSIDE", "STAND_EXIT")
    assert D.STAND_EXIT_ENDS == ("wound", "drag", "inside")
    assert all(getattr(T.Threat, name) is True for name in S.T6_SWITCHES)


# ================================================================ P25-U: the stand leaves at two attackers
def _attacked(tmp_path, attackers, early=True):
    """The stand on its post, one zombie in the doorway on the approach square (1.2 tiles), the rest of the group 7 to
    8 tiles off outside, the frame reading `attackers`; one tick."""
    r, sv = stood(tmp_path)
    sv.STAND_DRAG_EARLY = early
    r.frame(x=POST[0], y=POST[1], zombies=[dz(1, 111.3, 201.5)] + group(8.0, POST)[1:], attackers=attackers)
    a = tick(r, sv)
    return r, sv, a


def test_two_attackers_end_the_stand_drag_with_the_count_logged_and_the_decision_a_flee(tmp_path):
    """E14: two attackers read 3.001 s before the third: the stand ends `drag` on that tick, `doorway_drag` 2, the
    Doorway gone and the tick's decision the stand's flee (`flee` "doorway")."""
    r, sv, _ = _attacked(tmp_path, 2)
    w = door_why(r)
    assert w["doorway_left"] == "drag" and w["doorway_drag"] == 2 and w["flee"] == "doorway"
    assert sv.mode == "flee" and not isinstance(sv.fight, D.Doorway) and "doorway" not in w


def test_one_attacker_keeps_the_stand(tmp_path):
    r, sv, a = _attacked(tmp_path, 1)
    w = door_why(r)
    assert a.type == "attack" and w["doorway"] == 1 and "doorway_left" not in w and "doorway_drag" not in w


def test_three_attackers_end_it_drag_as_before(tmp_path):
    r, sv, _ = _attacked(tmp_path, S.DRAG_DOWN_N)
    w = door_why(r)
    assert w["doorway_left"] == "drag" and w["doorway_drag"] == 3 and w["flee"] == "doorway"


def test_with_stand_drag_early_off_two_attackers_keep_the_stand_and_three_end_it(tmp_path):
    """The rule before P25-U (ruling R1): DRAG_DOWN_N attackers end the stand, two keep it (the swing)."""
    r, sv, a = _attacked(tmp_path, 2, early=False)
    w = door_why(r)
    assert a.type == "attack" and w["doorway"] == 1 and "doorway_left" not in w
    (tmp_path / "three").mkdir()
    r3, sv3, _ = _attacked(tmp_path / "three", S.DRAG_DOWN_N, early=False)
    assert door_why(r3)["doorway_left"] == "drag" and door_why(r3)["doorway_drag"] == 3


def test_the_stand_s_drag_end_reads_before_the_drag_down_guard(tmp_path):
    """The two rules fire at the same count; the stand's end names the tick (`doorway_left` "drag"), never the guard's
    group steer (`group` "drag"), `_doorway` being the threat plan's first row."""
    r, sv, _ = _attacked(tmp_path, 2)
    w = door_why(r)
    assert w["doorway_left"] == "drag" and w.get("group") != "drag"


# ================================================================ P25-V: a standing zombie inside the stand's room
# building 1's second room, east of its kitchen
BEDROOM = [square(x, y, room="bedroom", building=1) for x in (115, 116) for y in (200, 201, 202)]


def _rooms(r):
    """The shelter world with the door open and building 1's bedroom east of its kitchen."""
    r.scan(grid(95, 108, 196, 207) + house(1, 112, door=OPEN) + BEDROOM)


def _inside_tick(tmp_path, zs, inside=True, rooms=False):
    r, sv = stood(tmp_path)
    sv.STAND_INSIDE = inside
    if rooms:
        _rooms(r)
    r.frame(x=POST[0], y=POST[1], zombies=zs + group(8.0, POST)[1:])
    a = tick(r, sv)
    return r, sv, a


def test_the_stand_s_room_is_the_kitchen_s_nine_squares_never_the_bedroom(tmp_path):
    r, sv = stood(tmp_path)
    _rooms(r)
    room = D.stand_room(r.world, sv.flee.plan)
    assert room == frozenset((x, y, 0) for x in (112, 113, 114) for y in (200, 201, 202))
    assert P.in_building(r.world, dz(9, 115.5, 201.5), 1)   # the read the ruling bounds: the whole building


def test_a_standing_zombie_beside_the_post_inside_ends_the_stand_inside_with_its_id_and_square(tmp_path):
    """E14: a zombie through the window square beside the door, inside the kitchen 1.4 tiles from the post: the stand
    ends `inside` (`doorway_inside` its id and square), the tick's decision the stand's flee."""
    r, sv, _ = _inside_tick(tmp_path, [dz(4, 113.5, 200.5)])
    w = door_why(r)
    assert w["doorway_left"] == "inside" and w["doorway_inside"] == {"id": 4, "square": [113, 200]}
    assert w["flee"] == "doorway" and sv.mode == "flee" and not isinstance(sv.fight, D.Doorway)


def test_the_door_square_s_zombie_alone_keeps_the_stand(tmp_path):
    r, sv, a = _inside_tick(tmp_path, [dz(1, 112.2, 201.8)])
    w = door_why(r)
    assert a is not None and a.type in ("shove", "attack") and w["doorway"] == 1 and "doorway_left" not in w


def test_a_downed_zombie_inside_keeps_the_stand_and_is_stomped(tmp_path):
    r, sv, a = _inside_tick(tmp_path, [dz(4, 113.5, 200.5, floor=True)])
    w = door_why(r)
    assert (a.type, a.args) == ("stomp", {"targetId": 4}) and w["doorway"] == 1 and "doorway_left" not in w


def test_the_stand_s_target_inside_keeps_it_and_a_second_one_inside_ends_it(tmp_path):
    """The zombie the stand fights (its target, pinned on the tick before at the approach square) stepping onto the
    kitchen square north of the threshold is the stand's to fight; a second one inside is not."""
    r, sv = stood(tmp_path)
    rest = group(8.0, POST)[1:]
    r.frame(x=POST[0], y=POST[1], zombies=[dz(1, 111.3, 201.5)] + rest)
    assert tick(r, sv).type == "attack" and sv.fight.target == 1
    r.answer({"state": "done", "result": {"swings": 1, "attackStarted": True, "meleeDelay": 0.0, "targetDead": False}})
    r.frame(x=POST[0], y=POST[1], zombies=[dz(1, 112.5, 200.5)] + rest)
    tick(r, sv)
    assert door_why(r)["doorway"] == 1 and "doorway_left" not in door_why(r)
    r.frame(x=POST[0], y=POST[1], zombies=[dz(1, 112.5, 200.5), dz(4, 114.5, 202.5)] + rest)
    tick(r, sv)
    assert door_why(r)["doorway_left"] == "inside" and door_why(r)["doorway_inside"]["id"] == 4


def test_a_standing_zombie_in_another_room_of_the_building_keeps_the_stand(tmp_path):
    r, sv, _ = _inside_tick(tmp_path, [dz(4, 115.5, 201.5)], rooms=True)
    w = door_why(r)
    assert w.get("doorway") == 1 and "doorway_left" not in w


def test_with_stand_inside_off_the_zombie_inside_keeps_the_stand(tmp_path):
    r, sv, _ = _inside_tick(tmp_path, [dz(4, 113.5, 200.5)], inside=False)
    w = door_why(r)
    assert w.get("doorway") == 1 and "doorway_left" not in w


# ================================================================ P25-W: a stand's end under a group walks out
# the stand's group (ids 1-3, which the World keeps where last seen) now east of the post, 7.5 to 8.1 tiles off the
# map's squares, and a fourth 5.5 tiles east: none inside, none refusing the way out west through the door
EAST = [dz(1, 120.0, 201.5), dz(2, 120.5, 203.0), dz(3, 120.5, 200.0), dz(5, 118.0, 201.5)]


def _wounded(tmp_path, zs, exit_on=True):
    """The stand on its post; one tick with part 4 whole (the start's snapshot), then one with it bleeding: the
    `wound` end's tick, its command returned."""
    r, sv = stood(tmp_path)
    sv.STAND_EXIT = exit_on
    r.frame(x=POST[0], y=POST[1], zombies=zs, wounds={"parts": [part(4)]})
    tick(r, sv)
    assert door_why(r).get("doorway") == 1
    r.frame(x=POST[0], y=POST[1], zombies=zs, wounds={"parts": [part(4, bleeding=True, bleedingTime=3.0)],
                                                       "bleeding": 1})
    return r, sv, tick(r, sv)


def closes(r):
    return [a for a in r.acts.history if a.type == "interact" and a.args["kind"] == "close"]


def test_a_stand_ended_wound_walks_out_by_the_door_never_the_close(tmp_path):
    """E14: the `wound` end's close shut the kitchen door with five zombies inside. With the door's way out free, the
    end's tick walks out (the walk to the square beyond the approach square, at a run), logged `doorway_exit`
    {end "wound", exit "door"}; no close is sent, the plan is dropped and the Flee kept."""
    r, sv, a = _wounded(tmp_path, EAST)
    w = door_why(r)
    assert (a.type, a.args) == ("walkTo", {"x": 110.5, "y": 201.5, "gait": "run"})
    assert w["doorway_left"] == "wound" and w["doorway_exit"] == {"end": "wound", "exit": "door"}
    assert w["flee"] == "doorway" and w["exit"] == 1 and sv.flee.plan is None and sv.flee.walking_out == "wound"
    assert not closes(r) and not isinstance(sv.fight, D.Doorway)
    all_sends_valid(r)


def test_a_stand_ended_inside_walks_out_and_the_walk_runs_ahead_of_the_inside_corner(tmp_path):
    """P25-V's end hands to P25-W's exit: the zombie inside at 1.4 tiles (within CORNERED_R) ends the stand; the exit
    walk goes, and on the next tick the running walk holds, never the inside corner's Fight on it (the way out runs
    ahead of every row, as the close ran)."""
    zs = [dz(4, 113.5, 200.5)] + EAST
    r, sv = stood(tmp_path)
    r.frame(x=POST[0], y=POST[1], zombies=zs)
    a = tick(r, sv)
    assert (a.type, a.args) == ("walkTo", {"x": 110.5, "y": 201.5, "gait": "run"})
    assert door_why(r)["doorway_exit"] == {"end": "inside", "exit": "door"}
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    r.frame(x=POST[0] - 0.3, y=POST[1], zombies=zs)
    assert tick(r, sv) is None
    w = door_why(r)
    assert "holding" in w and w["flee"] == "doorway" and "cornered" not in w and sv.mode == "flee"
    assert not closes(r) and "doorway_exit" not in w


def test_a_stand_ended_drag_at_the_door_with_the_way_out_taken_holds_trapped_never_the_close(tmp_path):
    """Two attackers, one on the door square and one on the approach square outside: the stand ends `drag`, the way
    out through the door is refused (a zombie stands on its outside square) and no other is known: the trapped hold,
    logged `doorway_exit` {end "drag", exit "trapped"}; no close."""
    r, sv = stood(tmp_path)
    r.frame(x=POST[0], y=POST[1], zombies=[dz(1, 112.2, 201.8), dz(2, 111.4, 201.5)], attackers=2)
    a = tick(r, sv)
    w = door_why(r)
    assert a is None and w["doorway_exit"] == {"end": "drag", "exit": "trapped"} and w["trapped"] == 1
    assert not closes(r) and sv.flee.plan is None


def test_with_no_way_out_the_trapped_hold_passes_the_tick_to_the_care(tmp_path):
    """P25-Q's care on the end's trapped tick: a zombie outside nearer the door's outside square than the player
    refuses the way out; the wound end's tick holds trapped and the care bandages the new bleeding part."""
    from .test_survive_g import hold
    from .test_survive import last
    r, sv = stood(tmp_path)
    hold(r, 501, "Base.Bandage")
    zs = [dz(6, 110.0, 203.5)]
    r.frame(x=POST[0], y=POST[1], zombies=zs, wounds={"parts": [part(4)]})
    tick(r, sv)
    r.frame(x=POST[0], y=POST[1], zombies=zs, wounds={"parts": [part(4, bleeding=True, bleedingTime=3.0)],
                                                       "bleeding": 1})
    a = tick(r, sv)
    d = last(tmp_path)
    t = d["inputs"]["branches"]["threat"]
    assert (a.type, a.args["itemId"], a.args["part"]) == ("bandage", 501, 4) and d["branch"] == "care"
    assert t["doorway_exit"] == {"end": "wound", "exit": "trapped"} and t["trapped"] == 1 and not closes(r)


def test_a_stand_ended_quiet_closes_the_door_as_before(tmp_path):
    """The room is clear: the `quiet` end keeps the close from inside, no `doorway_exit`."""
    r, sv = stood(tmp_path)
    far = group(8.0, POST)
    r.advance(D.DOOR_HOLD_S)
    r.frame(x=POST[0], y=POST[1], zombies=far)
    tick(r, sv)
    w = door_why(r)
    assert r.cmd()[1]["kind"] == "close" and w["doorway_left"] == "quiet" and "doorway_exit" not in w


def test_with_stand_exit_off_the_wound_end_closes_the_door(tmp_path):
    r, sv, a = _wounded(tmp_path, EAST, exit_on=False)
    w = door_why(r)
    assert (a.type, a.args["kind"]) == ("interact", "close") and w["doorway_left"] == "wound"
    assert "doorway_exit" not in w and sv.flee.plan["left"] == "wound"


def test_the_exit_kind_reads_a_door_s_edge_and_a_doorless_opening(tmp_path):
    r, sv = stood(tmp_path)
    door = {"building": 1, "inner": (112, 201, 0), "outer": (111, 201, 0), "door": None}
    assert P.exit_kind(r.world, door) == "door"
    assert P.exit_kind(r.world, dict(door, inner=(112, 200, 0), outer=(111, 200, 0))) == "opening"
    assert P.exit_kind(r.world, dict(door, door=(112, 201, 0))) == "door"
