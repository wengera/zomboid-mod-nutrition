"""Survival 13 (survival iteration 12; Plan 24 Task 36; E10, `e_day_10-20261030-084253`: zero kills to the day cap,
the arms' hold set by a bite's pain at game minute 605 and never released, the seek and the pull flipping at the
12-tile listing edge, the finishing stomp refused `not valid` before the frames read the target fallen, 55 fills
rejected `no source` 60 to 159 tiles off, the doorway stand never taken). The fake mod over PZA/1.7.

- P24-AT: the arms' hold reads `body.strain` (the stiffness, #4369), set at STIFF_HARD on either arm and released under
  STIFF_SOFT; the arm pain (#4370's divider) is its own reason, `wounded`: no swing at STRAIN_HARD, a lone target still
  sought, groups fled as today.
- P24-AU: a zombie that leaves the listing (beyond LISTED_R, AIM_R's 12) is held in the seek's and the pull's reads
  at its last listed square for EDGE_HOLD_TICKS planner ticks, so a leg is not superseded by the edge's flip.
- P24-AV: the finish's stomp goes on the first frame that reads its target `onFloor` (never on a shove's knock-down
  alone); a stomp failed `stood` reads the target again (standing: the Fight's path; fallen: one more stomp, then the
  floor strike); and the flee's finish is refused for a chasing zombie standing within KEEP_R of the target (the
  deferred minor 5 of review-t32-fix1).
- P24-AW: a fill is sent only to a water source within the loaded grid (`goals.leg_max`, P24-AI) and within
  FILL_WALK_R; a loaded source farther off is walked to first (a square beside it), one beyond the grid never sent.
"""
import functools
import json

import pytest

from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .test_policies import all_sends_valid, square
from .test_survive import last, make, threat_why, tick
from .test_survive_q import fr, z


def stiff(l, r=0.0):
    return {"l": l, "r": r}


# ================================================================ P24-AT: the hold on the stiffness; the wounded reason
def test_the_stiffness_constants():
    """#4369: the health panel names a part's stiffness from 5 and calls it minor under 20."""
    assert (P.STIFF_HARD, P.STIFF_SOFT) == (20.0, 5.0) and (P.STRAIN_HARD, P.STRAIN_SOFT) == (20.0, 10.0)


@pytest.mark.parametrize("arm", [None, 5.0])
def test_the_arms_hold_sets_on_the_stiffness_of_either_arm_and_releases_under_stiff_soft(tmp_path, arm):
    """The right arm's stiffness at STIFF_HARD sets the hold (a zombie at 4 tiles, beyond KEEP_R: the `strain` flee, why
    `strain` kind `arms` with both values); at 6 it holds, under STIFF_SOFT it releases and the fight goes (its leg
    ended, so no `flip` keeps the flee)."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 104.0)], arm, stiff(0.0, 20.0))
    tick(r, sv)
    w = threat_why(tmp_path)
    assert sv.strain_hold and w["flee"] == "strain"
    assert w["strain"]["kind"] == "arms" and w["strain"]["armPain"] == arm and w["strain"]["strain"] == stiff(0.0, 20.0)
    fr(r, [z(1, 104.0)], arm, stiff(6.0, 0.0))
    tick(r, sv)
    assert sv.strain_hold and threat_why(tmp_path)["flee"] == "strain"
    r.answer()                                             # the steer leg ended: no `flip` keeps the flee
    fr(r, [z(1, 104.0)], arm, stiff(4.9, 0.0))
    tick(r, sv)
    assert not sv.strain_hold and sv.mode == "fight" and "flee" not in threat_why(tmp_path)


def test_the_arm_pain_alone_is_the_wounded_reason_never_the_hold(tmp_path):
    """E9's bite: armPain 37.6 with the stiffness 0 on both arms (E10's: 21 to 95.2 from game minute 605, never under
    21): no hold, no `strain` flee; a zombie at 4 tiles is fought, the why's `pain` naming `wounded` and both values;
    at 2 tiles the backpedal, at point blank the shove, never an attack."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 104.0)], 37.6, stiff(0.0))
    tick(r, sv)
    w = threat_why(tmp_path)
    assert not sv.strain_hold and sv.spent is None and sv.mode == "fight" and "flee" not in w
    assert w["pain"] == {"kind": "wounded", "armPain": 37.6, "strain": stiff(0.0)}
    fr(r, [z(1, 102.0)], 37.6, stiff(0.0))
    a = tick(r, sv)
    assert a.type == "aim" and threat_why(tmp_path)["leg"] == "back"
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    fr(r, [z(1, 100.8)], 37.6, stiff(0.0))
    assert tick(r, sv).type == "shove" and threat_why(tmp_path)["shove"] == "strain"
    assert not any(x.type == "attack" for x in r.acts.history)
    all_sends_valid(r)


def test_wounded_a_lone_target_is_still_sought(tmp_path):
    """armPain 25 (no stiffness), one chaser at 7 tiles and nobody else listed: the fight is sought (the seek leg),
    where the arms' hold seeks nothing."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 107.0)], 25.0, stiff(0.0))
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert sv.mode == "fight" and a.type == "aim" and w["leg"] == "seek" and w["pain"]["kind"] == "wounded"
    (tmp_path / "hold").mkdir()
    r2, sv2 = make(tmp_path / "hold")
    fr(r2, [z(1, 107.0)], 25.0, stiff(21.0))
    tick(r2, sv2)
    assert sv2.mode is None and last(tmp_path / "hold")["branch"] != "threat"


@pytest.mark.parametrize("zs", [
    [z(1, 107.0), z(2, 107.0, 202.0)],                         # a pair within ENGAGE_R
    [z(1, 107.0), z(2, 111.0, 200.5)],                         # another chaser listed: a group coming
    [z(1, 107.0), z(2, 108.0, 200.0, floor=True)],             # ... or fallen within ENGAGE_R, the target not alone
])
def test_wounded_no_fight_is_sought_but_a_lone_one(tmp_path, zs):
    """Unwounded each of these is sought (the pair, the pull, the target with a fallen one beside it); wounded none
    is: the goal runs."""
    for case, arm in (("well", None), ("hurt", 25.0)):
        (tmp_path / case).mkdir()
        r, sv = make(tmp_path / case)
        fr(r, zs, arm, stiff(0.0))
        tick(r, sv)
        assert (sv.mode == "fight") is (case == "well"), case


def test_wounded_under_strain_soft_shoves_at_point_blank_as_p24_ag(tmp_path):
    """armPain 15 (STRAIN_SOFT to STRAIN_HARD): neither the hold nor `wounded`; the point-blank shove (P24-AG)."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 100.8)], 15.0, stiff(0.0))
    assert tick(r, sv).type == "shove" and "pain" not in threat_why(tmp_path) and not sv.strain_hold


def test_the_threat_module_names_the_rule():
    assert hasattr(T.Threat, "_lone")


# ================================================================ P24-AU: the listing-edge flip
E10 = "e_day_10-20261030-084253"


def edge_rig(tmp_path, edge=True):
    """A pull: the chaser 1 at 7 tiles east, the idle zombie 2 at 11.5 (within LISTED_R, beyond DANGER_R): the first
    leg pulls west, accepted; `edge` False is the rule before P24-AU (`Survive.EDGE`)."""
    from .test_survive_o import zd
    r, sv = make(tmp_path)
    sv.EDGE = edge
    r.frame(zombies=[zd(1, 107.0, 200.0), zd(2, 111.5, 200.5, has_target=False)])
    leg = tick(r, sv)
    assert leg.type == "aim" and threat_why(tmp_path)["leg"] == "pull"
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    return r, sv, leg


def unlisted(r, x):
    """The next frame: the player at `x` (walked west by the pull), the chaser at 6.6 tiles, zombie 2 no longer in the
    frame (the World keeps it at its last square, now past LISTED_R)."""
    from .test_survive_o import zd
    r.frame(x=x, zombies=[zd(1, x + 6.6, 200.0, me=(x, 200.0))])


def test_the_edge_hold_constants():
    """Six planner ticks: 3 s at the drivers' PLANNER_HZ 2 (`driverlib.day`); the edge is the listing's, AIM_R's too."""
    assert P.EDGE_HOLD_TICKS == 6 and P.LISTED_R == P.AIM_R == 12.0 and S.Survive.EDGE is True


def test_a_zombie_leaving_the_listing_holds_the_pull_for_edge_hold_ticks(tmp_path):
    """E10's run 4 (lines 234-245: seek, pull, seek, pull, seek, pull, seek, each aim superseded by the next): the
    group zombie at the 12-tile edge decided the leg each tick. Zombie 2 leaves the listing (12.1 tiles): the pull leg
    is held, its group read at the zombie's last listed square, for EDGE_HOLD_TICKS ticks (logged `edge`); on the
    seventh tick unlisted it is lost as before and the seek leg goes."""
    r, sv, leg = edge_rig(tmp_path)
    for k in range(P.EDGE_HOLD_TICKS):
        unlisted(r, 99.4)
        assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == leg.aid, k
        assert 2 in sv.fight.edge
    unlisted(r, 99.4)
    a = tick(r, sv)
    assert a.type == "aim" and threat_why(tmp_path)["leg"] == "seek" and 2 not in sv.fight.edge


def test_without_the_edge_hold_the_leg_flips_on_the_first_tick_unlisted(tmp_path):
    r, sv, leg = edge_rig(tmp_path, edge=False)
    unlisted(r, 99.4)
    a = tick(r, sv)
    assert a.type == "aim" and threat_why(tmp_path)["leg"] == "seek" and not sv.fight.edge


def test_a_zombie_back_in_the_listing_ends_its_edge_hold(tmp_path):
    """Back within LISTED_R the zombie reads as listed again (its own square), its hold ended."""
    from .test_survive_o import zd
    r, sv, leg = edge_rig(tmp_path)
    unlisted(r, 99.4)
    tick(r, sv)
    assert 2 in sv.fight.edge
    r.frame(x=99.4, zombies=[zd(1, 106.0, 200.0, me=(99.4, 200.0)), zd(2, 111.0, 200.5, has_target=False,
                                                                        me=(99.4, 200.0))])
    assert tick(r, sv) is None and not sv.fight.edge and threat_why(tmp_path)["holding"] == leg.aid


def test_pull_from_reads_an_edge_held_zombie_at_its_last_listed_square(tmp_path):
    """`policies.pull_from`'s `edge`: an unlisted zombie (here at 30 tiles) held at its listed square counts in the group,
    whatever the World now holds of it; within DANGER_R there it refuses the pull as a listed one does."""
    from .test_policies import Rig
    from .test_survive_o import zd
    r = Rig(tmp_path)
    r.frame(zombies=[zd(1, 107.0, 200.0), zd(2, 130.0, 200.0, has_target=False)])
    t = (1, r.world.zombies[1], 7.0)
    assert P.pull_from(r.world, t) is None
    assert P.pull_from(r.world, t, edge={2: {"x": 111.5, "y": 200.5}}) == pytest.approx((111.5, 200.5))
    assert P.pull_from(r.world, t, edge={2: {"x": 104.0, "y": 200.0}}) is None


def test_e10_run_4_holds_the_pull_where_the_record_flipped():
    """E10 replayed at HEAD (open loop past the first divergence: the record's frames follow its own legs): from line
    234 to 245 the record sent seven aims, the leg flipping between the seek and the pull each one; with the edge hold
    no seek leg follows a pull leg within EDGE_HOLD_TICKS ticks, so fewer aims go there; with EDGE off the replay is the
    record's seven, the flip reproduced."""
    got, off = e10_lines(), e10_lines(("EDGE",))

    def legs(g):
        return [(k, g[k]["why"].get("leg")) for k in range(234, 246) if k in g and g[k]["action"]
                and g[k]["action"]["type"] == "aim"]
    assert [leg for _, leg in legs(off)] == ["seek", "pull", "seek", "pull", "seek", "pull", "seek"]
    flips = [(a, b) for (a, la), (b, lb) in zip(legs(got), legs(got)[1:]) if la == "pull" and lb == "seek"]
    assert all(b - a > P.EDGE_HOLD_TICKS for a, b in flips) and len(legs(got)) < 7


@functools.lru_cache(maxsize=8)
def _e10(off=()):
    import os
    from agent.base import replay_decisions as R

    def m(sv):
        for k in off:
            setattr(sv, k, False)
    return json.dumps(R.decisions(R.replay(os.path.join(R.ARTIFACTS, E10), mutate=m)))


def e10_lines(off=()):
    """{line: decision} of E10's decision log replayed at HEAD (open loop past the first divergence), `off` off."""
    return {d["line"]: d for d in json.loads(_e10(tuple(off)))}


# ================================================================ P24-AV: the stomp on the first fallen frame
def knock_fight(tmp_path):
    """A Fight at armPain 12 (the shove preferred at point blank) whose shove at zombie 1 (0.8 tiles) read
    `knockdown` true, the frame not yet reading it on the floor."""
    from .test_survive_m import fight
    from .test_survive_m import fr as mfr
    from .test_survive_m import z as mz
    zs = [mz(1, 100.8)]
    r, f = fight(tmp_path, zs, arm=12.0)
    assert f.step().type == "shove"
    r.answer({"state": "done", "result": {"knockdown": True, "attackStarted": True, "targetDead": False}})
    return r, f, mfr, mz


def test_a_knocked_down_target_is_stomped_on_the_first_frame_that_reads_it_fallen_never_before(tmp_path):
    """E10's a59: the stomp sent on the shove's `knockdown` before any frame read the target `onFloor` was rejected
    `not valid`. The Fight now holds (no send, why `knocked`) while the knock-down is unread on the frame, and stomps
    on the first frame whose `onFloor` reads true."""
    r, f, mfr, mz = knock_fight(tmp_path)
    mfr(r, [mz(1, 100.8)], 12.0)
    assert f.step() is None and f.why["knocked"] == 1
    mfr(r, [mz(1, 100.8, floor=True)], 12.0)
    a = f.step()
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and f.why["downed"] == 1


def test_a_knock_down_never_read_on_the_floor_ends_its_hold_after_knock_read_s(tmp_path):
    """Past KNOCK_READ_S with no frame reading it fallen the zombie is read standing again: the shove."""
    r, f, mfr, mz = knock_fight(tmp_path)
    mfr(r, [mz(1, 100.8)], 12.0)
    assert f.step() is None and f.why["knocked"] == 1                   # the knock-down read: waited on
    r.advance(P.KNOCK_READ_S + 0.1)
    mfr(r, [mz(1, 100.8)], 12.0)
    assert f.step().type == "shove" and "knocked" not in f.why


def test_a_stomp_failed_stood_reads_the_target_again_one_more_stomp_then_the_floor_strike(tmp_path):
    """`stood`: the target rose before the stomp landed. Standing on the next frame: the Fight's own path (the shove
    at point blank at armPain 12); fallen again: one more stomp; that one `stood` too: the floor strike."""
    from .test_survive_m import fight
    from .test_survive_m import fr as mfr
    from .test_survive_m import z as mz
    r, f = fight(tmp_path, [mz(1, 100.8, floor=True)], arm=12.0)
    assert f.step().type == "stomp"
    r.answer({"state": "failed", "reason": "stood"})
    mfr(r, [mz(1, 100.8)], 12.0)
    assert f.step().type == "shove"                                      # standing: the Fight's shove
    r.answer({"state": "done", "result": {"knockdown": False, "attackStarted": True, "targetDead": False}})
    mfr(r, [mz(1, 100.8, floor=True)], 12.0)
    assert f.step().type == "stomp"                                      # fallen again: one more stomp
    r.answer({"state": "failed", "reason": "stood"})
    mfr(r, [mz(1, 100.8, floor=True)], 12.0)
    a = f.step()
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and f.why["floor"] is True


def chaser_by(tmp_path, target_x, chaser, caps=None):
    """A `many` flee (three chasers listed beyond DANGER_R) after the Fight struck zombie 1, now fallen at `target_x`;
    `chaser` a fourth zombie record (or None)."""
    from .test_survive_q import GROUP3, struck
    r, sv = struck(tmp_path)
    zs = [z(1, target_x, floor=True)] + GROUP3 + ([chaser] if chaser else [])
    fr(r, zs)
    return r, sv, tick(r, sv)


def test_e9_s_line_334_geometry_a_chaser_within_keep_r_of_the_target_refuses_the_finish(tmp_path):
    """The deferred minor 5 of review-t32-fix1 (E9's line 334: 7474 fallen 4.62 tiles off, 7479 standing and chasing
    2.16 tiles from it, 1.97 beyond it along y, 6.49 from the player; here 1.96 from the target): the 4.6-tile stomp
    walk would end at the chaser; the finish is refused (logged `finish_block`) and the flee runs. An idle zombie
    there refuses nothing. E9's own line: `test_survive_q.test_e9_s_7474_at_line_334_is_refused_for_7479_by_it`."""
    r, sv, a = chaser_by(tmp_path, 104.62, z(5, 106.49, 200.6))
    w = threat_why(tmp_path)
    assert a.type == "steer" and "finish" not in w and w["flee"] == "many"
    assert w["finish_block"] == {"target": 1, "chaser": 5, "dist": pytest.approx(1.96, abs=0.01)}
    (tmp_path / "idle").mkdir()
    r2, sv2, a2 = chaser_by(tmp_path / "idle", 104.62, z(5, 106.49, 200.6, has_target=False))
    assert (a2.type, a2.args) == ("stomp", {"targetId": 1})


def test_a_fallen_target_with_the_nearest_standing_four_tiles_off_it_is_finished(tmp_path):
    """The nearest standing chaser 4 tiles beyond the fallen target (7 from the player, beyond DANGER_R and KEEP_R of
    the target): the stomp goes."""
    r, sv, a = chaser_by(tmp_path, 103.0, z(5, 107.0, 200.0))
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and "finish_block" not in threat_why(tmp_path)


def test_the_flee_s_finish_stomps_once_more_after_stood_then_strikes_the_floor(tmp_path):
    """P24-AV in the flee's finish (P24-AQ): its stomp failed `stood` and the target lies again: one more stomp
    (`kind` "stomp2"); that one `stood` too: the floor strike (within FIGHT_REACH)."""
    from .test_survive_q import GROUP3, struck
    r, sv = struck(tmp_path)
    zs = [z(1, 101.5, floor=True)] + GROUP3
    fr(r, zs)
    assert tick(r, sv).type == "stomp"
    r.answer({"state": "failed", "reason": "stood"})
    fr(r, zs)
    a = tick(r, sv)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and threat_why(tmp_path)["kind"] == "stomp2"
    r.answer({"state": "failed", "reason": "stood"})
    fr(r, zs)
    a = tick(r, sv)
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and threat_why(tmp_path)["kind"] == "floor"


def test_the_flee_s_finish_spent_after_a_stomp_that_went(tmp_path):
    """A stomp that went (done, started) spends the finish: the steer follows, as P24-AQ."""
    from .test_survive_q import GROUP3, struck
    r, sv = struck(tmp_path)
    zs = [z(1, 101.5, floor=True)] + GROUP3
    fr(r, zs)
    assert tick(r, sv).type == "stomp"
    r.answer({"state": "done", "result": {"hit": True, "attackStarted": True, "targetDead": False}})
    fr(r, zs)
    assert tick(r, sv).type == "steer"


# ================================================================ P24-AW: the fill from a loaded source
def fill_rig(tmp_path, sources, width=None, x=100.0):
    """A thirsty Survive holding one empty vessel (5) with `sources` scanned (each (x, y)), the frame's
    `me.loadedWidth` `width` (None: never read), the player at (`x`, 200)."""
    from .test_survive_g import hold, source
    r, sv = make(tmp_path)
    r.scan([source(sx, sy) for sx, sy in sources])
    r.frame(x=x)
    if width is not None:
        r.world.loaded_width = width   # as the World keeps the last frame's `me.loadedWidth` (PZA/1.7)
    hold(r, 5, "Base.PopEmpty", use="container")
    r.frame(x=x, thirst=0.2)
    if width is not None:
        r.world.loaded_width = width
    return r, sv


def need_why(tmp_path):
    return last(tmp_path)["inputs"]["branches"]["need"]


def test_the_fill_constants():
    """FILL_WALK_R 20 (the ruling's) and FILL_NEAR_R 2; the loaded grid is the goal legs' (P24-AI, `goals.leg_max`:
    40 tiles at a width of 104, #4375)."""
    from agent.base.planner import goals as G
    from agent.base.planner import water as W
    assert (W.FILL_WALK_R, W.FILL_NEAR_R) == (20.0, 2.0)
    assert G.leg_max(type("Wd", (), {"loaded_width": 104})()) == 40.0


def test_a_source_within_fill_walk_r_is_filled_as_before(tmp_path):
    r, sv = fill_rig(tmp_path, [(118, 200)], width=104)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 118, "y": 200}) and need_why(tmp_path)["fill"]["dist"] == pytest.approx(18.5, abs=0.01)


def test_a_loaded_source_beyond_fill_walk_r_takes_a_walk_beside_it_first_then_the_fill(tmp_path):
    """A source 30.5 tiles off, inside the loaded grid (40 at width 104): a walk at a walk to the open square beside it
    nearest the player (ties by x, then y: (129, 199)), why `fill` `walk`, held while it runs; done there, the fill."""
    r, sv = fill_rig(tmp_path, [(130, 200)], width=104)
    r.scan([square(x, y) for x in (129, 130, 131) for y in (199, 200, 201) if (x, y) != (130, 200)])
    r.frame(thirst=0.2)
    r.world.loaded_width = 104
    a = tick(r, sv)
    w = need_why(tmp_path)["fill"]
    assert (a.type, a.args) == ("walkTo", {"x": 129.5, "y": 199.5, "gait": "walk"}) and w["walk"] == [129, 199]
    assert w["source"] == [130, 200] and last(tmp_path)["branch"] == "need"
    r.fake.answer({"walkTo": ["accepted"]})
    r.pump()
    r.frame(thirst=0.2)
    assert tick(r, sv) is None                                            # the walk is the need's: held
    r.answer()
    r.frame(x=129.5, y=200.5, thirst=0.2)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 130, "y": 200})
    all_sends_valid(r)


@pytest.mark.parametrize("width,sources", [(104, [(160, 200)]), (104, [(141, 200)]), (None, [(160, 200)])])
def test_a_source_beyond_the_loaded_grid_is_never_sent(tmp_path, width, sources):
    """E10: 55 fills rejected `no source`, sent 60.04 to 159.03 tiles off. A source beyond the loaded grid (`leg_max`:
    40 at width 104; LEG_MAX 40 with no width read) takes no fill and no walk: the want names `water_source`, logged
    `unloaded` (the known clean sources out of the grid)."""
    r, sv = fill_rig(tmp_path, sources, width=width)
    for _ in range(3):
        tick(r, sv)
        r.frame(thirst=0.2)
        if width is not None:
            r.world.loaded_width = width
    assert not any(a.type in ("fill", "walkTo") for a in r.acts.history)
    w = need_why(tmp_path)["fill"]
    assert w["want"] == "water_source" and w["unloaded"] == 1 and "water_source" in sv.need_marks


def test_the_nearest_loaded_source_is_taken_over_a_nearer_one_out_of_the_grid_on_the_other_axis(tmp_path):
    """The grid is square (Chebyshev, the chunk grid of #4375): a source 41 tiles north (out) is passed for one 30
    tiles east and 30 south (in, 42.4 by the crow): the walk goes to the loaded one."""
    r, sv = fill_rig(tmp_path, [(100, 159), (130, 230)], width=104)
    tick(r, sv)
    w = need_why(tmp_path)["fill"]
    assert w["source"] == [130, 230] and "walk" in w


def test_a_failed_walk_to_a_source_leaves_it_out(tmp_path):
    """The walk failed (`no path`): the source is left out as a fill's walk failure leaves it (SOURCE_RETRY_MIN), so
    the need does not walk at it again at once."""
    r, sv = fill_rig(tmp_path, [(130, 200)], width=104)
    tick(r, sv)
    assert r.cmd()[0] == "walkTo"
    r.answer({"state": "failed", "reason": "no path"})
    r.frame(thirst=0.2)
    r.world.loaded_width = 104
    tick(r, sv)
    assert r.world.dry_now() == {(130, 200, 0)} and sum(a.type == "walkTo" for a in r.acts.history) == 1
