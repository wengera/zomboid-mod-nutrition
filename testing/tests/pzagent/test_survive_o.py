"""Survival 12 (survival iteration 11, the commit label; Plan 24 Task 32, spec § 6 item 23; E9, `e_day_9-20261030-052429`:
no kill, six fights dropped by the look behind for a chaser 10.74 to 11.90 tiles behind the target, the character
held 16.511 s against a `solidTrans` row): ruling P24-AN, the pull (a lone chaser drawn from the group by the stance
walking away from it, then fought alone; the `many` listing counting only a zombie within DANGER_R or chasing), and
ruling P24-AS (amendment 1), the transparent solid in a heading read. The fake mod over PZA/1.7."""
import functools
import json

import pytest

from agent.base.planner import policies as P
from agent.base.planner import survive as S

from .test_policies import CAPS_14, Rig, all_sends_valid, square, zombie
from .test_survive import make, threat_why, tick


def zd(zid, x, y, has_target=True, me=(100.0, 200.0)):
    return dict(zombie(zid, x, y, me=me), hasTarget=has_target)


def why(tmp_path):
    return threat_why(tmp_path)


# ================================================================ P24-AN: the pull
def test_the_pull_constants():
    """PULL_R: "until the chaser alone is within FIGHT_REACH + KEEP_R"; the switches on."""
    assert P.PULL_R == P.FIGHT_REACH + P.KEEP_R == 4.5
    assert S.Survive.PULL is True and S.Survive.TRANS is True
    assert P.stance_leg_kind(7.0, False, seek=True, pull=True) == "pull"
    assert P.stance_leg_kind(7.0, True, seek=True, pull=True) == "toward"   # the advance first, as for the seek


@pytest.mark.parametrize("zs,d,reach,want", [
    ([zd(1, 107.0, 200.0), zd(2, 111.0, 200.0), zd(3, 109.0, 207.0, has_target=False)], 7.0, P.ENGAGE_R,
     (110.0, 203.5)),                                                                     # the group's centroid
    ([zd(1, 107.0, 200.0)], 7.0, P.ENGAGE_R, None),                                       # nobody else listed
    ([zd(1, 107.0, 200.0, has_target=False), zd(2, 111.0, 200.0)], 7.0, P.ENGAGE_R, None),   # the target idle
    ([zd(1, 107.0, 200.0), zd(2, 105.0, 200.0, has_target=False)], 7.0, P.ENGAGE_R, None),   # one within DANGER_R
    ([zd(1, 107.0, 200.0), zd(2, 108.5, 200.0)], 7.0, P.ENGAGE_R, None),                  # a second chaser near
    ([zd(1, 107.0, 200.0), zd(2, 108.5, 200.0, has_target=False)], 7.0, P.ENGAGE_R, (108.5, 200.0)),   # idle there
    ([zd(1, 109.5, 200.0), zd(2, 111.0, 200.0)], 9.5, P.ENGAGE_R, None),                  # the chaser past ENGAGE_R
    ([zd(1, 109.5, 200.0), zd(2, 111.0, 200.0)], 9.5, P.DISENGAGE_R, (111.0, 200.0)),     # ... kept once pulled
    ([zd(1, 107.0, 200.0), zd(2, 112.5, 200.0)], 7.0, P.ENGAGE_R, None),                  # beyond LISTED_R
])
def test_pull_from_reads_one_chaser_with_the_rest_listed_beyond_danger_r(tmp_path, zs, d, reach, want):
    r = Rig(tmp_path)
    r.frame(zombies=zs)
    got = P.pull_from(r.world, (1, r.world.zombies[1], d), reach=reach)
    assert got == (None if want is None else pytest.approx(want))


def test_pull_from_leaves_the_dead_out(tmp_path):
    r = Rig(tmp_path)
    r.frame(zombies=[zd(1, 107.0, 200.0), zd(2, 105.0, 200.0, has_target=False), zd(3, 111.0, 200.0)])
    assert P.pull_from(r.world, (1, r.world.zombies[1], 7.0)) is None
    assert P.pull_from(r.world, (1, r.world.zombies[1], 7.0), skip={2}) == pytest.approx((111.0, 200.0))


def test_a_chaser_with_another_listed_behind_it_is_pulled_never_dropped(tmp_path):
    """E9's six drops (lines 187, 232, 243, 295, 305 and 344: the target chasing within ENGAGE_R, a chaser 10.74 to
    11.90 tiles behind it): five engage as pulls on the HEAD replay; line 344 rightly stays a drop (Task 32 fix 1, the
    review's minor 7: at 343 a second chaser, 7474, reads within ENGAGE_R, so no lone chaser is pulled, and the look
    behind flees for 7489, which reads fallen at 11.69 tiles: whether `others_behind` skips an `onFloor` zombie is
    the controller's ruling). Here: the fight engages, its first leg the pull, an aim facing the chaser while walking
    away from the group's centroid (west, the group east), no `behind`; with PULL off (the rule before) the look
    behind flees `held`."""
    zs = [zd(1, 107.0, 200.0), zd(2, 111.0, 200.5)]
    r, sv = make(tmp_path)
    r.frame(zombies=zs)
    tick(r, sv)
    w = why(tmp_path)
    t, a = r.cmd()
    assert t == "aim" and a["targetId"] == 1 and w["leg"] == "pull" and w["fight"] is True and "behind" not in w
    assert a["vx"] == pytest.approx(-1.0, abs=0.01) and w["pull"] == [111.0, 200.5]
    assert sv.fight.pull is True and sv.fight.pulling((1, r.world.zombies[1], 7.0))
    all_sends_valid(r)
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    sv2.PULL = False
    r2.frame(zombies=zs)
    tick(r2, sv2)
    w2 = why(tmp_path / "b")
    assert r2.cmd()[0] == "steer" and w2["flee"] == "held" and w2["behind"] == [2]


def test_the_pull_holds_its_leg_until_the_chaser_comes_within_pull_r_then_the_stance_stands(tmp_path):
    """The pull leg holds while the chaser closes from 7 to 5 tiles (the leg it calls for unchanged); at 4.4 tiles
    (inside PULL_R) the leg gives way and the stance stands facing it (`stand`, the target `sought`: no seek toward
    it past the group), the look behind reading no walk."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 107.0, 200.0), zd(2, 111.0, 200.5)])
    tick(r, sv)
    leg = r.acts.history[-1]
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    r.frame(zombies=[zd(1, 105.0, 200.0), zd(2, 110.0, 200.5)])
    assert tick(r, sv) is None and why(tmp_path)["holding"] == leg.aid
    r.frame(zombies=[zd(1, 104.4, 200.0), zd(2, 109.0, 200.5)])
    tick(r, sv)
    t, a = r.cmd()
    w = why(tmp_path)
    assert t == "aim" and w["leg"] == "stand" and (a["vx"], a["vy"]) == (0.0, 0.0) and 1 in sv.fight.sought
    assert "behind" not in w and sv.mode == "fight"


def test_a_lone_chaser_met_within_pull_r_is_stood_for_never_sought(tmp_path):
    """The pull's end read at the first sight: the chaser at 4 tiles (beyond KEEP_R, within PULL_R), a chaser behind it
    at 10.5: the stance stands (no seek leg toward it), no `behind`."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 110.5, 200.2)])
    tick(r, sv)
    w = why(tmp_path)
    assert r.cmd()[0] == "aim" and w["leg"] == "stand" and "behind" not in w and "seek" not in w


def test_a_pulled_chaser_that_falls_past_engage_r_is_stood_for_not_sought_back(tmp_path):
    """F1 with the PZA/1.5 caps replayed (line 164 pulled 15911 at 8.93 tiles; line 165 read it at 9.34): once pulled, a
    lone chaser past ENGAGE_R and within DISENGAGE_R is faced standing (`_pull_waits`), never sought back toward the
    group; the mutant without the wait seeks it."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 108.5, 200.0), zd(2, 111.5, 200.5)])
    tick(r, sv)
    assert why(tmp_path)["leg"] == "pull"
    r.answer()
    r.frame(zombies=[zd(1, 109.4, 200.0), zd(2, 111.9, 200.5)])
    tick(r, sv)
    w = why(tmp_path)
    assert r.cmd()[0] == "aim" and w["leg"] == "stand" and "seek" not in w and "behind" not in w


@pytest.mark.parametrize("zs", [
    [zd(1, 107.0, 200.0, has_target=False), zd(2, 111.0, 200.5)],          # the target idle: the seek as before
    [zd(1, 107.0, 200.0), zd(3, 105.0, 203.0, has_target=False), zd(2, 111.0, 200.5)],   # another within DANGER_R
])
def test_no_pull_without_a_lone_chaser_and_the_group_beyond_danger_r(tmp_path, zs):
    r, sv = make(tmp_path)
    r.frame(zombies=zs)
    tick(r, sv)
    assert why(tmp_path).get("leg") != "pull" and "pull" not in why(tmp_path)


def test_the_pull_never_switches_to_a_nearer_idle_one_and_pins_the_chaser(tmp_path):
    """The one chaser is the fight: an idle zombie at 6.5 tiles nearer than the chaser at 8.5 (part of the group) is
    neither pinned first nor switched to while the pull runs."""
    from .test_survive import open_yard
    for i, pull in enumerate((True, False)):
        d = tmp_path / str(i)
        d.mkdir()
        r, sv = make(d)
        sv.PULL = pull
        r.scan(open_yard())                       # mapped open ground: the idle one is engageable (its flood reaches)
        r.frame(zombies=[zd(1, 108.5, 200.0), zd(3, 100.0, 206.5, has_target=False), zd(2, 111.0, 200.5)])
        tick(r, sv)
        a = r.cmd()[1]
        assert (why(d).get("leg") == "pull") is pull and (a["targetId"] == 1) is pull and (sv.fight.target == 1) is pull


def test_without_the_stance_nothing_is_pulled(tmp_path):
    """A PZA/1.4 build (no `aim`): no stance to turn into, the approach as before."""
    r, sv = make(tmp_path, caps=CAPS_14)
    r.frame(zombies=[zd(1, 107.0, 200.0), zd(2, 111.0, 200.5)])
    tick(r, sv)
    assert r.cmd()[0] != "aim" and "pull" not in why(tmp_path)


# ================================================================ P24-AN: the listing's count
def test_the_listing_counts_a_zombie_only_within_danger_r_or_chasing(tmp_path):
    """Four listed within LISTED_R, three of them beyond DANGER_R reading no `hasTarget` (a frame without the field):
    no `many` by the listing (P24-AD extended from the flee's count to the listing's); chasing, they make it; with
    IDLE off (the rules before P24-AD) every zombie counts."""
    def unread(zid, x, y):
        z = zd(zid, x, y)
        z["hasTarget"] = None
        return z
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0), unread(2, 109.0, 203.0), unread(3, 109.0, 197.0), unread(4, 110.0, 200.0)])
    sv._read_spent()
    held = sv._within(P.DANGER_R)
    assert sv._many_read(held, 1) == (False, None)
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 109.0, 203.0), zd(3, 109.0, 197.0), zd(4, 110.0, 200.0)])
    assert sv._many_read(sv._within(P.DANGER_R), 1) == (True, 4)
    r.frame(zombies=[zd(1, 104.0, 200.0), unread(2, 109.0, 203.0), unread(3, 109.0, 197.0), unread(4, 110.0, 200.0)])
    sv.IDLE = False
    assert sv._many_read(sv._within(P.DANGER_R), 1) == (True, 4)


# ================================================================ P24-AS: the transparent solid (amendment 1)
def trans_row(x=102):
    """The open ground 95..106 by 194..206 with the column x = `x` read `solidTrans` (a fence or counter the engine
    blocks but sees through), nothing else blocked."""
    return [square(i, j, solidTrans=(i == x)) for i in range(95, 107) for j in range(194, 207)]


def test_a_flee_heading_turns_off_a_solid_trans_row(tmp_path):
    """E9 held its y 16.511 s against a `solidTrans` row (y 10587) every run steer pointed into: the steer away from a
    zombie west at 3 tiles turns off the row east of it (north or south); with TRANS off (`solid` alone, the rule
    before) the heading runs east into it."""
    for i, (trans, into) in enumerate(((True, False), (False, True))):
        d = tmp_path / str(i)
        d.mkdir()
        r, sv = make(d, caps=CAPS_14)
        sv.TRANS = trans
        r.scan(trans_row())
        zs = [zd(1, 97.5, 200.5, me=(100.5, 200.5)), zd(2, 97.5, 199.5, me=(100.5, 200.5)),
              zd(3, 97.5, 201.5, me=(100.5, 200.5))]
        r.frame(x=100.5, y=200.5, zombies=zs)
        tick(r, sv)
        t, a = r.cmd()
        assert t == "steer" and why(d)["flee"] == "many"
        assert (a["vx"] > 0.9) is into and (abs(a["vy"]) > 0.4) is not into
        assert P.clear_heading(r.world, (1.0, 0.0), trans=False) and not P.clear_heading(r.world, (1.0, 0.0))


def test_the_world_reads_solid_trans_only_for_the_heading(tmp_path):
    """`line_clear(trans=True)` refuses a `solidTrans` square between the ends (the heading read); the default (a
    fight's line of sight, a goal's route) sees through it as before."""
    r = Rig(tmp_path)
    r.scan(trans_row())
    r.frame(x=100.5, y=200.5)
    assert r.world.line_clear((100.5, 200.5), (104.5, 200.5)) is True
    assert r.world.line_clear((100.5, 200.5), (104.5, 200.5), trans=True) is False
    assert r.world.line_clear((100.5, 200.5), (104.5, 200.5), unknown_open=True, trans=True) is False
    assert r.world.blocked((101, 200, 0), (102, 201, 0), trans=True) and not r.world.blocked((101, 200, 0),
                                                                                             (102, 201, 0))


def test_the_backpedal_turns_off_a_solid_trans_square_behind(tmp_path):
    """The stance's backpedal (a heading read) never steps into a `solidTrans` square: a zombie east at 2.2 tiles,
    the column x = 99 behind the player read `solidTrans`: the back leg turns off due west."""
    r, sv = make(tmp_path)
    r.scan(trans_row(99))
    r.frame(x=100.5, y=200.5, zombies=[zd(1, 102.7, 200.5, me=(100.5, 200.5))])
    sv.fight = None
    tick(r, sv)
    f = sv.fight
    a = f._stance_leg(1, r.world.zombies[1], 2.2, kind="back")
    assert a.vx > -0.9 and f.why["leg"] == "back"
    f.trans = False
    a2 = f._stance_leg(1, r.world.zombies[1], 2.2, kind="back")
    assert a2.vx == pytest.approx(-1.0)


def test_a_way_out_whose_square_beyond_is_a_transparent_solid_is_refused(tmp_path):
    """P24-AS on the flee's way out (`exit_plan`'s `_beyond`, the walk's end): building 1's open west door leads to
    (111, 201); the square beyond it, (110, 201), read `solidTrans`: no way out there (the walk would end against it);
    with `trans` off (the rule before) the exit is taken."""
    from .test_night import OPEN, house
    r = Rig(tmp_path)
    r.scan([square(x, y, solidTrans=(x, y) == (110, 201)) for x in range(105, 109) for y in range(196, 207)]
           + [sq for sq in house(1, 112, door=OPEN) if not (sq["x"] == 110 and sq["y"] == 201)]
           + [square(110, 201, solidTrans=True)])
    r.frame(x=113.5, y=201.5)
    assert P.exit_plan(r.world, []) is None
    plan = P.exit_plan(r.world, [], trans=False)
    assert plan is not None and plan["target"] == (110, 201, 0)


# ================================================================ Task 32 fix 1: the stance's count (the review's major 6)
E9 = "e_day_9-20261030-052429"


@functools.lru_cache(maxsize=4)
def _e9(off=()):
    import os
    from agent.base import replay_decisions as R

    def m(sv):
        for k in off:
            setattr(sv, k, False)
    return json.dumps(R.decisions(R.replay(os.path.join(R.ARTIFACTS, E9), mutate=m)))


def e9_lines(off=()):
    """{line: decision} of E9's decision log replayed at HEAD (open loop: a line after the first divergence is read for
    its geometry and decision, never for a kill), the switches `off` off."""
    return {d["line"]: d for d in json.loads(_e9(tuple(off)))}


def test_idle_zombies_held_beyond_danger_r_keep_the_pull_s_stance(tmp_path):
    """The review's major 6: a chaser at 7 tiles, idle zombies held at 7.5 and 9.5 (three held within DISENGAGE_R, past
    MAX_FIGHT): the stance counts only the standing ones within DANGER_R or chasing (`_stance_count`: one), so the pull
    leg holds; with STANCE_LISTED off (the rule Task 32 landed) the three turn the stance off and the Fight runs at the
    chaser."""
    zs = [zd(1, 107.0, 200.0), zd(2, 107.0, 202.0, has_target=False), zd(3, 109.0, 196.0, has_target=False)]
    for case in ("on", "off"):
        (tmp_path / case).mkdir()
        r, sv = make(tmp_path / case)
        sv.STANCE_LISTED = case == "on"
        r.frame(zombies=zs)
        leg = tick(r, sv)                                   # sought within ENGAGE_R: the chaser and the idle one at 7.3
        assert leg.type == "aim" and why(tmp_path / case)["leg"] == "pull"
        r.fake.answer({"aim": ["accepted"]})
        r.pump()
        r.frame(zombies=zs)
        a = tick(r, sv)                                     # running: held within DISENGAGE_R, all three
        assert len(sv._within(P.DISENGAGE_R)) == 3
        if case == "on":
            assert a is None and why(tmp_path / case)["holding"] == leg.aid and sv.fight.stance is True
            assert sv._stance_count(sv._within(P.DISENGAGE_R)) == 1
        else:
            assert sv.fight.stance is False and r.cmd() == ("walkTo", {"x": 107.5, "y": 200.5, "gait": "run"})


def test_a_fallen_zombie_is_no_count_toward_the_stance(tmp_path):
    """A zombie lying on the floor within DANGER_R is no standing attacker: two chasers and a fallen one held, the
    stance counts two (MAX_FIGHT)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 103.0, 200.0), zd(2, 103.0, 202.0), dict(zd(3, 104.0, 198.0), onFloor=True)])
    held = sv._within(P.DISENGAGE_R)
    assert len(held) == 3 and sv._stance_count(held) == 2


def test_e9_s_line_342_keeps_the_pull_s_leg(tmp_path):
    """E9 replayed at HEAD: line 341 sends the pull leg at 7479 (8.15 tiles); at 342, where Task 32's stance gate read
    three held (7594 fallen at 7.43 on the tick before, 7474 idle at 9.17) and ran at the chaser, the leg holds. With
    STANCE_LISTED off the run comes back (the review's line 342)."""
    got, old = e9_lines(), e9_lines(("STANCE_LISTED",))
    assert got[341]["why"]["leg"] == "pull" and got[341]["why"]["target"] == 7479
    assert got[342]["action"] is None and got[342]["why"]["leg"] == "pull" and "holding" in got[342]["why"]
    assert old[342]["action"]["type"] == "walkTo" and old[342]["action"]["args"]["gait"] == "run"


# ================================================================ Task 32 fix 1: the review's minor 8
def test_reachable_adjacent_reads_a_solid_trans_neighbour_as_solid_with_trans(tmp_path):
    """The reposition's squares (`World.reachable_adjacent`): a `solidTrans` neighbour of the target is listed with
    `trans` off (the read before) and left out with it on; the Fight's `_reposition` passes its `trans`."""
    r = Rig(tmp_path)
    r.scan(trans_row(102))
    r.frame(x=100.5, y=200.5)
    on = r.world.reachable_adjacent((103.5, 200.5), 0, trans=True)
    off = r.world.reachable_adjacent((103.5, 200.5), 0)
    assert all(sq[0] != 102 for sq in on) and any(sq[0] == 102 for sq in off)
    assert set(on) < set(off)


def test_the_ride_refuses_a_walk_whose_line_crosses_a_solid_trans_square(tmp_path):
    """`_ride_leg` (P24-U: the ride has no pathing): a running flee walk whose straight line crosses the `solidTrans`
    column is no ride's leg with TRANS on; with TRANS off (the read before) it is."""
    class Leg:
        type = "walkTo"
        args = {"x": 104.5, "y": 200.5}
    r, sv = make(tmp_path)
    r.scan(trans_row(102))
    r.frame(x=100.5, y=200.5)
    sv._flee_leg = lambda: Leg
    assert sv._ride_leg() is None
    sv.TRANS = False
    assert sv._ride_leg() is Leg
    Leg.args = {"x": 101.5, "y": 203.5}
    sv.TRANS = True
    assert sv._ride_leg() is Leg
