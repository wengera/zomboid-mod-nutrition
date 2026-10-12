"""The replay's explicit sleep option and opt-in auto-drink detection (Plan 11f Task 4 fix round 1, F-T4-1, F-T4-2).

The replay host has no getServerOptions, so an unset option reads sleep as allowed (NUT.readSleepOptions: an unreadable
option reads true), while a live server with SleepAllowed or SleepNeeded false freezes the sleep state: the replay then
booked the stand-in's waking hours as debt at the acute record's 24 h window close. replay_live now takes
sleep_allowed (required), and the stand-in's NutritionRevamp.server.nutrients.sleepDisabled is set from it."""
import json
import os
import sys

import pytest

from .server_host import REPO

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
X263 = os.path.join(ART, "x263-20261010-122318")
X265 = os.path.join(ART, "x265-20261010-124149")


def synthetic_ring(hours=30, dtm=2.0):
    n = int(hours * 60 / dtm)
    return [{"s": i + 1, "ev": i + 1, "drained": i, "age": 100.0 + i * dtm / 60.0, "dtM": dtm,
             "hour": int((8 + i * dtm / 60.0) % 24), "min": int((i * dtm) % 60), "on": True} for i in range(n)]


def run_sleep(allowed):
    rows = synthetic_ring()
    out, be = RL.replay_live(rows, [], None, paths=["acute.debtH"], hour_offset=8.0 - 100.0 % 24,
                             sleep_allowed=allowed)
    return out, be


def test_sleep_off_books_no_debt_at_the_window_close_and_sleep_on_does():
    off, be_off = run_sleep(False)
    on, be_on = run_sleep(True)
    assert be_off.rt.eval("function() return NutritionRevamp.server.nutrients.sleepDisabled end")() is True
    assert be_on.rt.eval("function() return NutritionRevamp.server.nutrients.sleepDisabled end")() is False
    assert max(r["acute.debtH"] for r in off) == 0
    assert on[-1]["acute.debtH"] > 1.0


def test_replay_live_refuses_a_missing_sleep_option():
    with pytest.raises(ValueError, match="sleep"):
        RL.replay_live(synthetic_ring(1), [], None, paths=["acute.debtH"])


def test_the_start_document_may_carry_the_option():
    rows = synthetic_ring(26)
    out, be = RL.replay_live(rows, [], {"sleepAllowed": False}, paths=["acute.debtH"], hour_offset=8.0 - 100.0 % 24)
    assert be.rt.eval("function() return NutritionRevamp.server.nutrients.sleepDisabled end")() is True
    assert max(r["acute.debtH"] for r in out) == 0


def load_run(run):
    if not os.path.isdir(run):
        pytest.skip("the artifact is not in this tree")
    rd = {}
    for name in ("events", "start", "start-stats", "player"):
        with open(os.path.join(run, name + ".json"), encoding="utf-8") as fh:
            rd[name] = json.load(fh)
    pages = sorted(f for f in os.listdir(run) if f.startswith("minute-ring-admin-"))
    pages.sort(key=lambda f: int(f.split("-")[-1].split(".")[0]))
    rr, rp = RL.load_ring([os.path.join(run, f) for f in pages if not f.startswith("gate-")])
    return rd, rr, rp


def test_x263_detects_exactly_the_unlogged_auto_drink_and_the_replay_follows_it():
    rd, rr, rp = load_run(X263)
    found = RL.detect_autodrinks(rr, rd["events"])
    assert [x["s"] for x in found] == [179]
    assert found[0]["litres"] == pytest.approx(0.2, abs=0.002)
    kw = dict(paths=rp, user="admin", player=rd["player"], start_stats=rd["start-stats"], sleep_allowed=False,
              constants=RL.DEFICIT_11F)                          # the ring's build's deficit drive (Plan 11g Task 7)
    rows_off, be_off = RL.replay_live(rr, rd["events"], rd["start"], **kw)
    assert be_off.injected == []
    rows_on, be_on = RL.replay_live(rr, rd["events"], rd["start"], detect_autodrink=True, **kw)
    assert [x["s"] for x in be_on.injected] == [179]
    # Plan 11g Task 4: the artifact's ring was taken on the P model (its start record's satiety.P is no longer
    # loaded, so the replay seeds G from HUNGER), and HUNGER no longer replays within DEFAULT_TOL (the P model's replay
    # held it under 0.002 with the drink injected: this test at 0f14044f). The injected drink is read off the liquid
    # lane, which no satiety constant enters (since Plan 11g Task 6c fix 1 the stomach fill reads the lane whole, where the
    # ring's was taken at 0.2, so the fill no longer replays to 0.002); HUNGER's distance under the meal pool M is pinned as a
    # reading until a live run on M (Plan 11g Task 8)
    tol = {"body.energyState": RL.DEFAULT_TOL["body.energyState"], "satiety.L": RL.DEFAULT_TOL["satiety.L"],
           "stomach.liquid": ("abs", 1.0)}
    d_off = RL.diff(rows_off, rr, tol)
    d_on = RL.diff(rows_on, rr, tol)
    assert not d_off["ok"] and d_on["ok"], (d_off["findings"][:2], d_on["findings"][:2])
    assert d_off["fields"]["stomach.liquid"]["over"] > 0 and d_on["fields"]["stomach.liquid"]["max"] < 0.5
    h = RL.diff(rows_on, rr, {"HUNGER": RL.DEFAULT_TOL["HUNGER"]})["fields"]["HUNGER"]
    assert round(h["max"], 4) == 0.0121, h                              # the P ring against the refit M (Plan 11g Task 6c fix 1, and fix 2's alike): a reading (0.0171 under Task 6c's fit, 0.031 under the gut stage's fit), at DEFICIT_11F, the ring's deficit drive (Plan 11g Task 7)


def test_x265_logged_milk_is_not_injected():
    rd, rr, rp = load_run(X265)
    assert RL.detect_autodrinks(rr, rd["events"]) == []
