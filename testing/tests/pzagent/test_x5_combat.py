"""drivers/x5_combat.py and base/gates.measure_x5 (Plan 22 Task 14, X5 "combat"), offline: the driver is never invoked.

The phases run against CombatMod, a FakeMod (every line through pza1.encode) ticking on a fake clock at 10 Hz: it
answers cmd.txt (equip, walkTo, attack, stop), emits the kit's item_added after the RCON additem, and per encounter a
zombie spawned at 4 tiles closing 0.5 tiles a frame; a walkTo ends when the zombie is within 2 tiles, the first
attack lands with attackStarted false and halves the zombie's health, the second with attackStarted true and
meleeDelay 40 kills it (a frame at health 0, then a zombie_dead event). The fake bus answers zombie.near, zombie.get,
damage.watch, item.get and players with the @reply shapes of PZTestKit_Server.lua (zombie.near L1927, damage.watch
and zombie.get Task 7's block at the file's end, players L16), the empty collections included (`{}` for an empty
Lua table)."""
import copy
import json
import os

import pytest

from agent.base import gates as GT
from agent.base import pza1
from agent.base.transport.files import FileTransport
from agent.drivers import x5_combat as D
from .fakemod import DEFAULT_FRAME, FakeMod

REPO = D.REPO
X = D.X


# ================================================================ static: refusal, constants, imports
def test_the_driver_refuses_arguments_before_main():
    with open(D.__file__, encoding="utf-8") as fh:
        src = fh.read()
    i_ref, i_main = src.index("refusal = parse_argv(sys.argv[1:], __file__)"), src.rindex("    main()")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    assert D.parse_argv(["x"], D.__file__) and D.parse_argv(["--help"], D.__file__)
    assert D.parse_argv([], D.__file__) is None


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(D.__file__) == D.DRIVER == D.KEY + ".py" == "x5_combat.py"
    assert D.KEY == "x5_combat" and D.ARTIFACT == "x5_combat.json"
    assert D.PROFILE == "testing/profiles/agent.toml" and os.path.isfile(os.path.join(REPO, D.PROFILE))
    want = {"BUDGET_S": 780.0, "USER": "admin", "MIN_FREE_GB": 12.0, "KIT": "Base.BaseballBat", "ENCOUNTERS": 5,
            "ENCOUNTER_S": 90.0, "STOP_HEALTH": 50.0, "PAIR_SLACK_S": 1.0, "KIT_TIMEOUT_S": 30.0,
            "EQUIP_TIMEOUT_S": 30.0, "FIGHT_HZ": 5, "GONE_S": 2.0, "HELLO_TIMEOUT_S": 60.0}
    for k, v in want.items():
        assert getattr(D, k) == v, k
        assert k == "USER" or D.CONSTANTS[k] == v, k
    assert D.PHASES == ("hello", "kit", "damage_hook", "encounters")
    assert D.PARK_RX == r"LuaError|STACK TRACE|attempted index|tried to call nil"
    assert GT.AGREE_TOL == 0.5


def test_nothing_is_imported_from_a_frozen_driver():
    src = open(D.__file__, encoding="utf-8").read()
    imports = [l.split("#")[0].strip() for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
    drivers = [l for l in imports if "drivers" in l or l.split()[1].split(".")[0] in (
        "a_pipe", "a_pipe_2", "a_pipe_3", "a_pipe_4", "b_actions", "b_actions_2", "c_survive", "c_survive_2",
        "c_survive_dense", "p22_probe", "x4_link")]
    assert drivers == [], drivers
    assert "import _dlib as DL" in imports and "import xlib as X" in imports
    assert "from agent.base.planner.policies import Fight, item_id_ok" in imports
    for frozen in ("agent.link", "agent.grades", "agent.world", "agent.policy", "link_for"):
        assert frozen not in src, frozen
    assert "X5(xs, FileTransport(DL.state_dir(clients[USER]))).run()" in src
    assert "make_client=clearing_make_client(session.make_client)" in src
    assert "def memory_gate(xs" in src and "DL.wait_memory" in src and "DL.clear_state_dir(c)" in src
    assert 'out["measure_x5"] = GT.measure_x5(out)' in src


def test_preboot_on_the_real_profile(agent_fixture, monkeypatch):
    monkeypatch.setattr(D.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(D.DL.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(D.DL.C, "git_dirty", lambda rel: (False, ""))
    real = D.DL.C.git_say
    tracked = {"v": ""}
    monkeypatch.setattr(D.DL.C, "git_say", lambda *a: tracked["v"] if a[0] == "ls-files" else real(*a))
    pre, ok = D.preboot(D.__file__)
    assert ok, pre
    assert pre["profile"] == "agent" and pre["driver_checks"]["driver_file"] is True
    tracked["v"] = "testing/artifacts/x5_combat-20261027-120000/x5_combat.json"
    assert D.preboot(D.__file__)[1] is False
    tracked["v"] = ""
    assert D.preboot(os.path.join(os.path.dirname(D.__file__), "x4_link.py"))[1] is False


def test_driver_checks_refuse_a_dirty_lua_base_or_driver():
    say = lambda *a: ""
    c, ok = D.driver_checks(D.__file__, git_say=say, git_dirty=lambda rel: (False, ""))
    assert ok and c["no_committed_artifact"] is True and c["profile_exists"] is True
    for dirty in ("testing/PZAgent", "testing/agent/base", "testing/agent/drivers/x5_combat.py"):
        c, ok = D.driver_checks(D.__file__, git_say=say, git_dirty=lambda rel, d=dirty: (rel == d, ""))
        assert ok is False, dirty
    c, ok = D.driver_checks(D.__file__, git_say=say, git_dirty=lambda rel: (None, "no git"))
    assert ok is False                                  # unknown is not clean
    c, ok = D.driver_checks(D.__file__, git_say=lambda *a: "testing/artifacts/x5_combat-1/x5_combat.json",
                            git_dirty=lambda rel: (False, ""))
    assert ok is False and c["no_committed_artifact"] is False


# ================================================================ CombatMod: the fake Lua on a fake clock
class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def now(self):
        return self.t


KIT_ID = 5001


class CombatMod(FakeMod):
    """The fake Lua: sleep(dt) runs its ticks (one frame a tick at 10 Hz) on the shared clock. Flags: `start_dist`
    (tiles a spawned zombie starts at), `body_drop` (the player's health lost at each zombie's first landed swing),
    `near_fail` (encounter numbers whose zombie.near spawns none), `dead_player` (players replies {}), `close` (tiles
    a zombie closes a frame), `bus_s` (seconds each bus reply takes), `ambient` (a still zombie, id 6000, listed at 9
    tiles from the first frame on, before any spawn), `vanish_ticks` (a spawned zombie leaves the frames that many
    ticks after its spawn with no zombie_dead event: a despawn), `reuse_ids` (every spawn takes online id 7001 again,
    as the server may reuse a dead zombie's id), `bus_dead_at` (the zombie.near of that encounter and every ping
    stall: a dead bus)."""
    SWING_TICKS = 3       # ticks from an attack's accept to its end
    REACH = 2.0           # tiles: a walkTo ends when the zombie is this close

    def __init__(self, d, clock, start_dist=4.0, body_drop=5.0, near_fail=(), dead_player=False, close=0.5,
                 bus_s=0.05, ambient=False, vanish_ticks=None, reuse_ids=False, bus_dead_at=None):
        super().__init__(d, clock=clock.now)
        self.clk = clock
        self.hz, self.x, self.y = 10, 100.5, 200.5
        self.start_dist, self.body_drop, self.near_fail = start_dist, body_drop, set(near_fail)
        self.dead_player, self.close, self.bus_s = dead_player, close, bus_s
        self.health, self.weapon, self.has_kit = 100.0, None, False
        self.zombies = {}            # id -> {dist, health, dead, gone, swings, age, still}
        if ambient:
            self.zombies[6000] = {"dist": 9.0, "health": 1.0, "dead": False, "gone": False, "swings": 0, "age": 0,
                                  "still": True}
        self.vanish_ticks, self.reuse_ids, self.bus_dead_at = vanish_ticks, reuse_ids, bus_dead_at
        self.next_id, self.nears = 7001, 0
        self.cmd_seen, self.walk, self.attack, self.pending = 0, None, None, []
        self.server_damage = []      # the server's damage.watch records {i, tag, amount, wall}
        self.since_calls = 0
        self.next_t = clock.t
        self.hello()
        self._tick()

    def sleep(self, dt):
        end = self.clk.t + dt
        while self.next_t <= end:
            self.clk.t = self.next_t
            self._tick()
            self.next_t += 1.0 / self.hz
        self.clk.t = end

    # -- the server's side ----------------------------------------------------------------------------------------
    def additem(self):
        self.has_kit = True
        self.pending.append({"itemId": KIT_ID, "fullType": D.KIT, "weight": 1.5})

    def spawn(self):
        zid = self.next_id
        if not self.reuse_ids:
            self.next_id += 1
        self.zombies[zid] = {"dist": self.start_dist, "health": 1.0, "dead": False, "gone": False, "swings": 0,
                             "age": 0, "still": False}
        return zid

    def zombie_get(self, zid):
        z = self.zombies.get(zid)
        if z is None:
            return {"ok": True, "side": "server", "id": zid, "found": False}
        return {"ok": True, "side": "server", "id": zid, "found": True, "health": z["health"],
                "x": self.x + z["dist"], "y": self.y, "z": 0, "dead": z["dead"]}

    # -- the Lua ------------------------------------------------------------------------------------------------
    def _live(self):
        return {i: z for i, z in self.zombies.items() if not z["dead"] and not z["gone"]}

    def _poll(self):
        p = os.path.join(self.dir, "cmd.txt")
        if not os.path.isfile(p):
            return
        with open(p, encoding="utf-8") as f:
            cmd = json.loads(f.read())
        if cmd["seq"] <= self.cmd_seen:
            return
        self.cmd_seen = cmd["seq"]
        t, aid, args = cmd["type"], cmd["aid"], cmd["args"]
        for run in (self.walk, self.attack):
            if run is not None:
                self.act(run["aid"], "failed", run["type"], reason="superseded")
        self.walk = self.attack = None
        if t == "attack" and args["targetId"] not in self._live():
            self.act(aid, "rejected", t, reason="no target")
            return
        self.act(aid, "accepted", t)
        if t == "equip":
            self.weapon = {"type": D.KIT, "cond": 1.0, "reach": 1.125, "ammo": None}
            self.act(aid, "done", t, result={})
        elif t == "stop":
            self.act(aid, "done", t, result={})
        elif t == "walkTo":
            self.walk = {"aid": aid, "type": t}
        elif t == "attack":
            self.attack = {"aid": aid, "type": t, "id": args["targetId"], "wait": self.SWING_TICKS}

    def _tick(self):
        self._poll()
        for ev in self.pending:
            self.event("item_added", **ev)
        self.pending = []
        for zid, z in self.zombies.items():
            if z["dead"] and not z["gone"]:
                z["gone"] = True
                self.event("zombie_dead", id=zid)
        for z in self._live().values():
            z["age"] += 1
            if self.vanish_ticks is not None and not z["still"] and z["age"] > self.vanish_ticks:
                z["gone"] = True
            elif not z["still"]:
                z["dist"] = max(1.0, z["dist"] - self.close)
        live = self._live()
        if self.walk is not None and (not live or min(z["dist"] for z in live.values()) <= self.REACH):
            self.act(self.walk["aid"], "done", "walkTo", result={})
            self.walk = None
        if self.attack is not None:
            self.attack["wait"] -= 1
            if self.attack["wait"] <= 0:
                self._swing()
        zs = [{"id": i, "x": self.x + z["dist"], "y": self.y, "dist": z["dist"], "hasTarget": True,
               "crawler": False, "health": z["health"]} for i, z in self.zombies.items() if not z["gone"]]
        me = dict(DEFAULT_FRAME["me"], x=self.x, y=self.y)
        self.frame(me=me, body=dict(DEFAULT_FRAME["body"], health=self.health), weapon=self.weapon, zombies=zs)

    def _swing(self):
        a, self.attack = self.attack, None
        z = self.zombies[a["id"]]
        z["swings"] += 1
        if z["swings"] == 1:
            z["health"] = 0.5
            self.health -= self.body_drop
            self.server_damage.append({"i": len(self.server_damage) + 1, "tag": "ZOMBIE", "amount": self.body_drop,
                                       "wall": int(self.clk.t * 1000)})
            res = {"swings": 1, "attackStarted": False, "meleeDelay": 0, "targetDead": False}
        else:
            z["health"], z["dead"] = 0.0, True
            res = {"swings": 1, "attackStarted": True, "meleeDelay": 40, "targetDead": True}
        self.act(a["aid"], "done", "attack", result=res)


class FakeServer:
    def __init__(self, mod):
        self.mod, self.errors = mod, []

    def rcon(self, cmd):
        self.mod.additem()
        return True, "Item %s Added in admin's inventory." % D.KIT


def make_ask(mod, clock, asked):
    def ask(node, cmd, args, timeout=30):
        asked.append((node, cmd, args, timeout))
        mod.sleep(mod.bus_s)
        if cmd == "item.get":
            if not mod.has_kit:
                return "no item %s in admin's inventory" % D.KIT
            return {"fullType": D.KIT, "id": KIT_ID, "uses": 1, "age": 0, "weight": 1.5}
        if cmd == "ping" or (cmd == "zombie.near" and mod.nears + 1 == mod.bus_dead_at):
            return {"error": "TimeoutError: no reply within %s s" % timeout}
        if cmd == "zombie.near":
            mod.nears += 1
            if mod.nears in mod.near_fail:
                return {"ok": False, "requested": 1, "spawned": 0, "at": {"x": 100, "y": 200, "z": 0}, "dists": {},
                        "reason": "spawned 0 of 1"}
            mod.spawn()
            return {"ok": True, "requested": 1, "spawned": 1, "at": {"x": 100, "y": 200, "z": 0},
                    "dists": [mod.start_dist]}
        if cmd == "zombie.get":
            return mod.zombie_get(int(args))
        if cmd == "damage.watch":
            parts = args.split()
            since = int(parts[2]) if len(parts) == 3 else 0
            if len(parts) == 3:
                mod.since_calls += 1
            counts = {}
            for r in mod.server_damage:
                counts[r["tag"]] = counts.get(r["tag"], 0) + 1
            last = [dict(r) for r in mod.server_damage if r["i"] > since]
            return {"ok": True, "side": "server", "hooked": True, "user": parts[0], "counts": counts or {},
                    "n": len(mod.server_damage), "last": last or {}, "dropped": 0}
        if cmd == "players":
            return {} if mod.dead_player else ["admin"]
        return {"error": "unknown command " + cmd}
    return ask


def run_x5(tmp_path, budget_s=1e9, **flags):
    clock = Clock()
    sd = str(tmp_path / "clients" / "admin" / "Lua" / "pzagent" / "admin")
    mod = CombatMod(sd, clock, **flags)
    out = D.new_out()
    asked = []
    xs = X.Xs(out, node=lambda side: side, server=FakeServer(mod), ask=make_ask(mod, clock, asked), clock=clock.now,
              sleep=mod.sleep, budget_s=budget_s, user="admin")
    xs.path = str(tmp_path / D.ARTIFACT)
    x5 = D.X5(xs, FileTransport(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep)
    x5.run()
    out["frames"]["parks"] = 0              # main's read_logs: the console read, no client here
    out["finished"] = True
    return out, mod, asked, x5


@pytest.fixture(scope="module")
def clean_run(tmp_path_factory):
    return run_x5(tmp_path_factory.mktemp("x5"))


def _act(lines, aid, states):
    return next(l for l in lines if l.get("kind") == "act" and l.get("aid") == aid and l.get("state") in states)


# ================================================================ the fake run: every phase's reading and the measure
def test_a_clean_fake_run_reads_every_phase(clean_run):
    out, mod, asked, x5 = clean_run
    assert out["phase_errors"] == {} and out.get("budget_stop") is None
    rd = out["readings"]
    assert list(rd) == list(D.PHASES)
    assert rd["hello"]["ok"] and rd["hello"]["proto"] == "PZA/1"
    kit = rd["kit"]
    assert kit["spawn"]["confirmed"] is True and kit["item"]["itemId"] == KIT_ID
    assert kit["item"]["source"] == "item_added" and kit["equip"]["state"] == "done"
    assert kit["weapon_frame"]["type"] == D.KIT and kit["ok"] is True
    dh = rd["damage_hook"]
    assert dh["hooked"] is True and dh["n"] == 0 and dh["counts"] == {} and dh["last_i"] == 0
    rows = rd["encounters"]["rows"]
    assert [r["i"] for r in rows] == [1, 2, 3, 4, 5] and all(r["void"] is None for r in rows)
    assert out["stop"]["reason"] == "encounters"
    for k, r in enumerate(rows):
        assert r["zid"] == 7001 + k and r["near"]["spawned"] == 1
        assert r["end"]["reason"] == "dead" and r["killed"] is True
        assert [a["type"] for a in r["actions"]] == ["walkTo", "attack", "attack"], r["actions"]
        assert [s["state"] for s in r["swings"]] == ["done", "done"]
        s1, s2 = r["swings"]
        assert s1["result"]["attackStarted"] is False and s2["result"] == {"swings": 1, "attackStarted": True,
                                                                            "meleeDelay": 40, "targetDead": True}
        assert s1["client_health_before"] == 1.0 and s1["client_health_after"] == 0.5
        assert s2["client_health_before"] == 0.5 and s2["client_health_after"] == 0.0
        assert s1["server_before"]["health"] == 1.0 and s1["server_after"]["health"] == 0.5
        assert s2["server_before"]["health"] == 0.5 and s2["server_after"]["dead"] is True
        for s in (s1, s2):
            assert s["pair_void"] is False and s["pair_after"]["dt_ms"] <= 1000.0
            assert s["pair_before"]["void"] is False
            assert s["targetId"] == r["zid"] and s["accepted_wallMs"] < s["ended_wallMs"]
            assert set(s) >= {"aid", "accepted_wall", "ended_wall", "state", "reason", "result",
                              "client_health_before", "client_health_after", "server_before", "server_after",
                              "pair_void", "loop_ms"}
        assert r["health_lost"] == pytest.approx(5.0) and r["server_tags"] == {"ZOMBIE": 1}
        assert r["damage"]["since"] == k and r["damage"]["ok"] is True
        dists = [p["dist"] for p in r["approach"]]
        assert dists[0] == pytest.approx(3.5) and dists == sorted(dists, reverse=True) and len(dists) >= 3
        assert r["server_end"]["dead"] is True and r["players"] == ["admin"]
    zgets = [a for a in asked if a[1] == "zombie.get"]
    assert len(zgets) == 5 * 5                         # per swing a before and an after, per encounter an end read
    assert all(a[3] == D.SERVER_TIMEOUT_S for a in asked if a[1] in ("zombie.get", "zombie.near", "damage.watch"))
    assert x5.world.damage_counts_server == {"ZOMBIE": 5} and len(x5.world.damage) == 5
    fr = out["frames"]
    assert fr["n"] == len(fr["cost"]) and fr["gaps"] == 0 and fr["bad"] == 0 and fr["lua_errors"] == 0
    json.dumps(out, allow_nan=False)                    # the artifact persists as plain JSON
    assert os.path.isfile(x5.xs.path)


def test_the_measure_reads_the_clean_run(clean_run):
    out = clean_run[0]
    m = GT.measure_x5(out)
    assert m["measure"] == "measure_x5" and "verdict" not in m
    assert m["attack_started_share"] == {"share": 0.5, "started": 5, "n": 10}
    assert m["melee_delay"] == {"min": 0, "p50": 0, "max": 40, "n": 10}
    ag = m["client_server_agreement"]
    assert ag["share"] == 1.0 and ag["n"] == 10 and ag["voided"] == 0 and ag["tol"] == 0.5
    assert m["loop_ms"]["n"] == 5 and m["loop_ms"]["p50"] > 0 and m["loop_ms"]["p90"] >= m["loop_ms"]["p50"]
    assert m["kills"] == {"n": 5, "per_encounter": [True] * 5}
    assert m["health_lost"] == [pytest.approx(5.0)] * 5
    assert m["server_tags"] == [{"ZOMBIE": 1}] * 5
    assert m["encounters"] == {"n": 5, "voided": 0}
    assert m["stop"]["reason"] == "encounters"
    json.dumps(m, allow_nan=False)


def test_loop_ms_is_the_first_actions_accept_minus_the_first_sight(clean_run):
    out, mod, asked, x5 = clean_run
    for r in out["readings"]["encounters"]["rows"]:
        first = r["actions"][0]
        acc = _act(x5.lines, first["aid"], ("accepted",))
        assert r["loop_ms"] == acc["wallMs"] - r["seen"]["wallMs"] and r["loop_ms"] > 0
        sight = next(l for l in x5.lines if l.get("kind") == "frame" and l["seq"] == r["seen"]["seq"])
        assert any(z["id"] == r["zid"] for z in sight["zombies"])
        assert all(s["loop_ms"] is None for s in r["swings"])     # the first action is the walk


def test_loop_ms_sits_on_the_first_swing_when_the_first_action_is_an_attack(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "ENCOUNTERS", 1)
    out, mod, asked, x5 = run_x5(tmp_path, start_dist=1.5)
    r = out["readings"]["encounters"]["rows"][0]
    assert [a["type"] for a in r["actions"]] == ["attack", "attack"]
    acc = _act(x5.lines, r["swings"][0]["aid"], ("accepted",))
    assert r["swings"][0]["loop_ms"] == r["loop_ms"] == acc["wallMs"] - r["seen"]["wallMs"]
    assert r["swings"][1]["loop_ms"] is None


def test_a_spawn_of_none_voids_its_encounter_and_the_rest_run(tmp_path):
    out, mod, asked, x5 = run_x5(tmp_path, near_fail={2})
    rows = out["readings"]["encounters"]["rows"]
    assert len(rows) == 5 and rows[1]["void"].startswith("zombie.near") and rows[1]["swings"] == []
    assert rows[1]["near"]["spawned"] == 0 and rows[1]["killed"] is None
    m = GT.measure_x5(out)
    assert m["encounters"] == {"n": 5, "voided": 1} and m["kills"]["n"] == 4
    assert m["kills"]["per_encounter"] == [True, None, True, True, True]
    assert m["attack_started_share"]["n"] == 8


def test_the_stop_at_stop_health_ends_the_session(tmp_path):
    out, mod, asked, x5 = run_x5(tmp_path, body_drop=30.0)
    rows = out["readings"]["encounters"]["rows"]
    assert out["stop"]["reason"] == "health" and len(rows) == 2
    assert rows[0]["end"]["reason"] == "dead" and rows[1]["end"]["reason"] == "stop"
    assert len(rows[1]["swings"]) == 1 and rows[1]["stopped_aid"] is None     # stopped before the next send
    assert out["stop"]["encounter"] == 2 and rows[1]["killed"] is False
    assert GT.measure_x5(out)["health_lost"] == [pytest.approx(30.0)] * 2


def test_an_encounter_past_encounter_s_stops_its_running_walk(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "ENCOUNTERS", 1)
    monkeypatch.setattr(D, "ENCOUNTER_S", 3.0)
    out, mod, asked, x5 = run_x5(tmp_path, start_dist=8.0, close=0.0)
    r = out["readings"]["encounters"]["rows"][0]
    assert r["end"]["reason"] == "timeout" and r["killed"] is False and r["swings"] == []
    assert r["stopped_aid"] is not None and _act(x5.lines, r["stopped_aid"], ("done",))
    assert [(a["type"], a["state"], a["reason"]) for a in r["actions"]] == [("walkTo", "failed", "superseded")]
    assert r["server_end"]["dead"] is False and r["server_end"]["health"] == 1.0
    assert len(r["approach"]) >= 25 and {p["dist"] for p in r["approach"]} == {8.0}
    assert out["stop"]["reason"] == "encounters"


def test_a_players_reply_without_the_user_is_a_death(tmp_path):
    out, mod, asked, x5 = run_x5(tmp_path, dead_player=True)
    assert out["stop"]["reason"] == "death" and len(out["readings"]["encounters"]["rows"]) == 1
    assert out["readings"]["encounters"]["rows"][0]["players"] == []


def test_the_budgets_reserve_stops_the_encounters(tmp_path):
    out, mod, asked, x5 = run_x5(tmp_path, budget_s=D.RESERVE_S + 6.0)
    assert out["stop"]["reason"] == "budget" and out.get("budget_stop") is None
    assert len(out["readings"]["encounters"]["rows"]) < 5


def test_no_hello_skips_every_phase(tmp_path):
    clock = Clock()
    sd = str(tmp_path / "sd")
    os.makedirs(sd)
    out = D.new_out()
    step = lambda dt: setattr(clock, "t", clock.t + dt)
    xs = X.Xs(out, node=lambda side: side, ask=lambda *a, **k: ["admin"], clock=clock.now, sleep=step,
              budget_s=1e9, user="admin")
    D.X5(xs, FileTransport(sd, clock=clock.now), clock=clock.now, sleep=step).run()
    assert "hello" in out["phase_errors"] and list(out["readings"]) == ["hello"]
    assert out["stop"]["reason"] == "no_hello"
    m = GT.measure_x5(out)
    assert m["encounters"] == {"n": 0, "voided": 0} and m["loop_ms"]["n"] == 0


# ================================================================ the builders, alone
def _lines(tmp_path, write):
    clock = Clock()
    mod = FakeMod(str(tmp_path / "b"), clock=clock.now)
    write(mod, clock)
    return FileTransport(str(tmp_path / "b")).lines()


def _zframe(mod, health, zid=9):
    return mod.frame(zombies=[{"id": zid, "x": 101.0, "y": 200.0, "dist": 1.0, "hasTarget": True,
                               "crawler": False, "health": health}])


def test_a_pair_1_5_s_apart_is_voided_and_1_0_s_is_kept(tmp_path):
    def write(mod, clock):
        _zframe(mod, 0.8)                               # wallMs t0
        clock.t += 1.0
        _zframe(mod, 0.6)                               # t0 + 1000
    lines = _lines(tmp_path, write)
    frames = [l for l in lines if l["kind"] == "frame"]
    t1 = frames[1]["wallMs"]
    server = {"ok": True, "found": True, "health": 0.6, "dead": False, "wallMs": t1 + 1500}
    p = D.pair_reading(frames, 9, server)
    assert p["void"] is True and p["dt_ms"] == 1500 and "PAIR_SLACK_S" in p["why"]
    p = D.pair_reading(frames, 9, dict(server, wallMs=t1 + 1000))
    assert p["void"] is False and p["dt_ms"] == 1000 and p["client_health"] == 0.6 and p["frame_seq"] == 2
    p = D.pair_reading(frames, 9, dict(server, wallMs=t1 - 600))        # nearer the first frame
    assert p["frame_seq"] == 1 and p["client_health"] == 0.8 and p["void"] is False
    assert D.pair_reading(frames, 10, server)["void"] is True           # no frame lists that zombie
    p = D.pair_reading(frames, 9, dict(server, wallMs=t1 - 600), after_seq=1)   # only the frames after the end act
    assert p["frame_seq"] == 2 and p["dt_ms"] == 600
    p = D.pair_reading(frames, 9, dict(server, wallMs=t1), before_seq=2)        # only the frames before the accept
    assert p["frame_seq"] == 1 and p["dt_ms"] == 1000 and p["void"] is False
    p = D.pair_reading(frames, 9, dict(server, wallMs=t1), after_seq=2)         # a kill: no frame lists it after
    assert p["void"] is True and p["frame_seq"] is None and "no frame" in p["why"]
    assert D.pair_reading(frames, 9, dict(server, found=False, health=None, wallMs=t1))["void"] is True
    assert D.pair_reading(frames, 9, None)["void"] is True


def test_the_voided_pair_leaves_the_agreement(clean_run):
    out = copy.deepcopy(clean_run[0])
    s = out["readings"]["encounters"]["rows"][0]["swings"][0]
    s["pair_void"], s["pair_after"]["void"] = True, True
    s["pair_after"]["client_health"] = 0.9                 # would disagree with the server's 0.5 by 0.4: still kept
    s2 = out["readings"]["encounters"]["rows"][1]["swings"][0]
    s2["pair_after"]["client_health"] = s2["pair_after"]["server_health"] + 0.51
    ag = GT.measure_x5(out)["client_server_agreement"]
    assert ag["n"] == 9 and ag["voided"] == 1 and ag["share"] == pytest.approx(8 / 9)


def test_the_measure_of_an_empty_artifact_reads_none():
    m = GT.measure_x5({})
    assert m["attack_started_share"] == {"share": None, "started": 0, "n": 0}
    assert m["melee_delay"] == {"min": None, "p50": None, "max": None, "n": 0}
    assert m["client_server_agreement"]["share"] is None and m["loop_ms"] == {"p50": None, "p90": None, "n": 0}
    assert m["stop"] is None


def test_new_zombie_takes_the_nearest_id_not_known_before(tmp_path):
    def write(mod, clock):
        mod.frame(zombies=[{"id": 1, "x": 101.0, "y": 200.0, "dist": 1.0, "hasTarget": False, "crawler": False,
                            "health": 1.0}])
        mod.frame(zombies=[{"id": 1, "x": 101.0, "y": 200.0, "dist": 1.0, "hasTarget": False, "crawler": False,
                            "health": 1.0},
                           {"id": 3, "x": 105.0, "y": 200.0, "dist": 5.0, "hasTarget": False, "crawler": False,
                            "health": 1.0},
                           {"id": 2, "x": 104.0, "y": 200.0, "dist": 4.0, "hasTarget": False, "crawler": False,
                            "health": 1.0}])
    lines = _lines(tmp_path, write)
    seen = D.new_zombie(lines, {1})
    assert seen["id"] == 2 and seen["frame"]["seq"] == 2
    assert D.new_zombie(lines, {1, 2, 3}) is None


def test_counts_diff_and_damage_last_read_the_empty_lua_table():
    assert D.counts_diff({"ZOMBIE": 1}, {"ZOMBIE": 3, "FALLDOWN": 1}) == {"ZOMBIE": 2, "FALLDOWN": 1}
    assert D.counts_diff({"ZOMBIE": 1}, {"ZOMBIE": 1}) == {}
    assert D.counts_diff({}, None) is None
    assert D.damage_last({"last": {}}) == [] and D.damage_last("usage") == []
    assert [r["i"] for r in D.damage_last({"last": [{"i": 2}, {"i": 1}]})] == [1, 2]


def test_players_list_reads_the_empty_table_as_nobody():
    assert D.players_list(["admin"]) == ["admin"] and D.players_list({}) == []
    assert D.players_list({"error": "timeout"}) is None and D.players_list("no") is None


def test_the_attack_schema_is_the_one_the_driver_sends():
    assert pza1.ACTION_ARGS["attack"] == {"targetId": "int"} and pza1.ACTION_ARGS["equip"] == {"itemId": "int"}


def test_the_sight_is_the_new_zombie_not_one_listed_before_the_spawn(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "ENCOUNTERS", 2)
    out, mod, asked, x5 = run_x5(tmp_path, ambient=True)
    rows = out["readings"]["encounters"]["rows"]
    assert [r["zid"] for r in rows] == [7001, 7002] and all(r["killed"] for r in rows)
    first = next(l for l in x5.lines if l.get("kind") == "frame" and l["zombies"])
    assert [z["id"] for z in first["zombies"]] == [6000]               # listed long before the first spawn
    assert all(s["targetId"] == r["zid"] for r in rows for s in r["swings"])


def test_a_zombie_absent_from_the_frames_for_gone_s_ends_its_encounter(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "ENCOUNTERS", 1)
    out, mod, asked, x5 = run_x5(tmp_path, start_dist=8.0, close=0.0, vanish_ticks=5)
    r = out["readings"]["encounters"]["rows"][0]
    assert r["end"]["reason"] == "gone" and r["killed"] is False
    last_seen = max(p["wallMs"] for p in r["approach"])
    assert D.GONE_S * 1000 < r["end"]["wallMs"] - last_seen <= D.GONE_S * 1000 + 200
    assert r["actions"] and all(a["type"] == "walkTo" and a["state"] in ("done", "failed") for a in r["actions"])
    assert r["swings"] == [] and r["server_end"]["found"] is True and r["server_end"]["dead"] is False


# ================================================================ fix 1
def test_loop_ms_is_reported_raw_and_net_of_the_pre_swing_server_read(tmp_path, monkeypatch):
    """Live, zombie.near places the zombie about a tile off, so the first action is an Attack and the synchronous
    zombie.get before its send sits inside the raw loop: raw - net is that step's round trip."""
    monkeypatch.setattr(D, "ENCOUNTERS", 2)
    out, mod, asked, x5 = run_x5(tmp_path, start_dist=1.5, bus_s=0.3)
    rows = out["readings"]["encounters"]["rows"]
    for r in rows:
        s1, s2 = r["swings"]
        assert s1["loop_ms"] == r["loop_ms"] and s1["pre_read_ms"] == pytest.approx(300, abs=1)
        assert s1["pre_read_ms"] == s1["server_before"]["epoch_ms_after"] - s1["server_before"]["epoch_ms_before"]
        assert s2["pre_read_ms"] == pytest.approx(300, abs=1)
    m = GT.measure_x5(out)
    raw = sorted(r["loop_ms"] for r in rows)
    net = sorted(r["loop_ms"] - r["swings"][0]["pre_read_ms"] for r in rows)
    assert m["loop_ms"] == {"p50": raw[0], "p90": raw[1], "n": 2}
    assert m["loop_ms_net"] == {"p50": net[0], "p90": net[1], "n": 2}
    assert raw[0] - net[0] == pytest.approx(300, abs=1) and net[0] > 0


def test_a_walk_first_leaves_the_net_loop_equal_to_the_raw(clean_run):
    out = clean_run[0]
    rows = out["readings"]["encounters"]["rows"]
    assert all(s["pre_read_ms"] > 0 for r in rows for s in r["swings"])
    m = GT.measure_x5(out)
    assert m["loop_ms_net"] == m["loop_ms"]
    walk = rows[0]["actions"][0]
    assert walk["type"] == "walkTo"


def test_an_unfenced_pair_is_voided():
    frames = [{"kind": "frame", "seq": 1, "wallMs": 1000, "zombies": [{"id": 9, "health": 0.8}]},
              {"kind": "frame", "seq": 3, "wallMs": 1100, "zombies": [{"id": 9, "health": 0.8}]}]
    server = {"ok": True, "found": True, "health": 0.8, "dead": False, "wallMs": 1050,
              "epoch_ms_before": 1000, "epoch_ms_after": 1100}
    act = {"aid": "a1", "args": {"targetId": 9}, "accepted_wall": None, "ended_wall": 5.0, "accepted_seq": None,
           "accepted_wallMs": None, "ended_seq": None, "ended_wallMs": None, "state": "timeout", "reason": "",
           "result": None}
    row = D.swing_row(act, server, server, frames)
    for k in ("pair_before", "pair_after"):
        assert row[k]["void"] is True and "unfenced" in row[k]["why"], k
    assert row["pair_void"] is True and row["pre_read_ms"] == 100
    fenced = D.swing_row(dict(act, accepted_seq=2, ended_seq=2), server, server, frames)
    assert fenced["pair_before"]["frame_seq"] == 1 and fenced["pair_after"]["frame_seq"] == 3
    assert fenced["pair_void"] is False
    assert D.swing_row(act, None, None, frames)["pre_read_ms"] == 0


def test_a_dead_bus_names_the_stop_bus_dead(tmp_path):
    out, mod, asked, x5 = run_x5(tmp_path, bus_dead_at=2)
    assert out["stop"]["reason"] == "bus_dead" and out["stop"]["detail"]
    assert "encounters" in out["phase_walls"] and out["phase_walls"]["encounters"].get("bus_dead")
    assert out["phase_errors"] == {} and len(out["readings"]["encounters"]["rows"]) == 1


def test_a_reused_online_id_is_sighted_and_fought_again(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "ENCOUNTERS", 3)
    out, mod, asked, x5 = run_x5(tmp_path, reuse_ids=True)
    rows = out["readings"]["encounters"]["rows"]
    assert [r["zid"] for r in rows] == [7001] * 3 and all(r["void"] is None for r in rows)
    assert all(r["end"]["reason"] == "dead" and len(r["swings"]) == 2 for r in rows)
    assert all(r["swings"][0]["client_health_before"] == 1.0 for r in rows)
