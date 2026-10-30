"""Survival 11 (Plan 24 Task 27, spec § 6 item 20 and amendment 6's guides' rulings; PZA/1.7 on the planner), the
threat branch's half: ruling P24-AG's disengage (the arms' strain hold at `body.armPain` STRAIN_HARD, released under
STRAIN_SOFT; the ENDURANCE moodle's first level) and ruling P24-AK's tired gate (`stats.fatigue` at TIRED_FIGHT_T):
a spent character flees `strain`, engages and seeks nothing, and a `walk` corner yields. The Fight's half (the shove
and the stomp) is `test_survive_m.py`; the legs and the unwear `test_survive_n.py`. The fake mod over PZA/1.7."""
import pytest

from agent.base.planner import policies as P
from agent.base.planner import survive as S

from .test_policies import zombie
from .test_survive import make, threat_why, tick, last


def fr(r, arm=None, zs=(), **k):
    """A frame with `body.armPain` `arm` (None: an older Lua's null) and zombies `zs`."""
    r.frame(zombies=list(zs), wounds={"armPain": arm}, **k)


def fight_on(tmp_path, arm=None, **k):
    """A Survive whose fight runs on zombie 1, 4 tiles east (within DANGER_R)."""
    r, sv = make(tmp_path)
    fr(r, arm, [zombie(1, 104.0, 200.0)], **k)
    tick(r, sv)
    assert sv.mode == "fight" and threat_why(tmp_path)["fight"] is True
    return r, sv


def test_the_strain_constants():
    """#4370: a swing's damage is divided by armPain / 10 past 10, halved at 20; #3926, #4076: the ENDURANCE moodle's
    first level at endurance 0.75 or under; P24-AK: fatigue 0.6, the first TIRED moodle (night.TIRED_T)."""
    from agent.base.planner import night as N
    assert (P.STRAIN_SOFT, P.STRAIN_HARD, P.ENDURANCE_T, P.TIRED_FIGHT_T) == (10.0, 20.0, 0.75, 0.6)
    assert P.TIRED_FIGHT_T == N.TIRED_T and S.Survive.STRAIN is True


def test_arm_pain_20_disengages_the_fight_and_the_hold_lasts_until_under_10(tmp_path):
    """P24-AG: the running fight at armPain 20 turns to the flee (reason `strain`, the why naming it, a steer at a run:
    the flee's legs as today); at 15 the hold keeps the flee; at 9.99 the hold ends and the flee turns to fight the one
    held zombie again (its leg ended)."""
    r, sv = fight_on(tmp_path, arm=19.99)
    fr(r, 20.0, [zombie(1, 104.0, 200.0)])
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert sv.mode == "flee" and w["flee"] == "strain" and a.type == "steer" and a.args["gait"] == "run"
    assert w["strain"] == {"kind": "arms", "armPain": 20.0, "endurance": 1.0, "fatigue": 0.05}
    r.answer()
    fr(r, 15.0, [zombie(1, 104.0, 200.0)])
    tick(r, sv)
    assert sv.mode == "flee" and threat_why(tmp_path)["flee"] == "strain" and sv.strain_hold
    r.answer()
    fr(r, 9.99, [zombie(1, 104.0, 200.0)])
    tick(r, sv)
    assert sv.mode == "fight" and not sv.strain_hold and "strain" not in threat_why(tmp_path)


def test_arm_pain_between_the_lines_never_starts_the_hold(tmp_path):
    """P24-AG's hysteresis: 19.99 is under STRAIN_HARD, so the fight goes on (the Fight's own shove and stomp read
    STRAIN_SOFT: `test_survive_m.py`)."""
    r, sv = fight_on(tmp_path, arm=19.99)
    fr(r, 19.99, [zombie(1, 104.0, 200.0)])
    tick(r, sv)
    assert sv.mode == "fight" and not sv.strain_hold


def test_no_new_engage_while_the_strain_hold_runs(tmp_path):
    """P24-AG: no new fight while the hold runs: a chasing zombie at 7 tiles (within ENGAGE_R, beyond DANGER_R) is
    not engaged and the goal runs; one at 4 tiles is fled `strain`. Once armPain reads under 10 the same 7-tile zombie
    is engaged (P24-X)."""
    r, sv = make(tmp_path)
    fr(r, 25.0)
    tick(r, sv)
    assert sv.strain_hold
    fr(r, 12.0, [zombie(1, 107.0, 200.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] != "threat" and sv.mode is None and sv._sought() is None
    fr(r, 12.0, [zombie(1, 104.0, 200.0)])
    tick(r, sv)
    assert sv.mode == "flee" and threat_why(tmp_path)["flee"] == "strain"
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    fr(r2, 9.0, [zombie(1, 107.0, 200.0)])
    tick(r2, sv2)
    assert sv2.mode == "fight" and threat_why(tmp_path / "b")["fight"] is True


@pytest.mark.parametrize("endurance,spent", [(0.75, True), (0.7, True), (0.76, False)])
def test_the_endurance_moodle_starts_no_fight_and_disengages(tmp_path, endurance, spent):
    """P24-AG (#4371: the first ENDURANCE level halves every swing): at endurance 0.75 or under a zombie at 4 tiles is
    fled `strain` (kind `endurance`), none at 7 engaged; over it, fought."""
    r, sv = make(tmp_path)
    fr(r, None, [zombie(1, 104.0, 200.0)], endurance=endurance)
    tick(r, sv)
    w = threat_why(tmp_path)
    if spent:
        assert sv.mode == "flee" and w["flee"] == "strain" and w["strain"]["kind"] == "endurance"
    else:
        assert sv.mode == "fight" and w["fight"] is True
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    fr(r2, None, [zombie(1, 107.0, 200.0)], endurance=endurance)
    tick(r2, sv2)
    assert (sv2.mode is None) is spent


def test_a_running_fight_disengages_at_the_endurance_moodle(tmp_path):
    r, sv = fight_on(tmp_path)
    fr(r, None, [zombie(1, 104.0, 200.0)], endurance=0.74)
    tick(r, sv)
    assert sv.mode == "flee" and threat_why(tmp_path)["strain"]["kind"] == "endurance"


@pytest.mark.parametrize("fatigue,spent", [(0.6, True), (0.8, True), (0.59, False)])
def test_the_tired_gate(tmp_path, fatigue, spent):
    """Ruling P24-AK (the guides' tired gate; #4371: the first TIRED level halves every swing): no sought or standing
    fight at fatigue 0.6 or above: a zombie at 4 tiles is fled `strain` (kind `tired`), one at 7 not engaged."""
    r, sv = make(tmp_path)
    fr(r, None, [zombie(1, 104.0, 200.0)], fatigue=fatigue)
    tick(r, sv)
    w = threat_why(tmp_path)
    assert (sv.mode == "flee" and w["strain"]["kind"] == "tired") if spent else sv.mode == "fight"
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    fr(r2, None, [zombie(1, 107.0, 200.0)], fatigue=fatigue)
    tick(r2, sv2)
    assert (sv2.mode is None) is spent


def test_the_hold_reads_the_arms_first_then_the_endurance_then_the_tiredness(tmp_path):
    r, sv = make(tmp_path)
    for arm, e, f, kind in ((20.0, 0.5, 0.9, "arms"), (5.0, 0.5, 0.9, "endurance"), (None, 0.9, 0.9, "tired"),
                            (None, 0.9, 0.1, None)):
        fr(r, arm, endurance=e, fatigue=f)
        sv._read_strain()
        got = sv._spent()
        assert (got and got["kind"]) == kind, (arm, e, f)


def test_an_older_frame_with_no_arm_pain_ends_the_hold(tmp_path):
    """No `body.armPain` (an older Lua): nothing to hold on, the hold ends."""
    r, sv = make(tmp_path)
    fr(r, 30.0)
    sv._read_strain()
    assert sv.strain_hold
    fr(r, None)
    sv._read_strain()
    assert not sv.strain_hold and sv._spent() is None


def test_a_walk_corner_yields_to_the_strain_after_health_and_a_many_episode(tmp_path):
    """P24-AG: a spent character's `walk` corner yields (`strain`), as under the health flee; `health` and a running
    `many` episode read first."""
    r, sv = make(tmp_path)
    fr(r, None, endurance=0.7)
    assert sv._walk_yields() == "strain"
    sv.mode, sv.flee_many = "flee", True
    assert sv._walk_yields() == "many"
    fr(r, None, endurance=0.7, health=30.0)
    assert sv._walk_yields() == "health"


def test_with_strain_off_nothing_is_read(tmp_path):
    """The seam (`Survive.STRAIN`, the replay tests' `pre_ag`): off, armPain 30, endurance 0.5 and fatigue 0.9 fight."""
    r, sv = make(tmp_path)
    sv.STRAIN = False
    fr(r, 30.0, [zombie(1, 104.0, 200.0)], endurance=0.5, fatigue=0.9)
    tick(r, sv)
    assert sv.mode == "fight" and sv._spent() is None
