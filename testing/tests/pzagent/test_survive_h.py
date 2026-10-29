"""Survival 8 (Plan 24 Task 18, spec § 6 item 17; the seventh chain's E7, `e_day_7-20261029-140813`: 227 game
minutes, zero kills, three fights all fled, the goal walking on with a lone zombie listed at 7 to 10 tiles; Angus at
the screen: stuck on doors, forgetting nearby zombies, wandering the woods): P24-X, the fight sought within ENGAGE_R;
P24-Y, every walk a building; P24-Z, the stuck door marked and routed around. The fake mod over the PZA/1.5 skills."""
import math

import pytest

from agent.base.planner import policies as P
from agent.base.planner import survive as S

from .test_policies import CAPS_14, Rig, all_sends_valid, zombie
from .test_survive import last, make, open_yard, threat_why, tick


def zd(zid, x, y, has_target=True, health=1.0, me=(100.0, 200.0)):
    return dict(zombie(zid, x, y, me=me), hasTarget=has_target, health=health)


# ================================================================ P24-X: the fight sought
def test_the_engage_constants():
    assert P.ENGAGE_R == 10.0 and P.ENGAGE_R == P.DISENGAGE_R and P.ENGAGE_R < P.AIM_R
    assert P.stance_leg_kind(5.0, False, seek=True) == "seek" and P.stance_leg_kind(2.4, False, seek=True) == "back"
    assert P.stance_leg_kind(2.0, False, seek=True) == "enter" and P.stance_leg_kind(5.0, True, seek=True) == "toward"
    assert S.Survive.ENGAGE is True and S.Survive.SEEK is True


def goal_walking(r, sv):
    """The open yard scanned, no zombie: the goal's scan, then its walk to the edge, left running."""
    r.scan(open_yard())
    r.frame()
    tick(r, sv)
    while r.acts.current is not None and r.acts.current.type == "scan":
        r.answer()
        r.frame()
        tick(r, sv)
    assert last(r.dir)["branch"] == "goal" and r.acts.current is not None
    assert r.acts.current.type == "walkTo" and sv.goals.current is not None
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    return r.acts.current


def test_one_zombie_at_eight_tiles_with_the_goal_walking_is_sought_with_a_toward_stance_leg(tmp_path):
    """P24-X: one zombie listed at 8 tiles (beyond DANGER_R, within ENGAGE_R), armed, full health, the goal's walk
    running: the threat branch engages, its first leg an `aim` toward the zombie (`leg` "seek", the unit vector),
    the goal superseded on the next tick; before P24-X the goal walked on."""
    r, sv = make(tmp_path)
    walk = goal_walking(r, sv)
    r.frame(zombies=[zd(1, 108.0, 200.0)])
    tick(r, sv)
    d = last(tmp_path)
    assert d["branch"] == "threat" and d["inputs"]["threats"] == 0
    t, a = r.cmd()
    assert t == "aim" and (a["vx"], a["vy"], a["targetId"]) == (1.0, 0.0, 1)
    w = threat_why(tmp_path)
    assert w["fight"] is True and w["leg"] == "seek" and w["seek"] is True and w["stance"] is True
    assert sv.mode == "fight" and sv.fight.seek and r.acts.history[-2] is walk
    r.frame(zombies=[zd(1, 108.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and sv.goals.current is None
    assert sv.goals.history[-1]["state"] == "superseded" and sv.goals.history[-1]["reason"] == "aim"
    all_sends_valid(r)


def test_two_zombies_at_nine_tiles_are_sought(tmp_path):
    """P24-X: two within ENGAGE_R at 9 tiles (health 100, over FLEE_HEALTH_PAIR): engaged, the nearer the target."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 109.0, 200.0), zd(2, 100.0, 209.2)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and r.cmd()[0] == "aim" and r.cmd()[1]["targetId"] == 1
    assert threat_why(tmp_path)["leg"] == "seek"


@pytest.mark.parametrize("health, sought", [(59.0, False), (60.0, True)])
def test_two_are_sought_only_at_flee_health_pair(tmp_path, health, sought):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 109.0, 200.0), zd(2, 100.0, 209.2)], health=health)
    tick(r, sv)
    assert (last(tmp_path)["branch"] == "threat") is sought


def test_three_within_engage_r_are_not_sought_and_three_within_danger_r_are_fled_as_before(tmp_path):
    """P24-X seeks one or two: three listed at 8 to 9 tiles leave the goal to run (the threat branch passes, as
    before P24-X); three within DANGER_R are the `many` flee, as before."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 108.0, 200.0), zd(2, 100.0, 209.0), zd(3, 92.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "threat" and sv.mode is None
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 100.0, 204.0), zd(3, 96.0, 200.0)])
    tick(r2, sv2)
    assert r2.cmd()[0] == "steer" and threat_why(tmp_path / "b")["flee"] == "many"


def test_four_listed_pressing_are_no_seek_but_two_fought_while_two_stand_off_are(tmp_path):
    """The `many` reason live is no seek: MANY_LISTED_N listed within LISTED_R with more than MAX_FIGHT of them
    pressing (`_pressing`: within ENGAGE_R or chasing), two within ENGAGE_R and two chasing at 11 tiles. The E7
    write-up's reading (Task 18): each of E7's fights fled four listed, two of them standing off at 11.6 and 11.8
    tiles, not chasing; with the two far ones standing (`hasTarget` false) the pair is sought."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 108.0, 200.0), zd(2, 100.0, 209.0), zd(3, 111.0, 201.0), zd(4, 89.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "threat"
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.frame(zombies=[zd(1, 108.0, 200.0), zd(2, 100.0, 209.0), zd(3, 111.0, 201.0, has_target=False),
                      zd(4, 89.0, 200.0, has_target=False)])
    tick(r2, sv2)
    assert last(tmp_path / "b")["branch"] == "threat" and threat_why(tmp_path / "b")["fight"] is True


def test_e7_s_first_fight_is_fought_and_e5_s_horde_is_still_fled(tmp_path):
    """The listing's two cases off the records (the E7 write-up, Task 18): E7's line 68 (the pair at 3.1 and 6.2
    tiles chasing, two more listed at 11.6 and 11.8 standing): the fight stays on (before P24-X the `many` flee,
    `listed` 4); E5's line 220 (4.9 chasing, 10.4 and 11.3 chasing, 11.7 and 11.9 standing): three press, the
    `many` flee on the listing as before."""
    r, sv = make(tmp_path, caps=CAPS_14)
    e7 = [zd(1, 103.1, 200.0), zd(2, 100.0, 206.2), zd(3, 88.4, 200.0, has_target=False),
          zd(4, 100.0, 188.2, has_target=False)]
    r.frame(zombies=e7)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["fight"] is True and "listed" not in w
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b", caps=CAPS_14)
    e5 = [zd(1, 104.9, 200.0), zd(2, 100.0, 210.4), zd(3, 88.7, 200.0), zd(4, 100.0, 188.3, has_target=False),
          zd(5, 111.9, 200.0, has_target=False)]
    r2.frame(zombies=e5)
    tick(r2, sv2)
    w = threat_why(tmp_path / "b")
    assert w["flee"] == "many" and w["listed"] == 5


@pytest.mark.parametrize("weapon_off, health", [(True, 100.0), (False, 39.0)])
def test_below_the_flee_line_or_unarmed_nothing_is_sought(tmp_path, weapon_off, health):
    """P24-X: below FLEE_HEALTH (one) or unarmed, a zombie at 8 tiles is not sought: the goal runs."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 108.0, 200.0)], health=health, **({"weapon": None} if weapon_off else {}))
    tick(r, sv)
    assert last(tmp_path)["branch"] != "threat" and sv.mode is None


def test_a_zombie_marked_unreachable_is_not_sought(tmp_path):
    r, sv = make(tmp_path)
    sv.unreachable[1] = r.clock() + P.UNREACHABLE_S
    r.frame(zombies=[zd(1, 108.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "threat"
    r.advance(P.UNREACHABLE_S)
    r.frame(zombies=[zd(1, 108.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and r.cmd()[0] == "aim"


def test_a_sleeper_is_not_woken_to_seek(tmp_path):
    """No seek while the night's Sleep is current (a sleeper is woken by a zombie within DANGER_R only, as before)."""
    from agent.base.pza1 import Sleep
    r, sv = make(tmp_path)
    r.frame()
    sv.night.last = r.acts.send(Sleep())
    r.frame(zombies=[zd(1, 108.0, 200.0)])
    assert sv._sought() is None
    r.answer()
    r.frame(zombies=[zd(1, 108.0, 200.0)])
    assert sv._sought() is not None


def test_the_seek_leg_gives_way_at_keep_r_to_iteration_7_s_stance(tmp_path):
    """P24-X then P24-N: the seek leg holds while its target stays beyond KEEP_R (the target at 6 then 3 tiles) and
    gives way the tick it comes inside (2.4): the backpedal; the target is then `sought` and the seek never resumes
    for it (beyond KEEP_R again at 3.5: a standing leg, iteration 7's)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 106.0, 200.0)])
    tick(r, sv)
    leg = r.acts.history[-1]
    assert threat_why(tmp_path)["leg"] == "seek"
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    r.advance(0.5)
    r.frame(zombies=[zd(1, 103.0, 200.0)])
    assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == leg.aid
    r.advance(0.5)
    r.frame(zombies=[zd(1, 102.4, 200.0)])
    tick(r, sv)
    t, a = r.cmd()
    assert t == "aim" and a["vx"] == -1.0 and threat_why(tmp_path)["leg"] == "back" and 1 in sv.fight.sought
    r.answer()
    r.advance(2.0)
    r.frame(zombies=[zd(1, 103.5, 200.0)])
    tick(r, sv)
    assert r.cmd()[1]["vx"] == 0.0 and threat_why(tmp_path)["leg"] == "stand"


def test_a_flee_leg_ending_with_its_pursuer_alone_at_six_tiles_turns_to_fight_it(tmp_path):
    """P24-X: a `pair` flee at health 55 (two at 4 tiles, under FLEE_HEALTH_PAIR); its leg ends with one left at 6
    tiles, alone: the flee turns and fights it (one at 55, over FLEE_HEALTH), its first leg the seek; before P24-X the
    refight margin (FLEE_HEALTH + REFIGHT_MARGIN, 60) kept the flee `held`."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 100.0, 204.0)], health=55.0)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "pair"
    r.answer()
    r.event("zombie_dead", id=2)
    r.frame(zombies=[zd(1, 106.0, 200.0)], health=55.0)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["fight"] is True and sv.mode == "fight" and r.cmd()[0] == "aim" and w["leg"] == "seek"


def test_a_running_flee_leg_is_kept_until_it_ends_then_the_fight(tmp_path):
    """`flip` (P23-AM 1) keeps the flee's own running leg: the turn comes when the leg ends ("when a flee leg
    ends")."""
    r, sv = make(tmp_path, caps=CAPS_14)
    r.scan(open_yard())
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 100.0, 204.0)], health=55.0)
    tick(r, sv)
    leg = r.acts.history[-1]
    r.fake.answer({"steer": ["accepted"]})
    r.pump()
    r.event("zombie_dead", id=2)
    r.advance(1.0)
    r.frame(x=97.0, zombies=[zd(1, 104.0, 200.0, me=(97.0, 200.0))], health=55.0)
    assert tick(r, sv) is None and threat_why(tmp_path)["flee"] == "flip" and leg.state == "accepted"
    r.answer()
    r.advance(1.0)
    r.frame(x=97.0, zombies=[zd(1, 104.0, 200.0, me=(97.0, 200.0))], health=55.0)
    tick(r, sv)
    assert threat_why(tmp_path)["fight"] is True and r.cmd()[0] == "walkTo"


def test_the_health_flee_stays_below_its_margin_and_no_seek_below_the_line(tmp_path):
    """The health flee stays (P24-X): a `health` episode (one at 3 tiles, health 39) keeps running at 45 with its
    pursuer alone at 6 tiles (the refight margin kept for it), and turns to fight at 60."""
    r, sv = make(tmp_path)
    r.scan(open_yard())
    r.frame(zombies=[zd(1, 103.0, 200.0)], health=39.0)
    tick(r, sv)
    assert threat_why(tmp_path)["flee"] == "health" and sv.flee_health
    r.answer()
    r.frame(zombies=[zd(1, 106.0, 200.0)], health=45.0)
    tick(r, sv)
    assert threat_why(tmp_path)["flee"] == "held" and sv.mode == "flee"
    r.answer()
    r.frame(zombies=[zd(1, 106.0, 200.0)], health=60.0)
    tick(r, sv)
    assert threat_why(tmp_path)["fight"] is True and not sv.flee_health


def test_two_sought_are_the_fight_not_a_group_behind_it_but_a_third_listed_beyond_is(tmp_path):
    """P24-A (b) under P24-X: the second of the two sought, behind the first on its bearing, is the fight (no
    `behind`); a zombie listed beyond ENGAGE_R behind the target and chasing turns the seek to the `held` flee, as
    before; one standing off there (not chasing: the E7 write-up's reading) does not."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 105.0, 200.0), zd(2, 109.0, 200.5)])
    tick(r, sv)
    assert r.cmd()[0] == "aim" and "behind" not in threat_why(tmp_path)
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.frame(zombies=[zd(1, 105.0, 200.0), zd(2, 111.0, 200.5)])
    tick(r2, sv2)
    w = threat_why(tmp_path / "b")
    assert r2.cmd()[0] == "steer" and w["flee"] == "held" and w["behind"] == [2]
    (tmp_path / "c").mkdir()
    r3, sv3 = make(tmp_path / "c")
    r3.frame(zombies=[zd(1, 105.0, 200.0), zd(2, 111.0, 200.5, has_target=False)])
    tick(r3, sv3)                                                    # standing off beyond ENGAGE_R: no group
    assert r3.cmd()[0] == "aim" and "behind" not in threat_why(tmp_path / "c")


def test_a_seek_beyond_aim_r_walks_at_a_walk_and_a_failed_seek_walk_marks_its_target(tmp_path):
    """The seek beyond AIM_R (the Lua refuses the aim there) is a walk at a walk, never a run; a seek walk (that one,
    or the walk round a wall) failed for a walk reason marks the target unreachable, as an attack's walk does."""
    r = Rig(tmp_path)
    r.frame(zombies=[zd(1, 112.5, 200.0)])
    f = P.Fight(r.world, r.acts, r.clock)
    f.stance, f.seek = True, True
    cmd = f.choose()
    assert (cmd.TYPE, cmd.gait) == ("walkTo", "walk") and f.why["seek"] is True and f.why["leg"] == "walk"
    f.send(cmd)
    r.answer("failed")
    f.observe()
    assert 1 not in f.unreachable
    f.send(f.choose())
    r.fake.answer({"walkTo": ["accepted", {"state": "failed", "reason": "stuck"}]})
    r.pump()
    f.observe()
    assert f.unreachable.get(1, 0) > r.clock() and f.target is None
    g = P.Fight(r.world, r.acts, r.clock)
    g.stance = True
    assert g.choose().gait == "run"                                       # not sought: the approach at a run


def test_a_flee_leg_boxed_in_a_fence_corner_takes_the_rest_of_the_circle_never_a_known_blocked_edge(tmp_path):
    """T19.5 (the E7 write-up, Task 18): E7's legs a71-a74 ran four times into a known fence corner (fences east and
    south of the player, the group north-west): every turn within 90 degrees of the away vector read blocked, so the
    away vector was kept. Now the rest of the circle (WIDE_TURNS) is read, then any heading whose first STEP_PROBE
    tile is clear: the leg never crosses a known blocked edge on its first steps."""
    from .test_policies import grid
    at = {(103, y): {"blockW": True} for y in range(190, 211)}
    at.update({(x, 201): dict(at.get((x, 201), {}), blockN=True) for x in range(90, 103)})
    r, sv = make(tmp_path)
    r.scan(grid(90, 106, 190, 210, at))
    me = (102.5, 200.5)
    zs = [zd(i, me[0] - 3.0 + 0.3 * i, me[1] - 3.0 - 0.3 * i, me=me) for i in (1, 2, 3)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    tick(r, sv)
    t, a = r.cmd()
    assert t == "steer" and threat_why(tmp_path)["flee"] == "many"
    v = (a["vx"], a["vy"])
    assert P.clear_heading(r.world, v, P.STEER_PROBE)
    assert threat_why(tmp_path)["turn"] in P.WIDE_TURNS + P.STEER_TURNS and threat_why(tmp_path)["probe"] is not None
