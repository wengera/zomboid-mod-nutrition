"""Survival 6 (Plan 24 Task 10, ruling P24-G, Angus's direction of 2026-10-29 after F2's shots): the standing fight
(the combat stance with the backpedal, its stand-off fallback), on the fake mod over the PZA/1.5 skills Task 9 landed.
The decision goldens (`test_replay_decisions.py`) stay unmoved: their artifacts' hellos announce no PZA/1.5 skill, and
the planner sends one only to a build whose caps carry it (`World.can`)."""
import math

import pytest

from agent.base.planner import policies as P
from agent.base.planner import survive as S

from .test_policies import CAPS_14, all_sends_valid, square, zombie
from .test_survive import last, make, threat_why, tick


def zd(zid, x, y, has_target=True, health=1.0):
    """A zombie record at (x, y) with `hasTarget` and `health` set (the stance's closing read and its progress)."""
    return dict(zombie(zid, x, y), hasTarget=has_target, health=health)


def stance_args(r):
    t, a = r.cmd()
    assert t == "aim", (t, a)
    return a


# ================================================================ the constants
def test_the_stance_constants():
    """Named change (ruling P24-N, Task 12): KEEP_R replaces P24-M's BACKPEDAL_BAND and the closing read's
    CLOSE_MIN; AIM_HOLD_S mirrors the Lua's K.AIM_HOLD_MS."""
    assert (P.AIM_LEG_S, P.STAND_MAX_S, P.KEEP_R, P.AIM_HOLD_S) == (2.0, 20.0, 2.5, 2.0)
    assert not hasattr(P, "BACKPEDAL_BAND") and not hasattr(P, "CLOSE_MIN")
    assert P.FIGHT_REACH < P.KEEP_R < P.DANGER_R
    assert S.BRANCHES[0] == "threat"


# ================================================================ the stance against one (P24-N)
def test_one_zombie_at_four_tiles_is_met_standing_then_backpedalled_inside_keep_r_then_swung_at(tmp_path):
    """P24-N (named change of the P24-M case): one held at 4 tiles, armed, full health: `aim` facing it for
    AIM_LEG_S, standing (beyond KEEP_R it is let come); the standing leg holds while the target stays beyond KEEP_R
    and gives way the tick it comes inside (2.2 tiles): the next leg backpedals along the away vector (west, the zombie
    east of the player); within reach the `attack` goes from the stance (the running leg gives way)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    a = stance_args(r)
    assert a == {"vx": 0.0, "vy": 0.0, "seconds": 2.0, "targetId": 1, "bearing": -1.0}
    w = threat_why(tmp_path)
    assert w["fight"] is True and w["stance"] is True and w["leg"] == "stand" and w["back"] is None
    sends = len(r.acts.history)
    r.advance(0.5)
    r.frame(zombies=[zd(1, 102.6, 200.0)])
    assert tick(r, sv) is None and len(r.acts.history) == sends            # the leg holds beyond KEEP_R
    assert threat_why(tmp_path)["holding"] == r.acts.history[-1].aid
    r.advance(0.5)
    r.frame(zombies=[zd(1, 102.2, 200.0)])                                  # inside KEEP_R: the stand gives way
    tick(r, sv)
    assert stance_args(r)["vx"] == -1.0 and threat_why(tmp_path)["back"] == [-1.0, 0.0]
    assert threat_why(tmp_path)["leg"] == "back" and len(r.acts.history) == sends + 1
    r.advance(0.5)
    r.frame(zombies=[zd(1, 101.0, 200.0)])
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1}) and threat_why(tmp_path)["stance"] is True   # from the stance
    assert sv.fight.in_stance()
    all_sends_valid(r)


@pytest.mark.parametrize("x, kind", [(106.0, "stand"), (102.55, "stand"), (102.5, "back"), (102.2, "back"),
                                     (102.01, "back")])
def test_a_pinned_target_beyond_keep_r_is_stood_facing_and_inside_it_backpedalled_from(tmp_path, x, kind):
    """Ruling P24-N 2: beyond KEEP_R (6 and 2.55 tiles) the leg stands facing the target, (0, 0); inside it and
    beyond FIGHT_REACH (2.5, 2.2, 2.01) the leg backpedals along the away vector whatever the target's own move (a
    zombie that does not come is backed from as one that does: no closing read)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, x, 200.0, has_target=False)])
    tick(r, sv)
    a = stance_args(r)
    assert (a["vx"], a["vy"]) == ((-1.0, 0.0) if kind == "back" else (0.0, 0.0))
    assert threat_why(tmp_path)["leg"] == kind and "closing" not in threat_why(tmp_path)


@pytest.mark.parametrize("x", [102.0, 101.6])
def test_the_fights_first_action_is_aim_even_within_reach_then_the_swing_from_it(tmp_path, x):
    """Ruling P24-N 1: the stance opens every fight: a target already within FIGHT_REACH (2.0, 1.6 tiles) at the
    fight's first choose is met with an `enter` leg, (0, 0) (the stance is not held: `in_stance`), and the next tick
    the swing goes from it (the running leg gives way within reach). Within CORNERED_R (1.5) of a character with no
    fight running the corner rules stand (P24-G 1: a cornered Fight never stands): its swing goes at once."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, x, 200.0)])
    tick(r, sv)
    a = stance_args(r)
    assert (a["vx"], a["vy"], a["targetId"]) == (0.0, 0.0, 1) and threat_why(tmp_path)["leg"] == "enter"
    assert r.acts.history[0].type == "aim"
    r.answer("progress")
    r.frame(zombies=[zd(1, x, 200.0)])
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1}) and sv.fight._attack_held is True


def test_a_first_engagement_within_cornered_r_is_the_corners_swing(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 101.0, 200.0)])
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1}) and threat_why(tmp_path)["corner_kind"] == "walk"


def test_after_a_walk_released_the_stance_a_target_in_reach_is_aimed_at_before_the_swing(tmp_path):
    """Any send other than the Fight's aim or its attack from the stance releases it (Task 9's hand-over): after a
    walk the stance is not held, so the first choose within reach is an `enter` leg; an attack whose stance hold ran
    out (AIM_HOLD_S after its end) needs one too."""
    r = Rig(tmp_path)
    r.frame(zombies=[zd(1, 101.0, 200.0)])
    f = stance_fight(r)
    f.send(P.WalkTo(101.5, 200.5, "run"))
    assert not f.in_stance()
    cmd = f.choose()
    assert cmd.TYPE == "aim" and f.why["leg"] == "enter"
    f.send(cmd)
    assert f.in_stance()
    att = f.choose()
    assert att.TYPE == "attack"
    a = f.send(att)
    assert f.in_stance()
    r.answer()
    assert a.state == "done" and f.in_stance()                             # the Lua's hold after the swing
    r.advance(P.AIM_HOLD_S)
    assert not f.in_stance() and f.choose().TYPE == "aim"


def test_a_stance_leg_ended_re_aims_and_backpedals_inside_keep_r_whatever_the_target_does(tmp_path):
    """Named change (P24-N, the P24-M closing case): each AIM_LEG_S the stance re-aims; inside KEEP_R the leg
    backpedals whether or not the target moved toward the player since the last leg (P24-M stood when it did not)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 102.2, 200.0)])
    tick(r, sv)
    assert stance_args(r)["vx"] == -1.0
    r.answer()
    r.advance(2.0)
    r.frame(x=99.0, zombies=[zd(1, 101.2, 200.0)])                          # 2.2 tiles still: it followed
    tick(r, sv)
    assert stance_args(r)["vx"] == -1.0 and threat_why(tmp_path)["leg"] == "back"
    r.answer()
    r.advance(2.0)
    r.frame(x=99.0, zombies=[zd(1, 101.2, 200.0)])                          # it stood: backpedalled all the same
    tick(r, sv)
    assert stance_args(r)["vx"] == -1.0 and threat_why(tmp_path)["back"] == [-1.0, 0.0]


def test_a_first_leg_on_a_zombie_with_no_target_beyond_keep_r_stands(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0, has_target=False)])
    tick(r, sv)
    a = stance_args(r)
    assert (a["vx"], a["vy"], a["targetId"]) == (0.0, 0.0, 1)


def test_the_backpedal_never_steps_into_a_wall_or_over_a_fence(tmp_path):
    """The backpedal reads the steer probe (`policies.clear_heading`: `line_clear` over STEER_PROBE, which reads a
    hoppable fence blocked, P24-G 4: the stance never vaults): a fence on the player's west edge turns the heading by
    STEER_TURNS to the first clear one (+30 degrees); walled in on every turn, the leg stands (a wall behind is never
    stepped into)."""
    r, sv = make(tmp_path)
    sqs = [square(x, y) for x in range(95, 106) for y in range(195, 206)]
    sqs = [dict(s, blockW=True, hopW=True) if (s["x"], s["y"]) == (100, 200) else s for s in sqs]
    r.scan(sqs)
    r.frame(x=100.5, y=200.5, zombies=[zd(1, 103.0, 200.5)])                # 2.5 tiles: inside KEEP_R
    tick(r, sv)
    a = stance_args(r)
    turns = [P._rotate((-1.0, 0.0), t) for t in P.STEER_TURNS]
    first = next(v for v in turns if P.clear_heading(r.world, v))
    assert not P.clear_heading(r.world, (-1.0, 0.0)) and (a["vx"], a["vy"]) == first and first != (-1.0, 0.0)
    (tmp_path / "w").mkdir()
    r2, sv2 = make(tmp_path / "w")
    walls = [dict(square(x, y), solid=True) for x in range(95, 106) for y in range(195, 206)
             if (x, y) != (100, 200) and x < 102]
    r2.scan(walls + [square(x, y) for x in range(102, 106) for y in range(195, 206)] + [square(100, 200),
                                                                                      square(101, 200)])
    r2.frame(x=100.5, y=200.5, zombies=[zd(1, 102.7, 200.5)])               # 2.2 tiles, walled in behind
    tick(r2, sv2)
    a = stance_args(r2)
    assert (a["vx"], a["vy"]) == (0.0, 0.0) and threat_why(tmp_path / "w")["leg"] == "back"
    assert threat_why(tmp_path / "w")["back"] is None


def test_two_zombies_at_full_health_are_met_in_the_stance_backing_from_both(tmp_path):
    """Named change (P24-M): both at 2.5 tiles, inside KEEP_R."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 102.5, 200.0), zd(2, 100.0, 202.5)])
    tick(r, sv)
    a = stance_args(r)
    assert a["targetId"] in (1, 2) and abs(a["vx"] + math.sqrt(0.5)) < 1e-9 and abs(a["vy"] + math.sqrt(0.5)) < 1e-9


def test_two_zombies_under_flee_health_pair_are_fled_not_stood(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 100.0, 204.0)], health=55.0)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "pair"


def test_three_zombies_are_fled_never_stood(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 100.0, 204.0), zd(3, 103.0, 203.0)])
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "many"


def test_one_zombie_under_flee_health_is_fled_never_stood(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)], health=35.0)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "health"


def test_unarmed_the_stance_is_never_taken(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)], weapon=None)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "unarmed"


def test_a_running_stance_gives_way_to_the_flee_when_a_third_comes(tmp_path):
    """The flee from three supersedes the stance leg (the Lua releases the stance on supersede)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    assert r.cmd()[0] == "aim"
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 100.0, 204.0), zd(3, 103.0, 203.0)])
    tick(r, sv)
    assert r.cmd()[0] == "steer" and sv.mode == "flee"


def test_a_pza_1_4_build_is_never_sent_the_stance(tmp_path):
    """`World.can`: a hello whose caps lack `aim` (every decision golden's artifact) keeps the approach walk."""
    r, sv = make(tmp_path, caps=CAPS_14)
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 104.5, "y": 200.5, "gait": "run"})
    assert "stance" not in threat_why(tmp_path) and not r.world.can("aim") and r.world.can("attack")


# ================================================================ the stand-off fallback
def stand_legs(r, sv, n, x=104.0, health=1.0, dt=2.0):
    """`n` stance legs answered done, each AIM_LEG_S of clock, the zombie standing at `x` with `health`."""
    for _ in range(n):
        r.answer()
        r.advance(dt)
        r.frame(zombies=[zd(1, x, 200.0, has_target=False, health=health)])
        tick(r, sv)


def test_a_stand_with_no_progress_in_stand_max_s_closes_in_the_stance_never_a_walk_at_a_run(tmp_path):
    """Ruling P24-N 1 (named change of the P24-G fallback to the approach and swing): a stand-off (the zombie standing
    6 tiles off, never coming) after STAND_MAX_S without its health falling is closed on in the stance: an `aim` with
    the unit vector toward it (`advance`), never a `walkTo` at a run; the stall clock (FIGHT_MAX_S, the stalled flee)
    starts only then."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 106.0, 200.0, has_target=False)])
    tick(r, sv)
    assert r.cmd()[0] == "aim"
    stand_legs(r, sv, 9, x=106.0)                                           # 18 s
    assert stance_args(r)["vx"] == 0.0 and last(tmp_path)["inputs"]["fight_s"] == 2.0   # one leg's clock
    stand_legs(r, sv, 1, x=106.0)                                           # 20 s: the advance
    a = stance_args(r)
    assert (a["vx"], a["vy"], a["targetId"]) == (1.0, 0.0, 1) and sv.fight.advance and not sv.fight.standoff
    w = threat_why(tmp_path)
    assert w["leg"] == "toward" and w["advance"] is True and w["stance"] is True
    assert not any(x.type == "walkTo" for x in r.acts.history)
    r.answer()
    r.advance(1.0)
    r.frame(zombies=[zd(1, 106.0, 200.0, has_target=False)])
    tick(r, sv)
    assert last(tmp_path)["inputs"]["fight_s"] == 1.0                       # the advance's stall clock runs
    assert stance_args(r)["vx"] == 1.0


def test_the_advance_with_its_line_blocked_walks_round_the_wall_at_a_run(tmp_path):
    """The advance's one walk: the line to the stand-off target blocked over STEER_PROBE (a wall between), the
    approach walk at a run (the path follower walks round it); with the line clear, the aim toward it."""
    r, sv = make(tmp_path)
    sqs = [square(x, y) for x in range(95, 110) for y in range(195, 206)]
    sqs = [dict(s, blockW=True) if (s["x"], s["y"]) == (102, 200) else s for s in sqs]
    r.scan(sqs)
    r.frame(x=100.5, y=200.5, zombies=[zd(1, 106.5, 200.5, has_target=False)])
    tick(r, sv)
    for _ in range(10):
        r.answer()
        r.advance(2.0)
        r.frame(x=100.5, y=200.5, zombies=[zd(1, 106.5, 200.5, has_target=False)])
        tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 106.5, "y": 200.5, "gait": "run"}) and sv.fight.advance
    assert threat_why(tmp_path)["leg"] == "walk"


def test_a_falling_target_health_restarts_the_stand_clock_and_ends_the_advance(tmp_path):
    """Named change (P24-N): the clock restarts on a hit; at STAND_MAX_S without one the advance (an aim toward,
    never a walk); a hit then ends the advance and the stand begins again."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0, has_target=False)])
    tick(r, sv)
    stand_legs(r, sv, 8)                                                    # 16 s
    stand_legs(r, sv, 1, health=0.6)                                        # a hit landed: the clock restarts
    assert threat_why(tmp_path)["stand_s"] == 0.0
    stand_legs(r, sv, 9, health=0.6)                                        # 18 s more: still standing
    assert r.cmd()[0] == "aim" and not sv.fight.advance and stance_args(r)["vx"] == 0.0
    stand_legs(r, sv, 1, health=0.6)
    assert stance_args(r)["vx"] == 1.0 and sv.fight.advance and not sv.fight.standoff
    stand_legs(r, sv, 1, health=0.4)                                        # the next hit: the stand again
    assert stance_args(r)["vx"] == 0.0 and not sv.fight.advance and threat_why(tmp_path)["stand_s"] == 0.0


def test_a_kill_restarts_the_stand_on_the_next_target(tmp_path):
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0, has_target=False), zd(2, 100.0, 204.5, has_target=False)])
    tick(r, sv)
    assert stance_args(r)["targetId"] == 1
    stand_legs(r, sv, 0)
    for _ in range(9):
        r.answer()
        r.advance(2.0)
        r.frame(zombies=[zd(1, 104.0, 200.0, has_target=False), zd(2, 100.0, 204.5, has_target=False)])
        tick(r, sv)
    r.answer()
    r.event("zombie_dead", id=1)
    r.advance(2.0)
    r.frame(zombies=[zd(2, 100.0, 204.5, has_target=False)])
    tick(r, sv)
    assert stance_args(r)["targetId"] == 2 and threat_why(tmp_path)["stand_s"] == 0.0 and not sv.fight.standoff


def test_the_corner_keeps_its_swing_and_never_stands(tmp_path):
    """The corner rules stay: a cornered Fight (`point_blank`) never takes the stance (`Fight.standing`)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    f = P.Fight(r.world, r.acts, r.clock, target=1)
    f.stance, f.point_blank = True, True
    assert not f.standing()
    f.point_blank, f.only = False, {1}
    assert not f.standing()
    f.only = None
    assert f.standing()


def test_two_held_under_flee_health_pair_with_one_within_danger_r_fight_by_the_approach_not_the_stance(tmp_path):
    """The pair rule reads the DANGER_R count (one here, so the hysteresis fights); the stance reads the held count:
    two held at health 50 (under FLEE_HEALTH_PAIR) is no standing fight: the running stance leg gives way to the
    approach walk once the hold radius (DISENGAGE_R while the fight runs) holds the second."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 92.0, 200.0)], health=50.0)
    tick(r, sv)
    assert r.cmd()[0] == "aim"                                              # one held within DANGER_R
    r.frame(zombies=[zd(1, 104.0, 200.0), zd(2, 92.0, 200.0)], health=50.0)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 104.5, "y": 200.5, "gait": "run"}) and threat_why(tmp_path)["fight"] is True
    assert last(tmp_path)["inputs"]["held"] == 2


def test_trapped_on_a_room_square_the_fight_keeps_the_approach_never_the_stance(tmp_path):
    """The corner rules stay for a trapped character (`_trapped`: a room square, no way out, nothing to adopt): the
    held zombie inside the closed room is walked to and swung at, never backpedalled from inside the walls."""
    from .test_survive import closed_room
    r, sv = make(tmp_path)
    r.scan(closed_room())
    me = (100.5, 200.5)
    r.frame(x=me[0], y=me[1], zombies=[dict(zombie(1, 104.5, 204.5, me=me), health=1.0)])
    tick(r, sv)
    assert r.cmd()[0] == "walkTo" and sv._trapped(sv._within(S.DANGER_R), True)


def test_a_standing_fight_reads_no_walk_so_the_look_behind_its_target_does_not_flee(tmp_path):
    """P24-A (b) reads the fight's walk: the stance does not walk beyond reach, so zombie 2 listed behind zombie 1
    (the E5 case of `test_survive`'s P24-A (b) test, there pinned on a PZA/1.4 build) does not turn it to a flee; after
    the stand-off fallback the Fight walks, and the look behind reads again."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 105.0, 200.0), zd(2, 110.0, 201.0)])
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd()[0] == "aim" and w["fight"] is True and "behind" not in w
    sv.fight.standoff = True
    r.answer()
    r.frame(zombies=[zd(1, 105.0, 200.0), zd(2, 110.0, 201.0)])
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd()[0] == "steer" and w["flee"] == "held" and w["behind"] == [2]


def test_the_advance_reads_as_a_walk_so_the_look_behind_its_target_flees(tmp_path):
    """P24-N: the advance closes on the target (an aim toward it), so P24-A (b)'s look behind reads it as the walk
    it is: zombie 2 listed behind zombie 1 turns it to the `held` flee, as the approach walk did."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 105.0, 200.0), zd(2, 110.0, 201.0)])
    tick(r, sv)
    assert r.cmd()[0] == "aim"
    sv.fight.advance = True
    r.answer()
    r.frame(zombies=[zd(1, 105.0, 200.0), zd(2, 110.0, 201.0)])
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd()[0] == "steer" and w["flee"] == "held" and w["behind"] == [2]


# ================================================================ the care branch (P24-G 2)
from agent.base.planner import care as C   # noqa: E402  (the care tests' module, beside the stance's)


def part(i, **k):
    """A PZA/1.5 part record: index `i`, health 80, no bleeding, unbandaged (bandageLife and bandageDirty None as the
    Lua leaves them on an unbandaged part), `k` laid over."""
    return dict({"i": i, "h": 80.0, "bleeding": False, "bleedingTime": 0.0, "bandaged": False, "bandageLife": None,
                 "bandageDirty": None, "deep": False, "infected": False}, **k)


def hold(r, iid, full_type, use="bandage", weight=0.1):
    r.event("item_added", itemId=iid, fullType=full_type, weight=weight, use=use)


def care_frame(r, parts, **k):
    r.frame(wounds={"parts": parts, "bleeding": sum(1 for p in parts if p.get("bleeding"))}, **k)


def care_why(tmp_path):
    return last(tmp_path)["inputs"]["branches"]["care"]


def test_the_care_constants_and_the_item_kinds():
    assert (C.CARE_RETRY_MIN, C.DIRTY_RAG_MIN, C.WASH_R) == (2.0, 10.0, 15.0)
    kinds = {t: C.care_kind(t) for t in ("Base.Bandage", "Base.AlcoholBandage", "Base.Bandaid", "Base.RippedSheets",
                                         "Base.AlcoholRippedSheets", "Base.DenimStrips", "Base.RippedSheetsDirty",
                                         "Base.BandageDirty", "Base.DenimStripsDirty", "Base.RagFilter",
                                         "Base.BandageBox", "Base.Tshirt_WhiteTINT")}
    assert kinds == {"Base.Bandage": "bandage", "Base.AlcoholBandage": "bandage", "Base.Bandaid": "bandage",
                     "Base.RippedSheets": "rag", "Base.AlcoholRippedSheets": "rag", "Base.DenimStrips": "rag",
                     "Base.RippedSheetsDirty": "dirty", "Base.BandageDirty": "dirty", "Base.DenimStripsDirty": "dirty",
                     "Base.RagFilter": None, "Base.BandageBox": None, "Base.Tshirt_WhiteTINT": None}
    assert [C.rippable(t) for t in ("Base.Tshirt_WhiteLongSleeveTINT", "Base.Shirt_FormalWhite", "Base.Socks_Long",
                                    "Base.Shirt_Denim", "Base.Shorts_LongDenim", "Base.Hat_BucketHat",
                                    "Base.Jacket_Leather")] == [True, True, True, False, False, False, False]


def test_the_care_branch_runs_between_the_threat_and_the_need():
    assert S.BRANCHES == ("threat", "care", "need", "load", "night", "goal")


def bleeding_rig(tmp_path, items, bleeding_time=5.0, deep=False, caps=None):
    r, sv = make(tmp_path, caps=caps)
    r.frame()
    for iid, ft in items:
        hold(r, iid, ft)
    care_frame(r, [part(5, bleeding=True, bleedingTime=bleeding_time, deep=deep)], thirst=0.5)
    return r, sv


def test_a_bleeding_part_takes_a_bandage_before_a_clean_rag_before_a_dirty_one(tmp_path):
    """P24-G 2: the best held item: a bandage, then a clean rag; the bandage goes on the part by index; the need
    (thirst 0.5) waits behind the care branch."""
    r, sv = bleeding_rig(tmp_path, [(12, "Base.RippedSheetsDirty"), (11, "Base.RippedSheets"), (10, "Base.Bandage")])
    hold(r, 30, "Base.WaterBottle", use="water")                                  # the need would drink it
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 5}) and last(tmp_path)["branch"] == "care"
    assert care_why(tmp_path) == {"reason": "bleeding", "part": 5, "item": 10, "kind": "bandage", "bleedingTime": 5.0,
                                  "deep": False}
    (tmp_path / "b").mkdir()
    r2, sv2 = bleeding_rig(tmp_path / "b", [(12, "Base.RippedSheetsDirty"), (11, "Base.RippedSheets")])
    tick(r2, sv2)
    assert r2.cmd() == ("bandage", {"itemId": 11, "part": 5})
    all_sends_valid(r2)


def test_a_dirty_rag_goes_on_only_past_dirty_rag_min_of_bleeding_time(tmp_path):
    r, sv = bleeding_rig(tmp_path, [(12, "Base.RippedSheetsDirty")], bleeding_time=10.0)
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care"                                    # 10.0: not past the rule
    (tmp_path / "b").mkdir()
    r2, sv2 = bleeding_rig(tmp_path / "b", [(12, "Base.RippedSheetsDirty")], bleeding_time=10.5)
    tick(r2, sv2)
    assert r2.cmd() == ("bandage", {"itemId": 12, "part": 5}) and care_why(tmp_path / "b")["kind"] == "dirty"


def test_the_deep_wound_is_bandaged_first_then_the_longest_bleeding(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 10, "Base.Bandage")
    hold(r, 11, "Base.Bandage")
    care_frame(r, [part(3, bleeding=True, bleedingTime=20.0), part(7, bleeding=True, bleedingTime=5.0, deep=True),
                   part(9, bleeding=True, bleedingTime=30.0)])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 7})
    r.answer()
    r.event("item_removed", itemId=10, fullType="Base.Bandage")
    care_frame(r, [part(3, bleeding=True, bleedingTime=20.0),
                   part(7, bandaged=True, bandageLife=3.0, bandageDirty=False),
                   part(9, bleeding=True, bleedingTime=30.0)])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 11, "part": 9})


def test_with_no_rag_an_unworn_cotton_garment_is_ripped_never_one_of_the_first_sight(tmp_path):
    """P24-G 2: no bandage item of any kind held, the bleeding part waits on a rip of a cotton garment; the T-shirt
    the character stood in (the inventory's first sight, between the hello and the first frame) is never asked."""
    r, sv = make(tmp_path)
    hold(r, 20, "Base.Tshirt_WhiteLongSleeveTINT", use="other")                   # the first sight: worn
    r.frame()
    assert r.world.first_sight == {20}
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care"
    hold(r, 21, "Base.Shirt_FormalWhite", use="other")                            # a looted shirt
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 21}) and care_why(tmp_path) == {"reason": "no_rag", "part": 5, "item": 21}
    all_sends_valid(r)


def test_a_rip_refused_worn_marks_the_item_and_it_is_never_asked_again(tmp_path):
    """Named change, Task 10 fix 1 (the review's major 2): the rip is the wound's, so the case bleeds."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 21, "Base.Shirt_FormalWhite", use="other")
    bleeds = [part(5, bleeding=True, bleedingTime=5.0)]
    care_frame(r, bleeds)
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 21})                                    # no rag held: one rip for the wound
    r.answer({"state": "failed", "reason": "worn"})
    for _ in range(3):
        r.advance(1.0)
        care_frame(r, bleeds, game_min=485.0)
        tick(r, sv)
    assert r.world.marked("unrippable") == {21: 485.0} and sum(a.type == "rip" for a in r.acts.history) == 1


def test_a_dirty_rag_is_washed_at_a_known_source_within_wash_r_with_no_zombie_near(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(105, 200, water={"amount": 20.0, "tainted": False, "infinite": True}),
            square(130, 200, water={"amount": 20.0, "tainted": False, "infinite": True})])
    r.frame()
    hold(r, 12, "Base.RippedSheetsDirty")
    care_frame(r, [])
    tick(r, sv)
    assert r.cmd() == ("wash", {"itemId": 12, "x": 105, "y": 200})
    w = care_why(tmp_path)
    assert w["reason"] == "dirty_rag" and w["item"] == 12 and w["source"] == [105, 200]
    all_sends_valid(r)


def test_no_wash_with_a_zombie_within_disengage_r_or_no_source_within_wash_r(tmp_path):
    r, sv = make(tmp_path)
    r.scan([square(105, 200, water={"amount": 20.0, "tainted": False, "infinite": True})])
    r.frame()
    hold(r, 12, "Base.RippedSheetsDirty")
    care_frame(r, [], zombies=[zd(1, 108.0, 200.0, has_target=False)])            # 8 tiles: no threat, not quiet
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care"
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.scan([square(116, 200, water={"amount": 20.0, "tainted": False, "infinite": True})])   # 16 tiles
    r2.frame()
    hold(r2, 12, "Base.RippedSheetsDirty")
    care_frame(r2, [])
    tick(r2, sv2)
    assert last(tmp_path / "b")["branch"] != "care"


def test_a_spent_bandage_is_replaced_with_a_clean_rag(tmp_path):
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 11, "Base.RippedSheets")
    care_frame(r, [part(4, bandaged=True, bandageLife=0.0, bandageDirty=True)])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 11, "part": 4}) and care_why(tmp_path)["reason"] == "spent"
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.frame()
    hold(r2, 12, "Base.RippedSheetsDirty")                                         # no clean one: kept on
    care_frame(r2, [part(4, bandaged=True, bandageLife=0.0, bandageDirty=True)])
    tick(r2, sv2)
    assert last(tmp_path / "b")["branch"] != "care"


def test_the_care_branch_yields_to_a_threat_within_danger_r(tmp_path):
    """The threat branch runs first: a zombie within DANGER_R answers it (the stance) and the running bandage is
    superseded by that send."""
    r, sv = bleeding_rig(tmp_path, [(10, "Base.Bandage")])
    tick(r, sv)
    assert r.cmd()[0] == "bandage"
    bandage = r.acts.history[-1]
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and r.cmd()[0] == "aim" and r.acts.current is not bandage


def test_a_refused_bandage_item_waits_care_retry_min(tmp_path):
    r, sv = bleeding_rig(tmp_path, [(10, "Base.Bandage"), (11, "Base.RippedSheets")])
    tick(r, sv)
    r.answer({"state": "failed", "reason": "not valid"})
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], game_min=480.5)
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 11, "part": 5})                      # 10 held out
    r.answer({"state": "failed", "reason": "not valid"})
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], game_min=481.0)
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care"                                     # both held out
    r.advance(10.0)
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], game_min=482.5)    # 2 minutes after 10's refusal
    for _ in range(10):                                                           # the failed-command cooldown's ticks
        tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 5})


def test_a_pza_1_4_build_is_sent_no_care(tmp_path):
    r, sv = bleeding_rig(tmp_path, [(10, "Base.Bandage")], caps=CAPS_14)
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care"


def test_a_part_record_without_the_care_fields_reads_no_wound(tmp_path):
    """A PZA/1.4 part (`i`, `h` only: the decoded care fields None) is no bleeding part."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 10, "Base.Bandage")
    care_frame(r, [{"i": 5, "h": 60.0}])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care"


# ================================================================ the one mark store (ruling P24-I)
def test_the_world_keeps_one_mark_an_item_with_its_reason_and_the_old_views_read_it(tmp_path):
    """P24-I (the Task 4b review's minor 6): `World.marks` {id: (reason, world minute)} replaces the three stores;
    `empty_ids`, `refused` and `no_effect_ids` are its views, the latest mark wins, an item's removal drops its mark,
    and `to_json` keeps its three fields (a World that never marked one serialises as before)."""
    import json
    from agent.base.world import MARK_REASONS, World
    w = World()
    w.apply({"kind": "frame", "gameMin": 480, "worldAge": 8.0, "wallMs": 0})
    for iid, ft in ((1, "Base.WaterBottle"), (2, "Base.Apple"), (3, "Base.Disinfectant"), (4, "Base.Shirt_FormalWhite")):
        w.apply({"kind": "event", "event": "item_added", "itemId": iid, "fullType": ft, "weight": 0.1})
    base = json.loads(w.to_json())
    assert "emptyIds" not in base and "refusedIds" not in base and "noEffectIds" not in base
    w.mark_empty(1)
    w.mark_refused(2)
    w.mark_no_effect(3)
    w.mark(4, "unrippable")
    assert w.marks == {1: ("empty", 480.0), 2: ("refused", 480.0), 3: ("no_effect", 480.0), 4: ("unrippable", 480.0)}
    assert (w.empty_ids, w.refused, w.no_effect_ids) == ({1}, {2: 480.0}, {3})
    d = json.loads(w.to_json())
    assert (d["emptyIds"], d["refusedIds"], d["noEffectIds"]) == ([1], [2], [3]) and "unrippable" not in w.to_json()
    w.mark_no_effect(1)
    assert w.empty_ids == set() and w.no_effect_ids == {1, 3}
    w.apply({"kind": "event", "event": "item_removed", "itemId": 3, "fullType": "Base.Disinfectant"})
    assert 3 not in w.marks and w.no_effect_ids == {1}
    assert MARK_REASONS[:4] == ("empty", "refused", "no_effect", "unrippable")
    try:
        w.mark(2, "lost")
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown reason is refused")


def test_a_mark_never_fixes_the_gamemin_fallbacks_origin():
    """A mark other than `refused` reads the minute without `world_minutes`' first-read side effect (a frame with
    no worldAge: the fallback's origin is fixed by the first timer that reads it, never by a mark)."""
    from agent.base.world import World
    w = World()
    w.apply({"kind": "frame", "gameMin": 600, "wallMs": 0})
    w.apply({"kind": "event", "event": "item_added", "itemId": 1, "fullType": "Base.WaterBottle", "weight": 0.1})
    w.mark_empty(1)
    assert w.marks[1] == ("empty", None) and w._gm0 is None


def test_the_first_sight_is_the_inventory_between_a_hello_and_the_first_frame():
    from agent.base.world import World
    w = World()
    w.apply({"kind": "hello", "caps": []})
    w.apply({"kind": "event", "event": "item_added", "itemId": 1, "fullType": "Base.Socks_Long", "weight": 0.1})
    w.apply({"kind": "frame", "gameMin": 480, "wallMs": 0})
    w.apply({"kind": "event", "event": "item_added", "itemId": 2, "fullType": "Base.Socks_Long", "weight": 0.1})
    assert w.first_sight == {1}
    w.apply({"kind": "hello", "caps": []})
    assert w.first_sight == set()


def test_no_garment_is_ripped_while_a_rag_is_held(tmp_path):
    """Named change, Task 10 fix 1: a bleeding part, a dirty rag held under DIRTY_RAG_MIN's rule (so it does not go
    on) and no source to wash it: the garment is still not ripped while any rag is held."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 21, "Base.Shirt_FormalWhite", use="other")
    hold(r, 11, "Base.RippedSheetsDirty")
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care" and not any(a.type == "rip" for a in r.acts.history)


def test_no_garment_is_ripped_for_stock_with_no_wound(tmp_path):
    """Task 10 fix 1, the review's major 2 (ruling P24-G 2: the rip is the wound's): no rag of any kind held, a looted
    cotton shirt held and no part bleeding: nothing is ripped, the need's drink goes; the first bleeding part rips it."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 21, "Base.Shirt_FormalWhite", use="other")
    hold(r, 30, "Base.WaterBottle", use="water")
    care_frame(r, [part(5)], thirst=0.5)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 30}) and last(tmp_path)["branch"] == "need"
    assert care_why(tmp_path) == {} and not any(a.type == "rip" for a in r.acts.history)
    r.answer("done")
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 21}) and care_why(tmp_path) == {"reason": "no_rag", "part": 5, "item": 21}


# ================================================================ the water chain (P24-G 3)
from agent.base.planner import view as V   # noqa: E402
from agent.base.planner.goals import ExploreToward, GoalRunner   # noqa: E402
from .test_policies import Rig   # noqa: E402


def need_why(tmp_path):
    return last(tmp_path)["inputs"]["branches"]["need"]


def source(x, y, tainted=False, amount=20.0, infinite=False):
    return square(x, y, water={"amount": amount, "tainted": tainted, "infinite": infinite})


def thirsty(r, **k):
    r.frame(thirst=0.2, **k)


def test_the_water_chain_constants():
    """Named change, Task 10 fix 1 (ruling P24-L): FILL_R is gone with the tainted fallback it bounded."""
    assert (S.FILL_RETRY_MIN, S.THIRST_T, S.FILL_WANTS) == (2.0, 0.12, ("container", "water_source"))
    assert S.SOURCE_FAILS == ("no source", "no water", "not adjacent", "stuck", "no path", "no square")
    assert not hasattr(S, "FILL_R")


def test_a_clean_water_item_is_drunk_before_a_tainted_one_and_a_tainted_one_without(tmp_path):
    """Step 1: the need drinks a held `water` item, a clean one first (one the World knows tainted, `tainted_ids`,
    only with no clean one held), whatever their ids."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 1, "Base.WaterBottle", use="water")
    hold(r, 2, "Base.WaterBottle", use="water")
    r.world.mark(1, "tainted")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 2})
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.frame()
    hold(r2, 1, "Base.WaterBottle", use="water")
    r2.world.mark(1, "tainted")
    thirsty(r2)
    tick(r2, sv2)
    assert r2.cmd() == ("consume", {"itemId": 1})


def test_no_water_held_a_vessel_is_filled_at_the_nearest_clean_source_then_drunk(tmp_path):
    """Step 2: no `water` item, a `container` held: `fill` at the nearest known source (the Lua walks there); its
    done marks the vessel `filled`, which `by_use` reads water, and the next tick drinks it."""
    r, sv = make(tmp_path)
    r.scan([source(110, 200), source(104, 200, amount=0.0), source(120, 200)])     # the dry one is no source
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 110, "y": 200}) and last(tmp_path)["branch"] == "need"
    w = need_why(tmp_path)
    assert w["item"] is None and w["mark"] is None and set(w["fill"]) == {"vessel", "source", "dist"}
    assert w["fill"]["vessel"] == 5 and w["fill"]["source"] == [110, 200]
    all_sends_valid(r)
    assert tick(r, sv) is None                                                   # its fill is current: held
    r.answer({"state": "done", "result": {"amount": 0.5, "added": 0.5, "fluid": "Water", "tainted": False}})
    r.advance(S.FILL_SETTLE_S)                  # 9 fix 2: no item_changed came: the settle time reads it filled
    thirsty(r)
    tick(r, sv)
    assert r.world.marks[5][0] == "filled" and r.world.by_use()["water"] == [5]
    assert r.cmd() == ("consume", {"itemId": 5})


def test_a_tainted_source_is_never_filled_from_a_clean_one_at_any_distance_is(tmp_path):
    """Ruling P24-L (Task 10 fix 1, the review's major 1; re-cut from Task 10's FILL_R fallback): the Lua refuses every
    tainted drink, so only a clean source is filled from, at any distance; with only a tainted one known the vessel
    is kept (still a `container`), nothing is sent, and the want names `water_source` (not `container`)."""
    r, sv = make(tmp_path)
    r.scan([source(105, 200, tainted=True, infinite=True), source(160, 200)])     # clean at 60.5 tiles
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 160, "y": 200})
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.scan([source(105, 200, tainted=True, infinite=True)])
    r2.frame()
    hold(r2, 5, "Base.PopEmpty", use="container")
    for _ in range(3):
        thirsty(r2)
        tick(r2, sv2)
    assert not any(a.type == "fill" for a in r2.acts.history) and r2.world.by_use()["container"] == [5]
    assert need_why(tmp_path / "b")["fill"] == {"vessel": 5, "source": None, "want": "water_source"}
    assert set(sv2.need_marks) == {"water", "water_source"}
    assert V.view(r2.world, sv2)["needs_wanted"] == ["water", "water_source"]


def test_a_fill_refused_for_its_water_leaves_the_source_out(tmp_path):
    r, sv = make(tmp_path)
    r.scan([source(105, 200), source(110, 200)])
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    hold(r, 6, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 105, "y": 200})
    r.answer({"state": "failed", "reason": "no water"})
    thirsty(r)
    tick(r, sv)
    # named change, Task 10 fix 1 (minor 5): a failure for its source frees the vessel for the next source at once
    assert r.cmd() == ("fill", {"itemId": 5, "x": 110, "y": 200}) and r.world.dry_now() == {(105, 200, 0)}


@pytest.mark.parametrize("end", [{"state": "failed", "reason": "not adjacent"}, {"state": "failed", "reason": "stuck"},
                                 "timeout"])
def test_a_fill_whose_walk_failed_leaves_its_source_out_and_takes_the_next(tmp_path, end):
    """Task 10 fix 1, minor 5: a walk to the source that failed (`not adjacent`, a stuck reason, or the fill timed out
    on the Actions deadline) leaves the source out as a dry one does, and the vessel goes to the next source."""
    r, sv = make(tmp_path)
    r.scan([source(105, 200), source(110, 200)])
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 105, "y": 200})
    if end == "timeout":
        r.fake.answer({"fill": ["accepted"]})
        r.pump()
        r.advance(31.0)
        r.pump()
        assert r.acts.history[-1].state == "timeout"
    else:
        r.answer(end)
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 110, "y": 200}) and r.world.dry_now() == {(105, 200, 0)}


def test_a_vessel_whose_fill_failed_otherwise_waits_fill_retry_min_from_the_end_and_no_container_is_wanted(tmp_path):
    """Task 10 fix 1, minor 5: an `interrupted` fill (queued, nothing rose) holds the vessel out FILL_RETRY_MIN game
    minutes counted from the minute its end was read (never from the send); meanwhile a vessel is held, so no
    `container` want is marked (`fill_why` names it held out), and the source stays a source."""
    r, sv = make(tmp_path)
    r.scan([source(105, 200)])
    r.frame(game_min=480.0)
    hold(r, 5, "Base.PopEmpty", use="container")
    thirsty(r, game_min=480.0)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 105, "y": 200})
    r.fake.answer({"fill": ["accepted"]})
    r.pump()
    thirsty(r, game_min=481.5)                       # the walk and the queue: 1.5 game minutes
    r.answer({"state": "failed", "reason": "interrupted"})
    thirsty(r, game_min=481.5)
    tick(r, sv)
    assert need_why(tmp_path)["fill"] == {"held_out": [5]} and set(sv.need_marks) == {"water"}
    thirsty(r, game_min=483.4)                       # 1.9 minutes from the end (3.4 from the send): still out
    tick(r, sv)
    assert need_why(tmp_path)["fill"] == {"held_out": [5]} and not r.world.dry_now()
    for _ in range(S.FAILED_COOLDOWN_TICKS):         # the same command's failure cooldown, past the hold-out
        thirsty(r, game_min=483.5)
        tick(r, sv)
    assert [a.args for a in r.acts.history if a.type == "fill"][1:] == [{"itemId": 5, "x": 105, "y": 200}]


def test_no_vessel_held_the_container_want_is_marked_for_the_goal_layer(tmp_path):
    """Step 3: no water and no vessel held: the water want and the container want are marked (`need_marks`), the
    view lists both in `needs_wanted`, and a known empty vessel in a container is named in `stock_uses`."""
    r, sv = make(tmp_path)
    r.scan([source(105, 200), square(102, 200, containers=[{"type": "counter", "n": 1, "items": ["Base.PopEmpty"]}])])
    thirsty(r)
    tick(r, sv)
    w = need_why(tmp_path)
    assert w["mark"] == "water" and w["fill"] == {"want": "container"} and set(sv.need_marks) == {"water", "container"}
    v = V.view(r.world, sv)
    assert v["needs_wanted"] == ["water", "container"] and "container" in v["stock_uses"]
    hold(r, 7, "Base.WaterBottle", use="water")
    thirsty(r)
    tick(r, sv)
    assert "container" not in sv.need_marks and "water" not in sv.need_marks


def test_a_vessel_with_no_source_known_marks_the_water_source_want(tmp_path):
    """Named change, Task 10 fix 1 (ruling P24-L): a vessel and no clean source known marks `water_source` beside
    `water` (the goal layer's to find), never `container`; a vessel lost marks `container` and drops it."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert need_why(tmp_path)["fill"] == {"vessel": 5, "source": None, "want": "water_source"}
    assert set(sv.need_marks) == {"water", "water_source"}
    r.event("item_removed", itemId=5)
    thirsty(r)
    tick(r, sv)
    assert set(sv.need_marks) == {"water", "container"}


def test_a_pza_1_4_build_is_sent_no_fill(tmp_path):
    r, sv = make(tmp_path, caps=CAPS_14)
    r.scan([source(105, 200)])
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert not any(a.type == "fill" for a in r.acts.history) and "fill" not in need_why(tmp_path)


# ================================================================ the climb in routes (P24-G 4)
class Src:
    NAME = "test"

    def __init__(self, goal):
        self.goal = goal

    def propose(self, view):
        g, self.goal = self.goal, None
        return g


def fenced(hop=True):
    """A yard x 98..112, y 196..204, a fence on the west edge of the squares x 102 (blocked, hoppable unless `hop`
    is False: a wall)."""
    return [square(x, y, blockW=(x == 102), hopW=(x == 102 and hop)) for x in range(98, 113) for y in range(196, 205)]


def walk_stuck(r, g, me=(101.5, 200.5)):
    r.frame(x=me[0], y=me[1])
    runner = GoalRunner(Src(g), r.clock)
    runner.kit.bind(r.world, r.acts)
    runner.kit.explore.scanned.add(runner.kit.explore.place())   # the place is scanned already
    runner.send(runner.tick(r.world, r.acts))
    assert r.cmd()[0] == "walkTo"
    r.answer({"state": "failed", "reason": "stuck"})
    r.frame(x=me[0], y=me[1])
    return runner, runner.tick(r.world, r.acts)


def test_a_walk_stuck_at_a_hoppable_edge_climbs_it_then_walks_on(tmp_path):
    """P24-G 4: the explicit climb only where the walk failed `stuck` and the route's next edge (the line's first
    step from the player's square) is hoppable: `climb` of the fence's square (the edge's holder, x 102), then the
    walk again once the climb ends done."""
    r = Rig(tmp_path)
    r.scan(fenced())
    g = ExploreToward(110, 200)
    runner, cmd = walk_stuck(r, g)
    assert g.state == "running" and (cmd.TYPE, cmd.args()) == ("climb", {"x": 102, "y": 200})
    assert (110, 200) in r.world.stuck                                           # Explore marked the stuck walk's target
    runner.send(cmd)
    r.answer()
    r.frame(x=102.5, y=200.5)
    cmd = runner.tick(r.world, r.acts)
    assert (cmd.TYPE, cmd.args()) == ("walkTo", {"x": 110, "y": 200, "gait": "walk"})
    assert (110, 200) not in r.world.stuck                                       # minor 9: the climb crossed it
    all_sends_valid(r)


def test_a_walk_stuck_at_a_wall_or_far_from_the_fence_never_climbs(tmp_path):
    r = Rig(tmp_path)
    r.scan(fenced(hop=False))
    g = ExploreToward(110, 200)
    _, cmd = walk_stuck(r, g)
    assert cmd is None and (g.state, g.reason) == ("failed", "stuck")
    (tmp_path / "b").mkdir()
    r2 = Rig(tmp_path / "b")
    r2.scan(fenced())
    g2 = ExploreToward(110, 200)
    _, cmd = walk_stuck(r2, g2, me=(99.5, 200.5))                                # the fence two squares on
    assert cmd is None and (g2.state, g2.reason) == ("failed", "stuck")


def test_a_failed_climb_fails_the_goal_and_a_pza_1_4_build_never_climbs(tmp_path):
    r = Rig(tmp_path)
    r.scan(fenced())
    g = ExploreToward(110, 200)
    runner, cmd = walk_stuck(r, g)
    runner.send(cmd)
    r.answer({"state": "failed", "reason": "fell"})
    r.frame(x=101.5, y=200.5)
    runner.tick(r.world, r.acts)
    assert (g.state, g.reason) == ("failed", "fell")
    (tmp_path / "b").mkdir()
    r2 = Rig(tmp_path / "b", caps=CAPS_14)
    r2.scan(fenced())
    g2 = ExploreToward(110, 200)
    _, cmd = walk_stuck(r2, g2)
    assert cmd is None and (g2.state, g2.reason) == ("failed", "stuck")


def test_hop_ahead_reads_the_first_step_its_holder_and_a_diagonal_through_an_open_corner(tmp_path):
    r = Rig(tmp_path)
    r.scan(fenced() + [square(101, 195, blockN=True, hopN=True)])
    r.frame(x=101.5, y=200.5)
    w = r.world
    assert w.hop_ahead((101.5, 200.5), (110.5, 200.5)) == (102, 200)               # east: the holder is the far square
    assert w.hop_ahead((102.5, 200.5), (95.5, 200.5)) == (102, 200)                # west: the holder is its own square
    assert w.hop_ahead((101.5, 200.5), (110.5, 209.5)) == (102, 200)               # a diagonal through (101, 201)
    assert w.hop_ahead((100.5, 200.5), (110.5, 200.5)) is None                     # the fence one square on
    assert w.hop_ahead((103.5, 200.5), (110.5, 200.5)) is None                     # no fence on the line


def test_no_route_ever_vaults_the_steer_probe_reads_a_hoppable_edge_blocked(tmp_path):
    """The sprint's legs and the stance's backpedal read `clear_heading` (`line_clear`, which never climbs): a
    heading over a hoppable fence is blocked, so a flee leg turns off it (Task 1b's rule, kept)."""
    r = Rig(tmp_path)
    r.scan(fenced())
    r.frame(x=101.5, y=200.5)
    assert not P.clear_heading(r.world, (1.0, 0.0)) and P.clear_heading(r.world, (-1.0, 0.0))
    assert r.world.reachable((101, 200, 0), (104, 200, 0))                        # a walk's flood climbs it


def test_the_world_applies_item_changed_and_drops_a_vessel_mark(tmp_path):
    """PZA/1.5.1's `item_changed` (Task 9 fix 1): the held item's use, fluid and amount from then on; a vessel-state
    mark (`filled`, `tainted`, `empty`) gives way to the engine's read, the others stay."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    hold(r, 6, "Base.Disinfectant", use="other")
    r.world.mark(5, "filled")
    r.world.mark_no_effect(6)
    r.event("item_changed", itemId=5, use="other", fluid="TaintedWater", amount=0.5)
    r.event("item_changed", itemId=6, use="other", amount=0.2)
    assert r.world.inventory[5]["use"] == "other" and r.world.inventory[5]["fluid"] == "TaintedWater"
    assert 5 not in r.world.marks and r.world.marks[6][0] == "no_effect" and r.world.tainted_ids() == {5}
    r.event("item_changed", itemId=5, use="container", amount=0.0)
    assert "fluid" not in r.world.inventory[5] and r.world.by_use()["container"] == [5]


def test_a_tainted_drink_refused_marks_it_undrinkable_and_the_tainted_source_is_never_filled_from(tmp_path):
    """Re-cut, Task 10 fix 1 (ruling P24-L): a held bottle of tainted water (a looted one: its record names
    TaintedWater) is drunk only with no clean one, the Lua refuses it (`W.drinkable`), it is marked `undrinkable`
    (read `other`), and the held vessel is never filled at the tainted source the map knows: it is kept, and the want
    names `water_source`."""
    r, sv = make(tmp_path)
    r.scan([source(105, 200, tainted=True, infinite=True)])
    r.frame()
    hold(r, 5, "Base.WaterBottle", use="water")
    r.event("item_changed", itemId=5, use="water", fluid="TaintedWater", amount=0.5)
    hold(r, 6, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 5})
    r.answer({"state": "failed", "reason": "not valid"})
    for _ in range(3):
        thirsty(r)
        tick(r, sv)
    assert r.world.marks[5][0] == "undrinkable" and r.world.by_use()["other"] == [5]
    assert r.world.by_use()["container"] == [6] and not any(a.type == "fill" for a in r.acts.history)
    assert need_why(tmp_path)["fill"] == {"vessel": 6, "source": None, "want": "water_source"}


# ================================================================ Task 9 fix 2: the planner's side of item_changed
def test_item_changed_moves_a_vessel_between_container_and_water_and_clears_its_mark(tmp_path):
    """Item 1: a fill's event moves a `container` to `water` (the amount and fluid kept) and clears an `empty` mark; a
    drink to empty moves `water` back to `container`; an id not held is ignored."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    r.world.mark_empty(5)
    r.event("item_changed", itemId=5, use="water", fluid="Water", amount=0.5)
    assert r.world.by_use()["water"] == [5] and 5 not in r.world.marks
    assert r.world.inventory[5]["amount"] == 0.5 and r.world.inventory[5]["fluid"] == "Water"
    r.event("item_changed", itemId=5, use="container", amount=0.0)
    assert r.world.by_use()["container"] == [5] and r.world.by_use()["water"] == []
    before = dict(r.world.inventory)
    r.event("item_changed", itemId=99, use="water", fluid="Water", amount=1.0)
    assert r.world.inventory == before and 99 not in r.world.changes and r.world.missing_items == 0


def test_mark_empty_moves_a_drinkable_vessel_to_container_not_other(tmp_path):
    """Item 2: for the ticks before the event arrives (and on a log without it) an emptied bottle is a vessel."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 5, "Base.WaterBottle", use="water")
    hold(r, 6, "Base.Disinfectant", use="other")
    r.world.mark_empty(5)
    r.world.mark_empty(6)
    u = r.world.by_use()
    assert u["container"] == [5] and u["water"] == [] and u["other"] == [6]


def fill_rig(tmp_path, sources=(110,)):
    r, sv = make(tmp_path)
    r.scan([source(x, 200, infinite=True) for x in sources])
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd()[0] == "fill"
    return r, sv


def test_a_done_fill_waits_for_its_item_changed_before_the_drink(tmp_path):
    """Item 3: done at t0: the need holds (settling), then drinks once the vessel's event reads it water."""
    assert S.FILL_SETTLE_S == 2.0
    r, sv = fill_rig(tmp_path)
    r.answer({"state": "done", "result": {"amount": 0.5, "added": 0.5, "fluid": "Water", "tainted": False}})
    thirsty(r)
    assert tick(r, sv) is None and need_why(tmp_path) == {"settling": 5} and 5 not in r.world.marks
    r.advance(1.0)
    thirsty(r)
    assert tick(r, sv) is None and need_why(tmp_path) == {"settling": 5}
    r.event("item_changed", itemId=5, use="water", fluid="Water", amount=0.5)
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 5}) and 5 not in r.world.marks and not sv.fills


def test_a_done_fill_with_no_event_reads_filled_after_fill_settle_s(tmp_path):
    r, sv = fill_rig(tmp_path)
    r.answer({"state": "done", "result": {"amount": 0.5, "added": 0.5, "fluid": "Water", "tainted": False}})
    thirsty(r)
    tick(r, sv)
    r.advance(S.FILL_SETTLE_S - 0.5)
    thirsty(r)
    assert tick(r, sv) is None and 5 not in r.world.marks
    r.advance(0.5)
    thirsty(r)
    tick(r, sv)
    assert r.world.marks[5][0] == "filled" and r.cmd() == ("consume", {"itemId": 5})


def test_a_tainted_fill_marks_its_source_square_tainted_and_the_next_fill_takes_another(tmp_path):
    """Item 3: a fill that read TaintedWater (the event, use other) from a source the map read clean puts that square
    in the World's `tainted_sources`; `water_sources` then reads it tainted and the next fill takes the clean one."""
    r, sv = make(tmp_path)
    r.scan([source(110, 200), source(120, 200)])
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    hold(r, 6, "Base.PopEmpty", use="container")
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 110, "y": 200})
    r.answer({"state": "done", "result": {"amount": 0.5, "added": 0.5, "fluid": "TaintedWater"}})
    r.event("item_changed", itemId=5, use="other", fluid="TaintedWater", amount=0.5)
    thirsty(r)
    tick(r, sv)
    assert r.world.tainted_sources == {(110, 200, 0)} and r.world.tainted_ids() == {5}
    assert [(s[1], s[2].get("tainted")) for s in r.world.water_sources(math.inf)] == [((110, 200, 0), True),
                                                                                       ((120, 200, 0), False)]
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 5})
    r.answer({"state": "failed", "reason": "not valid"})
    thirsty(r)
    tick(r, sv)
    thirsty(r)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 6, "x": 120, "y": 200})


def test_the_event_after_a_drink_leaves_the_no_effect_mark_of_the_consume_check(tmp_path):
    """Item 3: the no-effect check is anchored on the consume's done; the drink's item_changed lands about a second
    later and clears no `no_effect` mark."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 7, "Base.WaterBottle", use="water")
    thirsty(r, game_min=480.0)
    tick(r, sv)
    assert r.cmd() == ("consume", {"itemId": 7})
    r.answer("done")
    thirsty(r, game_min=482.0)                      # no fall in thirst
    tick(r, sv)
    r.event("item_changed", itemId=7, use="water", fluid="Water", amount=0.9)
    thirsty(r, game_min=483.0)
    tick(r, sv)
    assert r.world.marks[7][0] == "no_effect" and r.world.by_use()["other"] == [7]


def test_a_bandage_refused_in_bag_is_marked_and_never_retried(tmp_path):
    """Named change, Task 10 fix 2 (item 3): the Lua moves a bag item itself now (PZA/1.5.2), so in bag means the
    move could not be queued: a hard refusal, the item marked in_bag for good."""
    r, sv = bleeding_rig(tmp_path, [(10, "Base.Bandage")])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 5})
    r.answer({"state": "failed", "reason": "in bag"})
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], game_min=480.5)
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care" and r.world.marks[10][0] == "in_bag"
    r.advance(10.0)
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], game_min=482.5)
    for _ in range(10):
        tick(r, sv)
    assert sum(a.type == "bandage" for a in r.acts.history) == 1


def test_a_wash_refused_in_bag_is_marked_never_retried_and_leaves_its_source(tmp_path):
    """Named change, Task 10 fix 2 (item 3): in bag is final for a wash too."""
    r, sv = make(tmp_path)
    r.scan([square(105, 200, water={"amount": 20.0, "tainted": False, "infinite": True})])
    r.frame()
    hold(r, 12, "Base.RippedSheetsDirty")
    care_frame(r, [])
    tick(r, sv)
    assert r.cmd() == ("wash", {"itemId": 12, "x": 105, "y": 200})
    r.answer({"state": "failed", "reason": "in bag"})
    care_frame(r, [], game_min=480.5)
    tick(r, sv)
    assert not r.world.dry and r.world.marks[12][0] == "in_bag" and last(tmp_path)["branch"] != "care"
    r.advance(10.0)
    care_frame(r, [], game_min=482.5)
    for _ in range(10):
        tick(r, sv)
    assert sum(a.type == "wash" for a in r.acts.history) == 1


def test_the_ripped_sheets_read_bandage_a_sealed_can_other_and_the_choice_order_holds(tmp_path):
    """Item 5: `RippedSheets` and the other CanBandage items count `bandage`, `Base.Pop2` (sealed) `other`; within the
    `bandage` use the care branch still reads the name: bandage > clean rag > dirty rag."""
    r, sv = make(tmp_path)
    r.frame()
    for iid, ft in ((1, "Base.RippedSheets"), (2, "Base.RippedSheetsDirty"), (3, "Base.Bandage"),
                    (4, "Base.DenimStrips"), (5, "Base.Pop2")):
        r.event("item_added", itemId=iid, fullType=ft, weight=0.1)       # no `use` on the line: the dataset answers
    care_frame(r, [part(5, bleeding=True, bleedingTime=20.0)])
    v = V.view(r.world, sv)
    assert v["inventory_by_use"]["bandage"] == 4 and v["inventory_by_use"]["other"] == 1
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 3, "part": 5})
    for iid in (3, 1, 4):                                                # then the clean rags, the dirty one last
        r.event("item_removed", itemId=iid)
        r.answer("done")
        care_frame(r, [part(5, bleeding=True, bleedingTime=20.0)])
        tick(r, sv)                                                      # named change, Task 10 fix 1 (minor 6):
        care_frame(r, [part(5, bleeding=True, bleedingTime=20.0)])       # the part waits one frame newer than the
        tick(r, sv)                                                      # one read with its bandage's done
        assert r.cmd()[1]["itemId"] == {3: 1, 1: 4, 4: 2}[iid]


# ================================================================ Task 10 fix 1: the review's minors
def test_a_stance_leg_superseded_re_aims_but_one_that_fails_ends_the_stand_at_once(tmp_path):
    """Minor 11: a stance leg that ends failed (here `not loaded`: a build that cannot take the stance) or times out
    sets `standoff` at once, so the next choose is the approach walk rather than STAND_MAX_S of re-sent legs; a
    superseded leg (this planner's own next send) re-aims; named change (P24-N): STAND_MAX_S is no fallback any
    more, the stand closes in the stance (`advance`) and `standoff` stays unset."""
    for k, end in enumerate(({"state": "failed", "reason": "not loaded"}, "timeout")):
        (tmp_path / str(k)).mkdir()
        r, sv = make(tmp_path / str(k))
        r.frame(zombies=[zd(1, 104.0, 200.0)])
        tick(r, sv)
        assert r.cmd()[0] == "aim"
        if end == "timeout":
            r.fake.answer({"aim": ["accepted"]})
            r.pump()
            r.advance(31.0)
            r.pump()
        else:
            r.answer(end)
        r.frame(zombies=[zd(1, 104.0, 200.0)])
        tick(r, sv)
        assert r.cmd() == ("walkTo", {"x": 104.5, "y": 200.5, "gait": "run"}) and sv.fight.standoff
        assert sv.fight.standoff_why == ("failed not loaded" if k == 0 else "timeout")
    (tmp_path / "s").mkdir()
    r, sv = make(tmp_path / "s")
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    r.answer({"state": "failed", "reason": "superseded"})
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    assert r.cmd()[0] == "aim" and not sv.fight.standoff and sv.fight.standoff_why is None
    stand_legs(r, sv, 10)
    assert not sv.fight.standoff and sv.fight.advance and sv.fight.standoff_why is None


def test_a_bandaged_part_waits_one_frame_newer_than_its_done_before_it_is_bandaged_again(tmp_path):
    """Minor 6: the bandage's done read before a frame reads it on (the stale frame still lists part 5 bleeding and
    unbandaged) puts no second item on the wound; a newer frame that reads it bandaged ends the wait, and one that
    still reads it bleeding (the bandage did not take) is bandaged again."""
    r, sv = bleeding_rig(tmp_path, [(10, "Base.Bandage"), (11, "Base.Bandage")])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 5})
    r.event("item_removed", itemId=10)
    r.answer("done")
    tick(r, sv)                                                                  # the stale frame: part 5 waits
    assert sum(a.type == "bandage" for a in r.acts.history) == 1 and sv.care.fresh == {5: r.world.frame_n}
    care_frame(r, [part(5, bandaged=True, bandageLife=1.0)])
    tick(r, sv)
    assert sum(a.type == "bandage" for a in r.acts.history) == 1 and not sv.care.fresh
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 11, "part": 5})


def test_care_is_a_policy_and_reads_quiet_from_survive(tmp_path):
    """Minor 13: `Care(Policy)`: the house's busy and send, its own `sent` recording each item's action; Survive sets
    `quiet` each tick (no zombie within DISENGAGE_R) before `choose()`."""
    assert issubclass(C.Care, P.Policy)
    assert C.Care.busy is P.Policy.busy and C.Care.send is P.Policy.send and C.Care.sent is not P.Policy.sent
    r, sv = bleeding_rig(tmp_path, [(10, "Base.Bandage")])
    tick(r, sv)
    assert sv.care.quiet is True and sv.care.sends[10] is sv.care.last and sv.care.busy()


def test_the_water_squares_are_memoised_on_the_map_version_and_the_dry_store_is_the_worlds(tmp_path):
    """Minors 4 and 14: the World holds the water squares (one map walk per map version, never per tick) and the dry
    store the wash and the fill share (`mark_dry`, SOURCE_RETRY_MIN game minutes)."""
    from agent.base import world as W
    r = Rig(tmp_path)
    r.scan([source(105, 200), square(106, 200)])
    r.frame()
    w = r.world
    first = w.water_squares()
    assert first is w.water_squares() and [sq for sq, _ in first] == [(105, 200, 0)]
    r.fake.map_full([source(110, 200)], scan_id=2)
    r.pump()
    assert w.water_squares() is not first and [sq for sq, _ in w.water_squares()] == [(105, 200, 0), (110, 200, 0)]
    w.mark_dry((105, 200, 0))
    assert [s[1] for s in w.water_sources()] == [(110, 200, 0)] and w.dry_now() == {(105, 200, 0)}
    r.frame(game_min=480.0 + W.SOURCE_RETRY_MIN)
    assert [s[1] for s in w.water_sources()] == [(105, 200, 0), (110, 200, 0)] and w.dry_now() == set()
    assert [s[1] for s in w.water_sources(6.0)] == [(105, 200, 0)]


def test_by_use_is_read_once_a_tick(tmp_path):
    """Minor 14: the need's pick, its retry window and the fill read one `by_use()` a tick."""
    r, sv = make(tmp_path)
    r.scan([source(110, 200)])
    r.frame()
    hold(r, 5, "Base.PopEmpty", use="container")
    hold(r, 6, "Base.Apple", use="food")
    calls = []
    real = r.world.by_use
    r.world.by_use = lambda: calls.append(1) or real()
    thirsty(r, hunger=0.5)
    tick(r, sv)
    assert r.cmd() == ("fill", {"itemId": 5, "x": 110, "y": 200}) and len(calls) == 1


def shelter_yard(fence_hop=True):
    """test_night's house 1 at x 110 (its door on the west edge of (110, 201), the approach square (109, 201)) with
    open ground x 104..109 by y 199..203 in front, a fence on the west edges of the squares x 108 (blocked, hoppable
    unless `fence_hop` is False)."""
    from .test_night import house
    sqs = [s for s in house(1, 110) if s["x"] >= 110]
    return sqs + [square(x, y, blockW=(x == 108), hopW=(x == 108 and fence_hop))
                  for x in range(104, 110) for y in range(199, 204)]


def test_the_shelter_walk_climbs_a_fence_on_its_route_and_walks_on(tmp_path):
    """Minor 9: the Shelter goal's approach walk failed `stuck` at a hoppable edge on its line's first step climbs it
    (`Kit.hop_after`, the step kept at `approach`) and walks the approach again once the climb ends done; a climb that
    fails is read as that walk's stuck end (one door: the machine shuns the building)."""
    from agent.base.planner.goals import Shelter
    for k, climb_end in enumerate(("done", {"state": "failed", "reason": "fell"})):
        (tmp_path / str(k)).mkdir()
        r = Rig(tmp_path / str(k))
        r.scan(shelter_yard())
        r.frame(x=107.5, y=201.5)
        g = Shelter(1)
        runner = GoalRunner(Src(g), r.clock)
        runner.send(runner.tick(r.world, r.acts))
        assert r.cmd() == ("walkTo", {"x": 109.5, "y": 201.5, "gait": "walk"})
        r.answer({"state": "failed", "reason": "stuck"})
        r.frame(x=107.5, y=201.5)
        cmd = runner.tick(r.world, r.acts)
        assert (cmd.TYPE, cmd.args()) == ("climb", {"x": 108, "y": 201}) and g.plan["step"] == "approach"
        assert g.why["step"] == "climb" and g.state == "running"
        runner.send(cmd)
        r.answer(climb_end)
        r.frame(x=108.5, y=201.5)
        cmd = runner.tick(r.world, r.acts)
        if k == 0:
            assert (cmd.TYPE, cmd.args()) == ("walkTo", {"x": 109.5, "y": 201.5, "gait": "walk"})
            assert g.why["step"] == "approach"
            all_sends_valid(r)
        else:
            assert cmd is None and (g.state, g.reason) == ("failed", "shun") and 1 in runner.kit.shunned


def test_the_shelter_walk_stuck_at_a_wall_shuns_as_before(tmp_path):
    from agent.base.planner.goals import Shelter
    r = Rig(tmp_path)
    r.scan(shelter_yard(fence_hop=False))
    r.frame(x=107.5, y=201.5)
    g = Shelter(1)
    runner = GoalRunner(Src(g), r.clock)
    runner.send(runner.tick(r.world, r.acts))
    r.answer({"state": "failed", "reason": "stuck"})
    r.frame(x=107.5, y=201.5)
    assert runner.tick(r.world, r.acts) is None and (g.state, g.reason) == ("failed", "shun")
    assert not any(a.type == "climb" for a in r.acts.history)


# ================================================================ Task 10 fix 2: worn, rip and moved (PZA/1.5.2)
def hello152(r):
    """A PZA/1.5.2 hello (the fake's default mod is "fake": an unparsable version, so the pre-1.5.2 guess)."""
    r.fake.hello(mod="1.5.2")
    r.pump()


def garment(r, iid, ft="Base.Shirt_FormalWhite", **k):
    r.event("item_added", itemId=iid, fullType=ft, weight=0.1, use="other", **k)


def test_item_fields_read_the_hellos_mod_version(tmp_path):
    from agent.base.world import World
    r, _ = make(tmp_path)
    assert r.world.item_fields() is False                                         # "fake": the guess stays
    for mod, want in (("1.5.1", False), ("1.5.2", True), ("1.6.0", True), ("2.0.0", True), ("", False)):
        w = World()
        w.apply({"kind": "hello", "mod": mod, "caps": []})
        assert w.item_fields() is want, mod
    assert World().item_fields() is False


def test_a_worn_garment_on_a_1_5_2_log_is_never_asked_and_an_unworn_one_after_the_hello_is(tmp_path):
    """Task 10 fix 2, item 1: the record worn replaces the first-sight guess; a garment first seen after the
    hello with worn absent is a candidate, even one inside the old first-sight window."""
    r, sv = make(tmp_path)
    hello152(r)
    garment(r, 20, rip="cotton", worn=True)                                       # in the window, worn
    garment(r, 22, rip="cotton")                                                  # in the window, not worn
    r.frame()
    assert r.world.first_sight == {20, 22} and r.world.inventory[20]["worn"] is True
    assert "worn" not in r.world.inventory[22]
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 22}) and care_why(tmp_path)["item"] == 22   # 20 is lower and never asked
    all_sends_valid(r)
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    hello152(r2)
    r2.frame()
    garment(r2, 20, rip="cotton", worn=True)
    care_frame(r2, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r2, sv2)
    assert last(tmp_path / "b")["branch"] != "care" and not any(a.type == "rip" for a in r2.acts.history)


def test_item_changed_states_worn_again_and_a_garment_taken_off_becomes_a_candidate(tmp_path):
    r, sv = make(tmp_path)
    hello152(r)
    r.frame()
    garment(r, 21, rip="cotton", worn=True)
    r.event("item_changed", itemId=21, use="other", rip="cotton")                 # taken off: worn absent
    assert "worn" not in r.world.inventory[21] and r.world.inventory[21]["rip"] == "cotton"
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 21})


@pytest.mark.parametrize("rip, asked", [("cotton", True), ("denim", False), ("leather", False), (None, False)])
def test_only_a_cotton_rip_class_is_asked_on_a_1_5_2_log_whatever_the_name(tmp_path, rip, asked):
    """Task 10 fix 2, item 2: cotton can run; denim and leather need a tool the planner has no action for; absent
    is no class. The name decides nothing: a shirt named so with no class is never asked, a pair of jeans classed
    cotton is."""
    r, sv = make(tmp_path)
    hello152(r)
    r.frame()
    ft = "Base.Trousers_Denim" if rip == "cotton" else "Base.Shirt_FormalWhite"
    garment(r, 21, ft=ft, **({"rip": rip} if rip else {}))
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r, sv)
    if asked:
        assert r.cmd() == ("rip", {"itemId": 21})
    else:
        assert not any(a.type == "rip" for a in r.acts.history)


def test_a_pre_1_5_2_log_keeps_the_name_guess_and_the_first_sight(tmp_path):
    """The guess stays for older logs: a hello naming 1.5.1 reads the name regex, the inventory first sight is left
    out, and a rip class on a record is ignored there."""
    r, sv = make(tmp_path)
    r.fake.hello(mod="1.5.1")
    r.pump()
    garment(r, 20)
    r.frame()
    garment(r, 21, ft="Base.Trousers_Denim")
    garment(r, 22, ft="Base.Shirt_FormalWhite", rip="denim")
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r, sv)
    assert r.cmd() == ("rip", {"itemId": 22})                                     # 20 first sight, 21 named denim


@pytest.mark.parametrize("kind", ["bandage", "rip"])
def test_an_in_bag_refusal_is_final_the_item_is_marked_and_never_asked_again(tmp_path, kind):
    """Task 10 fix 2, item 3: in bag means the move could not be queued: marked in_bag, not retried each
    CARE_RETRY_MIN; the next item of the kind goes instead, and a removal drops the mark."""
    r, sv = make(tmp_path)
    hello152(r)
    r.frame()
    if kind == "bandage":
        hold(r, 10, "Base.Bandage")
        hold(r, 11, "Base.Bandage")
    else:
        garment(r, 10, rip="cotton")
        garment(r, 11, rip="cotton")
    bleeds = [part(5, bleeding=True, bleedingTime=5.0)]
    care_frame(r, bleeds)
    tick(r, sv)
    assert r.cmd()[0] == kind and r.cmd()[1]["itemId"] == 10
    r.answer({"state": "failed", "reason": "in bag"})
    care_frame(r, bleeds, game_min=481.0)
    tick(r, sv)
    assert r.world.marked("in_bag").keys() == {10} and r.cmd()[1]["itemId"] == 11   # 10 is not asked again
    r.answer({"state": "failed", "reason": "in bag"})
    for m in (483.0, 490.0, 600.0):                                                # far past CARE_RETRY_MIN
        care_frame(r, bleeds, game_min=m)
        tick(r, sv)
    assert sum(a.type == kind and a.args["itemId"] == 10 for a in r.acts.history) == 1
    assert sum(a.type == kind and a.args["itemId"] == 11 for a in r.acts.history) == 1
    r.event("item_removed", itemId=10, fullType="Base.Bandage")
    assert 10 not in r.world.marks


def test_a_bandage_that_moved_a_bag_item_is_done_and_the_moved_items_first_appearance_is_no_pickup(tmp_path):
    """Task 10 fix 2, item 3: the Lua moves the item to the main inventory first (its item_added arrives before the
    bandage item_removed) and reports moved true; the planner reads an ordinary done. The planner never saw bag
    items and nothing in it counts an item_added as a pickup (loot results come from the interact act moved, the
    view lists raw event names): the sequence leaves no residue in the inventory, the containers or the
    missing-items count."""
    r, sv = make(tmp_path)
    hello152(r)
    r.frame()
    bleeds = [part(5, bleeding=True, bleedingTime=5.0)]
    care_frame(r, bleeds)
    tick(r, sv)                                                                   # nothing held: no care command
    assert not any(a.type in ("bandage", "rip") for a in r.acts.history)
    hold(r, 40, "Base.Bandage")                                                   # it came out of a bag
    care_frame(r, bleeds, game_min=481.0)
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 40, "part": 5})
    r.answer({"state": "done", "result": {"part": 5, "dirty": False, "life": 3.5, "moved": True}})
    r.event("item_removed", itemId=40, fullType="Base.Bandage")
    care_frame(r, [part(5, bandaged=True, bandageLife=3.5, bandageDirty=False)], game_min=482.0)
    tick(r, sv)
    assert 40 not in r.world.inventory and r.world.missing_items == 0 and not r.world.marks
    assert sum(a.type == "bandage" for a in r.acts.history) == 1 and last(tmp_path)["branch"] != "care"
    assert not any(isinstance(v, dict) and v.get("looted") for v in r.world.containers.values())
    assert r.world.first_sight == set()                                           # a moved item is never first sight


def test_an_aim_refused_no_target_is_not_a_stand_off(tmp_path):
    """Task 10 fix 2, item 5: the Lua refuses an aim whose target is gone no target; the build holds the stance all
    the same, so standoff is not set (any other failed leg still sets it)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    assert r.cmd()[0] == "aim"
    r.answer({"state": "failed", "reason": "no target"})
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    assert sv.fight.standoff is False and sv.fight.standoff_why is None
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    r2.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r2, sv2)
    r2.answer({"state": "failed", "reason": "not allowed"})
    r2.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r2, sv2)
    assert sv2.fight.standoff is True and sv2.fight.standoff_why == "failed not allowed"


def night_rig(tmp_path, fence_hop=True, caps=None):
    r, sv = make(tmp_path, caps=caps)
    r.scan(shelter_yard(fence_hop))
    r.frame(x=107.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 109.5, "y": 201.5, "gait": "walk"})
    r.answer({"state": "failed", "reason": "stuck"})
    r.frame(x=107.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    return r, sv


def test_the_nights_own_shelter_walk_climbs_a_fence_on_its_route_and_walks_on(tmp_path):
    """Task 10 fix 2, item 6 (10 fix 1, concern 8): Night's approach walk failed stuck at a hoppable edge climbs it
    (night.hop_after, the plan step kept at approach) and walks the approach again once the climb ends done; a climb
    that does not end done is read as that walk's stuck end (one door: the building is shunned)."""
    r, sv = night_rig(tmp_path)
    assert r.cmd() == ("climb", {"x": 108, "y": 201}) and sv.night.plan["step"] == "approach"
    assert last(tmp_path)["inputs"]["branches"]["night"]["step"] == "climb"
    r.world.stuck[(109, 201)] = r.world.world_minutes()
    r.answer()
    r.frame(x=108.5, y=201.5, fatigue=0.65)
    for _ in range(S.FAILED_COOLDOWN_TICKS):   # the stuck walk's same-args cooldown (a climb outlasts it live)
        tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 109.5, "y": 201.5, "gait": "walk"}) and sv.night.plan["step"] == "approach"
    assert sv.night.climbed == {(108, 201)} and (109, 201) not in r.world.stuck
    assert [s["step"] for s in sv.night.steps] == ["approach", "climb"]
    all_sends_valid(r)
    (tmp_path / "b").mkdir()
    r2, sv2 = night_rig(tmp_path / "b")
    assert r2.cmd()[0] == "climb"
    r2.answer({"state": "failed", "reason": "fell"})
    r2.frame(x=107.5, y=201.5, fatigue=0.65)
    tick(r2, sv2)
    assert 1 in sv2.night.shunned
    assert sum(a.type == "climb" for a in r2.acts.history) == 1


def test_the_nights_shelter_walk_stuck_at_a_wall_or_on_a_1_4_build_never_climbs(tmp_path):
    r, sv = night_rig(tmp_path, fence_hop=False)
    assert not any(a.type == "climb" for a in r.acts.history) and 1 in sv.night.shunned
    (tmp_path / "b").mkdir()
    r2, sv2 = night_rig(tmp_path / "b", caps=CAPS_14)
    assert not any(a.type == "climb" for a in r2.acts.history)


def stance_fight(r):
    f = P.Fight(r.world, r.acts, r.clock)
    f.stance = True   # Survive sets it each tick
    return f


def test_the_stance_is_never_aimed_at_a_target_beyond_the_luas_aim_r_it_is_walked_toward_first(tmp_path):
    """Task 10 fix 2 (the re-review of 10 fix 1, minor 2): the Lua refuses an aim at a target beyond K.AIM_R (12
    tiles) as no target, which would set standoff; the Fight walks toward a farther target as the approach and swing
    does, keeps no stand clock while it does, and takes the stance once the target is inside AIM_R."""
    assert P.AIM_R == 12.0
    r = Rig(tmp_path)
    r.frame(zombies=[zd(1, 113.0, 200.0)])                                      # 13 tiles
    f = stance_fight(r)
    f.observe()
    assert f.step() is not None and r.cmd()[0] == "walkTo" and f.standoff is False and f._stand is None
    r.answer()
    r.frame(zombies=[zd(1, 112.0, 200.0)])                                      # 12 tiles: inside
    f.observe()
    assert f.step() is not None and stance_args(r)["targetId"] == 1
    assert f._stand is not None and f.standoff is False
    all_sends_valid(r)


def test_a_far_target_holds_no_stand_clock_so_no_stand_off_falls_before_it_is_in_range(tmp_path):
    r = Rig(tmp_path)
    f = stance_fight(r)
    for k in range(3):
        r.advance(P.STAND_MAX_S)                                                # far longer than a stand would last
        r.frame(zombies=[zd(1, 114.0 + k * 0.01, 200.0)])
        f.observe()
    assert f.standoff is False and f._stand is None
