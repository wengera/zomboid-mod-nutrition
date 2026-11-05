"""Survival 25 (survival iteration 23; Plan 29 Task 1; F13, `f_goals_14-20261105-021722`, rows #4633 and #4634). The
fake mod over PZA/1.8 on F13's gate: the fence row's north edges on y 10642 (`blockN` true, `hopN` false), its gate's
door record at (10747, 10642) open false, locked false, barricaded false (state.log lines 1929 and 2173), the open
ground south of it (lines 2173-2174) and north of it (line 1928); the character at F13's stall position
(10747.7880859375, 10641.6865234375) (state.log line 4574 on, decision lines 639 to 1624), the goal F13's model
answered from the view's `edge` (10748, 10650) (decision line 823 on).

- P29-A (`ROUTE_CROSS`), the route through a door read by whether it crossed: the route's walk (the goal's
  `GoalEdge._edge_cmd` and the Fight's `FightEdge._edge_answer`) goes to the square one step beyond the door's far
  square (10747.5, 10643.5) when the map holds it open, else the far square's centre (10747.5, 10642.5), F13's target,
  0.8629818220113737 tiles from the stall inside the Lua walk's done radius; logged `route` {door, target, beyond,
  start_side}; a leg ending `done` on its start's side is a door failure noted (`World.note_door_fail(door, "not
  crossed", "out")`), never "next", logged `route_end` {door, crossed, noted, next, dropped}; the second marks the door,
  which the route then reads as wall: the run's next way, else the goal ends `failed "blocked edge"`, cooled; the
  Fight's route at a walk, never a run.
"""
from agent.base.planner import edges as E
from agent.base.planner import survive as S
from agent.base.planner import threat as T
from agent.base.planner.goals import ExploreToward, GoalRunner, goal_key

from .test_policies import Rig, square
from .test_survive import make, threat_why, tick
from .test_survive_g import Src

STALL = (10747.7880859375, 10641.6865234375)   # F13's stall position (state.log line 4574 on)
GATE = (10747, 10642, 0)                        # the gate's square, its door record on its north edge
FAR = (10747.5, 10642.5)                        # the far square's centre: F13's route target (decision line 278)
BEYOND = (10747.5, 10643.5)                     # one step beyond it: open ground (state.log line 2174)
EDGE = (10748, 10650)                           # the view's `edge`, F13's calls 14 to 18 (decision line 823 on)
SHUT = {"barricaded": False, "locked": False, "open": False}   # the gate's door record (state.log lines 1929, 2173)
SECOND = 10750                                  # the test's own second gate on the row (no such record in F13)


def gate_map(beyond_solid=False, second=False):
    """F13's fence row x 10744..10750 (state.log line 1929): y 10641 open (line 1928), y 10642 blocked north and not
    hoppable, the gate's door record at x 10747 (lines 1929, 2173), y 10643 and 10644 open (lines 1930-1932, 2173-2174);
    the map ends at x 10744 and 10750, so the row's run has no end within it (no walk round). `beyond_solid`: the beyond
    square (10747, 10643) solid; `second`: an unlocked door record at x SECOND too."""
    out = []
    for x in range(10744, 10751):
        door = SHUT if x == GATE[0] or (second and x == SECOND) else None
        out += [square(x, 10641, light=1),
                square(x, 10642, light=1, blockN=True, edgeN=True, door=door),
                square(x, 10643, light=1, solid=beyond_solid and x == GATE[0]),
                square(x, 10644, light=1)]
    return out


def route_why(target, beyond, door=(10747, 10642)):
    return {"door": list(door), "target": list(target), "beyond": beyond, "start_side": "N"}


# ================================================================ P29-A: the goal's route
def goal_rig(tmp_path, cross=True, **k):
    """F13's goal: the runner's ExploreToward at the view's `edge` from the stall position, the place scanned."""
    r = Rig(tmp_path)
    r.scan(gate_map(**k))
    r.frame(x=STALL[0], y=STALL[1], game_min=648.0)
    runner = GoalRunner(Src(ExploreToward(*EDGE)), r.clock)
    runner.kit.route_cross = cross
    runner.kit.bind(r.world, r.acts)
    runner.kit.explore.scanned.add(runner.kit.explore.place())
    return r, runner


def step(r, runner):
    """One runner tick, its command sent; the command's (type, args), else None."""
    cmd = runner.tick(r.world, r.acts)
    if cmd is None:
        return None
    runner.send(cmd)
    return r.cmd()


def leg_done(r, runner, at, game_min=648.5):
    """The running walk answered done with the character at `at`; the next tick's command (sent), else None."""
    r.answer()
    r.frame(x=at[0], y=at[1], game_min=game_min)
    return step(r, runner)


def test_the_iteration_23_route_switch():
    """`ROUTE_CROSS` on `threat.Threat` beside BLOCKED_EDGE (the Fight's `route_cross` rule and the goals' kit read
    it), on by default, the first name of `survive.T13_SWITCHES`; the kit's copy on by default too."""
    assert S.T13_SWITCHES[0] == "ROUTE_CROSS" and "T13_SWITCHES" in S.__all__
    assert T.Threat.ROUTE_CROSS is True and S.Survive.ROUTE_CROSS is True
    assert GoalRunner(Src(None)).kit.route_cross is True


def test_the_goal_route_at_the_gate_walks_one_step_beyond_its_far_square(tmp_path):
    """P29-A (a): from F13's stall, the goal's route walks at a walk to the beyond square's centre (10747.5, 10643.5),
    1.8 tiles off, never the far square's centre inside the done radius; logged `route` {beyond True}."""
    r, runner = goal_rig(tmp_path)
    assert step(r, runner) == ("walkTo", {"x": BEYOND[0], "y": BEYOND[1], "gait": "walk"})
    w = runner.current.why
    assert w["route"] == route_why(BEYOND, True)
    assert w["blocked_edge"]["door"] == [10747, 10642] and w["blocked_edge"]["action"] == "route"
    assert w["leg"] == list(BEYOND)


def test_the_beyond_square_solid_falls_back_to_the_far_square(tmp_path):
    """P29-A (b): with the beyond square solid in the map, the route's walk goes to the far square's centre, logged
    `route` {beyond False}."""
    r, runner = goal_rig(tmp_path, beyond_solid=True)
    assert step(r, runner) == ("walkTo", {"x": FAR[0], "y": FAR[1], "gait": "walk"})
    assert runner.current.why["route"] == route_why(FAR, False)


def test_a_route_leg_done_on_its_start_side_is_a_door_failure_never_next(tmp_path):
    """P29-A (c): the leg ended `done` with the character still at the stall position (its start's side): `route_end`
    {crossed False, noted True}, the gate's failure counted (`World.door_fails`), and the route sent once more at the
    same door (one failure marks nothing: DOOR_FAILS_TO_MARK)."""
    r, runner = goal_rig(tmp_path)
    step(r, runner)
    assert leg_done(r, runner, STALL) == ("walkTo", {"x": BEYOND[0], "y": BEYOND[1], "gait": "walk"})
    assert runner.why["route_end"] == {"door": [10747, 10642], "crossed": False, "noted": True,
                                       "next": [10747, 10642], "dropped": False}
    assert [f[1] for f in r.world.door_fails[GATE]] == ["not crossed"] and GATE not in r.world.marked_doors()
    assert runner.current.running


def test_the_second_uncrossed_leg_marks_the_gate_and_routes_through_the_run_s_next_way(tmp_path):
    """P29-A (c), a run with a second way: the second uncrossed leg marks the gate (`World.marked_doors`), the route
    reads it as wall and walks to the next unlocked door record on the row, one step beyond its far square."""
    r, runner = goal_rig(tmp_path, second=True)
    step(r, runner)
    leg_done(r, runner, STALL)
    nxt = leg_done(r, runner, STALL, game_min=649.0)
    assert runner.why["route_end"] == {"door": [10747, 10642], "crossed": False, "noted": True,
                                       "next": [SECOND, 10642], "dropped": False}
    assert GATE in r.world.marked_doors()
    assert nxt == ("walkTo", {"x": SECOND + 0.5, "y": 10643.5, "gait": "walk"})
    assert runner.current.why["route"] == route_why((SECOND + 0.5, 10643.5), True, door=(SECOND, 10642))


def test_the_second_uncrossed_leg_with_no_other_way_drops_the_goal_blocked_edge_cooled(tmp_path):
    """P29-A (c), a run without: the second uncrossed leg marks the gate and, no other way on the row, the goal ends
    `failed "blocked edge"`, cooled (`route_end` {dropped True}); nothing more is sent at the gate."""
    r, runner = goal_rig(tmp_path)
    step(r, runner)
    leg_done(r, runner, STALL)
    sent = len(r.acts.history)
    assert leg_done(r, runner, STALL, game_min=649.0) is None and len(r.acts.history) == sent
    assert runner.why["route_end"] == {"door": [10747, 10642], "crossed": False, "noted": True, "next": None,
                                       "dropped": True}
    row = runner.history[-1]
    assert (row["type"], row["state"], row["reason"]) == ("ExploreToward", "failed", "blocked edge")
    assert goal_key("ExploreToward", {"x": EDGE[0], "y": EDGE[1]}) in runner.cooled


def test_a_route_leg_done_across_the_gate_crossed_and_the_goal_walks_on(tmp_path):
    """P29-A (d): the leg ended `done` with the character at the beyond square: `route_end` {crossed True, noted
    False}, nothing counted on the gate, and the next leg the goal's own walk to its target."""
    r, runner = goal_rig(tmp_path)
    step(r, runner)
    assert leg_done(r, runner, BEYOND) == ("walkTo", {"x": EDGE[0], "y": EDGE[1], "gait": "walk"})
    assert runner.why["route_end"] == {"door": [10747, 10642], "crossed": True, "noted": False, "next": None,
                                       "dropped": False}
    assert GATE not in r.world.door_fails


def test_with_route_cross_off_the_goal_walks_to_the_far_square_and_reads_done_as_next(tmp_path):
    """P29-A (f), the pin of the rule before it: with the kit's `route_cross` off the route walks to the far square's
    centre and a `done` on the start's side is "next", the same walk sent again (F13's loop), nothing noted."""
    r, runner = goal_rig(tmp_path, cross=False)
    assert step(r, runner) == ("walkTo", {"x": FAR[0], "y": FAR[1], "gait": "walk"})
    assert "route" not in runner.current.why
    assert leg_done(r, runner, STALL) == ("walkTo", {"x": FAR[0], "y": FAR[1], "gait": "walk"})
    assert "route_end" not in runner.why and GATE not in r.world.door_fails


def test_survive_copies_route_cross_to_the_goals_kit(tmp_path):
    r, sv = make(tmp_path)
    sv.ROUTE_CROSS = False
    r.frame(x=STALL[0], y=STALL[1])
    tick(r, sv)
    assert sv.goals.kit.route_cross is False


# ================================================================ P29-A: the Fight's route
CHASER = (10747.5, 10645.5)   # a chaser across the gate, 3.8 tiles from the stall (the test's own)


def chaser():
    from .test_policies import zombie
    return dict(zombie(1, CHASER[0], CHASER[1], me=STALL), hasTarget=True)


def fight_rig(tmp_path, cross=True, **k):
    r, sv = make(tmp_path)
    sv.ROUTE_CROSS = cross
    r.scan(gate_map(**k))
    r.frame(x=STALL[0], y=STALL[1], zombies=[chaser()], game_min=648.0)
    return r, sv


def test_the_fight_s_route_at_the_gate_walks_beyond_it_at_a_walk_never_a_run(tmp_path):
    """P29-A (e): the Fight's route through the gate to a chaser across it walks to the beyond square at a walk, never
    the run of P25-X's route (memory `no-sprinting`; the visual pass's fifth, F13's shots 111 and 112)."""
    r, sv = fight_rig(tmp_path)
    a = tick(r, sv)
    assert (a.type, a.args) == ("walkTo", {"x": BEYOND[0], "y": BEYOND[1], "gait": "walk"})
    w = threat_why(tmp_path)
    assert w["route"] == route_why(BEYOND, True) and w["blocked_edge"]["action"] == "route"


def test_the_fight_s_route_done_on_its_start_side_notes_the_gate(tmp_path):
    """P29-A (e): the Fight's route walk ended `done` with the character still at the stall: `route_end` {crossed
    False, noted True} on the next line's threat why, the gate's failure counted; the second marks it, and the chaser,
    no other way on the row, is refused across the edge (marked, `blocked_edge` refuse)."""
    r, sv = fight_rig(tmp_path)
    tick(r, sv)
    r.answer()
    r.frame(x=STALL[0], y=STALL[1], zombies=[chaser()], game_min=648.5)
    tick(r, sv)
    assert threat_why(tmp_path)["route_end"] == {"door": [10747, 10642], "crossed": False, "noted": True,
                                                 "next": [10747, 10642], "dropped": False}
    assert [f[1] for f in r.world.door_fails[GATE]] == ["not crossed"]
    r.answer()
    r.frame(x=STALL[0], y=STALL[1], zombies=[chaser()], game_min=649.0)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["route_end"]["dropped"] is True and GATE in r.world.marked_doors()
    assert w["blocked_edge"] == {"edge": [10747, 10642, "N"], "door": None, "action": "refuse"}
    assert sv.edge_marks.get(1) == ((10747, 10642, 0), "N")


def test_the_fight_s_route_done_across_the_gate_crossed(tmp_path):
    r, sv = fight_rig(tmp_path)
    tick(r, sv)
    r.answer()
    r.frame(x=BEYOND[0], y=BEYOND[1], zombies=[chaser()], game_min=648.5)
    tick(r, sv)
    assert threat_why(tmp_path)["route_end"] == {"door": [10747, 10642], "crossed": True, "noted": False,
                                                 "next": None, "dropped": False}
    assert GATE not in r.world.door_fails


def test_with_route_cross_off_the_fight_s_route_runs_to_the_far_square_as_before(tmp_path):
    """P29-A (f) for the Fight, the pin: with `ROUTE_CROSS` off, P25-X's route at a run to the far square's centre, its
    `done` read as before (no note)."""
    r, sv = fight_rig(tmp_path, cross=False)
    a = tick(r, sv)
    assert (a.type, a.args) == ("walkTo", {"x": FAR[0], "y": FAR[1], "gait": "run"})
    assert "route" not in threat_why(tmp_path) and "route_cross" not in sv._fight_rules()
    r.answer()
    r.frame(x=STALL[0], y=STALL[1], zombies=[chaser()], game_min=648.5)
    tick(r, sv)
    assert "route_end" not in threat_why(tmp_path) and GATE not in r.world.door_fails


def test_the_beyond_square_is_the_far_square_plus_the_edge_s_normal(tmp_path):
    """`edges.beyond_square`: the far square plus the edge's unit normal, away from the near square, through the
    shared `policies._beyond` read (open: mapped, not solid nor `solidTrans`, no room, the step not blocked): the
    square north of the row's north side is not mapped, so a route north reads None."""
    r = Rig(tmp_path)
    r.scan(gate_map())
    edge = ((10747, 10642, 0), "N")
    assert E.beyond_square(r.world, (10747, 10642, 0), edge) == (10747, 10643, 0)
    assert E.beyond_square(r.world, (10747, 10641, 0), edge) is None
    assert E.side_of(edge, STALL) == "N" and E.side_of(edge, BEYOND) == "S"
