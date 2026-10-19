"""x46_lib -- the session engine of Plan 16 Task 9's live sessions x461a-x467: the plan's changes (Tasks 2-8) proven on a
dedicated server, one boot per session, the STAGED copy of mod/ booted (CLAUDE.md s5, x201).

Built on testing/experiments/xlib.py (the bus step, the wall budget, the grade recorder, RCON, the spawn, the abort,
teardown and copy skeleton) and, like x45h_lib.py and x45i_lib.py (the latest libs), on testing/experiments/x45g_lib.py,
which is frozen with x452-x457 and imported unchanged: its Sess's plumbing (the bus step, the clock, the eat, the pairs,
the ring, the store's next save, the x452 day) and its pure grades are reused. Nothing in x45g_lib is patched at import;
x467 alone installs its cadence bands into the frozen module inside the driver's process (x45i's precedent), and a test
installs them through monkeypatch. The pairs are saved under checks.pairs and every PAIRS grade runs at PAIR_SLACK
(0.8 s, Plan 15's live review F3).

THE STAGED COPY. Every profile boots release/plan16-x46/NutritionRevamp/Contents/mods/NutritionRevamp, staged from mod/'s
last commit before the boot (`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan16-x46`);
staged_gate checks it against release_pack.manifest() of mod/ at STAGED_FROM (a git archive) and refuses on a mismatch,
and preboot refuses when STAGED_FROM is not mod/'s last commit.

THE PROFILES (testing/profiles/x46-*.toml; fixture default, admin -debug, PZTestKit and the staged copy, Nutrition
false (ruling T18-1), DayLength 1, build 42.21.0): x46-mod sleep off (the fixture's SleepAllowed and SleepNeeded false);
x46-gut sleep off with TKX_StudyFoods (x363's TKX.MilkSolid); x46-sleep with SleepAllowed and SleepNeeded true.

THE FIRST SIGHT (CLAUDE.md s5, Plan 15 Task 14b). The fixture's character has no store record and no backup on the
character (preboot reads the fixture's players.db: the admin blob holds no "NutritionRevamp" key), so every session
starts on a fresh record, and a fresh record lands its seed plate (W.seedPlate) at first sight. The predictions are the
HEAD replay of each exact schedule from that first sight: testing/experiments/x46_prerun.py, from FIRST_SIGHT (x452b's
live first sight on this fixture: firstSeen 3.0527, the written HUNGER 0.0253, THIRST 0, FATIGUE 0), written to
testing/experiments/x46_prerun.json and re-derived by one command, `python testing/experiments/x46_prerun.py --write`;
preboot re-runs the session's prerun and refuses a boot whose committed predictions are not the HEAD replay's.

THE CLOCK. RCON settimespeed n (time.multiplier only when it fails); x466 alone sets a fractional true multiplier through
time.multiplier (x453b's 0.05); x463a raises time.multiplier with nobody on (x432's 30) and restores it, read back,
before the rejoin (never under a near-stopped clock, #3788). Every setting is restored from the trueMult read at S.

THE SESSIONS (each under 10 wall minutes; a driver per session names its prefix, profile, artifact, budget and PRED):
  x461a plate     (x46-mod)   S (auto-drink off; restored at C from the flag read before), H, W (start.json), F (a can of bolognese, a banana, two broccoli:
                  667.15 kcal), E (speed 5 until the seed plate has emptied: the stomach under EMPTY_G), P (at speed 1
                  the plate eaten, then 0.5 L of Water at once; PLATE_WATCH_H watched at speed 1 with pairs), T (TAIL_H at
                  speed 5), C, R.
  x461b drinks    (x46-gut)   S (auto-drink off), H, W, F (TKX.MilkSolid), E, WA (0.5 L of Water at once, WATCH_M game
                  minutes at speed 1), MI (0.5 L of CowMilk at once from a Base.Milk carton, WATCH_M), SO (speed 5 to the
                  next request, HUNGER at H_REQ, then TKX.MilkSolid eaten at speed 1 and WATCH_M watched), C, R: x363's
                  water, milk and solid on this build, its fills and liquid lane against the replay.
  x462  tooltip   (x46-mod)   S, F (a Banana, a fills-table food), TM (tooltip.measure Banana 1 then 0, the option read
                  before and after), C.
  x463a freeze    (x46-sleep) S, H (FREEZE_PATHS), PRE (a can and 0.25 L of Coffee, PRE_H at speed 1), OFF (the record
                  read; admin quits; the record read away; the ring read and stopped; time.multiplier AWAY_MULT until the
                  world age passes the departure by AWAY_MIN_H; restored and read back; the record read again; the ring
                  started again; admin rejoins from a fresh client restore in <run>/c1b; the resume polled; RETURN_H at
                  speed 1), C, R.
  x463b hardkill  (x46-mod)   S, F (two Bananas), ADV (ADV_H at speed 5), SAVE (a slot write after ADV polled and the
                  backup's writes read, so the character holds its copy; then RCON save: the world and the players
                  saved; else the arm is skipped), EAT (one Banana; the store's after-eat save polled; LATE_H at speed
                  5; the slot file's next write polled and its latest stamp read off its text), KILL (the session's own
                  server PID read, recorded and killed with taskkill; players.db read offline; the session's own client
                  PID recorded and killed), UP (the server started again on the same cache, admin rejoins in <run>/c1b;
                  in the poll iteration that first sees the record: the record, the age, the load rule's counters and
                  the copy; then the inventory), C.
  x464  bodyclock (x46-sleep) S, H (CLOCK_RING), TR (TRACK_H at speed 1), NAP (player.sleep.hold until NAP_H booked,
                  then awake AWAKE_H), FULL (the same to FULL_H), OFF (SleepAllowed read off the run's ini; the age read,
                  then RCON changeoption SleepAllowed false; the poll followed; OFF_H at speed 1), ON (SleepAllowed back
                  to the value read; ON_H), C (the clock, and SleepAllowed if ON did not run), R.
  x465  night     (x46-sleep) S, H (NIGHT_RING), PRE (PRE_H awake), NIGHT (player.sleep.hold, acute.winSleptH polled to
                  NIGHT_H booked, the game's own fast-forward at its default FastForwardMultiplier), POST (POST_H awake),
                  C, R.
  x466  refusal   (x46-mod)   S, H (x453's ring), F (two Broccoli), SEED (true multiplier SLOW_MULT; record.set the
                  stomach's calories then water to SEED_G, Overfull 4; the food timer polled above 3200), X (the reads;
                  eat.action Broccoli; REFUSE_WAIT_S; the reads again; action.cancel; then 0.2 L of Water drunk), C, R.
  x467  day       (x46-mod)   x452b's three-meal day (x45g_lib's x452 phases S, H, W, F, X), sleep off, on the final
                  curve, its cadence bands the HEAD replay of the schedule from the first sight; C, R.

THE GRADES (pure; each has a failing case in testing/tests/test_x46_lib.py; a grade on no valid sample is unmeasured,
never as_predicted; every tolerance is named below, before any run):
  every ringed session  H1, RING, Z (x45g_lib's).
  x461a/b  REPLAY_<field>  the HEAD replay of the run's own ring (start.json, the eats, the sips as logged, the ring's
                  cold multiplier fed: tools/replay_live.replay_live, ring_cold auto) within REPLAY_TOL on every row.
           COLD_FED  the ring rows carry the cold field and the replay backend fed it (#3947's precondition).
           (reading) checks.cold_ablation: THIRST's miss with the cold not fed.
  x461a    OF_MIN_3, OF_MIN_4  the game minutes at Overfull 3 or more and at 4 after the plate's first landing within
                  OF_TOL_MIN of the prerun; OF_PEAK the peak stomach mass within OF_PEAK_TOL_G of it.
  x461b    W_PEAK, M_PEAK  the liquid lane's peak after each drink's first sip row within LIQ_PEAK_TOL_G of the prerun;
           W_HALF the water's liquid half-time within LIQ_HALF_TOL_M of it.
  x462     T_ON (hideOn 1: ok, vanilla true, hungerLineDrawn false, tagLeft false), T_OFF (hideOn 0: ok, vanilla true,
           hungerLineDrawn true, tagLeft false), T_NATIVE (nativeTag false on the first call), T_RESTORED (both replies
           restored, the option accessor reading the same before and after).
  x463a    AWAY_STILL  the record read away and again before the rejoin, every FREEZE path equal.
           FREEZE      on the first return ring row whose stamps moved, every value path equal to the away read
                       (FREEZE_TOL) and the gap at least AWAY_MIN_H (else unmeasured).
           STAMPS      on that row every stamp moved by one gap (STAMP_TOL_H), the gap the resume counted.
           WRITTEN     that row's HUNGER, THIRST and FATIGUE equal to one of the last two online rows before the quit
                       (STAT_TOL): the disconnect's save, no write at the return minute.
  x463b    KILL_OWN    the PID killed is the one the session's pzt server recorded, and the process exited.
           ROLLBACK    the world age after the restart, and the record's lastSeen at the sight, under the store
                       FILE's latest stamp (the slot the load rule reads, after its write past LATE_H) (precondition:
                       else RESTORED, ON_CLOCK and CONSISTENT are unmeasured).
           RESTORED    NutritionRevamp.server.backup.stats.restored 1 and aheadKept 0 (the copy is the world save's
                       or a later snapshot's, so the restored record resumes forward or back: a reading).
           ON_CLOCK    the restored record's latest stamp within ON_CLOCK_GM of the world age at the sight.
           CONSISTENT  graded on a RESTORED as predicted and a record read that answered: the restored record holds the
                       banana's eat (monotony entry) iff the inventory lost the banana.
           COPY_SAVED  the admin blob of players.db read after the kill holds the "NutritionRevamp" key (the copy saved
                       with the character); its length beside the fixture's is a reading.
  x464     TRACK       before the first sleep, bodyHour within TRACK_TOL_H of the world hour on every row (seeded there).
           NAP_KEEP    the nap's bout booked NAP_MIN..4 h; after its close bodyHour still within TRACK_TOL_H of the
                       world hour.
           FULL_RESET  the full sleep's bout booked at least 4 h; after its close bodyHour within RESET_TOL_H of 07:00
                       plus the game hours since the last asleep row, that reset hour more than DISCRIM_H off the world
                       hour (else unmeasured: a reset and a clock on the world hour read alike).
           POLL_OFF, POLL_ON  the ring's polled sleep setting follows the RCON change within POLL_GM game minutes of
                       the age read before the change (the live poll a reading).
           NO_RHYTHM   sleep off: bodyOn false, the writer's hunger factor 1, acute.circ 0 and bodyHour held on every
                       ring row from the first row after the flip.
           RESEED      sleep on again: the first row with bodyOn true reads bodyHour within TRACK_TOL_H of the world hour.
  x465     FF_DEFAULT  the server's FastForwardMultiplier the game's default (precondition).
           NO_LOSS     acute.winSleptH's gain over the night within NO_LOSS_TOL_H of the game hours of the steps the ring
                       reads asleep (x30's rule: row k+1's sleptH > 0 makes step k asleep).
           CAUGHT_UP   after the night the record's lastSeen within CATCH_TOL_GM of the world age (nothing carried left).
           (reading)   the stall counters (P.stalls, P.substeps) over the night; the asleep share of the hold's span.
  x466     REACHED     Overfull 4 and the food timer above 3200 at the attempt (precondition).
           REFUSED     the guard's refused and held counters rose by 1 and the intake landed nothing in REFUSE_WAIT_S.
           (ITEM_INTACT, RECORD_KEPT and QUEUE_CLEARED are graded only when the guard's counters rose: the server saw
           the eat; the client queue is read empty before the eat)
           ITEM_INTACT the Broccoli's server copy keeps its id and hunger change and the count is unchanged.
           RECORD_KEPT the meal pool not raised, the stomach not heavier by REFUSE_MASS_TOL, the eats count unchanged.
           QUEUE_CLEARED action.cancel finds the client queue empty (before 0).
           DRINK_LANDS the water's sips rose and at least DRINK_MIN_L was drunk.
  x467     x452's (x45g_lib.Sess.grade_x452) at this lib's bands, plus NO_RHYTHM_DAY: every ring row bodyOn not true and
           the hunger factor 1.

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run, this file is never edited (CLAUDE.md s5).
"""
import glob
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                                   # testing/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import xlib as X                                                              # noqa: E402
import x45g_lib as G                                                          # noqa: E402

REPO = X.REPO
SRV = X.SRV
CLI = G.CLI
USER = G.USER
NR = G.NR
LIB_FILE = "x46_lib.py"
MOD_DIR = G.MOD_DIR
STAGE_OUT = "release/plan16-x46"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_FROM = "648b4a83"                 # mod/'s last commit (Plan 16 Task 5 fix 1)
PRERUN_FILE = "testing/experiments/x46_prerun.json"
FIXTURE_PLAYERS_DB = "testing/fixtures/default/cache/server/Saves/Multiplayer/pzt/players.db"
FIXTURE_STORE_DIR = "testing/fixtures/default/cache/server/Lua/NutritionRevamp"   # the mod's store slots (review L7)
PLAYERS_DB_REL = ("server", "Saves", "Multiplayer", "pzt", "players.db")
MIN_FREE_GB = 12.0
MOD_DAY_LENGTH = 1
HOUR_OFFSET = G.HOUR_OFFSET

PROFILES = {"x46-mod": {"sleep": False, "tkx": False},
            "x46-gut": {"sleep": False, "tkx": True},
            "x46-sleep": {"sleep": True, "tkx": False}}
SESSIONS = {
    "x461a": {"driver": "x461a_plate.py", "artifact": "plate.json", "profile": "x46-mod"},
    "x461b": {"driver": "x461b_drinks.py", "artifact": "drinks.json", "profile": "x46-gut"},
    "x462": {"driver": "x462_tooltip.py", "artifact": "tooltip.json", "profile": "x46-mod"},
    "x463a": {"driver": "x463a_freeze.py", "artifact": "freeze.json", "profile": "x46-sleep"},
    "x463b": {"driver": "x463b_hardkill.py", "artifact": "hardkill.json", "profile": "x46-mod"},
    "x464": {"driver": "x464_bodyclock.py", "artifact": "bodyclock.json", "profile": "x46-sleep"},
    "x465": {"driver": "x465_night.py", "artifact": "night.json", "profile": "x46-sleep"},
    "x466": {"driver": "x466_refusal.py", "artifact": "refusal.json", "profile": "x46-mod"},
    "x467": {"driver": "x467_day.py", "artifact": "day.json", "profile": "x46-mod"},
}
NO_RING = ("x462", "x463b")

# ---- the first sight (x452b-20261017-153935 day.json: checks.H.h1_record.values.firstSeen 3.052661895751953 and
# checks.S.stats_all.stats Hunger 0.025309816002845764, Thirst 0, Fatigue 0; the first written HUNGER is within the
# seed plate's dead zone of the vanilla HUNGER the record found, so the written value stands in for it)
FIRST_SIGHT = {"age": 3.05, "stats": {"HUNGER": 0.0253, "THIRST": 0.0, "FATIGUE": 0.0}}

# ---- the foods (x45g_lib.FOODS, the item pass's macros) and the study food (TKX_StudyFoods, replay_live.study_foods)
BOLOGNESE, BANANA, BROCCOLI = G.BOLOGNESE, G.BANANA, G.BROCCOLI
MILKSOLID = "TKX.MilkSolid"
PLATE = (BOLOGNESE, BANANA, BROCCOLI, BROCCOLI)           # 540.00 + 105.11 + 2 x 11.02 = 667.15 kcal
# the plate's landings after its first eat's start (game minutes at speed 1, DayLength 1): the can 9 and the banana 16
# (x45g_lib.EAT_CAN_GM, EAT_BAN_GM, read off x446), each broccoli about 5 more (its HungerChange -9 against the
# banana's -16: a shorter eat; an estimate, the replay of the run's own ring is the exact check); the water's drink
# starts a minute after the last landing and lands sip by sip over its span (replay_live.spread_drinks, DayLength 1)
PLATE_LAND_GM = (9, 16, 21, 26)
WATER_AT_GM = 27
WATER, COWMILK, COFFEE = "Water", "CowMilk", "Coffee"
BOTTLE, CANTEEN, CARTON, SPORTS = "Base.WaterBottle", "Base.Canteen", "Base.Milk", "Base.Sportsbottle"
DRINK_L = 0.5
MILK_MAX_TIME = 232                      # ISDrinkFluidAction.new: 232 x eatingLoop; 0.5 L of CowMilk reads loop 1
                                         # (an estimate for the prerun's spread; the replay of the run's own ring
                                         # lands the milk as its sips were logged)
COFFEE_L = 0.25

# ---- the ring paths
EATS_G, LANDED_G, SIPS_G, WRITES_G = G.EATS_G, G.LANDED_G, G.SIPS_G, G.WRITES_G
CIRC_G = "_G.NutritionRevamp.server.writer.input.circ"            # the writer's hunger circadian factor (one player)
SLEEPON_G = "_G.NutritionRevamp.server.options.sleepOn"
STALLS_G = "_G.NutritionRevamp.server.players.stalls"
SUBSTEPS_G = "_G.NutritionRevamp.server.players.substeps"
RUNS_G = "_G.NutritionRevamp.server.minute.stats.runs"
GUT_RING = G.STOMACH_PATHS + ("stomachFill", "satiety.M", "satiety.hModel", "body.energyState", "body.met",
                              "body.coldMult", "kineticsAge", "fluids.water", "fluids.na", "fluids.dehydPct",
                              "fluids.thirstTarget", "fluids.autoDrop", "drain.dehydrated", EATS_G, LANDED_G, SIPS_G,
                              WRITES_G)
FREEZE_STAMPS = ("lastSeen", "kineticsAge", "satiety.t", "nutrients.lastAgeH", "body.lastAgeH", "body.dayStartH",
                 "acute.winStartH", "drain.fedAgeH")
FREEZE_VALUES = ("stomach.buffer.water", "stomach.buffer.calories", "stomach.liquid", "satiety.M", "satiety.L",
                 "body.fm", "body.lm", "body.energyState", "body.inDay", "body.eeDay", "body.dayIndex",
                 "fluids.water", "fluids.na", "fluids.dehydPct", "acute.caf", "acute.gutCaf", "acute.cafTol",
                 "acute.debtH", "acute.S", "acute.awakeH", "acute.bodyHour", "acute.winSleptH")
FREEZE_PATHS = FREEZE_STAMPS + FREEZE_VALUES
WRITTEN = ("HUNGER", "THIRST", "FATIGUE")
CLOCK_RING = ("acute.bodyHour", "acute.bodyOn", "acute.circ", "acute.sleptH", "acute.boutH", "acute.gapH",
              "acute.winSleptH", "acute.S", "acute.awakeH", "kineticsAge", "lastSeen", "satiety.hModel", CIRC_G,
              SLEEPON_G, STALLS_G, SUBSTEPS_G)
NIGHT_RING = ("acute.sleptH", "acute.boutH", "acute.gapH", "acute.winSleptH", "acute.winStartH", "acute.debtH",
              "acute.S", "acute.bodyHour", "kineticsAge", "lastSeen", "satiety.M", "body.energyState",
              "fluids.water", STALLS_G, SUBSTEPS_G, RUNS_G)
DAY_RING = tuple(G.RING["x452"]) + ("acute.bodyOn", CIRC_G)
RING46 = {"x461a": GUT_RING, "x461b": GUT_RING, "x463a": FREEZE_PATHS, "x464": CLOCK_RING, "x465": NIGHT_RING,
          "x466": tuple(G.RING["x453"]), "x467": DAY_RING}
GUARD_PATHS = tuple(f"NutritionRevamp.server.eatGuard.stats.{k}" for k in ("checks", "refused", "held", "stopped",
                                                                            "failures", "passthrough"))
STORE_STATS = ("NutritionRevamp.server.store.stats.loads", "NutritionRevamp.server.store.stats.created",
               "NutritionRevamp.server.store.stats.resumes", "NutritionRevamp.server.store.stats.resumedH",
               "NutritionRevamp.server.store.stats.rewound", "NutritionRevamp.server.store.stats.failures")
BACKUP_STATS = tuple(f"NutritionRevamp.server.backup.stats.{k}" for k in ("writes", "bytes", "reads", "restored",
                                                                          "aheadKept", "rejected.absent",
                                                                          "rejected.garbled", "rejected.sum"))
LASTWRITE = "NutritionRevamp.server.store.file.lastWrite.admin"
FILE_LAST = "NutritionRevamp.server.store.file.last.admin"    # the slot file's text as last written (W's read)
BANANA_ENTRY = f"monotony.t.[{BANANA}].last"

# ---- the tolerances and sizes (named before any run)
PAIR_SLACK = 0.8                         # Plan 15's live review F3 (x45h_lib, x45i_lib)
REPLAY_TOL = {"HUNGER": ("abs", 0.002), "THIRST": ("abs", 0.002), "body.energyState": ("abs", 0.005),
              "stomachFill": ("abs", 0.002), "stomach.liquid": ("abs", 2.0)}   # x446's three and x363's two fills
EMPTY_G = 30.0
EMPTY_CAP_H = 8.0
PLATE_WATCH_H = 0.75
TAIL_H = 1.0
OF_TOL_MIN = 3.0
OF_PEAK_TOL_G = 40.0
WATCH_M = 45.0
H_REQ = 0.25
REQ_CAP_H = 12.0
LIQ_PEAK_TOL_G = 30.0
LIQ_HALF_TOL_M = 3.0
TOOLTIP_FOOD = BANANA
AWAY_MULT = 30.0                         # x432's: 72 game hours in about 100 wall s with nobody on
AWAY_MIN_H = 72.0
AWAY_POLL_S = 2.0
AWAY_CAP_S = 240.0
DEPART_CAP_S = 30.0
RESUME_CAP_S = 60.0
PRE_H = 0.3
RETURN_H = 0.1
FREEZE_TOL = 1e-9
STAMP_TOL_H = 1e-6
STAT_TOL = 1e-6
ADV_H = 1.0
LATE_H = 2.0                             # game hours at speed 5 after the eat: the store's stamps run past the save by
                                         # more than the restart-to-sight span (a rejoin about 40 wall s, about 1.1 game
                                         # h at speed 1 with PauseEmpty false), so the record is still ahead at the sight
SAVE_SETTLE_S = 8.0
SAVE_CAP_S = 70.0                        # a slot write comes at most once a real minute (S.SAVE_GAP_MS 60000)
LATE_WRITE_CAP_S = 70.0                  # review H1: the file's write after LATE_H, the one the load rule reads
ON_CLOCK_GM = 2.0                        # review H3: the restored record's latest stamp on the world clock
KILL_WAIT_S = 30.0
UP_CAP_S = 60.0
TRACK_H = 0.25
TRACK_TOL_H = 0.05
RESET_TOL_H = 0.1
DISCRIM_H = 1.0
NAP_MIN_H = 1.0                          # K.acute.NAP_MIN_H
MAIN_SLEEP_H = 4.0                       # K.circadian.MAIN_SLEEP_H
WAKE_H = 7.0                             # K.circadian.WAKE_H
NAP_H = 1.5
FULL_H = 5.0
AWAKE_H = 0.3                            # past K.acute.BOUT_GAP_H (10 game minutes), so the bout closes
SLEEP_CAP_S = 90.0
SLEEP_POLL_S = 0.25
POLL_S_FAST = 0.25
HOLD_S = 600
WAKE_SETTLE_S = 3.0
POLL_GM = 2.0
POLL_CAP_S = 15.0
OFF_H = 0.4
ON_H = 0.2
NIGHT_H = 7.0
NIGHT_CAP_S = 150.0
POST_H = 0.3
NO_LOSS_TOL_H = 0.05
CATCH_TOL_GM = 2.0
FF_DEFAULT = 40.0                        # ServerOptions FastForwardMultiplier's default (the fixture's pzt.ini, 40.0)
SLOW_MULT = 0.05                         # x453b's: a game minute 12.5 wall s
SEED_KCAL = G.SEED_KCAL
SEED_G = 1150.0                          # past CAPACITY_HARD_G 1100: Overfull 4
SEED_MIN_G = 1110.0
TIMER_POLL_S = 0.5
TIMER_CAP_S = 60.0
REFUSE_WAIT_S = 8.0
REFUSE_MASS_TOL = 10.0
DRINK_466_L = 0.2
DRINK_MIN_L = 0.15
SETTLE_POLLS = G.SETTLE_POLLS
DRINK_CAP_S = G.DRINK_CAP_S
CONSTANTS = {k: v for k, v in dict(globals()).items() if re.match(r"^[A-Z][A-Z0-9_]+$", k)
             and isinstance(v, (int, float, str, bool, tuple)) and k not in ("REPO", "HERE")}

# ---- the harness markers (the repository files and every deployed copy)
HARNESS_FILES = dict(G.HARNESS_FILES)
HARNESS_MARKERS = {k: tuple(v) for k, v in G.HARNESS_MARKERS.items()}
HARNESS_MARKERS["PZTestKit_Server.lua"] += tuple(f'TK.register("{c}", function(' for c in (
    "player.sleep", "player.sleep.hold", "autodrink.set"))
HARNESS_MARKERS["PZTestKit_Client.lua"] += tuple(f'TK.register("{c}", function(' for c in ("tooltip.measure",
                                                                                          "quit"))
HARNESS_MARKERS["PZTestKit_Core.lua"] += tuple(f'TK.register("{c}", function(' for c in ("witness.moddata",))
LOG_RX = G.LOG_RX
MOD_ERR_RX = G.MOD_ERR_RX
RESTORE_RX = re.compile(r"restored from the backup on the character|moved back .* game hours onto a world clock")


# ================================================================ small readers (pure)
num = G.num
g = G.g
vals = G.vals
ring_age = G.ring_age


def wrapdiff(a, b):
    """a - b on the 24-hour circle, in [-12, 12)."""
    return ((a - b + 12.0) % 24.0) - 12.0


def world_hour(age):
    return (age + HOUR_OFFSET) % 24.0


def load_prerun(path=None):
    p = path or os.path.join(REPO, PRERUN_FILE)
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


PRERUN = load_prerun()


def online(rows):
    return [r for r in rows if r.get("on") is not False and ring_age(r) is not None]


def mass_of(r):
    return G.stomach_mass(r)


def overfull_minutes(rows, a0, a1=None):
    """Game minutes at Overfull 3 or more and at 4, and the peak mass, over ring rows after age a0 (to a1): each row
    counts its dtM (the step it closed)."""
    m3 = m4 = 0.0
    peak, n = None, 0
    for r in rows:
        a = ring_age(r)
        if a is None or a <= a0 or (a1 is not None and a > a1):
            continue
        m = mass_of(r)
        if m is None:
            continue
        n += 1
        lv = G.overfull_level(m)
        dt = num(r.get("dtM")) or 1.0
        if lv >= 3:
            m3 += dt
        if lv >= 4:
            m4 += dt
        peak = m if peak is None else max(peak, m)
    return {"m3": m3, "m4": m4, "peak": peak, "n": n}


def first_rise_age(rows, key, after=None):
    """The age of the first ring row whose `key` counter rose over the row before (after age `after`)."""
    prev = None
    for r in rows:
        a = ring_age(r)
        if prev is not None and a is not None and (after is None or a > after):
            x, y = num(prev.get(key)), num(r.get(key))
            if x is not None and y is not None and y > x:
                return a
        prev = r
    return None


def liquid_course(rows, a0, a1):
    """The liquid lane from age a0 to a1: its peak, the peak's age and the game minutes from the peak until it first
    reads half the peak (None when it never does inside the window)."""
    w = [(ring_age(r), num(r.get("stomach.liquid"))) for r in rows
         if ring_age(r) is not None and a0 <= ring_age(r) <= a1 and num(r.get("stomach.liquid")) is not None]
    if not w:
        return {"peak": None, "peak_age": None, "half_m": None}
    pa, pk = max(w, key=lambda t: t[1])
    half = next((a for a, v in w if a > pa and v <= pk / 2.0), None)
    return {"peak": pk, "peak_age": pa, "half_m": None if half is None else (half - pa) * 60.0}


# ================================================================ the grades (pure)
def grade_band(obs, pred, tol, name):
    """A reading against its prerun band: unmeasured when either is missing."""
    o = {"value": obs, "predicted": pred, "tol": tol}
    if obs is None or pred is None:
        o["why"] = f"no {name} reading or no prediction"
        return "unmeasured", o
    o["miss"] = abs(obs - pred)
    return ("as_predicted" if o["miss"] <= tol else "falsified"), o


def grade_cold_fed(rows, backend_cold):
    n = sum(1 for r in rows if isinstance(r.get("cold"), (int, float)) and not isinstance(r.get("cold"), bool))
    o = {"rows_with_cold": n, "rows": len(rows), "backend_ring_cold": backend_cold}
    if not rows:
        return "unmeasured", dict(o, why="no ring rows")
    return ("as_predicted" if n > 0 and backend_cold is True else "falsified"), o


def grade_tooltip(reply, hide_on):
    """One tooltip.measure arm: ok, the requested arm, vanilla's line present to hide, the hunger line drawn iff the
    hide is off, no leaked tag."""
    r = reply if isinstance(reply, dict) else {}
    o = {k: r.get(k) for k in ("ok", "hideOn", "vanilla", "hungerLineDrawn", "tagLeft", "height", "heightBase",
                               "heightOn", "heightOff", "lineDrop", "bandShown", "nativeTag", "error", "reason")}
    if r.get("ok") is not True or r.get("vanilla") is not True:
        o["why"] = "the measure failed or the food shows no vanilla hunger line"
        return ("falsified" if r.get("tagLeft") is True else "unmeasured"), o
    ok = (r.get("hideOn") is bool(hide_on) and r.get("hungerLineDrawn") is (not hide_on)
          and r.get("tagLeft") is not True)
    return ("as_predicted" if ok else "falsified"), o


def grade_native(first):
    r = first if isinstance(first, dict) else {}
    if "nativeTag" not in r:
        return "unmeasured", {"why": "no first reply"}
    return ("as_predicted" if r.get("nativeTag") is False else "falsified"), {"nativeTag": r.get("nativeTag")}


def grade_restored(on, off, opt_before, opt_after):
    o = {"restored_on": g(on, "restored"), "restored_off": g(off, "restored"), "option_before": opt_before,
         "option_after": opt_after}
    if opt_before is None or opt_after is None:
        return "unmeasured", dict(o, why="the option read failed")
    ok = g(on, "restored") is True and g(off, "restored") is True and opt_before == opt_after
    return ("as_predicted" if ok else "falsified"), o


def value_diff(a, b, paths, tol):
    """The paths whose values differ between two reads (a missing value on either side differs)."""
    out = {}
    for p in paths:
        x, y = (a or {}).get(p), (b or {}).get(p)
        if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, (int, float)) or \
                not isinstance(y, (int, float)):
            if x != y or x is None:
                out[p] = [x, y]
        elif abs(x - y) > tol * max(1.0, abs(x)):
            out[p] = [x, y]
    return out


def grade_away_still(away0, away1):
    if not away0 or not away1:
        return "unmeasured", {"why": "an away read is missing"}
    d = value_diff(away0, away1, FREEZE_PATHS, 0.0)
    return ("as_predicted" if not d else "falsified"), {"diff": d, "paths": len(FREEZE_PATHS)}


def resumed_row(rows, away):
    """The first online return row whose lastSeen moved past the away read's by more than an hour (the resume)."""
    ls0 = num((away or {}).get("lastSeen"))
    if ls0 is None:
        return None
    for r in rows:
        if r.get("on") is False:
            continue
        ls = num(r.get("lastSeen"))
        if ls is not None and ls > ls0 + 1.0:
            return r
    return None


def grade_freeze(rows, away):
    r = resumed_row(rows, away)
    if r is None:
        return "unmeasured", {"why": "no return row with moved stamps"}
    gap = num(r.get("lastSeen")) - num(away.get("lastSeen"))
    o = {"row_s": r.get("s"), "gap_h": gap}
    if gap < AWAY_MIN_H:
        return "unmeasured", dict(o, why=f"the gap {gap:.3f} h is under {AWAY_MIN_H} h")
    d = value_diff(away, r, FREEZE_VALUES, FREEZE_TOL)
    o["diff"] = d
    return ("as_predicted" if not d else "falsified"), o


def grade_stamps(rows, away, resumed_h=None):
    r = resumed_row(rows, away)
    if r is None:
        return "unmeasured", {"why": "no return row with moved stamps"}
    gap = num(r.get("lastSeen")) - num(away.get("lastSeen"))
    moved = {}
    for p in FREEZE_STAMPS:
        x, y = num(away.get(p)), num(r.get(p))
        moved[p] = None if x is None or y is None else y - x
    bad = {p: v for p, v in moved.items() if v is None or abs(v - gap) > STAMP_TOL_H}
    o = {"gap_h": gap, "moved": moved, "bad": bad, "resumedH": resumed_h}
    if resumed_h is not None and abs(resumed_h - gap) > 1e-3:
        bad["resumedH"] = resumed_h
    return ("as_predicted" if not bad else "falsified"), o


def grade_written(rows_pre, rows_ret, away):
    """The return row's written stats equal one of the last two online rows before the quit."""
    r = resumed_row(rows_ret, away)
    last = [x for x in rows_pre if x.get("on") is not False][-2:]
    if r is None or not last:
        return "unmeasured", {"why": "no resumed row or no online row before the quit"}
    o = {"row_s": r.get("s"), "ret": {k: r.get(k) for k in WRITTEN}, "pre": [{k: x.get(k) for k in WRITTEN}
                                                                              for x in last]}
    ok = all(any(num(x.get(k)) is not None and num(r.get(k)) is not None and abs(num(x.get(k)) - num(r.get(k)))
                 <= STAT_TOL for x in last) for k in WRITTEN)
    return ("as_predicted" if ok else "falsified"), o


def grade_kill_own(kill):
    """The PID killed is the one the session's own Server object recorded, alive before the kill, the taskkill
    answered 0 and the process exited (review L1)."""
    k = kill or {}
    o = {k2: k.get(k2) for k2 in ("pid_recorded", "pid_killed", "alive_before", "taskkill_rc", "exited", "rc",
                                  "client_pid")}
    if k.get("pid_recorded") is None:
        return "unmeasured", dict(o, why="no PID recorded (the kill was skipped)")
    ok = (k.get("pid_killed") == k.get("pid_recorded") and k.get("alive_before") is True
          and k.get("taskkill_rc") == 0 and k.get("exited") is True)
    return ("as_predicted" if ok else "falsified"), o


def grade_rollback(up, eat):
    """The world the restart loaded behind the store FILE's latest stamp (the slot the load rule reads, review H1), and
    still behind it at the sight (the record's first lastSeen, the world age the load met): both, or the load rule's
    ahead case was not set up. The in-memory record's latest is a reading beside it."""
    a_up, latest, sight = num(g(up, "age_restart")), num(g(eat, "file_latest")), num(g(up, "sight_lastSeen"))
    o = {"age_after_restart": a_up, "file_latest_before_kill": latest, "sight_lastSeen": sight,
         "memory_latest_before_kill": num(g(eat, "latest"))}
    if a_up is None or latest is None or sight is None:
        return "unmeasured", dict(o, why="an age is missing (the file's last text unread, or no sight)")
    return ("as_predicted" if a_up < latest and sight < latest else "falsified"), o


def grade_restored_copy(up, rolled):
    """The copy restored once and no ahead store kept (review H3): the restored record then resumes FORWARD when its
    copy is the world save's (resumes) or back when a later snapshot's (rewound); both are readings."""
    o = {"restored": num(g(up, "backup", BACKUP_STATS[3])), "aheadKept": num(g(up, "backup", BACKUP_STATS[4])),
         "rewound": num(g(up, "store", STORE_STATS[4])), "resumes": num(g(up, "store", STORE_STATS[2])),
         "resumedH": num(g(up, "store", STORE_STATS[3])), "rolled_back": rolled}
    if not rolled:
        return "unmeasured", dict(o, why="the world was not behind the store at the sight")
    if o["restored"] is None or o["aheadKept"] is None:
        return "unmeasured", dict(o, why="the counters did not read")
    o["direction"] = "back" if (o["rewound"] or 0) >= 1 else ("forward" if (o["resumes"] or 0) >= 1 else "none")
    ok = o["restored"] == 1 and o["aheadKept"] == 0
    return ("as_predicted" if ok else "falsified"), o


def grade_on_clock(up):
    """The restored record's latest stamp (over FREEZE_STAMPS, at the first record read) within ON_CLOCK_GM of the
    world age read in the same poll iteration: the resume put it on the world clock, in either direction (review H3)."""
    latest, a = num(g(up, "record", "latest")), num(g(up, "age"))
    o = {"latest": latest, "age": a}
    if latest is None or a is None:
        return "unmeasured", dict(o, why="no record or no age at the sight")
    o["off_gm"] = (latest - a) * 60.0
    return ("as_predicted" if abs(o["off_gm"]) <= ON_CLOCK_GM else "falsified"), o


def grade_consistent(up, eat, restored):
    """The restored record holds the banana's eat iff the inventory lost the banana; graded only on a restore that
    read as predicted (review H3.3) and on a record read that answered (review L4)."""
    has = g(up, "entry") is not None
    n0, n1 = num(g(eat, "count_before")), num(g(up, "count"))
    o = {"entry_after": g(up, "entry"), "count_before_eat": n0, "count_after": n1, "restored": restored}
    if not restored:
        return "unmeasured", dict(o, why="no restore read as predicted")
    if num(g(up, "record", "values", "lastSeen")) is None:
        return "unmeasured", dict(o, why="the record read after the restart did not answer")
    if n0 is None or n1 is None:
        return "unmeasured", dict(o, why="a banana count did not read")
    lost = n1 < n0
    o["eat_in_record"], o["banana_lost"] = has, lost
    return ("as_predicted" if has == lost else "falsified"), o


def grade_copy_saved(db):
    d = db or {}
    if d.get("length") is None:
        return "unmeasured", {"why": "players.db unread", "error": d.get("error")}
    return ("as_predicted" if d.get("has_key") is True else "falsified"), dict(d)


def grade_track(rows, a0, a1, tol=TRACK_TOL_H):
    w = [r for r in online(rows) if a0 < ring_age(r) <= a1 and r.get("acute.bodyOn") is True
         and num(r.get("acute.bodyHour")) is not None]
    if not w:
        return "unmeasured", {"why": "no ring row with the clock on in the window"}
    d = [abs(wrapdiff(num(r["acute.bodyHour"]), world_hour(ring_age(r)))) for r in w]
    return ("as_predicted" if max(d) <= tol else "falsified"), {"n": len(w), "max_off_h": max(d), "tol": tol}


def bout_close(rows, a0, a1):
    """The sleep in (a0, a1]: the largest boutH, the last row with sleptH > 0 and the first later row whose boutH reads
    0 (the bout's close)."""
    w = [r for r in online(rows) if a0 < ring_age(r) <= a1]
    bout = max((num(r.get("acute.boutH")) or 0.0 for r in w), default=0.0)
    last = None
    for r in w:
        if (num(r.get("acute.sleptH")) or 0.0) > 0:
            last = r
    close = None
    if last is not None:
        close = next((r for r in w if ring_age(r) > ring_age(last) and (num(r.get("acute.boutH")) or 0.0) == 0.0), None)
    return {"bout_h": bout, "last_asleep": last, "close": close}


def grade_nap_keep(rows, a0, a1):
    b = bout_close(rows, a0, a1)
    o = {"bout_h": b["bout_h"], "close_s": g(b, "close", "s")}
    if b["close"] is None or not (NAP_MIN_H <= b["bout_h"] < MAIN_SLEEP_H):
        return "unmeasured", dict(o, why=f"no closed bout of {NAP_MIN_H} to {MAIN_SLEEP_H} booked hours")
    after = [r for r in online(rows) if ring_age(b["close"]) <= ring_age(r) <= a1 and r.get("acute.bodyOn") is True]
    d = [abs(wrapdiff(num(r.get("acute.bodyHour")), world_hour(ring_age(r)))) for r in after
         if num(r.get("acute.bodyHour")) is not None]
    if not d:
        return "unmeasured", dict(o, why="no row after the close")
    o.update({"n": len(d), "max_off_h": max(d)})
    return ("as_predicted" if max(d) <= TRACK_TOL_H else "falsified"), o


def grade_full_reset(rows, a0, a1):
    b = bout_close(rows, a0, a1)
    o = {"bout_h": b["bout_h"], "close_s": g(b, "close", "s")}
    if b["close"] is None or b["bout_h"] < MAIN_SLEEP_H:
        return "unmeasured", dict(o, why=f"no closed bout of {MAIN_SLEEP_H} booked hours or more")
    wake = ring_age(b["last_asleep"])
    after = [r for r in online(rows) if ring_age(b["close"]) <= ring_age(r) <= a1
             and num(r.get("acute.bodyHour")) is not None]
    if not after:
        return "unmeasured", dict(o, why="no row after the close")
    off = [abs(wrapdiff(num(r["acute.bodyHour"]), WAKE_H + (ring_age(r) - wake))) for r in after]
    disc = [abs(wrapdiff(WAKE_H + (ring_age(r) - wake), world_hour(ring_age(r)))) for r in after]   # the reset's
    # hour against the world's: a reset and a clock left on the world hour are told apart only when these differ
    o.update({"wake_age": wake, "n": len(after), "max_off_h": max(off), "min_world_off_h": min(disc),
              "body_at_close": num(b["close"].get("acute.bodyHour"))})
    if min(disc) <= DISCRIM_H:
        return "unmeasured", dict(o, why=f"07:00 within {DISCRIM_H} h of the world hour: a reset is not told apart")
    return ("as_predicted" if max(off) <= RESET_TOL_H else "falsified"), o


def ring_flip(rows, change_age, want):
    """The age of the first online ring row after change_age whose polled sleep setting reads `want` (review M1: the
    ring's own minute row, not a bus round trip)."""
    if change_age is None:
        return None
    return next((ring_age(r) for r in online(rows) if ring_age(r) > change_age and r.get(SLEEPON_G) is want), None)


def grade_poll(change_age, flip_age):
    o = {"change_age": change_age, "flip_age": flip_age}
    if change_age is None:
        return "unmeasured", dict(o, why="the change did not read back an age")
    if flip_age is None:
        return "falsified", dict(o, why="the poll never followed")
    o["gm"] = (flip_age - change_age) * 60.0
    return ("as_predicted" if o["gm"] <= POLL_GM else "falsified"), o


def grade_no_rhythm(rows, a0, a1):
    """Every online ring row in (a0, a1]: bodyOn false, the hunger factor 1, acute.circ 0, bodyHour held."""
    w = [r for r in online(rows) if a0 < ring_age(r) <= a1]
    if not w:
        return "unmeasured", {"why": "no ring row in the window"}
    held = num(w[0].get("acute.bodyHour"))
    bad = []
    for r in w:
        bh = num(r.get("acute.bodyHour"))
        if r.get("acute.bodyOn") is True or num(r.get(CIRC_G)) != 1 or num(r.get("acute.circ")) != 0 or \
                (held is not None and (bh is None or abs(bh - held) > 1e-9)):
            bad.append({"s": r.get("s"), "bodyOn": r.get("acute.bodyOn"), "circ_h": r.get(CIRC_G),
                        "circ_f": r.get("acute.circ"), "bodyHour": bh})
    return ("as_predicted" if not bad else "falsified"), {"n": len(w), "bad": bad[:10], "held": held}


def grade_reseed(rows, a0):
    r = next((x for x in online(rows) if ring_age(x) > a0 and x.get("acute.bodyOn") is True), None)
    if r is None or num(r.get("acute.bodyHour")) is None:
        return "unmeasured", {"why": "no row with the clock back on"}
    d = abs(wrapdiff(num(r["acute.bodyHour"]), world_hour(ring_age(r))))
    return ("as_predicted" if d <= TRACK_TOL_H else "falsified"), {"s": r.get("s"), "off_h": d}


def grade_no_rhythm_day(rows):
    w = online(rows)
    if not w:
        return "unmeasured", {"why": "no ring rows"}
    bad = [r.get("s") for r in w if r.get("acute.bodyOn") is True or (num(r.get(CIRC_G)) is not None
                                                                     and num(r.get(CIRC_G)) != 1)]
    read = sum(1 for r in w if num(r.get(CIRC_G)) is not None)
    if read == 0:
        return "unmeasured", {"why": "the hunger factor never read"}
    return ("as_predicted" if not bad else "falsified"), {"n": len(w), "factor_read": read, "bad_s": bad[:10]}


def grade_ff(ini_value):
    if ini_value is None:
        return "unmeasured", {"why": "FastForwardMultiplier unread"}
    return ("as_predicted" if abs(ini_value - FF_DEFAULT) < 1e-9 else "falsified"), {"value": ini_value,
                                                                                     "default": FF_DEFAULT}


def night_booking(rows, a0, a1, lag=1):
    """Over ring rows in (a0, a1]: the gain of winSleptH (refused across a window close) and the game hours of the steps
    the ring reads asleep. A live ring lags its drain by one row (lag 1, x30: row k+1 sleptH > 0 makes step k, the dtM of
    row k, asleep); a replay's row k is drain k itself (lag 0: its own dtM)."""
    w = [r for r in online(rows) if a0 < ring_age(r) <= a1]
    if len(w) < 2:
        return None
    starts = {num(r.get("acute.winStartH")) for r in w}
    if len(starts) > 1:
        return {"window_closed": True}
    asleep = 0.0
    for prev, r in zip(w, w[1:]):
        if (num(r.get("acute.sleptH")) or 0.0) > 0:
            asleep += (num((prev if lag else r).get("dtM")) or 0.0) / 60.0
    gain = (num(w[-1].get("acute.winSleptH")) or 0.0) - (num(w[0].get("acute.winSleptH")) or 0.0)
    return {"window_closed": False, "booked_h": gain, "asleep_h": asleep, "span_h": ring_age(w[-1]) - ring_age(w[0]),
            "stalls": [num(w[0].get(STALLS_G)), num(w[-1].get(STALLS_G))],
            "substeps": [num(w[0].get(SUBSTEPS_G)), num(w[-1].get(SUBSTEPS_G))]}


def grade_no_loss(book):
    if not book or book.get("window_closed"):
        return "unmeasured", dict(book or {}, why="no night rows, or a sleep window closed inside the night")
    o = dict(book)
    if book["asleep_h"] < NAP_MIN_H:
        return "unmeasured", dict(o, why="the ring reads under an hour asleep")
    o["miss_h"] = abs(book["booked_h"] - book["asleep_h"])
    return ("as_predicted" if o["miss_h"] <= NO_LOSS_TOL_H else "falsified"), o


def grade_caught_up(read):
    a, ls = num(g(read, "age")), num(g(read, "lastSeen"))
    if a is None or ls is None:
        return "unmeasured", {"why": "no read after the night"}
    o = {"age": a, "lastSeen": ls, "lag_gm": (a - ls) * 60.0}
    return ("as_predicted" if o["lag_gm"] <= CATCH_TOL_GM else "falsified"), o


def grade_reached(at):
    lv, t = num(g(at, "level")), num(g(at, "timer"))
    o = {"level": lv, "timer": t}
    if lv is None or t is None:
        return "unmeasured", dict(o, why="no read at the attempt")
    return ("as_predicted" if lv == 4 and t > G.TIMER_REFUSE else "falsified"), o


def grade_refused(x):
    b, a = g(x, "guard_before") or {}, g(x, "guard_after") or {}
    lb, la = num(g(x, "intake_before", "landed")), num(g(x, "intake_after", "landed"))
    rb, ra = num(b.get(GUARD_PATHS[1])), num(a.get(GUARD_PATHS[1]))
    hb, ha = num(b.get(GUARD_PATHS[2])), num(a.get(GUARD_PATHS[2]))
    o = {"refused": [rb, ra], "held": [hb, ha], "landed": [lb, la]}
    if None in (lb, la, rb, ra, hb, ha):
        return "unmeasured", dict(o, why="a counter did not read")
    ok = ra - rb == 1 and ha - hb == 1 and la == lb
    return ("as_predicted" if ok else "falsified"), o


def server_saw(x):
    """The guard's refused and held counters both rose by 1 (review M2): the eat reached the server's serverStart."""
    b, a = g(x, "guard_before") or {}, g(x, "guard_after") or {}
    d = [None if num(a.get(p)) is None or num(b.get(p)) is None else num(a.get(p)) - num(b.get(p))
         for p in GUARD_PATHS[1:3]]
    return d == [1, 1]


def grade_item_intact(x):
    b, a = g(x, "item_before") or {}, g(x, "item_after") or {}
    nb, na = num(g(x, "count_before")), num(g(x, "count_after"))
    o = {"id": [b.get("id"), a.get("id")], "hungChange": [b.get("hungChange"), a.get("hungChange")], "count": [nb, na]}
    if b.get("id") is None or nb is None or na is None:
        return "unmeasured", dict(o, why="the item or the count did not read")
    ok = a.get("id") == b.get("id") and a.get("hungChange") == b.get("hungChange") and na == nb
    return ("as_predicted" if ok else "falsified"), o


def grade_record_kept(x):
    mb, ma = num(g(x, "M_before")), num(g(x, "M_after"))
    sb, sa = num(g(x, "mass_before")), num(g(x, "mass_after"))
    eb, ea = num(g(x, "intake_before", "eats")), num(g(x, "intake_after", "eats"))
    o = {"M": [mb, ma], "mass": [sb, sa], "eats": [eb, ea]}
    if None in (mb, ma, sb, sa, eb, ea):
        return "unmeasured", dict(o, why="a record value did not read")
    ok = ma <= mb + 1e-6 and sa <= sb + REFUSE_MASS_TOL and ea == eb
    return ("as_predicted" if ok else "falsified"), o


def grade_queue_cleared(cancel):
    c = cancel if isinstance(cancel, dict) else {}
    if c.get("ok") is not True or num(c.get("before")) is None:
        return "unmeasured", {"why": "action.cancel did not answer", "reply": c}
    o = {"before": c.get("before"), "current": c.get("current")}
    return ("as_predicted" if num(c["before"]) == 0 and c.get("current") is None else "falsified"), o


def grade_drink_lands(d):
    o = {"landed": g(d, "landed"), "drunk": g(d, "drunk"), "fill_ok": g(d, "fill_ok")}
    if not d or g(d, "fill_ok") is not True:
        return "unmeasured", dict(o, why="no drink or the fill gate failed")
    ok = g(d, "landed") is True and (num(g(d, "drunk")) or 0.0) >= DRINK_MIN_L
    return ("as_predicted" if ok else "falsified"), o


# ================================================================ the replay (x45g_lib's bookkeeping, this lib's foods)
def eat_event(full, s, label=None):
    if full in G.FOODS:
        return G.mod_eat_event(full, s, label)
    return {"s": s, "kind": "eat", "food": full, "label": label}


def build_events(rows, eats, drinks=()):
    """x45g_lib.build_events with this lib's foods: each landed eat at the first ring row whose eats count rose, each
    drink's litres over the rows whose sips rose inside its span."""
    saved = G.mod_eat_event
    G.mod_eat_event = lambda full, s, label=None: (saved(full, s, label) if full in G.FOODS
                                                   else eat_event(full, s, label))
    try:
        return G.build_events(rows, eats, drinks)
    finally:
        G.mod_eat_event = saved


def replay_events(rows, eats, start_age, drinks=()):
    events0, notes = build_events(rows, eats, drinks)
    drops, moves = G.autodrop_events(rows), G.ring_moving_events(rows)
    first = next((r for r in rows if num(r.get("age")) is not None
                  and (start_age is None or r["age"] > start_age + 1e-9)), None)
    held = [e for e in drops + moves if first is not None and e["s"] <= first["s"]]
    keep = [e for e in drops + moves if first is None or e["s"] > first["s"]]
    return sorted(events0 + keep, key=lambda e: e["s"]), {
        "notes": notes, "held_in_start": held, "autodrops": len([e for e in keep if e["kind"] == "autodrop"]),
        "moves": len([e for e in keep if e["kind"] == "activity"])}


def replay_grade(ring_rows, events, start, tol, paths=None, player=None, start_stats=None, ring_cold=None):
    """The HEAD replay of the ring (tools/replay_live.replay_live, sleep off; the ring's cold fed unless ring_cold is
    False) and its diff under tol. Returns (rows, diff, backend)."""
    import replay_live as RL
    rows, be = RL.replay_live(ring_rows, events, start, paths=paths, user=USER, player=player,
                              start_stats=start_stats, sleep_allowed=False, ring_cold=ring_cold)
    return rows, RL.diff(rows, ring_rows, tol), be


# ================================================================ the pre-boot checks (offline; tested)
def harness_markers_ok(repo=REPO):
    found = {}
    for fname, rel in HARNESS_FILES.items():
        try:
            with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""
        found[fname] = {mk: (mk in text) for mk in HARNESS_MARKERS[fname]}
    return found, all(all(d.values()) for d in found.values())


def profile_doc_checks(name, doc, text=""):
    """A profile's TOML against PROFILES[name]: its header naming its own file, the fixture, the one admin client, the
    sleep keys, PZTestKit, the staged copy (and TKX_StudyFoods by its path for x46-gut), Nutrition false, DayLength 1,
    no FastForwardMultiplier override, two version verify rows."""
    spec = PROFILES.get(name)
    if spec is None:
        return {"known_profile": False}
    mods = [m.get("id") for m in doc.get("mods") or []]
    paths = {m.get("id"): m.get("path") for m in doc.get("mods") or []}
    sb = doc.get("sandbox") or {}
    srv = doc.get("server") or {}
    want = ["PZTestKit", NR] + (["TKX_StudyFoods"] if spec["tkx"] else [])
    return {"known_profile": True,
            "header_names_file": text.startswith(f"# testing/profiles/{name}.toml"),
            "fixture_default": doc.get("fixture") == "default",
            "one_admin_client": doc.get("clients", ["admin"]) == ["admin"],
            "sleep_keys": srv.get("SleepAllowed") is spec["sleep"] and srv.get("SleepNeeded") is spec["sleep"],
            "no_fast_forward_override": "FastForwardMultiplier" not in srv,
            "mods_staged": mods == want and paths.get(NR) == STAGE_MOD and
            (not spec["tkx"] or paths.get("TKX_StudyFoods") == "testing/experiments/TKX_StudyFoods"),
            "nutrition_false": sb.get("Nutrition") is False,
            "day_length": sb.get("DayLength") == MOD_DAY_LENGTH,
            "verify_version": sum(1 for v in doc.get("verify") or [] if v.get("args") == f"{NR}.version") >= 2}


def fixture_fresh(repo=REPO):
    """The fixture's admin character holds no copy of a record (players.db's blob has no NutritionRevamp key), so
    every session starts on a fresh record (Task 3's rule: a fresh record for a real player empties the copy)."""
    p = os.path.join(repo, FIXTURE_PLAYERS_DB)
    r = players_db_read(p)
    r["store_dir"] = os.path.isdir(os.path.join(repo, FIXTURE_STORE_DIR))       # review L7: no store slot either
    r["fresh"] = r.get("length") is not None and r.get("has_key") is False and r["store_dir"] is False
    return r


def players_db_read(path, user=USER):
    """The admin row of a players.db read without a lock: the blob's length and whether it holds the mod's key."""
    out = {"path": path}
    try:
        uri = "file:" + path.replace("\\", "/") + "?mode=ro&immutable=1"
        c = sqlite3.connect(uri, uri=True)
        try:
            row = c.execute("select data from networkPlayers where username = ?", (user,)).fetchone()
        finally:
            c.close()
        if row is None or row[0] is None:
            out["error"] = "no row"
            return out
        out["length"] = len(row[0])
        out["has_key"] = b"NutritionRevamp" in bytes(row[0])
    except (sqlite3.Error, OSError) as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def mod_head(repo=REPO):
    try:
        p = subprocess.run(["git", "log", "-1", "--format=%h", "--", MOD_DIR], cwd=repo, capture_output=True,
                           text=True)
    except OSError:
        return None
    return p.stdout.strip() or None


def prerun_current(key, repo=REPO, compute=None, committed=None):
    """The session's committed prerun against the HEAD replay re-derived now (x46_prerun.compute): equal or not."""
    if compute is None:
        import x46_prerun as PR
        compute = PR.compute
    have = (committed if committed is not None else load_prerun(os.path.join(repo, PRERUN_FILE))).get(key)
    if key not in PRERUN_KEYS:
        return {"needed": False, "ok": True}
    try:
        now = json.loads(json.dumps(compute([key])[key], sort_keys=True, default=str))
    except Exception as e:                                         # noqa: BLE001 - recorded, refuses the boot
        return {"needed": True, "ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"needed": True, "ok": have == now, "committed": have is not None,
            "diff": None if have == now else {"committed": have, "now": now}}


PRERUN_KEYS = ("x461a", "x461b", "x464", "x465", "x466", "x467")


def preboot(key, profile_name, prefix, driver_file, repo=REPO, compute=None):
    """The driver's prefix, profile and file name its session (CLAUDE.md s5); no artifact of the prefix committed; the
    profile's TOML; the harness markers in the repository; STAGED_FROM mod/'s last commit; the fixture fresh; the
    session's prerun current. Returns (checks, ok)."""
    import tomllib
    c = {"key": key in SESSIONS, "prefix": prefix == key, "profile": profile_name == g(SESSIONS, key, "profile"),
         "driver_file": os.path.basename(driver_file) == g(SESSIONS, key, "driver")}
    c["no_prior_artifact"] = not glob.glob(os.path.join(repo, "testing", "artifacts", prefix + "-*"))
    head = mod_head(repo)
    c["staged_from_is_mod_head"] = head is not None and (head.startswith(STAGED_FROM) or STAGED_FROM.startswith(head))
    try:
        with open(os.path.join(repo, "testing", "profiles", profile_name + ".toml"), encoding="utf-8") as fh:
            text = fh.read()
        prof = profile_doc_checks(profile_name, tomllib.loads(text), text)
    except (OSError, ValueError) as e:
        prof = {"profile_read": False, "error": f"{type(e).__name__}: {e}"}
    c["profile_checks"] = prof
    found, ok = harness_markers_ok(repo)
    c["harness_markers"] = ok
    c["harness_found"] = found
    fr = fixture_fresh(repo)
    c["fixture"] = fr
    c["fixture_fresh"] = fr["fresh"]
    pr = prerun_current(key, repo, compute)
    c["prerun"] = pr
    c["prerun_current"] = pr["ok"]
    skip = ("profile_checks", "harness_found", "fixture", "prerun")
    good = all(v is True for k, v in c.items() if k not in skip) and \
        all(v is True for k, v in prof.items() if k != "error")
    return c, good


def staged_gate(repo=REPO):
    """x45g_lib's gate at this lib's paths and commit."""
    return G.staged_gate(repo=repo, commit=STAGED_FROM, stage_root=STAGE_ROOT, stage_mod=STAGE_MOD)


# ================================================================ the session
class Sess(G.Sess):
    """One x46 session's phases over an xlib.Xs, on x45g_lib.Sess's plumbing. `launch(S, user, sub)` relaunches a
    client (x463a, x463b), `kill(S)` and `restart(S, tag)` kill and start this session's own server (x463b); each is
    None offline unless a test passes a fake."""

    def __init__(self, xs, key, run_dir=None, launch=None, kill=None, restart=None, prerun=None):
        self.xs = xs
        self.out = xs.out
        self.key = key
        self.spec = SESSIONS[key]
        self.D = self.out.setdefault("checks", {})
        self.run_dir = run_dir
        self.speeds = self.out.setdefault("speeds", [])
        self.cur_speed = None
        self.restore_to = None
        self.pages, self.eats, self.pairs, self.points, self.consts, self.drinks = [], [], [], [], [], []
        self.sets = self.out.setdefault("sets", [])
        self.red0 = None
        self.launch, self.kill_fn, self.restart_fn = launch, kill, restart
        self.P = prerun if prerun is not None else PRERUN.get(key, {})
        self.out["lib_x46"] = LIB_FILE
        self.out["constants_x46"] = dict(CONSTANTS)
        self.out["prerun_x46"] = self.P

    # -- reads
    def glob_read(self, tag, paths, log=False):
        return vals(self.lread(tag, SRV, "_G", paths, log=log))

    def stomach_now(self, tag):
        return self.stomach(tag)

    def hunger(self, tag):
        return num(self.stats(tag).get("hunger"))

    def count(self, tag, full):
        r = self.k(tag, SRV, "witness.chain", f"{USER} getInventory.getCountTypeRecurse({full})", log=False)
        return num(r.get("value"))

    # -- the drink (x45g_lib.Sess.drink with the container, fluid and litres named)
    def drink46(self, container, fluid, litres, label):
        row = {"label": label, "container": container, "fluid": fluid, "litres": litres, "drunk": None}
        self.drinks.append(row)
        row["spawn"] = self.spawn(container, 1, label + "_spawn")
        row["fill"] = self.k(label + "_fill", SRV, "fluid.fill", f"{USER} {container} {fluid} {litres}")
        row["probe_before"] = self.k(label + "_probe0", SRV, "autodrink.probe", USER)
        fill, pb = row["fill"], row["probe_before"]
        want = fluid.lower()
        row["fill_ok"] = (fill.get("ok") is True and str(fill.get("fluid", "")).lower() == want
                          and pb.get("item") == container and str(pb.get("fluid", "")).lower() == want)
        if not row["fill_ok"]:
            self.xs.note(f"drink {label}: fill gate failed (fill {fill.get('ok')}/{fill.get('fluid')}, "
                         f"probe {pb.get('item')}/{pb.get('fluid')})")
        b = self.intake(label + "_before")
        row["age0"] = self.age(label + "_age0")
        q = self.k(label + "_drink", CLI, "drink.action", f"{container} 1")
        row["queued"] = {k: q.get(k) for k in ("queued", "percentage", "spawned", "itemId", "filledRatioBefore")}
        self.xs.spawned_stop(q, label)
        st = {"last": b.get("sips"), "still": 0, "rose": False}

        def fn():
            a = self.intake(label + "_poll")
            v = a.get("sips")
            if v is not None and st["last"] is not None and v > st["last"]:
                st["rose"], st["still"] = True, 0
            elif st["rose"]:
                st["still"] += 1
            st["last"] = v
            return st["rose"] and st["still"] >= SETTLE_POLLS, a
        self.poll(label + "_sips", fn, DRINK_CAP_S)
        row["landed"] = st["rose"]
        row["age1"] = self.age(label + "_age1")
        row["probe_after"] = self.k(label + "_probe1", SRV, "autodrink.probe", USER)
        l0 = num(g(row, "fill", "litres"))
        l1 = num(g(row, "probe_after", "litres")) if g(row, "probe_after", "item") == container else 0.0
        row["drunk"] = (l0 - l1) if (l0 is not None and l1 is not None) else None
        if not st["rose"]:
            self.xs.note(f"drink {label}: sips never rose")
        self.D.setdefault("drinks", []).append(row)
        return row

    def watch(self, label, hours, speed=1, pairs=False):
        a = self.age(label + "_a")
        end = (a or 0.0) + hours
        fn = (lambda x: self.pair(label)) if pairs else None
        return self.run_until(end, speed, label, every_s=G.PAIR_EVERY_S if pairs else None, fn=fn)

    # ======================================================== the shared phases
    def phase_S46(self):
        self.phase_S()
        P = self.D["S"]
        P["sleep"] = self.glob_read("S_sleep", (SLEEPON_G[3:],), log=True)
        if self.key in ("x461a", "x461b"):
            P["autodrink"] = self.k("S_autodrink", SRV, "autodrink.set", f"{USER} false")

    def phase_H(self):
        P = self.D["H"] = {}
        paths = list(RING46[self.key])
        rec = [p for p in paths if not p.startswith("_G.")]
        P["ring_paths"] = paths
        P["h1_record"] = self.lread("H_h1", SRV, f"record:{USER}", rec + list(G.H1_EXTRA))
        P["h1_globals"] = self.lread("H_h1g", SRV, "_G", [p[3:] for p in paths if p.startswith("_G.")])
        P["ring_start"] = self.ring_start(paths)

    def phase_E(self):
        """Speed 5 until the seed plate has emptied (the stomach under EMPTY_G), at most EMPTY_CAP_H; then speed 1."""
        P = self.D["E"] = {"start": self.age("E_a0")}
        cap = (P["start"] or 0.0) + EMPTY_CAP_H
        st = {"mass": None}

        def stop(a):
            st["mass"] = self.stomach("E_st")["mass"]
            return st["mass"] is not None and st["mass"] < EMPTY_G
        P["reached"] = self.run_until(cap, G.SPEED_FAST, "E_fast", stop=stop)
        P["mass"] = st["mass"]
        P["emptied"] = st["mass"] is not None and st["mass"] < EMPTY_G
        if not P["emptied"]:
            self.xs.note(f"E: the stomach read {st['mass']} g at the cap")
        self.set_speed(1, "E_one")
        P["end"] = self.age("E_a1")

    # ======================================================== x461a: the plate and the water
    def phase_F461a(self):
        P = self.D["F"] = {}
        P["bolognese"] = self.spawn(BOLOGNESE, 1, "F_bol")
        P["banana"] = self.spawn(BANANA, 1, "F_ban")
        P["broccoli"] = self.spawn(BROCCOLI, 2, "F_broc")

    def phase_P(self):
        P = self.D["P"] = {"start": self.age("P_a0"), "eats": []}
        self.set_speed(1, "P_one")
        for i, full in enumerate(PLATE):
            P["eats"].append(self.eat(full, f"P_eat{i}"))
        P["water"] = self.drink46(BOTTLE, WATER, DRINK_L, "P_water")
        P["watch_end"] = self.watch("P_watch", PLATE_WATCH_H, 1, pairs=True)

    def phase_T(self):
        self.D["T"] = {"end": self.watch("T_tail", TAIL_H, G.SPEED_FAST)}

    # ======================================================== x461b: x363's water, milk and solid
    def phase_F461b(self):
        self.D["F"] = {"solid": self.spawn(MILKSOLID, 1, "F_solid")}

    def phase_WA(self):
        P = self.D["WA"] = {}
        self.set_speed(1, "WA_one")
        P["water"] = self.drink46(BOTTLE, WATER, DRINK_L, "WA_water")
        P["end"] = self.watch("WA_watch", WATCH_M / 60.0, 1)

    def phase_MI(self):
        P = self.D["MI"] = {}
        self.set_speed(1, "MI_one")
        P["milk"] = self.drink46(CARTON, COWMILK, DRINK_L, "MI_milk")
        P["end"] = self.watch("MI_watch", WATCH_M / 60.0, 1)

    def phase_SO(self):
        P = self.D["SO"] = {"start": self.age("SO_a0")}
        cap = (P["start"] or 0.0) + REQ_CAP_H
        st = {"h": None}

        def stop(a):
            st["h"] = self.hunger("SO_h")
            return st["h"] is not None and st["h"] >= H_REQ
        P["request_age"] = self.run_until(cap, G.SPEED_FAST, "SO_fast", stop=stop)
        P["request_hunger"] = st["h"]
        P["capped"] = not (st["h"] is not None and st["h"] >= H_REQ)
        self.set_speed(1, "SO_one")
        P["eat"] = self.eat(MILKSOLID, "SO_solid")
        P["end"] = self.watch("SO_watch", WATCH_M / 60.0, 1)

    # ======================================================== x462: the tooltip hide
    def phase_F462(self):
        self.D["F"] = {"food": self.spawn(TOOLTIP_FOOD, 1, "F_food")}

    def phase_TM(self):
        P = self.D["TM"] = {}
        P["option_before"] = self.k("TM_opt0", CLI, "lua.call", "NutritionRevamp.client.tooltip.optionOn").get("r1")
        P["on"] = self.k("TM_on", CLI, "tooltip.measure", f"{TOOLTIP_FOOD} 1")
        P["off"] = self.k("TM_off", CLI, "tooltip.measure", f"{TOOLTIP_FOOD} 0")
        P["option_after"] = self.k("TM_opt1", CLI, "lua.call", "NutritionRevamp.client.tooltip.optionOn").get("r1")

    # ======================================================== x463a: the offline freeze
    def freeze_read(self, tag):
        v = self.rec(tag, FREEZE_PATHS, log=True)
        return {p: v.get(p) for p in FREEZE_PATHS}

    def phase_PRE(self):
        P = self.D["PRE"] = {}
        P["bolognese"] = self.spawn(BOLOGNESE, 1, "PRE_bol")
        self.set_speed(1, "PRE_one")
        P["eat"] = self.eat(BOLOGNESE, "PRE_eat")
        P["coffee"] = self.drink46(BOTTLE, COFFEE, COFFEE_L, "PRE_coffee")
        P["end"] = self.watch("PRE_watch", PRE_H, 1)

    def players_gone(self, lst):
        if isinstance(lst, list):
            return USER not in lst
        return isinstance(lst, dict) and not lst

    def save_pages(self, tag, suffix):
        """The ring's pages read now, renamed <name>-<suffix>.json in the run folder (a ring started again reads its
        pages under the same names), then the ring stopped."""
        pages = self.read_pages(tag)
        files = []
        for pg in pages:
            f = pg.get("file")
            if not f or not self.run_dir:
                continue
            new = f[:-5] + f"-{suffix}.json"
            try:
                os.replace(os.path.join(self.run_dir, f), os.path.join(self.run_dir, new))
                self.xs.copied = [c for c in self.xs.copied if c != f] + [new]
                pg["file"] = new
                files.append(new)
            except OSError as e:
                pg["rename_error"] = f"{type(e).__name__}: {e}"
        stop = self.k(tag + "_stop", SRV, "minute.ring", f"{USER} stop")
        return {"pages": pages, "files": files, "stop": stop}

    def phase_OFF(self):
        o = self.D["OFF"] = {"rejoined": False}
        self.set_speed(1, "OFF_one")
        o["pre"] = self.freeze_read("OFF_pre")
        c = self.xs.clients.get(USER)
        q = {"wall0": self.xs.wall()}
        try:
            q["rc"] = c.quit() if c is not None else None
        except Exception as e:                       # noqa: BLE001 - recorded
            q["error"] = f"{type(e).__name__}: {e}"
        q["wall1"] = self.xs.wall()
        self.xs.clients.pop(USER, None)
        o["quit"] = q

        def gone():
            lst = self.xs.step("OFF_players", SRV, "players", log=False).get("ack")
            return self.players_gone(lst), lst
        o["depart"] = self.poll("OFF_depart", gone, DEPART_CAP_S, 0.5)
        if not o["depart"]["done"]:
            self.xs.note("OFF: admin never left the server inside the cap; the clock is not raised")
            return
        o["away0"] = self.freeze_read("OFF_away0")
        o["ring_pre"] = self.save_pages("OFF_ring", "pre")
        o["restore_to"] = num(self.snap("OFF_mult0", log=True).get("trueMult"))
        ls = num(o["away0"].get("lastSeen"))
        if ls is None or o["restore_to"] is None:
            self.xs.note("OFF: lastSeen or trueMult unread; the clock is not raised")
            return
        o["target"] = ls + AWAY_MIN_H + 0.5
        try:
            o["raise"] = self.set_mult(AWAY_MULT, "OFF_raise")

            def fn():
                a = self.age("OFF_wait")
                return (a is not None and a >= o["target"]), a
            o["away_wait"] = {k: v for k, v in self.poll("OFF_wait", fn, AWAY_CAP_S, AWAY_POLL_S).items()}
        finally:
            o["restore"] = self.set_mult(o["restore_to"], "OFF_restore")
            if not o["restore"]["ok"]:
                o["restore_retry"] = self.set_mult(o["restore_to"], "OFF_restore2")
        if not (o["restore"]["ok"] or g(o, "restore_retry", "ok")):
            self.xs.note("OFF: the multiplier did not read back the value read before; admin does not rejoin")
            return
        o["away1"] = self.freeze_read("OFF_away1")
        o["ring_start2"] = self.ring_start(list(RING46[self.key]), tag="OFF_ring2")
        o["stats0"] = self.glob_read("OFF_st0", STORE_STATS, log=True)
        o["launch"] = self.launch(self, USER, "c1b") if self.launch else {"error": "no launcher"}
        o["rejoined"] = bool(g(o, "launch", "ready_took"))
        if not o["rejoined"]:
            return

        def moved():
            v = num(self.rec("OFF_first", ("lastSeen",)).get("lastSeen"))
            return (v is not None and v > ls + 1.0), v
        o["resume_wait"] = self.poll("OFF_resume", moved, RESUME_CAP_S, 0.5)
        o["stats1"] = self.glob_read("OFF_st1", STORE_STATS, log=True)
        o["first"] = self.freeze_read("OFF_first_read")
        o["end"] = self.watch("OFF_return", RETURN_H, 1)
        self.out["world_changes"]["left_in_place"].append(
            "OFF: admin quit; the clock ran at AWAY_MULT and was restored; admin rejoined from a fresh client restore "
            "in <run>/c1b")

    # ======================================================== x463b: the hard kill
    def store_read(self, tag):
        r = vals(self.lread(tag, SRV, f"record:{USER}", FREEZE_STAMPS + (BANANA_ENTRY,), log=True))
        latest = max([num(r.get(p)) for p in FREEZE_STAMPS if num(r.get(p)) is not None], default=None)
        return {"values": r, "latest": latest, "entry": r.get(BANANA_ENTRY)}

    def phase_F463b(self):
        self.D["F"] = {"banana": self.spawn(BANANA, 2, "F_ban")}

    def phase_ADV(self):
        self.D["ADV"] = {"end": self.watch("ADV_fast", ADV_H, G.SPEED_FAST)}
        self.set_speed(1, "ADV_one")
        self.D["ADV"]["lastWrite"] = num(self.glob_read("ADV_lw", (LASTWRITE,)).get(LASTWRITE))

    def file_latest(self, tag):
        """The slot file's latest stamp (the max over FREEZE_STAMPS of the text the store last wrote, W's read):
        the stamp the load rule compares with the world at the sight (review H1)."""
        last = self.k(tag, SRV, "lua.global", FILE_LAST)
        txt = last.get("value")
        try:
            rec = json.loads(txt).get("rec") if isinstance(txt, str) else None
        except (ValueError, AttributeError):
            rec = None
        if not isinstance(rec, dict):
            return None
        vs = []
        for p in FREEZE_STAMPS:
            d = rec
            for seg in p.split("."):
                d = d.get(seg) if isinstance(d, dict) else None
            if num(d) is not None:
                vs.append(num(d))
        return max(vs) if vs else None

    def wait_write(self, tag, after, cap_s):
        """The store's lastWrite polled until it passes `after` (None: any read)."""
        def fn():
            lw = num(self.glob_read(tag, (LASTWRITE,)).get(LASTWRITE))
            return (lw is not None and (after is None or lw > after)), lw
        return self.poll(tag, fn, cap_s)

    def phase_SAVE(self):
        """Review H2: the character's copy exists before the world save: a slot write after ADV's end (each writes the
        copy, BK.write) and the backup's writes at 1 or more; else the arm is skipped (its grades unmeasured)."""
        P = self.D["SAVE"] = {}
        w = self.wait_write("SAVE_lw", num(g(self.D, "ADV", "lastWrite")), SAVE_CAP_S)
        P["write_after_adv"], P["lastWrite"] = w["done"], w["last"]
        P["backup_before"] = self.glob_read("SAVE_bk0", BACKUP_STATS, log=True)
        P["copy_ready"] = w["done"] and (num(P["backup_before"].get(BACKUP_STATS[0])) or 0) >= 1
        if not P["copy_ready"]:
            self.xs.note("SAVE: no slot write after ADV or no backup write; the kill arm is skipped")
            return
        P["rcon"] = self.xs.rcon("save", "SAVE_rcon")
        self.sleep_until(self.xs.clock() + SAVE_SETTLE_S)
        P["age"] = self.age("SAVE_age")
        P["store"] = self.store_read("SAVE_store")
        P["backup"] = self.glob_read("SAVE_bk", BACKUP_STATS, log=True)

    def phase_EAT(self):
        P = self.D["EAT"] = {}
        P["count_before"] = self.count("EAT_n0", BANANA)
        lw0 = num(self.glob_read("EAT_lw0", (LASTWRITE,)).get(LASTWRITE))
        P["eat"] = self.eat(BANANA, "EAT_ban")

        def fn():
            lw = num(self.glob_read("EAT_lw", (LASTWRITE,)).get(LASTWRITE))
            return (lw is not None and (lw0 is None or lw > lw0)), lw
        P["saved"] = self.poll("EAT_save", fn, SAVE_CAP_S)["done"]
        P["count_after"] = self.count("EAT_n1", BANANA)
        st = self.store_read("EAT_store")
        P.update({"latest": st["latest"], "entry": st["entry"], "store": st})
        P["backup"] = self.glob_read("EAT_bk", BACKUP_STATS, log=True)
        P["eat_write"] = num(self.glob_read("EAT_lw1", (LASTWRITE,)).get(LASTWRITE))
        P["late_end"] = self.watch("EAT_late", LATE_H, G.SPEED_FAST)
        w = self.wait_write("EAT_late_lw", P["eat_write"], LATE_WRITE_CAP_S)      # review H1: the FILE moves on
        P["late_write"], P["late_lastWrite"] = w["done"], w["last"]
        P["file_latest"] = self.file_latest("EAT_file")
        st = self.store_read("EAT_store2")
        P.update({"latest": st["latest"], "store2": st})
        P["age"] = self.age("EAT_age")

    def phase_KILL(self):
        P = self.D["KILL"] = {}
        if not g(self.D, "SAVE", "copy_ready"):
            P["skipped"] = "the copy was not ready before the world save (review H2)"
            self.xs.note("KILL: skipped: " + P["skipped"])
            return
        c = self.xs.clients.get(USER)
        P["client_pid"] = getattr(getattr(c, "proc", None), "pid", None)          # review L1, before the kill
        P.update(self.kill_fn(self) if self.kill_fn else {"error": "no killer"})
        if self.run_dir:
            P["players_db"] = players_db_read(os.path.join(self.run_dir, *PLAYERS_DB_REL))
        try:                                        # review L1/L2: this session's own client of a dead server, killed
            if c is not None:
                c.kill()
            P["client_killed"] = c is not None
        except Exception as e:                       # noqa: BLE001 - recorded
            P["client_kill_error"] = f"{type(e).__name__}: {e}"
        self.xs.clients.pop(USER, None)

    def phase_UP(self):
        P = self.D["UP"] = {}
        if not g(self.D, "KILL", "exited"):
            self.xs.note("UP: the server did not exit; no restart")
            return
        P["restart"] = self.restart_fn(self, "up") if self.restart_fn else {"error": "no restarter"}
        if not g(P, "restart", "ok"):
            return
        P["age_restart"] = self.age("UP_age0")
        P["launch"] = self.launch(self, USER, "c1b") if self.launch else {"error": "no launcher"}
        if not g(P, "launch", "ready_took"):
            return

        def fn():
            # review L5: the record, the counters, the copy and the age in the iteration that first sees the record,
            # before the restore's dirty slot rewrites the copy at the next store step
            st = self.store_read("UP_rec")
            v = num(st["values"].get("lastSeen"))
            if v is None:
                return False, None
            snap = {"record": st, "sight_lastSeen": v, "age": self.age("UP_age"),
                    "backup": self.glob_read("UP_bk", BACKUP_STATS, log=True),
                    "store": self.glob_read("UP_st", STORE_STATS, log=True),
                    "copy": self.k("UP_copy", SRV, "witness.moddata",
                                   f"player:{USER} NutritionRevamp.backup.age NutritionRevamp.backup.n")}
            return True, snap
        w = self.poll("UP_rec_wait", fn, UP_CAP_S, 0.5)
        P["record_wait"] = {"done": w["done"], "polls": w["polls"]}
        if w["done"]:
            P.update(w["last"])
            P["entry"] = P["record"]["entry"]
        P["count"] = self.count("UP_n", BANANA)
        self.out["world_changes"]["left_in_place"].append(
            "KILL/UP: the session's own server killed and started again on its run folder; admin rejoined in "
            "<run>/c1b")

    # ======================================================== x464: the body clock
    def sleep_until_booked(self, label, booked_h, cap_s):
        """x447's night (x30's, shortened): player.sleep.hold, acute.winSleptH polled until booked_h more is booked
        (Plan 16 Task 7's rule: never the unbroken run), the hold cancelled and the flag cleared."""
        n = {"label": label, "age0": self.age(label + "_a0")}
        w0 = num(self.rec(label + "_w0", ("acute.winSleptH",)).get("acute.winSleptH")) or 0.0
        n["win0"] = w0
        n["hold"] = self.k(label + "_hold", SRV, "player.sleep.hold", f"{USER} {HOLD_S}")

        def fn():
            v = num(self.rec(label + "_win", ("acute.winSleptH",)).get("acute.winSleptH"))
            return (v is not None and v - w0 >= booked_h), v
        p = self.poll(label + "_poll", fn, cap_s, SLEEP_POLL_S)
        n["reached"], n["win1"] = p["done"], p["last"]
        n["cancel"] = self.k(label + "_cancel", SRV, "player.sleep.hold", f"{USER} 0")
        n["wake"] = self.k(label + "_wake", SRV, "player.sleep", f"{USER} false")
        self.sleep_until(self.xs.clock() + WAKE_SETTLE_S)
        n["age1"] = self.age(label + "_a1")
        return n

    def phase_TR(self):
        P = self.D["TR"] = {"a0": self.age("TR_a0")}
        P["a1"] = self.watch("TR_watch", TRACK_H, 1)

    def phase_NAP(self):
        P = self.D["NAP"] = self.sleep_until_booked("NAP", NAP_H, SLEEP_CAP_S)
        P["a2"] = self.watch("NAP_awake", AWAKE_H, 1)

    def phase_FULL(self):
        P = self.D["FULL"] = self.sleep_until_booked("FULL", FULL_H, SLEEP_CAP_S)
        P["a2"] = self.watch("FULL_awake", AWAKE_H, 1)

    def ini_value(self, key):
        """A key of the run's server ini (the profile's [server] keys, and what changeoption saves), or None."""
        ini = getattr(self.xs.server, "ini", None)
        try:
            with open(ini, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = re.match(r"^\s*" + re.escape(key) + r"\s*=\s*(\S*)", line)
                    if m:
                        return m.group(1)
        except (OSError, TypeError):
            return None
        return None

    def change_sleep(self, label, value):
        return self.xs.rcon(f"changeoption SleepAllowed {'true' if value else 'false'}", label)

    def toggle(self, label, value, want, hours):
        """The setting changed by RCON, the age read BEFORE it (review M1); the flip graded off the ring's polled
        setting (grade_x464); the live poll of the setting kept as a reading."""
        P = self.D[label] = {}
        self.set_speed(1, label + "_one")
        P["change_age"] = self.age(label + "_a0")
        P["rcon"] = self.change_sleep(label + "_rcon", value)

        def fn():
            v = self.glob_read(label + "_poll", (SLEEPON_G[3:],)).get(SLEEPON_G[3:])
            return v is want, v
        p = self.poll(label + "_poll", fn, POLL_CAP_S, POLL_S_FAST)
        P["poll_age"] = self.age(label + "_a1") if p["done"] else None
        P["followed"] = p["done"]
        P["a2"] = self.watch(label + "_watch", hours, 1)
        return P

    def phase_OFF464(self):
        raw = self.ini_value("SleepAllowed")                      # review L3: the value before, restored after
        self.D["sleep_allowed_before"] = None if raw is None else raw.lower() == "true"
        self.toggle("OFF", False, False, OFF_H)

    def phase_ON464(self):
        before = self.D.get("sleep_allowed_before")
        if before is None:
            self.xs.note("ON: SleepAllowed unread before OFF; set true, the profile's value")
            before = True
        self.toggle("ON", before, before, ON_H)
        self.D["sleep_restored"] = g(self.D, "ON", "rcon", "ok") is True

    def phase_C46(self):
        """The clock restored, and (review L3) every other setting this session changed restored from the value read
        before it: x461a/b's auto-drink flag from autodrink.set's `before`, x464's SleepAllowed when ON did not run."""
        before = g(self.D, "S", "autodrink", "before")
        if g(self.D, "S", "autodrink") is not None and isinstance(before, bool):
            self.D["autodrink_restore"] = self.k("C_autodrink", SRV, "autodrink.set",
                                                 f"{USER} {'true' if before else 'false'}")
        if "OFF" in self.D and not self.D.get("sleep_restored"):
            b = self.D.get("sleep_allowed_before")
            self.D["sleep_restore"] = self.change_sleep("C_sleep", True if b is None else b)
        self.restore_clock()

    # ======================================================== x465: the fast-forwarded night
    def ff_read(self):
        ini = getattr(self.xs.server, "ini", None)
        try:
            with open(ini, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = re.match(r"^\s*FastForwardMultiplier\s*=\s*([0-9.]+)", line)
                    if m:
                        return float(m.group(1))
        except (OSError, TypeError):
            return None
        return None

    def phase_PRE465(self):
        P = self.D["PRE"] = {"ff": self.ff_read(), "a0": self.age("PRE_a0")}
        P["a1"] = self.watch("PRE_watch", PRE_H, 1)

    def phase_NIGHT(self):
        self.D["NIGHT"] = self.sleep_until_booked("NIGHT", NIGHT_H, NIGHT_CAP_S)

    def phase_POST(self):
        P = self.D["POST"] = {"a0": self.age("POST_a0")}
        P["a1"] = self.watch("POST_watch", POST_H, 1)
        a = self.age("POST_age")
        P["read"] = {"age": a, "lastSeen": num(self.rec("POST_rec", ("lastSeen",)).get("lastSeen"))}

    # ======================================================== x466: the server refusal
    def phase_F466(self):
        self.D["F"] = {"broccoli": self.spawn(BROCCOLI, 2, "F_broc")}

    def phase_SEED466(self):
        P = self.D["SEED"] = {}
        P["slow"] = self.set_mult(SLOW_MULT, "SEED_slow")
        st = self.stomach("SEED_st0")
        P["before"] = st
        w = num(st["values"].get("stomach.buffer.water"))
        cal = num(st["values"].get("stomach.buffer.calories"))
        if st["mass"] is None or w is None:
            raise RuntimeError(f"the stomach did not read: {st}")
        P["calories"] = self.record_set("SEED_kcal", "stomach.buffer.calories", f"{max(cal or 0.0, SEED_KCAL):.3f}")
        P["water"] = self.record_set("SEED_water", "stomach.buffer.water", f"{w + (SEED_G - st['mass']):.3f}")
        st1 = self.stomach("SEED_st1")
        P["after"] = st1
        if st1["mass"] is not None and st1["mass"] < SEED_MIN_G:
            w1 = num(st1["values"].get("stomach.buffer.water")) or 0.0
            P["reset"] = self.record_set("SEED_water2", "stomach.buffer.water", f"{w1 + (SEED_G - st1['mass']):.3f}")
            self.xs.note(f"SEED: the stomach read {st1['mass']} g after the seed, under {SEED_MIN_G}; water re-set")

        def fn():
            s = self.stats("SEED_timer")
            return G.refusing({"timer": s.get("foodTimer")}), s.get("foodTimer")
        P["timer"] = self.poll("SEED_timer", fn, TIMER_CAP_S, TIMER_POLL_S)

    def phase_X466(self):
        P = self.D["X"] = {}
        st = self.stomach("X_st0")
        s = self.stats("X_s0")
        P["at"] = {"level": st["level"], "mass": st["mass"], "timer": s.get("foodTimer")}
        P["M_before"] = num(self.rec("X_M0", ("satiety.M",)).get("satiety.M"))
        P["mass_before"] = st["mass"]
        P["intake_before"] = self.intake("X_in0")
        P["guard_before"] = self.glob_read("X_g0", GUARD_PATHS, log=True)
        P["item_before"] = self.xs.item_id(BROCCOLI, "X_item0")
        P["count_before"] = self.count("X_n0", BROCCOLI)
        qb = self.k("X_queue0", CLI, "action.cancel")                 # review M2: the eat goes into an empty queue
        P["queue_before"] = {k: qb.get(k) for k in ("ok", "before", "current", "javaBefore")}
        if num(qb.get("before")) != 0 or qb.get("current") is not None:
            self.xs.note(f"X: the client queue was not empty before the eat: {P['queue_before']}")
        t0 = self.xs.clock()
        q = self.k("X_eat", CLI, "eat.action", f"{BROCCOLI} 1")
        P["eat"] = {k: q.get(k) for k in ("queued", "spawned", "itemId", "validStart", "maxTime", "moodleFoodEaten")}
        self.xs.spawned_stop(q, "X_eat")
        self.sleep_until(t0 + REFUSE_WAIT_S)
        P["intake_after"] = self.intake("X_in1")
        P["guard_after"] = self.glob_read("X_g1", GUARD_PATHS, log=True)
        P["item_after"] = self.xs.item_id(BROCCOLI, "X_item1")
        P["count_after"] = self.count("X_n1", BROCCOLI)
        P["M_after"] = num(self.rec("X_M1", ("satiety.M",)).get("satiety.M"))
        P["mass_after"] = self.stomach("X_st1")["mass"]
        P["cancel"] = self.k("X_cancel", CLI, "action.cancel")
        P["drink"] = self.drink46(BOTTLE, WATER, DRINK_466_L, "X_drink")

    # ======================================================== x467: the three-meal day (x452's phases)
    def phase_F467(self):
        P = self.D["F"] = {}
        P["bolognese"] = self.spawn(BOLOGNESE, 3, "F_bol")
        P["banana"] = self.spawn(BANANA, G.SPAWN_BANANAS, "F_ban")

    def phases(self):
        S, H, R = ("S", self.phase_S46), ("H", self.phase_H), ("R", self.phase_R)
        C, W = ("C", self.phase_C46), ("W", self.phase_W)
        return {
            "x461a": [S, H, W, ("F", self.phase_F461a), ("E", self.phase_E), ("P", self.phase_P),
                      ("T", self.phase_T), C, R],
            "x461b": [S, H, W, ("F", self.phase_F461b), ("E", self.phase_E), ("WA", self.phase_WA),
                      ("MI", self.phase_MI), ("SO", self.phase_SO), C, R],
            "x462": [S, ("F", self.phase_F462), ("TM", self.phase_TM), C],
            "x463a": [S, H, ("PRE", self.phase_PRE), ("OFF", self.phase_OFF), C, R],
            "x463b": [S, ("F", self.phase_F463b), ("ADV", self.phase_ADV), ("SAVE", self.phase_SAVE),
                      ("EAT", self.phase_EAT), ("KILL", self.phase_KILL), ("UP", self.phase_UP), C],
            "x464": [S, H, ("TR", self.phase_TR), ("NAP", self.phase_NAP), ("FULL", self.phase_FULL),
                     ("OFF", self.phase_OFF464), ("ON", self.phase_ON464), C, R],
            "x465": [S, H, ("PRE", self.phase_PRE465), ("NIGHT", self.phase_NIGHT), ("POST", self.phase_POST), C, R],
            "x466": [S, H, ("F", self.phase_F466), ("SEED", self.phase_SEED466), ("X", self.phase_X466),
                     ("C", self.phase_C453), R],
            "x467": [S, H, W, ("F", self.phase_F467), ("X", self.phase_X452), C, R],
        }[self.key]

    def closing_names(self):
        return ("C", "R")

    # ======================================================== the grades
    def grade_all(self):
        self.D["pairs"] = list(self.pairs)                                     # Plan 15 review F4
        if self.key in NO_RING:
            self._g("Z", G.grade_z(self.out), "a mod error line in the server log, or admin parked in the debugger")
            getattr(self, "grade_" + self.key)([])
            self.out["verdict_summary"] = {k: v.get("verdict") for k, v in self.out["verdicts"].items()}
            return
        saved = G.PAIR_SLACK_S
        G.PAIR_SLACK_S = PAIR_SLACK
        try:
            super().grade_all()
        finally:
            G.PAIR_SLACK_S = saved

    def grade_replay(self, rows):
        """The HEAD replay of the run's own ring with REPLAY_TOL (x45g_lib.Sess.grade_replay at this lib's paths, foods
        and tolerances), the ring's cold multiplier fed; THIRST's miss without it recorded as checks.cold_ablation."""
        xs = self.xs
        tol = REPLAY_TOL if self.key in ("x461a", "x461b") else G.REPLAY_TOL
        start_path = os.path.join(self.run_dir or "", "start.json")
        if not rows or not os.path.isfile(start_path):
            self.out["replay"] = {"error": "no ring rows or no start record"}
            for f in tol:
                xs.grade(f"REPLAY_{f}", "unmeasured", {"why": "no replay"}, "")
            return None
        with open(start_path, encoding="utf-8") as fh:
            start = json.load(fh)
        start_stats = g(self.D, "W", "start_stats") or {}
        drinks = [d for d in self.drinks if d.get("fill_ok")]
        events, book = replay_events(rows, self.eats, num(g(self.D, "W", "start_age")), drinks)
        nut = g(self.D, "S", "nutrition") or {}
        sex = g(self.D, "H", "h1_record", "values", "body.sex")
        player = {"female": sex == 2, "weight": num(nut.get("weight")) or 80.0,
                  "macros": [num(nut.get(k)) or 0.0 for k in ("calories", "carbs", "lipids", "proteins")]}
        if self.run_dir:
            for name, obj in (("events.json", events), ("player.json", player)):
                with open(os.path.join(self.run_dir, name), "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(obj, fh, indent=1, sort_keys=True)
                xs.copied.append(name)
        self.out["model_inputs"] = {"tool": "tools/replay_live.py replay_live (ServerReplay) at HEAD, ring_cold auto",
                                    "ring": self.pages, "events": "events.json", "start": "start.json",
                                    "start_stats": start_stats, "player": player, "sleep_allowed": False,
                                    "tol": {k: list(v) for k, v in tol.items()}, "bookkeeping": book}
        try:
            rep, d, be = replay_grade(rows, events, start, tol, paths=list(RING46[self.key]), player=player,
                                      start_stats=start_stats)
        except Exception as e:                     # noqa: BLE001 - recorded, graded unmeasured
            self.out["replay"] = {"error": f"{type(e).__name__}: {e}"}
            for f in tol:
                xs.grade(f"REPLAY_{f}", "unmeasured", {"why": "the replay raised"}, "")
            return None
        if self.run_dir:
            with open(os.path.join(self.run_dir, "replay.json"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"rows": rep, "diff": d, "events": events}, indent=1, sort_keys=True,
                                    default=str) + "\n")
            xs.copied.append("replay.json")
        self.out["replay"] = {"rows": len(rep), "fields": d.get("fields"), "findings_n": len(d.get("findings") or []),
                              "ring_cold": getattr(be, "ring_cold", None)}
        for f in tol:
            self._g(f"REPLAY_{f}", G.grade_replay_field(d, f), f"{f} off the HEAD replay by more than {tol[f][1]}")
        if self.key in ("x461a", "x461b"):
            try:
                _, d0, _ = replay_grade(rows, events, start, {"THIRST": tol["THIRST"]}, paths=list(RING46[self.key]),
                                        player=player, start_stats=start_stats, ring_cold=False)
                self.D["cold_ablation"] = {"THIRST": g(d0, "fields", "THIRST")}
            except Exception as e:                 # noqa: BLE001 - a reading
                self.D["cold_ablation"] = {"error": f"{type(e).__name__}: {e}"}
        return be

    def grade_x461_common(self, rows):
        be = self.grade_replay(rows)
        self._g("COLD_FED", grade_cold_fed(rows, getattr(be, "ring_cold", None) if be is not None else None),
                "no ring row carries the cold field, or the replay did not feed it")

    def grade_x461a(self, rows):
        self.grade_x461_common(rows)
        a0 = first_rise_age(rows, EATS_G, after=num(g(self.D, "P", "start")))
        ofm = overfull_minutes(rows, a0) if a0 is not None else None
        if ofm is not None:
            ofm["reached_3"] = ofm["m3"] > 0                     # review L6: a reading; OF_MIN_3's band holds 0
        self.D["overfull"] = ofm
        pr = self.P or {}
        self._g("OF_MIN_3", grade_band(g(ofm, "m3"), num(pr.get("of_m3")), OF_TOL_MIN, "Overfull 3+ minutes"),
                f"the minutes at Overfull 3 or more off the prerun by more than {OF_TOL_MIN}")
        self._g("OF_MIN_4", grade_band(g(ofm, "m4"), num(pr.get("of_m4")), OF_TOL_MIN, "Overfull 4 minutes"),
                f"the minutes at Overfull 4 off the prerun by more than {OF_TOL_MIN}")
        self._g("OF_PEAK", grade_band(g(ofm, "peak"), num(pr.get("of_peak")), OF_PEAK_TOL_G, "peak mass"),
                f"the peak stomach mass off the prerun by more than {OF_PEAK_TOL_G} g")

    def grade_x461b(self, rows):
        self.grade_x461_common(rows)
        wa0 = num(g(self.D, "WA", "water", "age0"))
        mi0 = num(g(self.D, "MI", "milk", "age0"))
        so0 = num(g(self.D, "SO", "start"))
        w = liquid_course(rows, wa0, mi0) if wa0 is not None and mi0 is not None else {}
        m = liquid_course(rows, mi0, so0) if mi0 is not None and so0 is not None else {}
        self.D["liquid"] = {"water": w, "milk": m}
        pr = self.P or {}
        self._g("W_PEAK", grade_band(w.get("peak"), num(pr.get("w_peak")), LIQ_PEAK_TOL_G, "water peak"),
                f"the water's liquid peak off the prerun by more than {LIQ_PEAK_TOL_G} g")
        self._g("W_HALF", grade_band(w.get("half_m"), num(pr.get("w_half_m")), LIQ_HALF_TOL_M, "water half-time"),
                f"the water's liquid half-time off the prerun by more than {LIQ_HALF_TOL_M} game minutes")
        self._g("M_PEAK", grade_band(m.get("peak"), num(pr.get("m_peak")), LIQ_PEAK_TOL_G, "milk peak"),
                f"the milk's liquid peak off the prerun by more than {LIQ_PEAK_TOL_G} g")

    def grade_x462(self, rows):
        T = self.D.get("TM") or {}
        self._g("T_ON", grade_tooltip(T.get("on"), True), "with the hide on, the hunger line drawn or a tag left")
        self._g("T_OFF", grade_tooltip(T.get("off"), False), "with the hide off, the hunger line not drawn")
        self._g("T_NATIVE", grade_native(T.get("on")), "the food carried the hide tag before the first call")
        self._g("T_RESTORED", grade_restored(T.get("on"), T.get("off"), T.get("option_before"), T.get("option_after")),
                "the option accessor not restored")

    def grade_x463a(self, rows):
        o = self.D.get("OFF") or {}
        pre = []
        for f in g(o, "ring_pre", "files") or []:
            try:
                with open(os.path.join(self.run_dir, f), encoding="utf-8") as fh:
                    pre += (json.load(fh).get("rows_list") or [])
            except (OSError, ValueError, TypeError):
                continue
        pre.sort(key=lambda r: r.get("s") or 0)
        away = o.get("away0") or {}
        self._g("AWAY_STILL", grade_away_still(away, o.get("away1")), "the record changed while its player was away")
        self._g("FREEZE", grade_freeze(rows, away), "a record value changed across the absence")
        st0, st1 = o.get("stats0") or {}, o.get("stats1") or {}
        rh = None
        a, b = num(st0.get(STORE_STATS[3])), num(st1.get(STORE_STATS[3]))
        if a is not None and b is not None:
            rh = b - a
        self._g("STAMPS", grade_stamps(rows, away, rh), "a stamp not moved by the one gap the resume counted")
        self._g("WRITTEN", grade_written(pre, rows, away), "a written stat changed across the absence")

    def grade_x463b(self, rows):
        K_, E, U = self.D.get("KILL") or {}, self.D.get("EAT") or {}, self.D.get("UP") or {}
        self._g("KILL_OWN", grade_kill_own(K_), "a PID other than the session's own server killed, or no exit")
        v, o = grade_rollback(U, E)
        self.xs.grade("ROLLBACK", v, o, "the world age after the restart not under the store file's latest stamp")
        rolled = v == "as_predicted"
        v, o = grade_restored_copy(U, rolled)
        self.xs.grade("RESTORED", v, o, "the copy not restored once, or an ahead store kept")
        restored = v == "as_predicted"
        if restored:
            self._g("ON_CLOCK", grade_on_clock(U), f"the restored record off the world clock by more than {ON_CLOCK_GM} "
                    "game minutes")
        else:
            self.xs.grade("ON_CLOCK", "unmeasured", {"why": "no restore read as predicted"}, "")
        self._g("CONSISTENT", grade_consistent(U, E, restored), "the record's eat and the inventory disagree")
        self._g("COPY_SAVED", grade_copy_saved(K_.get("players_db")), "the players.db blob holds no copy")
        self.D["fixture_players_db"] = players_db_read(os.path.join(REPO, FIXTURE_PLAYERS_DB))

    def grade_x464(self, rows):
        TR, NAP, FULL = self.D.get("TR") or {}, self.D.get("NAP") or {}, self.D.get("FULL") or {}
        OFF, ON = self.D.get("OFF") or {}, self.D.get("ON") or {}
        a_first = num(NAP.get("age0"))
        self._g("TRACK", grade_track(rows, num(TR.get("a0")) or 0.0, a_first if a_first is not None else 1e18),
                f"bodyHour off the world hour by more than {TRACK_TOL_H} h before any sleep")
        self._g("NAP_KEEP", grade_nap_keep(rows, num(NAP.get("age0")) or 0.0, num(NAP.get("a2")) or 0.0),
                "a nap reset the body clock")
        self._g("FULL_RESET", grade_full_reset(rows, num(FULL.get("age0")) or 0.0, num(FULL.get("a2")) or 0.0),
                f"a full sleep's close not at 07:00 plus the time since waking within {RESET_TOL_H} h")
        OFF["flip_age"] = ring_flip(rows, num(OFF.get("change_age")), False)
        ON["flip_age"] = ring_flip(rows, num(ON.get("change_age")), True)
        self._g("POLL_OFF", grade_poll(num(OFF.get("change_age")), num(OFF.get("flip_age"))),
                f"the sleep poll not following SleepAllowed false within {POLL_GM} game minutes")
        flip = num(OFF.get("flip_age"))
        nxt = None
        if flip is not None:
            nxt = next((ring_age(r) for r in online(rows) if ring_age(r) > flip), None)
        self._g("NO_RHYTHM", grade_no_rhythm(rows, nxt if nxt is not None else 1e18, num(OFF.get("a2")) or 0.0),
                "with sleep off, the clock on, a hunger factor not 1, circ not 0 or the phase moved")
        self._g("POLL_ON", grade_poll(num(ON.get("change_age")), num(ON.get("flip_age"))),
                f"the sleep poll not following SleepAllowed true within {POLL_GM} game minutes")
        self._g("RESEED", grade_reseed(rows, num(ON.get("change_age")) or 1e18),
                "sleep on again, the clock not seeded at the world hour")

    def grade_x465(self, rows):
        PRE, N, POST = self.D.get("PRE") or {}, self.D.get("NIGHT") or {}, self.D.get("POST") or {}
        self._g("FF_DEFAULT", grade_ff(PRE.get("ff")), "the server's FastForwardMultiplier not the default")
        book = night_booking(rows, num(N.get("age0")) or 0.0, num(POST.get("a1")) or 0.0)
        self.D["night"] = book
        if book and not book.get("window_closed"):
            hold = (num(N.get("age1")) or 0.0) - (num(N.get("age0")) or 0.0)
            self.D["night_reading"] = {"hold_span_h": hold, "asleep_share": book["asleep_h"] / hold if hold else None}
        self._g("NO_LOSS", grade_no_loss(book), "the night's booked sleep off the asleep steps' game hours")
        self._g("CAUGHT_UP", grade_caught_up(POST.get("read")), "the record still behind the world after the night")

    def grade_x466(self, rows):
        X_ = self.D.get("X") or {}
        v, o = grade_reached(X_.get("at"))
        self.xs.grade("REACHED", v, o, "not Overfull 4 with the food timer above 3200 at the attempt")
        if v != "as_predicted":
            for n in ("REFUSED", "ITEM_INTACT", "RECORD_KEPT", "QUEUE_CLEARED"):
                self.xs.grade(n, "unmeasured", {"why": "the attempt was not at Overfull 4"}, "")
        else:
            self._g("REFUSED", grade_refused(X_), "the guard did not refuse, or the eat landed")
            saw = server_saw(X_)
            for n, fn, why in (("ITEM_INTACT", lambda: grade_item_intact(X_), "the item changed or was consumed"),
                               ("RECORD_KEPT", lambda: grade_record_kept(X_), "the record took the refused eat"),
                               ("QUEUE_CLEARED", lambda: grade_queue_cleared(X_.get("cancel")),
                                "the client queue still held the eat")):
                if saw:
                    self._g(n, fn(), why)
                else:
                    self.xs.grade(n, "unmeasured", {"why": "the server never saw the eat (the guard's counters did "
                                                           "not rise)"}, why)
        self._g("DRINK_LANDS", grade_drink_lands(X_.get("drink")), "the drink after the refusal did not land")

    def grade_x467(self, rows):
        """x452's grade (x45g_lib.Sess.grade_x452: its phases and grades read no session key), its replay through
        this lib's grade_replay, then NO_RHYTHM_DAY."""
        self.grade_x452(rows)
        self._g("NO_RHYTHM_DAY", grade_no_rhythm_day(rows), "a sleep-off ring row with the clock on or a factor not 1")


def install_bands(prerun=None, setattr_=setattr):
    """x467's cadence bands (the prerun's) into the frozen module (x45i's precedent): this process only, or through a
    test's monkeypatch.setattr."""
    p = (prerun if prerun is not None else PRERUN).get("x467") or {}
    bands = p.get("cad_p") or {}
    setattr_(G, "CAD_P_TARGETS", {k: bands.get(k) for k in ("lunch", "dinner", "breakfast")})
    setattr_(G, "CAD_H_TARGET", p.get("cad_h"))


# ================================================================ the live run
def launch_real(make_client, prof, rec_fx, started, tl):
    """x43_strength_lib's relaunch: a fresh client restore in <run>/<sub>, started and waited ready."""
    def launch(S, user, sub):
        c, restored = make_client(os.path.join(S.run_dir, sub), user, S.xs.server, rec_fx,
                                  safemode=prof.safemode, launcher=prof.launcher)
        c.start()
        started.append(c)
        S.xs.clients[user] = c
        tl.mark("client_launch", user=user, which=sub, restored=restored)
        took = c.wait_ready(timeout=prof.client_timeout)
        tl.mark("client_ready", user=user, which=sub, took=took)
        return {"restored": restored, "ready_took": took}
    return launch


def kill_real(tl):
    """The hard-kill arm's kill: ONLY the server process this session's pzt started, identified by the PID its Server
    object holds, recorded before the kill (amendments s1); server.kill() is taskkill /PID <that pid> /T /F."""
    def kill(S):
        srv = S.xs.server
        proc = getattr(srv, "proc", None)
        out = {"pid_recorded": getattr(proc, "pid", None)}
        S.xs.persist()
        tl.mark("server_kill", pid=out["pid_recorded"])
        if proc is None:
            out["error"] = "no server process"
            return out
        out["alive_before"] = srv.alive
        r = subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, text=True)
        out["taskkill_rc"], out["taskkill_out"] = r.returncode, (r.stdout + r.stderr)[:300]
        out["pid_killed"] = proc.pid
        try:
            out["rc"] = proc.wait(KILL_WAIT_S)
            out["exited"] = True
        except Exception as e:                       # noqa: BLE001 - recorded
            out["exited"] = False
            out["error"] = f"{type(e).__name__}: {e}"
        return out
    return kill


def restart_real(prof, run_dir, tl):
    """The same Server object started again on its run folder's cache (the world as the engine last saved it), its log
    in a second file so the first stays whole."""
    def restart(S, tag):
        srv = S.xs.server
        out = {"log": f"server-stdout-{tag}.log"}
        try:
            srv._started.clear()
            srv.log_path = os.path.join(run_dir, out["log"])
            srv.bus.reset()
            out["took"] = srv.start(timeout=prof.server_timeout)
            out["pid"] = srv.proc.pid
            out["ok"] = True
            tl.mark("server_restarted", pid=out["pid"], took=out["took"])
        except Exception as e:                       # noqa: BLE001 - recorded
            out["ok"] = False
            out["error"] = f"{type(e).__name__}: {e}"
        S.xs.copied.append(out["log"])
        return out
    return restart


def main(key, prefix, profile_name, artifact, session_text, pred, budget_s, driver_file):
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_client, make_server, teardown, verify   # noqa: E402

    pre, ok = preboot(key, profile_name, prefix, driver_file)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    if key == "x467":
        install_bands()                                                  # this process only
    prof = profile.load(profile_name)
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(prefix)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"restored": f"fixture {prof.fixture} restored into the run dir", "left_in_place": []}}
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, predictions=pred, user=USER)
    xs.path = os.path.join(run_dir, artifact)
    S = Sess(xs, key, run_dir=run_dir, launch=launch_real(make_client, prof, rec_fx, started, tl),
             kill=kill_real(tl), restart=restart_real(prof, run_dir, tl))
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "session_key": key, "session": session_text, "driver": driver_file, "lib": LIB_FILE,
        "user": USER, "profile": prof.report(), "preboot": pre,
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", G.LUA_DIR),
        "harness_lua_dirty": git_dirty(G.LUA_DIR)[0],
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + LIB_FILE),
        "lib_x45g_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/x45g_lib.py"),
        "prerun_commit": git_say("log", "-1", "--format=%h", "--", PRERUN_FILE),
        "replay_tool_commit": git_say("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
        "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "predictions": pred, "meta": {"budget_s": budget_s},
    })
    if not doctor_clean:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"]:
        xs.refuse("the harness Lua is dirty; commit before the boot (CLAUDE.md s5)")
    mg = out["manifest_gate"] = staged_gate()
    want = f'"value": "{mg.get("staged_version")}"'
    vrows = [v for v in prof.verify if v.get("args") == f"{NR}.version"]
    mg["verify_rows_match"] = bool(vrows) and all(str(v.get("expect")) == want for v in vrows)
    if not (mg["ok"] and mg["verify_rows_match"]):
        xs.refuse(f"the staged copy does not match the pinned commit or the verify rows: {mg!r}; not started")
    try:
        shutil.copyfile(os.path.join(REPO, STAGE_ROOT, G.MANIFEST_NAME), os.path.join(run_dir, G.MANIFEST_NAME))
        xs.copied.append(G.MANIFEST_NAME)
    except OSError as e:
        out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(prof.sources)
    if out["lint_errors"]:
        xs.refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")
    server = None
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        holder["server"] = server
        xs.server = server
        out["server_launch_wall"] = xs.wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = xs.wall()
        out["server_pid"] = server.proc.pid
        tl.mark("server_started", pid=server.proc.pid)
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, started=started))
        tl.mark("session_ready")
        out["session_ready_wall"] = xs.wall()
        out["build"] = server.build
        out["verify"] = verify(prof, server, clients, tl)
        dm, okm = X.deployed_marker_check(run_dir, list(HARNESS_MARKERS), HARNESS_MARKERS)
        xs.mem("ready")
        xs.persist()
        if xs.abort_on_missing_marker(dm, okm):
            pass
        elif not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            S.body_run(S.phases())
    except Exception as e:                         # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            L = out["logs"] = {"patterns": {"log": LOG_RX.pattern, "restore": RESTORE_RX.pattern}}
            if server is not None:
                logs = sorted(set([os.path.join(run_dir, "server-stdout.log"), server.log_path]))
                L["server"], L["server_echo_excluded"], L["restore_lines"] = [], 0, []
                for lp in logs:
                    hits, skipped = X.grep_noecho(lp, LOG_RX, 300, G.ECHO_RX, G.NEVER_RX)
                    L["server"] += hits
                    L["server_echo_excluded"] += skipped
                    L["restore_lines"] += X.grep_noecho(lp, RESTORE_RX, 20, G.ECHO_RX, G.NEVER_RX)[0]
                L["mod_error"] = [ln for ln in L["server"] if MOD_ERR_RX.search(ln)][:40]
            for c in every:
                lines, _ = X.grep_noecho(c.console, LOG_RX, 80, G.ECHO_RX, G.NEVER_RX)
                L.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        xs.finish(teardown, hard_kill, every, read_logs=read_logs, grade_all=S.grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, artifact)
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "abort": out.get("abort"),
                      "budget_stop": out.get("budget_stop"), "stop_reason": out.get("stop_reason"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "logs_error": out.get("logs_error"),
                      "run_id": run_id, "run_dir": run_dir, "memory": out.get("memory"),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])
    return out
