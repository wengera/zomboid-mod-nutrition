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


def test_x332_hunger_over_the_dry_canteen_refill_is_within_tolerance():
    if not os.path.isdir(X332):
        pytest.skip("the artifact is not in this tree")

    def rd(name):
        with open(os.path.join(X332, name + ".json"), encoding="utf-8") as fh:
            return json.load(fh)

    pages = sorted(glob.glob(os.path.join(X332, "minute-ring-admin-*.json")),
                   key=lambda f: int(f.rsplit("-", 1)[1].split(".")[0]))
    ring, rp = RL.load_ring(pages)
    events = []
    n = 0
    for e in rd("events"):
        if e.get("label") == "autodrop":
            events.append({"s": e["s"], "kind": "autodrop", "g": e["vec"]["water"], "label": "autodrop"})
            n += 1
        else:
            events.append(e)
    assert n >= 1
    kw = dict(paths=rp, user="admin", player=rd("player"), start_stats=rd("start-stats"), sleep_allowed=False)
    old, _ = RL.replay_live(ring, rd("events"), rd("start"), **kw)
    new, _ = RL.replay_live(ring, events, rd("start"), **kw)
    live = {r["s"]: r for r in ring}

    def worst(rows, f="HUNGER"):
        d = [abs(r[f] - live[r["s"]][f]) for r in rows
             if 1033 <= r["s"] <= 1049 and not r.get("between") and not r.get("suspect") and not r.get("offline")
             and r.get(f) is not None and live.get(r["s"], {}).get(f) is not None]
        return max(d)
    # Plan 11g Task 4: the artifact's ring was taken on the P model (its start record's satiety.P is no longer loaded,
    # so the replay seeds G from HUNGER), and HUNGER no longer replays within DEFAULT_TOL: on the P model the drink
    # event ran ahead (0.00495, over the tolerance) and the autodrop event held it (0.00055 measured with a setpath
    # stand-in; this test at 0f14044f). The order is read off the liquid lane, which the satiety model does not enter;
    # HUNGER's distance under G is pinned as a reading until a live run on G (Plan 11g Task 8)
    assert worst(old, "stomach.liquid") > 50.0                     # the drink event runs a minute ahead: 73 g
    assert worst(new, "stomach.liquid") < 1e-9                     # the autodrop lands where the mod lands it
    # stomachFill weighs the liquid lane at LIQUID_WEIGHT, which Plan 11g Task 6 refit (0.2 to 0.181397): the ring's
    # fill was taken at 0.2, so the autodrop's fill now reads a little under the ring's, a reading
    assert worst(old, "stomachFill") > 0.2 and round(worst(new, "stomachFill"), 4) == 0.022
    assert (round(worst(old), 4), round(worst(new), 4)) == (0.149, 0.1504)   # the P ring against the fitted G: readings (0.0514, 0.0536 under its provisional constants)
