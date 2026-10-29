"""drivers/p_stance.py (Plan 24 Task 16, ruling P24-T: the two-minute live probe of the combat stance on PZA/1.5.4), offline: the driver is never invoked.

The static tests read its arguments (`--session 1` and `--fixture agent`, nothing else), its constants and its imports;
the script's action shapes are checked against the schema (`pza1.json` at HEAD) and the fake mod's own argument check;
the pre-boot checks run against the real profile and throwaway fixture records (conftest's `agent_fixture`). The loop
runs `p_stance.make_session` (the driver's Probe on its Script) on ProbeMod and the day tests' FakeBus: a fake mod that
holds the stance through an aim leg (or does not), strafes along the vector, keeps the stance past a swing and drops it
at a walk. The grade's failing cases run on synthetic records built frame by frame, one case per grade field."""
import json
import os
import re
import types

import pytest

from agent.base import pza1
from agent.base.transport.files import FileTransport
from agent.driverlib import day as CH_DAY
from agent.driverlib import session as S
from agent.drivers import p_stance as P
from .fakemod import DEFAULT_FRAME, FakeMod, bad_args
from .test_e_day_6 import Clock, FakeBus, FakeServer, InlinePolls

REPO = S.REPO
X = S.X
KIT = S.DEFAULTS["KIT"]
KIT_ID = 5001
ZID = 77
SCHEMA = os.path.join(REPO, "testing", "agent", "base", "schema", "pza1.json")


# ================================================================ static: refusal, constants, imports
def test_the_driver_refuses_arguments_before_main():
    src = open(P.__file__, encoding="utf-8").read()
    i_ref = src.index("refusal = parse_argv(sys.argv[1:], __file__)")
    i_main = src.rindex("    main(flags(sys.argv[1:]))")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    me = P.__file__
    for bad in (["x"], ["--help"], ["--session"], ["--session", "2"], ["--session", "0"], ["--session", "one"],
                ["--fixture"], ["--fixture", "agent-s1"], ["--fixture", "two"], ["--prev", "a.json"],
                ["--session", "1", "--session", "1"], ["--fixture", "agent", "--fixture", "agent"],
                ["--session", "1", "--prev", "a.json"], ["--day", "2"], ["--session", "1", "x"]):
        r = P.parse_argv(bad, me)
        assert r and "p_stance.py" in r and "\n" not in r, bad
    for good in ([], ["--session", "1"], ["--fixture", "agent"], ["--session", "1", "--fixture", "agent"],
                 ["--fixture", "agent", "--session", "1"]):
        assert P.parse_argv(good, me) is None, good
    assert P.flags([]) == {"session": 1, "fixture": "agent", "prev": None}


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(P.__file__) == P.DRIVER == P.KEY + ".py" == "p_stance.py"
    assert (P.KEY, P.PROFILE, P.ARTIFACT) == ("p_stance", "testing/profiles/agent.toml", "p_stance.json")
    assert os.path.isfile(os.path.join(REPO, P.PROFILE))
    assert P.BUDGET_S == 150.0 and P.LIMITS["DAY_CAP_S"] == P.BUDGET_S and P.LIMITS["PLANNER_HZ"] == 10
    assert P.ALLOWED == ("--session", "--fixture") and P.USER == "admin" and P.MIN_FREE_GB == 12.0
    assert P.CONSTANTS == dict(S.DEFAULTS, **P.LIMITS, BUDGET_S=150.0, BOOT_BUDGET_S=P.BOOT_BUDGET_S)
    assert P.GRADE_KEY == "grade_p1" and P.STEPS == ("idle", "aim_stand", "aim_strafe", "aim_target", "attack",
                                                      "post_attack", "walk", "settle")
    doc = P.__doc__
    for word in ("RULES", "--session 1", "--fixture agent", "script_done", "STANCE HOLDS", "STANCE FAILS", "held_frac",
                 "force_frac", "strafe_tiles", "strafe_tiles_per_s", "handover_ok", "release_ok", "heldFrames"):
        assert word in doc, word


def test_nothing_is_imported_from_a_frozen_driver():
    src = open(P.__file__, encoding="utf-8").read()
    imports = [l.split("#")[0].strip() for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
    frozen = [l for l in imports if re.match(r"^(a_|b_|c_|d_|e_|f_|p22|x4_|x5_)", l.split()[1].split(".")[-1])
              or "drivers" in l or l.split()[1] in ("agent.link", "agent.grades", "agent.grade_c", "agent.world",
                                                     "agent.policy")]
    assert frozen == [], frozen
    for need in ("import xlib as X", "from agent.driverlib import session as DS", "from agent.driverlib import day as DY"):
        assert need in imports, need
    assert "gates_e" not in "\n".join(imports)           # the grade is the driver's own
    assert "DY.boot_and_run(args, lambda: preboot(_ME, args), run_session, grade, key=KEY, driver=DRIVER," in src
    assert "grade_key=GRADE_KEY" in src


# ================================================================ the script against the schema
def test_the_schema_carries_the_fields_the_probe_reads():
    schema = json.load(open(SCHEMA, encoding="utf-8"))
    aim = schema["definitions"]["result_aim"]["properties"] if "definitions" in schema else None
    if aim is None:
        aim = next(v for k, v in _walk(schema) if k == "result_aim")["properties"]
    assert {"d", "held", "heldFrames", "ticks"} <= set(aim)
    assert pza1.ACTION_ARGS["aim"] == {"vx": "float", "vy": "float", "seconds": "float", "targetId": "int",
                                       "bearing": "float"}
    assert pza1.GROUPS["me"][17:19] == ("aiming", "forceAim")         # PZA/1.6 appends worn after them
    assert "aim" in pza1.ACTION_TYPES and "walkTo" in pza1.ACTION_ARGS and "attack" in pza1.ACTION_ARGS


def _walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v)


def test_the_scripts_actions_are_the_legs_and_pass_the_schema(tmp_path, monkeypatch):
    r = run_probe(tmp_path, monkeypatch, zombie=True)
    cmds = [c for c in r.mod.cmds if c["type"] not in ("equip", "stop")]
    assert [c["type"] for c in cmds] == ["aim", "aim", "aim", "attack", "walkTo"]
    for c in r.mod.cmds:
        assert bad_args(c) == "", c
    stand, strafe, target, attack, walk = (c["args"] for c in cmds)
    assert stand == {"vx": 0.0, "vy": 0.0, "seconds": 5.0, "targetId": -1, "bearing": 0.0}
    assert strafe == {"vx": -1.0, "vy": 0.0, "seconds": 5.0, "targetId": -1, "bearing": 0.0}
    assert target == {"vx": 0.0, "vy": 0.0, "seconds": 3.0, "targetId": ZID, "bearing": -1.0}
    assert attack == {"targetId": ZID}
    assert walk["gait"] == "walk" and walk["y"] == 200.0 and walk["x"] == r.mod.walk_from + P.WALK_TILES


# ================================================================ pre-boot on the real profile
def test_preboot_on_the_real_profile(agent_fixture, monkeypatch):
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (False, ""))
    real = S.DL.C.git_say
    tracked = {"v": ""}
    monkeypatch.setattr(S.DL.C, "git_say", lambda *a: tracked["v"] if a[0] == "ls-files" else real(*a))
    pre, ok = P.preboot(P.__file__, P.flags([]))
    assert ok, pre
    assert pre["profile"] == "agent" and pre["driver_checks"]["driver_file"] is True
    assert pre["driver_checks"]["driver_prefix"] is True and pre["driver_checks"]["driverlib_dirty"] is False
    assert pre["chain_checks"]["fixture"] == "agent" and pre["chain_checks"]["fixture_ok"] is True
    tracked["v"] = "testing/artifacts/p_stance-20261029-120000/p_stance.json"
    assert P.preboot(P.__file__, P.flags([]))[1] is False
    tracked["v"] = ""
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (rel == "testing/agent/driverlib", ""))
    assert P.preboot(P.__file__, P.flags([]))[1] is False
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (rel == "testing/agent/drivers/p_stance.py", ""))
    assert P.preboot(P.__file__, P.flags([]))[1] is False
    monkeypatch.setattr(S.DL.C, "git_dirty", lambda rel: (False, ""))
    assert P.preboot(os.path.join(os.path.dirname(P.__file__), "e_day_6.py"), P.flags([]))[1] is False
    (agent_fixture / "agent" / "fixture.json").unlink()
    pre, ok = P.preboot(P.__file__, P.flags([]))
    assert ok is False and pre["chain_checks"]["fixture_ok"] is False


# ================================================================ ProbeMod: the fake mod for the loop
class ProbeMod(FakeMod):
    """One frame a tick at 10 Hz on the shared clock. `mode` "holds": aiming and forceAim true through an aim leg and for
    HOLD_S after a swing, false otherwise; "no_stance": never; "no_strafe" holds but never moves; "hit" holds but drops `aiming` and
    `forceAim` for HIT_S from HIT_AT_S with `hitReaction` and `attackers` set; "dies" holds and writes the death event
    and a zero-health frame at DIE_AT_S; "turns" holds but reads `dir` "S" from TURN_AT_S. An aim leg moves the
    character along (vx, vy) at one tile a second; a walkTo moves it WALK_TILES in one second and drops the stance. A
    new command supersedes the open action (failed "superseded"). attack answers done {attackStarted true}, aim done
    {d, held, heldFrames, ticks}. `zombie`: a zombie listed 1 tile away (within the weapon's reach of 1.125)."""
    HOLD_S = 2.0
    HIT_AT_S, HIT_S, DIE_AT_S, TURN_AT_S = 2.0, 1.0, 7.0, 7.0      # seconds after the first aim

    def __init__(self, d, clock, mode="holds", zombie=False, mod="1.5.4", zombie_dist=1.0):
        super().__init__(d, clock=clock.now)
        self.clk, self.t0, self.hz = clock, clock.t, 10
        self.mode, self.zombie, self.zombie_dist = mode, zombie, zombie_dist
        self.weapon, self.has_kit = None, False
        self.pending, self.cmd_seen, self.cmds = [], 0, []
        self.cur, self.hold_until, self.aim0 = None, -1.0, None
        self.x, self.y, self.walk_from = 100.0, 200.0, None
        self.hello(mode="append", mod=mod)
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
        if self.cur is not None:
            self.act(self.cur["aid"], "failed", self.cur["type"], reason="superseded")
            self.cur = None
        self.act(aid, "accepted", t)
        if t == "equip":
            self.weapon = {"type": KIT, "cond": 1.0, "reach": 1.125, "ammo": None}
            self.act(aid, "done", t, result={})
        elif t == "aim":
            if self.aim0 is None:
                self.aim0 = self.s()
            self.cur = {"aid": aid, "type": t, "end": self.s() + args["seconds"], "vx": args["vx"], "vy": args["vy"],
                        "ticks": 0, "held": 0}
        elif t == "walkTo":
            self.walk_from = self.x
            self.cur = {"aid": aid, "type": t, "end": self.s() + 1.0, "vx": 0.0, "vy": 0.0,
                        "tx": args["x"], "x0": self.x}
        elif t == "attack":
            if self.mode != "no_stance":
                self.hold_until = self.s() + self.HOLD_S
            self.act(aid, "done", t, result={"attackStarted": True})
        else:
            self.act(aid, "done", t, result={})

    def _hit(self):
        return self.mode == "hit" and self.aim0 is not None and self.HIT_AT_S <= self.s() - self.aim0 < self.HIT_AT_S + self.HIT_S

    def _stance(self):
        if self.mode == "no_stance" or self._hit():
            return False
        c = self.cur
        return (c is not None and c["type"] == "aim") or self.s() < self.hold_until

    def _tick(self):
        self._poll()
        for ev in self.pending:
            self.event("item_added", **ev)
        self.pending = []
        c = self.cur
        if c is not None and c["type"] == "aim":
            c["ticks"] += 1
            c["held"] += 1 if self._stance() else 0
            if self.mode != "no_strafe":
                self.x += c["vx"] / self.hz
                self.y += c["vy"] / self.hz
        if c is not None and c["type"] == "walkTo":
            self.x = c["x0"] + (c["tx"] - c["x0"]) * min(1.0, 1.0 - (c["end"] - self.s()))
        stance = self._stance()
        moving = bool(c is not None and (c["type"] == "walkTo" or abs(c.get("vx", 0)) + abs(c.get("vy", 0)) > 0))
        me = dict(DEFAULT_FRAME["me"], dir="E", x=self.x, y=self.y, aiming=stance, forceAim=stance, moving=moving)
        if self._hit():
            me.update(hitReaction="HitReaction", attackers=1)
        if self.mode == "turns" and self.aim0 is not None and self.s() - self.aim0 >= self.TURN_AT_S:
            me["dir"] = "S"
        groups = {}
        if self.mode == "dies" and self.aim0 is not None and self.s() - self.aim0 >= self.DIE_AT_S:
            if not getattr(self, "dead", False):
                self.dead = True
                self.death()
            groups["body"] = dict(DEFAULT_FRAME["body"], health=0.0)
        gmin = 480.0 + self.s() * 16.0 / 60.0
        zs = [{"id": ZID, "x": self.x + self.zombie_dist, "y": self.y, "dist": self.zombie_dist, "hasTarget": False, "crawler": False,
               "health": 1.0}] if self.zombie else []
        self.frame(gameMin=gmin, worldAge=8.0 + (gmin - 480.0) / 60.0, me=me, weapon=self.weapon, zombies=zs, **groups)
        if c is not None and self.s() >= c["end"] - 1e-9:
            self.cur = None
            if c["type"] == "aim":
                self.act(c["aid"], "done", "aim", result={"d": 5.0, "held": stance, "heldFrames": c["held"],
                                                           "ticks": c["ticks"]})
            else:
                self.act(c["aid"], "done", c["type"], result={})


def run_probe(tmp_path, monkeypatch, name="probe.json", **knobs):
    """One `p_stance.make_session` on ProbeMod and FakeBus (the driver's Probe, Script, limits and a PollThread's
    schedule run inline); then the driver's grade."""
    clock = Clock()
    sd = str(tmp_path / ("sd-" + name))
    mod = ProbeMod(sd, clock, **knobs)
    fb = FakeBus(mod)
    monkeypatch.setattr(S.DL, "time", types.SimpleNamespace(time=clock.now))
    out = S.new_out()
    xs = X.Xs(out, node=lambda side: side, server=FakeServer(mod), ask=fb.ask, clock=clock.now, sleep=mod.sleep,
              budget_s=1e9, user="admin", clients={"admin": types.SimpleNamespace(seen={})})
    xs.path = str(tmp_path / name)
    sess = P.make_session(xs, FileTransport(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep,
                          free=lambda: 30.0, polls=InlinePolls(clock=clock.now))
    sess.run()
    out["frames"]["parks"] = 0
    P.grade(out)
    out["finished"] = True
    return types.SimpleNamespace(out=out, mod=mod, bus=fb, sess=sess, xs=xs, g=out.get("grade_p1"))


# ================================================================ the loop
def test_a_session_that_holds_the_stance_grades_holds_and_stops_script_done(tmp_path, monkeypatch):
    r = run_probe(tmp_path, monkeypatch, zombie=True)
    out, g = r.out, r.g
    assert "grade_p1_error" not in out and g is not None
    assert out["stop"]["reason"] == "script_done", out["stop"]
    assert g["verdict"] == "STANCE HOLDS", g
    steps = [s["step"] for s in out["probe"]["steps"]]
    assert steps == list(P.STEPS)
    assert all(s["state"] in ("done", "skipped") for s in out["probe"]["steps"]), out["probe"]["steps"]
    for leg in ("aim_stand", "aim_strafe", "aim_target"):
        assert g["held_frac"][leg] == 1.0 and g["force_frac"][leg] == 1.0, (leg, g["legs"][leg])
        assert g["legs"][leg]["result_frac"] == 1.0 and g["legs"][leg]["n"] > 20
    assert g["idle"]["n"] > 30 and g["idle"]["aiming_frac"] == 0.0 and g["idle"]["force_frac"] == 0.0
    assert g["strafe_ok"] and 2.5 < g["strafe_tiles"] < 4.5 and 0.8 < g["strafe_tiles_per_s"] < 1.2
    assert g["strafe"]["moving_frac"] == 1.0 and g["strafe"]["running_frac"] == 0.0
    assert g["handover_ok"] is True and g["release_ok"] is True
    assert g["mod_ok"] is True and g["hello_mod"] == "1.5.4" and g["target_skipped"] is False
    assert len(out["probe"]["frames"]) > 200 and out["loop"]["stopped"]["sent"] is True
    log = [json.loads(l) for l in open(r.sess.log_path, encoding="utf-8")]
    assert [l["goal"]["type"] for l in log] == list(P.STEPS) and all(l["branch"] == "script" for l in log)
    saved = json.load(open(r.xs.path, encoding="utf-8"))
    assert saved["probe"]["steps"] and saved["probe"]["frames"], "the probe is in the persisted artifact"


def test_a_zombie_beyond_the_weapons_reach_skips_the_target_legs(tmp_path, monkeypatch):
    r = run_probe(tmp_path, monkeypatch, zombie=True, zombie_dist=1.6)
    rows = {s["step"]: s for s in r.out["probe"]["steps"]}
    assert all(rows[n]["skipped"] and "reach" in rows[n]["note"] for n in ("aim_target",)), rows["aim_target"]
    assert rows["attack"]["skipped"] and r.g["target_skipped"] is True and r.g["handover_ok"] is None
    assert [c["type"] for c in r.mod.cmds if c["type"] not in ("equip", "stop")] == ["aim", "aim", "walkTo"]


def test_with_no_zombie_the_target_legs_are_skipped_and_said_so(tmp_path, monkeypatch):
    r = run_probe(tmp_path, monkeypatch, zombie=False)
    g, rows = r.g, {s["step"]: s for s in r.out["probe"]["steps"]}
    for name in ("aim_target", "attack", "post_attack"):
        assert rows[name]["skipped"] is True and rows[name]["state"] == "skipped" and rows[name]["note"], name
    assert "reach" in rows["aim_target"]["note"]
    assert g["verdict"] == "STANCE HOLDS" and g["handover_ok"] is None and g["target_skipped"] is True
    assert g["release_ok"] is True and r.out["stop"]["reason"] == "script_done"
    assert [c["type"] for c in r.mod.cmds if c["type"] not in ("equip", "stop")] == ["aim", "aim", "walkTo"]


def test_a_stance_that_never_reads_grades_fails_at_its_first_frame(tmp_path, monkeypatch):
    r = run_probe(tmp_path, monkeypatch, mode="no_stance", zombie=True)
    g = r.g
    assert g["verdict"].startswith("STANCE FAILS"), g["verdict"]
    assert g["held_frac"]["aim_stand"] == 0.0 and g["held_frac"]["aim_strafe"] == 0.0
    first = g["legs"]["aim_stand"]["first_false"]
    assert first is not None and ("seq %s" % first) in g["verdict"]
    assert g["handover_ok"] is False
    assert r.out["stop"]["reason"] == "script_done"


def test_a_strafe_that_does_not_move_fails_strafe_but_not_the_stance(tmp_path, monkeypatch):
    r = run_probe(tmp_path, monkeypatch, mode="no_strafe")
    g = r.g
    assert g["verdict"] == "STANCE HOLDS; strafe_ok false" and g["strafe_ok"] is False and abs(g["strafe_tiles"]) < 0.01


def test_an_attacked_leg_is_told_from_a_failed_stance(tmp_path, monkeypatch):
    r = run_probe(tmp_path, monkeypatch, mode="hit")
    g = r.g
    assert g["verdict"].startswith("STANCE FAILS") and "aim_stand" in g["verdict"], g["verdict"]
    assert g["verdict"].count("(attacked)") == 1 and "aim_strafe" not in g["verdict"], g["verdict"]
    assert g["legs"]["aim_stand"]["attacked"] is True and g["legs"]["aim_stand"]["attacked_frames"] >= 8
    assert g["legs"]["aim_strafe"]["attacked"] is False and g["legs"]["aim_strafe"]["attacked_frames"] == 0
    assert g["held_frac"]["aim_stand"] < P.HELD_MIN and r.out["stop"]["reason"] == "script_done"
    fr = r.out["probe"]["frames"]
    assert any(f["hitReaction"] == "HitReaction" and f["attackers"] == 1 for f in fr) and "zombiesSeen" in fr[0]


def test_a_death_mid_leg_stops_the_loop_and_the_grade_is_still_written(tmp_path, monkeypatch):
    r = run_probe(tmp_path, monkeypatch, mode="dies")
    out, g = r.out, r.g
    assert out["stop"]["reason"] == "death", out["stop"]
    assert "grade_p1_error" not in out and g is not None and g["stop"] == "death"
    steps = {s["step"]: s for s in out["probe"]["steps"]}
    assert "walk" not in steps and "settle" not in steps, list(steps)
    assert g["release_ok"] is False


def test_the_backpedal_heading_is_graded_from_the_recorded_dirs(tmp_path, monkeypatch):
    r = run_probe(tmp_path, monkeypatch)
    assert r.g["strafe"]["dirs"] == [P.STRAFE_DIR] and r.g["dir_ok"] is True and r.g["verdict"] == "STANCE HOLDS"
    r = run_probe(tmp_path, monkeypatch, name="turn.json", mode="turns")
    g = r.g
    assert g["dir_ok"] is False and g["strafe"]["dirs"] == [P.STRAFE_DIR, "S"]
    assert g["verdict"].startswith("STANCE FAILS") and "dir turned" in g["verdict"], g["verdict"]
    assert "S" in g["verdict"]


# ================================================================ the grade's failing cases, one per field
def synth(aiming=lambda step, t: True, force=None, dx=lambda t: -(t - 10200) / 1000.0, attack_state="done",
          walk_state="done", zombie_skipped=False, mod="1.5.4", stop="script_done"):
    """A probe record built frame by frame at 10 Hz (t in ms from 0): the step rows of the module docstring's script
    and frames whose `aiming` is aiming(step, t), `forceAim` force(step, t) (default the same), x along the strafe
    by dx(t)."""
    force = force or aiming
    rows = [
        {"step": "idle", "state": "done", "startMs": 0, "endMs": 5000, "ackedMs": None, "skipped": False},
        {"step": "aim_stand", "state": "done", "ackedMs": 5100, "endMs": 10100, "skipped": False,
         "result": {"d": 0.0, "held": True, "heldFrames": 49, "ticks": 49}},
        {"step": "aim_strafe", "state": "done", "ackedMs": 10200, "endMs": 15200, "skipped": False,
         "result": {"d": 5.0, "held": True, "heldFrames": 49, "ticks": 49}},
        {"step": "aim_target", "state": "done", "ackedMs": 15300, "endMs": 18300, "skipped": zombie_skipped,
         "result": {"d": 0.0, "held": True, "heldFrames": 29, "ticks": 29}},
        {"step": "attack", "state": attack_state, "ackedMs": 18400, "endMs": 18900, "skipped": zombie_skipped},
        {"step": "post_attack", "state": "done", "startMs": 18900, "endMs": 21400, "skipped": zombie_skipped},
        {"step": "walk", "state": walk_state, "ackedMs": 21500, "endMs": 22500, "skipped": False},
        {"step": "settle", "state": "done", "startMs": 22500, "endMs": 24000, "skipped": False}]

    def step_at(t):
        for r in rows:
            lo = r.get("ackedMs") if r.get("ackedMs") is not None else r.get("startMs")
            if lo is not None and lo <= t <= r["endMs"]:
                return r["step"]
        return "gap"
    frames = []
    for i, t in enumerate(range(0, 24001, 100)):
        st = step_at(t)
        x = 100.0 + (dx(t) if 10200 <= t <= 15200 else (dx(15200) if t > 15200 else 0.0))
        frames.append({"seq": i + 1, "wallMs": float(t), "x": x, "y": 200.0, "dir": "E", "pace": 0.0,
                       "moving": 10200 <= t <= 15200, "running": False, "sprinting": False,
                       "aiming": aiming(st, t), "forceAim": force(st, t)})
    return {"probe": {"steps": rows, "frames": frames, "hello": {"mod": mod}}, "stop": {"reason": stop}}


def stance_on(step, t):
    return step in ("aim_stand", "aim_strafe", "aim_target") or 18400 <= t < 20400


def stance_off_after_swing(step, t):
    return step in ("aim_stand", "aim_strafe", "aim_target")


def test_the_synthetic_record_that_holds_grades_every_field_true():
    g = P.grade_p1(synth(aiming=stance_on))
    assert g["verdict"] == "STANCE HOLDS" and g["strafe_ok"] and g["handover_ok"] is True and g["release_ok"] is True
    assert g["held_frac"] == {"aim_stand": 1.0, "aim_strafe": 1.0, "aim_target": 1.0}
    assert g["strafe_tiles"] == pytest.approx(4.0, abs=0.01) and g["strafe_tiles_per_s"] == pytest.approx(1.0, abs=0.01)


def test_aiming_false_everywhere_fails_at_the_first_frame_of_the_stand_leg():
    out = synth(aiming=lambda step, t: False)
    g = P.grade_p1(out)
    first = next(f["seq"] for f in out["probe"]["frames"] if 6100 <= f["wallMs"] <= 10100)
    assert g["verdict"].startswith("STANCE FAILS") and ("seq %s" % first) in g["verdict"]
    assert g["held_frac"]["aim_stand"] == 0.0 and g["held_frac"]["aim_strafe"] == 0.0
    assert g["handover_ok"] is False


def test_the_strafe_leg_alone_failing_fails_the_verdict():
    g = P.grade_p1(synth(aiming=lambda step, t: stance_on(step, t) and step != "aim_strafe"))
    assert g["verdict"].startswith("STANCE FAILS") and "aim_strafe" in g["verdict"] and "aim_stand" not in g["verdict"]
    g = P.grade_p1(synth(aiming=lambda step, t: stance_on(step, t) and step != "aim_stand"))
    assert g["verdict"].startswith("STANCE FAILS") and "aim_stand" in g["verdict"]


def test_a_leg_holding_just_under_the_threshold_fails_and_just_over_holds():
    def part(frac):
        return lambda step, t: stance_on(step, t) and (step != "aim_stand" or (t % 1000) < frac * 1000)
    assert P.grade_p1(synth(aiming=part(0.75)))["verdict"].startswith("STANCE FAILS")
    assert P.grade_p1(synth(aiming=part(0.95)))["verdict"] == "STANCE HOLDS"


def test_a_leg_with_no_frames_fails():
    out = synth(aiming=stance_on)
    out["probe"]["frames"] = [f for f in out["probe"]["frames"] if not 5100 <= f["wallMs"] <= 10100]
    g = P.grade_p1(out)
    assert g["verdict"].startswith("STANCE FAILS") and "aim_stand read no frames" in g["verdict"]


def test_force_frac_reads_the_force_flag_apart_from_aiming():
    g = P.grade_p1(synth(aiming=stance_on, force=lambda step, t: False))
    assert g["force_frac"]["aim_stand"] == 0.0 and g["held_frac"]["aim_stand"] == 1.0 and g["verdict"] == "STANCE HOLDS"


def test_a_strafe_of_zero_tiles_fails_strafe():
    g = P.grade_p1(synth(aiming=stance_on, dx=lambda t: 0.0))
    assert g["strafe_ok"] is False and g["strafe_tiles"] == pytest.approx(0.0) and g["strafe_tiles_per_s"] == pytest.approx(0.0)
    g = P.grade_p1(synth(aiming=stance_on, dx=lambda t: -(t - 10200) / 8000.0))
    assert g["strafe_ok"] is False and g["strafe_tiles"] < P.STRAFE_MIN_TILES
    g = P.grade_p1(synth(aiming=stance_on, dx=lambda t: (t - 10200) / 1000.0))       # forward, not back
    assert g["strafe_ok"] is False and g["strafe_tiles"] < 0


def test_handover_fails_when_the_stance_drops_at_the_swing_or_the_swing_is_not_done():
    assert P.grade_p1(synth(aiming=stance_off_after_swing))["handover_ok"] is False
    assert P.grade_p1(synth(aiming=stance_on, attack_state="failed"))["handover_ok"] is False
    assert P.grade_p1(synth(aiming=stance_on, zombie_skipped=True))["handover_ok"] is None


def test_release_fails_when_the_stance_stays_or_the_walk_is_not_done():
    assert P.grade_p1(synth(aiming=lambda step, t: stance_on(step, t) or t >= 21500))["release_ok"] is False
    assert P.grade_p1(synth(aiming=stance_on, force=lambda step, t: stance_on(step, t) or t >= 21500))[
        "release_ok"] is False
    assert P.grade_p1(synth(aiming=stance_on, walk_state="failed"))["release_ok"] is False


def test_the_verdict_names_a_stale_mod_and_a_strafe_that_did_not_move():
    g = P.grade_p1(synth(aiming=stance_on, mod="1.5.3"))
    assert g["mod_ok"] is False and g["verdict"] == "STANCE HOLDS; mod != 1.5.4" and g["report_lines"][0] == g["verdict"]
    g = P.grade_p1(synth(aiming=stance_on, mod="1.5.3", dx=lambda t: 0.0))
    assert g["verdict"] == "STANCE HOLDS; mod != 1.5.4; strafe_ok false"
    g = P.grade_p1(synth(aiming=lambda step, t: False, mod="1.5.3"))
    assert g["verdict"].startswith("STANCE FAILS") and g["verdict"].endswith("; mod != 1.5.4")


def test_an_attacked_synthetic_leg_reads_attacked_and_an_unattacked_failure_does_not():
    out = synth(aiming=lambda step, t: stance_on(step, t) and not 7000 <= t < 8000)
    for f in out["probe"]["frames"]:
        f.update(hitReaction="", attackers=0)
        if 7000 <= f["wallMs"] < 8000:
            f["attackers"] = 2
    g = P.grade_p1(out)
    assert g["verdict"].startswith("STANCE FAILS") and "(attacked)" in g["verdict"]
    assert g["legs"]["aim_stand"]["attacked_frames"] >= 1
    out = synth(aiming=lambda step, t: stance_on(step, t) and not 7000 <= t < 8000)
    for f in out["probe"]["frames"]:
        f.update(hitReaction="", attackers=0)
    g = P.grade_p1(out)
    assert g["verdict"].startswith("STANCE FAILS") and "attacked" not in g["verdict"]
    assert g["legs"]["aim_stand"]["attacked"] is False


def test_a_wrong_mod_version_and_a_missing_probe_are_reported():
    assert P.grade_p1(synth(aiming=stance_on, mod="1.5.3"))["mod_ok"] is False
    g = P.grade_p1({})
    assert g["verdict"].startswith("STANCE FAILS") and g["release_ok"] is False and g["handover_ok"] is None


def test_grade_records_a_grade_failure_rather_than_raising(monkeypatch):
    out = {}
    monkeypatch.setattr(P, "grade_p1", lambda o: 1 / 0)
    P.grade(out)
    assert "grade_p1_error" in out and "grade_p1" not in out
