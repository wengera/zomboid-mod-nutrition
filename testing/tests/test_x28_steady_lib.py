"""x28_steady_lib (Plan 11f Task 5r): finding F-T5-2 fixed. x27_energy_lib's run_phase passed phase= into
Timeline.mark(phase, ...), so a budget stop or a phase error raised a TypeError that escaped run_phase and skipped the
ring read-back (R), the departure flush (D) and Z (x273). These tests show the x28 copy's budget and error paths reach
R, D and Z, and pin the replay's drink events read off the ring's fluids.autoDrop. Pure Python: no game."""
import os
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                          # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x28_steady_lib as L   # noqa: E402
from pzt.session import Timeline   # noqa: E402


def bare(lib, tmp_path):
    """A Session with no boot: only what run_phase and body touch."""
    S = object.__new__(lib.Session)
    S.out = {"phase_walls": {}, "phase_errors": {}, "notes": [], "phases": {}}
    S.tl, S.t0, S.cur = Timeline(), time.time(), "pre"
    S.path = str(tmp_path / "doc.json")
    S.server, S.clients = None, {}
    return S


def wire(S, scenario):
    calls = []
    for name in ("S", "H", "W", "R", "D", "Z"):
        setattr(S, "phase_" + name, (lambda n: (lambda: calls.append(n)))(name))

    def x(_S):
        calls.append("X")
        scenario()
    S.scenario = x
    return calls


def test_a_budget_stop_reaches_the_read_back_and_the_flush(tmp_path):
    S = bare(L, tmp_path)

    def over():
        raise L.Budget("wall past the budget")
    calls = wire(S, over)
    S.body()
    assert calls == ["S", "H", "W", "X", "R", "D", "Z"]
    assert S.out["budget_stop"]["phase"] == "X"
    assert any(it["phase"] == "budget_stop" and it.get("stopped_phase") == "X" for it in S.tl.items)
    assert os.path.isfile(S.path)


def test_a_phase_error_reaches_the_read_back_and_the_flush(tmp_path):
    S = bare(L, tmp_path)

    def boom():
        raise RuntimeError("User admin not found")
    calls = wire(S, boom)
    S.body()
    assert calls == ["S", "H", "W", "X", "R", "D", "Z"]
    assert "RuntimeError" in S.out["phase_errors"]["X"]["error"]
    assert any(it["phase"] == "error" and it.get("failed_phase") == "X" for it in S.tl.items)


def test_the_frozen_x27_lib_no_longer_shows_the_defect_this_file_fixes(tmp_path):
    """Timeline.mark takes its phase positionally only, so the frozen x27 lib's mark(..., phase=...) lands the
    keyword as a field: run_phase records the budget stop instead of raising a duplicate-argument TypeError."""
    import x27_energy_lib as L27
    S = bare(L27, tmp_path)

    def over():
        raise L27.Budget("wall past the budget")
    S.run_phase("X", over)
    assert S.out["budget_stop"]["phase"] == "X" and S.tl.items[-1]["phase"] == "X"


def test_the_drink_events_are_the_rings_autodrop_rows():
    rows = [{"s": 1, "age": 1.0, "fluids.autoDrop": 0}, {"s": 2, "age": 1.02, "fluids.autoDrop": 0.125},
            {"s": 3, "age": 1.03}, {"s": 4, "age": 1.05, "fluids.autoDrop": 0.0625}]
    ev = L.autodrop_events(rows)
    assert [(e["s"], e["kind"], e["vec"]["water"]) for e in ev] == [(2, "drink", 250.0), (4, "drink", 125.0)]


def test_the_calendar_and_the_schedule():
    assert L.at(0, 7.0) == 0.0 and L.day_of(L.at(5, 0.5)) == 5 and L.day_of(L.at(5, 23.99)) == 5
    kinds = {}
    for age, kind, label in L.SCHEDULE:
        kinds.setdefault(kind, []).append(label)
    assert kinds["maint"] == ["D0_13", "D0_20", "D1_08", "D1_13", "D1_20"]
    assert len(kinds["request"]) == 12 and kinds["request"][0] == "D2_08" and kinds["request"][-1] == "D5_20"
    assert all(a <= b for a, b in zip([x[0] for x in L.SCHEDULE], [x[0] for x in L.SCHEDULE][1:]))
