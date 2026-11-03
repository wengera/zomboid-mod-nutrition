"""Survival 22 (survival iteration 20; Plan 27 Task 5; E19, `e_day_19-20261103-072904`, its `GUIDE.md` §§ 1, 3, 4 and 5:
the 141.47037506103516 game minutes on the gate square with four walks `stuck` unmoved, the five kills by one swing at
a fallen zombie, fight 2's stance legs at 20951 fallen 8.683652011883524 to 11.861148063389683 tiles off, line 386's
listing; F10, `f_goals_11-20261103-075140`, its `GUIDE.md` §§ 2 to 6: the hold's lone fight at 27031, the undressed
bleed, the low fight's hall at 26967, the spent replaces, P26-L1's swings). The fake mod over PZA/1.7.1; each test's
geometry is simplified from the line its docstring names.

- P27-F, the stuck square (`STUCK_LEAVE`): a goal walk ended `stuck` unmoved marks its square and its route's first
  edge for STUCK_MARK_MIN (logged `stuck_mark`); the scripted source never rests there (logged `leave`); the view
  carries `stuck`.
"""
import pytest

from agent.base.planner import goal_prompt as GP
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import view as V
from agent.base.planner.goals import ExploreToward, GoalRunner, LootBuilding, Rest, ScriptedSource

from .test_goals import Src
from .test_policies import Rig, square
from .test_survive import last, make


def sends(r):
    return [a.type for a in r.acts.history]


# ================================================================ P27-F: the stuck square
ME = (100.4, 200.6)   # the player on the outdoor square (100, 200), as E19's on (10732, 10641) north of the gate


def open_row(r):
    """An outdoor strip from x 95 to 112 over y 199 to 201: the walk's straight line east is mapped square by square."""
    r.scan([square(x, y) for x in range(95, 113) for y in (199, 200, 201)])


def stuck_walk(r, runner, moved_to=None, reason="stuck"):
    """E19's a151 (line 587) simplified: a goal walk from the player's square east toward (110, 200), ended `failed`
    (`reason`) 6 s on, the player unmoved (or on `moved_to`); the runner then reads the end."""
    r.frame(x=ME[0], y=ME[1], game_min=640.0)
    runner.kit.bind(r.world, r.acts)
    runner.kit.explore.scanned.add(runner.kit.explore.place())
    runner.send(runner.tick(r.world, r.acts))
    assert r.cmd() == ("walkTo", {"x": 110, "y": 200, "gait": "walk"})
    r.answer({"state": "failed", "reason": reason})
    x, y = moved_to or ME
    r.frame(x=x, y=y, game_min=640.1)
    runner.observe(r.world, r.acts)


def test_a_goal_walk_ended_stuck_unmoved_marks_its_square_and_its_first_edge(tmp_path):
    """E19's four walks from the gate square (a151, a152, a154, a155: lines 587, 610, 1110 and 1608, each `stuck` 5.992
    to 5.994 s after its accept with the character unmoved): the runner marks the square (100, 200) and the route's
    first edge out of it, the west edge of (101, 200), logged `stuck_mark` {edge, square, goal}; the mark reads at the
    player's square for STUCK_MARK_MIN game minutes from the tick that read the end (game minute 640.1), no longer."""
    r = Rig(tmp_path)
    open_row(r)
    runner = GoalRunner(Src(ExploreToward(110, 200)), r.clock)
    stuck_walk(r, runner)
    want = {"edge": [101, 200, "W"], "square": [100, 200],
            "goal": {"type": "ExploreToward", "args": {"x": 110, "y": 200}}}
    assert runner.stuck_now == want
    assert runner.stuck_at(r.world) == {"square": [100, 200], "edge": [101, 200, "W"]}
    r.frame(x=ME[0], y=ME[1], game_min=640.1 + P.STUCK_MARK_MIN - 0.5)
    runner.observe(r.world, r.acts)
    assert runner.stuck_now is None and runner.stuck_at(r.world) is not None
    r.frame(x=ME[0], y=ME[1], game_min=640.2 + P.STUCK_MARK_MIN)
    assert runner.stuck_at(r.world) is None


@pytest.mark.parametrize("moved_to, reason", [((101.6, 200.6), "stuck"), (None, "no path")])
def test_a_walk_that_moved_the_player_off_its_square_or_failed_otherwise_marks_nothing(tmp_path, moved_to, reason):
    """The same walk ended `stuck` with the player on the next square east (the frame's square not the send's), or ended
    `no path` unmoved: no mark, nothing logged."""
    r = Rig(tmp_path)
    open_row(r)
    runner = GoalRunner(Src(ExploreToward(110, 200)), r.clock)
    stuck_walk(r, runner, moved_to, reason)
    assert runner.stuck_now is None and runner.stuck_marks == {}


def test_with_stuck_leave_off_the_runner_marks_nothing(tmp_path):
    """`test_a_goal_walk_ended_stuck_unmoved_marks_its_square_and_its_first_edge`'s walk with `stuck_leave` off
    (Survive's `STUCK_LEAVE`): no mark."""
    r = Rig(tmp_path)
    open_row(r)
    runner = GoalRunner(Src(ExploreToward(110, 200)), r.clock)
    runner.stuck_leave = False
    stuck_walk(r, runner)
    assert runner.stuck_now is None and runner.stuck_at(r.world) is None


def survive_stuck(tmp_path, on=True):
    """A Survive whose goal walk from (100, 200) ended `stuck` unmoved (E19's a151), its next tick read."""
    r = Rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(ExploreToward(110, 200)))
    sv.STUCK_LEAVE = on
    open_row(r)
    r.frame(x=ME[0], y=ME[1], game_min=640.0)
    sv.goals.kit.bind(r.world, r.acts)
    sv.goals.kit.explore.scanned.add(sv.goals.kit.explore.place())
    a = sv.tick(r.world, r.acts)
    assert a is not None and a.type == "walkTo"
    r.answer({"state": "failed", "reason": "stuck"})
    r.frame(x=ME[0], y=ME[1], game_min=640.1)
    sv.tick(r.world, r.acts)
    return r, sv


def test_survive_logs_the_stuck_mark_on_the_line_that_marks_and_the_view_carries_stuck(tmp_path):
    """E19's line 588 (the tick after a151's `stuck` end): the decision line's goal why carries `stuck_mark`; the goal
    view carries `stuck` {square, edge}, rendered as its own `stuck:` line after `last_goal`."""
    r, sv = survive_stuck(tmp_path)
    d = last(tmp_path)
    assert d["inputs"]["branches"]["goal"]["stuck_mark"]["square"] == [100, 200]
    v = sv._view()
    assert v["stuck"] == {"square": [100, 200], "edge": [101, 200, "W"]}
    lines = V.render(v).splitlines()
    k = [ln.split(":", 1)[0] for ln in lines]
    assert k[k.index("last_goal") + 1] == "stuck"
    assert 'stuck: {"edge":[101,200,"W"],"square":[100,200]}' in lines


def test_with_stuck_leave_off_survive_logs_no_mark_and_the_view_carries_no_stuck(tmp_path):
    """`test_survive_logs_the_stuck_mark_on_the_line_that_marks_and_the_view_carries_stuck`'s walk with `STUCK_LEAVE`
    off: no `stuck_mark`, no `stuck` key, the view's keys KEYS alone."""
    r, sv = survive_stuck(tmp_path, on=False)
    assert "stuck_mark" not in (last(tmp_path)["inputs"]["branches"].get("goal") or {})
    v = sv._view()
    assert "stuck" not in v and set(v) == set(V.KEYS)


def stuck_view(**k):
    """A scripted view with no candidate left (scanned, no edge, nothing to loot): E19's 17 Rests on the gate square,
    the player on (100, 200) marked with the west edge of (101, 200) east of it."""
    v = {"pos": {"x": ME[0], "y": ME[1], "z": 0}, "needs_wanted": [], "want_shelter": False, "buildings": [],
         "edge": None, "scanned_here": True, "stock_uses": [], "load": {"weight": 4.5, "max": 8.0, "level": 0},
         "stuck": {"square": [100, 200], "edge": [101, 200, "W"]}}
    v.update(k)
    return v


def b(bid, x, y, dist, looted=True, containers=2, door=None, blocked=False):
    return {"id": bid, "x": x, "y": y, "door": door, "dist": dist, "containers": containers, "looted": looted,
            "doors": 1, "visited": False, "shunned": False, "shelter": True, "blocked": blocked}


def test_on_a_marked_square_with_no_building_the_source_explores_away_from_the_edge(tmp_path):
    """E19's 17 Rests (lines 624 to 1644) with nothing known to walk back to: the source answers an ExploreToward
    STUCK_LEAVE_R tiles from the square on its side of the marked edge (west of a west edge east of it), never Rest;
    logged `leave` {why stuck, target}."""
    src = ScriptedSource()
    g = src.propose(stuck_view())
    assert (g.TYPE, g.args()) == ("ExploreToward", {"x": 100 - int(P.STUCK_LEAVE_R), "y": 200})
    assert src.last_leave == {"why": "stuck", "target": {"type": "ExploreToward", "args": g.args()}}
    north = src.propose(stuck_view(stuck={"square": [100, 200], "edge": [100, 201, "N"]}))
    assert north.args() == {"x": 100, "y": 200 - int(P.STUCK_LEAVE_R)}


def test_the_walk_back_to_the_nearest_building_on_the_square_s_side_comes_first(tmp_path):
    """The known cluster's nearest building on the player's side of the edge (building 2 west, its door (81, 200)) is
    the way out, before the farther one and passing over building 3 across the edge (east, nearer): an ExploreToward
    at its door."""
    v = stuck_view(buildings=[b(3, 120, 200, 19.6), b(2, 80, 200, 20.4, door=[81, 200]), b(4, 70, 200, 30.4)])
    g = ScriptedSource().propose(v)
    assert (g.TYPE, g.args()) == ("ExploreToward", {"x": 81, "y": 200})


def test_with_no_building_on_its_side_the_nearest_unlooted_one_is_looted(tmp_path):
    """Building 3 across the edge, unlooted with no container known (so no candidate loots it): a LootBuilding of it,
    the loot's own route crossing by its door."""
    v = stuck_view(buildings=[b(3, 120, 200, 19.6, looted=False, containers=0)])
    g = ScriptedSource().propose(v)
    assert (g.TYPE, g.args()) == ("LootBuilding", {"building": 3})


def test_a_cooled_way_out_is_passed_over_and_with_no_mark_the_source_rests(tmp_path):
    """The walk back cooled (the view's `cooled`): the next way out, the explore away; the same view with no `stuck`:
    Rest as before, no `leave`."""
    door = {"type": "ExploreToward", "args": {"x": 81, "y": 200}}
    v = stuck_view(buildings=[b(2, 80, 200, 20.4, door=[81, 200])], cooled=[door])
    g = ScriptedSource().propose(v)
    assert (g.TYPE, g.args()) == ("ExploreToward", {"x": 100 - int(P.STUCK_LEAVE_R), "y": 200})
    src = ScriptedSource()
    rest = src.propose({k: x for k, x in stuck_view().items() if k != "stuck"})
    assert isinstance(rest, Rest) and src.last_leave is None


def test_the_runner_logs_the_leave_on_the_source_s_next_pick(tmp_path):
    """Through the runner: a marked square, the scripted source's pick is the leave and the goal why carries `leave`."""
    r = Rig(tmp_path)
    open_row(r)
    runner = GoalRunner(ScriptedSource(), r.clock)
    r.frame(x=ME[0], y=ME[1], game_min=640.0)
    runner.tick(r.world, r.acts, stuck_view())
    assert runner.why["leave"]["why"] == "stuck" and runner.current.TYPE == "ExploreToward"


def test_the_prompt_tells_the_model_what_stuck_names():
    """The LLM source's prompt carries P27-F's sentence."""
    assert ("`stuck` names a square your walks could not leave and the edge they failed on: answer a goal away "
            "from it") in GP.system(60.0)
