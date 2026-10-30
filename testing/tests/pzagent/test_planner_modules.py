"""The planner's modules after Plan 25 Task 2's pure move: every moved name still reached by its old path (the frozen
drivers and the tests import from there), the same object as at its new home, and the mixins wired."""
import importlib

import pytest

from agent.base.planner import doorway, fight, goals, policies, survive, threat

GOAL_MOVES = [(mod, name) for mod, names in goals._MOVED.items() for name in names]


@pytest.mark.parametrize("mod,name", GOAL_MOVES)
def test_every_moved_goal_name_is_reached_through_goals(mod, name):
    home = importlib.import_module("agent.base.planner." + mod)
    assert getattr(goals, name) is getattr(home, name)


def test_goals_star_import_and_an_unknown_name():
    ns = {}
    exec("from agent.base.planner.goals import *", ns)
    assert all(n in ns for n in goals.__all__)
    with pytest.raises(AttributeError):
        goals.NOT_A_NAME


def test_pull_from_and_standing_by_their_old_modules():
    from agent.base.planner import pull
    assert policies.pull_from is pull.pull_from
    assert doorway.standing is policies.standing
    with pytest.raises(AttributeError):
        policies.NOT_A_NAME


def test_the_frozen_drivers_import_lines_resolve():
    ns = {}
    exec("from agent.base.planner.goals import ScriptedSource\n"
         "from agent.base.planner.policies import Fight, item_id_ok\n", ns)
    assert ns["ScriptedSource"] is goals.ScriptedSource and ns["Fight"] is fight.Fight


def test_the_threat_constants_are_the_policies_table_s():
    for name in threat.__all__:
        if name != "Threat":
            assert getattr(threat, name) == getattr(policies, name), name


def test_the_mixins_are_wired():
    from agent.base.planner.care_yield import CareYield
    from agent.base.planner.engage import Engage
    from agent.base.planner.finish import FightFinish, ThreatFinish
    from agent.base.planner.hold import Hold
    from agent.base.planner.pull import FightPull, ThreatPull
    for mixin in (Hold, Engage, ThreatPull, CareYield, doorway.DoorwayStand, ThreatFinish):
        assert issubclass(survive.Survive, mixin)
    for mixin in (FightPull, FightFinish):
        assert issubclass(fight.Fight, mixin) and issubclass(doorway.Doorway, mixin)
