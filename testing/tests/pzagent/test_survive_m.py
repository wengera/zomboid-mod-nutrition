"""Survival 11 (Plan 24 Task 27; PZA/1.7's `shove` and `stomp`, `zombies[].onFloor`, `body.armPain`), the Fight's half:
ruling P24-AG's preference (at `body.armPain` STRAIN_SOFT the stomp on a fallen target and the shove at point blank
over a swing), ruling P24-AH (in a standing fight a second zombie inside KEEP_R with the pin in reach is shoved, the
nearer of the two, before the next swing; never a shove or stomp of another with a standing zombie within the
weapon's MinRange) and ruling P24-AL (finish the fallen: a downed zombie within FIGHT_REACH takes the stomp, else the
weapon's floor strike, the shove of a standing one at point blank first). The fake mod over PZA/1.7."""
import pytest

from agent.base import pza1
from agent.base.planner import policies as P
from agent.base.planner.policies import Fight

from .test_policies import Rig, all_sends_valid, zombie
from .test_survive import make, threat_why, tick

NO_SWINGS = tuple(t for t in pza1.ACTION_TYPES if t not in ("shove", "stomp"))   # a build before PZA/1.7's two


def z(zid, x, y=200.0, floor=False):
    return dict(zombie(zid, x, y), onFloor=True if floor else None)


def fr(r, zs, arm=None, **k):
    r.frame(zombies=list(zs), wounds={"armPain": arm}, **k)


def fight(tmp_path, zs, arm=None, caps=None, stance=False, pin=None):
    """A Fight on a fresh Rig (`caps` the hello's, default every type), the frame's zombies `zs`, `stance` set as
    Survive's `_stance_ok` sets it, pinned to `pin` (else the nearest at its first choose)."""
    r = Rig(tmp_path, caps=caps)
    fr(r, zs, arm)
    f = Fight(r.world, r.acts, r.clock, target=pin)
    f.stance = stance
    return r, f


def test_the_swing_constants():
    """#4372: the bat's MinRange 0.61 (the bare hand's 0.6); the Lua's SHOVE_R 1.5; a refused skill waits as a mark."""
    assert (P.STAND_MIN_R, P.SHOVE_R, P.SWING_SKIP_S) == (0.61, 1.5, P.UNREACHABLE_S)
    assert P.SWING_TYPES == ("attack", "aim", "shove", "stomp")


# ================================================================ P24-AG: the preference at STRAIN_SOFT
def test_arm_pain_12_with_a_fallen_pin_stomps(tmp_path):
    r, f = fight(tmp_path, [z(1, 101.0, floor=True)], arm=12.0)
    a = f.step()
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and f.why["downed"] == 1 and f.why["stomp"] is True
    all_sends_valid(r)


def test_arm_pain_12_with_a_standing_pin_at_point_blank_shoves(tmp_path):
    r, f = fight(tmp_path, [z(1, 100.8)], arm=12.0)
    a = f.step()
    assert (a.type, a.args) == ("shove", {"targetId": 1}) and f.why["shove"] == "strain" and f.why["strain"] == 12.0
    r.answer({"state": "done", "result": {"knockdown": False, "attackStarted": True, "targetDead": False}})
    fr(r, [z(1, 100.8)], 12.0)
    assert f.step().type == "shove"   # every swing while the arms hurt: the shove, never the swing


@pytest.mark.parametrize("arm", [9.99, None])
def test_under_10_the_point_blank_pin_takes_the_swing(tmp_path, arm):
    r, f = fight(tmp_path, [z(1, 100.8)], arm=arm)
    a = f.step()
    assert a.type == "attack" and "shove" not in f.why


def test_beyond_point_blank_the_strained_fight_still_swings(tmp_path):
    """P24-AG prefers the shove at point blank only: a standing pin at 1.5 tiles (in reach) takes the swing."""
    r, f = fight(tmp_path, [z(1, 101.5)], arm=15.0)
    assert f.step().type == "attack"


# ================================================================ P24-AH: the second zombie, and the stomp
def stance_in(tmp_path, zs, arm=None):
    """A standing Fight on pin 1 within reach, its `enter` leg sent and running (the stance held)."""
    r, f = fight(tmp_path, zs, arm=arm, stance=True, pin=1)
    a = f.step()
    assert a.type == "aim" and f.why["leg"] == "enter"
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    fr(r, zs, arm)
    return r, f


@pytest.mark.parametrize("pin_x,second_x,shoved", [(101.2, 102.0, 1), (101.8, 101.0, 2)])
def test_a_second_zombie_inside_keep_r_with_the_pin_in_reach_shoves_the_nearer(tmp_path, pin_x, second_x, shoved):
    """P24-AH: the stance held on pin 1 within FIGHT_REACH, zombie 2 inside KEEP_R: the nearer of the two is shoved
    before the next swing (`why` `shove` "second"); after the shove the swing goes, then the shove again."""
    zs = [z(1, pin_x), z(2, second_x)]
    r, f = stance_in(tmp_path, zs)
    a = f.step()
    assert (a.type, a.args) == ("shove", {"targetId": shoved}) and f.why["shove"] == "second"
    r.answer({"state": "done", "result": {"knockdown": False, "attackStarted": True, "targetDead": False}})
    fr(r, zs)
    a = f.step()
    while a.type == "aim":   # the shove released the stance: the enter leg again (the Lua's K.start)
        r.fake.answer({"aim": ["accepted"]})
        r.pump()
        fr(r, zs)
        a = f.step()
    assert (a.type, a.args) == ("attack", {"targetId": 1})
    all_sends_valid(r)


def test_no_second_zombie_or_none_inside_keep_r_takes_the_swing(tmp_path):
    for i, zs in enumerate(([z(1, 101.2)], [z(1, 101.2), z(2, 103.0)])):
        d = tmp_path / str(i)
        d.mkdir()
        r, f = stance_in(d, zs)
        assert f.step().type == "attack"


def test_outside_a_standing_fight_the_second_zombie_is_not_shoved(tmp_path):
    """P24-AH is the standing fight's: a Fight without the stance (the approach and swing) swings."""
    r, f = fight(tmp_path, [z(1, 101.2), z(2, 102.0)])
    assert f.step().type == "attack"


def test_a_fallen_pin_within_half_a_tile_is_stomped(tmp_path):
    r, f = fight(tmp_path, [z(1, 100.4, floor=True)])
    a = f.step()
    assert (a.type, a.args) == ("stomp", {"targetId": 1})


def test_another_standing_zombie_within_min_range_takes_no_shove_or_stomp(tmp_path):
    """P24-AH: the stomp's refusal read before the send: a standing zombie within STAND_MIN_R of the player makes the
    engine's call shove it, so the strained shove of pin 1 goes as the swing, and on a build without the shove the
    fallen pin takes the weapon's floor strike (P24-AL), never the stomp."""
    r, f = fight(tmp_path, [z(1, 100.9), z(2, 100.0, 200.5)], arm=15.0, pin=1)
    a = f.step()
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and "shove" not in f.why
    (tmp_path / "b").mkdir()
    caps = tuple(t for t in pza1.ACTION_TYPES if t != "shove")
    r2, f2 = fight(tmp_path / "b", [z(1, 101.0, floor=True), z(2, 100.0, 200.5)], caps=caps)
    a = f2.step()
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and f2.why["floor"] is True


# ================================================================ P24-AL: finish the fallen
def test_a_downed_zombie_in_reach_is_finished_before_the_standing_pin(tmp_path):
    """P24-AL: the pin (1) stands at 1.8 tiles, zombie 2 lies at 1.5: the stomp goes to 2 first."""
    r, f = fight(tmp_path, [z(1, 101.8), z(2, 101.5, floor=True)], pin=1)
    a = f.step()
    assert (a.type, a.args) == ("stomp", {"targetId": 2}) and f.why["target"] == 1


def test_the_shove_of_a_standing_zombie_at_point_blank_comes_first(tmp_path):
    """P24-AL: a downed zombie at 1.5 tiles and a standing one at 0.8: the standing one is shoved first."""
    r, f = fight(tmp_path, [z(1, 100.8), z(2, 101.5, floor=True)])
    a = f.step()
    assert (a.type, a.args) == ("shove", {"targetId": 1}) and f.why["shove"] == "first"


@pytest.mark.parametrize("end", [{"state": "failed", "reason": "standing"}, {"state": "failed", "reason": "out of reach"},
                                 {"state": "rejected", "reason": "not valid"},
                                 {"state": "done", "result": {"hit": False, "attackStarted": False,
                                                              "targetDead": False}}])
def test_a_refused_stomp_takes_the_floor_strike(tmp_path, end):
    """P24-AL: a stomp the Lua refused, failed or dropped (attackStarted false) leaves the target out of the stomp for
    SWING_SKIP_S; the weapon's floor strike (an attack of the downed zombie) follows; past it the stomp again."""
    zs = [z(1, 101.0, floor=True)]
    r, f = fight(tmp_path, zs)
    assert f.step().type == "stomp"
    r.answer(end)
    fr(r, zs)
    a = f.step()
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and f.why["floor"] is True
    r.answer({"state": "done", "result": {"swings": 1, "attackStarted": True, "meleeDelay": 0.0,
                                          "targetDead": False}})
    r.advance(P.SWING_SKIP_S + 0.1)
    fr(r, zs)
    assert f.step().type == "stomp"


def test_a_shove_s_knockdown_is_stomped_before_the_frame_reads_it_down(tmp_path):
    """PZA/1.7.1 (9 fix 12: `knockdown` read off the knocked-down state at the hit, `onFloor` a second later): the
    shove's target reads downed for KNOCK_READ_S, so the stomp follows at once; past it the frame's read stands."""
    zs = [z(1, 100.8)]
    r, f = fight(tmp_path, zs, arm=12.0)
    assert f.step().type == "shove"
    r.answer({"state": "done", "result": {"knockdown": True, "attackStarted": True, "targetDead": False}})
    fr(r, zs, 12.0)
    a = f.step()
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and P.KNOCK_READ_S == 2.0
    r.answer({"state": "failed", "reason": "superseded"})
    r.advance(P.KNOCK_READ_S + 0.1)
    fr(r, zs, 12.0)
    assert f.step().type == "shove"


def test_a_superseded_stomp_is_no_refusal(tmp_path):
    zs = [z(1, 101.0, floor=True)]
    r, f = fight(tmp_path, zs)
    f.step()
    r.answer({"state": "failed", "reason": "superseded"})
    fr(r, zs)
    assert f.step().type == "stomp"


def test_a_stomp_kill_is_a_kill(tmp_path):
    """P24-Q's metric reads the stomp's `targetDead` as an attack's."""
    zs = [z(1, 101.0, floor=True)]
    r, f = fight(tmp_path, zs)
    f.step()
    r.answer({"state": "done", "result": {"hit": True, "attackStarted": True, "targetDead": True}})
    fr(r, zs)
    f.observe()
    assert f.kill == 1 and r.world.kills == 1 and 1 in f.dead


def test_a_downed_zombie_behind_a_blocked_line_or_beyond_reach_is_not_finished(tmp_path):
    """P24-AL reads the downed within FIGHT_REACH on a line not read blocked: one at 2.5 tiles is walked to (the
    approach), one behind a wall (the line's reposition) takes no stomp."""
    from .test_policies import behind_wall_n
    r, f = fight(tmp_path, [z(1, 102.5, floor=True)])
    a = f.step()
    assert a.type == "walkTo" and "downed" not in f.why
    (tmp_path / "b").mkdir()
    r2 = Rig(tmp_path / "b")
    r2.scan(behind_wall_n())
    fr(r2, [z(7, 100.5, 199.5, floor=True)])
    f2 = Fight(r2.world, r2.acts, r2.clock)
    a = f2.step()
    assert a.type == "walkTo" and "downed" not in f2.why and f2.why["line"] is False


def test_a_downed_zombie_breaks_a_running_stance_leg(tmp_path):
    """P24-AL: a stance leg running on a pin 3 tiles off gives way once a zombie lies within reach."""
    r, f = fight(tmp_path, [z(1, 103.0)], stance=True)
    a = f.step()
    assert a.type == "aim"
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    fr(r, [z(1, 103.0)])
    assert f.busy()
    fr(r, [z(1, 103.0), z(2, 101.0, floor=True)])
    assert not f.busy()


def test_a_build_before_pza1_7_swings_as_before(tmp_path):
    """No `shove` or `stomp` in the hello's caps and no `onFloor` or `armPain` on the frames (the goldens' records):
    the swing, whatever the second zombie or the arms (the hold and the endurance read `Survive`'s)."""
    r, f = fight(tmp_path, [z(1, 100.8), z(2, 101.5)], arm=None, caps=NO_SWINGS, stance=False)
    assert f.step().type == "attack"
    (tmp_path / "b").mkdir()
    r2, f2 = fight(tmp_path / "b", [z(1, 100.8)], arm=15.0, caps=NO_SWINGS)
    assert f2.step().type == "attack"


def test_survive_s_fight_shoves_at_point_blank_with_the_arms_strained(tmp_path):
    """End to end: Survive's fight on one zombie at 0.8 tiles, armPain 12 (under STRAIN_HARD, no hold): the shove."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 100.8)], 12.0)
    a = tick(r, sv)
    assert a.type == "shove" and threat_why(tmp_path)["shove"] == "strain" and sv.mode == "fight"
