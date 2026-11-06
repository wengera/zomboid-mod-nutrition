"""Plan 31 Task 1 (the `Survive(control=...)` fork, `planner/control.py`): the ladder the default and the by-name
variant loader.

Pinned here: an unknown name raises `ControlError` at construction, never at the first tick; `control="ladder"` is
the default and adds no field to the decision line (the six decision goldens of `test_replay_decisions.py` pin the
ladder byte for byte; this file pins the line's shape against the variant contract); a variant package found by name
answers `assess(survive, frame)` with a Decision `_apply` sends, and keeps its state on `survive.control_state`. The
stubs live in this file (a `sys.modules` entry or a temporary package directory on the planner's `__path__`), never
importable from the planner in production."""
import contextlib
import importlib
import json
import sys
import types

import pytest

from agent.base import planner as planner_pkg
from agent.base.planner import control as C
from agent.base.planner.survive import Decision, Survive
from agent.base.pza1 import WalkTo

from .test_policies import Rig
from .test_survive import decisions, make


def stub_module(**names):
    mod = types.ModuleType("agent.base.planner.ctl_stub")
    for k, v in names.items():
        setattr(mod, k, v)
    return mod


def walk_stub(survive, frame):
    """A trivial control: a goal-branch walk from the frame's own position, counting its ticks on control_state."""
    survive.control_state["n"] = survive.control_state.get("n", 0) + 1
    frame["need"], frame["consume_refused"], frame["cooled"], frame["branches"] = None, None, None, {}
    return Decision("goal", None, WalkTo(frame["x"] + 1.0, frame["y"]), frame)


@pytest.fixture
def stub(monkeypatch):
    monkeypatch.setitem(sys.modules, "agent.base.planner.ctl_stub", stub_module(assess=walk_stub))
    return "ctl_stub"


def build(tmp_path, **kw):
    r = Rig(tmp_path)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, **kw)
    return r, sv


# ================================================================ the loader
def test_the_ladder_is_the_default_and_loads_no_function():
    assert C.CONTROLS == ("ladder",)
    assert C.load("ladder") is None


@pytest.mark.parametrize("name", ["nope", "a.b", "", "survive", "../x", None, 3])
def test_an_unknown_name_raises_control_error_at_construction(tmp_path, name):
    r = Rig(tmp_path)
    with pytest.raises(C.ControlError):
        Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, control=name)


def test_control_error_is_a_value_error():
    assert issubclass(C.ControlError, ValueError)


def test_the_stub_is_not_importable_from_the_planner_in_production(tmp_path):
    assert "agent.base.planner.ctl_stub" not in sys.modules
    r = Rig(tmp_path)
    with pytest.raises(C.ControlError):
        Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, control="ctl_stub")


def test_a_package_without_assess_is_a_control_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "agent.base.planner.ctl_stub", stub_module(assess="not callable"))
    with pytest.raises(C.ControlError, match="assess"):
        C.load("ctl_stub")
    monkeypatch.setitem(sys.modules, "agent.base.planner.ctl_stub", stub_module())
    with pytest.raises(C.ControlError, match="assess"):
        C.load("ctl_stub")


@contextlib.contextmanager
def disk_package(tmp_path, monkeypatch, name, source):
    """A package `name` written under `tmp_path` and put on the planner's `__path__`; on exit the module, the
    attribute the import set on the planner package and the path finder's cache entries are all gone."""
    pkg = tmp_path / name
    pkg.mkdir()
    (pkg / "__init__.py").write_text(source, encoding="utf-8")
    monkeypatch.setattr(planner_pkg, "__path__", [str(tmp_path)] + list(planner_pkg.__path__))
    monkeypatch.delitem(sys.modules, f"agent.base.planner.{name}", raising=False)
    importlib.invalidate_caches()
    try:
        yield
    finally:
        sys.modules.pop(f"agent.base.planner.{name}", None)
        if hasattr(planner_pkg, name):
            delattr(planner_pkg, name)
        for key in [k for k in sys.path_importer_cache if str(tmp_path) in k]:
            del sys.path_importer_cache[key]
        importlib.invalidate_caches()


def test_a_package_found_on_disk_by_name_loads(tmp_path, monkeypatch):
    with disk_package(tmp_path, monkeypatch, "ctl_disk", "def assess(survive, frame):\n    return None\n"):
        assert C.load("ctl_disk")(None, None) is None
    assert "agent.base.planner.ctl_disk" not in sys.modules and not hasattr(planner_pkg, "ctl_disk")


def test_a_variant_s_own_missing_import_propagates_never_an_unknown_name(tmp_path, monkeypatch):
    with disk_package(tmp_path, monkeypatch, "ctl_broken", "import not_a_real_module_zz\n"):
        with pytest.raises(ModuleNotFoundError, match="not_a_real_module_zz"):
            C.load("ctl_broken")


# ================================================================ the fork
def test_the_default_and_the_named_ladder_write_the_same_line(tmp_path):
    lines = []
    for sub, kw in (("a", {}), ("b", {"control": "ladder"})):
        d = tmp_path / sub
        d.mkdir()
        r, sv = build(d, **kw)
        r.frame()
        sv.tick(r.world, r.acts)
        (line,) = decisions(d)
        line.pop("wall")
        lines.append(json.dumps(line, sort_keys=True))
    assert lines[0] == lines[1]


def test_the_ladder_s_line_gains_no_control_field(tmp_path):
    r, sv = build(tmp_path)
    r.frame()
    sv.tick(r.world, r.acts)
    (line,) = decisions(tmp_path)
    assert "control" not in line and "control" not in line["inputs"]
    assert sv.control == "ladder" and sv.control_state == {}


def test_assess_of_the_ladder_is_the_ladder_body(tmp_path):
    r, sv = build(tmp_path)
    r.frame()
    inputs = sv._read(r.world, r.acts)
    d = sv.assess(inputs)
    assert isinstance(d, Decision) and set(d.inputs["branches"]) >= {"threat"}


def test_a_stub_control_answers_and_apply_sends_its_decision(tmp_path, stub):
    r, sv = build(tmp_path, control=stub)
    assert sv.control == "ctl_stub" and sv.control_state == {}
    r.frame(x=100.0, y=200.0)
    a = sv.tick(r.world, r.acts)
    assert a is not None and r.cmd() == ("walkTo", {"x": 101.0, "y": 200.0, "gait": "walk"})
    assert sv.control_state == {"n": 1} and sv.last_branch == "goal"
    (line,) = decisions(tmp_path)
    assert line["branch"] == "goal" and line["sent"] is True
    assert line["action"] == {"type": "walkTo", "args": {"x": 101.0, "y": 200.0, "gait": "walk"}}


def test_the_stub_line_keeps_the_decision_line_contract(tmp_path, stub):
    """The contract a variant keeps (scoping § 5): `inputs.x`/`inputs.y`, `branch`, and `inputs.branches`."""
    r, sv = build(tmp_path, control=stub)
    r.frame(x=100.0, y=200.0)
    sv.tick(r.world, r.acts)
    (line,) = decisions(tmp_path)
    assert (line["inputs"]["x"], line["inputs"]["y"]) == (100.0, 200.0)
    assert "branches" in line["inputs"] and "branch" in line


def flee_stub(survive, frame):
    """A threat-branch control: a flee leg with the reason on `inputs.branches.threat.flee`."""
    frame["need"], frame["consume_refused"], frame["cooled"] = None, None, None
    frame["branches"] = {"threat": {"flee": "health"}}
    return Decision("threat", None, WalkTo(frame["x"] - 5.0, frame["y"], "run"), frame)


def test_a_threat_branch_stub_keeps_the_fight_and_flee_contract_on_the_line(tmp_path, monkeypatch):
    """The contract `session.Fights` and the grades read: `branch == "threat"` on a fight tick, the flee's reason at
    `inputs.branches.threat.flee`, the position at `inputs.x`/`inputs.y`; and the fork adds no field of its own."""
    monkeypatch.setitem(sys.modules, "agent.base.planner.ctl_stub", stub_module(assess=flee_stub))
    r, sv = build(tmp_path, control="ctl_stub")
    r.frame(x=100.0, y=200.0)
    sv.tick(r.world, r.acts)
    (line,) = decisions(tmp_path)
    assert line["branch"] == "threat" and sv.last_branch == "threat"
    assert line["inputs"]["branches"]["threat"]["flee"] == "health"
    assert (line["inputs"]["x"], line["inputs"]["y"]) == (100.0, 200.0)
    assert line["action"] == {"type": "walkTo", "args": {"x": 95.0, "y": 200.0, "gait": "run"}}
    assert "control" not in line and "control" not in line["inputs"]


def test_the_ladder_body_is_never_run_under_a_variant(tmp_path, stub, monkeypatch):
    def boom(self, inputs):
        raise AssertionError("the ladder ran under a variant")
    monkeypatch.setattr(Survive, "_assess_ladder", boom)
    r, sv = build(tmp_path, control=stub)
    r.frame()
    assert sv.tick(r.world, r.acts) is not None
    assert sv.control_state == {"n": 1}
    other = tmp_path / "ladder"   # the control: the ladder does reach `_assess_ladder`
    other.mkdir()
    r2, ladder = build(other)
    r2.frame()
    with pytest.raises(AssertionError, match="ladder ran"):
        ladder.tick(r2.world, r2.acts)


def test_a_stub_control_s_state_persists_across_ticks_and_is_per_instance(tmp_path, stub):
    r, sv = build(tmp_path, control=stub)
    for _ in range(3):
        r.frame()
        r.advance(1.0)
        sv.tick(r.world, r.acts)
    assert sv.control_state == {"n": 3}
    d2 = tmp_path / "second"
    d2.mkdir()
    _, other = build(d2, control=stub)
    assert other.control_state == {}


def test_make_still_builds_the_default_ladder(tmp_path):
    r, sv = make(tmp_path)
    assert sv.control == "ladder" and sv._control_assess is None


# ================================================================ the prepare seam (Plan 31 Task 1 residual)
def test_the_ladder_and_a_package_without_prepare_have_none(stub):
    assert C.prepare_of("ladder") is None
    assert C.prepare_of(stub) is None


def test_a_prepare_that_is_not_callable_is_a_control_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "agent.base.planner.ctl_stub", stub_module(assess=walk_stub, prepare="no"))
    with pytest.raises(C.ControlError, match="prepare"):
        C.prepare_of("ctl_stub")


def test_a_package_with_prepare_is_called_once_with_the_instance_before_any_read(tmp_path, monkeypatch):
    seen = []

    def prepare(survive):
        seen.append(("prepare", survive, dict(survive.control_state), survive.ticks))
        survive.GOAL_CONTINUE = False   # an instance switch the first tick's read must already see
        survive.control_state["prepared"] = True

    def assess(survive, frame):
        seen.append(("assess", survive.GOAL_CONTINUE, survive.control_state["prepared"]))
        return walk_stub(survive, frame)

    real_read = Survive._read

    def read(self, world, actions):
        seen.append(("read", self.GOAL_CONTINUE))
        return real_read(self, world, actions)

    monkeypatch.setattr(Survive, "_read", read)
    monkeypatch.setitem(sys.modules, "agent.base.planner.ctl_stub", stub_module(assess=assess, prepare=prepare))
    r, sv = build(tmp_path, control="ctl_stub")
    assert seen == [("prepare", sv, {}, 0)]   # at construction, `control_state` an empty dict, no tick yet
    assert Survive.GOAL_CONTINUE is True and sv.GOAL_CONTINUE is False   # the instance's switch, never the class's
    for _ in range(2):
        r.frame()
        r.advance(1.0)
        sv.tick(r.world, r.acts)
    assert [s[0] for s in seen] == ["prepare", "read", "assess", "read", "assess"]
    assert seen[1] == ("read", False) and seen[2] == ("assess", False, True)   # the first read saw the switch off
    assert sum(1 for s in seen if s[0] == "prepare") == 1   # once, never per tick


def test_a_package_without_prepare_constructs_as_before(tmp_path, stub):
    r, sv = build(tmp_path, control=stub)
    assert sv.control_state == {} and sv.GOAL_CONTINUE is Survive.GOAL_CONTINUE


def test_a_prepare_error_surfaces_at_construction(tmp_path, monkeypatch):
    def prepare(survive):
        raise RuntimeError("prepare broke")
    monkeypatch.setitem(sys.modules, "agent.base.planner.ctl_stub", stub_module(assess=walk_stub, prepare=prepare))
    with pytest.raises(RuntimeError, match="prepare broke"):
        build(tmp_path, control="ctl_stub")
