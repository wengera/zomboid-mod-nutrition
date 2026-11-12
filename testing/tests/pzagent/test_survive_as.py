"""Plan 36 Task 3 (the engagement picker; the spec `docs/superpowers/specs/2026-11-11-plan-36-the-engagement-design.md`
§ 3.3): where the fight happens, decided before contact, by the withdraw vector the Fight's running melee carries
(`group.ThreatGroup._pull`, `Fight.withdraw`):

- the spread: two or more standing zombies closing within GROUP_ENTRY_R whose bearings spread more than
  PULL_SPREAD_DEG send the melee with the withdraw into the widest gap of their bearings (along the bisector, away
  from their centroid), until the spread falls under PULL_STOP_DEG or the nearest stands within the reach; then the
  melee is re-sent without it;
- the cone: a standing zombie closing within CONE_TRIGGER_R more than CONE_OFF_DEG off the pinned target's bearing
  sends the vector away from the bisector of the two bearings, until it stands inside the cone (CONE_HALF_DEG);
- the leave at GROUP_LEAVE_N is the pull: F21's shape (`f_goals_21-20261111-150552`, decision lines 364 to 412: three
  and four standing with the meet spent, `engage_hold` {rule "leave"} on the leave's run) sends the melee with the
  withdraw, no hold;
- logged `engage_pull` {why, spread, n, heading[, flank]} on the threat why.

Named change, Plan 37 Task 3 (unit tests of an earlier rule whose fixtures the disposition selector reaches, pinned
with its switch off): DISPOSITION off in `survive` and `kitchen_survive`, the picker as Plan 36 sent it (`hunt` sends
no withdraw, `hold` the pull read always; `test_disposition.py`). Plan 37 Task 3 deleted the leave's `run` above
RETREAT_MAX_N, SPENT_LEAVE's run read over by the engaged melee and fix 1b's retreat hysteresis with their tests (named
in the task report); the ring read's 45 degrees is `policies.room_open_heading`'s default (the clock's).

Every fixture is synthetic (the shapes of F21 and the spec's § 3.3, never a replay), the fake mod announcing
PZA/1.13 with the `melee` cap."""
import inspect
import math

import pytest

from agent.base.planner import group as G
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .test_survive import threat_why, tick
from .test_survive_an import accept
from .test_survive_ar import GROUP, heading, rig, work_of
from .test_survive_q import z

ME = (100.0, 200.0)   # the frame's default position


def zp(zid, deg, d):
    """A standing zombie `d` tiles from ME at bearing `deg` (0 east, 90 the world's +y)."""
    return z(zid, ME[0] + d * math.cos(math.radians(deg)), ME[1] + d * math.sin(math.radians(deg)))


def survive(tmp_path, first, leave=False, disposition=False):
    """A Survive (GROUP_LEAVE `leave`, DISPOSITION `disposition`) on a `rig` announcing PZA/1.13 with `melee`: its first
    line fights `first` (one standing zombie within KEEP_R) with the melee, accepted, its last step `face`. Plan 37
    Task 3 fix 1: the spread's and the cone's cases read the live path (the selector's `hunt` sends the picker's
    spread and cone pulls as Plan 36 did); the rest pin Plan 36's picker with the switch off."""
    r = rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.GROUP_LEAVE = leave
    sv.DISPOSITION = disposition
    r.frame(zombies=[first])
    tick(r, sv)
    a = r.acts.history[-1]
    assert a.type == "melee" and sv.mode == "fight"
    accept(r, a, "face")
    return r, sv, a


def line(tmp_path, r, sv, zs, **frame):
    """One more decision line half a second on, over `zs`: (its threat why, the last action sent)."""
    r.advance(0.5)
    r.frame(zombies=zs, **frame)
    tick(r, sv)
    return threat_why(tmp_path), r.acts.history[-1]


def withdraw(a):
    return (a.args["withdrawX"], a.args["withdrawY"])


def three(d1, d):
    """The pinned 1 at `d1` tiles east (bearing 0), 2 and 3 at `d` tiles at bearings -70 and +70."""
    return [zp(1, 0.0, d1), zp(2, -70.0, d), zp(3, 70.0, d)]


# ================================================================ the constants and the geometry
def test_the_constants():
    """The spec's § 3.3 values, and no Plan 35 leave hold left in the threat branch's source."""
    assert (P.PULL_SPREAD_DEG, P.PULL_STOP_DEG, P.CONE_HALF_DEG, P.CONE_OFF_DEG, P.CONE_TRIGGER_R) == (
        60.0, 45.0, 60.0, 90.0, 4.0)
    assert '_engage_holds("leave"' not in inspect.getsource(T)


@pytest.mark.parametrize("bearings, spread, gap", [
    ((-70.0, 0.0, 70.0), 140.0, 180.0),   # the bisector 0, away from the centroid: west
    ((0.0, 90.0), 90.0, 225.0),
    ((0.0, 90.0, 180.0, 270.0), 270.0, 45.0),   # four round the player: the first widest gap
    ((10.0, 10.0), 0.0, 190.0),
    ((350.0, 20.0), 30.0, 185.0),   # across the 0 line
])
def test_spread_gap(bearings, spread, gap):
    s, g = G.spread_gap(bearings)
    assert s == pytest.approx(spread) and g == pytest.approx(gap)


# ================================================================ the spread
def spread_rig(tmp_path):
    """The engaged melee at 1 (2.3 tiles east); then 1 closes to 2.1 and to 1.9 (beyond the reach, 1.2 + ATTACK_MARGIN)
    while 2 and 3 come in at bearings -70 and +70 from 5.5 to 5.0 tiles: the third line reads all three closing. On the
    live path (fix 1): the three lines inside DISPOSITION_DWELL_S read `hunt`, its pull the spread's."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.3), disposition=True)
    line(tmp_path, r, sv, three(2.1, 5.5))
    why, b = line(tmp_path, r, sv, three(1.9, 5.0))
    return r, sv, a, why, b


def test_three_closing_at_a_wide_spread_send_the_melee_with_the_withdraw_along_the_bisector(tmp_path):
    """Three standing closing at bearings -70, 0 and +70 (the spread 140 degrees, above PULL_SPREAD_DEG), the nearest
    beyond the reach: the engaged melee is re-sent with the withdraw due west (the bisector 0 turned about, away from
    their centroid), the melee alone (never a flee leg, a steer or a walk), logged `engage_pull` {why "spread",
    spread 140, n 3, heading 180} and the melee why's `withdraw`."""
    r, sv, a, why, b = spread_rig(tmp_path)
    assert b is not a and b.type == "melee" and b.args["targetId"] == 1
    assert withdraw(b) == pytest.approx((-1.0, 0.0), abs=1e-9)
    assert why["melee"]["withdraw"] == pytest.approx([-1.0, 0.0], abs=1e-9) and why.get("fight") is True
    pull = why["engage_pull"]
    assert (pull["why"], pull["n"]) == ("spread", 3)
    assert pull["spread"] == pytest.approx(140.0) and pull["heading"] == pytest.approx(180.0)
    assert sv.pull == pytest.approx((-1.0, 0.0), abs=1e-9)


def test_the_running_pull_holds_down_to_pull_stop_deg(tmp_path):
    """The pull running, 2 and 3 come in to bearings -25 and +25 (the spread 50: under PULL_SPREAD_DEG, not under
    PULL_STOP_DEG) without closing: the pull holds (every standing zombie counts once it runs), no re-send (the same
    withdraw sector)."""
    r, sv, a, why, b = spread_rig(tmp_path)
    accept(r, b, "face")
    why, c = line(tmp_path, r, sv, [zp(1, 0.0, 1.9), zp(2, -25.0, 5.0), zp(3, 25.0, 5.0)])
    assert why["engage_pull"]["spread"] == pytest.approx(50.0) and c is b


def test_the_spread_under_pull_stop_deg_drops_the_vector(tmp_path):
    """The pull running, 2 and 3 at bearings -20 and +20 (the spread 40, under PULL_STOP_DEG): no `engage_pull`, the
    melee re-sent without the withdraw (the reflex stands)."""
    r, sv, a, why, b = spread_rig(tmp_path)
    accept(r, b, "face")
    why, c = line(tmp_path, r, sv, [zp(1, 0.0, 1.9), zp(2, -20.0, 4.5), zp(3, 20.0, 4.5)])
    assert "engage_pull" not in why and sv.pull is None
    assert c is not b and c.type == "melee" and "withdrawX" not in c.args and "withdraw" not in why["melee"]


def test_the_nearest_within_the_reach_drops_the_vector(tmp_path):
    """The pull running, 1 closes to 1.4 tiles (within the reach, 1.55) while 2 and 3 hold at 5.0 (one closing, so no
    fighting retreat, fix 1): the vector is dropped, the melee re-sent without it (the reflex presses)."""
    r, sv, a, why, b = spread_rig(tmp_path)
    accept(r, b, "face")
    why, c = line(tmp_path, r, sv, three(1.4, 5.0))
    assert "engage_pull" not in why and c.type == "melee" and "withdrawX" not in c.args


def test_one_closing_at_five_tiles_sends_no_pull(tmp_path):
    """The engaged melee at 1 (2.3 tiles east, not closing); one more standing zombie closes from 5.5 to 5.0 tiles at
    bearing 70 (one closing: no spread; beyond CONE_TRIGGER_R: no cone): no `engage_pull`, no re-send."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.3))
    line(tmp_path, r, sv, [zp(1, 0.0, 2.3), zp(2, 70.0, 5.5)])
    why, b = line(tmp_path, r, sv, [zp(1, 0.0, 2.3), zp(2, 70.0, 5.0)])
    assert "engage_pull" not in why and b is a and sv.pull is None


def test_two_standing_at_a_wide_spread_but_not_closing_send_no_pull(tmp_path):
    """Two standing at bearings 0 and 120 neither closing (the second steady at 5.0): no pull starts (the start reads
    the closing ones)."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.3))
    line(tmp_path, r, sv, [zp(1, 0.0, 2.3), zp(2, 120.0, 5.0)])
    why, b = line(tmp_path, r, sv, [zp(1, 0.0, 2.3), zp(2, 120.0, 5.0)])
    assert "engage_pull" not in why and b is a


# ================================================================ the cone
def cone_rig(tmp_path):
    """The engaged melee at 1 (2.0 tiles east, steady); 2 closes from 3.8 to 3.3 tiles at bearing 120 (120 degrees off
    the pin, more than CONE_OFF_DEG; within CONE_TRIGGER_R). On the live path (fix 1): `hunt`, its pull the cone's."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.0), disposition=True)
    line(tmp_path, r, sv, [zp(1, 0.0, 2.0), zp(2, 120.0, 3.8)])
    why, b = line(tmp_path, r, sv, [zp(1, 0.0, 2.0), zp(2, 120.0, 3.3)])
    return r, sv, a, why, b


def test_a_flanker_off_the_cone_sends_the_vector_that_brings_it_into_the_cone(tmp_path):
    """A standing zombie 120 degrees off the pinned target inside 4 tiles and closing: the engaged melee is re-sent
    with the withdraw at 240 degrees (away from the bisector of the pin's 0 and the flanker's 120), logged
    `engage_pull` {why "cone", spread 120, n 2, flank 2, heading 240}."""
    r, sv, a, why, b = cone_rig(tmp_path)
    assert b is not a and b.type == "melee" and b.args["targetId"] == 1
    assert withdraw(b) == pytest.approx(heading(240))
    pull = why["engage_pull"]
    assert (pull["why"], pull["n"], pull["flank"]) == ("cone", 2, 2)
    assert pull["spread"] == pytest.approx(120.0) and pull["heading"] == pytest.approx(240.0)


def test_the_cone_s_pull_holds_until_the_flanker_is_inside_the_cone(tmp_path):
    """The cone's pull running: the flanker at bearing 70 (70 off the pin, outside CONE_HALF_DEG), not closing, holds
    it; at bearing 50 (inside the cone) the vector is dropped and the melee re-sent without it."""
    r, sv, a, why, b = cone_rig(tmp_path)
    accept(r, b, "face")
    why, c = line(tmp_path, r, sv, [zp(1, 0.0, 2.0), zp(2, 70.0, 3.4)])
    assert why["engage_pull"]["why"] == "cone" and why["engage_pull"]["spread"] == pytest.approx(70.0)
    why, d = line(tmp_path, r, sv, [zp(1, 0.0, 2.0), zp(2, 50.0, 3.4)])
    assert "engage_pull" not in why and d.type == "melee" and "withdrawX" not in d.args


def test_a_flanker_beyond_cone_trigger_r_or_inside_the_cone_sends_none(tmp_path):
    """A standing zombie closing at bearing 80 (80 off the pin, not more than CONE_OFF_DEG) from 3.8 to 3.3 tiles: no
    cone (and one closing: no spread)."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.0))
    line(tmp_path, r, sv, [zp(1, 0.0, 2.0), zp(2, 80.0, 3.8)])
    why, b = line(tmp_path, r, sv, [zp(1, 0.0, 2.0), zp(2, 80.0, 3.3)])
    assert "engage_pull" not in why and b is a


# ================================================================ the leave is the pull (F21's shape)
def test_the_leave_s_retreat_is_the_pull_when_the_trio_stands_in_a_line(tmp_path):
    """GROUP_LEAVE on, three standing within GROUP_ENTRY_R at bearings -10, 0 and +10 (a line already, the spread 20):
    the leave's retreat holds (the Fight), and its melee carries no withdraw (the reflex stands)."""
    r, sv, a = survive(tmp_path, z(1, 101.8), leave=True)
    why, b = line(tmp_path, r, sv, [zp(1, 0.0, 1.8), zp(2, -10.0, 2.2), zp(3, 10.0, 2.4)])
    assert why["group_leave"]["leg"] == "retreat" and "engage_pull" not in why
    assert r.acts.history[-1].type == "melee" and "withdrawX" not in r.acts.history[-1].args


# ================================================================ the ring's open heading (`room_open_heading`)
def ring(h):
    """A room ring as `World.room` returns it (Plan 36 Task 1): the eight headings' clear tiles `h`, each stop a wall."""
    return {"h": list(h), "stop": ["wall"] * 8, "tick": 1}


@pytest.mark.parametrize("h, run, out", [
    ((0.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0), (1.0, 0.0), 45.0),    # open at 45, walled at 0: a +x run turns to 45
    ((0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0), (1.0, 0.0), 45.0),    # a tie at 45 and 315 (both 45 off): the first
    ((1.0, 2.5, 2.5, 0.0, 0.0, 0.0, 0.0, 0.0), heading(80), 90.0),   # a tie at 45 and 90: the nearer the run's 80
    ((0.0, 0.0, 0.0, 3.0, 3.0, 3.0, 0.0, 0.0), (1.0, 0.0), None),    # every candidate (315, 0, 45) walled: kept
    ((3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), (1.0, 0.0), 0.0),     # the run's own heading the most open
])
def test_room_open_takes_the_most_open_ring_heading_within_45_degrees(h, run, out):
    """Fix 2 (`policies.room_open_heading` on `World.room`, the ring Task 1 landed, at its default arc: the clock's
    gain-distance read since Plan 37 Task 3 widened the break steer's): of the ring headings within ROOM_OPEN_DEG of the
    run's, the largest clear tiles, a tie to the nearest the run's heading (then the first); every candidate at 0.0
    keeps the run's heading."""
    from types import SimpleNamespace
    v, deg = P.room_open_heading(SimpleNamespace(room=lambda: ring(h)), run)
    if out is None:
        assert (v, deg) == (run, None)
    else:
        assert deg == pytest.approx(out) and v == pytest.approx(heading(out), abs=1e-12)


def test_room_open_with_no_ring_keeps_the_heading():
    """No ring on the frame (`World.room` None): the run's heading kept."""
    from types import SimpleNamespace
    assert P.room_open_heading(SimpleNamespace(room=lambda: None), (0.6, 0.8)) == ((0.6, 0.8), None)


def test_work_of_a_pulled_melee_keeps_the_five_work_fields(tmp_path):
    """The pulled melee's work: the five fields as every melee's, the withdraw beside them."""
    r, sv, a, why, b = spread_rig(tmp_path)
    w = work_of(b)
    assert {k: w[k] for k in ("workR", "crawlerR", "bandLo", "floorHealth", "pile")} == {
        "workR": 3.5, "crawlerR": 1.2, "bandLo": 0.4, "floorHealth": 40.0, "pile": True}


# ================================================================ fix 1: the fighting retreat at three closing
def column(d1, d2, d3):
    """A column east of ME: 1 at `d1` tiles (bearing 0), 2 at `d2` (bearing 5) and 3 at `d3` (bearing -5)."""
    return [zp(1, 0.0, d1), zp(2, 5.0, d2), zp(3, -5.0, d3)]


def test_three_closing_in_a_column_send_the_withdraw_away_from_their_centroid(tmp_path):
    """Fix 1 (the controller's ruling, Angus's fighting retreat): three standing closing in a column (the spread 10
    degrees, under PULL_STOP_DEG), the far two at 5 tiles: the engaged melee is re-sent with the withdraw away from
    their centroid (due west), logged `engage_pull` {why "retreat", n 3}."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.3))
    line(tmp_path, r, sv, column(2.1, 5.5, 5.5))
    why, b = line(tmp_path, r, sv, column(1.9, 5.0, 5.0))
    assert b is not a and b.type == "melee" and b.args["targetId"] == 1
    assert withdraw(b) == pytest.approx((-1.0, 0.0), abs=1e-9)
    pull = why["engage_pull"]
    assert (pull["why"], pull["n"]) == ("retreat", 3) and pull["spread"] == pytest.approx(10.0)
    assert pull["heading"] == pytest.approx(180.0)


def test_two_closing_in_a_column_send_none(tmp_path):
    """Two standing closing in a column (the spread 5 degrees): under GROUP_LEAVE_N closing, no withdraw."""
    r, sv, a = survive(tmp_path, zp(1, 0.0, 2.3))
    line(tmp_path, r, sv, column(2.1, 5.5, 5.5)[:2])
    why, b = line(tmp_path, r, sv, column(1.9, 5.0, 5.0)[:2])
    assert "engage_pull" not in why and b is a


# ================================================================ fix 3: the corner Fight's pull along the ring
def kitchen_survive(tmp_path, h):
    """`survive` on room squares (a kitchen round ME), GROUP_LEAVE off, the World's `room` read a ring of `h` (None:
    no ring); the engaged melee at 1 (1.8 tiles east); then three standing close in from the east on two lines (1 to
    0.9, 2 and 3 to 1.6 at bearings +-20): the corner's lines (`engage_hold` {rule "cornered"} or the Fight on a room
    square), the fighting retreat's three closing. Returns (the last threat why, the last action)."""
    from .test_policies import grid
    r = rig(tmp_path)
    r.scan(grid(96, 104, 196, 204, at={(x, y): {"room": "kitchen", "building": 1}
                                       for x in range(96, 105) for y in range(196, 205)}))
    if h is not None:
        r.world.room = lambda: ring(h)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.GROUP_LEAVE = False
    sv.DISPOSITION = False   # Plan 37 Task 3: the picker as Plan 36 sent it
    r.frame(zombies=[z(1, 101.8)])
    tick(r, sv)
    a = r.acts.history[-1]
    assert a.type == "melee"
    accept(r, a, "face")
    line(tmp_path, r, sv, [zp(1, 0.0, 1.2), zp(2, 20.0, 2.0), zp(3, -20.0, 2.0)])
    return line(tmp_path, r, sv, [zp(1, 0.0, 0.9), zp(2, 20.0, 1.6), zp(3, -20.0, 1.6)])


def test_the_corner_fight_s_pull_is_clamped_to_the_ring_s_open_heading(tmp_path):
    """Fix 3: on room squares three standing close in from the east (the retreat's vector due west, 180): the ring
    reads only north (90) open within 90 degrees of it: the melee is sent with the withdraw clamped north, logged
    `engage_pull` {why "retreat", heading 90, room {from 180}}."""
    why, b = kitchen_survive(tmp_path, (0.0, 0.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    pull = why["engage_pull"]
    assert pull["why"] == "retreat" and pull["heading"] == pytest.approx(90.0)
    assert pull["room"]["from"] == pytest.approx(180.0, abs=1e-6)
    assert b.type == "melee" and withdraw(b) == pytest.approx((0.0, 1.0), abs=1e-9)


def test_the_corner_fight_s_pull_with_no_open_heading_sends_no_withdraw(tmp_path):
    """Fix 3: the same, the ring open only east (0, 180 degrees off the vector): no heading within 90 degrees is open:
    the vector is dropped (the reflex stands), logged `engage_pull` {why "retreat", room "closed"}."""
    why, b = kitchen_survive(tmp_path, (3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    assert why["engage_pull"]["why"] == "retreat" and why["engage_pull"]["room"] == "closed"
    assert sv_pull_none(b)


def sv_pull_none(b):
    return b.type == "melee" and "withdrawX" not in b.args


def test_the_corner_fight_with_no_ring_sends_no_pull(tmp_path):
    """Fix 3: an old frame (no ring) on room squares: the corner Fight as before, no `engage_pull`, no withdraw."""
    why, b = kitchen_survive(tmp_path, None)
    assert "engage_pull" not in why and sv_pull_none(b)


def test_the_door_fight_and_the_sheltered_fight_take_no_pull(tmp_path):
    """Fix 3 (`Threat._pull_ok`, read at the method: the door fight and the doorway's chokepoint keep their
    exclusion): a door fight's line (`door` set) and a sheltered one read no pull, ring or none; the corner and the
    room square's Fight only with a ring; the open-ground Fight always."""
    from types import SimpleNamespace
    for room, inside in ((None, False), (ring([3.0] * 8), False), (ring([3.0] * 8), True), (None, True)):
        sv = SimpleNamespace(world=SimpleNamespace(room=lambda room=room: room), sheltered=False,
                             night=SimpleNamespace(inside=lambda inside=inside: inside))
        ok = lambda kind, door=None: T.Threat._pull_ok(sv, kind, door)
        assert ok("door", [(1, None)]) is False and ok("fight", [(1, None)]) is False
        assert ok("cornered") is (room is not None)
        assert ok("fight") is ((not inside) or room is not None)
        sv.sheltered = True
        assert ok("fight") is False and ok("cornered") is False
