"""Survival 17 (survival iteration 15; Plan 25 Task 10; F5, `f_goals_6-20261030-192251`, rows #4452-#4460). The fake
mod over PZA/1.7.1.

- P25-P, the unarmed fight: with no weapon held, one zombie within DANGER_R and the health at or above
  FLEE_HEALTH_PAIR, the Fight runs (the stance, the shove at point blank logged `shove` "unarmed", the stomp of the
  fallen), never an `attack`, logged `unarmed_fight`; two within DANGER_R, or the health under FLEE_HEALTH_PAIR, flee
  `unarmed` as before; the doorway stand stays armed-only; the trapped fight takes the unarmed character too.
- P25-Q, the trapped hold yields to care: the Flee's trapped hold (no command) passes the tick to the care branch.
- P25-R, the model told what the program will not do unarmed, and an ExploreToward at the view's `toward` accepted.
- P25-S, the low fight: under FLEE_HEALTH, at or above FLEE_HEALTH_FLOOR, one zombie within DANGER_R is fought by the
  shove and the stomp (E13: the health held near 31 from game minute 712, the last 15 fights fled `health`).
- P25-T, the break's misses counted over the Fight's life: SHOVE_BREAK_N misses at one target, whatever their spacing,
  take the break (E13's fight 18: eight shoves 28.5 s apart, the window never read a run).
- The residual of the F5 write-up: on a `1.7` hello the wear pick leaves out a garment an `item_changed` read worn.
"""
import pytest

from agent.base.planner import doorway as D
from agent.base.planner import fight as F
from agent.base.planner import goal_prompt as GP
from agent.base.planner import goals as G
from agent.base.planner import llm as L
from agent.base.planner import policies as P
from agent.base.planner import survive as S

from .test_survive import closed_room, last, make, sheltered, shelter_world, threat_why, tick
from .test_survive_g import care_frame, care_why, hold, part
from .test_survive_j import JACKET, rec
from .test_survive_n import unwear_rig
from .test_survive_p import POST, stood
from .test_survive_p import z as dz
from .test_survive_p import why as door_why
from .test_survive_q import z
from .test_survive_q import fr
from .test_survive_t import DOWN, MISS, NO_STIFF, WOUND, shoved


def test_the_iteration_15_switches():
    assert S.T5_SWITCHES == ("UNARMED_FIGHT", "TRAPPED_CARE", "LOW_FIGHT", "SHOVE_BREAK_RUN")
    assert "shove_break_run" in F.FIGHT_RULES and P.SHOVE_BREAK_N == 3 and P.SHOVE_REPEAT_S == 3.0
    for name in S.T5_SWITCHES:
        assert getattr(S.Survive, name) is True, name
    assert not set(S.T5_SWITCHES) & (set(S.T4_SWITCHES) | set(S.T3_SWITCHES))
    assert (P.FLEE_HEALTH_PAIR, P.POINT_BLANK_R, P.DANGER_R, P.FIGHT_REACH) == (60.0, 1.0, 6.0, 2.0)
    assert (P.FLEE_HEALTH, P.FLEE_HEALTH_FLOOR) == (40.0, 20.0)


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
    fallen zombie is stomped.
    Named change, ruling P28-E (Plan 28 Task 3): pinned with `CIRCLE` off, the rule before it (the straight backpedal
    from a lone zombie, where the leg circles now: `test_survive_ac`)."""
    r, sv = make(tmp_path)
    sv.CIRCLE = False
    lone(r, 104.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "aim" and w["fight"] is True and w["unarmed_fight"] is True and "flee" not in w
    assert w["leg"] == "stand" and not w.get("seek") and sv.fight.shove_only == "unarmed"
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
    w = threat_why(tmp_path)
    assert a.type == "steer" and w["flee"] == "unarmed" and "unarmed_fight" not in w


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


def test_trapped_a_zombie_beyond_fight_reach_inside_the_room_is_met_in_the_stance_never_walked_to(tmp_path):
    """Review-t10 minor 1: unarmed in the closed room, one zombie 2.1 tiles off inside it: the shove-only Fight takes
    the stance (the aim) and sends no walk nor steer toward the zombie on any tick; at point blank, the shove."""
    r, sv = trap(tmp_path, [z(1, 104.6, 202.5)])
    seen = []
    for _ in range(3):
        a = tick(r, sv)
        seen.append(a.type if a is not None else None)
        r.frame(x=TRAP_ME[0], y=TRAP_ME[1], zombies=[z(1, 104.6, 202.5)], weapon=None)
    assert not {"walkTo", "steer"} & set(seen) and "aim" in seen
    assert threat_why(tmp_path)["unarmed_fight"] is True
    r.frame(x=TRAP_ME[0], y=TRAP_ME[1], zombies=[z(1, 103.3, 202.5)], weapon=None)
    a = tick(r, sv)
    assert (a.type, a.args) == ("shove", {"targetId": 1})


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
    """The stand's post needs the swing's reach: unarmed, it ends `unarmed` as before, one zombie alone near."""
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


# ================================================================ P25-Q: the trapped hold yields to care
TWO_IN = [z(1, 100.5, 202.5), z(2, 102.5, 200.5)]   # two zombies 2 tiles off in the closed room: the unarmed flee


def test_trapped_a_bleeding_part_is_bandaged_with_the_held_bandage(tmp_path, monkeypatch):
    """F5: five parts bleeding, a bandage and four rags held, 215 `trapped` lines sending nothing: the trapped hold
    passes the tick to the care, which bandages the bleeding part (no ride); the threat's why keeps `trapped`.
    Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
    r, sv = make(tmp_path)
    r.scan(closed_room())
    hold(r, 501, "Base.Bandage")
    care_frame(r, [part(9, bleeding=True, bleedingTime=3.0)], x=TRAP_ME[0], y=TRAP_ME[1], zombies=TWO_IN,
               weapon=None)
    a = tick(r, sv)
    d = last(tmp_path)
    assert (a.type, a.args["itemId"], a.args["part"], a.args.get("keepMoving", False)) == ("bandage", 501, 9, False)
    assert d["branch"] == "care" and d["inputs"]["branches"]["threat"]["trapped"] == 2
    assert d["inputs"]["branches"]["threat"]["flee"] == "unarmed" and care_why(tmp_path)["reason"] == "bleeding"


def test_trapped_the_running_bandage_holds_the_care_s_tick(tmp_path, monkeypatch):
    """Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
    r, sv = make(tmp_path)
    r.scan(closed_room())
    hold(r, 501, "Base.Bandage")
    parts = [part(9, bleeding=True, bleedingTime=3.0)]
    care_frame(r, parts, x=TRAP_ME[0], y=TRAP_ME[1], zombies=TWO_IN, weapon=None)
    tick(r, sv)
    r.fake.answer({"bandage": ["accepted"]})
    r.pump()
    care_frame(r, parts, x=TRAP_ME[0], y=TRAP_ME[1], zombies=TWO_IN, weapon=None)
    assert tick(r, sv) is None
    d = last(tmp_path)
    assert d["branch"] == "care" and "holding" in care_why(tmp_path) and sends(r) == ["bandage"]


def test_trapped_with_no_dressing_and_a_worn_cotton_garment_the_unwear(tmp_path, monkeypatch):
    """P25-H's unwear on the trapped hold's tick (quiet reads false with the zombies in the room; the trapped tick
    counts as quiet for the unwear, never for the wash): the T-shirt covering the least comes off.
    Named change, Plan 31 Task 15a (ruling P31-H): the Dress the default; pinned with `DRESS_MANEUVER` off."""
    monkeypatch.setattr("agent.base.planner.survive.Survive.DRESS_MANEUVER", False)
    r, sv = unwear_rig(tmp_path)
    r.scan(closed_room())
    care_frame(r, [part(9, bleeding=True, bleedingTime=14.7)], x=TRAP_ME[0], y=TRAP_ME[1], zombies=TWO_IN,
               weapon=None)
    a = tick(r, sv)
    assert (a.type, a.args) == ("unwear", {"itemId": 20}) and last(tmp_path)["branch"] == "care"
    assert care_why(tmp_path)["reason"] == "unwear"


def test_trapped_with_nothing_to_tend_the_hold_takes_the_tick_and_no_lower_branch_runs(tmp_path):
    """Nothing bleeds: the care answers nothing, the hold takes the tick (the threat's line, no command), and the
    need below never runs (thirst high, water held)."""
    r, sv = make(tmp_path)
    r.scan(closed_room())
    r.event("item_added", itemId=701, fullType="Base.WaterBottle", weight=1.0, use="water")
    r.frame(x=TRAP_ME[0], y=TRAP_ME[1], zombies=TWO_IN, weapon=None, thirst=0.6)
    assert tick(r, sv) is None
    d = last(tmp_path)
    assert d["branch"] == "threat" and d["inputs"]["branches"]["threat"]["trapped"] == 2
    assert "care" in d["inputs"]["branches"] and "need" not in d["inputs"]["branches"] and sends(r) == []


def test_trapped_with_a_zombie_in_reach_the_fight_goes_first(tmp_path):
    """P25-P on: the lone zombie at 0.8 tiles is shoved before any bandage."""
    r, sv = make(tmp_path)
    r.scan(closed_room())
    hold(r, 501, "Base.Bandage")
    care_frame(r, [part(9, bleeding=True, bleedingTime=3.0)], x=TRAP_ME[0], y=TRAP_ME[1],
               zombies=[z(1, 103.3, 202.5)], weapon=None)
    a = tick(r, sv)
    assert a.type == "shove" and last(tmp_path)["branch"] == "threat"


def test_with_trapped_care_off_the_trapped_hold_sends_nothing(tmp_path):
    r, sv = make(tmp_path)
    sv.TRAPPED_CARE = False
    r.scan(closed_room())
    hold(r, 501, "Base.Bandage")
    care_frame(r, [part(9, bleeding=True, bleedingTime=3.0)], x=TRAP_ME[0], y=TRAP_ME[1], zombies=TWO_IN,
               weapon=None)
    assert tick(r, sv) is None
    d = last(tmp_path)
    assert d["branch"] == "threat" and "care" not in d["inputs"]["branches"] and sends(r) == []


# ================================================================ P25-R: the prompt and the `toward` square
def test_the_loop_sentence_says_how_the_program_fights_armed_and_unarmed():
    """Named change, ruling P25-Z (Plan 25's close fix): unarmed, the program shoves and stomps a lone zombie (P25-P's
    unarmed fight) and flees two or more; the prompt said it fled them all."""
    want = ("the program fights the zombies near you itself while it holds a weapon; with `weapon` null it shoves and "
            "stomps a lone zombie and flees two or more, so loot for a weapon first; you loot the nearest building")
    assert want in L.SYSTEM
    assert "with `weapon` null it flees them" not in L.SYSTEM
    assert "the program clears the zombies near you itself" not in L.SYSTEM


def test_the_toward_explanation_says_an_explore_at_its_square_is_always_accepted():
    assert "toward names the next building to walk to when none is near (its door); an ExploreToward at its square " \
           "is always accepted" in L.SYSTEM


def test_the_strategy_never_says_the_program_clears_the_zombies_unarmed():
    texts = [s["text"] for s in GP.strategy()]
    assert not any("(the program clears the zombies near you)" in t for t in texts)
    assert any("(the program clears the zombies near you while weapon is not null)" in t for t in texts)
    line = next(s for s in GP.strategy() if "while weapon is not null" in s["text"])
    assert "weapon" in line["reads"]


def far_view(toward=True):
    """A view at (100, 200) listing building 2 150 tiles east, its `toward` square (250, 200) and door (249, 201)."""
    b = {"id": 2, "x": 250, "y": 200, "door": [249, 201], "dist": 150.0, "containers": 3, "looted": False}
    v = {"pos": {"x": 100.0, "y": 200.0}, "buildings": [b], "woods_r": G.WOODS_R}
    if toward:
        v["toward"] = {"for": "unlooted", "building": 2, "door": [249, 201], "square": [250, 200], "dist": 150.0}
    return v


@pytest.mark.parametrize("x, y, err", [(250, 200, None), (249, 201, None), (250, 235, None), (100, 350, "out of range"),
                                       (250, 260, "out of range")])
def test_an_explore_at_the_toward_square_is_accepted_whatever_its_distance_and_elsewhere_refused(x, y, err):
    """F5: 9 of 25 explore answers pointed back toward building 2, 128.85 to 222.79 tiles off, and were refused: an
    ExploreToward within WOODS_R of the view's `toward` square or door is the walk the goal layer takes in legs, so it
    is accepted 150 tiles off; one 150 tiles off elsewhere is refused as before."""
    got = L.place_error(G.ExploreToward(x, y), far_view())
    assert got == (None if err is None else "invalid: " + err)


def test_with_no_toward_the_far_square_is_refused_as_before():
    assert L.place_error(G.ExploreToward(250, 200), far_view(toward=False)) == "invalid: out of range"


def test_an_explore_near_pos_but_in_the_woods_keeps_its_wording():
    v = far_view()
    assert L.place_error(G.ExploreToward(140, 200), v) == "invalid: in the woods"


# ================================================================ P25-S: the low fight
def test_under_flee_health_one_zombie_is_fought_by_the_shove_and_the_stomp_logged_low_fight(tmp_path):
    """E13 (the health near 31 from game minute 712 to the cap, the last 15 fights fled `health`, nothing killed for 96
    game minutes): health 35, a bat held, one zombie 4 tiles off: the Fight's stance (an `aim`, never sought), logged
    `low_fight`; at 1.6 tiles the backpedal, never the swing; at 0.8 the shove (`shove` "low"); its knock-down read, the
    stomp."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 104.0)], health=35.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "aim" and w["fight"] is True and w["low_fight"] is True and "flee" not in w
    assert w["leg"] == "stand" and not w.get("seek") and sv.fight.shove_only == "low" and "unarmed_fight" not in w
    r.advance(0.5)
    r.frame(zombies=[z(1, 101.6)], health=35.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "aim" and w["leg"] == "back" and w["low_fight"] is True
    r.advance(0.5)
    r.frame(zombies=[z(1, 100.8)], health=35.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("shove", {"targetId": 1}) and w["shove"] == "low" and w["low_fight"] is True
    r.fake.answer({"shove": ["accepted", DOWN]})
    r.pump()
    r.advance(0.5)
    r.frame(zombies=[z(1, 101.2, floor=True)], health=35.0)
    a = tick(r, sv)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and threat_why(tmp_path)["low_fight"] is True
    assert "attack" not in sends(r)


@pytest.mark.parametrize("zs, health, want", [
    ([z(1, 100.8), z(2, 100.0, 205.0)], 35.0, "flee"),   # two within DANGER_R: the `health` flee
    ([z(1, 100.8)], 15.0, "flee"),                       # under FLEE_HEALTH_FLOOR: the `health` flee
    ([z(1, 100.8)], 20.0, "low"),                        # at the floor: the low fight
    ([z(1, 100.8)], 45.0, "fight")])                     # over FLEE_HEALTH: the ordinary fight, no `low_fight`
def test_the_low_fight_s_bounds(tmp_path, zs, health, want):
    r, sv = make(tmp_path)
    r.frame(zombies=zs, health=health)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    if want == "flee":
        assert a.type == "steer" and w["flee"] == "health" and "low_fight" not in w
    elif want == "low":
        assert a.type == "shove" and w["low_fight"] is True
    else:
        assert a.type == "attack" and w["fight"] is True and "low_fight" not in w


def test_a_running_health_flee_turns_to_the_low_fight_when_one_zombie_is_left(tmp_path):
    """A `health` flee from two (health 35) whose second zombie leaves DANGER_R turns to the low fight (the refight
    margin held it before)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 103.0), z(2, 100.0, 205.0)], health=35.0)
    assert tick(r, sv).type == "steer" and threat_why(tmp_path)["flee"] == "health"
    r.answer()
    r.advance(1.0)
    r.frame(zombies=[z(1, 103.0), z(2, 100.0, 209.0)], health=35.0)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert sv.mode == "fight" and w["low_fight"] is True and "flee" not in w


def test_with_low_fight_off_the_lone_zombie_is_fled_health_as_before(tmp_path):
    r, sv = make(tmp_path)
    sv.LOW_FIGHT = False
    r.frame(zombies=[z(1, 100.8)], health=35.0)
    a = tick(r, sv)
    assert a.type == "steer" and threat_why(tmp_path)["flee"] == "health"


def test_unarmed_under_flee_health_the_unarmed_flee_stays(tmp_path):
    """Unarmed, under FLEE_HEALTH_PAIR the unarmed fight is not allowed, whatever the low fight reads: `unarmed`."""
    r, sv = make(tmp_path)
    lone(r, 100.8, health=35.0)
    a = tick(r, sv)
    assert a.type == "steer" and threat_why(tmp_path)["flee"] == "unarmed"


# ================================================================ P25-T: the misses counted over the run
def spaced(r, sv, end=MISS, gap=5.0, x=100.8):
    """One shove at the lone zombie at `x` (unarmed: every shove at point blank), answered `end`, then `gap` seconds."""
    lone(r, x)
    a = tick(r, sv)
    assert (a.type, a.args) == ("shove", {"targetId": 1})
    r.fake.answer({"shove": ["accepted", end]})
    r.pump()
    r.advance(gap)


def test_three_missed_shoves_5_s_apart_take_the_break(tmp_path):
    """E13's fight 18 (eight shoves over 28.5 s, the backpedal spacing them past SHOVE_REPEAT_S): three missed shoves at
    one zombie 5 s apart: the next tick breaks away (`corner` {kind break, shoved, n 1, misses 3}), the count reset."""
    r, sv = make(tmp_path)
    for _ in range(3):
        spaced(r, sv)
    lone(r, 100.8)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and a.args["gait"] == P.FLEE_GAIT and a.args["vx"] < -0.99
    assert w["corner"] == {"kind": "break", "shoved": 1, "n": 1, "misses": 3} and sv.fight._miss_run == {}


def test_two_spaced_misses_shove_again_without_the_corner_s_why(tmp_path):
    r, sv = make(tmp_path)
    for _ in range(2):
        spaced(r, sv)
    lone(r, 100.8)
    a = tick(r, sv)
    assert a.type == "shove" and "corner" not in threat_why(tmp_path) and sv.fight._miss_run == {1: 2}


def test_a_knock_down_between_the_spaced_misses_resets_the_count(tmp_path):
    """Miss, miss, knock-down (then read standing again past KNOCK_READ_S), miss: one miss since it, the shove again."""
    r, sv = make(tmp_path)
    spaced(r, sv)
    spaced(r, sv)
    spaced(r, sv, end=DOWN)
    lone(r, 100.8)
    assert tick(r, sv) is None and threat_why(tmp_path)["knocked"] == 1   # the knock wait, read at its end
    r.advance(P.KNOCK_READ_S)
    spaced(r, sv)
    lone(r, 100.8)
    a = tick(r, sv)
    assert a.type == "shove" and sv.fight._miss_run == {1: 1}


def test_a_new_fight_starts_its_count_at_0(tmp_path):
    """Two misses, the zombie gone (the Fight ends), back again: a new Fight; its third miss is its first: no break."""
    r, sv = make(tmp_path)
    spaced(r, sv)
    spaced(r, sv)
    first = sv.fight
    r.event("zombie_dead", id=1)   # the zombie gone from the listing: the threat branch holds nothing, the Fight ends
    r.frame(weapon=None)
    tick(r, sv)
    assert sv.fight is None and first._miss_run == {1: 2}
    spaced(r, sv)
    lone(r, 100.8)
    a = tick(r, sv)
    assert a.type == "shove" and sv.fight is not first and sv.fight._miss_run == {1: 1}


def test_two_at_point_blank_after_a_spaced_miss_break_through_the_gap(tmp_path):
    """P25-A's two-zombie break needs the last shove missed within SHOVE_REPEAT_S; the backpedal's spacing defeats it as
    it does the lone break (P25-T): E11's wounded corner (`test_survive_t.shoved`) misses its shove at zombie 1, 5 s
    pass, and a second zombie stands 0.9 tiles off: the break through the gap; with the switch off, the shove again."""
    zs = [z(1, 100.49)]
    two = [z(1, 100.49), z(2, 100.0, 200.9)]
    r, sv = shoved(tmp_path, zs)
    r.advance(4.5)
    fr(r, two, WOUND, NO_STIFF, health=70.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and w["corner"] == {"kind": "break", "shoved": 1, "n": 2}
    (tmp_path / "off").mkdir()
    r2, sv2 = shoved(tmp_path / "off", zs)
    sv2.SHOVE_BREAK_RUN = False
    r2.advance(4.5)
    fr(r2, two, WOUND, NO_STIFF, health=70.0)
    a2 = tick(r2, sv2)
    assert a2.type == "shove" and "corner" not in threat_why(tmp_path / "off")


def test_with_shove_break_run_off_spaced_misses_never_break(tmp_path):
    """The switch off: P25-L's window (SHOVE_BREAK_N x SHOVE_REPEAT_S) as iteration 14 left it: four misses 5 s apart
    never break."""
    r, sv = make(tmp_path)
    sv.SHOVE_BREAK_RUN = False
    for _ in range(4):
        spaced(r, sv)
    lone(r, 100.8)
    assert tick(r, sv).type == "shove" and "corner" not in threat_why(tmp_path)


# ================================================================ the residual: the rejected wears
def test_on_a_1_7_hello_the_wear_pick_leaves_out_a_garment_an_item_changed_read_worn(tmp_path):
    """F5's care stock sent the wear of trousers worn since seq 654 five times, each rejected `worn`: at `3281cad2`
    `item_fields` read the `1.7` hello False, so `item_changed`'s `worn` never landed (P25-O, `447e9115`, fixed it).
    On a `1.7` hello an unworn jacket is the pick; once an `item_changed` reads it worn it is left out."""
    from .test_survive_j import cloth, wl
    r, sv = make(tmp_path)
    r.fake.hello(mod="1.7")
    r.pump()
    assert r.world.item_fields() is True
    cloth(r, 20, bite=10.0, scratch=10.0)
    r.frame(worn=[wl(JACKET, 5.0, 5.0)])
    assert sv.care._wear_pick()[0] == 20
    r.event("item_changed", itemId=20, use="clothing", clothing=rec(bite=10.0, scratch=10.0, worn=True), worn=True)
    assert r.world.inventory[20]["worn"] is True and sv.care._wear_pick() is None
