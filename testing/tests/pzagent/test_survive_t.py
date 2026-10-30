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


