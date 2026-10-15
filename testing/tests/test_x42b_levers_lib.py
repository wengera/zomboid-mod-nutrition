"""Offline tests of testing/experiments/x42b_levers_lib.py (Plan 13 Task 0, the x422 re-run; x42_levers_lib.py's tests copied): every grade of the x421 session run against
a fake world behind a fake bus, once as predicted and once per defect flag that must falsify it.

The fake bus answers the harness's real reply shapes. The three new commands' shapes come from their `@reply` lines
(testing/PZTestKit/PZTestKit/42/media/lua): `trait.def` {ok, side, trait, field, cost, free, xpBoosts, exclusive,
granted, label, description} (shared/PZTestKit_Core.lua), `creation.picks` {ok, armed, picks} and the client `perk.xp`
{perk, side, xp, level} (client/PZTestKit_Client.lua), `perk.park` {ok, perk, levelBefore, levelAfter, xpBefore,
xpAfter [, target]} (server/PZTestKit_Server.lua). The others are recorded shapes: `lua.callm` {ok, side, path, method,
nargs, r1} and `witness.chain` {ok, value} with value the string "true" (x192-20261006-194648 persist.json
boots.2.death), `lua.read` {ok, side, root, n, values, tables, types, missing}, `players` a list of usernames or {},
`stats.get` {weight, traitList, maxWeight, ...}, `xp.grant` {ok, perk, amount, side, xpBefore, xpAfter, levelBefore,
levelAfter}, `inventory.add` {ok, fullType, count, side, invWeight, maxWeight}, the rest per their `@reply` lines.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                                  # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x42b_levers_lib as L           # noqa: E402
import xlib as X                      # noqa: E402

TOTALS = [0, 75, 150, 300, 750, 1500, 3000, 4500, 6000, 7500, 9000]   # a stand-in Strength level table
BAND_TRAIT = {"weak": "weak", "feeble": "feeble", "stout": "stout", "strong": "strong"}


def fresh_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {},
            "world_changes": {"left_in_place": []}}


def vanilla_defs(f):
    obese = {"cost": 0, "free": True, "xpBoosts": {"Fitness": -2},
             "exclusive": ["athletic", "emaciated", "fit", "lighteater", "very underweight", "underweight",
                           "overweight"], "granted": {}}
    if not f.get("merge"):
        obese.update(cost=-10, free=False, xpBoosts={})
    under = {"cost": 0, "free": True, "xpBoosts": {} if not f.get("edit_fail") else {"Fitness": -1},
             "exclusive": ["obese", "very underweight", "overweight"], "granted": {}}
    over = {"cost": 0, "free": True, "xpBoosts": {"Fitness": -1},
            "exclusive": ["fit", "emaciated", "very underweight", "underweight", "obese"], "granted": {}}
    if f.get("edit_fail"):
        over["exclusive"] = ["athletic", "fit", "emaciated", "very underweight", "underweight"]
    return {"Obese": obese, "Underweight": under, "Overweight": over}


class World:
    """The server, bob's client and admin's client, a clock, a log file and an ini, all fake."""

    def __init__(self, flags, tmp):
        self.f = flags
        self.now = 1000.0
        self.log = os.path.join(tmp, "server-stdout.log")
        self.ini = os.path.join(tmp, "pzt.ini")
        with open(self.log, "w", encoding="utf-8") as fh:
            fh.write("LOG  : General boot\n")
        with open(self.ini, "w", encoding="utf-8") as fh:
            fh.write("AntiCheatSafety=2\nAntiCheatXP=2\n")
        self.sdefs = vanilla_defs(flags)
        self.cdefs = vanilla_defs(flags)
        if flags.get("client_diff"):
            self.cdefs["Overweight"] = dict(self.cdefs["Overweight"], cost=3)
        self.edit_errors = 1 if flags.get("edit_fail") else 0
        self.bob = {"weight": 80.0, "traits": {"nutritionist"}, "strength": 5, "xp": 1500.0, "protein": 120.0,
                    "dead": False, "online": True, "fitness_exe": 0}
        self.client = {"weight": 80.0, "traits": {"nutritionist"}, "strength": 5, "xp": 1500.0}
        self.newgame = None
        self.picks = None
        self.fired = None
        self.events = []
        self.dropped = 0
        self.calls = 0
        self.post_death_ui = False
        self.respawning = False
        self.in_pin = False

    # -- the clock
    def clock(self):
        return self.now

    def sleep(self, s):
        self.now += max(0.0, s)
        self.tick()

    def tick(self):
        b = self.bob
        if b["fitness_exe"] > 0:
            b["fitness_exe"] -= 1
            if b["fitness_exe"] == 0 and not self.f.get("silent_pushups"):
                self.addxp("Strength", 1.0 * L.protein_factor(b["protein"]), fitness=True)

    def log_line(self, s):
        with open(self.log, "a", encoding="utf-8") as fh:
            fh.write(s + "\n")

    # -- the server's recorder
    def addxp(self, perk, amount, fitness=False):
        self.calls += 1
        if len(self.events) >= L.EVENT_CAP:
            self.dropped += 1
            return
        self.events.append({"user": "bob", "perk": perk, "amount": amount, "ms": int(self.now * 1000),
                            "protein": self.bob["protein"], "fitness": fitness, "level": self.bob["strength"],
                            "xp": self.bob["xp"]})

    def server_g(self):
        ev = {i + 1: e for i, e in enumerate(self.events)}
        tl = {"version": 1, "edits": {"errors": self.edit_errors,
                                      **{k: {"ok": self.edit_errors == 0, "ret": "true"} for k in
                                         ("underweightFitness", "overweightAthletic", "overweightObese")}},
              "xp": {"n": len(self.events), "calls": self.calls, "dropped": self.dropped, "ev": ev}}
        if self.newgame is not None:
            tl["newGame"] = self.newgame
        return {"TKX_TraitLevers": tl,
                "SandboxVars": {"MultiplierConfig": {"Global": 1.0, "GlobalToggle": True, "Strength": 1.0},
                                "Nutrition": False, "DayLength": 1}}

    def client_g(self):
        g = {"TKX_TraitLevers": {"version": 1, "edits": {"errors": self.edit_errors,
                                                         **{k: {"ok": self.edit_errors == 0, "ret": "true"} for k in
                                                            ("underweightFitness", "overweightAthletic",
                                                             "overweightObese")}}},
             "TK": {}}
        if self.fired is not None:
            g["TK"]["picksFired"] = self.fired
        return g

    @staticmethod
    def lread(g, args, side):
        parts = args.split()
        root, paths = parts[0], parts[1:]
        node = g
        if root != "_G":
            for seg in root.split("."):
                node = node.get(seg) if isinstance(node, dict) else None
        out = {"ok": True, "side": side, "root": root, "n": len(paths), "values": {}, "tables": {}, "types": {},
               "missing": {}}
        for p in paths:
            cur = node
            for seg in p.split("."):
                if isinstance(cur, dict):
                    nxt = cur.get(seg)
                    if nxt is None and seg.isdigit():
                        nxt = cur.get(int(seg))
                    cur = nxt
                else:
                    cur = None
            if cur is None:
                out["missing"][p] = "nil"
            elif isinstance(cur, dict):
                out["tables"][p] = len(cur)
            else:
                out["values"][p] = cur
        return out

    def tdef(self, defs, name, side):
        d = defs.get(name)
        if d is None:
            return {"ok": False, "side": side, "trait": name, "reason": "no definition"}
        desc = "TKX-TRAITLEVERS-MARKER obese description" if name == "Obese" else "d"
        return {"ok": True, "side": side, "trait": name, "field": name.upper(), "label": name, "description": desc,
                "xpBoostsRead": not self.f.get("boosts_unread"), **d}

    # -- the respawn and the handler
    def create(self):
        b = self.bob
        before_traits = set(self.picks) if self.picks else {"nutritionist"}
        if self.picks and self.f.get("drop_picks"):
            before_traits = {"strong", "obese"}
        lvl = 5
        if "strong" in before_traits:
            lvl = 9
        before = {"traits": sorted(before_traits), "traitsStr": ",".join(sorted(before_traits)), "weight": 80.0,
                  "strength": lvl, "strengthXp": float(TOTALS[lvl]), "hasStrong": "strong" in before_traits}
        traits = set(before_traits)
        traits.discard("strong")
        traits.add("out of shape")
        step = "LoseLevel" if lvl == 10 else "LevelPerk"
        lvl = lvl - 1 if lvl == 10 else lvl + 1
        if not self.f.get("no_swap"):
            for t in L.BANDS:
                traits.discard(t)
            band = L.band_of(lvl)
            if band:
                traits.add(band)
        after = {"traits": sorted(traits), "traitsStr": ",".join(sorted(traits)), "weight": L.WEIGHT_TARGET,
                 "strength": lvl, "strengthXp": float(TOTALS[lvl - 1]), "hasStrong": "strong" in traits,
                 "hasOutOfShape": True}
        prev = self.newgame
        self.newgame = {"count": (prev["count"] if prev else 0) + 1, "user": "bob", "squareNil": True,
                        "before": before, "after": after,
                        "writes": {"step": step, "stepCall": {"ok": True, "ret": "nil"}, "weight": {"ok": True}}}
        b.update(weight=L.WEIGHT_TARGET, traits=set(traits), strength=lvl, xp=float(TOTALS[lvl - 1]), dead=False)
        if not self.f.get("no_reply_sync"):
            self.client.update(weight=b["weight"], traits=set(traits), strength=lvl, xp=b["xp"])
        self.picks = None

    # -- the bus
    def ask(self, node, cmd, args="", timeout=20):
        self.now += 0.05
        a = args.split()
        b = self.bob
        if node == "server":
            return self.server(cmd, a, args)
        if node == "client:bob":
            return self.bob_client(cmd, a, args)
        if node == "client":
            if cmd == "trait.def":
                return self.tdef(self.cdefs, a[0], "client")
            if cmd == "lua.read":
                return self.lread(self.client_g(), args, "client")
        return {"error": f"unknown {node} {cmd}"}

    def server(self, cmd, a, args):
        b = self.bob
        if cmd == "ping":
            return "pong"
        if cmd == "players":
            return ["admin", "bob"] if b["online"] else ["admin"]
        if cmd == "time.snapshot":
            return {"worldAge": 7.0, "hour": 14, "minutes": 0, "mult": 1.0, "trueMult": 1.0, "wall": self.now}
        if cmd == "witness.chain":
            chain = a[1]
            if chain == "getRole.getName":
                return {"ok": True, "value": self.f.get("role", "user"), "hops": 2}
            if chain == "getAccessLevel":
                return {"ok": True, "value": "None", "hops": 1}
            if chain == "isDead":
                return {"ok": True, "value": "true" if b["dead"] else "false", "hops": 1}
            if chain == "getFitness.getCurrentExe":
                return {"ok": True, "value": "pushups" if b["fitness_exe"] > 0 else None, "hops": 2}
        if cmd == "lua.read":
            return self.lread(self.server_g(), args, "server")
        if cmd == "trait.def":
            return self.tdef(self.sdefs, a[0], "server")
        if cmd == "health.reduce":
            b["dead"] = True
            self.post_death_ui = True
            return {"ok": True, "side": "server", "requested": 110, "before": 100, "after": 0, "health": 0, "parts": {}}
        if cmd == "lua.call":
            if a[0] == "TKX_TraitLevers.xpReset":
                self.events, self.calls, self.dropped = [], 0, 0
                return {"ok": True, "side": "server", "path": a[0], "nargs": 0, "r1": True}
            if a[0] == "TKX_TraitLevers.zombieNear":
                self.zombie = True
                return {"ok": True, "side": "server", "path": a[0], "nargs": 1, "r1": 1, "r2": 1.0}
        if cmd == "stats.get":
            return {"weight": b["weight"], "traitList": sorted(b["traits"]) or {}, "maxWeight": 15,
                    "wall": self.now}
        if cmd == "perk.xp":
            return {"perk": "Strength", "user": "bob", "side": "server", "xp": b["xp"], "level": b["strength"],
                    "serverWorldAge": 7.0}
        if cmd == "perk.level":
            before = b["strength"]
            b["strength"] = int(a[2])
            if self.f.get("debug_swaps"):
                for t in L.BANDS:
                    b["traits"].discard(t)
                    self.client["traits"].discard(t)
                band = L.band_of(b["strength"])
                if band:
                    b["traits"].add(band)
                    self.client["traits"].add(band)
            self.client["strength"] = b["strength"]
            return {"perk": "Strength", "requested": int(a[2]), "side": "server", "before": before,
                    "after": b["strength"], "xp": b["xp"]}
        if cmd == "perk.set":
            before = b["strength"]
            b["strength"] = int(a[2])
            b["xp"] = float(TOTALS[b["strength"]])
            return {"perk": "Strength", "requested": int(a[2]), "side": "server", "before": before,
                    "setPerkLevelDebug": True, "afterSetPerkLevelDebug": b["strength"], "setXPToLevel": True,
                    "after": b["strength"], "route": "setPerkLevelDebug"}
        if cmd == "perk.park":
            lb, xb = b["strength"], b["xp"]
            b["xp"] = float(TOTALS[int(a[2])])
            if int(a[2]) == L.PIN_LEVEL:
                self.in_pin = True
            return {"ok": True, "perk": "Strength", "levelBefore": lb, "levelAfter": b["strength"], "xpBefore": xb,
                    "xpAfter": b["xp"], "target": b["xp"]}
        if cmd == "xp.grant":
            amt = float(a[2])
            lb, xb = b["strength"], b["xp"]
            if not (self.f.get("park_stops") and b["strength"] == 10):
                landed = amt * L.protein_factor(b["protein"])
                if self.f.get("park_short") and b["strength"] == 10:
                    landed *= 0.5
                b["xp"] = min(TOTALS[10], b["xp"] + landed)
                if self.f.get("park_drops_level") and b["strength"] == 10:
                    b["strength"] = 9
                self.addxp("Strength", landed)
            if self.in_pin:
                if self.f.get("kick"):
                    b["online"] = False
                if self.f.get("ac_line"):
                    self.log_line("ERROR: Multiplayer AntiCheatXPUpdate: xp growth is too high Strength")
            return {"ok": True, "perk": "Strength", "amount": amt, "side": "server", "xpBefore": xb, "xpAfter": b["xp"],
                    "levelBefore": lb, "levelAfter": b["strength"]}
        if cmd == "inventory.add":
            self.load = getattr(self, "load", 0.0) + 3.0 * int(a[2])
            return {"ok": True, "fullType": a[1], "count": int(a[2]), "side": "server", "invWeight": self.load,
                    "maxWeight": 15}
        return {"error": f"unknown server {cmd}"}

    def bob_client(self, cmd, a, args):
        b = self.bob
        if cmd == "trait.def":
            return self.tdef(self.cdefs, a[0], "client")
        if cmd == "lua.read":
            return self.lread(self.client_g(), args, "client")
        if cmd == "lua.global":
            return {"type": "table"} if self.respawning else {"type": "nil"}
        if cmd == "lua.callm":
            path, method = a[0], a[1]
            base = {"ok": True, "side": "client", "path": path, "method": method, "nargs": 0}
            if path == "ISPostDeathUI.instance.0":
                if not self.post_death_ui:
                    return {"ok": False, "side": "client", "path": path, "method": method, "failedAt": "0"}
                if method == "onRespawn":
                    self.respawning = True
                    return base
                return dict(base, r1=True)
            if path == "CharacterCreationMain.instance":
                return dict(base, r1=True)
            if path in ("CoopMapSpawnSelect.instance", "CharacterCreationProfession.instance"):
                return dict(base, r1=False)
            if path == "CoopCharacterCreation.instance" and method == "accept":
                if self.picks is not None:
                    self.fired = {"count": (self.fired or {}).get("count", 0) + 1, "wall": int(self.now * 1000),
                                  "listAfter": {i + 1: p for i, p in enumerate(self.picks)}}
                self.post_death_ui, self.respawning = False, False
                self.create()
                return base
        if cmd == "creation.picks":
            self.picks = [L.norm(x) for x in a]
            return {"ok": True, "armed": True, "picks": a}
        if cmd == "stats.get":
            c = self.client
            return {"weight": c["weight"], "traitList": sorted(c["traits"]) or {}, "maxWeight": 15, "wall": self.now}
        if cmd == "perk.xp":
            return {"perk": "Strength", "side": "client", "xp": self.client["xp"], "level": self.client["strength"]}
        if cmd == "exercise.do":
            b["fitness_exe"] = 4
            return {"ok": True, "exercise": a[0], "minutes": int(a[1]), "queued": True, "queueLen": 1}
        if cmd == "attack.melee":
            if not getattr(self, "zombie", False):
                return {"ok": False, "reason": "no zombie within 2 tiles"}
            if not self.f.get("silent_melee"):
                self.addxp("Strength", 1.0 * L.protein_factor(b["protein"]))
            return {"ok": True, "target": {"x": 1, "y": 1, "dist": 1.0}, "swings": int(a[0]),
                    "weapon": "Base.BaseballBat", "result": "attack-melee", "file": "pzt-results/attack-melee.json"}
        if cmd == "player.walk":
            if not self.f.get("silent_walk"):
                self.addxp("Strength", 2.0 * L.protein_factor(b["protein"]))
            return {"dx": int(a[0]), "dy": int(a[1]), "run": False, "from": {"x": 0, "y": 0}, "target": {"x": 1},
                    "queued": True, "clientRunning": False, "clientMoving": True}
        return {"error": f"unknown client {cmd}"}


def session(flags, tmp_path):
    w = World(flags, str(tmp_path))
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: side, ask=w.ask, budget_s=1e9, clock=w.clock, sleep=w.sleep, user="admin")
    lv = L.Levers(xs, log_path=w.log, ini_path=w.ini)
    lv.body()
    lv.grade_all()
    return out, w


def verdicts(out):
    return {k: v["verdict"] for k, v in out["verdicts"].items()}


def test_the_fixed_world_grades_every_check_as_predicted(tmp_path):
    out, _ = session({}, tmp_path)
    assert out["phase_errors"] == {}
    assert verdicts(out) == {str(i): "as_predicted" for i in range(1, 10)}
    assert out["verdicts"]["6"]["observed"]["route_swaps"] is True
    assert out["verdicts"]["3"]["observed"]["marker_on_client"] is True
    assert out["checks"]["N2"]["fired"]["count"] == 1


@pytest.mark.parametrize("flag,check", [
    ("merge", "1"), ("edit_fail", "2"), ("client_diff", "3"), ("no_reply_sync", "4"), ("drop_picks", "5"),
    ("no_swap", "6"), ("debug_swaps", "6"), ("silent_walk", "7"), ("silent_melee", "7"), ("silent_pushups", "7"),
    ("park_stops", "8"), ("park_short", "8"), ("park_drops_level", "8"), ("kick", "9"), ("ac_line", "9")])
def test_each_defect_falsifies_its_check(tmp_path, flag, check):
    out, _ = session({flag: True}, tmp_path)
    assert out["phase_errors"] == {}
    assert out["verdicts"][check]["verdict"] == "falsified", out["verdicts"][check]


def test_a_silent_source_is_named(tmp_path):
    out, _ = session({"silent_walk": True}, tmp_path)
    assert out["verdicts"]["7"]["observed"]["silent_sources"] == ["walk"]


def test_an_admin_role_leaves_the_pin_unmeasured(tmp_path):
    out, _ = session({"role": "admin"}, tmp_path)
    assert out["verdicts"]["9"]["verdict"] == "unmeasured"


def test_the_respawn_route_reads_the_handler_and_three_pairs(tmp_path):
    out, w = session({}, tmp_path)
    n1 = out["checks"]["N1"]
    assert n1["landed"] and n1["count_after"] == 1
    assert [p["delay"] for p in n1["pairs"]] == list(L.PAIR_DELAYS_S)
    assert n1["newGame"]["after"]["strength"] == 6 and n1["newGame"]["writes"]["step"] == "LevelPerk"
    assert out["checks"]["N2"]["newGame"]["count"] == 2
    assert out["checks"]["S9"]["span_s"] >= L.PIN_WATCH_S


def test_a_death_that_never_lands_is_unmeasured_not_falsified():
    v, o = L.grade_newgame(None, [])
    assert v == "unmeasured"
    v, o = L.grade_illegal({"before": {"traitsStr": "strong"}}, {"count": 0})
    assert v == "unmeasured"


def test_a_pair_wider_than_a_wall_second_is_unmeasured():
    ng = {"after": {"strength": 6, "weight": 77.7, "traitsStr": "out of shape,stout"}}
    p = {"delay": 3.0, "server_stats": {"wall": 1.0, "weight": 77.7, "traitList": ["out of shape", "stout"]},
         "client_stats": {"wall": 2.5, "weight": 77.7, "traitList": ["out of shape", "stout"]},
         "server_xp": {"wall": 2.6, "level": 6}, "client_xp": {"wall": 2.7, "level": 6}}
    assert L.grade_newgame(ng, [p])[0] == "unmeasured"
    p["client_stats"]["wall"] = 1.2
    assert L.grade_newgame(ng, [p])[0] == "as_predicted"


def test_zero_source_windows_are_unmeasured():
    assert L.grade_sources({})[0] == "unmeasured"
    assert L.grade_sources({"walk": {"ran": False, "events": []}})[0] == "unmeasured"
    assert L.grade_sources({"walk": {"ran": True, "events": []}})[0] == "falsified"


def test_a_short_pin_watch_is_unmeasured():
    pin = {"role": "user", "anticheat_xp": "2", "polls": [{"online": True}], "span_s": 60.0}
    assert L.grade_pin(pin)[0] == "unmeasured"
    pin["span_s"] = 130.0
    assert L.grade_pin(pin)[0] == "as_predicted"
    pin["anticheat_xp"] = "4"
    assert L.grade_pin(pin)[0] == "unmeasured"


def test_the_pure_helpers():
    assert L.norm("OUT_OF_SHAPE") == L.norm("out of shape") == L.norm("base:out of shape") == "outofshape"
    assert [L.band_of(n) for n in (0, 1, 2, 4, 5, 6, 8, 9, 10)] == [
        "weak", "weak", "feeble", "feeble", None, "stout", "stout", "strong", "strong"]
    assert L.protein_factor(120) == 1.5 and L.protein_factor(50) == 1.0 and L.protein_factor(300) == 1.0
    assert L.protein_factor(-301) == 0.7 and L.protein_factor(None) is None
    assert L.sandbox_mult({"SandboxVars.MultiplierConfig.GlobalToggle": True,
                           "SandboxVars.MultiplierConfig.Global": 2.0,
                           "SandboxVars.MultiplierConfig.Strength": 3.0}) == 2.0
    assert L.sandbox_mult({"SandboxVars.MultiplierConfig.GlobalToggle": False,
                           "SandboxVars.MultiplierConfig.Global": 2.0,
                           "SandboxVars.MultiplierConfig.Strength": 3.0}) == 3.0
    assert L.names({}) == set() and L.names("a,b") == {"a", "b"} and L.names(["Out Of Shape"]) == {"outofshape"}
    rows = L.event_rows([{"values": {"TKX_TraitLevers.xp.ev.2.amount": 3, "TKX_TraitLevers.xp.ev.1.amount": 1,
                                     "TKX_TraitLevers.xp.ev.1.perk": "Strength"}}])
    assert [r["i"] for r in rows] == [1, 2] and rows[0]["perk"] == "Strength"


def test_the_event_read_pages_stay_inside_the_read_cap(tmp_path):
    out, w = session({}, tmp_path)
    reads = [s for s in out["steps"] if s["cmd"] == "lua.read" and "xp.ev." in s["args"]]
    assert reads and all(len(s["args"].split()) - 1 <= 64 for s in reads)


def test_an_unread_boost_map_leaves_checks_1_and_2_unmeasured(tmp_path):
    out, _ = session({"boosts_unread": True}, tmp_path)
    assert out["verdicts"]["1"]["verdict"] == "unmeasured"
    assert out["verdicts"]["2"]["verdict"] == "unmeasured"


def test_check_5_records_the_order_of_the_picks(tmp_path):
    out, _ = session({}, tmp_path)
    o = out["verdicts"]["5"]["observed"]
    assert len(o["pick_order"]) == 4 and isinstance(o["order_kept"], bool)
