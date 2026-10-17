"""The seed plate (Plan 15 Task 13 fix 1, the controller's ruling, option (a); NR_Server_Writer.lua W.seedPlate).

On an empty stomach the meal pool alone cannot write a HUNGER under the curve of the seed's capped read (about 0.13 at
07:00), so a fresh record whose vanilla HUNGER sits under that lands a real meal first: the curve fit's plate of the
guide's foods through the intake's own landing, sized to the least kcal whose first write is within the dead zone of the
vanilla HUNGER, at most one 667 kcal plate. A fresh spawn then writes about the HUNGER vanilla had, and a spawn at 0
returns to Peckish on the meal cadence. The runs are the mod's server pipeline (tools/replay_live.ServerReplay), a fresh
stand-in at 07:00 whose HUNGER is set before its first minute.
"""
import os
import sys

import pytest

from .server_host import REPO

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

DEAD = 0.02                                  # K.hungerCurve.DEAD_ZONE, written here
WATER = [{"minute": m, "kind": "autodrop", "g": 500.0} for m in (60, 180, 300, 420, 540, 660)]


def fresh(h0, minutes=60, extra=(), paths=("satiety.M",), plate_max=None):
    be = RL.ServerReplay(hour_offset=7.0, rng="half", sleep_allowed=False)
    if plate_max is not None:
        be.NR.server.writer.SEED_PLATE_MAX = plate_max
    ev = [{"minute": 0, "kind": "stat", "stat": "HUNGER", "value": h0}] + WATER + list(extra)
    ev = sorted((e for e in ev if e["minute"] < minutes), key=lambda e: e["minute"])
    rows = RL.run(be, RL.synthetic_ages(minutes), ev, list(paths), start_age=0.0)
    return rows, be


@pytest.mark.parametrize("h0", (0.0, 0.1, 0.2, 0.5))
def test_a_fresh_spawn_writes_back_its_vanilla_hunger_in_its_first_minute(h0):
    rows, be = fresh(h0, 2)
    assert abs(rows[0]["HUNGER"] - h0) <= DEAD + 1e-9
    W = be.NR.server.writer
    assert W.stats.seedPlates == (1 if h0 < 0.13 else 0)            # 0.2 and 0.5 the meal pool alone reaches


def test_a_spawn_at_zero_eats_a_real_plate_and_returns_to_peckish_on_the_meal_cadence():
    rows, be = fresh(0.0, 8 * 60, paths=("satiety.M", "stomach.buffer.calories"))
    W = be.NR.server.writer
    kcal = float(W.lastSeedKcal)
    assert 0 < kcal < float(W.SEED_PLATE_MAX) and W.stats.seedShort == 0
    assert rows[0]["stomach.buffer.calories"] == pytest.approx(kcal, rel=1e-6)   # landed whole, as an eat lands
    assert rows[0]["satiety.M"] >= be.K.hungerCurve.FED_M
    peckish = next(r["age"] for r in rows if r["HUNGER"] > 0.15)
    assert 3.5 <= peckish <= 4.4                                     # the curve's meal cadence (#3933, #3944)


def test_the_plate_is_capped_and_a_short_one_is_counted():
    rows, be = fresh(0.0, 2, plate_max=50.0)
    W = be.NR.server.writer
    assert W.stats.seedShort == 1 and W.stats.seedPlates == 1 and float(W.lastSeedKcal) == 50.0
    assert rows[0]["HUNGER"] > DEAD                                   # the residual, reported, never scaled past the cap


def test_a_record_seen_before_is_never_seeded():
    # fresh at 0.5 (the meal pool alone reaches it), then HUNGER set to 0 at minute 30: the record has its M, no plate
    rows, be = fresh(0.5, 60, extra=[{"minute": 30, "kind": "stat", "stat": "HUNGER", "value": 0.0}])
    W = be.NR.server.writer
    assert W.stats.seedPlates == 0 and W.stats.seeded == 1
