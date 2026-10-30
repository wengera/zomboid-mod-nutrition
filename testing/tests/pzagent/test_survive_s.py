"""Survival 13 (survival iteration 12; Plan 24 Task 36; E10, `e_day_10-20261030-084253`: zero kills to the day cap,
the arms' hold set by a bite's pain at game minute 605 and never released, the seek and the pull flipping at the
12-tile listing edge, the finishing stomp refused `not valid` before the frames read the target fallen, 55 fills
rejected `no source` 60 to 159 tiles off, the doorway stand never taken). The fake mod over PZA/1.7.

- P24-AT: the arms' hold reads `body.strain` (the stiffness, #4369), set at STIFF_HARD on either arm and released under
  STIFF_SOFT; the arm pain (#4370's divider) is its own reason, `wounded`: no swing at STRAIN_HARD, a lone target still
  sought, groups fled as today.
- P24-AU: a zombie that leaves the listing (beyond LISTED_R, AIM_R's 12) is held in the seek's and the pull's reads
  at its last listed square for EDGE_HOLD_TICKS planner ticks, so a leg is not superseded by the edge's flip.
"""
import functools
import json

import pytest

from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .test_policies import all_sends_valid
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
