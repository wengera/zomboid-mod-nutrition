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
- P25-X (the amendment; E15: 158 game minutes cycling at zombie 8064 behind a locked chain-link gate): a known blocked
  outdoor edge (not hoppable, its door records locked) on the straight line to a Fight's target refuses the seek and
  marks the target until it is read on the player's side; an unlocked door record on the edge's run routes the walk
  through it; a goal's or a fill's target beyond it is routed through that door, else dropped (`failed "blocked
  edge"`, cooled); logged `blocked_edge` {edge, door, action}.

Task 14 fix 1 (the review's minors, `review-t14.md`, and two rulings): a marked zombie read across its edge is out of the
hold (`EDGE_OUT_OF_HOLD`); the refusal's why never overwrites a routed second zombie's `blocked_edge`; a stand's
`walking_out` clears with its exit; the stand's end table reads `drag` before `health`; P25-Y, a dirty rag alone under
DIRTY_RAG_MIN no longer blocks the rip or the unwear (`DIRTY_RAG_RIP`; F6, `f_goals_7-20261031-000629`).
"""
from agent.base.planner import doorway as D
from agent.base.planner import policies as P
from agent.base.planner import survive as S

from .test_night import OPEN, house
from .test_policies import all_sends_valid, grid, square
from .test_survive import group, last, make, tick
from .test_survive_g import care_frame, care_why, hold, part
from .test_survive_p import POST, stood
from .test_survive_p import why as door_why
from .test_survive_p import z as dz
from .test_survive_n import TSHIRT, unwear_rig


def test_the_iteration_16_switches():
    assert S.T6_SWITCHES == ("STAND_DRAG_EARLY", "STAND_INSIDE", "STAND_EXIT", "BLOCKED_EDGE", "EDGE_OUT_OF_HOLD",
                             "DIRTY_RAG_RIP")
    assert D.STAND_EXIT_ENDS == ("wound", "crowd", "drag", "inside")   # named change, ruling P26-K (Plan 26 Task 7):
    # the stand's `crowd` end walks out too (a `crowd` with nobody inside and the door square clear closes, P26-K2)
    assert all(getattr(S.Survive, name) is True for name in S.T6_SWITCHES)


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
    """One tick of the stand at its post with `zs` (`STAND_INSIDE` as given). Named change, ruling P27-G (Plan 27
    Task 5): `FLOOR_FINISH` off (P24-AL's stomp of a downed zombie inside is pinned with the rule before it)."""
    r, sv = stood(tmp_path)
    sv.STAND_INSIDE = inside
    sv.FLOOR_FINISH = False
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


def test_with_no_way_out_the_trapped_hold_passes_the_tick_to_the_care(tmp_path, monkeypatch):
    """P25-Q's care on the end's trapped tick: a zombie outside nearer the door's outside square than the player
    refuses the way out; the wound end's tick holds trapped and the care bandages the new bleeding part.
    Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
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


# ================================================================ P25-X: a known blocked edge
LOCKED = {"open": False, "locked": True, "barricaded": False}
UNLOCKED = {"open": False, "locked": False, "barricaded": False}
ME = (100.5, 200.5)


def walled(doors=None, hop=False):
    """`test_survive_g.fenced`'s yard (x 98..112, y 196..204) with its fence on the west edges of x 102 a wall (not
    hoppable: E15's chain-link) unless `hop`; `doors` {y: door record} on the wall's squares at x 102 (E15's gate
    (10756, 10642) locked, (10747, 10642) unlocked)."""
    doors = doors or {}
    return [square(x, y, blockW=(x == 102), hopW=(x == 102 and hop), edgeW=(x == 102),
                   door=doors.get(y) if x == 102 else None) for x in range(98, 113) for y in range(196, 205)]


def chaser(x, y=200.5):
    return dict(dz(1, x, y, me=ME), hasTarget=True)


def gate_rig(tmp_path, doors=None, hop=False, zx=104.5, edge=True, cross=True):
    """`cross` False: ruling P29-A's switch (`ROUTE_CROSS`, Plan 29 Task 1) off, P25-X's route to the far square.
    Named change, ruling P30-C (Plan 30 Task 3): a chaser behind a gate within DOOR_HELD_R is decided now
    (`door_held`); P25-X's cases pinned with `DOOR_HELD` off."""
    r, sv = make(tmp_path)
    sv.BLOCKED_EDGE = edge
    sv.DOOR_HELD = False
    sv.ROUTE_CROSS = cross
    r.scan(walled(doors, hop))
    r.frame(x=ME[0], y=ME[1], zombies=[chaser(zx)])
    return r, sv


def walks(r):
    return [a for a in r.acts.history if a.type == "walkTo"]


def test_a_chaser_across_a_locked_gate_is_refused_and_marked_until_it_comes_round(tmp_path):
    """E15's gate zombie: a chaser 4 tiles off across the wall, the gate on its edge locked: no seek, no walk toward it
    on any tick, the target marked (`edge_marks`, an unreachable wall that never lapses), logged `blocked_edge`
    {edge [102, 200, "W"], door None, action refuse}; read on the player's side of the wall it is free again."""
    r, sv = gate_rig(tmp_path, {200: LOCKED})
    tick(r, sv)
    w = door_why(r)
    assert w["blocked_edge"] == {"edge": [102, 200, "W"], "door": None, "action": "refuse"} and w["marked"] == 1
    assert sv.edge_marks == {1: ((102, 200, 0), "W")} and sv.unreachable[1] == float("inf")
    for _ in range(4):
        r.advance(P.UNREACHABLE_S)
        r.frame(x=ME[0], y=ME[1], zombies=[chaser(103.5)])
        tick(r, sv)
        last_a = r.acts.history[-1] if r.acts.history else None
        if last_a is not None and last_a.state not in ("done", "failed", "timeout", "rejected"):
            r.answer()
    assert not [a for a in walks(r) if a.args["x"] > ME[0]] and 1 in sv.edge_marks   # the goal's walks go elsewhere
    r.frame(x=ME[0], y=ME[1], zombies=[chaser(101.6)])
    tick(r, sv)
    assert 1 not in sv.edge_marks and 1 not in sv.unreachable


def test_an_unlocked_gate_on_the_crossed_edge_routes_the_seek_through_it(tmp_path):
    """Named change, ruling P29-A (Plan 29 Task 1): pinned with `ROUTE_CROSS` off, P25-X's route before it."""
    r, sv = gate_rig(tmp_path, {200: UNLOCKED}, cross=False)
    a = tick(r, sv)
    w = door_why(r)
    assert (a.type, a.args) == ("walkTo", {"x": 102.5, "y": 200.5, "gait": "run"})
    assert w["blocked_edge"] == {"edge": [102, 200, "W"], "door": [102, 200], "action": "route"} and not sv.edge_marks


def test_a_locked_gate_with_an_unlocked_one_on_the_wall_s_run_routes_through_the_unlocked_one(tmp_path):
    """E15's fence row: the gate on the line locked, an unlocked door record 3 squares along the wall: the seek walks
    to the far side of the unlocked door, never across the locked one; a route walk that fails marks the target.
    Named change, ruling P29-A (Plan 29 Task 1): pinned with `ROUTE_CROSS` off, P25-X's route before it."""
    r, sv = gate_rig(tmp_path, {200: LOCKED, 203: UNLOCKED}, cross=False)
    a = tick(r, sv)
    w = door_why(r)
    assert (a.type, a.args) == ("walkTo", {"x": 102.5, "y": 203.5, "gait": "run"})
    assert w["blocked_edge"] == {"edge": [102, 200, "W"], "door": [102, 203], "action": "route"}
    r.answer({"state": "failed", "reason": "stuck"})
    r.frame(x=ME[0], y=ME[1], zombies=[chaser(104.5)])
    tick(r, sv)
    assert sv.edge_marks.get(1) == ((102, 200, 0), "W")


def test_a_hoppable_fence_keeps_the_fence_wait(tmp_path):
    r, sv = gate_rig(tmp_path, hop=True)
    a = tick(r, sv)
    w = door_why(r)
    assert a.type == "aim" and w["fence_wait"]["target"] == 1 and "blocked_edge" not in w and not sv.edge_marks


def test_with_blocked_edge_off_the_seek_is_iteration_15_s(tmp_path):
    r, sv = gate_rig(tmp_path, {200: LOCKED}, edge=False)
    a = tick(r, sv)
    w = door_why(r)
    assert (a.type, a.args["x"]) == ("walkTo", 104.5) and "blocked_edge" not in w and not sv.edge_marks   # across


def _goal(tmp_path, doors, cross=True):
    from agent.base.planner.goals import ExploreToward, GoalRunner
    from .test_policies import Rig
    from .test_survive_g import Src
    r = Rig(tmp_path)
    r.scan(walled(doors))
    r.frame(x=ME[0], y=ME[1])
    runner = GoalRunner(Src(ExploreToward(x=108, y=200)), r.clock)
    runner.kit.route_cross = cross   # P29-A's switch (Survive's ROUTE_CROSS)
    runner.kit.bind(r.world, r.acts)
    runner.kit.explore.scanned.add(runner.kit.explore.place())
    return r, runner


def test_a_goal_beyond_the_wall_walks_a_leg_to_the_unlocked_door_then_its_target(tmp_path):
    """Named change, ruling P29-A (Plan 29 Task 1): pinned with `ROUTE_CROSS` off, P25-X's route before it."""
    r, runner = _goal(tmp_path, {200: LOCKED, 203: UNLOCKED}, cross=False)
    runner.send(runner.tick(r.world, r.acts))
    assert r.cmd() == ("walkTo", {"x": 102.5, "y": 203.5, "gait": "walk"})
    assert runner.current.why["blocked_edge"] == {"edge": [102, 200, "W"], "door": [102, 203], "action": "route"}
    r.answer()
    r.frame(x=102.5, y=203.5)
    runner.kit.explore.scanned.add(runner.kit.explore.place())
    runner.send(runner.tick(r.world, r.acts))
    assert r.cmd() == ("walkTo", {"x": 108, "y": 200, "gait": "walk"}) and runner.current.running


def test_a_goal_beyond_the_wall_with_no_unlocked_door_fails_blocked_edge_and_is_cooled(tmp_path):
    from agent.base.planner.goals import goal_key
    r, runner = _goal(tmp_path, {200: LOCKED})
    assert runner.tick(r.world, r.acts) is None
    row = runner.history[-1]
    assert (row["type"], row["state"], row["reason"]) == ("ExploreToward", "failed", "blocked edge")
    assert goal_key("ExploreToward", {"x": 108, "y": 200}) in runner.cooled and not walks(r)


def test_a_water_source_beyond_the_wall_is_reached_through_its_door_or_passed_over(tmp_path):
    """The need's fill (E15's 17 fills at building 2's laundry, beyond the gate): a source across the wall is walked
    to through the unlocked door first; with the door locked it is passed over for a source on the player's side.
    Named change, ruling P29-A for the fill (Plan 29 Task 1 fix 1, review-t1 M2): pinned with the Water's
    `route_cross` off, P25-X's fill route before it, turned off at its source (Survive's ROUTE_CROSS, copied to the
    Water each need tick since Plan 29 Task 2)."""
    from .test_survive_g import hold, need_why, source
    r, sv = make(tmp_path)
    sv.ROUTE_CROSS = False
    r.scan(walled({200: LOCKED, 203: UNLOCKED}) + [source(108, 199)])
    hold(r, 5, "Base.PopEmpty", use="container")
    r.frame(x=ME[0], y=ME[1], thirst=0.2)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 102.5, "y": 203.5, "gait": "walk"})
    assert need_why(tmp_path)["fill"]["blocked_edge"]["action"] == "route"
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.scan(walled({200: LOCKED}) + [source(108, 199), source(99, 196)])
    hold(r2, 5, "Base.PopEmpty", use="container")
    r2.frame(x=ME[0], y=ME[1], thirst=0.2)
    tick(r2, sv2)
    assert r2.cmd() == ("fill", {"itemId": 5, "x": 99, "y": 196})


def test_e7_s_walk_round_the_fence_row_routes_through_its_unlocked_door():
    """E7's record (the review's blocker of Plan 24 Task 18): the seek on 533, 8.07 tiles off across the fixture's
    fence row (its north edges on y 10642), whose nearest way is the unlocked door record at (10747, 10642): at line
    49 the walk goes to that door's far square at a run, logged `blocked_edge` {route}, where iteration 15 walked
    round the wall at 533's square (`test_survive_h.test_e7_lines_52_to_73_...`, `edge` False); held from line 50.
    Named change, ruling P29-A (Plan 29 Task 1): pinned with `ROUTE_CROSS` off, P25-X's route before it."""
    from .test_survive_h import _e7_lines
    rows, _ = _e7_lines(50, engage_any=True, cross=False)
    w = rows[48]["inputs"]["branches"]["threat"]
    assert rows[48]["action"] == {"type": "walkTo", "args": {"gait": "run", "x": 10747.5, "y": 10642.5}}
    assert w["blocked_edge"] == {"action": "route", "door": [10747, 10642], "edge": [10739, 10642, "N"]}
    assert w["target"] == 533 and "holding" in rows[49]["inputs"]["branches"]["threat"]
    rows, _ = _e7_lines(49, engage_any=True, edge=False)
    assert rows[48]["action"] == {"type": "walkTo", "args": {"gait": "walk", "x": 10740.5, "y": 10647.5}}


# ================================================================ Task 14 fix 1: the review's minors
def _out_ticks(tmp_path, on):
    """The gate rig (the gate on the chaser's edge locked), the refusal tick, then three ticks with the chaser 3 tiles
    off across the wall, the decision line and the mode of each; then one with it read on the player's side."""
    r, sv = gate_rig(tmp_path, {200: LOCKED})
    sv.EDGE_OUT_OF_HOLD = on
    tick(r, sv)
    lines = []
    for _ in range(3):
        r.advance(1.0)
        r.frame(x=ME[0], y=ME[1], zombies=[chaser(103.5)])
        tick(r, sv)
        lines.append((last(tmp_path), sv.mode))
    r.frame(x=ME[0], y=ME[1], zombies=[chaser(101.6)])
    tick(r, sv)
    return r, sv, lines, (last(tmp_path), sv.mode)


def test_a_zombie_marked_for_a_blocked_edge_and_read_across_it_is_out_of_the_hold_and_counts_again_on_this_side(tmp_path):
    """Minor 1, the controller's ruling (P25-X amended; `EDGE_OUT_OF_HOLD`): E15's gate zombie within DANGER_R across
    the fence neither flees `unreachable` nor holds the threat branch: the goal runs (branch `goal`, no mode, the
    threat why empty) on every tick it stays across; the tick it reads on the player's side it counts again (the
    Fight on it)."""
    r, sv, lines, back = _out_ticks(tmp_path, True)
    assert sv.edge_marks == {} and 1 not in sv.unreachable
    for line, mode in lines:
        assert line["branch"] == "goal" and mode is None and line["inputs"]["branches"]["threat"] == {}
    line, mode = back
    assert line["branch"] == "threat" and mode == "fight" and line["inputs"]["branches"]["threat"]["target"] == 1


def test_with_edge_out_of_hold_off_the_marked_zombie_across_the_edge_flees_unreachable_as_before(tmp_path):
    r, sv, lines, back = _out_ticks(tmp_path, False)
    for line, mode in lines:
        w = line["inputs"]["branches"]["threat"]
        assert line["branch"] == "threat" and mode == "flee" and w["flee"] == "unreachable"
    assert back[1] == "fight"


def test_the_marked_zombie_across_the_edge_is_left_out_of_the_listing_and_the_dangerr_count_only_while_across(tmp_path):
    """`_within` (the held set, the DANGER_R count the pair rule and the hysteresis read) leaves out the marked ids
    read across their edge, `raw` keeps them (the decision line's own readings); a second zombie on the player's side
    counts."""
    r, sv = gate_rig(tmp_path, {200: LOCKED})
    tick(r, sv)
    r.frame(x=ME[0], y=ME[1], zombies=[chaser(103.5), dict(dz(2, 99.0, 200.5, me=ME), hasTarget=True)])
    tick(r, sv)
    assert len(sv._within(P.DANGER_R)) == 1 and sv._edge_out() == {1}
    assert len(sv._within(P.DANGER_R, raw=True)) == 2
    sv.EDGE_OUT_OF_HOLD = False
    assert len(sv._within(P.DANGER_R)) == 2 and sv._edge_out() == frozenset()


def _two_walls(tmp_path):
    """A wall on the west edges of x 102 over y 190..215 whose one unlocked door record is at y 210: a chaser at
    (103.5, 196.5) crosses at y 199 (11 squares from the door, beyond DISENGAGE_R: refused), a second at (104.5, 205.5)
    crosses nearer it (routed)."""
    r, sv = make(tmp_path)
    r.scan([square(x, y, blockW=(x == 102), edgeW=(x == 102), door=UNLOCKED if (x, y) == (102, 210) else None)
            for x in range(98, 113) for y in range(190, 216)])
    r.frame(x=ME[0], y=ME[1], zombies=[chaser(103.5, 196.5), dict(chaser(104.5, 205.5), id=2)])
    return r, sv


def test_the_refusal_s_why_never_overwrites_the_routed_second_zombie_s_blocked_edge(tmp_path):
    """Minor 2: the nearer zombie is refused (marked, the choose re-run), the second routed through the unlocked door:
    the tick's action is the route walk and the logged `blocked_edge` is the route's own (door [102, 210]),
    `marked` the refused id; not the first zombie's refusal over a route walk. Named change, ruling P29-A (Plan 29
    Task 1): pinned with `ROUTE_CROSS` off, P25-X's route before it."""
    r, sv = _two_walls(tmp_path)
    sv.ROUTE_CROSS = False
    a = tick(r, sv)
    w = door_why(r)
    assert (a.type, a.args) == ("walkTo", {"x": 102.5, "y": 210.5, "gait": "run"})
    assert w["marked"] == 1 and 1 in sv.edge_marks and 2 not in sv.edge_marks
    assert w["blocked_edge"]["action"] == "route" and w["blocked_edge"]["door"] == [102, 210]
    assert w["target"] == 2


def test_a_lone_refusal_still_logs_its_own_blocked_edge(tmp_path):
    r, sv = gate_rig(tmp_path, {200: LOCKED})
    tick(r, sv)
    w = door_why(r)
    assert w["blocked_edge"]["action"] == "refuse" and w["marked"] == 1


def test_a_stand_s_way_out_that_ended_is_no_longer_the_stand_s_for_a_later_exit_of_the_same_flee(tmp_path):
    """Minor 3 (`Flee.walking_out`): the `inside` end walks out (the walk to the square beyond the approach square);
    once the player stands outside the exit ends and `walking_out` clears; a later exit the same Flee takes (the exit
    record of the first, standing in for the next room's) is not `stand_exit_running`, so the threat plan reads its rows
    (here the `many` flee's hold, the group episode kept), never the stale row (`("flee", "doorway")` ahead of the
    corner and the drag guard)."""
    zs = [dz(4, 113.5, 200.5)] + EAST
    r, sv = stood(tmp_path)
    r.frame(x=POST[0], y=POST[1], zombies=zs)
    tick(r, sv)
    first = sv.flee.exit
    assert sv.flee.walking_out == "inside" and sv.flee.stand_exit_running() and first is not None
    r.fake.answer({"walkTo": ["accepted", "done"]})
    r.pump()
    r.frame(x=110.5, y=201.5, zombies=EAST)
    tick(r, sv)
    assert sv.flee.exit is None and sv.flee.walking_out is None
    sv.flee.exit = dict(first, step="walk")   # a later way out of the same Flee
    assert not sv.flee.stand_exit_running()
    r.frame(x=POST[0], y=POST[1], zombies=[dz(6, 113.5, 201.5)])
    tick(r, sv)
    w = door_why(r)
    assert w["flee"] != "doorway" and "doorway_exit" not in w and "doorway_left" not in w


def test_a_trapped_stand_end_leaves_no_way_out_running(tmp_path):
    """Minor 3: the stand's `drag` end with no way out (the trapped hold) leaves no `walking_out`, so a way out the Flee
    takes later is no stand's."""
    r, sv = stood(tmp_path)
    r.frame(x=POST[0], y=POST[1], zombies=[dz(1, 112.2, 201.8), dz(2, 111.4, 201.5)], attackers=2)
    tick(r, sv)
    assert door_why(r)["doorway_exit"] == {"end": "drag", "exit": "trapped"}
    assert sv.flee.walking_out is None and not sv.flee.stand_exit_running()


def test_a_stand_ended_drag_under_flee_health_leaves_by_the_way_out_never_the_close(tmp_path):
    """Minor 4, the controller's ruling (`STAND_DRAG_EARLY`): the end table reads `drag` before `health`, so two
    attackers with the health under FLEE_HEALTH end `drag` and walk out (logged `doorway_exit`), never the `health`
    close with the group at the front; off, `health` first and the close."""
    def run(sub, early):
        (tmp_path / sub).mkdir()
        r, sv = stood(tmp_path / sub)
        sv.STAND_DRAG_EARLY = early
        r.frame(x=POST[0], y=POST[1], zombies=[dz(1, 111.3, 201.5)] + group(8.0, POST)[1:], attackers=2,
                health=S.FLEE_HEALTH - 1.0)
        tick(r, sv)
        return r, sv
    r, sv = run("on", True)
    w = door_why(r)
    assert w["doorway_left"] == "drag" and w["doorway_drag"] == 2 and "doorway_exit" in w and not closes(r)
    r, sv = run("off", False)
    w = door_why(r)
    assert w["doorway_left"] == "health" and "doorway_exit" not in w and "doorway_drag" not in w


# ================================================================ P25-Y: a dirty rag alone does not block the rip
def _dirty_rig(tmp_path, held, bleeding_time=3.0, garments=None, switch=True, unworn=True, stock_early=True):
    """`test_survive_n.unwear_rig`'s PZA/1.7 world (no worn garment unless `garments`), `held` [(id, fullType)] of
    bandage items, an unworn cotton T-shirt 30 held (`unworn`); part 9 bleeding at `bleeding_time`; no zombie, one
    care tick. `stock_early` is Survive's `STOCK_EARLY` (ruling P27-K1, Plan 27 Task 5)."""
    r, sv = unwear_rig(tmp_path, garments=garments or [])
    sv.DIRTY_RAG_RIP = switch
    sv.STOCK_EARLY = stock_early
    for iid, ft in held:
        hold(r, iid, ft)
    if unworn:
        r.event("item_added", itemId=30, fullType="Base.Tshirt_Blue", weight=0.2, use="clothing", rip="cotton",
                clothing={"loc": TSHIRT, "bite": 1.0, "scratch": 1.0})
    care_frame(r, [part(9, bleeding=True, bleedingTime=bleeding_time)])
    tick(r, sv)
    return r, sv


def test_the_iteration_16_care_switch():
    assert S.T6_SWITCHES[-1] == "DIRTY_RAG_RIP" and vars(S.Survive)["DIRTY_RAG_RIP"] is True


def test_a_dirty_rag_alone_under_dirty_rag_min_no_longer_blocks_the_rip_of_an_unworn_garment(tmp_path, monkeypatch):
    """P25-Y (F6: part 3 bled from game minute 701 to 743 with a dirty rag the only dressing and a cotton T-shirt held
    unworn): bleedingTime 3.0, under DIRTY_RAG_MIN: the garment is ripped, logged `no_rag` with the dirty rag's id
    (`dirty`); the next care tick the clean rag dresses the part.
    Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
    r, sv = _dirty_rig(tmp_path, [(12, "Base.RippedSheetsDirty")])
    assert r.cmd() == ("rip", {"itemId": 30})
    assert care_why(tmp_path) == {"reason": "no_rag", "part": 9, "item": 30, "dirty": 12}


def test_with_a_clean_rag_held_the_part_is_bandaged_with_it_never_the_rip(tmp_path, monkeypatch):
    """Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
    r, sv = _dirty_rig(tmp_path, [(12, "Base.RippedSheetsDirty"), (11, "Base.RippedSheets")])
    assert r.cmd() == ("bandage", {"itemId": 11, "part": 9})
    assert care_why(tmp_path)["kind"] == "rag"


def test_past_dirty_rag_min_the_dirty_rag_dresses_the_part_as_before(tmp_path, monkeypatch):
    """Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
    r, sv = _dirty_rig(tmp_path, [(12, "Base.RippedSheetsDirty")], bleeding_time=12.0)
    assert r.cmd() == ("bandage", {"itemId": 12, "part": 9}) and care_why(tmp_path)["kind"] == "dirty"


def test_a_dirty_rag_alone_with_no_garment_unworn_takes_the_unwear_of_a_worn_cotton_one(tmp_path, monkeypatch):
    """P25-H's unwear behind the same block: no unworn garment, a worn cotton T-shirt, a quiet tick: the unwear, logged
    with the dirty rag's id.
    Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
    r, sv = _dirty_rig(tmp_path, [(12, "Base.RippedSheetsDirty")], unworn=False,
                       garments=[(20, "Base.Tshirt_White", TSHIRT, 1.0, 2.0)])
    assert r.cmd() == ("unwear", {"itemId": 20})
    assert care_why(tmp_path) == {"reason": "unwear", "item": 20, "loc": TSHIRT, "cover": 3.0, "part": 9, "dirty": 12}


def test_with_dirty_rag_rip_off_a_dirty_rag_held_blocks_the_rip_and_the_unwear_as_in_iteration_15(tmp_path,
                                                                                                  monkeypatch):
    """Named change, ruling P27-K1 (Plan 27 Task 5): pinned with `STOCK_EARLY` off (on, the stock's early rip counts
    the clean dressings alone, so the unworn T-shirt is ripped whatever the dirty rag: `test_survive_ab`).
    Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
    r, sv = _dirty_rig(tmp_path, [(12, "Base.RippedSheetsDirty")], switch=False, stock_early=False)
    assert last(tmp_path)["branch"] != "care" and not [a for a in r.acts.history if a.type in ("rip", "unwear")]
    (tmp_path / "w").mkdir()
    r, sv = _dirty_rig(tmp_path / "w", [(12, "Base.RippedSheetsDirty")], switch=False, unworn=False,
                       garments=[(20, "Base.Tshirt_White", TSHIRT, 1.0, 2.0)], stock_early=False)
    assert last(tmp_path / "w")["branch"] != "care" and not [a for a in r.acts.history if a.type in ("rip", "unwear")]
