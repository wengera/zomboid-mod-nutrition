"""p_stance -- Plan 24 Task 16 (ruling P24-T): a two-minute live probe of the combat stance on PZA/1.5.4.

Why: in the sixth chain's first session the stance never read live (`me.aiming` false on all 185 aim-leg frames; the
rows #4321-#4331). Task 9 fix 6 (PZA/1.5.4: the frame's `me.forceAim`, the aim result's `heldFrames` and `ticks`, the
stance asserted by `setForceAim` in OnPlayerUpdate every frame) changed the `aim` skill; before the seventh chain boots
on it this probe proves the stance live, with no planner: a fixed script of actions goes through the same transport and
the library's session loop, the frames are read, and the grade is offline.

THE SCRIPT (Script, the loop's planner; every step one decision line in decision.log whose goal type is the step's
name, so the shot taker shoots on each step, and one row in out["probe"]["steps"]), in order:
  1 idle          5 s, nothing sent; `aiming` and `forceAim` read false.
  2 aim_stand     aim {bearing 0, vx 0, vy 0, seconds 5}, no target: the stance standing, facing east.
  3 aim_strafe    aim {bearing 0, vx -1, vy 0, seconds 5}: face east, move west (the backpedal): the position change
                  along the vector, the heading held east, the gait and `running`.
  4 aim_target    only when a zombie is listed within the weapon's reach (`weapon.reach` on the frame, else
                  FIGHT_REACH) at that moment: aim {targetId, vx 0, vy 0, seconds 3},
                  then
    attack        attack {targetId} (one swing), then
    post_attack   2.5 s idle (the kept stance runs out its hold); else all three are skipped, each row saying so.
  5 walk          walkTo 3 tiles east of where the character stands, at a walk, after the stance: `aiming` drops.
  6 settle        1.5 s idle; then the stop reason `script_done` (the loop's Stop).
The loop runs at PLANNER_HZ 10 so a step starts within a tenth of a second of the last one's end. BUDGET_S (150 s) is
the loop's wall time after the first frame (the library's DAY_CAP_S); the boot has its own BOOT_BUDGET_S. `rate` is
not sent: the frames come at the Lua's default rate and the grade counts the frames it reads.

THE RECORD out["probe"]: {steps [{step, state, reason, aid, type, args, result, startMs, endMs, ackedMs, skipped,
note}] (the *Ms are this host's epoch ms: the python clock, which is the client's wallMs clock on the one host),
frames [{seq, wallMs, x, y, dir, pace, moving, running, sprinting, aiming, forceAim, hitReaction, attackers,
zombiesSeen}] (every frame, compact),
hello {mod, ...}}; out["grade_p1"] is `grade_p1(out)`, else out["grade_p1_error"].

THE GRADE (grade_p1, in this file): a leg's frames are those from LEG_SETTLE_MS after its action was accepted to the
action's end (the first second is the stance taking hold, which the Lua counts from the second tick on).
  per aim leg (stand, strafe, target): n, held_frac (frames with `aiming` true over n), force_frac (`forceAim`),
    first_false (the first leg frame with `aiming` false), result {held, heldFrames, ticks, d}, result_frac
    (heldFrames over ticks);
  strafe_tiles, strafe_tiles_per_s, strafe_ok (the change along the leg's vector at least STRAFE_MIN_TILES), the
    running, moving and sprinting fractions and the directions read;
  handover_ok (the swing from the stance: the attack done, `aiming` true through the second after it was accepted);
    None when the target legs were skipped;
  release_ok (the walk done, `aiming` and `forceAim` false on RELEASE_MIN of the frames from the walk's ack to the
    script's end);
  per aim leg also attacked_frames (frames with `hitReaction` non-empty or `attackers` above 0) and attacked (any):
    a dip in held_frac under a hit is told from a failed stance;
  dir_ok (the strafe leg's frames read the one heading STRAFE_DIR, the bearing 0 facing east);
  verdict: `STANCE HOLDS` when stand and strafe both read `aiming` true on at least HELD_MIN of their frames, else
    `STANCE FAILS` naming the first frame it read false (`(attacked)` appended when a failed leg was attacked, and
    `dir` when the strafe heading turned); either verdict takes `; mod != 1.5.4` for a stale mod and
    `; strafe_ok false` for a strafe that did not move.

RULES: never edited after its run; takes only `--session 1` and `--fixture agent`, each once (anything else is
refused); one live session at a time; free memory gated at MIN_FREE_GB before the boot; never -safemode; launched by
the controller. Nothing is imported from a frozen driver but `xlib` (and `_dlib` through the library).
"""
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import xlib as X                                      # noqa: E402,F401 - the provenance the RULES name
from agent.base import pza1                           # noqa: E402
from agent.base.planner import policies as POL        # noqa: E402
from agent.base.world import me_xy                    # noqa: E402
from agent.driverlib import day as DY                 # noqa: E402
from agent.driverlib import session as DS             # noqa: E402
from agent.driverlib.polls import PollThread          # noqa: E402

KEY = "p_stance"
DRIVER = "p_stance.py"
ARTIFACT = "p_stance.json"
PROFILE = "testing/profiles/agent.toml"
REPO = DS.REPO
_ME = os.path.basename(os.path.abspath(__file__))
ALLOWED = ("--session", "--fixture")
USER = DY.USER
FIXTURE = "agent"
MOD_VERSION = "1.5.4"
BUDGET_S = 150.0                  # the loop's wall time after the first frame (the library's DAY_CAP_S)
BOOT_BUDGET_S = 900.0             # the wall budget from the memory gate, the boot included
PLANNER_HZ = 10
MIN_FREE_GB = DY.MIN_FREE_GB
LIMITS = {"DAY_CAP_S": BUDGET_S, "PLANNER_HZ": PLANNER_HZ, "DAMAGE_POLL_S": DY.DAMAGE_POLL_S}
CONSTANTS = dict(DS.DEFAULTS, **LIMITS, BUDGET_S=BUDGET_S, BOOT_BUDGET_S=BOOT_BUDGET_S)
GRADE_KEY = "grade_p1"

# ---- the script
IDLE_S = 5.0
STAND_S = 5.0
STRAFE_S = 5.0
TARGET_S = 3.0
POST_ATTACK_S = 2.5
SETTLE_S = 1.5
FIGHT_REACH = POL.FIGHT_REACH     # the reach when the frame lacks the weapon's: an attack beyond reach releases the stance
WALK_TILES = 3.0
STEPS = ("idle", "aim_stand", "aim_strafe", "aim_target", "attack", "post_attack", "walk", "settle")
STRAFE_VEC = (-1.0, 0.0)
STRAFE_DIR = "E"                  # the strafe leg faces bearing 0: east, while it moves west

# ---- the grade
LEG_SETTLE_MS = 1000.0
HELD_MIN = 0.9
STRAFE_MIN_TILES = 1.0
RELEASE_MIN = 0.9
HANDOVER_WINDOW_MS = 1000.0
AIM_LEGS = ("aim_stand", "aim_strafe", "aim_target")


# ================================================================ arguments
def parse_argv(argv, driver_file):
    """The one-line refusal of anything but `--session 1` and `--fixture agent` (each once), else None."""
    refusal = DS.parse_argv(argv, driver_file, ALLOWED)
    if refusal:
        return refusal
    f = DS.parse_flags(argv, ALLOWED) or {}
    if f.get("--session", "1") != "1" or f.get("--fixture", FIXTURE) != FIXTURE:
        return "%s: takes only --session 1 and --fixture %s; refused: %s" % (os.path.basename(driver_file), FIXTURE,
                                                                             " ".join(argv))
    return None


def flags(argv):
    """{session, fixture, prev} off an argv parse_argv accepted: always session 1, fixture agent, no prev."""
    return {"session": 1, "fixture": FIXTURE, "prev": None}


# ================================================================ the script
class Script:
    """The loop's planner: the fixed script of the module docstring. `tick(world, actions)` returns the Action it
    sent (or None) and raises the library's Stop("script_done") after the last step. Its decision lines go to
    `log_path` (one per step start: branch "script", goal {type: step name}); its step rows are `rows`."""

    def __init__(self, world, actions, log_path, clock):
        self.world, self.actions, self.log_path, self.clock = world, actions, log_path, clock
        self.i = 0
        self.cur = None            # the open step: {row, action, until}
        self.rows = []
        self.last_branch = None
        self.target = None         # the zombie id the target legs use
        self.skip_target = False

    # -- the log
    def _log(self, name, row):
        line = {"wall": self.clock(), "branch": "script", "goal": {"type": name}, "sent": row.get("aid") is not None,
                "inputs": {"step": name, "args": row.get("args"), "note": row.get("note")}}
        try:
            with open(self.log_path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(line, default=str) + "\n")
        except OSError:
            pass

    # -- the steps
    def _plan(self, name):
        """(cmd, wait_s, note) of the step: a command to send, else seconds to wait, else (None, None, why) skipped."""
        w = self.world
        if name == "idle":
            return None, IDLE_S, None
        if name == "aim_stand":
            return pza1.Aim(vx=0.0, vy=0.0, seconds=STAND_S, targetId=-1, bearing=0.0), None, None
        if name == "aim_strafe":
            return pza1.Aim(vx=STRAFE_VEC[0], vy=STRAFE_VEC[1], seconds=STRAFE_S, targetId=-1, bearing=0.0), None, None
        if name == "aim_target":
            wp = getattr(w, "weapon", None)
            reach = wp.get("reach") if isinstance(wp, dict) else None
            reach = float(reach) if isinstance(reach, (int, float)) and not isinstance(reach, bool) else FIGHT_REACH
            near = sorted((z.get("dist"), zid) for zid, z in (w.zombies or {}).items()
                          if isinstance(z.get("dist"), (int, float)) and z["dist"] <= reach)
            if not near:
                self.skip_target = True
                return None, None, "no zombie listed within the weapon's reach (%s tiles): the target legs are skipped" % reach
            self.target = near[0][1]
            return pza1.Aim(vx=0.0, vy=0.0, seconds=TARGET_S, targetId=self.target, bearing=-1.0), None, None
        if name == "attack":
            if self.skip_target:
                return None, None, "skipped with the target legs"
            return pza1.Attack(targetId=self.target), None, None
        if name == "post_attack":
            if self.skip_target:
                return None, None, "skipped with the target legs"
            return None, POST_ATTACK_S, None
        if name == "walk":
            xy = me_xy(w)
            if xy is None:
                return None, None, "no position read: the walk is skipped"
            return pza1.WalkTo(x=float(xy[0]) + WALK_TILES, y=float(xy[1]), gait="walk"), None, None
        if name == "settle":
            return None, SETTLE_S, None
        raise ValueError("unknown step %r" % name)

    def _finish(self):
        s, self.cur = self.cur, None
        row, a = s["row"], s["action"]
        now = self.clock()
        if a is not None:
            row.update(state=a.state, reason=a.reason, result=a.result,
                       ackedMs=a.acked_wall * 1000.0 if a.acked_wall is not None else None,
                       endMs=(a.ended_wall if a.ended_wall is not None else now) * 1000.0)
        else:
            row.update(state="done", endMs=s["until"] * 1000.0)

    def tick(self, world, actions):
        now = self.clock()
        if self.cur is not None:
            a = self.cur["action"]
            if a is not None:
                if not actions.done(a):
                    return None
            elif now < self.cur["until"]:
                return None
            self._finish()
        while self.i < len(STEPS):
            name = STEPS[self.i]
            self.i += 1
            cmd, wait_s, note = self._plan(name)
            row = {"step": name, "state": None, "reason": "", "aid": None, "type": None, "args": None, "result": None,
                   "startMs": now * 1000.0, "endMs": None, "ackedMs": None, "skipped": cmd is None and wait_s is None,
                   "note": note}
            self.rows.append(row)
            if row["skipped"]:
                row.update(state="skipped", endMs=now * 1000.0)
                self._log(name, row)
                continue
            if cmd is not None:
                a = actions.send(cmd, deadline_s=getattr(cmd, "seconds", 0.0) + 10.0 if cmd.TYPE == "aim" else 30.0)
                row.update(aid=a.aid, type=a.type, args=dict(a.args))
                self.last_branch = "script"
                self._log(name, row)
                self.cur = {"row": row, "action": a, "until": None}
                return a
            row.update(type="wait", args={"seconds": wait_s})
            self._log(name, row)
            self.cur = {"row": row, "action": None, "until": now + wait_s}
            return None
        raise DS.Stop("script_done", "the script's %d steps ran" % len(STEPS))


# ================================================================ the session
class Probe(DS.Session):
    """The library's Session with the probe's two hooks: every frame kept compact, the script's rows and the hello in
    the record."""

    def __init__(self, *a, **kw):
        self.probe_frames = []
        super().__init__(*a, **kw)

    def on_frame(self, line):
        me = self.world.me if isinstance(self.world.me, dict) else {}
        self.probe_frames.append({
            "seq": line.get("seq"), "wallMs": line.get("wallMs"), "x": me.get("x"), "y": me.get("y"),
            "dir": me.get("dir"), "pace": me.get("pace"), "moving": me.get("moving"), "running": me.get("running"),
            "sprinting": me.get("sprinting"), "aiming": me.get("aiming"), "forceAim": me.get("forceAim"),
            "hitReaction": me.get("hitReaction"), "attackers": me.get("attackers"),
            "zombiesSeen": me.get("zombiesSeen")})

    def extra_record(self):
        """out["probe"] rebuilt at every save (the grade reads it); the loop's own record takes nothing."""
        hello = self.world.hello if isinstance(self.world.hello, dict) else {}
        self.out["probe"] = {"steps": [dict(r) for r in self.planner.rows], "frames": list(self.probe_frames),
                             "hello": {"mod": hello.get("mod"), "proto": hello.get("proto"),
                                       "build": hello.get("build")}}
        return {}


def make_session(xs, transport, **kw):
    """The probe's Session on the script: LIMITS laid over the library's DEFAULTS (`limits` over them), a PollThread on
    the session's clock and the library's shots; `kw` its clock, sleep, free, polls and shots."""
    clock = kw.get("clock") or time.time
    lim = dict(LIMITS, **(kw.pop("limits", None) or {}))
    return Probe(xs, transport, planner_factory=Script, limits=lim,
                 polls=kw.pop("polls", None) or PollThread(clock),
                 shots=kw.pop("shots", None) if "shots" in kw else DY.day_shots(xs, clock), **kw)


# ================================================================ pre-boot
def preboot(driver_file, args, repo=REPO):
    """The library's pre-boot checks (DS.preboot) and the fixture's (DY.chain_checks: the agent fixture reads)."""
    pre, ok = DS.preboot(driver_file, KEY, DRIVER, PROFILE, repo)
    pre["chain_checks"], ok2 = DY.chain_checks(args)
    return pre, bool(ok and ok2)


def run_session(xs, transport, prev, pre):
    sess = make_session(xs, transport)
    sess.run()
    return sess


# ================================================================ the grade
def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _frac(rows, key):
    vals = [r.get(key) for r in rows]
    return (sum(1 for v in vals if v is True) / len(vals)) if vals else None


def leg_frames(frames, row, settle_ms=LEG_SETTLE_MS):
    """The frames of an action row's leg: wallMs from its ack plus `settle_ms` to its end; [] without both."""
    lo, hi = _num(row.get("ackedMs")), _num(row.get("endMs"))
    if lo is None or hi is None:
        return []
    return [f for f in frames if _num(f.get("wallMs")) is not None and lo + settle_ms <= f["wallMs"] <= hi]


def is_attacked(f):
    """True when a frame reads a hit reaction or an attacker."""
    a = f.get("attackers")
    return bool(f.get("hitReaction")) or (isinstance(a, (int, float)) and not isinstance(a, bool) and a > 0)


def grade_leg(frames, row):
    """One aim leg's reading: {n, held_frac, force_frac, first_false, attacked_frames, attacked, result, result_frac,
    state}."""
    fr = leg_frames(frames, row)
    att = sum(1 for f in fr if is_attacked(f))
    res = row.get("result") if isinstance(row.get("result"), dict) else {}
    first_false = next((f.get("seq") for f in fr if f.get("aiming") is not True), None)
    hf, tk = _num(res.get("heldFrames")), _num(res.get("ticks"))
    return {"n": len(fr), "held_frac": _frac(fr, "aiming"), "force_frac": _frac(fr, "forceAim"),
            "first_false": first_false, "attacked_frames": att, "attacked": att > 0, "state": row.get("state"), "reason": row.get("reason"),
            "result": {k: res.get(k) for k in ("held", "heldFrames", "ticks", "d")},
            "result_frac": (hf / tk) if hf is not None and tk else None}


def strafe_reading(frames, row, vec=STRAFE_VEC):
    """The strafe leg's displacement along its vector: {strafe_tiles, strafe_tiles_per_s, strafe_ok, running_frac,
    moving_frac, sprinting_frac, dirs}."""
    fr = leg_frames(frames, row)
    out = {"strafe_tiles": None, "strafe_tiles_per_s": None, "strafe_ok": False, "running_frac": _frac(fr, "running"),
           "moving_frac": _frac(fr, "moving"), "sprinting_frac": _frac(fr, "sprinting"),
           "dirs": sorted({str(f.get("dir")) for f in fr})}
    out["dir_ok"] = bool(fr) and out["dirs"] == [STRAFE_DIR]
    pts = [f for f in fr if _num(f.get("x")) is not None and _num(f.get("y")) is not None]
    if len(pts) < 2:
        return out
    a, b = pts[0], pts[-1]
    norm = math.hypot(*vec) or 1.0
    tiles = ((b["x"] - a["x"]) * vec[0] + (b["y"] - a["y"]) * vec[1]) / norm
    dt = (b["wallMs"] - a["wallMs"]) / 1000.0
    out.update(strafe_tiles=tiles, strafe_tiles_per_s=(tiles / dt) if dt > 0 else None,
               strafe_ok=tiles >= STRAFE_MIN_TILES)
    return out


def handover(frames, steps):
    """True when the swing came from the stance: the attack done and `aiming` true on HELD_MIN of the frames of the
    HANDOVER_WINDOW_MS after it was accepted; None when the target legs were skipped."""
    att, tgt = steps.get("attack"), steps.get("aim_target")
    if att is None or tgt is None or att.get("skipped") or tgt.get("skipped"):
        return None
    lo = _num(att.get("ackedMs"))
    if att.get("state") != "done" or lo is None:
        return False
    fr = [f for f in frames if _num(f.get("wallMs")) is not None and lo <= f["wallMs"] <= lo + HANDOVER_WINDOW_MS]
    return bool(fr) and (_frac(fr, "aiming") or 0.0) >= HELD_MIN


def release(frames, steps):
    """True when the walk was done and `aiming` and `forceAim` read false on RELEASE_MIN of the frames from the walk's
    ack to the script's end; False when it was not done or no frame was read."""
    walk = steps.get("walk")
    if walk is None or walk.get("state") != "done" or _num(walk.get("ackedMs")) is None:
        return False
    fr = [f for f in frames if _num(f.get("wallMs")) is not None and f["wallMs"] >= walk["ackedMs"]]
    if not fr:
        return False
    off = sum(1 for f in fr if f.get("aiming") is False and f.get("forceAim") is False)
    return off / len(fr) >= RELEASE_MIN


def grade_p1(out):
    """out["grade_p1"] (the module docstring): the legs' fractions, the strafe, the hand-over, the release and the
    one-line verdict."""
    probe = out.get("probe") if isinstance(out.get("probe"), dict) else {}
    frames, rows = probe.get("frames") or [], probe.get("steps") or []
    steps = {r["step"]: r for r in rows}
    legs = {}
    for name in AIM_LEGS:
        r = steps.get(name)
        legs[name] = grade_leg(frames, r) if r is not None and not r.get("skipped") else None
    idle = steps.get("idle")
    idle_fr = [f for f in frames if idle and _num(idle.get("startMs")) is not None and _num(idle.get("endMs"))
               is not None and idle["startMs"] <= f.get("wallMs", 0) <= idle["endMs"]]
    g = {"legs": legs, "held_frac": {k: (v or {}).get("held_frac") for k, v in legs.items()},
         "force_frac": {k: (v or {}).get("force_frac") for k, v in legs.items()},
         "idle": {"n": len(idle_fr), "aiming_frac": _frac(idle_fr, "aiming"), "force_frac": _frac(idle_fr, "forceAim")},
         "strafe": strafe_reading(frames, steps["aim_strafe"]) if "aim_strafe" in steps else None,
         "handover_ok": handover(frames, steps), "release_ok": release(frames, steps),
         "hello_mod": (probe.get("hello") or {}).get("mod"),
         "target_skipped": bool(steps.get("aim_target", {}).get("skipped")),
         "stop": (out.get("stop") or {}).get("reason")}
    g["mod_ok"] = g["hello_mod"] == MOD_VERSION
    g["strafe_tiles"] = (g["strafe"] or {}).get("strafe_tiles")
    g["strafe_tiles_per_s"] = (g["strafe"] or {}).get("strafe_tiles_per_s")
    g["strafe_ok"] = bool((g["strafe"] or {}).get("strafe_ok"))
    fails = []
    g["dir_ok"] = bool((g["strafe"] or {}).get("dir_ok"))
    for name in ("aim_stand", "aim_strafe"):
        leg = legs.get(name)
        if leg is None or leg["n"] == 0:
            fails.append("%s read no frames" % name)
        elif (leg["held_frac"] or 0.0) < HELD_MIN:
            fails.append("%s: first frame with aiming false: seq %s (held_frac %.2f)" % (
                name, leg["first_false"], leg["held_frac"] or 0.0) + (" (attacked)" if leg["attacked"] else ""))
    if g["strafe"] and g["strafe"]["dirs"] and not g["dir_ok"]:
        fails.append("aim_strafe: dir turned, read %s not %s" % (g["strafe"]["dirs"], STRAFE_DIR))
    g["verdict"] = "STANCE HOLDS" if not fails else "STANCE FAILS: " + "; ".join(fails)
    if not g["mod_ok"]:
        g["verdict"] += "; mod != %s" % MOD_VERSION
    if not g["strafe_ok"]:
        g["verdict"] += "; strafe_ok false"
    g["report_lines"] = [
        g["verdict"],
        "held_frac %s force_frac %s" % (g["held_frac"], g["force_frac"]),
        "strafe %s tiles, %s tiles/s, strafe_ok %s" % (g["strafe_tiles"], g["strafe_tiles_per_s"], g["strafe_ok"]),
        "handover_ok %s release_ok %s mod %s stop %s" % (g["handover_ok"], g["release_ok"], g["hello_mod"], g["stop"])]
    return g


def grade(out):
    DY.grade(out, GRADE_KEY, grade_p1)


# ================================================================ the boot
def main(args, budget_s=BOOT_BUDGET_S):
    return DY.boot_and_run(args, lambda: preboot(_ME, args), run_session, grade, key=KEY, driver=DRIVER,
                           artifact=ARTIFACT, profile=PROFILE, constants=CONSTANTS, grade_key=GRADE_KEY, user=USER,
                           budget_s=budget_s, min_free_gb=MIN_FREE_GB)


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main(flags(sys.argv[1:]))
