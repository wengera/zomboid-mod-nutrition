"""Survival 25, fix 1 (Plan 29 Task 1 fix 1; the review `review-t1.md`, M1, M2 and the minors m1, m2). On F13's gate
(`test_survive_ae.gate_map`: the fence row on y 10642, the gate's door record at (10747, 10642), the stall position
(10747.7880859375, 10641.6865234375)).

- M1, P29-B over every goal with a walk target (`Goal.stall_target`): a LootBuilding's last walk's square (None when
  its last send was no `walkTo`: a loot working through one room's containers is no stall), a Shelter's plan door
  square; a Rest and a Stock none.
- M2, the need's fill route read by crossing (`water.Water`, `route_cross`): the fill's walk through the gate goes to
  the step beyond its far square, its end read by `edges.read_route_end` (an uncrossed `done` notes the gate, the
  second marks it and the source is passed over), never F13's loop.
- m1, a route leg ended `failed` on its start's side notes the door too (the goal's leg logic and the Fight's target
  mark decide the rest, as before; the runner's P27-F stuck mark beside it, a separate store).
- m2, a stale route record is cleared at the next route read (`GoalEdge._edge_cmd`), so a later leg's end is never
  read against it.
"""
from agent.base.actions import Action
from agent.base.planner import survive as S
from agent.base.planner.goals import ExploreToward, GoalRunner, LootBuilding, Rest, Shelter, Stock, goal_key

from .test_policies import CRATE, Rig, square
from .test_survive import inside, last, tick
from .test_survive_ae import BEYOND, EDGE, FAR, GATE, STALL, gate_map, goal_rig, leg_done, step
from .test_survive_g import Src, hold, need_why, source

LOOT_SQ = (10747, 10647)   # the test's own building 1 room square with a crate, south of the gate (not in F13)
SOURCE = (10747, 10646)    # the test's own water source south of the gate (not in F13; E15's fills aimed past this row)


def act(aid, typ, **args):
    return Action(aid=aid, type=typ, args=args, deadline_s=30.0, sent_wall=0.0)


# ================================================================ M1: P29-B over every goal with a walk target
def test_a_loot_s_stall_target_is_its_last_walk_s_square_else_none():
    """`LootBuilding.stall_target`: the square of the walk it last sent; None with nothing sent or a last send that
    was no `walkTo` (a loot `interact`: the Lua walks to the container itself)."""
    g = LootBuilding(1)
    assert g.stall_target() is None
    g.last = act("a1", "walkTo", x=FAR[0], y=FAR[1], gait="walk")
    assert g.stall_target() == [10747, 10642]   # the integer square under the walk's centre FAR (review-t1 fix 1 r1)
    g.last = act("a2", "interact", x=LOOT_SQ[0], y=LOOT_SQ[1], kind="loot", filter="bandage", maxWeight=8.0)
    assert g.stall_target() is None


def test_a_shelter_s_stall_target_is_its_plan_s_door_and_a_rest_s_or_a_stock_s_none():
    s = Shelter(1)
    s.plan = None
    assert s.stall_target() is None
    s.plan = {"doors": [(10740, 10630, 0), (10741, 10630, 0)], "door_i": 1, "step": "approach"}
    assert s.stall_target() == [10741, 10630]
    assert Rest(5.0).stall_target() is None and Stock("water").stall_target() is None
    assert ExploreToward(*EDGE).stall_target() == list(EDGE)


def loot_stall(tmp_path, at):
    """A Survive whose one goal is building 1's loot beyond F13's gate, under F13's own route rules (`ROUTE_CROSS` off:
    each route walk to the far square answered `done` at once and re-sent), the character read at `at`, 5 s a tick,
    until the goal's budget ends; the last line's goal why."""
    r = Rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(LootBuilding(1)))
    sv.ROUTE_CROSS = False
    r.scan(gate_map() + [inside(LOOT_SQ[0], LOOT_SQ[1], containers=[CRATE])])
    r.frame(x=STALL[0], y=STALL[1], game_min=648.0)
    a = tick(r, sv)
    assert a is not None and (a.type, a.args["x"], a.args["y"]) == ("walkTo", FAR[0], FAR[1])
    gm = 648.0
    while not sv.goals.history:
        if a is not None and a.state not in ("done", "failed", "timeout", "rejected"):
            r.answer()
        r.advance(5.0)
        gm += 0.1
        r.frame(x=at[0], y=at[1], game_min=gm)
        a = tick(r, sv)
    return r, sv, (last(tmp_path)["inputs"]["branches"].get("goal") or {})


def test_a_loot_whose_route_walks_end_done_unmoved_for_its_budget_is_a_stall(tmp_path):
    """M1: a LootBuilding through F13's gate, its route walks `done` unmoved for 90 s: `failed "goal budget"`, `stall`
    {moved, target: its last walk's square}, the goal cooled, the view's `stall` that square (`mark_far` a no-op)."""
    r, sv, w = loot_stall(tmp_path, (STALL[0], STALL[1] - 0.3))
    row = sv.goals.history[-1]
    assert (row["type"], row["state"], row["reason"]) == ("LootBuilding", "failed", "goal budget")
    assert w["stall"]["target"] == [10747, 10642] and abs(w["stall"]["moved"] - 0.3) < 1e-9   # the integer square (r1)
    assert goal_key("LootBuilding", {"building": 1}) in sv.goals.cooled
    assert sv._view()["stall"] == [10747, 10642] and not r.world.stuck   # the integer square (r1)


def test_a_loot_whose_last_send_was_a_loot_interact_is_no_stall(tmp_path):
    """M1's guard: a LootBuilding at its budget end whose last send was a loot `interact` (working through one room's
    containers) is no stall, however little the character moved: nothing cooled by it, no `stall`."""
    r = Rig(tmp_path)
    r.frame(x=STALL[0], y=STALL[1])
    runner = GoalRunner(Src(None), r.clock)
    g = LootBuilding(1)
    g.start_xy, g.sent_n = STALL, 3
    g.last = act("a3", "interact", x=LOOT_SQ[0], y=LOOT_SQ[1], kind="loot", filter="food", maxWeight=8.0)
    runner._stall(r.world, g)
    assert runner.stall_now is None and runner.stall is None and not getattr(g, "cool", False)
    g.last = act("a4", "walkTo", x=FAR[0], y=FAR[1], gait="walk")
    runner._stall(r.world, g)
    assert runner.stall_now == {"moved": 0.0, "target": [10747, 10642]} and g.cool is True   # the integer square (r1)


# ================================================================ M2: the need's fill route read by crossing
def fill_rig(tmp_path, cross=True):
    """A thirsty character at F13's stall holding an empty vessel, the one clean source known beyond the gate."""
    from .test_survive import make
    r, sv = make(tmp_path)
    sv.water.route_cross = cross
    r.scan(gate_map() + [source(*SOURCE)])
    hold(r, 5, "Base.PopEmpty", use="container")
    r.frame(x=STALL[0], y=STALL[1], thirst=0.2, game_min=648.0)
    return r, sv


def fill_done(r, sv, at, game_min):
    r.answer()
    r.frame(x=at[0], y=at[1], thirst=0.2, game_min=game_min)
    return tick(r, sv)


def test_the_fill_s_route_through_the_gate_walks_one_step_beyond_its_far_square(tmp_path):
    r, sv = fill_rig(tmp_path)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": BEYOND[0], "y": BEYOND[1], "gait": "walk"})
    f = need_why(tmp_path)["fill"]
    assert f["route"] == {"door": [10747, 10642], "target": list(BEYOND), "beyond": True, "start_side": "N"}
    assert f["blocked_edge"]["action"] == "route" and f["walk"] == list(BEYOND)


def test_an_uncrossed_fill_walk_notes_the_gate_and_the_second_passes_the_source_over(tmp_path):
    """M2: the fill's route walk ended `done` at the stall (its start's side) notes the gate (`route_end` {crossed
    False, noted True} in the next plan's `fill` why) and the walk goes again; the second marks the gate and, no other
    way on the row, the source is passed over (`want` water_source): no third fill walk (the goal layer's scan takes
    the tick), never F13's loop."""
    r, sv = fill_rig(tmp_path)
    tick(r, sv)
    a = fill_done(r, sv, STALL, 648.5)
    f = need_why(tmp_path)["fill"]
    assert f["route_end"] == {"door": [10747, 10642], "crossed": False, "noted": True, "next": [10747, 10642],
                              "dropped": False}
    assert [x[1] for x in r.world.door_fails[GATE]] == ["not crossed"]
    assert a is not None and (a.type, a.args["y"]) == ("walkTo", BEYOND[1])
    sent = len(r.acts.history)
    fill_done(r, sv, STALL, 649.0)
    f = need_why(tmp_path)["fill"]
    assert f["route_end"]["dropped"] is True and GATE in r.world.marked_doors()
    assert f["want"] == "water_source" and f["blocked_edge"]["action"] == "drop"
    assert last(tmp_path)["branch"] != "need" and not [a for a in r.acts.history[sent:] if a.type == "walkTo"]


def test_a_crossed_fill_walk_goes_on_to_the_fill(tmp_path):
    r, sv = fill_rig(tmp_path)
    tick(r, sv)
    fill_done(r, sv, BEYOND, 648.5)
    f = need_why(tmp_path)["fill"]
    assert f["route_end"] == {"door": [10747, 10642], "crossed": True, "noted": False, "next": None,
                              "dropped": False}
    assert r.cmd() == ("fill", {"itemId": 5, "x": SOURCE[0], "y": SOURCE[1]}) and GATE not in r.world.door_fails


def test_with_route_cross_off_the_fill_walks_to_the_far_square_and_reads_done_as_before(tmp_path):
    """The pin of P25-X's fill route: the walk to the far square's centre, its `done` at the stall noting nothing, the
    same walk sent again (F13's loop shape). Named change, Plan 29 Task 2 (Survive copies ROUTE_CROSS to the Water
    each need tick): the switch turned off at its source, Survive's ROUTE_CROSS."""
    r, sv = fill_rig(tmp_path, cross=False)
    sv.ROUTE_CROSS = False
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": FAR[0], "y": FAR[1], "gait": "walk"})
    fill_done(r, sv, STALL, 648.5)
    assert r.cmd() == ("walkTo", {"x": FAR[0], "y": FAR[1], "gait": "walk"})
    assert "route_end" not in need_why(tmp_path)["fill"] and GATE not in r.world.door_fails


# ================================================================ m1: a failed end on the start's side
def test_a_route_leg_failed_stuck_at_the_stall_is_counted_on_the_gate(tmp_path):
    """m1: the goal's route leg ended `failed "stuck"` with the character at the stall (its start's side): the gate's
    failure counted (`World.door_fails`), `route_end` {crossed False, noted True} on the line; the leg's own logic
    decides the goal as before (no hop: `failed "stuck"`, cooled), and the runner's P27-F stuck mark reads the same
    walk in its own store."""
    r, runner = goal_rig(tmp_path)
    step(r, runner)
    r.answer({"state": "failed", "reason": "stuck"})
    r.frame(x=STALL[0], y=STALL[1], game_min=648.5)
    runner.tick(r.world, r.acts)
    assert [x[1] for x in r.world.door_fails[GATE]] == ["not crossed"]
    assert runner.why["route_end"]["crossed"] is False and runner.why["route_end"]["noted"] is True
    row = runner.history[-1]
    assert (row["state"], row["reason"]) == ("failed", "stuck")
    assert goal_key("ExploreToward", {"x": EDGE[0], "y": EDGE[1]}) in runner.cooled
    assert runner.stuck_now is not None   # P27-F's mark, its own store


def test_the_fight_s_route_failed_on_its_start_side_notes_the_gate_and_marks_the_target(tmp_path):
    from .test_survive_ae import chaser, fight_rig
    r, sv = fight_rig(tmp_path)
    tick(r, sv)
    r.answer({"state": "failed", "reason": "stuck"})
    r.frame(x=STALL[0], y=STALL[1], zombies=[chaser()], game_min=648.5)
    tick(r, sv)
    assert [x[1] for x in r.world.door_fails[GATE]] == ["not crossed"]
    assert sv.edge_marks.get(1) == ((10747, 10642, 0), "N")


def test_a_superseded_route_leg_notes_nothing(tmp_path):
    from agent.base.planner.policies import PREEMPTED
    r, runner = goal_rig(tmp_path)
    step(r, runner)
    g = runner.current
    a = g.last
    a.state, a.reason = "failed", PREEMPTED
    assert g._route_ended(r.world, a) is None and GATE not in r.world.door_fails and g.edge_route is None


# ================================================================ m2: the stale route cleared
def test_a_route_read_that_finds_no_edge_clears_the_stale_route(tmp_path):
    """m2: a route leg superseded (its end never read), then a route read from across the gate finding no edge: the
    old record is cleared, so the next leg's `done` is read as a plain leg (no `route_end`, nothing noted)."""
    r, runner = goal_rig(tmp_path)
    step(r, runner)
    g = runner.current
    assert g.edge_route is not None
    r.frame(x=BEYOND[0], y=BEYOND[1], game_min=648.5)
    assert g._edge_cmd(r.world, EDGE[0], EDGE[1], 40.0) is None and g.edge_route is None
    g.leg = (EDGE[0], EDGE[1])
    a = act("a9", "walkTo", x=EDGE[0], y=EDGE[1], gait="walk")
    a.state = "done"
    r.frame(x=STALL[0], y=STALL[1], game_min=649.0)
    assert g._leg_ended(a, r.world) == "next" and g.take_route_end() is None and GATE not in r.world.door_fails


def test_the_route_end_reads_only_its_own_walk(tmp_path):
    """m2's second guard: a walk whose target is not the route record's is never read against it."""
    r, runner = goal_rig(tmp_path)
    step(r, runner)
    g = runner.current
    a = act("a8", "walkTo", x=EDGE[0], y=EDGE[1], gait="walk")
    a.state = "done"
    assert g._route_ended(r.world, a) is None and GATE not in r.world.door_fails


def test_leg_done_helper_still_reads_the_route(tmp_path):
    """The fixture's own read (`test_survive_ae.leg_done`) after the fix: an uncrossed `done` noted once."""
    r, runner = goal_rig(tmp_path)
    step(r, runner)
    leg_done(r, runner, STALL)
    assert [x[1] for x in r.world.door_fails[GATE]] == ["not crossed"]
