"""x401-accept -- Plan 11b Task 4, session S4a: the live acceptance of the 1.0.0 release in Managed mode (Mode 1) on
fixture `two` (admin -debug, then bob release), one boot of profile x40-accept. On the STAGED copy the controller
makes after Task 3c (release/plan11-x40/NutritionRevamp/Contents/mods/NutritionRevamp, `python tools/release_pack.py
stage mod/NutritionRevamp --out release/plan11-x40`; release/ is gitignored; mod/ is never booted). The driver names no
commit and no sha for the stage: before the boot it imports tools/release_pack.py and checks that the staged
MANIFEST.json equals release_pack.manifest(mod/NutritionRevamp) on a clean mod/ tree (so it is HEAD's) and that the
staged files hash to that MANIFEST; it records HEAD and the MANIFEST's sha256 and refuses to boot on any mismatch. It
never re-stages. Build 42.21.0 (4a0e9546ec), Nutrition false, DayLength 1 (a game minute is 0.625 s of wall at true
multiplier 1), TKX_StudyFoods by its path. Artifact: `accept.json`, the staged MANIFEST.json and the protein pair's ring
pages copied beside it (server-stdout.log as x391a-h: the controller copies it when it is the evidence of an event).
Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2). Shape:
x391h_bench.py at c8778f69 (liveness, the wall budget, the deployed-marker check, the RCON spawn confirmed by item.get,
grading in finally), with x201_release.py's self-report greps.

PHASES (run order; each checked against the wall budget before it starts):
  S0  ready, ping, players, the clocks, both records present and MIN_RUNS minute runs.
  A   THE SELF-REPORTS and THE ZEROED RATES: live reads of NutritionRevamp.server.writer.zeroed, .mode, .stats.nms and
      .limitations (its key count: the code's count), `lua.call NutritionRevamp.vanillaRate HungerIncrease`,
      `lua.global ZomboidGlobals.HungerIncrease`, the seven saved rates against the live table, the version on all three
      sides. After teardown the logs: the server's self-report line, each client's, the zeroing line and no Nutrition
      Makes Sense warning. The limitations count is also parsed from the staged NR_Server_Writer.lua (STATIC_LIMITS).
  BF  THE BODY FAT ROW (Task 3a): on each client one lua.read of NutritionRevamp.client (view.level, view.female,
      view.fatBand, the mirror's body_fm and body_weight, rows 1..ROW_SCAN keys), then the body_fat row's key, text,
      valueText and fatBand; on the server the record's body.sex, body.fm, body.lm. n = 1 per client.
  B1  THE STATS HOLD: the true multiplier read, `time.multiplier SLOW_MULT` (see DEVIATION 2), STATS_S of `stats.all
      admin` at POLL_S, the writer's writes before and after, the multiplier restored to its read value.
  B2  PANIC 10, ruling 3, sized to `moodle.watch PANIC WATCH_S` on admin's client (the hold procedure below).
  B3  PANIC 6.6, the same, with `moodle.level admin PANIC` on the server at every poll: the #3400 flicker, a reading.
  B4  TEMPERATURE at `effects.tempOffset 0.5`, TEMP_HOLD_S after establishment, the record's effects.tempTarget read at
      every poll.
  H   THE LEAK CLOSED: `lua.call ModData.exists NutritionRevamp.players` on the server (and on bob, a reading); on bob
      `event.watch OnReceiveGlobalModData`, `lua.call ModData.request NutritionRevamp.players`, LEAK_WAIT_S, `event.watch
      OnReceiveGlobalModData read`.
  ML  THE MIRROR LIMIT (#3012's rule): bus.requests.stats answered and denied on the server; on bob `lua.call
      NutritionRevamp.client.requestMirror` twice back to back (client acks about 0.5 s each, both inside 5 s); the
      server's counters again after ML_SETTLE_S; bob's NutritionRevamp.client.received before and after.
  PP  THE PROTEIN PAIR (11d, the controller may drop it from the delta): TKX.SnackP on admin and TKX.SnackC on bob, 239
      kcal each, spawned by RCON additem and confirmed by the server's item.get (an id) and the client's witness; a
      minute.ring on each user (RING_PATHS); foodtimer 0 on both; both eats queued back to back; the landings polled;
      then `settimespeed 5` until PP_HOURS game hours past the later landing (cap PP_CAP_S), `settimespeed 1`; both
      rings read and stopped, their pages copied into the artifact. A READING: each player's HUNGER over the 3 h off
      its own ring (the live contrast across two bodies). The replay arm (the same body with the snack swapped,
      tools/replay_live.py on each ring) is NOT run by this driver (DEVIATION 5).
  WW  WORLD WATER (11a): `water.take admin` (the nearest source within 10 tiles); with no source the reading is
      unmeasured, with the reply. Queued: intake.stats.worldSips polled until it rises and settles, then the next
      writer write; the stomach's liquid lane, satiety.M, fluids.thirstTarget and THIRST read before and after;
      `action.cancel` on admin after (CLAUDE.md s5).
  OF  THE OVERFULL MOODLE, OWN COLUMN (11c): admin's stomach driven past 730 g and 1100 g by two TKX.Mixed650 eats
      (436.9 g each: 300 water, 81.25 carbohydrate, 25.28 fat, 24.38 protein, 6 fibre) and one 1 L WATER_ITEM drink
      (its server copy filled by fluid.fill, the client's the RCON spawn's, x363's route). After each intake: the
      server record's stomach (its mass, K.stomach.mass), bus.lastSig.admin (the push signature, its fifth digit the
      level at the last flush), then on admin's client `lua.call NutritionRevamp.client.requestMirror`, the arrival
      polled, and the client's mirror stomachMass, moodles.levels.overfull, view.classes.overfull, moodles.route and
      `lua.call NutritionRevamp.client.moodles.probe overfull`. No MoodleFramework in this profile: the own column.
  Z   the mod-error lines, admin not parked, `players`, the clock, the writer's counters. With a dead bus Z's server
      steps are skipped and only its local readings are taken.

THE HOLD (ruling 3, B2-B4): the driver sets `lua.setpath NutritionRevamp.server.store.records.admin.effects.<field>
<target>` at every poll (POLL_S apart, the bus's own pace beyond it), and the setpath's own `before` (the field read on
the same server tick just before the set) is the read-back (DEVIATION 3). The stats read of poll k (and the moodle.level
and the effects reads beside it) is GRADED when set k wrote the target and set k+1's `before` is the target: the field
held from one set to the next, so no K.effects.compose rebuild touched it in between. The hold starts with the first set
and is ESTABLISHED at the first graded read-back (the first `before` equal to the target); only then is admin's client
clock read (time.snapshot `wall`, getTimestampMs) and, for PANIC, `moodle.watch PANIC WATCH_S` armed, at the first poll
at least ARM_SETTLE_S after the establishment whose server PANIC read is at or over the floor (so the client's 1 Hz
stats packet has carried the held level before the watch starts). The driver keeps
setting the target at every poll until `moodle.watch read` answers done and for one poll after, then reads the client
clock again (the hold's end) and restores the field's value from before the hold. A watch transition counts only when
its `at` lies between the two client walls; one outside is dropped and named. The graded game minutes are the world-age
span of the graded polls (stats k to stats k+1). Fewer than MIN_GRADED_MIN graded game minutes reads unmeasured.

LIVENESS AND THE BUDGET (x391h's D1, D2): after any server bus step whose ack is a TimeoutError or RuntimeError the
driver sends `ping`; without a pong out["abort"] says so, every later server step is skipped and the run goes to Z. The
wall budget BUDGET_S (840 s from the driver's t0 before the boot) is checked before each phase against PHASE_EST_S and
inside every poll loop. Teardown, the artifact copy and grading run in finally. A dead-bus phase is void, not falsified.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured / void, each with its falsifier):
  STAGE   the staged MANIFEST equals release_pack.manifest(mod/NutritionRevamp) on a clean tree and the staged files
          hash to it; every deployed NutritionRevamp copy (server and both clients) hashes to it too.
  V       every verify row ok (the version 1.0.0 on the server and both clients; TKX.SnackP's script on both sides).
  A       exactly one server self-report line: v1.0.0, side=server, mode=managed, rates=zeroed, limitations= the code's
          count (the live key count of NutritionRevamp.server.writer.limitations, and STATIC_LIMITS when parsed);
          one client line on each console: v1.0.0, side=client, mode=managed, frameworks=none; the zeroing line once;
          no `Nutrition Makes Sense is loaded` line; writer.zeroed true, mode 1, stats.nms false;
          vanillaRate(HungerIncrease) 9.6e-6 within 1e-12 (#0470, re-read on 42.21: holds); ZomboidGlobals.HungerIncrease
          0; each of the seven saved rates non-zero and its live ZomboidGlobals value 0.
  BF      on each client at view level 2: the body_fat row's text key is UI_NR_FatBand_<word> for the plain band of
          body_fm / body_weight on the amendment's cut table for the sex the view read (view.female); within FAT_BAND
          (0.005) of a cut either neighbouring word is accepted (the hold). view.female agrees with the record's body.sex
          (2 female). A reading of the shipped view, n = 1 per client.
  STATS   B1: between two consecutive stats.all reads with no game-minute boundary between them (less a LAG_MIN drain
          lag) HUNGER, THIRST and FATIGUE are equal: they change only at the writer's ticks. Falsifier: a change between
          two reads inside one game minute. Unmeasured: fewer than MIN_STATS_READS reads or no minute boundary crossed.
  PANIC10 B2: over the graded polls PANIC never reads under 10 - 1.2556 - 0.01 = 8.7344 (#3400's decay at DayLength 1)
          and the watch counts 0 transitions inside the hold. Falsifier: a graded read under 8.7344, or a transition
          inside the hold. Unmeasured: fewer than MIN_GRADED_MIN graded game minutes, the watch not done, or not armed.
  PANIC66 B3: a READING, no threshold: the transitions inside the hold (#3400's predicted flicker within 1.26 of the
          threshold 6) and moodle.level at each graded poll. Unmeasured as PANIC10.
  TEMP    B4: every graded TEMPERATURE read at least TEMP_SKIP_MIN game minutes (the first ten writes) after the
          establishment sits within TEMP_TOL (0.05 C) of the same poll's effects.tempTarget. Falsifier: one off.
          Unmeasured: fewer than MIN_GRADED_MIN graded game minutes after the skip.
  LEAK    ModData.exists("NutritionRevamp.players") false on the server; bob's OnReceiveGlobalModData fires 0 times in
          LEAK_WAIT_S after ModData.request("NutritionRevamp.players"). Falsifier: true, or a firing.
  MIRROR  the two requests: answered +1 and denied +1 on the server. Falsifier: any other pair of deltas.
  PP      a READING: each ring covers the 3 h after the landings (its first window row within PP_EDGE_H of a0, its last within PP_EDGE_H
          of a0 + 3, no gap in the rows' ev); the row count is a reported reading; both eats landed
          (intake.stats.landed +2) with both spawns confirmed. Void: a spawn not confirmed. Unmeasured: short rings.
  WW      with a source: worldSips rises and the stomach's liquid lane rises; satiety.M and THIRST at the next write
          are readings. No source, or no sip in WW_CAP_S: unmeasured, with the reply.
  OF      the own column agrees with its mirror at every read: moodles.levels.overfull = view.classes.overfull = the
          probe's level = fullnessLevel(the mirror's stomachMass) (0 at or under 730 g, then 1 + the rung of the
          discomfort 100 x (mass - 730) / 370 on 33.3, 66.7, 100), route "own"; the server mass passes 730 g and 1100 g.
          Falsifier: a disagreement at an arrived read. Unmeasured: a threshold the server mass never passed (named),
          or no arrival.
  Z       no mod error line; admin not parked; the server alive (players answers a list).

DEVIATIONS from the run sheet's x252a text and amendments, stated before the run:
  1. The phases are the run sheet's S4a list (A, B, H, the mirror limit, world water, the overfull own-column drive,
     the protein pair) plus the amendments' Body fat read; C, D, E, F, G and I are absorbed or dropped (run sheet (b)).
  2. B1 slows the clock to SLOW_MULT for its window: the server answers the bus every 20 ticks or at a minute event
     (PZTestKit_Server.lua's tick poll), so a stats.all costs 0.6-2 s and at DayLength 1 (0.625 s a game minute) every
     pair of reads straddles a write; at true multiplier SLOW_MULT a game minute is 6.25 s, so most pairs fall inside one
     minute and a drift between writes would show. The true multiplier read before is restored after, and read back.
  3. Ruling 3's read-back is the setpath's own `before` (the field read on the server tick of the next set), at every
     poll, in place of a separate `lua.global` once a game minute: the bus cannot answer a command a game minute.
  4. The 0.2 s poll is POLL_S between commands; each poll is two to four server commands, so a poll spans one to four
     game minutes.
  5. The protein pair is a live reading off two rings; the replay grade (the same body, the snack swapped) is left to a
     regrade on the copied ring pages or dropped by the controller (run sheet (c), "the controller's call").
  6. The Body fat read uses lua.read on the client root NutritionRevamp.client (the view module's own state), not
     lua.call: the rows are a table, which lua.call answers only by its key count.
PRE-RUN EDITS after the Opus review of 4d5e1c3e (the driver had not run):
  7. The OF drive runs at true multiplier SLOW_MULT (0.1), read before and restored in a finally as B1 does, so the
     stomach does not empty between intakes: a networked eat ends in real time (#3766).
  8. Every eat.action and drink.action reply is tested as spawned != "found" ("found" or "client", a string,
     PZTestKit_Client.lua:287-292). The first other reply sets P["void"] = "<label>: spawned=<value>" and stops the
     phase (PP stops its rings first), and the PP and OF grades are void.
  9. A hold is graded only from its establishment (hold_summary: k >= est_i, the first graded read-back), so a read
     answered before any write at the target is never graded; B2, B3 and B4 share the rule. TEMP's skip stays.
  10. STATS grades trivial when no stat changed between any two reads; PANIC10 and PANIC66 are measured only with a
      watch of samples > 0 and a non-nil min and max.
  11. PP is graded on coverage: the window's first row within PP_EDGE_H (0.1 h) of the landing age, its last within
      0.1 h of +3 h, and no gap in the rows' ev; the row count is a reported reading (PP_MIN_ROWS is gone).
  12. PROBE_RX is applied to the self-report, zeroing, Overlay and NMS greps only (grep_noecho probe=True); Z's
      mod-error filter drops the bus echo (ECHO_RX) and a line that opens with a command's name (CMD_ECHO_RX) and keeps
      a real mod error that mentions requestMirror or ModData.
  13. B3's summary records the first armed poll (first_armed: its PANIC, level and the arm reply's level).

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time. 4. A session killed
by the host is reported, and its measured phases are never re-run to replace their figures (ruling H2-1).
"""
import ctypes
import glob
import hashlib
import importlib.util
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


PROFILE = "x40-accept"
PREFIX = "x401"
SESSION = ("Plan 11b Task 4, session S4a (x401): the 1.0.0 release in Managed mode on fixture two -- the self-reports and "
           "the zeroed rates, the Body fat row, the stats hold, the PANIC holds at 10 and 6.6 with their moodle watches, "
           "the TEMPERATURE hold, the closed leak, the mirror limit, the protein pair, world water and the overfull "
           "moodle's own column; one boot of " + PROFILE)
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert PROFILE == "x40-accept", f"PROFILE {PROFILE} is not this driver's"
ARTIFACT = "accept.json"
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
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_SERVER = LUA_DIR + "/server/PZTestKit_Server.lua"
HARNESS_CLIENT = LUA_DIR + "/client/PZTestKit_Client.lua"
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
EXPECT_MODE = "managed"
VANILLA_HUNGER_RATE = 9.6e-6        # #0470 (42.20.4; re-read on 42.21: holds)
RATE_TOL = 1e-12
RATE_KEYS = ("HungerIncrease", "HungerIncreaseWhenWellFed", "HungerIncreaseWhileAsleep", "HungerIncreaseWhenExercise",
             "ThirstIncrease", "ThirstSleepingIncrease", "FatigueIncrease")      # NR_Server_Writer.lua W.RATE_KEYS
# BF: the amendment's cut table (task-3-amendments.md item 3, the 20-39 y column), fractions; lower bounds of bands 1-4
FAT_CUTS = {"male": (0.06, 0.08, 0.20, 0.25), "female": (0.13, 0.21, 0.33, 0.39)}
FAT_WORDS = ("veryLean", "lean", "healthy", "high", "veryHigh")
FAT_BAND = 0.005
ROW_SCAN = 40
# B1
SLOW_MULT = 0.1
STATS_S = 30.0
LAG_MIN = 0.1                       # game minutes: the drain's lag after a minute event (a few ticks at SLOW_MULT)
MIN_STATS_READS = 10
# B2-B4
POLL_S = 0.2
WATCH_S = 60
PANIC_HI, PANIC_LO = 10.0, 6.6
PANIC_DECAY_MAX = 1.2556            # #3400: vanilla's PANIC decay between writes at DayLength 1
PANIC_SLACK = 0.01
TEMP_OFFSET = 0.5
TEMP_TOL = 0.05
TEMP_SKIP_MIN = 10.0                # the first ten graded writes, one a game minute
TEMP_HOLD_S = 40.0                  # wall seconds after the establishment
HOLD_CAP_S = 110.0                  # wall seconds from a hold's first set: the cap on every hold
EST_CAP_S = 20.0                    # a hold not established inside this many wall seconds stops (unmeasured)
ARM_SETTLE_S = 3.0                  # wall seconds from the establishment before a watch is armed
MIN_GRADED_MIN = 10.0
# H
LEAK_KEY = "NutritionRevamp.players"
LEAK_WAIT_S = 5.0
# ML
ML_SETTLE_S = 2.5
# PP
SNACK_P, SNACK_C = "TKX.SnackP", "TKX.SnackC"
RING_PATHS = ("satiety.M", "satiety.S", "satiety.t", "stomach.liquid", "body.energyState", "fluids.thirstTarget")
PP_HOURS = 3.0
PP_CAP_S = 90.0
PP_EDGE_H = 0.1            # the window's first row within this of a0, its last within this of a0 + PP_HOURS
SPEED_FAST = 5
LAND_CAP_S = 30.0
# WW
WW_CAP_S = 40.0
WRITE_CAP_S = 10.0
# OF
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
# spawns
SPAWN_WAIT_S = 2.5
SEEN_CAP_S = 10.0
# liveness and the wall budget
PING_TIMEOUT_S = 5
BUDGET_S = 840.0
PHASE_EST_S = {"S0": 20.0, "A": 20.0, "BF": 15.0, "B1": 45.0, "B2": 90.0, "B3": 95.0, "B4": 65.0, "H": 12.0,
               "ML": 10.0, "PP": 75.0, "WW": 45.0, "OF": 90.0}
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
    "A": {"server self-report lines": 1, "server": {"version": EXPECT_VERSION, "side": "server", "mode": EXPECT_MODE,
                                                    "rates": "zeroed", "limitations": "the code's count"},
          "client lines": "one on each console: version, side=client, mode=managed, frameworks=none",
          "zeroing line": 1, "Nutrition Makes Sense warning lines": 0,
          "writer.zeroed": True, "writer.mode": 1, "writer.stats.nms": False,
          "vanillaRate(HungerIncrease)": f"{VANILLA_HUNGER_RATE} within {RATE_TOL} (#0470)",
          "ZomboidGlobals.HungerIncrease": 0, "saved rates": "each non-zero, its live ZomboidGlobals value 0",
          "falsifier": "any of these off"},
    "BF": {"view level": 2, "body_fat text": "UI_NR_FatBand_<word> of the plain band of body_fm/body_weight on "
                                            "FAT_CUTS for view.female (either neighbour within FAT_BAND of a cut)",
           "view.female": "agrees with the record's body.sex (2 female)", "n": "1 per client",
           "falsifier": "a word off the predicted band, or the sex disagreeing",
           "unmeasured": "no body_fat row (level not 2, no rows, no body)"},
    "STATS": {"HUNGER, THIRST, FATIGUE": "equal between two consecutive reads with no game-minute boundary between "
                                         f"them (less a {LAG_MIN} min drain lag)",
              "falsifier": "a change inside one game minute",
              "unmeasured": f"fewer than {MIN_STATS_READS} reads or no boundary crossed"},
    "PANIC10": {"graded PANIC reads": f">= {PANIC_HI} - {PANIC_DECAY_MAX} - {PANIC_SLACK}",
                "watch transitions inside the hold": 0,
                "falsifier": "a graded read under the floor, or a transition inside the hold",
                "unmeasured": f"under {MIN_GRADED_MIN} graded game minutes, the watch not armed or not done"},
    "PANIC66": {"reading": "no threshold: transitions inside the hold (#3400's flicker) and moodle.level per poll",
                "unmeasured": "as PANIC10"},
    "TEMP": {"graded TEMPERATURE reads after the first ten writes": f"within {TEMP_TOL} C of effects.tempTarget",
             "falsifier": "one off", "unmeasured": f"under {MIN_GRADED_MIN} graded game minutes after the skip"},
    "LEAK": {"server ModData.exists(NutritionRevamp.players)": False, "bob OnReceiveGlobalModData firings": 0,
             "falsifier": "true, or a firing"},
    "MIRROR": {"answered delta": 1, "denied delta": 1, "falsifier": "any other pair"},
    "PP": {"reading": "each player's HUNGER over 3 game hours off its own ring (two bodies; the replay arm is not run "
                      "here)", "rings": f"each ring covers the 3 h: first row within {PP_EDGE_H} h of the landing, last within {PP_EDGE_H} h of +3 h, no ev gap", "landed": "+2",
           "void": "a spawn not confirmed", "unmeasured": "short rings or a landing missing"},
    "WW": {"with a source": "worldSips rises and stomach.liquid rises; satiety.M and THIRST at the next write read",
           "unmeasured": "no source within 10 tiles, or no sip", "falsifier": "a sip with no liquid rise"},
    "OF": {"each arrived read": "levels.overfull = view.classes.overfull = probe level = fullnessLevel(mirror "
                                "stomachMass); route own",
           "server mass": "passes 730 g and 1100 g",
           "falsifier": "a disagreement at an arrived read",
           "unmeasured": "a threshold never passed (named), or no arrival"},
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
            tl.mark("error", phase=name, detail=str(e)[:200])
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


def fat_bands(frac, female):
    """The plain band of frac on the sex's cuts, and every band a FAT_BAND hold could keep instead."""
    cuts = FAT_CUTS["female" if female else "male"]
    plain = sum(1 for c in cuts if frac >= c)
    ok = {plain}
    for i, c in enumerate(cuts):
        if abs(frac - c) <= FAT_BAND:
            ok.update({i, i + 1})
    return plain, sorted(ok)


def stomach_mass(v):
    parts = [num(v.get(p)) for p in STOMACH_PARTS]
    if any(x is None for x in parts):
        return None
    return sum(parts)


# ---------------------------------------------------------------- the stage check (before the boot)
def load_release_pack():
    spec = importlib.util.spec_from_file_location("x401_release_pack", os.path.join(REPO, "tools", "release_pack.py"))
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


def phase_A():
    P = out["phases"]["A"] = {}
    W = f"{NR}.server.writer"
    P["zeroed"] = gread(SRV, f"{W}.zeroed", "A_zeroed")
    P["mode"] = gread(SRV, f"{W}.mode", "A_mode")
    P["nms"] = gread(SRV, f"{W}.stats.nms", "A_nms")
    P["limitations"] = gread(SRV, f"{W}.limitations", "A_limitations")
    P["vanillaRate"] = keep(step("A_vanillaRate", SRV, "lua.call", f"{NR}.vanillaRate HungerIncrease"))
    P["zg_hunger"] = gread(SRV, "ZomboidGlobals.HungerIncrease", "A_zg_hunger")
    paths = [f"{W}.saved.{k}" for k in RATE_KEYS] + [f"ZomboidGlobals.{k}" for k in RATE_KEYS]
    P["rates"] = lread(SRV, "_G", paths, "A_rates")
    P["version"] = {s: lread(s, "_G", [f"{NR}.version", f"{NR}.build"], f"A_version_{s.replace(':', '_')}")
                    for s in (SRV, ADMIN, BOB)}


def phase_BF():
    P = out["phases"]["BF"] = {}
    for side in CLIENT_SIDES:
        u = side.split(":", 1)[1]
        R = P[u] = {}
        paths = ["view.level", "view.female", "view.fatBand", "received", "mirror.body_fm", "mirror.body_weight",
                 "view.stats.rebuilds"] + [f"view.rows.{i}.key" for i in range(1, ROW_SCAN + 1)]
        a = lread(side, f"{NR}.client", paths, f"BF_scan_{u}")
        v = vals(a)
        R["scan"] = {k: v.get(k) for k in paths[:7]}
        R["scan_missing"] = a.get("missing")
        R["row_keys"] = [v.get(f"view.rows.{i}.key") for i in range(1, ROW_SCAN + 1)]
        idx = next((i for i in range(1, ROW_SCAN + 1) if v.get(f"view.rows.{i}.key") == "body_fat"), None)
        R["row_index"] = idx
        if idx is not None:
            b = lread(side, f"{NR}.client.view.rows.{idx}", ["key", "text", "valueText", "fatBand", "label",
                                                             "labelText"], f"BF_row_{u}")
            R["row"] = vals(b)
            R["row_missing"] = b.get("missing")
        R["record"] = vals(lread(SRV, f"record:{u}", ["body.sex", "body.fm", "body.lm"], f"BF_record_{u}"))


def phase_B1():
    P = out["phases"]["B1"] = {"reads": []}
    P["mult_before"] = snap("B1_mult0")
    m0 = num(P["mult_before"].get("trueMult"))
    P["restore_to"] = m0 if m0 is not None else 1.0
    P["w0"] = num(vals(lread(SRV, "_G", [WRITES], "B1_w0")).get(WRITES))
    try:
        P["slow"] = keep(step("B1_slow", SRV, "time.multiplier", fmtnum(SLOW_MULT)))
        P["mult_slow"] = snap("B1_mult_slow")
        time.sleep(1.0)
        P["window_start"] = wall()
        end = time.time() + STATS_S
        while time.time() < end and not over_budget():
            a = keep(step("B1_stats", SRV, "stats.all", "admin"))
            st = a.get("stats") or {}
            P["reads"].append({"wall": a.get("wall"), "srv_wall": num(a.get("ack_wall")), "age": num(a.get("worldAge")), "mult": num(a.get("mult")),
                               "H": num(st.get("Hunger")), "T": num(st.get("Thirst")), "F": num(st.get("Fatigue"))})
            time.sleep(POLL_S)
        P["window_end"] = wall()
        P["w1"] = num(vals(lread(SRV, "_G", [WRITES], "B1_w1")).get(WRITES))
    finally:
        P["restore"] = keep(step("B1_restore", SRV, "time.multiplier", fmtnum(P["restore_to"])))
        P["mult_after"] = snap("B1_mult1")


def hold(tag, field, target, watch=False, level=False, temp=False, hold_s=None):
    """Ruling 3's hold of effects.<field> at target (see the docstring's THE HOLD)."""
    H = out["phases"][tag] = {"field": field, "target": target, "with_watch": watch, "polls": []}
    fpath = f"{NR}.server.store.records.admin.effects.{field}"
    H["path"] = fpath
    polls = H["polls"]
    start = wall()
    est_i, armed, done, orig_known = None, False, False, False
    try:
        while True:
            if over_budget(3.0):
                H["budget_stop"] = wall()
                note(f"{tag}: stopped at the wall budget")
                break
            if parked():
                H["parked_stop"] = wall()
                break
            s = keep(step(f"{tag}_set", SRV, "lua.setpath", f"{fpath} {fmtnum(target)}"))
            row = {"i": len(polls), "wall": s.get("wall"), "set_ok": s.get("ok"), "before": s.get("before"),
                   "after": s.get("after"), "err": s.get("err") or s.get("raw")}
            if not orig_known:
                H["orig"] = s.get("before")
                orig_known = s.get("ok") is True
            polls.append(row)
            if est_i is None and len(polls) >= 2 and is_target(row.get("before"), target) \
                    and is_target(polls[-2].get("after"), target):
                est_i = row["i"]
                H["est_i"] = est_i
                H["est"] = snap(f"{tag}_est_time", ADMIN)
                H["est_srv_wall"] = row["wall"]
            st = keep(step(f"{tag}_stats", SRV, "stats.all", "admin"))
            ss = st.get("stats") or {}
            row["age"] = num(st.get("worldAge"))
            row["panic"] = num(ss.get("Panic"))
            row["temp"] = num(ss.get("Temperature"))
            row["stats_wall"] = st.get("wall")
            if (watch and est_i is not None and "watch_arm" not in H
                    and wall() - polls[est_i]["wall"] >= ARM_SETTLE_S
                    and row["panic"] is not None and row["panic"] >= target - PANIC_DECAY_MAX - PANIC_SLACK):
                # armed only after the establishment and ARM_SETTLE_S (the client's 1 Hz stats packet has carried the
                # held level), on a server read at or over the floor
                H["watch_arm"] = keep(step(f"{tag}_watch_arm", ADMIN, "moodle.watch", f"PANIC {WATCH_S}"))
                H["armed_i"] = row["i"]
                armed = H["watch_arm"].get("armed") is True
                if not armed:
                    note(f"{tag}: moodle.watch not armed: {str(H['watch_arm'])[:300]}")
            if level:
                lv = keep(step(f"{tag}_level", SRV, "moodle.level", "admin PANIC"))
                row["level"] = lv.get("level")
            if temp:
                e = lread(SRV, "record:admin", ["effects.tempTarget", "effects.tempAdj", "effects.tempOffset"],
                          f"{tag}_eff")
                ev = vals(e)
                row["tempTarget"] = num(ev.get("effects.tempTarget"))
                row["tempAdj"] = num(ev.get("effects.tempAdj"))
                row["tempOffset"] = num(ev.get("effects.tempOffset"))
            if watch and "watch_arm" in H and not armed:
                break                       # the watch did not arm: the hold ends (unmeasured)
            if watch:
                if done:
                    break                   # the one poll after the watch answered done
                if armed:
                    w = keep(step(f"{tag}_watch_read", ADMIN, "moodle.watch", "read"))
                    row["watch_done"] = w.get("done")
                    if w.get("done") is True:
                        done = True
                        H["watch"] = {k: w.get(k) for k in ("ok", "moodle", "done", "samples", "min", "max",
                                                            "transitions", "changes", "level", "err", "wall")}
            elif est_i is not None and hold_s is not None and wall() - polls[est_i]["wall"] >= hold_s:
                break
            if est_i is None and wall() - start >= EST_CAP_S:
                H["est_stop"] = wall()
                note(f"{tag}: not established inside {EST_CAP_S} s")
                break
            if wall() - start >= HOLD_CAP_S:
                H["cap_stop"] = wall()
                note(f"{tag}: stopped at HOLD_CAP_S")
                break
            time.sleep(POLL_S)
    finally:
        if est_i is not None:
            H["end"] = snap(f"{tag}_end_time", ADMIN)
        if watch and armed and not done:
            H["watch_last"] = keep(step(f"{tag}_watch_last", ADMIN, "moodle.watch", "read"))
        if orig_known:
            H["restore"] = keep(step(f"{tag}_restore", SRV, "lua.setpath", f"{fpath} {fmtnum(num(H.get('orig')))}"))
            out["world_changes"]["left_in_place"].append(f"{tag}: effects.{field} held at {target}, then restored to "
                                                         f"{H.get('orig')!r}")
        H["done"] = done
        H["armed"] = armed
    return H


def is_target(v, target):
    x = num(v)
    return x is not None and abs(x - target) < 1e-9


def phase_B2():
    hold("B2", "panicTarget", PANIC_HI, watch=True)


def phase_B3():
    hold("B3", "panicTarget", PANIC_LO, watch=True, level=True)


def phase_B4():
    hold("B4", "tempOffset", TEMP_OFFSET, temp=True, hold_s=TEMP_HOLD_S)


def phase_H():
    P = out["phases"]["H"] = {}
    P["exists_server"] = keep(step("H_exists_srv", SRV, "lua.call", f"ModData.exists {LEAK_KEY}"))
    P["exists_bob"] = keep(step("H_exists_bob", BOB, "lua.call", f"ModData.exists {LEAK_KEY}"))
    P["watch0"] = keep(step("H_watch0", BOB, "event.watch", "OnReceiveGlobalModData"))
    P["request"] = keep(step("H_request", BOB, "lua.call", f"ModData.request {LEAK_KEY}"))
    time.sleep(LEAK_WAIT_S)
    P["watch1"] = keep(step("H_watch1", BOB, "event.watch", "OnReceiveGlobalModData read"))


def phase_ML():
    P = out["phases"]["ML"] = {}
    rq = [f"{NR}.server.bus.requests.stats.answered", f"{NR}.server.bus.requests.stats.denied"]
    P["srv0"] = vals(lread(SRV, "_G", rq, "ML_srv0"))
    P["bob0"] = gread(BOB, f"{NR}.client.received", "ML_bob0")
    P["req1"] = keep(step("ML_req1", BOB, "lua.call", f"{NR}.client.requestMirror"))
    P["req2"] = keep(step("ML_req2", BOB, "lua.call", f"{NR}.client.requestMirror"))
    P["req_gap_s"] = (P["req2"].get("wall") or 0) - (P["req1"].get("wall") or 0)
    time.sleep(ML_SETTLE_S)
    P["srv1"] = vals(lread(SRV, "_G", rq, "ML_srv1"))
    P["bob1"] = gread(BOB, f"{NR}.client.received", "ML_bob1")


def read_ring(user, tag):
    pages, frm = [], None
    for _ in range(4):
        after = time.time() - 1.0
        args = f"{user} read" + ("" if frm is None else f" {frm}")
        r = keep(step(f"{tag}_read", SRV, "minute.ring", args, timeout=60))
        pg = {"reply": {k: r.get(k) for k in ("ok", "from", "rows", "next", "more", "recorded", "overwritten",
                                              "errors", "lastError", "result", "error")}}
        name = r.get("result")
        if isinstance(name, str) and name:
            doc = wait_doc(name, after)
            pg["doc_rows"] = len((doc or {}).get("rows_list") or [])
            if doc is not None:
                dest = f"pp-{name}.json"
                try:
                    # the server's own result file, byte-identical (x36_gut_lib's read_pages)
                    shutil.copyfile(os.path.join(server.bus.results_dir, name + ".json"), os.path.join(run_dir, dest))
                    copied.append(dest)
                    pg["file"] = dest
                except (OSError, AttributeError) as e:
                    pg["copy_error"] = f"{type(e).__name__}: {e}"
                pg["rows"] = doc.get("rows_list") or []
        pages.append(pg)
        if not r.get("ok") or not r.get("more") or r.get("next") is None:
            break
        frm = r.get("next")
    return pages


def phase_PP():
    P = out["phases"]["PP"] = {"spawns": {}, "eats": {}}
    pair = (("admin", SNACK_P), ("bob", SNACK_C))
    for u, f in pair:
        P["spawns"][u] = spawn_confirmed(u, f, 1, f"PP_spawn_{u}")
    if not all(P["spawns"][u]["confirmed"] for u, _ in pair):
        P["void"] = "a spawn not confirmed"
        return
    P["records0"] = {u: vals(lread(SRV, f"record:{u}", list(RING_PATHS), f"PP_rec0_{u}")) for u in USERS}
    P["ring_start"] = {u: keep(step(f"PP_ring_start_{u}", SRV, "minute.ring", " ".join([u, "start"] + list(RING_PATHS))))
                       for u in USERS}
    for u, _ in pair:
        P[f"foodtimer_{u}"] = keep(step(f"PP_foodtimer_{u}", SRV, "foodtimer.set", f"{u} 0")).get("after")
    b = intake("PP_before")
    P["before"] = b
    for u, f in pair:
        q = keep(step(f"PP_eat_{u}", f"client:{u}", "eat.action", f"{f} 1"))
        P["eats"][u] = {k: q.get(k) for k in ("queued", "fraction", "spawned", "itemId", "maxTime", "wall")}
        if q.get("spawned") != "found":
            P["void"] = f"PP_eat_{u}: spawned={q.get('spawned')}"
            note(f"PP: {P['void']}, not 'found'; the phase stops")
            break
    if P.get("void"):
        for u in USERS:
            P[f"ring_stop_{u}"] = keep(step(f"PP_ring_stop_{u}", SRV, "minute.ring", f"{u} stop"))
        return
    end = time.time() + LAND_CAP_S
    P["landed"] = False
    while time.time() < end and not over_budget():
        a = intake("PP_poll")
        if a.get("landed") is not None and b.get("landed") is not None and a["landed"] >= b["landed"] + 2:
            P["landed"] = True
            P["after"] = a
            break
        time.sleep(0.3)
    P["landed_snap"] = snap("PP_landed_t")
    a0 = num(P["landed_snap"].get("worldAge"))
    P["course_from_age"] = a0
    try:
        P["fast"] = rcon(f"settimespeed {SPEED_FAST}", "PP_fast")
        end = time.time() + PP_CAP_S
        ages = []
        while time.time() < end and not over_budget(15.0):
            s = snap("PP_age")
            ages.append(num(s.get("worldAge")))
            if a0 is not None and ages[-1] is not None and ages[-1] >= a0 + PP_HOURS:
                break
            time.sleep(1.0)
        P["ages"] = ages
    finally:
        P["one"] = rcon("settimespeed 1", "PP_one")
    P["end_snap"] = snap("PP_end_t")
    P["records1"] = {u: vals(lread(SRV, f"record:{u}", list(RING_PATHS), f"PP_rec1_{u}")) for u in USERS}
    P["rings"] = {}
    for u in USERS:
        P["rings"][u] = read_ring(u, f"PP_ring_{u}")
        P[f"ring_stop_{u}"] = keep(step(f"PP_ring_stop_{u}", SRV, "minute.ring", f"{u} stop"))
    out["world_changes"]["left_in_place"].append("PP: SnackP eaten by admin, SnackC by bob; 3 game hours at speed 5")


def phase_WW():
    P = out["phases"]["WW"] = {}
    rec_paths = ["stomach.liquid", "satiety.M", "fluids.thirstTarget", "fluids.water"]
    P["rec0"] = vals(lread(SRV, "record:admin", rec_paths, "WW_rec0"))
    P["in0"] = intake("WW_in0")
    st = keep(step("WW_stats0", SRV, "stats.all", "admin"))
    P["thirst0"] = num((st.get("stats") or {}).get("Thirst"))
    P["take"] = keep(step("WW_take", ADMIN, "water.take", "admin"))
    if not P["take"].get("queued"):
        P["unmeasured"] = f"water.take not queued: {why(P['take']) or P['take'].get('reason')}"
        note(f"WW: {P['unmeasured']}")
        return
    try:
        end = time.time() + WW_CAP_S
        last, still, rose = P["in0"].get("worldSips"), 0, False
        polls = []
        while time.time() < end and not over_budget(10.0):
            if parked():
                break
            a = intake("WW_poll")
            s = a.get("worldSips")
            polls.append({"wall": a.get("wall"), "worldSips": s})
            if s is not None and last is not None and s > last:
                rose, still = True, 0
            elif rose:
                still += 1
            last = s
            if rose and still >= 3:
                break
            time.sleep(0.3)
        P["polls"] = polls
        P["rose"] = rose
        P["in1"] = intake("WW_in1")
        w1 = P["in1"].get("writer.stats.writes")
        end = time.time() + WRITE_CAP_S
        while time.time() < end and w1 is not None and not over_budget(5.0):
            a = intake("WW_wpoll")
            if a.get("writer.stats.writes") is not None and a["writer.stats.writes"] >= w1 + 2:
                P["in2"] = a
                break
            time.sleep(0.3)
        st = keep(step("WW_stats1", SRV, "stats.all", "admin"))
        P["thirst1"] = num((st.get("stats") or {}).get("Thirst"))
        P["thirst1_age"] = num(st.get("worldAge"))
        P["rec1"] = vals(lread(SRV, "record:admin", rec_paths, "WW_rec1"))
    finally:
        P["cancel"] = keep(step("WW_cancel", ADMIN, "action.cancel"))
        out["world_changes"]["left_in_place"].append("WW: water.take on admin, then action.cancel")


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


def phase_OF():
    """The overfull drive at true multiplier SLOW_MULT (DEVIATION 7), read before and restored in a finally as B1 does."""
    P = out["phases"]["OF"] = {"steps": [], "intakes": []}
    P["mult_before"] = snap("OF_mult0")
    m0 = num(P["mult_before"].get("trueMult"))
    P["restore_to"] = m0 if m0 is not None else 1.0
    try:
        P["slow"] = keep(step("OF_slow", SRV, "time.multiplier", fmtnum(SLOW_MULT)))
        P["mult_slow"] = snap("OF_mult_slow")
        of_drive(P)
    finally:
        P["restore"] = keep(step("OF_restore", SRV, "time.multiplier", fmtnum(P["restore_to"])))
        P["mult_after"] = snap("OF_mult1")


def of_drive(P):
    rc0 = num(gread(ADMIN, f"{NR}.client.received", "OF_rc0").get("value"))
    last_req = None
    plan = (("eat1", "eat", MIX650), ("eat2", "eat", MIX650), ("drink", "drink", WATER_ITEM))
    for label, kind, ftype in plan:
        if over_budget(15.0):
            note(f"OF: {label} skipped at the wall budget")
            break
        sp = spawn_confirmed("admin", ftype, 1, f"OF_{label}_spawn")
        it = {"label": label, "kind": kind, "spawn": sp}
        P["intakes"].append(it)
        if not sp["confirmed"]:
            P["void"] = f"{label}: spawn not confirmed"
            break
        if kind == "eat":
            it["eat"] = eat("admin", ftype, f"OF_{label}")
            ok = it["eat"].get("landed") and not it["eat"].get("client_spawned")
        else:
            it["drink"] = drink("admin", ftype, WATER_FLUID, WATER_L, f"OF_{label}")
            ok = it["drink"].get("drank") and not it["drink"].get("client_spawned")
        cs = (it.get("eat") or it.get("drink") or {}).get("client_spawned")
        if cs:
            P["void"] = f"{label}: {cs}"
            P["void_spawn"] = True
            note(f"OF: {P['void']}, not 'found'; the drive stops")
            break
        if not ok:
            note(f"OF: {label} did not land")
        if last_req is not None and time.time() - last_req < REQUEST_GAP_S:
            time.sleep(REQUEST_GAP_S - (time.time() - last_req))
        last_req = time.time()
        R, rc0 = overfull_read(f"OF_{label}_read", rc0)
        R["after"] = label
        P["steps"].append(R)
    out["world_changes"]["left_in_place"].append("OF: two TKX.Mixed650 eaten and a WaterBottle drunk by admin")


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


PHASES = (("S0", phase_S0), ("A", phase_A), ("BF", phase_BF), ("B1", phase_B1), ("B2", phase_B2), ("B3", phase_B3),
          ("B4", phase_B4), ("H", phase_H), ("ML", phase_ML), ("PP", phase_PP), ("WW", phase_WW), ("OF", phase_OF))


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


def grade_A():
    A = out["phases"].get("A") or {}
    Ls = g(out, "logs", "server") or {}
    lines = Ls.get("self") or []
    srv = parse_self(lines[0], SELF_SRV_RX) if lines else None
    cli = {}
    for u, rows in (g(out, "logs", "clients") or {}).items():
        sl = [ln for r in rows for ln in (r.get("self") or [])]
        cli[u] = {"lines": len(sl), "parsed": parse_self(sl[0], SELF_CLI_RX) if sl else None}
    live_limits = num(g(A, "limitations", "keyCount"))
    static = g(out, "stage", "static_limitations")
    rates = g(A, "rates", "values") or {}
    saved = {k: num(rates.get(f"{NR}.server.writer.saved.{k}")) for k in RATE_KEYS}
    live = {k: num(rates.get(f"ZomboidGlobals.{k}")) for k in RATE_KEYS}
    vr = num(g(A, "vanillaRate", "r1"))
    zg = num(val(A.get("zg_hunger")))
    obs = {"server_lines": len(lines), "server": srv, "clients": cli, "zero_lines": len(Ls.get("zero") or []),
           "nms_lines": Ls.get("nms") or [], "zeroed": val(A.get("zeroed")), "mode": val(A.get("mode")),
           "nms_flag": val(A.get("nms")), "limitations_live": live_limits, "limitations_static": static,
           "vanillaRate": vr, "zg_hunger": zg, "saved": saved, "live": live,
           "versions": {s: vals(v) for s, v in (A.get("version") or {}).items()}}
    S = out["summaries"]["A"] = obs
    bad = []
    if len(lines) != 1 or srv is None:
        bad.append("server self-report lines != 1")
    else:
        for k, want in (("version", EXPECT_VERSION), ("side", "server"), ("mode", EXPECT_MODE), ("rates", "zeroed")):
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
        for k, want in (("version", EXPECT_VERSION), ("side", "client"), ("mode", EXPECT_MODE),
                        ("frameworks", "none")):
            if p.get(k) != want:
                bad.append(f"{u} {k}={p.get(k)!r}")
    if obs["zero_lines"] != 1:
        bad.append(f"zero lines {obs['zero_lines']}")
    if obs["nms_lines"]:
        bad.append("a Nutrition Makes Sense warning")
    if obs["zeroed"] is not True or num(obs["mode"]) != 1 or obs["nms_flag"] is not False:
        bad.append("writer zeroed/mode/nms flag")
    if vr is None or abs(vr - VANILLA_HUNGER_RATE) > RATE_TOL:
        bad.append(f"vanillaRate {vr}")
    if zg is None or zg != 0:
        bad.append(f"ZomboidGlobals.HungerIncrease {zg}")
    for k in RATE_KEYS:
        if saved[k] is None or saved[k] == 0 or live[k] != 0:
            bad.append(f"rate {k}: saved {saved[k]} live {live[k]}")
    for s, v in obs["versions"].items():
        if v.get(f"{NR}.version") != EXPECT_VERSION:
            bad.append(f"{s} version {v.get(f'{NR}.version')!r}")
    if not A:
        grade("A", PRED["A"], obs, "void" if phase_dead("A") or bus["dead"] else "unmeasured", "phase A not run")
    else:
        grade("A", PRED["A"], obs, "falsified" if bad else "as_predicted", PRED["A"]["falsifier"], {"bad": bad})
    return S


def grade_BF():
    P = out["phases"].get("BF") or {}
    res, bad, unm = {}, [], []
    for u in USERS:
        R = P.get(u) or {}
        sc = R.get("scan") or {}
        row = R.get("row") or {}
        fm, w = num(sc.get("mirror.body_fm")), num(sc.get("mirror.body_weight"))
        female = sc.get("view.female")
        sex = num((R.get("record") or {}).get("body.sex"))
        r = {"level": sc.get("view.level"), "female": female, "record_sex": sex, "fm": fm, "weight": w,
             "row_index": R.get("row_index"), "text": row.get("text"), "valueText": row.get("valueText"),
             "fatBand": row.get("fatBand")}
        if num(sc.get("view.level")) != 2 or R.get("row_index") is None or fm is None or w is None or not w > 0:
            unm.append(u)
            r["status"] = "unmeasured"
        else:
            frac = fm / w
            plain, okb = fat_bands(frac, female is True)
            r.update({"fraction": frac, "plain_band": plain, "accepted_bands": okb,
                      "predicted_key": "UI_NR_FatBand_" + FAT_WORDS[plain],
                      "accepted_keys": ["UI_NR_FatBand_" + FAT_WORDS[i] for i in okb]})
            sex_ok = sex is None or (female is True) == (sex == 2)
            r["sex_agrees"] = sex_ok if sex is not None else None
            if row.get("text") not in r["accepted_keys"] or not sex_ok:
                bad.append(u)
                r["status"] = "falsified"
            else:
                r["status"] = "as_predicted"
        res[u] = r
    out["summaries"]["BF"] = res
    if not P:
        grade("BF", PRED["BF"], None, "void" if phase_dead("BF") or bus["dead"] else "unmeasured", "phase BF not run")
    elif bad:
        grade("BF", PRED["BF"], res, "falsified", PRED["BF"]["falsifier"], {"bad": bad, "unmeasured": unm})
    elif len(unm) == len(USERS):
        grade("BF", PRED["BF"], res, "unmeasured", PRED["BF"]["unmeasured"], {"unmeasured": unm})
    else:
        grade("BF", PRED["BF"], res, "as_predicted", PRED["BF"]["falsifier"], {"unmeasured": unm})


def minute_index(age, lag=0.0):
    return math.floor(age * 60.0 - lag + 1e-9)


def grade_STATS():
    P = out["phases"].get("B1") or {}
    rd = [r for r in P.get("reads") or [] if r.get("age") is not None]
    off, crossings, changes = [], 0, {"H": 0, "T": 0, "F": 0}
    for a, b in zip(rd, rd[1:]):
        boundary = minute_index(b["age"]) > minute_index(a["age"], LAG_MIN)
        if minute_index(b["age"]) > minute_index(a["age"]):
            crossings += 1
        for k in ("H", "T", "F"):
            if a.get(k) is not None and b.get(k) is not None and a[k] != b[k]:
                changes[k] += 1
                if not boundary:
                    off.append({"stat": k, "a": a, "b": b})
    obs = {"reads": len(rd), "crossings": crossings, "changes": changes, "off_boundary": off[:10],
           "writes": [P.get("w0"), P.get("w1")], "mult": [g(P, "mult_before", "trueMult"), g(P, "mult_slow", "trueMult"),
                                                          g(P, "mult_after", "trueMult")],
           "span_game_min": (rd[-1]["age"] - rd[0]["age"]) * 60.0 if len(rd) >= 2 else None}
    out["summaries"]["STATS"] = obs
    if phase_dead("B1"):
        grade("STATS", PRED["STATS"], obs, "void", "the server bus died inside B1")
    elif off:
        grade("STATS", PRED["STATS"], obs, "falsified", PRED["STATS"]["falsifier"])
    elif len(rd) < MIN_STATS_READS or crossings == 0:
        grade("STATS", PRED["STATS"], obs, "unmeasured", PRED["STATS"]["unmeasured"])
    elif sum(changes.values()) == 0:
        grade("STATS", PRED["STATS"], obs, "trivial", "no stat changed between any two reads: nothing was held against")
    else:
        grade("STATS", PRED["STATS"], obs, "as_predicted", PRED["STATS"]["falsifier"])


def hold_summary(tag):
    H = out["phases"].get(tag) or {}
    polls = H.get("polls") or []
    target = H.get("target")
    graded = []
    est_i = H.get("est_i")
    for k in range(len(polls) - 1):
        # graded only from the establishment (the first graded read-back): a read answered before any write at the
        # target is never graded
        if est_i is not None and k >= est_i and is_target(polls[k].get("after"), target)                 and is_target(polls[k + 1].get("before"), target):
            graded.append(k)
    span = 0.0
    for k in graded:
        a, b = polls[k].get("age"), polls[k + 1].get("age")
        if a is not None and b is not None and b >= a:
            span += (b - a) * 60.0
    ungraded = [k for k in range(len(polls) - 1) if k not in graded]
    est_w, end_w = num(g(H, "est", "ack_wall")), num(g(H, "end", "ack_wall"))
    w = H.get("watch") if isinstance(H.get("watch"), dict) else {}
    ch = as_list(w.get("changes"))
    inside = [c for c in ch if isinstance(c, dict) and est_w is not None and end_w is not None
              and est_w <= (num(c.get("at")) or -1) <= end_w]
    outside = [c for c in ch if c not in inside]
    S = {"polls": len(polls), "graded": len(graded), "graded_game_min": span, "ungraded_polls": ungraded,
         "est_i": H.get("est_i"), "est_wall": est_w, "end_wall": end_w, "armed": H.get("armed"), "done": H.get("done"),
         "watch": {k: w.get(k) for k in ("samples", "min", "max", "transitions", "level", "err")},
         "transitions_inside": len(inside), "changes_inside": inside, "changes_outside_dropped": outside,
         "orig": H.get("orig"), "restored": g(H, "restore", "after")}
    ai = H.get("armed_i")
    if ai is not None and 0 <= ai < len(polls):
        S["first_armed"] = {"i": ai, "panic": polls[ai].get("panic"), "level": polls[ai].get("level"),
                            "age": polls[ai].get("age"), "arm_reply_level": g(H, "watch_arm", "level")}
    return H, polls, graded, S


def grade_PANIC(tag, phase_name, target, is_reading):
    H, polls, graded, S = hold_summary(tag)
    floor = target - PANIC_DECAY_MAX - PANIC_SLACK
    reads = [polls[k].get("panic") for k in graded]
    S["floor"] = floor
    S["panic_graded"] = {"n": len([x for x in reads if x is not None]),
                         "min": min([x for x in reads if x is not None], default=None),
                         "max": max([x for x in reads if x is not None], default=None)}
    S["low"] = [{"i": k, "panic": polls[k].get("panic"), "age": polls[k].get("age")} for k in graded
                if polls[k].get("panic") is not None and polls[k]["panic"] < floor]
    if is_reading:
        S["levels_graded"] = [polls[k].get("level") for k in graded]
    out["summaries"][phase_name] = S
    if not H:
        grade(phase_name, PRED[phase_name], None, "void" if phase_dead(tag) or bus["dead"] else "unmeasured", f"phase {tag} not run")
        return
    if phase_dead(tag):
        grade(phase_name, PRED[phase_name], S, "void", "the server bus died inside the hold")
        return
    wt = S["watch"]
    measured = (S["graded_game_min"] >= MIN_GRADED_MIN and S["armed"] and S["done"] and (num(wt.get("samples")) or 0) > 0
                and num(wt.get("min")) is not None and num(wt.get("max")) is not None)
    if not measured:
        grade(phase_name, PRED[phase_name], S, "unmeasured", PRED[phase_name]["unmeasured"])
    elif is_reading:
        grade(phase_name, PRED[phase_name], S, "as_predicted", "a reading (no threshold)")
    elif S["low"] or S["transitions_inside"] > 0:
        grade(phase_name, PRED[phase_name], S, "falsified", PRED[phase_name]["falsifier"])
    else:
        grade(phase_name, PRED[phase_name], S, "as_predicted", PRED[phase_name]["falsifier"])


def grade_TEMP():
    H, polls, graded, S = hold_summary("B4")
    est_i = H.get("est_i")
    est_age = polls[est_i].get("age") if est_i is not None and est_i < len(polls) else None
    late = [k for k in graded if est_age is not None and polls[k].get("age") is not None
            and polls[k]["age"] >= est_age + TEMP_SKIP_MIN / 60.0]
    span = 0.0
    for k in late:
        a, b = polls[k].get("age"), polls[k + 1].get("age")
        if a is not None and b is not None and b >= a:
            span += (b - a) * 60.0
    rows = [{"i": k, "temp": polls[k].get("temp"), "tempTarget": polls[k].get("tempTarget"),
             "diff": (polls[k]["temp"] - polls[k]["tempTarget"]) if polls[k].get("temp") is not None
             and polls[k].get("tempTarget") is not None else None} for k in late]
    off = [r for r in rows if r["diff"] is None or not (num(r["tempTarget"]) or 0) > 0 or abs(r["diff"]) > TEMP_TOL]
    S.update({"est_age": est_age, "late_graded": len(late), "late_game_min": span, "rows": rows, "off": off,
              "max_abs_diff": max([abs(r["diff"]) for r in rows if r["diff"] is not None], default=None)})
    out["summaries"]["TEMP"] = S
    if not H:
        grade("TEMP", PRED["TEMP"], None, "void" if phase_dead("B4") or bus["dead"] else "unmeasured", "phase B4 not run")
    elif phase_dead("B4"):
        grade("TEMP", PRED["TEMP"], S, "void", "the server bus died inside the hold")
    elif span < MIN_GRADED_MIN or not late:
        grade("TEMP", PRED["TEMP"], S, "unmeasured", PRED["TEMP"]["unmeasured"])
    elif off:
        grade("TEMP", PRED["TEMP"], S, "falsified", PRED["TEMP"]["falsifier"])
    else:
        grade("TEMP", PRED["TEMP"], S, "as_predicted", PRED["TEMP"]["falsifier"])


def grade_LEAK():
    P = out["phases"].get("H") or {}
    ex = g(P, "exists_server", "r1")
    c0, c1 = num(g(P, "watch0", "count")), num(g(P, "watch1", "count"))
    fires = (c1 - c0) if c0 is not None and c1 is not None else None
    obs = {"exists_server": ex, "exists_bob": g(P, "exists_bob", "r1"), "hooked": g(P, "watch0", "hooked"),
           "count": [c0, c1], "firings": fires, "fires": g(P, "watch1", "fires"),
           "request": {k: g(P, "request", k) for k in ("ok", "r1", "err", "failedAt")}}
    out["summaries"]["LEAK"] = obs
    if not P:
        grade("LEAK", PRED["LEAK"], None, "void" if phase_dead("H") or bus["dead"] else "unmeasured", "phase H not run")
    elif phase_dead("H"):
        grade("LEAK", PRED["LEAK"], obs, "void", "the server bus died inside H")
    elif ex is None or fires is None or g(P, "watch0", "hooked") is not True or g(P, "request", "ok") is not True:
        grade("LEAK", PRED["LEAK"], obs, "unmeasured", "a read or the request did not answer")
    elif ex is not False or fires != 0:
        grade("LEAK", PRED["LEAK"], obs, "falsified", PRED["LEAK"]["falsifier"])
    else:
        grade("LEAK", PRED["LEAK"], obs, "as_predicted", PRED["LEAK"]["falsifier"])


def grade_MIRROR():
    P = out["phases"].get("ML") or {}
    a0 = num((P.get("srv0") or {}).get(f"{NR}.server.bus.requests.stats.answered"))
    a1 = num((P.get("srv1") or {}).get(f"{NR}.server.bus.requests.stats.answered"))
    d0 = num((P.get("srv0") or {}).get(f"{NR}.server.bus.requests.stats.denied"))
    d1 = num((P.get("srv1") or {}).get(f"{NR}.server.bus.requests.stats.denied"))
    da = (a1 - a0) if None not in (a0, a1) else None
    dd = (d1 - d0) if None not in (d0, d1) else None
    obs = {"answered": [a0, a1], "denied": [d0, d1], "answered_delta": da, "denied_delta": dd,
           "req_gap_s": P.get("req_gap_s"), "req_ok": [g(P, "req1", "r1"), g(P, "req2", "r1")],
           "bob_received": [val(P.get("bob0")), val(P.get("bob1"))]}
    out["summaries"]["MIRROR"] = obs
    if not P:
        grade("MIRROR", PRED["MIRROR"], None, "void" if phase_dead("ML") or bus["dead"] else "unmeasured", "phase ML not run")
    elif phase_dead("ML"):
        grade("MIRROR", PRED["MIRROR"], obs, "void", "the server bus died inside ML")
    elif da is None or dd is None or g(P, "req1", "r1") is not True or g(P, "req2", "r1") is not True:
        grade("MIRROR", PRED["MIRROR"], obs, "unmeasured", "a counter unread or a request not sent")
    elif da == 1 and dd == 1:
        grade("MIRROR", PRED["MIRROR"], obs, "as_predicted", PRED["MIRROR"]["falsifier"])
    else:
        grade("MIRROR", PRED["MIRROR"], obs, "falsified", PRED["MIRROR"]["falsifier"])


def ring_course(pages, a0):
    rows = {}
    for pg in pages or []:
        for r in pg.get("rows") or []:
            if isinstance(r, dict) and r.get("age") is not None:
                rows[(r.get("s"), r.get("age"))] = r
    rr = sorted(rows.values(), key=lambda r: r["age"])
    if a0 is None:
        return {"rows": len(rr)}
    win = [r for r in rr if a0 <= r["age"] <= a0 + PP_HOURS]
    hs = [num(r.get("HUNGER")) for r in win if num(r.get("HUNGER")) is not None]
    evs = [r.get("ev") for r in win]
    gaps = [{"after_age": win[i]["age"], "ev": [evs[i], evs[i + 1]]} for i in range(len(win) - 1)
            if isinstance(evs[i], (int, float)) and isinstance(evs[i + 1], (int, float)) and evs[i + 1] - evs[i] > 1]
    first_d = (win[0]["age"] - a0) if win else None
    last_d = (a0 + PP_HOURS - win[-1]["age"]) if win else None
    return {"rows": len(rr), "window_rows": len(win), "first_gap_h": first_d, "last_gap_h": last_d,
            "ev_gaps": gaps,
            "covered": bool(win) and first_d <= PP_EDGE_H and last_d <= PP_EDGE_H and not gaps,
            "hunger_first": hs[0] if hs else None,
            "hunger_last": hs[-1] if hs else None, "hunger_mean": (sum(hs) / len(hs)) if hs else None,
            "hunger_min": min(hs) if hs else None, "hunger_max": max(hs) if hs else None,
            "hourly": [{"h": h, "HUNGER": next((num(r.get("HUNGER")) for r in rr if r["age"] >= a0 + h), None)}
                       for h in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)]}


def grade_PP():
    P = out["phases"].get("PP") or {}
    a0 = P.get("course_from_age")
    course = {u: ring_course(g(P, "rings", u), a0) for u in USERS}
    obs = {"spawns": {u: g(P, "spawns", u, "confirmed") for u in USERS}, "landed": P.get("landed"),
           "eats": P.get("eats"), "from_age": a0, "ages_last": (P.get("ages") or [None])[-1],
           "course": course, "files": [pg.get("file") for u in USERS for pg in (g(P, "rings", u) or [])],
           "contrast_mean_C_minus_P": (course["bob"].get("hunger_mean") - course["admin"].get("hunger_mean"))
           if None not in (course["bob"].get("hunger_mean"), course["admin"].get("hunger_mean")) else None,
           "replay": "not run by this driver (DEVIATION 5)"}
    out["summaries"]["PP"] = obs
    spawned = any(g(P, "eats", u, "spawned") not in (None, "found") for u in USERS)
    if not P:
        grade("PP", PRED["PP"], None, "void" if phase_dead("PP") or bus["dead"] else "unmeasured", "phase PP not run")
    elif phase_dead("PP"):
        grade("PP", PRED["PP"], obs, "void", "the server bus died inside PP")
    elif P.get("void") or spawned:
        grade("PP", PRED["PP"], obs, "void", PRED["PP"]["void"] + (f" ({P.get('void') or 'a client spawn'})" if spawned or P.get("void") else ""))
    elif not P.get("landed") or not all(course[u].get("covered") for u in USERS):
        grade("PP", PRED["PP"], obs, "unmeasured", PRED["PP"]["unmeasured"])
    else:
        grade("PP", PRED["PP"], obs, "as_predicted", "a reading (no threshold)")


def grade_WW():
    P = out["phases"].get("WW") or {}
    r0, r1 = P.get("rec0") or {}, P.get("rec1") or {}
    l0, l1 = num(r0.get("stomach.liquid")), num(r1.get("stomach.liquid"))
    obs = {"take": {k: g(P, "take", k) for k in ("ok", "queued", "source", "fluidAmount", "tainted", "reason")},
           "rose": P.get("rose"), "worldSips": [g(P, "in0", "worldSips"), g(P, "in1", "worldSips")],
           "liquid": [l0, l1], "M": [num(r0.get("satiety.M")), num(r1.get("satiety.M"))],
           "thirstTarget": [num(r0.get("fluids.thirstTarget")), num(r1.get("fluids.thirstTarget"))],
           "THIRST": [P.get("thirst0"), P.get("thirst1")], "next_write": bool(P.get("in2")),
           "cancel": {k: g(P, "cancel", k) for k in ("ok", "before", "after", "current", "stopped")}}
    out["summaries"]["WW"] = obs
    if not P:
        grade("WW", PRED["WW"], None, "void" if phase_dead("WW") or bus["dead"] else "unmeasured", "phase WW not run")
    elif phase_dead("WW"):
        grade("WW", PRED["WW"], obs, "void", "the server bus died inside WW")
    elif P.get("unmeasured") or not P.get("rose"):
        grade("WW", PRED["WW"], obs, "unmeasured", P.get("unmeasured") or "no world sip in WW_CAP_S")
    elif l0 is None or l1 is None or not l1 > l0:
        grade("WW", PRED["WW"], obs, "falsified", PRED["WW"]["falsifier"])
    else:
        grade("WW", PRED["WW"], obs, "as_predicted", PRED["WW"]["falsifier"])


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
    safe("grade_A", grade_A)
    safe("grade_BF", grade_BF)
    safe("grade_STATS", grade_STATS)
    safe("grade_PANIC:B2", grade_PANIC, "B2", "PANIC10", PANIC_HI, False)
    safe("grade_PANIC:B3", grade_PANIC, "B3", "PANIC66", PANIC_LO, True)
    safe("grade_TEMP", grade_TEMP)
    safe("grade_LEAK", grade_LEAK)
    safe("grade_MIRROR", grade_MIRROR)
    safe("grade_PP", grade_PP)
    safe("grade_WW", grade_WW)
    safe("grade_OF", grade_OF)
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
                 "bus_note": "The server answers the bus every 20 ticks (2 s at 10 Hz) or at a minute event "
                             "(PZTestKit_Server.lua's tick poll and its EveryOneMinute poll); x391h's server steps took "
                             "0.75-2.0 s. A poll is two to four server commands.",
                 "hold_note": "Ruling 3's read-back is the setpath's `before` (DEVIATION 3).",
                 "clock_note": "DayLength 1: a game minute is 0.625 s of wall at true multiplier 1; B1 runs at "
                               f"true multiplier {SLOW_MULT} (DEVIATION 2)."},
        "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                      if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict,
                                                                             re.Pattern))
                      and k not in ("REPO", "PRED", "PHASES")},
        "predictions": PRED,
        "deviations": [
            "The phases are the run sheet's S4a list plus the amendments' Body fat read; C, D, E, F, G and I are "
            "absorbed or dropped (run sheet (b)).",
            f"B1 runs at true multiplier {SLOW_MULT}, restored after: the server answers the bus every 20 ticks or at "
            "a minute event, so at 0.625 s a game minute every pair of reads would straddle a write.",
            "Ruling 3's read-back is the setpath's own `before`, at every poll, not a lua.global once a game minute.",
            "The 0.2 s poll is POLL_S between commands; a poll is two to four server commands (one to four game "
            "minutes).",
            "The protein pair is a live reading off two rings; the replay arm is left to a regrade or dropped.",
            "The Body fat read is a lua.read of NutritionRevamp.client (the rows are a table lua.call cannot return).",
        ],
        "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                          "left_in_place": []},
        "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
        "summaries": {}, "memory": [],
    }
    S, staged = stage_check()
    out["stage"] = S
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
