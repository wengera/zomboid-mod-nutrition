"""x391e-owed -- Plan 11b Task 2 (live), session S2e: the owed performance reads of the run sheet's Task 2 (c) that the
four shoot-out sessions do not take, at N = 60 ghost records beside the two real players, DayLength 1 (about 6.27
ticks a game minute, #3346). On the staged copy of the tree at 513778e8 (release/plan11-x39/NutritionRevamp/Contents/
mods/NutritionRevamp, MANIFEST.json sha256 83c79a04...52c0; release/ is gitignored; mod/ is never booted), build
42.21.0 (4a0e9546ec), Nutrition false. One boot of profile x39-shootout-e (fixture two, admin -debug then bob release,
DayLength 1, gclog true). Artifact: `owed.json`, the staged MANIFEST.json and the server's gc.log copied byte-identical
beside it. Shape: x391a_shootout.py's helpers, ring and perf handling and grading helpers (themselves x244c_notice.py's).
Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2). The
driver asserts that its PREFIX and PROFILE match its own file name.

PHASES: S0 (ready, records, MIN_RUNS), then
  B   THE EMPTY-CHECK BENCH (the plan's x251c (1), verbatim but for three draws): time.snapshot reads the multiplier;
      `time.multiplier 0.0001`; wait 3 s for the queue to empty; one lua.read of NutritionRevamp.server.players.{served,
      ticks, ...}; then BENCH_DRAWS times `bench.global NutritionRevamp.server.players.tick 100000`, each followed by a
      read of served (unchanged, or that draw is marked invalid: a drain ran inside it); then `lua.setpath
      NutritionRevamp.server.players.ticks <the value read before the first bench>` (the bench inflated it by
      BENCH_DRAWS x 100000) and a read back; then `time.multiplier <the value read first>`. The next two minute events'
      ticksLast, budgetMs and runCap are dropped from every reading (the bench's calls could sit in ticksPrev if the
      restore missed a tick): the driver waits until players.minutes has risen by 2 past the restore before phase L
      arms anything, and records those two minutes' values under `dropped`.
  L   OWN-ACTION LATENCY on admin, arms idle, burst (`ghost.load 60 burst feed`) and mod (`ghost.load 60 mod feed` +
      `ghost.modq on`), each: the load and SETTLE_S, ghost.stats reset, RCON `additem "admin" "Base.Apple" 3` (a
      client spawn is an item the server never heard of: harness-commands action.latency), SPAWN_WAIT_S,
      `foodtimer.set admin 0`, perf.local and tick.ring armed, then `action.latency Base.Apple 3` on client:admin and
      `action.latency read` polled (client bus only, no server traffic) until done or LAT_CAP_S; then the server reads
      and the stop. Then the NON-FOOD SMOKE (Plan 11a Task 19 fix 1's carry): `action.latency Base.Hammer 1` and its
      read: it answers reason "not a Food item" without parking the -debug client.
  W   THE REAL-PLAYER COSTS (the writer-side lanes the dry ghosts never reach, amendment 6, 11f item 2, 11g item 4):
      `stats.bench admin BOREDOM 100000` bare, then wrapped (the writer's own NR.num / pcall(NR.call ...) route), and
      `bench.global NutritionRevamp.bench_writer 10000` then `100000` (one writer step a call over a filled steady
      input). The sixty-player projections are arithmetic: the BOREDOM lane = usPerPair x 60 a rising minute (one get
      and one set), the writer = usPerCall x 60 a minute event.
  FC  THE FAST CLOCK: `ghost.load 60 mod feed` + `ghost.modq on`, RCON `settimespeed 30`, SETTLE_S, ghost.stats reset,
      perf.local and tick.ring over FC_WALL_S, ghost.stats (maxStaleGameMinutes, staleGameNowMax, starvation), the
      queue's state, then RCON `settimespeed 1` (restored whatever went wrong, from the phase's finally), modq off and
      the stop.
  ST  THE INDUCED STALL (11c amendment 5): `ghost.load 60 mod feed` + `ghost.modq on`, STALL_WARM_S so every ghost has
      run, then `ghost.modq off` (the ghosts leave the mod's queue; nothing runs them) and a wait until at least
      STALL_GAP_MIN game minutes have passed (read off time.snapshot), so every ghost's next run sees a gap of at least
      sixty game minutes at once; then perf.local and tick.ring armed, ghost.stats reset (its `before` carries every
      ghost's staleness now), `ghost.modq on`, STALL_READ_S of wall, the reads, modq off, the stop. The catch-up is
      read off the ring: from the first frame after the modq-on step, the frames until the ghosts' cumulative runs
      reach N - REALS are the catch-up frames; their busy max, end-to-end max and batch ms a run, against the later
      frames' (steady). The stall arm keeps every ring frame (no drop windows: the modq-on reply can arrive after the
      catch-up frames have started), and names the bus steps' spans beside it.
  Z   the stops, the speed restore check, the logs.

THE SEAMS (Plan 11a ruling 15): every ghost run (burst and mod alike) runs the writer dry and skips the store step for
ghost names, set inside H0.work. Each loaded arm reads store.file.stats.writes at its start and end; a rise above the
real players' own saves (REALS * (floor(span / 60) + 1) + floor(span / 300) + 1) voids that arm.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  EMPTY     every valid draw: usPerCall <= 100 (the ruling-2 clause: the empty check at most 0.1 ms a frame, one
            P.tick call a frame); served unchanged across every draw (else that draw is invalid).
  RESTORE   players.ticks reads back the value read before the bench.
  DROP      two minute events pass after the restore inside DROP_WAIT_S.
  LAT       every arm returns 3 samples, each done (the item left the container inside 30 s); medians and maxima are a
            reading (no threshold), burst against mod.
  NONFOOD   action.latency Base.Hammer 1 reads done with reason "not a Food item"; admin not parked.
  BENCH     stats.bench bare and wrapped ok with usPerPair; bench_writer answers usPerCall with no error at both n.
  FAST      the mod queue at settimespeed 30: maxStaleGameMinutes <= 15 (about three frames of game time; the 10 ms
            budget's was 42.8, #3480) and the window keeps >= 500 ring frames; frame period and worst frame reported.
  STALL     every ghost's staleness at the reset is >= 60 game minutes; the catch-up's ghost runs number N - REALS
            within the first CATCHUP_EVENTS minute events; the catch-up's batch ms a run exceeds the steady frames'.
  S         every loaded arm: failures 0, storeGhostKeys 0.
  SEAM      no loaded arm's writes delta above its allowance.
  G         gc.log exists (pauses reported, not graded: the benches are single long frames by design).
  Z         no mod error line; admin not parked; the speed restored (time.snapshot mult back to the value before FC).

THE READING GUIDE CAVEATS (amendment 6): the writer is omitted from every ghost run (W.dry), so usPerRun, staleness and
starvation read optimistic; P.meanMs is sized on a dry-ghost mean; no carrier reading is valid during a ghost load;
the writer's real-player cost (phase W) is added for the sixty projection. The ghosts' records here carry no monotony
seed (the run sheet seeds S2a-S2d only). The benches in B and W are each one long server frame by design.

DEVIATIONS (stated before the run): the empty-check bench takes BENCH_DRAWS = 3 draws (the plan names one) with one
restore after the third; the stall is induced by holding the ghosts out of the mod's queue (`ghost.modq off`) for at
least sixty game minutes rather than by raising time.multiplier: a raised multiplier makes every frame a minute frame
and its per-frame step is unread, while the hold gives every ghost the same gap at one known moment (the run sheet's
condition: every ghost's next run sees a gap of at least 60 game minutes); the two real players are not stalled.

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


PROFILE = "x39-shootout-e"
PREFIX = "x391e"
SESSION = ("Plan 11b Task 2 session S2e: the owed reads at N = 60, DayLength 1 -- the empty-check bench and its ticks "
           "restore, own-action latency under idle, burst and mod plus the non-Food smoke, the real players' BOREDOM "
           "pair and writer, the fast clock and the induced one-hour stall -- on the staged copy at 513778e8; one boot "
           "of " + PROFILE)
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert PROFILE == "x39-shootout-" + PREFIX[-1], f"PROFILE {PROFILE} does not match PREFIX {PREFIX}"
ARTIFACT = "owed.json"
MANIFEST_NAME = "MANIFEST.json"
GCLOG = "gc.log"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (ADMIN, BOB)
USERS = ("admin", "bob")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/plan11-x39/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_AT = "513778e8"
MANIFEST_SHA256 = "83c79a04a38da11b8edd8bd96cc391ec29a91529b5bae065e42c0ef44bcf52c0"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_SERVER = LUA_DIR + "/server/PZTestKit_Server.lua"
NR = "NutritionRevamp"
N = 60
REALS = 2
SLOW_BENCH_MULT = 0.0001
EMPTY_WAIT_S = 3.0
BENCH_N = 100000
BENCH_DRAWS = 3
EMPTY_MAX_US = 100.0             # ruling 2: the empty check at most 0.1 ms a frame (one P.tick call a frame)
DROP_WAIT_S = 20.0
LAT_ARMS = (("Lidle", None), ("Lburst", "burst"), ("Lmod", "mod"))
LAT_FOOD = "Base.Apple"
LAT_N = 3
NONFOOD = "Base.Hammer"
SPAWN_WAIT_S = 2.5
LAT_CAP_S = 120.0
LAT_POLL_S = 1.0
SETTLE_S = 3.0
STAT_BENCH_N = 100000
WRITER_NS = (10000, 100000)
FAST_SPEED = 30
FC_WALL_S = 75.0
FC_MIN_FRAMES = 500
FAST_STALE_MAX = 15.0
STALL_WARM_S = 8.0
STALL_GAP_MIN = 65.0             # game minutes the ghosts are held out (>= 60, K.satiety.MAX_GAP_M)
STALL_GAP_CAP_S = 90.0
STALL_READ_S = 20.0
CATCHUP_EVENTS = 3
RING_N = 1500
PERF_N = 400
S0_WAIT_S = 90.0
MIN_RUNS = 4
MIN_FREE_GB = 12.0
RESULT_WAIT_S = 30.0
POLL_S = 0.5
LOG_LIMIT = 400
SAVE_GAP_S = 60
FREQ_MS = (110, 120)             # the end-to-end thresholds counted for Rule 6's frequency
BUSY_MS = (10, 15, 20)
INDEX_GAP_S = 300
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
MOD_LIFE_RX = re.compile(r"minute: \w+ failed|players: hook failed|players: extra|players: task|fast: |options: |"
                         r"effects: .* failed|nutrients: .* failed|metabolism: .* failed|non-finite")
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
QPATHS = tuple(f"{NR}.server.players.{k}" for k in ("served", "meanMs", "budgetMs", "runCap", "ticks", "ticksLast",
                                                    "ticksPrev", "minutes", "drained")) + \
    (f"{NR}.server.store.file.stats.writes", f"{NR}.server.store.file.stats.bytes",
     f"{NR}.server.minute.stats.runs", f"{NR}.server.minute.stats.failures")

PRED = {
    "EMPTY": {"every valid draw usPerCall": f"<= {EMPTY_MAX_US}", "served across each draw": "unchanged"},
    "RESTORE": {"players.ticks after lua.setpath": "the value read before the first bench"},
    "DROP": {"minute events after the restore inside DROP_WAIT_S": ">= 2"},
    "LAT": {"every arm": f"{LAT_N} samples, each done", "reading": "median and max per arm, burst against mod"},
    "NONFOOD": {"action.latency Base.Hammer 1": "done, reason 'not a Food item'", "admin parked": False},
    "BENCH": {"stats.bench bare and wrapped": "ok with usPerPair", "bench_writer": "usPerCall, no error, both n"},
    "FAST": {"maxStaleGameMinutes": f"<= {FAST_STALE_MAX}", "kept ring frames": f">= {FC_MIN_FRAMES}"},
    "STALL": {"every ghost's staleness at the reset": ">= 60 game minutes",
              "catch-up runs": f"N - REALS within the first {CATCHUP_EVENTS} minute events",
              "catch-up batch ms a run": "> the steady frames'"},
    "S": {"failures": 0, "storeGhostKeys": 0},
    "SEAM": {"store writes delta a loaded arm": "<= REALS*(floor(span/60)+1) + floor(span/300) + 1"},
    "G": {"gc.log": "exists"},
    "Z": {"mod_error": "none", "admin_lua_error": False, "speed restored": True},
}

# session state (set in main)
prof = rec_fx = run_id = run_dir = path = tl = None
t0 = time.time()
server, clients, started = None, {}, []
cur_phase = {"name": "pre"}
launch = {"epoch_ms": None}
out = {"phases": {}, "verdicts": {}, "summaries": {}, "notes": [], "steps": [], "world_changes": {"left_in_place": []}}


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


def mem(tag):
    row = {"tag": tag, "wall": wall(), "free_gb": free_gb()}
    out.setdefault("memory", []).append(row)
    return row


def grep_noecho(log, rx, limit):
    hits_, skipped = [], 0
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not rx.search(line):
                    continue
                if ECHO_RX.search(line):
                    skipped += 1
                    continue
                hits_.append(line.strip()[:600])
                if len(hits_) >= limit:
                    break
    except OSError:
        pass
    return hits_, skipped


def note(msg):
    out["notes"].append({"wall": wall(), "phase": cur_phase["name"], "note": msg})


def persist():
    if path is None:
        return
    try:
        out["timeline"] = list(tl.items) if tl is not None else []
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


def lread(side, root, paths, tag):
    return keep(step(tag, side, "lua.read", " ".join([root] + list(paths))))


def qread(tag):
    """One lua.read of the mod's queue state, the store's writes and the minute's counters."""
    a = lread(SRV, "_G", QPATHS, tag)
    v = a.get("values") or {}
    row = {k.split(".")[-1] if ".players." in k else k.replace(f"{NR}.server.", ""): num(v.get(k)) for k in QPATHS}
    row.update({"wall": a.get("wall"), "wall_after": a.get("wall_after"), "epoch_ms_before": a.get("epoch_ms_before"),
                "missing": a.get("missing"), "ok": a.get("ok")})
    return row


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
    if tl is not None:
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
    ok = False
    while True:
        a = lread(SRV, "_G", [f"{NR}.server.minute.stats.runs"], "S0_runs")
        runs = num((a.get("values") or {}).get(f"{NR}.server.minute.stats.runs"))
        recs = {u: gread(SRV, f"{NR}.server.store.records.{u}", f"S0_rec_{u}") for u in USERS}
        ok = all(r.get("resolved") for r in recs.values()) and runs is not None and runs >= MIN_RUNS
        polls.append({"wall": wall(), "records": {u: r.get("resolved") for u, r in recs.items()}, "runs": runs})
        if ok or time.time() >= end:
            break
        time.sleep(POLL_S)
    P["wait"] = {"ok": ok, "polls": polls}
    if not ok:
        note("S0: the real players' records or MIN_RUNS were not reached inside S0_WAIT_S")
    P["q"] = qread("S0_q")


def fmt_mult(v):
    v = num(v)
    if v is None:
        return "1"
    return repr(float(v))


def phase_B():
    P = out["phases"]["B"] = {"draws": []}
    P["snap0"] = snap("B_snap0")
    P["mult0"] = P["snap0"].get("mult")
    P["slow"] = keep(step("B_slow", SRV, "time.multiplier", str(SLOW_BENCH_MULT)))
    try:
        time.sleep(EMPTY_WAIT_S)
        P["q0"] = qread("B_q0")
        ticks0 = P["q0"].get("ticks")
        served = P["q0"].get("served")
        for i in range(BENCH_DRAWS):
            r = keep(step(f"B_bench{i}", SRV, "bench.global", f"{NR}.server.players.tick {BENCH_N}", timeout=90))
            q = qread(f"B_q{i + 1}")
            d = {"draw": i, "bench": r, "served_before": served, "served_after": q.get("served"),
                 "usPerCall": num(r.get("usPerCall")), "ms": num(r.get("ms")), "error": r.get("error"),
                 "ticks_after": q.get("ticks")}
            d["valid"] = (served is not None and q.get("served") == served and d["usPerCall"] is not None
                          and not r.get("error"))
            served = q.get("served")
            P["draws"].append(d)
        P["ticks_before"] = ticks0
        if ticks0 is not None:
            P["restore"] = keep(step("B_restore", SRV, "lua.setpath", f"{NR}.server.players.ticks {int(ticks0)}"))
        P["q_restored"] = qread("B_q_restored")
    finally:
        P["mult_restore"] = keep(step("B_mult_restore", SRV, "time.multiplier", fmt_mult(P.get("mult0"))))
    P["snap1"] = snap("B_snap1")
    m0 = num(P["q_restored"].get("minutes")) if P.get("q_restored") else None
    P["dropped"] = []
    end = time.time() + DROP_WAIT_S
    last = m0
    while time.time() < end and m0 is not None:
        q = qread("B_drop_poll")
        m = num(q.get("minutes"))
        if m is not None and last is not None and m > last:
            P["dropped"].append({k: q.get(k) for k in ("minutes", "ticksLast", "ticksPrev", "budgetMs", "runCap",
                                                       "meanMs", "served", "wall")})
            last = m
        if m is not None and m >= m0 + 2:
            break
        time.sleep(POLL_S)
    P["minutes_after_restore"] = (last - m0) if (last is not None and m0 is not None) else None


def load_arm(A, tag, sched):
    if sched is None:
        return
    load_sched = "mod" if sched == "mod" else sched
    A["load"] = keep(step(f"{tag}_load", SRV, "ghost.load", f"{N} {load_sched} feed", timeout=60))
    if not A["load"].get("ok"):
        note(f"{tag}: ghost.load failed: {A['load'].get('reason') or A['load'].get('raw')}")
    if sched == "mod":
        A["modq_on"] = keep(step(f"{tag}_modq_on", SRV, "ghost.modq", "on"))


def unload_arm(A, tag, sched):
    if sched == "mod":
        A["modq_off"] = keep(step(f"{tag}_modq_off", SRV, "ghost.modq", "off"))
    if sched is not None:
        A["stop"] = keep(step(f"{tag}_stop", SRV, "ghost.stop"))
        out["world_changes"]["left_in_place"].append(f"{tag}: {N - REALS} ghost records ran against admin and bob "
                                                     f"under {sched}")


def lat_read(tag, cap):
    end = time.time() + cap
    polls = 0
    r = {}
    while time.time() < end:
        if parked():
            break
        r = keep(step(f"{tag}_latread", ADMIN, "action.latency", "read"))
        polls += 1
        if r.get("done") is True:
            break
        time.sleep(LAT_POLL_S)
    r["polls"] = polls
    return r


def make_lat(tag, sched):
    def fn():
        A = out["phases"][tag] = {"tag": tag, "N": N if sched else None, "sched": sched, "mem_before": mem(f"{tag}_0")}
        A["q_pre"] = qread(f"{tag}_q_pre")
        load_arm(A, tag, sched)
        if sched is not None:
            time.sleep(SETTLE_S)
            A["reset"] = keep(step(f"{tag}_reset", SRV, "ghost.stats", "reset"))
        A["additem"] = rcon(f'additem "admin" "{LAT_FOOD}" {LAT_N}', f"{tag}_additem")
        time.sleep(SPAWN_WAIT_S)
        A["foodtimer"] = keep(step(f"{tag}_foodtimer", SRV, "foodtimer.set", "admin 0"))
        A["q_start"] = qread(f"{tag}_q_start")
        A["perf_arm"] = keep(step(f"{tag}_perf_arm", SRV, "perf.local", str(PERF_N)))
        A["ring_arm"] = keep(step(f"{tag}_ring_arm", SRV, "tick.ring", str(RING_N)))
        A["window_start_wall"] = wall()
        A["lat_arm"] = keep(step(f"{tag}_lat", ADMIN, "action.latency", f"{LAT_FOOD} {LAT_N}"))
        A["lat"] = lat_read(tag, LAT_CAP_S)
        A["window_end_wall"] = wall()
        after = time.time() - 1.0
        A["perf_read"] = keep(step(f"{tag}_perf_read", SRV, "perf.local", f"read {tag}"))
        A["ring_read"] = keep(step(f"{tag}_ring_read", SRV, "tick.ring", f"read {tag}"))
        if sched is not None:
            A["stats"] = keep(step(f"{tag}_stats", SRV, "ghost.stats"))
        A["q_end"] = qread(f"{tag}_q_end")
        A["perf_doc"] = wait_doc(f"perf-local-{tag}", after)
        A["ring_doc"] = wait_doc(f"tick-ring-{tag}", after)
        unload_arm(A, tag, sched)
        A["drop_windows"] = [span(A["ring_arm"]), span(A["perf_read"])]
        A["mem_after"] = mem(f"{tag}_1")
    return fn


def phase_NF():
    P = out["phases"]["NF"] = {}
    P["arm"] = keep(step("NF_lat", ADMIN, "action.latency", f"{NONFOOD} 1"))
    P["read"] = lat_read("NF", 30.0)
    P["parked"] = parked()


def phase_W():
    P = out["phases"]["W"] = {}
    P["boredom_bare"] = keep(step("W_bored_bare", SRV, "stats.bench", f"admin BOREDOM {STAT_BENCH_N}", timeout=90))
    P["boredom_wrapped"] = keep(step("W_bored_wrapped", SRV, "stats.bench", f"admin BOREDOM {STAT_BENCH_N} wrapped",
                                     timeout=90))
    P["writer"] = {}
    for n in WRITER_NS:
        P["writer"][str(n)] = keep(step(f"W_writer_{n}", SRV, "bench.global", f"{NR}.bench_writer {n}", timeout=120))


def phase_FC():
    tag = "FC"
    A = out["phases"][tag] = {"tag": tag, "N": N, "sched": "mod", "mem_before": mem("FC_0")}
    A["snap0"] = snap("FC_snap0")
    A["q_pre"] = qread("FC_q_pre")
    load_arm(A, tag, "mod")
    A["speed_up"] = rcon(f"settimespeed {FAST_SPEED}", "FC_speed_up")
    out["world_changes"]["left_in_place"].append(f"FC: settimespeed {FAST_SPEED} for the arm, restored to 1 after")
    try:
        time.sleep(SETTLE_S)
        A["reset"] = keep(step("FC_reset", SRV, "ghost.stats", "reset"))
        A["q_start"] = qread("FC_q_start")
        A["snap_fast"] = snap("FC_snap_fast")
        A["perf_arm"] = keep(step("FC_perf_arm", SRV, "perf.local", str(PERF_N)))
        A["ring_arm"] = keep(step("FC_ring_arm", SRV, "tick.ring", str(RING_N)))
        A["window_start_wall"] = wall()
        time.sleep(FC_WALL_S)
        A["window_end_wall"] = wall()
        after = time.time() - 1.0
        A["perf_read"] = keep(step("FC_perf_read", SRV, "perf.local", "read FC"))
        A["ring_read"] = keep(step("FC_ring_read", SRV, "tick.ring", "read FC"))
        A["stats"] = keep(step("FC_stats", SRV, "ghost.stats"))
        A["q_end"] = qread("FC_q_end")
        A["perf_doc"] = wait_doc("perf-local-FC", after)
        A["ring_doc"] = wait_doc("tick-ring-FC", after)
    finally:
        A["speed_restore"] = rcon("settimespeed 1", "FC_speed_restore")
    A["snap1"] = snap("FC_snap1")
    unload_arm(A, tag, "mod")
    A["drop_windows"] = [span(A["ring_arm"]), span(A["perf_read"])] if A.get("perf_read") else []
    A["mem_after"] = mem("FC_1")


def phase_ST():
    tag = "ST"
    A = out["phases"][tag] = {"tag": tag, "N": N, "sched": "mod", "mem_before": mem("ST_0")}
    A["q_pre"] = qread("ST_q_pre")
    load_arm(A, tag, "mod")
    time.sleep(STALL_WARM_S)
    A["warm_stats"] = keep(step("ST_warm_stats", SRV, "ghost.stats"))
    A["hold"] = keep(step("ST_hold", SRV, "ghost.modq", "off"))
    A["snap_hold"] = snap("ST_snap_hold")
    a0 = num(A["snap_hold"].get("worldAge"))
    end = time.time() + STALL_GAP_CAP_S
    gap = None
    polls = 0
    while time.time() < end:
        time.sleep(2.0)
        s = snap("ST_gap_poll")
        polls += 1
        a1 = num(s.get("worldAge"))
        if a0 is not None and a1 is not None:
            gap = (a1 - a0) * 60.0
            if gap >= STALL_GAP_MIN:
                break
    A["hold_gap_game_minutes"] = gap
    A["hold_polls"] = polls
    A["q_start"] = qread("ST_q_start")
    A["perf_arm"] = keep(step("ST_perf_arm", SRV, "perf.local", str(PERF_N)))
    A["ring_arm"] = keep(step("ST_ring_arm", SRV, "tick.ring", str(RING_N)))
    A["reset"] = keep(step("ST_reset", SRV, "ghost.stats", "reset"))
    A["modq_on2"] = keep(step("ST_release", SRV, "ghost.modq", "on"))
    A["window_start_wall"] = wall()
    time.sleep(STALL_READ_S)
    A["window_end_wall"] = wall()
    after = time.time() - 1.0
    A["perf_read"] = keep(step("ST_perf_read", SRV, "perf.local", "read ST"))
    A["ring_read"] = keep(step("ST_ring_read", SRV, "tick.ring", "read ST"))
    A["stats"] = keep(step("ST_stats", SRV, "ghost.stats"))
    A["q_end"] = qread("ST_q_end")
    A["perf_doc"] = wait_doc("perf-local-ST", after)
    A["ring_doc"] = wait_doc("tick-ring-ST", after)
    unload_arm(A, tag, "mod")
    A["drop_windows"] = []
    A["bus_spans"] = {"reset": span(A["reset"]), "release": span(A["modq_on2"]), "ring_arm": span(A["ring_arm"]),
                      "perf_read": span(A["perf_read"])}
    A["mem_after"] = mem("ST_1")


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["stop_left"] = keep(step("Z_stop", SRV, "ghost.stop"))
    P["modq_off"] = keep(step("Z_modq_off", SRV, "ghost.modq", "off"))
    P["players"] = keep(step("Z_players", SRV, "players"))
    P["time"] = snap("Z_time")
    P["q"] = qread("Z_q")
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:20]
    P["admin_parked"] = parked()
    P["mem"] = mem("Z")


def body():
    order = [("S0", phase_S0), ("B", phase_B)]
    order += [(tag, make_lat(tag, sched)) for tag, sched in LAT_ARMS]
    order += [("NF", phase_NF), ("W", phase_W), ("FC", phase_FC), ("ST", phase_ST), ("Z", phase_Z)]
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


def delta(A, key):
    a, b = g(A, "q_start", key), g(A, "q_end", key)
    return (b - a) if a is not None and b is not None else None


def seam_allowance(A):
    a, b = g(A, "q_start", "epoch_ms_before"), g(A, "q_end", "epoch_ms_before")
    if a is None or b is None:
        return None, None
    span_s = (b - a) / 1000.0
    return span_s, REALS * (int(span_s // SAVE_GAP_S) + 1) + int(span_s // INDEX_GAP_S) + 1


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
    span_ms = (kept[-1]["stop"] - kept[0]["start"]) if len(kept) >= 2 else None
    S = {"N": A.get("N"), "sched": A.get("sched"), "frames_ring": len(fr), "frames": len(kept),
         "frames_dropped": len(fr) - len(kept), "minute_frames": len(mins), "kept_span_ms": span_ms,
         "busy": summ(busy), "busy_minute": summ([f["busy"] for f in mins]),
         "busy_other": summ([f["busy"] for f in rest]), "endPeriod": summ(endp), "period": summ(per),
         "busy_sum": sum(busy), "busy_ms_per_frame": (sum(busy) / len(busy)) if busy else None,
         "busy_ms_per_game_minute": (sum(busy) / len(mins)) if mins else None,
         "ghostMs_sum": sum((f["ghostMs"] or 0) for f in kept), "runs_sum": sum((f["runs"] or 0) for f in kept),
         "ghostMs_minute": summ([f["ghostMs"] for f in mins]), "runs_frame": summ([f["runs"] for f in kept]),
         "frames_with_runs_ring": sum(1 for f in kept if (f["runs"] or 0) > 0),
         "perf_windows": len(pw), "perf_kept": len(pk), "perf_max": summ([r["max"] for r in pk]),
         "top5_endPeriod": [{k: f[k] for k in ("frame", "start", "busy", "period", "endPeriod", "minute", "runs",
                                                 "ghostMs")} for f in sorted(kept, key=lambda f: -(f["endPeriod"] or -1))[:5]],
         "top5_busy": [{k: f[k] for k in ("frame", "start", "busy", "period", "endPeriod", "minute", "runs",
                                             "ghostMs")} for f in sorted(kept, key=lambda f: -(f["busy"] or -1))[:5]]}
    # Rule 6: the worst frame and how often it comes
    per100 = (100000.0 / span_ms) if span_ms else None
    freq = {}
    for t in FREQ_MS:
        c = sum(1 for x in endp if x > t)
        freq[f"endPeriod_over{t}"] = c
        freq[f"endPeriod_over{t}_per100s"] = (c * per100) if per100 else None
    for t in BUSY_MS:
        c = sum(1 for x in busy if x >= t)
        freq[f"busy_ge{t}"] = c
        freq[f"busy_ge{t}_per100s"] = (c * per100) if per100 else None
    if idle is not None and g(idle, "endPeriod", "max") is not None:
        im = idle["endPeriod"]["max"]
        c = sum(1 for x in endp if x > im)
        freq["endPeriod_over_idle_max"] = c
        freq["endPeriod_over_idle_max_per100s"] = (c * per100) if per100 else None
    if endp:
        top = max(endp)
        freq["endPeriod_max_count"] = sum(1 for x in endp if x == top)
        freq["endPeriod_within5_of_max"] = sum(1 for x in endp if x >= top - 5)
    if pk:
        pm = max(r["max"] for r in pk)
        freq["perf_windows_at_max"] = sum(1 for r in pk if r["max"] == pm)
        freq["perf_windows_over_idle_max"] = (sum(1 for r in pk if r["max"] > g(idle, "perf_max", "max"))
                                              if idle is not None and g(idle, "perf_max", "max") is not None else None)
    S["rule6"] = {"endPeriod_max": g(S, "endPeriod", "max"), "busy_max": g(S, "busy", "max"),
                  "perf_max_max": g(S, "perf_max", "max"), "freq": freq}
    if mins:
        S["ghost_ms_per_game_minute_ring"] = S["ghostMs_sum"] / len(mins)
    if st.get("ok"):
        S["ghost"] = {k: st.get(k) for k in GHOST_KEYS}
        runs, ms = num(st.get("runs")), num(st.get("ms"))
        S["ghost_ms_per_run"] = (ms / runs) if runs else None
        mev = num(st.get("minuteEventsSince"))
        S["ghost_ms_per_minute_event"] = (ms / mev) if mev else None
        S["ghost_runs_per_minute_event"] = (runs / mev) if mev else None
        fwr = num(st.get("framesWithRuns"))
        S["batching"] = {"ghost_runs": runs, "minuteEventsSince": mev, "framesWithRuns": fwr,
                         "framesWithRuns_per_minute_event": (fwr / mev) if (fwr is not None and mev) else None,
                         "served_delta": delta(A, "served"), "minutes_delta": delta(A, "minutes"),
                         "drained_delta": delta(A, "drained"),
                         "non_ghost_served": (delta(A, "served") - runs) if (delta(A, "served") is not None
                                                                              and runs is not None) else None}
    S["queue"] = {"start": {k: g(A, "q_start", k) for k in ("served", "meanMs", "budgetMs", "runCap", "ticksLast",
                                                            "ticksPrev", "minutes")},
                  "end": {k: g(A, "q_end", k) for k in ("served", "meanMs", "budgetMs", "runCap", "ticksLast",
                                                        "ticksPrev", "minutes")}}
    span_s, allow = seam_allowance(A)
    S["seam"] = {"writes_delta": delta(A, "store.file.stats.writes"), "bytes_delta": delta(A, "store.file.stats.bytes"),
                 "span_s": span_s, "allowance": allow}
    S["seam"]["void"] = (S["seam"]["writes_delta"] is not None and allow is not None
                         and S["seam"]["writes_delta"] > allow)
    if A.get("sched_read"):
        S["spread"] = {k: g(A, "sched_read", k) for k in ("k", "armed", "minutes", "capped", "errors", "lastSpread",
                                                           "lastShipped", "lastQueued", "lastTpm", "lastLowered",
                                                           "runCap", "budgetMs", "meanMs", "lastError")}
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


def mean(xs):
    xs = [x for x in xs if x is not None]
    return (sum(xs) / len(xs)) if xs else None


def lat_summary(A):
    L = A.get("lat") or {}
    samples = L.get("samples") or []
    if isinstance(samples, dict):                  # a Lua array may come back keyed "1".."n"
        samples = [samples[k] for k in sorted(samples, key=lambda x: int(x) if str(x).isdigit() else 0)]
    ms = [num(s.get("ms")) for s in samples if isinstance(s, dict)]
    done = [s.get("done") for s in samples if isinstance(s, dict)]
    mt = [num(s.get("maxTime")) for s in samples if isinstance(s, dict)]
    xs = sorted(x for x in ms if x is not None)
    med = None
    if xs:
        k = len(xs) // 2
        med = xs[k] if len(xs) % 2 else (xs[k - 1] + xs[k]) / 2.0
    return {"n": len(samples), "ms": ms, "done": done, "maxTime": mt, "median_ms": med,
            "max_ms": max(xs) if xs else None, "min_ms": min(xs) if xs else None, "reason": L.get("reason"),
            "read_done": L.get("done"), "polls": L.get("polls")}


def catchup(A):
    fr = frames_of(A.get("ring_doc"))
    rel = g(A, "modq_on2", "epoch_ms_before")
    if not fr or rel is None:
        return None
    after = [f for f in fr if f["start"] is not None and f["start"] >= rel - 100]
    need = N - REALS
    cum, idx, mins = 0, None, 0
    first_min = None
    for i, f in enumerate(after):
        if f["minute"] == 1:
            mins += 1
            if first_min is None:
                first_min = i
        cum += f["runs"] or 0
        if idx is None and cum >= need:
            idx = i
            break
    C = {"release_epoch_ms": rel, "frames_after": len(after), "need_runs": need, "first_minute_frame": first_min}
    if idx is None:
        C["complete"] = False
        C["runs_seen"] = cum
        return C
    cu = [f for f in after[:idx + 1] if (f["runs"] or 0) > 0 or f["minute"] == 1]
    steady = [f for f in after[idx + 1:]]
    sr = [f for f in steady if (f["runs"] or 0) > 0]

    def per_run(fs):
        r = sum(f["runs"] or 0 for f in fs)
        return (sum(f["ghostMs"] or 0 for f in fs) * 1000.0 / r) if r else None

    C.update({"complete": True, "minute_events_to_complete": mins, "frames_to_complete": idx + 1,
              "catchup_frames": [{k: f[k] for k in ("frame", "start", "busy", "period", "endPeriod", "minute", "runs",
                                                    "ghostMs")} for f in after[:idx + 1] if (f["runs"] or 0) > 0],
              "catchup_busy_max": max((f["busy"] for f in cu if f["busy"] is not None), default=None),
              "catchup_endPeriod_max": max((f["endPeriod"] for f in cu if f["endPeriod"] is not None), default=None),
              "catchup_us_per_run": per_run([f for f in after[:idx + 1]]),
              "catchup_runs": sum(f["runs"] or 0 for f in after[:idx + 1]),
              "catchup_ghost_ms": sum(f["ghostMs"] or 0 for f in after[:idx + 1]),
              "steady_us_per_run": per_run(sr), "steady_runs": sum(f["runs"] or 0 for f in sr),
              "steady_busy": summ([f["busy"] for f in steady]), "steady_endPeriod": summ([f["endPeriod"] for f in steady]),
              "steady_frames": len(steady)})
    # the next three minute events' frames (from the first minute frame after the release)
    if first_min is not None:
        win, k = [], 0
        for f in after[first_min:]:
            if f["minute"] == 1:
                k += 1
                if k > CATCHUP_EVENTS:
                    break
            win.append(f)
        C["next3"] = {"frames": len(win), "busy": summ([f["busy"] for f in win]),
                      "endPeriod": summ([f["endPeriod"] for f in win]), "runs": sum(f["runs"] or 0 for f in win),
                      "ghostMs": sum(f["ghostMs"] or 0 for f in win), "us_per_run": per_run(win)}
    return C


def grade_all():
    ph = out["phases"]
    S = out["summaries"]
    # B: the empty check
    B = ph.get("B") or {}
    draws = B.get("draws") or []
    if draws:
        valid = [d for d in draws if d.get("valid")]
        S["empty"] = {"usPerCall": [d.get("usPerCall") for d in draws], "valid": [d.get("valid") for d in draws],
                      "ms": [d.get("ms") for d in draws], "served": [[d.get("served_before"), d.get("served_after")]
                                                                     for d in draws]}
        ok = len(valid) == len(draws) and all(d["usPerCall"] <= EMPTY_MAX_US for d in valid)
        grade("EMPTY", PRED["EMPTY"], S["empty"], "as_predicted" if ok else
              ("unmeasured" if not valid else "falsified"), "a draw over 100 us a call, or a drain inside a draw")
        rb = num(g(B, "q_restored", "ticks"))
        tb = num(B.get("ticks_before"))
        S["restore"] = {"ticks_before": tb, "restore_ack": B.get("restore"), "ticks_read_back": rb,
                        "ticks_after_benches": [d.get("ticks_after") for d in draws]}
        ra = num(g(B, "restore", "after"))
        S["restore"]["setpath_after"] = ra
        grade("RESTORE", PRED["RESTORE"], S["restore"], "unmeasured" if ra is None or tb is None else
              ("as_predicted" if ra == tb and g(B, "restore", "ok") is True else "falsified"),
              "lua.setpath's own read-back (after) not the value read before the first bench; the later lua.read "
              "adds the frames between the two reads")
        mar = B.get("minutes_after_restore")
        grade("DROP", PRED["DROP"], {"minutes_after_restore": mar, "dropped": B.get("dropped")},
              "unmeasured" if mar is None else ("as_predicted" if mar >= 2 else "falsified"), "fewer than two minutes")
    else:
        for k in ("EMPTY", "RESTORE", "DROP"):
            grade(k, PRED[k], None, "unmeasured", "phase B took no draw")
    # L: latency and the frames under each arm
    lat = S["latency"] = {}
    idle = None
    for tag, sched in LAT_ARMS:
        A = ph.get(tag) or {}
        if not A:
            continue
        lat[tag] = lat_summary(A)
        if A.get("ring_doc"):
            S[tag] = arm_summary(A, idle)
            if tag == "Lidle":
                idle = S[tag]
    if lat:
        bad = {t: v for t, v in lat.items() if v["n"] != LAT_N or not all(d is True for d in v["done"])}
        lat["burst_vs_mod"] = {"median_ms": [g(lat, "Lburst", "median_ms"), g(lat, "Lmod", "median_ms")],
                               "max_ms": [g(lat, "Lburst", "max_ms"), g(lat, "Lmod", "max_ms")],
                               "idle_median_ms": g(lat, "Lidle", "median_ms"), "idle_max_ms": g(lat, "Lidle", "max_ms")}
        grade("LAT", PRED["LAT"], {t: {k: v.get(k) for k in ("n", "ms", "done", "median_ms", "max_ms", "reason")}
                                   for t, v in lat.items() if t != "burst_vs_mod"},
              "as_predicted" if not bad and len([t for t in lat if t != "burst_vs_mod"]) == len(LAT_ARMS)
              else "falsified", "an arm short of samples or a sample not done", {"bad": list(bad)})
    else:
        grade("LAT", PRED["LAT"], None, "unmeasured", "no latency arm")
    NF = ph.get("NF") or {}
    if NF:
        rd = NF.get("read") or {}
        ok = rd.get("done") is True and rd.get("reason") == "not a Food item" and not NF.get("parked") \
            and not out.get("admin_lua_error")
        grade("NONFOOD", PRED["NONFOOD"], {"arm": NF.get("arm"), "read": {k: rd.get(k) for k in ("ok", "done", "reason",
                                                                                                 "n", "samples")},
                                           "parked": NF.get("parked")},
              "as_predicted" if ok else "falsified", "no 'not a Food item' reply, or admin parked")
    else:
        grade("NONFOOD", PRED["NONFOOD"], None, "unmeasured", "phase NF not run")
    W = ph.get("W") or {}
    if W:
        bb, bw = W.get("boredom_bare") or {}, W.get("boredom_wrapped") or {}
        wr = W.get("writer") or {}
        S["real_costs"] = {
            "boredom_bare_usPerPair": num(bb.get("usPerPair")), "boredom_bare_ms": num(bb.get("ms")),
            "boredom_bare_loopMs": num(bb.get("loopMs")), "boredom_wrapped_usPerPair": num(bw.get("usPerPair")),
            "boredom_wrapped_ms": num(bw.get("ms")), "boredom_wrapped_loopMs": num(bw.get("loopMs")),
            "writer_usPerCall": {n: num(g(wr, n, "usPerCall")) for n in wr}, "writer_ms": {n: num(g(wr, n, "ms"))
                                                                                          for n in wr}}
        rc = S["real_costs"]
        if rc["boredom_wrapped_usPerPair"] is not None:
            rc["boredom_lane_ms_at_60_a_rising_minute"] = rc["boredom_wrapped_usPerPair"] * 60 / 1000.0
        w100 = rc["writer_usPerCall"].get(str(WRITER_NS[-1]))
        if w100 is not None:
            rc["writer_ms_at_60_a_minute_event"] = w100 * 60 / 1000.0
        ok = bb.get("ok") is True and bw.get("ok") is True and all(
            num(g(wr, str(n), "usPerCall")) is not None and not g(wr, str(n), "error") for n in WRITER_NS)
        grade("BENCH", PRED["BENCH"], rc, "as_predicted" if ok else "falsified", "a bench without its figure")
    else:
        grade("BENCH", PRED["BENCH"], None, "unmeasured", "phase W not run")
    FC = ph.get("FC") or {}
    if FC.get("ring_doc"):
        S["FC"] = arm_summary(FC, idle)
        st = FC.get("stats") or {}
        S["FC"]["fast"] = {"maxStaleGameMinutes": num(st.get("maxStaleGameMinutes")),
                           "staleGameNowMax": num(st.get("staleGameNowMax")),
                           "starvedEvents": num(st.get("starvedEvents")), "minuteEventsSince": num(st.get("minuteEventsSince")),
                           "usPerRun": num(st.get("usPerRun")), "mult_fast": g(FC, "snap_fast", "mult"),
                           "mult_after": g(FC, "snap1", "mult"), "mult_before": g(FC, "snap0", "mult")}
        f = S["FC"]["fast"]
        ok = f["maxStaleGameMinutes"] is not None and f["maxStaleGameMinutes"] <= FAST_STALE_MAX \
            and S["FC"]["frames"] >= FC_MIN_FRAMES
        grade("FAST", PRED["FAST"], {**f, "frames": S["FC"]["frames"], "endPeriod": S["FC"]["endPeriod"],
                                     "period": S["FC"]["period"], "perf_max": S["FC"]["perf_max"],
                                     "busy": S["FC"]["busy"]},
              "unmeasured" if f["maxStaleGameMinutes"] is None else ("as_predicted" if ok else "falsified"),
              "a ghost staler than 15 game minutes, or too few frames")
    else:
        grade("FAST", PRED["FAST"], None, "unmeasured", "no fast-clock ring")
    ST = ph.get("ST") or {}
    if ST.get("ring_doc"):
        S["ST"] = arm_summary(ST, idle)
        C = S["ST"]["catchup"] = catchup(ST)
        before = g(ST, "reset", "before") or {}
        sg = before.get("staleGameMinutes") or []
        if isinstance(sg, dict):
            sg = list(sg.values())
        sg = [num(x) for x in sg if num(x) is not None]
        S["ST"]["stale_at_release"] = {"min": min(sg) if sg else None, "max": max(sg) if sg else None, "n": len(sg),
                                       "hold_gap_game_minutes": ST.get("hold_gap_game_minutes")}
        ok1 = bool(sg) and min(sg) >= 60.0
        ok2 = bool(C) and C.get("complete") and C.get("minute_events_to_complete") is not None \
            and C["minute_events_to_complete"] <= CATCHUP_EVENTS
        ok3 = bool(C) and C.get("catchup_us_per_run") is not None and C.get("steady_us_per_run") is not None \
            and C["catchup_us_per_run"] > C["steady_us_per_run"]
        grade("STALL", PRED["STALL"], {"stale_at_release": S["ST"]["stale_at_release"],
                                       "catchup": {k: (C or {}).get(k) for k in (
                                           "complete", "minute_events_to_complete", "frames_to_complete",
                                           "catchup_busy_max", "catchup_endPeriod_max", "catchup_us_per_run",
                                           "steady_us_per_run", "catchup_runs", "steady_runs")},
                                       "next3": (C or {}).get("next3"), "perf_max": S["ST"]["perf_max"]},
              "as_predicted" if (ok1 and ok2 and ok3) else "falsified",
              "a ghost under 60 game minutes stale, the catch-up not done in 3 minute events, or no costlier run",
              {"parts": {"gap": ok1, "complete": ok2, "costlier": ok3}})
    else:
        grade("STALL", PRED["STALL"], None, "unmeasured", "no stall ring")
    loaded = [t for t, s in LAT_ARMS if s is not None] + ["FC", "ST"]
    have = [t for t in loaded if t in S]
    if have:
        badS = {}
        for t in have:
            gh = S[t].get("ghost") or {}
            if gh.get("failures") != 0 or gh.get("storeGhostKeys") != 0:
                badS[t] = {k: gh.get(k) for k in ("failures", "storeGhostKeys", "lastError")}
        grade("S", PRED["S"], {t: {k: g(S, t, "ghost", k) for k in ("failures", "storeGhostKeys", "neverRun")}
                               for t in have}, "as_predicted" if not badS else "falsified", "a failure or a leak",
              {"bad": badS})
        seam = {t: S[t]["seam"] for t in have}
        voids = [t for t in have if S[t]["seam"]["void"]]
        unread = [t for t in have if S[t]["seam"]["writes_delta"] is None]
        grade("SEAM", PRED["SEAM"], seam, "as_predicted" if not voids and not unread else "falsified",
              "a writes rise above the allowance", {"void_arms": voids, "unread_arms": unread})
    else:
        for k in ("S", "SEAM"):
            grade(k, PRED[k], None, "unmeasured", "no loaded arm")
    every = [t for t in ["Lidle"] + have if t in S]
    S["rule6_table"] = {t: {"sched": g(S, t, "sched"), **(g(S, t, "rule6") or {}),
                            "adds_p99_endPeriod": g(S, t, "adds", "endPeriod", "p99"),
                            "adds_max_perf": g(S, t, "adds", "perf_max", "max")} for t in every}
    gc = out.get("gc") or {}
    grade("G", PRED["G"], {"exists": gc.get("exists"), "pause_events": gc.get("pause_events"),
                           "pause_max_ms": gc.get("pause_max_ms"), "stall_events": gc.get("stall_events"),
                           "arm_pause_max_ms": {t: g(S, t, "gc", "pause_max_ms") for t in every}},
          "as_predicted" if gc.get("exists") else "falsified", "gc.log absent")
    Z = ph.get("Z") or {}
    if Z:
        mb, ma = num(g(FC, "snap0", "mult")), num(g(FC, "snap1", "mult"))
        restored = (mb is not None and ma is not None and abs(mb - ma) < 1e-6)
        obs = {"server_mod_error_lines": Z.get("server_mod_error_lines") or [],
               "admin_lua_error": out.get("admin_lua_error"), "speed_restored": restored, "mult_before_fc": mb,
               "mult_after_fc": ma, "z_mult": g(Z, "time", "mult")}
        ok = not obs["server_mod_error_lines"] and not obs["admin_lua_error"] and restored
        grade("Z", PRED["Z"], obs, "as_predicted" if ok else "falsified", "a mod error line, admin parked, speed not back")
    else:
        grade("Z", PRED["Z"], None, "unmeasured", "phase Z not run")


# ---------------------------------------------------------------- run
def main():
    global prof, rec_fx, run_id, run_dir, path, tl, t0, server, clients, out
    prof = profile.load(PROFILE)
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(PREFIX)
    path = os.path.join(run_dir, ARTIFACT)
    tl, t0 = Timeline(), time.time()
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
                 "staging": "python tools/release_pack.py stage mod/NutritionRevamp --out release/plan11-x39 at "
                            "513778e8 (Plan 11b Task 2); no instrument added",
                 "seams_note": "Every ghost run, in every loaded arm, runs the writer dry (W.dry) and skips the store "
                               "step for ghost names (S.skip = H0.isGhost), set inside H0.work, which every scheduler "
                               "calls (Plan 11a ruling 15).",
                 "batching_note": "burst times its 58 ghost runs in one batch at the minute event; mod keeps one "
                                  "batch open across a drain's contiguous ghost runs and closes it at a real player's "
                                  "run, a task or the drain's end (H0.modRun, H0.modWrap).",
                 "cost_note": "Every server reading is cost, not behaviour: the ghosts run copies of the real records "
                              "against the two real IsoPlayers. The two real players stay on the mod's own drain.",
                 "timer_note": "getTimestampMs is 1 ms resolution: a frame's busy is a 1 ms reading; every per-run cost "
                               "is a total over many runs divided by their count."},
        "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                      if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict,
                                                                             re.Pattern))
                      and k not in ("REPO", "PRED")},
        "predictions": PRED,
        "deviations": [
            "The empty-check bench takes three draws (the plan names one), with one restore of players.ticks after the "
            "third.",
            "The stall is induced by holding the ghosts out of the mod's queue (ghost.modq off) for at least sixty game "
            "minutes, not by raising time.multiplier; the two real players are not stalled.",
            "The ghost records carry no monotony seed in this session (the run sheet seeds S2a-S2d only).",
        ],
        "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                          "left_in_place": []},
        "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
        "summaries": {}, "memory": [],
    }
    try:
        out["meta"]["harness_server_sha256"] = sha256_file(os.path.join(REPO, HARNESS_SERVER))
        out["meta"]["staged_manifest_sha256"] = sha256_file(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME))
        out["meta"]["staged_manifest_expected"] = MANIFEST_SHA256
    except OSError as e:
        out["meta"]["hash_error"] = f"{type(e).__name__}: {e}"
    if not doctor_clean:
        out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
        persist()
        print(json.dumps(out["doctor"], indent=1))
        sys.exit(1)
    if out["meta"].get("staged_manifest_sha256") != MANIFEST_SHA256:
        out["error"] = "the staged MANIFEST differs from the expected one; the session was not started"
        persist()
        sys.exit(1)
    m0 = mem("preboot")
    if m0["free_gb"] is None or m0["free_gb"] < MIN_FREE_GB:
        out["error"] = f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started"
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
                print(f"copied to {dest_dir}")
            except Exception as e:                 # noqa: BLE001 - never raise
                print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "empty": g(out, "summaries", "empty"), "latency": g(out, "summaries", "latency"),
                      "real_costs": g(out, "summaries", "real_costs"), "fast": g(out, "summaries", "FC", "fast"),
                      "stall": {k: g(out, "summaries", "ST", "catchup", k) for k in (
                          "complete", "minute_events_to_complete", "catchup_busy_max", "catchup_endPeriod_max",
                          "catchup_us_per_run", "steady_us_per_run")},
                      "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "run_id": run_id,
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])

if __name__ == "__main__":
    main()
