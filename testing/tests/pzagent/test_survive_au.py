"""Plan 36 Task 2a addendum (the press on the back step; the spec `2026-11-11-plan-36-the-engagement-design.md`
§ 3.2): `survive.T21_SWITCHES`, the switch BACKSWING beside Task 4's ACTION_CLOCK (merged at the controller's cherry-pick) on `threat.Threat`, on by default: every melee sent with work
carries backswing true (the Fight's `backswing`, set each tick beside its withdraw; `dispatch.FightDispatch.
_work_inputs`, `maneuvers.melee.WorkInputs.backswing`), so the reflex keeps its step's walk held through a press
(PZAgent_StanceMelee.lua's K.meleePressWalk). Off, or on a bare Fight, the melee goes as before (backswing false is
absent on the wire). Synthetic fixtures (test_survive_ar.py's), the fake mod."""
from agent.base.planner import survive as S
from agent.base.planner import threat as T
from agent.base.planner.maneuvers.melee import WorkInputs
from agent.driverlib import trial

from .test_survive import threat_why, tick
from .test_survive_ar import ONE, WORK_ARGS, fight, rig, work_of
from .test_survive_q import z


def test_the_switch_is_declared_on_by_default_and_recorded_by_the_trial_loop(tmp_path):
    assert S.T21_SWITCHES == ("ACTION_CLOCK", "BACKSWING") and "T21_SWITCHES" in S.__all__
    assert T.Threat.BACKSWING is True
    r = rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    assert trial.switches(sv)["BACKSWING"] is True


def test_the_work_inputs_carry_backswing_into_the_args_and_the_behaviour():
    on = WorkInputs(3.5, 1.2, 0.4, None, 40.0, True, backswing=True)
    off = WorkInputs(3.5, 1.2, 0.4, None, 40.0, True)
    assert on.args()["backswing"] is True and off.args()["backswing"] is False
    assert on.behaviour() != off.behaviour()


def test_a_bare_fight_sends_no_backswing(tmp_path):
    """A Fight Survive never set (the attribute's default False): the melee's args as before, no backswing key."""
    r, f = fight(tmp_path, ONE)
    a = f.step()
    assert a.type == "melee" and work_of(a) == WORK_ARGS and "backswing" not in a.args


def test_a_fight_with_backswing_sends_it_with_the_work(tmp_path):
    r, f = fight(tmp_path, ONE)
    f.backswing = True
    a = f.step()
    assert a.type == "melee" and work_of(a) == WORK_ARGS and a.args["backswing"] is True


def _corner(tmp_path, backswing):
    """test_survive_ar's corner fight (two standing at 0.5 tiles: `cornered`), the melee with work at its pin."""
    r = rig(tmp_path)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    sv.GROUP_LEAVE = False
    if backswing is not None:
        sv.BACKSWING = backswing
    r.frame(zombies=[z(1, 100.5), z(2, 100.0, 200.5)])
    tick(r, sv)
    assert threat_why(tmp_path)["cornered"] == 1
    return r.acts.history[-1]


def test_survive_sends_backswing_on_every_melee_with_work(tmp_path):
    a = _corner(tmp_path, None)
    assert a.type == "melee" and work_of(a) == WORK_ARGS and a.args["backswing"] is True


def test_with_the_switch_off_the_melee_goes_as_before(tmp_path):
    a = _corner(tmp_path, False)
    assert a.type == "melee" and work_of(a) == WORK_ARGS and "backswing" not in a.args
