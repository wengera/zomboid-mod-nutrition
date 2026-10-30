"""Survival 14 (survival iteration 13; Plan 25 Task 3; E11, `e_day_11-20261030-113732`, rows #4402-#4412, and F3,
`f_goals_4-20261030-114742`, rows #4413-#4427). The fake mod over PZA/1.7.1.

- P25-A, the corner under a hold: after a shove whose result read no knock-down, one standing zombie within FIGHT_REACH
  takes the swing (#4370: a halved swing beats a seventh shove), two take a steer through the gap the shove opened;
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


def test_one_at_point_blank_after_a_missed_shove_takes_the_swing(tmp_path):
    """#4370: at armPain 20 the divider halves the swing, and a halved swing beats a seventh shove: alone within
    FIGHT_REACH, the shoved zombie takes the attack, the `wounded` rule's no-swing overridden; `corner` {kind swing}."""
    r, sv = shoved(tmp_path, [z(1, 100.49)])
    a = tick(r, sv)
    assert (a.type, a.args) == ("attack", {"targetId": 1})
    assert threat_why(tmp_path)["corner"] == {"kind": "swing", "shoved": 1, "n": 1}
    all_sends_valid(r)


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
    walk in to it), logged `finish_first` {target, dist}."""
    r, sv = attack_running(tmp_path, [z(1, 101.74)])
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


