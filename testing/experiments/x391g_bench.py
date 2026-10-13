"""x391g-bench -- Plan 11b Task 2 (live), the confirmatory session x391g (ruling T2-1): the slot-save price, own-action
latency at the NORMAL clock and, if time allows, one seeded-record `mod` arm at the normal clock, at N = 60 ghost
records beside the two real players. On the staged copy of the tree at 513778e8 (release/plan11-x39/NutritionRevamp/
Contents/mods/NutritionRevamp, MANIFEST.json sha256 83c79a04...52c0; release/ is gitignored; mod/ is never booted;
`git log 513778e8..HEAD -- mod/` empty, checked before the boot), on the FIXED harness (016dce05: a ghost run restores
its carrier's vanilla macro stores; time.snapshot reports the true multiplier), build 42.21.0 (4a0e9546ec), Nutrition
false. One boot of profile x39-shootout-g (fixture two, admin -debug then bob release, the FIXTURE's DayLength (4:
a game minute is 3.75 s of wall, about 37.5 ticks) with no time.multiplier call, gclog true, + TKX_StudyFoods for the
seed). Artifact: `bench.json`, the staged MANIFEST.json and the server's gc.log copied byte-identical beside it
(server-stdout.log as x391a-e: the controller copies it when it is the evidence of an event). Shape: x391e_owed.py's
(its helpers, its latency arms and non-Food smoke, its grading helpers), with x391d's arm (run_arm) and seed. Written
BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2). The driver
asserts that its PREFIX and PROFILE match its own file name, that PZTestKit_Server.lua holds the carrier-restore
wrapper (HARNESS_MARKERS) and records HARNESS_COMMIT; it refuses to boot otherwise.

WHY: the ghosts skip the store step (Plan 11a ruling 15), so no shoot-out prices the real players' slot save; at 60
real players a save comes about once a second (each player at most once a real minute, S.SAVE_GAP_MS 60000). x391e's
own-action latency was read at about 5x clock (the multiplier restore set getMultiplier's value), so it is re-read here
at the normal clock.

PHASES: S0 (ready, records, MIN_RUNS; time.snapshot recorded as mult = trueMult (getTrueMultiplier) and eff = mult
(getMultiplier)), then
  P   THE SLOT-SAVE PRICE: a lua.read of the store's counters; `store.probe roundtrip save` (one synthetic
      non-ASCII-named record saved through the mod's own F.save, never put in store.records, so the players' queue
      never runs it; bench needs it); a pilot `store.probe bench PILOT_N`; n picked from the pilot so that a draw
      (n intact reads plus n writes) stays near DRAW_TARGET_MS (under about 2 s): n = clamp(floor(DRAW_TARGET_MS /
      the pilot's ms an iteration), N_MIN, N_MAX); then BENCH_DRAWS draws of `store.probe bench <n>`; then
      `store.probe clear` (from the phase's finally) and the counters again. Read per draw: usPerWrite, usPerIntact,
      writeMs, intactMs, bytes, mismatches, failed. The bench puts the store's counters back, so the seam reads after
      count only the mod's own saves (the roundtrip save and the clear's index write land between P's two reads).
      Each draw is one long server frame by design; no arm is open across P.
  I   THE IDLE ARM: x391d's run_arm with no load, ARM_WALL_S of ring and perf, the reference every later arm's adds
      are taken against.
  L   OWN-ACTION LATENCY on admin at the normal clock (x391e's, verbatim but for SETTLE_S and the idle reference), arms
      Lidle, Lburst (`ghost.load 60 burst feed`) and Lmod (`ghost.load 60 mod feed` + `ghost.modq on`), each: the
      load and SETTLE_S, ghost.stats reset, RCON `additem "admin" "Base.Apple" 3`, SPAWN_WAIT_S, `foodtimer.set
      admin 0`, perf.local and tick.ring armed, `action.latency Base.Apple 3` on client:admin and `action.latency
      read` polled until done or LAT_CAP_S; then the server reads and the stop. Then the NON-FOOD SMOKE (x391e's):
      `action.latency Base.Hammer 1`, which answers reason "not a Food item" without parking the -debug client.
  (3) IF TIME ALLOWS (wall() <= PART3_LATEST_S when NF ends, so the seed, the arm, Z and the teardown fit 15 minutes):
  SEED  x391b's monotony seed (RCON additem TKX.Mono450 x SEED_EATS to each player, then eat.action rounds on both
      clients), so the real records hold food and absorption runs;
  Gmod  x391d's mod arm at the normal clock: ghost.load 60 mod feed -> ghost.modq on -> SETTLE_S -> ghost.stats reset
      -> ARM_WALL_S of ring and perf -> ghost.stats -> modq off -> stop, with the queue, store and attribution reads at
      the start and end, for the worst frame and its rate.
  Z   the stops, the logs.

THE MULTIPLIER: no time.multiplier call anywhere (a bare one would set 1, and any call changes the clock under test);
time.snapshot at S0 and before every arm records mult (trueMult) and eff (mult). Nothing is graded on eff.

THE SEAMS (Plan 11a ruling 15): every ghost run (burst and mod alike) runs the writer dry and skips the store step for
ghost names, set inside H0.work; since 016dce05 H0.work also restores the carrier's macros after each ghost run. An
arm is VOID when the store's index gains a key, a ghost record is in the store, or the writes exceed REALS x (minute
events + 1) + floor(span / 300) + 1 (x391d's rule). THE SEAM CHECK (CARRIER, as x391f): in the arms with no eat
in the window (I and Gmod), the store's writes delta from the window's start to its end is at most REALS x
(floor(span / 60) + 1) + floor(span / 300) + 1, plus one save per intake landing in that arm (a late seed eat landing
inside an arm marks the slot dirty and may add one save per player; the plain allowance comparison is reported beside
the grade). The L arms' eats are real intake landings that save (x391e's L arms
wrote 3 in about 20 s), so their writes and attribution are reported, not graded.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  PROBE   (usPerWrite, and write+intact, is a lower bound on a real slot save: no encode, synthetic record, ruling
          T2-5) a READING with no threshold: the roundtrip save ok; BENCH_DRAWS draws each ok with usPerWrite and
          usPerIntact, mismatches 0, failed 0; the clear ok. Reported against 14 ms (the inferred per-save cost) and
          against the 60-player rate (about one save a second): the write's ms a real second at 60 players, and the
          probe's bytes beside the real players' mean bytes a store write (store.file.stats.bytes / writes, the slot saves and
          the index writes together).
  MULT    every time.snapshot's trueMult is 1 within MULT_TOL (the normal clock); eff recorded, not graded.
  I       idle: ring busy p99 <= 10 ms and period p50 within 99..101 ms.
  F       I (and Gmod when run) keep >= MIN_FRAMES ring frames and >= MIN_MINUTE_FRAMES minute frames.
  LAT     every latency arm returns 3 samples, each done; medians and maxima per arm are a READING (no threshold),
          burst against mod and both against idle.
  NONFOOD action.latency Base.Hammer 1 reads done with reason "not a Food item"; admin not parked.
  SEED    (part 3) both records carry monotony.t.[TKX.Mono450].n >= 1 after the seed.
  GMOD    (part 3) Gmod against I: p99 end-to-end add <= 20 ms, longest-window add <= 25 ms, starvedEvents 0
          (ruling 2's bounds); its worst frame and its rate reported (Rule 6).
  S       every loaded arm: failures 0, storeGhostKeys 0.
  SEAM    no loaded arm void.
  CARRIER I and Gmod: writes delta <= REALS x (floor(span/60) + 1) + floor(span/300) + 1 (L arms reported only).
  G       gc.log exists (pauses reported, not graded: the benches are single long frames by design).
  Z       no mod error line; admin not parked.

THE READING GUIDE CAVEATS: the probe's record is a synthetic eight-double record, smaller than a real player's, and the
bench prices F.intact and F.write (a getFileReader read and compare; a getFileWriter truncate, write and close), not
the encode F.save runs before them; so usPerWrite is the file cost of a save of `bytes` bytes, and a real save adds the
encode of a larger text. The writer is omitted from every ghost run; no carrier reading is valid during a ghost load.

DEVIATIONS from x391e_owed.py (stated before the run):
  1. PROFILE x39-shootout-g, PREFIX x391g, ARTIFACT bench.json; the fixture's DayLength (the profile sets none) and no
     time.multiplier call.
  2. Phases B (the empty check), W (the real-player benches), FC (the fast clock) and ST (the stall) dropped: x391e
     read them; phase P (the slot-save price), an idle arm I (x391d's run_arm) and part 3 (x391b's seed and x391d's mod
     arm) added.
  3. SETTLE_S is 5.0 (x391e's 3.0 was 5 minute events at DayLength 1; 5 s is 1.3 at the normal clock, as x391d).
  4. Every arm's adds are taken against I, not Lidle (Lidle carries an eat).
  5. HARNESS_COMMIT 016dce05 recorded and HARNESS_MARKERS asserted before the boot; git log 513778e8..HEAD -- mod/
     must be empty; MULT and CARRIER added.
  6. The server-log greps and the mod-error filter also exclude PROBE_RX (this driver's own probe and command names,
     the probe record's name `tkprobe` included), beside the bus's echo prefix (CLAUDE.md s5).
  (2, added) x391e's load_arm and unload_arm are inlined in make_lat, with identical behaviour.

Pre-run edits made after the review of 74e25743 (nothing has run): CARRIER allows for intake landings; the seed
skips a player whose RCON additem ack is not ok and stops on an eat.action `spawned` other than "found"; ruling
T2-5 is stated in PROBE and the probe note, and the bytes key is relabelled; the deployed harness markers are
asserted before body().

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


PROFILE = "x39-shootout-g"
PREFIX = "x391g"
SESSION = ("Plan 11b Task 2, confirmatory session x391g (ruling T2-1): the slot-save price (store.probe bench), "
           "own-action latency under idle, burst and mod at the normal clock plus the non-Food smoke, and if time "
           "allows one seeded-record mod arm at the normal clock, at N = 60, on the staged copy at 513778e8 and the "
           "fixed harness (016dce05); one boot of " + PROFILE)
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert PROFILE == "x39-shootout-" + PREFIX[-1], f"PROFILE {PROFILE} does not match PREFIX {PREFIX}"
ARTIFACT = "bench.json"
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
HARNESS_COMMIT = "016dce05"     # the harness fix: a ghost run restores its carrier's macros; the true multiplier
HARNESS_MARKERS = ("-- ---- Plan 11b Task 2 fix: a ghost run restores the carrier's macros ----",
                   "g.rec.reconcile.baseline = NR.kernel.reconcile.baselineAfter(pre)",
                   'TK.call(nut, "setCalories", pre.calories)')
NR = "NutritionRevamp"
N = 60
REALS = 2
MULT_TOL = 1e-4
NORMAL_MULT = 1.0
# P: the slot-save price
PILOT_N = 50
BENCH_DRAWS = 3
DRAW_TARGET_MS = 1500.0          # a draw (n intact reads + n writes) under about 2 s
N_MIN = 50
N_MAX = 10000                    # store.probe's own bound (TK.SP.MAX)
N_FALLBACK = N_MAX               # the pilot read 0 ms (1 ms clock): an iteration under 20 us
SAVE_COST_MS = 14.0              # the inferred per-save cost the reading is set against
SAVES_PER_S_AT_60 = 1.0          # 60 real players, each at most one save a real minute
# I and Gmod
ARM_WALL_S = 85.0
MIN_FRAMES = 800
MIN_MINUTE_FRAMES = 18          # about 22 minute frames in 85 s at 3.75 s a game minute
# L
LAT_ARMS = (("Lidle", None), ("Lburst", "burst"), ("Lmod", "mod"))
LAT_FOOD = "Base.Apple"
LAT_N = 3
NONFOOD = "Base.Hammer"
SPAWN_WAIT_S = 2.5
LAT_CAP_S = 120.0
LAT_POLL_S = 1.0
SETTLE_S = 5.0
# part 3
PART3_LATEST_S = 660.0           # 900 s - (seed 80 + reads 10 + arm 115 + Z 10 + teardown 25)
SEED_FOOD = "TKX.Mono450"
SEED_EATS = 5
SEED_EAT_CAP_S = 40.0
SEED_CAP_S = 80.0
SEED_SPAWN_WAIT_S = 2.5
RING_N = 1500
PERF_N = 400
S0_WAIT_S = 90.0
MIN_RUNS = 4
MIN_FREE_GB = 12.0
RESULT_WAIT_S = 30.0
POLL_S = 0.5
LOG_LIMIT = 400
IDLE_BUSY_P99_MAX = 10
IDLE_PERIOD_BAND = (99, 101)
RULE_P99 = 20.0                  # ruling 2: adds at most 20 ms at p99
RULE_MAX = 25.0                  # ruling 2: adds at most 25 ms at the max
SAVE_GAP_S = 60
FREQ_MS = (110, 120)             # the end-to-end thresholds counted for Rule 6's frequency
BUSY_MS = (10, 15, 20)
INDEX_GAP_S = 300
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
PROBE_RX = re.compile(r"\b(?:store\.probe|tkprobe|action\.latency|tick\.ring|perf\.local|"
                      r"ghost\.(?:load|modq|stats|stop)|time\.snapshot|lua\.(?:read|global)|foodtimer\.set|"
                      r"eat\.action|additem)")
                                            # this driver's own probe and command names, excluded from every log grep
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
     f"{NR}.server.minute.stats.runs", f"{NR}.server.minute.stats.failures",
     # the write attribution (added after x391b's seam reading, before this driver's run): the real players' intake
     # landings and sips, the writer's sip folds, the reconcile's landings, the store's deferrals and failures, and
     # each real player's last write stamp
     f"{NR}.server.intake.stats.landed", f"{NR}.server.intake.stats.sips", f"{NR}.server.intake.stats.worldSips",
     f"{NR}.server.writer.stats.sips", f"{NR}.server.reconcile.stats.landed", f"{NR}.server.store.file.stats.deferred",
     f"{NR}.server.store.file.stats.writeFailures", f"{NR}.server.store.file.lastWrite.admin",
     f"{NR}.server.store.file.lastWrite.bob")
INTAKE_LANDED = f"{NR}.server.intake.stats.landed"


PRED = {
    "PROBE": {"reading": "no threshold", "roundtrip save": "ok",
              f"{BENCH_DRAWS} draws": "ok with usPerWrite and usPerIntact, mismatches 0, failed 0", "clear": "ok",
              "lower bound": "usPerWrite (and write+intact) is a lower bound on a real slot save: no encode, "
                             "synthetic record (ruling T2-5)",
              "reported against": f"{SAVE_COST_MS} ms a save and {SAVES_PER_S_AT_60} save a real second at 60 players"},
    "MULT": {"every time.snapshot trueMult": f"{NORMAL_MULT} within {MULT_TOL}", "eff": "recorded, not graded"},
    "I": {"busy p99": f"<= {IDLE_BUSY_P99_MAX}", "period p50": list(IDLE_PERIOD_BAND)},
    "F": {"I and Gmod kept ring frames": f">= {MIN_FRAMES}", "kept minute frames": f">= {MIN_MINUTE_FRAMES}"},
    "LAT": {"every arm": f"{LAT_N} samples, each done",
            "reading": "median and max per arm, burst against mod, both against idle (no threshold)"},
    "NONFOOD": {"action.latency Base.Hammer 1": "done, reason 'not a Food item'", "admin parked": False},
    "SEED": {f"monotony.t.[{SEED_FOOD}].n on both records": ">= 1 (part 3)"},
    "GMOD": {"Gmod against I": f"p99 add <= {RULE_P99}, max add <= {RULE_MAX}, starvedEvents 0 (part 3)",
             "Rule 6": "worst frame and its rate reported"},
    "S": {"failures": 0, "storeGhostKeys": 0},
    "SEAM": {"store writes delta a loaded arm": "<= REALS*(minute events+1) + floor(span/300) + 1 (x391d's void rule)",
             "store index keys": "unchanged", "storeGhostKeys": 0},
    "CARRIER": {"I and Gmod (the arms with no eat in the window), store writes delta (window start to end)":
                "<= REALS*(floor(span/60)+1) + floor(span/300) + 1 + the arm's intake.stats.landed delta: at most one "
                "save per real player a real minute plus one per intake landing (a late seed eat landing inside an "
                "arm marks the slot dirty and may add one save per player); the plain allowance comparison is "
                "reported beside it (over_plain_allowance)",
                "reconcile.stats.landed and intake deltas": "reported per arm, not graded",
                "L arms": "writes and attribution reported, not graded (each eat is a real intake save)"},
    "G": {"gc.log": "exists"},
    "Z": {"mod_error": "none", "admin_lua_error": False},
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
                if ECHO_RX.search(line) or PROBE_RX.search(line):
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
    ix = gread(SRV, f"{NR}.server.store.file.index", f"{tag}_ix")
    row["index_keys"] = ix.get("keyCount")
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


def mread(tag):
    """time.snapshot's trueMult (getTrueMultiplier, time.multiplier's `mult`) and mult (getMultiplier, its `eff`)."""
    s = snap(tag)
    return {"mult": num(s.get("trueMult")), "eff": num(s.get("mult")), "worldAge": num(s.get("worldAge")),
            "wall": s.get("wall"), "epoch_ms_before": s.get("epoch_ms_before")}


# ---------------------------------------------------------------- the arm (x391d's, without the spread and budget15 arms)
def run_arm(tag, sched):
    """One arm. sched None is the idle arm (no load); "mod" is the mod's own queue. Server bus traffic inside the
    window: the ring arm only, before it the perf arm, after it the perf read; their spans are the drop windows."""
    A = out["phases"][tag] = {"tag": tag, "N": N if sched else None, "sched": sched, "mem_before": mem(f"{tag}_0")}
    A["mult"] = mread(f"{tag}_mult")
    A["q_pre"] = qread(f"{tag}_q_pre")
    if sched is not None:
        A["load"] = keep(step(f"{tag}_load", SRV, "ghost.load", f"{N} {sched} feed", timeout=60))
        if not A["load"].get("ok"):
            note(f"{tag}: ghost.load failed: {A['load'].get('reason') or A['load'].get('raw')}")
        if sched == "mod":
            A["modq_on"] = keep(step(f"{tag}_modq_on", SRV, "ghost.modq", "on"))
            if not A["modq_on"].get("ok"):
                note(f"{tag}: ghost.modq on failed: {A['modq_on'].get('reason') or A['modq_on'].get('raw')}")
        time.sleep(SETTLE_S)
        A["reset"] = keep(step(f"{tag}_reset", SRV, "ghost.stats", "reset"))
    A["q_start"] = qread(f"{tag}_q_start")
    A["perf_arm"] = keep(step(f"{tag}_perf_arm", SRV, "perf.local", str(PERF_N)))
    A["ring_arm"] = keep(step(f"{tag}_ring_arm", SRV, "tick.ring", str(RING_N)))
    A["window_start_wall"] = wall()
    time.sleep(ARM_WALL_S)
    A["window_end_wall"] = wall()
    after = time.time() - 1.0
    A["perf_read"] = keep(step(f"{tag}_perf_read", SRV, "perf.local", f"read {tag}"))
    A["ring_read"] = keep(step(f"{tag}_ring_read", SRV, "tick.ring", f"read {tag}"))
    if sched is not None:
        A["stats"] = keep(step(f"{tag}_stats", SRV, "ghost.stats"))
    A["q_end"] = qread(f"{tag}_q_end")
    if sched == "mod":
        A["modq_off"] = keep(step(f"{tag}_modq_off", SRV, "ghost.modq", "off"))
    A["perf_doc"] = wait_doc(f"perf-local-{tag}", after)
    A["ring_doc"] = wait_doc(f"tick-ring-{tag}", after)
    if sched is not None:
        A["stop"] = keep(step(f"{tag}_stop", SRV, "ghost.stop"))
        out["world_changes"]["left_in_place"].append(f"{tag}: {N - REALS} ghost records ran against admin and bob "
                                                     f"under {sched} (their Java reads land on the carriers)")
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
    P["mult"] = mread("S0_mult")
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


def pick_n(pilot):
    """n so that one draw (n intact reads + n writes) stays near DRAW_TARGET_MS, from the pilot's ms an iteration."""
    ms = (num(pilot.get("intactMs")) or 0) + (num(pilot.get("writeMs")) or 0)
    pn = num(pilot.get("n")) or PILOT_N
    if not pilot.get("ok") or ms <= 0:
        return N_FALLBACK if pilot.get("ok") else None, None
    per = ms / pn
    return int(max(N_MIN, min(N_MAX, math.floor(DRAW_TARGET_MS / per)))), per


def phase_P():
    P = out["phases"]["P"] = {"draws": []}
    P["q0"] = qread("P_q0")
    try:
        P["save"] = keep(step("P_save", SRV, "store.probe", "roundtrip save", timeout=60))
        if not P["save"].get("ok"):
            note(f"P: store.probe roundtrip save failed: {P['save'].get('err') or P['save'].get('raw')}")
            return
        P["pilot"] = keep(step("P_pilot", SRV, "store.probe", f"bench {PILOT_N}", timeout=90))
        n, per = pick_n(P["pilot"])
        P["n"], P["pilot_ms_per_iteration"] = n, per
        if n is None:
            note("P: the pilot bench failed; no draw taken")
            return
        for i in range(BENCH_DRAWS):
            r = keep(step(f"P_bench{i}", SRV, "store.probe", f"bench {n}", timeout=90))
            P["draws"].append({"draw": i, "ok": r.get("ok"), "n": num(r.get("n")), "bytes": num(r.get("bytes")),
                               "usPerWrite": num(r.get("usPerWrite")), "usPerIntact": num(r.get("usPerIntact")),
                               "writeMs": num(r.get("writeMs")), "intactMs": num(r.get("intactMs")),
                               "mismatches": num(r.get("mismatches")), "failed": num(r.get("failed")),
                               "writeFailures": num(r.get("writeFailures")), "reason": r.get("reason"),
                               "raw": r.get("raw"), "wall": r.get("wall"), "wall_after": r.get("wall_after")})
    finally:
        P["clear"] = keep(step("P_clear", SRV, "store.probe", "clear", timeout=60))
        out["world_changes"]["left_in_place"].append("P: store.probe roundtrip save then clear (both synthetic slots "
                                                     "emptied, the index entry dropped and the index written)")
        P["q1"] = qread("P_q1")


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
        A["mult"] = mread(f"{tag}_mult")
        A["q_pre"] = qread(f"{tag}_q_pre")
        if sched is not None:
            A["load"] = keep(step(f"{tag}_load", SRV, "ghost.load", f"{N} {sched} feed", timeout=60))
            if not A["load"].get("ok"):
                note(f"{tag}: ghost.load failed: {A['load'].get('reason') or A['load'].get('raw')}")
            if sched == "mod":
                A["modq_on"] = keep(step(f"{tag}_modq_on", SRV, "ghost.modq", "on"))
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
        if sched == "mod":
            A["modq_off"] = keep(step(f"{tag}_modq_off", SRV, "ghost.modq", "off"))
        if sched is not None:
            A["stop"] = keep(step(f"{tag}_stop", SRV, "ghost.stop"))
            out["world_changes"]["left_in_place"].append(f"{tag}: {N - REALS} ghost records ran against admin and "
                                                         f"bob under {sched}")
        A["drop_windows"] = [span(A["ring_arm"]), span(A["perf_read"])]
        A["mem_after"] = mem(f"{tag}_1")
    return fn


def phase_NF():
    P = out["phases"]["NF"] = {}
    P["arm"] = keep(step("NF_lat", ADMIN, "action.latency", f"{NONFOOD} 1"))
    P["read"] = lat_read("NF", 30.0)
    P["parked"] = parked()


def landed(tag):
    a = lread(SRV, "_G", [INTAKE_LANDED], tag)
    return num((a.get("values") or {}).get(INTAKE_LANDED))


def mono(tag):
    rows = {}
    for u in USERS:
        a = lread(SRV, f"record:{u}", [f"monotony.t.[{SEED_FOOD}].n", f"monotony.t.[{SEED_FOOD}].last"], f"{tag}_{u}")
        v = a.get("values") or {}
        rows[u] = {"n": num(v.get(f"monotony.t.[{SEED_FOOD}].n")), "last": num(v.get(f"monotony.t.[{SEED_FOOD}].last")),
                   "missing": a.get("missing"), "ok": a.get("ok")}
    return rows


def phase_SEED():
    P = out["phases"]["SEED"] = {"rounds": []}
    P["mono_before"] = mono("SEED_mono0")
    P["additem"] = {u: rcon(f'additem "{u}" "{SEED_FOOD}" {SEED_EATS}', f"SEED_additem_{u}") for u in USERS}
    out["world_changes"]["left_in_place"].append(f"SEED: RCON additem {SEED_FOOD} x{SEED_EATS} to each player")
    time.sleep(SEED_SPAWN_WAIT_S)
    # no client-side spawn fallback (review of 74e25743): a player whose RCON additem ack is not ok is skipped in every
    # round, and the seed stops for all players as soon as an eat.action reply's spawned is anything but "found"
    P["additem_ok"] = {u: P["additem"][u].get("ok") is True for u in USERS}
    seed_users = [u for u in USERS if P["additem_ok"][u]]
    P["skipped_players"] = [u for u in USERS if u not in seed_users]
    t_end = time.time() + SEED_CAP_S
    for k in range(SEED_EATS):
        if time.time() >= t_end or parked():
            note(f"SEED: stopped before round {k} (cap {SEED_CAP_S} s or admin parked)")
            break
        R = {"round": k}
        R["foodtimer"] = {u: keep(step(f"SEED{k}_ft_{u}", SRV, "foodtimer.set", f"{u} 0")).get("after") for u in USERS}
        base = landed(f"SEED{k}_landed0")
        R["landed_before"] = base
        R["queued"] = {}
        for s in CLIENT_SIDES:
            if who(s) not in seed_users:
                R["queued"][who(s)] = {"skipped": "RCON additem ack not ok"}
                continue
            q = keep(step(f"SEED{k}_eat_{who(s)}", s, "eat.action", f"{SEED_FOOD} 1"))
            R["queued"][who(s)] = {kk: q.get(kk) for kk in ("queued", "fraction", "spawned", "itemId", "validStart",
                                                             "maxTime", "raw")}
            if q.get("spawned") != "found" and "stop_reason" not in P:
                P["stop_reason"] = f"round {k}: {who(s)} eat.action spawned={q.get('spawned')!r}, not 'found'"
                note("SEED: " + P["stop_reason"])
                break   # the stop is immediate: no further eat.action this round (re-review of 612f1acf)
        want = sum(1 for u in USERS if R["queued"].get(u, {}).get("queued"))
        end = min(time.time() + SEED_EAT_CAP_S, t_end)
        R["landed_after"] = base
        while time.time() < end and want > 0 and base is not None:
            if parked():
                break
            cur = landed(f"SEED{k}_poll")
            R["landed_after"] = cur
            if cur is not None and cur >= base + want:
                break
            time.sleep(POLL_S)
        R["wall"] = wall()
        P["rounds"].append(R)
        if "stop_reason" in P:
            break
    P["mono_after"] = mono("SEED_mono1")
    P["q"] = qread("SEED_q")


def phase_Gmod():
    run_arm("Gmod", "mod")


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["stop_left"] = keep(step("Z_stop", SRV, "ghost.stop"))
    P["modq_off"] = keep(step("Z_modq_off", SRV, "ghost.modq", "off"))
    P["players"] = keep(step("Z_players", SRV, "players"))
    P["time"] = snap("Z_time")
    P["mult"] = mread("Z_mult")
    P["q"] = qread("Z_q")
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)
                                   and not PROBE_RX.search(e)][:20]
    P["admin_parked"] = parked()
    P["mem"] = mem("Z")


def body():
    order = [("S0", phase_S0), ("P", phase_P), ("I", lambda: run_arm("I", None))]
    order += [(tag, make_lat(tag, sched)) for tag, sched in LAT_ARMS]
    order += [("NF", phase_NF)]
    for name, fn in order:
        run_phase(name, fn)
        if parked():
            out["abort"] = f"admin parked in the debugger after phase {name}"
            run_phase("Z", phase_Z)
            return
    out["part3"] = {"wall_at_decision": wall(), "latest": PART3_LATEST_S, "run": wall() <= PART3_LATEST_S}
    if out["part3"]["run"]:
        for name, fn in (("SEED", phase_SEED), ("Gmod", phase_Gmod)):
            run_phase(name, fn)
            if parked():
                out["abort"] = f"admin parked in the debugger after phase {name}"
                break
    else:
        note(f"part 3 skipped: wall {out['part3']['wall_at_decision']} s past {PART3_LATEST_S} s")
    run_phase("Z", phase_Z)


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
    # the seam (revised after x391b, before this driver's run): x391b's real players saved about once a game minute
    # each during its ghost loads, past the once-a-real-minute premise, with no ghost slot file and no ghost record;
    # a ghost leak is 58 saves a minute event and an index entry each. The arm is void when the store's index gains
    # a key, when a ghost record is in the store, or when the writes exceed every real player saving at every minute
    # event (REALS x (minutes + 1)) plus the index; the once-a-real-minute allowance is still reported.
    wd, md = S["seam"]["writes_delta"], delta(A, "minutes")
    S["seam"]["real_minute_rule_exceeded"] = (wd is not None and allow is not None and wd > allow)
    S["seam"]["allowance_minute_events"] = (REALS * (md + 1) + int(span_s // INDEX_GAP_S) + 1)         if (md is not None and span_s is not None) else None
    S["seam"]["index_keys"] = [g(A, "q_start", "index_keys"), g(A, "q_end", "index_keys")]
    S["seam"]["attribution"] = {k: delta(A, k) for k in ("intake.stats.landed", "intake.stats.sips",
                                                         "intake.stats.worldSips", "writer.stats.sips",
                                                         "reconcile.stats.landed", "store.file.stats.deferred",
                                                         "store.file.stats.writeFailures")}
    ik = S["seam"]["index_keys"]
    S["seam"]["void"] = bool(
        (wd is not None and S["seam"]["allowance_minute_events"] is not None and wd > S["seam"]["allowance_minute_events"])
        or (ik[0] is not None and ik[1] is not None and ik[1] > ik[0])
        or (num(g(A, "stats", "storeGhostKeys")) or 0) > 0)
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


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = len(xs) // 2
    return xs[k] if len(xs) % 2 else (xs[k - 1] + xs[k]) / 2.0


def grade_all():
    ph = out["phases"]
    S = out["summaries"]
    # P: the slot-save price (a reading)
    P = ph.get("P") or {}
    draws = P.get("draws") or []
    q0, q1 = P.get("q0") or {}, P.get("q1") or {}
    real_w, real_b = num(q0.get("store.file.stats.writes")), num(q0.get("store.file.stats.bytes"))
    pr = {"n": P.get("n"), "pilot_ms_per_iteration": P.get("pilot_ms_per_iteration"),
          "usPerWrite": [d.get("usPerWrite") for d in draws], "usPerIntact": [d.get("usPerIntact") for d in draws],
          "writeMs": [d.get("writeMs") for d in draws], "intactMs": [d.get("intactMs") for d in draws],
          "bytes": [d.get("bytes") for d in draws], "mismatches": [d.get("mismatches") for d in draws],
          "failed": [d.get("failed") for d in draws], "save_ok": g(P, "save", "ok"), "clear_ok": g(P, "clear", "ok"),
          # stats.bytes / stats.writes counts every store write, the slot saves and the index writes together: a mean
          # bytes a store write, the index writes mixed in, not a mean bytes a slot save
          "real_mean_bytes_per_store_write_at_P": (real_b / real_w) if (real_w and real_b is not None) else None,
          "real_writes_at_P": real_w,
          "store_writes_across_P": [q0.get("store.file.stats.writes"), q1.get("store.file.stats.writes")],
          "index_keys_across_P": [q0.get("index_keys"), q1.get("index_keys")]}
    mw, mi = median(pr["usPerWrite"]), median(pr["usPerIntact"])
    pr["median_usPerWrite"], pr["median_usPerIntact"] = mw, mi
    if mw is not None:
        pr["write_over_save_cost"] = mw / (SAVE_COST_MS * 1000.0)
        pr["write_ms_per_real_s_at_60"] = mw / 1000.0 * SAVES_PER_S_AT_60
    if mw is not None and mi is not None:
        pr["write_plus_intact_us"] = mw + mi
        pr["write_plus_intact_over_save_cost"] = (mw + mi) / (SAVE_COST_MS * 1000.0)
        pr["write_plus_intact_ms_per_real_s_at_60"] = (mw + mi) / 1000.0 * SAVES_PER_S_AT_60
    S["probe"] = pr
    if not draws:
        grade("PROBE", PRED["PROBE"], pr, "unmeasured", "no bench draw")
    else:
        ok = (pr["save_ok"] is True and pr["clear_ok"] is True and len(draws) == BENCH_DRAWS
              and all(d.get("ok") is True and d.get("usPerWrite") is not None and d.get("usPerIntact") is not None
                      and d.get("mismatches") == 0 and d.get("failed") == 0 for d in draws))
        grade("PROBE", PRED["PROBE"], pr, "as_predicted" if ok else "falsified",
              "a draw without its figures, a mismatch or a failed write, or the save or clear not ok")
    # MULT: trueMult graded, eff recorded
    reads = {t: g(ph, t, "mult") for t in ("S0", "I", "Lidle", "Lburst", "Lmod", "Gmod", "Z") if g(ph, t, "mult")}
    S["mult"] = reads
    vals = [r.get("mult") for r in reads.values()]
    if not vals or all(v is None for v in vals):
        grade("MULT", PRED["MULT"], reads, "unmeasured", "no multiplier read")
    else:
        okm = all(v is not None and abs(v - NORMAL_MULT) <= MULT_TOL for v in vals)
        grade("MULT", PRED["MULT"], reads, "as_predicted" if okm else "falsified", "a trueMult off 1")
    # I: the idle reference
    I = ph.get("I") or {}
    if I.get("ring_doc"):
        S["I"] = arm_summary(I)
        b, p = S["I"]["busy"], S["I"]["period"]
        ok = (b["p99"] is not None and b["p99"] <= IDLE_BUSY_P99_MAX and p["p50"] is not None
              and IDLE_PERIOD_BAND[0] <= p["p50"] <= IDLE_PERIOD_BAND[1])
        grade("I", PRED["I"], {"busy": b, "period": p, "perf_max": S["I"]["perf_max"], "endPeriod": S["I"]["endPeriod"]},
              "as_predicted" if ok else "falsified", "busy p99 over 10 or period p50 off")
    else:
        grade("I", PRED["I"], None, "unmeasured", "no idle ring document")
    idle = S.get("I")
    # L: latency and the frames under each arm
    lat = S["latency"] = {}
    for tag, sched in LAT_ARMS:
        A = ph.get(tag) or {}
        if not A:
            continue
        lat[tag] = lat_summary(A)
        if A.get("ring_doc"):
            S[tag] = arm_summary(A, idle)
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
    # part 3: the seed and the seeded mod arm
    sd = ph.get("SEED") or {}
    ma = sd.get("mono_after") or {}
    if ma:
        ns = {u: g(ma, u, "n") for u in USERS}
        ok = all(n is not None and n >= 1 for n in ns.values())
        grade("SEED", PRED["SEED"], {"n": ns, "rounds": len(sd.get("rounds") or []), "stop_reason": sd.get("stop_reason"),
                                   "skipped_players": sd.get("skipped_players"), "additem_ok": sd.get("additem_ok")},
              "as_predicted" if ok else "falsified", "a record without the seed food's monotony entry")
    else:
        grade("SEED", PRED["SEED"], {"part3": out.get("part3")}, "unmeasured", "part 3 not run or no seed read")
    G = ph.get("Gmod") or {}
    if G.get("ring_doc"):
        S["Gmod"] = arm_summary(G, idle)
        x = S["Gmod"]
        row = {"adds_p99_endPeriod": g(x, "adds", "endPeriod", "p99"), "adds_max_perf": g(x, "adds", "perf_max", "max"),
               "starvedEvents": g(x, "ghost", "starvedEvents"), "starvedMinutes": g(x, "ghost", "starvedMinutes"),
               "maxStaleGameMinutes": g(x, "ghost", "maxStaleGameMinutes"), "rule6": x.get("rule6"),
               "ghost_ms_per_minute_event": x.get("ghost_ms_per_minute_event"), "usPerRun": g(x, "ghost", "usPerRun"),
               "queue_end": g(x, "queue", "end"), "seam_void": g(x, "seam", "void")}
        if row["seam_void"]:
            grade("GMOD", PRED["GMOD"], row, "unmeasured", "the arm is void under the seam rule")
        else:
            ok = (row["adds_p99_endPeriod"] is not None and row["adds_p99_endPeriod"] <= RULE_P99
                  and row["adds_max_perf"] is not None and row["adds_max_perf"] <= RULE_MAX
                  and row["starvedEvents"] == 0)
            grade("GMOD", PRED["GMOD"], row, "as_predicted" if ok else "falsified",
                  "p99 add over 20, max add over 25, or a starved ghost-minute")
    else:
        grade("GMOD", PRED["GMOD"], {"part3": out.get("part3")}, "unmeasured", "part 3 not run or no Gmod ring")
    # F: the frame counts of I and Gmod
    fr = [t for t in ("I", "Gmod") if t in S]
    if fr:
        short = {t: [S[t]["frames"], S[t]["minute_frames"]] for t in fr
                 if S[t]["frames"] < MIN_FRAMES or S[t]["minute_frames"] < MIN_MINUTE_FRAMES}
        grade("F", PRED["F"], {t: [S[t]["frames"], S[t]["minute_frames"]] for t in fr},
              "as_predicted" if not short else "falsified", "an arm short", {"short": short})
    else:
        grade("F", PRED["F"], None, "unmeasured", "no arm")
    # S, SEAM and CARRIER
    loaded = [t for t, s in LAT_ARMS if s is not None] + ["Gmod"]
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
        voids = [t for t in have if S[t]["seam"]["void"]]
        unread = [t for t in have if S[t]["seam"]["writes_delta"] is None]
        grade("SEAM", PRED["SEAM"], {t: S[t]["seam"] for t in have},
              "as_predicted" if not voids and not unread else "falsified", "a void arm",
              {"void_arms": voids, "unread_arms": unread})
    else:
        for k in ("S", "SEAM"):
            grade(k, PRED[k], None, "unmeasured", "no loaded arm")
    every = [t for t in ("I", "Lidle", "Lburst", "Lmod", "Gmod") if t in S]
    car_arms = [t for t in ("I", "Gmod") if t in S]      # the L arms' eats are real intake saves: reported only
    # the grade allows for intake landings (review of 74e25743): a late seed eat landing inside an arm marks the slot
    # dirty and may add one save per player, so the grade is writes_delta <= allowance + the arm's intake.stats.landed
    # delta; the plain allowance comparison stays beside it as a reported reading (over_plain_allowance)
    car = {t: {"writes_delta": g(S, t, "seam", "writes_delta"), "allowance": g(S, t, "seam", "allowance"),
               "span_s": g(S, t, "seam", "span_s"), "attribution": g(S, t, "seam", "attribution"),
               "minutes_delta": delta(ph.get(t) or {}, "minutes")} for t in car_arms}
    for r in car.values():
        r["intake_landed_delta"] = (r["attribution"] or {}).get("intake.stats.landed")
        r["allowance_with_intake"] = (r["allowance"] + (r["intake_landed_delta"] or 0)) \
            if r["allowance"] is not None else None
        r["over_plain_allowance"] = (r["writes_delta"] > r["allowance"]) \
            if r["writes_delta"] is not None and r["allowance"] is not None else None
    S["writes_L"] = {t: {"writes_delta": g(S, t, "seam", "writes_delta"), "allowance": g(S, t, "seam", "allowance"),
                         "attribution": g(S, t, "seam", "attribution")} for t in every if t not in car_arms}
    over = [t for t, r in car.items() if r["writes_delta"] is not None and r["allowance_with_intake"] is not None
            and r["writes_delta"] > r["allowance_with_intake"]]
    unr = [t for t, r in car.items() if r["writes_delta"] is None or r["allowance"] is None]
    S["carrier"] = car
    grade("CARRIER", PRED["CARRIER"], car, "unmeasured" if not car or len(unr) == len(car) else
          ("as_predicted" if not over and not unr else "falsified"),
          "an arm's writes above one save per real player a real minute plus the index plus its intake landings",
          {"over": over, "unread": unr})
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
        obs = {"server_mod_error_lines": Z.get("server_mod_error_lines") or [],
               "admin_lua_error": out.get("admin_lua_error")}
        ok = not obs["server_mod_error_lines"] and not obs["admin_lua_error"]
        grade("Z", PRED["Z"], obs, "as_predicted" if ok else "falsified", "a mod error line, admin parked")
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
        "harness_commit": HARNESS_COMMIT,
        "harness_fix_is_ancestor": git_say("merge-base", "--is-ancestor", HARNESS_COMMIT, "HEAD") == "",
        "mod_log_since_stage": git_say("log", "--oneline", f"{STAGED_AT}..HEAD", "--", MOD_DIR),
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
                 "carrier_note": "Since 016dce05 H0.work restores the carrier's four vanilla macro stores after each "
                                 "ghost run and seeds the ghost record's reconcile baseline from them.",
                 "probe_note": "store.probe bench prices F.intact and F.write on a synthetic eight-double record's "
                               "text (its bytes in the reply), not the encode F.save runs before them: usPerWrite (and write+intact) is "
                               "a lower bound on a real slot save, no encode, synthetic record (ruling T2-5).",
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
            "PROFILE x39-shootout-g, PREFIX x391g, ARTIFACT bench.json; the fixture's DayLength and no time.multiplier "
            "call.",
            "Phases B, W, FC and ST dropped (x391e read them); P (the slot-save price), I (x391d's idle arm) and part 3 "
            "(x391b's seed and x391d's mod arm, if wall <= PART3_LATEST_S) added; x391e's load_arm and unload_arm are "
            "inlined in make_lat, with identical behaviour.",
            "SETTLE_S 5.0 (x391e's 3.0 was five minute events at DayLength 1).",
            "Every arm's adds against I, not Lidle (Lidle carries an eat).",
            "HARNESS_COMMIT 016dce05 recorded and HARNESS_MARKERS asserted before the boot; git log 513778e8..HEAD -- "
            "mod/ must be empty; MULT and CARRIER added.",
            "The server-log greps and the mod-error filter also exclude PROBE_RX, the driver's own probe names.",
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
    try:
        with open(os.path.join(REPO, HARNESS_SERVER), encoding="utf-8", errors="replace") as fh:
            srv_text = fh.read()
    except OSError as e:
        srv_text = ""
        out["meta"]["harness_read_error"] = f"{type(e).__name__}: {e}"
    out["meta"]["harness_markers_found"] = {m: (m in srv_text) for m in HARNESS_MARKERS}
    if not all(out["meta"]["harness_markers_found"].values()):
        out["error"] = f"PZTestKit_Server.lua lacks the carrier-restore wrapper of {HARNESS_COMMIT}; not started"
        persist()
        print(out["error"])
        sys.exit(1)
    if out["mod_log_since_stage"] != "":
        out["error"] = f"git log {STAGED_AT}..HEAD -- {MOD_DIR} is not empty: {out['mod_log_since_stage']!r}; not started"
        persist()
        print(out["error"])
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
        dm = {}
        for rel in deployed:
            if rel.endswith("PZTestKit_Server.lua"):
                try:
                    with open(os.path.join(run_dir, rel), encoding="utf-8", errors="replace") as fh:
                        dm[rel] = all(m in fh.read() for m in HARNESS_MARKERS)
                except OSError as e:
                    dm[rel] = f"{type(e).__name__}: {e}"
        out["meta"]["deployed_harness_markers"] = dm
        mem("ready")
        persist()
        # the deployed copy must hold the carrier-restore wrapper (review of 74e25743): abort before body() otherwise
        if not dm or not all(v is True for v in dm.values()):
            out["abort"] = f"the deployed PZTestKit_Server.lua lacks the carrier-restore markers of {HARNESS_COMMIT}: {dm!r}"
            tl.mark("error", detail=out["abort"][:200])
            print(out["abort"])
        else:
            try:
                body()
            except Exception as e:                 # noqa: BLE001 - keep the rows already collected
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
                      "probe": g(out, "summaries", "probe"), "latency": g(out, "summaries", "latency"),
                      "mult": g(out, "summaries", "mult"), "carrier": g(out, "summaries", "carrier"),
                      "rule6_table": g(out, "summaries", "rule6_table"), "part3": out.get("part3"),
                      "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "run_id": run_id,
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])


if __name__ == "__main__":
    main()
