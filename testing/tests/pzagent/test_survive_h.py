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
    """Named changes, Task 18 fix 1: ENGAGE_R 9 inside DISENGAGE_R 10 (the review's minor 8, a band); the KEEP_R guard
    is `seek_allowed`'s alone (minor 13): `stance_leg_kind` takes the caller's seek as read."""
    assert P.ENGAGE_R == 9.0 and P.DISENGAGE_R == 10.0 and P.ENGAGE_R < P.DISENGAGE_R < P.AIM_R
    assert P.stance_leg_kind(5.0, False, seek=True) == "seek" and P.stance_leg_kind(2.4, False, seek=False) == "back"
    assert P.stance_leg_kind(2.4, False, seek=True) == "seek"
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
    """P24-X: two within ENGAGE_R at 8.5 and 8.8 tiles (health 100, over FLEE_HEALTH_PAIR): engaged, the nearer the
    target (fix 1, minor 8: ENGAGE_R 9, the pair drawn in from 9.0 and 9.2)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 108.5, 200.0), zd(2, 100.0, 208.8)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and r.cmd()[0] == "aim" and r.cmd()[1]["targetId"] == 1
    assert threat_why(tmp_path)["leg"] == "seek"


@pytest.mark.parametrize("health, sought", [(59.0, False), (60.0, True)])
def test_two_are_sought_only_at_flee_health_pair(tmp_path, health, sought):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 108.5, 200.0), zd(2, 100.0, 208.8)], health=health)
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
    r.frame(zombies=[zd(1, 105.0, 200.0), zd(2, 108.5, 200.5)])                # fix 1: within ENGAGE_R 9
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


# ================================================================ P24-Y: every walk a building
from agent.base.planner import goals as G   # noqa: E402  (the P24-Y section's modules)
from agent.base.planner import llm as L   # noqa: E402
from agent.base.planner import view as V   # noqa: E402
from agent.base.planner.view import render, view   # noqa: E402

from .test_night import house   # noqa: E402
from .test_policies import CRATE, FRIDGE, grid   # noqa: E402


def test_the_destination_constants_and_the_loot_wants():
    """P24-Y: BUILDING_R 60, WOODS_R 40; the loot's wants in order, water and container, clothing (wanted by name:
    the Lua's loot filter and the item record carry no clothing yet, so no loot answers it), food, bandage, weapon."""
    assert (G.BUILDING_R, G.WOODS_R) == (60.0, 40.0)
    assert G.STOCK_WANTS == ("water", "container", "clothing", "food", "bandage", "weapon")
    assert "container" in P.LOOT_WANTS and "clothing" not in P.LOOT_WANTS


def test_the_building_boxes_and_the_woods_test(tmp_path):
    r = Rig(tmp_path)
    r.scan(house(1, 110) + house(2, 150))
    w = r.world
    assert w.building_boxes() == {1: (110, 200, 112, 202), 2: (150, 200, 152, 202)}
    assert w.building_dist(100.0, 201.0, 1) == 10.0 and w.building_dist(111.0, 201.0, 1) == 0.0
    assert w.building_dist(100.0, 201.0, 9) is None
    assert w.nearest_building(100.0, 201.0) == (10.0, 1) and w.nearest_building(160.0, 201.0)[1] == 2
    assert w.building_near(100.0, 201.0, 10.0) and not w.building_near(100.0, 160.0, G.WOODS_R)


def test_an_edge_in_the_woods_is_never_the_edge_once_a_building_is_known(tmp_path):
    """`World.unexplored_edge(WOODS_R)`: with no building known, the plain nearest edge (the first house still to
    find); with one known, a square farther than WOODS_R from every building is left out (E7's walk east from game
    minute 622 took the plain nearest edge each time, 545 tiles from the nearest building it knew by 746)."""
    r = Rig(tmp_path)
    r.scan(grid(60, 100, 199, 203))
    r.frame(x=62.0, y=201.0)
    w = r.world
    assert w.unexplored_edge(G.WOODS_R) == w.unexplored_edge() and w.unexplored_edge()[0] == 60
    r.scan(house(1, 110))
    r.frame(x=62.0, y=201.0)
    plain, edge = w.unexplored_edge(), w.unexplored_edge(G.WOODS_R)
    assert not w.building_near(plain[0] + 0.5, plain[1] + 0.5, G.WOODS_R)
    assert edge is not None and w.building_near(edge[0] + 0.5, edge[1] + 0.5, G.WOODS_R) and edge[0] >= 69


def bview(**k):
    v = {key: None for key in V.KEYS}
    v.update(pos={"x": 100.5, "y": 200.5, "z": 0}, load={"level": 0}, scanned_here=True, buildings=[], cooled=[],
             needs_wanted=[], stock_uses=[])
    v.update(k)
    return v


def bld(bid, dist, looted=False, containers=2, door=(120, 200)):
    return {"id": bid, "x": door[0] + 1, "y": door[1], "door": list(door), "dist": dist, "containers": containers,
            "looted": looted, "doors": 1, "visited": False, "shunned": False, "shelter": True, "holds": {},
            "box": [door[0] + 1, door[1] - 1, door[0] + 3, door[1] + 1]}


def picks(v):
    return [(g.TYPE, g.args()) for g in G.ScriptedSource().candidates(v)]


def test_the_scripted_loop_loots_the_nearest_unlooted_building_then_the_next_and_walks_only_to_buildings():
    """P24-Y's loop on the view: the nearest unlooted building within BUILDING_R, then the next; none within it, the
    walk to the nearest unlooted one beyond (its door) before any edge; all looted, the edge (the view's, never in
    the woods); in the woods with no edge, the walk back to the nearest building (`toward` "cluster"); else the
    rest."""
    v = bview(buildings=[bld(1, 20.0, looted=True), bld(2, 30.0), bld(3, 45.0), bld(4, 61.0)], edge=[90, 90])
    assert picks(v)[:3] == [("LootBuilding", {"building": 2}), ("LootBuilding", {"building": 3}),
                            ("ExploreToward", {"x": 90, "y": 90})]
    far = {"for": "unlooted", "building": 4, "door": [170, 200], "square": [171, 200], "dist": 70.0}
    v = bview(buildings=[bld(1, 20.0, looted=True), bld(4, 70.0, door=(170, 200))], edge=[90, 90], toward=far)
    assert picks(v)[:2] == [("ExploreToward", {"x": 170, "y": 200}), ("ExploreToward", {"x": 90, "y": 90})]
    v = bview(buildings=[bld(1, 20.0, looted=True)], edge=[90, 90])
    assert G.ScriptedSource().propose(v).args() == {"x": 90, "y": 90}
    home = {"for": "cluster", "building": 1, "door": [150, 200], "square": [151, 200], "dist": 50.0}
    v = bview(buildings=[bld(1, 50.0, looted=True, door=(150, 200))], edge=None, toward=home)
    assert picks(v) == [("ExploreToward", {"x": 150, "y": 200})]
    v = bview(buildings=[bld(1, 20.0, looted=True)], edge=None, toward=None)
    assert G.ScriptedSource().propose(v).TYPE == "Rest"


def test_the_view_names_the_walk_toward_an_unlooted_building_beyond_building_r_or_back_to_the_cluster(tmp_path):
    from .test_survive import make as smake
    r, sv = smake(tmp_path)
    far = house(2, 180)
    for s in far:
        if (s["x"], s["y"]) == (181, 201):
            s["containers"] = [FRIDGE]
    r.scan(house(1, 110) + far)
    r.frame(x=100.0, y=201.5)
    t = view(r.world, sv)["toward"]
    assert t == {"for": "unlooted", "building": 2, "door": [180, 201], "square": [180, 201], "dist": 80.5}
    r.world.mark_looted((181, 201, 0, 0), "food")
    assert view(r.world, sv)["toward"] is None                              # all looted, the player by building 1
    r.frame(x=100.0, y=140.0)
    t = view(r.world, sv)["toward"]
    assert t["for"] == "cluster" and t["building"] == 1 and t["door"] == [110, 201]


def test_loot_building_takes_water_then_the_container_then_food(tmp_path):
    """P24-Y's want order in one building: water, then an empty vessel (`container`), then food; `clothing` is
    passed over (no loot answers it)."""
    from .test_survive import make as smake
    r, sv = smake(tmp_path)
    sqs = house(1, 110)
    for s in sqs:
        if (s["x"], s["y"]) == (111, 201):
            s["containers"] = [{"type": "counter", "n": 3, "items": ["Base.Apple", "Base.PopEmpty",
                                                                     "Base.WaterBottle"]}]
    r.scan(sqs)
    r.frame(x=109.5, y=201.5)
    g = G.LootBuilding(1)
    k = G.Kit(r.world, r.acts, r.clock)
    g.kit = k
    wants = []
    for _ in range(3):
        cmd = g.step(r.world, r.acts, r.clock)
        assert cmd is not None and cmd.TYPE == "interact"
        wants.append(cmd.filter)
        k.loot.sent(cmd, r.acts.send(cmd))
        g.sent(cmd, r.acts.history[-1])
        r.answer()
        k.observe(r.world, r.acts)
    assert wants == ["water", "container", "food"]


def test_the_llm_view_lists_what_each_building_holds_and_the_prompt_constrains_the_walks(tmp_path):
    """P24-Y on the LLM source: the rendered buildings carry `h:` (what each is known to hold), the view's `toward`
    is rendered, `SYSTEM` states the loop and the woods rule, and an ExploreToward farther than WOODS_R from every
    listed building is refused `invalid: in the woods` (one within it, and any with no building listed, pass)."""
    from .test_survive import make as smake
    r, sv = smake(tmp_path)
    sqs = house(1, 110)
    for s in sqs:
        if (s["x"], s["y"]) == (111, 201):
            s["containers"] = [FRIDGE, CRATE]
    r.scan(sqs)
    r.frame(x=100.0, y=201.5)
    v = view(r.world, sv)
    text = render(v)
    assert "1 @110,201 door 110,201 10.5 c2 - h:bandage1,food1" in text and "\ntoward: null" in text
    assert "Your loop" in L.SYSTEM and "woods_r, %g at the start" % G.WOODS_R in L.SYSTEM and "woods" in L.SYSTEM
    woods = G.ExploreToward(100, 150)
    assert L.place_error(woods, v) == "invalid: in the woods"
    assert L.place_error(G.ExploreToward(100, 170), v) is None               # 31 tiles from the house's box
    assert L.place_error(woods, dict(v, buildings=[])) is None
    assert "in the woods" in V.WHYS


def test_e7_line_541_in_the_woods_proposes_the_walk_back_never_the_edge_further_out():
    """E7's line 541 (game minute 634, 71.8 tiles from the nearest building it knew, the goal walking the plain
    edge east to (10857, 10637)): the scripted source on the replayed world proposes a destination within WOODS_R
    of a known building."""
    from types import SimpleNamespace
    from agent.base import replay_decisions as R
    got = {}

    def grab(sv):
        real = sv.tick

        def tick_(world, actions):
            out = real(world, actions)
            got["w"], got["sv"] = world, sv
            return out
        sv.tick = tick_
    rows = R.replay(R.ARTIFACTS + "/e_day_7-20261029-140813", upto=541, mutate=grab)
    assert rows[-1]["goal"]["args"] == {"x": 10857, "y": 10637}
    w, sv = got["w"], got["sv"]
    surv = SimpleNamespace(night=sv.night, goals=SimpleNamespace(kit=sv.goals.kit, history=[], cooling=lambda: []),
                           clock=sv.clock, need_marks={})
    v = view(w, surv)
    g = G.ScriptedSource().propose(v)
    mx, my = P.me_xy(w)
    assert w.nearest_building(mx, my)[0] > G.WOODS_R
    assert g.TYPE == "ExploreToward" and w.building_near(g.x + 0.5, g.y + 0.5, G.WOODS_R), g


def _woods_sweep(world, sv, out):
    """The scripted source's proposal on the view of this tick, as the world reads and again with every container
    read looted (the replay's recorded goals mark none: a looted town is where the walks go): an ExploreToward with a
    building known whose square has none within WOODS_R is a walk into the woods (P24-Y), kept in `out`."""
    from types import SimpleNamespace
    surv = SimpleNamespace(night=sv.night, goals=SimpleNamespace(kit=sv.goals.kit, history=[], cooling=lambda: []),
                           clock=sv.clock, need_marks={})
    kept = {k: set(c["looted"]) for k, c in world.containers.items()}
    for looted in (False, True):
        if looted:
            for c in world.containers.values():
                c["looted"] = set(P.LOOT_WANTS)
        g = G.ScriptedSource().propose(view(world, surv))
        out["n"] += 1
        if g.TYPE == "ExploreToward" and world.building_boxes():
            out["explore"] += 1
            if not world.building_near(g.x + 0.5, g.y + 0.5, G.WOODS_R):
                out["woods"].append((world.game_min, g.x, g.y))
    for k, v in kept.items():
        world.containers[k]["looted"] = v


SWEEP_RUNS = {"e2": None, "e3": None, "e4": None, "e5": None, "f1": None, "e7": 1420}


@pytest.mark.parametrize("key", sorted(SWEEP_RUNS))
def test_no_scripted_walk_targets_the_woods_on_the_records(key):
    """P24-Y's sweep over the goldens' records and E7 (to line 1420, its `state.log`'s last aligned line): on every
    fifth replayed tick the scripted source's ExploreToward, once a building is known, targets a square with a
    building within WOODS_R."""
    from agent.base import replay_decisions as R
    out = {"n": 0, "explore": 0, "woods": []}

    def sweep(sv):
        real = sv.tick
        k = {"i": 0}

        def tick_(world, actions):
            k["i"] += 1
            if k["i"] % 5 == 0:
                _woods_sweep(world, sv, out)
            return real(world, actions)
        sv.tick = tick_
    run = "e_day_7-20261029-140813" if key == "e7" else R.RUNS[key]
    R.replay(R.ARTIFACTS + "/" + run, upto=SWEEP_RUNS[key], mutate=sweep)
    assert out["n"] > 10 and out["woods"] == [], out["woods"][:5]
    assert out["explore"] > 10


def test_no_scripted_walk_targets_the_woods_on_the_synthetic_fixture(tmp_path):
    """The same sweep on every frame of the synthetic PZA/1 fixture (`fixtures/pza1-synthetic-1.log`)."""
    import os
    import shutil
    from agent.base.transport.files import FileTransport
    from agent.base.world import World
    src = os.path.join(os.path.dirname(__file__), "fixtures", "pza1-synthetic-1.log")
    shutil.copy(src, str(tmp_path / "state.log"))
    w = World()
    from agent.base.actions import Actions
    from agent.base.planner.survive import Survive
    acts = Actions(FileTransport(str(tmp_path)), clock=lambda: 0.0)
    sv = Survive(w, acts, str(tmp_path / "decision.log"), lambda: 0.0)
    out = {"n": 0, "explore": 0, "woods": []}
    for ln in FileTransport(str(tmp_path)).lines():
        w.apply(ln)
        if ln["kind"] == "frame":
            _woods_sweep(w, sv, out)
    assert out["n"] > 0 and out["woods"] == []


# ================================================================ P24-Z: the stuck door
from agent.base.planner import night as N   # noqa: E402
from agent.base import world as W   # noqa: E402

from .test_night import CLOSED, LOCKED, two_door_house   # noqa: E402


def test_a_door_failing_twice_is_marked_for_door_retry_min(tmp_path):
    """P24-Z: one failure counts, the second within DOOR_RETRY_MIN (30) game minutes marks the door with its reason;
    the mark stands 30 game minutes; a failure older than 30 minutes no longer counts toward the next mark."""
    r = Rig(tmp_path)
    r.frame(game_min=480.0)
    w, door = r.world, (110, 201, 0)
    assert W.DOOR_RETRY_MIN == 30.0
    assert w.note_door_fail(door, "locked") is False and w.marked_doors() == set()
    r.frame(game_min=485.0)
    assert w.note_door_fail(door, "not adjacent") is True and w.marked_doors() == {door}
    assert w.door_marks[door] == (485.0 * 1.0, "not adjacent", "out")       # Task 18 fix 1: its side kept
    r.frame(game_min=514.9)
    assert w.marked_doors() == {door}
    r.frame(game_min=515.0)
    assert w.marked_doors() == set()
    w.note_door_fail(door, "locked")
    r.frame(game_min=546.0)
    assert w.note_door_fail(door, "locked") is False                       # the first is 31 minutes old


def test_a_marked_door_is_left_out_of_the_routes_and_the_shelter_goal_reads_the_marks(tmp_path):
    """The marks reach every plan through `night.exterior_doors`: the Shelter goal's plan takes the other door;
    with every door marked the building is `door_blocked` and no plan answers."""
    r = Rig(tmp_path)
    r.scan(two_door_house(exterior2=CLOSED))
    r.frame(x=100.0, y=201.5)
    w = r.world
    assert N.exterior_doors(w, 1, 0) == [(110, 201, 0), (110, 202, 0)] and not N.door_blocked(w, 1, 0)
    for _ in range(2):
        w.note_door_fail((110, 201, 0), "locked")
    assert N.exterior_doors(w, 1, 0) == [(110, 202, 0)] and N.shelter_plan(w, 1)["doors"] == [(110, 202, 0)]
    g = G.Shelter(1)
    cmd = g.step(w, r.acts, r.clock)
    assert (cmd.TYPE, cmd.x, cmd.y) == ("walkTo", 109.5, 202.5)            # the approach of the other door
    for _ in range(2):
        w.note_door_fail((110, 202, 0), "interrupted")
    assert N.door_blocked(w, 1, 0) and N.shelter_plan(w, 1) is None
    assert N.exterior_doors(w, 1, 0, marked=True) == [(110, 201, 0), (110, 202, 0)]


def test_a_loot_stood_against_a_locked_door_routes_in_by_the_next_door_and_marks_the_first(tmp_path):
    """P24-Z end to end (E7's case): the loot from outside fails `not adjacent` (the player on door 1's approach:
    its first failure); the route opens door 1, which fails `locked` (its second: marked); the plan's next door (2)
    is opened, the player steps in, and the loot resumes from inside on the next container; door 1 is left out of
    every plan for DOOR_RETRY_MIN."""
    from .test_survive import make as smake
    r, sv = smake(tmp_path)
    sqs = two_door_house(exterior2=CLOSED)
    for s in sqs:
        if (s["x"], s["y"]) == (112, 202):
            s["containers"] = [FRIDGE]
        if (s["x"], s["y"]) == (112, 200):
            s["containers"] = [CRATE]
    r.scan(sqs)
    r.frame(x=109.5, y=201.5)
    tick(r, sv)
    t, a = r.cmd()
    assert t == "interact" and a["kind"] == "loot" and sv.goals.current.TYPE == "LootBuilding"
    r.answer({"state": "failed", "reason": "not adjacent"})
    r.frame(x=109.5, y=201.5)
    tick(r, sv)
    assert r.world.door_fails[(110, 201, 0)][0][1] == "not adjacent"
    assert r.cmd() == ("interact", {"x": 110, "y": 201, "kind": "open", "filter": "all", "maxWeight": 0.0})
    assert last(tmp_path)["inputs"]["branches"]["goal"]["route"] == "open"
    r.answer({"state": "failed", "reason": "locked"})
    r.frame(x=109.5, y=201.5)
    tick(r, sv)
    assert r.world.marked_doors() == {(110, 201, 0)} and r.world.door_marks[(110, 201, 0)][1] == "locked"
    assert r.cmd() == ("interact", {"x": 110, "y": 202, "kind": "open", "filter": "all", "maxWeight": 0.0})
    r.answer()
    r.frame(x=109.5, y=201.5)
    tick(r, sv)
    t, a = r.cmd()
    assert t == "walkTo" and last(tmp_path)["inputs"]["branches"]["goal"]["route"] == "enter"
    r.answer()
    r.frame(x=a["x"], y=a["y"])
    tick(r, sv)
    t, a = r.cmd()
    # Task 18 fix 1 (major 3): the loot failed `not adjacent` from outside kept its container, so it resumes there
    assert (t, a["kind"], a["x"], a["y"]) == ("interact", "loot", 112, 202) and sv.goals.current.TYPE == "LootBuilding"
    assert N.exterior_doors(r.world, 1, 0) == [(110, 202, 0)]
    r.frame(x=111.5, y=202.5, game_min=480.0 + W.DOOR_RETRY_MIN)
    assert sorted(N.exterior_doors(r.world, 1, 0)) == [(110, 201, 0), (110, 202, 0)]


def test_a_building_with_every_door_marked_is_blocked_and_passed_over_for_the_next(tmp_path):
    """P24-Z: the only door marked, the view reads the building `blocked` (`x`, its `door` None) and the scripted
    source loots the next building; a LootBuilding whose route finds no door left fails `no door`; the LLM source
    refuses the blocked building."""
    from .test_survive import make as smake
    r, sv = smake(tmp_path)
    one = house(1, 110)
    two = house(2, 130)
    for s in one + two:
        if (s["x"], s["y"]) in ((111, 201), (131, 201)):
            s["containers"] = [FRIDGE]
    r.scan(one + two)
    r.frame(x=109.5, y=201.5)
    for _ in range(2):
        r.world.note_door_fail((110, 201, 0), "locked")
    v = view(r.world, sv)
    b1 = next(b for b in v["buildings"] if b["id"] == 1)
    assert b1["blocked"] is True and b1["door"] is None and " x h:" in V._building(b1)
    assert G.ScriptedSource().propose(v).args() == {"building": 2}
    assert L.place_error(G.LootBuilding(1), v) == "invalid: refused"
    g = G.LootBuilding(1)
    g.kit = G.Kit(r.world, r.acts, r.clock)
    g.begin(r.world, r.acts, r.clock)
    g.route_due = True
    assert g.choose(r.world, r.acts, r.clock) is None and (g.state, g.reason) == ("failed", "no door")


def test_e7_s_loots_at_the_locked_back_door_mark_it_and_the_route_takes_the_north_door():
    """P24-Z on E7's record (lines 236-282 replayed: the recorded loots, bound to the record's aids): the character
    stood at (10770.45, 10633.45) on the locked back door's square (10770, 10633) of building 5 while its loots failed
    `not adjacent` (257 a55, 269 a56); the replayed Survive counts them on that door and marks it at the second, so
    building 5's exterior doors read only the north door (10768, 10628), and a route's first step walks to its
    approach square (10768, 10627). Read with P24-X off (`Survive.ENGAGE`): with it on, the zombie listed at 9.4
    tiles from line 243 is sought and the record's loots are not replayed."""
    from agent.base import replay_decisions as R
    got = {}

    def grab(sv):
        sv.ENGAGE = False
        real = sv.tick

        def tick_(world, actions):
            out = real(world, actions)
            got["w"] = world
            return out
        sv.tick = tick_
    R.replay(R.ARTIFACTS + "/e_day_7-20261029-140813", upto=282, mutate=grab)
    w = got["w"]
    door = (10770, 10633, 0)
    assert w.door_near((10770.4521484375, 10633.451171875), 0, S.DOOR_NEAR_R) == door
    assert w.marked_doors() == {door} and w.door_marks[door][1] == "not adjacent"
    assert N.exterior_doors(w, 5, 0) == [(10768, 10628, 0)]
    cmd, step = N.shelter_step(w, N.shelter_plan(w, 5))
    assert step == "approach" and (cmd.x, cmd.y) == (10768.5, 10627.5)


# ================================================================ Task 18 fix 1: the blocker, major 2, ruling 2
ME = (100.5, 200.5)


def walled(at=None, wall_x=102, y0=197, y1=203, hop=False):
    """The open grid 90..120 by 190..212 with a wall on the west edge of x == `wall_x` from y0 to y1 (a way round
    north and south of it; `hop` a hoppable fence)."""
    at = dict(at or {})
    for y in range(y0, y1 + 1):
        at[(wall_x, y)] = dict(at.get((wall_x, y), {}), blockW=True, hopW=hop)
    return grid(90, 120, 190, 212, at)


def zm(zid, x, y, has_target=True):
    return zd(zid, x, y, has_target=has_target, me=ME)


def stance_fight(r, sought=()):
    """A Fight as Survive's engage makes it: the stance, the seek, the held threats; `sought` already sought."""
    f = P.Fight(r.world, r.acts, r.clock)
    f.stance, f.seek, f.threats = True, True, list(r.world.zombies.values())
    f.sought |= set(sought)
    return f


def sent(r, f, cmd):
    f.send(cmd)
    r.fake.answer({cmd.TYPE: ["accepted"]})
    r.pump()


def seek_walk(tmp_path):
    """The blocker's case: target 1 chasing 8 tiles east behind a wall: the seek's walk round it, at a walk."""
    r = Rig(tmp_path)
    r.scan(walled())
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 108.5, 200.5)])
    f = stance_fight(r)
    cmd = f.choose()
    assert (cmd.TYPE, cmd.gait) == ("walkTo", "walk") and f.why["seek"] is True and f.why["leg"] == "walk"
    sent(r, f, cmd)
    assert f._stance_walk[2] == "seek" and f.busy()
    return r, f


def test_the_seek_walk_round_a_wall_gives_way_to_a_zombie_closing_nearer_and_the_seek_takes_it(tmp_path):
    """The review's blocker (E7's a12 held 21 ticks while 564 closed to 2.84 tiles): another zombie SEEK_SWITCH_R
    nearer than the walk's target ends the walk, and the next choose re-pins the seek to it (`seek_switch`), its line
    clear: an aim toward it. One under the margin nearer keeps the walk."""
    r, f = seek_walk(tmp_path)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 108.5, 200.5), zm(2, 100.5, 193.5)])
    assert f.busy() is False
    cmd = f.choose()
    assert cmd.TYPE == "aim" and cmd.targetId == 2 and f.why["seek_switch"] is True and f.why["leg"] == "seek"
    (tmp_path / "b").mkdir()
    r2, f2 = seek_walk(tmp_path / "b")
    r2.frame(x=ME[0], y=ME[1], zombies=[zm(1, 108.5, 200.5), zm(2, 100.5, 192.8)])   # 7.7 tiles: under the margin
    assert f2.busy() is True


@pytest.mark.parametrize("pos, why", [((102.9, 200.5), "inside KEEP_R: the backpedal"),
                                      ((101.9, 200.5), "in reach: the enter leg"),
                                      ((111.0, 200.5), "beyond DISENGAGE_R")])
def test_the_seek_walk_gives_way_inside_keep_r_in_reach_and_beyond_disengage_r(tmp_path, pos, why):
    r, f = seek_walk(tmp_path)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, *pos)])
    assert f.busy() is False, why


def test_the_seek_walk_gives_way_when_the_line_clears_and_holds_while_it_does_not(tmp_path):
    r, f = seek_walk(tmp_path)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 107.5, 200.5)])
    assert f.busy() is True                                               # nearer, still behind the wall
    r.scan(grid(90, 120, 190, 212))
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 107.5, 200.5)])
    assert f.busy() is False and f.choose().TYPE == "aim" and f.why["leg"] == "seek"


def advance_walk(tmp_path):
    """The advance (a target already sought, STAND_MAX_S gone) closes on its pin: its walk round the wall."""
    r = Rig(tmp_path)
    r.scan(walled())
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 106.5, 200.5)])
    f = stance_fight(r, sought={1})
    f._stand, f.advance = (1, r.clock(), 1.0), True
    cmd = f.choose()
    assert cmd.TYPE == "walkTo" and f.why["advance"] is True
    sent(r, f, cmd)
    assert f._stance_walk[2] == "advance" and f.busy()
    return r, f


@pytest.mark.parametrize("y2, gives", [(201.7, True), (202.7, True), (196.5, True), (200.5 + 5.7, False)])
def test_the_advance_walk_round_a_wall_gives_way_to_a_closing_zombie(tmp_path, y2, gives):
    """Task 18 fix 2, the re-review's blocker 1 (E7 at 327 sent this walk): the advance's walk round a wall ends when
    another zombie the Fight may pin closes inside KEEP_R (1.2 and 2.2 tiles) or stands SEEK_SWITCH_R or more nearer
    than its target (4.0 against 6.0); one no nearer (5.7 against 6.0) is not a reason. The next choose re-pins to it
    and the advance ends (the stance's, not a walk toward the old target)."""
    r, f = advance_walk(tmp_path)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 106.5, 200.5), zm(2, 100.5, y2)])
    assert f.busy() is (not gives)
    if gives:
        cmd = f.choose()
        assert f.target == 2 and f.advance is False and cmd.TYPE == "aim" and cmd.targetId == 2


def test_the_advance_walk_round_a_wall_holds_for_its_own_target_until_reach(tmp_path):
    r, f = advance_walk(tmp_path)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 104.5, 200.5)])
    assert f.busy() is True
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 102.3, 200.5)])
    assert f.busy() is False


def test_the_advance_aim_leg_gives_way_to_a_zombie_inside_keep_r(tmp_path):
    r = Rig(tmp_path)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 106.5, 200.5)])
    f = stance_fight(r, sought={1})
    f._stand, f.advance = (1, r.clock(), 1.0), True
    cmd = f.choose()
    assert cmd.TYPE == "aim" and f.why["leg"] == "toward"
    sent(r, f, cmd)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 106.0, 200.5), zm(2, 100.5, 202.0)])
    assert f.busy() is False


def test_the_seek_walk_beyond_aim_r_gives_way_once_the_target_is_within_aim_r(tmp_path):
    r = Rig(tmp_path)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 113.0, 200.5)])
    f = stance_fight(r)
    cmd = f.choose()
    assert (cmd.TYPE, cmd.gait) == ("walkTo", "walk")
    sent(r, f, cmd)
    assert f._stance_walk[2] == "far" and f.busy()
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 112.6, 200.5)])
    assert f.busy() is True
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 110.5, 200.5)])
    assert f.busy() is False


def test_a_seek_aim_leg_gives_way_to_a_nearer_zombie(tmp_path):
    """E7's lines 61-66 (the seek on 534 held its leg while 564 came from 10.2 to 4.3 tiles): a running seek leg ends
    once another zombie is SEEK_SWITCH_R nearer, and the seek takes it."""
    r = Rig(tmp_path)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 108.5, 200.5)])
    f = stance_fight(r)
    cmd = f.choose()
    assert cmd.TYPE == "aim" and f.why["leg"] == "seek"
    sent(r, f, cmd)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 108.0, 200.5), zm(2, 100.5, 193.5)])
    assert f.busy() is False and f.choose().targetId == 2


E7 = "e_day_7-20261029-140813"


def _e7_lines(upto, engage_any=False, no_give=False):
    """E7 replayed to `upto`: the rows, and per tick {walk: the running stance walk's target id else None, zs:
    {zombie id: tiles}}. `engage_any`: the engage as built at 9c477f80 (every zombie within ENGAGE_R engageable), so
    the review's walk at line 52 is reproduced; `no_give`: the blocker's mutant (the walk never gives way)."""
    from agent.base import replay_decisions as R
    out = {}

    def m(sv):
        if engage_any:
            sv._engageable = lambda zid, z: True
        real = sv.tick

        def tick_(world, actions):
            res = real(world, actions)
            f, cur = sv.fight, actions.current
            walk = (f._stance_walk[1] if f is not None and f._stance_walk is not None and cur is not None
                    and f._stance_walk[0] is cur else None)
            zs = {zid: P.zdist(world, z) for zid, z in world.zombies.items() if z.get("x") is not None}
            out[len(out) + 1] = {"walk": walk, "zs": zs}
            return res
        sv.tick = tick_
    orig = P.Fight._walk_gives_way
    if no_give:
        P.Fight._walk_gives_way = lambda self: False
    try:
        rows = R.replay(R.ARTIFACTS + "/" + E7, upto=upto, mutate=m)
    finally:
        P.Fight._walk_gives_way = orig
    return rows, out


def _walk_held_wrongly(out, a, b):
    """The lines in a..b on which a stance walk ran on with its target beyond DISENGAGE_R or gone, or another zombie
    SEEK_SWITCH_R nearer than it (the blocker's rule)."""
    bad = []
    for k in range(a, b + 1):
        o = out[k]
        if o["walk"] is None:
            continue
        d = o["zs"].get(o["walk"])
        if d is None or d > P.DISENGAGE_R or any(v <= d - P.SEEK_SWITCH_R for z, v in o["zs"].items()
                                                  if z != o["walk"]):
            bad.append(k)
    return bad


def test_e7_lines_52_to_73_the_seek_walk_round_the_wall_gives_way_and_never_runs_past_a_closer_zombie():
    """The review's blocker on E7's record: with the engage as built at 9c477f80 (`engage_any`), the seek walk round
    the wall on 533 was sent at line 52 (8.17 tiles; at line 49, 8.07 tiles, since ENGAGE_R is 9, fix 1's minor 8)
    and, before this fix, ran to line 73 while 533 receded past DISENGAGE_R and 564 and 534 closed to 2.84 and 3.10
    tiles (the mutant `no_give` reproduces it); now it gives way at line 56 (its line toward 533 clear) and no stance
    walk runs on any tick of 49-73 past its target's leaving or a nearer zombie. Under HEAD's whole rules 533, idle behind the wall, is not engaged until it chases (line 54), the
    walk round the wall then gives way at 56, and the seek on 534 switches to 564 at line 64 (6.22 tiles against
    7.12), across a fence and chasing: a standing leg, not a walk."""
    rows, out = _e7_lines(73, engage_any=True)
    assert rows[48]["action"] == {"type": "walkTo", "args": {"gait": "walk", "x": 10740.5, "y": 10647.5}}
    assert out[49]["walk"] == 533 and out[55]["walk"] == 533 and out[56]["walk"] is None
    assert rows[55]["action"]["type"] == "aim"
    assert _walk_held_wrongly(out, 49, 73) == []
    _, mut = _e7_lines(73, engage_any=True, no_give=True)
    assert all(mut[k]["walk"] == 533 for k in range(49, 74)) and _walk_held_wrongly(mut, 49, 73) != []
    rows, out = _e7_lines(73)
    assert all(rows[k - 1]["branch"] != "threat" for k in range(47, 54))
    assert rows[53]["action"]["type"] == "walkTo" and out[55]["walk"] == 533 and out[56]["walk"] is None
    w = rows[63]["inputs"]["branches"]["threat"]
    assert rows[63]["action"]["args"]["targetId"] == 564 and w["leg"] == "stand" and w["seek_switch"] is True
    assert _walk_held_wrongly(out, 47, 73) == []


def test_a_seek_walk_that_fails_marks_its_target_for_seek_skip_s(tmp_path):
    """Major 2 (E4's gate zombie sought every UNREACHABLE_S): a seek walk failed for a walk reason skips its target
    SEEK_SKIP_S (60 s, three UNREACHABLE_S), longer than a swing's mark."""
    assert P.SEEK_SKIP_S == 60.0 and P.SEEK_SKIP_S > P.UNREACHABLE_S
    r, f = seek_walk(tmp_path)
    r.fake.answer({"walkTo": [{"state": "failed", "reason": "no path"}]})
    r.pump()
    f.observe()
    assert f.unreachable[1] == r.clock() + P.SEEK_SKIP_S and f.target is None


def enclosed(zx=108, zy=200, has_path=False):
    """The open grid with square (zx, zy) walled on its four edges (no way to a square beside it), or with `has_path`
    a wall segment west of it only (a way round)."""
    if has_path:
        return walled(wall_x=zx - 2)
    at = {(zx, zy): {"blockW": True, "blockN": True}, (zx + 1, zy): {"blockW": True}, (zx, zy + 1): {"blockN": True}}
    return grid(90, 120, 190, 212, at)


def test_an_idle_zombie_with_no_way_to_it_is_not_engaged_and_the_goal_runs(tmp_path):
    """Major 2 and ruling 2: an idle zombie (`hasTarget` false) 8 tiles off, its square walled in (no clear line, no
    square beside it the bounded flood reaches): not engaged, marked `unsought` for UNREACHABLE_S (no flood re-read
    meanwhile), logged; the goal runs. Once it chases it is engaged at once."""
    r, sv = make(tmp_path)
    r.scan(enclosed())
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 108.5, 200.5, has_target=False)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "threat" and sv.mode is None
    assert threat_why(tmp_path) == {"unsought": [1]} and sv.unsought[1] == r.clock() + P.UNREACHABLE_S
    calls = []
    real = r.world.flood
    r.world.flood = lambda *a, **k: calls.append(1) or real(*a, **k)
    r.frame(x=ME[0] + 0.6, y=ME[1], zombies=[zm(1, 108.5, 200.5, has_target=False)])
    tick(r, sv)
    assert calls == [] and sv.mode is None                                  # the mark answers, no flood
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 108.5, 200.5)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and sv.mode == "fight"


@pytest.mark.parametrize("sqs, engaged", [("path", True), ("clear", True), ("unscanned", False)])
def test_an_idle_zombie_is_engaged_with_a_clear_line_or_a_way_to_it(tmp_path, sqs, engaged):
    """Ruling 2's non-chasing target: engaged with its line clear, or a square beside it in the player's bounded
    flood (a wall with a way round); one on ground the map does not hold (the spawn's: no line read, no flood) is
    not."""
    r, sv = make(tmp_path)
    r.scan({"path": enclosed(has_path=True), "clear": grid(90, 120, 190, 212),
            "unscanned": grid(95, 104, 196, 205)}[sqs])
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 108.5, 200.5, has_target=False)])
    tick(r, sv)
    assert (sv.mode == "fight") is engaged


@pytest.mark.parametrize("inside", [False, True])
def test_a_chasing_zombie_across_a_building_s_walls_is_not_engaged(tmp_path, inside):
    """Major 2: a zombie inside a building the character is outside of (a locked or unentered one), or outside the
    building the character shelters in (the night's shelter, the converse), is not engaged, chasing or not."""
    r, sv = make(tmp_path)
    r.scan(house(1, 110, door=LOCKED) + grid(98, 106, 196, 206))
    me, z = ((111.5, 201.5), (104.5, 201.5)) if inside else ((104.5, 201.5), (111.5, 201.5))
    r.frame(x=me[0], y=me[1], zombies=[zd(1, z[0], z[1], me=me)])
    tick(r, sv)
    assert sv.mode is None and last(tmp_path)["branch"] != "threat"
    assert threat_why(tmp_path) == {"unsought": [1]}


def test_a_running_fight_with_only_an_unreachable_idle_zombie_left_ends_and_the_goal_runs(tmp_path):
    """Major 2: the fight engaged on a chasing zombie, an idle one walled in beside it (`unsought` in the fight's why,
    never pinned anew beyond DANGER_R: the Fight's `avoid`); once the chaser is gone the fight ends (`_released`) and
    the goal runs."""
    r, sv = make(tmp_path)
    r.scan(enclosed())
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 107.5, 203.5), zm(2, 108.5, 200.5, has_target=False)])
    tick(r, sv)
    assert sv.mode == "fight" and threat_why(tmp_path)["unsought"] == [2] and sv.fight.target == 1
    assert sv.fight.avoid == {2}
    r.answer()
    r.advance(W.ZOMBIE_TTL_S + 1)                                           # the chaser gone from the World
    r.frame(x=ME[0], y=ME[1], zombies=[zm(2, 108.5, 200.5, has_target=False)])
    tick(r, sv)
    assert 1 not in r.world.zombies and sv.mode is None and last(tmp_path)["branch"] != "threat"


def test_ruling_2_no_seek_on_a_room_or_door_square_nor_at_a_chaser_across_a_fence(tmp_path):
    """The review's ruling 2: a chasing zombie at 8 tiles is fought standing, never sought, (a) with the character
    on a room square of the building the zombie is in too, (b) on a door square, (c) across a known fence (the
    fence is the chokepoint); an idle zombie across the fence (the flood climbs a hoppable edge to it) is sought."""
    room = {(x, y): {"room": "hall", "building": 1} for x in range(90, 113) for y in range(190, 213)}
    cases = {"room": grid(90, 120, 190, 212, room),                          # its east side open: a way out
             "door": grid(90, 120, 190, 212, {(100, 200): {"door": dict(CLOSED)}}),
             "fence": walled(wall_x=104, y0=190, y1=212, hop=True)}
    for name, sqs in cases.items():
        (tmp_path / name).mkdir()
        r, sv = make(tmp_path / name)
        r.scan(sqs)
        r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 108.5, 200.5)])
        tick(r, sv)
        w = threat_why(tmp_path / name)
        assert sv.mode == "fight" and w["leg"] == "stand" and "seek" not in w, name
    (tmp_path / "idle").mkdir()
    r, sv = make(tmp_path / "idle")
    r.scan(cases["fence"])
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 108.5, 200.5, has_target=False)])
    tick(r, sv)
    assert sv.mode == "fight" and threat_why(tmp_path / "idle")["leg"] == "seek"
    assert P.seek_allowed(r.world, (1, r.world.zombies[1], 8.0), True) is False
    (tmp_path / "trapped").mkdir()                                          # held ground with no stance: no engage
    r, sv = make(tmp_path / "trapped")
    r.scan(grid(90, 120, 190, 212, {(x, y): {"room": "hall", "building": 1} for x in range(90, 121)
                                    for y in range(190, 213)}))
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 108.5, 200.5)])
    tick(r, sv)
    assert sv.mode is None and last(tmp_path / "trapped")["branch"] != "threat"


@pytest.mark.parametrize("key", ["e2", "e3", "e4", "e5", "f1", "f1-caps15"])
def test_the_spawn_engage_in_every_golden_is_neither_engaged_nor_sought(key):
    """Task 18's every golden engaged the zombie listed 7.0 tiles from the fixture's spawn at line 1 (the sixth's a
    seek walk round a wall: the blocker's live first act): it stands idle on ground the first frame's map does not
    hold (no line read, no flood), so it is not engaged (major 2: `unsought`, logged on the sixth), and the spawn is a
    room square (`_chokepoint`), so even engaged it would not be sought (ruling 2), and on the five PZA/1.4 builds
    (no stance) held ground engages nothing."""
    from agent.base import replay_decisions as R
    got = {}

    def m(sv):
        real = sv.tick

        def tick_(world, actions):
            if not got:
                zid, z = next((i, z) for i, z in world.zombies.items() if z.get("x") is not None)
                got.update(z=z, d=P.zdist(world, z), choke=sv._chokepoint(), eng=sv._engageable(zid, z),
                           line=P.line_to(world, z))
                sv.unsought.clear()
            return real(world, actions)
        sv.tick = tick_
    rows = R.replay(R.ARTIFACTS + "/" + R.RUNS[key], caps=R.HELLO_CAPS.get(key), upto=2, mutate=m)
    assert got["d"] == 7.0 and got["z"].get("hasTarget") is False and got["line"] is None
    assert got["eng"] is False and got["choke"] is True
    assert rows[0]["branch"] != "threat"
    assert bool(rows[0]["inputs"]["branches"]["threat"].get("unsought")) is (key == "f1-caps15")


# ================================================================ Task 18 fix 1: majors 3 to 6 (the review's numbering)
from .test_policies import square   # noqa: E402
from .test_survive_g import hold   # noqa: E402


@pytest.mark.parametrize("end, marked", [({"state": "failed", "reason": "not adjacent"}, False),
                                         ({"state": "failed", "reason": "stuck"}, False),
                                         ({"state": "failed", "reason": "no match"}, True),
                                         ("done", True)])
def test_a_failed_loot_keeps_its_container_until_it_fails_twice(tmp_path, end, marked):
    """The review's major 3 (E7's a55 to a62: eight loots failed `not adjacent` from outside building 5, each
    container marked looted, the building read looted with 28 containers known): a loot marks its containers looted
    for its use only when it ended done or failed `no match` (nothing of the use there); any other end counts one
    failure on each, and the second (LOOT_FAILS_TO_PASS, as the doors) passes it."""
    assert P.LOOT_FAILS_TO_PASS == 2
    r = Rig(tmp_path)
    r.scan([square(110, 200, containers=[FRIDGE])])
    r.frame(x=109.5, y=200.5)
    lh = P.LootHouse(r.world, r.acts, r.clock, want="food")
    for n in (1, 2):
        lh.send(lh.choose())
        r.answer(end)
        lh.observe()
        key = next(iter(r.world.containers))
        assert ("food" in r.world.containers[key]["looted"]) is (marked or n == 2), n
        if marked:
            break
    assert lh.choose() is None


def _e7_loots(upto, fixed=True):
    """E7 replayed with P24-X off (the record's loots replayed, as `test_e7_s_loots_at_the_locked_back_door_...`),
    each recorded loot handed to the goal kit's LootHouse (`pending`) and its end observed every tick: the World's
    containers, {(x, y, filter): end state and reason} of the loots."""
    from agent.base import replay_decisions as R
    got = {"ends": {}}

    def m(sv):
        sv.ENGAGE = False
        loot = sv.goals.kit.loot
        real_send, real_tick = sv.goals.send, sv.tick

        def send(cmd):
            a = real_send(cmd)
            if cmd.TYPE == "interact" and cmd.kind == "loot":
                loot.pending.append((cmd.x, cmd.y, 0, a))
                got["ends"][(cmd.x, cmd.y, cmd.filter)] = a
            return a

        def tick_(world, actions):
            loot.world, loot.actions = world, actions
            loot.observe()
            got["w"] = world
            return real_tick(world, actions)
        sv.goals.send, sv.tick = send, tick_
    R.replay(R.ARTIFACTS + "/" + E7, upto=upto, mutate=m)
    return got["w"], {k: (a.state, a.reason) for k, a in got["ends"].items()}


def test_e7_s_eight_loots_failed_not_adjacent_keep_their_containers():
    """Major 3 on E7's record (lines 1-357): the eight loots a55 to a62 (lines 241 to 333) failed `not adjacent` from
    the back door's square; each container they targeted stays lootable for its use (one failure each: before this
    fix every one was marked looted, and the LootBuilding ended `looted`), while the loots that ended done (a54 at
    line 236, food at (10769, 10635), and the spawn house's) mark theirs."""
    w, ends = _e7_loots(357)
    failed = [k for k, e in ends.items() if e == ("failed", "not adjacent")]
    assert len(failed) == 8 and ends[(10766, 10633, "food")] == ("failed", "not adjacent")
    for x, y, use in failed:
        for key, c in w.containers.items():
            if key[:2] == (x, y) and any(P.use_of(i) == use for i in c["items"]):
                assert use not in c["looted"], (x, y, use)
    done = [k for k, e in ends.items() if e[0] == "done"]
    assert done and all(any(key[:2] == k[:2] and k[2] in c["looted"] for key, c in w.containers.items())
                        for k in done)


def test_a_door_marked_from_outside_stays_a_way_out_from_inside_and_the_adoption_keeps_it(tmp_path):
    """The review's major 4 (the marks dropped the way out): a door marked from outside (`side` "out": E7's locked
    back door) is left out of every approach from outside (the shelter plans, the loot's route, the view's `door`
    and `blocked`), and stays a way out from inside (`night.exits`, `exit_plan`: the flee walks out through it) and
    the adoption's door (`adoptable`, `Flee._adopt`), ranked after the doors not marked."""
    r = Rig(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=108.5, y=201.5)
    w, door = r.world, (110, 201, 0)
    for _ in range(2):
        w.note_door_fail(door, "locked")                                       # outside: side "out"
    assert w.door_marks[door][2] == "out" and w.marked_doors("out") == {door} and w.marked_doors("in") == set()
    assert N.exterior_doors(w, 1, 0) == [] and N.door_blocked(w, 1, 0) and N.shelter_plan(w, 1) is None
    r.frame(x=111.5, y=201.5)                                                  # inside
    assert [e["door"] for e in N.exits(w, 1, 0)] == [door] and P.adoptable(w)
    plan = P.exit_plan(w, [])
    assert plan is not None and plan["door"] == door
    f = P.Flee(r.world, r.acts, r.clock, threats=[zd(1, 112.5, 202.5, me=(111.5, 201.5))])
    cmd = f.choose()
    assert cmd.TYPE == "walkTo" and f.why["exit"] == 1 and f.why["door"] == list(door)
    f.adopted = False
    assert f._adopt(f._threats())["doors"] == [door]


def test_a_door_failed_from_inside_is_marked_from_inside_and_ranked_last_for_the_ways_out(tmp_path):
    """The mark keeps its side: a door whose open failed twice from inside (`_door_failed` reads the player's room
    square) is `side` "in": the approaches from outside keep it, the ways out rank it after an unmarked one."""
    from .test_survive import make as smake
    r, sv = smake(tmp_path)
    r.scan(two_door_house(exterior2=CLOSED))
    r.frame(x=111.5, y=201.5)
    for _ in range(2):
        sv._door_failed(type("A", (), {"type": "interact", "state": "failed", "reason": "locked",
                                       "args": {"x": 110, "y": 201, "kind": "open"}})())
    w = r.world
    assert w.door_marks[(110, 201, 0)][2] == "in" and (110, 201, 0) in N.exterior_doors(w, 1, 0)
    assert N.exterior_doors(w, 1, 0, marked=True)[-1] == (110, 201, 0)
    plan = P.exit_plan(w, [])
    assert plan["door"] == (110, 202, 0)


def test_the_container_want_is_capped_at_two_vessels_held(tmp_path):
    """The review's major 5 (E7's replayed map: 14 empty vessels known in building 5, 8 in building 2, each loot
    filling to the cap before the food): `container` is wanted only while fewer than CONTAINERS_HELD_N (2) vessels
    (`water` and `container` held) are held; with two held the loot goes to the food."""
    assert G.CONTAINERS_HELD_N == 2
    from .test_survive import make as smake
    r, sv = smake(tmp_path)
    sqs = house(1, 110)
    for s in sqs:
        if (s["x"], s["y"]) == (111, 201):
            s["containers"] = [{"type": "counter", "n": 2, "items": ["Base.Apple", "Base.PopEmpty"]}]
    r.scan(sqs)
    r.frame(x=109.5, y=201.5)
    hold(r, 5, "Base.PopEmpty", use="container")
    assert G.wanted_uses(r.world) == G.STOCK_WANTS
    hold(r, 6, "Base.WaterBottle", use="water")
    assert "container" not in G.wanted_uses(r.world)
    g = G.LootBuilding(1)
    g.kit = G.Kit(r.world, r.acts, r.clock)
    cmd = g.step(r.world, r.acts, r.clock)
    assert cmd.TYPE == "interact" and cmd.filter == "food"
    assert "container" not in view(r.world, sv)["stock_uses"]


def test_after_rest_n_rests_the_woods_radius_widens_by_woods_step_up_to_its_cap_and_a_new_building_resets_it(
        tmp_path):
    """The review's major 6 and ruling 3 (E7's sparse spawn: four buildings known, the 40-tile ring mapped, the
    scripted source then resting): after REST_N (3) Rests in a row ended rested with no building newly read, the woods
    radius widens by WOODS_STEP (20) up to WOODS_MAX_R (80); the next proposal is the edge within the widened ring of
    the known cluster; another goal's end restarts the run; a building newly read resets the radius to WOODS_R. The
    fixture: one house, the ground round it mapped to a solid ring with one gap 49.5 tiles west of the house's box."""
    assert (G.REST_N, G.WOODS_STEP, G.WOODS_MAX_R) == (3, 20.0, 80.0)
    from .test_survive import make as smake
    r, sv = smake(tmp_path)
    ring = {(x, y): {"solid": True} for x in range(60, 117) for y in (196, 206)}
    ring.update({(x, y): {"solid": True} for x in (60, 116) for y in range(196, 207)})
    del ring[(60, 201)]
    hs = {(s_["x"], s_["y"]) for s_ in house(1, 110)}
    r.scan([q for q in grid(60, 116, 196, 206, ring) if (q["x"], q["y"]) not in hs] + house(1, 110))
    r.frame(x=100.5, y=201.5)
    runner, kit = sv.goals, sv.goals.kit
    runner.observe(r.world, r.acts)
    kit.explore.scanned.add(P.place_of(r.world))                                # the place scanned
    v = view(r.world, sv)
    assert kit.woods_r == G.WOODS_R and v["woods_r"] == G.WOODS_R and v["edge"] is None
    assert G.ScriptedSource().propose(v).TYPE == "Rest"
    for n in range(1, 3 * G.REST_N + 1):
        g = G.Rest(1.0)
        g.state = "done"
        runner._close(g)
        assert kit.woods_r == min(G.WOODS_R + G.WOODS_STEP * (n // G.REST_N), G.WOODS_MAX_R), n
        if n == G.REST_N:
            v = view(r.world, sv)
            assert v["woods_r"] == 60.0 and v["edge"] == [60, 201]
            g = G.ScriptedSource().propose(v)
            assert g.TYPE == "ExploreToward" and (g.x, g.y) == (60, 201)
            assert L.place_error(g, v) is None and L.place_error(g, dict(v, woods_r=G.WOODS_R)) is not None
    assert kit.woods_r == G.WOODS_MAX_R
    other = G.ExploreToward(1, 1)
    other.state = "done"
    kit.woods_r, kit.rests = G.WOODS_R + G.WOODS_STEP, 2
    runner._close(other)
    assert kit.rests == 0 and kit.woods_r == G.WOODS_R + G.WOODS_STEP           # another goal: the run restarts
    r.scan(house(2, 140))
    runner.observe(r.world, r.acts)
    assert kit.woods_r == G.WOODS_R and kit.rests == 0                          # a building newly read


# ================================================================ Task 18 fix 1: the review's minors
def test_the_woods_filter_is_memoised_per_map_version_and_reads_as_the_box_test(tmp_path):
    """The review's minor 7 (the woods test ran every box against every square on every proposal, 136.6 ms on E7's
    map with 44 boxes): `World.near_buildings(r)`, bucketed on an r-tile grid and memoised per map version, is the
    brute box test's set, and `unexplored_edge(woods_r)` reads it (one build per map version)."""
    r = Rig(tmp_path)
    r.scan(grid(40, 160, 180, 220) + house(1, 110) + house(2, 150) + house(3, 60, 215))
    r.frame(x=100.5, y=201.5)
    w = r.world
    for rad in (G.WOODS_R, 60.0, 7.5):
        brute = {(x, y) for (x, y, _) in w.map
                 if any(W._box_dist(b, x + 0.5, y + 0.5) <= rad for b in w.building_boxes().values())}
        assert w.near_buildings(rad) == brute, rad
    built = []
    real = w.memo
    w.memo = lambda key, fn: real(key, lambda: built.append(key) or fn())
    w._memo.pop(("near_buildings", G.WOODS_R), None)
    w.unexplored_edge(G.WOODS_R)
    w.unexplored_edge(G.WOODS_R)
    assert built.count(("near_buildings", G.WOODS_R)) == 1
    r.scan([square(200, 200)])                                                   # a new map version: rebuilt
    w.unexplored_edge(G.WOODS_R)
    assert built.count(("near_buildings", G.WOODS_R)) == 2


def test_engage_r_is_a_tile_inside_disengage_r_so_a_zombie_idling_at_ten_tiles_does_not_flap(tmp_path):
    """The review's minor 8: ENGAGE_R 9, DISENGAGE_R 10. A zombie at 9.5 tiles is not engaged (the goal runs); one
    engaged at 8.5 that steps back to 9.6 is still held (the fight goes on); beyond DISENGAGE_R the fight ends."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 109.5, 200.0)])
    tick(r, sv)
    assert sv.mode is None and last(tmp_path)["branch"] != "threat"
    r.frame(zombies=[zd(1, 108.5, 200.0)])
    tick(r, sv)
    assert sv.mode == "fight"
    r.answer()
    r.frame(zombies=[zd(1, 109.6, 200.0)])
    tick(r, sv)
    assert sv.mode == "fight" and last(tmp_path)["branch"] == "threat"
    r.frame(zombies=[zd(1, 110.4, 200.0)])
    tick(r, sv)
    assert sv.mode is None


def test_the_wide_turns_read_the_group_ahead_before_the_group_blind_tier(tmp_path):
    """The review's minor 9: boxed in a fence corner (every turn within 90 degrees blocked), the first wide turn clear
    of the map (-120) runs at the far group (three zombies 6 tiles off at 250 degrees, one at 1.6 tiles west setting
    the away vector); the group-aware wide tier comes first, so the leg takes 150, clear and with no held threat
    ahead."""
    import math as m
    at = {(103, y): {"blockW": True} for y in range(190, 211)}
    at.update({(x, 201): dict(at.get((x, 201), {}), blockN=True) for x in range(90, 103)})
    r = Rig(tmp_path)
    r.scan(grid(90, 106, 190, 210, at))
    me = (102.5, 200.5)

    def pt(a, d):
        return me[0] + d * m.cos(m.radians(a)), me[1] + d * m.sin(m.radians(a))
    zs = [zombie(1, *pt(180, 1.6), me=me)] + [zombie(i, *pt(250 + 3 * (i - 3), 6.0 + 0.3 * i), me=me)
                                              for i in (2, 3, 4)]
    r.frame(x=me[0], y=me[1], zombies=zs)
    f = P.Flee(r.world, r.acts, r.clock, threats=list(r.world.zombies.values()))
    ts = f._threats()
    cmd = f._steer(ts)
    far = [z for z in ts if P.zdist(r.world, z) > P.NEAR_R]
    v = P.away_vector(r.world, [(z["x"], z["y"]) for z in ts])
    blind = next(t for t in P.WIDE_TURNS if f._clear(P._rotate(v, t)))
    assert all(not f._clear(P._rotate(v, t)) for t in P.STEER_TURNS)
    assert blind == -120 and f._ahead(P._rotate(v, blind), far)
    assert f.why["turn"] == 150 and f.why["probe"] == P.AHEAD_R and not f._ahead((cmd.vx, cmd.vy), far)


@pytest.mark.parametrize("chases, leg", [(False, "toward"), (True, "back")])
def test_an_idle_target_sought_to_keep_r_is_advanced_on_at_once(tmp_path, chases, leg):
    """The review's minor 10 (a non-chasing target sought to 2.5 tiles: back, then stand, until STAND_MAX_S from the
    seek's start runs the advance, a 10 to 20 s dither in front of an idle zombie): a sought target inside KEEP_R
    that reads no target of its own takes the advance at once (`toward` to reach); a chasing one is backpedalled
    from, iteration 7's stance."""
    r = Rig(tmp_path)
    r.scan(grid(90, 120, 190, 212))
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 105.5, 200.5, has_target=chases)])
    f = stance_fight(r)
    f.observe()
    cmd = f.choose()
    assert cmd.TYPE == "aim" and f.why["leg"] == "seek"
    sent(r, f, cmd)
    r.advance(0.5)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 102.9, 200.5, has_target=chases)])
    f.observe()
    assert 1 in f.sought and f.advance is (not chases) and f.busy() is False
    assert f.choose().TYPE == "aim" and f.why["leg"] == leg


# ================================================================ Task 18 fix 2: held ground engages no idle zombie
def held_yard(tmp_path):
    """Survive on a grid every square of which is a room of building 1: the character holds ground."""
    r, sv = make(tmp_path)
    r.scan(grid(90, 120, 190, 212, {(x, y): {"room": "hall", "building": 1} for x in range(90, 121)
                                    for y in range(190, 213)}))
    return r, sv


@pytest.mark.parametrize("x, has_target, engageable", [(108.5, False, False), (107.0, False, False),
                                                       (105.0, False, True), (108.5, True, True)])
def test_engageable_on_held_ground_refuses_an_idle_zombie_beyond_danger_r(tmp_path, x, has_target, engageable):
    """Fix 2, the re-review's blocker 2 (E7 286-332: idle 571 at 8.48 tiles superseded building 5's loot from a room
    square, 41 `stand` lines, then the advance walk out): while `_chokepoint` holds an idle zombie beyond DANGER_R
    (8.0 and 6.5 tiles) is not engageable; a chasing one (8.0) and an idle one within DANGER_R (4.5) are."""
    r, sv = held_yard(tmp_path)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, x, 200.5, has_target=has_target)])
    assert sv._chokepoint() is True
    assert sv._engageable(1, r.world.zombies[1]) is engageable


def test_engageable_off_held_ground_still_engages_an_idle_zombie_with_a_clear_line(tmp_path):
    r, sv = make(tmp_path)
    r.scan(grid(90, 120, 190, 212))
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, 108.5, 200.5, has_target=False)])
    assert sv._chokepoint() is False and sv._engageable(1, r.world.zombies[1]) is True


def _e7_threat_lines(a, b, mutant=False):
    from agent.base import replay_decisions as R

    def m(sv):
        if mutant:   # the engage as built at 45491db3: the chokepoint does not refuse an idle zombie
            def eng(zid, z):
                sv._chokepoint = lambda: False
                try:
                    return S.Survive._engageable(sv, zid, z)
                finally:
                    del sv._chokepoint
            sv._engageable = eng
    rows = R.replay(R.ARTIFACTS + "/" + E7, upto=b, mutate=m)
    return [k for k in range(a, b + 1) if rows[k - 1]["branch"] == "threat"]


def test_e7_lines_286_to_332_the_loot_from_the_room_runs_on_past_an_idle_zombie():
    """The re-review's blocker 2 on E7's record: from a room square at building 5, idle 571 (8.48 tiles, `hasTarget`
    false) engaged at 45491db3 and stood 41 lines before the advance walk at 327; now no line of 286-332 is the threat
    branch (the mutant, the engage without the chokepoint rule, brings it back)."""
    assert _e7_threat_lines(286, 332) == []
    assert _e7_threat_lines(286, 332, mutant=True) != []
