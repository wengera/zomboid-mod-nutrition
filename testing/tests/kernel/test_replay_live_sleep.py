"""The replay's explicit sleep option and opt-in auto-drink detection (Plan 11f Task 4 fix round 1, F-T4-1, F-T4-2).

The replay host has no getServerOptions, so an unset option reads sleep as allowed (NR.server.readSleep: an unreadable
option reads true), while a live server with SleepAllowed or SleepNeeded false freezes the sleep state: the replay then
booked the stand-in's waking hours as debt at the acute record's 24 h window close. replay_live now takes
sleep_allowed (required), answered by a getServerOptions stand-in the options poll reads every minute
(NutritionRevamp.sleepOn(), Plan 16 Task 4)."""
import json
import os
import sys

import pytest

from . import at_build
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
    assert be_off.rt.eval("function() return NutritionRevamp.sleepOn() end")() is False
    assert be_on.rt.eval("function() return NutritionRevamp.sleepOn() end")() is True
    assert max(r["acute.debtH"] for r in off) == 0
    assert on[-1]["acute.debtH"] > 1.0


def test_replay_live_refuses_a_missing_sleep_option():
    with pytest.raises(ValueError, match="sleep"):
        RL.replay_live(synthetic_ring(1), [], None, paths=["acute.debtH"])


def test_the_start_document_may_carry_the_option():
    rows = synthetic_ring(26)
    out, be = RL.replay_live(rows, [], {"sleepAllowed": False}, paths=["acute.debtH"], hour_offset=8.0 - 100.0 % 24)
    assert be.rt.eval("function() return NutritionRevamp.sleepOn() end")() is False
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


def test_x263_detects_exactly_the_unlogged_auto_drink_and_the_replay_follows_it(tmp_path):
    # Plan 15 Task 14b: x263's ring ran the old liquid lane (slowed by the solid lane's whole kcal), so the replay that
    # follows its auto-drink holds on the build before that change and is re-run there, frozen (CLAUDE.md § 5)
    code, out = at_build.run(tmp_path, at_build.PRE_LIQUID_LANE,
                             "testing/tests/kernel/test_replay_live_sleep.py::"
                             "test_x263_detects_exactly_the_unlogged_auto_drink_and_the_replay_follows_it",
                             ("testing/artifacts/x263-20261010-122318", "testing/artifacts/x265-20261010-124149"))
    assert code == 0 and " passed" in out, out


def test_x265_logged_milk_is_not_injected():
    rd, rr, rp = load_run(X265)
    assert RL.detect_autodrinks(rr, rd["events"]) == []
