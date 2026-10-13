"""x406-monotony -- Plan 11b Task 4 session S4f (live): the 168 h monotony window's edge crossed live with no step, on
the staged 1.0.0 copy the controller made after Task 3c (release/plan11-x40/NutritionRevamp/Contents/mods/
NutritionRevamp, staged with `python tools/release_pack.py stage mod/NutritionRevamp --out release/plan11-x40`;
release/ is gitignored; mod/ is never booted). One boot of profile x40-monotony (fixture default, admin -debug,
Nutrition false, DayLength 1, sleep off, TKX_StudyFoods by its path). Build 42.21.0 (4a0e9546ec). Artifact
`monotony.json`, the staged MANIFEST.json and the minute ring's pages copied byte-identical beside it. Written BEFORE
the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

The driver hard-codes no commit or sha of the mod: before the boot it compares the staged copy's MANIFEST.json with
tools/release_pack.py's manifest() of mod/NutritionRevamp at HEAD (the tree clean) and of the staged tree itself,
records HEAD and the MANIFEST's sha256, and refuses to boot on any mismatch; it never re-stages. It asserts its PREFIX
and PROFILE against its own file name and the harness markers of 016dce05, 07c27dc4, 2ffdbc81, 513778e8 and ccb71a1b
(the repository copies before the boot, every deployed copy after it), each commit an ancestor of HEAD. The lib is
x391h_bench.py's (Plan 11b Task 2's latest), as x404_exercise.py carries it: bus liveness, the wall budget, spawns
confirmed by the server's item.get, grading in `finally`.

WHY (run sheet Task 4 (c), 11f): the 168 h monotony window edge. A type back-dated with H6 (`record.set`) to 167.9
game hours since its last eat crosses the edge with no step in the floor targets or the written UNHAPPINESS and
BOREDOM: one type with a decayed count above one portion at the edge stays in monotony.t; one at or under one portion
is dropped, its level already 0 (NR_Kernel_Monotony.lua: K.monotony.count past the window reads K.monotony.faded, the
decayed count while above one portion, else 0; K.monotony.prune drops a type past the window whose count is 0, and it
runs only at an eat, NR_Server_Intake IN.monotony). PANIC is held at or under 5 (#3691: vanilla resets BOREDOM while
PANIC is above 5).

THE ARITHMETIC (named before the run; the constants read live at S0): a type's count at dt game hours after its last
eat is n x 2^(-dt / HALF_LIFE_H 72); at the edge (dt = WINDOW_H 168) the factor is 2^(-168/72) = 0.19843; its level
is SLOPE 4.3 x max(0, count - 1), at most CAP 30; the BOREDOM target is the largest level, held under BORED_MAX 49.
The driver sets TKX.Mono450's n to COUNT_A_EDGE / factor (count 3.0 at the edge: level 8.6, falling about 0.12 a game
hour, continuous across the edge) and TKX.Mixed400's to COUNT_B_EDGE / factor (count 0.8 at the edge: level 0 on
both sides of it), and both types' `last` to the world age minus (WINDOW_H - EDGE_LEAD_H), so the edge comes
EDGE_LEAD_H (0.2 game hours, 12 game minutes, 7.5 s of wall) after the sets (167.8 h; the run sheet's 167.9 h, see
DEVIATIONS). The sets run on a nearly stopped clock (`time.multiplier SET_MULT`), so the writes land at one world age.

PHASES (each checked against the wall budget before it starts; the server bus's liveness after every server step):
  S0    ready, ping, players, speed 1, the kernel constants (K.monotony.WINDOW_H, HALF_LIFE_H, SLOPE, CAP, BORED_MAX,
        MEAL_KCAL), the record, the server's PANIC, UNHAPPINESS and BOREDOM (stats.all).
  H     the minute ring armed on admin: both types' n, last and s, Unit50's n, the writer's last inputs (panic,
        unhappyTarget, boredTarget, bored), its writes, the intake's eats and landed (every row also carries the six
        written stats, UNHAPPINESS and BOREDOM among them).
  FOOD  RCON `additem "admin" "TKX.Mono450" 6`, `"TKX.Mixed400" 3` and `"TKX.Unit50" 1`, each confirmed by the
        server's item.get id with no leftover before it (ruling T2-11; never inventory.add).
  EATS  at speed 1, N_A eats of TKX.Mono450 then N_B of TKX.Mixed400, each: foodtimer 0, eat.action <type> 1 (a
        `spawned` other than "found" stops the eats, ruling T2-11), intake.stats.landed polled until it rises
        (EAT_CAP_S); then both entries read.
  SET   the clock read (its trueMult), then `time.multiplier SET_MULT` (a game minute about 625 s of wall); the world
        age T (time.snapshot), then `record.set admin monotony.t.[<type>].last <T - WINDOW_H + EDGE_LEAD_H>` for
        both types, then `record.set ... .n` to COUNT_A_EDGE / factor and COUNT_B_EDGE / factor; each reply read; both
        entries read back; the server's stats.all; the world age after them (age_after); then, in a `finally`, the
        clock restored (`time.multiplier` to the trueMult read first, else 1).
  EDGE  speed 1 until the world age passes the edge by POST_EDGE_M game minutes; the server's stats.all at the edge
        and at the end.
  PRUNE both entries read; one TKX.Unit50 eaten (the prune runs at an eat); both entries and Unit50's read again;
        speed 1 for AFTER_PRUNE_M more game minutes.
  RING  the ring's pages read and copied (always run; the server steps skipped on a dead bus).
  Z     the local readings first, then players, the clock and the intake's counters.

PREDICTIONS (graded in `verdicts`; a dead-bus phase is void, never falsified):
  FOOD        the server answers an id for each type after its spawn and none before.
  EATS        every eat queued with spawned "found" and landed; both entries exist after them. Falsifier: an eat that
              does not land on a live bus. (A stopped eat voids the later phases' readings.)
  SET         every record.set replies ok with `after` equal to the value sent (within 1e-9), and the entries read
              back equal. Falsifier: a reply not ok or a value off.
  PANIC       the writer's PANIC input reads at most 5 on every ring row from the sets to the end of EDGE (#3691).
              Falsifier: a row over 5 (then EDGE_STATS's BOREDOM half is void).
  EDGE_TARGET on every CLEAN ring row from EDGE_PRE_ROWS rows before the edge to the end of EDGE (a clean row reads a
              world age at least one game minute past SET's age_after and its previous row's past age_after, so the
              drain it reads ran after every write), the writer's BOREDOM target
              (the previous drain's input) equals the kernel's target at the previous row's world age from the row's
              entries (K.monotony.target off K.monotony.level and count, computed here) within TGT_TOL; and the
              target's change at the edge rows is no larger than the largest change on the window's other rows plus
              TGT_TOL. Falsifier: either off. Unmeasured: fewer than EDGE_PRE_ROWS clean rows precede the edge, the
              ring does not cover the edge, monotony.t holds a type besides the two after the eats or the sets, or
              neither key count was read (the prediction's premise, read as lua.global's key count).
  EDGE_STATS  the written UNHAPPINESS and BOREDOM change at the edge rows by no more than the largest change on the
              STAT_NEIGHBOURS clean rows either side plus STAT_STEP_TOL (0.1; the step a dropped type would make is
              8.6). Falsifier: a larger change. Unmeasured: as EDGE_TARGET's clean-row gate. The BOREDOM half is void
              when PANIC exceeded 5.
  PRUNE       before the Unit50 eat both entries exist (past the window, the under-one type is not yet dropped: the
              prune runs at an eat); after it TKX.Mono450's entry exists with its n and last unchanged and
              TKX.Mixed400's is gone. Falsifier: either off. Void: the Unit50 eat did not land.
  RING        every page read with errors 0.
  Z           no mod error line, admin not parked, and the server alive at the end.

DEVIATIONS from the run sheet and the amendments, stated before the run:
  PRE-RUN EDITS after the Opus review of f099c44a (made before any boot):
  1. The sets run on a nearly stopped clock (`time.multiplier SET_MULT` 0.001, the clock read first and restored in
     a `finally`, as x402b's C2 does), and EDGE_LEAD_H is 0.2 game hours, so `last` is T - 167.8 h, not the run
     sheet's 167.9 h: the four sets and their read-backs take 3-8 game minutes at speed 1, which against a 0.1 h
     lead put the writes inside the graded window's neighbour rows; the longer lead leaves about ten clean rows
     before the edge.
  2. The graded window (EDGE_TARGET and EDGE_STATS, the neighbour rows included) starts at the first ring row whose
     world age is at least one game minute past SET's age_after (its previous row past age_after too), and both
     grades read unmeasured unless at least EDGE_PRE_ROWS such clean rows precede the edge.
  3. EDGE_TARGET reads unmeasured when neither monotony.t key count (after the eats, after the sets) was read.
  4. PROBE_RX excludes time.multiplier, the driver's new command.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time; free memory read
before the boot, refused under 12 GB. 4. A session killed by the host is reported, and its measured phases are never
re-run to replace their figures (ruling H2-1).
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

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))
import release_pack                                             # noqa: E402

PROFILE = "x40-monotony"
PREFIX = "x406"
SESSION = ("Plan 11b Task 4 session S4f (x406): two monotony types back-dated by record.set to 167.9 game hours, one "
           "above and one under a portion at the 168 h edge, the minute ring through the edge and the prune at the next "
           "eat, on the staged 1.0.0 copy; one boot of " + PROFILE)
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert PROFILE == "x40-monotony" and _ME == "x406_monotony.py", f"PROFILE {PROFILE} does not match the driver {_ME}"
ARTIFACT = "monotony.json"
MANIFEST_NAME = "MANIFEST.json"
USER = "admin"
ADMIN = "client:admin"
SRV = "server"
NR = "NutritionRevamp"
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/plan11-x40/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_FILES = {"PZTestKit_Server.lua": LUA_DIR + "/server/PZTestKit_Server.lua",
                 "PZTestKit_Client.lua": LUA_DIR + "/client/PZTestKit_Client.lua"}
HARNESS_COMMITS = {"016dce05": "a ghost run restores its carrier's macros; time.snapshot reports the true multiplier",
                   "07c27dc4": "the store probe formats tiny magnitudes with tostring (Kahlua %g hangs below 1e-292)",
                   "2ffdbc81": "action.cancel stops a started action through ISTimedActionQueue.clear (H3)",
                   "513778e8": "action.cancel reads isStarted index-first (Task 1 fix 1)",
                   "ccb71a1b": "record.set (H6)"}
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": (
        "-- ---- Plan 11b Task 2 fix: a ghost run restores the carrier's macros ----",                    # 016dce05
        "g.rec.reconcile.baseline = NR.kernel.reconcile.baselineAfter(pre)",                             # 016dce05
        'TK.call(nut, "setCalories", pre.calories)',                                                     # 016dce05
        'if type(v) == "number" and v ~= 0 and math.abs(v) < 1e-280 then return tostring(v) end '
        '-- Kahlua %g hangs below ~1e-292',                                                              # 07c27dc4
        'TK.register("record.set", function(argv)'),                                                     # ccb71a1b
    "PZTestKit_Client.lua": (
        'TK.register("action.cancel", function()',                                                       # 2ffdbc81
        "if cur.isStarted ~= nil then out.started = cur:isStarted() == true end"),                       # 513778e8
}
KPATHS = {"window": f"{NR}.kernel.monotony.WINDOW_H", "half": f"{NR}.kernel.monotony.HALF_LIFE_H",
          "slope": f"{NR}.kernel.monotony.SLOPE", "cap": f"{NR}.kernel.monotony.CAP",
          "boredMax": f"{NR}.kernel.monotony.BORED_MAX", "staple": f"{NR}.kernel.monotony.STAPLE",
          "mealKcal": f"{NR}.kernel.monotony.MEAL_KCAL"}
TYPE_A, TYPE_B, TYPE_P = "TKX.Mono450", "TKX.Mixed400", "TKX.Unit50"
N_A, N_B = 6, 3
COUNT_A_EDGE = 3.0                   # TYPE_A's decayed count at the edge: level 4.3 x 2 = 8.6, kept by the prune
COUNT_B_EDGE = 0.8                   # TYPE_B's: level 0 on both sides, dropped by the prune
EDGE_LEAD_H = 0.2                    # `last` = T - (WINDOW_H - EDGE_LEAD_H): 167.8 h (pre-run edit; the sheet's 167.9 h)
SET_MULT = 0.001                     # time.multiplier during the sets: the writes land at one world age (pre-run edit)
POST_EDGE_M = 30.0
AFTER_PRUNE_M = 4.0
EDGE_PRE_ROWS = 4                    # the clean rows the grades need before the edge (about ten after a 0.2 h lead)
STAT_NEIGHBOURS = 5
TGT_TOL = 0.01
STAT_STEP_TOL = 0.1
SET_TOL = 1e-9
PANIC_MAX = 5.0


def entry_paths(t):
    return [f"monotony.t.[{t}].n", f"monotony.t.[{t}].last", f"monotony.t.[{t}].s"]


WIN = f"_G.{NR}.server.writer.input."
RING_RECORD = tuple(entry_paths(TYPE_A) + entry_paths(TYPE_B) + [f"monotony.t.[{TYPE_P}].n", "moodLast.u", "moodLast.b"])
RING_GLOBALS = (WIN + "panic", WIN + "unhappyTarget", WIN + "boredTarget", WIN + "bored",
                f"_G.{NR}.server.writer.stats.writes", f"_G.{NR}.server.intake.stats.eats",
                f"_G.{NR}.server.intake.stats.landed")
INTAKE_PATHS = (f"{NR}.server.intake.stats.eats", f"{NR}.server.intake.stats.cancels",
                f"{NR}.server.intake.stats.landed", f"{NR}.server.intake.stats.failures",
                f"{NR}.server.intake.stats.monotony", f"{NR}.server.intake.stats.monotonyHealed",
                f"{NR}.server.intake.stats.monotonyFailures")
# the clock
SPEED_FAST = 5
EAT_CAP_S = 25.0
SPAWN_WAIT_S = 2.5
# liveness and the wall budget
PING_TIMEOUT_S = 5
BUDGET_S = 840.0                     # from t0 (before the boot); RING, Z and the teardown fit 900 s
PHASE_EST_S = {"S0": 8.0, "H": 4.0, "FOOD": 12.0, "EATS": 80.0, "SET": 10.0, "EDGE": 35.0, "PRUNE": 20.0}
MIN_FREE_GB = 12.0
RESULT_WAIT_S = 30.0
POLL_S = 0.25
LOG_LIMIT = 400
ECHO_RX = re.compile(r"PZTK: ")
PROBE_RX = re.compile(r"\b(?:minute\.ring|lua\.(?:read|global)|time\.(?:snapshot|multiplier)|record\.set|item\.get|eat\.action|"
                      r"foodtimer\.set|additem|settimespeed|stats\.all)")
                                     # this driver's own probe and command names, excluded from every log grep
MOD_LIFE_RX = re.compile(r"minute: \w+ failed|players: hook failed|players: task|intake: |writer: |non-finite")
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")

META_NOTES = {
    "ring_note": "a ring row is sampled inside EveryOneMinute before the mod's queue drains that minute: row k reads "
                 "the state drain k-1 left, so its writer inputs are drain k-1's, taken at about row k-1's world age",
    "set_note": "record.set writes into the in-memory record only (H6); the entries reach the slot file at the next "
                "store step",
    "spawn_note": "the foods are spawned by RCON additem and confirmed by the server's item.get id (ruling T2-11)",
    "eat_note": "a networked eat ends in real time, 232 x 20 ms, whatever the clock (#3766)",
    "frame_note": "no frame window is graded in this session (no tick.ring), so no drop_windows apply"}
SUMMARY_KEYS = ("set", "edge", "edge_stats", "panic", "prune")

DEVIATIONS = (
    'Pre-run edit after the Opus review of f099c44a: the sets run on a nearly stopped clock (time.multiplier '
    "SET_MULT, restored in a finally) and EDGE_LEAD_H is 0.2 h, so last is T - 167.8 h, not the run sheet's 167.9 "
    'h.',
    "Pre-run edit: the graded edge window starts a game minute past SET's age_after (clean rows), and EDGE_TARGET "
    'and EDGE_STATS read unmeasured unless EDGE_PRE_ROWS clean rows precede the edge.',
    'Pre-run edit: EDGE_TARGET reads unmeasured when neither monotony.t key count was read.',
    'Pre-run edit: PROBE_RX excludes time.multiplier.',
)


PRED = {
    "FOOD": {"item.get after the spawn": f"an id for {TYPE_A}, {TYPE_B} and {TYPE_P}, none before",
             "falsifier": "an id missing on a live bus"},
    "EATS": {"every eat": "spawned found and landed; both entries exist after", "falsifier": "an eat not landed"},
    "SET": {"record.set": "ok, after equal to the value sent within 1e-9; the entries read back equal",
            "falsifier": "a reply not ok or a value off"},
    "PANIC": {"the writer's PANIC input": f"<= {PANIC_MAX} on every row from the sets to the end of EDGE (#3691)",
              "falsifier": "a row over it (EDGE_STATS's BOREDOM half then void)"},
    "EDGE_TARGET": {"writer boredTarget": "the kernel's target at the previous row's age within TGT_TOL; its change "
                                          "at the edge rows no larger than the window's largest other change + TGT_TOL",
                    "falsifier": "either off",
                    "unmeasured": "fewer than EDGE_PRE_ROWS clean rows (a game minute past the sets' age_after) before "
                                  "the edge, the ring not covering it, or the key-count premise unread or off"},
    "EDGE_STATS": {"UNHAPPINESS and BOREDOM": "the change at the edge rows <= the largest change on the neighbour "
                                              f"rows + {STAT_STEP_TOL}",
                   "falsifier": "a larger change", "void": "BOREDOM's half when PANIC exceeded 5"},
    "PRUNE": {"before the Unit50 eat": "both entries exist", "after": f"{TYPE_A} kept with n and last unchanged, "
                                                                    f"{TYPE_B} gone",
              "falsifier": "either off", "void": "the Unit50 eat did not land"},
    "RING": {"pages": "all read, errors 0"},
    "Z": {"mod_error": "none", "admin_lua_error": False, "players": "answers a list (the server alive at the end)"},
}

# session state (set in main)
prof = rec_fx = run_id = run_dir = path = tl = None
t0 = time.time()
server, clients, started = None, {}, []
cur_phase = {"name": "pre"}
bus = {"dead": None}
out = {"phases": {}, "verdicts": {}, "summaries": {}, "notes": [], "steps": [], "world_changes": {"left_in_place": []}}
copied = []


class BusDead(Exception):
    """The server bus stopped answering; the phase ends and every later server step is skipped."""


class Budget(Exception):
    """The wall budget passed, or admin parked in the debugger, inside a phase's poll."""


class StopEats(Exception):
    """An eat.action reply's spawned was not "found": the session's eats stop (ruling T2-11)."""


# ---------------------------------------------------------------- plumbing (x391h's)
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


STALL_RX = re.compile(r"^(?:TimeoutError|RuntimeError)\b")


def stalled(v):
    return isinstance(v, dict) and isinstance(v.get("error"), str) and STALL_RX.match(v["error"]) is not None


def mark_dead(tag):
    if not bus["dead"]:
        bus["dead"] = tag
        out["abort"] = f"server bus dead after {tag}"
        note(out["abort"])
        if tl is not None:
            tl.mark("error", detail=out["abort"][:200])


def ping(tag):
    """The bus liveness probe: True only when the server answers pong inside PING_TIMEOUT_S; no pong sets it dead."""
    if bus["dead"]:
        return False
    r = step(tag, SRV, "ping", timeout=PING_TIMEOUT_S, liveness=False)
    if r.get("ack") == "pong":
        return True
    mark_dead(tag)
    return False


def step(name, side, cmd, args="", timeout=30, liveness=True, log=True):
    t_before, e_before = wall(), time.time()
    if side == SRV and bus["dead"]:
        row = {"step": name, "side": side, "cmd": cmd, "args": args, "phase": cur_phase["name"],
               "wall_before": t_before, "wall_after": t_before, "epoch_ms_before": int(e_before * 1000),
               "epoch_ms_after": int(e_before * 1000), "took": 0.0, "skipped": True,
               "ack": {"error": f"skipped: server bus dead after {bus['dead']}"}}
        if log:
            out["steps"].append(row)
        return row
    try:
        v = ask(node(side), cmd, args, timeout=timeout)
    except Exception as e:                     # noqa: BLE001 - an unknown side is a recorded fault
        v = {"error": f"{type(e).__name__}: {e}"}
    t_after = wall()
    row = {"step": name, "side": side, "cmd": cmd, "args": args, "phase": cur_phase["name"],
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": int(e_before * 1000),
           "epoch_ms_after": int(time.time() * 1000), "took": round(t_after - t_before, 3), "ack": v}
    if not isinstance(v, dict):
        row["ack_shape"] = type(v).__name__
    if log or stalled(v):
        out["steps"].append(row)
    if side == SRV and liveness and stalled(v):
        alive = ping(f"{name}_liveness")
        row["liveness_pong"] = alive
        if not alive:
            raise BusDead(out.get("abort") or f"server bus dead after {name}")
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def keep(r):
    a = dict(ack(r))
    a["wall"] = r["wall_before"]
    a["wall_after"] = r["wall_after"]
    a["side"] = a.get("side", r["side"])
    if not isinstance(r.get("ack"), dict):
        a["raw"] = r.get("ack")
    return a


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def parked():
    c = clients.get(USER) if isinstance(clients, dict) else None
    return c is not None and "lua_error" in getattr(c, "seen", {})


def check():
    """Every poll's guard: the wall budget and the debugger park."""
    if wall() > BUDGET_S:
        raise Budget(f"wall {wall()} s past the budget {BUDGET_S} s")
    if parked():
        raise Budget("admin parked in the debugger")


def lread(side, root, paths, tag, log=True):
    return keep(step(tag, side, "lua.read", " ".join([root] + list(paths)), log=log))


def vals(a):
    return a.get("values") or {}


def snap(tag, log=True):
    a = keep(step(tag, SRV, "time.snapshot", log=log))
    return {k: a.get(k) for k in ("worldAge", "hour", "minutes", "mult", "trueMult", "wall", "wall_after")}


def age(tag="age"):
    return num(snap(tag, log=False).get("worldAge"))


def wait_doc(name, after):
    if bus["dead"]:
        note(f"result {name}: skipped, server bus dead after {bus['dead']}")
        return None
    try:
        return server.bus.wait_result(name, timeout=RESULT_WAIT_S, after=after)
    except Exception as e:                     # noqa: BLE001
        note(f"result {name}: {type(e).__name__}: {e}")
        return None


def grade(name, verdict, observed, falsifier, extra=None):
    row = {"phase": name, "predicted": PRED.get(name), "falsifier": falsifier, "observed": observed,
           "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][name] = row
    if tl is not None:
        tl.mark("verdict", name=name, verdict=verdict)


def run_phase(name, fn):
    cur_phase["name"] = name
    out["phase_walls"][name] = {"start": wall()}
    was_dead = bus["dead"]
    try:
        fn()
    except BusDead as e:
        out["phase_walls"][name]["bus_dead"] = str(e)
        note(f"phase {name} ended: {e}")
    except Budget as e:
        out["phase_walls"][name]["budget_stop"] = str(e)
        out["budget_stop"] = {"phase": name, "why": str(e), "wall": wall()}
        note(f"phase {name} stopped: {e}")
    except StopEats as e:
        out["phase_walls"][name]["stop_eats"] = str(e)
        note(f"phase {name} stopped: {e}")
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        if tl is not None:
            tl.mark("error", failed_phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    if bus["dead"] and not was_dead and not out["phase_walls"][name].get("bus_dead"):
        out["phase_walls"][name]["bus_dead"] = f"server bus dead after {bus['dead']}"
    out["phase_walls"][name]["end"] = wall()
    persist()


def phase_dead(name):
    return bool(g(out, "phase_walls", name, "bus_dead"))


def rcon(cmd, tag):
    t_before, e_before = wall(), time.time()
    if bus["dead"]:
        row = {"step": tag, "side": SRV, "cmd": "rcon", "args": cmd, "phase": cur_phase["name"],
               "wall_before": t_before, "wall_after": t_before, "skipped": True,
               "ack": {"ok": False, "reply": f"skipped: server bus dead after {bus['dead']}"}}
        out["steps"].append(row)
        return dict(row["ack"], skipped=True)
    try:
        ok, rep = server.rcon(cmd)
    except Exception as e:                     # noqa: BLE001
        ok, rep = False, f"{type(e).__name__}: {e}"
    row = {"step": tag, "side": SRV, "cmd": "rcon", "args": cmd, "phase": cur_phase["name"], "wall_before": t_before,
           "wall_after": wall(), "epoch_ms_before": int(e_before * 1000), "epoch_ms_after": int(time.time() * 1000),
           "ack": {"ok": ok, "reply": str(rep)[:300]}}
    out["steps"].append(row)
    if tl is not None:
        tl.mark("rcon", cmd=cmd, ok=ok)
    return row["ack"]


def speed(mode, tag):
    """fast: settimespeed 5; one: settimespeed 1 (which also resets a time.multiplier). The clock read after it."""
    rcon(f"settimespeed {SPEED_FAST if mode == 'fast' else 1}", tag)
    s = snap(tag + "_t")
    out.setdefault("speeds", []).append({"mode": mode, "age": s.get("worldAge"), "mult": s.get("mult"),
                                         "trueMult": s.get("trueMult"), "wall": s.get("wall")})
    return s


def wait_age(target, tag):
    while True:
        check()
        a = age(tag)
        if a is not None and a >= target:
            return a
        if bus["dead"]:
            raise BusDead(out.get("abort") or "server bus dead")
        time.sleep(POLL_S)


def item_id(full_type, tag):
    """The server's copy of admin's first item of the type (item.get): its id and state, or no id."""
    a = keep(step(tag, SRV, "item.get", f"{USER} {full_type}"))
    return {k: a.get(k) for k in ("id", "fullType", "hungChange", "hungerChange", "baseHunger", "calories", "uses",
                                  "age", "error", "raw", "wall")}


def spawn(full_type, n, tag):
    """RCON additem confirmed by the server's item.get id (ruling T2-11); a leftover before the spawn voids it."""
    row = {"type": full_type, "n": n}
    row["before"] = item_id(full_type, tag + "_id0")
    row["additem"] = rcon(f'additem "{USER}" "{full_type}" {int(n)}', tag + "_additem")
    time.sleep(SPAWN_WAIT_S)
    row["after"] = item_id(full_type, tag + "_id1")
    row["leftover_before"] = row["before"].get("id") is not None
    row["confirmed"] = row["after"].get("id") is not None and not row["leftover_before"]
    if row["confirmed"]:
        out["world_changes"]["left_in_place"].append(f"RCON additem {full_type} x{n}")
    else:
        note(f"spawn {full_type}: not confirmed ({'a leftover before the spawn' if row['leftover_before'] else 'no id after'})")
    return row


def intake(tag, log=False):
    a = lread(SRV, "_G", INTAKE_PATHS, tag, log=log)
    v = vals(a)
    return {k.rsplit(".", 1)[-1]: num(v.get(k)) for k in INTAKE_PATHS} | {"wall": a.get("wall")}


def eat_queue(full_type, tag):
    """foodtimer 0, then eat.action <type> 1 on admin's client; a `spawned` other than "found" stops the eats."""
    keep(step(tag + "_foodtimer", SRV, "foodtimer.set", f"{USER} 0"))
    q = keep(step(tag + "_eat", ADMIN, "eat.action", f"{full_type} 1"))
    row = {k: q.get(k) for k in ("queued", "fraction", "spawned", "itemId", "validStart", "maxTime", "error", "raw",
                                 "wall")}
    row["tag"] = tag
    out.setdefault("eats", []).append(row)
    if q.get("spawned") != "found":
        out["stop_reason"] = f"{tag}: eat.action spawned {q.get('spawned')!r}, not 'found' (ruling T2-11)"
        raise StopEats(out["stop_reason"])
    return row


# ---------------------------------------------------------------- the monotony verbs
def k_const(name):
    return g(out, "phases", "S0", "k", name)


def entries(tag, log=True):
    """Both types' entries and Unit50's n from the record, one lua.read: {type: {n, last, s, present}}."""
    paths = entry_paths(TYPE_A) + entry_paths(TYPE_B) + [f"monotony.t.[{TYPE_P}].n"]
    a = lread(SRV, f"record:{USER}", paths, tag, log=log)
    v, miss = vals(a), a.get("missing") or {}
    E = {}
    for t in (TYPE_A, TYPE_B):
        n_p, l_p, s_p = entry_paths(t)
        E[t] = {"n": num(v.get(n_p)), "last": num(v.get(l_p)), "s": v.get(s_p),
                "present": num(v.get(n_p)) is not None, "missing": miss.get(n_p)}
    E[TYPE_P] = {"n": num(v.get(f"monotony.t.[{TYPE_P}].n")), "present": num(v.get(f"monotony.t.[{TYPE_P}].n")) is not None}
    E["wall"] = a.get("wall")
    return E


def tkeys(tag):
    """monotony.t's key count (lua.global answers a table by its key count)."""
    a = keep(step(tag, SRV, "lua.global", f"{NR}.server.store.records.{USER}.monotony.t"))
    return num(a.get("keyCount"))


def mood(tag):
    a = keep(step(tag, SRV, "stats.all", USER))
    st = a.get("stats") or {}
    pick = {}
    for k, alt in (("PANIC", "Panic"), ("UNHAPPINESS", "Unhappiness"), ("BOREDOM", "Boredom"), ("STRESS", "Stress")):
        pick[k] = num(st.get(k, st.get(alt)))
    pick["worldAge"] = num(a.get("worldAge"))
    pick["wall"] = a.get("wall")
    return pick


def eat_landed(full_type, label):
    """foodtimer 0 and eat.action (eat_queue: a `spawned` other than "found" stops the eats), then intake.stats.landed
    polled until it rises (EAT_CAP_S)."""
    E = {"food": full_type, "label": label}
    E["before"] = intake(label + "_in0")
    E["queued"] = eat_queue(full_type, label)
    E["landed"] = False
    end = time.time() + EAT_CAP_S
    while time.time() < end:
        check()
        a = intake(label + "_poll")
        if a.get("landed") is not None and E["before"].get("landed") is not None and a["landed"] > E["before"]["landed"]:
            E["landed"], E["after"] = True, a
            E["landed_age"] = age(label + "_landed_a")
            break
        if bus["dead"]:
            raise BusDead(out.get("abort") or "server bus dead")
        time.sleep(POLL_S)
    if not E["landed"]:
        note(f"{label}: landed did not rise within {EAT_CAP_S} s")
    out.setdefault("eat_rows", []).append(E)
    return E


def count_at(n, last, a, window, half):
    """K.monotony.count: n decayed to age a; past the window K.monotony.faded (the decayed count above one portion,
    else 0)."""
    if n is None or last is None or a is None:
        return None
    dt = a - last
    c = n * math.exp(-0.6931471805599453 * dt / half)
    if dt > window and c <= 1:
        return 0.0
    return c


def target_at(ents, a, k):
    """K.monotony.target's BOREDOM half at age a over the entries {type: (n, last, s)}: the largest level, under
    BORED_MAX; a level is f x min(CAP, SLOPE x max(0, count - 1)), f STAPLE for a staple."""
    u = 0.0
    for n, last, s in ents:
        c = count_at(n, last, a, k["window"], k["half"])
        if c is None:
            return None
        f = k["staple"] if s is True else 1.0
        u = max(u, f * min(k["cap"], k["slope"] * max(0.0, c - 1.0)))
    return min(k["boredMax"], u)


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    P["ping"] = ping("S0_ping")
    P["players"] = keep(step("S0_players", SRV, "players"))
    P["one"] = speed("one", "S0_one")
    P["kernel"] = lread(SRV, "_G", list(KPATHS.values()), "S0_kernel")
    P["k"] = {k: num(vals(P["kernel"]).get(p)) for k, p in KPATHS.items()}
    P["record"] = lread(SRV, f"record:{USER}", ["firstSeen", "resets", "body.sex"], "S0_record")
    P["entries"] = entries("S0_entries")
    P["mood"] = mood("S0_mood")
    P["intake"] = intake("S0_intake", log=True)


def phase_H():
    P = out["phases"]["H"] = {}
    paths = list(RING_RECORD) + list(RING_GLOBALS)
    P["paths"] = paths
    P["start"] = keep(step("H_ring_start", SRV, "minute.ring", " ".join([USER, "start"] + paths)))
    P["snap"] = snap("H_snap")


def phase_FOOD():
    P = out["phases"]["FOOD"] = {}
    P["a"] = spawn(TYPE_A, N_A, "FOOD_a")
    P["b"] = spawn(TYPE_B, N_B, "FOOD_b")
    P["p"] = spawn(TYPE_P, 1, "FOOD_p")


def phase_EATS():
    P = out["phases"]["EATS"] = {"eats": []}
    F = out["phases"].get("FOOD") or {}
    if g(F, "a", "confirmed") is not True or g(F, "b", "confirmed") is not True:
        note("EATS: a food spawn was not confirmed; no eat")
        return
    for i in range(N_A):
        P["eats"].append(eat_landed(TYPE_A, f"EATS_a{i}"))
    for i in range(N_B):
        P["eats"].append(eat_landed(TYPE_B, f"EATS_b{i}"))
    P["entries"] = entries("EATS_entries")
    P["t_keys"] = tkeys("EATS_keys")
    P["mood"] = mood("EATS_mood")


def phase_SET():
    P = out["phases"]["SET"] = {"sets": []}
    E0 = g(out, "phases", "EATS", "entries") or {}
    if not (g(E0, TYPE_A, "present") and g(E0, TYPE_B, "present")):
        note("SET: an entry is absent after the eats; no set (the edge is unmeasured)")
        return
    k = g(out, "phases", "S0", "k") or {}
    window, half = k.get("window"), k.get("half")
    if window is None or half is None:
        note("SET: the kernel's WINDOW_H or HALF_LIFE_H not read; no set")
        return
    factor = 2.0 ** (-window / half)
    P["clock0"] = snap("SET_clock0")
    P["slowed"] = False
    try:
        # pre-run edit after the review of f099c44a: the writes land on a nearly stopped clock (x402b's C2 form)
        P["slow"] = keep(step("SET_slow", SRV, "time.multiplier", str(SET_MULT)))
        P["slowed"] = True
        T = num(snap("SET_T").get("worldAge"))
        if T is None:
            note("SET: no world age; no set")
            return
        last = T - window + EDGE_LEAD_H
        P.update({"T": T, "last": last, "edge_age": last + window, "factor": factor,
                  "n_a": COUNT_A_EDGE / factor, "n_b": COUNT_B_EDGE / factor})
        for t, key in ((TYPE_A, "last"), (TYPE_B, "last"), (TYPE_A, "n"), (TYPE_B, "n")):
            val = last if key == "last" else (P["n_a"] if t == TYPE_A else P["n_b"])
            r = keep(step(f"SET_{key}_{t}", SRV, "record.set", f"{USER} monotony.t.[{t}].{key} {val!r}"))
            P["sets"].append({"type": t, "key": key, "sent": val,
                              **{x: r.get(x) for x in ("ok", "key", "keyType", "before", "after", "afterType",
                                                       "error")}})
        P["entries"] = entries("SET_entries")
        P["t_keys"] = tkeys("SET_keys")
        P["mood"] = mood("SET_mood")
        P["age_after"] = age("SET_a1")
    finally:
        if P["slowed"] and not bus["dead"]:
            tm = num(P["clock0"].get("trueMult"))
            P["restore_to"] = tm if tm is not None and tm > 0 else 1
            P["restore"] = keep(step("SET_restore", SRV, "time.multiplier", f"{P['restore_to']:g}"))
            P["slowed"] = False
            if tl is not None:
                tl.mark("clock_restored")


def phase_EDGE():
    P = out["phases"]["EDGE"] = {}
    edge = num(g(out, "phases", "SET", "edge_age"))
    if edge is None:
        note("EDGE: no edge age (SET did not run); skipped")
        return
    P["one"] = speed("one", "EDGE_one")
    P["at_edge"] = wait_age(edge, "EDGE_wait0")
    P["mood_edge"] = mood("EDGE_mood0")
    P["end_age"] = wait_age(edge + POST_EDGE_M / 60.0, "EDGE_wait1")
    P["mood_end"] = mood("EDGE_mood1")


def phase_PRUNE():
    P = out["phases"]["PRUNE"] = {}
    P["before"] = entries("PRUNE_e0")
    if g(out, "phases", "FOOD", "p", "confirmed") is not True:
        note("PRUNE: the Unit50 spawn was not confirmed; no eat (void)")
        return
    P["eat"] = eat_landed(TYPE_P, "PRUNE_eat")
    P["after"] = entries("PRUNE_e1")
    a = num(P["eat"].get("landed_age")) or age("PRUNE_a")
    if a is not None:
        wait_age(a + AFTER_PRUNE_M / 60.0, "PRUNE_wait")
    P["after_wait"] = entries("PRUNE_e2")
    P["mood"] = mood("PRUNE_mood")


def phase_RING():
    P = out["phases"]["RING"] = {"pages": []}
    frm = None
    for _ in range(8):
        after = time.time() - 1.0
        r = keep(step("RING_read", SRV, "minute.ring", f"{USER} read" + ("" if frm is None else f" {frm}"),
                      timeout=60))
        pg = {"reply": {k: r.get(k) for k in ("ok", "from", "rows", "skipped", "next", "more", "recorded",
                                              "overwritten", "errors", "lastError", "gErrors", "result", "error")}}
        name = r.get("result")
        if isinstance(name, str) and name:
            doc = wait_doc(name, after)
            src = os.path.join(server.bus.results_dir, name + ".json")
            if doc is not None and os.path.isfile(src):
                shutil.copyfile(src, os.path.join(run_dir, name + ".json"))
                copied.append(name + ".json")
                pg["file"] = name + ".json"
                pg["doc_rows"] = len(doc.get("rows_list") or [])
        P["pages"].append(pg)
        if not r.get("ok") or not r.get("more") or r.get("next") is None:
            break
        frm = r.get("next")
    P["stop"] = keep(step("RING_stop", SRV, "minute.ring", f"{USER} stop"))


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["bus_dead"] = bus["dead"]
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)
                                   and not PROBE_RX.search(e)][:20]
    P["admin_parked"] = parked()
    P["mem"] = mem("Z")
    P["players"] = keep(step("Z_players", SRV, "players"))
    P["time"] = snap("Z_time")
    P["intake"] = intake("Z_intake", log=True)


ORDER = (("S0", phase_S0), ("H", phase_H), ("FOOD", phase_FOOD), ("EATS", phase_EATS), ("SET", phase_SET),
         ("EDGE", phase_EDGE), ("PRUNE", phase_PRUNE))
EAT_PHASES = ("EATS", "SET", "EDGE", "PRUNE")   # every later phase rests on the eats (ruling T2-11's stop)


def body():
    out["budget"] = {"BUDGET_S": BUDGET_S, "checks": [], "estimate_total_s": sum(PHASE_EST_S.values())}
    for name, fn in ORDER:
        if bus["dead"] or out.get("budget_stop"):
            break                                  # out["abort"] or out["budget_stop"] names why; RING and Z still run
        if out.get("stop_reason") and name in EAT_PHASES:
            out["phase_walls"][name] = {"skipped": out["stop_reason"]}
            continue
        est = PHASE_EST_S.get(name, 0.0)
        out["budget"]["checks"].append({"phase": name, "wall": wall(), "estimate": est})
        if wall() + est > BUDGET_S:
            out["abort"] = out.get("abort") or f"wall budget: {name} (estimate {est} s) would end past {BUDGET_S} s"
            note(f"wall budget: {name} (estimate {est} s) would end past {BUDGET_S} s at wall {wall()} s")
            break
        run_phase(name, fn)
        if parked():
            out["abort"] = f"admin parked in the debugger after phase {name}"
            break
    for name, fn in (("RING", phase_RING), ("Z", phase_Z)):
        run_phase(name, fn)


def read_logs(every):
    L = out["logs"] = {"patterns": {"life": MOD_LIFE_RX.pattern, "log": LOG_RX.pattern, "echo_excluded": ECHO_RX.pattern,
                                    "probe_excluded": PROBE_RX.pattern}, "limits": {"log": LOG_LIMIT}, "clients": {}}
    if server is not None:
        life, life_echo = grep_noecho(server.log_path, MOD_LIFE_RX, LOG_LIMIT)
        raw, echoed = grep_noecho(server.log_path, LOG_RX, LOG_LIMIT)
        L["server"] = {"life_lines": life, "life_echo_excluded": life_echo, "lines": raw, "echo_lines_excluded": echoed}
    for c in every:
        u = getattr(c, "username", "?")
        lines, ech = grep_noecho(c.console, LOG_RX, 60)
        L["clients"].setdefault(u, []).append({"console": os.path.relpath(c.console, run_dir), "lines": lines,
                                               "echo_lines_excluded": ech})


# ---------------------------------------------------------------- grading (pure: reads `out` and the ring files)
def load_ring(rdir):
    rows = []
    for pg in g(out, "phases", "RING", "pages") or []:
        f = pg.get("file")
        if not f:
            continue
        try:
            with open(os.path.join(rdir, f), encoding="utf-8") as fh:
                rows.extend((json.load(fh) or {}).get("rows_list") or [])
        except (OSError, ValueError) as e:
            note(f"ring page {f}: {type(e).__name__}: {e}")
    seen, uniq = set(), []
    for r in sorted((r for r in rows if isinstance(r, dict) and num(r.get("s")) is not None), key=lambda r: r["s"]):
        if r["s"] not in seen:
            seen.add(r["s"])
            uniq.append(r)
    return uniq


def row_ents(r):
    ents = []
    for t in (TYPE_A, TYPE_B):
        n_p, l_p, s_p = entry_paths(t)
        if num(r.get(n_p)) is not None:
            ents.append((num(r.get(n_p)), num(r.get(l_p)), r.get(s_p) is True))
    return ents


def biggest_change(xs):
    ds = [abs(b - a) for a, b in zip(xs, xs[1:]) if a is not None and b is not None]
    return max(ds) if ds else None


def grade_all():
    S = out["summaries"]
    ph = out["phases"]
    dead = bus["dead"]
    k = g(ph, "S0", "k") or {}
    S["kernel"] = k
    rows = load_ring(run_dir) if run_dir else []
    S["ring_rows"] = len(rows)
    # RING
    pages = g(ph, "RING", "pages") or []
    errs = [num(g(p, "reply", "errors")) for p in pages]
    if not pages:
        grade("RING", "void" if dead else "unmeasured", {"pages": 0}, "no page read")
    else:
        ok = all(p.get("file") for p in pages) and all((e or 0) == 0 for e in errs)
        grade("RING", "as_predicted" if ok else ("void" if dead else "falsified"),
              {"pages": len(pages), "files": [p.get("file") for p in pages], "errors": errs}, "a page unread or errors")
    # FOOD
    F = ph.get("FOOD") or {}
    if not F:
        grade("FOOD", "void" if dead else "unmeasured", None, "phase not run")
    else:
        conf = {x: g(F, x, "confirmed") for x in ("a", "b", "p")}
        grade("FOOD", "as_predicted" if all(v is True for v in conf.values()) else
              ("void" if phase_dead("FOOD") else "falsified"), conf, PRED["FOOD"]["falsifier"])
    # EATS
    E = ph.get("EATS") or {}
    eats = E.get("eats") or []
    landed = [e.get("landed") for e in eats]
    obs = {"n": len(eats), "landed": landed, "spawned": [g(e, "queued", "spawned") for e in eats],
           "entries": E.get("entries"), "stop_reason": out.get("stop_reason")}
    S["eats"] = obs
    if out.get("stop_reason") or phase_dead("EATS"):
        grade("EATS", "void", obs, "an eat stopped (spawned not found) or the bus died")
    elif len(eats) < N_A + N_B:
        grade("EATS", "void" if dead else "unmeasured", obs, "not every eat ran")
    else:
        ok = all(x is True for x in landed) and g(E, "entries", TYPE_A, "present") and g(E, "entries", TYPE_B, "present")
        grade("EATS", "as_predicted" if ok else "falsified", obs, PRED["EATS"]["falsifier"])
    # SET
    St = ph.get("SET") or {}
    sets = St.get("sets") or []
    bad = [s for s in sets if s.get("ok") is not True or num(s.get("after")) is None
           or abs(num(s.get("after")) - s["sent"]) > SET_TOL * max(1.0, abs(s["sent"]))]
    back = St.get("entries") or {}
    back_bad = []
    if St.get("n_a") is not None:
        for t, n_v in ((TYPE_A, St["n_a"]), (TYPE_B, St["n_b"])):
            for key, v in (("n", n_v), ("last", St["last"])):
                got = num(g(back, t, key))
                if got is None or abs(got - v) > SET_TOL * max(1.0, abs(v)):
                    back_bad.append({"type": t, "key": key, "sent": v, "read": got})
    S["set"] = {k2: St.get(k2) for k2 in ("T", "last", "edge_age", "factor", "n_a", "n_b")} | {
        "sets": sets, "bad": bad, "read_back_bad": back_bad}
    if len(sets) < 4:
        grade("SET", "void" if (dead or phase_dead("SET") or out.get("stop_reason")) else "unmeasured", S["set"],
              "not every set ran")
    else:
        grade("SET", "as_predicted" if not bad and not back_bad else "falsified", S["set"], PRED["SET"]["falsifier"])
    # the edge window
    edge = num(St.get("edge_age"))
    end_age = num(g(ph, "EDGE", "end_age"))
    t_set = num(St.get("T"))
    win = [r for r in rows if edge is not None and t_set is not None and num(r.get("age")) is not None
           and r["age"] > t_set and (end_age is None or r["age"] <= end_age + 1.0 / 60.0)]
    # PANIC
    pan = [num(r.get(WIN + "panic")) for r in win]
    pan_n = [p for p in pan if p is not None]
    over = [p for p in pan_n if p > PANIC_MAX]
    S["panic"] = {"rows": len(win), "read": len(pan_n), "max": max(pan_n) if pan_n else None, "over": len(over)}
    if not pan_n:
        grade("PANIC", "void" if (dead or out.get("stop_reason")) else "unmeasured", S["panic"],
              PRED["PANIC"]["falsifier"], {"stop_reason": out.get("stop_reason")})
    else:
        grade("PANIC", "as_predicted" if not over else "falsified", S["panic"], PRED["PANIC"]["falsifier"])
    # EDGE_TARGET
    need = ("window", "half", "slope", "cap", "boredMax", "staple")
    by_s = {r["s"]: r for r in rows}
    # pre-run edit after the review of f099c44a: a clean row reads an age at least a game minute past SET's age_after
    # and its previous row (the drain it reads) one past age_after, so no write lands inside the graded window
    age_after = num(St.get("age_after"))
    trows = []
    for r in win:
        prev = by_s.get(r["s"] - 1)
        if prev is None or num(prev.get("age")) is None:
            continue
        if age_after is None or r["age"] < age_after + 1.0 / 60.0 or prev["age"] <= age_after:
            continue
        pred = target_at(row_ents(r), prev["age"], k) if all(k.get(x) is not None for x in need) else None
        got = num(r.get(WIN + "boredTarget"))
        trows.append({"s": r["s"], "age": r.get("age"), "drain_age": prev["age"], "pred": pred, "got": got,
                      "past_edge": prev["age"] > edge if edge is not None else None,
                      "UNHAPPINESS": num(r.get("UNHAPPINESS")), "BOREDOM": num(r.get("BOREDOM")),
                      "unhappyTarget": num(r.get(WIN + "unhappyTarget"))})
    edge_i = next((i for i, t in enumerate(trows) if t["past_edge"]), None)
    S["edge"] = {"edge_age": edge, "age_after": age_after, "rows": len(trows), "edge_index": edge_i,
                 "clean_rows_before_edge": edge_i, "rows_list": trows[max(0, (edge_i or 0) - 8):(edge_i or 0) + 12]}
    keys = [num(St.get("t_keys")), num(g(ph, "EATS", "t_keys"))]
    S["edge"]["t_keys"] = keys
    covered = edge_i is not None and edge_i >= EDGE_PRE_ROWS
    if not covered:
        grade("EDGE_TARGET", "void" if (dead or phase_dead("EDGE") or out.get("stop_reason")) else "unmeasured",
              S["edge"], PRED["EDGE_TARGET"]["unmeasured"], {"stop_reason": out.get("stop_reason")})
    elif all(x is None for x in keys):
        grade("EDGE_TARGET", "unmeasured", S["edge"], "neither monotony.t key count read (the premise)")
    elif any(x is not None and x != 2 for x in keys):
        grade("EDGE_TARGET", "unmeasured", S["edge"], "monotony.t holds a type besides the two (the premise)")
    else:
        lo = max(0, edge_i - EDGE_PRE_ROWS)
        tw = trows[lo:]
        off = [t for t in tw if t["pred"] is None or t["got"] is None or abs(t["pred"] - t["got"]) > TGT_TOL]
        edge_rows = {edge_i, edge_i + 1}
        d_edge = [abs(tw_b["got"] - tw_a["got"]) for j, (tw_a, tw_b) in enumerate(zip(trows[lo:], trows[lo + 1:]))
                  if (lo + j + 1) in edge_rows and tw_a["got"] is not None and tw_b["got"] is not None]
        d_other = [abs(tw_b["got"] - tw_a["got"]) for j, (tw_a, tw_b) in enumerate(zip(trows[lo:], trows[lo + 1:]))
                   if (lo + j + 1) not in edge_rows and tw_a["got"] is not None and tw_b["got"] is not None]
        step_ok = bool(d_edge) and max(d_edge) <= (max(d_other) if d_other else 0.0) + TGT_TOL
        S["edge"].update({"off": off[:10], "off_n": len(off), "d_edge": d_edge,
                          "d_other_max": max(d_other) if d_other else None, "step_ok": step_ok})
        grade("EDGE_TARGET", "as_predicted" if (not off and step_ok) else "falsified", S["edge"],
              PRED["EDGE_TARGET"]["falsifier"])
    # EDGE_STATS
    if not covered:
        S["edge_stats"] = None
        grade("EDGE_STATS", "void" if (dead or phase_dead("EDGE") or out.get("stop_reason")) else "unmeasured", None,
              "fewer than EDGE_PRE_ROWS clean rows before the edge, or the ring does not cover it",
              {"stop_reason": out.get("stop_reason")})
    else:
        res = {}
        for stat in ("UNHAPPINESS", "BOREDOM"):
            seq = [t[stat] for t in trows]
            d_edge = [abs(seq[i] - seq[i - 1]) for i in (edge_i, edge_i + 1)
                      if 0 < i < len(seq) and seq[i] is not None and seq[i - 1] is not None]
            nb = [i for i in range(max(1, edge_i - STAT_NEIGHBOURS), min(len(seq), edge_i + 2 + STAT_NEIGHBOURS))
                  if i not in (edge_i, edge_i + 1)]
            d_nb = [abs(seq[i] - seq[i - 1]) for i in nb if seq[i] is not None and seq[i - 1] is not None]
            res[stat] = {"d_edge": d_edge, "d_neighbours_max": max(d_nb) if d_nb else None,
                         "ok": bool(d_edge) and max(d_edge) <= (max(d_nb) if d_nb else 0.0) + STAT_STEP_TOL}
        res["boredom_void"] = bool(over)
        S["edge_stats"] = res
        oks = [res["UNHAPPINESS"]["ok"]] + ([] if over else [res["BOREDOM"]["ok"]])
        grade("EDGE_STATS", "as_predicted" if all(oks) else "falsified", res, PRED["EDGE_STATS"]["falsifier"])
    # PRUNE
    Pr = ph.get("PRUNE") or {}
    b4, af = Pr.get("before") or {}, Pr.get("after") or {}
    obs = {"before": b4, "after": af, "after_wait": Pr.get("after_wait"), "landed": g(Pr, "eat", "landed")}
    S["prune"] = obs
    if not Pr or g(Pr, "eat", "landed") is not True:
        grade("PRUNE", "void" if (Pr or dead or out.get("stop_reason")) else "unmeasured", obs, PRED["PRUNE"]["void"])
    else:
        ok = (g(b4, TYPE_A, "present") is True and g(b4, TYPE_B, "present") is True
              and g(af, TYPE_A, "present") is True and g(af, TYPE_B, "present") is False
              and num(g(af, TYPE_A, "n")) == num(g(b4, TYPE_A, "n"))
              and num(g(af, TYPE_A, "last")) == num(g(b4, TYPE_A, "last")))
        grade("PRUNE", "as_predicted" if ok else "falsified", obs, PRED["PRUNE"]["falsifier"])
    # Z
    Z = ph.get("Z") or {}
    pl = g(Z, "players", "raw")
    alive = isinstance(pl, list) and len(pl) > 0
    obs = {"server_mod_error_lines": Z.get("server_mod_error_lines") or [],
           "admin_lua_error": out.get("admin_lua_error"), "players": pl, "server_alive": alive,
           "bus_dead": Z.get("bus_dead")}
    ok = bool(Z) and not obs["server_mod_error_lines"] and not obs["admin_lua_error"] and alive
    grade("Z", "as_predicted" if ok else ("unmeasured" if not Z else "falsified"), obs,
          "a mod error line, admin parked, or no players answer")


# ---------------------------------------------------------------- the pre-boot gates
def manifest_gate():
    """The staged copy against release_pack's manifest of mod/NutritionRevamp at HEAD (the tree clean)."""
    M = {"head": git_say("rev-parse", "HEAD"), "head_short": git_say("rev-parse", "--short", "HEAD"),
         "mod_commit": git_say("log", "-1", "--format=%h", "--", MOD_DIR), "mod_dirty": git_dirty(MOD_DIR)[0],
         "staged_manifest": f"{STAGE_ROOT}/{MANIFEST_NAME}", "staged_mod": STAGE_MOD}
    try:
        mpath = os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME)
        M["staged_manifest_sha256"] = sha256_file(mpath)
        with open(mpath, encoding="utf-8") as fh:
            staged = json.load(fh)
        head = release_pack.manifest(os.path.join(REPO, MOD_DIR))
        booted = release_pack.manifest(os.path.join(REPO, STAGE_MOD))
        M["files"] = len(head)
        M["staged_equals_head"] = staged == head
        M["staged_tree_equals_head"] = booted == head
        if staged != head:
            M["diff_staged_vs_head"] = release_pack.diff(staged, head)
        if booted != head:
            M["diff_tree_vs_head"] = release_pack.diff(booted, head)
    except (OSError, ValueError) as e:
        M["error"] = f"{type(e).__name__}: {e}"
    M["ok"] = (M.get("staged_equals_head") is True and M.get("staged_tree_equals_head") is True
               and M["mod_dirty"] is False and "error" not in M)
    return M


def harness_gate():
    H = {"commits": HARNESS_COMMITS, "ancestors": {c: git_say("merge-base", "--is-ancestor", c, "HEAD") == ""
                                                     for c in HARNESS_COMMITS},
         "lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR), "lua_dirty": git_dirty(LUA_DIR)[0],
         "repo_markers": {}}
    for fname, rel in HARNESS_FILES.items():
        try:
            with open(os.path.join(REPO, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            H["repo_markers"][fname] = {m: (m in text) for m in HARNESS_MARKERS[fname]}
            H.setdefault("repo_sha256", {})[fname] = sha256_file(os.path.join(REPO, rel))
        except OSError as e:
            H["repo_markers"][fname] = {"error": f"{type(e).__name__}: {e}"}
    H["ok"] = (all(H["ancestors"].values()) and all(isinstance(v, dict) and v and all(x is True for x in v.values())
                                                    for v in H["repo_markers"].values()))
    return H


def deployed_gate():
    """Every deployed copy of each harness file in the run dir holds its markers (each file read once)."""
    dm = {}
    for fname in HARNESS_FILES:
        for cand in sorted(glob.glob(os.path.join(run_dir, "**", "mods", "PZTestKit", "**", fname), recursive=True)):
            rel = os.path.relpath(cand, run_dir).replace(os.sep, "/")
            try:
                with open(cand, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                dm[rel] = all(m in text for m in HARNESS_MARKERS[fname])
            except OSError as e:
                dm[rel] = f"{type(e).__name__}: {e}"
    have = {f: any(k.endswith(f) for k in dm) for f in HARNESS_FILES}
    return dm, all(have.values()) and all(v is True for v in dm.values())


def refuse(msg):
    out["error"] = msg
    persist()
    print(msg)
    sys.exit(1)


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
        "run_id": run_id, "session": SESSION, "driver": _ME, "users": list(prof.users), "profile": prof.report(),
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "study_foods_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_StudyFoods"),
        "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                      if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict,
                                                                             re.Pattern))
                      and k not in ("REPO", "PRED", "DEVIATIONS")},
        "predictions": PRED,
        "deviations": list(DEVIATIONS),
        "meta": {"staging": "python tools/release_pack.py stage mod/NutritionRevamp --out release/plan11-x40 "
                            "(the controller, after Task 3c); the driver never re-stages", **META_NOTES},
        "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
        "summaries": {}, "memory": [], "world_changes": {"restored": "fixture default restored into the run dir",
                                                         "left_in_place": []},
    }
    out["manifest_gate"] = manifest_gate()
    out["harness_gate"] = harness_gate()
    if not doctor_clean:
        refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if not out["manifest_gate"]["ok"]:
        refuse("the staged copy does not equal release_pack's manifest of mod/NutritionRevamp at HEAD (or mod/ is "
               "dirty); not started")
    if not out["harness_gate"]["ok"]:
        refuse("a harness marker is missing or a harness commit is not an ancestor of HEAD; not started")
    m0 = mem("preboot")
    if m0["free_gb"] is None or m0["free_gb"] < MIN_FREE_GB:
        refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    lint_errors = lint_paths(prof.sources)
    out["lint_errors"] = lint_errors
    if lint_errors:
        refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")
    try:
        shutil.copyfile(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME), os.path.join(run_dir, MANIFEST_NAME))
        copied.append(MANIFEST_NAME)
    except OSError as e:
        out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini)
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
        dm, dok = deployed_gate()
        out["meta"]["deployed_harness_markers"] = dm
        mem("ready")
        persist()
        if not dok:
            out["abort"] = f"a deployed harness file lacks a marker: {dm!r}"
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
            adm = clients.get(USER) if isinstance(clients, dict) else None
            out["admin_lua_error"] = ("lua_error" in getattr(adm, "seen", ())) if adm is not None else None
            out["client_seen"] = [{"user": getattr(c, "username", str(i)), **dict(getattr(c, "seen", {}))}
                                  for i, c in enumerate(every)]
            if server is not None:
                out["server_errors"] = server.errors[:30]
                out["server_error_count"] = len(server.errors)
            for fn, key in ((lambda: read_logs(every), "logs_error"), (grade_all, "summary_error")):
                try:
                    fn()
                except Exception as e:             # noqa: BLE001
                    out[key] = f"{type(e).__name__}: {e}"
                    out[key + "_traceback"] = traceback.format_exc()[-3000:]
            out["bus_dead"] = bus["dead"]
            out["copied"] = sorted(set(copied))
            out["wall_seconds"] = round(time.time() - t0, 1)
            persist()
            dest_dir = os.path.join(REPO, "testing", "artifacts", run_id)
            try:
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copyfile(path, os.path.join(dest_dir, ARTIFACT))
                for nm in sorted(set(copied)):
                    if os.path.isfile(os.path.join(run_dir, nm)):
                        shutil.copyfile(os.path.join(run_dir, nm), os.path.join(dest_dir, nm))
                print(f"copied to {dest_dir}")
            except Exception as e:                 # noqa: BLE001 - never raise
                print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "summaries": {k: out.get("summaries", {}).get(k) for k in SUMMARY_KEYS},
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "body_error": out.get("body_error"),
                      "abort": out.get("abort"), "budget_stop": out.get("budget_stop"),
                      "stop_reason": out.get("stop_reason"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "run_id": run_id,
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])


if __name__ == "__main__":
    main()
