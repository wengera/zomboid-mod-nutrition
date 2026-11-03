"""Survival 22 (survival iteration 20; Plan 27 Task 5; E19, `e_day_19-20261103-072904`, its `GUIDE.md` §§ 1, 3, 4 and 5:
the 141.47037506103516 game minutes on the gate square with four walks `stuck` unmoved, the five kills by one swing at
a fallen zombie, fight 2's stance legs at 20951 fallen 8.683652011883524 to 11.861148063389683 tiles off, line 386's
listing; F10, `f_goals_11-20261103-075140`, its `GUIDE.md` §§ 2 to 6: the hold's lone fight at 27031, the undressed
bleed, the low fight's hall at 26967, the spent replaces, P26-L1's swings). The fake mod over PZA/1.7.1; each test's
geometry is simplified from the line its docstring names.

- P27-F, the stuck square (`STUCK_LEAVE`): a goal walk ended `stuck` unmoved marks its square and its route's first
  edge for STUCK_MARK_MIN (logged `stuck_mark`); the scripted source never rests there (logged `leave`); the view
  carries `stuck`.
- P27-G, the floor swing as the finish (`FLOOR_FINISH`): with a weapon held and the swing allowed, the Fight's finish
  and the flee's swing at a fallen zombie within FIGHT_REACH ahead of the stomp (logged `floor_finish`); no stomp while
  a strike at the same zombie runs.
"""
import pytest

from agent.base.planner import goal_prompt as GP
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import view as V
from agent.base.planner.goals import ExploreToward, GoalRunner, LootBuilding, Rest, ScriptedSource

from .test_goals import Src
from .test_policies import Rig, square
from .test_survive import last, make, threat_why, tick
from .test_survive_q import GROUP3, fr, z


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


# ================================================================ P27-G: the floor swing as the finish
FALLEN_H = 2.0870866775512695   # E19's highest health a fallen zombie died from at one swing (GUIDE § 1, #4553)


def fallen(x=101.5, **k):
    return dict(z(1, x, floor=True), health=FALLEN_H, **k)


def test_e19_s_fallen_zombie_within_fight_reach_takes_the_floor_swing_ahead_of_the_stomp(tmp_path):
    """E19's five kills by one swing at a zombie read fallen (a30, a100, a126, a132, a149; the four landed stomps took
    0.1437922716140747 to 0.20751547813415527 each): the lone zombie fallen 1.5 tiles off, a bat held, no hold: the
    Fight's finish is the attack, logged `floor_finish` {target, health}, no stomp."""
    r, sv = make(tmp_path)
    fr(r, [fallen()])
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and w["fight"] is True
    assert w["floor_finish"] == {"target": 1, "health": FALLEN_H} and "stomp" not in w


@pytest.mark.parametrize("case", ["beyond_reach", "arms", "endurance", "off"])
def test_the_stomp_stays_the_finish_beyond_reach_with_the_swing_barred_or_the_switch_off(tmp_path, case):
    """The stomp, not the swing: the fallen one 3.5 tiles off (beyond FIGHT_REACH, within FINISH_R: the stomp's walk
    in); the arms' pain at 25 (STRAIN_HARD: `no_swing`); the endurance hold (0.6897225379943848, its fight within
    KEEP_R); or `FLOOR_FINISH` off."""
    r, sv = make(tmp_path)
    k = {"arms": {"arm": 25.0, "strain": {"l": 0.0, "r": 0.0}}, "endurance": {"endurance": 0.6897225379943848}}
    if case == "off":
        sv.FLOOR_FINISH = False
    fr(r, [fallen(103.5 if case == "beyond_reach" else 101.5)], **k.get(case, {}))
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and "floor_finish" not in w, case


def striking(r, sv):
    """The Fight's attack at zombie 1 standing 1.5 tiles off (after the stance's enter leg, when one goes), accepted
    and running."""
    for _ in range(3):
        fr(r, [z(1, 101.5)])
        a = tick(r, sv)
        r.fake.act(a.aid, "accepted", a.type)
        r.pump()
        r.advance(0.5)
        if a.type == "attack":
            assert a.args == {"targetId": 1}
            return a
    raise AssertionError(sends(r))


def test_a_running_strike_at_the_zombie_it_knocked_down_is_held_no_stomp_sent(tmp_path):
    """E19's four stomps refused `busy` (each sent while the strike at the same zombie still ran, each followed by the
    killing swing): the attack runs and its target reads fallen: the Fight holds it, no stomp; with `FLOOR_FINISH` off
    the stomp goes as before (P25-B's give-way)."""
    r, sv = make(tmp_path)
    a = striking(r, sv)
    fr(r, [fallen()])
    assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == a.aid and "stomp" not in sends(r)
    (tmp_path / "off").mkdir()
    r2, sv2 = make(tmp_path / "off")
    sv2.FLOOR_FINISH = False
    striking(r2, sv2)
    fr(r2, [fallen()])
    assert tick(r2, sv2).type == "stomp"


def test_the_many_flee_s_finish_swings_at_a_fallen_zombie_within_reach(tmp_path):
    """E19's flee finish (P27-A's two firings under `many`, each a stomp refused `busy` and the floor strike the kill):
    a zombie fallen 1.8 tiles off (beyond CORNERED_R, within FIGHT_REACH) never struck, GROUP3 chasing 7.5 off: the
    flee's finish is the attack (kind `floor_finish`, logged `floor_finish`); fallen 3.5 off, the stomp."""
    r, sv = make(tmp_path)
    sv.LISTING_FALLEN = False   # P27-I off: GROUP3 makes `many` with the fallen one counted
    fr(r, [fallen(101.8)] + GROUP3)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and w["flee"] == "many" and sv.flee.last is a
    assert w["kind"] == "floor_finish" and w["floor_finish"] == {"target": 1, "health": FALLEN_H}
    (tmp_path / "far").mkdir()
    r2, sv2 = make(tmp_path / "far")
    sv2.LISTING_FALLEN = False
    fr(r2, [fallen(103.5)] + GROUP3)
    assert tick(r2, sv2).type == "stomp"


def test_the_flee_finish_holds_while_a_strike_at_its_fallen_zombie_runs(tmp_path):
    """The Fight's attack at zombie 1 runs as GROUP3 comes into the listing and 1 reads fallen: the `many` flee's
    finish holds the strike (nothing sent, logged `strike_runs`), never a stomp or a steer over it; with
    `FLOOR_FINISH` off the stomp is sent."""
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r, sv = make(d)
        sv.FLOOR_FINISH = on
        sv.LISTING_FALLEN = False   # P27-I off: GROUP3 makes `many` with the fallen one counted
        a = striking(r, sv)
        fr(r, [fallen()] + GROUP3)
        got = tick(r, sv)
        w = threat_why(d)
        assert w["flee"] == "many"
        if on:
            assert got is None and w["strike_runs"] == {"target": 1, "aid": a.aid} and sends(r)[-1] == "attack"
        else:
            assert got.type == "stomp"


# ================================================================ P27-H: the stance at a fallen zombie out of reach
FAR = 108.683652011883524   # E19's fight 2: 20951 read fallen and unmoving 8.683652011883524 tiles off (GUIDE § 4)


def stance_then_fallen(tmp_path, extra=(), wall=False):
    """E19's fight 2 simplified: the Fight takes the stance at zombie 1 chasing 2.4 tiles off (sought at once, within
    KEEP_R), then the frames read it fallen FAR - 100 tiles off (with `extra` zombies; `wall`: a room square's west wall
    at x 104 on the line, which no P25-X read takes). Returns (r, sv) after the stance's first leg."""
    r, sv = make(tmp_path)
    if wall:
        r.scan([square(x, 200, room="hall" if x == 104 else None, blockW=x == 104) for x in range(99, 111)])
    fr(r, [z(1, 102.4)])
    assert tick(r, sv).type == "aim" and sv.mode == "fight"
    return r, sv


def fallen_tick(r, sv, extra=()):
    r.advance(0.5)
    fr(r, [z(1, FAR, floor=True)] + list(extra))
    return tick(r, sv)


def test_e19_s_stance_at_a_fallen_target_beyond_finish_r_walks_to_it_after_fallen_seek_ticks(tmp_path):
    """E19's fight 2 (eleven stance legs, 20.437649965286255 s, at 20951 lying 8.68 to 11.86 tiles off): three ticks
    the stance stands (its leg held, or the stand leg once the back leg gives way), the FALLEN_SEEK_TICKS-th the leg
    gives way and the walk to it goes at a walk, logged
    `fallen_seek` {target, dist, ticks 4}; once it lies within FINISH_R the finish's stomp takes it."""
    r, sv = stance_then_fallen(tmp_path)
    for _ in range(P.FALLEN_SEEK_TICKS - 1):
        a = fallen_tick(r, sv)
        assert (a is None or a.type == "aim") and "fallen_seek" not in threat_why(tmp_path)
    a = fallen_tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("walkTo", {"x": 108.5, "y": 200.5, "gait": "walk"})
    assert w["fallen_seek"] == {"target": 1, "dist": pytest.approx(FAR - 100.0), "ticks": P.FALLEN_SEEK_TICKS}
    r.fake.act(a.aid, "accepted", "walkTo")
    r.pump()
    r.advance(0.5)
    fr(r, [z(1, 104.5, floor=True)])
    assert tick(r, sv).type == "stomp"


def test_a_standing_zombie_within_danger_r_leaves_the_fallen_target(tmp_path):
    """The same stance with a second zombie standing idle 5 tiles south (within DANGER_R): no walk; the stance on the
    fallen one ends (`fallen_seek` {left True}), marked unreachable, and the Fight takes the standing one."""
    r, sv = stance_then_fallen(tmp_path)
    other = [z(2, 100.0, 205.0, has_target=False)]
    for _ in range(P.FALLEN_SEEK_TICKS - 1):
        fallen_tick(r, sv, other)
    a = fallen_tick(r, sv, other)
    w = threat_why(tmp_path)
    assert w["fallen_seek"]["left"] is True and 1 in sv.unreachable and "walkTo" not in sends(r)
    assert w["target"] == 2 and a is not None and a.args.get("targetId") == 2


def test_a_fallen_target_behind_a_wall_is_left_and_the_fight_released(tmp_path):
    """A wall on the line to the fallen one (a room square's west edge at x 104, no P25-X read): no walk, `left` True,
    and on the next tick, nothing else held, the threat branch releases the Fight (the goal's tick)."""
    r, sv = stance_then_fallen(tmp_path, wall=True)
    for _ in range(P.FALLEN_SEEK_TICKS):
        fallen_tick(r, sv)
    assert threat_why(tmp_path)["fallen_seek"]["left"] is True and "walkTo" not in sends(r)
    fallen_tick(r, sv)
    assert sv.mode is None and last(tmp_path)["branch"] != "threat"


def test_with_fallen_seek_off_the_stance_stands_at_the_fallen_target(tmp_path):
    """`test_e19_s_stance_at_a_fallen_target_beyond_finish_r_walks_to_it_after_fallen_seek_ticks`'s geometry with
    `FALLEN_SEEK` off: six fallen ticks, no walk, no `fallen_seek`."""
    r, sv = stance_then_fallen(tmp_path)
    sv.FALLEN_SEEK = False
    for _ in range(6):
        fallen_tick(r, sv)
        assert "fallen_seek" not in threat_why(tmp_path)
    assert "walkTo" not in sends(r)


# ================================================================ P27-I: the listing's count
TARGET = z(1, 104.0)   # the fight's standing chaser 4 tiles east (held, within DANGER_R)
FALLEN_TWO = [z(2, 100.0, 207.0, floor=True), z(3, 100.0, 192.0, floor=True)]   # E19 line 386's 20937 and 20974:
# fallen, read chasing, 7 and 8 tiles off (listed, beyond DANGER_R)
STANDING_FAR = z(4, 110.538954093041877)   # E19's 20944, standing and chasing 10.538954093041877 tiles off


def test_e19_s_line_386_two_fallen_in_the_listing_make_no_many(tmp_path):
    """E19's line 386 (the listing's count of four began a new `many` episode: two of the four it counted read fallen):
    the target 4 tiles off, two fallen 7 and 8 off, a standing chaser 10.54 off: the fallen are left out, two counted,
    no `many`: the fight, logged `listing` {fallen 2, across 0}; with `LISTING_FALLEN` off, `many` on the listing."""
    r, sv = make(tmp_path)
    fr(r, [TARGET] + FALLEN_TWO + [STANDING_FAR])
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w.get("flee") != "many" and w["listing"] == {"fallen": 2, "across": 0} and "listed" not in w
    (tmp_path / "off").mkdir()
    r2, sv2 = make(tmp_path / "off")
    sv2.LISTING_FALLEN = False
    fr(r2, [TARGET] + FALLEN_TWO + [STANDING_FAR])
    tick(r2, sv2)
    w = threat_why(tmp_path / "off")
    assert w["flee"] == "many" and w["listed"] == 4 and "listing" not in w


def fence_row(r):
    """An outdoor strip y 200, x 99 to 112, its square 106's west edge a blocked, unhoppable fence (P25-X's known
    blocked edge, as E19's fence row at y 10642 with its locked gate)."""
    r.scan([square(x, 200, blockW=x == 106) for x in range(99, 113)])


def test_e19_s_gate_zombie_across_the_fence_out_of_the_hold_is_left_out_of_the_listing(tmp_path):
    """E19's 20923, the gate zombie across the fence row, counted at line 386: here a chaser 11 tiles east across the
    fence (beyond the hold radius), the target 4 off and two chasers 9.5 north and south: three counted, no `many`,
    logged `listing` {fallen 0, across 1}; within the hold radius (8 tiles east, with a fight's DISENGAGE_R hold, or the
    target's own side) it counts."""
    r, sv = make(tmp_path)
    fence_row(r)
    far = [z(5, 100.0, 209.5), z(6, 100.0, 190.5)]
    fr(r, [TARGET, z(7, 111.0)] + far)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w.get("flee") != "many" and w["listing"] == {"fallen": 0, "across": 1}
    (tmp_path / "off").mkdir()
    r2, sv2 = make(tmp_path / "off")
    sv2.LISTING_FALLEN = False
    fence_row(r2)
    fr(r2, [TARGET, z(7, 111.0)] + far)
    tick(r2, sv2)
    assert threat_why(tmp_path / "off")["flee"] == "many"


def test_the_held_count_leaves_the_fallen_out_during_a_fight(tmp_path):
    """A running fight (mode fight, the hold radius DISENGAGE_R): its standing target 2.4 tiles off and two fallen
    chasers 7 and 8 off: the held count reads one, not three over MAX_FIGHT: no `many`; with the switch off, `many`."""
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r, sv = make(d)
        sv.LISTING_FALLEN = on
        fr(r, [z(1, 102.4)])
        assert tick(r, sv).type == "aim" and sv.mode == "fight"
        r.advance(0.5)
        fr(r, [z(1, 102.4)] + FALLEN_TWO)
        tick(r, sv)
        assert (threat_why(d).get("flee") == "many") is (not on), on


# ================================================================ P27-J: the shove-only fight's close
HOLD_E = 0.6897225379943848   # E18's endurance under the hold (test_survive_aa's), F10's hold read lower


def held_off(r, sv, x=103.3, ticks=1, **k):
    """`ticks` ticks of the frame with zombie 1 standing at (`x`, 200) (`k` laid over it), under the endurance hold;
    each leg sent is accepted and left running. The last tick's action."""
    a = None
    for _ in range(ticks):
        fr(r, [dict(z(1, x), **k)], endurance=HOLD_E)
        a = tick(r, sv)
        if a is not None:
            r.fake.act(a.aid, "accepted", a.type)
            r.pump()
        r.advance(0.5)
    return a


def test_f10_s_hold_rests_at_an_idle_zombie_within_danger_r(tmp_path):
    """F10's fifth reading (P27-C stood 12.509 s facing 27031 reading no target of its own, `hasTarget` false, 2.8 to
    3.4 tiles off): under the endurance hold the lone idle zombie 3.3 tiles off takes no hold fight; the hold's rest
    runs, nothing sent, logged `rest` {endurance, since_min, idle 1}; with `SHOVE_CLOSE` off, P27-C's hold fight."""
    r, sv = make(tmp_path)
    assert held_off(r, sv, hasTarget=False) is None
    w = threat_why(tmp_path)
    assert w["flee"] == "strain" and w["rest"]["idle"] == 1 and "hold_fight" not in w and sends(r) == []
    (tmp_path / "off").mkdir()
    r2, sv2 = make(tmp_path / "off")
    sv2.SHOVE_CLOSE = False
    assert held_off(r2, sv2, hasTarget=False).type == "aim" and threat_why(tmp_path / "off")["hold_fight"] is True


@pytest.mark.parametrize("k", [{"hasTarget": True}, {"hasTarget": None}])
def test_a_chasing_zombie_or_one_with_no_target_read_takes_the_hold_fight(tmp_path, k):
    """`hasTarget` true, or a frame carrying none (read None): the lone zombie is the hold fight's (P27-C)."""
    r, sv = make(tmp_path)
    assert held_off(r, sv, **k).type == "aim" and threat_why(tmp_path)["hold_fight"] is True


def test_f10_s_hold_fight_closes_on_a_chaser_holding_beyond_point_blank(tmp_path):
    """F10's hold fight (lines 656-681: the stance at 27031, the zombie at 2.86 then 3.2 to 3.4 tiles for twenty lines,
    five aim legs and nothing else): the chaser holding 3.3 tiles off, alone: the stance stands five ticks, the
    SHOVE_CLOSE_TICKS-th the leg gives way and the walk to the square one short of it goes at a walk, logged
    `shove_close` {target, dist, ticks}; arrived at point blank, the shove."""
    r, sv = make(tmp_path)
    for k in range(P.SHOVE_CLOSE_TICKS - 1):
        a = held_off(r, sv)
        assert (a is None or a.type == "aim") and "shove_close" not in threat_why(tmp_path), k
    a = held_off(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("walkTo", {"x": 102.5, "y": 200.5, "gait": "walk"}) and w["hold_fight"] is True
    assert w["shove_close"] == {"target": 1, "dist": pytest.approx(3.3), "ticks": P.SHOVE_CLOSE_TICKS}
    a = held_off(r, sv, x=100.8)
    assert (a.type, a.args) == ("shove", {"targetId": 1}) and threat_why(tmp_path)["shove"] == "hold"


def test_a_chaser_behind_a_wall_is_left_and_the_hold_rests(tmp_path):
    """The same chaser with a wall on the line (a room square's west edge at x 102, which no P25-X read takes): no walk;
    the target is left (`shove_close` {left True}, marked unreachable) and on the next tick the hold rests (no leg,
    `rest`) though it stands chasing within DANGER_R."""
    r, sv = make(tmp_path)
    r.scan([square(x, 200, room="hall" if x == 102 else None, blockW=x == 102) for x in range(99, 106)])
    held_off(r, sv, ticks=P.SHOVE_CLOSE_TICKS)
    w = threat_why(tmp_path)
    assert w["shove_close"]["left"] is True and 1 in sv.unreachable and "walkTo" not in sends(r)
    n = len(r.acts.history)
    assert held_off(r, sv) is None and "rest" in threat_why(tmp_path) and len(r.acts.history) == n


def test_the_unarmed_fight_closes_on_a_chaser_and_never_on_an_idle_one(tmp_path):
    """The unarmed fight (no weapon, health 100: P25-P) at a chaser 3.3 tiles off: the close walk on the
    SHOVE_CLOSE_TICKS-th tick; at the same zombie idle (`hasTarget` false) eight ticks and no walk."""
    for idle in (False, True):
        d = tmp_path / str(idle)
        d.mkdir()
        r, sv = make(d)
        for _ in range(P.SHOVE_CLOSE_TICKS + (2 if idle else 0)):
            fr(r, [z(1, 103.3, has_target=not idle)], weapon=None)
            a = tick(r, sv)
            if a is not None:
                r.fake.act(a.aid, "accepted", a.type)
                r.pump()
            r.advance(0.5)
        assert ("walkTo" in sends(r)) is (not idle) and threat_why(d)["unarmed_fight"] is True


def test_with_shove_close_off_the_hold_fight_stands_at_the_chaser(tmp_path):
    """`test_f10_s_hold_fight_closes_on_a_chaser_holding_beyond_point_blank`'s chaser with `SHOVE_CLOSE` off: eight
    ticks, no walk (F10's twenty lines of aim legs)."""
    r, sv = make(tmp_path)
    sv.SHOVE_CLOSE = False
    held_off(r, sv, ticks=8)
    assert "walkTo" not in sends(r) and "shove_close" not in threat_why(tmp_path)
