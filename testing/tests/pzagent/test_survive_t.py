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


