"""x5_combat -- Plan 22 X5, "combat": the agent base's second live session. One boot of `agent` (fixture `agent`,
Zombies = 5, one admin -debug client, PZTestKit + PZAgent); the agent equips a bat and fights ENCOUNTERS zombies the
server spawns beside it, one at a time, under the `Fight` policy, while the driver measures each swing over the PZA/1
file channel and the server bus. A measurement with pass lines and no gate (spec § 10): `agent.base.gates.measure_x5`
reports it, this driver prints the report at its end, and the controller reads it.

PHASES (each through xs.run_phase; a phase's fault lands under out["phase_errors"][name] and the next still runs;
each reading at out["readings"][phase]):
  hello        pump until the hello line and a first frame, within HELLO_TIMEOUT_S; the hello's proto must be "PZA/1".
               {ok, proto, hello, first_frame {seq, wallMs}}; a failed hello skips every other phase.
  kit          KIT x1 through xs.spawn (RCON additem confirmed by item.get, xlib.Xs.spawn); then pump until an
               `item_added` event of fullType KIT read after the spawn began (KIT_TIMEOUT_S; else the first KIT the
               inventory already holds, source "inventory"); then Equip(itemId) awaited to a terminal state
               (ACT_TIMEOUT_S); then pump until a frame's weapon.type is KIT (EQUIP_TIMEOUT_S). {spawn, item {itemId,
               source, seq, wallMs} | None, equip {aid, state, reason, result, ended_wall} | None, weapon_frame {seq,
               wallMs, type} | None, ok}. An unconfirmed spawn or equip is recorded and the session goes on.
  damage_hook  `damage.watch USER` once (the server's OnPlayerGetDamage listener): {ok, hooked, n, counts, last_i,
               ack}; its records merged into World.merge_damage.
  encounters   up to ENCOUNTERS encounters, readings.encounters {planned, rows [...]}, each row:
                 i, near (the `zombie.near 1` reply {ok, requested, spawned, at, dists [, reason]}), void (None, or
                 why: a reply not ok or spawning none, or no new zombie in a frame within SIGHT_TIMEOUT_S);
                 zid and seen {seq, wallMs, wall, dist, health}: the first frame after the spawn step listing a
                 zombie id the last frame before it did not list (the nearest such id; scoped to the encounter, as
                 the dead and last-seen marks are, so a server that reuses a dead zombie's online id neither voids the
                 sight nor ends the encounter at once); body_at_sight;
                 then the Fight policy ticked at FIGHT_HZ (every POLL_S: pump, the end checks; every 1 / FIGHT_HZ s:
                 observe, choose and send, a `zombie.get` of the target taken right before an attack's send and
                 another right after its end is read) until the end: `dead` (a zombie_dead event for zid or a frame
                 listing zid at health <= 0), `stop` (a stop below), `gone` (no frame listed zid for GONE_S of the
                 client's clock) or `timeout` (ENCOUNTER_S since the encounter began); a still-running action is
                 then stopped (Stop(), stopped_aid) and awaited, ACT_TIMEOUT_S at most;
                 end {reason, wall, wallMs}, stalled and fight_s (the Fight's stall clock), server_end (zombie.get of
                 zid at the end), killed (dead, or server_end reads dead true; None for a voided encounter);
                 actions [every action the Fight sent: {aid, type, args, state, reason, result, accepted_wall,
                 ended_wall, accepted_seq, accepted_wallMs, ended_seq, ended_wallMs}], the walks kept with their ends;
                 swings [per attack: {aid, targetId, accepted_wall, ended_wall, accepted_seq, accepted_wallMs,
                 ended_seq, ended_wallMs, state, reason, result (attackStarted, meleeDelay), client_health_before (the
                 target's health in the last frame before the accept listing it), client_health_after (in the first
                 frame after the end act listing it; None when none does, as after a kill), server_before,
                 server_after (the zombie.get replies, each with epoch_ms_before, epoch_ms_after and wallMs their
                 midpoint), pair_before, pair_after ({server_ms, server_health, frame_seq, frame_wallMs, dt_ms,
                 client_health, void, why}: the reply against the frame listing the target nearest it by wall time,
                 pair_before among the frames before the accept, pair_after among those after the end act; void when
                 apart by more than PAIR_SLACK_S, no such frame lists the target (a kill: Sense lists no dead zombie),
                 the server read no health, or the fence is missing (no accept act, or no end act: a rejected or
                 timed-out attack is voided, never paired unfenced)), pre_read_ms (the pre-send zombie.get's round
                 trip, epoch_ms_after - epoch_ms_before; 0 when none was taken),
                 pair_void (pair_after's void: the pair measure_x5's agreement reads), loop_ms (the encounter's loop
                 latency on the swing that was its first action, else None)}];
                 loop_ms (the first action's accept act wallMs minus seen.wallMs, both the client's clock: raw, so
                 when the first action is an attack it holds the pre-send zombie.get's round trip, that swing's
                 pre_read_ms; measure_x5's loop_ms_net subtracts it and is the agent's own loop);
                 approach [{seq, wallMs, dist}: zid's distance in each frame from the sight to the end of the first
                 swing whose attackStarted read true, for the fight reflex ruling]; body_at_end, health_lost
                 (body_at_sight - body_at_end);
                 between encounters: damage {since, ok, n, last, counts} (`damage.watch USER since <i>`, i the largest
                 record index seen, merged into World.merge_damage), server_tags {tag: n} (the counts' rise over the
                 encounter, None when the read failed), players (the `players` reply's usernames, or None).

STOPS (out["stop"] {reason, detail, wall, encounter}, the first that holds): `health` (a frame's body.health at or
below STOP_HEALTH), `death` (a frame's body.health <= 0, or a `players` reply, a list or {} for nobody, without USER;
an error reply is no death), `budget` (the wall budget's last RESERVE_S reached), `encounters` (ENCOUNTERS run),
`no_hello`; a phase that ends on xlib's Budget names `budget_stop`, on xlib's BusDead (a stalled step and no pong)
`bus_dead` (detail: the step after which the bus died), on a fault `phase_error`.

THE INSTRUMENT'S COST ON THE FIGHT: each swing takes two synchronous server round trips (the zombie.get right before
its send and the one right after its end is read; about 0.3 s each, so about 0.6 s a swing) during which the driver
neither pumps nor ticks the Fight. The fight is slower than the bare agent's and the zombie gets those seconds to
hit, so `health_lost` reads high against an uninstrumented fight; each step's `took` is in out["steps"].

FRAMES (out["frames"]): as x4_link's: `cost` every frame's {seq, tick, wallMs, cost}; `n`; `gaps`, `gap_list`; `bad`;
`lua_errors`, `lua_error_msgs`; `parks` (the console's PARK_RX lines, plus 1 when pzt saw the park and the console
showed nothing). out["measure_x5"] is measure_x5's report; out["finished"] is set last.

Clocks: a line's wallMs is the client's clock (ms); `*_wall` keys are this process's clock in seconds; a server
reply's wallMs is this process's clock in ms (the step's midpoint), the same host's epoch as the client's wallMs.

RULES: never edited after its run (the next pass is a new file); takes no argument; one live session at a time; free
memory gated at MIN_FREE_GB before the boot; never -safemode. Nothing is imported from the frozen drivers but `_dlib`
and `xlib`; x4_link's helpers (parse_argv, memory_gate, clearing_make_client, count_parks, cost_row, act_line,
hello_reading) and c_survive's players_list are copied, since neither driver is a library.
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

import _dlib as DL                                    # noqa: E402
import xlib as X                                      # noqa: E402
from agent.base import gates as GT                    # noqa: E402
from agent.base import pza1                           # noqa: E402
from agent.base.actions import Actions                # noqa: E402
from agent.base.planner.policies import Fight, item_id_ok  # noqa: E402
from agent.base.transport.files import FileTransport  # noqa: E402
from agent.base.world import World                    # noqa: E402

KEY = "x5_combat"
DRIVER = "x5_combat.py"
PROFILE = "testing/profiles/agent.toml"
ARTIFACT = "x5_combat.json"
BUDGET_S = 780.0
USER = "admin"
MIN_FREE_GB = 12.0
KIT = "Base.BaseballBat"
ENCOUNTERS = 5
ENCOUNTER_S = 90.0
STOP_HEALTH = 50.0
PAIR_SLACK_S = 1.0
KIT_TIMEOUT_S = 30.0
EQUIP_TIMEOUT_S = 30.0
FIGHT_HZ = 5
GONE_S = 2.0
HELLO_TIMEOUT_S = 60.0
SIGHT_TIMEOUT_S = 15.0     # a spawned zombie not in a frame by then voids its encounter
SERVER_TIMEOUT_S = 10.0    # each encounter-phase server step's bus timeout
ACT_TIMEOUT_S = 10.0       # Equip's deadline, and the closing Stop's wait
POLL_S = 0.05              # the pump's 20 Hz
RESERVE_S = 30.0           # the budget's last seconds, left to the teardown
PERSIST_S = 60.0
REPO = DL.REPO
AGENT_LUA = "testing/PZAgent"
AGENT_BASE = "testing/agent/base"
# a copy of a_pipe_3's CLIENT_ERR_RX (a_pipe.py's): a Lua error line in the client console, the -debug client's park
PARK_RX = r"LuaError|STACK TRACE|attempted index|tried to call nil"
_ME = os.path.basename(os.path.abspath(__file__))

CONSTANTS = {k: globals()[k] for k in (
    "BUDGET_S", "MIN_FREE_GB", "KIT", "ENCOUNTERS", "ENCOUNTER_S", "STOP_HEALTH", "PAIR_SLACK_S", "KIT_TIMEOUT_S",
    "EQUIP_TIMEOUT_S", "FIGHT_HZ", "GONE_S", "HELLO_TIMEOUT_S", "SIGHT_TIMEOUT_S", "SERVER_TIMEOUT_S",
    "ACT_TIMEOUT_S", "POLL_S", "RESERVE_S", "PERSIST_S", "PARK_RX")}
PHASES = ("hello", "kit", "damage_hook", "encounters")


def parse_argv(argv, driver_file):
    """The driver takes no argument: the refusal text, or None for a bare call."""
    if argv:
        return f"{os.path.basename(driver_file)} takes no arguments; a bare call boots the session"
    return None


def new_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {},
            "readings": {}, "frames": new_frames(), "world_changes": {"left_in_place": []}, "stop": None,
            "finished": False}


def new_frames():
    return {"cost": [], "n": 0, "gaps": 0, "gap_list": [], "bad": 0, "lua_errors": 0, "lua_error_msgs": [],
            "parks": None}


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
    """x4_link's memory_gate (a_pipe.py's), copied: the memory wait before the boot; a false result refuses. The wall
    budget's clock restarts after it; the readings stay under out["memory_wait"]."""
    ok, readings = (wait or DL.wait_memory)(MIN_FREE_GB)
    xs.out["memory_wait"] = readings
    if not ok:
        xs.refuse("blocked: memory")
    xs.t0 = xs.clock()
    return readings


def clearing_make_client(make):
    """x4_link's clearing_make_client, copied: pzt.session.make_client, then the stale pzagent/ folder removed before
    the client is started (the fixture snapshot copies the client's Lua/ folder)."""
    def wrapped(*a, **kw):
        c, restored = make(*a, **kw)
        DL.clear_state_dir(c)
        return c, restored
    return wrapped


def count_parks(consoles, admin_parked=False):
    """x4_link's count_parks, copied: ({user: [PARK_RX lines]}, parks), plus 1 when pzt saw the client park and no
    console line shows it."""
    import re
    rx, echo, never = re.compile(PARK_RX), re.compile(r"PZTK: "), re.compile(r"(?!x)x")
    found, n = {}, 0
    for user, path in consoles:
        lines, _ = X.grep_noecho(path, rx, 80, echo, never)
        found[user] = lines
        n += len(lines)
    if n == 0 and admin_parked:
        n = 1
    return found, n


# ================================================================ the readings: pure functions over PZA/1 lines
def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _frames(lines):
    return [l for l in lines if l.get("kind") == "frame"]


def cost_row(frame):
    """A frame's row in out["frames"]["cost"] (x4_link's)."""
    c = frame.get("cost")
    return {"seq": frame.get("seq"), "tick": frame.get("tick"), "wallMs": frame.get("wallMs"),
            "cost": dict(c) if isinstance(c, dict) else None}


def act_line(lines, aid, states):
    """The first act line for `aid` in one of `states`, or None (x4_link's)."""
    for l in lines:
        if l.get("kind") == "act" and l.get("aid") == aid and l.get("state") in states:
            return l
    return None


def hello_reading(lines):
    hello = next((l for l in lines if l.get("kind") == "hello"), None)
    frame = next((l for l in lines if l.get("kind") == "frame"), None)
    proto = hello.get("proto") if hello else None
    return {"ok": hello is not None and proto == pza1.PROTO and frame is not None, "proto": proto, "hello": hello,
            "first_frame": {"seq": frame.get("seq"), "wallMs": frame.get("wallMs")} if frame else None}


def players_list(reply):
    """c_survive's players_list, copied: the `players` reply as a list of usernames ({} -> [], nobody online); None
    when it is not one (an error string, a dict with an `error` key, a stall)."""
    if isinstance(reply, dict) and ("error" in reply or X.stalled(reply)):
        return None
    if isinstance(reply, list):
        return [str(n) for n in reply]
    if isinstance(reply, dict):
        return [str(reply[k]) for k in sorted(reply, key=str)]
    return None


def zrec(frame, zid):
    """The frame's zombie record of id `zid`, or None."""
    for z in frame.get("zombies") or ():
        if isinstance(z, dict) and z.get("id") == zid:
            return z
    return None


def body_health(frame):
    b = frame.get("body") if isinstance(frame, dict) else None
    return _num(b.get("health")) if isinstance(b, dict) else None


def item_added(lines, full_type):
    """The first `item_added` event of `full_type` among `lines`, or None."""
    for l in lines:
        if l.get("kind") == "event" and l.get("event") == "item_added" and l.get("fullType") == full_type:
            return l
    return None


def new_zombie(lines, known):
    """The first frame listing a zombie id not in `known`: {id, frame, rec} of the nearest such id (ties by id), or
    None."""
    for f in _frames(lines):
        new = [z for z in f.get("zombies") or () if isinstance(z, dict) and z.get("id") is not None
               and z["id"] not in known]
        if new:
            z = min(new, key=lambda r: (_num(r.get("dist")) if _num(r.get("dist")) is not None else math.inf,
                                        str(r["id"])))
            return {"id": z["id"], "frame": f, "rec": z}
    return None


def damage_last(ack):
    """A damage.watch reply's `last` records sorted by i ({} -- the empty Lua table -- and a non-dict read as [])."""
    if not isinstance(ack, dict):
        return []
    last = ack.get("last")
    recs = list(last.values()) if isinstance(last, dict) else list(last) if isinstance(last, list) else []
    recs = [r for r in recs if isinstance(r, dict) and _num(r.get("i")) is not None]
    return sorted(recs, key=lambda r: r["i"])


def counts_diff(before, after):
    """{tag: rise} of damage.watch's per-tag totals over an encounter, rises of 0 left out; None when `after` is not
    a dict (the read failed)."""
    if not isinstance(after, dict):
        return None
    before = before if isinstance(before, dict) else {}
    out = {}
    for tag in sorted(after, key=str):
        d = (_num(after[tag]) or 0) - (_num(before.get(tag)) or 0)
        if d:
            out[tag] = d
    return out


def server_reading(row):
    """A zombie.get step's row as the reading: the reply's fields (or `raw` when it is not a dict), the step's
    epoch_ms_before and epoch_ms_after, and wallMs their midpoint (this process's clock, ms)."""
    ack = row.get("ack")
    r = dict(ack) if isinstance(ack, dict) else {"raw": ack}
    b, a = row.get("epoch_ms_before"), row.get("epoch_ms_after")
    r["epoch_ms_before"], r["epoch_ms_after"] = b, a
    r["wallMs"] = (b + a) / 2.0 if _num(b) is not None and _num(a) is not None else None
    return r


def pair_reading(frames, zid, server, slack_s=PAIR_SLACK_S, before_seq=None, after_seq=None):
    """A server read of zombie `zid` against the frame listing it with a health nearest the read's wallMs (ties by
    the earlier seq), among the frames before `before_seq` and after `after_seq` when given (a swing's pair_before
    reads the frames before its accept, its pair_after those after its end act, so neither pairs a state across the
    swing): {server_ms, server_health, frame_seq, frame_wallMs, dt_ms, client_health, void, why}. void when there is
    no server read, no server time or health (a found false), no such frame listing the zombie with a health, or the
    frame and the reply are apart by more than slack_s."""
    p = {"server_ms": None, "server_health": None, "frame_seq": None, "frame_wallMs": None, "dt_ms": None,
         "client_health": None, "void": True, "why": None}
    if not isinstance(server, dict):
        p["why"] = "no server read"
        return p
    p["server_ms"], p["server_health"] = _num(server.get("wallMs")), _num(server.get("health"))
    whys = []
    if p["server_ms"] is None:
        whys.append("no server time")
    if server.get("found") is not True or p["server_health"] is None:
        whys.append("the server read no health")
    best = None
    if p["server_ms"] is not None:
        for f in frames:
            if (before_seq is not None and f["seq"] >= before_seq) or (after_seq is not None and f["seq"] <= after_seq):
                continue
            z, w = zrec(f, zid), _num(f.get("wallMs"))
            if z is None or w is None or _num(z.get("health")) is None:
                continue
            k = (abs(w - p["server_ms"]), f.get("seq"))
            if best is None or k < best[0]:
                best = (k, f, z)
    if best is None:
        whys.append("no frame lists the zombie with a health")
    else:
        (dt, seq), f, z = best
        p.update(frame_seq=seq, frame_wallMs=f.get("wallMs"), dt_ms=dt, client_health=z.get("health"))
        if dt > slack_s * 1000.0:
            whys.append("frame and reply apart by %s ms, more than PAIR_SLACK_S" % dt)
    p["void"] = bool(whys)
    p["why"] = "; ".join(whys) or None
    return p


def health_before(frames, zid, seq):
    """The zombie's health in the last frame before `seq` listing it, or None."""
    h = None
    for f in frames:
        if seq is not None and f["seq"] < seq and zrec(f, zid) is not None:
            h = zrec(f, zid).get("health")
    return h


def health_after(frames, zid, seq):
    """The zombie's health in the first frame after `seq` listing it, or None."""
    for f in frames:
        if seq is not None and f["seq"] > seq and zrec(f, zid) is not None:
            return zrec(f, zid).get("health")
    return None


def action_row(a, lines):
    """An Action as its row: its end and its accept and end act lines' seq and wallMs (the client's clock)."""
    acc = act_line(lines, a.aid, ("accepted",))
    end = act_line(lines, a.aid, ("done", "failed", "rejected"))
    return {"aid": a.aid, "type": a.type, "args": dict(a.args), "state": a.state, "reason": a.reason,
            "result": a.result, "accepted_wall": a.acked_wall, "ended_wall": a.ended_wall,
            "accepted_seq": acc.get("seq") if acc else None, "accepted_wallMs": acc.get("wallMs") if acc else None,
            "ended_seq": end.get("seq") if end else None, "ended_wallMs": end.get("wallMs") if end else None}


def swing_row(act, pre, post, frames, slack_s=PAIR_SLACK_S):
    """One attack's row (the module docstring): `act` its action_row, `pre` and `post` the server_reading taken
    right before its send and right after its end was read (None when not taken)."""
    tid = act["args"].get("targetId")
    pb = fence(pair_reading(frames, tid, pre, slack_s, before_seq=act["accepted_seq"]), act["accepted_seq"],
               "no accept act")
    pa = fence(pair_reading(frames, tid, post, slack_s, after_seq=act["ended_seq"]), act["ended_seq"], "no end act")
    row = {k: act[k] for k in ("aid", "accepted_wall", "ended_wall", "accepted_seq", "accepted_wallMs", "ended_seq",
                               "ended_wallMs", "state", "reason", "result")}
    row.update({"targetId": tid, "client_health_before": health_before(frames, tid, act["accepted_seq"]),
                "client_health_after": health_after(frames, tid, act["ended_seq"]), "server_before": pre,
                "server_after": post, "pair_before": pb, "pair_after": pa, "pair_void": pa["void"],
                "pre_read_ms": read_ms(pre), "loop_ms": None})
    return row


def fence(pair, seq, what):
    """A swing's pair voided when its fence seq is None (a rejected or timed-out attack): never paired unfenced."""
    if seq is None:
        pair["void"] = True
        pair["why"] = "; ".join(w for w in (pair["why"], "unfenced: %s" % what) if w)
    return pair


def read_ms(server):
    """A server_reading's round trip in ms (epoch_ms_after - epoch_ms_before); 0 when there was no read."""
    if not isinstance(server, dict):
        return 0
    b, a = _num(server.get("epoch_ms_before")), _num(server.get("epoch_ms_after"))
    return a - b if a is not None and b is not None else 0


def approach_reading(frames, zid, until_seq):
    """{seq, wallMs, dist} of zid in each frame listing it up to `until_seq` (None: every frame)."""
    out = []
    for f in frames:
        if until_seq is not None and f["seq"] > until_seq:
            break
        z = zrec(f, zid)
        if z is not None:
            out.append({"seq": f["seq"], "wallMs": f.get("wallMs"), "dist": z.get("dist")})
    return out


def client_dead(lines, zid):
    """True when a zombie_dead event names zid or a frame lists it at health <= 0."""
    for l in lines:
        if l.get("kind") == "event" and l.get("event") == "zombie_dead" and l.get("id") == zid:
            return True
        if l.get("kind") == "frame":
            z = zrec(l, zid)
            h = _num(z.get("health")) if z else None
            if h is not None and h <= 0:
                return True
    return False


def _end(a):
    return {"state": a.state, "reason": a.reason, "result": a.result, "ended_wall": a.ended_wall}


# ================================================================ the session
class X5:
    """The phases over one FileTransport: `pump()` reads the transport, feeds World and Actions and keeps the frames'
    rows and counters; each phase slices `self.lines` (every line read, in seq order) for its reading."""

    def __init__(self, xs, transport, clock=time.time, sleep=time.sleep):
        self.xs, self.tr, self.clock, self.sleep = xs, transport, clock, sleep
        self.out = xs.out
        self.out.setdefault("frames", new_frames())
        self.world = World()
        self.actions = Actions(transport, clock=clock)
        self.lines = []
        self.frame_ids = set()      # the zombie ids the last frame listed
        self.zlast = {}             # zombie id -> the client wallMs of the last frame listing it (this encounter)
        self.dead_ids = set()       # ids a zombie_dead event named or a frame listed at health <= 0 (this encounter)
        self.since_i = 0            # the largest damage.watch record index seen
        self.counts = {}            # the server's per-tag damage totals, as last read
        self.last_persist = clock()

    # -- the pump ------------------------------------------------------------------------------------------------
    def pump(self):
        got = self.tr.lines()
        fr = self.out["frames"]
        for l in got:
            self.world.apply(l)
            if l.get("kind") == "frame":
                fr["cost"].append(cost_row(l))
                fr["n"] += 1
                self.frame_ids = set()
                for z in l.get("zombies") or ():
                    if isinstance(z, dict) and z.get("id") is not None:
                        self.frame_ids.add(z["id"])
                        self.zlast[z["id"]] = l.get("wallMs")
                        h = _num(z.get("health"))
                        if h is not None and h <= 0:
                            self.dead_ids.add(z["id"])
            elif l.get("kind") == "event" and l.get("event") == "lua_error":
                fr["lua_errors"] += 1
                fr["lua_error_msgs"] = (fr["lua_error_msgs"] + [l.get("msg")])[-20:]
            elif l.get("kind") == "event" and l.get("event") == "zombie_dead":
                self.dead_ids.add(l.get("id"))
        self.actions.pump(got)
        self.lines.extend(got)
        fr["gaps"], fr["gap_list"], fr["bad"] = len(self.tr.gaps), [list(g) for g in self.tr.gaps[:50]], self.tr.bad
        return got

    def wait(self, pred, timeout_s):
        """Pump every POLL_S until pred() or timeout_s; True when pred() held. xs.check() guards every poll."""
        t0 = self.clock()
        while True:
            self.pump()
            if pred():
                return True
            if self.clock() - t0 > timeout_s:
                return False
            self.xs.check()
            self.sleep(POLL_S)

    def send(self, cmd, deadline_s=ACT_TIMEOUT_S):
        a = self.actions.send(cmd, deadline_s=deadline_s)
        self.wait(lambda: self.actions.done(a), deadline_s + 1.0)
        return a

    def reading(self, phase, value):
        self.out["readings"][phase] = value
        return value

    def set_stop(self, reason, detail, encounter=None):
        """The session's first stop, named in out["stop"]; a later one is not kept."""
        if self.out.get("stop") is None:
            self.out["stop"] = {"reason": reason, "detail": detail, "wall": self.xs.wall(), "encounter": encounter}
            self.xs.note("stop: %s (%s)" % (reason, detail))
        return self.out["stop"]

    def frame_stop(self):
        """(reason, detail) when the last frame's health or the budget's reserve stops the session, else None."""
        h = body_health({"body": self.world.body})
        if h is not None and h <= 0:
            return "death", "a frame's body.health %s" % h
        if h is not None and h <= STOP_HEALTH:
            return "health", "a frame's body.health %s at or below STOP_HEALTH %s" % (h, STOP_HEALTH)
        if self.xs.wall() > self.xs.budget_s - RESERVE_S:
            return "budget", "wall %s s within RESERVE_S of the budget %s s" % (self.xs.wall(), self.xs.budget_s)
        return None

    def server(self, name, cmd, args):
        return self.xs.step(name, "server", cmd, args, timeout=SERVER_TIMEOUT_S)

    def zget(self, zid, name):
        return server_reading(self.server(name, "zombie.get", str(int(zid))))

    def merge_damage(self, ack):
        """A damage.watch reply into the World; the largest record index and the totals kept."""
        if not isinstance(ack, dict):
            return
        self.world.merge_damage(ack, int(self.clock() * 1000))
        for r in damage_last(ack):
            self.since_i = max(self.since_i, r["i"])
        if isinstance(ack.get("counts"), dict):
            self.counts = dict(ack["counts"])

    # -- the phases ----------------------------------------------------------------------------------------------
    def hello(self):
        self.wait(lambda: self.world.hello is not None and self.world.me is not None, HELLO_TIMEOUT_S)
        r = self.reading("hello", hello_reading(self.lines))
        if not r["ok"]:
            raise RuntimeError("no PZA/1 hello and frame within %s s (proto %r)" % (HELLO_TIMEOUT_S, r["proto"]))

    def kit(self):
        r = self.reading("kit", {"spawn": None, "item": None, "equip": None, "weapon_frame": None, "ok": False})
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
            self.xs.note("kit: no %s item id to equip" % KIT)
            return
        i1 = len(self.lines)
        a = self.send(pza1.Equip(iid))
        r["equip"] = {"aid": a.aid, **_end(a)}

        def wielded():
            return any((f.get("weapon") or {}).get("type") == KIT for f in _frames(self.lines[i1:]))
        self.wait(wielded, EQUIP_TIMEOUT_S)
        f = next((f for f in _frames(self.lines[i1:]) if (f.get("weapon") or {}).get("type") == KIT), None)
        r["weapon_frame"] = {"seq": f["seq"], "wallMs": f.get("wallMs"), "type": KIT} if f else None
        r["ok"] = bool((r["spawn"] or {}).get("confirmed")) and a.state == "done" and f is not None

    def damage_hook(self):
        row = self.server("damage_watch", "damage.watch", USER)
        ack = row.get("ack")
        a = ack if isinstance(ack, dict) else {}
        self.merge_damage(ack)
        self.reading("damage_hook", {"ok": a.get("ok"), "hooked": a.get("hooked"), "n": a.get("n"),
                                     "counts": a.get("counts"), "last_i": self.since_i, "ack": ack})

    def encounters(self):
        r = self.reading("encounters", {"planned": ENCOUNTERS, "rows": []})
        for i in range(1, ENCOUNTERS + 1):
            self.pump()
            why = self.frame_stop()
            if why is not None:
                self.set_stop(why[0], why[1], i)
                break
            row = self.encounter(i)
            r["rows"].append(row)
            self.between(row)
            self.xs.persist()
            self.last_persist = self.clock()
            if self.out.get("stop") is not None:
                break
        if self.out.get("stop") is None:
            self.set_stop("encounters", "%d encounters run" % len(r["rows"]))

    def between(self, row):
        """After an encounter: damage.watch since the last record seen, merged, the encounter's tag rises; the
        players list (a reply without USER is a death)."""
        since, before = self.since_i, dict(self.counts)
        ack = self.server("damage_watch_since", "damage.watch", "%s since %d" % (USER, since)).get("ack")
        ok = isinstance(ack, dict) and ack.get("ok") is True
        if ok:
            self.merge_damage(ack)
        a = ack if isinstance(ack, dict) else {}
        row["damage"] = {"since": since, "ok": ok, "n": a.get("n"), "last": len(damage_last(ack)),
                         "counts": a.get("counts") if ok else None, "raw": None if isinstance(ack, dict) else ack}
        row["server_tags"] = counts_diff(before, self.counts) if ok else None
        names = players_list(self.server("players", "players", "").get("ack"))
        row["players"] = names
        if names is not None and USER not in names:
            self.set_stop("death", "players reply without %s: %s" % (USER, names), row["i"])

    def encounter(self, i):
        self.pump()
        t0, i0 = self.clock(), len(self.lines)
        known = set(self.frame_ids)                 # the encounter's scope: ids, marks and lines from here on
        self.zlast, self.dead_ids = {}, set()
        row = {"i": i, "void": None, "start_wall": self.xs.wall(), "near": None, "zid": None, "seen": None,
               "killed": None, "actions": [], "swings": [], "approach": [], "loop_ms": None, "stopped_aid": None}
        row["near"] = self.server("near", "zombie.near", "1").get("ack")
        near = row["near"] if isinstance(row["near"], dict) else {}
        if near.get("ok") is not True or not _num(near.get("spawned")):
            row["void"] = "zombie.near: ok %r, spawned %r (%s)" % (near.get("ok"), near.get("spawned"),
                                                                   near.get("reason") or str(row["near"])[:120])
            return row
        self.wait(lambda: new_zombie(self.lines[i0:], known) is not None, SIGHT_TIMEOUT_S)
        sight = new_zombie(self.lines[i0:], known)
        if sight is None:
            row["void"] = "no new zombie in a frame within SIGHT_TIMEOUT_S %s s" % SIGHT_TIMEOUT_S
            return row
        zid, f = sight["id"], sight["frame"]
        row["zid"] = zid
        row["seen"] = {"seq": f["seq"], "wallMs": f.get("wallMs"), "wall": self.xs.wall(),
                       "dist": sight["rec"].get("dist"), "health": sight["rec"].get("health")}
        row["body_at_sight"] = body_health(f)
        fight = Fight(self.world, self.actions, clock=self.clock)
        entries, h0 = [], len(self.actions.history)
        next_tick, end = self.clock(), None
        while end is None:
            self.pump()
            self.posts(entries)
            end = self.end_of(zid, t0, i)
            if end is not None:
                break
            if self.clock() >= next_tick:
                self.fight_tick(fight, entries)
                next_tick = self.clock() + 1.0 / FIGHT_HZ
            if self.clock() - self.last_persist > PERSIST_S:
                self.xs.persist()
                self.last_persist = self.clock()
            self.xs.check()
            self.sleep(POLL_S)
        row["end"] = {"reason": end, "wall": self.xs.wall(), "wallMs": self.world.frame_wall_ms}
        row["stalled"], row["fight_s"] = fight.stalled, round(fight.fight_s(), 3)
        if self.actions.current is not None:
            s = self.actions.stop()
            row["stopped_aid"] = s.aid
            self.wait(lambda: all(self.actions.done(a) for a in self.actions.history[h0:]), ACT_TIMEOUT_S)
        self.posts(entries)
        row["server_end"] = self.zget(zid, "zget_end")
        self.pump()
        lines = self.lines[i0:]
        frames = _frames(lines)
        acts = [action_row(e["a"], lines) for e in entries]
        row["actions"] = acts
        row["swings"] = [swing_row(a, e["pre"], e["post"], frames) for a, e in zip(acts, entries)
                         if a["type"] == "attack"]
        if acts and _num(acts[0]["accepted_wallMs"]) is not None and _num(row["seen"]["wallMs"]) is not None:
            row["loop_ms"] = acts[0]["accepted_wallMs"] - row["seen"]["wallMs"]
            if acts[0]["type"] == "attack":
                row["swings"][0]["loop_ms"] = row["loop_ms"]
        hit = next((s for s in row["swings"] if isinstance(s["result"], dict)
                    and s["result"].get("attackStarted") is True), None)
        row["approach"] = approach_reading([fr for fr in frames if fr["seq"] >= f["seq"]], zid,
                                           hit["ended_seq"] if hit else None)
        last = frames[-1] if frames else f
        row["body_at_end"] = body_health(last)
        b0, b1 = row["body_at_sight"], row["body_at_end"]
        row["health_lost"] = b0 - b1 if b0 is not None and b1 is not None else None
        srv_dead = (row["server_end"] or {}).get("dead") is True
        row["killed"] = end == "dead" or client_dead(lines, zid) or srv_dead
        return row

    def end_of(self, zid, t0, i):
        """The encounter's end, or None: dead, stop (a frame_stop, named in out["stop"]), gone, timeout."""
        if zid in self.dead_ids:
            return "dead"
        why = self.frame_stop()
        if why is not None:
            self.set_stop(why[0], why[1], i)
            return "stop"
        last, now = _num(self.zlast.get(zid)), _num(self.world.frame_wall_ms)
        if last is not None and now is not None and now - last > GONE_S * 1000.0:
            return "gone"
        if self.clock() - t0 > ENCOUNTER_S:
            return "timeout"
        return None

    def fight_tick(self, fight, entries):
        """Fight.step() split as Survive splits it: observe, then (not busy) choose; a zombie.get of an attack's
        target right before its send."""
        fight.observe()
        if fight.busy():
            return
        cmd = fight.choose()
        if cmd is None:
            return
        pre = self.zget(cmd.targetId, "zget_before") if cmd.TYPE == "attack" else None
        a = fight.send(cmd)
        entries.append({"a": a, "pre": pre, "post": None, "posted": False})

    def posts(self, entries):
        """A zombie.get of each attack's target right after its end is read (once an attack)."""
        for e in entries:
            a = e["a"]
            if a.type == "attack" and not e["posted"] and self.actions.done(a):
                e["posted"] = True
                e["post"] = self.zget(a.args["targetId"], "zget_after")

    def run(self):
        self.xs.run_phase("hello", self.hello)
        if (self.out["readings"].get("hello") or {}).get("ok"):
            for name in PHASES[1:]:
                self.xs.run_phase(name, getattr(self, name))
        else:
            self.xs.note("no hello: every other phase skipped")
            self.set_stop("no_hello", "no PZA/1 hello and frame within HELLO_TIMEOUT_S")
        if self.out.get("stop") is None:
            bs = self.out.get("budget_stop")
            if bs:
                self.set_stop("budget_stop", bs.get("why"))
            elif self.xs.bus_dead:
                self.set_stop("bus_dead", "server bus dead after %s" % self.xs.bus_dead)
            else:
                self.set_stop("phase_error", sorted(self.out.get("phase_errors") or {}))


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
            X5(xs, FileTransport(DL.state_dir(clients[USER]))).run()
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
            out["measure_x5"] = GT.measure_x5(out)
        except Exception as e:                               # noqa: BLE001 - the controller re-measures the artifact
            out["measure_x5_error"] = f"{type(e).__name__}: {e}"
        out["finished"] = True
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)
    print(json.dumps({"run_id": run_id, "run_dir": run_dir, "error": out.get("error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "budget_stop": out.get("budget_stop"), "stop": out.get("stop"),
                      "measure_x5": out.get("measure_x5"), "wall_seconds": out.get("wall_seconds")},
                     indent=1, default=str))
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main()
