"""Survival 13 (survival iteration 12; Plan 24 Task 36; E10, `e_day_10-20261030-084253`: zero kills to the day cap,
the arms' hold set by a bite's pain at game minute 605 and never released, the seek and the pull flipping at the
12-tile listing edge, the finishing stomp refused `not valid` before the frames read the target fallen, 55 fills
rejected `no source` 60 to 159 tiles off, the doorway stand never taken). The fake mod over PZA/1.7.

- P24-AT: the arms' hold reads `body.strain` (the stiffness, #4369), set at STIFF_HARD on either arm and released under
  STIFF_SOFT; the arm pain (#4370's divider) is its own reason, `wounded`: no swing at STRAIN_HARD, a lone target still
  sought, groups fled as today.
"""
import pytest

from agent.base.planner import policies as P
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
