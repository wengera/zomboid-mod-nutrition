"""Plan 34 Task 3c fix 1 (the fix arm at 24a35f2b on the `agent` fixture with the model, P31-T, not evidence; the rows
in `testing/trials/trials.md`): three trials, three deaths, `x_trial-ladder-20261109-141434`,
`x_trial-ladder-20261109-142025` and `x_trial-ladder-20261109-142418`.

- RETREAT_REGAIN's press held: Plan 35 Task 8 deleted RETREAT_REGAIN and its tests (named in the task report).
- SPENT_LEAVE's read (`group.ThreatGroup._spent_meet`): the second trial's lines 119 and 120 read `strain` 47.2 and the
  maneuver's `spent` true (the Lua's spent meet: `PZAgent_StanceMelee.lua`'s `spentOf`, the arms' pain over
  K.MELEE_SPENT_PAIN 10) with `group_leave` {leg "retreat", n 4}: the read took only the holds and the shove-and-stomp
  Fight, never the arms' pain. It now also reads the pain over STRAIN_SOFT (the Lua's threshold).
- POINT_BLANK_FIGHT's radius over a flee (`threat.Threat._point_blank`): the third trial's line 343 pinned 8836 at 2.455
  tiles over the `health` flee and line 358 8847 at 2.18, and the first trial's line 392 pinned 13837 at 2.24 over
  `many`; under `many` or `health` the rule now fights only within POINT_BLANK_OVER_R (1.5).

The fixtures are synthetic, built from the trials' numbers, never a replay; the fake mod."""
import pytest

from agent.base.planner import policies as P
from agent.base.planner import threat as T

from .test_policies import zombie
from .test_survive import make, threat_why, tick
from .test_survive_ak import closing


def test_the_constant():
    """POINT_BLANK_OVER_R 1.5, inside KEEP_R."""
    assert P.POINT_BLANK_OVER_R == 1.5 and P.POINT_BLANK_OVER_R < P.KEEP_R


# ================================================================ (B) the spent read is the Lua's
STIFF = {"l": 5.7, "r": 5.7}   # the second trial's line 119: under STIFF_HARD, no arms' hold


@pytest.mark.parametrize("pain, leg", [(47.2, "run"), (15.0, "run"), (9.0, "retreat")])
def test_the_arms_pain_alone_makes_the_meet_spent(tmp_path, pain, leg):
    """The second trial's lines 119 and 120: three closing within GROUP_ENTRY_R, `body.armPain` 47.2 with no hold (the
    stiffness 5.7): the meet is spent (the Lua's `spentOf`: the pain over K.MELEE_SPENT_PAIN 10, STRAIN_SOFT), so the
    leg is the `run`, `group_leave` {leg "run", n 3, spent true}; at 15 (over the Lua's threshold, under STRAIN_HARD)
    the same; at 9 the retreat."""
    closing(tmp_path, wounds={"armPain": pain, "strain": STIFF})
    gl = threat_why(tmp_path)["group_leave"]
    assert gl["leg"] == leg and gl.get("spent", False) is (leg == "run")
    if leg == "run":
        assert gl["n"] == 3


def test_with_spent_leave_off_the_pain_leaves_the_retreat(tmp_path):
    """A pin (SPENT_LEAVE off): the pain 47.2, the retreat."""
    closing(tmp_path, off=("SPENT_LEAVE",), wounds={"armPain": 47.2, "strain": STIFF})
    gl = threat_why(tmp_path)["group_leave"]
    assert gl["leg"] == "retreat" and "spent" not in gl


# ================================================================ (C) point blank over a flee: POINT_BLANK_OVER_R
def rig(tmp_path, zs, health):
    r, sv = make(tmp_path)
    r.frame(zombies=zs, health=health)
    return r, sv


@pytest.mark.parametrize("reason", ["many", "health"])
def test_over_many_or_health_only_a_zombie_within_point_blank_over_r_is_fought(tmp_path, reason):
    """`_point_blank` read directly: under `many` or `health` a standing zombie at 2.2 tiles is no point-blank fight
    (the flee stands); at 1.2 it is."""
    r, sv = rig(tmp_path, [zombie(1, 102.2, 200.0)], 80.0)
    assert sv._point_blank(reason) is None and sv.point_blank_fight is None
    (tmp_path / "near").mkdir()
    r, sv = rig(tmp_path / "near", [zombie(1, 101.2, 200.0)], 80.0)
    assert sv._point_blank(reason) == {"target": 1, "dist": pytest.approx(1.2), "over": reason}


@pytest.mark.parametrize("reason", ["pair", "held", "flip"])
def test_over_the_other_reasons_keep_r_as_before(tmp_path, reason):
    """A pin (the other reasons): a standing zombie at 2.2 tiles is fought, KEEP_R's reach as before."""
    r, sv = rig(tmp_path, [zombie(1, 102.2, 200.0)], 80.0)
    assert sv._point_blank(reason) == {"target": 1, "dist": pytest.approx(2.2), "over": reason}


def test_the_health_flee_with_a_zombie_at_2_2_tiles_flees(tmp_path):
    """The third trial's line 343 on the fake mod: the health at 30 (under FLEE_HEALTH, over FLEE_HEALTH_FLOOR), a
    standing zombie at 2.2 tiles and a second at 4.47: the `health` flee, no `point_blank_fight`; the pair at health 50
    (the `pair` flee) is fought at 2.2 as before."""
    r, sv = rig(tmp_path, [zombie(1, 102.2, 200.0), zombie(2, 100.0, 204.0)], 30.0)
    tick(r, sv)
    why = threat_why(tmp_path)
    assert why.get("flee") == "health" and "point_blank_fight" not in why
    (tmp_path / "pair").mkdir()
    r, sv = rig(tmp_path / "pair", [zombie(1, 102.2, 200.0), zombie(2, 100.0, 204.0)], 50.0)
    tick(r, sv)
    why = threat_why(tmp_path / "pair")
    assert why.get("flee") is None and why["point_blank_fight"]["over"] == "pair"


def test_the_radius_is_the_threat_s_attribute_and_a_seam_restores_keep_r(tmp_path):
    """`threat.Threat.POINT_BLANK_OVER_R` is the constant (no switch); a seam onto the rule before it (a replay's
    `pre_t19`, a pinned test) sets KEEP_R, and `many` at 2.2 tiles is fought again."""
    assert T.Threat.POINT_BLANK_OVER_R == P.POINT_BLANK_OVER_R
    r, sv = rig(tmp_path, [zombie(1, 102.2, 200.0)], 80.0)
    sv.POINT_BLANK_OVER_R = P.KEEP_R
    assert sv._point_blank("many") == {"target": 1, "dist": pytest.approx(2.2), "over": "many"}
