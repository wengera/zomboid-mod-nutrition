"""Survival 23 (survival iteration 21; Plan 28 Task 3; F11, `f_goals_12-20261103-144240`, its `GUIDE.md` §§ 2, 3 and 5:
the seven bites, five after a shove at point blank that knocked nothing down, the ten `out_of_reach` lines while 14725
closed from 7.712846482962758 tiles after the corner's break, the 22 shoves and no swing at 14725 under the arms' pain,
the stomp a145 at 14725 refused `busy` while a144 ran at 14630, then 14725 left lying 2.5172987398919933 tiles off, the
scratched parts 4, 6 and 8 never dressed; rows #4580, #4581, #4583 and #4585; the jar read's shove reach, #4592). The
fake mod over PZA/1.7.2 (the part record's `wound`); each test's geometry is simplified from the line its docstring
names.

- P28-D, a `busy` rejection is no refusal (`BUSY_RETRY`): a shove or a stomp `rejected` `busy` leaves no
  `swing_refused` record; the next send of that kind at that id is logged `busy_retry` {target, kind}.
"""
import math

import pytest

from agent.base.planner import care as C
from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T
from agent.base import pza1
from agent.base.pza1 import Shove, Stomp

from .test_policies import Rig, square
from .test_survive import last, make, threat_why, tick
from .test_survive_g import care_frame, care_why, garment, hello152, hold, part
from .test_survive_q import DONE_SHOVE, GROUP3, STIFF, fr, z


def fight(r, **k):
    """A Fight on the rig (every rule of `fight.FIGHT_RULES` on), `k` set on it."""
    f = F.Fight(r.world, r.acts, r.clock)
    for name, v in k.items():
        setattr(f, name, v)
    return f


def end(r, a, state, reason="", result=None):
    """Action `a` ends `state` (`reason`, `result`) by its act line."""
    r.fake.act(a.aid, state, a.type, reason=reason, result=result)
    r.pump()


def accept(r, a):
    r.fake.act(a.aid, "accepted", a.type)
    r.pump()


# ================================================================ P28-D: a `busy` rejection is no refusal
F11_LYING = 2.5172987398919933   # a146's 14725 read fallen this far off on lines 642-651, nothing within 6 tiles


def busy_rig(tmp_path, reason="busy"):
    """F11's a144 to a146 simplified (lines 630 to 642): a Fight cornered as F11's was (`point_blank`) sent the stomp
    a145 at 14725, fallen 1.2 tiles off, while its attack a144 at 14630 ran; the stomp's end is `rejected` `reason`;
    then 14630 reads dead (its corpse listed 0.5 tiles off) and 14725 fallen F11_LYING tiles off, no standing zombie
    within KEEP_R. Returns (r, f) before the next step."""
    r = Rig(tmp_path)
    r.frame(zombies=[z(14725, 101.2, floor=True)])
    f = fight(r, point_blank=True)
    end(r, f.send(Stomp(14725)), "rejected", reason)
    r.advance(0.5)
    r.frame(zombies=[z(14725, 100.0 + F11_LYING, floor=True), z(14630, 99.5, floor=True)])
    f.dead[14630] = r.clock() + P.UNREACHABLE_S
    return r, f


def test_f11_s_stomp_rejected_busy_goes_again_on_the_next_tick(tmp_path):
    """F11's line 642: 14725 lies F11_LYING tiles off (beyond FIGHT_REACH, within FINISH_R) with nobody standing near,
    and the stomp a145 refused `busy` while a144 ran: no refusal is recorded at 14725, so the finish rule lists it and
    the stomp goes again (its walk in), logged `busy_retry` {target 14725, kind "stomp"}, the latch cleared."""
    r, f = busy_rig(tmp_path)
    a = f.step()
    assert (a.type, a.args) == ("stomp", {"targetId": 14725})
    assert f.why["busy_retry"] == {"target": 14725, "kind": "stomp"} and f.why["downed"] == 14725
    assert ("stomp", 14725) not in f.swing_refused and f._busy_retry is None


def test_with_busy_retry_off_the_busy_stomp_is_refused_and_the_drifted_pin_holds_out_of_reach(tmp_path):
    """The same with the `busy_retry` rule off (Survive's `BUSY_RETRY`): the refusal holds the stomp off 14725 for
    SWING_SKIP_S, the finish rule leaves it out beyond FIGHT_REACH, and the cornered Fight sends nothing
    (`out_of_reach`), F11's lines 642 to 651."""
    r, f = busy_rig(tmp_path)
    f.rules = f.rules - {"busy_retry"}
    assert f.step() is None and f.why["out_of_reach"] is True and "busy_retry" not in f.why
    assert ("stomp", 14725) in f.swing_refused


def test_a_stomp_rejected_not_valid_is_refused_for_swing_skip_s_as_before(tmp_path):
    """A stomp `rejected` `not valid` says something about the target: no stomp at it for SWING_SKIP_S (P24-AL), then
    the stomp, never logged `busy_retry`."""
    r, f = busy_rig(tmp_path, "not valid")
    assert f.step() is None and f.why["out_of_reach"] is True and "busy_retry" not in f.why
    r.advance(P.SWING_SKIP_S - 1.0)
    r.frame(zombies=[z(14725, 100.0 + F11_LYING, floor=True)])
    assert f.step() is None
    r.advance(1.0)
    r.frame(zombies=[z(14725, 100.0 + F11_LYING, floor=True)])
    a = f.step()
    assert (a.type, a.args) == ("stomp", {"targetId": 14725}) and "busy_retry" not in f.why


def test_a_shove_rejected_busy_goes_again(tmp_path):
    """A shove at a chaser at point blank under the arms' pain 30 (P24-AG's) rejected `busy`: the next tick shoves
    again, logged `busy_retry` {target, kind "shove"}; with the rule off the refusal holds the shove off and the
    wounded fight's backpedal goes (P24-AP)."""
    for on in (True, False):
        d = tmp_path / str(on)
        d.mkdir()
        r = Rig(d)
        fr(r, [z(9, 100.9)], 30.0)
        f = fight(r)
        if not on:
            f.rules = f.rules - {"busy_retry"}
        a = f.step()
        assert (a.type, a.args) == ("shove", {"targetId": 9})
        end(r, a, "rejected", "busy")
        r.advance(0.5)
        fr(r, [z(9, 100.9)], 30.0)
        b = f.step()
        if on:
            assert (b.type, b.args) == ("shove", {"targetId": 9}) and f.why["busy_retry"] == {"target": 9,
                                                                                            "kind": "shove"}
        else:
            assert b.type == "aim" and f.why["leg"] == "back" and "busy_retry" not in f.why


def test_the_busy_latch_clears_on_any_other_end_at_that_id(tmp_path):
    """The latch (`_busy_retry`) is cleared by the next send of its kind at its id, and also by any other end read at
    that id (amendment 4): the stomp rejected `busy`, then a shove at 14725 ended done: the latch is gone."""
    r, f = busy_rig(tmp_path)
    f.observe()
    assert f._busy_retry == ("stomp", 14725)
    f.send(Shove(14725))
    r.answer(DONE_SHOVE)
    f.observe()
    assert f._busy_retry is None


def test_the_busy_retry_switch():
    assert "BUSY_RETRY" in S.T11_SWITCHES and T.Threat.BUSY_RETRY is True and "busy_retry" in F.FIGHT_RULES
