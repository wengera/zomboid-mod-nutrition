"""x402b-store -- Plan 11b Task 4 session S4b2 (live), the second of two boots on one world (x260b's method): session
S4b1's (x402a_store.py) <run>/server folder is COPIED into this run's folder and booted again with
make_server(reuse=True) (each session its own run folder, so a failed session never damages the saved state); each
client is a fresh fixture restore. Read across the restart: the stop window's eat in the newest slot line (ruling
T20-1), the restart decay (ruling C-1's server half: satiety.M, S and t across the restart's gap, clamped at
K.satiety.MAX_GAP_M = 60 game minutes), the JSON number round trip's load and the probe's clear (H7), the prune
(phase G of the plan), bob's rejoin on a fresh record and his first-minute eat (ruling C-2).

USAGE: python testing/experiments/x402b_store.py <S4b1 run dir or run id (testing/runs/<id>)>

One boot of profile x40-store-b (x40-store byte for byte below its header but the description): fixture two, bob
(release) attached FIRST and then admin (-debug), so admin's first sight comes well past the 60 game-minute cap after
the boot; Nutrition false; DayLength 1; TKX_StudyFoods; the SAME staged copy S4b1 booted (release/plan11-x40). Before
the boot the driver checks that the staged MANIFEST.json equals release_pack.manifest() of mod/NutritionRevamp at
HEAD (a `git archive` of HEAD) and of the staged mod folder itself, and that its sha256 equals the one S4b1 recorded;
it refuses to boot on a mismatch, and never stages. No commit or sha is hard-coded. The harness markers are checked
as in S4b1 (016dce05, 07c27dc4, store.probe, minute.ring), on the repository file and on every deployed copy.
Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

Artifact: `store.json`, with the staged MANIFEST.json, S4b1's newest admin slot line (start.json), the minute-ring
pages and this session's store files beside it, byte-identical.

PHASES (PRE, A, then the clients, RD, RTL, G, C2, R, Z):
  PRE (before the boot, no game process): S4b1's store.json read (its W phase, its lambda, its RT reply, its last
      snapshot); S4b1's <run>/server copied whole into <run>/server; the copied store files parsed: admin's newest
      complete slot line (the line the store loads; written to start.json), bob's, and the probe's two slot files.
  A   the server booted on the copy, BEFORE any client: time.snapshot (the clock continued from S4b1's world save);
      record:admin (no record expected: the store loads at first sight); `minute.ring admin start <RING_PATHS>`, so
      the ring sees the first sight; the store's counters.
  --  the clients: bob, then admin (attach_clients users ["bob", "admin"]); the verify rows.
  RD  THE RESTART DECAY. record:admin polled until its kineticsAge moves off the slot line's (the first kinetics step
      after the load; cap FIRST_STEP_CAP_S); RD_POST_MIN game minutes run on; the store's counters (loads, created);
      admin's ring read so far (so a later dead bus keeps the restart's rows; R reads on from its `next`).
  RTL `store.probe roundtrip load` (the eight hard doubles loaded through F.load and K.store.load, each compared with
      == and logged on the server), a ping, `store.probe clear` (both probe slots emptied, its index entry dropped,
      the index written), a ping, the store's index read.
  G   THE PRUNE (plan phase G). The server's wall ms T_q (time.snapshot's `wall`, getTimestampMs, the unit S.prune
      takes) and NutritionRevamp.server.players.served; bob's client quits; polled every POLL_G_S until bob's
      departure has run in the queue: players.online.bob nil, served past its value at the quit and
      store.file.lastWrite.bob >= T_q (the departure task's slot write); G_DEPART_CAP_S without all three is
      unmeasured, with the reads, and the prune is not run. Then `lua.call NutritionRevamp.server.store.prune
      <T_q + 31 x 86400000> 30` (S.prune(now, keepDays)); store.records.bob, store.file.index.bob and
      store.file.lastWrite.bob read; one more minute event waited (served rises again); the three read once more.
      The prune leaves store.file.lastPrune 31 days ahead, so the hourly prune does not run again this uptime.
  C2  BOB'S REJOIN AND FIRST-MINUTE EAT (ruling C-2). The counters (writer.stats.seeded, store.stats.created,
      intake.stats.landed, intake.stats.acuteFlags, players.served) read; `minute.ring bob start <BOB_RING>`; the game
      clock SLOWED with `time.multiplier SLOW_MULT` (a game minute then lasts 0.625 / SLOW_MULT s of wall, so no minute
      event, and so no first sight and no writer step, falls while bob joins and eats; a networked eat ends in real
      time whatever the clock, #3766); a fresh fixture restore in <run>/c2b joins as bob; TKX.Mixed400 spawned on bob
      by RCON additem and CONFIRMED by item.get (ruling T2-11); record:bob read; `eat.action TKX.Mixed400` on bob's
      client (spawned must read "found"); INTAKE_LANDED polled to +1; record:bob and the counters read at once (the
      landing read); `time.multiplier 1` restores the clock; polled until writer.stats.seeded rises (bob's first
      writer step seeds M); record:bob and the counters read again.
  R   `minute.ring admin read` from RD's `next` and `minute.ring bob read`, page after page, copied byte-identical.
  Z   the local readings first (mod error lines, admin parked, memory), then players, time.snapshot and the counters.

LIVENESS, BUDGET (x391h's D1, D2, as S4b1): a server step that times out is followed by a ping; no pong -> the bus
is dead, every later server step is skipped and the run goes to Z; a phase the bus died inside is VOID. The wall
budget BUDGET_S (840 s from t0, before PRE and the boot) is checked before each phase and inside every poll. The
clock is restored to 1 in C2's finally whenever it was slowed and the bus answers. Teardown, the store files' copy,
the artifact copy and the grading run in `finally`. No graded frame window exists, so no drop window is needed.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured / void; each with its falsifier):
  STOPWIN   (ruling T20-1; graded from S4b1's W reading and the copied slot files, before the boot) admin's newest
            complete slot line holds the stop window's eat: its gen is past S4b1's pre-eat gen and its
            monotony.t.[TKX.Mixed400].n is at least 1 (absent before the eat). Falsifier: either not so. Trivial: the
            stop's server time came SAVE_GAP_MS or more after admin's last regular write, so a regular save could
            carry it. Unmeasured: S4b1's W did not stop the server after a confirmed landing.
  CLOCK     the boot's world age is at or after S4b1's last time.snapshot and within CLOCK_MAX_M game minutes of it
            (the world saved at the stop). Falsifier: earlier, or later by more.
  LOAD      admin's first record read after the load carries the slot line's firstSeen and resets, and
            store.stats.created reads 0 at RD's end (both players loaded from file, no fresh record). Falsifier: any
            one not so.
  RD_DECAY  the first ring row whose kineticsAge moved off the slot line's reads M_1 = M_slot x exp(-lambda x
            min(D, GAP_CAP_H)), D = kineticsAge_1 - kineticsAge_slot, within RC_TOL relative; lambda the median of this
            session's admin ring pairs (no eat on admin here), else S4b1's. Falsifier: outside. Unmeasured: no lambda,
            no slot line or no moved row.
  RD_CLAMP  with D > 1 h: RD_DECAY as predicted and the no-cap value off by more than CLAMP_SEP. Unmeasured: D <= 1 h.
  RD_T      satiety.t at the first step reads at or after the boot's world age and later than the slot line's.
  RD_S      satiety.S at the first step is at most the slot line's (expected value reported). Trivial: both 0.
  RT_LOAD   `store.probe roundtrip load` answers ok, userEqual true and allEqual true: each of the eight values equal
            (==) on the raw decoded record and on the loaded one. Falsifier: any false on a live bus. Unmeasured: no
            probe slot reads (S4b1's save failed). Void: the bus died at the load.
  CLEAR     `store.probe clear` answers ok, emptied true, indexed true and indexWritten true, and after the session
            both probe slot files read empty. Falsifier: any not so on a live bus.
  G_DEPART  bob's departure ran inside G_DEPART_CAP_S: online.bob nil, served past its quit value, lastWrite.bob >=
            T_q. Unmeasured (not falsified): the cap passed, with the reads; the prune is then not run.
  G_PRUNE   the prune answers 1 (bob alone: admin is online, the probe cleared) and store.records.bob,
            store.file.index.bob and store.file.lastWrite.bob read nil. Falsifier: any other count or a non-nil read.
  G_HOLD    after one more minute event (served risen) the three read nil again: no queued write refilled the slot.
            Falsifier: a non-nil read. Unmeasured: served did not rise inside the cap.
  REJOIN    bob's rejoined record reads resets 0, firstSeen between the relaunch's world age and the landing read's,
            and store.stats.created up by 1 from C2's start. Falsifier: any not so.
  C2_ORDER  the slowed clock holds off bob's first writer step: the landing read finds writer.stats.seeded unchanged
            since C2's start, so the eat landed before the seed. Falsifier: seeded rose before the landing read; C2_M
            and C2_SEED are then unmeasured (never falsified).
  C2_M      at the landing read bob's record holds no finite satiety.M: the eat in the fresh record's first minute is
            not fed into M (IN.feed skips an absent M; the writer's named limitation). Falsifier: a finite M with
            seeded unchanged.
  C2_SEED   after the clock is restored, writer.stats.seeded rises by 1 inside SEED_CAP_S and bob's satiety.M reads a
            finite number (seeded from the HUNGER the eat lowered). Falsifier: not so on a live bus.
  C2_ACUTE  the acute empty-stomach multiplier (K.nutrients.ACUTE_EMPTY_MULT 1.5 below ACUTE_EMPTY_FILL 0.2) is
            UNMEASURED by design, written before the run: no shipped or study food crosses an acute rung only under
            the multiplier (iron's rung 2 is 20 mg/kg, about 1400 mg at 70 kg, 933 mg under x1.5; vitamin A's acute
            test is absolute, with no multiplier), and an eat before first sight finds no record.body, so
            IN.acuteAtEat tests nothing. Read beside it: body.fm at the landing and intake.stats.acuteFlags' delta.
  Z         no mod error line on the server; admin not parked; the server answers its last players read.

READINGS (not graded): S4b1's drift lost at the stop (the slot line's kineticsAge against S4b1's last ring row); the
slot line's buffer calories against S4b1's pre-eat read; the round trip's eight values; bob's seeded M; the slowed
clock's replies; the store's index keys before and after the clear.

DEVIATIONS from the run sheet and the amendments, stated before the run:
  1. Bob is attached before admin, so admin's first sight comes past the 60 game-minute cap after the boot.
  2. C2 slows the game clock (time.multiplier SLOW_MULT) for bob's rejoin and eat: at DayLength 1 a game minute is
     0.625 s and an eat lasts 4.64 s of real time, so a first-minute eat is otherwise impossible.
  3. The acute multiplier half of C-2 is unmeasured by design (C2_ACUTE).

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


PROFILE = "x40-store-b"
PREFIX = "x402b"
SESSION = ("Plan 11b Task 4 session S4b2: S4b1's server folder booted again -- the stop window's eat, the restart "
           "decay, the round trip's load and clear, the prune, bob's rejoin and first-minute eat, on the staged 1.0.0 "
           "release; one boot of " + PROFILE)
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert PROFILE == "x40-store-b", f"PROFILE {PROFILE} is not this driver's profile"
ARTIFACT = "store.json"
S1_ARTIFACT = "store.json"
MANIFEST_NAME = "MANIFEST.json"
ADMIN = "client:admin"
BOB = "client:bob"
SRV = "server"
USERS = ("admin", "bob")
ATTACH_ORDER = ["bob", "admin"]
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
BUDGET_S = 840.0                 # from t0 (before PRE and the boot): no phase but Z starts past it
PHASE_EST_S = {"A": 8.0, "RD": 20.0, "RTL": 10.0, "G": 45.0, "C2": 100.0, "R": 15.0}
PING_TIMEOUT_S = 5
RESULT_WAIT_S = 30.0
POLL_S = 0.3
POLL_G_S = 0.5
LOG_LIMIT = 400
SPAWN_WAIT_S = 2.5
W_FOOD = "TKX.Mixed400"          # S4b1's stop-window food
RC_FOOD = "TKX.Mixed650"         # S4b1's reconnect food
C2_FOOD = "TKX.Mixed400"
LAND_CAP_S = 20.0
FIRST_STEP_CAP_S = 40.0
RD_POST_MIN = 5
CLOCK_MAX_M = 60.0
GAP_CAP_H = 1.0                  # K.satiety.MAX_GAP_M = 60 game minutes
MEAL_HALF_LIFE_H = 0.583749      # K.satiety.MEAL_HALF_LIFE_H (the constant-based lambda, trait 1, reported only)
ACUTE_DECAY_HALF_LIFE_H = 0.15   # K.satiety.ACUTE_DECAY_HALF_LIFE_H (RD_S's expected value, reported only)
PAIR_MAX_M = 2.5
RC_TOL = 1e-6
CLAMP_SEP = 1e-3
SAVE_GAP_MS = 60000              # S.SAVE_GAP_MS
G_DEPART_CAP_S = 60.0
G_MINUTE_CAP_S = 15.0
PRUNE_AHEAD_MS = 31 * 86400000   # T_q + 31 real days
PRUNE_KEEP_DAYS = 30
SLOW_MULT = 0.001                # a game minute of 625 s of wall while bob joins and eats
SEED_CAP_S = 15.0
ADMIN_REC = "record:admin"
BOB_REC = "record:bob"
LANDED = f"{NR}.server.intake.stats.landed"
SEEDED = f"{NR}.server.writer.stats.seeded"
CREATED = f"{NR}.server.store.stats.created"
ACUTE = f"{NR}.server.intake.stats.acuteFlags"
SERVED = f"{NR}.server.players.served"
REC_PATHS = ("satiety.M", "satiety.S", "satiety.t", "kineticsAge", "stomach.buffer.calories", "stomach.liquid",
             "firstSeen", "resets", f"monotony.t.[{RC_FOOD}].n", f"monotony.t.[{W_FOOD}].n", "lastIntake.fullType")
C2_PATHS = ("satiety.M", "satiety.S", "satiety.t", "kineticsAge", "firstSeen", "lastSeen", "resets", "body.fm",
            "body.lm", "stomach.buffer.calories", "stomach.liquid", "lastIntake.fullType", f"monotony.t.[{C2_FOOD}].n")
COUNTERS = (SEEDED, CREATED, f"{NR}.server.store.stats.loads", LANDED, ACUTE, SERVED,
            f"{NR}.server.store.file.stats.writes", f"{NR}.server.store.file.stats.reads",
            f"{NR}.server.store.file.stats.readFailures", f"{NR}.server.store.file.stats.pruned")
RING_PATHS = ("satiety.M", "satiety.S", "satiety.t", "kineticsAge", "stomach.buffer.calories", "stomach.liquid",
              "lastSeen", "firstSeen", "resets", f"monotony.t.[{RC_FOOD}].n", f"monotony.t.[{W_FOOD}].n",
              f"_G.{LANDED}", f"_G.{NR}.server.intake.stats.sips", f"_G.{NR}.server.intake.stats.worldSips",
              f"_G.{NR}.server.writer.stats.sips", f"_G.{NR}.server.reconcile.stats.landed", f"_G.{SEEDED}",
              f"_G.{NR}.server.store.file.stats.writes", f"_G.{NR}.server.store.file.gen.admin",
              f"_G.{NR}.server.store.file.lastWrite.admin", f"_G.{SERVED}", f"_G.{NR}.server.store.stats.loads")
BOB_RING = ("satiety.M", "satiety.t", "kineticsAge", "firstSeen", "resets", "body.fm", f"monotony.t.[{C2_FOOD}].n",
            f"_G.{SEEDED}", f"_G.{LANDED}", f"_G.{CREATED}")
PAIR_SAME = (f"_G.{LANDED}", f"_G.{NR}.server.intake.stats.sips", f"_G.{NR}.server.intake.stats.worldSips",
             f"_G.{NR}.server.writer.stats.sips", f"_G.{NR}.server.reconcile.stats.landed")
G_PATHS = (f"{NR}.server.players.online.bob", SERVED, f"{NR}.server.store.file.lastWrite.bob",
           f"{NR}.server.store.file.index.bob", f"{NR}.server.store.records.bob")
NIL3 = (f"{NR}.server.store.records.bob", f"{NR}.server.store.file.index.bob", f"{NR}.server.store.file.lastWrite.bob")
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
    "STOPWIN": {"admin's newest complete slot line": f"gen past S4b1's pre-eat gen and monotony.t.[{W_FOOD}].n >= 1",
                "falsifier": "either not so", "trivial": "the stop came SAVE_GAP_MS or more after the last regular write",
                "unmeasured": "S4b1's W did not stop the server after a confirmed landing"},
    "CLOCK": {"boot age - S4b1's last snapshot age, game minutes": [0, CLOCK_MAX_M],
              "falsifier": "earlier, or later by more"},
    "LOAD": {"first record read": "firstSeen and resets equal the slot line's", "store.stats.created at RD's end": 0,
             "falsifier": "any one not so"},
    "RD_DECAY": {"M_1": "M_slot x exp(-lambda x min(D, 1 h)), lambda the median of this session's admin ring pairs "
                        "(else S4b1's)", "tolerance": f"{RC_TOL} relative", "falsifier": "outside the tolerance",
                 "unmeasured": "no lambda, no slot line or no moved row",
                 "reported": "the no-cap value and ln 2 / MEAL_HALF_LIFE_H (trait 1)"},
    "RD_CLAMP": {"with D > 1 h": f"RD_DECAY as predicted and the no-cap value off M_1 by more than {CLAMP_SEP}",
                 "falsifier": "RD_DECAY falsified while D > 1 h", "unmeasured": "D <= 1 h"},
    "RD_T": {"satiety.t at the first step": ">= the boot's world age and > the slot line's t", "falsifier": "not so"},
    "RD_S": {"satiety.S at the first step": "<= the slot line's (expected value reported)", "trivial": "both 0",
             "falsifier": "a rise"},
    "RT_LOAD": {"store.probe roundtrip load": "ok, userEqual true, allEqual true (eight values == raw and loaded)",
                "falsifier": "any false on a live bus", "unmeasured": "no probe slot reads",
                "void": "the bus died at the load"},
    "CLEAR": {"store.probe clear": "ok, emptied, indexed, indexWritten all true; both probe slot files empty after",
              "falsifier": "any not so on a live bus"},
    "G_DEPART": {"within s": G_DEPART_CAP_S, "online.bob": "nil", "served": "past its quit value",
                 "lastWrite.bob": ">= T_q", "unmeasured": "the cap passed (the reads kept; no prune run)"},
    "G_PRUNE": {"lua.call store.prune <T_q + 31 d> 30": 1, "records.bob, file.index.bob, file.lastWrite.bob": "nil",
                "falsifier": "any other count or a non-nil read"},
    "G_HOLD": {"after one more minute event": "the three nil again", "falsifier": "a non-nil read",
               "unmeasured": "served did not rise inside the cap"},
    "REJOIN": {"resets": 0, "firstSeen": "between the relaunch's world age and the landing read's",
               "store.stats.created": "+1 from C2's start", "falsifier": "any not so"},
    "C2_ORDER": {"writer.stats.seeded at the landing read": "unchanged since C2's start (the eat landed before bob's "
                                                            "first writer step)",
                 "else": "C2_M and C2_SEED unmeasured"},
    "C2_M": {"bob's satiety.M at the landing read": "absent or not finite (not fed: IN.feed skips an absent M)",
             "falsifier": "a finite M with seeded unchanged"},
    "C2_SEED": {"after the clock's restore": f"writer.stats.seeded +1 inside {SEED_CAP_S} s and a finite satiety.M",
                "falsifier": "not so on a live bus"},
    "C2_ACUTE": {"the acute empty-stomach multiplier": "unmeasured by design (no food crosses a rung only under x1.5; "
                                                       "no record.body before first sight)",
                 "read": "body.fm at the landing, intake.stats.acuteFlags' delta"},
    "Z": {"mod_error": "none", "admin_lua_error": False, "players": "answers a list"},
}

# session state (set in main)
prof = rec_fx = run_id = run_dir = path = tl = None
t0 = time.time()
server, clients, started = None, {}, []
cur_phase = {"name": "pre"}
bus = {"dead": None}
stopped = {"by": None}                     # unused in this session (kept for the shared helpers)
copied = []
S1 = {}
S1_DIR = None
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
            tl.mark("error", phase=name, detail=str(e)[:200])
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


# ---------------------------------------------------------------- S4b1 and the copy
def parse_line(f):
    """The last line of a slot file decoded: (doc, line) or (None, reason)."""
    try:
        with open(f, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        return None, f"{type(e).__name__}: {e}"
    if not text.strip():
        return None, "empty"
    line = text.splitlines()[-1]
    try:
        doc = json.loads(line)
    except ValueError as e:
        return None, f"ValueError: {e}"
    return (doc, line) if isinstance(doc, dict) else (None, "not an object")


def newest_slot(root, user):
    """The newest complete slot line of a user under root: {file, gen, rec, line} or None, and every slot file read."""
    files, best = [], None
    for f in sorted(glob.glob(os.path.join(root, "**", "NutritionRevamp", "*", f"p_{hex_name(user)}_*.json"),
                              recursive=True)):
        doc, line = parse_line(f)
        row = {"rel": os.path.relpath(f, run_dir).replace(os.sep, "/"), "bytes": os.path.getsize(f),
               "sha256": sha256_file(f)}
        if doc is None:
            row["unread"] = line
        else:
            row.update({"gen": doc.get("gen"), "done": doc.get("done")})
            if doc.get("done") is True and isinstance(doc.get("rec"), dict) and \
                    (best is None or (num(doc.get("gen")) or -1) > (num(best["gen"]) or -1)):
                best = {"file": os.path.basename(f), "gen": doc.get("gen"), "rec": doc["rec"], "line": line}
        files.append(row)
    return best, files


def s1_last_age(s1):
    ages = [num(g(st, "ack", "worldAge")) for st in (s1.get("steps") or [])
            if st.get("side") == SRV and st.get("cmd") == "time.snapshot" and isinstance(st.get("ack"), dict)]
    ages = [a for a in ages if a is not None]
    return max(ages) if ages else None


def phase_PRE():
    P = out["phases"]["PRE"] = {}
    with open(os.path.join(S1_DIR, S1_ARTIFACT), encoding="utf-8") as fh:
        s1 = json.load(fh)
    S1["doc"] = s1
    P["s1_run_id"] = s1.get("run_id")
    P["s1_verdicts"] = {k: v.get("verdict") for k, v in (s1.get("verdicts") or {}).items()}
    P["s1_manifest_sha256"] = g(s1, "meta", "staged_manifest_sha256")
    P["s1_W"] = g(s1, "readings", "W_ARMED")
    P["s1_lambda"] = g(s1, "readings", "lambda", "median")
    P["s1_rt_save"] = {k: g(s1, "phases", "RT", "save", k) for k in ("ok", "saved", "gen", "slot", "hex", "user")}
    P["s1_last_snapshot_age"] = s1_last_age(s1)
    P["s1_server_stopped_by"] = s1.get("server_stopped_by")
    src = os.path.join(S1_DIR, "server")
    if not os.path.isdir(os.path.join(src, "Server")):
        raise RuntimeError(f"S4b1 has no server cache at {src}")
    t_c = time.time()
    shutil.copytree(src, os.path.join(run_dir, "server"))
    P["copy_seconds"] = round(time.time() - t_c, 2)
    root = os.path.join(run_dir, "server")
    best, files = newest_slot(root, "admin")
    P["admin_slots"] = files
    bob, bfiles = newest_slot(root, "bob")
    P["bob_slots"] = bfiles
    P["bob_newest_gen"] = bob["gen"] if bob else None
    hx = P["s1_rt_save"].get("hex")
    P["probe_slots"] = [{"rel": os.path.relpath(f, run_dir).replace(os.sep, "/"), "bytes": os.path.getsize(f)}
                        for f in sorted(glob.glob(os.path.join(root, "**", "NutritionRevamp", "*", f"p_{hx}_*.json"),
                                                  recursive=True))] if hx else []
    if best is None:
        raise RuntimeError("no complete admin slot line in the copy")
    rec = best["rec"]
    sat = rec.get("satiety") or {}
    mono = (rec.get("monotony") or {}).get("t") or {}
    S1["slot_rec"] = rec
    P["slot"] = {"file": best["file"], "gen": best["gen"], "kineticsAge": rec.get("kineticsAge"),
                 "satiety": {k: sat.get(k) for k in ("M", "S", "L", "t", "nicH")},
                 "firstSeen": rec.get("firstSeen"), "resets": rec.get("resets"), "lastSeen": rec.get("lastSeen"),
                 "W_FOOD_n": (mono.get(W_FOOD) or {}).get("n"), "RC_FOOD_n": (mono.get(RC_FOOD) or {}).get("n"),
                 "buffer_calories": ((rec.get("stomach") or {}).get("buffer") or {}).get("calories"),
                 "liquid": (rec.get("stomach") or {}).get("liquid")}
    with open(os.path.join(run_dir, "start.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(best["line"])
    copied.append("start.json")


# ---------------------------------------------------------------- phases
def phase_A():
    P = out["phases"]["A"] = {}
    P["boot_snap"] = snap("A_boot_t")
    P["record_before_client"] = lread(SRV, ADMIN_REC, ["satiety.M", "kineticsAge"], "A_rec0")
    P["ring_start"] = keep(step("A_ring", SRV, "minute.ring", "admin start " + " ".join(RING_PATHS)))
    if not P["ring_start"].get("ok"):
        note(f"A: minute.ring start failed: {P['ring_start'].get('error') or P['ring_start'].get('raw')}")
    P["counters"] = lread(SRV, "_G", COUNTERS, "A_counters")
    P["index"] = gread(SRV, f"{NR}.server.store.file.index", "A_index")


def phase_RD():
    P = out["phases"]["RD"] = {}
    k_slot = num((out["phases"].get("PRE") or {}).get("slot", {}).get("kineticsAge"))

    def moved():
        a = lread(SRV, ADMIN_REC, REC_PATHS, "RD_first")
        k = num(vals(a).get("kineticsAge"))
        if a.get("ok") is True and "first_present" not in P:
            P["first_present"] = a               # the first read that finds the loaded record
        return (k is not None and k_slot is not None and k != k_slot), a
    P["first_step"] = poll_until("RD_first", moved, FIRST_STEP_CAP_S)
    s = snap("RD_t")
    a0 = num(s.get("worldAge"))
    P["post_wait"] = wait_age(None if a0 is None else a0 + RD_POST_MIN / 60.0, "RD_post_wait",
                              RD_POST_MIN * 0.625 * 3 + 10)
    P["post_rec"] = lread(SRV, ADMIN_REC, REC_PATHS, "RD_post_rec")
    P["counters"] = lread(SRV, "_G", COUNTERS, "RD_counters")
    P["ring_pages"] = read_pages("admin", "RD_ring")       # read now, so a later dead bus keeps the restart's rows
    last = P["ring_pages"][-1]["reply"] if P["ring_pages"] else {}
    P["ring_next"] = last.get("next")


def phase_RTL():
    P = out["phases"]["RTL"] = {}
    P["load"] = keep(step("RTL_load", SRV, "store.probe", "roundtrip load", timeout=60))
    P["load_ping"] = ping("RTL_load_ping")
    P["index_before"] = gread(SRV, f"{NR}.server.store.file.index", "RTL_index0")
    P["clear"] = keep(step("RTL_clear", SRV, "store.probe", "clear", timeout=60))
    P["clear_ping"] = ping("RTL_clear_ping")
    P["index_after"] = gread(SRV, f"{NR}.server.store.file.index", "RTL_index1")
    out["world_changes"]["left_in_place"].append("RTL: the probe's slots emptied and its index entry dropped (clear)")


def nil3(tag):
    a = lread(SRV, "_G", NIL3, tag)
    return {"ok": a.get("ok"), "present": {p: present(a, p) for p in NIL3}, "values": vals(a),
            "missing": a.get("missing"), "wall": a.get("wall")}


def phase_G():
    P = out["phases"]["G"] = {"pruned": False}
    P["t_q"] = snap("G_tq")
    T_q = num(P["t_q"].get("ack_wall"))
    P["T_q"] = T_q
    P["q"] = lread(SRV, "_G", G_PATHS, "G_q")
    served_q = num(vals(P["q"]).get(SERVED))
    c = clients.get("bob")
    tq = wall()
    try:
        P["quit_rc"] = c.quit() if c is not None else None
    except Exception as e:                     # noqa: BLE001
        P["quit_error"] = f"{type(e).__name__}: {e}"
    P["quit_walls"] = [tq, wall()]
    clients.pop("bob", None)
    tl.mark("client_quit", user="bob", which="first", rc=P.get("quit_rc"))

    def departed():
        a = lread(SRV, "_G", G_PATHS, "G_depart")
        v = vals(a)
        on, sv, lw = present(a, G_PATHS[0]), num(v.get(SERVED)), num(v.get(G_PATHS[2]))
        done = (a.get("ok") is True and not on and sv is not None and served_q is not None and sv > served_q
                and lw is not None and T_q is not None and lw >= T_q)
        return done, {"wall": a.get("wall"), "online": on, "served": sv, "lastWrite": lw,
                      "index": v.get(G_PATHS[3]), "record": present(a, G_PATHS[4])}
    P["depart"] = poll_until("G_depart", departed, G_DEPART_CAP_S, sleep_s=POLL_G_S)
    if not P["depart"]["done"] or T_q is None:
        note("G: bob's departure did not read inside G_DEPART_CAP_S (or T_q unread); the prune is not run")
        return
    now = int(T_q + PRUNE_AHEAD_MS)
    P["prune_now"] = now
    P["prune"] = keep(step("G_prune", SRV, "lua.call", f"{NR}.server.store.prune {now} {PRUNE_KEEP_DAYS}"))
    P["pruned"] = True
    out["world_changes"]["left_in_place"].append("G: bob's record pruned (his slots emptied, his index entry "
                                                 "dropped); store.file.lastPrune set 31 days ahead for this uptime")
    P["nil_a"] = nil3("G_nil_a")
    sa = num(vals(lread(SRV, "_G", [SERVED], "G_served_a")).get(SERVED))
    P["served_after_prune"] = sa

    def minute():
        v = num(vals(lread(SRV, "_G", [SERVED], "G_served_b")).get(SERVED))
        return (v is not None and sa is not None and v > sa), {"served": v, "wall": wall()}
    P["minute"] = poll_until("G_minute", minute, G_MINUTE_CAP_S)
    P["nil_b"] = nil3("G_nil_b")
    P["pruned_stat"] = lread(SRV, "_G", [f"{NR}.server.store.file.stats.pruned"], "G_pruned_stat")


def phase_C2():
    P = out["phases"]["C2"] = {"void": None, "slowed": False}
    if "bob" in clients or not g(out, "phases", "G", "pruned"):
        P["void"] = ("bob is still online (G did not quit him)" if "bob" in clients
                     else "the prune did not run, so bob's record is not fresh")
        note(f"C2: {P['void']}; not run (void)")
        return
    P["c0"] = lread(SRV, "_G", COUNTERS, "C2_c0")
    P["ring_start"] = keep(step("C2_ring", SRV, "minute.ring", "bob start " + " ".join(BOB_RING)))
    try:
        P["slow"] = keep(step("C2_slow", SRV, "time.multiplier", str(SLOW_MULT)))
        P["slowed"] = True
        P["launch_snap"] = snap("C2_launch_t")
        c2, restored = make_client(os.path.join(run_dir, "c2b"), "bob", server, rec_fx,
                                   safemode=prof.safemode, launcher=prof.launcher)
        P["c2b_restored"] = restored
        c2.start()
        started.append(c2)
        clients["bob"] = c2
        tl.mark("client_launch", user="bob", which="c2b", restored=restored)
        P["ready_took"] = c2.wait_ready(timeout=prof.client_timeout)
        tl.mark("client_ready", user="bob", which="c2b", took=P["ready_took"])
        P["ready_snap"] = snap("C2_ready_t")
        P["spawn"] = spawn_food("C2", "bob", C2_FOOD)
        if not P["spawn"]["confirmed"]:
            P["void"] = P["spawn"]["void_reason"]
            note(f"C2: {P['void']}; no eat (void)")
            return
        P["pre"] = lread(SRV, BOB_REC, C2_PATHS, "C2_pre")
        P["pre_counters"] = lread(SRV, "_G", COUNTERS, "C2_pre_counters")
        base = num(vals(P["c0"]).get(LANDED))
        P["eat"] = eat("C2_eat", BOB, C2_FOOD)
        if not P["eat"]["ok_found"]:
            P["void"] = P["eat"]["stop_reason"]
            note(f"C2: {P['void']}; the phase stops (void)")
            return

        def landed_c2():
            a = lread(SRV, "_G", COUNTERS, "C2_land")
            v = num(vals(a).get(LANDED))
            return (base is not None and v is not None and v >= base + 1), a
        P["land"] = poll_until("C2_land", landed_c2, LAND_CAP_S)
        P["land_rec"] = lread(SRV, BOB_REC, C2_PATHS, "C2_land_rec")
        P["land_snap"] = snap("C2_land_t")
    finally:
        if P["slowed"] and not srv_gone():
            P["restore"] = keep(step("C2_restore", SRV, "time.multiplier", "1"))
            P["slowed"] = False
            tl.mark("clock_restored")
    if not g(P, "land", "done"):
        note("C2: the landing did not read inside LAND_CAP_S")
        return
    s_land = num(vals(g(P, "land", "last") or {}).get(SEEDED))

    def seeded():
        a = lread(SRV, "_G", COUNTERS, "C2_seed")
        v = num(vals(a).get(SEEDED))
        return (v is not None and s_land is not None and v > s_land), a
    P["seed"] = poll_until("C2_seed", seeded, SEED_CAP_S)
    P["after_rec"] = lread(SRV, BOB_REC, C2_PATHS, "C2_after_rec")
    out["world_changes"]["left_in_place"].append("C2: bob rejoined from a fresh fixture restore in <run>/c2b on a "
                                                 "fresh record and ate one TKX.Mixed400")


def phase_R():
    P = out["phases"]["R"] = {}
    P["admin"] = read_pages("admin", "R_admin", g(out, "phases", "RD", "ring_next"))
    P["bob"] = read_pages("bob", "R_bob") if "C2" in out["phases"] else []


def phase_Z():
    P = out["phases"]["Z"] = {}
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)
                                   and not PROBE_RX.search(e)][:20]
    P["admin_parked"] = parked()
    P["mem"] = mem("Z")
    P["bus_dead"] = bus["dead"]
    P["players"] = keep(step("Z_players", SRV, "players"))
    P["time"] = snap("Z_time")
    P["counters"] = lread(SRV, "_G", COUNTERS, "Z_counters")


def body():
    order = (("RD", phase_RD), ("RTL", phase_RTL), ("G", phase_G), ("C2", phase_C2), ("R", phase_R))
    out["budget"] = {"BUDGET_S": BUDGET_S, "checks": []}
    for name, fn in order:
        if srv_gone():
            break
        est = PHASE_EST_S.get(name, 0.0)
        out["budget"]["checks"].append({"phase": name, "wall": wall(), "estimate": est})
        if over_budget(est) and name != "R":
            out["abort"] = f"wall budget: {name} (estimate {est} s) would end past {BUDGET_S} s at wall {wall()} s"
            note(out["abort"])
            continue                           # R still runs: the rings are read before the stop
        run_phase(name, fn)
        if parked():
            out["abort"] = f"admin parked in the debugger after phase {name}"
            if name != "R":
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


def ring_rows_of(key):
    rows = {}
    pages = (g(out, "phases", "RD", "ring_pages") or []) if key == "admin" else []
    for p in pages + (g(out, "phases", "R", key) or []):
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


def phase_void(name):
    """A phase the bus died inside: its verdicts are void."""
    return bool((out["phase_walls"].get(name) or {}).get("bus_dead"))


def grade_all():
    ph = out["phases"]
    R = out["readings"]
    PRE = ph.get("PRE") or {}
    slot = PRE.get("slot") or {}
    # STOPWIN (S4b1's W against the copied slot line)
    s1W = PRE.get("s1_W") or {}
    g0 = s1W.get("g0") or {}
    pre_rec = s1W.get("pre_rec") or {}
    gen0 = num(g0.get(f"{NR}.server.store.file.gen.admin"))
    n_pre = num(pre_rec.get(f"monotony.t.[{W_FOOD}].n")) or 0
    n_slot = num(slot.get("W_FOOD_n"))
    obs = {"s1_state": s1W.get("state"), "s1_saved_at_confirm": s1W.get("saved_at_confirm"),
           "s1_saved_before_stop": s1W.get("saved_before_stop"),
           "s1_no_regular_save_possible": s1W.get("no_regular_save_possible"),
           "s1_stop_after_last_write_ms": s1W.get("stop_after_last_write_ms"), "gen_pre_eat": gen0,
           "slot_gen": slot.get("gen"), "n_pre_eat": n_pre, "n_slot": n_slot,
           "buffer_pre_eat": pre_rec.get("stomach.buffer.calories"), "buffer_slot": slot.get("buffer_calories"),
           "admin_online_at_confirm": g(s1W, "confirm", "admin_online")}
    if s1W.get("state") != "stopped" or not slot:
        grade("STOPWIN", PRED["STOPWIN"], obs, "unmeasured", "S4b1's W did not stop the server after a landing")
    else:
        present_ = (num(slot.get("gen")) is not None and gen0 is not None and num(slot.get("gen")) > gen0
                    and n_slot is not None and n_slot >= n_pre + 1)
        if not present_:
            v = "falsified"
        elif s1W.get("no_regular_save_possible") is True:
            v = "as_predicted"
        else:
            v = "trivial"
        grade("STOPWIN", PRED["STOPWIN"], obs, v, "the slot line lacks the eat")
    # CLOCK
    A = ph.get("A") or {}
    s1_age, boot = num(PRE.get("s1_last_snapshot_age")), num(g(A, "boot_snap", "worldAge"))
    if s1_age is not None and boot is not None:
        dm = (boot - s1_age) * 60
        grade("CLOCK", PRED["CLOCK"], {"s1_last_age": s1_age, "boot_age": boot, "game_minutes": dm},
              "as_predicted" if 0 <= dm <= CLOCK_MAX_M else "falsified", "earlier, or later by more")
    else:
        grade("CLOCK", PRED["CLOCK"], {"s1_last_age": s1_age, "boot_age": boot}, "unmeasured", "no age on a side")
    # LOAD
    RD = ph.get("RD") or {}
    first = vals(RD.get("first_present") or {})
    created = num(vals(RD.get("counters") or {}).get(CREATED))
    if RD and first and not phase_void("RD"):
        checks = {k: {"slot": slot.get(k), "read": first.get(k), "ok": slot.get(k) == first.get(k)}
                  for k in ("firstSeen", "resets")}
        checks["created"] = {"read": created, "ok": created == 0}
        grade("LOAD", PRED["LOAD"], checks, "as_predicted" if all(c["ok"] for c in checks.values()) else "falsified",
              "any one not so")
    else:
        grade("LOAD", PRED["LOAD"], {"first": first}, "void" if phase_void("RD") else "unmeasured",
              "the record never read")
    # RD (the restart decay)
    rows = ring_rows_of("admin")
    R["admin_ring_rows"] = len(rows)
    sat = slot.get("satiety") or {}
    k_slot = num(slot.get("kineticsAge"))
    post = [r for r in rows if num(r.get("kineticsAge")) is not None and num(r.get("kineticsAge")) != k_slot]
    pairs = lambda_pairs(post)
    lams = [p["lambda"] for p in pairs]
    lam, src = median(lams), "this session's admin ring pairs"
    if lam is None and num(PRE.get("s1_lambda")) is not None:
        lam, src = num(PRE.get("s1_lambda")), "S4b1's lambda (no pair here)"
    R["lambda"] = {"pairs": len(pairs), "median": median(lams), "min": min(lams) if lams else None,
                   "max": max(lams) if lams else None, "s1": PRE.get("s1_lambda"), "used": lam, "source": src}
    if phase_void("RD"):
        for k in ("RD_DECAY", "RD_CLAMP", "RD_T", "RD_S"):
            grade(k, PRED[k], None, "void", "the bus died inside RD")
    else:
        decay_grade("RD", num(sat.get("M")), k_slot, num(sat.get("S")), num(sat.get("t")), rows, lam, src, boot,
                    {"slot_file": slot.get("file"), "slot_gen": slot.get("gen")})
    # RT_LOAD and CLEAR
    RTL = ph.get("RTL") or {}
    ld, cl = RTL.get("load") or {}, RTL.get("clear") or {}
    if not RTL:
        grade("RT_LOAD", PRED["RT_LOAD"], None, "unmeasured", "phase RTL not run")
        grade("CLEAR", PRED["CLEAR"], None, "unmeasured", "phase RTL not run")
    else:
        lobs = {k: ld.get(k) for k in ("ok", "userEqual", "allEqual", "gen", "slot", "reason", "err", "hex", "user")}
        lobs["values"] = ld.get("values")
        if ld.get("skipped") or (phase_void("RTL") and not ld.get("ok")):
            grade("RT_LOAD", PRED["RT_LOAD"], lobs, "void", "the bus died at the load")
        elif ld.get("reason") and not ld.get("ok"):
            grade("RT_LOAD", PRED["RT_LOAD"], lobs, "unmeasured", "no probe slot reads")
        else:
            ok = ld.get("ok") is True and ld.get("userEqual") is True and ld.get("allEqual") is True
            grade("RT_LOAD", PRED["RT_LOAD"], lobs, "as_predicted" if ok else "falsified", "any false on a live bus")
        hx = ld.get("hex") or g(PRE, "s1_rt_save", "hex")
        after = [{"file": os.path.basename(f), "bytes": os.path.getsize(f)} for f in
                 sorted(glob.glob(os.path.join(run_dir, "server", "**", "NutritionRevamp", "*", f"p_{hx}_*.json"),
                                  recursive=True))] if hx else []
        cobs = {k: cl.get(k) for k in ("ok", "emptied", "indexed", "indexWritten")}
        cobs.update({"probe_files_after": after, "index_keys_before": g(RTL, "index_before", "keyCount"),
                     "index_keys_after": g(RTL, "index_after", "keyCount")})
        if cl.get("skipped") or (phase_void("RTL") and not cl.get("ok")):
            grade("CLEAR", PRED["CLEAR"], cobs, "void", "the bus died at the clear")
        else:
            ok = (all(cl.get(k) is True for k in ("ok", "emptied", "indexed", "indexWritten")) and bool(after)
                  and all(f["bytes"] == 0 for f in after))
            grade("CLEAR", PRED["CLEAR"], cobs, "as_predicted" if ok else "falsified", "any not so on a live bus")
    # G
    G = ph.get("G") or {}
    if not G:
        for k in ("G_DEPART", "G_PRUNE", "G_HOLD"):
            grade(k, PRED[k], None, "unmeasured", "phase G not run")
    elif phase_void("G") and not G.get("pruned"):
        dep = G.get("depart") or {}
        grade("G_DEPART", PRED["G_DEPART"], {"T_q": G.get("T_q"), "last": dep.get("last"), "polls": dep.get("polls")},
              "as_predicted" if dep.get("done") else "void", "the bus died inside G")
        for k in ("G_PRUNE", "G_HOLD"):
            grade(k, PRED[k], {"depart": dep.get("last")}, "void", "the bus died inside G")
    else:
        dep = G.get("depart") or {}
        grade("G_DEPART", PRED["G_DEPART"], {"T_q": G.get("T_q"), "last": dep.get("last"), "polls": dep.get("polls"),
                                             "kept": dep.get("kept")},
              "as_predicted" if dep.get("done") else "unmeasured", "the cap passed (unmeasured, never falsified)")
        if not G.get("pruned"):
            grade("G_PRUNE", PRED["G_PRUNE"], None, "unmeasured", "the prune was not run")
            grade("G_HOLD", PRED["G_HOLD"], None, "unmeasured", "the prune was not run")
        else:
            r1 = num(g(G, "prune", "r1"))
            na = G.get("nil_a") or {}
            ok = r1 == 1 and na.get("ok") is True and not any((na.get("present") or {}).values())
            grade("G_PRUNE", PRED["G_PRUNE"], {"r1": r1, "prune": G.get("prune"), "nil_a": na,
                                               "pruned_stat": vals(G.get("pruned_stat") or {})},
                  "as_predicted" if ok else "falsified", "any other count or a non-nil read")
            nb = G.get("nil_b") or {}
            if not g(G, "minute", "done"):
                grade("G_HOLD", PRED["G_HOLD"], {"minute": G.get("minute"), "nil_b": nb}, "unmeasured",
                      "served did not rise inside the cap")
            else:
                ok = nb.get("ok") is True and not any((nb.get("present") or {}).values())
                grade("G_HOLD", PRED["G_HOLD"], {"minute": g(G, "minute", "last"), "nil_b": nb},
                      "as_predicted" if ok else "falsified", "a non-nil read")
    # C2 and REJOIN
    C2 = ph.get("C2") or {}
    keys = ("REJOIN", "C2_ORDER", "C2_M", "C2_SEED")
    c0 = vals(C2.get("c0") or {})
    land_c = vals(g(C2, "land", "last") or {})
    lr = C2.get("land_rec") or {}
    lv = vals(lr)
    acute_obs = {"body_fm_at_landing": lv.get("body.fm"), "body_present_at_landing": present(lr, "body.fm"),
                 "acuteFlags_delta": ((num(land_c.get(ACUTE)) - num(c0.get(ACUTE)))
                                      if None not in (num(land_c.get(ACUTE)), num(c0.get(ACUTE))) else None),
                 "why": "no food crosses an acute rung only under x1.5 (iron rung 2 is 20 mg/kg); an eat before "
                        "first sight finds no record.body"}
    grade("C2_ACUTE", PRED["C2_ACUTE"], acute_obs, "unmeasured", "unmeasured by design (written before the run)")
    R["C2"] = {"slow_reply": g(C2, "slow", "raw"), "restore_reply": g(C2, "restore", "raw"),
               "ready_took": C2.get("ready_took"), "seeded_M": vals(C2.get("after_rec") or {}).get("satiety.M")}
    if not C2 or C2.get("void"):
        for k in keys:
            grade(k, PRED[k], {"void": C2.get("void")} if C2 else None, "void" if C2 else "unmeasured",
                  C2.get("void") or "phase C2 not run")
    elif phase_void("C2") and not g(C2, "land", "done"):
        for k in keys:
            grade(k, PRED[k], None, "void", "the bus died inside C2")
    elif not g(C2, "land", "done"):
        for k in keys:
            grade(k, PRED[k], {"land": C2.get("land")}, "unmeasured", "the landing did not read")
    else:
        la, lo = num(g(C2, "launch_snap", "worldAge")), num(g(C2, "land_snap", "worldAge"))
        fs, rs = num(lv.get("firstSeen")), lv.get("resets")
        cr0, cr1 = num(c0.get(CREATED)), num(land_c.get(CREATED))
        ok = (rs == 0 and fs is not None and la is not None and lo is not None and la - 1e-9 <= fs <= lo + 1e-9
              and cr0 is not None and cr1 is not None and cr1 - cr0 == 1)
        grade("REJOIN", PRED["REJOIN"], {"resets": rs, "firstSeen": fs, "launch_age": la, "landing_age": lo,
                                         "created_c0": cr0, "created_landing": cr1,
                                         "lastIntake": lv.get("lastIntake.fullType")},
              "as_predicted" if ok else "falsified", "any not so")
        s0, sl = num(c0.get(SEEDED)), num(land_c.get(SEEDED))
        order_ok = s0 is not None and sl is not None and sl == s0
        grade("C2_ORDER", PRED["C2_ORDER"], {"seeded_c0": s0, "seeded_landing": sl,
                                             "satiety_t_landing": lv.get("satiety.t")},
              "as_predicted" if order_ok else "falsified", "seeded rose before the landing read")
        M_land = num(lv.get("satiety.M"))
        if not order_ok:
            grade("C2_M", PRED["C2_M"], {"M_landing": M_land}, "unmeasured", "the seed preceded the landing")
            grade("C2_SEED", PRED["C2_SEED"], None, "unmeasured", "the seed preceded the landing")
        else:
            finite = M_land is not None and M_land == M_land and abs(M_land) != float("inf")
            grade("C2_M", PRED["C2_M"], {"M_landing": M_land, "M_present": present(lr, "satiety.M"),
                                         "missing": (lr.get("missing") or {}).get("satiety.M"),
                                         "monotony_n": lv.get(f"monotony.t.[{C2_FOOD}].n")},
                  "falsified" if finite else "as_predicted", "a finite M with seeded unchanged")
            sd = C2.get("seed") or {}
            M_after = num(vals(C2.get("after_rec") or {}).get("satiety.M"))
            s_after = num(vals(sd.get("last") or {}).get(SEEDED))
            ok = sd.get("done") is True and s_after == (sl + 1) and M_after is not None
            v = "as_predicted" if ok else ("void" if phase_void("C2") else "falsified")
            grade("C2_SEED", PRED["C2_SEED"], {"seeded_landing": sl, "seeded_after": s_after, "M_after": M_after,
                                               "polls": sd.get("polls")}, v, "not so on a live bus")
    # Z
    Z = ph.get("Z") or {}
    if Z:
        lines = Z.get("server_mod_error_lines") or []
        answered = isinstance(g(Z, "players", "raw"), list)
        ok = not lines and not out.get("admin_lua_error") and answered
        grade("Z", PRED["Z"], {"server_mod_error_lines": lines, "admin_lua_error": out.get("admin_lua_error"),
                               "players": g(Z, "players", "raw")}, "as_predicted" if ok else "falsified",
              "a mod error line, admin parked, or no players answer")
    else:
        grade("Z", PRED["Z"], None, "unmeasured", "phase Z not run")


# ---------------------------------------------------------------- run
def main():
    global prof, rec_fx, run_id, run_dir, path, tl, t0, server, clients, out, S1_DIR
    if len(sys.argv) < 2:
        print(__doc__.split("USAGE: ")[1].splitlines()[0])
        sys.exit(2)
    S1_DIR = sys.argv[1] if os.path.isdir(sys.argv[1]) else os.path.join(REPO, "testing", "runs", sys.argv[1])
    prof = profile.load(PROFILE)
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(PREFIX)
    path = os.path.join(run_dir, ARTIFACT)
    tl, t0 = Timeline(), time.time()
    doctor_clean, doctor_text = doctor()
    out = {
        "run_id": run_id, "session": SESSION, "users": list(prof.users), "attach_order": ATTACH_ORDER,
        "profile": prof.report(),
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"), "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "session1_dir": S1_DIR,
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
                 "staging": "the same staged copy S4b1 booted (release/plan11-x40, the controller's); never staged here",
                 "chain_note": "S4b1's <run>/server copied whole into this run folder and booted with "
                               "make_server(reuse=True); each client is a fresh fixture restore (restore_client refuses "
                               "an existing folder); the characters persist server-side",
                 "ring_note": "a ring row is sampled inside EveryOneMinute before the mod's queue drains that minute",
                 "slow_note": f"C2 sets time.multiplier {SLOW_MULT} while bob joins and eats (a game minute of "
                              f"{0.625 / SLOW_MULT:.0f} s of wall) and restores 1 after the landing read",
                 "prune_note": "S.prune(now, keepDays) with now = T_q + 31 days; it sets store.file.lastPrune to that "
                               "now, so the hourly prune is not due again this uptime"},
        "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                      if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, list,
                                                                             re.Pattern))
                      and k not in ("REPO", "PRED", "S1_DIR")},
        "predictions": PRED,
        "deviations": [
            "Bob is attached before admin, so admin's first sight comes past the 60 game-minute cap after the boot.",
            f"C2 slows the game clock (time.multiplier {SLOW_MULT}) for bob's rejoin and eat: at DayLength 1 a game "
            "minute is 0.625 s and a networked eat lasts 4.64 s of real time, so a first-minute eat is otherwise "
            "impossible.",
            "The acute multiplier half of C-2 is unmeasured by design (C2_ACUTE).",
        ],
        "world_changes": {"restored": "S4b1's server folder copied; both clients restored from fixture two",
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
    run_phase("PRE", phase_PRE)
    if "PRE" in out["phase_errors"]:
        out["error"] = "phase PRE failed: no boot"
        persist()
        print(json.dumps(out["phase_errors"], indent=1)[:3000])
        sys.exit(1)
    s1_sha = g(out, "phases", "PRE", "s1_manifest_sha256")
    if s1_sha != mg.get("manifest_sha256"):
        out["error"] = (f"the staged MANIFEST sha256 {mg.get('manifest_sha256')} is not the one S4b1 booted "
                        f"({s1_sha}): not the same staged copy; not started")
        persist()
        print(out["error"])
        sys.exit(1)
    try:
        shutil.copyfile(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME), os.path.join(run_dir, MANIFEST_NAME))
        copied.append(MANIFEST_NAME)
    except OSError as e:
        out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, reuse=True, gclog=prof.gclog)
        out["server_launch_wall"] = wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = wall()
        tl.mark("server_started")
        run_phase("A", phase_A)
        clients = attach_clients(run_dir, prof, server, rec_fx, tl, users=ATTACH_ORDER, started=started)
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
            if server is not None:
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
                      "lambda": g(out, "readings", "lambda"), "C2": g(out, "readings", "C2"),
                      "bus_dead": out.get("bus_dead"),
                      "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "run_id": run_id, "run_dir": run_dir,
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])


if __name__ == "__main__":
    main()
