"""The survival priority list (Plan 22 Task 10): threat -> need -> load -> night -> goal over the policies, with Plan 21b's
hysteresis (`testing/agent/policy.py`'s docstring, frozen) and the hold-radius fix, `need` consuming a held item by id,
the failed-action cooldown and the decision log; Plan 21's `test_policy.py` cases ported to the typed actions, end to
end on the fake mod. Plan 23 Task 13 (ruling P23-F): the forage and explore tests are rewritten in place as
goal tests (`planner/goals.py`'s scripted source: Stock for a need, LootBuilding for a building, ExploreToward)."""
import json

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
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 105.0, 200.0), zombie(2, 108.0, 200.0), zombie(3, 100.0, 209.0)])
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
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0), zombie(2, 103.0, 201.0)], health=health)
    tick(r, sv)
    assert r.cmd()[0] == want
    if want == "steer":
        assert threat_why(tmp_path)["flee"] == "pair"


def test_a_running_flee_turns_to_fight_only_with_one_threat_and_a_health_margin(tmp_path):
    r, sv = make(tmp_path)
    three = [zombie(1, 103.0, 200.0), zombie(2, 103.0, 201.0), zombie(3, 104.0, 200.0)]
    r.frame(zombies=three, health=74.0)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "many"
    r.answer()
    r.event("zombie_dead", id=3)
    r.frame(zombies=three[:2], health=74.0)
    tick(r, sv)                                              # two threats at 74: the flee is held, re-aimed
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "held"
    r.answer()
    r.event("zombie_dead", id=2)
    r.frame(zombies=three[:1], health=59.0)
    tick(r, sv)                                              # one threat under FLEE_HEALTH + REFIGHT_MARGIN: held
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "held"
    r.answer()
    r.frame(zombies=three[:1], health=74.0)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 103.5, "y": 200.5, "gait": "run"})
    assert threat_why(tmp_path) == {"fight": True, "target": 1, "pinned": True, "dist": 3.0, "approach": False,
                                    "line": None, "reposition": None}


def test_a_running_fight_turns_to_flee_only_on_the_flee_conditions(tmp_path):
    r, sv = make(tmp_path)
    two = [zombie(1, 103.0, 200.0), zombie(2, 103.0, 201.0)]
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
    for _ in range(3):
        r.answer()
        r.advance(1.0)
        r.frame(zombies=z())
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
    """M-6: a zombie within DANGER_R whose line is blocked, the character inside: no flee out of the shelter."""
    from .test_night import house
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=111.5, y=201.5, zombies=[zombie(1, 108.5, 201.5)])
    assert tick(r, sv) is None
    d = last(tmp_path)
    assert d["branch"] == "threat" and d["sent"] is False and threat_why(tmp_path)["flee"] == "held_inside"
    assert r.acts.history == []
    r.frame(x=111.5, y=201.5, zombies=[zombie(1, 108.5, 201.5), zombie(2, 112.5, 202.5)])   # one inside: clear
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
    from .test_night import CLOSED, OPEN
    r, sv = make(tmp_path)
    shelter_world(r, CLOSED)
    r.frame(x=100.0, y=201.5, zombies=group())
    tick(r, sv)                                              # the approach square (111, 201) is 11.5 tiles away
    assert r.cmd() == ("walkTo", {"x": 111.5, "y": 201.5, "gait": "run"})
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
    assert r.cmd() == ("walkTo", {"x": 112.5, "y": 200.5, "gait": "run"})
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


def test_unarmed_and_sheltered_with_a_zombie_in_line_re_closes_once_then_steers(tmp_path):
    """I2: never hold with a line clear; one re-close of the open door, and when it fails the steer."""
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
    assert tick(r, sv) is not None and r.cmd()[0] == "steer"


def test_unarmed_with_a_zombie_in_the_doorway_never_re_closes(tmp_path):
    """Concern 4: a known zombie within 1.5 tiles of the door: the steer at once, no close tried beside it."""
    from .test_night import OPEN
    r, sv = make(tmp_path)
    me = sheltered(r, sv, weapon=None)
    shelter_world(r, OPEN)
    zs = [zombie(1, 112.5, 201.5, me=me)] + group(8.0, me)[1:]
    r.frame(x=me[0], y=me[1], zombies=zs, weapon=None)
    assert tick(r, sv) is not None and r.cmd()[0] == "steer"
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
    """M5: `pair` counts DANGER_R while a fight holds DISENGAGE_R (the surviving half of the Plan 21b fix)."""
    r, sv = make(tmp_path)
    cut = {"scratched": 1}
    r.frame(zombies=[zombie(1, 105.0, 200.0)], wounds=cut)
    tick(r, sv)
    r.frame(zombies=[zombie(1, 105.0, 200.0), zombie(2, 108.0, 200.0)], wounds=cut)
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


def test_a_flee_that_starts_inside_adopts_the_building_and_re_closes(tmp_path):
    """Concern 3: the character inside a known building (a loot), a group in line through the open door: the
    building is adopted as sheltered, the door re-closed, then the inside hold."""
    from .test_night import CLOSED, OPEN
    r, sv = make(tmp_path)
    shelter_world(r, OPEN)
    me = (113.5, 201.5)
    zs = [zombie(1, 108.5, 201.2, me=me), zombie(2, 109.5, 201.7, me=me), zombie(3, 107.6, 201.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 112, "y": 201, "kind": "close", "filter": "all", "maxWeight": 0.0})
    assert threat_why(tmp_path)["flee"] == "many" and threat_why(tmp_path)["step"] == "reclose"
    assert sv.flee.sheltered is True and sv.flee.plan["building"] == 1
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
def test_an_adopted_building_guards_its_open_door_before_the_nearer_closed_one(tmp_path):
    """F1: a loot entered by the north door left it open; the group nears the closed west door; the re-close names
    the open north door."""
    from .test_night import CLOSED, OPEN, house
    r, sv = make(tmp_path)
    north = [square(113, y) for y in range(194, 200)]
    north_door = square(113, 200, room="kitchen", building=1, door=OPEN, blockN=False, edgeN=True)
    r.scan(grid(95, 108, 196, 207) + house(1, 112, door=CLOSED) + north + [north_door])
    me = (113.5, 201.5)
    zs = [zombie(1, 108.5, 201.5, me=me), zombie(2, 109.0, 201.5, me=me), zombie(3, 113.5, 196.5, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 113, "y": 200, "kind": "close", "filter": "all", "maxWeight": 0.0})
    assert sv.flee.door() == (113, 200, 0)
