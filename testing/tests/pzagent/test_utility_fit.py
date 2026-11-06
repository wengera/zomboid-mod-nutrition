"""The utility's fit (Plan 31 Task 11 U; `tools/utility_fit.py`, its compact artifact `data/fits/utility-weights.json`):
the linear program's solver, the logistic fit, the verdict rules, the stability probes, and the package's dials pinned
to the artifact the tool reproduces."""
import itertools
import json
import os
import sys

import numpy as np
import pytest

from agent.base.planner.utility import acts as A
from agent.base.planner.utility import features as F
from agent.base.planner.utility import models as M
from agent.base.planner.utility import weights as W

from .test_utility import door, dress, fight, retreat, sit, zed

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import utility_fit as U  # noqa: E402


@pytest.fixture(scope="module")
def art():
    with open(U.OUT, encoding="utf-8") as f:
        return json.load(f)


# ================================================================ the solver
def brute(c, A_, b):
    """max c.x over the vertices of A x <= b in 2 or 3 dimensions (every n-subset of rows solved), else None."""
    A_, b, n = np.asarray(A_, float), np.asarray(b, float), len(c)
    best = None
    for rows in itertools.combinations(range(len(b)), n):
        M_ = A_[list(rows)]
        if abs(np.linalg.det(M_)) < 1e-9:
            continue
        x = np.linalg.solve(M_, b[list(rows)])
        if np.all(A_ @ x <= b + 1e-7):
            v = float(np.dot(c, x))
            best = v if best is None or v > best else best
    return best


def test_lp_max_on_a_box():
    st, x, v = U.lp_max([1.0, 1.0], [[1, 0], [0, 1], [-1, 0], [0, -1]], [1.0, 2.0, 0.0, 0.0])
    assert st == "optimal" and v == pytest.approx(3.0) and list(x) == pytest.approx([1.0, 2.0])


def test_lp_max_reads_an_empty_region_infeasible():
    st, x, _ = U.lp_max([1.0], [[1.0], [-1.0]], [-1.0, 0.0])
    assert st == "infeasible" and x is None


@pytest.mark.parametrize("seed", range(40))
def test_lp_max_agrees_with_the_vertices(seed):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(2, 4))
    A_ = np.vstack([rng.normal(size=(int(rng.integers(1, 8)), n)), np.eye(n), -np.eye(n)])
    b = np.concatenate([rng.normal(size=len(A_) - 2 * n) + 1.0, np.full(2 * n, 4.0)])
    c = rng.normal(size=n)
    st, x, v = U.lp_max(c, A_, b)
    want = brute(c, A_, b)
    if want is None:
        assert st == "infeasible"
    else:
        assert st == "optimal" and v == pytest.approx(want, abs=1e-6) and np.all(A_ @ x <= b + 1e-6)


def test_the_logistic_fit_recovers_its_coefficients():
    rng = np.random.default_rng(3)
    d = rng.uniform(0.0, 6.0, 40000)
    p = 1.0 / (1.0 + np.exp(-(-0.5 - 1.5 * d)))
    y = rng.uniform(size=d.size) < p
    beta = U.logistic(np.column_stack([np.ones_like(d), d]), y)
    assert beta == pytest.approx([-0.5, -1.5], abs=0.1)


# ================================================================ the verdict rules
def _labels(s, cands):
    return {rule: (lab.key if lab is not None else None, sorted(o.key for o in others))
            for rule, lab, others in U.label(s, cands, _W(), {"branch": "goal", "action": {"type": "walkTo"}})}


class _W:
    map = {}

    def marked_doors(self, side=None):
        return frozenset()

    def edge_steps(self, a, b):
        return []


TRAVEL = A.Candidate("travel", "travel")


def test_rule_one_labels_the_fight_over_every_act_that_is_no_fight():
    s = sit([zed(1, 4.0), zed(2, 2.0, standing=False, deg=90.0)])
    cands = [fight(s.zed(1)), fight(s.zed(2)), TRAVEL, retreat()]
    assert _labels(s, cands)["one"] == ("fight:1", sorted(["travel", retreat().key]))


def test_rule_one_leaves_out_a_spent_character_s_unaware_zombie_and_a_group_listed():
    spent = sit([zed(1, 4.0, aware=False)], endurance=0.3)
    assert "one" not in _labels(spent, [fight(spent.zed(1)), TRAVEL])
    crowd = sit([zed(1, 4.0), zed(2, 8.0, deg=90.0), zed(3, 9.0, deg=180.0)])
    assert "one" not in _labels(crowd, [fight(crowd.zed(1)), TRAVEL])


def test_the_dress_rules_beat_every_act_but_a_fight_and_leave_a_group_out():
    quiet = sit([], bleeding=[F.Part(1, 5.0, 50.0)])
    assert _labels(quiet, [dress(), TRAVEL])["dress_quiet"] == ("dress:1", ["travel"])
    far = sit([zed(1, 4.0)], bleeding=quiet.bleeding)
    assert _labels(far, [dress(), TRAVEL, fight(far.zed(1))])["dress_far"] == ("dress:1", ["travel"])
    near = sit([zed(1, 2.0)], bleeding=quiet.bleeding)
    assert "dress_far" not in _labels(near, [dress(), TRAVEL, fight(near.zed(1))])
    group = sit([zed(i, 7.0 + 0.5 * i, deg=40.0 * i) for i in range(3)], bleeding=quiet.bleeding)
    assert not {"dress_quiet", "dress_far"} & set(_labels(group, [dress(), TRAVEL]))


def test_the_group_rules_set_the_nearest_filter_s_retreat_over_the_fights_beyond_reach():
    s = sit([zed(1, 2.0), zed(2, 4.0, deg=90.0), zed(3, 4.5, deg=180.0)])
    far_ret, near_ret = retreat(door(9.0)), retreat(A.Filter("door", (105, 200, 0), (105.5, 200.5), 7, 5.5))
    cands = [fight(z) for z in s.zeds] + [far_ret, near_ret]
    lab = _labels(s, cands)
    assert lab["group_coming"] == (near_ret.key, ["fight:2", "fight:3"])
    close = sit([zed(1, 1.0), zed(2, 2.0, deg=90.0), zed(3, 2.4, deg=180.0)])
    assert "group" not in _labels(close, [fight(z) for z in close.zeds] + [near_ret])   # all in reach: the scores'


def test_a_row_is_the_labelled_score_less_the_other_s_with_h_in_the_constant():
    raw_l = {"kill": 0.5, "hit": -0.2, "bleed": 0.0, "chase": 1.0, "goal": 0.0, "regress": 0.0}
    raw_o = {"kill": 0.0, "hit": -0.1, "bleed": -0.1, "chase": 0.0, "goal": 1.0, "regress": -0.3}
    a, c = U._row(raw_l, raw_o)
    assert dict(zip(U.NAMES, a)) == pytest.approx({"K": 0.5, "B": 0.1, "C": 1.0, "G": 0.3, "V": -1.0})
    assert c == pytest.approx(-0.1)


def test_a_flat_weight_reads_no_moved_line():
    raw = {"kill": 0.0, "hit": 0.0, "bleed": 0.0, "chase": 0.0, "goal": 1.0, "regress": 0.0}
    lab = [{"act": "a", "raw": {"a": dict(raw, kill=1.0), "b": raw}}]
    st = U.stability(lab, {k: 1.0 for k in U.NAMES})
    assert st["probes"]["K"]["x0.95"]["moved"] == 1 and st["probes"]["G"]["x0.95"]["moved"] == 0


# ================================================================ the artifact and the package's dials
def test_the_models_are_the_artifact_s(art):
    used = art["models"]["used"]
    assert (M.FITTED.hit_b0, M.FITTED.hit_b1, M.FITTED.p_swing, M.FITTED.p_finish) == (
        used["hit_b0"], used["hit_b1"], used["p_swing"], used["p_finish"])
    assert art["models"]["hazard"]["n"] > 0 and art["models"]["hazard"]["onsets"] > 0


def test_the_weights_are_the_chosen_point_inside_their_intervals(art):
    lp = art["lp"]
    assert lp["status"] == "optimal" and lp["radius"] > 0.0 and lp["least_slack"] >= 0.0
    for name, dial in W.WEIGHTS.items():
        assert dial.value == lp["chosen"][name]
        assert [dial.lo, dial.hi] == lp["intervals"][name]
        assert dial.lo <= dial.value <= dial.hi
    at = {b["weight"] for b in lp["at_bound"]}
    assert all(("lower bound" in W.WEIGHTS[n].source) for n in at)


def test_every_weight_s_five_percent_probe_moves_a_labelled_line(art):
    for name, probe in art["stability"]["probes"].items():
        assert probe["x0.95"]["moved"] > 0 and probe["x1.05"]["moved"] > 0, name


def test_every_rule_with_rows_holds_at_the_chosen_point(art):
    for group, rec in art["lp"]["slacks"].items():
        assert rec["least"]["slack"] >= 0.0, group
    for rule, rec in art["verdicts"]["structural"].items():
        assert rec["held"] == rec["n"], rule
    assert art["verdicts"]["door"]["wait_candidates"] == 0


def test_the_inputs_are_the_committed_rings(art):
    assert set(art["inputs"]) == set(U.RINGS)
    for key, files in art["inputs"].items():
        assert "decision.log" in files and "state.log" in files


def test_the_tool_reproduces_its_artifact():
    """`--check`: the models refitted and the program solved again from the rings give the committed bytes."""
    assert U.main(["--check"]) == 0
