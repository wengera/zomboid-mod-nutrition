"""Offline tests of testing/experiments/x45g_lib.py (Plan 15 Task 11, runs x452-x457): every grade with a failing case
and its unmeasured case, the pre-boot checks on the real repository, a real run layout and a real staged copy of the
pinned commit, and each session's body run against a fake world behind a fake bus, once as predicted and once per
defect flag that must move a named grade off as_predicted.

The fake bus answers the harness's real reply shapes, read off the handlers' `@reply` lines
(docs/reference/harness-commands.md): time.snapshot {worldAge, hour, minutes, mult, trueMult, wall}; stats.get (both
sides) {calories, ..., hunger, thirst, endurance, fatigue, moodles {hungry, thirst, foodEaten, heavyLoad, endurance},
traits {..., HighThirst, LowThirst}, traitList, foodTimer, worldAge, mult, wall}; stats.all {side, user, worldAge, mult,
wall, stats {Hunger, ..., FoodSickness}, missing}; stats.setany {ok, stat, side, requested, before, after};
health.get {ok, side, overall, health, parts}; health.reduce {ok, side, requested, before, after, health, parts};
moodle.level {ok, side, user, moodle, level}; witness.chain {ok, value, hops, failedAt} with the end value tostring'd;
lua.read {ok, side, root, n, values, tables, types, missing}; lua.global {side, name, resolved, type, value};
lua.call {ok, side, path, nargs, r1, r2, r3}; record.set {ok, side, user, path, key, keyType, before, beforeType,
after, afterType}; trait.set {trait, field, op, before, enumFound, collection, route, after, traitList, held};
bodypart.set {ok, side, part, field, requested, before, after, synced}; item.get the item state dict or the string
"no item ..."; autodrink.probe {ok, side, thirst, autoDrink, containers}; nutrition.get {calories, carbs, lipids,
proteins, weight, hunger, thirst, ...}; eat.action {queued, fraction, spawned, itemId, itemBefore, validStart, maxTime,
moodleFoodEaten, before}; action.cancel {ok, before, after, current, started, adding, stopped, javaBefore, javaAfter,
cleared}; minute.ring start {ok, side, user, armed, cap, paths, stats, online, probe}, read {ok, side, user, from, rows,
skipped, next, more, ..., errors, result, file}, stop {ok, side, user, stopped, recorded, overwritten, errors};
time.multiplier the string "mult=<true> eff=<effective>"; RCON settimespeed and additem as x44's fake.
"""
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x45g_lib as L                  # noqa: E402
import xlib as X                      # noqa: E402

REPO = L.REPO
EFF = 4.75                             # the effective multiplier over the true one (#3762)
FOOD_MASS = {L.BOLOGNESE: {"water": 300.0, "proteins": 23.6, "carbs": 61.83, "lipids": 22.19, "fibre": 4.0},
             L.BANANA: {"water": 88.47, "proteins": 1.29, "carbs": 26.97, "lipids": 0.39, "fibre": 3.07},
             L.BROCCOLI: {"water": 28.93, "proteins": 0.91, "carbs": 2.15, "lipids": 0.12, "fibre": 0.84}}


def fresh_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
            "world_changes": {"left_in_place": []}}


def lvl(v, at):
    return sum(1 for t in at if v > t)


def interp(knots, x):
    if x <= knots[0][0]:
        return knots[0][1]
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return knots[-1][1]


THIRST_KNOTS = ((0, 0), (1, 0.12), (2, 0.25), (3, 0.45), (4, 0.84), (8, 1.0))
HUNGER_AFTER = ((0.0, 0.0), (0.5, 0.0), (3.8, 0.15), (8.0, 0.25), (17.0, 0.45), (40.0, 0.69))


# ---------------------------------------------------------------- the fake world
class FakeBus:
    def __init__(self, results_dir):
        self.results_dir = results_dir

    def wait_result(self, name, timeout=30, after=None):
        with open(os.path.join(self.results_dir, name + ".json"), encoding="utf-8") as fh:
            return json.load(fh)


class FakeServer:
    def __init__(self, world, results_dir):
        self.w = world
        self.errors = []
        self.bus = FakeBus(results_dir)

    def rcon(self, cmd):
        return self.w.rcon(cmd)


class FakeClient:
    def __init__(self, user):
        self.username = user
        self.seen = {}
        self.alive = True
        self.console = os.devnull


class World:
    """A minimal mechanistic stand-in of the mod at DayLength 1: a game hour 37.5 wall s at speed 1, a minute step at
    every game-minute boundary (the stomach's emptying, the meal pool, the drain and its floor, the caps and the
    constant, the re-applied terms, the food timer, the nausea and the endurance ceiling, the water loss by the trait
    scale, the ring row), vanilla's per-tick terms continuous, the client a 0.6 s lagged copy of the server. `flags`
    are defects that must move a named grade."""
    GH_S = 37.5
    STEP_S = 0.1
    LAG_S = 0.6

    def __init__(self, results_dir, flags=()):
        self.dir = results_dir
        self.f = set(flags)
        self.t, self.age, self.speed = 0.0, 3.2, 1.0
        self.health, self.hunger, self.thirst, self.endurance, self.food_sick = 100.0, 0.2, 0.01, 1.0, 0.0
        self.red = L.CONST_DEFAULT
        self.timer = 0.0
        self.traits = set()
        self.parts = {}
        self.inv = {}
        self.eats = self.landed = self.sips = 0
        self.reapplied = 0
        self.writes = 0
        self.ring, self.ring_on, self.s, self.paths = [], False, 0, []
        self.pending = []
        self.meal_age = None
        self.forced_unfed = False
        self.fills = {}
        self.hist = []
        self.scale = 1.0
        self.rec = {"firstSeen": 3.2, "kineticsAge": 3.2, "stomachFill": 0.0,
                    "satiety": {"M": 950.0, "S": 0.0, "L": 0.0, "t": 3.2, "hModel": 0.2},
                    "stomach": {"buffer": {"water": 0.0, "proteins": 0.0, "carbs": 0.0, "lipids": 0.0, "fibre": 0.0,
                                           "calories": 0.0}, "liquid": 0.0, "volX": 0.0},
                    "drain": {"fedAgeH": 3.2, "starvedH": 0.0, "acuteH": 0.0, "starveAcute": False, "starving": False,
                              "active": False, "state": 0, "targetFloor": 100.0, "rate": 0.0, "drainThisMinute": 0.0,
                              "bmi0": 0.0, "recentKcal": None, "dehydrated": False},
                    "body": {"fm": 13.005, "lm": 52.02, "lx": 0.0, "sex": 1, "met": 1.3, "coldMult": 1.0,
                             "energyState": 1.0, "inDay": 0.0, "eeDay": 0.0},
                    "fluids": {"water": -28.0, "dehydPct": 0.04, "thirstTarget": 0.01, "na": 0.0, "k": 0.0,
                               "naPlasma": 140.0, "sweatLmin": 0.0, "autoDrop": 0.0},
                    "effects": {"enduranceCap": 1.0, "foodSickStep": 0.0, "foodSickTarget": 0.0}}
        self.snapshot()

    # -- the clock
    def clock(self):
        return self.t

    def sleep(self, dt):
        self.advance(dt)

    def advance(self, dt):
        end = self.t + dt
        while self.t < end - 1e-12:
            gm_per_s = self.speed * 60.0 / self.GH_S
            to_min = (math.floor(self.age * 60.0 + 1e-9) + 1 - self.age * 60.0) / gm_per_s
            due = [p[0] for p in self.pending if p[0] > self.t]
            step = min(end - self.t, to_min, min(due) - self.t if due else 1e18)
            step = max(step, 1e-9)
            gh = step / self.GH_S * self.speed
            self.continuous(gh)
            n0 = math.floor(self.age * 60.0 + 1e-9)
            self.age += gh
            self.t += step
            if math.floor(self.age * 60.0 + 1e-9) > n0:
                self.minute()
            for p in [p for p in self.pending if p[0] <= self.t + 1e-12]:
                self.pending.remove(p)
                p[1]()
            self.snapshot()

    # -- vanilla's per-tick terms
    def bleeding(self):
        return min(4, sum(1 for t, fl in self.parts.values() if fl and t > 0))

    def sick_level(self):
        return lvl(self.food_sick / 100.0, (0.25, 0.5, 0.75, 0.90))

    def continuous(self, gh):
        drop = 0.0
        if self.bleeding() == 4:
            drop += L.WOUND_X451 * gh + self.red * L.M_H * gh
        if self.sick_level() == 4:
            drop += self.red * L.M_H * gh
        self.health = max(0.0, self.health - drop)

    # -- the mod's minute
    def w(self):
        b = self.rec["body"]
        return b["fm"] + b["lm"] + b["lx"]

    def minute(self):
        R, f = self.rec, self.f
        self.writes += 1
        st, b = R["stomach"], R["stomach"]["buffer"]
        E = b["calories"]
        frac = min(0.05, (1.25 + 0.0025 * E) / E) if E > 0 else 0.05
        for k in b:
            b[k] *= (1 - frac)
        st["liquid"] *= 0.95
        sat = R["satiety"]
        hl = 3.0 if "wf_slow" in f else 0.69
        sat["M"] *= 2 ** (-(1 / 60.0) / hl)
        D = R["drain"]
        if sat["M"] >= L.FED_M or D["fedAgeH"] > self.age:
            D["fedAgeH"] = self.age
        unfed = self.age - D["fedAgeH"]
        D["starveAcute"] = unfed >= (31.0 if "onset_late" in f else 30.0)
        D["starving"] = D["starveAcute"]
        fl = R["fluids"]
        self.scale = 1.0 if "trait_ignored" in f else (1.5 if "HighThirst" in self.traits else
                                                       (0.5 if "LowThirst" in self.traits else 1.0))
        loss = L.basal_g_day(R["body"]["lm"], self.scale) / 1440.0 * (2.0 if "loss_x2" in f else 1.0)
        if "dry" in f:
            loss *= 4.0
        fl["water"] -= loss
        fl["na"] -= L.BASAL_NA / 1440.0
        weu = L.WATER_PER_MMOL * (fl["na"] + fl["k"])
        fl["dehydPct"] = 100.0 * max(0.0, weu - fl["water"]) / 1000.0 / self.w()
        D["dehydrated"] = fl["dehydPct"] >= (4.2 if "onset_late_pct" in f else 4.0)
        floors, rates = [], []
        if D["starving"]:
            floors.append(50.0)
            rates.append(25.0)
        if D["dehydrated"]:
            floors.append(50.0 - 40.0 * (fl["dehydPct"] - 4.0) / 11.0)
            rates.append(200.0)
        D["active"] = bool(floors)
        D["targetFloor"] = min(floors) if floors else 100.0
        D["rate"] = max(rates) if rates else 0.0
        if "drain_x2" in f:
            D["rate"] *= 2
        D["state"] = 1 if D["starving"] else (6 if D["dehydrated"] else 0)
        if D["active"]:
            take = D["rate"] / 1440.0
            if "floor_leak" in f:
                self.health -= take
            elif self.health > D["targetFloor"]:
                self.health -= min(take, self.health - D["targetFloor"])
        elif self.health < 100.0:
            self.health = min(100.0, self.health + 0.06)
        # the written stats
        if D["starveAcute"] and "no_lift" not in f:
            self.hunger = 1.0
        elif self.forced_unfed:
            self.hunger = 0.69
        elif self.meal_age is not None:
            h = interp(HUNGER_AFTER, (self.age - self.meal_age) * (2.5 if "fast_hunger" in f else 1.0))
            if "eat_hunger" in f and self.age - self.meal_age < 0.1:
                h = 0.1
            self.hunger = min(h, 0.69)
        cap = 1.0 if D["dehydrated"] and "no_tlift" not in f else 0.83
        self.thirst = min(interp(THIRST_KNOTS, fl["dehydPct"]), cap)
        severe = self.hunger > 0.70 or self.thirst > 0.84
        if "const_stuck" not in f:
            was = self.red
            self.red = 0.0 if severe else L.CONST_DEFAULT
            if was == 0.0 and "no_reapply" not in f:
                k = 2.0 if "reapply_x2" in f else 1.0
                y = 0.0
                if self.bleeding() == 4:
                    y += k * L.CONST_DEFAULT * L.M_H / 60.0
                if self.sick_level() == 4:
                    y += k * L.CONST_DEFAULT * L.M_H / 60.0
                if y > 0:
                    self.health -= y
                    self.reapplied += 1
        level = L.overfull_level(L.stomach_mass({f"stomach.buffer.{k}": v for k, v in b.items()} |
                                                {"stomach.liquid": st["liquid"]}))
        if level == 4 and "no_refuse" not in f:
            self.timer = 4400.0
        elif level == 3 and "early_refuse" in f:
            self.timer = 4400.0
        elif D["active"] or "timer_off" in f:
            self.timer = 0.0
        elif sat["M"] >= L.WELL_FED_M or ("wf_long" in f and sat["M"] >= 300.0):
            self.timer = 2800.0 if level >= 2 else 1000.0
        else:
            self.timer = 0.0
        if level == 4 and "no_nausea" not in f:
            self.food_sick = max(self.food_sick, 30.0)
        self.endurance = 0.73 if level >= 3 and "no_endcap" not in f else 1.0
        R["effects"]["enduranceCap"] = 0.73 if level >= 3 else 1.0
        R["stomachFill"] = min(1.0, L.stomach_mass({f"stomach.buffer.{k}": v for k, v in b.items()} |
                                                    {"stomach.liquid": st["liquid"]}) / 730.0)
        if self.ring_on:
            self.s += 1
            row = {"s": self.s, "ev": self.s, "age": self.age, "dtM": 1.0, "hour": int(L.hour_of(self.age)),
                   "min": int(self.age * 60) % 60, "on": True, "HUNGER": self.hunger, "THIRST": self.thirst,
                   "FATIGUE": 0.0, "BOREDOM": 0.0, "UNHAPPINESS": 0.0, "NICOTINE_WITHDRAWAL": 0.0, "moving": False}
            for p in self.paths:
                ok, v = self.read_path(p)
                if ok:
                    row[p] = v
            self.ring.append(row)

    # -- the moodles and the snapshots
    def moodles(self):
        return {"hungry": lvl(self.hunger, L.HUNGRY_AT), "thirst": lvl(self.thirst, (0.12, 0.25, 0.70, 0.84)),
                "foodEaten": lvl(self.timer, (0.0, 1600.0, 3200.0, 4800.0)), "heavyLoad": 0,
                "endurance": lvl(-self.endurance, (-0.75, -0.5, -0.25, -0.1))}

    def snap_now(self):
        return {"calories": 1000.0, "carbs": 100.0, "lipids": 40.0, "proteins": 60.0, "weight": 65.0,
                "hunger": self.hunger, "thirst": self.thirst, "statsApi": True, "incWeight": False,
                "incWeightLot": False, "decWeight": False, "endurance": self.endurance, "fatigue": 0.0,
                "moodles": self.moodles(),
                "traits": {"obese": False, "HighThirst": "HighThirst" in self.traits,
                           "LowThirst": "LowThirst" in self.traits, "HeartyAppetite": False, "LightEater": False},
                "traitList": sorted(self.traits), "traitRoute": "getKnownTraits", "maxWeight": 8,
                "foodTimer": self.timer, "standardFoodTime": 2880, "asleep": False, "running": False,
                "sprinting": False, "moving": False, "worldAge": self.age, "mult": self.speed * EFF,
                "wall": int(self.t * 1000)}

    def snapshot(self):
        self.hist.append((self.t, self.snap_now()))
        if len(self.hist) > 400:
            self.hist = self.hist[-200:]

    def client_snap(self):
        old = [s for t, s in self.hist if t <= self.t - self.LAG_S]
        s = dict(old[-1] if old else self.hist[0][1])
        if "client_stale" in self.f:
            s["moodles"] = dict(s["moodles"], foodEaten=0, hungry=0, thirst=0)
        return s

    # -- the record and the globals
    def globals_(self):
        return {"NutritionRevamp.server.intake.stats.eats": self.eats,
                "NutritionRevamp.server.intake.stats.landed": self.landed,
                "NutritionRevamp.server.intake.stats.sips": self.sips,
                "NutritionRevamp.server.writer.stats.writes": self.writes,
                "NutritionRevamp.server.writer.h.admin.red": self.red,
                "NutritionRevamp.server.writer.h.admin.ft": self.timer,
                "NutritionRevamp.server.writer.severeStats.reapplied": self.reapplied,
                "NutritionRevamp.server.nutrients.fctx.basalScale": self.scale,
                "NutritionRevamp.server.store.file.lastWrite.admin": 1000.0 + math.floor(self.t / 20.0),
                "NutritionRevamp.server.players.online.admin": True,
                "NutritionRevamp.client.tooltip.stats.hidden": 0, "NutritionRevamp.client.tooltip.stats.shown": 0,
                "NutritionRevamp.client.tooltip.stats.draws": 0,
                "SandboxVars.Nutrition": False, "SandboxVars.DayLength": 1, "NutritionRevamp.version": "1.0.0",
                "SandboxVars.NR.Severity": 1.0, "SandboxVars.StatsDecrease": 3,
                "NutritionRevamp.server.nutrients.sleepDisabled": True}

    def read_path(self, p):
        if p.startswith("_G."):
            v = self.globals_().get(p[3:])
            return (v is not None), v
        d = self.rec
        for seg in p.split("."):
            if not isinstance(d, dict) or seg not in d:
                return False, None
            d = d[seg]
        return (d is not None and not isinstance(d, dict)), d

    def set_path(self, p, v):
        segs = p.split(".")
        d = self.rec
        for seg in segs[:-1]:
            d = d[seg]
        before = d.get(segs[-1])
        d[segs[-1]] = v
        if p == "satiety.M" and v < L.FED_M:
            self.forced_unfed = True
        return before

    # -- the eat
    def land(self, full):
        if self.inv.get(full, 0) <= 0:
            return
        self.inv[full] -= 1
        self.eats += 1
        self.landed += 1
        b = self.rec["stomach"]["buffer"]
        for k, v in FOOD_MASS[full].items():
            b[k] += v
        b["calories"] += L.FOODS[full]["cal"]
        self.rec["fluids"]["water"] += FOOD_MASS[full]["water"]
        self.rec["satiety"]["M"] += L.FOODS[full]["cal"] * 1.2
        self.forced_unfed = False
        self.meal_age = self.age
        self.hunger = 0.1 if "eat_hunger" in self.f else 0.0

    def drink_done(self, full):
        lit = self.fills.get(full, 0.0)
        self.inv[full] -= 1
        self.fills[full] = 0.0
        self.sips += 2
        self.rec["fluids"]["water"] += lit * 1000.0
        self.rec["stomach"]["liquid"] += 0.0

    # -- RCON and the bus
    def rcon(self, cmd):
        m = re.match(r'settimespeed (\d+)', cmd)
        if m:
            if "rcon_inert" not in self.f or self.speed >= 1.0:
                self.speed = float(m.group(1))
            return True, "Time speed set to " + m.group(1)
        m = re.match(r'additem "admin" "([^"]+)" (\d+)', cmd)
        if m:
            self.inv[m.group(1)] = self.inv.get(m.group(1), 0) + int(m.group(2))
            return True, "Item " + m.group(1) + " Added in admin's inventory."
        return False, "Unknown command " + cmd

    def ask(self, node, cmd, args="", timeout=30):
        self.advance(self.STEP_S / 2)
        r = self._answer(node, cmd, args.split() if args else [])
        self.advance(self.STEP_S / 2)
        return r

    def _answer(self, node, cmd, a):
        srv = node == L.SRV
        if cmd == "ping":
            return "pong"
        if cmd == "players":
            return ["admin"]
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": int(L.hour_of(self.age)), "minutes": 0, "mult": self.speed * EFF,
                    "trueMult": self.speed, "wall": int(self.t * 1000)}
        if cmd == "time.multiplier":
            self.speed = float(a[0])
            return f"mult={self.speed} eff={self.speed * EFF}"
        if cmd == "stats.get":
            return self.snap_now() if srv else self.client_snap()
        if cmd == "stats.all":
            return {"side": "server", "user": "admin", "worldAge": self.age, "mult": self.speed * EFF,
                    "wall": int(self.t * 1000), "missing": {},
                    "stats": {"Hunger": self.hunger, "Thirst": self.thirst, "FoodSickness": self.food_sick,
                              "Fatigue": 0.0, "Boredom": 0.0, "Unhappiness": 0.0, "NicotineWithdrawal": 0.0}}
        if cmd == "stats.setany":
            before = self.food_sick
            self.food_sick = float(a[2])
            return {"ok": True, "stat": a[1], "side": "server", "requested": float(a[2]), "before": before,
                    "after": self.food_sick}
        if cmd == "health.get":
            return {"ok": True, "side": "server", "overall": self.health, "health": self.health, "parts": []}
        if cmd == "health.reduce":
            before = self.health
            self.health = max(0.0, self.health - float(a[1]))
            return {"ok": True, "side": "server", "requested": float(a[1]), "before": before, "after": self.health,
                    "health": self.health, "parts": []}
        if cmd == "moodle.level":
            lv = {"SICK": self.sick_level(), "BLEEDING": self.bleeding()}.get(a[1], 0)
            return {"ok": True, "side": "server", "user": a[0], "moodle": a[1], "level": lv}
        if cmd == "witness.chain":
            chain = a[1] if srv else a[0]
            if chain == "getBodyDamage.getHealthReductionFromSevereBadMoodles":
                return {"ok": True, "value": repr(self.red), "hops": 2}
            if chain.endswith(".getTags"):
                return {"ok": True, "value": "[base:fruit]", "hops": 3}
            return {"ok": False, "failedAt": 1, "error": "no member", "hops": 1}
        if cmd == "lua.read":
            root, paths = a[0], a[1:]
            v, miss = {}, {}
            for p in paths:
                ok, x = self.read_path(p if root.startswith("record:") else "_G." + p)
                if ok:
                    v[p] = x
                else:
                    miss[p] = "nil"
            return {"ok": True, "side": "server" if srv else "client", "root": root, "n": len(paths), "values": v,
                    "tables": {}, "types": {}, "missing": miss}
        if cmd == "lua.global":
            rec = {"gen": 1, "rec": {"satiety": {"t": self.age}}, "done": True}
            return {"side": "server", "name": a[0], "resolved": True, "type": "string", "value": json.dumps(rec)}
        if cmd == "lua.call":
            return {"ok": True, "side": "client", "path": a[0], "nargs": 0, "r1": "base:hide_hunger_change"}
        if cmd == "record.set":
            raw = a[2]
            val = float(raw) if re.match(r"^-?[0-9.]+$", raw) else raw
            before = self.set_path(a[1], val)
            return {"ok": True, "side": "server", "user": a[0], "path": a[1], "key": a[1].split(".")[-1],
                    "keyType": "string", "before": before, "beforeType": type(before).__name__, "after": val,
                    "afterType": "number"}
        if cmd == "trait.set":
            before = a[1] in self.traits
            if a[2] == "add":
                self.traits.add(a[1])
            else:
                self.traits.discard(a[1])
            after = a[1] in self.traits
            return {"trait": a[1], "field": a[1].upper(), "op": a[2], "before": before, "enumFound": True,
                    "collection": "getCharacterTraits()", "route": "x", "after": after,
                    "traitList": sorted(self.traits), "held": (a[2] == "add") == after}
        if cmd == "bodypart.set":
            i, field, raw = int(a[1]), a[2], a[3]
            p = self.parts.setdefault(i, [0.0, False])
            if field == "bleedingTime":
                p[0] = float(raw)
            else:
                p[1] = raw == "true"
            return {"ok": True, "side": "server", "part": i, "field": field, "requested": raw, "after": raw,
                    "synced": False}
        if cmd == "item.get":
            n = self.inv.get(a[1], 0)
            return {"fullType": a[1], "id": 1000 + n, "uses": 1} if n else f"no item {a[1]} in admin's inventory"
        if cmd == "autodrink.probe":
            out = {"ok": True, "side": "server", "thirst": self.thirst, "autoDrink": True, "item": None,
                   "litres": None, "fluid": None, "containers": sum(1 for v in self.fills.values() if v > 0)}
            for full, lit in self.fills.items():
                if self.inv.get(full) and lit > 0:
                    out.update({"item": full, "litres": lit, "fluid": "Water"})
                    break
            return out
        if cmd == "fluid.fill":
            refused = "fill_refused" in self.f
            if not refused:
                self.fills[a[1]] = float(a[3])
            return {"ok": not refused, "side": "server", "fullType": a[1], "id": 3000, "spawned": False,
                    "requested": float(a[3]), "litres": 0.0 if refused else float(a[3]),
                    "fluid": None if refused else a[2], "capacity": 1.0}
        if cmd == "drink.action":
            self.pending.append((self.t + 3.0, lambda fl=a[0]: self.drink_done(fl)))
            return {"queued": True, "percentage": 1.0, "spawned": "found" if self.inv.get(a[0]) else "client",
                    "itemId": 8, "filledRatioBefore": 1.0, "before": {}}
        if cmd == "nutrition.get":
            return {"calories": 1000.0, "carbs": 100.0, "lipids": 40.0, "proteins": 60.0, "weight": 65.0,
                    "hunger": self.hunger, "thirst": self.thirst, "statsApi": True, "incWeight": False,
                    "incWeightLot": False, "decWeight": False}
        if cmd == "eat.action":
            full = a[0]
            cs = self.client_snap()
            valid = cs["moodles"]["foodEaten"] < 3
            if valid or "refuse_lands" in self.f:
                self.pending.append((self.t + 3.0, lambda fl=full: self.land(fl)))
            return {"queued": True, "fraction": 1, "spawned": "found" if self.inv.get(full) else "client",
                    "itemId": 7, "itemBefore": {}, "validStart": valid, "maxTime": 120,
                    "moodleFoodEaten": cs["moodles"]["foodEaten"], "before": {}}
        if cmd == "action.cancel":
            return {"ok": True, "before": 0, "after": 0, "current": None, "started": False, "adding": False,
                    "stopped": True, "javaBefore": 0, "javaAfter": 0, "cleared": True}
        if cmd == "minute.ring":
            if a[1] == "start":
                self.ring_on, self.paths = True, a[2:]
                return {"ok": True, "side": "server", "user": "admin", "armed": True, "cap": 4320,
                        "paths": list(self.paths), "stats": [], "online": True, "probe": {}}
            if a[1] == "read":
                frm = int(a[2]) if len(a) > 2 else 1
                rows = [r for r in self.ring if r["s"] >= frm][:720]
                more = bool(rows) and rows[-1]["s"] < self.s
                name = f"minute-ring-admin-{frm}"
                with open(os.path.join(self.dir, name + ".json"), "w", encoding="utf-8") as fh:
                    json.dump({"rows_list": rows, "paths": self.paths}, fh)
                return {"ok": True, "side": "server", "user": "admin", "from": frm, "rows": len(rows), "skipped": 0,
                        "next": rows[-1]["s"] + 1 if more else None, "more": more, "oldest": 1, "newest": self.s,
                        "recorded": self.s, "overwritten": 0, "cap": 4320, "events": self.s, "errors": 0,
                        "lastError": None, "gErrors": 0, "gLastError": None, "result": name,
                        "file": f"pzt-results/{name}.json"}
            self.ring_on = False
            return {"ok": True, "side": "server", "user": "admin", "stopped": True, "recorded": self.s,
                    "overwritten": 0, "errors": 0, "lastError": None}
        return {"error": f"fake: unknown {cmd}"}


FAKE_BANDS = {"lunch": 3.8, "dinner": 3.8, "breakfast": 3.8}       # the fake's cadence (HUNGER_AFTER)


def run_session(key, tmp_path, monkeypatch, flags=(), budget=1e9, replay=None, bands=True):
    d = str(tmp_path)
    if bands:
        monkeypatch.setattr(L, "CAD_P_TARGETS", dict(FAKE_BANDS))
        monkeypatch.setattr(L, "CAD_H_TARGET", 8.0)
    w = World(d, flags)
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={"admin": FakeClient("admin")}, ask=w.ask, budget_s=budget,
              clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = FakeServer(w, d)
    S = L.Sess(xs, key, run_dir=d)

    def fake_replay(ring_rows, events, start, tol, **kw):
        n = len(ring_rows)
        d_ = replay if replay is not None else {"fields": {f: {"n": n, "max": 0.0, "over": 0, "worst_s": None}
                                                           for f in tol}, "findings": [], "classes": {}}
        return [{"s": r["s"]} for r in ring_rows], d_, None
    monkeypatch.setattr(L, "replay_grade", fake_replay)
    S.body_run(S.phases())
    out["logs"] = {"mod_error": []}
    out["admin_lua_error"] = False
    S.grade_all()
    v = {k: x["verdict"] for k, x in out["verdicts"].items()}
    return v, out, w, S


def bad(v, out):
    return {k: (x, out["verdicts"][k]["observed"]) for k, x in v.items() if x != "as_predicted"}


# ---------------------------------------------------------------- each session end to end, as predicted
@pytest.mark.parametrize("key", list(L.SESSIONS))
def test_session_as_predicted(key, tmp_path, monkeypatch):
    v, out, w, S = run_session(key, tmp_path, monkeypatch)
    assert not out["phase_errors"], out["phase_errors"]
    assert v and all(x == "as_predicted" for x in v.values()), bad(v, out)
    assert out["checks"]["restore"]["ok"] is True and w.speed == 1.0          # the start's speed restored
    assert len(out["checks"]["H"]["ring_paths"]) <= 32
    names = {"x452": {"HYDRATED", "EAT0", "CAD_FEEL_P", "CAD_FEEL_H", "WF_SHOW", "WF_SPAN", "PAIRS_foodEaten",
                      "PAIRS_hungry", "REPLAY_HUNGER", "REPLAY_THIRST", "REPLAY_body.energyState"},
             "x453": {"OF_REACH", "OF_REFUSE", "OF_EARLY", "OF_TIMER", "OF_NAUSEA", "OF_ENDURANCE", "PAIRS_foodEaten"},
             "x454": {"ONSET", "STARVING_SHOWN", "CONST", "DRAIN_RATE", "FLOOR_HOLD", "RECOVER", "PAIRS_hungry"},
             "x455": {"ONSET", "CONST", "N_BLEED", "S_BLEED", "S_SICK"},
             "x456": {"DEHYD_ONSET", "PARCHED_SHOWN", "CONST", "DEHYD_DRAIN", "DEHYD_FLOOR", "BASAL", "DEHYD_PACE",
                      "P_SICK", "PAIRS_thirst"},
             "x457": {"SCALE", "LOSS_BASE", "LOSS_HIGH", "LOSS_OFF", "LOSS_LOW", "RATIO_HIGH", "RATIO_OFF",
                      "RATIO_LOW", "TRAITS"}}[key] | {"H1", "RING", "Z"}
    assert set(v) == names, set(v) ^ names


def test_x452_records_the_schedule_and_the_t9_reads(tmp_path, monkeypatch):
    v, out, w, S = run_session("x452", tmp_path, monkeypatch)
    plan = out["checks"]["X"]["plan"]
    assert plan["lunch_at_1230"] and abs(L.hour_of(plan["lunch"]) - 12.5) < 1e-9
    assert [m["label"] for m in out["checks"]["X"]["meals"]] == ["lunch", "dinner", "breakfast"]
    assert all(e.get("validStart") is True for e in S.eats) and len(S.eats) == 6
    t9 = out["checks"]["T9"]
    assert t9["verdict"] == "unmeasured" and t9["before"] and t9["after"]["hide_tag_in_set"] is False
    assert "T9" not in out["verdicts"]
    assert not [s for s in out["steps"] if s["cmd"] == "foodtimer.set"]      # the mod owns the timer
    assert os.path.isfile(os.path.join(str(tmp_path), "start.json"))
    van = out["checks"]["vanilla_cadence"]
    assert len(van["day90"]) == 3 and len(van["profile"]) == 3
    wf = out["checks"]["wf_vs_vanilla"]
    assert len(wf) == 3 and all(r["mod_h"] is not None and "vanilla_90_h" in r for r in wf)
    assert "WF_VS_VANILLA" not in out["verdicts"]
    dr = out["checks"]["X"]["drinks"]
    assert [d["container"] for d in dr] == list(L.DRINKS) and all(d["fill_ok"] and d["landed"] for d in dr)
    assert all(abs(d["drunk"] - L.DRINK_L) < 1e-9 for d in dr)
    assert "probe" in t9["after"] and "optionOn" in t9["after"]


def test_x453_seeds_slows_and_refuses(tmp_path, monkeypatch):
    v, out, w, S = run_session("x453", tmp_path, monkeypatch)
    seed = out["checks"]["SEED"]
    assert seed["slow"]["ok"] and abs(seed["after"]["mass"] - L.SEED_G) <= 2
    ref = out["checks"]["X"]["refusal"]
    assert ref["validStart"] is False and ref["landed"] is False and ref["level_at_attempt"] == 4
    trig = out["checks"]["X"]["trigger"]
    assert trig["level"] == 4 and trig["food_sick"] >= 29.5 and out["verdicts"]["OF_NAUSEA"]["observed"]["hold"] is trig
    assert 3 <= len(out["checks"]["X"]["eats"]) <= L.MAX_EATS


def test_x454_sets_the_clock_and_the_health(tmp_path, monkeypatch):
    v, out, w, S = run_session("x454", tmp_path, monkeypatch)
    sets = {s["path"]: s for s in out["sets"]}
    assert sets["satiety.M"]["reply"]["ok"] and sets["drain.fedAgeH"]["reply"]["ok"]
    assert out["sets"].index(sets["satiety.M"]) < out["sets"].index(sets["drain.fedAgeH"])     # M first
    assert abs(sets["drain.fedAgeH"]["value"] if isinstance(sets["drain.fedAgeH"]["value"], float) else
               float(sets["drain.fedAgeH"]["value"]) - (sets["drain.fedAgeH"]["age"] - 29.75)) < 0.01
    assert out["checks"]["B"]["h1"] <= L.HEALTH_SEED + 0.01


# ---------------------------------------------------------------- each defect moves its grade
@pytest.mark.parametrize("key,flag,grades", [
    ("x452", "eat_hunger", {"EAT0"}),
    ("x452", "fast_hunger", {"CAD_FEEL_P", "CAD_FEEL_H"}),
    ("x452", "timer_off", {"WF_SHOW"}),
    ("x452", "wf_long", {"WF_SPAN"}),
    ("x452", "dry", {"HYDRATED"}),
    ("x452", "client_stale", {"PAIRS_foodEaten", "PAIRS_hungry"}),
    ("x453", "no_refuse", {"OF_REFUSE", "OF_TIMER"}),
    ("x453", "refuse_lands", {"OF_REFUSE"}),
    ("x453", "early_refuse", {"OF_EARLY"}),
    ("x453", "no_nausea", {"OF_NAUSEA"}),
    ("x453", "no_endcap", {"OF_ENDURANCE"}),
    ("x453", "client_stale", {"PAIRS_foodEaten"}),
    ("x454", "onset_late", {"ONSET"}),
    ("x454", "no_lift", {"ONSET", "STARVING_SHOWN", "CONST"}),
    ("x454", "const_stuck", {"CONST"}),
    ("x454", "drain_x2", {"DRAIN_RATE"}),
    ("x454", "floor_leak", {"FLOOR_HOLD"}),
    ("x454", "client_stale", {"PAIRS_hungry"}),
    ("x455", "no_reapply", {"S_BLEED", "S_SICK"}),
    ("x455", "reapply_x2", {"S_BLEED", "S_SICK"}),
    ("x455", "const_stuck", {"CONST", "S_BLEED", "S_SICK"}),
    ("x456", "onset_late_pct", {"DEHYD_ONSET"}),
    ("x456", "no_tlift", {"DEHYD_ONSET", "PARCHED_SHOWN"}),
    ("x456", "loss_x2", {"BASAL", "DEHYD_PACE"}),
    ("x456", "drain_x2", {"DEHYD_DRAIN"}),
    ("x456", "floor_leak", {"DEHYD_FLOOR"}),
    ("x456", "no_reapply", {"P_SICK"}),
    ("x456", "client_stale", {"PAIRS_thirst"}),
    ("x457", "trait_ignored", {"SCALE", "LOSS_HIGH", "LOSS_LOW", "RATIO_HIGH", "RATIO_LOW"}),
    ("x457", "loss_x2", {"LOSS_BASE", "LOSS_HIGH", "LOSS_OFF", "LOSS_LOW"}),
])
def test_each_defect_moves_its_grade(key, flag, grades, tmp_path, monkeypatch):
    v, out, _, _ = run_session(key, tmp_path, monkeypatch, flags=(flag,))
    for gname in grades:
        assert v.get(gname) != "as_predicted", (key, flag, gname, out["verdicts"].get(gname, {}).get("observed"))


def test_x452_a_replay_over_the_tolerance_falsifies(tmp_path, monkeypatch):
    d = {"fields": {"HUNGER": {"n": 10, "max": 0.01, "over": 2, "worst_s": 5},
                    "THIRST": {"n": 10, "max": 0.0, "over": 0, "worst_s": None},
                    "body.energyState": {"n": 0, "max": 0.0, "over": 0, "worst_s": None}},
         "findings": [{"field": "HUNGER", "s": 5}], "classes": {}}
    v, out, _, _ = run_session("x452", tmp_path, monkeypatch, replay=d)
    assert v["REPLAY_HUNGER"] == "falsified" and v["REPLAY_THIRST"] == "as_predicted"
    assert v["REPLAY_body.energyState"] == "unmeasured"


def test_x452_cadence_unnamed_is_unmeasured_and_refused_at_preboot(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "CAD_P_TARGETS", {"lunch": None, "dinner": None, "breakfast": None})
    monkeypatch.setattr(L, "CAD_H_TARGET", None)
    v, out, _, _ = run_session("x452", tmp_path, monkeypatch, bands=False)
    assert v["CAD_FEEL_P"] == "unmeasured" and v["CAD_FEEL_H"] == "unmeasured"
    assert L.predictions_named() is False
    checks, ok = L.preboot("x452", L.PROFILE, "x452", "x452_day.py")
    assert ok is False and checks["cadence_bands_named"] is False


def test_x452_a_dehydrated_row_ends_the_graded_rows(tmp_path, monkeypatch):
    v, out, _, _ = run_session("x452", tmp_path, monkeypatch, flags=("dry",))
    assert v["HYDRATED"] == "falsified"
    assert any("excluded (review H2)" in n["note"] for n in out["notes"])


def test_x452_a_refused_fill_leaves_the_replay(tmp_path, monkeypatch):
    seen = {}
    real = L.replay_events

    def spy(rows, eats, start_age, drinks=()):
        seen["drinks"] = list(drinks)
        return real(rows, eats, start_age, drinks)
    monkeypatch.setattr(L, "replay_events", spy)
    v, out, _, S = run_session("x452", tmp_path, monkeypatch, flags=("fill_refused",))
    assert S.drinks and not any(d["fill_ok"] for d in S.drinks) and seen["drinks"] == []
    assert any("fill gate" in n["note"] for n in out["notes"])


def test_the_budget_stops_the_scenario_and_keeps_the_closing_phases(tmp_path, monkeypatch):
    v, out, w, _ = run_session("x454", tmp_path, monkeypatch, budget=40.0)
    assert out.get("budget_stop") and "C" in out["phase_walls"] and "R" in out["phase_walls"]
    assert w.speed == 1.0
    assert v["RECOVER"] != "as_predicted"


# ---------------------------------------------------------------- the pure grades: failing and unmeasured cases
def _srv(t, age, **moodles):
    return {"wall": t, "wall_after": t + 0.1, "worldAge": age, "moodles": moodles}


def _pairs(levels, client, key="foodEaten", dt=1.5):
    out = []
    for i, (s, c) in enumerate(zip(levels, client)):
        t = i * dt
        out.append({"tag": f"p{i}", "s0": _srv(t, i, **{key: s}), "c": _srv(t + 0.2, i, **{key: c}),
                    "s1": _srv(t + 0.4, i, **{key: s})})
    return out


def test_grade_pairs():
    assert L.grade_pairs(_pairs([0, 1, 1, 1, 0, 0], [0, 1, 1, 1, 0, 0]), "foodEaten")[0] == "as_predicted"
    assert L.grade_pairs(_pairs([0, 1, 1, 1, 0, 0], [0, 1, 0, 1, 0, 0]), "foodEaten")[0] == "falsified"
    assert L.grade_pairs(_pairs([0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]), "foodEaten")[0] == "unmeasured"
    assert L.grade_pairs(_pairs([1, 1], [1, 1]), "foodEaten")[0] == "unmeasured"
    steady = _pairs([1] * 8, [1] * 8, dt=5.0)                              # no level change: a stale client passes it
    r = L.grade_pairs(steady, "foodEaten")
    assert r[0] == "unmeasured" and r[1]["transitions"] == 0
    lag = _pairs([0, 1, 1, 1, 1, 1], [0, 0, 1, 1, 1, 1], dt=1.0)           # the client one push behind
    assert L.grade_pairs(lag, "foodEaten")[0] == "as_predicted"


def test_grade_eat0():
    rows = [{"s": i, "age": 5 + i / 60.0, L.EATS_G: (2 if i >= 3 else 0), "HUNGER": 0.0 if i >= 3 else 0.3}
            for i in range(8)]
    m = [{"label": "lunch", "landed": True, "eats_after": 2}]
    assert L.grade_eat0(m, rows)[0] == "as_predicted"
    rows[4]["HUNGER"] = 0.05
    assert L.grade_eat0(m, rows)[0] == "falsified"
    assert L.grade_eat0([{"landed": False, "eats_after": 2}], rows)[0] == "unmeasured"
    assert L.grade_eat0([{"landed": True, "eats_after": 9}], rows)[0] == "unmeasured"


def test_grade_return():
    assert L.grade_return([{"ret": 3.5, "span": 6}], 3.8, 1.0)[0] == "as_predicted"
    assert L.grade_return([{"ret": 2.5, "span": 6}], 3.8, 1.0)[0] == "falsified"
    assert L.grade_return([{"ret": None, "span": 6}], 3.8, 1.0)[0] == "falsified"
    assert L.grade_return([{"ret": None, "span": 4}], 3.8, 1.0)[0] == "unmeasured"
    assert L.grade_return([], 3.8, 1.0)[0] == "unmeasured"
    assert L.grade_return([{"ret": 3.5, "span": 6, "target": None}], 3.8, 1.0)[0] == "unmeasured"
    assert L.grade_return([{"ret": 3.5, "span": 6, "target": 2.7}], None, 0.5)[0] == "falsified"
    assert L.grade_return([{"ret": 3.5, "span": 6, "target": 3.3}], None, 0.5)[0] == "as_predicted"


def test_grade_hydrated_and_the_cut():
    rows = [{"s": i, "fluids.dehydPct": 1.0 + i * 0.1, "drain.dehydrated": False} for i in range(20)]
    assert L.grade_hydrated(rows)[0] == "as_predicted"
    hot = [dict(r, **{"fluids.dehydPct": 4.0}) if r["s"] == 15 else r for r in rows]
    assert L.grade_hydrated(hot)[0] == "falsified"
    on = [dict(r, **{"drain.dehydrated": r["s"] >= 12}) for r in rows]
    assert L.grade_hydrated(on)[0] == "falsified"
    kept, cut = L.hydrated_rows(on)
    assert len(kept) == 12 and cut == 8 and L.hydrated_rows(rows) == (rows, 0)
    assert L.grade_hydrated([{"s": 1}])[0] == "unmeasured"


def test_first_return_and_counts_row():
    rows = [{"s": i, "age": float(i), "HUNGER": 0.1 * i, L.EATS_G: i} for i in range(6)]
    assert L.first_return(rows, 0.0, 5.0, 0.25) == 3.0
    assert L.first_return(rows, 0.0, 2.0, 0.25) is None
    assert L.counts_row(rows, 3) == 3 and L.counts_row(rows, 9) is None


def test_grade_replay_field():
    d = {"fields": {"HUNGER": {"n": 5, "max": 0.001, "over": 0}}, "findings": []}
    assert L.grade_replay_field(d, "HUNGER")[0] == "as_predicted"
    d["fields"]["HUNGER"]["over"] = 1
    assert L.grade_replay_field(d, "HUNGER")[0] == "falsified"
    assert L.grade_replay_field({"fields": {}}, "HUNGER")[0] == "unmeasured"


def _meal(age, landed=True):
    return {"label": "m", "landed": landed, "landed_age": age}


def test_grade_wf_show():
    p = [{"s0": _srv(0, 5.01, foodEaten=1), "s1": _srv(0.4, 5.02, foodEaten=1)}]
    assert L.grade_wf_show([_meal(5.0)], p)[0] == "as_predicted"
    p0 = [{"s0": _srv(0, 5.01, foodEaten=0), "s1": _srv(0.4, 5.02, foodEaten=0)}]
    assert L.grade_wf_show([_meal(5.0)], p0)[0] == "falsified"
    assert L.grade_wf_show([_meal(5.0)], [{"s0": _srv(0, 6.0, foodEaten=1)}])[0] == "unmeasured"


def test_grade_wf_span():
    rows = [{"s": i, "age": 5.0 + i / 60.0, "satiety.M": 700 * 2 ** (-(i / 60.0) / 0.69)} for i in range(90)]
    ring_end = L.ring_wf_end(rows, 5.0, 7.0)
    on = [{"s0": _srv(0, a, foodEaten=1)} for a in (5.1, 5.3, ring_end - 0.01)]
    off = [{"s0": _srv(0, a, foodEaten=0)} for a in (ring_end + 0.01, 5.9)]
    assert L.grade_wf_span(_meal(5.0), on + off, rows, 7.0)[0] == "as_predicted"
    late = [{"s0": _srv(0, a, foodEaten=1)} for a in (5.1, ring_end + 0.2)] + \
        [{"s0": _srv(0, ring_end + 0.25, foodEaten=0)}]
    assert L.grade_wf_span(_meal(5.0), late, rows, 7.0)[0] == "falsified"
    assert L.grade_wf_span(_meal(5.0), on, rows, 7.0)[0] == "unmeasured"
    assert L.grade_wf_span(None, on + off, rows, 7.0)[0] == "unmeasured"


def test_wf_vs_vanilla_is_a_reading():
    r = L.wf_vs_vanilla([0.47, None], {"day90": [{"well_fed_h": 0.2}, {"well_fed_h": 0.48}],
                                       "profile": [{"well_fed_h": 1.17}]})
    assert r == [{"meal": 0, "mod_h": 0.47, "vanilla_90_h": 0.2, "vanilla_profile_h": 1.17},
                 {"meal": 1, "mod_h": None, "vanilla_90_h": 0.48, "vanilla_profile_h": None}]
    assert not hasattr(L, "grade_wf_vs_vanilla")


def test_vanilla_meals_reads_a_cadence():
    v = L.vanilla_meals([5.5, 11.5], 0.2, 90.0, 20.0)
    assert len(v) == 2 and v[0]["peckish"] is not None and v[0]["peckish"] > 3.0
    assert v[0]["well_fed_h"] is not None


def test_overfull_level_and_mass():
    assert [L.overfull_level(m) for m in (700, 731, 853, 854, 977, 1099, 1100)] == [0, 1, 1, 2, 3, 3, 4]
    v = {f"stomach.buffer.{k}": 100.0 for k in ("water", "proteins", "carbs", "lipids", "fibre")}
    v["stomach.liquid"] = 0.4
    assert L.stomach_mass(v) == 500 and L.stomach_mass({}) is None


def test_grade_of_reach_refuse_early():
    eats = [{"label": "a", "landed": True, "pre_level": 2, "post_level": 3},
            {"label": "b", "landed": True, "pre_level": 3, "post_level": 4}]
    assert L.grade_of_reach(eats)[0] == "as_predicted"
    assert L.grade_of_reach(eats[:1])[0] == "falsified"
    assert L.grade_of_reach([{"landed": False}])[0] == "unmeasured"
    ref = {"pre_level": 4, "level_at_attempt": 4, "validStart": False, "landed": False, "mass0": 1102, "mass1": 1100}
    assert L.grade_of_refuse(ref)[0] == "as_predicted"
    assert L.grade_of_refuse(dict(ref, validStart=True))[0] == "falsified"
    assert L.grade_of_refuse(dict(ref, landed=True))[0] == "falsified"
    assert L.grade_of_refuse(dict(ref, mass1=1140))[0] == "falsified"
    assert L.grade_of_refuse(dict(ref, pre_level=3))[0] == "unmeasured"
    left = L.grade_of_refuse(dict(ref, level_at_attempt=3, validStart=True))
    assert left[0] == "unmeasured" and "left Overfull 4" in left[1]["why"]
    assert L.grade_of_refuse(None)[0] == "unmeasured"
    assert L.grade_of_early(eats)[0] == "as_predicted"
    assert L.grade_of_early([dict(eats[0], validStart=False)])[0] == "falsified"
    assert L.grade_of_early([])[0] == "unmeasured"


def test_grade_of_timer_nausea_endurance():
    reads = [{"settled": True, "level": 2, "timer": 0}, {"settled": True, "level": 4, "timer": 4400}]
    assert L.grade_of_timer(reads)[0] == "as_predicted"
    assert L.grade_of_timer([dict(reads[1], timer=1000)])[0] == "falsified"
    assert L.grade_of_timer([reads[0], {"settled": True, "level": 3, "timer": 4400}, reads[1]])[0] == "falsified"
    assert L.grade_of_timer(reads[:1])[0] == "unmeasured"
    assert L.grade_of_timer([dict(reads[1], timer=1000, settled=False)])[0] == "unmeasured"
    hold = {"level": 4, "food_sick": 30.0, "sick": 1}
    assert L.grade_of_nausea(hold)[0] == "as_predicted"
    assert L.grade_of_nausea(dict(hold, food_sick=5.0))[0] == "falsified"
    assert L.grade_of_nausea(dict(hold, sick=0))[0] == "falsified"
    assert L.grade_of_nausea(dict(hold, level=3))[0] == "unmeasured"
    er = [{"settled2": True, "level": 3, "endurance": 0.73, "end_moodle": 1}]
    assert L.grade_of_endurance(er, 1.0)[0] == "as_predicted"
    assert L.grade_of_endurance([dict(er[0], endurance=0.9)], 1.0)[0] == "falsified"
    assert L.grade_of_endurance([dict(er[0], end_moodle=0)], 1.0)[0] == "falsified"
    assert L.grade_of_endurance(er, 0.3)[0] == "unmeasured"
    assert L.grade_of_endurance([dict(er[0], level=2)], 1.0)[0] == "unmeasured"


def _onset_rows(onset_unfed=30.0, h_on=1.0, pre_h=0.69):
    rows = []
    for i in range(30):
        age = 10.0 + i / 60.0
        unfed = 29.75 + i / 60.0
        on = unfed >= onset_unfed
        rows.append({"s": i, "age": age, "drain.fedAgeH": age - unfed, "drain.starveAcute": on,
                     "HUNGER": h_on if on else pre_h})
    return rows


def test_grade_onset():
    assert L.grade_onset(_onset_rows(), 9.99)[0] == "as_predicted"
    assert L.grade_onset(_onset_rows(onset_unfed=30.2), 9.99)[0] == "falsified"
    assert L.grade_onset(_onset_rows(h_on=0.69), 9.99)[0] == "falsified"
    assert L.grade_onset(_onset_rows(pre_h=0.75), 9.99)[0] == "falsified"
    assert L.grade_onset(_onset_rows(onset_unfed=99), 9.99)[0] == "unmeasured"


def test_grade_shown_and_const():
    p = [{"s0": _srv(0, 10.01, hungry=3), "s1": _srv(0.4, 10.02, hungry=4)}]
    assert L.grade_shown(p, 10.0, "hungry")[0] == "as_predicted"
    p3 = [{"s0": _srv(0, 10.01, hungry=3), "s1": _srv(0.4, 10.02, hungry=3)}]
    assert L.grade_shown(p3, 10.0, "hungry")[0] == "falsified"
    assert L.grade_shown(p, None, "hungry")[0] == "unmeasured"
    assert L.grade_shown(p, 12.0, "hungry")[0] == "unmeasured"
    reads = [(9.0, 0.0165), (10.5, 0.0), (11.0, 0.0)]
    assert L.grade_const(reads, 10.0, None, 0.0165)[0] == "as_predicted"
    assert L.grade_const([(9.0, 0.0165), (10.5, 0.0165)], 10.0, None, 0.0165)[0] == "falsified"
    assert L.grade_const([(9.0, 0.0), (10.5, 0.0)], 10.0, None, 0.0165)[0] == "falsified"
    assert L.grade_const([(10.5, 0.0)], 10.0, None, 0.0165)[0] == "unmeasured"
    assert L.grade_const(reads + [(12.0, 0.0165)], 10.0, 11.5, 0.0165)[0] == "as_predicted"


def _drain_points(rate_day, h0=55.0, floor=50.0, hours=8.0, leak=0.0):
    pts, h = [], h0
    for i in range(int(hours * 20)):
        age = 10.0 + i / 20.0
        pts.append({"age": age, "overall": h})
        h = max(floor - leak * i / 20.0, h - rate_day / 24.0 / 20.0) if not leak else h - rate_day / 24.0 / 20.0
    return pts


def test_grade_drain_rate():
    assert L.grade_drain_rate(_drain_points(25.0), 50.0, 55.0, 25.0)[0] == "as_predicted"
    assert L.grade_drain_rate(_drain_points(50.0), 50.0, 55.0, 25.0)[0] == "falsified"
    assert L.grade_drain_rate(_drain_points(25.0)[:3], 50.0, 55.0, 25.0)[0] == "unmeasured"
    deep = _drain_points(200.0, h0=100.0, floor=47.0, hours=8.0)          # the hold's points a little under a later floor
    a_reach = next(p["age"] for p in deep if p["overall"] <= 47.0 + L.FLOOR_REACH)
    held = [dict(p, overall=p["overall"] - 0.4 * max(0.0, p["age"] - a_reach)) for p in deep]
    cut = L.grade_drain_rate(held, 46.4, 100.0, 200.0, a_reach)
    assert cut[0] == "as_predicted" and abs(cut[1]["rel_err"]) < 1e-6


def test_grade_floor_hold():
    rows = [{"s": i, "age": 10.0 + i / 60.0, "drain.targetFloor": 50.0} for i in range(600)]
    pts = _drain_points(25.0)
    assert L.grade_floor_hold(pts, rows, 0.3)[0] == "as_predicted"
    leak = _drain_points(25.0, leak=1.0)
    assert L.grade_floor_hold(leak, rows, 0.3)[0] == "falsified"
    assert L.grade_floor_hold(_drain_points(25.0, hours=5.0), rows, 0.3)[0] == "unmeasured"
    assert L.grade_floor_hold(_drain_points(25.0, h0=90.0, hours=2.0), rows, 0.3)[0] == "unmeasured"


def test_grade_recover():
    pts = [{"age": 12.0 + i / 20.0, "overall": 50.0 + 0.6 * i / 20.0} for i in range(45)]
    rec = {"landed_age": 12.0, "off_age": 12.01, "const_after": 0.0165, "red0": 0.0165, "points": pts}
    assert L.grade_recover(rec)[0] == "as_predicted"
    assert L.grade_recover(dict(rec, off_age=None))[0] == "falsified"
    assert L.grade_recover(dict(rec, const_after=0.0))[0] == "falsified"
    flat = [dict(p, overall=50.0) for p in pts]
    assert L.grade_recover(dict(rec, points=flat))[0] == "falsified"
    assert L.grade_recover(dict(rec, points=pts[:5]))[0] == "unmeasured"


def _win(rate, gh=10.0 / 37.5, lv=4, name="BLEEDING", k=(0.0, 0.0), r=(0, 5)):
    dwall = gh * 37.5
    return {"h0": {"overall": 90.0, "wall": 0.0, "wall_after": 0.0},
            "h1": {"overall": 90.0 - rate * gh, "wall": dwall, "wall_after": dwall},
            "s0": {"worldAge": 10.0, "wall": 0.0, "wall_after": 0.0},
            "s1": {"worldAge": 10.0 + gh, "wall": dwall, "wall_after": dwall},
            "lv0": {name: {"level": lv}}, "lv1": {name: {"level": lv}},
            "k0": {"ok": True, "value": str(k[0])}, "k1": {"ok": True, "value": str(k[1])}, "r0": r[0], "r1": r[1]}


def test_grade_n_s_bleed_and_sick():
    red = L.CONST_DEFAULT
    n = L.WOUND_X451 + red * L.M_H
    assert L.grade_n_bleed(_win(n), red)[0] == "as_predicted"
    assert L.grade_n_bleed(_win(n * 0.5), red)[0] == "falsified"
    assert L.grade_n_bleed(_win(n, lv=3), red)[0] == "unmeasured"
    s = 25.0 / 24.0
    ok_ = L.grade_s_bleed(_win(n + s), _win(n), red, s, 5)
    assert ok_[0] == "as_predicted" and abs(ok_[1]["bias_bound_per_gh"] - 0.002 * 1800 * 0.6 / 17) < 1e-12
    assert L.grade_s_bleed(_win(n - red * L.M_H), _win(n), red, s, 5)[0] == "falsified"   # no re-applied term
    assert L.grade_s_bleed(_win(n + s, k=(0.0165, 0.0165)), _win(n), red, s, 5)[0] == "falsified"
    assert L.grade_s_bleed(_win(n + s), _win(n), red, s, 0)[0] == "falsified"
    assert L.grade_s_bleed(_win(n + s, lv=2), _win(n), red, s, 5)[0] == "unmeasured"
    sick = red * L.M_H + s
    assert L.grade_sick(_win(sick, name="SICK"), red, s)[0] == "as_predicted"
    assert L.grade_sick(_win(sick * 2, name="SICK"), red, s)[0] == "falsified"
    assert L.grade_sick(_win(sick, name="SICK", k=(0.0165, 0.0)), red, s)[0] == "falsified"
    assert L.grade_sick(_win(sick, name="SICK", lv=3), red, s)[0] == "unmeasured"


def _dehyd_rows(onset_pct=4.0, t_on=0.90, pre_t=0.83):
    rows = []
    for i in range(40):
        p = 3.9 + i * 0.005
        on = p >= onset_pct
        rows.append({"s": i, "age": 10.0 + i / 60.0, "fluids.dehydPct": p, "drain.dehydrated": on,
                     "THIRST": t_on if on else pre_t})
    return rows


def test_grade_dehyd_onset():
    assert L.grade_dehyd_onset(_dehyd_rows(), 9.99)[0] == "as_predicted"
    assert L.grade_dehyd_onset(_dehyd_rows(onset_pct=4.04), 9.99)[0] == "falsified"     # the row before past 4 %
    rows = _dehyd_rows()
    for r in rows:
        if r["fluids.dehydPct"] >= 3.98:
            r["drain.dehydrated"] = True
    assert L.grade_dehyd_onset(rows, 9.99)[0] == "falsified"                 # the onset under 4 %
    assert L.grade_dehyd_onset(_dehyd_rows(t_on=0.83), 9.99)[0] == "falsified"
    assert L.grade_dehyd_onset(_dehyd_rows(pre_t=0.85), 9.99)[0] == "falsified"
    assert L.grade_dehyd_onset(_dehyd_rows(onset_pct=99), 9.99)[0] == "unmeasured"


def _water_rows(loss_gh, n=200, **extra):
    return [dict({"s": i, "age": 10.0 + i / 60.0, "fluids.water": -500.0 - loss_gh * i / 60.0, "stomach.liquid": 0.0,
                  "stomach.buffer.water": 0.0, "fluids.sweatLmin": 0.0, "body.coldMult": 1.0, L.LANDED_G: 0,
                  L.SIPS_G: 0}, **extra) for i in range(n)]


def test_water_loss_and_grade_loss():
    pred = L.basal_g_day(52.02) / 24.0
    loss, cond = L.water_loss(_water_rows(pred), 9.9, 20.0)
    assert abs(loss - pred) < 1e-6 and cond["clean"]
    assert L.grade_loss(loss, cond, 52.02, 1.0, 0.03)[0] == "as_predicted"
    loss2, cond2 = L.water_loss(_water_rows(pred * 1.2), 9.9, 20.0)
    assert L.grade_loss(loss2, cond2, 52.02, 1.0, 0.03)[0] == "falsified"
    loss3, cond3 = L.water_loss(_water_rows(pred, **{"stomach.liquid": 50.0}), 9.9, 20.0)
    assert cond3["clean"] is False and L.grade_loss(loss3, cond3, 52.02, 1.0, 0.03)[0] == "unmeasured"
    loss4, cond4 = L.water_loss(_water_rows(pred, n=30), 9.9, 20.0)
    assert L.grade_loss(loss4, cond4, 52.02, 1.0, 0.03)[0] == "unmeasured"
    rows = _water_rows(pred)
    for r in rows[100:]:
        r[L.SIPS_G] = 1
    assert L.water_loss(rows, 9.9, 20.0)[1]["clean"] is False


def test_dehyd_pace_and_grades():
    w, lm = 65.025, 52.02
    grow = (L.basal_g_day(lm) - L.WATER_PER_MMOL * L.BASAL_NA) / 24.0
    pct_gh = grow / (10.0 * w)
    p = L.dehyd_pace(w, lm, pct_gh, 6.0, 50.0, 100.0)
    assert abs(p["live_h"] - p["kernel_h"]) < 1e-6 and abs(p["kernel_h"] - 38.13) < 0.05
    assert L.grade_pace(p)[0] == "as_predicted"
    sp = L.dehyd_spec(p)
    assert abs(sp["kernel_gap_h"] - (p["kernel_h"] - 35.0)) < 1e-9 and sp["spec_h"] == 35.0
    assert L.dehyd_spec({})["live_gap_h"] is None and not hasattr(L, "grade_spec")
    fast = L.dehyd_pace(w, lm, pct_gh * 2.0, 6.0, 50.0, 100.0)
    assert L.grade_pace(fast)[0] == "falsified"
    assert L.grade_pace(L.dehyd_pace(w, lm, None, 6.0, 50.0))[0] == "unmeasured"
    half = L.dehyd_pace(w, lm, pct_gh, 3.0, 50.0, 75.0)                   # half the drain from half the height
    assert abs(half["live_h"] - p["live_h"]) < 1e-6


def test_grade_scale_ratio_traits():
    arms = {k: {"scale": v, "loss": 83.33 * v, "clean": True,
                "traits": {"HighThirst": k == "HIGH", "LowThirst": k == "LOW"}} for k, v in L.TRAIT_SCALE.items()}
    assert L.grade_scale(arms, 3)[0] == "as_predicted"
    bad_ = json.loads(json.dumps(arms))
    bad_["HIGH"]["scale"] = 1.0
    assert L.grade_scale(bad_, 3)[0] == "falsified"
    two = {k: dict(a, scale=a["scale"] * 2) for k, a in arms.items()}
    assert L.grade_scale(two, 3)[0] == "falsified" and L.grade_scale(two, 1)[0] == "as_predicted"
    assert L.grade_scale({"BASE": arms["BASE"]}, 3)[0] == "unmeasured"
    for k in ("HIGH", "OFF", "LOW"):
        assert L.grade_ratio(arms, k)[0] == "as_predicted"
    assert L.grade_ratio(bad_ | {"HIGH": dict(arms["HIGH"], loss=83.33)}, "HIGH")[0] == "falsified"
    assert L.grade_ratio(arms | {"LOW": dict(arms["LOW"], clean=False)}, "LOW")[0] == "unmeasured"
    assert L.grade_traits(arms)[0] == "as_predicted"
    wrong = json.loads(json.dumps(arms))
    wrong["OFF"]["traits"]["HighThirst"] = True
    assert L.grade_traits(wrong)[0] == "falsified"
    assert L.grade_traits({"BASE": arms["BASE"]})[0] == "unmeasured"


def test_grade_ring_h1_z():
    assert L.grade_ring([{"file": "a", "reply": {"errors": 0}}])[0] == "as_predicted"
    assert L.grade_ring([{"file": "a", "reply": {"errors": 2}}])[0] == "falsified"
    assert L.grade_ring([{"reply": {"errors": 0}}])[0] == "falsified"
    assert L.grade_ring([])[0] == "unmeasured"
    assert L.grade_h1({"ok": True, "missing": {}}, {"ok": True})[0] == "as_predicted"
    assert L.grade_h1({"ok": True, "missing": {"drain.x": "nil"}}, {"ok": True})[0] == "falsified"
    assert L.grade_z({"logs": {"mod_error": []}, "admin_lua_error": False})[0] == "as_predicted"
    assert L.grade_z({"logs": {"mod_error": ["NR_X.lua failed:"]}, "admin_lua_error": False})[0] == "falsified"
    assert L.grade_z({"logs": {"mod_error": []}, "admin_lua_error": True})[0] == "falsified"
    assert L.grade_z({})[0] == "unmeasured"


def test_day_plan():
    p = L.day_plan(4.1)                                                    # 11:06
    assert abs(L.hour_of(p["lunch"]) - 12.5) < 1e-9 and p["lunch_at_1230"]
    assert abs(L.hour_of(p["dinner"]) - 18.5) < 1e-9 and abs(L.hour_of(p["breakfast"]) - 7.5) < 1e-9
    late = L.day_plan(5.45)                                                # 12:27
    assert not late["lunch_at_1230"] and abs(late["lunch"] - 5.55) < 1e-9


def test_fit_slope_and_window_rate():
    assert abs(L.fit_slope([(0, 1), (1, 3), (2, 5)]) - 2.0) < 1e-12
    assert L.fit_slope([(1, 1)]) is None and L.fit_slope([(1, 1), (1, 2)]) is None
    r = L.window_rate(_win(30.0, gh=1.0))
    assert abs(r["rate_per_gh"] - 30.0) < 1e-9
    assert L.window_rate({"h0": {}, "h1": {}})["rate_per_gh"] is None


# ---------------------------------------------------------------- the replay bookkeeping
def test_build_events_keys_each_eat_to_its_row():
    rows = [{"s": i, "age": 5 + i / 60.0, L.EATS_G: (0 if i < 3 else (1 if i < 5 else 2))} for i in range(8)]
    eats = [{"food": L.BOLOGNESE, "landed": True, "label": "a"}, {"food": L.BANANA, "landed": True, "label": "b"}]
    ev, notes = L.build_events(rows, eats)
    assert [e["s"] for e in ev] == [3, 5] and [e["fullType"] for e in ev] == [L.BOLOGNESE, L.BANANA]
    assert abs(ev[0]["hunger"] + 0.24) < 1e-6 and not notes
    ev2, notes2 = L.build_events(rows[:4], eats)
    assert len(ev2) == 1 and notes2


def test_replay_grade_runs_the_head_replay_on_a_synthetic_ring():
    """The real wrapper reaches tools/replay_live.replay_live (the stub in the session tests stands in for it)."""
    pytest.importorskip("lupa")
    import replay_live as RL
    assert callable(RL.replay_live) and callable(RL.diff)


# ---------------------------------------------------------------- the pre-boot checks
def test_harness_markers_are_in_the_repository():
    found, ok = L.harness_markers_ok()
    assert ok, found


def test_deployed_marker_check_on_a_run_layout():
    with tempfile.TemporaryDirectory() as d:
        for fname, rel in L.HARNESS_FILES.items():
            side = rel.split("/")[-2]
            dst = os.path.join(d, "server", "Zomboid", "mods", "PZTestKit", "42", "media", "lua", side, fname)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(REPO, rel), dst)
        dm, ok = X.deployed_marker_check(d, list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)
        assert ok, dm
        p = os.path.join(d, "server", "Zomboid", "mods", "PZTestKit", "42", "media", "lua", "client",
                         "PZTestKit_Client_Body.lua")
        with open(p, "w", encoding="utf-8") as out:
            out.write("-- emptied")
        assert X.deployed_marker_check(d, list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)[1] is False


def test_staged_gate_on_a_real_staged_copy_of_the_pinned_commit():
    import release_pack as RP
    with tempfile.TemporaryDirectory() as d:
        arch = subprocess.run(["git", "archive", "--format=tar", L.STAGED_FROM, L.MOD_DIR], cwd=REPO,
                              capture_output=True, check=True)
        with tarfile.open(fileobj=io.BytesIO(arch.stdout)) as tf:
            tf.extractall(os.path.join(d, "src"), filter="data")
        RP.stage(os.path.join(d, "src", *L.MOD_DIR.split("/")), os.path.join(d, "out"))
        root = os.path.join(d, "out", "NutritionRevamp")
        mod = os.path.join(root, "Contents", "mods", "NutritionRevamp")
        mg = L.staged_gate(stage_root=root, stage_mod=mod)
        assert mg["ok"] and mg["staged_version"] == "1.0.0", mg
        with open(os.path.join(mod, *L.STAGED_CORE.split("/")), "a", encoding="utf-8") as fh:
            fh.write("\n-- drift\n")
        assert L.staged_gate(stage_root=root, stage_mod=mod)["ok"] is False


def test_the_pinned_commit_is_the_mod_trees_last():
    last = subprocess.run(["git", "log", "-1", "--format=%h", "--", L.MOD_DIR], cwd=REPO, capture_output=True,
                          text=True).stdout.strip()
    assert last.startswith(L.STAGED_FROM) or L.STAGED_FROM.startswith(last)


@pytest.mark.parametrize("key", list(L.SESSIONS))
def test_preboot_passes_on_the_repository(key, monkeypatch):
    monkeypatch.setattr(L, "CAD_P_TARGETS", dict(FAKE_BANDS))
    monkeypatch.setattr(L, "CAD_H_TARGET", 8.0)
    if any(d.startswith(key + "-") for d in os.listdir(os.path.join(REPO, "testing", "artifacts"))):
        pytest.skip("the session has run; its committed artifact is the evidence "
                    "(test_preboot_refuses_a_committed_artifact covers the refusal)")
    drv = L.SESSIONS[key]["driver"]
    checks, ok = L.preboot(key, L.PROFILE, key, drv)
    assert ok, checks
    assert L.preboot(key, L.PROFILE, "x999", drv)[1] is False
    assert L.preboot(key, "x45-mod", key, drv)[1] is False
    other = [k for k in L.SESSIONS if k != key][0]
    assert L.preboot(key, L.PROFILE, key, L.SESSIONS[other]["driver"])[1] is False


def test_preboot_refuses_a_committed_artifact(tmp_path):
    shutil.copytree(os.path.join(REPO, "testing", "profiles"), tmp_path / "testing" / "profiles")
    for rel in L.HARNESS_FILES.values():
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(os.path.join(REPO, rel), dst)
    (tmp_path / "testing" / "artifacts").mkdir()
    assert L.preboot("x454", L.PROFILE, "x454", "x454_starve.py", repo=str(tmp_path))[1] is True
    (tmp_path / "testing" / "artifacts" / "x454-20261017-100000").mkdir()
    checks, ok = L.preboot("x454", L.PROFILE, "x454", "x454_starve.py", repo=str(tmp_path))
    assert ok is False and checks["no_prior_artifact"] is False


def test_profile_doc_checks_fail_a_wrong_profile():
    import tomllib
    with open(os.path.join(REPO, "testing", "profiles", L.PROFILE + ".toml"), encoding="utf-8") as fh:
        text = fh.read()
    doc = tomllib.loads(text)
    assert all(L.profile_doc_checks(L.PROFILE, doc, text).values())
    bad_ = dict(doc, sandbox=dict(doc["sandbox"], Nutrition=True))
    assert L.profile_doc_checks(L.PROFILE, bad_, text)["nutrition_false"] is False
    bad_ = dict(doc, server={"SleepAllowed": True, "SleepNeeded": True})
    assert L.profile_doc_checks(L.PROFILE, bad_, text)["sleep_off"] is False
    bad_ = dict(doc, mods=[{"id": "PZTestKit"}, {"id": "NutritionRevamp", "path": "mod/NutritionRevamp"}])
    assert L.profile_doc_checks(L.PROFILE, bad_, text)["mods_staged"] is False
    assert L.profile_doc_checks("x45-mod", doc, text)["named_profile"] is False


@pytest.mark.parametrize("key", list(L.SESSIONS))
def test_driver_names_its_session(key):
    drv = L.SESSIONS[key]["driver"]
    src = open(os.path.join(REPO, "testing", "experiments", drv), encoding="utf-8").read()
    assert f'KEY = "{key}"' in src and f'PREFIX = "{key}"' in src and f'PROFILE = "{L.PROFILE}"' in src
    assert f'ARTIFACT = "{L.SESSIONS[key]["artifact"]}"' in src and "import x45g_lib as L" in src
    assert drv.startswith(key + "_")


@pytest.mark.parametrize("key", list(L.SESSIONS))
def test_every_prediction_names_a_grade_the_session_makes(key, tmp_path, monkeypatch):
    import importlib
    mod = importlib.import_module(L.SESSIONS[key]["driver"][:-3])
    v, out, _, _ = run_session(key, tmp_path, monkeypatch)
    assert set(mod.PRED) == set(v), set(mod.PRED) ^ set(v)
    assert mod.BUDGET_S <= 500.0                                       # plus about 60 s of closing: under 10 min


def test_restore_falls_back_to_time_multiplier(tmp_path, monkeypatch):
    v, out, w, _ = run_session("x453", tmp_path, monkeypatch, flags=("rcon_inert",))
    r = out["checks"]["restore"]
    assert r["set"]["ok"] is False and "set_mult" in r and r["ok"] is True and w.speed == 1.0


def test_the_cadence_bands_are_named_from_the_prerun():
    assert L.predictions_named() is True
    assert L.CAD_P_TARGETS == {"lunch": 3.683, "dinner": 3.700, "breakfast": 4.183} and L.CAD_H_TARGET == 9.683


def test_prerun_schedule_keys_mirror_the_drivers():
    import x45g_prerun as P
    assert P.k_of(P.START_AGE + 1 / 60.0) == 0 and P.k_of(330 / 60.0) == 149
    assert P.SET_AGE > P.START_AGE
