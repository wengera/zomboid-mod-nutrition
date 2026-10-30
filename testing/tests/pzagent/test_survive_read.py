"""Plan 25 Task 2 (the close review of Plan 24, minor 8; refactor A's rule `_read` -> `assess` -> `_apply`): every
observe of a policy the tick holds when `_read` returns (the Night, the Care, the running Fight and the Flee) runs in
`_read`, once, and `assess` calls none (`OBSERVES_IN_READ`, the named golden cause; off, the observes as Plan 24 left
them inside `assess`). A policy `assess` itself makes (a new Fight, Flee or Doorway) takes its first observe at its
answer: its construction read, no action of its own to end yet."""
import pytest

from agent.base.planner.care import Care
from agent.base.planner.fight import Fight
from agent.base.planner.flee import Flee
from agent.base.planner.night import Night

from .test_survive import make, tick
from .test_survive_q import fr, z


@pytest.fixture
def calls(monkeypatch):
    """Every observe as (phase, policy), the phase `read` inside `Survive._read`, `assess` after it."""
    log, phase = [], {"now": None}
    for cls in (Night, Care, Fight, Flee):
        orig = cls.observe

        def rec(self, _orig=orig):
            log.append((phase["now"], self))
            return _orig(self)
        monkeypatch.setattr(cls, "observe", rec)
    return log, phase


def run(r, sv, phase):
    """One tick through `_read`, `assess` and `_apply`, the phase marked; returns the policies held at `_read`'s end."""
    phase["now"] = "read"
    inputs = sv._read(r.world, r.acts)
    held = [p for p in (sv.night, sv.care, sv.fight, sv.flee) if p is not None]
    phase["now"] = "assess"
    d = sv.assess(inputs)
    phase["now"] = "apply"
    sv._apply(d)
    return held


@pytest.mark.parametrize("health", [100.0, 30.0])   # a fight, then the health flee
def test_assess_calls_no_observe_of_a_policy_read_held(tmp_path, calls, health):
    log, phase = calls
    r, sv = make(tmp_path)
    for x in (104.0, 103.0, 102.0):
        fr(r, [z(1, x)], health=health)
        del log[:]
        held = run(r, sv, phase)
        assert sv.fight is not None or sv.flee is not None
        for p in held:
            seen = [ph for ph, q in log if q is p]
            assert seen == ["read"], (type(p).__name__, seen)
        made = [q for ph, q in log if ph == "assess"]
        assert all(not any(q is p for p in held) for q in made)
        r.answer()


def test_with_the_switch_off_the_threat_s_observes_run_in_assess(tmp_path, calls):
    """`OBSERVES_IN_READ` off (the rules before Task 2): the Fight made on the first tick is observed in `assess` on
    the next, the Night only where its branch is reached."""
    log, phase = calls
    r, sv = make(tmp_path)
    sv.OBSERVES_IN_READ = False
    fr(r, [z(1, 104.0)])
    run(r, sv, phase)
    fr(r, [z(1, 103.0)])
    del log[:]
    held = run(r, sv, phase)
    f = next(p for p in held if isinstance(p, Fight))
    assert [ph for ph, q in log if q is f] == ["assess"]
    assert not any(isinstance(q, Night) for _, q in log)


def test_a_tick_through_tick_reads_each_held_policy_once(tmp_path, calls):
    log, phase = calls
    r, sv = make(tmp_path)
    fr(r, [z(1, 104.0)])
    tick(r, sv)
    fr(r, [z(1, 103.0)])
    del log[:]
    tick(r, sv)
    for p in (sv.night, sv.care, sv.fight):
        assert sum(1 for _, q in log if q is p) == 1
