"""Survival 12 (survival iteration 11; Plan 24 Task 32; E9: a bite on part 5 read `body.armPain` 37.6 with `body.strain`
0 and held the strain hold to the death; two struck targets fell and were left under the `many` flee; four bites bled
the health from 96.39 to 0 in 13.111 s with five rags held): ruling P24-AP, the wounded fight (the arms' hold stops
the seeking only; within KEEP_R the shove, the stomp and the backpedal, never the swing at STRAIN_HARD) and ruling
P24-AQ, the fallen target under `many` (one stomp, or the floor strike, before the flee resumes). P24-AR is
`test_survive_r.py`. The fake mod over PZA/1.7. Task 32 fix 1: ruling R2 (every hold kind fights within KEEP_R, no
swing under any) and the finish's reach FINISH_R (the review's major 5)."""
import pytest

from agent.base.planner.policies import Fight

from .test_policies import CAPS_14, Rig, all_sends_valid, zombie
from .test_survive import last, make, threat_why, tick


def z(zid, x, y=200.0, floor=False, has_target=True):
    return dict(zombie(zid, x, y), onFloor=True if floor else None, hasTarget=has_target)


def fr(r, zs, arm=None, strain=None, **k):
    r.frame(zombies=list(zs), wounds={"armPain": arm, "strain": strain}, **k)


DONE_SHOVE = {"state": "done", "result": {"knockdown": False, "attackStarted": True, "targetDead": False}}


# ================================================================ P24-AP: the wounded fight
def test_the_arms_hold_alone_fights_a_zombie_within_keep_r_with_the_backpedal_never_the_swing(tmp_path):
    """armPain 25 (the hold), one zombie at 2.0 tiles (within KEEP_R and FIGHT_REACH, beyond point blank): no `strain`
    flee; the Fight's answer is the backpedal (an aim away from it, `wounded` 25), never an attack."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 102.0)], 25.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert sv.mode == "fight" and w["fight"] is True and "flee" not in w and sv.strain_hold
    assert a.type == "aim" and a.args["vx"] < -0.9 and w["wounded"] == 25.0 and w["leg"] == "back"
    assert not any(x.type == "attack" for x in r.acts.history)
    all_sends_valid(r)


def test_at_point_blank_the_wounded_fight_shoves_every_time(tmp_path):
    r, sv = make(tmp_path)
    fr(r, [z(1, 100.8)], 25.0)
    assert tick(r, sv).type == "shove" and threat_why(tmp_path)["shove"] == "strain"
    r.answer(DONE_SHOVE)
    fr(r, [z(1, 100.8)], 25.0)
    assert tick(r, sv).type == "shove"
    assert not any(x.type == "attack" for x in r.acts.history)


def test_the_wounded_backpedal_holds_until_point_blank(tmp_path):
    """The back leg holds while its target stands between point blank and KEEP_R + KEEP_MARGIN (no re-send a tick),
    and gives way at point blank for the shove."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 102.0)], 25.0)
    leg = tick(r, sv)
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    fr(r, [z(1, 101.6)], 25.0)
    assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == leg.aid
    fr(r, [z(1, 100.9)], 25.0)
    assert tick(r, sv).type == "shove"


def test_a_fallen_target_is_stomped_and_a_refused_stomp_takes_the_backpedal_not_the_floor_strike(tmp_path):
    """At STRAIN_HARD the stomp still goes (outside the divider, #4374); refused, the floor strike (a swing) does not:
    the backpedal; under STRAIN_HARD the floor strike follows as P24-AL rules."""
    for i, (arm, want) in enumerate(((25.0, "aim"), (19.0, "attack"))):
        d = tmp_path / str(i)
        d.mkdir()
        r = Rig(d)
        fr(r, [z(1, 101.0, floor=True)], arm)
        f = Fight(r.world, r.acts, r.clock)
        assert f.step().type == "stomp"
        r.answer({"state": "failed", "reason": "out of reach"})
        fr(r, [z(1, 101.0, floor=True)], arm)
        a = f.step()
        assert a.type == want and (f.why.get("wounded") == arm) is (want == "aim")


def test_a_corner_at_strain_hard_backpedals_and_without_the_stance_holds(tmp_path):
    """The cornered Fight (point blank's rules) at armPain 25 with its pin at 1.2 tiles: the back leg, never the swing;
    on a build without `aim` nothing is sent (`hold`)."""
    for i, caps in enumerate((None, CAPS_14)):
        d = tmp_path / str(i)
        d.mkdir()
        r = Rig(d, caps=caps)
        fr(r, [z(1, 101.2)], 25.0)
        f = Fight(r.world, r.acts, r.clock, target=1)
        f.point_blank = True
        a = f.step()
        if caps is None:
            assert a.type == "aim" and f.why["leg"] == "back" and f.why["wounded"] == 25.0
        else:
            assert a is None and f.why["hold"] is True


def test_beyond_keep_r_the_arms_hold_still_flees_strain(tmp_path):
    r, sv = make(tmp_path)
    fr(r, [z(1, 104.0)], 25.0)
    tick(r, sv)
    assert sv.mode == "flee" and threat_why(tmp_path)["flee"] == "strain"


@pytest.mark.parametrize("arm", [25.0, None])
@pytest.mark.parametrize("k", [{"endurance": 0.7}, {"fatigue": 0.7}])
def test_the_endurance_or_tired_hold_fights_within_keep_r_shove_then_stomp_never_the_swing(tmp_path, k, arm):
    """Ruling R2 (named change, Task 32 fix 1; the review's major 4: E9's endurance hold from game minute 617 put the
    `strain` flee back on with a zombie at 0.5 tiles): the endurance or the tired hold, with the arms' or alone,
    fights a zombie within KEEP_R as the arms' hold does: the backpedal at 2.0 tiles (never the swing), the shove at
    point blank every time, the stomp of a fallen one, never the floor strike; logged `spent`. With HOLD_WIDE off
    (the rule Task 32 landed) the endurance or tired hold flees `strain`."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 102.0)], arm, **k)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert sv.mode == "fight" and "flee" not in w and sv.spent_kinds
    assert a.type == "aim" and w["leg"] == "back" and w["spent"] == list(sv.spent_kinds)
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    fr(r, [z(1, 100.8)], arm, **k)
    a = tick(r, sv)
    assert a.type == "shove" and threat_why(tmp_path)["shove"] == ("strain" if arm else "spent")
    r.answer(DONE_SHOVE)
    fr(r, [z(1, 100.8)], arm, **k)
    assert tick(r, sv).type == "shove"                                  # every time
    r.answer(DONE_SHOVE)
    fr(r, [z(1, 100.8, floor=True)], arm, **k)
    assert tick(r, sv).type == "stomp"
    r.answer({"state": "failed", "reason": "out of reach"})
    fr(r, [z(1, 100.8, floor=True)], arm, **k)
    assert tick(r, sv).type == "aim"                                    # refused: the backpedal, no floor strike
    assert not any(x.type == "attack" for x in r.acts.history)
    (tmp_path / "off").mkdir()
    r2, sv2 = make(tmp_path / "off")
    sv2.HOLD_WIDE = False
    fr(r2, [z(1, 102.0)], arm, **k)
    tick(r2, sv2)
    assert sv2.mode == "flee" and threat_why(tmp_path / "off")["flee"] == "strain"


@pytest.mark.parametrize("k", [{"endurance": 0.7}, {"fatigue": 0.7}])
def test_beyond_keep_r_the_endurance_or_tired_hold_still_flees_strain(tmp_path, k):
    """R2's exemption is within KEEP_R only: at 4 tiles the hold flees `strain` as before (the release lines govern the
    seeking, never a zombie at point blank)."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 104.0)], None, **k)
    tick(r, sv)
    assert sv.mode == "flee" and threat_why(tmp_path)["flee"] == "strain"


def test_the_hold_s_why_carries_the_stiffness_beside_the_pain(tmp_path):
    """`body.strain` (#4369) is logged beside the pain in the hold's why when the frame carries it, read nowhere else."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 104.0)], 25.0, strain={"l": 0.0, "r": 1.5})
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["strain"] == {"kind": "arms", "armPain": 25.0, "endurance": 1.0, "fatigue": 0.05,
                           "strain": {"l": 0.0, "r": 1.5}}


def test_the_walk_corner_no_longer_yields_to_a_hold_within_keep_r(tmp_path):
    """P24-AP for the arms; R2 (named change, Task 32 fix 1) for the endurance hold beside it: no `strain` yield with
    the zombie within KEEP_R; with HOLD_WIDE off the endurance hold yields as Task 32 landed it."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 101.2)], 25.0)
    sv._read_spent()
    assert sv._walk_yields() is None
    fr(r, [z(1, 101.2)], 25.0, endurance=0.7)
    sv._read_spent()
    assert sv._walk_yields() is None
    sv.HOLD_WIDE = False
    assert sv._walk_yields() == "strain"


def test_the_arms_hold_still_seeks_nothing(tmp_path):
    r, sv = make(tmp_path)
    fr(r, [z(1, 107.0)], 25.0)
    tick(r, sv)
    assert sv.mode is None and last(tmp_path)["branch"] != "threat"


# ================================================================ P24-AQ: the fallen target under `many`
GROUP3 = [z(2, 107.5, 200.0), z(3, 107.5, 203.0), z(4, 107.5, 197.0)]   # three chasers beyond DANGER_R: `listed` many


def struck(tmp_path, caps=CAPS_14):
    """A Survive whose Fight swung at zombie 1 at 1.5 tiles (the approach and swing of a PZA/1.4-stance build)."""
    r, sv = make(tmp_path, caps=caps)
    fr(r, [z(1, 101.5)])
    a = tick(r, sv)
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and 1 in sv.struck
    r.answer({"state": "done", "result": {"swings": 1, "attackStarted": True, "meleeDelay": 0.0,
                                          "targetDead": False}})
    return r, sv


def test_a_struck_target_fallen_under_the_many_flee_is_stomped_once_before_the_flee_resumes(tmp_path):
    """The struck target lies at 1.5 tiles, three chasers listed at 7.5 (the `many` flee, none standing within
    DANGER_R): the flee's first answer is one stomp (the Flee's own action, logged `finish`); the steer follows."""
    r, sv = struck(tmp_path)
    fr(r, [z(1, 101.5, floor=True)] + GROUP3)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and w["flee"] == "many" and w["finish"] == 1
    assert sv.flee.last is a and w["kind"] == "stomp"
    fr(r, [z(1, 101.5, floor=True)] + GROUP3)
    assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == a.aid
    r.answer({"state": "done", "result": {"hit": True, "attackStarted": True, "targetDead": False}})
    fr(r, [z(1, 101.5, floor=True)] + GROUP3)
    assert tick(r, sv).type == "steer"
    all_sends_valid(r)


def test_a_standing_zombie_within_danger_r_keeps_the_flee_as_today(tmp_path):
    r, sv = struck(tmp_path)
    fr(r, [z(1, 101.5, floor=True), z(5, 104.0, 200.0)] + GROUP3)
    assert tick(r, sv).type == "steer" and "finish" not in threat_why(tmp_path)


def test_a_fallen_zombie_never_struck_is_left(tmp_path):
    """At 1.9 tiles (beyond CORNERED_R, whose `walk` corner would take a zombie at 1.5 first, struck or not)."""
    r, sv = make(tmp_path, caps=CAPS_14)
    fr(r, [z(1, 101.9, floor=True)] + GROUP3)
    assert tick(r, sv).type == "steer" and threat_why(tmp_path)["flee"] == "many"
    (tmp_path / "b").mkdir()
    r2, sv2 = struck(tmp_path / "b")
    fr(r2, [z(1, 101.9, floor=True)] + GROUP3)
    assert tick(r2, sv2).type == "stomp"                               # struck, the same read stomps


def test_a_refused_stomp_takes_one_floor_strike_then_the_flee(tmp_path):
    r, sv = struck(tmp_path)
    zs = [z(1, 101.5, floor=True)] + GROUP3
    fr(r, zs)
    assert tick(r, sv).type == "stomp"
    r.answer({"state": "failed", "reason": "out of reach"})
    fr(r, zs)
    a = tick(r, sv)
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and threat_why(tmp_path)["kind"] == "floor"
    r.answer({"state": "done", "result": {"swings": 1, "attackStarted": True, "meleeDelay": 0.0,
                                          "targetDead": False}})
    fr(r, zs)
    assert tick(r, sv).type == "steer"


def test_at_strain_hard_a_refused_stomp_takes_no_floor_strike(tmp_path):
    r, sv = struck(tmp_path)
    zs = [z(1, 101.5, floor=True)] + GROUP3
    fr(r, zs, 25.0)
    assert tick(r, sv).type == "stomp"
    r.answer({"state": "failed", "reason": "out of reach"})
    fr(r, zs, 25.0)
    assert tick(r, sv).type == "steer"


def test_the_finishing_stomp_s_kill_is_a_kill(tmp_path):
    r, sv = struck(tmp_path)
    zs = [z(1, 101.5, floor=True)] + GROUP3
    fr(r, zs)
    tick(r, sv)
    r.answer({"state": "done", "result": {"hit": True, "attackStarted": True, "targetDead": True}})
    fr(r, zs)
    tick(r, sv)
    assert r.world.kills == 1 and threat_why(tmp_path)["kill"] == 1 and 1 in sv.dead


def test_no_finish_under_a_flee_that_is_not_many(tmp_path):
    """The `health` flee (health 30) with the struck target fallen: the flee runs as today."""
    r, sv = struck(tmp_path)
    fr(r, [z(1, 101.5, floor=True), z(5, 107.0, 200.0)], health=30.0)
    a = tick(r, sv)
    assert a.type == "steer" and threat_why(tmp_path)["flee"] == "health"


# ================================================================ Task 32 fix 1: the finish's reach (the review's major 5)
def test_finish_r_reaches_e9_s_7474_at_line_334_s_geometry(tmp_path):
    """FINISH_R 5.0 (inside the Lua stomp's K.ATTACK_R 6, which its 4 s walk at #4197's 2.04 tiles a second covers):
    E9's 7474 first read fallen on a decision tick at 4.62 tiles with the nearest standing 6.49 (HEAD replay line 334):
    the stomp is sent at it; R3's 4.0 would not have reached it."""
    from agent.base.planner import survive as S
    assert S.FINISH_R == 5.0 and 4.62 <= S.FINISH_R < 6.0
    r, sv = struck(tmp_path)
    zs = [z(1, 104.62, floor=True), z(2, 106.49, 200.0), z(3, 107.5, 203.0), z(4, 107.5, 197.0)]
    fr(r, zs)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and w["finish"] == 1 and w["dist"] == pytest.approx(4.62)
    (tmp_path / "far").mkdir()
    r2, sv2 = struck(tmp_path / "far")
    fr(r2, [z(1, 105.1, floor=True)] + zs[1:])
    assert tick(r2, sv2).type == "steer"                                # beyond FINISH_R: the flee as today


def test_beyond_fight_reach_a_refused_stomp_takes_no_floor_strike(tmp_path):
    """The floor strike swings from where the player stands: within FIGHT_REACH only; a stomp refused at 4 tiles is
    followed by the flee."""
    r, sv = struck(tmp_path)
    zs = [z(1, 104.0, floor=True)] + GROUP3
    fr(r, zs)
    assert tick(r, sv).type == "stomp"
    r.answer({"state": "failed", "reason": "out of reach"})
    fr(r, zs)
    assert tick(r, sv).type == "steer"


def test_e9_s_7474_is_finished_at_line_334_and_7488_stays_left_under_its_standing_neighbour():
    """E9 replayed at HEAD: line 334 sends the finishing stomp at 7474 (fallen 4.62 tiles off, the nearest standing
    6.49); 7488, fallen on lines 141 to 150 at 1.24 to 5.73 tiles, always had a standing zombie within DANGER_R (1.57
    to 2.26 tiles), so no reach finishes it under P24-AQ's condition (the review's major 5: one of E9's two fallen
    targets, not both)."""
    from .test_survive_o import e9_lines
    got = e9_lines()
    w = got[334]["why"]
    assert got[334]["action"] == {"type": "stomp", "args": {"targetId": 7474}} and w["finish"] == 7474
    assert 4.6 < w["dist"] < 4.63 and w["flee"] == "many"
    assert not any(got[k]["why"].get("finish") == 7488 for k in range(141, 151) if k in got)


def test_under_the_endurance_hold_a_refused_stomp_takes_no_floor_strike(tmp_path):
    """Ruling R2 in the flee's finish: the floor strike is a swing, so under the endurance hold (no arm pain) a
    refused stomp is followed by the flee, as at STRAIN_HARD."""
    r, sv = struck(tmp_path)
    zs = [z(1, 101.5, floor=True)] + GROUP3
    fr(r, zs, endurance=0.7)
    assert tick(r, sv).type == "stomp"
    r.answer({"state": "failed", "reason": "out of reach"})
    fr(r, zs, endurance=0.7)
    assert tick(r, sv).type == "steer"
