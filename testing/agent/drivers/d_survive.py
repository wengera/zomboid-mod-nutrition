"""d_survive -- Plan 22 Task 17, the agent base's acceptance (spec § 10): one survival day on `agent` (fixture `agent`,
Zombies = 5, one admin -debug client, PZTestKit + PZAgent, the 90-minute day, sleep allowed) under the Python `Survive`
planner (agent/base/planner/survive.py; no sleep branch, ruling P22-1) over the PZA/1 file channel, the server's
`stats.all`, `players` and `damage.watch since` polled into the `World`. One detached session (ruling P22-9) of up to
DAY_CAP_S of loop wall time inside BUDGET_S; the controller launches it and polls the persisted artifact. No pass/fail
gate: `agent.base.gates.grade_d` is a report (d_grade.py prints it), with `death_explained` for a death.

The form is c_survive.py's (Plan 21b Stage C, frozen; its docstring L1-L57 is the model) ported onto
FileTransport / World / Actions / Survive; nothing is imported from a frozen driver but `_dlib` and `xlib`.

PHASES (each through xs.run_phase; a phase's fault lands under out["phase_errors"][name]; each reading at
out["readings"][phase]):
  hello    pump until the hello line (HELLO_TIMEOUT_S); its proto must be "PZA/1" and its mode "append" (anything
           else fails the phase); then until the first frame (FRAME_TIMEOUT_S). {ok, proto, mode, build, hello,
           first_frame {seq, wallMs}, wait_ms}. A failed hello skips the kit and the loop (stop `error`).
  kit      x5_combat's kit: KIT x1 through xs.spawn (RCON additem confirmed by item.get); pump until an `item_added`
           of KIT read after the spawn began (KIT_TIMEOUT_S; else the first KIT the inventory already holds, source
           "inventory"); Equip(itemId) awaited to a terminal state (ACT_TIMEOUT_S); pump until a frame's weapon.type
           is KIT (EQUIP_TIMEOUT_S). {spawn, item {itemId, source, seq, wallMs} | None, equip {aid, state, reason,
           result, ended_wall} | None, weapon_frame {seq, wallMs, type} | None, armed, ok}. An unconfirmed spawn or
           equip is recorded and the session goes on (the planner flees every threat while unarmed).
  survive  the planner loop, every POLL_S of the clock:
             pump the transport (each line into World, then Actions): a frame's body.health <= STOP_HEALTH, the
               lua_error events and the link's silence are read here; the last LAST_FRAMES frames' {seq, wallMs,
               gameMin, worldAge, me, body, load, stats} are kept;
             at PLANNER_HZ: survive.tick(world, actions) (it writes decision.log beside the artifact; the driver
               reads it incrementally, keeps its last LAST_DECISIONS lines and builds the fights from its threat
               branch); every Action it returns is kept with its end (loop.actions);
             every SERVER_POLL_S, the first at the loop's start: the server's stats.all (_dlib.bus_stats) merged by
               World.merge_server (the stats map, the read's wallMs), then a pump, then one needs row
               [gameMin, hunger, thirst, fatigue, health, serverHunger] off the frame nearest the read's wallMs, and
               needs_pairs [{frameSeq, frameWallMs, serverWallMs, dtMs, paired}] beside it: paired when the frame
               and the read are within PAIR_S (the same wall second; serverHunger None when the read failed);
               then the `players` list (@reply [<username>, ...], {} when nobody is online);
             every DAMAGE_POLL_S, the first at the loop's start (it installs the server's listener):
               `damage.watch USER since <i>`, i the largest record index merged, merged by World.merge_damage; each
               new record kept as {i, tag, amount, wall (the server's TK.now, epoch ms), wallMs (the merge, this
               process's clock)} (the last SERVER_RECORDS_KEPT of them) and summed by tag (loop.damage.totals:
               the server's health lost by source);
             every MEM_POLL_S, the first MEM_POLL_S after the loop's start: host free memory (xlib.free_gb), every
               read under out["memory_reads"];
             every PERSIST_S: out["loop"] rebuilt and xs.persist() (the controller polls the persisted artifact).
           STOP CONDITIONS (c_survive's), the first that holds ends the loop, named in out["stop"] {reason, detail,
           wallS, gameMin, worldAge}:
             death           a frame's body.health <= STOP_HEALTH, or a `players` reply (a list, or {} for nobody)
                             without USER; a players reply that is an error (a string, a dict with an `error` key, a
                             stall) is no death: it counts as a failed read, the last kept as loop.players_error;
             bus_dead        BUS_DEAD_POLLS consecutive failed server polls (neither stats.all with a stats map nor
                             a players list), no link line for BUS_DEAD_S, xlib's BusDead (a stalled step and no
                             pong; a bus already dead at a server poll, as after a kit phase it ended: x5_combat fix 1's
                             naming), or the client parked in the debugger (xs.check);
             lua_error_storm more than STORM_N lua_error events within STORM_WINDOW_S of the client's own clock
                             (each event's wallMs), so a backlog read at once is no storm;
             memory          MEM_LOW_READS consecutive reads below LIVE_MIN_FREE_GB (None counts as low);
             day_cap         the loop's own wall time reaches DAY_CAP_S (one game day at the 90-minute day);
             budget          xs.check's wall budget (BUDGET_S from the end of the memory gate, the boot included);
             error           anything else the loop raised (its type and message).
THE DEATH RECORD (spec § 10: the frames explain a death): out["loop"]["death"] {via ("frame" | "players"), detail,
wallS, gameMin, frame (the death frame or None), last_decisions (the decision log's last LAST_DECISIONS lines),
last_frames (the last LAST_FRAMES frames' {seq, wallMs, gameMin, worldAge, me, body, load, stats}), server_damage (the
server's records merged into World, with their i and server wall, whose wall (else wallMs) lies within DEATH_WINDOW_S
before the client's clock at the stop), client_damage (World.damage's client records within the same window),
window_ms {from, to}}. A final `damage.watch since` read precedes it, so the records up to the death are merged.

out["loop"]: wallS, ticks, decisions, last_decisions, needs, needs_fields, needs_pairs, fights [{startS, startWall,
gameMin, health, threats, threats_max, nearest, ticks, sent, fight_ticks, flee {reason: n}, end {endS, gameMin,
health, branch} | None}], actions [{aid, type, args, state, reason, sentS, endedS}], lua_errors_per_min, cost {n,
p50, p99, max, tickMaxMs, over5}, server_polls, server_fails, players_error, memory, damage {polls, fails, since,
merged, lost, dropped, counts, totals {tag: {n, amount}}}, first_game_min (the session's first frame's), game_min.
out["frames"] {n, gaps, gap_list, bad, lua_errors, lua_error_msgs, parks}; out["missing"] (the map lines' missing
names). out["grade_d"] is grade_d's report; out["finished"] is set last.

Clocks: a line's wallMs is the client's clock (ms); `*S` keys are this process's clock in seconds since the loop
began; a server read's wallMs is this process's clock in ms, the same host's epoch as the client's wallMs; a damage
record's `wall` is the server's TK.now (getTimestampMs), the same host's epoch.

RULES: never edited after its run (the next pass is a new file); takes no argument; one live session at a time; free
memory gated at MIN_FREE_GB before the boot; never -safemode; launched detached by the controller and polled through
the persisted artifact. Copied, since no frozen driver is a library: parse_argv, memory_gate, clearing_make_client
and count_parks (x4_link / x5_combat), x5_combat's kit, item_added, hello check and players_list (c_survive's), and
c_survive's DecisionTail, server_stats, read_players, Stop and its loop's stops.
"""
import json
import os
import re
import sys
import time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _dlib as DL                                    # noqa: E402
import xlib as X                                      # noqa: E402
from agent.base import gates as GT                    # noqa: E402
from agent.base import pza1                           # noqa: E402
from agent.base.actions import Actions                # noqa: E402
from agent.base.planner.policies import item_id_ok    # noqa: E402
from agent.base.planner.survive import Survive        # noqa: E402
from agent.base.transport.files import FileTransport  # noqa: E402
from agent.base.world import World                    # noqa: E402

KEY = "d_survive"
DRIVER = "d_survive.py"
PROFILE = "testing/profiles/agent.toml"
ARTIFACT = "d_survive.json"
BUDGET_S = 5700.0                    # the brief; c_survive.py L82
USER = "admin"                       # c_survive.py L83
MIN_FREE_GB = 12.0                   # the pre-boot floor; c_survive.py L84
DAY_CAP_S = 5400                     # ruling P22-9; c_survive.py L94
PLANNER_HZ = 2                       # c_survive.py L88
SERVER_POLL_S = 60                   # c_survive.py L89
DAMAGE_POLL_S = 30                   # the brief
PERSIST_S = 30                       # c_survive.py L90
MEM_POLL_S = 300                     # c_survive.py L91
LIVE_MIN_FREE_GB = 0.5               # the in-session floor; c_survive.py L92
STOP_HEALTH = 0.0                    # the brief: a frame's body.health at or below this is a death
MEM_LOW_READS = 2                    # c_survive.py L93
BUS_DEAD_S = 60                      # link silence; c_survive.py L95
BUS_DEAD_POLLS = 2                   # consecutive failed server polls; c_survive.py L96
STORM_N = 10                         # c_survive.py L97
STORM_WINDOW_S = 60                  # c_survive.py L98
HELLO_TIMEOUT_S = 60.0               # c_survive.py L99
FRAME_TIMEOUT_S = 10.0               # c_survive.py L100
KIT = "Base.BaseballBat"             # c_survive.py L103
POLL_S = 0.1                         # c_survive.py L104
DECISION_LOG = "decision.log"        # c_survive.py L105
LAST_DECISIONS = 10                  # c_survive.py L106
KIT_TIMEOUT_S = 30.0                 # x5_combat.py L116
EQUIP_TIMEOUT_S = 30.0               # x5_combat.py L117
ACT_TIMEOUT_S = 10.0                 # Equip's deadline; x5_combat.py L123
SERVER_TIMEOUT_S = 10.0              # the damage.watch step's bus timeout; x5_combat.py L122
LAST_FRAMES = 30                     # the brief: the death record keeps the last 30 frames
DEATH_WINDOW_S = 300                 # the brief: the damage records of the last 5 minutes
PAIR_S = 1.0                         # a needs row's frame and server read share a wall second (CLAUDE.md § 5)
SERVER_RECORDS_KEPT = 2000           # the damage records kept for the death window (10 polls of damage.watch's 200)
REPO = DL.REPO
AGENT_LUA = "testing/PZAgent"
AGENT_BASE = "testing/agent/base"
# a copy of x5_combat.py L131 (a_pipe_3's CLIENT_ERR_RX): a Lua error line in the client console, the -debug park
PARK_RX = r"LuaError|STACK TRACE|attempted index|tried to call nil"
STOPS = ("death", "bus_dead", "lua_error_storm", "memory", "day_cap", "budget", "error")
NEEDS_FIELDS = ["gameMin", "hunger", "thirst", "fatigue", "health", "serverHunger"]
LIMITS = ("PLANNER_HZ", "SERVER_POLL_S", "DAMAGE_POLL_S", "PERSIST_S", "MEM_POLL_S", "LIVE_MIN_FREE_GB",
          "MEM_LOW_READS", "DAY_CAP_S", "BUS_DEAD_S", "BUS_DEAD_POLLS", "STORM_N", "STORM_WINDOW_S")
_ME = os.path.basename(os.path.abspath(__file__))

CONSTANTS = {k: globals()[k] for k in (
    "BUDGET_S", "MIN_FREE_GB", "DAY_CAP_S", "PLANNER_HZ", "SERVER_POLL_S", "DAMAGE_POLL_S", "PERSIST_S", "MEM_POLL_S",
    "LIVE_MIN_FREE_GB", "STOP_HEALTH", "MEM_LOW_READS", "BUS_DEAD_S", "BUS_DEAD_POLLS", "STORM_N", "STORM_WINDOW_S",
    "HELLO_TIMEOUT_S", "FRAME_TIMEOUT_S", "KIT", "POLL_S", "LAST_DECISIONS", "KIT_TIMEOUT_S", "EQUIP_TIMEOUT_S",
    "ACT_TIMEOUT_S", "SERVER_TIMEOUT_S", "LAST_FRAMES", "DEATH_WINDOW_S", "PAIR_S", "SERVER_RECORDS_KEPT",
    "PARK_RX")}
PHASES = ("hello", "kit", "survive")


def parse_argv(argv, driver_file):
    """The driver takes no argument: the refusal text, or None for a bare call (x5_combat's)."""
    if argv:
        return f"{os.path.basename(driver_file)} takes no arguments; a bare call boots the session"
    return None


def new_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
            "loop": {}, "frames": new_frames(), "world_changes": {"left_in_place": []}, "stop": None,
            "finished": False}


def new_frames():
    return {"n": 0, "gaps": 0, "gap_list": [], "bad": 0, "lua_errors": 0, "lua_error_msgs": [], "parks": None}


def driver_checks(driver_file, repo=REPO, git_say=None, git_dirty=None):
    """The driver's own pre-boot checks: its file name, the profile on disk, no committed artifact of its key (a
    driver that ran is frozen), the agent Lua, the agent base and the driver committed clean. Returns (checks, ok)."""
    git_say = git_say or DL.C.git_say
    git_dirty = git_dirty or DL.C.git_dirty
    base = os.path.basename(driver_file)
    c = {"driver_file": base == DRIVER, "driver_prefix": base.startswith(KEY),
         "profile_exists": os.path.isfile(os.path.join(repo, PROFILE))}
    c["no_committed_artifact"] = git_say("ls-files", "--", f"testing/artifacts/{KEY}-*") == ""
    c["agent_lua_dirty"] = git_dirty(AGENT_LUA)[0]
    c["agent_base_dirty"] = git_dirty(AGENT_BASE)[0]
    c["driver_dirty"] = git_dirty(f"testing/agent/drivers/{DRIVER}")[0]
    ok = (c["driver_file"] and c["driver_prefix"] and c["profile_exists"] and c["no_committed_artifact"]
          and c["agent_lua_dirty"] is False and c["agent_base_dirty"] is False and c["driver_dirty"] is False)
    return c, ok


def preboot(driver_file, repo=REPO):
    """_dlib.preboot (git provenance, doctor, harness Lua clean, the layout lint) and the driver's own checks."""
    pre, ok = DL.preboot(driver_file, os.path.join(repo, PROFILE))
    pre["driver_checks"], ok2 = driver_checks(driver_file, repo)
    return pre, bool(ok and ok2)


def memory_gate(xs, wait=None):
    """x5_combat's memory_gate (x4_link's, a_pipe.py's), copied: the memory wait before the boot; a false result
    refuses. The wall budget's clock restarts after it; the readings stay under out["memory_wait"]."""
    ok, readings = (wait or DL.wait_memory)(MIN_FREE_GB)
    xs.out["memory_wait"] = readings
    if not ok:
        xs.refuse("blocked: memory")
    xs.t0 = xs.clock()
    return readings


def clearing_make_client(make):
    """x5_combat's clearing_make_client, copied: pzt.session.make_client, then the stale pzagent/ folder removed before
    the client is started (the fixture snapshot copies the client's Lua/ folder)."""
    def wrapped(*a, **kw):
        c, restored = make(*a, **kw)
        DL.clear_state_dir(c)
        return c, restored
    return wrapped


def count_parks(consoles, admin_parked=False):
    """x5_combat's count_parks, copied: ({user: [PARK_RX lines]}, parks), plus 1 when pzt saw the client park and no
    console line shows it."""
    rx, echo, never = re.compile(PARK_RX), re.compile(r"PZTK: "), re.compile(r"(?!x)x")
    found, n = {}, 0
    for user, path in consoles:
        lines, _ = X.grep_noecho(path, rx, 80, echo, never)
        found[user] = lines
        n += len(lines)
    if n == 0 and admin_parked:
        n = 1
    return found, n


# ================================================================ pure helpers
def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _d(v):
    return v if isinstance(v, dict) else {}


def players_list(reply):
    """c_survive's players_list (x5_combat's copy): the `players` reply as a list of usernames ({} -> [], nobody
    online); None when it is not one (an error string, a dict with an `error` key, a stall)."""
    if isinstance(reply, dict) and ("error" in reply or X.stalled(reply)):
        return None
    if isinstance(reply, list):
        return [str(n) for n in reply]
    if isinstance(reply, dict):
        return [str(reply[k]) for k in sorted(reply, key=str)]
    return None


def server_stats(reply):
    """c_survive's server_stats, copied: stats.all's stats map ({<registry id>: value}); None when the reply carries
    none."""
    if isinstance(reply, dict) and isinstance(reply.get("stats"), dict):
        return reply["stats"]
    return None


def read_players(xs):
    """c_survive's read_players, copied: the server's `players` reply (the step's ack)."""
    return xs.step("players", X.SRV, "players").get("ack")


def item_added(lines, full_type):
    """x5_combat's item_added, copied: the first `item_added` event of `full_type` among `lines`, or None."""
    for l in lines:
        if l.get("kind") == "event" and l.get("event") == "item_added" and l.get("fullType") == full_type:
            return l
    return None


def damage_last(ack):
    """x5_combat's damage_last, copied: a damage.watch reply's `last` records sorted by i ({} -- the empty Lua table --
    and a non-dict read as [])."""
    if not isinstance(ack, dict):
        return []
    last = ack.get("last")
    recs = list(last.values()) if isinstance(last, dict) else list(last) if isinstance(last, list) else []
    recs = [r for r in recs if isinstance(r, dict) and _num(r.get("i")) is not None]
    return sorted(recs, key=lambda r: r["i"])


def frame_row(f):
    """A frame as the death record keeps it: {seq, wallMs, gameMin, worldAge, me, body, load, stats}."""
    return {"seq": f.get("seq"), "wallMs": f.get("wallMs"), "gameMin": f.get("gameMin"), "worldAge": f.get("worldAge"),
            "me": f.get("me"), "body": f.get("body"), "load": f.get("load"), "stats": f.get("stats")}


def body_health(f):
    b = f.get("body") if isinstance(f, dict) else None
    return _num(b.get("health")) if isinstance(b, dict) else None


def pair_frame(frames, server_ms, slack_s=PAIR_S):
    """The frame of `frames` nearest `server_ms` (ties by the earlier seq) and its pair row {frameSeq, frameWallMs,
    serverWallMs, dtMs, paired}: paired when both times are numbers and within slack_s. (None, row) with no frame."""
    row = {"frameSeq": None, "frameWallMs": None, "serverWallMs": server_ms, "dtMs": None, "paired": False}
    if _num(server_ms) is None:
        return (frames[-1] if frames else None), row
    best = None
    for f in frames:
        w = _num(f.get("wallMs"))
        if w is None:
            continue
        k = (abs(w - server_ms), f.get("seq") or 0)
        if best is None or k < best[0]:
            best = (k, f)
    if best is None:
        return None, row
    (dt, _), f = best
    row.update(frameSeq=f.get("seq"), frameWallMs=f.get("wallMs"), dtMs=dt, paired=dt <= slack_s * 1000.0)
    return f, row


def needs_row(f, stats):
    """[gameMin, hunger, thirst, fatigue, health, serverHunger] off a frame and the server's stats map."""
    f = f or {}
    st = _d(f.get("stats"))
    return [f.get("gameMin"), st.get("hunger"), st.get("thirst"), st.get("fatigue"), body_health(f),
            _num(_d(stats).get("Hunger"))]


def in_window(t, lo, hi):
    return _num(t) is not None and lo <= t <= hi


class DecisionTail:
    """c_survive's DecisionTail, copied (c_survive.py L203-L230), with `on_line`: the last `n` lines of the decision
    log, read incrementally (only the bytes appended since the last read); each parsed line also goes to on_line."""

    def __init__(self, path, n=LAST_DECISIONS, on_line=None):
        self.path = path
        self.pos = 0
        self.lines = deque(maxlen=n)
        self.on_line = on_line

    def read(self):
        try:
            with open(self.path, "rb") as fh:
                fh.seek(self.pos)
                data = fh.read()
        except OSError:
            return
        cut = data.rfind(b"\n")
        if cut < 0:
            return
        self.pos += cut + 1
        for raw in data[:cut].split(b"\n"):
            if raw.strip():
                try:
                    line = json.loads(raw.decode("utf-8"))
                except ValueError:
                    line = {"unparsed": raw.decode("utf-8", "replace")}
                self.lines.append(line)
                if self.on_line is not None:
                    self.on_line(line)

    def last(self):
        return list(self.lines)


class Fights:
    """The fights off the decision log: a fight is a run of consecutive lines whose branch is `threat`; it opens at
    the first, counts its ticks, sends, fight ticks and flee reasons (inputs.branches.threat: {fight: true} or
    {flee: reason}), and ends at the first line of another branch. `t0` is the loop's start (the log's clock)."""

    def __init__(self):
        self.rows = []
        self.open = None
        self.t0 = None

    def _s(self, wall):
        return wall - self.t0 if _num(wall) is not None and self.t0 is not None else None

    def feed(self, line):
        inp = _d(line.get("inputs"))
        if line.get("branch") == "threat":
            if self.open is None:
                self.open = {"startS": self._s(line.get("wall")), "startWall": line.get("wall"),
                             "gameMin": line.get("gameMin"), "health": inp.get("health"),
                             "threats": inp.get("threats"), "threats_max": 0, "nearest": inp.get("nearest"),
                             "ticks": 0, "sent": 0,
                             "fight_ticks": 0, "flee": {}, "end": None}
                self.rows.append(self.open)
            f = self.open
            f["ticks"] += 1
            f["sent"] += 1 if line.get("sent") else 0
            why = _d(_d(inp.get("branches")).get("threat"))
            if why.get("fight") is True:
                f["fight_ticks"] += 1
            elif why.get("flee") is not None:
                r = str(why["flee"])
                f["flee"][r] = f["flee"].get(r, 0) + 1
            f["threats_max"] = max(f["threats_max"], _num(inp.get("threats")) or 0)
        elif self.open is not None and "unparsed" not in line:
            self.open["end"] = {"endS": self._s(line.get("wall")), "gameMin": line.get("gameMin"),
                                "health": inp.get("health"), "branch": line.get("branch")}
            self.open = None


class Stop(Exception):
    """c_survive's Stop, copied: a stop condition held, its reason (one of STOPS) and detail."""

    def __init__(self, reason, detail):
        super().__init__("%s: %s" % (reason, detail))
        self.reason, self.detail = reason, detail


# ================================================================ the session
class Day:
    """The hello, kit and survive phases over one FileTransport. clock, sleep, players (the players read), free (the
    memory read) and `limits` (the loop's cadence and caps by constant name, LIMITS; tests) are injectable."""

    def __init__(self, xs, transport, clock=time.time, sleep=time.sleep, players=read_players, free=X.free_gb,
                 limits=None, poll_s=POLL_S):
        self.xs, self.tr, self.clock, self.sleep = xs, transport, clock, sleep
        self.out = xs.out
        self.out.setdefault("frames", new_frames())
        self.loop = self.out.setdefault("loop", {})
        self.rd = self.out.setdefault("readings", {})
        self.players, self.free, self.poll_s = players, free, poll_s
        self.lim = {k: globals()[k] for k in LIMITS}
        self.lim.update(limits or {})
        self.world = World()
        self.actions = Actions(transport, clock=clock)
        run_dir = os.path.dirname(xs.path) if xs.path else os.getcwd()
        self.log_path = os.path.join(run_dir, DECISION_LOG)
        xs.copied.append(DECISION_LOG)
        self.planner = Survive(self.world, self.actions, self.log_path, clock)
        self.fights = Fights()
        self.tail = DecisionTail(self.log_path, on_line=self.fights.feed)
        self.lines = []               # the lines before the loop (hello and kit slice them); the loop keeps none
        self.keep_lines = True
        self.frames = deque(maxlen=LAST_FRAMES)
        self.first_game_min = None
        self.n_frames = 0
        self.client_now = None        # the latest line's client clock (s)
        self.err_times = deque()      # the client clock (s) of each lua_error inside the storm window
        self.err_per_min = {}
        self.ticks_ms, self.tick_max, self.over5 = [], None, 0
        self.missing = []
        self.death_frame = None
        self.t_loop0 = None
        self.last_line_t = None
        self.ready = False
        self.ticks = 0
        self.sent = []                # every Action the planner sent
        self.needs, self.needs_pairs = [], []
        self.server_polls = self.server_fails = self.fails_in_row = 0
        self.players_error = None
        self.mem_rows, self.mem_low_in_row = [], 0
        self.since_i = 0
        self.server_records = deque(maxlen=SERVER_RECORDS_KEPT)
        self.damage = {"polls": 0, "fails": 0, "since": 0, "merged": 0, "lost": 0, "dropped": None, "counts": None,
                       "totals": {}}

    # -- the pump ------------------------------------------------------------------------------------------------
    def loop_s(self):
        return None if self.t_loop0 is None else self.clock() - self.t_loop0

    def pump(self):
        got = self.tr.lines()
        for l in got:
            self.world.apply(l)
            self.on_line(l)
        self.actions.pump(got)
        if got:
            self.last_line_t = self.clock()  # every pump that reads a line, the server poll's included
        if self.keep_lines:
            self.lines.extend(got)
        fr = self.out["frames"]
        fr["gaps"], fr["gap_list"], fr["bad"] = len(self.tr.gaps), [list(g) for g in self.tr.gaps[:50]], self.tr.bad
        return got

    def on_line(self, l):
        fr = self.out["frames"]
        w = _num(l.get("wallMs"))
        if w is not None:
            self.client_now = w / 1000.0 if self.client_now is None else max(self.client_now, w / 1000.0)
        k = l.get("kind")
        if k == "frame":
            self.n_frames += 1
            fr["n"] = self.n_frames
            self.frames.append(frame_row(l))
            if self.first_game_min is None:
                self.first_game_min = l.get("gameMin")
            c = _d(l.get("cost"))
            if _num(c.get("tickMs")) is not None:
                self.ticks_ms.append(c["tickMs"])
            if _num(c.get("tickMaxMs")) is not None:
                self.tick_max = c["tickMaxMs"] if self.tick_max is None else max(self.tick_max, c["tickMaxMs"])
            self.over5 += _num(c.get("over5")) or 0
            h = body_health(l)
            if h is not None and h <= STOP_HEALTH and self.death_frame is None:
                self.death_frame = {"health": h, "seq": l.get("seq"), "wallMs": l.get("wallMs"),
                                    "gameMin": l.get("gameMin")}
        elif k == "event" and l.get("event") == "lua_error":
            fr["lua_errors"] += 1
            fr["lua_error_msgs"] = (fr["lua_error_msgs"] + [l.get("msg")])[-20:]
            s = self.loop_s()
            if s is not None:
                if w is not None:
                    self.err_times.append(w / 1000.0)
                m = str(int(s // 60))
                self.err_per_min[m] = self.err_per_min.get(m, 0) + 1
        elif k == "map":
            for m in l.get("missing") or ():
                if m not in self.missing:
                    self.missing.append(m)

    def wait(self, pred, timeout_s):
        """x5_combat's wait: pump every poll until pred() or timeout_s; True when pred() held. xs.check() guards it."""
        t0 = self.clock()
        while True:
            self.pump()
            if pred():
                return True
            if self.clock() - t0 > timeout_s:
                return False
            self.xs.check()
            self.sleep(self.poll_s)

    # -- phase: hello --------------------------------------------------------------------------------------------
    def phase_hello(self):
        t0 = self.clock()
        r = {"ok": False, "proto": None, "mode": None, "build": None, "hello": None, "first_frame": None,
             "wait_ms": None}
        self.rd["hello"] = r
        self.wait(lambda: self.world.hello is not None, HELLO_TIMEOUT_S)
        r["wait_ms"] = (self.clock() - t0) * 1000.0
        h = self.world.hello
        if h is None:
            raise RuntimeError("no hello line within %s s" % HELLO_TIMEOUT_S)
        r.update(hello=h, proto=h.get("proto"), mode=h.get("mode"), build=h.get("build"))
        if r["proto"] != pza1.PROTO:
            raise RuntimeError("hello proto %r, not %s" % (r["proto"], pza1.PROTO))
        if r["mode"] != "append":
            raise RuntimeError("hello mode %r, not append" % (r["mode"],))
        if not self.wait(lambda: self.n_frames > 0, FRAME_TIMEOUT_S):
            raise RuntimeError("no frame within %s s after the hello" % FRAME_TIMEOUT_S)
        f = next(l for l in self.lines if l.get("kind") == "frame")
        r["first_frame"] = {"seq": f.get("seq"), "wallMs": f.get("wallMs")}
        r["ok"] = True
        self.ready = True

    # -- phase: kit (x5_combat's) --------------------------------------------------------------------------------
    def phase_kit(self):
        r = {"spawn": None, "item": None, "equip": None, "weapon_frame": None, "armed": False, "ok": False}
        self.rd["kit"] = r
        i0 = len(self.lines)
        r["spawn"] = self.xs.spawn(KIT, 1, "kit")
        self.wait(lambda: item_added(self.lines[i0:], KIT) is not None, KIT_TIMEOUT_S)
        ev = item_added(self.lines[i0:], KIT)
        if ev is not None:
            r["item"] = {"itemId": ev.get("itemId"), "source": "item_added", "seq": ev.get("seq"),
                         "wallMs": ev.get("wallMs")}
        else:
            held = sorted(i for i, it in self.world.inventory.items() if it.get("fullType") == KIT and item_id_ok(i))
            if held:
                r["item"] = {"itemId": held[0], "source": "inventory", "seq": None, "wallMs": None}
            self.xs.note("kit: no item_added of %s within %s s%s" % (KIT, KIT_TIMEOUT_S,
                                                                    "; the inventory's kept" if held else ""))
        iid = (r["item"] or {}).get("itemId")
        if not item_id_ok(iid):
            self.xs.note("kit: no %s item id to equip; the planner flees every threat unarmed" % KIT)
            return
        i1 = len(self.lines)
        a = self.actions.send(pza1.Equip(iid), deadline_s=ACT_TIMEOUT_S)
        self.wait(lambda: self.actions.done(a), ACT_TIMEOUT_S + 1.0)
        r["equip"] = {"aid": a.aid, "state": a.state, "reason": a.reason, "result": a.result,
                      "ended_wall": a.ended_wall}

        def wield():
            return next((f for f in self.lines[i1:] if f.get("kind") == "frame"
                         and (f.get("weapon") or {}).get("type") == KIT), None)
        self.wait(lambda: wield() is not None, EQUIP_TIMEOUT_S)
        f = wield()
        r["weapon_frame"] = {"seq": f["seq"], "wallMs": f.get("wallMs"), "type": KIT} if f else None
        r["armed"] = f is not None
        r["ok"] = bool((r["spawn"] or {}).get("confirmed")) and a.state == "done" and f is not None
        if f is None:
            self.xs.note("kit: no frame shows %s in the primary hand after %s s" % (KIT, EQUIP_TIMEOUT_S))

    # -- phase: survive ------------------------------------------------------------------------------------------
    def phase_survive(self):
        if not self.ready:
            raise RuntimeError("the hello phase did not pass: no loop on this link")
        self.keep_lines = False
        self.lines = []
        now = self.clock()
        self.t_loop0 = now
        self.fights.t0 = now
        self.loop["startPyMs"] = now * 1000.0
        self.last_line_t = now
        lim = self.lim
        tick_dt = 1.0 / lim["PLANNER_HZ"]
        next_tick, next_server, next_damage = now, now, now
        next_persist, next_mem = now + lim["PERSIST_S"], now + lim["MEM_POLL_S"]
        try:
            while True:
                now = self.clock()
                self.pump()
                self.check_lines(now)
                if now >= next_server:
                    next_server = now + lim["SERVER_POLL_S"]
                    self.server_poll(now)
                if now >= next_damage:
                    next_damage = now + lim["DAMAGE_POLL_S"]
                    self.damage_poll()
                if now >= next_mem:
                    next_mem = now + lim["MEM_POLL_S"]
                    self.memory_read(now)
                if now - self.t_loop0 >= lim["DAY_CAP_S"]:
                    raise Stop("day_cap", "the loop reached %ss of wall time" % lim["DAY_CAP_S"])
                self.check_budget()
                if now >= next_tick:
                    next_tick = next_tick + tick_dt if next_tick + tick_dt > now else now + tick_dt
                    self.planner_tick()
                if now >= next_persist:
                    next_persist = now + lim["PERSIST_S"]
                    self.save()
                self.sleep(self.poll_s)
        except Stop as s:
            self.set_stop(s.reason, s.detail)
        except X.BusDead as e:
            self.set_stop("bus_dead", "xlib BusDead: %s" % e)
        except Exception as e:                       # noqa: BLE001 - the loop's own fault ends it, named
            self.set_stop("error", "%s: %s" % (type(e).__name__, e))
            raise
        finally:
            self.save()

    def check_budget(self):
        try:
            self.xs.check()
        except X.Budget as e:
            raise Stop("bus_dead" if "parked" in str(e) else "budget", str(e))

    def check_lines(self, now):
        """The stops read off the link: a death frame, a lua_error storm, a silent link."""
        if self.death_frame is not None:
            raise Stop("death", "frame seq %s body.health %s" % (self.death_frame["seq"], self.death_frame["health"]))
        if self.client_now is not None:
            while self.err_times and self.err_times[0] < self.client_now - self.lim["STORM_WINDOW_S"]:
                self.err_times.popleft()
        if len(self.err_times) > self.lim["STORM_N"]:
            raise Stop("lua_error_storm", "%d lua_error events within %ss" % (len(self.err_times),
                                                                               self.lim["STORM_WINDOW_S"]))
        if now - self.last_line_t >= self.lim["BUS_DEAD_S"]:
            raise Stop("bus_dead", "no link line for %ss (the client parked or gone)" % self.lim["BUS_DEAD_S"])

    def server_poll(self, now):
        """stats.all merged into the World, a pump, one needs row paired by wall time, the players list; a death or a
        dead bus raises Stop."""
        if self.xs.bus_dead:
            raise Stop("bus_dead", "server bus dead after %s" % self.xs.bus_dead)
        self.server_polls += 1
        r = DL.bus_stats(self.xs, USER) or {}
        stats = server_stats(r.get("ack"))
        if stats is not None:
            self.world.merge_server(stats, r.get("wallMs"))
        self.pump()
        f, pair = pair_frame(list(self.frames), r.get("wallMs"))
        self.needs.append(needs_row(f, stats))
        self.needs_pairs.append(pair)
        reply = self.players(self.xs)
        names = players_list(reply)
        if names is None:
            self.players_error = {"wallS": now - self.t_loop0, "reply": str(reply)[:300]}
        if stats is not None or names is not None:
            self.fails_in_row = 0
        else:
            self.server_fails += 1
            self.fails_in_row += 1
        if names is not None and USER not in names:
            raise Stop("death", "players reply without %s: %s" % (USER, names))
        if self.fails_in_row >= self.lim["BUS_DEAD_POLLS"]:
            raise Stop("bus_dead", "%d consecutive failed server polls, %ss apart" % (
                self.fails_in_row, self.lim["SERVER_POLL_S"]))

    def damage_poll(self):
        """damage.watch USER since <i>: the new records merged into the World, kept with their i and server wall, and
        summed by tag; a gap in the indices (records aged out of the server's list) counts in `lost`."""
        dm = self.damage
        dm["polls"] += 1
        ack = self.xs.step("damage_watch", X.SRV, "damage.watch", "%s since %d" % (USER, self.since_i),
                           timeout=SERVER_TIMEOUT_S, log=False).get("ack")
        if not (isinstance(ack, dict) and ack.get("ok") is True):
            dm["fails"] += 1
            dm["last_error"] = str(ack)[:300]
            return
        merge_ms = self.clock() * 1000.0
        seen = set(self.world.damage_seen_i)
        new = [r for r in damage_last(ack) if r["i"] not in seen]
        self.world.merge_damage(ack, merge_ms)
        for r in new:
            if r["i"] > self.since_i + 1:
                dm["lost"] += int(r["i"] - self.since_i - 1)
            self.since_i = max(self.since_i, r["i"])
            tag = str(r.get("tag"))
            self.server_records.append({"i": r["i"], "tag": tag, "amount": r.get("amount"), "wall": r.get("wall"),
                                        "wallMs": merge_ms})
            t = dm["totals"].setdefault(tag, {"n": 0, "amount": 0.0})
            t["n"] += 1
            t["amount"] += _num(r.get("amount")) or 0.0
        dm["merged"] += len(new)
        dm["since"], dm["dropped"], dm["counts"] = self.since_i, ack.get("dropped"), ack.get("counts")

    def memory_read(self, now):
        """c_survive's memory_read: one free-memory read; MEM_LOW_READS in a row below LIVE_MIN_FREE_GB stop."""
        g = self.free()
        self.mem_rows.append({"wallS": now - self.t_loop0, "free_gb": g})
        self.out["memory_reads"] = list(self.mem_rows)
        if X.memory_ok(g, self.lim["LIVE_MIN_FREE_GB"]):
            self.mem_low_in_row = 0
            return
        self.mem_low_in_row += 1
        if self.mem_low_in_row >= self.lim["MEM_LOW_READS"]:
            raise Stop("memory", "%d consecutive reads below %s GB, the last %s GB" % (
                self.mem_low_in_row, self.lim["LIVE_MIN_FREE_GB"], g))

    def planner_tick(self):
        a = self.planner.tick(self.world, self.actions)
        self.ticks += 1
        self.tail.read()
        if a is not None:
            self.sent.append(a)

    # -- the record ----------------------------------------------------------------------------------------------
    def action_rows(self):
        t0 = self.t_loop0 or 0.0
        return [{"aid": a.aid, "type": a.type, "args": dict(a.args), "state": a.state, "reason": a.reason,
                 "sentS": a.sent_wall - t0, "endedS": a.ended_wall - t0 if a.ended_wall is not None else None}
                for a in self.sent]

    def save(self):
        """out["loop"] rebuilt, persist."""
        ts = self.ticks_ms
        self.loop.update({
            "wallS": self.loop_s(), "ticks": self.ticks, "decisions": len(self.sent),
            "last_decisions": self.tail.last(), "needs": list(self.needs), "needs_fields": list(NEEDS_FIELDS),
            "needs_pairs": list(self.needs_pairs), "fights": [dict(f) for f in self.fights.rows],
            "actions": self.action_rows(), "lua_errors_per_min": dict(self.err_per_min),
            "cost": {"n": len(ts), "p50": GT.pct(ts, 50), "p99": GT.pct(ts, 99), "max": max(ts) if ts else None,
                     "tickMaxMs": self.tick_max, "over5": self.over5},
            "server_polls": self.server_polls, "server_fails": self.server_fails,
            "players_error": self.players_error, "memory": list(self.mem_rows),
            "damage": dict(self.damage, totals={k: dict(v) for k, v in self.damage["totals"].items()}),
            "first_game_min": self.first_game_min, "game_min": self.world.game_min})
        self.out["missing"] = list(self.missing)
        self.xs.persist()

    def death_record(self, via, detail):
        """The death record (the module docstring), after a last damage.watch read (guarded: a dead bus keeps what was
        merged)."""
        try:
            self.damage_poll()
        except Exception as e:                       # noqa: BLE001 - the record is written whatever the bus does
            self.damage["final_error"] = "%s: %s" % (type(e).__name__, e)
        self.tail.read()
        hi = (self.client_now if self.client_now is not None else self.clock()) * 1000.0
        lo = hi - DEATH_WINDOW_S * 1000.0
        server = [dict(r) for r in self.server_records
                  if in_window(r["wall"] if _num(r.get("wall")) is not None else r["wallMs"], lo, hi)]
        client = [dict(r) for r in self.world.damage
                  if r.get("side") != "server" and in_window(r.get("wallMs"), lo, hi)]
        return {"via": via, "detail": detail, "wallS": self.loop_s(), "gameMin": self.world.game_min,
                "frame": self.death_frame, "last_decisions": self.tail.last(), "last_frames": list(self.frames),
                "server_damage": server, "client_damage": client, "window_ms": {"from": lo, "to": hi}}

    def set_stop(self, reason, detail):
        """The session's first stop, named in out["stop"]; a death also writes out["loop"]["death"]."""
        if self.out.get("stop") is not None:
            return
        self.out["stop"] = {"reason": reason, "detail": detail, "wallS": self.loop_s(), "gameMin": self.world.game_min,
                            "worldAge": (self.frames[-1] if self.frames else {}).get("worldAge")}
        if reason == "death":
            self.loop["death"] = self.death_record("frame" if self.death_frame is not None else "players", detail)
        self.xs.note("stop %s: %s" % (reason, detail))

    def run(self):
        self.xs.run_phase("hello", self.phase_hello)
        if self.ready:
            self.xs.run_phase("kit", self.phase_kit)
            self.xs.run_phase("survive", self.phase_survive)
        else:
            self.xs.note("no hello: the kit and the loop skipped")
        if self.out.get("stop") is None:
            # the loop never began (an earlier phase's fault or the budget): named all the same (c_survive's run)
            # (only a failed hello reaches here: a kit phase ended on xlib's BusDead still runs the loop, whose first
            # server poll names bus_dead, x5_combat fix 1's naming)
            bs = self.out.get("budget_stop")
            pe = self.out.get("phase_errors", {})
            reason, detail = ("budget", bs.get("why")) if bs else ("error", "; ".join(
                "%s: %s" % (k, v.get("error")) for k, v in pe.items()) or "the loop did not run")
            self.set_stop(reason, detail)
        self.xs.persist()


# ================================================================ the boot
def main(budget_s=BUDGET_S):
    from _common import ask, hard_kill                       # noqa: E402
    import x49b_lib as B                                     # noqa: E402
    from pzt import fixture as fx, profile, session          # noqa: E402
    from pzt.bus import resolve_side                         # noqa: E402
    from pzt.paths import new_run_dir                        # noqa: E402

    pre, ok = preboot(_ME)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    prof = profile.load(os.path.join(REPO, PROFILE))
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(KEY)
    tl = session.Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = new_out()
    out["world_changes"]["restored"] = f"fixture {prof.fixture} restored into the run dir"
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, user=USER)
    xs.path = os.path.join(run_dir, ARTIFACT)
    out.update({"run_id": run_id, "session_key": KEY, "driver": _ME, "user": USER, "profile": prof.report(),
                "preboot": pre, "argv": sys.argv[1:], "constants": CONSTANTS,
                "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                            "build": rec_fx.get("build")},
                "driver_commit": DL.C.git_say("log", "-1", "--format=%h", "--", f"testing/agent/drivers/{DRIVER}")})
    memory_gate(xs)
    xs.mem("preboot")
    xs.persist()
    try:
        out.update(DL.boot(xs, prof, rec_fx, run_dir, [USER], started, clients, holder,
                           make_client=clearing_make_client(session.make_client)))
        xs.mem("ready")
        xs.persist()
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            out["state_dir"] = DL.state_dir(clients[USER])
            Day(xs, FileTransport(DL.state_dir(clients[USER]))).run()
    except Exception as e:                                   # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            found, n = count_parks([(getattr(c, "username", "?"), c.console) for c in every], xs.parked())
            out["logs"] = {"patterns": {"park": PARK_RX}, "clients": found}
            out["frames"]["parks"] = n

        xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs)
        xs.mem("after")
        try:
            out["grade_d"] = GT.grade_d(out)
        except Exception as e:                               # noqa: BLE001 - the controller re-grades the artifact
            out["grade_d_error"] = f"{type(e).__name__}: {e}"
        out["finished"] = True
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)
    print(json.dumps({"run_id": run_id, "run_dir": run_dir, "error": out.get("error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "budget_stop": out.get("budget_stop"), "stop": out.get("stop"),
                      "report": (out.get("grade_d") or {}).get("report_lines"),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str))
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main()
