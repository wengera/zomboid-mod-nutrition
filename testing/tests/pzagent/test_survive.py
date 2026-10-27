"""The survival priority list (Plan 22 Task 10): threat -> need -> forage -> explore over the policies, with Plan 21b's
hysteresis (`testing/agent/policy.py`'s docstring, frozen) and the hold-radius fix, `need` consuming a held item by id,
the failed-action cooldown and the decision log; Plan 21's `test_policy.py` cases ported to the typed actions, end to
end on the fake mod."""
import json

import pytest

from agent.base.planner import Planner
from agent.base.planner import survive as S
from agent.base.planner.survive import Survive

from .test_policies import BAT, CRATE, FRIDGE, Rig, all_sends_valid, square, swing, zombie


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


# ================================================================ the list and its constants
def test_branch_order_and_thresholds_are_plan_21s_without_sleep():
    assert S.BRANCHES == ("threat", "need", "forage", "explore")
    assert (S.DANGER_R, S.DISENGAGE_R, S.THIRST_T, S.HUNGER_T) == (6.0, 10.0, 0.5, 0.5)
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
    assert a is not None and r.cmd() == ("walkTo", {"x": 104, "y": 200, "gait": "run"})
    d = last(tmp_path)
    assert d["branch"] == "threat" and d["inputs"]["threats"] == 2 and d["inputs"]["armed"] is True
    assert d["action"] == {"type": "walkTo", "args": {"x": 104, "y": 200, "gait": "run"}} and d["sent"] is True


def test_threat_ignores_a_zombie_beyond_danger_r(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 106.5, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "threat"


def test_a_threat_engaged_at_six_tiles_holds_beyond_six_within_ten(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(101, 200, containers=[CRATE])])
    r.frame(zombies=[zombie(1, 105.5, 200.0)])
    tick(r, sv)
    assert r.cmd()[0] == "walkTo" and last(tmp_path)["branch"] == "threat"
    r.answer()
    r.frame(zombies=[zombie(1, 107.0, 200.0)])               # 7 tiles: beyond DANGER_R, inside DISENGAGE_R
    tick(r, sv)
    d = last(tmp_path)
    assert d["branch"] == "threat" and d["inputs"]["mode"] == "fight" and d["inputs"]["held"] == 1
    assert d["inputs"]["threats"] == 0 and r.cmd() == ("walkTo", {"x": 107, "y": 200, "gait": "run"})
    r.answer()
    r.frame(zombies=[zombie(1, 111.0, 200.0)])               # 11 tiles: disengaged
    tick(r, sv)
    assert last(tmp_path)["branch"] == "forage" and r.cmd() == ("interact", {"x": 101, "y": 200, "kind": "loot",
                                                                             "filter": "all"})


def test_with_no_threat_running_a_zombie_at_seven_tiles_is_no_threat(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 107.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "threat"


def test_the_too_many_count_reads_within_danger_r_only(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zombie(1, 103.0, 200.0)])
    tick(r, sv)                                              # fight: a walk to it, left current
    r.frame(zombies=[zombie(1, 103.0, 200.0), zombie(2, 108.0, 200.0), zombie(3, 100.0, 209.0)])
    assert tick(r, sv) is None                               # three held within 10, one within 6: still a fight
    d = last(tmp_path)
    assert d["branch"] == "threat" and d["inputs"]["held"] == 3 and d["inputs"]["threats"] == 1
    assert "flee" not in d["inputs"]["branches"]["threat"] and d["sent"] is False and d["action"] is None
    r.frame(zombies=[zombie(1, 103.0, 200.0), zombie(2, 104.0, 201.0), zombie(3, 100.0, 204.5)])
    tick(r, sv)                                              # three within 6: too many
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "many"


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
    assert r.cmd() == ("walkTo", {"x": 103, "y": 200, "gait": "run"}) and threat_why(tmp_path) == {"fight": True}


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
    assert r.cmd() == ("attack", {"targetId": 1}) and threat_why(tmp_path) == {"fight": True}


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
    r.scan([square(101, 200, containers=[CRATE])])
    r.frame()
    tick(r, sv)
    assert r.cmd()[0] == "interact"
    r.frame()
    assert tick(r, sv) is None                               # the loot is current: held, nothing sent
    d = last(tmp_path)
    assert d["branch"] == "forage" and d["sent"] is False and d["action"] is None
    r.frame(zombies=[zombie(1, 101.5, 200.0)])
    assert tick(r, sv) is not None and r.cmd() == ("attack", {"targetId": 1})   # the threat pre-empts the loot
    assert len(r.acts.history) == 2


# ================================================================ need
def test_need_consumes_a_held_water_bottle_by_id_when_thirsty_then_food(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=702, fullType="Base.Apple", weight=0.2)
    r.event("item_added", itemId=701, fullType="Base.WaterBottleFull", weight=1.0)
    r.frame(thirst=0.6, hunger=0.6)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 701}) and last(tmp_path)["branch"] == "need"
    r.answer({"state": "done", "result": {"itemId": 701}})
    r.event("item_removed", itemId=701, fullType="Base.WaterBottleFull")
    r.frame(thirst=0.2, hunger=0.6)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 702})
    all_sends_valid(r)


def test_need_marks_food_and_falls_through_to_forage_for_it(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(101, 200, containers=[CRATE]), square(103, 200, containers=[FRIDGE])])
    r.frame(hunger=0.6)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 103, "y": 200, "kind": "loot", "filter": "food"})
    d = last(tmp_path)
    assert d["branch"] == "forage" and d["inputs"]["need"] == "food"


def test_forage_never_loots_at_load_level_three(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(101, 200, containers=[CRATE])])
    r.event("item_added", itemId=602, fullType="Base.Plank", weight=3.0)
    r.frame(level=3)
    tick(r, sv)
    assert r.cmd() == ("drop", {"itemId": 602}) and last(tmp_path)["branch"] == "forage"
    assert last(tmp_path)["inputs"]["load"] == 3


# ================================================================ the cooldown
def test_a_failed_action_cools_its_branch_for_ten_planner_ticks(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=701, fullType="Base.WaterBottleFull", weight=1.0)
    r.frame(thirst=0.6)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 701})
    r.answer({"state": "failed", "reason": "not valid"})
    for i in range(S.FAILED_COOLDOWN_TICKS):
        r.frame(thirst=0.6)
        a = tick(r, sv)
        d = last(tmp_path)
        assert d["branch"] != "need" and d["inputs"]["cooled"] == {"type": "consume", "args": {"itemId": 701}}, i
        if a is not None:
            r.answer()                                       # explore's scan
    r.frame(thirst=0.6)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 701}) and last(tmp_path)["inputs"]["cooled"] is None
    assert [a.type for a in r.acts.history].count("consume") == 2


def test_a_cooled_action_passes_over_to_the_next_branch(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(102, 200, containers=[CRATE])])
    r.event("item_added", itemId=701, fullType="Base.WaterBottleFull", weight=1.0)
    r.frame(thirst=0.6)
    tick(r, sv)
    r.answer({"state": "failed", "reason": "not valid"})
    r.frame(thirst=0.6)
    tick(r, sv)
    assert r.cmd()[0] == "interact" and last(tmp_path)["branch"] == "forage"


def test_a_superseded_action_is_not_a_failure(tmp_path):
    r, sv = make(tmp_path)
    r.event("item_added", itemId=701, fullType="Base.WaterBottleFull", weight=1.0)
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
    r.event("item_added", itemId=701, fullType="Base.WaterBottleFull", weight=1.0)

    def step(i, **k):
        r.advance(0.25)
        r.frame(game_min=480.0 + i, **k)
        if tick(r, sv) is not None:
            r.answer({"state": "done", "result": swing(True)} if r.cmd()[0] == "attack" else "done")

    step(0)                                                  # explore: scan
    r.scan([square(x, y, containers=[CRATE] if (x, y) == (101, 201) else []) for x in range(99, 102)
            for y in range(199, 202)])
    step(1)                                                  # forage: loot the crate
    step(2, thirst=0.6)                                      # need: drink the bottle
    step(3, zombies=[zombie(1, 103.0, 200.0)])               # threat: walk to it
    step(4, zombies=[zombie(1, 101.0, 200.0)])               # threat: attack
    step(5, zombies=[zombie(1, 101.0, 200.0)], health=30.0)  # threat: flee
    r.event("zombie_dead", id=1)
    step(6, level=3)                                         # nothing to drop, no loot: explore walks
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
        assert set(d) == {"wall", "gameMin", "branch", "inputs", "action", "sent"}
        assert d["wall"] == 1000.0 + 0.25 * (i + 1) and d["gameMin"] == 480.0 + i
    branches = [json.loads(ln)["branch"] for ln in lines]
    assert {"threat", "need", "forage", "explore"} <= set(branches)
