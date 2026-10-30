"""Survival 12 (survival iteration 11; Plan 24 Task 32; E9: four bites bled the health from 96.39065551757812 to 0 in
13.111 s under the `many` flee with five rags held): ruling P24-AR, the care tick inside a long flee (the riding
bandage under a `many` flee with a chaser: the nearest beyond RIDE_MANY_R, or after FLEE_CARE_S since the first `many`
with FLEE_CARE_N bleeding parts whatever the distance). The fake mod over PZA/1.5's parts."""
import pytest

from agent.base.planner import care as C

from .test_survive import make, threat_why, tick
from .test_survive_g import care_frame, hold, part
from .test_survive_q import z


# ================================================================ P24-AR: the care tick inside a long flee
def many_leg(tmp_path, parts, x, since=None):
    """A `many` flee from a chaser (the episode's flag set, as `test_survive_g`'s ride tests do), its steer leg sent and
    running; then the frame with `parts` bleeding and the chaser at `x` tiles, ticked. `since`: wall seconds since the
    first `many` read (Survive's `many_since`), None for none."""
    r, sv = make(tmp_path)
    hold(r, 10, "Base.Bandage")
    care_frame(r, parts, zombies=[z(1, 105.5)], health=30.0)
    tick(r, sv)
    r.answer("progress")
    sv.flee_many = True
    sv.many_since = None if since is None else r.clock() - since
    care_frame(r, parts, zombies=[z(1, 100.0 + x)], health=30.0)
    tick(r, sv)
    return r, sv


def rode(r):
    return any(a.type == "bandage" and a.args.get("keepMoving") is True for a in r.acts.history)


def test_the_ride_constants():
    assert (C.RIDE_MANY_R, C.FLEE_CARE_S, C.FLEE_CARE_N) == (3.0, 20.0, 2) and C.RIDE_MANY_R < C.RIDE_R


@pytest.mark.parametrize("x,ride", [(3.5, True), (2.5, False)])
def test_a_many_flee_rides_the_bandage_with_the_chaser_beyond_ride_many_r(tmp_path, x, ride):
    r, sv = many_leg(tmp_path, [part(6, bleeding=True, bleedingTime=5.0)], x)
    assert rode(r) is ride
    if ride:
        assert r.cmd() == ("bandage", {"itemId": 10, "part": 6, "keepMoving": True})


@pytest.mark.parametrize("since,parts,ride", [
    (C.FLEE_CARE_S, [part(6, bleeding=True, bleedingTime=5.0), part(3, bleeding=True, bleedingTime=2.0)], True),
    (C.FLEE_CARE_S - 1.0, [part(6, bleeding=True, bleedingTime=5.0), part(3, bleeding=True, bleedingTime=2.0)], False),
    (C.FLEE_CARE_S, [part(6, bleeding=True, bleedingTime=5.0)], False),
    (None, [part(6, bleeding=True, bleedingTime=5.0), part(3, bleeding=True, bleedingTime=2.0)], False),
])
def test_after_flee_care_s_two_bleeding_parts_ride_whatever_the_distance(tmp_path, since, parts, ride):
    """E9's line 450 (game minute 623: parts 0 and 8 bleeding, the nearest at 0.63 tiles): FLEE_CARE_S since the first
    `many` with two parts bleeding rides at 1.0 tiles; a second short of it, one part, or no `many` read, does not."""
    r, sv = many_leg(tmp_path, parts, 1.0, since=since)
    assert rode(r) is ride


def test_the_many_clock_starts_at_the_first_many_and_ends_with_the_threat(tmp_path):
    from .test_survive import group
    r, sv = make(tmp_path)
    r.frame(x=100.0, y=201.5, zombies=group())
    tick(r, sv)
    assert threat_why(tmp_path)["flee"] == "many" and sv.many_since == r.clock()
    r.answer()
    r.advance(5.0)
    r.frame(x=100.0, y=201.5, zombies=group())
    tick(r, sv)
    assert sv.many_since == r.clock() - 5.0
    r.frame(x=100.0, y=201.5, zombies=group(-20.0))                    # every one beyond DISENGAGE_R: nothing held
    tick(r, sv)
    assert sv.many_since is None and sv.mode is None
