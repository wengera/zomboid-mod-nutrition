"""Offline tests of testing/experiments/x46_lib.py and x46_prerun.py (Plan 16 Task 9, runs x461a-x467): every grade with
a failing case and its unmeasured case; the pre-boot checks on the real repository, the real staged copy and the real
fixture; the prerun current at HEAD; and each session's body run against a fake world behind a fake bus (test_x45g_lib's
World, extended here with the body clock, the absence, the hard kill, the guard and the tooltip), once as predicted and
once per defect flag that must move a named grade off as_predicted.

The fake bus answers the harness's real reply shapes (docs/reference/harness-commands.md), test_x45g_lib's list plus:
autodrink.set {ok, side, requested, before, after}; player.sleep {requested, before, setAsleep, after, held};
player.sleep.hold {user, seconds, before, after, armed, deadlineWall}; witness.chain {ok, value, hops} with a count's
value tostring'd; witness.moddata {side, scope, arg, values, missing, worldAge, resolved, keys, keyCount, count};
tooltip.measure {ok, fullType, hideOn, height, hungerLineDrawn, bandShown, wrapped, vanilla, hungerChange, nativeTag,
fill, heightBase, heightOn, heightOff, lineDrop, lineSpacing, bandOn, bandOff, hiddenOn, shownOn, tagAfter, tagLeft,
optionBefore, restored}; players [] with nobody on; RCON save and changeoption as the game's text.
"""
import copy
import json
import math
import os
import re
import sqlite3
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x46_lib as L                   # noqa: E402
import x46_prerun as PR               # noqa: E402
import x45g_lib as G                  # noqa: E402
import xlib as X                      # noqa: E402
import test_x45g_lib as T             # noqa: E402

REPO = L.REPO
FF_FAKE = 20.0                         # the fake's fast-forward: game time runs this much faster with admin asleep


# ---------------------------------------------------------------- the fake world
class FakeProc:
    def __init__(self, pid):
        self.pid = pid


class Client46(T.FakeClient):
    def __init__(self, user, world, pid=7001):
        super().__init__(user)
        self.w = world
        self.proc = FakeProc(pid)
        self.killed = False

    def quit(self, timeout=60):
        self.w.online = False
        self.alive = False
        return 0

    def kill(self):
        self.killed = True
        self.alive = False
        self.w.online = False


class Server46(T.FakeServer):
    def __init__(self, world, results_dir, ini=None):
        super().__init__(world, results_dir)
        self.ini = ini


def split_path(p):
    out, buf, i = [], "", 0
    while i < len(p):
        c = p[i]
        if c == "[":
            j = p.index("]", i)
            out.append(p[i + 1:j])
            i = j + 1
            if i < len(p) and p[i] == ".":
                i += 1
            continue
        if c == ".":
            out.append(buf)
            buf = ""
        else:
            buf += c
        i += 1
    if buf:
        out.append(buf)
    return out


class World46(T.World):
    """test_x45g_lib.World with this lib's record: the stamps, the acute sleep state and the body clock (K.circadian's
    rules: seeded at the world hour, advanced by integrated time, reset to 07:00 plus the gap at the close of a bout of
    4 booked hours, off with sleep off), the absence (no step offline; the first minute back moves the stamps by the
    gap; that minute runs nothing), the sleep poll (the setting followed at the next minute), the guard (an eat at
    Overfull 4 refused, nothing landed), the hard kill and the restart (the world and the character as saved), the
    fast-forward (FF_FAKE x the speed with admin asleep) and the tooltip measure."""

    def __init__(self, results_dir, flags=(), sleep_on=False):
        self.sleep_on = sleep_on
        self.sleep_opt = sleep_on
        self.opt_due = None
        self.online = True
        self.asleep = False
        self.resume_due = False
        self.skip_next = False
        self.stats46 = {"resumes": 0, "resumedH": 0.0, "loads": 0, "created": 1, "failures": 0}   # no rewound
        # key until the first backward resume (NR_Server_Store.lua:95, :198; re-review N4)
        self.backup = {"writes": 0, "bytes": 0, "reads": 0, "restored": 0, "aheadKept": 0, "rejected.absent": 0,
                       "rejected.garbled": 0, "rejected.sum": 0}
        self.guard = {"checks": 0, "refused": 0, "held": 0, "stopped": 0, "failures": 0, "passthrough": 0}
        self.queue_left = False
        self.saved = None
        self.dead = False
        self.fluids_by = {}
        self.file = None                 # the slot file's record (the text the load rule reads)
        self.copy = None                 # the character's copy (modData), written with each slot write
        self.last_write = None           # the store's lastWrite (wall ms)
        self.last_write_t = -60.0 if "early_write" in flags else -30.0   # the first write 30 wall s in (0: early)
        self.dirty = False
        self.pending_pick = False
        super().__init__(results_dir, flags)
        R = self.rec
        R["lastSeen"] = self.age
        R["satiety"]["t"] = self.age
        R["nutrients"] = {"lastAgeH": self.age}
        R["body"].update({"lastAgeH": self.age, "dayStartH": 3.0, "dayIndex": 0})
        R["acute"] = {"sleptH": 0.0, "boutH": 0.0, "gapH": 0.0, "winSleptH": 0.0, "winStartH": 3.0, "debtH": 0.0,
                      "S": 0.2, "awakeH": 0.0, "caf": 0.0, "gutCaf": 0.0, "cafTol": 0.0,
                      "bodyHour": L.world_hour(self.age), "bodyOn": sleep_on,
                      "circ": 0.0}
        R["monotony"] = {"t": {}}
        self.meal_age = self.age                    # HUNGER rises from the start (x461b's request comes)

    # -- the clock: the fast-forward while asleep
    def advance(self, dt):
        end = self.t + dt
        while self.t < end - 1e-12:
            sp = self.speed * (FF_FAKE if self.asleep and self.sleep_on and self.online else 1.0)
            gm_per_s = sp * 60.0 / self.GH_S
            to_min = (math.floor(self.age * 60.0 + 1e-9) + 1 - self.age * 60.0) / gm_per_s
            due = [p[0] for p in self.pending if p[0] > self.t]
            step = max(min(end - self.t, to_min, min(due) - self.t if due else 1e18), 1e-9)
            gh = step / self.GH_S * sp
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

    def circ_f(self):
        return 0.1 * math.cos(2 * math.pi * (self.rec["acute"]["bodyHour"] - 4.0) / 24.0) if hasattr(self, "rec") \
            else 0.0

    # -- the minute
    def row_offline(self):
        self.s += 1
        row = {"s": self.s, "ev": self.s, "age": self.age, "dtM": 1.0, "on": False}
        for p in self.paths:
            ok, v = self.read_path(p)
            if ok:
                row[p] = v
        self.ring.append(row)

    def minute(self):
        if self.dead:
            return
        try:
            self.minute_body()
        finally:
            # re-review N1: PZTestKit's EveryOneMinute hook (the ring) runs before the mod's poll (Mods= order), so a
            # change made since the last minute shows on the NEXT ring row
            if self.opt_due is not None and self.age >= self.opt_due:
                self.sleep_on, self.opt_due = self.sleep_opt, None

    def minute_body(self):
        if not self.online:
            if "away_step" in self.f:
                self.rec["satiety"]["M"] *= 0.99
            if self.ring_on:
                self.row_offline()
            return
        R = self.rec
        if self.resume_due and self.pending_pick:
            self.pick()
            self.resume_due, self.skip_next = False, True
            self._ring_only()
            return
        if self.resume_due:
            gap = self.age - R["lastSeen"]
            for p in L.FREEZE_STAMPS:
                if "no_shift_one" in self.f and p == "drain.fedAgeH":
                    continue
                self._set(p, self._get(p) + gap)
            if "freeze_leak" in self.f:
                R["satiety"]["M"] += 5.0
            if "written_drift" in self.f:
                self.hunger += 0.01
            self.stats46["resumes"] += 1
            self.stats46["resumedH"] += gap
            self.resume_due, self.skip_next = False, True
            self._ring_only()
            return
        if self.skip_next:
            self.skip_next = False
            self._ring_only()
            return
        self.acute_minute()
        R["lastSeen"] = self.age
        R["kineticsAge"] = self.age
        R["satiety"]["t"] = self.age
        R["nutrients"]["lastAgeH"] = self.age
        R["body"]["lastAgeH"] = self.age
        super().minute()
        if self.ring and self.ring_on and self.ring[-1]["s"] == self.s:
            self.ring[-1]["cold"] = R["body"]["coldMult"]
        if self.dirty or (self.t - self.last_write_t >= 60.0 and "no_first_write" not in self.f):
            self.write_file()

    def write_file(self):
        """A slot write (S.step: at most once a real minute, or after a dirty mark) and its copy on the character."""
        self.file = copy.deepcopy(self.rec)
        self.copy = copy.deepcopy(self.rec)
        self.backup["writes"] += 1
        self.last_write_t, self.dirty = self.t, False
        self.last_write = 1000.0 + self.t * 1000.0

    @staticmethod
    def latest(rec):
        vs = []
        for p in L.FREEZE_STAMPS:
            d = rec
            for seg in p.split("."):
                d = d.get(seg) if isinstance(d, dict) else None
            if isinstance(d, (int, float)):
                vs.append(d)
        return max(vs) if vs else None

    def pick(self):
        """S.pick at the sight after a restart: the file ahead of the world loads the copy, else the file; then the
        resume puts the record on the world clock, forward (resumes) or back (rewound)."""
        self.pending_pick = False
        ahead = self.file is not None and self.latest(self.file) > self.age
        sv_copy = (self.saved or {}).get("copy")
        if ahead and sv_copy is not None and "keep_store" not in self.f:
            self.rec = copy.deepcopy(sv_copy)
            self.backup["restored"] += 1
        else:
            self.rec = copy.deepcopy(self.file)
            if ahead and sv_copy is None:
                self.backup["aheadKept"] += 1
        if "no_resume" in self.f:
            return
        gap = self.age - max(self.rec["lastSeen"], self.rec["kineticsAge"])
        for p in L.FREEZE_STAMPS:
            self._set(p, self._get(p) + gap)
        if gap > 0:
            self.stats46["resumes"] += 1
            self.stats46["resumedH"] += gap
        elif gap < 0:
            self.stats46["rewound"] = self.stats46.get("rewound", 0) + 1

    def _ring_only(self):
        if not self.ring_on:
            return
        self.s += 1
        row = {"s": self.s, "ev": self.s, "age": self.age, "dtM": 1.0, "on": True, "HUNGER": self.hunger,
               "THIRST": self.thirst, "FATIGUE": 0.0, "cold": self.rec["body"]["coldMult"]}
        for p in self.paths:
            ok, v = self.read_path(p)
            if ok:
                row[p] = v
        self.ring.append(row)

    def acute_minute(self):
        a, dt = self.rec["acute"], 1.0 / 60.0
        if not self.sleep_on:
            a["bodyOn"] = True if "clock_on_off" in self.f else False
            a["circ"] = 0.0
            a.update({"sleptH": 0.0, "boutH": 0.0, "gapH": 0.0, "winSleptH": 0.0})
            return
        if a["bodyOn"] is True:
            a["bodyHour"] = (a["bodyHour"] + dt) % 24.0
        elif "no_reseed" not in self.f:
            a["bodyHour"], a["bodyOn"] = L.world_hour(self.age), True
        else:
            a["bodyOn"] = True
        if self.asleep:
            a["sleptH"] += dt
            a["boutH"] += dt
            a["gapH"] = 0.0
            a["winSleptH"] += dt * (0.5 if "lose_sleep" in self.f else 1.0)
        else:
            a["sleptH"] = 0.0
            if a["boutH"] > 0:
                a["gapH"] += dt
                if a["gapH"] >= 10.0 / 60.0 - 1e-9:
                    thr = 1.0 if "nap_resets" in self.f else 4.0
                    if a["boutH"] + 1e-6 >= thr and "no_reset" not in self.f:
                        a["bodyHour"] = (7.0 + a["gapH"]) % 24.0
                    a["boutH"], a["gapH"] = 0.0, 0.0
        a["circ"] = self.circ_f()

    # -- paths
    def _get(self, p):
        d = self.rec
        for seg in split_path(p):
            d = d[seg]
        return d

    def _set(self, p, v):
        segs = split_path(p)
        d = self.rec
        for seg in segs[:-1]:
            d = d[seg]
        d[segs[-1]] = v

    def globals_(self):
        g_ = super().globals_()
        bh = (self.rec.get("acute") or {}).get("bodyHour", 0.0)
        circ = 1.0 if not self.sleep_on else 1.0 + 0.05 * math.cos(2 * math.pi * bh / 24)
        g_["NutritionRevamp.server.store.file.lastWrite.admin"] = self.last_write
        g_.update({"NutritionRevamp.server.writer.input.circ": circ,
                   "NutritionRevamp.server.options.sleepOn": self.sleep_on,
                   "NutritionRevamp.server.players.stalls": 0, "NutritionRevamp.server.players.substeps": 0,
                   "NutritionRevamp.server.minute.stats.runs": self.writes})
        for k, v in self.stats46.items():
            g_[f"NutritionRevamp.server.store.stats.{k}"] = v
        for k, v in self.backup.items():
            g_[f"NutritionRevamp.server.backup.stats.{k}"] = v
        for k, v in self.guard.items():
            g_[f"NutritionRevamp.server.eatGuard.stats.{k}"] = v
        return g_

    def read_path(self, p):
        if p.startswith("_G."):
            return super().read_path(p)
        d = self.rec
        for seg in split_path(p):
            if not isinstance(d, dict) or seg not in d:
                return False, None
            d = d[seg]
        return (d is not None and not isinstance(d, dict)), d

    # -- the eat and the drink
    def land(self, full):
        if full == L.MILKSOLID:
            if self.inv.get(full, 0) <= 0:
                return
            self.inv[full] -= 1
            self.eats += 1
            self.landed += 1
            self.rec["stomach"]["buffer"]["water"] += 453.87
            self.rec["stomach"]["buffer"]["calories"] += 314.15
            self.rec["satiety"]["M"] += 300.0
            self.meal_age = self.age
            self.hunger = 0.0
            return
        n0 = self.inv.get(full, 0)
        super().land(full)
        if self.inv.get(full, 0) < n0:
            self.rec["monotony"]["t"][full] = {"n": 1, "last": self.age}
            self.dirty = True                                    # an eat marks the slot (S.mark)

    def drink_done(self, full):
        super().drink_done(full)
        self.rec["stomach"]["liquid"] += 400.0

    # -- RCON
    def rcon(self, cmd):
        if cmd == "save":
            self.saved = {"copy": copy.deepcopy(self.copy), "age": self.age, "inv": dict(self.inv)}
            return True, "World saved"
        m = re.match(r"changeoption (\w+) (true|false)", cmd)
        if m:
            self.sleep_opt = m.group(2) == "true"
            self.opt_due = self.age + (5.0 if "poll_slow" in self.f else 0.0) / 60.0
            self.advance(0.3)                       # the RCON's round trip: about 0.5 game minutes between the reads
            return True, f"Option : {m.group(1)} is now : {m.group(2)}"
        return super().rcon(cmd)

    # -- the hooks the driver's main gives the session
    def launch(self, S, user, sub):
        """A fresh client restore: about 40 wall s from the call to the sight (x432: 34 s to ready), the world running
        (PauseEmpty false)."""
        self.online, self.resume_due = True, True
        S.xs.clients[user] = Client46(user, self, pid=7002)
        self.advance(40.0)
        return {"restored": True, "ready_took": 40.0}

    def kill(self, S):
        self.dead = True
        self.online = False
        pid = 4242
        return {"pid_recorded": pid, "pid_killed": 4343 if "kill_other" in self.f else pid, "alive_before": True,
                "taskkill_rc": 0, "exited": True, "rc": 1}

    def restart(self, S, tag):
        """The world and the characters as last saved (map_t.bin and players.db at the RCON save), the store's
        files as last written; the record leaves memory until the sight's load (pick)."""
        self.dead = False
        sv = self.saved
        if sv is not None:
            self.age = sv["age"]
            self.inv = dict(sv["inv"]) if "keep_inv" not in self.f else self.inv
        self.rec = {}
        self.pending_pick = True
        self.speed = 1.0
        self.advance(2.0)
        return {"ok": True, "took": 2.0, "pid": 5151, "log": f"server-stdout-{tag}.log"}

    # -- the bus
    def _answer(self, node, cmd, a):
        srv = node == L.SRV
        if self.dead and srv and cmd != "ping":
            return {"error": "TimeoutError: no answer"}
        if cmd == "players":
            return ["admin"] if self.online else []
        if cmd == "autodrink.set":
            return {"ok": True, "side": "server", "requested": a[1] == "true", "before": True,
                    "after": a[1] == "true"}
        if cmd == "player.sleep.hold":
            before = self.asleep
            self.asleep = float(a[1]) > 0 or self.asleep
            return {"user": a[0], "seconds": float(a[1]), "before": before, "after": self.asleep,
                    "armed": float(a[1]) > 0, "deadlineWall": int(self.t * 1000) + 1000 * int(float(a[1]))}
        if cmd == "player.sleep":
            before = self.asleep
            self.asleep = a[1] == "true"
            return {"requested": self.asleep, "before": before, "setAsleep": True, "after": self.asleep,
                    "held": True}
        if cmd == "witness.chain":
            chain = a[1] if srv else a[0]
            m = re.match(r"getInventory\.getCountTypeRecurse\(([^)]+)\)", chain)
            if m:
                return {"ok": True, "value": str(self.inv.get(m.group(1), 0)), "hops": 2}
        if cmd == "witness.moddata":
            return {"side": "server", "scope": "player", "arg": a[0], "values": {a[1]: self.age - 0.5, a[2]: 2},
                    "missing": {}, "worldAge": self.age, "resolved": True, "keys": ["NutritionRevamp"],
                    "keyCount": 1, "count": 2}
        if cmd == "tooltip.measure":
            on = a[1] == "1"
            leak = "tag_left" in self.f
            drawn = (not on) or "hide_off" in self.f
            return {"ok": not leak, "fullType": a[0], "hideOn": on, "height": 120 if drawn else 106,
                    "hungerLineDrawn": drawn, "bandShown": on, "wrapped": True, "vanilla": True,
                    "hungerChange": -0.16, "nativeTag": "native_tag" in self.f, "fill": 1.32, "heightBase": 120,
                    "heightOn": 106, "heightOff": 120, "lineDrop": 14, "lineSpacing": 14, "bandOn": True,
                    "bandOff": False, "hiddenOn": 1, "shownOn": 0, "tagAfter": leak, "tagLeft": leak,
                    "optionBefore": True, "restored": "not_restored" not in self.f}
        if cmd == "lua.global" and a[0] == L.FILE_LAST:
            doc = {"gen": 1, "rec": self.file if self.file is not None else {"satiety": {"t": self.age}},
                   "done": True}
            return {"side": "server", "name": a[0], "resolved": True, "type": "string", "value": json.dumps(doc)}
        if cmd == "lua.call" and not srv and a[0] == "NutritionRevamp.client.tooltip.optionOn":
            return {"ok": True, "side": "client", "path": a[0], "nargs": 0, "r1": True}
        if cmd == "fluid.fill":
            r = super()._answer(node, cmd, a)
            self.fluids_by[a[1]] = a[2]
            return r
        if cmd == "autodrink.probe":
            r = super()._answer(node, cmd, a)
            if r.get("item") is not None:
                r["fluid"] = self.fluids_by.get(r["item"], "Water")
            return r
        if cmd == "eat.action":
            st = self.rec["stomach"]
            m = L.mass_of({f"stomach.buffer.{k}": v for k, v in st["buffer"].items()} | {"stomach.liquid": st["liquid"]})
            if G.overfull_level(m) == 4 and "client_refuses" in self.f:          # never reaches the server
                return {"queued": True, "fraction": 1, "spawned": "found", "itemId": 7, "itemBefore": {},
                        "validStart": False, "maxTime": 120, "moodleFoodEaten": 3, "before": {}}
            if G.overfull_level(m) == 4 and "guard_off" not in self.f:
                self.guard["checks"] += 1
                self.guard["refused"] += 1
                self.guard["held"] += 1
                self.queue_left = "queue_left" in self.f
                cs = self.client_snap()
                return {"queued": True, "fraction": 1, "spawned": "found" if self.inv.get(a[0]) else "client",
                        "itemId": 7, "itemBefore": {}, "validStart": False, "maxTime": 120,
                        "moodleFoodEaten": cs["moodles"]["foodEaten"], "before": {}}
            if G.overfull_level(m) == 4:                                   # guard_off: the eat lands
                self.pending.append((self.t + 3.0, lambda fl=a[0]: self.land(fl)))
                return {"queued": True, "fraction": 1, "spawned": "found", "itemId": 7, "itemBefore": {},
                        "validStart": False, "maxTime": 120, "moodleFoodEaten": 3, "before": {}}
        if cmd == "action.cancel" and self.queue_left:
            self.queue_left = False
            return {"ok": True, "before": 1, "after": 0, "current": "ISEatFoodAction", "started": True,
                    "adding": False, "stopped": True, "javaBefore": 1, "javaAfter": 0, "cleared": True}
        if cmd == "minute.ring" and a[1] == "start":
            self.ring, self.s = [], 0
        return super()._answer(node, cmd, a)


def fresh_out():
    return T.fresh_out()


def run_session(key, tmp_path, monkeypatch, flags=(), budget=1e9, replay=None, prerun=None):
    os.makedirs(str(tmp_path), exist_ok=True)
    d = str(tmp_path)
    sleep_on = L.PROFILES[L.SESSIONS[key]["profile"]]["sleep"]
    w = World46(d, flags, sleep_on=sleep_on)
    ini = os.path.join(d, "pzt.ini")
    with open(ini, "w", encoding="utf-8") as fh:
        fh.write("PauseEmpty=false\nFastForwardMultiplier=%s\nSleepAllowed=%s\n"
                 % ("10.0" if "ff_changed" in flags else "40.0", "true" if sleep_on else "false"))
    if "no_late_write" in flags:
        monkeypatch.setattr(L, "LATE_WRITE_CAP_S", 0.0)
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={"admin": Client46("admin", w)}, ask=w.ask, budget_s=budget,
              clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = Server46(w, d, ini)
    if key == "x463b":
        db = os.path.join(d, *L.PLAYERS_DB_REL)
        os.makedirs(os.path.dirname(db), exist_ok=True)
        c = sqlite3.connect(db)
        c.execute("create table networkPlayers (id INTEGER PRIMARY KEY, username TEXT, data BLOB)")
        blob = b"x" * 4086 + (b"" if "no_copy" in flags else b"NutritionRevamp" + b"y" * 9000)
        c.execute("insert into networkPlayers (username, data) values (?, ?)", ("admin", blob))
        c.commit()
        c.close()
    if key == "x467":
        monkeypatch.setattr(G, "CAD_P_TARGETS", dict(T.FAKE_BANDS))
        monkeypatch.setattr(G, "CAD_H_TARGET", 8.0)
    S = L.Sess(xs, key, run_dir=d, launch=w.launch, kill=w.kill, restart=w.restart, prerun=prerun or {})

    def fake_replay(ring_rows, events, start, tol, **kw):
        n = len(ring_rows)
        d_ = replay if replay is not None else {"fields": {f: {"n": n, "max": 0.0, "over": 0, "worst_s": None}
                                                           for f in tol}, "findings": [], "classes": {}}

        class Be:
            ring_cold = kw.get("ring_cold") is not False
        return [{"s": r["s"]} for r in ring_rows], d_, Be()
    monkeypatch.setattr(L, "replay_grade", fake_replay)
    S.body_run(S.phases())
    out["logs"] = {"mod_error": []}
    out["admin_lua_error"] = False
    S.grade_all()
    v = {k: x["verdict"] for k, x in out["verdicts"].items()}
    return v, out, w, S


def bad(v, out):
    return {k: (x, out["verdicts"][k]["observed"]) for k, x in v.items() if x != "as_predicted"}


NAMES = {
    "x461a": {"REPLAY_HUNGER", "REPLAY_THIRST", "REPLAY_body.energyState", "REPLAY_stomachFill",
              "REPLAY_stomach.liquid", "COLD_FED", "OF_MIN_3", "OF_MIN_4", "OF_PEAK"},
    "x461b": {"REPLAY_HUNGER", "REPLAY_THIRST", "REPLAY_body.energyState", "REPLAY_stomachFill",
              "REPLAY_stomach.liquid", "COLD_FED", "W_PEAK", "W_HALF", "M_PEAK"},
    "x462": {"T_ON", "T_OFF", "T_NATIVE", "T_RESTORED"},
    "x463a": {"AWAY_STILL", "FREEZE", "STAMPS", "WRITTEN"},
    "x463b": {"KILL_OWN", "ROLLBACK", "RESTORED", "ON_CLOCK", "CONSISTENT", "COPY_SAVED"},
    "x464": {"TRACK", "NAP_KEEP", "FULL_RESET", "POLL_OFF", "NO_RHYTHM", "POLL_ON", "RESEED"},
    "x465": {"FF_DEFAULT", "NO_LOSS", "CAUGHT_UP"},
    "x466": {"REACHED", "REFUSED", "ITEM_INTACT", "RECORD_KEPT", "QUEUE_CLEARED", "DRINK_LANDS"},
    "x467": {"HYDRATED", "EAT0", "CAD_FEEL_P", "CAD_FEEL_H", "WF_SHOW", "WF_SPAN", "PAIRS_foodEaten", "PAIRS_hungry",
             "REPLAY_HUNGER", "REPLAY_THIRST", "REPLAY_body.energyState", "NO_RHYTHM_DAY"},
}
BANDED = {"OF_MIN_3", "OF_MIN_4", "OF_PEAK", "W_PEAK", "W_HALF", "M_PEAK"}   # the fake has no prerun of its own


# ---------------------------------------------------------------- each session end to end
@pytest.mark.parametrize("key", list(L.SESSIONS))
def test_session_as_predicted(key, tmp_path, monkeypatch):
    v, out, w, S = run_session(key, tmp_path, monkeypatch)
    assert not out["phase_errors"], out["phase_errors"]
    want = NAMES[key] | ({"Z"} if key in L.NO_RING else {"H1", "RING", "Z"})
    assert set(v) == want, set(v) ^ want
    graded = {k: x for k, x in v.items() if k not in BANDED}
    assert all(x == "as_predicted" for x in graded.values()), bad(graded, out)
    assert all(v[k] == "unmeasured" for k in BANDED & set(v))                # no prediction offline: never a pass
    assert out["checks"]["restore"]["ok"] is True and w.speed == 1.0
    if key not in L.NO_RING:
        assert len(out["checks"]["H"]["ring_paths"]) <= 32
    assert G.PAIR_SLACK_S == 0.3                                               # the frozen slack restored


def test_x461a_bands_graded_against_a_prerun(tmp_path, monkeypatch):
    v, out, _, _ = run_session("x461a", tmp_path, monkeypatch, prerun={"of_m3": 0.0, "of_m4": 0.0, "of_peak": 0.0})
    of = out["checks"]["overfull"]
    assert of["n"] > 0
    pr = {"of_m3": of["m3"], "of_m4": of["m4"], "of_peak": of["peak"]}
    v2, _, _, _ = run_session("x461a", tmp_path / "b", monkeypatch, prerun=pr)
    assert all(v2[k] == "as_predicted" for k in ("OF_MIN_3", "OF_MIN_4", "OF_PEAK"))
    pr_far = {"of_m3": of["m3"] + 10, "of_m4": of["m4"] + 10, "of_peak": of["peak"] + 100}
    v3, _, _, _ = run_session("x461a", tmp_path / "c", monkeypatch, prerun=pr_far)
    assert all(v3[k] == "falsified" for k in ("OF_MIN_3", "OF_MIN_4", "OF_PEAK"))


def test_x461b_records_the_three_courses(tmp_path, monkeypatch):
    v, out, w, S = run_session("x461b", tmp_path, monkeypatch)
    dr = out["checks"]["drinks"]
    assert [(d["container"], d["fluid"]) for d in dr] == [(L.BOTTLE, L.WATER), (L.CARTON, L.COWMILK)]
    assert all(d["fill_ok"] and d["landed"] for d in dr)
    assert out["checks"]["SO"]["eat"]["landed"] and not out["checks"]["SO"]["capped"]
    assert out["checks"]["S"]["autodrink"]["after"] is False
    liq = out["checks"]["liquid"]
    assert liq["water"]["peak"] is not None and liq["milk"]["peak"] is not None
    assert "cold_ablation" in out["checks"]


def test_x463a_reads_the_absence(tmp_path, monkeypatch):
    v, out, w, S = run_session("x463a", tmp_path, monkeypatch)
    o = out["checks"]["OFF"]
    assert o["rejoined"] and o["restore"]["ok"] and o["away_wait"]["done"]
    assert o["ring_pre"]["files"] and all(f.endswith("-pre.json") for f in o["ring_pre"]["files"])
    assert all(os.path.isfile(os.path.join(str(tmp_path), f)) for f in o["ring_pre"]["files"])
    assert out["verdicts"]["FREEZE"]["observed"]["gap_h"] >= L.AWAY_MIN_H
    assert any("c1b" in c for c in out["world_changes"]["left_in_place"])


def test_x463b_kills_only_its_own_pid_and_restarts(tmp_path, monkeypatch):
    v, out, w, S = run_session("x463b", tmp_path, monkeypatch)
    K = out["checks"]["KILL"]
    assert K["pid_recorded"] == K["pid_killed"] == 4242 and K["players_db"]["has_key"] is True
    assert K["client_pid"] == 7001 and K["client_killed"] is True and S.xs.clients.get("admin") is not None
    sv = out["checks"]["SAVE"]
    assert sv["copy_ready"] and sv["write_after_adv"] and sv["rcon"]["ok"]
    assert sv["existing_write"] is False                       # the fake's first write falls after ADV: SAVE waited
    assert out["verdicts"]["ON_CLOCK"]["observed"]["resumes"] + out["verdicts"]["ON_CLOCK"]["observed"]["rewound"] >= 1
    E = out["checks"]["EAT"]
    assert E["entry"] is not None and E["saved"] is True and E["late_write"] is True
    assert E["file_latest"] is not None and E["file_latest"] > sv["age"] + L.LATE_H     # read off the file's text
    U = out["checks"]["UP"]
    assert U["restart"]["ok"] and U["launch"]["ready_took"] and U["entry"] is None and U["count"] == 2
    assert out["verdicts"]["CONSISTENT"]["observed"]["eat_in_record"] is False
    assert out["verdicts"]["RESTORED"]["observed"]["direction"] == "forward"               # the save's copy
    assert out["verdicts"]["ROLLBACK"]["observed"]["file_latest_before_kill"] > U["sight_lastSeen"]


def test_x466_reads_the_queue_empty_before_the_eat(tmp_path, monkeypatch):
    v, out, w, S = run_session("x466", tmp_path, monkeypatch)
    q = out["checks"]["X"]["queue_before"]
    assert q["ok"] is True and q["before"] == 0 and q["current"] is None
    steps = [s["cmd"] for s in out["steps"] if s["phase"] == "X"]
    assert steps.index("action.cancel") < steps.index("eat.action")


def test_x464_the_clock_resets_only_on_the_full_sleep(tmp_path, monkeypatch):
    v, out, w, S = run_session("x464", tmp_path, monkeypatch)
    o = out["verdicts"]
    assert L.NAP_MIN_H <= o["NAP_KEEP"]["observed"]["bout_h"] < L.MAIN_SLEEP_H
    assert o["FULL_RESET"]["observed"]["bout_h"] >= L.MAIN_SLEEP_H
    assert o["FULL_RESET"]["observed"]["min_world_off_h"] > L.DISCRIM_H
    assert out["checks"]["NAP"]["reached"] and out["checks"]["FULL"]["reached"]
    off = out["checks"]["OFF"]
    assert off["flip_age"] is not None and off["flip_age"] > off["change_age_after"] > off["change_age"]
    assert off["poll_age"] is not None and off["gap_from_before_gm"] > out["verdicts"]["POLL_OFF"]["observed"]["gm"]
    assert out["verdicts"]["POLL_OFF"]["observed"]["change_age"] == off["change_age_after"]
    assert out["checks"]["sleep_allowed_before"] is True and out["checks"]["sleep_restored"] is True
    assert "sleep_restore" not in out["checks"] and w.sleep_on is True


def test_x464_restores_sleep_allowed_at_c_when_on_never_ran(tmp_path, monkeypatch):
    real = L.Sess.phase_ON464
    monkeypatch.setattr(L.Sess, "phase_ON464", lambda self: (_ for _ in ()).throw(RuntimeError("ON skipped")))
    v, out, w, S = run_session("x464", tmp_path, monkeypatch)
    assert out["checks"]["sleep_restore"]["ok"] and w.sleep_opt is True
    assert real is not None


def test_x461a_restores_the_auto_drink_flag(tmp_path, monkeypatch):
    v, out, w, S = run_session("x461a", tmp_path, monkeypatch)
    assert out["checks"]["S"]["autodrink"]["before"] is True
    assert out["checks"]["autodrink_restore"]["requested"] is True
    assert out["checks"]["overfull"]["reached_3"] in (True, False)


@pytest.mark.parametrize("key,flag,grades", [
    ("x461a", "client_stale", set()),                                    # no pair grade in x461a: nothing moves
    ("x462", "hide_off", {"T_ON"}),
    ("x462", "tag_left", {"T_ON", "T_OFF"}),
    ("x462", "native_tag", {"T_NATIVE"}),
    ("x462", "not_restored", {"T_RESTORED"}),
    ("x463a", "freeze_leak", {"FREEZE"}),
    ("x463a", "away_step", {"AWAY_STILL"}),
    ("x463a", "no_shift_one", {"STAMPS"}),
    ("x463a", "written_drift", {"WRITTEN"}),
    ("x463b", "kill_other", {"KILL_OWN"}),
    ("x463b", "keep_store", {"RESTORED"}),
    ("x463b", "keep_inv", {"CONSISTENT"}),
    ("x463b", "no_copy", {"COPY_SAVED"}),
    ("x463b", "no_late_write", {"ROLLBACK"}),
    ("x463b", "no_first_write", {"COPY_SAVED", "RESTORED"}),
    ("x463b", "no_resume", {"ON_CLOCK"}),
    ("x464", "nap_resets", {"NAP_KEEP"}),
    ("x464", "no_reset", {"FULL_RESET"}),
    ("x464", "poll_slow", {"POLL_OFF", "POLL_ON"}),
    ("x464", "clock_on_off", {"NO_RHYTHM"}),
    ("x464", "no_reseed", {"RESEED"}),
    ("x465", "ff_changed", {"FF_DEFAULT"}),
    ("x465", "lose_sleep", {"NO_LOSS"}),
    ("x466", "guard_off", {"REFUSED", "RECORD_KEPT", "ITEM_INTACT"}),
    ("x466", "queue_left", {"QUEUE_CLEARED"}),
    ("x466", "client_refuses", {"REFUSED", "ITEM_INTACT", "RECORD_KEPT", "QUEUE_CLEARED"}),
    ("x466", "fill_refused", {"DRINK_LANDS"}),
    ("x467", "fast_hunger", {"CAD_FEEL_P", "CAD_FEEL_H"}),
    ("x467", "client_stale", {"PAIRS_foodEaten", "PAIRS_hungry"}),
])
def test_each_defect_moves_its_grade(key, flag, grades, tmp_path, monkeypatch):
    v, out, _, _ = run_session(key, tmp_path, monkeypatch, flags=(flag,))
    for gname in grades:
        assert v.get(gname) != "as_predicted", (key, flag, gname, out["verdicts"].get(gname, {}).get("observed"))


def test_a_replay_over_the_tolerance_falsifies(tmp_path, monkeypatch):
    d = {"fields": {f: {"n": 10, "max": 0.0, "over": 0, "worst_s": None} for f in L.REPLAY_TOL}, "findings": [],
         "classes": {}}
    d["fields"]["THIRST"] = {"n": 10, "max": 0.01, "over": 3, "worst_s": 4}
    v, _, _, _ = run_session("x461a", tmp_path, monkeypatch, replay=d)
    assert v["REPLAY_THIRST"] == "falsified" and v["REPLAY_HUNGER"] == "as_predicted"


def test_the_budget_stops_the_scenario_and_keeps_the_closing_phases(tmp_path, monkeypatch):
    v, out, w, _ = run_session("x464", tmp_path, monkeypatch, budget=30.0)
    assert out.get("budget_stop") and "C" in out["phase_walls"] and "R" in out["phase_walls"]
    assert w.speed == 1.0 and v["FULL_RESET"] != "as_predicted"


# ---------------------------------------------------------------- the pure grades: pass, fail and unmeasured
def _ring(n, f, a0=3.2, step=1.0 / 60.0, **extra):
    out = []
    for i in range(n):
        r = {"s": i + 1, "age": a0 + i * step, "dtM": step * 60.0, "on": True}
        r.update(f(i, r["age"]))
        r.update(extra)
        out.append(r)
    return out


def test_grade_band_and_cold_fed():
    assert L.grade_band(3.0, 2.0, 1.0, "x")[0] == "as_predicted"
    assert L.grade_band(3.5, 2.0, 1.0, "x")[0] == "falsified"
    assert L.grade_band(None, 2.0, 1.0, "x")[0] == "unmeasured"
    assert L.grade_band(2.0, None, 1.0, "x")[0] == "unmeasured"
    rows = [{"cold": 1.0}, {"cold": 1.2}]
    assert L.grade_cold_fed(rows, True)[0] == "as_predicted"
    assert L.grade_cold_fed(rows, False)[0] == "falsified"
    assert L.grade_cold_fed([{"x": 1}], True)[0] == "falsified"
    assert L.grade_cold_fed([], True)[0] == "unmeasured"


def test_overfull_minutes_liquid_course_and_first_rise():
    masses = [500, 900, 1000, 1110, 1000, 800]
    zero = {p: 0.0 for p in G.STOMACH_PATHS}
    rows = [dict(zero, s=i, age=1 + i / 60, dtM=1.0, **{"stomach.liquid": m}) for i, m in enumerate(masses)]
    of = L.overfull_minutes(rows, 1.0)
    assert of["m3"] == 3.0 and of["m4"] == 1.0 and of["peak"] == 1110 and of["n"] == 5
    lc = L.liquid_course(rows, 1.0, 2.0)
    assert lc["peak"] == 1110 and lc["half_m"] is None
    lc2 = L.liquid_course(rows + [dict(zero, age=1.2, **{"stomach.liquid": 500})], 1.0, 2.0)
    assert lc2["half_m"] == pytest.approx((1.2 - (1 + 3 / 60)) * 60)
    r2 = [{"age": 1.0, "e": 0}, {"age": 1.1, "e": 0}, {"age": 1.2, "e": 1}]
    assert L.first_rise_age(r2, "e") == 1.2 and L.first_rise_age(r2, "e", after=1.3) is None


def _tm(on, **kw):
    r = {"ok": True, "hideOn": on, "vanilla": True, "hungerLineDrawn": not on, "tagLeft": False, "nativeTag": False,
         "restored": True}
    r.update(kw)
    return r


def test_grade_tooltip_native_restored():
    assert L.grade_tooltip(_tm(True), True)[0] == "as_predicted"
    assert L.grade_tooltip(_tm(False), False)[0] == "as_predicted"
    assert L.grade_tooltip(_tm(True, hungerLineDrawn=True), True)[0] == "falsified"
    assert L.grade_tooltip(_tm(False, hungerLineDrawn=False), False)[0] == "falsified"
    assert L.grade_tooltip(_tm(True, hideOn=False), True)[0] == "falsified"
    assert L.grade_tooltip(_tm(True, ok=False, tagLeft=True), True)[0] == "falsified"
    assert L.grade_tooltip(_tm(True, vanilla=False), True)[0] == "unmeasured"
    assert L.grade_tooltip("no item", True)[0] == "unmeasured"
    assert L.grade_native(_tm(True))[0] == "as_predicted"
    assert L.grade_native(_tm(True, nativeTag=True))[0] == "falsified"
    assert L.grade_native({})[0] == "unmeasured"
    assert L.grade_restored(_tm(True), _tm(False), True, True)[0] == "as_predicted"
    assert L.grade_restored(_tm(True, restored=False), _tm(False), True, True)[0] == "falsified"
    assert L.grade_restored(_tm(True), _tm(False), True, False)[0] == "falsified"
    assert L.grade_restored(_tm(True), _tm(False), None, True)[0] == "unmeasured"


def _away(ls=10.0, **kw):
    a = {p: 1.5 for p in L.FREEZE_VALUES}
    a.update({p: ls - 0.01 * i for i, p in enumerate(L.FREEZE_STAMPS)})
    a["lastSeen"] = ls
    a.update(kw)
    return a


def _resumed(away, gap, **kw):
    r = dict(away)
    for p in L.FREEZE_STAMPS:
        r[p] = away[p] + gap
    r.update({"s": 7, "on": True, "age": away["lastSeen"] + gap})
    r.update(kw)
    return r


def test_freeze_grades():
    a = _away()
    assert L.grade_away_still(a, dict(a))[0] == "as_predicted"
    assert L.grade_away_still(a, dict(a, **{"satiety.M": 1.6}))[0] == "falsified"
    assert L.grade_away_still(a, None)[0] == "unmeasured"
    rows = [dict(a, s=1, on=False), dict(a, s=2, on=True), _resumed(a, 80.0), _resumed(a, 80.0, **{"satiety.M": 1.4})]
    assert L.grade_freeze(rows, a)[0] == "as_predicted"
    assert L.grade_freeze([rows[0], rows[1], rows[3]], a)[0] == "falsified"
    assert L.grade_freeze([_resumed(a, 50.0)], a)[0] == "unmeasured"
    assert L.grade_freeze(rows[:2], a)[0] == "unmeasured"
    assert L.grade_stamps(rows, a, 80.0)[0] == "as_predicted"
    assert L.grade_stamps(rows, a, 79.0)[0] == "falsified"
    bad_row = _resumed(a, 80.0)
    bad_row["drain.fedAgeH"] = a["drain.fedAgeH"]
    assert L.grade_stamps([bad_row], a, None)[0] == "falsified"
    assert L.grade_stamps([], a)[0] == "unmeasured"
    pre = [{"on": True, "HUNGER": 0.10, "THIRST": 0.2, "FATIGUE": 0.0},
           {"on": True, "HUNGER": 0.11, "THIRST": 0.2, "FATIGUE": 0.0}]
    ret = [_resumed(a, 80.0, HUNGER=0.11, THIRST=0.2, FATIGUE=0.0)]
    assert L.grade_written(pre, ret, a)[0] == "as_predicted"
    assert L.grade_written(pre, [_resumed(a, 80.0, HUNGER=0.12, THIRST=0.2, FATIGUE=0.0)], a)[0] == "falsified"
    assert L.grade_written([], ret, a)[0] == "unmeasured"


def test_hardkill_grades(tmp_path):
    k = {"pid_recorded": 5, "pid_killed": 5, "alive_before": True, "taskkill_rc": 0, "exited": True}
    assert L.grade_kill_own(k)[0] == "as_predicted"
    assert L.grade_kill_own(dict(k, pid_killed=6))[0] == "falsified"
    assert L.grade_kill_own(dict(k, exited=False))[0] == "falsified"
    assert L.grade_kill_own(dict(k, alive_before=False))[0] == "falsified"
    assert L.grade_kill_own(dict(k, taskkill_rc=128))[0] == "falsified"
    assert L.grade_kill_own({})[0] == "unmeasured"
    up = {"age_restart": 4.0, "sight_lastSeen": 5.0}
    assert L.grade_rollback(up, {"file_latest": 6.0, "latest": 6.5})[0] == "as_predicted"
    assert L.grade_rollback(up, {"file_latest": 4.5, "latest": 6.5})[0] == "falsified"   # the FILE behind by the sight
    assert L.grade_rollback(up, {"latest": 6.5})[0] == "unmeasured"                       # the file unread
    assert L.grade_rollback({"age_restart": 4.0}, {"file_latest": 6.0})[0] == "unmeasured"

    def U(restored, ahead, rewound=0, resumes=0):
        return {"backup": {L.BACKUP_STATS[3]: restored, L.BACKUP_STATS[4]: ahead},
                "store": {L.STORE_STATS[4]: rewound, L.STORE_STATS[2]: resumes, L.STORE_STATS[3]: 1.1}}
    assert L.grade_restored_copy(U(1, 0, 0, 1), True)[0] == "as_predicted"           # forward: restored 1, rewound 0
    assert L.grade_restored_copy(U(1, 0, 0, 1), True)[1]["direction"] == "forward"
    assert L.grade_restored_copy(U(1, 0, 1, 0), True)[0] == "as_predicted"
    assert L.grade_restored_copy(U(0, 1), True)[0] == "falsified"                    # aheadKept 1
    assert L.grade_restored_copy(U(1, 1), True)[0] == "falsified"
    assert L.grade_restored_copy(U(0, 0), True)[0] == "falsified"
    assert L.grade_restored_copy(U(1, 0), False)[0] == "unmeasured"
    assert L.grade_restored_copy({"backup": {L.BACKUP_STATS[3]: 1}}, True)[0] == "unmeasured"
    st = {L.STORE_STATS[2]: 1, L.STORE_STATS[4]: 0}
    assert L.grade_on_clock({"record": {"latest": 5.0}, "age": 5.0 + 4 / 60, "store": st})[0] == "as_predicted"
    assert L.grade_on_clock({"record": {"latest": 5.0}, "age": 5.0 - 4 / 60,
                             "store": {L.STORE_STATS[2]: 0, L.STORE_STATS[4]: 1}})[0] == "as_predicted"
    assert L.grade_on_clock({"record": {"latest": 5.0}, "age": 5.1, "store": st})[0] == "falsified"
    assert L.grade_on_clock({"record": {"latest": 5.0}, "age": 5.0,                   # re-review N2: no resume ran
                             "store": {L.STORE_STATS[2]: 0, L.STORE_STATS[4]: 0}})[0] == "falsified"
    assert L.grade_on_clock({"record": {"latest": 5.0}, "age": 5.0})[0] == "unmeasured"
    assert L.grade_on_clock({"record": {"latest": 5.0}, "age": 5.0,                   # re-review N4: no rewound key
                             "store": {L.STORE_STATS[2]: 1}})[0] == "as_predicted"
    assert L.grade_on_clock({"record": {"latest": 5.0}, "age": 5.0, "store": {}})[0] == "unmeasured"
    assert L.grade_on_clock({"record": {"latest": None}, "age": 5.1, "store": st})[0] == "unmeasured"
    rec = {"values": {"lastSeen": 5.0}}
    assert L.grade_consistent({"entry": None, "count": 2, "record": rec}, {"count_before": 2}, True)[0] == "as_predicted"
    assert L.grade_consistent({"entry": 5.1, "count": 1, "record": rec}, {"count_before": 2}, True)[0] == "as_predicted"
    assert L.grade_consistent({"entry": None, "count": 1, "record": rec}, {"count_before": 2}, True)[0] == "falsified"
    assert L.grade_consistent({"entry": 5.1, "count": 2, "record": rec}, {"count_before": 2}, True)[0] == "falsified"
    assert L.grade_consistent({"entry": None, "count": 2, "record": rec}, {"count_before": 2}, False)[0] == "unmeasured"
    assert L.grade_consistent({"entry": None, "count": 2, "record": {"values": {}}}, {"count_before": 2},
                              True)[0] == "unmeasured"                                # review L4: a failed record read
    assert L.grade_copy_saved({"length": 9000, "has_key": True})[0] == "as_predicted"
    assert L.grade_copy_saved({"length": 4086, "has_key": False})[0] == "falsified"
    assert L.grade_copy_saved({"error": "locked"})[0] == "unmeasured"


def test_players_db_read_and_the_fixture_is_fresh(tmp_path):
    fr = L.fixture_fresh()
    assert fr["fresh"] is True and fr["length"] == 4086
    p = str(tmp_path / "players.db")
    c = sqlite3.connect(p)
    c.execute("create table networkPlayers (id INTEGER PRIMARY KEY, username TEXT, data BLOB)")
    c.execute("insert into networkPlayers (username, data) values ('admin', ?)", (b"abcNutritionRevampdef",))
    c.commit()
    c.close()
    assert L.players_db_read(p) == {"path": p, "length": 21, "has_key": True}
    assert "error" in L.players_db_read(str(tmp_path / "none.db"))
    assert L.fixture_fresh(str(tmp_path))["fresh"] is False
    # review L7: a store slot folder in the fixture defeats the first sight too
    fake = tmp_path / "repo"
    db = fake / L.FIXTURE_PLAYERS_DB
    db.parent.mkdir(parents=True)
    c = sqlite3.connect(str(db))
    c.execute("create table networkPlayers (id INTEGER PRIMARY KEY, username TEXT, data BLOB)")
    c.execute("insert into networkPlayers (username, data) values ('admin', ?)", (b"plain",))
    c.commit()
    c.close()
    assert L.fixture_fresh(str(fake))["fresh"] is True
    (fake / L.FIXTURE_STORE_DIR).mkdir(parents=True)
    r = L.fixture_fresh(str(fake))
    assert r["fresh"] is False and r["store_dir"] is True


def _clock_rows(a0, hours, body=None, on=True, **extra):
    n = int(hours * 60)
    out = []
    for i in range(n):
        a = a0 + i / 60.0
        out.append({"s": i, "age": a, "dtM": 1.0, "on": True, "acute.bodyOn": on,
                    "acute.bodyHour": L.world_hour(a) if body is None else body(a), **extra})
    return out


def test_track_and_reseed():
    rows = _clock_rows(3.2, 0.5)
    assert L.grade_track(rows, 3.0, 4.0)[0] == "as_predicted"
    off = _clock_rows(3.2, 0.5, body=lambda a: L.world_hour(a) + 0.2)
    assert L.grade_track(off, 3.0, 4.0)[0] == "falsified"
    assert L.grade_track(rows, 9.0, 10.0)[0] == "unmeasured"
    assert L.grade_reseed(rows, 3.0)[0] == "as_predicted"
    assert L.grade_reseed(off, 3.0)[0] == "falsified"
    assert L.grade_reseed(_clock_rows(3.2, 0.5, on=False), 3.0)[0] == "unmeasured"
    assert L.wrapdiff(0.5, 23.5) == pytest.approx(1.0) and L.wrapdiff(23.5, 0.5) == pytest.approx(-1.0)


def _sleep_rows(a0, asleep_h, awake_h, reset=True, body0=None):
    rows, bout, gap = [], 0.0, 0.0
    bh = L.world_hour(a0) if body0 is None else body0
    n1, n2 = int(asleep_h * 60), int((asleep_h + awake_h) * 60)
    for i in range(n2):
        a = a0 + (i + 1) / 60.0
        bh = (bh + 1 / 60.0) % 24
        if i < n1:
            slept, bout, gap = 1.0, bout + 1 / 60.0, 0.0
        else:
            slept = 0.0
            if bout > 0:
                gap += 1 / 60.0
                if gap >= 10 / 60.0 - 1e-9:
                    if bout >= 4 and reset:
                        bh = 7.0 + gap
                    bout, gap = 0.0, 0.0
        rows.append({"s": i, "age": a, "dtM": 1.0, "on": True, "acute.sleptH": slept, "acute.boutH": bout,
                     "acute.gapH": gap, "acute.bodyHour": bh, "acute.bodyOn": True})
    return rows


def test_nap_keep_and_full_reset():
    nap = _sleep_rows(4.0, 1.5, 0.3)
    assert L.grade_nap_keep(nap, 3.9, 6.0)[0] == "as_predicted"
    reset_nap = _sleep_rows(4.0, 1.5, 0.3)
    for r in reset_nap:
        if r["s"] >= 100:
            r["acute.bodyHour"] = 7.0 + (r["age"] - reset_nap[89]["age"])
    assert L.grade_nap_keep(reset_nap, 3.9, 6.0)[0] == "falsified"
    assert L.grade_nap_keep(_sleep_rows(4.0, 0.5, 0.3), 3.9, 6.0)[0] == "unmeasured"
    assert L.grade_nap_keep(_sleep_rows(4.0, 1.5, 0.05), 3.9, 6.0)[0] == "unmeasured"      # no close yet
    full = _sleep_rows(8.0, 5.0, 0.3)
    assert L.grade_full_reset(full, 7.9, 14.0)[0] == "as_predicted"
    assert L.grade_full_reset(_sleep_rows(8.0, 5.0, 0.3, reset=False), 7.9, 14.0)[0] == "falsified"
    assert L.grade_full_reset(_sleep_rows(8.0, 3.0, 0.3), 7.9, 14.0)[0] == "unmeasured"
    near = _sleep_rows(-5.2, 5.0, 0.3)                                   # wakes at world 07:00: no discrimination
    assert L.grade_full_reset(near, -6.0, 1.0)[0] == "unmeasured"


def test_poll_no_rhythm_and_the_day():
    ring = [{"s": i, "age": 5.0 + i / 60.0, "on": True, L.SLEEPON_G: i < 3} for i in range(6)]
    assert L.ring_flip(ring, 5.0 + 0.5 / 60.0, False) == pytest.approx(5.0 + 3 / 60.0)
    assert L.ring_flip(ring, 5.0, True) == pytest.approx(5.0 + 1 / 60.0)
    assert L.ring_flip(ring, None, False) is None and L.ring_flip(ring, 9.0, False) is None
    assert L.grade_poll(5.0, 5.0 + 1.0 / 60.0)[0] == "as_predicted"
    assert L.grade_poll(5.0, 5.0 + 2.2 / 60.0)[0] == "as_predicted"                # re-review N1: two events
    assert L.grade_poll(5.0, 5.0 + 3.0 / 60.0)[0] == "falsified"
    assert L.grade_poll(5.0, None)[0] == "falsified"
    assert L.grade_poll(None, 5.0)[0] == "unmeasured"
    ok = _clock_rows(5.0, 0.3, body=lambda a: 11.0, on=False, **{L.CIRC_G: 1.0, "acute.circ": 0.0})
    assert L.grade_no_rhythm(ok, 4.9, 6.0)[0] == "as_predicted"
    moved = _clock_rows(5.0, 0.3, body=lambda a: 11.0 + a, on=False, **{L.CIRC_G: 1.0, "acute.circ": 0.0})
    assert L.grade_no_rhythm(moved, 4.9, 6.0)[0] == "falsified"
    factor = _clock_rows(5.0, 0.3, body=lambda a: 11.0, on=False, **{L.CIRC_G: 0.95, "acute.circ": 0.0})
    assert L.grade_no_rhythm(factor, 4.9, 6.0)[0] == "falsified"
    circ = _clock_rows(5.0, 0.3, body=lambda a: 11.0, on=False, **{L.CIRC_G: 1.0, "acute.circ": 0.02})
    assert L.grade_no_rhythm(circ, 4.9, 6.0)[0] == "falsified"
    assert L.grade_no_rhythm(_clock_rows(5.0, 0.3, on=True, **{L.CIRC_G: 1.0, "acute.circ": 0.0}), 4.9,
                             6.0)[0] == "falsified"
    assert L.grade_no_rhythm(ok, 9.0, 10.0)[0] == "unmeasured"
    day = [{"s": 1, "age": 4.0, "on": True, "acute.bodyOn": False, L.CIRC_G: 1.0}]
    assert L.grade_no_rhythm_day(day)[0] == "as_predicted"
    assert L.grade_no_rhythm_day([dict(day[0], **{L.CIRC_G: 0.97})])[0] == "falsified"
    assert L.grade_no_rhythm_day([dict(day[0], **{"acute.bodyOn": True})])[0] == "falsified"
    assert L.grade_no_rhythm_day([{"s": 1, "age": 4.0, "on": True}])[0] == "unmeasured"
    assert L.grade_no_rhythm_day([])[0] == "unmeasured"


def _night(n_asleep, booked_scale=1.0, close=False, gap_rows=()):
    rows, win = [], 0.0
    for i in range(n_asleep + 4):
        asleep = 1 <= i <= n_asleep and i not in gap_rows
        if asleep:
            win += 3.2 / 60.0 * booked_scale
        rows.append({"s": i, "age": 4.0 + i * 3.2 / 60.0, "dtM": 3.2, "on": True,
                     "acute.sleptH": 0.05 if asleep else 0.0, "acute.winSleptH": win,
                     "acute.winStartH": 3.0 if not (close and i > 5) else 27.0, L.STALLS_G: 0, L.SUBSTEPS_G: 0})
    return rows


def test_night_grades():
    b = L.night_booking(_night(150), 3.9, 20.0)
    assert L.grade_no_loss(b)[0] == "as_predicted" and abs(b["booked_h"] - b["asleep_h"]) < 1e-9
    assert L.grade_no_loss(L.night_booking(_night(150, gap_rows=(20, 50)), 3.9, 20.0))[0] == "as_predicted"
    assert L.grade_no_loss(L.night_booking(_night(150, 0.95), 3.9, 20.0))[0] == "falsified"
    assert L.grade_no_loss(L.night_booking(_night(150, close=True), 3.9, 20.0))[0] == "unmeasured"
    assert L.grade_no_loss(L.night_booking(_night(5), 3.9, 20.0))[0] == "unmeasured"
    assert L.grade_no_loss(None)[0] == "unmeasured"
    lag0 = L.night_booking(_night(150), 3.9, 20.0, lag=0)
    assert lag0["asleep_h"] == pytest.approx(b["asleep_h"])
    assert L.grade_caught_up({"age": 10.0, "lastSeen": 10.0 - 1 / 60})[0] == "as_predicted"
    assert L.grade_caught_up({"age": 10.0, "lastSeen": 9.9})[0] == "falsified"
    assert L.grade_caught_up({})[0] == "unmeasured"
    assert L.grade_ff(40.0)[0] == "as_predicted" and L.grade_ff(20.0)[0] == "falsified"
    assert L.grade_ff(None)[0] == "unmeasured"


def _x(**kw):
    x = {"guard_before": {L.GUARD_PATHS[1]: 0, L.GUARD_PATHS[2]: 0},
         "guard_after": {L.GUARD_PATHS[1]: 1, L.GUARD_PATHS[2]: 1},
         "intake_before": {"landed": 3, "eats": 3}, "intake_after": {"landed": 3, "eats": 3},
         "item_before": {"id": 7, "hungChange": -9}, "item_after": {"id": 7, "hungChange": -9},
         "count_before": 2, "count_after": 2, "M_before": 500.0, "M_after": 499.0, "mass_before": 1150.0,
         "mass_after": 1148.0}
    x.update(kw)
    return x


def test_refusal_grades():
    assert L.grade_reached({"level": 4, "timer": 4400})[0] == "as_predicted"
    assert L.grade_reached({"level": 3, "timer": 4400})[0] == "falsified"
    assert L.grade_reached({"level": 4, "timer": 3000})[0] == "falsified"
    assert L.grade_reached({})[0] == "unmeasured"
    assert L.grade_refused(_x())[0] == "as_predicted"
    assert L.grade_refused(_x(intake_after={"landed": 4, "eats": 4}))[0] == "falsified"
    assert L.grade_refused(_x(guard_after={L.GUARD_PATHS[1]: 0, L.GUARD_PATHS[2]: 0}))[0] == "falsified"
    assert L.grade_refused(_x(guard_after={}))[0] == "unmeasured"
    assert L.server_saw(_x()) is True
    assert L.server_saw(_x(guard_after={L.GUARD_PATHS[1]: 0, L.GUARD_PATHS[2]: 0})) is False
    assert L.server_saw(_x(guard_after={L.GUARD_PATHS[1]: 1, L.GUARD_PATHS[2]: 0})) is False
    assert L.server_saw(_x(guard_after={})) is False
    assert L.grade_item_intact(_x())[0] == "as_predicted"
    assert L.grade_item_intact(_x(count_after=1))[0] == "falsified"
    assert L.grade_item_intact(_x(item_after={"id": 8, "hungChange": -9}))[0] == "falsified"
    assert L.grade_item_intact(_x(item_after={"id": 7, "hungChange": -4.5}))[0] == "falsified"
    assert L.grade_item_intact(_x(item_before={}))[0] == "unmeasured"
    assert L.grade_record_kept(_x())[0] == "as_predicted"
    assert L.grade_record_kept(_x(M_after=520.0))[0] == "falsified"
    assert L.grade_record_kept(_x(mass_after=1180.0))[0] == "falsified"
    assert L.grade_record_kept(_x(intake_after={"landed": 3, "eats": 4}))[0] == "falsified"
    assert L.grade_record_kept(_x(M_after=None))[0] == "unmeasured"
    assert L.grade_queue_cleared({"ok": True, "before": 0, "current": None})[0] == "as_predicted"
    assert L.grade_queue_cleared({"ok": True, "before": 1, "current": "ISEatFoodAction"})[0] == "falsified"
    assert L.grade_queue_cleared({"ok": False, "reason": "no local player"})[0] == "unmeasured"
    d = {"fill_ok": True, "landed": True, "drunk": 0.2}
    assert L.grade_drink_lands(d)[0] == "as_predicted"
    assert L.grade_drink_lands(dict(d, landed=False))[0] == "falsified"
    assert L.grade_drink_lands(dict(d, drunk=0.05))[0] == "falsified"
    assert L.grade_drink_lands(dict(d, fill_ok=False))[0] == "unmeasured"


# ---------------------------------------------------------------- the pre-boot checks on the real repository
@pytest.mark.parametrize("key", list(L.SESSIONS))
def test_preboot_on_the_repository_refuses_only_the_committed_artifact(key, monkeypatch):
    """Every session has run (Task 9 phase 2): its artifact is committed, so preboot now refuses a second boot on that
    check alone; every other check still passes on the repository. mod/'s head is held at the runs' STAGED_FROM: a
    later mod/ commit (Plan 16 Task 10's COMPATIBILITY.md, e69499be) moves it, and the staged-copy check is a pre-boot
    gate of runs that are done."""
    monkeypatch.setattr(L, "mod_head", lambda repo=None: L.STAGED_FROM)
    spec = L.SESSIONS[key]
    checks, ok = L.preboot(key, spec["profile"], key, spec["driver"],
                           compute=lambda keys: {k: L.PRERUN[k] for k in keys})
    skip = ("profile_checks", "harness_found", "fixture", "prerun")
    bad = {k: v for k, v in checks.items() if k not in skip and v is not True}
    assert ok is False and bad == {"no_prior_artifact": False}, bad
    assert all(v is True for k, v in checks["profile_checks"].items() if k != "error")


def test_preboot_refuses_a_committed_artifact(tmp_path):
    import shutil
    for d in ("testing/profiles",):
        shutil.copytree(os.path.join(REPO, d), tmp_path / d)
    for rel in list(L.HARNESS_FILES.values()) + [L.FIXTURE_PLAYERS_DB, L.PRERUN_FILE]:
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(os.path.join(REPO, rel), dst)
    (tmp_path / "testing" / "artifacts").mkdir()
    real_head = L.mod_head
    try:
        L.mod_head = lambda repo=None: L.STAGED_FROM   # the runs' staged commit: mod/ has moved past it (Plan 16 Task 10)
        c, ok = L.preboot("x462", "x46-mod", "x462", "x462_tooltip.py", repo=str(tmp_path))
        assert ok is True, {k: v for k, v in c.items() if v is not True}
        (tmp_path / "testing" / "artifacts" / "x462-20261019-000000").mkdir()
        c, ok = L.preboot("x462", "x46-mod", "x462", "x462_tooltip.py", repo=str(tmp_path))
        assert ok is False and c["no_prior_artifact"] is False
    finally:
        L.mod_head = real_head


def test_preboot_refuses_a_wrong_prefix_profile_file_or_stale_prerun():
    _, ok = L.preboot("x461a", "x46-mod", "x461b", "x461a_plate.py", compute=lambda k: {"x461a": L.PRERUN["x461a"]})
    assert ok is False
    _, ok = L.preboot("x461a", "x46-sleep", "x461a", "x461a_plate.py", compute=lambda k: {"x461a": L.PRERUN["x461a"]})
    assert ok is False
    _, ok = L.preboot("x461a", "x46-mod", "x461a", "x461b_drinks.py", compute=lambda k: {"x461a": L.PRERUN["x461a"]})
    assert ok is False
    stale = dict(L.PRERUN["x461a"], of_peak=1.0)
    checks, ok = L.preboot("x461a", "x46-mod", "x461a", "x461a_plate.py", compute=lambda k: {"x461a": stale})
    assert ok is False and checks["prerun_current"] is False
    checks, ok = L.preboot("x462", "x46-mod", "x462", "x462_tooltip.py", compute=lambda k: 1 / 0)
    assert checks["prerun"]["needed"] is False and checks["prerun_current"] is True   # no replay prediction to check
    c = L.prerun_current("x464", compute=lambda k: 1 / 0)
    assert c["ok"] is False and "ZeroDivisionError" in c["error"]


def test_profile_checks_fail_each_key():
    import tomllib
    text = open(os.path.join(REPO, "testing", "profiles", "x46-sleep.toml"), encoding="utf-8").read()
    doc = tomllib.loads(text)
    assert all(L.profile_doc_checks("x46-sleep", doc, text).values())
    assert L.profile_doc_checks("x46-mod", doc, text)["sleep_keys"] is False
    bad = copy.deepcopy(doc)
    bad["server"]["FastForwardMultiplier"] = 10.0
    assert L.profile_doc_checks("x46-sleep", bad, text)["no_fast_forward_override"] is False
    bad = copy.deepcopy(doc)
    bad["sandbox"]["Nutrition"] = True
    assert L.profile_doc_checks("x46-sleep", bad, text)["nutrition_false"] is False
    bad = copy.deepcopy(doc)
    bad["mods"][1]["path"] = "mod/NutritionRevamp"
    assert L.profile_doc_checks("x46-sleep", bad, text)["mods_staged"] is False
    assert L.profile_doc_checks("x46-sleep", doc, "# another header")["header_names_file"] is False
    assert L.profile_doc_checks("x99", doc, text) == {"known_profile": False}


def test_the_drivers_name_their_own_file_profile_and_artifact():
    import runpy
    for key, spec in L.SESSIONS.items():
        m = runpy.run_path(os.path.join(REPO, "testing", "experiments", spec["driver"]), run_name="not_main")
        assert m["KEY"] == m["PREFIX"] == key and m["PROFILE"] == spec["profile"] and m["ARTIFACT"] == spec["artifact"]
        if key == "x463b":                                                      # detached by the controller (N3)
            assert m["BUDGET_S"] == 600.0
        else:
            assert m["BUDGET_S"] + 60 <= 570                                    # under the 10-minute foreground cap
        assert set(m["PRED"]) >= NAMES[key] | {"Z"}


def test_the_staged_copy_gate_and_the_harness_markers():
    found, ok = L.harness_markers_ok()
    assert ok, {f: [k for k, v in d.items() if not v] for f, d in found.items()}
    mg = L.staged_gate()
    if mg.get("error") and "MANIFEST" in mg["error"]:
        pytest.skip("release/plan16-x46 is not staged on this machine")
    assert mg["ok"] and mg["staged_version"] == "1.0.0" and mg["commit"] == L.STAGED_FROM


def test_deployed_marker_check_on_a_real_run_layout(tmp_path):
    for fname, rel in L.HARNESS_FILES.items():
        dst = tmp_path / "server" / "mods" / "PZTestKit" / "42" / "media" / "lua" / os.path.basename(
            os.path.dirname(rel)) / fname
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(open(os.path.join(REPO, rel), encoding="utf-8", errors="replace").read(), encoding="utf-8")
    dm, ok = X.deployed_marker_check(str(tmp_path), list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)
    assert ok, dm
    first = next(iter(L.HARNESS_FILES))
    p = next(tmp_path.rglob(first))
    p.write_text(p.read_text(encoding="utf-8").replace('TK.register("', 'TK.reg("'), encoding="utf-8")
    assert X.deployed_marker_check(str(tmp_path), list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)[1] is False


# ---------------------------------------------------------------- the prerun
def test_the_committed_prerun_is_the_head_replay():
    have = L.load_prerun()
    now = PR.canonical(PR.compute())
    for k in L.PRERUN_KEYS:
        assert have.get(k) == now[k], k


def test_the_prerun_starts_at_the_first_sight_with_its_seed_plate():
    p = L.load_prerun()
    assert p["x461a"]["seed_kcal"] and p["x461a"]["seed_kcal"] > 300                 # the seed plate landed
    assert p["x467"]["seed_kcal"] == p["x461a"]["seed_kcal"]
    assert p["_provenance"]["first_sight"] == L.FIRST_SIGHT
    assert p["x465"]["miss_h"] == 0.0 and p["x465"]["stalls"][1] >= 1              # the carry exercised, nothing lost
    assert abs(p["x464"]["full_close_reset_off_h"]) < 1e-6 and abs(p["x464"]["full_close_world_off_h"]) > L.DISCRIM_H
    assert abs(p["x464"]["nap_close_off_h"]) < 1e-6 and abs(p["x464"]["seed_off_h"]) < 1e-6
    assert p["x466"]["seed_level"] == 4 and p["x466"]["level4_minutes"] >= 3
    assert all(v is not None for v in p["x467"]["cad_p"].values()) and p["x467"]["cad_h"] is not None
    assert p["x467"]["dehydrated_rows"] == 0


def test_the_prerun_command_checks_and_names_staleness(tmp_path, monkeypatch, capsys):
    assert PR.main(["--check", "x466"]) == 0
    fake = dict(L.load_prerun())
    fake["x466"] = dict(fake["x466"], level4_minutes=-1)
    path = tmp_path / "prerun.json"
    path.write_text(json.dumps(fake), encoding="utf-8")
    monkeypatch.setattr(L, "load_prerun", lambda p=None: json.loads(path.read_text(encoding="utf-8")))
    assert PR.main(["--check", "x466"]) == 1
    assert "x466" in capsys.readouterr().out


def test_install_bands_reads_the_prerun(monkeypatch):
    seen = {}
    L.install_bands({"x467": {"cad_p": {"lunch": 1.0, "dinner": 2.0, "breakfast": 3.0}, "cad_h": 9.0}},
                    setattr_=lambda o, k, v: seen.__setitem__(k, v))
    assert seen == {"CAD_P_TARGETS": {"lunch": 1.0, "dinner": 2.0, "breakfast": 3.0}, "CAD_H_TARGET": 9.0}
    assert G.CAD_H_TARGET == 9.550                                                   # the frozen module untouched


def test_x463b_takes_an_existing_write_without_waiting(tmp_path, monkeypatch):
    v, out, w, S = run_session("x463b", tmp_path, monkeypatch, flags=("early_write",))
    sv = out["checks"]["SAVE"]
    assert sv["existing_write"] is True and sv["write_after_adv"] is True and sv["copy_ready"] is True
    assert not [s_ for s_ in out["steps"] if s_["step"].startswith("SAVE_lw")]               # no wait
    assert v["RESTORED"] == "as_predicted" and v["ON_CLOCK"] == "as_predicted"


def test_the_x463b_caps_are_the_rereview_s(monkeypatch):
    assert L.RELAUNCH_TIMEOUT_S == 120.0 and L.RESTART_TIMEOUT_S == 150.0 and L.ON_CLOCK_GM == 5.0
    assert L.POLL_GM == 2.5

    class Prof:
        client_timeout, server_timeout, safemode, launcher = 180, 420, False, "java"
    seen = {}

    class C:
        proc = None

        def start(self):
            pass

        def wait_ready(self, timeout):
            seen["ready"] = timeout
            return 1.0

    class Srv:
        class bus:
            @staticmethod
            def reset():
                pass

        class _started:
            @staticmethod
            def clear():
                pass

        class proc:
            pid = 9

        def start(self, timeout):
            seen["start"] = timeout
            return 1.0

    class Tl:
        def mark(self, *a, **k):
            pass

    class Xs:
        server, clients, copied = Srv(), {}, []
    S = type("S", (), {"xs": Xs, "run_dir": "."})()
    L.launch_real(lambda *a, **k: (C(), True), Prof, {}, [], Tl())(S, "admin", "c1b")
    L.restart_real(Prof, ".", Tl())(S, "up")
    assert seen == {"ready": 120.0, "start": 150.0}
