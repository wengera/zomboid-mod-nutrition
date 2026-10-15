"""Offline tests of testing/experiments/x43b_strength_lib.py (Plan 13 Task 22, run x434): x43_strength_lib.py's tests of
the Task 22 session re-run on the copy, and the copy's two changes: a trait list answered as {} (the harness's empty
list) reads as the empty list, so a close that writes native 5 grades its band, and PLACE_MIN 8."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))
sys.path.insert(0, HERE)

import pytest                         # noqa: E402

import test_x43_strength_lib as T     # noqa: E402
import x43b_strength_lib as LB        # noqa: E402


@pytest.fixture(scope="module")
def kern():
    return LB.Kernel(T.SHARED)


@pytest.fixture()
def lib_b(monkeypatch):
    monkeypatch.setattr(T, "L", LB)
    orig = T.World.stats

    def stats(self, side):
        out = orig(self, side)
        if out.get("traitList") == []:
            out["traitList"] = {}                     # the harness's empty list
        return out
    monkeypatch.setattr(T.World, "stats", stats)
    return LB


def test_the_copy_changes():
    assert LB.PLACE_MIN == 8.0 and LB.LIB_FILE == "x43b_strength_lib.py"
    assert LB.traits_of({"traitList": {}}) == [] and LB.traits_of({"traitList": None}) is None
    assert LB.traits_of({"traitList": ["Strong"]}) == ["strong"]


def test_t22_flow_on_the_copy_with_empty_lists(kern, lib_b):
    v, o = T.run_session(kern, "22", {"growth": True}, hour=6.0)
    assert set(v.values()) == {"as_predicted"}, (v, {k: o["verdicts"][k]["observed"].get("why") for k in v})
    natives = [o["verdicts"][f"22_level{k}"]["observed"]["want_native"] for k in (1, 2, 3)]
    assert 5 in natives                                # a close at native 5 graded on an empty list


def test_t22_defects_on_the_copy(kern, lib_b):
    v, _o = T.run_session(kern, "22", {"growth": True, "drift": True}, hour=6.0)
    assert v["22_close1"] == "falsified"
    v, _o = T.run_session(kern, "22", {"growth": True, "no_band": True}, hour=6.0)
    assert "falsified" in {v[f"22_level{k}"] for k in (1, 2, 3)}


def test_x434_imports_the_copy():
    with open(os.path.join(T.REPO, "testing", "experiments", "x434_growth.py"), encoding="utf-8") as fh:
        text = fh.read()
    assert "import x43b_strength_lib as L" in text and 'PREFIX = "x434"' in text
