"""x403-overlay -- Plan 11b Task 4, session S4c: the 1.0.0 release in Overlay (Mode 2) beside a stand-in for Nutrition
Makes Sense, on fixture `two` (admin -debug, then bob release), one boot of profile x40-overlay, with MoodleFramework.
On the STAGED copy the controller makes after Task 3c (release/plan11-x40/NutritionRevamp/Contents/mods/NutritionRevamp,
`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan11-x40`; release/ is gitignored; mod/ is never
booted). The driver names no commit and no sha for the stage: before the boot it imports tools/release_pack.py and checks
that the staged MANIFEST.json equals release_pack.manifest(mod/NutritionRevamp) on a clean mod/ tree (so it is HEAD's)
and that the staged files hash to it; it records HEAD and the MANIFEST's sha256 and refuses to boot on any mismatch. It
never re-stages. TKX_NmsStub (testing/experiments/TKX_NmsStub/42/mod.info: name=, id=NutritionMakesSense, versionMin;
never Nutrition Makes Sense's code) puts Nutrition Makes Sense's id in the server's activated-mods list without loading
anything. Build 42.21.0 (4a0e9546ec), Nutrition false, DayLength 1, [sandbox.NR] Mode = 2, TKX_StudyFoods by its path.
Artifact: `overlay.json` and the staged MANIFEST.json beside it (server-stdout.log as x391a-h: the controller copies it
when it is the evidence of an event). Written BEFORE the boot with every prediction in it and never edited after the run
(CLAUDE.md s5, B3-1/B3-2). Shape: x401_accept.py (the same liveness, budget, stage check, marker check, RCON spawns
confirmed by item.get and the client's witness, and the same overfull drive).

PHASES (run order; each checked against the wall budget before it starts):
  S0  ready, ping, players, the clocks, both records present and MIN_RUNS minute runs.
  N   THE OVERLAY READS (the plan's x252b): writer.zeroed, writer.mode, writer.stats.nms, `lua.call
      NutritionRevamp.vanillaRate HungerIncrease`, `lua.global ZomboidGlobals.HungerIncrease`, the seven saved rates
      against the live table, the version on all three sides, admin's moodle route. Then admin's HUNGER and the writer's
      writes read, the world clock polled (with a stats.all of admin at every poll) until 60 game minutes have passed
      (cap N_CAP_S), and HUNGER and the writes read again. After teardown the logs: the server's self-report, each
      client's, exactly one `Nutrition Makes Sense is loaded` warning, the Overlay line and no zeroing line.
  MF  THE OVERFULL MOODLE, MOODLEFRAMEWORK ROUTE (11c): x401's drive (two TKX.Mixed650 eats and one 1 L WATER_ITEM
      drink on admin, each spawned by RCON additem and confirmed by item.get and the client's witness), and after each
      intake the server's stomach mass and push signature, then on admin's client `lua.call
      NutritionRevamp.client.requestMirror`, the arrival polled, the mirror's stomachMass, moodles.levels.overfull,
      view.classes.overfull, moodles.route and `lua.call NutritionRevamp.client.moodles.probe overfull` (on this route
      the probe answers the framework moodle's own getLevel()). On-screen drawing is not a harness reading: Angus's eye
      on the -debug client during the session, recorded in the reading guide, or unmeasured.
  Z   the mod-error lines, admin not parked, `players`, the clock, the writer's counters.

LIVENESS AND THE BUDGET (x391h's D1, D2): a ping after any server step that times out; no pong ends every server phase
(the later server steps skipped, Z's local readings kept). BUDGET_S 840 s from t0, checked before each phase and inside
every poll loop. Teardown, the artifact copy and grading in finally. A dead-bus phase is void, not falsified.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured / void, each with its falsifier):
  STAGE   as x401: the staged MANIFEST equals release_pack.manifest(mod/NutritionRevamp) on a clean tree, the staged
          files and every deployed copy hash to it.
  V       every verify row ok.
  NMS     the server log carries exactly one `Nutrition Makes Sense is loaded` line; writer.stats.nms true.
  N       writer.zeroed false and mode 2; vanillaRate(HungerIncrease) and ZomboidGlobals.HungerIncrease both 9.6e-6
          within 1e-12 (#0470); each of the seven live ZomboidGlobals rates equals its saved value and is non-zero; one
          server self-report line with mode=overlay, rates=vanilla and limitations= the code's count; one client line on
          each console with mode=overlay (admin frameworks=MoodleFramework); the Overlay line once and no zeroing line.
  HUNGER  admin's HUNGER at the second read is above the first, 60 or more game minutes apart, the writer's writes rose
          between them, and no stats.all read in between is below the one before it (vanilla's rise; no writer HUNGER
          set lowered it). Falsifier: no rise, writes not rising, or a fall. Unmeasured: under 60 game minutes reached.
  MF      the framework route agrees with its mirror at every arrived read: moodles.levels.overfull =
          view.classes.overfull = the framework moodle's getLevel() = fullnessLevel(the mirror's stomachMass), route
          "framework"; the server mass passes 730 g and 1100 g. A reading under Nutrition Makes Sense's id: the plan's
          x252b grades nothing else under it, and the run sheet's S4c table adds this drive (task-4-A-report concern).
          Falsifier: a disagreement at an arrived read. Unmeasured: a threshold never passed (named), or no arrival.
  DRAW    the on-screen drawing: unmeasured by the driver (Angus's eye, in the reading guide).
  Z       no mod error line; admin not parked; the server alive.

DEVIATIONS from the run sheet's x252b text and amendments, stated before the run:
  1. TKX_StudyFoods is in the profile (the run sheet's S4c line omits it): the MoodleFramework drive is "the same drive"
     as S4a's, which eats TKX.Mixed650.
  2. The HUNGER phase reads stats.all at every clock poll as well as at its ends, and grades the series as never
     falling (a writer HUNGER set in Overlay would show as a step down; vanilla's rise only climbs).
  3. The MoodleFramework drive is graded on the harness's reads; the drawing is not (DRAW is unmeasured).
PRE-RUN EDITS after the Opus review of 4d5e1c3e (the driver had not run):
  4. The MF drive runs at true multiplier SLOW_MULT (0.1), read before and restored in a finally as x401's B1 does, so
     the stomach does not empty between intakes: a networked eat ends in real time (#3766).
  5. Every eat.action and drink.action reply is tested as spawned != "found" ("found" or "client", a string,
     PZTestKit_Client.lua:287-292); the first other reply sets P["void"] = "<label>: spawned=<value>", stops the drive,
     and the MF grade is void.
  6. PROBE_RX is applied to the self-report, zeroing, Overlay and NMS greps only (grep_noecho probe=True); Z's mod-error
     filter drops the bus echo (ECHO_RX) and a line that opens with a command's name (CMD_ECHO_RX) and keeps a real mod
     error that mentions requestMirror or ModData.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time. 4. A session killed
by the host is reported, and its measured phases are never re-run to replace their figures (ruling H2-1).
"""
import ctypes
import glob
import hashlib
import importlib.util
import json
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


PROFILE = "x40-overlay"
PREFIX = "x403"
SESSION = ("Plan 11b Task 4, session S4c (x403): the 1.0.0 release in Overlay beside a Nutrition Makes Sense stand-in "
           "on fixture two -- the one warning, the rates left vanilla, admin's HUNGER rising across 60 game minutes "
           "while the writer runs, and the overfull moodle on the MoodleFramework route; one boot of " + PROFILE)
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert PROFILE == "x40-overlay", f"PROFILE {PROFILE} is not this driver's"
ARTIFACT = "overlay.json"
MANIFEST_NAME = "MANIFEST.json"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (ADMIN, BOB)
USERS = ("admin", "bob")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_OUT = "release/plan11-x40"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
WRITER_REL = "common/media/lua/server/NR_Server_Writer.lua"
STUB_DIR = "testing/experiments/TKX_NmsStub"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_COMMITS = {"016dce05": "a ghost run restores its carrier's macros; time.snapshot reports the true multiplier",
                   "07c27dc4": "the store probe formats tiny magnitudes with tostring (Kahlua %g hangs below 1e-292)",
                   "b932cbb2": "moodle.watch (client) and moodle.level (server), Plan 11b Task 1 H1 and H2"}
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": (
        "-- ---- Plan 11b Task 2 fix: a ghost run restores the carrier's macros ----",              # 016dce05
        "g.rec.reconcile.baseline = NR.kernel.reconcile.baselineAfter(pre)",                       # 016dce05
        'TK.call(nut, "setCalories", pre.calories)',                                               # 016dce05
        'if type(v) == "number" and v ~= 0 and math.abs(v) < 1e-280 then return tostring(v) end '
        '-- Kahlua %g hangs below ~1e-292',                                                        # 07c27dc4
        'TK.register("moodle.level", function(argv)'),                                             # b932cbb2
    "PZTestKit_Client.lua": (
        'TK.register("moodle.watch", function(argv)',),                                            # b932cbb2
}
NR = "NutritionRevamp"
EXPECT_VERSION = "1.0.0"
EXPECT_MODE = "overlay"
VANILLA_HUNGER_RATE = 9.6e-6        # #0470 (42.20.4; re-read on 42.21: holds)
RATE_TOL = 1e-12
RATE_KEYS = ("HungerIncrease", "HungerIncreaseWhenWellFed", "HungerIncreaseWhileAsleep", "HungerIncreaseWhenExercise",
             "ThirstIncrease", "ThirstSleepingIncrease", "FatigueIncrease")      # NR_Server_Writer.lua W.RATE_KEYS
# N: the HUNGER rise
N_GAME_MIN = 60.0
N_CAP_S = 75.0                      # 60 game minutes are 37.5 s of wall at DayLength 1
N_POLL_S = 0.5
# MF: the overfull drive (x401's)
MIX650 = "TKX.Mixed650"
WATER_ITEM, WATER_FLUID, WATER_L = "Base.WaterBottle", "Water", 1.0
CAP_MAX_G, CAP_HARD_G = 730.0, 1100.0         # K.stomach.CAPACITY_MAX_G, CAPACITY_HARD_G
DISCOMFORT_MAX = 100.0                        # K.satiety.DISCOMFORT_MAX
OVERFULL_AT = (100.0 / 3, 200.0 / 3, 100.0)   # K.view.OVERFULL_AT
STOMACH_PARTS = ("stomach.liquid", "stomach.buffer.water", "stomach.buffer.proteins", "stomach.buffer.carbs",
                 "stomach.buffer.lipids", "stomach.buffer.fibre")
ARRIVE_CAP_S = 8.0
REQUEST_GAP_S = 5.5                           # past NR_Server_Bus.lua REQUEST_GAP_MS (5000)
DRINK_CAP_S = 60.0
LAND_CAP_S = 30.0
# spawns
SPAWN_WAIT_S = 2.5
SEEN_CAP_S = 10.0
# liveness and the wall budget
PING_TIMEOUT_S = 5
BUDGET_S = 840.0
PHASE_EST_S = {"S0": 20.0, "N": 95.0, "MF": 90.0}
SLOW_MULT = 0.1                    # the MF drive's true multiplier (DEVIATION 4), as x401's B1 and OF
S0_WAIT_S = 90.0
MIN_RUNS = 4
MIN_FREE_GB = 12.0
RESULT_WAIT_S = 30.0
LOG_LIMIT = 400
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
PROBE_NAMES = (r"(?:lua\.(?:read|global|call|setpath)|stats\.all|time\.(?:snapshot|multiplier)|moodle\.(?:watch|level)|"
               r"event\.watch|minute\.ring|item\.get|witness\.fields|foodtimer\.set|eat\.action|drink\.action|"
               r"fluid\.fill|water\.take|action\.cancel|additem|settimespeed|requestMirror|ModData)")
PROBE_RX = re.compile(r"\b" + PROBE_NAMES)
                                            # this driver's own probe and command names, excluded from the self-report,
                                            # zeroing, Overlay and NMS greps only (grep_noecho probe=True); never from Z's
                                            # mod-error filter, which drops the bus echo and the exact command echo form
CMD_ECHO_RX = re.compile(r"^\s*" + PROBE_NAMES + r"(?:\s|$)")
                                            # a line that is a bare echo of one command: it opens with the command's name
SELF_SRV_RX = re.compile(r"NutritionRevamp v(\S+) build (\S+) side=server (.*)")
SELF_CLI_RX = re.compile(r"NutritionRevamp v(\S+) build (\S+) side=client (.*)")
PAIR_RX = re.compile(r"(\w+)=(\S+)")
ZERO_RX = re.compile(r"writer: vanilla's hunger, thirst and fatigue rates saved and zeroed at boot \(Mode 1\)")
OVERLAY_RX = re.compile(r"writer: Mode 2 \(Overlay\)")
NMS_RX = re.compile(r"Nutrition Makes Sense is loaded")
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")
LIMIT_ADD_RX = re.compile(r"^W\.limitations\[#W\.limitations \+ 1\]\s*=")
INTAKE_LANDED = f"{NR}.server.intake.stats.landed"
INTAKE_PATHS = (f"{NR}.server.intake.stats.eats", INTAKE_LANDED, f"{NR}.server.intake.stats.sips",
                f"{NR}.server.intake.stats.worldSips", f"{NR}.server.intake.stats.failures",
                f"{NR}.server.writer.stats.writes", f"{NR}.server.writer.stats.sips")
WRITES = f"{NR}.server.writer.stats.writes"


PRED = {
    "STAGE": {"staged MANIFEST": "equals release_pack.manifest(mod/NutritionRevamp) on a clean mod/ tree (HEAD's)",
              "staged files": "hash to the staged MANIFEST", "deployed copies": "hash to the staged MANIFEST",
              "falsifier": "any difference (the boot is refused before it starts)"},
    "V": {"verify rows": "all ok"},
    "NMS": {"`Nutrition Makes Sense is loaded` lines in the server log": 1, "writer.stats.nms": True,
            "falsifier": "any other count, or the flag false"},
    "N": {"writer.zeroed": False, "writer.mode": 2,
          "vanillaRate(HungerIncrease)": f"{VANILLA_HUNGER_RATE} within {RATE_TOL} (#0470)",
          "ZomboidGlobals.HungerIncrease": f"{VANILLA_HUNGER_RATE} within {RATE_TOL}",
          "live rates": "each equals its saved value, non-zero",
          "server self-report": {"lines": 1, "version": EXPECT_VERSION, "mode": EXPECT_MODE, "rates": "vanilla",
                                 "limitations": "the code's count"},
          "client lines": "one per console, mode=overlay; admin frameworks=MoodleFramework",
          "Overlay line": 1, "zeroing lines": 0, "falsifier": "any of these off"},
    "HUNGER": {"HUNGER": "rises across >= 60 game minutes", "writer.stats.writes": "rises",
               "series": "never falls between consecutive stats.all reads",
               "falsifier": "no rise, writes not rising, or a fall", "unmeasured": "under 60 game minutes reached"},
    "MF": {"each arrived read": "levels.overfull = view.classes.overfull = the framework moodle's getLevel() = "
                                "fullnessLevel(mirror stomachMass); route framework",
           "server mass": "passes 730 g and 1100 g",
           "note": "a reading under Nutrition Makes Sense's id (the plan grades nothing else there)",
           "falsifier": "a disagreement at an arrived read",
           "unmeasured": "a threshold never passed (named), or no arrival"},
    "DRAW": {"on-screen drawing": "not a harness reading: Angus's eye on the -debug client, in the reading guide"},
    "Z": {"mod_error": "none", "admin_lua_error": False, "players": "answers a list"},
}

# session state (set in main)
prof = rec_fx = run_id = run_dir = path = tl = None
t0 = time.time()
server, clients, started = None, {}, []
cur_phase = {"name": "pre"}
bus = {"dead": None}
copied = []
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


def grep_noecho(log, rx, limit, probe=True):
    hits_, skipped = [], 0
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not rx.search(line):
                    continue
                if ECHO_RX.search(line) or (probe and PROBE_RX.search(line)):
                    skipped += 1
                    continue
                hits_.append(line.strip()[:2000])
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
    """The server bus stopped answering; the phase ends and every later server step is skipped."""


STALL_RX = re.compile(r"^(?:TimeoutError|RuntimeError)\b")


def stalled(v):
    return isinstance(v, dict) and isinstance(v.get("error"), str) and STALL_RX.match(v["error"]) is not None


def set_dead(tag):
    if not bus["dead"]:
        bus["dead"] = tag
        out["abort"] = f"server bus dead after {tag}"
        note(out["abort"])
        if tl is not None:
            tl.mark("error", detail=out["abort"][:200])


def ping(tag):
    """The bus liveness probe: True only when the server answers pong inside PING_TIMEOUT_S."""
    if bus["dead"]:
        return False
    r = step(tag, SRV, "ping", timeout=PING_TIMEOUT_S, liveness=False)
    if r.get("ack") == "pong":
        return True
    set_dead(tag)
    return False


def step(name, side, cmd, args="", timeout=30, liveness=True):
    t_before, e_before = wall(), time.time()
    if side == SRV and bus["dead"]:
        row = {"step": name, "side": side, "cmd": cmd, "args": args, "phase": cur_phase["name"],
               "wall_before": t_before, "wall_after": t_before, "epoch_ms_before": int(e_before * 1000),
               "epoch_ms_after": int(e_before * 1000), "took": 0.0, "skipped": True,
               "ack": {"error": f"skipped: server bus dead after {bus['dead']}"}}
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
            set_dead(name)
            raise BusDead(out["abort"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def keep(r):
    a = dict(ack(r))
    if "wall" in a:
        a["ack_wall"] = a["wall"]              # the answering side's own wall (getTimestampMs), kept beside the driver's
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


def parked():
    c = clients.get("admin") if isinstance(clients, dict) else None
    return c is not None and "lua_error" in getattr(c, "seen", {})


def lread(side, root, paths, tag):
    return keep(step(tag, side, "lua.read", " ".join([root] + list(paths))))


def vals(a):
    return a.get("values") or {}


def snap(tag, side=SRV):
    return keep(step(tag, side, "time.snapshot"))


def wait_doc(name, after, side=SRV, timeout=RESULT_WAIT_S):
    if side == SRV and bus["dead"]:
        note(f"result {name} on {side}: skipped, server bus dead after {bus['dead']}")
        return None
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
    bus_was_dead = bus["dead"]
    try:
        fn()
    except BusDead as e:
        out["phase_walls"][name]["bus_dead"] = str(e)
        note(f"phase {name} ended: {e}")
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        if tl is not None:
            tl.mark("error", in_phase=name, detail=str(e)[:200])  # pre-run: phase= collided with Timeline.mark(phase, ...) (x402 fix, 05dd5c4b)
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    if bus["dead"] and not bus_was_dead and not out["phase_walls"][name].get("bus_dead"):
        out["phase_walls"][name]["bus_dead"] = f"server bus dead after {bus['dead']}"
    out["phase_walls"][name]["end"] = wall()
    persist()


def rcon(cmd, tag):
    t_before, e_before = wall(), time.time()
    if bus["dead"]:
        ok, rep = False, f"skipped: server bus dead after {bus['dead']}"
        row = {"step": tag, "side": SRV, "cmd": "rcon", "args": cmd, "phase": cur_phase["name"],
               "wall_before": t_before, "wall_after": t_before, "epoch_ms_before": int(e_before * 1000),
               "epoch_ms_after": int(e_before * 1000), "skipped": True, "ack": {"ok": ok, "reply": rep}}
        out["steps"].append(row)
        return {"cmd": cmd, "ok": ok, "reply": rep, "wall": t_before, "skipped": True}
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
    return {"cmd": cmd, "ok": ok, "reply": str(rep)[:300], "wall": t_before}


def why(a):
    for k in ("error", "err", "reason", "raw"):
        if a.get(k) is not None:
            return a.get(k)
    return None


def over_budget(extra=0.0):
    return wall() + extra > BUDGET_S


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def fmtnum(v):
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)) and float(v) == int(v) and abs(v) < 1e15:
        return str(int(v))
    return repr(float(v))


def as_list(x):
    """A Lua array as the bus encodes it: a list, a dict keyed "1".."n", or {} when empty."""
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        ks = sorted((k for k in x if str(k).isdigit()), key=lambda k: int(k))
        return [x[k] for k in ks]
    return []


def phase_dead(name):
    return bool(g(out, "phase_walls", name, "bus_dead"))


# ---------------------------------------------------------------- the model's own formulas (for the predictions)
def fullness_level(mass):
    """K.view.fullnessLevel: 0 at or under 730 g, else 1 + the rung of the discomfort on OVERFULL_AT."""
    m = num(mass)
    if m is None or m != m or m == float("inf"):
        return 0
    d = DISCOMFORT_MAX * min(1.0, max(0.0, (m - CAP_MAX_G) / (CAP_HARD_G - CAP_MAX_G)))
    if d <= 0:
        return 0
    return 1 + sum(1 for a in OVERFULL_AT if d >= a)


def stomach_mass(v):
    parts = [num(v.get(p)) for p in STOMACH_PARTS]
    if any(x is None for x in parts):
        return None
    return sum(parts)


# ---------------------------------------------------------------- the stage check (before the boot)
def load_release_pack():
    spec = importlib.util.spec_from_file_location("x403_release_pack", os.path.join(REPO, "tools", "release_pack.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def manifest_diff(a, b):
    a, b = a or {}, b or {}
    return {"only_a": sorted(set(a) - set(b))[:20], "only_b": sorted(set(b) - set(a))[:20],
            "differ": sorted(k for k in set(a) & set(b) if a[k] != b[k])[:20]}


def static_limits(text):
    """The writer's limitations count off its source: the strings in the `limitations = {` block plus each
    `W.limitations[#W.limitations + 1] =` line. None when the block is not found."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if re.match(r"^\s*limitations\s*=\s*\{\s*$", ln)), None)
    if start is None:
        return None
    indent = len(lines[start]) - len(lines[start].lstrip())
    n, end = 0, None
    for j in range(start + 1, len(lines)):
        ln = lines[j]
        if re.match(r"^\s*\},?\s*$", ln) and len(ln) - len(ln.lstrip()) == indent:
            end = j
            break
        if re.match(r'^\s*"', ln):
            n += 1
    if end is None:
        return None
    return n + sum(1 for ln in lines if LIMIT_ADD_RX.match(ln))


def stage_check():
    S = {"stage_root": STAGE_ROOT, "head": git_say("rev-parse", "HEAD"), "mod_commit": git_say("log", "-1", "--format=%h",
                                                                                                 "--", MOD_DIR)}
    dirty, why_ = git_dirty(MOD_DIR)
    S["mod_dirty"], S["mod_dirty_note"] = dirty, why_
    mpath = os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME)
    try:
        S["manifest_sha256"] = sha256_file(mpath)
        with open(mpath, encoding="utf-8") as fh:
            staged = json.load(fh)
    except (OSError, ValueError) as e:
        S["error"] = f"staged MANIFEST unreadable: {type(e).__name__}: {e}"
        S["ok"] = False
        return S, None
    try:
        rp = load_release_pack()
        head_man = rp.manifest(os.path.join(REPO, MOD_DIR))
        files_man = rp.manifest(os.path.join(REPO, STAGE_MOD))
    except Exception as e:                     # noqa: BLE001
        S["error"] = f"release_pack.manifest failed: {type(e).__name__}: {e}"
        S["ok"] = False
        return S, staged
    S["head_equal"] = head_man == staged
    S["files_equal"] = files_man == staged
    S["entries"] = len(staged)
    if not S["head_equal"]:
        S["head_diff"] = manifest_diff(staged, head_man)
    if not S["files_equal"]:
        S["files_diff"] = manifest_diff(staged, files_man)
    try:
        with open(os.path.join(REPO, STAGE_MOD, WRITER_REL), encoding="utf-8", errors="replace") as fh:
            S["static_limitations"] = static_limits(fh.read())
    except OSError as e:
        S["static_limitations"] = None
        S["writer_read_error"] = f"{type(e).__name__}: {e}"
    try:
        info = {}
        for p in glob.glob(os.path.join(REPO, STAGE_MOD, "*", "mod.info")):
            with open(p, encoding="utf-8", errors="replace") as fh:
                for ln in fh.read().splitlines():
                    if "=" in ln:
                        k, v = ln.split("=", 1)
                        info.setdefault(os.path.basename(os.path.dirname(p)), {})[k.strip()] = v.strip()
        S["mod_info"] = {d: {k: v for k, v in kv.items() if k in ("id", "modversion", "versionMin")}
                         for d, kv in info.items()}
    except OSError as e:
        S["mod_info_error"] = f"{type(e).__name__}: {e}"
    S["ok"] = dirty is False and S["head_equal"] and S["files_equal"]
    return S, staged


def deployed_check(staged):
    """Every NutritionRevamp folder the harness placed in the run (server and clients) hashed against the MANIFEST."""
    D = {}
    try:
        rp = load_release_pack()
    except Exception as e:                     # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}
    for cand in sorted(glob.glob(os.path.join(run_dir, "**", "mods", "NutritionRevamp"), recursive=True)):
        if not os.path.isdir(cand):
            continue
        rel = os.path.relpath(cand, run_dir).replace(os.sep, "/")
        try:
            m = rp.manifest(cand)
            D[rel] = {"equal": m == staged, "entries": len(m)}
            if m != staged:
                D[rel]["diff"] = manifest_diff(staged, m)
        except Exception as e:                 # noqa: BLE001
            D[rel] = {"error": f"{type(e).__name__}: {e}"}
    return D


def harness_markers(root, glob_prefix):
    """{file: {marker: found}} for each harness file in HARNESS_MARKERS under root, each file read once."""
    found = {}
    for fname, markers in HARNESS_MARKERS.items():
        for cand in sorted(glob.glob(os.path.join(root, glob_prefix, fname), recursive=True)):
            try:
                with open(cand, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()       # read once: a second fh.read() is empty (x391f, ruling B3-2)
                found[os.path.relpath(cand, root).replace(os.sep, "/")] = {m: (m in text) for m in markers}
            except OSError as e:
                found[os.path.relpath(cand, root).replace(os.sep, "/")] = {"error": f"{type(e).__name__}: {e}"}
    return found


def markers_ok(found):
    names = {os.path.basename(k) for k in found}
    if names != set(HARNESS_MARKERS):
        return False
    return all(isinstance(v, dict) and v and all(x is True for x in v.values()) for v in found.values())


# ---------------------------------------------------------------- helpers for the phases
def intake(tag):
    a = lread(SRV, "_G", INTAKE_PATHS, tag)
    v = vals(a)
    r = {k.rsplit(".", 1)[-1] if ".intake." in k else k.replace(f"{NR}.server.", ""): num(v.get(k)) for k in INTAKE_PATHS}
    r["wall"] = a.get("wall")
    return r


def item_get(user, ftype, tag):
    a = keep(step(tag, SRV, "item.get", f"{user} {ftype}"))
    return {"id": a.get("id"), "fullType": a.get("fullType"), "calories": a.get("calories"), "raw": a.get("raw"),
            "error": a.get("error"), "wall": a.get("wall")}


def spawn_confirmed(user, ftype, n, tag):
    """RCON additem confirmed by the server's item.get (an id, none before) and the client's witness (ruling T2-11).
    An unconfirmed spawn voids its phase; there is never a client spawn."""
    R = {"user": user, "fullType": ftype, "n": n}
    R["before"] = item_get(user, ftype, f"{tag}_get0")
    R["additem"] = rcon(f'additem "{user}" "{ftype}" {int(n)}', f"{tag}_additem")
    time.sleep(SPAWN_WAIT_S)
    R["after"] = item_get(user, ftype, f"{tag}_get1")
    R["leftover_before"] = R["before"].get("id") is not None
    R["server_confirmed"] = R["after"].get("id") is not None and not R["leftover_before"]
    R["client_seen"] = False
    if R["server_confirmed"]:
        end = time.time() + SEEN_CAP_S
        while time.time() < end and not over_budget():
            w = keep(step(f"{tag}_seen", f"client:{user}", "witness.fields", f"item {user}/{ftype} getID"))
            if isinstance(w.get("resolved"), str) and w.get("resolved"):
                R["client_seen"] = True
                R["seen"] = {k: w.get(k) for k in ("resolved", "fields", "wall")}
                break
            time.sleep(1.0)
    R["confirmed"] = R["server_confirmed"] and R["client_seen"]
    if R["confirmed"]:
        out["world_changes"]["left_in_place"].append(f"RCON additem {ftype} x{n} to {user}")
    else:
        R["void_reason"] = ("a leftover before the spawn" if R["leftover_before"] else
                            "no server id after the spawn" if not R["server_confirmed"] else "the client never saw it")
        note(f"{tag}: spawn of {ftype} for {user} not confirmed ({R['void_reason']})")
    return R


def eat(user, ftype, tag):
    """foodtimer 0, eat.action <ftype> 1 on the user's client, landed polled until it rises (LAND_CAP_S)."""
    row = {"user": user, "food": ftype, "landed": False}
    row["foodtimer"] = keep(step(f"{tag}_foodtimer", SRV, "foodtimer.set", f"{user} 0")).get("after")
    b = intake(f"{tag}_before")
    row["before"] = b
    q = keep(step(f"{tag}_eat", f"client:{user}", "eat.action", f"{ftype} 1"))
    row["queued"] = {k: q.get(k) for k in ("queued", "fraction", "spawned", "itemId", "validStart", "maxTime",
                                           "moodleFoodEaten", "wall")}
    if q.get("spawned") != "found":
        # eat.action answers spawned = "found" (the item sat in the inventory) or "client" (a client-side spawn)
        note(f"{tag}: eat.action spawned={q.get('spawned')!r} for {ftype}, not 'found'; the landing is void")
        row["client_spawned"] = f"spawned={q.get('spawned')}"
    if not q.get("queued"):
        row["queue_reply"] = {k: q.get(k) for k in ("raw", "error", "reason")}
        note(f"{tag}: not queued: {str(q)[:300]}")
        return row
    end = time.time() + LAND_CAP_S
    while time.time() < end and not over_budget():
        if parked():
            break
        a = intake(f"{tag}_poll")
        if a.get("landed") is not None and b.get("landed") is not None and a["landed"] > b["landed"]:
            row["landed"] = True
            row["after"] = a
            row["landed_snap"] = snap(f"{tag}_landed_t")
            break
        time.sleep(0.3)
    if not row["landed"]:
        note(f"{tag}: landed did not rise within {LAND_CAP_S} s")
    return row


def drink(user, container, fluid, litres, tag):
    """x363's route: the RCON-spawned container's server copy filled by fluid.fill, drink.action <container> 1, the
    sips polled until they stop rising for 3 polls after a rise (DRINK_CAP_S)."""
    row = {"user": user, "container": container, "fluid": fluid, "litres": litres, "drank": False}
    row["fill"] = keep(step(f"{tag}_fill", SRV, "fluid.fill", f"{user} {container} {fluid} {fmtnum(litres)}"))
    b = intake(f"{tag}_before")
    row["before"] = b
    q = keep(step(f"{tag}_drink", f"client:{user}", "drink.action", f"{container} 1"))
    row["queued"] = {k: q.get(k) for k in ("queued", "percentage", "spawned", "itemId", "filledRatioBefore", "wall")}
    if q.get("spawned") != "found":
        note(f"{tag}: drink.action spawned={q.get('spawned')!r} for {container}, not 'found'; the drink is void")
        row["client_spawned"] = f"spawned={q.get('spawned')}"
    if not q.get("queued"):
        row["queue_reply"] = {k: q.get(k) for k in ("raw", "error", "reason")}
        note(f"{tag}: not queued: {str(q)[:300]}")
        return row
    end = time.time() + DRINK_CAP_S
    last, still, rose = b.get("sips"), 0, False
    while time.time() < end and not over_budget():
        if parked():
            break
        a = intake(f"{tag}_poll")
        s = a.get("sips")
        if s is not None and last is not None and s > last:
            rose, still = True, 0
        elif rose:
            still += 1
        last = s
        if rose and still >= 3:
            break
        time.sleep(0.3)
    row["after"] = intake(f"{tag}_after")
    row["drank"] = rose
    row["sips"] = (num(row["after"].get("sips")) or 0) - (num(b.get("sips")) or 0)
    if not rose:
        note(f"{tag}: sips never rose")
    return row


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    P["ping"] = ping("S0_ping")
    P["players"] = keep(step("S0_players", SRV, "players"))
    P["time"] = {"server": snap("S0_time"), "admin": snap("S0_time_admin", ADMIN), "bob": snap("S0_time_bob", BOB)}
    end = time.time() + S0_WAIT_S
    polls, ok = [], False
    while not over_budget():
        a = lread(SRV, "_G", [f"{NR}.server.minute.stats.runs"], "S0_runs")
        runs = num(vals(a).get(f"{NR}.server.minute.stats.runs"))
        recs = {u: gread(SRV, f"{NR}.server.store.records.{u}", f"S0_rec_{u}") for u in USERS}
        ok = all(r.get("resolved") for r in recs.values()) and runs is not None and runs >= MIN_RUNS
        polls.append({"wall": wall(), "records": {u: r.get("resolved") for u, r in recs.items()}, "runs": runs})
        if ok or time.time() >= end:
            break
        time.sleep(0.5)
    P["wait"] = {"ok": ok, "polls": polls}
    if not ok:
        note("S0: the real players' records or MIN_RUNS were not reached inside S0_WAIT_S")


def phase_N():
    P = out["phases"]["N"] = {"series": []}
    W = f"{NR}.server.writer"
    P["zeroed"] = gread(SRV, f"{W}.zeroed", "N_zeroed")
    P["mode"] = gread(SRV, f"{W}.mode", "N_mode")
    P["nms"] = gread(SRV, f"{W}.stats.nms", "N_nms")
    P["limitations"] = gread(SRV, f"{W}.limitations", "N_limitations")
    P["vanillaRate"] = keep(step("N_vanillaRate", SRV, "lua.call", f"{NR}.vanillaRate HungerIncrease"))
    P["zg_hunger"] = gread(SRV, "ZomboidGlobals.HungerIncrease", "N_zg_hunger")
    paths = [f"{W}.saved.{k}" for k in RATE_KEYS] + [f"ZomboidGlobals.{k}" for k in RATE_KEYS]
    P["rates"] = lread(SRV, "_G", paths, "N_rates")
    P["version"] = {s: lread(s, "_G", [f"{NR}.version", f"{NR}.build"], f"N_version_{s.replace(':', '_')}")
                    for s in (SRV, ADMIN, BOB)}
    P["route"] = gread(ADMIN, f"{NR}.client.moodles.route", "N_route")
    P["w0"] = num(vals(lread(SRV, "_G", [WRITES], "N_w0")).get(WRITES))
    s0 = keep(step("N_stats0", SRV, "stats.all", "admin"))
    P["h0"] = num((s0.get("stats") or {}).get("Hunger"))
    P["a0"] = num(s0.get("worldAge"))
    P["series"].append({"wall": s0.get("wall"), "age": P["a0"], "H": P["h0"]})
    end = time.time() + N_CAP_S
    P["reached"] = False
    while time.time() < end and not over_budget(5.0):
        time.sleep(N_POLL_S)
        s = keep(step("N_stats", SRV, "stats.all", "admin"))
        row = {"wall": s.get("wall"), "age": num(s.get("worldAge")), "H": num((s.get("stats") or {}).get("Hunger"))}
        P["series"].append(row)
        if P["a0"] is not None and row["age"] is not None and (row["age"] - P["a0"]) * 60.0 >= N_GAME_MIN:
            P["reached"] = True
            break
    last = P["series"][-1]
    P["h1"], P["a1"] = last.get("H"), last.get("age")
    P["w1"] = num(vals(lread(SRV, "_G", [WRITES], "N_w1")).get(WRITES))


def phase_MF():
    """The overfull drive on the framework route at true multiplier SLOW_MULT (DEVIATION 4), read before and restored
    in a finally."""
    P = out["phases"]["MF"] = {"steps": [], "intakes": []}
    P["mult_before"] = snap("MF_mult0")
    m0 = num(P["mult_before"].get("trueMult"))
    P["restore_to"] = m0 if m0 is not None else 1.0
    try:
        P["slow"] = keep(step("MF_slow", SRV, "time.multiplier", fmtnum(SLOW_MULT)))
        P["mult_slow"] = snap("MF_mult_slow")
        mf_drive(P)
    finally:
        P["restore"] = keep(step("MF_restore", SRV, "time.multiplier", fmtnum(P["restore_to"])))
        P["mult_after"] = snap("MF_mult1")


def mf_drive(P):
    rc0 = num(gread(ADMIN, f"{NR}.client.received", "MF_rc0").get("value"))
    last_req = None
    plan = (("eat1", "eat", MIX650), ("eat2", "eat", MIX650), ("drink", "drink", WATER_ITEM))
    for label, kind, ftype in plan:
        if over_budget(15.0):
            note(f"MF: {label} skipped at the wall budget")
            break
        sp = spawn_confirmed("admin", ftype, 1, f"MF_{label}_spawn")
        it = {"label": label, "kind": kind, "spawn": sp}
        P["intakes"].append(it)
        if not sp["confirmed"]:
            P["void"] = f"{label}: spawn not confirmed"
            break
        if kind == "eat":
            it["eat"] = eat("admin", ftype, f"MF_{label}")
            ok = it["eat"].get("landed") and not it["eat"].get("client_spawned")
        else:
            it["drink"] = drink("admin", ftype, WATER_FLUID, WATER_L, f"MF_{label}")
            ok = it["drink"].get("drank") and not it["drink"].get("client_spawned")
        cs = (it.get("eat") or it.get("drink") or {}).get("client_spawned")
        if cs:
            P["void"] = f"{label}: {cs}"
            P["void_spawn"] = True
            note(f"MF: {P['void']}, not 'found'; the drive stops")
            break
        if not ok:
            note(f"MF: {label} did not land")
        if last_req is not None and time.time() - last_req < REQUEST_GAP_S:
            time.sleep(REQUEST_GAP_S - (time.time() - last_req))
        last_req = time.time()
        R, rc0 = overfull_read(f"MF_{label}_read", rc0)
        R["after"] = label
        P["steps"].append(R)
    out["world_changes"]["left_in_place"].append("MF: two TKX.Mixed650 eaten and a WaterBottle drunk by admin")


def overfull_read(tag, last_received):
    R = {"tag": tag}
    sv = vals(lread(SRV, "record:admin", list(STOMACH_PARTS), f"{tag}_srv"))
    R["server_parts"] = sv
    R["server_mass"] = stomach_mass(sv)
    R["server_level"] = fullness_level(R["server_mass"]) if R["server_mass"] is not None else None
    sig = gread(SRV, f"{NR}.server.bus.lastSig.admin", f"{tag}_sig")
    R["lastSig"] = val(sig)
    s = num(R["lastSig"])
    R["lastSig_level"] = int(s // 10000) % 10 if s is not None else None
    R["request"] = keep(step(f"{tag}_req", ADMIN, "lua.call", f"{NR}.client.requestMirror"))
    paths = ["received", "mirror.stomachMass", "moodles.levels.overfull", "view.classes.overfull", "moodles.route"]
    end = time.time() + ARRIVE_CAP_S
    R["arrived"] = False
    c = {}
    while time.time() < end and not over_budget():
        a = lread(ADMIN, f"{NR}.client", paths, f"{tag}_cli")
        c = vals(a)
        rc = num(c.get("received"))
        if rc is not None and last_received is not None and rc > last_received:
            R["arrived"] = True
            break
        time.sleep(0.5)
    R["client"] = c
    R["probe"] = keep(step(f"{tag}_probe", ADMIN, "lua.call", f"{NR}.client.moodles.probe overfull"))
    rc = num(c.get("received"))
    return R, (rc if rc is not None else last_received)


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["bus_dead"] = bus["dead"]
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)
                                   and not CMD_ECHO_RX.search(e)][:20]
    P["admin_parked"] = parked()
    P["mem"] = mem("Z")
    P["players"] = keep(step("Z_players", SRV, "players"))
    P["time"] = snap("Z_time")
    P["writer"] = vals(lread(SRV, "_G", [f"{NR}.server.writer.stats.{k}" for k in ("writes", "failures", "sips",
                                                                                   "skipped", "seeded", "guarded")],
                             "Z_writer"))


PHASES = (("S0", phase_S0), ("N", phase_N), ("MF", phase_MF))


def body():
    out["budget"] = {"BUDGET_S": BUDGET_S, "checks": []}
    for name, fn in PHASES:
        if bus["dead"]:
            break
        est = PHASE_EST_S.get(name, 0.0)
        out["budget"]["checks"].append({"phase": name, "wall": wall(), "estimate": est})
        if over_budget(est):
            out["abort"] = f"wall budget: {name} (estimate {est} s) would end past {BUDGET_S} s at wall {wall()} s"
            note(out["abort"])
            break
        run_phase(name, fn)
        if parked():
            out["abort"] = f"admin parked in the debugger after phase {name}"
            break
    run_phase("Z", phase_Z)


def read_logs(every):
    L = out["logs"] = {"patterns": {"log": LOG_RX.pattern, "self_server": SELF_SRV_RX.pattern,
                                    "self_client": SELF_CLI_RX.pattern, "zero": ZERO_RX.pattern,
                                    "overlay": OVERLAY_RX.pattern, "nms": NMS_RX.pattern,
                                    "echo_excluded": ECHO_RX.pattern, "probe_excluded": PROBE_RX.pattern},
                       "clients": {}}
    if server is not None:
        lp = server.log_path
        L["server"] = {k: grep_noecho(lp, rx, LOG_LIMIT, probe=k != "lines")[0] for k, rx in
                       (("self", SELF_SRV_RX), ("zero", ZERO_RX), ("overlay", OVERLAY_RX), ("nms", NMS_RX),
                        ("lines", LOG_RX))}
    for c in every:
        u = getattr(c, "username", "?")
        L["clients"].setdefault(u, []).append({"console": os.path.relpath(c.console, run_dir),
                                               "self": grep_noecho(c.console, SELF_CLI_RX, 20)[0],
                                               "lines": grep_noecho(c.console, LOG_RX, 60, probe=False)[0]})


def parse_self(line, rx):
    m = rx.search(line or "")
    if not m:
        return None
    d = dict(PAIR_RX.findall(m.group(0)))       # side= sits in the fixed part of the pattern
    d["version"], d["build"] = m.group(1), m.group(2)
    return d


# ---------------------------------------------------------------- grading
def grade_stage():
    S = out.get("stage") or {}
    D = out.get("deployed") or {}
    dep_ok = bool(D) and all(isinstance(v, dict) and v.get("equal") is True for v in D.values()) \
        if isinstance(D, dict) and "error" not in D else False
    obs = {"head_equal": S.get("head_equal"), "files_equal": S.get("files_equal"), "mod_dirty": S.get("mod_dirty"),
           "manifest_sha256": S.get("manifest_sha256"), "head": S.get("head"),
           "deployed": {k: v.get("equal") if isinstance(v, dict) else v for k, v in D.items()}}
    if not S.get("ok"):
        grade("STAGE", PRED["STAGE"], obs, "falsified", PRED["STAGE"]["falsifier"])
    elif not D:
        grade("STAGE", PRED["STAGE"], obs, "unmeasured", "no deployed copy read (no boot)")
    else:
        grade("STAGE", PRED["STAGE"], obs, "as_predicted" if dep_ok else "falsified", "a deployed copy differs")


def grade_OF(route="own", phase_name="OF", phase_tag="OF"):
    P = out["phases"].get(phase_tag) or {}
    rows, bad = [], []
    for R in P.get("steps") or []:
        c = R.get("client") or {}
        m = num(c.get("mirror.stomachMass"))
        want = fullness_level(m) if m is not None else None
        r = {"after": R.get("after"), "server_mass": R.get("server_mass"), "server_level": R.get("server_level"),
             "lastSig": R.get("lastSig"), "lastSig_level": R.get("lastSig_level"), "arrived": R.get("arrived"),
             "mirror_mass": m, "want": want, "levels": num(c.get("moodles.levels.overfull")),
             "classes": num(c.get("view.classes.overfull")), "route": c.get("moodles.route"),
             "probe": [g(R, "probe", "r1"), g(R, "probe", "r2"), g(R, "probe", "r3")]}
        if R.get("arrived"):
            ok = (want is not None and r["levels"] == want and r["classes"] == want and num(r["probe"][0]) == want
                  and r["route"] == route and r["probe"][2] == route)
            r["agrees"] = ok
            if not ok:
                bad.append(r["after"])
        rows.append(r)
    masses = [r["server_mass"] for r in rows if r["server_mass"] is not None]
    passed = {"730": any(m > CAP_MAX_G for m in masses), "1100": any(m >= CAP_HARD_G for m in masses)}
    arrived = [r for r in rows if r.get("arrived")]
    obs = {"rows": rows, "passed": passed, "void": P.get("void"), "route": route}
    out["summaries"][phase_name] = obs
    if not P:
        grade(phase_name, PRED[phase_name], None, "void" if phase_dead(phase_tag) or bus["dead"] else "unmeasured",
              f"phase {phase_tag} not run")
    elif phase_dead(phase_tag):
        grade(phase_name, PRED[phase_name], obs, "void", "the server bus died inside the drive")
    elif bad:
        grade(phase_name, PRED[phase_name], obs, "falsified", PRED[phase_name]["falsifier"], {"bad": bad})
    elif P.get("void_spawn") or (P.get("void") and not arrived):
        grade(phase_name, PRED[phase_name], obs, "void", P.get("void"))
    elif not arrived or not all(passed.values()):
        grade(phase_name, PRED[phase_name], obs, "unmeasured", PRED[phase_name]["unmeasured"],
              {"thresholds_not_passed": [k for k, v in passed.items() if not v]})
    else:
        grade(phase_name, PRED[phase_name], obs, "as_predicted", PRED[phase_name]["falsifier"])


def grade_N():
    P = out["phases"].get("N") or {}
    Ls = g(out, "logs", "server") or {}
    lines = Ls.get("self") or []
    srv = parse_self(lines[0], SELF_SRV_RX) if lines else None
    cli = {}
    for u, rows in (g(out, "logs", "clients") or {}).items():
        sl = [ln for r in rows for ln in (r.get("self") or [])]
        cli[u] = {"lines": len(sl), "parsed": parse_self(sl[0], SELF_CLI_RX) if sl else None}
    live_limits = num(g(P, "limitations", "keyCount"))
    static = g(out, "stage", "static_limitations")
    rates = g(P, "rates", "values") or {}
    saved = {k: num(rates.get(f"{NR}.server.writer.saved.{k}")) for k in RATE_KEYS}
    live = {k: num(rates.get(f"ZomboidGlobals.{k}")) for k in RATE_KEYS}
    vr = num(g(P, "vanillaRate", "r1"))
    zg = num(val(P.get("zg_hunger")))
    nms_lines = Ls.get("nms") or []
    obs = {"server_lines": len(lines), "server": srv, "clients": cli, "overlay_lines": len(Ls.get("overlay") or []),
           "zero_lines": len(Ls.get("zero") or []), "nms_lines": nms_lines, "zeroed": val(P.get("zeroed")),
           "mode": val(P.get("mode")), "nms_flag": val(P.get("nms")), "limitations_live": live_limits,
           "limitations_static": static, "vanillaRate": vr, "zg_hunger": zg, "saved": saved, "live": live,
           "route": val(P.get("route")),
           "versions": {s: vals(v) for s, v in (P.get("version") or {}).items()}}
    out["summaries"]["N"] = obs
    # NMS: the one warning line and the flag
    if not P:
        grade("NMS", PRED["NMS"], {"nms_lines": nms_lines}, "void" if phase_dead("N") or bus["dead"] else "unmeasured",
              "phase N not run")
    else:
        ok = len(nms_lines) == 1 and obs["nms_flag"] is True
        grade("NMS", PRED["NMS"], {"nms_lines": nms_lines, "nms_flag": obs["nms_flag"]},
              "as_predicted" if ok else "falsified", PRED["NMS"]["falsifier"])
    bad = []
    if len(lines) != 1 or srv is None:
        bad.append("server self-report lines != 1")
    else:
        for k, want in (("version", EXPECT_VERSION), ("side", "server"), ("mode", EXPECT_MODE), ("rates", "vanilla")):
            if srv.get(k) != want:
                bad.append(f"server {k}={srv.get(k)!r}")
        lim = num(srv.get("limitations"))
        if lim is None or live_limits is None or lim != live_limits or (static is not None and lim != static):
            bad.append(f"limitations={srv.get('limitations')!r} live={live_limits} static={static}")
    for u in USERS:
        c = cli.get(u) or {}
        p = c.get("parsed") or {}
        if c.get("lines") != 1:
            bad.append(f"{u} client self-report lines {c.get('lines')}")
        for k, want in (("version", EXPECT_VERSION), ("side", "client"), ("mode", EXPECT_MODE)):
            if p.get(k) != want:
                bad.append(f"{u} {k}={p.get(k)!r}")
    if (g(cli, "admin", "parsed") or {}).get("frameworks") != "MoodleFramework":
        bad.append("admin frameworks not MoodleFramework")
    if obs["overlay_lines"] != 1 or obs["zero_lines"] != 0:
        bad.append(f"overlay lines {obs['overlay_lines']}, zero lines {obs['zero_lines']}")
    if obs["zeroed"] is not False or num(obs["mode"]) != 2:
        bad.append("writer zeroed/mode")
    if vr is None or abs(vr - VANILLA_HUNGER_RATE) > RATE_TOL:
        bad.append(f"vanillaRate {vr}")
    if zg is None or abs(zg - VANILLA_HUNGER_RATE) > RATE_TOL:
        bad.append(f"ZomboidGlobals.HungerIncrease {zg}")
    for k in RATE_KEYS:
        if saved[k] is None or saved[k] == 0 or live[k] != saved[k]:
            bad.append(f"rate {k}: saved {saved[k]} live {live[k]}")
    for s, v in obs["versions"].items():
        if v.get(f"{NR}.version") != EXPECT_VERSION:
            bad.append(f"{s} version {v.get(f'{NR}.version')!r}")
    if not P:
        grade("N", PRED["N"], obs, "void" if phase_dead("N") or bus["dead"] else "unmeasured", "phase N not run")
    else:
        grade("N", PRED["N"], obs, "falsified" if bad else "as_predicted", PRED["N"]["falsifier"], {"bad": bad})
    # HUNGER: vanilla's rise across 60 game minutes while the writer runs
    ser = [r for r in P.get("series") or [] if r.get("H") is not None]
    falls = [{"a": a, "b": b} for a, b in zip(ser, ser[1:]) if b["H"] < a["H"]]
    h0, h1, a0, a1 = P.get("h0"), P.get("h1"), P.get("a0"), P.get("a1")
    w0, w1 = P.get("w0"), P.get("w1")
    span = (a1 - a0) * 60.0 if None not in (a0, a1) else None
    ho = {"h0": h0, "h1": h1, "rise": (h1 - h0) if None not in (h0, h1) else None, "game_min": span,
          "writes": [w0, w1], "writes_delta": (w1 - w0) if None not in (w0, w1) else None, "reads": len(ser),
          "falls": falls[:10], "reached": P.get("reached")}
    out["summaries"]["HUNGER"] = ho
    if not P:
        grade("HUNGER", PRED["HUNGER"], None, "void" if phase_dead("N") or bus["dead"] else "unmeasured",
              "phase N not run")
    elif phase_dead("N"):
        grade("HUNGER", PRED["HUNGER"], ho, "void", "the server bus died inside N")
    elif span is None or span < N_GAME_MIN or None in (h0, h1, w0, w1):
        grade("HUNGER", PRED["HUNGER"], ho, "unmeasured", PRED["HUNGER"]["unmeasured"])
    elif not h1 > h0 or not w1 > w0 or falls:
        grade("HUNGER", PRED["HUNGER"], ho, "falsified", PRED["HUNGER"]["falsifier"])
    else:
        grade("HUNGER", PRED["HUNGER"], ho, "as_predicted", PRED["HUNGER"]["falsifier"])


def safe(name, fn, *a, **kw):
    """One grader under its own guard: a raise is recorded by name and the other graders still run."""
    try:
        fn(*a, **kw)
    except Exception as e:                     # noqa: BLE001
        out.setdefault("grade_errors", {})[name] = {"error": f"{type(e).__name__}: {e}",
                                                  "tb": traceback.format_exc()[-2000:]}


def grade_all():
    safe("grade_stage", grade_stage)
    vr = out.get("verify") or []
    grade("V", PRED["V"], [{k: r.get(k) for k in ("side", "cmd", "args", "ok")} for r in vr],
          ("as_predicted" if all(r.get("ok") for r in vr) else "falsified") if vr else "unmeasured",
          "a verify row not ok")
    safe("grade_N", grade_N)
    safe("grade_OF:MF", grade_OF, route="framework", phase_name="MF", phase_tag="MF")
    grade("DRAW", PRED["DRAW"], None, "unmeasured", "the drawing is not a harness reading (Angus's eye)")
    Z = out["phases"].get("Z") or {}
    if Z:
        pl = g(Z, "players", "raw")
        alive = isinstance(pl, list) and len(pl) > 0
        obs = {"server_mod_error_lines": Z.get("server_mod_error_lines") or [],
               "admin_lua_error": out.get("admin_lua_error"), "players": pl, "server_alive": alive,
               "bus_dead": Z.get("bus_dead")}
        ok = not obs["server_mod_error_lines"] and not obs["admin_lua_error"] and alive
        grade("Z", PRED["Z"], obs, "as_predicted" if ok else "falsified", "a mod error line, admin parked, or no players")
    else:
        grade("Z", PRED["Z"], None, "unmeasured", "phase Z not run")


# ---------------------------------------------------------------- run
def refuse(msg):
    out["error"] = msg
    persist()
    print(msg)
    sys.exit(1)


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
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
        "harness_lua_dirty": git_dirty(LUA_DIR)[0],
        "harness_commits": HARNESS_COMMITS,
        "harness_fixes_are_ancestors": {c: git_say("merge-base", "--is-ancestor", c, "HEAD") == ""
                                        for c in HARNESS_COMMITS},
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "meta": {"staged_mod": STAGE_MOD, "staging": "python tools/release_pack.py stage mod/NutritionRevamp --out "
                                                     "release/plan11-x40 (the controller, after Task 3c)",
                 "stub_note": "TKX_NmsStub is a 42/mod.info with name=, id=NutritionMakesSense and versionMin only; it "
                              "puts the id in the activated-mods list and loads nothing.",
                 "bus_note": "The server answers the bus every 20 ticks (2 s at 10 Hz) or at a minute event "
                             "(PZTestKit_Server.lua's tick poll and its EveryOneMinute poll).",
                 "clock_note": "DayLength 1: a game minute is 0.625 s of wall at true multiplier 1; no time.multiplier "
                               "call in this driver."},
        "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                      if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict,
                                                                             re.Pattern))
                      and k not in ("REPO", "PRED", "PHASES")},
        "predictions": PRED,
        "deviations": [
            "TKX_StudyFoods is in the profile: the MoodleFramework drive is S4a's drive, which eats TKX.Mixed650.",
            "The HUNGER phase reads stats.all at every clock poll and grades the series as never falling.",
            "The MoodleFramework drive is graded on the harness's reads; the drawing is not (DRAW unmeasured).",
        ],
        "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                          "left_in_place": []},
        "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
        "summaries": {}, "memory": [],
    }
    S, staged = stage_check()
    out["stage"] = S
    try:
        with open(os.path.join(REPO, STUB_DIR, "42", "mod.info"), encoding="utf-8") as fh:
            out["meta"]["stub_mod_info"] = fh.read().splitlines()
        out["meta"]["stub_files"] = sorted(os.path.relpath(os.path.join(d, f), os.path.join(REPO, STUB_DIR))
                                           .replace(os.sep, "/") for d, _, fs in os.walk(os.path.join(REPO, STUB_DIR))
                                           for f in fs)
    except OSError as e:
        out["meta"]["stub_error"] = f"{type(e).__name__}: {e}"
    if not doctor_clean:
        refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if not S.get("ok"):
        refuse(f"the staged copy does not match mod/ at HEAD (or mod/ is dirty): {json.dumps(S, default=str)[:1500]}; "
               "not started")
    found = harness_markers(REPO, LUA_DIR + "/**")
    out["meta"]["harness_markers_repo"] = found
    if not markers_ok(found):
        refuse(f"the repository harness lacks a marker of {', '.join(HARNESS_COMMITS)}: {found!r}; not started")
    if not all(out["harness_fixes_are_ancestors"].values()):
        refuse(f"a harness commit is not an ancestor of HEAD: {out['harness_fixes_are_ancestors']!r}; not started")
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
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        out["server_launch_wall"] = wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = wall()
        tl.mark("server_started")
        clients = attach_clients(run_dir, prof, server, rec_fx, tl, started=started)
        tl.mark("session_ready")
        out["session_ready_wall"] = wall()
        out["build"] = server.build
        out["boot_info"] = {"client_debug": {u: getattr(c, "debug", None) for u, c in clients.items()}}
        out["verify"] = verify(prof, server, clients, tl)
        out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                                 **{u: sorted(set(c.mods_not_found)) for u, c in clients.items()}}
        out["deployed"] = deployed_check(staged)
        dm = harness_markers(run_dir, "**/mods/PZTestKit/**")
        out["meta"]["deployed_harness_markers"] = dm
        mem("ready")
        persist()
        if not markers_ok(dm):
            out["abort"] = f"a deployed harness file lacks a marker of {', '.join(HARNESS_COMMITS)}: {dm!r}"
            tl.mark("error", detail=out["abort"][:200])
            print(out["abort"])
        elif not all(isinstance(v, dict) and v.get("equal") is True for v in out["deployed"].values()) \
                or not out["deployed"]:
            out["abort"] = f"a deployed NutritionRevamp copy differs from the staged MANIFEST: {out['deployed']!r}"[:2000]
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
                grade_all()
            except Exception as e:                 # noqa: BLE001
                out["summary_error"] = f"{type(e).__name__}: {e}"
                out["summary_traceback"] = traceback.format_exc()[-3000:]
            out["bus_dead"] = bus["dead"]
            out["copied"] = list(copied)
            out["wall_seconds"] = round(time.time() - t0, 1)
            persist()
            dest_dir = os.path.join(REPO, "testing", "artifacts", run_id)
            try:
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copyfile(path, os.path.join(dest_dir, ARTIFACT))
                for nm in copied:
                    if os.path.isfile(os.path.join(run_dir, nm)):
                        shutil.copyfile(os.path.join(run_dir, nm), os.path.join(dest_dir, nm))
                print(f"copied to {dest_dir}")
            except Exception as e:                 # noqa: BLE001 - never raise
                print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "body_error": out.get("body_error"),
                      "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "phase_walls": out.get("phase_walls"),
                      "summary_error": out.get("summary_error"), "grade_errors": out.get("grade_errors"),
                      "run_id": run_id,
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])


if __name__ == "__main__":
    main()
