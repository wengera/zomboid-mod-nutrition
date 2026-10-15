"""Offline tests of testing/experiments/x42e_melee_lib.py (Plan 13 Task 1, run x425): x42d's melee fake world with the
bat added through RCON additem (reaching the client after a delay) instead of the server's inventory.add; once as
predicted and once per defect flag that must move the grade off as_predicted.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                                  # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x42e_melee_lib as E            # noqa: E402
import xlib as X                      # noqa: E402
from test_x42c_calib_lib import FakeClient, fresh_out   # noqa: E402
from test_x42d_melee_lib import MeleeWorld              # noqa: E402


class RconServer:
    def __init__(self, world):
        self.w = world

    def rcon(self, cmd):
        w = self.w
        if cmd.startswith("additem"):
            if not w.f.get("additem_lost"):
                w.bat_at = w.now + 1.5
            return True, "Item added"
        if not w.f.get("no_zombie") and w.zombie_at is None:
            w.zombie_at = w.now + (70.0 if w.f.get("slow_zombie") else 3.0)
        return True, "Horde spawned."


class RconWorld(MeleeWorld):
    def __init__(self, flags, log):
        super().__init__(flags, log)
        self.bat_at = None

    def tick(self):
        super().tick()
        if self.bat_at is not None and self.now >= self.bat_at:
            self.has_bat = True


def run(tmp_path, flags=None):
    w = RconWorld(flags or {}, str(tmp_path / "server-stdout.log"))
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, ask=w.ask, budget_s=5000.0, clock=w.clock, sleep=w.sleep,
              clients={"admin": FakeClient(w)}, server=RconServer(w), user="admin")
    mm = E.Melee(xs, log_path=w.log)
    mm.body()
    mm.grade_all()
    return out


def v(out):
    return out["verdicts"]["7_melee"]["verdict"]


def test_fixed_world_is_as_predicted(tmp_path):
    out = run(tmp_path)
    assert v(out) == "as_predicted" and out["phase_errors"] == {}
    assert out["checks"]["equip"]["on_server"] is True
    assert out["checks"]["equip"]["equip"]["ok"] is True


def test_a_slow_zombie_inside_the_search_is_found(tmp_path):
    out = run(tmp_path, {"slow_zombie": True})
    assert v(out) == "as_predicted"
    assert len(out["checks"]["melee"]["hordes"]) >= 2


def test_a_lost_additem_is_unmeasured(tmp_path):
    out = run(tmp_path, {"additem_lost": True, "dead_no_events": True})
    assert v(out) == "unmeasured"
    assert out["checks"]["equip"]["equip"]["ok"] is False


def test_weapon_hit_without_strength_falsifies(tmp_path):
    assert v(run(tmp_path, {"silent_melee": True})) == "falsified"


def test_inconsistent_packets_are_unmeasured(tmp_path):
    assert v(run(tmp_path, {"inconsistent": True})) == "unmeasured"


def test_no_zombie_is_unmeasured(tmp_path):
    out = run(tmp_path, {"no_zombie": True})
    assert v(out) == "unmeasured"
    assert len(out["checks"]["melee"]["hordes"]) <= E.HORDE_MAX
