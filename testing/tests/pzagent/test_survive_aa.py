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

from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S

from .test_survive import make, threat_why, tick
from .test_survive_g import care_frame, care_why, hold, part
from .test_survive_q import GROUP3, STIFF, fr, struck, z
from .test_survive_t import MISS, riding

FALLEN_D = 2.5339841792960844   # E18's line 1649: 30744 knocked down by the shove a354, read `onFloor` from seq 17980
NECK_BT = 15.462026596069336    # E18's part 9 `bleedingTime` at its first re-dressing (GUIDE § 7)
HOLD_E = 0.6897225379943848     # E18's line 1649 endurance (the hold's `strain` why)
ATTACK_DONE = {"state": "done", "result": {"swings": 1, "attackStarted": True, "meleeDelay": 0.0,
                                           "targetDead": False}}


def sends(r):
    return [a.type for a in r.acts.history]


def test_the_iteration_19_switches_and_constants():
    assert S.T9_SWITCHES == ("FLEE_FINISH", "MANY_TAIL", "HOLD_LONE", "HOLD_REST", "SPENT_KEEP", "LOW_SWING")
    assert "T9_SWITCHES" in S.__all__ and "low_swing" in F.FIGHT_RULES
    assert all(getattr(S.Survive, name) is True for name in S.T9_SWITCHES)
    assert not set(S.T9_SWITCHES) & set(S.T8_SWITCHES + S.T7_SWITCHES + S.T6_SWITCHES)
    assert (P.FINISH_CLEAR_R, P.MANY_TAIL_TICKS, P.SPENT_REDRESS_BT) == (3.0, 4, 10.0)


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
    struck, no stomp sent): the struck test dropped, it is stomped; with `FLEE_FINISH` off, P24-AQ leaves it. Named
    change, ruling P27-I (Plan 27 Task 5): pinned with `LISTING_FALLEN` off (GROUP3's three and the fallen one make
    `many` only with the fallen counted)."""
    r, sv = make(tmp_path)
    sv.LISTING_FALLEN = False
    fr(r, [z(30452, 102.053499872133796, floor=True)] + GROUP3)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 30452}) and w["flee"] == "many"
    assert w["flee_finish"]["struck"] is False
    (tmp_path / "off").mkdir()
    r2, sv2 = make(tmp_path / "off")
    sv2.FLEE_FINISH = False
    sv2.LISTING_FALLEN = False
    fr(r2, [z(30452, 102.053499872133796, floor=True)] + GROUP3)
    assert tick(r2, sv2).type == "steer" and "finish" not in threat_why(tmp_path / "off")


def test_a_fallen_zombie_whose_one_stomp_is_spent_leaves_the_next_one_in_reach_to_be_finished(tmp_path):
    """Review minor 1 (P24-AQ's case, `test_survive_q`, with a second fallen zombie): 1 fallen at 1.5 tiles is stomped
    once and survives (the stomp done, no `stood`, its end None), 9 fallen at 3.0 tiles with the clearance kept: the
    next tick's stomp is at 9, not silence at the spent 1."""
    r, sv = struck(tmp_path)
    zs = [z(1, 101.5, floor=True), z(9, 103.0, floor=True)] + GROUP3
    fr(r, zs)
    a = tick(r, sv)
    assert (a.type, a.args) == ("stomp", {"targetId": 1}) and threat_why(tmp_path)["flee"] == "many"
    r.answer({"state": "done", "result": {"hit": True, "attackStarted": True, "targetDead": False}})
    r.advance(0.5)
    fr(r, zs)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("stomp", {"targetId": 9}) and w["finish"] == 9 and w["flee"] == "many"


def test_the_flee_finish_logs_the_tick_s_own_flee_reason(tmp_path):
    """Review minor 5 (E18's line 1649, `e18_1649`; P24-AQ's `GROUP3` with the nearest standing zombie then fallen): a
    `strain` tick logs `flee_finish` reason "strain"; a tick of a `many` episode that now reads `unarmed` (the weapon
    gone) logs "unarmed", not "many"."""
    r, sv = make(tmp_path)
    fr(r, e18_1649(), endurance=HOLD_E)
    tick(r, sv)
    assert threat_why(tmp_path)["flee_finish"]["reason"] == "strain"
    (tmp_path / "unarmed").mkdir()
    r2, sv2 = make(tmp_path / "unarmed")
    fr(r2, [z(1, 104.0)] + GROUP3)
    tick(r2, sv2)
    assert sv2.flee_many and threat_why(tmp_path / "unarmed")["flee"] == "many"
    r2.answer()
    fr(r2, [z(1, 101.5, floor=True)] + GROUP3, weapon=None)
    assert tick(r2, sv2).type == "stomp"
    w = threat_why(tmp_path / "unarmed")
    assert w["flee"] == "unarmed" and w["flee_finish"]["reason"] == "unarmed"


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
    flee, neither struck; with `FLEE_FINISH` off neither goes (P24-AQ: no finish on E9's replay at all). Named change,
    ruling P27-I (Plan 27 Task 5): read with `LISTING_FALLEN` off (with it on, E9's fallen leave the listing and the
    `many` episodes these finishes ran under move)."""
    from .test_survive_o import e9_lines
    got = e9_lines(("LISTING_FALLEN",))
    fin = {k: (d["why"]["finish"], d["why"]["flee_finish"]) for k, d in got.items() if d["why"].get("finish")}
    assert sorted(fin) == [274, 363] and (fin[274][0], fin[363][0]) == (7479, 7481)
    assert all(f["reason"] == "many" and f["struck"] is False for _, f in fin.values())
    assert got[274]["action"] == {"type": "stomp", "args": {"targetId": 7479}}
    assert not any(d["why"].get("finish") for d in e9_lines(("FLEE_FINISH", "LISTING_FALLEN")).values())

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
    """`test_a_many_episode_strung_out_for_many_tail_ticks_ends_and_the_lone_one_is_fought`'s geometry (`STRUNG`) with
    `MANY_TAIL` off: six strung-out ticks and the `many` episode holds, no `many_tail`."""
    r, sv = many_episode(tmp_path)
    sv.MANY_TAIL = False
    for _ in range(6):
        w = strung_tick(r, sv, tmp_path)
        assert w["flee"] == "many" and "many_tail" not in w


# ================================================================ P27-C: the hold's lone zombie
def test_e18_s_hold_with_one_zombie_at_4_tiles_is_the_hold_fight(tmp_path):
    """E18's endurance hold (fights 21 to 39 each fled `strain`; `inputs.threats` 1 on 57 of its 271 lines) with one
    zombie 4 tiles off and no other listed: the Fight (`shove_only` "hold"), logged `hold_fight`, no `strain` flee; at
    point blank the shove (`shove` "hold"), never an attack."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 104.0)], endurance=HOLD_E)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "aim" and sv.mode == "fight" and sv.fight.shove_only == "hold"
    assert w["hold_fight"] is True and "flee" not in w and "low_fight" not in w and not w.get("seek")
    r.advance(0.5)
    fr(r, [z(1, 100.8)], endurance=HOLD_E)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("shove", {"targetId": 1}) and w["shove"] == "hold" and w["hold_fight"] is True
    assert "attack" not in sends(r)


@pytest.mark.parametrize("second", [z(2, 91.0), z(2, 100.0, 205.0, has_target=False)])
def test_a_second_chaser_listed_or_a_second_within_danger_r_flees_strain(tmp_path, second):
    """A second chaser 9 tiles off (listed within LISTED_R), or a second zombie standing within DANGER_R: the `strain`
    flee as before."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 104.0), second], endurance=HOLD_E)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and w["flee"] == "strain" and "hold_fight" not in w


def test_the_arms_hold_and_the_endurance_hold_under_flee_health_pair_flee_strain(tmp_path):
    """The arms' hold (a stiffness of 25) with the same lone zombie: `strain`; the endurance hold at health 55 (under
    FLEE_HEALTH_PAIR): `strain`."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 104.0)], 25.0, STIFF)
    assert tick(r, sv).type == "steer" and threat_why(tmp_path)["flee"] == "strain"
    (tmp_path / "low").mkdir()
    r2, sv2 = make(tmp_path / "low")
    fr(r2, [z(1, 104.0)], endurance=HOLD_E, health=55.0)
    assert tick(r2, sv2).type == "steer" and threat_why(tmp_path / "low")["flee"] == "strain"


def test_with_hold_lone_off_the_lone_zombie_is_fled_strain(tmp_path):
    """`test_e18_s_hold_with_one_zombie_at_4_tiles_is_the_hold_fight`'s geometry (one zombie 4 tiles off, the endurance
    hold) with `HOLD_LONE` off: the `strain` flee as before."""
    r, sv = make(tmp_path)
    sv.HOLD_LONE = False
    fr(r, [z(1, 104.0)], endurance=HOLD_E)
    assert tick(r, sv).type == "steer" and threat_why(tmp_path)["flee"] == "strain"


# ================================================================ P27-C2: the hold's rest
IDLE2 = z(2, 100.0, 209.0, has_target=False)   # a second zombie listed 9 tiles off, idle (the World keeps it listed)


def strain_run(tmp_path):
    """The endurance hold's `strain` flee at a run: two zombies within DANGER_R, 5 tiles east and 5 north (the lone
    hold fight refused); its leg ends."""
    r, sv = make(tmp_path)
    fr(r, [z(1, 105.0), z(2, 100.0, 205.0)], endurance=HOLD_E)
    a = tick(r, sv)
    assert a.type == "steer" and a.args["gait"] == "run" and threat_why(tmp_path)["flee"] == "strain"
    r.answer()
    r.advance(0.5)
    return r, sv


def test_the_hold_with_no_chaser_listed_rests(tmp_path):
    """E18's hold walked on 158 of its 271 `strain` lines, `inputs.threats` 0 on 213: with the two listed 8 and 9
    tiles off and idle (`hasTarget` false) the flee sends nothing, logged `rest` {endurance, since_min 0.0}; a game
    minute on it rests on (`since_min` 1.0)."""
    r, sv = strain_run(tmp_path)
    n = len(r.acts.history)
    fr(r, [z(1, 108.0, has_target=False), IDLE2], endurance=HOLD_E)
    assert tick(r, sv) is None
    w = threat_why(tmp_path)
    assert w["flee"] == "strain" and w["rest"] == {"endurance": HOLD_E, "since_min": 0.0}
    assert len(r.acts.history) == n and "hold_walk" not in w
    r.advance(0.5)
    fr(r, [z(1, 108.0, has_target=False), IDLE2], endurance=HOLD_E, game_min=481.0)
    assert tick(r, sv) is None and threat_why(tmp_path)["rest"]["since_min"] == pytest.approx(1.0)


def test_a_chaser_listed_10_tiles_off_restores_the_walk(tmp_path):
    """One chaser 10 tiles off (within LISTED_R): P25-C's walk, logged `hold_walk`, no `rest`."""
    r, sv = strain_run(tmp_path)
    fr(r, [z(1, 110.0), IDLE2], endurance=HOLD_E)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and a.args["gait"] == "walk" and w["hold_walk"] is True and "rest" not in w


def test_a_zombie_within_danger_r_runs(tmp_path):
    """Two within DANGER_R again: the run (the running leg ended), no `rest`."""
    r, sv = strain_run(tmp_path)
    fr(r, [z(1, 105.0), z(2, 100.0, 205.0)], endurance=HOLD_E)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "steer" and a.args["gait"] == "run" and "rest" not in w and w["flee"] == "strain"


def test_with_hold_rest_off_the_hold_walks(tmp_path):
    """`strain_run`'s hold with the two idle zombies listed 8 and 9 tiles off (the rest test's geometry) and `HOLD_REST`
    off: P25-C's walk, no `rest`."""
    r, sv = strain_run(tmp_path)
    sv.HOLD_REST = False
    fr(r, [z(1, 108.0, has_target=False), IDLE2], endurance=HOLD_E)
    a = tick(r, sv)
    assert a.type == "steer" and a.args["gait"] == "walk" and "rest" not in threat_why(tmp_path)


def rest_tick(r, sv, minute):
    """One rest tick of `strain_run`'s hold at game minute `minute` (the two idle zombies 8 and 9 tiles off): the why's
    `rest.since_min`."""
    r.advance(0.5)
    fr(r, [z(1, 108.0, has_target=False), IDLE2], endurance=HOLD_E, game_min=minute)
    assert tick(r, sv) is None
    return threat_why(r.dir)["rest"]["since_min"]


@pytest.mark.parametrize("kind", ["hold", "doorway"])
def test_a_rest_run_broken_by_a_hold_or_doorway_decision_restarts_since_min(tmp_path, monkeypatch, kind):
    """Review minor 4 (the rest of `test_the_hold_with_no_chaser_listed_rests`): a rest tick, a tick the threat plan
    answers `hold` (held inside) or `doorway` (the stand) is not the rest, so `rest_from` is reset and the next rest
    tick, a game minute later, reads `since_min` 0.0 (not 1.0)."""
    r, sv = strain_run(tmp_path)
    assert rest_tick(r, sv, 480.0) == 0.0 and sv.rest_from is not None
    plan = sv._threat_plan
    monkeypatch.setattr(sv, "_threat_plan", lambda held, breach: (kind, None))
    monkeypatch.setattr(sv, "_stand", lambda held: (None, None))
    r.advance(0.5)
    fr(r, [z(1, 108.0, has_target=False), IDLE2], endurance=HOLD_E, game_min=480.5)
    tick(r, sv)
    assert sv.rest_from is None
    monkeypatch.setattr(sv, "_threat_plan", plan)
    assert rest_tick(r, sv, 481.0) == 0.0


def test_a_care_yield_between_two_rest_ticks_keeps_the_rest_counting(tmp_path, monkeypatch):
    """Review minor 4, ruling P27-2b: a tick yielded to the care (a bandage sent standing still) continues the rest:
    `rest_from` is kept and the next rest tick, a game minute after the first, reads `since_min` 1.0."""
    r, sv = strain_run(tmp_path)
    assert rest_tick(r, sv, 480.0) == 0.0
    monkeypatch.setattr(sv, "_care_yields", lambda held: 9.0)
    r.advance(0.5)
    fr(r, [z(1, 108.0, has_target=False), IDLE2], endurance=HOLD_E, game_min=480.5)
    tick(r, sv)
    assert threat_why(r.dir)["care"] is True and sv.rest_from is not None
    monkeypatch.undo()
    assert rest_tick(r, sv, 481.0) == pytest.approx(1.0)


# ================================================================ P27-D: the spent dressing kept
def neck(r, bt=NECK_BT, bleeding=False, items=((11, "Base.Bandage"),)):
    r.frame()
    for iid, full in items:
        hold(r, iid, full)
    care_frame(r, [part(9, bandaged=True, bandageLife=0.0, bandageDirty=True, bleeding=bleeding, bleedingTime=bt)])


def test_e18_s_neck_under_its_spent_dressing_is_kept(tmp_path):
    """E18's part 9 at its first re-dressing (GUIDE § 7: `bandaged` true, `bandageDirty` true, `bandageLife` 0, bleeding
    false, bleedingTime 15.462026596069336; the re-dressing took the health from 82.34173583984375 to
    67.09330749511719): no bandage, logged `spent_kept` {part 9, bleedingTime, dirty true}."""
    r, sv = make(tmp_path)
    neck(r)
    tick(r, sv)
    assert "bandage" not in sends(r)
    assert care_why(tmp_path)["spent_kept"] == {"part": 9, "bleedingTime": NECK_BT, "dirty": True}


@pytest.mark.parametrize("bt, bleeding", [(9.0, False), (NECK_BT, True), (P.SPENT_REDRESS_BT, False)])
def test_a_spent_dressing_is_replaced_at_a_short_bleed_or_a_bleeding_part(tmp_path, bt, bleeding):
    """bleedingTime 9.0 or at SPENT_REDRESS_BT, or the part bleeding under the dressing whatever the time: the clean
    bandage (`reason` spent), no `spent_kept`."""
    r, sv = make(tmp_path)
    neck(r, bt, bleeding)
    tick(r, sv)
    w = care_why(tmp_path)
    assert r.cmd() == ("bandage", {"itemId": 11, "part": 9}) and w["reason"] == "spent" and "spent_kept" not in w


def test_the_replace_still_prefers_a_clean_bandage_to_a_rag(tmp_path):
    """`neck` at bleedingTime 9.0 (the short-bleed test's geometry) holding a ripped sheet and a bandage: the bandage
    (13) is the one sent, not the rag (12)."""
    r, sv = make(tmp_path)
    neck(r, 9.0, items=((12, "Base.RippedSheets"), (13, "Base.Bandage")))
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 13, "part": 9}) and care_why(tmp_path)["kind"] == "bandage"


def test_with_spent_keep_off_the_long_bleed_is_redressed(tmp_path):
    """E18's neck (`test_e18_s_neck_under_its_spent_dressing_is_kept`'s geometry, bleedingTime 15.46) with `SPENT_KEEP`
    off: the bandage is sent as before."""
    r, sv = make(tmp_path)
    sv.SPENT_KEEP = False
    neck(r)
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 11, "part": 9})


# ================================================================ P27-E: the low fight's swing
def shoves(r, sv, n, **k):
    """`n` shoves at the lone zombie at point blank (0.8 tiles), each answered missed (done, `knockdown` false), a
    second between them."""
    for _ in range(n):
        lone(r, **k)
        a = tick(r, sv)
        assert (a.type, a.args) == ("shove", {"targetId": 1}), a
        r.fake.answer({"shove": ["accepted", MISS]})
        r.pump()
        r.advance(1.0)


def lone(r, health=35.0, **k):
    fr(r, [z(1, 100.8)], health=health, **k)


def test_the_low_fight_swings_after_three_missed_shoves_then_shoves_again(tmp_path):
    """F8's last fight (28762 shoved six times, never swung at) in the low fight (health 35): after SHOVE_FAIL_N missed
    shoves the full swing (`attack`, logged `low_swing` {target, missed 3}); its end read, the shove again (the count
    reset by the swing, so no second swing at once)."""
    r, sv = make(tmp_path)
    shoves(r, sv, P.SHOVE_FAIL_N)
    lone(r)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and w["low_swing"] == {"target": 1, "missed": 3}
    assert w["low_fight"] is True and sv.fight._miss_run.get(1, 0) == 0
    r.fake.answer({"attack": ["accepted", ATTACK_DONE]})
    r.pump()
    r.advance(1.0)
    lone(r)
    a = tick(r, sv)
    assert (a.type, a.args) == ("shove", {"targetId": 1}) and "low_swing" not in threat_why(tmp_path)


def test_two_missed_shoves_shove_again(tmp_path):
    """`test_the_low_fight_swings_after_three_missed_shoves_then_shoves_again`'s geometry (health 35, the lone target at
    point blank) after SHOVE_FAIL_N - 1 missed shoves: the shove again, no `low_swing`."""
    r, sv = make(tmp_path)
    shoves(r, sv, 2)
    lone(r)
    a = tick(r, sv)
    assert a.type == "shove" and "low_swing" not in threat_why(tmp_path)


def test_the_unarmed_and_the_hold_fights_keep_no_swing_after_three_missed_shoves(tmp_path):
    """The unarmed fight (no weapon, health 100) and the hold fight (the endurance hold) after three missed shoves: no
    `attack` (P25-T's lone break, a steer, takes the count)."""
    for name, k in (("unarmed", {"health": 100.0, "weapon": None}), ("hold", {"health": 100.0, "endurance": HOLD_E})):
        (tmp_path / name).mkdir()
        r, sv = make(tmp_path / name)
        shoves(r, sv, P.SHOVE_FAIL_N, **k)
        lone(r, **k)
        a = tick(r, sv)
        assert a.type != "attack" and "attack" not in sends(r) and "low_swing" not in threat_why(tmp_path / name), name


def test_with_low_swing_off_the_low_fight_never_swings(tmp_path):
    """The same geometry after SHOVE_FAIL_N missed shoves with `LOW_SWING` off: no `attack` is ever sent."""
    r, sv = make(tmp_path)
    sv.LOW_SWING = False
    shoves(r, sv, P.SHOVE_FAIL_N)
    lone(r)
    a = tick(r, sv)
    assert a.type != "attack" and "attack" not in sends(r)


def test_a_riding_bandage_holds_the_due_low_swing(tmp_path):
    """Review minor 2 (P25-D's `test_e11_s_rides_...` in `test_survive_t`, with the low fight's swing due): three missed
    shoves at the lone 28762-like target at point blank, a bandage riding (`fight.ride`): no `attack` is sent, the tick
    logs `ride_wait` (the ride's aid) and the bandage stays the current action."""
    r, sv = make(tmp_path)
    shoves(r, sv, P.SHOVE_FAIL_N)
    ride = riding(r, sv)
    lone(r)
    assert tick(r, sv) is None
    w = threat_why(tmp_path)
    assert w["ride_wait"] == ride.aid and r.acts.history[-1] is ride
    assert "attack" not in sends(r) and "low_swing" not in w


def test_the_swing_from_fight_reach_is_followed_by_the_backpedal(tmp_path):
    """Review minor 3 (the brief's `the full swing at FIGHT_REACH, then the backpedal`): after three missed shoves the
    target stands 1.5 tiles off (within FIGHT_REACH, beyond point blank): the full swing goes (`no_swing`'s exception
    lets the wounded backpedal give way), and on the next tick the `aim` back leg, not a second swing."""
    r, sv = make(tmp_path)
    shoves(r, sv, P.SHOVE_FAIL_N)
    fr(r, [z(1, 101.5)], health=35.0)
    a = tick(r, sv)
    assert (a.type, a.args) == ("attack", {"targetId": 1}) and threat_why(tmp_path)["low_swing"]["missed"] == 3
    r.fake.answer({"attack": ["accepted", ATTACK_DONE]})
    r.pump()
    r.advance(1.0)
    fr(r, [z(1, 101.5)], health=35.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert a.type == "aim" and a.args["vx"] < -0.9 and w["leg"] == "back" and "low_swing" not in w
    assert sends(r).count("attack") == 1
