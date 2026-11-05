"""Survival 24 (survival iteration 22; Plan 28 Task 7b; the architecture review `arch-review-cerebellum.md` §§ 3.5 and
4.2, cut 1 of the maneuver layer; Task 7a's reflex skill `melee`, PZA/1.8). The fake mod over PZA/1.8, its hello
announcing `melee` only where a test asks (`fakemod.MELEE_CAPS`); each test's geometry is the review's cases.

- The `Maneuver` base (`planner/maneuvers/base.py`): one named physical sequence with its own state, one command at a
  time; `observe()` reads its own actions' ends (each once, an earlier one's late end too) and its current action's
  progress lines, `step()` the next command or None, `over()` None while it runs else its end (`superseded` once
  another sender took the slot), `why` its own fields, logged as `{maneuver: name, ...}`.
"""
from agent.base.planner.maneuvers import Maneuver
from agent.base.pza1 import Scan

from .fakemod import MELEE_CAPS
from .test_policies import Rig


class Scanner(Maneuver):
    """A maneuver of one command a turn: a scan of radius 4, re-sent while its owner calls `step`."""
    name = "scanner"

    def __init__(self, world, actions, clock):
        super().__init__(world, actions, clock)
        self.ends, self.lines = [], []

    def step(self):
        return None if self.over() is not None or self.running() else Scan(4)

    def ended(self, a, current):
        self.ends.append((a.aid, a.state, a.reason, current))

    def progressed(self, line):
        self.lines.append(line["result"])


def send(r, m):
    """`m`'s next command sent through the rig's Actions as its owner would, `m.sent` told."""
    cmd = m.step()
    a = r.acts.send(cmd)
    m.sent(cmd, a)
    return a


def act(r, a, state, reason="", result=None):
    r.fake.act(a.aid, state, a.type, reason=reason, result=result)
    r.pump()


# ================================================================ the Maneuver base
def test_a_maneuver_that_sent_nothing_runs_nothing_and_has_no_end(tmp_path):
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Scanner(r.world, r.acts, r.clock)
    m.observe()
    assert (m.action, m.running(), m.over(), m.drained(), m.why, m.n) == (None, False, None, True, {}, 0)
    assert m.log() == {"maneuver": "scanner"}


def test_observe_reads_its_current_action_s_end_once(tmp_path):
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Scanner(r.world, r.acts, r.clock)
    a = send(r, m)
    assert m.action is a and m.running() and not m.drained() and m.n == 1 and m.step() is None
    act(r, a, "accepted")
    m.observe()
    assert m.ends == [] and m.running()
    act(r, a, "done", result={})
    m.observe()
    m.observe()
    assert m.ends == [(a.aid, "done", "", True)] and not m.running() and m.drained() and m.over() is None


def test_an_earlier_action_s_late_end_is_read_as_not_current(tmp_path):
    """The maneuver's second send supersedes its first in the Lua; the first's end (here a late `done`, the line
    written before the second reached the Lua) is still read, once, marked not current."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Scanner(r.world, r.acts, r.clock)
    a = send(r, m)
    act(r, a, "accepted")
    b = r.acts.send(Scan(4))
    m.sent(Scan(4), b)
    act(r, a, "done", result={"kill": True})
    m.observe()
    assert m.ends == [(a.aid, "done", "", False)] and m.action is b and m.running() and m.over() is None
    assert m.n == 2 and not m.drained()


def test_another_sender_s_command_ends_the_maneuver_superseded(tmp_path):
    """One command at a time: once another sender's action is current, the maneuver's own (not yet ended) no longer
    runs, and its end is `superseded` at once (the Lua's `failed superseded` line read later, still once)."""
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Scanner(r.world, r.acts, r.clock)
    a = send(r, m)
    act(r, a, "accepted")
    r.acts.send(Scan(2))
    m.observe()
    assert not m.running() and m.over() == "superseded" and m.step() is None and not m.drained()
    act(r, a, "failed", "superseded")
    m.observe()
    assert m.ends == [(a.aid, "failed", "superseded", True)] and m.drained() and m.over() == "superseded"


def test_progress_lines_of_the_current_action_are_read_once_each(tmp_path):
    r = Rig(tmp_path, caps=MELEE_CAPS)
    m = Scanner(r.world, r.acts, r.clock)
    a = send(r, m)
    act(r, a, "accepted")
    act(r, a, "progress", result={"step": "stand"})
    m.observe()
    m.observe()
    act(r, a, "progress", result={"step": "face"})
    act(r, a, "progress", result={"step": "swing"})
    m.observe()
    assert m.lines == [{"step": "stand"}, {"step": "face"}, {"step": "swing"}]
