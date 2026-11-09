"""Plan 34 Task 3 (the column; F19, `f_goals_19-20261109-060929`, GUIDE.md § 4 "The retreat's live reading"): the
fighting retreat held at the stance's band. Three switches of `survive.T19_SWITCHES` on `threat.Threat`, each a rule of
the Fight (`fight.FIGHT_RULES`) or of the leave (`group.ThreatGroup._group_leave`), and fix B of ruling P34-A:

- RETREAT_GAP (the Fight's `retreat_gap`): under the retreat the stance leg's kind is the distance's own
  (`Fight._retreat_kind`: the backpedal within KEEP_R, held to KEEP_R + KEEP_MARGIN while it runs, else the stand),
  every approaching kind read as the stand, the backpedal's heading the retreat's. F19's episode one (decision lines 274
  to 299) sent 15 back legs at 4.49 to 5.21 tiles, fix 3 forcing every leg to a backpedal.
- RETREAT_MELEE (the Fight's `retreat_melee`): under the retreat a running strike-mode melee whose last progress step is
  no press in flight gives way when a standing zombie other than its target is within RETREAT_BACK_R, logged
  `retreat_break` {other, dist}, the back leg sent in its place. F19's lines 1536 and 1537: a281 held at 0.84 tiles
  while 12454 walked in from behind to 0.49 and bit.
- STRUNG_HOLD (the leave's): the `strung` end only after STRUNG_LINES consecutive lines under GROUP_LEAVE_N. F19's
  episode one: 11 `strung` ends alternating with the retreat's lines.
- CRAWLER_CLEAR (the Fight's `crawler_clear`, ruling P34-A fix B): with a fallen or crawling zombie other than the
  finish target within CRAWLER_AVOID_R, or two such whatever the target, and a standing one within DANGER_R, the
  stance's backpedal away from the fallen zombies, no melee and no stomp until none lies within CRAWLER_AVOID_R. The
  smoke trial `x_trial-ladder-20261109-105452` (P31-T, not evidence): the character stood at the crawlers 9174 and 9175
  while the melee pressed the standing 9128, 13 wounds in 20 s.

The fixtures are synthetic, built from the GUIDE's and the trial row's numbers, never a replay; the fake mod."""
import math

import pytest

from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .fakemod import MELEE_CAPS
from .test_policies import Rig, zombie
from .test_survive import threat_why, tick
from .test_survive_ak import ME, NEAR, WEST_V, closing, fight4, pair, zm


def unit(dx, dy):
    n = math.hypot(dx, dy)
    return dx / n, dy / n


def angle(a, b):
    """Degrees between unit vectors `a` and `b`."""
    return math.degrees(math.acos(max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1]))))


def accept(r, a, step=None):
    """`a` accepted by the fake mod and, with `step`, one progress line of that step."""
    r.fake.act(a.aid, "accepted", a.type)
    if step is not None:
        r.fake.act(a.aid, "progress", a.type, result={"step": step})
    r.pump()


# ================================================================ the switches and the constants
def test_the_switches_and_the_constants():
    """The three Task 3 switches and CRAWLER_CLEAR (ruling P34-A fix B) on `threat.Threat`, on by default, in
    `survive.T19_SWITCHES`; their Fight rules among `fight.FIGHT_RULES`, each dropped by its own switch alone; the
    constants RETREAT_BACK_R 1.5, STRUNG_LINES 3 and CRAWLER_AVOID_R 1.2."""
    for name in ("RETREAT_GAP", "RETREAT_MELEE", "STRUNG_HOLD", "CRAWLER_CLEAR"):
        assert name in S.T19_SWITCHES and getattr(T.Threat, name) is True, name
    assert {"retreat_gap", "retreat_melee", "crawler_clear"} <= set(F.FIGHT_RULES)
    on = type("On", (), {n: getattr(S.Survive, n) for n in [r.upper() for r in F.FIGHT_RULES]})()
    every = T.Threat._fight_rules(on)
    for name in ("RETREAT_GAP", "RETREAT_MELEE", "CRAWLER_CLEAR"):
        setattr(on, name, False)
        assert T.Threat._fight_rules(on) == every - {name.lower()}, name
        setattr(on, name, True)
    assert (P.RETREAT_BACK_R, P.STRUNG_LINES, P.CRAWLER_AVOID_R) == (1.5, 3, 1.2)


# ================================================================ RETREAT_GAP
EPISODE = (4.49, 4.9, 5.21)   # F19's episode one: the nearest standing zombie on the retreat's lines (GUIDE § 4)


def episode(chasing=False):
    """Three standing east of the player at EPISODE's distances (`hasTarget` as `chasing`)."""
    return [zm(i, ME[0] + d, ME[1] + 0.1 * i, hasTarget=chasing) for i, d in enumerate(EPISODE, 1)]


def test_episode_one_s_shape_sends_the_stand_not_the_back_leg(tmp_path):
    """F19's lines 274 to 299: three standing at 4.49, 4.9 and 5.21 tiles under the retreat, the Fight out of the stance
    (three held, over MAX_FIGHT) with the approach walk its ladder's answer: the rule on sends the stand, an `aim` (0, 0)
    facing the nearest (`back` None), `retreat_leg` {kind "stand", in_place_of "walkTo"}."""
    r, f = fight4(tmp_path, episode(), stance=False)
    cmd = f.choose()
    assert (cmd.TYPE, cmd.targetId, cmd.vx, cmd.vy) == ("aim", 1, 0.0, 0.0)
    assert f.why["leg"] == "stand" and f.why["back"] is None and f.why["retreat"] is True
    assert f.why["retreat_leg"] == {"kind": "stand", "in_place_of": "walkTo"}


def test_in_the_stance_the_ladder_s_own_leg_under_the_retreat_is_the_stand(tmp_path):
    """The same three chasing with the Fight in the stance: the ladder's own stance leg is the distance's kind, the
    stand (no `retreat_leg`: nothing replaced)."""
    r, f = fight4(tmp_path, episode(chasing=True))
    cmd = f.choose()
    assert (cmd.TYPE, cmd.vx, cmd.vy) == ("aim", 0.0, 0.0) and f.why["leg"] == "stand"
    assert "retreat_leg" not in f.why


def test_the_pin_within_keep_r_takes_the_back_leg_on_the_retreat_heading(tmp_path):
    """The pin at 2.2 tiles (within KEEP_R, beyond FIGHT_REACH: the brief's 2.0 is FIGHT_REACH itself, the ladder's
    reach) east and two more south-east: the back leg on the retreat heading, away from the group's centroid, which
    differs from the heading away from the pin alone by more than 30 degrees."""
    zs = [zm(1, ME[0] + 2.2, ME[1]), zm(2, ME[0] + 3.0, ME[1] + 3.0), zm(3, ME[0] + 2.0, ME[1] + 4.0)]
    cx = sum(z["x"] for z in zs) / 3
    cy = sum(z["y"] for z in zs) / 3
    away = unit(ME[0] - cx, ME[1] - cy)
    assert angle(away, (-1.0, 0.0)) > 30.0   # away from the pin alone is due west
    r, f = fight4(tmp_path, zs, retreat=away)
    cmd = f.choose()
    assert cmd.TYPE == "aim" and cmd.targetId == 1 and f.why["leg"] == "back"
    assert (cmd.vx, cmd.vy) == pytest.approx(away)


def test_the_pin_in_reach_is_met_by_the_melee_as_before(tmp_path):
    """The pin at 1.2 tiles (within FIGHT_REACH) on a PZA/1.8 build: the melee goes at it as before the rule."""
    zs = [zm(1, ME[0] + 1.2, ME[1]), zm(2, ME[0] + 3.5, ME[1]), zm(3, ME[0] + 4.0, ME[1] + 1.0)]
    r, f = fight4(tmp_path, zs, caps=MELEE_CAPS)
    cmd = f.choose()
    assert (cmd.TYPE, cmd.targetId) == ("melee", 1) and "retreat_leg" not in f.why


def test_a_running_stand_leg_gives_way_within_keep_r_and_a_back_leg_past_its_margin(tmp_path):
    """`busy` under the rule: a running stand leg (the pin at 3.0) holds while the pin stays beyond KEEP_R and gives
    way when it comes to 2.3, the back leg then sent; that back leg holds at 2.6 (within KEEP_R + KEEP_MARGIN, 2.75)
    and gives way at 2.8, the stand then sent."""
    def at(d):
        r.frame(x=ME[0], y=ME[1], zombies=[zm(1, ME[0] + d, ME[1])])
        f.observe()
    r, f = fight4(tmp_path, [zm(1, ME[0] + 3.0, ME[1])], target=1)
    a = f.step()
    accept(r, a)
    assert f.why["leg"] == "stand" and f.busy() is True
    at(2.3)
    assert f.busy() is False
    b = f.step()
    accept(r, b)
    assert b.type == "aim" and f.why["leg"] == "back" and (b.args["vx"], b.args["vy"]) == pytest.approx(WEST_V)
    at(2.6)
    assert f.busy() is True
    at(2.8)
    assert f.busy() is False
    c = f.step()
    assert c.type == "aim" and f.why["leg"] == "stand"


def test_with_retreat_gap_off_fix_3_s_back_leg_goes_at_4_9_tiles(tmp_path):
    """The pin of the rule before it (`retreat_gap` off, Plan 33 Task 3 fix 3): the pin at 4.9 tiles in the stance
    takes the back leg on the retreat heading whatever its distance."""
    r, f = fight4(tmp_path, [zm(1, ME[0] + 4.9, ME[1])], target=1)
    f.rules = f.rules - {"retreat_gap"}
    cmd = f.choose()
    assert cmd.TYPE == "aim" and f.why["leg"] == "back" and (cmd.vx, cmd.vy) == pytest.approx(WEST_V)


def test_the_retreat_leg_logs_its_kind_in_reach_under_a_hit_reaction(tmp_path):
    """The hit reaction's line (Plan 33 Task 3 fix 4 (b)'s shape, the pin at 1.5 within reach): the back leg as before,
    `retreat_leg` now carrying its kind, {kind "back", in_place_of None}."""
    zs = [zm(1, 102.0, 200.5), zm(2, 103.5, 200.5), zm(3, 104.0, 201.5)]
    r, f = fight4(tmp_path, zs, stance=False, target=1, hit_reaction="Bite")
    cmd = f.choose()
    assert cmd.TYPE == "aim" and (cmd.vx, cmd.vy) == pytest.approx(WEST_V)
    assert f.why["retreat_leg"] == {"kind": "back", "in_place_of": None}


# ================================================================ STRUNG_HOLD
THREE = NEAR                                  # 2.91, 2.90 and 5.8 tiles: three within GROUP_ENTRY_R
TWO = NEAR[:2] + ((100.5, 207.5),)            # the third at 7.0, beyond it


def strung(tmp_path, counts, hold=True):
    """The leave opened (`closing`), then one line a count of `counts` (3 or 2 standing within GROUP_ENTRY_R), with
    STRUNG_HOLD `hold`; the `group_leave` why of each line."""
    r, sv = closing(tmp_path)
    sv.STRUNG_HOLD = hold
    assert sv.leave is not None
    out = []
    for n in counts:
        r.advance(0.5)
        r.frame(x=100.5, y=200.5, zombies=pair(THREE if n == 3 else TWO))
        tick(r, sv)
        out.append(threat_why(tmp_path)["group_leave"])
    return sv, out


def test_the_strung_end_waits_for_strung_lines_lines_under_the_count(tmp_path):
    """F19's episode one's flicker: the count 3, 2, 3, 2, 2, 2 over six lines: the leave holds through the first five
    (`strung_n` 0, 1, 0, 1, 2: logged on the lines under the count, absent at it) and ends `strung` on the sixth."""
    sv, gl = strung(tmp_path, (3, 2, 3, 2, 2, 2))
    assert [g.get("strung_n", 0) for g in gl[:5]] == [0, 1, 0, 1, 2]
    assert ["strung_n" in g for g in gl[:5]] == [False, True, False, True, True]
    assert [g["n"] for g in gl[:5]] == [3, 2, 3, 2, 2] and all(g["leg"] == "retreat" for g in gl[:5])
    assert gl[5] == {"end": "strung", "n": 2} and sv.leave is None and sv.strung_n == 0


def test_with_strung_hold_off_the_leave_ends_on_the_first_line_under_the_count(tmp_path):
    """The pin of the rule before it (STRUNG_HOLD off): the same lines end the leave `strung` on the second."""
    sv, gl = strung(tmp_path, (3, 2), hold=False)
    assert gl[0] == {"n": 3, "leg": "retreat"} and gl[1] == {"end": "strung", "n": 2} and sv.leave is None


# ================================================================ RETREAT_MELEE
NORTH = (0.0, -1.0)


def melee_at(tmp_path, other, step, rule=True):
    """F19's lines 1535 to 1537: the strike melee sent at 1 at 0.84 tiles east under the retreat (2 standing 1.9 tiles
    west), accepted, its progress at `step`; then 2 at `other` tiles west. The Fight, observed."""
    r, f = fight4(tmp_path, [zm(1, ME[0] + 0.84, ME[1]), zm(2, ME[0] - 1.9, ME[1])], retreat=NORTH, target=1,
                  caps=MELEE_CAPS)
    if not rule:
        f.rules = f.rules - {"retreat_melee"}
    a = f.step()
    assert (a.type, a.args["targetId"], a.args["mode"]) == ("melee", 1, "strike")
    accept(r, a, step)
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, ME[0] + 0.84, ME[1]), zm(2, ME[0] - other, ME[1])])
    f.observe()
    return r, f


def test_a_strike_melee_not_pressing_gives_way_to_a_zombie_behind_within_retreat_back_r(tmp_path):
    """F19's lines 1536 and 1537 (a281 held while 12454 walked in from behind to 0.49 tiles): the melee's last step
    `face`, 2 at 0.49 behind: `busy` False, and the next choose sends the back leg on the retreat heading in the melee's
    place, logged `retreat_break` {other 2, dist 0.49}."""
    r, f = melee_at(tmp_path, 0.49, "face")
    assert f.busy() is False
    cmd = f.choose()
    assert cmd.TYPE == "aim" and (cmd.vx, cmd.vy) == pytest.approx(NORTH) and f.why["leg"] == "back"
    assert f.why["retreat_break"]["other"] == 2 and f.why["retreat_break"]["dist"] == pytest.approx(0.49)


@pytest.mark.parametrize("step, rule, holds", [("face", True, False), ("swing", True, True), ("shove", True, True),
                                               ("face", False, True)])
def test_the_give_way_at_1_2_tiles_waits_for_a_press_in_flight_and_the_switch(tmp_path, step, rule, holds):
    """2 at 1.2 tiles behind (within RETREAT_BACK_R, farther than the target, so the retreat's pin holds on 1): a step
    no press gives way (`retreat_break` {dist 1.2} on the next choose); a press in flight (`swing`, `shove`) holds;
    with `retreat_melee` off (the pin of the rule before it) the melee holds. (At 0.49 the retreat pin's own switch,
    PAIR_SWITCH_R, gives the melee way whatever the rule reads: Plan 33 Task 3 fix 4 (a).)"""
    r, f = melee_at(tmp_path, 1.2, step, rule=rule)
    assert f.busy() is holds
    if not holds:
        f.choose()
        assert f.why["retreat_break"]["dist"] == pytest.approx(1.2)


def test_outside_the_retreat_the_melee_holds(tmp_path):
    """No retreat: the same melee with 2 at 1.2 behind holds (the rule reads the retreat only)."""
    r, f = fight4(tmp_path, [zm(1, ME[0] + 0.84, ME[1]), zm(2, ME[0] - 1.9, ME[1])], retreat=None, target=1,
                  caps=MELEE_CAPS)
    a = f.step()
    accept(r, a, "face")
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, ME[0] + 0.84, ME[1]), zm(2, ME[0] - 1.2, ME[1])])
    f.observe()
    assert a.type == "melee" and f.busy() is True


# ================================================================ CRAWLER_CLEAR (ruling P34-A fix B)
SMOKE_ME = (10791.28, 10629.24)   # the smoke trial's frame 1835


def sz(zid, x, y, crawler=False):
    return dict(zombie(zid, x, y, me=SMOKE_ME), crawler=crawler, onFloor=crawler)


SMOKE = [sz(9174, 10792.1, 10630.0, crawler=True), sz(9175, 10790.0, 10629.1, crawler=True),
         sz(9128, 10790.1, 10630.0), sz(9173, 10789.3, 10629.0)]


def smoke(tmp_path, zs=SMOKE, rule=True, retreat=None):
    r = Rig(tmp_path, caps=MELEE_CAPS)
    r.frame(x=SMOKE_ME[0], y=SMOKE_ME[1], zombies=zs)
    f = F.Fight(r.world, r.acts, r.clock)
    f.stance, f.retreat = True, retreat
    if not rule:
        f.rules = f.rules - {"crawler_clear"}
    return r, f


def test_the_smoke_trial_s_frame_backpedals_away_from_the_crawlers_and_sends_no_melee(tmp_path):
    """The smoke trial's frame 1835: 9174 crawling 1.12 tiles off (within CRAWLER_AVOID_R), 9175 at 1.29, the standing
    9128 at 1.40 and 9173 at 1.99: the rule sends the stance's backpedal facing 9128 on the heading away from the two
    crawlers' centroid (east and north: away from both), no melee, logged `crawler_clear` {fallen [9174, 9175], away,
    n 1}."""
    r, f = smoke(tmp_path)
    cmd = f.choose()
    cx, cy = (10792.1 + 10790.0) / 2, (10630.0 + 10629.1) / 2
    away = unit(SMOKE_ME[0] - cx, SMOKE_ME[1] - cy)
    assert away[0] > 0.0 and away[1] < 0.0
    assert cmd.TYPE == "aim" and cmd.targetId == 9128 and (cmd.vx, cmd.vy) == pytest.approx(away)
    assert f.why["leg"] == "back"
    cc = f.why["crawler_clear"]
    assert cc["fallen"] == [9174, 9175] and cc["n"] == 1 and cc["away"] == pytest.approx(list(away))
    for c in (9174, 9175):
        z = r.world.zombies[c]
        assert math.hypot(z["x"] - SMOKE_ME[0] - cmd.vx, z["y"] - SMOKE_ME[1] - cmd.vy) > math.hypot(
            z["x"] - SMOKE_ME[0], z["y"] - SMOKE_ME[1])


def test_with_crawler_clear_off_the_smoke_frame_sends_the_melee_at_9128(tmp_path):
    """The pin of the rule before it (`crawler_clear` off): the melee at 9128, the pair rule's standing pin."""
    r, f = smoke(tmp_path, rule=False)
    cmd = f.choose()
    assert (cmd.TYPE, cmd.targetId) == ("melee", 9128) and "crawler_clear" not in f.why


def test_a_lone_crawler_within_crawler_r_is_still_stomped_first(tmp_path):
    """One crawler at 0.9 tiles and a standing zombie at 3: CRAWLER_FIRST's finish as before (one crawler is stomped,
    a field of them is left), no `crawler_clear`."""
    zs = [sz(1, SMOKE_ME[0] + 0.9, SMOKE_ME[1], crawler=True), sz(2, SMOKE_ME[0] - 3.0, SMOKE_ME[1])]
    r, f = smoke(tmp_path, zs)
    cmd = f.choose()
    assert cmd.targetId == 1 and cmd.TYPE in ("melee", "stomp") and "crawler_first" in f.why
    assert "crawler_clear" not in f.why


def test_two_fallen_within_crawler_avoid_r_are_left_whatever_the_target(tmp_path):
    """Two crawlers within CRAWLER_AVOID_R (0.9 east, 1.1 north-east) and a standing zombie at 3 west: the backpedal,
    not CRAWLER_FIRST's stomp."""
    zs = [sz(1, SMOKE_ME[0] + 0.9, SMOKE_ME[1], crawler=True), sz(3, SMOKE_ME[0] + 0.8, SMOKE_ME[1] - 0.75,
                                                                   crawler=True),
          sz(2, SMOKE_ME[0] - 3.0, SMOKE_ME[1])]
    r, f = smoke(tmp_path, zs)
    cmd = f.choose()
    assert cmd.TYPE == "aim" and cmd.targetId == 2 and cmd.vx < 0.0 and f.why["crawler_clear"]["n"] == 2


def test_with_no_standing_zombie_within_danger_r_the_rule_is_silent(tmp_path):
    """Crawlers alone (the standing one 7 tiles off): no `crawler_clear`, the Fight's finish as before."""
    zs = [sz(1, SMOKE_ME[0] + 0.9, SMOKE_ME[1], crawler=True), sz(3, SMOKE_ME[0] + 0.8, SMOKE_ME[1] - 0.75,
                                                                   crawler=True),
          sz(2, SMOKE_ME[0] - 7.0, SMOKE_ME[1])]
    r, f = smoke(tmp_path, zs)
    f.choose()
    assert "crawler_clear" not in f.why


@pytest.mark.parametrize("step, holds", [("face", False), ("swing", True)])
def test_a_running_strike_melee_gives_way_to_a_crawler_arriving_unless_a_press_is_in_flight(tmp_path, step, holds):
    """A strike melee at the standing 2 at 1.5 tiles with a crawler at 1.6 (beyond CRAWLER_AVOID_R); a second crawler
    arrives at 1.1: its last step `face` gives way (the backpedal next), `swing` holds."""
    first = [sz(2, SMOKE_ME[0] + 1.5, SMOKE_ME[1]), sz(3, SMOKE_ME[0], SMOKE_ME[1] + 1.6, crawler=True)]
    r, f = smoke(tmp_path, first)
    a = f.step()
    assert (a.type, a.args["targetId"], a.args["mode"]) == ("melee", 2, "strike")
    accept(r, a, step)
    r.frame(x=SMOKE_ME[0], y=SMOKE_ME[1], zombies=first + [sz(4, SMOKE_ME[0] - 1.1, SMOKE_ME[1], crawler=True)])
    f.observe()
    assert f.busy() is holds
    if not holds:
        cmd = f.choose()
        assert cmd.TYPE == "aim" and f.why["crawler_clear"]["n"] == 1 and cmd.vx > 0.0


def test_the_clear_leg_holds_while_a_crawler_lies_within_and_gives_way_once_clear(tmp_path):
    """The backpedal sent holds while a crawler lies within CRAWLER_AVOID_R; with the crawlers beyond it the leg gives
    way (the ladder's turn)."""
    r, f = smoke(tmp_path)
    a = f.step()
    accept(r, a)
    assert "crawler_clear" in f.why and f.busy() is True
    far = [sz(9174, 10793.5, 10630.0, crawler=True), sz(9175, 10789.5, 10629.1, crawler=True),
           sz(9128, 10790.1, 10630.0), sz(9173, 10789.3, 10629.0)]
    r.frame(x=SMOKE_ME[0], y=SMOKE_ME[1], zombies=far)
    f.observe()
    assert f.busy() is False


@pytest.mark.parametrize("retreat, wins", [((1.0, 0.0), True), ((-1.0, 0.0), False)])
def test_under_the_retreat_its_heading_wins_within_90_degrees_of_the_crawler_heading(tmp_path, retreat, wins):
    """Under the retreat: its heading (east) is sent where it lies within 90 degrees of the crawler heading (east and
    north), else (west) the crawler heading."""
    r, f = smoke(tmp_path, retreat=retreat)
    cmd = f.choose()
    cx, cy = (10792.1 + 10790.0) / 2, (10630.0 + 10629.1) / 2
    away = unit(SMOKE_ME[0] - cx, SMOKE_ME[1] - cy)
    assert (cmd.vx, cmd.vy) == pytest.approx(retreat if wins else away)
