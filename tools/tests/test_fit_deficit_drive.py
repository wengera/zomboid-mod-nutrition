"""Tests for tools/fit_deficit_drive.py, the deficit drive's fit (Plan 11g Task 7), and its registry
testing/tests/kernel/deficit_oracles.py.

The objective ranks a feasible point by its smallest scored margin and an infeasible one below it; the search skips a
falling bypass ramp, keeps every value inside its bound and never scores a point twice; the tie rule prefers the point
nearer the shipped constants; a patch reaches the kernel host and the server path's and never a tracked file; the
registry's bands are the tests' own.
"""
import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import fit_deficit_drive as F  # noqa: E402

from kernel import deficit_oracles as DO  # noqa: E402  (fit_gut_satiety puts testing/tests on sys.path)
from kernel import test_replay_live_energy as E  # noqa: E402
from kernel import test_satiety_meal_studies as M  # noqa: E402

LO, HI, SPAN, FLOOR = "deficit.EX_BYPASS_LO", "deficit.EX_BYPASS_HI", "deficit.BALANCE_SPAN_KCAL", "deficit.DEFICIT_FLOOR"


def readings(dfc=30.0, bal=-55.0, r2=1.2, r3=1.0, dmm=0.5, rise=0.09, steady=1.0, six=1.0, mm=5.0):
    karl = {a: {"bal": bal, "dfc": dfc} for a in DO.KARL_ALTS}
    return {"fast": {"r2": r2, "r3": r3}, "karl": karl,
            "king": {"bout": 73, "rise": rise, "risemm": rise * 260.0, "dmm": dmm},
            "steady": {"ratios": [steady] * 3, "es": [steady, steady]}, "six": six, "s1255": {"es": 1.09, "mm": mm},
            "whybrow": [[53, 0.30, 0.04], [27, 0.30, 0.04]], "emech": [0.7, 0.7]}


def test_the_margin_is_the_distance_inside_over_the_half_width():
    o = DO.Oracle("x", "g", lambda r: r, lo=1.0, hi=3.0)
    assert o.scale == 1.0 and o.margin(2.0) == 1.0 and o.margin(1.0) == 0.0 and o.margin(3.5) == -0.5
    one = DO.Oracle("y", "g", lambda r: r, hi=10.0, scale=10.0)
    assert one.margin(5.0) == 0.5 and one.margin(12.0) == -0.2
    assert one.margin(None) == -math.inf and one.margin(math.nan) == -math.inf


def test_the_worst_twin_k_alternative_sets_karl_def():
    r = readings()
    r["karl"]["loadwalk"]["dfc"] = 18.0          # nearest the band's floor 17.33
    r["karl"]["run10"]["dfc"] = 38.0             # 1.0 from the ceiling, farther than loadwalk's 0.67
    assert DO.BY_NAME["karl_def"].pick(r) == 18.0
    assert DO.margins(r)["karl_def"] == DO.BY_NAME["karl_def"].margin(18.0)


def test_a_feasible_point_ranks_by_its_smallest_scored_margin_and_a_broken_constraint_ranks_below():
    good = F.score(readings())
    thin = F.score(readings(dfc=18.0))
    assert good["feasible"] and thin["feasible"] and good["loss"] < thin["loss"]
    assert math.isclose(thin["loss"], -thin["smallest"]) and math.isclose(thin["smallest"], DO.BY_NAME["karl_def"].margin(18.0))
    bal_out = F.score(readings(bal=-40.0))       # Karl BAL is now a constraint: outside -64..-46 it is infeasible
    assert not bal_out["feasible"] and bal_out["shortfall"] > 0 and bal_out["loss"] > thin["loss"]
    six_out = F.score(readings(six=1.4))
    assert not six_out["feasible"]
    # BAL inside its band never enters the objective: two BAL readings inside score alike
    assert F.score(readings(bal=-50.0))["loss"] == F.score(readings(bal=-60.0))["loss"]


def test_king_reads_the_distance_under_its_bound_and_fails_a_flat_restriction():
    r = readings(dmm=1.0, rise=0.09)             # bound min(3.3, 0.25 x 23.4) = 3.3
    assert math.isclose(DO.margins(r)["king"], (3.3 - 1.0) / 3.3)
    assert DO.margins(readings(rise=0.01))["king"] == -math.inf


def test_the_spec_is_bounded_and_the_ramp_must_rise():
    for spec in ({LO: [0.28]}, {SPAN: [0]}, {FLOOR: [-0.01]}, {HI: [1.2]}):
        try:
            F.load_spec({"params": spec})
        except ValueError as e:
            assert next(iter(spec)) in str(e) and "bound" in str(e)
        else:
            raise AssertionError(spec)
    assert F.load_spec({"params": {LO: [0.282], FLOOR: [0]}})
    assert not F._valid({LO: 0.5, HI: 0.4}) and F._valid({LO: 0.3, HI: 0.4})


def test_the_search_skips_a_falling_ramp_stays_in_bounds_and_scores_nothing_twice():
    seen = []

    def fake(args):
        patch, fixed = args
        seen.append(dict(patch))
        # best at the largest span and the floor 0: the refinement walks the span up and tries the floor's zero step
        return {"params": dict(patch), "loss": -patch[SPAN] / 1e4 + patch[FLOOR], "feasible": True, "smallest": 0.0}
    saved = F._worker
    F._worker = fake
    try:
        spec = F.load_spec({"params": {SPAN: [3000, 4000], FLOOR: [0], LO: [0.282, 0.6], HI: [0.5, 0.7]},
                            "refine": {"rounds": 2, "factor": 1.1}})
        cands, chosen, _, _ = F.search(spec, fixed={}, start={SPAN: 3100, FLOOR: 0.02, LO: 0.282, HI: 0.575})
    finally:
        F._worker = saved
    assert all(F._valid(p) for p in seen)                                    # no LO 0.6 with HI 0.5
    assert len(seen) == len({tuple(sorted(p.items())) for p in seen})
    assert all(F._inside(k, v) for p in seen for k, v in p.items())
    assert any(p[FLOOR] == F.ZERO_STEP for p in seen)                         # the zero is stepped off
    assert chosen["params"][SPAN] > 4000 and chosen["params"][FLOOR] == 0


def test_the_tie_rule_prefers_the_point_nearer_the_start():
    start = {SPAN: 3100.0, FLOOR: 0.02}
    far = {"params": {SPAN: 6000.0, FLOOR: 0.02}, "loss": -0.5000}
    near = {"params": {SPAN: 3200.0, FLOOR: 0.02}, "loss": -0.4995}
    worse = {"params": {SPAN: 3100.0, FLOOR: 0.02}, "loss": -0.4}
    assert F.choose([far, near, worse], start) is near
    assert F.choose([far, worse], start) is far


def test_the_registry_bands_are_the_tests_bands():
    by = DO.BY_NAME
    assert (by["karl_def"].lo, by["karl_def"].hi) == (26.0 / 1.5, 39.0)
    assert E.karl_pass(-55.0, by["karl_def"].lo + 1e-9) == (True, True) and E.karl_pass(-55.0, 39.0 + 1e-9)[1] is False
    assert (by["karl_bal"].lo, by["karl_bal"].hi) == (-64.0, -46.0)
    assert math.isclose(by["fast_r2"].lo, 1.20 / M.TOL) and math.isclose(by["fast_r3"].hi, M.TOL)
    assert by["steady"].hi == M.STEADY_TOL and (by["six"].lo, by["six"].hi) == (0.9, 1.3) and by["s1255"].hi == 10.0
    assert {o.role for o in DO.ORACLES} == {"scored", "constraint", "fixed"}
    assert [o.name for o in DO.ORACLES if o.role == "scored"] == ["fast_r2", "fast_r3", "karl_def", "king"]
    assert {o.group for o in DO.ORACLES if o.role == "fixed"} == set(DO.FIXED_GROUPS)


def test_a_patch_reaches_both_hosts_and_no_tracked_file():
    tracked = subprocess.run(["git", "status", "--porcelain", "--", "mod"], cwd=F.FG.REPO, capture_output=True,
                             text=True).stdout
    base = F.read_groups({}, ("s1255", "fast"))
    moved = F.read_groups({FLOOR: 0.5, SPAN: 6000.0}, ("s1255", "fast"))
    assert base["s1255"]["mm"] != moved["s1255"]["mm"]               # the kernel host (hungerTarget's floor) and the
    assert base["fast"]["r2"] != moved["fast"]["r2"]                 # server path (the span) are both patched
    again = F.read_groups({}, ("fast",))
    assert again["fast"]["r2"] == base["fast"]["r2"]                 # and the patch is undone
    assert subprocess.run(["git", "status", "--porcelain", "--", "mod"], cwd=F.FG.REPO, capture_output=True,
                          text=True).stdout == tracked


def test_a_two_point_grid_writes_the_full_and_the_compact_fit():
    saved = F._worker

    def fake(args):
        patch, fixed = args
        r = F.score(readings(dfc=20.0 if patch[SPAN] == 4000 else 30.0))
        r["params"] = dict(patch)
        return r
    F._worker = fake
    try:
        with tempfile.TemporaryDirectory() as out:
            chosen = F.fit(F.load_spec({"params": {SPAN: [3100, 4000]}, "refine": {"rounds": 0}}), out)
            with open(os.path.join(out, "fit.json"), encoding="utf-8") as fh:
                doc = json.load(fh)
            with open(os.path.join(out, "fit-compact.json"), encoding="utf-8") as fh:
                comp = json.load(fh)
    finally:
        F._worker = saved
    assert chosen["params"] == {SPAN: 3100} and doc["chosen"]["params"] == {SPAN: 3100}
    assert [c["params"][SPAN] for c in doc["candidates"]] == [3100, 4000]
    assert sorted(doc["candidates"][0]["margins"]) == sorted(o.name for o in DO.ORACLES)
    assert doc["fixed"]["start"]["whybrow"] == doc["fixed"]["chosen"]["whybrow"]   # no fitted constant moves L
    assert comp["candidates"] == 2 and comp["chosen"] == doc["chosen"] and len(comp["source_sha256"]) == 64
    assert [p["value"] for p in comp["profile"][SPAN]] == [3100, 4000]
