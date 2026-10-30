"""Survival 11 (survival iteration 10; Plan 24 Task 27, spec § 6 item 20 and amendment 6's guides' rulings; PZA/1.7 on the planner), the
threat branch's half: ruling P24-AG's disengage (the arms' strain hold at `body.armPain` STRAIN_HARD, released under
STRAIN_SOFT; the ENDURANCE moodle's first level) and ruling P24-AK's tired gate (`stats.fatigue` at TIRED_FIGHT_T):
a spent character flees `strain`, engages and seeks nothing, and a `walk` corner yields. The Fight's half (the shove
and the stomp) is `test_survive_m.py`; the legs and the unwear `test_survive_n.py`. The fake mod over PZA/1.7."""
import pytest

from agent.base.planner import policies as P
from agent.base.planner import survive as S

from .test_policies import zombie
from .test_survive import make, threat_why, tick, last


def fr(r, arm=None, zs=(), stiff=None, **k):
    """A frame with `body.armPain` `arm` (None: an older Lua's null), the left arm's stiffness `stiff` (`body.strain`
    {l: stiff, r: 0}; None: an older Lua's null) and zombies `zs`."""
    r.frame(zombies=list(zs), wounds={"armPain": arm, "strain": None if stiff is None else {"l": stiff, "r": 0.0}},
            **k)


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


def test_a_stiffness_of_20_disengages_the_fight_and_the_hold_lasts_until_under_5(tmp_path):
    """P24-AG as ruling P24-AT reads it (named change, Plan 24 Task 36: the hold reads the arms' stiffness, STIFF_HARD
    and STIFF_SOFT, no longer the pain): the running fight at a stiffness of 20 turns to the flee (reason `strain`,
    the why naming it, a steer at a run: the flee's legs as today); at 15 the hold keeps the flee; at 4.99 the hold
    ends and the flee turns to fight the one held zombie again (its leg ended)."""
    r, sv = fight_on(tmp_path, stiff=19.99)
    fr(r, None, [zombie(1, 104.0, 200.0)], stiff=20.0)
    a = tick(r, sv)
    w = threat_why(tmp_path)
    assert sv.mode == "flee" and w["flee"] == "strain" and a.type == "steer" and a.args["gait"] == "run"
    assert w["strain"] == {"kind": "arms", "armPain": None, "endurance": 1.0, "fatigue": 0.05,
                           "strain": {"l": 20.0, "r": 0.0}}
    r.answer()
    fr(r, None, [zombie(1, 104.0, 200.0)], stiff=15.0)
    tick(r, sv)
    assert sv.mode == "flee" and threat_why(tmp_path)["flee"] == "strain" and sv.strain_hold
    r.answer()
    fr(r, None, [zombie(1, 104.0, 200.0)], stiff=4.99)
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
    not engaged and the goal runs; one at 4 tiles is fled `strain`. Once the stiffness reads under 5 the same 7-tile
    zombie is engaged (P24-X). Named change, Task 36 (P24-AT): the hold set and held by the stiffness."""
    r, sv = make(tmp_path)
    fr(r, None, stiff=25.0)
    tick(r, sv)
    assert sv.strain_hold
    fr(r, None, [zombie(1, 107.0, 200.0)], stiff=12.0)
    tick(r, sv)
    assert last(tmp_path)["branch"] != "threat" and sv.mode is None and sv._sought() is None
    fr(r, None, [zombie(1, 104.0, 200.0)], stiff=12.0)
    tick(r, sv)
    assert sv.mode == "flee" and threat_why(tmp_path)["flee"] == "strain"
    (tmp_path / "b").mkdir()
    r2, sv2 = make(tmp_path / "b")
    fr(r2, None, [zombie(1, 107.0, 200.0)], stiff=4.0)
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
    for st, e, f, kind in ((20.0, 0.5, 0.9, "arms"), (4.0, 0.5, 0.9, "endurance"), (None, 0.9, 0.9, "tired"),
                           (None, 0.9, 0.1, None)):   # named change, Task 36 (P24-AT): the arms' read is the stiffness
        fr(r, None, endurance=e, fatigue=f, stiff=st)
        sv._read_spent()
        got = sv.spent
        assert (got and got["kind"]) == kind, (st, e, f)


def test_the_endurance_hold_is_released_only_above_0_80(tmp_path):
    """Review-t27 blocker 1 (F1 gm 635-637: 0.747, then a fight started at 0.753, then 0.740): the hold set at 0.75 or
    under holds through 0.753, 0.76 and 0.80 itself, and ends above ENDURANCE_RELEASE 0.80; a hold not set (0.76 from
    rest) is not set by the band."""
    assert P.ENDURANCE_RELEASE == 0.80
    r, sv = make(tmp_path)
    for e, held in ((0.76, False), (0.747, True), (0.753, True), (0.80, True), (0.74, True), (0.801, False),
                    (0.76, False), (0.75, True)):
        fr(r, None, endurance=e)
        sv._read_spent()
        assert (sv.spent is not None) is held and sv.endurance_hold is held, e
        assert held is False or sv.spent["kind"] == "endurance"


def test_the_f1_sequence_holds_the_flee_through_gm_637(tmp_path):
    """The F1 record's three readings through the machine: a fight at 0.76, 0.747 flees `strain`, 0.753 keeps fleeing
    (no turn back for a swing), 0.740 still flees; 0.81 turns to fight again."""
    r, sv = fight_on(tmp_path, endurance=0.76)
    for e, mode in ((0.747, "flee"), (0.753, "flee"), (0.740, "flee"), (0.81, "fight")):
        r.answer()
        fr(r, None, [zombie(1, 104.0, 200.0)], endurance=e)
        tick(r, sv)
        assert sv.mode == mode, e
        if mode == "flee":
            assert threat_why(tmp_path)["flee"] == "strain"


def test_an_older_frame_with_no_stiffness_ends_the_hold(tmp_path):
    """No `body.strain` (an older Lua): nothing to hold on, the hold ends (named change, Task 36: P24-AT's read)."""
    r, sv = make(tmp_path)
    fr(r, 30.0, stiff=30.0)
    sv._read_spent()
    assert sv.strain_hold
    fr(r, 30.0)
    sv._read_spent()
    assert not sv.strain_hold and sv.spent is None


def test_a_walk_corner_yields_to_the_strain_after_health_and_a_many_episode(tmp_path):
    """P24-AG: a spent character's `walk` corner yields (`strain`), as under the health flee; `health` and a running
    `many` episode read first."""
    r, sv = make(tmp_path)
    fr(r, None, endurance=0.7)
    sv._read_spent()
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
    assert sv.mode == "fight" and sv.spent is None
