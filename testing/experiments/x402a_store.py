"""x402a-store -- Plan 11b Task 4 session S4b1 (live), the first of two boots on one world (x260 and x260b's shape):
the store's JSON number round trip saved before a restart (store.probe roundtrip save, H7), the reconnect decay
(ruling C-1: admin eats TKX.Mixed650, quits, the server runs on, a fresh client restore rejoins, and satiety.M and S
decay by the gap clamped at K.satiety.MAX_GAP_M = 60 game minutes) and the store's stop window (ruling T20-1: admin
eats TKX.Mixed400 and the server is stopped with admin still online as soon as the landing reads). Session S4b2
(x402b_store.py, profile x40-store-b) copies this run's <run>/server folder and boots it again; it reads the stop
window's eat in the newest slot line, the restart decay, the round trip's load and the prune.

One boot of profile x40-store: fixture two (admin -debug, then bob release), Nutrition false, DayLength 1 (a game
minute is 0.625 s of wall at speed 1), TKX_StudyFoods, and the STAGED copy of the release at release/plan11-x40
(`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan11-x40`, made by the controller after
Task 3c; release/ is gitignored; mod/ is never booted, and the driver never stages). Before the boot the driver checks
that the staged MANIFEST.json equals release_pack.manifest() of mod/NutritionRevamp at HEAD (a `git archive` of HEAD,
so a dirty working tree is never what is compared) and equals the manifest of the staged mod folder itself (the bytes
under test); it records HEAD, the MANIFEST sha256 and the staged NR_Core version, and refuses to boot on a mismatch.
No commit or sha is hard-coded. It also asserts PREFIX and PROFILE against its own file name, and that
PZTestKit_Server.lua (the repository file before the boot, every deployed copy after it, each file read once) holds
the carrier-restore markers of 016dce05, the %g guard of 07c27dc4 and the store.probe and minute.ring registrations.
Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

Artifact: `store.json`, with the staged MANIFEST.json, the minute-ring pages and the store's slot and index files
(copied after the stop) beside it, byte-identical.

PHASES (S0, RT, RC, R, W, then Z; the session's end is W's server stop):
  S0  ping, players, time.snapshot, the mode, both records present and NutritionRevamp.server.minute.stats.runs >=
      MIN_RUNS (cap S0_WAIT_S); `minute.ring admin start <RING_PATHS>`; the store's counters (the slot size reading).
  RT  `store.probe roundtrip save` (a synthetic non-ASCII-named record of eight hard doubles saved through the mod's
      own F.save; never put in store.records) and a ping. S4b2 loads it after the restart and clears it.
  RC  THE RECONNECT DECAY. TKX.Mixed650 spawned on admin by RCON `additem` and CONFIRMED by the server's `item.get`
      (an id; a leftover before the spawn voids the phase; ruling T2-11; never inventory.add); record:admin read;
      `eat.action TKX.Mixed650` on admin's client (its `spawned` must read "found", else the phase stops, void);
      INTAKE_LANDED polled to +1 (cap LAND_CAP_S); RC_PRE_MIN game minutes run on (the ring's per-minute pairs give
      M's clearance rate); record read; admin's client QUITS; the departure polled (players.online.admin absent, cap
      DEPART_CAP_S); the record read while away; the server runs on until the world age is AWAY_MIN_H past the away
      record's kineticsAge, so that with the client's own boot the offline gap passes the 60 game-minute cap; a FRESH
      fixture restore in <run>/c1b joins as admin (x192 and x34's form) and becomes the session's admin client; the
      record polled until its kineticsAge moves (the first kinetics step after the rejoin); RC_POST_MIN game minutes
      more; the record read.
  R   `minute.ring admin read`, page after page; each page copied byte-identical (the ring is lost at the stop).
  W   THE STOP WINDOW (ruling T20-1). TKX.Mixed400 spawned and confirmed as in RC; time.snapshot and the store's
      admin slot state (gen, lastWrite, writes) read; when less than W_MIN_REMAIN_S of the real minute's save gap
      (S.SAVE_GAP_MS 60000) remains since admin's last write, the driver first waits for that regular save (cap
      W_FRESH_CAP_S), so no regular save can fall between the landing and the stop; record:admin read (the Mixed400
      monotony count absent, the buffer, M, gen); `eat.action TKX.Mixed400`; the store's gen, lastWrite, writes and
      INTAKE_LANDED read back to back until the landing reads (cap LAND_CAP_S); one more read of the same (W_prestop:
      at least one more bus round trip, about two game minutes, so the dirty mark's next store step is due; it shows
      whether that save is visible before the stop); then at once the server is stopped (`quit` on its stdin,
      Server.stop) with admin still online, so no departure flush runs. The eat reaches the file only through the
      dirty mark (IN.land -> S.mark), whose save runs at admin's next store step (S.step saves a dirty slot whatever the save gap says). The clients are
      then killed: the server is gone, so a client quit has nothing to disconnect from.
      DEVIATION from the run sheet's "stop the server within one game minute": a game minute is 0.625 s at DayLength
      1 and a server bus round trip about 1.3 s (x391h), so the stop follows the read after the one that sees the
      landing (about 1.3-4 s, 2-6 game minutes, after it), not a game-minute timer. That is still well inside the
      real minute's save gap, so a regular save cannot carry the eat: the stop's server time is set against admin's
      last regular write (the non-trivial condition), and saved_at_confirm and saved_before_stop record whether the
      dirty save was visible at the two reads.
  Z   the local readings first (mod error lines, admin parked, memory), then, unless W stopped the server, players,
      time.snapshot and the store's counters.

LIVENESS (x391h's D1, D2): after any server bus step whose ack is a TimeoutError or RuntimeError the driver pings
(PING_TIMEOUT_S); without a pong the bus is dead, every later server step is skipped (answered {"error": "skipped: ..."}
without a send) and the run goes to Z; a phase that the bus died inside is VOID, never falsified. The wall budget
BUDGET_S (840 s from t0, before the boot) is checked before each phase (wall() + PHASE_EST_S[phase] > BUDGET_S: that
phase and every later one but Z are skipped, out["abort"] says so) and inside every poll. A server stopped by W skips
every later server step the same way (out["server_stopped_by"]). Teardown, the artifact copy and the grading run in
`finally`. No graded frame window exists in this session, so no drop window is needed.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured / void; each with its falsifier):
  RT_SAVE   `store.probe roundtrip save` answers ok with saved true, a gen and a path, and a ping after it answers
            pong. Falsifier: not ok on a live bus. Void: the bus died at the save.
  RC_OFFLINE every ring row of admin taken while away (on false) holds the away record's kineticsAge and satiety.M
            unchanged: nothing integrates offline time (KIN.step runs only for an online player). Falsifier: a row
            that moved. Unmeasured: no away row.
  RC_DECAY  M's clearance rate lambda is measured on the ring's online minute pairs (no landing or sip between,
            kineticsAge apart by at most PAIR_MAX_M game minutes): lambda = ln(M_i / M_i+1) / (kineticsAge_i+1 -
            kineticsAge_i), the median taken. The first row after the rejoin whose kineticsAge moved reads
            M_1 = M_q x exp(-lambda x min(D, GAP_CAP_H)), where M_q and kineticsAge_q are the away record's and
            D = kineticsAge_1 - kineticsAge_q in game hours (KIN.drain caps the drain at K.satiety.MAX_GAP_M and
            K.satiety.mealClear clears M first-order on every one-minute substep, so the product is exact), within
            RC_TOL relative. Falsifier: outside. Unmeasured: no lambda pair, no away record or no moved row. The
            no-cap value M_q x exp(-lambda x D) and the constant-based lambda (ln 2 / MEAL_HALF_LIFE_H, trait 1) are
            reported beside it.
  RC_CLAMP  with D > GAP_CAP_H: RC_DECAY as predicted and the no-cap value off M_1 by more than CLAMP_SEP relative,
            so the read tells the cap from no cap. Falsifier: RC_DECAY falsified while D > 1 h. Unmeasured: D <= 1 h.
  RC_T      satiety.t after the rejoin's first writer step reads at or after the relaunch's world age (read before the
            client starts: the server may see the player before the client reads ready) and later than the away
            record's t (the writer steps S over the gap from the stamp, ruling C-1). Falsifier: not so.
  RC_S      satiety.S after the rejoin is at most the away record's (S only rises while vigorous; the expected value
            S_q x exp(-ln 2 x min(t gap, 1 h) / ACUTE_DECAY_HALF_LIFE_H) is reported). Trivial: both 0.
  W_ARMED   a READING, graded in S4b2 (STOPWIN): the landing confirmed, the stop sent, admin online at the confirm
            read, and the stop's server time less than SAVE_GAP_MS after admin's last regular write.
  Z         no mod error line on the server; admin not parked; the server answered its last read before the stop.

READINGS (not graded): the real players' mean bytes per store write (store.file.stats.bytes / writes; x391h's #3759
reading of 2540 bytes absorbed the owed row); the rejoin's client boot; the departure's poll count.

DEVIATIONS from the run sheet and the amendments, stated before the run:
  1. `store.probe bench` and the slot size are dropped as owed reads (absorbed by x391h, #3757-#3761); the slot size
     is kept as a reading.
  2. The stop window's stop follows one read past the read that confirms the landing (see W), not a game-minute
     timer.
  3. The reconnect's away wait (AWAY_MIN_H) is a driver choice so the offline gap passes the cap.
  4. The eats use TKX_StudyFoods' Mixed650 (RC) and Mixed400 (W), so each phase's monotony entry is its own.
  PRE-RUN EDITS after the Opus review of 0e50f67e (made before any boot):
  5. W_MIN_REMAIN_S is 30 s (was 15 s), the margin of the save gap left before the eat, so a regular save cannot
     fall between the landing and the stop.
  6. The W docstring no longer says the dirty save runs "past the save gap": S.step saves a dirty slot whatever the
     save gap says.
  7. run_phase's error mark passed `phase=` to Timeline.mark, whose first parameter is named phase (a TypeError that
     would escape any phase failure); it passes in_phase= instead.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time. 4. Free host
memory is read before the boot and the boot refused under MIN_FREE_GB (CLAUDE.md s5). 5. A session killed by the
host is reported, and its readings are never re-run to replace their figures (ruling H2-1).
"""
import ctypes
import glob
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.bus import resolve_side                                # noqa: E402
from pzt.harness import lint_paths                              # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, attach_clients, make_client,  # noqa: E402
                         make_server, teardown, verify)


PROFILE = "x40-store"
PREFIX = "x402a"
SESSION = ("Plan 11b Task 4 session S4b1: the round trip's save, the reconnect decay and the stop window on the "
           "staged 1.0.0 release, the first of two boots on one world; one boot of " + PROFILE)
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert PROFILE == "x40-store", f"PROFILE {PROFILE} is not this driver's profile"
ARTIFACT = "store.json"
MANIFEST_NAME = "MANIFEST.json"
ADMIN = "client:admin"
BOB = "client:bob"
SRV = "server"
USERS = ("admin", "bob")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_OUT = "release/plan11-x40"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_CORE = "common/media/lua/shared/NR_Core.lua"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_SERVER = LUA_DIR + "/server/PZTestKit_Server.lua"
HARNESS_COMMITS = {"016dce05": "a ghost run restores its carrier's macros; time.snapshot reports the true multiplier",
                   "07c27dc4": "the store probe formats tiny magnitudes with tostring (Kahlua %g hangs below 1e-292)"}
HARNESS_MARKERS = ("-- ---- Plan 11b Task 2 fix: a ghost run restores the carrier's macros ----",          # 016dce05
                   "g.rec.reconcile.baseline = NR.kernel.reconcile.baselineAfter(pre)",                   # 016dce05
                   'TK.call(nut, "setCalories", pre.calories)',                                           # 016dce05
                   'if type(v) == "number" and v ~= 0 and math.abs(v) < 1e-280 then return tostring(v) end '
                   '-- Kahlua %g hangs below ~1e-292',                                                    # 07c27dc4
                   'TK.register("store.probe", function(argv)',                                           # H7
                   'TK.register("minute.ring", function(argv)')                                           # H2
NR = "NutritionRevamp"
MIN_FREE_GB = 12.0
BUDGET_S = 840.0                 # from t0 (before the boot): no phase but Z starts past it
PHASE_EST_S = {"S0": 25.0, "RT": 8.0, "RC": 130.0, "R": 12.0, "W": 60.0}
PING_TIMEOUT_S = 5
RESULT_WAIT_S = 30.0
POLL_S = 0.3
S0_WAIT_S = 90.0
MIN_RUNS = 4
LOG_LIMIT = 400
SPAWN_WAIT_S = 2.5
RC_FOOD = "TKX.Mixed650"
W_FOOD = "TKX.Mixed400"
LAND_CAP_S = 20.0
RC_PRE_MIN = 4                   # game minutes run on after the landing before the quit (lambda pairs)
DEPART_CAP_S = 30.0
AWAY_MIN_H = 0.5                 # game hours past the away record's kineticsAge before the relaunch
AWAY_WAIT_CAP_S = 60.0
FIRST_STEP_CAP_S = 30.0
RC_POST_MIN = 5
GAP_CAP_H = 1.0                  # K.satiety.MAX_GAP_M = 60 game minutes
MEAL_HALF_LIFE_H = 0.583749      # K.satiety.MEAL_HALF_LIFE_H (the constant-based lambda, trait 1, reported only)
ACUTE_DECAY_HALF_LIFE_H = 0.15   # K.satiety.ACUTE_DECAY_HALF_LIFE_H (RC_S's expected value, reported only)
PAIR_MAX_M = 2.5                 # a lambda pair's kineticsAge step, game minutes (excludes the gap's step)
RC_TOL = 1e-6                    # relative; the ring carries exact doubles (TK.json's tostring branch)
CLAMP_SEP = 1e-3                 # relative separation of the no-cap value that RC_CLAMP requires
SAVE_GAP_MS = 60000              # S.SAVE_GAP_MS: a player's slot is written at most once a real minute
W_MIN_REMAIN_S = 30.0
W_FRESH_CAP_S = 70.0
STOP_TIMEOUT_S = 120
ADMIN_REC = "record:admin"
LANDED = f"{NR}.server.intake.stats.landed"
REC_PATHS = ("satiety.M", "satiety.S", "satiety.t", "kineticsAge", "stomach.buffer.calories", "stomach.liquid",
             "firstSeen", "resets", f"monotony.t.[{RC_FOOD}].n", f"monotony.t.[{W_FOOD}].n", "lastIntake.fullType")
RING_PATHS = ("satiety.M", "satiety.S", "satiety.t", "kineticsAge", "stomach.buffer.calories", "stomach.liquid",
              "lastSeen", "firstSeen", "resets", f"monotony.t.[{RC_FOOD}].n", f"monotony.t.[{W_FOOD}].n",
              f"_G.{LANDED}", f"_G.{NR}.server.intake.stats.sips", f"_G.{NR}.server.intake.stats.worldSips",
              f"_G.{NR}.server.writer.stats.sips", f"_G.{NR}.server.reconcile.stats.landed",
              f"_G.{NR}.server.writer.stats.seeded",
              f"_G.{NR}.server.store.file.stats.writes", f"_G.{NR}.server.store.file.gen.admin",
              f"_G.{NR}.server.store.file.lastWrite.admin", f"_G.{NR}.server.players.served")
PAIR_SAME = (f"_G.{LANDED}", f"_G.{NR}.server.intake.stats.sips", f"_G.{NR}.server.intake.stats.worldSips",
             f"_G.{NR}.server.writer.stats.sips", f"_G.{NR}.server.reconcile.stats.landed")
STORE_G = (f"{NR}.server.store.file.gen.admin", f"{NR}.server.store.file.lastWrite.admin",
           f"{NR}.server.store.file.stats.writes", f"{NR}.server.store.file.stats.bytes", LANDED,
           f"{NR}.server.players.online.admin")
SLOT_G = (f"{NR}.server.store.file.stats.writes", f"{NR}.server.store.file.stats.bytes",
          f"{NR}.server.store.file.stats.reads", f"{NR}.server.store.file.stats.writeFailures",
          f"{NR}.server.store.file.stats.repaired", f"{NR}.server.store.file.gen.admin",
          f"{NR}.server.store.file.gen.bob", f"{NR}.server.store.stats.loads", f"{NR}.server.store.stats.created")
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
PROBE_RX = re.compile(r"\b(?:store\.probe|tkprobe|minute\.ring|time\.snapshot|time\.multiplier|lua\.(?:read|global|call)|"
                      r"eat\.action|additem|item\.get)")
                                            # this driver's own probe and command names, excluded from every log grep
MOD_LIFE_RX = re.compile(r"minute: \w+ failed|players: hook failed|players: task|store: |writer: |intake: |"
                         r"players: first sight|non-finite")
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")


PRED = {
    "RT_SAVE": {"store.probe roundtrip save": "ok, saved true, a gen and a path; ping after it pong",
                "falsifier": "not ok on a live bus", "void": "the bus died at the save"},
    "RC_OFFLINE": {"every away ring row (on false)": "kineticsAge and satiety.M equal the away record's",
                   "falsifier": "an away row that moved", "unmeasured": "no away row"},
    "RC_DECAY": {"M_1": "M_q x exp(-lambda x min(D, 1 h)), lambda the median of the ring's online minute pairs",
                 "tolerance": f"{RC_TOL} relative", "falsifier": "outside the tolerance",
                 "unmeasured": "no lambda pair, no away record or no moved row after the rejoin",
                 "reported": "the no-cap value and ln 2 / MEAL_HALF_LIFE_H (trait 1)"},
    "RC_CLAMP": {"with D > 1 h": f"RC_DECAY as predicted and the no-cap value off M_1 by more than {CLAMP_SEP}",
                 "falsifier": "RC_DECAY falsified while D > 1 h", "unmeasured": "D <= 1 h"},
    "RC_T": {"satiety.t after the rejoin": ">= the relaunch's world age and > the away record's t",
             "falsifier": "not so"},
    "RC_S": {"satiety.S after the rejoin": "<= the away record's (expected value reported)", "trivial": "both 0",
             "falsifier": "a rise"},
    "W_ARMED": {"reading": "the landing confirmed, the stop sent with admin online, the stop's server time under "
                           "SAVE_GAP_MS after admin's last regular write; graded in S4b2 as STOPWIN"},
    "Z": {"mod_error": "none", "admin_lua_error": False, "server": "answered its last read before the stop"},
}

# session state (set in main)
prof = rec_fx = run_id = run_dir = path = tl = None
t0 = time.time()
server, clients, started = None, {}, []
cur_phase = {"name": "pre"}
bus = {"dead": None}                       # D1: the step after which the server bus stopped answering ping
stopped = {"by": None}                     # W: the server stopped on purpose; later server steps are skipped
copied = []
out = {"phases": {}, "verdicts": {}, "readings": {}, "notes": [], "steps": [], "phase_walls": {}, "phase_errors": {},
       "world_changes": {"left_in_place": []}}


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


class BusDead(Exception):
    """D1: the server bus stopped answering; the phase ends and every later server step is skipped."""


STALL_RX = re.compile(r"^(?:TimeoutError|RuntimeError)\b")


def stalled(v):
    """An ack that means the server did not answer: a TimeoutError or RuntimeError from ask()."""
    return isinstance(v, dict) and isinstance(v.get("error"), str) and STALL_RX.match(v["error"]) is not None


def srv_gone():
    return bus["dead"] or stopped["by"]


def ping(tag):
    """The bus liveness probe (D1): True only when the server answers pong inside PING_TIMEOUT_S."""
    if srv_gone():
        return False
    r = step(tag, SRV, "ping", timeout=PING_TIMEOUT_S, liveness=False)
    if r.get("ack") == "pong":
        return True
    if not bus["dead"]:
        bus["dead"] = tag
        out["abort"] = f"server bus dead after {tag}"
        note(out["abort"])
        if tl is not None:
            tl.mark("error", detail=out["abort"][:200])
    return False


def step(name, side, cmd, args="", timeout=30, liveness=True):
    t_before, e_before = wall(), time.time()
    if side == SRV and srv_gone():
        why = f"server bus dead after {bus['dead']}" if bus["dead"] else f"server stopped by {stopped['by']}"
        row = {"step": name, "side": side, "cmd": cmd, "args": args, "phase": cur_phase["name"],
               "wall_before": t_before, "wall_after": t_before, "epoch_ms_before": int(e_before * 1000),
               "epoch_ms_after": int(e_before * 1000), "took": 0.0, "skipped": True,
               "ack": {"error": f"skipped: {why}"}}
        out["steps"].append(row)
        return row
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
    if side == SRV and liveness and stalled(v):
        alive = ping(f"{name}_liveness")
        row["liveness_pong"] = alive
        if not alive:
            bus["dead"] = bus["dead"] or name
            out["abort"] = f"server bus dead after {name}"
            note(out["abort"])
            if tl is not None:
                tl.mark("error", detail=out["abort"][:200])
            raise BusDead(out["abort"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def keep(r):
    a = dict(ack(r))
    if "wall" in a:
        a["ack_wall"] = a["wall"]              # the reply's own wall (time.snapshot: the server's getTimestampMs)
    a["wall"] = r["wall_before"]
    a["wall_after"] = r["wall_after"]
    a["epoch_ms_before"] = r.get("epoch_ms_before")
    a["epoch_ms_after"] = r.get("epoch_ms_after")
    a["side"] = a.get("side", r["side"])
    if not isinstance(r.get("ack"), dict):
        a["raw"] = r.get("ack")
    if r.get("skipped"):
        a["skipped"] = True
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


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parked():
    c = clients.get("admin") if isinstance(clients, dict) else None
    return c is not None and "lua_error" in getattr(c, "seen", {})


def lread(side, root, paths, tag):
    return keep(step(tag, side, "lua.read", " ".join([root] + list(paths))))


def vals(a):
    return a.get("values") or {}


def present(a, p):
    return p in (a.get("values") or {}) or p in (a.get("tables") or {}) or p in (a.get("types") or {})


def snap(tag):
    return keep(step(tag, SRV, "time.snapshot"))


def offset_ms(s):
    """The server's getTimestampMs less the driver's epoch ms at the reply's midpoint (one machine, so near 0)."""
    w, e0, e1 = num(s.get("ack_wall")), s.get("epoch_ms_before"), s.get("epoch_ms_after")
    if w is None or e0 is None or e1 is None:
        return None
    return w - (e0 + e1) / 2.0


def wait_doc(name, after, timeout=RESULT_WAIT_S):
    if srv_gone():
        note(f"result {name}: skipped, server gone")
        return None
    try:
        return server.bus.wait_result(name, timeout=timeout, after=after)
    except Exception as e:                     # noqa: BLE001 - a missing document is a recorded fault
        note(f"result {name}: {type(e).__name__}: {e}")
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
    bus_was_dead = bus["dead"]
    try:
        fn()
    except BusDead as e:
        out["phase_walls"][name]["bus_dead"] = str(e)
        note(f"phase {name} ended: {e}")
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        if tl is not None:
            tl.mark("error", in_phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    if bus["dead"] and not bus_was_dead and not out["phase_walls"][name].get("bus_dead"):
        out["phase_walls"][name]["bus_dead"] = f"server bus dead after {bus['dead']}"
    out["phase_walls"][name]["end"] = wall()
    persist()


def rcon(cmd, tag):
    t_before, e_before = wall(), time.time()
    if srv_gone():
        rep = f"skipped: server gone ({bus['dead'] or stopped['by']})"
        out["steps"].append({"step": tag, "side": SRV, "cmd": "rcon", "args": cmd, "phase": cur_phase["name"],
                             "wall_before": t_before, "wall_after": t_before, "skipped": True,
                             "ack": {"ok": False, "reply": rep}})
        return {"cmd": cmd, "ok": False, "reply": rep, "wall": t_before, "skipped": True}
    try:
        ok, rep = server.rcon(cmd)
    except Exception as e:                     # noqa: BLE001
        ok, rep = False, f"{type(e).__name__}: {e}"
    row = {"step": tag, "side": SRV, "cmd": "rcon", "args": cmd, "phase": cur_phase["name"], "wall_before": t_before,
           "wall_after": wall(), "epoch_ms_before": int(e_before * 1000), "epoch_ms_after": int(time.time() * 1000),
           "ack": {"ok": ok, "reply": str(rep)[:300]}}
    out["steps"].append(row)
    tl.mark("rcon", cmd=cmd, ok=ok)
    return {"cmd": cmd, "ok": ok, "reply": str(rep)[:300], "wall": t_before}


def over_budget(extra=0.0):
    return wall() + extra > BUDGET_S


def poll_until(tag, fn, cap_s, sleep_s=POLL_S):
    """fn() -> (done, reading); polled until done, the cap or the wall budget; the readings kept (first 5, last 5)."""
    end = time.time() + cap_s
    polls, done, last = [], False, None
    while True:
        done, last = fn()
        polls.append(last)
        if done:
            break
        if time.time() >= end:
            note(f"{tag}: not reached inside {cap_s} s")
            break
        if over_budget():
            note(f"{tag}: stopped at the wall budget {BUDGET_S} s")
            break
        if sleep_s:
            time.sleep(sleep_s)
    return {"done": done, "last": last, "polls": len(polls),
            "kept": polls[:5] + polls[-5:] if len(polls) > 10 else polls}


def wait_age(target, tag, cap_s):
    if target is None:
        note(f"{tag}: no target age (an unread clock); not waited")
        return {"done": False, "skipped": "no target age"}

    def fn():
        s = snap(tag)
        a = num(s.get("worldAge"))
        return (a is not None and a >= target), {"worldAge": a, "wall": s.get("wall"), "srv_ms": s.get("ack_wall")}
    return poll_until(tag, fn, cap_s)


def item_get(tag, user, food):
    a = keep(step(tag, SRV, "item.get", f"{user} {food}"))
    return {"id": a.get("id"), "fullType": a.get("fullType"), "calories": a.get("calories"), "raw": a.get("raw"),
            "error": a.get("error"), "wall": a.get("wall")}


def spawn_food(tag, user, food):
    """RCON additem, confirmed by the server's item.get id (ruling T2-11); a leftover before it voids the spawn."""
    sp = {"before": item_get(f"{tag}_item0", user, food)}
    sp["additem"] = rcon(f'additem "{user}" "{food}" 1', f"{tag}_additem")
    time.sleep(SPAWN_WAIT_S)
    sp["after"] = item_get(f"{tag}_item1", user, food)
    sp["leftover_before"] = sp["before"].get("id") is not None
    sp["confirmed"] = sp["after"].get("id") is not None and not sp["leftover_before"]
    if not sp["confirmed"]:
        sp["void_reason"] = (f"a leftover {food} before the spawn (the spawn is unproven)" if sp["leftover_before"]
                             else f"no {food} on the server after the spawn")
    return sp


def eat(tag, side, food):
    a = keep(step(tag, side, "eat.action", food))
    ok = a.get("queued") is True and a.get("spawned") == "found"
    a["ok_found"] = ok
    if not ok:
        a["stop_reason"] = (f"eat.action spawned {a.get('spawned')!r}, not 'found' (the client spawned its own copy)"
                            if a.get("queued") is True else f"eat.action did not queue: {a.get('raw') or a.get('error')}")
    return a


def landed_now(tag):
    return num(vals(lread(SRV, "_G", [LANDED], tag)).get(LANDED))


def read_pages(user, tag, start_from=None):
    pages = []
    frm = start_from
    for _ in range(12):
        after = time.time() - 1.0
        args = f"{user} read" + ("" if frm is None else f" {frm}")
        r = keep(step(f"{tag}_read", SRV, "minute.ring", args, timeout=60))
        pg = {"reply": {k: r.get(k) for k in ("ok", "from", "rows", "skipped", "next", "more", "oldest", "newest",
                                               "recorded", "overwritten", "errors", "lastError", "result", "error")}}
        name = r.get("result")
        if isinstance(name, str) and name:
            doc = wait_doc(name, after)
            pg["doc_rows"] = len((doc or {}).get("rows_list") or [])
            src = os.path.join(server.bus.results_dir, name + ".json")
            if doc is not None and os.path.isfile(src):
                shutil.copyfile(src, os.path.join(run_dir, name + ".json"))
                copied.append(name + ".json")
                pg["file"] = name + ".json"
        pages.append(pg)
        if not r.get("ok") or not r.get("more") or r.get("next") is None:
            break
        frm = r.get("next")
    return pages


# ---------------------------------------------------------------- the staged copy (amendments: never re-staged)
def head_manifest():
    """release_pack.manifest() of mod/NutritionRevamp at HEAD: a `git archive` of HEAD into a scratch folder, so a
    dirty working tree is never what is compared."""
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import release_pack as RP                   # noqa: E402 - the release tool, loaded at the check
    tmp = tempfile.mkdtemp(prefix="x402-head-")
    try:
        data = subprocess.run(["git", "-C", REPO, "archive", "--format=tar", "HEAD", MOD_DIR],
                              capture_output=True, timeout=120).stdout
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            tf.extractall(tmp, filter="data")
        return RP.manifest(os.path.join(tmp, *MOD_DIR.split("/"))), RP
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def manifest_gate():
    g_ = {"head": git_say("rev-parse", "HEAD"), "staged_manifest": f"{STAGE_ROOT}/{MANIFEST_NAME}"}
    try:
        g_["manifest_sha256"] = sha256_file(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME))
        with open(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME), encoding="utf-8") as fh:
            staged = json.load(fh)
        head, RP = head_manifest()
        tree = RP.manifest(os.path.join(REPO, *STAGE_MOD.split("/")))
        g_["files"] = len(staged)
        g_["equals_head"] = staged == head
        g_["equals_staged_tree"] = staged == tree
        g_["differ_head"] = sorted(k for k in set(staged) | set(head) if staged.get(k) != head.get(k))[:20]
        g_["differ_tree"] = sorted(k for k in set(staged) | set(tree) if staged.get(k) != tree.get(k))[:20]
        with open(os.path.join(REPO, *STAGE_MOD.split("/"), *STAGED_CORE.split("/")), encoding="utf-8") as fh:
            m = re.search(r'version\s*=\s*"([^"]+)"', fh.read())
        g_["staged_version"] = m.group(1) if m else None
    except Exception as e:                     # noqa: BLE001 - a failed check refuses the boot
        g_["error"] = f"{type(e).__name__}: {e}"
    want = f'"value": "{g_.get("staged_version")}"'
    rows = [v for v in (prof.verify if prof is not None else []) if v.get("args") == f"{NR}.version"]
    g_["verify_version_rows"] = len(rows)
    g_["verify_rows_match"] = bool(rows) and all(str(v.get("expect")) == want for v in rows)
    g_["ok"] = (not g_.get("error") and g_.get("equals_head") is True and g_.get("equals_staged_tree") is True
                and g_["verify_rows_match"])
    return g_


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    P["ping"] = ping("S0_ping")
    P["players"] = keep(step("S0_players", SRV, "players"))
    P["time"] = snap("S0_time")
    P["mode"] = gread(SRV, f"{NR}.server.options.mode", "S0_mode")
    end = time.time() + S0_WAIT_S
    polls, ok = [], False
    while True:
        a = lread(SRV, "_G", [f"{NR}.server.minute.stats.runs"], "S0_runs")
        runs = num(vals(a).get(f"{NR}.server.minute.stats.runs"))
        recs = {u: gread(SRV, f"{NR}.server.store.records.{u}", f"S0_rec_{u}") for u in USERS}
        ok = all(r.get("resolved") for r in recs.values()) and runs is not None and runs >= MIN_RUNS
        polls.append({"wall": wall(), "records": {u: r.get("resolved") for u, r in recs.items()}, "runs": runs})
        if ok or time.time() >= end or over_budget():
            break
        time.sleep(POLL_S)
    P["wait"] = {"ok": ok, "polls": polls}
    if not ok:
        note("S0: the real players' records or MIN_RUNS were not reached inside S0_WAIT_S")
    P["ring_start"] = keep(step("S0_ring", SRV, "minute.ring", "admin start " + " ".join(RING_PATHS)))
    if not P["ring_start"].get("ok"):
        note(f"S0: minute.ring start failed: {P['ring_start'].get('error') or P['ring_start'].get('raw')}")
    P["slot"] = lread(SRV, "_G", SLOT_G, "S0_slot")
    P["record"] = lread(SRV, ADMIN_REC, REC_PATHS, "S0_rec")


def phase_RT():
    P = out["phases"]["RT"] = {}
    P["save"] = keep(step("RT_save", SRV, "store.probe", "roundtrip save", timeout=60))
    P["ping"] = ping("RT_ping")
    out["world_changes"]["left_in_place"].append("RT: store.probe roundtrip save wrote the probe's synthetic record "
                                                 "(one slot file and its index entry); S4b2 loads it and clears it")


def phase_RC():
    P = out["phases"]["RC"] = {"void": None}
    P["spawn"] = spawn_food("RC", "admin", RC_FOOD)
    if not P["spawn"]["confirmed"]:
        P["void"] = P["spawn"]["void_reason"]
        note(f"RC: {P['void']}; no eat (void)")
        return
    P["pre"] = lread(SRV, ADMIN_REC, REC_PATHS, "RC_pre")
    P["landed0"] = landed_now("RC_landed0")
    P["eat"] = eat("RC_eat", ADMIN, RC_FOOD)
    if not P["eat"]["ok_found"]:
        P["void"] = P["eat"]["stop_reason"]
        note(f"RC: {P['void']}; the phase stops (void)")
        return
    base = P["landed0"]

    def landed_rc():
        v = landed_now("RC_land")
        return (base is not None and v is not None and v >= base + 1), {"landed": v, "wall": wall()}
    P["land"] = poll_until("RC_land", landed_rc, LAND_CAP_S)
    if not P["land"]["done"]:
        note("RC: the eat's landing did not read inside LAND_CAP_S; the decay is still read (M as the writer left it)")
    s = snap("RC_land_t")
    a0 = num(s.get("worldAge"))
    P["pre_wait"] = wait_age(None if a0 is None else a0 + RC_PRE_MIN / 60.0, "RC_pre_wait", RC_PRE_MIN * 0.625 * 3 + 10)
    P["q_rec"] = lread(SRV, ADMIN_REC, REC_PATHS, "RC_q_rec")
    P["q_snap"] = snap("RC_q_t")
    c1 = clients.get("admin")
    tq = wall()
    try:
        P["quit_rc"] = c1.quit() if c1 is not None else None
    except Exception as e:                     # noqa: BLE001
        P["quit_error"] = f"{type(e).__name__}: {e}"
    P["quit_walls"] = [tq, wall()]
    clients.pop("admin", None)
    tl.mark("client_quit", user="admin", which="first", rc=P.get("quit_rc"))
    on = f"{NR}.server.players.online.admin"

    def departed():
        a = lread(SRV, "_G", [on, f"{NR}.server.store.file.lastWrite.admin", f"{NR}.server.store.file.gen.admin"],
                  "RC_depart")
        return (a.get("ok") is True and not present(a, on)), {"wall": a.get("wall"), "online": present(a, on),
                                                               "values": vals(a)}
    P["depart"] = poll_until("RC_depart", departed, DEPART_CAP_S)
    P["away_rec"] = lread(SRV, ADMIN_REC, REC_PATHS, "RC_away_rec")
    P["away_snap"] = snap("RC_away_t")
    k_away = num(vals(P["away_rec"]).get("kineticsAge"))
    P["away_wait"] = wait_age(None if k_away is None else k_away + AWAY_MIN_H, "RC_away_wait", AWAY_WAIT_CAP_S)
    P["launch_snap"] = snap("RC_launch_t")
    c2, restored = make_client(os.path.join(run_dir, "c1b"), "admin", server, rec_fx,
                               safemode=prof.safemode, launcher=prof.launcher)
    P["c1b_restored"] = restored
    c2.start()
    started.append(c2)
    clients["admin"] = c2
    tl.mark("client_launch", user="admin", which="c1b", restored=restored)
    P["ready_took"] = c2.wait_ready(timeout=prof.client_timeout)
    tl.mark("client_ready", user="admin", which="c1b", took=P["ready_took"])
    P["join_snap"] = snap("RC_join_t")

    def moved():
        a = lread(SRV, ADMIN_REC, REC_PATHS, "RC_first")
        k = num(vals(a).get("kineticsAge"))
        return (k is not None and k_away is not None and k != k_away), a
    P["first_after"] = poll_until("RC_first", moved, FIRST_STEP_CAP_S)
    j0 = num(P["join_snap"].get("worldAge"))
    P["post_wait"] = wait_age(None if j0 is None else j0 + RC_POST_MIN / 60.0, "RC_post_wait",
                              RC_POST_MIN * 0.625 * 3 + 10)
    P["post_rec"] = lread(SRV, ADMIN_REC, REC_PATHS, "RC_post_rec")
    out["world_changes"]["left_in_place"].append("RC: admin ate one TKX.Mixed650, quit and rejoined from a fresh "
                                                 "fixture restore in <run>/c1b")


def phase_R():
    P = out["phases"]["R"] = {}
    P["pages"] = read_pages("admin", "R")
    last = P["pages"][-1]["reply"] if P["pages"] else {}
    P["next"] = last.get("next")


def phase_W():
    P = out["phases"]["W"] = {"void": None, "stopped": False}
    P["spawn"] = spawn_food("W", "admin", W_FOOD)
    if not P["spawn"]["confirmed"]:
        P["void"] = P["spawn"]["void_reason"]
        note(f"W: {P['void']}; no eat (void)")
        return
    P["t0"] = snap("W_t0")
    P["g0"] = lread(SRV, "_G", STORE_G, "W_g0")
    lw = num(vals(P["g0"]).get(STORE_G[1]))
    sw = num(P["t0"].get("ack_wall"))
    P["remaining_ms"] = (SAVE_GAP_MS - (sw - lw)) if (lw is not None and sw is not None) else None
    if P["remaining_ms"] is None or P["remaining_ms"] < W_MIN_REMAIN_S * 1000:
        def fresh():
            a = lread(SRV, "_G", STORE_G, "W_fresh")
            v = num(vals(a).get(STORE_G[1]))
            return (v is not None and lw is not None and v > lw), {"wall": a.get("wall"), "lastWrite": v}
        P["fresh_wait"] = poll_until("W_fresh", fresh, W_FRESH_CAP_S)
        P["t0"] = snap("W_t0b")
        P["g0"] = lread(SRV, "_G", STORE_G, "W_g0b")
    P["offset_ms"] = offset_ms(P["t0"])
    P["pre_rec"] = lread(SRV, ADMIN_REC, REC_PATHS, "W_pre_rec")
    base = num(vals(P["g0"]).get(LANDED))
    P["eat"] = eat("W_eat", ADMIN, W_FOOD)
    if not P["eat"]["ok_found"]:
        P["void"] = P["eat"]["stop_reason"]
        note(f"W: {P['void']}; the phase stops (void); the teardown stops the server as usual")
        return

    def landed_w():
        a = lread(SRV, "_G", STORE_G, "W_land")
        v = num(vals(a).get(LANDED))
        return (base is not None and v is not None and v >= base + 1), a
    P["land"] = poll_until("W_land", landed_w, LAND_CAP_S, sleep_s=0)
    if not P["land"]["done"]:
        P["void"] = "the landing did not read inside LAND_CAP_S; the teardown stops the server as usual"
        note(f"W: {P['void']}")
        return
    conf = P["land"]["last"]
    P["confirm"] = {"wall": conf.get("wall"), "wall_after": conf.get("wall_after"),
                    "epoch_ms_after": conf.get("epoch_ms_after"), "values": vals(conf),
                    "admin_online": present(conf, STORE_G[5])}
    g_before = num(vals(P["g0"]).get(STORE_G[0]))
    g_conf = num(vals(conf).get(STORE_G[0]))
    P["saved_at_confirm"] = (g_before is not None and g_conf is not None and g_conf > g_before)
    # one more read before the stop: at least one bus round trip (about two game minutes) past the landing, so the
    # dirty mark's next store step is due; it shows whether that save is visible before the stop
    pre = lread(SRV, "_G", STORE_G, "W_prestop")
    g_pre = num(vals(pre).get(STORE_G[0]))
    P["prestop"] = {"wall": pre.get("wall"), "wall_after": pre.get("wall_after"), "values": vals(pre),
                    "admin_online": present(pre, STORE_G[5])}
    P["saved_before_stop"] = (g_before is not None and g_pre is not None and g_pre > g_before)
    P["stop_epoch_ms"] = int(time.time() * 1000)
    P["stop_wall"] = wall()
    stopped["by"] = "W"
    out["server_stopped_by"] = "W"
    tl.mark("server_stop_sent", by="W")
    try:
        P["stop_rc"] = server.stop(timeout=STOP_TIMEOUT_S)
    except Exception as e:                     # noqa: BLE001
        P["stop_error"] = f"{type(e).__name__}: {e}"
    P["stop_returned_wall"] = wall()
    P["stopped"] = True
    tl.mark("server_stopped", rc=P.get("stop_rc"), by="W")
    off = P.get("offset_ms")
    lw0 = num(vals(P["g0"]).get(STORE_G[1]))
    P["stop_server_ms_est"] = (P["stop_epoch_ms"] + off) if off is not None else None
    P["stop_after_last_write_ms"] = ((P["stop_server_ms_est"] - lw0) if (P["stop_server_ms_est"] is not None
                                                                        and lw0 is not None) else None)
    P["no_regular_save_possible"] = (P["stop_after_last_write_ms"] is not None
                                     and P["stop_after_last_write_ms"] < SAVE_GAP_MS)
    out["world_changes"]["left_in_place"].append("W: admin ate one TKX.Mixed400 and the server was stopped with admin "
                                                 "online (S4b2 boots this server folder)")


def phase_Z():
    P = out["phases"]["Z"] = {}
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)
                                   and not PROBE_RX.search(e)][:20]
    P["admin_parked"] = parked()
    P["mem"] = mem("Z")
    P["bus_dead"] = bus["dead"]
    P["server_stopped_by"] = stopped["by"]
    P["players"] = keep(step("Z_players", SRV, "players"))
    P["time"] = snap("Z_time")
    P["slot"] = lread(SRV, "_G", SLOT_G, "Z_slot")


def body():
    order = (("S0", phase_S0), ("RT", phase_RT), ("RC", phase_RC), ("R", phase_R), ("W", phase_W))
    out["budget"] = {"BUDGET_S": BUDGET_S, "checks": []}
    for name, fn in order:
        if srv_gone():
            break
        est = PHASE_EST_S.get(name, 0.0)
        out["budget"]["checks"].append({"phase": name, "wall": wall(), "estimate": est})
        if over_budget(est) and name != "R":
            out["abort"] = f"wall budget: {name} (estimate {est} s) would end past {BUDGET_S} s at wall {wall()} s"
            note(out["abort"])
            if name == "W" or "R" in out["phases"]:
                break
            continue                           # R still runs: the ring is lost at the stop
        run_phase(name, fn)
        if parked():
            out["abort"] = f"admin parked in the debugger after phase {name}"
            if "R" not in out["phases"] and name != "R":
                run_phase("R", phase_R)
            break
    run_phase("Z", phase_Z)


def read_logs(every):
    L = out["logs"] = {"patterns": {"life": MOD_LIFE_RX.pattern, "log": LOG_RX.pattern, "echo_excluded": ECHO_RX.pattern,
                                    "probe_excluded": PROBE_RX.pattern}, "limits": {"log": LOG_LIMIT}, "clients": {}}
    if server is not None:
        life, life_echo = grep_noecho(server.log_path, MOD_LIFE_RX, LOG_LIMIT)
        raw, echoed = grep_noecho(server.log_path, LOG_RX, LOG_LIMIT)
        L["server"] = {"life_lines": life, "life_excluded": life_echo, "lines": raw, "excluded": echoed}
    for c in every:
        u = getattr(c, "username", "?")
        lines, ech = grep_noecho(c.console, LOG_RX, 60)
        L["clients"].setdefault(u, []).append({"console": os.path.relpath(c.console, run_dir), "lines": lines,
                                               "excluded": ech})


def hex_name(u):
    """K.store.hexName: four lowercase hex digits per character code."""
    return "".join("%04x" % ord(ch) for ch in u)


def copy_store_files():
    """The store's slot and index files after the stop, copied byte-identical as store-<name>; admin's newest
    complete slot line parsed (the line S4b2 loads)."""
    S = out["store_files"] = {"files": []}
    best = None
    for f in sorted(glob.glob(os.path.join(run_dir, "server", "**", "NutritionRevamp", "*", "*.json"), recursive=True)):
        base = os.path.basename(f)
        if not (base.startswith("p_") or base.startswith("index_")):
            continue
        dest = "store-" + base
        shutil.copyfile(f, os.path.join(run_dir, dest))
        copied.append(dest)
        row = {"rel": os.path.relpath(f, run_dir).replace(os.sep, "/"), "copy": dest, "bytes": os.path.getsize(f),
               "sha256": sha256_file(f)}
        if base.startswith("p_" + hex_name("admin") + "_"):
            try:
                with open(f, encoding="utf-8") as fh:
                    text = fh.read()
                line = text.splitlines()[-1] if text.strip() else ""
                doc = json.loads(line) if line else None
                if isinstance(doc, dict):
                    row.update({"gen": doc.get("gen"), "done": doc.get("done")})
                    if doc.get("done") and (best is None or (doc.get("gen") or -1) > (best[1].get("gen") or -1)):
                        best = (dest, doc)
            except (OSError, ValueError, IndexError) as e:
                row["parse_error"] = f"{type(e).__name__}: {e}"
        S["files"].append(row)
    if best is not None:
        rec = best[1].get("rec") or {}
        mono = ((rec.get("monotony") or {}).get("t") or {})
        S["admin_newest"] = {"copy": best[0], "gen": best[1].get("gen"),
                             "W_FOOD_n": (mono.get(W_FOOD) or {}).get("n"), "RC_FOOD_n": (mono.get(RC_FOOD) or {}).get("n"),
                             "buffer_calories": ((rec.get("stomach") or {}).get("buffer") or {}).get("calories"),
                             "kineticsAge": rec.get("kineticsAge"), "satiety": rec.get("satiety")}


# ---------------------------------------------------------------- grading
def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def ring_rows():
    rows = {}
    for p in g(out, "phases", "R", "pages") or []:
        f = p.get("file")
        if not f:
            continue
        try:
            with open(os.path.join(run_dir, f), encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        for r in doc.get("rows_list") or []:
            rows[r["s"]] = r
    return [rows[s] for s in sorted(rows)]


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def lambda_pairs(rows, landed_eq=None):
    """M's clearance rate on consecutive online minute rows with no landing or sip between them."""
    out_ = []
    for a, b in zip(rows, rows[1:]):
        if a.get("on") is not True or b.get("on") is not True or a.get("norec") or b.get("norec"):
            continue
        if any(a.get(k) != b.get(k) for k in PAIR_SAME):
            continue
        if landed_eq is not None and num(a.get(PAIR_SAME[0])) != landed_eq:
            continue
        ma, mb = num(a.get("satiety.M")), num(b.get("satiety.M"))
        ka, kb = num(a.get("kineticsAge")), num(b.get("kineticsAge"))
        if None in (ma, mb, ka, kb) or ma <= 0 or mb <= 0 or kb <= ka or (kb - ka) * 60 > PAIR_MAX_M:
            continue
        out_.append({"s": [a["s"], b["s"]], "dk_min": (kb - ka) * 60, "lambda": math.log(ma / mb) / (kb - ka)})
    return out_


def decay_grade(prefix, Mq, kq, Sq, tq, rows_after, lam, lam_src, join_age, extra_obs):
    """The decay verdicts across a gap: rows_after are the ring rows after the gap (online), the first whose
    kineticsAge moved off kq is the first step."""
    first = None
    for r in rows_after:
        k = num(r.get("kineticsAge"))
        if r.get("on") is True and not r.get("norec") and k is not None and kq is not None and k != kq:
            first = r
            break
    obs = dict(extra_obs)
    obs.update({"M_q": Mq, "kineticsAge_q": kq, "lambda": lam, "lambda_source": lam_src,
                "lambda_const_trait1": math.log(2) / MEAL_HALF_LIFE_H})
    if first is None or Mq is None or kq is None or lam is None:
        grade(f"{prefix}_DECAY", PRED[f"{prefix}_DECAY"], obs, "unmeasured",
              "no lambda, no pre-gap record or no moved row")
        grade(f"{prefix}_CLAMP", PRED[f"{prefix}_CLAMP"], obs, "unmeasured", "the decay was not read")
        grade(f"{prefix}_T", PRED[f"{prefix}_T"], obs, "unmeasured", "the decay was not read")
        grade(f"{prefix}_S", PRED[f"{prefix}_S"], obs, "unmeasured", "the decay was not read")
        return obs
    k1, M1 = num(first.get("kineticsAge")), num(first.get("satiety.M"))
    D = k1 - kq
    pred = Mq * math.exp(-lam * min(D, GAP_CAP_H))
    nocap = Mq * math.exp(-lam * D)
    rel = (M1 / pred - 1.0) if (M1 is not None and pred) else None
    rel_nocap = (M1 / nocap - 1.0) if (M1 is not None and nocap) else None
    obs.update({"first_row": {k: first.get(k) for k in ("s", "age", "on", "kineticsAge", "satiety.M", "satiety.S",
                                                        "satiety.t")},
                "D_h": D, "D_min": D * 60, "M_1": M1, "predicted": pred, "rel": rel, "no_cap": nocap,
                "rel_no_cap": rel_nocap})
    ok = rel is not None and abs(rel) <= RC_TOL
    grade(f"{prefix}_DECAY", PRED[f"{prefix}_DECAY"], obs, "as_predicted" if ok else "falsified",
          "outside the tolerance")
    if D > GAP_CAP_H:
        sep = rel_nocap is not None and abs(rel_nocap) > CLAMP_SEP
        v = "as_predicted" if (ok and sep) else ("falsified" if not ok else "unmeasured")
        grade(f"{prefix}_CLAMP", PRED[f"{prefix}_CLAMP"],
              {"D_h": D, "rel": rel, "rel_no_cap": rel_nocap, "separated": sep}, v, "the decay falsified while D > 1 h")
    else:
        grade(f"{prefix}_CLAMP", PRED[f"{prefix}_CLAMP"], {"D_h": D}, "unmeasured",
              "D <= 1 h: the cap was not exercised")
    t1, S1 = num(first.get("satiety.t")), num(first.get("satiety.S"))
    t_ok = (t1 is not None and tq is not None and t1 > tq and (join_age is None or t1 >= join_age - 1e-9))
    grade(f"{prefix}_T", PRED[f"{prefix}_T"], {"t_q": tq, "t_1": t1, "join_age": join_age},
          "as_predicted" if t_ok else ("unmeasured" if t1 is None or tq is None else "falsified"), "not so")
    if Sq is None or S1 is None:
        grade(f"{prefix}_S", PRED[f"{prefix}_S"], {"S_q": Sq, "S_1": S1}, "unmeasured", "S not read")
    else:
        gap_h = (t1 - tq) if (t1 is not None and tq is not None) else None
        exp_S = (Sq * math.exp(-math.log(2) * min(gap_h, GAP_CAP_H) / ACUTE_DECAY_HALF_LIFE_H)
                 if gap_h is not None else None)
        v = "trivial" if (Sq == 0 and S1 == 0) else ("as_predicted" if S1 <= Sq + 1e-12 else "falsified")
        grade(f"{prefix}_S", PRED[f"{prefix}_S"], {"S_q": Sq, "S_1": S1, "expected": exp_S, "t_gap_h": gap_h}, v,
              "a rise")
    return obs


def grade_all():
    ph = out["phases"]
    R = out["readings"]
    # RT_SAVE
    RT = ph.get("RT") or {}
    sv = RT.get("save") or {}
    if not RT:
        grade("RT_SAVE", PRED["RT_SAVE"], None, "unmeasured", "phase RT not run")
    elif sv.get("skipped") or (bus["dead"] and not sv.get("ok")):
        grade("RT_SAVE", PRED["RT_SAVE"], sv, "void", "the bus died at the save")
    else:
        ok = sv.get("ok") is True and sv.get("saved") is True and sv.get("gen") is not None and RT.get("ping") is True
        grade("RT_SAVE", PRED["RT_SAVE"], {k: sv.get(k) for k in ("ok", "saved", "gen", "slot", "path", "bytes", "hex",
                                                                 "user", "err")} | {"ping": RT.get("ping")},
              "as_predicted" if ok else "falsified", "not ok on a live bus")
    # the ring
    rows = ring_rows()
    R["ring_rows"] = len(rows)
    RC = ph.get("RC") or {}
    l0 = num(RC.get("landed0"))
    L1 = (l0 + (1 if g(RC, "land", "done") else 0)) if l0 is not None else None   # the RC eat's count, if it landed
    away_i = next((i for i, r in enumerate(rows) if r.get("on") is False and not r.get("norec")
                   and (L1 is None or num(r.get(PAIR_SAME[0])) == L1)), None)
    pre_rows = rows[:away_i] if away_i is not None else []
    away_rows = []
    post_rows = []
    if away_i is not None:
        j = away_i
        while j < len(rows) and rows[j].get("on") is False:
            away_rows.append(rows[j])
            j += 1
        post_rows = rows[j:]
    pairs_pre = lambda_pairs(pre_rows, L1)
    pairs_post = lambda_pairs(post_rows, L1)
    lams = [p["lambda"] for p in pairs_pre + pairs_post]
    lam = median(lams)
    R["lambda"] = {"pre_pairs": len(pairs_pre), "post_pairs": len(pairs_post), "median": lam,
                   "min": min(lams) if lams else None, "max": max(lams) if lams else None,
                   "pairs": (pairs_pre + pairs_post)[:40]}
    if RC.get("void"):
        for k in ("RC_OFFLINE", "RC_DECAY", "RC_CLAMP", "RC_T", "RC_S"):
            grade(k, PRED[k], {"void": RC.get("void")}, "void", "the phase stopped")
    elif not RC or "RC" in {k for k, v in out["phase_walls"].items() if v.get("bus_dead")}:
        for k in ("RC_OFFLINE", "RC_DECAY", "RC_CLAMP", "RC_T", "RC_S"):
            grade(k, PRED[k], None, "void" if RC else "unmeasured",
                  "the bus died inside RC" if RC else "phase RC not run")
    else:
        aw = vals(RC.get("away_rec") or {})
        Mq, kq = num(aw.get("satiety.M")), num(aw.get("kineticsAge"))
        Sq, tq = num(aw.get("satiety.S")), num(aw.get("satiety.t"))
        if away_rows:
            moved = [r["s"] for r in away_rows if num(r.get("kineticsAge")) != kq or num(r.get("satiety.M")) != Mq]
            grade("RC_OFFLINE", PRED["RC_OFFLINE"], {"away_rows": len(away_rows), "moved": moved[:10], "M_q": Mq,
                                                     "kineticsAge_q": kq},
                  "as_predicted" if not moved else "falsified", "an away row that moved")
        else:
            grade("RC_OFFLINE", PRED["RC_OFFLINE"], {"away_rows": 0}, "unmeasured", "no away row")
        decay_grade("RC", Mq, kq, Sq, tq, post_rows, lam, "the ring's online minute pairs (S4b1)",
                    num(g(RC, "launch_snap", "worldAge")),
                    {"ready_took": RC.get("ready_took"), "depart_polls": g(RC, "depart", "polls"),
                     "first_direct": vals(g(RC, "first_after", "last") or {})})
    # W_ARMED (a reading; S4b2 grades STOPWIN)
    W = ph.get("W") or {}
    R["W_ARMED"] = {k: W.get(k) for k in ("void", "stopped", "saved_at_confirm", "saved_before_stop", "prestop",
                                          "stop_wall", "stop_epoch_ms",
                                          "stop_server_ms_est", "stop_after_last_write_ms", "no_regular_save_possible",
                                          "remaining_ms", "offset_ms", "stop_rc", "stop_error")}
    R["W_ARMED"]["g0"] = vals(W.get("g0") or {})
    R["W_ARMED"]["confirm"] = W.get("confirm")
    R["W_ARMED"]["pre_rec"] = vals(W.get("pre_rec") or {})
    R["W_ARMED"]["state"] = "stopped" if W.get("stopped") else ("void" if W.get("void") else "not run")
    # slot size (a reading)
    for tag in ("S0", "Z"):
        sl = vals(g(ph, tag, "slot") or {})
        w_, b_ = num(sl.get(SLOT_G[0])), num(sl.get(SLOT_G[1]))
        R[f"slot_bytes_per_write_{tag}"] = (b_ / w_) if (w_ and b_ is not None) else None
    # Z
    Z = ph.get("Z") or {}
    if Z:
        last_ok = (W.get("stopped") is True and isinstance(g(W, "confirm", "values"), dict)) or \
                  isinstance(g(Z, "players", "raw"), list)
        lines = Z.get("server_mod_error_lines") or []
        ok = not lines and not out.get("admin_lua_error") and last_ok
        grade("Z", PRED["Z"], {"server_mod_error_lines": lines, "admin_lua_error": out.get("admin_lua_error"),
                               "server_answered": last_ok}, "as_predicted" if ok else "falsified",
              "a mod error line, admin parked, or no server answer")
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
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"), "build": rec_fx.get("build")},
        "argv": sys.argv[1:],
        "commit": git_say("rev-parse", "--short", "HEAD"),
        "mod_commit": git_say("log", "-1", "--format=%h", "--", MOD_DIR),
        "mod_dirty_not_booted": git_dirty(MOD_DIR)[0],
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
        "harness_commits": HARNESS_COMMITS,
        "harness_fixes_are_ancestors": {c: git_say("merge-base", "--is-ancestor", c, "HEAD") == ""
                                        for c in HARNESS_COMMITS},
        "harness_lua_dirty": git_dirty(LUA_DIR)[0],
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "meta": {"staged_mod": STAGE_MOD, "staged_manifest": f"{STAGE_ROOT}/{MANIFEST_NAME}",
                 "staging": "python tools/release_pack.py stage mod/NutritionRevamp --out release/plan11-x40 (the "
                            "controller, after Task 3c); the driver checks it and never stages",
                 "chain_note": "S4b2 (x402b_store.py) copies this run's <run>/server folder and boots it again "
                               "(x260b's method); this session's end is W's server stop with admin online",
                 "ring_note": "a ring row is sampled inside EveryOneMinute before the mod's queue drains that minute",
                 "decay_note": "KIN.drain caps a gap's drain at K.satiety.MAX_GAP_M (60) game minutes in one-minute "
                               "substeps, and K.satiety.mealClear clears M first-order on each, so M after the gap is "
                               "M_q x exp(-lambda x min(D, 1 h)) exactly; lambda (ln 2 x trait / MEAL_HALF_LIFE_H) is "
                               "measured on the ring",
                 "stop_note": "a dedicated server fires no Lua event around a stop (ruling T20-1): the eat reaches "
                              "the file only through the dirty mark's next store step"},
        "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                      if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict,
                                                                             re.Pattern))
                      and k not in ("REPO", "PRED")},
        "predictions": PRED,
        "deviations": [
            "store.probe bench and the slot size are dropped as owed reads (absorbed by x391h, #3757-#3761); the slot "
            "size is kept as a reading.",
            "The stop window's stop follows one read past the read that confirms the landing (a game minute is 0.625 s "
            "and a server bus round trip about 1.3 s), with saved_at_confirm, saved_before_stop and the stop's server "
            "time against admin's last "
            "regular write recorded; the run sheet's 'within one game minute' is not reachable through the bus.",
            "The reconnect's away wait AWAY_MIN_H is a driver choice so the offline gap passes the 60 game-minute cap.",
            "RC eats TKX.Mixed650 and W TKX.Mixed400, so each phase's monotony entry is its own.",
        ],
        "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                          "left_in_place": []},
        "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
        "readings": {}, "memory": [],
    }
    try:
        out["meta"]["harness_server_sha256"] = sha256_file(os.path.join(REPO, HARNESS_SERVER))
    except OSError as e:
        out["meta"]["hash_error"] = f"{type(e).__name__}: {e}"
    if not doctor_clean:
        out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
        persist()
        print(json.dumps(out["doctor"], indent=1))
        sys.exit(1)
    out["manifest_gate"] = mg = manifest_gate()
    out["meta"]["staged_manifest_sha256"] = mg.get("manifest_sha256")
    if not mg["ok"]:
        out["error"] = f"the staged copy does not match HEAD's manifest or the verify rows: {mg!r}; not started"
        persist()
        print(out["error"][:2000])
        sys.exit(1)
    try:
        with open(os.path.join(REPO, HARNESS_SERVER), encoding="utf-8", errors="replace") as fh:
            srv_text = fh.read()
    except OSError as e:
        srv_text = ""
        out["meta"]["harness_read_error"] = f"{type(e).__name__}: {e}"
    out["meta"]["harness_markers_found"] = {m: (m in srv_text) for m in HARNESS_MARKERS}
    if not all(out["meta"]["harness_markers_found"].values()):
        out["error"] = "PZTestKit_Server.lua lacks a harness marker (016dce05, 07c27dc4, store.probe, minute.ring)"
        persist()
        print(out["error"])
        sys.exit(1)
    if not all(out["harness_fixes_are_ancestors"].values()):
        out["error"] = f"a harness fix is not an ancestor of HEAD: {out['harness_fixes_are_ancestors']!r}; not started"
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
        copied.append(MANIFEST_NAME)
    except OSError as e:
        out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        out["server_launch_wall"] = wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = wall()
        tl.mark("server_started")
        clients = attach_clients(run_dir, prof, server, rec_fx, tl, started=started)
        tl.mark("session_ready")
        out["session_ready_wall"] = wall()
        out["build"] = server.build
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
                        text = fh.read()   # read once (x391f-20261013-113457, ruling B3-2)
                    dm[rel] = all(m in text for m in HARNESS_MARKERS)
                except OSError as e:
                    dm[rel] = f"{type(e).__name__}: {e}"
        out["meta"]["deployed_harness_markers"] = dm
        mem("ready")
        persist()
        if not dm or not all(v is True for v in dm.values()):
            out["abort"] = f"the deployed PZTestKit_Server.lua lacks a harness marker: {dm!r}"
            tl.mark("error", detail=out["abort"][:200])
            print(out["abort"])
        elif not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
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
            if server is not None and stopped["by"]:
                # the server is gone: a client quit has nothing to disconnect from, so the clients are killed
                for c in every:
                    if c.alive:
                        c.kill()
                        tl.mark("client_killed", user=getattr(c, "username", "?"), why="server stopped by W")
            elif server is not None:
                teardown(tl, server, [c for c in every if c.alive])
                out["server_stop_wall"] = wall()
        except Exception as e:                     # noqa: BLE001
            out["teardown_error"] = f"{type(e).__name__}: {e}"
        finally:
            if server is not None:
                hard_kill(server, every)
            out["admin_lua_error"] = any("lua_error" in getattr(c, "seen", {}) for c in every
                                         if getattr(c, "username", None) == "admin")
            out["client_seen"] = [{"user": getattr(c, "username", str(i)), **dict(getattr(c, "seen", {}))}
                                  for i, c in enumerate(every)]
            if server is not None:
                out["server_errors"] = server.errors[:30]
                out["server_error_count"] = len(server.errors)
            mem("after")
            try:
                read_logs(every)
            except Exception as e:                 # noqa: BLE001
                out["logs_error"] = f"{type(e).__name__}: {e}"
            try:
                copy_store_files()
            except Exception as e:                 # noqa: BLE001
                out["store_files_error"] = f"{type(e).__name__}: {e}"
            try:
                grade_all()
            except Exception as e:                 # noqa: BLE001
                out["summary_error"] = f"{type(e).__name__}: {e}"
                out["summary_traceback"] = traceback.format_exc()[-3000:]
            out["bus_dead"] = bus["dead"]
            out["copied"] = sorted(set(copied))
            out["wall_seconds"] = round(time.time() - t0, 1)
            persist()
            dest_dir = os.path.join(REPO, "testing", "artifacts", run_id)
            try:
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copyfile(path, os.path.join(dest_dir, ARTIFACT))
                for f in sorted(set(copied)):
                    if os.path.isfile(os.path.join(run_dir, f)):
                        shutil.copyfile(os.path.join(run_dir, f), os.path.join(dest_dir, f))
                print(f"copied to {dest_dir}")
            except Exception as e:                 # noqa: BLE001 - never raise
                print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "lambda": g(out, "readings", "lambda", "median"), "W_ARMED": g(out, "readings", "W_ARMED"),
                      "bus_dead": out.get("bus_dead"), "server_stopped_by": out.get("server_stopped_by"),
                      "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "run_id": run_id, "run_dir": run_dir,
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])


if __name__ == "__main__":
    main()
