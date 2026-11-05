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
- P29-B (`GOAL_STALL`), a budget end that never moved marks its target: F13's calls 14 to 18 (each goal begun at the
  stall position, 90 s of wall time, the character unmoved): a `goal budget` end with the character moved under
  STALL_R since the goal began cools the goal and marks its target (`mark_far`), logged `stall` {moved, target}, the
  next view carrying `stall` (the target) and `cooled` naming the goal.
"""
from agent.base.planner import edges as E
from agent.base.planner import survive as S
from agent.base.planner import threat as T
from agent.base.planner.goals import ExploreToward, GoalRunner, goal_key

from .test_policies import Rig, square
from .test_survive import last, make, threat_why, tick
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


# ================================================================ P29-B: a budget end that never moved
def stall_rig(tmp_path, on=True):
    """F13's calls 14 to 18: a Survive whose goal (the source's one ExploreToward at the view's `edge`) begins at the
    stall position, under F13's own route rules (`ROUTE_CROSS` off: the walk to the far square, each `done` read as
    "next"), `GOAL_STALL` set to `on`."""
    r = Rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(ExploreToward(*EDGE)))
    sv.ROUTE_CROSS = False
    sv.GOAL_STALL = on
    r.scan(gate_map())
    r.frame(x=STALL[0], y=STALL[1], game_min=648.0)
    sv.goals.kit.bind(r.world, r.acts)
    sv.goals.kit.explore.scanned.add(sv.goals.kit.explore.place())
    return r, sv


def stand(r, sv, at, dt=5.0):
    """F13's stall: every route walk answered `done` at once, the clock stepped `dt` wall seconds a tick, the character
    read at `at`, until the goal's budget ends; the last tick's decision line's goal why."""
    a = tick(r, sv)
    assert a is not None and (a.type, a.args["x"], a.args["y"]) == ("walkTo", FAR[0], FAR[1])
    gm = 648.0
    while not sv.goals.history:
        if a is not None and a.state not in ("done", "failed", "timeout", "rejected"):
            r.answer()
        r.advance(dt)
        gm += 0.1
        r.frame(x=at[0], y=at[1], game_min=gm)
        a = tick(r, sv)
    return (last(r.dir)["inputs"]["branches"].get("goal") or {})


def test_the_iteration_23_switches_and_stall_r():
    """`survive.T13_SWITCHES`: ROUTE_CROSS (P29-A, on `threat.Threat`) and GOAL_STALL (P29-B, on `Survive`, copied to
    the goal runner each tick), each on by default; STALL_R the Lua walk's done radius."""
    from agent.base.planner import policies as P
    assert S.T13_SWITCHES[:2] == ("ROUTE_CROSS", "GOAL_STALL")
    assert all(getattr(S.Survive, n) is True for n in S.T13_SWITCHES)
    assert P.STALL_R == 1.0 == P.WALK_DONE_R and GoalRunner(Src(None)).goal_stall is True


def test_a_budget_end_that_never_moved_marks_its_target_and_the_view_names_it(tmp_path):
    """P29-B: F13's goal begun at the stall position, its route walks `done` unmoved for 90 s of wall time, the
    character within 0.3 tiles of where it began: the end is `failed "goal budget"` with `stall` {moved, target} on the
    line, the goal cooled and its target marked (`mark_far`: `World.stuck`), the next view carrying `stall` (the
    target, rendered after `last_goal`) and `cooled` naming the goal."""
    from agent.base.planner import view as V
    r, sv = stall_rig(tmp_path)
    at = (STALL[0], STALL[1] - 0.3)
    w = stand(r, sv, at)
    row = sv.goals.history[-1]
    assert (row["type"], row["state"], row["reason"]) == ("ExploreToward", "failed", "goal budget")
    moved = w["stall"]["moved"]
    assert abs(moved - 0.3) < 1e-9 and w["stall"] == {"moved": moved, "target": list(EDGE)}
    assert goal_key("ExploreToward", {"x": EDGE[0], "y": EDGE[1]}) in sv.goals.cooled
    assert EDGE in r.world.stuck
    v = sv._view()
    assert v["stall"] == list(EDGE)
    assert {"type": "ExploreToward", "args": {"x": EDGE[0], "y": EDGE[1]}} in v["cooled"]
    lines = V.render(v).splitlines()
    k = [ln.split(":", 1)[0] for ln in lines]
    assert k[k.index("last_goal") + 1] == "stall" and "stall: [10748,10650]" in lines


def test_a_budget_end_that_moved_2_5_tiles_marks_nothing_as_today(tmp_path):
    """P29-B's other side: the character 2.5 tiles from where the goal began at its budget end: `failed "goal
    budget"` with no `stall`, no mark, not cooled (it sent), no `stall` in the view."""
    r, sv = stall_rig(tmp_path)
    w = stand(r, sv, (STALL[0], STALL[1] - 2.5))
    assert sv.goals.history[-1]["reason"] == "goal budget" and "stall" not in w
    assert sv.goals.cooled == {} and EDGE not in r.world.stuck and "stall" not in sv._view()


def test_with_goal_stall_off_a_budget_end_unmoved_marks_nothing(tmp_path):
    r, sv = stall_rig(tmp_path, on=False)
    w = stand(r, sv, (STALL[0], STALL[1] - 0.3))
    assert sv.goals.history[-1]["reason"] == "goal budget" and "stall" not in w
    assert sv.goals.cooled == {} and EDGE not in r.world.stuck and "stall" not in sv._view()
    assert sv.goals.goal_stall is False


def test_a_rest_s_budget_end_is_never_a_stall(tmp_path):
    """P29-B reads a goal with a target of its own (`stall_target`: an ExploreToward's square); a Rest stands by
    design, so its budget end (here a Rest past its budget unread by its own check) is no stall: nothing marked, no
    `stall` (it is cooled as before, having sent nothing)."""
    from agent.base.planner.goals import Rest
    r = Rig(tmp_path)
    r.frame(x=STALL[0], y=STALL[1])
    runner = GoalRunner(Src(Rest(5.0)), r.clock)
    runner.tick(r.world, r.acts)
    r.advance(200.0)
    runner.observe(r.world, r.acts)
    assert runner.history[-1]["reason"] == "goal budget"
    assert runner.stall_now is None and runner.stalled() is None and not r.world.stuck


def test_the_prompt_names_the_stall_square_as_one_not_to_answer():
    from agent.base.planner import goal_prompt as GP
    assert ("`stall` names the target square of the last goal that ran out of time with you not moving: never "
            "answer that square while it reads") in GP.system(60.0)


# ================================================================ Task 2: the hit rules (E22's and F13's fixtures)
E22 = "e_day_22-20261105-004919"
E22_BAT = {"type": "Base.BaseballBat", "cond": 15, "reach": 1.125, "ammo": 0}   # E22's weapon (state.log seq 7019)


def zr(zid, x, y, me, chasing=True, floor=None):
    """A zombie record at (x, y) as the frames list it: `hasTarget` `chasing`, `onFloor` `floor` (None: not read)."""
    from .test_policies import zombie
    return dict(zombie(zid, x, y, me=me), hasTarget=chasing, onFloor=floor)


def e22_frame(r, me, zs, health, game_min, **k):
    """One of E22's frames: the character at `me`, the zombies `zs` ((id, x, y) or (id, x, y, chasing, floor)), E22's
    bat and the frame's health."""
    recs = [zr(*z[:3], me=me, chasing=z[3] if len(z) > 3 else True, floor=z[4] if len(z) > 4 else None) for z in zs]
    r.frame(x=me[0], y=me[1], zombies=recs, weapon=E22_BAT, health=health, game_min=game_min, **k)


def test_the_iteration_23_hit_rule_switches():
    """Task 2's switches follow Task 1's in `survive.T13_SWITCHES`, each on `threat.Threat` and on by default."""
    assert S.T13_SWITCHES[2:] == ("HEALTH_NEAR", "DRESS_FINISH", "MANY_NEAR")
    assert all(getattr(T.Threat, n) is True for n in S.T13_SWITCHES[2:])


# ---------------------------------------------------------------- P29-E: the `health` flee only from within DANGER_R
# E22's line 743 (state.log seq 6981, game minute 662): the `many` flee's group read two within DANGER_R, health
# 30.72905731201172; line 749 (seq 7019): the `health` flee's steer sent at a run with 11515 chasing 8.197687115943333
# tiles off and nobody within DANGER_R (11522 10.798 and 11516 11.006 tiles off, beyond the hold), health
# 30.81458282470703 (GUIDE section 9: 138 of the `health` flee's 181 lines read no zombie within 6 tiles)
E22_743 = ((10749.9755859375, 10693.3134765625), [(11515, 10751.265625, 10693.32421875),
                                                   (11516, 10753.5576171875, 10688.5478515625),
                                                   (11522, 10754.52734375, 10685.47265625)], 30.72905731201172)
E22_749 = ((10742.3740234375, 10686.2451171875), [(11515, 10748.634765625, 10691.537109375),
                                                   (11522, 10753.0341796875, 10687.9658203125),
                                                   (11516, 10753.0732421875, 10688.826171875)], 30.81458282470703)


def health_flee(tmp_path, on=True, walls=False, parts=None, rag=False):
    """E22's `health` flee: line 743's frame from a fresh Survive (two within DANGER_R under FLEE_HEALTH: the `health`
    flee's steer at a run, the fresh read of the record's running `many` episode), that steer answered done, then line
    749's frame ticked; `walls`: a wall between the character and 11515 (the test's own: x 10745's west edges, y 10684
    to 10693, mapped with the squares round it); `parts`: the body's part records; `rag`: a clean rag held. The last
    tick's action."""
    from .test_survive_g import hold
    r, sv = make(tmp_path)
    sv.HEALTH_NEAR = on
    if rag:
        hold(r, 10, "Base.RippedSheets")
    if walls:
        r.scan([square(x, y, blockW=x == 10745, edgeW=x == 10745) for x in range(10740, 10751)
                for y in range(10684, 10694)])
    me, zs, h = E22_743
    e22_frame(r, me, zs, h, 662.0)
    a = tick(r, sv)
    assert a.type == "steer" and a.args["gait"] == "run" and threat_why(tmp_path)["flee"] == "health"
    r.answer()
    r.advance(0.5)
    me, zs, h = E22_749
    wounds = None if parts is None else {"parts": parts, "bleeding": sum(1 for p in parts if p.get("bleeding"))}
    e22_frame(r, me, zs, h, 662.1, wounds=wounds)
    return r, sv, tick(r, sv)


def test_e22_s_health_flee_from_a_chaser_at_8_2_tiles_holds_the_low_fight_s_stance_at_it(tmp_path):
    """P29-E (`HEALTH_NEAR`): E22's line 749, health 30.81458282470703, nobody within DANGER_R and 11515 chasing in view
    8.197687115943333 tiles off: no `health` flee; the low fight's stance, an `aim` at 11515 (its legs walk, never run),
    logged `health_near` {near 0} beside `low_fight`."""
    r, sv, a = health_flee(tmp_path)
    w = threat_why(tmp_path)
    assert (a.type, a.args["targetId"]) == ("aim", 11515) and "gait" not in a.args
    assert w["fight"] is True and "flee" not in w and w["health_near"] == {"near": 0} and w["low_fight"] is True


def test_with_health_near_off_line_749_flees_health_at_a_run_as_e22_did(tmp_path):
    r, sv, a = health_flee(tmp_path, on=False)
    w = threat_why(tmp_path)
    assert (a.type, a.args["gait"]) == ("steer", "run") and w["flee"] == "health" and "health_near" not in w


def test_with_none_in_view_the_threat_branch_passes_to_the_care_s_dressing(tmp_path):
    """P29-E: line 749 with a wall between the character and 11515 (its line read blocked) and a part bleeding with a
    rag held (the test's own): no flee and no stance; the threat episode ends (`mode` None), logged `health_near`
    {near 0}, and the care branch's dressing takes the tick."""
    from .test_survive_g import part
    r, sv, a = health_flee(tmp_path, walls=True, parts=[part(5, bleeding=True, bleedingTime=5.0)], rag=True)
    row = last(tmp_path)
    assert row["branch"] == "care" and (a.type, a.args["part"]) == ("bandage", 5)
    assert row["inputs"]["branches"]["threat"] == {"health_near": {"near": 0}, "held": 1} and sv.mode is None


def test_with_a_zombie_within_danger_r_the_health_flee_runs_as_today(tmp_path):
    """P29-E's other side: line 743's frame (11515 1.29 and 11516 5.96 tiles off, both within DANGER_R): the `health`
    flee's steer at a run, no `health_near`, the switch on."""
    r, sv = make(tmp_path)
    me, zs, h = E22_743
    e22_frame(r, me, zs, h, 662.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args["gait"]) == ("steer", "run") and w["flee"] == "health" and "health_near" not in w


# ---------------------------------------------------------------- P29-D: the dressing ridden through the flees
# E22's lines 537 to 542 (state.log seqs 5154 to 5189, game minutes 634 to 635): the care's rag a126 (971539017) rode
# the `health` flee's leg a125 on part 0, its leg done at seq 5187 with 11512 9.601549438765653 tiles off, and line 542
# sent the next steer a127 at a run, which superseded a126 at seq 5190, nobody within 6 tiles (GUIDE section 7: four of
# the twelve superseded dressings on such lines)
E22_537 = ((10730.5166015625, 10672.0751953125), [(11512, 10729.40234375, 10679.59765625),
                                                   (11516, 10724.5947265625, 10679.4052734375),
                                                   (11602, 10721.833984375, 10678.642578125)], 29.19933319091797)
E22_542 = ((10734.3759765625, 10669.9150390625), [(11512, 10729.5, 10678.185546875),
                                                   (11516, 10725.5, 10676.9765625)], 29.069862365722656)
E22_PART0 = {"i": 0, "h": 35.08428192138672, "bleeding": True, "bleedingTime": 2.6065080165863037, "bandaged": False,
             "bandageLife": None, "bandageDirty": None, "deep": False, "infected": False}   # part 0 (seq 5149, 5189)
E22_RAG = 971539017   # the clean rag a126 tied (decision line 537)


def ridden_flee(tmp_path, final, dress=True, health_near=False):
    """E22's ride: the `health` flee's steer from 11512 and 11516 within DANGER_R (the test's own start: E22's episode
    began `many`), running; line 537's frame, the care's rag riding it on part 0 (accepted); the leg answered done;
    then `final` (me, zombies, health) ticked with DRESS_FINISH `dress` and HEALTH_NEAR `health_near` (off by default:
    line 542's `health` flee, which P29-E withholds, so the case reads P29-D alone). (r, sv, the ride, the action)."""
    from .test_survive_g import hold
    r, sv = make(tmp_path)
    sv.DRESS_FINISH, sv.HEALTH_NEAR = dress, health_near
    hold(r, E22_RAG, "Base.RippedSheets")
    wounds = {"parts": [E22_PART0], "bleeding": 1}
    me, zs, h = E22_537
    near = [(11512, me[0] - 1.0, me[1] + 4.0), (11516, me[0] - 3.0, me[1] + 4.0)]
    e22_frame(r, me, near, h, 634.0, wounds=wounds)
    leg = tick(r, sv)
    assert leg.type == "steer" and threat_why(tmp_path)["flee"] == "health"
    r.answer("progress")
    r.advance(0.5)
    e22_frame(r, me, zs, h, 634.1, wounds=wounds)
    ride = tick(r, sv)
    assert (ride.type, ride.args) == ("bandage", {"itemId": E22_RAG, "part": 0, "keepMoving": True})
    r.fake.act(ride.aid, "accepted", "bandage")
    r.fake.act(leg.aid, "done", "steer", result={})
    r.pump()
    r.advance(2.5)
    me, zs, h = final
    e22_frame(r, me, zs, h, 635.0, wounds=wounds)
    return r, sv, ride, tick(r, sv)


def test_e22_s_line_542_dressing_is_waited_on_never_superseded_by_the_flee_s_steer(tmp_path):
    """P29-D (`DRESS_FINISH`): line 542, the leg done, the rag still riding, nobody within DANGER_R (11512 9.6 tiles
    off): the `health` flee sends no steer, logged `dress_finish` {action, near 0}; the dressing runs on."""
    r, sv, ride, a = ridden_flee(tmp_path, E22_542)
    w = threat_why(tmp_path)
    assert a is None and w["flee"] == "health" and w["dress_finish"] == {"action": ride.aid, "near": 0}
    assert r.acts.current is ride and sv.care.riding() is ride


def test_with_dress_finish_off_line_542_s_steer_supersedes_the_dressing_as_e22_did(tmp_path):
    r, sv, ride, a = ridden_flee(tmp_path, E22_542, dress=False)
    assert (a.type, a.args["gait"]) == ("steer", "run") and "dress_finish" not in threat_why(tmp_path)
    assert r.acts.current is a


def test_a_zombie_within_danger_r_supersedes_the_dressing_as_before(tmp_path):
    """P29-D's other side: line 542 with 11512 and 11516 within DANGER_R (5.0 and 5.5 tiles, the test's own): the
    `health` flee's steer supersedes the dressing, no `dress_finish`."""
    me, _, h = E22_542
    final = (me, [(11512, me[0] - 3.0, me[1] + 4.0), (11516, me[0] - 3.3, me[1] + 4.4)], h)
    r, sv, ride, a = ridden_flee(tmp_path, final)
    assert (a.type, a.args["gait"]) == ("steer", "run") and "dress_finish" not in threat_why(tmp_path)


def test_with_every_rule_on_line_542_s_dressing_rides_on_under_the_stance(tmp_path):
    """With HEALTH_NEAR on too (the default), line 542 reads no `health` flee (P29-E): the low fight's stance at 11512,
    whose legs a riding bandage holds off (P24-U), so nothing supersedes the dressing either."""
    r, sv, ride, a = ridden_flee(tmp_path, E22_542, health_near=True)
    w = threat_why(tmp_path)
    assert a is None and w["fight"] is True and w["ride"] == ride.aid and r.acts.current is ride


def test_survive_copies_route_cross_to_the_water_chain_and_pre_t13_turns_it_off(tmp_path):
    """Task 1 fix 1's addendum: Survive copies ROUTE_CROSS to the water chain beside BLOCKED_EDGE (the need's fill read,
    `water.Water.route_cross`), so `pre_t13` (every iteration-23 switch off) turns the fill's route read off too."""
    from .test_replay_decisions import pre_t13
    r, sv = make(tmp_path)
    r.frame(thirst=0.5)
    tick(r, sv)
    assert sv.water.route_cross is True
    (tmp_path / "off").mkdir()
    r2, sv2 = make(tmp_path / "off")
    pre_t13(sv2)
    r2.frame(thirst=0.5)
    tick(r2, sv2)
    assert sv2.water.route_cross is False


# ---------------------------------------------------------------- P29-G: the `many` count over the standing
# E22's line 1340 (state.log seq 11776, game minute 741): the `health` flee from 11855 and 11856, both read fallen 3.57
# and 3.6 tiles off (11810 chasing 6.17, 11527 and 11526 idle beyond DANGER_R); line 1341 (seq 11783): 11810 came to
# 5.93 tiles and the `many` flee read three within DANGER_R, one of them standing (GUIDE section 9: at most one standing
# within 6 tiles on 145 of the `many` flee's 198 lines)
E22_1340 = ((10789.0009765625, 10625.439453125), [(11855, 10789.2705078125, 10629, False, True),
                                                   (11856, 10789.5009765625, 10629, False, True),
                                                   (11810, 10784.1396484375, 10621.6416015625),
                                                   (11527, 10794.5029296875, 10633.3896484375, False),
                                                   (11526, 10796.2607421875, 10633.287109375, False)],
            26.294525146484375)
E22_1341 = ((10789.990234375, 10624.7216796875), [(11856, 10789.5009765625, 10629, False, True),
                                                   (11855, 10789.2705078125, 10629, False, True),
                                                   (11810, 10784.7451171875, 10621.9580078125),
                                                   (11527, 10794.5029296875, 10633.3896484375, False),
                                                   (11526, 10796.2607421875, 10633.287109375, False)],
            26.3076171875)


def standing(zs, ids):
    """The records `zs` with the zombies `ids` read standing (`onFloor` None), the test's own."""
    return [(z[0], z[1], z[2], z[3] if len(z) > 3 else True) if z[0] in ids else z for z in zs]


def many_rig(tmp_path, second, on=True, first=E22_1340):
    """`first` (line 1340's frame by default) then `second` from a fresh Survive with MANY_NEAR `on`, each leg answered
    done before the next tick; the second tick's threat why."""
    r, sv = make(tmp_path)
    sv.MANY_NEAR = on
    for k, (me, zs, h) in enumerate((first, second)):
        e22_frame(r, me, zs, h, 741.0 + 0.1 * k)
        if tick(r, sv) is not None:
            r.answer()
        r.advance(0.5)
    return r, sv, threat_why(tmp_path)


def test_e22_s_line_1341_three_within_danger_r_one_standing_makes_no_many(tmp_path):
    """P29-G (`MANY_NEAR`): line 1341, 11810 standing 5.93 tiles off and 11856 and 11855 fallen within DANGER_R: no
    `many`, logged `many_near` {n 1}; the `health` flee runs on (the DANGER_R count three, no low fight)."""
    r, sv, w = many_rig(tmp_path, E22_1341)
    assert w.get("flee") != "many" and w["many_near"] == {"n": 1} and sv.flee_many is False
    assert w["flee"] == "health"


def test_with_many_near_off_line_1341_flees_many_as_e22_did(tmp_path):
    r, sv, w = many_rig(tmp_path, E22_1341, on=False)
    assert w["flee"] == "many" and "many_near" not in w


def test_three_standing_within_danger_r_make_many_as_today(tmp_path):
    """P29-G's other side: line 1341 with 11856 and 11855 read standing (the test's own): three standing within
    DANGER_R, `many`, no `many_near`."""
    me, zs, h = E22_1341
    r, sv, w = many_rig(tmp_path, (me, standing(zs, (11855, 11856)), h))
    assert w["flee"] == "many" and "many_near" not in w and sv.flee_many is True


def test_a_many_episode_holds_at_two_standing_and_ends_at_one(tmp_path):
    """P29-G's hysteresis: the episode begun at three standing (line 1341's three read standing) holds while two stand
    within DANGER_R (11855 read fallen again) and reads no `many` at one standing (both fallen: line 1341 itself),
    logged `many_near` {n 1}."""
    me, zs, h = E22_1341
    r, sv, w = many_rig(tmp_path, (me, standing(zs, (11856,)), h), first=(me, standing(zs, (11855, 11856)), h))
    assert w["flee"] == "many" and "many_near" not in w
    e22_frame(r, me, zs, h, 741.2)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w.get("flee") != "many" and w["many_near"] == {"n": 1}
