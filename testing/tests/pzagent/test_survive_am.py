"""Plan 34 Task 2 (the column; F19, `f_goals_19-20261109-060929`, GUIDE.md § 3 "The door": on decision line 1595 the
leave's leg turned `door` with the nearest standing zombie at 0.37 tiles, building 12's one-room door at (10620, 10629)
on the west edge of that square; the plan's `enter` walk to (10619.5, 10629.5) ended `done` 0.93 tiles off it with the
character outside, and line 1602's close shut the door with the character at (10620.37, 10629.18), east of the door's
edge, 12431 at 0.60 tiles; the bite came 0.334 s later, then the drag-down): two rules behind `threat.Threat`'s
switches (`survive.T19_SWITCHES`). Fix C of ruling P34-A (the drag guard's waiting shove held under SHOVE_CLEAR) went
with the guard's shove at Plan 35 Task 8 (its tests named in the task report).

- DOOR_INSIDE (`flee.Flee._at_post`, `_close_refused`, the Flee's `door_inside` rule): every shelter plan's enter is
  read on its `done` against `policies.on_post` (a room square of the plan's building); outside, the enter is walked
  again to the stand's post square (`policies.stand_post`, `enter_to`), a retry, and the plain plan is dropped at
  STEP_RETRIES (the stand plan falls back as before); the close (the step and the re-close) is sent only from a room
  square of the building with the door not guarded (`_door_guarded`), else the plan is dropped, logged
  `shelter_drop` {shelter, step, ended | refused, retries}.
- LEAVE_DOOR_RACE (`group.ThreatGroup._leave_door`, `_leave_leg`): the leave picks no new door with the nearest standing
  zombie within DOOR_RACE_R (`door_refused` "race") nor a door whose building has no second way out (`door_verdicts`
  with `second_exit` True: `door_refused` "one_exit"), and a running door plan before its close is dropped with a
  standing zombie within DOOR_ABORT_R (`door_dropped` "abort"), the leg re-read on the same line.

The fixtures are synthetic, built from F19's geometry (the GUIDE's numbers), never a replay; the fake mod."""
import math

import pytest

from agent.base.planner import flee as FL
from agent.base.planner import night as N
from agent.base.planner import policies as P
from agent.base.planner.flee import Flee

from .test_night import CLOSED, OPEN, house
from .test_policies import Rig, square, zombie
from .test_survive import threat_why, tick
from .test_survive_ak import closing, shifted_house

DOOR = (10620, 10629, 0)        # F19's door, on the west edge of the outdoor square east of building 12
INSIDE = (10619, 10629, 0)      # the plan's `inside`: the threshold room square
POST = (10618, 10629, 0)        # `stand_post`: the room square one on from the threshold
APPROACH = (10621.5, 10629.5)   # the approach square's centre, where the enter starts
LINE_1602 = (10620.37, 10629.18)   # where F19's close went: east of the door's edge, outside
FAR = (10625.5, 10633.5)        # a held zombie away from the door (no guard, no corridor)


def f19_house(door=OPEN):
    """Building 12 (room squares 10617..10619 by 10628..10630, `room` and `building` 12), its one door on the west edge
    of the outdoor square (10620, 10629) (`blockW` while it reads closed), walls round the rest, open ground about
    it."""
    sqs = []
    for x in range(10612, 10627):
        for y in range(10624, 10635):
            if 10617 <= x <= 10619 and 10628 <= y <= 10630:
                sqs.append(square(x, y, room="room", building=12, blockW=x == 10617, edgeW=x == 10617,
                                  blockN=y == 10628, edgeN=y == 10628))
                continue
            east = x == 10620 and 10628 <= y <= 10630
            south = y == 10631 and 10617 <= x <= 10619
            at_door = (x, y) == DOOR[:2]
            sqs.append(square(x, y, door=dict(door) if at_door else None,
                              blockW=east and not (at_door and door["open"]), edgeW=east, blockN=south, edgeN=south))
    return sqs


def zf(zid, at, me):
    return zombie(zid, at[0], at[1], me=me)


def flee_at(tmp_path, me, zs=(FAR,), step="enter", stand=False, rule=True):
    """A Flee on a fresh Rig over F19's house, the player at `me`, held zombies at `zs`, its plan kept to F19's door at
    `step` (a stand plan with `stand`: its way and post as `Flee.choose` sets them), the `door_inside` rule `rule`."""
    r = Rig(tmp_path)
    r.scan(f19_house())
    r.frame(x=me[0], y=me[1], zombies=[zf(i + 1, at, me) for i, at in enumerate(zs)])
    f = Flee(r.world, r.acts, r.clock)
    if not rule:
        f.rules = f.rules - {"door_inside"}
    f.plan = N.shelter_plan(r.world, 12, door=DOOR, step=step)
    f.picked = True
    if stand:
        f.plan.update(stand=True, way=r.world.door_way(DOOR), post=POST)
    return r, f


def move(r, me, zs=(FAR,)):
    r.frame(x=me[0], y=me[1], zombies=[zf(i + 1, at, me) for i, at in enumerate(zs)])


def closed(r):
    """The last command is the close of F19's door."""
    t, a = r.cmd()
    return t == "interact" and (a["x"], a["y"], a["kind"]) == (10620, 10629, "close")


def sent(r):
    return [(a.type, a.args.get("kind")) for a in r.acts.history]


# ================================================================ DOOR_INSIDE
def test_the_fixture_reads_f19_s_door(tmp_path):
    """The plan's `inside` is the threshold square and `stand_post` the square beyond it; F19's close position reads
    off the building's room squares (the outdoor door square)."""
    assert "door_inside" in FL.FLEE_RULES
    r, f = flee_at(tmp_path, APPROACH)
    assert f.plan["inside"] == INSIDE and r.world.door_way(DOOR) == (INSIDE, DOOR)
    assert P.stand_post(r.world, r.world.door_way(DOOR), 12) == POST
    move(r, LINE_1602)
    assert not P.on_post(r.world, 12)
    move(r, (10619.4, 10629.5))
    assert P.on_post(r.world, 12)


def test_a_plain_plan_s_enter_done_outside_is_walked_again_to_the_post(tmp_path):
    """(a) The plain plan's enter (to the threshold square's centre) ended `done` with the character at F19's line
    1602 position: the step goes back to `enter` with `enter_to` the post, its walk sent there, logged {shelter 12,
    step "enter", ended "outside", retries 1}; no close is sent."""
    r, f = flee_at(tmp_path, APPROACH)
    f.step()
    assert r.cmd() == ("walkTo", {"x": 10619.5, "y": 10629.5, "gait": "run"})
    r.answer()
    move(r, LINE_1602)
    f.step()
    assert r.cmd() == ("walkTo", {"x": 10618.5, "y": 10629.5, "gait": "run"})
    assert f.plan["step"] == "enter" and f.plan["enter_to"] == POST and f.plan["retries"] == 1
    assert f.why == {"shelter": 12, "step": "enter", "ended": "outside", "retries": 1}
    assert ("interact", "close") not in sent(r)


def test_with_door_inside_off_the_plain_plan_closes_from_outside_as_before(tmp_path):
    """(a)'s pin: with the `door_inside` rule off (Survive's DOOR_INSIDE off), the enter's `done` outside advances to
    the close, sent from F19's line 1602 position as F19 sent it."""
    r, f = flee_at(tmp_path, APPROACH, rule=False)
    f.step()
    r.answer()
    move(r, LINE_1602)
    f.step()
    assert closed(r)


def test_an_enter_done_inside_goes_on_to_the_close(tmp_path):
    """The enter's `done` on a room square of the building: the close is sent (no retry)."""
    r, f = flee_at(tmp_path, APPROACH)
    f.step()
    r.answer()
    move(r, (10619.4, 10629.5))
    f.step()
    assert closed(r) and f.plan["retries"] == 0


def test_the_close_from_inside_is_refused_with_a_zombie_at_the_door(tmp_path):
    """(b) The character inside at (10619.4, 10629.5), a zombie at (10620.6, 10629.5) on the door square: the close is
    refused `guarded` and the plan dropped (`shelter_drop` {shelter 12, step "close", refused "guarded"}); with no
    zombie near, the close is sent."""
    me = (10619.4, 10629.5)
    r, f = flee_at(tmp_path, me, zs=((10620.6, 10629.5),), step="close")
    f.step()
    assert ("interact", "close") not in sent(r) and f.plan is None
    assert f.why["shelter_drop"] == {"shelter": 12, "step": "close", "refused": "guarded"}
    (tmp_path / "clear").mkdir()
    r2, f2 = flee_at(tmp_path / "clear", me, step="close")
    f2.step()
    assert closed(r2) and "shelter_drop" not in f2.why


def test_the_close_from_outside_is_refused(tmp_path):
    """(c) The character outside (F19's line 1602 position) at the close step, no zombie near the door: the close is
    refused `outside` and the plan dropped; off the room squares, the steer follows."""
    r, f = flee_at(tmp_path, LINE_1602, step="close")
    f.step()
    assert ("interact", "close") not in sent(r) and f.plan is None
    assert f.why["shelter_drop"] == {"shelter": 12, "step": "close", "refused": "outside"}
    assert r.cmd()[0] == "steer"


def test_the_close_with_door_inside_off_is_sent_from_outside(tmp_path):
    """(c)'s pin: with the rule off the close step is sent from outside as before."""
    r, f = flee_at(tmp_path, LINE_1602, step="close", rule=False)
    f.step()
    assert closed(r)


def test_step_retries_enters_outside_drop_the_plain_plan(tmp_path):
    """(d) STEP_RETRIES enters ending outside: the first two walked again to the post, the third drops the plain plan
    (`shelter_drop` {shelter 12, step "enter", ended "outside", retries 3}), the steer following."""
    r, f = flee_at(tmp_path, APPROACH)
    f.step()
    for k in range(1, N.STEP_RETRIES):
        r.answer()
        move(r, LINE_1602)
        f.step()
        assert r.cmd() == ("walkTo", {"x": 10618.5, "y": 10629.5, "gait": "run"}) and f.plan["retries"] == k
    r.answer()
    move(r, LINE_1602)
    f.step()
    assert f.plan is None and f.picked is True and f.ended == "outside"
    assert f.why["shelter_drop"] == {"shelter": 12, "step": "enter", "ended": "outside", "retries": N.STEP_RETRIES}
    assert r.cmd()[0] == "steer" and ("interact", "close") not in sent(r)


def test_step_retries_enters_outside_give_the_stand_up_as_before(tmp_path):
    """(d) The stand plan: STEP_RETRIES enters ending outside give the stand up (`stand` False, the step at `close`) as
    before; each retry's walk goes to the post."""
    r, f = flee_at(tmp_path, APPROACH, stand=True)
    f.step()
    assert r.cmd() == ("walkTo", {"x": 10618.5, "y": 10629.5, "gait": "run"})
    for k in range(1, N.STEP_RETRIES):
        r.answer()
        move(r, LINE_1602)
        f.step()
        assert r.cmd() == ("walkTo", {"x": 10618.5, "y": 10629.5, "gait": "run"}) and f.plan["retries"] == k
    r.answer()
    move(r, LINE_1602)
    f.observe()
    assert f.plan["stand"] is False and f.plan["step"] == "close" and f.plan["retries"] == N.STEP_RETRIES


def test_the_stand_plan_s_enter_on_its_post_starts_the_stand(tmp_path):
    """The stand plan's enter ending on its post starts the stand as before (`stand`, `stood`)."""
    r, f = flee_at(tmp_path, APPROACH, stand=True)
    f.step()
    r.answer()
    move(r, (10618.9, 10629.5))
    f.observe()
    assert f.plan["step"] == "stand" and f.plan["stood"] is True


def test_the_re_close_reads_the_same_guard(tmp_path):
    """The sheltered re-close (the plan `done`, the door reading open, the hold broken) reads the close's guard
    (`_door_guarded`, factored out of it): from inside with nobody near, the re-close; with a zombie on the door square,
    the plan dropped."""
    me = (10619.4, 10629.5)
    r, f = flee_at(tmp_path, me, zs=((10623.5, 10629.5),), step="done")
    f.hold_ok = False
    f.step()
    assert closed(r) and f.why["step"] == "reclose"
    (tmp_path / "g").mkdir()
    r2, f2 = flee_at(tmp_path / "g", me, zs=((10620.6, 10629.5),), step="done")
    f2.hold_ok = False
    f2.step()
    assert ("interact", "close") not in sent(r2) and f2.plan is None


def test_next_door_clears_enter_to():
    """`night._next_door` clears the plan's `enter_to`; `shelter_step`'s enter walks to `enter_to`, else the post, else
    `inside`."""
    plan = {"doors": [(1, 1, 0), (5, 1, 0)], "door_i": 0, "rooms": [(2, 1, 0), (4, 1, 0)], "inside": (2, 1, 0),
            "step": "enter", "enter_to": (3, 1, 0)}
    assert N._next_door(plan) and "enter_to" not in plan and plan["step"] == "approach"


# ================================================================ LEAVE_DOOR_RACE
FAR3 = ((97.4, 200.6), (97.45, 199.9), (100.5, 206.3))   # the trio's second line at 3.10, 3.11 and 5.8 tiles: closing


def test_the_race_constants():
    assert (P.DOOR_RACE_R, P.DOOR_ABORT_R) == (3.0, 1.0)


def test_a_door_raced_by_the_nearest_standing_within_door_race_r_is_refused(tmp_path):
    """(e) The leave with an `ok` door within LEAVE_DOOR_R (house 1 moved 4 tiles west, its door 5.1 tiles east) and
    the nearest standing zombie at 2.90 tiles (2 at (97.65, 199.95), within DOOR_RACE_R): no door (`door_refused`
    "race", `near` its tiles), the leg `retreat`; at 3.10 tiles the door leg."""
    r, sv = closing(tmp_path, scan=shifted_house(-4))
    why = threat_why(tmp_path)
    gl = why["group_leave"]
    assert gl["door_refused"] == "race" and gl["leg"] == "retreat"
    assert gl["near"] == pytest.approx(math.hypot(2.85, 0.55))
    assert why["fight"] is True and r.cmd()[0] == "aim"
    (tmp_path / "far").mkdir()
    r2, sv2 = closing(tmp_path / "far", second=FAR3, scan=shifted_house(-4))
    gl2 = threat_why(tmp_path / "far")["group_leave"]
    assert gl2["leg"] == "door" and "door_refused" not in gl2
    assert r2.cmd() == ("walkTo", {"x": 105.5, "y": 201.5, "gait": "run"})


def test_with_leave_door_race_off_the_raced_door_is_walked_to(tmp_path):
    """(e)'s pin: the rule off, the door at 2.90 tiles is the leave's leg as before."""
    r, sv = closing(tmp_path, scan=shifted_house(-4), off=("LEAVE_DOOR_RACE",))
    gl = threat_why(tmp_path)["group_leave"]
    assert gl["leg"] == "door" and "door_refused" not in gl


def test_a_running_door_plan_is_dropped_with_a_standing_zombie_within_door_abort_r(tmp_path):
    """(f) The door leg's approach walk running (the plan before its close) and a standing zombie at 0.9 tiles: the
    plan is dropped (`door_dropped` "abort", `near` 0.9), the leg re-read on the same line (the retreat: three within
    DANGER_R, none within STAND_MIN_R)."""
    r, sv = closing(tmp_path, second=FAR3, scan=shifted_house(-4))
    assert threat_why(tmp_path)["group_leave"]["leg"] == "door"
    flee = sv.flee
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    r.advance(0.5)
    me = (103.5, 201.5)
    zs = [zombie(1, 102.6, 201.5, me=me), zombie(2, 100.5, 201.0, me=me), zombie(3, 101.0, 204.0, me=me)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    gl = threat_why(tmp_path)["group_leave"]
    assert gl["door_dropped"] == "abort" and gl["near"] == pytest.approx(0.9) and gl["leg"] == "retreat"
    assert flee.plan is None and sv.mode == "fight" and r.cmd()[0] != "walkTo"


def test_a_one_exit_door_is_refused_for_the_leave(tmp_path):
    """(g) A one-door building with no window (house 1 at x 106, its one west door): the leave's door is refused
    `one_exit` (`door_verdicts` with `second_exit` True), the leg `retreat`; with LEAVE_DOOR_RACE off the door as
    before (a fresh Flee's read is no stand's, so no `one_exit`)."""
    one = house(1, 106, door=CLOSED)
    r, sv = closing(tmp_path, second=FAR3, scan=one)
    gl = threat_why(tmp_path)["group_leave"]
    assert gl["door_refused"] == "one_exit" and gl["leg"] == "retreat"
    (tmp_path / "off").mkdir()
    r2, sv2 = closing(tmp_path / "off", second=FAR3, scan=one, off=("LEAVE_DOOR_RACE",))
    gl2 = threat_why(tmp_path / "off")["group_leave"]
    assert gl2["leg"] == "door" and gl2["door"] == [106, 201, 0]


def test_door_verdicts_second_exit_overrides_the_stand_s_rule(tmp_path):
    """`door_verdicts(ts, second_exit)`: True reads `one_exit` whatever `stand_ok`; False never; None the stand's rule
    as before."""
    r = Rig(tmp_path)
    r.scan(house(1, 106, door=CLOSED))
    r.frame(x=100.5, y=201.5, zombies=[zombie(1, 95.5, 201.5, me=(100.5, 201.5))])
    f = Flee(r.world, r.acts, r.clock)
    ts = list(r.world.zombies.values())
    assert [v for *_, v in f.door_verdicts(ts)] == ["ok"]
    assert [v for *_, v in f.door_verdicts(ts, second_exit=True)] == ["one_exit"]
    f.stand_ok = True
    assert [v for *_, v in f.door_verdicts(ts)] == ["one_exit"]
    assert [v for *_, v in f.door_verdicts(ts, second_exit=False)] == ["ok"]
