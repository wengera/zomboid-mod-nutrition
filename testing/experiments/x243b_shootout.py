"""x243b-shootout -- Plan 10c Task H3 (live), session b of the scheduler shoot-out: an idle baseline; burst, drainTicks
and budget10 at N = 20 and N = 40 synthetic players; and the shipped drain's starvation at N = 60 (ruling 3), DayLength
1. On the UNINSTRUMENTED staged copy of the tree at 9578eb9 (release/hitch-9578eb9/NutritionRevamp/Contents/mods/
NutritionRevamp, staged by Task 0, MANIFEST.json sha256 c86e295a...b389; release/ is gitignored; mod/ is never
booted). One boot of profile x24-shootout-b (fixture two, admin -debug then bob release, Nutrition false, DayLength 1,
gclog true). ONE artifact, `shootout.json`, plus the staged MANIFEST.json and the server's gc.log copied byte-identical
beside it. A copy of x243a_shootout.py (a0c5af1; which is never edited) with the arms, predictions and grading of
this session. Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5,
B3-1/B3-2).

THE INSTRUMENT, THE CALIBRATION AND THE POPULATIONS: as x243a_shootout.py's docstring states them (tick.ring,
perf.local, ghost.load ... feed, ghost.stats reset between arms, no ghost.bench; a fed ghost is about one real
player's minute, band 0.72..1.0; ring frames and perf windows minus the spans of the bus steps inside an arm; adds
against this session's own idle arm over the same population). The two real players stay on the mod's OWN drain.

PHASES (order S0, I, then ARMS in order, then Z):
  S0  as x243a.
  I   the idle baseline, as x243a (ARM_WALL_S, no load).
  ARMS  burst20, drainTicks20, budget10_20, budget10_40, burst40, drainTicks40 (each ARM_WALL_S, about 1020 frames),
      then shipped60 (SHIP_WALL_S, about 110 minute events; ruling 3: starvation only, the cost arms use the designs
      under test). Each arm as x243a's: ghost.stop of the previous load; for drainTicks tpm<n> from TK.H0.tpmSeen;
      ghost.load N sched feed [tpm<n>]; ghost.stats reset; perf.local; tick.ring; the wall; perf.local read,
      tick.ring read, ghost.stats; ghost.stop.
  Z   as x243a.

ORDER (no scheduler always first; x243a ran budget10 first at N = 60): burst first at N = 20, budget10 first at
N = 40, drainTicks never first.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  I     idle: ring busy p99 <= 10 ms and period p50 within 99..101 ms.
  F     every arm but shipped60 keeps >= 1000 ring frames and >= 100 minute frames; shipped60 >= 100 minute events.
  LIN   the burst's minute-frame busy p50 at N = 40 over that at N = 20 lies within 1.5..2.8 (the ghost counts give
        38 / 18 = 2.11).
  B20   burst20: the minute frames' busy p50 within 0.5x..2x of 18 x 0.826 ms (14.9 ms).
  B40   burst40: the minute frames' busy p50 within 0.5x..2x of 38 x 0.826 ms (31.4 ms).
  Q     drainTicks and budget10 at N = 20 and 40: starvedEvents 0; tpmSource not "none" for drainTicks.
  SHIP  shipped60: ghost runs a minute event within 3..6 (one a tick on the ticks the real drain leaves, about
        6.27 - 2), dropped > 0, and neverRun >= 40 of the 58 ghosts (the rebuilt queue serves the same ghosts first).
  S     every arm: failures 0, storeGhostKeys 0; neverRun 0 except shipped60.
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
SESSION = ("Plan 10c Task H3 session b: an idle baseline; burst, drainTicks and budget10 at N = 20 and 40, each about "
           "1000 frames; the shipped drain's starvation at N = 60 (ruling 3), DayLength 1 -- on the uninstrumented "
           "staged copy at 9578eb9; one boot of " + PROFILE)
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
REALS = 2
ARM_WALL_S = 101.5               # about 1020 frames at the ten-tick lock; about 162 minute frames at DayLength 1
SHIP_WALL_S = 70.0               # about 110 minute events at DayLength 1
ARMS = (("burst20", 20, "burst", ARM_WALL_S), ("drainTicks20", 20, "drainTicks", ARM_WALL_S),
        ("budget10_20", 20, "budget10", ARM_WALL_S), ("budget10_40", 40, "budget10", ARM_WALL_S),
        ("burst40", 40, "burst", ARM_WALL_S), ("drainTicks40", 40, "drainTicks", ARM_WALL_S),
        ("shipped60", 60, "shipped", SHIP_WALL_S))
LIN_BAND = (1.5, 2.8)
SHIP_RPM = (3.0, 6.0)
SHIP_NEVER_MIN = 40
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
    "F": {"kept ring frames": f">= {MIN_FRAMES}", "kept minute frames": f">= {MIN_MINUTE_FRAMES}",
          "shipped60 minute events": f">= {MIN_MINUTE_FRAMES}"},
    "LIN": {"burst40 minute busy p50 / burst20's": list(LIN_BAND)},
    "B20": {"burst20 minute busy p50 / (18 x 0.826)": list(PRED_BAND)},
    "B40": {"burst40 minute busy p50 / (38 x 0.826)": list(PRED_BAND)},
    "Q": {"drainTicks and budget10 at 20 and 40 starvedEvents": 0, "drainTicks tpmSource": "not none"},
    "SHIP": {"ghost runs a minute event": list(SHIP_RPM), "dropped": "> 0", "neverRun": f">= {SHIP_NEVER_MIN}"},
    "S": {"failures": 0, "storeGhostKeys": 0, "neverRun": "0 except shipped60"},
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
        "The H3 amendments put the day-boundary arm (N = 60 across 07:00 for burst and budget10) in this session; it "
        "runs in x243d with the empty-check A/B, to keep each session near the 15-minute cap.",
        "Ruling 3's shipped-drain arm reads starvation only; its ring and perf windows are kept but not graded.",
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


def make_arm(tag, n, sched, wall_s):
    def fn():
        run_arm(tag, n, sched, wall_s)
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
    order = [("S0", phase_S0), ("I", phase_I)] + [(a[0], make_arm(*a)) for a in ARMS] + [("Z", phase_Z)]
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
    tags = [a[0] for a in ARMS]
    for t in tags:
        A = ph.get(t) or {}
        if A.get("ring_doc"):
            S[t] = arm_summary(A, idle)
    have = [t for t in tags if t in S]
    if have:
        fr = {t: [S[t]["frames"], S[t]["minute_frames"], g(S, t, "ghost", "minuteEventsSince")] for t in ["I"] + have
              if t in S}
        short = {}
        for t, v in fr.items():
            if t == "shipped60":
                if (v[2] or 0) < MIN_MINUTE_FRAMES:
                    short[t] = v
            elif v[0] < MIN_FRAMES or v[1] < MIN_MINUTE_FRAMES:
                short[t] = v
        grade("F", PRED["F"], fr, "as_predicted" if not short and len(have) == len(tags) else "falsified",
              "an arm short", {"short": short})
    else:
        grade("F", PRED["F"], None, "unmeasured", "no arm")

    def mb(t):
        return g(S, t, "busy_minute", "p50")

    for key, t, k in (("B20", "burst20", 20 - REALS), ("B40", "burst40", 40 - REALS)):
        if t in S:
            ref = k * FED_MS
            grade(key, PRED[key], {"busy_minute": S[t]["busy_minute"], "ref_ms": ref,
                                   "ratio": (mb(t) / ref) if mb(t) is not None else None,
                                   "ghost_ms_per_run": S[t].get("ghost_ms_per_run")},
                  "as_predicted" if band_ok(mb(t), ref) else "falsified", "outside 0.5..2x")
        else:
            grade(key, PRED[key], None, "unmeasured", "no arm")
    if mb("burst20") and mb("burst40") is not None:
        r = mb("burst40") / mb("burst20")
        grade("LIN", PRED["LIN"], {"p50_20": mb("burst20"), "p50_40": mb("burst40"), "ratio": r,
                                   "ghost_ms_per_run_20": g(S, "burst20", "ghost_ms_per_run"),
                                   "ghost_ms_per_run_40": g(S, "burst40", "ghost_ms_per_run")},
              "as_predicted" if LIN_BAND[0] <= r <= LIN_BAND[1] else "falsified", "outside 1.5..2.8")
    else:
        grade("LIN", PRED["LIN"], None, "unmeasured", "a burst arm missing or zero")
    q = [t for t in ("drainTicks20", "budget10_20", "budget10_40", "drainTicks40") if t in S]
    if q:
        obs = {t: {"starvedEvents": g(S, t, "ghost", "starvedEvents"), "tpmSource": g(S, t, "ghost", "tpmSource"),
                   "maxStaleGameMinutes": g(S, t, "ghost", "maxStaleGameMinutes")} for t in q}
        bad = [t for t in q if obs[t]["starvedEvents"] != 0 or
               (t.startswith("drainTicks") and obs[t]["tpmSource"] in (None, "none"))]
        grade("Q", PRED["Q"], obs, "as_predicted" if not bad and len(q) == 4 else "falsified",
              "a starved ghost, no tpm seed or an arm missing", {"bad": bad})
    else:
        grade("Q", PRED["Q"], None, "unmeasured", "no arm")
    if "shipped60" in S:
        gh = S["shipped60"].get("ghost") or {}
        rpm = S["shipped60"].get("ghost_runs_per_minute_event")
        ok = (rpm is not None and SHIP_RPM[0] <= rpm <= SHIP_RPM[1] and (gh.get("dropped") or 0) > 0
              and (gh.get("neverRun") or 0) >= SHIP_NEVER_MIN)
        grade("SHIP", PRED["SHIP"], {"runs_per_minute_event": rpm,
                                     **{k: gh.get(k) for k in ("runs", "minuteEventsSince", "dropped", "yielded",
                                                               "neverRun", "starvedEvents", "starvedMinutes",
                                                               "maxStaleMinutes", "maxStaleGameMinutes", "failures")}},
              "as_predicted" if ok else "falsified", "runs a minute outside 3..6, nothing dropped or too few never-run")
    else:
        grade("SHIP", PRED["SHIP"], None, "unmeasured", "no arm")
    if have:
        bad = {}
        for t in have:
            gh = S[t].get("ghost") or {}
            nr_ok = (gh.get("neverRun") == 0) or t == "shipped60"
            if gh.get("failures") != 0 or gh.get("storeGhostKeys") != 0 or not nr_ok:
                bad[t] = {k: gh.get(k) for k in ("failures", "storeGhostKeys", "neverRun", "lastError")}
        grade("S", PRED["S"], {t: {k: g(S, t, "ghost", k) for k in ("failures", "storeGhostKeys", "neverRun")}
                               for t in have}, "as_predicted" if not bad else "falsified", "a failure, a leak or a never-run",
              {"bad": bad})
    else:
        grade("S", PRED["S"], None, "unmeasured", "no arm")
    gc = out.get("gc") or {}
    if gc.get("exists"):
        mx = [g(S, t, "gc", "pause_max_ms") for t in ["I"] + have if t in S]
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
