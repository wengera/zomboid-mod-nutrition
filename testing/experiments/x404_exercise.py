"""x404-exercise -- Plan 11b Task 4 session S4d (live): the exercise reads owed to the 1.0.0 release, on the staged copy
the controller made after Task 3c (release/plan11-x40/NutritionRevamp/Contents/mods/NutritionRevamp, staged with
`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan11-x40`; release/ is gitignored; mod/ is
never booted). One boot of profile x40-exercise (fixture default, admin -debug, Nutrition false, DayLength 1 -- a game
minute 0.625 s of wall at speed 1 -- sleep off, TKX_StudyFoods by its path). Build 42.21.0 (4a0e9546ec). Artifact
`exercise.json`, the staged MANIFEST.json and the minute ring's pages copied byte-identical beside it. Written BEFORE
the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

The driver hard-codes no commit or sha of the mod: before the boot it compares the staged copy's MANIFEST.json with
tools/release_pack.py's manifest() of mod/NutritionRevamp at HEAD (the tree clean) and of the staged tree itself,
records HEAD and the MANIFEST's sha256, and refuses to boot on any mismatch. It never re-stages. It asserts that its
PREFIX and PROFILE match its own file name, that the harness files (the repository copies before the boot, every
deployed copy after it, each file read once) hold the markers of 016dce05, 07c27dc4, 2ffdbc81, 513778e8 and ccb71a1b
(HARNESS_MARKERS), and that each of those commits is an ancestor of HEAD; it refuses to boot, or aborts before body(),
otherwise. The lib is x391h_bench.py's (Plan 11b Task 2's latest): its bus liveness, wall budget, server-confirmed
spawns and grading in `finally` (task-4-amendments, Lessons from Task 2).

WHY (run sheet Task 4 (c), the owed reads S4d carries):
  * X64's sweatActive half (#2972's bound: `sweatActive` was not read): `fluids.sweatActive` with `sweat6h`, `loss6h`
    and `body.met` on the minute ring through a long burpee set and the 6 h after it; it turns on when sweat exceeds
    K.fluids.SWEAT_ACTIVE_SHARE (0.5) of the 6 h loss (NR_Kernel_Fluids.lua K.fluids.sweatActive);
  * 11f's C-26 raw-against-raw fall gate (#3693; x351-x353 ran before the gate): one eat after a Fitness set, on a
    carried load, on a minute when the raw rate is still falling, bills idle (COMPENDIUM.Default 1.3);
  * 11h's cancel path (ruling T4-2; #3724, #3739): a started Fitness set stopped through ISTimedActionQueue.clear (H3
    `action.cancel`) drops the server's exercise flag and clears the wrapper's record, and the wrapper's stop count
    rises by 1;
  * 11h's movement end through its own branch's twin (#3736): ISFitnessAction:update's line 39 ends a set on
    pressedMovement(true) OR an ENDURANCE moodle above ISFitnessUI.enduranceLevelThreshold (2), with the same three
    calls; a server `stats.set` of ENDURANCE low during a set drives that branch; the key press stays unmeasured;
  * optional, X33 (#1299): a completed eat, a cancelled eat of a normal item and a cancelled eat of an item driven under
    vanilla's guard `abs(getHungerChange()*100) <= 1` (ISEatFoodAction:serverStop :146-149), each read on the server.

PHASES (each checked against the wall budget before it starts; the server bus's liveness after every server step):
  S0   ready, ping, players, the clock, speed 1, the record, the kernel constants the grades read live
       (K.fluids.SWEAT_ACTIVE_SHARE, K.energy.FALL_EPS, COMPENDIUM.Default, CLASS_MET.Default and LightDomestic,
       EXERCISE_MET.burpees and squats), the Fitness wraps installed (wrappedStart, wrappedStop).
  H    the minute ring armed on admin (RING_PATHS: the fluids and billing record paths and the wrapper's, intake's and
       writer's globals; every row also carries the engine's raw rate `rate`, the exercise flag `exe` and `moving`).
  LOAD the carried load and the C-26 food: RCON `additem "admin" "Base.BarBell" 2` (6.0 kg each, 12 kg) and
       `additem "admin" "TKX.Unit50" 1`, each CONFIRMED by the server's `item.get` id (ruling T2-11; never
       inventory.add for an item a client will eat), a leftover before the spawn voiding the confirmation; then the
       server's inventory weight and capacity weight (witness.chain) and maxWeight (stats.get).
  B    THE BURPEE SET: rested (the server's endurance moodle at most 1, else speed 5 to it), at speed 1, `exercise.do
       burpees 60` (60 game minutes, 37.5 s of wall), followed at the server (the exercise flag, the wrapper's record
       and counters, the endurance) until the flag clears, it never shows within SET_START_CAP_M (refused), or the
       world passes the ask plus OVERRUN_M (then `action.cancel`, named). The way it ended is a reading: its timer
       (at or past the ask) or before its ask (the endurance branch: the moodle read at the clear).
  C26  THE EAT ON THE FALLING RATE (only on a confirmed load and food): at once after the clear, the server's load
       (witness.chain) and `foodtimer.set admin 0`, `eat.action TKX.Unit50 1` (stopping the session's eats if its
       `spawned` is not "found"), intake.stats.landed polled until it rises (EAT_CAP_S), then speed 1 until
       C26_WINDOW_M game minutes past the clear.
  SIX  speed 5 until 6 game hours past the clear (the sweat EMA's fall), then speed 1.
  CAN  THE CANCEL: rested; `exercise.do squats 60`; CANCEL_AFTER_M game minutes after the flag shows, the wrapper's
       state, then `action.cancel` on admin's client; the flag polled until it clears (CANCEL_CAP_S); the wrapper's
       state at the clear and REST_M game minutes later.
  TWIN THE MOVEMENT BRANCH'S TWIN: rested; `exercise.do squats 60`; TWIN_AFTER_M game minutes after the flag shows, the
       wrapper's state, then the SERVER's `stats.set admin endurance TWIN_ENDURANCE`; the flag, the server's
       endurance and moodle and the client's polled until the flag clears (TWIN_CAP_S). If it has not cleared, the
       CLIENT's `stats.set endurance TWIN_ENDURANCE` (a second route, a reading) and the same poll; if it still has
       not, `action.cancel` (the cleanup, lessons #3739). The wrapper's state at the clear and REST_M later.
  X33  OPTIONAL (only inside the budget): three arms, each on its own TKX type spawned by RCON and confirmed by
       item.get with no leftover: completed (TKX.SnackP, eaten whole), cancelled normal (TKX.SnackC, `action.cancel`
       CANCEL_EAT_AFTER_S after the queue) and cancelled under the guard (TKX.SnackF, its hungChange driven to
       GUARD_HC by the server's item.set, read back state-modified, then the same cancel); before and after each, the
       server's item.get, nutrition.get and the intake's counters (eats, cancels, landed).
  RING the ring's pages read and copied (always run, the server steps skipped on a dead bus).
  Z    the local readings first (mod error lines, admin parked), then the server's: players, the clock, the
       wrapper's state.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured / void, each with its falsifier;
a dead-bus phase is void, never falsified):
  LOAD       the server answers an id for Base.BarBell and for TKX.Unit50 after the spawn (none before), and its
             capacity weight reads at least LOAD_MIN_KG. Falsifier: an id missing on a live bus, or the load under
             LOAD_MIN_KG.
  SET_B      the burpee set starts (the flag shows within SET_START_CAP_M) and the wrapper records "burpees" while
             it runs. Falsifier: no flag on a live bus, or another record. Its length and end are a reading.
  SWEAT_ON   on a ring row from the set's first flagged row to 6 game hours after its clear, fluids.sweatActive reads
             true. Falsifier: every such row reads false. Unmeasured: no such row read.
  SWEAT_RULE on every ring row that carries sweatActive, sweat6h and loss6h, sweatActive equals (loss6h > 0 and
             sweat6h / loss6h > SWEAT_ACTIVE_SHARE), the share read live. Falsifier: any row that differs.
  SWEAT_OFF  a READING: the first row after the clear that reads false again, its hours after the clear and the ratio.
  C26        on each of the eat's two candidate drains (the drain before and the drain after the ring row where
             intake.stats.landed first shows the eat), when the ring reads the raw rate falling against the row
             before (more than FALL_EPS, or the flag's clear), not moving and not flagged, the drain bills
             body.met == COMPENDIUM.Default (1.3, read live) within 1e-9 (the next row's body.met: row k + 1 reads
             what drain k billed). Falsifier: a candidate drain that meets the conditions and bills otherwise. Trivial:
             the stripped rate at the eat (raw / (1 + 0.35 x (capacity weight / maxWeight)^2), the engine's load
             factor, #2649's form) under TRIVIAL_STRIPPED (the rate's own class bills no more than idle). Void: the
             load or the food not confirmed, the eat not landed, or the bus dead. Unmeasured: no candidate drain meets
             the conditions. The C26 window's other still falling drains are a reading, and so is old_gate_falling
             on each candidate: whether the pre-C-26 gate (the stripped rate, divided by the lighter load after the
             eat against the heavier one before) would also have read a fall there (with a 0.1 kg food on a 12 kg
             load it likely would: the reading names how sharp the trap was; it does not grade the gate).
  CANCEL     action.cancel replies ok with started true, stopped true and cleared true; the server's flag clears
             within CANCEL_CAP_S; the wrapper's stops counter is exactly one higher at the clear than before the
             cancel; the record reads nil at the clear and REST_M later. Falsifier: any of these off on a live bus.
             Unmeasured: the set never showed.
  TWIN       after the server's stats.set of ENDURANCE, the flag clears within TWIN_CAP_S on the server route alone,
             before the set's own timer (the clear's world age under the first flag's plus TWIN_ASK_M - 1); the stops
             counter one higher at the clear; the record nil at the clear and REST_M later. Falsifier: the server
             route does not clear the flag within TWIN_CAP_S, or the stops or record off. TWIN_CLIENT, a reading:
             whether the client's own stats.set cleared it when the server's did not. Unmeasured: the set never showed.
  X33        the guard arm (TKX.SnackF, |hungerChange x 100| <= 1 read back): the cancel reached the server
             (intake.stats.cancels +1) and nothing was applied: intake.stats.landed unchanged, the item still on the
             server with its hungChange unchanged, the server's calories unchanged within 1e-6. Falsifier: a landing,
             a changed item or changed calories after a cancel that reached the server. Unmeasured: the arm not run
             (the budget or a failed spawn), the cancel not started, or cancels not +1. The completed and the normal
             cancelled arms are READINGS beside it (completed: eats +1, landed +1, the item gone; normal: cancels +1,
             and whether it landed).
  RING       every page read with errors 0.
  Z          no mod error line, admin not parked, and the server alive at the end (players answers a list).

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time; free memory read
before the boot, refused under 12 GB. 4. A session killed by the host is reported, and its measured phases are never
re-run to replace their figures (ruling H2-1).
"""
import ctypes
import glob
import hashlib
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

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))
import release_pack                                             # noqa: E402

PROFILE = "x40-exercise"
PREFIX = "x404"
SESSION = ("Plan 11b Task 4 session S4d (x404): the burpee set's sweatActive through the 6 h after it, the C-26 eat on "
           "a falling raw rate on a carried load, the Fitness cancel through action.cancel, the movement branch's "
           "endurance twin and the optional X33 cancelled eats, on the staged 1.0.0 copy; one boot of " + PROFILE)
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert PROFILE == "x40-exercise" and _ME == "x404_exercise.py", f"PROFILE {PROFILE} does not match the driver {_ME}"
ARTIFACT = "exercise.json"
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
KPATHS = {"share": f"{NR}.kernel.fluids.SWEAT_ACTIVE_SHARE", "fallEps": f"{NR}.kernel.energy.FALL_EPS",
          "idleMet": f"{NR}.kernel.energy.COMPENDIUM.Default", "classDefault": f"{NR}.kernel.energy.CLASS_MET.Default",
          "classLight": f"{NR}.kernel.energy.CLASS_MET.LightDomestic",
          "burpees": f"{NR}.kernel.energy.EXERCISE_MET.burpees", "squats": f"{NR}.kernel.energy.EXERCISE_MET.squats"}
EXETYPE = f"{NR}.server.fitness.exeType.{USER}"
FIT_PATHS = (EXETYPE, f"{NR}.server.fitness.stats.starts", f"{NR}.server.fitness.stats.stops",
             f"{NR}.server.fitness.stats.untyped", f"{NR}.server.fitness.stats.failures",
             f"{NR}.server.fitness.wrappedStart", f"{NR}.server.fitness.wrappedStop", f"{NR}.server.fitness.lastError",
             f"{NR}.server.metabolism.stats.exeFallbacks")
INTAKE_PATHS = (f"{NR}.server.intake.stats.eats", f"{NR}.server.intake.stats.cancels",
                f"{NR}.server.intake.stats.landed", f"{NR}.server.intake.stats.failures")
RING_RECORD = ("fluids.sweatActive", "fluids.sweat6h", "fluids.loss6h", "fluids.sweatLmin", "fluids.water",
               "fluids.na", "body.met", "body.epoc", "body.exKcalDay", "satiety.M")
RING_GLOBALS = ("_G." + EXETYPE, f"_G.{NR}.server.fitness.stats.starts", f"_G.{NR}.server.fitness.stats.stops",
                f"_G.{NR}.server.fitness.stats.untyped", f"_G.{NR}.server.metabolism.stats.exeFallbacks",
                f"_G.{NR}.server.intake.stats.eats", f"_G.{NR}.server.intake.stats.landed",
                f"_G.{NR}.server.intake.stats.cancels", f"_G.{NR}.server.writer.stats.writes")
LANDED_RING = f"_G.{NR}.server.intake.stats.landed"
EXE_CHAIN = "getFitness.getCurrentExe"      # the server's current Fitness exercise (nil when none)
INVW_CHAIN = "getInventoryWeight"
CAPW_CHAIN = "getInventory.getCapacityWeight"
# the load and the foods
LOAD_ITEM, LOAD_N, LOAD_MIN_KG = "Base.BarBell", 2, 10.0      # 6.0 kg each (weapon.txt item BarBell, Weight = 6.0)
C26_FOOD = "TKX.Unit50"                                        # 50 kcal; maxTime 232 (hungerConsumed 2: one loop)
X33_ARMS = (("done", "TKX.SnackP"), ("cancel", "TKX.SnackC"), ("guard", "TKX.SnackF"))
GUARD_HC = -0.005                                              # |hungChange x 100| = 0.5 <= 1 (serverStop :146-149)
# the clock and the sets
SPEED_FAST = 5
SET_START_CAP_M = 3.0
OVERRUN_M = 15.0
REST_M = 4.0
ENDURANCE_MAX = 2                    # ISFitnessUI.enduranceLevelThreshold
ENDURANCE_REST_CAP_M = 60.0
B_ASK_M = 60
C26_WINDOW_M = 20.0                  # game minutes past the clear at speed 1 (the eat lands about 7 of them in)
SIX_H = 6.0
CANCEL_ASK_M = 60
CANCEL_AFTER_M = 2.0
CANCEL_CAP_S = 15.0
TWIN_ASK_M = 60
TWIN_AFTER_M = 2.0
TWIN_ENDURANCE = 0.05                # the ENDURANCE moodle above 2 (level 3 under 0.25, 4 under 0.1)
TWIN_CAP_S = 12.0
CANCEL_EAT_AFTER_S = 2.0             # an eat lasts 232 x 20 ms = 4.64 s of real time (#3766)
EAT_CAP_S = 25.0
X33_POLL_CAP_S = 12.0
SPAWN_WAIT_S = 2.5
TRIVIAL_STRIPPED = 1.55              # between CLASS_MET.Default 1.5 and LightDomestic 1.6: at or under it the rate's own
                                     # class bills no more than idle, so the gate cannot show
LOAD_K = 0.35                        # the engine's load factor 1 + 0.35 x (capacity / max)^2 (#2649's form)
MET_TOL = 1e-9
# liveness and the wall budget
PING_TIMEOUT_S = 5
BUDGET_S = 840.0                     # from t0 (before the boot); RING, Z and the teardown fit 900 s
PHASE_EST_S = {"S0": 12.0, "H": 4.0, "LOAD": 12.0, "B": 75.0, "C26": 30.0, "SIX": 60.0, "CAN": 45.0, "TWIN": 50.0,
               "X33": 50.0}
FINAL_PHASES = ("RING", "Z")
EAT_PHASES = ("C26", "X33")          # skipped once an eat.action reply's spawned is not "found" (ruling T2-11)
MIN_FREE_GB = 12.0
RESULT_WAIT_S = 30.0
POLL_S = 0.25
LOG_LIMIT = 400
ECHO_RX = re.compile(r"PZTK: ")
PROBE_RX = re.compile(r"\b(?:minute\.ring|lua\.(?:read|global)|time\.snapshot|witness\.chain|stats\.(?:get|set|all)|"
                      r"exercise\.do|action\.cancel|eat\.action|item\.(?:get|set)|foodtimer\.set|nutrition\.get|"
                      r"additem|settimespeed)")
                                     # this driver's own probe and command names, excluded from every log grep
MOD_LIFE_RX = re.compile(r"minute: \w+ failed|players: hook failed|players: task|fitness: |intake: |writer: |"
                         r"metabolism: |non-finite")
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")

META_NOTES = {
    "ring_note": "a ring row is sampled inside EveryOneMinute before the mod's queue drains that minute: row k reads the "
                 "state drain k-1 left, and row k + 1's body.met is what drain k billed",
    "eat_note": "a networked eat ends in real time, 232 x 20 ms, whatever the clock (#3766)",
    "spawn_note": "every eaten or carried item is spawned by RCON additem and confirmed by the server's item.get id "
                  "(ruling T2-11); an unconfirmed spawn voids its phase",
    "frame_note": "no frame window is graded in this session (no tick.ring), so no drop_windows apply",
    "twin_note": "the harness has no movement key press: the endurance branch of ISFitnessAction:update's line 39 is "
                 "driven as the movement end's twin (#3736)"}
SUMMARY_KEYS = ("set_b", "sweat", "sweat_off", "c26", "cancel", "twin", "twin_client")


PRED = {
    "LOAD": {"item.get after the spawn": f"an id for {LOAD_ITEM} and {C26_FOOD}, none before",
             "capacity weight": f">= {LOAD_MIN_KG} kg",
             "falsifier": "an id missing on a live bus, or the load under LOAD_MIN_KG"},
    "SET_B": {"burpees 60": "the flag shows within SET_START_CAP_M and the record reads burpees while it runs",
              "reading": "its length and how it ended (timer, or before the ask by the endurance branch)",
              "falsifier": "no flag on a live bus, or another record"},
    "SWEAT_ON": {"fluids.sweatActive": "true on a ring row between the set's first flagged row and 6 h after its clear",
                 "falsifier": "every such row false", "unmeasured": "no such row read"},
    "SWEAT_RULE": {"every row": "sweatActive == (loss6h > 0 and sweat6h / loss6h > K.fluids.SWEAT_ACTIVE_SHARE)",
                   "falsifier": "any row that differs"},
    "SWEAT_OFF": {"reading": "the first row after the clear that reads false, its hours after the clear and ratio"},
    "C26": {"the eat's candidate drains": "falling raw (> FALL_EPS against the row before, or the flag's clear), not "
                                          "moving, not flagged -> billed body.met == COMPENDIUM.Default within 1e-9",
            "trivial": f"the stripped rate at the eat under {TRIVIAL_STRIPPED}",
            "void": "the load or the food unconfirmed, the eat not landed, or the bus dead",
            "unmeasured": "no candidate drain meets the conditions",
            "falsifier": "a candidate drain meeting the conditions that bills otherwise"},
    "CANCEL": {"action.cancel": "ok, started true, stopped true, cleared true",
               "server flag": f"clears within {CANCEL_CAP_S} s", "stops": "+1 at the clear",
               "record": "nil at the clear and REST_M later",
               "falsifier": "any of these off on a live bus", "unmeasured": "the set never showed"},
    "TWIN": {"server stats.set ENDURANCE": f"{TWIN_ENDURANCE}: the flag clears within {TWIN_CAP_S} s on the server "
                                         "route, before the set's own timer",
             "stops": "+1 at the clear", "record": "nil at the clear and REST_M later",
             "falsifier": "the server route does not clear the flag, or the stops or record off",
             "TWIN_CLIENT": "a reading: the client's own stats.set when the server's did not clear it",
             "unmeasured": "the set never showed"},
    "X33": {"guard arm": "cancels +1; landed unchanged; the item on the server with its hungChange unchanged; the "
                         "server's calories unchanged within 1e-6",
            "readings": "the completed arm (eats +1, landed +1, item gone) and the normal cancelled arm",
            "falsifier": "a landing, a changed item or changed calories after a cancel that reached the server",
            "unmeasured": "the arm not run, the cancel not started, or cancels not +1"},
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


# ---------------------------------------------------------------- the Fitness verbs (x37's, on this lib)
def fit_read(tag, log=False):
    f = lread(SRV, "_G", FIT_PATHS, tag + "_fit", log=log)
    v = vals(f)
    return {"wall": f.get("wall"), "exeType": v.get(FIT_PATHS[0]), "starts": num(v.get(FIT_PATHS[1])),
            "stops": num(v.get(FIT_PATHS[2])), "untyped": num(v.get(FIT_PATHS[3])), "failures": num(v.get(FIT_PATHS[4])),
            "wrappedStart": v.get(FIT_PATHS[5]), "wrappedStop": v.get(FIT_PATHS[6]), "lastError": v.get(FIT_PATHS[7]),
            "fallbacks": num(v.get(FIT_PATHS[8])), "missing": f.get("missing")}


def fit_poll(tag):
    """One server poll: the current exercise (the string "nil" when none), the wrapper's state and the world age."""
    w = keep(step(tag + "_exe", SRV, "witness.chain", f"{USER} {EXE_CHAIN}", log=False))
    f = fit_read(tag)
    v = w.get("value")
    return {**f, "age": age(tag + "_a"), "exe": v, "on": isinstance(v, str) and v not in ("", "nil")}


def endurance(tag, side=SRV):
    if side == SRV:
        a = keep(step(tag, SRV, "stats.get", USER, log=False))
    else:
        a = keep(step(tag, side, "stats.get", "", log=False))
    return {"moodle": num((a.get("moodles") or {}).get("endurance")), "endurance": num(a.get("endurance")),
            "age": num(a.get("worldAge")), "maxWeight": num(a.get("maxWeight")), "wall": a.get("wall")}


def ensure_rested(label):
    """The server's endurance moodle; above ENDURANCE_MAX - 1, speed 5 until it is at most that (a cap), then speed 1."""
    e = endurance(label + "_end0")
    row = {"label": label, "before": e, "rested": False}
    if e["moodle"] is not None and e["moodle"] > ENDURANCE_MAX - 1:
        row["rested"] = True
        speed("fast", label + "_fast")
        cap = (e["age"] or 0.0) + ENDURANCE_REST_CAP_M / 60.0
        while True:
            check()
            e = endurance(label + "_end")
            if (e["moodle"] is not None and e["moodle"] <= ENDURANCE_MAX - 1) or (e["age"] is not None and e["age"] >= cap):
                break
            time.sleep(4 * POLL_S)
        speed("one", label + "_one")
    row["after"] = e
    out.setdefault("rests", []).append(row)
    return row


def start_set(name, minutes, label):
    """exercise.do <name> <minutes> on admin's client, then server polls until the flag shows (SET_START_CAP_M)."""
    st = {"label": label, "exercise": name, "ask_m": minutes}
    st["before"] = fit_read(label + "_f0", log=True)
    q = keep(step(label + "_do", ADMIN, "exercise.do", f"{name} {minutes}"))
    st["queued"] = {k: q.get(k) for k in ("ok", "queued", "queueLen", "error", "queueError", "wall")}
    st["age_queued"] = age(label + "_aq")
    st["polls"] = []
    st["started"] = False
    while True:
        check()
        p = fit_poll(label + "_p")
        st["polls"].append(p)
        if p["on"]:
            st["started"], st["first_on_age"], st["first_on_wall"] = True, p["age"], p["wall"]
            st["record_first"] = p.get("exeType")
            break
        if p["age"] is not None and st["age_queued"] is not None and p["age"] > st["age_queued"] + SET_START_CAP_M / 60.0:
            break
        if bus["dead"]:
            raise BusDead(out.get("abort") or "server bus dead")
        time.sleep(POLL_S)
    if not st["started"]:
        note(f"set {label}: the server never showed exercise {name} within {SET_START_CAP_M} game minutes")
    return st


def follow_until(st, until_age, label, cap_s=None):
    """Polls the flag until it clears, the world age passes until_age, or cap_s of wall. Returns True on a clear."""
    end = time.time() + cap_s if cap_s is not None else None
    while True:
        check()
        p = fit_poll(label)
        st["polls"].append(p)
        if p["exeType"] is not None and st.get("record_during") is None:
            st["record_during"] = p["exeType"]
        if not p["on"]:
            st["clear_age"], st["clear_wall"] = p["age"], p["wall"]
            return True
        if until_age is not None and p["age"] is not None and p["age"] >= until_age:
            return False
        if end is not None and time.time() >= end:
            return False
        if bus["dead"]:
            raise BusDead(out.get("abort") or "server bus dead")
        time.sleep(POLL_S)


def cancel(label):
    a = keep(step(label + "_cancel", ADMIN, "action.cancel"))
    return {k: a.get(k) for k in ("ok", "before", "after", "current", "started", "adding", "stopped", "javaBefore",
                                  "javaAfter", "cleared", "clearError", "reason", "error", "raw", "wall")}


def after_clear(st, label):
    st["at_clear"] = fit_read(label + "_fc", log=True)
    st["endurance_at_clear"] = endurance(label + "_endc")
    base = num(st.get("clear_age"))
    if base is not None:
        wait_age(base + REST_M / 60.0, label + "_rest")
    st["after_rest"] = fit_read(label + "_fr", log=True)


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    P["ping"] = ping("S0_ping")
    P["players"] = keep(step("S0_players", SRV, "players"))
    P["one"] = speed("one", "S0_one")
    P["kernel"] = lread(SRV, "_G", list(KPATHS.values()), "S0_kernel")
    P["k"] = {k: num(vals(P["kernel"]).get(p)) for k, p in KPATHS.items()}
    P["record"] = lread(SRV, f"record:{USER}", ["firstSeen", "resets", "body.sex", "body.fm", "body.lm",
                                                "fluids.sweat6h", "fluids.loss6h", "fluids.sweatActive"], "S0_record")
    P["fit"] = fit_read("S0_fit", log=True)
    P["intake"] = intake("S0_intake", log=True)
    P["stats"] = endurance("S0_stats")


def phase_H():
    P = out["phases"]["H"] = {}
    paths = list(RING_RECORD) + list(RING_GLOBALS)
    P["paths"] = paths
    P["start"] = keep(step("H_ring_start", SRV, "minute.ring", " ".join([USER, "start"] + paths)))
    P["snap"] = snap("H_snap")


def phase_LOAD():
    P = out["phases"]["LOAD"] = {}
    P["load"] = spawn(LOAD_ITEM, LOAD_N, "LOAD_bar")
    P["food"] = spawn(C26_FOOD, 1, "LOAD_food")
    P["weights"] = load_read("LOAD_w")


def load_read(tag):
    iw = keep(step(tag + "_inv", SRV, "witness.chain", f"{USER} {INVW_CHAIN}"))
    cw = keep(step(tag + "_cap", SRV, "witness.chain", f"{USER} {CAPW_CHAIN}"))
    e = endurance(tag + "_st")
    capw, maxw = num(cw.get("value")), e.get("maxWeight")
    lf = (1.0 + LOAD_K * (capw / maxw) ** 2) if (capw is not None and maxw) else None
    return {"inventoryWeight": num(iw.get("value")), "capacityWeight": capw, "maxWeight": maxw, "loadFactor": lf,
            "wall": iw.get("wall")}


def phase_B():
    P = out["phases"]["B"] = {}
    P["rest"] = ensure_rested("B_rest")
    st = P["set"] = start_set("burpees", B_ASK_M, "B")
    if not st["started"]:
        return
    if st.get("record_first") is not None:
        st["record_during"] = st["record_first"]
    cleared = follow_until(st, st["first_on_age"] + (B_ASK_M + OVERRUN_M) / 60.0, "B_p")
    if not cleared:
        note(f"B: still running {OVERRUN_M} game minutes past its ask; action.cancel (named)")
        st["cap_cancel"] = cancel("B_cap")
        follow_until(st, None, "B_pc", cap_s=CANCEL_CAP_S)
    st["ran_m"] = ((st["clear_age"] - st["first_on_age"]) * 60.0) if st.get("clear_age") is not None else None
    st["ended"] = ("cap_cancel" if "cap_cancel" in st else
                   "timer" if st["ran_m"] is not None and st["ran_m"] >= B_ASK_M - 1.0 else
                   "before_ask" if st["ran_m"] is not None else None)
    st["at_clear"] = fit_read("B_fc", log=True)
    st["endurance_at_clear"] = endurance("B_endc")
    P["clear_snap"] = snap("B_clear_t")


def phase_C26():
    P = out["phases"]["C26"] = {}
    st = g(out, "phases", "B", "set") or {}
    L = g(out, "phases", "LOAD") or {}
    P["preconditions"] = {"load": g(L, "load", "confirmed"), "food": g(L, "food", "confirmed"),
                          "set_cleared": st.get("clear_age") is not None}
    clear_age = num(st.get("clear_age"))
    if not all(P["preconditions"].values()):
        note(f"C26: preconditions not met {P['preconditions']}; no eat (void)")
        if clear_age is not None:
            wait_age(clear_age + C26_WINDOW_M / 60.0, "C26_wait")
        return
    P["weights_before"] = load_read("C26_w0")
    P["intake_before"] = intake("C26_in0", log=True)
    P["queued"] = eat_queue(C26_FOOD, "C26")
    P["queue_age"] = age("C26_aq")
    P["landed"] = False
    end = time.time() + EAT_CAP_S
    while time.time() < end:
        check()
        a = intake("C26_poll")
        if a.get("landed") is not None and P["intake_before"].get("landed") is not None \
                and a["landed"] > P["intake_before"]["landed"]:
            P["landed"], P["intake_after"] = True, a
            P["landed_snap"] = snap("C26_landed_t")
            break
        if bus["dead"]:
            raise BusDead(out.get("abort") or "server bus dead")
        time.sleep(POLL_S)
    if not P["landed"]:
        note(f"C26: landed did not rise within {EAT_CAP_S} s")
    P["weights_after"] = load_read("C26_w1")
    if clear_age is not None:
        wait_age(clear_age + C26_WINDOW_M / 60.0, "C26_wait")


def phase_SIX():
    P = out["phases"]["SIX"] = {}
    clear_age = num(g(out, "phases", "B", "set", "clear_age"))
    if clear_age is None:
        note("SIX: no clear age (the set never ran or never cleared); skipped")
        return
    P["fast"] = speed("fast", "SIX_fast")
    P["arrived"] = wait_age(clear_age + SIX_H + 2.0 / 60.0, "SIX_wait")
    P["one"] = speed("one", "SIX_one")


def phase_CAN():
    P = out["phases"]["CAN"] = {}
    P["rest"] = ensure_rested("CAN_rest")
    st = P["set"] = start_set("squats", CANCEL_ASK_M, "CAN")
    if not st["started"]:
        return
    follow_until(st, st["first_on_age"] + CANCEL_AFTER_M / 60.0, "CAN_p")
    if st.get("clear_age") is not None:
        note("CAN: the set cleared before the cancel")
        after_clear(st, "CAN")
        return
    st["before_cancel"] = fit_read("CAN_fb", log=True)
    st["cancel"] = cancel("CAN")
    st["cancel_age"] = age("CAN_ca")
    st["cleared"] = follow_until(st, None, "CAN_pc", cap_s=CANCEL_CAP_S)
    st["clear_s_after_cancel"] = (st["clear_wall"] - st["cancel"]["wall"]) if (
        st.get("clear_wall") is not None and st["cancel"].get("wall") is not None) else None
    after_clear(st, "CAN")


def phase_TWIN():
    P = out["phases"]["TWIN"] = {}
    P["rest"] = ensure_rested("TWIN_rest")
    st = P["set"] = start_set("squats", TWIN_ASK_M, "TWIN")
    if not st["started"]:
        return
    follow_until(st, st["first_on_age"] + TWIN_AFTER_M / 60.0, "TWIN_p")
    if st.get("clear_age") is not None:
        note("TWIN: the set cleared before the endurance write")
        after_clear(st, "TWIN")
        return
    st["before_write"] = fit_read("TWIN_fb", log=True)
    st["server_set"] = keep(step("TWIN_sset", SRV, "stats.set", f"{USER} endurance {TWIN_ENDURANCE}"))
    st["route"] = None
    st["moodles"] = []

    def poll_route(route, cap_s):
        end = time.time() + cap_s
        while True:
            check()
            p = fit_poll(f"TWIN_{route}")
            st["polls"].append(p)
            st["moodles"].append({"route": route, "server": endurance(f"TWIN_{route}_se"),
                                  "client": endurance(f"TWIN_{route}_ce", side=ADMIN)})
            if not p["on"]:
                st["clear_age"], st["clear_wall"] = p["age"], p["wall"]
                return True
            if time.time() >= end:
                return False
            if bus["dead"]:
                raise BusDead(out.get("abort") or "server bus dead")
            time.sleep(POLL_S)
    if poll_route("server", TWIN_CAP_S):
        st["route"] = "server"
    else:
        note(f"TWIN: the server's endurance write did not clear the flag within {TWIN_CAP_S} s; the client's route")
        st["client_set"] = keep(step("TWIN_cset", ADMIN, "stats.set", f"endurance {TWIN_ENDURANCE}"))
        if poll_route("client", TWIN_CAP_S):
            st["route"] = "client"
        else:
            note("TWIN: neither route cleared the flag; action.cancel (the cleanup, lessons #3739)")
            st["cleanup_cancel"] = cancel("TWIN_cleanup")
            follow_until(st, None, "TWIN_pc", cap_s=CANCEL_CAP_S)
            st["route"] = "cancel" if st.get("clear_age") is not None else None
    st["clear_s_after_write"] = (st["clear_wall"] - st["server_set"]["wall"]) if (
        st.get("clear_wall") is not None and st["server_set"].get("wall") is not None) else None
    after_clear(st, "TWIN")


def x33_read(tag):
    return {"intake": intake(tag + "_in", log=True), "nutrition": {k: keep(step(tag + "_nut", SRV, "nutrition.get",
                                                                                 USER)).get(k)
                                                                    for k in ("calories", "carbs", "lipids", "proteins",
                                                                              "hunger")}}


def phase_X33():
    P = out["phases"]["X33"] = {"arms": {}}
    for arm, full_type in X33_ARMS:
        check()
        A = P["arms"][arm] = {"type": full_type}
        A["spawn"] = spawn(full_type, 1, f"X33_{arm}_sp")
        if not A["spawn"]["confirmed"]:
            continue
        if arm == "guard":
            A["item_set"] = keep(step(f"X33_{arm}_set", SRV, "item.set", f"{USER} {full_type} hungChange {GUARD_HC}"))
        A["pre_item"] = item_id(full_type, f"X33_{arm}_i0")
        A["pre"] = x33_read(f"X33_{arm}_pre")
        A["queued"] = eat_queue(full_type, f"X33_{arm}")
        base = A["pre"]["intake"]
        if arm != "done":
            time.sleep(CANCEL_EAT_AFTER_S)
            A["cancel"] = cancel(f"X33_{arm}")
        end = time.time() + X33_POLL_CAP_S
        while time.time() < end:
            check()
            a = intake(f"X33_{arm}_poll")
            key = "landed" if arm == "done" else "cancels"
            if a.get(key) is not None and base.get(key) is not None and a[key] > base[key]:
                break
            time.sleep(POLL_S)
        time.sleep(1.0)
        A["post_item"] = item_id(full_type, f"X33_{arm}_i1")
        A["post"] = x33_read(f"X33_{arm}_post")


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
    P["fit"] = fit_read("Z_fit", log=True)
    P["intake"] = intake("Z_intake", log=True)


ORDER = (("S0", phase_S0), ("H", phase_H), ("LOAD", phase_LOAD), ("B", phase_B), ("C26", phase_C26),
         ("SIX", phase_SIX), ("CAN", phase_CAN), ("TWIN", phase_TWIN), ("X33", phase_X33))


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


def sweat_rule(r, share):
    s6, l6 = num(r.get("fluids.sweat6h")), num(r.get("fluids.loss6h"))
    if s6 is None or l6 is None or share is None:
        return None
    return bool(l6 > 0 and s6 / l6 > share)


def drains(rows, k_c):
    """Per drain k (between ring rows k and k+1): the ring's falling test against row k-1 (raw rate drop > FALL_EPS, or
    the flag's clear), moving, the flag, and the billed MET (row k+1's body.met). Rows are consecutive by `s`."""
    out_ = []
    by_s = {r["s"]: r for r in rows}
    for r in rows:
        s = r["s"]
        prev, nxt = by_s.get(s - 1), by_s.get(s + 1)
        if prev is None or nxt is None:
            continue
        rp, rk = num(prev.get("rate")), num(r.get("rate"))
        fall_eps = k_c.get("fallEps")
        falling = None
        if rp is not None and rk is not None and fall_eps is not None:
            falling = rk < rp - fall_eps
        if prev.get("exe") is True and r.get("exe") is False:
            falling = True
        out_.append({"s": s, "age": r.get("age"), "rate_prev": rp, "rate": rk, "falling": falling,
                     "moving": r.get("moving"), "exe": r.get("exe"), "billed": num(nxt.get("body.met")),
                     "landed": num(r.get(LANDED_RING)), "landed_next": num(nxt.get(LANDED_RING))})
    return out_


def grade_all():
    S = out["summaries"]
    ph = out["phases"]
    dead = bus["dead"]
    k_c = g(ph, "S0", "k") or {}
    S["kernel"] = k_c
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
    # LOAD
    L = ph.get("LOAD") or {}
    lw = g(L, "weights", "capacityWeight")
    if not L:
        grade("LOAD", "void" if dead else "unmeasured", None, "phase not run")
    elif phase_dead("LOAD"):
        grade("LOAD", "void", {"load": g(L, "load", "confirmed"), "food": g(L, "food", "confirmed")}, "bus dead")
    else:
        ok = g(L, "load", "confirmed") is True and g(L, "food", "confirmed") is True and lw is not None and lw >= LOAD_MIN_KG
        grade("LOAD", "as_predicted" if ok else "falsified",
              {"load_confirmed": g(L, "load", "confirmed"), "food_confirmed": g(L, "food", "confirmed"),
               "weights": L.get("weights")}, PRED["LOAD"]["falsifier"])
    # SET_B
    st = g(ph, "B", "set") or {}
    if not st:
        grade("SET_B", "void" if (dead or phase_dead("B")) else "unmeasured", None, "phase not run")
    else:
        rec = st.get("record_during")
        reading = {"started": st.get("started"), "record_during": rec, "ran_m": st.get("ran_m"), "ended": st.get("ended"),
                   "first_on_age": st.get("first_on_age"), "clear_age": st.get("clear_age"),
                   "endurance_at_clear": st.get("endurance_at_clear"), "stops_at_clear": g(st, "at_clear", "stops")}
        S["set_b"] = reading
        if phase_dead("B") and not st.get("started"):
            grade("SET_B", "void", reading, "bus dead")
        else:
            ok = st.get("started") is True and rec == "burpees"
            grade("SET_B", "as_predicted" if ok else "falsified", reading, PRED["SET_B"]["falsifier"])
    # SWEAT
    share = k_c.get("share")
    first_on = next((r for r in rows if r.get("exe") is True), None)
    clear_age = num(st.get("clear_age"))
    win = [r for r in rows if first_on is not None and r["s"] >= first_on["s"] and clear_age is not None
           and num(r.get("age")) is not None and r["age"] <= clear_age + SIX_H]
    on_rows = [r for r in win if r.get("fluids.sweatActive") is True]
    S["sweat"] = {"window_rows": len(win), "on_rows": len(on_rows), "share": share,
                  "first_on": ({k: on_rows[0].get(k) for k in ("s", "age", "fluids.sweat6h", "fluids.loss6h",
                                                               "body.met", "exe")} if on_rows else None),
                  "max_ratio": max((num(r.get("fluids.sweat6h")) / num(r.get("fluids.loss6h"))
                                    for r in win if num(r.get("fluids.loss6h"))), default=None),
                  "sweat6h_max": max((num(r.get("fluids.sweat6h")) for r in win
                                      if num(r.get("fluids.sweat6h")) is not None), default=None)}
    if not win:
        grade("SWEAT_ON", "void" if dead else "unmeasured", S["sweat"], PRED["SWEAT_ON"]["falsifier"])
    else:
        grade("SWEAT_ON", "as_predicted" if on_rows else "falsified", S["sweat"], PRED["SWEAT_ON"]["falsifier"])
    checked, off = 0, []
    for r in rows:
        exp = sweat_rule(r, share)
        got = r.get("fluids.sweatActive")
        if exp is None or not isinstance(got, bool):
            continue
        checked += 1
        if got != exp:
            off.append({k: r.get(k) for k in ("s", "age", "fluids.sweat6h", "fluids.loss6h", "fluids.sweatActive")})
    S["sweat_rule"] = {"checked": checked, "off": off[:20], "off_n": len(off)}
    if checked == 0:
        grade("SWEAT_RULE", "void" if dead else "unmeasured", S["sweat_rule"], PRED["SWEAT_RULE"]["falsifier"])
    else:
        grade("SWEAT_RULE", "as_predicted" if not off else "falsified", S["sweat_rule"], PRED["SWEAT_RULE"]["falsifier"])
    after_on = [r for r in rows if on_rows and r["s"] > on_rows[-1]["s"]]
    off_row = next((r for r in after_on if r.get("fluids.sweatActive") is False), None)
    S["sweat_off"] = ({"s": off_row["s"], "age": off_row.get("age"),
                       "h_after_clear": (off_row["age"] - clear_age) if (clear_age is not None
                                                                         and num(off_row.get("age")) is not None) else None,
                       "sweat6h": off_row.get("fluids.sweat6h"), "loss6h": off_row.get("fluids.loss6h")}
                      if off_row else None)
    grade("SWEAT_OFF", "as_predicted" if off_row else "unmeasured", S["sweat_off"], "a reading (no threshold)")
    # C26
    C = ph.get("C26") or {}
    dr = drains(rows, k_c)
    idle = k_c.get("idleMet")
    base = num(g(C, "intake_before", "landed"))
    r_star = next((r for r in rows if base is not None and num(r.get(LANDED_RING)) is not None
                   and r[LANDED_RING] > base and clear_age is not None and num(r.get("age")) is not None
                   and r["age"] >= clear_age), None)
    cand = []
    if r_star is not None:
        cand = [d for d in dr if d["s"] in (r_star["s"] - 1, r_star["s"])]
    lf = g(C, "weights_before", "loadFactor")
    lf1 = g(C, "weights_after", "loadFactor")
    for d in cand:
        d["meets"] = d["falling"] is True and d["moving"] is False and d["exe"] is False
        d["bills_idle"] = (d["billed"] is not None and idle is not None and abs(d["billed"] - idle) <= MET_TOL)
        d["stripped"] = (d["rate"] / lf) if (d["rate"] is not None and lf) else d["rate"]
        # a reading: whether the pre-C-26 gate (the stripped rate, its divisor the lighter load after the eat against
        # the heavier one before) would also have read a fall on this drain
        if None not in (d["rate"], d["rate_prev"], lf, lf1, k_c.get("fallEps")):
            d["old_gate_falling"] = d["rate"] / lf1 < d["rate_prev"] / lf - k_c["fallEps"]
    window = [d for d in dr if clear_age is not None and num(d.get("age")) is not None
              and clear_age - 1.0 / 60.0 <= d["age"] <= clear_age + C26_WINDOW_M / 60.0]
    still = [d for d in window if d["falling"] is True and d["moving"] is False and d["exe"] is False]
    S["c26"] = {"preconditions": C.get("preconditions"), "landed": C.get("landed"), "landing_row": r_star["s"] if r_star else None,
                "candidates": cand, "load_factor": lf, "idle_met": idle,
                "window": {"drains": len(window), "still_falling": len(still),
                           "billed_idle": sum(1 for d in still if d["billed"] is not None and idle is not None
                                              and abs(d["billed"] - idle) <= MET_TOL),
                           "other": [d for d in still if not (d["billed"] is not None and idle is not None
                                                              and abs(d["billed"] - idle) <= MET_TOL)][:10]}}
    met = [d for d in cand if d.get("meets")]
    if not C or not all((C.get("preconditions") or {}).values()) or C.get("landed") is not True or phase_dead("C26"):
        grade("C26", "void", S["c26"], PRED["C26"]["void"], {"stop_reason": out.get("stop_reason")})
    elif not met:
        grade("C26", "unmeasured", S["c26"], PRED["C26"]["unmeasured"])
    elif any(not d["bills_idle"] for d in met):
        grade("C26", "falsified", S["c26"], PRED["C26"]["falsifier"])
    elif all(d["stripped"] is not None and d["stripped"] < TRIVIAL_STRIPPED for d in met):
        grade("C26", "trivial", S["c26"], PRED["C26"]["trivial"])
    else:
        grade("C26", "as_predicted", S["c26"], PRED["C26"]["falsifier"])
    # CANCEL
    cs = g(ph, "CAN", "set") or {}
    c = cs.get("cancel") or {}
    obs = {"started": cs.get("started"), "cancel": c, "cleared": cs.get("cleared"),
           "clear_s_after_cancel": cs.get("clear_s_after_cancel"),
           "stops_before": g(cs, "before_cancel", "stops"), "stops_at_clear": g(cs, "at_clear", "stops"),
           "record_before": g(cs, "before_cancel", "exeType"), "record_at_clear": g(cs, "at_clear", "exeType"),
           "record_after_rest": g(cs, "after_rest", "exeType")}
    S["cancel"] = obs
    if not cs:
        grade("CANCEL", "void" if dead else "unmeasured", obs, "phase not run")
    elif not cs.get("started") or not c:
        grade("CANCEL", "void" if phase_dead("CAN") else "unmeasured", obs, PRED["CANCEL"]["unmeasured"])
    elif phase_dead("CAN"):
        grade("CANCEL", "void", obs, "bus dead")
    else:
        sb, sc = num(obs["stops_before"]), num(obs["stops_at_clear"])
        ok = (c.get("ok") is True and c.get("started") is True and c.get("stopped") is True and c.get("cleared") is True
              and cs.get("cleared") is True and sb is not None and sc is not None and sc - sb == 1
              and obs["record_at_clear"] is None and obs["record_after_rest"] is None
              and not (g(cs, "at_clear", "missing") or {}).get(FIT_PATHS[2]))
        grade("CANCEL", "as_predicted" if ok else "falsified", obs, PRED["CANCEL"]["falsifier"])
    # TWIN
    ts = g(ph, "TWIN", "set") or {}
    obs = {"started": ts.get("started"), "route": ts.get("route"), "server_set": ts.get("server_set"),
           "client_set": ts.get("client_set"), "clear_s_after_write": ts.get("clear_s_after_write"),
           "first_on_age": ts.get("first_on_age"), "clear_age": ts.get("clear_age"),
           "stops_before": g(ts, "before_write", "stops"), "stops_at_clear": g(ts, "at_clear", "stops"),
           "record_at_clear": g(ts, "at_clear", "exeType"), "record_after_rest": g(ts, "after_rest", "exeType"),
           "moodles": (ts.get("moodles") or [])[:40]}
    S["twin"] = obs
    if not ts:
        grade("TWIN", "void" if dead else "unmeasured", obs, "phase not run")
    elif not ts.get("started") or "server_set" not in ts:
        grade("TWIN", "void" if phase_dead("TWIN") else "unmeasured", obs, PRED["TWIN"]["unmeasured"])
    elif phase_dead("TWIN"):
        grade("TWIN", "void", obs, "bus dead")
    else:
        sb, sc = num(obs["stops_before"]), num(obs["stops_at_clear"])
        fo, ca = num(obs["first_on_age"]), num(obs["clear_age"])
        before_timer = fo is not None and ca is not None and ca < fo + (TWIN_ASK_M - 1.0) / 60.0
        ok = (ts.get("route") == "server" and before_timer and sb is not None and sc is not None and sc - sb == 1
              and obs["record_at_clear"] is None and obs["record_after_rest"] is None)
        grade("TWIN", "as_predicted" if ok else "falsified", obs, PRED["TWIN"]["falsifier"],
              {"before_timer": before_timer})
    S["twin_client"] = {"ran": "client_set" in ts, "cleared": ts.get("route") == "client"} if ts else None
    # X33
    X = g(ph, "X33", "arms") or {}
    S["x33"] = {}
    for arm, full_type in X33_ARMS:
        A = X.get(arm) or {}
        pre, post = A.get("pre") or {}, A.get("post") or {}

        def d(k, pre_=pre, post_=post):
            a, b = num(g(pre_, "intake", k)), num(g(post_, "intake", k))
            return (b - a) if (a is not None and b is not None) else None
        cal0, cal1 = num(g(pre, "nutrition", "calories")), num(g(post, "nutrition", "calories"))
        S["x33"][arm] = {"type": full_type, "confirmed": g(A, "spawn", "confirmed"), "queued": A.get("queued"),
                         "cancel": A.get("cancel"), "eats": d("eats"), "cancels": d("cancels"), "landed": d("landed"),
                         "item_before": A.get("pre_item"), "item_after": A.get("post_item"),
                         "calories_delta": (cal1 - cal0) if (cal0 is not None and cal1 is not None) else None,
                         "item_set": {k: g(A, "item_set", k) for k in ("hungChange", "hungerChange", "before")}
                         if A.get("item_set") else None}
    gd = S["x33"].get("guard") or {}
    hc = num(g(gd, "item_before", "hungerChange"))
    under = hc is not None and abs(hc * 100.0) <= 1.0
    if not X or not gd.get("confirmed") or gd.get("queued") is None:
        grade("X33", "void" if (dead or phase_dead("X33") or out.get("stop_reason")) else "unmeasured", S["x33"],
              PRED["X33"]["unmeasured"],
              {"stop_reason": out.get("stop_reason")})
    elif not under or g(gd, "cancel", "started") is not True or gd.get("cancels") != 1:
        grade("X33", "void" if phase_dead("X33") else "unmeasured", S["x33"], PRED["X33"]["unmeasured"],
              {"under_guard": under})
    else:
        item_same = (g(gd, "item_after", "id") is not None
                     and g(gd, "item_after", "id") == g(gd, "item_before", "id")
                     and num(g(gd, "item_after", "hungChange")) == num(g(gd, "item_before", "hungChange")))
        cal_same = gd.get("calories_delta") is not None and abs(gd["calories_delta"]) <= 1e-6
        ok = gd.get("landed") == 0 and item_same and cal_same
        grade("X33", "as_predicted" if ok else "falsified", S["x33"], PRED["X33"]["falsifier"],
              {"under_guard": under, "item_same": item_same, "calories_same": cal_same})
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
