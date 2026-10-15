"""Offline tests of Plan 14 Task 5 fix round 3: the beer containers (testing/experiments/x44_beers.py) checked against the
install's item scripts and the x445 run's live fills, x447's pre-run override with its pre-boot check, and x445b's beer
arm against the guide lib's fake vanilla world (its real reply shapes), as predicted and with a failing case per grade."""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))
sys.path.insert(0, HERE)

import test_x44_guide_lib as T       # noqa: E402
import x44_beers as BE               # noqa: E402
import x44_guide_lib as L            # noqa: E402
import x445b_beers as D5             # noqa: E402
import x447_mod_acute as D7          # noqa: E402

REPO = L.REPO
X445 = os.path.join(REPO, "testing", "artifacts", "x445-20261015-175946", "drinks.json")
HAVE_SCRIPTS = os.path.isfile(BE.GAME_ITEMS)


# ---------------------------------------------------------------- the containers against the scripts
@pytest.mark.skipif(not HAVE_SCRIPTS, reason="the install's item scripts are absent on this machine")
@pytest.mark.parametrize("full, line", [("Base.BeerCan", 6101), ("Base.Pop2", 7051), ("Base.Pop", 7025),
                                        ("Base.SodaCan", 7174)])
def test_each_beer_container_takes_a_beer_fill(full, line):
    with open(BE.GAME_ITEMS, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    c = BE.container_check(text, full)
    assert c["ok"] and c["line"] == line and c["capacity"] == 0.3, c
    assert not c["opened_false"] and not c["opening_recipe"] and not c["fluid_filter"] and c["prefilled"]


@pytest.mark.skipif(not HAVE_SCRIPTS, reason="the install's item scripts are absent on this machine")
@pytest.mark.parametrize("full", ["Base.BeerBottle", "Base.BeerImported"])
def test_the_sealed_beers_fail_the_check(full):
    with open(BE.GAME_ITEMS, encoding="utf-8", errors="replace") as fh:
        c = BE.container_check(fh.read(), full)
    assert c["ok"] is False and c["opened_false"] and c["opening_recipe"], c


@pytest.mark.skipif(not HAVE_SCRIPTS, reason="the install's item scripts are absent on this machine")
def test_script_check_passes_the_choice_and_fails_the_old_one():
    assert BE.script_check()[1] is True
    assert BE.script_check(L.BEER_CONTAINERS)[1] is False                      # the frozen lib's x445 set
    assert BE.script_check(("Base.BeerCan", "Base.Pop2", "Base.Pop", "Base.Pop3"))[1] is False   # a coffee type
    assert BE.script_check(("Base.BeerCan", "Base.Pop2", "Base.Pop", "Base.Pop"))[1] is False    # not distinct
    assert BE.script_check(path=os.path.join(REPO, "nowhere.txt"))[1] is False


def _block(name, body):
    return f"\n    item {name}\n    {{\n{body}\n    }}\n"


def test_container_check_failing_cases():
    ok = "        component FluidContainer\n        {\n            Capacity = 0.3,\n            Fluids\n            {\n" \
         "                fluid = Beer:1.0,\n            }\n        }"
    assert BE.container_check(_block("A", ok), "Base.A")["ok"] is True
    assert BE.container_check(_block("A", ok.replace("Capacity = 0.3", "Capacity = 0.2")), "Base.A")["ok"] is False
    assert BE.container_check(_block("A", ok + "\n        Opened = false,"), "Base.A")["ok"] is False
    assert BE.container_check(_block("A", "        OpeningRecipe = X,\n" + ok), "Base.A")["ok"] is False
    assert BE.container_check(_block("A", ok + "\n        Whitelist = Water,"), "Base.A")["ok"] is False
    assert BE.container_check(_block("A", ok.replace("fluid = Beer:1.0,", "")), "Base.A")["ok"] is False
    assert BE.container_check(_block("A", "        Weight = 1,"), "Base.A")["ok"] is False
    assert BE.container_check(_block("A", ok), "Base.B")["found"] is False


def test_x445_live_fills_back_the_choice():
    with open(X445, encoding="utf-8") as fh:
        doc = json.load(fh)
    by = {d["container"]: d for d in doc["drinks"]}
    for full in BE.LIVE_EVIDENCE:
        f = by[full]["fill"]
        assert f["ok"] is True and abs(f["litres"] - 0.3) < 1e-6 and f["fluid"] == "Beer" and by[full]["landed"]
    for full in ("Base.BeerBottle", "Base.BeerImported"):
        assert by[full]["fill"]["ok"] is False and by[full]["fill"]["litres"] == 0 and not by[full]["landed"]


# ---------------------------------------------------------------- x447's override
def test_x447_overrides_its_beers_after_the_check(monkeypatch):
    monkeypatch.setattr(L, "BEER_CONTAINERS", L.BEER_CONTAINERS)                  # restored after the test
    assert D7.BEERS == BE.BEERS
    if HAVE_SCRIPTS:
        D7.beers_preboot()
        assert L.BEER_CONTAINERS == BE.BEERS
    monkeypatch.setattr(BE, "script_check", lambda beers: ({"why": "x"}, False))
    monkeypatch.setattr(L, "BEER_CONTAINERS", ("Base.BeerBottle",))
    with pytest.raises(SystemExit):
        D7.beers_preboot()
    assert L.BEER_CONTAINERS == ("Base.BeerBottle",)                              # refused before any override


def test_x447_m2_drinks_the_override(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "BEER_CONTAINERS", BE.BEERS)
    S, out, w, seen, d = T.run_modded("M2", tmp_path, monkeypatch, age=3.3)
    beers = [x["container"] for x in S.drinks if x["fluid"] == "Beer"]
    assert beers == list(BE.BEERS) and all(x["fill_ok"] for x in S.drinks)


# ---------------------------------------------------------------- x445b
@pytest.fixture
def v4b(monkeypatch):
    monkeypatch.setattr(L, "SESSIONS", dict(L.SESSIONS, **{D5.KEY: dict(D5.SPEC)}))
    monkeypatch.setattr(L, "BEER_CONTAINERS", D5.BEERS)
    monkeypatch.setattr(L, "Sess", D5.BeerSess)
    return D5.KEY


def test_x445b_names_its_session(v4b):
    assert D5.PREFIX == "x445b" and D5.PROFILE == "x44-vanilla-sleep" and D5.BUDGET_S <= 500
    if any(d.startswith("x445b-") for d in os.listdir(os.path.join(T.REPO, "testing", "artifacts"))):
        pytest.skip("x445b has run; its committed artifact is the evidence")
    checks, ok = L.preboot(v4b, D5.PROFILE, D5.PREFIX, "x445b_beers.py")
    assert ok, checks
    assert L.preboot(v4b, D5.PROFILE, D5.PREFIX, "x445_drinks.py")[1] is False


def test_x445b_register_sets_its_process(monkeypatch):
    monkeypatch.setattr(L, "SESSIONS", dict(L.SESSIONS))
    monkeypatch.setattr(L, "BEER_CONTAINERS", L.BEER_CONTAINERS)
    monkeypatch.setattr(L, "Sess", L.Sess)
    D5.register()
    assert L.SESSIONS["V4b"]["prefix"] == "x445b" and L.BEER_CONTAINERS == BE.BEERS and L.Sess is D5.BeerSess


def test_x445b_flow_as_predicted(v4b):
    v, out, w = T.run_vanilla(v4b)
    assert v == {"V4_B_decay": "as_predicted", "V4_B_zero": "as_predicted"}, T.whys(out)
    assert [x["container"] for x in out["drinks"]] == list(BE.BEERS) and all(x["fill_ok"] for x in out["drinks"])
    assert [p for p, _f in out["phase_walls"].items()] == ["S", "B", "C", "R"]
    assert out["checks"]["restore"]["ok"] is True and out["checks"]["S"]["thirst"]["values"] == {"thirst": 0.0}
    assert [e["kind"] for e in out["model_inputs"]["scenario"]["events"]].count("drink") == 4


@pytest.mark.parametrize("flag, verdict", [("intox_slow", "falsified"), ("fill_refused", "unmeasured"),
                                           ("probe_item_only", "unmeasured")])
def test_x445b_failing_cases(v4b, flag, verdict):
    v, out, _w = T.run_vanilla(v4b, {flag: True})
    assert v["V4_B_decay"] == verdict and v["V4_B_zero"] == verdict, (v, T.whys(out))
