"""Offline tests of testing/experiments/x49c_lib.py, x49c_prerun.py and x495_release.py (Plan 18 Task 4, run x495, the
release after a snack): x495's body run against test_x49b_lib's fake world (the mod on the replay host with vanilla's
physics laid over it tick by tick, the probe's snapshots and trackers on both sides, the harness's real reply shapes),
once as predicted and once per defect flag, so every grade has a case that falsifies it; the S pair's retry, REL_END's
eased bound, the measured budget, the rebinding of x49b's preboot and main, the prerun current at HEAD and the driver's
refusal and predictions.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
EXP = os.path.join(os.path.dirname(HERE), "experiments")
sys.path.insert(0, EXP)

import x49c_lib as L                  # noqa: E402
import x49c_prerun as PR              # noqa: E402
import x49b_lib as B                  # noqa: E402
import x48_lib as L48                 # noqa: E402
import x49_lib as L49                 # noqa: E402
import xlib as X                      # noqa: E402
import test_x48_lib as T48            # noqa: E402
import test_x49b_lib as TB            # noqa: E402

REPO = L.REPO


def run_session(tmp_path, flags=(), budget=1e9, s_gaps=0):
    d = str(tmp_path)
    os.makedirs(d, exist_ok=True)
    w = TB.World(d, flags)
    T48.fake_lread_saves(w)
    out = T48.fresh_out()
    if s_gaps:                                                   # the S pair's first reads fall over 1 s apart
        orig, left = w.ask, [s_gaps]

        def ask(node, cmd, args="", timeout=30):
            if cmd == "lua.read" and node == L.CLIENT and str(args).startswith("TKX_Symptoms.c ") and left[0] > 0:
                left[0] -= 1
                w.t += 3.0                                   # the read's midpoint 1.5 s off the server's
            return orig(node, cmd, args, timeout)
        w.ask = ask
    xs = X.Xs(out, node=lambda side: side, clients={"admin": T48.FakeClient("admin")}, ask=w.ask, budget_s=budget,
              clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = T48.FakeServer(w, d)
    S = L.Sess(xs, "x495", run_dir=d)
    for _ in range(int(0.25 * 60)):
        w.sleep(w.GH_S / 60.0)
    S.body_run(S.phases())
    out["logs"] = {"mod_error": []}
    out["admin_lua_error"] = False
    S.grade_all()
    v = {k: x["verdict"] for k, x in out["verdicts"].items()}
    return v, out, w, S


bad = TB.bad
NAMES = TB.NAMES - {"PAIN_ONSET"}                               # beriberi lands before the onset window


@pytest.fixture(scope="module")
def as_predicted(tmp_path_factory):
    return run_session(tmp_path_factory.mktemp("x495"))


def test_x495_as_predicted(as_predicted):
    v, out, w, S = as_predicted
    assert set(v) == NAMES
    assert not bad(v, out), bad(v, out)
    assert not out["phase_errors"] and not out.get("skipped_phases") and not out.get("budget_stop")
    assert list(out["phase_walls"]) == ["S", "H", "W", "A", "P1", "B", "L", "C", "R"]
    assert [a["arm"] for a in S.arms] == ["B", "L1", "L2"]


def test_x495_reads_as_its_prerun(as_predicted):
    v, out, w, S = as_predicted
    p = L.load_prerun()["x495"]
    assert out["verdicts"]["PAIN_LEVELS"]["observed"]["B"]["want"] == p["pre"]["levels"]["pain"] == 2
    assert out["verdicts"]["PAIN_LEVELS"]["observed"]["L2"]["want"] == p["end"]["levels"]["pain"] == 1
    assert out["verdicts"]["END_LEVELS"]["observed"]["B"]["want"] == 2
    lp = out["verdicts"]["REL_LAPSE"]["observed"]
    assert lp["mask"] == p["lapse"]["mask"] == 4
    ru = out["verdicts"]["REL_UNHAPPY"]["observed"]
    assert ru["fall"] == pytest.approx(p["lapse"]["u_before"] - p["lapse"]["u_after"], abs=0.05)
    re_ = out["verdicts"]["REL_END"]["observed"]
    assert re_["cap_before"] == pytest.approx(0.355) and re_["cap_after"] > 0.72 and re_["eased_max"] == 1
    assert out["verdicts"]["REL_HEAL"]["observed"]["last_gap"] == pytest.approx(0.0, abs=B.REL_HEAL_TOL)
    assert [round(st["value"], 6) for st in out["stat_sets"]] == [0.3, 25.0]


FLAGS = [
    ("no_floors", {"STRESS_FLOOR", "STRESS_LEVELS", "UNHAPPY_LEVELS", "REPLAY_effects.stressFloor",
                   "REPLAY_effects.unhappyFloor", "REPLAY_moodLast.u", "REL_UNHAPPY"}),
    ("no_u_target", {"UNHAPPY_FLOOR", "REPLAY_moodLast.u", "REL_UNHAPPY"}),
    ("no_s_target", {"STRESS_FLOOR"}),
    ("no_cap", {"END_CAP", "END_LEVELS", "REPLAY_effects.enduranceCap"}),
    ("pain_kept", {"REL_PAIN", "PAIN_LEVELS", "REPLAY_effects.pain.7"}),
    ("no_beri_pain", {"PAIN_PART", "PAIN_TARGET", "PAIN_LEVELS", "REPLAY_effects.pain.13"}),
    ("pain_lost", {"PAIN_PART", "PAIN_TARGET", "PAIN_LEVELS"}),
    ("slow_moodle", {"PAIN_FOLLOWS"}),
    ("client_stale", {"PAIN_FOLLOWS", "PAIN_LEVELS", "END_LEVELS", "STRESS_LEVELS", "UNHAPPY_LEVELS", "REL_END"}),
    ("no_ease", {"REL_END", "REPLAY_effects.enduranceCap", "REPLAY_drain.target"}),
    ("no_subtract", {"REL_UNHAPPY"}),
    ("no_stress_decay", {"REL_STRESS"}),
    ("no_lapse", {"REL_LAPSE", "REL_UNHAPPY"}),
    ("heal_over", {"REL_HEAL"}),
    ("half_take", {"REPLAY_health"}),
    ("no_onset", {"ONSET"}),
    ("no_beri", {"BERI_ON"}),
]


@pytest.mark.parametrize("flag,grades", FLAGS)
def test_each_defect_falsifies_its_grade(flag, grades, tmp_path):
    v, out, w, S = run_session(tmp_path, flags=(flag,))
    falsified = {k for k, x in v.items() if x == "falsified"}
    assert grades <= falsified, (flag, bad(v, out))


def test_every_grade_has_a_failing_case():
    flagged = set().union(*(g for _, g in FLAGS))
    pure = {"OPT", "H1", "RING", "Z", "P0_BASE"}               # their failing cases: test_x49b_lib's pure tests
    assert NAMES <= flagged | pure, NAMES - flagged - pure


def test_the_s_pair_is_retried_until_valid(tmp_path):
    v, out, w, S = run_session(tmp_path, s_gaps=1)
    P = out["checks"]["S"]
    assert P["pair_tries"] == 2 and P["pair"]["valid"] and v["P0_BASE"] == "as_predicted"
    v, out, w, S = run_session(tmp_path / "all", s_gaps=9)
    assert out["checks"]["S"]["pair_tries"] == L.S_PAIR_TRIES and v["P0_BASE"] == "unmeasured"


def test_rel_end_holds_the_eased_bound():
    inf = TB._inf(n=400, a0=3.5, **{"effects.enduranceCap": 0.7295})
    ps = TB._rel_pairs(n=60, gm=1.5, e0=0.355)
    assert L.grade_rel_end_x495(ps, inf, 4.0, 0.355)[0] == "as_predicted"
    slow = TB._rel_pairs(n=60, gm=1.5, e0=0.355, climb=0.001)                   # still Endurance 2 at the end
    v, o, _ = L.grade_rel_end_x495(slow, inf, 4.0, 0.355)
    assert v == "falsified" and o["off_levels"]
    assert B.grade_rel_end(slow, inf, 4.0, 0.355)[0] == "as_predicted"           # x49b's bound (2) alone passes it
    # at the eased cap the writer pulls ENDURANCE back each minute: not a pull-down
    held = TB._rel_pairs(n=60, gm=1.5, e0=0.355)
    for i, p in enumerate(held):
        if p["s"]["endurance"] >= 0.73:
            for side in ("s", "c"):
                p[side]["endurance"] = 0.7345 if i % 2 else 0.7302
    assert L.grade_rel_end_x495(held, inf, 4.0, 0.355)[0] == "as_predicted"
    assert B.grade_rel_end(held, inf, 4.0, 0.355)[0] == "falsified"              # x49b's check would read it a fall
    pulled = TB._rel_pairs(n=60, gm=1.5, e0=0.355)
    pulled[20]["s"]["endurance"] = 0.2                                           # a pull-down well under the cap
    assert L.grade_rel_end_x495(pulled, inf, 4.0, 0.355)[0] == "falsified"
    assert L.grade_rel_end_x495(held, _inf_cap(0.355), 4.0, 0.355)[0] == "falsified"    # never eased


def _inf_cap(c):
    return TB._inf(n=400, a0=3.5, **{"effects.enduranceCap": c})


def test_the_budget_fits_the_measured_costs_and_a_slow_boot_cuts_only_l2(tmp_path):
    import x495_release as D
    w = L.predicted_wall()
    assert w["phases_end"] < D.BUDGET_S - B.CLOSE_RESERVE_S and w["worst_call"] < 600.0
    # a budget that leaves L2 short: its timed grades unmeasured, nothing falsified
    v, out, ww, S = run_session(tmp_path, budget=222.0)                # L2 starts at about 186 s in the fake
    l2 = S.arm_rec("L2")
    assert l2 and l2["secs_given"] < l2["secs_asked"] - 0.5
    assert "falsified" not in v.values(), bad(v, out)
    assert v["REL_END"] == "unmeasured" and v["REL_STRESS"] == "unmeasured"


def test_preboot_and_main_are_x49b_s_code_over_x495():
    f = L._rebind(B.main, SESSIONS=L.SESSIONS, preboot=L.preboot, LIB_FILE=L.LIB_FILE, Sess=L.Sess,
                  PRERUN_FILE=L.PRERUN_FILE)
    assert f.__code__ is B.main.__code__
    assert f.__globals__["Sess"] is L.Sess and f.__globals__["SESSIONS"] is L.SESSIONS
    assert B.SESSIONS == {"x494": B.SESSIONS["x494"]}                             # the frozen lib untouched


def test_preboot_on_the_repository_and_its_refusals(tmp_path):
    pre, ok = L.preboot("x495", "x495_release.py")
    if pre.get("no_prior_artifact") is False:
        pytest.skip("the session's artifact is committed: preboot refuses it by design")
    if not os.path.isfile(os.path.join(REPO, L48.FIXTURE_PLAYERS_DB)):
        pytest.skip("the default fixture cache is not provisioned on this machine")
    assert ok, {k: v for k, v in pre.items() if v is not True}
    assert L.preboot("x495", "x494_accept.py")[1] is False
    assert L.preboot("x494", "x494_accept.py")[1] is False
    stale = L.preboot("x495", "x495_release.py", compute=lambda keys: {"x495": {"x": 1}})
    assert stale[1] is False and stale[0]["prerun_current"] is False


def test_the_prerun_is_the_head_replay_and_reads_as_documented():
    pr = L48.prerun_current("x495", REPO, PR.compute, committed=L.load_prerun())
    assert pr["ok"], pr.get("diff")
    p = L.load_prerun()["x495"]
    assert p["pre"]["levels"] == {"endurance": 2, "pain": 2, "stress": 1, "unhappy": 1}
    assert p["end"]["levels"] == {"endurance": 1, "pain": 1, "stress": 0, "unhappy": 0}
    assert p["lapse"]["lag_m"] == 0 and p["lapse"]["mask"] == 4 and p["lapse"]["cap_before"] == 0.355
    assert p["heal_at_target_after_lapse_m"] is not None and p["l2_gm"] >= B.REL_HEAL_MIN_GM
    assert p["end"]["effects.pain.7"] == 0.0 and p["end"]["effects.pain.13"] == 12.95


def test_the_driver_names_its_session_refuses_arguments_and_predicts_every_grade():
    src = open(os.path.join(EXP, "x495_release.py"), encoding="utf-8").read()
    assert 'KEY = "x495"' in src and 'PREFIX = "x495"' in src and 'PROFILE = "x49-accept"' in src
    i_ref, i_main = src.index("L.parse_argv(sys.argv[1:]"), src.index("L.main(KEY")
    assert i_ref < i_main and "sys.exit(refusal)" in src[i_ref:i_main]
    import importlib
    D = importlib.import_module("x495_release")
    assert set(D.PRED) == NAMES and all(D.PRED.values())
    assert D.BUDGET_S <= 470.0
