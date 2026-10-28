"""The night instinct (Plan 23 Task 12, P23-9): when tired or late, shelter in a known interior and sleep.

`planner/night.py`'s `Night` over the fake mod: the want (fatigue above TIRED_T, or the hour at LATE_HOUR or later
with fatigue above LATE_FATIGUE), the shelter steps one action at a time (approach the door, open it if it reads
closed, step to the interior square, close the door, sleep), the shun of a building whose step failed, the hold on a
sleep refused `not safe`, the want cleared by a sleep that ended rested, and `want_shelter` with no interior known;
end to end through `Survive`'s `night` branch."""
import json

import pytest

from agent.base.planner import night as N
from agent.base.planner.night import Night
from agent.base.planner.survive import Survive

from .test_policies import Rig, all_sends_valid, square, zombie

CLOSED = {"open": False, "locked": False, "barricaded": False}
OPEN = {"open": True, "locked": False, "barricaded": False}
LOCKED = {"open": False, "locked": True, "barricaded": False}


def house(bid, x0, y0=200, door=CLOSED):
    """A 3 x 3 interior of building `bid` at x0..x0+2, y0..y0+2, its west wall at x0 with one door on the west edge of
    (x0, y0 + 1) (blocked while the door reads closed), its north wall on y0; and the open outdoor squares x0-3..x0-1
    by y0-1..y0+3 in front of it."""
    sqs = []
    for x in range(x0, x0 + 3):
        for y in range(y0, y0 + 3):
            at_door = (x, y) == (x0, y0 + 1)
            sqs.append(square(x, y, room="kitchen", building=bid, door=door if at_door else None,
                              blockW=(x == x0) and not (at_door and door["open"]), blockN=(y == y0),
                              edgeW=(x == x0), edgeN=(y == y0)))
    for x in range(x0 - 3, x0):
        for y in range(y0 - 1, y0 + 4):
            sqs.append(square(x, y))
    return sqs


def make(tmp_path):
    r = Rig(tmp_path)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    return r, sv


def tick(r, sv):
    return sv.tick(r.world, r.acts)


def last(tmp_path):
    with open(tmp_path / "decision.log", encoding="utf-8") as f:
        return [json.loads(ln) for ln in f][-1]


def night_why(tmp_path):
    return last(tmp_path)["inputs"]["branches"]["night"]


def end(r, *states):
    """Answer the last cmd with exactly `states` (no `accepted` first: a refusal at check comes alone)."""
    cmd = json.loads((r.dir / "cmd.txt").read_text(encoding="utf-8"))
    r.fake.answer({cmd["type"]: list(states)})
    r.pump()


DONE_SLEEP = {"state": "done", "result": {"sleptH": 8.0, "fatigueBefore": 0.65, "fatigueAfter": 0.05,
                                          "bedType": "floor"}}


# ================================================================ the constants and the want
def test_the_constants():
    assert (N.TIRED_T, N.LATE_HOUR, N.LATE_FATIGUE, N.SHUN_MIN, N.NOT_SAFE_S) == (0.6, 22.0, 0.3, 120, 30.0)


@pytest.mark.parametrize("hour, fatigue, wants", [
    (8.0, 0.65, True), (8.0, 0.6, False),                       # tired: above TIRED_T, the first TIRED moodle
    (23.0, 0.35, True), (23.0, 0.2, False),                     # late: the brief's two
    (22.0, 0.31, True), (21.99, 0.35, False), (22.0, 0.3, False),
    (None, 0.35, False), (None, 0.65, True),                    # an old log's frame has no hour: daytime
])
def test_the_want_reads_fatigue_and_the_hour(tmp_path, hour, fatigue, wants):
    r = Rig(tmp_path)
    r.frame(hour=hour, fatigue=fatigue)
    assert Night(r.world, r.acts, r.clock).wants() is wants


# ================================================================ the shelter steps
def test_tired_outside_with_a_closed_door_known_walks_opens_enters_closes_then_sleeps(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=100.0, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 109.5, "y": 201.5, "gait": "walk"})
    d = last(tmp_path)
    assert d["branch"] == "night" and d["inputs"]["fatigue"] == 0.65 and d["inputs"]["hour"] == 8.0
    assert night_why(tmp_path)["step"] == "approach" and night_why(tmp_path)["building"] == 1
    assert night_why(tmp_path)["shunned"] == []
    r.answer()
    r.frame(x=109.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 110, "y": 201, "kind": "open", "filter": "all", "maxWeight": 0.0})
    assert night_why(tmp_path)["step"] == "open"
    r.answer()
    r.frame(x=109.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 110.5, "y": 200.5, "gait": "walk"})   # the interior square nearest the door
    assert night_why(tmp_path)["step"] == "enter"
    r.answer()
    r.frame(x=110.5, y=200.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 110, "y": 201, "kind": "close", "filter": "all", "maxWeight": 0.0})
    assert night_why(tmp_path)["step"] == "close"
    r.answer()
    r.frame(x=110.5, y=200.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("sleep", {}) and night_why(tmp_path)["step"] == "sleep"
    assert [a.type for a in r.acts.history] == ["walkTo", "interact", "walkTo", "interact", "sleep"]
    assert sv.night.visited == {1}
    all_sends_valid(r)


def test_an_open_door_is_never_opened_again(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110, door=OPEN))
    r.frame(x=100.0, y=201.5, fatigue=0.65)
    tick(r, sv)
    r.answer()
    r.frame(x=109.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd()[0] == "walkTo" and night_why(tmp_path)["step"] == "enter"


def test_a_zombie_within_danger_r_sends_no_night_command(tmp_path):
    r = Rig(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=100.0, y=201.5, fatigue=0.65, zombies=[zombie(1, 104.0, 201.5)])
    n = Night(r.world, r.acts, r.clock)
    n.observe()
    assert n.choose() is None and n.why["threat"] is True
    r.frame(x=100.0, y=201.5, fatigue=0.65, zombies=[zombie(1, 108.0, 201.5)])   # 8 tiles: no threat, the walk goes
    assert n.choose() is not None and r.acts.history == []


def test_a_zombie_within_danger_r_leaves_the_tick_to_the_threat_branch(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=100.0, y=201.5, fatigue=0.65, zombies=[zombie(1, 103.0, 201.5)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat"


def test_a_failed_open_shuns_the_building_and_the_next_is_tried(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110) + house(2, 120))
    r.frame(x=100.0, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert night_why(tmp_path)["building"] == 1
    r.answer()
    r.frame(x=109.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd()[1]["kind"] == "open"
    r.answer({"state": "failed", "reason": "locked"})
    r.frame(x=109.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 119.5, "y": 201.5, "gait": "walk"})
    assert night_why(tmp_path)["building"] == 2 and night_why(tmp_path)["shunned"] == [1]
    assert sv.night.shunned == {1: 480.0}
    r.frame(x=109.5, y=201.5, fatigue=0.65, game_min=599.0)   # still inside SHUN_MIN
    assert sv.night.shunned_now() == {1}
    r.frame(x=109.5, y=201.5, fatigue=0.65, game_min=600.0)   # SHUN_MIN game minutes on: B1 again
    assert sv.night.shunned_now() == set()


@pytest.mark.parametrize("reason", ["not adjacent", "stuck", "no path", "no square"])
def test_a_walk_or_approach_failure_shuns_the_building(tmp_path, reason):
    r, sv = make(tmp_path)
    r.scan(house(1, 110) + house(2, 120))
    r.frame(x=100.0, y=201.5, fatigue=0.65)
    tick(r, sv)
    r.answer({"state": "failed", "reason": reason})
    r.frame(x=100.0, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert night_why(tmp_path)["building"] == 2 and sv.night.shunned_now() == {1}


def test_a_superseded_step_is_sent_again(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=100.0, y=201.5, fatigue=0.65)
    tick(r, sv)
    r.answer({"state": "failed", "reason": "superseded"})
    r.frame(x=100.0, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 109.5, "y": 201.5, "gait": "walk"}) and sv.night.shunned == {}


def test_a_building_the_character_stood_in_is_preferred(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110) + house(2, 120))
    r.frame(x=121.5, y=201.5)                                 # standing in building 2, not tired
    tick(r, sv)
    assert sv.night.visited == {2}
    r.frame(x=100.0, y=201.5, fatigue=0.65)                   # building 1 is nearer, building 2 known
    tick(r, sv)
    assert night_why(tmp_path)["building"] == 2


def test_no_interior_known_sets_want_shelter_and_passes(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(x, y) for x in range(99, 102) for y in range(199, 202)])
    r.frame(fatigue=0.65)
    tick(r, sv)
    assert sv.night.want_shelter is True and last(tmp_path)["branch"] != "night"
    assert night_why(tmp_path)["want_shelter"] is True


def test_an_interior_with_no_door_known_is_no_shelter(tmp_path):
    r, sv = make(tmp_path)
    r.scan([s for s in house(1, 110) if s["door"] is None])
    r.frame(x=100.0, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert sv.night.want_shelter is True and last(tmp_path)["branch"] != "night"


def test_not_wanting_clears_want_shelter(tmp_path):
    r, sv = make(tmp_path)
    r.frame(fatigue=0.65)
    tick(r, sv)
    assert sv.night.want_shelter is True
    r.frame(fatigue=0.1)
    tick(r, sv)
    assert sv.night.want_shelter is False


# ================================================================ inside: the sleep
def test_on_an_interior_square_tired_sleeps_at_once(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=111.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("sleep", {}) and [a.type for a in r.acts.history] == ["sleep"]
    assert last(tmp_path)["branch"] == "night"


def test_a_sleep_refused_not_safe_holds_the_branch_for_not_safe_s(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110) + [square(x, y) for x in range(99, 102) for y in range(199, 202)])
    r.frame(x=111.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    end(r, {"state": "rejected", "reason": "not safe"})
    for i in range(11):                                       # 2.5 .. 27.5 s: held, nothing sent, no lower branch
        r.advance(2.5)
        r.frame(x=111.5, y=201.5, fatigue=0.65)
        assert tick(r, sv) is None, i
        d = last(tmp_path)
        assert d["branch"] == "night" and d["sent"] is False and night_why(tmp_path)["hold"] > 0.0, i
    r.advance(2.5)                                            # 30.0 s: tried again
    r.frame(x=111.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("sleep", {}) and [a.type for a in r.acts.history] == ["sleep", "sleep"]


def test_a_sleep_done_rested_ends_the_want_until_fatigue_reads_tired_again(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110) + [square(x, y) for x in range(99, 102) for y in range(199, 202)])
    r.frame(x=111.5, y=201.5, fatigue=0.65, hour=23.0)
    tick(r, sv)
    r.answer(DONE_SLEEP)
    r.frame(x=111.5, y=201.5, fatigue=0.35, hour=23.0, game_min=960.0)   # late and above LATE_FATIGUE, but rested
    tick(r, sv)
    assert last(tmp_path)["branch"] != "night" and sv.night.wants() is False
    assert sv.night.last_sleep == {"gameMin": 960.0, "sleptH": 8.0, "fatigueBefore": 0.65, "fatigueAfter": 0.05,
                                   "bedType": "floor"}
    r.answer()
    r.frame(x=111.5, y=201.5, fatigue=0.65, hour=23.0)
    tick(r, sv)
    assert r.cmd() == ("sleep", {}) and last(tmp_path)["branch"] == "night"


def test_a_running_sleep_is_held_when_fatigue_falls_under_the_want(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110) + [square(x, y) for x in range(99, 102) for y in range(199, 202)])
    r.frame(x=111.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    r.fake.answer({"sleep": ["accepted"]})
    r.pump()
    r.frame(x=111.5, y=201.5, fatigue=0.2)                    # asleep, the fatigue falling: never superseded
    assert tick(r, sv) is None
    d = last(tmp_path)
    assert d["branch"] == "night" and d["sent"] is False and [a.type for a in r.acts.history] == ["sleep"]


# ================================================================ Task 12 fix 1
def two_door_house(exterior2=None):
    """house(1, 110) with an open interior door at (111, 201) between two rooms; with `exterior2`, a second exterior
    door on the west wall at (110, 202)."""
    sqs = house(1, 110)
    for s in sqs:
        if (s["x"], s["y"]) == (111, 201):
            s["door"] = dict(OPEN)
        if exterior2 is not None and (s["x"], s["y"]) == (110, 202):
            s["door"], s["blockW"] = dict(exterior2), not exterior2["open"]
    return sqs


def test_an_interior_door_is_never_the_shelters_door(tmp_path):
    r, sv = make(tmp_path)
    r.scan(two_door_house())
    r.frame(x=100.0, y=201.5, fatigue=0.65)
    assert N.exterior_doors(r.world, 1, 0) == [(110, 201, 0)]
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 109.5, "y": 201.5, "gait": "walk"})
    assert sv.night.shunned == {} and sv.night.want_shelter is False


def test_a_failed_open_tries_the_buildings_next_exterior_door_before_the_shun(tmp_path):
    r, sv = make(tmp_path)
    r.scan(two_door_house(exterior2=LOCKED))
    r.frame(x=109.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 110, "y": 201, "kind": "open", "filter": "all", "maxWeight": 0.0})
    r.answer({"state": "failed", "reason": "locked"})
    r.frame(x=109.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("interact", {"x": 110, "y": 202, "kind": "open", "filter": "all", "maxWeight": 0.0})
    assert sv.night.shunned == {} and night_why(tmp_path)["ended"] == "next door"
    r.answer({"state": "failed", "reason": "locked"})
    r.frame(x=109.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert sv.night.shunned == {1: 480.0} and sv.night.want_shelter is True


def test_a_sleep_refused_not_allowed_ends_the_want_for_the_session(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110) + [square(x, y) for x in range(99, 102) for y in range(199, 202)])
    r.frame(x=111.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    end(r, {"state": "rejected", "reason": "not allowed"})
    r.frame(x=111.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert sv.night.allowed is False and last(tmp_path)["branch"] != "night"
    assert night_why(tmp_path) == {"wants": False, "barred": "not allowed"}   # logged once
    for _ in range(12):
        if r.acts.current is not None:
            r.answer()
        r.advance(2.5)
        r.frame(x=111.5, y=201.5, fatigue=0.9, hour=23.0)
        tick(r, sv)
        assert night_why(tmp_path) == {"wants": False}
    assert [a.type for a in r.acts.history].count("sleep") == 1


def test_a_sleep_refused_not_valid_holds_the_branch_for_not_valid_s(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110) + [square(x, y) for x in range(99, 102) for y in range(199, 202)])
    r.frame(x=111.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    end(r, {"state": "rejected", "reason": "not valid"})
    for i in range(23):                                       # 2.5 .. 57.5 s: held, nothing sent
        r.advance(2.5)
        r.frame(x=111.5, y=201.5, fatigue=0.65)
        assert tick(r, sv) is None, i
        assert last(tmp_path)["branch"] == "night" and night_why(tmp_path)["hold"] > 0.0, i
    r.advance(2.5)                                            # 60.0 s: tried again
    r.frame(x=111.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert [a.type for a in r.acts.history] == ["sleep", "sleep"]


def test_the_rested_latch_clears_with_the_new_day(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110) + [square(x, y) for x in range(99, 102) for y in range(199, 202)])
    r.frame(x=111.5, y=201.5, fatigue=0.65, hour=23.0)
    tick(r, sv)
    r.answer(DONE_SLEEP)
    r.frame(x=111.5, y=201.5, fatigue=0.35, hour=23.0)
    tick(r, sv)
    assert sv.night.rested is True and sv.night.wants() is False
    if r.acts.current is not None:
        r.answer()
    r.frame(x=111.5, y=201.5, fatigue=0.1, hour=6.0)           # the next morning
    tick(r, sv)
    assert sv.night.rested is False
    if r.acts.current is not None:
        r.answer()
    r.frame(x=111.5, y=201.5, fatigue=0.5, hour=22.5)          # the next night, under TIRED_T
    tick(r, sv)
    assert sv.night.wants() is True and r.cmd() == ("sleep", {}) and last(tmp_path)["branch"] == "night"


@pytest.mark.parametrize("reason", ["not adjacent", "no door", "interrupted"])
def test_a_failed_close_never_shuns_the_shelter_the_character_is_in(tmp_path, reason):
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=109.5, y=201.5, fatigue=0.65)
    tick(r, sv)                                               # open
    r.answer()
    r.frame(x=109.5, y=201.5, fatigue=0.65)
    tick(r, sv)                                               # enter
    r.answer()
    r.frame(x=110.5, y=200.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd()[1]["kind"] == "close"
    r.answer({"state": "failed", "reason": reason})
    r.frame(x=110.5, y=200.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("sleep", {}) and sv.night.shunned == {} and night_why(tmp_path)["ended"] == "passed"


def test_a_step_ending_otherwise_is_retried_step_retries_times_then_the_building_is_shunned(tmp_path):
    r = Rig(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=100.0, y=201.5, fatigue=0.65)
    n = Night(r.world, r.acts, r.clock)
    for i in range(N.STEP_RETRIES):
        assert n.step() is not None and r.cmd()[0] == "walkTo", i
        r.answer({"state": "failed", "reason": "interrupted"})
        r.frame(x=100.0, y=201.5, fatigue=0.65)
    assert n.step() is None and n.shunned == {1: 480.0} and n.want_shelter is True
    assert [a.type for a in r.acts.history] == ["walkTo"] * N.STEP_RETRIES


def test_the_night_keeps_its_record_for_loop_night(tmp_path):
    r, sv = make(tmp_path)
    r.scan(house(1, 110))
    for x, y in ((109.5, 201.5), (109.5, 201.5), (110.5, 200.5), (110.5, 200.5)):
        r.frame(x=x, y=y, fatigue=0.65)
        tick(r, sv)
        assert night_why(tmp_path)["aid"] == r.acts.history[-1].aid
        r.advance(1.0)
        r.answer(DONE_SLEEP if r.cmd()[0] == "sleep" else "done")
    assert r.cmd() == ("sleep", {})
    r.frame(x=110.5, y=200.5, fatigue=0.05)
    tick(r, sv)
    n = sv.night
    assert n.wants_n == 4
    assert [(s["step"], s["building"], s["state"]) for s in n.steps] == [("open", 1, "done"), ("enter", 1, "done"),
                                                                         ("close", 1, "done")]
    assert [s["aid"] for s in n.steps] == [a.aid for a in r.acts.history[:3]]
    assert n.steps[0]["startS"] == 0.0 and n.steps[0]["endS"] == 1.0
    assert len(n.sleeps) == 1 and n.sleeps[0]["state"] == "done" and n.sleeps[0]["sleptH"] == 8.0
    assert n.sleeps[0]["fatigueAfter"] == 0.05 and n.sleeps[0]["result"]["bedType"] == "floor"


def test_the_shelter_machine_runs_without_night(tmp_path):
    """Task 13's Shelter goal calls the same functions."""
    r = Rig(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=100.0, y=201.5)
    plan = N.shelter_plan(r.world, 1)
    assert plan["doors"] == [(110, 201, 0)] and plan["inside"] == (110, 200, 0) and plan["step"] == "approach"
    cmd, step = N.shelter_step(r.world, plan)
    assert step == "approach" and cmd.TYPE == "walkTo"
    assert N.shelter_plan(r.world, 2) is None
