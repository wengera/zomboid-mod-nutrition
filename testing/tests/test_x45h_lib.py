"""Offline tests of testing/experiments/x45h_lib.py (x453b, live review F6): the session against test_x45g_lib's fake
world (the harness's real reply shapes), as predicted and once per defect flag moving a named grade; the pairs saved; the
seed order; the pre-boot checks."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x45h_lib as H                  # noqa: E402
import x45g_lib as G                  # noqa: E402
import xlib as X                      # noqa: E402
import test_x45g_lib as T             # noqa: E402


def run_b(tmp_path, flags=(), budget=1e9):
    d = str(tmp_path)
    w = T.World(d, flags)
    out = T.fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={"admin": T.FakeClient("admin")}, ask=w.ask, budget_s=budget,
              clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = T.FakeServer(w, d)
    S = H.Sess(xs, "x453b", run_dir=d)
    S.body_run(S.phases())
    out["logs"] = {"mod_error": []}
    out["admin_lua_error"] = False
    S.grade_all()
    return {k: v["verdict"] for k, v in out["verdicts"].items()}, out, w, S


def test_as_predicted(tmp_path):
    v, out, w, S = run_b(tmp_path)
    assert not out["phase_errors"], out["phase_errors"]
    assert all(x == "as_predicted" for x in v.values()), T.bad(v, out)
    assert set(v) == {"H1", "RING", "Z", "OF_REACH", "OF_REFUSE", "OF_EARLY", "OF_TIMER", "OF_NAUSEA", "OF_ENDURANCE",
                      "PAIRS_foodEaten"}
    assert out["checks"]["restore"]["ok"] and w.speed == 1.0
    assert out["checks"]["pairs"] and len(out["checks"]["pairs"]) == len(S.pairs)            # review F4
    assert out["verdicts"]["PAIRS_foodEaten"]["observed"]["pair_slack_s"] == H.PAIR_SLACK_B
    assert G.PAIR_SLACK_S == 0.3                                                               # restored after the grade
    sets = [s["path"] for s in out["sets"]]
    assert sets[:2] == ["stomach.buffer.calories", "stomach.buffer.water"]                    # calories first
    assert out["checks"]["SEED"]["slow"]["ok"] and len(out["checks"]["X"]["eats"]) == 1
    assert out["checks"]["X"]["timer_polls"] and out["checks"]["X"]["trigger"]["level"] == 4


@pytest.mark.parametrize("flag,grades", [
    ("no_refuse", {"OF_REFUSE", "OF_TIMER"}),
    ("refuse_lands", {"OF_REFUSE"}),
    ("no_nausea", {"OF_NAUSEA"}),
    ("no_endcap", {"OF_ENDURANCE"}),
    ("client_stale", {"PAIRS_foodEaten"}),
])
def test_each_defect_moves_its_grade(tmp_path, flag, grades):
    v, out, _, _ = run_b(tmp_path, (flag,))
    for gname in grades:
        assert v.get(gname) != "as_predicted", (flag, gname, out["verdicts"].get(gname, {}).get("observed"))


def test_the_slack_is_restored_when_the_grade_raises(monkeypatch, tmp_path):
    v, out, w, S = run_b(tmp_path)

    def boom(rows):
        raise RuntimeError("x")
    monkeypatch.setattr(S, "grade_x453", boom)
    with pytest.raises(RuntimeError):
        S.grade_x453b([])
    assert G.PAIR_SLACK_S == 0.3


def test_preboot_and_the_driver(monkeypatch):
    monkeypatch.setitem(G.SESSIONS, "x453b", H.SESSIONS["x453b"])
    if any(d.startswith("x453b-") for d in os.listdir(os.path.join(G.REPO, "testing", "artifacts"))):
        pytest.skip("x453b has run; its artifact is the evidence")
    checks, ok = G.preboot("x453b", G.PROFILE, "x453b", "x453b_overfull.py")
    assert ok, checks
    src = open(os.path.join(G.REPO, "testing", "experiments", "x453b_overfull.py"), encoding="utf-8").read()
    assert 'KEY = "x453b"' in src and "import x45h_lib as L" in src and 'PROFILE = "x45g-mod"' in src


def test_other_keys_keep_x45g_phases(tmp_path):
    d = str(tmp_path)
    w = T.World(d)
    xs = X.Xs(T.fresh_out(), node=lambda side: side, clients={}, ask=w.ask, clock=w.clock, sleep=w.sleep)
    assert [n for n, _ in H.Sess(xs, "x457", run_dir=d).phases()] == [n for n, _ in G.Sess(xs, "x457").phases()]


def test_the_frozen_table_is_untouched_by_import():
    assert "x453b" not in G.SESSIONS
