"""tools/calibrate_drain_curve.py (Plan 17 Task 1): the curve's opening slope and its solver, and the committed
calibration artifact in sync with a recomputation off the replay host."""
import json
import math
import os
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools.calibrate_drain_curve import solve_a, opening_slope  # noqa: E402
import tools.calibrate_drain_curve as C  # noqa: E402


# ---- the pure part (the plan's cases, verbatim) ---------------------------------------------------------------------

def test_opening_slope_is_a_over_log():
    assert abs(opening_slope(0.24, 1800.0) - 0.24 / __import__("math").log(1 + 0.24 * 1800.0)) < 1e-12


def test_solve_a_meets_the_target_slope():
    a = solve_a(target=3.564 / 100.0, span=1800.0)
    assert abs(opening_slope(a, 1800.0) - 3.564 / 100.0) < 1e-9


def test_solve_a_gives_the_line_when_the_target_is_at_or_under_the_mean_slope():
    assert solve_a(target=1.0 / 1800.0, span=1800.0) == 0.0
    assert solve_a(target=0.5 / 1800.0, span=1800.0) == 0.0


# ---- the pure part, more ---------------------------------------------------------------------------------------------

def test_solve_a_on_the_severity_clock():
    for target in (1.5, 16.4, 81.7, 1000.0):
        a = solve_a(target, 1.0)
        assert a > 0 and abs(opening_slope(a, 1.0) - target) < 1e-9 * target


def test_solve_a_just_over_the_line_is_small_and_positive():
    a = solve_a(1.0 * (1 + 1e-6), 1.0)
    assert 0 < a < 1e-4


def test_solve_a_past_its_bound_raises():
    with pytest.raises(ValueError):
        solve_a(opening_slope(C.A_HI, 1.0) * 2, 1.0)


def test_the_curve_ends_and_its_line():
    assert C.curve(0.0, 1.0, 50.0) == 1.0
    assert abs(C.curve(1.0, 1.0, 50.0)) < 1e-15
    assert abs(C.curve(0.25, 1.0, 0.0) - 0.75) < 1e-15
    eps = 1e-7
    assert abs((1 - C.curve(eps, 1.0, 50.0)) / eps - opening_slope(50.0, 1.0)) < 1e-3


def test_vanillas_rates_at_the_90_minute_day():
    assert abs(C.r_hunger(90) - 3.564) < 1e-12
    assert abs(C.r_thirst(90) - 17.82) < 1e-12


def test_calibrate_opens_at_vanillas_rate():
    cal = C.calibrate(4.36e-4, 1.09e-2)
    assert abs(cal["opening_health_per_h"]["starve"] - 3.564) < 1e-9
    assert abs(cal["opening_health_per_h"]["dehyd"] - 17.82) < 1e-9


# ---- the artifact ---------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def art():
    with open(C.ARTIFACT, encoding="utf-8") as fh:
        return json.load(fh)


def test_the_artifact_names_its_fields(art):
    for k in ("a_starve", "a_dehyd", "starve_dpdt_per_h", "dehyd_dpdt_per_h", "r_hunger_90", "r_thirst_90",
              "day_minutes", "window_h", "inputs", "inputs_sha256", "tool_commit"):
        assert k in art, k
    assert art["day_minutes"] == 90
    assert art["window_h"] == {"starve": 24, "dehyd": 6}
    assert art["inputs_sha256"] == C.combined(art["inputs"])


def test_both_a_values_are_finite_and_positive(art):
    for k in ("a_starve", "a_dehyd"):
        assert math.isfinite(art[k]) and art[k] > 0, k


def test_the_artifacts_a_values_open_at_vanillas_rate(art):
    s = 100 * opening_slope(art["a_starve"], 1.0) * art["starve_dpdt_per_h"]
    d = 100 * opening_slope(art["a_dehyd"], 1.0) * art["dehyd_dpdt_per_h"]
    assert abs(s - art["r_hunger_90"]) < 1e-9 and abs(d - art["r_thirst_90"]) < 1e-9


@pytest.fixture(scope="module")
def fresh(tmp_path_factory):
    """An artifact written now from the working tree, so the check cases do not depend on whether the committed
    artifact's inputs have moved since (a later mod/ edit changes their hashes, which --check reports by design)."""
    path = os.path.join(str(tmp_path_factory.mktemp("cal")), "calibration.json")
    C.write(path)
    with open(path, encoding="utf-8") as fh:
        return path, json.load(fh)


def test_check_is_in_sync_on_a_fresh_write(fresh):
    assert C.check(path=fresh[0]) == []


def _copy_inputs(dst):
    for p in C.input_files():
        rel = os.path.relpath(p, C.REPO)
        os.makedirs(os.path.join(dst, os.path.dirname(rel)), exist_ok=True)
        shutil.copyfile(p, os.path.join(dst, rel))


def test_a_copy_of_the_inputs_hashes_the_same(tmp_path):
    _copy_inputs(str(tmp_path))
    assert C.input_hashes(str(tmp_path)) == C.input_hashes()


def test_check_fails_when_one_input_byte_changes(tmp_path, fresh):
    _copy_inputs(str(tmp_path))
    target = os.path.join(str(tmp_path), "tools", "replay_live.py")
    with open(target, "rb") as fh:
        data = bytearray(fh.read())
    data[10] = data[10] ^ 0x01
    with open(target, "wb") as fh:
        fh.write(bytes(data))
    bad = C.check(path=fresh[0], root=str(tmp_path))
    assert len(bad) == 1 and bad[0].startswith("input tools/replay_live.py:")


def test_check_fails_when_a_value_differs(tmp_path, fresh):
    forged = dict(fresh[1])
    forged["a_starve"] = forged["a_starve"] * (1 + 1e-12)
    path = os.path.join(str(tmp_path), "calibration.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(C.dumps(forged))
    bad = C.check(path=path)
    assert len(bad) == 1 and bad[0].startswith("value a_starve:")


def test_the_committed_values_match_a_fresh_write(art, fresh):
    """The committed calibration against a recomputation, inputs aside: the a values and the reads they rest on."""
    for k in ("a_starve", "a_dehyd", "starve_dpdt_per_h", "dehyd_dpdt_per_h", "starve", "dehyd"):
        assert fresh[1][k] == art[k], k


def test_main_check_exits_non_zero_on_a_finding(monkeypatch):
    monkeypatch.setattr(C, "check", lambda: ["input x: sha256 a, the artifact's b"])
    assert C.main(["--check"]) == 1
    monkeypatch.setattr(C, "check", lambda: [])
    assert C.main(["--check"]) == 0
