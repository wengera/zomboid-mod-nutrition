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
from agent.base.planner.utility import select as S
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
def _labels(s, cands, ctx=A.Context(group=True)):
    return {rule: (lab.key if lab is not None else None, sorted(o.key for o in others))
            for rule, lab, others in U.label(s, cands, _W(), {"branch": "goal", "action": {"type": "walkTo"}}, ctx)}


class _W:
    map = {}

    def marked_doors(self, side=None):
        return frozenset()

    def edge_steps(self, a, b):
        return []


TRAVEL = A.Candidate("travel", "travel")


def test_rule_one_labels_the_fight_at_an_aware_zombie_in_reach_over_every_act_and_every_farther_fight():
    """The controller's ruling on M3 (fix 1, and fix 2: the fights at standing zombies beyond reach too; a fallen
    one's finish left to the scores): one zombie in reach is fought, whatever else is listed."""
    s = sit([zed(1, 2.0), zed(2, 1.5, standing=False, deg=90.0), zed(3, 5.0, deg=180.0)])
    cands = [fight(s.zed(1)), fight(s.zed(2)), fight(s.zed(3)), TRAVEL, retreat()]
    assert _labels(s, cands)["one"] == ("fight:1", sorted(["fight:3", "travel", retreat().key]))
    crowd = sit([zed(1, 2.0), zed(2, 8.0, deg=90.0), zed(3, 9.0, deg=180.0)], endurance=0.3)
    assert _labels(crowd, [fight(z) for z in crowd.zeds] + [TRAVEL])["one"][0] == "fight:1"


def test_rule_one_leaves_out_a_zombie_beyond_reach_or_unaware():
    far = sit([zed(1, 4.0)])
    assert "one" not in _labels(far, [fight(far.zed(1)), TRAVEL])
    unaware = sit([zed(1, 2.0, aware=False)])
    assert "one" not in _labels(unaware, [fight(unaware.zed(1)), TRAVEL])


def test_the_dress_rules_beat_every_act_but_a_fight_and_leave_a_group_out():
    quiet = sit([], bleeding=[F.Part(1, 5.0, 50.0)])
    assert _labels(quiet, [dress(), TRAVEL])["dress_quiet"] == ("dress:1", ["travel"])
    far = sit([zed(1, 4.0)], bleeding=quiet.bleeding)
    assert _labels(far, [dress(), TRAVEL, fight(far.zed(1))])["dress_far"] == ("dress:1", ["travel"])
    near = sit([zed(1, 2.0)], bleeding=quiet.bleeding)
    assert "dress_far" not in _labels(near, [dress(), TRAVEL, fight(near.zed(1))])
    group = sit([zed(i, 7.0 + 0.5 * i, deg=40.0 * i) for i in range(3)], bleeding=quiet.bleeding)
    assert not {"dress_quiet", "dress_far"} & set(_labels(group, [dress(), TRAVEL]))


def stand(z):
    return A.Candidate("stand", "stand:%s" % z.id, target=z.id, zed=z)


def test_the_group_rule_sets_the_nearest_filter_s_retreat_over_the_stand_and_the_fights_beyond_reach():
    s = sit([zed(1, 3.0), zed(2, 4.0, deg=90.0), zed(3, 4.5, deg=180.0)])
    far_ret, near_ret = retreat(door(9.0)), retreat(A.Filter("door", (105, 200, 0), (105.5, 200.5), 7, 5.5))
    cands = [fight(z) for z in s.zeds] + [stand(s.zed(1)), far_ret, near_ret]
    assert _labels(s, cands)["group_coming"] == (near_ret.key, ["fight:1", "fight:2", "fight:3", "stand:1"])
    close = sit([zed(1, 1.0), zed(2, 2.0, deg=90.0), zed(3, 2.4, deg=180.0)])
    assert "group" not in _labels(close, [fight(z) for z in close.zeds] + [near_ret])   # all in reach: the scores'


def test_with_no_filter_the_group_rule_sets_the_stand_over_walking_into_the_group():
    s = sit([zed(1, 4.0), zed(2, 7.0, deg=90.0), zed(3, 9.0, deg=180.0)])
    cands = [fight(z) for z in s.zeds] + [stand(s.zed(1))]
    assert _labels(s, cands)["group_coming"] == ("stand:1", ["fight:2", "fight:3"])
    assert "group_coming" not in _labels(s, cands, A.Context(group=False))   # no group arriving: no stand rule


def test_a_row_is_the_labelled_score_less_the_other_s_with_h_in_the_constant():
    raw_l = {"kill": 0.5, "hit": -0.2, "bleed": 0.0, "chase": 1.0, "goal": 0.0, "regress": 0.0}
    raw_o = {"kill": 0.0, "hit": -0.1, "bleed": -0.1, "chase": 0.0, "goal": 1.0, "regress": -0.3}
    a, c = U._row(raw_l, raw_o)
    assert dict(zip(U.NAMES, a)) == pytest.approx({"K": 0.5, "B": 0.1, "C": 1.0, "G": 0.3, "V": -1.0})
    assert c == pytest.approx(-0.1)


def test_a_row_s_constant_is_linear_in_the_drag_down_s_price():
    (r,) = U._at([{"a": [0.0] * 5, "c0": 0.5, "cd": -1.0}], 3.0)
    assert r["c"] == pytest.approx(-2.5)


# ================================================================ the artifact and the package's dials
def test_the_models_are_the_artifact_s(art):
    used = art["models"]["used"]
    assert (M.FITTED.hit_b0, M.FITTED.hit_b1, M.FITTED.p_swing, M.FITTED.p_finish) == (
        used["hit_b0"], used["hit_b1"], used["p_swing"], used["p_finish"])
    assert art["models"]["hazard"]["n"] > 0 and art["models"]["hazard"]["onsets"] == 51
    assert "51 hit-reaction onsets over ten rings" in M.__doc__


def test_the_weights_are_the_chosen_point_inside_their_intervals(art):
    lp = art["lp"]
    assert lp["status"] == "optimal" and lp["radius"] > 0.0 and lp["least_slack"] >= 0.0
    assert lp["drag_hits"] == S.DRAG_HITS
    for name, dial in W.WEIGHTS.items():
        assert dial.value == lp["chosen"][name]
        assert [dial.lo, dial.hi] == lp["intervals"][name]
        assert dial.lo <= dial.value <= dial.hi
    at = {b["weight"] for b in lp["at_bound"]}
    assert all(("lower bound" in W.WEIGHTS[n].source) for n in at)
    assert all("no direction sets it" in W.WEIGHTS[n].source for n in lp["unset"])


def test_the_weights_no_direction_sets_are_named_with_their_meaning(art):
    unset = art["lp"]["unset"]
    assert set(unset) == {"K", "V"}
    assert all(text.startswith("no direction sets it") for text in unset.values())


def test_the_caps_on_k_and_c_follow_the_drag_down_s_price(art):
    probe = art["lp"]["drag_probe"]
    assert [float(k) for k in probe] == list(U.DRAG_PROBE)
    feasible = [k for k in probe if probe[k]["status"] == "optimal"]   # fix 3: at 1 hit the region empties
    assert len(feasible) >= 2 and "3" in feasible
    his = [(probe[k]["K"][1], probe[k]["C"][1]) for k in feasible]
    assert all(a < b for a, b in zip([h[0] for h in his], [h[0] for h in his][1:]))
    assert all(a < b for a, b in zip([h[1] for h in his], [h[1] for h in his][1:]))
    assert probe["3"]["K"] == art["lp"]["intervals"]["K"] and probe["3"]["C"] == art["lp"]["intervals"]["C"]


FLAT = ("DRAG_HITS", "G", "hit_b0")   # flat at +-5 % on the two goldens' rings (the artifact's `flat`;
                                                # fix 1's report names them for the controller's ruling)


def test_the_flat_parameters_are_the_artifact_s(art):
    assert tuple(art["decision_probes"]["flat"]) == FLAT


@pytest.mark.parametrize("name", list(U.NAMES) + ["DRAG_HITS", "hit_b0"])
def test_each_parameter_s_five_percent_probe_moves_a_decision(art, request, name):
    """Fix 1 (M5): the probes count moved decisions on the goldens' rings, never margins; a flat one fails."""
    if name in FLAT:
        request.node.add_marker(pytest.mark.xfail(strict=True, reason="flat at +-5 %: for the controller's ruling"))
    assert sum(art["decision_probes"]["probes"][name].values()) > 0, name


def test_every_constraint_holds_at_the_chosen_point_with_its_own_slack(art):
    lp = art["lp"]
    assert len(lp["slacks"]) == lp["rows"] == art["verdicts"]["rows"]
    assert min(s[-1] for s in lp["slacks"]) >= 0.0
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
