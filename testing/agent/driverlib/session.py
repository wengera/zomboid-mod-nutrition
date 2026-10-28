"""One live session of the agent base: a driver's boot seams and `Session`, the phases over one FileTransport.

A driver (testing/agent/drivers/<key>.py) owns its constants, its profile, its boot (`_dlib.boot`) and its grade; it
builds `Session(xs, FileTransport(state_dir), planner_factory, ...)` and calls `run()`. The cadences and caps are
`DEFAULTS` with the driver's `limits` laid over them (`session.lim`), so a driver changes a cadence by argument.

PHASES (each through xs.run_phase; a phase's fault lands under out["phase_errors"][name]; each reading at
out["readings"][phase]):
  hello        pump until the hello line (HELLO_TIMEOUT_S); its proto must be pza1.PROTO and its mode "append"; then
               until the first frame (FRAME_TIMEOUT_S). {ok, proto, mode, build, hello, first_frame {seq, wallMs},
               wait_ms}. A failed hello skips the rest (stop `error`, or `bus_dead` for a park).
  damage_hook  the server's damage listener installed before the kit (`damage.watch USER` once), its records merged as
               the loop merges them; {ok, hooked, n, counts, last_i, ack}.
  kit          KIT x1 through xs.spawn (RCON additem confirmed by item.get); pump until an `item_added` of KIT
               (KIT_TIMEOUT_S; else the first KIT the inventory holds, source "inventory"); Equip(itemId) awaited to a
               terminal state (ACT_TIMEOUT_S); pump until a frame's weapon.type is KIT (EQUIP_TIMEOUT_S). {spawn, item,
               equip, weapon_frame, armed, ok}. An unconfirmed spawn or equip is recorded and the session goes on.
  loop         every poll_s of the clock: pump the transport (each line into World, then Actions; a frame's
               body.health <= STOP_HEALTH, the lua_error events and the link's silence are read here); at
               PLANNER_HZ the planner's tick (its decision log read incrementally, the fights built off its threat
               branch); the server reads (below); every MEM_POLL_S a host free-memory read; every PERSIST_S out["loop"]
               rebuilt (record.loop_summary and the driver's extra_record()) and persisted.
THE SERVER READS: synchronously, as the first Plan 22 acceptance driver read them, every SERVER_POLL_S (the first at
the loop's start) stats.all merged into the World, a pump, one needs row [gameMin, hunger, thirst, fatigue, health,
serverHunger] off the frame nearest the read's wallMs with its pair row {frameSeq, frameWallMs, serverWallMs, dtMs,
paired (within PAIR_S)}, then the `players` list; every DAMAGE_POLL_S `damage.watch USER since <i>`, its new records
merged, kept (the last SERVER_RECORDS_KEPT) and summed by tag. With `polls` (a polls.PollThread) the same three reads
are scheduled at the loop's start on the worker and the loop merges, at every pass, each result newer than the last it
merged (so a slow bus never holds the loop): a stats result and a players result make one server poll; a read that
raised on the worker counts as that half failed.
THE WORKER AND THE MAIN THREAD: the worker's reads run through xs.step, which appends rows to out["steps"] and, on a
stall, adds a ping row and (xs.mark_dead) out["abort"], a note and a timeline mark, all while the loop's xs.persist may
be serialising out. A list append mid-dump is harmless; a key added mid-dump (the stall and dead-bus path only) makes
that one persist raise "dictionary changed size", which Xs.persist catches, its tmp-and-replace write keeping the last
artifact whole: at most one PERSIST_S of staleness, never a corrupt file. A later change that adds worker-side writes
keeps to that rule or moves the write to the merge. The bus itself (pzt's CommandBus: one seq, one command file) takes
one caller at a time, so the loop's end joins the worker with a timeout covering the longest read (the step's 30 s
bus timeout plus the liveness ping: Session.polls_join_s), records loop.polls_joined, and skips the death record's
final damage read while the worker is still in a read (damage.final_error names it).
STOP CONDITIONS, the first that holds ends the loop, named in out["stop"] {reason, detail, wallS, gameMin, worldAge}:
  death            a frame's body.health <= STOP_HEALTH, or a `players` reply (a list, or {} for nobody) without the
                   user (an error reply is no death: a failed read, the last kept as loop.players_error);
  bus_dead         BUS_DEAD_POLLS consecutive failed server polls (neither a stats map nor a players list), no link
                   line for BUS_DEAD_S, xlib's BusDead or a bus already dead, or the client parked in the debugger;
  lua_error_storm  more than STORM_N lua_error events within STORM_WINDOW_S of the client's own clock;
  memory           MEM_LOW_READS consecutive reads below LIVE_MIN_FREE_GB (None counts as low);
  day_cap          the loop's own wall time reaches DAY_CAP_S;
  budget           xs.check's wall budget;
  error            anything else the loop raised.
A death writes out["loop"]["death"] (record.death_record). A stop before the loop ran leaves loop.started absent.

Two hooks a driver may override: `on_frame(line)` (every frame line, after the World has it) and `extra_record()`
(a dict merged into out["loop"] at every save).
"""
import json
import os
import re
import sys
import time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.dirname(HERE)
TESTING = os.path.dirname(AGENT)
for _p in (os.path.join(AGENT, "drivers"), os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _dlib as DL                                    # noqa: E402
import xlib as X                                      # noqa: E402
from agent.base import pza1                           # noqa: E402
from agent.base.actions import Actions                # noqa: E402
from agent.base.planner.policies import item_id_ok    # noqa: E402
from agent.base.planner.survive import Survive        # noqa: E402
from agent.base.world import World                    # noqa: E402

REPO = DL.REPO
DEFAULTS = {
    "BUDGET_S": 1200.0,           # the wall budget from the end of the memory gate, the boot included
    "MIN_FREE_GB": 12.0,          # the pre-boot memory floor (CLAUDE.md § 5)
    "DAY_CAP_S": 840,             # the loop's own wall time
    "PLANNER_HZ": 2,
    "SERVER_POLL_S": 60,          # stats.all and players
    "DAMAGE_POLL_S": 5,           # damage.watch since
    "PERSIST_S": 30,
    "MEM_POLL_S": 300,
    "LIVE_MIN_FREE_GB": 0.5,      # the in-session memory floor
    "STOP_HEALTH": 0.0,           # a frame's body.health at or below this is a death
    "MEM_LOW_READS": 2,
    "BUS_DEAD_S": 60,             # link silence
    "BUS_DEAD_POLLS": 2,          # consecutive failed server polls
    "STORM_N": 10,
    "STORM_WINDOW_S": 60,
    "HELLO_TIMEOUT_S": 60.0,
    "FRAME_TIMEOUT_S": 10.0,
    "KIT": "Base.BaseballBat",
    "POLL_S": 0.1,                # the loop's pass
    "LAST_DECISIONS": 10,
    "KIT_TIMEOUT_S": 30.0,
    "EQUIP_TIMEOUT_S": 30.0,
    "ACT_TIMEOUT_S": 10.0,        # Equip's deadline
    "SERVER_TIMEOUT_S": 10.0,     # the damage.watch step's bus timeout
    "LAST_FRAMES": 300,           # 30 s at 10 Hz: a wound's onset
    "DEATH_WINDOW_S": 300,        # the damage records a death record keeps
    "PAIR_S": 1.0,                # a needs row's frame and server read share a wall second (CLAUDE.md § 5)
    "SERVER_RECORDS_KEPT": 5000,
    # a Lua error line in the client console, the -debug park
    "PARK_RX": r"LuaError|STACK TRACE|attempted index|tried to call nil",
}
DECISION_LOG = "decision.log"
STEP_TIMEOUT_S = 30.0         # xlib.Xs.step's default bus timeout: the stats and players reads'
NEEDS_FIELDS = ["gameMin", "hunger", "thirst", "fatigue", "health", "serverHunger"]
AGENT_LUA = "testing/PZAgent"
AGENT_BASE = "testing/agent/base"
DRIVERLIB = "testing/agent/driverlib"
STOPS = ("death", "bus_dead", "lua_error_storm", "memory", "day_cap", "budget", "error")
PHASES = ("hello", "damage_hook", "kit", "loop")


# ================================================================ arguments and the boot's seams
def parse_flags(argv, allowed=()):
    """{flag: value} for argv made only of `allowed` flags, each once with one value; None when it is not."""
    got, i = {}, 0
    argv = list(argv)
    while i < len(argv):
        flag = argv[i]
        if flag not in allowed or flag in got or i + 1 >= len(argv) or argv[i + 1].startswith("--"):
            return None
        got[flag] = argv[i + 1]
        i += 2
    return got


def parse_argv(argv, driver_file, allowed=()):
    """The one-line refusal for any argument not in `allowed` (each allowed flag takes exactly one value; --help, a
    positional, a repeated or bare flag are refused), else None."""
    if parse_flags(argv, allowed) is not None:
        return None
    me = os.path.basename(driver_file)
    if not allowed:
        return "%s takes no arguments; a bare call boots the session" % me
    return "%s takes only %s; refused: %s" % (me, ", ".join("%s <value>" % a for a in allowed), " ".join(argv))


def new_frames():
    return {"n": 0, "gaps": 0, "gap_list": [], "bad": 0, "lua_errors": 0, "lua_error_msgs": [], "parks": None}


def new_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
            "loop": {}, "frames": new_frames(), "world_changes": {"left_in_place": []}, "stop": None,
            "finished": False}


def driver_checks(driver_file, key, driver, profile, repo=REPO, git_say=None, git_dirty=None):
    """The driver's own pre-boot checks: its file name and key prefix, the profile on disk, no committed artifact of its
    key (a driver that ran is frozen), and the agent Lua, the agent base, this library and the driver committed clean
    (the artifact's commit then recovers the code that ran). Returns (checks, ok)."""
    git_say = git_say or DL.C.git_say
    git_dirty = git_dirty or DL.C.git_dirty
    base = os.path.basename(driver_file)
    c = {"driver_file": base == driver, "driver_prefix": base.startswith(key),
         "profile_exists": os.path.isfile(os.path.join(repo, profile))}
    c["no_committed_artifact"] = git_say("ls-files", "--", "testing/artifacts/%s-*" % key) == ""
    c["agent_lua_dirty"] = git_dirty(AGENT_LUA)[0]
    c["agent_base_dirty"] = git_dirty(AGENT_BASE)[0]
    c["driverlib_dirty"] = git_dirty(DRIVERLIB)[0]
    c["driver_dirty"] = git_dirty("testing/agent/drivers/%s" % driver)[0]
    ok = (c["driver_file"] and c["driver_prefix"] and c["profile_exists"] and c["no_committed_artifact"]
          and c["agent_lua_dirty"] is False and c["agent_base_dirty"] is False and c["driverlib_dirty"] is False
          and c["driver_dirty"] is False)
    return c, ok


def preboot(driver_file, key, driver, profile, repo=REPO):
    """_dlib.preboot (git provenance, doctor, harness Lua clean, the layout lint), the library's commit and the
    driver's own checks."""
    pre, ok = DL.preboot(driver_file, os.path.join(repo, profile))
    pre["driverlib_commit"] = DL.C.git_say("log", "-1", "--format=%h", "--", DRIVERLIB)
    pre["driver_checks"], ok2 = driver_checks(driver_file, key, driver, profile, repo)
    return pre, bool(ok and ok2)


def memory_gate(xs, min_gb, wait=None):
    """The memory wait before the boot; a false result refuses. The wall budget's clock restarts after it; the
    readings stay under out["memory_wait"]."""
    ok, readings = (wait or DL.wait_memory)(min_gb)
    xs.out["memory_wait"] = readings
    if not ok:
        xs.refuse("blocked: memory")
    xs.t0 = xs.clock()
    return readings


def clearing_make_client(make):
    """pzt.session.make_client, then the stale pzagent/ folder removed before the client is started (the fixture
    snapshot copies the client's Lua/ folder)."""
    def wrapped(*a, **kw):
        c, restored = make(*a, **kw)
        DL.clear_state_dir(c)
        return c, restored
    return wrapped


def count_parks(consoles, admin_parked=False, park_rx=DEFAULTS["PARK_RX"]):
    """({user: [park_rx lines]}, parks) over [(user, console path)], plus 1 when pzt saw the client park and no
    console line shows it."""
    rx, echo, never = re.compile(park_rx), re.compile(r"PZTK: "), re.compile(r"(?!x)x")
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


def in_window(t, lo, hi):
    return _num(t) is not None and lo <= t <= hi


def players_list(reply):
    """The `players` reply as a list of usernames ({} -> [], nobody online); None when it is not one (an error string,
    a dict with an `error` key, a stall)."""
    if isinstance(reply, dict) and ("error" in reply or X.stalled(reply)):
        return None
    if isinstance(reply, list):
        return [str(n) for n in reply]
    if isinstance(reply, dict):
        return [str(reply[k]) for k in sorted(reply, key=str)]
    return None


def server_stats(reply):
    """stats.all's stats map ({<registry id>: value}); None when the reply carries none."""
    if isinstance(reply, dict) and isinstance(reply.get("stats"), dict):
        return reply["stats"]
    return None


def read_players(xs):
    """The server's `players` reply (the step's ack)."""
    return xs.step("players", X.SRV, "players").get("ack")


def item_added(lines, full_type):
    """The first `item_added` event of `full_type` among `lines`, or None."""
    for l in lines:
        if l.get("kind") == "event" and l.get("event") == "item_added" and l.get("fullType") == full_type:
            return l
    return None


def damage_last(ack):
    """A damage.watch reply's `last` records sorted by i ({} -- the empty Lua table -- and a non-dict read as [])."""
    if not isinstance(ack, dict):
        return []
    last = ack.get("last")
    recs = list(last.values()) if isinstance(last, dict) else list(last) if isinstance(last, list) else []
    recs = [r for r in recs if isinstance(r, dict) and _num(r.get("i")) is not None]
    return sorted(recs, key=lambda r: r["i"])


def frame_row(f):
    """A frame as the record keeps it: {seq, wallMs, gameMin, worldAge, me, body, load, stats, zombies [{id, dist}]}."""
    return {"seq": f.get("seq"), "wallMs": f.get("wallMs"), "gameMin": f.get("gameMin"), "worldAge": f.get("worldAge"),
            "me": f.get("me"), "body": f.get("body"), "load": f.get("load"), "stats": f.get("stats"),
            "zombies": [{"id": z.get("id"), "dist": z.get("dist")} for z in f.get("zombies") or ()
                        if isinstance(z, dict)]}


def body_health(f):
    b = f.get("body") if isinstance(f, dict) else None
    return _num(b.get("health")) if isinstance(b, dict) else None


def pair_frame(frames, server_ms, slack_s=DEFAULTS["PAIR_S"]):
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


class DecisionTail:
    """The last `n` lines of the decision log, read incrementally (only the bytes appended since the last read); each
    parsed line also goes to on_line."""

    def __init__(self, path, n=DEFAULTS["LAST_DECISIONS"], on_line=None):
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
                             "ticks": 0, "sent": 0, "fight_ticks": 0, "flee": {}, "end": None}
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
    """A stop condition held: its reason (one of STOPS) and detail."""

    def __init__(self, reason, detail):
        super().__init__("%s: %s" % (reason, detail))
        self.reason, self.detail = reason, detail


# ================================================================ the session
class Session:
    """The hello, damage-hook, kit and loop phases over one FileTransport (the module docstring). `planner_factory
    (world, actions, log_path, clock)` makes the planner once; clock, sleep, players (the players read), free (the
    memory read), limits (laid over DEFAULTS), poll_s (default POLL_S), polls (a PollThread) and polls_join_s (the
    worker's join at the loop's end; default the longest read) are injectable."""

    def __init__(self, xs, transport, planner_factory=Survive, clock=time.time, sleep=time.sleep,
                 players=read_players, free=X.free_gb, limits=None, poll_s=None, polls=None, polls_join_s=None):
        self.xs, self.tr, self.clock, self.sleep = xs, transport, clock, sleep
        self.user = xs.user
        self.out = xs.out
        self.out.setdefault("frames", new_frames())
        self.loop = self.out.setdefault("loop", {})
        self.rd = self.out.setdefault("readings", {})
        self.lim = dict(DEFAULTS)
        self.lim.update(limits or {})
        self.players, self.free = players, free
        self.poll_s = self.lim["POLL_S"] if poll_s is None else poll_s
        self.polls = polls
        # the join at the loop's end covers the longest read: a bus step's timeout and its liveness ping
        self.polls_join_s = polls_join_s if polls_join_s is not None else (
            max(STEP_TIMEOUT_S, self.lim["SERVER_TIMEOUT_S"]) + getattr(xs, "ping_timeout_s", 5))
        self.world = World()
        self.actions = Actions(transport, clock=clock)
        run_dir = os.path.dirname(xs.path) if xs.path else os.getcwd()
        self.log_path = os.path.join(run_dir, DECISION_LOG)
        xs.copied.append(DECISION_LOG)
        self.planner = planner_factory(self.world, self.actions, self.log_path, clock)
        self.fights = Fights()
        self.tail = DecisionTail(self.log_path, n=self.lim["LAST_DECISIONS"], on_line=self.fights.feed)
        self.lines = []               # the lines before the loop (hello and kit slice them); the loop keeps none
        self.keep_lines = True
        self.frames = deque(maxlen=self.lim["LAST_FRAMES"])
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
        self.since_i = 0              # the largest damage record index merged; the poll worker reads it at each call
        self.server_records = deque(maxlen=self.lim["SERVER_RECORDS_KEPT"])
        self.damage = {"polls": 0, "fails": 0, "since": 0, "merged": 0, "lost": 0, "dropped": None, "counts": None,
                       "totals": {}}
        self._seen = {}               # polls: the (result, wall) tuple last merged, by read name
        self._round = {}              # polls: the current server poll's halves, {"stats"|"players": ok}
        self._err_i = 0               # polls: the errors already counted

    # -- the hooks -----------------------------------------------------------------------------------------------
    def on_frame(self, line):
        """Every frame line, after the World and the record have it; nothing by default."""

    def extra_record(self):
        """A dict merged into out["loop"] at every save; none by default."""
        return {}

    # -- the pump ------------------------------------------------------------------------------------------------
    def loop_s(self):
        return None if self.t_loop0 is None else self.clock() - self.t_loop0

    def pump(self):
        got = self.tr.lines()
        for l in got:
            self.world.apply(l)
            self.read_line(l)
        self.actions.pump(got)
        if got:
            self.last_line_t = self.clock()
        if self.keep_lines:
            self.lines.extend(got)
        fr = self.out["frames"]
        fr["gaps"], fr["gap_list"], fr["bad"] = len(self.tr.gaps), [list(g) for g in self.tr.gaps[:50]], self.tr.bad
        return got

    def read_line(self, l):
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
            if h is not None and h <= self.lim["STOP_HEALTH"] and self.death_frame is None:
                self.death_frame = {"health": h, "seq": l.get("seq"), "wallMs": l.get("wallMs"),
                                    "gameMin": l.get("gameMin")}
            self.on_frame(l)
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
        """Pump every poll until pred() or timeout_s; True when pred() held. xs.check() guards it."""
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
        hello_s, frame_s = self.lim["HELLO_TIMEOUT_S"], self.lim["FRAME_TIMEOUT_S"]
        self.wait(lambda: self.world.hello is not None, hello_s)
        r["wait_ms"] = (self.clock() - t0) * 1000.0
        h = self.world.hello
        if h is None:
            raise RuntimeError("no hello line within %s s" % hello_s)
        r.update(hello=h, proto=h.get("proto"), mode=h.get("mode"), build=h.get("build"))
        if r["proto"] != pza1.PROTO:
            raise RuntimeError("hello proto %r, not %s" % (r["proto"], pza1.PROTO))
        if r["mode"] != "append":
            raise RuntimeError("hello mode %r, not append" % (r["mode"],))
        if not self.wait(lambda: self.n_frames > 0, frame_s):
            raise RuntimeError("no frame within %s s after the hello" % frame_s)
        f = next(l for l in self.lines if l.get("kind") == "frame")
        r["first_frame"] = {"seq": f.get("seq"), "wallMs": f.get("wallMs")}
        r["ok"] = True
        self.ready = True

    # -- phase: damage_hook --------------------------------------------------------------------------------------
    def phase_damage_hook(self):
        """The server's damage listener installed before the kit (`damage.watch USER` once), its records merged as the
        loop merges them; {ok, hooked, n, counts, last_i, ack}."""
        ack = self.damage_poll(args=self.user)
        a = ack if isinstance(ack, dict) else {}
        self.rd["damage_hook"] = {"ok": a.get("ok"), "hooked": a.get("hooked"), "n": a.get("n"),
                                  "counts": a.get("counts"), "last_i": self.since_i, "ack": ack}

    # -- phase: kit ----------------------------------------------------------------------------------------------
    def phase_kit(self):
        kit = self.lim["KIT"]
        r = {"spawn": None, "item": None, "equip": None, "weapon_frame": None, "armed": False, "ok": False}
        self.rd["kit"] = r
        i0 = len(self.lines)
        r["spawn"] = self.xs.spawn(kit, 1, "kit")
        self.wait(lambda: item_added(self.lines[i0:], kit) is not None, self.lim["KIT_TIMEOUT_S"])
        ev = item_added(self.lines[i0:], kit)
        if ev is not None:
            r["item"] = {"itemId": ev.get("itemId"), "source": "item_added", "seq": ev.get("seq"),
                         "wallMs": ev.get("wallMs")}
        else:
            held = sorted(i for i, it in self.world.inventory.items() if it.get("fullType") == kit and item_id_ok(i))
            if held:
                r["item"] = {"itemId": held[0], "source": "inventory", "seq": None, "wallMs": None}
            self.xs.note("kit: no item_added of %s within %s s%s" % (kit, self.lim["KIT_TIMEOUT_S"],
                                                                    "; the inventory's kept" if held else ""))
        iid = (r["item"] or {}).get("itemId")
        if not item_id_ok(iid):
            self.xs.note("kit: no %s item id to equip; the planner flees every threat unarmed" % kit)
            return
        i1 = len(self.lines)
        act_s = self.lim["ACT_TIMEOUT_S"]
        a = self.actions.send(pza1.Equip(iid), deadline_s=act_s)
        self.wait(lambda: self.actions.done(a), act_s + 1.0)
        r["equip"] = {"aid": a.aid, "state": a.state, "reason": a.reason, "result": a.result,
                      "ended_wall": a.ended_wall}

        def wield():
            return next((f for f in self.lines[i1:] if f.get("kind") == "frame"
                         and (f.get("weapon") or {}).get("type") == kit), None)
        self.wait(lambda: wield() is not None, self.lim["EQUIP_TIMEOUT_S"])
        f = wield()
        r["weapon_frame"] = {"seq": f["seq"], "wallMs": f.get("wallMs"), "type": kit} if f else None
        r["armed"] = f is not None
        r["ok"] = bool((r["spawn"] or {}).get("confirmed")) and a.state == "done" and f is not None
        if f is None:
            self.xs.note("kit: no frame shows %s in the primary hand after %s s" % (kit, self.lim["EQUIP_TIMEOUT_S"]))

    # -- phase: loop ---------------------------------------------------------------------------------------------
    def phase_loop(self):
        if not self.ready:
            raise RuntimeError("the hello phase did not pass: no loop on this link")
        self.keep_lines = False
        self.lines = []
        now = self.clock()
        self.t_loop0 = now
        self.fights.t0 = now
        self.loop["startPyMs"] = now * 1000.0
        self.loop["started"] = True                  # a stop before the loop ran is never survived
        self.last_line_t = now
        lim = self.lim
        tick_dt = 1.0 / lim["PLANNER_HZ"]
        next_tick, next_server, next_damage = now, now, now
        next_persist, next_mem = now + lim["PERSIST_S"], now + lim["MEM_POLL_S"]
        if self.polls is not None:
            self.start_polls()
        stop = None
        try:
            while True:
                now = self.clock()
                self.pump()
                self.check_lines(now)
                if self.polls is not None:
                    self.merge_polls(now)
                else:
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
            stop = (s.reason, s.detail)
        except X.BusDead as e:
            stop = ("bus_dead", "xlib BusDead: %s" % e)
        except Exception as e:                       # noqa: BLE001 - the loop's own fault ends it, named
            stop = ("error", "%s: %s" % (type(e).__name__, e))
            raise
        finally:
            self.end_polls()                         # joined before the stop's own bus read (the death record)
            if stop is not None:
                self.set_stop(*stop)
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

    # -- the server reads: synchronous -----------------------------------------------------------------------------
    def server_poll(self, now):
        """stats.all merged into the World, a pump, one needs row paired by wall time, the players list; a death or a
        dead bus raises Stop."""
        if self.xs.bus_dead:
            raise Stop("bus_dead", "server bus dead after %s" % self.xs.bus_dead)
        self.server_polls += 1
        stats_ok = self.merge_stats(DL.bus_stats(self.xs, self.user) or {})
        reply = self.players(self.xs)
        names = self.read_names(reply, now)
        self.count_poll(stats_ok or names is not None)
        self.check_players(names)

    def merge_stats(self, r):
        """One stats.all read ({ack, wallMs}) merged: the World's server map, a pump, the needs row and its pair row.
        True when it carried a stats map."""
        stats = server_stats(_d(r).get("ack"))
        if stats is not None:
            self.world.merge_server(stats, r.get("wallMs"))
        self.pump()
        f, pair = pair_frame(list(self.frames), _d(r).get("wallMs"), self.lim["PAIR_S"])
        self.needs.append(needs_row(f, stats))
        self.needs_pairs.append(pair)
        return stats is not None

    def read_names(self, reply, now):
        names = players_list(reply)
        if names is None:
            self.players_error = {"wallS": now - self.t_loop0, "reply": str(reply)[:300]}
        return names

    def count_poll(self, ok):
        if ok:
            self.fails_in_row = 0
        else:
            self.server_fails += 1
            self.fails_in_row += 1

    def check_players(self, names):
        self.check_death(names)
        self.check_fails()

    def check_death(self, names):
        if names is not None and self.user not in names:
            raise Stop("death", "players reply without %s: %s" % (self.user, names))

    def check_fails(self):
        if self.fails_in_row >= self.lim["BUS_DEAD_POLLS"]:
            raise Stop("bus_dead", "%d consecutive failed server polls, %ss apart" % (
                self.fails_in_row, self.lim["SERVER_POLL_S"]))

    def damage_poll(self, args=None):
        """damage.watch USER since <i> read and merged (damage_read, damage_merge); the ack."""
        self.damage["polls"] += 1
        return self.damage_merge(self.damage_read(args))

    def damage_read(self, args=None):
        """The damage.watch step's ack; `since` is the largest index merged when the call is made."""
        args = args or "%s since %d" % (self.user, self.since_i)
        return self.xs.step("damage_watch", X.SRV, "damage.watch", args, timeout=self.lim["SERVER_TIMEOUT_S"],
                            log=False).get("ack")

    def damage_merge(self, ack):
        """The new records merged into the World, kept with their i and server wall, and summed by tag; a gap in the
        indices (records aged out of the server's list) counts in `lost`. A record merged twice is skipped."""
        dm = self.damage
        if not (isinstance(ack, dict) and ack.get("ok") is True):
            dm["fails"] += 1
            dm["last_error"] = str(ack)[:300]
            return ack
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
        return ack

    # -- the server reads: through the PollThread ------------------------------------------------------------------
    def start_polls(self):
        """The three reads scheduled on the worker: stats and players every SERVER_POLL_S, damage every DAMAGE_POLL_S
        (its `since` read off self.since_i at each call)."""
        p = self.polls
        p.schedule("stats", self.lim["SERVER_POLL_S"], lambda: DL.bus_stats(self.xs, self.user) or {})
        p.schedule("players", self.lim["SERVER_POLL_S"], lambda: self.players(self.xs))
        p.schedule("damage", self.lim["DAMAGE_POLL_S"], lambda: self.damage_read())
        p.start()

    def end_polls(self):
        """The worker stopped and joined (polls_join_s); loop.polls_joined records whether it ended, and a worker
        still in a read is noted (the death record's final read is then skipped)."""
        if self.polls is None or "polls_joined" in self.loop:
            return
        joined = self.polls.stop(self.polls_join_s)
        self.loop["polls_joined"] = joined
        if not joined:
            self.xs.note("the poll worker did not end within %ss: a read still in flight" % self.polls_join_s)

    def polls_busy(self):
        return self.polls is not None and self.polls.alive()

    def _new(self, name):
        got = self.polls.latest(name)
        if got[1] is None or got is self._seen.get(name):
            return None
        self._seen[name] = got
        return got

    def _half(self, name, ok):
        """One half of a server poll arrived; a poll is closed when both have, or when a half arrives twice (the other
        then counts failed)."""
        if name in self._round:
            self._close_round()
        self._round[name] = ok
        if len(self._round) == 2:
            self._close_round()

    def _close_round(self):
        rd, self._round = self._round, {}
        self.server_polls += 1
        self.count_poll(any(rd.values()))

    def merge_polls(self, now):
        """Each result newer than the last merged, and each read that raised on the worker (a failed half); the
        players check and the dead-bus check as the synchronous poll makes them, after the merge (a death reply that
        landed with the worker's mark_dead is a death). Never waits on the bus."""
        names = None
        st, pl, dg = self._new("stats"), self._new("players"), self._new("damage")
        errs = self.polls.errors[self._err_i:]
        self._err_i += len(errs)
        for e in errs:
            if e["name"] == "damage":
                self.damage["polls"] += 1
                self.damage["fails"] += 1
                self.damage["last_error"] = str(e["error"])[:300]
            elif e["name"] in ("stats", "players"):
                if e["name"] == "players":
                    self.players_error = {"wallS": now - self.t_loop0, "reply": str(e["error"])[:300]}
                self._half(e["name"], False)
        if st is not None:
            self._half("stats", self.merge_stats(st[0] or {}))
        if pl is not None:
            names = self.read_names(pl[0], now)
            self._half("players", names is not None)
        if dg is not None:
            self.damage["polls"] += 1
            self.damage_merge(dg[0])
        self.check_death(names)
        if self.xs.bus_dead:
            raise Stop("bus_dead", "server bus dead after %s" % self.xs.bus_dead)
        self.check_fails()
        t = getattr(self.polls, "_thread", None)
        if t is not None and not t.is_alive():
            raise Stop("error", "the poll worker ended outside a read")

    # -- memory, the planner -------------------------------------------------------------------------------------
    def memory_read(self, now):
        """One free-memory read; MEM_LOW_READS in a row below LIVE_MIN_FREE_GB stop."""
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
    def save(self):
        """out["loop"] rebuilt (record.loop_summary, then extra_record()), persist."""
        self.loop.update(record.loop_summary(self))
        self.loop.update(self.extra_record() or {})
        self.out["missing"] = list(self.missing)
        self.xs.persist()

    def death_record(self, via, detail):
        """A last damage.watch read (skipped while the poll worker is still in a read: one bus caller at a time;
        guarded: a dead bus keeps what was merged), then record.death_record."""
        if self.polls_busy():
            self.damage["final_error"] = "poll worker still in a read"
        else:
            try:
                self.damage_poll()
            except Exception as e:                   # noqa: BLE001 - the record is written whatever the bus does
                self.damage["final_error"] = "%s: %s" % (type(e).__name__, e)
        self.tail.read()
        return record.death_record(self, via, detail)

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
            self.xs.run_phase("damage_hook", self.phase_damage_hook)
            self.xs.run_phase("kit", self.phase_kit)
            self.xs.run_phase("loop", self.phase_loop)
        else:
            self.xs.note("no hello: the kit and the loop skipped")
        if self.out.get("stop") is None:
            # the loop never began (a failed hello or the budget): named all the same; a park is bus_dead
            bs = self.out.get("budget_stop")
            pe = self.out.get("phase_errors", {})
            if bs:
                reason, detail = ("bus_dead" if "parked" in str(bs.get("why")) else "budget"), bs.get("why")
            else:
                reason, detail = "error", "; ".join("%s: %s" % (k, v.get("error")) for k, v in pe.items()) or (
                    "the loop did not run")
            self.set_stop(reason, detail)
        self.xs.persist()


# record reads this module's helpers; imported last so either module may be imported first
from agent.driverlib import record                    # noqa: E402
