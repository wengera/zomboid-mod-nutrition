"""Offline tests of testing/experiments/x42d_melee_lib.py (Plan 13 Task 1, run x424): the melee window run against the
fake world of test_x42c_calib_lib.py, extended with the harness's weapon.equip ({ok, fullType, itemId, twoHands,
queued}, PZTestKit_Client.lua's @reply line), the primary-hand read through witness.chain ({ok, value, hops}) and a
server log that holds x423's inconsistent-packet line when the hit is rejected; once as predicted and once per defect
flag that must move the grade off as_predicted.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                                  # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x42d_melee_lib as M            # noqa: E402
import xlib as X                      # noqa: E402
from test_x42c_calib_lib import FakeClient, FakeServer, World, fresh_out   # noqa: E402

LINE = ('WARN : Multiplayer  f:3445 st:2,394,783,009 at INetworkPacket.logInconsistentPacket> The packet '
        'PlayerHitZombie is not consistent: { "weapon" : { "Weapon": { "weapon" : null } } }\n')


class MeleeWorld(World):
    def __init__(self, flags, log):
        super().__init__(flags)
        self.log = log
        self.hand_server = None
        self.hand_client = None
        self.has_bat = False
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("LOG  : General boot\n")

    def ask(self, node, cmd, args="", timeout=30):
        a = args.split()
        if cmd == "inventory.add" and a[1] == M.WEAPON:
            self.sleep(0.05)
            self.has_bat = True
            return {"ok": True, "fullType": a[1], "count": 1, "side": node, "invWeight": 3.0, "maxWeight": 12}
        if cmd == "weapon.equip":
            self.sleep(0.05)
            if not self.has_bat:
                return {"ok": False, "fullType": a[0], "queued": False, "reason": "no item"}
            self.hand_client = a[0]
            if not self.f.get("no_equip"):
                self.hand_server = a[0]
            return {"ok": True, "fullType": a[0], "itemId": 77, "twoHands": True, "queued": True}
        if cmd == "witness.chain" and a[-1] == "getPrimaryHandItem.getFullType":
            self.sleep(0.05)
            v = self.hand_server if node == "server" else self.hand_client
            return {"ok": True, "value": v if v else "nil", "hops": 2}
        if cmd == "attack.melee":
            self.sleep(0.05)
            if self.zombie_at is None or self.now < self.zombie_at:
                return {"ok": False, "reason": "no zombie within 2 tiles"}
            f = self.f
            if f.get("inconsistent"):
                with open(self.log, "a", encoding="utf-8") as fh:
                    fh.write(LINE)
            elif not f.get("no_hit") and not f.get("dead_no_events"):
                if not f.get("silent_melee"):
                    self.addxp("Strength", 1.0)
                    self.addxp("Strength", 2.0)
                self.addxp("LongBlunt", 2.5)
            self.melee_result = {"n": int(a[0]), "swings": int(a[0]) - 1, "targetDead": not f.get("no_hit"),
                                 "returns": {}}
            return {"ok": True, "target": {"x": 1, "y": 1, "dist": 0.5}, "swings": int(a[0]),
                    "weapon": M.WEAPON, "result": "attack-melee", "file": "pzt-results/attack-melee.json"}
        return super().ask(node, cmd, args, timeout)


def run(tmp_path, flags=None):
    w = MeleeWorld(flags or {}, str(tmp_path / "server-stdout.log"))
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, ask=w.ask, budget_s=5000.0, clock=w.clock, sleep=w.sleep,
              clients={"admin": FakeClient(w)}, server=FakeServer(w), user="admin")
    mm = M.Melee(xs, log_path=w.log)
    mm.body()
    mm.grade_all()
    return out


def v(out):
    return out["verdicts"]["7_melee"]["verdict"]


def test_fixed_world_is_as_predicted(tmp_path):
    out = run(tmp_path)
    assert v(out) == "as_predicted"
    assert out["phase_errors"] == {}
    assert out["checks"]["equip"]["on_server"] is True
    o = out["verdicts"]["7_melee"]["observed"]
    assert o["strength_sum"] == 3.0 and o["inconsistent_lines"] == 0 and o["xp_delta"] == 3.0


def test_weapon_not_on_server_is_unmeasured(tmp_path):
    assert v(run(tmp_path, {"no_equip": True, "dead_no_events": True})) == "unmeasured"


def test_inconsistent_packets_are_unmeasured_not_falsified(tmp_path):
    out = run(tmp_path, {"inconsistent": True})
    assert v(out) == "unmeasured"
    assert out["verdicts"]["7_melee"]["observed"]["inconsistent_lines"] >= 1


def test_weapon_hit_without_strength_falsifies(tmp_path):
    assert v(run(tmp_path, {"silent_melee": True})) == "falsified"


def test_dead_target_clean_log_no_events_falsifies(tmp_path):
    assert v(run(tmp_path, {"dead_no_events": True})) == "falsified"


def test_no_zombie_is_unmeasured(tmp_path):
    assert v(run(tmp_path, {"no_zombie": True})) == "unmeasured"


def test_no_hit_is_unmeasured(tmp_path):
    assert v(run(tmp_path, {"no_hit": True})) == "unmeasured"


def test_cap_is_unmeasured(tmp_path):
    assert v(run(tmp_path, {"at_cap": True, "park_fails": True})) == "unmeasured"


def test_pure_grade_on_empty_input():
    assert M.grade_melee2({})[0] == "unmeasured"
