"""c_survive -- Plan 21 Task 12, Stage C (spec § 4.3): survival, the answer. One boot of `agent` (fixture `agent`,
Zombies = 5, admin -debug, PZTestKit + PZAgent, the 90-minute day, sleep allowed); the scripted bot (agent/policy.py)
plays until a stop condition ends the session. No pass/fail gate: the grade (c_grade.py, agent/grade_c.py) is a report.
c_survive_dense.py runs the same loop on agent-dense (Zombies = 4) and imports everything here, its names passed in a
Spec.

PHASES (each through xs.run_phase; a phase's fault is recorded and the next still runs):
  hello   wait for the hello line (HELLO_TIMEOUT_S), whose mode must be "append" (anything else fails the phase), then
          for the first frame (FRAME_TIMEOUT_S).
  kit     the start kit: KIT (Base.BaseballBat) x1 through xs.spawn (RCON additem confirmed by item.get), then the
          client's weapon.equip of it (PZTestKit_Client.lua, @reply {ok, fullType, itemId, twoHands, queued [, reason]}),
          then up to EQUIP_TIMEOUT_S for a frame whose weapon.type is KIT. All three under readings.start_kit; an
          unconfirmed spawn or equip is recorded and the session goes on (the policy flees when unarmed).
  survive the planner loop, every POLL_S of the clock:
            pump the link (each line through World.apply; the frame's tick cost, a death frame and lua_error events
              are read here);
            every SERVER_POLL_S: the server's stats.all (_dlib.bus_stats) merged into the World (World.merge_server
              with the reply's stats map and this process's wall ms) and the server's `players` list (@reply
              [<username>, ...], {} when nobody is online); one needs row is sampled there, so the client frame and
              the server reading share a wall second: [gameMin, hunger, thirst, fatigue, health, serverHunger]
              (serverHunger the stats map's Hunger, None when the read failed);
            every MEM_POLL_S, the first one MEM_POLL_S after the loop's start: host free memory (xlib.free_gb),
              every read under out["memory_reads"];
            at PLANNER_HZ: policy.tick() (it writes decision.log beside the artifact; the driver keeps the last ten
              lines); a `fight` sent opens a fights row {seq, startS, startWallMs, gameMin, health, threats,
              nearest, end}, its end ({state, detail, wallMs}, the client's clock) read off the goal's end;
            every PERSIST_S: out["loop"] rebuilt and xs.persist() (the controller polls the persisted artifact).
          STOP CONDITIONS, the first that holds ends the loop, named in out["stop"] {reason, detail, wallS, gameMin}:
            death           a frame's health <= 0, or a `players` reply (a list, or {} for nobody) without USER; a
                            players reply that is an error (a string, a dict with an `error` key, a stall) is no
                            death: it counts as a failed read, the last one kept as loop.players_error;
            bus_dead        BUS_DEAD_POLLS consecutive failed server polls (neither stats.all with a stats map nor a
                            players list; SERVER_POLL_S apart, so one failed poll is never enough), no link line for
                            BUS_DEAD_S (the client parked or gone), xlib's BusDead (a stalled step and no pong), or
                            the client parked in the debugger (xs.check);
            lua_error_storm more than STORM_N lua_error events within a STORM_WINDOW_S window of the client's own
                            clock (each event's wallMs), so a backlog read at once is no storm;
            memory          MEM_LOW_READS consecutive reads below LIVE_MIN_FREE_GB (None counts as low,
                            xlib.memory_ok); MIN_FREE_GB is the pre-boot floor only: a running server and client
                            leave the host at 2-3 GB (the `ready` readings of a_pipe and a_pipe_2);
            day_cap         the loop's own wall time reaches DAY_CAP_S (one game day at the 90-minute day);
            budget          xs.check's wall budget (BUDGET_S from the end of the memory gate, the boot included);
            error           anything else the loop raised (its type and message).
          A death keeps out["loop"]["death"] {via, detail, wallS, gameMin, last_decisions}.
  The kit's weapon.equip is asked every EQUIP_RETRY_S up to EQUIP_TIMEOUT_S until its reply is ok (x42e's pattern),
  every ask under readings.start_kit.equip_asks; `armed` is read off the frames only.
out["loop"]: ticks (planner ticks, one decision.log line each), decisions (goals sent), last_decisions (the log's last
ten lines), needs, fights, lua_errors_per_min ({loop minute: count}), cost ({n, p50, p99, max} of each frame's tick
cost, the sum of COST_KEYS), goal_outcomes ({goal: {state: {detail: n}}} over every goal the policy sent, scan
excluded; "refused" for a refused ack, "open" for one not seen to end), server_polls, server_fails, memory, wallS.
out["missing"], gaps, bad, lua_errors and client_lua_errors as a_pipe's. out["finished"] is set last.

Clocks: a line's wallMs is the client's PZA.now(); wallS and startS are this process's clock since the loop began.

RULES: never edited after its run (the next pass is a new file); takes no argument; one live session at a time; free
memory gated at MIN_FREE_GB before the boot; never -safemode; launched detached by the controller and polled through
the persisted artifact.
"""
import collections
import json
import os
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
from agent.drivers import a_pipe as AP                # noqa: E402  (Pipe and the boot seams; a frozen file)
from agent.grade_c import pct                         # noqa: E402
from agent.policy import CONFIG, Policy               # noqa: E402

KEY = "c_survive"
DRIVER = "c_survive.py"
PROFILE = "testing/profiles/agent.toml"
ARTIFACT = "c_survive.json"
BUDGET_S = 5700.0
USER = "admin"
MIN_FREE_GB = 12.0
REPO = DL.REPO
_ME = os.path.basename(os.path.abspath(__file__))

PLANNER_HZ = 2
SERVER_POLL_S = 60
PERSIST_S = 30
MEM_POLL_S = 300
LIVE_MIN_FREE_GB = 0.5               # the in-session floor (MIN_FREE_GB is the pre-boot one)
MEM_LOW_READS = 2                    # consecutive reads below LIVE_MIN_FREE_GB that stop the loop
DAY_CAP_S = 5400
BUS_DEAD_S = 60                      # link silence; and the dispatch's 60 s, which BUS_DEAD_POLLS polls exceed
BUS_DEAD_POLLS = 2                   # consecutive failed server polls (SERVER_POLL_S apart) that stop the loop
STORM_N = 10                         # more lua_error events than this within STORM_WINDOW_S is a storm
STORM_WINDOW_S = 60
HELLO_TIMEOUT_S = 60.0
FRAME_TIMEOUT_S = 10.0
EQUIP_TIMEOUT_S = 15.0
EQUIP_RETRY_S = 1.0
KIT = "Base.BaseballBat"
POLL_S = 0.1
DECISION_LOG = "decision.log"
LAST_DECISIONS = 10
COST_KEYS = ("pollMs", "actMs", "scanStepMs", "senseMs", "linkMs")
AGENT_LUA = "testing/PZAgent"
AGENT_PY = "testing/agent"
CLIENT_ERR_RX = AP.CLIENT_ERR_RX
FINISHED = ("done", "failed")
STOPS = ("death", "bus_dead", "lua_error_storm", "memory", "day_cap", "budget", "error")

CONSTANTS = {k: globals()[k] for k in (
    "BUDGET_S", "MIN_FREE_GB", "PLANNER_HZ", "SERVER_POLL_S", "PERSIST_S", "MEM_POLL_S", "LIVE_MIN_FREE_GB",
    "MEM_LOW_READS", "DAY_CAP_S", "BUS_DEAD_S", "BUS_DEAD_POLLS", "STORM_N", "STORM_WINDOW_S", "HELLO_TIMEOUT_S",
    "FRAME_TIMEOUT_S", "EQUIP_TIMEOUT_S", "EQUIP_RETRY_S", "KIT", "POLL_S",
    "COST_KEYS", "CLIENT_ERR_RX")}

Spec = collections.namedtuple("Spec", "key driver profile artifact")
SPEC = Spec(KEY, DRIVER, PROFILE, ARTIFACT)

parse_argv = AP.parse_argv
client_errors = AP.client_errors
clearing_make_client = AP.clearing_make_client
_seq = AP._seq


def new_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {},
            "readings": {"start_kit": None}, "loop": {}, "stop": None,
            "world_changes": {"left_in_place": []}, "finished": False}


def driver_checks(driver_file, spec=SPEC, repo=REPO, git_say=None, git_dirty=None):
    """The driver's own pre-boot checks on its spec: its file name and key, its profile on disk, no committed artifact
    of its key (a driver that ran is frozen), the agent Lua, the agent Python and this file committed clean (the dense
    driver imports this file, so both are checked). Returns (checks, ok)."""
    git_say = git_say or DL.C.git_say
    git_dirty = git_dirty or DL.C.git_dirty
    base = os.path.basename(driver_file)
    c = {"driver_file": base == spec.driver, "driver_prefix": base.startswith(spec.key),
         "profile_exists": os.path.isfile(os.path.join(repo, spec.profile))}
    c["no_committed_artifact"] = git_say("ls-files", "--", f"testing/artifacts/{spec.key}-*") == ""
    c["agent_lua_dirty"] = git_dirty(AGENT_LUA)[0]
    c["agent_py_dirty"] = git_dirty(AGENT_PY)[0]
    c["driver_dirty"] = git_dirty(f"testing/agent/drivers/{spec.driver}")[0]
    ok = (c["driver_file"] and c["driver_prefix"] and c["profile_exists"] and c["no_committed_artifact"]
          and c["agent_lua_dirty"] is False and c["agent_py_dirty"] is False and c["driver_dirty"] is False)
    return c, ok


def preboot(driver_file, spec=SPEC, repo=REPO):
    pre, ok = DL.preboot(driver_file, os.path.join(repo, spec.profile))
    pre["driver_checks"], ok2 = driver_checks(driver_file, spec, repo)
    return pre, bool(ok and ok2)


memory_gate = AP.memory_gate


# ================================================================ pure helpers
def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def tick_cost(cost):
    """A frame's tick cost: the sum of the COST_KEYS present as numbers; None when the frame carries none."""
    if not isinstance(cost, dict):
        return None
    vals = [_num(cost.get(k)) for k in COST_KEYS]
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def players_list(reply):
    """The `players` reply as a list of usernames ({} -> [], nobody online); None when it is not one: an error string,
    or a dict with an `error` key (the bus's own failure reply, a stall included)."""
    if isinstance(reply, dict) and ("error" in reply or X.stalled(reply)):
        return None
    if isinstance(reply, (list, dict)):
        return [str(n) for n in _seq(reply)]
    return None


def server_stats(reply):
    """stats.all's stats map ({<registry id>: value}); None when the reply carries none."""
    if isinstance(reply, dict) and isinstance(reply.get("stats"), dict):
        return reply["stats"]
    return None


def read_players(xs):
    """The server's `players` reply (the step's ack)."""
    return xs.step("players", X.SRV, "players").get("ack")


def equip_weapon(xs, full_type):
    """The client's weapon.equip of `full_type` (the step's ack)."""
    return xs.step("equip_" + full_type.split(".")[-1], "client:" + xs.user, "weapon.equip", full_type).get("ack")


class DecisionTail:
    """The last `n` lines of the decision log, read incrementally (only the bytes appended since the last read)."""

    def __init__(self, path, n=LAST_DECISIONS):
        self.path = path
        self.pos = 0
        self.lines = deque(maxlen=n)

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
                    self.lines.append(json.loads(raw.decode("utf-8")))
                except ValueError:
                    self.lines.append({"unparsed": raw.decode("utf-8", "replace")})

    def last(self):
        return list(self.lines)


class Stop(Exception):
    """A stop condition held: its reason (one of STOPS) and detail."""

    def __init__(self, reason, detail):
        super().__init__("%s: %s" % (reason, detail))
        self.reason, self.detail = reason, detail


# ================================================================ the session
class Survive(AP.Pipe):
    """The hello, kit and survive phases over one Link. clock, sleep, bus_stats, players, free (the memory read),
    spawn and equip are injectable; `limits` overrides the loop's cadence and caps by constant name (tests)."""

    def __init__(self, xs, link, world=None, clock=time.time, sleep=time.sleep, bus_stats=DL.bus_stats,
                 players=read_players, free=X.free_gb, spawn=None, equip=equip_weapon, limits=None, poll_s=POLL_S):
        super().__init__(xs, link, world=world, clock=clock, sleep=sleep, bus_stats=bus_stats, poll_s=poll_s)
        self.rd = self.out.setdefault("readings", {"start_kit": None})
        self.players = players
        self.free = free
        self.spawn = spawn or xs.spawn
        self.equip = equip
        lim = {k: globals()[k] for k in ("PLANNER_HZ", "SERVER_POLL_S", "PERSIST_S", "MEM_POLL_S", "LIVE_MIN_FREE_GB",
                                          "MEM_LOW_READS", "DAY_CAP_S", "BUS_DEAD_S", "BUS_DEAD_POLLS", "STORM_N",
                                          "STORM_WINDOW_S")}
        lim.update(limits or {})
        self.lim = lim
        run_dir = os.path.dirname(xs.path) if xs.path else os.getcwd()
        self.log_path = os.path.join(run_dir, DECISION_LOG)
        xs.copied.append(DECISION_LOG)
        self.policy = Policy(self.world, link, self.log_path, clock)
        self.tail = DecisionTail(self.log_path)
        self.frame = None            # the latest frame line (frames are not kept: a day is ~27000 of them)
        self.n_frames = 0
        self.n_lua_errors = 0
        self.err_times = deque()     # the client clock (wallMs / 1000) of each lua_error, inside the storm window
        self.client_now = None       # the latest line's client clock (s)
        self.err_per_min = {}
        self.costs = []
        self.death_frame = None
        self.t_loop0 = None
        self.ready = False           # set by a hello phase that passed: the kit and the loop need it
        self.loop = self.out.setdefault("loop", {})
        self.ticks = 0
        self.decisions = 0
        self.needs = []
        self.fights = []
        self.server_polls = 0
        self.server_fails = 0
        self.fails_in_row = 0
        self.players_error = None
        self.mem_rows = []
        self.mem_low_in_row = 0

    # ---- reading the link (a_pipe's on_line, bounded for a day-long session)
    def loop_s(self):
        return None if self.t_loop0 is None else self.clock() - self.t_loop0

    def on_line(self, l):
        self.world.apply(l)
        self.last_seq = max(self.last_seq, l.get("seq", 0))
        w = _num(l.get("wallMs"))
        if w is not None:
            self.client_now = w / 1000.0 if self.client_now is None else max(self.client_now, w / 1000.0)
        k = l.get("kind")
        if k == "frame":
            self.frame = l
            self.n_frames += 1
            g = l.get("goal") or {}
            if g.get("state") in FINISHED and (g.get("seq") not in self.goal_end
                                               or self.goal_end[g.get("seq")].get("from") == "event"):
                self.goal_end[g.get("seq")] = {"state": g.get("state"), "detail": g.get("detail"),
                                               "seq": l.get("seq"), "wallMs": l.get("wallMs"), "from": "frame"}
            c = tick_cost(l.get("cost"))
            if c is not None:
                self.costs.append(c)
            h = _num(l.get("health"))
            if h is not None and h <= 0 and self.death_frame is None:
                self.death_frame = {"health": h, "seq": l.get("seq"), "wallMs": l.get("wallMs"),
                                    "gameMin": l.get("gameMin")}
        elif k == "hello" and self.hello is None:
            self.hello = l
        elif k == "event":
            ev = l.get("event")
            self.events[ev] = self.events.get(ev, 0) + 1
            if ev in ("goal_done", "goal_failed") and l.get("goalSeq") not in self.goal_end:
                # goal_done carries no detail: a later frame of the same goal replaces this entry
                self.goal_end[l.get("goalSeq")] = {"state": ev[5:], "detail": l.get("reason", ""), "seq": l.get("seq"),
                                                   "wallMs": l.get("wallMs"), "from": "event"}
            elif ev == "lua_error":
                self.n_lua_errors += 1
                if len(self.lua_errors) < 20:
                    self.lua_errors.append(l)
                s = self.loop_s()
                if s is not None:
                    if w is not None:
                        self.err_times.append(w / 1000.0)
                    m = str(int(s // 60))
                    self.err_per_min[m] = self.err_per_min.get(m, 0) + 1
        for m in _seq(l.get("missing")):
            if m not in self.missing:
                self.missing.append(m)

    def sync_out(self):
        self.out["missing"] = list(self.missing)
        self.out["gaps"] = [list(g) for g in self.link.gaps]
        self.out["bad"] = getattr(self.link, "bad", 0)
        self.out["lua_errors"] = self.n_lua_errors
        self.out["lua_error_lines"] = list(self.lua_errors)
        self.out["events"] = dict(self.events)
        self.out["lines_read"] = self.last_seq
        self.out["frames_read"] = self.n_frames

    # ---- phase: hello
    def phase_hello(self):
        t0 = self.py_ms()
        self.wait_until(lambda: self.hello is not None, HELLO_TIMEOUT_S)
        self.out["hello_wait_ms"] = self.py_ms() - t0
        self.need_hello()
        self.out["hello"] = self.hello
        self.out["mode"] = self.hello.get("mode")
        self.out["hello_build"] = self.hello.get("build")
        if self.out["mode"] != "append":
            raise RuntimeError("hello mode %r, not append" % (self.out["mode"],))
        if not self.wait_until(lambda: self.frame is not None, FRAME_TIMEOUT_S):
            raise RuntimeError("no frame after the hello")
        self.ready = True

    def need_ready(self):
        self.need_hello()
        if not self.ready:
            raise RuntimeError("the hello phase did not pass: no loop on this link")

    # ---- phase: kit
    def armed_with(self, full_type):
        w = (self.frame or {}).get("weapon")
        return isinstance(w, dict) and w.get("type") == full_type

    def phase_kit(self):
        self.need_ready()
        kit = {"type": KIT, "spawn": None, "equip": None, "armed": False}
        self.rd["start_kit"] = kit
        kit["spawn"] = self.spawn(KIT, 1, "spawn_" + KIT.split(".")[-1])
        self.xs.persist()
        asks, end = [], self.clock() + EQUIP_TIMEOUT_S
        while True:
            r = self.equip(self.xs, KIT)
            a = r if isinstance(r, dict) else {"raw": r}
            asks.append({k: a.get(k) for k in ("ok", "queued", "itemId", "twoHands", "reason", "raw")})
            if a.get("ok") is True or self.clock() >= end:
                break
            t_next = self.clock() + EQUIP_RETRY_S
            self.wait_until(lambda: self.clock() >= t_next, EQUIP_RETRY_S + 1.0)
        kit["equip"] = asks[-1]
        kit["equip_asks"] = asks
        kit["armed"] = self.wait_until(lambda: self.armed_with(KIT), EQUIP_TIMEOUT_S)
        if not kit["armed"]:
            self.xs.note("start kit: no frame shows %s in the primary hand after %ss" % (KIT, EQUIP_TIMEOUT_S))

    # ---- phase: survive
    def phase_survive(self):
        self.need_ready()
        now = self.clock()
        self.t_loop0 = now
        self.loop["startPyMs"] = now * 1000.0
        self.last_line_t = now
        lim = self.lim
        tick_dt = 1.0 / lim["PLANNER_HZ"]
        next_tick, next_server, next_persist = now, now, now + lim["PERSIST_S"]
        next_mem = now + lim["MEM_POLL_S"]
        try:
            while True:
                now = self.clock()
                if self.pump():
                    self.last_line_t = now
                self.check_lines(now)
                if now >= next_server:
                    next_server = now + lim["SERVER_POLL_S"]
                    self.server_poll(now)
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
            raise Stop("death", "frame seq %s health %s" % (self.death_frame["seq"], self.death_frame["health"]))
        if self.client_now is not None:
            while self.err_times and self.err_times[0] < self.client_now - self.lim["STORM_WINDOW_S"]:
                self.err_times.popleft()
        if len(self.err_times) > self.lim["STORM_N"]:
            raise Stop("lua_error_storm", "%d lua_error events within %ss" % (len(self.err_times),
                                                                               self.lim["STORM_WINDOW_S"]))
        if now - self.last_line_t >= self.lim["BUS_DEAD_S"]:
            raise Stop("bus_dead", "no link line for %ss (the client parked or gone)" % self.lim["BUS_DEAD_S"])

    def server_poll(self, now):
        """stats.all merged into the World, the players list, one needs row; a death or a dead bus raises Stop."""
        self.server_polls += 1
        r = self.bus_stats(self.xs, USER) or {}
        stats = server_stats(r.get("ack"))
        if stats is not None:
            self.world.merge_server(stats, r.get("wallMs"))
        reply = self.players(self.xs)
        names = players_list(reply)
        me = self.world.me
        self.needs.append([me.get("gameMin"), me.get("hunger"), me.get("thirst"), me.get("fatigue"),
                           me.get("health"), _num((stats or {}).get("Hunger"))])
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
            raise Stop("bus_dead", "%d consecutive failed server polls, %ss apart (over the dispatch's %ss)" % (
                self.fails_in_row, self.lim["SERVER_POLL_S"], BUS_DEAD_S))

    def memory_read(self, now):
        """One free-memory read, kept under out["memory_reads"]; MEM_LOW_READS in a row below LIVE_MIN_FREE_GB stop."""
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
        f = self.frame or {}
        sent = self.policy.tick()
        self.ticks += 1
        self.tail.read()
        if sent is None:
            return
        self.decisions += 1
        if sent == "fight" and self.policy.running is not None:
            inp = (self.tail.last() or [{}])[-1].get("inputs") or {}
            self.fights.append({"seq": self.policy.running[2], "startS": self.loop_s(), "startWallMs": f.get("wallMs"),
                                "gameMin": f.get("gameMin"), "health": f.get("health"),
                                "threats": inp.get("threats"), "nearest": inp.get("nearest"), "end": None})

    # ---- the record
    def goal_outcomes(self):
        """{goal: {state: {detail: n}}} over every goal the policy sent (configuration commands excluded)."""
        hist = {}
        for seq, (goal, _args) in sorted(self.policy.sent.items()):
            if goal in CONFIG:
                continue
            end = self.goal_end.get(seq)
            ack = self.link.ack_of(seq)
            if end is not None:
                state, detail = end["state"], end.get("detail") or ""
            elif ack is not None and not ack.get("ok"):
                state, detail = "refused", ack.get("reason") or ""
            else:
                state, detail = "open", ""
            d = hist.setdefault(goal, {}).setdefault(state, {})
            d[str(detail)] = d.get(str(detail), 0) + 1
        return hist

    def close_fights(self):
        """Each fight's end from goal_end, refreshed while it came from a goal_done event (no detail) and a frame of
        the same goal may still bring the detail."""
        for f in self.fights:
            if (f["end"] is None or f["end"].get("from") == "event") and f["seq"] in self.goal_end:
                e = self.goal_end[f["seq"]]
                f["end"] = {"state": e["state"], "detail": e.get("detail"), "wallMs": e.get("wallMs"),
                            "from": e.get("from")}

    def save(self):
        """out["loop"] rebuilt, sync_out, persist."""
        self.close_fights()
        cs = self.costs
        self.loop.update({
            "wallS": self.loop_s(), "ticks": self.ticks, "decisions": self.decisions,
            "last_decisions": self.tail.last(), "needs": list(self.needs),
            "needs_fields": ["gameMin", "hunger", "thirst", "fatigue", "health", "serverHunger"],
            "fights": [dict(f) for f in self.fights], "lua_errors_per_min": dict(self.err_per_min),
            "cost": {"n": len(cs), "p50": pct(cs, 50), "p99": pct(cs, 99), "max": max(cs) if cs else None,
                     "keys": list(COST_KEYS)},
            "goal_outcomes": self.goal_outcomes(), "server_polls": self.server_polls,
            "server_fails": self.server_fails, "players_error": self.players_error, "memory": list(self.mem_rows)})
        self.sync_out()
        self.xs.persist()

    def set_stop(self, reason, detail):
        f = self.frame or {}
        self.out["stop"] = {"reason": reason, "detail": detail, "wallS": self.loop_s(), "gameMin": f.get("gameMin"),
                            "worldAge": f.get("worldAge")}
        if reason == "death":
            self.tail.read()
            self.loop["death"] = {"via": "frame" if self.death_frame is not None else "players", "detail": detail,
                                  "wallS": self.loop_s(), "gameMin": f.get("gameMin"),
                                  "frame": self.death_frame, "last_decisions": self.tail.last()}
        self.xs.note("stop %s: %s" % (reason, detail))

    def phases(self):
        return [("hello", self.phase_hello), ("kit", self.phase_kit), ("survive", self.phase_survive)]

    def run(self):
        for name, fn in self.phases():
            self.xs.run_phase(name, fn)
            self.sync_out()
        if self.out.get("stop") is None:
            # the survive phase never began its loop (an earlier phase's fault or the budget): named all the same
            bs = self.out.get("budget_stop")
            pe = self.out.get("phase_errors", {})
            reason, detail = ("budget", bs.get("why")) if bs else ("error", "; ".join(
                "%s: %s" % (k, v.get("error")) for k, v in pe.items()) or "the loop did not run")
            self.set_stop(reason, detail)
        self.xs.persist()


# ================================================================ the boot
def main(spec=SPEC, me=_ME, budget_s=BUDGET_S):
    from _common import ask, hard_kill                       # noqa: E402
    import x49b_lib as B                                     # noqa: E402
    from pzt import fixture as fx, profile, session          # noqa: E402
    from pzt.bus import resolve_side                         # noqa: E402
    from pzt.paths import new_run_dir                        # noqa: E402

    pre, ok = preboot(me, spec)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    prof = profile.load(os.path.join(REPO, spec.profile))
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(spec.key)
    tl = session.Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = new_out()
    out["world_changes"]["restored"] = f"fixture {prof.fixture} restored into the run dir"
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, user=USER)
    xs.path = os.path.join(run_dir, spec.artifact)
    out.update({"run_id": run_id, "session_key": spec.key, "driver": me, "user": USER, "profile": prof.report(),
                "preboot": pre, "argv": sys.argv[1:], "constants": CONSTANTS,
                "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                            "build": rec_fx.get("build")},
                "driver_commit": DL.C.git_say("log", "-1", "--format=%h", "--", f"testing/agent/drivers/{spec.driver}"),
                "c_survive_commit": DL.C.git_say("log", "-1", "--format=%h", "--", f"testing/agent/drivers/{DRIVER}")})
    memory_gate(xs)
    xs.mem("preboot")
    xs.persist()
    sv = None
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
            sv = Survive(xs, DL.link_for(clients, USER))
            sv.run()
    except Exception as e:                                   # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            found, n = client_errors([(getattr(c, "username", "?"), c.console) for c in every])
            out["logs"] = {"patterns": {"client_error": CLIENT_ERR_RX}, "clients": found}
            out["client_lua_errors"] = n

        if sv is not None:
            sv.sync_out()
        xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs)
        xs.mem("after")
        out["finished"] = True
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, spec.artifact)
    print(json.dumps({"run_id": run_id, "run_dir": run_dir, "error": out.get("error"), "abort": out.get("abort"),
                      "stop": out.get("stop"), "phase_errors": {k: v.get("error") for k, v in
                                                                out.get("phase_errors", {}).items()},
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str))
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main()
