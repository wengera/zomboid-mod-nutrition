"""Plan 34 Task 5 (spec section 3.5): the decision line's `frame_age`, the line's `wall` less the frame's
`World.frame_wall_ms` in seconds, rounded to 3 places, written only when `frame_wall_ms` is a number and the age exceeds
`policies.FRAME_STALE_S` (F19's melee at the first wound was sent off a frame 0.970 s old, the session's median lag
0.057 s: `testing/artifacts/f_goals_19-20261109-060929/GUIDE.md` section 2), so a line off a fresh frame keeps its
bytes and every decision golden with it. No rule reads it."""
from agent.base.planner import policies as P

from .test_survive import last, make, tick


def _line_at_age(tmp_path, age_s=None, wall_ms=False):
    """One tick on a quiet frame, the clock `age_s` seconds past the frame's wall (or `frame_wall_ms` set to `wall_ms`
    when given), the line written."""
    r, sv = make(tmp_path)
    r.frame()
    if wall_ms is not False:
        r.world.frame_wall_ms = wall_ms
    else:
        r.world.frame_wall_ms = r.t["now"] * 1000.0
        r.t["now"] += age_s
    tick(r, sv)
    return last(tmp_path)


def test_the_constant_is_half_a_second():
    assert P.FRAME_STALE_S == 0.5


def test_a_line_off_a_frame_0_9_s_old_carries_its_age(tmp_path):
    ln = _line_at_age(tmp_path, 0.9)
    assert ln["frame_age"] == 0.9


def test_the_age_is_rounded_to_three_places(tmp_path):
    ln = _line_at_age(tmp_path, 0.97012345)
    assert ln["frame_age"] == 0.97


def test_a_line_off_a_fresh_frame_carries_no_key(tmp_path):
    assert "frame_age" not in _line_at_age(tmp_path, 0.1)


def test_a_line_at_the_bound_carries_no_key(tmp_path):
    assert "frame_age" not in _line_at_age(tmp_path, 0.5)


def test_a_line_with_no_frame_wall_carries_no_key(tmp_path):
    assert "frame_age" not in _line_at_age(tmp_path, wall_ms=None)
