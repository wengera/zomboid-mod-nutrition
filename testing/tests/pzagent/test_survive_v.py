"""Survival 16 (survival iteration 14's second half; Plan 25 Task 8; E12, `e_day_12-20261030-175041`, rows #4428-#4439).
The fake mod over PZA/1.7.1.

- P25-J, the fallen finished out to FINISH_R: with no standing zombie within KEEP_R the Fight's finish reads the downed
  out to FINISH_R (the stomp's own walk in); a standing one within KEEP_R is fought first (at point blank its shove, as
  P24-AL); the doorway stand's finish is bounded by its post (`doorway.off_post_at`); the `pair` flee yields to that
  stomp. Task 8 fix 1 (P25-J (3) amended): one finish rule (`finish.finish_rule`) read before a `pair` flee, the
  Fight's knock window included (E12's a86 order), and inside a running `pair` flee (its own stomp, its refusals).
- P25-K, the stand leaves on its first wound: a part bleeding that was not when the stand began ends it `wound`.
- P25-L, the break after SHOVE_BREAK_N missed shoves in a row at a lone target under a divided swing.
- P25-M, the hold's release logged on the threat why once (`release` {kind, why, endurance | armPain, held_min}).
- The residuals of review-t7: `view.why_of` reads `shunned` for a Shelter alone; P25-H's bleeding step past the settle
  window with the garment still reading worn.
"""
import pytest

from agent.base.planner import care as C
from agent.base.planner import doorway as D
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T
from agent.base.planner import view as V

from .test_policies import all_sends_valid
from .test_survive import make, threat_why, tick
from .test_survive_g import care_why, part
from .test_survive_n import SHIRT, bleed, unwear_rig
from .test_survive_p import POST, stood
from .test_survive_p import z as dz
from .test_survive_q import STIFF, fr, z
from .test_survive_t import DOWN, MISS, NO_STIFF, WOUND, shoved


def test_the_iteration_14_switches_and_constant():
    assert S.T4_SWITCHES == ("UNWEAR_WOUND", "FINISH_FAR", "STAND_WOUND", "SHOVE_BREAK", "SHELTER_LEGS")
    for name in S.T4_SWITCHES:
        assert getattr(S.Survive, name) is True, name
    assert P.SHOVE_BREAK_N == 3 and not set(S.T4_SWITCHES) & set(T.T3_SWITCHES)
    assert P.SHOVE_BREAK_N * P.SHOVE_REPEAT_S == BREAK_WINDOW_S


# ================================================================ P25-J: the fallen finished out to FINISH_R
@pytest.mark.parametrize("x, stomped", [(102.5, True), (104.9, True), (105.1, False)])
def test_a_downed_zombie_within_finish_r_with_no_standing_one_within_keep_r_is_stomped(tmp_path, x, stomped):
    """E12 (#4435: every knocked-down zombie first read fallen 2.12 to 2.73 tiles off): a downed zombie at 2.5 or 4.9
    tiles, nothing standing within KEEP_R, takes the finish's `Stomp` (logged `downed`), the stomp's walk covering the
    distance; at 5.1 tiles, beyond FINISH_R, no stomp."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, x, floor=True)])
    a = tick(r, sv)
    w = threat_why(tmp_path)
    if stomped:
        assert (a.type, a.args) == ("stomp", {"targetId": 1}) and w["downed"] == 1 and w["stomp"] is True
        assert "finish_first" not in w
        all_sends_valid(r)
    else:
        assert a is None or a.type != "stomp"


def test_with_finish_far_off_the_stomp_at_2_5_is_p25_b_s_and_with_both_off_none(tmp_path):
    """The switch off (`FINISH_FAR`, `pre_t4`): the same zombie is stomped by P25-B's stomp first (`finish_first`),
    the rule before; with FINISH_FIRST off too the Fight does not stomp it."""
    r, sv = make(tmp_path)
    sv.FINISH_FAR = False
    r.frame(zombies=[z(1, 102.5, floor=True)])
    a = tick(r, sv)
    assert a.type == "stomp" and threat_why(tmp_path)["finish_first"]["target"] == 1
    (tmp_path / "off").mkdir()
    r2, sv2 = make(tmp_path / "off")
    sv2.FINISH_FAR = sv2.FINISH_FIRST = False
    r2.frame(zombies=[z(1, 102.5, floor=True)])
    a2 = tick(r2, sv2)
    assert a2 is None or a2.type != "stomp"


def test_a_standing_zombie_inside_keep_r_is_fought_first_and_the_downed_waits(tmp_path):
    """A downed zombie 2.5 tiles east and a standing one 2.2 tiles west (inside KEEP_R, beyond point blank): the
    standing one is fought (the stance's leg at it), the downed left (neither the finish nor P25-B's stomp first)."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 102.5, floor=True), z(2, 97.8)])
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a is not None and a.type != "stomp" and a.args.get("targetId") == 2
    assert "downed" not in w and "finish_first" not in w


def test_a_standing_zombie_at_point_blank_is_shoved_first_as_before(tmp_path):
    """P24-AL as before: a downed zombie within FIGHT_REACH and a standing one at point blank: the shove first."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 101.5, floor=True), z(2, 99.2)])
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("shove", {"targetId": 2}) and w["shove"] == "first" and w["downed"] == 1


def test_a_far_downed_zombie_with_a_chaser_beside_it_is_not_walked_to(tmp_path):
    """The far stomp keeps P25-B's chaser guard (`finish.finish_chaser`): a standing chaser 1.5 tiles beyond the fallen
    one (4.0 tiles from the player, beyond KEEP_R) refuses the stomp's walk."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 102.5, floor=True), z(2, 104.0)])
    a = tick(r, sv)
    assert a is None or a.type != "stomp"


def _stand_frame(r, zs, me=POST, **k):
    r.frame(x=me[0], y=me[1], zombies=zs, **k)


def test_the_stand_stomps_a_downed_zombie_whose_walk_keeps_its_post_and_leaves_one_whose_walk_does_not(tmp_path):
    """P25-J (2), E12's 10906 lay fallen 2.87 to 2.96 tiles from the stand (GUIDE § 3): from the post square (113.5,
    201.5), a fallen zombie 2.9 tiles off on the approach square outside, 1.9 tiles from the threshold square's centre
    (within DOOR_OFF_R), is stomped; from the threshold (112.5, 201.5), one 2.9 tiles off outside, as far from the
    threshold's centre, is left (the stomp's walk would leave the stand)."""
    r, sv = stood(tmp_path)
    me = (113.5, 201.5)
    rest = [dz(2, 106.0, 204.0, me=me), dz(3, 106.0, 199.0, me=me)]
    _stand_frame(r, [dz(1, 110.6, 201.5, me=me, floor=True)] + rest, me=me)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and w["doorway"] == 1 and w["downed"] == 1
    (tmp_path / "far").mkdir()
    r2, sv2 = stood(tmp_path / "far")
    rest2 = [dz(2, 105.0, 204.0), dz(3, 105.0, 199.0)]
    _stand_frame(r2, [dz(1, 109.6, 201.5, floor=True)] + rest2)
    a2 = tick(r2, sv2)
    assert a2 is None or a2.type != "stomp"
    assert D.off_post_at(r2.world, sv2.flee.plan, 109.6, 201.5) and not D.off_post_at(r.world, sv.flee.plan, 110.6,
                                                                                         201.5)


def test_the_pair_flee_yields_to_the_stomp_of_a_downed_zombie_within_finish_r(tmp_path):
    """P25-J (3), E12: health 50 (under FLEE_HEALTH_PAIR), a downed zombie 2.5 tiles east and a standing one 5 tiles
    west (within DANGER_R, beyond KEEP_R): `n` 2, but the stomp goes before the `pair` flee, logged `pair_yield`; with
    FINISH_FAR off, the `pair` flee as before."""
    zs = [z(1, 102.5, floor=True), z(2, 95.0)]
    r, sv = make(tmp_path)
    r.frame(zombies=zs, health=50.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and w["pair_yield"] == 1 and w["fight"] is True
    assert "flee" not in w
    (tmp_path / "off").mkdir()
    r2, sv2 = make(tmp_path / "off")
    sv2.FINISH_FAR = False
    r2.frame(zombies=zs, health=50.0)
    a2 = tick(r2, sv2)
    assert threat_why(tmp_path / "off")["flee"] == "pair" and a2.type != "stomp"


def test_the_pair_flee_stands_with_a_standing_zombie_within_keep_r(tmp_path):
    """No yield when a standing zombie is within KEEP_R (2.2 tiles): the `pair` flee as before."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 102.5, floor=True), z(2, 97.8)], health=50.0)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["flee"] == "pair" and "pair_yield" not in w


A86 = z(2, 95.0)   # E12's second zombie of the a86 knock-down (decision.log 337-342): within DANGER_R, beyond KEEP_R
STOMP_DEAD = {"state": "done", "result": {"hit": True, "attackStarted": True, "targetDead": True}}


def test_the_a86_order_the_pair_flee_waits_out_the_knock_window_and_the_fallen_zombie_is_stomped(tmp_path):
    """P25-J (3) amended (8 fix 1), E12's a86 order: the walk corner's shove at the lone target ends `knockdown` true
    with a second zombie 5 tiles off; the next frame reads the knocked zombie pushed to 1.8 tiles (the corner ends,
    beyond CORNERED_R) and not yet `onFloor`, under FLEE_HEALTH_PAIR: the rule lists it in the Fight's knock window, so
    no `pair` flee: the Fight's knock wait (`knocked`, `pair_yield`); the frame reading it fallen at 2.5 tiles takes the
    stomp (the walk in) and its `targetDead` reads the kill. At HEAD before the fix the `pair` flee ran from it."""
    r, sv = shoved(tmp_path, [z(1, 100.49), A86], end=DOWN)
    fr(r, [z(1, 101.8), A86], WOUND, NO_STIFF, health=50.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a is None and w["knocked"] == 1 and w["fight"] is True and w["pair_yield"] == 1 and "flee" not in w
    r.advance(0.5)
    fr(r, [z(1, 102.5, floor=True), A86], WOUND, NO_STIFF, health=50.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and w["downed"] == 1 and w["stomp"] is True
    assert w["pair_yield"] == 1 and "flee" not in w
    r.answer(STOMP_DEAD)
    fr(r, [A86], WOUND, NO_STIFF, health=50.0)
    tick(r, sv)
    assert r.world.kills == 1 and threat_why(tmp_path)["kill"] == 1
    all_sends_valid(r)


def test_with_finish_far_off_the_a86_order_flees_pair_as_before(tmp_path):
    """The switch off (`pre_t4`): the same order's tick in the knock window flees `pair`, as E12 did."""
    r, sv = shoved(tmp_path, [z(1, 100.49), A86], end=DOWN)
    sv.FINISH_FAR = False
    fr(r, [z(1, 101.8), A86], WOUND, NO_STIFF, health=50.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type in ("steer", "walkTo") and w["flee"] == "pair" and "pair_yield" not in w


def _pair_flee(tmp_path):
    """A `pair` flee running: health 50, zombie 1 standing 3 tiles east (beyond KEEP_R), zombie 2 at 5 tiles west."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 103.0), A86], health=50.0)
    a = tick(r, sv)
    assert a.type in ("steer", "walkTo") and threat_why(tmp_path)["flee"] == "pair" and sv.mode == "flee"
    r.advance(0.5)
    return r, sv


@pytest.mark.parametrize("x, stomped", [(102.5, True), (105.5, False)])
def test_inside_a_running_pair_flee_a_zombie_read_fallen_within_finish_r_is_stomped_and_beyond_it_the_flee_runs(
        tmp_path, x, stomped):
    """P25-J (3) amended (c): inside a running `pair` flee the rule is consulted each tick (P24-AQ's finish extended to
    `pair`, the rule's guards): zombie 1 read fallen 2.5 tiles off takes the flee's finishing `Stomp` (`finish`, kind
    stomp, `pair_yield`) and its `targetDead` is a kill; read fallen 5.5 tiles off (beyond FINISH_R) the flee runs on."""
    r, sv = _pair_flee(tmp_path)
    r.frame(zombies=[z(1, x, floor=True), A86], health=50.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert w["flee"] == "pair"
    if not stomped:
        assert a is None or a.type not in ("stomp", "attack")
        assert "pair_yield" not in w and "finish" not in w
        return
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and w["finish"] == 1 and w["kind"] == "stomp"
    assert w["pair_yield"] == 1
    r.answer(STOMP_DEAD)
    r.frame(zombies=[A86], health=50.0)
    tick(r, sv)
    assert r.world.kills == 1 and threat_why(tmp_path)["kill"] == 1 and 1 in sv.dead
    all_sends_valid(r)


def test_a_stomp_refused_inside_the_pair_flee_leaves_the_rule_silent_and_the_flee_runs(tmp_path):
    """The flee's stomp refused (the Lua's `not valid`): the rule is silent at that zombie, no floor strike (a `pair`
    finish is the stomp alone) and the flee runs, no `pair_yield`."""
    r, sv = _pair_flee(tmp_path)
    zs = [z(1, 102.5, floor=True), A86]
    r.frame(zombies=zs, health=50.0)
    assert tick(r, sv).type == "stomp"
    r.answer({"state": "failed", "reason": "not valid"})
    r.advance(0.5)
    r.frame(zombies=zs, health=50.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert w["flee"] == "pair" and "pair_yield" not in w and "finish" not in w
    assert a is None or a.type not in ("stomp", "attack")


def test_a_stomp_the_fight_had_refused_lets_the_pair_flee_run(tmp_path):
    """The review's minor 1: the Fight's stomp at the fallen zombie 2.5 tiles off refused (`not valid`, SWING_SKIP_S);
    the next frame under FLEE_HEALTH_PAIR: the rule reads the Fight's refusal, so no yield: the `pair` flee runs."""
    r, sv = make(tmp_path)
    zs = [z(1, 102.5, floor=True), A86]
    r.frame(zombies=zs, health=70.0)
    assert tick(r, sv).type == "stomp"
    r.answer({"state": "failed", "reason": "not valid"})
    r.advance(0.5)
    r.frame(zombies=zs, health=50.0)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["flee"] == "pair" and "pair_yield" not in w


def test_pair_yield_is_never_logged_on_a_strain_line(tmp_path):
    """The review's minor 1: the yield's conditions (a fallen zombie 3 tiles off, a second at 5, health 50) under the
    arms' hold with no zombie within KEEP_R: the `strain` flee answers, and `pair_yield` is not on its line."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 103.0, floor=True), A86], 25.0, STIFF, health=50.0)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["flee"] == "strain" and "pair_yield" not in w


# ================================================================ P25-K: the stand leaves on its first wound
def test_a_part_bleeding_since_the_stand_began_ends_it_wound_and_the_flee_closes_the_door(tmp_path):
    """E12 (#4431: the bleeding parts rose from 1 to 7 at the door, the first bite far above FLEE_HEALTH): the stand's
    frame gains part 4 bleeding, not in its start's snapshot: the stand ends `wound` (`doorway_wound` [4]) and the
    Flee's close from inside answers the tick (flee `doorway`). Named change, P25-W (Plan 25 Task 14): the `wound` end
    now walks out by the way out (`test_survive_x`); this case pins the close with `STAND_EXIT` off."""
    r, sv = stood(tmp_path)
    sv.STAND_EXIT = False
    far = [dz(i, x + 8.0, y) for i, x, y in ((1, 97.0, 201.5), (2, 98.0, 204.0), (3, 98.0, 199.0))]
    _stand_frame(r, far, wounds={"parts": [part(4)]})
    tick(r, sv)
    assert threat_why(tmp_path).get("doorway") == 1
    _stand_frame(r, far, wounds={"parts": [part(4, bleeding=True, bleedingTime=3.0)], "bleeding": 1})
    tick(r, sv)
    w = threat_why(tmp_path)
    assert r.cmd()[0] == "interact" and r.cmd()[1]["kind"] == "close"
    assert w["doorway_left"] == "wound" and w["doorway_wound"] == [4] and w["flee"] == "doorway"
    assert sv.flee.plan["left"] == "wound" and sv.mode == "flee"


def test_a_part_bleeding_before_the_stand_does_not_end_it(tmp_path):
    """Part 4 bleeding through the flee to the door (the start's snapshot holds it): the stand stands; part 4 bleeding
    on and part 6 not new either (it never bled): no end."""
    bleeding = {"parts": [part(4, bleeding=True, bleedingTime=3.0), part(6)], "bleeding": 1}
    r, sv = make(tmp_path)
    from .test_survive_p import to_post
    a = to_post(r, sv, wounds=bleeding)
    assert a is not None and a.type == "aim" and sv.flee.plan["step"] == "stand"
    assert sv.flee.plan["bleed0"] == frozenset({4})
    r.fake.answer({"aim": ["accepted"]})
    r.pump()
    far = [dz(i, x + 8.0, y) for i, x, y in ((1, 97.0, 201.5), (2, 98.0, 204.0), (3, 98.0, 199.0))]
    _stand_frame(r, far, wounds=bleeding)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w.get("doorway") == 1 and "doorway_left" not in w


def test_the_wound_end_reads_before_the_health_end_on_the_same_tick(tmp_path):
    """The order chosen (the ruling's: `wound` before `health`): a tick that reads a new bleeding part and the health
    under FLEE_HEALTH logs `wound` (both ends close the door the same way); the health alone logs `health`
    (`test_survive_p`). Named change, P25-W (Plan 25 Task 14): `STAND_EXIT` off, so both close."""
    r, sv = stood(tmp_path)
    sv.STAND_EXIT = False
    near =[dz(1, 111.3, 201.5), dz(2, 106.0, 204.0), dz(3, 106.0, 199.0)]
    _stand_frame(r, near, wounds={"parts": [part(4, bleeding=True)], "bleeding": 1}, health=S.FLEE_HEALTH - 1.0)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w["doorway_left"] == "wound" and w["doorway_wound"] == [4] and r.cmd()[1]["kind"] == "close"


def test_with_stand_wound_off_a_new_bleeding_part_keeps_the_stand(tmp_path):
    r, sv = stood(tmp_path)
    sv.STAND_WOUND = False
    far = [dz(i, x + 8.0, y) for i, x, y in ((1, 97.0, 201.5), (2, 98.0, 204.0), (3, 98.0, 199.0))]
    _stand_frame(r, far, wounds={"parts": [part(4, bleeding=True)], "bleeding": 1})
    tick(r, sv)
    w = threat_why(tmp_path)
    assert w.get("doorway") == 1 and "doorway_left" not in w


# ================================================================ P25-L: the break after repeated misses
def missed(r, end=MISS):
    """The last shove ends `end`, half a second passes and E11's lone zombie at 0.49 tiles is read again."""
    r.fake.answer({"shove": ["accepted", end]})
    r.pump()
    r.advance(0.5)
    fr(r, [z(1, 100.49)], WOUND, NO_STIFF, health=70.0)


def test_two_missed_shoves_take_the_third_and_three_take_the_break(tmp_path):
    """E12 (#4434, #4436: 29 `strain` shoves, 6 knock-downs in 39 done shoves, no swing for 108 game minutes): after the
    first and the second missed shove at the lone target the shove goes again (`corner` {kind shove}); after the third,
    the steer at a run away from it, logged `corner` {kind break, shoved, n 1, misses 3}, the run of misses reset."""
    r, sv = shoved(tmp_path, [z(1, 100.49)])
    for n in (2, 3):
        a = tick(r, sv)
        assert (a.type, a.args) == ("shove", {"targetId": 1}), n
        assert threat_why(tmp_path)["corner"]["kind"] == "shove"
        missed(r)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and a.args["gait"] == P.FLEE_GAIT and a.args["vx"] < -0.99
    assert w["corner"] == {"kind": "break", "shoved": 1, "n": 1, "misses": 3}
    assert sv.fight._misses is None
    all_sends_valid(r)


def test_a_knock_down_between_the_misses_resets_the_run(tmp_path):
    """Miss, knock-down (the knock wait, then read standing again past KNOCK_READ_S), miss, miss: two misses since the
    knock-down, so the shove goes again, never the break."""
    r, sv = shoved(tmp_path, [z(1, 100.49)])
    assert tick(r, sv).type == "shove"
    missed(r, DOWN)
    assert tick(r, sv) is None   # the knock wait
    r.advance(P.KNOCK_READ_S)
    fr(r, [z(1, 100.49)], WOUND, NO_STIFF, health=70.0)
    for _ in range(2):
        assert tick(r, sv).type == "shove"
        missed(r)
    a = tick(r, sv)
    assert a.type == "shove" and threat_why(tmp_path)["corner"]["kind"] == "shove"


BREAK_WINDOW_S = 9.0   # SHOVE_BREAK_N x SHOVE_REPEAT_S, pinned by `test_the_iteration_14_switches_and_constant`


def test_misses_older_than_the_window_do_not_count(tmp_path):
    """The window SHOVE_BREAK_N x SHOVE_REPEAT_S (9 s): the first miss (sent at 0), a pause of 7 s, a second shove (no
    corner: past SHOVE_REPEAT_S) and a third, both missed; read at 9.5 s the first lies outside the window, two inside
    it: the shove again, not the break; that fourth shove missed too, three lie inside the window at 10 s: the break
    (8 fix 1, review-t8 minor 5: the case fails at the parent on that behaviour, the window read by literal). Named
    change, ruling P25-T (Plan 25 Task 10): the misses count over the Fight's life; this case pins the window with
    `SHOVE_BREAK_RUN` off (`test_survive_w` the run)."""
    r, sv = shoved(tmp_path, [z(1, 100.49)])
    sv.SHOVE_BREAK_RUN = False
    t0 = r.clock() - 0.5
    r.advance(7.0)
    fr(r, [z(1, 100.49)], WOUND, NO_STIFF, health=70.0)
    a = tick(r, sv)
    assert a.type == "shove" and "corner" not in threat_why(tmp_path)
    missed(r)
    a = tick(r, sv)
    assert a.type == "shove" and threat_why(tmp_path)["corner"]["kind"] == "shove"
    missed(r)
    r.advance(1.0)
    fr(r, [z(1, 100.49)], WOUND, NO_STIFF, health=70.0)
    assert r.clock() - t0 > BREAK_WINDOW_S
    a = tick(r, sv)
    assert a.type == "shove" and threat_why(tmp_path)["corner"] == {"kind": "shove", "shoved": 1, "n": 1, "sore": True}
    missed(r)
    a = tick(r, sv)
    assert a.type == "steer" and threat_why(tmp_path)["corner"] == {"kind": "break", "shoved": 1, "n": 1, "misses": 3}


def test_with_shove_break_off_the_shoves_go_on(tmp_path):
    r, sv = shoved(tmp_path, [z(1, 100.49)])
    sv.SHOVE_BREAK = False
    for _ in range(3):
        assert tick(r, sv).type == "shove"
        missed(r)
    assert tick(r, sv).type == "shove"


def test_a_doorway_fight_never_breaks(tmp_path):
    """The stand's own shove at point blank (every time at STRAIN_HARD) after four missed shoves: still the shove."""
    r, sv = stood(tmp_path)
    zs = [dz(1, 111.7, 201.5)] + [dz(2, 106.0, 204.0), dz(3, 106.0, 199.0)]
    for _ in range(4):
        _stand_frame(r, zs, wounds={"armPain": WOUND, "strain": NO_STIFF})
        a = tick(r, sv)
        assert (a.type, a.args) == ("shove", {"targetId": 1}) and threat_why(tmp_path)["shove"] == "doorway"
        r.fake.answer({"shove": ["accepted", MISS]})
        r.pump()
        r.advance(0.5)
    assert "corner" not in threat_why(tmp_path)


# ================================================================ P25-M: the hold's release is a field
def test_an_endurance_hold_released_on_the_line_logs_release_once(tmp_path):
    """Set at game minute 600 at 0.72 (a zombie 5 tiles off), released at 610 at 0.81 (above ENDURANCE_RELEASE):
    `release` {kind endurance, why line, endurance 0.81, held_min 10.0} on that tick's threat why; the next tick none."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 105.0)], endurance=0.72, game_min=600.0)
    tick(r, sv)
    assert sv.endurance_hold and "release" not in threat_why(tmp_path)
    r.frame(zombies=[z(1, 108.0)], endurance=0.81, game_min=610.0)
    tick(r, sv)
    assert threat_why(tmp_path)["release"] == {"kind": "endurance", "why": "line", "endurance": 0.81,
                                               "held_min": 10.0}
    assert sv.spent is None
    r.frame(zombies=[z(1, 108.0)], endurance=0.82, game_min=611.0)
    tick(r, sv)
    assert "release" not in threat_why(tmp_path)


def test_a_timed_release_logs_why_timed_with_its_span(tmp_path):
    """P25-C's timed release (set at 600 at 0.72, quiet HOLD_QUIET_S, game minute 616 at 0.74): `release` {why timed,
    endurance 0.74, held_min 16.0}."""
    r, sv = make(tmp_path)
    t0 = r.clock()
    r.frame(zombies=[z(1, 105.0)], endurance=0.72, game_min=600.0)
    tick(r, sv)
    r.t["now"] = t0 + P.HOLD_QUIET_S
    r.frame(zombies=[z(1, 108.0)], endurance=0.74, game_min=616.0)
    tick(r, sv)
    assert threat_why(tmp_path)["release"] == {"kind": "endurance", "why": "timed", "endurance": 0.74,
                                               "held_min": 16.0}


def test_the_arms_hold_released_logs_why_pain_with_the_arms_pain(tmp_path):
    """The arms' hold (a stiffness of 25 at game minute 600), released once both arms read under STIFF_SOFT (game
    minute 605): `release` {kind arms, why pain, armPain 12.0, armStiffness 3.0 (the reading that released it: 8 fix 1,
    review-t8 minor 6), held_min 5.0}."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 108.0)], 12.0, {"l": 25.0, "r": 0.0}, game_min=600.0)
    tick(r, sv)
    assert sv.strain_hold
    fr(r, [z(1, 108.0)], 12.0, {"l": 3.0, "r": 0.0}, game_min=605.0)
    tick(r, sv)
    assert threat_why(tmp_path)["release"] == {"kind": "arms", "why": "pain", "armPain": 12.0, "armStiffness": 3.0,
                                                 "held_min": 5.0}


def test_no_release_is_logged_with_strain_off(tmp_path):
    r, sv = make(tmp_path)
    sv.STRAIN = False
    r.frame(zombies=[z(1, 105.0)], endurance=0.72, game_min=600.0)
    tick(r, sv)
    r.frame(zombies=[z(1, 108.0)], endurance=0.81, game_min=610.0)
    tick(r, sv)
    assert "release" not in threat_why(tmp_path)


# ================================================================ the residuals of review-t7
@pytest.mark.parametrize("typ, why", [("LootBuilding", "failed"), ("Shelter", "shunned")])
def test_a_failure_no_door_reads_shunned_for_a_shelter_and_failed_for_a_loot(typ, why):
    """`shunned` is the Shelter's reading only (the prompt says a shunned building is passed over for SHUN_MIN, which a
    LootBuilding's `no door` never stamps); the runner still cools both (`goals.COOL_REASONS`)."""
    assert V.why_of({"type": typ, "state": "failed", "reason": "no door"}) == why


def test_past_the_settle_window_the_still_worn_garment_gives_way_to_the_next_least_covering(tmp_path):
    """P25-H past WEAR_SETTLE_MAX frames with the T-shirt still reading worn (no `item_changed`): `_unwear_pick` leaves
    it out for WEAR_RETRY_MIN game minutes since its send, so the bleeding step unwears the next least-covering cotton
    garment, the shirt 21 (an unwear the Lua did not carry out is not retried at once; the next garment gives the rag);
    within the window nothing was sent."""
    r, sv = unwear_rig(tmp_path)
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 20})
    r.fake.answer({"unwear": ["accepted", {"state": "done", "result": {"itemId": 20, "loc": "base:tshirt"}}]})
    r.pump()
    done_n = r.world.act_n[str(sv.care.sends[20].aid)]
    while r.world.frame_n + 1 < done_n + C.WEAR_SETTLE_MAX:
        bleed(r)
        tick(r, sv)
        assert sum(1 for a in r.acts.history if a.type in ("unwear", "rip")) == 1
    assert r.world.inventory[20].get("worn") is True
    bleed(r)
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 21})
    assert care_why(tmp_path) == {"reason": "unwear", "part": 9, "item": 21, "loc": SHIRT, "cover": 7.0}


# ================================================================ P25-O: the hello's two-number mod version
@pytest.mark.parametrize("mod, want", [("1.7", True), ("1.7.1", True), ("1.5.2", True), ("1.5", False),
                                       ("1.4.9", False), ("", False), (None, False)])
def test_item_fields_reads_a_two_number_mod_version(mod, want):
    """Ruling P25-O: the Lua's hello has read `mod` "1.7" since PZA/1.7 (`PZA.VERSION`); a missing third number reads
    0, so "1.7" is (1, 7, 0), past 1.5.2, and "1.5" (1, 5, 0) is not."""
    from agent.base.world import World
    w = World()
    w.apply({"kind": "hello", "mod": mod, "caps": []})
    assert w.item_fields() is want


def test_p25_h_s_unwear_runs_on_the_live_hello_s_mod_1_7(tmp_path):
    """P25-H through Survive on the live form of the hello (`mod` "1.7", as every PZA/1.7 session's state.log line 1):
    part 9 bleeding, every cotton garment worn, nothing held, no zombie: the care's bleeding step unwears the T-shirt
    (before P25-O the three-number match read the hello False, and `_unwear_step` sent nothing)."""
    from .test_survive_n import TSHIRT, worn
    r, sv = make(tmp_path)
    r.fake.hello(mod="1.7")
    r.pump()
    assert r.world.item_fields() is True
    worn(r, 20, "Base.Tshirt_White", TSHIRT, 1.0, 2.0)
    worn(r, 21, "Base.Shirt_FormalWhite", SHIRT, 2.0, 5.0)
    r.frame()
    bleed(r)
    tick(r, sv)
    assert r.cmd() == ("unwear", {"itemId": 20})
    assert care_why(tmp_path) == {"reason": "unwear", "part": 9, "item": 20, "loc": TSHIRT, "cover": 3.0}


# ================================================================ P25-N: a Shelter approaches its door in legs
FAR_DOOR = (160, 201)   # building 1's west door (`test_night.house(1, 160)`), its approach square (159, 201)


def shelter_runner(tmp_path, legs=True):
    """F4's goal walks (54 to 62 squares to building 8's door): a Shelter(1) of a building whose door is 60 tiles off
    the player at (100.5, 201.5), no window width read (the leg LEG_MAX 40)."""
    from agent.base.planner.goals import GoalRunner, Shelter
    from .test_goals import Src
    from .test_night import house
    from .test_policies import Rig
    r = Rig(tmp_path)
    r.scan(house(1, FAR_DOOR[0]))
    r.frame(x=100.5, y=201.5, game_min=500.0)
    g = Shelter(1)
    runner = GoalRunner(Src(g), r.clock)
    runner.kit.shelter_legs = legs
    return r, runner, g


def run_step(r, runner):
    runner.observe(r.world, r.acts)
    cmd = runner.tick(r.world, r.acts)
    if cmd is not None:
        runner.send(cmd)
    return cmd


def test_a_shelter_whose_door_lies_60_tiles_off_walks_a_leg_then_the_machine_s_approach(tmp_path):
    """Ruling P25-N: the first walk is a leg to the square LEG_MAX - LEG_SQ_MARGIN toward the door (139.5, 201.5), at a
    walk, logged `leg` and `legLen`; that leg done, the door within the leg length, the machine's own approach walk to
    the door's approach square (159.5, 201.5), the plan's step `approach` untouched by the leg."""
    from agent.base.planner import goals as G
    r, runner, g = shelter_runner(tmp_path)
    cmd = run_step(r, runner)
    assert (cmd.TYPE, cmd.x, cmd.y, cmd.gait) == ("walkTo", 139.5, 201.5, "walk")
    assert g.why["leg"] == [139.5, 201.5] and g.why["legLen"] == G.LEG_MAX and g.why["step"] == "approach"
    assert g.plan["step"] == "approach"
    r.answer()
    r.frame(x=139.5, y=201.5, game_min=501.0)
    cmd = run_step(r, runner)
    assert (cmd.TYPE, cmd.x, cmd.y) == ("walkTo", 159.5, 201.5) and "leg" not in g.why
    assert g.plan["step"] == "approach" and g.state == "running"
    all_sends_valid(r)


def test_a_leg_s_no_square_halves_it_and_at_leg_min_the_goal_fails_no_square_unshunned(tmp_path):
    """A leg failed `no square` is re-sent at 20, then 10 tiles (LEG_MIN); the third `no square` ends the goal `failed
    "no square"`, cooled (the runner passes it over) and the building not in the kit's `shunned` (the stamp is the
    machine's: F4's loop shunned building 8 on each leg's failure)."""
    r, runner, g = shelter_runner(tmp_path)
    lens = []
    for _ in range(3):
        cmd = run_step(r, runner)
        lens.append(g.why["legLen"])
        assert cmd.TYPE == "walkTo" and g.state == "running"
        r.answer({"state": "failed", "reason": "no square"})
        r.frame(x=100.5, y=201.5, game_min=501.0)
    run_step(r, runner)
    assert lens == [40.0, 20.0, 10.0]
    assert (g.state, g.reason) == ("failed", "no square") and g.cool is True
    assert 1 not in runner.kit.shunned and runner.cooling() == [{"type": "Shelter", "args": {"building": 1}}]


def test_with_shelter_legs_off_the_shelter_walks_to_the_door_s_approach_directly(tmp_path):
    r, runner, g = shelter_runner(tmp_path, legs=False)
    cmd = run_step(r, runner)
    assert (cmd.TYPE, cmd.x, cmd.y) == ("walkTo", 159.5, 201.5) and "leg" not in g.why


def test_through_survive_the_switch_reaches_the_goals_kit_and_the_night(tmp_path):
    """`Survive.SHELTER_LEGS` (`T4_SWITCHES`, the replay tests' `pre_t4`) is copied each tick onto the goals' kit
    (`Kit.shelter_legs`) and the Night (`Night.legs`)."""
    r, sv = make(tmp_path)
    r.frame()
    sv.SHELTER_LEGS = False
    tick(r, sv)
    assert sv.goals.kit.shelter_legs is False and sv.night.legs is False


def test_the_night_s_shelter_approach_walks_in_legs_too(tmp_path):
    """The night instinct's own shelter machine sends the same direct door walk (`night.shelter_step`): tired, with
    building 1's door 60 tiles off, the night's first walk is the leg (logged `leg`, step `approach`); the leg done,
    the approach walk; with SHELTER_LEGS off, the direct approach walk."""
    from .test_night import house, night_why
    r, sv = make(tmp_path)
    r.scan(house(1, FAR_DOOR[0]))
    r.frame(x=100.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 139.5, "y": 201.5, "gait": "walk"})
    w = night_why(tmp_path)
    assert w["step"] == "approach" and w["leg"] == [139.5, 201.5] and w["legLen"] == 40.0
    r.answer()
    r.frame(x=139.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert r.cmd() == ("walkTo", {"x": 159.5, "y": 201.5, "gait": "walk"}) and "leg" not in night_why(tmp_path)
    assert sv.night.plan["step"] == "approach"
    (tmp_path / "off").mkdir()
    r2, sv2 = make(tmp_path / "off")
    sv2.SHELTER_LEGS = False
    r2.scan(house(1, FAR_DOOR[0]))
    r2.frame(x=100.5, y=201.5, fatigue=0.65)
    tick(r2, sv2)
    assert r2.cmd() == ("walkTo", {"x": 159.5, "y": 201.5, "gait": "walk"})


def test_the_night_s_final_leg_failure_is_the_approach_s_own_failure(tmp_path):
    """The night's legs halve on `no square` (40, 20, 10); the failure at LEG_MIN is read into the plan as the direct
    approach walk's `no square` would be (`shelter_ended`: one door, so the machine shuns the building, as before)."""
    from .test_night import house, night_why
    r, sv = make(tmp_path)
    r.scan(house(1, FAR_DOOR[0]))
    lens = []
    for _ in range(3):
        r.frame(x=100.5, y=201.5, fatigue=0.65)
        tick(r, sv)
        lens.append(night_why(tmp_path)["legLen"])
        r.answer({"state": "failed", "reason": "no square"})
    r.frame(x=100.5, y=201.5, fatigue=0.65)
    tick(r, sv)
    assert lens == [40.0, 20.0, 10.0] and 1 in sv.night.shunned and sv.night.plan is None
