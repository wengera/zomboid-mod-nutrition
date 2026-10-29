"""Survival 9 (Plan 24 Task 21, spec § 6 item 19; the eighth chain's E8, `e_day_8-20261029-174023`: four kills, then
two bites, one bandaged, the other bleeding 73 game minutes to the death with no dressing held; from game minute 618
every goal walk failed `no square`, 62 to 234 tiles off; fight 1's `many` fired on three held, two of them idle):
refactor A (a pure ordered `assess`, the water chain lifted out), P24-AB (the rag stock), P24-AC (legged far walks),
P24-AD (idle zombies and `many`). The fake mod over the PZA/1.5 skills."""
import json

from agent.base.planner import survive as S
from agent.base.planner import water as W

from .test_survive import make, tick


# ================================================================ refactor A
def test_assess_decides_without_sending_or_writing_and_apply_sends_and_logs(tmp_path):
    """Refactor A: `assess` returns the Decision (branch, owner, command, inputs) with nothing sent and no line
    written; `_apply` sends it through its owner and appends the line; `tick` is the two."""
    r, sv = make(tmp_path)
    r.frame(zombies=[dict(id=1, x=104.0, y=200.0, dist=4.0, hasTarget=True, crawler=False, health=1.0)])
    sent_before = len(r.acts.history)
    d = sv.assess(sv._read(r.world, r.acts))
    assert isinstance(d, S.Decision) and d.branch == "threat" and d.cmd is not None and d.owner is sv.fight
    assert len(r.acts.history) == sent_before and not (tmp_path / "decision.log").exists()
    assert set(d.inputs["branches"]) == {"threat"} and d.inputs["cooled"] is None
    a = sv._apply(d)
    assert a is r.acts.history[-1] and a.type == d.cmd.TYPE and sv.last_branch == "threat"
    line = json.loads((tmp_path / "decision.log").read_text(encoding="utf-8").splitlines()[-1])
    assert line["branch"] == "threat" and line["sent"] is True and line["action"]["type"] == d.cmd.TYPE


def test_the_water_chain_is_its_own_module_and_survive_re_exports_its_constants():
    """Refactor A (the Task 10 review's ruling 7): `planner/water.py` holds the fill, its constants and its wants."""
    assert (S.FILL_SETTLE_S, S.FILL_RETRY_MIN, S.FILL_WANTS, S.SOURCE_FAILS) == (
        W.FILL_SETTLE_S, W.FILL_RETRY_MIN, W.FILL_WANTS, W.SOURCE_FAILS)
    assert not hasattr(S.Survive, "_fill_plan") and not hasattr(S.Survive, "_check_fills")


def test_survive_s_fills_are_the_water_chain_s(tmp_path):
    r, sv = make(tmp_path)
    assert sv.fills is sv.water.fills
    marks = {"container": 1.0, "water_source": 2.0, "water": 3.0}
    sv.water.why = {"want": "water_source"}
    sv.water.wants(marks, 9.0)
    assert marks == {"water_source": 9.0, "water": 3.0}
    W.Water.clear(marks)
    assert marks == {"water": 3.0}
