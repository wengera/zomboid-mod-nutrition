"""drivers/e_day_3.py (Plan 23, the third chain's session driver: e_day_2.py copied under its own key), offline: the driver is never invoked.

The static tests read its arguments (`--session`, `--fixture`, `--prev`), its constants and its imports; the
pre-boot checks run against the real profile and throwaway fixture records (conftest's `agent_fixture`). The loop runs
`e_day_3.make_session` (the driver's `Chain` with its planner, limits and polls) on DayMod and FakeBus, copied from
test_driverlib.py (not from the frozen test files) and extended with the knobs a chained day needs: `stats` laid over
the frame's stats, `items` (item_added at the first tick), `level` (the frame's load level) and `inside` (a room
square under the player, so the night sleeps at once); the fake mod answers consume (thirst falls), drop (the item
leaves, the level falls) and sleep (a result with sleptH, fatigue falls). The server's reads run through InlinePolls
(a PollThread whose schedule runs on the loop's thread at each `latest`, so the fake clock stays single-threaded)."""
import json
import os
import re
import types

import pytest

from agent.base.planner.goals import ScriptedSource
from agent.base.planner.survive import Survive
from agent.base.transport.files import FileTransport
from agent.driverlib import chain as CH
from agent.driverlib import day as CH_DAY
from agent.driverlib import polls as P
from agent.driverlib import session as S
from agent.drivers import e_day_2 as E1
from agent.drivers import e_day_3 as E
from .fakemod import DEFAULT_FRAME, FakeMod, square

REPO = S.REPO
X = S.X
KIT = S.DEFAULTS["KIT"]
KIT_ID = 5001
ZID = 77
WATER = {"itemId": 701, "fullType": "Base.WaterBottle", "weight": 1.0, "use": "water"}
PLANK = {"itemId": 602, "fullType": "Base.Plank", "weight": 3.0, "use": "other"}


# ================================================================ static: refusal, constants, imports
def test_the_driver_refuses_arguments_before_main():
    src = open(E.__file__, encoding="utf-8").read()
    i_ref = src.index("refusal = parse_argv(sys.argv[1:], __file__)")
    i_main = src.rindex("    main(flags(sys.argv[1:]))")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    me = E.__file__
    for bad in (["x"], ["--help"], ["--session"], ["--session", "0"], ["--session", "-1"], ["--session", "two"],
                ["--session", "1.5"], ["--fixture"], ["--prev"], ["--session", "2", "--session", "3"],
                ["--day", "2"], ["--session", "2", "x"]):
        r = E.parse_argv(bad, me)
        assert r and "e_day_3.py" in r and "\n" not in r, bad
    for good in ([], ["--session", "2"], ["--fixture", "chain-1"], ["--prev", "a.json"],
                 ["--session", "3", "--fixture", "chain-2", "--prev", "testing/runs/e_day-1/e_day.json"]):
        assert E.parse_argv(good, me) is None, good
    assert E.flags([]) == {"session": 1, "fixture": "agent", "prev": None}
    assert E.flags(["--prev", "a.json", "--session", "2", "--fixture", "chain-1"]) == {
        "session": 2, "fixture": "chain-1", "prev": "a.json"}


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(E.__file__) == E.DRIVER == E.KEY + ".py" == "e_day_3.py"
    assert (E.KEY, E.PROFILE, E.ARTIFACT) == ("e_day_3", "testing/profiles/agent.toml", "e_day_3.json")
    assert os.path.isfile(os.path.join(REPO, E.PROFILE))
    assert (E.BUDGET_S, E.DAY_CAP_S, E.PLANNER_HZ, E.DAMAGE_POLL_S) == (1200.0, 840, 2, 5)
    assert E.LIMITS == {"DAY_CAP_S": 840, "PLANNER_HZ": 2, "DAMAGE_POLL_S": 5}
    assert E.CONSTANTS == dict(S.DEFAULTS, **E.LIMITS, BUDGET_S=1200.0)
    assert E.ALLOWED == ("--session", "--fixture", "--prev") and E.DEFAULT_FIXTURE == "agent" and E.USER == "admin"
    assert E.MIN_FREE_GB == S.DEFAULTS["MIN_FREE_GB"] == 12.0
    # M-8: the day's constants are day.py's, imported (one copy for e_day and f_goals)
    assert E.LIMITS is CH_DAY.LIMITS and E.CONSTANTS is CH_DAY.CONSTANTS and E.USER is CH_DAY.USER


def test_nothing_is_imported_from_a_frozen_driver():
    src = open(E.__file__, encoding="utf-8").read()
    imports = [l.split("#")[0].strip() for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
    frozen = [l for l in imports if re.match(r"^(a_|b_|c_|d_|p22|x4_|x5_)", l.split()[1].split(".")[-1])
              or "drivers" in l or l.split()[1] in ("agent.link", "agent.grades", "agent.grade_c", "agent.world",
                                                     "agent.policy")]
    assert frozen == [], frozen
    for need in ("import xlib as X", "from agent.driverlib import session as DS",
                 "from agent.driverlib import day as DY", "from agent.base import gates_e as GE",
                 "from agent.base.planner.survive import Survive",
                 "from agent.base.planner.goals import ScriptedSource"):
        assert need in imports, need
    assert "Survive(world, actions, log_path, clock, source=ScriptedSource())" in src
    assert "return DY.make_day_session(xs, transport, planner, prev=prev, **kw)" in src     # M-8: one builder
    # the boot is the library's (Task 16d): driverlib/day.boot_and_run, its order tested in test_driverlib.py
    assert "DY.boot_and_run(args, lambda: preboot(_ME, args), run_session, grade, key=KEY, driver=DRIVER," in src
    assert 'grade_key="grade_e1"' in src and 'DY.grade(out, "grade_e1", GE.grade_e1)' in src
    assert E.Chain is CH_DAY.Chain and E.parse_argv is CH_DAY.parse_argv and E.flags is CH_DAY.flags
    doc = E.__doc__
    for word in ("RULES", "--session", "--fixture", "--prev", "pzt snapshot --from-run", "never edited after its run",
                 "goals", "night", "lineage", "t_loop0_ms", "use", "branch", "day_cap"):
        assert word in doc, word


def test_the_chain_record_names_the_session_the_fixture_the_prev_and_the_commit():
    args = {"session": 2, "fixture": "chain-1", "prev": "testing/runs/e_day-1/e_day.json"}
    assert CH_DAY.chain_record(args, "agent", "abc1234") == {
        "session": 2, "fixture_arg": "chain-1", "profile_fixture": "agent",
        "prev": "testing/runs/e_day-1/e_day.json", "commit": "abc1234"}


def test_load_prev_reads_an_artifact_and_names_a_bad_one(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"loop": {"last_frames": [{"seq": 1}]}}), encoding="utf-8")
    assert CH_DAY.load_prev(str(p)) == ({"loop": {"last_frames": [{"seq": 1}]}}, None)
    art, err = CH_DAY.load_prev(str(tmp_path / "missing.json"))
    assert art is None and "missing.json" in err
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    art, err = CH_DAY.load_prev(str(tmp_path / "bad.json"))
    assert art is None and err
    (tmp_path / "list.json").write_text("[1]", encoding="utf-8")
    assert CH_DAY.load_prev(str(tmp_path / "list.json"))[0] is None
    assert CH_DAY.load_prev(None) == (None, None)


def _chain_fixture(root, name):
    sv = root / name / "cache" / "server" / "Server"
    sv.mkdir(parents=True)
    (root / name / "fixture.json").write_text(json.dumps(
        {"name": name, "build": "42.21.0", "server": {"name": "pzt", "mods": ["PZTestKit"]}, "clients": {"admin": {}},
         "parent": "agent", "session": 1}))


def test_preboot_on_the_real_profile(agent_fixture, monkeypatch, tmp_path):
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (False, ""))
    real = S.DL.C.git_say
    tracked = {"v": ""}
    monkeypatch.setattr(S.DL.C, "git_say", lambda *a: tracked["v"] if a[0] == "ls-files" else real(*a))
    pre, ok = E.preboot(E.__file__, E.flags([]))
    assert ok, pre
    assert pre["profile"] == "agent" and pre["driver_checks"]["driver_file"] is True
    assert pre["driver_checks"]["driverlib_dirty"] is False and pre["driverlib_commit"]
    assert pre["chain_checks"] == {"fixture": "agent", "fixture_ok": True, "fixture_error": None,
                                   "fixture_session": None, "prev": None, "prev_ok": None, "prev_error": None,
                                   "prev_frames": None, "prev_session": None, "session": 1,
                                   "session_consistent": None}
    _chain_fixture(agent_fixture, "chain-1")
    prev = tmp_path / "e_day_3.json"
    prev.write_text(json.dumps({"loop": {"last_frames": [{"seq": 1}]}}), encoding="utf-8")
    pre, ok = E.preboot(E.__file__, E.flags(["--session", "2", "--fixture", "chain-1", "--prev", str(prev)]))
    assert ok, pre
    assert pre["chain_checks"]["fixture_ok"] is True and pre["chain_checks"]["prev_ok"] is True
    assert pre["chain_checks"]["prev_frames"] is True and pre["chain_checks"]["fixture_session"] == 1
    assert pre["chain_checks"]["session_consistent"] is True
    pre, ok = E.preboot(E.__file__, E.flags(["--fixture", "nope"]))
    assert ok is False and pre["chain_checks"]["fixture_ok"] is False and "nope" in pre["chain_checks"]["fixture_error"]
    pre, ok = E.preboot(E.__file__, E.flags(["--prev", str(tmp_path / "gone.json")]))
    assert ok is False and pre["chain_checks"]["prev_ok"] is False
    tracked["v"] = "testing/artifacts/e_day-20261028-120000/e_day.json"
    assert E.preboot(E.__file__, E.flags([]))[1] is False
    tracked["v"] = ""
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (rel == "testing/agent/driverlib", ""))
    assert E.preboot(E.__file__, E.flags([]))[1] is False
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (False, ""))
    assert E.preboot(os.path.join(os.path.dirname(E.__file__), "d_survive.py"), E.flags([]))[1] is False


# ================================================================ DayMod and FakeBus (test_driverlib.py's, copied)
class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def now(self):
        return self.t


class DayMod(FakeMod):
    """test_driverlib.py's DayMod (one frame a tick at 10 Hz on the shared clock; equip wields the bat, attack kills
    its zombie, every other type accepted and done), trimmed to the knobs these tests use and extended: `stats` laid
    over the frame's stats, `items` (item_added events at the first tick), `level` (the frame's load level) and
    `inside` (a full map of one room square under the player, building 1). consume answers done {itemId} with an
    item_removed and the thirst and hunger set to 0.05; drop answers done {moved 1} with an item_removed and the level
    set to 0; sleep answers done {sleptH 6.0, fatigueBefore, fatigueAfter 0.1, bedType "floor"} and the fatigue set to
    0.1."""

    def __init__(self, d, clock, stats=None, items=(), level=0, inside=False):
        super().__init__(d, clock=clock.now)
        self.clk, self.t0 = clock, clock.t
        self.hz = 10
        self.stats = dict(DEFAULT_FRAME["stats"], **(stats or {}))
        self.level = level
        self.health, self.weapon, self.has_kit = 100.0, None, False
        self.pending, self.cmd_seen, self.cmds = [dict(i) for i in items], 0, []
        self.server_records = []
        self.hello(mode="append")
        if inside:
            self.map_full([square(x=100, y=200, room="bedroom", building=1)])
        self.next_t = clock.t
        self._tick()
        self.next_t += 1.0 / self.hz

    def s(self):
        return self.clk.t - self.t0

    def sleep(self, dt):
        end = self.clk.t + dt
        while self.next_t <= end + 1e-9:
            self.clk.t = self.next_t
            self._tick()
            self.next_t += 1.0 / self.hz
        self.clk.t = max(self.clk.t, end)

    def additem(self):
        self.has_kit = True
        self.pending.append({"itemId": KIT_ID, "fullType": KIT, "weight": 1.5})

    def _poll(self):
        p = os.path.join(self.dir, "cmd.txt")
        if not os.path.isfile(p):
            return
        with open(p, encoding="utf-8") as f:
            cmd = json.loads(f.read())
        if cmd["seq"] <= self.cmd_seen:
            return
        self.cmd_seen = cmd["seq"]
        self.cmds.append(cmd)
        t, aid, args = cmd["type"], cmd["aid"], cmd["args"]
        if t == "attack":
            self.act(aid, "rejected", t, reason="no target")
            return
        self.act(aid, "accepted", t)
        result = {}
        if t == "equip":
            self.weapon = {"type": KIT, "cond": 1.0, "reach": 1.125, "ammo": None}
        elif t == "consume":
            result = {"itemId": args["itemId"]}
            self.event("item_removed", itemId=args["itemId"])
            self.stats.update(thirst=0.05, hunger=0.05)
        elif t == "drop":
            result = {"moved": 1}
            self.event("item_removed", itemId=args["itemId"])
            self.level = 0
        elif t == "sleep":
            result = {"sleptH": 6.0, "fatigueBefore": self.stats["fatigue"], "fatigueAfter": 0.1, "bedType": "floor"}
            self.stats["fatigue"] = 0.1
        self.act(aid, "done", t, result=result)

    def _tick(self):
        self._poll()
        for ev in self.pending:
            self.event("item_added", **ev)
        self.pending = []
        gmin = 480.0 + self.s() * 16.0 / 60.0
        self.frame(gameMin=gmin, worldAge=8.0 + (gmin - 480.0) / 60.0,
                   body=dict(DEFAULT_FRAME["body"], health=self.health),
                   weapon=self.weapon, zombies=[], stats=dict(self.stats),
                   load=dict(DEFAULT_FRAME["load"], level=self.level))


class FakeServer:
    def __init__(self, mod):
        self.mod, self.errors = mod, []

    def rcon(self, cmd):
        self.mod.additem()
        return True, "Item %s Added in admin's inventory." % KIT


class FakeBus:
    """test_driverlib.py's FakeBus, its happy path: the server's bus in its real reply shapes (stats.all, players,
    damage.watch, item.get, ping), each call costing the fake mod bus_s."""

    def __init__(self, mod, bus_s=0.05):
        self.mod, self.bus_s = mod, bus_s
        self.asked, self.stats_calls, self.players_calls, self.damage_calls = [], [], [], []
        self.hooked_ms = None

    def ask(self, node, cmd, args, timeout=30):
        self.asked.append((node, cmd, args, timeout))
        if self.bus_s:
            self.mod.sleep(self.bus_s)
        m = self.mod
        if cmd == "ping":
            return "pong"
        if cmd == "item.get":
            if not m.has_kit:
                return "no item %s in admin's inventory" % KIT
            return {"fullType": KIT, "id": KIT_ID, "uses": 1, "age": 0, "weight": 1.5}
        if cmd == "stats.all":
            self.stats_calls.append(m.s())
            return {"side": "server", "user": args, "worldAge": 8.0, "mult": 1.0, "wall": 1,
                    "stats": {"Hunger": 0.11, "Thirst": 0.1, "Fatigue": 0.05}, "missing": {}}
        if cmd == "players":
            self.players_calls.append(m.s())
            return ["admin"]
        if cmd == "damage.watch":
            parts = args.split()
            self.damage_calls.append((m.s(), args))
            if self.hooked_ms is None:
                self.hooked_ms = round(m.clk.t * 1000)
            return {"ok": True, "side": "server", "hooked": True, "user": parts[0], "counts": {}, "n": 0, "last": {},
                    "dropped": 0}
        return {"error": "unknown command " + cmd}


class InlinePolls(P.PollThread):
    """test_driverlib.py's InlinePolls: `latest(name)` first runs that read when it is due, on the caller's thread."""

    def start(self):
        self.started = True

    def latest(self, name):
        self.run_due(only=name)
        return super().latest(name)


def run_chain(tmp_path, monkeypatch, day_cap_s=40, prev=None, name="session.json", **knobs):
    """One `e_day_3.make_session` on DayMod and FakeBus (the driver's Chain, planner, limits and a PollThread's
    schedule run inline), DAY_CAP_S laid over the driver's limits; then the driver's grade."""
    clock = Clock()
    sd = str(tmp_path / ("sd-" + name))
    mod = DayMod(sd, clock, **knobs)
    fb = FakeBus(mod)
    monkeypatch.setattr(S.DL, "time", types.SimpleNamespace(time=clock.now))   # _dlib.bus_stats's wallMs clock
    out = S.new_out()
    xs = X.Xs(out, node=lambda side: side, server=FakeServer(mod), ask=fb.ask, clock=clock.now, sleep=mod.sleep,
              budget_s=1e9, user="admin", clients={"admin": types.SimpleNamespace(seen={})})
    xs.path = str(tmp_path / name)
    sess = E.make_session(xs, FileTransport(sd, clock=clock.now), prev, clock=clock.now, sleep=mod.sleep,
                          free=lambda: 30.0, polls=InlinePolls(clock=clock.now), limits={"DAY_CAP_S": day_cap_s})
    sess.run()
    out["frames"]["parks"] = 0
    E.grade(out)
    out["finished"] = True
    return types.SimpleNamespace(out=out, mod=mod, bus=fb, day=sess, xs=xs, clock=clock)


GOAL_KEYS = {"type", "args", "state", "reason", "startS", "endS", "source"}


# ================================================================ the loop on the fake session
def test_a_clean_session_stops_at_the_day_cap_with_the_chain_record(tmp_path, monkeypatch):
    r = run_chain(tmp_path, monkeypatch)
    out, loop = r.out, r.out["loop"]
    assert out["phase_errors"] == {} and out["stop"]["reason"] == "day_cap"
    assert out["stop"]["wallS"] == pytest.approx(40, abs=0.2)
    s = r.day
    assert isinstance(s, E.Chain) and isinstance(s.planner, Survive) and isinstance(s.planner.goals.source,
                                                                                    ScriptedSource)
    assert (s.lim["DAY_CAP_S"], s.lim["PLANNER_HZ"], s.lim["DAMAGE_POLL_S"]) == (40, 2, 5)
    assert s.polls is not None and loop["polls_joined"] is True and loop["poll_errors"] == []
    assert loop["goals"] and all(set(g) == GOAL_KEYS for g in loop["goals"])
    assert all(g["source"] == "scripted" for g in loop["goals"])
    assert loop["goals"] == s.planner.goals.rows()
    assert loop["night"] == {"wants": 0, "steps": [], "sleeps": []}
    assert loop["lineage"] is None
    assert loop["t_loop0_ms"] == loop["startPyMs"] == s.t_loop0 * 1000.0
    assert loop["actions"] and all(a["branch"] in ("goal", "need", "load", "night", "threat") for a in loop["actions"])
    assert all(("use" in a) is (a["type"] == "consume") for a in loop["actions"])
    persisted = json.loads((tmp_path / "session.json").read_text(encoding="utf-8"))
    assert persisted["loop"]["goals"] == json.loads(json.dumps(loop["goals"]))
    assert persisted["loop"]["t_loop0_ms"] == loop["t_loop0_ms"]
    g = out["grade_e1"]
    assert g["grade"] == "grade_e1" and g["survived"] is True and g["game_minutes"] > 0 and g["lineage"] is None
    assert g["needs"]["time_base"] == "t_loop0_ms" and g["death"] is None
    json.dumps(out, allow_nan=False)


def test_a_second_session_with_prev_records_the_lineage_diff(tmp_path, monkeypatch):
    a = run_chain(tmp_path, monkeypatch, name="a.json", day_cap_s=10)
    prev, err = CH_DAY.load_prev(str(tmp_path / "a.json"))
    assert err is None and prev["loop"]["last_frames"]
    args = E.flags(["--session", "2", "--prev", str(tmp_path / "a.json")])
    assert args["session"] == 2
    b = run_chain(tmp_path, monkeypatch, name="b.json", day_cap_s=10, prev=prev)
    lin = b.out["loop"]["lineage"]
    first = b.day.first_frame
    assert first["seq"] == 2 and first["gameMin"] == 480.0                     # the hello is seq 1
    assert lin == CH.lineage_diff(prev, first)
    gm = a.out["loop"]["last_frames"][-1]["gameMin"]
    wa = a.out["loop"]["last_frames"][-1]["worldAge"]
    assert lin["game_min"] == {"prev": gm, "now": 480.0}
    # the fake's clock began again at 8 h: a clock that ran backwards, the stale save the lineage catches
    # (P23-Y amended)
    assert lin["world_age"]["prev"] == wa and lin["world_age"]["now"] == 8.0
    assert lin["world_age"]["delta_min"] == pytest.approx((8.0 - wa) * 60.0) and lin["world_age"]["delta_min"] < 0
    assert lin["world_age"]["ok"] is False and lin["ok"] is False
    # I-6: the previous frame is the first kept after the loop stopped the character
    assert a.out["loop"]["last_frame_after_stop"] is True and a.out["loop"]["stopped"]["acked"] is True
    assert prev["loop"]["last_frames"][-1]["seq"] > prev["loop"]["stopped"]["ack_seq"]
    assert b.out["grade_e1"]["lineage"] == lin
    same = {"loop": {"last_frames": [{"seq": 9, "gameMin": 480.0, "worldAge": 8.0,
                                      "me": {"x": 100.0, "y": 200.0},
                                      "body": {"health": 100.0}, "stats": {"hunger": 0.1, "thirst": 0.1,
                                                                           "fatigue": 0.05},
                                      "load": {"n": 12}}]}}
    c = run_chain(tmp_path, monkeypatch, name="c.json", day_cap_s=5, prev=same)
    assert c.out["loop"]["lineage"]["ok"] is True and c.out["loop"]["lineage"]["position"]["d"] == 0.0
    moved = json.loads(json.dumps(same))
    moved["loop"]["last_frames"][-1]["me"]["x"] = 90.0
    d = run_chain(tmp_path, monkeypatch, name="d.json", day_cap_s=5, prev=moved)
    assert d.out["loop"]["lineage"]["ok"] is False
    assert d.out["loop"]["lineage"]["position"]["d"] == pytest.approx(10.0)


def test_a_consume_done_lands_in_the_action_rows_with_its_use_and_the_needs(tmp_path, monkeypatch):
    r = run_chain(tmp_path, monkeypatch, day_cap_s=20, stats={"thirst": 0.3}, items=[WATER])
    rows = [a for a in r.out["loop"]["actions"] if a["type"] == "consume"]
    assert rows and rows[0]["args"] == {"itemId": 701} and rows[0]["state"] == "done"
    assert rows[0]["use"] == "water" and rows[0]["branch"] == "need"
    nd = r.out["grade_e1"]["needs"]
    assert nd["drink"]["sent"] >= 1 and nd["drink"]["done"] >= 1 and nd["drink"]["stat_fell"] is True
    assert nd["unknown"] == 0


def test_a_drop_row_carries_its_branch_and_counts_as_a_guard_drop(tmp_path, monkeypatch):
    r = run_chain(tmp_path, monkeypatch, day_cap_s=10, items=[PLANK], level=3)
    rows = [a for a in r.out["loop"]["actions"] if a["type"] == "drop"]
    assert rows and rows[0]["args"] == {"itemId": 602} and rows[0]["state"] == "done"
    assert rows[0]["branch"] == "load" and "use" not in rows[0]
    assert r.out["grade_e1"]["load"]["guard_drops"] >= 1 and r.out["grade_e1"]["load"]["flee_drops"] == 0


def test_the_sleeps_result_lands_in_night(tmp_path, monkeypatch):
    r = run_chain(tmp_path, monkeypatch, day_cap_s=10, stats={"fatigue": 0.7}, inside=True)
    night = r.out["loop"]["night"]
    assert night["wants"] >= 1 and len(night["sleeps"]) == 1
    sl = night["sleeps"][0]
    assert sl["state"] == "done" and sl["sleptH"] == 6.0 and sl["fatigueBefore"] == 0.7 and sl["fatigueAfter"] == 0.1
    assert sl["result"] == {"sleptH": 6.0, "fatigueBefore": 0.7, "fatigueAfter": 0.1, "bedType": "floor"}
    assert night["sleeps"] is not r.day.planner.night.sleeps                  # a copy, never the planner's own list
    rows = [a for a in r.out["loop"]["actions"] if a["type"] == "sleep"]
    assert rows and rows[0]["branch"] == "night"
    sleep = r.out["grade_e1"]["needs"]["sleep"]
    assert sleep == {"sent": 1, "done": 1, "sleptH": 6.0, "fatigue_fell": True}


def test_grade_records_a_grade_failure_rather_than_raising(monkeypatch):
    out = {"loop": {}}
    monkeypatch.setattr(E.GE, "grade_e1", lambda o: (_ for _ in ()).throw(ValueError("boom")))
    E.grade(out)
    assert out["grade_e1_error"] == "ValueError: boom" and "grade_e1" not in out


def test_a_later_chain_session_holding_the_bat_spawns_none(tmp_path, monkeypatch):
    """C-1: the bat a session ends with is in the next session's first sight; no second one is spawned."""
    bat = {"itemId": KIT_ID, "fullType": KIT, "weight": 1.5, "use": "weapon"}
    r = run_chain(tmp_path, monkeypatch, day_cap_s=5, items=[bat])
    kit = r.out["readings"]["kit"]
    assert kit["spawn"] is None and kit["item"]["source"] == "held" and kit["item"]["itemId"] == KIT_ID
    assert kit["armed"] is True and kit["ok"] is True and not r.mod.has_kit                 # no RCON additem


# ================================================================ the copy: e_day_2.py's body, its own key
def test_the_copy_differs_from_e_day_2_only_in_its_docstring_head_and_its_three_names():
    """Plan 23 (P23-AG): the same body; only the first docstring paragraph, KEY, DRIVER and ARTIFACT differ."""
    a = open(E1.__file__, encoding="utf-8").read()
    b = open(E.__file__, encoding="utf-8").read()
    mark = "\n\nThe driver is thin"
    norm = b[b.index(mark):]
    for mine, theirs in (('KEY = "e_day_3"', 'KEY = "e_day_2"'), ('DRIVER = "e_day_3.py"', 'DRIVER = "e_day_2.py"'),
                         ('ARTIFACT = "e_day_3.json"', 'ARTIFACT = "e_day_2.json"')):
        assert norm.count(mine) == 1, mine
        norm = norm.replace(mine, theirs)
    assert norm == a[a.index(mark):]
    head = b[:b.index(mark)]
    for c in ("145868e2", "e_day_2-20261028-124249"):
        assert c in head, c
    assert E.CONSTANTS == E1.CONSTANTS and E.PROFILE == E1.PROFILE
