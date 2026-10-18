"""The ordinary day's Overfull minutes (Plan 15 Task 14b; the close review's M1 and the liquid-emptying report,
docs/superpowers/research/2026-10-16-game-feel/liquid-emptying-report.md section 7).

A fresh record (its seed plate at 07:00: 514 kcal, 501 since the hunger curve's re-fit moved the curve's
inverse), then a 667 kcal plate and the guide's 500 g of water at 08:00, run
through the mod's server pipeline on the lupa host (tools/mod_guide_series.server_run). The stomach's mass each minute
(both lanes, K.stomach.mass's keys) is read through K.view.fullnessLevel, the level the Overfull moodle shows. Before
the liquid lane read only drink-borne kcal, the water sat beside the plate at a half-time of about 85 min and held
Overfull 4 for 23 minutes (26 at level 3, 28 at 2, 30 at 1); it now leaves at water's 13 min, and the peak stays,
since the 500 g lands in one minute.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
import mod_guide_series as S  # noqa: E402

MASS_KEYS = ("water", "proteins", "carbs", "lipids", "fibre")


@pytest.fixture(scope="module")
def day():
    paths = ["stomach.liquid"] + ["stomach.buffer." + k for k in MASS_KEYS]
    ev = [S.FRESH, S.plate_meal(60, 667.0), {"minute": 60, "kind": "autodrop", "g": S.AUTODROP_G}]
    rows, be = S.server_run(ev, 300, paths)
    K = be.K
    masses = [r["stomach.liquid"] + sum(r["stomach.buffer." + k] for k in MASS_KEYS) for r in rows]
    levels = [int(K.view.fullnessLevel(m)) for m in masses]
    return masses, levels


def test_the_ordinary_day_spends_five_minutes_at_overfull_4(day):
    _, levels = day
    exact = {lv: sum(1 for x in levels if x == lv) for lv in (1, 2, 3, 4)}
    # 23, 26, 28 and 30 under the plate-kcal rule; level 3 read 6 before the curve's re-fit (a 514 kcal seed plate)
    # Plan 16 Task 4: a sleep-off server has no hunger rhythm, so the 07:00 seed plate is no longer sized under the
    # morning trough's factor and lands larger: 5, 5, 8 and 13 before
    assert exact == {4: 6, 3: 6, 2: 9, 1: 14}


def test_the_peak_is_the_drink_landing_whole(day):
    masses, _ = day
    assert max(masses) == pytest.approx(1239.23, abs=0.01)    # 1206.96 before Plan 16 Task 4 (the seed plate under the morning trough), 1214.80 before the re-fit
    assert max(masses) > 1100                        # past the 1100 g hard capacity for the landing minute
