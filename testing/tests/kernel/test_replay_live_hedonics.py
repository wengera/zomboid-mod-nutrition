"""tools/replay_live.py carries the food hedonics rows (Plan 19 Task 6): each logged eat names its plain flag (rule R1)
and taste class (R4), a dish eat takes its ingredient list (extraTypes), and every server row carries the ring's
plain share and the floor the writer composed (hedonics.share, hedonics.f), so a live run with plain eats replays
the floor exactly. The replay runs the mod's own server adapters, so the booking and the floor are the mod's."""
import os
import sys

import pytest

from .server_host import REPO

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

START = {"username": "admin", "firstSeen": 99.0, "lastSeen": 99.0, "satiety": {"M": 10.0, "S": 0, "L": 0, "t": 99.0}}
LARD = {"calories": 3000.0, "proteins": 0.0, "carbs": 0.0, "lipids": 333.0, "water": 0.0}


def test_a_plain_eat_logs_its_flag_and_class_and_the_rows_carry_the_floor():
    # mutation: the writer's floor left uncomposed (or the ring never booked) reads hedonics.f 0 here
    rp = RL.ServerReplay(start=dict(START))
    rp.step(100.0)
    rp.apply({"kind": "eat", "vec": LARD, "fullType": "Base.Lard"}, 100.0)
    assert rp.eats[-1]["plain"] is True and rp.eats[-1]["class"] == "fatty"
    rp.step(100.0 + 1 / 60.0)
    row = rp.row(())
    assert row["hedonics.share"] == pytest.approx(1.0)
    assert row["hedonics.f"] == pytest.approx(rp.K.hedonics.floorOf(1.0)) and row["hedonics.f"] > 0


def test_an_eat_with_no_plain_energy_logs_false_and_its_class():
    rp = RL.ServerReplay(start=dict(START))
    v = {"calories": 450.0, "proteins": 16.875, "carbs": 56.25, "lipids": 17.5, "water": 200.0}
    rp.apply({"kind": "eat", "vec": v, "fullType": "Base.Carrots"}, 100.0)
    assert rp.eats[-1]["plain"] is False and rp.eats[-1]["class"] == "savoury"
    rp.apply({"kind": "drink", "fluid": "Water", "litres": 0.3}, 100.0)
    assert rp.eats[-1]["kind"] == "drink" and "plain" not in rp.eats[-1]     # a drink books no hedonics


def test_a_dish_eat_takes_its_ingredient_list():
    rp = RL.ServerReplay(start=dict(START))
    rp.apply({"kind": "eat", "fullType": "Base.Butter", "cal": 120.0, "carb": 12.0, "lip": 6.0, "pro": 4.0,
              "hunger": -0.2, "extraTypes": ["Base.Carrots", "Base.Carrots", "Base.Carrots", "Base.BaconRashers"]},
             100.0)
    assert rp.eats[-1]["plain"] is False and rp.eats[-1]["class"] == "savoury"
    assert rp.record().lastIntake.source == "dish"
