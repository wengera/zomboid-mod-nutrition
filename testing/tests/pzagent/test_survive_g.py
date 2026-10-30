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


@pytest.fixture
def unsought(monkeypatch):
    """Named change, ruling P24-X (Plan 24 Task 18): every Fight Survive engages is sought to KEEP_R
    (`test_survive_h`), its first legs `seek` legs toward the target; the cases of iteration 7's stance beyond KEEP_R
    (the stand, its clock, the advance, the look behind) pin it on a Fight whose seek is off, as after a seek that
    reached KEEP_R (`Fight.sought`)."""
    monkeypatch.setattr(S.Survive, "SEEK", False)


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
    AIM_LEG_S; the leg holds while the target stays beyond KEEP_R and gives way the tick it comes inside (2.2 tiles):
    the next leg backpedals along the away vector (west, the zombie east of the player); within reach the `attack`
    goes from the stance (the running leg gives way). Named change, ruling P24-X: the first leg is the seek, (1, 0)
    toward it (it stood, (0, 0), letting it come), `leg` "seek"; the rest is iteration 7's."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    a = stance_args(r)
    assert a == {"vx": 1.0, "vy": 0.0, "seconds": 2.0, "targetId": 1, "bearing": -1.0}
    w = threat_why(tmp_path)
    assert w["fight"] is True and w["stance"] is True and w["leg"] == "seek" and w["back"] is None
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
def test_a_pinned_target_beyond_keep_r_is_stood_facing_and_inside_it_backpedalled_from(tmp_path, x, kind, unsought):
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
    f.send(f.choose())
    assert f.in_stance()
    r.acts.send(P.Stop())                                                  # another sender: the stance released
    assert not f.in_stance()


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


def test_a_first_leg_on_a_zombie_with_no_target_beyond_keep_r_stands(tmp_path, unsought):
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


def test_a_stand_with_no_progress_in_stand_max_s_closes_in_the_stance_never_a_walk_at_a_run(tmp_path, unsought):
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
    r.answer()
    r.advance(1.0)
    r.frame(zombies=[zd(1, 106.0, 200.0, has_target=False)])
    tick(r, sv)
    assert last(tmp_path)["inputs"]["fight_s"] == 2.0 and sv.fight.fight_s() == 2.0   # unbroken, toward the stall


def test_the_advance_with_its_line_blocked_walks_round_the_wall_at_a_walk(tmp_path):
    """The advance's one walk: the line to the stand-off target blocked over STEER_PROBE (a wall between), the
    approach walk (the path follower walks round it); with the line clear, the aim toward it. Named change (Task 12
    fix 1, the review's minor 3): at a walk, never a run (ruling P24-N 1: "in the stance ... not to a run")."""
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
    assert r.cmd() == ("walkTo", {"x": 106.5, "y": 200.5, "gait": "walk"}) and sv.fight.advance
    assert threat_why(tmp_path)["leg"] == "walk"


def test_a_falling_target_health_restarts_the_stand_clock_and_ends_the_advance(tmp_path, unsought):
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


def test_a_standing_fight_reads_no_walk_so_the_look_behind_its_target_does_not_flee(tmp_path, unsought):
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


def test_the_advance_reads_as_a_walk_so_the_look_behind_its_target_flees(tmp_path, unsought):
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
    superseded by that send. Since ruling P24-P (Task 12) that holds for a zombie at CARE_R (4.0 tiles) or nearer;
    named change (Task 12 fix 1, the review's major 2): a running bandage is superseded only inside CARE_HOLD_R (3.0
    tiles), so a zombie arriving at 4.0 holds it and one at 3.0 takes the tick."""
    r, sv = bleeding_rig(tmp_path, [(10, "Base.Bandage")])
    tick(r, sv)
    assert r.cmd()[0] == "bandage"
    bandage = r.acts.history[-1]
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], zombies=[zd(1, 104.0, 200.0)])
    assert tick(r, sv) is None and last(tmp_path)["branch"] == "care" and r.acts.current is bandage
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], zombies=[zd(1, 103.0, 200.0)])
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
    on) and no source to wash it: the garment is still not ripped while any rag is held. Ruling P24-AB's stock rips
    nothing either while a dirty rag is held (Task 21 fix 1, review-t21 minor 5: washing it is the care's job)."""
    r, sv = make(tmp_path)
    r.frame()
    hold(r, 21, "Base.Shirt_FormalWhite", use="other")
    hold(r, 11, "Base.RippedSheetsDirty")
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "care" and not any(a.type == "rip" for a in r.acts.history)


def test_no_garment_is_ripped_for_stock_with_no_wound(tmp_path):
    """Task 10 fix 1, the review's major 2 (ruling P24-G 2: the rip is the wound's): no rag of any kind held, a looted
    cotton shirt held and no part bleeding: nothing is ripped, the need's drink goes; the first bleeding part rips it.
    Named change, ruling P24-AB (Plan 24 Task 21): the rag stock rips only on an idle tick, behind the need, so the
    drink still goes first (the idle tick's stock rip is `test_survive_i.py`'s)."""
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
    `quiet` each tick (no zombie within DISENGAGE_R) before `choose()`. Named change (Task 12 fix 1, P24-U): the
    Care's own `busy` adds a running ride to the house's rule (`test_a_torso_wound_rides_...`)."""
    assert issubclass(C.Care, P.Policy)
    assert C.Care.send is P.Policy.send and C.Care.sent is not P.Policy.sent and C.Care.busy is not P.Policy.busy
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


# ================================================================ Task 12: no sprint anywhere (ruling P24-O)
def test_no_policy_of_the_planner_can_emit_a_sprint():
    """Ruling P24-O (E6: 13 sprint steers, the character tripped; a fence climb begun at a sprint rolls a trip,
    #4296): the planner's gaits are walk and run. Every planner module is swept for the literal "sprint" as a value
    (its docstrings and comments name the history), and the schema's gait enum keeps it (the Lua still accepts it)."""
    import ast
    import os
    from agent.base import pza1
    from agent.base.planner import goals, llm, night, view
    assert "sprint" in pza1.GAITS
    for mod in (P, S, C, goals, night, view, llm):
        with open(mod.__file__, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        hits = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Constant) and n.value == "sprint"]
        assert hits == [], (os.path.basename(mod.__file__), hits)
    assert P.FLEE_GAIT == "run" and not hasattr(P.Flee, "_group_sprint")


def test_no_decision_golden_sends_a_sprint():
    """The sweep over the six decision goldens' replays (re-recorded under P24-O where a sprint became a run)."""
    import json
    from agent.base import replay_decisions as R
    for key in sorted(R.RUNS):
        with open(R.golden_path(key), encoding="utf-8") as f:
            gaits = {(d["action"] or {}).get("args", {}).get("gait") for d in json.load(f)["decisions"]}
        assert "sprint" not in gaits and "run" in gaits, key


def test_the_flees_every_leg_and_walk_runs(tmp_path):
    """A melee zombie at 0.5 tiles (once a sprint within SPRINT_R), a `many` group at full endurance (once the group
    sprint) and the group's exit on a room square (once at a sprint): every one at a run."""
    from .test_survive import many_yard
    r = Rig(tmp_path)
    r.frame(zombies=[zombie(1, 100.5, 200.0), zombie(2, 105.0, 200.0)])
    P.Flee(r.world, r.acts, r.clock).step()
    assert r.cmd()[0] == "steer" and r.cmd()[1]["gait"] == "run"
    (tmp_path / "m").mkdir()
    r2, sv2 = make(tmp_path / "m")
    many_yard(r2, endurance=1.0)
    tick(r2, sv2)
    assert threat_why(tmp_path / "m")["flee"] == "many" and r2.cmd()[1]["gait"] == "run"
    assert all(a.args.get("gait") != "sprint" for a in r.acts.history + r2.acts.history)


# ================================================================ Task 12: the bandage under a far threat (P24-P)
def test_care_r_is_four_tiles_inside_danger_r():
    assert C.CARE_R == 4.0 and P.FIGHT_REACH < C.CARE_R < P.DANGER_R


@pytest.mark.parametrize("x, care", [(105.0, True), (104.01, True), (104.0, False), (103.0, False)])
def test_a_bleeding_part_is_bandaged_with_a_zombie_held_beyond_care_r_and_not_inside_it(tmp_path, x, care):
    """Ruling P24-P: a fight running on one zombie (held), a part bleeding, a bandage held: with the zombie at 5 or
    4.01 tiles the threat branch yields (`care` on its why) and the care branch bandages; at 4 or 3 tiles the threat
    answers (the stance). Named change (Task 12 fix 1, the review's major 2): the zombie stands at `x` for
    CARE_STILL_TICKS ticks before the yield's start reads it not closing (it came from 6 tiles before)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 106.0, 200.0)])
    tick(r, sv)
    assert sv.mode == "fight" and r.cmd()[0] == "aim"
    hold(r, 10, "Base.Bandage")
    for _ in range(C.CARE_STILL_TICKS):
        care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], zombies=[zd(1, x, 200.0)])
        tick(r, sv)
        assert last(tmp_path)["branch"] == "threat" and "care" not in threat_why(tmp_path)
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], zombies=[zd(1, x, 200.0)])
    tick(r, sv)
    if care:
        assert last(tmp_path)["branch"] == "care" and r.cmd() == ("bandage", {"itemId": 10, "part": 5})
        assert threat_why(tmp_path)["care"] is True and threat_why(tmp_path)["nearest"] == pytest.approx(x - 100.0)
        assert sv.mode == "fight" and last(tmp_path)["inputs"]["held"] == 1
    else:
        assert last(tmp_path)["branch"] == "threat" and r.cmd()[0] in ("aim", "attack")


def test_the_bandage_runs_under_a_health_flee_and_is_superseded_when_a_zombie_comes_inside_care_hold_r(tmp_path):
    """E6's case (lines 285-306: the `health` flee held one or two at 4 to 9.6 tiles, bleeding, no bandage): the
    flee yields to the bandage while the nearest is beyond CARE_R, the bandage holds the tick while it runs, and a
    zombie at 3 tiles takes the tick back: the flee's steer supersedes it. Named change (Task 12 fix 1, the review's
    major 2): the zombie (no chaser: `hasTarget` false) reads 3 tiles, then 7 on CARE_STILL_TICKS ticks, the yield
    starting on the last (no fall since the read two ticks before), each flee leg ended before the next tick, and a
    running bandage holds at 3.5 tiles (inside CARE_R,
    beyond CARE_HOLD_R); the supersede line is CARE_HOLD_R (3.0)."""
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    bleed = [part(5, bleeding=True, bleedingTime=5.0)]
    care_frame(r, bleed, zombies=[zd(1, 103.0, 200.0, has_target=False)], health=30.0)
    tick(r, sv)
    assert sv.mode == "flee" and threat_why(tmp_path)["flee"] == "health" and r.cmd()[0] == "steer"
    for _ in range(C.CARE_STILL_TICKS - 1):
        r.answer()
        care_frame(r, bleed, zombies=[zd(1, 107.0, 200.0, has_target=False)], health=30.0)
        tick(r, sv)
        assert last(tmp_path)["branch"] == "threat" and r.cmd()[0] == "steer"
    r.answer()
    care_frame(r, bleed, zombies=[zd(1, 107.0, 200.0, has_target=False)], health=30.0)
    tick(r, sv)
    assert last(tmp_path)["branch"] == "care" and r.cmd()[0] == "bandage"
    bandage = r.acts.history[-1]
    r.fake.answer({"bandage": ["accepted"]})
    r.pump()
    for x in (106.0, 103.5):
        care_frame(r, bleed, zombies=[zd(1, x, 200.0, has_target=False)], health=30.0)
        assert tick(r, sv) is None and last(tmp_path)["branch"] == "care"
        assert care_why(tmp_path)["holding"] == bandage.aid and threat_why(tmp_path)["care"] is True
    care_frame(r, bleed, zombies=[zd(1, 103.0, 200.0, has_target=False)], health=30.0)
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and r.cmd()[0] == "steer" and r.acts.current is not bandage
    all_sends_valid(r)


def test_no_yield_to_the_care_under_a_group_or_with_nothing_to_tend(tmp_path):
    """The `many` reason (four listed within LISTED_R, the nearest at 6) keeps the threat's tick; so does a bleeding
    part with no bandage, rag or rippable garment held (the threat never stands down for nothing), and a PZA/1.4
    build."""
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    zs = [zd(1, 106.0, 200.0), zd(2, 100.0, 207.0), zd(3, 93.0, 200.0), zd(4, 100.0, 193.0)]
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], zombies=zs)
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and threat_why(tmp_path)["flee"] == "many"
    (tmp_path / "n").mkdir()
    r2, sv2 = make(tmp_path / "n")
    r2.frame(zombies=[zd(1, 106.0, 200.0)])
    tick(r2, sv2)
    care_frame(r2, [part(5, bleeding=True, bleedingTime=5.0)], zombies=[zd(1, 106.0, 200.0)])
    tick(r2, sv2)
    assert last(tmp_path / "n")["branch"] == "threat" and "care" not in threat_why(tmp_path / "n")
    (tmp_path / "o").mkdir()
    r3, sv3 = make(tmp_path / "o", caps=CAPS_14)
    hold(r3, 10, "Base.Bandage")
    care_frame(r3, [part(5, bleeding=True, bleedingTime=5.0)], zombies=[zd(1, 106.0, 200.0)])
    tick(r3, sv3)
    assert last(tmp_path / "o")["branch"] == "threat"


def test_under_a_held_threat_only_the_bleeding_step_answers(tmp_path):
    """With a threat held beyond CARE_R a spent bandage is not replaced (the threat keeps its tick: no bleeding step
    to yield to, `tends_wound` False); with no threat it is."""
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    spent = [part(5, bandaged=True, bandageLife=0.0)]
    care_frame(r, spent, zombies=[zd(1, 106.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and "care" not in threat_why(tmp_path)
    assert not sv.care.tends_wound()
    (tmp_path / "q").mkdir()
    r2, sv2 = make(tmp_path / "q")
    hold(r2, 10, "Base.Bandage")
    care_frame(r2, spent)
    tick(r2, sv2)
    assert r2.cmd() == ("bandage", {"itemId": 10, "part": 5}) and care_why(tmp_path / "q")["reason"] == "spent"


# ================================================================ Task 12: kills as the metric (P24-Q)
def test_a_kill_read_off_an_attack_is_logged_and_counted_once(tmp_path):
    """Ruling P24-Q: the Fight reads `targetDead` on its attack's result: the next decision line's threat why carries
    `kill` (the zombie id), `World.kills` counts it, `to_json` carries it; a second result on the same id counts
    nothing more, and the view tells the model the kills so far."""
    import json as _json
    r, sv = make(tmp_path, caps=CAPS_14)
    r.frame(zombies=[zd(1, 101.6, 200.0)])
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1}) and r.world.kills == 0
    assert "kills" not in _json.loads(r.world.to_json())
    r.fake.answer({"attack": ["accepted", {"state": "done", "result": {"swings": 1, "attackStarted": True,
                                                                        "targetDead": True}}]})
    r.pump()
    r.frame(zombies=[zd(1, 101.6, 200.0), zd(2, 104.0, 200.0)])
    tick(r, sv)
    assert threat_why(tmp_path)["kill"] == 1 and r.world.kills == 1 and r.world.killed == {1}
    assert _json.loads(r.world.to_json())["kills"] == 1
    r.frame(zombies=[zd(2, 104.0, 200.0)])
    tick(r, sv)
    assert "kill" not in threat_why(tmp_path) and r.world.kills == 1
    assert r.world.note_kill(1) is False and r.world.kills == 1
    v = V.view(r.world, sv)
    assert v["kills"] == 1 and "kills: 1" in V.render(v).splitlines()


def test_a_kill_read_off_an_aim_counts_and_a_live_target_does_not(tmp_path):
    """An aim that ends done with `targetDead` (the Lua ends it at once) is a kill too; `targetDead` false is none."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    assert r.cmd()[0] == "aim"
    r.fake.answer({"aim": ["accepted", {"state": "done", "result": {"d": 0.0, "held": True, "targetDead": False}}]})
    r.pump()
    r.frame(zombies=[zd(1, 104.0, 200.0)])
    tick(r, sv)
    assert r.world.kills == 0 and "kill" not in threat_why(tmp_path) and r.cmd()[0] == "aim"
    r.fake.answer({"aim": ["accepted", {"state": "done", "result": {"d": 0.0, "held": True, "targetDead": True}}]})
    r.pump()
    r.frame(zombies=[])
    tick(r, sv)
    assert r.world.kills == 1 and threat_why(tmp_path)["kill"] == 1


# ================================================================ Task 12 fix 1: the stance leg gives way on distance
def test_the_keep_margin_constant():
    assert P.KEEP_MARGIN == 0.25 and P.KEEP_R + P.KEEP_MARGIN < P.DANGER_R
    assert [P.stance_leg_kind(d, False) for d in (2.0, 2.01, 2.5, 2.51)] == ["enter", "back", "back", "stand"]
    assert [P.stance_leg_kind(d, True) for d in (2.0, 2.01, 6.0)] == ["enter", "toward", "toward"]


def test_a_backpedal_gives_way_to_a_standing_leg_once_the_target_is_past_keep_r_and_its_margin(tmp_path):
    """The review's major 1 (a backpedal held its whole AIM_LEG_S while its target fell back past KEEP_R; #4324's
    full leg moved the character 3.0 tiles while the target's distance rose from 2.48 to 3.48): a back leg sent at 2.3
    tiles holds at 2.7 (inside KEEP_R + KEEP_MARGIN) and gives way at 2.9 to a standing leg, (0, 0)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 102.3, 200.0)])
    tick(r, sv)
    assert stance_args(r)["vx"] == -1.0 and threat_why(tmp_path)["leg"] == "back"
    back = r.acts.history[-1]
    r.answer("progress")
    r.advance(0.5)
    r.frame(zombies=[zd(1, 102.7, 200.0)])
    assert tick(r, sv) is None and threat_why(tmp_path)["holding"] == back.aid
    r.advance(0.5)
    r.frame(zombies=[zd(1, 102.9, 200.0)])
    tick(r, sv)
    a = stance_args(r)
    assert (a["vx"], a["vy"]) == (0.0, 0.0) and threat_why(tmp_path)["leg"] == "stand"
    assert r.acts.history[-2] is back and len(r.acts.history) == 2
    all_sends_valid(r)


def test_an_enter_leg_whose_target_is_knocked_out_of_reach_gives_way_to_the_backpedal(tmp_path):
    """The review's major 1, the `enter` leg: sent with its target in reach (1.8 tiles, the stance not held), the
    target knocked back to 2.3 tiles: the leg gives way to a `back` leg (it stood its 2 s before)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 101.8, 200.0)])
    tick(r, sv)
    assert threat_why(tmp_path)["leg"] == "enter"
    enter = r.acts.history[-1]
    r.answer("progress")
    r.advance(0.3)
    r.frame(zombies=[zd(1, 102.3, 200.0)])
    tick(r, sv)
    assert stance_args(r)["vx"] == -1.0 and threat_why(tmp_path)["leg"] == "back" and r.acts.history[-2] is enter


def test_the_advance_s_toward_leg_holds_until_reach(tmp_path):
    """Only the advance's `toward` leg is held whatever the distance reads, until its target is within reach: even
    once the advance ended (a hit restarts the stand) and the distance calls for a backpedal."""
    r = Rig(tmp_path)
    r.frame(zombies=[zd(1, 106.0, 200.0, has_target=False)])
    f = stance_fight(r)
    f.observe()
    f.advance = True
    leg = f.step()
    assert leg.type == "aim" and f.why["leg"] == "toward"
    r.answer("progress")
    for x in (103.0, 102.4, 102.1):
        r.frame(zombies=[zd(1, x, 200.0, has_target=False)])
        f.observe()
        assert f.busy(), x
        f.advance = False                                                   # the advance ended: still held
    r.frame(zombies=[zd(1, 101.9, 200.0, has_target=False)])
    f.observe()
    assert not f.busy()


# ================================================================ Task 12 fix 1: the care yield's hysteresis
def test_the_care_hold_line_and_the_still_ticks():
    assert (C.CARE_HOLD_R, C.CARE_STILL_TICKS) == (3.0, 2) and P.FIGHT_REACH < C.CARE_HOLD_R < C.CARE_R


def test_a_chaser_closing_half_a_tile_a_tick_from_4_6_starts_no_bandage(tmp_path):
    """The review's major 2, its first test: a zombie closing 0.5 tiles a tick (5.6, 5.1, 4.6, 4.1, then 3.6) under
    a running fight starts no bandage: each read beyond CARE_R is a fall since the read two ticks before."""
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    for x in (105.6, 105.1, 104.6, 104.1, 103.6):
        care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], zombies=[zd(1, x, 200.0)])
        tick(r, sv)
        assert last(tmp_path)["branch"] == "threat" and "care" not in threat_why(tmp_path), x
        r.answer()
    assert not any(a.type == "bandage" for a in r.acts.history)


def test_a_still_zombie_at_4_5_is_bandaged_held_at_3_5_and_superseded_at_2_9(tmp_path):
    """The review's major 2, its second test: a zombie standing at 4.5 tiles reads not closing on the third tick and
    the bandage starts; once it runs, the zombie at 3.5 (inside CARE_R) holds it, and at 2.9 (inside CARE_HOLD_R) the
    threat takes the tick back: the stance leg supersedes the bandage."""
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    bleed = [part(5, bleeding=True, bleedingTime=5.0)]
    for _ in range(C.CARE_STILL_TICKS):
        care_frame(r, bleed, zombies=[zd(1, 104.5, 200.0)])
        tick(r, sv)
        assert last(tmp_path)["branch"] == "threat"
    care_frame(r, bleed, zombies=[zd(1, 104.5, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "care" and r.cmd() == ("bandage", {"itemId": 10, "part": 5})
    bandage = r.acts.history[-1]
    r.fake.answer({"bandage": ["accepted"]})
    r.pump()
    care_frame(r, bleed, zombies=[zd(1, 103.5, 200.0)])
    assert tick(r, sv) is None and last(tmp_path)["branch"] == "care"
    assert threat_why(tmp_path) == {"care": True, "nearest": pytest.approx(3.5), "held": 1}
    care_frame(r, bleed, zombies=[zd(1, 102.9, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and r.cmd()[0] == "aim" and r.acts.current is not bandage
    all_sends_valid(r)


@pytest.mark.parametrize("chases, care", [(True, False), (False, True)])
def test_no_standing_bandage_starts_while_a_flee_leg_runs_from_a_chaser(tmp_path, chases, care):
    """The review's ruling on concern 2: a `health` flee does not block the yield against a zombie that is not
    closing; against a chaser (`hasTarget`) during a running flee leg the standing bandage waits (it would stop the
    run). Here the leg (a thigh's wound: no ride) runs while the zombie reads 5.5 tiles, then 7 (never closing)."""
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    thigh = [part(11, bleeding=True, bleedingTime=5.0)]
    for x in (105.5,) + (107.0,) * C.CARE_STILL_TICKS:
        care_frame(r, thigh, zombies=[zd(1, x, 200.0, has_target=chases)], health=30.0)
        tick(r, sv)
        if r.acts.current is not None and r.acts.current.state == "sent":
            r.answer("progress")
    assert sv.mode == "flee" and r.acts.history[0].type == "steer"
    assert (last(tmp_path)["branch"] == "care") is care and threat_why(tmp_path).get("care", False) is care
    assert care or (threat_why(tmp_path)["flee"] == "health" and threat_why(tmp_path)["holding"])
    assert any(a.type == "bandage" for a in r.acts.history) is care


def test_a_running_bandage_whose_part_stops_bleeding_is_superseded_by_the_threat(tmp_path):
    """The review's minor 7 (Task 12's commit 4 removed the `running` clause, read as equivalent; it is not): once no
    part bleeds, `tends_wound` reads false, the yield ends and the threat's send supersedes the running bandage, the
    zombie still at 4.5 tiles. Kept: once nothing bleeds the threat matters more."""
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    for _ in range(C.CARE_STILL_TICKS + 1):
        care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], zombies=[zd(1, 104.5, 200.0)])
        tick(r, sv)
    bandage = r.acts.history[-1]
    assert bandage.type == "bandage"
    r.fake.answer({"bandage": ["accepted"]})
    r.pump()
    care_frame(r, [part(5, bleeding=True, bleedingTime=5.0)], zombies=[zd(1, 104.5, 200.0)])
    assert tick(r, sv) is None and last(tmp_path)["branch"] == "care"
    care_frame(r, [part(5)], zombies=[zd(1, 104.5, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and r.cmd()[0] == "aim" and r.acts.current is not bandage


# ================================================================ Task 12 fix 1: the riding bandage (ruling P24-U)
def test_the_ride_constants():
    assert (C.RIDE_R, C.LEG_FIRST, C.RIDE_FREE) == (6.0, 11, ("stopped",)) and C.CARE_R < C.RIDE_R <= P.DANGER_R
    assert P.RIDE_TYPES == ("walkTo", "steer")


def test_a_leg_stays_running_under_the_riding_bandages_sent_after_it_and_nothing_else(tmp_path):
    """PZA/1.5.3 (ruling P24-R): a keepMoving bandage leaves the leg its slot, so the leg's policy stays busy while
    it runs (`policies.running`); a standing bandage, or any other send, replaces it; an aim is never ridden."""
    from agent.base import pza1
    r = Rig(tmp_path)
    r.frame()
    leg = r.acts.send(P.Steer(1.0, 0.0, 3.0, "run"))
    ride = r.acts.send(pza1.Bandage(10, part=6, keepMoving=True))
    assert r.acts.current is ride and P.running(r.acts, leg) and P.rides_on(r.acts, leg)
    r.acts.send(pza1.Bandage(11, part=6, keepMoving=True))   # a second ride supersedes the first, the leg still runs
    assert P.running(r.acts, leg)
    r.acts.send(pza1.Bandage(12, part=6))
    assert not P.running(r.acts, leg)
    aim = r.acts.send(P.Aim(0.0, 0.0, 2.0, targetId=1))
    r.acts.send(pza1.Bandage(10, part=6, keepMoving=True))
    assert not P.rides_on(r.acts, aim) and not P.running(r.acts, aim)


def flee_leg_rig(tmp_path, parts, x, chases=True):
    """A `health` flee (health 30) from one zombie (`hasTarget` `chases`), its steer leg sent at 5.5 tiles and
    running (progress); then the frame with `parts` bleeding and the zombie at `x` tiles, ticked."""
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    care_frame(r, parts, zombies=[zd(1, 105.5, 200.0, has_target=chases)], health=30.0)
    tick(r, sv)
    assert sv.mode == "flee" and r.cmd()[0] == "steer" and threat_why(tmp_path)["flee"] == "health"
    r.answer("progress")
    care_frame(r, parts, zombies=[zd(1, 100.0 + x, 200.0, has_target=chases)], health=30.0)
    tick(r, sv)
    return r, sv


def test_a_torso_wound_rides_the_running_flee_leg_with_the_chaser_at_7(tmp_path):
    """Ruling P24-U, the review's first ride test: under the running steer, the chaser at 7 tiles (beyond RIDE_R),
    the upper torso bleeding: the care sends `bandage` with keepMoving on part 6; the Flee's leg is held (it still
    runs: `running`), its end re-aims with a new steer that keeps the ride (the Care busy on the ride's own act lines),
    and the ride's done frees the Care."""
    torso = [part(6, bleeding=True, bleedingTime=5.0)]
    r, sv = flee_leg_rig(tmp_path, torso, 7.0)
    assert last(tmp_path)["branch"] == "care" and r.cmd() == ("bandage", {"itemId": 10, "part": 6, "keepMoving": True})
    assert threat_why(tmp_path) == {"care": True, "ride": True, "nearest": 7.0, "held": 1}
    assert care_why(tmp_path)["ride"] is True
    leg, ride = r.acts.history[0], r.acts.history[-1]
    r.fake.act(ride.aid, "accepted", "bandage")
    r.pump()
    care_frame(r, torso, zombies=[zd(1, 107.0, 200.0)], health=30.0)
    assert tick(r, sv) is None and last(tmp_path)["branch"] == "threat"
    w = threat_why(tmp_path)
    assert w["holding"] == leg.aid and w["ride"] == ride.aid and sv.flee.busy() and sv.care.busy()
    r.fake.act(leg.aid, "done", "steer", result={})
    r.pump()
    care_frame(r, torso, zombies=[zd(1, 107.0, 200.0)], health=30.0)
    tick(r, sv)
    assert r.cmd()[0] == "steer" and sv.care.riding() is ride and threat_why(tmp_path)["ride"] == ride.aid
    assert r.acts.current is not ride and sv.care.busy()                    # busy on the ride's own act lines
    r.answer("progress")
    r.fake.act(ride.aid, "done", "bandage", result={"part": 6, "walking": True})
    r.pump()
    care_frame(r, [part(6, bandaged=True)], zombies=[zd(1, 107.0, 200.0)], health=30.0)
    tick(r, sv)
    assert sv.care.riding() is None and not sv.care.busy() and "ride" not in threat_why(tmp_path)
    assert sum(a.type == "bandage" for a in r.acts.history) == 1
    all_sends_valid(r)


@pytest.mark.parametrize("x, parts", [(5.0, [part(6, bleeding=True, bleedingTime=5.0)]),
                                      (7.0, [part(11, bleeding=True, bleedingTime=5.0)])])
def test_no_ride_with_the_chaser_at_5_nor_for_a_thigh(tmp_path, x, parts):
    """The review's second and third ride tests: the chaser at 5 tiles (inside RIDE_R), or a thigh bleeding (part
    11: the Lua refuses a leg part `leg part`): no ride, and no standing bandage either while the flee leg runs from
    a chaser (item 2); the Flee's leg holds the tick."""
    r, sv = flee_leg_rig(tmp_path, parts, x)
    assert last(tmp_path)["branch"] == "threat" and "care" not in threat_why(tmp_path)
    assert threat_why(tmp_path)["holding"] == r.acts.history[0].aid
    assert not any(a.type == "bandage" for a in r.acts.history)


def test_a_flee_leg_with_no_chaser_rides_whatever_the_distance(tmp_path):
    """No zombie chasing (`hasTarget` false) at 5 tiles: the ride goes beside the running leg."""
    r, sv = flee_leg_rig(tmp_path, [part(6, bleeding=True, bleedingTime=5.0)], 5.0, chases=False)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 6, "keepMoving": True})


def test_the_worst_part_above_the_legs_rides_past_a_worse_thigh(tmp_path):
    """A deep thigh wound and a forearm scratch: the ride takes the forearm (part 3), never the thigh."""
    r, sv = flee_leg_rig(tmp_path, [part(11, bleeding=True, bleedingTime=9.0, deep=True),
                                    part(3, bleeding=True, bleedingTime=2.0)], 7.0)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 3, "keepMoving": True})


def test_no_ride_starts_in_a_stance_fight_and_its_legs_are_held_off_while_one_runs(tmp_path):
    """No ride under an aim (the Lua rejects it `aiming`): a fight's yield is the standing bandage. A ride running
    when the flee turns to a fight (the health back over the refight line) holds the Fight's stance leg off (its aim
    would end the ride) until the ride ends; then the stance leg goes."""
    torso = [part(6, bleeding=True, bleedingTime=5.0)]
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    for _ in range(C.CARE_STILL_TICKS + 1):
        care_frame(r, torso, zombies=[zd(1, 105.0, 200.0)])
        tick(r, sv)
    assert sv.mode == "fight" and r.cmd() == ("bandage", {"itemId": 10, "part": 6})
    (tmp_path / "f").mkdir()
    r2, sv2 = flee_leg_rig(tmp_path / "f", torso, 7.0)
    ride = r2.acts.history[-1]
    assert ride.args.get("keepMoving") is True
    r2.fake.act(ride.aid, "accepted", "bandage")
    r2.pump()
    r2.advance(S.FLIP_MIN_S)                                     # past the flip: the refight is not held back
    care_frame(r2, torso, zombies=[zd(1, 107.0, 200.0)], health=100.0)
    assert tick(r2, sv2) is None and sv2.mode == "fight"
    assert threat_why(tmp_path / "f")["ride"] == ride.aid and r2.acts.history[-1] is ride
    r2.fake.act(ride.aid, "done", "bandage", result={"part": 6, "walking": True})
    r2.pump()
    care_frame(r2, [part(6, bandaged=True)], zombies=[zd(1, 107.0, 200.0)], health=100.0)
    tick(r2, sv2)
    assert r2.cmd()[0] == "aim" and "ride" not in threat_why(tmp_path / "f")


def test_a_ride_the_engine_stopped_holds_no_item_out(tmp_path):
    """A ride ended `failed stopped` (a run, an aim, a hit stopped it) leaves its item usable; a standing bandage's
    failure holds it out CARE_RETRY_MIN as before."""
    r, sv = flee_leg_rig(tmp_path, [part(6, bleeding=True, bleedingTime=5.0)], 7.0)
    ride = r.acts.history[-1]
    r.fake.act(ride.aid, "failed", "bandage", reason="stopped")
    r.pump()
    sv.care.observe()
    assert sv.care.held_out == {} and sv.care.riding() is None


def test_a_ride_takes_a_walk_only_on_an_open_line(tmp_path):
    """PZA/1.5.3's obligation (the ride walks straight, no pathing): a flee walk is ridden only while its straight
    line to its target reads clear on the map; a steer always."""
    r, sv = flee_leg_rig(tmp_path, [part(6, bleeding=True, bleedingTime=5.0)], 5.0)
    sqs = [square(x, y) for x in range(95, 112) for y in range(195, 206)]
    r.scan([dict(s, blockW=True) if (s["x"], s["y"]) == (103, 200) else s for s in sqs])
    assert sv._ride_leg() is r.acts.history[0]
    walk = sv.flee.send(P.WalkTo(105.5, 200.5, "run"))
    assert sv._ride_leg() is None
    walk2 = sv.flee.send(P.WalkTo(100.5, 203.5, "run"))
    assert sv._ride_leg() is walk2 and walk is not walk2


# ================================================================ Task 12 fix 1: the dead target (concern 6, ruled)
def test_a_target_read_dead_is_unpinned_and_skipped_for_unreachable_s_logged_dead(tmp_path):
    """The controller's ruling on concern 6 (F1's line 254 swung at 15911 on its kill tick, the zombie still
    listed): an attack ends done with `targetDead` on zombie 1 at 1.6 tiles, and the next frame still lists 1 at 1.6
    and 2 at 4.0: the next command is no `attack 1` but a stance leg on 2; the why logs `dead` [1], never
    `unreachable`; the skip is time-bounded (UNREACHABLE_S), the World's `killed` the only permanent record."""
    r, sv = make(tmp_path)
    r.frame(zombies=[zd(1, 101.6, 200.0)])
    tick(r, sv)
    assert threat_why(tmp_path)["leg"] == "enter"
    r.answer("progress")
    r.frame(zombies=[zd(1, 101.6, 200.0)])
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1})
    r.fake.answer({"attack": ["accepted", {"state": "done", "result": {"swings": 1, "attackStarted": True,
                                                                        "targetDead": True}}]})
    r.pump()
    r.frame(zombies=[zd(1, 101.6, 200.0), zd(2, 104.0, 200.0)])
    tick(r, sv)
    a = stance_args(r)
    assert a["targetId"] == 2 and r.cmd() != ("attack", {"targetId": 1})
    w = threat_why(tmp_path)
    assert w["kill"] == 1 and w["target"] == 2 and w["dead"] == [1] and "unreachable" not in w
    assert sv.fight.target == 2 and 1 in sv.fight.blocked() and sv.dead == sv.fight.dead
    assert last(tmp_path)["inputs"]["held"] == 2                            # the record's own reading of the frame
    r.advance(P.UNREACHABLE_S)
    assert 1 not in sv.fight.blocked() and r.world.killed == {1}


def test_a_corpse_still_listed_alone_is_no_threat(tmp_path):
    """F1's line 333 (the swing at 15937 on its kill tick, the only zombie listed): the dead zombie is left out of
    the held list (`_within`), so the threat branch passes instead of fleeing it `unreachable`."""
    r, sv = make(tmp_path, caps=CAPS_14)
    r.frame(zombies=[zd(1, 101.6, 200.0)])
    tick(r, sv)
    assert r.cmd() == ("attack", {"targetId": 1})
    r.fake.answer({"attack": ["accepted", {"state": "done", "result": {"swings": 1, "attackStarted": True,
                                                                        "targetDead": True}}]})
    r.pump()
    r.frame(zombies=[zd(1, 101.6, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "threat" and sv.mode is None and threat_why(tmp_path) == {"kill": 1}
    assert sum(a.type == "attack" for a in r.acts.history) == 1


# ================================================================ Task 12 fix 2: the re-review's two majors and minors
def test_the_chaser_rule_is_keyed_on_the_flee_episode_not_the_leg_running(tmp_path):
    """The re-review's major 1 (probe A): a `health` flee from a chaser held at a flat 5.5 tiles, a thigh bleeding.
    Each time the steer leg ends (answered `done`) the Flee re-steers on that tick; the gap between two legs is the
    same flight and starts no standing bandage."""
    thigh = [part(11, bleeding=True, bleedingTime=5.0)]
    r, sv = flee_leg_rig(tmp_path, thigh, 5.5)
    assert sv.mode == "flee"
    assert r.cmd()[0] == "steer" or threat_why(tmp_path)["holding"]
    for _ in range(C.CARE_STILL_TICKS + 3):
        leg = r.acts.current
        r.fake.act(leg.aid, "done", "steer", result={})
        r.pump()
        care_frame(r, thigh, zombies=[zd(1, 105.5, 200.0)], health=30.0)
        tick(r, sv)
        assert last(tmp_path)["branch"] == "threat" and r.cmd()[0] == "steer" and "care" not in threat_why(tmp_path)
        r.answer("progress")
    assert not any(a.type == "bandage" for a in r.acts.history)


def stopped_ride_rig(tmp_path):
    """Probe B: the chaser at 7, a torso bleeding, a water item held, thirst 0.5 (`need` would drink), the ride sent
    and answered `failed stopped`; returns (rig, survive, the flee leg, the ride, the torso)."""
    torso = [part(6, bleeding=True, bleedingTime=5.0)]
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    hold(r, 20, "Base.WaterBottle", use="water")
    care_frame(r, torso, zombies=[zd(1, 105.5, 200.0)], health=30.0, thirst=0.5)
    tick(r, sv)
    r.answer("progress")
    care_frame(r, torso, zombies=[zd(1, 107.0, 200.0)], health=30.0, thirst=0.5)
    tick(r, sv)
    leg, ride = r.acts.history[0], r.acts.history[-1]
    assert leg.type == "steer" and ride.type == "bandage" and ride.args["keepMoving"] is True
    r.fake.act(ride.aid, "failed", "bandage", reason="stopped")
    r.pump()
    return r, sv, leg, ride, torso


def test_a_stopped_ride_hands_the_tick_to_the_flee_not_to_a_drink_nor_a_standing_bandage(tmp_path):
    """The re-review's major 2 (probe B): the ride the engine stopped is no failure to cool (the item stays free) and
    the care rides again only after RIDE_RETRY_S; the tick after it returns to the threat (the leg held), never the
    need's `consume` (which would supersede the flee leg) nor, the tick after, a standing bandage under the chaser."""
    r, sv, leg, ride, torso = stopped_ride_rig(tmp_path)
    assert C.RIDE_RETRY_S == 3.0
    for _ in range(2):
        care_frame(r, torso, zombies=[zd(1, 107.0, 200.0)], health=30.0, thirst=0.5)
        assert tick(r, sv) is None
        row = last(tmp_path)
        assert row["branch"] == "threat" and row["inputs"]["cooled"] is None and "care" not in threat_why(tmp_path)
        assert threat_why(tmp_path)["holding"] == leg.aid
    assert [a.type for a in r.acts.history] == ["steer", "bandage"]
    assert sv.care.held_out == {} and sv.last_failed is None
    r.advance(C.RIDE_RETRY_S + 0.1)                                          # the retry: the ride goes again
    care_frame(r, torso, zombies=[zd(1, 107.0, 200.0)], health=30.0, thirst=0.5)
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 6, "keepMoving": True})
    all_sends_valid(r)


def test_a_stance_less_fights_approach_walk_is_never_ridden(tmp_path, monkeypatch):
    """The re-review's minor 3 (mutant 3h): with `_stance_ok` false a Fight sends the approach `walkTo` at a run; a
    bleeding torso gets no keepMoving bandage beside it (a ride toward the zombie), only a flee's leg is ridden."""
    monkeypatch.setattr(S.Survive, "_stance_ok", lambda self, held, inside: False)
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    r.scan([square(x, y) for x in range(95, 112) for y in range(195, 206)])   # an open map: the walk's line reads clear
    torso = [part(6, bleeding=True, bleedingTime=5.0)]
    for _ in range(4):
        care_frame(r, torso, zombies=[zd(1, 105.5, 200.0, has_target=False)])
        tick(r, sv)
        if r.acts.current is not None and r.acts.current.state == "sent":
            r.answer("progress")
    assert sv.mode == "fight" and any(a.type == "walkTo" for a in r.acts.history)
    assert not any(a.type == "bandage" and a.args.get("keepMoving") for a in r.acts.history)


@pytest.mark.parametrize("chases, x, ride", [(True, 102.5, False), (True, 107.0, True), (False, 107.0, True)])
def test_a_many_flee_with_a_chaser_held_blocks_the_ride_inside_ride_many_r(tmp_path, chases, x, ride):
    """The re-review's minor 4 (ruling on concern 3): `flee_many` with any held chaser blocked the ride (the nearest at
    7 beyond RIDE_R, but several chasers converge); with no chaser the group is not closing and the ride goes. Named
    change, ruling P24-AR (Plan 24 Task 32; renamed from `..._blocks_the_ride`): the chaser at 7 tiles (beyond
    RIDE_MANY_R) now lets the ride go; at 2.5 it still blocks it (`test_survive_r` reads the long flee's clock)."""
    torso = [part(6, bleeding=True, bleedingTime=5.0)]
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    care_frame(r, torso, zombies=[zd(1, 105.5, 200.0, has_target=chases)], health=30.0)
    tick(r, sv)
    r.answer("progress")
    sv.flee_many = True
    care_frame(r, torso, zombies=[zd(1, x, 200.0, has_target=chases)], health=30.0)
    tick(r, sv)
    assert any(a.type == "bandage" for a in r.acts.history) is ride


def test_the_dead_entry_drops_once_the_world_no_longer_lists_the_id(tmp_path):
    """The re-review's minor 5: after the kill the id stays skipped while listed (the corpse on its kill tick); a
    `zombie_dead` for it drops the entry on the next tick, so the same id listed at 1.5 tiles afterwards is a new
    zombie and the threat answers it."""
    r, sv = make(tmp_path, caps=CAPS_14)
    r.frame(zombies=[zd(1, 101.6, 200.0)])
    tick(r, sv)
    r.fake.answer({"attack": ["accepted", {"state": "done", "result": {"swings": 1, "attackStarted": True,
                                                                        "targetDead": True}}]})
    r.pump()
    r.frame(zombies=[zd(1, 101.6, 200.0)])
    tick(r, sv)
    assert 1 in sv.dead and last(tmp_path)["branch"] != "threat"
    r.frame(zombies=[zd(1, 101.6, 200.0)])
    tick(r, sv)
    assert 1 in sv.dead
    r.event("zombie_dead", id=1)
    r.frame()
    tick(r, sv)
    assert 1 not in sv.dead
    r.frame(zombies=[zd(1, 101.5, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and r.cmd() == ("attack", {"targetId": 1})
