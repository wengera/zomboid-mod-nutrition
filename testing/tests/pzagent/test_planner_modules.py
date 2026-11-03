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


def test_the_window_filter_and_failure_leg_live_in_windows_and_goals_re_exports_neither():
    """Ruling P26-R: `usable_windows`, `note_window_end` and their WINDOW_DEAD and WINDOW_REPEAT moved from `goals` to
    `planner/windows.py`, imported at the top of `night`, `flee`, `goals` and `goal_policies` (one object each)."""
    from agent.base.planner import flee, goal_policies, night, windows
    assert night.usable_windows is goals.usable_windows is windows.usable_windows
    assert flee.note_window_end is goal_policies.note_window_end is windows.note_window_end
    assert not set(windows.__all__) & set(goals.__all__)


def test_the_flee_rules_are_its_switches_lower_cased_each_dropped_by_its_own_switch():
    """Ruling P26-R: `Threat._flee_rules` hands the Flee `flee.FLEE_RULES` with every switch on, as `_fight_rules`
    hands the Fight `fight.FIGHT_RULES`, and a switch off drops its own rule (the switch's name lower-cased) alone."""
    import types
    from agent.base.planner import flee
    names = [r.upper() for r in flee.FLEE_RULES]
    on = types.SimpleNamespace(**{n: getattr(survive.Survive, n) for n in names})
    assert all(getattr(on, n) is True for n in names)
    assert threat.Threat._flee_rules(on) == frozenset(flee.FLEE_RULES)
    for n in names:
        off = types.SimpleNamespace(**dict(vars(on), **{n: False}))
        assert threat.Threat._flee_rules(off) == frozenset(flee.FLEE_RULES) - {n.lower()}, n
