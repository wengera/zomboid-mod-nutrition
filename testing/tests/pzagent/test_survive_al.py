"""Plan 34 Task 1 (the column; F19, `f_goals_19-20261109-060929`, GUIDE.md § 3 "The run and the care": above
RETREAT_MAX_N the leave's `run` alternated with the care, 21 of the 55 decision lines from game minute 770 to 777 the
care's, 8 `stop`s, an `unwear` and 5 `rip`s, each rip superseded 0.5 to 1.5 s later as four or five standing zombies
within 6 tiles closed back to 1.78-2.47 tiles, each care line logging `care_commit` {phase "yield", key ["bleed", 7]}
with the nearest standing 2.9 to 4.2 tiles off): `survive.T19_SWITCHES`, the seven switches of Plan 34 declared on
`threat.Threat`, and LEAVE_CARE's rule (`care_yield.CareYield._care_commit`, `_care_yields`): with GROUP_LEAVE_N or
more standing zombies within GROUP_ENTRY_R (`Threat.group_n`, `group.ThreatGroup._group_read`) no care action takes
the tick but the ride (P24-U, P24-AR, P26-D, P27-O: a bandage with keepMoving on a part above the legs, which keeps
the leg); logged `care_withheld` {why "group", n, key} on the threat's why. The fixtures are synthetic, built from
F19's shape (the GUIDE's numbers), never a replay; the fake mod over PZA/1.5's parts."""
import pytest

from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .test_survive import last, make, threat_why, tick
from .test_survive_g import care_frame, hold, part
from .test_survive_q import z

T19 = S.T19_SWITCHES
COLUMN = (3.6, 4.2, 4.6, 5.5)   # F19's column at line 1559's shape: four standing within 6 tiles, none within KEEP_R
CARE_SENDS = ("stop", "rip", "unwear", "bandage")


def test_the_t19_switches():
    """`survive.T19_SWITCHES`, each a `threat.Threat` attribute on by default (Tasks 2 to 4 fill the six after
    LEAVE_CARE; Task 3 appends CRAWLER_CLEAR, ruling P34-A fix B)."""
    assert T19 == ("LEAVE_CARE", "DOOR_INSIDE", "LEAVE_DOOR_RACE", "RETREAT_GAP", "RETREAT_MELEE", "STRUNG_HOLD",
                   "SHOVE_CLEAR", "CRAWLER_CLEAR")
    assert all(getattr(T.Threat, k) is True for k in T19) and all(getattr(S.Survive, k) is True for k in T19)
    assert "T19_SWITCHES" in S.__all__
    assert (P.GROUP_LEAVE_N, P.GROUP_ENTRY_R) == (3, 6.0)


def bleed_rig(tmp_path, dists, on=True, item=(11, "Base.RippedSheets"), parts=None, **frame):
    """A Survive (GROUP_LEAVE off, `make`'s default) with LEAVE_CARE `on`, `item` held, part 7 bleeding (or `parts`),
    one standing chaser east of the player at each of `dists` tiles; one tick."""
    r, sv = make(tmp_path)
    sv.LEAVE_CARE = on
    hold(r, *item)
    parts = [part(7, bleeding=True, bleedingTime=5.0)] if parts is None else parts
    care_frame(r, parts, zombies=[z(i + 1, 100.0 + d) for i, d in enumerate(dists)], **frame)
    tick(r, sv)
    return r, sv, parts


def care_sent(r):
    """The care sends among the actions sent (a bandage riding a leg, keepMoving, left out)."""
    return [a.type for a in r.acts.history
            if a.type in CARE_SENDS and not (a.type == "bandage" and a.args.get("keepMoving") is True)]


# ================================================================ LEAVE_CARE: the care barred under a column
def test_f19_s_column_withholds_the_care_and_the_threat_branch_answers(tmp_path):
    """F19's line 1559's shape: part 7 bleeding, a rag held, four standing chasers at 3.6, 4.2, 4.6 and 5.5 tiles (none
    within KEEP_R): the threat branch answers (its `many` flee, no care send), its why carrying `care_withheld` {why
    "group", n 4, key ["bleed", 7]}; on the next line, the run's leg running, the rag rides the leg (part 7 above the
    legs, the nearest beyond RIDE_MANY_R: the bandage with keepMoving, P24-AR), the one care send the column leaves, the
    commitment still withheld."""
    r, sv, parts = bleed_rig(tmp_path, COLUMN)
    assert last(tmp_path)["branch"] == "threat" and care_sent(r) == []
    why = threat_why(tmp_path)
    assert why["care_withheld"] == {"why": "group", "n": 4, "key": ["bleed", 7]}
    assert why.get("flee") == "many" and "care_commit" not in why and "care" not in why
    assert sv.group_n == 4
    r.answer("progress")
    r.advance(0.5)
    care_frame(r, parts, zombies=[z(i + 1, 100.0 + d) for i, d in enumerate(COLUMN)])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 11, "part": 7, "keepMoving": True}) and care_sent(r) == []
    why = threat_why(tmp_path)
    assert why["ride"] is True and why["care_withheld"] == {"why": "group", "n": 4, "key": ["bleed", 7]}


@pytest.mark.parametrize("on,branch", [(True, "threat"), (False, "care")])
def test_a_leg_part_bleeding_under_the_column_s_run_is_never_tended_standing(tmp_path, on, branch):
    """A thigh (part 11, LEG_FIRST: no ride) bleeding under the same column, the `many` run's leg running: with the rule
    on the threat branch answers line after line (no care send, `care_withheld` {key ["bleed", 11]}); off (the pin of
    the rule before it), the care's commitment yields and its Dress stops the run, as F19's stops did."""
    r, sv, parts = bleed_rig(tmp_path, COLUMN, on=on, parts=[part(11, bleeding=True, bleedingTime=5.0)])
    if on:
        assert r.cmd()[0] == "steer"
        r.answer("progress")
    for _ in range(2):
        r.advance(0.5)
        care_frame(r, parts, zombies=[z(i + 1, 100.0 + d) for i, d in enumerate(COLUMN)])
        tick(r, sv)
        assert last(tmp_path)["branch"] == branch
    if on:
        assert care_sent(r) == []
        assert threat_why(tmp_path)["care_withheld"] == {"why": "group", "n": 4, "key": ["bleed", 11]}
    else:
        assert care_sent(r)[:1] == ["stop"]


def test_with_leave_care_off_f19_s_column_yields_to_the_care_as_f19_did(tmp_path):
    """The falsifier (a pin of the rule before it, LEAVE_CARE off): the same column yields the tick to the care
    (CARE_COMMIT's yield, the nearest standing beyond CARE_HOLD_R), whose Dress sends its stop, as F19's care lines did;
    nothing logs `care_withheld`."""
    r, sv, _ = bleed_rig(tmp_path, COLUMN, on=False)
    assert last(tmp_path)["branch"] == "care" and care_sent(r) == ["stop"]
    why = threat_why(tmp_path)
    assert "care_withheld" not in why and why["care_commit"]["key"] == ["bleed", 7]


def test_the_ride_goes_under_a_column(tmp_path):
    """The ride kept (P24-U, P24-AR): a bandage held, part 6 (above the legs) bleeding, three standing chasers at 3.5,
    4.2 and 5.0 tiles (the nearest beyond RIDE_MANY_R), the `many` flee's run steer running: with LEAVE_CARE on the
    bandage rides the leg (keepMoving), no standing care send."""
    col = (3.5, 4.2, 5.0)
    r, sv, parts = bleed_rig(tmp_path, col, item=(10, "Base.Bandage"),
                             parts=[part(6, bleeding=True, bleedingTime=5.0)])
    assert last(tmp_path)["branch"] == "threat" and threat_why(tmp_path).get("flee") == "many"
    assert r.cmd()[0] == "steer" and care_sent(r) == []
    r.answer("progress")
    r.advance(0.5)
    care_frame(r, parts, zombies=[z(i + 1, 100.0 + d) for i, d in enumerate(col)])
    tick(r, sv)
    assert r.cmd() == ("bandage", {"itemId": 10, "part": 6, "keepMoving": True})
    assert threat_why(tmp_path)["ride"] is True and care_sent(r) == []


def test_two_standing_yield_to_the_care_as_before(tmp_path):
    """Under GROUP_LEAVE_N: two standing chasers at 3.6 and 4.2 tiles, part 7 bleeding, a rag held: the care's yield as
    before (CARE_COMMIT's yield, the Dress's stop), nothing withheld."""
    r, sv, _ = bleed_rig(tmp_path, COLUMN[:2])
    assert last(tmp_path)["branch"] == "care" and care_sent(r) == ["stop"]
    assert "care_withheld" not in threat_why(tmp_path) and sv.group_n == 2


@pytest.mark.parametrize("third,withheld", [(5.9, True), (6.1, False)])
def test_the_count_s_edge_is_group_entry_r(tmp_path, third, withheld):
    """The count's edge: two standing at 3.6 and 4.2 tiles and a third at 5.9 (within GROUP_ENTRY_R) withhold the care;
    the third at 6.1 does not (the count 2: the care's stop)."""
    r, sv, _ = bleed_rig(tmp_path, (3.6, 4.2, third))
    why = threat_why(tmp_path)
    if withheld:
        assert last(tmp_path)["branch"] == "threat" and care_sent(r) == []
        assert why["care_withheld"] == {"why": "group", "n": 3, "key": ["bleed", 7]}
    else:
        assert last(tmp_path)["branch"] == "care" and care_sent(r) == ["stop"] and "care_withheld" not in why


def test_group_n_counts_the_standing_within_group_entry_r_on_a_plain_fight_line(tmp_path):
    """`group_n` is read every tick, a line without the care included: a fight line (one standing at 2.0 tiles, one at
    4.0, a fallen one at 3.0, one standing at 7.0) reads 2, the fallen one and the one beyond GROUP_ENTRY_R left out;
    nothing withheld."""
    r, sv = make(tmp_path)
    r.frame(zombies=[z(1, 102.0), z(2, 104.0), z(3, 103.0, floor=True), z(4, 107.0)])
    tick(r, sv)
    assert last(tmp_path)["branch"] == "threat" and sv.group_n == 2
    assert sv.care_withheld is None and "care_withheld" not in threat_why(tmp_path)
