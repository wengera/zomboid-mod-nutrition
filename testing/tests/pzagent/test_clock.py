"""Plan 36 Task 4 (the action clock, `planner/clock.py`; the spec `2026-11-11-plan-36-the-engagement-design.md` § 3.4):
the clock's own reads on synthetic frames: the speed rule per state, the floor against the zombie's recent speed, the
time to contact, `allows` at the margin's edge, the action kinds and the durations table."""
import math

import pytest

from agent.base import pza1
from agent.base.planner import clock as CK
from agent.base.planner import policies as P
from agent.base.world import World

ME = (100.0, 200.0)


def zr(zid, x, y=ME[1], state="walktoward", target=True, floor=None, crawler=False):
    """A frame's zombie record (PZA/1.9's fields the clock reads)."""
    return {"id": zid, "x": x, "y": y, "dist": abs(x - ME[0]), "hasTarget": target, "crawler": crawler,
            "health": 1.0, "onFloor": floor, "known": None, "state": state, "behind": None}


def world_at(zombies, wall_ms=1_000_000, me=ME):
    w = World()
    feed(w, zombies, wall_ms, me)
    return w


def feed(w, zombies, wall_ms, me=ME):
    w.apply({"kind": "frame", "seq": 1, "wallMs": wall_ms, "gameMin": 480, "me": {"x": me[0], "y": me[1], "z": 0},
             "zombies": list(zombies)})


# ================================================================ the constants
def test_the_speeds_the_margin_and_the_durations():
    """The controller's ruling of 2026-11-11 17:13:44 (the speeds, floors) and the durations read off F20's and F21's
    act lines (the report's table)."""
    assert (P.LUNGE_TPS, P.WALK_TPS, P.CRAWL_TPS, P.FLOOR_TPS) == (1.6, 1.45, 0.7, 0.3)
    assert (P.ACTION_MARGIN_S, P.CLOCK_SPEED_S, P.CLOCK_SPEED_MIN_S, P.CONTACT_R) == (1.5, 2.0, 0.3, 0.7)
    assert P.ACTION_S == {"rip": 4.134, "unwear": 1.078, "bandage": 5.444, "loot": 1.679, "door": 0.112,
                          "scan": 0.031}
    assert set(CK.TIMED) == set(P.ACTION_S)
    assert (P.CLOCK_LEG_S, P.CLOCK_EPISODE_S) == (3.0, 12.0)


# ================================================================ the speed rule
@pytest.mark.parametrize("rec, floor", [
    (dict(state="lunge"), 1.6), (dict(state="lunge-network"), 1.6), (dict(state="attack"), 1.6),
    (dict(state="attack-network", target=False), 1.6),
    (dict(state="walktoward"), 1.45), (dict(state="pathfind", target=False), 1.45),
    (dict(state="staggerback", target=False), 1.45), (dict(state="turnalerted", target=False), 1.45),
    (dict(state="idle", target=True), 1.45), (dict(state=None, target=True), 1.45),
    (dict(state="idle", target=False), 0.0), (dict(state=None, target=False), 0.0),
    (dict(state="crawler", floor=True, crawler=True), 0.7), (dict(state="lunge", floor=True, crawler=True), 0.7),
    (dict(state="onground", floor=True), 0.3), (dict(state="lunge", floor=True), 0.3),
])
def test_the_floor_per_state(rec, floor):
    """LUNGE_TPS lunging or attacking; WALK_TPS walking, pathing, staggering, turning, or chasing in any other state;
    an idle zombie with no target none; a crawler CRAWL_TPS and a fallen one FLOOR_TPS whatever its state."""
    assert CK.speed_floor(zr(1, ME[0] + 3, **rec)) == floor


def test_the_recent_speed_wins_over_a_lower_floor_and_the_floor_over_a_slower_track():
    """A walking zombie tracked at 2.0 tiles a second over 1 s reads 2.0 (over WALK_TPS); a lunging one tracked at
    0.5 reads LUNGE_TPS; an idle one tracked at 0.8 reads 0.8 (its own speed alone)."""
    ck, w = CK.ActionClock(), World()
    feed(w, [zr(1, 110.0), zr(2, 110.0, y=210.0, state="lunge"), zr(3, 110.0, y=190.0, state="idle", target=False)],
         1_000_000)
    ck.observe(w)
    feed(w, [zr(1, 108.0), zr(2, 109.5, y=210.0, state="lunge"), zr(3, 109.2, y=190.0, state="idle", target=False)],
         1_001_000)
    ck.observe(w)
    z = w.zombies
    assert ck.speed(1, z[1]) == pytest.approx(2.0)
    assert ck.speed(2, z[2]) == 1.6
    assert ck.speed(3, z[3]) == pytest.approx(0.8)


def test_a_track_under_the_minimum_span_reads_the_floor_alone_and_ages_to_two_seconds():
    """Two frames 0.2 s apart read no own speed (CLOCK_SPEED_MIN_S); a track keeps CLOCK_SPEED_S of frames, an
    unlisted zombie's dropped."""
    ck, w = CK.ActionClock(), World()
    feed(w, [zr(1, 110.0)], 1_000_000)
    ck.observe(w)
    feed(w, [zr(1, 109.0)], 1_000_200)
    ck.observe(w)
    assert ck.speed(1, w.zombies[1]) == 1.45
    for i, t in enumerate(range(1_000_500, 1_004_000, 500)):
        feed(w, [zr(1, 108.0 - 0.1 * i)], t)
        ck.observe(w)
    tr = ck.tracks[1]
    assert tr[-1][0] - tr[0][0] <= P.CLOCK_SPEED_S
    w.zombies.clear()
    ck.observe(w)
    assert ck.tracks == {} and ck.ttc is None and ck.nearest is None


# ================================================================ the time to contact
def test_the_time_to_contact_is_the_gap_past_contact_over_the_speed():
    """At 3.7 tiles walking: (3.7 - 0.7) / 1.45; at 0.5 (inside CONTACT_R): 0; an idle zombie standing: never (inf);
    one read dead left out; the smallest the nearest's."""
    w = world_at([zr(1, ME[0] + 3.7), zr(2, ME[0] - 0.5, state="lunge"), zr(3, ME[0] + 2.0, state="idle", target=False),
                  zr(4, ME[0], y=ME[1] + 1.0, state="lunge")])
    per, least = CK.time_to_contact(w, skip={4})
    assert per[1] == pytest.approx(3.0 / 1.45) and per[2] == 0.0 and math.isinf(per[3]) and 4 not in per
    assert least == 0.0
    per, least = CK.time_to_contact(world_at([zr(1, ME[0] + 3.7)]))
    assert least == pytest.approx(3.0 / 1.45)
    assert CK.time_to_contact(world_at([])) == ({}, None)


def test_a_lunger_at_one_tile_reads_under_the_margin():
    """F21's shape: the nearest standing at 1.0 tile lunging: (1.0 - 0.7) / 1.6 = 0.1875 s, under ACTION_MARGIN_S."""
    ck = CK.ActionClock()
    ck.observe(world_at([zr(1, ME[0] + 1.0, state="lunge")]))
    assert ck.ttc == pytest.approx(0.3 / 1.6) and ck.under_margin() and ck.nearest == 1
    assert not any(ck.allows(k) for k in CK.TIMED)


# ================================================================ allows at the margin's edge
@pytest.mark.parametrize("kind", ["rip", "unwear", "bandage", "loot", "door", "scan"])
def test_allows_only_past_the_duration_plus_the_margin(kind):
    """`allows` reads the smallest time to contact strictly above the kind's duration plus 1.5 s: at the edge no, a
    hundredth past it yes; nobody listed, yes; a duration given in place of the table's read so too."""
    need = P.ACTION_S[kind] + P.ACTION_MARGIN_S
    assert CK.ActionClock.need(kind) == pytest.approx(need)
    ck = CK.ActionClock()
    for ttc, ok in ((need, False), (need + 0.01, True), (need - 0.01, False)):
        ck.ttc = ttc
        assert ck.allows(kind) is ok, (ttc, ok)
    for gap, ok in ((need + 0.05, True), (need - 0.05, False)):
        ck.observe(world_at([zr(1, ME[0] + P.CONTACT_R + gap * P.WALK_TPS)]))
        assert ck.allows(kind) is ok, (gap, ok)
    ck.observe(world_at([]))
    assert ck.allows(kind) and not ck.under_margin()
    ck.observe(world_at([zr(1, ME[0] + P.CONTACT_R + 3.0 * P.WALK_TPS)]))
    assert ck.allows(kind, duration_s=1.0) and not ck.allows(kind, duration_s=2.0)


# ================================================================ the action kinds
def test_the_action_kinds():
    """rip, unwear, a standing bandage, the loot and the door's open and close interacts, the scan are the clock's;
    a riding bandage (keepMoving), a steer, a walk, a melee and a stop are not."""
    kinds = [CK.cmd_kind(c) for c in (pza1.Rip(1), pza1.Unwear(1), pza1.Bandage(1, part=3),
                                      pza1.Bandage(1, part=3, keepMoving=True), pza1.Interact(1, 2, "loot"),
                                      pza1.Interact(1, 2, "open"), pza1.Interact(1, 2, "close"), pza1.Scan(10),
                                      pza1.Steer(1.0, 0.0, 3.0, "run"), pza1.WalkTo(1.0, 2.0, "walk"), pza1.Stop())]
    assert kinds == ["rip", "unwear", "bandage", None, "loot", "door", "door", "scan", None, None, None]
    assert CK.action_kind("bandage", {"keepMoving": True}) is None and CK.action_kind("interact", {"kind": "x"}) is None
