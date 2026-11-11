"""Plan 34 Task 3c (ruling P34-I; the trial `x_trial-ladder-20261109-132439`, the fix arm at b1e99cfc on the `agent`
fixture with the model, P31-T, not evidence; its row in `testing/trials/trials.md`): the retreat's rhythm. After 11
kills with no hit three standing zombies stood on the character at 0.5 tiles and the leave fired (decision line 407);
then thirty lines churned: the retreat's band sent the melee (every one in mode `shove`, the meet spent), the drag
guard at `me.attackers` 2 sent its `many` run superseding it, the next line sent the melee again, the back leg almost
never went, nine bites from line 432 and the drag-down at game minute 622. Two switches of `survive.T19_SWITCHES` on
`threat.Threat` stay (Plan 35 Task 8 deleted RETREAT_REGAIN and DRAG_DEFER with their tests, named in its report):

- SPENT_LEAVE (the leave's, `group.ThreatGroup._leave_leg`): with the meet spent (the melee's mode `shove`: a hold or a
  shove-and-stomp Fight, `ThreatGroup._spent_meet`) the retreat's upper bound is GROUP_LEAVE_N - 1, so GROUP_LEAVE_N
  standing within GROUP_ENTRY_R take the `run`, logged `group_leave` {leg "run", n, spent true}.
- RUN_HOLD (amendment 1; the trial `x_trial-ladder-20261109-134527`, lines 412 to 449: the leg flicked between the run
  at five and the retreat at four, the character never running clear): once a leave's leg read `run` it stays `run`
  while that leave holds, logged `group_leave` {leg "run", n, held true}.

The fixtures are synthetic, built from the trial's numbers, never a replay; the fake mod."""
from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .test_survive import threat_why, tick
from .test_survive_ak import FIVE_NEAR, band, closing, pair


# ================================================================ the switches and the constant
def test_the_switches_and_the_constant():
    """SPENT_LEAVE and amendment 1's RUN_HOLD on `threat.Threat` (and so `survive.Survive`), on by default, the last two
    of `survive.T19_SWITCHES`; Plan 35 Task 8: no RETREAT_REGAIN or DRAG_DEFER switch, no `retreat_regain` Fight rule,
    no RETREAT_REGAIN_S."""
    assert S.T19_SWITCHES[-2:] == ("SPENT_LEAVE", "RUN_HOLD")
    for name in ("SPENT_LEAVE", "RUN_HOLD"):
        assert getattr(T.Threat, name) is True and getattr(S.Survive, name) is True, name
    assert not any(hasattr(T.Threat, n) for n in ("RETREAT_REGAIN", "DRAG_DEFER"))
    assert "retreat_regain" not in F.FIGHT_RULES and not hasattr(P, "RETREAT_REGAIN_S")


# ================================================================ (c) SPENT_LEAVE
def test_a_spent_meet_takes_the_run_at_group_leave_n(tmp_path):
    """Three standing closing within GROUP_ENTRY_R with the meet spent (the tired hold, `stats.fatigue` 0.7): the leg is
    the `run` (`group_leave` {leg "run", n 3, spent true}, the threat plan's `many` flee, a run steer); unspent, the
    retreat; with SPENT_LEAVE off and spent (a pin), the retreat."""
    r, sv = closing(tmp_path, fatigue=0.7)
    why = threat_why(tmp_path)
    assert why["group_leave"]["leg"] == "run" and why["group_leave"]["n"] == 3 and why["group_leave"]["spent"] is True
    assert why["flee"] == "many" and r.cmd()[0] == "steer" and r.cmd()[1]["gait"] == "run"
    (tmp_path / "fresh").mkdir()
    closing(tmp_path / "fresh")
    gl = threat_why(tmp_path / "fresh")["group_leave"]
    assert gl["leg"] == "retreat" and "spent" not in gl
    (tmp_path / "off").mkdir()
    closing(tmp_path / "off", off=("SPENT_LEAVE",), fatigue=0.7)
    gl = threat_why(tmp_path / "off")["group_leave"]
    assert gl["leg"] == "retreat" and "spent" not in gl


# ================================================================ amendment 1: RUN_HOLD
FAR = ((100.5, 207.5), (93.0, 200.5), (108.5, 200.5), (100.5, 193.0))   # 7.0 to 8.0 tiles: beyond GROUP_ENTRY_R


def counted(n):
    """FIVE_NEAR's first `n` within GROUP_ENTRY_R, the rest moved beyond it."""
    return FIVE_NEAR[:n] + FAR[:5 - n]


def held_run(tmp_path, hold=True):
    """The leave opened by five closing (the `run`), then the counts 4, 4, 3, 2 a line, RUN_HOLD `hold`; each line's
    `group_leave` (None on a line logging none), the first line's included."""
    r, sv = band(tmp_path, 5)
    sv.RUN_HOLD = hold
    out = [threat_why(tmp_path)["group_leave"]]
    for n in (4, 4, 3, 2):
        r.advance(0.5)
        r.frame(x=100.5, y=200.5, zombies=pair(counted(n)))
        tick(r, sv)
        out.append(threat_why(tmp_path).get("group_leave"))
    return sv, out


def test_a_leave_that_ran_keeps_the_run_until_it_ends_strung(tmp_path):
    """The counts 5, 4, 4, 3, 2: the leg reads `run` on the first four lines (held from the second, `held` true, `n` the
    count); the fifth, two standing, ends the leave `strung` (Plan 35 Task 8 deleted STRUNG_HOLD's held lines)."""
    sv, gl = held_run(tmp_path)
    assert [g.get("leg") for g in gl[:4]] == ["run"] * 4
    assert [g.get("held", False) for g in gl[:4]] == [False, True, True, True]
    assert [g["n"] for g in gl[:4]] == [5, 4, 4, 3]
    assert gl[4] == {"end": "strung", "n": 2} and sv.leave is None


def test_with_run_hold_off_the_count_reads_the_retreat_again(tmp_path):
    """A pin (RUN_HOLD off, the rule before it): the second and third lines (four standing) read the retreat."""
    sv, gl = held_run(tmp_path, hold=False)
    assert gl[0]["leg"] == "run" and gl[1]["leg"] == "retreat" and gl[2]["leg"] == "retreat"
    assert all("held" not in (g or {}) for g in gl)
