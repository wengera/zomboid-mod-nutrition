"""Survival 18 (survival iteration 16; Plan 25 Task 14; E14, `e_day_14-20261030-235607`, rows #4472-#4481). The fake
mod over PZA/1.7.1, on `test_survive`'s shelter world (building 1's 3 x 3 kitchen at x 112, its west door at
(112, 201), the stand's post on the threshold square (112, 201)).

- P25-U, the stand leaves at two attackers: the stand's `drag` end fires at DRAG_DOWN_N - 1 attackers (E14 read three
  0.101 s before `EndDeath`, two 3.001 s before), logged `doorway_left` "drag" and `doorway_drag` (the count).
"""
from agent.base.planner import doorway as D
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .test_survive import group, tick
from .test_survive_p import POST, stood
from .test_survive_p import why as door_why
from .test_survive_p import z as dz


def test_the_iteration_16_switches():
    assert S.T6_SWITCHES == ("STAND_DRAG_EARLY",)
    assert all(getattr(T.Threat, name) is True for name in S.T6_SWITCHES)


# ================================================================ P25-U: the stand leaves at two attackers
def _attacked(tmp_path, attackers, early=True):
    """The stand on its post, one zombie in the doorway on the approach square (1.2 tiles), the rest of the group 7 to
    8 tiles off outside, the frame reading `attackers`; one tick."""
    r, sv = stood(tmp_path)
    sv.STAND_DRAG_EARLY = early
    r.frame(x=POST[0], y=POST[1], zombies=[dz(1, 111.3, 201.5)] + group(8.0, POST)[1:], attackers=attackers)
    a = tick(r, sv)
    return r, sv, a


def test_two_attackers_end_the_stand_drag_with_the_count_logged_and_the_decision_a_flee(tmp_path):
    """E14: two attackers read 3.001 s before the third: the stand ends `drag` on that tick, `doorway_drag` 2, the
    Doorway gone and the tick's decision the stand's flee (`flee` "doorway")."""
    r, sv, _ = _attacked(tmp_path, 2)
    w = door_why(r)
    assert w["doorway_left"] == "drag" and w["doorway_drag"] == 2 and w["flee"] == "doorway"
    assert sv.mode == "flee" and not isinstance(sv.fight, D.Doorway) and "doorway" not in w


def test_one_attacker_keeps_the_stand(tmp_path):
    r, sv, a = _attacked(tmp_path, 1)
    w = door_why(r)
    assert a.type == "attack" and w["doorway"] == 1 and "doorway_left" not in w and "doorway_drag" not in w


def test_three_attackers_end_it_drag_as_before(tmp_path):
    r, sv, _ = _attacked(tmp_path, S.DRAG_DOWN_N)
    w = door_why(r)
    assert w["doorway_left"] == "drag" and w["doorway_drag"] == 3 and w["flee"] == "doorway"


def test_with_stand_drag_early_off_two_attackers_keep_the_stand_and_three_end_it(tmp_path):
    """The rule before P25-U (ruling R1): DRAG_DOWN_N attackers end the stand, two keep it (the swing)."""
    r, sv, a = _attacked(tmp_path, 2, early=False)
    w = door_why(r)
    assert a.type == "attack" and w["doorway"] == 1 and "doorway_left" not in w
    (tmp_path / "three").mkdir()
    r3, sv3, _ = _attacked(tmp_path / "three", S.DRAG_DOWN_N, early=False)
    assert door_why(r3)["doorway_left"] == "drag" and door_why(r3)["doorway_drag"] == 3


def test_the_stand_s_drag_end_reads_before_the_drag_down_guard(tmp_path):
    """The two rules fire at the same count; the stand's end names the tick (`doorway_left` "drag"), never the guard's
    group steer (`group` "drag"), `_doorway` being the threat plan's first row."""
    r, sv, _ = _attacked(tmp_path, 2)
    w = door_why(r)
    assert w["doorway_left"] == "drag" and w.get("group") != "drag"
