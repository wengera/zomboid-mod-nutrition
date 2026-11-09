"""The facing trial (Plan 32 Task 2, ruling P31-T): one short live boot that holds the character still and runs Task 1's
`probe` act (PZA/1.11, `PZAgent_FacingProbe.lua`) under each facing mechanism for N ticks, standing and back-pedalling,
so `tools/facing_score.py` ranks the mechanisms by the engine's own body angle into `testing/trials/facing.md`.
Driven by `testing/agent/drivers/x_facing.py`. A trial is not evidence (CLAUDE.md section 5, "Trials"): its run stays in
`testing/runs/x_facing-<stamp>/`, nothing is copied into `testing/artifacts/`, no row cites it. The machine-safety rules
bind the boot all the same. There is no planner decision: the session's "planner" is `ProbeSequencer`, a scripted
sequencer, and the boot, pre-boot and teardown are `driverlib/trial.py`'s (`trial.preboot`, `trial.boot_and_run`).

THE ARGUMENTS (`parse_argv`, `flags`; the driver's ALLOWED): `--fixture <name>` (default `arena-east`), `--ticks N`
(the ring ticks of every Probe, an integer from 1 to MAX_TICKS, default 60), `--zombie` (bare: one zombie at the target
for the press modes), `--modes a,b,c` (the plan filtered by mode name, each name once, the order and both movements
kept), `--minutes N` (the loop's wall cap, default the trial's), `--detached` (bare, past the foreground bound).
Anything else is refused in one line naming the driver's file; each flag once.

THE PLAN (`MODES`, one `(mode, vx, vy, k)` per run): the seven modes standing, in the schema's order but for the turn
rate taken twice (`turn_k` at k 3 and 5), then `read`, `snap_aimed`, `unaimed_face` and `unaimed_snap` back-pedalling
(`BACK`: the unit vector away from the cursor's bearing, `(-cos c, -sin c)`, filled once c is read, so the walk and the
facing toward the target differ). `PRESS_MODES` are the two that press `DoAttack` at a zombie target.

THE SEQUENCER (`ProbeSequencer.tick(world, actions)`, five states): `aim`: one `Aim(0, 0, 2.0)` holds the stance 2 s
so `me.aimAngle` reads the cursor's bearing; `hold`: the tick samples `me.aimAngle` (null skipped) until the Aim ends
and the rest passes, then `cursor_bearing` (the median of the first 20 samples, angles unwrapped about the first) is c,
the target `target_point(me, c)` six tiles at c + pi/2; `spawn`/`confirm` (only `--zombie`): one `createhorde2` at the
target square over RCON, confirmed when a zombie not listed before stands within CONFIRM_R tiles of it (re-sent once
after CONFIRM_S; a second miss ends the run with `error`), its id the `targetId` of the press runs; `probe`: one Probe
sent when the previous act ended plus REST_S of rest; after the last one ends and rests, a `Stop`, and `finished` is
True (the chain ends the loop on it; `--minutes` still bounds it). The decision line every tick (written to the run's
decision.log): `{"wall", "branch": "probe", "action": <the sent command or None>, "aid", "plan_index", "mode", "move":
"still"|"back", "k", "cursor_bearing", "target": [x, y]}`, so `facing_score.py` reads the plan without the state log.

THE ARGS (`flags`) carry the keys `trial.boot_and_run` and `trial.trial_record` read, filled with the facing's own: the
variant `facing`, the `street` wave plan (no spawns), no teleport, no snapshot, no model.
"""
import json
import math
import os
import re
import statistics
import types

from agent.base import pza1
from agent.base.actions import TERMINAL
from agent.driverlib import day as DY
from agent.driverlib import session as DS
from agent.driverlib import trial as TR

DEFAULT_FIXTURE = "arena-east"
DEFAULT_TICKS = 60
MAX_TICKS = 600                      # a ring tick is a client tick: 10 s at 60 Hz, well inside the Probe's deadline
VARIANT = "facing"                   # trial.json's `variant` and the run id's tail (the key alone: x_facing-<stamp>)
BACK = "back"                        # a MODES movement: the unit vector away from the cursor's bearing, filled at run time
MODES = [("read", 0, 0, -1), ("snap_aimed", 0, 0, -1), ("unaimed_face", 0, 0, -1), ("unaimed_snap", 0, 0, -1),
         ("block_aim", 0, 0, -1), ("ignore_aim", 0, 0, -1), ("turn_k", 0, 0, 3.0), ("turn_k", 0, 0, 5.0),
         ("read", BACK, BACK, -1), ("snap_aimed", BACK, BACK, -1), ("unaimed_face", BACK, BACK, -1),
         ("unaimed_snap", BACK, BACK, -1)]
PRESS_MODES = ("snap_aimed", "unaimed_snap")          # the modes that press DoAttack at a zombie target
AIM_S = 2.0                          # the stance held for the cursor's bearing
REST_S = 2.0                         # seconds of rest after an act ends, before the next
BEARING_FRAMES = 20                  # cursor_bearing's frames
TARGET_DIST = 6.0                    # tiles from the character to the target
CONFIRM_R = 2.0                      # tiles: a new zombie this near the spawn square confirms it
CONFIRM_S = 8.0                      # seconds a spawn has to reach the frames before its one re-send
PROBE_SLACK_S = 10.0                 # a Probe's deadline beyond its ring ticks at 20 per second
VALUED = ("--fixture", "--ticks", "--modes", "--minutes", "--dist")
BARE = ("--zombie", "--detached")
FIXTURE_RX = TR.FIXTURE_RX


# ---------------------------------------------------------------- the arguments
def usage(me):
    return ("%s takes only --fixture <name> [--ticks N] [--zombie] [--dist T] [--modes %s,...] [--minutes N] [--detached]"
            % (me, "|".join(pza1.PROBE_MODES[:2])))


def _tokens(argv):
    """{flag: value or True} for argv made only of the VALUED and BARE flags, each once; None when it is not."""
    got, i = {}, 0
    argv = list(argv)
    while i < len(argv):
        flag = argv[i]
        if flag in got:
            return None
        if flag in BARE:
            got[flag] = True
            i += 1
        elif flag in VALUED and i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            got[flag] = argv[i + 1]
            i += 2
        else:
            return None
    return got


def _dist(s):
    """The --dist tiles (the target point and the zombie square from the character), 0.5 to 12.0; None otherwise."""
    try:
        d = float(s)
    except ValueError:
        return None
    return d if 0.5 <= d <= 12.0 and d == d else None


def _ticks(s):
    return int(s) if re.fullmatch(r"[0-9]+", s) and 1 <= int(s) <= MAX_TICKS else None


def _mode_names(s):
    """The --modes list, or None when it names a mode twice, one not in the schema's enum, or none."""
    names = s.split(",")
    if not names or any(n not in pza1.PROBE_MODES for n in names) or len(set(names)) != len(names):
        return None
    return names


def parse_argv(argv, driver_file):
    """The one-line refusal of anything but the facing trial's arguments, else None."""
    me = os.path.basename(driver_file)
    head = "%s; refused: %s" % (usage(me), " ".join(argv))
    t = _tokens(argv)
    if t is None:
        return head
    why = None
    if "--fixture" in t and not FIXTURE_RX.match(t["--fixture"]):
        why = "--fixture takes a fixture name"
    elif "--ticks" in t and _ticks(t["--ticks"]) is None:
        why = "--ticks takes a whole number from 1 to %d" % MAX_TICKS
    elif "--dist" in t and _dist(t["--dist"]) is None:
        why = "--dist takes tiles from 0.5 to 12.0 (the target point and the zombie square from the character)"
    elif "--modes" in t and _mode_names(t["--modes"]) is None:
        why = "--modes takes distinct names of %s" % ", ".join(pza1.PROBE_MODES)
    elif "--minutes" in t and TR._minutes(t["--minutes"]) is None:
        why = "--minutes takes a number > 0 and at most %d" % TR.MAX_MINUTES
    else:
        bound = TR.wall_bound(flags(argv))["total_s"]
        if bound > TR.FOREGROUND_CAP_S and "--detached" not in t:
            why = ("the wall bound %s s passes the foreground cap %s s: pass --detached (the controller launches it "
                   "detached after Angus approves)" % (TR.tidy(bound), TR.tidy(TR.FOREGROUND_CAP_S)))
    return "%s (%s)" % (head, why) if why else None


def flags(argv):
    """The args dict off an argv parse_argv accepted: the facing's own (fixture, ticks, zombie, modes, minutes,
    detached) beside the keys the trial boot reads, fixed (the module docstring)."""
    t = _tokens(argv) or {}
    return {"variant": VARIANT, "fixture": t.get("--fixture", DEFAULT_FIXTURE),
            "ticks": _ticks(t["--ticks"]) if "--ticks" in t else DEFAULT_TICKS, "zombie": bool(t.get("--zombie")),
            "modes": _mode_names(t["--modes"]) if "--modes" in t else None,
            "dist": _dist(t["--dist"]) if "--dist" in t else TARGET_DIST,
            "minutes": TR._minutes(t["--minutes"]) if "--minutes" in t else TR.DEFAULT_MINUTES,
            "no_llm": True, "goals": TR.DEFAULT_GOALS, "waves": TR.DEFAULT_WAVES, "teleport": None,
            "make_fixture": None, "detached": bool(t.get("--detached"))}


# ---------------------------------------------------------------- the geometry
def filter_modes(modes, names):
    """`modes` kept to the runs whose mode name is in `names`, in order (both movements); all of them with no names."""
    return list(modes) if not names else [m for m in modes if m[0] in names]


def cursor_bearing(frames):
    """The median `me.aimAngle` (radians) over the first BEARING_FRAMES frames, null ones skipped, the angles unwrapped
    about the first read so a bearing straddling +-pi is one bearing; None when none read."""
    vals = [f["me"]["aimAngle"] for f in list(frames)[:BEARING_FRAMES]
            if isinstance(f.get("me"), dict) and isinstance(f["me"].get("aimAngle"), (int, float))]
    if not vals:
        return None
    base = vals[0]
    med = base + statistics.median(math.remainder(v - base, 2 * math.pi) for v in vals)
    return math.remainder(med, 2 * math.pi)


def target_point(me, c, dist=TARGET_DIST):
    """(x, y): the point `dist` tiles from the character at the bearing c + pi/2 (a quarter turn from the cursor)."""
    a = c + math.pi / 2
    return me["x"] + dist * math.cos(a), me["y"] + dist * math.sin(a)


def plan_of(modes, c, ticks, zid=None):
    """The Probe arguments of each run, in order: [{mode, move, k, vx, vy, ticks, targetId}] with BACK filled as the
    unit vector away from c, and the press modes carrying the zombie's id when one was confirmed."""
    out = []
    for mode, vx, vy, k in modes:
        back = vx == BACK
        out.append({"mode": mode, "move": "back" if back else "still", "k": k, "ticks": ticks,
                    "vx": (-math.cos(c) + 0.0) if back else 0.0, "vy": (-math.sin(c) + 0.0) if back else 0.0,
                    "targetId": zid if zid is not None and mode in PRESS_MODES else -1})
    return out


# ---------------------------------------------------------------- the sequencer
class ProbeSequencer:
    """The facing trial's session planner (the module docstring, THE SEQUENCER). `log_path` the decision log, `clock` the
    session's, `spawn(x, y)` the RCON createhorde2 at a square (None without --zombie). `finished` True after the Stop;
    `error` names why a run ended without its plan."""
    last_branch = "probe"

    def __init__(self, log_path, clock, ticks=DEFAULT_TICKS, zombie=False, modes=None, spawn=None, dist=TARGET_DIST):
        self.log_path, self.clock = log_path, clock
        self.ticks, self.zombie, self.spawn, self.dist = ticks, zombie, spawn, dist
        self.modes = filter_modes(MODES, modes)
        self.state, self.finished, self.error = "aim", False, None
        self.cur, self.rest_until = None, None
        self.frames, self.cursor, self.target, self.zid = [], None, None, None
        self.plan, self.i, self.sent_n = [], 0, 0
        self.t_spawn, self.resent, self.before = None, False, set()
        self.spawns = []
        self.rows = []
        open(log_path, "w", encoding="utf-8").close()

    # -- the act in flight and the rest after it
    def _free(self, now):
        """True once the last act ended (a terminal state) and the rest has passed."""
        if self.cur is not None:
            if self.cur.state not in TERMINAL:
                return False
            if self.rest_until is None:
                self.rest_until = (self.cur.ended_wall if self.cur.ended_wall is not None else now) + REST_S
        return self.rest_until is None or now >= self.rest_until

    def _sent(self, a):
        self.cur, self.rest_until = a, None
        return a

    def _fail(self, why, actions):
        self.error, self.finished = why, True
        return self._sent(actions.stop())

    # -- the tick
    def tick(self, world, actions):
        now = self.clock()
        a = None
        me = world.me or {}
        if self.state == "aim":
            a = self._sent(actions.send(pza1.Aim(0.0, 0.0, AIM_S), deadline_s=AIM_S + PROBE_SLACK_S))
            self.state = "hold"
        elif self.state == "hold":
            if isinstance(me.get("aimAngle"), (int, float)):
                self.frames.append({"me": {"aimAngle": me["aimAngle"]}})
            if self._free(now):
                a = self._bearing(world, actions, now)
        elif self.state == "confirm":
            a = self._confirm(world, actions, now)
        elif self.state == "probe" and self._free(now):
            a = self._next_probe(actions)
        self._log(now, a)
        return a

    def _bearing(self, world, actions, now):
        c = cursor_bearing(self.frames)
        me = world.me or {}
        if c is None or not all(isinstance(me.get(k), (int, float)) for k in ("x", "y")):
            return self._fail("no cursor bearing: me.aimAngle read null for the whole stance hold", actions)
        self.cursor = c
        self.target = target_point(me, c, dist=self.dist)
        if self.zombie:
            self.state = "confirm"
            self.before = set(world.zombies)
            self._spawn(now)
            return None
        self.plan, self.state = plan_of(self.modes, c, self.ticks), "probe"
        return self._next_probe(actions)

    def _spawn(self, now):
        sq = (int(math.floor(self.target[0])), int(math.floor(self.target[1])))
        self.spawns.append(sq)
        self.t_spawn = now
        self.spawn(*sq)

    def _confirm(self, world, actions, now):
        tx, ty = self.target
        for zid, z in sorted(world.zombies.items(), key=lambda kv: str(kv[0])):
            if zid not in self.before and math.hypot(z.get("x", 1e9) - tx, z.get("y", 1e9) - ty) <= CONFIRM_R:
                self.zid, self.plan, self.state = zid, plan_of(self.modes, self.cursor, self.ticks, zid), "probe"
                return self._next_probe(actions) if self._free(now) else None
        if now - self.t_spawn >= CONFIRM_S:
            if self.resent:
                return self._fail("no zombie listed within %s tiles of the spawn square after two sends" % CONFIRM_R,
                                  actions)
            self.resent = True
            self._spawn(now)
        return None

    def _next_probe(self, actions):
        if self.i >= len(self.plan):
            self.finished = True
            return self._sent(actions.stop())
        p = self.plan[self.i]
        if p["targetId"] >= 0:
            cmd = pza1.Probe(p["mode"], targetId=p["targetId"], ticks=p["ticks"], k=p["k"], vx=p["vx"], vy=p["vy"])
        else:
            cmd = pza1.Probe(p["mode"], x=self.target[0], y=self.target[1], ticks=p["ticks"], k=p["k"], vx=p["vx"],
                             vy=p["vy"])
        a = self._sent(actions.send(cmd, deadline_s=p["ticks"] / 20.0 + PROBE_SLACK_S))
        self.rows.append({"plan_index": self.i, "aid": a.aid, "mode": p["mode"], "move": p["move"], "k": p["k"]})
        self.i += 1
        return a

    # -- the decision line and the record
    def _log(self, now, a):
        row = self.rows[-1] if self.rows else {}
        line = {"wall": now, "branch": "probe", "state": self.state,
                "action": {"type": a.type, "args": a.args} if a is not None else None,
                "aid": a.aid if a is not None else None, "plan_index": row.get("plan_index"),
                "mode": row.get("mode"), "move": row.get("move"), "k": row.get("k"),
                "cursor_bearing": self.cursor, "target": list(self.target) if self.target else None}
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(line, default=str) + "\n")

    def record(self):
        return {"cursor_bearing": self.cursor, "target": list(self.target) if self.target else None,
                "zombie_id": self.zid, "spawns": [list(s) for s in self.spawns], "error": self.error,
                "finished": self.finished, "plan": [dict(r) for r in self.rows]}


# ---------------------------------------------------------------- the session
class FacingChain(DY.Chain):
    """day.Chain for a planner with no goals or night: the record carries the sequencer's, and the loop ends when the
    sequencer finishes (its Stop sent: the chain's closing Stop follows as every session's)."""

    def planner_tick(self):
        super().planner_tick()
        if getattr(self.planner, "finished", False):
            raise DS.Stop("day_cap", "the facing plan finished: %s" % (self.planner.error or "every probe ran"))

    def extra_record(self):
        return {"t_loop0_ms": self.t_loop0 * 1000.0 if self.t_loop0 is not None else None,
                "results": [{"aid": a.aid, "type": a.type, "state": a.state, "result": a.result}
                            for a in self.sent if a.type == "probe"],
                "facing": self.planner.record()}

    def end_state(self):
        last = self.frames[-1] if self.frames else {}
        me = DS._d(last.get("me"))
        return {"pos": [me.get("x"), me.get("y"), me.get("z")] if me else None, "health": DS.body_health(last),
                "start_health": DS.body_health(self.first_frame or {})}


def run_session(args, xs, transport, pre, note_planner, **kw):
    """The facing session: a FacingChain over the sequencer, its createhorde2 sent through `xs.rcon` (the trial's
    CREATEHORDE2_CMD at the character's floor, count 1, radius 0), built, noted, run; returned for the teardown."""
    def spawn(x, y):
        return xs.rcon(TR.CREATEHORDE2_CMD.format(x=x, y=y, z=0, count=1, radius=0), "facing_zombie")

    def planner(world, actions, log_path, clock):
        return ProbeSequencer(log_path, clock, ticks=args["ticks"], zombie=args["zombie"], modes=args["modes"], dist=args.get("dist", TARGET_DIST),
                              spawn=spawn)
    limits = dict(TR.limits_of(args), **(kw.pop("limits", None) or {}))
    sess = DY.make_day_session(xs, transport, planner, limits=limits, cls=FacingChain, **kw)
    note_planner(sess.planner)
    sess.run()
    return sess


# ---------------------------------------------------------------- the pre-boot
def preboot(args, profile, **kw):
    """The trial's pre-boot (trial.preboot) over the facing's args: the variant check reads a one-name control (there is
    no planner package), the model is never probed (no_llm)."""
    kw.setdefault("control", types.SimpleNamespace(CONTROLS=(VARIANT,)))
    return TR.preboot(dict(args, no_llm=True, make_fixture=None), profile, **kw)
