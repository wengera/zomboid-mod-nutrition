"""Offline tests of testing/experiments/x45i_lib.py and x452b_day.py (Plan 15 Task 14b): x452b's session against
test_x45g_lib's fake world (the harness's real reply shapes) as predicted and once per defect flag moving a named grade;
the bands are the HEAD replay of x452's schedule; the install touches the frozen module only when asked; the pre-boot
checks on the real repository."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x45i_lib as I                  # noqa: E402
import x45g_lib as G                  # noqa: E402
import xlib as X                      # noqa: E402
import test_x45g_lib as T             # noqa: E402

X452_GRADES = {"HYDRATED", "EAT0", "CAD_FEEL_P", "CAD_FEEL_H", "WF_SHOW", "WF_SPAN", "PAIRS_foodEaten", "PAIRS_hungry",
               "REPLAY_HUNGER", "REPLAY_THIRST", "REPLAY_body.energyState", "H1", "RING", "Z"}


def run_b(tmp_path, monkeypatch, flags=(), bands=None, replay=None):
    """x452b's body run after the install (through monkeypatch), the bands the fake world's (T.FAKE_BANDS) unless given."""
    I.install(monkeypatch.setattr, monkeypatch.setitem)
    monkeypatch.setattr(G, "CAD_P_TARGETS", dict(bands or T.FAKE_BANDS))
    monkeypatch.setattr(G, "CAD_H_TARGET", 8.0)
    d = str(tmp_path)
    w = T.World(d, flags)
    out = T.fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={"admin": T.FakeClient("admin")}, ask=w.ask, budget_s=1e9,
              clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = T.FakeServer(w, d)

    def fake_replay(ring_rows, events, start, tol, **kw):
        n = len(ring_rows)
        d_ = replay if replay is not None else {"fields": {f: {"n": n, "max": 0.0, "over": 0, "worst_s": None}
                                                           for f in tol}, "findings": [], "classes": {}}
        return [{"s": r["s"]} for r in ring_rows], d_, None
    monkeypatch.setattr(G, "replay_grade", fake_replay)
    S = G.Sess(xs, "x452b", run_dir=d)
    S.body_run(S.phases())
    out["logs"] = {"mod_error": []}
    out["admin_lua_error"] = False
    S.grade_all()
    return {k: v["verdict"] for k, v in out["verdicts"].items()}, out, w, S


def test_as_predicted_on_x452s_phases_and_grades(tmp_path, monkeypatch):
    v, out, w, S = run_b(tmp_path, monkeypatch)
    assert isinstance(S, I.Sess) and S.key == "x452" and S.spec == I.SESSIONS["x452b"]
    assert out["session_key_b"] == "x452b" and out["lib_x45i"] == "x45i_lib.py"
    assert not out["phase_errors"], out["phase_errors"]
    assert set(v) == X452_GRADES and all(x == "as_predicted" for x in v.values()), T.bad(v, out)
    assert [m["label"] for m in out["checks"]["X"]["meals"]] == ["lunch", "dinner", "breakfast"]
    assert out["checks"]["restore"]["ok"] and w.speed == 1.0


@pytest.mark.parametrize("flag,grades", [
    ("eat_hunger", {"EAT0"}),
    ("fast_hunger", {"CAD_FEEL_P", "CAD_FEEL_H"}),
    ("timer_off", {"WF_SHOW"}),
    ("wf_long", {"WF_SPAN"}),
    ("dry", {"HYDRATED"}),
    ("client_stale", {"PAIRS_foodEaten", "PAIRS_hungry"}),
])
def test_each_defect_moves_its_grade(tmp_path, monkeypatch, flag, grades):
    v, out, _, _ = run_b(tmp_path, monkeypatch, (flag,))
    for gname in grades:
        assert v.get(gname) != "as_predicted", (flag, gname, out["verdicts"].get(gname, {}).get("observed"))


def test_a_replay_over_the_tolerance_falsifies(tmp_path, monkeypatch):
    d = {"fields": {"HUNGER": {"n": 10, "max": 0.01, "over": 2, "worst_s": 5},
                    "THIRST": {"n": 10, "max": 0.0, "over": 0, "worst_s": None},
                    "body.energyState": {"n": 0, "max": 0.0, "over": 0, "worst_s": None}},
         "findings": [{"field": "HUNGER", "s": 5}], "classes": {}}
    v, _, _, _ = run_b(tmp_path, monkeypatch, replay=d)
    assert v["REPLAY_HUNGER"] == "falsified"


def test_the_installed_bands_grade_the_cadence(tmp_path, monkeypatch):
    # the real bands (lunch 3.483) against the fake world's 3.8 h returns: inside 0.5 h, so as predicted; bands moved by
    # a whole hour falsify
    v, _, _, _ = run_b(tmp_path, monkeypatch, bands=I.CAD_P_TARGETS_B)
    assert v["CAD_FEEL_P"] == "as_predicted"
    v, _, _, _ = run_b(tmp_path, monkeypatch, bands={k: x + 1.0 for k, x in I.CAD_P_TARGETS_B.items()})
    assert v["CAD_FEEL_P"] == "falsified"


def test_the_bands_are_the_head_replay_of_x452s_schedule():
    # x45g_prerun.py x452 at HEAD: each Peckish return and dinner's Hungry, and the hydration and stomach readings the
    # driver's HYDRATED names; a later mod change that moves them fails here before any boot
    import x45g_prerun as P
    r = P.x452()
    got = {m: r["meals"][m]["peckish_h"] for m in ("lunch", "dinner", "breakfast")}
    assert got == I.CAD_P_TARGETS_B
    assert r["meals"]["dinner"]["hungry_h"] == I.CAD_H_TARGET_B
    assert r["max_dehydPct"] == I.PRERUN_B["max_dehydPct"] and r["dehydrated_rows"] == 0
    assert r["max_THIRST"] == I.PRERUN_B["max_THIRST"] and r["max_stomach_g"] == I.PRERUN_B["max_stomach_g"]
    assert r["max_overfull"] == I.PRERUN_B["max_overfull"]
    assert all(r["meals"][m]["well_fed_h"] == I.PRERUN_B["well_fed_h"] for m in r["meals"])
    assert all(r["meals"][m]["eat0_max"] == 0 for m in r["meals"])


def test_the_driver_names_its_session_and_the_lib_its_bands():
    src = open(os.path.join(G.REPO, "testing", "experiments", "x452b_day.py"), encoding="utf-8").read()
    assert 'KEY = "x452b"' in src and 'PREFIX = "x452b"' in src and "import x45i_lib as L" in src
    assert 'PROFILE = "x45g-mod"' in src and 'ARTIFACT = "day.json"' in src
    for m, x in I.CAD_P_TARGETS_B.items():
        assert "%s %.3f" % (m, x) in src, m
    assert "9.550" in src and "1.452" in src and "790 g" in src


def test_the_import_leaves_the_frozen_module_alone():
    assert "x452b" not in G.SESSIONS and G.Sess is not I.Sess and G.LIB_FILE == "x45g_lib.py"
    assert G.CAD_P_TARGETS == {"lunch": 3.533, "dinner": 3.583, "breakfast": 4.033} and G.STAGED_FROM == "a97fec05"
    assert G.preboot is I._FROZEN_PREBOOT and G.staged_gate is I._FROZEN_STAGED_GATE


def test_the_install_puts_x452b_in(monkeypatch):
    I.install(monkeypatch.setattr, monkeypatch.setitem)
    assert G.SESSIONS["x452b"] == I.SESSIONS["x452b"] and G.Sess is I.Sess and G.LIB_FILE == "x45i_lib.py"
    assert G.CAD_P_TARGETS == I.CAD_P_TARGETS_B and G.CAD_H_TARGET == I.CAD_H_TARGET_B
    assert G.STAGED_FROM == I.STAGED_FROM_B and G.staged_gate.keywords == {"commit": I.STAGED_FROM_B}
    assert G.preboot is I.preboot


def test_other_keys_keep_x45g_phases(tmp_path):
    d = str(tmp_path)
    w = T.World(d)
    xs = X.Xs(T.fresh_out(), node=lambda side: side, clients={}, ask=w.ask, clock=w.clock, sleep=w.sleep)
    assert [n for n, _ in I.Sess(xs, "x457", run_dir=d).phases()] == [n for n, _ in G.Sess(xs, "x457").phases()]
    assert [n for n, _ in I.Sess(xs, "x452b", run_dir=d).phases()] == [n for n, _ in G.Sess(xs, "x452").phases()]


def test_preboot_on_the_real_repository(monkeypatch):
    if any(d.startswith("x452b-") for d in os.listdir(os.path.join(G.REPO, "testing", "artifacts"))):
        pytest.skip("x452b has run; its artifact is the evidence")
    I.install(monkeypatch.setattr, monkeypatch.setitem)
    checks, ok = G.preboot("x452b", G.PROFILE, "x452b", "x452b_day.py")
    assert ok, checks
    assert checks["cadence_bands_named"] and checks["bands_installed"] and checks["staged_from_is_mod_head"]


def test_preboot_refuses_bands_not_installed_or_a_stale_pin(monkeypatch):
    I.install(monkeypatch.setattr, monkeypatch.setitem)
    monkeypatch.setattr(G, "CAD_P_TARGETS", {"lunch": 3.533, "dinner": 3.583, "breakfast": 4.033})
    checks, ok = I.preboot("x452b", G.PROFILE, "x452b", "x452b_day.py")
    assert ok is False and checks["bands_installed"] is False
    I.install(monkeypatch.setattr, monkeypatch.setitem)
    monkeypatch.setattr(I, "mod_head", lambda repo=None: "a97fec05")
    checks, ok = I.preboot("x452b", G.PROFILE, "x452b", "x452b_day.py")
    assert ok is False and checks["staged_from_is_mod_head"] is False
