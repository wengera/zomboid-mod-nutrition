"""x243a-shootout -- Plan 10c Task H3 (live), session a of the scheduler shoot-out: an idle baseline and the seven
schedulers under test at N = 60 synthetic players, DayLength 1. On the UNINSTRUMENTED staged copy of the tree at
9578eb9 (release/hitch-9578eb9/NutritionRevamp/Contents/mods/NutritionRevamp, staged by Task 0, MANIFEST.json sha256
c86e295a...b389; release/ is gitignored; mod/ is never booted), so no sub-block timer inflates any arm. One boot of
profile x24-shootout-a (fixture two, admin -debug then bob release, Nutrition false, DayLength 1, gclog true). ONE
artifact, `shootout.json`, plus the staged MANIFEST.json and the server's gc.log copied byte-identical beside it.
Shape: x241_smoke.py and x242b_costs.py (step, keep, gread, run_phase, grade, make_server + attach_clients, the
echo-excluding log greps, the artifact copied by the driver). Written BEFORE the boot with every prediction in it and
never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE INSTRUMENT (the harness at 6af6595, server side; its comment block in PZTestKit_Server.lua is the contract):
  tick.ring <n> / read <tag>   every server frame stamped at OnTickEvenPaused and at the harness's OnTick hook
        (getTimestampMs, 1 ms): busy (start -> OnTick, the ghost batches inside it), period (start -> next start),
        endPeriod (OnTick -> next OnTick), the minute flag, the ghost runs and the ghost ms in the frame.
  perf.local <n> / read <tag>   getPerformanceLocal()'s per-window max-update-period (the hitch reading, #3443),
        sampled once per engine window (about 1 s, about 10 frames).
  ghost.load <N> <sched> feed [tpm<n>] / ghost.stats [reset] / ghost.stop   N - 2 ghost records run through the real
        pipeline against the two real players under a harness scheduler; the two real players stay on the mod's
        OWN drain (they are never moved onto a ghost scheduler). Every ghost is loaded with `feed` (x242b F).
  ghost.bench is NEVER called here: the calibration is x242b's.

THE CALIBRATION (x242b F, as the H2b review read it): a fed ghost is about one real player's minute, within a band of
about 0.72..1.0 of a real player; x242b's batch-timed fed ghost was 0.826 ms a run (0.800 unfed). Each arm's own ghost
cost is ghost.stats ms / runs (batch-timed, 1 ms resolution per batch). The cost-equivalent N of an arm is reported
as the band 2 + (N - 2) x [0.72, 1.0].

PHASES (order S0, I, then the seven scheduler arms in ARM_ORDER, then Z):
  S0  ready marks, verify rows, players, time, perf.local now, the free memory; wait (cap S0_WAIT_S) until both real
      records exist and the mod's minute ran MIN_RUNS times.
  I   the idle baseline: no ghost load; perf.local PERF_N, tick.ring RING_N; ARM_WALL_S of wall with NO bus traffic;
      perf.local read, tick.ring read; the result documents kept whole.
  <sched> for each scheduler in ARM_ORDER: ghost.stop of the previous load (if any); for drainTicks the running
      ticks-per-minute count TK.H0.tpmSeen is read and passed as tpm<n>; ghost.load N sched feed [tpm<n>];
      ghost.stats reset; perf.local PERF_N; tick.ring RING_N; ARM_WALL_S of wall with NO bus traffic; perf.local
      read, tick.ring read, ghost.stats; the result documents kept whole; ghost.stop.
  Z   ghost.stop if a load is left, the mod-error check, the free memory.
  After teardown: the server log is grepped (echo lines dropped first, CLAUDE.md s5) and gc.log is parsed.

ARM ORDER (the amendments: no scheduler always runs first): budget10, rr2, burst, budget5, drainTicks, budget15, rr5.
x243b and x243c rotate their own orders.

THE POPULATIONS (analysis in grade_all, off the artifact's own rows):
  ring frames: every frame of the arm's ring with a recorded busy (>= 0), minus every frame whose [start, stop]
      overlaps a bus step the driver sent inside the arm (the ring arm and the perf.local read; the tick.ring read
      writes its document after its own ring's last frame, so it is in no ring and in no kept perf window).
      Populations: busy (all frames), busy over minute frames, busy over the other frames, endPeriod (all frames).
  perf windows: the samples after the first (the first sample's window began before the arm), minus every window
      whose (previous sample, sample] interval overlaps a bus step inside the arm. Population: max-update-period.
  p50 / p99 / max are nearest-rank. "Adds" is the arm's figure minus the idle arm's same figure over the same
      population. Total busy a game minute = the kept frames' busy sum / the kept minute frames.
  GC: gc.log's uptime stamps mapped to epoch ms from the server's launch epoch (the JVM's uptime 0 is the process
      start; alignment about +-1 s); per arm, the pauses and stalls inside the arm's ring span, and those within
      GC_NEAR_MS of a minute frame.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  I     idle: ring busy p99 <= 10 ms and period p50 within 99..101 ms (x241: busy p99 9).
  F     every arm keeps >= 1000 ring frames and >= 100 minute frames.
  BURST burst: the minute frames' busy p50 within 0.5x..2x of 58 x 0.826 ms (47.9 ms).
  RR2   rr2: the minute frames' busy p50 within 0.5x..2x of 29 x 0.826 ms (23.95 ms).
  RR5   rr5: the minute frames' busy p50 within 0.5x..2x of 12 x 0.826 ms (9.91 ms).
  DRAIN drainTicks: busy max <= 25 ms and starvedEvents 0; tpmSource not "none".
  B5    budget5 starves: starvedEvents > 0 (about 6 runs a tick x 6.27 ticks < 58 ghosts a game minute).
  B10   budget10: starvedEvents 0; its perf windows add at most 20 ms at p99 and 25 ms at the max over idle.
  B15   budget15: starvedEvents 0.
  A6    the one-event burst adds more than 25 ms at the perf windows' max over idle (Decision 6 (a) not admissible).
  S     every arm: failures 0, storeGhostKeys 0, neverRun 0 except budget5.
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


PROFILE = "x24-shootout-a"
PREFIX = "x243a"
SESSION = ("Plan 10c Task H3 session a: the scheduler shoot-out at N = 60, DayLength 1 -- an idle baseline, then "
           "budget10, rr2, burst, budget5, drainTicks, budget15 and rr5, each about 1000 frames -- on the "
           "uninstrumented staged copy at 9578eb9; one boot of " + PROFILE)
ARTIFACT = "shootout.json"
MANIFEST_NAME = "MANIFEST.json"
GCLOG = "gc.log"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (BOB, ADMIN)
USERS = ("admin", "bob")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/hitch-9578eb9/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_AT = "9578eb9"
MANIFEST_SHA256 = "c86e295a3ef4c70bde57ab436c9dc3919172dd81db2a8a71164659d62415b389"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_SERVER = LUA_DIR + "/server/PZTestKit_Server.lua"
NR = "NutritionRevamp"
N = 60
REALS = 2
ARM_ORDER = ("budget10", "rr2", "burst", "budget5", "drainTicks", "budget15", "rr5")
ARM_WALL_S = 101.5               # about 1020 frames at the ten-tick lock; about 162 minute frames at DayLength 1
RING_N = 1500
PERF_N = 400
MIN_FRAMES = 1000
MIN_MINUTE_FRAMES = 100
S0_WAIT_S = 90.0
MIN_RUNS = 4
MIN_FREE_GB = 12.0
RESULT_WAIT_S = 30.0
POLL_S = 0.5
LOG_LIMIT = 400
FED_MS = 0.826                   # x242b phases.F.fed.stop.stats: batch-timed fed ghost ms a run
BAND = (0.72, 1.0)               # a fed ghost against a real player's minute (the H2b review)
PRED_BAND = (0.5, 2.0)
IDLE_BUSY_P99_MAX = 10
IDLE_PERIOD_BAND = (99, 101)
DRAIN_BUSY_MAX = 25
RULE_P99 = 20.0                  # ruling 2: (b) adds at most 20 ms at p99
RULE_MAX = 25.0                  # ruling 2: (b) adds at most 25 ms at the max; (a) the burst at most 25 ms
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
    "BURST": {"burst minute busy p50 / (58 x 0.826)": list(PRED_BAND)},
    "RR2": {"rr2 minute busy p50 / (29 x 0.826)": list(PRED_BAND)},
    "RR5": {"rr5 minute busy p50 / (12 x 0.826)": list(PRED_BAND)},
    "DRAIN": {"drainTicks busy max": f"<= {DRAIN_BUSY_MAX}", "starvedEvents": 0, "tpmSource": "not none"},
    "B5": {"budget5 starvedEvents": "> 0"},
    "B10": {"budget10 starvedEvents": 0, "perf max adds at p99": f"<= {RULE_P99}",
            "perf max adds at max": f"<= {RULE_MAX}"},
    "B15": {"budget15 starvedEvents": 0},
    "A6": {"burst perf max adds at max": f"> {RULE_MAX}"},
    "S": {"failures": 0, "storeGhostKeys": 0, "neverRun": "0 except budget5"},
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
             "cost_note": "Every reading is cost, not behaviour: the ghosts run copies of the real records against "
                          "the two real IsoPlayers (their Java writes land on the carriers). The two real players "
                          "stay on the mod's own drain throughout. No behaviour row rests on this session.",
             "timer_note": "getTimestampMs is 1 ms resolution: a frame's busy is a 1 ms reading; every per-run cost "
                           "is a total over many runs divided by their count."},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [
        "The H3 amendments put the empty-check A/B (2 x 3000 frames) in this session; with the seven arms it would "
        "run about 27 minutes against the amendments' 15-minute session cap, so the A/B and the day-boundary arm run "
        "in a fourth session, x243d (DayLength 1).",
    ],
    "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {}, "summaries": {},
    "memory": [],
}
try:
    out["meta"]["harness_server_sha256"] = sha256_file(os.path.join(REPO, HARNESS_SERVER))
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


def wait_doc(name, after):
    try:
        return server.bus.wait_result(name, timeout=RESULT_WAIT_S, after=after)
    except Exception as e:                     # noqa: BLE001 - a missing document is a recorded fault
        note(f"result {name}: {type(e).__name__}: {e}")
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


# ---------------------------------------------------------------- the arm
def run_arm(tag, n, sched, wall_s=ARM_WALL_S):
    """One arm. sched None is an idle arm (no load). Bus traffic inside the window: the ring arm only, before it the
    perf arm, after it the perf read; their spans are the arm's drop windows."""
    A = out["phases"][tag] = {"tag": tag, "N": n if sched else None, "sched": sched, "mem_before": mem(f"{tag}_0")}
    if sched is not None:
        args = f"{n} {sched} feed"
        if sched == "drainTicks":
            A["tpm_read"] = gread(SRV, "TK.H0.tpmSeen", f"{tag}_tpm")
            t = num(val(A["tpm_read"]))
            if t is not None and t >= 1:
                args += f" tpm{int(t)}"
        A["load"] = keep(step(f"{tag}_load", SRV, "ghost.load", args, timeout=60))
        if not A["load"].get("ok"):
            note(f"{tag}: ghost.load failed: {A['load'].get('reason') or A['load'].get('raw')}")
        A["reset"] = keep(step(f"{tag}_reset", SRV, "ghost.stats", "reset"))
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
    A["perf_doc"] = wait_doc(f"perf-local-{tag}", after)
    A["ring_doc"] = wait_doc(f"tick-ring-{tag}", after)
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


def phase_I():
    run_arm("I", None, None)


def make_arm(sched):
    def fn():
        run_arm(sched, N, sched)
    return fn


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["stop_left"] = keep(step("Z_stop", SRV, "ghost.stop"))
    P["players"] = keep(step("Z_players", SRV, "players"))
    P["time"] = snap("Z_time")
    P["minstats"] = minstats("Z")
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:20]
    P["admin_parked"] = parked()
    P["mem"] = mem("Z")


def body():
    order = [("S0", phase_S0), ("I", phase_I)] + [(s, make_arm(s)) for s in ARM_ORDER] + [("Z", phase_Z)]
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
        near = []
        for f in mins:
            ne = gc_in((f["start"] or 0) - GC_NEAR_MS, (f["stop"] or 0) + GC_NEAR_MS)
            if ne:
                near.append({"frame": f["frame"], "busy": f["busy"], "events": len(ne),
                             "max_ms": max(e["ms"] for e in ne), "stall": any(e["kind"] == "stall" for e in ne)})
        S["gc"]["minute_frames_near_gc"] = len(near)
        S["gc"]["minute_frames_near_stall"] = sum(1 for x in near if x["stall"])
        S["gc"]["near_max_ms"] = max([x["max_ms"] for x in near], default=None)
        top = sorted(mins, key=lambda f: -(f["busy"] or -1))[:5]
        S["gc"]["top5_minute_busy_near"] = [{"frame": f["frame"], "busy": f["busy"],
                                             "gc_within_1s": [{"kind": e["kind"], "ms": e["ms"]} for e in
                                                              gc_in((f["start"] or 0) - GC_NEAR_MS, (f["stop"] or 0) + GC_NEAR_MS)][:6]}
                                            for f in top]
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


def band_ok(x, ref):
    return x is not None and PRED_BAND[0] * ref <= x <= PRED_BAND[1] * ref


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
    for s in ARM_ORDER:
        A = ph.get(s) or {}
        if A.get("ring_doc"):
            S[s] = arm_summary(A, idle)
    have = [s for s in ARM_ORDER if s in S]
    if have:
        short = {s: [S[s]["frames"], S[s]["minute_frames"]] for s in ["I"] + have if s in S
                 if S[s]["frames"] < MIN_FRAMES or S[s]["minute_frames"] < MIN_MINUTE_FRAMES}
        grade("F", PRED["F"], {s: [S[s]["frames"], S[s]["minute_frames"]] for s in ["I"] + have if s in S},
              "as_predicted" if not short and len(have) == len(ARM_ORDER) else "falsified", "an arm short",
              {"short": short})
    else:
        grade("F", PRED["F"], None, "unmeasured", "no arm")

    def mb(s):
        return g(S, s, "busy_minute", "p50")

    for key, s, k in (("BURST", "burst", N - REALS), ("RR2", "rr2", math.ceil((N - REALS) / 2)),
                      ("RR5", "rr5", math.ceil((N - REALS) / 5))):
        if s in S:
            ref = k * FED_MS
            grade(key, PRED[key], {"busy_minute": S[s]["busy_minute"], "ref_ms": ref,
                                   "ratio": (mb(s) / ref) if mb(s) is not None else None,
                                   "ghost_ms_per_run": S[s].get("ghost_ms_per_run")},
                  "as_predicted" if band_ok(mb(s), ref) else "falsified", "outside 0.5..2x")
        else:
            grade(key, PRED[key], None, "unmeasured", "no arm")
    if "drainTicks" in S:
        d = S["drainTicks"]
        src = g(d, "ghost", "tpmSource")
        ok = (d["busy"]["max"] is not None and d["busy"]["max"] <= DRAIN_BUSY_MAX
              and g(d, "ghost", "starvedEvents") == 0 and src not in (None, "none"))
        grade("DRAIN", PRED["DRAIN"], {"busy": d["busy"], "starvedEvents": g(d, "ghost", "starvedEvents"),
                                       "tpmSource": src, "tpmSeed": g(d, "ghost", "tpmSeed")},
              "as_predicted" if ok else "falsified", "busy max over 25, a starved ghost or no tpm seed")
    else:
        grade("DRAIN", PRED["DRAIN"], None, "unmeasured", "no arm")
    if "budget5" in S:
        se = g(S, "budget5", "ghost", "starvedEvents")
        grade("B5", PRED["B5"], {"starvedEvents": se, "starvedMinutes": g(S, "budget5", "ghost", "starvedMinutes"),
                                 "maxStaleGameMinutes": g(S, "budget5", "ghost", "maxStaleGameMinutes")},
              "unmeasured" if se is None else ("as_predicted" if se > 0 else "falsified"), "no starvation")
    else:
        grade("B5", PRED["B5"], None, "unmeasured", "no arm")
    if "budget10" in S:
        b = S["budget10"]
        se = g(b, "ghost", "starvedEvents")
        a99, amx = g(b, "adds", "perf_max", "p99"), g(b, "adds", "perf_max", "max")
        ok = se == 0 and a99 is not None and a99 <= RULE_P99 and amx is not None and amx <= RULE_MAX
        grade("B10", PRED["B10"], {"starvedEvents": se, "perf_max": b["perf_max"], "adds_perf_max": g(b, "adds", "perf_max"),
                                   "busy": b["busy"], "adds_busy": g(b, "adds", "busy")},
              "as_predicted" if ok else "falsified", "a starved ghost or the bounds exceeded")
    else:
        grade("B10", PRED["B10"], None, "unmeasured", "no arm")
    if "budget15" in S:
        se = g(S, "budget15", "ghost", "starvedEvents")
        grade("B15", PRED["B15"], {"starvedEvents": se}, "unmeasured" if se is None else
              ("as_predicted" if se == 0 else "falsified"), "a starved ghost")
    else:
        grade("B15", PRED["B15"], None, "unmeasured", "no arm")
    if "burst" in S:
        amx = g(S, "burst", "adds", "perf_max", "max")
        grade("A6", PRED["A6"], {"adds_perf_max": g(S, "burst", "adds", "perf_max"), "perf_max": S["burst"]["perf_max"],
                                 "adds_busy_minute": g(S, "burst", "adds", "busy_minute")},
              "unmeasured" if amx is None else ("as_predicted" if amx > RULE_MAX else "falsified"), "burst adds <= 25")
    else:
        grade("A6", PRED["A6"], None, "unmeasured", "no arm")
    if have:
        bad = {}
        for s in have:
            gh = S[s].get("ghost") or {}
            nr_ok = (gh.get("neverRun") == 0) or s == "budget5"
            if gh.get("failures") != 0 or gh.get("storeGhostKeys") != 0 or not nr_ok:
                bad[s] = {k: gh.get(k) for k in ("failures", "storeGhostKeys", "neverRun", "lastError")}
        grade("S", PRED["S"], {s: {k: g(S, s, "ghost", k) for k in ("failures", "storeGhostKeys", "neverRun")}
                               for s in have}, "as_predicted" if not bad else "falsified", "a failure, a leak or a never-run",
              {"bad": bad})
    else:
        grade("S", PRED["S"], None, "unmeasured", "no arm")
    gc = out.get("gc") or {}
    if gc.get("exists"):
        mx = [g(S, s, "gc", "pause_max_ms") for s in ["I"] + have if s in S]
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
    for cand in sorted(glob.glob(os.path.join(run_dir, "**", "mods", "PZTestKit", "**", "PZTestKit_Server.lua"),
                                 recursive=True)):
        deployed[os.path.relpath(cand, run_dir).replace(os.sep, "/")] = sha256_file(cand)
    out["meta"]["deployed_harness_server_sha256"] = deployed
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
            print(f"copied to {dest_dir}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")

print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id,
                  "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:6000])
