"""Plan 34 Task 3c fix 1 (the fix arm at 24a35f2b on the `agent` fixture with the model, P31-T, not evidence; the rows
in `testing/trials/trials.md`): three trials, three deaths, `x_trial-ladder-20261109-141434`,
`x_trial-ladder-20261109-142025` and `x_trial-ladder-20261109-142418`.

- RETREAT_REGAIN's press held (`fight.Fight._regain_busy`): the second trial's lines 114 to 118 sent the press at 6883,
  then at 6854, then at 6855 on three lines, each a retreat re-pin (`_retreat_read`) that cut the running melee, the
  first with its shove in flight (line 116 `shove`, line 117 a new melee), so no press finished and no back leg went
  between them; the first trial's lines 265 and 266 the same (13836, then 13802 0.44 s on). The press's own melee now
  holds by the melee's rule alone (`dispatch.FightDispatch._melee_holds`) until it has pressed once with no press in
  flight; then the back leg as before (lines 91 to 94 and 107 to 108 of the second trial read the back leg live).
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
from .test_survive_ak import WEST_V, closing
from .test_survive_an import accept
from .test_survive_ap import frame, pressed, progress


def test_the_constant():
    """POINT_BLANK_OVER_R 1.5, inside KEEP_R."""
    assert P.POINT_BLANK_OVER_R == 1.5 and P.POINT_BLANK_OVER_R < P.KEEP_R


# ================================================================ (A) the press once, then the back leg
ONE_PRESS = ((0.78, 0.0), (3.0, 0.5), (3.5, -0.5))   # the first trial's line 263: 13802 at 0.78, one within reach
ONE_NEXT = ((0.66, 0.0), (2.9, 0.5), (3.4, -0.5))


def test_a_strike_press_that_pressed_once_gives_way_to_the_back_leg(tmp_path):
    """The first trial's line 263 as a fixture (unspent, one in reach: the press is the strike melee): while its swing
    is in flight it holds; once its act lines read the press resolved (`face`) the next choose reads `busy` False and
    sends the back leg on the retreat heading, logged `retreat_regain` {phase "back", near, since 0}."""
    r, f, a = pressed(tmp_path, spent=(), offs=ONE_PRESS)
    assert (a.type, a.args["mode"]) == ("melee", "strike") and f.why["retreat_regain"]["phase"] == "press"
    accept(r, a, "swing")
    frame(r, f, ONE_NEXT)
    assert f.busy() is True and f.step() is None
    progress(r, a, "face")
    frame(r, f, ONE_NEXT)
    assert f.busy() is False
    b = f.step()
    assert b.type == "aim" and (b.args["vx"], b.args["vy"]) == pytest.approx(WEST_V)
    g = f.why["retreat_regain"]
    assert g["phase"] == "back" and g["near"] == pytest.approx(0.66) and g["since"] == pytest.approx(0.0)


PRESS_AT_1 = ((0.6, 0.0), (1.4, 0.3), (3.0, 0.5))   # the press at 1 (two in reach: the shove form)
REPINNED = ((0.9, 0.0), (0.4, 0.1), (3.0, 0.5))     # 2 come 0.49 tiles nearer than 1: the retreat's re-pin reads 2


def test_a_press_in_flight_is_not_cut_by_the_retreat_s_re_pin(tmp_path):
    """The second trial's lines 115 to 117: the press's melee at 1 with its shove in flight, 2 come nearer than 1 by more
    than PAIR_SWITCH_R (the retreat's re-pin): it holds; its press resolved, the back leg goes, no melee at 2."""
    r, f, a = pressed(tmp_path, spent=(), offs=PRESS_AT_1)
    assert (a.type, a.args["targetId"], a.args["mode"]) == ("melee", 1, "shove")
    accept(r, a, "shove")
    frame(r, f, REPINNED)
    assert f.busy() is True and f.step() is None
    progress(r, a, "face")
    frame(r, f, REPINNED)
    assert f.busy() is False
    b = f.step()
    assert b.type == "aim" and f.why["retreat_regain"]["phase"] == "back"


def test_a_press_not_yet_begun_is_not_cut_by_the_retreat_s_re_pin(tmp_path):
    """The second trial's lines 117 and 118 (6854's press re-pinned to 6855 0.54 s on, before any press step): the
    press's melee accepted, no step yet, the re-pin read: it holds (no new press at 2)."""
    r, f, a = pressed(tmp_path, spent=(), offs=PRESS_AT_1)
    accept(r, a)
    frame(r, f, REPINNED)
    assert f.busy() is True and f.step() is None


def test_with_retreat_regain_off_the_re_pin_cuts_the_melee(tmp_path):
    """A pin (`retreat_regain` off, the rule before it): the re-pin gives the running melee way."""
    r, f, a = pressed(tmp_path, rule=False, spent=(), offs=PRESS_AT_1)
    accept(r, a, "shove")
    frame(r, f, REPINNED)
    assert f.busy() is False


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
