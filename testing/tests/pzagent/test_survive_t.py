"""Survival 14 (survival iteration 13; Plan 25 Task 3; E11, `e_day_11-20261030-113732`, rows #4402-#4412, and F3,
`f_goals_4-20261030-114742`, rows #4413-#4427). The fake mod over PZA/1.7.1.

- P25-A, the corner under a hold: after a shove whose result read no knock-down, one standing zombie within FIGHT_REACH
  takes the swing only while it is undivided (review-t3 finding 1: else it is shoved again), two take a steer through the gap the shove opened;
  never a second shove at the same target within SHOVE_REPEAT_S.
- P25-B, the stomp before a running attack: a fallen zombie within FINISH_R is stomped before any attack walk toward a
  standing one beyond FIGHT_REACH, a running attack giving way on the first frame that reads it fallen.
- P25-C, the endurance hold on the run: the `strain` flee walks with no zombie within DANGER_R and runs inside it; the
  hold releases above ENDURANCE_RELEASE as before, or after HOLD_SPAN_MIN game minutes with no zombie within DANGER_R
  for HOLD_QUIET_S; the goal view carries the hold (`spent` {kind, value}).
- P25-D, the ride waits: a riding bandage in flight holds a Fight that sends no swing (a hold, or the arms' pain) off
  its shoves, stomps and legs, unless the frame reads DRAG_DOWN_N - 1 attackers.
- P25-E, the stand's stalled walk: a doorway stand's walk that stalls re-routes once through `reachable_adjacent`, then
  drops the plan (`doorway_left` `stall`); a walk still within STUCK_MOVE for DOOR_WALK_S stalls whatever the zombies.
- P25-F, the fence wait: a chaser across a known hoppable edge is waited for in the stance FENCE_BACK_R back on the
  player's own side, never repositioned for nor marked unreachable, until the stand clock's STAND_MAX_S.
"""
import functools
import os

import pytest

from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .test_policies import all_sends_valid
from .test_survive import make, threat_why, tick
from .test_survive_q import fr, z

F3 = "f_goals_4-20261030-114742"


# ================================================================ P25-C: the hold in the goal view
def test_the_goal_view_carries_the_endurance_hold_as_spent_and_none_without_a_hold(tmp_path):
    """F3's hold read: endurance 0.7267035841941833 (#4415's first reading under ENDURANCE_T, game minute 648): the
    view's `spent` is {kind endurance, value 0.7267035841941833}; at endurance 0.9 no hold, no key."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 104.0)], endurance=0.7267035841941833)
    tick(r, sv)
    assert sv._view()["spent"] == {"kind": "endurance", "value": 0.7267035841941833}
    (tmp_path / "fit").mkdir()
    r2, sv2 = make(tmp_path / "fit")
    r2.frame(zombies=[z(1, 104.0)], endurance=0.9)
    tick(r2, sv2)
    assert "spent" not in sv2._view()


def test_the_goal_source_s_rendered_view_carries_the_hold_line(tmp_path):
    """End to end with Task 4's render (`view.render`): the hold read this tick is the view's `hold:` line."""
    from agent.base.planner import view as V
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 104.0)], endurance=0.7267035841941833)
    tick(r, sv)
    assert "hold: endurance 0.73" in V.render(sv._view()).splitlines()


def test_the_spent_view_reads_the_stiffness_for_the_arms_and_the_fatigue_for_tired(tmp_path):
    r, sv = make(tmp_path)
    fr(r, [z(1, 104.0)], 12.0, {"l": 25.0, "r": 3.0})
    tick(r, sv)
    assert sv.spent_view() == {"kind": "arms", "value": 25.0}
    (tmp_path / "tired").mkdir()
    r2, sv2 = make(tmp_path / "tired")
    r2.frame(zombies=[z(1, 104.0)], fatigue=0.7)
    tick(r2, sv2)
    assert sv2.spent_view() == {"kind": "tired", "value": 0.7}


def test_the_iteration_13_constants():
    assert P.SHOVE_REPEAT_S == 3.0 and (P.HOLD_SPAN_MIN, P.HOLD_QUIET_S) == (15.0, 20.0)
    assert P.DOOR_WALK_S == 20.0 and P.FENCE_BACK_R == (1.5, 2.5)
    for name in T.T3_SWITCHES:
        assert getattr(S.Survive, name) is True, name
    assert T.T3_SWITCHES == ("CORNER_BREAK", "FINISH_FIRST", "HOLD_RUN", "RIDE_WAIT", "DOOR_WALK", "FENCE_WAIT")


# ================================================================ P25-A: the corner under a hold
WOUND = 219.9          # E11's `body.armPain` on its last corners (line 430, #4406: 38.3 at the onset, 270.1 at the end)
NO_STIFF = {"l": 0.0, "r": 0.0}
MISS = {"state": "done", "result": {"attackStarted": True, "knockdown": False, "targetDead": False}}
DOWN = {"state": "done", "result": {"attackStarted": True, "knockdown": True, "targetDead": False}}
A112 = [z(1, 100.49), z(2, 100.0, 201.54)]   # E11's frame 3603 (#4408): 27606 at 0.49, 27613 at 1.54, both chasing
A116 = [z(1, 100.58), z(2, 100.0, 198.09)]   # ... and 3665: 27613 at 0.58, 27606 at 1.91


def shoved(tmp_path, zs, end=MISS, arm=WOUND, **k):
    """The `wounded` corner of E11 (health 70, the arms' pain `arm`, no stiffness): the walk corner on zombie 1 at
    point blank shoves it (P24-AG), the shove ends `end`, half a second passes and the frame is read again."""
    r, sv = make(tmp_path)
    fr(r, zs, arm, NO_STIFF, health=70.0, **k)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "shove" and a.args["targetId"] == 1 and w["cornered"] == 1 and w["shove"] == "strain"
    r.fake.answer({"shove": ["accepted", end]})
    r.pump()
    r.advance(0.5)
    fr(r, zs, arm, NO_STIFF, health=70.0, **k)
    return r, sv


@pytest.mark.parametrize("zs", [A112, A116])
def test_e11_two_at_point_blank_after_a_missed_shove_break_away_through_the_gap(tmp_path, zs):
    """E11's last corners (#4406: seven shoves, none knocking down, no swing; the two zombies within FIGHT_REACH): the
    shove read `knockdown` false, so the next answer is the steer at a run away from the shoved zombie's bearing (west
    of zombie 1), never a second shove; logged `corner` {kind break}."""
    r, sv = shoved(tmp_path, zs)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and a.args["gait"] == "run" and a.args["vx"] < -0.99 and abs(a.args["vy"]) < 0.01
    assert w["corner"] == {"kind": "break", "shoved": 1, "n": 2} and w["cornered"] == 1
    assert sum(1 for x in r.acts.history if x.type == "shove") == 1
    all_sends_valid(r)


def test_one_at_point_blank_after_a_missed_shove_is_shoved_again_while_the_swing_is_divided(tmp_path):
    """Review-t3 finding 1 (#4370, #4371, #4373, #4374): at E11's armPain (219.9, a divider of 22) the swing lands at
    1/22 of its damage, the shove's knock-down is a crit roll pain does not touch: alone within FIGHT_REACH, the
    missed-shove zombie is shoved again at once (SHOVE_REPEAT_S binds the break's pair only). Named change, ruling
    P25-I (Plan 25 Task 7): the branch is logged, `corner` {kind shove, sore true}."""
    r, sv = shoved(tmp_path, [z(1, 100.49)])
    a = tick(r, sv)
    assert (a.type, a.args) == ("shove", {"targetId": 1})
    assert threat_why(tmp_path)["corner"] == {"kind": "shove", "shoved": 1, "n": 1, "sore": True}
    assert not any(x.type == "attack" for x in r.acts.history)
    all_sends_valid(r)


def test_boxed_in_with_no_clear_heading_is_shoved_again_not_swung_at(tmp_path):
    """Two within reach but no heading clear (the break fails): the divided swing is not the answer, the shove is
    (named change, P25-I: logged `corner` {kind shove})."""
    r, sv = shoved(tmp_path, A112)
    sv.fight.clear_heading = lambda *a, **k: False   # no gap
    sv.fight._clear_turn = lambda *a, **k: None
    a = tick(r, sv)
    assert a.type == "shove" and threat_why(tmp_path)["corner"] == {"kind": "shove", "shoved": 1, "n": 2, "sore": True}


@pytest.mark.parametrize("k", [{"endurance": 0.6}, {"fatigue": 0.7}])
def test_under_the_endurance_or_tired_hold_the_missed_shove_is_shoved_again(tmp_path, k):
    """The hold halves the swing again (#4371): the lone zombie missed by a shove is shoved again, never swung at
    (named change, P25-I: logged `corner` {kind shove, sore false}: no arms' pain read)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 100.49)], health=70.0, **k)
    assert tick(r, sv).type == "shove"
    r.fake.answer({"shove": ["accepted", MISS]})
    r.pump()
    r.advance(0.5)
    r.frame(zombies=[z(1, 100.49)], health=70.0, **k)
    a = tick(r, sv)
    assert a.type == "shove" and threat_why(tmp_path)["corner"] == {"kind": "shove", "shoved": 1, "n": 1, "sore": False}


def test_the_arms_hold_alone_leaves_the_swing_undivided_so_the_corner_swings(tmp_path):
    """The swing is undivided (armPain under STRAIN_SOFT, no endurance or tired hold): the corner's swing is taken."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 100.49)], 5.0, {"l": 25.0, "r": 0.0}, health=70.0)
    a = tick(r, sv)
    assert a.type == "shove" and sv.spent_kinds == ("arms",)
    r.fake.answer({"shove": ["accepted", MISS]})
    r.pump()
    r.advance(0.5)
    fr(r, [z(1, 100.49)], 5.0, {"l": 25.0, "r": 0.0}, health=70.0)
    assert tick(r, sv).type == "attack" and threat_why(tmp_path)["corner"]["kind"] == "swing"


def test_a_shove_that_knocked_its_target_down_is_no_corner_answer(tmp_path):
    """The knock-down read (P24-AV): the Fight waits for the frame's `onFloor`, nothing sent, no `corner`; read
    standing again past KNOCK_READ_S (still within SHOVE_REPEAT_S of the shove) it is shoved again, no `corner`."""
    r, sv = shoved(tmp_path, [z(1, 100.49)], end=DOWN)
    assert tick(r, sv) is None and "corner" not in threat_why(tmp_path)
    r.advance(P.KNOCK_READ_S)
    fr(r, [z(1, 100.49)], WOUND, NO_STIFF, health=70.0)
    assert P.KNOCK_READ_S + 0.5 < P.SHOVE_REPEAT_S
    a = tick(r, sv)
    assert a.type == "shove" and "corner" not in threat_why(tmp_path)


def test_past_shove_repeat_s_the_shove_goes_again(tmp_path):
    """The window: SHOVE_REPEAT_S after the missed shove's send, the point-blank shove (P24-AG) is sent again."""
    r, sv = shoved(tmp_path, [z(1, 100.49)])
    r.advance(P.SHOVE_REPEAT_S)
    fr(r, [z(1, 100.49)], WOUND, NO_STIFF, health=70.0)
    a = tick(r, sv)
    assert a.type == "shove" and "corner" not in threat_why(tmp_path)


def test_under_the_endurance_hold_a_missed_shove_breaks_away_too(tmp_path):
    """The corner under any hold: the endurance hold's point-blank shove (R2) missed, two within reach: the break."""
    r, sv = make(tmp_path)
    r.frame(zombies=A112, endurance=0.6, health=70.0)
    assert tick(r, sv).type == "shove"
    r.fake.answer({"shove": ["accepted", MISS]})
    r.pump()
    r.advance(0.5)
    r.frame(zombies=A112, endurance=0.6, health=70.0)
    assert tick(r, sv).type == "steer" and threat_why(tmp_path)["corner"]["kind"] == "break"


def test_with_corner_break_off_the_missed_shove_is_shoved_again(tmp_path):
    """The switch (`Survive.CORNER_BREAK`, the replay tests' seam): off, E11's rule: the shove again."""
    r, sv = shoved(tmp_path, A112)
    sv.CORNER_BREAK = False
    assert tick(r, sv).type == "shove"


# ================================================================ P25-B: the stomp before a running attack
def attack_running(tmp_path, zs, caps=None):
    """E11's third target (#4405): zombie 1 standing 1.74 tiles off; the stance's enter leg, then the attack, accepted
    and running (the Lua walks in to the bat's reach)."""
    r, sv = make(tmp_path, caps=caps)
    r.frame(zombies=zs)
    a = tick(r, sv)
    if a.type == "aim":
        r.fake.answer({"aim": ["accepted"]})
        r.pump()
        r.frame(zombies=zs)
        a = tick(r, sv)
    assert (a.type, a.args) == ("attack", {"targetId": 1})
    r.fake.answer({"attack": ["accepted"]})
    r.pump()
    return r, sv


def test_e11_s_third_target_fallen_under_the_running_attack_is_stomped_on_its_first_fallen_frame(tmp_path):
    """#4405: 27581 read fallen 2.1044 tiles off two frames after the attack's acceptance and lay 4.3 s while the attack
    ran to `out of reach`: the running attack gives way on the first frame reading it fallen and the stomp goes (its
    walk in to it), logged `finish_first` {target, dist}. Named change, Plan 25 Task 8 (P25-J): with `FINISH_FAR` on
    the finish itself reads the fallen out to FINISH_R (no standing zombie within KEEP_R), so P25-B's own why is pinned
    with it off (`test_survive_v` pins the stomp with it on)."""
    r, sv = attack_running(tmp_path, [z(1, 101.74)])
    sv.FINISH_FAR = False
    r.frame(zombies=[z(1, 102.1044, floor=True)])
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 1})
    assert w["finish_first"] == {"target": 1, "dist": pytest.approx(2.1044)}
    all_sends_valid(r)


def test_a_fallen_zombie_within_finish_r_is_stomped_before_the_walk_toward_a_standing_one(tmp_path):
    """The approach walk (a PZA/1.4 build with the stomp: no stance) toward zombie 1 standing 3.5 tiles off goes after
    the stomp of zombie 2 fallen 4.5 tiles off (within FINISH_R)."""
    from .test_policies import CAPS_14
    r, sv = make(tmp_path, caps=CAPS_14)
    sv.FINISH_FAR = False   # named change, Plan 25 Task 8: P25-J's finish takes it first (`test_survive_v`)
    r.frame(zombies=[z(1, 103.5), z(2, 100.0, 204.5, floor=True)])
    a = tick(r, sv)
    assert (a.type, a.args) == ("stomp", {"targetId": 2}) and threat_why(tmp_path)["finish_first"]["target"] == 2


@pytest.mark.parametrize("case", ["chaser", "far", "no_stomp", "off"])
def test_no_stomp_first_by_a_chaser_beyond_finish_r_without_the_stomp_or_switched_off(tmp_path, case):
    """The refusals: a standing chaser within KEEP_R of the fallen one (the stomp's walk would end at it: the flee
    finish's own guard, P24-AV); the fallen one beyond FINISH_R; a build without the stomp; `FINISH_FIRST` off. The
    attack runs on (nothing sent)."""
    from .test_policies import CAPS_14
    caps = tuple(t for t in CAPS_14 if t != "stomp") if case == "no_stomp" else None
    r, sv = attack_running(tmp_path, [z(1, 101.74)], caps=caps)
    sv.FINISH_FIRST = case != "off"
    fallen = z(1, 102.1044, floor=True) if case != "far" else z(1, 105.2, floor=True)
    others = [z(2, 103.0, 200.5)] if case == "chaser" else []
    r.frame(zombies=[fallen] + others)
    assert tick(r, sv) is None and "finish_first" not in threat_why(tmp_path)


# ================================================================ P25-C: the endurance hold on the run
def strain_flee(tmp_path, endurance=0.7267035841941833):
    """F3's hold (#4415): the endurance first read under ENDURANCE_T, a zombie 5 tiles off (within DANGER_R, beyond
    KEEP_R): the `strain` flee at a run; its leg ends."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 105.0)], endurance=endurance)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and a.args["gait"] == "run" and w["flee"] == "strain" and "hold_walk" not in w
    r.answer()
    return r, sv


def test_under_the_endurance_hold_the_strain_flee_walks_with_no_zombie_within_danger_r(tmp_path):
    """F3's strain lines with the nearest 7.04 to 8.16 tiles off (lines 699-702, #4415): the flee's next leg goes at a
    walk, logged `hold_walk`; a zombie back within DANGER_R (line 703: 4.21 tiles) drops the walking leg and runs."""
    r, sv = strain_flee(tmp_path)
    r.frame(zombies=[z(1, 108.0)], endurance=0.7256643176078796)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and a.args["gait"] == "walk" and w["flee"] == "strain" and w["hold_walk"] is True
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    r.frame(zombies=[z(1, 104.21)], endurance=0.7222950458526611)
    a = tick(r, sv)
    assert a is not None and a.type == "steer" and a.args["gait"] == "run" and "hold_walk" not in threat_why(tmp_path)


def test_with_hold_run_off_the_strain_flee_runs(tmp_path):
    r, sv = strain_flee(tmp_path)
    sv.HOLD_RUN = False
    r.frame(zombies=[z(1, 108.0)], endurance=0.7256643176078796)
    assert tick(r, sv).args["gait"] == "run"


@functools.lru_cache(maxsize=1)
def f3_frames():
    """F3's frames from the first reading the endurance at ENDURANCE_T or under (game minute 648) through game
    minute 670, one each half second at most (the drivers' PLANNER_HZ 2): (gameMin, worldAge, endurance, wall
    seconds)."""
    from agent.base.replay_decisions import ARTIFACTS
    from agent.base.transport.files import FileTransport
    out = []
    for ln in FileTransport(os.path.join(ARTIFACTS, F3)).lines():
        if ln["kind"] != "frame" or not 648 <= ln.get("gameMin", 0) <= 670:
            continue
        e = (ln.get("stats") or {}).get("endurance")
        wall = ln["wallMs"] / 1000.0
        if e is not None and (out or e <= P.ENDURANCE_T) and (not out or wall - out[-1][3] >= 0.5):
            out.append((ln["gameMin"], ln["worldAge"], e, wall))
    return tuple(out)


@pytest.mark.parametrize("near_at", [None, 662])
def test_f3_s_hold_releases_by_game_minute_663_in_a_quiet_replay(tmp_path, near_at):
    """F3's endurance, frame by frame from game minute 648 (0.7267035841941833) on F3's own clocks, with its one
    zombie held 8 tiles off after the first frame (5 tiles: the `strain` flee): the hold stands through game minute
    662 and is released at 663 (HOLD_SPAN_MIN after the set, no zombie within DANGER_R for HOLD_QUIET_S), its
    endurance 0.7489942908287048, under ENDURANCE_RELEASE. With the zombie back within DANGER_R through game minute 662
    (`near_at`) the release waits HOLD_QUIET_S past its last frame there."""
    frames = f3_frames()
    assert frames[0][:3] == (648, 3.8128223419189453, 0.7267035841941833)
    r, sv = make(tmp_path)
    released = None
    for k, (gm, wa, e, wall) in enumerate(frames):
        r.t["now"] = wall
        x = 105.0 if k == 0 or gm == near_at else 108.0
        r.frame(zombies=[z(1, x)], endurance=e, game_min=gm, world_age=wa)
        n = len(r.acts.history)
        tick(r, sv)
        if len(r.acts.history) > n:
            r.answer()   # each leg ends at once: the next frame plans again
        if released is None and not sv.endurance_hold:
            released = (gm, e, wall)
    if near_at is None:
        assert released[:2] == (663, 0.7489942908287048)
        return
    last_near = max(w for g, _, _, w in frames if g == near_at)
    first_quiet = min(w for _, _, _, w in frames if w - last_near >= P.HOLD_QUIET_S)
    assert released is not None and released[2] == first_quiet and released[0] > 663


def test_after_a_timed_release_the_hold_sets_again_only_under_the_released_reading(tmp_path):
    """The release is a ratchet: set at game minute 600 (0.72, a zombie at 5 tiles), released at 616 at 0.74 (quiet
    since 600), it stays off at 0.745 and 0.74 and sets again at 0.73, a new span."""
    r, sv = make(tmp_path)
    t0 = r.clock()
    r.frame(zombies=[z(1, 105.0)], endurance=0.72, game_min=600.0)
    tick(r, sv)
    assert sv.endurance_hold
    r.t["now"] = t0 + P.HOLD_QUIET_S
    r.frame(zombies=[z(1, 108.0)], endurance=0.74, game_min=616.0)
    tick(r, sv)
    assert not sv.endurance_hold
    for e, held in ((0.745, False), (0.74, False), (0.73, True)):
        r.frame(zombies=[z(1, 108.0)], endurance=e, game_min=617.0)
        tick(r, sv)
        assert sv.endurance_hold is held, e


def test_the_release_above_endurance_release_stands_as_before(tmp_path):
    r, sv = strain_flee(tmp_path)
    r.frame(zombies=[z(1, 108.0)], endurance=0.81)
    tick(r, sv)
    assert not sv.endurance_hold and sv.spent is None


def test_a_shelter_step_sent_at_a_walk_runs_once_a_zombie_comes_within_danger_r(tmp_path):
    """Review-t3 finding 3 (every flee reason may take a shelter, and `gait` is the gait of every leg and walk): under the
    endurance hold with the nearest 6.5 tiles off the strain flee's shelter step (the enter) goes at a walk; with the
    zombie at 4.5 the running walk is dropped and sent again at a run (not only the steer leg)."""
    from .test_night import CLOSED, OPEN
    from .test_survive import shelter_world

    def frames(r, sv, zx, x=100.0):
        r.frame(x=x, y=201.5, zombies=[z(1, zx, 201.5)], endurance=0.7267035841941833)
        a = tick(r, sv)
        while a is not None and a.type == "scan":
            r.answer()
            r.frame(x=x, y=201.5, zombies=[z(1, zx, 201.5)], endurance=0.7267035841941833)
            a = tick(r, sv)
        return a
    r, sv = make(tmp_path)
    sv.DOORWAY = False
    shelter_world(r, CLOSED)
    assert frames(r, sv, 96.0).args["gait"] == "run"            # the flee starts at a run, a zombie at 4
    r.answer()
    assert frames(r, sv, 105.0, x=111.5).type == "interact"     # at the door; the zombie 6.5 off
    r.answer()
    shelter_world(r, OPEN)
    a = frames(r, sv, 105.0, x=111.5)
    assert (a.type, a.args["gait"]) == ("walkTo", "walk") and threat_why(tmp_path)["hold_walk"] is True
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    b = frames(r, sv, 107.0, x=111.5)
    assert b is not None and b is not a and (b.type, b.args["gait"]) == ("walkTo", "run")
    assert "hold_walk" not in threat_why(tmp_path)


def test_an_exit_walk_sent_at_a_walk_is_dropped_when_the_gait_is_the_run(tmp_path):
    """`Flee.keep_gait` reads the exit step's walk as the shelter step's: a running walkTo at a walk is dropped at the
    run; a walk already at the run is kept."""
    from agent.base import pza1
    from agent.base.planner.flee import Flee
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 105.0)])
    f = Flee(r.world, r.acts, r.clock)
    for gait, dropped in (("walk", True), ("run", False)):
        a = r.acts.send(pza1.WalkTo(101.5, 201.5, gait))
        f.last, f._exit_a, f._dropped, f.gait = a, a, None, P.FLEE_GAIT
        f.keep_gait()
        assert (f._dropped is a) == dropped, gait


# ================================================================ P25-D: the ride waits for the next send
def riding(r, sv):
    """A bandage riding (keepMoving) in flight: sent by the care and accepted, as E11's a111 and a114 rode the `many`
    flee's steers (#4408)."""
    from agent.base import pza1
    cmd = pza1.Bandage(10, part=7, keepMoving=True)
    a = r.acts.send(cmd)
    sv.care.sent(cmd, a)
    r.fake.act(a.aid, "accepted", "bandage")
    r.pump()
    assert sv.care.riding() is a
    return a


@pytest.mark.parametrize("zs", [A112, A116])
def test_e11_s_rides_a112_and_a116_keep_the_bandage_against_the_hold_s_shove(tmp_path, zs):
    """E11's a111 and a114 were superseded by the corner's shoves a112 and a116 (#4408), each sent with no attacker
    pinning the player beyond one (`me.attackers` 1 at a112, 0 at a116): with the ride in flight the wounded corner
    sends nothing (logged `ride_wait`, the ride's aid), the bandage the current action still."""
    r, sv = make(tmp_path)
    fr(r, zs, WOUND, NO_STIFF, health=70.0)
    ride = riding(r, sv)
    fr(r, zs, WOUND, NO_STIFF, health=70.0, attackers=1)
    assert tick(r, sv) is None
    w = threat_why(tmp_path)
    assert w["ride_wait"] == ride.aid and w["cornered"] == 1 and r.acts.history[-1] is ride
    assert not any(a.type == "shove" for a in r.acts.history)


def test_with_no_ride_or_ride_wait_off_the_corner_shoves(tmp_path):
    r, sv = make(tmp_path)
    fr(r, A112, WOUND, NO_STIFF, health=70.0)
    assert tick(r, sv).type == "shove"
    (tmp_path / "off").mkdir()
    r2, sv2 = make(tmp_path / "off")
    sv2.RIDE_WAIT = False
    fr(r2, A112, WOUND, NO_STIFF, health=70.0)
    riding(r2, sv2)
    fr(r2, A112, WOUND, NO_STIFF, health=70.0)
    assert tick(r2, sv2).type == "shove"


def test_under_attack_the_fight_s_own_send_still_pre_empts_the_ride(tmp_path):
    """The Fight's side alone (Survive's drag-down guard flees first at the same line): with `me.attackers` at
    DRAG_DOWN_N - 1 the held Fight's point-blank shove goes whatever rides; at one attacker it waits."""
    from .test_policies import Rig
    for attackers, want in ((P.DRAG_DOWN_N - 1, "shove"), (1, None)):
        d = tmp_path / str(attackers)
        d.mkdir()
        r = Rig(d)
        r.frame(zombies=[z(1, 100.49)], attackers=attackers)
        f = F.Fight(r.world, r.acts, r.clock, target=1)
        f.point_blank, f.spent = True, ("endurance",)
        from agent.base import pza1
        ride = r.acts.send(pza1.Bandage(10, part=7, keepMoving=True))
        r.fake.act(ride.aid, "accepted", "bandage")
        r.pump()
        f.ride = ride
        a = f.step()
        assert (a.type if a is not None else None) == want, attackers


def test_a_fight_that_swings_is_not_held_by_the_ride_within_reach(tmp_path):
    """P24-U as before: no hold and no pain, the target within reach: the attack goes (the ride's wait is the held
    Fight's only)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 101.5)], health=70.0)
    riding(r, sv)
    r.frame(zombies=[z(1, 101.5)], health=70.0)
    a = tick(r, sv)
    assert a is not None and a.type in ("attack", "aim") and "ride_wait" not in threat_why(tmp_path)


# ================================================================ P25-E: the stand's stalled walk
def stand_walk(r, sv):
    """`test_survive_p`'s shelter world: a `many` flee against three takes building 1's door for the doorway stand,
    its approach walk to (111.5, 201.5) sent and accepted (11.5 tiles off: E11's walk stood 11.44 from its door)."""
    from .test_night import CLOSED
    from .test_survive import group, shelter_world
    shelter_world(r, CLOSED)
    r.frame(x=100.0, y=201.5, zombies=group())
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 201.5, "gait": "run"}) and sv.flee.plan.get("stand") is True
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    return r.acts.history[-1]


def stall(r, sv, zs, seconds, me=(100.1, 201.5)):
    from .test_survive import group
    t = 0.0
    while t < seconds:
        r.advance(0.5)
        t += 0.5
        r.frame(x=me[0], y=me[1], zombies=zs if zs is not None else group())
        a = tick(r, sv)
        if a is not None:
            return a
    return None


def test_a_stand_s_stalled_walk_re_routes_once_then_drops_the_plan(tmp_path):
    """E11's walk toward building 2's door stood 2.101 s 11.44 tiles from it with a zombie at 5.36 and was dropped
    (#4409): the stand's walk that stalls (WALK_STALL_S with the group within DANGER_R) is re-sent once to the walk
    target's nearest `reachable_adjacent` square (logged `door_walk` {stall, end reroute}), the plan kept; that walk
    stalling too drops the plan (`door_walk` end drop, `doorway_left` stall) and the steer goes."""
    from .test_survive import group
    r, sv = make(tmp_path)
    walk = stand_walk(r, sv)
    a = stall(r, sv, group(0.1), 1.0)
    w = threat_why(tmp_path)
    assert a is not None and a.type == "walkTo" and (a.args["x"], a.args["y"]) == (110.5, 201.5)
    assert w["door_walk"]["end"] == "reroute" and w["door_walk"]["stall"] >= P.WALK_STALL_S
    assert sv.flee.plan is not None and sv.flee.plan.get("stand") is True and walk is not a
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    a = stall(r, sv, group(0.1), 1.0)
    w = threat_why(tmp_path)
    assert a is not None and a.type == "steer" and w["door_walk"]["end"] == "drop" and w["doorway_left"] == "stall"
    assert sv.flee.plan is None
    all_sends_valid(r)


def test_a_stand_s_stalled_walk_against_a_fence_re_routes_through_the_climb(tmp_path):
    """Review-t3 finding 4 (E11's stall, #4409: 11.44 tiles out against a fence, where a target one square over gives the
    pathfinder the same obstacle): the hoppable edge on the line to the walk's target (`World.hop_ahead`) is climbed
    (`door_walk` end reroute, `climb` the fence square), the plan kept, and the walk is sent again, at its own target,
    once the climb ends; that walk stalling too drops the plan."""
    from .test_policies import square
    from .test_survive import group
    r, sv = make(tmp_path)
    walk = stand_walk(r, sv)
    r.scan([square(101, 201, blockW=True, hopW=True)])
    a = stall(r, sv, group(0.1), 1.0)
    w = threat_why(tmp_path)
    assert a is not None and (a.type, a.args) == ("climb", {"x": 101, "y": 201}) and walk is not a
    assert w["door_walk"] == {"stall": pytest.approx(w["door_walk"]["stall"]), "end": "reroute", "climb": [101, 201]}
    assert w["climb"] == [101, 201] and sv.flee.plan.get("stand") is True and "via" not in sv.flee.plan
    all_sends_valid(r)
    r.answer()
    r.advance(0.5)
    r.frame(x=101.5, y=201.5, zombies=group(0.1))
    a = tick(r, sv)
    assert a is not None and (a.type, a.args["x"], a.args["y"]) == ("walkTo", 111.5, 201.5) and "via" not in threat_why(tmp_path)
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    a = stall(r, sv, group(0.1), 1.0, me=(101.6, 201.5))
    assert a is not None and a.type == "steer" and threat_why(tmp_path)["door_walk"]["end"] == "drop"


def test_a_stand_s_stalled_walk_with_no_fence_on_its_line_re_routes_to_the_adjacent_square(tmp_path):
    """The same stall with no hoppable edge on the line (or a build without `climb`): the `reachable_adjacent` square."""
    from .test_survive import group
    r, sv = make(tmp_path)
    stand_walk(r, sv)
    a = stall(r, sv, group(0.1), 1.0)
    assert a.type == "walkTo" and (a.args["x"], a.args["y"]) == (110.5, 201.5) and "climb" not in threat_why(tmp_path)["door_walk"]


def test_a_build_without_climb_re_routes_to_the_adjacent_square_even_against_a_fence(tmp_path):
    """The climb is sent only to a build announcing it: the fence on the line, the hello without `climb`: the
    `reachable_adjacent` square as before."""
    from agent.base import pza1
    from .test_policies import square
    from .test_survive import group
    r, sv = make(tmp_path, caps=tuple(t for t in pza1.ACTION_TYPES if t != "climb"))
    stand_walk(r, sv)
    r.scan([square(101, 201, blockW=True, hopW=True)])
    a = stall(r, sv, group(0.1), 1.0)
    assert a.type == "walkTo" and (a.args["x"], a.args["y"]) == (110.5, 201.5) and "climb" not in threat_why(tmp_path)["door_walk"]


def test_a_stand_s_walk_still_for_door_walk_s_stalls_with_no_zombie_within_danger_r(tmp_path):
    """With the group held 7 to 8 tiles off (the `many` episode holds them), the walk waited the Lua's stuck time
    (P23-AM 2's limit): still within STUCK_MOVE for DOOR_WALK_S it stalls, and re-routes."""
    from .test_survive import group
    r, sv = make(tmp_path)
    stand_walk(r, sv)
    me = (102.0, 201.5)
    a = stall(r, sv, group(-3.5, me), P.DOOR_WALK_S - 0.5, me=me)
    assert a is None and "door_walk" not in threat_why(tmp_path)
    a = stall(r, sv, group(-3.5, me), 1.0, me=me)
    assert a is not None and a.type == "walkTo" and threat_why(tmp_path)["door_walk"]["end"] == "reroute"


def test_a_plan_without_the_stand_or_door_walk_off_drops_at_its_stall_as_before(tmp_path):
    """P23-AM 2 unchanged for a shelter that is no stand (`DOORWAY` off) and with `DOOR_WALK` off."""
    from .test_survive import group
    for name in ("DOORWAY", "DOOR_WALK"):
        d = tmp_path / name
        d.mkdir()
        r, sv = make(d)
        setattr(sv, name, False)
        stand_walk_any(r, sv)
        a = stall(r, sv, group(0.1), 1.0)
        w = threat_why(d)
        assert a.type == "steer" and w["ended"] == "stalled" and "door_walk" not in w, name


def stand_walk_any(r, sv):
    from .test_night import CLOSED
    from .test_survive import group, shelter_world
    shelter_world(r, CLOSED)
    r.frame(x=100.0, y=201.5, zombies=group())
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 201.5, "gait": "run"})
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()


# ================================================================ P25-F: the fence wait
def fence_rig(tmp_path, zx, me=(100.5, 200.5), has_target=True, caps=None):
    """`test_survive_g.fenced`'s yard (a hoppable fence on the west edges of x 102), the player on its west side at
    `me`, one zombie east of the fence at (`zx`, 200.5) chasing (`has_target`)."""
    from .test_policies import zombie
    from .test_survive_g import fenced
    r, sv = make(tmp_path, caps=caps)
    r.scan(fenced())
    zs = [dict(zombie(1, zx, 200.5, me=me), onFloor=None, hasTarget=has_target)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    return r, sv


def fence_frame(r, zx, me=(100.5, 200.5), floor=False):
    from .test_policies import zombie
    r.frame(x=me[0], y=me[1], zombies=[dict(zombie(1, zx, 200.5, me=me), onFloor=True if floor else None,
                                            hasTarget=True)])


def test_a_chaser_across_the_fence_is_waited_for_in_the_stance_back_from_the_fence(tmp_path):
    """The guides' fence trick (§ 9 change 4): a chaser at 104.5 across the fence at x 102, the player 1.5 tiles back:
    the stance stands (an `aim` of (0, 0) facing it), logged `fence_wait` {target, fence, dist, leg}."""
    r, sv = fence_rig(tmp_path, 104.5)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "aim" and (a.args["vx"], a.args["vy"]) == (0.0, 0.0) and a.args["targetId"] == 1
    assert w["fence_wait"] == {"target": 1, "fence": [102.0, 200.5], "dist": 1.5, "leg": "stand"}
    all_sends_valid(r)


def test_at_the_fence_within_reach_it_is_neither_repositioned_for_nor_marked(tmp_path):
    """The chaser at the fence 2.0 tiles off (within FIGHT_REACH, its line blocked by the fence): no reposition walk,
    no unreachable mark (the rule before it: the walk round, then the mark); the stance stands."""
    r, sv = fence_rig(tmp_path, 104.5)
    tick(r, sv)
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    for _ in range(3):
        r.advance(0.5)
        fence_frame(r, 102.5)
        tick(r, sv)
    assert not any(a.type == "walkTo" for a in r.acts.history) and 1 not in sv.unreachable
    assert threat_why(tmp_path)["fence_wait"]["target"] == 1


def test_once_it_crosses_it_is_swung_at_and_once_fallen_stomped(tmp_path):
    """Across (101.6: the fence off the line) the swing from the held stance; fallen after the hop, the stomp (P24-AL's
    finish)."""
    r, sv = fence_rig(tmp_path, 104.5)
    tick(r, sv)
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    fence_frame(r, 101.6)
    a = tick(r, sv)
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and "fence_wait" not in threat_why(tmp_path)
    r.answer()
    fence_frame(r, 101.6, floor=True)
    assert tick(r, sv).type == "stomp"


def test_too_near_the_fence_it_steps_back_and_too_far_it_closes_to_the_band(tmp_path):
    """0.5 tiles from the fence (101.5): the backpedal west, away from the fence (`leg` back); 4.5 tiles back (97.5):
    the stance's step toward the fence (`leg` toward), never across it."""
    r, sv = fence_rig(tmp_path, 104.5, me=(101.5, 200.5))
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "aim" and a.args["vx"] < -0.99 and w["fence_wait"]["leg"] == "back"
    (tmp_path / "far").mkdir()
    r2, sv2 = fence_rig(tmp_path / "far", 104.5, me=(97.5, 200.5))
    a = tick(r2, sv2)
    w = threat_why(tmp_path / "far")
    assert a.type == "aim" and a.args["vx"] > 0.99 and w["fence_wait"]["leg"] == "toward"


@pytest.mark.parametrize("case", ["idle", "pza14", "off"])
def test_no_fence_wait_for_an_idle_zombie_on_a_build_without_the_stance_or_switched_off(tmp_path, case):
    from .test_policies import CAPS_14
    r, sv = fence_rig(tmp_path, 104.5, has_target=case != "idle", caps=CAPS_14 if case == "pza14" else None)
    sv.FENCE_WAIT = case != "off"
    tick(r, sv)
    assert "fence_wait" not in threat_why(tmp_path)


def test_past_stand_max_s_the_fence_wait_is_left_as_today(tmp_path):
    """The stand clock (P24-N): STAND_MAX_S with no fall of its health and the advance closes on it round the fence,
    the wait left (no `fence_wait`)."""
    r, sv = fence_rig(tmp_path, 104.5)
    tick(r, sv)
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    r.advance(P.STAND_MAX_S + 0.5)
    fence_frame(r, 104.5)
    tick(r, sv)
    assert "fence_wait" not in threat_why(tmp_path) and sv.fight.advance
