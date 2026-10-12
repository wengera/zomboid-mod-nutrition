"""Tests for tools/fit_gut_satiety.py, the gut-satiety joint fit (Plan 11g Task 5).

The two-point grid: the tool returns the point with the lower summed relative miss and writes fit.json with one entry
per oracle; the same grid gives byte-identical output apart from the date; a patch reaches both hosts (the lupa kernel
host and the server path's) and never a tracked file; the registry's misses agree with test_satiety_meal_studies.py's
hard ratios on the shipped constants.
"""
import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import fit_gut_satiety as F  # noqa: E402

from kernel import gut_oracles as GO  # noqa: E402  (fit_gut_satiety puts testing/tests on sys.path)
from kernel import test_satiety_meal_studies as M  # noqa: E402

TWO_POINTS = {"params": {"FULL_WEIGHT": [0.55, 0.3]}, "refine": {"rounds": 0}}


def run_fit(spec, out):
    return F.fit(F.load_spec(spec), out, jobs=1)


def test_the_miss_is_the_relative_excess_beyond_the_tolerance():
    band = GO.Oracle("x", "g", lambda r: r, target=10.0, lo=9.0, hi=11.0, scale=10.0, kind="two-sided", row="S0")
    assert band.miss(10.0) == 0.0 and band.miss(9.0) == 0.0 and band.miss(11.0) == 0.0
    assert math.isclose(band.miss(12.0), 0.1) and math.isclose(band.miss(7.0), 0.2)
    one = GO.Oracle("y", "g", lambda r: r, target=61.0, lo=0.0, hi=None, scale=61.0, kind="one-sided", row="S0")
    assert one.miss(5.0) == 0.0 and math.isclose(one.miss(-61.0), 1.0)
    assert one.miss(None) == GO.NONE_MISS
    ratio = GO.ratio_oracle("z", "g", lambda r: r, 26.0, 1.5, "S0")
    assert (ratio.lo, ratio.hi) == (26.0 / 1.5, 39.0)
    neg = GO.ratio_oracle("w", "g", lambda r: r, -9.0, 1.5, "S0")
    assert (neg.lo, neg.hi) == (-13.5, -6.0) and math.isclose(neg.miss(6.0), 12.0 / 9.0)
    reading = GO.Oracle("v", "g", lambda r: r, target=0.0, kind="reading", row="S0")
    assert reading.miss(3.0) is None


def test_the_registry_agrees_with_the_meal_studies_hard_ratios():
    # on the shipped constants a meal-study oracle's miss is 0 exactly when hard_ratios' ratio is within its tolerance
    host = F.new_host()
    readings = GO.read_all(host)
    hr = M.hard_ratios(host)
    pairs = {"callahan_190": ("callahan0", M.TOL), "callahan_400": ("callahan1", M.TOL),
             "callahan_825": ("callahan2", M.TOL), "callahan_fasted_190": ("callahan_fasted0", M.TOL),
             "callahan_fasted_400": ("callahan_fasted1", M.TOL), "callahan_fasted_825": ("callahan_fasted2", M.TOL),
             "meal650": ("meal650", M.TOL), "rolls_soup": ("rolls_soup", M.TOL), "rolls_cw": ("rolls_cw", M.TOL),
             "rolls_cas": ("rolls_cas", M.TOL), "rolls_drop": ("rolls_drop", M.TOL),
             "marmonier_pc": ("marmonier_pc", 1.5), "marmonier_pf": ("marmonier_pf", 1.5)}
    by = {o.name: o for o in GO.ORACLES}
    for name, (key, tol) in pairs.items():
        miss = by[name].miss(by[name].pick(readings))
        assert (miss == 0.0) == (hr[key] <= tol + 1e-12), (name, miss, hr[key])


def test_a_patch_reaches_both_hosts_and_no_tracked_file():
    tracked = subprocess.run(["git", "status", "--porcelain", "--", "mod"], cwd=F.REPO, capture_output=True,
                             text=True).stdout
    base = F.evaluate({})
    moved = F.evaluate({"FULL_WEIGHT": 0.3})
    assert base["readings"]["rolls_1999"] != moved["readings"]["rolls_1999"]   # the kernel host is patched
    assert base["readings"]["karl"]["bal"] != moved["readings"]["karl"]["bal"]       # the server path is patched
    again = F.evaluate({})
    assert again["readings"]["karl"]["bal"] == base["readings"]["karl"]["bal"]       # and the patch is undone
    assert subprocess.run(["git", "status", "--porcelain", "--", "mod"], cwd=F.REPO, capture_output=True,
                          text=True).stdout == tracked


def test_a_two_point_grid_returns_the_point_with_the_lower_summed_miss():
    with tempfile.TemporaryDirectory() as out:
        chosen = run_fit(TWO_POINTS, out)
        with open(os.path.join(out, "fit.json"), encoding="utf-8") as fh:
            fit = json.load(fh)
    cands = fit["candidates"]
    assert [c["params"]["FULL_WEIGHT"] for c in cands] == [0.55, 0.3]
    hard = [o.name for o in GO.ORACLES if o.kind != "reading"]
    for c in cands:
        assert sorted(c["oracles"]) == sorted(o.name for o in GO.ORACLES)            # one entry per oracle
        assert math.isclose(c["loss"], sum(c["oracles"][n]["miss"] for n in hard))
        assert all(c["oracles"][o.name]["miss"] is None for o in GO.ORACLES if o.kind == "reading")
    assert cands[0]["loss"] != cands[1]["loss"]
    best = min(cands, key=lambda c: c["loss"])
    assert fit["chosen"]["params"] == best["params"] == chosen["params"]
    assert fit["chosen"]["loss"] == best["loss"]
    assert fit["grid"] == TWO_POINTS
    assert len(fit["head"]) == 40 and fit["date"]


def test_the_same_grid_gives_byte_identical_output_but_the_date():
    texts = []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as out:
            run_fit({"params": {"FULL_WEIGHT": [0.55, 0.5]}, "refine": {"rounds": 1, "factor": 1.1,
                                                                       "params": ["FULL_WEIGHT"]}}, out)
            with open(os.path.join(out, "fit.json"), encoding="utf-8") as fh:
                texts.append(fh.read())
    a, b = (json.loads(t) for t in texts)
    a.pop("date"), b.pop("date")
    assert a == b
    strip = [t.replace(json.loads(t)["date"], "") for t in texts]
    assert strip[0] == strip[1]
    assert any(c["phase"] == "refine" for c in a["candidates"])


def test_stage_a_exits_with_a_clear_message_until_its_constants_exist():
    with tempfile.TemporaryDirectory() as out:
        p = subprocess.run([sys.executable, os.path.join(HERE, "..", "fit_gut_satiety.py"), "--out", out,
                            "--stage", "A"], capture_output=True, text=True)
    assert p.returncode == 2, p
    assert "stage A" in p.stderr and "A_HALF_LIFE_H" in p.stderr, p.stderr


def test_an_unknown_constant_is_refused():
    try:
        F.load_spec({"params": {"NO_SUCH_CONSTANT": [1.0]}})
        F.evaluate({"NO_SUCH_CONSTANT": 1.0})
    except ValueError as e:
        assert "NO_SUCH_CONSTANT" in str(e)
    else:
        raise AssertionError("an unknown constant was accepted")
