"""x244b-notice -- Plan 10c Task H4 (live), session b: does a player notice the minute burst (review-platform X2), and
Decision 6's evidence completed per ruling H4-1, at the 37-tick spacing (time.multiplier 0.1674, the DayLength 4
spacing, #3394; set live after S0 in phase M, as x243c did), N = 60 synthetic players. One idle baseline, then
burst, budget15, burst, budget15, budget15, burst (three draws of each, rotated). On the UNINSTRUMENTED staged copy of
the tree at 9578eb9 (release/hitch-9578eb9/NutritionRevamp/Contents/mods/NutritionRevamp, staged by Task 0,
MANIFEST.json sha256 c86e295a...b389; release/ is gitignored; mod/ is never booted). One boot of profile x24-notice-b
(fixture two, admin -debug then bob release, Nutrition false, DayLength 1 in the profile, gclog true). Artifact: `notice.json`, the
staged MANIFEST.json, the server's gc.log and every client ring document (`posring/world-posring-<arm>_<user>.json`)
copied byte-identical beside it. Shape: x244a_notice.py (its sibling, a copy with
PREFIX, PROFILE, SLOW_MULT, MIN_MINUTE_FRAMES and this docstring changed, and, after x244a's run showed the two
players 248 tiles apart and bob's ring empty, the RCON teleport in S0 and the empty-series guard in the rule added
before this driver's boot) and x243c_shootout.py's phase M. Written BEFORE the boot with
every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2). The driver asserts that its PREFIX
and PROFILE match its own file name (H3 session b's slip).

THE SERVER INSTRUMENT, THE CALIBRATION AND THE POPULATIONS: as x243a_shootout.py's docstring states them (tick.ring,
perf.local, ghost.load ... feed, ghost.stats reset between arms, no ghost.bench; ring frames and perf windows minus
the spans of the server bus steps inside an arm; adds against this session's own idle arm over the same population;
the p99 rules on the ring's end-to-end period, the max rules on the perf.local window max). The two real players stay
on the mod's OWN drain throughout; the ghosts are cost, not behaviour.

THE CLIENT INSTRUMENT (the harness at e15a9ca): `world.posring <n> pace <dx>` on each client arms a ring of that
client's OnTick frames: the wall (getTimestampMs, the same host clock as the server's ring), the remote player's
position (thousandths of a tile), the remote player's getLastRemoteUpdate() stamp (set to System.currentTimeMillis()
by GameClient.rememberPlayerPosition when a PlayerPacket is processed on that client, jar 42.20.4), and the nearest
zombie's position. `pace <dx>` keeps the local player walking dx tiles out and back with the game's own walk action;
the sign of dx alternates arm by arm so the anchor does not wander. Both clients pace, so each client watches a
moving remote player.

UPDATE GAPS (graded off the client ring documents; the frames inside the server ring's kept span only):
  stamp gaps    the times between successive distinct getLastRemoteUpdate() stamps (each stamp is a received player
                packet's processing time on that client). THE PRIMARY SERIES.
  move gaps     the times between successive client frames in which the remote player's position changed.
  frame gaps    the client's own frame intervals (a client-side hitch reading).
  A gap is the interval (previous event, event). A gap that overlaps a server bus step's span is dropped. A gap is
  LINED UP with a minute frame when it overlaps a server minute frame's [start - ALIGN_MS, stop + ALIGN_MS] (within
  +-1 server frame). The CHANCE CONTROL counts the same gaps against the minute frames shifted by half the mean
  minute spacing. Per series: p50, p99, max, the count of gaps >= GAP_MS, the count of those lined up, the count of
  every gap lined up, and the control counts.

THE CLIENT RULE (plan Task H4 Step 3; the amendments), per client, on the stamp gaps:
  SHOWS(arm)  lined-up gaps >= 100 ms number at least half the arm's minute frames AND more than twice the control.
  NONE(arm)   lined-up gaps >= 100 ms per minute frame exceed the idle arm's rate by at most 0.05.
  The burst is evidence for (b) on a client when all three burst draws SHOW and all three budget15 draws are NONE.
  If no burst draw and no budget15 draw SHOWS, a frame below the burst's length is not noticeable at this load
  through this reading. Anything else is mixed. Both clients are reported; the session outcome is the clients'
  common outcome, else mixed.

DECISION 6 (ruling 2), the three draws: for every burst and budget15 draw the adds over idle at p99 (ring endPeriod)
and at the max (perf windows); starvation; ghost ms per minute event (ghost.stats ms / minuteEventsSince) and busy a
game minute over idle. budget15 meets (b)'s peak clauses when every draw adds <= 20 ms at p99 and <= 25 ms at the max;
its total clause when its mean ghost ms per minute event is <= 1.1 x the bursts' mean (busy a game minute reported
beside it). The empty-check clause is not measured here (ruling H4-1 leaves it to Plan 11).

PHASES: S0, then M (tick.ring 200, time.multiplier SLOW_MULT, 12 s of wall, TK.H0.tpmSeen, a 5 s rate probe), then the
arms, then Z. S0 is (ready marks, verify rows, players, time, perf.local now, both clients' player.stats and their distance;
wait until both records exist and the mod's minute ran MIN_RUNS times), then the arms in ARMS, then Z. Each arm:
ghost.load N <sched> feed and ghost.stats reset (not for idle); world.posring CLIENT_RING_N pace +-PACE_DX on admin
then bob; perf.local PERF_N; tick.ring RING_N; ARM_WALL_S of wall with NO server bus traffic; perf.local read,
tick.ring read, ghost.stats; world.posring read on admin then bob; ghost.stop.

S0 TELEPORT (added after x244a, before this boot): x244a found admin and bob 248 tiles apart at spawn, so admin's ring
read bob only through the far-player updates (about 2.5 a second, whole-tile positions) and bob's ring never saw admin.
S0 here sends RCON `teleport "bob" "admin"` (TeleportPlayerCommand, `/teleport user1 user2`), waits TELEPORT_WAIT_S,
re-reads both positions, and if they are still over NEAR_TILES apart sends `teleport bob admin` once and re-reads.
The client rule treats an empty stamp series as unmeasured (x244a's bob was graded on an empty series).

DEVIATIONS (stated before the run): no zombie is spawned. Fixture two's sandbox has Zombies = 6 (none), the only
spawner (zombie.near) places zombies one tile from the first player, and the harness has no god mode, so a 15-minute
session would put both subjects under attack; the zombie columns are expected to read -1 throughout, and the reading
rests on the remote player (the plan's "or"). The players pace rather than stand (the amendments: bob keeps walking).

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  I     idle: ring busy p99 <= 10 ms and period p50 within 99..101 ms.
  F     every arm keeps >= 1000 ring frames and >= MIN_MINUTE_FRAMES (20) minute frames (about 27 at 37 ticks a
        minute: a minute-frame p99 is not reachable, so the minute frames' max is the reading).
  C     every client ring: >= 1000 client frames inside the span, the remote player present in >= 90 % of them,
        posring errors 0, pace queued > 0, and >= 100 stamp gaps.
  RULE  session outcome "evidence for (b)" on both clients (the burst's minute frames lengthen the end-to-end period
        by about 42-44 ms at the 37-tick spacing, x243c, to a 161 ms longest window; a player packet relayed through such a
        frame waits for it).
  A6    every burst draw adds more than 25 ms at the perf windows' max over idle.
  B15P  every budget15 draw adds <= 20 ms at the ring endPeriod p99 and <= 25 ms at the perf windows' max.
  B15S  every budget15 draw: starvedEvents 0.
  TOT   budget15's mean ghost ms per minute event <= 1.1 x the bursts' mean.
  S     every arm: failures 0, storeGhostKeys 0, neverRun 0.
  G     gc.log exists; no pause over 1 ms inside any arm.
  Z     no mod error line; admin not parked.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time. 4. A session killed
by the host is reported, and its measured arms are never re-run to replace their figures (ruling H2-1).
"""
import ctypes
import glob
import hashlib
import json
import math
import os
import re
import shutil
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.bus import resolve_side                                # noqa: E402
from pzt.harness import lint_paths                              # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, attach_clients, make_server,  # noqa: E402
                         teardown, verify)


PROFILE = "x24-notice-b"
PREFIX = "x244b"
SLOW_MULT = 0.1674               # #3394: 37 or 38 ticks between consecutive minute events (x243c)
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert PROFILE == "x24-notice-" + PREFIX[-1], f"PROFILE {PROFILE} does not match PREFIX {PREFIX}"
SESSION = ("Plan 10c Task H4 session b: does a player notice the minute burst, and Decision 6's three draws -- "
           "at time.multiplier 0.1674 (37 ticks a game minute) idle, then burst, budget15, burst, budget15, "
           "budget15, burst at N = 60, each about 1000 "
           "frames, both clients recording a frame ring of the other player -- on the uninstrumented staged copy at "
           "9578eb9; one boot of " + PROFILE)
ARTIFACT = "notice.json"
MANIFEST_NAME = "MANIFEST.json"
GCLOG = "gc.log"
POSRING_DIR = "posring"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (ADMIN, BOB)
USERS = ("admin", "bob")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/hitch-9578eb9/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_AT = "9578eb9"
MANIFEST_SHA256 = "c86e295a3ef4c70bde57ab436c9dc3919172dd81db2a8a71164659d62415b389"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_SERVER = LUA_DIR + "/server/PZTestKit_Server.lua"
HARNESS_CLIENT_BODY = LUA_DIR + "/client/PZTestKit_Client_Body.lua"
NR = "NutritionRevamp"
N = 60
REALS = 2
ARMS = (("I", None), ("burst1", "burst"), ("b15_1", "budget15"), ("burst2", "burst"), ("b15_2", "budget15"),
        ("b15_3", "budget15"), ("burst3", "burst"))
BURSTS = ("burst1", "burst2", "burst3")
B15S = ("b15_1", "b15_2", "b15_3")
ARM_WALL_S = 101.5               # about 1020 frames at the ten-tick lock
RING_N = 1500
PERF_N = 400
CLIENT_RING_N = 20000
PACE_DX = 6
GAP_MS = 100
ALIGN_MS = 100                   # +-1 server frame around a minute frame
MIN_FRAMES = 1000
MIN_MINUTE_FRAMES = 20
MIN_CLIENT_FRAMES = 1000
MIN_STAMP_GAPS = 100
OTHER_PRESENT = 0.9
SHOW_RATE = 0.5
SHOW_OVER_CONTROL = 2.0
NONE_MARGIN = 0.05
S0_WAIT_S = 90.0
TELEPORT_WAIT_S = 20.0
NEAR_TILES = 20.0
MIN_RUNS = 4
MIN_FREE_GB = 12.0
RESULT_WAIT_S = 30.0
CLIENT_RESULT_WAIT_S = 60.0
POLL_S = 0.5
LOG_LIMIT = 400
FED_MS = 0.826                   # x242b phases.F.fed.stop.stats: batch-timed fed ghost ms a run
BAND = (0.72, 1.0)               # a fed ghost against a real player's minute (the H2b review)
IDLE_BUSY_P99_MAX = 10
IDLE_PERIOD_BAND = (99, 101)
RULE_P99 = 20.0                  # ruling 2: (b) adds at most 20 ms at p99
RULE_MAX = 25.0                  # ruling 2: (b) adds at most 25 ms at the max; (a) the burst at most 25 ms
RULE_ALT_ADD = 33.0              # ruling 2: the alternative adds more than 33 ms ...
RULE_ALT_FRAME = 133.0           # ... or pushes a frame over 133 ms
RULE_TOTAL = 1.1                 # ruling 2: the scheduler's total at most 1.1 x the burst's
GC_PAUSE_MAX = 1.0
GC_NEAR_MS = 1000
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
MOD_LIFE_RX = re.compile(r"minute: \w+ failed|players: hook failed|fast: |options: |effects: .* failed|"
                         r"nutrients: .* failed|metabolism: .* failed|non-finite")
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")
GC_UP_RX = re.compile(r"^\[(\d+(?:\.\d+)?)s\]")
GC_PAUSE_RX = re.compile(r"Pause [^\n]*?(\d+(?:\.\d+)?)ms\s*$")
GC_STALL_RX = re.compile(r"Allocation Stall \([^)]*\) (\d+(?:\.\d+)?)ms")
GHOST_KEYS = ("scheduler", "ghosts", "runs", "failures", "lastError", "ms", "usPerRun", "minuteEvents",
              "minuteEventsSince", "tpmLast", "meanMs", "queued", "starvedEvents", "starvedMinutes",
              "maxStaleMinutes", "neverRun", "maxStaleGameMinutes", "staleGameNowMax", "frames", "framesWithRuns",
              "maxRunsPerFrame", "meanRunsPerRunFrame", "meanRunsPerFrame", "suppressed", "syncs", "bodySyncs",
              "dropped", "yielded", "feed", "tpmSeed", "tpmSource", "storeGhostKeys", "wallSinceLoad",
              "gameMinutesSinceLoad")

prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir(PREFIX)
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, clients, started = None, {}, []
cur_phase = {"name": "pre"}
launch = {"epoch_ms": None}
client_docs = {}                 # (arm, user) -> the parsed client ring document (kept out of notice.json)


def wall():
    return round(time.time() - t0, 3)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class _MemStat(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def free_gb():
    try:
        m = _MemStat()
        m.dwLength = ctypes.sizeof(m)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return round(m.ullAvailPhys / float(2 ** 30), 2)
    except Exception:                          # noqa: BLE001 - a missing reading is recorded as None
        return None


PRED = {
    "I": {"busy p99": f"<= {IDLE_BUSY_P99_MAX}", "period p50": list(IDLE_PERIOD_BAND)},
    "F": {"kept ring frames": f">= {MIN_FRAMES}", "kept minute frames": f">= {MIN_MINUTE_FRAMES}"},
    "C": {"client frames in span": f">= {MIN_CLIENT_FRAMES}", "remote present": f">= {OTHER_PRESENT}",
          "posring errors": 0, "pace queued": "> 0", "stamp gaps": f">= {MIN_STAMP_GAPS}"},
    "RULE": {"session outcome": "evidence for (b) on both clients"},
    "A6": {"every burst draw perf max adds at max": f"> {RULE_MAX}"},
    "B15P": {"every budget15 draw endPeriod p99 adds": f"<= {RULE_P99}", "perf max adds at max": f"<= {RULE_MAX}"},
    "B15S": {"every budget15 draw starvedEvents": 0},
    "TOT": {"budget15 mean ghost ms per minute event / bursts' mean": f"<= {RULE_TOTAL}"},
    "S": {"failures": 0, "storeGhostKeys": 0, "neverRun": 0},
    "G": {"gc.log": "exists", "pause max inside an arm": f"<= {GC_PAUSE_MAX} ms"},
    "Z": {"mod_error": "none", "admin_lua_error": False},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "users": list(prof.users), "profile": prof.report(),
    "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                "clients": {u: {"debug": (rec_fx.get("clients") or {}).get(u, {}).get("debug")}
                            for u in (rec_fx.get("clients") or {})}},
    "argv": sys.argv[1:],
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", MOD_DIR),
    "mod_dirty_not_booted": git_dirty(MOD_DIR)[0],
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "meta": {"staged_mod": STAGE_MOD, "staged_at": STAGED_AT, "staged_manifest": f"{STAGE_ROOT}/{MANIFEST_NAME}",
             "staging": "staged by Plan 10c Task 0 with no instrument added (the uninstrumented copy)",
             "calibration_note": "x242b F: a fed ghost is about one real player's minute, band 0.72..1.0; the "
                                 "fed batch-timed ghost cost was 0.826 ms a run. No ghost.bench in this session.",
             "cost_note": "Every server reading is cost, not behaviour: the ghosts run copies of the real records "
                          "against the two real IsoPlayers (their Java writes land on the carriers). The two real "
                          "players stay on the mod's own drain throughout. No behaviour row rests on this session.",
             "client_note": "The client rings are the clients' own OnTick frames on the same host clock as the "
                            "server ring (getTimestampMs is System.currentTimeMillis on each process). The stamp "
                            "series is getLastRemoteUpdate() of the remote player, set when that client processes a "
                            "PlayerPacket (GameClient.rememberPlayerPosition, jar 42.20.4).",
             "timer_note": "getTimestampMs is 1 ms resolution: a frame's busy is a 1 ms reading; every per-run cost "
                           "is a total over many runs divided by their count."},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [
        "No zombie is spawned: fixture two's sandbox has Zombies = 6 (none), zombie.near places zombies one tile "
        "from the first player and the harness has no god mode, so a 15-minute session would put both subjects "
        "under attack. The zombie columns are expected to read -1; the reading rests on the remote player.",
        "Both players pace (world.posring ... pace +-6) rather than stand, so each client watches a moving remote "
        "player (the amendments: bob keeps walking).",
    ],
    "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {}, "summaries": {},
    "memory": [],
}
try:
    out["meta"]["harness_server_sha256"] = sha256_file(os.path.join(REPO, HARNESS_SERVER))
    out["meta"]["harness_client_body_sha256"] = sha256_file(os.path.join(REPO, HARNESS_CLIENT_BODY))
    out["meta"]["staged_manifest_sha256"] = sha256_file(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME))
    out["meta"]["staged_manifest_expected"] = MANIFEST_SHA256
except OSError as e:
    out["meta"]["hash_error"] = f"{type(e).__name__}: {e}"


def mem(tag):
    row = {"tag": tag, "wall": wall(), "free_gb": free_gb()}
    out["memory"].append(row)
    return row


def grep_noecho(log, rx, limit):
    hits, skipped = [], 0
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not rx.search(line):
                    continue
                if ECHO_RX.search(line):
                    skipped += 1
                    continue
                hits.append(line.strip()[:600])
                if len(hits) >= limit:
                    break
    except OSError:
        pass
    return hits, skipped


def note(msg):
    out["notes"].append({"wall": wall(), "phase": cur_phase["name"], "note": msg})


def persist():
    try:
        out["timeline"] = list(tl.items)
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=str)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def node(side):
    return resolve_side(side, server, clients)


def step(name, side, cmd, args="", timeout=30):
    t_before, e_before = wall(), time.time()
    try:
        n = node(side)
        v = ask(n, cmd, args, timeout=timeout)
    except Exception as e:                     # noqa: BLE001 - an unknown side is a recorded fault
        v = {"error": f"{type(e).__name__}: {e}"}
    t_after = wall()
    row = {"step": name, "side": side, "cmd": cmd, "args": args, "phase": cur_phase["name"],
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": int(e_before * 1000),
           "epoch_ms_after": int(time.time() * 1000), "took": round(t_after - t_before, 3), "ack": v}
    if not isinstance(v, dict):
        row["ack_shape"] = type(v).__name__
    out["steps"].append(row)
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def keep(r):
    a = dict(ack(r))
    a["wall"] = r["wall_before"]
    a["wall_after"] = r["wall_after"]
    a["epoch_ms_before"] = r.get("epoch_ms_before")
    a["epoch_ms_after"] = r.get("epoch_ms_after")
    a["side"] = a.get("side", r["side"])
    if not isinstance(r.get("ack"), dict):
        a["raw"] = r.get("ack")
    return a


def gread(side, name, tag):
    r = step(tag, side, "lua.global", name)
    a = ack(r)
    row = {"name": name, "side": side, "wall": r["wall_before"], "wall_after": r["wall_after"],
           "resolved": a.get("resolved"), "type": a.get("type")}
    for k in ("value", "keyCount", "failedAt", "stoppedOn", "error"):
        if k in a:
            row[k] = a.get(k)
    if not isinstance(r.get("ack"), dict):
        row["raw"] = r.get("ack")
    return row


def val(row):
    if not isinstance(row, dict) or not row.get("resolved"):
        return None
    return row.get("value")


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def who(side):
    return side.split(":", 1)[1] if side.startswith("client:") else side


def parked():
    c = clients.get("admin") if isinstance(clients, dict) else None
    return c is not None and "lua_error" in getattr(c, "seen", {})


def minstats(tag):
    d = {k: num(val(gread(SRV, f"{NR}.server.minute.stats.{k}", f"{tag}_min_{k}"))) for k in ("runs", "failures")}
    for k in ("minutes", "drained"):
        d[f"players_{k}"] = num(val(gread(SRV, f"{NR}.server.players.{k}", f"{tag}_p_{k}")))
    return d


def snap(tag):
    return keep(step(tag, SRV, "time.snapshot"))


def wait_doc(name, after, side=SRV, timeout=RESULT_WAIT_S):
    try:
        return node(side).bus.wait_result(name, timeout=timeout, after=after)
    except Exception as e:                     # noqa: BLE001 - a missing document is a recorded fault
        note(f"result {name} on {side}: {type(e).__name__}: {e}")
        return None


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier, "observed": observed,
           "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)


def run_phase(name, fn):
    cur_phase["name"] = name
    out["phase_walls"][name] = {"start": wall()}
    try:
        fn()
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    out["phase_walls"][name]["end"] = wall()
    persist()


def span(r):
    return [r.get("epoch_ms_before"), r.get("epoch_ms_after")]


def client_doc(tag, side, after):
    """Read one client ring document, copy its file byte-identical into the run dir's posring folder, keep the
    parsed document in memory for grading, and return its header (frames_list left out of notice.json)."""
    user = who(side)
    name = f"world-posring-{tag}_{user}"
    d = wait_doc(name, after, side, CLIENT_RESULT_WAIT_S)
    row = {"name": name, "present": d is not None}
    if d is None:
        return row
    client_docs[(tag, user)] = d
    src = os.path.join(node(side).bus.results_dir, name + ".json")
    dst_dir = os.path.join(run_dir, POSRING_DIR)
    try:
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copyfile(src, os.path.join(dst_dir, name + ".json"))
        row["file"] = f"{POSRING_DIR}/{name}.json"
        row["sha256"] = sha256_file(os.path.join(dst_dir, name + ".json"))
    except OSError as e:
        row["copy_error"] = f"{type(e).__name__}: {e}"
    for k, v in d.items():
        if k != "frames_list":
            row[k] = v
    return row


# ---------------------------------------------------------------- the arm
def run_arm(tag, n, sched, k, wall_s=ARM_WALL_S):
    """One arm. sched None is an idle arm (no load). Server bus traffic inside the window: the ring arm only, before
    it the perf arm, after it the perf read; their spans are the arm's drop windows. The client rings are armed before
    the server's perf and ring arms and read after the server's reads."""
    A = out["phases"][tag] = {"tag": tag, "N": n if sched else None, "sched": sched, "mem_before": mem(f"{tag}_0")}
    if sched is not None:
        A["load"] = keep(step(f"{tag}_load", SRV, "ghost.load", f"{n} {sched} feed", timeout=60))
        if not A["load"].get("ok"):
            note(f"{tag}: ghost.load failed: {A['load'].get('reason') or A['load'].get('raw')}")
        A["reset"] = keep(step(f"{tag}_reset", SRV, "ghost.stats", "reset"))
    dx = PACE_DX if k % 2 == 0 else -PACE_DX
    A["pace_dx"] = dx
    A["client_arm"] = {who(s): keep(step(f"{tag}_cring_{who(s)}", s, "world.posring", f"{CLIENT_RING_N} pace {dx}"))
                       for s in CLIENT_SIDES}
    A["perf_arm"] = keep(step(f"{tag}_perf_arm", SRV, "perf.local", str(PERF_N)))
    A["ring_arm"] = keep(step(f"{tag}_ring_arm", SRV, "tick.ring", str(RING_N)))
    A["window_start_wall"] = wall()
    time.sleep(wall_s)
    A["window_end_wall"] = wall()
    after = time.time() - 1.0
    A["perf_read"] = keep(step(f"{tag}_perf_read", SRV, "perf.local", f"read {tag}"))
    A["ring_read"] = keep(step(f"{tag}_ring_read", SRV, "tick.ring", f"read {tag}"))
    if sched is not None:
        A["stats"] = keep(step(f"{tag}_stats", SRV, "ghost.stats"))
    A["client_read"] = {who(s): keep(step(f"{tag}_cread_{who(s)}", s, "world.posring", f"read {tag}_{who(s)}",
                                          timeout=60)) for s in CLIENT_SIDES}
    A["perf_doc"] = wait_doc(f"perf-local-{tag}", after)
    A["ring_doc"] = wait_doc(f"tick-ring-{tag}", after)
    A["client_docs"] = {who(s): client_doc(tag, s, after) for s in CLIENT_SIDES}
    if sched is not None:
        A["stop"] = keep(step(f"{tag}_stop", SRV, "ghost.stop"))
        out["world_changes"]["left_in_place"].append(f"{tag}: {n - REALS} ghost records ran against admin and bob "
                                                     f"under {sched} (their Java writes land on the carriers)")
    A["drop_windows"] = [span(A["ring_arm"]), span(A["perf_read"])]
    A["mem_after"] = mem(f"{tag}_1")
    persist()
    return A


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    P["players"] = keep(step("S0_players", SRV, "players"))
    P["time"] = snap("S0_time")
    P["perf_now"] = keep(step("S0_perf_now", SRV, "perf.local", "now"))
    P["mode"] = gread(SRV, f"{NR}.server.options.mode", "S0_mode")
    P["seen"] = {who(s): dict(getattr(node(s), "seen", {})) for s in CLIENT_SIDES}
    P["pos"] = {who(s): keep(step(f"S0_pos_{who(s)}", s, "player.stats")) for s in CLIENT_SIDES}
    try:
        a, b = P["pos"]["admin"], P["pos"]["bob"]
        P["distance"] = math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))
    except (KeyError, TypeError, ValueError):
        P["distance"] = None
    P["teleports"] = []
    for cmd in ('teleport "bob" "admin"', "teleport bob admin"):
        P["teleports"].append(rcon(cmd, "S0_teleport"))
        out["world_changes"]["left_in_place"].append(f"S0: RCON {cmd}")
        time.sleep(TELEPORT_WAIT_S)
        pos = {who(s): keep(step(f"S0_pos2_{who(s)}", s, "player.stats")) for s in CLIENT_SIDES}
        try:
            dist = math.hypot(float(pos["admin"]["x"]) - float(pos["bob"]["x"]),
                              float(pos["admin"]["y"]) - float(pos["bob"]["y"]))
        except (KeyError, TypeError, ValueError):
            dist = None
        P["teleports"][-1]["pos"] = pos
        P["teleports"][-1]["distance"] = dist
        P["distance_after"] = dist
        if dist is not None and dist <= NEAR_TILES:
            break
    if P.get("distance_after") is None or P["distance_after"] > NEAR_TILES:
        note(f"S0: the players are not within {NEAR_TILES} tiles after the teleports: {P.get('distance_after')}")
    end = time.time() + S0_WAIT_S
    polls = []
    while True:
        recs = {u: gread(SRV, f"{NR}.server.store.records.{u}", f"S0_rec_{u}") for u in USERS}
        runs = num(val(gread(SRV, f"{NR}.server.minute.stats.runs", "S0_runs")))
        ok = all(r.get("resolved") for r in recs.values()) and runs is not None and runs >= MIN_RUNS
        polls.append({"wall": wall(), "records": {u: r.get("resolved") for u, r in recs.items()}, "runs": runs})
        if ok or time.time() >= end:
            break
        time.sleep(POLL_S)
    P["wait"] = {"ok": ok, "polls": polls}
    if not ok:
        note("S0: the real players' records or MIN_RUNS were not reached inside S0_WAIT_S")
    P["minstats"] = minstats("S0")


def rcon(cmd, tag):
    t_before, e_before = wall(), time.time()
    try:
        ok, rep = server.rcon(cmd)
    except Exception as e:                     # noqa: BLE001
        ok, rep = False, f"{type(e).__name__}: {e}"
    row = {"step": tag, "side": SRV, "cmd": "rcon", "args": cmd, "phase": cur_phase["name"], "wall_before": t_before,
           "wall_after": wall(), "epoch_ms_before": int(e_before * 1000), "epoch_ms_after": int(time.time() * 1000),
           "ack": {"ok": ok, "reply": str(rep)[:300]}}
    out["steps"].append(row)
    tl.mark("rcon", cmd=cmd, ok=ok)
    return {"cmd": cmd, "ok": ok, "reply": str(rep)[:300], "wall": t_before, "epoch_ms_before": row["epoch_ms_before"],
            "epoch_ms_after": row["epoch_ms_after"]}


def rate_probe(tag):
    a = snap(f"{tag}_t0")
    time.sleep(5.0)
    b = snap(f"{tag}_t1")
    wa, wb = num(a.get("worldAge")), num(b.get("worldAge"))
    ea, eb = a.get("epoch_ms_before"), b.get("epoch_ms_before")
    r = {"t0": a, "t1": b}
    if None not in (wa, wb, ea, eb) and eb > ea:
        r["world_minutes_per_s"] = (wb - wa) * 60.0 / ((eb - ea) / 1000.0)
    return r


def phase_M():
    P = out["phases"]["M"] = {}
    P["hooks"] = keep(step("M_ring", SRV, "tick.ring", "200"))
    P["mult"] = keep(step("M_mult", SRV, "time.multiplier", str(SLOW_MULT)))
    out["world_changes"]["left_in_place"].append(f"M: time.multiplier {SLOW_MULT} from here to the end")
    time.sleep(12.0)
    P["tpm"] = gread(SRV, "TK.H0.tpmSeen", "M_tpm")
    P["rate"] = rate_probe("M")


def make_arm(tag, sched, k):
    def fn():
        run_arm(tag, N, sched, k)
    return fn


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["stop_left"] = keep(step("Z_stop", SRV, "ghost.stop"))
    P["client_off"] = {who(s): keep(step(f"Z_coff_{who(s)}", s, "world.posring", "off")) for s in CLIENT_SIDES}
    P["players"] = keep(step("Z_players", SRV, "players"))
    P["time"] = snap("Z_time")
    P["minstats"] = minstats("Z")
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:20]
    P["admin_parked"] = parked()
    P["mem"] = mem("Z")


def body():
    order = [("S0", phase_S0)]
    if SLOW_MULT is not None:
        order.append(("M", phase_M))
    order += [(tag, make_arm(tag, sched, k)) for k, (tag, sched) in enumerate(ARMS)] + [("Z", phase_Z)]
    for name, fn in order:
        run_phase(name, fn)
        if parked() and name != "Z":
            out["abort"] = f"admin parked in the debugger after phase {name}"
            run_phase("Z", phase_Z)
            return


def read_logs(every):
    L = out["logs"] = {"patterns": {"life": MOD_LIFE_RX.pattern, "log": LOG_RX.pattern, "echo_excluded": ECHO_RX.pattern},
                       "limits": {"log": LOG_LIMIT}, "clients": {}}
    if server is not None:
        life, life_echo = grep_noecho(server.log_path, MOD_LIFE_RX, LOG_LIMIT)
        raw, echoed = grep_noecho(server.log_path, LOG_RX, LOG_LIMIT)
        L["server"] = {"life_lines": life, "life_echo_excluded": life_echo, "lines": raw, "echo_lines_excluded": echoed}
    for c in every:
        u = getattr(c, "username", "?")
        lines, ech = grep_noecho(c.console, LOG_RX, 60)
        L["clients"].setdefault(u, []).append({"console": os.path.relpath(c.console, run_dir), "lines": lines,
                                               "echo_lines_excluded": ech})


def read_gc():
    p = os.path.join(run_dir, GCLOG)
    G = out["gc"] = {"path": "gc.log (run dir)", "exists": os.path.isfile(p), "launch_epoch_ms": launch["epoch_ms"]}
    if not G["exists"]:
        return
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError as e:
        G["error"] = f"{type(e).__name__}: {e}"
        return
    events = []
    for ln in lines:
        mu = GC_UP_RX.search(ln)
        if not mu:
            continue
        up_ms = float(mu.group(1)) * 1000.0
        ms = GC_STALL_RX.search(ln)
        mp = GC_PAUSE_RX.search(ln)
        if ms:
            events.append({"kind": "stall", "up_ms": up_ms, "ms": float(ms.group(1)), "line": ln[:200]})
        elif mp:
            events.append({"kind": "pause", "up_ms": up_ms, "ms": float(mp.group(1)), "line": ln[:200]})
    if launch["epoch_ms"] is not None:
        for e in events:
            e["epoch_ms"] = launch["epoch_ms"] + e["up_ms"]
    pauses = [e["ms"] for e in events if e["kind"] == "pause"]
    stalls = [e["ms"] for e in events if e["kind"] == "stall"]
    G.update({"bytes": os.path.getsize(p), "lines": len(lines), "pause_events": len(pauses),
              "pause_max_ms": max(pauses) if pauses else None, "pause_sum_ms": sum(pauses) if pauses else None,
              "stall_events": len(stalls), "stall_max_ms": max(stalls) if stalls else None,
              "events": events})


# ---------------------------------------------------------------- grading
def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def pct(xs, p):
    s = sorted(xs)
    if not s:
        return None
    k = max(1, min(len(s), math.ceil(round(p * len(s), 9))))
    return s[k - 1]


def summ(xs):
    xs = [x for x in xs if x is not None]
    return {"n": len(xs), "p50": pct(xs, 0.5), "p99": pct(xs, 0.99), "max": max(xs) if xs else None,
            "min": min(xs) if xs else None, "mean": (sum(xs) / len(xs)) if xs else None, "sum": sum(xs) if xs else 0,
            "p99_reachable": len(xs) >= 100}


def frames_of(doc):
    F = (doc or {}).get("frames_list") or {}
    keys = ("frame", "start", "stop", "busy", "period", "endPeriod", "minute", "runs", "ghostMs")
    cols = [F.get(k) or [] for k in keys]
    n = min(len(c) for c in cols) if cols else 0
    return [dict(zip(keys, (c[i] for c in cols))) for i in range(n)]


def hits(lo, hi, wins):
    for w in wins or []:
        if w[0] is None or w[1] is None or lo is None or hi is None:
            continue
        if lo <= w[1] and hi >= w[0]:
            return True
    return False


def arm_frames(A):
    fr = frames_of(A.get("ring_doc"))
    wins = A.get("drop_windows") or []
    kept = [f for f in fr if f["busy"] is not None and f["busy"] >= 0 and not hits(f["start"], f["stop"], wins)]
    return fr, kept


def perf_windows(A):
    S = (A.get("perf_doc") or {}).get("samples_list") or {}
    w, mx = S.get("wall") or [], S.get("max") or []
    wins = A.get("drop_windows") or []
    rows = []
    for k in range(1, min(len(w), len(mx))):
        rows.append({"k": k, "lo": w[k - 1], "hi": w[k], "max": mx[k], "drop": hits(w[k - 1], w[k], wins)})
    return rows


def gc_in(lo, hi):
    ev = g(out, "gc", "events") or []
    return [e for e in ev if e.get("epoch_ms") is not None and lo is not None and hi is not None
            and lo <= e["epoch_ms"] <= hi]


def arm_summary(A, idle=None):
    fr, kept = arm_frames(A)
    busy = [f["busy"] for f in kept]
    mins = [f for f in kept if f["minute"] == 1]
    rest = [f for f in kept if f["minute"] != 1]
    endp = [f["endPeriod"] for f in kept if f["endPeriod"] is not None and f["endPeriod"] >= 0]
    per = [f["period"] for f in kept if f["period"] is not None and f["period"] >= 0]
    pw = perf_windows(A)
    pk = [r for r in pw if not r["drop"]]
    st = A.get("stats") or {}
    S = {"N": A.get("N"), "sched": A.get("sched"), "frames_ring": len(fr), "frames": len(kept),
         "frames_dropped": len(fr) - len(kept), "minute_frames": len(mins),
         "busy": summ(busy), "busy_minute": summ([f["busy"] for f in mins]),
         "busy_other": summ([f["busy"] for f in rest]), "endPeriod": summ(endp), "period": summ(per),
         "endPeriod_over110": sum(1 for x in endp if x > 110), "endPeriod_over133": sum(1 for x in endp if x > 133),
         "busy_sum": sum(busy), "busy_ms_per_frame": (sum(busy) / len(busy)) if busy else None,
         "busy_ms_per_game_minute": (sum(busy) / len(mins)) if mins else None,
         "ghostMs_sum": sum((f["ghostMs"] or 0) for f in kept), "runs_sum": sum((f["runs"] or 0) for f in kept),
         "ghostMs_minute": summ([f["ghostMs"] for f in mins]), "runs_frame": summ([f["runs"] for f in kept]),
         "perf_windows": len(pw), "perf_kept": len(pk), "perf_max": summ([r["max"] for r in pk]),
         "perf_over133": sum(1 for r in pk if (r["max"] or 0) > 133),
         "top5_endPeriod": [{k: f[k] for k in ("frame", "start", "busy", "period", "endPeriod", "minute", "runs",
                                                 "ghostMs")} for f in sorted(kept, key=lambda f: -(f["endPeriod"] or -1))[:5]]}
    if mins:
        S["ghost_ms_per_game_minute_ring"] = S["ghostMs_sum"] / len(mins)
    if st.get("ok"):
        S["ghost"] = {k: st.get(k) for k in GHOST_KEYS}
        runs, ms = num(st.get("runs")), num(st.get("ms"))
        S["ghost_ms_per_run"] = (ms / runs) if runs else None
        mev = num(st.get("minuteEventsSince"))
        S["ghost_ms_per_minute_event"] = (ms / mev) if mev else None
        S["ghost_runs_per_minute_event"] = (runs / mev) if mev else None
        if A.get("N"):
            S["n_eq_band"] = [REALS + (A["N"] - REALS) * BAND[0], REALS + (A["N"] - REALS) * BAND[1]]
            if S["ghost_ms_per_run"]:
                S["ghost_over_fed_calibration"] = S["ghost_ms_per_run"] / FED_MS
    if kept:
        lo, hi = kept[0]["start"], kept[-1]["stop"]
        ev = gc_in(lo, hi)
        S["gc"] = {"pauses": sum(1 for e in ev if e["kind"] == "pause"),
                   "pause_max_ms": max([e["ms"] for e in ev if e["kind"] == "pause"], default=None),
                   "stalls": sum(1 for e in ev if e["kind"] == "stall"),
                   "stall_max_ms": max([e["ms"] for e in ev if e["kind"] == "stall"], default=None)}
    if idle:
        S["adds"] = {}
        for pop in ("busy", "busy_minute", "endPeriod", "perf_max"):
            a, b = S.get(pop) or {}, idle.get(pop) or {}
            S["adds"][pop] = {q: (a[q] - b[q]) if a.get(q) is not None and b.get(q) is not None else None
                              for q in ("p50", "p99", "max")}
        for k in ("busy_ms_per_game_minute", "busy_ms_per_frame"):
            if S.get(k) is not None and idle.get(k) is not None:
                S["adds"][k] = S[k] - idle[k]
    return S


# ---------------------------------------------------------------- client gaps
def union_len(ivs, lo, hi):
    tot, cur_lo, cur_hi = 0, None, None
    for a, b in sorted((max(a, lo), min(b, hi)) for a, b in ivs if b >= lo and a <= hi):
        if cur_hi is None or a > cur_hi:
            if cur_hi is not None:
                tot += cur_hi - cur_lo
            cur_lo, cur_hi = a, b
        else:
            cur_hi = max(cur_hi, b)
    if cur_hi is not None:
        tot += cur_hi - cur_lo
    return tot


def lined(a, b, wins):
    for w in wins:
        if a <= w[1] and b >= w[0]:
            return True
    return False


def gap_stats(events, minute_wins, shifted_wins, drops, lo, hi, n_minutes):
    """events: sorted event times (ms). A gap is (previous event, event)."""
    gaps = []
    for i in range(1, len(events)):
        a, b = events[i - 1], events[i]
        if b < lo or a > hi or hits(a, b, drops):
            continue
        gaps.append((a, b))
    L = [b - a for a, b in gaps]
    big = [(a, b) for a, b in gaps if b - a >= GAP_MS]
    big_l = [x for x in big if lined(x[0], x[1], minute_wins)]
    big_c = [x for x in big if lined(x[0], x[1], shifted_wins)]
    all_l = sum(1 for a, b in gaps if lined(a, b, minute_wins))
    all_c = sum(1 for a, b in gaps if lined(a, b, shifted_wins))
    top = sorted(gaps, key=lambda x: -(x[1] - x[0]))[:10]
    return {"gaps": summ(L), "ge_gap": len(big), "ge_gap_lined": len(big_l), "ge_gap_control": len(big_c),
            "lined_all": all_l, "control_all": all_c, "minute_frames": n_minutes,
            "ge_gap_lined_per_minute": (len(big_l) / n_minutes) if n_minutes else None,
            "ge_gap_control_per_minute": (len(big_c) / n_minutes) if n_minutes else None,
            "ge200": sum(1 for x in L if x >= 200),
            "top10": [{"from": a, "to": b, "ms": b - a, "lined": lined(a, b, minute_wins)} for a, b in top]}


def client_summary(A, user):
    d = client_docs.get((A["tag"], user))
    fr, kept = arm_frames(A)
    if d is None or not kept:
        return None
    F = d.get("frames_list") or {}
    t = [num(x) for x in (F.get("t") or [])]
    ox, oy = F.get("ox") or [], F.get("oy") or []
    olr = [num(x) for x in (F.get("olr") or [])]
    zx = F.get("zx") or []
    n = min(len(t), len(ox), len(oy), len(olr))
    lo, hi = kept[0]["start"], kept[-1]["stop"]
    idx = [i for i in range(n) if t[i] is not None and lo <= t[i] <= hi]
    mins = [f for f in fr if f["minute"] == 1 and f["start"] is not None and f["stop"] is not None
            and f["stop"] >= lo and f["start"] <= hi]
    wins = [(f["start"] - ALIGN_MS, f["stop"] + ALIGN_MS) for f in mins]
    if len(mins) >= 2:
        spacing = (mins[-1]["start"] - mins[0]["start"]) / (len(mins) - 1)
    else:
        spacing = 0
    shift = spacing / 2.0
    swins = [(a + shift, b + shift) for a, b in wins]
    drops = A.get("drop_windows") or []
    stamps = []
    for i in idx:
        v = olr[i]
        if v is None or v < 0:
            continue
        if not stamps or v != stamps[-1]:
            stamps.append(v)
    moves, prev = [], None
    for i in idx:
        if ox[i] == -1:
            prev = None
            continue
        cur = (ox[i], oy[i])
        if prev is not None and cur != prev:
            moves.append(t[i])
        prev = cur
    frames_t = [t[i] for i in idx]
    S = {"user": user, "frames_doc": n, "frames_in_span": len(idx),
         "other_present": (sum(1 for i in idx if olr[i] is not None and olr[i] >= 0) / len(idx)) if idx else None,
         "zombie_frames": sum(1 for i in idx if i < len(zx) and zx[i] != -1),
         "errors": d.get("errors"), "lastError": d.get("lastError"), "paceQueued": d.get("paceQueued"),
         "paceNoSquare": d.get("paceNoSquare"), "span": [lo, hi], "minute_frames": len(mins),
         "minute_spacing_ms": spacing, "control_shift_ms": shift,
         "minute_window_coverage": (union_len(wins, lo, hi) / float(hi - lo)) if hi > lo else None,
         "stamp": gap_stats(stamps, wins, swins, drops, lo, hi, len(mins)),
         "move": gap_stats(moves, wins, swins, drops, lo, hi, len(mins)),
         "frame": gap_stats(frames_t, wins, swins, drops, lo, hi, len(mins))}
    return S


def shows(cs):
    st = (cs or {}).get("stamp") or {}
    nl, nc, nm = st.get("ge_gap_lined"), st.get("ge_gap_control"), st.get("minute_frames")
    if nl is None or not nm or not g(st, "gaps", "n"):
        return None
    return nl >= SHOW_RATE * nm and nl > SHOW_OVER_CONTROL * (nc or 0)


def none_(cs, idle_cs):
    r = g(cs, "stamp", "ge_gap_lined_per_minute")
    ri = g(idle_cs, "stamp", "ge_gap_lined_per_minute")
    if r is None or ri is None or not g(cs, "stamp", "gaps", "n") or not g(idle_cs, "stamp", "gaps", "n"):
        return None
    return r <= ri + NONE_MARGIN


def mean(xs):
    xs = [x for x in xs if x is not None]
    return (sum(xs) / len(xs)) if xs else None


def grade_all():
    ph = out["phases"]
    S = out["summaries"]
    I = ph.get("I") or {}
    if I.get("ring_doc"):
        S["I"] = arm_summary(I)
        b, p = S["I"]["busy"], S["I"]["period"]
        ok = (b["p99"] is not None and b["p99"] <= IDLE_BUSY_P99_MAX and p["p50"] is not None
              and IDLE_PERIOD_BAND[0] <= p["p50"] <= IDLE_PERIOD_BAND[1])
        grade("I", PRED["I"], {"busy": b, "period": p, "perf_max": S["I"]["perf_max"]},
              "as_predicted" if ok else "falsified", "busy p99 over 10 or period p50 off")
    else:
        grade("I", PRED["I"], None, "unmeasured", "no idle ring document")
    idle = S.get("I")
    tags = [t for t, _s in ARMS if t != "I"]
    for t in tags:
        A = ph.get(t) or {}
        if A.get("ring_doc"):
            S[t] = arm_summary(A, idle)
    have = [t for t in tags if t in S]
    every = ["I"] + have if "I" in S else have
    if have:
        short = {t: [S[t]["frames"], S[t]["minute_frames"]] for t in every
                 if S[t]["frames"] < MIN_FRAMES or S[t]["minute_frames"] < MIN_MINUTE_FRAMES}
        grade("F", PRED["F"], {t: [S[t]["frames"], S[t]["minute_frames"]] for t in every},
              "as_predicted" if not short and len(have) == len(tags) else "falsified", "an arm short", {"short": short})
    else:
        grade("F", PRED["F"], None, "unmeasured", "no arm")
    # the client rings
    C = S["clients"] = {}
    for t, _s in ARMS:
        A = ph.get(t) or {}
        if not A.get("ring_doc"):
            continue
        C[t] = {u: client_summary(A, u) for u in USERS}
    bad = {}
    for t, row in C.items():
        for u, cs in row.items():
            if cs is None:
                bad[f"{t}/{u}"] = "no document"
                continue
            probs = []
            if cs["frames_in_span"] < MIN_CLIENT_FRAMES:
                probs.append(f"frames {cs['frames_in_span']}")
            if (cs["other_present"] or 0) < OTHER_PRESENT:
                probs.append(f"remote present {cs['other_present']}")
            if cs["errors"] not in (0, None):
                probs.append(f"errors {cs['errors']}")
            if not cs["paceQueued"]:
                probs.append("pace queued 0")
            if g(cs, "stamp", "gaps", "n") is None or g(cs, "stamp", "gaps", "n") < MIN_STAMP_GAPS:
                probs.append(f"stamp gaps {g(cs, 'stamp', 'gaps', 'n')}")
            if probs:
                bad[f"{t}/{u}"] = probs
    if C:
        grade("C", PRED["C"], {t: {u: (None if cs is None else {k: cs[k] for k in ("frames_in_span", "other_present",
                                                                                   "errors", "paceQueued")})
                                   for u, cs in row.items()} for t, row in C.items()},
              "as_predicted" if not bad else "falsified", "a client ring short, empty or raising", {"bad": bad})
    else:
        grade("C", PRED["C"], None, "unmeasured", "no client ring")
    # the client rule
    rule = S["client_rule"] = {}
    for u in USERS:
        idle_cs = g(C, "I", u)
        bs = {t: shows(g(C, t, u)) for t in BURSTS}
        b15s = {t: shows(g(C, t, u)) for t in B15S}
        b15n = {t: none_(g(C, t, u), idle_cs) for t in B15S}
        bn = {t: none_(g(C, t, u), idle_cs) for t in BURSTS}
        if None in list(bs.values()) + list(b15n.values()) + list(b15s.values()):
            outcome = "unmeasured"
        elif all(bs.values()) and all(b15n.values()):
            outcome = "evidence for (b)"
        elif not any(bs.values()) and not any(b15s.values()):
            outcome = "not noticeable at this load"
        else:
            outcome = "mixed"
        rule[u] = {"burst_shows": bs, "budget15_shows": b15s, "budget15_none": b15n, "burst_none": bn,
                   "outcome": outcome,
                   "per_minute": {t: g(C, t, u, "stamp", "ge_gap_lined_per_minute") for t, _s in ARMS},
                   "control_per_minute": {t: g(C, t, u, "stamp", "ge_gap_control_per_minute") for t, _s in ARMS}}
    outs = {rule[u]["outcome"] for u in USERS}
    session_outcome = outs.pop() if len(outs) == 1 else "mixed"
    rule["session_outcome"] = session_outcome
    grade("RULE", PRED["RULE"], {u: rule[u]["outcome"] for u in USERS} | {"session": session_outcome},
          "unmeasured" if session_outcome == "unmeasured" else
          ("as_predicted" if session_outcome == "evidence for (b)" else "falsified"),
          "any outcome but evidence for (b) on both clients")
    # Decision 6, the three draws
    D = S["decision6"] = {"draws": {}}
    for t in BURSTS + B15S:
        if t not in S:
            continue
        x = S[t]
        D["draws"][t] = {"adds_p99_endPeriod": g(x, "adds", "endPeriod", "p99"),
                         "adds_max_perf": g(x, "adds", "perf_max", "max"),
                         "perf_max_max": g(x, "perf_max", "max"), "endPeriod_max": g(x, "endPeriod", "max"),
                         "starvedEvents": g(x, "ghost", "starvedEvents"),
                         "starvedMinutes": g(x, "ghost", "starvedMinutes"),
                         "ghost_ms_per_minute_event": x.get("ghost_ms_per_minute_event"),
                         "busy_ms_per_game_minute": x.get("busy_ms_per_game_minute"),
                         "adds_busy_ms_per_game_minute": g(x, "adds", "busy_ms_per_game_minute")}
    dr = D["draws"]
    bm = mean([g(dr, t, "ghost_ms_per_minute_event") for t in BURSTS])
    fm = mean([g(dr, t, "ghost_ms_per_minute_event") for t in B15S])
    bb = mean([g(dr, t, "adds_busy_ms_per_game_minute") for t in BURSTS])
    fb = mean([g(dr, t, "adds_busy_ms_per_game_minute") for t in B15S])
    D["total"] = {"burst_mean_ghost_ms_per_minute_event": bm, "budget15_mean_ghost_ms_per_minute_event": fm,
                  "ratio_ghost_ms_per_minute_event": (fm / bm) if (fm is not None and bm) else None,
                  "burst_mean_adds_busy_per_game_minute": bb, "budget15_mean_adds_busy_per_game_minute": fb,
                  "ratio_adds_busy_per_game_minute": (fb / bb) if (fb is not None and bb) else None}
    have_b = [t for t in BURSTS if t in dr]
    have_f = [t for t in B15S if t in dr]
    if have_b:
        amx = [g(dr, t, "adds_max_perf") for t in have_b]
        ok = len(have_b) == 3 and all(x is not None and x > RULE_MAX for x in amx)
        grade("A6", PRED["A6"], {t: dr[t] for t in have_b}, "as_predicted" if ok else "falsified",
              "a burst draw adds <= 25 at the max")
        D["burst_alternative_clause"] = {t: (g(dr, t, "adds_max_perf") or 0) > RULE_ALT_ADD
                                         or (g(dr, t, "adds_p99_endPeriod") or 0) > RULE_ALT_ADD
                                         or (g(dr, t, "perf_max_max") or 0) > RULE_ALT_FRAME for t in have_b}
    else:
        grade("A6", PRED["A6"], None, "unmeasured", "no burst draw")
    if have_f:
        okp = len(have_f) == 3 and all((g(dr, t, "adds_p99_endPeriod") is not None
                                        and g(dr, t, "adds_p99_endPeriod") <= RULE_P99
                                        and g(dr, t, "adds_max_perf") is not None
                                        and g(dr, t, "adds_max_perf") <= RULE_MAX) for t in have_f)
        grade("B15P", PRED["B15P"], {t: dr[t] for t in have_f}, "as_predicted" if okp else "falsified",
              "a budget15 draw over 20 at p99 or 25 at the max")
        oks = len(have_f) == 3 and all(g(dr, t, "starvedEvents") == 0 for t in have_f)
        grade("B15S", PRED["B15S"], {t: g(dr, t, "starvedEvents") for t in have_f},
              "as_predicted" if oks else "falsified", "a starved ghost")
        r = D["total"]["ratio_ghost_ms_per_minute_event"]
        grade("TOT", PRED["TOT"], D["total"], "unmeasured" if r is None else
              ("as_predicted" if r <= RULE_TOTAL else "falsified"), "over 1.1x")
        D["budget15_ruling2"] = {"peak_clauses_every_draw": okp, "no_starvation_every_draw": oks,
                                 "total_clause": (r <= RULE_TOTAL) if r is not None else None,
                                 "empty_check_clause": "not measured here (ruling H4-1)"}
    else:
        for k in ("B15P", "B15S", "TOT"):
            grade(k, PRED[k], None, "unmeasured", "no budget15 draw")
    if have:
        badS = {}
        for t in have:
            gh = S[t].get("ghost") or {}
            if gh.get("failures") != 0 or gh.get("storeGhostKeys") != 0 or gh.get("neverRun") != 0:
                badS[t] = {k: gh.get(k) for k in ("failures", "storeGhostKeys", "neverRun", "lastError")}
        grade("S", PRED["S"], {t: {k: g(S, t, "ghost", k) for k in ("failures", "storeGhostKeys", "neverRun")}
                               for t in have}, "as_predicted" if not badS else "falsified",
              "a failure, a leak or a never-run", {"bad": badS})
    else:
        grade("S", PRED["S"], None, "unmeasured", "no arm")
    gc = out.get("gc") or {}
    if gc.get("exists"):
        mx = [g(S, t, "gc", "pause_max_ms") for t in every]
        mx = [x for x in mx if x is not None]
        worst = max(mx) if mx else None
        grade("G", PRED["G"], {"pause_events": gc.get("pause_events"), "pause_max_ms": gc.get("pause_max_ms"),
                               "stall_events": gc.get("stall_events"), "arm_pause_max_ms": worst},
              "as_predicted" if (worst is None or worst <= GC_PAUSE_MAX) else "falsified", "a pause over 1 ms in an arm")
    else:
        grade("G", PRED["G"], {"exists": False}, "falsified", "gc.log absent")
    Z = ph.get("Z") or {}
    if Z:
        obs = {"server_mod_error_lines": Z.get("server_mod_error_lines") or [], "admin_lua_error": out.get("admin_lua_error")}
        ok = not obs["server_mod_error_lines"] and not obs["admin_lua_error"]
        grade("Z", PRED["Z"], obs, "as_predicted" if ok else "falsified", "a mod error line, admin parked")
    else:
        grade("Z", PRED["Z"], None, "unmeasured", "phase Z not run")


# ---------------------------------------------------------------- run
if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    persist()
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)
if out["meta"].get("staged_manifest_sha256") != MANIFEST_SHA256:
    out["error"] = "the staged MANIFEST differs from the expected one; the session was not started"
    persist()
    sys.exit(1)
_m0 = mem("preboot")
if _m0["free_gb"] is None or _m0["free_gb"] < MIN_FREE_GB:
    out["error"] = f"free memory {_m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started"
    persist()
    print(out["error"])
    sys.exit(1)
lint_errors = lint_paths(prof.sources)
out["lint_errors"] = lint_errors
if lint_errors:
    out["error"] = "the layout lint found an ERROR in a profile mod folder; the session was not started"
    persist()
    print(json.dumps(lint_errors, indent=1))
    sys.exit(1)

try:
    shutil.copyfile(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME), os.path.join(run_dir, MANIFEST_NAME))
except OSError as e:
    out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"

try:
    server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
    out["server_launch_wall"] = wall()
    launch["epoch_ms"] = int(time.time() * 1000)
    server.start(timeout=prof.server_timeout)
    out["server_cmd_gclog"] = [a for a in (getattr(server, "cmd", None) or []) if a.startswith("-Xlog")]
    out["server_started_wall"] = wall()
    tl.mark("server_started")
    clients = attach_clients(run_dir, prof, server, rec_fx, tl, started=started)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["boot_info"] = {"server_launch_to_started_s": getattr(server, "t_started", None),
                        "client_debug": {u: getattr(c, "debug", None) for u, c in clients.items()}}
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             **{u: sorted(set(c.mods_not_found)) for u, c in clients.items()}}
    deployed = {}
    for cand in sorted(glob.glob(os.path.join(run_dir, "**", "mods", "PZTestKit", "**", "PZTestKit_*.lua"),
                                 recursive=True)):
        deployed[os.path.relpath(cand, run_dir).replace(os.sep, "/")] = sha256_file(cand)
    out["meta"]["deployed_harness_sha256"] = deployed
    mem("ready")
    persist()
    try:
        body()
    except Exception as e:                     # noqa: BLE001 - keep the rows already collected
        out["body_error"], out["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    persist()
except Exception as e:                         # noqa: BLE001
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    every = list(started)
    try:
        if server is not None:
            teardown(tl, server, [c for c in every if c.alive])
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, every)
        adm = clients.get("admin") if isinstance(clients, dict) else None
        out["admin_lua_error"] = ("lua_error" in getattr(adm, "seen", ())) if adm is not None else None
        out["client_seen"] = [{"user": getattr(c, "username", str(i)), **dict(getattr(c, "seen", {}))}
                              for i, c in enumerate(every)]
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
        try:
            read_logs(every)
        except Exception as e:                 # noqa: BLE001
            out["logs_error"] = f"{type(e).__name__}: {e}"
        try:
            read_gc()
        except Exception as e:                 # noqa: BLE001
            out["gc_error"] = f"{type(e).__name__}: {e}"
        try:
            grade_all()
        except Exception as e:                 # noqa: BLE001
            out["summary_error"] = f"{type(e).__name__}: {e}"
            out["summary_traceback"] = traceback.format_exc()[-3000:]
        out["wall_seconds"] = round(time.time() - t0, 1)
        persist()
        dest_dir = os.path.join(REPO, "testing", "artifacts", run_id)
        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copyfile(path, os.path.join(dest_dir, ARTIFACT))
            for nm in (MANIFEST_NAME, GCLOG):
                if os.path.isfile(os.path.join(run_dir, nm)):
                    shutil.copyfile(os.path.join(run_dir, nm), os.path.join(dest_dir, nm))
            src_pr = os.path.join(run_dir, POSRING_DIR)
            if os.path.isdir(src_pr):
                os.makedirs(os.path.join(dest_dir, POSRING_DIR), exist_ok=True)
                for p in sorted(glob.glob(os.path.join(src_pr, "*.json"))):
                    shutil.copyfile(p, os.path.join(dest_dir, POSRING_DIR, os.path.basename(p)))
            print(f"copied to {dest_dir}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")

print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                  "client_rule": {u: g(out, "summaries", "client_rule", u, "outcome") for u in USERS},
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id,
                  "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:6000])
