"""x405-energy -- Plan 11b Task 4 session S4e (live): the energy level's hysteresis actually exercised, and the client's
energy-level lag at the shipping day length's spacing, on the staged 1.0.0 copy the controller made after Task 3c
(release/plan11-x40/NutritionRevamp/Contents/mods/NutritionRevamp, staged with `python tools/release_pack.py stage
mod/NutritionRevamp --out release/plan11-x40`; release/ is gitignored; mod/ is never booted). One boot of profile
x40-energy (fixture default, admin -debug, a fresh restore, Nutrition false, DayLength 1, sleep off, TKX_StudyFoods by
its path). Build 42.21.0 (4a0e9546ec). Artifact `energy.json`, the staged MANIFEST.json and the minute ring's pages
copied byte-identical beside it. Written BEFORE the boot with every prediction in it and never edited after the run
(CLAUDE.md s5, B3-1/B3-2).

The driver hard-codes no commit or sha of the mod: before the boot it compares the staged copy's MANIFEST.json with
tools/release_pack.py's manifest() of mod/NutritionRevamp at HEAD (the tree clean) and of the staged tree itself,
records HEAD and the MANIFEST's sha256, and refuses to boot on any mismatch; it never re-stages. It asserts its PREFIX
and PROFILE against its own file name and the harness markers of 016dce05, 07c27dc4, 2ffdbc81, 513778e8 and ccb71a1b
(the repository copies before the boot, every deployed copy after it), each commit an ancestor of HEAD. The lib is
x391h_bench.py's (Plan 11b Task 2's latest), as x404_exercise.py carries it: bus liveness, the wall budget, spawns
confirmed by the server's item.get, grading in `finally`.

WHY (run sheet Task 4 (c)):
  * 11g: the energy-level hysteresis actually exercised. K.view.energyLevel holds a reached level until the energy
    state falls ENERGY_BAND (0.01) under its bound (ruling T7-2; the server alone holds it off the player's last push
    signature, every mirror carries it as body_energyLevel, ruling T7-7). Drive a fresh record's fast just past level
    1's bound, then feed so the state falls under the bound but within the band: the server's held level stays at 1
    and the client shows 1 on same-second pairs; then feed past the band, and the level falls.
  * 11g: the client energy-level lag at the shipping day length (C-28): measured at the DayLength 4 spacing
    (`time.multiplier 0.1674` at speed 1, a game minute about 3.73 s of wall), the wall seconds and game minutes from
    the server's level change to the client's; the expected bound is the 60 s push gap (NR_Server_Bus.lua
    PUSH_GAP_MS), about 16 game minutes at that spacing.

THE ARITHMETIC THE DESIGN RESTS ON (named before the run): es = 1 + 0.5 x (-eb24h / BALANCE_SPAN_KCAL 3970.55) + 0.5
x fatDep (K.deficit.state), so 1 kcal of the trailing window's balance moves es by 1.259e-4; x364's resting fast
spent about 95.3 kcal a game hour (its ring's body.eeDay) and raised es 0.0120 a game hour; a meal enters the window
as the stomach empties it, at K.stomach.RATE_BASE 1.25 + RATE_PER_KCAL 0.0025 x the load kcal a minute. So a 217 kcal
snack empties at about 107 kcal an hour, barely over the fast's spend, and dips es by about 0.0006 at most; THE SNACK
HERE IS TKX.Mixed400 (named departure from the run sheet's "small snack"): it empties at about 135 kcal an hour at
first, and dips es by about 0.006 over about 2.3 game hours before the fast's spend wins again, so a state just over
1.10 when it lands falls inside the band and stays above 1.09. THE MEAL IS TKX.Mixed650 (eat time 464 x 20 ms): on
top of the snack's remainder it empties at about 190 kcal an hour and carries es under 1.09.

PHASES (each checked against the wall budget before it starts; the server bus's liveness after every server step):
  S0    ready, ping, players, speed 1, the kernel constants read live (K.view.ENERGY_AT[1] and [2], ENERGY_BAND,
        K.deficit.BALANCE_SPAN_KCAL, the bus's PUSH_GAP_MS), the record (firstSeen, body.energyState), one pair.
  H     the minute ring armed on admin (the energy state, the day's expenditure and intake, the stomach, the last push
        signature and push count, the intake's counters).
  FOOD  RCON `additem "admin" "TKX.Mixed400" 1` and `additem "admin" "TKX.Mixed650" 1`, each confirmed by the server's
        item.get id with no leftover before it (ruling T2-11; never inventory.add).
  FAST  speed 5 until the record's energy state reads at least ENERGY_AT[1] - FAST_STOP_GAP (polled every POLL_S),
        then the slow spacing: `settimespeed 1` and `time.multiplier 0.1674`.
  RISE  at the slow spacing, pairs back to back (PAIR: the client's mirror level, mirror state, moodle level, view
        class and received count in one lua.read, at once the server's last push signature, push count and the
        record's energy state in one lua.read, then the world age), until the server's held level reads 1 and the
        client shows 1 plus RISE_TAIL more pairs; caps: RISE_WAIT_CAP_S for the server's change, then LAG_CAP_S
        for the client's.
  HOLD  speed 1; the snack eaten (foodtimer 0, eat.action TKX.Mixed400 1; a `spawned` other than "found" stops the
        eats); pairs for HOLD_S of wall, or until the state reads at most ENERGY_AT[1] - ENERGY_BAND + FLOOR_GAP.
  FALL  speed 1; the meal eaten (eat.action TKX.Mixed650 1); pairs at speed 1 until the state reads at most
        ENERGY_AT[1] - ENERGY_BAND + FLOOR_GAP (FALL_ONE_CAP_S), then the slow spacing and pairs until the server's
        held level reads 0 and the client shows 0 plus FALL_TAIL pairs; caps: FALL_WAIT_CAP_S for the server's
        change, then LAG_CAP_S for the client's.
  RING  the ring's pages read and copied (always run; the server steps skipped on a dead bus).
  Z     the local readings first, then players, the clock and the intake's counters.

PREDICTIONS (graded in `verdicts`; a dead-bus phase is void, never falsified):
  FOOD        the server answers an id for TKX.Mixed400 and TKX.Mixed650 after the spawn and none before.
  LEVEL_RISE  the server's held level steps 0 -> 1 at the bound: its first level-1 pair reads es >= ENERGY_AT[1] -
              ES_TOL and its last level-0 pair es < ENERGY_AT[1] + ES_TOL (the sig is the last flush's, the es the
              tick's: ES_TOL covers a game minute's move). Falsifier: either off. Unmeasured: no change in RISE.
  LAG_RISE    the client's first pair showing 1 comes at most PUSH_GAP_S + LAG_SLACK_S (65 s) of wall after the
              server's first pair holding 1 (lag_est, with its bracket from the last pairs before each change), and the
              client never shows a level the server has not held before it. Expected about 16 game minutes at the
              slow spacing (C-28). Falsifier: lag_est over 65 s, or the client changing first or to another level.
              Unmeasured: no server change, or the client's cap ended before 65 s.
  HOLD        every same-second pair (wall gap <= PAIR_GAP_MAX_S) in HOLD and FALL whose es lies in [ENERGY_AT[1] -
              ENERGY_BAND + ES_TOL, ENERGY_AT[1] - ES_TOL] reads the server's held level 1 and the client's 1 (the
              window is not cut at the fall's change: a level dropped inside the band is the falsifier itself); at
              least HOLD_MIN_PAIRS such pairs. Falsifier: a level other than 1 on either side in the band. Unmeasured:
              fewer such pairs and none bad (the state never entered the band).
  LEVEL_FALL  the server's held level steps 1 -> 0 at the band's floor: its first level-0 pair after the hold reads
              es < ENERGY_AT[1] - ENERGY_BAND + ES_TOL and its last level-1 pair es >= ENERGY_AT[1] - ENERGY_BAND -
              ES_TOL. Falsifier: either off. Unmeasured: no change in FALL.
  LAG_FALL    as LAG_RISE for the change 1 -> 0.
  SLOW        every time.snapshot read at the slow spacing (RISE and FALL's slow part) reads trueMult 0.1674 within
              1e-4. Falsifier: a measured read off; a null read is unmeasured.
  RING        every page read with errors 0. The ring's per-minute held level (its signature's energy digit) is a
              reading beside the pairs.
  Z           no mod error line, admin not parked, and the server alive at the end.

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

PROFILE = "x40-energy"
PREFIX = "x405"
SESSION = ("Plan 11b Task 4 session S4e (x405): a fresh, unfed record's fast to the energy level-1 bound, the crossing "
           "and the client's lag at the DayLength 4 spacing, the hold inside ENERGY_BAND after a snack and the fall past "
           "it after a meal, on same-second pairs, on the staged 1.0.0 copy; one boot of " + PROFILE)
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert PROFILE == "x40-energy" and _ME == "x405_energy.py", f"PROFILE {PROFILE} does not match the driver {_ME}"
ARTIFACT = "energy.json"
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
KPATHS = {"at1": f"{NR}.kernel.view.ENERGY_AT.1", "at2": f"{NR}.kernel.view.ENERGY_AT.2",
          "band": f"{NR}.kernel.view.ENERGY_BAND", "span": f"{NR}.kernel.deficit.BALANCE_SPAN_KCAL",
          "gapMs": f"{NR}.server.bus.PUSH_GAP_MS"}
CLI_ENERGY = (f"{NR}.client.mirror.body_energyLevel", f"{NR}.client.mirror.body_energyState",
              f"{NR}.client.moodles.levels.energy", f"{NR}.client.view.classes.energy", f"{NR}.client.received")
SRV_ENERGY = (f"{NR}.server.bus.lastSig.{USER}", f"{NR}.server.bus.effects.stats.pushes",
              f"{NR}.server.store.records.{USER}.body.energyState")
INTAKE_PATHS = (f"{NR}.server.intake.stats.eats", f"{NR}.server.intake.stats.cancels",
                f"{NR}.server.intake.stats.landed", f"{NR}.server.intake.stats.failures")
RING_RECORD = ("body.energyState", "body.eeDay", "body.inDay", "stomachFill", "stomach.buffer.calories", "satiety.M",
               "body.fm")
RING_GLOBALS = (f"_G.{NR}.server.bus.lastSig.{USER}", f"_G.{NR}.server.bus.effects.stats.pushes",
                f"_G.{NR}.server.intake.stats.eats", f"_G.{NR}.server.intake.stats.landed")
SIG_RING = f"_G.{NR}.server.bus.lastSig.{USER}"
SNACK, MEAL = "TKX.Mixed400", "TKX.Mixed650"
# the clock
SPEED_FAST = 5
SLOW_MULT = 0.1674                   # at speed 1 on DayLength 1: a game minute about 3.73 s of wall (the DayLength 4 spacing)
MULT_TOL = 1e-4
FAST_STOP_GAP = 0.004                # the fast stops at es >= ENERGY_AT[1] - this (about 20 game minutes short of it)
FAST_CAP_H = 20.0                    # game hours of fast at most
FLOOR_GAP = 0.003                    # HOLD ends, and FALL goes slow, at es <= ENERGY_AT[1] - ENERGY_BAND + this
ES_TOL = 0.0005                      # a game minute's move of es at the fast's rate (0.0002) with room
PUSH_GAP_S = 60.0                    # NR_Server_Bus.lua PUSH_GAP_MS (read live too)
LAG_SLACK_S = 5.0
PAIR_GAP_MAX_S = 1.0
RISE_WAIT_CAP_S = 150.0
LAG_CAP_S = 80.0
RISE_TAIL = 3
HOLD_S = 90.0
HOLD_MIN_PAIRS = 5
FALL_ONE_CAP_S = 60.0
FALL_WAIT_CAP_S = 150.0
FALL_TAIL = 3
PAIR_SLEEP_S = 0.05
EAT_CAP_S = 25.0
SPAWN_WAIT_S = 2.5
# liveness and the wall budget
PING_TIMEOUT_S = 5
BUDGET_S = 840.0                     # from t0 (before the boot); RING, Z and the teardown fit 900 s
PHASE_EST_S = {"S0": 10.0, "H": 4.0, "FOOD": 10.0, "FAST": 75.0, "RISE": 120.0, "HOLD": 100.0, "FALL": 150.0}
MIN_FREE_GB = 12.0
RESULT_WAIT_S = 30.0
POLL_S = 0.25
LOG_LIMIT = 400
ECHO_RX = re.compile(r"PZTK: ")
PROBE_RX = re.compile(r"\b(?:minute\.ring|lua\.(?:read|global)|time\.(?:snapshot|multiplier)|item\.get|eat\.action|"
                      r"foodtimer\.set|additem|settimespeed|stats\.get)")
                                     # this driver's own probe and command names, excluded from every log grep
MOD_LIFE_RX = re.compile(r"minute: \w+ failed|players: hook failed|players: task|intake: |writer: |bus: |non-finite")
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")

META_NOTES = {
    "pair_note": "a pair is the client's lua.read of its mirror level, mirror state, moodle level, view class and "
                 "received count, at once the server's lua.read of the last push signature, the push count and the "
                 "record's energy state (one tick each), then the world age; the server's held level is the "
                 "signature's energy digit (K.view.signatureEnergy), the client's shown level its mirror's "
                 "body_energyLevel when a whole number, else its view's class (K.view.mirrorEnergy)",
    "lag_note": "lag_est is the client's first new-level read's wall minus the server's first new-level read's; its "
                "bracket runs from the last old-level reads on each side; walls are the driver's clock",
    "snack_note": "the snack is TKX.Mixed400, not a smaller one: a 217 kcal snack empties barely faster than the fast "
                  "spends and dips es by about 0.0006 (the docstring's arithmetic)",
    "spawn_note": "the foods are spawned by RCON additem and confirmed by the server's item.get id (ruling T2-11)",
    "eat_note": "a networked eat ends in real time, 232 x 20 ms a loop, whatever the clock (#3766); Mixed650 eats in two",
    "frame_note": "no frame window is graded in this session (no tick.ring), so no drop_windows apply"}
SUMMARY_KEYS = ("fast", "rise", "hold", "fall", "pairs")


PRED = {
    "FOOD": {"item.get after the spawn": f"an id for {SNACK} and {MEAL}, none before",
             "falsifier": "an id missing on a live bus"},
    "LEVEL_RISE": {"server": "first level-1 pair es >= ENERGY_AT[1] - ES_TOL; last level-0 pair es < ENERGY_AT[1] + ES_TOL",
                   "falsifier": "either off", "unmeasured": "no change in RISE"},
    "LAG_RISE": {"client": f"its first level-1 read at most {PUSH_GAP_S + LAG_SLACK_S} s of wall after the server's",
                 "expected": "about 16 game minutes at the slow spacing (C-28)",
                 "falsifier": "lag_est over the bound, the client changing first, or to a level the server never held",
                 "unmeasured": "no server change, or the client's cap ended before the bound"},
    "HOLD": {"same-second pairs in HOLD and FALL with es in [AT1 - BAND + ES_TOL, AT1 - ES_TOL]":
             "server level 1 and client level 1", "minimum pairs": HOLD_MIN_PAIRS,
             "falsifier": "a level other than 1 on either side in the band", "unmeasured": "fewer such pairs"},
    "LEVEL_FALL": {"server": "first level-0 pair es < AT1 - BAND + ES_TOL; last level-1 pair es >= AT1 - BAND - ES_TOL",
                   "falsifier": "either off", "unmeasured": "no change in FALL"},
    "LAG_FALL": {"client": f"its first level-0 read at most {PUSH_GAP_S + LAG_SLACK_S} s of wall after the server's",
                 "falsifier": "as LAG_RISE", "unmeasured": "as LAG_RISE"},
    "SLOW": {"time.snapshot at the slow spacing": f"trueMult {SLOW_MULT} within {MULT_TOL}",
             "falsifier": "a measured read off (a null read is unmeasured)"},
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


# ---------------------------------------------------------------- the energy verbs
PAIRS = []


def energy_digit(sig):
    """The energy level a push signature holds (K.view.signatureEnergy): floor(sig / 1000) % 10; None for a non-number."""
    v = num(sig)
    if v is None:
        return None
    return int(math.floor(v / 1000.0)) % 10


def k_const(name, default=None):
    v = g(out, "phases", "S0", "k", name)
    return v if v is not None else default


def pair(tag):
    """A same-second pair (x36's energy pair on this lib): the client's mirror, moodle and view in one lua.read, at once
    the server's signature, push count and the record's energy state in one lua.read, then the world age."""
    c = lread(ADMIN, "_G", CLI_ENERGY, tag + "_c", log=False)
    s = lread(SRV, "_G", SRV_ENERGY, tag + "_s", log=False)
    a = snap(tag + "_a", log=False)
    cv, sv = vals(c), vals(s)
    lv = num(cv.get(CLI_ENERGY[0]))
    view = num(cv.get(CLI_ENERGY[3]))
    shown = int(lv) if (lv is not None and lv == int(lv)) else (int(view) if view is not None else None)
    cw, sw = num(c.get("wall")), num(s.get("wall"))
    row = {"tag": tag, "phase": cur_phase["name"], "age": num(a.get("worldAge")), "trueMult": num(a.get("trueMult")),
           "client_wall": cw, "server_wall": sw, "wall_gap": (sw - cw) if (cw is not None and sw is not None) else None,
           "client_level": shown, "client_mirror_level": lv, "client_mirror_es": num(cv.get(CLI_ENERGY[1])),
           "client_moodle": num(cv.get(CLI_ENERGY[2])), "client_view": view, "client_received": num(cv.get(CLI_ENERGY[4])),
           "server_sig": num(sv.get(SRV_ENERGY[0])), "server_level": energy_digit(sv.get(SRV_ENERGY[0])),
           "server_pushes": num(sv.get(SRV_ENERGY[1])), "server_es": num(sv.get(SRV_ENERGY[2]))}
    if c.get("missing"):
        row["client_missing"] = c.get("missing")
    if s.get("missing"):
        row["server_missing"] = s.get("missing")
    PAIRS.append(row)
    return row


def es_now(tag):
    a = lread(SRV, "_G", [SRV_ENERGY[2]], tag, log=False)
    return num(vals(a).get(SRV_ENERGY[2]))


def slow(tag):
    """The DayLength 4 spacing: settimespeed 1, then time.multiplier SLOW_MULT, and the clock read after it."""
    rcon("settimespeed 1", tag + "_one")
    m = keep(step(tag + "_mult", SRV, "time.multiplier", str(SLOW_MULT)))
    s = snap(tag + "_t")
    out.setdefault("speeds", []).append({"mode": "slow", "age": s.get("worldAge"), "mult": s.get("mult"),
                                         "trueMult": s.get("trueMult"), "wall": s.get("wall"), "reply": m.get("raw")})
    return s


def watch_change(frm, to, wait_cap_s, tail, label, stop_es=None):
    """Pairs back to back until the server's held level reads `to` (after `frm`) and the client shows `to`, plus `tail`
    pairs; wait_cap_s for the server's change, then LAG_CAP_S for the client's. Returns a summary of the walls."""
    R = {"from": frm, "to": to, "server_first": None, "client_first": None, "pairs": 0}
    t_start = time.time()
    t_server = None
    extra = 0
    while True:
        check()
        p = pair(label)
        R["pairs"] += 1
        if p["server_level"] == to and R["server_first"] is None:
            R["server_first"] = {k: p.get(k) for k in ("tag", "age", "server_wall", "server_es", "server_sig")}
            t_server = time.time()
        if p["client_level"] == to and R["client_first"] is None and R["server_first"] is not None:
            R["client_first"] = {k: p.get(k) for k in ("tag", "age", "client_wall", "client_mirror_level",
                                                      "client_view", "client_received")}
        if R["client_first"] is not None:
            extra += 1
            if extra > tail:
                break
        if t_server is None and time.time() - t_start > wait_cap_s:
            R["cap"] = "server"
            break
        if t_server is not None and R["client_first"] is None and time.time() - t_server > LAG_CAP_S:
            R["cap"] = "client"
            break
        if bus["dead"]:
            raise BusDead(out.get("abort") or "server bus dead")
        time.sleep(PAIR_SLEEP_S)
    R["wall_s"] = round(time.time() - t_start, 3)
    return R


def eat_landed(full_type, label):
    """foodtimer 0 and eat.action (eat_queue), then intake.stats.landed polled until it rises (EAT_CAP_S), pairing
    meanwhile so the record's state is read through the eat."""
    E = {"food": full_type}
    E["before"] = intake(label + "_in0", log=True)
    E["queued"] = eat_queue(full_type, label)
    E["landed"] = False
    end = time.time() + EAT_CAP_S
    while time.time() < end:
        check()
        pair(label + "_eatpair")
        a = intake(label + "_poll")
        if a.get("landed") is not None and E["before"].get("landed") is not None and a["landed"] > E["before"]["landed"]:
            E["landed"], E["after"] = True, a
            E["landed_snap"] = snap(label + "_landed_t")
            break
        if bus["dead"]:
            raise BusDead(out.get("abort") or "server bus dead")
        time.sleep(POLL_S)
    if not E["landed"]:
        note(f"{label}: landed did not rise within {EAT_CAP_S} s")
    return E


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    P["ping"] = ping("S0_ping")
    P["players"] = keep(step("S0_players", SRV, "players"))
    P["one"] = speed("one", "S0_one")
    P["kernel"] = lread(SRV, "_G", list(KPATHS.values()), "S0_kernel")
    P["k"] = {k: num(vals(P["kernel"]).get(p)) for k, p in KPATHS.items()}
    P["record"] = lread(SRV, f"record:{USER}", ["firstSeen", "resets", "body.sex", "body.energyState", "body.eeDay",
                                                "body.inDay", "body.fm", "body.lm"], "S0_record")
    P["intake"] = intake("S0_intake", log=True)
    P["pair"] = pair("S0_pair")


def phase_H():
    P = out["phases"]["H"] = {}
    paths = list(RING_RECORD) + list(RING_GLOBALS)
    P["paths"] = paths
    P["start"] = keep(step("H_ring_start", SRV, "minute.ring", " ".join([USER, "start"] + paths)))
    P["snap"] = snap("H_snap")


def phase_FOOD():
    P = out["phases"]["FOOD"] = {}
    P["snack"] = spawn(SNACK, 1, "FOOD_snack")
    P["meal"] = spawn(MEAL, 1, "FOOD_meal")


def phase_FAST():
    P = out["phases"]["FAST"] = {}
    at1 = k_const("at1", 1.10)
    P["stop_es"] = stop = at1 - FAST_STOP_GAP
    P["es0"] = es0 = es_now("FAST_es0")
    P["age0"] = a0 = age("FAST_a0")
    if es0 is not None and es0 >= stop:
        note(f"FAST: es {es0} already at or past {stop}; no fast")
    else:
        P["fast"] = speed("fast", "FAST_fast")
        cap = (a0 or 0.0) + FAST_CAP_H
        polls = 0
        while True:
            check()
            e = es_now("FAST_es")
            a = age("FAST_a")
            polls += 1
            if (e is not None and e >= stop) or (a is not None and a >= cap):
                P["es_stop"], P["age_stop"] = e, a
                break
            if bus["dead"]:
                raise BusDead(out.get("abort") or "server bus dead")
            time.sleep(POLL_S)
        P["polls"] = polls
    P["slow"] = slow("FAST_slow")
    P["es1"] = es_now("FAST_es1")
    P["pair"] = pair("FAST_pair")


def phase_RISE():
    P = out["phases"]["RISE"] = {}
    P["watch"] = watch_change(0, 1, RISE_WAIT_CAP_S, RISE_TAIL, "RISE")


def phase_HOLD():
    P = out["phases"]["HOLD"] = {}
    at1, band = k_const("at1", 1.10), k_const("band", 0.01)
    floor = at1 - band + FLOOR_GAP
    P["one"] = speed("one", "HOLD_one")
    if g(out, "phases", "FOOD", "snack", "confirmed") is not True:
        note("HOLD: the snack was not confirmed; no eat (the hold reads the pairs alone)")
    else:
        P["eat"] = eat_landed(SNACK, "HOLD_snack")
    end = time.time() + HOLD_S
    n = 0
    while time.time() < end:
        check()
        p = pair("HOLD")
        n += 1
        if p["server_es"] is not None and p["server_es"] <= floor:
            P["floor_reached"] = {k: p.get(k) for k in ("age", "server_es", "server_level", "client_level")}
            break
        if bus["dead"]:
            raise BusDead(out.get("abort") or "server bus dead")
        time.sleep(PAIR_SLEEP_S)
    P["pairs"] = n


def phase_FALL():
    P = out["phases"]["FALL"] = {}
    at1, band = k_const("at1", 1.10), k_const("band", 0.01)
    floor = at1 - band + FLOOR_GAP
    P["one"] = speed("one", "FALL_one")
    if g(out, "phases", "FOOD", "meal", "confirmed") is not True:
        note("FALL: the meal was not confirmed; no eat (void)")
        return
    P["eat"] = eat_landed(MEAL, "FALL_meal")
    end = time.time() + FALL_ONE_CAP_S
    while True:
        check()
        p = pair("FALL_one")
        if p["server_es"] is not None and p["server_es"] <= floor:
            break
        if p["server_level"] == 0:
            note("FALL: the server's level fell at speed 1, before the slow spacing")
            break
        if time.time() >= end:
            note(f"FALL: es still over {floor} after {FALL_ONE_CAP_S} s at speed 1; the slow spacing anyway")
            break
        if bus["dead"]:
            raise BusDead(out.get("abort") or "server bus dead")
        time.sleep(PAIR_SLEEP_S)
    P["slow"] = slow("FALL_slow")
    P["watch"] = watch_change(1, 0, FALL_WAIT_CAP_S, FALL_TAIL, "FALL")


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


ORDER = (("S0", phase_S0), ("H", phase_H), ("FOOD", phase_FOOD), ("FAST", phase_FAST), ("RISE", phase_RISE),
         ("HOLD", phase_HOLD), ("FALL", phase_FALL))
EAT_PHASES = ()                      # HOLD and FALL read their pairs even after a stopped eat


def body():
    out["budget"] = {"BUDGET_S": BUDGET_S, "checks": [], "estimate_total_s": sum(PHASE_EST_S.values())}
    for name, fn in ORDER:
        if bus["dead"] or out.get("budget_stop"):
            break                                  # out["abort"] or out["budget_stop"] names why; RING and Z still run
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
    out["pairs"] = PAIRS
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


def change_of(pairs, frm, to):
    """The server's and the client's change frm -> to across `pairs` (in order): each side's first new-level read after
    an old-level read on that side and the last old-level read before it; lag_est from the server's first to the
    client's first, its bracket, the game minutes, and whether the client ever showed a level outside {frm, to} or
    changed before the server."""
    C = {"from": frm, "to": to}
    si = next((i for i, p in enumerate(pairs) if p.get("server_level") == to
               and any(q.get("server_level") == frm for q in pairs[:i])), None)
    if si is None:
        C["server_changed"] = False
        return C
    C["server_changed"] = True
    s_last_old = next((pairs[j] for j in range(si - 1, -1, -1) if pairs[j].get("server_level") == frm), None)
    sf = pairs[si]
    C["server_first"] = {k: sf.get(k) for k in ("tag", "age", "server_wall", "server_es", "server_sig")}
    C["server_last_old"] = {k: s_last_old.get(k) for k in ("tag", "age", "server_wall", "server_es")} if s_last_old else None
    ci = next((i for i, p in enumerate(pairs) if p.get("client_level") == to
               and any(q.get("client_level") == frm for q in pairs[:i])), None)
    C["client_changed"] = ci is not None
    C["client_before_server"] = ci is not None and ci < si
    C["client_other_levels"] = sorted({p.get("client_level") for p in pairs
                                       if p.get("client_level") is not None and p.get("client_level") not in (frm, to)})
    if ci is None:
        return C
    cf = pairs[ci]
    c_last_old = next((pairs[j] for j in range(ci - 1, -1, -1) if pairs[j].get("client_level") == frm), None)
    C["client_first"] = {k: cf.get(k) for k in ("tag", "age", "client_wall", "client_mirror_level", "client_view",
                                                "client_received")}
    C["client_last_old"] = {k: c_last_old.get(k) for k in ("tag", "age", "client_wall")} if c_last_old else None
    sw, cw = num(sf.get("server_wall")), num(cf.get("client_wall"))
    C["lag_est_s"] = (cw - sw) if (cw is not None and sw is not None) else None
    if s_last_old is not None and cw is not None and num(s_last_old.get("server_wall")) is not None:
        C["lag_upper_s"] = cw - s_last_old["server_wall"]
    if c_last_old is not None and sw is not None and num(c_last_old.get("client_wall")) is not None:
        C["lag_lower_s"] = max(0.0, c_last_old["client_wall"] - sw)
    sa, ca = num(sf.get("age")), num(cf.get("age"))
    C["lag_game_min"] = ((ca - sa) * 60.0) if (sa is not None and ca is not None) else None
    if s_last_old is not None and ca is not None and num(s_last_old.get("age")) is not None:
        C["lag_game_min_upper"] = (ca - s_last_old["age"]) * 60.0
    return C


def grade_change(name_level, name_lag, pairs, frm, to, es_lo_ok, es_hi_ok, dead_phase):
    C = change_of(pairs, frm, to)
    out["summaries"].setdefault("changes", {})[name_level] = C
    if not C.get("server_changed"):
        v = "void" if dead_phase else "unmeasured"
        grade(name_level, v, C, PRED[name_level]["unmeasured"])
        grade(name_lag, v, C, PRED[name_lag]["unmeasured"])
        return C
    es_first = num(g(C, "server_first", "server_es"))
    es_old = num(g(C, "server_last_old", "server_es"))
    ok_lv = es_first is not None and es_lo_ok(es_first) and (es_old is None or es_hi_ok(es_old))
    grade(name_level, "as_predicted" if ok_lv else "falsified", C, PRED[name_level]["falsifier"],
          {"es_first": es_first, "es_last_old": es_old})
    bound = PUSH_GAP_S + LAG_SLACK_S
    lag = num(C.get("lag_est_s"))
    if C.get("client_before_server") or C.get("client_other_levels"):
        grade(name_lag, "falsified", C, PRED[name_lag]["falsifier"])
    elif lag is None:
        waited = None
        lastp = pairs[-1] if pairs else None
        if lastp is not None and num(lastp.get("client_wall")) is not None and num(g(C, "server_first", "server_wall")) is not None:
            waited = lastp["client_wall"] - C["server_first"]["server_wall"]
        v = "falsified" if (waited is not None and waited > bound) else ("void" if dead_phase else "unmeasured")
        grade(name_lag, v, C, PRED[name_lag]["falsifier"], {"waited_s": waited})
    else:
        grade(name_lag, "as_predicted" if lag <= bound else "falsified", C, PRED[name_lag]["falsifier"],
              {"bound_s": bound})
    return C


def grade_all():
    S = out["summaries"]
    ph = out["phases"]
    dead = bus["dead"]
    at1, band = k_const("at1"), k_const("band")
    S["kernel"] = g(ph, "S0", "k")
    pairs = out.get("pairs") or PAIRS
    gaps = [abs(p["wall_gap"]) for p in pairs if num(p.get("wall_gap")) is not None]
    S["pairs"] = {"n": len(pairs), "max_wall_gap": max(gaps) if gaps else None,
                  "over_gap": sum(1 for x in gaps if x > PAIR_GAP_MAX_S)}
    # FOOD
    F = ph.get("FOOD") or {}
    if not F:
        grade("FOOD", "void" if dead else "unmeasured", None, "phase not run")
    else:
        ok = g(F, "snack", "confirmed") is True and g(F, "meal", "confirmed") is True
        grade("FOOD", "as_predicted" if ok else ("void" if phase_dead("FOOD") else "falsified"),
              {"snack": g(F, "snack", "confirmed"), "meal": g(F, "meal", "confirmed")}, PRED["FOOD"]["falsifier"])
    S["fast"] = {k: g(ph, "FAST", k) for k in ("es0", "age0", "stop_es", "es_stop", "age_stop", "es1", "polls")}
    if at1 is None or band is None:
        for k in ("LEVEL_RISE", "LAG_RISE", "HOLD", "LEVEL_FALL", "LAG_FALL"):
            grade(k, "void" if dead else "unmeasured", None, "the kernel's ENERGY_AT[1] or ENERGY_BAND not read")
    else:
        rise = [p for p in pairs if p.get("phase") in ("S0", "FAST", "RISE")]
        S["rise"] = grade_change("LEVEL_RISE", "LAG_RISE", rise, 0, 1, lambda e: e >= at1 - ES_TOL,
                                 lambda e: e < at1 + ES_TOL, phase_dead("RISE") or bool(dead))
        fall = [p for p in pairs if p.get("phase") in ("HOLD", "FALL")]
        # every same-second pair after the rise whose es lies inside the band under the bound, whatever its phase: a
        # level dropped inside the band is the falsifier itself, so the window is not cut at the fall's change
        lo, hi = at1 - band + ES_TOL, at1 - ES_TOL
        held = [p for p in fall if num(p.get("server_es")) is not None and lo <= p["server_es"] <= hi
                and num(p.get("wall_gap")) is not None and abs(p["wall_gap"]) <= PAIR_GAP_MAX_S]
        bad = [{k: p.get(k) for k in ("tag", "age", "server_es", "server_level", "client_level", "wall_gap")}
               for p in held if p.get("server_level") != 1 or p.get("client_level") != 1]
        S["hold"] = {"band": [lo, hi], "pairs_in_band": len(held), "bad": bad[:20], "bad_n": len(bad),
                     "es_min": min((p["server_es"] for p in fall if num(p.get("server_es")) is not None), default=None),
                     "snack_landed": g(ph, "HOLD", "eat", "landed"), "floor_reached": g(ph, "HOLD", "floor_reached"),
                     "rise_reached": bool(g(S, "rise", "server_changed"))}
        if bad:
            grade("HOLD", "falsified", S["hold"], PRED["HOLD"]["falsifier"])
        elif len(held) < HOLD_MIN_PAIRS:
            grade("HOLD", "void" if (dead or phase_dead("HOLD") or phase_dead("FALL")) else "unmeasured", S["hold"],
                  PRED["HOLD"]["unmeasured"])
        else:
            grade("HOLD", "as_predicted", S["hold"], PRED["HOLD"]["falsifier"])
        S["fall"] = grade_change("LEVEL_FALL", "LAG_FALL", fall, 1, 0, lambda e: e < at1 - band + ES_TOL,
                                 lambda e: e >= at1 - band - ES_TOL, phase_dead("FALL") or bool(dead))
        S["fall"]["meal_landed"] = g(ph, "FALL", "eat", "landed")
    # SLOW
    slow_pairs = [p for p in pairs if p.get("phase") == "RISE" or (p.get("phase") == "FALL" and p.get("tag") == "FALL")]
    measured = [p["trueMult"] for p in slow_pairs if num(p.get("trueMult")) is not None]
    off = [m for m in measured if abs(m - SLOW_MULT) > MULT_TOL]
    S["slow"] = {"reads": len(slow_pairs), "measured": len(measured), "off": off[:10],
                 "speeds": out.get("speeds")}
    if not measured:
        grade("SLOW", "void" if dead else "unmeasured", S["slow"], PRED["SLOW"]["falsifier"])
    else:
        grade("SLOW", "as_predicted" if not off else "falsified", S["slow"], PRED["SLOW"]["falsifier"])
    # RING
    pages = g(ph, "RING", "pages") or []
    errs = [num(g(p, "reply", "errors")) for p in pages]
    if not pages:
        grade("RING", "void" if dead else "unmeasured", {"pages": 0}, "no page read")
    else:
        ok = all(p.get("file") for p in pages) and all((e or 0) == 0 for e in errs)
        grade("RING", "as_predicted" if ok else ("void" if dead else "falsified"),
              {"pages": len(pages), "files": [p.get("file") for p in pages], "errors": errs}, "a page unread or errors")
    rows = load_ring(run_dir) if run_dir else []
    lv_changes, last = [], None
    for r in rows:
        lv = energy_digit(r.get(SIG_RING))
        if lv is not None and last is not None and lv != last:
            lv_changes.append({"s": r.get("s"), "age": r.get("age"), "from": last, "to": lv,
                               "es": r.get("body.energyState")})
        if lv is not None:
            last = lv
    S["ring_levels"] = {"rows": len(rows), "changes": lv_changes}
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
                      and k not in ("REPO", "PRED")},
        "predictions": PRED,
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
