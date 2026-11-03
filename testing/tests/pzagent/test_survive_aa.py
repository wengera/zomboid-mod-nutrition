"""Survival 21 (survival iteration 19; Plan 27 Task 1; E18, `e_day_18-20261102-224036`, its `GUIDE.md` §§ 4, 6 and 7:
line 1649's `strain` flee from 30744, knocked down 2.5339841792960844 tiles off, line 939's `many` flee from 30452
fallen, the endurance hold on 271 `strain` lines, the neck's re-dressings at bleedingTime 15.462026596069336 and
13.89616870880127; F9 `f_goals_10-20261102-231705` and F8 `f_goals_9-20261102-181937`). The fake mod over PZA/1.7.1;
each test's geometry is simplified from the line its docstring names.

- P27-A, the finish under a flee (`FLEE_FINISH`): the flee's finish runs under the `strain`, `pair` and `many` flees on
  any zombie the frame reads `onFloor` within FINISH_R (the struck test dropped, logged `struck`), with no standing
  zombie within FINISH_CLEAR_R of the character nor of the fallen one; the `health` flee keeps no finish.
- P27-B, the `many` episode's tail (`MANY_TAIL`): MANY_TAIL_TICKS consecutive ticks with at most one standing zombie
  within DANGER_R and at most one of the listed pressing end the episode (logged `many_tail`).
- P27-C, the hold's lone zombie (`HOLD_LONE`): under the endurance hold alone, one zombie standing within DANGER_R
  and no other chaser listed, the Fight is the shove and the stomp (`shove_only` "hold", logged `hold_fight`).
- P27-C2, the hold's rest (`HOLD_REST`): the endurance hold's `strain` flee with nobody within DANGER_R and no chaser
  listed sends no leg (logged `rest`).
- P27-D, the spent dressing kept (`SPENT_KEEP`): a spent dressing on a part not bleeding is replaced only at a
  bleedingTime at or under SPENT_REDRESS_BT (logged `spent_kept`).
- P27-E, the low fight's swing (`LOW_SWING`): SHOVE_FAIL_N missed shoves at the low fight's lone target take one full
  swing, the miss count reset by it.
"""
import pytest

from agent.base.planner import policies as P
from agent.base.planner import survive as S

from .test_survive import make, threat_why, tick
from .test_survive_g import care_frame, care_why, hold, part
from .test_survive_q import GROUP3, STIFF, fr, struck, z
from .test_survive_t import MISS

FALLEN_D = 2.5339841792960844   # E18's line 1649: 30744 knocked down by the shove a354, read `onFloor` from seq 17980
NECK_BT = 15.462026596069336    # E18's part 9 `bleedingTime` at its first re-dressing (GUIDE § 7)
HOLD_E = 0.6897225379943848     # E18's line 1649 endurance (the hold's `strain` why)
ATTACK_DONE = {"state": "done", "result": {"swings": 1, "attackStarted": True, "meleeDelay": 0.0,
                                           "targetDead": False}}


def sends(r):
    return [a.type for a in r.acts.history]


def test_the_iteration_19_switches_and_constants():
    assert S.T9_SWITCHES == ("FLEE_FINISH", "MANY_TAIL")
    assert "T9_SWITCHES" in S.__all__
    assert all(getattr(S.Survive, name) is True for name in S.T9_SWITCHES)
    assert not set(S.T9_SWITCHES) & set(S.T8_SWITCHES + S.T7_SWITCHES + S.T6_SWITCHES)
    assert (P.FINISH_CLEAR_R, P.MANY_TAIL_TICKS) == (3.0, 4)


# ================================================================ P27-A: the finish under a flee
def e18_1649(standing_at=(100.0, 204.5)):
    """E18's line 1649, simplified: the endurance hold (0.6897225379943848), 30744 fallen 2.5339841792960844 tiles
    east, a standing zombie at `standing_at` (4.5 tiles north: within DANGER_R, beyond FINISH_CLEAR_R) and a chaser 9
    tiles west (E18's 30735 chased 8.7463 tiles off): the lone hold fight is refused for the chaser, so the flee is
    `strain`. E18's own frame read no standing zombie within DANGER_R (30738 idle at 8.4365 tiles); the standing one
    here is the case the clearance reads."""
    return [z(30744, 100.0 + FALLEN_D, floor=True), z(30738, *standing_at), z(30735, 91.0)]


def test_e18_s_30744_knocked_down_under_the_strain_flee_is_stomped(tmp_path):
    """E18's line 1649 (the `strain` flee ran from 30744, fallen 2.5339841792960844 tiles off, no stomp sent): the
    flee's first answer is the stomp, the Flee's own action, logged `finish` and `flee_finish` {reason strain, struck
    False (no swing of this planner's struck it), clear 4.5}; the steer follows on the next tick."""
    r, sv = make(tmp_path)
    fr(r, e18_1649(), endurance=HOLD_E)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 30744}) and w["flee"] == "strain" and sv.flee.last is a
    assert w["finish"] == 30744 and w["kind"] == "stomp" and w["dist"] == pytest.approx(FALLEN_D)
    assert w["flee_finish"] == {"reason": "strain", "struck": False, "clear": 4.5}
    r.answer({"state": "done", "result": {"hit": True, "attackStarted": True, "targetDead": False}})
    fr(r, e18_1649(), endurance=HOLD_E)
    assert tick(r, sv).type == "steer"


@pytest.mark.parametrize("dist, want", [(2.9, "steer"), (3.1, "stomp")])
def test_a_standing_zombie_within_finish_clear_r_of_the_character_refuses_the_finish(tmp_path, dist, want):
    """The same geometry with the standing zombie 2.9 tiles north (within FINISH_CLEAR_R): the flee runs, no finish;
    at 3.1 the stomp goes."""
    r, sv = make(tmp_path)
    fr(r, e18_1649((100.0, 200.0 + dist)), endurance=HOLD_E)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == want and w["flee"] == "strain"
    assert ("finish" in w) is (want == "stomp")


def test_a_chaser_within_finish_clear_r_of_the_fallen_one_refuses_the_finish(tmp_path):
    """A chaser standing 2.9 tiles east of the fallen one (5.43 from the character): `finish_block` {target, chaser},
    the flee as today."""
    r, sv = make(tmp_path)
    zs = [z(30744, 100.0 + FALLEN_D, floor=True), z(30738, 100.0 + FALLEN_D + 2.9), z(30735, 91.0)]
    fr(r, zs, endurance=HOLD_E)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and "finish" not in w and w["finish_block"]["chaser"] == 30738


def test_the_health_flee_keeps_no_finish(tmp_path):
    """Health 30 with the same geometry (two within DANGER_R: no low fight): the `health` flee, no finish (a stomp at
    FLEE_HEALTH is the fall the guides warn of)."""
    r, sv = make(tmp_path)
    fr(r, e18_1649(), health=30.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and w["flee"] == "health" and "finish" not in w


def test_the_many_case_of_p24_aq_still_stomps_and_logs_the_struck_read(tmp_path):
    """P24-AQ's case (`test_survive_q`): the struck target fallen at 1.5 tiles under the `many` flee, GROUP3 chasing 7.5
    tiles off: the stomp, logged `flee_finish` {reason many, struck True, clear 7.5}."""
    r, sv = struck(tmp_path)
    fr(r, [z(1, 101.5, floor=True)] + GROUP3)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and w["flee"] == "many"
    assert w["flee_finish"] == {"reason": "many", "struck": True, "clear": 7.5}


def test_a_fallen_zombie_never_struck_under_the_many_flee_is_stomped_and_with_the_switch_off_left(tmp_path):
    """E18's line 939 (30452 fallen off its window climb 2.053499872133796 tiles off under the `many` flee, never
    struck, no stomp sent): the struck test dropped, it is stomped; with `FLEE_FINISH` off, P24-AQ leaves it."""
    r, sv = make(tmp_path)
    fr(r, [z(30452, 102.053499872133796, floor=True)] + GROUP3)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 30452}) and w["flee"] == "many"
    assert w["flee_finish"]["struck"] is False
    (tmp_path / "off").mkdir()
    r2, sv2 = make(tmp_path / "off")
    sv2.FLEE_FINISH = False
    fr(r2, [z(30452, 102.053499872133796, floor=True)] + GROUP3)
    assert tick(r2, sv2).type == "steer" and "finish" not in threat_why(tmp_path / "off")


def test_the_pair_flee_s_finish_is_the_flee_finish_logged_pair(tmp_path):
    """A running `pair` flee (health 55, two within DANGER_R) whose nearer zombie falls 2.5 tiles off with the other 4.5
    off: the stomp, logged `flee_finish` {reason pair} with `pair_yield`."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 102.5), z(2, 100.0, 204.5)], health=55.0)
    assert tick(r, sv).type == "steer" and threat_why(tmp_path)["flee"] == "pair"
    r.answer()
    fr(r, [z(1, 102.5, floor=True), z(2, 100.0, 204.5)], health=55.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and w["flee"] == "pair"
    assert w["flee_finish"]["reason"] == "pair" and w["pair_yield"] == 1



def test_the_old_sessions_replays_stomp_the_fallen_their_flees_left():
    """The replays at HEAD of the old sessions the rule reaches (open loop): E9's stomps 7479 at line 274 (fallen 4.42
    tiles off, the nearest standing 10.25) and 7481 at line 363 (4.45, the nearest standing 7.42) under the `many`
    flee, neither struck; with `FLEE_FINISH` off neither goes (P24-AQ: no finish on E9's replay at all)."""
    from .test_survive_o import e9_lines
    got = e9_lines()
    fin = {k: (d["why"]["finish"], d["why"]["flee_finish"]) for k, d in got.items() if d["why"].get("finish")}
    assert sorted(fin) == [274, 363] and (fin[274][0], fin[363][0]) == (7479, 7481)
    assert all(f["reason"] == "many" and f["struck"] is False for _, f in fin.values())
    assert got[274]["action"] == {"type": "stomp", "args": {"targetId": 7479}}
    assert not any(d["why"].get("finish") for d in e9_lines(("FLEE_FINISH",)).values())

# ================================================================ P27-B: the `many` episode's tail
START = [z(1, 103.0), z(2, 103.0, 201.0), z(3, 104.0)]   # three chasing within 4 tiles: the `many` episode
STRUNG = [z(1, 105.0), z(2, 100.0, 188.5, has_target=False), z(3, 88.5, has_target=False)]   # one chasing at 5, two
# idle 11.5 tiles off (listed, beyond DISENGAGE_R, neither chasing): one standing within DANGER_R, one pressing
SECOND = [z(1, 105.0), z(2, 100.0, 205.0), z(3, 88.5, has_target=False)]   # a second standing within DANGER_R


def many_episode(tmp_path):
    r, sv = make(tmp_path)
    fr(r, START)
    assert tick(r, sv).type == "steer" and threat_why(tmp_path)["flee"] == "many"
    r.answer()
    return r, sv


def strung_tick(r, sv, tmp_path, zs=STRUNG):
    """Half a second on, the frame `zs` read and planned; a leg it sends ends at once."""
    r.advance(0.5)
    fr(r, zs)
    n = len(r.acts.history)
    tick(r, sv)
    if len(r.acts.history) > n:
        r.answer()
    return threat_why(tmp_path)


def test_a_many_episode_strung_out_for_many_tail_ticks_ends_and_the_lone_one_is_fought(tmp_path):
    """The group strung out (one chasing 5 tiles off, the rest idle 11.5 off: E18's 168 `many` lines with one or none
    within DANGER_R): three ticks the episode holds (`many`), the fourth ends it, logged `many_tail` {ticks 4, standing
    1, pressing 1}, and the lone one is fought by the ordinary rules."""
    r, sv = many_episode(tmp_path)
    for k in range(P.MANY_TAIL_TICKS - 1):
        w = strung_tick(r, sv, tmp_path)
        assert w["flee"] == "many" and "many_tail" not in w, k
    w = strung_tick(r, sv, tmp_path)
    assert w["many_tail"] == {"ticks": 4, "standing": 1, "pressing": 1}
    assert sv.mode == "fight" and w["fight"] is True and "flee" not in w and not sv.flee_many


def test_three_strung_out_ticks_then_a_second_within_danger_r_resets_the_count(tmp_path):
    """Three strung-out ticks, then a second zombie standing within DANGER_R: the count resets (the episode never ends
    while two stand within DANGER_R), so three more strung-out ticks still flee `many` and the fourth ends it."""
    r, sv = many_episode(tmp_path)
    for _ in range(3):
        assert strung_tick(r, sv, tmp_path)["flee"] == "many"
    w = strung_tick(r, sv, tmp_path, SECOND)
    assert w["flee"] == "many" and sv.many_tail_n == 0
    for k in range(3):
        w = strung_tick(r, sv, tmp_path)
        assert w["flee"] == "many" and "many_tail" not in w, k
    assert strung_tick(r, sv, tmp_path)["many_tail"]["ticks"] == 4


def test_with_many_tail_off_the_strung_out_episode_holds(tmp_path):
    r, sv = many_episode(tmp_path)
    sv.MANY_TAIL = False
    for _ in range(6):
        w = strung_tick(r, sv, tmp_path)
        assert w["flee"] == "many" and "many_tail" not in w
