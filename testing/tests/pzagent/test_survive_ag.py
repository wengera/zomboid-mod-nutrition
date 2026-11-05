"""Survival 26 (iteration 24, Plan 30 Task 3; the spec `2026-11-05-plan-30-the-intent-design.md` § 2 item 3): the six
rules of `survive.T14_SWITCHES`, each with its killing test, on E23's (`e_day_23-20261105-095110`), F14's
(`f_goals_15-20261105-092752`) and fabricated fixtures, each fixture's line named where it is the artifact's.

- P30-B (`GOAL_CONTINUE`, the goal runner): `test_goals.py`'s Plan 30 block; the switch here.
"""
from agent.base.planner import survive as S


def test_the_iteration_24_switches():
    """`survive.T14_SWITCHES`, each on `Survive` (or a class it derives) and on by default."""
    assert S.T14_SWITCHES == ("GOAL_CONTINUE",)
    assert all(getattr(S.Survive, n) is True for n in S.T14_SWITCHES)
