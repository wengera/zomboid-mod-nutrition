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
    r = F.evaluate({"MEAL_HALF_LIFE_H": 5.0})                # neither arm back inside 900 min (1.5 before the Task 6 fit)
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
    for spec in ({"FULL_WEIGHT": [1.5]}, {"FULL_WEIGHT": [0]}, {"LIQUID_WEIGHT": [2]}, {"MEAL_REQ": [-1.0]}, {"MEAL_REQ": [0]}):
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
    for name in ("tieken_liquid_4h", "tieken_solid_below_liquid"):                       # readings (ruling T6c-2)
        assert r["oracles"][name] == {"value": None, "miss": None}, name
    assert r["oracles"]["diekmann_after_tieken"]["miss"] == GO.NONE_MISS
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


def test_tieken_is_read_only_and_reports_its_distance_outside_the_band():
    # ruling T6c-2: Tieken's three entries are reading-kind, never in the loss, with their band kept for the report
    by = {o.name: o for o in GO.ORACLES}
    for name in ("tieken_liquid_4h", "tieken_solid_4h", "tieken_solid_below_liquid"):
        o = by[name]
        assert o.kind == "reading" and o.row == "S1833" and o.miss(0.5) is None, name
        assert name in GO.NAMED, name
    o = by["tieken_liquid_4h"]
    assert o.outside(0.1) == 0 and abs(o.outside(-0.046) - (0.04 + 0.046) / 0.14) < 1e-12
    r = F.evaluate({})
    assert all(r["oracles"][n]["miss"] is None for n in ("tieken_liquid_4h", "tieken_solid_4h",
                                                          "tieken_solid_below_liquid"))
    assert abs(r["loss"] - sum(v["miss"] for v in r["oracles"].values() if v["miss"] is not None)) < 1e-12


def test_s1233s_volume_slope_is_scored_two_sided_at_one_and_a_half_times():
    # ruling T6c-3: r300 - r600 against (5263 - 4703) / 4323 = 0.1295, the band [0.1295 / 1.5, 0.1295 x 1.5]
    o = {o.name: o for o in GO.ORACLES}["rolls98_slope"]
    s = (5263.0 - 4703.0) / 4323.0
    assert o.kind == "two-sided" and o.row == "S1233" and o.tol == "1.5x"
    assert abs(o.target - s) < 1e-12 and abs(o.lo - s / 1.5) < 1e-12 and abs(o.hi - s * 1.5) < 1e-12
    assert o.miss(o.pick({"rolls_1998": [0.73, 0.68, 0.60]})) == 0.0
    assert o.miss(o.pick({"rolls_1998": [0.69, 0.689, 0.688]})) > 0                  # flat: below the band
    assert o.miss(o.pick({"rolls_1998": [0.9, 0.7, 0.6]})) > 0                       # too steep: above it


def test_liquid_weight_is_fitted_in_zero_to_one():
    # ruling T6c-5: LIQUID_WEIGHT is a fitted constant (a default parameter) in (0, 1], a weight on drunk liquid's mass;
    # two rows set it (S1231's null above, S1233's slope below), not the bound
    assert "LIQUID_WEIGHT" in F.DEFAULT_PARAMS and F.BOUNDS["LIQUID_WEIGHT"] == (0, 1)
    assert F.load_spec({"params": {"LIQUID_WEIGHT": [0.19, 0.5, 1.0]}})
    for bad in (1.01, 0.0):
        try:
            F.load_spec({"params": {"LIQUID_WEIGHT": [bad]}})
        except ValueError as e:
            assert "LIQUID_WEIGHT" in str(e) and "bound" in str(e)
        else:
            raise AssertionError("%r was accepted" % bad)


def test_s1231s_null_for_water_drunk_alongside_is_scored_two_sided():
    # ruling T6c-5: S1231's casserole with its water drunk against the casserole alone, 1657 - 1639 = +18 kJ in the
    # study, within +/- 148 kJ (the arms' SE, a DESIGN CHOICE) either way; the miss over the same 148 kJ
    o = {o.name: o for o in GO.ORACLES}["rolls_cw_minus_cas"]
    assert o.kind == "two-sided" and o.row == "S1231" and o.group == "rolls_1999"
    assert o.target == 18.0 and o.lo == 18.0 - 148.0 and o.hi == 18.0 + 148.0 and o.scale == 148.0
    assert o.pick({"rolls_1999": {"soup": 1209.0, "cw": 1657.0, "cas": 1639.0}}) == 18.0
    assert o.miss(o.pick({"rolls_1999": {"soup": 1200.0, "cw": 1700.0, "cas": 1788.0}})) == 0.0     # -88 kJ: inside
    assert abs(o.miss(-278.0) - 1.0) < 1e-12                     # 148 kJ below the band: a miss of 1
    assert abs(o.miss(314.0) - 1.0) < 1e-12                      # 148 kJ above it
    # it is in the loss: the shipped point scores it
    r = F.evaluate({})
    assert r["oracles"]["rolls_cw_minus_cas"]["miss"] == 0.0
    # water drunk at full weight lowers the casserole-with-water lunch far past the band (the null S1231 reports)
    assert F.evaluate({"LIQUID_WEIGHT": 1.0})["oracles"]["rolls_cw_minus_cas"]["miss"] > 0


def _compact_pair(tmp):
    run_fit(TWO_POINTS, tmp)
    src = os.path.join(tmp, "fit.json")
    out = os.path.join(tmp, "c")
    F.write_compact(src, out)
    return src, os.path.join(out, "fit-compact.json")


def test_the_compact_artifact_is_deterministic_and_hashed_to_its_source():
    import hashlib
    with tempfile.TemporaryDirectory() as tmp:
        src, comp = _compact_pair(tmp)
        first = open(comp, "rb").read()
        F.write_compact(src, os.path.join(tmp, "c"))
        assert open(comp, "rb").read() == first
        doc = json.loads(first)
        raw = open(src, "rb").read()
        assert doc["source_sha256"] == hashlib.sha256(raw).hexdigest() and doc["source_bytes"] == len(raw)
        assert os.path.exists(os.path.join(tmp, "fit-compact.json")) is False


def test_the_compact_chosen_is_the_full_chosen_and_the_profile_minimum_is_its_loss():
    with tempfile.TemporaryDirectory() as tmp:
        src, comp = _compact_pair(tmp)
        full = json.load(open(src))
        doc = json.load(open(comp))
        assert doc["chosen"] == full["chosen"] and doc["candidates"] == len(full["candidates"])
        assert doc["spec"] == full["grid"] and doc["head"] == full["head"]
        for name, rows in doc["profile"].items():
            assert min(r["best_loss"] for r in rows) == full["chosen"]["loss"]
            assert [r["value"] for r in rows] == sorted(r["value"] for r in rows)
        assert [r["value"] for r in doc["profile"]["FULL_WEIGHT"]] == [0.3, 0.55]


def test_a_fit_run_writes_the_compact_file_beside_fit_json():
    with tempfile.TemporaryDirectory() as tmp:
        spec = os.path.join(tmp, "g.json")
        json.dump(TWO_POINTS, open(spec, "w"))
        assert F.main(["--grid", spec, "--out", os.path.join(tmp, "o")]) == 0
        assert os.path.exists(os.path.join(tmp, "o", "fit-compact.json"))
        assert F.main(["--compact", os.path.join(tmp, "o", "fit.json"), "--out", os.path.join(tmp, "p")]) == 0
        assert open(os.path.join(tmp, "p", "fit-compact.json"), "rb").read() == \
            open(os.path.join(tmp, "o", "fit-compact.json"), "rb").read()



def test_the_refinement_applies_both_bounds():
    # Plan 11g close (tools/fitlib.py): a refined value is clamped to the inclusive high bound, and one at or under the
    # exclusive low bound is skipped, never scored
    assert F._admit("FULL_WEIGHT", 1.3, {}) == 1 and F._admit("LIQUID_WEIGHT", 0.4, {}) == 0.4
    assert F._admit("FULL_WEIGHT", 0.0, {}) is None and F._admit("MEAL_REQ", -1.0, {}) is None
