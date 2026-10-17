"""The replay's `autodrop` event kind (Plan 11f ruling T9-4, finding F-T9-4).

The live libs once injected the writer's auto-drink sip as a `drink` event, landed through IN.land before the drain,
while the mod lands fluids.autoDrop in the Nutrients step AFTER Kinetics has emptied the stomach that minute
(NR_Server_Minute.lua:18, NR_Server_Kinetics.lua:91-95, NR_Server_Nutrients.lua:423-433). `autodrop` {g} adds the
water mass to the record's fluids.autoDrop before the drain, so the mod's own Nutrients step lands it at its own point."""
import glob
import json
import os
import sys

import pytest

from . import at_build
from .server_host import REPO

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

X332 = os.path.join(REPO, "testing", "artifacts", "x332-20261011-141601")
LIQ = "stomach.liquid"


def synthetic_ring(n=8, dtm=1.0):
    return [{"s": i + 1, "ev": i + 1, "drained": i, "age": 100.0 + i * dtm / 60.0, "dtM": dtm,
             "hour": int((8 + i * dtm / 60.0) % 24), "min": int((i * dtm) % 60), "on": True} for i in range(n)]


def replay(events):
    rows = synthetic_ring()
    out, be = RL.replay_live(rows, events, None, paths=[LIQ, "fluids.autoDrop"], hour_offset=8.0 - 100.0 % 24,
                             sleep_allowed=True)
    return out, be


def test_autodrop_lands_its_grams_after_the_drain_untouched():
    g = 900.0
    out, _ = replay([{"s": 3, "kind": "autodrop", "g": g}])
    by_k = {r["k"]: r for r in out}
    assert by_k[1][LIQ] in (None, 0)
    assert by_k[2][LIQ] == pytest.approx(g, abs=1e-6)       # live's order: Kinetics drained first, the sip lands after
    assert by_k[2]["fluids.autoDrop"] == 0                  # the Nutrients step consumed it
    assert by_k[3][LIQ] < g                                 # emptied from the next drain on


def test_a_drink_event_lands_before_the_drain_and_runs_one_minute_ahead():
    g = 900.0
    drink, _ = replay([{"s": 3, "kind": "drink", "vec": {"water": g}}])
    auto, _ = replay([{"s": 3, "kind": "autodrop", "g": g}])
    assert drink[2][LIQ] < auto[2][LIQ] - 1.0
    assert drink[3][LIQ] < auto[3][LIQ]


def test_autodrop_marks_the_row_before_it_between_like_any_event():
    out, _ = replay([{"s": 3, "kind": "autodrop", "g": 100.0}])
    assert [r["between"] for r in out[:4]] == [False, True, False, False]


def test_autodrop_refuses_a_bad_mass():
    for ev in ({"s": 3, "kind": "autodrop"}, {"s": 3, "kind": "autodrop", "g": -5.0},
               {"s": 3, "kind": "autodrop", "g": "x"}):
        with pytest.raises(ValueError, match="autodrop"):
            replay([ev])


def test_x332_hunger_over_the_dry_canteen_refill_is_within_tolerance(tmp_path):
    # Plan 15 Task 14b: x332's ring ran the old liquid lane (slowed by the solid lane's whole kcal), so its replay
    # readings (0.04, 0.0465 HUNGER; the liquid order; the 0.7972 fill) hold on the build before that change and are
    # re-run there, frozen, never re-pinned at HEAD (CLAUDE.md § 5)
    if not os.path.isdir(X332):
        pytest.skip("the artifact is not in this tree")
    code, out = at_build.run(tmp_path, at_build.PRE_LIQUID_LANE,
                             "testing/tests/kernel/test_replay_live_autodrop.py::"
                             "test_x332_hunger_over_the_dry_canteen_refill_is_within_tolerance",
                             ("testing/artifacts/x332-20261011-141601",))
    assert code == 0 and " passed" in out, out
