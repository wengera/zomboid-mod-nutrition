"""Offline tests of testing/experiments/x42c_calib_lib.py (Plan 13 Task 1, run x423): the session body run against a fake
world behind a fake bus, once as predicted and once per defect flag that must move a grade off as_predicted.

The fake bus answers the harness's real reply shapes, read off the handlers' `@reply` lines
(testing/PZTestKit/PZTestKit/42/media/lua): perk.xp {perk, user, side, xp, level, serverWorldAge}; perk.set {perk,
requested, side, before, ..., after, route}; nutrition.set / nutrition.get {calories, carbs, lipids, proteins, ...};
stats.setany {ok, stat, side, requested, before, after}; stats.get {..., proteins, endurance, moodles, maxWeight, moving,
worldAge, wall}; witness.chain {ok, value, hops, failedAt} with a nil end read as the string "nil" (x422's recorded
S7_push_exe polls); exercise.do {ok, exercise, minutes, queued, queueLen}; action.cancel {ok, before, after, current,
started, adding, stopped, javaBefore, javaAfter, cleared}; inventory.add {ok, fullType, count, side, invWeight,
maxWeight}; player.walk {dx, dy, run, from, target, queued}; attack.melee {ok, target, swings, weapon, result, file} |
{ok, reason}; lua.read {ok, side, root, n, values, tables, types, missing}; lua.call {ok, side, path, nargs, r1};
players a list of usernames; time.snapshot {worldAge, hour, minutes, mult, trueMult, wall}. The attack-melee result
document is {n, swings, targetDead, returns} (PZTestKit_Client.lua attackOnTick).
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                                  # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x42c_calib_lib as L            # noqa: E402
import xlib as X                      # noqa: E402

REP_S = 1.3


def fresh_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {},
            "world_changes": {"left_in_place": []}}


class FakeBus:
    def __init__(self, world):
        self.w = world

    def wait_result(self, name, timeout=10, after=0.0):
        w = self.w
        w.sleep(L.MELEE_SWINGS * 1.2)
        return w.melee_result


class FakeClient:
    def __init__(self, world):
        self.bus = FakeBus(world)
        self.seen = {}
        self.username = "admin"


class World:
    def __init__(self, flags):
        self.f = flags
        self.now = 1000.0
        self.last_tick = self.now
        self.xp = 487500.0 if flags.get("at_cap") else 37500.0
        self.level = 5
        self.protein = 120.0
        self.endurance = 0.6
        self.exe_until = None       # the set's server flag
        self.exe_start_pending = None
        self.next_rep = None
        self.moving_until = 0.0
        self.inv = 2.0
        self.max_w = 8.0
        self.next_roll = None
        self.zombie_at = None
        self.melee_result = None
        self.events, self.calls, self.dropped = [], 0, 0

    # -- the clock
    def clock(self):
        return self.now

    def sleep(self, s):
        end = self.now + max(0.0, s)
        while self.now < end:
            self.now = min(end, self.now + 0.1)
            self.tick()

    def tick(self):
        if self.exe_start_pending is not None and self.now >= self.exe_start_pending:
            self.exe_start_pending = None
            self.exe_until = self.now + 10000.0
            self.next_rep = self.now + REP_S
        if self.exe_until is not None:
            if self.f.get("self_end") and self.endurance < 0.3:
                self.exe_until = None
            elif self.next_rep is not None and self.now >= self.next_rep:
                self.next_rep += REP_S
                self.endurance -= 0.015
                if self.xp < L.CAP_XP:
                    if not self.f.get("silent_pushups"):
                        amt = 6.0 * L.protein_factor(self.protein)
                        if self.f.get("wrong_amount"):
                            amt = 4.0
                        self.addxp("Strength", amt)
                    self.addxp("Fitness", 0.0)
        moving = self.now < self.moving_until and not self.f.get("no_move")
        if moving and self.inv > 0.5 * self.max_w:
            if self.next_roll is None:
                self.next_roll = self.now + 10.0
            if self.now >= self.next_roll:
                self.next_roll += 10.0
                if not self.f.get("silent_walk") and self.xp < L.CAP_XP:
                    self.addxp("Strength", 2.0)

    def addxp(self, perk, amount):
        self.calls += 1
        if perk == "Strength":
            self.xp += amount
        if len(self.events) >= L.EVENT_CAP - (self.f.get("dropped") and L.EVENT_CAP - 20 or 0):
            self.dropped += 1
            return
        self.events.append({"user": "admin", "perk": perk, "amount": amount, "ms": int(self.now * 1000),
                            "protein": self.protein, "fitness": self.exe_until is not None, "level": self.level,
                            "xp": self.xp})

    # -- the bus
    def g(self):
        ev = {i + 1: e for i, e in enumerate(self.events)}
        return {"TKX_TraitLevers": {"server": True, "newGame": {"count": 0},
                                    "xp": {"n": len(self.events), "calls": self.calls, "dropped": self.dropped,
                                           "ev": ev}},
                "SandboxVars": {"MultiplierConfig": {"Global": 1.0, "GlobalToggle": True, "Strength": 1.0},
                                "Nutrition": False, "DayLength": 1}}

    def lread(self, args, side):
        parts = args.split()
        paths = parts[1:]
        out = {"ok": True, "side": side, "root": parts[0], "n": len(paths), "values": {}, "tables": {}, "types": {},
               "missing": {}}
        for p in paths:
            node = self.g()
            for seg in p.split("."):
                if isinstance(node, dict):
                    node = node.get(seg, node.get(int(seg)) if seg.isdigit() else node.get(seg))
                else:
                    node = None
            if node is None or isinstance(node, dict):
                out["missing"][p] = True
            else:
                out["values"][p] = node
        return out

    def body(self):
        return {"proteins": self.protein, "endurance": self.endurance, "maxWeight": self.max_w,
                "moodles": {"endurance": 0 if self.endurance > 0.75 else 3 if self.endurance < 0.25 else 1,
                            "heavyLoad": 3 if self.inv > self.max_w else 0},
                "moving": self.now < self.moving_until and not self.f.get("no_move"), "worldAge": 100.0,
                "wall": self.now}

    def ask(self, node, cmd, args="", timeout=30):
        self.sleep(0.05)
        a = args.split()
        if cmd == "ping":
            return "pong"
        if cmd == "players":
            return ["admin"]
        if cmd == "time.snapshot":
            return {"worldAge": 100.0, "hour": 9, "minutes": 0, "mult": 1.0, "trueMult": 1.0, "wall": self.now}
        if cmd == "lua.read":
            return self.lread(args, node)
        if cmd == "lua.call":
            if a[0] == "TKX_TraitLevers.xpReset":
                self.events, self.calls, self.dropped = [], 0, 0
            return {"ok": True, "side": node, "path": a[0], "nargs": len(a) - 1, "r1": True}
        if cmd == "perk.xp":
            return {"perk": a[-1], "user": "admin", "side": node, "xp": self.xp, "level": self.level,
                    "serverWorldAge": 100.0}
        if cmd == "perk.set":
            if not self.f.get("park_fails"):
                self.xp, self.level = 37500.0, 5
            return {"perk": a[1], "requested": int(a[2]), "side": node, "before": 10, "after": self.level,
                    "route": "both"}
        if cmd == "nutrition.set":
            if not self.f.get("protein_high"):
                self.protein = float(a[2])
            return {"calories": 0, "carbs": 0, "lipids": 0, "proteins": self.protein, "weight": 80}
        if cmd == "nutrition.get":
            return {"calories": 0, "carbs": 0, "lipids": 0, "proteins": self.protein, "weight": 80}
        if cmd == "stats.setany":
            before = self.endurance
            self.endurance = float(a[2])
            return {"ok": True, "stat": a[1], "side": node, "requested": float(a[2]), "before": before,
                    "after": self.endurance}
        if cmd == "stats.get":
            return self.body()
        if cmd == "witness.chain":
            chain = a[-1]
            if chain == "getFitness.getCurrentExe":
                return {"ok": True, "value": "zombie.characters.Fitness$FitnessExercise@1"
                        if self.exe_until is not None else "nil", "hops": 2}
            if chain == "getInventoryWeight":
                return {"ok": True, "value": self.inv, "hops": 1}
            if chain == "getRole.getName":
                return {"ok": True, "value": "admin", "hops": 2}
            return {"ok": False, "failedAt": 1}
        if cmd == "exercise.do":
            if not self.f.get("set_never"):
                self.exe_start_pending = self.now + 1.0
            return {"ok": True, "exercise": a[0], "minutes": int(a[1]), "queued": True, "queueLen": 1}
        if cmd == "action.cancel":
            was = 1 if (self.exe_until is not None or self.now < self.moving_until) else 0
            self.exe_until = None
            self.moving_until = self.now
            return {"ok": True, "before": was, "after": 0, "started": bool(was), "adding": False, "stopped": True,
                    "javaBefore": was, "javaAfter": 0, "cleared": True}
        if cmd == "inventory.add":
            self.inv += 6.0
            return {"ok": True, "fullType": a[1], "count": 1, "side": node, "invWeight": self.inv,
                    "maxWeight": self.max_w}
        if cmd == "player.walk":
            self.moving_until = self.now + 8.0
            return {"dx": int(a[0]), "dy": 0, "run": False, "target": {}, "queued": True}
        if cmd == "attack.melee":
            if self.zombie_at is None or self.now < self.zombie_at:
                return {"ok": False, "reason": "no zombie within 2 tiles"}
            if not self.f.get("no_hit"):
                if not self.f.get("silent_melee"):
                    self.addxp("Strength", 1.0)
                    self.addxp("Strength", 2.0)
                self.addxp("Blunt", 2.5)
            self.melee_result = {"n": int(a[0]), "swings": int(a[0]), "targetDead": not self.f.get("no_hit"),
                                 "returns": {}}
            return {"ok": True, "target": {"x": 1, "y": 1, "dist": 1.0}, "swings": int(a[0]),
                    "weapon": "Base.BaseballBat", "result": "attack-melee", "file": "pzt-results/attack-melee.json"}
        return {"error": f"fake bus: no {cmd}"}


class FakeServer:
    def __init__(self, world):
        self.w = world

    def rcon(self, cmd):
        if not self.w.f.get("no_zombie"):
            self.w.zombie_at = self.w.now + 3.0
        return True, "Horde spawned"


def run(flags=None):
    w = World(flags or {})
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, ask=w.ask, budget_s=5000.0, clock=w.clock, sleep=w.sleep,
              clients={"admin": FakeClient(w)}, server=FakeServer(w), user="admin")
    cb = L.Calib(xs)
    cb.body()
    cb.grade_all()
    return out, w


def verdicts(out):
    return {k: v["verdict"] for k, v in out["verdicts"].items()}


def test_fixed_world_is_as_predicted():
    out, w = run()
    assert verdicts(out) == {"pushups": "as_predicted", "7_walk": "as_predicted", "7_melee": "as_predicted"}
    assert out["phase_errors"] == {}
    r = out["reading"]
    # 0.6 -> 0.25 at 0.015 a rep with the stop at the first read at or under 0.25
    assert r["reps"] >= 23 and r["xp_per_set"] == pytest.approx(6.0 * r["reps"])
    assert r["xp_delta"] == pytest.approx(r["xp_per_set"])
    assert r["set_s"] > 20 and r["xp_per_s"] == pytest.approx(r["xp_per_set"] / r["set_s"])
    assert out["checks"]["pushups"]["stop_reason"] == "endurance"
    assert out["checks"]["pushups"]["exe_cleared"] is True
    assert out["checks"]["walk"]["move_cleared"] is True


def test_self_ending_set_is_read_as_ended():
    out, _ = run({"self_end": True})
    assert out["checks"]["pushups"]["stop_reason"] == "ended"
    assert "cancel" not in out["checks"]["pushups"]
    assert verdicts(out)["pushups"] == "as_predicted"


def test_zero_events_falsifies_the_set():
    out, _ = run({"silent_pushups": True})
    assert verdicts(out)["pushups"] == "falsified"
    assert out["verdicts"]["pushups"]["observed"]["reps"] == 0


def test_an_amount_off_six_falsifies_and_is_listed():
    out, _ = run({"wrong_amount": True})
    o = out["verdicts"]["pushups"]["observed"]
    assert verdicts(out)["pushups"] == "falsified"
    assert o["n_mismatches"] == o["reps"] > 0
    assert o["xp_per_set"] == pytest.approx(4.0 * o["reps"])     # reported, never dropped


def test_a_store_outside_the_neutral_window_is_unmeasured_and_listed():
    out, _ = run({"protein_high": True})
    o = out["verdicts"]["pushups"]["observed"]
    assert verdicts(out)["pushups"] == "unmeasured"
    assert o["n_outside"] == o["reps"] > 0
    assert o["xp_per_set"] == pytest.approx(6.0 * o["reps"])     # each 9 / 1.5


def test_the_cap_at_the_open_is_unmeasured_everywhere():
    out, _ = run({"at_cap": True, "park_fails": True})
    assert verdicts(out) == {"pushups": "unmeasured", "7_walk": "unmeasured", "7_melee": "unmeasured"}


def test_the_cap_is_parked_before_the_window():
    out, _ = run({"at_cap": True})
    g = out["checks"]["pushups"]["gate"]
    assert g["parked"] is True and g["xp_open"] < L.CAP_XP
    assert verdicts(out)["pushups"] == "as_predicted"


def test_a_set_never_seen_is_unmeasured():
    out, _ = run({"set_never": True})
    assert verdicts(out)["pushups"] == "unmeasured"
    assert out["checks"]["pushups"]["stop_reason"] == "never_started"


def test_dropped_records_are_unmeasured():
    out, _ = run({"dropped": True})
    assert verdicts(out)["pushups"] == "unmeasured"


def test_silent_walk_falsifies():
    out, _ = run({"silent_walk": True})
    assert verdicts(out)["7_walk"] == "falsified"


def test_a_walk_that_never_moves_is_unmeasured():
    out, _ = run({"no_move": True, "silent_walk": True})
    assert verdicts(out)["7_walk"] == "unmeasured"


def test_silent_melee_with_a_hit_falsifies():
    out, _ = run({"silent_melee": True})
    assert verdicts(out)["7_melee"] == "falsified"


def test_no_zombie_is_unmeasured():
    out, _ = run({"no_zombie": True})
    assert verdicts(out)["7_melee"] == "unmeasured"
    assert out["checks"]["melee"]["misses"] > 0


def test_swings_without_a_hit_are_unmeasured():
    out, _ = run({"no_hit": True})
    assert verdicts(out)["7_melee"] == "unmeasured"


def test_pure_grades_on_empty_input():
    assert L.grade_pushups({})[0] == "unmeasured"
    assert L.grade_walk({})[0] == "unmeasured"
    assert L.grade_melee({})[0] == "unmeasured"


def test_protein_factor_and_window():
    assert L.protein_factor(0) == 1.0 and L.protein_factor(120) == 1.5 and L.protein_factor(-400) == 0.7
    assert L.neutral(0) and L.neutral(-300) and L.neutral(50) and not L.neutral(51) and not L.neutral(-301)


def test_event_read_paging_stays_under_64_paths():
    out, _ = run()
    for s in out["steps"]:
        if s["cmd"] == "lua.read":
            assert len(s["args"].split()) - 1 <= 64
