"""The survival priority list (Plan 22 Task 10): threat -> need -> load -> night -> goal over the policies, with Plan 21b's
hysteresis (`testing/agent/policy.py`'s docstring, frozen) and the hold-radius fix, `need` consuming a held item by id,
the failed-action cooldown and the decision log; Plan 21's `test_policy.py` cases ported to the typed actions, end to
end on the fake mod. Plan 23 Task 13 (ruling P23-F): the forage and explore tests are rewritten in place as
goal tests (`planner/goals.py`'s scripted source: Stock for a need, LootBuilding for a building, ExploreToward)."""
import functools
import json
import math
import os
import shutil
import tempfile

import pytest

from agent.base.planner import Planner
from agent.base.planner import goals as G
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner.survive import Survive

from .test_policies import BAT, CRATE, FRIDGE, SHELF, Rig, all_sends_valid, behind_wall_n, grid, square, swing, zombie


def make(tmp_path):
    r = Rig(tmp_path)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    return r, sv


def tick(r, sv):
    return sv.tick(r.world, r.acts)


def decisions(tmp_path):
    with open(tmp_path / "decision.log", encoding="utf-8") as f:
        return [json.loads(ln) for ln in f]


def last(tmp_path):
    return decisions(tmp_path)[-1]


def threat_why(tmp_path):
    return last(tmp_path)["inputs"]["branches"]["threat"]


def inside(x, y, bid=1, **k):
    """A room square of building `bid` (a LootBuilding goal's container square)."""
    return square(x, y, room="kitchen", building=bid, **k)


# ================================================================ the list and its constants
def test_branch_order_puts_the_load_and_the_night_after_the_need_and_the_goal_last():
    assert S.BRANCHES == ("threat", "need", "load", "night", "goal")   # Task 13: the goal replaced forage, explore
    assert S.DANGER_R is P.DANGER_R
    assert (S.DANGER_R, S.DISENGAGE_R, S.THIRST_T, S.HUNGER_T) == (6.0, 10.0, 0.12, 0.15)   # [#0509], [#0508]
    assert G.STOCK_WANTS == ("water", "food", "bandage", "weapon") and set(G.STOCK_WANTS) == set(P.LOOT_WANTS)
    assert not hasattr(S, "STOCK_WANTS") and not hasattr(Survive, "_forage") and not hasattr(Survive, "_explore")
    assert (S.FLEE_HEALTH, S.FLEE_HEALTH_PAIR, S.REFIGHT_MARGIN, S.MAX_FIGHT) == (40.0, 60.0, 20.0, 2)
    assert S.FAILED_COOLDOWN_TICKS == 10


def test_survive_is_a_planner(tmp_path):
    r, sv = make(tmp_path)
    assert isinstance(sv, Planner) and sv.log_path == str(tmp_path / "decision.log")


# ================================================================ threat
def test_threat_fights_when_armed_and_at_most_two_within_danger_r(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 104.0, 200.0), zombie(2, 100.0, 205.0)])
    a = tick(r, sv)
    assert a is not None and r.cmd() == ("walkTo", {"x": 104.5, "y": 200.5, "gait": "run"})
    d = last(tmp_path)
    assert d["branch"] == "threat" and d["inputs"]["threats"] == 2 and d["inputs"]["armed"] is True
    assert d["action"] == {"type": "walkTo", "args": {"x": 104.5, "y": 200.5, "gait": "run"}} and d["sent"] is True


def test_threat_ignores_a_zombie_beyond_danger_r(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 106.5, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "threat"


@pytest.mark.parametrize("engage", [5.5, 6.0])           # 6.0: the `<= DANGER_R` boundary
def test_a_threat_engaged_at_six_tiles_holds_beyond_six_within_ten(tmp_path, engage):
    r, sv = make(tmp_path)
    r.scan([inside(101, 200, containers=[CRATE])])
    r.frame(zombies=[zombie(1, 100.0 + engage, 200.0)])
    tick(r, sv)
    assert r.cmd()[0] == "walkTo" and last(tmp_path)["branch"] == "threat"
    r.answer()
    r.frame(zombies=[zombie(1, 107.0, 200.0)])               # 7 tiles: beyond DANGER_R, inside DISENGAGE_R
    tick(r, sv)
    d = last(tmp_path)
    assert d["branch"] == "threat" and d["inputs"]["mode"] == "fight" and d["inputs"]["held"] == 1
    assert d["inputs"]["threats"] == 0 and r.cmd() == ("walkTo", {"x": 107.5, "y": 200.5, "gait": "run"})
    r.answer()
    r.frame(zombies=[zombie(1, 111.0, 200.0)])               # 11 tiles: disengaged
    tick(r, sv)
    assert last(tmp_path)["branch"] == "goal" and r.cmd() == ("interact", {"x": 101, "y": 200, "kind": "loot",
                                                                             "filter": "bandage", "maxWeight": 8.0})


def test_with_no_threat_running_a_zombie_at_seven_tiles_is_no_threat(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 107.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "threat"


def test_the_too_many_count_reads_the_hold_radius_during_a_fight(tmp_path):
    """P23-AG ruling 2 (E1's fight 2: engaged with one, fled only once four were within 6): a fight engaged at 5 tiles
    with two more closing from 8 and 9 turns to a flee before they are within 6."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 105.0, 200.0)])
    tick(r, sv)                                              # fight: a walk to it, left current
    assert last(tmp_path)["inputs"]["mode"] is None and r.cmd()[0] == "walkTo"
    r.frame(zombies=[zombie(1, 105.0, 200.0), zombie(2, 108.0, 200.0), zombie(3, 100.0, 209.0)])
    tick(r, sv)                                              # three held within 10, one within 6: too many
    d = last(tmp_path)
    assert d["branch"] == "threat" and d["inputs"]["held"] == 3 and d["inputs"]["threats"] == 1
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "many"


def test_with_no_fight_running_the_too_many_count_reads_danger_r(tmp_path):
    """Named change, ruling P24-A (b): zombie 2 stood at (108, 200), straight behind the fight's target: it moves to
    (100, 192), off the target's bearing, so the case reads the count alone (three listed within 12: no `many`)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 105.0, 200.0), zombie(2, 100.0, 192.0), zombie(3, 100.0, 209.0)])
    tick(r, sv)                                              # one within 6 and no fight running: a fight
    assert r.cmd()[0] == "walkTo" and threat_why(tmp_path)["fight"] is True
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.frame(zombies=[zombie(1, 103.0, 200.0), zombie(2, 104.0, 201.0), zombie(3, 100.0, 204.5)])
    tick(r2, sv2)                                            # three within 6: too many
    assert r2.cmd()[0] == "steer" and threat_why(tmp_path / "b")["flee"] == "many"


def test_unarmed_flees(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0)], weapon=None)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "unarmed"
    assert last(tmp_path)["inputs"]["armed"] is False


def test_low_health_flees(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0)], health=39.0)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "health"


@pytest.mark.parametrize("health, want", [(59.0, "steer"), (61.0, "walkTo")])
def test_two_threats_under_flee_health_pair_are_fled(tmp_path, health, want):
    """Named change, ruling P24-A (b): zombie 2 stood at (103, 201), 18 degrees off zombie 1's bearing and farther:
    behind it, so the fight's walk was refused; it moves to (100, 203), the pair rule read alone."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0), zombie(2, 100.0, 203.0)], health=health)
    tick(r, sv)
    assert r.cmd()[0] == want
    if want == "steer":
        assert threat_why(tmp_path)["flee"] == "pair"


def test_a_running_flee_turns_to_fight_only_with_one_threat_and_a_health_margin(tmp_path):
    """Survival 3 (ruling P23-AM 1) moved the hysteresis's tail beyond DANGER_R: a flee whose episode began `many`
    stays `many` while a held threat is within DANGER_R (two at 3 tiles, once `held`), so the pair retreats to 7
    tiles before the `held` rule and the refight margin are read (the refight walk 7.0 tiles, once 3.0)."""
    r, sv = make(tmp_path)
    three = [zombie(1, 103.0, 200.0), zombie(2, 103.0, 201.0), zombie(3, 104.0, 200.0)]
    r.frame(zombies=three, health=74.0)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "many"
    r.answer()
    r.event("zombie_dead", id=3)
    r.frame(zombies=three[:2], health=74.0)
    tick(r, sv)                                              # two threats at 3 tiles: the many episode holds
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "many"
    r.answer()
    far = [zombie(1, 107.0, 200.0), zombie(2, 107.0, 201.0)]
    r.frame(zombies=far, health=74.0)
    tick(r, sv)                                              # two held at 7 tiles at 74: the flee is held, re-aimed
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "held"
    r.answer()
    r.event("zombie_dead", id=2)
    r.frame(zombies=far[:1], health=59.0)
    tick(r, sv)                                              # one threat under FLEE_HEALTH + REFIGHT_MARGIN: held
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "held"
    r.answer()
    r.frame(zombies=far[:1], health=74.0)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 107.5, "y": 200.5, "gait": "run"})
    assert threat_why(tmp_path) == {"fight": True, "target": 1, "pinned": True, "dist": 7.0, "approach": False,
                                    "line": None, "reposition": None}


def test_a_running_fight_turns_to_flee_only_on_the_flee_conditions(tmp_path):
    """Named change, ruling P24-A (b): zombie 2 moves from (103, 201), behind zombie 1, to (100, 203)."""
    r, sv = make(tmp_path)
    two = [zombie(1, 103.0, 200.0), zombie(2, 100.0, 203.0)]
    r.frame(zombies=two, health=74.0)
    tick(r, sv)
    for n in (1, 2, 1):                                      # the run-1 flapping: threats 2, 1, 2, 1
        if n == 1:
            r.event("zombie_dead", id=2)
        r.frame(zombies=two[:n], health=74.0)
        tick(r, sv)
        assert last(tmp_path)["inputs"]["threats"] == n and last(tmp_path)["branch"] == "threat"
    assert [a.type for a in r.acts.history] == ["walkTo"]


@pytest.mark.parametrize("dist, flees", [(5.0, True), (2.74, True), (1.5, False)])   # 2.74: run 1's standoff
def test_a_fight_that_does_not_close_in_fight_max_s_flees(tmp_path, dist, flees):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 100.0 + dist, 200.0)])
    tick(r, sv)
    r.advance(20.0)
    r.frame(zombies=[zombie(1, 100.0 + dist, 200.0)])
    assert tick(r, sv) is None                               # at FIGHT_MAX_S exactly: not yet
    r.advance(1.0)
    r.frame(zombies=[zombie(1, 100.0 + dist, 200.0)])
    tick(r, sv)
    assert (r.cmd()[0] == "steer") is flees
    if flees:
        d = last(tmp_path)
        assert threat_why(tmp_path)["flee"] == "stalled" and d["inputs"]["fight_s"] == 21.0


def test_a_stalled_fights_flee_is_held_until_the_zombie_closes(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 105.0, 200.0)])
    tick(r, sv)
    r.advance(21.0)
    r.frame(zombies=[zombie(1, 105.0, 200.0)])
    tick(r, sv)
    assert r.cmd()[0] == "steer"
    r.answer()
    r.frame(zombies=[zombie(1, 105.0, 200.0)])
    tick(r, sv)                                              # one threat at full health, yet the stall's flee holds
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "stalled"
    r.answer()
    r.frame(zombies=[zombie(1, 101.5, 200.0)])
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1}) and threat_why(tmp_path)["fight"] is True
    assert "flee" not in threat_why(tmp_path)


# I2: a target whose three started swings took no health is unreachable for UNREACHABLE_S; the threat branch flees
# rather than attack it again (run 1's 103 attacks on zombie 32404).
def test_an_unreachable_only_threat_is_fled_never_attacked_again(tmp_path):
    r, sv = make(tmp_path)
    z = lambda: [dict(zombie(1, 101.0, 200.0), health=1.167)]
    r.frame(zombies=z())
    for _ in range(3):
        tick(r, sv)
        assert r.cmd() == ("attack", {"targetId": 1})
        r.answer({"state": "done", "result": swing(True)})
        r.frame(zombies=z())
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "unreachable"
    for i in range(3):                                       # each leg moves (survival 2 fix round 1, I3: a leg that
        r.answer()                                           # did not move would corner the marked zombie at 1.0)
        r.advance(1.0)
        x = 100.0 - (i + 1)
        r.frame(x=x, zombies=[dict(zombie(1, x + 1.0, 200.0, me=(x, 200.0)), health=1.167)])
        tick(r, sv)
        assert r.cmd()[0] == "steer"
    assert [a.type for a in r.acts.history].count("attack") == 3


def test_the_log_line_carries_mode_and_fight_s(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0)])
    tick(r, sv)
    assert (last(tmp_path)["inputs"]["mode"], last(tmp_path)["inputs"]["fight_s"]) == (None, None)
    r.advance(7.5)
    r.frame(zombies=[zombie(1, 103.0, 200.0)])
    tick(r, sv)
    assert (last(tmp_path)["inputs"]["mode"], last(tmp_path)["inputs"]["fight_s"]) == ("fight", 7.5)
    r.frame(zombies=[zombie(1, 103.0, 200.0)], health=30.0)
    tick(r, sv)
    r.frame(zombies=[zombie(1, 103.0, 200.0)], health=30.0)
    tick(r, sv)
    assert (last(tmp_path)["inputs"]["mode"], last(tmp_path)["inputs"]["fight_s"]) == ("flee", None)


# ================================================================ one action at a time
def test_a_running_action_is_not_re_sent_and_a_higher_branch_pre_empts_it(tmp_path):
    r, sv = make(tmp_path)
    r.scan([inside(101, 200, containers=[CRATE])])
    r.frame()
    tick(r, sv)
    assert r.cmd()[0] == "interact"
    r.frame()
    assert tick(r, sv) is None                               # the goal's loot is current: held, nothing sent
    d = last(tmp_path)
    assert d["branch"] == "goal" and d["sent"] is False and d["action"] is None
    assert d["goal"] == {"type": "LootBuilding", "args": {"building": 1}, "state": "running", "source": "scripted"}
    r.frame(zombies=[zombie(1, 101.5, 200.0)])
    assert tick(r, sv) is not None and r.cmd() == ("attack", {"targetId": 1})   # the threat pre-empts the loot
    assert len(r.acts.history) == 2


# ================================================================ need
def test_need_consumes_a_held_water_bottle_by_id_when_thirsty_then_food(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=702, fullType="Base.Apple", weight=0.2)
    r.event("item_added", itemId=701, fullType="Base.WaterBottle", weight=1.0)
    r.frame(thirst=0.6, hunger=0.6)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 701}) and last(tmp_path)["branch"] == "need"
    r.answer({"state": "done", "result": {"itemId": 701}})
    r.event("item_removed", itemId=701, fullType="Base.WaterBottle")
    r.frame(thirst=0.2, hunger=0.6)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 702})
    all_sends_valid(r)


def test_last_branch_is_the_branch_of_the_last_decision_line(tmp_path):
    r, sv = make(tmp_path)
    assert sv.last_branch is None
    r.event("item_added", itemId=701, fullType="Base.WaterBottle", weight=1.0)
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    r.frame(thirst=0.6, level=3)
    tick(r, sv)
    assert sv.last_branch == "need" == last(tmp_path)["branch"]
    r.answer({"state": "done", "result": {"itemId": 701}})
    r.event("item_removed", itemId=701, fullType="Base.WaterBottle")
    r.frame(thirst=0.05, level=3)
    tick(r, sv)
    assert sv.last_branch == "load" == last(tmp_path)["branch"]


def test_a_shelter_goal_failing_no_plan_shuns_the_building_in_the_nights_store(tmp_path):
    class Once:
        NAME = "once"

        def __init__(self):
            self.n = 0

        def propose(self, view):
            self.n += 1
            return G.Shelter(7) if self.n == 1 else None
    r = Rig(tmp_path)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Once())
    assert sv.goals.kit.shunned is sv.night.shunned
    r.frame(game_min=500.0)
    tick(r, sv)
    assert sv.goals.history[-1]["type"] == "Shelter" and sv.goals.history[-1]["state"] == "failed"
    assert sv.goals.history[-1]["reason"] == "no plan"
    assert sv.night.shunned == {7: 500.0} and 7 in sv.night.shunned_now()


def test_need_holds_its_running_consume_before_reading_the_thresholds(tmp_path):
    r, sv = make(tmp_path)
    r.scan([inside(101, 200, containers=[CRATE])])
    r.event("item_added", itemId=701, fullType="Base.WaterBottle", weight=1.0)
    r.frame(thirst=0.6)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 701})
    r.frame(thirst=0.4)                                      # the drink already reads, the consume still current
    assert tick(r, sv) is None
    d = last(tmp_path)
    assert d["branch"] == "need" and d["sent"] is False and d["action"] is None
    assert [a.type for a in r.acts.history] == ["consume"]
    r.answer({"state": "done", "result": {"itemId": 701}})
    r.frame(thirst=0.1)
    tick(r, sv)
    assert r.cmd()[0] == "interact" and last(tmp_path)["branch"] == "goal"


def test_the_threat_inputs_reach_the_log(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0), zombie(2, 103.0, 202.0)], weapon=None)
    tick(r, sv)
    why = threat_why(tmp_path)
    assert why["flee"] == "unarmed" and why["centroid"] == [103.0, 201.0] and why["nearest"] == 3.0


def test_need_marks_food_and_the_goal_stocks_it(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(101, 200, containers=[CRATE]), square(103, 200, containers=[FRIDGE])])
    r.frame(hunger=0.6)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 103, "y": 200, "kind": "loot", "filter": "food", "maxWeight": 8.0})
    d = last(tmp_path)
    assert d["branch"] == "goal" and d["inputs"]["need"] == "food" and d["goal"]["type"] == "Stock"
    assert d["goal"]["args"] == {"kind": "food"} and sv.need_marks == {"food": 1000.0}


def test_the_goal_never_loots_at_load_level_three(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(101, 200, containers=[CRATE])])
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    r.frame(level=3)
    tick(r, sv)
    assert r.cmd() == ("drop", {"itemId": 602}) and last(tmp_path)["branch"] == "load"   # Task 12: was "forage"
    assert last(tmp_path)["inputs"]["load"] == 3
    assert last(tmp_path)["inputs"]["branches"]["load"] == {"level": 3, "drop": 602}


# ================================================================ Plan 23 Task 12: the load branch, the night's inputs
@pytest.mark.parametrize("level, want", [(2, None), (3, "drop"), (4, "drop")])
def test_the_load_branch_drops_one_spare_item_at_drop_at_or_above(tmp_path, level, want):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    r.frame(level=level)
    tick(r, sv)
    assert (last(tmp_path)["branch"] == "load") is (want is not None)
    if want:
        assert r.cmd() == ("drop", {"itemId": 602})


def test_the_load_branch_holds_on_its_drop_then_drops_the_next_and_passes_with_nothing_spare(tmp_path):
    r, sv = make(tmp_path)
    r.scan([inside(101, 200, containers=[CRATE])])
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    r.event("item_added", itemId=603, fullType="Base.Nails", weight=0.5)
    r.frame(level=3)
    tick(r, sv)
    assert r.cmd() == ("drop", {"itemId": 602})
    r.frame(level=3)
    assert tick(r, sv) is None and last(tmp_path)["branch"] == "load"   # its drop is current: held
    r.answer()
    r.event("item_removed", itemId=602, fullType="Base.Plank")
    r.frame(level=3)
    tick(r, sv)
    assert r.cmd() == ("drop", {"itemId": 603})
    r.answer()
    r.event("item_removed", itemId=603, fullType="Base.Nails")
    r.frame(level=3)
    tick(r, sv)                                              # nothing spare: load passes, no loot goal at 3
    d = last(tmp_path)
    assert d["branch"] == "goal" and d["inputs"]["branches"]["load"] == {"level": 3, "drop": None}
    assert d["goal"]["type"] == "ExploreToward" and r.cmd()[0] == "scan"
    assert "interact" not in [a.type for a in r.acts.history]


def test_the_load_branch_drops_before_the_night_sleeps(tmp_path):
    from .test_night import house
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    r.frame(x=111.5, y=201.5, fatigue=0.65, level=3)
    tick(r, sv)
    assert r.cmd() == ("drop", {"itemId": 602}) and last(tmp_path)["branch"] == "load"
    r.answer()
    r.event("item_removed", itemId=602, fullType="Base.Plank")
    r.frame(x=111.5, y=201.5, fatigue=0.65, level=2)
    tick(r, sv)
    assert r.cmd() == ("sleep", {}) and last(tmp_path)["branch"] == "night"


def test_the_log_inputs_carry_the_hour_and_fatigue(tmp_path):
    r, sv = make(tmp_path)
    r.frame(hour=21.5, fatigue=0.25)
    tick(r, sv)
    d = last(tmp_path)
    assert (d["inputs"]["hour"], d["inputs"]["fatigue"]) == (21.5, 0.25)
    assert d["inputs"]["branches"]["night"] == {"wants": False}


# ================================================================ the cooldown
def test_a_failed_action_cools_its_branch_for_ten_planner_ticks(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=701, fullType="Base.WaterBottle", weight=1.0)
    r.frame(thirst=0.6)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 701})
    r.answer({"state": "failed", "reason": "interrupted"})   # not "not valid", which marks a water bottle empty
    for i in range(S.FAILED_COOLDOWN_TICKS):
        r.frame(thirst=0.6)
        a = tick(r, sv)
        d = last(tmp_path)
        assert d["branch"] != "need" and d["inputs"]["cooled"] == {"type": "consume", "args": {"itemId": 701}}, i
        if a is not None:
            r.answer()                                       # the ExploreToward goal's scan
    r.frame(thirst=0.6)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 701}) and last(tmp_path)["inputs"]["cooled"] is None
    assert [a.type for a in r.acts.history].count("consume") == 2


def test_a_cooled_action_passes_over_to_the_next_branch(tmp_path):
    r, sv = make(tmp_path)
    r.scan([inside(102, 200, containers=[CRATE])])
    r.event("item_added", itemId=701, fullType="Base.WaterBottle", weight=1.0)
    r.frame(thirst=0.6)
    tick(r, sv)
    r.answer({"state": "failed", "reason": "interrupted"})
    r.frame(thirst=0.6)
    tick(r, sv)
    assert r.cmd()[0] == "interact" and last(tmp_path)["branch"] == "goal"


def test_a_superseded_action_is_not_a_failure(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=701, fullType="Base.WaterBottle", weight=1.0)
    r.frame(thirst=0.6)
    tick(r, sv)
    r.answer({"state": "failed", "reason": "superseded"})
    r.frame(thirst=0.6)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 701}) and last(tmp_path)["inputs"]["cooled"] is None


@pytest.mark.parametrize("weapon, want", [(BAT, "attack"), (None, "steer")])
def test_a_failed_fight_action_never_passes_the_threat_branch_over(tmp_path, weapon, want):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 101.0, 200.0)])
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1})
    r.answer({"state": "failed", "reason": "no target"})
    r.frame(zombies=[zombie(1, 101.0, 200.0)], weapon=weapon)
    tick(r, sv)
    assert r.cmd()[0] == want and last(tmp_path)["branch"] == "threat"


# ================================================================ the decision log
def scenario(tmp_path):
    """A short session through every branch on the injected clock; returns the decision log's bytes."""
    tmp_path.mkdir()
    r, sv = make(tmp_path)
    r.event("item_added", itemId=701, fullType="Base.WaterBottle", weight=1.0)

    def step(i, **k):
        r.advance(0.25)
        r.frame(game_min=480.0 + i, **k)
        if tick(r, sv) is not None:
            r.answer({"state": "done", "result": swing(True)} if r.cmd()[0] == "attack" else "done")

    step(0)                                                  # goal ExploreToward: scan the place
    r.scan([inside(x, y, containers=[CRATE] if (x, y) == (101, 201) else []) for x in range(99, 102)
            for y in range(199, 202)])
    step(1)                                                  # goal LootBuilding: loot the crate
    step(2, thirst=0.6)                                      # need: drink the bottle
    step(3, zombies=[zombie(1, 103.0, 200.0)])               # threat: walk to it
    step(4, zombies=[zombie(1, 101.0, 200.0)])               # threat: attack
    step(5, zombies=[zombie(1, 101.0, 200.0)], health=30.0)  # threat: flee
    r.event("zombie_dead", id=1)
    step(6, level=3)                                         # nothing to drop, the loot ended: a goal
    step(7)
    all_sends_valid(r)
    return (tmp_path / "decision.log").read_bytes()


def test_the_decision_log_is_byte_stable_under_an_injected_clock(tmp_path):
    a = scenario(tmp_path / "a")
    b = scenario(tmp_path / "b")
    assert a == b and a.endswith(b"\n") and b"\r" not in a
    lines = a.decode("utf-8").splitlines()
    assert len(lines) == 8
    for i, ln in enumerate(lines):
        d = json.loads(ln)
        assert ln == json.dumps(d, sort_keys=True)
        assert set(d) == {"wall", "gameMin", "branch", "inputs", "action", "sent", "goal"}
        assert d["wall"] == 1000.0 + 0.25 * (i + 1) and d["gameMin"] == 480.0 + i
    branches = [json.loads(ln)["branch"] for ln in lines]
    assert {"threat", "need", "goal"} <= set(branches)
    goals = [json.loads(ln)["goal"] for ln in lines]
    assert [g["type"] for g in goals[:2]] == ["ExploreToward", "LootBuilding"]
    assert all(g is None or set(g) == {"type", "args", "state", "source"} for g in goals)


# P9 (the wave's Minor 8): a zombie whose id read nil is a danger but never a fight target.
def test_a_lone_nil_id_zombie_is_fled_never_held(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(None, 103.0, 200.0)])
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "unreachable"
    assert last(tmp_path)["inputs"]["threats"] == 1


def test_a_nil_id_zombie_beside_an_int_id_one_leaves_the_int_id_the_target(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(None, 101.0, 200.0), zombie(5, 101.5, 200.0)])
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 5}) and threat_why(tmp_path)["fight"] is True


# ================================================================ Plan 23 Task 10: the line, the pair rule on wounds, the flee's drop
def test_a_target_with_no_clear_neighbour_is_fled_unreachable(tmp_path):
    r, sv = make(tmp_path)
    walls = {(x, y): {"solid": True} for x in (99, 100, 101) for y in (198, 199, 200) if (x, y) not in
             ((100, 199), (100, 200))}
    r.scan(behind_wall_n(walls))
    r.frame(zombies=[zombie(7, 100.5, 199.5)])
    assert tick(r, sv) is None                               # the Fight reads the line, finds no square, marks 7
    assert threat_why(tmp_path)["line"] is False and sv.unreachable == {7: r.clock() + P.UNREACHABLE_S}
    r.frame(zombies=[zombie(7, 100.5, 199.5)])
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "unreachable"
    assert [a.type for a in r.acts.history] == ["steer"]


@pytest.mark.parametrize("wound", ["bleeding", "scratched", "bitten"])
def test_two_threats_with_a_wound_are_fled_pair_above_flee_health_pair(tmp_path, wound):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0), zombie(2, 103.0, 201.0)], health=90.0, wounds={wound: 1})
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "pair"


def test_one_threat_with_a_wound_is_still_fought(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0)], health=90.0, wounds={"bleeding": 1})
    tick(r, sv)
    assert r.cmd()[0] == "walkTo" and threat_why(tmp_path)["fight"] is True


# Plan 22 run 2's last flee was pinned at load level 4: a flee at DROP_AT or above drops the spare item first.
def test_a_flee_at_load_level_three_drops_one_spare_item_first_then_steers(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    r.event("item_added", itemId=603, fullType="Base.Nails", weight=0.5)
    r.frame(zombies=[zombie(1, 103.0, 200.0)], weapon=None, level=3)
    tick(r, sv)
    assert r.cmd() == ("drop", {"itemId": 602}) and last(tmp_path)["branch"] == "threat"
    assert threat_why(tmp_path)["flee"] == "unarmed" and threat_why(tmp_path)["flee_drop"] == 602
    r.answer()
    r.event("item_removed", itemId=602, fullType="Base.Plank")
    r.frame(zombies=[zombie(1, 103.0, 200.0)], weapon=None, level=3)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and "flee_drop" not in threat_why(tmp_path)
    r.answer()
    r.frame(zombies=[zombie(1, 103.0, 200.0)], weapon=None, level=3)
    tick(r, sv)
    assert [a.type for a in r.acts.history] == ["drop", "steer", "steer"]   # one drop per flee episode


def test_a_flee_drop_waits_on_its_drop_and_a_new_flee_drops_again(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    r.event("item_added", itemId=603, fullType="Base.Nails", weight=0.5)
    r.frame(zombies=[zombie(1, 103.0, 200.0)], weapon=None, level=4)
    tick(r, sv)
    assert r.cmd() == ("drop", {"itemId": 602})
    r.frame(zombies=[zombie(1, 103.0, 200.0)], weapon=None, level=4)
    assert tick(r, sv) is None                               # the drop is current: the flee holds on it
    r.answer()
    r.event("item_removed", itemId=602, fullType="Base.Plank")
    r.event("zombie_dead", id=1)
    r.frame(level=2, weapon=None)                            # the threat gone: the flee episode ends at no threat
    tick(r, sv)
    assert sv.mode is None and sv.flee is None and sv.flee_dropped is False
    assert last(tmp_path)["branch"] != "threat"
    r.frame(zombies=[zombie(2, 103.0, 200.0)], weapon=None, level=4)
    tick(r, sv)
    assert r.cmd() == ("drop", {"itemId": 603})              # a new flee episode: one drop again
    between = [a.type for a in r.acts.history][1:-1]
    assert not {"steer", "walkTo", "attack"} & set(between), between   # no threat command between the two drops


def test_a_flee_under_drop_at_never_drops(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    r.frame(zombies=[zombie(1, 103.0, 200.0)], weapon=None, level=2)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and "flee_drop" not in threat_why(tmp_path)


# ================================================================ Plan 23 Task 11: the first moodle, the empties, the loot's want and cap
WATER = {"type": "counter", "n": 1, "items": ["Base.WaterBottle"]}
TOOLS = {"type": "crate", "n": 1, "items": ["Base.BaseballBat"]}


def held(r, *items):
    for iid, ft in items:
        r.event("item_added", itemId=iid, fullType=ft, weight=0.5)


@pytest.mark.parametrize("thirst, hunger, want", [(0.13, 0.1, 703), (0.11, 0.1, None), (0.1, 0.16, 701),
                                                  (0.1, 0.14, None), (0.13, 0.16, 703)])
def test_the_needs_fire_at_the_first_moodle_on_the_least_id_of_the_use(tmp_path, thirst, hunger, want):
    r, sv = make(tmp_path)
    held(r, (704, "Base.Apple"), (705, "Base.WaterBottle"), (701, "Base.Apple"), (703, "Base.WaterBottle"))
    r.frame(thirst=thirst, hunger=hunger)
    tick(r, sv)
    if want is None:
        assert last(tmp_path)["branch"] != "need" and "consume" not in [a.type for a in r.acts.history]
    else:
        assert r.cmd() == ("consume", {"itemId": want}) and last(tmp_path)["branch"] == "need"


def test_a_water_consume_failed_not_valid_marks_it_empty_and_the_next_tick_takes_the_other(tmp_path):
    r, sv = make(tmp_path)
    held(r, (705, "Base.WaterBottle"), (703, "Base.WaterBottle"))
    r.frame(thirst=0.3)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 703})
    r.answer({"state": "failed", "reason": "not valid"})
    r.frame(thirst=0.3)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 705}) and r.world.empty_ids == {703}
    assert r.world.by_use()["water"] == [705] and 703 in r.world.by_use()["other"]
    assert last(tmp_path)["inputs"]["consume_refused"] is None


@pytest.mark.parametrize("reason", ["interrupted", "superseded", "no target"])
def test_a_water_consume_failed_otherwise_is_not_marked_empty(tmp_path, reason):
    r, sv = make(tmp_path)
    held(r, (703, "Base.WaterBottle"))
    r.frame(thirst=0.3)
    tick(r, sv)
    r.answer({"state": "failed", "reason": reason})
    r.frame(thirst=0.3)
    tick(r, sv)
    assert r.world.empty_ids == set()


def test_a_food_consume_failed_not_valid_is_refused_never_marked_empty(tmp_path):
    """Fix wave P (I-4, P23-AD): a refused food is remembered in `World.refused` (never `empty_ids`), so `by_use` drops
    it from `food` and the need never retries it; with no other food held the need marks `food`."""
    r, sv = make(tmp_path)
    held(r, (701, "Base.Apple"))
    r.frame(hunger=0.3)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 701})
    r.answer({"state": "failed", "reason": "not valid"})
    r.frame(hunger=0.3)
    tick(r, sv)
    d = last(tmp_path)
    assert r.world.empty_ids == set() and r.world.refused == {701: 480.0} and r.world.by_use()["food"] == []
    assert d["inputs"]["consume_refused"] == 701 and d["inputs"]["need"] == "food" and d["inputs"]["cooled"] is None
    r.frame(hunger=0.3)
    tick(r, sv)
    assert last(tmp_path)["inputs"]["consume_refused"] is None   # logged on the tick that read the end only
    assert [a.type for a in r.acts.history].count("consume") == 1


@pytest.mark.parametrize("load_max, cap", [(8.0, 8.0), (None, 0.0)])
def test_the_goals_loot_carries_the_cap_and_logs_it(tmp_path, load_max, cap):
    r, sv = make(tmp_path)
    r.scan([square(103, 200, containers=[FRIDGE])])
    r.frame(hunger=0.3, load_max=load_max)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 103, "y": 200, "kind": "loot", "filter": "food", "maxWeight": cap})
    assert last(tmp_path)["inputs"]["branches"]["goal"]["cap"] == cap


def test_with_no_need_loot_building_takes_the_stocks_wants_in_order_water_food_bandage_weapon(tmp_path):
    r, sv = make(tmp_path)
    r.scan([inside(101, 200, containers=[TOOLS]), inside(102, 200, containers=[CRATE]),
            inside(103, 200, containers=[FRIDGE]), inside(106, 200, containers=[WATER])])
    filters = []
    for _ in range(4):
        r.frame()
        tick(r, sv)
        filters.append((r.cmd()[1]["filter"], r.cmd()[1]["x"]))
        r.answer()
    assert filters == [("water", 106), ("food", 103), ("bandage", 102), ("weapon", 101)]
    r.frame()
    tick(r, sv)                                              # the building is looted: the goal ends done
    assert sv.goals.history[-1]["type"] == "LootBuilding" and sv.goals.history[-1]["state"] == "done"
    r.frame()
    tick(r, sv)
    assert last(tmp_path)["goal"]["type"] == "ExploreToward" and r.cmd()[0] == "scan"


def test_with_no_need_an_other_only_container_is_never_looted(tmp_path):
    r, sv = make(tmp_path)
    r.scan([inside(101, 200, containers=[SHELF])])
    r.frame()
    tick(r, sv)
    assert last(tmp_path)["goal"]["type"] == "ExploreToward" and "interact" not in [a.type for a in r.acts.history]
    assert last(tmp_path)["inputs"]["branches"]["goal"]["proposed"] == "ExploreToward"


def test_a_need_mark_stocks_its_use_even_when_another_use_is_nearer(tmp_path):
    r, sv = make(tmp_path)
    r.scan([inside(101, 200, containers=[CRATE]), square(106, 200, containers=[WATER])])
    r.frame(thirst=0.3)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 106, "y": 200, "kind": "loot", "filter": "water", "maxWeight": 8.0})


def test_twenty_ticks_of_a_looting_world_never_send_all(tmp_path):
    r, sv = make(tmp_path)
    at = {(101, 200): {"containers": [SHELF]}, (102, 200): {"containers": [CRATE]},
          (103, 201): {"containers": [FRIDGE, SHELF]}, (104, 199): {"containers": [WATER]},
          (105, 200): {"containers": [TOOLS]}, (98, 202): {"containers": [dict(FRIDGE, type="counter")]},
          (97, 198): {"containers": [dict(WATER, type="sink")]}}
    r.scan([dict(s, room="kitchen", building=1) for s in grid(95, 106, 196, 204, at)])
    for i in range(20):
        r.frame(thirst=0.3 if i % 3 == 0 else 0.1, hunger=0.3 if i % 3 == 1 else 0.1, game_min=480.0 + i)
        if tick(r, sv) is not None:
            r.answer()
    loots = [a.args for a in r.acts.history if a.type == "interact"]
    assert len(loots) >= 5
    assert all(a["filter"] in ("food", "water", "weapon", "bandage") for a in loots), loots
    assert all(a["maxWeight"] == 8.0 for a in loots)
    for d in decisions(tmp_path):
        assert d["inputs"]["branches"].get("goal", {}).get("want") != "all"
    all_sends_valid(r)


# Task 10's review (M3): the Fight's stall clock follows the pinned target, so the stall guard reads its distance.
def test_the_stall_reads_the_pinned_targets_distance_not_the_nearest_zombies(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 105.0, 200.0)])
    tick(r, sv)
    assert sv.fight.target == 1 and r.cmd() == ("walkTo", {"x": 105.5, "y": 200.5, "gait": "run"})
    both = lambda: [zombie(1, 105.0, 200.0), zombie(2, 101.5, 200.0)]   # an unpinned zombie within reach
    r.frame(zombies=both())
    assert tick(r, sv) is None and sv.fight.target == 1
    assert sv.fight.target_dist() == 5.0
    r.advance(21.0)
    r.frame(zombies=both())
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "stalled"


# Task 11 fix 1 (review-t11 I1): a counter looted for water on a thirst is looted again for food on a hunger.
def test_a_counter_looted_for_water_is_looted_again_for_food(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(102, 200, containers=[{"type": "counter", "n": 2, "items": ["Base.WaterBottle", "Base.Apple"]}])])
    r.frame(thirst=0.3)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 102, "y": 200, "kind": "loot", "filter": "water", "maxWeight": 8.0})
    r.answer({"state": "done", "result": {"moved": 1, "skipped": 0}})
    r.event("item_added", itemId=801, fullType="Base.WaterBottle", weight=1.0)   # the Stock(water) ends stocked
    r.frame(hunger=0.3)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 102, "y": 200, "kind": "loot", "filter": "food", "maxWeight": 8.0})
    assert [h["args"] for h in sv.goals.history] == [{"kind": "water"}] and sv.goals.current.args() == {"kind": "food"}


# ================================================================ fix wave P
def test_a_refused_food_is_passed_for_the_next_food_held(tmp_path):
    r, sv = make(tmp_path)
    held(r, (701, "Base.Apple"), (702, "Base.Apple"))
    r.frame(hunger=0.3)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 701})
    r.answer({"state": "failed", "reason": "not valid"})
    r.frame(hunger=0.3)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 702}) and last(tmp_path)["branch"] == "need"


def test_a_sealed_can_is_never_eaten_and_the_need_marks_food(tmp_path):
    """I-4: `Base.TinnedBeans` is `CantEat` in the dataset, so `other`: hungry, holding only it, the need marks food."""
    r, sv = make(tmp_path)
    held(r, (701, "Base.TinnedBeans"))
    r.frame(hunger=0.3)
    tick(r, sv)
    assert "consume" not in [a.type for a in r.acts.history] and last(tmp_path)["inputs"]["need"] == "food"


def test_the_need_eats_the_most_perishable_food_first(tmp_path):
    """I-4, the spec's "smallest spoil risk": the least `days_fresh` (Bread 3 before Apple 5), ties by least id, a
    food with no `days_fresh` (Crisps) last."""
    r, sv = make(tmp_path)
    held(r, (701, "Base.Crisps"), (702, "Base.Apple"), (703, "Base.Bread"), (704, "Base.Bread"))
    order = []
    for _ in range(4):
        r.frame(hunger=0.3)
        tick(r, sv)
        iid = r.cmd()[1]["itemId"]
        order.append(iid)
        r.answer({"state": "done", "result": {"itemId": iid}})
        r.event("item_removed", itemId=iid)
    assert order == [703, 704, 702, 701]


def test_a_thirst_crossing_during_a_running_sleep_sends_nothing(tmp_path):
    """P23-AB: while the night's sleep is current the need and load branches send nothing (logged holding_sleep);
    the night's own hold answers the tick, and the needs are answered at the wake."""
    from .test_night import house
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    held(r, (701, "Base.WaterBottle"), (702, "Base.Apple"), (601, "Base.Plank"))
    r.frame(x=111.5, y=201.5, fatigue=0.65, thirst=0.1)
    tick(r, sv)
    assert r.cmd() == ("sleep", {})
    r.fake.answer({"sleep": ["accepted"]})
    r.pump()
    sleep = r.acts.history[-1]
    for i in range(5):
        r.advance(0.5)
        r.frame(x=111.5, y=201.5, fatigue=0.5, thirst=0.3, hunger=0.4, level=3)
        assert tick(r, sv) is None, i
        d = last(tmp_path)
        assert d["sent"] is False and d["branch"] == "night", i
        assert d["inputs"]["branches"]["need"] == {"holding_sleep": sleep.aid}, i
        assert d["inputs"]["branches"]["load"] == {"holding_sleep": sleep.aid}, i
    assert [a.type for a in r.acts.history] == ["sleep"]
    r.answer({"state": "done", "result": {"sleptH": 8.0, "fatigueBefore": 0.65, "fatigueAfter": 0.05}})
    r.frame(x=111.5, y=201.5, fatigue=0.05, thirst=0.3)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 701})              # the wake: the need answers


def test_a_threat_still_pre_empts_a_running_sleep(tmp_path):
    from .test_night import house
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=111.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    r.fake.answer({"sleep": ["accepted"]})
    r.pump()
    r.frame(x=111.5, y=201.5, fatigue=0.65, zombies=[zombie(1, 112.5, 202.5)])
    assert tick(r, sv) is not None and last(tmp_path)["branch"] == "threat"


def test_inside_with_every_held_threat_behind_a_wall_the_threat_branch_holds(tmp_path):
    """M-6: a zombie within DANGER_R whose line is blocked, the character inside: no flee out of the shelter. (Survival
    2, P23-AJ 1: the zombie moved from 3.0 to 4.0 tiles, outside HOLD_BREAK_R, which breaks the hold at 3.0.)"""
    from .test_night import house
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=111.5, y=201.5, zombies=[zombie(1, 107.5, 201.5)])
    assert tick(r, sv) is None
    d = last(tmp_path)
    assert d["branch"] == "threat" and d["sent"] is False and threat_why(tmp_path)["flee"] == "held_inside"
    assert r.acts.history == []
    r.frame(x=111.5, y=201.5, zombies=[zombie(1, 107.5, 201.5), zombie(2, 112.5, 202.5)])   # one inside: clear
    assert tick(r, sv) is not None and threat_why(tmp_path).get("flee") != "held_inside"


def test_outside_a_line_blocked_threat_is_not_held(tmp_path):
    from .test_night import house
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=108.5, y=201.5, zombies=[zombie(1, 111.5, 201.5)])
    tick(r, sv)
    assert threat_why(tmp_path).get("flee") != "held_inside"


def test_an_unmapped_threat_square_is_never_read_blocked(tmp_path):
    from .test_night import house
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=111.5, y=201.5, zombies=[zombie(1, 115.5, 201.5)])   # east of the house: no square mapped there
    assert tick(r, sv) is not None and threat_why(tmp_path).get("flee") != "held_inside"


def test_a_refused_food_is_eaten_again_after_refused_ttl_min(tmp_path):
    """P23-AD: the refusal lasts 120 world minutes, not the session."""
    r, sv = make(tmp_path)
    held(r, (701, "Base.Apple"))
    r.frame(hunger=0.3)
    tick(r, sv)
    r.answer({"state": "failed", "reason": "not valid"})
    r.frame(hunger=0.3)                                                # the refusal read at 480
    tick(r, sv)
    assert r.world.refused == {701: 480.0}
    for _ in range(S.FAILED_COOLDOWN_TICKS):                           # +60, past the command cool-down: still refused
        if r.acts.current is not None:
            r.answer()
        r.frame(hunger=0.3, game_min=540.0)
        tick(r, sv)
    assert [a.type for a in r.acts.history].count("consume") == 1
    if r.acts.current is not None:
        r.answer()
    r.frame(hunger=0.3, game_min=601.0)                                # +121: food again
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 701})


# ================================================================ the flee to shelter (ruling P23-AG)
# E1 (e_day-20261028-110422) died at game minute 606, pinned 15 s against a fence the World held while fleeing four
# zombies (the review of survival 1 traced it). A flee with a
# known building whose door's approach square lies away from the threats runs the shelter steps at a run.
GROUP = [(1, 97.0, 201.5), (2, 98.0, 204.0), (3, 98.0, 199.0)]   # three within DANGER_R, west of the player


def group(dx=0.0, me=(100.0, 201.5)):
    return [zombie(i, x + dx, y, me=me) for i, x, y in GROUP]


def shelter_world(r, door, x0=112):
    """Building 1's 3 x 3 interior at x0 (its west door at (x0, 201)) and the open ground x 95..x0-1 mapped."""
    from .test_night import house
    r.scan(grid(95, x0 - 4, 196, 207) + house(1, x0, door=door))


def test_a_flee_with_a_shelter_away_from_the_threats_runs_its_steps_then_holds_inside(tmp_path):
    """Survival 3 (ruling P23-AM 3): the flee is `many` and the nearest beyond SPRINT_R at full endurance, so the
    shelter walks go at a sprint (once a run)."""
    from .test_night import CLOSED, OPEN
    r, sv = make(tmp_path)
    shelter_world(r, CLOSED)
    r.frame(x=100.0, y=201.5, zombies=group())
    tick(r, sv)                                              # the approach square (111, 201) is 11.5 tiles away
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 201.5, "gait": "sprint"})
    w = threat_why(tmp_path)
    assert w["flee"] == "many" and w["shelter"] == 1 and w["step"] == "approach"
    r.answer()
    me = (111.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=group(8.0, me))
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 112, "y": 201, "kind": "open", "filter": "all", "maxWeight": 0.0})
    r.answer()
    shelter_world(r, OPEN)                                   # the door's edge reads open (the live edges)
    r.frame(x=me[0], y=me[1], zombies=group(8.0, me))
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 112.5, "y": 200.5, "gait": "sprint"})
    r.answer()
    me = (112.5, 200.5)                                      # inside, every threat behind the west wall: not yet held,
    r.frame(x=me[0], y=me[1], zombies=group(8.0, me))        # the close is still due
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 112, "y": 201, "kind": "close", "filter": "all", "maxWeight": 0.0})
    assert threat_why(tmp_path)["step"] == "close"
    r.answer()
    shelter_world(r, CLOSED)
    r.frame(x=me[0], y=me[1], zombies=group(8.0, me))
    assert tick(r, sv) is None
    d = last(tmp_path)
    assert d["branch"] == "threat" and d["sent"] is False and threat_why(tmp_path)["flee"] == "held_inside"
    assert [a.type for a in r.acts.history] == ["walkTo", "interact", "walkTo", "interact"]
    shelter_world(r, OPEN)                                   # zombie 1 opens the door and stands in it: its line clears
    zs = [zombie(1, 112.5, 201.5, me=me)] + group(8.0, me)[1:]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1}) and threat_why(tmp_path)["fight"] is True
    assert threat_why(tmp_path)["sheltered"] is True
    all_sends_valid(r)


def test_a_shelter_whose_approach_square_is_nearer_the_threats_is_never_run_to(tmp_path):
    from .test_night import CLOSED
    r, sv = make(tmp_path)
    shelter_world(r, CLOSED)
    me = (104.0, 201.5)                                      # the approach square is 3 tiles from the threats, the
    zs = [zombie(1, 108.5, 201.5, me=me), zombie(2, 108.5, 203.0, me=me), zombie(3, 108.5, 200.0, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)                    # player 4.5
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "many"
    assert threat_why(tmp_path)["shelter"] is None and r.cmd()[1]["vx"] < 0.0


def test_a_shelter_beyond_shelter_flee_r_is_never_run_to(tmp_path):
    from .test_night import CLOSED
    assert P.SHELTER_FLEE_R == 25.0
    r, sv = make(tmp_path)
    shelter_world(r, CLOSED, x0=127)                         # the approach square (126, 201): 26 tiles away
    r.frame(x=100.0, y=201.5, zombies=group())
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["shelter"] is None


def test_a_locked_door_falls_back_to_the_steer_and_shuns_the_building(tmp_path):
    from .test_night import CLOSED
    r, sv = make(tmp_path)
    shelter_world(r, CLOSED)                                 # the map reads it closed; the open finds it locked
    r.frame(x=100.0, y=201.5, zombies=group())
    tick(r, sv)
    r.answer()
    me = (111.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=group(8.0, me))
    tick(r, sv)
    assert r.cmd()[1]["kind"] == "open"
    r.answer({"state": "failed", "reason": "locked"})
    r.frame(x=me[0], y=me[1], zombies=group(8.0, me))
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["shelter"] is None
    assert sv.night.shunned == {1: 480.0}
    r.answer()
    r.frame(x=me[0], y=me[1], zombies=group(8.0, me))
    tick(r, sv)                                              # the episode keeps the steer
    assert r.cmd()[0] == "steer"
    sv2_dir = tmp_path / "b"
    sv2_dir.mkdir()
    r2, sv2 = make(sv2_dir)                                  # a new flee in the same store passes the shunned building
    sv2.night.shunned[1] = 480.0
    shelter_world(r2, CLOSED)
    r2.frame(x=100.0, y=201.5, zombies=group())
    tick(r2, sv2)
    assert r2.cmd()[0] == "steer"


def test_a_door_the_map_reads_locked_is_never_run_to(tmp_path):
    from .test_night import LOCKED
    r, sv = make(tmp_path)
    shelter_world(r, LOCKED)
    r.frame(x=100.0, y=201.5, zombies=group())
    tick(r, sv)
    assert r.cmd()[0] == "steer" and sv.night.shunned == {}


# ================================================================ survival 1 fix round 1 (the review's I1-I4, M1-M5)
def sheltered(r, sv, weapon=BAT):
    """Run the shelter steps of the first test to the closed door and the inside hold; the player at (112.5, 200.5)."""
    from .test_night import CLOSED, OPEN
    shelter_world(r, CLOSED)
    r.frame(x=100.0, y=201.5, zombies=group(), weapon=weapon)
    tick(r, sv)
    me = (111.5, 201.5)
    for door, at in ((CLOSED, me), (OPEN, me), (OPEN, (112.5, 200.5))):
        r.answer()
        if door is OPEN:
            shelter_world(r, OPEN)
        me = at
        r.frame(x=me[0], y=me[1], zombies=group(8.0, me), weapon=weapon)
        tick(r, sv)
    assert r.cmd()[1]["kind"] == "close"
    r.answer()
    shelter_world(r, CLOSED)
    r.frame(x=me[0], y=me[1], zombies=group(8.0, me), weapon=weapon)
    assert tick(r, sv) is None and threat_why(r.dir)["flee"] == "held_inside"
    return me


@pytest.mark.parametrize("far", [False, True])
def test_a_zombie_in_the_corridor_to_the_door_refuses_it(tmp_path, far):
    """I1 and M3: a zombie 4 tiles along the line to a door 11.5 tiles away (and one 0.5 behind) passed the nearest-
    against-nearest test; a known zombie on the line beyond the hold radius refuses it too."""
    from .test_night import CLOSED
    r, sv = make(tmp_path)
    shelter_world(r, CLOSED)
    me = (100.0, 201.5)
    on_line = zombie(2, 111.0 if far else 104.0, 201.6, me=me)   # far: 11 tiles, not held
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 99.5, 201.5, me=me), on_line], weapon=None)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["shelter"] is None
    assert P.CORRIDOR_R == 2.0


def test_a_zombie_beside_the_corridor_beyond_corridor_r_does_not_refuse_it(tmp_path):
    from .test_night import CLOSED
    r, sv = make(tmp_path)
    shelter_world(r, CLOSED)
    me = (100.0, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 99.5, 201.5, me=me), zombie(2, 104.0, 204.0, me=me)], weapon=None)
    tick(r, sv)                                              # 2.5 tiles off the line
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 201.5, "gait": "run"})


def test_a_known_zombie_inside_the_building_refuses_it(tmp_path):
    """M4."""
    from .test_night import CLOSED
    r, sv = make(tmp_path)
    shelter_world(r, CLOSED)
    me = (100.0, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 99.5, 201.5, me=me), zombie(2, 113.5, 202.5, me=me)], weapon=None)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["shelter"] is None


def test_unarmed_and_sheltered_with_a_zombie_in_line_re_closes_once_then_holds_trapped(tmp_path):
    """I2: never hold with a line clear; one re-close of the open door, and when it fails no second close.
    (Survival 2 fix round 1: on a room square the flee never steers; it holds, `trapped`.)"""
    from .test_night import OPEN
    r, sv = make(tmp_path)
    sheltered(r, sv, weapon=None)
    me = (113.5, 201.5)                                      # in the door's row
    shelter_world(r, OPEN)
    zs = [zombie(1, 109.5, 201.5, me=me)] + group(8.0, me)[1:]
    r.frame(x=me[0], y=me[1], zombies=zs, weapon=None)
    assert tick(r, sv) is not None
    assert r.cmd() == ("interact", {"x": 112, "y": 201, "kind": "close", "filter": "all", "maxWeight": 0.0})
    assert threat_why(tmp_path)["step"] == "reclose"
    r.answer({"state": "failed", "reason": "blocked"})
    r.frame(x=me[0], y=me[1], zombies=zs, weapon=None)
    assert tick(r, sv) is None and threat_why(tmp_path)["trapped"] == 1
    assert [a.type for a in r.acts.history].count("interact") == 3   # the open, the close and the one re-close


def test_unarmed_with_a_zombie_in_the_doorway_never_re_closes(tmp_path):
    """Concern 4: a known zombie within 1.5 tiles of the door: no close tried beside it. (Survival 2 fix round 1: on
    a room square the flee never steers; unarmed, it holds, `trapped`.)"""
    from .test_night import OPEN
    r, sv = make(tmp_path)
    me = sheltered(r, sv, weapon=None)
    shelter_world(r, OPEN)
    zs = [zombie(1, 112.5, 201.5, me=me)] + group(8.0, me)[1:]
    r.frame(x=me[0], y=me[1], zombies=zs, weapon=None)
    assert tick(r, sv) is None and threat_why(tmp_path)["trapped"] == 1
    assert [a.type for a in r.acts.history].count("interact") == 2   # the open and the close of the steps only


def test_the_door_fight_kills_in_the_doorway_then_re_closes_never_walks_out(tmp_path):
    """I3: after the doorway kill, two zombies 5 tiles outside, line-clear through the open door: a close, no walk."""
    from .test_night import CLOSED, OPEN
    r, sv = make(tmp_path)
    sheltered(r, sv)
    me = (113.5, 201.5)                                      # inside, in the door's row: the open door is in line
    shelter_world(r, OPEN)
    outside = [zombie(2, 108.5, 201.2, me=me), zombie(3, 109.5, 201.7, me=me)]
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 112.5, 201.5, me=me)] + outside)
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1}) and threat_why(tmp_path)["sheltered"] is True
    assert sv.fight.only == {1} and sv.fight.unreachable is sv.unreachable
    r.answer({"state": "done", "result": swing(True)})
    r.event("zombie_dead", id=1)
    r.frame(x=me[0], y=me[1], zombies=outside)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 112, "y": 201, "kind": "close", "filter": "all", "maxWeight": 0.0})
    assert threat_why(tmp_path)["sheltered"] is True and threat_why(tmp_path)["step"] == "reclose"
    r.answer()
    shelter_world(r, CLOSED)
    r.frame(x=me[0], y=me[1], zombies=outside)
    assert tick(r, sv) is None and threat_why(tmp_path)["flee"] == "held_inside"
    assert "walkTo" not in [a.type for a in r.acts.history[-3:]]


def test_a_shelter_step_failed_for_no_shun_reason_falls_back_without_a_shun(tmp_path):
    """M1: only night.SHUN_REASONS shun; any failure falls back to the steer."""
    from .test_night import CLOSED
    r, sv = make(tmp_path)
    shelter_world(r, CLOSED)
    r.frame(x=100.0, y=201.5, zombies=group())
    tick(r, sv)
    r.answer({"state": "failed", "reason": "interrupted"})
    r.frame(x=100.0, y=201.5, zombies=group())
    tick(r, sv)
    assert r.cmd()[0] == "steer" and sv.night.shunned == {}


def test_a_wounded_fight_with_zombies_at_five_and_eight_still_fights(tmp_path):
    """M5: `pair` counts DANGER_R while a fight holds DISENGAGE_R (the surviving half of the Plan 21b fix). Named
    change, ruling P24-A (b): zombie 2 moves from (108, 200), straight behind the target, to (100, 208)."""
    r, sv = make(tmp_path)
    cut = {"scratched": 1}
    r.frame(zombies=[zombie(1, 105.0, 200.0)], wounds=cut)
    tick(r, sv)
    r.frame(zombies=[zombie(1, 105.0, 200.0), zombie(2, 100.0, 208.0)], wounds=cut)
    tick(r, sv)
    assert last(tmp_path)["inputs"]["mode"] == "fight" and "flee" not in threat_why(tmp_path)
    assert [a.type for a in r.acts.history] == ["walkTo"]


def test_every_fight_survive_makes_shares_its_unreachable_memory(tmp_path):
    """The X5-2 addendum: the driver built its Fights without the marks; Survive gives every Fight the one memory."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0)])
    tick(r, sv)
    first = sv.fight
    r.answer()
    r.frame(zombies=[zombie(1, 103.0, 200.0)], health=30.0)    # a flee in between
    tick(r, sv)
    assert sv.mode == "flee"
    r.answer()
    r.frame(zombies=[zombie(1, 103.0, 200.0)], health=100.0)
    tick(r, sv)
    assert sv.mode == "fight" and sv.fight is not first
    assert first.unreachable is sv.unreachable and sv.fight.unreachable is sv.unreachable


def test_a_running_flee_counts_many_within_danger_r_and_holds_the_rest(tmp_path):
    """Ruling 2: the hold radius widens `many` only while a fight runs; a flee with three held, one within 6, reads
    `held`."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0)], weapon=None)
    tick(r, sv)
    r.answer()
    r.frame(zombies=[zombie(1, 103.0, 200.0), zombie(2, 108.0, 200.0), zombie(3, 100.0, 209.0)])
    tick(r, sv)
    assert last(tmp_path)["inputs"]["mode"] == "flee" and threat_why(tmp_path)["flee"] == "held"


# ================================================================ survival 1 fix round 2
def test_a_door_refused_at_the_first_re_aim_is_taken_at_the_next(tmp_path):
    """T1: the melee zombie ahead toward the door refuses its corridor at the flee's start; once it is behind, the
    next re-aim picks the door."""
    from .test_night import CLOSED
    r, sv = make(tmp_path)
    shelter_world(r, CLOSED)
    me = (100.0, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 100.8, 201.5, me=me)], weapon=None)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["shelter"] is None
    r.answer()
    me = (101.0, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 99.5, 201.5, me=me)], weapon=None)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 201.5, "gait": "run"}) and threat_why(tmp_path)["shelter"] == 1


def test_a_flee_that_starts_inside_with_its_only_door_toward_the_group_adopts_the_building(tmp_path):
    """Concern 3's case under ruling P23-AJ 3 and its fix round 1 (the adoption is back as the fallback): the
    character inside after a loot, a group in line through the open west door, the only way out: its outside square
    is nearer each zombie than the character is, so no exit is walked at the group; the building is adopted, the
    door re-closed, then the inside hold."""
    from .test_night import CLOSED, OPEN
    r, sv = make(tmp_path)
    shelter_world(r, OPEN)
    me = (113.5, 201.5)
    zs = [zombie(1, 108.5, 201.2, me=me), zombie(2, 109.5, 201.7, me=me), zombie(3, 107.6, 201.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 112, "y": 201, "kind": "close", "filter": "all", "maxWeight": 0.0})
    assert threat_why(tmp_path)["flee"] == "many" and threat_why(tmp_path)["step"] == "reclose"
    assert sv.flee.exit is None and sv.flee.sheltered is True and sv.flee.adopted is True
    r.answer()
    shelter_world(r, CLOSED)
    r.frame(x=me[0], y=me[1], zombies=zs)
    assert tick(r, sv) is None and threat_why(tmp_path)["flee"] == "held_inside"
    assert [a.type for a in r.acts.history] == ["interact"]


def test_the_sheltered_hold_survives_a_threat_on_an_unmapped_square(tmp_path):
    """Concern 2: the door closed, no line reads clear; a held zombie on unscanned ground (its line unknown) does
    not end the hold."""
    r, sv = make(tmp_path)
    me = sheltered(r, sv)
    zs = group(8.0, me) + [zombie(4, 118.5, 201.5, me=me)]      # x 118: nothing mapped east of the house
    r.frame(x=me[0], y=me[1], zombies=zs)
    n = len(r.acts.history)
    assert tick(r, sv) is None and len(r.acts.history) == n
    assert threat_why(tmp_path)["step"] == "done" and sv.flee.sheltered is True


def test_a_door_fight_that_steps_off_the_room_drops_the_stale_flee(tmp_path):
    from .test_night import OPEN
    r, sv = make(tmp_path)
    me = sheltered(r, sv)
    shelter_world(r, OPEN)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 112.5, 201.5, me=me)])
    tick(r, sv)
    stale = sv.flee
    assert r.cmd() == ("attack", {"targetId": 1}) and stale is not None and stale.sheltered
    r.answer({"state": "done", "result": swing(True)})
    me = (111.5, 201.5)                                      # knocked out of the doorway, the group still held
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 112.5, 201.5, me=me)])
    tick(r, sv)
    assert sv.mode == "flee" and sv.flee is not stale and not sv.flee.sheltered
    (tmp_path / "b").mkdir()                                 # alone with the doorway zombie: the fight goes on unpinned
    r2, sv2 = make(tmp_path / "b")
    me = sheltered(r2, sv2)
    shelter_world(r2, OPEN)
    r2.frame(x=me[0], y=me[1], zombies=[zombie(1, 112.5, 201.5, me=me)])
    tick(r2, sv2)
    for i in (2, 3):
        r2.event("zombie_dead", id=i)
    r2.answer({"state": "done", "result": swing(True)})
    me = (111.5, 201.5)
    r2.frame(x=me[0], y=me[1], zombies=[zombie(1, 112.5, 201.5, me=me)])
    tick(r2, sv2)
    assert sv2.mode == "fight" and sv2.flee is None and sv2.fight.only is None


# ================================================================ survival 1 fix round 3
def test_inside_a_flee_walks_out_of_the_open_door_away_from_the_group_not_the_nearer_closed_one(tmp_path):
    """F1's map under ruling P23-AJ 3 (survival 2: the adopted re-close is gone): a loot entered by the north door
    left it open; two zombies near the closed west door, a third come in (its line clear, so no hold): the flee
    walks out of the north door at a run."""
    from .test_night import CLOSED, OPEN, house
    r, sv = make(tmp_path)
    north = [square(113, y) for y in range(194, 200)]
    north_door = square(113, 200, room="kitchen", building=1, door=OPEN, blockN=False, edgeN=True)
    r.scan(grid(95, 108, 196, 207) + house(1, 112, door=CLOSED) + north + [north_door])
    me = (113.5, 201.5)
    zs = [zombie(1, 108.5, 201.5, me=me), zombie(2, 109.0, 201.5, me=me), zombie(3, 112.2, 202.6, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 113.5, "y": 198.5, "gait": "run"})   # the square beyond the doorway
    assert threat_why(tmp_path)["flee"] == "many" and "cornered" not in threat_why(tmp_path)
    w = threat_why(tmp_path)
    assert w["exit"] == 1 and w["outer"] == [113, 199, 0] and w["door"] is None and w["step"] == "walk"


# ================================================================ survival 2 (ruling P23-AJ)
# E2 (e_day_2-20261028-124249) died at game minute 592 standing inside building 3: the inside hold stood while a zombie
# closed from 5.78 to 3.05 tiles with its line read blocked, then nine sprint steers pinned it against its own room's
# walls, the bat never swung. The hold breaks on approach (1), a cornered flee fights (2), and inside a building the
# flee walks out (3).
def test_the_survival_2_constants():
    assert (S.HOLD_BREAK_R, S.CLOSING_TICKS, S.CORNERED_R, S.CORNER_FREE_R) == (3.0, 3, 1.5, 5.0)


@pytest.mark.parametrize("zx, holds", [(108.0, True), (108.6, False)])   # 3.5 and 2.9 tiles, the line blocked
def test_a_held_threat_within_hold_break_r_breaks_the_inside_hold_whatever_its_line_reads(tmp_path, zx, holds):
    """Rule 1: the west door closed, the zombie behind the west wall; at 2.9 tiles the hold breaks. The only way
    out (the closed door) runs at it, so with one held the Fight takes it (the broken hold's fallback)."""
    from .test_night import house
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    me = (111.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, zx, 201.5, me=me)])
    assert P.line_to(r.world, r.world.zombies[1]) is False
    sent = tick(r, sv)
    w = threat_why(tmp_path)
    if holds:
        assert sent is None and w["flee"] == "held_inside"
    else:
        assert sent is not None and w.get("flee") is None and w["fight"] is True and w["breach"] == "near"
        assert r.cmd() == ("walkTo", {"x": 108.5, "y": 201.5, "gait": "run"})


@pytest.mark.parametrize("xs, broken_at", [((107.0, 107.5, 108.0), 3), ((107.0, 107.5, 107.3, 107.7), None)])
def test_a_threat_closing_on_three_ticks_inside_danger_r_breaks_the_hold(tmp_path, xs, broken_at):
    """Rule 1: the nearest held threat at 5.5, 5.0, 4.5 tiles on three ticks, its line blocked: the third breaks the
    hold (`closing`); 5.5, 5.0, 5.2, 4.8 never closes three in a row and holds."""
    from .test_night import house
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    me = (112.5, 201.5)
    for i, zx in enumerate(xs, 1):
        r.frame(x=me[0], y=me[1], zombies=[zombie(1, zx, 201.5, me=me)])
        sent = tick(r, sv)
        w = threat_why(tmp_path)
        if i == broken_at:
            assert sent is not None and w.get("flee") != "held_inside" and w["breach"] == "closing"
        else:
            assert sent is None and w["flee"] == "held_inside"


def open_yard(x0=90, x1=112, y0=192, y1=212):
    return grid(x0, x1, y0, y1)


@pytest.mark.parametrize("n", [2, 3])
def test_a_stuck_flee_with_the_nearest_within_cornered_r_fights_it_whatever_the_count(tmp_path, n):
    """Rule 2: a pair (health 50) or three (`many`) fled; the leg moved 0.1 tiles (stuck) and the nearest is at 1.2:
    the Fight takes the nearest, MAX_FIGHT aside; once the nearest is beyond CORNER_FREE_R the flee resumes with a
    fresh Flee (its first leg not stuck)."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    zs = [zombie(1, 103.0, 201.5, me=me), zombie(2, 100.5, 205.0, me=me), zombie(3, 98.0, 198.0, me=me)][:n]
    r.frame(x=me[0], y=me[1], zombies=zs, health=50.0)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and sv.mode == "flee"
    r.answer()
    me = (100.6, 201.5)
    zs = [zombie(1, 101.8, 201.5, me=me), zombie(2, 100.6, 204.0, me=me), zombie(3, 98.6, 199.0, me=me)][:n]
    r.frame(x=me[0], y=me[1], zombies=zs, health=50.0)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd() == ("attack", {"targetId": 1}) and w["cornered"] == 1 and w["fight"] is True
    assert sv.mode == "fight" and sv.fight.target == 1
    r.answer({"state": "done", "result": swing(True)})
    zs = [zombie(1, 105.8, 201.5, me=me), zombie(2, 100.6, 207.0, me=me), zombie(3, 95.0, 201.5, me=me)][:n]
    r.frame(x=me[0], y=me[1], zombies=zs, health=50.0)     # knocked back: the nearest beyond 5 tiles
    tick(r, sv)
    assert r.cmd()[0] == "steer" and sv.cornered is None and sv.mode == "flee" and sv.flee.stuck() is False


@pytest.mark.parametrize("nx, cornered", [(99.7, True), (100.1, False)])   # the nearest at 1.2 and 1.6 tiles
def test_a_flee_leg_that_moved_is_cornered_only_at_melee_range(tmp_path, nx, cornered):
    """Survival 2 read a leg that moved as no corner (the nearest at 1.2: the steer); the coordinator's amendment 6
    to ruling P23-AM judges the corner on every threat tick whatever ran, so at 1.2 tiles (one or two within
    CORNERED_R, the line clear, no mark) the corner attacks, a `walk` corner ending beyond CORNERED_R; at 1.6 the
    steer."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 103.0, 201.5, me=me), zombie(2, 100.5, 205.0, me=me)], health=50.0)
    tick(r, sv)
    r.answer()
    me = (98.5, 201.5)                                       # it moved 2 tiles; the nearest followed
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, nx, 201.5, me=me), zombie(2, 99.0, 204.0, me=me)], health=50.0)
    tick(r, sv)
    if cornered:
        assert r.cmd() == ("attack", {"targetId": 1}) and threat_why(tmp_path)["cornered"] == 1
        assert sv.corner_kind == "walk" and sv.corner_free == S.CORNERED_R and sv.fight.mark_free_r == 0.0
    else:
        assert r.cmd()[0] == "steer" and "cornered" not in threat_why(tmp_path) and sv.cornered is None


def closed_room(bid=2):
    """Building `bid`'s 5 x 5 room x 100..104, y 200..204, walled on all four sides with no door or opening, in a
    mapped yard x 98..106, y 198..206."""
    at = {}
    for x in range(100, 105):
        for y in range(200, 205):
            at[(x, y)] = {"room": "storage", "building": bid, "blockW": x == 100, "blockN": y == 200}
    for y in range(200, 205):
        at[(105, y)] = {"blockW": True}
    for x in range(100, 105):
        at[(x, 205)] = {"blockN": True}
    return grid(98, 106, 198, 206, at)


@pytest.mark.parametrize("nx, cornered", [(103.7, True), (104.5, False)])   # the nearest at 1.2 and 2.0 tiles
def test_on_a_room_square_with_no_way_out_the_nearest_within_cornered_r_is_fought(tmp_path, nx, cornered):
    """Rule 2: three zombies came in (`many`), no exterior door or opening known: the nearest at 1.2 is fought on the
    first tick as `cornered`; at 2.0 too, as the trapped fight (fix round 1, the review's G3: inside with no way out
    and nothing to adopt, armed, the flee is the Fight, never a steer). Survival 4 (e07a52cb) steered at 1.2 first
    (three within GROUP_NEAR_R, a group); its fix round 1, R3, reads no group on a trapped room square (no leg can
    move there), so the corner stands at once, as before survival 4."""
    r, sv = make(tmp_path)
    r.scan(closed_room())
    me = (102.5, 202.5)
    zs = [zombie(1, nx, 202.5, me=me), zombie(2, 100.5, 200.5, me=me), zombie(3, 104.5, 204.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    assert P.exit_plan(r.world, list(r.world.zombies.values())) is None and not P.adoptable(r.world)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd() == ("attack", {"targetId": 1}) and w["fight"] is True and "group" not in w
    assert (w.get("cornered") == 1) is cornered


@pytest.mark.parametrize("weapon", [BAT, None])
def test_a_flee_on_a_room_square_with_no_way_out_and_the_nearest_at_three_tiles_fights_armed_else_holds(tmp_path,
                                                                                                       weapon):
    """Survival 2's "no door known, the nearest at 3 tiles: the steer", turned by fix round 1 (G3, M4): armed, the
    Fight on the nearest; unarmed, the trapped hold (no command): never a steer into the room's walls."""
    r, sv = make(tmp_path)
    r.scan(closed_room())
    me = (100.5, 204.5)
    zs = [zombie(1, 100.5, 201.5, me=me), zombie(2, 101.5, 201.5, me=me), zombie(3, 102.5, 201.6, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs, weapon=weapon)
    tick(r, sv)
    w = threat_why(tmp_path)
    if weapon is None:
        assert r.acts.history == [] and w["flee"] == "unarmed" and w["trapped"] == 2 and "exit" not in w
    else:
        assert r.cmd() == ("walkTo", {"x": 100.5, "y": 201.5, "gait": "run"}) and w["fight"] is True
        assert sv.fight.target == 1


def test_a_flee_starting_inside_walks_out_of_the_door_away_from_the_threats_then_steers_outside(tmp_path):
    """Rule 3: two exterior doors, threats north (one in line through the open north doorway, so no hold): the walk
    to the south door's outside square at a run; nothing more while it runs or while the frame reads inside; the
    steer once the frame reads outside, the building left (never the episode's shelter)."""
    from .test_policies import two_door_house
    r, sv = make(tmp_path)
    r.scan(two_door_house())
    me = (111.5, 201.5)
    north = lambda me: [zombie(1, 110.5, 197.5, me=me), zombie(2, 111.5, 197.0, me=me),
                        zombie(3, 112.5, 197.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=north(me))
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 204.5, "gait": "run"})   # beyond the doorway's yard square
    w = threat_why(tmp_path)
    assert w["flee"] == "many" and w["exit"] == 1 and w["outer"] == [111, 203, 0] and w["step"] == "walk"
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    me = (111.5, 202.4)                                     # mid-walk, inside
    r.frame(x=me[0], y=me[1], zombies=north(me))
    assert tick(r, sv) is None and len(r.acts.history) == 1
    r.fake.answer({"walkTo": ["done"]})
    r.pump()
    me = (111.5, 203.5)                                     # through the doorway: the yard
    r.frame(x=me[0], y=me[1], zombies=north(me))
    tick(r, sv)
    assert r.cmd()[0] == "steer" and r.cmd()[1]["vy"] > 0.0 and sv.flee.left == {1} and sv.flee.exit is None
    assert [a.type for a in r.acts.history] == ["walkTo", "steer"]
    all_sends_valid(r)


def test_an_exit_through_a_closed_door_walks_first_opens_after_a_failed_walk_and_a_walk_ending_inside_refuses_it(
        tmp_path):
    """Rule 3 with fix round 1 (I2): threats south, the north door closed: the run walk through it first (the jar's
    path follower opens a door on a player's path); that walk failed, the open, then the walk again; a walk that ended
    done with the frame still inside refuses that way out; with none left the building is adopted (the south door
    open toward the group, its re-close guarded) and dropped, the flee holds `trapped` that tick, and the next tick
    is the trapped fight (G3)."""
    from .test_night import CLOSED, OPEN
    from .test_policies import two_door_house
    r, sv = make(tmp_path)
    r.scan(two_door_house(north=CLOSED))
    me = (111.5, 201.5)
    south = lambda me: [zombie(1, 111.5, 205.5, me=me), zombie(2, 110.5, 205.5, me=me),
                        zombie(3, 112.5, 205.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=south(me))
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 198.5, "gait": "run"})
    assert threat_why(tmp_path)["step"] == "walk" and threat_why(tmp_path)["door"] == [111, 200, 0]
    r.answer({"state": "failed", "reason": "no path"})
    r.frame(x=me[0], y=me[1], zombies=south(me))
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 111, "y": 200, "kind": "open", "filter": "all", "maxWeight": 0.0})
    r.answer()
    r.scan(two_door_house(north=OPEN))
    r.frame(x=me[0], y=me[1], zombies=south(me))
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 198.5, "gait": "run"})
    r.answer()
    r.frame(x=me[0], y=me[1], zombies=south(me))            # done, still inside: refused
    assert tick(r, sv) is None
    assert sv.flee.refused == {(111, 199, 0)} and threat_why(tmp_path)["trapped"] == 1 and sv.flee.adopted
    r.frame(x=me[0], y=me[1], zombies=south(me))
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 205.5, "gait": "run"}) and threat_why(tmp_path)["fight"] is True
    assert [a.type for a in r.acts.history] == ["walkTo", "interact", "walkTo", "walkTo"]
    all_sends_valid(r)


def test_an_exit_walk_that_stops_moving_for_exit_stall_s_is_dropped_and_the_next_way_out_taken(tmp_path):
    """Fix round 1 (G2): the walk out of the south doorway leaves the player in place for 1.0 s while still running:
    dropped (the Flee no longer waits on it), that way refused, and the north doorway walked."""
    from .test_policies import two_door_house
    r, sv = make(tmp_path)
    r.scan([q for q in two_door_house() if q["x"] < 115])     # the group east on unscanned ground: no hold
    me = (111.5, 201.5)
    east = lambda me: [zombie(1, 116.0, 201.2, me=me), zombie(2, 115.8, 201.9, me=me), zombie(3, 115.5, 201.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=east(me))
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 198.5, "gait": "run"})
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    for dt, moved in ((0.5, 0.0), (0.5, 0.2)):              # 0.2 tiles in 1.0 s: under STUCK_MOVE
        r.advance(dt)
        r.frame(x=me[0], y=me[1] - moved, zombies=east(me))
        tick(r, sv)
    assert sv.flee.refused == {(111, 199, 0)}
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 204.5, "gait": "run"})
    assert P.WALK_STALL_S == 1.0   # P24-A (g): EXIT_STALL_S and STEP_STALL_S are one constant


@pytest.mark.parametrize("held", [3, 4])
def test_a_running_exit_walk_is_pre_empted_by_the_corner(tmp_path, held):
    """Fix round 1 (G2): mid-walk a zombie comes within CORNERED_R: the attack goes, superseding the walk. Named
    change, ruling P23-AP 2: that holds with three held (zombie 3 died); with four held (GROUP_HOLD_N) they are a
    group: no corner. Named change, ruling P24-A (f): on the room square the group takes the exit, never the steer:
    the running walk (at a run) is re-sent at a sprint, the exit kept and not refused."""
    from .test_policies import two_door_house
    r, sv = make(tmp_path)
    r.scan([q for q in two_door_house() if q["x"] < 115])     # the group east on unscanned ground: no hold
    me = (111.5, 201.5)
    east = [zombie(1, 116.0, 201.2, me=me), zombie(2, 115.8, 201.9, me=me), zombie(3, 115.5, 201.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=east)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 198.5, "gait": "run"}) and threat_why(tmp_path)["flee"] == "many"
    walk = r.acts.history[-1]
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    if held == 3:
        r.event("zombie_dead", id=3)
    r.frame(x=me[0], y=me[1], zombies=east[:held - 1] + [zombie(4, 112.5, 201.8, me=me)])
    tick(r, sv)
    w = threat_why(tmp_path)
    if held == 3:
        assert r.cmd() == ("attack", {"targetId": 4}) and w["cornered"] == 4
        return
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 198.5, "gait": "sprint"}) and w["group"] == "hold"
    assert "cornered" not in w and w["exit"] == 1 and sv.flee.exit is not None and not sv.flee.refused
    assert sv.flee._dropped is walk and r.acts.history[-1] is not walk and sv.flee._exit_a is r.acts.history[-1]


def test_a_held_threat_within_hold_break_r_breaks_the_sheltered_hold_too(tmp_path):
    """Rule 1 on the chosen shelter (iteration 1's sheltered hold): the door closed, zombie 1 at 2.7 tiles outside
    the west wall, its line blocked; the only way out runs at it and four are held, so the plan is dropped (never
    the hold that let E2's zombie close); fix round 1: the adoption re-reads the same closed door, drops, and the flee
    holds, `trapped`, with no command, for the corner to fight at melee range. Survival 3 (ruling P23-AM 1): the
    episode began `many` and a held threat is within DANGER_R, so its reason stays `many` (once `held`)."""
    r, sv = make(tmp_path)
    me = sheltered(r, sv)
    zs = [zombie(1, 109.8, 200.5, me=me)] + group(8.0, me)[1:]
    r.frame(x=me[0], y=me[1], zombies=zs)
    assert P.line_to(r.world, r.world.zombies[1]) is False
    n = len(r.acts.history)
    assert tick(r, sv) is None and len(r.acts.history) == n
    w = threat_why(tmp_path)
    assert w["breach"] == "near" and w["flee"] == "many" and w["trapped"] == 1 and sv.flee.plan is None


def test_inside_at_melee_range_the_corner_fights_before_any_walk_out_then_walks_once_beyond_cornered_r(tmp_path):
    """Fix round 1 (rule 2 before rule 3): at health 30 (`health`), a zombie in the room 1.2 tiles off with the
    north doorway a way out: the Fight first; knocked back to 1.8 tiles the corner ends (CORNERED_R, a way out known)
    and the flee walks out of the north doorway."""
    from .test_policies import two_door_house
    r, sv = make(tmp_path)
    r.scan(two_door_house())
    me = (111.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 110.6, 202.3, me=me)], health=30.0)
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1}) and threat_why(tmp_path)["cornered"] == 1
    assert sv.fight.point_blank is True and sv.corner_free == S.CORNERED_R
    r.answer({"state": "done", "result": swing(True)})
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 110.0, 202.5, me=me)], health=30.0)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 198.5, "gait": "run"}) and sv.cornered is None


# ================================================================ survival 2 fix round 1: E2's own geometry
ARTIFACTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "artifacts")
E2 = os.path.join(ARTIFACTS, "e_day_2-20261028-124249")
E3 = os.path.join(ARTIFACTS, "e_day_3-20261028-153631")
E4 = os.path.join(ARTIFACTS, "e_day_4-20261028-173649")


@functools.lru_cache(maxsize=3)
def _run_lines(run):
    """A run's state.log through FileTransport (the delta frames merged as live) and its decision walls by log
    line."""
    from agent.base.transport.files import FileTransport
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(os.path.join(run, "state.log"), os.path.join(d, "state.log"))
        lines = list(FileTransport(d).lines())
    with open(os.path.join(run, "decision.log"), encoding="utf-8") as f:
        walls = [json.loads(ln)["wall"] for ln in f]
    return lines, walls


def run_worlds(run, decision_lines):
    """(line, wall, World) for each of the ascending `decision_lines`: one World fed the run's state.log up to the
    first frame at or after the wall of `decision.log` line `line`, as live."""
    from agent.base.world import World
    lines, walls = _run_lines(run)
    w, i = World(), 0
    for line in decision_lines:
        while True:
            if i >= len(lines):
                raise AssertionError("no frame at line %d" % line)
            ln = lines[i]
            w.apply(ln)
            i += 1
            if ln["kind"] == "frame" and ln["wallMs"] / 1000.0 >= walls[line - 1]:
                break
        yield line, walls[line - 1], w


def e2_world(decision_line):
    """A World of E2's state.log up to the first frame at or after the wall of `decision.log` line `decision_line`."""
    return next(run_worlds(E2, [decision_line]))[2]


def test_e2_building_3_has_two_openings_and_neither_is_a_window():
    """Fix round 1 (the review's G1): of the seven steps out of building 3 the first build read, five are smashed
    windows (the bathroom's west, the kitchen's north, the hall's (10741, 10635), the living room's two); the two
    doorways, their doors broken to debris, remain."""
    w = e2_world(227)
    assert w.openings(3) == [((10740, 10634, 0), (10740, 10635, 0)), ((10743, 10630, 0), (10743, 10629, 0))]
    assert (w.map[(10738, 10632, 0)].get("window") is not None and w.map[(10738, 10632, 0)]["edgeW"]
            and not w.map[(10738, 10632, 0)]["blockW"])


@pytest.mark.parametrize("line", [159, 162])
def test_e2_at_game_minutes_582_to_583_no_way_out_is_walked_past_the_hall(line):
    """Fix round 1: E2 in building 3's bathroom, two zombies held in the hall: both doorways lie past them (each
    outside square nearer a zombie than the player is), so no exit; the bathroom's west window (the first build's
    pick) is none."""
    w = e2_world(line)
    held = [z for z in w.zombies.values() if z.get("x") is not None and P.zdist(w, z) <= P.DISENGAGE_R]
    assert len(held) == 2 and P.on_room(w)
    assert P.exit_plan(w, held) is None and not P.adoptable(w)


def test_e2_at_line_164_the_broken_hold_fights_zombie_12839(tmp_path):
    """Fix round 1 (the review's G3): line 164 (game minute 583), the hold broken by `closing` (5.948, 5.626, 5.462
    tiles on lines 162-164): no way out, nothing to adopt, armed: the Fight on 12839, never the walk at the window."""
    w = e2_world(164)
    r = Rig(tmp_path)
    sv = Survive(w, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.mode, sv.flee = "flee", P.Flee(w, r.acts, r.clock)
    sv.closing = (2, 5.626)
    sv.tick(w, r.acts)
    why = threat_why(tmp_path)
    assert sv.mode == "fight" and sv.fight.target == 12839 and why["fight"] is True and why["breach"] == "closing"
    assert r.cmd()[0] == "walkTo"


def test_e2_at_game_minute_585_the_zombie_in_the_bathroom_doorway_is_fought_not_walked_past(tmp_path):
    """Fix round 1 (concern 3): decision.log line 177, zombie 12839 at 0.48 tiles in the bathroom's doorway: the
    survival 2 build chose the far east window (10749, 10629) past it; now no way out is taken and the corner fights
    it."""
    w = e2_world(177)
    held = [z for z in w.zombies.values() if z.get("x") is not None and P.zdist(w, z) <= P.DISENGAGE_R]
    near_id, near = min(((zid, z) for zid, z in w.zombies.items() if z in held), key=lambda p: P.zdist(w, p[1]))
    assert P.zdist(w, near) < 0.5 and P.exit_plan(w, held) is None
    r = Rig(tmp_path)
    sv = Survive(w, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.tick(w, r.acts)
    assert r.cmd() == ("attack", {"targetId": near_id})
    assert threat_why(tmp_path)["cornered"] == near_id


def test_a_marked_zombie_within_cornered_r_still_corners_and_is_swung_at(tmp_path):
    """Fix round 1 (the review's I3): zombie 1 marked unreachable (its line once read blocked) bites at 1.2 tiles in a
    room with no way out: the corner ignores the mark and its Fight swings at it. Named change, ruling P23-AP 2: the
    other two stand at 3.05 tiles (were 2.83), so no third zombie is within GROUP_NEAR_R (no group)."""
    r, sv = make(tmp_path)
    r.scan(closed_room())
    me = (102.5, 202.5)
    zs = [zombie(1, 103.7, 202.5, me=me), zombie(2, 100.5, 200.2, me=me), zombie(3, 104.5, 204.8, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    sv.unreachable[1] = r.clock() + 20.0
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1}) and threat_why(tmp_path)["cornered"] == 1


def test_a_broken_hold_at_a_chosen_shelter_fights_only_in_its_doorway_or_inside(tmp_path):
    """Fix round 1 (the review's I4): sheltered behind the closed west door, one zombie at 2.7 tiles outside it: the
    hold breaks (`near`), no way out, one held: the Fight, kept to the building's doorway and inside (`only` empty
    here), so nothing is sent: no walk out through the door to it."""
    r, sv = make(tmp_path)
    me = sheltered(r, sv)
    for i in (2, 3):
        r.event("zombie_dead", id=i)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 109.8, 200.5, me=me)])
    n = len(r.acts.history)
    assert tick(r, sv) is None and len(r.acts.history) == n
    assert sv.mode == "fight" and sv.fight.only == set() and threat_why(tmp_path)["breach"] == "near"


def test_a_dropped_exit_walk_with_nothing_left_unarmed_stops_and_holds(tmp_path):
    """Fix round 1 (G2, M4): the doorways' doors broken (no door record, so nothing to adopt), the south one with a
    solid square past it (skipped, I1): the north walk stalls 1.0 s and is dropped; unarmed with no way out, the flee
    sends one `Stop` for the still-running walk and then holds, `trapped`."""
    from .test_policies import two_door_house
    r, sv = make(tmp_path)
    sqs = [q for q in two_door_house() if q["x"] < 115] + [square(111, 204, solid=True)]
    for q in sqs:
        q["door"] = None
    r.scan(sqs)
    me = (111.5, 201.5)
    east = [zombie(1, 116.0, 201.2, me=me), zombie(2, 115.8, 201.9, me=me), zombie(3, 115.5, 201.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=east, weapon=None)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 198.5, "gait": "run"})
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    for _ in range(2):
        r.advance(0.5)
        r.frame(x=me[0], y=me[1], zombies=east, weapon=None)
        tick(r, sv)
    assert r.cmd() == ("stop", {}) and threat_why(tmp_path)["trapped"] == 1


# ================================================================ survival 2 fix round 2 (the re-review's G4)
def wall_thumper(boxed):
    """`closed_room` with the player at (102.5, 200.4) inside its north wall and zombie 1 outside it at (102.5, 199.1),
    1.3 tiles off, its line blocked by the wall; `boxed`, the zombie's open neighbours solid (no reposition square)."""
    sqs = closed_room()
    if boxed:
        sqs += [square(x, y, solid=True) for x, y in ((101, 198), (102, 198), (103, 198), (101, 199), (103, 199))]
    return sqs


def test_a_zombie_at_1_3_tiles_behind_a_blocked_line_is_no_corner_and_the_tick_ends(tmp_path):
    """G4, the recursion probe: e42a7efb cornered on it, freed its mark and re-pinned it after every mark until a
    RecursionError (the driver loop's catch-all would end the session). It is no corner's target (not `in_reach`);
    the broken hold's Fight marks it unreachable once and sends nothing at it."""
    r, sv = make(tmp_path)
    r.scan(wall_thumper(boxed=True))
    me = (102.5, 200.4)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 102.5, 199.1, me=me)])
    assert P.line_to(r.world, r.world.zombies[1]) is False and not P.in_reach(r.world, r.world.zombies[1], 1.5)
    tick(r, sv)
    assert "cornered" not in threat_why(tmp_path) and sv.cornered is None
    assert all(a.type != "attack" for a in r.acts.history) and 1 in sv.unreachable


def test_a_point_blank_fight_never_re_pins_a_zombie_it_marked_behind_a_blocked_line(tmp_path):
    """G4, the recursion and the walk probes on the Fight itself (`mark_free_r` 1.5, `point_blank`): boxed, the mark
    ends the choose with no command; open, the one reposition walk goes, and after its second blocked read the mark
    holds: no walk re-sent each tick."""
    for boxed in (True, False):
        d = tmp_path / str(boxed)
        d.mkdir()
        r = Rig(d)
        r.scan(wall_thumper(boxed))
        me = (102.5, 200.4)
        r.frame(x=me[0], y=me[1], zombies=[zombie(1, 102.5, 199.1, me=me)])
        f = P.Fight(r.world, r.acts, r.clock, target=1)
        f.point_blank, f.mark_free_r = True, 1.5
        if boxed:
            assert f.step() is None and 1 in f.unreachable and r.acts.history == []
            continue
        f.step()
        assert r.cmd()[0] == "walkTo" and f.repositioned
        r.answer()
        r.frame(x=me[0], y=me[1], zombies=[zombie(1, 102.5, 199.1, me=me)])
        for _ in range(3):
            assert f.step() is None
            r.frame(x=me[0], y=me[1], zombies=[zombie(1, 102.5, 199.1, me=me)])
        assert [a.type for a in r.acts.history] == ["walkTo"] and 1 in f.unreachable


def test_an_id_marked_in_a_choose_is_never_freed_within_it(tmp_path):
    """G4: the recursion's guard: an id marked during the running choose stays skipped whatever `mark_free_r` frees;
    the next choose starts clean."""
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(7, 100.8, 200.0)])
    f = P.Fight(r.world, r.acts, r.clock)
    f.mark_free_r = 1.5
    f.unreachable[7] = r.clock() + 20.0
    assert f.blocked() == set()                                   # in reach at 0.8: freed
    f._mark_unreachable(7)
    assert f.blocked() == {7}
    f.choose()
    assert f._marked_now == set()


def test_e2_at_line_164_with_a_third_zombie_held_the_trapped_fight_answers(tmp_path):
    """The re-review's minor: line 164's own test passes with `_trapped_fight` off (the broken hold's one-or-two
    fallback fights there). With a third held zombie behind the bathroom's walls in the hall, that fallback is out
    (`many`); no way out and nothing to adopt: the trapped fight (G3) takes the nearest, 12839."""
    w = e2_world(164)
    w.zombies[99999] = dict(zombie(99999, 10744.5, 10633.5), seenWallMs=w.frame_wall_ms)
    held = [z for z in w.zombies.values() if z.get("x") is not None and P.zdist(w, z) <= P.DISENGAGE_R]
    assert len(held) == 3 and all(P.line_to(w, z) is False for z in held)
    r = Rig(tmp_path)
    sv = Survive(w, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.mode, sv.flee = "flee", P.Flee(w, r.acts, r.clock)
    sv.closing = (2, 5.626)
    sv.tick(w, r.acts)
    assert sv.mode == "fight" and sv.fight.target == 12839 and threat_why(tmp_path)["fight"] is True


# ================================================================ survival 3 (ruling P23-AM): E3's group
# E3 (e_day_3-20261028-153631) died at game minute 600: a fight and a `many` shelter flee superseded each other four
# times in 8 s (decision.log lines 230-245), then the shelter's enter walk stood while the group closed (247-275).
def test_the_survival_3_constants():
    assert (S.FLIP_MIN_S, S.GROUP_R_N) == (5.0, 3)
    assert (P.WALK_STALL_S, P.SPRINT_END, P.SPRINT_MAX_S) == (1.0, 0.5, 20.0)


def e3_replay(tmp_path, first_line, last_line, setup=None):
    """E3's decision lines `first_line`..`last_line` replayed (`run_replay`)."""
    return run_replay(E3, tmp_path, first_line, last_line, setup)


def run_replay(run, tmp_path, first_line, last_line, setup=None):
    """A run's decision lines `first_line`..`last_line` replayed through a fresh Survive on the recorded worlds, its
    clock the recorded walls: a steer leg still running FLEE_S after its send is answered `done` (the Lua's steer ends
    at its seconds), a walk is left running. `setup(r, sv, w)` runs before the first tick. Returns the Rig, the
    Survive and {line: (decision row, Action sent or None)}."""
    r = Rig(tmp_path)
    sv, out = None, {}
    for line, wall, w in run_worlds(run, range(first_line, last_line + 1)):
        r.t["now"] = wall
        if sv is None:
            sv = Survive(w, r.acts, str(tmp_path / "decision.log"), r.clock)
            if setup is not None:
                setup(r, sv, w)
        cur = r.acts.current
        if cur is not None and cur.type == "steer" and wall - cur.sent_wall >= P.FLEE_S:
            r.answer()
        a = sv.tick(w, r.acts)
        out[line] = (last(tmp_path), a)
    return r, sv, out


def e3_world_at_seq(seq, run=E3):
    """A World of a run's state.log (E3's by default) up to the line of `seq`."""
    from agent.base.world import World
    w = World()
    for ln in _run_lines(run)[0]:
        w.apply(ln)
        if ln.get("seq", 0) >= seq:
            return w
    raise AssertionError("no line at seq %d" % seq)


def test_e3_building_2s_bedroom_door_is_no_exterior_door_and_its_kitchen_and_front_doors_are(tmp_path):
    """The coordinator's amendment 5 (E3's write-up, concern 2): E3's kept map at seq 2300. The door (10725, 10629)
    stands on the bedroom square's west edge (edgeW, open, blockW False), joining it to the corridor (10724, 10629);
    its north edge is the bedroom's wall (blockN True), the outdoor square across it the old rule's "exterior"
    neighbour. The bathroom's (10725, 10635) and the closet's (10723, 10637) doors join rooms too (edgeW to the
    corridor, the kitchen); the hall's west door (10721, 10628) leads to a closet. Building 2's exterior doors: the
    kitchen's south door (10721, 10638), open and unlocked, kept on the outdoor square below the kitchen's (10721,
    10637) with `building` None as the live scan gives it (fix round 1, R2: invisible to `doors_of(2)` until then),
    ranked first, its approach the door square itself; and the hall's north door (10722, 10627), locked, its approach
    (10722, 10626) outside it."""
    from agent.base.planner import night as N
    w = e3_world_at_seq(2300)
    assert w.map[(10721, 10638, 0)].get("building") is None and w.map[(10721, 10638, 0)]["door"]["open"]
    assert w.door_way((10725, 10629, 0)) is None and N.approach_square(w, (10725, 10629, 0)) is None
    assert N.exterior_doors(w, 2, 0) == [(10721, 10638, 0), (10722, 10627, 0)]
    assert w.door_way((10721, 10638, 0)) == ((10721, 10637, 0), (10721, 10638, 0))
    assert w.door_way((10722, 10627, 0)) == ((10722, 10627, 0), (10722, 10626, 0))
    assert N.approach_square(w, (10722, 10627, 0)) == (10722, 10626, 0)
    assert N.shelter_plan(w, 2, door=(10725, 10629, 0)) is None
    assert N.shelter_plan(w, 2, door=(10721, 10638, 0))["inside"] == (10721, 10637, 0)
    assert [e["door"] for e in N.exits(w, 2, 0) if e["door"] is not None] == [(10722, 10627, 0)]


@functools.lru_cache(maxsize=1)
def _e3_sequential():
    """E3's lines 230-284 through one Survive (`e3_replay`), shared by the sequential tests."""
    d = tempfile.mkdtemp()
    import pathlib
    r, sv, out = e3_replay(pathlib.Path(d), 230, 284)
    return [a for a in r.acts.history], {ln: (row, a) for ln, (row, a) in out.items()}


def test_e3_after_the_first_many_flee_no_fight_walk_supersedes_it_while_the_group_is_held():
    """Ruling P23-AM 1 on E3's lines 230-253 through one Survive (the recorded inputs, a steer leg answered `done`
    FLEE_S after its send): line 230 engages 14930 (one threat); at 231 four are held and the `many` flee takes the
    kitchen door's approach (amendment 5 and fix round 1's R2: building 2's open south door) at a sprint (rule 3).
    The recorded run turned back to fight at 234, 238 and 242 (a33, a35, a37, each superseding the flee's walk) and
    fled again at 235, 239 and 244; now no fight goes: where the held count stays over MAX_FIGHT or the nearest is
    within DANGER_R the reason stays `many`, two held beyond DANGER_R read `held`, and one held beyond DANGER_R is
    kept by the running shelter step (`steps`). One walk, never superseded until rule 2 drops it at 254. Named change,
    ruling P24-A (a): at line 230 four zombies are listed within LISTED_R (one held within DANGER_R), so the `many`
    flee and its approach walk go there (`listed` 4), with no fight walk first."""
    sent, out = _e3_sequential()
    why230 = out[230][0]["inputs"]["branches"]["threat"]
    assert why230["flee"] == "many" and why230["listed"] == 4 and "fight" not in why230
    assert out[230][1].args == {"x": 10721.5, "y": 10638.5, "gait": "sprint"}
    for line in range(230, 254):
        d = out[line][0]
        why = d["inputs"]["branches"]["threat"]
        assert "fight" not in why and why["shelter"] == 2 and why["step"] == "approach", line
        assert (line == 230) is d["sent"], line
        held, near = d["inputs"]["held"], d["inputs"]["nearest"]
        if held > S.MAX_FIGHT or near <= S.DANGER_R or "listed" in why:   # P24-A (a): or four listed within 12
            assert why["flee"] == "many", line
        elif held == 1:
            assert why["flee"] == "steps", line
    assert {out[ln][0]["inputs"]["branches"]["threat"]["flee"] for ln in (238, 242)} == {"steps"}
    assert out[234][0]["inputs"]["branches"]["threat"]["listed"] == 5   # P24-A (a): `steps` before, now `many`
    d, a = out[254]
    assert a.type == "steer" and d["inputs"]["branches"]["threat"]["ended"] == "stalled"


def test_e3_a_group_gathering_on_a_walk_corner_is_steered_from_not_fought_standing():
    """Fix round 1, G1, on E3's lines 254-284 through the same one Survive. Named change, ruling P23-AP 2: fix round
    1's `walk` corner took 14926 alone at 258 (1.08 tiles) with four held, and ended for the steer at 271 (three
    within CORNERED_R); now four held are a group (GROUP_HOLD_N) from 258: no corner, the running sprint leg is held
    (`group` "hold"), and at 260 (the leg's FLEE_S out) the next sprint leg goes. The recorded frames never move the
    player, so that leg stands, and at 263, WALK_STALL_S after it with 14918 in reach, R1 reads it stuck: the `stuck`
    corner's attack on 14918 (0.55 tiles), as rule 4 rules after a stuck leg; no attack before it. Named change,
    ruling P24-A (a): no fight walk at 230, so the running leg is a2 (a3 before)."""
    sent, out = _e3_sequential()
    for line in (258, 259):
        d, a = out[line]
        why = d["inputs"]["branches"]["threat"]
        assert a is None and why["group"] == "hold" and why["holding"] == "a2" and "cornered" not in why, line
    d, steer = out[260]
    why = d["inputs"]["branches"]["threat"]
    assert steer.type == "steer" and steer.args["gait"] == "sprint" and why["group"] == "hold"
    assert "cornered" not in why and why["flee"] == "many"
    assert all(not (a.type == "attack" and out[254][0]["wall"] <= a.sent_wall < out[263][0]["wall"]) for a in sent)
    d, a = out[263]
    assert a.type == "attack" and a.args == {"targetId": 14918} and d["inputs"]["branches"]["threat"]["cornered"]
    assert d["wall"] - out[260][0]["wall"] >= P.WALK_STALL_S and steer.state == "sent"   # R1: stuck while it ran


def test_a_walk_corner_on_one_zombie_ends_when_two_more_come_within_cornered_r(tmp_path):
    """Fix round 1, G1, the unit case: a goal walk outside, zombie 1 at 1.2 tiles: the `walk` corner attacks it; two
    more come within CORNERED_R: the corner ends and the flee steers (a sprint), no attack sent."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 99.3, 201.5, me=me)])
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1}) and sv.corner_kind == "walk"
    r.fake.answer({"attack": ["accepted"]})
    r.pump()
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me))
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a is not None and a.type == "steer" and a.args["gait"] == "sprint" and "cornered" not in w
    assert sv.cornered is None and sv.mode == "flee" and w["flee"] == "many"


def e3_recorded_plan(w):
    """The shelter plan E3 ran at line 247 (building 2 kept to the bedroom door (10725, 10629), its `inside` the
    corridor square (10724, 10629), at its `enter` step), kept by hand: amendment 5 no longer makes it."""
    rooms = [sq for sq in w.interiors()[2] if sq[2] == 0]
    return {"building": 2, "doors": [(10725, 10629, 0)], "door_i": 0, "rooms": rooms, "inside": (10724, 10629, 0),
            "step": "enter", "retries": 0, "near": 0.0}


def e3_on_the_enter_step(r, sv, w):
    """`e3_replay`'s setup: the `many` flee E3 ran, its Flee at the recorded plan's `enter` step."""
    sv.mode, sv.flee_many = "flee", True
    sv.flee = P.Flee(w, r.acts, r.clock, shunned=sv.night.shunned)
    sv.flee.plan, sv.flee.picked = e3_recorded_plan(w), True


def test_e3_the_enter_walk_standing_with_a_threat_within_danger_r_is_dropped_and_a_sprint_steer_follows(tmp_path):
    """Rulings P23-AM 2 and 3 on E3's lines 247-255, the recorded plan at its `enter` step (`e3_recorded_plan`): the
    enter walk to (10724.5, 10629.5) goes at a sprint (`many`, endurance 0.97). The frame moves the player west until
    line 251 (125.09 s), then it stands; at 253 (0.98 s still) no held threat is within DANGER_R, at 254 (1.42 s)
    14918 is at 5.94 tiles: the walk is dropped (`stalled`), the plan with it for the episode, and the steer goes at
    once, a sprint (the group beyond SPRINT_R). The recorded walk stood until 275, the group at 0.48 tiles."""
    r, sv, out = e3_replay(tmp_path, 247, 255, setup=e3_on_the_enter_step)
    enter = out[247][1]
    assert enter.args == {"x": 10724.5, "y": 10629.5, "gait": "sprint"}
    for line in range(248, 254):
        assert out[line][1] is None and out[line][0]["inputs"]["branches"]["threat"]["holding"] == enter.aid, line
    d, steer = out[254]
    why = d["inputs"]["branches"]["threat"]
    assert steer.type == "steer" and steer.args["gait"] == "sprint" and why["ended"] == "stalled"
    assert why["flee"] == "many" and why["shelter"] is None and 5.5 < d["inputs"]["nearest"] <= S.DANGER_R
    still = d["wall"] - out[251][0]["wall"]                  # the frame stands from line 251 (125.09 s)
    assert P.WALK_STALL_S <= still < 1.5 and out[253][0]["inputs"]["nearest"] > S.DANGER_R
    assert sv.flee.plan is None and sv.flee.picked
    assert out[255][1] is None and out[255][0]["inputs"]["branches"]["threat"]["holding"] == steer.aid


@pytest.mark.parametrize("line, want", [(260, ("steer", "hold")), (271, ("steer", "hold"))])
def test_e3_at_melee_range_on_the_shelter_walk_the_corner_answers(tmp_path, line, want):
    """The coordinator's amendment 6 (E3's write-up, concern 4): lines 260-275 passed with a zombie within 1.5 tiles
    and no corner, the character on the plan's enter walk (no steer leg, no room square). Now the corner is judged on
    every threat tick whatever runs: at line 271 (three within CORNERED_R, no stuck leg) rule 4 steers, a sprint.
    Named change, ruling P23-AP 2: at line 260 (14926 at 0.51 tiles, one within CORNERED_R) fix round 1 attacked;
    five are held there, a group (GROUP_HOLD_N), so the group steer drops the walk there too."""
    def setup(r, sv, w):
        e3_on_the_enter_step(r, sv, w)
        sv.flee.threats, sv.flee.many = [z for z in w.zombies.values() if z.get("x") is not None], True
        sv.flee.step()
        assert r.cmd() == ("walkTo", {"x": 10724.5, "y": 10629.5, "gait": "run"})   # 0.51 tiles: within SPRINT_R
    r, sv, out = e3_replay(tmp_path, line, line, setup=setup)
    d, a = out[line]
    why = d["inputs"]["branches"]["threat"]
    assert a is not None and a.type == want[0] and why["group"] == want[1] and d["inputs"]["held"] >= S.GROUP_HOLD_N
    assert a.args["gait"] == "sprint" and "cornered" not in why and why["flee"] == "many"
    assert why["ended"] == "pre-empted" and sv.flee.plan is None and sv.flee.picked   # the walk dropped


def many_yard(r, me=(100.5, 201.5), endurance=1.0, d=4.0):
    """The open yard, the player at `me`, three zombies `d` tiles west (a `many` flee)."""
    r.scan(open_yard())
    zs = [zombie(1, me[0] - d, me[1], me=me), zombie(2, me[0] - d, me[1] + 0.8, me=me),
          zombie(3, me[0] - d, me[1] - 0.8, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs, endurance=endurance)
    return zs


@pytest.mark.parametrize("endurance, gait", [(1.0, "sprint"), (0.51, "sprint"), (0.5, "run"), (0.3, "run")])
def test_a_many_flee_with_the_nearest_at_four_tiles_sprints_while_endurance_reads_above_sprint_end(
        tmp_path, endurance, gait):
    """Ruling P23-AM 3: three at 4 tiles, nothing to shelter in: the steer goes at a sprint (once a run beyond
    SPRINT_R) while `stats.endurance` reads above SPRINT_END."""
    r, sv = make(tmp_path)
    many_yard(r, endurance=endurance)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and r.cmd()[1]["gait"] == gait and threat_why(tmp_path)["flee"] == "many"


def test_a_pair_flee_at_four_tiles_still_runs(tmp_path):
    """Rule 3 is the group's: a `pair` flee (two at health 50) beyond SPRINT_R runs."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 96.5, 201.5, me=me), zombie(2, 96.5, 202.3, me=me)], health=50.0)
    tick(r, sv)
    assert threat_why(tmp_path)["flee"] == "pair" and r.cmd()[1]["gait"] == "run"


def test_with_no_endurance_read_a_many_flee_sprints_for_sprint_max_s_then_runs(tmp_path):
    """Rule 3's fallback: a frame with no endurance: the steer sprints from the episode's first sprint for
    SPRINT_MAX_S wall seconds, then runs."""
    r, sv = make(tmp_path)
    zs = many_yard(r)
    gaits = []
    for _ in range(9):
        r.world.stats = dict(r.world.stats, endurance=None)
        tick(r, sv)
        gaits.append(r.cmd()[1]["gait"])
        r.answer()
        r.advance(3.0)
        r.frame(x=100.5, y=201.5, zombies=zs)
    assert gaits == ["sprint"] * 7 + ["run"] * 2       # sprints at 0, 3, ... 18 s; runs at 21 and 24


def test_a_many_flee_whose_count_falls_to_one_within_danger_r_stays_a_flee_until_it_is_beyond(tmp_path):
    """Ruling P23-AM 1: two of the three die; the last at 4 tiles at full health. HEAD turned to fight it at once
    (one held, health over the margin); the `many` episode reads the hold radius and the nearest within DANGER_R, so
    it steers on; with that zombie at 7 tiles the fight resumes."""
    r, sv = make(tmp_path)
    zs = many_yard(r)
    tick(r, sv)
    r.answer()
    for i in (2, 3):
        r.event("zombie_dead", id=i)
    r.frame(x=100.5, y=201.5, zombies=zs[:1])
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "many" and sv.mode == "flee"
    r.answer()
    r.frame(x=100.5, y=201.5, zombies=[zombie(1, 93.5, 201.5, me=(100.5, 201.5))])
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 93.5, "y": 201.5, "gait": "run"}) and threat_why(tmp_path)["fight"] is True


def test_a_fight_walk_never_supersedes_a_flee_leg_sent_under_flip_min_s_ago(tmp_path):
    """Ruling P23-AM 1, FLIP_MIN_S: the `many` steer runs; one second in, two have died and the last stands 7 tiles
    off: the hysteresis would fight, but the leg is held (`flip`, nothing sent); once the leg ended the fight's walk
    goes."""
    r, sv = make(tmp_path)
    many_yard(r)
    tick(r, sv)
    leg = r.acts.history[-1]
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    r.advance(1.0)
    for i in (2, 3):
        r.event("zombie_dead", id=i)
    far = [zombie(1, 93.5, 201.5, me=(100.5, 201.5))]
    r.frame(x=100.5, y=201.5, zombies=far)
    assert tick(r, sv) is None
    w = threat_why(tmp_path)
    assert w["flee"] == "flip" and w["holding"] == leg.aid and sv.mode == "flee"
    r.fake.answer({"steer": ["done"]})
    r.pump()
    r.frame(x=100.5, y=201.5, zombies=far)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 93.5, "y": 201.5, "gait": "run"}) and sv.mode == "fight"


def test_the_flee_wins_the_tie_a_fight_walk_half_a_second_old_is_superseded_by_the_group(tmp_path):
    """FLIP_MIN_S the other way: the flee is never held back for a fight's walk (it is the retreat)."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 96.5, 201.5, me=me)])
    tick(r, sv)
    assert r.cmd()[0] == "walkTo" and sv.mode == "fight"
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    r.advance(0.5)
    many_yard(r)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "many"


def stall_shelter(r, sv):
    """`shelter_world` with the closed west door and `group()` at 3 tiles: the `many` flee's approach walk sent and
    accepted."""
    from .test_night import CLOSED
    shelter_world(r, CLOSED)
    r.frame(x=100.0, y=201.5, zombies=group())
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 201.5, "gait": "sprint"})
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    return r.acts.history[-1]


def test_a_shelter_walk_that_stands_step_stall_s_with_a_threat_within_danger_r_is_dropped_and_steered(tmp_path):
    """Ruling P23-AM 2: the approach walk leaves the player where it was for 1.0 s with the group at 3 tiles: dropped
    (`stalled`), the plan with it for the episode (not shunned in the night's store), and the steer sent at once."""
    r, sv = make(tmp_path)
    walk = stall_shelter(r, sv)
    for _ in range(2):
        r.advance(0.5)
        r.frame(x=100.1, y=201.5, zombies=group())
        tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd()[0] == "steer" and w["ended"] == "stalled" and w["shelter"] is None
    assert sv.flee.plan is None and sv.flee.picked and sv.night.shunned == {} and walk.state == "accepted"


def test_a_shelter_walk_that_moves_or_stands_with_no_threat_within_danger_r_is_kept(tmp_path):
    """Rule 2's limits: a walk that moved 0.5 tiles in each half second is kept; one that stands with the group held
    at 7 to 8 tiles (the `many` episode holds them) waits the Lua's own stuck time."""
    r, sv = make(tmp_path)
    walk = stall_shelter(r, sv)
    for k in range(1, 5):
        r.advance(0.5)
        me = (100.0 + 0.5 * k, 201.5)
        r.frame(x=me[0], y=me[1], zombies=group(0.0, me))
        assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == walk.aid
    me = (102.0, 201.5)
    for _ in range(6):
        r.advance(0.5)
        r.frame(x=me[0], y=me[1], zombies=group(-3.5, me))
        assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == walk.aid
    assert threat_why(tmp_path)["flee"] == "many" and sv.flee.plan is not None


def test_an_open_step_stands_at_the_door_unstalled_but_its_walk_to_the_door_stalls(tmp_path):
    """Rule 2 on `open`: the Lua's interact walks until the player is within one square of the door, then queues the
    open; standing there 2 s is the open, never a stall. An open sent from 3 squares off whose walk stands 1 s with a
    threat within DANGER_R is dropped."""
    for far in (False, True):
        d = tmp_path / str(far)
        d.mkdir()
        r = Rig(d)
        sv = Survive(r.world, r.acts, str(d / "decision.log"), r.clock)
        stall_shelter(r, sv)
        r.fake.answer({"walkTo": ["done"]})
        r.pump()
        me = (108.5, 201.5) if far else (111.5, 201.5)
        r.frame(x=me[0], y=me[1], zombies=group(8.0, me))
        tick(r, sv)
        assert r.cmd()[0] == "interact" and r.cmd()[1]["kind"] == "open"
        r.fake.answer({"interact": ["accepted"]})
        r.pump()
        zs = [zombie(1, me[0] - 3.0, me[1], me=me)] + group(8.0, me)[1:]
        for _ in range(4):
            r.advance(0.5)
            r.frame(x=me[0], y=me[1], zombies=zs)
            tick(r, sv)
        w = last(d)["inputs"]["branches"]["threat"]
        if far:
            assert r.cmd()[0] == "steer" and w["ended"] == "stalled"
        else:
            assert r.cmd()[0] == "interact" and w["step"] == "open" and "holding" in w


def group_at_melee(me):
    return [zombie(1, me[0] - 1.0, me[1] + 0.7, me=me), zombie(2, me[0], me[1] + 1.1, me=me),
            zombie(3, me[0] + 0.9, me[1] + 0.8, me=me)]


@pytest.mark.parametrize("room", [False, True])
def test_three_within_cornered_r_after_a_leg_that_moved_are_steered_from_not_fought(tmp_path, room):
    """Ruling P23-AM 4: a `many` steer leg moved two tiles and three zombies followed within CORNERED_R: the branch
    steers again (a sprint, away from the group), never stands to swing outside. Named change, survival 4 fix round 1
    (R3): on the closed room's square (no way out, nothing to adopt) no leg can move, so the corner swings at once
    (iteration 3 steered there, one leg into the walls first)."""
    r, sv = make(tmp_path)
    r.scan(closed_room())
    me = (102.5, 205.6)
    zs = [zombie(1, 101.5, 208.5, me=me), zombie(2, 102.5, 208.7, me=me), zombie(3, 103.5, 208.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "many"
    r.answer()
    me = (102.5, 203.5) if room else (99.0, 204.6)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me))
    assert P.on_room(r.world) is room
    a = tick(r, sv)
    w = threat_why(tmp_path)
    if room:
        assert a is not None and a.type == "attack" and w["cornered"] == 2 and "group" not in w
        assert sv.corner_kind == "inside"
        return
    assert a is not None and a.type == "steer" and a.args["gait"] == "sprint" and len(r.acts.history) == 2
    assert "cornered" not in w and sv.mode == "flee"
    assert all(a.type != "attack" for a in r.acts.history) and w["flee"] == "many"


def test_three_within_cornered_r_after_a_stuck_leg_are_fought(tmp_path):
    """Rule 4's other side: the leg moved 0.1 tiles (stuck) with three within CORNERED_R: the corner's attack."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    zs = [zombie(1, 97.5, 201.5, me=me), zombie(2, 97.5, 202.5, me=me), zombie(3, 97.5, 200.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    r.answer()
    me = (100.6, 201.5)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me))
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 2}) and threat_why(tmp_path)["cornered"] == 2   # 1.1 tiles, the nearest
    attack = r.acts.history[-1]
    r.fake.answer({"attack": ["accepted"]})
    r.pump()
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me))
    assert tick(r, sv) is None                         # fix round 1, G1: a `stuck` corner is kept against the group
    assert threat_why(tmp_path)["cornered"] == 2 and threat_why(tmp_path)["holding"] == attack.aid


def test_a_new_flee_episode_after_a_many_one_ended_starts_without_its_many(tmp_path):
    """Rule 1's episode ends with the episode: a `many` flee whose group is gone (none held) leaves no `many` behind;
    the next flee, a `pair` at health 50, runs (no group sprint) and with one left at 4 tiles reads `held`."""
    r, sv = make(tmp_path)
    many_yard(r)
    tick(r, sv)
    assert threat_why(tmp_path)["flee"] == "many" and sv.flee_many
    r.answer()
    for i in (1, 2, 3):
        r.event("zombie_dead", id=i)
    r.frame(x=100.5, y=201.5, zombies=[])
    tick(r, sv)
    assert sv.mode is None and not sv.flee_many
    me = (100.5, 201.5)
    two = [zombie(4, 96.5, 201.5, me=me), zombie(5, 96.5, 202.3, me=me)]
    r.frame(x=me[0], y=me[1], zombies=two, health=50.0)
    tick(r, sv)
    assert threat_why(tmp_path)["flee"] == "pair" and r.cmd()[0] == "steer" and r.cmd()[1]["gait"] == "run"
    r.answer()
    r.event("zombie_dead", id=5)
    r.frame(x=me[0], y=me[1], zombies=two[:1], health=50.0)
    tick(r, sv)
    assert threat_why(tmp_path)["flee"] == "held" and r.cmd()[1]["gait"] == "run"


def test_a_group_at_melee_range_never_re_steers_over_its_own_running_leg_while_it_moves(tmp_path):
    """Amendment 6 with rule 4: three come within CORNERED_R while the `many` steer leg runs and moves the player
    0.6 tiles a half second: the leg is kept (no new steer each tick, `give_way` drops only a walk). Fix round 1's
    R1: once the running leg has left the player within STUCK_MOVE for WALK_STALL_S with the group in reach, it reads
    stuck and the corner attacks before the leg's FLEE_S is out (E3's a40 stood its 3 s, health 93.7 to 68.3)."""
    r, sv = make(tmp_path)
    many_yard(r)
    tick(r, sv)
    leg = r.acts.history[-1]
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    me = (100.5, 201.5)
    for _ in range(3):
        r.advance(0.5)
        me = (me[0] + 0.6, me[1])
        r.frame(x=me[0], y=me[1], zombies=group_at_melee(me))
        assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == leg.aid
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me))
    assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == leg.aid      # 0.5 s unmoved: kept
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me))
    tick(r, sv)                                                                     # 1.0 s unmoved: stuck
    assert r.cmd() == ("attack", {"targetId": 2}) and threat_why(tmp_path)["cornered"] == 2
    assert sv.corner_kind == "stuck" and leg.state == "accepted"


def test_an_unmoved_running_leg_with_no_threat_within_cornered_r_runs_its_course(tmp_path):
    """R1's limit: the leg stands 2 s with the group 3 to 4 tiles off: not stuck (no corner, no re-steer)."""
    r, sv = make(tmp_path)
    many_yard(r)
    tick(r, sv)
    leg = r.acts.history[-1]
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    for _ in range(4):
        r.advance(0.5)
        many_yard(r)
        assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == leg.aid
    assert sv.flee.stuck() is False


def test_a_running_fight_keeps_its_pin_when_another_zombie_comes_within_cornered_r(tmp_path):
    """Amendment 6 leaves a running fight alone (Task 10's pin): the Fight walks to zombie 1 at 3 tiles; zombie 2
    comes within 1.2 tiles behind: no corner, the walk to 1 is held."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 103.5, 201.5, me=me)])
    tick(r, sv)
    walk = r.acts.history[-1]
    assert walk.type == "walkTo" and sv.mode == "fight" and sv.fight.target == 1
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 103.5, 201.5, me=me), zombie(2, 99.3, 201.5, me=me)])
    assert tick(r, sv) is None
    assert "cornered" not in threat_why(tmp_path) and sv.fight.target == 1 and sv.cornered is None


def test_a_walk_corner_never_swings_at_a_marked_zombie_or_through_a_blocked_line(tmp_path):
    """Amendment 6's `walk` corner keeps run 1's lesson: on a goal walk outside (no flee, no stuck leg, no room
    square), a zombie at 0.7 tiles behind the wall the map reads, or one at 0.8 marked unreachable, is no corner (the
    stuck and inside corners keep survival 2's point blank and marks aside); the same zombie unmarked is one."""
    r, sv = make(tmp_path)
    r.scan(behind_wall_n())
    me = (100.5, 200.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(7, 100.5, 199.8, me=me)])
    assert P.line_to(r.world, r.world.zombies[7]) is False and sv.mode is None
    assert sv._cornered([r.world.zombies[7]], False) is None
    r.frame(x=me[0], y=me[1], zombies=[zombie(7, 100.5, 201.3, me=me)])
    sv.unreachable[7] = r.clock() + 20.0
    assert P.line_to(r.world, r.world.zombies[7]) is True and sv._cornered([r.world.zombies[7]], False) is None
    sv.unreachable.clear()
    assert sv._cornered([r.world.zombies[7]], False) == 7 and sv.corner_kind == "walk"


def test_a_many_flee_s_running_shelter_walk_keeps_the_flee_past_flip_min_s(tmp_path):
    """Ruling P23-AM 1's `steps` (my addition, the report's concern 1): the `many` flee's approach walk runs 6 s,
    the player moving; two of the group die and the last stands 7.5 tiles off: past FLIP_MIN_S the walk is still the
    flee's (`steps`), never superseded by a fight walk."""
    r, sv = make(tmp_path)
    walk = stall_shelter(r, sv)
    for k in range(1, 13):
        r.advance(0.5)
        me = (100.0 + 0.6 * k, 201.5)
        if k == 6:
            for i in (2, 3):
                r.event("zombie_dead", id=i)
        zs = group(0.0, me) if k < 6 else [zombie(1, me[0] - 7.5, 201.5, me=me)]
        r.frame(x=me[0], y=me[1], zombies=zs)
        assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == walk.aid, k
    assert threat_why(tmp_path)["flee"] == "steps" and r.t["now"] - walk.sent_wall > S.FLIP_MIN_S


# ================================================================ survival 4 (ruling P23-AP): E4's stuck area and group
# E4 (e_day_4-20261028-173649) died at game minute 627: twelve walks failed stuck from one square north of a locked gate
# (21.85 game minutes), a `walk` corner held 35 ticks while the group formed outside 1.5 tiles (decision.log lines
# 447-481), and a steer leg aimed west at line 440 ran into two zombies listed after it was aimed.
def test_the_survival_4_constants():
    assert (S.GROUP_R_N, S.GROUP_NEAR_R, S.GROUP_HOLD_N, S.STUCK_RETRY_S) == (3, 3.0, 4, 2.0)


def test_e4_the_third_proposal_from_the_stuck_square_is_no_walk_across_the_fence_row(tmp_path):
    """Ruling P23-AP 1 on E4's lines 86-115 through one Survive (the recorded worlds, the character standing on
    (10732.84, 10641.54) north of the locked gate (10732, 10642) throughout; building 2's containers read looted, as the
    loot goal that ended `done` at line 54 left them; a scan answered done, a walk failed `stuck` 6 s after its send,
    as a13-a24 ended 5.994-5.996 s after their accepts). The first two proposals are the record's rows 3 and 4,
    (10738, 10642) and (10742, 10642), both across the fence row (their lines blocked); each fails unmoved, a stuck
    pair from (10732, 10641). The third (the record's row 5 walked to (10742, 10641), across the fence line on the west
    edges of x 10735) is ExploreToward (10734, 10630): the place rescanned first, then a walk north whose straight line
    is clear and which the flood from the player reaches."""
    r = Rig(tmp_path)
    sv, proposals, sends = None, [], []
    for line, wall, w in run_worlds(E4, range(86, 116)):
        r.t["now"] = wall
        if sv is None:
            sv = Survive(w, r.acts, str(tmp_path / "decision.log"), r.clock)
            for k in list(w.containers):
                w.mark_looted(k)
        cur = r.acts.current
        if cur is not None and cur.type == "scan":
            r.answer()
        elif cur is not None and cur.type == "walkTo" and wall - cur.sent_wall >= 6.0:
            r.answer({"state": "failed", "reason": "stuck"})
        a = sv.tick(w, r.acts)
        why = last(tmp_path)["inputs"]["branches"]["goal"]
        if why.get("proposed"):
            proposals.append((line, why["proposed"], why["args"]))
        if a is not None:
            sends.append((line, a.type, a.args))
    me = (w.me["x"], w.me["y"])
    assert [p[1:] for p in proposals[:3]] == [("ExploreToward", {"x": 10738, "y": 10642}),
                                              ("ExploreToward", {"x": 10742, "y": 10642}),
                                              ("ExploreToward", {"x": 10734, "y": 10630})]
    assert proposals[2][0] == 113 and w.stuck_run["to"] == [(10738, 10642), (10742, 10642)]
    for x, y in ((10738, 10642), (10742, 10642), (10742, 10641)):
        assert not w.line_clear(me, (x + 0.5, y + 0.5)), (x, y)
    assert w.line_clear(me, (10734.5, 10630.5)) and w.reachable((10732, 10641, 0), (10734, 10630, 0))
    third = [s for s in sends if s[0] >= 113]
    assert third[:2] == [(113, "scan", {"r": 10}), (114, "walkTo", {"x": 10734, "y": 10630, "gait": "walk"})]
    assert all(s[2].get("y", 0) < 10642 for s in third if s[1] == "walkTo")


def e4_flee(r, sv, w):
    """`run_replay`'s setup for E4's last fight: the `many` flee episode E4 ran from line 412 (a fresh Flee)."""
    sv.mode, sv.flee_many = "flee", True
    sv.flee = P.Flee(w, r.acts, r.clock, shunned=sv.night.shunned)


def e4_flee_held(r, sv, w):
    """`run_replay`'s setup: E4's flee from line 412 as a fresh Flee whose episode is not `many` (P24-A (c)'s
    other side: a `walk` corner is taken outside a `many` episode)."""
    e4_flee(r, sv, w)
    sv.flee_many = False


def test_e4_in_the_many_episode_no_walk_corner_is_taken_and_the_stuck_corners_and_retries_follow(tmp_path):
    """Ruling P24-A (c) on E4's lines 447-462 through one Survive (the recorded worlds; the `many` flee E4 ran): at 447
    (19032 at 1.35 tiles) the `walk` corner yields to the running `many` episode (`yield` "many") and the flee's sprint
    leg goes. The recorded frames never move the player: at 450 the leg reads stuck (R1) with 19035 at 0.50 tiles, a
    `stuck` corner; its retry at 455 (four held, the nearest beyond POINT_BLANK_R, STUCK_RETRY_S on), the next
    `stuck` corner at 457 and the next retry at 462 (P23-AP 2)."""
    r, sv, out = run_replay(E4, tmp_path, 447, 462, setup=e4_flee)
    d, steer = out[447]
    why = d["inputs"]["branches"]["threat"]
    assert steer.type == "steer" and steer.args["gait"] == "sprint" and why["yield"] == "many"
    assert why["flee"] == "many" and "cornered" not in why
    d, a = out[450]
    why = d["inputs"]["branches"]["threat"]
    assert a.type == "attack" and why["cornered"] == 19035 and why["corner_kind"] == "stuck"
    for line in (453, 460):   # P24-A fix 1 (1): STUCK_RETRY_GROUP_S under the group (455 and 462 before)
        d, retry = out[line]
        assert retry.type == "steer" and d["inputs"]["branches"]["threat"]["group"] == "retry", line
    d, a = out[457]
    assert a.type == "attack" and d["inputs"]["branches"]["threat"]["corner_kind"] == "stuck"


def test_e4_the_walk_corner_ends_when_the_held_count_reaches_four_and_the_group_steer_goes(tmp_path):
    """Ruling P23-AP 2 on E4's lines 447-481 through one Survive (the recorded worlds; the flee E4 ran, read here as
    not `many`: named change, ruling P24-A (c), whose `many` episode takes no `walk` corner). Line
    447: 19032 at 1.35 tiles, 19035 at 2.54, 19030 at 6.69 (three held, two within GROUP_NEAR_R): the `walk` corner
    attacks 19032, as the record did. At line 453 19042 comes within the hold radius (9.81 tiles on the replay's frame;
    the record's line 454 read the held count 4): four held, a group (GROUP_HOLD_N), so the corner ends and the group
    sprint steer is sent, not the attack (the record held the corner to line 481, the held count rising to six). The
    recorded frames never answer the steer with movement: the leg read stuck (R1) is a `stuck` corner from line 457,
    and its retry (STUCK_RETRY_S, the nearest beyond POINT_BLANK_R) one more leg at 462."""
    r, sv, out = run_replay(E4, tmp_path, 447, 481, setup=e4_flee_held)
    d, a = out[447]
    assert a.type == "attack" and a.args == {"targetId": 19032} and d["inputs"]["branches"]["threat"]["cornered"]
    for line in range(448, 453):
        why = out[line][0]["inputs"]["branches"]["threat"]
        assert out[line][1] is None and why["cornered"] == 19032 and out[line][0]["inputs"]["held"] == 3, line
    d, steer = out[453]
    why = d["inputs"]["branches"]["threat"]
    assert d["inputs"]["held"] == S.GROUP_HOLD_N and why["group"] == "hold" and "cornered" not in why
    assert steer.type == "steer" and steer.args["gait"] == "sprint" and why["flee"] == "many"
    assert all(out[ln][1] is None for ln in range(454, 457))
    d, a = out[457]
    assert a.type == "attack" and d["inputs"]["branches"]["threat"]["cornered"] == 19032
    d, retry = out[460]   # P24-A fix 1 (1): four held, the leg at STUCK_RETRY_GROUP_S, point blank no bar (462 before)
    why = d["inputs"]["branches"]["threat"]
    assert retry.type == "steer" and why["group"] == "retry" and d["inputs"]["nearest"] <= P.POINT_BLANK_R
    assert S.STUCK_RETRY_GROUP_S <= d["wall"] - out[457][0]["wall"] < S.STUCK_RETRY_S


def test_e4_line_440s_leg_is_cut_at_seq_3950_and_re_aimed(tmp_path):
    """Ruling P23-AP 3: E4's line-440 leg, a sprint along (-0.892, -0.451) from (10778.22, 10645.98), aimed with
    19042, 19043 and 19045 held (nothing ahead). At seq 3950 the frames list 19032 at 7.43 tiles 12 degrees off that
    heading (inside AHEAD_CONE and AHEAD_R) and 19035 at 9.18 (past AHEAD_R, 2.3 tiles off the tube): the leg is cut
    (`_cut` [19032]) and the next choose re-aims by the turn rules, a heading with no held threat beyond SPRINT_R
    ahead. The record ran the leg 8.92 tiles on, to 1.26 and 2.31 tiles of them (seq 3975)."""
    from agent.base.pza1 import Steer
    w440 = next(run_worlds(E4, [440]))[2]
    r = Rig(tmp_path)
    f = P.Flee(w440, r.acts, r.clock)
    f.threats = [z for z in w440.zombies.values() if z.get("x") is not None and P.zdist(w440, z) <= P.DISENGAGE_R]
    heading = (-0.8923450287767858, -0.45135390728048114)
    far = [z for z in f.threats if P.zdist(w440, z) > P.SPRINT_R]
    assert f._ahead(heading, far) == []
    f.send(Steer(heading[0], heading[1], P.FLEE_S, "sprint"))
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    w = e3_world_at_seq(3950, run=E4)
    f.world = w
    f.threats = [z for z in w.zombies.values() if z.get("x") is not None and P.zdist(w, z) <= P.DISENGAGE_R]
    r.advance(1.4)
    f.observe()
    assert not f.busy() and f._cut == [19032]
    cmd = f.choose()
    new = (cmd.vx, cmd.vy)
    assert cmd.TYPE == "steer" and f.why["cut"] == [19032] and f._cut is None
    far = [z for z in f.threats if P.zdist(w, z) > P.SPRINT_R]
    assert f._ahead(new, far) == [] and abs(new[0] * heading[0] + new[1] * heading[1]) < 0.99


def test_e4_lines_438_to_442_the_leg_is_cut_where_19032_is_first_listed(tmp_path, monkeypatch):
    """Rule 3 through one Survive (E4's flee from line 438, a fresh Flee): the leg sent at 438 is the record's 440
    heading (turn 90, (-0.893, -0.451)); at 442, the first frame listing 19032 (9.3 tiles, in the tube just past the
    leg's AHEAD_R end), the leg is cut and a new sprint leg sent, turned away (`cut` [19032]). Named change, ruling
    P24-A (a): the fresh Flee's leg at 438 is its episode's first, which the met window now turns (the record's was
    not a first leg): the window is read as none here, so the cut rule is read alone."""
    from agent.base.world import World
    monkeypatch.setattr(World, "met_window", lambda self, r=None: None)
    r, sv, out = run_replay(E4, tmp_path, 438, 442, setup=e4_flee)
    d, leg = out[438]
    assert leg.type == "steer" and (round(leg.args["vx"], 3), round(leg.args["vy"], 3)) == (-0.893, -0.451)
    assert all(out[ln][1] is None for ln in (439, 440, 441))
    d, cut = out[442]
    why = d["inputs"]["branches"]["threat"]
    assert cut.type == "steer" and why["cut"] == [19032] and cut.args["vx"] > 0.0


@pytest.mark.parametrize("far, group", [(9.0, "hold"), (None, None)])
def test_a_walk_corner_ends_once_four_are_held(tmp_path, far, group):
    """Ruling P23-AP 2's hold count: a `walk` corner on zombie 1 at 1.2 tiles with two more held 8 tiles east keeps
    swinging (three held); a fourth held at 9 tiles ends it for the group's sprint steer, no attack sent."""
    r, sv = make(tmp_path)
    r.scan(open_yard(80, 115))
    me = (100.5, 201.5)
    zs = [zombie(1, 99.3, 201.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    attack = r.acts.history[-1]
    assert r.cmd() == ("attack", {"targetId": 1}) and sv.corner_kind == "walk"
    r.fake.answer({"attack": ["accepted"]})
    r.pump()
    zs += [zombie(2, 108.5, 201.5, me=me), zombie(3, 108.5, 203.5, me=me)]
    if far is not None:
        zs.append(zombie(4, me[0] + far, 199.5, me=me))
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=zs)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    if group is None:
        assert a is None and w["cornered"] == 1 and w["holding"] == attack.aid and "group" not in w
        return
    assert a is not None and a.type == "steer" and a.args["gait"] == "sprint" and w["group"] == "hold"
    assert "cornered" not in w and sv.cornered is None and [x.type for x in r.acts.history] == ["attack", "steer"]


@pytest.mark.parametrize("d3, group", [(2.9, "near"), (3.2, None)])
def test_a_third_zombie_within_group_near_r_ends_the_walk_corner(tmp_path, d3, group):
    """Ruling P23-AP 2's near count: zombie 1 at 1.2 tiles cornered, zombie 2 at 2.5; a third at 2.9 tiles (within
    GROUP_NEAR_R) ends the corner for the steer, at 3.2 it does not."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    zs = [zombie(1, 99.3, 201.5, me=me), zombie(2, 100.5, 204.0, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1}) and sv.corner_kind == "walk"
    r.fake.answer({"attack": ["accepted"]})
    r.pump()
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=zs + [zombie(3, 100.5, 201.5 - d3, me=me)])
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a is not None and a.type == "steer" and w.get("group") == "near") is (group is not None)
    assert (w.get("cornered") == 1) is (group is None)


def stuck_corner(r, sv):
    """`test_three_within_cornered_r_after_a_stuck_leg_are_fought`'s geometry: a leg that moved 0.1 tiles, then three
    within CORNERED_R: the `stuck` corner's attack on 2 at 1.1 tiles; returns the player's position."""
    r.scan(open_yard())
    me = (100.5, 201.5)
    zs = [zombie(1, 97.5, 201.5, me=me), zombie(2, 97.5, 202.5, me=me), zombie(3, 97.5, 200.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    r.answer()
    me = (100.6, 201.5)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me))
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 2}) and sv.corner_kind == "stuck"
    r.fake.answer({"attack": ["accepted"]})
    r.pump()
    return me


def back_off(me, d):
    """The three of `group_at_melee` stepped back so the nearest stands `d` tiles off (all within GROUP_NEAR_R)."""
    return [zombie(1, me[0] - d, me[1] + 0.6, me=me), zombie(2, me[0], me[1] + d, me=me),
            zombie(3, me[0] + d, me[1] + 0.6, me=me)]


@pytest.mark.parametrize("d, wait, retry", [(1.8, 2.0, True), (1.8, 1.5, False), (1.2, 1.0, True),
                                            (0.9, 1.0, True), (1.2, 0.9, False)])
def test_a_stuck_corner_against_a_group_tries_one_leg_once_the_nearest_is_beyond_point_blank(tmp_path, d, wait,
                                                                                             retry):
    """Ruling P23-AP 2: a `stuck` corner keeps swinging against the group, re-tested every tick: with the nearest
    beyond POINT_BLANK_R (1.8 tiles, the three within GROUP_NEAR_R) and the stuck read STUCK_RETRY_S old, the corner
    ends for one sprint steer leg (`group` "retry"); at 1.5 s it keeps swinging. Named change, ruling P24-A fix 1
    (1): with the three within CORNERED_R (1.2 or 0.9 tiles: point blank no bar) the leg goes at STUCK_RETRY_GROUP_S
    (1.0 s; it kept swinging at 1.5 s and at 0.9 tiles before), not at 0.9 s."""
    r, sv = make(tmp_path)
    me = stuck_corner(r, sv)
    attack = r.acts.history[-1]
    r.advance(wait)
    r.frame(x=me[0], y=me[1], zombies=back_off(me, d))
    a = tick(r, sv)
    w = threat_why(tmp_path)
    if not retry:
        assert a is None and w["cornered"] == 2 and w["holding"] == attack.aid and sv.corner_kind == "stuck"
        return
    assert a is not None and a.type == "steer" and a.args["gait"] == "sprint" and w["group"] == "retry"
    assert sv.cornered is None and sv.mode == "flee" and sv.flee.stuck() is False


def test_a_retried_leg_read_stuck_is_a_new_stuck_corner_with_its_own_retry_clock(tmp_path):
    """The retry's leg stands WALK_STALL_S with the group in reach (R1): a new `stuck` corner, its stuck read now, so
    no second retry before its own clock runs. Named change, ruling P24-A fix 1 (1): the three within CORNERED_R,
    that clock is STUCK_RETRY_GROUP_S (1.0 s), not STUCK_RETRY_S: held at 0.9 s, the next leg at 1.0 s."""
    r, sv = make(tmp_path)
    me = stuck_corner(r, sv)
    r.advance(2.0)
    r.frame(x=me[0], y=me[1], zombies=back_off(me, 1.2))
    tick(r, sv)
    assert r.cmd()[0] == "steer"
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    for _ in range(2):
        r.advance(0.5)
        r.frame(x=me[0], y=me[1], zombies=back_off(me, 1.2))
        tick(r, sv)
    assert r.cmd()[0] == "attack" and sv.corner_kind == "stuck" and sv.stuck_wall == r.clock()
    attack = r.acts.history[-1]
    r.fake.answer({"attack": ["accepted"]})
    r.pump()
    r.advance(0.9)
    r.frame(x=me[0], y=me[1], zombies=back_off(me, 1.2))
    assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == attack.aid
    r.advance(0.1)
    r.frame(x=me[0], y=me[1], zombies=back_off(me, 1.2))
    a = tick(r, sv)
    assert a.type == "steer" and threat_why(tmp_path)["group"] == "retry"


def test_a_running_leg_is_cut_and_re_aimed_when_a_zombie_comes_into_its_cone(tmp_path):
    """Ruling P23-AP 3: the `many` leg runs east from the three west; zombie 4 appears 6 tiles east, dead ahead: the
    leg is cut and a new sprint leg sent, turned off it (`cut` [4]); the new leg is not cut again for 4."""
    r, sv = make(tmp_path)
    zs = many_yard(r)
    tick(r, sv)
    leg = r.acts.history[-1]
    assert leg.type == "steer" and leg.args["vx"] == pytest.approx(1.0)
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    me = (101.5, 201.5)
    r.advance(0.5)
    zs = [zombie(i, z["x"], z["y"], me=me) for i, z in zip((1, 2, 3), zs)] + [zombie(4, 107.5, 201.6, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a is not None and a.type == "steer" and w["cut"] == [4] and w["turn"] not in (None, 0)
    far = [z for z in sv.flee.threats if P.zdist(r.world, z) > P.SPRINT_R]
    assert sv.flee._ahead((a.args["vx"], a.args["vy"]), far) == []
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    r.advance(0.5)
    r.frame(x=me[0] + 0.5, y=me[1], zombies=zs)
    assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == a.aid


@pytest.mark.parametrize("x4", [103.3, None])
def test_a_running_leg_is_not_cut_for_a_zombie_within_sprint_r_or_with_none_new_ahead(tmp_path, x4):
    """Rule 3's limits: a zombie 1.8 tiles ahead (within SPRINT_R, which the aim never refuses either) or no new one:
    the leg runs on."""
    r, sv = make(tmp_path)
    zs = many_yard(r)
    tick(r, sv)
    leg = r.acts.history[-1]
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    me = (101.5, 201.5)
    r.advance(0.5)
    zs = [zombie(i, z["x"], z["y"], me=me) for i, z in zip((1, 2, 3), zs)]
    if x4 is not None:
        zs.append(zombie(4, x4, 201.5, me=me))
    r.frame(x=me[0], y=me[1], zombies=zs)
    assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == leg.aid


def test_a_threat_already_ahead_at_the_aim_never_cuts_the_leg(tmp_path):
    """A leg aimed with zombie 4 ahead (every heading refused, the fallback keeping it: `_aimed`) is not cut for 4;
    the same leg aimed with nothing ahead is."""
    from agent.base.pza1 import Steer
    r = Rig(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(4, 106.5, 201.5, me=me)])
    f = P.Flee(r.world, r.acts, r.clock)
    f._aimed = frozenset([4])
    f.send(Steer(1.0, 0.0, P.FLEE_S, "sprint"))
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    r.advance(0.5)
    r.frame(x=me[0] + 0.5, y=me[1], zombies=[zombie(4, 106.0, 201.5, me=me)])
    f.observe()
    assert f.busy() and f._cut is None
    f._leg = f._leg[:3] + (frozenset(),)
    f.observe()
    assert not f.busy() and f._cut == [4]


def test_a_stuck_corner_on_one_zombie_never_retries(tmp_path):
    """The retry is the group's (P23-AP 2): a `stuck` corner on one zombie, 2.5 s on with it at 1.2 tiles, swings on."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 97.5, 201.5, me=me), zombie(2, 100.5, 205.0, me=me)],
            health=50.0)
    tick(r, sv)
    r.answer()
    me = (100.6, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 99.5, 201.5, me=me)], health=50.0)
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1}) and sv.corner_kind == "stuck"
    attack = r.acts.history[-1]
    r.fake.answer({"attack": ["accepted"]})
    r.pump()
    r.advance(2.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 99.4, 201.5, me=me)], health=50.0)
    assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == attack.aid


def test_a_zombie_ahead_of_the_away_vector_but_not_of_the_turned_leg_cuts_it_once_it_comes_ahead(tmp_path):
    """The aim's ahead is the chosen heading's (P23-AP 3): zombie 4 dead east at 5.5 tiles turns the `many` leg off the
    away vector (east), nothing ahead of the leg; when 4 then stands on the leg's own heading, the leg is cut."""
    r, sv = make(tmp_path)
    zs = many_yard(r)
    me = (100.5, 201.5)
    zs = zs + [zombie(4, 106.0, 201.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    leg = r.acts.history[-1]
    h = (leg.args["vx"], leg.args["vy"])
    assert leg.type == "steer" and threat_why(tmp_path)["turn"] not in (None, 0) and threat_why(tmp_path)["ahead"] == [4]
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    r.advance(0.5)
    zs = zs[:3] + [zombie(4, me[0] + 6.0 * h[0], me[1] + 6.0 * h[1], me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    a = tick(r, sv)
    assert a is not None and a.type == "steer" and threat_why(tmp_path)["cut"] == [4]


# ================================================================ survival 4 fix round 1 (the review of e07a52cb)
def ring(me, d=5.0, n=8):
    """`n` zombies (ids 11..) on a circle `d` tiles round `me`: every heading has one within its cone or tube."""
    return [zombie(11 + k, me[0] + d * math.cos(2 * math.pi * k / n), me[1] + d * math.sin(2 * math.pi * k / n), me=me)
            for k in range(n)]


def test_a_leg_aimed_with_a_zombie_ahead_is_not_cut_when_the_frames_relist_it_and_r1_reads_it_stuck(tmp_path):
    """G1 through one Survive: zombie 1 at 1.2 tiles and a ring of eight at 5 tiles (a group): the group steer's leg
    takes the fallback heading with ring zombies ahead (`_aimed` not empty). The next frames list the same zombies as
    new records: no cut (e07a52cb read the last tick's records as id None, cut the leg every tick and R1 never came);
    the leg held at 0.5 s, and at 1.0 s, unmoved WALK_STALL_S with zombie 1 in reach, R1's `stuck` corner attacks."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    zs = [zombie(1, 99.3, 201.5, me=me)] + ring(me)
    r.frame(x=me[0], y=me[1], zombies=zs)
    leg = tick(r, sv)
    assert leg.type == "steer" and threat_why(tmp_path)["group"] == "hold" and sv.flee._leg[3]
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=[dict(z) for z in zs])
    assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == leg.aid and "cut" not in threat_why(tmp_path)
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=[dict(z) for z in zs])
    a = tick(r, sv)
    assert a.type == "attack" and a.args == {"targetId": 1} and sv.corner_kind == "stuck"
    assert [x.type for x in r.acts.history] == ["steer", "attack"]


def test_the_cut_never_counts_a_zombie_the_world_no_longer_holds(tmp_path):
    """G1: a record the World has replaced (or dropped) reads no id; only the World's current records are read."""
    from agent.base.pza1 import Steer
    r = Rig(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(4, 106.5, 201.5, me=me)])
    f = P.Flee(r.world, r.acts, r.clock)
    f._aimed = frozenset([4])
    f.send(Steer(1.0, 0.0, P.FLEE_S, "sprint"))
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    stale = [dict(r.world.zombies[4])]
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(4, 106.4, 201.5, me=me)])
    f.threats = stale
    f.observe()
    assert f.busy() and f._cut is None


def test_e2_bathroom_with_four_held_behind_the_walls_corners_at_once(tmp_path):
    """R3 on E2's line 177 (12839 at 0.48 tiles in the bathroom's doorway, its line clear; 12788 at 5.21 behind the
    wall; no way out, nothing to adopt), with two more held 3.9 and 4.9 tiles west outside the walls: four held, a
    group, but a trapped room square: no leg can move, so the corner's attack on 12839 at once (e07a52cb steered a
    leg into the walls first)."""
    w = e2_world(177)
    for zid, x, y in ((99901, 10734.5, 10633.5), (99902, 10733.5, 10634.5)):
        w.zombies[zid] = dict(zombie(zid, x, y), seenWallMs=w.frame_wall_ms)
    held = [z for z in w.zombies.values() if z.get("x") is not None and P.zdist(w, z) <= S.DANGER_R]
    assert len(held) == S.GROUP_HOLD_N and P.exit_plan(w, held) is None and not P.adoptable(w)
    r = Rig(tmp_path)
    sv = Survive(w, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.tick(w, r.acts)
    why = threat_why(tmp_path)
    assert r.cmd() == ("attack", {"targetId": 12839}) and why["cornered"] == 12839 and "group" not in why


@pytest.mark.parametrize("d2, d3, want", [(1.2, 0.5, 3), (0.9, 0.5, 3), (0.9, 0.7, 2), (1.6, 0.95, 3), (1.3, 1.1, 2)])
def test_a_corner_re_pins_to_the_nearest_zombie_within_point_blank_at_each_attack(tmp_path, d2, d3, want):
    """R4 (E4: the corner swung at 19032 while 19035 at 0.48 tiles bit): the `stuck` corner on 2 (1.1 tiles); its
    attack ends, 2 at 1.2 and 3 at 0.5: the next attack is on 3, the corner's id with it; with 2 at 1.3 and 3 at
    1.1, nearer but beyond POINT_BLANK_R, the pin on 2 holds. Named change, ruling P24-A fix 1 (2) (P24-A (d)'s
    hysteresis margined): with 2 at 0.9 and 3 at 0.5 (0.4 nearer, REPIN_MARGIN 0.3) the re-pin goes; with 3 at 0.7
    (0.2 nearer) the pin holds; with the pin wandered to 1.6, beyond CORNERED_R, the re-pin goes."""
    r, sv = make(tmp_path)
    me = stuck_corner(r, sv)
    r.fake.answer({"attack": [{"state": "done", "result": swing(True)}]})
    r.pump()
    r.advance(0.5)
    zs = [zombie(1, me[0] - 1.0, me[1] + 0.7, me=me), zombie(2, me[0], me[1] + d2, me=me),
          zombie(3, me[0] + d3, me[1], me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    a = tick(r, sv)
    assert a.type == "attack" and a.args == {"targetId": want} and sv.cornered == want
    assert threat_why(tmp_path)["cornered"] == want


def test_a_corner_whose_pin_is_marked_ends_rather_than_following_a_retarget_beyond_point_blank(tmp_path):
    """Fix round 2 (N1, the re-review's probe): the `stuck` corner on 2; 2 steps to 1.7 tiles into a pocket walled on
    all four edges (its line blocked, no reposition square), so the Fight marks it and its recursion re-pins zombie 4
    at 3.5 tiles in the open. The corner follows a re-pin only within POINT_BLANK_R: it ends, the tick is planned
    again and the `many` flee steers; no walk toward 4 (4a86c05c followed and walked at 4 until the retry)."""
    r, sv = make(tmp_path)
    me = stuck_corner(r, sv)
    at = {(98, 201): {"blockN": True, "blockW": True}, (99, 201): {"blockW": True}, (98, 202): {"blockN": True}}
    r.scan(grid(90, 112, 192, 212, at))
    r.fake.answer({"attack": [{"state": "done", "result": swing(True)}]})
    r.pump()
    r.advance(0.5)
    zs = [zombie(1, me[0] - 4.5, me[1] - 2.0, me=me), zombie(2, 98.9, 201.5, me=me),
          zombie(3, me[0] + 4.5, me[1] - 2.0, me=me), zombie(4, me[0], me[1] + 3.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    assert P.line_to(r.world, r.world.zombies[2]) is False
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and sv.cornered is None and sv.mode == "flee" and 2 in sv.unreachable
    assert "cornered" not in w and w["flee"] == "many"
    assert all(x.type != "walkTo" for x in r.acts.history)


# ================================================================ Plan 24 survival 5, the group (ruling P24-A)
F1 = os.path.join(ARTIFACTS, "f_goals-20261028-202437")


def test_the_survival_5_constants():
    """P24-A (a) and (h); (g): EXIT_STALL_S and STEP_STALL_S are one WALK_STALL_S, and CORNERED_R's second quantity
    (the running leg's stuck read) is STUCK_NEAR_R."""
    assert (S.MANY_LISTED_N, S.DRAG_DOWN_N, P.LISTED_R) == (4, 3, 12.0)
    assert (P.WALK_STALL_S, P.STUCK_NEAR_R, P.CORNERED_R) == (1.0, 1.5, 1.5)
    assert not hasattr(P, "EXIT_STALL_S") and not hasattr(P, "STEP_STALL_S")


def test_four_listed_within_twelve_tiles_are_many_whatever_the_count_within_six(tmp_path):
    """P24-A (a) (#4268: E5's group was listed at the 12-tile edge while the branch counted within 6): one zombie
    within DANGER_R and three more listed within LISTED_R, none behind the first: `many`, logged `listed` 4; with
    three listed the fight goes."""
    r, sv = make(tmp_path)
    zs = [zombie(1, 105.0, 200.0), zombie(2, 100.0, 210.0), zombie(3, 91.0, 203.0), zombie(4, 100.0, 188.5)]
    r.frame(zombies=zs)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd()[0] == "steer" and w["flee"] == "many" and w["listed"] == 4
    assert last(tmp_path)["inputs"]["threats"] == 1
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.frame(zombies=zs[:3])
    tick(r2, sv2)
    w = threat_why(tmp_path / "b")
    assert r2.cmd() == ("walkTo", {"x": 105.5, "y": 200.5, "gait": "run"}) and w["fight"] is True
    assert "listed" not in w


def test_a_fight_does_not_walk_at_a_zombie_with_another_listed_behind_it(tmp_path):
    """P24-A (b) (E5 line 219: the fight walked at 19275 with 19278 and 19249 listed behind it, and the group
    arrived round it): the walk at zombie 1 (5 tiles east) is not sent with zombie 2 listed 10 tiles out 6 degrees off
    its bearing: the flee, `held` (`behind` [2]); a running fight's walk is left the same way; within reach the
    attack goes whatever stands behind."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 105.0, 200.0), zombie(2, 110.0, 201.0)])
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd()[0] == "steer" and w["flee"] == "held" and w["behind"] == [2] and "fight" not in w
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.frame(zombies=[zombie(1, 105.0, 200.0)])
    tick(r2, sv2)
    assert r2.cmd()[0] == "walkTo" and sv2.mode == "fight"
    r2.fake.answer({"walkTo": ["accepted"]})
    r2.pump()
    r2.frame(zombies=[zombie(1, 104.5, 200.0), zombie(2, 109.0, 199.0)])
    tick(r2, sv2)
    w = threat_why(tmp_path / "b")
    assert r2.cmd()[0] == "steer" and w["flee"] == "held" and w["behind"] == [2]
    (tmp_path / "c").mkdir()
    r3, sv3 = make(tmp_path / "c")
    r3.frame(zombies=[zombie(1, 101.5, 200.0), zombie(2, 106.0, 200.5)])
    tick(r3, sv3)
    assert r3.cmd() == ("attack", {"targetId": 1}) and "behind" not in threat_why(tmp_path / "c")


def test_a_walk_corner_yields_to_the_health_flee_and_none_is_taken_under_it(tmp_path):
    """P24-A (c), the close review's I1 (F1's `walk` corner held from health 99.4 to 0.9): a `walk` corner at health
    45 attacks (`corner_kind` "walk" logged, (g)); at 39 it ends for the `health` flee (`yield` "health"), a sprint
    leg; on the next tick, the zombie still within CORNERED_R and the leg running, no new `walk` corner."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    one = [zombie(1, 99.3, 201.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=one, health=45.0)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd() == ("attack", {"targetId": 1}) and w["cornered"] == 1 and w["corner_kind"] == "walk"
    r.fake.answer({"attack": ["accepted"]})
    r.pump()
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=one, health=39.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and a.args["gait"] == "sprint" and w["flee"] == "health" and w["yield"] == "health"
    assert "cornered" not in w and sv.cornered is None and sv.mode == "flee"
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    r.advance(0.3)
    r.frame(x=me[0] + 0.6, y=me[1], zombies=[zombie(1, 100.2, 201.5, me=(me[0] + 0.6, me[1]))], health=38.0)
    assert tick(r, sv) is None
    w = threat_why(tmp_path)
    assert w["yield"] == "health" and "cornered" not in w and w["holding"] == a.aid


def test_a_stuck_corner_keeps_swinging_under_flee_health(tmp_path):
    """P24-A (c)'s other side: a `stuck` corner keeps the override, no leg moving there."""
    r, sv = make(tmp_path)
    me = stuck_corner(r, sv)
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me), health=30.0)
    assert tick(r, sv) is None
    w = threat_why(tmp_path)
    assert w["cornered"] == 2 and w["corner_kind"] == "stuck" and "yield" not in w and sv.mode == "fight"


def test_no_walk_corner_is_taken_while_a_many_flee_episode_runs(tmp_path):
    """P24-A (c): a `many` flee's leg runs and has moved; one zombie comes within CORNERED_R (no group): the `walk`
    corner yields to the running `many` episode (`yield` "many"), the leg held, no attack."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 103.0, 201.5, me=me), zombie(2, 100.5, 204.5, me=me),
                                       zombie(3, 98.0, 199.0, me=me)])
    leg = tick(r, sv)
    assert leg.type == "steer" and threat_why(tmp_path)["flee"] == "many"
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    r.advance(0.4)
    me = (99.5, 200.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 100.7, 200.5, me=me), zombie(2, 100.5, 205.5, me=me),
                                       zombie(3, 97.0, 196.0, me=me)])
    assert tick(r, sv) is None
    w = threat_why(tmp_path)
    assert w["yield"] == "many" and w["flee"] == "many" and w["holding"] == leg.aid and "cornered" not in w
    assert not any(a.type == "attack" for a in r.acts.history)


def f1_walk_corner(r, sv, w):
    """`run_replay`'s setup: F1's `walk` corner on 15921 as the record ran it (taken at line 561, a cornered Fight
    pinned to it, marks never freed)."""
    sv.mode, sv.cornered, sv.corner_kind, sv.corner_free = "fight", 15921, "walk", S.CORNERED_R
    sv.fight = sv._corner_fight = P.Fight(w, r.acts, r.clock, unreachable=sv.unreachable, target=15921)
    sv.fight.point_blank, sv.fight.mark_free_r = True, 0.0


def test_f1_s_last_fight_the_walk_corner_yields_to_health_at_the_first_line_under_40(tmp_path):
    """P24-A (c) on F1's lines 600-612 (the recorded worlds; the record's `walk` corner on 15921 set up as it ran):
    the corner holds while health reads 69.5 to 44.3; at 607, the first line under FLEE_HEALTH (33.8), it yields
    (`yield` "health") and the flee goes, its reason `many` (four listed within LISTED_R, (a), read before
    `health`): the shelter approach walk to building 2 (the episode's shelter pick), which stands and is dropped
    at 610 (`stalled`) for a sprint steer. The record swung on to health 0.9."""
    r, sv, out = run_replay(F1, tmp_path, 600, 612, setup=f1_walk_corner)
    for line in range(600, 607):
        d = out[line][0]
        why = d["inputs"]["branches"]["threat"]
        assert why["cornered"] == 15921 and why["corner_kind"] == "walk" and d["inputs"]["health"] >= 40.0, line
    d, a = out[607]
    why = d["inputs"]["branches"]["threat"]
    assert d["inputs"]["health"] < S.FLEE_HEALTH and why["yield"] == "health" and "cornered" not in why
    assert a.type == "walkTo" and why["flee"] == "many" and why["listed"] == 4 and why["step"] == "approach"
    d, steer = out[610]
    assert steer.type == "steer" and d["inputs"]["branches"]["threat"]["ended"] == "stalled"


def test_f1_line_599_sends_the_attack_not_the_approach_walk_at_point_blank(tmp_path):
    """P24-A (e), the close review's I3 on F1's line 599 (15921 at 0.49 tiles, the approach due after two swings not
    started): the record walked to its square's centre; the attack goes, the flag cleared."""
    def setup(r, sv, w):
        f1_walk_corner(r, sv, w)
        sv.fight.approach = True
    r, sv, out = run_replay(F1, tmp_path, 599, 599, setup=setup)
    d, a = out[599]
    assert a.type == "attack" and a.args == {"targetId": 15921} and sv.fight.approach is False
    assert d["inputs"]["branches"]["threat"]["dist"] <= P.POINT_BLANK_R


@pytest.mark.parametrize("south", [False, True])
def test_on_a_room_square_the_group_is_left_by_the_exit_or_the_trapped_fight_never_the_steer(tmp_path, south):
    """P24-A (f), the close review's I4: three zombies at melee range north of the player on building 1's room
    square. Named change, ruling P24-A fix 1 (3): EXIT_CLEAR_R reads the exit's own square and the line ahead to it,
    never the player's back, so the south doorway's exit walk goes at once, at a sprint (the flee adopted the
    building and the next tick's trapped corner swung before). With a fourth zombie in the south exit's tube (and so
    no exit), the group's flee adopts the building (its open doors: the re-close is guarded, the plan drops) and holds,
    no steer; the next tick the room square is trapped, so the corner swings."""
    from .test_policies import two_door_house
    r, sv = make(tmp_path)
    r.scan(two_door_house())
    me = (111.5, 201.5)
    zs = [zombie(1, 110.6, 200.6, me=me), zombie(2, 111.5, 200.4, me=me), zombie(3, 112.4, 200.7, me=me)]
    if south:
        zs.append(zombie(4, 111.6, 202.6, me=me))
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["group"] in ("near", "hold") and not any(a.type == "steer" for a in r.acts.history)
    if not south:
        assert r.cmd() == ("walkTo", {"x": 111.5, "y": 204.5, "gait": "sprint"}) and w["exit"] == 1
        return
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd()[0] == "attack" and w["corner_kind"] == "inside" and "group" not in w
    assert not any(a.type == "steer" for a in r.acts.history)


def test_the_drag_down_guard_leaves_a_stuck_corner_for_the_group_sprint(tmp_path):
    """P24-A (h) (#4290, #4291: three attackers within 0.9 tiles make the next hit the drag-down, health to 0 in one
    call; the fixture's Strength 2): the `stuck` corner swings with one attacker; at two (DRAG_DOWN_N - 1) it ends
    at once for the group's sprint leg (`group` "drag"), whatever its kind."""
    r, sv = make(tmp_path)
    me = stuck_corner(r, sv)
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me), attackers=1)
    assert tick(r, sv) is None and sv.cornered == 2
    r.advance(0.1)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me), attackers=S.DRAG_DOWN_N - 1)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and a.args["gait"] == "sprint" and w["group"] == "drag" and "cornered" not in w
    assert sv.cornered is None and sv.mode == "flee"


def test_the_drag_down_guard_takes_the_running_exit_at_a_sprint_inside(tmp_path):
    """P24-A (h) with (f): inside, the exit walk running (a `many` flee), two attackers: the walk is re-sent at a
    sprint, never a steer."""
    from .test_policies import two_door_house
    r, sv = make(tmp_path)
    r.scan([q for q in two_door_house() if q["x"] < 115])
    me = (111.5, 201.5)
    east = [zombie(1, 116.0, 201.2, me=me), zombie(2, 115.8, 201.9, me=me), zombie(3, 115.5, 201.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=east)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 198.5, "gait": "run"})
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    r.advance(0.2)
    r.frame(x=me[0], y=me[1] - 0.6, zombies=east, attackers=2)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 198.5, "gait": "sprint"}) and w["group"] == "drag"
    assert not any(a.type == "steer" for a in r.acts.history)


def test_on_a_trapped_room_square_the_drag_down_guard_leaves_the_corner_swinging(tmp_path):
    """P24-A (h): on a room square with no way out and nothing to adopt there is no leg to take: the corner swings."""
    r, sv = make(tmp_path)
    r.scan(closed_room())
    me = (102.5, 203.5)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me), attackers=2)
    assert P.on_room(r.world)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd()[0] == "attack" and w["corner_kind"] == "inside" and "group" not in w


def test_a_cornered_fight_sends_no_attack_in_a_hit_reaction(tmp_path):
    """P24-A (i): the `stuck` corner's attack ended; the frame reads a hit reaction: no attack (`hitReaction`), the
    branch holds; the frame after it clears, the attack."""
    r, sv = make(tmp_path)
    me = stuck_corner(r, sv)
    r.fake.answer({"attack": [{"state": "done", "result": swing(True)}]})
    r.pump()
    n = len(r.acts.history)
    r.advance(0.5)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me), hit_reaction="HitReaction")
    assert tick(r, sv) is None and len(r.acts.history) == n
    assert threat_why(tmp_path)["hitReaction"] == "HitReaction" and sv.cornered == 2
    r.advance(0.1)
    r.frame(x=me[0], y=me[1], zombies=group_at_melee(me))
    a = tick(r, sv)
    assert a.type == "attack" and "hitReaction" not in threat_why(tmp_path)


def test_the_flee_is_observed_once_a_tick_over_this_tick_s_held_records(tmp_path, monkeypatch):
    """P24-A (g), the close review's M1: one `observe` per policy a tick (the Flee's was run twice, its first over the
    last tick's held records); the breach read once on a re-planned tick (fix round 2's N1 case below)."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    seen = []
    real = P.Flee.observe

    def spy(self):
        seen.append(([id(z) for z in self.threats or ()], sorted(id(z) for z in r.world.zombies.values())))
        return real(self)
    monkeypatch.setattr(P.Flee, "observe", spy)
    me = (100.5, 201.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(1, 103.0, 201.5, me=me), zombie(2, 100.5, 204.5, me=me),
                                       zombie(3, 98.0, 199.0, me=me)])
    tick(r, sv)
    assert len(seen) == 1
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    r.advance(0.3)
    r.frame(x=me[0] - 0.8, y=me[1], zombies=[zombie(1, 103.0, 201.5, me=me), zombie(2, 100.5, 204.5, me=me),
                                             zombie(3, 98.0, 199.0, me=me)])
    tick(r, sv)
    assert len(seen) == 2 and sorted(seen[1][0]) == seen[1][1]   # this tick's records


def test_a_re_planned_tick_reads_the_breach_once(tmp_path, monkeypatch):
    """P24-A (g), M1: the N1 re-plan (a corner whose pin is marked ends and the tick is planned again) no longer runs
    `_breach` twice, which restarted the closing count."""
    calls = []
    real = Survive._breach
    monkeypatch.setattr(Survive, "_breach", lambda self, held: calls.append(1) or real(self, held))
    replans = []
    real_decide = Survive._decide
    monkeypatch.setattr(Survive, "_decide",
                        lambda self, held, breach, replanned=False:
                        replans.append(replanned) or real_decide(self, held, breach, replanned))
    test_a_corner_whose_pin_is_marked_ends_rather_than_following_a_retarget_beyond_point_blank(tmp_path)
    assert True in replans and len(calls) == sv_ticks(tmp_path)


def sv_ticks(tmp_path):
    """The threat ticks of a test's decision.log."""
    return sum(1 for d in decisions(tmp_path) if d["branch"] == "threat")


def test_f1_s_recorded_re_pins_each_came_with_the_pin_beyond_point_blank():
    """P24-A (d) read on F1's last fight (the close review's I2: the pin alternated 15921, 15917 about eight times):
    every recorded re-pin (568, 573, 590, 599, 615) went while the pin itself stood beyond POINT_BLANK_R (1.03 to
    1.30 tiles), so the hysteresis as ruled leaves each one standing; it holds a pin within POINT_BLANK_R only
    (`test_a_corner_re_pins_to_the_nearest_zombie_within_point_blank_at_each_attack`, E5's line 242). A finding for
    the next ruling, not a defect of (d)."""
    with open(os.path.join(F1, "decision.log"), encoding="utf-8") as f:
        rows = [json.loads(ln) for ln in f]
    targets = {k: (rows[k - 1]["inputs"]["branches"].get("threat") or {}).get("target") for k in range(561, 616)}
    repins = [k for k in range(562, 616) if targets[k] is not None and targets[k - 1] is not None
              and targets[k] != targets[k - 1]]
    assert repins == [568, 573, 590, 599, 615]
    from agent.base import replay_decisions as R
    from agent.base.world import World
    lines, recorded = R.read_record(F1)
    w, i = World(), 0
    for line, (frame_end, _) in enumerate(R.align(lines, recorded), 1):   # the frame each tick read (Task 1's rule)
        for ln in lines[i:frame_end]:
            w.apply(ln)
        i = frame_end
        if line in repins:
            pin, new = w.zombies[targets[line - 1]], w.zombies[targets[line]]
            assert P.zdist(w, pin) > P.POINT_BLANK_R and P.zdist(w, new) <= P.POINT_BLANK_R, line


# ================================================================ Plan 24 survival 5 fix 1 (rulings on the concerns)
def test_the_survival_5_fix_1_constants():
    assert (S.STUCK_RETRY_GROUP_S, S.STUCK_RETRY_S, P.REPIN_MARGIN, P.BEHIND_MARGIN) == (1.0, 2.0, 0.3, 0.5)


def test_f1_s_recorded_re_pin_lines_switch_three_times_under_the_margin_not_five():
    """P24-A fix 1 (2) on F1's last fight: a cornered Fight pinned to 15921 at line 561, its point-blank re-pin read at
    each line the record sent an attack or walk (the chooses), on the frames those ticks read. The record switched at
    568, 573, 590, 599 and 615; with the margin (the pin beyond CORNERED_R, or the new one REPIN_MARGIN nearer) 573
    (0.18 nearer) and 590 (already on 15917) go: three switches, 568 (0.44 nearer), 599 (0.81) and 615 (0.71). The
    margin halves the alternation; it does not end it (each of the three is a zombie well nearer than the pin)."""
    from agent.base import replay_decisions as R
    from agent.base.actions import Actions
    from agent.base.world import World
    with open(os.path.join(F1, "decision.log"), encoding="utf-8") as f:
        rows = [json.loads(ln) for ln in f]
    sends = [k for k in range(561, 616) if rows[k - 1]["sent"] and rows[k - 1]["action"]["type"] in ("attack", "walkTo")]
    lines, recorded = R.read_record(F1)
    w, i = World(), 0
    fight = None
    pins = []
    for line, (frame_end, _) in enumerate(R.align(lines, recorded), 1):
        for ln in lines[i:frame_end]:
            w.apply(ln)
        i = frame_end
        if line == 561:
            fight = P.Fight(w, Actions(None, clock=lambda: 0.0), clock=lambda: 0.0, target=15921)
            fight.point_blank = True
        if line in sends:
            fight._repin_point_blank()
            pins.append((line, fight.target))
    switches = [line for (line, t), (_, prev) in zip(pins[1:], pins) if t != prev]
    assert switches == [568, 599, 615]


def test_f1_s_corner_read_stuck_at_537_tries_a_leg_within_one_second():
    """P24-A fix 1 (1) on the F1 golden: the corner taken at 537 reads `stuck` (the leg stood with 15921 at 1.25
    tiles); with four held (GROUP_HOLD_N) its retry leg goes within STUCK_RETRY_GROUP_S of the stuck read, where
    survival 5 held the corner on (the record's group steer went at 540)."""
    from agent.base import replay_decisions as R
    g = {d["line"]: d for d in json.load(open(R.golden_path("f1"), encoding="utf-8"))["decisions"]}
    rows = {k: r for k, r in enumerate(R.replay(F1), 1)}
    assert g[537]["why"]["corner_kind"] == "stuck"
    retry = next(k for k in range(538, 546) if g[k]["why"].get("group") == "retry")
    assert g[retry]["action"]["type"] == "steer" and retry <= 540
    assert rows[retry]["wall"] - rows[537]["wall"] < S.STUCK_RETRY_S
