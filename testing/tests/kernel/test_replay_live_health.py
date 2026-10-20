"""The replay host's health (Plan 17 Task 4): every server row carries the stand-in's overall health, its start the
player config's `health` (else 100), less what the mod's drain takes through ReduceGeneralHealth plus what
AddGeneralHealth gives back; `game_heal` gives that add the game's spread, 5.05 / 17 of the argument (#3898), as the
mod's heal assumes and the guide's replay already does. A live ring's `health` field (the harness's Plan 17 Task 4
wrap) is compared with it, so the drain's live readings (x481, x482) grade health against the HEAD replay."""
import os
import sys

import pytest

from .server_host import REPO

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

START = 2.39
R90 = 0.0396 * 90                        # vanilla's hunger level-4 drain a game hour at the 90-minute day (#0516)


def starve_events(at_minute, lead_h=0.02):
    """satiety.M 0 then the unfed clock past the acute onset (K.drain.STARVE_ONSET_H, 30 h) by lead_h, at one step."""
    age = START + (at_minute + 1) / 60.0
    return [{"minute": at_minute, "kind": "setpath", "path": "satiety.M", "value": 0},
            {"minute": at_minute, "kind": "setpath", "path": "drain.fedAgeH", "value": age - 30.0 - lead_h}]


def test_every_row_carries_the_start_health_and_no_drain_moves_it():
    rows, be = RL.replay_arm([], minutes=5, start_age=START, paths=("drain.active",), sleep_allowed=False,
                             player={"health": 61.5})
    assert [r["health"] for r in rows] == [61.5] * 5
    rows, _ = RL.replay_arm([], minutes=2, start_age=START, sleep_allowed=False)
    assert rows[0]["health"] == 100.0                              # no player health: the stand-in's 100


def test_a_vanilla_add_starvation_takes_health_down_the_target_at_vanillas_rate():
    rows, be = RL.replay_arm(starve_events(3), minutes=40, start_age=START, sleep_allowed=False,
                             paths=("drain.target", "drain.active", "drain.state"), death_pace=1, health_combine=3)
    on = [r for r in rows if r.get("drain.active") is True]
    assert len(on) >= 30 and on[0]["k"] == 3
    for r in on:
        assert r["health"] == pytest.approx(r["drain.target"], abs=1e-9)        # the line never outruns its cap
    per_min = [a["health"] - b["health"] for a, b in zip(on, on[1:])]
    assert per_min and all(d == pytest.approx(R90 / 60.0, rel=1e-9) for d in per_min)
    assert all(r["health"] == 100.0 for r in rows[:3])


def test_game_heal_spreads_the_add_and_the_default_adds_in_full():
    for heal, want in ((True, 5.05 / 17.0), (False, 1.0)):
        rows, be = RL.replay_arm([], minutes=1, start_age=START, sleep_allowed=False, player={"health": 50.0},
                                 game_heal=heal)
        bd = be.p.getBodyDamage(be.p)
        bd.AddGeneralHealth(bd, 1.0)
        assert be.row(())["health"] == pytest.approx(50.0 + want, abs=1e-12)


def test_replay_live_passes_game_heal_to_its_backend():
    ring = [{"s": 1, "age": START + 1 / 60.0, "on": True}, {"s": 2, "age": START + 2 / 60.0, "on": True}]
    for heal in (True, False):
        rows, be = RL.replay_live(ring, [], None, sleep_allowed=False, game_heal=heal)
        assert be.game_heal is heal and rows[0]["health"] == 100.0
