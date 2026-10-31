"""Survival 17 (survival iteration 15; Plan 25 Task 10; F5, `f_goals_6-20261030-192251`, rows #4452-#4460). The fake
mod over PZA/1.7.1.

- P25-P, the unarmed fight: with no weapon held, one zombie within DANGER_R and the health at or above
  FLEE_HEALTH_PAIR, the Fight runs (the stance, the shove at point blank logged `shove` "unarmed", the stomp of the
  fallen), never an `attack`, logged `unarmed_fight`; two within DANGER_R, or the health under FLEE_HEALTH_PAIR, flee
  `unarmed` as before; the doorway stand stays armed-only; the trapped fight takes the unarmed character too.
"""
import pytest

from agent.base.planner import doorway as D
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .test_survive import closed_room, make, sheltered, shelter_world, threat_why, tick
from .test_survive_p import POST, stood
from .test_survive_p import z as dz
from .test_survive_p import why as door_why
from .test_survive_q import z
from .test_survive_t import DOWN, MISS


def test_the_iteration_15_switches():
    assert S.T5_SWITCHES == ("UNARMED_FIGHT",)
    for name in S.T5_SWITCHES:
        assert getattr(S.Survive, name) is True, name
    assert not set(S.T5_SWITCHES) & (set(S.T4_SWITCHES) | set(T.T3_SWITCHES))
    assert (P.FLEE_HEALTH_PAIR, P.POINT_BLANK_R, P.DANGER_R, P.FIGHT_REACH) == (60.0, 1.0, 6.0, 2.0)


def sends(r):
    return [a.type for a in r.acts.history]


def lone(r, x, floor=False, **k):
    """One zombie east of the player at `x` (the player at 100, 200), no weapon held."""
    r.frame(zombies=[z(1, x, floor=floor)], weapon=None, **k)


# ================================================================ P25-P: the unarmed fight
def test_unarmed_one_zombie_is_fought_from_the_stance_shoved_at_point_blank_and_stomped_never_swung_at(tmp_path):
    """F5 (27 fights, every one fled `unarmed`): one zombie 4 tiles off, no weapon, health 100: the Fight's stance (an
    `aim`, never sought: the unarmed Fight closes on nothing), logged `unarmed_fight`; at 1.6 tiles (in reach, beyond
    point blank) the backpedal, never an attack; at 0.8 the shove, logged `shove` "unarmed"; its knock-down read, the
    fallen zombie is stomped."""
    r, sv = make(tmp_path)
    lone(r, 104.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "aim" and w["fight"] is True and w["unarmed_fight"] is True and "flee" not in w
    assert w["leg"] == "stand" and not w.get("seek") and sv.fight.unarmed is True
    r.advance(0.5)
    lone(r, 101.6)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "aim" and w["leg"] == "back" and a.args["vx"] < -0.9 and w["unarmed_fight"] is True
    r.advance(0.5)
    lone(r, 100.8)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("shove", {"targetId": 1}) and w["shove"] == "unarmed" and w["unarmed_fight"] is True
    r.fake.answer({"shove": ["accepted", DOWN]})
    r.pump()
    r.advance(0.5)
    lone(r, 101.2, floor=True)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and w["downed"] == 1 and w["unarmed_fight"] is True
    assert "attack" not in sends(r)


def test_unarmed_a_missed_shove_is_shoved_again_never_the_corner_s_swing(tmp_path):
    """P25-A's corner after a missed shove swings an undivided weapon; unarmed there is none: the lone target is shoved
    again (the corner's `shove` kind), never an attack."""
    r, sv = make(tmp_path)
    lone(r, 100.8)
    assert tick(r, sv).type == "shove"
    r.fake.answer({"shove": ["accepted", MISS]})
    r.pump()
    r.advance(0.5)
    lone(r, 100.8)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert "attack" not in sends(r) and w["corner"]["kind"] == "shove"


def test_unarmed_a_second_zombie_within_danger_r_is_fled_unarmed(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 100.8), z(2, 100.0, 205.0)], weapon=None)
    a = tick(r, sv)
    assert a.type == "steer" and threat_why(tmp_path)["flee"] == "unarmed" and "unarmed_fight" not in threat_why(tmp_path)


@pytest.mark.parametrize("health, fights", [(59.0, False), (60.0, True)])
def test_unarmed_under_flee_health_pair_the_lone_zombie_is_fled(tmp_path, health, fights):
    r, sv = make(tmp_path)
    lone(r, 100.8, health=health)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    if fights:
        assert a.type == "shove" and w["unarmed_fight"] is True
    else:
        assert a.type == "steer" and w["flee"] == "unarmed"


def test_unarmed_on_a_build_without_the_shove_the_lone_zombie_is_fled(tmp_path):
    """The unarmed fight is the shove's: a build that does not announce it flees as before."""
    from .test_policies import CAPS_14
    r, sv = make(tmp_path, caps=tuple(c for c in CAPS_14 if c != "shove"))
    lone(r, 100.8)
    a = tick(r, sv)
    assert a.type == "steer" and threat_why(tmp_path)["flee"] == "unarmed"


def test_with_unarmed_fight_off_the_lone_zombie_is_fled_as_before(tmp_path):
    r, sv = make(tmp_path)
    sv.UNARMED_FIGHT = False
    lone(r, 100.8)
    a = tick(r, sv)
    assert a.type == "steer" and threat_why(tmp_path)["flee"] == "unarmed"


TRAP_ME = (102.5, 202.5)   # the closed room's centre (`test_survive.closed_room`: no door, no opening)


def trap(tmp_path, zs, **k):
    r, sv = make(tmp_path)
    r.scan(closed_room())
    r.frame(x=TRAP_ME[0], y=TRAP_ME[1], zombies=zs, weapon=None, **k)
    return r, sv


def test_trapped_on_a_room_square_the_lone_zombie_in_reach_is_shoved_not_the_trapped_hold(tmp_path):
    """F5's trapped stand (110 s, nothing sent under one zombie's bite runs): one zombie at 0.8 tiles in the closed
    room: the shove; with the switch off, the trapped hold as before."""
    zs = [z(1, 103.3, 202.5)]
    r, sv = trap(tmp_path, zs)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("shove", {"targetId": 1}) and w["shove"] == "unarmed" and "trapped" not in w
    (tmp_path / "off").mkdir()
    r2, sv2 = trap(tmp_path / "off", zs)
    sv2.UNARMED_FIGHT = False
    assert tick(r2, sv2) is None and threat_why(tmp_path / "off")["trapped"] == 2


def sheltered_open(tmp_path):
    """Unarmed in the shelter (`test_survive.sheltered`), its door then read open: (rig, survive, the player)."""
    from .test_night import OPEN
    r, sv = make(tmp_path)
    me = sheltered(r, sv, weapon=None)
    shelter_world(r, OPEN)
    return r, sv, me


def test_the_sheltered_trapped_flee_s_lone_zombie_in_the_doorway_takes_the_trapped_fight(tmp_path):
    """F5's order (`sheltered`, the door open, no way out): unarmed in the shelter, one zombie in the doorway 1.0 tile
    off, nobody else within DANGER_R: the first tick drops the shelter plan and holds `trapped` (the care tried); the
    next, trapped, `_trapped_fight` makes the Fight, which shoves it (before: the trapped hold on every tick)."""
    r, sv, me = sheltered_open(tmp_path)
    r.frame(x=me[0], y=me[1], zombies=[z(1, 112.5, 201.5)], weapon=None)
    assert tick(r, sv) is None and threat_why(tmp_path)["trapped"] == 1
    r.frame(x=me[0], y=me[1], zombies=[z(1, 112.5, 201.5)], weapon=None)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("shove", {"targetId": 1}) and w["unarmed_fight"] is True and "trapped" not in w
    (tmp_path / "off").mkdir()
    r2, sv2, me2 = sheltered_open(tmp_path / "off")
    sv2.UNARMED_FIGHT = False
    for _ in range(2):
        r2.frame(x=me2[0], y=me2[1], zombies=[z(1, 112.5, 201.5)], weapon=None)
        assert tick(r2, sv2) is None and threat_why(tmp_path / "off")["trapped"] == 1


def test_the_unarmed_trapped_fight_takes_a_zombie_within_fight_reach_only(tmp_path):
    """`_trapped_fight` (the flee rows' trapped fight) takes the unarmed character only with a reachable zombie within
    FIGHT_REACH (the shove's side of the room): read on the trapped tick after the re-close failed, one zombie 1.0
    tile off is fought and one 2.5 tiles off is not; a second within DANGER_R or the health under FLEE_HEALTH_PAIR
    neither."""
    r, sv, me = sheltered_open(tmp_path)
    for _ in range(2):
        r.frame(x=me[0], y=me[1], zombies=[z(1, 112.5, 203.0)], weapon=None)
        if tick(r, sv) is not None:
            r.answer({"state": "failed", "reason": "blocked"})
    assert threat_why(tmp_path)["trapped"] == 1

    def read(zs, health=100.0):
        r.frame(x=me[0], y=me[1], zombies=zs, weapon=None, health=health)
        return sv._trapped_fight(sv._within(P.DANGER_R), True)

    assert read([z(1, 112.5, 203.0)]) is None
    assert read([z(1, 112.5, 201.5)]) == ("fight", None)
    assert read([z(1, 112.5, 201.5), z(4, 109.5, 200.5)]) is None
    assert read([z(1, 112.5, 201.5)], health=59.0) is None


def test_the_doorway_stand_still_ends_unarmed(tmp_path):
    """The stand's post needs the swing's reach: unarmed, it ends `unarmed` as before, though one zombie alone is near."""
    r, sv = stood(tmp_path)
    r.frame(x=POST[0], y=POST[1], zombies=[dz(1, 111.3, 201.5)], weapon=None)
    tick(r, sv)
    assert door_why(r)["doorway_left"] == "unarmed" and not isinstance(sv.fight, D.Doorway)


def test_the_many_flee_s_finish_sends_no_floor_strike_unarmed(tmp_path):
    """The `many` flee's finish (P24-AQ) never swings the floor strike unarmed (`_unarmed`): a struck zombie fallen
    beside a standing one inside STAND_MIN_R refuses the stomp, and unarmed the floor strike is not taken."""
    r, sv = make(tmp_path)
    sv.struck[1] = r.clock()
    sv.flee_many, sv.mode = True, "flee"
    r.frame(zombies=[z(1, 101.0, floor=True)], weapon=None)
    sv.flee = None
    r.world.hello["caps"] = [c for c in r.world.hello["caps"] if c != "stomp"]
    assert sv._unarmed() is True
    assert sv._flee_finish("many") is None and sv.finishing.get(1) == "floor"
