"""Tests for tools/fit_gut_satiety.py, the gut-satiety joint fit (Plan 11g Task 5).

The two-point grid: the tool returns the point with the lower summed relative miss and writes fit.json with one entry
per oracle; the same grid gives byte-identical output apart from the date; a patch reaches both hosts (the lupa kernel
host and the server path's) and never a tracked file; the registry reads its meal-study figures from test_satiety_meal_studies.py.
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


def test_a_nan_or_infinite_reading_misses_and_a_reading_that_never_returns_fails_a_lower_bound():
    one = GO.Oracle("y", "g", lambda r: r, target=61.0, lo=0.0, scale=61.0, kind="one-sided", row="S0")
    assert one.miss(math.nan) == GO.NONE_MISS and one.miss(math.inf) == GO.NONE_MISS
    assert one.miss(-math.inf) == GO.NONE_MISS and one.miss(None) == GO.NONE_MISS
    late = GO.Oracle("z", "g", lambda r: r, target=361.0, lo=361.0, scale=360.0, kind="one-sided", row="S0",
                     none_is="inf")
    assert late.miss(None) == 0.0 and late.miss(400.0) == 0.0 and late.miss(300.0) > 0
    assert late.miss(math.nan) == GO.NONE_MISS and late.miss(-math.inf) == GO.NONE_MISS


def test_the_later_minus_earlier_pickers_pass_a_late_none_and_miss_an_early_one():
    f = GO._later_minus_earlier
    assert f(None, 100) == math.inf and f(300, 100) == 200
    assert f(100, None) == -math.inf and f(None, None) == -math.inf
    by = {o.name: o for o in GO.ORACLES}
    for name in ("diekmann_after_tieken", "melanson_f_minus_c"):
        assert by[name].none_is == "inf"
        assert by[name].miss(f(None, 100)) == 0.0 and by[name].miss(f(100, None)) == GO.NONE_MISS
        assert by[name].miss(f(None, None)) == GO.NONE_MISS


def test_an_arm_that_never_returns_scores_zero_on_the_diekmann_lower_bounds():
    r = F.evaluate({"G_HALF_LIFE_H": 5.0})                # neither arm back inside 900 min (1.5 before the Task 6 fit)
    by = {o.name: o for o in GO.ORACLES}
    assert r["readings"]["diekmann"]["hf"]["back"] is None and r["readings"]["diekmann"]["lf"]["back"] is None
    for name in ("diekmann_hf_6h", "diekmann_lf_6h"):
        assert by[name].none_is == "inf" and r["oracles"][name]["miss"] == 0.0, name


def test_an_oracle_needs_a_positive_scale_unless_it_is_a_reading():
    try:
        GO.Oracle("bad", "g", lambda r: r, target=0.0, lo=0.0, kind="one-sided", row="S0")
    except AssertionError as e:
        assert "bad" in str(e)
    else:
        raise AssertionError("a zero scale was accepted")
    assert GO.Oracle("ok", "g", lambda r: r, target=0.0, kind="reading", row="S0").scale is None


def test_a_bounded_constant_is_refused_out_of_bounds_and_the_refinement_stops_at_the_bound():
    for spec in ({"FULL_WEIGHT": [1.5]}, {"FULL_WEIGHT": [0]}, {"LIQUID_WEIGHT": [2]}, {"G_REQ": [-1.0]}, {"G_REQ": [0]}):
        try:
            F.load_spec({"params": spec})
        except ValueError as e:
            assert next(iter(spec)) in str(e) and "bound" in str(e)
        else:
            raise AssertionError(spec)
    assert F.load_spec({"params": {"FULL_WEIGHT": [1]}})
    seen = []

    def fake(patch):
        seen.append(dict(patch))
        return {"params": dict(patch), "loss": -patch["FULL_WEIGHT"], "oracles": {}}
    saved = F._eval_worker
    F._eval_worker = fake
    try:
        F.search(F.load_spec({"params": {"FULL_WEIGHT": [0.9]}, "refine": {"rounds": 3, "factor": 1.25}}))
    finally:
        F._eval_worker = saved
    assert max(p["FULL_WEIGHT"] for p in seen) == 1.0
    assert len(seen) == len({tuple(sorted(p.items())) for p in seen})        # nothing evaluated twice (or at the point itself)


def test_a_group_that_raises_scores_its_oracles_as_misses_and_the_rest_still_run():
    saved = GO.GROUPS["moore"], GO.GROUPS["tieken"]

    def boom(h):
        raise RuntimeError("the kernel rejected the candidate")
    GO.GROUPS["moore"] = boom
    GO.GROUPS["tieken"] = boom
    try:
        r = F.evaluate({})
    finally:
        GO.GROUPS["moore"], GO.GROUPS["tieken"] = saved
    assert "RuntimeError" in r["readings"]["moore"] and "the kernel rejected" in r["readings"]["moore"]
    assert r["oracles"]["moore_half_emptying"] == {"value": None, "miss": None}              # a reading: reported only
    for name in ("tieken_liquid_4h", "tieken_solid_below_liquid", "diekmann_after_tieken"):
        assert r["oracles"][name]["miss"] == GO.NONE_MISS, name
    assert r["oracles"]["meal650"]["miss"] is not None and r["oracles"]["meal650"]["value"] is not None


def test_the_two_hard_bounds_join_the_registry_with_their_figures_from_the_meal_studies():
    by = {o.name: o for o in GO.ORACLES}
    b = by["breakfast400_held"]
    assert (b.kind, b.lo, b.scale) == ("one-sided", M.BREAKFAST_HOLD_MIN, M.BREAKFAST_HOLD_MIN) and b.row == ""
    assert b.miss(b.pick({"breakfast400": [(10, 180), (10, 90)]})) == 0.5
    o = by["rolls98_ordering"]
    assert o.kind == "one-sided" and o.lo == 0.0
    assert o.miss(o.pick({"rolls_1998": [0.7, 0.71, 0.6]})) > 0 and o.miss(o.pick({"rolls_1998": [0.72, 0.71, 0.6]})) == 0.0
    # each meal-study figure is the very object the tests read
    assert GO.CALLAHAN is M.CALLAHAN_MIN and GO.ROLLS_1999 is M.ROLLS_1999 and GO.ROLLS_1998 is M.ROLLS_1998
    assert GO.MARMONIER_DIFF is M.MARMONIER_DIFF and GO.MEAL650 is M.MEAL650_MIN and GO.S1222 is M.S1222_BAND
    shipped = F.evaluate({})["oracles"]
    assert shipped["breakfast400_held"]["miss"] == 0.0 and shipped["rolls98_ordering"]["miss"] == 0.0
