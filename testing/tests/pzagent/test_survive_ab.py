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
- P27-H, the stance at a fallen zombie out of reach (`FALLEN_SEEK`): a target fallen beyond FINISH_R for
  FALLEN_SEEK_TICKS is walked to, or left with a standing zombie within DANGER_R or its line blocked (logged
  `fallen_seek`).
- P27-I, the listing's count (`LISTING_FALLEN`): the `many` counts leave out a fallen zombie and one across a known
  blocked edge out of the hold radius (logged `listing`).
- P27-J, the shove-only fight's close (`SHOVE_CLOSE`): the hold's lone fight only at a chaser, the rest kept at an idle
  one (logged `rest` {idle}); a chaser holding beyond point blank for SHOVE_CLOSE_TICKS walked to (logged
  `shove_close`), or left for a blocked line.
- P27-K1, the rag stock ahead of the bleed (`STOCK_EARLY`): the stock's rip on any tick with no zombie within DANGER_R
  under RAG_STOCK, a goal walk superseded, and the care yield taking the wound's rip (logged `stock_early`).
- P27-K2, the low fight's exit (`LOW_EXIT`): after SHOVE_FAIL_N missed shoves the low fight leaves its target for the
  `health` flee (logged `low_exit`), and the inside corner yields to that flee under FLEE_HEALTH_FLOOR (logged
  `corner` {yield health}).
- P27-K3, the replace held off under a chaser (`REPLACE_QUIET`): no replace while a listed zombie chases (logged
  `spent_held`).
- P27-L, P26-L1's divided swing withdrawn: `WOUNDED_SWING` off by default.
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
    logged `listing` {fallen 0, across 1}; across a fence within the hold radius (DANGER_R's, no threat policy running)
    it counts: with the fence at x 103 and the chaser 4.5 tiles east beyond it, the target 4 tiles north, the four make
    `many`."""
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
    (tmp_path / "held").mkdir()
    r3, sv3 = make(tmp_path / "held")
    r3.scan([square(x, 200, blockW=x == 103) for x in range(99, 113)])
    fr(r3, [z(1, 100.0, 204.0), z(7, 104.5)] + far)
    tick(r3, sv3)
    w = threat_why(tmp_path / "held")
    assert w["flee"] == "many" and "listing" not in w


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


# ================================================================ P27-K1: the rag stock ahead of the bleed
from agent.base import pza1                                                          # noqa: E402

from .test_survive_g import care_frame, garment, hello152, hold, part              # noqa: E402


def shirt_rig(tmp_path, source=None, dressings=()):
    """F10's undressed bleed, ahead of it: a PZA/1.5.2 build (the item record's `worn` and `rip`), the looted unworn
    cotton T-shirt 22 held (F10's 1034854646), the clean dressings `dressings` [(id, fullType)] held, no part
    bleeding."""
    r = Rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=source)
    hello152(r)
    r.frame()
    garment(r, 22, ft="Base.Tshirt_WhiteTINT", rip="cotton")
    for iid, ft in dressings:
        hold(r, iid, ft)
    care_frame(r, [part(5)])
    return r, sv


def test_f10_s_last_rag_gone_the_stock_rips_over_a_running_goal_walk(tmp_path):
    """F10's game minutes 656 to 665 (the last clean rag on at 656, the T-shirt held, no stock rip before the bites):
    a goal walk runs with two dressings held; the dressings gone (under RAG_STOCK), the next tick's stock rips the
    T-shirt over the running walk (a rip is a few seconds standing), logged `stock_early` {rags 0, bandages 0, branch
    goal}; with `STOCK_EARLY` off the walk runs on and nothing is ripped."""
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r, sv = shirt_rig(d, Src(ExploreToward(110, 200)), ((10, "Base.Bandage"), (12, "Base.RippedSheets")))
        sv.STOCK_EARLY = on
        sv.goals.kit.bind(r.world, r.acts)
        sv.goals.kit.explore.scanned.add(sv.goals.kit.explore.place())
        walk = tick(r, sv)
        assert walk.type == "walkTo"
        r.fake.act(walk.aid, "accepted", "walkTo")
        r.pump()
        for iid in (10, 12):
            r.event("item_removed", itemId=iid)
        care_frame(r, [part(5)])
        a = tick(r, sv)
        if on:
            assert (a.type, a.args) == ("rip", {"itemId": 22}) and last(d)["branch"] == "care"
            stock = last(d)["inputs"]["branches"]["care"]["stock"]
            assert stock["stock_early"] == {"rags": 0, "bandages": 0, "branch": "goal"}
        else:
            assert a is None and r.acts.current is walk and "rip" not in sends(r)


@pytest.mark.parametrize("extra", ["idle_at_9_5", "dirty_rag"])
def test_the_early_stock_rips_with_an_idle_zombie_beyond_danger_r_or_a_dirty_rag_held(tmp_path, extra):
    """No zombie within DANGER_R (one idle 9.5 tiles off, within DISENGAGE_R: the old stock's quiet refused it), or a
    dirty rag held (no clean dressing: the clean dressings under RAG_STOCK, F10's {bandage 0, dirty 1, rag 0}): the
    T-shirt is ripped, logged `stock_early` {branch stock}."""
    dressings = ((11, "Base.RippedSheetsDirty"),) if extra == "dirty_rag" else ()
    r, sv = shirt_rig(tmp_path, dressings=dressings)
    zs = [z(1, 109.5, has_target=False)] if extra == "idle_at_9_5" else []
    r.frame(zombies=zs)
    care_frame(r, [part(5)], zombies=zs)
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 22})
    assert last(tmp_path)["inputs"]["branches"]["care"]["stock"]["stock_early"]["branch"] == "stock"


def bleeding_shirt(tmp_path, zs, **k):
    """F10's bites at game minutes 665 and 667 (parts 1 and 7 bleeding undressed, the T-shirt held): part 7 bleeding,
    no dressing, zombies `zs`."""
    r, sv = shirt_rig(tmp_path)
    care_frame(r, [part(7, bleeding=True, bleedingTime=12.0)], zombies=zs, **k)
    return r, sv


def test_f10_s_wound_rip_under_the_flee_is_held_while_the_nearest_stays_beyond_care_hold_r(tmp_path):
    """F10's lines 817, 832 and 847 (the wound's rip superseded each time by the threat branch's flee legs, a167, a169,
    a171): the endurance hold's `strain` flee from a chaser 5 tiles off (a second chaser listed 9 tiles west refusing
    the hold's lone fight), the care's rip of the T-shirt running: the yield holds it (nothing sent, the rip still
    current) as it holds a running bandage; with `STOCK_EARLY` off the flee's leg supersedes it."""
    two = [z(1, 105.0), z(2, 91.0)]
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r, sv = bleeding_shirt(d, two, endurance=HOLD_E)
        sv.STOCK_EARLY = on
        assert tick(r, sv).type == "steer" and threat_why(d)["flee"] == "strain"
        r.answer()
        rip = sv.care.send(pza1.Rip(22))   # the care's own rip of the T-shirt for part 7 (F10's a166), running
        r.fake.act(rip.aid, "accepted", "rip")
        r.pump()
        r.advance(0.5)
        care_frame(r, [part(7, bleeding=True, bleedingTime=12.0)], zombies=two, endurance=HOLD_E)
        a = tick(r, sv)
        if on:
            assert a is None and r.acts.current is rip and last(d)["branch"] == "care"
        else:
            assert a.type == "steer" and r.acts.history[-1] is a


def test_the_bleed_s_yield_under_a_fight_takes_the_wound_s_rip(tmp_path):
    """P26-D's yield (a Fight's tick with no zombie within FIGHT_REACH, the nearest within CARE_R) with nothing to
    dress part 7 but the T-shirt: the rip goes (the threat why's `care_yield` {why bleed}, the care line's
    `stock_early` {branch yield}); with `STOCK_EARLY` off the yield takes a dressing only and the Fight answers."""
    one = [z(1, 103.0)]
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r, sv = bleeding_shirt(d, one)
        sv.STOCK_EARLY = on
        first = tick(r, sv)
        assert sv.mode == "fight" and first.type != "rip"
        r.fake.act(first.aid, "accepted", first.type)
        r.pump()
        r.advance(0.5)
        care_frame(r, [part(7, bleeding=True, bleedingTime=12.0)], zombies=one)
        a = tick(r, sv)
        if on:
            assert (a.type, a.args) == ("rip", {"itemId": 22})
            assert threat_why(d)["care_yield"]["why"] == "bleed"
            assert last(d)["inputs"]["branches"]["care"]["stock_early"] == {"rags": 0, "bandages": 0,
                                                                             "branch": "yield"}
        else:
            assert a is None or a.type != "rip"


# ================================================================ P27-K2: the low fight's exit
from .test_survive_aa import ATTACK_DONE, lone, shoves                             # noqa: E402

PAINED = {"arm": 25.0, "strain": {"l": 0.0, "r": 0.0}}   # the arms' pain at STRAIN_HARD, no stiffness: no hold, the
# low fight's full swing barred (F10's hall: the arms' summed pain 113 to 241.3, #T82.7)


def test_f10_s_low_fight_leaves_its_lone_target_after_shove_fail_n_missed_shoves(tmp_path):
    """F10's hall (building 3, lines 1389-1456: eight shoves knocked nothing down, the swings divided, eight bites took
    the health from 36.35115051269531 to 5.18145751953125): the low fight (health 35) at its lone zombie at point blank
    with the arms' pain barring the swing: after SHOVE_FAIL_N missed shoves the Fight sends nothing, logged `low_exit`
    {target, missed 3}; the next tick the `health` flee's leg goes; with `LOW_EXIT` off the shove or a break follows,
    never the flee."""
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r, sv = make(d)
        sv.LOW_EXIT = on
        shoves(r, sv, P.SHOVE_FAIL_N, **PAINED)
        lone(r, **PAINED)
        a = tick(r, sv)
        w = threat_why(d)
        if on:
            assert a is None and w["low_exit"] == {"target": 1, "missed": 3} and w["low_fight"] is True
            r.advance(0.5)
            lone(r, **PAINED)
            a = tick(r, sv)
            assert a.type in ("steer", "walkTo") and threat_why(d)["flee"] == "health" and 1 in sv.low_left
        else:
            assert a is not None and "low_exit" not in w and "flee" not in w


def test_with_the_full_swing_due_the_low_fight_swings_once_and_leaves_after_three_more_misses(tmp_path):
    """The arms whole (P27-E's full swing due): three missed shoves take the swing (`low_swing`); three more missed
    shoves at the same zombie take the exit (`low_exit`), not a second swing."""
    r, sv = make(tmp_path)
    shoves(r, sv, P.SHOVE_FAIL_N)
    lone(r)
    assert tick(r, sv).type == "attack" and "low_swing" in threat_why(tmp_path)
    r.fake.answer({"attack": ["accepted", ATTACK_DONE]})
    r.pump()
    r.advance(1.0)
    shoves(r, sv, P.SHOVE_FAIL_N)
    lone(r)
    assert tick(r, sv) is None and threat_why(tmp_path)["low_exit"]["missed"] == 3
    assert sends(r).count("attack") == 1


def test_f10_s_inside_corner_yields_to_the_health_flee_under_flee_health_floor(tmp_path):
    """F10's line 1442 (health 11.3414306640625: the `health` flee's window step superseded on the next line by the
    inside corner's shove at point blank): E16's shed with a109's zombies at the door (one within POINT_BLANK_R), a way
    out known, health 15: no corner, the `health` flee's leg goes, logged `corner` {yield health}; at health 25 (at or
    above FLEE_HEALTH_FLOOR), or with `LOW_EXIT` off, the inside corner as before."""
    from .test_survive_y import E16_470, shed
    from .test_survive_y import zs as yzs
    me, rows = E16_470
    for health, on, corner in ((15.0, True, False), (25.0, True, True), (15.0, False, True)):
        d = tmp_path / ("%s-%s" % (health, on))
        d.mkdir()
        r, sv = make(d)
        sv.LOW_EXIT = on
        r.scan(shed())
        r.frame(x=me[0], y=me[1], zombies=yzs(rows, me), health=health, attackers=1)
        a = tick(r, sv)
        w = threat_why(d)
        if corner:
            assert w["corner_kind"] == "inside" and "corner" in w and w["corner"].get("yield") is None, (health, on)
        else:
            assert "cornered" not in w and w["flee"] == "health" and w["corner"] == {"yield": "health"}
            assert a is not None and a.type in ("walkTo", "steer", "window", "interact")


# ================================================================ P27-K3: the replace held off under a chaser
from .test_survive_g import care_why                                               # noqa: E402


def spent_part4(tmp_path, zs, on=True):
    """F10's spent replaces (each bled its part for the act's 5.978 to 6.281 s; the one superseded after the dressing
    came off bled part 4 five game minutes, #T82.4): part 4 under a spent dressing (`bandageLife` 0), not bleeding, its
    bleedingTime 5.0 (under SPENT_REDRESS_BT: P27-D replaces it), a clean bandage held, zombies `zs`; one tick."""
    r, sv = make(tmp_path)
    sv.REPLACE_QUIET = on
    r.frame(zombies=zs)
    hold(r, 11, "Base.Bandage")
    care_frame(r, [part(4, bandaged=True, bandageLife=0.0, bandageDirty=False, bleedingTime=5.0)], zombies=zs)
    tick(r, sv)
    return r, sv


def test_f10_s_spent_replace_is_held_while_a_listed_zombie_chases(tmp_path):
    """A chaser listed 10.5 tiles off (within LISTED_R, beyond ENGAGE_R: no threat held): the replace is held, nothing
    sent, logged `spent_held` {part 4, chasing 1}; the same zombie idle, or `REPLACE_QUIET` off: the bandage goes."""
    r, sv = spent_part4(tmp_path, [z(1, 110.5)])
    w = care_why(tmp_path)
    assert "bandage" not in sends(r) and w["spent_held"] == {"part": 4, "chasing": 1}
    for name, zs, on in (("idle", [z(1, 110.5, has_target=False)], True), ("off", [z(1, 110.5)], False)):
        (tmp_path / name).mkdir()
        r, sv = spent_part4(tmp_path / name, zs, on)
        assert r.cmd() == ("bandage", {"itemId": 11, "part": 4}) and "spent_held" not in care_why(tmp_path / name)


# ================================================================ P27-L: P26-L1's divided swing withdrawn
def test_f10_s_divided_swings_withdrawn_three_missed_shoves_take_the_break_by_default(tmp_path):
    """F10's six swings under the `wounded` reason after three failed shoves landed five times and lowered the target's
    listed health not at all (1.0190000534057617 before and after each), the arms' pain at 118.6 to 120.8 dividing it
    (#4370), where E19's undivided swings killed a fallen zombie in one; with E18's three, nine divided swings lowered
    no target: `WOUNDED_SWING` is off by default, so F8's last fight's geometry (three missed shoves at the lone
    standing zombie at point blank) takes P25-L's lone break, never the swing."""
    from .test_survive_z import LONE_AT, MISSED, wounded
    r, sv = make(tmp_path)
    assert sv.WOUNDED_SWING is False and S.Survive.WOUNDED_SWING is False
    for _ in range(3):
        wounded(r, LONE_AT)
        assert tick(r, sv).type == "shove"
        r.fake.answer({"shove": ["accepted", MISSED]})
        r.pump()
        r.advance(5.0)
    wounded(r, LONE_AT)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and w["corner"]["kind"] == "break" and "wounded_swing" not in w
    assert "attack" not in sends(r)


# ================================================================ iteration 20's switches and constants
def test_the_iteration_20_switches_and_constants():
    """`survive.T10_SWITCHES`, each on by default (P27-L's withdrawal is `WOUNDED_SWING`'s default, in T8_SWITCHES),
    the Fight's rules they hand down and policies.py's three new constants (the controller's numbers) and the leave's
    distance."""
    from agent.base.planner import fight as F
    assert S.T10_SWITCHES == ("STUCK_LEAVE", "FLOOR_FINISH", "FALLEN_SEEK", "LISTING_FALLEN", "SHOVE_CLOSE",
                              "STOCK_EARLY", "LOW_EXIT", "REPLACE_QUIET")
    assert "T10_SWITCHES" in S.__all__ and all(getattr(S.Survive, name) is True for name in S.T10_SWITCHES)
    assert not set(S.T10_SWITCHES) & set(S.T9_SWITCHES + S.T8_SWITCHES + S.T7_SWITCHES)
    assert {"floor_finish", "fallen_seek", "shove_close", "low_exit"} <= set(F.FIGHT_RULES)
    assert "WOUNDED_SWING" in S.T8_SWITCHES and S.Survive.WOUNDED_SWING is False
    assert (P.STUCK_MARK_MIN, P.FALLEN_SEEK_TICKS, P.SHOVE_CLOSE_TICKS, P.STUCK_LEAVE_R) == (30.0, 4, 6, 10.0)


def test_a_switch_turned_off_mid_count_sends_no_walk(tmp_path):
    """The due reads (`_fallen_due`, `_close_due`) read the rule as the tick sets it: FALLEN_SEEK_TICKS - 1 fallen
    ticks with `FALLEN_SEEK` on, then off for the tick that would be due: no walk; the same for `SHOVE_CLOSE` at the
    hold fight's chaser (the observe counts under the last tick's rules)."""
    r, sv = stance_then_fallen(tmp_path)
    for _ in range(P.FALLEN_SEEK_TICKS - 1):
        fallen_tick(r, sv)
    sv.FALLEN_SEEK = False
    fallen_tick(r, sv)
    assert "walkTo" not in sends(r) and "fallen_seek" not in threat_why(tmp_path)
    (tmp_path / "close").mkdir()
    r2, sv2 = make(tmp_path / "close")
    held_off(r2, sv2, ticks=P.SHOVE_CLOSE_TICKS - 1)
    sv2.SHOVE_CLOSE = False
    held_off(r2, sv2)
    assert "walkTo" not in sends(r2) and "shove_close" not in threat_why(tmp_path / "close")
